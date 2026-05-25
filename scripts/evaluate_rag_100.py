import json
import time
import requests
import statistics
from concurrent.futures import ThreadPoolExecutor

API_URL = "http://127.0.0.1:5001/api/qa/ask"

QUESTIONS = [
    # Sao Mai / SSG
    "Sao Mai Solution Group là công ty gì?",
    "SSG được thành lập năm nào?",
    "Tổng giám đốc của công ty là ai?",
    "Giám đốc của isg là ai?",
    "Tầm nhìn và sứ mệnh của SSG?",
    "SSG có những giải pháp nào nổi bật?",
    "Đối tác của Sao Mai gồm những ai?",
    "Khách hàng tiêu biểu của SSG?",
    "Công ty Hoa Mai làm về lĩnh vực gì?",
    "Các dự án lớn mà Sao Mai đã thực hiện?",
    "SSG có bao nhiêu nhân sự?",
    "Văn hóa công ty của Sao Mai là gì?",
    "Sao Mai có chứng chỉ ISO nào không?",
    "Năng lực sản xuất của SSG?",
    "Địa chỉ trụ sở của Sao Mai ở đâu?",
    
    # EcoSave / ecosip / eco xếp
    "EcoSave là gì?",
    "Lợi ích của hệ thống EcoSave?",
    "EcoSave giúp tiết kiệm bao nhiêu điện năng?",
    "Nguyên lý hoạt động của EcoSave?",
    "EcoSave áp dụng cho thiết bị nào?",
    "Tôi muốn hướng dẫn về Eco xếp",
    "Cho tôi thông tin về ecosip",
    "eco save hoạt động ra sao?",
    "Cách vận hành hệ thống EcoSave?",
    "Bảo trì hệ thống ecosip như thế nào?",
    "EcoSave có dùng cho máy nén khí không?",
    "Thời gian thu hồi vốn khi dùng EcoSave?",
    "Eco xếp có tự động điều khiển không?",
    "Tại sao nên chọn EcoSave của SSG?",
    "Các thành phần chính của hệ thống EcoSave?",

    # Smart Box
    "Smart Box là gì?",
    "Chức năng chính của Smart Box?",
    "Smart Box thu thập dữ liệu như thế nào?",
    "Lợi ích khi lắp đặt Smart Box?",
    "Smart Box hỗ trợ giao thức kết nối nào?",
    "Smart Box có dễ lắp đặt không?",
    "Ứng dụng của Smart Box trong sản xuất?",
    "Smart Box có thể kết nối với ERP không?",
    "Dữ liệu từ Smart Box được lưu trữ ở đâu?",
    "Smart Box có hoạt động offline không?",
    "Thiết lập cảnh báo trên Smart Box thế nào?",
    "Màn hình của Smart Box hiển thị gì?",
    "Smart Box có tính năng truy xuất nguồn gốc không?",
    "Cần bảo trì Smart Box bao lâu một lần?",
    "Thông số kỹ thuật của Smart Box?",

    # Camera AI / Machine Vision
    "Camera AI là giải pháp gì?",
    "Machine Vision của SSG có điểm gì nổi bật?",
    "Camera AI của hoa mai dùng để làm gì?",
    "Camera AI có thể phát hiện lỗi nào?",
    "Hệ thống Camera AI có cần ánh sáng đặc biệt không?",
    "Tốc độ xử lý của Camera AI là bao nhiêu?",
    "Machine vision có thay thế con người được không?",
    "Camera AI có thể đếm sản phẩm không?",
    "Camera AI kết hợp với robot được không?",
    "Làm sao để dạy AI nhận diện lỗi mới?",
    "Độ chính xác của Camera AI?",
    "Camera AI có dùng trong y tế được không?",
    "Giải pháp Camera AI cần phần cứng gì?",
    "Tôi muốn xem demo Camera AI",
    "Camera AI lưu trữ video trong bao lâu?",

    # Bamboo Kiosk / kiot
    "Bamboo Kiosk là gì?",
    "Chức năng của Bamboo Kiosk?",
    "Tôi muốn hướng dẫn về Bamboo kiot",
    "Bamboo Kiosk dùng để check-in được không?",
    "Bamboo Kiosk có nhận diện khuôn mặt không?",
    "Hệ thống Bamboo Kiosk có hỗ trợ giọng nói không?",
    "Kiot của Sao Mai có những tính năng gì?",
    "Dashboard của Bamboo quản lý những gì?",
    "Bamboo Kiosk có tự động in thẻ không?",
    "Làm sao để đặt lịch hẹn qua Bamboo?",
    "Quy trình đăng ký khách trên Bamboo Kiosk?",
    "Bamboo Kiosk có bảo mật thông tin không?",
    "Voice command trên Bamboo hoạt động thế nào?",
    "Bamboo Kiosk có kết nối với barrier không?",
    "Ai là người thiết kế hệ thống Bamboo?",

    # Inspection Machine
    "Inspection Machine là máy gì?",
    "Chức năng của Inspection Machine?",
    "Tôi muốn hướng dẫn về inspection machine",
    "Các nút bấm trên Inspection Machine?",
    "Nút Emergency STOP dùng làm gì?",
    "Làm sao để đổi model trên Inspection Machine?",
    "Quy trình vận hành Inspection Machine?",
    "Máy inspection của Sao Mai kiểm tra gì?",
    "Lỗi thường gặp trên Inspection Machine?",
    "Cách vệ sinh Inspection Machine?",
    "Bao lâu cần bảo dưỡng Inspection Machine?",
    "Inspection Machine có tự động phân loại sản phẩm không?",
    "Thông số của Inspection Machine?",
    "Máy inspection có xuất báo cáo không?",
    "Làm sao để reset Inspection Machine?",

    # Small Talk & Meta
    "Xin chào",
    "Bạn là ai?",
    "Bạn tên gì?",
    "Bạn có thể giúp gì cho tôi?",
    "Bạn biết những giải pháp nào?",
    "Cảm ơn bạn",
    "Tạm biệt",
    "Thôi được rồi",

    # Unrelated / Fallback testing
    "Thời tiết hôm nay thế nào?",
    "Cách nấu món phở bò?",
]

def run_test(question):
    start = time.perf_counter()
    try:
        resp = requests.post(API_URL, json={"question": question, "language": "vi", "channel": "kiosk"}, timeout=30)
        data = resp.json()
        end = time.perf_counter()
        
        if data.get("ok"):
            ans = data["item"]["answer"]
            used_fallback = data["item"]["used_fallback"]
            mode = data["item"]["answer_mode"]
            return {
                "question": question,
                "answer": ans,
                "latency": end - start,
                "used_fallback": used_fallback,
                "mode": mode,
                "error": None
            }
        else:
            return {
                "question": question,
                "error": data.get("error", "Unknown API Error"),
                "latency": end - start
            }
    except Exception as e:
        end = time.perf_counter()
        return {
            "question": question,
            "error": str(e),
            "latency": end - start
        }

if __name__ == "__main__":
    print(f"Bắt đầu test {len(QUESTIONS)} câu hỏi...")
    results = []
    
    # Run sequentially to not overload local Ollama completely, 
    # but we can do a very small concurrency like max_workers=2
    with ThreadPoolExecutor(max_workers=2) as executor:
        for res in executor.map(run_test, QUESTIONS):
            results.append(res)
            print(f"Done: {res['question'][:30]}... -> {res['latency']:.2f}s")
            
    with open("rag_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("Hoàn thành! Kết quả đã lưu vào rag_test_results.json")
