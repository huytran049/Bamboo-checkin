# USER GUIDE - Bamboo Nissin Registration Kiosk

## 1. Giới thiệu

`Bamboo Nissin Registration Kiosk` là ứng dụng kiosk offline-first dùng để tiếp nhận khách tại sự kiện. Hệ thống chạy trên Flask, sử dụng 2 camera để:

- Quét QR đăng ký.
- Chụp và OCR danh thiếp.
- Nhận diện và lưu ảnh khuôn mặt.
- Quét CCCD, trích xuất QR/OCR.
- Quản trị dữ liệu qua dashboard và xuất báo cáo.

Kiến trúc tổng thể:

- Frontend: HTML/CSS/JavaScript thuần trong `templates/` và `static/`.
- Backend: Flask app tại `application.py`, chia route trong `routes/`.
- Business logic: `services/`.
- Database: SQLite tại `database/registrations.db`.
- Dữ liệu hồ sơ: lưu theo thư mục trong `registrations/<REG_ID>/`.
- AI/vision: YOLO ONNX, RapidOCR, face embedding, worker Swift cho một số luồng OCR/face.

Luồng chính:

1. Camera card quét danh thiếp hoặc CCCD.
2. Backend OCR/parse dữ liệu và lưu hồ sơ.
3. Camera face chụp ảnh khuôn mặt và đăng ký embedding.
4. Hệ thống sinh QR đăng ký và có thể in tem QR.
5. Dashboard cho phép tìm kiếm, sửa, xóa, xuất dữ liệu.

## 2. Yêu cầu hệ thống

Yêu cầu tối thiểu theo code hiện tại:

- Hệ điều hành: Windows hoặc Linux. Một số tính năng worker/greeting audio thiên về macOS hoặc môi trường đã cài Swift/CUPS.
- Python: 3.11+.
- Trình duyệt: Chrome hoặc Edge để truy cập camera qua WebRTC.
- SQLite: dùng file cục bộ, không cần cài riêng.
- Redis: tùy chọn, dùng cho OCR async và queue face nếu bật trong `.env`.
- Mô hình AI:
  - `models/card/best.onnx` hoặc model card tương đương.
  - `models/person/yolov8n.pt` cho presence/person detection.
  - `models/face/w600k_r50.onnx` cho face embedding.
- Camera:
  - Camera 1 cho card/QR/CCCD.
  - Camera 2 cho face.

Python packages chính trong `requirements.txt`:

- `flask`, `flask_cors`, `python-dotenv`
- `pillow`, `numpy`, `opencv-python-headless`
- `rapidocr_onnxruntime`, `ultralytics`, `onnxruntime`
- `redis`, `openpyxl`, `pandas`, `qrcode`

## 3. Cài đặt

### 3.1 Chuẩn bị môi trường

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3.2 Kiểm tra tài nguyên bắt buộc

Đảm bảo các thành phần sau tồn tại:

- Thư mục `models/`
- Thư mục `registrations/` sẽ được tạo tự động nếu chưa có
- File `.env`
- File DB `database/registrations.db` sẽ được khởi tạo tự động

### 3.3 Khởi động ứng dụng

```powershell
python application.py
```

Ứng dụng đọc host/port từ biến môi trường và mặc định phục vụ giao diện web tại:

- `http://localhost:5000` nếu không cấu hình khác
- hoặc cổng đang khai báo trong `.env`

## 4. Cấu hình

Ứng dụng dùng `.env` tại root project. Các nhóm cấu hình quan trọng:

### 4.1 Flask runtime

- `HOST`: địa chỉ bind.
- `PORT`: cổng chạy ứng dụng.
- `FLASK_DEBUG` hoặc cờ debug tương đương.
- `FLASK_RELOADER`: bật/tắt auto reload.
- `FLASK_SECRET_KEY`: khóa session cho đăng nhập dashboard.

### 4.2 Tài khoản quản trị mặc định

Nếu bảng `users` chưa có dữ liệu, hệ thống tự tạo admin mặc định từ:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `ADMIN_DISPLAY_NAME`

Khuyến nghị đổi mật khẩu ngay khi triển khai thật.

### 4.3 OCR và Face

- `OCR_USE_REDIS`: bật queue OCR qua Redis.
- `FACE_USE_REDIS`: bật queue face qua Redis.
- `FACE_RECOGNITION_THRESHOLD`: ngưỡng so khớp khuôn mặt.
- `ENABLE_LLM`: bật/tắt nhánh OCR có LLM nếu môi trường hỗ trợ.
- `YOLO_MODEL`: model YOLO cho phát hiện người/card tùy luồng.

### 4.4 Đồng bộ dữ liệu ra ngoài

- `FORWARD_ENABLED`
- `FORWARD_URL`
- `FORWARD_API_KEY`

Nhóm này dùng cho tích hợp external API nếu hệ thống cần đẩy dữ liệu sang dịch vụ khác.

### 4.5 In QR

Các biến bắt đầu bằng `QR_PRINT_` điều khiển:

- Bật/tắt in tem QR.
- Tên máy in.
- Kích thước tem.
- DPI, scale, margin.
- Tùy chọn lệnh in.

### 4.6 Dữ liệu và log

- Log ghi vào `logs/kiosk.log`.
- Check-in log ghi vào `logs/checkin.txt`.
- Ảnh và JSON hồ sơ lưu trong `registrations/<REG_ID>/`.

## 5. Hướng dẫn sử dụng

### 5.1 Đăng nhập

Trang đăng nhập nằm tại:

- `/login`

API đăng nhập:

- `POST /api/auth/login`

Sau khi đăng nhập thành công, session được lưu bằng cookie Flask và người dùng có thể truy cập:

- `/dashboard`

API kiểm tra session hiện tại:

- `GET /api/auth/me`

Đăng xuất:

- `POST /api/auth/logout`

### 5.2 Chức năng A: Đăng ký từ danh thiếp

Luồng nghiệp vụ:

1. Frontend chụp ảnh danh thiếp từ camera card.
2. Backend có thể nhận diện card bằng `POST /api/card/frame`.
3. OCR danh thiếp chạy qua:
   - `POST /api/ocr/bcard`
   - hoặc async qua `POST /api/ocr/bcard_async/start`
   - hoặc quick async qua `POST /api/ocr/bcard_async/quick`
4. Kết quả OCR được parse thành các field:
   - `full_name`
   - `company`
   - `email`
   - `phone`
   - `title`
   - `address`
5. Hồ sơ được lưu bằng `POST /api/register`.
6. Hệ thống tạo thư mục `registrations/<REG_ID>/`, lưu:
   - `data.json`
   - `bcard.*`
   - `face.*` nếu có
   - `registration_qr.png`
7. SQLite được cập nhật vào bảng `bcard_registrations`.

Kết quả trả về từ backend thường gồm:

- `registration_id`
- `qr_url`
- `greeting_audio_url` nếu môi trường hỗ trợ
- `face_register_job_id` nếu có ảnh mặt để đăng ký embedding

### 5.3 Chức năng B: Quét CCCD

Luồng CCCD tách riêng với danh thiếp:

1. Frontend gửi ảnh CCCD sang `POST /api/ocr/cccd_qr_ocr`.
2. Backend ưu tiên worker Swift `workers_swift/cccd_qr_ocr_worker.swift`.
3. Nếu worker không sẵn sàng, backend fallback sang:
   - QR decode bằng OpenCV
   - OCR text bằng RapidOCR
   - Heuristic parse field CCCD
4. Frontend lưu nháp hoặc hoàn tất qua `POST /api/cccd/draft`.
5. Hệ thống lưu:
   - dữ liệu trích xuất trong `data.json`
   - ảnh `cccd_front.*`, `cccd_back.*`, `face.*`
6. SQLite cập nhật bảng `cccd_registrations`.

Các field CCCD chuẩn hóa:

- `idNumber`
- `oldId`
- `fullName`
- `dob`
- `gender`
- `address`
- `issued`
- `expiry`

### 5.4 Chức năng C: Nhận diện khuôn mặt

Các API chính:

- `POST /api/face/frame`
- `POST /api/face/frame_with_boxes`
- `POST /api/face/register_async`
- `POST /api/face/recognize_async`
- `GET /api/face/job/<job_id>`
- `GET /api/face/status`

Mục đích:

- Detect face trên frame camera.
- Đăng ký face embedding cho một `registration_id`.
- Nhận diện khách đã có trong database face.

Dữ liệu face được lưu trong:

- bảng `visitors`
- bảng `face_embeddings`

### 5.5 Chức năng D: Dashboard quản trị

Dashboard yêu cầu đăng nhập và có các tính năng:

- Xem thống kê: `GET /api/dashboard/stats`
- Xem danh sách đăng ký danh thiếp: `GET /api/dashboard/registrations`
- Xem chi tiết một đăng ký: `GET /api/dashboard/registrations/<reg_id>`
- Sửa đăng ký: `PUT /api/dashboard/registrations/<reg_id>`
- Xóa một hoặc nhiều đăng ký
- Export Excel/JSONL cho danh thiếp
- Xem, sửa, xóa, export dữ liệu CCCD

Dashboard render từ:

- `templates/index_dashboard.html`

JS điều khiển chính:

- `static/js/dashboard.js`

## 6. API

Danh sách API chính theo nhóm chức năng.

### 6.1 System

- `GET /api/status`: kiểm tra trạng thái OCR, YOLO, provider ONNX, AI readiness.

### 6.2 Auth

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

### 6.3 Registration

- `POST /api/register`: lưu hồ sơ đăng ký.
- `POST /api/presence/payload`: lưu payload hiện diện.
- `POST /api/presence/frame`: detect person bằng YOLO.
- `GET /api/registrations/<reg_id>/qr`: tra cứu hồ sơ theo QR đăng ký.

### 6.4 Card / OCR

- `POST /api/card/frame`: detect card từ frame.
- `POST /api/ocr/bcard_quick`: quick OCR detection-only.
- `POST /api/ocr/bcard`: OCR đồng bộ cho danh thiếp.
- `POST /api/ocr/bcard_async/start`: khởi tạo OCR async.
- `POST /api/ocr/bcard_async/quick`: khởi tạo quick OCR async.
- `GET /api/ocr/bcard_async/status/<task_id>`: lấy trạng thái OCR task.
- `POST /api/ocr/cccd_qr_ocr`: OCR + QR cho CCCD.

### 6.5 CCCD

- `POST /api/cccd/draft`: lưu nháp hoặc hoàn tất hồ sơ CCCD.

### 6.6 Face

- `POST /api/face/frame`
- `POST /api/face/frame_with_boxes`
- `POST /api/face/register_async`
- `POST /api/face/recognize_async`
- `GET /api/face/job/<job_id>`
- `GET /api/face/status`

### 6.7 Dashboard

- `GET /api/dashboard/stats`
- `GET /api/dashboard/registrations`
- `GET /api/dashboard/registrations/<reg_id>`
- `PUT /api/dashboard/registrations/<reg_id>`
- `DELETE /api/dashboard/registrations/<reg_id>`
- `POST /api/dashboard/registrations/bulk-delete`
- `GET /api/dashboard/export.xlsx`
- `GET /api/dashboard/export.jsonl`
- `GET /api/dashboard/notifications`
- `GET /api/dashboard/cccd`
- `GET /api/dashboard/cccd/<reg_id>`
- `PUT /api/dashboard/cccd/<reg_id>`
- `DELETE /api/dashboard/cccd/<reg_id>`
- `POST /api/dashboard/cccd/bulk-delete`
- `GET /api/dashboard/cccd/export.json`
- `GET /api/dashboard/cccd/export.xlsx`

## 7. Lỗi thường gặp

### 7.1 Không đăng nhập được dashboard

Nguyên nhân thường gặp:

- Chưa có user mặc định như mong đợi.
- `FLASK_SECRET_KEY` thay đổi giữa các lần chạy.
- Cookie/session bị trình duyệt chặn.

Cách kiểm tra:

- Xem bảng `users` trong `database/registrations.db`.
- Kiểm tra log trong `logs/kiosk.log`.

### 7.2 OCR không chạy hoặc kết quả rỗng

Nguyên nhân thường gặp:

- Thiếu model hoặc engine OCR khởi tạo lỗi.
- Ảnh đầu vào quá mờ, lệch góc, hoặc crop sai vùng.
- Redis được bật cho OCR nhưng worker queue không chạy.

Cách kiểm tra:

- Gọi `GET /api/status`.
- Xem log `kiosk.log`.
- Kiểm tra `OCR_USE_REDIS` và Redis local.

### 7.3 Face recognition không hoạt động

Nguyên nhân thường gặp:

- Thiếu model face embedding.
- Ảnh mặt không được lưu đúng trong thư mục registration.
- Ngưỡng `FACE_RECOGNITION_THRESHOLD` quá chặt.

Cách kiểm tra:

- Gọi `GET /api/face/status`.
- Kiểm tra bảng `visitors` và `face_embeddings`.

### 7.4 CCCD nhận diện sai hoặc không nhận diện

Nguyên nhân thường gặp:

- Worker Swift không có trên máy.
- Ảnh CCCD không rõ QR hoặc OCR text quá yếu.
- Frontend gửi ảnh chưa đúng chiều/chưa đủ sáng.

Cách kiểm tra:

- Thử trực tiếp `POST /api/ocr/cccd_qr_ocr`.
- Kiểm tra worker `workers_swift/cccd_qr_ocr_worker.swift`.

### 7.5 Lỗi SQLite locked

Code đã có retry và `WAL`, nhưng vẫn có thể xảy ra khi nhiều tác vụ cùng ghi.

Giảm rủi ro bằng cách:

- Không chạy quá nhiều luồng ghi đồng thời.
- Theo dõi các tác vụ OCR/face async.
- Kiểm tra timeout `SQLITE_TIMEOUT_SEC` và `SQLITE_BUSY_TIMEOUT_MS`.

### 7.6 QR không được in

Nguyên nhân thường gặp:

- `QR_PRINT_ENABLED=false`
- Máy in hoặc lệnh in chưa sẵn sàng
- Cấu hình printer/media không đúng

## 8. Deployment

### 8.1 Mô hình triển khai đề xuất

Phù hợp nhất với project hiện tại là triển khai 1 máy kiosk cục bộ:

- Flask app chạy nội bộ trên máy kiosk.
- SQLite lưu tại local disk.
- Model AI đặt trong thư mục `models/`.
- Camera kết nối trực tiếp vào máy.
- Redis local nếu cần queue.

### 8.2 Checklist triển khai

1. Cài Python và dependency.
2. Copy source code, `models/`, `.env`.
3. Kiểm tra camera, quyền truy cập camera từ browser.
4. Chạy `python application.py`.
5. Truy cập `/api/status` để xác nhận AI engine sẵn sàng.
6. Đăng nhập `/login` và kiểm tra dashboard.
7. Test từng luồng:
   - quét danh thiếp
   - quét CCCD
   - đăng ký face
   - export dashboard

### 8.3 Thành phần cần giám sát

- `logs/kiosk.log`
- `logs/checkin.txt`
- dung lượng thư mục `registrations/`
- file `database/registrations.db`
- trạng thái Redis nếu bật queue

### 8.4 Gợi ý hardening production

- Đổi toàn bộ mật khẩu mặc định.
- Thiết lập `FLASK_SECRET_KEY` riêng cho môi trường thật.
- Tắt debug mode.
- Hạn chế truy cập cổng ứng dụng trong mạng nội bộ.
- Sao lưu định kỳ `database/` và `registrations/`.

### 8.5 Các file quan trọng khi vận hành

- `application.py`: entrypoint Flask.
- `app_config.py`: khởi tạo logger, OCR, YOLO, Redis, DB.
- `database/update_database.py`: schema và thao tác SQLite.
- `services/registration.py`: lưu hồ sơ đăng ký.
- `services/ocr_service.py`: OCR danh thiếp sync/async.
- `services/cccd_service.py`: luồng CCCD.
- `services/face_service.py`: queue và xử lý face.

