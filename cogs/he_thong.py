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
            name="🧘 TU LUYỆN & THÔNG TIN",
            value="`!tuluyen`: Tích lũy linh khí\n`!dotpha`: Đột phá cảnh giới\n`!doituvi`: Đổi Linh thạch lấy Tu vi\n`!me`: Xem danh thiếp tu sĩ\n`!top`: Bảng xếp hạng",
            inline=False,
        )
        embed.add_field(
            name="⚔️ CHIẾN ĐẤU & THỬ THÁCH",
            value="`!sanboss`: Săn yêu thú\n`!bicanh`: Khám phá bí cảnh\n`!chemboss`: Trảm World Boss\n`!thachdau @`: PK Tỉ thí\n`!dosat @`: Đồ sát cướp bóc",
            inline=False,
        )
        embed.add_field(
            name="📚 CÔNG PHÁP & KỸ NĂNG",
            value="`!hoc <id>`: Lĩnh ngộ bí kíp\n`!congphap`: Quản lý & Trang bị kỹ năng\n`!danphuong`: Xem công thức luyện đan\n`!luyendan <id>`: Luyện chế linh đan",
            inline=False,
        )
        embed.add_field(
            name="🎒 VẬT PHẨM & TRANG BỊ",
            value="`!tuido`: Xem hành trang\n`!use <id>`: Sử dụng/Trang bị\n`!thao <id>`: Gỡ trang bị",
            inline=False,
        )
        embed.add_field(
            name="💰 GIAO THƯƠNG & CHỢ ĐEN",
            value="`!choden`: Xem chợ đen toàn giới\n`!ban <id> <giá>`: Treo đồ lên chợ\n`!chuyentien @ <lt>`: Chuyển Linh thạch\n`!giaodich @ <id> <giá>`: Bán đồ trực tiếp",
            inline=False,
        )
        embed.add_field(
            name="⚖️ ĐẤU GIÁ BẢO VẬT",
            value="`!daugialist`: Xem danh sách đấu giá\n`!daugia <id> <giá>`: Đưa đồ lên sàn\n`!bid <id> <giá>`: Đặt thầu/Mua đứt",
            inline=False,
        )
        embed.add_field(
            name="🤝 XÃ HỘI & TÔNG MÔN",
            value="`!songtu @`: Kết đôi Đạo lữ\n`!lithu`: Ly hôn\n`!lapphai`: Lập tông môn\n`!moiphai @`: Mời đệ tử\n`!roiphai`: Rời tông\n`!xemphai`: Xem tông môn",
            inline=False,
        )
        embed.add_field(
            name="🏪 THƯƠNG NHÂN & KHÁC",
            value="`?shop`: Shop hệ thống (Bot Thương Nhân)\n`?buy <id>`: Mua đồ shop\n`!nhiemvu`: Nhiệm vụ ngày\n`!trogiup`: Hiện bảng này",
            inline=False,
        )

        embed.set_footer(
            text="Gợi Ý: Luyện đan và trang bị pháp bảo mạnh để chinh phục World Boss!"
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(HeThong(bot))
