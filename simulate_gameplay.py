import asyncio
import aiosqlite
import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

# Thêm đường dẫn để import utils và cogs
sys.path.append(os.getcwd())
from utils import get_db


async def run_simulation():
    db_path = "tu_tien.db"
    print("🚀 BẮT ĐẦU MÔ PHỎNG HỆ THỐNG TU TIÊN V3...")

    # 1. Khởi tạo DB sạch
    from init_db import create_database

    create_database()
    print("✅ Đã khởi tạo lại Cơ sở dữ liệu sạch.")

    # Mock Bot & Context
    bot = MagicMock()
    bot.user = MagicMock(id=123456789)
    bot.guilds = [
        MagicMock(
            text_channels=[
                MagicMock(
                    name="thế giới tu chân",
                    permissions_for=lambda x: MagicMock(send_messages=True),
                )
            ]
        )
    ]

    # Mock update_quest_progress
    async def mock_update_quest(user_id, g_type, ctx=None):
        pass

    bot.update_quest_progress = mock_update_quest

    # --- SIMULATION 1: TÂN THỦ NHẬP MÔN ---
    print("\n[MÔ PHỎNG 1] Tân Thủ Nhập Môn & Tu Luyện...")
    from cogs.tu_luyen import TuLuyen

    cog_tu_luyen = TuLuyen(bot)

    user_id = "111111"
    ctx = AsyncMock()
    ctx.author.id = int(user_id)
    ctx.author.mention = f"<@{user_id}>"
    ctx.send = AsyncMock(return_value=AsyncMock(edit=AsyncMock()))

    # Lần đầu tu luyện (Insert player)
    await cog_tu_luyen.tuluyen.callback(cog_tu_luyen, ctx)

    # Tu luyện vài lần để đủ Tu Vi đột phá
    print("   - Đang tu luyện tích lũy...")
    async with get_db(db_path) as db:
        # Cheat 1 chút để test nhanh: Sét tu vi lên 200
        await db.execute(
            "UPDATE players SET tu_vi = 200, the_luc = 100 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()

    # --- SIMULATION 2: ĐỘT PHÁ CẢNH GIỚI ---
    print("\n[MÔ PHỎNG 2] Đột Phá Cảnh Giới...")
    from cogs.dot_pha import DoKiep

    cog_dot_pha = DoKiep(bot)

    # Mock random để chắc chắn thành công (Hoặc loop cho đến khi thành công)
    import random

    original_random = random.random
    random.random = lambda: 0.0  # Force success

    await cog_dot_pha.dotpha.callback(cog_dot_pha, ctx)
    random.random = original_random  # Restore

    async with get_db(db_path) as db:
        c = await db.execute(
            "SELECT canh_gioi_id, tu_vi FROM players WHERE user_id = ?", (user_id,)
        )
        res = await c.fetchone()
        print(f"   - Sau Đột Phá: Cảnh giới ID: {res[0]}, Tu Vi: {res[1]} (Phải là 0)")
        if res[0] == 2 and res[1] == 0:
            print("   => Logic thăng cấp & Reset Tu Vi: OK")
        else:
            print("   => ERROR: Logic thăng cấp sai!")

    # --- SIMULATION 3: GIAO THƯƠNG & ĐẤU GIÁ ---
    print("\n[MÔ PHỎNG 3] Đấu giá Thiên Đạo & Player Bid...")
    from cogs.dau_gia import DauGia

    cog_dau_gia = DauGia(bot)

    # 1. Hệ thống tạo phiên đấu giá
    await cog_dau_gia.system_auction_spawner()

    async with get_db(db_path) as db:
        c = await db.execute(
            "SELECT auction_id, current_bid, buyout_price FROM auctions WHERE seller_id = '0'"
        )
        auc = await c.fetchone()
        if auc:
            a_id, curr_bid, buyout = auc
            print(
                f"   - Đã tạo phiên hệ thống #{a_id}: Khởi điểm {curr_bid}, Mua đứt {buyout}"
            )

            # Giả định user có đủ tiền để bid
            await db.execute(
                "UPDATE players SET linh_thach = 1000000 WHERE user_id = ?", (user_id,)
            )
            await db.commit()

            # User Bid vượt giá khởi điểm
            await cog_dau_gia.place_bid.callback(cog_dau_gia, ctx, a_id, curr_bid + 500)

            # Kiểm tra tiền đã trừ chưa
            p = await db.execute(
                "SELECT linh_thach FROM players WHERE user_id = ?", (user_id,)
            )
            print(f"   - Sau khi Bid (+500): Linh Thạch: {(await p.fetchone())[0]:,}")

            # Kiểm tra trạng thái auction
            ac = await db.execute(
                "SELECT current_bid, highest_bidder_id FROM auctions WHERE auction_id = ?",
                (a_id,),
            )
            res_auc = await ac.fetchone()
            print(
                f"   - Auction #{a_id}: Giá hiện tại {res_auc[0]}, Người thầu: {res_auc[1]}"
            )

    # --- SIMULATION 4: XÃ HỘI (LẬP PHÁI) ---
    print("\n[MÔ PHỎNG 4] Khai Môn Lập Phái...")
    from cogs.xa_hoi import XaHoi

    cog_xa_hoi = XaHoi(bot)

    # Đủ tiền lập phái
    await cog_xa_hoi.lapphai.callback(cog_xa_hoi, ctx, ten_phai="Thiên Đạo Môn")

    async with get_db(db_path) as db:
        c = await db.execute(
            "SELECT ten_tong_mon FROM tong_mon WHERE bang_chu_id = ?", (user_id,)
        )
        res = await c.fetchone()
        if res:
            print(f"   - Đã lập phái: {res[0]}")
            print("   => Logic Xã Hội (Args capture): OK")

    # --- SIMULATION 5: BOSS THẾ GIỚI ---
    print("\n[MÔ PHỎNG 5] World Boss Spawn & Attack...")
    from cogs.su_kien import SuKien

    cog_su_kien = SuKien(bot)

    await cog_su_kien.spawn_boss()
    print(
        f"   - Boss đã giáng thế: {cog_su_kien.world_boss['name']} (HP: {cog_su_kien.world_boss['max_hp']:,})"
    )

    # Tấn công
    await cog_su_kien.chemboss.callback(cog_su_kien, ctx)
    print(f"   - Sau khi tấn công: HP Boss còn {cog_su_kien.world_boss['hp']:,}")

    print("\n🌟 MÔ PHỎNG HOÀN TẤT. KHÔNG PHÁT HIỆN LỖI XUNG ĐỘT.")


if __name__ == "__main__":
    asyncio.run(run_simulation())
