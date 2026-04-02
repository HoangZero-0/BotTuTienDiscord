import discord
from discord.ext import commands
from utils import get_db


class BangXepHang(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"

    @commands.command(name="top")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def leaderboard(self, ctx, category: str = "tuvi"):
        """
        Xem bảng xếp hạng Thiên Đạo.
        Cú pháp: !top [tuvi | linhthach | lucchien | tongmon]
        """
        category = category.lower()
        valid_cats = ["tuvi", "linhthach", "lucchien", "tongmon"]
        if category not in valid_cats:
            return await ctx.send(
                f"❌ Loại bảng xếp hạng không hợp lệ! Hãy chọn: `{', '.join(valid_cats)}`"
            )

        user_id = str(ctx.author.id)

        async with get_db(self.db_path) as db:
            embed = discord.Embed(color=discord.Color.gold())

            if category == "tuvi":
                embed.title = "🏆 TOP CAO THỦ TU VI"
                query = """
                    SELECT p.user_id, r.ten_canh_gioi, p.tu_vi 
                    FROM players p JOIN realms_master r ON p.canh_gioi_id = r.canh_gioi_id 
                    ORDER BY p.canh_gioi_id DESC, p.tu_vi DESC, p.user_id ASC LIMIT 10
                """
                # Bonus: Lấy hạng của bản thân (Khớp hoàn toàn với ORDER BY trên)
                rank_query = """
                    SELECT COUNT(*) + 1 FROM players 
                    WHERE canh_gioi_id > (SELECT canh_gioi_id FROM players WHERE user_id = ?) 
                    OR (canh_gioi_id = (SELECT canh_gioi_id FROM players WHERE user_id = ?) 
                        AND tu_vi > (SELECT tu_vi FROM players WHERE user_id = ?))
                    OR (canh_gioi_id = (SELECT canh_gioi_id FROM players WHERE user_id = ?) 
                        AND tu_vi = (SELECT tu_vi FROM players WHERE user_id = ?)
                        AND user_id < ?)
                """
                rank_args = (user_id, user_id, user_id, user_id, user_id, user_id)

            elif category == "linhthach":
                embed.title = "💰 TOP ĐẠI GIA LINH THẠCH"
                query = "SELECT user_id, '', linh_thach FROM players ORDER BY linh_thach DESC, user_id ASC LIMIT 10"
                rank_query = """
                    SELECT COUNT(*) + 1 FROM players 
                    WHERE linh_thach > (SELECT linh_thach FROM players WHERE user_id = ?)
                    OR (linh_thach = (SELECT linh_thach FROM players WHERE user_id = ?) AND user_id < ?)
                """
                rank_args = (user_id, user_id, user_id)

            elif category == "lucchien":
                embed.title = "⚔️ TOP CHIẾN THẦN LỰC CHIẾN"
                # Tính tổng LC = gốc + buff trang bị
                query = """
                    SELECT p.user_id, '', 
                    (p.luc_chien_goc + (SELECT IFNULL(SUM(im.chi_so_buff), 0) FROM inventory i JOIN item_master im ON i.item_id = im.item_id WHERE i.user_id = p.user_id AND i.trang_thai = 'dang_trang_bi')) as total_lc
                    FROM players p ORDER BY total_lc DESC, p.user_id ASC LIMIT 10
                """
                rank_query = """
                    WITH total_scores AS (
                        SELECT user_id, (luc_chien_goc + (SELECT IFNULL(SUM(im.chi_so_buff), 0) FROM inventory i JOIN item_master im ON i.item_id = im.item_id WHERE i.user_id = p.user_id AND i.trang_thai = 'dang_trang_bi')) as val FROM players p
                    )
                    SELECT COUNT(*) + 1 FROM total_scores 
                    WHERE val > (SELECT val FROM total_scores WHERE user_id = ?)
                    OR (val = (SELECT val FROM total_scores WHERE user_id = ?) AND user_id < ?)
                """
                rank_args = (user_id, user_id, user_id)

            elif category == "tongmon":
                embed.title = "🏯 TOP TÔNG MÔN HÙNG MẠNH"
                query = "SELECT bang_chu_id, ten_tong_mon, linh_thach_quy FROM tong_mon ORDER BY linh_thach_quy DESC, tong_mon_id ASC LIMIT 10"
                # Hạng tông môn của user
                rank_query = """
                    SELECT COUNT(*) + 1 FROM tong_mon 
                    WHERE linh_thach_quy > (SELECT linh_thach_quy FROM tong_mon WHERE tong_mon_id = (SELECT tong_mon_id FROM players WHERE user_id = ?))
                    OR (linh_thach_quy = (SELECT linh_thach_quy FROM tong_mon WHERE tong_mon_id = (SELECT tong_mon_id FROM players WHERE user_id = ?))
                        AND tong_mon_id < (SELECT tong_mon_id FROM players WHERE user_id = ?))
                """
                rank_args = (user_id, user_id, user_id)

            # Thực thi query chính
            cursor = await db.execute(query)
            rows = await cursor.fetchall()

            # Lấy hạng của user
            my_rank_res = await db.execute(rank_query, rank_args)
            my_rank_row = await my_rank_res.fetchone()
            my_rank = my_rank_row[0] if my_rank_row else "N/A"

            # Xây dựng nội dung
            leader_list = []
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}

            for i, row in enumerate(rows, 1):
                raw_id, extra, value = row
                medal = medals.get(i, f"**{i}.**")

                # Fetch tên hiển thị
                if category == "tongmon":
                    name = f"**{extra}** (Chủ: <@{raw_id}>)"
                else:
                    try:
                        uid_int = int(raw_id)
                        user = self.bot.get_user(uid_int)
                        if not user:
                            try:
                                user = await self.bot.fetch_user(uid_int)
                            except:
                                user = None
                    except (ValueError, TypeError):
                        user = None

                    name = f"**{user.name}**" if user else f"*Ẩn sĩ #{str(raw_id)[:4]}*"

                # Format value
                val_str = f"{value:,}"
                suffix = (
                    " LT"
                    if category in ["linhthach", "tongmon"]
                    else (" TV" if category == "tuvi" else " LC")
                )
                info = f"`{extra}` " if extra and category == "tuvi" else ""

                leader_list.append(f"{medal} {name} - {info}**{val_str}**{suffix}")

            embed.description = "\n".join(leader_list) or "Chưa có ai trên bảng vàng."
            embed.set_footer(text=f"Thứ hạng của đạo hữu: #{my_rank}")
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(BangXepHang(bot))
