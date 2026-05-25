# Bamboo Nissin Kiosk

Bamboo Nissin Kiosk là hệ thống kiosk tiếp đón và đăng ký khách dùng cho sự kiện, showroom, văn phòng hoặc khu vực lễ tân. Dự án tập trung vào mô hình offline-first: kiosk vẫn có thể ghi nhận thông tin tại chỗ, lưu dữ liệu cục bộ và chỉ đồng bộ ra hệ thống ngoài khi được cấu hình.

## Tính năng chính

- Quét QR để check-in hoặc truy xuất hồ sơ đăng ký.
- Quét danh thiếp và trích xuất thông tin như họ tên, công ty, chức vụ, email, số điện thoại, địa chỉ.
- Quét CCCD bằng QR/OCR và lưu hồ sơ định danh.
- Chụp khuôn mặt, phát hiện người dùng trước kiosk và hỗ trợ nhận diện khách quay lại.
- Dashboard quản trị để xem, tìm kiếm, chỉnh sửa, xóa và xuất dữ liệu.
- Quản lý lịch hẹn theo ngày/tháng, có thể bật overlay đặt lịch trên kiosk.
- Hỏi đáp bằng giọng nói dựa trên RAG v2, Ollama và TTS.
- Phát âm thanh hướng dẫn bằng tiếng Việt/tiếng Nhật.
- In QR đăng ký qua module `qr_printing`.
- Hỗ trợ xử lý nền bằng Redis worker và Swift worker trong các cấu hình triển khai nâng cao.

## Công nghệ sử dụng

- Backend: Python, Flask, Flask-CORS.
- Frontend: HTML, CSS, JavaScript thuần.
- Database: SQLite, tự khởi tạo trong `database/registrations.db`.
- OCR/AI: RapidOCR ONNX Runtime, YOLOv8, SCRFD/face embedding, OpenCV.
- QR: Nimiq QR Scanner phía trình duyệt, thư viện `qrcode` phía server.
- Export: OpenPyXL, Pandas.
- RAG/Q&A: ChromaDB, Ollama, gTTS.
- Worker tùy chọn: Redis, Swift.

## Cấu trúc thư mục

```text
.
├── application.py          # Entry point Flask
├── app_config.py           # Cấu hình runtime, OCR, YOLO, Redis, SQLite
├── env_settings.py         # Đọc/ghi một số cấu hình trong .env
├── card/                   # Xử lý danh thiếp, OCR, YOLO card
├── face/                   # Phát hiện và nhận diện khuôn mặt
├── routes/                 # Flask blueprints/API routes
├── services/               # Business logic cho registration, OCR, CCCD, face, Q&A
├── database/               # SQLite schema và repository
├── qr_printing/            # Sinh và in QR
├── rag/                    # Dữ liệu/cache/eval cho RAG
├── static/                 # CSS, JS, âm thanh, vendor browser libraries
├── templates/              # Giao diện kiosk, login, dashboard, Q&A
├── workers_swift/          # Worker Swift cho OCR/face ở môi trường hỗ trợ
├── scripts/                # Script runtime, RAG, đánh giá
├── docs/                   # Tài liệu nghiệp vụ/kỹ thuật
└── tests/                  # Unit/smoke/diagnostic tests
```

## Yêu cầu môi trường

- Python 3.11+.
- Chrome hoặc Edge để dùng camera qua WebRTC.
- Camera trước và/hoặc camera quét tài liệu tùy cấu hình kiosk.
- Redis, Ollama, Swift là tùy chọn, chỉ cần khi bật worker/RAG nâng cao.
- Thư mục `models/` cần được bổ sung riêng nếu triển khai đầy đủ OCR/YOLO/face model.

## Cài đặt

Tạo môi trường ảo và cài dependency:

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Linux/macOS
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

Tạo file `.env` ở thư mục gốc nếu cần ghi đè cấu hình mặc định:

```env
HOST=0.0.0.0
PORT=5000
FLASK_DEBUG=0
FLASK_RELOADER=0
FLASK_SECRET_KEY=change-me

ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_DISPLAY_NAME=Administrator

KIOSK_LANGUAGE=vi
QR_PRINT_ENABLED=false
APPOINTMENT_OVERLAY_ENABLED=false

OCR_USE_REDIS=0
FACE_USE_REDIS=0
FACE_RECOGNITION_THRESHOLD=0.40

FORWARD_ENABLED=false
FORWARD_URL=
FORWARD_API_KEY=

OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=business-card
RAG_V2_EMBED_MODEL=bge-m3
RAG_V2_GENERATE_MODEL=
RAG_V2_PREBUILD_INDEX=0
```

## Chạy ứng dụng

Chạy trực tiếp bằng Flask entry point:

```bash
python application.py
```

Mở trình duyệt:

```text
http://localhost:5000
```

Các trang chính:

- `/` - giao diện kiosk.
- `/login` - đăng nhập dashboard.
- `/dashboard` - quản trị dữ liệu đăng ký, CCCD, lịch hẹn và cấu hình.
- `/qa` hoặc `/qa-voice-demo` - giao diện hỏi đáp bằng giọng nói.
- `/api/status` - kiểm tra trạng thái OCR, YOLO, LLM và ONNX Runtime.

Trên Linux/macOS hoặc thiết bị kiosk, có thể dùng script khởi động:

```bash
chmod +x start_app.sh stop_app.sh
./start_app.sh
```

Script này có thể khởi động thêm Ollama/Redis worker/RAG index tùy biến môi trường. Mặc định trong script, nếu không đặt `PORT`, ứng dụng chạy ở cổng `5001`.

## Dashboard

Khi chạy lần đầu, database sẽ được tự khởi tạo. Tài khoản quản trị mặc định lấy từ `.env`:

- Username: `ADMIN_USERNAME`, mặc định `admin`
- Password: `ADMIN_PASSWORD`, mặc định `admin123`

Nên đổi các giá trị này trước khi triển khai thật.

Dashboard hỗ trợ:

- Thống kê tổng quan.
- Danh sách đăng ký từ danh thiếp.
- Danh sách đăng ký từ CCCD.
- Xem chi tiết, chỉnh sửa và xóa dữ liệu.
- Xóa hàng loạt.
- Xuất Excel/JSON.
- Quản lý lịch hẹn.
- Bật/tắt nhận diện khuôn mặt, in QR, overlay lịch hẹn và ngôn ngữ kiosk.

## Dữ liệu sinh ra khi chạy

Một số dữ liệu runtime sẽ được tạo trong quá trình sử dụng:

- `database/registrations.db` - SQLite database.
- `registrations/<registration_id>/` - ảnh, metadata và tài sản của từng lượt đăng ký.
- `logs/kiosk.log` - log ứng dụng.
- `.run/` - PID file khi chạy bằng `start_app.sh`.
- `rag/indexes/` hoặc thư mục index được cấu hình cho RAG.

Các dữ liệu này thường không nên commit lên GitHub nếu chứa thông tin khách hàng hoặc dữ liệu vận hành thật.

## Kiểm thử

Chạy toàn bộ test:

```bash
python -m pytest
```

Một số test/diagnostic có thể yêu cầu ảnh mẫu, model hoặc biến môi trường riêng. Nếu chỉ kiểm tra smoke test, có thể chạy từng file trong thư mục `tests/`.

## Ghi chú triển khai

- Đảm bảo trình duyệt được cấp quyền camera.
- Nếu chạy trên mạng nội bộ, đặt `HOST=0.0.0.0` và truy cập bằng IP của máy kiosk.
- Nếu bật Redis worker, cần Redis server chạy ở `localhost:6379`.
- Nếu bật Q&A RAG/TTS, cần chuẩn bị Ollama model và dữ liệu nguồn cho RAG.
- Nếu bật in QR, cấu hình printer bằng các biến như `QR_PRINTER_NAME`, `QR_PRINT_MEDIA`, `QR_PRINT_OPTIONS`.
- Không đưa `.env`, database thật, ảnh khách hàng, log và model thương mại lên repository công khai.
