# RAG Log

Tài liệu này chỉ dùng để ghi nhận các thay đổi liên quan đến RAG/Q&A knowledge retrieval.

Quy ước:
- Mỗi lần chỉnh sửa, bổ sung, fix lỗi, đổi model, đổi data source hoặc đổi logic retrieval/generation đều phải thêm một entry mới.
- Mỗi entry phải có `ngày giờ` cụ thể theo múi giờ dự án.
- Nội dung không liên quan đến RAG thì không ghi vào đây, mà ghi vào log ngày tương ứng trong `@check log md/`.

---

## Entry: 2026-04-13 14:41:14 +0700

### Node liên quan
- `1.2`
- `1.3`
- `1.4`
- `2.2`
- `2.3`
- `4.1`
- `5.1`
- `5.2`
- `6.4`
- `6.5`
- `8.1`

### Trạng thái
- Khởi tạo file log riêng cho RAG.
- Tổng hợp trạng thái hiện tại của bản `RAG chuẩn tối thiểu` đang áp dụng cho dự án Bamboo kiosk.

### Đã làm
- Chuyển Q&A kiến thức tĩnh từ dạng lexical/rule đơn giản sang pipeline RAG có ingest từ thư mục `Rag_data/`.
- Chuẩn hóa pipeline gồm các bước:
  - đọc dữ liệu nguồn từ `Rag_data/*.txt|*.md`
  - làm sạch text
  - chunking có overlap
  - embedding qua Ollama
  - lưu vector vào SQLite
  - retrieve theo cosine similarity
  - rerank hybrid bằng keyword overlap
  - augment prompt bằng chunk đã retrieve
  - gửi prompt sang Ollama generation
  - fallback về câu lễ tân khi không đủ ngữ cảnh
- Giữ lại `PROJECT_RULES` cho nhóm câu hỏi nghiệp vụ nội bộ của kiosk/dashboard để tránh để RAG xử lý sai workflow nội bộ.
- Thêm script rebuild index độc lập:
  - `python3 scripts/rebuild_rag_index.py`
- Thêm API quản trị RAG:
  - `GET /api/dashboard/qa/rag-status`
  - `POST /api/dashboard/qa/rag-rebuild`

### Đã sửa
- Sửa logic chọn embedding model để nhận đúng tag kiểu `:latest`.
- Cài thêm embedding model Ollama:
  - `nomic-embed-text:latest`
- Sửa lỗi runtime retrieval với `numpy array` khi tính cosine similarity.
- Bổ sung `index_name` vào vector store để hỗ trợ mở rộng nhiều index/corpus sau này.
- Bổ sung metadata/source label cho chunk để improve retrieval.
- Bổ sung source filter theo nhóm tài liệu:
  - `EcoSave`
  - `Camera AI`
  - `Smart Box`
  - `Inspection Machine`
  - `SSG`
- Siết guardrail:
  - câu ngoài phạm vi nhưng semantic score cao sẽ không được phép vượt qua nếu thiếu keyword/scope phù hợp
- Sửa post-process answer:
  - bỏ phần lặp lại nguyên câu hỏi ở đầu câu trả lời
  - nếu fallback thì xóa luôn `matched_sources` và `matched_contexts`

### Đang làm
- Theo dõi chất lượng retrieval thực tế trên bộ `Rag_data` hiện tại.
- Kiểm tra xem có cần tách nhỏ thêm một số tài liệu dài như:
  - `RAG_saomai1.txt`
  - `RAG_saomai2.txt`
  - `inspection_machine.txt`
- Đánh giá xem có cần giảm bớt việc trả raw `matched_contexts` ra public API hay chỉ giữ cho dashboard/debug nội bộ.

### Sẽ làm
- Thêm giao diện quản trị RAG trên dashboard nếu cần:
  - xem trạng thái index
  - rebuild index từ UI
  - xem danh sách source files
- Chuẩn hóa metadata theo tài liệu:
  - product/category/language/version/source_date
- Tách rõ hơn giữa:
  - Q&A kiến thức công ty/sản phẩm qua RAG
  - Q&A nghiệp vụ nội bộ qua rule/service động
- Nếu corpus tăng lớn hơn, cân nhắc:
  - vector store chuyên dụng
  - reranking tốt hơn
  - batch rebuild/incremental ingest

### Lưu ý
- Hiện tại nguồn ingest chính thức của RAG là thư mục `Rag_data/`, chưa có chức năng upload file từ UI.
- Đây là bản `RAG chuẩn tối thiểu`, ưu tiên dễ bảo trì và dễ mở rộng hơn là tối ưu hóa quá sớm.
- Model hiện tại:
  - embedding: `nomic-embed-text:latest`
  - generation: `llama3:latest`
- Dữ liệu hiện tại đã index thành công:
  - `ECOSAVE.txt`
  - `RAG_saomai1.txt`
  - `RAG_saomai2.txt`
  - `Smart_box.txt`
  - `camera_AI.txt`
  - `inspection_machine.txt`
- Sau khi thêm/sửa dữ liệu trong `Rag_data`, cần rebuild lại index trước khi test câu hỏi mới.
- Những thay đổi không liên quan đến RAG sẽ tiếp tục ghi ở `@check log md/13_4.md` hoặc log ngày tương ứng.

---

## Entry: 2026-04-13 14:44:03 +0700

### Node liên quan
- `1.4.1`
- `7.2`

### Trạng thái
- Chuẩn hóa lại quy trình khởi chạy để `start_app.sh` tự chuẩn bị phần RAG/Q&A thay vì phải chạy tay từng bước.

### Đã sửa
- File: `start_app.sh`
  - thêm env mặc định cho RAG:
    - `QA_EMBED_MODEL=nomic-embed-text:latest`
    - `QA_GENERATE_MODEL=llama3:latest`
    - `QA_PREBUILD_INDEX=1`
  - thêm bước kiểm tra model Ollama cần thiết trước khi mở app:
    - OCR model
    - QA embed model
    - QA generate model
  - sửa logic nhận diện model đã cài để chấp nhận cả tên có tag như `:latest`
  - thêm bước `ensure_rag_index_ready()`:
    - đọc trạng thái index hiện tại
    - nếu thiếu hoặc stale thì rebuild ngay trước khi app chạy
  - export đầy đủ biến môi trường RAG sang process Flask

### Đã kiểm tra
- `bash -n start_app.sh` OK
- Smoke startup bằng `start_app.sh`:
  - Ollama ready
  - model OCR ready
  - model QA embed ready
  - model QA generate ready
  - Redis ready
  - OCR worker start được
  - RAG index được xác nhận `is_ready=True`
  - Flask app chạy được trên cổng `5001`

### Kết luận vận hành
- Với trạng thái hiện tại, chỉ cần chạy:
  - `bash start_app.sh`
- Script sẽ tự lo các bước cần thiết cho phần RAG đang có.

### Lưu ý
- Lần chạy đầu tiên có thể lâu hơn nếu thiếu model Ollama và script phải `pull`.
- Nếu sau này sửa dữ liệu trong `Rag_data`, `start_app.sh` sẽ tự kiểm tra trạng thái index; khi phát hiện stale hoặc chưa có index thì sẽ rebuild trước khi app lên.
- Nếu muốn bỏ bước prebuild index lúc startup, có thể đặt:
  - `QA_PREBUILD_INDEX=0`

---

## Entry: 2026-04-13 15:09:40 +0700

### Node liên quan
- `7.2`

### Trạng thái
- Chuyển voice trả lời của QA từ browser TTS sang `edge_tts` runtime phía backend.

### Đã sửa
- File: `services/qa_service.py`
  - thêm `edge_tts` runtime cho câu trả lời QA
  - thêm chuẩn hóa text trước khi đọc:
    - đổi `;` và `:` thành điểm ngắt dễ nghe hơn
    - làm sạch khoảng trắng và dấu câu
  - tạo audio bằng `edge_tts` theo kiểu file tạm hệ thống:
    - generate mp3 tạm
    - đọc bytes vào memory
    - xóa file ngay sau khi lấy xong
  - không lưu voice vào DB
  - không lưu voice lâu dài vào folder dự án

- File: `routes/qa.py`
  - thêm endpoint `POST /api/qa/tts`
  - nhận text trả lời QA và trả về `audio/mpeg`

- File: `static/js/qa_voice_demo.js`
  - bỏ `speechSynthesis` của browser
  - đổi sang fetch audio từ backend
  - phát bằng `Audio` object
  - hỗ trợ dừng/clear audio cũ trước khi phát lại

### Đã kiểm tra
- `python3 -m py_compile services/qa_service.py routes/qa.py`
- `node --check static/js/qa_voice_demo.js`
- smoke test `POST /api/qa/tts`
  - status `200`
  - content type `audio/mpeg`
  - payload audio nhận được thành công

### Lưu ý
- Voice QA hiện là runtime, không tạo thêm dữ liệu lưu trữ lâu dài.
- Trên môi trường này, `edge_tts.stream()` không ổn định; `edge_tts.save()` chạy ổn nên đang dùng chiến lược file tạm hệ điều hành rồi xóa ngay.
- Nếu cần cải thiện độ tự nhiên hơn nữa, bước sau nên thêm:
  - tách câu tốt hơn
  - xử lý số/ký hiệu
  - cấu hình voice/rate riêng cho QA

---

## Entry: 2026-04-15 14:18:18 +0700

### Node liên quan
- `7.2`

### Trạng thái
- Thêm `voice command router` cho page `/qa-voice-demo` để tự động hóa các nút chính bằng giọng nói, nhưng vẫn giữ toàn bộ button tay làm fallback.

### Đã sửa
- File: `static/js/qa_voice_demo.js`
  - thêm bộ nhận lệnh giọng nói riêng cho page QA
  - thêm normalize transcript để match command ổn định hơn
  - thêm mapping lệnh:
    - `bắt đầu nói`
    - `nghe lại câu trả lời`
    - `làm mới`
    - `quay lại kiosk`
  - thêm logic ưu tiên:
    - nếu transcript khớp command thì chạy action UI tương ứng
    - nếu không khớp command thì coi như câu hỏi QA và gọi `/api/qa/ask`
  - thêm chế độ `question_only`:
    - khi người dùng nói `bắt đầu nói`, recognition sẽ tự khởi động lại để chờ riêng câu hỏi tiếp theo
  - tách `resetQaDemo()` để dùng chung cho button tay và voice command

- File: `templates/qa_voice_demo.html`
  - thêm hint các lệnh giọng nói đang hỗ trợ
  - thêm `id="qaBackLink"` để voice command có thể điều hướng về kiosk

- File: `static/css/qa_voice_demo.css`
  - thêm style cho khối hint lệnh giọng nói

### Mục tiêu
- Voice command chỉ hoạt động trong `/qa-voice-demo`
- Không can thiệp vào kiosk chính
- Giữ button tay để fallback nếu automation không hoạt động

### Đã kiểm tra
- `node --check static/js/qa_voice_demo.js` OK
- kiểm tra template/CSS:
  - `qaBackLink` có mặt trong HTML
  - `.qa-command-hint` có mặt trong CSS

### Cách test
- Mở `/qa-voice-demo`
- Bấm micro
- Thử từng lệnh:
  - `nghe lại câu trả lời`
  - `làm mới`
  - `quay lại kiosk`
  - `bắt đầu nói`
- Với `bắt đầu nói`:
  - sau khi nói lệnh này, hệ thống sẽ tự chuyển sang chờ câu hỏi tiếp theo

### Lưu ý
- Trên browser hiện tại, recognition vẫn cần một thao tác người dùng để bắt đầu phiên mic đầu tiên.
- Đây là bước 1: command router ở frontend.
- Chưa đụng đến router FAQ/RAG/dữ liệu động ở backend trong entry này.

---

## Entry: 2026-04-15 14:59:08 +0700

### Trạng thái
- Đổi QA voice runtime từ `Piper` sang `gTTS` và chuyển `/qa-voice-demo` sang chế độ mic luôn lắng nghe với wake word `bắt đầu`.

### Đã sửa
- File: `services/qa_service.py`
  - bỏ `Piper` khỏi runtime TTS của QA
  - dùng `gTTS` để tạo `mp3` trong memory
  - đổi cache key theo `gtts|lang|tld|text`
  - giữ nguyên lớp chuẩn hóa text trước TTS
  - `warmup_qa_tts()` đổi sang kiểu fail-soft: nếu warmup mạng lỗi thì chỉ log warning, không làm crash startup
  - `get_qa_tts_status()` giờ trả:
    - `provider = gtts`
    - `active_voice = lang=vi, tld=com`

- File: `routes/qa.py`
  - endpoint `/api/qa/tts` giờ trả `audio/mpeg`
  - đổi tên file download runtime sang `.mp3`

- File: `requirements.txt`
  - bỏ `piper-tts`
  - thêm `gTTS`

- File: `start_app.sh`
  - bỏ env `QA_TTS_PIPER_VOICE`
  - thêm:
    - `QA_TTS_GTTS_LANG`
    - `QA_TTS_GTTS_TLD`

- File: `templates/qa_voice_demo.html`
  - đổi hint trên page sang hướng dẫn wake word `bắt đầu`

- File: `static/js/qa_voice_demo.js`
  - bỏ cơ chế command router theo kiểu trước đó
  - thêm `wake word mode`
  - mic được tự khởi động ở chế độ chờ khi vào `/qa-voice-demo`
  - page luôn lắng nghe và chỉ khi transcript chứa `bắt đầu` thì mới chuyển sang phase nhận câu hỏi QA
  - nếu người dùng nói `bắt đầu` kèm câu hỏi trong cùng một câu, phần sau wake word sẽ được gửi thẳng vào QA
  - nếu chỉ nói `bắt đầu`, hệ thống sẽ tự chuyển sang mode chờ riêng câu hỏi tiếp theo
  - button tay vẫn được giữ nguyên để fallback
  - button `Bắt đầu nói` giờ là fallback để ép vào mode hỏi trực tiếp nếu automation không hoạt động

### Đã kiểm tra
- `python3 -m pip install gTTS` xác nhận package đã có sẵn
- `node --check static/js/qa_voice_demo.js` OK
- `python3 -m py_compile services/qa_service.py routes/qa.py` OK
- import/status test:
  - `provider = gtts`
  - `active_voice = lang=vi, tld=com`
- synthesize test:
  - `audio/mpeg`
  - payload audio tạo thành công

### Cách test
- Mở `/qa-voice-demo`
- Không cần bấm nút gì, chờ page tự vào trạng thái nghe
- Nói câu bất kỳ không có `bắt đầu`
  - hệ thống phải bỏ qua
- Nói `bắt đầu`
  - hệ thống phải chuyển sang chờ câu hỏi
- Nói `bắt đầu Smart Box dùng để làm gì`
  - hệ thống phải nhận và hỏi QA ngay
- Nếu automation không hoạt động:
  - dùng nút `Bắt đầu nói` để hỏi thủ công như fallback

### Lưu ý
- Chế độ always-listening vẫn phụ thuộc quyền micro của browser.
- Nếu browser chưa cấp quyền micro, page sẽ không thể tự vào chế độ nghe cho đến khi quyền được cấp.
- `gTTS` là TTS online, nên chất lượng giọng dễ nghe hơn `Piper`, nhưng độ trễ và độ ổn định sẽ phụ thuộc mạng.

---

## Entry: 2026-04-15 15:40:47 +0700

### Trạng thái
- Tăng tốc độ đọc QA voice lên `1.5x` và sửa lại wake-word loop của `/qa-voice-demo` để tránh tình trạng nút mic đổi text liên tục và chế độ `bắt đầu` không hoạt động ổn định.

### Đã sửa
- File: `services/qa_service.py`
  - thêm `QA_TTS_PLAYBACK_RATE`
  - `get_qa_tts_status()` giờ trả thêm `playback_rate`

- File: `start_app.sh`
  - export mặc định:
    - `QA_TTS_PLAYBACK_RATE=1.5`

- File: `static/js/qa_voice_demo.js`
  - thêm `playbackRate` phía client
  - khi phát audio QA:
    - `Audio.playbackRate = 1.5`
    - `defaultPlaybackRate = 1.5`
    - `preservesPitch = false`
  - sửa `extractQuestionAfterWakeWord()`:
    - ưu tiên tách câu hỏi từ transcript gốc bằng regex `bắt đầu`
    - chỉ fallback sang bản normalize khi cần
  - bỏ việc đổi text nút mic sang `Dừng ghi âm` trong các vòng auto-restart
  - giữ nút mic ổn định để tránh nhấp nháy `Bắt đầu nói / Dừng ghi âm`
  - khi bấm nút mic lúc đang nghe wake-word:
    - ép chuyển sang mode hỏi trực tiếp (`question_only`)
  - thêm fallback bootstrap:
    - nếu browser không tự bật mic ngay từ đầu, chỉ cần user click/chạm/phím bất kỳ trên page thì hệ thống sẽ tự thử khởi động lại wake-word mode

### Mục tiêu
- Voice QA đọc nhanh hơn mà không cần sửa nội dung answer
- Wake word `bắt đầu` hoạt động ổn định hơn
- Trải nghiệm UI bớt nhiễu vì nút mic không đổi text liên tục do auto-listening

### Đã kiểm tra
- `node --check static/js/qa_voice_demo.js` OK
- `python3 -m py_compile services/qa_service.py routes/qa.py` OK

### Cách test
- Restart app
- Mở `/qa-voice-demo`
- Cho phép micro nếu browser hỏi
- Quan sát:
  - nút mic không còn nhảy liên tục giữa `Bắt đầu nói` và `Dừng ghi âm`
- Nói:
  - `bắt đầu`
  - rồi nói tiếp câu hỏi
- Hoặc nói liền:
  - `bắt đầu Smart Box dùng để làm gì`
- Nghe câu trả lời:
  - tốc độ đọc phải nhanh hơn trước theo mức `1.5x`

### Lưu ý
- Tốc độ `1.5x` hiện là tốc độ playback phía client của audio `gTTS`, vì `gTTS` bản thân không có tham số speed runtime linh hoạt như một số engine khác.
- Nếu sau test vẫn còn browser nào không vào được wake-word mode ngay từ đầu, nguyên nhân thường là chính sách quyền micro của browser, không phải logic QA.

---

## Entry: 2026-04-15 16:57:03 +0700

### Trạng thái
- Đơn giản hóa lại toàn bộ logic `/qa-voice-demo` theo yêu cầu mới: chỉ còn 3 nút `Bắt đầu`, `Làm mới`, `Quay lại`; bỏ hoàn toàn `Nghe lại` và bỏ wake-word flow.

### Đã sửa
- File: `templates/qa_voice_demo.html`
  - bỏ nút `Nghe lại trả lời`
  - đổi nút chính thành `Bắt đầu`
  - thêm mô tả rõ logic:
    - `Bắt đầu` để bật nhận voice
    - `Kết thúc` để tạm dừng
    - `Làm mới` để xóa đoạn chat

- File: `static/js/qa_voice_demo.js`
  - viết lại logic frontend QA theo mode phiên nghe đơn giản
  - bỏ toàn bộ:
    - wake word `bắt đầu`
    - auto-listening khi vào page
    - router command cũ
    - nút `Nghe lại`
  - thêm state `listeningEnabled`
  - nút `Bắt đầu`:
    - bật nhận voice
    - đổi text nút thành `Kết thúc`
    - khi browser kết thúc một lượt nhận giọng, nếu phiên vẫn bật thì tự arm lại để nghe câu hỏi tiếp theo
  - nút `Kết thúc`:
    - chỉ tạm dừng nhận voice
    - không xóa history câu hỏi/câu trả lời
  - nút `Làm mới`:
    - dừng nhận voice
    - xóa toàn bộ history đang hiển thị
    - reset trạng thái UI
  - thêm `questionHistory` và `answerHistory`
    - hiển thị nối tiếp các lượt hỏi đáp
    - khi `Bắt đầu` lại sau khi `Kết thúc`, các lượt mới sẽ nối tiếp history cũ
  - giữ auto speak sau mỗi câu trả lời

- File: `services/qa_service.py`
  - đổi default `QA_TTS_PLAYBACK_RATE` từ `1.5` xuống `1.25`

- File: `start_app.sh`
  - đổi default `QA_TTS_PLAYBACK_RATE` từ `1.5` xuống `1.25`

### Đã kiểm tra
- `node --check static/js/qa_voice_demo.js` OK
- `python3 -m py_compile services/qa_service.py routes/qa.py` OK
- kiểm tra env override:
  - hiện không có `QA_TTS_PLAYBACK_RATE` trong `.env`
  - nên default mới `1.25` sẽ có hiệu lực sau restart app

### Cách test
- Restart app
- Mở `/qa-voice-demo`
- Kiểm tra chỉ còn 3 nút:
  - `Bắt đầu`
  - `Làm mới`
  - `Quay lại`
- Bấm `Bắt đầu`
  - nút phải đổi thành `Kết thúc`
  - status chuyển sang trạng thái nghe câu hỏi
- Hỏi 1 câu
  - câu hỏi và câu trả lời được append vào history
- Bấm `Kết thúc`
  - nhận voice dừng lại
  - history vẫn còn nguyên
- Bấm `Bắt đầu` lần nữa
  - hỏi tiếp câu mới
  - history phải nối tiếp, không bị xóa
- Bấm `Làm mới`
  - history bị xóa sạch
  - phiên voice dừng lại

### Lưu ý
- Bản này bỏ hẳn wake-word flow để tránh hành vi khó kiểm soát của browser.
- Logic mới đơn giản hơn, dễ kiểm thử hơn, và đúng sát yêu cầu vận hành hiện tại.

---

## Entry: 2026-04-15 16:58:54 +0700

### Trạng thái
- Chốt rõ semantics của nút `Làm mới` trên `/qa-voice-demo`: chỉ clear UI cho phiên hỏi đáp mới, không xóa lịch sử Q&A đã lưu trong database.

### Làm rõ logic hiện tại
- Route `POST /api/qa/ask` vẫn lưu từng lượt hỏi đáp vào DB qua `create_qa_history(...)`
- Nút `Làm mới` chỉ reset state frontend:
  - dừng voice recognition hiện tại
  - dừng phát audio
  - xóa `questionHistory` và `answerHistory` trên UI
  - không gọi bất kỳ API xóa history nào

### Ý nghĩa vận hành
- Dashboard Q&A vẫn giữ toàn bộ lịch sử đã hỏi trước đó
- `Làm mới` chỉ bắt đầu một phiên UI mới trên page `qa-voice-demo`
- `Kết thúc` chỉ tạm dừng nhận voice, không xóa history UI
- `Bắt đầu` lại sau đó sẽ nối tiếp history UI hiện có

### Lưu ý
- Nếu cần xóa thật lịch sử trong DB, chỉ dashboard mới có API/flow riêng cho việc đó.

---

## Entry: 2026-04-13 15:16:59 +0700

### Trạng thái
- Tối ưu trải nghiệm phát voice QA để không bị chờ thêm nhiều giây sau khi text answer đã hiện.

### Đã sửa
- File: `static/js/qa_voice_demo.js`
  - đổi autoplay voice sang cơ chế `fast-path`
  - khi text answer vừa hiện:
    - frontend bắt đầu preload `edge_tts` audio ở nền
    - nếu audio server sẵn rất nhanh thì phát ngay bản `edge_tts`
    - nếu audio server chưa kịp trong thời gian ngắn, frontend fallback đọc ngay bằng browser TTS để tránh khoảng chết
  - nút `Nghe lại trả lời` vẫn ưu tiên dùng audio backend `edge_tts`
  - thêm logic dừng/abort audio request cũ khi reset hoặc có câu hỏi mới

### Mục tiêu của thay đổi
- Ưu tiên `voice phát ngay sau khi text answer hiển thị`
- Không chờ backend TTS quá lâu trong autoplay
- Giữ `edge_tts` cho trường hợp nghe lại hoặc khi audio backend sẵn nhanh

### Đã kiểm tra
- `node --check static/js/qa_voice_demo.js`
- `python3 -m py_compile services/qa_service.py routes/qa.py`

### Lưu ý
- Đây là tối ưu UX trước mắt, chưa xử lý gốc độ trễ của bước generate text answer.
- Khi backend TTS đủ nhanh, autoplay vẫn dùng `edge_tts`.
- Khi backend TTS chậm, autoplay sẽ đọc bằng browser voice để không làm người dùng chờ thêm.

---

## Entry: 2026-04-13 15:33:16 +0700

### Trạng thái
- Bỏ hẳn browser TTS khỏi QA voice và tối ưu `edge_tts` theo hướng giảm thời gian tới âm thanh đầu tiên.

### Đã sửa
- File: `static/js/qa_voice_demo.js`
  - xóa fallback autoplay về browser TTS
  - chuyển autoplay và replay sang `edge_tts` backend thuần
  - đổi cách phát từ `1 audio cho cả đoạn` sang `chia theo từng câu`
  - prefetch audio cho từng câu song song ở nền
  - phát câu đầu tiên ngay khi sẵn, sau đó nối tiếp các câu còn lại
  - thêm dọn cache blob URL/audio promise khi reset hoặc có câu trả lời mới

- File: `services/qa_service.py`
  - thêm cache ngắn hạn cho `edge_tts` theo hash nội dung + voice + rate
  - thêm warmup `edge_tts`

- File: `start_app.sh`
  - gọi warmup `edge_tts` ngay lúc startup

### Đã kiểm tra
- `node --check static/js/qa_voice_demo.js`
- `python3 -m py_compile services/qa_service.py routes/qa.py`
- đo backend TTS:
  - lần đầu vẫn có độ trễ cold-start
  - cùng nội dung sau cache phản hồi gần như tức thì

### Lưu ý
- Việc chia theo từng câu nhằm giảm `time-to-first-audio`, không phải giảm tổng thời gian synth toàn bộ nội dung.
- Nếu câu trả lời dài, người dùng sẽ nghe được sớm hơn thay vì phải chờ xong cả đoạn mới phát.

---

## Entry: 2026-04-13 15:45:57 +0700

### Trạng thái
- Thay QA voice từ `edge_tts` sang `Piper` local để test tốc độ và chất lượng TTS local thực sự.

### Đã sửa
- Cài package Python:
  - `piper-tts`
- Thêm model Piper tiếng Việt vào repo:
  - `models/tts/piper/vi_VN-vais1000-medium/vi_VN-vais1000-medium.onnx`
  - `models/tts/piper/vi_VN-vais1000-medium/vi_VN-vais1000-medium.onnx.json`
- File: `services/qa_service.py`
  - thêm `QA_TTS_PROVIDER`
  - thêm loader cho `PiperVoice`
  - thêm synth runtime bằng Piper
  - output audio QA đổi sang `wav`
  - cache audio vẫn giữ để tăng tốc các câu lặp lại
- File: `routes/qa.py`
  - `POST /api/qa/tts` giờ trả `audio/wav` khi dùng Piper
- File: `start_app.sh`
  - đặt mặc định:
    - `QA_TTS_PROVIDER=piper`
    - `QA_TTS_PIPER_MODEL=<repo>/models/tts/piper/vi_VN-vais1000-medium/vi_VN-vais1000-medium.onnx`
  - warmup TTS lúc startup vẫn được giữ
- File: `requirements.txt`
  - thêm `piper-tts`

### Đã kiểm tra
- `python3 -m py_compile services/qa_service.py routes/qa.py`
- `node --check static/js/qa_voice_demo.js`
- smoke test `/api/qa/tts`:
  - lần đầu khoảng `656ms`
  - cùng nội dung sau cache khoảng `1ms`
  - content type: `audio/wav`

### So sánh nhanh với edge_tts
- `edge_tts`:
  - cold/warm synth thực tế khoảng nhiều giây
- `Piper local`:
  - synth local trên máy hiện tại dưới 1 giây cho câu test

### Lưu ý
- Đây là bản thay để test thực tế Piper trong luồng QA.
- Nếu bạn hài lòng về tốc độ nhưng chưa hài lòng về chất giọng, bước tiếp theo sẽ là đổi sang voice/model Piper Việt khác để so sánh chất lượng.

---

## Entry: 2026-04-13 15:46:47 +0700

### Trạng thái
- Dọn sạch luồng QA voice để chỉ còn `Piper`, không giữ song song `browser TTS` hay `edge_tts` fallback trong nhánh QA nữa.

### Đã sửa
- File: `services/qa_service.py`
  - xóa provider switch trong QA TTS
  - xóa nhánh synth bằng `edge_tts` khỏi luồng QA
  - cố định QA TTS dùng `Piper` và output `wav`
- File: `routes/qa.py`
  - cố định `POST /api/qa/tts` trả `audio/wav`
- File: `start_app.sh`
  - bỏ env `QA_TTS_PROVIDER` vì QA hiện không còn đa provider

### Làm rõ phạm vi
- `browser TTS`:
  - đã bị bỏ khỏi giao diện QA trước đó
- `edge_tts`:
  - đã bỏ khỏi luồng QA runtime
  - vẫn còn trong `scripts/generate_voice_asset.py` để phục vụ tạo asset voice tĩnh cho các phần khác của dự án nếu cần

### Đã kiểm tra
- `python3 -m py_compile services/qa_service.py routes/qa.py`
- `bash -n start_app.sh`
- `node --check static/js/qa_voice_demo.js`
- smoke test `/api/qa/tts`:
  - `200`
  - `audio/wav`
  - thời gian phản hồi khoảng dưới 1 giây cho câu test

---

## Entry: 2026-04-13 16:10:16 +0700

### Trạng thái
- Bổ sung lớp chuẩn hóa text cho QA voice để cải thiện cách đọc của Piper, đồng thời giữ lớp này đủ generic để áp dụng cho model voice khác trong tương lai.

### Đã sửa
- File: `services/qa_service.py`
  - quét `Rag_data` để lấy nhóm thuật ngữ Anh/viết tắt phổ biến rồi thêm vào từ điển đọc Việt hóa
  - thêm `TTS_MULTI_TERM_MAP` cho cụm nhiều từ như:
    - `Inspection Machine`
    - `Machine Vision`
    - `Camera AI`
    - `Smart Box`
    - `Flow Meter`
    - `QC Gate`
    - `Factory Automation`
    - `Saomai Solution Group`
  - thêm `TTS_TERM_MAP` cho viết tắt/thuật ngữ phổ biến như:
    - `AI`, `IoT`, `MES`, `ERP`, `PLC`, `HMI`, `QC`, `CDS`, `SME`, `SSG`, `CCTV`, `API`, `PDF`, `CAD`, `CNC`, `DB`, `OK`, `NG`
    - cùng một số từ kỹ thuật như `EcoSave`, `Dashboard`, `Server`, `Robot`, `Program`, `Signal`, `System`, `Vision`, `Switch`, `Compressor`, `Dryer`, `Reset`, `Laser`, `Traceability`
  - mở rộng `_prepare_tts_text()`:
    - đổi `;`, `:`, `/`, `->`, `-` thành nhịp nghỉ dễ nghe hơn
    - thay thế cách đọc cho cụm từ kỹ thuật
    - chuẩn hóa một số mẫu như `OK/NG`, `ON/OFF`, `CO2`, `m3/h`, `m3/min`, `mm`
    - làm sạch dấu câu để voice ngắt hợp lý hơn

- File: `static/js/qa_voice_demo.js`
  - nâng `sentence segmentation` phía client:
    - tách thêm theo `;`, `:`, `/`
    - chia nhỏ câu quá dài thành các đoạn ngắn hơn theo dấu phẩy
  - mục tiêu là giảm việc một segment quá dài bị đọc ngang

### Mục tiêu của thay đổi
- Cải thiện cách đọc tiếng Anh/viết tắt thường gặp bằng từ điển thay thế thủ công
- Tạo ngắt nghỉ tốt hơn với voice model local
- Giữ logic đủ độc lập với model để sau này đổi `Piper`, `Kokoro` hay model khác vẫn dùng lại lớp normalization này

### Đã kiểm tra
- `python3 -m py_compile services/qa_service.py`
- `node --check static/js/qa_voice_demo.js`

### Lưu ý
- Đây là lớp `text normalization + pronunciation dictionary + sentence segmentation`, không phụ thuộc riêng vào Piper.
- Nếu sau này đổi model voice, nên tiếp tục tái sử dụng lớp này trước khi đánh giá chất lượng voice thô của model mới.

---

## Entry: 2026-04-13 16:30:30 +0700

### Trạng thái
- Dọn môi trường và code để tập trung hoàn toàn vào `Piper` cho QA voice.

### Đã sửa
- File: `requirements.txt`
  - bỏ `edge-tts`
  - giữ lại `piper-tts`
- File: `scripts/generate_voice_asset.py`
  - xóa file vì không còn phục vụ luồng QA hiện tại

### Đã gỡ khỏi môi trường local
- `edge-tts`
- `kokoro-onnx`

### Đã kiểm tra
- import runtime:
  - `edge_tts` -> không còn import được
  - `kokoro_onnx` -> không còn import được
  - `piper` -> import được bình thường
- `pip list` chỉ còn `piper-tts` trong nhóm TTS đang dùng cho QA

### Kết luận
- QA voice hiện tại chỉ còn `Piper`
- Không còn dependency runtime của model voice khác trong nhánh QA

---

## Entry: 2026-04-13 16:41:30 +0700

### Trạng thái
- Hoàn tất bước triển khai thử nghiệm nhiều voice Piper tiếng Việt để tập trung tinh chỉnh chất lượng ngay trên nhánh `Piper-only`.

### Đã làm
- Thêm registry cho nhiều voice Piper Việt trong `services/qa_service.py`:
  - `vi_VN-vais1000-medium`
  - `vi_VN-25hours_single-low`
  - `vi_VN-vivos-x_low`
- Thêm cache `PiperVoice` theo từng voice để tránh load model lặp lại.
- Thêm API trạng thái TTS:
  - `GET /api/qa/tts-status`
  - trả về provider, active voice, segment pause và danh sách voice đã cài.
- Thêm benchmark script:
  - `python3 scripts/benchmark_piper_voices.py`
  - sinh file mẫu vào `.runtime/qa_tts_samples/` để nghe trực tiếp từng voice.
- Đồng bộ lại frontend QA để lấy `segment_pause_ms` từ backend thay vì hard-code cứng.

### Đã tải vào repo
- `models/tts/piper/vi_VN-vais1000-medium/vi_VN-vais1000-medium.onnx`
- `models/tts/piper/vi_VN-vais1000-medium/vi_VN-vais1000-medium.onnx.json`
- `models/tts/piper/vi_VN-25hours_single-low/vi_VN-25hours_single-low.onnx`
- `models/tts/piper/vi_VN-25hours_single-low/vi_VN-25hours_single-low.onnx.json`
- `models/tts/piper/vi_VN-vivos-x_low/vi_VN-vivos-x_low.onnx`
- `models/tts/piper/vi_VN-vivos-x_low/vi_VN-vivos-x_low.onnx.json`

### Đã kiểm tra
- `GET /api/qa/tts-status` trả đúng:
  - provider: `piper`
  - active voice: `vi_VN-vais1000-medium`
  - 3 voice Việt đều đã được nhận diện là `is_installed=true`
- Benchmark thực tế:
  - `vi_VN-vais1000-medium`: `337ms`
  - `vi_VN-25hours_single-low`: `311ms`
  - `vi_VN-vivos-x_low`: `277ms`
- Sample audio đã tạo tại:
  - `.runtime/qa_tts_samples/vi_VN-vais1000-medium.wav`
  - `.runtime/qa_tts_samples/vi_VN-25hours_single-low.wav`
  - `.runtime/qa_tts_samples/vi_VN-vivos-x_low.wav`

### Lưu ý
- Trong lúc synth benchmark vẫn xuất hiện cảnh báo `Missing phoneme from id map`; đây là dấu hiệu cần tiếp tục tinh chỉnh text normalization hoặc đổi voice mặc định nếu chất lượng đọc chưa đạt.
- Hiện tại voice mặc định vẫn giữ `vi_VN-vais1000-medium` để ưu tiên chất lượng trước tốc độ.
- Từ thời điểm này, hướng tối ưu tiếp theo sẽ chỉ xoay quanh `Piper`:
  - chọn voice mặc định tốt nhất
  - cải thiện cách đọc tiếng Anh/thuật ngữ
  - cải thiện ngắt nghỉ

---

## Entry: 2026-04-13 16:51:03 +0700

### Trạng thái
- Đổi voice mặc định của QA sang một model Piper khác để test trực tiếp, đồng thời sửa lỗi autoplay chỉ phát được khi bấm `Nghe lại trả lời`.

### Đã sửa
- File: `services/qa_service.py`
  - đổi default `QA_TTS_PIPER_VOICE` từ `vi_VN-vais1000-medium` sang `vi_VN-25hours_single-low`
- File: `start_app.sh`
  - đổi env mặc định `QA_TTS_PIPER_VOICE` sang `vi_VN-25hours_single-low`
- File: `static/js/qa_voice_demo.js`
  - bỏ cơ chế dùng chung `currentAudioController` cho mọi segment vì prefetch nhiều đoạn đã tự abort lẫn nhau
  - đổi sang quản lý nhiều `AbortController` độc lập theo từng request audio
  - thêm bước `unlockAudioPlayback()` để mở quyền phát audio ngay từ thao tác người dùng đầu tiên
  - gọi unlock trước khi start mic và trước khi replay, đồng thời gọi lại trước autoplay để giảm nguy cơ browser chặn `audio.play()`

### Đã kiểm tra
- `node --check static/js/qa_voice_demo.js`
- `python3 -m py_compile services/qa_service.py routes/qa.py`
- `get_qa_tts_status()['active_voice']` hiện trả:
  - `vi_VN-25hours_single-low`

### Lưu ý
- Nếu `.env` có set sẵn `QA_TTS_PIPER_VOICE` khác, giá trị đó vẫn sẽ override default mới.
- Fix autoplay hiện tại xử lý 2 nguyên nhân chính:
  - browser chặn phát tự động khi chưa unlock audio
  - logic prefetch cũ tự hủy request audio của chính nó khi câu trả lời bị chia thành nhiều segment

---

## Entry: 2026-04-15 20:35:02 +0700

### Trạng thái
- Sửa 2 lỗi runtime của `/qa-voice-demo`: báo sai quyền mic theo môi trường thiết bị và tiếp tục ghi âm trong lúc voice trả lời còn đang phát.

### Đã sửa
- File: `static/js/qa_voice_demo.js`
  - bỏ logic coi mọi lỗi `getUserMedia()` là lỗi quyền mic; chỉ các lỗi permission thật (`NotAllowedError`, `SecurityError`, `PermissionDeniedError`) mới báo `Chưa có quyền mic`
  - thêm nhánh `Permissions API` để đọc đúng trạng thái quyền mic khi browser hỗ trợ
  - với các lỗi mic không phải permission, cho phép recognition tự thử start thay vì chặn cứng ngay từ bước preflight
  - thêm cờ `speakingActive`
  - khi đang phát audio trả lời, dừng recognition và chặn mọi vòng restart nhận voice
  - chỉ resume nhận voice sau khi audio trả lời phát xong
  - chặn xử lý transcript mới nếu audio trả lời vẫn đang phát

### Đã kiểm tra
- `node --check static/js/qa_voice_demo.js`

### Lưu ý
- Bản sửa này giải quyết lỗi frontend tự báo sai `Chưa có quyền mic` khi môi trường mic thay đổi, nhưng nếu máy thực sự không còn nguồn `audio input` nào thì recognition vẫn sẽ không hoạt động; lúc đó status sẽ không còn đổ nhầm sang lỗi permission.
- Luồng hiện tại đã được siết về nguyên tắc:
  - ghi âm câu hỏi
  - nhận answer text
  - phát voice answer
  - chỉ sau khi voice answer kết thúc mới ghi âm tiếp

---

## Entry: 2026-04-15 20:59:53 +0700

### Trạng thái
- Siết tiếp state machine của `/qa-voice-demo` để tránh nuốt câu hỏi dở và tránh ghi nhận câu 2 khi câu 1 còn đang xử lý hoặc đang phát voice.

### Đã sửa
- File: `static/js/qa_voice_demo.js`
  - thêm cờ `qaBusy` để khóa toàn bộ nhận câu hỏi mới từ lúc bắt đầu gọi `/api/qa/ask` cho tới khi voice của câu trả lời phát xong
  - thêm `pendingQuestionDraft` và timer commit `3000ms`
  - transcript nhận được sẽ vào draft trước; chỉ sau `3 giây` im lặng mới được chốt thành câu hỏi thật để gửi sang RAG
  - nếu người dùng đang ngập ngừng hoặc nói nối tiếp, transcript mới sẽ được nối vào draft hiện tại và reset lại timer `3000ms`
  - trong lúc đang có draft chờ chốt, status chuyển sang `Đang chờ hoàn tất câu hỏi`
  - trong lúc đang xử lý câu hỏi hoặc đang phát voice, recognition sẽ không restart

### Đã kiểm tra
- `node --check static/js/qa_voice_demo.js`

### Lưu ý
- Logic hiện tại ưu tiên an toàn cho hội thoại:
  - không ghi nhận câu 2 khi câu 1 còn chưa xong
  - không chốt quá sớm một câu hỏi dở
- Ngưỡng `3000ms` đang được hard-code theo đúng yêu cầu hiện tại; nếu cần sau này có thể tách ra env/config riêng.

---

## Entry: 2026-04-16 11:06:24 +0700

### Trạng thái
- Bổ sung 2 file dữ liệu mới vào `Rag_data` và nạp lại vào index RAG để mở rộng khả năng hỏi đáp về chính dự án Bamboo Kiosk và nhóm giao tiếp cơ bản.

### Đã thêm
- File mới: `Rag_data/bamboo.txt`
  - tổng hợp thông tin toàn dự án Bamboo Kiosk:
    - Bamboo Kiosk là gì
    - mục tiêu
    - đối tượng sử dụng
    - chức năng kiosk
    - quy trình đăng ký
    - OCR, khuôn mặt, khách quay lại
    - đặt lịch
    - dashboard
    - Q&A
    - RAG và cách nạp dữ liệu
    - công nghệ chính
    - ứng dụng thực tế
- File mới: `Rag_data/giao_tiep_co_ban.txt`
  - khoảng hơn 30 câu giao tiếp cơ bản để xử lý các câu hỏi xã giao hoặc câu hỏi đơn giản ngoài nhóm sản phẩm

### Đã sửa
- File: `services/qa_service.py`
  - thêm `SOURCE_ALIASES` cho:
    - `bamboo`
    - `giao_tiep_co_ban`
  - thêm `SOURCE_FILTER_PATTERNS` để:
    - câu hỏi về Bamboo Kiosk ưu tiên `bamboo.txt`
    - câu hỏi xã giao như `Bạn là ai`, `Xin chào`, `Cảm ơn` ưu tiên `giao_tiep_co_ban.txt`

### Đã nạp dữ liệu
- Chạy:
  - `python3 scripts/rebuild_rag_index.py`
- Kết quả:
  - index trước rebuild: `105 chunks`
  - index sau rebuild: `122 chunks`
  - trạng thái sau rebuild: `is_ready=True`, `is_stale=False`

### Đã kiểm tra
- `python3 -m py_compile services/qa_service.py`
- Test:
  - `Bamboo Kiosk là gì và có những chức năng nào?`
    - matched source: `bamboo.txt`
  - `Bạn là ai?`
    - matched source: `giao_tiep_co_ban.txt`

### Lưu ý
- Trong dự án này, `nạp data` nghĩa là:
  1. thêm file `.txt` hoặc `.md` vào thư mục `Rag_data`
  2. rebuild lại RAG index
  3. hệ thống chunk file, tạo embedding và lưu vector vào SQLite
  4. từ đó Q&A mới truy xuất được dữ liệu mới
- Có 2 cách nạp:
  - thủ công: `python3 scripts/rebuild_rag_index.py`
  - tự động: chạy `bash start_app.sh` với `QA_PREBUILD_INDEX=1`, app sẽ tự kiểm tra index có stale hay không và rebuild nếu cần

---

## Entry: 2026-04-16 11:13:27 +0700

### Trạng thái
- Chuẩn hóa lại corpus Bamboo sang tiếng Việt có dấu, bổ sung file FAQ riêng cho Bamboo và nạp lại vào RAG index.

### Đã sửa
- File: `Rag_data/bamboo.txt`
  - viết lại toàn bộ sang tiếng Việt có dấu
  - bỏ cách diễn đạt kiểu `kiosk là gì` trong tiêu đề/cấu trúc tài liệu
  - giữ vai trò là tài liệu mô tả tổng quan toàn dự án
- File: `Rag_data/giao_tiep_co_ban.txt`
  - viết lại toàn bộ sang tiếng Việt có dấu
  - giữ vai trò xử lý các câu xã giao và giao tiếp cơ bản
- File mới: `Rag_data/bamboo_faq.txt`
  - thêm bộ FAQ riêng cho Bamboo
  - tập trung vào câu hỏi thường gặp về chức năng, dashboard, OCR, khuôn mặt, lịch hẹn, RAG, dữ liệu và lợi ích của hệ thống
- File: `services/qa_service.py`
  - thêm `bamboo_faq` vào `SOURCE_ALIASES`
  - mở rộng `SOURCE_FILTER_PATTERNS` để câu hỏi về Bamboo ưu tiên cả `bamboo.txt` và `bamboo_faq.txt`

### Đã nạp dữ liệu
- Chạy:
  - `python3 scripts/rebuild_rag_index.py`
- Kết quả:
  - index trước rebuild: `122 chunks`
  - index sau rebuild: `127 chunks`
  - trạng thái sau rebuild: `is_ready=True`, `is_stale=False`

### Lưu ý
- Từ thời điểm này, corpus Bamboo trong `Rag_data` đã được tách thành 3 lớp:
  - `bamboo.txt`: tài liệu tổng quan dự án
  - `bamboo_faq.txt`: FAQ chuyên cho Bamboo
  - `giao_tiep_co_ban.txt`: giao tiếp cơ bản

---

## Entry: 2026-04-16 11:46:39 +0700

### Trạng thái
- Triển khai 2 bước đầu tiên của lộ trình nâng cấp RAG:
  - chuẩn hóa corpus theo metadata
  - router rõ hơn giữa `rule / faq / rag / dynamic_reserved / fallback`

### Đã sửa
- File: `services/qa_service.py`
  - thêm `SOURCE_CATALOG` cho từng nguồn trong `Rag_data`
  - mỗi nguồn hiện có metadata chuẩn:
    - `topic`
    - `product`
    - `lang`
    - `source_kind`
    - `priority`
    - `updated_at`
  - metadata này được nạp vào từng chunk khi build index
  - thêm `FAQ_SOURCE_STEMS`
  - thêm `DYNAMIC_ROUTE_PATTERNS`
  - thêm `_source_catalog_entry(...)`
  - thêm `_classify_question_route(...)`
  - thêm `priority_bonus` trong scoring retrieval dựa trên metadata nguồn

### Router hiện tại
- `rule`
  - dùng cho các luật nghiệp vụ đã chốt của dự án Bamboo
- `faq`
  - dùng cho các câu thuộc `giao_tiep_co_ban.txt` hoặc `bamboo_faq.txt`
- `rag`
  - dùng cho các câu tài liệu/product/company từ `Rag_data`
- `dynamic_reserved`
  - dùng cho các câu hỏi dữ liệu sống như lịch hẹn của tôi, ai phụ trách, khung giờ trống
  - hiện tại chưa mở DB/app query nên sẽ fallback về lễ tân
- `fallback`
  - dùng khi retrieve không đủ tin cậy

### Đã nạp lại index
- Chạy:
  - `python3 scripts/rebuild_rag_index.py`
- Kết quả:
  - index sau rebuild vẫn sẵn sàng: `127 chunks`
  - trạng thái: `is_ready=True`, `is_stale=False`

### Đã kiểm tra
- `python3 -m py_compile services/qa_service.py`
- Smoke test 4 nhánh:
  - `Kiosk hiện hỗ trợ những chức năng chính nào?`
    - route: `rule`
  - `Bạn là ai?`
    - route: `faq`
    - source: `giao_tiep_co_ban.txt`
  - `EcoSave giúp tiết kiệm điện như thế nào?`
    - route: `rag`
  - `Hôm nay tôi có lịch hẹn nào không?`
    - route: `dynamic_reserved`
    - answer: fallback lễ tân

### Lưu ý
- Đây là bước đặt nền, chưa phải reranker hay eval retrieval.
- Metadata hiện đã có trong từng chunk/index, tạo điều kiện cho:
  - filter theo topic/product
  - routing chính xác hơn
  - đo retrieval ở bước sau

---

## Entry: 2026-04-16 15:02:21 +0700

### Trạng thái
- Sửa lỗi QA voice bị ghi nhận trùng cùng một câu hỏi và dẫn tới append nhiều câu trả lời trên UI.

### Nguyên nhân
- `SpeechRecognition` có thể bắn lại cùng một transcript ở các vòng nhận kế tiếp.
- Trong lúc đang có `pendingQuestionDraft`, recognition vẫn tự restart nên cùng một câu có thể bị thu lại lần nữa.
- Không có tầng dedupe ở lúc commit câu hỏi thật lên `/api/qa/ask`.

### Đã sửa
- File: `static/js/qa_voice_demo.js`
  - thêm `normalizeQuestionKey(...)` để chuẩn hóa transcript/câu hỏi trước khi so trùng
  - thêm `lastResultKey` và `lastResultAtMs`
    - chặn transcript giống hệt vừa nhận trong khoảng ngắn
  - thêm `lastSubmittedQuestionKey` và `lastSubmittedAtMs`
    - chặn submit cùng một câu hỏi lần hai trong vòng `8 giây`
  - khi đang có `pendingQuestionDraft`, recognition `end/no-speech` không tự restart ngay nữa
    - chỉ chờ hết timer `3 giây` để commit một lần
  - reset các mốc dedupe khi `Làm mới`

### Đã kiểm tra
- `node --check static/js/qa_voice_demo.js`

### Lưu ý
- Bản sửa này nhắm đúng lỗi kiểu:
  - một câu hỏi bị ghi nhận thành 2 dòng trong `Câu hỏi đã nhận`
  - một câu trả lời đúng bị nối thêm fallback không mong muốn
  - voice chỉ đọc câu trả lời cuối cùng do state bị ghi đè bởi lần submit trùng

---

## Entry: 2026-04-16 15:52:28 +0700

### Trạng thái
- Hoàn tất bước `eval retrieval` đầu tiên với bộ 40 câu chuẩn và lấy được baseline cho router/retrieval hiện tại.

### Đã thêm
- File: `rag/eval/qa_retrieval_eval_cases.json`
  - bộ 40 câu đánh giá chia theo nhóm:
    - `rule`
    - `faq`
    - `rag`
    - `dynamic_reserved`
    - `fallback`
- File: `scripts/run_qa_retrieval_eval.py`
  - script chạy eval trực tiếp trên `answer_static_question(...)`
  - đo:
    - `route_accuracy`
    - `mode_accuracy`
    - `source_hit_rate`
    - `fallback_accuracy`
  - in ra danh sách case fail để debug tiếp

### Đã sửa trong lúc chạy baseline
- File: `services/qa_service.py`
  - bỏ pattern `hi` khỏi `SOURCE_FILTER_PATTERNS` vì match quá rộng và làm nhiễu route
  - thêm pattern `tôi đang bối rối / toi dang boi roi` vào nhánh `giao_tiep_co_ban`
- File: `rag/eval/qa_retrieval_eval_cases.json`
  - chỉnh kỳ vọng của case `Bamboo có dashboard không?` sang `rule` để phản ánh đúng kiến trúc hiện tại

### Đã kiểm tra
- `python3 -m py_compile services/qa_service.py scripts/run_qa_retrieval_eval.py`
- Chạy:
  - `python3 scripts/run_qa_retrieval_eval.py`

### Baseline hiện tại
- Tổng số case: `40`
- Pass: `38`
- Fail: `2`
- `route_accuracy = 1.0`
- `mode_accuracy = 1.0`
- `source_hit_rate = 0.95`
- `fallback_accuracy = 1.0`

### Fail còn lại
- Cả 2 fail đều thuộc nhóm `Camera AI`
- Hệ thống trả lời đúng nội dung, nhưng source kéo về:
  - `RAG_saomai1.txt`
  - `RAG_saomai2.txt`
- thay vì ưu tiên:
  - `camera_AI.txt`

### Kết luận
- Router hiện tại đã ổn ở mức baseline:
  - rule
  - faq
  - rag
  - dynamic_reserved
  - fallback
- Điểm còn yếu nhất bây giờ không phải route hay fallback, mà là `source specificity` trong retrieval của một số nhóm câu hỏi gần nghĩa, đặc biệt là `Camera AI`.
- Đây là đúng thời điểm để bước sau cân nhắc `reranker` hoặc tăng trọng số/filter theo source/product cho từng nhóm câu hỏi.

---

## Entry: 2026-04-16 15:59:23 +0700

### Trạng thái
- Cải thiện source specificity cho retrieval và đưa baseline eval từ `38/40` lên `40/40` mà chưa cần thêm reranker nặng.

### Đã sửa
- File: `services/qa_service.py`
  - tách `PRIORITY_SOURCE_FILTER_PATTERNS`
  - đổi `_detect_source_filters(...)` sang cơ chế:
    - ưu tiên pattern đặc thù trước
    - sau đó mới fallback sang pattern tổng quát
  - các nhóm sản phẩm giờ ưu tiên đúng source riêng:
    - `ecosave` -> `ECOSAVE.txt`
    - `camera_ai` -> `camera_AI.txt`
    - `smart_box` -> `Smart_box.txt`
    - `inspection_machine` -> `inspection_machine.txt`
  - nhờ đó câu hỏi chứa đồng thời tên sản phẩm và `SSG/Sao Mai` không còn kéo nhầm tài liệu công ty lên trước

### Đã kiểm tra
- `python3 -m py_compile services/qa_service.py`
- Chạy lại:
  - `python3 scripts/run_qa_retrieval_eval.py`

### Baseline mới
- Tổng số case: `40`
- Pass: `40`
- Fail: `0`
- `route_accuracy = 1.0`
- `mode_accuracy = 1.0`
- `source_hit_rate = 1.0`
- `fallback_accuracy = 1.0`

### Kết luận
- Với bộ eval hiện tại, việc siết route/filter đã đủ để giải quyết điểm yếu `Camera AI`.
- Chưa cần thêm reranker phức tạp ở thời điểm này.
- Bước tiếp theo hợp lý hơn là:
  - mở rộng bộ eval lên 50+ case
  - thêm mode eval nhanh
  - chỉ cân nhắc reranker khi baseline mới xuất hiện fail thật sự mà route/filter không xử lý được.

---

## Entry: 2026-04-16 16:09:52 +0700

### Trạng thái
- Sửa lỗi QA page đôi khi append thêm một câu trả lời fallback giả sau câu trả lời đúng, đồng thời tăng tốc mạnh cho nhánh FAQ/giao tiếp cơ bản.

### Nguyên nhân
- File: `static/js/qa_voice_demo.js`
  - lỗi playback voice trước đó bị rơi vào cùng `catch` với lỗi lấy answer text
  - hậu quả là:
    - answer đúng đã được append vào UI
    - sau đó nếu playback lỗi hoặc bị gián đoạn, code lại append thêm fallback `Tôi chưa có đủ thông tin...`
- File: `services/qa_service.py`
  - nhánh `faq` vẫn gọi Ollama generate như nhánh `rag`
  - với các câu đơn giản như `Xin chào`, thời gian sinh text bị kéo dài không cần thiết
  - FAQ parser còn đang parse theo format cũ nên đọc sai câu trả lời từ `giao_tiep_co_ban.txt`

### Đã sửa
- File: `static/js/qa_voice_demo.js`
  - tách lỗi playback voice ra khỏi lỗi lấy answer text
  - `autoSpeakAnswer()` giờ chỉ log lỗi phát voice, không được phép append thêm fallback giả vào `answerHistory`
- File: `services/qa_service.py`
  - nhánh `faq` không còn gọi Ollama generate nữa
  - thay bằng `faq_extractive` trực tiếp từ source file FAQ/giao tiếp
  - thêm `_parse_faq_entries(...)`
    - hỗ trợ cả 2 format:
      - `Câu hỏi` + `Trả lời gợi ý: ...`
      - `Câu hỏi` + `dòng trả lời ngay bên dưới`
  - thêm `_extract_faq_answer(...)` đọc trực tiếp từ file nguồn trong `Rag_data`
  - thêm `_normalize_answer_text(...)` để tránh cắt mất phần đầu của câu trả lời FAQ như `Xin chào quý khách...`

### Đã kiểm tra
- `python3 -m py_compile services/qa_service.py`
- `node --check static/js/qa_voice_demo.js`
- Test trực tiếp:
  - câu: `Xin chào`
  - mode: `faq_extractive`
  - source: `giao_tiep_co_ban.txt`
  - answer: `Xin chào quý khách. Tôi có thể hỗ trợ giới thiệu về Bamboo, Sao Mai Solution Group, các giải pháp hoặc hướng dẫn đặt lịch.`
  - backend elapsed: khoảng `33.84ms`

### Kết quả kỳ vọng trên UI
- Không còn case:
  - 1 câu hỏi
  - nhưng 2 câu trả lời, trong đó câu thứ hai là fallback giả
- Các câu FAQ/giao tiếp cơ bản như:
  - `Xin chào`
  - `Bạn là ai?`
  - `Cảm ơn`
  - `Tôi đang bối rối`
  sẽ ra text nhanh hơn rất nhiều so với trước vì không còn đi qua LLM generate.

---

## Entry: 2026-04-16 17:00:57 +0700

### Trạng thái
- Cải thiện tốc độ hiển thị text của phần nhận voice câu hỏi trên `/qa-voice-demo`: transcript giờ đi đến đâu hiện tới đó, và câu hỏi được chốt sau `2 giây` không có voice mới.

### Đã sửa
- File: `static/js/qa_voice_demo.js`
  - bật `recognition.interimResults = true`
  - thêm `pendingQuestionInterim`
  - `renderQuestionHistory()` giờ hiển thị cả:
    - lịch sử câu hỏi đã chốt
    - draft/interim transcript đang được nói
  - khi người dùng đang nói, status chuyển sang `Đang ghi nhận câu hỏi`
  - giảm timer commit câu hỏi từ `3000ms` xuống `2000ms`
  - nếu recognition tự `end` trong lúc vẫn còn draft/interim, hệ thống sẽ restart nhanh để tiếp tục nghe và nối transcript

### Kết quả mong muốn
- Người dùng nói tới đâu, text phần `Câu hỏi đã nhận` sẽ hiện tới đó
- Không cần chờ quá lâu mới thấy text xuất hiện
- Sau khi ngừng nói khoảng `2 giây`, hệ thống mới chốt câu hỏi và gửi sang backend

### Đã kiểm tra
- `node --check static/js/qa_voice_demo.js`

### Lưu ý
- Đây là cải thiện ở tầng STT frontend, không thay đổi RAG backend.
- Tốc độ cuối cùng vẫn còn phụ thuộc vào khả năng `SpeechRecognition` của browser, nhưng độ trễ hiển thị transcript sẽ giảm rõ so với trước vì không còn đợi đến lúc commit xong mới render câu hỏi.

---

## Entry: 2026-04-16 18:25:37 +0700

### Trạng thái
- Bổ sung stream answer cho `/qa-voice-demo` để phần `Câu trả lời` hiển thị dần theo từng chunk do backend/LLM sinh ra, thay vì chờ xong toàn bộ câu trả lời mới render.

### Đã sửa
- File: `services/qa_service.py`
  - thêm `_iter_ollama_generate_chunks(...)` gọi Ollama `/api/generate` với `stream=True`
  - thêm `_build_qa_result(...)` để gom payload kết quả cuối thống nhất
  - thêm `stream_answer_static_question(...)`
    - `rule` / `faq` / `dynamic_reserved` / `fallback`:
      - trả ngay `answer_delta` + `done`
    - `rag`:
      - stream từng `answer_delta` khi Ollama trả chunk mới
      - nếu stream lỗi thì fallback sang `extractive` và phát `replace_answer`
      - cuối cùng phát `done` với payload kết quả đầy đủ để lưu DB và phát voice
- File: `routes/qa.py`
  - thêm endpoint `POST /api/qa/ask-stream`
  - dùng `application/x-ndjson`
  - chỉ lưu `qa_history` khi nhận event `done`, tránh lưu bản answer chưa hoàn tất
- File: `static/js/qa_voice_demo.js`
  - thêm `pendingAnswerDraft`
  - `renderAnswerHistory()` giờ hiển thị:
    - answer history đã chốt
    - answer draft đang stream
  - `askQuestion()` chuyển từ `/api/qa/ask` sang `/api/qa/ask-stream`
  - đọc `ReadableStream`, parse NDJSON và:
    - nối `answer_delta` vào `pendingAnswerDraft`
    - nhận `replace_answer` nếu backend phải thay toàn bộ draft
    - chỉ khi `done` mới commit vào `answerHistory` và bắt đầu TTS

### Đã kiểm tra
- `node --check static/js/qa_voice_demo.js`
- `python3 -m py_compile routes/qa.py services/qa_service.py`
- Smoke test với Flask test client:
  - câu `Xin chào`
    - nhận được `answer_delta` rồi `done`
  - câu `EcoSave giúp tiết kiệm điện như thế nào?`
    - nhận được nhiều `answer_delta` nhỏ liên tiếp rồi `done`

### Kết quả kỳ vọng trên UI
- Với câu FAQ ngắn:
  - `Câu trả lời` sẽ hiện gần như ngay lập tức
- Với câu RAG/LLM:
  - text sẽ tăng dần theo chunk sinh ra
  - không còn phải chờ xong đủ 3-5 câu mới thấy gì
- Voice vẫn chỉ phát sau khi backend chốt xong answer cuối cùng
  - mục tiêu của lần sửa này là giảm thời gian chờ nhìn thấy text, không phải stream TTS

---

## Entry: 2026-04-16 18:29:56 +0700

### Trạng thái
- Sửa nhánh QA voice để không còn gộp nhiều lỗi microphone/speech service vào cùng một thông báo `Chưa có quyền mic`.

### Nguyên nhân
- File: `static/js/qa_voice_demo.js`
  - trước đó `ensureMicPermission()` và `recognition.error` đang coi nhiều lỗi khác nhau là cùng một loại lỗi permission
  - đặc biệt:
    - `not-allowed`
    - `service-not-allowed`
    - lỗi không có input device / không truy cập được audio input
  - đều dễ bị hiển thị sai thành `Chưa có quyền mic`

### Đã sửa
- Thêm `resolveMicAccessState()`
  - phân biệt:
    - `granted`
    - `denied`
    - `unavailable`
    - `unsupported`
    - `unknown`
- Thêm `applyMicAccessState()`
  - map từng trạng thái sang đúng status/message UI
- Thêm `appendSystemAnswer()`
  - tránh append trùng các thông báo hệ thống vào `Câu trả lời`
- `ensureMicPermission()`
  - chuyển sang dùng `resolveMicAccessState()` thay vì tự gộp lỗi
- `recognition.error`
  - với `not-allowed` / `service-not-allowed`:
    - re-check lại trạng thái mic thật
    - nếu mic thực tế vẫn `granted` thì báo `Dịch vụ nhận giọng nói chưa sẵn sàng`
    - không còn đổ sai sang lỗi quyền mic

### Đã kiểm tra
- `node --check static/js/qa_voice_demo.js`

### Kết quả kỳ vọng
- Nếu browser thật sự chặn permission:
  - status: `Chưa có quyền mic`
- Nếu máy không có hoặc không truy cập được input device:
  - status: `Mic chưa sẵn sàng`
- Nếu mic có quyền nhưng speech service của browser lỗi:
  - status: `Dịch vụ nhận giọng nói chưa sẵn sàng`

---

## Entry: 2026-04-16 20:37:01 +0700

### Trạng thái
- Giảm hiện tượng transcript câu hỏi bị chập chờn/biến mất tạm thời trên `/qa-voice-demo`, đồng thời rút ngắn thêm thời gian chốt câu hỏi khi nội dung đã đủ rõ.

### Nguyên nhân
- File: `static/js/qa_voice_demo.js`
  - trước đó phần `Câu hỏi đã nhận` render trực tiếp từ `pendingQuestionDraft + pendingQuestionInterim`
  - transcript interim của `SpeechRecognition` có thể dao động từng event:
    - lúc có
    - lúc trống tạm thời
    - lúc bị browser rút ngắn rồi cập nhật lại
  - hậu quả là text hiển thị nhấp nháy hoặc biến mất ngắn rồi hiện lại
- Ngoài ra thời gian chốt câu hỏi đang dùng một ngưỡng cứng `2000ms`
  - với các câu đã đủ ý hoặc đã có dấu kết thúc, đây là thời gian chờ dài hơn mức cần thiết

### Đã sửa
- File: `static/js/qa_voice_demo.js`
  - thêm `stableQuestionPreview`
    - giữ một bản preview ổn định hơn của transcript đang nói
    - không xóa ngay chỉ vì một event interim tạm thời trống
  - thêm `syncStableQuestionPreview()`
    - chỉ cập nhật preview khi có transcript mới
    - chỉ xóa cứng khi reset/commit xong
  - `renderQuestionHistory()` giờ hiển thị `stableQuestionPreview` thay vì bám trực tiếp vào interim raw
  - thêm `getQuestionCommitDelayMs()`
    - `1200ms` nếu câu có dấu kết thúc `. ! ?`
    - `1500ms` nếu câu đã khá dài và không còn interim
    - `2000ms` cho các case còn lại

### Đã kiểm tra
- `node --check static/js/qa_voice_demo.js`

### Kết quả kỳ vọng
- Text trong `Câu hỏi đã nhận` sẽ ổn định hơn, ít bị hiện rồi mất lại trong lúc người dùng vẫn đang nói
- Với câu đã đủ ý, thời gian chốt câu hỏi có thể giảm khoảng `0.5s` đến `0.8s`
- Mục tiêu là cải thiện thêm 1 phần cảm nhận tốc độ mà không phá độ an toàn của logic `chờ người nói xong`

---

## Entry: 2026-04-16 21:18:41 +0700

### Trạng thái
- Đổi mô hình lưu lịch sử Q&A từ `mỗi câu hỏi/đáp = 1 dòng DB` sang `mỗi phiên hỏi đáp = 1 dòng DB`, và dashboard Q&A hiển thị theo phiên hội thoại.

### Đã sửa
- File: `database/update_database.py`
  - mở rộng bảng `qa_history` với các cột:
    - `session_key`
    - `conversation_json`
    - `turn_count`
    - `updated_at`
  - thêm migration cho DB cũ:
    - backfill `updated_at` từ `created_at`
  - `create_qa_history(...)` giờ hỗ trợ:
    - nếu có `session_key` mới:
      - tạo mới 1 phiên
    - nếu `session_key` đã tồn tại:
      - append thêm 1 lượt hỏi-đáp vào `conversation_json`
      - update `turn_count`, `answer`, `answer_mode`, `matched_sources`, `updated_at`
  - `list_qa_history(...)` giờ:
    - parse `conversation_json`
    - sort theo `updated_at`
    - fallback tương thích với record cũ chưa có `conversation_json`
- File: `routes/qa.py`
  - `/api/qa/ask`
  - `/api/qa/ask-stream`
  - đều nhận `session_key` từ frontend và lưu theo phiên
- File: `static/js/qa_voice_demo.js`
  - thêm `qaSessionKey`
  - tạo `session_key` mới khi vào page
  - chỉ tạo `session_key` mới khi bấm `Làm mới`
  - pause/resume bằng nút `Bắt đầu/Kết thúc` không tạo phiên mới
- File: `static/js/dashboard.js`
  - list Q&A đổi từ `lượt hỏi đáp` sang `phiên hỏi đáp`
  - mỗi item list hiển thị:
    - câu hỏi đầu phiên
    - câu trả lời cuối phiên
    - số lượt trong phiên
  - detail panel hiển thị toàn bộ hội thoại:
    - danh sách câu hỏi
    - danh sách câu trả lời
    - meta theo phiên
- File: `templates/index_dashboard.html`
  - đổi label tĩnh:
    - `0 phiên hỏi đáp`
    - `Chọn một phiên Q&A`
    - `xem toàn bộ hội thoại`

### Đã kiểm tra
- `python3 -m py_compile database/update_database.py routes/qa.py`
- `node --check static/js/qa_voice_demo.js`
- `node --check static/js/dashboard.js`
- Smoke test:
  - gửi 2 câu hỏi với cùng `session_key`
  - DB chỉ dùng 1 record
  - `conversation_json` được append
  - `turn_count` tăng đúng

### Kết quả kỳ vọng
- Trong `/qa-voice-demo`:
  - hỏi nhiều câu liên tiếp trong cùng phiên sẽ chỉ cập nhật 1 bản ghi DB
  - chỉ khi bấm `Làm mới` mới bắt đầu phiên lưu mới
- Trong dashboard:
  - Q&A được xem theo `phiên hội thoại`, không còn tách thành từng dòng hỏi-đáp rời rạc

---

## Entry: 2026-04-17 20:11:45 +0700

### Trạng thái
- Bắt đầu bước 2 tối ưu latency RAG/QA theo hướng ít rủi ro: cache kết quả câu hỏi, cache retrieval, và rút gọn context đưa vào prompt.

### Đã sửa
- File: `services/qa_service.py`
  - thêm config:
    - `QA_RESULT_CACHE_TTL_SEC`
    - `QA_RETRIEVE_CACHE_TTL_SEC`
    - `QA_RAG_PROMPT_TOP_K`
    - `QA_RAG_PROMPT_MAX_CHARS`
  - thêm cache ngắn hạn:
    - `_QA_RESULT_CACHE`
    - `_QA_RETRIEVE_CACHE`
  - thêm helper:
    - `_prune_small_cache(...)`
    - `_make_question_cache_key(...)`
    - `_clone_qa_result(...)`
    - `_get_cached_answer_result(...)`
    - `_set_cached_answer_result(...)`
  - `_retrieve_rag(...)`
    - cache lại kết quả retrieval theo:
      - index
      - embed model
      - question
      - source filters
  - `_build_augmented_prompt(...)`
    - chỉ lấy `QA_RAG_PROMPT_TOP_K`
    - chặn tổng context ở `QA_RAG_PROMPT_MAX_CHARS`
    - giảm prompt size cho nhánh `rag`
  - `stream_answer_static_question(...)`
    - check cache ngay đầu vào
    - lưu cache sau các nhánh:
      - `rule`
      - `dynamic_reserved`
      - `fallback`
      - `faq_extractive`
      - `rag`
  - `answer_static_question(...)`
    - check cache ngay đầu vào
    - lưu cache ở toàn bộ nhánh trả lời

### Đã kiểm tra
- `python3 -m py_compile services/qa_service.py routes/qa.py`
- Benchmark ngoài sandbox:
  - FAQ lặp lại:
    - câu hỏi: `Xin chào`
    - wall time lần 1: `434ms`
    - wall time lần 2: `0ms`
  - RAG lặp lại:
    - câu hỏi: `Smart Box dùng để làm gì trong nhà máy?`
    - wall time lần 1: `6291ms`
    - wall time lần 2: `0ms`
    - source vẫn đúng: `Smart_box.txt`

### Lưu ý
- `response_ms` trong payload hiện vẫn là thời gian build result ở lần gốc; benchmark trên đây dùng wall-clock ngoài hàm để đo hiệu quả cache thật.
- Bộ eval `scripts/run_qa_retrieval_eval.py` trong sandbox bị chặn kết nối localhost tới Ollama, nên không dùng số đó để đánh giá logic sau thay đổi.

---

## Entry: 2026-04-17 21:15:11 +0700

### Trạng thái
- Tiếp tục bước 2: giảm latency **lần hỏi đầu tiên** cho nhánh `rag`, không chỉ lượt lặp.

### Đã sửa
- File: `services/qa_service.py`
  - nâng cấp `_extract_answer_from_contexts(...)`
    - chấm điểm theo câu thay vì lấy câu đầu của chunk
    - dùng overlap token với câu hỏi
    - ưu tiên câu có tính giải thích như:
      - `dùng để`
      - `ứng dụng để`
      - `giúp`
      - `cho phép`
      - `có thể`
    - phạt các câu kiểu:
      - tiêu đề tài liệu
      - `Pain points`
      - câu có tỷ lệ chữ hoa bất thường
      - câu mở đầu bằng `Khả năng tương thích`
  - thêm `_should_use_extractive_fast_path(...)`
    - nếu câu hỏi thuộc nhánh `rag` nhưng retrieval rất rõ ràng / source-specific
    - đi thẳng `extractive_fast`
    - bỏ qua bước generate của Ollama
  - áp dụng fast-path này cho cả:
    - `stream_answer_static_question(...)`
    - `answer_static_question(...)`

### Đã kiểm tra
- `python3 -m py_compile services/qa_service.py`
- Benchmark ngoài sandbox:
  - câu hỏi: `Smart Box dùng để làm gì trong nhà máy?`
  - trước fast-path:
    - wall time: `8457ms`
    - mode: `rag`
  - sau fast-path:
    - wall time: `55ms`
    - mode: `extractive_fast`
    - source đúng: `Smart_box.txt`
    - answer:
      - `Ứng dụng để kiểm soát thông số trên hệ thống máy khắc Laser (Lazer), dây chuyền sản xuất nội thất gỗ công nghiệp, và thậm chí đáp ứng được các tiêu chuẩn khắt khe trong hệ thống sản xuất động cơ máy bay.`

### Lưu ý
- Fast-path này chỉ áp dụng khi retrieval đủ rõ và câu hỏi mang tính factual/source-specific.
- Những câu mơ hồ hoặc cần diễn đạt tổng hợp vẫn giữ nhánh `rag` qua Ollama như trước.

---

## Entry: 2026-04-17 21:17:04 +0700

### Trạng thái
- Chốt bước 2 bằng cách thêm cache ở tầng embedding/query để tối ưu cả trường hợp cùng câu hỏi nhưng khác `channel/session`.

### Đã sửa
- File: `services/qa_service.py`
  - thêm config:
    - `QA_EMBED_CACHE_TTL_SEC`
  - thêm cache:
    - `_QA_EMBED_CACHE`
  - thêm helper:
    - `_embed_query_text(...)`
  - `_retrieve_rag(...)`
    - đổi từ:
      - `_embed_texts([question], QA_EMBED_MODEL)[0]`
    - sang:
      - `_embed_query_text(question, QA_EMBED_MODEL)`

### Đã kiểm tra
- `python3 -m py_compile services/qa_service.py`
- Benchmark ngoài sandbox, cùng câu hỏi nhưng khác `channel` để bypass result cache:
  - câu hỏi: `Smart Box dùng để làm gì trong nhà máy?`
  - lần A:
    - wall time: `58ms`
    - mode: `extractive_fast`
  - lần B, khác channel:
    - wall time: `1ms`
    - mode: `extractive_fast`
  - answer giữ nguyên giữa hai lần

### Kết luận bước 2
- Đã hoàn thành bước 2 theo phạm vi tối ưu latency backend của Q&A/RAG:
  - cache kết quả câu hỏi
  - cache retrieval
  - cache embedding query
  - prompt context gọn hơn
  - fast-path extractive cho câu factual/source-specific
- Các nhánh vẫn còn chậm chủ yếu là những câu thật sự cần synthesis qua Ollama, không còn là do tầng retrieval/prompt cồng kềnh như trước.

---

## Entry: 2026-04-17 22:00:31 +0700

### Trạng thái
- Sửa regression của QA ở nhánh `extractive_fast`: câu hỏi về nhân sự/chức danh công ty có thể bị cắt sai theo dấu `:` rồi trả nhầm một câu mô tả chung.

### Đã sửa
- File: `services/qa_service.py`
  - cập nhật `_extract_answer_from_contexts(...)`
  - bỏ tách câu theo `:\s+` để không làm vỡ các mẫu như:
    - `Chủ Tịch: Nguyễn Quang Hưng`
    - `Tổng Giám Đốc: Nguyễn Văn Toàn`
  - thêm nhận diện `role/person question` cho các mẫu:
    - `chủ tịch`
    - `tổng giám đốc`
    - `giám đốc`
    - `ceo`
    - `chairman`
    - `president`
  - nếu tìm được cụm role trực tiếp trong chunk thì trả ngay đoạn đó
  - nếu câu hỏi dạng `... là ai` nhưng không có câu chứa đúng role tương ứng thì fallback, không được trả câu mô tả chung chung

### Đã kiểm tra
- `python3 -m py_compile services/qa_service.py`
- Smoke test:
  - `chủ tịch công ty là ai` -> `Chủ Tịch: Nguyễn Quang Hưng.`
  - `ceo công ty là ai` -> fallback
  - `trưởng phòng nhân sự là ai` -> fallback

### Kết quả
- QA không còn trả nhầm kiểu mô tả thiết bị/giải pháp cho câu hỏi nhân sự công ty.
- Các câu hỏi về chức danh chỉ được trả lời khi có đúng bằng chứng trong tài liệu.

---

## Entry: 2026-04-21 10:54:30 +0700

### Trạng thái
- Vá 2 điểm chất lượng ưu tiên của Q&A/RAG:
  - siết retrieval + fallback
  - chặn FAQ leakage vào nhánh `rag`

### Đã sửa
- File: `services/qa_service.py`

#### 1. Chặn FAQ leakage
- thêm cờ `include_faq_sources` cho `_retrieve_rag(...)`
- khi route không phải `faq`, retrieval sẽ bỏ qua các chunk có:
  - `metadata.source_kind = "faq"`
- áp dụng cho cả:
  - `answer_static_question(...)`
  - `stream_answer_static_question(...)`

#### 2. Siết fallback ngoài domain
- thêm `_is_out_of_domain_question(...)`
- với các câu rõ ràng ngoài phạm vi Bamboo/SSG/sản phẩm như:
  - thời tiết
  - giá vàng
  - thủ đô / capital
  - bóng đá / tỷ số
- hệ thống fallback sớm trước khi retrieval/generate

#### 3. Siết confidence retrieval
- tăng điều kiện tin cậy trong `_has_retrieval_confidence(...)`
- khi không có source filter:
  - yêu cầu `keyword_score` cao hơn
  - yêu cầu `semantic_score` tối thiểu
  - yêu cầu margin top-1/top-2 chặt hơn

#### 4. Thu hẹp `extractive_fast`
- chỉ cho phép `extractive_fast` với nhóm source sản phẩm:
  - `ECOSAVE.txt`
  - `Smart_box.txt`
  - `camera_AI.txt`
  - `inspection_machine.txt`
- đồng thời câu hỏi phải có intent rõ như:
  - `dùng để`
  - `làm gì`
  - `ứng dụng`
  - `có thể`
  - `kiểm tra`
  - `tiết kiệm`

### Sửa dữ liệu eval
- File: `rag/eval/qa_retrieval_eval_cases.json`
  - bỏ tiền tố rác `z`` ở đầu file để JSON parse lại bình thường

### Đã kiểm tra
- `python3 -m py_compile services/qa_service.py routes/qa.py`
- Smoke test:
  - `Hôm nay trời mưa không?` -> fallback
  - `Giá vàng hôm nay bao nhiêu?` -> fallback
  - `Thủ đô của Canada là gì?` -> fallback
  - `Bamboo có hỗ trợ OCR không?` -> route `rag`, source `bamboo.txt`
  - `Smart Box dùng để làm gì trong nhà máy?` -> `extractive_fast`, source `Smart_box.txt`

### Eval sau bản vá
- Bộ eval timeout-safe 40 case:
  - `passed_cases = 33`
  - `failed_cases = 7`
  - `route_accuracy = 1.0`
  - `mode_accuracy = 0.825`
  - `source_hit_rate = 1.0`
  - `fallback_accuracy = 1.0`

### Phần còn lại
- 7 case còn fail đều nằm ở nhóm product RAG do vẫn đi `extractive_fast`:
  - `rag_004`
  - `rag_006`
  - `rag_007`
  - `rag_008`
  - `rag_009`
  - `rag_010`
  - `rag_011`
- Nghĩa là:
  - fallback đã sạch
  - FAQ leakage đã chặn được
  - phần còn phải xử lý tiếp là chất lượng/độ rộng của `extractive_fast`

---

## Entry: 2026-04-21 11:13:49 +0700

### Trạng thái
- Tiếp tục 3 bước theo thứ tự:
  - thu hẹp thêm `extractive_fast`
  - cải thiện `context augmentation`
  - tinh chỉnh nhẹ `generate/model options`

### Đã sửa
- File: `services/qa_service.py`

#### 1. Thu hẹp tiếp `extractive_fast`
- thêm `_classify_question_intent(...)`
  - phân loại: 
    - `factual`
    - `explainer`
    - `listing`
    - `general`
- `extractive_fast` giờ chỉ chạy khi:
  - route là `rag`
  - intent là `factual`
  - có marker factual rõ như:
    - `năm nào`
    - `bao nhiêu`
    - `ở đâu`
    - `là ai`
    - `ceo`
    - `chủ tịch`
  - source filter là nhóm product source
  - top source nằm trong product source
  - chỉ có một source thực sự nổi bật (`same_source`)
  - score / keyword score vượt ngưỡng cao hơn
- kết quả là `extractive_fast` không còn chen vào các câu giải thích sản phẩm, câu Bamboo, hoặc câu công ty chung

#### 2. Cải thiện context augmentation
- thêm `_select_augmented_contexts(...)`
- trước khi build prompt:
  - loại duplicate context
  - giữ chunk tốt nhất đầu tiên
  - với câu `explainer` / `listing`:
    - ưu tiên ghép thêm chunk gần kề cùng source để giữ mạch ý
  - sau đó mới bổ sung thêm source khác nếu còn chỗ
- thêm `_normalize_context_key(...)` để chống lặp chunk gần giống nhau

#### 3. Cải thiện prompt theo intent
- `_build_augmented_prompt(...)` giờ sinh chỉ dẫn khác nhau theo intent:
  - `factual`:
    - trả lời trực tiếp ngay câu đầu
    - giữ nguyên số liệu/tên riêng
  - `explainer`:
    - trả lời theo 2-3 ý ngắn
    - tránh chọn ví dụ quá hẹp
  - `listing`:
    - ưu tiên liệt kê ngắn gọn
    - gom ý cùng nhóm
  - `general`:
    - trả lời ngắn gọn, trực tiếp

#### 4. Tinh chỉnh generate/model options
- thêm các option generate có kiểm soát:
  - `QA_GENERATE_NUM_PREDICT`
  - `QA_GENERATE_TOP_P`
  - `QA_GENERATE_REPEAT_PENALTY`
- áp dụng cho cả:
  - `_call_ollama_generate(...)`
  - `_iter_ollama_generate_chunks(...)`
- mục tiêu:
  - giảm lan man
  - giảm lặp
  - giữ answer ngắn hơn và ổn định hơn

### Đã kiểm tra
- `python3 -m py_compile services/qa_service.py routes/qa.py`
- Test tay các câu trước đây fail ở nhóm product:
  - `EcoSave giúp tiết kiệm điện như thế nào?` -> `rag`
  - `Smart Box dùng để làm gì trong nhà máy?` -> `rag`
  - `Smart Box có thể thu thập những loại dữ liệu nào?` -> `rag`
  - `Camera AI của SSG có thể ứng dụng vào đâu?` -> `rag`
  - `Inspection Machine có thể kiểm tra những gì?` -> `rag`
  - `Sao Mai Solution Group được thành lập năm nào?` -> `extractive_fast`

### Eval sau đợt tinh chỉnh
- Bộ eval timeout-safe 40 case:
  - `passed_cases = 40`
  - `failed_cases = 0`
  - `route_accuracy = 1.0`
  - `mode_accuracy = 1.0`
  - `source_hit_rate = 1.0`
  - `fallback_accuracy = 1.0`

### Kết quả
- `fallback` đã sạch
- `FAQ leakage` đã chặn
- `extractive_fast` chỉ còn dùng ở phạm vi rất hẹp
- nhóm câu sản phẩm giải thích dài đã chuyển sang `rag` đúng hơn
- prompt augmentation có chọn lọc context theo intent thay vì đẩy thẳng top-k thô

---

## Entry: 2026-04-21 18:35:45 +0700

### Trạng thái
- Đổi model generate của Q&A/RAG sang `qwen3:14b`.

### Đã sửa
- File: `.env`
  - thêm:
    - `QA_GENERATE_MODEL=qwen3:14b`

- File: `start_app.sh`
  - đổi default:
    - từ `llama3:latest`
    - sang `qwen3:14b`

- File: `services/qa_service.py`
  - đưa `qwen3:14b` lên đầu `GENERATE_MODEL_CANDIDATES`
  - mục tiêu:
    - nếu chạy không qua `.env`
    - hoặc cần fallback detect model
    - hệ thống vẫn ưu tiên `qwen3:14b`

### Đã kiểm tra
- `python3 -m py_compile services/qa_service.py`
- import runtime với `QA_GENERATE_MODEL=qwen3:14b`:
  - `QA_GENERATE_MODEL` resolve đúng thành `qwen3:14b`

### Lưu ý
- Tại thời điểm đổi cấu hình, `ollama list` trên máy vẫn chưa có `qwen3:14b`.
- Khi chạy `start_app.sh`, script sẽ tự kiểm tra model QA generate và pull nếu thiếu.

---

## Entry: 2026-04-21 20:03:30 +0700

### Trạng thái
- Đo nhanh so sánh `llama3:latest` và `qwen3:14b` trên cùng bộ 5 câu hỏi Q&A/RAG.

### Bộ câu hỏi benchmark
- `EcoSave giúp tiết kiệm điện như thế nào?`
- `Smart Box dùng để làm gì trong nhà máy?`
- `Camera AI của SSG có thể ứng dụng vào đâu?`
- `Bamboo lưu dữ liệu đăng ký ở đâu?`
- `Sao Mai Solution Group được thành lập năm nào?`

### Kết quả `llama3:latest`
- `EcoSave...`
  - mode: `rag`
  - thời gian: `11752ms`
  - nguồn: `ECOSAVE.txt`
- `Smart Box...`
  - mode: `rag`
  - thời gian: `6331ms`
  - nguồn: `Smart_box.txt`
- `Camera AI...`
  - mode: `rag`
  - thời gian: `8121ms`
  - nguồn: `camera_AI.txt`
- `Bamboo lưu dữ liệu...`
  - mode: `rag`
  - thời gian: `3197ms`
  - nguồn: `bamboo.txt`
- `Sao Mai Solution Group...`
  - mode: `rag`
  - thời gian: `3364ms`
  - nguồn: `RAG_saomai1.txt`, `RAG_saomai2.txt`

### Kết quả `qwen3:14b`
- Model đã được pull thành công bằng `ollama pull qwen3:14b`.
- `EcoSave...`
  - mode: `extractive`
  - thời gian: `25082ms`
  - nguồn: rỗng
- `Smart Box...`
  - mode: `fallback`
  - thời gian: `23661ms`
- `Camera AI...`
  - mode: `fallback`
  - thời gian: `21887ms`
- `Bamboo lưu dữ liệu...`
  - mode: `fallback`
  - thời gian: `21874ms`
- `Sao Mai Solution Group...`
  - mode: `rag`
  - thời gian: `21678ms`
  - câu trả lời bị cụt: `Sao Mai Solution Group được thành lập vào`

### Kết luận
- Trên máy hiện tại, `qwen3:14b` cho:
  - độ trễ cao hơn rõ rệt
  - nhiều câu fallback sai
  - chất lượng đầu ra kém ổn định hơn `llama3:latest`
- Kết luận thực dụng:
  - chưa nên dùng `qwen3:14b` làm model generate mặc định cho Q&A/RAG trên máy này
  - nếu cần tăng chất lượng, nên benchmark thêm:
    - `qwen3:8b`
    - hoặc giữ `llama3:latest` và tiếp tục tối ưu retrieval / rerank / prompt

---

## Entry: 2026-04-22 12:01:30 +0700

### Trạng thái
- Bổ sung tài liệu sơ đồ luồng RAG 1-2 trang.
- Vá lớp retrieval theo hướng đúng trọng tâm câu hỏi hơn.

### Đã thêm
- File mới: `docs/rag_flow_overview.md`
  - mô tả:
    - nguồn dữ liệu
    - build index
    - router
    - retrieval
    - augmentation
    - generate
    - history
    - TTS

### Đã sửa
- File: `services/qa_service.py`
  - thêm `QUESTION_STOPWORDS`
  - thêm `_question_focus_terms(...)`
  - thêm `_question_focus_phrases(...)`
  - thêm `_focus_alignment_score(...)`
  - thêm `_rerank_retrieved_contexts(...)`
  - đổi `_retrieve_rag(...)`:
    - lấy raw candidates rộng hơn
    - rerank theo `focus_score`
    - sau đó mới cắt về `QA_RAG_TOP_K`
  - đổi `_has_retrieval_confidence(...)`:
    - với câu `explainer/listing`, yêu cầu `focus_score` tối thiểu
  - đổi `_select_augmented_contexts(...)`:
    - rerank lại theo trọng tâm trước khi chọn context đưa vào prompt

### Mục tiêu kỹ thuật
- Giảm tình trạng:
  - đúng file nguồn nhưng lấy sai đoạn
  - đúng chủ đề nhưng lệch trọng tâm câu hỏi
- Giữ nguyên router hiện tại, chỉ vá lớp retrieval / augmentation để ít rủi ro hơn

### Kiểm tra nhanh
- `python3 -m py_compile services/qa_service.py routes/qa.py`
- Kiểm tra retrieve top-k với `llama3:latest`:
  - `Smart Box dùng để làm gì trong nhà máy?`
    - top chunks đều ở `Smart_box.txt`
    - `focus_score` tăng rõ ở các chunk mô tả công dụng
  - `Camera AI của SSG có thể ứng dụng vào đâu?`
    - top chunks dồn về `camera_AI.txt`
    - ưu tiên các chunk có marker ứng dụng
  - `SSG cung cấp những dịch vụ chính nào?`
    - top chunks dồn về `RAG_saomai1.txt`, `RAG_saomai2.txt`
    - ưu tiên chunk có nội dung dịch vụ

### Kiểm tra answer nhanh
- `Smart Box dùng để làm gì trong nhà máy?`
  - mode: `rag`
  - source: `Smart_box.txt`
  - answer bám vào công dụng hơn trước
- `Camera AI của SSG có thể ứng dụng vào đâu?`
  - mode: `rag`
  - source: `camera_AI.txt`
  - answer bám nhóm ứng dụng thay vì trôi sang mô tả chung
- `Nhà máy thông minh của SSG gồm những thành phần nào?`
  - mode: `rag`
  - source: `RAG_saomai2.txt`, `RAG_saomai1.txt`
  - answer ra dạng liệt kê đúng hướng hơn

### Lưu ý
- Full eval 40 câu với `llama3:latest` vẫn đang chậm do thời gian generate cao ở một số câu, nên đợt này mới chốt bằng kiểm tra retrieval top-k và câu trả lời trọng điểm.

---

## Entry: 2026-04-22 13:34:00 +0700

### Trạng thái
- Trả model generate của nhánh RAG/QA về `llama3:latest`.

### Đã sửa
- File: `.env`
  - đổi:
    - `QA_GENERATE_MODEL=qwen3:14b`
    - thành `QA_GENERATE_MODEL=llama3:latest`

- File: `start_app.sh`
  - đổi default:
    - từ `qwen3:14b`
    - sang `llama3:latest`

- File: `services/qa_service.py`
  - đổi thứ tự `GENERATE_MODEL_CANDIDATES`
  - đưa `llama3:latest` lên đầu
  - mục tiêu:
    - nếu không có env override
    - hoặc cần detect model đã cài
    - hệ thống vẫn ưu tiên quay về `llama3:latest`

### Đã kiểm tra
- `python3 -m py_compile services/qa_service.py`
- import runtime:
  - `QA_GENERATE_MODEL` resolve đúng thành `llama3:latest`
  - `GENERATE_MODEL_CANDIDATES` bắt đầu bằng `llama3:latest`

## 2026-04-23 10:58:00 +0700
- Vá lỗi retrieval lệch trọng tâm với câu overview như `thông tin về inspection`.
- Thêm `OVERVIEW_QUESTION_MARKERS`, cho `inspection` map thẳng sang `inspection_machine`, và tăng điểm cho chunk giới thiệu/tổng quan; đồng thời phạt chunk nặng danh sách nút điều khiển khi câu hỏi mang tính giới thiệu.
- Sau vá, truy vấn `thông tin về inspection` đổi top retrieval sang `inspection_machine.txt` chunk 0 (Giới thiệu chung) thay vì chunk danh sách nút.
## 2026-04-23 13:42:30 +0700
Node liên quan:
- `6.2.1`
- `6.3.1`
- `7.2`
- Tách nhánh safe-answer cho 2 nguồn yêu cầu độ chính xác cao.
- `giao_tiep_co_ban.txt`: thêm `faq_exact` bằng exact-match theo normalized question, trả thẳng câu trả lời đã duyệt trước khi vào retrieval/generate.
- `RAG_saomai1.txt`: thêm `saomai_fact_safe` cho các câu factual như chủ tịch, tổng giám đốc, năm thành lập, nhân sự, dự án, điện thoại, email, địa chỉ, website; trả template answer trực tiếp từ regex trên nguồn gốc.
- Đổi version answer cache sang `safe-v1` để vô hiệu hóa các câu trả lời cũ còn nằm trong cache.
## 2026-04-23 14:25:30 +0700
Node liên quan:
- `3.1`
- `3.4`
- `3.5`
- `6.6.1`
- `7.3.1`
- Vá lỗi follow-up mơ hồ của RAG như `chi tiết hơn về quy mô`.
- Thêm lấy ngữ cảnh phiên QA gần nhất theo `session_key` từ bảng `qa_history`, truyền vào service để rewrite follow-up ngắn theo chủ thể của lượt trước.
- Nếu câu hỏi mơ hồ nhưng không suy ra được chủ thể, trả `clarification` thay vì ném vào retrieval và trả lời bừa.
- Thêm hậu kiểm chặn prompt leakage (`Literal translation`, `Note:`, `Since the context is...`). Nếu phát hiện, thay bằng extractive/clarification sạch.
- Tách answer cache theo `session context subject` để tránh cùng một câu mơ hồ ăn lại cache của chủ thể khác.
## 2026-04-23 16:03:30 +0700
Node liên quan:
- `1.3`
- `4.1.4`
- Chuẩn hóa corpus ở mức ingest/chunk metadata thay vì chỉ để tài liệu text thuần.
- Thêm phân loại section cho từng block/chunk: `facts`, `overview`, `use_cases`, `faq`, `controls`, `general`.
- `search_text` của mỗi chunk giờ mang thêm nhãn loại nội dung; metadata chunk lưu thêm `section_kind`.
- Retrieval được bổ sung `section_bonus` để ưu tiên đúng loại đoạn theo câu hỏi: factual ưu tiên `facts`, hỏi tổng quan ưu tiên `overview`, hỏi ứng dụng ưu tiên `use_cases`, hỏi cách dùng/hướng dẫn ưu tiên `controls`.
- Rebuild lại RAG index sau thay đổi để metadata section có hiệu lực.
## 2026-04-23 17:54:30 +0700
Node liên quan:
- `3.1`
- `3.2`
- `3.3`
- `3.4`
- Mở rộng `query rewriting + follow-up memory` trong QA service.
- Follow-up không còn chỉ xử lý `chi tiết hơn`, mà thêm các mẫu mơ hồ như `nó`, `cái đó`, `còn cái này`, `cụ thể hơn`, `thế còn`, đồng thời suy ra `subject` và `intent` từ phiên hỏi đáp gần nhất.
- Bổ sung rewrite theo intent: overview, use_cases, controls, how_it_works, benefits, functions.
- Với subject là công ty (Sao Mai/SSG), follow-up kiểu `cụ thể hơn` + intent functions được rewrite sang `dịch vụ và giải pháp chính` thay vì `chức năng`, tránh va vào project rule của Bamboo kiosk.
- Tách answer cache theo `subject|intent` của session context để cùng một câu follow-up ngắn không ăn nhầm cache của chủ thể khác.
## 2026-04-23 19:09:30 +0700
Node liên quan:
- `3.3.1`
- `3.4.3`
- Sửa lỗi follow-up memory ghi đè sai chủ thể mới.
- Xác minh bằng test: `_detect_source_filters()` đã nhận ra `inspection_machine` nhưng `_rewrite_question_with_session_context()` vẫn bám chủ thể cũ từ session (`Camera AI`).
- Bản vá: thêm `_extract_explicit_subject_from_question()`, ưu tiên chủ thể hiện diện trong câu hỏi mới trước khi dùng session subject. Vì vậy các câu như `thông tin về inspection` hoặc `tôi hỏi về thông tin inspection cơ mà` sẽ rewrite sang `Inspection Machine`, không còn bị kéo về `Camera AI`.
## 2026-04-23 19:58:00 +0700
Node liên quan:
- `3.5`
- `6.6.2`
- `7.3`
- Điều tra lỗi `càng hỏi về sau càng sai` và xác định gốc lỗi nằm ở session memory bị ô nhiễm dần.
- Gốc 1: follow-up rewrite trước đây dùng chủ thể cũ của session ngay cả khi câu mới đã có topic riêng hoặc mang chủ đề mới ngoài domain hiện tại.
- Gốc 2: các answer kiểu `Về đội tester, tôi chưa có đủ thông tin...` không được nhận là fallback, nên vẫn giữ `matched_sources` rác và truyền sang lượt sau.
- Bản vá: thêm `scope clarification` cho câu có topic mới nhưng không có domain anchor; thêm `_is_fallback_like_answer()` để mọi biến thể `không đủ thông tin / liên hệ lễ tân` đều rơi sạch về fallback và xóa sources khỏi memory phiên.
## 2026-04-24 11:49:00 +0700
Node liên quan:
- `2.5`
- `3.3.2`
- `3.3.3`
- `3.5`
- `6.2.1`
- Sửa lỗi gốc ở lớp hiểu câu hỏi: trước đây hệ thống bắt pattern rời rạc nên không gom được `keyword -> subject -> intent`, dẫn tới 3 hiện tượng:
  - câu rỗng chủ thể bị lẫn với câu ngoài domain;
  - session subject cũ bị tái sử dụng quá dễ;
  - câu có chủ thể rõ nhưng lead-in mơ hồ như `tôi muốn hỏi vì sao mai` không được rewrite đúng.
- Bản vá theo hướng tổng quát, không theo từng case:
  - thêm `domain anchor` dựa trên `SOURCE_ALIASES` + focus terms/phrases;
  - chỉ cho `clarification` với câu thật sự rỗng chủ thể;
  - câu không có anchor vào tri thức dự án thì `fallback`, không cho đi RAG để hallucinate;
  - session subject chỉ còn hiệu lực nếu câu hiện tại là follow-up mơ hồ hoặc có độ khớp token đủ mạnh với subject cũ;
  - thêm `generic subject request` để các câu lead-in mơ hồ nhưng có subject rõ được rewrite sang overview đúng chủ thể.
- Kết quả kiểm tra lại chuỗi câu:
  - `câu hỏi`, `Tôi muốn hỏi về` -> `clarification`
  - `Tôi muốn hỏi vì sao mai` -> trả về overview của `Sao Mai Solution Group`
  - `hoa mai`, `Sapa`, `Vietnamobile`, `Bom Bo`, `Vietinbank`, `soi cầu...` -> `fallback`
  - `alo` -> đi `faq_extractive` từ `giao_tiep_co_ban.txt`
## 2026-04-24 11:55:00 +0700
Node liên quan:
- `8.2`
- Tạo tài liệu bản đồ cây RAG có đánh số cố định tại [docs/rag_tree_map.md](/Users/ssg/Documents/bamboo_nissin/docs/rag_tree_map.md).
- Mục đích: từ nay mọi thay đổi RAG sẽ tham chiếu theo node như `2.5`, `3.4.1`, `6.6.2` thay vì chỉ nói chung chung theo file.
