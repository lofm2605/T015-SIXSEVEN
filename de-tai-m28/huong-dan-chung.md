# Hướng dẫn chung cho cả nhóm

Thuật ngữ: xem bảng cuối tab.

## Cách dùng tab cá nhân

- Mỗi người một tab (P1 … P5), chia theo buổi 5–24/10.
- Mỗi dòng việc ghi: nơi chạy (Máy mình / Colab / Kaggle / CVAT), file đầu ra, dấu hiệu xong.
- Xong thì tích ô. Chưa xong thì báo lý do trong nhóm chat.
- Cần file của bạn khác: xem ngày giao trong tab bạn đó.

## Nhịp một buổi tối (120 phút) và Chủ nhật

| Phút | Làm gì | Xong khi |
| --- | --- | --- |
| 0–5 | `git pull`, đọc dòng việc hôm nay | Biết file đầu ra cần có |
| 5–60 | Việc đầu tiên trong tab của bạn. Buổi gán CVAT, khối bấm giờ và việc bạn khác chờ trong tối nay luôn làm ở đây | File đầu ra nằm đúng thư mục |
| 60–65 | Nghỉ: đứng dậy, uống nước | — |
| 65–115 | Việc ghi "(giờ thứ hai)" trong tab, hoặc làm tiếp việc đầu | File đầu ra nằm đúng thư mục |
| 115–120 | Commit, `git push`, báo nhóm chat | Có tin báo |

Mẫu tin báo: `P3 – 6/10 – Xong: data/gt50.json. Vướng: không. Buổi sau: khớp MediaPipe → 50.`

- Buổi gán CVAT: hết khối thì chạy `python tool\export.py <task> <Pk> <ngày>` (xuất chỉ nhãn từ CVAT trên máy bạn vào `raw/`, kèm file `.txt` ghi giờ tạo task), chạy các lệnh git mà script in ra (add, commit, `git pull --rebase --autostash`, push), rồi báo số mặt đã xong. Mất khoảng 5–8 phút; làm ngay trong tối đó, trước việc khác.
- Số phút ghi trong tab đã gồm pull và commit; cộng 5 phút nghỉ, mỗi buổi không quá 120 phút. Thấy sắp quá thì báo P5 để dời việc, đừng thức khuya.
- Việc bạn khác chờ trong cùng tối luôn nằm ở đầu buổi; việc dùng file bạn khác làm trong cùng tối luôn nằm ở phần sau.
- CN 11/10 và CN 18/10: cả nhóm làm cùng một khung 2 tiếng do P5 hẹn trước (đề xuất 9:00–11:00), vì có buổi gặp mentor và việc nối nhau. Phần không có việc là dự phòng cho việc trễ.
- Buổi bấm giờ (P1, P5 ngày 9–10/10; cả nhóm 13, 14, 15/10): đầu buổi đọc câu chung: "Làm theo nhịp bình thường; mặt xong khi mọi điểm đúng quy tắc."
- Buổi có khối bấm giờ (14–15/10): làm khối đó ngay đầu buổi, khi còn tỉnh. Phần sau hai tối này chỉ viết code hoặc chữ; không mở trang rà soát, task `demo-…` hay ảnh chồng có nhãn nháp.
- Mở cmd trên Máy mình, chạy `python facetimer.py <Pk> <manual|assisted> <task> <job> <khối> <seq cuối>`. `<job>` là số job trên CVAT của bạn (số sau `/jobs/` trên thanh địa chỉ; mỗi máy một số khác, chỉ để ghi chú). Ví dụ 14/10 của P1: `python facetimer.py P1 manual m28-manual 7 X1 10` (7 là số job ví dụ). Enter = xong mặt, p = tạm dừng. Số cuối là seq của mặt cuối cùng (thường 10, buổi thử 8), không phải số mặt. Buổi 13/10: `python facetimer.py Pk assisted m28-practice <job> D <seq cuối>`. Task practice của bạn chỉ có 4 mặt D của bạn (P1 D\_01–D\_04, P2 D\_05–D\_08, P3 D\_09–D\_12, P4 D\_13–D\_16, P5 D\_17–D\_20). Khi được hỏi seq, gõ số của mặt đầu (ví dụ P2 gõ 5, seq cuối là 8). Mặt thứ tư không có nháp: gõ "tay" trước Enter.
- Ghi đúng chữ `manual` hoặc `assisted`. Script của P5 chỉ đọc hai chữ này.
- Script ghi file `timing_Pk.csv` trên máy bạn. Không mở, không commit file này. Gửi P5 đầu buổi 17/10 (P5 gộp ngay trong tối đó). Riêng P1 gửi phần buổi thử ngày 10/10, ngay sau khối Pb (khoảng phút 60).
- Không xem tổng giờ của buổi 14–15/10 trước 17/10 (riêng tỉ lệ buổi thử 9–10/10 thì P5 tính và báo nhóm ngày 10/10).
- 16/10 xem chéo trên ảnh chồng (không ai mở được CVAT máy khác). P4 `git pull`, chạy `m28.py collect --skip-export` trên 10 file `raw/`, commit bảng ảnh chồng (`outputs/collect_1610/`) khoảng phút 15 (P2 `git pull` rồi quét), rồi tạo 5 file `outputs/review_1610/<chủ mặt>.csv` (cột: face\_id, task, điểm, mã lỗi, người xem, đã sửa). Mỗi file gồm mặt bị đánh dấu (từ `outputs/collect_1610.md` và danh sách P2 quét) cộng 1 mặt ngẫu nhiên mỗi task. Mặt của Pk do P(k+2) xem: P1 xem mặt của P4, P2 xem P5, P3 xem P1, P4 xem P2, P5 xem P3. Không ai xem mặt mình hay khối mình đã gán, và mỗi file chỉ một người ghi nên không đụng nhau khi commit. Người xem mở bảng ảnh chồng và ảnh cắt trong `data/` (phóng to được), ghi mã lỗi, commit. P4 commit các file này khoảng phút 45; ai không có mặt bù thì làm việc "(giờ thứ hai)" trước, nhận file rồi mới xem chéo.
- 17/10: chủ mặt mở `outputs/review_1610/<mình>.csv`, sửa trên CVAT của mình (task vẫn còn), ghi "đã sửa", rồi chạy `python tool\export.py <task> <Pk> 1710 --final` cho từng task và commit `final/`. Lỗi RULE thì P5 đã chép vào bảng ca khó ngay khi xem chéo ngày 16/10.

## Repo và thư mục chung

| Thư mục | Chứa gì | Ai ghi |
| --- | --- | --- |
| `config/` | Một file cấu hình 50 điểm duy nhất: `m28_config.json` | P3; P1 commit bản đóng băng 12/10 |
| `data/` | Ảnh cắt 512 × 512, `manifest.csv`, `gt50.json` | P1, P3 |
| `raw/` | File CVAT xuất, `<task>_<người>_<ngày>.xml` | Mỗi người file của mình (export.py) |
| `outputs/` | `predictions.json`, cờ, bảng NME, `timing_log.csv`, CSV QC | P2–P5 |
| `overlays/` | 10 ảnh chồng F | P1 |
| `final/` | File xuất lần 2 (17/10), bộ nộp: `final/<task>_<Pk>_1710.xml` | Mỗi người file của mình (export.py) |

- `gt50.json` có dạng `{tên file ảnh: {tên điểm: [x, y]}}`. `mp50.json` có dạng `{tên file ảnh: {"orig": {tên điểm: [x, y]}, "flip": {tên điểm: [x, y]}}}`, trong đó flip là kết quả trên ảnh lật đã bỏ lật về ảnh gốc. Toạ độ ảnh cắt 512.
- `flags.json` có dạng `{tên file ảnh: [tên điểm có cờ]}`.
- Mọi script đọc tên, thứ tự điểm từ `config/`. Không gõ tay danh sách điểm.
- Từ 7/10 (P4 dựng project CVAT; mọi task phát cho 5 máy mang label này) không đổi tên hay thứ tự điểm.
- Không sửa file trong `raw/`. `raw/` và `final/` do mỗi người ghi file của mình (`<task>_<Pk>_<ngày>.xml` kèm file `.txt` cùng tên ghi bản server, số ảnh, giờ tạo task; bằng `tool/export.py`; script không ghi đè file đã có); mặt bù 16/10 ra file `_1610` mới. `backups/<Pk>/`: file sao lưu task do P4 dựng; mỗi người chỉ khôi phục file trong thư mục của mình, không mở thư mục của người khác.
- `tool/`: lệnh `m28.py`, gói `m28core/` và trang rà soát `review_app.py`, giao cho khách (chỉ MediaPipe, Gradio, cvat-sdk; không torch, không ảnh). `config/pipeline.json` chỉ giữ giá trị chung, không bí mật: tên project `m28`, tiền tố task `demo-`, bản CVAT `2.77.0`, image\_quality 95. Không ghi địa chỉ server, project\_id, token hay mật khẩu. Địa chỉ và token đọc từ biến môi trường `CVAT_URL`, `CVAT_ACCESS_TOKEN` của từng máy; project tìm theo tên.
- `runs/<run>/`: kết quả từng lượt chạy pipeline, mỗi bước một thư mục con. Có ảnh mặt, nên mặc định không commit. Chỉ hai lượt chạy trên ảnh WFLW, `runs/F5/` và `runs/R1610/`, được commit vào repo nội bộ (như ảnh cắt) để bạn khác rà hoặc push trên máy họ. Lượt chạy trên ảnh khách hàng không bao giờ rời máy chạy nó.
- P1 ghi (ngày 8/10, khi tạo khung `m28.py`) đúng bốn dòng này vào `.gitignore`: `runs/*`, `!runs/F5/`, `!runs/R1610/`, `runs/*/_tmp/` (không viết `runs/`, vì git sẽ không lấy lại được hai thư mục kia).

## Dựng môi trường (Windows, Python 3.14)

venv: môi trường Python riêng cho dự án.

- [ ] Máy mình, từ tối 5/10, sau khi P2 push requirements.txt (chậm nhất đầu buổi 6/10): chạy khối lệnh dưới → có `.venv` và `face_landmarker.task`; xong khi dòng `python -c` in 1.0.1.
- [ ] Máy mình, từ 6/10: chạy `check_mp.py` → xong khi in ra 478.

```bat
rem Chạy trong cmd, không dùng PowerShell
py -3.14 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import mediapipe as mp; from mediapipe.tasks.python import vision; print(mp.__version__)"
curl -L -o face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

```python
# check_mp.py
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

opts = vision.FaceLandmarkerOptions(
    base_options=mp_python.BaseOptions(model_asset_path="face_landmarker.task"),
    running_mode=vision.RunningMode.IMAGE, num_faces=1)
with vision.FaceLandmarker.create_from_options(opts) as lm:
    res = lm.detect(mp.Image.create_from_file("data/X1_01.png"))
    print(mp.__version__, len(res.face_landmarks[0]) if res.face_landmarks else "no face")
```

- MediaPipe 1.0.1 mới chạy thử trên một laptop Windows Python 3.14. Không cài thêm `opencv-python` vào venv này.
- Lỗi trên mọi máy (pip không cài được, import lỗi): báo P2; P2 dựng venv Python 3.12 cho cả nhóm. Lỗi chỉ trên máy bạn (ví dụ Windows chặn DLL): không tắt bảo mật. Dùng Colab/Kaggle: `!pip install -q mediapipe==1.0.1` (Kaggle: bật Internet trong Settings), rồi cùng đoạn kiểm tra. Báo P2.
- Trang rà soát (Gradio) cài vào `.venv` chung, theo hai bước để không làm hỏng venv:
  1. 5/10, chỉ P2, sau khi đã `pip freeze > requirements.txt`: chạy `python -m pip install --dry-run -r requirements-ui.txt` để xem gói nào sẽ bị đổi phiên bản. Không có numpy, pillow hay opencv bị đổi thì cài thật, ghi đúng bản đã cài vào `requirements-ui.txt` thành `gradio==<bản>` (xem bằng `pip show gradio`, ví dụ 6.29.1) để ngày 16/10 cả nhóm cài đúng bản đã thử, rồi chạy lại đoạn FaceLandmarker trên 1 ảnh đã dùng tối nay (vẫn in 1.0.1 và 478); `check_mp.py` chạy đầu buổi 6/10, khi đã có `data/X1_01.png`.
  2. 16/10, P1, P4, P5 (P3 không cần): cài `requirements-ui.txt` nếu P2 báo bước 1 ổn, rồi chạy lại `check_mp.py`.
- Gradio không cài được hoặc làm hỏng MediaPipe: xoá `.venv` và dựng lại từ `requirements.txt` (đừng "cài thử rồi gỡ": gỡ gradio không trả lại phiên bản cũ của các gói khác). Cả nhóm rà bằng `--review excel` (ảnh chồng và Excel), không dùng venv thứ hai.

## Cài CVAT trên máy mình (cả 5 người)

Nhóm dùng CVAT tự cài miễn phí, không có máy chủ chung, nên mỗi người chạy một CVAT trên laptop của mình. Ở công ty thật, CVAT là một server chung và mọi người đăng nhập vào đó; công cụ của nhóm chạy được với server đó khi đổi `CVAT_URL` và token (cài `cvat-sdk` cùng bản với server; xem mục Chạy pipeline), không sửa code.

**Chuẩn chung cho 5 máy:** CVAT bản v2.77.0 (lấy theo tag git), `cvat-sdk==2.77.0` và `cvat-cli==2.77.0` trong `requirements.txt`, Docker Engine chạy trong Ubuntu WSL2. Docker Engine miễn phí với mọi tổ chức và chạy được cả trên Windows Home. Không ai nâng cấp trước 24/10, kể cả khi có v2.78. P4 cài trong tối 5/10 (máy đầu tiên) và sửa mục này theo đúng lệnh đã chạy thật. Hạn: CVAT chạy được trước buổi gán G đầu tiên của bạn (P1, P5: 8/10; P2, P3, P4: 9/10). Giờ cài của từng người ghi trong tab riêng.

**Phần A** (khoảng 30 phút làm, cần quyền admin một lần và khởi động lại máy):

1. Kiểm máy, rồi đăng vào nhóm chat (chỉ chữ): bản Windows (gõ `winver`), RAM, ổ C còn trống, và dòng Virtualization trong Task Manager → Performance → CPU. Cần: Virtualization là Enabled, RAM ít nhất 8 GB (nên 16 GB), ổ C còn trống ít nhất 30 GB. Kiểm cổng 8080, 8090 còn trống trong PowerShell: `Get-NetTCPConnection -LocalPort 8080,8090 -State Listen -ErrorAction SilentlyContinue` (không in gì là trống).
2. Mở PowerShell bằng "Run as administrator", chạy `wsl --install`, khởi động lại máy, mở "Ubuntu" từ menu Start và tạo user, mật khẩu Linux. Kiểm: `wsl --version` (WSL từ 2.1.5 trở lên, thấp hơn thì chạy `wsl --update`) và `wsl -l -v` (Ubuntu ở VERSION 2).
3. Chỉ máy 8 GB: tạo file `C:\Users\<tên bạn>\.wslconfig` gồm ba dòng `[wsl2]`, `memory=5GB`, `swap=4GB`, rồi chạy `wsl --shutdown`.

**Phần B** (khoảng 25 phút làm, cộng 15–30 phút chờ tải; trong lúc chờ làm việc khác):

4. Cài Docker Engine trong cửa sổ Ubuntu, theo mục "Install using the apt repository" ở docs.docker.com/engine/install/ubuntu (trang đổi thì chép đúng lệnh trên trang):

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

Khối trên là cách cũ (file `docker.list`), vẫn chạy; trang Docker hiện dùng file `docker.sources`. Làm theo một cách thôi, không làm cả hai (hai nguồn apt cho cùng một kho làm apt báo lỗi).

Chạy `wsl --shutdown` trong PowerShell, mở lại Ubuntu; `docker version` và `docker compose version` phải chạy được; báo "Cannot connect to the Docker daemon" thì chạy `sudo systemctl start docker` (không được thì `sudo service docker start`). Ai đã có sẵn Docker Desktop thì hỏi trưởng nhóm về giấy phép; được dùng thì bỏ bước này, các bước sau giữ nguyên. Không cài Docker Engine vào Ubuntu đã bật WSL Integration của Docker Desktop.

5. Tải đúng bản CVAT, gõ trong Ubuntu:

```bash
cd ~
git clone --branch v2.77.0 --depth 1 https://github.com/cvat-ai/cvat
cd cvat
git describe --tags      # phải in v2.77.0
echo "$CVAT_VERSION"     # phải in dòng trống
```

6. Chỉ máy mình vào được CVAT: tạo file `~/cvat/docker-compose.override.yml` với nội dung dưới. Cổng 8080 bận thì ghi `"127.0.0.1:18080:8080"` và dùng `http://localhost:18080` ở mọi chỗ sau.

```yaml
services:
  traefik:
    ports: !override
      - "127.0.0.1:8080:8080"
```

7. Chạy CVAT (lần đầu tải khoảng 1,5 GB): `docker compose up -d`. Xem `docker logs cvat_server -f`, chờ hết phần migrate rồi bấm Ctrl+C. Kiểm: `docker exec -t cvat_server python manage.py health_check` (mọi dòng là "working") và `curl -s http://localhost:8080/api/server/about` (thấy `"version":"2.77.0"`).
8. Tạo tài khoản admin của CVAT trên máy bạn: `docker exec -it cvat_server bash -ic 'python3 ~/manage.py createsuperuser'`. Mật khẩu không ghi vào code, tài liệu hay chat.
9. Tạo token: mở Chrome (trình duyệt CVAT hỗ trợ chính thức) ở `http://localhost:8080`. Luôn gõ localhost: gõ 127.0.0.1 thì CVAT trả 404. Đăng nhập, rồi tạo token như dòng "Token (mỗi người…)" ở mục pipeline: tên `m28-<Pk>`, quyền đọc/ghi, hạn 25/10, copy ngay vì token chỉ hiện một lần.
10. Biến môi trường: Start → "Edit environment variables for your account" → thêm `CVAT_URL` = `http://localhost:8080` và `CVAT_ACCESS_TOKEN` = token. Mở cmd mới. Không dùng setx trong PowerShell. Không đặt biến tên `CVAT_HOST`: tên này thuộc docker-compose của CVAT (đặt sai có thể làm CVAT trả 404); công cụ của nhóm chỉ đọc `CVAT_URL`.
11. Trong cmd, ở thư mục repo (nên để ở đường dẫn ngắn, ví dụ `C:\m28`; `.venv` đã có cvat-sdk, cvat-cli 2.77.0): chạy một lần `python -m cvat_cli config default-server http://localhost:8080`, rồi `python -m cvat_cli task ls` (không lỗi, danh sách rỗng là đúng).
12. Trước 10/10 (khi P4 đã commit `backups/all/m28-check.zip`): `python -m cvat_cli task create-from-backup backups\all\m28-check.zip`, mở 1 mặt xem tên điểm, thứ tự và cờ low\_conf, đăng "CVAT ok 2.77.0" vào nhóm chat, rồi xoá task `m28-check`.

**Dùng hằng ngày.**

- Mở Ubuntu và để cửa sổ mở suốt buổi, chạy `cd ~/cvat && docker compose start`; chờ 1–3 phút. Xong buổi chạy `docker compose stop` (máy 8 GB đỡ chậm).
- Đầu buổi gán, khôi phục task của hôm nay (chỉ từ thư mục của bạn): `python -m cvat_cli task create-from-backup backups\<Pk>\<tên task>.zip`. Khôi phục đúng một lần; lỡ hai lần thì xoá bản thừa trước khi gán. Task khôi phục có thể không nằm trong project nào: không sao, label đi kèm file zip.
- Cuối khối, xuất và commit: `python tool\export.py <tên task> <Pk> <ngày ddmm>`. Lệnh ghi file XML và một file `.txt` cùng tên (bản server, số ảnh, giờ tạo task theo giờ Việt Nam; P5 dùng để kiểm sạch thí nghiệm), rồi in lệnh git cho hai file đó. `--final` cho lần xuất 17/10; `--check` chỉ in các thông tin trên. Chưa có `export.py` (trước khi P4 báo tối 8/10) hoặc script lỗi: xuất bằng giao diện (Actions → Export task dataset → "CVAT for images 1.1", tắt Save images), giải nén lấy `annotations.xml`, đổi tên thành `raw/<task>_<Pk>_<ddmm>.xml` và ghi giờ tạo task (xem ở trang task) vào file `.txt` cùng tên.
- Không bao giờ chạy `docker compose down -v` trước 24/10: lệnh này xoá toàn bộ nhãn trên máy. Bản chính của nhãn là file XML trong repo.

**Kiểm không lộ ra mạng** (P4 tối 5/10, ai nghi ngờ thì làm lại): từ điện thoại cùng Wi-Fi mở `http://<IP LAN của laptop>:8080`. Không kết nối được (bị từ chối hoặc hết giờ) là đạt. Thấy trang hay dòng "404 page not found" là CVAT đang lộ ra mạng: báo P4. Không chuyển cổng, không tunnel.

**Kẹt:** dán toàn văn lỗi (chữ, không ảnh có mặt người) vào nhóm chat; P4 hỗ trợ, P5 gom lỗi và dời việc. Máy không bật được ảo hoá hoặc không có quyền admin thì báo ngay tối đó; dự phòng ở mục Rủi ro của tab Kế hoạch.

**Dọn máy 24/10** (sau khi P5 xác nhận đã nộp, khoảng 15 phút): thu hồi token trong CVAT, xoá hai biến `CVAT_URL`, `CVAT_ACCESS_TOKEN`, rồi trong `~/cvat` chạy `docker compose down -v` (lần này cố ý xoá ảnh và nhãn), xoá thư mục tạm `runs\<run>\_tmp` nếu còn. Báo P4 khi xong.

## Colab hay Kaggle

|  | Colab miễn phí | Kaggle |
| --- | --- | --- |
| Một phiên | Tối đa 12 giờ, tuỳ tài nguyên | 12 giờ (CPU/GPU) |
| Bỏ không | Tự ngắt, không công bố sau bao lâu | Tài liệu ghi 20 hoặc 60 phút; tính 20 |
| GPU | Bị giới hạn, không công bố loại | P100 hoặc 2 × T4, khoảng 30 giờ/tuần, có thể phải chờ |
| File có còn | `/content` mất khi máy ảo bị xoá; lưu vào Drive | `/kaggle/working` giữ tới 20 GB |
| Chia dữ liệu | File nén trong `MyDrive/M28/`, chép về `/content` rồi giải nén | Chỉ khi có bạn phải dùng Kaggle: P1 tạo dataset riêng tư `m28-wflw`, thêm bạn đó làm collaborator (quyền xem) |
| Lưu ý | Không dùng nhiều tài khoản để lách giới hạn | Có thể phải xác minh số điện thoại để bật Internet/GPU (chưa kiểm chứng) |

Nguồn: [FAQ Colab](https://research.google.com/colaboratory/faq.html), [tài liệu Kaggle Notebooks](https://www.kaggle.com/docs/notebooks), [mẹo dùng GPU trên Kaggle](https://www.kaggle.com/docs/efficient-gpu-usage).

MediaPipe chạy CPU, không cần GPU. Chỉ đưa WFLW lên, không đưa dữ liệu khách hàng.

## Lấy WFLW một lần, dùng chung

- Chỉ P1 tải, ngày 5/10, từ [trang WFLW](https://wywu.github.io/projects/LAB/WFLW.html).
- Ngày 7/10, P1 chia sẻ thư mục `MyDrive/M28/` (quyền xem). Mỗi bạn thêm lối tắt vào MyDrive.
- Không giải nén trong Drive. Drive dễ treo khi một thư mục có hơn khoảng 10.000 file.
- WFLW lấy ảnh từ WIDER FACE, giấy phép CC BY-NC-ND. Ảnh cắt, đáp án, ảnh chồng chỉ ở CVAT trên máy từng người và repo nội bộ; ngày 24/10 mỗi người xoá dữ liệu CVAT trên máy mình (mục cài CVAT).

```python
# Ô Colab. Bạn khác (không phải P1): bỏ ba dòng pip, gdown, wget.
from google.colab import drive
drive.mount('/content/drive')
!mkdir -p /content/drive/MyDrive/M28
%cd /content/drive/MyDrive/M28
!pip install -q gdown
!gdown 1hzBd48JIdWTJSsATBEB_eFVvPL1bx6UC -O WFLW_images.tar.gz
!wget -q https://wywu.github.io/projects/LAB/support/WFLW_annotations.tar.gz
!mkdir -p /content/wflw && cp WFLW_*.tar.gz /content/wflw/
%cd /content/wflw
!tar -xzf WFLW_images.tar.gz && tar -xzf WFLW_annotations.tar.gz
!wc -l WFLW_annotations/list_98pt_rect_attr_train_test/*.txt   # 7500 và 2500
```

## Dùng công cụ AI

Được dùng: Claude, ChatGPT, Gemini trong Colab, GitHub Copilot, khi mentor đã đồng ý (P5 hỏi ngày 5/10). Copilot đọc code trong file đang mở: tắt Copilot khi mở file của khách hàng. Sáu quy tắc chung:

1. Không đưa dữ liệu khách hàng hay ảnh mặt (kể cả WFLW) vào bất kỳ chat AI nào.
2. Theo FAQ Colab, Gemini lưu prompt, code và kết quả tới 18 tháng; người duyệt có thể đọc. Chỉ hỏi về code.
3. Code AI viết: chạy thử trên 5 mẫu, xem kết quả, rồi mới chạy cả tập.
4. Code có `mp.solutions` thì bỏ. Chỉ dùng `vision.FaceLandmarker` với `face_landmarker.task`.
5. Hỏi về lỗi thì dán toàn bộ traceback (cả khối thông báo lỗi).
6. Không chụp hay quay trang rà soát để dán vào chat AI (trên đó có ảnh mặt). Hỏi AI về trang rà soát thì dùng ảnh giả (chấm màu trên nền trắng). Không bao giờ dán token CVAT vào chat hay vào code.

Ba câu hỏi mẫu:

- "Giải thích lỗi này bằng lời đơn giản và cách sửa ngắn nhất. Python 3.14, Windows. Traceback: …"
- "Viết hàm Python đọc file `<tên>` có cột `<…>`, trả về `<…>`. Thêm 3 dòng `assert` để tự kiểm."
- "Giải thích từng khối của đoạn code này. Chỉ chỗ dễ sai khi ảnh không thấy mặt."

## Hai chỗ phải gán tay

| Chỗ | Task CVAT | Vì sao |
| --- | --- | --- |
| Nhánh gán tay của thí nghiệm | `m28-manual`, `m28-pilot-manual` | Đây là mốc để so. Có nhãn nháp thì mất mốc. |
| Tập G | `m28-gold-x`, `m28-gold-y` | G đo hai người tự gán lệch nhau bao nhiêu. Nếu có nhãn nháp, cả hai người sẽ bám theo model. Độ lệch đo được sẽ nhỏ hơn thật. |

Mọi chỗ khác dùng nhãn nháp rồi kiểm tra (ngoài thí nghiệm, mặt bị trang rà soát chọn Gán tay cũng gán tay). Gán tay: vẽ khuôn mặt mẫu rồi kéo từng điểm. Không mở đáp án.

## Chạy pipeline và trang rà soát

Pipeline (chuỗi bước tự chạy nối nhau) nằm trong một file `tool/m28.py`. Bạn chỉ cần nhớ 4 lệnh; lệnh `all` chạy cả chuỗi.

| Lệnh | Làm gì | Ai chạy | Cần mạng? |
| --- | --- | --- | --- |
| `prepare` | Làm nhãn nháp cho cả thư mục ảnh, gợi ý cho từng mặt, vẽ ảnh chồng | Người vận hành | Không |
| `review` | Mở trang rà soát; bấm Nhận / Gán tay / Bỏ ảnh | Người rà | Không |
| `push` | Tạo task CVAT mới, nhập nhãn nháp đúng một lần | Người vận hành, trên CVAT mà `CVAT_URL` trỏ tới (ở M28: P4 cho tập R; ai cũng thử được trên CVAT của mình) | Không (localhost); ở công ty: mạng nội bộ |
| `collect` | Sau khi gán: xuất nhãn (chỉ từ CVAT trên máy chạy lệnh; task thí nghiệm dùng `--skip-export` trên `raw/` mọi người đã commit), QC, bảng ảnh chồng, báo cáo ngắn | Người vận hành (ở M28: P4; task thí nghiệm dùng --skip-export) | Không (localhost); ở công ty: mạng nội bộ |

- Công ty thật (một CVAT chung), với ảnh khách hàng: cả 4 lệnh chạy trên cùng một máy (máy người vận hành giữ token); người rà ngồi tại máy đó. Ảnh và thư mục `runs/` không rời máy. Công cụ chỉ đọc `CVAT_URL` và `CVAT_ACCESS_TOKEN` (thêm `CVAT_ORG` nếu project của công ty nằm trong organization); ở công ty đổi các biến này, sửa số bản CVAT trong `config/pipeline.json` và cài `cvat-sdk` cùng bản với server là chạy được, không sửa code. Ở M28, `CVAT_URL` là `http://localhost:8080` trên máy từng người, nên `push`, `collect` không cần mạng; `collect` chỉ xuất được task trên CVAT của chính máy đó.
- Với ảnh WFLW của dự án (tập R): P1 chạy `prepare` rồi commit `runs/R1610/` vào repo nội bộ; P5 `git pull`, rà trên máy mình rồi commit file rà; P4 `git pull` rồi chạy `push` và `collect` trên CVAT của P4. Task `demo-R1610` chỉ có trên máy P4, nên P4 sửa một mình. Ai muốn tập thì chạy lượt mới `python tool\m28.py all --run thu<Pk> --list data\f5_list.csv --images <WFLW_images> --box wflw --review auto --task demo-thu<Pk>` trên CVAT của mình (xong thì xoá task và thư mục `runs\thu<Pk>`); không push thẳng `runs/F5/` (thư mục đã commit).

```bat
rem Chạy trong cmd, ở thư mục repo
call .venv\Scripts\activate.bat
rem --images: thư mục WFLW_images trên máy bạn
python tool\m28.py prepare --run R1610 --list data\r_list_1610.csv --images D:\WFLW\WFLW_images --box auto
python tool\m28.py review --run R1610 --reviewer P5
rem Máy có CVAT_URL và CVAT_ACCESS_TOKEN (ở M28: CVAT của P4 cho tập R)
python tool\m28.py push --run R1610 --images D:\WFLW\WFLW_images --task demo-R1610 --review-file triage_P5.csv
python tool\m28.py collect --task demo-R1610
rem Task thí nghiệm: chỉ đọc file raw/ mọi người đã commit
python tool\m28.py collect --task m28-manual --task m28-assisted --tag 1610 --skip-export
```

- Chạy lại cùng lệnh không làm lại bước đã xong (bước xong thật mới có file `done.txt`). Bước chưa xong (rà chưa bấm Xong, chạy `--dry-run`) thì lệnh in lý do rồi dừng, không ghi `done.txt`. Muốn làm lại một bước: thêm `--force <tên bước>`, ví dụ `--force flags`.
- `--dry-run`: `push` và `collect` không thay đổi gì trên CVAT: `push` chỉ ghi file XML ra máy (không cần token); `collect` chỉ đọc và in danh sách job sẽ xuất (cần token, không tải nhãn về). Cả hai không ghi `done.txt`, nên lần chạy thật sau đó không bị bỏ qua.
- `--review`: `ui` (mặc định, trang rà soát Gradio), `excel` (dự phòng khi không có Gradio), `auto` (lấy gợi ý autoqc, không cần người).
- Token (mỗi người, cho CVAT trên máy mình): mở `http://localhost:8080` → menu tên bạn → Settings → Security → nút "+"; đặt tên `m28-<Pk>`, quyền đọc/ghi, hạn 25/10. Token chỉ hiện một lần: dán thẳng vào biến môi trường người dùng `CVAT_ACCESS_TOKEN` (Start → "Edit environment variables for your account"), thêm `CVAT_URL` = `http://localhost:8080` (ghi rõ `http://`; thiếu thì cvat-sdk tự hiểu là https), rồi mở cmd mới. Không dùng setx trong PowerShell (lệnh vào lịch sử, lộ token), không đặt biến `CVAT_HOST`. Không lưu token ra file, không ghi vào code, log hay chat. Ngày 24/10 mỗi người tự thu hồi token của mình. Ở công ty: `CVAT_URL` là địa chỉ server chung, token do người đó tạo trên server đó.
- Trang rà soát chỉ mở trên máy mình. Địa chỉ đúng là địa chỉ Gradio in ra trong cmd (thường http://127.0.0.1:7860, có thể 7861 nếu cổng bận). Không chạy trên Colab/Kaggle, không bật `share=True` (kể cả khi Gradio gợi ý), không dùng tunnel (ngrok, cloudflared). Báo không vào được localhost: chạy `set NO_PROXY=localhost,127.0.0.1` rồi chạy lại; vẫn lỗi thì dùng `--review excel`.
- Rà một mặt: xem điểm có cờ trước, rồi nhìn cả mặt. Nhận nếu chỉ cần sửa nhẹ; Gán tay nếu nháp lật gương, dồn cục hay lệch cả vùng, hoặc ảnh có nhiều mặt cần gán; Bỏ ảnh nếu không có mặt, sai mặt, quá mờ. Quy tắc đầy đủ: `guideline_triage.md` của P5.
- Rà xong bấm **Xong** rồi đóng trang (Ctrl+C trong cmd). Đóng trước khi bấm Xong thì lệnh dừng, chưa ghi `done.txt`; gõ lại đúng lệnh để rà tiếp. Kết quả: `runs/<run>/review/triage_<Pk>.csv` (chỉ tên file, quyết định, lý do, số giây) và `runs/<run>/review/done.txt`. `--review-file` chỉ cần tên file. Xoá thư mục tạm của Gradio: `rmdir /s /q runs\R1610\_tmp`.
- Dự phòng `--review excel`: xem ảnh chồng trong `runs\<run>\overlays\`; mở `runs\<run>\autoqc\autoqc.csv` bằng Excel; điền cột `decision` (`nhan`, `gan_tay`, `bo`) và `reason`; lưu dạng CSV UTF-8 thành `runs\<run>\review\triage_<Pk>.csv`; rồi chạy lại đúng lệnh. Lệnh kiểm mọi dòng đã có quyết định, ghi `done.txt` và đi tiếp; còn dòng thiếu thì in tên mặt còn thiếu và dừng, không ghi `done.txt`.

## Bảng thuật ngữ

| Từ | Nghĩa |
| --- | --- |
| NME | Độ lệch trung bình so với đáp án, tính bằng % của IOD. |
| IOD | Khoảng cách hai khoé mắt ngoài trên đáp án WFLW (điểm 60 và 72). |
| Nhãn nháp | 50 điểm model đặt sẵn để người kiểm tra và sửa. |
| Cờ `low_conf` | Ô đánh dấu điểm nháp model không chắc; chỉ để nhắc, vẫn xem mọi điểm. |
| Sai số chấp nhận | Mức lệch mỗi vùng bằng 2 × trung vị lệch giữa hai người trên G (tạm 3% IOD, chốt 12/10), chỉ dùng để phân tích. |
| T-dev / T-test | Hai tập 100 mặt không ai gán; T-dev để chọn model và ngưỡng, T-test chạy đúng một lần cuối. |
| Khối | Nhóm mặt cố định của một job, ví dụ X1 gồm X1\_01 … X1\_10. |
| Skeleton | Nhãn `face50` trong CVAT: 50 điểm có tên, nối bằng cạnh như một hình mặt. |
| occluded | Bật khi điểm bị che và bạn chỉ ước lượng vị trí. |
| AUROC | Số từ 0 đến 1 cho biết cờ tách điểm sai khỏi điểm đúng tốt đến đâu; 0,5 là đoán bừa. |
| seq | Số thứ tự mặt trong khối (01–10). Seq 1–2 là mặt khởi động, không tính giờ. |
| 6 cờ WFLW | 6 thuộc tính khó của mỗi mặt WFLW: pose, expression, illumination, makeup, occlusion, blur (0 hoặc 1). Khác cờ low\_conf. |
| KTC | Khoảng tin cậy: khoảng mà kết quả thật có lẽ nằm trong. Tính bằng bootstrap: bốc lại ngẫu nhiên các mặt 2.000 lần. |
| Trung bình nhân | Nhân 5 tỉ lệ với nhau rồi lấy căn bậc 5. |

Từ mới của pipeline:

| Từ | Nghĩa |
| --- | --- |
| Pipeline | Chuỗi bước tự chạy nối nhau; ở đây là lệnh `tool/m28.py`. |
| Lượt chạy (run) | Một lần chạy pipeline trên một lô ảnh, có tên riêng (ví dụ `R1610`); kết quả ở `runs/<tên>/`. |
| prepare / review / push / collect | Chuẩn bị nhãn nháp / rà từng mặt / đẩy lên CVAT / thu nhãn về sau khi gán. |
| `m28.py push` | Bước đẩy ảnh và nhãn nháp lên CVAT. Khác với `git push` (đưa code lên repo). |
| Trang rà soát | Trang web chạy trên máy bạn (127.0.0.1) để duyệt nhãn nháp từng mặt trước khi nhập CVAT. |
| Triage (rà soát) | Phân loại nhanh từng mặt: Nhận, Gán tay hay Bỏ; kết quả ở `triage_<Pk>.csv`. |
| 127.0.0.1 | Địa chỉ "chính máy này"; máy khác và Internet không mở được. |
| autoqc | 5 phép kiểm của qc.py chạy trên nhãn nháp trước khi nhập, gợi ý ổn / cần xem / nên gán tay. |
| Ảnh chồng | Ảnh mặt có vẽ các điểm nháp lên trên, để nhìn là thấy điểm sai. |
| `--force <bước>` | Bắt làm lại một bước dù bước đó đã xong. |
| `--dry-run` | Chạy thử, không thay đổi gì trên CVAT: `push` chỉ ghi XML ra máy, `collect` chỉ in danh sách job; không ghi `done.txt`. |
| Personal Access Token | Mã truy cập cá nhân do CVAT cấp, dùng thay mật khẩu; thu hồi được bất cứ lúc nào. |
| Biến môi trường | Giá trị lưu trong Windows, code đọc bằng `os.environ`; nhờ vậy không ghi bí mật vào file. |
| Tập R | 50 ảnh WFLW gốc chưa dùng, có đáp án, để chạy thật pipeline và chấm trang rà soát. |

Từ mới về CVAT trên máy mình:

| Từ | Nghĩa |
| --- | --- |
| localhost | Địa chỉ của chính máy này. CVAT của bạn ở `http://localhost:8080`; máy khác không mở được. |
| Docker, WSL2 | WSL2 chạy Ubuntu bên trong Windows; Docker chạy CVAT trong đó thành nhiều "container". |
| Task backup | File zip CVAT sao lưu một task (ảnh, label, nhãn đã có). "Create from backup" tạo lại đúng task đó trên CVAT khác cùng bản. |
| `backups/<Pk>/` | Thư mục chứa file backup của riêng bạn, do P4 dựng. Chỉ khôi phục file trong thư mục của mình, đúng buổi. |
| `export.py` | Lệnh tự xuất nhãn (chỉ nhãn) từ CVAT của bạn vào `raw/` hoặc `final/`. |
| Dấu vân tay label | Mã băm tính từ tên, loại và thuộc tính của 50 điểm (không dùng id); 5 máy phải giống nhau. |
