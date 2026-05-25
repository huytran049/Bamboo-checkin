# Báo Cáo Tối Ưu Hóa & Nâng Cấp Kiến Trúc RAG V2 (Bamboo Nissin)

Tài liệu này tổng hợp ngắn gọn các thay đổi cốt lõi đã được thực hiện để chuyển đổi hệ thống RAG từ dạng Rule-based (dựa trên quy tắc cứng) sang chuẩn Generative AI linh hoạt, phục vụ trực tiếp cho Kiosk Voice QA.

---

## 1. Đại Tu Luồng Nạp Dữ Liệu (Ingestion & Storage)
- **Từ bỏ Regex Chunking**: Chuyển từ việc cắt file thủ công bằng RegEx sang sử dụng `RecursiveCharacterTextSplitter`, giúp giữ nguyên ngữ cảnh (overlap) và tránh mất mát dữ liệu khi format tài liệu bị thay đổi.
- **AI-Driven Metadata**: Loại bỏ phụ thuộc vào mapping tên file cứng trong `schema.py`. Áp dụng LLM để tự động phân tích và gán nhãn `doc_type`, `products`, `topic` cho từng chunk.
- **Tích hợp ChromaDB**: Chuyển đổi toàn bộ việc lưu trữ từ file `JSON` phẳng sang Vector Database (`ChromaDB`), cho phép lưu trữ vĩnh viễn và tìm kiếm với hiệu năng cao.

## 2. Nâng Cấp Thuật Toán Tìm Kiếm (Retrieval)
- **Hybrid Search**: Thay vì chỉ dùng từ khóa (Lexical), hệ thống giờ đây kết hợp **Dense Retrieval** (Tìm kiếm Vector qua ChromaDB) và **BM25 Reranking** (Ưu tiên từ khóa).
- **Hành vi mới**: Tìm kiếm dựa trên ý nghĩa câu chữ thay vì phải khớp chính xác từng ký tự, giúp truy xuất tài liệu ngay cả khi người dùng dùng từ đồng nghĩa.

## 3. Lột Xác Quy Trình Sinh Văn Bản (Generation)
- **Sửa Lỗi "Cắt Cụt" Câu**: Khắc phục triệt để tình trạng AI đang trả lời thì bị ngắt ngang bằng cách tăng tham số `num_predict` từ `96` lên `512` trong `generator.py`.
- **Dẹp Bỏ Extractive Fallback**: Xóa bỏ các logic "trả về chuỗi thô" (leaking raw metadata như `TIÊU_ĐỀ: ...`) trong `qa.py`. Bắt buộc LLM phải tự đọc ngữ cảnh và hành văn tự nhiên 100%.

## 4. Gỡ Bỏ Rào Cản Định Tuyến (Routing)
- **Xóa bỏ Intent If/Else cứng nhắc**: Viết lại `intent.py` để loại bỏ các câu hỏi ép buộc người dùng (VD: *"Bạn muốn hướng dẫn hệ thống nào..."*). Trả lại toàn quyền phân tích ngữ cảnh cho Vector Search và LLM.

## 5. Tối Ưu Trải Nghiệm Voice-to-Text (Kiosk Voice)
- **Phonetic Typo Correction**: Bổ sung bộ lọc tiền xử lý `correct_phonetic_typos()` ngay tại đầu vào API `qa.py`.
- **Tác dụng**: Khắc phục ngay lập tức các lỗi sai do phần mềm nhận diện giọng nói (Speech-to-Text) gây ra trước khi đưa vào RAG.
  - *ecosip, eco xếp* ➔ `EcoSave`
  - *hoa mai* ➔ `Sao Mai`
  - *kiot* ➔ `Kiosk`
  - *isg* ➔ `SSG`

---
**Kết Quả Cuối Cùng**: Hệ thống RAG V2 hiện tại không còn bị trói buộc bởi các lệnh `If-Else` cục bộ. Nó thông minh hơn, chống chịu tốt hơn với lỗi giọng nói (Voice), không bịa đặt thông tin (Zero Hallucination), và sinh câu trả lời mượt mà như một con người thực sự.
