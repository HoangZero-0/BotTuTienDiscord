import discord
from discord.ext import commands
import random
import asyncio
from utils import get_db


class BiCanh(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"

    # ========== SỰ KIỆN NGẪU NHIÊN TRONG BÍ CẢNH ==========
    # Tổng xác suất = 100%
    EVENTS = [
        ("treasure", 0.30),  # 30% - Kho báu: Nhận vật phẩm
        ("big_fortune", 0.08),  # 8%  - Cơ Duyên Lớn: Nhận đồ xịn + Tu Vi + CS
        ("trap_tv", 0.12),  # 12% - Bẫy trận: Mất % Tu Vi
        ("trap_cs", 0.10),  # 10% - Yêu khí xâm thực: Mất % Lực Chiến
        ("trap_item", 0.08),  # 8%  - Cướp đoạt: Rơi 1 vật phẩm
        ("npc", 0.12),  # 12% - NPC bí ẩn: Nhận Linh Thạch
        ("empty", 0.20),  # 20% - Tay không: Không nhận gì
    ]

    def _roll_event(self):
        roll = random.random()
        cumulative = 0
        for event_name, rate in self.EVENTS:
            cumulative += rate
            if roll < cumulative:
                return event_name
        return "empty"

    def _roll_grade(self, cg_id):
        """Roll phẩm cấp vật phẩm, cảnh giới cao = tỉ lệ đồ xịn cao hơn."""
        rates = {
            5: 0.0001 + (cg_id * 0.0003),  # Chí Tôn: Scale theo cảnh giới
            4: 0.001 + (cg_id * 0.002),  # Thần
            3: 0.02 + (cg_id * 0.008),  # Tiên
            2: 0.15 + (cg_id * 0.025),  # Linh
            1: 1.0,  # Phàm: Fallback
        }
        for grade in [5, 4, 3, 2, 1]:
            if random.random() < rates[grade]:
                return grade
        return 1

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def bicanh(self, ctx):
        user_id = str(ctx.author.id)
        async with get_db(self.db_path) as db:
            cursor = await db.execute(
                "SELECT canh_gioi_id, tu_vi, luc_chien_goc, the_luc, linh_thach FROM players WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return

            cg_id, tu_vi, luc_chien, the_luc, linh_thach = row

            # --- CHI PHÍ VÀO BÍ CẢNH ---
            if the_luc < 5:
                return await ctx.send(
                    "⚠️ Cần tối thiểu **5 Thể Lực** để thám hiểm bí cảnh!"
                )

            # Chi phí Linh Thạch: 2% linh thạch hiện có, tối thiểu 10
            lt_cost = max(10, int(linh_thach * 0.02 * (1 + cg_id * 0.1)))
            if linh_thach < lt_cost:
                return await ctx.send(
                    f"⚠️ Cần ít nhất **{lt_cost:,} Linh Thạch** để mở cổng bí cảnh! (Hiện có: {linh_thach:,})"
                )

            # Trừ chi phí
            await db.execute(
                "UPDATE players SET the_luc = the_luc - 5, linh_thach = linh_thach - ? WHERE user_id = ?",
                (lt_cost, user_id),
            )

            # --- TRÌNH DIỄN THÁM HIỂM ---
            exploration_msgs = [
                "🌀 Cổng bí cảnh mở toang, linh khí cuồn cuộn...",
                "🏜️ Bước vào không gian tĩnh mịch, vạn vật như ngưng đọng...",
                "🌌 Hư không rung chuyển, đạo hữu đi sâu vào lòng bí cảnh...",
            ]
            status_msg = await ctx.send(
                f"🚪 {ctx.author.mention} {random.choice(exploration_msgs)}"
            )
            await asyncio.sleep(1.5)

            # --- ROLL SỰ KIỆN ---
            event = self._roll_event()
            result_text = ""

            if event == "treasure":
                picked_grade = self._roll_grade(cg_id)
                c = await db.execute(
                    "SELECT item_id, ten_vat_pham FROM item_master WHERE pham_cap = ? ORDER BY RANDOM() LIMIT 1",
                    (picked_grade,),
                )
                item = await c.fetchone()
                if item:
                    item_id, item_ten = item
                    await db.execute(
                        "INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, ?, 1) ON CONFLICT(user_id, item_id) DO UPDATE SET so_luong = so_luong + 1",
                        (user_id, item_id),
                    )
                    grade_names = {
                        1: "Phàm",
                        2: "Linh",
                        3: "Tiên",
                        4: "Thần",
                        5: "Chí Tôn",
                    }
                    grade_emojis = {1: "⬜", 2: "🟢", 3: "🔵", 4: "🟣", 5: "🟡"}
                    result_text = (
                        f"🎁 **KHO BÁU!** Đạo hữu phát hiện một pháp bảo ẩn giấu!\n"
                        f"{grade_emojis[picked_grade]} Nhận được: **[{item_ten}]** — Phẩm cấp: `{grade_names[picked_grade]}`"
                    )
                else:
                    result_text = "🏜️ Bí cảnh trống rỗng, đạo hữu tay không trở về."

            elif event == "big_fortune":
                picked_grade = self._roll_grade(cg_id)
                # Buff thêm 1 bậc phẩm cấp cho Cơ Duyên Lớn (max 5)
                picked_grade = min(5, picked_grade + 1)
                c = await db.execute(
                    "SELECT item_id, ten_vat_pham FROM item_master WHERE pham_cap = ? ORDER BY RANDOM() LIMIT 1",
                    (picked_grade,),
                )
                item = await c.fetchone()
                bonus_tv = int(tu_vi * random.uniform(0.05, 0.15))
                bonus_cs = random.randint(50, 200) + int(
                    luc_chien * random.uniform(0.01, 0.03)
                )
                await db.execute(
                    "UPDATE players SET tu_vi = tu_vi + ?, luc_chien_goc = luc_chien_goc + ? WHERE user_id = ?",
                    (bonus_tv, bonus_cs, user_id),
                )
                if item:
                    item_id, item_ten = item
                    await db.execute(
                        "INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, ?, 1) ON CONFLICT(user_id, item_id) DO UPDATE SET so_luong = so_luong + 1",
                        (user_id, item_id),
                    )
                    result_text = (
                        f"🌟 **CƠ DUYÊN LỚN!** Thiên Đạo quyến cố đạo hữu!\n"
                        f"🎁 Nhận: **[{item_ten}]**\n"
                        f"✨ +**{bonus_tv:,}** Tu Vi | ⚔️ +**{bonus_cs:,}** Lực Chiến"
                    )
                else:
                    result_text = (
                        f"🌟 **CƠ DUYÊN LỚN!** Linh khí bí cảnh tẩy luyện toàn thân!\n"
                        f"✨ +**{bonus_tv:,}** Tu Vi | ⚔️ +**{bonus_cs:,}** Lực Chiến"
                    )

            elif event == "trap_tv":
                loss_pct = random.uniform(0.05, 0.15)
                loss_tv = int(tu_vi * loss_pct)
                await db.execute(
                    "UPDATE players SET tu_vi = max(0, tu_vi - ?) WHERE user_id = ?",
                    (loss_tv, user_id),
                )
                result_text = (
                    f"🪤 **BẪY TRẬN!** Đạo hữu lạc vào trận pháp cổ đại, linh khí bạo tán!\n"
                    f"📉 Mất: **-{loss_tv:,} Tu Vi** ({int(loss_pct*100)}%)"
                )

            elif event == "trap_cs":
                loss_pct = random.uniform(0.03, 0.10)
                loss_cs = int(luc_chien * loss_pct)
                await db.execute(
                    "UPDATE players SET luc_chien_goc = max(10, luc_chien_goc - ?) WHERE user_id = ?",
                    (loss_cs, user_id),
                )
                result_text = (
                    f"👹 **YÊU KHÍ XÂM THỰC!** Tà khí tràn ngập, xâm nhập kinh mạch!\n"
                    f"📉 Mất: **-{loss_cs:,} Lực Chiến** ({int(loss_pct*100)}%)"
                )

            elif event == "trap_item":
                inv_c = await db.execute(
                    "SELECT item_id, so_luong FROM inventory WHERE user_id = ? AND so_luong > 0 AND trang_thai != 'dang_trang_bi' ORDER BY RANDOM() LIMIT 1",
                    (user_id,),
                )
                dropped = await inv_c.fetchone()
                if dropped:
                    drop_id, _ = dropped
                    name_c = await db.execute(
                        "SELECT ten_vat_pham FROM item_master WHERE item_id = ?",
                        (drop_id,),
                    )
                    name_r = await name_c.fetchone()
                    drop_name = name_r[0] if name_r else "Vật phẩm"
                    await db.execute(
                        "UPDATE inventory SET so_luong = so_luong - 1 WHERE user_id = ? AND item_id = ?",
                        (user_id, drop_id),
                    )
                    await db.execute("DELETE FROM inventory WHERE so_luong <= 0")
                    result_text = (
                        f"💀 **CƯỚP ĐOẠT!** Bóng đen lướt qua, lục soát túi đồ!\n"
                        f"📦 Rơi mất: **{drop_name}** x1"
                    )
                else:
                    result_text = "💀 Bóng đen lướt qua nhưng túi đồ trống rỗng, đạo hữu may mắn thoát nạn."

            elif event == "npc":
                gold_bonus = int(lt_cost * random.uniform(3, 8))
                await db.execute(
                    "UPDATE players SET linh_thach = linh_thach + ? WHERE user_id = ?",
                    (gold_bonus, user_id),
                )
                npc_names = [
                    "Lão Nhân Bạch Phát",
                    "Tiên Tử Tuyết Liên",
                    "Ẩn Sĩ Hắc Bào",
                    "Thần Bí Đạo Nhân",
                ]
                result_text = (
                    f"🧙 **NPC BÍ ẨN!** {random.choice(npc_names)} tặng đạo hữu bảo vật!\n"
                    f"💰 Nhận: **+{gold_bonus:,} Linh Thạch**"
                )

            else:  # empty
                empty_msgs = [
                    "🏜️ Bí cảnh trống rỗng, đạo hữu tay không trở về.",
                    "🌫️ Sương mù dày đặc, không tìm thấy gì đáng giá.",
                    "🕳️ Lối đi bế tắc, đạo hữu buộc phải quay lại.",
                ]
                result_text = random.choice(empty_msgs)

            await db.commit()

        # Quest update ngoài DB context
        await self.bot.update_quest_progress(user_id, "bicanh", ctx)

        embed = discord.Embed(
            description=f"{ctx.author.mention}\n{result_text}",
            color=discord.Color.purple(),
        )
        embed.set_footer(text=f"💎 Chi phí: 5 Thể Lực + {lt_cost:,} Linh Thạch")
        await status_msg.edit(content=None, embed=embed)


async def setup(bot):
    await bot.add_cog(BiCanh(bot))
