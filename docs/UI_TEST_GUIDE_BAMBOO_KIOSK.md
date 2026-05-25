# Tài liệu test giao diện Bamboo Nissin Kiosk

## 1. Mục tiêu

Tài liệu này dùng cho đội tester kiểm tra toàn bộ chức năng theo hướng thao tác giao diện thực tế, không cần đọc code.

Phạm vi test gồm:

- Kiosk trang chính `/`
- Trang hỏi đáp giọng nói `/qa-voice-demo`
- Đăng nhập dashboard `/login`
- Dashboard quản trị `/dashboard`

## 2. Thông tin hệ thống hiện tại

Theo cấu hình đang có trong dự án:

- Cổng chạy chuẩn khi dùng script `start_app.sh`: `http://localhost:5001`
- Ngôn ngữ kiosk hiện tại: `vi`
- `APPOINTMENT_OVERLAY_ENABLED=false`
- `QR_PRINT_ENABLED=false`
- `FACE_USE_REDIS=1` nên trên dashboard sẽ hiểu là `face recognition` đang tắt

Hệ quả khi test:

- Popup đặt lịch trên kiosk mặc định không tự bật sau khi đăng ký xong
- In QR mặc định đang tắt
- Nhận diện khách quay lại mặc định đang tắt

Nếu cần test 3 chức năng trên, phải bật trong màn hình `Dashboard > Cài đặt`.

## 3. Tài khoản test dashboard

Trong database hiện có user:

- Username: `admin`

Mật khẩu không đọc được từ DB. Theo code, nếu chưa từng đổi thì mật khẩu mặc định là:

- Password mặc định: `admin123`

Nếu `admin123` không đăng nhập được, cần xin lại mật khẩu thật từ đội triển khai.

## 4. Điều kiện trước khi test

- Dự án đã chạy và truy cập được qua trình duyệt Chrome hoặc Edge
- Trình duyệt đã cấp quyền camera và micro
- Có ít nhất 2 camera:
- Camera 1 để quét danh thiếp/CCCD
- Camera 2 để chụp mặt và quét QR
- Có sẵn dữ liệu mẫu để test:
- 1 danh thiếp rõ nét
- 1 CCCD thật hoặc ảnh CCCD rõ nét
- 1 QR hợp lệ của bản đăng ký đã có
- 1 QR sai định dạng hoặc QR không tồn tại
- Có loa nếu cần test âm thanh hướng dẫn

## 5. Dữ liệu test nên chuẩn bị

- Danh thiếp đủ thông tin: tên, công ty, email, số điện thoại
- Danh thiếp thiếu một vài trường
- Danh thiếp mờ, nghiêng, chói sáng
- CCCD rõ thông tin
- CCCD mờ hoặc mất góc
- Khuôn mặt đủ sáng
- Khuôn mặt lệch khung hoặc quá gần
- QR hợp lệ của khách đã đăng ký
- QR rác hoặc QR không thuộc hệ thống

## 6. Smoke test nhanh

Tester nên chạy trước vòng này để xác nhận hệ thống sống:

1. Mở `/` và kiểm tra cả 2 camera lên hình.
2. Kiểm tra trang có 2 nút bên phải: `Đặt lịch`, `Hỏi đáp`.
3. Mở `/qa-voice-demo`, bấm `Bắt đầu`, xác nhận không vỡ giao diện.
4. Mở `/login`, đăng nhập dashboard.
5. Vào từng tab dashboard: `Thông tin khách hàng`, `Căn cước công dân`, `Đặt lịch`, `Q&A`, `Cài đặt`.
6. Kiểm tra dashboard load được dữ liệu và không có lỗi trắng trang.

## 7. Checklist test chi tiết

### 7.1 Kiosk trang chính `/`

#### KIOSK-01: Load giao diện mặc định

- Bước test:
- Mở trang `/`
- Cho phép camera nếu trình duyệt hỏi quyền
- Kỳ vọng:
- Trang hiển thị 2 khung camera
- Camera 1 có tiêu đề `Danh thiếp`
- Camera 2 có tiêu đề `Khuôn mặt / QR`
- Có 2 khung preview ảnh đã chụp
- Có 2 nút bên phải: `Đặt lịch`, `Hỏi đáp`
- Không lỗi JS trên màn hình

#### KIOSK-02: Chọn camera

- Bước test:
- Đổi camera ở dropdown camera 1
- Đổi camera ở dropdown camera 2
- Kỳ vọng:
- Video đổi đúng thiết bị
- Không treo trang
- Sau khi đổi camera vẫn tiếp tục quét/chụp được

#### KIOSK-03: Tắt/mở camera

- Bước test:
- Bấm nút nguồn camera 1
- Bấm lại để bật
- Lặp lại với camera 2
- Kỳ vọng:
- Camera tắt thì preview dừng
- Bật lại thì preview hoạt động lại
- Không cần reload trang

#### KIOSK-04: Quét danh thiếp thành công

- Bước test:
- Đưa danh thiếp rõ nét vào camera 1
- Giữ ổn định đến khi hệ thống tự chụp
- Kỳ vọng:
- Ảnh danh thiếp xuất hiện ở preview trái
- Hệ thống chuyển sang bước chụp mặt
- Không yêu cầu thao tác tay để chụp danh thiếp

#### KIOSK-05: Danh thiếp khó đọc

- Bước test:
- Đưa danh thiếp mờ hoặc nghiêng mạnh vào camera 1
- Kỳ vọng:
- Hệ thống không chụp sai liên tục
- Nếu OCR thất bại, hệ thống không bị treo
- Sau khi thay bằng danh thiếp rõ hơn vẫn tiếp tục được

#### KIOSK-06: Chụp khuôn mặt thành công

- Tiền đề:
- Đã quét được danh thiếp hoặc đã có dữ liệu CCCD
- Bước test:
- Đứng trước camera 2, đưa mặt vào khung nhận diện
- Giữ yên
- Kỳ vọng:
- Xuất hiện guide khung mặt
- Hệ thống tự chụp mặt
- Ảnh mặt xuất hiện ở preview phải

#### KIOSK-07: Chụp khuôn mặt thất bại rồi thử lại

- Bước test:
- Đứng lệch khung, quá gần hoặc quá tối
- Kỳ vọng:
- Hệ thống nhắc lại bằng trạng thái/âm thanh
- Không crash
- Khi đưa mặt đúng vị trí thì chụp được

#### KIOSK-08: Quét CCCD thành công

- Bước test:
- Đưa CCCD vào camera 1
- Chờ hệ thống đọc QR/OCR
- Sau đó đưa mặt vào camera 2
- Kỳ vọng:
- Hệ thống nhận diện theo luồng CCCD
- Dữ liệu CCCD được lưu vào dashboard mục `Căn cước công dân`
- Ảnh mặt vẫn được chụp và gắn với hồ sơ

#### KIOSK-09: Quét QR đăng ký hợp lệ

- Bước test:
- Đưa QR hợp lệ vào camera 2
- Kỳ vọng:
- Hệ thống đọc được QR
- Tự điền hoặc khôi phục đúng hồ sơ đã có
- Nếu là khách cũ, hệ thống đi tiếp đúng flow hoàn tất

#### KIOSK-10: Quét QR không hợp lệ

- Bước test:
- Đưa QR rác hoặc QR không thuộc hệ thống vào camera 2
- Kỳ vọng:
- Có phản hồi lỗi
- Không treo camera 2
- Sau QR lỗi vẫn quét được QR hợp lệ khác

#### KIOSK-11: Hoàn tất đăng ký và reset phiên

- Bước test:
- Hoàn tất 1 ca đăng ký bằng danh thiếp hoặc CCCD
- Rút thẻ/danh thiếp khỏi camera 1
- Kỳ vọng:
- Hệ thống hiển thị thông báo cảm ơn
- Nhắc lấy lại danh thiếp
- Sau một khoảng chờ, hệ thống reset về trạng thái chờ
- Dữ liệu hồ sơ mới xuất hiện trong dashboard

#### KIOSK-12: Nút `Hỏi đáp`

- Bước test:
- Tại trang `/`, bấm `Hỏi đáp`
- Kỳ vọng:
- Chuyển sang `/qa-voice-demo`
- Không giữ popup cũ của kiosk

#### KIOSK-13: Nút `Đặt lịch`

- Bước test:
- Tại trang `/`, bấm `Đặt lịch`
- Kỳ vọng:
- Popup đặt lịch mở ra ngay cả khi chưa hoàn tất đăng ký
- Có các trường ngày, giờ bắt đầu, giờ kết thúc, mục đích, nội dung

#### KIOSK-14: Popup đặt lịch khi tính năng đang tắt

- Tiền đề:
- `APPOINTMENT_OVERLAY_ENABLED=false`
- Bước test:
- Hoàn tất một ca đăng ký
- Kỳ vọng:
- Hệ thống không tự bật popup chọn `Đặt lịch / Hỏi đáp / Không`
- Chỉ còn test được bằng nút `Đặt lịch` thủ công ở cạnh phải

#### KIOSK-15: Đặt lịch thành công

- Tiền đề:
- Bật `Dashboard > Cài đặt > Đặt lịch`
- Bước test:
- Mở popup đặt lịch
- Chọn ngày tương lai
- Chọn giờ bắt đầu và giờ kết thúc hợp lệ
- Nhập mục đích hoặc nội dung
- Bấm `Đặt lịch`, rồi `Xác nhận`
- Kỳ vọng:
- Popup báo thành công
- Lịch hẹn xuất hiện trong dashboard mục `Đặt lịch`

#### KIOSK-16: Validate đặt lịch

- Bước test:
- Thử để trống ngày
- Thử để trống giờ
- Thử giờ kết thúc nhỏ hơn giờ bắt đầu
- Thử chọn ngày quá khứ
- Kỳ vọng:
- Popup báo lỗi đúng trường hợp
- Không tạo lịch lỗi vào DB

#### KIOSK-17: Trùng khung giờ đặt lịch

- Tiền đề:
- Ngày đó đã có lịch
- Bước test:
- Chọn khung giờ trùng lịch đang có
- Kỳ vọng:
- Hệ thống báo khung giờ đã có lịch
- Không cho xác nhận tạo trùng

### 7.2 Trang hỏi đáp `/qa-voice-demo`

#### QA-01: Load trang hỏi đáp

- Bước test:
- Mở `/qa-voice-demo`
- Kỳ vọng:
- Có nút `Bắt đầu`, `Làm mới`, `Quay lại`
- Có khu vực hội thoại
- Có trạng thái sẵn sàng

#### QA-02: Hỏi đáp bằng giọng nói

- Bước test:
- Bấm `Bắt đầu`
- Cấp quyền micro nếu trình duyệt hỏi
- Đọc 1 câu hỏi ngắn
- Kỳ vọng:
- Trạng thái chuyển qua các bước nghe, xử lý, trả lời
- Câu hỏi người dùng xuất hiện trong lịch sử chat
- Câu trả lời hệ thống xuất hiện

#### QA-03: Micro bị từ chối

- Bước test:
- Chặn quyền micro ở trình duyệt
- Bấm `Bắt đầu`
- Kỳ vọng:
- Có thông báo không dùng được micro
- Trang không bị treo

#### QA-04: Nút `Làm mới`

- Bước test:
- Sau khi có vài lượt hội thoại, bấm `Làm mới`
- Kỳ vọng:
- Hội thoại được reset
- Trạng thái quay về sẵn sàng

#### QA-05: Nút `Quay lại`

- Bước test:
- Bấm `Quay lại`
- Kỳ vọng:
- Quay lại trang kiosk `/`

### 7.3 Đăng nhập dashboard `/login`

#### LOGIN-01: Đăng nhập đúng

- Bước test:
- Vào `/login`
- Nhập `admin`
- Nhập mật khẩu đúng
- Kỳ vọng:
- Chuyển sang `/dashboard`

#### LOGIN-02: Sai tài khoản hoặc mật khẩu

- Bước test:
- Nhập sai user hoặc sai password
- Kỳ vọng:
- Hiển thị lỗi `Thông tin đăng nhập không hợp lệ`
- Không đăng nhập được

#### LOGIN-03: Bỏ trống trường

- Bước test:
- Để trống username hoặc password
- Kỳ vọng:
- Không submit thành công
- Có thông báo yêu cầu nhập

### 7.4 Dashboard `/dashboard`

#### DASH-01: Tab `Thông tin khách hàng`

- Bước test:
- Vào dashboard
- Mặc định ở tab `Thông tin khách hàng`
- Kỳ vọng:
- Có thống kê tổng lượt khách
- Có bảng danh sách
- Có nút `Xuất JSONL`, `Xuất Excel`

#### DASH-02: Tìm kiếm khách hàng

- Bước test:
- Gõ tên khách hoặc tên công ty vào ô tìm kiếm
- Kỳ vọng:
- Bảng lọc đúng kết quả
- Không reload trắng trang

#### DASH-03: Phân trang khách hàng

- Bước test:
- Bấm `Trang trước`, `Trang sau`
- Kỳ vọng:
- Di chuyển đúng trang
- Chỉ số trang cập nhật đúng

#### DASH-04: Xem chi tiết hồ sơ khách hàng

- Bước test:
- Click 1 dòng trong bảng khách hàng
- Kỳ vọng:
- Panel chi tiết hiện đúng ảnh danh thiếp, ảnh mặt, thông tin liên hệ

#### DASH-05: Sửa hồ sơ khách hàng

- Bước test:
- Mở hồ sơ
- Sửa tên, công ty, email hoặc số điện thoại
- Lưu
- Kỳ vọng:
- Dữ liệu mới hiển thị lại đúng

#### DASH-06: Xóa 1 hồ sơ khách hàng

- Bước test:
- Xóa 1 dòng dữ liệu
- Kỳ vọng:
- Dòng bị xóa khỏi danh sách
- Reload lại vẫn không còn

#### DASH-07: Xóa nhiều hồ sơ khách hàng

- Bước test:
- Tick nhiều dòng
- Bấm `Xóa`
- Kỳ vọng:
- Xóa đúng số lượng đã chọn

#### DASH-08: Lọc `Chỉ hiện mục cần kiểm tra`

- Bước test:
- Bật checkbox `Chỉ hiện mục cần kiểm tra`
- Kỳ vọng:
- Danh sách chỉ còn các hồ sơ thiếu trường bắt buộc

#### DASH-09: Export khách hàng

- Bước test:
- Bấm `Xuất Excel`
- Bấm `Xuất JSONL`
- Kỳ vọng:
- File tải về thành công
- Nội dung file khớp dữ liệu đang lọc

#### DASH-10: Tab `Căn cước công dân`

- Bước test:
- Chuyển sang tab `Căn cước công dân`
- Kỳ vọng:
- Có bảng danh sách CCCD
- Có thống kê
- Có export

#### DASH-11: Tìm kiếm và xem chi tiết CCCD

- Bước test:
- Tìm theo tên hoặc số CCCD
- Click vào 1 dòng
- Kỳ vọng:
- Thấy thông tin CCCD, ảnh CCCD và ảnh mặt

#### DASH-12: Sửa hồ sơ CCCD

- Bước test:
- Sửa họ tên, số CCCD, ngày sinh, giới tính, địa chỉ
- Lưu
- Kỳ vọng:
- Dữ liệu cập nhật đúng

#### DASH-13: Xóa và export CCCD

- Bước test:
- Xóa 1 hồ sơ
- Xóa nhiều hồ sơ
- Xuất JSON
- Xuất Excel
- Kỳ vọng:
- Tất cả thao tác thành công, không lệch dữ liệu

#### DASH-14: Tab `Đặt lịch`

- Bước test:
- Chuyển sang tab `Đặt lịch`
- Kỳ vọng:
- Có lịch theo tháng
- Có nút tháng trước, hôm nay, tháng sau
- Có danh sách lịch theo ngày được chọn

#### DASH-15: Xem chi tiết lịch hẹn

- Bước test:
- Chọn 1 ngày có lịch
- Click 1 lịch hẹn
- Kỳ vọng:
- Hiển thị đúng ngày, giờ, người liên hệ, trạng thái, người phụ trách, nội dung

#### DASH-16: Sửa lịch hẹn

- Bước test:
- Mở chi tiết lịch
- Sửa ngày, giờ, người liên hệ, mục đích, mô tả, người phụ trách, trạng thái
- Lưu
- Kỳ vọng:
- Dữ liệu cập nhật đúng

#### DASH-17: Xóa lịch hẹn

- Bước test:
- Xóa 1 lịch hẹn trong dashboard
- Kỳ vọng:
- Lịch biến mất khỏi tháng và danh sách ngày

#### DASH-18: Lọc lịch hẹn

- Bước test:
- Lọc theo trạng thái
- Lọc theo người phụ trách
- Kỳ vọng:
- Chỉ hiện lịch đúng điều kiện

#### DASH-19: Tab `Q&A`

- Bước test:
- Chuyển sang tab `Q&A`
- Kỳ vọng:
- Có lịch sử câu hỏi
- Có vùng chi tiết câu hỏi/câu trả lời

#### DASH-20: Tìm kiếm lịch sử Q&A

- Bước test:
- Tìm theo câu hỏi hoặc câu trả lời
- Kỳ vọng:
- Danh sách lọc đúng

#### DASH-21: Xóa 1 lịch sử Q&A và xóa toàn bộ

- Bước test:
- Xóa 1 record
- Xóa tất cả
- Kỳ vọng:
- Danh sách cập nhật đúng

#### DASH-22: Tab `Cài đặt`

- Bước test:
- Vào `Cài đặt`
- Kỳ vọng:
- Có các toggle:
- `QR print`
- `Face recognition`
- `Đặt lịch`
- `Japanese mode`

#### DASH-23: Bật/tắt cài đặt

- Bước test:
- Đổi trạng thái từng toggle
- Reload lại dashboard
- Kỳ vọng:
- Giá trị vẫn được giữ
- Hiển thị đúng biến môi trường liên quan

#### DASH-24: Đăng xuất

- Bước test:
- Bấm `Đăng xuất`
- Kỳ vọng:
- Quay về màn hình login
- Truy cập lại `/dashboard` phải yêu cầu đăng nhập lại

## 8. Regression ưu tiên cao

Sau mỗi lần sửa code, tối thiểu phải retest các case sau:

1. `KIOSK-01`, `KIOSK-04`, `KIOSK-06`, `KIOSK-11`
2. `KIOSK-08`, `KIOSK-09`, `KIOSK-10`
3. `QA-02`
4. `LOGIN-01`
5. `DASH-02`, `DASH-05`, `DASH-06`, `DASH-09`
6. `DASH-11`, `DASH-12`, `DASH-13`
7. `DASH-15`, `DASH-16`, `DASH-17`
8. `DASH-23`

## 9. Lỗi cần ghi rõ khi báo bug

Mỗi bug nên có đủ:

- Mã case test, ví dụ `KIOSK-10`
- Môi trường test: máy nào, browser nào, camera nào
- Dữ liệu dùng để test
- Các bước tái hiện
- Kết quả thực tế
- Kết quả mong đợi
- Ảnh chụp màn hình hoặc video
- Nếu có thể, đính kèm thời gian xảy ra lỗi để dev đối chiếu `logs/kiosk.log`

## 10. Ghi chú quan trọng cho đội test

- Trang kiosk có nhiều luồng tự động, nên khi test cần chờ đủ vài giây trước khi kết luận fail
- Một số tính năng phụ thuộc cấu hình bật/tắt trong `Dashboard > Cài đặt`
- Với các lỗi camera không lên hình, cần kiểm tra lại quyền camera của trình duyệt trước
- Với lỗi micro ở trang hỏi đáp, cần kiểm tra quyền micro trước
- Nếu đã hoàn tất đăng ký nhưng dashboard chưa thấy ngay, refresh tab dashboard rồi kiểm tra lại
