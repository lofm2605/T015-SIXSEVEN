# Hướng dẫn chạy m28 trên Windows

Dành cho cả 5 người (P1–P5). Mọi lệnh viết cho **cmd** (không phải PowerShell), Python 3.14, CPU, không cần GPU.
Bản này **chưa ai thử trên Windows thật**: gặp lỗi thì ghi lại nguyên văn rồi báo P1 (xem mục 8).
Ảnh WFLW là CC BY-NC-ND: chỉ dùng nội bộ, không gửi cho ai ngoài nhóm, không đưa vào chat AI nào khác.

## 0. Chuẩn bị
- Windows 10/11, ổ C còn trống ≥ 5 GB. Đặt thư mục ở đường dẫn **ngắn**, ví dụ `C:\m28`.
- Cài **Python 3.14** (python.org, tick "Add python.exe to PATH" và "py launcher") và **Git**. `curl` và `tar` có sẵn trong Windows 10/11.
- Mediapipe trên Python 3.14 mới thử trên một máy: nếu bước 3 báo lỗi import thì cài Python 3.12 và thay `py -3.14` bằng `py -3.12`.
- Cần tài khoản GitHub đã được chủ repo mời vào repo `lofm2605/T015-SIXSEVEN` (riêng tư).

## 1. Lấy code
```bat
cd C:\
git clone https://github.com/lofm2605/T015-SIXSEVEN.git m28
cd m28\source-tool\m28-prelabel
git checkout main
```
Từ đây mọi lệnh chạy trong thư mục `C:\m28\source-tool\m28-prelabel`. Muốn lấy bản mới: `git pull`.

## 2. Môi trường Python
```bat
py -3.14 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
rem bỏ torch/torchvision (chỉ để so sánh nội bộ, nặng, không cần để chạy m28):
findstr /V /I "torch" requirements.txt > %TEMP%\req_m28.txt
python -m pip install -r %TEMP%\req_m28.txt
python -m pip install -r requirements-ui.txt
python -m pip install pytest
python -c "import mediapipe as mp; print(mp.__version__)"
```
Phải in `1.0.1`. Mỗi lần mở cmd mới phải chạy lại `call .venv\Scripts\activate.bat`.
Trước khi cài `requirements-ui.txt`, nên thử `python -m pip install --dry-run -r requirements-ui.txt`: nếu nó định đổi numpy/opencv thì dừng và báo P2.

## 3. Model MediaPipe
```bat
curl -L -o face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```
Phải được file ~3,7 MB, đặt cùng thư mục chạy lệnh. Không commit file này.

## 4. Dữ liệu WFLW
**a) Gói dữ liệu đã cắt sẵn** (do chủ repo gửi, 9 file `m28_data_part00_meta.zip` … `part08_of_08.zip`): giải nén **tất cả vào cùng thư mục** `data\` rồi kiểm:
```bat
mkdir data
tar -xf m28_data_part00_meta.zip -C data
tar -xf m28_data_part01_of_08.zip -C data
rem ... lặp tới part08_of_08 (hoặc giải nén bằng Explorer, chọn thư mục data)
python tool\check_manifest.py data\manifest.csv
```
Phải in `manifest.csv đạt`; `data\crops\` có 616 ảnh, có `data\gt98.json`.

**b) Ảnh WFLW gốc** (chỉ cần khi chạy `prepare`/`all`, 743 MB; làm một lần):
```bat
mkdir D:\WFLW
curl -L -o D:\WFLW\WFLW_images.tar.gz "https://drive.usercontent.google.com/download?id=1hzBd48JIdWTJSsATBEB_eFVvPL1bx6UC&export=download&confirm=t"
tar -xzf D:\WFLW\WFLW_images.tar.gz -C D:\WFLW
dir D:\WFLW\WFLW_images
```
Kích thước file tải phải đúng 743.030.592 byte. Google Drive hết lượt tải thì thử lại sau hoặc hỏi P1 (có bản dự phòng trên Kaggle, xem `nguon-du-lieu.md`).
Nhãn gốc (chỉ P1/P3 cần khi sinh lại `manifest.csv`): `curl -L -O https://wywu.github.io/projects/LAB/support/WFLW_annotations.tar.gz`.

## 5. Chạy thử trên 5 mặt (không cần CVAT, không cần token)
Tạo danh sách 5 mặt F rồi chạy cả chuỗi ở chế độ chạy thử:
```bat
python -c "import csv;r=[x for x in csv.DictReader(open('data/manifest.csv',encoding='utf-8')) if x['set']=='F'][:5];w=csv.writer(open('data/f5_list.csv','w',newline=''));w.writerow(['wflw_image','wflw_line','seed']);[w.writerow([x['wflw_image'],x['wflw_line'],5]) for x in r]"
python tool\m28.py all --run F5 --list data\f5_list.csv --images D:\WFLW\WFLW_images --box wflw --review auto --dry-run
```
Kết quả đúng: các bước `crop`, `mediapipe`, `map50`, `flags`, `autoqc`, `overlays` đều "xong", `push` in "Chạy thử (--dry-run)" rồi dừng,
và có `runs\F5\xml\prelabel.xml` (5 mặt × 50 điểm). Lần chạy này `low_conf` = 0 vì `t_flip` trong `config\m28_config.json` còn `null` (P2 chốt sau họp 12/10).
Để thấy điểm đỏ trên trang rà soát khi thử: mở `config\m28_config.json`, đổi `"t_flip": null` thành `"t_flip": 0.0672` rồi chạy lại các bước từ `flags`:
`python tool\m28.py prepare --run F5 --list data\f5_list.csv --images D:\WFLW\WFLW_images --box wflw --force flags autoqc overlays`.
(Đừng commit file config sau khi sửa số này; hoàn lại bằng `git checkout config\m28_config.json`.)

## 6. Trang rà soát (giao diện trước khi nhập CVAT)
```bat
python tool\m28.py review --run F5 --reviewer P1 --force review
```
Trình duyệt tự mở http://127.0.0.1:7860 (chỉ máy bạn truy cập được). Chọn lý do **trước**, rồi bấm **Nhận (N) / Gán tay (G) / Bỏ ảnh (B)**; Hoàn tác (Z), ← → để chuyển mặt.
Rà hết thì bấm **Xong**, cửa sổ tự đóng. Kết quả nằm ở `runs\F5\review\triage_P1.csv`. Chỉ mở **một tab**. Không chia sẻ cổng này cho ai.
Không có Gradio hoặc trang lỗi: dùng `--review excel` (mở `runs\F5\autoqc\autoqc.csv` bằng Excel, điền cột `decision` = nhan / gan_tay / bo, lưu CSV UTF-8 thành `runs\F5\review\triage_P1.csv`).

## 7. Nhập vào CVAT (khi đã có CVAT trên máy)
Cài CVAT theo `de-tai-m28\huong-dan-chung.md` (mục cài CVAT). Token chỉ đặt trong biến môi trường, không ghi vào file hay chat:
```bat
set CVAT_URL=http://localhost:8080
set CVAT_ACCESS_TOKEN=<dán token của bạn>
python tool\m28.py push --run F5 --task demo-F5
python tool\m28.py collect --task demo-F5
```
Chỉ tạo task bắt đầu bằng `demo-`; không bao giờ chạy trên task `m28-`. `push` và `collect` thật là phần của P4, **chưa có**: hiện chỉ dùng `push --dry-run`.

## 8. Chạy test và báo lỗi
```bat
python -m pytest tests -q
```
Phải ra `116 passed` (hoặc hơn). Test chỉ dùng dữ liệu giả, không cần ảnh WFLW hay mạng.

| Triệu chứng | Cách xử lý |
|---|---|
| `Python ... bị chặn` / lỗi 4551 / DLL bị chặn (Smart App Control, antivirus) | Không tắt bảo mật. Thử cài Python từ python.org (không dùng Store), thêm thư mục dự án vào ngoại lệ của antivirus, hoặc dùng Python 3.12; còn kẹt thì báo P1/P2 |
| `UnicodeEncodeError` khi chuyển hướng ra file | `set PYTHONUTF8=1` rồi chạy lại |
| `Cổng 7860 bận` | Đã có bản trang rà soát đang chạy: đóng nó, hoặc `set GRADIO_SERVER_PORT=7861` |
| Trình duyệt không tự mở | `set M28_NO_BROWSER=1` rồi tự mở http://127.0.0.1:7860 |
| `Thiếu file config\...` / `Thiếu m28core.push` | Chưa `git pull`, hoặc phần đó là của P4 chưa commit |
| `không đọc được ảnh` ở bước crop | Sai `--images`: phải trỏ tới thư mục chứa `0--Parade`, `1--Handshaking`... |
| `import mediapipe` lỗi | Python 3.14 chưa hỗ trợ trên máy bạn: tạo lại venv bằng `py -3.12`; ghi lại phiên bản và báo P2 |

Khi báo lỗi gửi: bản Windows (`winver`), `python --version`, lệnh đã gõ và 10 dòng cuối của `runs\<run>\log.txt`. **Không** gửi ảnh mặt, `gt98.json`, file xuất CVAT hay token.
