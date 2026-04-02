import discord
from discord.ext import commands, tasks
import aiosqlite
import asyncio
import random
from datetime import datetime, timedelta
from utils import CleanID, CleanInt, get_db


class DauGia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"
        self.TAX_RATE = 0.10  # Thuế Thiên Đạo 10%
        self.MIN_BID_INCREMENT = 0.05  # Bước giá tối thiểu 5%

        self.auction_manager.start()
        self.system_auction_spawner.start()

    def cog_unload(self):
        self.auction_manager.cancel()
        self.system_auction_spawner.cancel()

    # --- AUTO FIX DB SCHEMA ---
    async def cog_load(self):
        async with get_db(self.db_path) as db:
            # Thêm cột buyout_price nếu chưa có
            try:
                await db.execute(
                    "ALTER TABLE auctions ADD COLUMN buyout_price INTEGER DEFAULT 0"
                )
                await db.commit()
            except:
                pass

    @tasks.loop(minutes=10)
    async def auction_manager(self):
        """Tự động kiểm tra và kết thúc đấu giá"""
        async with get_db(self.db_path) as db:
            now = datetime.now()
            cursor = await db.execute(
                "SELECT auction_id, seller_id, item_id, so_luong, current_bid, highest_bidder_id FROM auctions WHERE end_time <= ?",
                (now,),
            )
            expired = await cursor.fetchall()

            for a_id, seller, item_id, qty, bid, winner in expired:
                msg = ""
                # Phí giao dịch (chỉ áp dụng cho người chơi bán)
                tax = int(bid * self.TAX_RATE)
                gain = bid - tax

                if winner:
                    # Trao đồ cho người thắng
                    await db.execute(
                        "INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, ?, ?) ON CONFLICT(user_id, item_id) DO UPDATE SET so_luong = so_luong + ?",
                        (winner, item_id, qty, qty),
                    )
                    # Gửi tiền cho người bán
                    if seller != "0":
                        await db.execute(
                            "UPDATE players SET linh_thach = linh_thach + ? WHERE user_id = ?",
                            (gain, seller),
                        )
                        tax_info = f" (Đã trừ {tax:,} LT thuế)"
                    else:
                        tax_info = ""

                    msg = f"⚖️ **KẾT THÚC ĐẤU GIÁ**: <@{winner}> đã chiến thắng vật phẩm **ID {item_id}** với giá **{bid:,} LT**!{tax_info}"
                else:
                    # Trả lại đồ cho người bán (nếu là người chơi)
                    if seller != "0":
                        await db.execute(
                            "INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, ?, ?) ON CONFLICT(user_id, item_id) DO UPDATE SET so_luong = so_luong + ?",
                            (seller, item_id, qty, qty),
                        )
                    msg = f"⚖️ **KẾT THÚC ĐẤU GIÁ**: Phiên #**{a_id}** đã trôi qua mà không có ai thầu."

                # Thông báo toàn server
                for guild in self.bot.guilds:
                    ch = self.get_event_channel(guild)
                    if ch:
                        await ch.send(msg)

                await db.execute("DELETE FROM auctions WHERE auction_id = ?", (a_id,))

            await db.commit()

    @tasks.loop(minutes=1)
    async def system_auction_spawner(self):
        """Thiên Đạo giáng hạ bảo vật (Hệ thống đấu giá)"""
        async with get_db(self.db_path) as db:
            c = await db.execute("SELECT COUNT(*) FROM auctions WHERE seller_id = '0'")
            if (await c.fetchone())[0] > 0:
                return  # Chỉ 1 phiên hệ thống 1 lúc

            cursor = await db.execute(
                "SELECT item_id, ten_vat_pham, pham_cap FROM item_master ORDER BY RANDOM() LIMIT 1"
            )
            item = await cursor.fetchone()
            if not item:
                return

            i_id, i_name, i_pham = item
            starting_bid = (i_pham**3) * 500 + random.randint(100, 1000)
            buyout = starting_bid * 5  # Giá mua đứt hệ thống x5 lần khởi điểm
            end_time = datetime.now() + timedelta(minutes=15)

            await db.execute(
                "INSERT INTO auctions (seller_id, item_id, so_luong, current_bid, buyout_price, end_time) VALUES (?, ?, 1, ?, ?, ?)",
                ("0", i_id, starting_bid, buyout, end_time),
            )
            await db.commit()

            for guild in self.bot.guilds:
                ch = self.get_event_channel(guild)
                if ch:
                    embed = discord.Embed(
                        title="⚖️ ĐẤU GIÁ THIÊN ĐẠO", color=discord.Color.gold()
                    )
                    embed.description = (
                        f"✨ Một món bảo vật thượng giới vừa xuất hiện!\n\n"
                        f"📦 Vật phẩm: **{i_name}** [ID: {i_id}]\n"
                        f"💰 Khởi điểm: **{starting_bid:,} LT**\n"
                        f"⚡ Mua đứt: **{buyout:,} LT**\n"
                        f"⏳ Thời gian: **15 phút**"
                    )
                    await ch.send(embed=embed)

    @commands.command(name="daugia")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def start_auction(
        self,
        ctx,
        item_id: CleanID,
        starting_bid: CleanInt,
        buyout_price: CleanInt = 0,
        hours: int = 1,
    ):
        """Treo đấu giá vật phẩm. !daugia <id> <khởi_điểm> [mua_đứt] [giờ]"""
        if hours < 1 or hours > 48:
            return await ctx.send("❌ Thời gian từ 1-48 giờ.")
        if starting_bid < 100:
            return await ctx.send("❌ Giá khởi điểm > 100 LT.")
        if buyout_price > 0 and buyout_price <= starting_bid:
            return await ctx.send("❌ Giá mua đứt phải cao hơn giá khởi điểm!")

        user_id = str(ctx.author.id)
        async with get_db(self.db_path) as db:
            cursor = await db.execute(
                "SELECT so_luong, im.ten_vat_pham FROM inventory i JOIN item_master im ON i.item_id = im.item_id WHERE i.user_id = ? AND i.item_id = ? AND i.trang_thai != 'dang_trang_bi'",
                (user_id, item_id),
            )
            item = await cursor.fetchone()
            if not item:
                return await ctx.send(
                    "❌ Đạo hữu không có vật phẩm này hoặc đang trang bị nó!"
                )

            end_time = datetime.now() + timedelta(hours=hours)
            await db.execute(
                "INSERT INTO auctions (seller_id, item_id, so_luong, current_bid, buyout_price, end_time) VALUES (?, ?, 1, ?, ?, ?)",
                (user_id, item_id, starting_bid, buyout_price, end_time),
            )
            # Trừ đồ
            if item[0] > 1:
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
            buyout_txt = (
                f" | ⚡ Mua đứt: **{buyout_price:,} LT**" if buyout_price > 0 else ""
            )
            await ctx.send(
                f"✅ Đã treo **{item[1]}** đấu giá. Khởi điểm: **{starting_bid:,} LT**{buyout_txt}. Hạn: {hours}h."
            )

    @commands.command(name="bid")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def place_bid(self, ctx, auction_id: CleanID, amount: CleanInt):
        """Đặt thầu hoặc Mua đứt. !bid <phiên> <số_tiền>"""
        user_id = str(ctx.author.id)
        async with get_db(self.db_path) as db:
            cursor = await db.execute(
                "SELECT current_bid, seller_id, end_time, highest_bidder_id, buyout_price, item_id FROM auctions WHERE auction_id = ?",
                (auction_id,),
            )
            auc = await cursor.fetchone()
            if not auc:
                return await ctx.send("❌ Phiên này không tồn tại!")

            curr_bid, seller, end_t_str, last_bidder, buyout, item_id = auc
            end_time = datetime.strptime(
                str(end_t_str).split(".")[0], "%Y-%m-%d %H:%M:%S"
            )

            if user_id == seller:
                return await ctx.send("❌ Không thể tự đấu giá đồ của mình!")

            # Check bước giá (5%)
            min_next = int(curr_bid * (1 + self.MIN_BID_INCREMENT))
            if amount < min_next and (buyout == 0 or amount < buyout):
                return await ctx.send(
                    f"❌ Bước giá tối thiểu 5%! Đạo hữu phải đặt ít nhất **{min_next:,} LT**."
                )

            # Check Tài khoản
            p = await db.execute(
                "SELECT linh_thach FROM players WHERE user_id = ?", (user_id,)
            )
            if (await p.fetchone())[0] < amount:
                return await ctx.send("❌ Không đủ Linh Thạch!")

            # --- XỬ LÝ MUA ĐỨT ---
            if buyout > 0 and amount >= buyout:
                # Xóa phiên đấu giá ngay lập tức để tránh người khác thầu cùng lúc
                cursor = await db.execute(
                    "DELETE FROM auctions WHERE auction_id = ? AND buyout_price = ?",
                    (auction_id, buyout),
                )
                if cursor.rowcount == 0:
                    return await ctx.send(
                        "❌ Phiên đấu giá này đã kết thúc hoặc có biến động, hãy thử lại!"
                    )

                # Trả tiền cho bidder cũ
                if last_bidder:
                    await db.execute(
                        "UPDATE players SET linh_thach = linh_thach + ? WHERE user_id = ?",
                        (curr_bid, last_bidder),
                    )

                # Trừ tiền người mua
                await db.execute(
                    "UPDATE players SET linh_thach = linh_thach - ? WHERE user_id = ?",
                    (buyout, user_id),
                )

                # Trao đồ ngay
                await db.execute(
                    "INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, ?, 1) ON CONFLICT(user_id, item_id) DO UPDATE SET so_luong = so_luong + 1",
                    (user_id, item_id),
                )

                # Giao tiền cho người bán (trừ thuế)
                gain = int(buyout * (1 - self.TAX_RATE)) if seller != "0" else buyout
                if seller != "0":
                    await db.execute(
                        "UPDATE players SET linh_thach = linh_thach + ? WHERE user_id = ?",
                        (gain, seller),
                    )

                await db.commit()
                return await ctx.send(
                    f"⚡ **MUA ĐỨT THÀNH CÔNG!** Đạo hữu đã chốt vật phẩm với giá **{buyout:,} LT**!"
                )

            # --- ĐẶT THẦU BÌNH THƯỜNG ---
            # Sử dụng Update Atomic để tránh race condition
            # CHỐNG SNIPING: Nếu còn < 2 phút, cộng thêm 2 phút
            new_end_time = end_time
            if (end_time - datetime.now()).total_seconds() < 120:
                new_end_time = datetime.now() + timedelta(minutes=2)
                ext_msg = " | ⏳ *Phiên đấu giá đã được gia hạn thêm 2 phút!*"
            else:
                ext_msg = ""

            cursor = await db.execute(
                "UPDATE auctions SET current_bid = ?, highest_bidder_id = ?, end_time = ? WHERE auction_id = ? AND current_bid = ?",
                (amount, user_id, new_end_time, auction_id, curr_bid),
            )

            if cursor.rowcount == 0:
                return await ctx.send(
                    "❌ Giá đã thay đổi bởi một đạo hữu khác! Vui lòng !bid lại với giá mới."
                )

            # Nếu update thành công mới trừ tiền và trả tiền người cũ
            if last_bidder:
                await db.execute(
                    "UPDATE players SET linh_thach = linh_thach + ? WHERE user_id = ?",
                    (curr_bid, last_bidder),
                )
            await db.commit()
            await ctx.send(
                f"✅ Đã đặt thầu **{amount:,} LT** cho phiên #`{auction_id}`!{ext_msg}"
            )

    @commands.command(name="daugialist")
    async def list_auctions(self, ctx):
        async with get_db(self.db_path) as db:
            c = await db.execute(
                "SELECT a.auction_id, im.ten_vat_pham, a.current_bid, a.end_time, a.seller_id, a.buyout_price, im.pham_cap FROM auctions a JOIN item_master im ON a.item_id = im.item_id ORDER BY a.end_time ASC"
            )
            rows = await c.fetchall()

            embed = discord.Embed(
                title="⚖️ ĐẤU GIÁ VIỆN", color=discord.Color.dark_magenta()
            )
            if not rows:
                embed.description = "Hiện không có ai đấu giá."
            else:
                for a_id, name, bid, end, seller, buyout, pham in rows:
                    color_names = {1: "⬜", 2: "🟢", 3: "🔵", 4: "🟣", 5: "🟡"}
                    title = f"#{a_id} | {color_names.get(pham, '')} {name}"
                    seller_type = "🏛️ Hệ Thống" if seller == "0" else "👤 Người chơi"
                    buyout_txt = f" | ⚡ Mua đứt: **{buyout:,}**" if buyout > 0 else ""

                    embed.add_field(
                        name=title,
                        value=f"💰 Giá: **{bid:,} LT**{buyout_txt}\n👤 Bán: {seller_type}\n⏳ Kết thúc: `{str(end).split('.')[0]}`",
                        inline=False,
                    )
            await ctx.send(embed=embed)

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
    await bot.add_cog(DauGia(bot))
