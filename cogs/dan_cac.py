import discord
from discord.ext import commands
from utils import get_db

class DanCacSelect(discord.ui.Select):
    def __init__(self, items_with_price):
        self.items_with_price = items_with_price
        options = []
        for i_id, i_name, i_price in items_with_price:
            options.append(discord.SelectOption(
                label=i_name,
                description=f"Giá: {i_price:,} Linh Thạch",
                value=str(i_id)
            ))
        super().__init__(placeholder="Chọn loại đan dược để mua...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await self.view.process_purchase(interaction, int(self.values[0]))

class DanCacView(discord.ui.View):
    def __init__(self, db_path, items_with_price):
        super().__init__(timeout=60)
        self.db_path = db_path
        self.items_with_price = {i[0]: i for i in items_with_price}
        self.add_item(DanCacSelect(items_with_price))

    async def process_purchase(self, interaction: discord.Interaction, item_id: int):
        user_id = str(interaction.user.id)
        item_data = self.items_with_price[item_id]
        price = item_data[2]
        name = item_data[1]

        async with get_db(self.db_path) as db:
            cursor = await db.execute("SELECT linh_thach FROM players WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if not row:
                return await interaction.response.send_message("❌ Ngài chưa có tên trong hệ thống tu chân!", ephemeral=True)
            
            player_lt = row[0]
            if player_lt < price:
                return await interaction.response.send_message(f"⚠️ Kém cỏi! Ngài chỉ có {player_lt:,} Linh thạch, không đủ {price:,} nghìn lấy gì mua?", ephemeral=True)
            
            # Trừ linh thạch và thêm item
            await db.execute("UPDATE players SET linh_thach = linh_thach - ? WHERE user_id = ?", (price, user_id))
            await db.execute("INSERT INTO inventory (user_id, item_id, so_luong) VALUES (?, ?, 1) ON CONFLICT(user_id, item_id) DO UPDATE SET so_luong = so_luong + 1", (user_id, item_id))
            await db.commit()

        await interaction.response.send_message(f"🛒 **GIAO DỊCH THÀNH CÔNG!** {interaction.user.mention} đã mua thành công 1 viên **{name}** với giá {price:,} Linh Thạch.")

class DanCac(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"
        self.prices = {
            101: 200,      # Huyết Khí Đan
            102: 800,      # Tụ Khí Đan
            103: 3000,     # Trúc Cơ Đan
            104: 10000,    # Ngưng Nguyên Đan
            105: 50000,    # Hóa Anh Đan
            106: 200000,   # Định Thần Đan
            107: 800000,   # Phá Hư Đan
            108: 5000000,  # Thần Tủy Đan
            109: 20000000, # Hỗn Độn Đan
            110: 100000000,# Thái Mãng Đan
        }

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def dancac(self, ctx):
        async with get_db(self.db_path) as db:
            cursor = await db.execute("SELECT item_id, ten_vat_pham FROM item_master WHERE loai_vat_pham = 'dan_duoc' ORDER BY item_id ASC")
            items = await cursor.fetchall()
        
        items_with_price = []
        for row in items:
            i_id, i_name = row
            if i_id in self.prices:
                items_with_price.append((i_id, i_name, self.prices[i_id]))

        if not items_with_price:
            return await ctx.send("Tiệm Đan Các hiện đang đóng cửa do hết hàng!")

        view = DanCacView(self.db_path, items_with_price)
        await ctx.send(f"🏯 **QUANG LÂM ĐAN CÁC**\nKính chào {ctx.author.mention}, tiệm tại hạ chuyên bán thuốc trị Lôi kiếp, nâng Tu vi. Xin hãy lựa chọn:", view=view)

async def setup(bot):
    await bot.add_cog(DanCac(bot))
