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
            title="📊 DANH MỤC LỆNH & LUỒNG HOẠT ĐỘNG V4 GOLD FULL",
            description="Chào mừng đạo hữu đã bước chân vào con đường tu đạo đầy vinh quang.",
            color=discord.Color.gold(),
        )

        embed.add_field(
            name="🧘 TU LUYỆN & THÔNG TIN",
            value="`!me`: Hồ sơ cá nhân\n`!top`: Bảng xếp hạng\n`!tuluyen`: Tu luyện tập trung\n`!dotpha`: Đột phá bình cảnh\n`!doituvi`: Đổi Linh thạch lấy Tu vi",
            inline=False,
        )
        embed.add_field(
            name="⚔️ CHIẾN ĐẤU & THỬ THÁCH",
            value="`!sanboss`: Săn yêu thú\n`!bicanh`: Khám phá bí cảnh\n`!chemboss`: Hợp lực trảm Boss\n`!thachdau @`: Tỷ thí PVP\n`!dosat @`: Đồ sát cướp đoạt",
            inline=False,
        )
        embed.add_field(
            name="📚 CÔNG PHÁP & CHẾ TẠO",
            value="`!hoc`: Lĩnh ngộ bí kíp\n`!congphap`: Quản lý kỹ năng\n`!danphuong`: Xem công thức\n`!luyendan`: Luyện linh đan",
            inline=False,
        )
        embed.add_field(
            name="🎒 VẬT PHẨM & TRANG BỊ",
            value="`!tuido`: Tôn khố cá nhân\n`!use <id>`: Sử dụng/Trang bị\n`!thao <id>`: Tháo trang bị\n`!dancac`: Cửa hàng linh đan",
            inline=False,
        )
        embed.add_field(
            name="💰 GIAO THƯƠNG & ĐẤU GIÁ",
            value="`!ban <id>`: Treo Chợ Đen\n`!choden`: Xem Marketplace\n`!chuyentien @`: Chuyển tiền\n`!giaodich @`: Bán trực tiếp\n`!daugialist`: Sàn đấu giá\n`!daugia`: Mở đấu giá\n`!bid`: Trả giá thầu",
            inline=False,
        )
        embed.add_field(
            name="🤝 XÃ HỘI & TÔNG MÔN",
            value="`!songtu @`: Kết đạo lữ\n`!lithu`: Ly hôn\n`!lapphai`: Lập tông môn\n`!moiphai @`: Mời đệ tử\n`!roiphai`: Rời môn phái\n`!xemphai`: Tin tông môn",
            inline=False,
        )
        embed.add_field(
            name="⚙️ HỆ THỐNG TỰ ĐỘNG",
            value="• **Auto-Recovery**: Hồi 1 TL/s, 1% HP/s\n• **Boss**: Xuất hiện mỗi 2 giờ\n• **Flash Sale**: Mở shop mỗi 3 giờ\n• **Cơ Duyên**: Random rớt quà mỗi 30p\n• **Linh Thạch Rơi**: Gõ `!nhat` khi có thông báo",
            inline=False,
        )
        embed.add_field(
            name="🏪 THƯƠNG NHÂN & KHÁC",
            value="`?shop`: Chợ đen (Pháp tắc ?)\n`?buy <id>`: Mua đồ từ Merchant\n`!nhiemvu`: Nhiệm vụ ngày\n`!prefix`: Đổi tiền tố\n`!trogiup`: Hiện bảng này",
            inline=False,
        )

        embed.set_footer(text="⚔️ Tổng cộng: 36 lệnh chính thức | V4 GOLD FULL 🏆")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(HeThong(bot))
