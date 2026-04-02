import discord
from discord.ext import commands
import aiosqlite
import os
from utils import get_db, update_quest_progress

# 1. Khởi tạo Intents
intents = discord.Intents.default()
intents.message_content = True


class ThienDaoBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.db_path = "tu_tien.db"

    # 2. Hàm tính Lực Chiến Tổng (Dùng chung cho các Cogs)
    async def get_total_cp(self, user_id):
        async with get_db(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT p.luc_chien_goc + COALESCE(SUM(im.chi_so_buff), 0)
                FROM players p
                LEFT JOIN inventory i ON p.user_id = i.user_id AND i.trang_thai = 'dang_trang_bi'
                LEFT JOIN item_master im ON i.item_id = im.item_id
                WHERE p.user_id = ?
            """,
                (str(user_id),),
            )
            result = await cursor.fetchone()
            return result[0] if result else 0

    # 3. Hàm cập nhật tiến độ nhiệm vụ (V2.0)
    async def update_quest_progress(self, user_id, goal_type, ctx=None):
        await update_quest_progress(self.db_path, user_id, goal_type, ctx)

    # 3. Tự động nạp tất cả 11 Cogs
    async def setup_hook(self):
        extensions = [
            "cogs.tu_luyen",
            "cogs.dot_pha",
            "cogs.thong_tin",
            "cogs.bi_canh",
            "cogs.san_boss",
            "cogs.vat_pham",
            "cogs.bang_xep_hang",
            "cogs.he_thong",
            "cogs.xa_hoi",
            "cogs.giao_dich",
            "cogs.che_tao",
            "cogs.nhiem_vu",
            "cogs.dau_gia",
            "cogs.su_kien",
            "cogs.dan_cac",
            "cogs.cong_phap",
            "cogs.pvp",
            "cogs.do_sat",
        ]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"✅ Đã kích hoạt Pháp Tắc: {ext}")
            except Exception as e:
                print(f"❌ Lỗi nạp {ext}: {e}")

    # 4. Chỉ xử lý lệnh trong kênh Thế Giới Tu Chân
    async def on_message(self, message):
        if message.author == self.user:
            return

        # Bỏ qua nếu là tin nhắn riêng (DM)
        if not message.guild:
            return

        # Tên channel trên Discord thường tự động viết thường và đổi dấu cách thành gạch ngang
        # Ví dụ: "Thế Giới Tu Chân" -> "thế-giới-tu-chân"
        if message.channel.name.replace("-", " ").lower() != "thế giới tu chân":
            return

        await self.process_commands(message)

    async def on_ready(self):
        from utils import setup_db_columns

        await setup_db_columns(self.db_path)
        print(f"---")
        print(f"⛩️ Thiên Đạo [{self.user.name}] đã giáng lâm!")
        print(f"🌍 Thế giới Tu Tiên đã sẵn sàng vận hành.")
        print(f"---")

    # 4. Xử lý lỗi Cooldown toàn hệ thống
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            import random

            vui_ve = [
                f"⏳ Gấp cái gì? Tu tiên chứ có phải đi chợ đâu! Đợi {error.retry_after:.1f} giây nữa cho tĩnh tâm.",
                f"⏳ Tâm tính nóng nảy thế này dễ tẩu hỏa nhập ma lắm. Nghỉ {error.retry_after:.1f} giây đi đạo hữu.",
                f"⏳ Bàn phím sắp cháy rồi! Đợi {error.retry_after:.1f} giây cho nó nguội bớt rồi hãy nhấn tiếp.",
                f"⏳ Tu vi không phải hít không khí mà có, nghỉ ngơi {error.retry_after:.1f} giây cho kinh mạch hồi phục đi.",
                f"⏳ Đạo hữu định dùng 'Nhất Dương Chỉ' để đắc đạo à? Chờ {error.retry_after:.1f} giây nữa nhé.",
                f"⏳ Bình tĩnh! Thiên địa linh khí đang hội tụ, nhấn nhanh quá nó tắc nghẽn bây giờ. Đợi {error.retry_after:.1f} giây.",
                f"⏳ Đang hồi sức! Đạo hữu làm gì mà như bị truy sát vậy? {error.retry_after:.1f} giây nữa nhé.",
            ]
            await ctx.send(random.choice(vui_ve))
        elif isinstance(error, commands.CommandNotFound):
            pass  # Bỏ qua lỗi gõ sai lệnh để tránh spam
        else:
            import traceback

            traceback.print_exception(type(error), error, error.__traceback__)
            print(f"⚠️ Lỗi phát sinh: {error}")


bot = ThienDaoBot()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    # 5. Chạy Bot (Hãy đảm bảo Token đã được bảo mật trong .env)
    token = os.getenv("TOKEN_THIEN_DAO")
    if token:
        bot.run(token)
    else:
        print("❌ Lỗi: Không tìm thấy TOKEN_THIEN_DAO trong file .env")
