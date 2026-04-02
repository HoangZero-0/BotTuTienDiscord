import re
import aiosqlite
from datetime import date
from discord.ext import commands


class get_db:
    """Context Manager để kết nối DB và kích hoạt WAL mode (Fix lỗi Threads once)"""

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None

    async def __aenter__(self):
        self.conn = await aiosqlite.connect(self.db_path)
        await self.conn.execute("PRAGMA journal_mode=WAL")
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            await self.conn.close()


async def update_quest_progress(db_path, user_id, goal_type, ctx=None):
    """
    Cập nhật tiến độ nhiệm vụ.
    Nếu ctx được cung cấp, sẽ gửi thông báo chúc mừng khi hoàn thành.
    """
    today = str(date.today())
    async with get_db(db_path) as db:
        # Tìm các nhiệm vụ có loại này
        cursor = await db.execute(
            "SELECT quest_id, goal_value, description, reward_lt, reward_tv FROM daily_quests WHERE goal_type = ?",
            (goal_type,),
        )
        quests = await cursor.fetchall()

        for q_id, q_goal, q_desc, r_lt, r_tv in quests:
            cursor = await db.execute(
                "SELECT current_progress, last_completed_date FROM player_quests WHERE user_id = ? AND quest_id = ?",
                (str(user_id), q_id),
            )
            row = await cursor.fetchone()

            if not row or row[1] != today:
                current_progress = 0
            else:
                current_progress = row[0]

            if current_progress < q_goal:
                new_progress = current_progress + 1
                await db.execute(
                    """
                    INSERT INTO player_quests (user_id, quest_id, current_progress, last_completed_date) 
                    VALUES (?, ?, ?, ?) 
                    ON CONFLICT(user_id, quest_id) DO UPDATE SET current_progress = ?, last_completed_date = ?""",
                    (str(user_id), q_id, new_progress, today, new_progress, today),
                )

                # CỘNG THƯỞNG KHI HOÀN THÀNH
                if new_progress == q_goal:
                    # Lấy cảnh giới và tv_max (tu_vi_can_thiet của cảnh giới tiếp theo)
                    c_p = await db.execute(
                        """
                        SELECT p.canh_gioi_id, p.tu_vi, 
                        (SELECT tu_vi_can_thiet FROM realms_master WHERE canh_gioi_id = p.canh_gioi_id + 1) as tv_max
                        FROM players p WHERE p.user_id = ?
                        """,
                        (str(user_id),),
                    )
                    p_row = await c_p.fetchone()
                    if p_row:
                        p_cg, p_tv, tv_max = p_row
                        if tv_max is None:
                            tv_max = 999_999_999_999  # Max cấp

                        # Thưởng theo cảnh giới (V2.0 Scaling)
                        bonus_mult = 1 + (p_cg * 0.3)
                        final_lt = int(r_lt * bonus_mult)
                        final_tv = int(r_tv * bonus_mult)

                        # Cộng thưởng có chặn trần Tu Vi
                        new_tv = min(tv_max, p_tv + final_tv)

                        await db.execute(
                            "UPDATE players SET linh_thach = linh_thach + ?, tu_vi = ? WHERE user_id = ?",
                            (final_lt, new_tv, str(user_id)),
                        )

                        # Thông báo nếu có ctx
                        if ctx:
                            import discord

                            embed = discord.Embed(
                                title="✅ NHIỆM VỤ HOÀN THÀNH",
                                description=(
                                    f"🎊 Chúc mừng đạo hữu đã hoàn thành: **{q_desc}**\n"
                                    f"💰 Nhận: **{final_lt:,} LT**\n"
                                    f"✨ Nhận: **{final_tv:,} TV** (Cảnh giới rank {p_cg})"
                                ),
                                color=discord.Color.green(),
                            )
                            embed.set_footer(
                                text="Gõ !nhiemvu để xem các thử thách khác!"
                            )
                            await ctx.send(embed=embed)
        await db.commit()


class CleanID(commands.Converter):
    """
    Converter dùng để làm sạch ID (item_id, auction_id, ...)
    từ các định dạng như <7>, #7, `7` hoặc '7'.
    """

    async def convert(self, ctx, argument):
        # Loại bỏ các ký tự không phải số
        cleaned = re.sub(r"\D", "", str(argument))
        if not cleaned:
            raise commands.BadArgument(
                f'Không thể chuyển đổi "{argument}" thành ID hợp lệ.'
            )
        return int(cleaned)


class CleanInt(commands.Converter):
    """
    Converter dùng cho các giá trị số (giá, lượng, ...)
    hỗ trợ các ký tự phân cách như 1.000 hoặc 1,000.
    """

    async def convert(self, ctx, argument):
        # Giữ lại số, loại bỏ dấu chấm/phẩy/ký tự lạ
        cleaned = re.sub(r"[^0-9]", "", str(argument))
        if not cleaned:
            raise commands.BadArgument(f'Giá trị "{argument}" không phải là số hợp lệ.')
        return int(cleaned)


async def setup_db_columns(db_path):
    async with get_db(db_path) as db:
        new_cols = {
            "dao_hieu": "TEXT DEFAULT NULL",
            "sinh_luc": "INTEGER DEFAULT 100",
            "the_luc": "INTEGER DEFAULT 120",
            "last_the_luc_restore": "REAL DEFAULT 0",
            "last_sinh_luc_restore": "REAL DEFAULT 0",
            "current_boss_id": "INTEGER DEFAULT 0",
            "current_boss_hp": "INTEGER DEFAULT 0",
            "is_active": "INTEGER DEFAULT 0",
        }
        for col, col_def in new_cols.items():
            try:
                await db.execute(f"ALTER TABLE players ADD COLUMN {col} {col_def}")
            except Exception:
                pass  # Cột đã tồn tại
        await db.commit()


async def update_player_stats(db_path, user_id):
    """
    Cập nhật sinh lực và thể lực dựa trên thời gian trôi qua.
    1 giây hồi 1 điểm. Thể lực max 120. Sinh lực max = canh_gioi_id * 100.
    """
    import time

    now = time.time()
    async with get_db(db_path) as db:
        cursor = await db.execute(
            "SELECT canh_gioi_id, the_luc, sinh_luc, last_the_luc_restore, last_sinh_luc_restore FROM players WHERE user_id = ?",
            (str(user_id),),
        )
        row = await cursor.fetchone()
        if not row:
            return

        cg_id, the_luc, sinh_luc, last_tl_time, last_sl_time = row
        max_tl = 120
        max_sl = cg_id * 100

        # Nếu the_luc đang null do chưa update
        if the_luc is None:
            the_luc = 120
        if sinh_luc is None:
            sinh_luc = max_sl
        if not last_tl_time:
            last_tl_time = now
        if not last_sl_time:
            last_sl_time = now

        # Tính thời gian trôi qua (giây)
        sl_diff = int(now - last_sl_time)

        new_tl = the_luc
        # Thể Lực: KHÔNG tự hồi theo giây nữa, đợi loop 5 phút của hệ thống

        new_sl = sinh_luc
        new_last_sl = last_sl_time
        if sl_diff > 0 and sinh_luc < max_sl:
            # Hồi 1% máu mỗi giây
            heal_amount = int(max_sl * 0.01 * sl_diff)
            new_sl = min(max_sl, sinh_luc + heal_amount)
            new_last_sl = now

        if new_sl != sinh_luc or not last_tl_time or not last_sl_time:
            await db.execute(
                "UPDATE players SET the_luc = ?, sinh_luc = ?, last_the_luc_restore = ?, last_sinh_luc_restore = ? WHERE user_id = ?",
                (new_tl, new_sl, new_last_tl, new_last_sl, str(user_id)),
            )
            await db.commit()

        return new_tl, new_sl, max_tl, max_sl
