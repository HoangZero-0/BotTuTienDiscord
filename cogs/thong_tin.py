import discord
from discord.ext import commands
from utils import get_db, update_player_stats


class ThongTin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"

    @commands.command(name="me")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def profile(self, ctx):
        user_id = str(ctx.author.id)

        # 0. Cập nhật và lấy chỉ số HP/TL
        res = await update_player_stats(self.db_path, user_id)
        if not res:
            return await ctx.send(
                "❌ Đạo hữu chưa có danh tánh trong sổ Thiên Đạo. Hãy gõ `!tuluyen` trước!"
            )

        tl, sl, max_tl, max_sl = res

        async with get_db(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT p.tu_vi, p.luc_chien_goc, p.linh_thach, r.ten_canh_gioi, r.tu_vi_can_thiet, p.dao_hieu 
                FROM players p JOIN realms_master r ON p.canh_gioi_id = r.canh_gioi_id 
                WHERE p.user_id = ?""",
                (user_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return

            tv, cs, lt, ten_cg, tv_max, dao_hieu = row

            # Lấy LC từ trang bị
            cursor = await db.execute(
                """
                SELECT COALESCE(SUM(im.chi_so_buff), 0)
                FROM inventory i JOIN item_master im ON i.item_id = im.item_id
                WHERE i.user_id = ? AND i.trang_thai = 'dang_trang_bi'""",
                (user_id,),
            )
            buff_row = await cursor.fetchone()
            buff_cs = buff_row[0] if buff_row else 0
            total_cs = cs + buff_cs

            # Lấy thông tin Đạo Lữ
            dl_c = await db.execute(
                "SELECT dao_lu_id FROM players WHERE user_id = ?", (user_id,)
            )
            dl_r = await dl_c.fetchone()
            dao_lu_text = f"<@{dl_r[0]}>" if dl_r and dl_r[0] else "Chưa kết đôi"

            # Lấy thông tin Tông Môn
            tm_c = await db.execute(
                "SELECT tong_mon_id FROM players WHERE user_id = ?", (user_id,)
            )
            tm_r = await tm_c.fetchone()
            tong_mon_text = "Chưa gia nhập"
            if tm_r and tm_r[0]:
                tn_c = await db.execute(
                    "SELECT ten_tong_mon FROM tong_mon WHERE tong_mon_id = ?",
                    (tm_r[0],),
                )
                tn_r = await tn_c.fetchone()
                tong_mon_text = tn_r[0] if tn_r else "Không rõ"

            # --- TẠO THANH TIẾN ĐỘ ---
            def get_prog_bar(curr, mx, color="🟦"):
                if mx <= 0:
                    return "⬜" * 10
                perc = min(100, (curr / mx) * 100)
                filled = int(perc / 10)
                return (
                    "🟩" * filled + "⬜" * (10 - filled)
                    if color == "HP"
                    else (
                        "🟧" * filled + "⬜" * (10 - filled)
                        if color == "TL"
                        else "🟦" * filled + "⬜" * (10 - filled)
                    )
                )

            hp_bar = get_prog_bar(sl, max_sl, "HP")
            tl_bar = get_prog_bar(tl, max_tl, "TL")
            tv_bar = get_prog_bar(tv, tv_max)

            title_name = (
                f"📜 TU TIÊN DANH THIẾP: {dao_hieu if dao_hieu else ctx.author.name}"
            )
            embed = discord.Embed(title=title_name, color=discord.Color.gold())
            embed.set_thumbnail(url=ctx.author.display_avatar.url)

            embed.add_field(name="☯️ Cảnh Giới", value=f"**{ten_cg}**", inline=True)
            embed.add_field(name="💰 Linh Thạch", value=f"**{lt:,}**", inline=True)

            embed.add_field(
                name="🩸 Sinh Lực (HP)",
                value=f"`[{hp_bar}]` **{sl:,}/{max_sl:,}**",
                inline=False,
            )
            embed.add_field(
                name="⚡ Khí Lực (Thể Lực)",
                value=f"`[{tl_bar}]` **{tl}/{max_tl}**",
                inline=False,
            )

            embed.add_field(
                name="✨ Linh Khí (Tu Vi)",
                value=f"`[{tv_bar}]` **{tv:,}/{tv_max:,}**\n*(Đầy linh khí để đột phá)*",
                inline=False,
            )

            embed.add_field(
                name="⚔️ Thực Lực (Lực Chiến)",
                value=f"✨ Tổng: **{total_cs:,}**\n*(Gốc: {cs:,} | Trang bị: +{buff_cs:,})*",
                inline=False,
            )

            embed.add_field(name="💞 Đạo Lữ", value=dao_lu_text, inline=True)
            embed.add_field(name="🏯 Tông Môn", value=tong_mon_text, inline=True)

            embed.set_footer(
                text="Hệ Thống Bot Tu Tiên V4 | Gõ !tuido để xem hành trang"
            )
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ThongTin(bot))
