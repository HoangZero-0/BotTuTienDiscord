import discord
from discord.ext import commands
import random
from utils import get_db
import asyncio


class TuLuyen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def tuluyen(self, ctx):
        user_id = str(ctx.author.id)

        async with get_db(self.db_path) as db:
            # 1. Lấy thông tin người chơi & Cảnh giới
            cursor = await db.execute(
                """
                SELECT p.canh_gioi_id, p.tu_vi, p.luc_chien_goc, p.the_luc, r.ten_canh_gioi, r.tu_vi_can_thiet 
                FROM players p JOIN realms_master r ON p.canh_gioi_id = r.canh_gioi_id 
                WHERE p.user_id = ?""",
                (user_id,),
            )
            row = await cursor.fetchone()

            if not row:
                await db.execute("INSERT INTO players (user_id) VALUES (?)", (user_id,))
                await db.commit()
                await ctx.send(
                    f"🌸 Chào mừng đạo hữu {ctx.author.mention} bước vào con đường tu tiên! Hãy gõ lại lệnh để bắt đầu."
                )
                return

            cg_id, current_tv, current_cs, the_luc, ten_cg, tv_max = row

            if the_luc < 5:
                await ctx.send(
                    "⚠️ Thể lực không đủ (cần 5). Hãy đợi hồi phục hoặc dùng đan dược!"
                )
                return

            # Check Dao Lu
            cursor_st = await db.execute(
                "SELECT dao_lu_id FROM players WHERE user_id = ?", (user_id,)
            )
            st_row = await cursor_st.fetchone()
            has_partner = bool(st_row and st_row[0])

            is_deviation = random.random() < 0.10

            if is_deviation:
                penalty_type = random.random()
                penalty_tv = 0
                penalty_cs = 0

                if penalty_type < 0.4:
                    # 40% TV only
                    penalty_tv = int(tv_max * random.uniform(0.05, 0.20))
                elif penalty_type < 0.8:
                    # 40% CS only
                    penalty_cs = int(current_cs * random.uniform(0.03, 0.15))
                else:
                    # 20% Both
                    penalty_tv = int(tv_max * random.uniform(0.05, 0.20))
                    penalty_cs = int(current_cs * random.uniform(0.03, 0.15))

                new_tv = current_tv - penalty_tv
                new_cs = max(10, current_cs - penalty_cs)
                new_the_luc = max(0, the_luc - 5)

                msg = f"💥 **TẨU HỎA NHẬP MA!** {ctx.author.mention} vận công sai mạch môn, tẩu hỏa nhập ma!\n"

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

                        # new_tv is negative, adding it subtracts from max
                        new_tv = new_tv_max + new_tv

                        msg += f"🚨 **NGHIỆP CHƯỚNG!** Đạo hữu tuột cảnh giới, bị giáng xuống **{new_ten_cg}**!\n"
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

                # Broadcast if de-level
                if current_cg < cg_id:
                    for guild in self.bot.guilds:
                        ch = self.get_event_channel(guild)
                        if ch:
                            embed = discord.Embed(
                                title="🚨 TIN BUỒN TU TIÊN",
                                description=f"Đạo hữu <@{user_id}> vừa bị tẩu hỏa nhập ma nghiêm trọng, tuộc cảnh giới xuống **{new_ten_cg}**!",
                                color=discord.Color.red(),
                            )
                            await ch.send(embed=embed)

                return await ctx.send(msg)

            else:
                status_msg = await ctx.send(
                    f"🧘 {ctx.author.mention} đang nhập định, cảm ứng linh khí đất trời..."
                )
                await asyncio.sleep(1.0)

                gain_tv_base = int(tv_max * random.uniform(0.01, 0.30))
                # x2 if partnered
                gain_tv = gain_tv_base * 2 if has_partner else gain_tv_base
                gain_tv = max(1, gain_tv)

                gain_cs = random.randint(5, 15) + int(
                    current_cs * random.uniform(0.01, 0.02)
                )

                new_tv = min(tv_max, current_tv + gain_tv)
                new_cs = current_cs + gain_cs
                new_the_luc = max(0, the_luc - 5)

                await db.execute(
                    "UPDATE players SET tu_vi = ?, luc_chien_goc = ?, the_luc = ? WHERE user_id = ?",
                    (new_tv, new_cs, new_the_luc, user_id),
                )
                await db.commit()

        # Update quest outside DB lock context
        await self.bot.update_quest_progress(user_id, "tuluyen", ctx)

        status = "🌟 **BÌNH CẢNH!**" if new_tv == tv_max else "📈 Đang tích lũy..."
        msg_txt = random.choice(
            [
                f"✨ Ngài vừa ngộ được chân lý mới, tu vi tăng mạnh!",
                f"🔋 Linh khí cuồn cuộn đổ vào đan điền.",
                f"🌅 Một ngày tu trì vất vả, tu vi có chút tinh tiến.",
            ]
        )

        emb = discord.Embed(
            description=f"{ctx.author.mention} {msg_txt}", color=discord.Color.green()
        )
        emb.add_field(
            name="Thông tin",
            value=f"✨ Linh Khí: +{new_tv - current_tv} (**{new_tv}/{tv_max}**) \n⚔️ Chỉ Số: +{gain_cs} (**{new_cs:,}**) \n🛡️ Cảnh Giới: `{ten_cg}` | {status}",
        )
        await status_msg.edit(content=None, embed=emb)

    def get_event_channel(self, guild):
        # CHỈ tìm kênh có tên 'Thế Giới Tu Chân'
        channel = discord.utils.get(guild.text_channels, name="thế-giới-tu-chân")

        # Nếu không tìm thấy kênh theo slug, thử tìm theo tên hiển thị
        if not channel:
            channel = next(
                (
                    x
                    for x in guild.text_channels
                    if x.name.replace("-", " ").lower() == "thế giới tu chân"
                ),
                None,
            )

        if channel and channel.permissions_for(guild.me).send_messages:
            return channel
        return None


async def setup(bot):
    await bot.add_cog(TuLuyen(bot))
