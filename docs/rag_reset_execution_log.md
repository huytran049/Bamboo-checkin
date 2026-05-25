# RAG Reset Execution Log

## Mục tiêu
- Tách RAG cũ khỏi hướng phát triển lâu dài.
- Dựng `rag_v2` song song để build lại từ taxonomy dữ liệu trước, rồi mới cutover.
- Ghi rõ bước nào có thể tạo cải thiện rõ rệt để test lại voice QA ngay.

## Trạng thái hiện tại
- `services/qa_service.py` là runtime path hiện tại và được xem là `legacy`.
- Index hiện tại là `legacy index`, build theo chunk cũ và embedding cũ.
- Bước đầu tiên đã bắt đầu: tạo khung `services/rag_v2` và script kiểm tra taxonomy.

## Log

### 2026-05-06 - Step 1 - Freeze legacy and scaffold rag_v2
- Tạo package mới:
  - `services/rag_v2/__init__.py`
  - `services/rag_v2/schema.py`
  - `services/rag_v2/loaders.py`
  - `services/rag_v2/chunkers.py`
  - `services/rag_v2/service.py`
- Tạo script:
  - `scripts/rebuild_rag_v2.py`
- Chưa cutover production.
- Chưa thay route `/api/qa/ask` và `/api/qa/ask-stream`.

### 2026-05-06 - Step 2 - Implement chunking by document type
- Chuyển `draft chunk strategy` thành chunk builder thực tế cho từng loại tài liệu.
- Thêm `RagChunk` và `build_chunks(...)`.
- Thêm `preview_chunks(...)` để xem trước chunk mới mà chưa ảnh hưởng runtime path cũ.
- Cập nhật `scripts/rebuild_rag_v2.py`:
  - `--mode taxonomy`
  - `--mode chunks --limit N`
- Chưa build index mới.
- Chưa thay model embedding/generation.

### 2026-05-06 - Step 3 - Build standalone rag_v2 index artifact
- Tạo `services/rag_v2/indexer.py`.
- Tạo index artifact JSON độc lập tại `rag/indexes/`.
- Tách hoàn toàn khỏi `legacy index` hiện có trong SQLite.
- Ưu tiên `BGE-M3` nếu có sẵn trong Ollama.
- Nếu `BGE-M3` chưa có, fallback sang model embedding đã cài và ghi rõ reason.
- Ưu tiên `Qwen 8B` cho generation model target của `rag_v2`.

#### Ghi chú model ở thời điểm hiện tại
- `BGE-M3` hiện chưa có sẵn trong Ollama local.
- `Qwen3:8b` có sẵn.
- Vì vậy Step 3 có thể build index mới ngay, nhưng chưa đạt đúng target embedding cuối cùng nếu chưa cài thêm model.

### 2026-05-06 - Step 4 - Hybrid retrieval + metadata filtering
- Tạo `services/rag_v2/retriever.py`.
- Retriever mới gồm:
  - `dense score`
  - `lexical score`
  - `keyword overlap`
  - `doc_type bonus`
  - `metadata filter`
- Thêm `preview_retrieval(...)`.
- Cập nhật `scripts/rebuild_rag_v2.py`:
  - `--mode retrieve --question "..."`
- Chưa nối vào production route.
- Đây là mốc có kỳ vọng cải thiện retrieval rõ nhất trước khi sang answer path.

### 2026-05-06 - Step 5 - Answer path with Qwen 8B target
- Tạo `services/rag_v2/generator.py`.
- Tạo `services/rag_v2/qa.py`.
- Answer path mới:
  - retrieve bằng `rag_v2`
  - nếu top result là `faq` hoặc `small_talk` thì trả theo nhánh extractive
  - nếu là product/manual/profile thì build prompt và gọi model generate
  - fallback về extractive nếu generate lỗi
- Cập nhật `scripts/rebuild_rag_v2.py`:
  - `--mode answer --question "..."`
- Chưa nối `/api/qa/ask` và `/api/qa/ask-stream` sang `rag_v2`.

### 2026-05-06 - Step 6 - Route wiring with feature flag
- Thêm cờ môi trường `USE_RAG_V2=1`.
- Nối `routes/qa.py`:
  - `POST /api/qa/ask`
  - `POST /api/qa/ask-stream`
  sang `rag_v2` khi bật cờ.
- Giữ nguyên TTS path cũ.
- Giữ nguyên dashboard rebuild legacy.
- Mở rộng `GET /api/dashboard/qa/rag-status` để trả thêm:
  - `rag_v2`
  - `active_engine`
- Đây là bước đầu tiên cho phép test voice QA thật trên web bằng backend mới.

### 2026-05-06 - Post Step 6 - Answer quality hardening
- Sửa `rag_v2` theo hướng ưu tiên các lỗi tác động trực tiếp đến voice QA:
  - giảm fallback oan khi retrieval đã đúng domain
  - thêm `faq_match_bonus` để FAQ gần exact-match nổi lên đúng hơn
  - tách retrieval thành `strong / moderate / weak`
  - với mức `moderate`, ưu tiên trả `extractive` thay vì trả trắng
  - thêm nhánh `qa_extractive` cho các chunk có cấu trúc `Câu hỏi / Trả lời`
- Kết quả đã xác nhận bằng preview:
  - `Bamboo dùng để làm gì` -> hit đúng `bamboo_faq.txt`
  - `Smart Box dùng để làm gì` -> trả đúng rất nhanh theo `qa_extractive`
  - `Inspection Machine có các nút nào` -> không còn fallback trắng

### 2026-05-06 - Manual chunking and formatting refinement
- Sửa chunker `manual` để gom các block cùng mục thành một chunk đầy đủ hơn.
- Rebuild lại `rag_v2` index:
  - `chunk_count: 455`
- Sửa formatting extractive cho câu hỏi manual dạng liệt kê:
  - ví dụ `Inspection Machine có các nút nào`
  - câu trả lời giờ liệt kê rõ hơn thay vì chỉ dừng ở `Emergency STOP`

### 2026-05-06 - Session context wiring for rag_v2
- Nối `session_context` từ `routes/qa.py` vào `services/rag_v2/qa.py`.
- Thêm logic follow-up cơ bản:
  - nếu câu hỏi mới quá ngắn hoặc có dấu hiệu nối tiếp như `còn`, `vậy`, `máy này`, `hệ thống này`
  - retriever sẽ mở rộng truy vấn bằng câu hỏi/lượt trước
- Trạng thái:
  - đã nối code xong
  - cần test trên UI thật để xác nhận hiệu quả hội thoại nhiều lượt

## Hạng mục đã xử lý xong
- `rag_v2` đã là engine runtime mặc định khi khởi động qua `start_app.sh`
- fallback oan do confidence gate đã giảm rõ
- FAQ exact/near-exact match đã ổn hơn
- product Q&A dạng `Câu hỏi / Trả lời` đã trả lời nhanh hơn đáng kể
- manual retrieval và manual formatting đã cải thiện

## Hạng mục còn mở
- `BGE-M3` chưa được cài local, nên embedding hiện vẫn là `nomic-embed-text:latest`
- chưa có reranker model chuyên dụng
- follow-up multi-turn mới ở mức cơ bản, cần test UI thật để chốt có đủ hay chưa
- một số manual answer vẫn còn thiên về extractive dài, chưa phải summary đẹp hoàn toàn

### 2026-05-06 - BGE-M3 install in progress
- Đã bắt đầu pull `bge-m3` vào Ollama local.
- Đã đổi `start_app.sh` để mặc định:
  - `RAG_V2_EMBED_MODEL=bge-m3`
- Sau khi pull xong cần:
  - rebuild lại `rag_v2` index
  - xác nhận `embed_model_reason=configured`

## Các bước test voice QA nên làm

### Chưa cần test nhiều ở Step 1
- Step này chưa thay hành vi backend production.
- Chỉ cần xác nhận dự án vẫn boot và không ảnh hưởng đường cũ.

### Các step sẽ cho cải thiện rõ rệt

#### Step 2 - Taxonomy + chunking mới
- Cải thiện kỳ vọng: `rõ rệt`
- Lý do:
  - FAQ không còn bị trộn với manual và profile.
  - Các câu hỏi ngắn kiểu voice sẽ bám đúng block dữ liệu hơn.
- Mức độ nên retest: `cao`
- Nên test lại voice QA:
  - câu chào hỏi
  - câu hỏi profile công ty
  - câu hỏi giải pháp sản phẩm
  - câu hỏi thao tác manual

#### Step 3 - Index mới + embedding mới
- Cải thiện kỳ vọng: `rõ rệt`
- Lý do:
  - thay đổi không gian vector và chunk quality cùng lúc.
- Mức độ nên retest: `cao`
- Nên test lại voice QA:
  - câu hỏi ngắn dễ nhiễu
  - câu hỏi đồng âm/chung từ khóa
  - câu hỏi về Smart Box / EcoSave / Camera AI

#### Step 4 - Hybrid retrieval + metadata filter
- Cải thiện kỳ vọng: `rất rõ rệt`
- Lý do:
  - đây là bước quan trọng nhất để giảm retrieve sai nguồn.
- Mức độ nên retest: `rất cao`
- Nên test lại voice QA:
  - câu hỏi chứa từ khóa rất cụ thể
  - câu hỏi có tên sản phẩm
  - câu hỏi có cùng từ chung nhưng khác domain

#### Step 5 - Reranker + Qwen 8B generation
- Cải thiện kỳ vọng: `rõ rệt về chất lượng câu trả lời`
- Lý do:
  - retrieval tốt hơn và câu trả lời mạch lạc hơn.
- Mức độ nên retest: `rất cao`
- Nên test lại voice QA:
  - câu hỏi dài hơn
  - câu hỏi mô tả “dùng để làm gì”
  - câu hỏi “gồm những gì”

## Ghi chú reset
- Reset ở đây là reset `kiến trúc`, `index`, và `schema ingest`.
- Không xóa sạch `Rag_data`.
- Không mở rộng thêm logic mới vào `services/qa_service.py` trừ bugfix bắt buộc.

## Cập nhật 2026-05-06 - BGE-M3
- Đã cài `bge-m3:latest` vào Ollama local.
- Đã rebuild lại `rag_v2` index bằng `bge-m3:latest`.
- Kết quả build:
  - `chunk_count`: `455`
  - `embed_model`: `bge-m3:latest`
  - `generate_model`: `qwen3:8b`
- Test nhanh sau rebuild:
  - `Bamboo dùng để làm gì` -> đúng, `faq_extractive`
  - `Smart Box dùng để làm gì` -> đúng, `qa_extractive`
  - `SSG có bao nhiêu nhân sự` -> đúng, `faq_extractive`
  - `Inspection Machine có các nút nào` -> đúng nguồn, nhưng vẫn chậm hơn rõ so với nhóm FAQ/product
- Nhận định:
  - `BGE-M3` đã vào stack chạy thật.
  - Retrieval sạch hơn ở các câu FAQ và product.
  - Nhóm manual vẫn cần tối ưu tiếp ở `retrieval + answer formatting`, không phải chỉ đổi embedding là đủ.

## Cập nhật 2026-05-06 - Intent alignment cho company/profile
- Vấn đề phát hiện:
  - Các câu như `giải pháp của Sao Mai`, `dịch vụ của công ty`, `giải pháp AI của SSG` dễ bị lệch vì từ `giải pháp` xuất hiện ngay trong tên công ty `Tập đoàn Giải pháp Sao Mai`.
  - Hệ thống cũ kéo nhầm FAQ về `tên công ty/viết tắt` hoặc trả về một câu quá tổng quát thay vì đúng intent.
- Sửa toàn diện đã làm:
  - thêm `intent/topic bonus` trong retriever cho các nhóm:
    - `solution/service/product`
    - `identity/name/abbreviation`
    - `field/domain`
  - thêm `mismatch penalty` để phạt các chunk `tên công ty/viết tắt` khi câu hỏi thực ra đang hỏi `giải pháp/dịch vụ`
  - thêm `alias-aware matching` để hiểu `SSG ~ SaoMai`
  - thêm `specificity match` trong answer extraction để câu cụ thể như `giải pháp AI` ưu tiên FAQ cụ thể hơn câu tổng quát
  - bổ sung stopword hội thoại như `bạn/tôi/biết/xin/hãy...` để không làm lệch scoring
- Nhóm câu retest sau sửa:
  - `Bạn cho tôi biết giải pháp của Sao Mai` -> đúng
  - `SaoMai có những sản phẩm giải pháp gì` -> đúng
  - `SaoMai làm về lĩnh vực gì` -> đúng
  - `Tên đầy đủ của SaoMai là gì` -> đúng
  - `Công ty cung cấp những dịch vụ nào` -> đúng
  - `SaoMai có giải pháp AI không` -> đúng
- Ghi chú:
  - Đây là cải thiện ở tầng `retrieval + answer selection`, có tác dụng tổng thể hơn so với vá từng câu đơn lẻ.
  - Nhánh còn nên ưu tiên tiếp theo vẫn là `manual/follow-up multi-turn`.

## Cập nhật 2026-05-06 - Gỡ runtime ver1
- Đã bỏ hoàn toàn đường chạy `legacy` khỏi app runtime:
  - `routes/qa.py` chỉ còn dispatch vào `rag_v2`
  - `start_app.sh` chỉ còn prebuild `rag_v2`
  - TTS đã tách riêng sang `services/qa_tts_service.py`
- Đã xóa file/code runtime ver1:
  - `services/qa_service.py`
  - `scripts/rebuild_rag_index.py`
  - `scripts/run_qa_retrieval_eval.py`
- Phần còn sót lại chỉ là tham chiếu lịch sử trong một số file docs/script ghi chú, không còn được import hay dùng để chạy app.

## Cập nhật 2026-05-06 - Intent-driven QA
- Đã thêm `intent classifier` riêng tại `services/rag_v2/intent.py`.
- Pipeline mới trong `rag_v2`:
  - classify intent trước retrieval
  - chọn `answer_policy`
  - chỉ retrieve trên nhóm tài liệu phù hợp
  - áp dụng `clarify` hoặc `answerability gate` trước khi trả lời
- Các nhóm intent chính:
  - `capability/meta`
  - `company/profile`
  - `product/solution`
  - `manual/how-to`
  - `small-talk`
  - `clarify`
  - `unanswerable_ranking`
- Kết quả test nhanh:
  - `bạn có thể cung cấp những thông tin gì` -> `capability_meta`
  - `Hãy hướng dẫn cho tôi sử dụng hệ thống` -> `clarify`
  - `cho tôi thông tin về dự án thành công nhất của bạn` -> `answerability_gate`
  - `Xin chào` -> `small_talk` đúng nguồn
  - `Cho tôi biết về SaoMai Solution Group` -> `company/profile`
  - `Smart Box dùng để làm gì trong nhà máy` -> `product/solution`
  - `Inspection Machine có các nút nào` -> `manual/how-to`

## Cập nhật 2026-05-06 - Conversation close + leadership fact lookup
- Đã thêm `conversation_close` path:
  - các câu như `Thôi được rồi`, `Được rồi`, `Ok rồi` không còn chạm vào retrieval
  - hệ thống trả một câu đóng hội thoại ngắn
- Đã thêm `leadership_role_lookup`:
  - ví dụ `tổng giám đốc của công ty là ai` -> trả đúng 1 fact ngắn
- Đã thêm `leadership_person_lookup`:
  - ví dụ `Nguyễn Văn Toàn là ai` -> trả đúng vai trò của người đó
- Cách làm:
  - classify trước
  - retrieve trong nhóm `company/profile`
  - parse leadership facts thành cặp `vai trò -> tên` và `tên -> vai trò`
  - không dump lại cả danh sách ban lãnh đạo
