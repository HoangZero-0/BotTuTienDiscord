import discord
from discord.ext import commands
import random
from utils import get_db


class DoKiep(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"

    @commands.command(name="dotpha", aliases=["dokiep"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def dotpha(self, ctx):
        user_id = str(ctx.author.id)
        success = False
        try:
            async with get_db(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT p.canh_gioi_id, p.tu_vi, p.luc_chien_goc, 
                    (SELECT tu_vi_can_thiet FROM realms_master WHERE canh_gioi_id = p.canh_gioi_id + 1) as tv_max, 
                    r.ti_le_thanh_cong, r.ten_canh_gioi 
                    FROM players p JOIN realms_master r ON p.canh_gioi_id = r.canh_gioi_id 
                    WHERE p.user_id = ?""",
                    (user_id,),
                )
                row = await cursor.fetchone()

                if not row:
                    return await ctx.send(
                        "❌ Đạo hữu chưa có tên trong sổ Thiên Đạo! Hãy gõ `!tuluyen` trước."
                    )

                cg_id, tv, cs, tv_max, p_goc, ten_cg = row

                if tv < tv_max:
                    return await ctx.send(
                        f"❌ Linh khí chưa đầy (**{tv}/{tv_max}**), chưa thể đột phá!"
                    )

                # V3: Lực chiến chuẩn theo hàm nón chân thực (cg_id^1.35 * 100)
                cs_chuan = int(100 * (1.35**cg_id))

                # 1. TÍNH TỶ LỆ THƯỜNG TỪ NÉN TU VI/LỰC CHIẾN
                p_thuong = min(0.30, max(0, (cs - cs_chuan) / cs_chuan * 0.15))

                # 2. KIỂM TRA ĐAN DƯỢC HỖ TRỢ
                p_dan = 0
                dan_mapping = {
                    4: 103,  # Trúc Cơ
                    7: 105,  # Kết Đan
                    10: 107,  # Nguyên Anh
                    13: 109,  # Hóa Thần
                    16: 109,
                    19: 109,
                    22: 109,
                    25: 109,  # Phản Hư
                    28: 109,
                    31: 109,  # Đại Thừa
                    34: 109,
                    37: 109,  # Địa Tiên
                    40: 109,
                    43: 109,  # Thiên Tiên
                    46: 110,  # Tiên Quân (Cần Hoàn Hồn Đan)
                    49: 110,
                    52: 110,  # Tiên Đế
                    55: 110,
                    58: 110,  # Thần Quân
                    61: 110,
                    64: 110,  # Thần Đế (Đỉnh phong)
                }
                dan_id = dan_mapping.get(cg_id + 1)

                used_dan = False
                if dan_id:
                    c_dan = await db.execute(
                        "SELECT so_luong FROM inventory WHERE user_id = ? AND item_id = ?",
                        (user_id, dan_id),
                    )
                    res_dan = await c_dan.fetchone()
                    if res_dan and res_dan[0] > 0:
                        p_dan = 0.15 if dan_id != 109 else 0.20
                        used_dan = True

                # 3. KIỂM TRA BẢO VỆ
                has_protector = False
                c_prot = await db.execute(
                    "SELECT so_luong FROM inventory WHERE user_id = ? AND item_id = 110",
                    (user_id,),
                )
                res_prot = await c_prot.fetchone()
                if res_prot and res_prot[0] > 0:
                    has_protector = True

                p_tong = p_goc + p_thuong + p_dan
                p_loikiep = min(1.0, (cg_id / 66))
                co_loikiep = random.random() < p_loikiep
                success_roll = random.random() < p_tong

                embed = discord.Embed(
                    title="🌟 THIÊN ĐẠO ĐỘT PHÁ 🌟", color=discord.Color.gold()
                )

                if success_roll:
                    success = True
                    multiplier = 1.5 if co_loikiep else 1.1
                    new_cs = int(cs * multiplier)
                    import time

                    now = int(time.time())
                    await db.execute(
                        "UPDATE players SET canh_gioi_id = canh_gioi_id + 1, tu_vi = 0, luc_chien_goc = ?, the_luc = 120, sinh_luc = (canh_gioi_id + 1) * 100, last_the_luc_restore = ?, last_sinh_luc_restore = ? WHERE user_id = ?",
                        (new_cs, now, now, user_id),
                    )

                    msg = (
                        f"🎊 Chúc mừng đạo hữu ĐỘT PHÁ THÀNH CÔNG lên tầng cao mới! \n"
                    )
                    msg += f"🔥 Trạng thái: {'✅ Vượt qua Lôi Kiếp (+50% CS gốc)' if co_loikiep else '✅ Đột phá êm đềm (+10% CS gốc)'} \n"
                    if used_dan:
                        msg += f"🧪 Nhờ thần dược hỗ trợ, bình an vô sự (+{int(p_dan*100)}% tỷ lệ)\n"
                    msg += f"⚔️ Lực chiến nhảy vọt: **{new_cs:,}**"
                    embed.description = msg
                else:
                    success = False
                    msg = f"💀 ĐỘT PHÁ THẤT BẠI! \n"
                    if has_protector:
                        new_tv = int(tv * 0.9)
                        new_cs = cs
                        msg += "🛡️ May mắn thay, **Cửu Chuyển Hoàn Hồn Đan** đã phát huy tác dụng đoạt thiên địa tạo hóa, bảo toàn tính mạng và lực chiến cho đạo hữu!\n"
                        await db.execute(
                            "UPDATE inventory SET so_luong = so_luong - 1 WHERE user_id = ? AND item_id = 110",
                            (user_id,),
                        )
                    else:
                        penalty_tv = 0.8 if co_loikiep else 0.2
                        penalty_cs = 0.3 if co_loikiep else 0.1
                        new_tv = int(tv * (1 - penalty_tv))
                        new_cs = int(cs * (1 - penalty_cs))
                        msg += f"Trạng thái: {'⚡ BỊ LÔI KIẾP ĐÁNH TRỌNG THƯƠNG!' if co_loikiep else '💨 Linh khí bạo tán, mạch môn vỡ nát'}\n"
                        msg += f"📉 Tổn thất nặng nề: **-{int(penalty_tv*100)}%** Linh khí, **-{int(penalty_cs*100)}%** Lực chiến gốc."

                    await db.execute(
                        "UPDATE players SET tu_vi = ?, luc_chien_goc = ? WHERE user_id = ?",
                        (new_tv, new_cs, user_id),
                    )
                    embed.description = msg
                    embed.color = discord.Color.red()

                if used_dan:
                    await db.execute(
                        "UPDATE inventory SET so_luong = so_luong - 1 WHERE user_id = ? AND item_id = ?",
                        (user_id, dan_id),
                    )

                await db.execute("DELETE FROM inventory WHERE so_luong <= 0")
                await db.commit()
                await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"🆘 Lỗi Thiên Đạo khi đột phá: `{e}`")
            print(f"Error in dotpha: {e}")
            return

        # Vẫn gọi báo nhiệm vụ 'dokiep' để khớp với CSDL nhiệm vụ hiện hành
        if success:
            await self.bot.update_quest_progress(user_id, "dokiep", ctx)


async def setup(bot):
    await bot.add_cog(DoKiep(bot))
