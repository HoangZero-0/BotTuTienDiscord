import sqlite3
import json


def create_database():
    conn = sqlite3.connect("tu_tien.db")
    cursor = conn.cursor()

    print("Bắt đầu tái tạo Không Gian - Thiết lập Ma Trận Dữ Liệu Tiêu Chuẩn...")

    # --- TẠO BẢNG ---
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS players (user_id TEXT PRIMARY KEY, canh_gioi_id INTEGER DEFAULT 1, tu_vi INTEGER DEFAULT 0, linh_thach INTEGER DEFAULT 0, the_luc INTEGER DEFAULT 100, luc_chien_goc INTEGER DEFAULT 10, tong_mon_id INTEGER, dao_lu_id TEXT)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS cooldowns (user_id TEXT, command_name TEXT, last_used TIMESTAMP, PRIMARY KEY (user_id, command_name))"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS item_master (item_id INTEGER PRIMARY KEY AUTOINCREMENT, ten_vat_pham TEXT, loai_vat_pham TEXT, pham_cap INTEGER, chi_so_buff INTEGER, mo_ta TEXT)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS inventory (user_id TEXT, item_id INTEGER, so_luong INTEGER DEFAULT 1, trang_thai TEXT DEFAULT 'trong_tui', PRIMARY KEY (user_id, item_id))"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS market_listings (listing_id INTEGER PRIMARY KEY AUTOINCREMENT, seller_id TEXT, item_id INTEGER, so_luong INTEGER, gia_ban INTEGER, thoi_gian_het_han TIMESTAMP)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS realms_master (canh_gioi_id INTEGER PRIMARY KEY, ten_canh_gioi TEXT, tu_vi_can_thiet INTEGER, ti_le_thanh_cong REAL)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS boss_monster_master (monster_id INTEGER PRIMARY KEY AUTOINCREMENT, ten_quai TEXT, canh_gioi_yeu_cau INTEGER, luc_chien_min INTEGER, luc_chien_max INTEGER, loot_table TEXT)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS tong_mon (tong_mon_id INTEGER PRIMARY KEY AUTOINCREMENT, ten_tong_mon TEXT, bang_chu_id TEXT, linh_thach_quy INTEGER DEFAULT 0, cap_do INTEGER DEFAULT 1)"""
    )

    # --- BẢNG MỚI V2.0 ---
    # Nhiệm vụ hàng ngày
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS daily_quests (quest_id INTEGER PRIMARY KEY, description TEXT, goal_type TEXT, goal_value INTEGER, reward_lt INTEGER, reward_tv INTEGER)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS player_quests (user_id TEXT, quest_id INTEGER, current_progress INTEGER DEFAULT 0, last_completed_date TEXT, PRIMARY KEY (user_id, quest_id))"""
    )

    # Đấu giá
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS auctions (auction_id INTEGER PRIMARY KEY AUTOINCREMENT, seller_id TEXT, item_id INTEGER, so_luong INTEGER, current_bid INTEGER, highest_bidder_id TEXT, end_time TIMESTAMP)"""
    )

    # Xóa dữ liệu cũ
    cursor.executescript(
        """
        DELETE FROM realms_master;
        DELETE FROM item_master;
        DELETE FROM boss_monster_master;
        DELETE FROM daily_quests;
    """
    )

    # ==========================================
    # 1. HỆ THỐNG CẢNH GIỚI (8 Đại Cảnh Giới x 3 Giai Đoạn = 24 Cảnh Giới)
    # ==========================================
    realms_data = [
        # Luyện Khí (Phàm Nhân)
        (1, "Luyện Khí Sơ Kỳ", 0, 1.0),
        (2, "Luyện Khí Trung Kỳ", 200, 1.0),
        (3, "Luyện Khí Hậu Kỳ", 600, 1.0),
        # Trúc Cơ (Sải bước Tu Tiên)
        (4, "Trúc Cơ Sơ Kỳ", 1500, 0.9),
        (5, "Trúc Cơ Trung Kỳ", 3000, 0.85),
        (6, "Trúc Cơ Hậu Kỳ", 5000, 0.8),
        # Kim Đan (Kết Đan)
        (7, "Kim Đan Sơ Kỳ", 12000, 0.75),
        (8, "Kim Đan Trung Kỳ", 20000, 0.7),
        (9, "Kim Đan Hậu Kỳ", 35000, 0.65),
        # Nguyên Anh (Phá Đan Sinh Anh)
        (10, "Nguyên Anh Sơ Kỳ", 80000, 0.6),
        (11, "Nguyên Anh Trung Kỳ", 150000, 0.55),
        (12, "Nguyên Anh Hậu Kỳ", 250000, 0.5),
        # Hóa Thần (Lĩnh ngộ Pháp Tắc)
        (13, "Hóa Thần Sơ Kỳ", 600000, 0.45),
        (14, "Hóa Thần Trung Kỳ", 1200000, 0.4),
        (15, "Hóa Thần Hậu Kỳ", 2500000, 0.35),
        # Luyện Hư (Chưởng khống Không Gian)
        (16, "Luyện Hư Sơ Kỳ", 8000000, 0.3),
        (17, "Luyện Hư Trung Kỳ", 15000000, 0.25),
        (18, "Luyện Hư Hậu Kỳ", 30000000, 0.2),
        # Hợp Thể (Thiên Nhân Hợp Nhất)
        (19, "Hợp Thể Sơ Kỳ", 100000000, 0.15),
        (20, "Hợp Thể Trung Kỳ", 250000000, 0.1),
        (21, "Hợp Thể Hậu Kỳ", 600000000, 0.08),
        # Đại Thừa (Đỉnh phong Nhân giới)
        (22, "Đại Thừa Sơ Kỳ", 2000000000, 0.05),
        (23, "Đại Thừa Trung Kỳ", 5000000000, 0.03),
        (24, "Đại Thừa Hậu Kỳ", 10000000000, 0.01),
    ]
    cursor.executemany("INSERT INTO realms_master VALUES (?, ?, ?, ?)", realms_data)

    # ==========================================
    # 2. HỆ THỐNG VẬT PHẨM (10 Đan, 30 Pháp Bảo, 20 Nguyên Liệu)
    # ==========================================
    items_data = [
        # --- 10 ĐAN DƯỢC (ID: 101-110) ---
        (101, "Huyết Khí Đan", "dan_duoc", 1, 20, "Hồi 20 Thể Lực."),
        (102, "Tụ Khí Đan", "dan_duoc", 1, 50, "Tăng 50 Tu Vi ngay lập tức."),
        (103, "Trúc Cơ Đan", "dan_duoc", 2, 0, "Tăng 15% tỷ lệ đột phá Trúc Cơ."),
        (104, "Bồi Nguyên Đan", "dan_duoc", 2, 500, "Tăng 500 Tu Vi (Trúc Cơ dùng)."),
        (105, "Kết Đan Đan", "dan_duoc", 3, 0, "Tăng 15% tỷ lệ ngưng kết Kim Đan."),
        (106, "Đại Hoàn Đan", "dan_duoc", 3, 3000, "Tăng 3000 Tu Vi (Kim Đan dùng)."),
        (107, "Hóa Anh Đan", "dan_duoc", 4, 0, "Tăng 15% tỷ lệ đột phá Nguyên Anh."),
        (108, "Thiên Đạo Đan", "dan_duoc", 4, 50000, "Tăng 50000 Tu Vi cực mạnh."),
        (
            109,
            "Phá Giới Đan",
            "dan_duoc",
            5,
            0,
            "Tăng 20% tỷ lệ đột phá các cảnh giới lớn (Từ Hóa Thần trở lên).",
        ),
        (
            110,
            "Cửu Chuyển Hoàn Hồn Đan",
            "dan_duoc",
            5,
            100,
            "Bảo vệ một mạng khi Độ Kiếp thất bại.",
        ),
        # --- 30 PHÁP BẢO (ID: 201-230) Tăng dần từ Phàm đến Chí Tôn ---
        # Phàm Khí (Luyện Khí)
        (201, "Mộc Kiếm", "phap_bao", 1, 30, "Kiếm gỗ cho người mới."),
        (202, "Thiết Đao", "phap_bao", 1, 50, "Đao rèn bằng sắt thường."),
        (203, "Thanh Đồng Nhẫn", "phap_bao", 1, 80, "Nhẫn đồng xanh."),
        (204, "Tế Y", "phap_bao", 1, 100, "Áo vải gai."),
        (205, "Lang Nha Bổng", "phap_bao", 1, 150, "Gậy răng sói."),
        (206, "Bách Luyện Kiếm", "phap_bao", 1, 250, "Kiếm được rèn 100 lần."),
        # Linh Khí (Trúc Cơ)
        (207, "Hỏa Vân Kiếm", "phap_bao", 2, 600, "Kiếm tỏa hỏa khí."),
        (208, "Băng Phách Châm", "phap_bao", 2, 800, "Kim châm làm từ hàn băng."),
        (209, "Huyền Thiết Trọng Kiếm", "phap_bao", 2, 1200, "Kiếm nặng ngàn cân."),
        (210, "Ngọc Bội Bình An", "phap_bao", 2, 1500, "Ngọc bội tĩnh tâm."),
        (211, "Thanh Phong Lý", "phap_bao", 2, 2000, "Giày chạy như gió."),
        (212, "Xích Xà Biên", "phap_bao", 2, 2800, "Roi da rắn đỏ."),
        # Tiên Khí (Kim Đan - Nguyên Anh)
        (213, "Tử Lôi Kiếm", "phap_bao", 3, 6000, "Kiếm gọi sấm chớp."),
        (214, "Phi Tinh Nộ Cung", "phap_bao", 3, 9000, "Cung bắn ra sao băng."),
        (215, "Huyền Vũ Giáp", "phap_bao", 3, 12000, "Giáp mang sức mạnh Huyền Vũ."),
        (216, "Linh Lũng Tháp", "phap_bao", 3, 18000, "Tháp nhốt yêu thú."),
        (217, "Nhật Nguyệt Song Đao", "phap_bao", 3, 25000, "Song đao chứa âm dương."),
        (218, "Cửu Long Trượng", "phap_bao", 3, 35000, "Pháp trượng chín rồng."),
        # Thần Khí (Hóa Thần - Luyện Hư)
        (219, "Tru Tiên Kiếm", "phap_bao", 4, 80000, "Sát khí diệt tiên."),
        (220, "Đả Thần Tiên", "phap_bao", 4, 120000, "Đánh thẳng vào nguyên thần."),
        (221, "Lưu Ly Tịnh Hỏa Đăng", "phap_bao", 4, 180000, "Đèn chứa thiên hỏa."),
        (
            222,
            "Phấn Tái Càn Khôn Đỉnh",
            "phap_bao",
            4,
            250000,
            "Đỉnh nung chảy càn khôn.",
        ),
        (223, "Lạc Mặc Thần Tán", "phap_bao", 4, 380000, "Ô che chắn vạn vật."),
        (224, "Hư Không Kính", "phap_bao", 4, 500000, "Gương chiếu rọi hư không."),
        # Chí Tôn Thần Khí (Hợp Thể - Đại Thừa)
        (225, "Bàn Cổ Phủ", "phap_bao", 5, 1200000, "Rìu khai thiên lập địa."),
        (226, "Đông Hoàng Chung", "phap_bao", 5, 1800000, "Chuông trấn áp vạn cổ."),
        (227, "Hỗn Độn Kiếm", "phap_bao", 5, 2500000, "Kiếm chém đứt nhân quả."),
        (228, "Tạo Hóa Ngọc Điệp", "phap_bao", 5, 3500000, "Chứa đựng 3000 đại đạo."),
        (229, "Luân Hồi Kính", "phap_bao", 5, 5000000, "Kiểm soát luân hồi sinh tử."),
        (230, "Thái Cực Đồ", "phap_bao", 5, 8000000, "Đồ quyển vô cực vô tận."),
        # --- 20 NGUYÊN LIỆU (ID: 301-320) ---
        (301, "Cỏ Dại", "nguyen_lieu", 1, 0, ""),
        (302, "Quặng Sắt", "nguyen_lieu", 1, 0, ""),
        (303, "Linh Thảo", "nguyen_lieu", 1, 0, ""),
        (304, "Mảnh Vỡ Vũ Khí", "nguyen_lieu", 1, 0, ""),
        (305, "Huyết Liên Hoa", "nguyen_lieu", 2, 0, ""),
        (306, "Huyền Thiết", "nguyen_lieu", 2, 0, ""),
        (307, "Yêu Đan Phàm Cấp", "nguyen_lieu", 2, 0, ""),
        (308, "Tinh Nhũ Dịch", "nguyen_lieu", 2, 0, ""),
        (309, "Vảy Hỏa Long", "nguyen_lieu", 3, 0, ""),
        (310, "Thiên Thạch Tinh Kim", "nguyen_lieu", 3, 0, ""),
        (311, "Yêu Đan Linh Cấp", "nguyen_lieu", 3, 0, ""),
        (312, "Hồn Phách Dã Thú", "nguyen_lieu", 3, 0, ""),
        (313, "Vạn Năm Hàn Băng", "nguyen_lieu", 4, 0, ""),
        (314, "Cửu Cực Lôi Thạch", "nguyen_lieu", 4, 0, ""),
        (315, "Yêu Đan Vương Giả", "nguyen_lieu", 4, 0, ""),
        (316, "Tinh Hoa Nhật Nguyệt", "nguyen_lieu", 4, 0, ""),
        (317, "Hỗn Độn Chi Khí", "nguyen_lieu", 5, 0, ""),
        (318, "Nước Mắt Thiên Đạo", "nguyen_lieu", 5, 0, ""),
        (319, "Mảnh Vỡ Thế Giới", "nguyen_lieu", 5, 0, ""),
        (320, "Yêu Đan Hoàng Giả", "nguyen_lieu", 5, 0, ""),
    ]
    cursor.executemany(
        "INSERT INTO item_master (item_id, ten_vat_pham, loai_vat_pham, pham_cap, chi_so_buff, mo_ta) VALUES (?, ?, ?, ?, ?, ?)",
        items_data,
    )

    # ==========================================
    # 3. HỆ THỐNG YÊU THÚ (24 Yêu thú tương ứng 24 Cảnh giới)
    # Lực chiến tăng lũy tiến để tạo độ khó
    # ==========================================
    bosses_data = [
        # Yêu thú Luyện Khí (1-3)
        (1, "Thỏ Con Điên Cuồng", 1, 10, 50, json.dumps({"301": 50, "302": 30})),
        (2, "Dã Trư Đột Biến", 2, 60, 150, json.dumps({"302": 50, "304": 20})),
        (3, "Hắc Mao Lang", 3, 180, 400, json.dumps({"303": 40, "101": 10})),
        # Yêu thú Trúc Cơ (4-6)
        (4, "Thiết Tý Cự Oanh", 4, 500, 1000, json.dumps({"307": 30, "207": 5})),
        (5, "Xích Luyện Xà", 5, 1200, 2500, json.dumps({"305": 40, "104": 15})),
        (6, "Độc Nhãn Cự Hùng", 6, 3000, 6000, json.dumps({"306": 35, "209": 8})),
        # Yêu thú Kim Đan (7-9)
        (7, "Bích Thủy Giải", 7, 8000, 15000, json.dumps({"311": 30, "105": 10})),
        (8, "Hỏa Lân Thú", 8, 18000, 30000, json.dumps({"309": 25, "213": 5})),
        (9, "Phong Lôi Hạt", 9, 35000, 60000, json.dumps({"310": 30, "214": 4})),
        # Yêu thú Nguyên Anh (10-12)
        (10, "Lục Sí Thiên Đô", 10, 70000, 120000, json.dumps({"312": 20, "107": 10})),
        (
            11,
            "Minh Hỏa Cốt Long",
            11,
            150000,
            250000,
            json.dumps({"315": 15, "215": 3}),
        ),
        (
            12,
            "Cửu Anh Yêu Tướng",
            12,
            300000,
            500000,
            json.dumps({"316": 20, "217": 2}),
        ),
        # Yêu thú Hóa Thần (13-15)
        (13, "Bát Tý Ma Viên", 13, 600000, 1000000, json.dumps({"313": 25, "109": 8})),
        (
            14,
            "Hấp Huyết Yêu Mẫu",
            14,
            1200000,
            2000000,
            json.dumps({"314": 20, "221": 3}),
        ),
        (
            15,
            "Kim Tôn Sư Vương",
            15,
            2500000,
            4000000,
            json.dumps({"320": 15, "223": 2}),
        ),
        # Yêu thú Luyện Hư (16-18)
        (
            16,
            "Hư Không Ác Mộng",
            16,
            5000000,
            8000000,
            json.dumps({"317": 20, "108": 10}),
        ),
        (
            17,
            "Tinh Trần Cự Thú",
            17,
            10000000,
            18000000,
            json.dumps({"319": 15, "224": 2}),
        ),
        (
            18,
            "Nuốt Thiên Thôn Phệ Thú",
            18,
            20000000,
            35000000,
            json.dumps({"318": 10, "220": 1}),
        ),
        # Yêu thú Hợp Thể (19-21)
        (
            19,
            "Đại Đạo Phân Thân",
            19,
            45000000,
            80000000,
            json.dumps({"317": 30, "225": 1}),
        ),
        (
            20,
            "Hỗn Độn Ma Thần",
            20,
            100000000,
            180000000,
            json.dumps({"318": 20, "227": 1}),
        ),
        (
            21,
            "Cửu U Minh Vương",
            21,
            250000000,
            400000000,
            json.dumps({"319": 15, "226": 1}),
        ),
        # Yêu thú Đại Thừa (22-24)
        (
            22,
            "Thiên Phạt Chi Nhãn",
            22,
            600000000,
            1000000000,
            json.dumps({"110": 50, "320": 30}),
        ),
        (
            23,
            "Sáng Thế Tổ Long",
            23,
            1500000000,
            2500000000,
            json.dumps({"318": 40, "229": 1}),
        ),
        (
            24,
            "Thiên Đạo Ý Chí (Final Boss)",
            24,
            4000000000,
            8000000000,
            json.dumps({"230": 1, "228": 1}),
        ),
    ]
    cursor.executemany(
        "INSERT INTO boss_monster_master (monster_id, ten_quai, canh_gioi_yeu_cau, luc_chien_min, luc_chien_max, loot_table) VALUES (?, ?, ?, ?, ?, ?)",
        bosses_data,
    )

    # ==========================================
    # 4. HỆ THỐNG NHIỆM VỤ MẪU
    # ==========================================
    quests_data = [
        (1, "Tu luyện 5 lần", "tuluyen", 5, 200, 100),
        (2, "Săn 3 Yêu thú", "sanboss", 3, 500, 300),
        (3, "Luyện đan 1 lần", "luyendan", 1, 300, 150),
        (4, "Mua đồ tại shop", "buy_shop", 1, 100, 50),
        (5, "Tham gia Bí cảnh 2 lần", "bicanh", 2, 400, 200),
        (6, "Chuyển tiền đạo hữu 1 lần", "chuyentien", 1, 100, 50),
        (7, "Đặt thầu đấu giá 1 lần", "bid_auction", 1, 200, 100),
        (8, "Đột phá cảnh giới 1 lần", "dokiep", 1, 1000, 500),
        (9, "Săn Boss Thế Giới 1 lần", "worldboss", 1, 2000, 1000),
    ]
    cursor.executemany(
        "INSERT INTO daily_quests VALUES (?, ?, ?, ?, ?, ?)", quests_data
    )

    # --- TỐI ƯU HÓA (INDEX) ---
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_inventory_user ON inventory(user_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_player_quests_user ON player_quests(user_id)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_auctions_time ON auctions(end_time)")

    conn.commit()
    conn.close()
    print("Hoàn tất! CSDL tu_tien.db đã hội tụ đầy đủ Đại Đạo Pháp Tắc.")


if __name__ == "__main__":
    create_database()
