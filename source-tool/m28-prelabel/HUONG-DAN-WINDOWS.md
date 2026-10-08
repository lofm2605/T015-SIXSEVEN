# Hướng dẫn chạy m28 trên Windows

Dành cho cả 5 người (P1–P5). Mọi lệnh viết cho **cmd** (không phải PowerShell), Python 3.14, CPU, không cần GPU.
Bản này **chưa ai thử trên Windows thật**: gặp lỗi thì ghi lại nguyên văn rồi báo P1 (xem mục 8).
Ảnh trong xe (YawDD, DrivFace) là ảnh người lái xe, giấy phép chỉ cho dùng học tập/nghiên cứu: chỉ dùng nội bộ, không đăng, không gửi cho ai ngoài nhóm, không đưa vào chat AI nào khác.

> **Cách nhanh nhất:** sau khi lấy code (mục 1) và giải nén dữ liệu (mục 4), **nhấp đúp `chay.bat`** trong thư mục
> `source-tool\m28-prelabel`. File này tự cài môi trường Python lần đầu, tải model, rồi hiện menu: mở trang rà soát
> (Nạp ảnh, Các đợt, Ca khó, Cài đặt), rà lại lượt cũ, chạy thử 5 mặt, chạy test. Các mục dưới là cách làm tay từng bước.

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

## 4. Dữ liệu in-cabin (YawDD + DrivFace)
Từ 6/10/2026 (QĐ-001) tập chính là ảnh tài xế trong xe; nguồn và giấy phép: xem `nguon-du-lieu.md`. Ảnh người lái xe là dữ liệu nhạy cảm: chỉ để trên máy bạn, không đăng, không đưa vào chat AI.

**a) Gói dữ liệu đã cắt sẵn** (do chủ repo gửi, `m28_incab_part00_meta.zip` và `m28_incab_part01_of_05.zip` … `part05_of_05.zip`): giải nén **tất cả vào cùng thư mục** `data\` rồi kiểm:
```bat
mkdir data
for %f in (m28_incab_part*.zip) do tar -xf "%f" -C data
python tool\check_manifest.py data\manifest.csv
```
(Gõ trực tiếp trong cmd dùng `%f`; viết trong file `.bat` thì `%%f`.) Hoặc từng dòng `tar -xf m28_incab_part00_meta.zip -C data`, `tar -xf m28_incab_part01_of_05.zip -C data`, … Phải in
`Kiểm manifest kiểu: in-cabin (YawDD + DrivFace)` rồi `manifest.csv đạt`; `data\crops\` có 616 ảnh `.png`. Gói **chỉ có ảnh cắt và manifest** (không có video, không có khung gốc);
`data\sources\NOTICE.txt` và `data\DOC.txt` ghi nguồn, điều khoản, cột manifest. Chỉ dùng nội bộ nhóm, không phát tán, không đưa vào báo cáo/slide công khai.

**b) Tự dựng lại gói (chỉ P1/chủ repo; cần video YawDD 5,3 GB và DrivFace 26 MB):**
```bat
mkdir D:\incab
curl -L -o D:\incab\user06.tar https://skuld.cs.umass.edu/traces/mmsys/2014/user06.tar
tar -xf D:\incab\user06.tar -C D:\incab
rem user06.tar giai ra D:\incab\user06\YawDD dataset.rar. Giai nen file rar nay bang 7-Zip ban moi hoac WinRAR vao D:\incab (ra thu muc D:\incab\YawDD dataset); tar -xf co the giai duoc rar: chua thu
curl -L -o D:\incab\drivface.zip https://archive.ics.uci.edu/static/public/378/drivface.zip
tar -xf D:\incab\drivface.zip -C D:\incab
mkdir D:\incab\DrivFace\imgs
tar -xf D:\incab\DrivFace\DrivImages.zip -C D:\incab\DrivFace\imgs
python tool\inc_ingest.py all --yawdd "D:\incab\YawDD dataset" --drivface D:\incab\DrivFace --model face_landmarker.task --out data --seed 5
```
`drivface.zip` giải ra thư mục `DrivFace\` có `DrivImages.zip` (ảnh), `drivPoints.txt`, `readme.txt`; hai lệnh `mkdir`/`tar` thứ hai đưa ảnh vào `DrivFace\imgs\DrivImages\*.jpg` (đúng chỗ `inc_ingest.py` tìm). Các lệnh `tar -xf` trên Windows này **chưa thử**.
Quét video chậm (10-20 phút trên CPU 4 nhân của cloud; máy Windows chưa đo); `inc_ingest.py scan` lưu cache nên chạy lại `split`/`pack` chỉ mất vài phút. Gói zip ra `data_parts\` (mỗi file <= 28 MiB).
Chi tiết, các cờ và luật tách người: `TAI-LIEU-CHI-TIET.md`, mục "Dữ liệu in-cabin".

## 5. Chạy thử trên 5 mặt (không cần CVAT, không cần token)
Chỉ cần gói dữ liệu ở mục 4a (**không** cần video hay khung gốc): `--images data\crops` dùng chính ảnh cắt. Cách nhanh nhất là `chay.bat`, chọn 3. Hoặc gõ tay: tạo danh sách 5 mặt F rồi chạy cả chuỗi ở chế độ chạy thử:
```bat
python -c "import csv;r=[x for x in csv.DictReader(open('data/manifest.csv',encoding='utf-8')) if x['set']=='F'][:5];w=csv.writer(open('data/f5_list.csv','w',newline=''));w.writerow(['image','face_idx','seed']);[w.writerow([x['image'],x['face_idx'],x['seed']]) for x in r]"
python tool\m28.py all --run F5 --list data\f5_list.csv --images data\crops --box crop --review auto --dry-run
```
Kết quả đúng: các bước `crop`, `mediapipe`, `map50`, `flags`, `autoqc`, `overlays` đều "xong", `push` in "Chạy thử (--dry-run)" rồi dừng,
và có `runs\F5\xml\prelabel.xml` (5 mặt × 50 điểm). Lần chạy này `low_conf` = 0 vì `t_flip` trong `config\m28_config.json` còn `null` (P2 chốt sau họp 12/10).
Lưu ý: 50 điểm là **định nghĩa DMS** (từ 7/10/2026, QĐ-003): lông mày trái/phải 5+5, sống mũi 4, mắt trái/phải 8+8, môi ngoài 12, môi trong 8; **không có viền hàm**. **Trái/phải theo bức ảnh** (`*trai` ở nửa trái ảnh, `*phai` ở nửa phải ảnh), ngược với bản cũ.
Điểm là các đỉnh MediaPipe chọn sẵn (`config\m28_config.json`, `mp_idx`); khi mặt quay quá ~30 độ, mắt, mày, môi phía xa cụm lại sát sống mũi (xem README, mục "50 điểm DMS trên đỉnh MediaPipe").
Nếu `runs\F5` còn từ lần chạy trước 7/10/2026 (50 điểm cũ, tên `p01_jaw_R`…), `m28.py` tự tính lại `map50 flags autoqc overlays` bằng config mới (giữ crop và MediaPipe) và in một dòng báo; XML của lượt đã đẩy lên CVAT (`push` đã xong) không bị ghi lại.
Để thấy điểm đỏ trên trang rà soát khi thử: mở `config\m28_config.json`, đổi `"t_flip": null` thành `"t_flip": 0.0357` (số đề xuất cho họp 12/10 trên 50 điểm DMS, chưa chốt; số 0,0464 cũ là của 50 điểm cũ, không dùng) rồi chạy lại các bước từ `flags`:
`python tool\m28.py prepare --run F5 --list data\f5_list.csv --images data\crops --box crop --force flags autoqc overlays`.
(Đừng commit file config sau khi sửa số này; hoàn lại bằng `git checkout config\m28_config.json`.)

## 6. Trang rà soát (giao diện trước khi nhập CVAT)
```bat
python tool\m28.py review --run F5 --reviewer P1 --force review
```
Trình duyệt tự mở http://127.0.0.1:7860 (chỉ máy bạn truy cập được). Chọn lý do **trước**, rồi bấm **Nhận (N) / Gán tay (G) / Bỏ ảnh (B)**; Hoàn tác (Z), ← → để chuyển mặt.
**Gán tay** đưa mặt lên CVAT ở job riêng **kèm nháp, mọi điểm đánh dấu low_conf**: kiểm kỹ từng điểm, giữ điểm đúng, sửa điểm sai (mặt không có nháp thì lên **ảnh trống**). Phân vân Nhận/Gán tay thì chọn Nhận.
**"Gán tay" trên trang rà soát khác điều kiện "gán tay" của thí nghiệm.** Nút Gán tay chỉ ảnh hưởng task `demo-…` do `m28.py push` tạo: mặt lên job riêng kèm nháp, mọi điểm low_conf. Thí nghiệm bấm giờ 14–15/10 dùng task `m28-manual` (không nháp) và `m28-assisted` khôi phục từ `backups\`, không đi qua nút này nên không đổi. Không dùng số đo trên task `demo-…` làm mốc "gán tay" của thí nghiệm.
Rà hết thì bấm **Xong** (trang tải lại, hiện dải xanh; sau đó vẫn Đẩy lên CVAT, xem Các đợt, xuất Ca khó được), xong việc bấm **Đóng trang rà soát** ở đầu trang rồi xác nhận để lệnh trong cmd đi tiếp. Kết quả nằm ở `runs\F5\review\triage_P1.csv`. Chỉ mở **một tab**. Không chia sẻ cổng này cho ai.
Không có Gradio hoặc trang lỗi: dùng `--review excel` (mở `runs\F5\autoqc\autoqc.csv` bằng Excel, điền cột `decision` = nhan / gan_tay / bo, lưu CSV UTF-8 thành `runs\F5\review\triage_P1.csv`).

### Có ảnh mới, chưa có lượt nào: kéo thả ảnh (tab Nạp ảnh)
Cần `face_landmarker.task` (mục 3, cùng thư mục chạy lệnh) và `config\m28_config.json`, `config\map_mp50.json`.
```bat
python tool\review_app.py --nap P1
```
Trình duyệt mở http://127.0.0.1:7860. Ở tab **Nạp ảnh**: kéo thả ảnh .jpg/.jpeg/.png (tối đa 25 MB mỗi ảnh, 200 ảnh mỗi lần) vào ô lớn, kiểm danh sách ảnh bị loại,
bấm **Nạp & Mở** (chờ thanh tiến độ xong, trang tự chuyển sang rà) hoặc **Nạp & Tiếp tục** (ở lại tab này; xong thì bấm **Rà lượt này** khi cần). Có nút Huỷ, Thử lại, không gõ lệnh nào.
Ảnh nằm ở `runs\NAP_001\inbox` (tên đã làm sạch; tên gốc ở `runs\NAP_001\nap_ten_goc.csv`, log ở `runs\NAP_001\nap_log.txt`). Đang rà dở lượt khác thì vẫn nạp được:
lượt cũ không bị đụng, mở lại bằng lệnh cmd in ra (ví dụ `python tool\review_app.py runs\F5 P1`). Ảnh mặt người thật chỉ xử lý trên máy bạn, không đưa vào chat AI.

### Ca khó: đánh dấu, xuất gói, họp team
**Thành viên:** khi rà gặp mặt khó (đổi chỗ điểm, lật, dồn cục, ca chưa có quy tắc, pain point công cụ) bấm **K** (hoặc nút **Ca khó**), chọn loại, ghi chú, **Lưu**; không ảnh hưởng Nhận/Gán tay/Bỏ.
Cuối ngày mở tab **Ca khó**, kiểm lại, bấm **Xuất gói họp**; file nằm ở `outputs\ca_kho\ca_kho_P1_1610.zip` (cũng tải về được từ trang). Gửi file này cho người tổ chức qua Drive riêng tư của đội
hoặc gửi trực tiếp. Không đăng công khai, không đưa vào chat AI, không commit. Lượt không rõ nguồn (có thể là ảnh khách hàng) mặc định không kèm ảnh: đừng bật ô kèm ảnh nếu chưa chắc.

**Người tổ chức (P5):**
```bat
python tool\review_app.py --nap P5
```
Mở tab **Họp team** (không cần lượt), bấm **Tạo phiên mới hôm nay**, kéo thả các gói zip, bấm **Nhập các gói**, họp (bấm thẻ để xem, **Trình chiếu** để chiếu), rồi **Xuất biên bản**.
Biên bản ở `outputs\ca_kho\hop_1610\bien_ban_1610.md`: **tự** chép các khối vào `problem-backlog.md` và `so-quyet-dinh.md` rồi commit hai file đó (trang không ghi vào hai file này).
Sau họp xoá các gói zip đã nhận nếu không cần nữa.

### Thống kê và lọc dữ liệu train
Hai việc này **chỉ đọc** `runs\`, `raw\`, `final\`, `data\` và chỉ ghi dưới `outputs\`. Cần nhãn sửa tay trong `raw\` (P4 `collect` hoặc `export.py`) và, cho mục tốc độ, các file `timing_P1.csv` … `timing_P5.csv` do `facetimer.py` ghi.

**Xem số liệu (tab Thống kê):** `chay.bat` mục 1 (hoặc `python tool\review_app.py --nap P5`), chọn tab **Thống kê**; bấm **Làm mới**; **Xuất CSV + HTML** ghi `outputs\thong_ke\<ngày-giờ>\`. Ttest ẩn mặc định (tập đo một lần). Nhãn thí nghiệm (`m28-manual`, `m28-assisted`) chỉ có nháp khi chọn ô **Lượt chứa nháp**.
```bat
python tool\thong_ke.py --luot-nhap <lượt chứa nháp của khối X> --timing .
```
Chỗ đặt `timing_P*.csv`: thư mục `source-tool\m28-prelabel\` (hoặc `outputs\`, `raw\`, `final\`); file `timing_*.csv` đã bị `.gitignore` chặn. Định dạng là 12 cột của `facetimer.py` (`date, person, condition, task, job, block, seq, face_id, seconds, warmup, interrupted, note`), không đặt định dạng mới; thiếu cột thì báo rõ tên cột.

**Lọc dữ liệu train (tab Lọc dữ liệu hoặc lệnh):** bắt đầu bằng xem trước, không ghi gì:
```bat
if not exist outputs mkdir outputs
copy config\loc_mau.json outputs\loc_cua_toi.json
python tool\loc_du_lieu.py --cau-hinh outputs\loc_cua_toi.json --dry-run
python tool\loc_du_lieu.py --cau-hinh outputs\loc_cua_toi.json --ten finetune_v1 [--zip]
```
Bảng `--dry-run` cho biết bao nhiêu mặt bị loại vì sao. Nếu một lượt chạy khi `t_flip` còn `null` thì mọi cờ của lượt = false: bộ lọc cảnh báo rõ, dùng `"co": {"nguon": "tinh_lai", "t_flip": 0.06}` để tính lại cờ. Gói ở `outputs\train_sets\finetune_v1\` (có `README.md` ghi giấy phép và trích dẫn).

**Cảnh báo dữ liệu nhạy cảm:** gói train chứa **ảnh mặt người lái xe thật** (YawDD, DrivFace: chỉ dùng học tập, nghiên cứu, phi thương mại). Chỉ gửi trong đội (Drive riêng tư), không đăng, không giao bên thứ ba, không commit (`outputs\` và `*.zip` đã bị `.gitignore` chặn), không đưa vào chat AI. Bản HTML của Thống kê không có ảnh mặt và không có mã tài xế nên đưa vào báo cáo được.

## 7. Nhập vào CVAT (khi đã có CVAT trên máy)
**Lưu ý: `push`, `collect`, xoá task và bảy label skeleton theo nhóm mới chỉ thử bằng CVAT giả, CHƯA thử trên CVAT thật.** Lần đầu chạy trên task thử `demo-…` và báo P4 nếu có lỗi.

Cài CVAT theo `de-tai-m28\huong-dan-chung.md` (mục cài CVAT), rồi cài SDK cùng bản với server và sinh file label:
```bat
python -m pip install cvat-sdk==2.77.0
python tool\make_label.py
```
**Project CVAT dựng bằng label cũ không dùng được** (label `face50` kiểu một skeleton: bản 50 điểm `pNN_vùng_bên` trước QĐ-003, hoặc bản đầu của DMS trước QĐ-004): `push` dừng và báo "label face50 CŨ", chưa tạo task nào. P4 dựng lại project (xoá project `m28` cũ rỗng trong CVAT rồi `push` tạo lại, hoặc project mới tên khác, đặt trong `config\pipeline.json`) bằng `config\face50_label.json` mới (bảy label skeleton, mỗi nhóm một: `longmaytrai`, `longmayphai`, `songmui`, `mattrai`, `matphai`, `moingoai`, `moitrong`; tổng 50 sublabel tên mới, 47 cạnh, màu theo nhóm). Khi gán tay trong CVAT, mỗi mặt vẽ bảy skeleton (mỗi nhóm một) thay vì một.
**Cách chính (từ trang rà soát):** mở trang → tab **Cài đặt** → dán link `http://localhost:8080` và token CVAT vào ô → **Lưu** → **Thử kết nối CVAT** (phải thấy "Kết nối được", bản 2.77.0, tên tài khoản).
Mặc định token chỉ nằm trong bộ nhớ của trang này. Bật **Nhớ trên máy này** thì token lưu ở `%APPDATA%\m28\cvat.json` (ngoài repo; Windows không có quyền 0600 thật, file dựa vào quyền hồ sơ của bạn). Ngày 24/10 bấm **Quên token** và thu hồi token trong CVAT.
Không dán token vào chat hay file trong repo.

**Phương án thay thế (bắt buộc cho `m28.py push/collect` chạy ở cmd; lệnh cmd KHÔNG đọc `cvat.json`):** đặt token trong biến môi trường, **trong cùng cửa sổ cmd sẽ chạy lệnh hoặc mở trang**; `set` chỉ có tác dụng trong cửa sổ đó;
`setx CVAT_ACCESS_TOKEN <token>` lưu lâu dài nhưng chỉ thấy ở cửa sổ cmd MỞ SAU đó (và để lại token trong máy: ngày 24/10 thu hồi token và xoá biến).
```bat
set CVAT_URL=http://localhost:8080
set CVAT_ACCESS_TOKEN=<dán token của bạn>
python tool\m28.py push --run F5 --reviewer P2 --task demo-F5
python tool\m28.py collect --task demo-F5 --reviewer P2
```
- **Từ trang rà soát:** mở trang (`python tool\review_app.py runs\F5 P2`), nhập link/token ở tab Cài đặt (hoặc mở từ cửa sổ cmd đã `set`). Rà hết mặt thì nút **Đẩy lên CVAT** (dưới nút Xong) bật; bấm → hộp xác nhận (nút Huỷ là mặc định, Esc = Huỷ) → Đẩy.
  Thiếu link/token (tab Cài đặt hoặc biến môi trường) thì nút khoá và trang nhắc mở tab Cài đặt (hoặc lệnh `set`). Ô nhập token chỉ nằm ở tab Cài đặt.
- **Lần push dở** (mất mạng, nhập nhãn lỗi): `python tool\m28.py push --run F5 --resume` làm nốt trên đúng task đã tạo, hoặc `python tool\m28.py push --run F5 --cleanup --confirm-name demo-F5` để xoá task dở rồi đẩy lại.
  Sau khi `push` xong, gõ lại `push`/`all` ở cmd chỉ in "bỏ qua push" (đã ghi `runs\F5\push\done.txt`).
- **`collect`** chỉ xuất nhãn về `raw\<task>_<người>_<ngàyDDMM>.xml` (không ghi đè) và lập `outputs\collect_<task>.md`; luôn thêm `--reviewer P<số của bạn>`. `--skip-export` chỉ đọc `raw\`; `--dry-run` chỉ liệt kê job.
- **Tab Các đợt**: xem các lượt đã nạp (thẻ: ngày, ghi chú, số ảnh, Nhận/Gán tay/Bỏ/Chưa rà, trạng thái), xem lưới ảnh, xoá ảnh (rê chuột lên ảnh, bấm thùng rác), khôi phục, xoá cả đợt.
- **CẢNH BÁO khi xoá:**
  - Xoá ảnh hoặc đợt ở trang là **xoá mềm, chỉ trên máy bạn** (thùng rác `runs\<lượt>\_trash`, `runs\_trash`; khôi phục được). Nó **không xoá gì trên CVAT**: ảnh đã đẩy vẫn nằm trong task `demo-…`.
  - **Dọn thùng rác** và **Xoá vĩnh viễn** là xoá thật, không khôi phục được.
  - **Xoá task trên CVAT** (nút ở khu CVAT của đợt đã đẩy) **không hoàn tác được và mất cả nhãn đã sửa trong CVAT**: chạy `collect` trước. Hộp xác nhận bắt gõ lại đúng tên task và tick ô "Tôi hiểu…". Chỉ xoá được task do chính tool tạo (`demo-…` ghi trong `push.json`); không bao giờ task `m28-`.
Chỉ tạo task bắt đầu bằng `demo-`; không bao giờ chạy trên task `m28-`.

### Kiểm tra nhanh trước lần push đầu tiên
Làm một lần trên máy có CVAT, trước khi đẩy ảnh thật (mất khoảng 1-2 phút):
1. Bật CVAT (Ubuntu WSL: `docker compose up -d`, chờ 1-2 phút).
2. Đưa token cho tool: **Lưu** token ở tab Cài đặt và bật **Nhớ trên máy này** (để lệnh cmd cũng thấy), hoặc `set CVAT_URL=http://localhost:8080` và `set CVAT_ACCESS_TOKEN=<token>` trong cùng cửa sổ cmd. Không dán token vào chat hay file.
3. Chạy `python tool\cvat_smoke.py` (hoặc menu `chay.bat` mục "Kiem tra nhanh CVAT", hoặc nút **Chạy kiểm tra nhanh CVAT** ở tab Cài đặt). Tool tạo task `demo-smoke` từ 4 ảnh xám giả (không phải ảnh mặt), nhập nhãn nháp, xuất lại, kiểm, rồi **xoá task đó** (và project m28 nếu chính nó vừa tạo). Không đụng task nào khác. `--dry-run` chỉ kiểm cục bộ, không cần CVAT.
4. Đọc bảng cuối: `ĐẠT` là ổn; `HỎNG` kèm nguyên nhân tiếng Việt ở cột Ghi chú; `BỎ QUA` là bước không chạy vì bước trước hỏng hoặc vì bạn chọn cờ. Dòng cuối là `Tất cả ĐẠT` hoặc `Có N bước HỎNG`.
5. Muốn nhìn tận mắt: `python tool\cvat_smoke.py --giu-task`, mở link task in ra trong CVAT, kiểm 50 điểm, các cạnh và ô `low_conf`; lần chạy sau tự xoá task đó.
6. Có `HỎNG`: gửi P4 file `runs\_smoke\bao_cao_<giờ>.txt` (không gửi token, không gửi ảnh). Đừng tự xoá `runs\_smoke\dang_mo.json` trừ khi đã xoá task `demo-smoke` tay trong CVAT.

## 8. Chạy test và báo lỗi
```bat
python -m pytest tests -q
```
Trên máy Windows của chủ repo (7/10/2026, Python 3.14.7) ra `666 passed, 3 skipped` và **11 lỗi có sẵn do Windows** (tạo symlink cần quyền, đường dẫn/CRLF của vài bài test; không do M28): đừng coi 11 lỗi đó là hỏng, chỉ cần không có lỗi MỚI. Test chỉ dùng dữ liệu giả, không cần ảnh mặt thật hay mạng. Từ 8/10/2026 có thêm test cho bảng mặt, bộ lọc và Thống kê (`test_bang_mat.py`, `test_loc_du_lieu.py`, `test_thong_ke.py`, `test_toc_do.py`, `test_thong_ke_ui.py`: 122 test); số qua phải **không ít hơn** số lúc bạn đo gốc trước khi `git pull`.

| Triệu chứng | Cách xử lý |
|---|---|
| `Python ... bị chặn` / lỗi 4551 / DLL bị chặn (Smart App Control, antivirus) | Không tắt bảo mật. Thử cài Python từ python.org (không dùng Store), thêm thư mục dự án vào ngoại lệ của antivirus, hoặc dùng Python 3.12; còn kẹt thì báo P1/P2 |
| `UnicodeEncodeError` khi chuyển hướng ra file | `set PYTHONUTF8=1` rồi chạy lại |
| `Cổng 7860 bận` | Đã có bản trang rà soát đang chạy: đóng nó, hoặc `set GRADIO_SERVER_PORT=7861` |
| Trình duyệt không tự mở | `set M28_NO_BROWSER=1` rồi tự mở http://127.0.0.1:7860 |
| `Thiếu file config\...` / `Thiếu m28core.push` | Chưa `git pull`, hoặc phần đó là của P4 chưa commit |
| `không đọc được ảnh` ở bước crop | Sai `--images`: phải trỏ tới `data\frames` (khung gốc) hoặc `data\crops` (chỉ có gói, kèm `--box crop`) |
| `import mediapipe` lỗi | Python 3.14 chưa hỗ trợ trên máy bạn: tạo lại venv bằng `py -3.12`; ghi lại phiên bản và báo P2 |

Khi báo lỗi gửi: bản Windows (`winver`), `python --version`, lệnh đã gõ và 10 dòng cuối của `runs\<run>\log.txt`. **Không** gửi ảnh mặt, `gt98.json`, file xuất CVAT hay token.
