import discord
from discord.ext import commands
import random
from utils import get_db, update_player_stats
import asyncio
from datetime import date


class DaoHieuModal(discord.ui.Modal, title="Thiên Đạo Ghi Danh"):
    dao_hieu = discord.ui.TextInput(
        label="Nhập Đạo Hiệu của ngài:",
        placeholder="Ví dụ: Tử Linh, Tiêu Viêm...",
        min_length=2,
        max_length=20,
    )

    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        dh = self.dao_hieu.value.strip()
        async with get_db(self.db_path) as db:
            # Nếu chưa có thì insert, nếu có rồi thì update dao_hieu
            await db.execute(
                "INSERT INTO players (user_id, dao_hieu) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET dao_hieu = ?",
                (user_id, dh, dh),
            )
            await db.commit()
        await interaction.response.send_message(
            f"🌸 Kính chào **{dh}** - {interaction.user.mention} đã chính thức bước chân vào thế giới Tu Tiên!\n👉 Hãy gõ lại lệnh `!tuluyen` để bắt đầu hấp thụ linh khí."
        )


class DaoHieuView(discord.ui.View):
    def __init__(self, db_path):
        super().__init__(timeout=60)
        self.db_path = db_path

    @discord.ui.button(
        label="Bước Vào Đường Tu Tiên", style=discord.ButtonStyle.success, emoji="📜"
    )
    async def register_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(DaoHieuModal(self.db_path))


class TuLuyen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def tuluyen(self, ctx):
        user_id = str(ctx.author.id)
        # 1. Cập nhật và lấy chỉ số (HP/TL)
        res = await update_player_stats(self.db_path, user_id)
        if not res:
            view = DaoHieuView(self.db_path)
            await ctx.send(
                f"📜 {ctx.author.mention}, Thiên Đạo chưa thấy tên ngài trong sổ. Hãy ghi danh để bắt đầu!",
                view=view,
            )
            return

        tl, sl, max_tl, max_sl = res

        async with get_db(self.db_path) as db:
            # Lấy thông tin chi tiết
            cursor = await db.execute(
                """
                SELECT p.tu_vi, p.the_luc, r.ten_canh_gioi, 
                (SELECT tu_vi_can_thiet FROM realms_master WHERE canh_gioi_id = p.canh_gioi_id + 1) as tv_max, 
                p.dao_lu_id, p.canh_gioi_id, p.luc_chien_goc, p.dao_hieu
                FROM players p JOIN realms_master r ON p.canh_gioi_id = r.canh_gioi_id 
                WHERE p.user_id = ?""",
                (user_id,),
            )
            row = await cursor.fetchone()

            if not row:
                return

            (
                current_tv,
                current_tl,
                ten_cg,
                tv_max,
                dao_partner_id,
                cg_id,
                current_cs,
                dao_hieu,
            ) = row
            if tv_max is None or tv_max == 0:
                tv_max = 999_999_999  # Đỉnh phong

            dh_prefix = f"**{dao_hieu}** - " if dao_hieu else ""

            # Kiểm tra Thể lực (Cần ít nhất 2 để tu luyện)
            if tl < 2:
                # Nếu TL < 5, kiểm tra xem có dùng cơ chế cũ (TL < 2) không?
                # Ta thống nhất dùng chuẩn mới: Cần 5 TL.
                await ctx.send("⚠️ Thể lực không đủ (cần 5). Hãy đợi hồi phục!")
                return

            # Kiểm tra trạng thái sống còn
            if sl <= 0:
                await ctx.send(
                    "💀 Đạo hữu đang trọng thương, sinh lực cạn kiệt, không thể tu luyện! Hãy đợi hồi phục hoặc dùng linh đan."
                )
                return

            # Check Dao Lu (X2 Tu Vi)
            cursor_st = await db.execute(
                "SELECT dao_lu_id FROM players WHERE user_id = ?", (user_id,)
            )
            st_row = await cursor_st.fetchone()
            has_partner = bool(st_row and st_row[0])

            is_deviation = random.random() < 0.10  # 10% Tẩu hỏa nhập ma

            if is_deviation:
                penalty_type = random.random()
                penalty_tv = 0
                penalty_cs = 0

                if penalty_type < 0.4:
                    penalty_tv = int(tv_max * random.uniform(0.05, 0.20))
                elif penalty_type < 0.8:
                    penalty_cs = int(current_cs * random.uniform(0.03, 0.15))
                else:
                    penalty_tv = int(tv_max * random.uniform(0.05, 0.20))
                    penalty_cs = int(current_cs * random.uniform(0.03, 0.15))

                new_tv = current_tv - penalty_tv
                new_cs = max(10, current_cs - penalty_cs)
                new_the_luc = max(0, tl - 2)

                msg = f"💥 **TẨU HỎA NHẬP MA!** {dh_prefix}{ctx.author.mention} vận công sai mạch môn!\n"

                current_cg = cg_id
                if new_tv < 0:
                    if current_cg > 1:
                        current_cg -= 1
                        c_realm = await db.execute(
                            "SELECT tu_vi_can_thiet, ten_canh_gioi FROM realms_master WHERE canh_gioi_id = ?",
                            (current_cg,),
                        )
                        new_realm_data = await c_realm.fetchone()
                        new_tv_max, new_ten_cg = new_realm_data
                        new_tv = new_tv_max + new_tv
                        msg += f"🚨 **NGHIỆP CHƯỚNG!** Đạo hữu tuộc cảnh giới xuống **{new_ten_cg}**!\n"
                    else:
                        new_tv = 0
                        msg += "💨 Tu vi đã cạn kiệt, trở về tay trắng.\n"

                msg += f"📉 Tổn thất: "
                if penalty_tv > 0:
                    msg += f"**-{penalty_tv} Tu Vi** "
                if penalty_cs > 0:
                    msg += f"**-{penalty_cs} Lực Chiến**"

                await db.execute(
                    "UPDATE players SET canh_gioi_id = ?, tu_vi = ?, luc_chien_goc = ?, the_luc = ? WHERE user_id = ?",
                    (current_cg, new_tv, new_cs, new_the_luc, user_id),
                )
                await db.commit()
                return await ctx.send(msg)

            else:
                status_msg = await ctx.send(
                    f"🧘 {dh_prefix}{ctx.author.mention} đang nhập định, cảm ứng linh khí..."
                )
                await asyncio.sleep(1.0)

                # Tu vi nhận tỉ lệ thuận với cấp bậc (Bản đồ 66 cảnh giới)
                gain_tv_base = int(tv_max * random.uniform(0.02, 0.15))
                if random.random() < 0.05:  # 5% Đại cơ duyên
                    gain_tv_base = int(tv_max * random.uniform(0.3, 0.8))
                    await ctx.send(
                        f"🌟 **CƠ DUYÊN!** {dh_prefix}{ctx.author.mention} hấp thụ được linh khí tinh thuần!"
                    )

                gain_tv = gain_tv_base * 2 if has_partner else gain_tv_base
                gain_tv = max(1, gain_tv)

                gain_cs = random.randint(5, 15) + int(
                    current_cs * random.uniform(0.01, 0.02)
                )

                new_tv = min(tv_max, current_tv + gain_tv)
                new_cs = current_cs + gain_cs
                new_the_luc = max(0, tl - 2)  # Sử dụng 2 Thể lực

                await db.execute(
                    "UPDATE players SET tu_vi = ?, luc_chien_goc = ?, the_luc = ?, is_active = 1 WHERE user_id = ?",
                    (new_tv, new_cs, new_the_luc, user_id),
                )
                await db.commit()

        # Update quest progress
        await self.bot.update_quest_progress(user_id, "tuluyen", ctx)

        status = "🌟 **BÌNH CẢNH!**" if new_tv == tv_max else "📈 Đang tích lũy..."
        msg_txt = random.choice(
            [
                "✨ Tu vi tinh tiến!",
                "🔋 Linh khí dồi dào.",
                "🌅 Một ngày tu trì vất vả.",
            ]
        )

        emb = discord.Embed(
            description=f"{dh_prefix}{ctx.author.mention} {msg_txt}",
            color=discord.Color.green(),
        )
        emb.add_field(
            name="Thông tin",
            value=f"✨ Linh Khí: +{new_tv - current_tv} (**{new_tv}/{tv_max}**) \n⚔️ Chỉ Số: +{gain_cs} \n🛡️ Cảnh Giới: `{ten_cg}` | {status}",
        )
        await status_msg.edit(content=None, embed=emb)

    @commands.command(name="doituvi")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def doituvi(self, ctx, amount: int = None):
        if not amount or amount <= 0:
            return await ctx.send(
                "⚠️ Cú pháp: `!doituvi <số_linh_thạch>`\n(1 Linh Thạch = 10 Tu Vi)"
            )

        user_id = str(ctx.author.id)
        today = str(date.today())

        async with get_db(self.db_path) as db:
            cursor = await db.execute(
                "SELECT p.canh_gioi_id, p.tu_vi, p.linh_thach, r.tu_vi_can_thiet, p.dao_hieu FROM players p JOIN realms_master r ON p.canh_gioi_id = r.canh_gioi_id WHERE p.user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return await ctx.send("❌ Đạo hữu chưa ghi danh, hãy gõ `!tuluyen`.")

            cg_id, tv, lt, tv_max, dao_hieu = row
            dh_prefix = f"**{dao_hieu}** - " if dao_hieu else ""

            if lt < amount:
                return await ctx.send(f"⚠️ Linh thạch không đủ! (Đang có: {lt:,})")

            limit_per_day = cg_id * 1000

            # Kiểm tra giới hạn đổi
            cursor = await db.execute(
                "SELECT current_progress, last_completed_date FROM player_quests WHERE user_id = ? AND quest_id = 999",
                (user_id,),
            )
            q_row = await cursor.fetchone()
            used_today = q_row[0] if q_row and q_row[1] == today else 0

            if used_today + amount > limit_per_day:
                return await ctx.send(
                    f"🛑 Đã đạt giới hạn đổi trong ngày! (Còn lại: {limit_per_day - used_today:,})"
                )

            gain_tv = amount * 10
            new_tv = min(tv_max, tv + gain_tv)
            actual_gain = new_tv - tv

            if actual_gain <= 0:
                return await ctx.send("🌟 Linh khí đã đầy, hãy đột phá trước!")

            await db.execute(
                "UPDATE players SET linh_thach = linh_thach - ?, tu_vi = ? WHERE user_id = ?",
                (amount, new_tv, user_id),
            )

            new_used = used_today + amount
            await db.execute(
                "INSERT INTO player_quests (user_id, quest_id, current_progress, last_completed_date) VALUES (?, 999, ?, ?) ON CONFLICT(user_id, quest_id) DO UPDATE SET current_progress = ?, last_completed_date = ?",
                (user_id, new_used, today, new_used, today),
            )
            await db.commit()

            await ctx.send(
                f"💱 **ĐỔI CƠ DUYÊN THÀNH CÔNG**\n{dh_prefix}{ctx.author.mention} tiêu **{amount:,} LT** đổi **{actual_gain:,} TV**."
            )


async def setup(bot):
    await bot.add_cog(TuLuyen(bot))
