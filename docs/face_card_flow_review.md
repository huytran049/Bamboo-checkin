# Face Logic Trong Card Flow

## Mục tiêu

Tài liệu này tóm tắt lại phần logic face trong `card flow`, giải thích vì sao:

- khi chưa đưa card vào vẫn có thể thấy khung xanh
- nhưng sau khi quét card xong, bước face rất kém nhạy
- mặt đã đưa vào gần đúng khung nhưng không đổi sang xanh để `ready to capture`

File này chỉ để phân tích logic hiện tại, không phải bản sửa code.

## Kết luận ngắn

Lỗi chính không phải là `face detect` bị tắt trong `card flow`.

Lỗi chính là:

- hệ thống vẫn detect được mặt
- nhưng điều kiện để được coi là `ready to capture` đang quá chặt
- nên khung không đổi xanh dù người dùng cảm giác đã đưa mặt vào đúng vị trí

Nói ngắn gọn:

- `detect face` vẫn chạy
- nhưng `face readiness detection` đang kém
- nên UI không chuyển sang trạng thái sẵn sàng chụp

## Bản chất logic hiện tại

Trong flow hiện tại có 2 lớp điều kiện:

### 1. Detect face

Chỉ cần model tìm ra được bbox khuôn mặt.

Điều này có thể xảy ra cả khi khuôn mặt chưa nằm trong ellipse guide.

### 2. Ready to capture

Chỉ khi khuôn mặt thỏa đủ điều kiện thì UI mới đổi xanh và cho phép chụp:

- mặt nằm trong vùng guide
- mặt đủ lớn
- mặt ổn định liên tục trong một khoảng thời gian

Vì vậy:

- ngoài ellipse vẫn có thể detect mặt
- nhưng chỉ khi vào đúng điều kiện guide thì mới được capture

## Vì sao không có card vẫn thấy khung xanh

Đây không phải là dấu hiệu cho thấy logic card bị lỗi riêng.

Lý do là:

- khi ở `IDLE`, app vẫn có thể gọi face detection
- nếu bbox mặt tình cờ nằm đúng guide thì UI vẫn có thể hiện trạng thái valid

Nên hiện tượng:

- chưa đưa card mà vẫn thấy khung xanh

là phù hợp với logic hiện tại.

## Vì sao sau khi quét card xong thì face rất kém

Sau khi quét card, app chuyển sang phase `FACE`.

Lúc này hệ thống không chỉ cần thấy mặt, mà cần:

- bbox mặt nằm đúng trong guide
- kích thước mặt vượt ngưỡng tối thiểu
- giữ ổn định đủ lâu để countdown hoàn thành

Chỉ cần một trong các điều kiện trên không đạt thì:

- khung không đổi xanh
- countdown không chạy hoặc bị reset
- không kích hoạt capture

Đây là lý do người dùng thấy:

- mặt đã vào gần đúng vị trí
- nhưng UI vẫn không sẵn sàng chụp

## Điểm yếu chính của logic hiện tại

### 1. Điều kiện inside guide quá chặt

Logic hiện tại không chỉ hỏi "có detect mặt hay không".

Nó hỏi:

- tâm bbox có nằm trong ellipse không
- chiều cao bbox có đủ lớn không

Điều này làm cho hệ thống rất nhạy với:

- lệch tâm nhẹ
- rung bbox nhẹ
- mặt hơi nhỏ hơn kỳ vọng

### 2. Reset quá dễ

Nếu có frame không đạt điều kiện thì timer sẵn sàng chụp có thể bị reset.

Hệ quả:

- người dùng tưởng là đã gần đạt
- nhưng hệ thống luôn quay lại từ đầu

### 3. Chất lượng frame detect còn thấp

Face detection hiện đang chạy trên ảnh đã:

- resize xuống nhỏ
- nén JPEG

Điều này làm bbox dao động nhiều hơn, đặc biệt khi:

- ánh sáng kém
- người dùng vừa di chuyển xong
- còn tay/card/vật thể trong khung

### 4. Card flow làm lộ nhược điểm này rõ hơn

Không phải card flow làm hỏng detect.

Nhưng card flow làm người dùng thường ở trạng thái:

- vừa cầm card xong
- tay chưa rút ra hết
- vị trí đứng chưa ổn định
- chuyển hướng nhìn từ card sang camera hơi lệch

Trong điều kiện đó, một logic `ready to capture` quá chặt sẽ fail rất nhiều.

## Kết luận đúng về lỗi

Không nên mô tả lỗi là:

- flow card bị rơi
- card loop cướp mất face loop
- chỉ detect được khi không có card

Mô tả đúng hơn là:

> Trong `card flow`, bước face `ready to capture` rất kém nhạy. Hệ thống vẫn detect được mặt, nhưng không dễ xác nhận mặt là hợp lệ để đổi khung sang xanh và chụp.

Hoặc ngắn hơn:

> `Face detection exists, but face readiness detection is too strict.`

## Nếu muốn cải thiện thì cần sửa ở đâu

Ưu tiên theo thứ tự:

### 1. Frontend logic face

File chính:

- `static/js/mainpy.js`

Cần xem lại:

- điều kiện `isFaceInsideGuide(...)`
- ngưỡng kích thước mặt tối thiểu
- thời gian ổn định trước khi chụp
- cách reset timer khi lệch 1 vài frame
- chất lượng frame gửi sang detector

### 2. Guide UI

File:

- `static/css/styles.css`

Cần xem:

- kích thước ellipse guide
- guide hiện tại có quá hẹp / quá cao không

### 3. Backend chọn bbox mặt

File:

- `face/face_function.py`

Chỉ cần sửa nếu muốn:

- thay đổi cách chọn `best` face
- thêm hậu xử lý để bbox ổn định hơn

## Hướng cải thiện đề xuất

Nếu muốn cải thiện hiệu quả mà vẫn đúng hướng, nên ưu tiên:

1. Nới điều kiện `inside guide`
2. Nới ngưỡng kích thước mặt tối thiểu
3. Thêm smoothing cho bbox
4. Không reset countdown ngay chỉ vì lệch 1 frame
5. Tăng chất lượng ảnh gửi sang face detector
6. Điều chỉnh ellipse guide cho phù hợp góc cam thực tế

## Ghi chú tinh chỉnh cho Mac Mini

Sau khi kiểm tra thêm luồng hiện tại, hai tham số đáng ưu tiên tinh chỉnh là:

### 1. `presenceFps`

Trong phase `FACE`, loop detect hiện quyết định trực tiếp số lượng frame hợp lệ liên tiếp mà hệ thống có thể tích lũy để chụp.

Khuyến nghị test trên Mac Mini:

- mức an toàn: `18`
- mức nên thử đầu tiên: `20`
- mức cao nhưng vẫn hợp lý nếu máy còn dư tài nguyên: `24`

Không nên nhảy thẳng lên quá cao ngay từ đầu, vì còn chi phí:

- encode JPEG
- request frontend -> Flask
- Apple Vision detect
- render overlay

### 2. Delay trước khi bắt đầu tính capture trong phase `FACE`

Hiện tượng người dùng đã đưa mặt vào khung nhưng hệ thống chưa tính countdown thường đến từ delay đầu vào của phase `FACE`.

Khuyến nghị test:

- khoảng hợp lý: `250ms` đến `400ms`
- mốc nên thử đầu tiên: `300ms`

## Thiết lập hiện tại đã áp dụng

Để test thực tế trên máy hiện tại, đã áp dụng:

- `presenceFps = 20`
- `faceCaptureReadyAtMs = Date.now() + 300`

Mục tiêu của cấu hình này là:  

- bắt đầu tính capture sớm hơn
- tăng số frame hợp lệ liên tiếp
- giảm hiện tượng phải đưa mặt vào nhiều lần mới chụp

## Phát hiện thêm: CCCD không QR

Qua kiểm tra log và worker CCCD, đã xác định thêm một nguyên nhân riêng cho trường hợp:

- CCCD có QR: face nhạy hơn
- CCCD không QR: Cam2 chậm và khó vào `ready to capture`

Điểm quan trọng:

- trường hợp này không nhất thiết fallback sang business card
- nhưng vẫn có thể rất chậm trước khi vào `FACE`

Nguyên nhân:

- frontend luôn chờ `analyzeCardCanvasForCccd(...)` xong mới arm face capture
- với CCCD không QR, worker CCCD phải dựa nhiều hơn vào OCR text parsing
- Swift worker hiện đã từng crash ở nhánh regex parsing, làm request `/api/ocr/cccd_qr_ocr` kéo dài nhiều giây

Hệ quả:

- người dùng tưởng đã tới bước chụp mặt
- nhưng thực tế phase `FACE` chưa được arm
- tới khi vào `FACE` thì người dùng đã lệch nhịp, tạo cảm giác giống hệt card flow

## Bản vá đã áp dụng cho CCCD không QR

Đã vá trong:

- `workers_swift/cccd_qr_ocr_worker.swift`

Nội dung:

- chặn truy cập regex capture group ngoài phạm vi
- sửa regex parse tên để luôn có capture group hợp lệ

Mục tiêu:

- tránh crash Swift worker ở nhánh OCR CCCD không QR
- giảm thời gian chờ trước khi vào `FACE`
- giúp trải nghiệm Cam2 bớt giống business card flow

## Câu trả lời ngắn cho team

Có thể dùng đoạn này để mô tả lỗi:

> Trong `card flow`, face detector vẫn hoạt động nhưng phần đánh giá `ready to capture` đang quá khắt khe. Vì vậy người dùng đã đưa mặt vào gần đúng khung mà UI vẫn không chuyển xanh, dẫn đến không kích hoạt chụp ảnh.
