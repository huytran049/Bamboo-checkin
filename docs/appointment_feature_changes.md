# Ghi chú thay đổi: Màn `Đặt lịch`

## Mục tiêu

Thêm một mục mới trong sidebar tên `Đặt lịch`, đặt phía trên `Cài đặt`.

Màn hình mới cho phép:

- Hiển thị lịch tháng ngay trong dashboard web.
- Người dùng bấm vào một ngày để xem danh sách cuộc hẹn của ngày đó.
- Nếu ngày chưa có cuộc hẹn thì hiển thị `Empty`.
- Người dùng xóa từng cuộc hẹn đã tạo.

Lưu ý kỹ thuật:

- Dự án hiện tại là Flask + HTML + CSS + JavaScript thuần.
- Không có môi trường iOS/Swift để dùng `CalendarKit` native.
- Vì vậy phần lịch đã được triển khai theo kiểu web UI tương đương, chạy trực tiếp trong dashboard hiện có.

## File đã sửa

### 1. `/templates/index_dashboard.html`

Đã thêm menu sidebar mới:

- `Đặt lịch`
- Vị trí: nằm trên `Cài đặt`

Đã thêm một `section` mới với `data-screen="appointments"` gồm:

- Header màn hình `Đặt lịch`
- 3 nút điều hướng tháng:
  - `Tháng trước`
  - `Hôm nay`
  - `Tháng sau`
- Một khối lịch tháng dạng grid
- Một panel chi tiết ngày đã chọn

Các id HTML mới đã được thêm:

- `appointmentPrevMonthBtn`
- `appointmentTodayBtn`
- `appointmentNextMonthBtn`
- `appointmentMonthLabel`
- `appointmentMonthMeta`
- `appointmentsCalendarGrid`
- `appointmentSelectedDateLabel`
- `appointmentStatusMessage`
- `appointmentEmptyState`
- `appointmentDayList`

## 2. `/database/update_database.py`

Đã thêm hằng:

- `APPOINTMENT_TABLE = "appointments"`

Đã mở rộng `setup_database()` để tạo bảng mới:

```sql
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_date TEXT NOT NULL,
    start_time TEXT,
    end_time TEXT,
    title TEXT NOT NULL,
    description TEXT,
    contact_name TEXT,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
)
```

Đã thêm các hàm xử lý dữ liệu cuộc hẹn:

- `_normalize_appointment_date(value)`
- `_normalize_appointment_time(value)`
- `_ensure_appointment_table()`
- `create_appointment(...)`
- `list_appointments_for_date(appointment_date)`
- `list_appointments_for_month(year, month)`
- `delete_appointment(appointment_id)`

### Hành vi chính

`create_appointment(...)`

- Chuẩn hóa ngày theo dạng `YYYY-MM-DD`
- Chuẩn hóa giờ theo dạng `HH:MM`
- Kiểm tra:
  - `title` không được rỗng
  - `end_time >= start_time` nếu cả hai cùng có
- Ghi dữ liệu vào SQLite

`list_appointments_for_date(...)`

- Lấy tất cả cuộc hẹn trong một ngày
- Sắp xếp theo giờ bắt đầu tăng dần
- Những mục không có giờ sẽ nằm sau

`list_appointments_for_month(...)`

- Lấy toàn bộ cuộc hẹn của một tháng
- Dùng để render số lượng cuộc hẹn trên từng ô lịch

`delete_appointment(...)`

- Xóa 1 cuộc hẹn theo `id`

### Tương thích database cũ

Đã thêm `_ensure_appointment_table()` và gọi nó trong các hàm appointment để:

- Nếu file SQLite cũ chưa có bảng `appointments`
- Thì hệ thống sẽ tự tạo bảng khi API appointment được gọi
- Không cần xóa DB cũ

## 3. `/routes/dashboard.py`

Đã import các hàm backend mới:

- `list_appointments_for_month`
- `list_appointments_for_date`
- `create_appointment`
- `delete_appointment`

Đã thêm các API mới dưới prefix `/api/dashboard`:

### `GET /api/dashboard/appointments/month`

Query params:

- `year`
- `month`

Kết quả:

- Trả về tất cả cuộc hẹn của tháng

Ví dụ:

```json
{
  "ok": true,
  "items": []
}
```

### `GET /api/dashboard/appointments/day`

Query params:

- `date=YYYY-MM-DD`

Kết quả:

- Trả về tất cả cuộc hẹn của ngày đó

### `POST /api/dashboard/appointments`

Body JSON:

```json
{
  "appointment_date": "2026-04-04",
  "title": "Hop voi khach hang",
  "start_time": "09:00",
  "end_time": "10:00",
  "contact_name": "Nguyen Van A",
  "description": "Trao doi lich trinh"
}
```

Kết quả:

- Tạo một cuộc hẹn mới
- Trả lại bản ghi vừa tạo

Ghi chú:

- API này vẫn được giữ ở backend.
- Hiện tại form tạo cuộc hẹn trên dashboard đã bị bỏ theo yêu cầu mới.
- Nếu cần, cuộc hẹn vẫn có thể được tạo từ API/tool khác.

### `DELETE /api/dashboard/appointments/<appointment_id>`

Kết quả:

- Xóa một cuộc hẹn theo id

## 4. `/static/js/dashboard.js`

Đã thêm toàn bộ logic frontend cho màn `Đặt lịch`.

### Biến DOM mới

Đã bind các phần tử liên quan đến:

- điều hướng tháng
- grid lịch
- panel chi tiết ngày
- form tạo cuộc hẹn
- thông báo trạng thái

### Trạng thái mới

Đã thêm các state:

- `currentAppointmentMonth`
- `selectedAppointmentDate`
- `appointmentItems`

### Các hàm mới

#### Hỗ trợ xử lý ngày

- `toDateInputValue(date)`
- `getTodayKey()`
- `getAppointmentItemsForDate(dateKey)`
- `formatAppointmentMonthLabel(date)`
- `formatAppointmentDateLabel(dateKey)`
- `formatAppointmentTimeRange(item)`

#### Trạng thái UI

- `showAppointmentStatus(message, isError)`
- `setAppointmentBusy(busy)`

#### Render UI lịch

- `renderAppointmentDayList(dateKey)`
- `selectAppointmentDate(dateKey)`
- `renderAppointmentCalendar()`
- `loadAppointmentsForCurrentMonth(resetMessage)`

### Hành vi người dùng hiện tại

#### Khi mở màn `Đặt lịch`

- Dashboard chuyển sang screen `appointments`
- Tự tải danh sách cuộc hẹn của tháng hiện tại
- Tự chọn ngày hiện tại lúc khởi động

#### Khi bấm một ô ngày

- Ngày đó trở thành ngày đang chọn
- Panel bên phải hiển thị:
  - danh sách cuộc hẹn nếu có
  - `Empty` nếu không có

#### Khi bấm nút điều hướng tháng

- `Tháng trước`: lùi 1 tháng
- `Hôm nay`: quay về tháng hiện tại và chọn ngày hôm nay
- `Tháng sau`: tiến 1 tháng

#### Khi xóa một cuộc hẹn

- Mở confirm modal
- Nếu xác nhận:
  - gọi `DELETE /api/dashboard/appointments/<id>`
  - reload lại lịch tháng và panel ngày

### Tích hợp với search bar hiện tại

Đã chỉnh `updateSearchUiForScreen()`:

- Khi vào screen `appointments`
  - ô search global bị disable
  - placeholder đổi thành `Lịch hẹn không dùng tìm kiếm toàn cục`

Đã chỉnh `bindSearchInput(...)`:

- Nếu đang ở screen `appointments` thì bỏ qua logic search cũ

### Tích hợp với vòng refresh định kỳ

Đã thêm logic:

- Nếu screen hiện tại là `appointments`
- Dashboard sẽ refresh lại dữ liệu lịch theo chu kỳ đang có sẵn

## 5. `/static/css/dashboard.css`

Đã thêm CSS cho toàn bộ giao diện lịch:

- `.appointments-layout`
- `.appointments-calendar-card`
- `.appointments-detail-panel`
- `.appointments-weekdays`
- `.appointments-calendar-grid`
- `.appointment-day-cell`
- `.appointment-day-number`
- `.appointment-day-count`
- `.appointments-empty`
- `.appointments-day-list`
- `.appointment-item`
- `.appointment-item-head`
- `.appointment-item-time`
- `.appointment-item-contact`
- `.appointment-item-desc`

### Tối ưu hiển thị

Đã thêm style cho:

- ô ngày được chọn
- ô hôm nay
- ô có cuộc hẹn
- ngày nằm ngoài tháng hiện tại

### Responsive

Ở màn hình nhỏ:

- layout lịch chuyển từ 2 cột sang 1 cột
- form giờ bắt đầu / kết thúc chuyển từ 2 cột sang 1 cột

### Bổ sung icon fallback

Đã thêm:

```css
.ti-calendar::before { content: "\1F4C5"; }
```

để nếu font icon không tải được thì menu `Đặt lịch` vẫn có biểu tượng thay thế.

### Bổ sung style cho textarea

Đã mở rộng rule `.modal-field` để hỗ trợ:

- `textarea`
- chiều cao tối thiểu
- resize theo chiều dọc

## Kiểm tra đã chạy

Đã chạy kiểm tra cú pháp:

### Python

```bash
python3 -m py_compile /Users/ssg/Documents/bamboo_nissin/database/update_database.py /Users/ssg/Documents/bamboo_nissin/routes/dashboard.py
```

Kết quả:

- Thành công
- Không có lỗi cú pháp

### JavaScript

```bash
node --check /Users/ssg/Documents/bamboo_nissin/static/js/dashboard.js
```

Kết quả:

- Thành công
- Không có lỗi cú pháp

## Những gì chưa làm

- Chưa tích hợp thư viện `CalendarKit` native vì codebase hiện tại không phải iOS/Swift app.
- Chưa thêm edit/sửa cuộc hẹn.
- Chưa có UI tạo cuộc hẹn trong dashboard sau khi bỏ form theo yêu cầu mới.
- Chưa thêm lọc cuộc hẹn theo người liên hệ hoặc tiêu đề.
- Chưa thêm test tự động cho API appointment.
- Chưa chạy kiểm thử UI end-to-end trong trình duyệt.

## Cách kiểm tra thủ công

1. Restart app để backend reload code mới.
2. Mở dashboard.
3. Trong sidebar, bấm `Đặt lịch`.
4. Chọn một ngày bất kỳ.
5. Nếu chưa có dữ liệu thì panel phải hiện `Empty`.
6. Nếu database đã có dữ liệu cuộc hẹn:
   - ô ngày phải hiển thị số lượng cuộc hẹn
   - panel ngày phải hiển thị đúng danh sách
7. Thử xóa một cuộc hẹn có sẵn.
8. Xác nhận lịch và panel cập nhật lại đúng.

## Ghi chú kiểm soát

Nếu bạn muốn, bước tiếp theo tôi có thể viết thêm:

- tài liệu đặc tả API riêng cho appointment
- seed data mẫu cho lịch hẹn
- chức năng sửa cuộc hẹn
- chức năng click vào ngày rồi mở modal chi tiết lớn hơn
- chức năng tìm kiếm/lọc lịch hẹn
