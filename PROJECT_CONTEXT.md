# 📖 TÀI LIỆU NGỮ CẢNH DỰ ÁN: BOT TU TIÊN V3 GOLD FINAL (V4)

Tài liệu này được tạo ra để cung cấp toàn bộ ngữ cảnh, cấu trúc thư mục, chức năng của từng file và luồng hoạt động của hệ thống Bot Tu Tiên Discord. Rất hữu ích để cung cấp cho các AI khác khi cần phát triển thêm tính năng, gỡ lỗi hoặc tối ưu hóa.

## 1. TỔNG QUAN DỰ ÁN (OVERVIEW)
- **Tên dự án**: Bot Tu Tiên Discord (V3 Gold Finalized / V4)
- **Cơ sở dữ liệu**: SQLite vô đồng bộ (`aiosqlite`) dùng chế độ WAL giúp chống lock file khi access nhiều.
- **Thư viện chính**: `discord.py`, `aiosqlite`, `python-dotenv`.
- **Cơ chế đặc biệt**: Bot tách làm 2 Client chạy song song trên cùng một runtime bằng `asyncio.gather()`:
  - **Bot Thiên Đạo (Prefix: `!`)**: Bot chính quản lý toàn bộ logic hệ thống tu tiên (cày cuốc, đánh boss, PVP).
  - **Bot Thương Nhân (Prefix: `?`)**: Bot phụ hoạt động như một NPC độc lập, thỉnh thoảng mở chợ đen (`?shop`) và tương tác/chúc mừng khi người chơi độ kiếp thành công.
- **Kênh hoạt động**: Đa số các lệnh chỉ có tác dụng khi gửi trong kênh có tên là `#thế-giới-tu-chân`.

---

## 2. CẤU TRÚC THƯ MỤC VÀ LUỒNG KHỞI CHẠY
```text
📦 BotTuTienDiscord
├── 📜 run_game.py          (Entry point khởi động chính)
├── 📜 main_thiendao.py     (Core của Bot Thiên Đạo)
├── 📜 main_thuongnhan.py   (Core của Bot Thương Nhân)
├── 📜 init_db.py           (Khởi tạo cấu trúc Database và Seed Data)
├── 📜 utils.py             (Các hàm tiện ích dùng chung)
├── 📜 requirements.txt     (Thư viện Python)
├── 📜 HUONG_DAN_GOLDFULL.md(Hướng dẫn cơ bản cho người chơi)
├── 📁 .github/workflows    (Cấu hình CI/CD Deploy lên Katabump)
└── 📁 cogs                 (Thư mục chứa toàn bộ logic / pháp tắc chức năng)
    ├── bang_xep_hang.py
    ├── bi_canh.py
    ├── che_tao.py
    ├── cong_phap.py
    ├── dan_cac.py
    ├── dau_gia.py
    ├── dot_pha.py
    ├── giao_dich.py
    ├── he_thong.py
    ├── nhiem_vu.py
    ├── pvp.py
    ├── san_boss.py
    ├── su_kien.py
    ├── thong_tin.py
    ├── tu_luyen.py
    ├── vat_pham.py
    └── xa_hoi.py
```

### Quá trình khởi động (`run_game.py`):
1. Đọc Tokens từ file bảo mật `.env`.
2. Kiểm tra nếu file `tu_tien.db` chưa tồn tại thì gọi `init_db.py` để tạo CSDL mẫu (Bảng, Cảnh Giới, Vật Phẩm, Boss, Quests,...).
3. Khởi tạo đối tượng `ThienDaoBot` và đăng ký tất cả các Extension/Cogs từ thư mục `cogs/`.
4. Khởi tạo đối tượng `ThuongNhanBot` và đăng ký các lệnh cho bot này.
5. Chạy cả 2 bot song song qua hàm `asyncio.gather()`.

---

## 3. CHỨC NĂNG CÁC TRỤ CỘT CHÍNH (ROOT FILES)

- **`main_thiendao.py`**:
  - Class `ThienDaoBot` kế thừa `commands.Bot`.
  - Hàm `setup_hook`: Tự động Load list 17 file cogs.
  - Xử lý event `on_message`: Giới hạn channel hoạt động (chỉ xử lý lệnh ở kênh `thế-giới-tu-chân`).
  - Hàm `on_command_error`: Xử lý lỗi hệ thống, đặc biệt là cảnh báo Spam/Cooldown (`CommandOnCooldown`) bằng các câu quote nhập vai vui vẻ. Bỏ qua các chuỗi không phải lệnh (`CommandNotFound`).
- **`main_thuongnhan.py`**:
  - Sở hữu Task lặp lại theo thời gian `flash_sale` (tự động thông báo mở chợ đen mỗi 3h).
  - Lắng nghe event `on_message`, theo dõi ID của riêng "Bot Thiên Đạo". Nếu thấy Thiên Đạo thông báo "ĐỘ KIẾP THÀNH CÔNG", tự động phản hồi chúc mừng người chơi và random phát phần thưởng Linh thạch.
  - Cung cấp tính năng `?shop` (random xuất hiện vật phẩm lưu vào cache dictionary) và `?buy` check logic.
- **`init_db.py`**:
  - Xóa table cũ nếu DB cần reset, khởi tạo Schema SQL.
  - Insert Data mồi (Seed Data) cho: 24 Cảnh Giới (đến Đại Thừa), 10 Đan dược, 30 Pháp bảo, 20 Nguyên liệu, 24 Boss tương ứng các cảnh giới, thông số tỷ lệ, Daily Quests.
- **`utils.py`**:
  - `get_db`: Context Manager kết nối DB và kích hoạt PRAGMA WAL.
  - `update_quest_progress`: Hàm kiểm tra / tăng tiến trình hoàn thành nhiệm vụ hàng ngày của user và tự động trả buff thưởng tỷ lệ với Cảnh giới.
  - `update_player_stats`: Logic cập nhật HP/MP dựa trên thời gian trôi qua mỗi lần user gửi lệnh. (HP hồi 1% mỗi giây; Thể lực bị khóa chuyển cho Task Loop).
  - `CleanID`, `CleanInt`: Custom Discord Converters để làm sạch chuỗi input từ người dùng gõ lệnh lỗi (loại bỏ ký tự lạ `#`, `,`, `<>`).

---

## 4. CHI TIẾT CÁC MODULE CHỨC NĂNG (Thư mục `cogs/`)

Hệ thống được thiết kế theo chuẩn mô hình `Cogs` của thư viện `discord.py` nhằm mục đích dễ scale và refactor.

1. **`tu_luyen.py`**: 
   - Lệnh `!tuluyen`: Hút linh khí tu tiên. Cần 2 Thể lực. Random nhận Tu vi, Lực chiến. Có 10% tỷ lệ tẩu hỏa nhập ma sẽ trừ vào Tu vi hoặc rớt hẳn Cảnh giới nếu Tu vi lùi về âm. Nếu có Đạo Lữ thì buff x2 Tu vi nhận được.
   - Lệnh `!doituvi`: Tiêu hao Linh thạch đổi lấy Tu vi, giới hạn số lần mỗi ngày theo cảnh giới. Có sử dụng Discord UI View/Modal để User nhập Đạo Hiệu lúc mới bắt đầu chơi.
2. **`dot_pha.py`**:
   - Lệnh `!dotpha` (hay `!dokiep`): Đột phá lên cảnh giới tiếp theo khi thanh Tu Vi đầy. Tỷ lệ đột phá thành công dựa trên Lực Chiến chuẩn của player kết hợp với % Buff từ đan dược bảo hộ (Hóa Anh Đan, Phá Giới Đan,...). Có tỷ lệ bị "Lôi kiếp" phạt nặng hơn nếu roll trật (Trừ hao HP/CS, hoặc xài Hoàn Hồn Đan giữ tính mạng).
3. **`thong_tin.py`**:
   - Lệnh `!me`: Dựng Profile Tu Sĩ. Cấu trúc gồm: Cảnh giới, Sinh Lực (HP), Thể lực (TL năng lượng), Lực chiến. Sử dụng chuỗi emoji để tạo thanh Progress Bar sinh động thể hiện tỷ lệ %.
4. **`bi_canh.py`**:
   - Lệnh `!bicanh`: Trừ Thể Lực và 2% Linh thạch hiện có để thám hiểm vòng gacha event: Có thể vớ rương vật phẩm, Cơ duyên lớn (buff stat, đồ hiếm), gặp NPC phát tiền hoặc dính bẫy (hao HP/TuVi/Rớt đồ).
5. **`san_boss.py`**:
   - Lệnh `!sanboss`: Chiến đấu vs Boss ngẫu nhiên. Boss spawn hợp lệ với ±3 cảnh giới so với Player. Trận đấu tự động diễn ra theo 3 Round có report text. Dòng code random thuộc tính ẩn (Chí mạng, Tránh né, Phản đòn, Hút máu) trước khi round đấu bắt đầu áp dụng cho cả Boss và User. Roll loot item khi boss ngã.
6. **`vat_pham.py`**:
   - Túi hành trang (`!tuido`): List vật phẩm group theo categories.
   - Trang bị/Dùng (`!use`): Uống đan dược (hồi máu, cưỡng chế đột phá thành công 100%), hoặc trang bị Pháp Bảo (vũ khí) tăng % chiến lực (giới hạn đang là 5 slot).
   - Tháo gỡ (`!thao`): Gỡ pháp bảo về túi.
7. **`bang_xep_hang.py`**:
   - Lệnh `!top [tuvi/linhthach/lucchien/tongmon]`. Query Data sort by DESC limit 10. Tích hợp query Sub-Query lấy thứ hạng tương ứng của người gọi lệnh.
8. **`he_thong.py`**:
   - `recover_stamina`: Task Loop tự động chạy ẩn, recover +2 Thể lực mỗi 5 phút cho toàn bộ Players DB.
   - `!trogiup / !help`: Menu tra cứu lệnh bot cho Newbies.
9. **`xa_hoi.py`**:
   - Song Tu (`!songtu @` / `!lithu`): Yêu cầu đối phương tương tác qua UI Button Yes/No. Hoạt động song tu sẽ buff tốc độ cày `!tuluyen` gấp đôi.
   - Tông Môn (`!lapphai`, `!moiphai @`, `!roiphai`, `!xemphai`): Quản lý tạo phái bằng 50K Linh Thạch, chiêu mộ thủ hạ và check danh sách bang hội.
10. **`giao_dich.py`**:
    - `!chuyentien`: Gửi money trực tiếp, hệ thống cắt phế 10%.
    - `!giaodich`: Trao đổi Item/Pháp bảo với người chơi khác. Yêu cầu Check Validation kĩ lượng 2 bên (Tồn kho, không mặc trên người, người mua đủ tiền) kết hợp Confirm UI Buttons bảo mật thông tin.
11. **`che_tao.py`**:
    - `!danphuong`: Output list các loại công thức ép đan.
    - `!luyendan <id>`: Process hao mòn item theo chuẩn recipe, Tỉ lệ thành công ép đan bị ảnh hưởng bởi chênh lệch đẳng cấp Player vs Item. Thất bại nổ tung lọ đan mất hết hoặc có 40% nhận phế phẩm.
12. **`nhiem_vu.py`**:
    - `!nhiemvu`: Lấy thông tin về bảng nhiệm vụ ngày (từ table `daily_quests`), progress được vẽ qua emoji bar. (Quests trigger completion trong các cogs khác thông qua util script chung).
13. **`dau_gia.py`**:
    - Task ngầm `auction_manager`: Check list item đang ở sàn đấu, khóa hạn, phát item/linh thạch và thông báo cho winner.
    - Task ngầm `system_auction_spawner`: Lâu lâu thả hộp quà boss đấu giá từ "Hệ Thống (Seller=0)".
    - Lệnh người dùng: `!daugialist` (xem sàn), `!daugia` (treo vật), `!bid` (Bỏ giá + xử lý nâng min + tính chống Snipping time giãn ra). Có chức năng "Mua đứt" (Buyout).
14. **`su_kien.py`**:
    - `!chemboss`: Event Boss toàn server rớt xuống mỗi 2H/lần chặn đường. Ghi nhận Damage của ngườ dùng đóng góp thành Log. Phân phát thưởng khi HP chạm 0 theo TOP bảng xếp hạng DPS và trao thưởng Last Hit.
    - `co_duyen`: Trò chơi xổ số, 30 phút một lần ban lộc cho 1 user online ngẫu nhiên.
    - `random_drop`: Hệ thống chat 1 chuỗi tin nhắn rơi quà, người chơi có độ trễ phải reply `!nhat` sớm nhất để ẵm linh thạch.
15. **`dan_cac.py`**:
    - `!dancac`: Tính năng cửa hàng nhanh. Xây dựng giao diện Dropdown (Select Menu UI của Discord) để người dùng chọn mua theo giá cố định.
16. **`cong_phap.py`**:
    - `!hoc`: Chuyển item sách skill vào bảng kỹ năng cá nhân.
    - `!congphap`: Giao diện Select UI cài đặt Slot Skill sử dụng (Max 4 skill trên người) dùng trong đối kháng PVP.
17. **`pvp.py`**:
    - `!thachdau @`: Đấu trường Sinh - Tử. Cơ chế Battle Interaction Buttons.
    - Chờ đối thủ bấm "Accept". Chuyển về màn hình điều khiển.
    - Các bên lựa theo Turn ra đòn từ các slot Skills đã xếp. Dịch thuật thành Log Action diễn hoạ HP trừ trực tiếp trên Messages thay vì update spam tin.
    - Nếu Time out gõ đòn (1 phút) => Xử thua AFK.
    - Player thua bị Penalty tụt 5% kinh nghiệm tu vi chuyển cho Winner.

---

## 6. LƯU Ý CHO AI KHI PHÁT TRIỂN / HOÀN THIỆN
1. **DB Async Flow**: Do dùng `aiosqlite`, mọi method Query DB đều phải khai báo `async with get_db(self.db_path) as db:` và đi kèm `await db.execute(...)`, đừng nhầm với sqlite3 thông thường.
2. **Setup User Ngầm**: Có thể có User mới gõ lệnh mà bảng `players` Database chưa tồn tại. Phải luôn handle trường hợp "User chưa tu luyện" hoặc auto-insert giống lệnh `!tuluyen`.
3. **Missing Schema Note**: Bảng `skills_master` và `player_equipped_skills` có thể đang thiếu Data Seed khởi tạo trong màn dạo đầu `init_db.py`. Nếu AI làm việc với `pvp.py` và `cong_phap.py` hãy lưu ý điều này để thêm Script Insert chuẩn.
4. **Discord UI / Buttons**: Hệ thống lạm dụng nhiều class kế thừa `discord.ui.View` và `discord.ui.Select`. Khi update cần nắm vững event flow của discord `interaction_check` chống leak người thứ 3 bấm ké.

> END OF CONTEXT. Mọi tài nguyên đã sẵn sàng để tích hợp và tham vấn!
