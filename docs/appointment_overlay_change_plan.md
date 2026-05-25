# Kế hoạch sửa đổi: Overlay đặt lịch sau khi chụp card + face

## Mục tiêu

Bổ sung một overlay đặt lịch ở kiosk sau khi khách hoàn tất flow quét `card + face`.

Flow mong muốn:

- Khi hoàn tất `card + face`, hệ thống không đi thẳng sang màn cảm ơn ngay.
- Hệ thống hiển thị câu hỏi: khách có muốn đặt lịch hay không.
- Nếu khách chọn `Có`, mở overlay form đặt lịch.
- Nếu khách chọn `Không`, đi thẳng sang màn cảm ơn.
- Nếu khách đặt lịch thành công, dashboard sẽ hiển thị ngày có lịch bằng trạng thái nổi bật màu đỏ.
- Khi bấm vào ngày đó trên dashboard, panel bên cạnh hiển thị danh sách lịch trong ngày theo format nghiệp vụ mới.

Ngoài ra cần có cờ bật/tắt bằng `.env` để có thể tắt toàn bộ flow overlay và quay về flow cũ.

## Cờ bật/tắt bằng `.env`

Thêm biến môi trường:

```env
APPOINTMENT_OVERLAY_ENABLED=true
```

Ý nghĩa:

- `true`: bật flow overlay đặt lịch.
- `false`: tắt flow overlay, kiosk quay về flow cũ `card + face => cảm ơn`.

Flow theo flag:

- `APPOINTMENT_OVERLAY_ENABLED=false`
  - `card + face`
  - lưu dữ liệu như hiện tại
  - hiện cảm ơn
  - reset workflow

- `APPOINTMENT_OVERLAY_ENABLED=true`
  - `card + face`
  - hỏi `Bạn có muốn đặt lịch không?`
  - `Có` => mở form đặt lịch
  - `Không` => cảm ơn
  - `Huỷ` trong form => confirm
  - nếu xác nhận huỷ => cảm ơn
  - nếu không xác nhận huỷ => quay lại overlay đặt lịch
  - `Đặt lịch` => confirm => lưu lịch => cảm ơn

## Hiện trạng code hiện tại

### Dashboard

Hệ thống đã có màn appointment trong dashboard:

- xem lịch theo tháng
- xem danh sách lịch theo ngày
- xóa lịch
- tạo lịch qua API backend

Các file liên quan:

- `/Users/ssg/Documents/bamboo_nissin/routes/dashboard.py`
- `/Users/ssg/Documents/bamboo_nissin/database/update_database.py`
- `/Users/ssg/Documents/bamboo_nissin/static/js/dashboard.js`
- `/Users/ssg/Documents/bamboo_nissin/static/css/dashboard.css`
- `/Users/ssg/Documents/bamboo_nissin/templates/index_dashboard.html`

### Kiosk

Kiosk hiện chưa có:

- overlay hỏi có muốn đặt lịch hay không
- overlay form đặt lịch
- modal confirm dùng chung
- API public để kiosk tạo/lấy lịch

Flow kiosk hiện tại trong:

- `/Users/ssg/Documents/bamboo_nissin/static/js/mainpy.js`

đang đi từ hoàn tất scan/chụp sang thank-you/reset tương đối trực tiếp. Vì vậy overlay mới phải được chèn vào trước bước thank-you hiện tại.

## Những gì bắt buộc phải sửa

## 1. Bổ sung config bật/tắt bằng `.env`

### File cần sửa

- `/Users/ssg/Documents/bamboo_nissin/app_config.py`
- `/Users/ssg/Documents/bamboo_nissin/env_settings.py`
- `/Users/ssg/Documents/bamboo_nissin/routes/dashboard.py`
- `/Users/ssg/Documents/bamboo_nissin/static/js/dashboard.js` nếu muốn bật/tắt từ dashboard settings

### Việc cần làm

- Thêm biến `APPOINTMENT_OVERLAY_ENABLED` vào phần đọc env.
- Thêm giá trị này vào payload `get_dashboard_settings()`.
- Đồng bộ toggle bật/tắt bên dashboard:
  - thêm toggle ở screen settings
  - khi lưu settings thì ghi lại vào `.env`
  - dashboard phải hiển thị đúng trạng thái hiện tại của `APPOINTMENT_OVERLAY_ENABLED`
- Khi runtime đổi flag, JS kiosk cần nhận được trạng thái hiện tại theo API hoặc theo config render từ server.

## 2. Chèn overlay đặt lịch vào flow kiosk

### File cần sửa

- `/Users/ssg/Documents/bamboo_nissin/templates/index.html`
- `/Users/ssg/Documents/bamboo_nissin/static/css/styles.css`
- `/Users/ssg/Documents/bamboo_nissin/static/js/mainpy.js`

### Việc cần làm

- Thêm overlay hỏi:
  - nội dung `Bạn có muốn đặt lịch không?`
  - nút `Có`
  - nút `Không`

- Thêm overlay form đặt lịch:
  - `Loại`
  - `Lý do`
  - `Ngày hẹn`
  - `Lịch trong ngày`
  - `Giờ bắt đầu`
  - `Giờ kết thúc`
  - nút `Đặt lịch`
  - nút `Huỷ`

- Thêm modal confirm dùng chung cho kiosk.

- Chỉ các thao tác sau cần confirm:
  - `Đặt lịch`
  - `Huỷ`

- Không cần confirm cho:
  - `Có`
  - `Không`

- Chèn logic vào `mainpy.js` ở đúng điểm kết thúc flow:
  - nếu flag `false` => chạy flow cũ
  - nếu flag `true` => mở câu hỏi đặt lịch

## 3. Bổ sung API appointment cho kiosk

### Vấn đề hiện tại

Appointment API hiện nằm trong dashboard route và có `login_required`.

Kiosk public flow không nên gọi trực tiếp các API dashboard đó.

### File cần sửa

- `/Users/ssg/Documents/bamboo_nissin/routes/dashboard.py`
- thêm route public mới, có thể tại:
  - `/Users/ssg/Documents/bamboo_nissin/routes/pages.py`
  - hoặc tạo file route mới chuyên cho kiosk appointment

### API nên có

- `GET /api/appointments/day?date=YYYY-MM-DD`
  - trả danh sách lịch trong ngày
  - dùng để render phần `Lịch trong ngày` trong overlay

- `POST /api/appointments`
  - tạo lịch từ kiosk
  - dùng cho submit form đặt lịch

### Ghi chú

- Nên tách API kiosk và API dashboard rõ ràng để tránh phụ thuộc auth của dashboard.
- Logic thao tác DB vẫn nên tái sử dụng chung service/hàm DB hiện có.

## 4. Mở rộng schema appointment

### Vấn đề hiện tại

Bảng `appointments` hiện có các cột:

- `appointment_date`
- `start_time`
- `end_time`
- `title`
- `description`
- `contact_name`

Schema này chưa đủ cho nghiệp vụ mới.

### File cần sửa

- `/Users/ssg/Documents/bamboo_nissin/database/update_database.py`

### Cột nên bổ sung

- `appointment_type`
- `appointment_reason`
- `registration_id`
- `source`

### Ý nghĩa

- `appointment_type`: ví dụ `Khách hàng`, `Vận hành`
- `appointment_reason`: ví dụ `Tư vấn sản phẩm`, `Demo sản phẩm`, `Set up máy`, ...
- `registration_id`: liên kết lịch hẹn với bản ghi khách vừa tạo trong kiosk
- `source`: phân biệt lịch tạo từ `kiosk` hay từ nơi khác

### Hướng xử lý DB

- Nếu DB cũ chưa có các cột này, cần migration mềm theo cách tương thích với DB hiện có.
- Không nên yêu cầu xóa DB cũ.

## 5. Kiểm tra trùng lịch ở backend

### Vấn đề hiện tại

Hàm `create_appointment(...)` hiện mới check:

- ngày hợp lệ
- giờ hợp lệ
- `end_time >= start_time`

Chưa check trùng lịch.

### File cần sửa

- `/Users/ssg/Documents/bamboo_nissin/database/update_database.py`

### Rule cần bổ sung

Nếu có lịch đang tồn tại trong cùng ngày và khoảng giờ bị chồng lấn, phải từ chối tạo mới.

Ví dụ overlap:

- lịch cũ `08:00 - 09:00`
- lịch mới `08:30 - 09:30`

Trường hợp này phải báo trùng lịch.

### Lưu ý

- Frontend có thể báo sớm cho người dùng.
- Backend vẫn phải là nơi chặn cuối cùng.

## 6. Render overlay theo đúng workflow nghiệp vụ

### Dữ liệu dropdown

`Loại`:

- `Khách hàng`
- `Vận hành`

`Lý do` phụ thuộc `Loại`:

- nếu `Khách hàng`
  - `Tư vấn sản phẩm`
  - `Demo sản phẩm`
  - `Ký hợp đồng`

- nếu `Vận hành`
  - `Set up máy`
  - `Kiểm tra sản phẩm`

### Slot giờ

- thời gian đặt hẹn từ `08:00` đến `17:00`
- bước nhảy `10 phút`

### Hành vi UI

- Chọn ngày => tải danh sách lịch trong ngày
- Hiển thị các lịch đã có
- Nếu slot đang bị chiếm thì phải báo rõ
- `Giờ kết thúc` phải lớn hơn `Giờ bắt đầu`
- Nút `Có`:
  - mở form ngay, không cần confirm
- Nút `Không`:
  - sang cảm ơn ngay, không cần confirm
- Nút `Huỷ`:
  - mở confirm
  - nếu xác nhận huỷ => sang cảm ơn
  - nếu không xác nhận huỷ => quay lại form đặt lịch
- Nút `Đặt lịch`:
  - mở confirm
  - nếu xác nhận => submit tạo lịch
  - nếu không xác nhận => quay lại form đặt lịch

## 7. Sửa dashboard để hiển thị đúng nghiệp vụ mới

### File cần sửa

- `/Users/ssg/Documents/bamboo_nissin/static/js/dashboard.js`
- `/Users/ssg/Documents/bamboo_nissin/static/css/dashboard.css`
- `/Users/ssg/Documents/bamboo_nissin/templates/index_dashboard.html` nếu cần thêm nhãn hoặc layout

### Việc cần làm

- Đổi style ngày có lịch từ trạng thái xanh nhạt hiện tại sang trạng thái nổi bật màu đỏ.
- Khi bấm vào ngày, card chi tiết bên phải phải hiển thị theo format gần với mockup mới:

```text
Tên khách hàng - khung giờ hẹn
Lí do hẹn : Loại - Lí do
```

### Dữ liệu hiển thị đề xuất

- dòng 1:
  - `contact_name` hoặc tên khách theo `registration_id`
  - `start_time - end_time`

- dòng 2:
  - `appointment_type`
  - `appointment_reason`

- có thể giữ nút `Xóa` cho vận hành dashboard nếu vẫn cần

## 8. Gắn lịch hẹn với dữ liệu khách vừa scan

### File chính

- `/Users/ssg/Documents/bamboo_nissin/static/js/mainpy.js`

### Hướng làm

Overlay được mở sau khi `card + face` hoàn tất, nên tại thời điểm này hệ thống đã có dữ liệu khách trong session hiện tại.

Nên tận dụng để prefill:

- `contact_name`
- `registration_id`
- có thể thêm `company` vào `description` nếu cần

### Lợi ích

- dashboard dễ đối chiếu lịch với khách
- giảm nhập tay
- thuận tiện cho việc trace lại lịch được tạo từ session nào

## File dự kiến sẽ phải sửa

- `/Users/ssg/Documents/bamboo_nissin/.env`
- `/Users/ssg/Documents/bamboo_nissin/app_config.py`
- `/Users/ssg/Documents/bamboo_nissin/env_settings.py`
- `/Users/ssg/Documents/bamboo_nissin/routes/dashboard.py`
- `/Users/ssg/Documents/bamboo_nissin/routes/pages.py` hoặc route public mới cho kiosk
- `/Users/ssg/Documents/bamboo_nissin/database/update_database.py`
- `/Users/ssg/Documents/bamboo_nissin/templates/index.html`
- `/Users/ssg/Documents/bamboo_nissin/static/css/styles.css`
- `/Users/ssg/Documents/bamboo_nissin/static/js/mainpy.js`
- `/Users/ssg/Documents/bamboo_nissin/templates/index_dashboard.html`
- `/Users/ssg/Documents/bamboo_nissin/static/css/dashboard.css`
- `/Users/ssg/Documents/bamboo_nissin/static/js/dashboard.js`

## Thứ tự triển khai đề xuất

1. Thêm `APPOINTMENT_OVERLAY_ENABLED` vào `.env` và luồng settings.
2. Mở rộng schema appointment để lưu đủ `type/reason/registration_id/source`.
3. Bổ sung check trùng lịch ở backend.
4. Đồng bộ toggle bật/tắt trên dashboard settings.
5. Tạo API public cho kiosk để đọc lịch ngày và tạo lịch.
6. Thêm confirm modal và overlay vào kiosk.
7. Chèn flow overlay vào `mainpy.js` trước bước thank-you/reset.
8. Sửa dashboard để highlight ngày có lịch màu đỏ.
9. Sửa card danh sách lịch trong ngày theo format nghiệp vụ mới.

## Các quyết định cần giữ cố định khi code

- Nút `Có` và `Không` ở câu hỏi ban đầu:
  - không dùng confirm

- Khi `Huỷ` ở form đặt lịch:
  - phải hiện confirm
  - nếu xác nhận huỷ => đi thẳng sang cảm ơn
  - nếu không xác nhận huỷ => quay lại form đặt lịch

- Có cho phép nhiều cuộc hẹn chồng giờ hay không:
  - theo workflow hiện tại: không

- Có cho tạo appointment từ dashboard thủ công nữa hay không:
  - hiện tại API backend vẫn hỗ trợ
  - dashboard UI hiện chủ yếu là xem/xóa

- Có cho sửa lịch sau khi đã tạo không:
  - hiện tại chưa có yêu cầu
  - chưa cần làm ở phase này

## Kết luận

Phần appointment ở dashboard hiện tại có thể tái sử dụng làm nền dữ liệu, nhưng chưa đủ để phục vụ flow overlay mới ở kiosk.

Để triển khai đúng hướng đã chốt, cần bổ sung đồng thời:

- cờ bật/tắt bằng `.env`
- API public cho kiosk
- overlay + confirm trong kiosk
- mở rộng schema appointment
- check trùng lịch ở backend
- cập nhật dashboard để hiển thị đúng format nghiệp vụ và highlight ngày có lịch bằng màu đỏ
