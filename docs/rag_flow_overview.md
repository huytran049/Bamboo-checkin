# Sơ Đồ Luồng RAG Hiện Tại

## 1. Mục tiêu
- Mô tả ngắn gọn quy trình Q&A/RAG hiện tại của dự án Bamboo.
- Làm rõ luồng dữ liệu từ `Rag_data` đến câu trả lời cuối cùng.
- Chỉ ra các điểm kiểm soát chất lượng đang có trong hệ thống.

## 2. Thành phần chính
- Nguồn dữ liệu: [Rag_data](/Users/ssg/Documents/bamboo_nissin/Rag_data)
- Lõi xử lý RAG: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- API Q&A: [qa.py](/Users/ssg/Documents/bamboo_nissin/routes/qa.py)
- Lưu lịch sử và index: [update_database.py](/Users/ssg/Documents/bamboo_nissin/database/update_database.py)
- Frontend voice demo: [qa_voice_demo.js](/Users/ssg/Documents/bamboo_nissin/static/js/qa_voice_demo.js)
- Script rebuild index: [rebuild_rag_index.py](/Users/ssg/Documents/bamboo_nissin/scripts/rebuild_rag_index.py)
- Script eval retrieval: [run_qa_retrieval_eval.py](/Users/ssg/Documents/bamboo_nissin/scripts/run_qa_retrieval_eval.py)

## 3. Sơ đồ luồng tổng thể
```text
Rag_data/*.txt, *.md
    |
    v
[Làm sạch văn bản]
    |
    v
[Chunking + overlap + metadata]
    |
    v
[Embedding document chunks bằng QA_EMBED_MODEL]
    |
    v
[Lưu SQLite: qa_rag_chunks + qa_rag_index_state]
    |
    v
================================================================
Người dùng hỏi câu hỏi
    |
    v
[/api/qa/ask hoặc /api/qa/ask-stream]
    |
    v
[Router]
    |----> rule
    |----> faq
    |----> dynamic_reserved
    |----> rag
    |
    v
[Guard ngoài domain]
    |
    v
[Embedding query]
    |
    v
[Retrieve hybrid]
    - semantic score
    - keyword score
    - source priority
    - focus rerank
    |
    v
[Confidence gate]
    |
    +----> fail -> fallback
    |
    v
[Chọn ngữ cảnh augmentation]
    |
    +----> faq_extractive
    +----> extractive_fast
    +----> prompt + generate model
    |
    v
[Postprocess answer]
    |
    v
[Lưu qa_history theo session]
    |
    v
[Trả text stream + TTS]
```

## 4. Luồng build index
- Bước 1:
  - Quét toàn bộ file `.txt` và `.md` trong `Rag_data`.
- Bước 2:
  - Làm sạch văn bản.
  - Loại bỏ markdown noise, bullet, heading, khoảng trắng dư.
- Bước 3:
  - Tách thành block theo đoạn.
  - Chunk theo số từ mục tiêu và overlap.
- Bước 4:
  - Gắn metadata:
    - `topic`
    - `product`
    - `lang`
    - `source_kind`
    - `priority`
    - `updated_at`
- Bước 5:
  - Embed từng chunk bằng `QA_EMBED_MODEL`.
- Bước 6:
  - Chuẩn hóa vector.
  - Lưu vào SQLite.

## 5. Luồng trả lời câu hỏi
- Bước 1:
  - API nhận câu hỏi từ UI.
- Bước 2:
  - Router phân loại câu hỏi:
    - `rule`
    - `faq`
    - `rag`
    - `dynamic_reserved`
- Bước 3:
  - Nếu là ngoài domain thì fallback sớm.
- Bước 4:
  - Nếu đi `rag`, hệ thống embed query.
- Bước 5:
  - Retrieve các chunk liên quan.
- Bước 6:
  - Rerank theo trọng tâm câu hỏi:
    - focus term
    - focus phrase
    - intent marker
- Bước 7:
  - Kiểm tra confidence.
  - Nếu không đủ chắc chắn thì fallback.
- Bước 8:
  - Nếu đủ chắc chắn:
    - `faq` -> `faq_extractive`
    - factual rõ -> `extractive_fast`
    - còn lại -> `rag generate`
- Bước 9:
  - Hậu xử lý answer.
  - Lưu lịch sử vào `qa_history`.
- Bước 10:
  - Trả text thường hoặc text stream ra frontend.
  - Nếu cần, gọi TTS.

## 6. Các cơ chế chất lượng đang có
- Source filter theo chủ đề/sản phẩm.
- Guard câu hỏi ngoài phạm vi.
- Chặn FAQ leakage vào nhánh RAG thường.
- Confidence gate:
  - score tối thiểu
  - keyword score tối thiểu
  - margin top-1 / top-2
- Context augmentation có chọn lọc.
- Fast path chỉ dùng trong phạm vi hẹp.
- Cache:
  - answer cache
  - retrieval cache
  - query embedding cache
  - TTS cache
- Eval retrieval bằng bộ dataset nội bộ.

## 7. Điểm cần theo dõi thêm
- Đúng nguồn nhưng chưa đúng trọng tâm.
- Đầu vào voice có thể sai do STT.
- Generate model hiện tại cần benchmark riêng theo phần cứng.
- Bộ eval hiện cần mở rộng thêm case thực chiến.

## 8. Kết luận
- Hệ thống RAG hiện tại đã có đủ pipeline vận hành:
  - ingest
  - chunk
  - embed
  - index
  - retrieve
  - rerank
  - augment
  - generate
  - history
  - TTS
- Trọng tâm cải thiện tiếp theo:
  - tăng độ bám sát trọng tâm câu hỏi
  - mở rộng eval thực chiến
  - benchmark lại generate model theo đúng phần cứng đang dùng
