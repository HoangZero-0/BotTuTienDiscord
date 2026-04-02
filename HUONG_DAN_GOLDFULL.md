# 📊 DANH MỤC LỆNH & LUỒNG HOẠT ĐỘNG BOT TU TIÊN V4 (GOLD FULL)

#### 1. Bot Thiên Đạo (29 Lệnh - Prefix: !)

| Nhóm Lệnh       | Lệnh Chính    | Cách dùng (Syntax)          | Cooldown    | Chi phí        | Mô tả                                            |
| :-------------- | :------------ | :-------------------------- | :---------- | :------------- | :----------------------------------------------- |
| **Tu Hành**     | `!tuluyen`    | `!tuluyen`                  | **3 giây**  | **2 Thể Lực**  | Nhận Tu Vi & Lực chiến. Buff x2 nếu có Đạo lữ.   |
|                 | `!dotpha`     | `!dotpha`                   | 30 giây     | 0              | Đột phá cảnh giới (66 tầng). Thất bại mất TV/LC. |
|                 | `!doituvi`    | `!doituvi <LT>`             | 3 giây      | LT             | Đổi Linh thạch lấy Tu vi (1 LT = 10 TV).         |
| **Chinh Phạt**  | `!sanboss`    | `!sanboss`                  | **5 giây**  | **3 Thể Lực**  | Săn yêu thú kiếm Linh thạch, vật liệu & bí kíp.  |
|                 | `!bicanh`     | `!bicanh`                   | **10 giây** | **10 Thể Lực** | Thám hiểm không gian ảo, tìm kỳ ngộ cực lớn.     |
|                 | `!chemboss`   | `!chemboss`                 | **3 giây**  | **1 Thể Lực**  | Tham gia trảm Boss Thế Giới đang xuất hiện.      |
|                 | `!thachdau`   | `!thachdau @Tag`            | 30 giây     | 0              | PK/PVP Turn-based với đạo hữu khác.              |
| **Thông Tin**   | `!me`         | `!me`                       | 3 giây      | 0              | Xem Hồ sơ: TV, HP, TL, LC, Cảnh giới, Đạo lữ.    |
|                 | `!tuido`      | `!tuido`                    | 5 giây      | 0              | Xem túi đồ: Pháp bảo, đan dược, nguyên liệu.     |
|                 | `!top`        | `!top [loai]`               | 5 giây      | 0              | Bảng xếp hạng cao thủ toàn giới.                 |
| **Giao Thương** | `!chuyentien` | `!chuyentien @Tag <LT>`     | 10 giây     | 10% Thuế       | Chuyển tiền cho người chơi khác.                 |
|                 | `!giaodich`   | `!giaodich @Tag <ID> <Giá>` | 20 giây     | -              | Bán đồ trực tiếp cho người chơi cụ thể.          |
|                 | `!choden`     | `!choden`                   | 10 giây     | -              | Xem Market toàn server.                          |
|                 | `!ban`        | `!ban <ID> <Giá>`           | 10 giây     | -              | Treo đồ lên Market.                              |
|                 | `!daugia`     | `!daugia <ID> <Giá>`        | 30 giây     | 10% Thuế       | Đưa vật phẩm lên sàn Đấu Giá.                    |
|                 | `!bid`        | `!bid <ID> <Giá>`           | 5 giây      | -              | Đấu thầu hoặc Mua đứt bảo vật.                   |
| **Xã Hội**      | `!songtu`     | `!songtu @Tag`              | 30 giây     | -              | Kết duyên Đạo lữ (Buff x2 Tu luyện).             |
|                 | `!lapphai`    | `!lapphai <Tên>`            | 60 giây     | 50.000 LT      | Thành lập Tông môn.                              |
|                 | `!moiphai`    | `!moiphai @Tag`             | 15 giây     | -              | Mời thành viên vào Tông môn.                     |
|                 | `!roiphai`    | `!roiphai`                  | 30 giây     | -              | Rời khỏi tông môn hiện tại.                      |
| **Công Pháp**   | `!hoc`        | `!hoc <ID>`                 | 5 giây      | -              | Học kỹ năng từ bí kíp.                           |
|                 | `!congphap`   | `!congphap`                 | 5 giây      | -              | Quản lý & Trang bị kỹ năng.                      |

#### 2. Bot Thương Nhân (Prefix: ?)

| Lệnh Chính  | Cooldown | Mô tả                            |
| :---------- | :------- | :------------------------------- |
| `?shop`     | 5 giây   | Gọi thương nhân giới thiệu hàng. |
| `?buy <ID>` | 5 giây   | Mua vật phẩm từ thương nhân.     |

---

### ⚙️ HỆ THỐNG TỰ ĐỘNG (AUTOMATION)

1. **Hồi Thể Lực (Auto)**: Mỗi **5 Phút** hồi **+2 Thể Lực** (Max 120).
2. **Hồi Sinh Lực (Auto)**: Hồi **1% HP mỗi giây** (Online & Offline).
3. **Cơ Duyên Rớt Tiền**: Mỗi **30 Phút** rớt Linh thạch, nhặt bằng `!nhat`.
4. **World Boss**: Xuất hiện mỗi **2 Giờ**.
5. **Flash Sale**: Chợ đen mở mỗi **3 Giờ**.
6. **Đấu Giá**: Hệ thống tự treo đồ mỗi **1 Phút** (nếu sàn trống). Quét chốt đơn mỗi **10 Phút**.
