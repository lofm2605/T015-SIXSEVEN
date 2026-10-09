#!/usr/bin/env bash
# M28 - một file để chạy trên Ubuntu: cài môi trường (lần đầu), tải model, mở trang rà soát.
# Bản Ubuntu của chay.bat. Chạy: ./chay.sh   (hoặc bash chay.sh nếu chưa có quyền chạy: chmod +x chay.sh)
cd "$(dirname "$(readlink -f "$0")")" || exit 1
export PYTHONUTF8=1
MODEL_URL="https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

loi() {
  echo
  echo "Có lỗi ở trên. Đọc thông báo, sửa rồi chạy lại. Nếu không rõ, gửi P1: bản Ubuntu (lsb_release -a), python3 --version,"
  echo "và nội dung cửa sổ này (không gửi ảnh mặt hay token)."
  exit 1
}

tim_python() {
  for v in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$v" >/dev/null 2>&1; then PYV="$v"; return 0; fi
  done
  return 1
}

cai_moi_truong() {
  echo
  echo "=== Cài môi trường Python lần đầu (vài phút, cần mạng) ==="
  tim_python || { echo "Không tìm thấy Python 3. Cài: sudo apt install python3 python3-venv python3-pip"; return 1; }
  echo "Dùng $PYV ($($PYV --version 2>&1))"
  if ! "$PYV" -c "import ensurepip, venv" >/dev/null 2>&1; then
    echo "Thiếu gói venv của Python. Cài: sudo apt install python3-venv python3-pip   (đúng phiên bản, ví dụ python3.12-venv), rồi chạy lại."
    return 1
  fi
  "$PYV" -m venv .venv || return 1
  # shellcheck disable=SC1091
  . .venv/bin/activate
  python -m pip install --upgrade pip || return 1
  # bỏ torch/torchvision (chỉ để so sánh nội bộ, nặng, không cần để chạy m28)
  REQ="$(mktemp)"
  grep -v -i "torch" requirements.txt > "$REQ"
  python -m pip install -r "$REQ"; RC=$?
  rm -f "$REQ"
  [ "$RC" -eq 0 ] || return 1
  python -m pip install -r requirements-ui.txt || return 1
  if ! python -c "import mediapipe as mp; print('mediapipe', mp.__version__)"; then
    echo "mediapipe không import được: thử Python khác (python3.12), xoá .venv rồi chạy lại (menu mục 6)."
    return 1
  fi
  return 0
}

[ -x ".venv/bin/python" ] || cai_moi_truong || loi
# shellcheck disable=SC1091
. .venv/bin/activate

if [ ! -f face_landmarker.task ] && [ ! -f tool/face_landmarker.task ]; then
  echo
  echo "Chưa có face_landmarker.task, đang tải (khoảng 4 MB)..."
  if ! curl -L -f -o face_landmarker.task "$MODEL_URL"; then
    rm -f face_landmarker.task
    echo
    echo "Không tải được model. Tải tay file này rồi đặt tên face_landmarker.task cạnh chay.sh:"
    echo "$MODEL_URL"
    loi
  fi
fi

hoi_nguoi() {
  read -r -p "Tên người rà (P1-P5, Enter = P1): " NGUOI
  NGUOI="${NGUOI:-P1}"
}

mo_trang() {
  hoi_nguoi
  echo
  echo 'Đang mở trang rà soát (chỉ máy này vào được, địa chỉ http://127.0.0.1:7860). Xong việc bấm "Close page" trên trang.'
  python tool/review_app.py --nap "$NGUOI"
}

luot() {
  hoi_nguoi
  read -r -p "Tên lượt (thư mục trong runs/, ví dụ F5 hoặc NAP_001): " LUOT
  [ -n "$LUOT" ] || return 0
  if [ ! -d "runs/$LUOT" ]; then echo "Không thấy runs/$LUOT"; return 0; fi
  python tool/review_app.py "runs/$LUOT" "$NGUOI"
}

thu5() {
  if [ ! -f data/manifest.csv ]; then
    echo "Chưa có data/manifest.csv: giải nén gói dữ liệu in-cabin (m28_incab_part*.zip) vào thư mục data/ trước."
    return 0
  fi
  if [ ! -f data/crops/F_001.png ]; then
    echo "Chưa có data/crops/: giải nén đủ các phần m28_incab_part*.zip vào thư mục data/ trước."
    return 0
  fi
  python -c "import csv;r=[x for x in csv.DictReader(open('data/manifest.csv',encoding='utf-8')) if x['set']=='F'][:5];w=csv.writer(open('data/f5_list.csv','w',newline=''));w.writerow(['image','face_idx','seed']);[w.writerow([x['image'],x['face_idx'],x['seed']]) for x in r]"
  python tool/m28.py all --run F5 --list data/f5_list.csv --images data/crops --box crop --review auto --dry-run
  echo
  echo 'Nếu thấy "Chạy thử (--dry-run)" là đúng. Kết quả: runs/F5/xml/prelabel.xml'
}

smoke() {
  echo
  echo "=== Kiểm tra nhanh CVAT ==="
  echo "Cần CVAT đang chạy (docker compose up -d) và token ở tab Cài đặt (bật Nhớ trên máy này)"
  echo "hoặc biến môi trường CVAT_URL, CVAT_ACCESS_TOKEN trong cửa sổ này. Script tạo rồi xoá task demo-smoke (4 ảnh xám giả, không phải ảnh mặt)"
  echo "trong project m28; nếu chưa có project m28 thì tạo rồi xoá lại khi còn trống. Không đụng task khác."
  read -r -p "Chạy kiểm tra nhanh? (c = có, k = không): " TL
  case "$TL" in c|C) ;; *) return 0 ;; esac
  python tool/cvat_smoke.py
  MA=$?
  echo
  echo "Mã thoát: $MA"
  [ "$MA" -eq 0 ] || echo "Có bước HỎNG hoặc lỗi: gửi P4 file runs/_smoke/bao_cao_GIO.txt (không gửi token, không gửi ảnh)."
  read -r -p "Enter để về menu..." _
}

chay_test() {
  python -m pip show pytest >/dev/null 2>&1 || python -m pip install pytest
  python -m pytest tests -q
}

cai_lai() {
  read -r -p "Xoá .venv và cài lại từ đầu? (c = có, k = không): " TL
  case "$TL" in c|C) ;; *) return 0 ;; esac
  deactivate 2>/dev/null
  rm -rf .venv
  cai_moi_truong || loi
  # shellcheck disable=SC1091
  . .venv/bin/activate
}

while true; do
  echo
  echo "================= M28 - Nhãn nháp landmark khuôn mặt ================="
  echo "  1. Mở trang rà soát   (Nạp ảnh kéo thả, Các đợt, Ca khó, Thống kê, Cài đặt)"
  echo "  2. Rà lại một lượt có sẵn"
  echo "  3. Chạy thử 5 mặt F in-cabin (chỉ cần gói dữ liệu giải nén vào data/)"
  echo "  4. Kiểm tra nhanh CVAT   (tạo rồi xoá task demo-smoke, cần CVAT đang chạy)"
  echo "  5. Chạy test"
  echo "  6. Cài lại môi trường Python"
  echo "  7. Thoát"
  echo "======================================================================"
  read -r -p "Chọn 1-7: " C
  case "$C" in
    1) mo_trang ;;
    2) luot ;;
    3) thu5 ;;
    4) smoke ;;
    5) chay_test ;;
    6) cai_lai ;;
    7) exit 0 ;;
    *) echo "Chọn từ 1 đến 7." ;;
  esac
done
