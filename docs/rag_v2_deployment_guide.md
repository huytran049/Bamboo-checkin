# RAG v2 Deployment Guide

## Mục đích
Tài liệu này hướng dẫn cách triển khai từng bước cho `rag_v2` trong ngày đầu, đồng thời chỉ ra mốc nào nên test lại voice QA để kiểm tra hiệu quả.

## Phase 1

### 1. Kiểm tra taxonomy hiện tại
Chạy:

```bash
python3 scripts/rebuild_rag_v2.py
```

Kết quả mong đợi:
- In ra danh sách nguồn trong `Rag_data`
- Mỗi nguồn có:
  - `doc_type`
  - `source_group`
  - `product`
  - `topic`
  - `chunk_strategy`

Ý nghĩa:
- Đây là bước xác nhận `reset schema ingest` đã bắt đầu đúng hướng.

### 1b. Xem preview chunk mới
Chạy:

```bash
python3 scripts/rebuild_rag_v2.py --mode chunks --limit 40
```

Kết quả mong đợi:
- Thấy từng chunk mới theo taxonomy
- Nhìn rõ:
  - `doc_type`
  - `chunk_type`
  - `section`
  - `text`

Ý nghĩa:
- Đây là bước xác nhận `chunking mới` đã bắt đầu đúng.
- Chưa ảnh hưởng production path.

### 1c. Build index artifact cho rag_v2
Chạy:

```bash
python3 scripts/rebuild_rag_v2.py --mode build
```

Kết quả mong đợi:
- Tạo file index JSON trong `rag/indexes/`
- In ra:
  - `index_path`
  - `chunk_count`
  - `embed_model`
  - `embed_model_reason`
  - `generate_model`

Ý nghĩa:
- Đây là mốc tách `rag_v2` ra khỏi `legacy index`.
- Nếu `embed_model_reason` không phải `preferred_bge`, nghĩa là máy chưa chạy đúng target BGE-M3.

### 1d. Preview retrieval mới
Chạy:

```bash
python3 scripts/rebuild_rag_v2.py --mode retrieve --question "Smart Box dùng để làm gì" --limit 5
```

Kết quả mong đợi:
- In ra:
  - `filters`
  - `candidate_count`
  - danh sách `items` top-k
- Mỗi item có:
  - `source_name`
  - `doc_type`
  - `product`
  - `score`
  - `dense_score`
  - `lexical_score`
  - `keyword_score`

Ý nghĩa:
- Đây là cách kiểm trực tiếp xem Step 4 đã giảm retrieve sai nguồn hay chưa.
- Nếu top-k vẫn lẫn sai domain nhiều, chưa nên nối vào answer path.

### 1e. Preview answer path mới
Chạy:

```bash
python3 scripts/rebuild_rag_v2.py --mode answer --question "Smart Box dùng để làm gì"
```

Kết quả mong đợi:
- In ra object answer hoàn chỉnh:
  - `answer`
  - `answer_mode`
  - `matched_sources`
  - `matched_contexts`
  - `model_name`

Ý nghĩa:
- Đây là bước kiểm trực tiếp `rag_v2` đã có answer path đầy đủ hay chưa.
- Nếu câu trả lời vẫn sai domain hoặc fallback nhiều, chưa nên nối vào route production.

#### Các mốc preview nên kiểm sau bản vá chất lượng
Chạy:

```bash
python3 scripts/rebuild_rag_v2.py --mode answer --question "Bamboo dùng để làm gì"
python3 scripts/rebuild_rag_v2.py --mode answer --question "Smart Box dùng để làm gì"
python3 scripts/rebuild_rag_v2.py --mode answer --question "Inspection Machine có các nút nào"
```

Kết quả mong đợi hiện tại:
- `Bamboo dùng để làm gì`:
  - `answer_mode: faq_extractive`
  - source chính: `bamboo_faq.txt`
- `Smart Box dùng để làm gì`:
  - `answer_mode: qa_extractive`
  - source chính: `Smart_box.txt`
- `Inspection Machine có các nút nào`:
  - không được fallback trắng
  - phải trả ra danh sách nút/chức năng chính

### 1f. Bật rag_v2 cho app thật
Khi muốn cho web `/` và `/qa-voice-demo` dùng backend mới:

```bash
USE_RAG_V2=1 <lenh-khoi-dong-app-cua-ban>
```

Ví dụ nếu bạn đang dùng script khởi động riêng thì export cờ trước khi chạy script đó.

Kết quả mong đợi:
- `POST /api/qa/ask` và `POST /api/qa/ask-stream` đi vào `rag_v2`
- `GET /api/dashboard/qa/rag-status` trả thêm:
  - `active_engine: rag_v2`
  - `rag_v2.is_ready: true`

Checklist test voice QA sau khi bật:
- `Xin chào`
- `SSG có bao nhiêu nhân sự`
- `Smart Box dùng để làm gì`
- `Inspection Machine có các nút nào`

### 2. Chưa đổi route production
Trong phase này:
- `routes/qa.py` vẫn dùng `services.qa_service`
- `rag_v2` chỉ là đường build mới song song

Mục tiêu:
- không làm hỏng voice QA hiện có
- cho phép build mới an toàn

## Khi nào nên test voice QA

### Sau Step 2 - chunking mới
Nên test ngay vì đây thường là mốc đầu tiên cho cải thiện dễ cảm nhận.

Checklist:
- `Xin chào`
- `SSG là gì`
- `Smart Box dùng để làm gì`
- `Inspection Machine có các nút nào`

### Sau Step 3 - embedding/index mới
Nên test lại với câu hỏi dễ nhiễu.

Checklist:
- `Camera AI dùng để làm gì`
- `EcoSave tiết kiệm điện như thế nào`
- `SSG có bao nhiêu nhân sự`

### Sau Step 4 - hybrid retrieval
Đây là mốc nên test kỹ nhất.

Checklist:
- câu có từ khóa rõ
- câu có tên sản phẩm
- câu có yếu tố profile công ty
- câu hỏi manual kỹ thuật

### Sau phần hardening chất lượng
Đây là phase nên test hội thoại voice QA thật trên browser.

Checklist:
- hỏi 1 lượt:
  - `Bamboo dùng để làm gì`
  - `Smart Box dùng để làm gì`
  - `Inspection Machine có các nút nào`
- hỏi nhiều lượt liên tiếp:
  - `Inspection Machine là gì`
  - `còn các nút điều khiển thì sao`
  - `thế phần mềm của nó làm được gì`

Mục tiêu:
- câu follow-up không bị rơi sang domain khác
- câu manual không còn trả lời cụt một nửa

## Tiêu chí pass tạm thời
- Không trả nhầm small-talk khi hỏi về sản phẩm
- Không trả nhầm profile khi hỏi manual
- Nguồn match trong top retrieval phải đúng domain
- Answer voice không bị lan man quá nhiều

## Ghi chú
- Tài liệu này sẽ tiếp tục được cập nhật trong các bước tiếp theo.
- `BGE-M3` hiện chưa có local, nên chưa thể xem là hoàn tất phase embedding target.
- Nếu muốn chốt chất lượng production lâu dài, cần quyết tiếp:
  - cài `BGE-M3`
  - có thêm reranker thật hay chưa
