import discord
from discord.ext import commands
from utils import CleanInt, CleanID, get_db
import asyncio


class GiaoDich(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"
        self.TAX_RATE = 0.10  # Thuế 10%

    # ==================== !chuyentien @user <amount> ====================
    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def chuyentien(self, ctx, target: discord.Member, amount: CleanInt):
        """Chuyển Linh Thạch cho đạo hữu khác (Phí 10%)."""
        if amount < 10:
            return await ctx.send("❌ Số lượng tối thiểu là 10 Linh Thạch!")
        if target.id == ctx.author.id:
            return await ctx.send("❌ Đạo hữu không thể tự chuyển cho chính mình!")
        if target.bot:
            return await ctx.send("❌ Không thể chuyển tiền cho hệ thống!")

        user_id = str(ctx.author.id)
        target_id = str(target.id)
        tax = int(amount * self.TAX_RATE)
        receive_amount = amount - tax

        async with get_db(self.db_path) as db:
            p = await db.execute(
                "SELECT linh_thach FROM players WHERE user_id = ?", (user_id,)
            )
            res = await p.fetchone()
            if not res or res[0] < amount:
                return await ctx.send("❌ Tài khoản đạo hữu không đủ Linh Thạch!")

            t = await db.execute(
                "SELECT user_id FROM players WHERE user_id = ?", (target_id,)
            )
            if not await t.fetchone():
                return await ctx.send(
                    f"❌ **{target.name}** chưa bước vào con đường tu tiên!"
                )

        # Xác nhận giao dịch
        msg = await ctx.send(
            f"💸 {ctx.author.mention} muốn chuyển **{amount:,} LT** cho {target.mention}?\n"
            f"⚠️ **Thuế Thiên Đạo (10%):** -{tax:,} LT\n"
            f"🎁 Người nhận thực tế: **{receive_amount:,} LT**\n"
            f"Bấm ✅ để xác nhận. (15 giây)"
        )
        await msg.add_reaction("✅")

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) == "✅"
                and reaction.message.id == msg.id
            )

        try:
            await self.bot.wait_for("reaction_add", timeout=15.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("⏰ Hết thời gian xác nhận, giao dịch đã hủy.")

        # Thực thi chuyển tiền
        async with get_db(self.db_path) as db:
            # Check lại số dư lần cuối
            p = await db.execute(
                "SELECT linh_thach FROM players WHERE user_id = ?", (user_id,)
            )
            res = await p.fetchone()
            if not res or res[0] < amount:
                return await ctx.send("❌ Tài khoản đạo hữu không còn đủ Linh Thạch!")

            await db.execute(
                "UPDATE players SET linh_thach = linh_thach - ? WHERE user_id = ?",
                (amount, user_id),
            )
            await db.execute(
                "UPDATE players SET linh_thach = linh_thach + ? WHERE user_id = ?",
                (receive_amount, target_id),
            )
            await db.commit()

        await self.bot.update_quest_progress(user_id, "chuyentien", ctx)
        await ctx.send(
            f"✅ Đã chuyển thành công! **{receive_amount:,} LT** đã về tay {target.mention} (Đã trừ thuế)."
        )

    # ==================== !giaodich @user <item_id> <amount> ====================
    @commands.command()
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def giaodich(
        self, ctx, target: discord.Member, item_id: CleanID, amount: CleanInt
    ):
        """Bán 1 vật phẩm cho người chơi khác với giá chỉ định."""
        if target.id == ctx.author.id:
            return await ctx.send("❌ Không thể tự mua bán với chính mình!")
        if amount < 0:
            return await ctx.send("❌ Số lượng Linh Thạch không hợp lệ!")

        user_id = str(ctx.author.id)
        target_id = str(target.id)

        async with get_db(self.db_path) as db:
            # Kiểm tra người bán có đồ
            ic = await db.execute(
                "SELECT i.so_luong, im.ten_vat_pham, i.trang_thai FROM inventory i JOIN item_master im ON i.item_id = im.item_id WHERE i.user_id = ? AND i.item_id = ?",
                (user_id, item_id),
            )
            item_res = await ic.fetchone()
            if not item_res or item_res[0] <= 0:
                return await ctx.send("❌ Đạo hữu không sở hữu vật phẩm này!")
            if item_res[2] == "dang_trang_bi":
                return await ctx.send(
                    "❌ Vật phẩm đang trang bị, hãy tháo ra trước khi bán!"
                )

            item_name = item_res[1]

            # Kiểm tra người mua tồn tại
            pc = await db.execute(
                "SELECT user_id FROM players WHERE user_id = ?", (target_id,)
            )
            if not await pc.fetchone():
                return await ctx.send(
                    f"❌ **{target.name}** chưa bước vào con đường tu tiên!"
                )

        tax = int(amount * self.TAX_RATE)
        actual_gain = amount - tax

        msg = await ctx.send(
            f"🤝 {target.mention}, đạo hữu **{ctx.author.name}** muốn bán: **[{item_name}]** (ID: {item_id})\n"
            f"💰 Giá: **{amount:,} Linh Thạch**\n"
            f"Bấm ✅ để Mua, ❌ để Từ chối. (30 giây)"
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
            return await ctx.send(f"⏰ {target.name} không đáp lại lời mời giao dịch.")

        if str(reaction.emoji) == "❌":
            return await ctx.send(f"❌ {target.name} đã từ chối giao dịch.")

        # Đồng ý mua -> Thực thi giao dịch
        async with get_db(self.db_path) as db:
            # Check lại số dư người mua
            mc = await db.execute(
                "SELECT linh_thach FROM players WHERE user_id = ?", (target_id,)
            )
            m_res = await mc.fetchone()
            if not m_res or m_res[0] < amount:
                return await ctx.send(
                    f"❌ {target.name} không đủ Linh Thạch để thực hiện giao dịch!"
                )

            # Check lại inventory người bán
            sc = await db.execute(
                "SELECT so_luong FROM inventory WHERE user_id = ? AND item_id = ? AND trang_thai != 'dang_trang_bi'",
                (user_id, item_id),
            )
            s_res = await sc.fetchone()
            if not s_res or s_res[0] <= 0:
                return await ctx.send(
                    "❌ Người bán đã không còn sở hữu vật phẩm này hoặc đã trang bị nó!"
                )

            # BẮT ĐẦU HOÁN ĐỔI
            # Trừ tiền người mua
            await db.execute(
                "UPDATE players SET linh_thach = linh_thach - ? WHERE user_id = ?",
                (amount, target_id),
            )
            # Cộng tiền người bán (có thuế)
            await db.execute(
                "UPDATE players SET linh_thach = linh_thach + ? WHERE user_id = ?",
                (actual_gain, user_id),
            )

            # Chuyển đồ
            # Trừ đồ người bán
            if s_res[0] > 1:
                await db.execute(
                    "UPDATE inventory SET so_luong = so_luong - 1 WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id),
                )
            else:
                await db.execute(
                    "DELETE FROM inventory WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id),
                )

            # Cộng đồ người mua
            await db.execute(
                "INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, ?, 1) ON CONFLICT(user_id, item_id) DO UPDATE SET so_luong = so_luong + 1",
                (target_id, item_id),
            )

            await db.commit()

        await ctx.send(
            f"✅ **Giao dịch thành công!**\n"
            f"📦 **{item_name}** -> {target.mention}\n"
            f"💰 **{amount:,} LT** -> {ctx.author.mention} (Đã trừ thuế {tax:,})"
        )

    # ==================== !ban <item_id> <price> ====================
    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def ban(self, ctx, item_id: CleanID, price: CleanInt):
        """Treo vật phẩm lên Chợ Đen (Marketplace) toàn server."""
        if price <= 0:
            return await ctx.send("❌ Giá bán phải lớn hơn 0!")

        user_id = str(ctx.author.id)
        async with get_db(self.db_path) as db:
            # Kiểm tra vật phẩm trong túi
            ic = await db.execute(
                "SELECT so_luong, trang_thai FROM inventory WHERE user_id = ? AND item_id = ?",
                (user_id, item_id),
            )
            res = await ic.fetchone()
            if not res or res[0] <= 0:
                return await ctx.send("❌ Đạo hữu không sở hữu vật phẩm này!")
            if res[1] == "dang_trang_bi":
                return await ctx.send(
                    "❌ Vật phẩm đang trang bị, hãy tháo ra trước khi bán!"
                )

            # Lấy tên vật phẩm
            nc = await db.execute(
                "SELECT ten_vat_pham FROM item_master WHERE item_id = ?", (item_id,)
            )
            nr = await nc.fetchone()
            item_name = nr[0] if nr else f"ID: {item_id}"

            # Treo lên chợ (Hết hạn sau 24h)
            from datetime import datetime, timedelta

            expiry = datetime.now() + timedelta(hours=24)

            await db.execute(
                "INSERT INTO market_listings (seller_id, item_id, so_luong, gia_ban, thoi_gian_het_han) VALUES (?, ?, 1, ?, ?)",
                (user_id, item_id, price, expiry),
            )

            # Trừ 1 món từ túi
            if res[0] > 1:
                await db.execute(
                    "UPDATE inventory SET so_luong = so_luong - 1 WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id),
                )
            else:
                await db.execute(
                    "DELETE FROM inventory WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id),
                )

            await db.commit()

        await ctx.send(
            f"📦 **{ctx.author.name}** đã treo thành công **[{item_name}]** lên Chợ Đen với giá **{price:,} LT**!"
        )

    # ==================== !choden ====================
    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def choden(self, ctx):
        """Xem danh sách các vật phẩm đang được treo bán."""
        async with get_db(self.db_path) as db:
            # Chỉ lấy các listing chưa hết hạn
            cursor = await db.execute(
                """
                SELECT m.listing_id, im.ten_vat_pham, m.gia_ban, m.seller_id, m.item_id
                FROM market_listings m JOIN item_master im ON m.item_id = im.item_id
                WHERE m.thoi_gian_het_han > datetime('now')
                ORDER BY m.listing_id DESC LIMIT 10
                """
            )
            listings = await cursor.fetchall()

        if not listings:
            return await ctx.send(
                "🏪 Chợ Đen hiện đang vắng lặng, không có ai treo đồ."
            )

        embed = discord.Embed(
            title="🏪 CHỢ ĐEN TOÀN SERVER", color=discord.Color.dark_gray()
        )
        desc = ""
        for l_id, name, price, seller_id, i_id in listings:
            desc += f"`#{l_id}` **{name}** (ID:{i_id}) — 💰 **{price:,} LT** — Người bán: <@{seller_id}>\n"

        embed.description = desc
        embed.set_footer(
            text="Dùng !giaodich @nguoi_ban <ID> <Giá> để mua trực tiếp hoặc đợi hệ thống cập nhật Buy-Back."
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(GiaoDich(bot))
