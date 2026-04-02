import discord
from discord.ext import commands
import random
from utils import get_db, update_player_stats


class DoSat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"

    @commands.command(name="dosat")
    @commands.cooldown(1, 600, commands.BucketType.user)  # 10 phút/lần
    async def dosat(self, ctx, target: discord.Member = None):
        if not target:
            return await ctx.send("❌ Đạo hữu muốn sát hại ai? Vui lòng tag @Người_đó!")
        if target == ctx.author:
            return await ctx.send("❌ Tự sát bị cấm trong giới tu tiên!")
        if target.bot:
            return await ctx.send("❌ Không thể đồ sát thực thể thiên đạo (Bot)!")

        attacker_id = str(ctx.author.id)
        target_id = str(target.id)

        # 1. Kiểm tra trạng thái Kẻ Tấn Công
        res_a = await update_player_stats(self.db_path, attacker_id)
        if not res_a:
            return await ctx.send("❌ Đạo hữu chưa bước vào con đường tu tiên, lấy gì mà đồ sát?")
        a_tl, a_sl, a_max_tl, a_max_sl = res_a

        if a_tl < 10:
            return await ctx.send("⚠️ Đạo hữu không đủ **10 Thể Lực** để phát động đồ sát!")
        if a_sl <= 0:
            return await ctx.send("💀 Ngài đang trọng thương, hãy an phận dưỡng thương!")

        # 2. Kiểm tra trạng thái Nạn Nhân
        res_t = await update_player_stats(self.db_path, target_id)
        if not res_t:
            return await ctx.send("❌ Kẻ đó chỉ là phàm nhân, tha cho hắn đi!")
        t_tl, t_sl, t_max_tl, t_max_sl = res_t

        if t_sl <= 0:
            return await ctx.send("💀 Kẻ đó đã trọng thương gục ngã rồi, ngài cứ thích hành xác người chết à?")

        # 3. Tiến hành Xử Lý Đồ Sát
        success = False
        try:
            async with get_db(self.db_path) as db:
                # Query thông tin chi tiết
                ca = await db.execute(
                    """
                    SELECT p.tu_vi, p.linh_thach, p.tong_mon_id, p.luc_chien_goc + COALESCE(SUM(im.chi_so_buff), 0)
                    FROM players p 
                    LEFT JOIN inventory i ON p.user_id = i.user_id AND i.trang_thai = 'dang_trang_bi'
                    LEFT JOIN item_master im ON i.item_id = im.item_id
                    WHERE p.user_id = ?
                    """, (attacker_id,)
                )
                ra = await ca.fetchone()
                
                ct = await db.execute(
                    """
                    SELECT p.tu_vi, p.linh_thach, p.tong_mon_id, p.luc_chien_goc + COALESCE(SUM(im.chi_so_buff), 0)
                    FROM players p 
                    LEFT JOIN inventory i ON p.user_id = i.user_id AND i.trang_thai = 'dang_trang_bi'
                    LEFT JOIN item_master im ON i.item_id = im.item_id
                    WHERE p.user_id = ?
                    """, (target_id,)
                )
                rt = await ct.fetchone()

                if not ra or not rt:
                    return await ctx.send("❌ Có lỗi xảy ra khi tra cứu sổ Sinh Tử!")

                a_tv, a_lt, a_tm_id, a_cp = ra
                t_tv, t_lt, t_tm_id, t_cp = rt

                # Check cùng tông môn
                if a_tm_id and t_tm_id and a_tm_id == t_tm_id:
                    return await ctx.send("❌ Pháp tắc Tông môn ghi rõ: **Không thể tàn sát đồng môn!**")

                # Trừ Thể Lực của người tấn công
                await db.execute("UPDATE players SET the_luc = max(0, the_luc - 10) WHERE user_id = ?", (attacker_id,))

                # Logic tính sát thương
                ratio = a_cp / max(1, t_cp)
                bounded_ratio = min(3.0, max(0.3, ratio))
                
                # ST Gây ra (15% -> 35% HP max của đich * scale Lực Chiến)
                dmg_to_t = int(t_max_sl * random.uniform(0.15, 0.35) * bounded_ratio)
                dmg_to_t = max(1, dmg_to_t)
                
                new_t_sl = t_sl - dmg_to_t

                embed = discord.Embed(title="⚔️ HUYẾT ÁN TU CHÂN", color=discord.Color.dark_red())

                if new_t_sl <= 0:
                    # Kẻ tấn công Giết thành công Nạn nhân
                    new_t_sl = 0
                    stolen_tv = int(t_tv * 0.10)
                    stolen_lt = int(t_lt * 0.10)
                    
                    await db.execute("UPDATE players SET sinh_luc = 0, tu_vi = max(0, tu_vi - ?), linh_thach = max(0, linh_thach - ?) WHERE user_id = ?", (stolen_tv, stolen_lt, target_id))
                    await db.execute("UPDATE players SET tu_vi = tu_vi + ?, linh_thach = linh_thach + ? WHERE user_id = ?", (stolen_tv, stolen_lt, attacker_id))
                    
                    embed.description = (
                        f"👺 **{ctx.author.mention}** đã tập kích tàn nhẫn và kết liễu thành công **{target.mention}** với **{dmg_to_t:,}** sát thương!\n\n"
                        f"☠️ Nạn nhân tắt thở, khí tức tan biến, rơi vào trạng thái trọng thương!\n"
                        f"💰 Ác nhân đắc ý lục soát thi thể và cướp được:\n"
                        f"🔹 **{stolen_tv:,} Tu Vi**\n"
                        f"🔹 **{stolen_lt:,} Linh Thạch**"
                    )
                else:
                    # Nạn nhân sống sót => Sinh ra phản đòn
                    counter_ratio = min(3.0, max(0.3, 1 / ratio))
                    dmg_to_a = int(a_max_sl * random.uniform(0.10, 0.25) * counter_ratio)
                    dmg_to_a = max(1, dmg_to_a)
                    new_a_sl = a_sl - dmg_to_a
                    
                    if new_a_sl <= 0:
                        # Kẻ tấn công bị phản đòn tới chết
                        new_a_sl = 0
                        # Nạn nhân tự vệ cướp lại 5% của Ác nhân
                        stolen_tv = int(a_tv * 0.05)
                        stolen_lt = int(a_lt * 0.05)
                        
                        await db.execute("UPDATE players SET sinh_luc = 0, tu_vi = max(0, tu_vi - ?), linh_thach = max(0, linh_thach - ?) WHERE user_id = ?", (stolen_tv, stolen_lt, attacker_id))
                        await db.execute("UPDATE players SET sinh_luc = ?, tu_vi = tu_vi + ?, linh_thach = linh_thach + ? WHERE user_id = ?", (new_t_sl, stolen_tv, stolen_lt, target_id))
                        
                        embed.description = (
                            f"💢 **{ctx.author.mention}** định tập kích lén **{target.mention}** nhưng tự đâm đầu vào chỗ chết (chỉ gây **{dmg_to_t:,} ST**)!\n"
                            f"🛡️ Nạn nhân phòng thủ vững vàng và bật phản công cực mạnh bồi trả **{dmg_to_a:,} sát thương** đánh bay đầu ác nhân!\n\n"
                            f"💀 **{ctx.author.mention}** gục ngã tại chỗ!\n"
                            f"💰 Nạn nhân tự vệ chính đáng và lột luôn túi trữ vật của kẻ xấu:\n"
                            f"🔹 **{stolen_tv:,} Tu Vi**\n"
                            f"🔹 **{stolen_lt:,} Linh Thạch**"
                        )
                    else:
                        # Cả 2 đều trọng thương sống sót
                        await db.execute("UPDATE players SET sinh_luc = ? WHERE user_id = ?", (new_a_sl, attacker_id))
                        await db.execute("UPDATE players SET sinh_luc = ? WHERE user_id = ?", (new_t_sl, target_id))
                        
                        # Function vẽ HP Bar cho đẹp
                        def get_hp_bar(current, mx):
                            perc = min(100, (current / max(1, mx)) * 100)
                            filled = int(perc / 10)
                            return "🟥" * filled + "⬜" * (10 - filled)
                        
                        bar_a = get_hp_bar(new_a_sl, a_max_sl)
                        bar_t = get_hp_bar(new_t_sl, t_max_sl)
                        
                        embed.color = discord.Color.orange()
                        embed.description = (
                            f"⚔️ **{ctx.author.mention}** lao đến đâm **{target.mention}** cướp bảo vật nhưng nạn nhân vẫn kiên cường trụ vững!\n\n"
                            f"🗡️ Sát thương gánh chịu: **-{dmg_to_t:,}**\n"
                            f"🛡️ Nạn nhân phản đòn: **-{dmg_to_a:,}**\n\n"
                            f"🔴 **{ctx.author.name}**: `{bar_a}` ({new_a_sl:,}/{a_max_sl:,} HP)\n"
                            f"🔵 **{target.name}**: `{bar_t}` ({new_t_sl:,}/{t_max_sl:,} HP)\n\n"
                            f"💨 Hai bên liếc nhau nảy lửa rồi ai nấy tự lui về vận công chữa thương."
                        )

                await db.commit()
                
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"🆘 Lỗi sự cố khi tàn sát: `{e}`")
            print(f"Error in dosat: {e}")


async def setup(bot):
    await bot.add_cog(DoSat(bot))
