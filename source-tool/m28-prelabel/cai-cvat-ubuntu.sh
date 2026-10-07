#!/usr/bin/env bash
# Cài CVAT v2.77.0 trên Ubuntu (Docker Engine gốc, không WSL), theo de-tai-m28/huong-dan-chung.md mục "Cài CVAT trên máy mình".
# Cần mật khẩu sudo một lần. Không tạo tài khoản admin và không đụng token (làm tay sau, xem cuối file).
# Chạy: bash cai-cvat-ubuntu.sh        Cài vào ~/cvat, CVAT chỉ mở ở http://localhost:8080 (127.0.0.1).
set -euo pipefail
CVAT_DIR="$HOME/cvat"
CVAT_TAG="v2.77.0"

echo "=== 1/5 Cài Docker Engine (cần sudo) ==="
sudo apt-get update || true      # một mirror/nguồn lỗi chỉ báo cảnh báo, không dừng
sudo apt-get install -y ca-certificates curl
if ! command -v docker >/dev/null 2>&1; then
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
sudo systemctl enable --now docker
command -v git >/dev/null 2>&1 || sudo apt-get install -y git || echo "(không cài được git: sẽ tải CVAT bằng curl)"
sudo usermod -aG docker "$USER"
D="sg docker -c"      # nhóm docker chưa có hiệu lực trong phiên này: chạy lệnh docker qua sg

echo "=== 2/5 Tải CVAT $CVAT_TAG vào $CVAT_DIR ==="
if [ ! -d "$CVAT_DIR" ]; then
  if command -v git >/dev/null 2>&1; then
    git clone --branch "$CVAT_TAG" --depth 1 https://github.com/cvat-ai/cvat "$CVAT_DIR"
  else
    mkdir -p "$CVAT_DIR"
    curl -fL "https://github.com/cvat-ai/cvat/archive/refs/tags/$CVAT_TAG.tar.gz" | tar -xz --strip-components=1 -C "$CVAT_DIR"
  fi
fi
cd "$CVAT_DIR"
if [ -d .git ]; then echo "Bản: $(git describe --tags)   (phải là $CVAT_TAG)"; else echo "Bản: $CVAT_TAG (tải bằng curl, không có git)"; fi
[ -z "${CVAT_VERSION:-}" ] || { echo "Biến CVAT_VERSION đang đặt (${CVAT_VERSION}): bỏ nó đi (unset CVAT_VERSION) rồi chạy lại."; exit 1; }

echo "=== 3/5 Chỉ máy này vào được CVAT (127.0.0.1:8080) ==="
cat > docker-compose.override.yml <<'EOF'
services:
  traefik:
    ports: !override
      - "127.0.0.1:8080:8080"
EOF

echo "=== 4/5 Chạy CVAT (lần đầu tải khoảng 1,5 GB, vài phút) ==="
$D "docker compose up -d"

echo "=== 5/5 Chờ CVAT sẵn sàng ==="
for i in $(seq 1 60); do
  if curl -fs http://localhost:8080/api/server/about 2>/dev/null | grep -q '"version"'; then break; fi
  sleep 5
done
curl -s http://localhost:8080/api/server/about; echo
$D "docker exec -t cvat_server python manage.py health_check" || true

cat <<'EOF'

Xong phần cài. Việc còn lại làm TAY (có mật khẩu/token, không để Claude làm):
  1. Tạo tài khoản admin:  docker exec -it cvat_server bash -ic 'python3 ~/manage.py createsuperuser'
     (nhóm docker chỉ có hiệu lực sau khi đăng xuất/đăng nhập lại Ubuntu; trước đó thêm "sudo" phía trước, hoặc "sg docker -c '...'")
  2. Mở http://localhost:8080 (gõ localhost, KHÔNG gõ 127.0.0.1) bằng Chrome, đăng nhập, tạo token tên m28-<Pk>, hạn 25/10.
  3. Hằng ngày:  cd ~/cvat && docker compose start   /   docker compose stop
     KHÔNG chạy "docker compose down -v" trước 24/10 (xoá hết nhãn).
EOF
