import sqlite3
import json


def create_database():
    conn = sqlite3.connect("tu_tien.db")
    cursor = conn.cursor()

    print("Bắt đầu tái tạo Không Gian - Thiết lập Ma Trận Dữ Liệu V4 GOLD FULL...")

    # --- TẠO BẢNG ---
    # Bảng Players (Đã bổ sung Sinh Lực, Dao Hiệu, và các mốc thời gian hồi phục)
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS players (
            user_id TEXT PRIMARY KEY, 
            canh_gioi_id INTEGER DEFAULT 1, 
            tu_vi INTEGER DEFAULT 0, 
            linh_thach INTEGER DEFAULT 0, 
            the_luc INTEGER DEFAULT 100, 
            sinh_luc INTEGER DEFAULT 100,
            luc_chien_goc INTEGER DEFAULT 10, 
            tong_mon_id INTEGER, 
            dao_lu_id TEXT,
            dao_hieu TEXT,
            last_the_luc_restore INTEGER DEFAULT 0,
            last_sinh_luc_restore INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 0
        )"""
    )

    # Bảng Cooldowns
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS cooldowns (user_id TEXT, command_name TEXT, last_used TIMESTAMP, PRIMARY KEY (user_id, command_name))"""
    )

    # Bảng Item Master
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS item_master (item_id INTEGER PRIMARY KEY AUTOINCREMENT, ten_vat_pham TEXT, loai_vat_pham TEXT, pham_cap INTEGER, chi_so_buff INTEGER, mo_ta TEXT)"""
    )

    # Bảng Inventory
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS inventory (user_id TEXT, item_id INTEGER, so_luong INTEGER DEFAULT 1, trang_thai TEXT DEFAULT 'trong_tui', PRIMARY KEY (user_id, item_id))"""
    )

    # Bảng Marketplace (Chợ Đen)
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS market_listings (listing_id INTEGER PRIMARY KEY AUTOINCREMENT, seller_id TEXT, item_id INTEGER, so_luong INTEGER, gia_ban INTEGER, thoi_gian_het_han TIMESTAMP)"""
    )

    # Bảng Cảnh Giới
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS realms_master (canh_gioi_id INTEGER PRIMARY KEY, ten_canh_gioi TEXT, tu_vi_can_thiet INTEGER, ti_le_thanh_cong REAL)"""
    )

    # Bảng Yêu Thú
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS boss_monster_master (monster_id INTEGER PRIMARY KEY AUTOINCREMENT, ten_quai TEXT, canh_gioi_yeu_cau INTEGER, luc_chien_min INTEGER, luc_chien_max INTEGER, loot_table TEXT)"""
    )

    # Bảng Tông Môn
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS tong_mon (tong_mon_id INTEGER PRIMARY KEY AUTOINCREMENT, ten_tong_mon TEXT, bang_chu_id TEXT, linh_thach_quy INTEGER DEFAULT 0, cap_do INTEGER DEFAULT 1)"""
    )

    # --- HỆ THỐNG CÔNG PHÁP (MỚI V4) ---
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS skills_master (
            skill_id INTEGER PRIMARY KEY, 
            name TEXT, 
            element TEXT, 
            base_multiplier REAL, 
            stamina_cost INTEGER
        )"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS player_skills (
            user_id TEXT, 
            skill_id INTEGER, 
            level INTEGER DEFAULT 1, 
            PRIMARY KEY (user_id, skill_id)
        )"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS player_equipped_skills (
            user_id TEXT, 
            slot INTEGER, 
            skill_id INTEGER, 
            PRIMARY KEY (user_id, slot)
        )"""
    )

    # --- NHIỆM VỤ ---
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS daily_quests (quest_id INTEGER PRIMARY KEY, description TEXT, goal_type TEXT, goal_value INTEGER, reward_lt INTEGER, reward_tv INTEGER)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS player_quests (user_id TEXT, quest_id INTEGER, current_progress INTEGER DEFAULT 0, last_completed_date TEXT, PRIMARY KEY (user_id, quest_id))"""
    )

    # Bảng Đấu Giá
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS auctions (
            auction_id INTEGER PRIMARY KEY AUTOINCREMENT, 
            seller_id TEXT, 
            item_id INTEGER, 
            so_luong INTEGER, 
            current_bid INTEGER, 
            buyout_price INTEGER DEFAULT 0,
            highest_bidder_id TEXT, 
            end_time TIMESTAMP
        )"""
    )

    # Xóa dữ liệu cũ của các bảng Metadata để Seed lại (Giữ lại data người chơi)
    cursor.executescript(
        """
        DELETE FROM realms_master;
        DELETE FROM item_master;
        DELETE FROM boss_monster_master;
        DELETE FROM daily_quests;
        DELETE FROM skills_master;
    """
    )

    # ==========================================
    # 1. HỆ THỐNG CẢNH GIỚI (24 Cảnh Giới)
    # ==========================================
    realms_data = [
        (1, "Luyện Khí Sơ Kỳ", 0, 1.0),
        (2, "Luyện Khí Trung Kỳ", 200, 1.0),
        (3, "Luyện Khí Hậu Kỳ", 600, 1.0),
        (4, "Trúc Cơ Sơ Kỳ", 1500, 0.9),
        (5, "Trúc Cơ Trung Kỳ", 3000, 0.85),
        (6, "Trúc Cơ Hậu Kỳ", 5000, 0.8),
        (7, "Kim Đan Sơ Kỳ", 12000, 0.75),
        (8, "Kim Đan Trung Kỳ", 20000, 0.7),
        (9, "Kim Đan Hậu Kỳ", 35000, 0.65),
        (10, "Nguyên Anh Sơ Kỳ", 80000, 0.6),
        (11, "Nguyên Anh Trung Kỳ", 150000, 0.55),
        (12, "Nguyên Anh Hậu Kỳ", 250000, 0.5),
        (13, "Hóa Thần Sơ Kỳ", 600000, 0.45),
        (14, "Hóa Thần Trung Kỳ", 1200000, 0.4),
        (15, "Hóa Thần Hậu Kỳ", 2500000, 0.35),
        (16, "Luyện Hư Sơ Kỳ", 8000000, 0.3),
        (17, "Luyện Hư Trung Kỳ", 15000000, 0.25),
        (18, "Luyện Hư Hậu Kỳ", 30000000, 0.2),
        (19, "Hợp Thể Sơ Kỳ", 100000000, 0.15),
        (20, "Hợp Thể Trung Kỳ", 250000000, 0.1),
        (21, "Hợp Thể Hậu Kỳ", 600000000, 0.08),
        (22, "Đại Thừa Sơ Kỳ", 2000000000, 0.05),
        (23, "Đại Thừa Trung Kỳ", 5000000000, 0.03),
        (24, "Đại Thừa Hậu Kỳ", 10000000000, 0.01),
    ]
    cursor.executemany("INSERT INTO realms_master VALUES (?, ?, ?, ?)", realms_data)

    # ==========================================
    # 2. HỆ THỐNG VẬT PHẨM (Đan, Pháp Bảo, Nguyên Liệu, Bí Kíp)
    # ==========================================
    items_data = [
        # --- 10 ĐAN DƯỢC (ID: 101-110) ---
        (101, "Huyết Khí Đan", "dan_duoc", 1, 20, "Hồi 20 Thể Lực."),
        (102, "Tụ Khí Đan", "dan_duoc", 1, 50, "Tăng 50 Tu Vi ngay lập tức."),
        (103, "Trúc Cơ Đan", "dan_duoc", 2, 0, "Hỗ trợ đột phá Trúc Cơ."),
        (104, "Bồi Nguyên Đan", "dan_duoc", 2, 500, "Tăng 500 Tu Vi."),
        (105, "Kết Đan Đan", "dan_duoc", 3, 0, "Hỗ trợ ngưng kết Kim Đan."),
        (106, "Đại Hoàn Đan", "dan_duoc", 3, 3000, "Tăng 3000 Tu Vi."),
        (107, "Hóa Anh Đan", "dan_duoc", 4, 0, "Hỗ trợ đột phá Nguyên Anh."),
        (108, "Thiên Đạo Đan", "dan_duoc", 4, 50000, "Tăng 50000 Tu Vi."),
        (109, "Phá Giới Đan", "dan_duoc", 5, 0, "Tăng tỷ lệ đột phá lớn."),
        (110, "Hoàn Hồn Đan", "dan_duoc", 5, 100, "Bảo vệ mạng khi độ kiếp."),
        # --- PHÁP BẢO (ID: 201-230) ---
        (201, "Mộc Kiếm", "phap_bao", 1, 30, "Kiếm gỗ cơ bản."),
        (213, "Tử Lôi Kiếm", "phap_bao", 3, 6000, "Kiếm có sấm chớp."),
        (230, "Thái Cực Đồ", "phap_bao", 5, 8000000, "Thần khí chí tôn."),
        # --- NGUYÊN LIỆU (ID: 301-320) ---
        (301, "Cỏ Dại", "nguyen_lieu", 1, 0, ""),
        (303, "Linh Thảo", "nguyen_lieu", 1, 0, ""),
        # --- 10 BÍ KÍP CÔNG PHÁP (ID: 401-410) --- (MỚI)
        (401, "Bí Kíp: Hỏa Cầu Thuật", "skill_book", 1, 0, "Lĩnh ngộ Hỏa Cầu Thuật."),
        (402, "Bí Kíp: Thủy Tiễn", "skill_book", 1, 0, "Lĩnh ngộ Thủy Tiễn."),
        (403, "Bí Kíp: Lôi Xà", "skill_book", 2, 0, "Lĩnh ngộ Lôi Xà."),
        (404, "Bí Kíp: Phong Đao", "skill_book", 2, 0, "Lĩnh ngộ Phong Đao."),
        (
            405,
            "Bí Kíp: Kim Quang Chưởng",
            "skill_book",
            3,
            0,
            "Lĩnh ngộ Kim Quang Chưởng.",
        ),
        (406, "Bí Kíp: Thổ Độn", "skill_book", 3, 0, "Lĩnh ngộ Thổ Độn."),
        (
            407,
            "Bí Kíp: Băng Phong Trảm",
            "skill_book",
            4,
            0,
            "Lĩnh ngộ Băng Phong Trảm.",
        ),
        (408, "Bí Kíp: Thiên Hỏa Phần", "skill_book", 4, 0, "Lĩnh ngộ Thiên Hỏa Phần."),
        (409, "Bí Kíp: Hư Không Quyết", "skill_book", 5, 0, "Lĩnh ngộ Hư Không Quyết."),
        (410, "Bí Kíp: Thái Cực Kiếm", "skill_book", 5, 0, "Lĩnh ngộ Thái Cực Kiếm."),
    ]
    cursor.executemany(
        "INSERT INTO item_master (item_id, ten_vat_pham, loai_vat_pham, pham_cap, chi_so_buff, mo_ta) VALUES (?, ?, ?, ?, ?, ?)",
        items_data,
    )

    # ==========================================
    # 3. HỆ THỐNG CÔNG PHÁP TRONG TRẬN (10 Kỹ năng)
    # ==========================================
    skills_data = [
        (1, "Hỏa Cầu Thuật", "Hỏa", 1.2, 5),
        (2, "Thủy Tiễn", "Thủy", 1.1, 3),
        (3, "Lôi Xà", "Lôi", 1.8, 10),
        (4, "Phong Đao", "Phong", 1.5, 7),
        (5, "Kim Quang Chưởng", "Kim", 2.2, 15),
        (6, "Thổ Độn", "Thổ", 1.0, 5),
        (7, "Băng Phong Trảm", "Băng", 2.8, 20),
        (8, "Thiên Hỏa Phần", "Hỏa", 3.5, 30),
        (9, "Hư Không Quyết", "Không", 4.5, 50),
        (10, "Thái Cực Kiếm", "Vô", 6.0, 80),
    ]
    cursor.executemany("INSERT INTO skills_master VALUES (?, ?, ?, ?, ?)", skills_data)

    # ==========================================
    # 4. HỆ THỐNG YÊU THÚ & BOSS (Tối giản cho nhanh)
    # ==========================================
    bosses_data = [
        (1, "Thỏ Con Điên Cuồng", 1, 10, 50, json.dumps({"301": 50, "401": 5})),
        (
            12,
            "Cửu Anh Yêu Tướng",
            12,
            300000,
            500000,
            json.dumps({"316": 20, "405": 2}),
        ),
        (
            24,
            "Thiên Đạo Ý Chí",
            24,
            4000000000,
            8000000000,
            json.dumps({"230": 1, "410": 1}),
        ),
    ]
    cursor.executemany(
        "INSERT INTO boss_monster_master (monster_id, ten_quai, canh_gioi_yeu_cau, luc_chien_min, luc_chien_max, loot_table) VALUES (?, ?, ?, ?, ?, ?)",
        bosses_data,
    )

    # ==========================================
    # 5. HỆ THỐNG NHIỆM VỤ
    # ==========================================
    quests_data = [
        (1, "Tu luyện 5 lần", "tuluyen", 5, 200, 100),
        (2, "Săn 3 Yêu thú", "sanboss", 3, 500, 300),
        (3, "Luyện đan 1 lần", "luyendan", 1, 300, 150),
        (6, "Chuyển tiền đạo hữu", "chuyentien", 1, 100, 50),
    ]
    cursor.executemany(
        "INSERT INTO daily_quests VALUES (?, ?, ?, ?, ?, ?)", quests_data
    )

    # --- TỐI ƯU HÓA (INDEX) ---
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_inventory_user ON inventory(user_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_player_skills_user ON player_skills(user_id)"
    )

    conn.commit()
    conn.close()
    print("Hoàn tất! CSDL V4 GOLD FULL đã sẵn sàng.")


if __name__ == "__main__":
    create_database()
