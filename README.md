# ⚡ JEV AI — Binance ARB/USDT Trading System

Hệ thống Bot giao dịch định lượng tự động cho cặp **ARB/USDT** trên sàn **Binance**, được điều khiển bởi **Bộ não quyết định Jev AI từ [jevai.org](https://www.jevai.org/) / [TypeSafe AI](https://typesafe.ai/)**.

Hệ thống tích hợp mô hình ra quyết định "System One" siêu tốc (70ms–150ms), cơ chế quản trị rủi ro đa lớp (Dynamic ATR Trailing Stop Loss, Take Profit, Daily Circuit Breaker) và giao diện Web Terminal Dashboard thời gian thực.

---

## 🌟 Điểm Nổi Bật

1. **Bộ não quyết định Jev AI (jevai.org / TypeSafe AI)**:
   - Mô hình ra quyết định định kiểu (**Typed Decisions**) thay vì mô hình sinh chữ thông thường.
   - Nhận diện toàn diện trạng thái thị trường (`state`): Nến OHLCV, EMA Ribbon (9, 21, 50, 200), RSI (14), MACD, Bollinger Bands, ATR (14) và chênh lệch sổ lệnh (Order Book Depth & Flow).
   - Xuất ra hành động tối ưu (`BUY`, `SELL`, `HOLD`) kèm **xác suất chuẩn hóa** (calibrated probabilities $p$) và điểm tự tin.
   - Tích hợp sẵn **Jev Decision Emulator**: Đóng vai trò mô phỏng chuẩn giao thức Jev AI để có thể chạy bot mượt mà ngay cả khi chưa kích hoạt API Key chính thức.

2. **Cơ chế An toàn Vốn & Quản trị Rủi ro (Risk Guardian)**:
   - **Chế độ Paper Trading mặc định**: Giao dịch giả lập với $1,000 USDT ảo để kiểm chứng logic và tỷ lệ thắng trước khi dùng tiền thật.
   - **Dynamic Trailing Stop Loss**: Tự động dời điểm dừng lỗ lên cao khi giá ARB tăng để khóa chặt lợi nhuận.
   - **Ngắt mạch khẩn cấp (Circuit Breaker)**: Tự động dừng bot nếu mức sụt giảm trong ngày (Daily Drawdown) vượt quá 5%.
   - **Nút bấm khẩn cấp (Emergency Close All)**: Thanh lý toàn bộ vị thế chỉ bằng 1 cú click trên Web Terminal.

3. **Giao diện Web Terminal Dashboard**:
   - Biểu đồ nến TradingView thời gian thực cho cặp `BINANCE:ARBUSDT`.
   - Bảng hiển thị trực tiếp quyết định của Jev AI kèm luồng suy nghĩ (Reasoning).
   - Bảng thống kê tài khoản (Tổng tài sản, USDT khả dụng, ARB nắm giữ, Win Rate, Lịch sử giao dịch).
   - WebSocket streaming liên tục độ trễ cực thấp.

4. **Tự động hóa Quy trình**:
   - Tự động nâng phiên bản (`version.py`) theo quy tắc: mỗi lần thêm tính năng hoặc sửa lỗi sẽ tăng patch version (ví dụ: `1.0.0` ➔ `1.0.1`).
   - Tự động commit và đẩy lên GitHub repo `luanewb/jevai`.
   - Tuyệt đối không tự ý nén file zip.

---

## 🔑 Hướng Dẫn Lấy API Key Cho Jev AI (jevai.org)

Bạn có thể cấp quyền cho Jev AI theo 2 cách:

### Cách 1: Đăng ký API chính thức từ TypeSafe AI (Khuyến nghị)
1. Truy cập trang chủ TypeSafe: **[typesafe.ai](https://typesafe.ai)** hoặc **[console.typesafe.ai](https://console.typesafe.ai)**.
2. Nhập Email hoặc đăng nhập bằng Google/GitHub để tham gia Waitlist (hoặc nhận quyền truy cập Console). Thông thường quyền truy cập sẽ được cấp qua email trong vòng 1-2 ngày.
3. Khi vào được Console, chọn mục **API Keys** -> Bấm **Create New Key**.
4. Sao chép API Key (có định dạng `typesafe_...` hoặc `jev_...`) và dán vào file `.env`:
   ```env
   JEV_API_KEY=typesafe_your_api_key_here
   JEV_API_ENDPOINT=https://api.typesafe.ai/v1/systemone
   ```

### Cách 2: Dùng ngay qua OpenRouter / Vercel AI Gateway (Không cần đợi)
1. Đăng ký tài khoản tại **[openrouter.ai](https://openrouter.ai)** và tạo API Key.
2. Cấu hình trong `.env`:
   ```env
   JEV_API_KEY=sk-or-v1-...
   JEV_API_ENDPOINT=https://openrouter.ai/api/v1/chat/completions
   JEV_MODEL=typesafe-ai/jev
   ```

### Cách 3: Chế độ Giả lập Jev-Emulator (Miễn phí 100%)
- Nếu bạn chưa có API Key, bot đã được bật sẵn `JEV_ENABLE_EMULATOR_FALLBACK=true`. Hệ thống sẽ tự động sử dụng bộ giải thuật phân loại System One cục bộ để chạy giao dịch Paper Trading hoàn toàn bình thường mà không cần bất kỳ API Key nào!

---

## 🚀 Hướng Dẫn Cài Đặt & Khởi Chạy

### 1. Kích hoạt môi trường
```powershell
.\.venv\Scripts\activate
```

### 2. Cấu hình file `.env`
Sao chép `.env.example` thành `.env` và điền cấu hình theo nhu cầu:
```env
SYMBOL=ARB/USDT
TRADING_MODE=PAPER
PAPER_INITIAL_BALANCE=1000.0
RISK_PER_TRADE_PERCENT=1.5
MIN_JEV_CONFIDENCE=75
```

### 3. Khởi chạy Bot & Web Terminal
```powershell
python main.py
```
Sau đó mở trình duyệt tại: **`http://127.0.0.1:8080`** để giám sát và điều khiển.

---

## 🔄 Tự Động Hóa Phiên Bản & Đẩy GitHub

Khi bạn có chỉnh sửa hoặc tính năng mới, chạy lệnh:
```powershell
python scripts/bump_and_push.py "Nội dung cập nhật tính năng"
```
Hệ thống sẽ tự động:
- Nâng số phiên bản (ví dụ `1.0.0` ➔ `1.0.1`)
- Commit vào Git với thông điệp rõ ràng
- Đẩy trực tiếp lên nhánh `main` của repo GitHub: `https://github.com/luanewb/jevai.git`
