#!/bin/bash
# scripts/kiosk_startup.sh
# Tự động khởi chạy hệ thống Bamboo Kiosk và mở trình duyệt Chrome

# Đường dẫn tuyệt đối đến thư mục dự án
ROOT_DIR="/Users/ssg/Documents/bamboo_nissin"
CHROME_PROFILE_DIR="$HOME/Library/Application Support/BambooNissin/chrome_kiosk_profile"
cd "$ROOT_DIR"

# Dùng profile cố định để Chrome giữ lại quyền camera/micro theo site sau khi reboot.
mkdir -p "$CHROME_PROFILE_DIR"

# 1. Khởi chạy toàn bộ backend (Flask, Ollama, Redis, Workers)
# Chạy trong background để script tiếp tục thực hiện lệnh mở trình duyệt
bash start_app.sh &

# 2. Chờ cho đến khi server Flask sẵn sàng (port 5001)
echo "Đang chờ hệ thống khởi động..."
until curl -s http://127.0.0.1:5001/ > /dev/null; do
  sleep 2
done

# 3. Mở Google Chrome ở chế độ Kiosk (toàn màn hình, không thanh công cụ)
# Lưu ý: Đảm bảo đường dẫn Chrome đúng với hệ thống Mac của bạn
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --kiosk \
  --app=http://127.0.0.1:5001/ \
  --no-first-run \
  --no-default-browser-check \
  --user-data-dir="$CHROME_PROFILE_DIR" &
