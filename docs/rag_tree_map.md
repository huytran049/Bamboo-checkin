 # Sơ Đồ Cây RAG Của Dự Án

Tài liệu này dùng làm `bản đồ đánh số cố định` cho toàn bộ phần RAG/Q&A.

Từ nay khi sửa RAG, nên ghi theo dạng:

- `Sửa 2.4`: siết `out-of-domain`
- `Sửa 3.4.1`: ưu tiên `explicit subject` hơn `session subject`
- `Bổ sung 4.3.2`: thêm `focus rerank`

Không nên chỉ ghi kiểu:

- `sửa qa_service.py`
- `sửa retrieval`

vì cách đó không cho biết đang sửa đúng đoạn nào của pipeline.

## 1. Corpus Và Nguồn Tri Thức

### 1.1. Nguồn dữ liệu gốc
- Thư mục nguồn: [Rag_data](/Users/ssg/Documents/bamboo_nissin/Rag_data)
- Vai trò:
  - chứa dữ liệu công ty
  - chứa dữ liệu sản phẩm
  - chứa FAQ/giao tiếp

### 1.2. Catalog nguồn
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `SOURCE_CATALOG`
  - `FAQ_SOURCE_STEMS`
  - `PRODUCT_RAG_SOURCE_STEMS`
- Vai trò:
  - gán `topic`
  - gán `product`
  - gán `source_kind`
  - gán `priority`
- Ví dụ:
  - `rag_saomai1 -> topic=company_profile, product=saomai`
  - `giao_tiep_co_ban -> source_kind=faq`

### 1.3. Chuẩn hóa nội dung khi ingest
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `1.3.1` `_classify_block_section(...)`
  - `1.3.2` `_chunk_document(...)`
  - `1.3.3` `SECTION_KIND_LABELS`
- Vai trò:
  - tách block theo logic
  - gắn `section_kind`
  - chia chunk
  - chuẩn hóa `search_text`
- `1.3.1` Vai trò:
  - phân loại block thành `facts`, `overview`, `use_cases`, `controls`, `faq`, `general`
- `1.3.1` Ví dụ:
  - đoạn “Giới thiệu chung” của `inspection_machine` -> `overview`
  - đoạn danh sách nút `Start/Stop/Reset` -> `controls`
- `1.3.2` Vai trò:
  - cắt tài liệu thành chunk có metadata để retrieval dùng lại
- `1.3.2` Ví dụ:
  - một chunk sau ingest sẽ mang `source_name`, `section_kind`, `topic`, `product`
- `1.3.3` Vai trò:
  - ánh xạ nhãn section nội bộ thành tên nhất quán dùng trong metadata
- `1.3.3` Ví dụ:
  - `overview -> overview`, `controls -> controls`

### 1.4. Build lại index
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `1.4.1` `rebuild_rag_index(...)`
- Script vận hành:
  - [rebuild_rag_index.py](/Users/ssg/Documents/bamboo_nissin/scripts/rebuild_rag_index.py)
- `1.4.1` Vai trò:
  - quét `Rag_data`, chunk, embed, lưu lại toàn bộ index mới
- `1.4.1` Ví dụ:
  - sau khi sửa `camera_AI.txt`, chạy rebuild để câu hỏi mới thấy được nội dung mới

## 2. Hiểu Câu Hỏi Và Định Tuyến

### 2.1. Normalize và token nền
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `2.1.1` `QUESTION_STOPWORDS`
  - `2.1.2` `_question_focus_terms(...)`
  - `2.1.3` `_question_focus_phrases(...)`
- `2.1.1` Vai trò:
  - loại bỏ từ rỗng để hệ thống tập trung vào phần mang nghĩa
- `2.1.1` Ví dụ:
  - bỏ `là`, `ở`, `của`, `về`
- `2.1.2` Vai trò:
  - trích các token trọng tâm từ câu hỏi
- `2.1.2` Ví dụ:
  - `Camera AI dùng để làm gì` -> `camera`, `ai`, `dung`
- `2.1.3` Vai trò:
  - trích cụm 2-3 từ để giữ đúng ý hơn token đơn
- `2.1.3` Ví dụ:
  - `tiet kiem nang luong`, `camera ai`

### 2.2. Bắt chủ thể từ câu hỏi
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `2.2.1` `PRIORITY_SOURCE_FILTER_PATTERNS`
  - `2.2.2` `SOURCE_FILTER_PATTERNS`
  - `2.2.3` `_detect_source_filters(...)`
- Vai trò:
  - map câu hỏi sang `source_filters`
  - nhận diện subject như:
    - `EcoSave`
    - `Camera AI`
    - `Inspection Machine`
    - `Sao Mai`
- `2.2.1` Vai trò:
  - ưu tiên các pattern mạnh, đặc hiệu cao
- `2.2.1` Ví dụ:
  - `camera ai`, `machine vision` -> `camera_ai`
- `2.2.2` Vai trò:
  - bắt các pattern rộng hơn nhưng ít đặc hiệu hơn
- `2.2.2` Ví dụ:
  - `sao mai`, `ssg`, `công ty` -> `rag_saomai1`, `rag_saomai2`
- `2.2.3` Vai trò:+  
  - gom pattern thành `source_filters` cuối cùng để retrieval dùng
- `2.2.3` Ví dụ:
  - `Tôi muốn hỏi vì sao mai` -> `{'rag_saomai1','rag_saomai2'}`

### 2.3. Route câu hỏi
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `2.3.1` `PROJECT_RULES`
  - `2.3.2` `_classify_question_route(...)`
- Route chính:
  - `rule`
  - `faq`
  - `rag`
  - `dynamic_reserved`
- `2.3.1` Vai trò:
  - trả lời cứng cho các câu về chức năng kiosk đã chốt
- `2.3.1` Ví dụ:
  - `kiosk hiện hỗ trợ gì`
- `2.3.2` Vai trò:
  - quyết định câu hỏi đi nhánh nào trước khi retrieval
- `2.3.2` Ví dụ:
  - `Xin chào` -> `faq`
  - `Lịch hẹn của tôi` -> `dynamic_reserved`
  - `Camera AI là gì` -> `rag`

### 2.4. Chặn ngoài phạm vi
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `2.4.1` `OUT_OF_DOMAIN_PATTERNS`
  - `2.4.2` `_is_out_of_domain_question(...)`
- Vai trò:
  - chặn thời tiết
  - chặn giá vàng
  - chặn câu ngoài domain rõ ràng
- `2.4.1` Vai trò:
  - chứa danh sách pattern ngoài domain
- `2.4.1` Ví dụ:
  - `thời tiết`, `giá vàng`, `thủ đô`
- `2.4.2` Vai trò:
  - kiểm tra câu hiện tại có thuộc domain dự án hay không
- `2.4.2` Ví dụ:
  - `giá vàng hôm nay` -> `True`

### 2.5. Domain anchor
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `2.5.1` `SOURCE_ALIASES`
  - `2.5.2` `_best_domain_anchor(...)`
  - `2.5.3` `_has_domain_anchor(...)`
- Vai trò:
  - gom keyword rời rạc thành anchor theo tri thức dự án
  - quyết định câu có đáng đi tiếp vào RAG hay phải fallback
- `2.5.1` Vai trò:
  - cung cấp từ khóa đồng nghĩa cho từng nguồn tri thức
- `2.5.1` Ví dụ:
  - `inspection machine` có alias `máy inspection`, `kiểm tra kích thước`
- `2.5.2` Vai trò:
  - tìm anchor phù hợp nhất giữa câu hỏi và kho alias
- `2.5.2` Ví dụ:
  - `hệ thống tiết kiệm năng lượng ecosip` -> gần `ecosave`
- `2.5.3` Vai trò:
  - chốt câu này có đủ anchor để vào RAG hay phải dừng
- `2.5.3` Ví dụ:
  - `cửa hàng Vietnamobile` -> không có anchor nội bộ -> fallback

## 3. Follow-up Memory Và Query Rewriting

### 3.1. Session memory
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `3.1.1` `SESSION_SOURCE_SUBJECTS`
  - `3.1.2` `_extract_subject_from_session_context(...)`
  - `3.1.3` `_extract_last_turn(...)`
- `3.1.1` Vai trò:
  - map source sang subject đọc được
- `3.1.1` Ví dụ:
  - `camera_ai -> Camera AI`
- `3.1.2` Vai trò:
  - lấy subject cũ của phiên hỏi đáp để hỗ trợ follow-up
- `3.1.2` Ví dụ:
  - sau khi hỏi `EcoSave`, subject của session là `EcoSave`
- `3.1.3` Vai trò:
  - lấy lượt hỏi-đáp mới nhất trong session
- `3.1.3` Ví dụ:
  - dùng để biết câu trước đang hỏi về `Inspection Machine`

### 3.2. Nhận diện follow-up mơ hồ
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `3.2.1` `AMBIGUOUS_FOLLOWUP_MARKERS`
  - `3.2.2` `FOLLOWUP_PRONOUN_MARKERS`
  - `3.2.3` `AMBIGUOUS_FOLLOWUP_NOUNS`
  - `3.2.4` `_is_ambiguous_followup_question(...)`
- `3.2.1` Vai trò:
  - bắt các marker kiểu “chi tiết hơn”, “cụ thể hơn”
- `3.2.2` Vai trò:
  - bắt đại từ mơ hồ như `nó`, `cái đó`
- `3.2.3` Vai trò:
  - bắt danh từ quá chung như `thông tin`, `quy mô`
- `3.2.4` Vai trò:
  - kết luận câu hiện tại có phải follow-up mơ hồ hay không
- `3.2.4` Ví dụ:
  - `chi tiết hơn về quy mô` -> `True`

### 3.3. Suy ra chủ thể hiện tại
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `3.3.1` `_extract_explicit_subject_from_question(...)`
  - `3.3.2` `_session_subject_alignment_score(...)`
  - `3.3.3` `_is_generic_subject_request(...)`
- Vai trò:
  - xác định subject đang nói ở câu hiện tại
  - quyết định có được reuse memory cũ hay không
- `3.3.1` Vai trò:
  - lấy subject rõ ràng ngay trong câu hỏi hiện tại
- `3.3.1` Ví dụ:
  - `thông tin về inspection` -> `Inspection Machine`
- `3.3.2` Vai trò:
  - đo độ khớp giữa câu hiện tại và subject cũ
- `3.3.2` Ví dụ:
  - câu mới chứa `inspection` nhưng session cũ là `Camera AI` -> score thấp
- `3.3.3` Vai trò:
  - nhận diện câu chỉ là “xin thông tin tổng quan” về một subject rõ
- `3.3.3` Ví dụ:
  - `Tôi muốn hỏi vì sao mai` -> generic request về `Sao Mai`

### 3.4. Rewrite câu hỏi
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `3.4.1` `_infer_question_intent_for_rewrite(...)`
  - `3.4.2` `_infer_session_intent(...)`
  - `3.4.3` `_rewrite_question_with_session_context(...)`
- Vai trò:
  - biến câu mơ hồ thành câu rõ chủ thể và rõ intent
- `3.4.1` Vai trò:
  - đoán intent của câu hiện tại: factual, overview, controls, use_cases...
- `3.4.1` Ví dụ:
  - `nó hoạt động ra sao` -> `how_it_works`
- `3.4.2` Vai trò:
  - suy ra intent từ lượt trước nếu câu hiện tại không đủ rõ
- `3.4.2` Ví dụ:
  - lượt trước hỏi `ứng dụng`, lượt sau hỏi `cụ thể hơn` -> giữ intent `use_cases`
- `3.4.3` Vai trò:
  - rewrite câu cuối cùng trước khi vào retrieval
- `3.4.3` Ví dụ:
  - `chi tiết hơn` sau câu về `EcoSave` -> `Lợi ích nổi bật của EcoSave là gì?`

### 3.5. Clarification
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `3.5.1` `GENERIC_SCOPE_REQUEST_PATTERNS`
  - `3.5.2` `_is_generic_scope_request(...)`
  - `3.5.3` `_should_scope_clarify(...)`
  - `3.5.4` `_build_followup_clarification(...)`
- Vai trò:
  - chỉ hỏi lại khi câu thật sự thiếu chủ thể
  - không dùng clarification thay cho fallback
- `3.5.1` Vai trò:
  - liệt kê các pattern mở đầu quá chung
- `3.5.1` Ví dụ:
  - `tôi muốn hỏi về`, `cho tôi thông tin`
- `3.5.2` Vai trò:
  - kiểm tra câu có thật sự quá chung không
- `3.5.2` Ví dụ:
  - `Tôi muốn hỏi về` -> `True`
  - `Tôi muốn hỏi về Sapa` -> không còn coi là generic
- `3.5.3` Vai trò:
  - quyết định khi nào nên hỏi lại thay vì fallback
- `3.5.3` Ví dụ:
  - không có subject, không có anchor, nhưng câu chỉ là khung hỏi -> clarification
- `3.5.4` Vai trò:
  - sinh câu hỏi làm rõ cho người dùng
- `3.5.4` Ví dụ:
  - `Quý khách muốn hỏi cụ thể về Sao Mai, Bamboo...`

## 4. Retrieval

### 4.1. Truy xuất vector/hybrid
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `4.1.1` `_retrieve_rag(...)`
  - `4.1.2` `_keyword_overlap_score(...)`
  - `4.1.3` `_source_priority_bonus(...)`
  - `4.1.4` `_section_priority_bonus(...)`
- Vai trò:
  - semantic score
  - keyword score
  - priority bonus
  - section bonus
- `4.1.1` Vai trò:
  - lấy top context ban đầu từ index
- `4.1.1` Ví dụ:
  - câu `Camera AI dùng để làm gì` trả về top chunk từ `camera_AI.txt`
- `4.1.2` Vai trò:
  - đo độ trùng khớp từ khóa trực tiếp giữa câu hỏi và chunk
- `4.1.2` Ví dụ:
  - câu có `inspection` sẽ tăng điểm cho chunk có `inspection`
- `4.1.3` Vai trò:
  - cộng điểm ưu tiên theo tầm quan trọng của nguồn
- `4.1.3` Ví dụ:
  - `bamboo_faq` có priority cao hơn `bamboo` trong nhánh FAQ
- `4.1.4` Vai trò:
  - cộng/trừ điểm theo loại section
- `4.1.4` Ví dụ:
  - câu overview ưu tiên chunk `overview`, phạt chunk `controls`

### 4.2. Rerank theo trọng tâm câu hỏi
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `4.2.1` `_focus_alignment_score(...)`
  - `4.2.2` `_rerank_retrieved_contexts(...)`
- Vai trò:
  - không chỉ đúng source
  - mà còn đúng trọng tâm
- `4.2.1` Vai trò:
  - chấm thêm điểm theo focus terms/phrases
- `4.2.1` Ví dụ:
  - `quy mô` sẽ ưu tiên chunk có số liệu nhân sự hơn chunk giới thiệu chung
- `4.2.2` Vai trò:
  - sắp xếp lại top contexts sau retrieval ban đầu
- `4.2.2` Ví dụ:
  - cùng là `inspection_machine`, chunk “Giới thiệu chung” đứng trên chunk “Start/Stop”

### 4.3. Confidence gate
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `4.3.1` `_has_retrieval_confidence(...)`
- Vai trò:
  - retrieval không đủ tin cậy thì không được generate bừa
- `4.3.1` Ví dụ:
  - source top-k nhiễu hoặc focus score thấp -> fallback/clarification

## 5. Context Augmentation

### 5.1. Chọn context cuối cùng
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `5.1.1` `_select_augmented_contexts(...)`
- Vai trò:
  - chọn chunk nào vào prompt
  - bỏ trùng
  - giữ các chunk liền mạch
- `5.1.1` Ví dụ:
  - giữ 2 chunk cùng `camera_AI.txt` thay vì lấy 3 nguồn rời rạc

### 5.2. Build prompt
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `5.2.1` `_build_augmented_prompt(...)`
- Vai trò:
  - ráp question + context + style trả lời
- `5.2.1` Ví dụ:
  - factual question -> prompt ngắn, yêu cầu trả lời đúng thực thể
  - explainer question -> prompt thiên về tóm tắt ý chính

## 6. Answering Layer

### 6.1. Rule answer
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `6.1.1` `_match_project_rule(...)`
- `6.1.1` Vai trò:
  - trả lời cứng cho câu nghiệp vụ nội bộ kiosk
- `6.1.1` Ví dụ:
  - `kiosk có những chức năng gì`

### 6.2. FAQ exact
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `6.2.1` `_extract_exact_faq_answer(...)`
- Áp dụng chính cho:
  - [giao_tiep_co_ban.txt](/Users/ssg/Documents/bamboo_nissin/Rag_data/giao_tiep_co_ban.txt)
- `6.2.1` Vai trò:
  - match câu hỏi chuẩn hóa và trả lại câu trả lời đã duyệt
- `6.2.1` Ví dụ:
  - `alo` -> câu chào từ `giao_tiep_co_ban.txt`

### 6.3. Company fact safe
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `6.3.1` `_extract_saomai_fact_answer(...)`
- Áp dụng chính cho:
  - [RAG_saomai1.txt](/Users/ssg/Documents/bamboo_nissin/Rag_data/RAG_saomai1.txt)
- `6.3.1` Vai trò:
  - lấy fact công ty theo regex/template, tránh generate tự do
- `6.3.1` Ví dụ:
  - `chủ tịch công ty là ai`

### 6.4. Extractive answer
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `6.4.1` `_extract_answer_from_contexts(...)`
- Vai trò:
  - trả lời trực tiếp từ context
  - làm fallback khi generate lỗi

### 6.5. Generate bằng Ollama
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `6.5.1` `_call_ollama_generate(...)`
  - `6.5.2` `_iter_ollama_generate_chunks(...)`
- `6.5.1` Vai trò:
  - generate non-stream cho API trả một cục
- `6.5.1` Ví dụ:
  - dashboard test QA
- `6.5.2` Vai trò:
  - generate stream theo chunk cho UI live
- `6.5.2` Ví dụ:
  - `/qa-voice-demo` hiển thị câu trả lời dần dần

### 6.6. Guardrails sau generate
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `6.6.1` `_looks_like_prompt_leakage(...)`
  - `6.6.2` `_is_fallback_like_answer(...)`
- Vai trò:
  - chặn answer rò prompt
  - chặn answer fallback giả
- `6.6.1` Ví dụ:
  - answer chứa `Literal translation` -> bị chặn
- `6.6.2` Ví dụ:
  - answer kiểu `Về đội tester, tôi chưa có đủ thông tin...` -> coi là fallback thật

## 7. Delivery, Session, Lưu Vết

### 7.1. API ask / ask-stream
- File: [qa.py](/Users/ssg/Documents/bamboo_nissin/routes/qa.py)
- Node code:
  - `7.1.1` `POST /api/qa/ask`
  - `7.1.2` `POST /api/qa/ask-stream`
- `7.1.1` Vai trò:
  - API trả lời non-stream
- `7.1.2` Vai trò:
  - API trả lời stream cho UI realtime

### 7.2. Entry point xử lý
- File: [qa_service.py](/Users/ssg/Documents/bamboo_nissin/services/qa_service.py)
- Node code:
  - `7.2.1` `answer_static_question(...)`
  - `7.2.2` `stream_answer_static_question(...)`
- `7.2.1` Vai trò:
  - orchestrate toàn bộ pipeline cho câu trả lời thường
- `7.2.2` Vai trò:
  - orchestrate pipeline có stream delta

### 7.3. Session context từ DB
- File: [qa_history_repo.py](/Users/ssg/Documents/bamboo_nissin/database/repositories/qa_history_repo.py)
- Node:
  - `7.3.1` `get_latest_qa_session_context(...)`
- Façade:
  - [update_database.py](/Users/ssg/Documents/bamboo_nissin/database/update_database.py)
- `7.3.1` Vai trò:
  - lấy conversation gần nhất, matched_sources và contexts để feed vào memory
- `7.3.1` Ví dụ:
  - câu `chi tiết hơn` lấy được subject từ lượt trước

### 7.4. History QA
- File repo:
  - [qa_history_repo.py](/Users/ssg/Documents/bamboo_nissin/database/repositories/qa_history_repo.py)
- Vai trò:
  - lưu conversation theo session
  - cấp memory cho follow-up
- Ví dụ:
  - cùng một `session_key` sẽ gom nhiều lượt hỏi đáp vào cùng một phiên

## 8. Eval Và Theo Dõi

### 8.1. Bộ eval
- Dataset:
  - [qa_retrieval_eval_cases.json](/Users/ssg/Documents/bamboo_nissin/rag/eval/qa_retrieval_eval_cases.json)
- Script:
  - [run_qa_retrieval_eval.py](/Users/ssg/Documents/bamboo_nissin/scripts/run_qa_retrieval_eval.py)
- Vai trò:
  - đo route accuracy, source hit, fallback accuracy, mode accuracy
- Ví dụ:
  - chạy sau khi sửa `4.2` để xem retrieval có bám trọng tâm hơn không

### 8.2. Nhật ký thay đổi
- File log:
  - [rag.md](/Users/ssg/Documents/bamboo_nissin/rag/md/rag.md)
- Vai trò:
  - lưu lịch sử thay đổi RAG theo ngày giờ
- Ví dụ:
  - tra lại entry đã sửa `3.3.1` hay `6.6.2` vào ngày nào

## Quy Ước Ghi Sửa Đổi Từ Nay

Khi sửa RAG, ghi theo format:

- `Node`: số node bị sửa
- `Mục tiêu`: sửa gì
- `Nguyên nhân`: lỗi ở đâu
- `Cách sửa`: sửa logic nào
- `Tác động`: ảnh hưởng expected

Ví dụ:

- `Sửa 2.5.3`
  - Mục tiêu: siết `domain anchor`
  - Nguyên nhân: câu ngoài domain vẫn lọt vào RAG
  - Cách sửa: tăng ngưỡng anchor và bỏ reuse session subject yếu

- `Bổ sung 3.3.2`
  - Mục tiêu: chặn reuse subject cũ sai
  - Nguyên nhân: memory ô nhiễm kéo dài nhiều lượt
  - Cách sửa: thêm `session_subject_alignment_score`

- `Sửa 6.6.1`
  - Mục tiêu: chặn prompt leakage
  - Nguyên nhân: model trả cả note nội bộ
  - Cách sửa: thêm detector và thay bằng extractive/fallback

## Mapping Nhanh Các Sửa Gần Đây

- `fallback-like answer`:
  - `6.6.2`
- `explicit subject thắng session subject`:
  - `3.3.1`
- `query rewriting cho follow-up`:
  - `3.4`
- `section metadata cho chunk`:
  - `1.3`
- `focus rerank`:
  - `4.2`
- `domain anchor`:
  - `2.5`
- `clarification chỉ cho câu thật sự thiếu chủ thể`:
  - `3.5`
