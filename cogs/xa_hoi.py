import discord
from discord.ext import commands
from utils import get_db
import random
import asyncio


class XaHoi(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"

    # ==================== !songtu @user ====================
    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def songtu(self, ctx, target: discord.Member):
        """Kết đôi Đạo Lữ — Cần đối phương đồng ý."""
        if target == ctx.author:
            return await ctx.send("❌ Không thể tự kết đôi với chính mình!")
        if target.bot:
            return await ctx.send("❌ Không thể kết đôi với linh thú máy!")

        user_id = str(ctx.author.id)
        partner_id = str(target.id)

        async with get_db(self.db_path) as db:
            # Kiểm tra cả 2 đều có trong hệ thống
            c1 = await db.execute(
                "SELECT dao_lu_id FROM players WHERE user_id = ?", (user_id,)
            )
            c2 = await db.execute(
                "SELECT dao_lu_id FROM players WHERE user_id = ?", (partner_id,)
            )
            r1, r2 = await c1.fetchone(), await c2.fetchone()

            if not r1:
                return await ctx.send("❌ Đạo hữu chưa có tên trong sổ Thiên Đạo!")
            if not r2:
                return await ctx.send(
                    f"❌ **{target.name}** chưa bước vào con đường tu tiên!"
                )
            if r1[0]:
                return await ctx.send(
                    "❌ Đạo hữu đã có Đạo Lữ rồi! Hãy `!lithu` trước."
                )
            if r2[0]:
                return await ctx.send(f"❌ **{target.name}** đã có Đạo Lữ rồi!")

        # Gửi lời mời và chờ phản ứng
        msg = await ctx.send(
            f"💞 {target.mention}, đạo hữu **{ctx.author.name}** muốn kết đôi Song Tu với ngài!\n"
            f"Bấm ✅ để đồng ý, ❌ để từ chối. (30 giây)"
        )
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        def check(reaction, user):
            return (
                user == target
                and str(reaction.emoji) in ["✅", "❌"]
                and reaction.message.id == msg.id
            )

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add", timeout=30.0, check=check
            )
        except asyncio.TimeoutError:
            return await ctx.send(
                f"⏰ {target.name} không phản hồi, lời mời Song Tu đã hết hạn."
            )

        if str(reaction.emoji) == "❌":
            return await ctx.send(f"💔 {target.name} đã từ chối lời mời Song Tu.")

        # Đồng ý → Kết đôi
        async with get_db(self.db_path) as db:
            # Kiểm tra lại lần cuối để tránh race condition (kết đôi cùng lúc)
            c_check = await db.execute(
                "SELECT dao_lu_id FROM players WHERE user_id IN (?, ?)",
                (user_id, partner_id),
            )
            rows = await c_check.fetchall()
            for r in rows:
                if r[0]:
                    return await ctx.send(
                        "❌ Đã xảy ra biến cố! Một trong hai người đã có Đạo Lữ trong lúc chờ đợi."
                    )

            await db.execute(
                "UPDATE players SET dao_lu_id = ? WHERE user_id = ?",
                (partner_id, user_id),
            )
            await db.execute(
                "UPDATE players SET dao_lu_id = ? WHERE user_id = ?",
                (user_id, partner_id),
            )
            await db.commit()

        quotes = [
            f"💞 Chúc mừng {ctx.author.mention} và {target.mention} đã kết thành Đạo Lữ! Tu Vi x2 khi tu luyện!",
            f"🌹 Dây tơ hồng đã thắt! {ctx.author.mention} và {target.mention} từ nay cùng nhau tu luyện.",
            f"🎆 Pháo hoa rực trời! Chúc mối lương duyên bền lâu hơn cả thọ nguyên chân tiên!",
        ]
        await ctx.send(random.choice(quotes))

    # ==================== !lithu ====================
    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def lithu(self, ctx):
        """Hủy kết đôi Đạo Lữ."""
        user_id = str(ctx.author.id)
        async with get_db(self.db_path) as db:
            c = await db.execute(
                "SELECT dao_lu_id FROM players WHERE user_id = ?", (user_id,)
            )
            row = await c.fetchone()
            if not row or not row[0]:
                return await ctx.send("❌ Đạo hữu chưa có Đạo Lữ nào.")

            partner_id = row[0]
            await db.execute(
                "UPDATE players SET dao_lu_id = NULL WHERE user_id = ?", (user_id,)
            )
            await db.execute(
                "UPDATE players SET dao_lu_id = NULL WHERE user_id = ?", (partner_id,)
            )
            await db.commit()

        await ctx.send(
            f"💔 {ctx.author.mention} đã cắt đứt dây tơ hồng. Đạo Lữ đã ly khai!"
        )

    # ==================== !lapphai <tên> ====================
    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def lapphai(self, ctx, *, ten_phai: str):
        """Lập Tông Môn — Tốn 50,000 Linh Thạch."""
        user_id = str(ctx.author.id)
        async with get_db(self.db_path) as db:
            p = await db.execute(
                "SELECT linh_thach, tong_mon_id FROM players WHERE user_id = ?",
                (user_id,),
            )
            res = await p.fetchone()
            if not res:
                return await ctx.send("❌ Đạo hữu chưa có tên trong sổ Thiên Đạo!")
            lt, tm_id = res

            if tm_id:
                return await ctx.send("❌ Đạo hữu đã có tông môn rồi!")
            if lt < 50000:
                return await ctx.send(
                    "❌ Không đủ **50,000** Linh Thạch để lập tông môn."
                )

            await db.execute(
                "INSERT INTO tong_mon (ten_tong_mon, bang_chu_id) VALUES (?, ?)",
                (ten_phai, user_id),
            )
            await db.execute(
                "UPDATE players SET linh_thach = linh_thach - 50000, tong_mon_id = last_insert_rowid() WHERE user_id = ?",
                (user_id,),
            )
            await db.commit()
            await ctx.send(f"🎊 Chúc mừng **{ten_phai}** chính thức khai môn lập phái!")

    # ==================== !moiphai @user ====================
    @commands.command()
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def moiphai(self, ctx, target: discord.Member):
        """Mời người chơi vào Tông Môn."""
        if target.bot:
            return await ctx.send("❌ Không thể mời linh thú máy vào môn phái!")

        user_id = str(ctx.author.id)
        target_id = str(target.id)

        async with get_db(self.db_path) as db:
            # Kiểm tra người mời là bang chủ
            c = await db.execute(
                "SELECT tong_mon_id FROM players WHERE user_id = ?", (user_id,)
            )
            r = await c.fetchone()
            if not r or not r[0]:
                return await ctx.send("❌ Đạo hữu chưa có tông môn!")

            tm_id = r[0]
            bc = await db.execute(
                "SELECT bang_chu_id, ten_tong_mon FROM tong_mon WHERE tong_mon_id = ?",
                (tm_id,),
            )
            br = await bc.fetchone()
            if not br or br[0] != user_id:
                return await ctx.send("❌ Chỉ Bang Chủ mới có quyền mời người!")

            ten_tm = br[1]

            # Kiểm tra target chưa có tông môn
            tc = await db.execute(
                "SELECT tong_mon_id FROM players WHERE user_id = ?", (target_id,)
            )
            tr = await tc.fetchone()
            if not tr:
                return await ctx.send(
                    f"❌ **{target.name}** chưa bước vào con đường tu tiên!"
                )
            if tr[0]:
                return await ctx.send(f"❌ **{target.name}** đã có tông môn rồi!")

        # Gửi lời mời
        msg = await ctx.send(
            f"🏯 {target.mention}, Bang Chủ **{ctx.author.name}** mời ngài gia nhập **{ten_tm}**!\n"
            f"Bấm ✅ để đồng ý, ❌ để từ chối. (30 giây)"
        )
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        def check(reaction, user):
            return (
                user == target
                and str(reaction.emoji) in ["✅", "❌"]
                and reaction.message.id == msg.id
            )

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add", timeout=30.0, check=check
            )
        except asyncio.TimeoutError:
            return await ctx.send(f"⏰ {target.name} không phản hồi, lời mời hết hạn.")

        if str(reaction.emoji) == "❌":
            return await ctx.send(f"❌ {target.name} đã từ chối lời mời.")

        async with get_db(self.db_path) as db:
            # Kiểm tra lại lần cuối
            tc = await db.execute(
                "SELECT tong_mon_id FROM players WHERE user_id = ?", (target_id,)
            )
            tr = await tc.fetchone()
            if tr and tr[0]:
                return await ctx.send(
                    f"❌ **{target.name}** đã gia nhập tông môn khác trong lúc chờ!"
                )

            await db.execute(
                "UPDATE players SET tong_mon_id = ? WHERE user_id = ?",
                (tm_id, target_id),
            )
            await db.commit()
        await ctx.send(f"🎊 **{target.name}** chính thức gia nhập **{ten_tm}**!")

    # ==================== !roiphai ====================
    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def roiphai(self, ctx):
        """Rời khỏi Tông Môn hiện tại."""
        user_id = str(ctx.author.id)
        async with get_db(self.db_path) as db:
            c = await db.execute(
                "SELECT tong_mon_id FROM players WHERE user_id = ?", (user_id,)
            )
            r = await c.fetchone()
            if not r or not r[0]:
                return await ctx.send("❌ Đạo hữu chưa gia nhập tông môn nào.")

            # Kiểm tra có phải bang chủ không
            bc = await db.execute(
                "SELECT bang_chu_id FROM tong_mon WHERE tong_mon_id = ?", (r[0],)
            )
            br = await bc.fetchone()
            if br and br[0] == user_id:
                return await ctx.send(
                    "❌ Bang Chủ không thể rời môn phái! Hãy giải tán hoặc chuyển quyền trước."
                )

            await db.execute(
                "UPDATE players SET tong_mon_id = NULL WHERE user_id = ?", (user_id,)
            )
            await db.commit()
        await ctx.send(f"🚪 {ctx.author.mention} đã rời khỏi tông môn.")

    # ==================== !xemphai ====================
    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def xemphai(self, ctx):
        """Xem thông tin Tông Môn hiện tại."""
        user_id = str(ctx.author.id)
        async with get_db(self.db_path) as db:
            c = await db.execute(
                "SELECT tong_mon_id FROM players WHERE user_id = ?", (user_id,)
            )
            r = await c.fetchone()
            if not r or not r[0]:
                return await ctx.send("❌ Đạo hữu chưa gia nhập tông môn nào.")

            tm_id = r[0]
            tc = await db.execute(
                "SELECT ten_tong_mon, bang_chu_id FROM tong_mon WHERE tong_mon_id = ?",
                (tm_id,),
            )
            tr = await tc.fetchone()
            if not tr:
                return await ctx.send("❌ Tông môn không tồn tại.")

            ten_tm, bc_id = tr

            # Đếm thành viên
            mc = await db.execute(
                "SELECT COUNT(*) FROM players WHERE tong_mon_id = ?", (tm_id,)
            )
            mr = await mc.fetchone()
            member_count = mr[0] if mr else 0

            # Danh sách thành viên (tối đa 10)
            lc = await db.execute(
                "SELECT user_id FROM players WHERE tong_mon_id = ? LIMIT 10", (tm_id,)
            )
            members = await lc.fetchall()
            member_list = []
            for (mid,) in members:
                tag = "👑" if mid == bc_id else "👤"
                member_list.append(f"{tag} <@{mid}>")

            embed = discord.Embed(
                title=f"🏯 {ten_tm}",
                color=discord.Color.dark_gold(),
            )
            embed.add_field(name="👑 Bang Chủ", value=f"<@{bc_id}>", inline=True)
            embed.add_field(name="👥 Thành Viên", value=str(member_count), inline=True)
            embed.add_field(
                name="📋 Danh Sách",
                value="\n".join(member_list) or "Trống",
                inline=False,
            )
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(XaHoi(bot))
