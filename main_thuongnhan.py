import discord
from discord.ext import commands
import aiosqlite
import asyncio
import random
from discord.ext import tasks
from utils import CleanID, CleanInt, get_db, update_quest_progress


class ThuongNhanBot(commands.Bot):
    def __init__(self, thiendao_id):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="?", intents=intents, help_command=None)
        self.thiendao_id = thiendao_id
        self.db_path = "tu_tien.db"
        self.user_shops = {}  # Bộ nhớ đệm Shop: {user_id: {item_id: price}}
        self.flash_sale.start()

    def cog_unload(self):
        self.flash_sale.cancel()

    @tasks.loop(hours=3)
    async def flash_sale(self):
        """Mở shop giới hạn toàn server"""
        print("🏪 [Thương Nhân] Đang mở Chợ Đen giới hạn...")
        for guild in self.guilds:
            # CHỈ tìm kênh có tên 'Thế Giới Tu Chân'
            channel = discord.utils.get(guild.text_channels, name="thế-giới-tu-chân")

            # Nếu không tìm thấy kênh theo slug, thử tìm theo tên hiển thị (một số thư viện/OS có thể khác biệt)
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
                embed = discord.Embed(
                    title="🎒 CHỢ ĐEN GIỚI HẠN", color=discord.Color.dark_gray()
                )
                embed.description = "🔥 Lão phu vừa nhập được vài món hàng 'nóng'! Chợ đen sẽ mở trong **30 phút**, đạo hữu hãy nhanh tay gõ `?shop`!"
                await channel.send(embed=embed)
        await asyncio.sleep(1800)  # Mở trong 30p (có thể dùng cờ trạng thái nếu muốn)

    async def on_ready(self):
        print(f"---")
        print(f"💰 [{self.user.name}] đã hạ phàm!")
        print(f"🧐 Đang rình rập ID Thiên Đạo: {self.thiendao_id}")
        print(f"---")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            quotes = [
                f"⏳ Ngươi tính ép giá lão phu à? Đợi {error.retry_after:.1f} giây nữa rồi hãy hỏi mua!",
                f"⏳ Chậm lại, chậm lại! Chỗ lão phu không phải cái chợ vỡ. {error.retry_after:.1f} giây nữa quay lại.",
                f"⏳ Đạo hữu vội vã quá, linh thạch chưa kịp đếm xong. Đợi {error.retry_after:.1f} giây nhé.",
            ]
            await ctx.send(random.choice(quotes))
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"⚠️ Thiếu thông tin! Cú pháp: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`"
            )
        elif not isinstance(error, commands.CommandNotFound):
            print(f"⚠️ Lỗi Thương Nhân: {error}")

    async def on_message(self, message):
        if message.author == self.user:
            return

        # Chỉ xử lý trong kênh Thế Giới Tu Chân
        if (
            not message.guild
            or message.channel.name.replace("-", " ").lower() != "thế giới tu chân"
        ):
            return

        # Tương tác khi thấy Thiên Đạo báo Đột Phá thành công
        if (
            message.author.id == self.thiendao_id
            and "ĐỘ KIẾP THÀNH CÔNG" in message.content
        ):
            await asyncio.sleep(2)
            if message.mentions:
                player = message.mentions[0]
                gift = random.randint(200, 1000)

                async with get_db(self.db_path) as db:
                    await db.execute(
                        "UPDATE players SET linh_thach = linh_thach + ? WHERE user_id = ?",
                        (gift, str(player.id)),
                    )
                    await db.commit()

                quotes = [
                    f"💸 Ô kìa, chúc mừng {player.mention} đạo hữu! Cầm lấy {gift} Linh Thạch này, vào tiệm ta làm vài món đồ hộ thân đi!",
                    f"🌟 Chúc mừng đạo hữu {player.mention} thoát thai hoán cốt! Ta tặng ngài {gift} Linh Thạch lấy thảo nhé!",
                    f"🤑 {player.mention} đạo hữu thật là yêu nghiệt! Nhận {gift} Linh Thạch quà gặp mặt của tệ xá nào!",
                ]
                await message.channel.send(random.choice(quotes))

        await self.process_commands(message)


# Đăng ký các lệnh dưới dạng phương thức của class hoặc dùng decorator bên trong class
def setup_commands(bot):
    @bot.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def shop(ctx):
        async with get_db(bot.db_path) as db:
            cursor = await db.execute(
                "SELECT item_id, ten_vat_pham, pham_cap, mo_ta FROM item_master ORDER BY RANDOM() LIMIT 3"
            )
            items = await cursor.fetchall()
            user_id = str(ctx.author.id)
            bot.user_shops[user_id] = {}  # Reset shop cũ

            embed = discord.Embed(
                title="🛒 Chợ Đen Vạn Giới",
                description="Hàng thật giá cao, hàng giả giá... cũng cao!",
                color=discord.Color.dark_gray(),
            )
            for i_id, name, grade, desc in items:
                # Công thức giá V2.0: Tăng mạnh theo phẩm cấp (Exponential)
                base_price = (grade**3) * 1000
                price = int(base_price + random.randint(500, 2000))
                bot.user_shops[user_id][i_id] = price  # Lưu giá vào bộ nhớ đệm
                embed.add_field(
                    name=f"[ID: {i_id}] {name}",
                    value=f"Giá: **{price:,} Linh Thạch**\n*{desc}*",
                    inline=False,
                )

            embed.set_footer(text="Cú pháp: ?buy ID Giá")
            await ctx.send(embed=embed)

    @bot.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def buy(ctx, item_id: CleanID, price: CleanInt):
        user_id = str(ctx.author.id)
        async with get_db(bot.db_path) as db:
            # KIỂM TRA GIÁ VÀ ID TRONG BỘ NHỚ ĐỆM TRƯỚC
            if user_id not in bot.user_shops or item_id not in bot.user_shops[user_id]:
                return await ctx.send(
                    "❌ Đạo hữu chưa xem món này trong Chợ Đen hoặc cửa hàng đã đổi món!"
                )

            expected_price = bot.user_shops[user_id][item_id]
            if price < expected_price:
                return await ctx.send(
                    f"⚠️ **BỊP À?** Giá niêm yết là **{expected_price:,} LT**, đạo hữu đưa có **{price:,} LT** thì mua bằng niềm tin à?"
                )
            if price > expected_price:
                return await ctx.send(
                    f"🧐 **ĐÀO HOA?** Đạo hữu định đưa thêm tiền boa cho lão phu à? Chỉ cần đúng **{expected_price:,} LT** là đủ!"
                )

            # SAU ĐÓ MỚI KIỂM TRA SỐ DƯ TÀI KHOẢN
            cursor = await db.execute(
                "SELECT linh_thach FROM players WHERE user_id = ?", (user_id,)
            )
            result = await cursor.fetchone()

            if not result or result[0] < expected_price:
                return await ctx.send(
                    "🔥 Lão phu không làm từ thiện! Tài khoản đạo hữu không đủ Linh Thạch!"
                )

            cursor = await db.execute(
                "SELECT ten_vat_pham FROM item_master WHERE item_id = ?", (item_id,)
            )
            item = await cursor.fetchone()
            if not item:
                return await ctx.send("❌ Món đồ này lão phu chưa nghe tên bao giờ!")

            await db.execute(
                "UPDATE players SET linh_thach = linh_thach - ? WHERE user_id = ?",
                (price, user_id),
            )
            if random.random() < 0.05:
                # Trúng kế: Nhận "Cỏ Dại" (301)
                item_id_scam = 301
                await db.execute(
                    "INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, ?, 1) ON CONFLICT(user_id, item_id) DO UPDATE SET so_luong = so_luong + 1",
                    (user_id, item_id_scam),
                )
                await db.commit()
                return await ctx.send(
                    f"😂 **TRÚNG KẾ!** Lão phu lỡ tay gói nhầm một đống **Cỏ Dại** cho đạo hữu rồi! {price:,} Linh Thạch coi như học phí nhé!"
                )

            await db.execute(
                """
                INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, ?, 1)
                ON CONFLICT(user_id, item_id) DO UPDATE SET so_luong = so_luong + 1""",
                (user_id, item_id),
            )

            await db.commit()
            await ctx.send(
                f"🛍️ Giao dịch thành công! **{item[0]}** đã nằm trong túi đạo hữu. Khách quý, khách quý!"
            )

        # CẬP NHẬT NHIỆM VỤ (Dùng hàm chung từ utils.py)
        await update_quest_progress(bot.db_path, user_id, "buy_shop", ctx)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    TOKEN = os.getenv("TOKEN_THUONG_NHAN")
    ID_THIEN_DAO = int(os.getenv("ID_BOT_THIEN_DAO", 0))

    if TOKEN and ID_THIEN_DAO:
        bot = ThuongNhanBot(ID_THIEN_DAO)
        setup_commands(bot)
        bot.run(TOKEN)
    else:
        print("❌ Lỗi: Thiếu cấu hình TOKEN hoặc ID_THIEN_DAO trong file .env")
