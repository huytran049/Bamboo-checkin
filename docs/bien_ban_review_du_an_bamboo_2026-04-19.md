# BIÊN BẢN REVIEW DỰ ÁN BAMBOO KIOSK

## 1. Thông tin chung

- Tên dự án: Hệ thống lễ tân thông minh Bamboo Kiosk
- Thời điểm review: 19/04/2026
- Hình thức review: Rà soát nội bộ
- Mục đích review:
  - Tổng hợp mức độ hoàn thành dự án
  - Xác nhận các hạng mục đã triển khai
  - Ghi nhận các tồn tại kỹ thuật còn mở
  - Làm cơ sở cho tài liệu bàn giao và danh sách fix

## 2. Phạm vi review

- Luồng kiosk tiếp đón người dùng
- Nhận diện hiện diện và điều hướng trạng thái
- Quét danh thiếp, OCR, điền biểu mẫu
- Quét CCCD và nhận dạng thông tin cơ bản
- Chụp ảnh khuôn mặt và nhận diện khách quay lại
- Lưu hồ sơ đăng ký
- Sinh và in QR registration
- Dashboard quản trị
- Phần hỏi đáp Q&A / RAG
- Luồng voice và popup hỗ trợ thao tác

## 3. Đánh giá tổng quát

- Dự án đã hoàn thành phần lõi của hệ thống
- Các chức năng chính đã liên kết thành một luồng nghiệp vụ tương đối hoàn chỉnh
- Hệ thống đã đạt mức có thể demo, kiểm thử nội bộ và tiếp tục hoàn thiện phục vụ bàn giao
- Trọng tâm hiện tại không còn là dựng chức năng từ đầu
- Trọng tâm hiện tại là:
  - ổn định luồng
  - chuẩn hóa tài liệu
  - tối ưu có chọn lọc
  - khóa các quyết định kỹ thuật đã chốt

## 4. Các nhiệm vụ đã hoàn thành

### 4.1. Nhóm kiosk flow

- Đã xây dựng luồng kiosk cơ bản:
  - nhận diện có người
  - hướng dẫn thao tác
  - quét thông tin
  - chụp khuôn mặt
  - lưu đăng ký
  - reset phiên mới

- Đã hoàn thiện cơ chế chuyển phase chính:
  - `IDLE`
  - `CARD`
  - `FACE`
  - `SUBMITTING`
  - `REMOVING`

- Đã xử lý nhiều lỗi trạng thái:
  - reset không đúng lúc
  - timer cũ còn sót
  - popup còn mở nhưng flow đã chuyển
  - khách quay lại làm kẹt luồng face capture

- Đã tối ưu cấu trúc `mainpy.js` theo hướng giảm rủi ro:
  - tách quản lý timer
  - tách audio controller
  - tách welcome / returning overlay
  - tách OCR polling
  - tách face recognition polling
  - tách presence reaction

### 4.2. Nhóm OCR danh thiếp

- Đã tích hợp OCR danh thiếp vào luồng kiosk
- Đã có cơ chế:
  - chụp ảnh danh thiếp
  - gửi OCR async
  - nhận kết quả
  - điền form tự động

- Đã xử lý các lỗi dữ liệu sau OCR:
  - dữ liệu đúng nhưng form fill sai
  - field bị ghi đè bởi giá trị rỗng
  - merge không ổn định giữa các lượt cập nhật

- Đã chuẩn hóa lại hướng lưu:
  - dữ liệu OCR
  - dữ liệu biểu mẫu
  - dữ liệu SQLite
  - dữ liệu JSON trong thư mục registration

### 4.3. Nhóm CCCD

- Đã triển khai nhận dạng CCCD trong cùng hệ thống kiosk
- Đã phân luồng được giữa:
  - danh thiếp
  - CCCD

- Đã có khả năng:
  - quét QR CCCD
  - đọc thông tin cơ bản
  - lưu draft
  - đẩy dữ liệu lên dashboard

### 4.4. Nhóm khuôn mặt

- Đã tích hợp chụp ảnh khuôn mặt sau bước quét thông tin
- Đã có cơ chế face registration cho hồ sơ mới
- Đã có cơ chế nhận diện khách quay lại

- Đã xử lý các lỗi quan trọng:
  - nhận diện quay lại xong nhưng auto capture không chạy
  - guide khuôn mặt không chuyển xanh đúng lúc
  - state của returning visitor kéo sang flow face capture

- Đã ổn định lại các mốc:
  - clear recognition hold
  - clear popup chào mừng
  - reset face guide
  - reset auto capture state

### 4.5. Nhóm popup, voice, điều hướng thao tác

- Đã thay popup hỏi đặt lịch cũ bằng popup chọn chức năng
- Đã bổ sung các nhánh:
  - Đặt lịch
  - Hỏi đáp
  - Không

- Đã điều chỉnh các logic liên quan:
  - timeout popup
  - reset sau cảm ơn
  - reset khi khách rút card
  - điều kiện chờ popup đóng rồi mới reset

- Đã tạo giao diện Q&A riêng biệt với kiosk chính
- Đã giữ được tính tách biệt giữa:
  - luồng nghiệp vụ kiosk
  - luồng hỏi đáp Q&A

### 4.6. Nhóm Q&A / RAG

- Đã tạo nhánh Q&A riêng để phục vụ giai đoạn AI hỏi đáp
- Đã tách dữ liệu RAG vào thư mục riêng
- Đã tổ chức lại nguồn dữ liệu theo hướng:
  - dữ liệu sản phẩm
  - dữ liệu công ty
  - dữ liệu giao tiếp cơ bản
  - dữ liệu FAQ Bamboo

- Đã triển khai các thành phần chính:
  - ingest dữ liệu
  - chunking
  - retrieval
  - route giữa `rule / faq / rag / fallback`
  - lưu lịch sử
  - voice trả lời

- Đã xây dựng bộ eval retrieval
- Đã chạy kiểm tra theo bộ câu hỏi chuẩn
- Đã cải thiện route và source filtering để tăng độ chính xác retrieval

- Đã triển khai giao diện Q&A riêng:
  - hỏi đáp bằng voice
  - hiển thị câu hỏi
  - hiển thị câu trả lời
  - lưu theo phiên hội thoại

### 4.7. Nhóm dashboard

- Đã bổ sung màn hình Q&A trên dashboard
- Đã đổi cách lưu lịch sử:
  - không còn lưu rời từng cặp hỏi đáp
  - chuyển sang lưu theo phiên hội thoại

- Đã tối ưu dashboard theo hướng:
  - lazy load theo màn
  - giảm refresh thừa
  - giảm request nền không cần thiết

- Đã thêm các thao tác quản trị:
  - xem lịch sử
  - tìm kiếm
  - xóa lịch sử chat

### 4.8. Nhóm QR registration và in QR

- Đã tích hợp sinh QR cho từng registration
- Đã đổi nội dung QR theo hướng thực dụng hơn:
  - hiển thị được thông tin thực tế khi quét
  - không chỉ còn mã `REG_...`

- Đã xử lý lại luồng in QR:
  - tách bố cục ảnh QR ra file riêng
  - tách option máy in `lp` ra file riêng
  - giảm phụ thuộc vào `.env`

- Đã chuẩn hóa 2 file cấu hình:
  - `qr_printing/layout.json`
  - `qr_printing/print_profile.json`

- Đã khóa profile in theo cấu hình thực tế đã test:
  - `Custom 78 x 52 mm`
  - `Landscape`
  - `Scale 254%`

## 5. Các kết quả kỹ thuật đáng ghi nhận

- Hệ thống đã vượt mức demo rời rạc
- Các module chính đã kết nối được với nhau trong cùng một luồng
- Nhiều lỗi phát sinh trong quá trình tích hợp đã được xử lý trực tiếp trên codebase thật
- Q&A đã chuyển từ mức thử nghiệm sang mức có kiến trúc rõ hơn
- Dashboard đã có vai trò quản trị thực tế thay vì chỉ xem dữ liệu thô
- Luồng QR đã rõ ràng hơn cả về quét lại thông tin lẫn in tem

## 6. Các tồn tại còn mở

- Voice recognition trên trình duyệt vẫn phụ thuộc trạng thái micro và browser API
- Q&A / RAG vẫn cần tiếp tục theo dõi regression khi tối ưu backend
- Logic kiosk trung tâm vẫn còn phức tạp, dù đã tách bớt module
- Cần thêm một vòng kiểm thử thực tế với đúng thiết bị để khóa hoàn toàn phần in QR
- Một số phần đã ở mức ổn định chức năng, nhưng chưa ở mức tối ưu cuối cùng về kiến trúc

## 7. Kết luận review

- Dự án Bamboo Kiosk đã hoàn thành phần nền tảng cốt lõi
- Các chức năng chính đã có thể vận hành liên thông
- Dự án đủ điều kiện chuyển sang giai đoạn:
  - tổng hợp tài liệu
  - chốt danh sách fix
  - chốt các quyết định kỹ thuật
  - kiểm thử và bàn giao theo phạm vi

- Nhận định chung:
  - Dự án đã hoàn thành cơ bản
  - Phần còn lại chủ yếu là hoàn thiện, chuẩn hóa và khóa rủi ro

## 8. Kiến nghị sau review

- Hoàn thiện biên bản review chính thức
- Hoàn thiện danh sách fix và các hướng kỹ thuật đã chốt
- Kiểm thử lại các flow kiosk trọng yếu theo checklist
- Kiểm tra lại nhánh Q&A sau mỗi thay đổi tối ưu
- Chốt cấu hình in QR trên thiết bị thật

---

**Ghi chú:**  
Biên bản này là bản tổng hợp review nội bộ, phục vụ báo cáo tiến độ và chuẩn bị tài liệu bàn giao.
