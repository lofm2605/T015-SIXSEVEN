# Hướng dẫn chạy m28 trên Ubuntu

Bản Ubuntu của `HUONG-DAN-WINDOWS.md`. Mọi lệnh viết cho **bash**, CPU, không cần GPU. Các mục nào không khác Windows (cách rà soát, ca khó, nhập CVAT trên trang) thì xem mục tương ứng bên kia;
ở đây chỉ ghi chỗ khác. Bản này **chưa chạy đủ trên Ubuntu thật**: gặp lỗi thì ghi nguyên văn rồi báo P1.
Ảnh trong xe (YawDD, DrivFace) là ảnh người lái xe, chỉ dùng nội bộ nhóm, không đăng, không đưa vào chat AI.

> **Cách nhanh nhất:** lấy code (mục 1), giải nén dữ liệu (mục 4), rồi trong thư mục `source-tool/m28-prelabel` chạy `./chay.sh`.
> File tự cài môi trường Python lần đầu, tải model, rồi hiện menu giống `chay.bat`.

## 0. Chuẩn bị
```bash
sudo apt update
sudo apt install -y git curl unzip python3 python3-venv python3-pip
```
- **Phiên bản Python:** kế hoạch ghi Python 3.14, nhưng Ubuntu thường chỉ có 3.10 (22.04) hoặc 3.12 (24.04). `chay.sh` tự chọn bản mới nhất có sẵn (3.14 → 3.10).
  Mã nguồn biên dịch được trên 3.10; **mediapipe 1.0.1 và gradio 6.29.1 có chạy trên 3.10 hay không thì chưa kiểm**: nếu `pip install` báo không có bản phù hợp, cài Python mới hơn
  (Ubuntu 22.04: PPA `deadsnakes`, `sudo apt install python3.12 python3.12-venv`) rồi chạy lại (menu mục 6 để cài lại `.venv`).
- Thiếu `python3-venv` thì `python3 -m venv` báo thiếu `ensurepip`: cài đúng gói theo phiên bản (`python3.12-venv`...).
- CVAT cài **Docker Engine gốc trên Ubuntu** (không cần WSL): làm theo `de-tai-m28/huong-dan-chung.md`, bỏ phần WSL; `docker compose up -d` chạy thẳng, chỉ mở ở `http://localhost:8080`.

## 1. Lấy code
```bash
cd ~
git clone https://github.com/lofm2605/T015-SIXSEVEN.git m28
cd m28/source-tool/m28-prelabel
git checkout main
```
Muốn lấy bản mới: `git pull`. Nếu `chay.sh` báo `Permission denied`: `chmod +x chay.sh`.

## 2. Môi trường Python (làm tay; `chay.sh` đã làm hộ)
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
# bỏ torch/torchvision (chỉ để so sánh nội bộ, nặng, không cần để chạy m28):
grep -v -i torch requirements.txt > /tmp/req_m28.txt
python -m pip install -r /tmp/req_m28.txt
python -m pip install -r requirements-ui.txt
python -m pip install pytest
python -c "import mediapipe as mp; print(mp.__version__)"
```
Phải in `1.0.1`. Mỗi lần mở terminal mới chạy lại `source .venv/bin/activate`. Trước khi cài `requirements-ui.txt` nên thử `python -m pip install --dry-run -r requirements-ui.txt`:
nếu nó định đổi numpy/opencv thì dừng và báo P2.

## 3. Model MediaPipe
```bash
curl -L -o face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```
Phải được file ~3,7 MB, đặt cùng thư mục chạy lệnh. Không commit file này.

## 4. Dữ liệu in-cabin (YawDD + DrivFace)
**a) Gói đã cắt sẵn** (chủ repo gửi `m28_incab_part*.zip`): giải nén tất cả vào cùng thư mục `data/` rồi kiểm:
```bash
mkdir -p data
for f in m28_incab_part*.zip; do unzip -o "$f" -d data; done
python tool/check_manifest.py data/manifest.csv
```
Phải in `Kiểm manifest kiểu: in-cabin (YawDD + DrivFace)` rồi `manifest.csv đạt`; `data/crops/` có 616 ảnh `.png`.

**b) Tự dựng lại gói (chỉ P1/chủ repo; cần video YawDD 5,3 GB và DrivFace 26 MB):**
```bash
sudo apt install -y p7zip-full        # giải nén file .rar của YawDD
mkdir -p ~/incab && cd ~/incab
curl -L -O https://skuld.cs.umass.edu/traces/mmsys/2014/user06.tar
tar -xf user06.tar
7z x "user06/YawDD dataset.rar" -o"$HOME/incab"        # ra thư mục "YawDD dataset"
curl -L -o drivface.zip https://archive.ics.uci.edu/static/public/378/drivface.zip
unzip -o drivface.zip -d "$HOME/incab"
mkdir -p DrivFace/imgs && unzip -o DrivFace/DrivImages.zip -d DrivFace/imgs
cd -    # về lại source-tool/m28-prelabel
python tool/inc_ingest.py all --yawdd "$HOME/incab/YawDD dataset" --drivface "$HOME/incab/DrivFace" --model face_landmarker.task --out data --seed 5
```
Các lệnh tải/giải nén này **chưa thử**: đối chiếu tên thư mục thật sau mỗi bước. Chi tiết các cờ: `TAI-LIEU-CHI-TIET.md`, mục "Dữ liệu in-cabin".

## 5. Chạy thử trên 5 mặt (không cần CVAT, không cần token)
Cách nhanh: `./chay.sh`, chọn 3. Hoặc gõ tay:
```bash
python -c "import csv;r=[x for x in csv.DictReader(open('data/manifest.csv',encoding='utf-8')) if x['set']=='F'][:5];w=csv.writer(open('data/f5_list.csv','w',newline=''));w.writerow(['image','face_idx','seed']);[w.writerow([x['image'],x['face_idx'],x['seed']]) for x in r]"
python tool/m28.py all --run F5 --list data/f5_list.csv --images data/crops --box crop --review auto --dry-run
```
Kết quả đúng: các bước `crop`, `mediapipe`, `map50`, `flags`, `autoqc`, `overlays` đều "xong", `push` in "Chạy thử (--dry-run)", và có `runs/F5/xml/prelabel.xml`.
Khoản `t_flip` và điểm đỏ: như `HUONG-DAN-WINDOWS.md` mục 5; hoàn lại config bằng `git checkout config/m28_config.json`.

## 6. Trang rà soát
```bash
python tool/m28.py review --run F5 --reviewer P1 --force review
python tool/review_app.py --nap P1          # chưa có lượt nào: kéo thả ảnh ở tab Nạp ảnh
python tool/review_app.py runs/F5 P1        # mở lại một lượt
```
Trình duyệt tự mở http://127.0.0.1:7860 (chỉ máy bạn vào được). Cách rà, Ca khó, tab Các đợt: như bản Windows (đổi `\` thành `/` trong đường dẫn; thông báo trong tool vẫn in `\` kiểu Windows, gõ lại bằng `/`).
Khác với Windows:
- Chạy trên máy không có giao diện (SSH) hoặc trình duyệt không tự mở: `export M28_NO_BROWSER=1`, rồi tự mở http://127.0.0.1:7860 (qua SSH: `ssh -L 7860:127.0.0.1:7860 <máy>`). Không `share=True`, không tunnel công khai.
- Cổng bận: `export GRADIO_SERVER_PORT=7861`.
- `--review excel` mở CSV bằng LibreOffice Calc (`libreoffice --calc runs/F5/autoqc/autoqc.csv`), lưu CSV UTF-8 thành `runs/F5/review/triage_P1.csv`.

### Bấm giờ và thống kê (thí nghiệm hai nhóm, QĐ-006)
Đội chia **hai nhóm độc lập**: `manual` (gán tay hoàn toàn) và `assisted` (dùng tool, sửa nháp), cùng một bộ ảnh. Ai ở nhóm nào do cả đội chốt, ghi vào `config/nhom_thi_nghiem.json` (file mẫu để trống; tool không đoán). Đồng hồ thay `facetimer.py`.

**Quy trình một buổi (mỗi người):**
1. Đầu buổi **khôi phục task của hôm nay** (file sao lưu P4 phát) rồi mở trang: `./chay.sh` mục 1 (hoặc `python tool/review_app.py --nap P5`).
2. **Nạp ảnh** ở tab Nạp ảnh (**Upload & Continue** hoặc **Upload & Open**): đồng hồ ⏱ ở đầu trang **tự chạy** cho người rà của trang (phải là P1–P5; đặt ở tab Cài đặt). Nhóm lấy từ file nhóm, người chưa có trong file thì mặc định `assisted` và dòng bấm giờ ghi cờ `chua_co_nhom`. **Mỗi đợt một đồng hồ riêng**, giờ của đợt này không lẫn vào đợt khác (mỗi lần Nạp ảnh là một đợt mới): **Upload & Open** chuyển đồng hồ sang đợt mới (đồng hồ đợt cũ tạm dừng, giữ nguyên giờ); **Upload & Continue** lúc đã có đồng hồ ở đợt khác thì đồng hồ đó giữ nguyên và đợt mới chờ ở 00:00. Một người chỉ có một đồng hồ chạy tại một lúc. Đợt đã có đồng hồ thì giữ nguyên, không đè.
3. Gán nhãn trong CVAT như thường. Nghỉ thì bấm nút **Pause** cạnh đồng hồ, quay lại bấm **Resume** (cùng một nút, đổi chữ; **Start** với đợt đang chờ). Chuyển trang sang đợt khác (**Review batch** ở tab Các đợt) lúc đồng hồ đang chạy thì đồng hồ đi theo sang đợt đó nếu đợt đó đã có đồng hồ; đợt chưa có đồng hồ thì chỉ tạm dừng đồng hồ cũ, không tự tạo thêm. Chip ghi giờ của đợt đang mở, giờ các đợt khác ghi mờ cạnh chip và trên thẻ đợt ở tab Các đợt. Không còn tab Đồng hồ.
4. Xong việc **của một đợt**: `python tool/m28.py collect --task demo-<đợt> --reviewer P<số của bạn>` **trước**, rồi bấm **Close page**, chọn đợt ở ô **Đợt cần lưu / bỏ** (ô chỉ hiện khi bạn có đồng hồ ở từ hai đợt) và bấm **Save timing**. Mỗi lần bấm lưu **một đợt** (nhiều đợt thì lưu lần lượt từng đợt): trang ghi dòng của đợt đó vào `outputs/timing/timing_P<số>.csv` và gói **`outputs/ket_qua/ketqua_P<số>_<DDMM>_<đợt>.zip`**: **gửi file `.zip` này cho nhóm trưởng** (Drive riêng tư của đội; gói không có ảnh, token, email hay đường dẫn). Chưa thấy nhãn đã xuất trong `raw/` thì trang nhắc chạy `collect` trước; bấm Save timing thêm lần nữa mới lưu gói chỉ có thời gian. Sau khi lưu, bấm **Cancel** để ở lại trang hoặc **Close page** để tắt.
5. Quên bấm, nghỉ lâu, qua nửa đêm, tắt trang đột ngột: phiên vẫn lưu được, kèm cờ `canh_bao` trong dòng bấm giờ để thống kê đánh dấu (không còn nút Sửa thời gian trên giao diện); khi có cảnh báo chưa xử lý, Save timing hỏi bằng cách bấm thêm một lần. Đóng trang khi đồng hồ chạy thì nó **tự tạm dừng**; mở lại trang, bấm **Resume**. Muốn bỏ phiên (không lưu gì): hộp Đóng trang → chọn đợt → **Discard session**, bấm hai lần.

**Nhóm trưởng tổng kết** (chỉ cần các gói zip, không cần ảnh hay CVAT):
```bash
source .venv/bin/activate
python tool/tong_ket.py --vao <thư mục chứa các gói> --ra outputs/tong_ket
```
Công cụ kiểm từng gói (loại gói hỏng hoặc trùng và nói lý do), gộp các người, tính ba chỉ số và ghi `outputs/tong_ket/<ngày-giờ>/thong_ke.html` + CSV. Trên trang cũng có nút **Nạp các gói kết quả của nhóm** ở tab Thống kê.

**Ba chỉ số (tab Thống kê, `python tool/thong_ke.py`):** (1) NME của nháp so với nhãn gán tay của nhóm manual trên cùng ảnh; (2) tỉ lệ điểm phải sửa của nhóm assisted (ngưỡng 2% IOD, chỉnh được); (3) giây/mặt hai nhóm và % nhanh hơn của assisted (mục tiêu ≥ 20%, KTC 90% bằng cluster bootstrap; mỗi nhóm dưới 2 người thì chỉ có kết quả mô tả). **Hạn chế:** tốc độ từng người khác nhau lẫn vào kết quả (nên có một đợt khởi động chung hoặc chia nhóm cân tốc độ); giây/mặt là ước lượng chia đều nếu không bấm từng mặt.

### Thống kê và lọc dữ liệu train
Chỉ đọc `runs/`, `raw/`, `final/`, `data/`; chỉ ghi dưới `outputs/`. Cùng code với Windows (xem mục "Thống kê và lọc dữ liệu train" trong `HUONG-DAN-WINDOWS.md`), chỉ khác lệnh:
```bash
source .venv/bin/activate
python tool/thong_ke.py --luot-nhap <lượt chứa nháp> [--nguong-sua 2] [--goi <thư mục gói>] [--timing .]
mkdir -p outputs
cp config/loc_mau.json outputs/loc_cua_toi.json
python tool/loc_du_lieu.py --cau-hinh outputs/loc_cua_toi.json --dry-run
python tool/loc_du_lieu.py --cau-hinh outputs/loc_cua_toi.json --ten finetune_v1
```
Hai tab **Thống kê** và **Lọc dữ liệu** nằm trong trang rà soát (`./chay.sh` mục 1 hoặc `python tool/review_app.py --nap P5`). Gói train chứa ảnh mặt người lái xe thật: chỉ dùng nội bộ nhóm, không đưa lên git hay chat AI.

## 7. Nhập vào CVAT
Cài CVAT cùng bản 2.77.0 (mục 0), rồi:
```bash
python -m pip install cvat-sdk==2.77.0
python tool/make_label.py
```
- **Từ trang rà soát:** tab **Cài đặt** → dán `http://localhost:8080` và token → **Save** → **Test CVAT connection**. Bật **Nhớ trên máy này** thì token lưu ở `~/.config/m28/cvat.json`
  (hoặc `$XDG_CONFIG_HOME/m28/`), ngoài repo, quyền `0600` (chỉ chủ máy đọc được; tool tự đặt). Ngày 24/10 bấm **Forget token** và thu hồi token trong CVAT.
- **Lệnh trong terminal** (`m28.py push/collect`) **không đọc `cvat.json`**: đặt biến môi trường trong chính terminal đó:
```bash
export CVAT_URL=http://localhost:8080
read -rs CVAT_ACCESS_TOKEN && export CVAT_ACCESS_TOKEN     # gõ/dán token, không hiện ra màn hình và không vào lịch sử
python tool/m28.py push --run F5 --reviewer P2 --task demo-F5
python tool/m28.py collect --task demo-F5 --reviewer P2
```
  Đừng viết token thẳng trên dòng lệnh (`export CVAT_ACCESS_TOKEN=...` ghi vào `~/.bash_history`). Đóng terminal là biến mất; không lưu vào `~/.bashrc`.
- **`collect` tách nhãn theo từng job** (task `demo-…`, mặc định bật): ngoài file cả task còn có `raw/<task>_<người>_<DDMM>_job<id>.xml` (+ `.txt`), tách offline, không gọi thêm CVAT. `--no-per-job` bỏ tách; `--job <id>` (nhiều lần được) chỉ ghi job đó; `--dry-run` in frame, loại và tên file job sẽ ghi. Tách file đã xuất từ trước:
```bash
python tool/tach_job.py --xml raw/demo-F5_P2_1810.xml
python tool/tach_job.py --xml final/demo-F5_P2_1810.xml --out final/ --job 105
```
  File job **chỉ để đọc/đo** (`python tool/eval50.py --gt raw/<file>_job<id>.xml ...`), **không nhập lại vào CVAT**, không vào git.
- Kiểm tra nhanh trước lần push đầu: `./chay.sh` mục 4, hoặc `python tool/cvat_smoke.py` (và `--dry-run` để kiểm cục bộ). Các cảnh báo xoá, `collect`, `demo-` / `m28-`: như `HUONG-DAN-WINDOWS.md` mục 7.
- Kiểm CVAT đang chạy: `docker compose ps` trong thư mục CVAT, rồi mở http://localhost:8080.

## 8. Test và báo lỗi
```bash
source .venv/bin/activate
python -m pytest tests -q
```
Trên Windows có 11 lỗi có sẵn (symlink, CRLF); trên Ubuntu **chưa có số đo**, ghi lại kết quả đầu tiên rồi báo P1. `tests/test_chay_bat.py` chỉ đọc tĩnh `chay.bat`, nên vẫn chạy được trên Linux.
Test chỉ dùng dữ liệu giả, không cần ảnh mặt thật hay mạng.

| Triệu chứng | Cách xử lý |
|---|---|
| `No module named ensurepip` / `venv` | `sudo apt install python3-venv` (hoặc `python3.X-venv`) |
| `pip install mediapipe` không tìm được bản phù hợp | Python quá cũ/mới: cài Python 3.12 (PPA `deadsnakes`), xoá `.venv`, chạy lại |
| `ImportError: libGL.so.1` / `libgthread` | `sudo apt install libgl1 libglib2.0-0` |
| `UnicodeEncodeError` | `export PYTHONUTF8=1` (`chay.sh` đã đặt) |
| `Cổng 7860 bận` | Đóng bản đang chạy, hoặc `export GRADIO_SERVER_PORT=7861` |
| Trình duyệt không tự mở | `export M28_NO_BROWSER=1` rồi tự mở http://127.0.0.1:7860 |
| `docker: permission denied` | `sudo usermod -aG docker $USER`, đăng xuất và đăng nhập lại |
| `Thiếu file config/...` | Chưa `git pull`, hoặc đứng sai thư mục (phải ở `source-tool/m28-prelabel`) |

Khi báo lỗi gửi: bản Ubuntu (`lsb_release -a`), `python --version`, lệnh đã gõ và 10 dòng cuối của `runs/<run>/log.txt`. **Không** gửi ảnh mặt, file xuất CVAT hay token.
