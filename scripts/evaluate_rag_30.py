import json
import time
import requests

API_URL = "http://127.0.0.1:5001/api/qa/ask"

QUESTIONS = [
    # Sao Mai / SSG
    "Sao Mai Solution Group là công ty gì?",
    "Tổng giám đốc của công ty là ai?",
    "Công ty Hoa Mai làm về lĩnh vực gì?", # typo Hoa Mai
    "Các dự án lớn mà Sao Mai đã thực hiện?",
    "SSG có bao nhiêu nhân sự?",
    
    # EcoSave / ecosip / eco xếp
    "EcoSave là gì?",
    "Tôi muốn hướng dẫn về Eco xếp", # typo Eco xếp
    "Cho tôi thông tin về ecosip", # typo ecosip
    "Thời gian thu hồi vốn khi dùng EcoSave?",
    "Tại sao nên chọn EcoSave của SSG?",

    # Smart Box
    "Smart Box là gì?",
    "Smart Box thu thập dữ liệu như thế nào?",
    "Lợi ích khi lắp đặt Smart Box?",
    "Smart Box có hoạt động offline không?",
    "Sờ mát bốc dùng để làm gì?", # typo Sờ mát bốc (unmapped, should fallback or struggle)

    # Camera AI / Machine Vision
    "Camera AI là giải pháp gì?",
    "Camera AI của hoa mai dùng để làm gì?", # typo Hoa Mai
    "Camera AI kết hợp với robot được không?",
    "Tôi muốn xem demo Camera AI",
    "Camera AI lưu trữ video trong bao lâu?",

    # Bamboo Kiosk / kiot
    "Bamboo Kiosk là gì?",
    "Tôi muốn hướng dẫn về Bamboo kiot", # typo kiot
    "Bamboo Kiosk có nhận diện khuôn mặt không?",
    "Làm sao để đặt lịch hẹn qua Bamboo?",
    "Quy trình đăng ký khách trên Bamboo Kiosk?",

    # Inspection Machine
    "Inspection Machine là máy gì?",
    "Tôi muốn hướng dẫn về inspection machine",
    "Máy inspection của Sao Mai kiểm tra gì?",
    
    # Unrelated
    "Cách nấu món phở bò?",
    "Tỉ số trận bóng đá hôm nay?",
]

def run_tests():
    print(f"Bắt đầu test {len(QUESTIONS)} câu hỏi...")
    results = []
    
    success_count = 0
    fallback_count = 0
    error_count = 0
    total_time = 0
    
    for i, q in enumerate(QUESTIONS):
        start = time.perf_counter()
        try:
            resp = requests.post(API_URL, json={"question": q, "language": "vi", "channel": "kiosk"}, timeout=60)
            data = resp.json()
            end = time.perf_counter()
            lat = end - start
            total_time += lat
            
            if data.get("ok"):
                ans = data["item"]["answer"]
                used_fallback = data["item"]["used_fallback"]
                
                if used_fallback:
                    fallback_count += 1
                    print(f"[{i+1}/30] FALLBACK: '{q}' ({lat:.2f}s)")
                else:
                    success_count += 1
                    print(f"[{i+1}/30] SUCCESS: '{q}' ({lat:.2f}s)")
                
                results.append({"question": q, "answer": ans, "latency": lat, "fallback": used_fallback})
            else:
                error_count += 1
                print(f"[{i+1}/30] ERROR: '{q}'")
        except Exception as e:
            error_count += 1
            print(f"[{i+1}/30] EXCEPTION: '{q}' - {str(e)}")
            
    print("\n" + "="*40)
    print("BÁO CÁO KẾT QUẢ RAG V2 (30 Câu hỏi Đại diện)")
    print("="*40)
    print(f"Tổng số câu hỏi: {len(QUESTIONS)}")
    print(f"Thành công (Trả lời được): {success_count} ({success_count/len(QUESTIONS)*100:.1f}%)")
    print(f"Fallback (Từ chối trả lời): {fallback_count} ({fallback_count/len(QUESTIONS)*100:.1f}%)")
    print(f"Lỗi hệ thống: {error_count} ({error_count/len(QUESTIONS)*100:.1f}%)")
    print(f"Thời gian phản hồi trung bình: {total_time/len(QUESTIONS):.2f}s")
    
    with open("rag_report_30.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_tests()
