# Luong OCR CCCD

## Muc tieu

Flow CCCD duoc tach rieng voi flow danh thiep:

- Phat hien anh tu `cam card` co phai CCCD hay khong
- Neu la CCCD thi uu tien `QR + OCR`
- Luu du lieu CCCD vao `registrations/<reg_id>/data.json`
- Hien thi tren dashboard muc `Can cuoc cong dan`
- Khong insert nham vao SQLite `registrations` cua danh thiep

## Tong quan luong

1. Camera card chup anh the.
2. Frontend gui anh sang endpoint phan tich CCCD.
3. Backend goi worker CCCD de doc `QR + OCR`.
4. Neu ket qua duoc nhan dien la CCCD:
   - frontend fill form CCCD
   - frontend goi API luu nhap CCCD
   - backend ghi vao `registrations/<reg_id>/data.json`
5. Neu khong phai CCCD:
   - frontend roi ve flow OCR danh thiep cu

## Cac diem vao chinh

### 1. Frontend bat dau tu cam card

File: [static/js/mainpy.js](/Users/ssg/Documents/bamboo_nissin/static/js/mainpy.js)

- Ham `handleScanBCard()` chup anh tu camera card
- Sau khi co canvas anh, frontend goi:
  - `analyzeCardCanvasForCccd(canvas)`
- Neu ham nay tra ve `null`:
  - moi chay tiep OCR danh thiep bang `startAsyncBcardOcrFromCanvas(canvas)`

Dieu nay giup thu CCCD truoc, danh thiep sau.

### 2. Endpoint phan tich CCCD

File: [routes/ocr.py](/Users/ssg/Documents/bamboo_nissin/routes/ocr.py)

Endpoint:

- `POST /api/ocr/cccd_qr_ocr`

Backend nhan file anh va goi:

- `run_cccd_qr_ocr_from_image_bytes(...)`

trong file [services/cccd_service.py](/Users/ssg/Documents/bamboo_nissin/services/cccd_service.py)

## Logic nhan dien CCCD

Frontend hien tai xac dinh CCCD theo 2 lop:

### 1. Tin vao backend/worker

Neu response tra ve:

- `is_cccd = true`

thi frontend coi do la CCCD.

### 2. Fallback phia frontend

Ngay ca khi `is_cccd = false`, frontend van tu kiem tra lai trong:

- `isLikelyCccdResult(js)`

Rule fallback:

- Neu `qr.parsed.idNumber` co gia tri thi coi la CCCD
- Hoac parse lai tu `qr.raw`
- Hoac OCR co du keyword CCCD va du field manh

Keyword dang dung:

- `can cuoc`
- `citizen identity`
- `ngay sinh`
- `gioi tinh`
- `noi thuong tru`
- `place of residence`

Field manh dang check:

- `idNumber`
- `fullName`
- `dob`
- `gender`
- `address`

## Merge du lieu QR va OCR

Sau khi backend tra ve JSON:

- Frontend parse them QR raw bang `parseVNIdQr(...)`
- Neu QR raw hop le thi merge vao `js.data`

Thu tu uu tien thuc te:

- `QR` uu tien cho:
  - `idNumber`
  - `fullName`
  - `dob`
  - `gender`
  - `address`
  - `issued`
- `OCR` dung de bo sung khi QR thieu hoac de fallback

## Luu nhap CCCD

File: [static/js/mainpy.js](/Users/ssg/Documents/bamboo_nissin/static/js/mainpy.js)

Sau khi nhan dien duoc CCCD:

- `applyCccdFields(js.data || {})`
- `saveCccdDraftInBackground(js, imageDataUrl)`

Frontend goi endpoint:

- `POST /api/cccd/draft`

File route:

- [routes/registration.py](/Users/ssg/Documents/bamboo_nissin/routes/registration.py)

Service xu ly:

- [services/registration.py](/Users/ssg/Documents/bamboo_nissin/services/registration.py)
- Ham `save_cccd_draft(payload)`

API nay se:

- tao `registration_id` neu chua co
- luu du lieu CCCD vao `data.json`
- luu anh the vao folder registration neu co
- gan cac key phu nhu:
  - `cccd_scan_status`
  - `cccd_field_meta`
  - `cccd_qr_raw`
  - `cccd_ocr_text`

## Cau truc `data.json` cua CCCD

Phan CCCD chinh nam trong:

```json
{
  "data": {
    "fullName": "",
    "idNumber": "",
    "dob": "",
    "issued": "",
    "address": "",
    "oldId": "",
    "gender": "",
    "expiry": ""
  }
}
```

Ngoai ra con co the co:

```json
{
  "cccd_scan_status": "draft",
  "cccd_field_meta": {},
  "cccd_qr_raw": "",
  "cccd_ocr_text": "",
  "last_qr_raw": ""
}
```

## Tach biet voi flow danh thiep

### Danh thiep

Flow danh thiep van dung:

- OCR async
- SQLite `registrations`
- dashboard registrations

### CCCD

Flow CCCD hien tai:

- luu vao `registrations/<reg_id>/data.json`
- dashboard CCCD doc tu folder `registrations`
- khong insert vao SQLite danh thiep neu chi co du lieu CCCD

Logic tach nay nam trong:

- [services/registration.py](/Users/ssg/Documents/bamboo_nissin/services/registration.py)

Ham `save_registration(payload)` co 3 nhanh:

1. Co du lieu danh thiep:
   - save vao SQLite
2. Dang cho OCR danh thiep (`pending_bcard_ocr`):
   - tao placeholder row cho danh thiep
3. Chi co du lieu CCCD:
   - bo qua SQLite danh thiep

## Dashboard CCCD

Dashboard CCCD khong doc tu bang SQLite rieng.

No doc tu:

- `registrations/*/data.json`

Code nam trong:

- [database/update_database.py](/Users/ssg/Documents/bamboo_nissin/database/update_database.py)
- [routes/dashboard.py](/Users/ssg/Documents/bamboo_nissin/routes/dashboard.py)

Dashboard normalize cac field:

- `id_number`
- `full_name`
- `dob`
- `issued`
- `address`
- `old_id`
- `gender`
- `expiry`

Neu `data` rong nhung van co `cccd_qr_raw` hoac `last_qr_raw`, backend se co fallback parse lai QR raw de hien table.

## Giao dien bang CCCD

Giao dien bang `CCCD` duoc thiet ke de giong format cua bang `registrations`, nhung duoc tach thanh mot man hinh rieng trong dashboard.

### Vi tri trong dashboard

File giao dien:

- [templates/index_dashboard.html](/Users/ssg/Documents/bamboo_nissin/templates/index_dashboard.html)

Menu sidebar co 2 man chinh:

- `ダッシュボード` cho registrations
- `Căn cước công dân` cho CCCD

Khi bam vao muc `Căn cước công dân`, frontend doi sang:

- `<section class="app-screen" data-screen="cccd">`

Chu khong render them mot bang moi ben duoi registrations.

### Bo cuc tong the

Man `CCCD` giu cung mot layout tong the nhu man `registrations`:

- 1 toolbar tren cung
- 1 khu table ben trai
- 1 panel detail ben phai
- 1 hang pagination ben duoi table

Format layout dung cung class:

- `database-layout`
- `database-layout-row`
- `database-layout-main`
- `guest-detail-panel`

Dieu nay giup:

- do rong bang
- kieu vien, shadow, spacing
- cach chia cot trai/phai

giong voi man `registrations`.

### Toolbar tren cung

Toolbar cua `CCCD` giong registrations o cach dat thanh phan:

- ben trai la tieu de `CCCD`
- ben phai la 2 nut export

Nut hien tai:

- `JSON出力`
- `EXCEL出力`

Code lien quan:

- [templates/index_dashboard.html](/Users/ssg/Documents/bamboo_nissin/templates/index_dashboard.html)
- [static/js/dashboard.js](/Users/ssg/Documents/bamboo_nissin/static/js/dashboard.js)

Frontend bind event:

- `cccdExportJsonBtn`
- `cccdExportExcelBtn`

va goi:

- `/api/dashboard/cccd/export.json`
- `/api/dashboard/cccd/export.xlsx`

### Khu table ben trai

Bang `CCCD` dung cung style table voi registrations:

- `table`
- `table-hover`
- `table-responsive`
- `table-scroll-area`

Bang duoc render trong:

- `#cccdTable`
- `#cccdTableBody`

Neu khong co du lieu thi hien:

- `#cccdEmptyRow`

No giong registrations o cac diem sau:

- co `thead`
- co `tbody`
- row clickable
- hover row
- row duoc select de hien detail ben phai
- co pagination rieng

### Cac cot hien tai cua bang CCCD

Sau cac lan chinh sua gan day, bang `CCCD` hien tai duoc dinh huong theo format registrations nhung voi noi dung CCCD.

Ve nghiep vu, cac cot chinh la:

- `Số CCCD`
- `Họ và tên`
- `Giới tính`
- `Ngày sinh`
- `Địa chỉ`
- `Thời gian đăng ký`
- `Thao tác`

Trong code/table goc van co the thay mot so cot cu nhu:

- `登録ID`
- `発行日`

nhung logic render hien tai da huong toi viec:

- an `Mã đăng ký`
- an `Ngày cấp`
- dua `Sửa` / `Xóa` ra cot cuoi

Phan render row nam trong:

- [static/js/dashboard.js](/Users/ssg/Documents/bamboo_nissin/static/js/dashboard.js)

va duoc tao bang DOM thay vi HTML co dinh.

### Cot thao tac

Giong registrations, bang `CCCD` co cot thao tac o cuoi dong.

Moi dong co:

- nut `Sửa`
- nut `Xóa`

CSS dung chung:

- `.action-btn`
- `.action-edit`
- `.action-delete`

Logic JS:

- `openCccdEditModal(item)`
- `deleteCccd(regId)`

Nut `Sửa` mo modal edit CCCD.
Nut `Xóa` xoa du lieu CCCD trong `data.json`, sau do row bien mat khoi bang neu khong con du lieu CCCD.

### Panel detail ben phai

Ben phai bang la panel detail giong registrations, nhung don gian hon.

Registrations co:

- thong tin
- hinh anh
- recent activity
- OCR text

CCCD hien tai chi giu:

- tieu de `Chọn CCCD`
- 1 card `Trich xuat JSON`

Khi click vao mot dong:

- frontend goi detail API
- do `extracted_json` vao `#cccdDetailJson`
- cap nhat `#cccdDetailName`

Code lien quan:

- [static/js/dashboard.js](/Users/ssg/Documents/bamboo_nissin/static/js/dashboard.js)

### Pagination

Bang `CCCD` co phan trang rieng giong registrations:

- nut `Prev`
- thong tin trang
- nut `Next`

Bien frontend:

- `cccdPagination.page`
- `cccdPagination.totalPages`
- `cccdPagination.total`

Nut dieu huong:

- `cccdPrevBtn`
- `cccdNextBtn`

### Cac file giao dien lien quan

Neu muon sua UI bang `CCCD`, cac file chinh la:

- [templates/index_dashboard.html](/Users/ssg/Documents/bamboo_nissin/templates/index_dashboard.html)
- [static/js/dashboard.js](/Users/ssg/Documents/bamboo_nissin/static/js/dashboard.js)
- [static/css/dashboard.css](/Users/ssg/Documents/bamboo_nissin/static/css/dashboard.css)

### Tom tat giao dien

Man `CCCD` dang duoc to chuc de giong format `registrations` theo huong:

- cung sidebar dashboard
- cung kieu toolbar
- cung kieu table ben trai
- cung kieu panel detail ben phai
- cung co pagination
- cung co export
- cung co thao tac sua/xoa

Khac biet chinh la:

- registrations tap trung vao danh thiep va hinh anh
- CCCD tap trung vao du lieu trich xuat JSON va cac field dinh danh

## Cac endpoint lien quan

### OCR CCCD

- `POST /api/ocr/cccd_qr_ocr`

### Luu nhap CCCD

- `POST /api/cccd/draft`

### Dashboard CCCD

- `GET /api/dashboard/cccd`
- `GET /api/dashboard/cccd/<reg_id>`
- `GET /api/dashboard/cccd/export.json`
- `GET /api/dashboard/cccd/export.xlsx`

## Diem can luu y hien tai

1. Worker CCCD duoc khai bao trong [services/cccd_service.py](/Users/ssg/Documents/bamboo_nissin/services/cccd_service.py) la:
   - `workers_swift/cccd_qr_ocr_worker.swift`

2. Neu file worker nay khong ton tai tren may, endpoint CCCD se fail runtime.

3. Dashboard CCCD chi hien du lieu khi trong `data.json` co:
   - `data.*`
   - hoac co `cccd_qr_raw` / `last_qr_raw` hop le de fallback

4. Flow CCCD hien la flow luu nhap theo folder registration, khong phai bang SQLite rieng.

## File chinh can doc neu muon debug

- [static/js/mainpy.js](/Users/ssg/Documents/bamboo_nissin/static/js/mainpy.js)
- [routes/ocr.py](/Users/ssg/Documents/bamboo_nissin/routes/ocr.py)
- [services/cccd_service.py](/Users/ssg/Documents/bamboo_nissin/services/cccd_service.py)
- [routes/registration.py](/Users/ssg/Documents/bamboo_nissin/routes/registration.py)
- [services/registration.py](/Users/ssg/Documents/bamboo_nissin/services/registration.py)
- [database/update_database.py](/Users/ssg/Documents/bamboo_nissin/database/update_database.py)
- [routes/dashboard.py](/Users/ssg/Documents/bamboo_nissin/routes/dashboard.py)

## Tom tat ngan

- Camera card chup anh
- Frontend thu nhan dien CCCD truoc
- Backend/worker tra ket qua `QR + OCR`
- Neu la CCCD thi luu nhap vao `registrations/<reg_id>/data.json`
- Dashboard CCCD doc tu cac `data.json`
- Neu khong phai CCCD thi moi chay flow danh thiep
