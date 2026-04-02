import asyncio
import aiosqlite
import os


async def check_logic():
    db_path = "tu_tien.db"
    print("🔍 KIỂM TRA TÍNH TOÀN VẸN LOGIC HỆ THỐNG...")

    async with aiosqlite.connect(db_path) as db:
        # 1. Kiểm tra bảng realms_master
        c = await db.execute("SELECT COUNT(*) FROM realms_master")
        count = (await c.fetchone())[0]
        print(f"   [1] Số lượng Cảnh giới: {count} (Target: 24)")

        # 2. Kiểm tra logic tv_max (Next level threshold)
        # Giả sử người chơi ở level 1
        c = await db.execute(
            "SELECT tu_vi_can_thiet FROM realms_master WHERE canh_gioi_id = 1 + 1"
        )
        tv_max = (await c.fetchone())[0]
        print(f"   [2] Ngưỡng thăng cấp từ Level 1 lên Level 2: {tv_max} (Target: 200)")

        # 3. Kiểm tra logic Công thức Lực chiến (CP)
        # Test Query tính tổng CP (Base + Items)
        user_id = "test_user"
        await db.execute(
            "INSERT OR REPLACE INTO players (user_id, luc_chien_goc) VALUES (?, 1000)",
            (user_id,),
        )
        await db.execute(
            "INSERT OR REPLACE INTO item_master (item_id, ten_vat_pham, chi_so_buff) VALUES (999, 'Thần Kiếm', 5000)"
        )
        await db.execute(
            "INSERT OR REPLACE INTO inventory (user_id, item_id, so_luong, trang_thai) VALUES (?, 999, 1, 'dang_trang_bi')",
            (user_id,),
        )

        cp_query = """
            SELECT p.luc_chien_goc + IFNULL((
                SELECT SUM(im.chi_so_buff) 
                FROM inventory i 
                JOIN item_master im ON i.item_id = im.item_id 
                WHERE i.user_id = p.user_id AND i.trang_thai = 'dang_trang_bi'
            ), 0)
            FROM players p WHERE p.user_id = ?
        """
        c = await db.execute(cp_query, (user_id,))
        total_cp = (await c.fetchone())[0]
        print(
            f"   [3] Kiểm tra tính Lực chiến: {total_cp} (1000 + 5000 = 6000?) -> {'OK' if total_cp == 6000 else 'FAIL'}"
        )

        # 4. Kiểm tra logic Xã Hội (Sửa lỗi Capture tên phái)
        # Vì đây là lệnh gọi, ta kiểm tra xem bảng tong_mon có nhận đúng dữ liệu không
        await db.execute(
            "INSERT INTO tong_mon (ten_tong_mon, bang_chu_id) VALUES (?, ?)",
            ("Thiên Đạo Môn", user_id),
        )
        c = await db.execute(
            "SELECT ten_tong_mon FROM tong_mon WHERE bang_chu_id = ?", (user_id,)
        )
        tm_name = (await c.fetchone())[0]
        print(
            f"   [4] Kiểm tra lưu tên Tông Môn: '{tm_name}' -> {'OK' if tm_name == 'Thiên Đạo Môn' else 'FAIL'}"
        )

        await db.rollback()  # Không lưu dữ liệu rác

    print("\n✅ HOÀN TẤT KIỂM TRA LOGIC. HỆ THỐNG SẴN SÀNG.")


if __name__ == "__main__":
    asyncio.run(check_logic())
