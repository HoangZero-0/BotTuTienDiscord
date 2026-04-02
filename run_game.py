import asyncio

# --- Hệ thống Bot Tu Tiên V3 Gold - Khởi động ---
import discord
import os
from main_thiendao import ThienDaoBot
from main_thuongnhan import ThuongNhanBot, setup_commands

from dotenv import load_dotenv

load_dotenv()

# --- CẤU HÌNH ---
# Tokens được đọc bảo mật từ file .env
TOKEN_THIEN_DAO = os.getenv("TOKEN_THIEN_DAO")
TOKEN_THUONG_NHAN = os.getenv("TOKEN_THUONG_NHAN")
ID_BOT_THIEN_DAO = int(
    os.getenv("ID_BOT_THIEN_DAO", 0)
)  # ID của Bot Thiên Đạo để Bot Thương Nhân theo dõi


# ==========================================
# KHỞI CHẠY HỆ THỐNG
# ==========================================
async def main():
    # 0. Tự động kiểm tra và khởi tạo Database (Deployment Friendly)
    if not os.path.exists("tu_tien.db"):
        print("📁 Không tìm thấy Cơ sở dữ liệu. Đang tự động khởi tạo 'tu_tien.db'...")
        from init_db import create_database

        create_database()
    else:
        # Cập nhật dữ liệu cấu trúc (Cảnh giới, Vật phẩm) nếu cần
        # Optional: Đạo hữu có thể bỏ comment dòng dưới nếu muốn tự động cập nhật cân bằng game mỗi khi restart
        # from init_db import create_database; create_database()
        print("📁 Đã tìm thấy Cơ sở dữ liệu hiện có. Tiếp tục khởi động...")

    # 1. Khởi tạo Bot Thiên Đạo
    bot_td = ThienDaoBot()

    # 2. Khởi tạo Bot Thương Nhân
    bot_tn = ThuongNhanBot(ID_BOT_THIEN_DAO)
    setup_commands(bot_tn)  # Nạp các lệnh cho Thương Nhân

    print("🚀 THIÊN ĐẠO ĐÃ GIÁNG LÂM")

    # 3. Chạy song song cả 2 bot
    await asyncio.gather(bot_td.start(TOKEN_THIEN_DAO), bot_tn.start(TOKEN_THUONG_NHAN))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n📴 Hệ thống đã đóng cửa. Hẹn gặp lại các đạo hữu!")
    except Exception as e:
        print(f"⚠️ Lỗi hệ thống: {e}")
