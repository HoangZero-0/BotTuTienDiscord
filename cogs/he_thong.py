import discord
from discord.ext import commands, tasks
import aiosqlite
from utils import get_db


class HeThong(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "tu_tien.db"

    def cog_unload(self):
        pass

    @commands.command(name="trogiup", aliases=["help"])
    async def help_command(self, ctx):
        embed = discord.Embed(
            title="📜 THIÊN ĐẠO QUY TẮC - BOT TU TIÊN V4 GOLD FULL",
            description="Chào mừng đạo hữu đã bước chân vào con đường tu đạo đầy gian nan nhưng vinh quang.",
            color=discord.Color.gold(),
        )

        embed.add_field(
            name="🧘 Tu Luyện & Đột Phá",
            value="`!tuluyen`: Tích lũy linh khí\n`!dotpha`: Cầu linh kiếp thăng cấp\n`!me`: Xem danh thiếp tu sĩ",
            inline=False,
        )
        embed.add_field(
            name="⚔️ Chiến Đấu & Thử Thách",
            value="`!sanboss`: Săn yêu thú kiếm đồ\n`!bicanh`: Khám phá di tích cổ\n`!chemboss`: Chung tay trảm World Boss",
            inline=False,
        )
        embed.add_field(
            name="🧪 Vật Phẩm & Linh Đan",
            value="`!tuido`: Xem hành trang\n`!use <id>`: Sử dụng vật phẩm\n`!thao <id>`: Tháo trang bị\n`!danphuong`: Xem công thức luyện đan\n`!luyendan <id>`: Luyện chế linh đan",
            inline=False,
        )
        embed.add_field(
            name="💰 Giao Thương & Đấu Giá",
            value="`?shop`: Shop Thương Nhân\n`!daugialist`: Đấu giá sàn\n`!daugia`: Treo đấu giá\n`!bid`: Đặt thầu/Mua đứt\n`!chuyentien`: Chuyển tiền (Thuế 10%)\n`!giaodich`: Bán đồ trực tiếp",
            inline=False,
        )
        embed.add_field(
            name="🤝 Xã Hội & Bang Phái",
            value="`!songtu @`: Kết đôi\n`!lapphai`: Lập tông môn\n`!moiphai`: Mời đệ tử\n`!xemphai`: Thông tin tông môn",
            inline=False,
        )
        embed.add_field(
            name="🏆 Vinh Danh",
            value="`!nhiemvu`: Xem nhiệm vụ ngày\n`!top`: Bảng vàng thiên đạo",
            inline=False,
        )

        embed.set_footer(
            text="Gợi Ý: Luyện đan và trang bị pháp bảo mạnh để chinh phục World Boss!"
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(HeThong(bot))
