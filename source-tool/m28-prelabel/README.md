# m28-prelabel

**Giải quyết:** gán 50 điểm landmark khuôn mặt từ đầu trong CVAT rất chậm và dễ lệch giữa người với người.
Chưa có mục P-xxx trong [`problem-backlog.md`](../../problem-backlog.md) (file đang trống); khi ghi thì thêm link vào đây.
Kế hoạch đầy đủ của đề tài M28: [`de-tai-m28/`](../../de-tai-m28/).

## Pain point
Gán tay 50 điểm cho mỗi mặt trong CVAT: mất vài phút/mặt (50 lần kéo điểm), dễ đổi chỗ trái/phải, và hai người gán
cùng một mặt ra hai kết quả khác nhau. Đội đo thời gian thật bằng thí nghiệm ghép cặp 14–15/10/2026 (gán tay so với
sửa nhãn nháp, trên cùng khuôn mặt); mục tiêu là nhanh hơn ≥ 20% mà nhãn không kém đi.

## Tool làm gì
`tool/m28.py` đặt sẵn 50 điểm lên ảnh mặt tài xế bằng MediaPipe Face Landmarker (chạy offline trên CPU), cho một người
rà nháp trên trang Gradio chỉ mở ở 127.0.0.1, rồi nhập nhãn nháp vào CVAT để người chỉ kiểm và sửa.

| Lệnh | Làm gì |
|---|---|
| `prepare` | Cắt mặt, chạy MediaPipe, đổi 478 → 50 điểm, gắn cờ `low_conf`, tự kiểm, vẽ ảnh chồng |
| `review` | Trang rà soát: mỗi mặt bấm **Nhận / Gán tay / Bỏ ảnh** |
| `push` | Tạo task CVAT mới `demo-…` và nhập nhãn nháp đúng một lần |
| `collect` | Sau khi gán: xuất nhãn từ CVAT về `raw/` (chỉ đọc); với task `demo-…` còn tách nhãn theo từng job ra `raw/<task>_<người>_<DDMM>_job<id>.xml` (offline; file job chỉ để đọc/đo, không nhập lại vào CVAT). Tách file đã xuất từ trước: `python tool/tach_job.py --xml raw/<file>.xml` |
| `all` | `prepare` → `review` → `push` |

### Đồng hồ bấm giờ, Thống kê ba chỉ số và tổng kết cho nhóm trưởng (09/10/2026, QĐ-006)
Thí nghiệm chia **hai nhóm độc lập**: `manual` (gán tay hoàn toàn) và `assisted` (dùng tool, sửa nháp), cùng một bộ ảnh; nhóm ghi ở `config/nhom_thi_nghiem.json` (file mẫu trống, đội tự điền).

| Việc | Ở đâu | Làm gì |
|---|---|---|
| Bấm giờ | tab **Đồng hồ** (thay `facetimer.py`) | Bắt đầu (hoặc bấm gợi ý sau khi nạp ảnh xong), Tạm dừng/Tiếp tục, Hủy (gõ HUY), **Xong (lưu & xuất)**. Đo cả **phiên**; bấm từng mặt chỉ là tuỳ chọn. Ghi `outputs/timing/timing_<Pk>.csv` (12 cột đầu đúng facetimer, cột thêm cuối) và gói kết quả `outputs/ket_qua/ketqua_<Pk>_<DDMM>_<đợt>.zip` (+ `.json`, không ảnh) để **gửi nhóm trưởng**. |
| Thống kê | tab **Thống kê**, `python tool/thong_ke.py` | Chỉ **ba chỉ số**: NME của nháp so với nhãn manual, tỉ lệ điểm phải sửa (nhóm assisted), so sánh thời gian manual với assisted (KTC 90% bằng cluster bootstrap). |
| Tổng kết | `python tool/tong_ket.py --vao <thư mục chứa các gói> --ra outputs/tong_ket/` | Của nhóm trưởng: gộp gói của thành viên (kiểm sha256, loại gói hỏng/trùng), cùng ba chỉ số, CSV + HTML tĩnh. Không cần ảnh hay CVAT. |

Giới hạn: tốc độ từng người lẫn vào kết quả (thiết kế hai nhóm); giây/mặt là ước lượng chia đều nếu không bấm từng mặt; chưa thử với nhãn xuất thật từ CVAT, giờ thật buổi 14–15/10, Windows/cmd. Chi tiết: [`TAI-LIEU-CHI-TIET.md`](TAI-LIEU-CHI-TIET.md), mục "Đồng hồ, gói kết quả, Thống kê ba chỉ số".

### Lọc dữ liệu train (08/10/2026, QĐ-005)
Hai việc đọc dữ liệu đã có (không sửa `runs\`, `raw\`, `final\`, `data\`), có cả lệnh và tab trong trang rà soát:

| Lệnh | Tab | Làm gì |
|---|---|---|
| `python tool\thong_ke.py [--luot-nhap <lượt>] [--nguong-sua 2] [--gom-ttest] [--timing <thư mục>] [--goi <thư mục>]` | **Thống kê** | Ba chỉ số của thí nghiệm hai nhóm (xem mục trên; từ QĐ-006 trang không còn cờ `low_conf`, số lượng, tiến độ, giây rà). Ghi `outputs\thong_ke\<ngày-giờ>\`: `thong_ke.html` (không ảnh mặt, không mã tài xế) + CSV từng bảng + `nme_nhap.csv` |
| `python tool\loc_du_lieu.py --cau-hinh config\loc_mau.json [--dry-run] [--ten T] [--ghi-de] [--zip]` | **Lọc dữ liệu** | Lọc ảnh đã có nhãn sửa tay thành bộ train/val/test (cho một model landmark KHÁC sau này; **chỉ chuẩn bị dữ liệu, không train**). Tiêu chí: cờ `low_conf` (tổng, theo nhóm, theo vùng), NME nháp, cờ manifest, quyết định rà, vệ sinh nhãn. Chia theo `set` gốc rồi kiểm không tài xế nào ở hai phần. Ghi `outputs\train_sets\<tên>\` |

- **Vào:** gói kết quả (`outputs\ket_qua\`, `outputs\goi_nhom\`), nhãn sửa tay `raw\<task>_<Pk>_<DDMM>.xml` (`final\` chỉ cho Lọc dữ liệu), `outputs\timing\timing_P*.csv` của tab Đồng hồ (hay `timing_P*.csv` của `facetimer.py`), `runs\<lượt>\` (nháp), `data\manifest.csv`, `config\nhom_thi_nghiem.json`. Chưa có thứ nào thì mục tương ứng hiện trạng thái trống nói rõ cần file gì, ai làm ra (không hiện số 0 hay số giả).
- **Luật cứng của bộ lọc:** mặt nguồn không rõ (lượt Nạp ảnh, có thể là ảnh khách hàng), mặt xoá mềm, mặt chưa có nhãn sửa tay, mặt `Bỏ` luôn bị loại. Gói xuất chứa ảnh mặt người lái xe: chỉ dùng nội bộ nhóm, không git, không chat AI.
- **Giới hạn:** chưa thử với nhãn bảy skeleton xuất thật từ CVAT, file bấm giờ thật (14–15/10), `final\`, lượt `--box auto` có ảnh gốc khác tên; tab chưa được chụp trên Windows thật. Chi tiết cách tính từng số: [`TAI-LIEU-CHI-TIET.md`](TAI-LIEU-CHI-TIET.md), mục "Thống kê và lọc dữ liệu train".

## Cài đặt và chạy
Windows (cmd, Python 3.14), từ thư mục `source-tool\m28-prelabel`:
```bat
py -3.14 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
curl -L -o face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
python tool\m28.py all --run thuP1 --list data\f5_list.csv --images data\crops --box crop --review auto --task demo-thuP1
```
Ubuntu: dùng `chay.sh` và [`HUONG-DAN-UBUNTU.md`](HUONG-DAN-UBUNTU.md); Windows từng bước: [`HUONG-DAN-WINDOWS.md`](HUONG-DAN-WINDOWS.md).

Đăng nhập CVAT bằng Personal Access Token trong biến môi trường `CVAT_ACCESS_TOKEN` và địa chỉ trong `CVAT_URL`
(hoặc nhập ở tab Cài đặt của trang rà soát). Không ghi token vào code, repo hay chat. `push --dry-run` không cần token.

## Đầu vào / đầu ra
- Vào: ảnh mặt (khung gốc hoặc ảnh cắt 512) và danh sách `image,face_idx` như `data/manifest.csv`; `config/m28_config.json`
  (định nghĩa 50 điểm, nguồn duy nhất cho CVAT, ánh xạ và đánh giá).
- Ra: `runs/<run>/…` (ảnh chồng, cờ, quyết định rà soát, `push/manual_list.txt`), task CVAT `demo-…` có nhãn nháp,
  và sau khi gán: `raw/<task>_<Pk>_<ngày>.xml` (CVAT for images 1.1).
- Nhập vào CVAT: `push` tự nhập; nhãn nháp là bảy skeleton theo nhóm (mày trái/phải, sống mũi, mắt trái/phải, môi ngoài/trong),
  mỗi điểm có thuộc tính `low_conf`.

## Đã thử trên
- 616 mặt in-cabin thật (YawDD + DrivFace, gói `data/crops`, 7/10/2026): `prepare`, `review --review auto`,
  `push --dry-run`, `eval50.py`, ra XML đủ 50 điểm/mặt đúng tên và đúng thứ tự.
- Trang rà soát: Gradio 6.29.1 trên Chromium headless, 616 mặt, mỗi quyết định trung vị 0,11 giây.
- Bộ test trong `tests/` (CVAT giả).
- **Chưa thử:** `push` và `collect` trên **CVAT thật** v2.77.0 (kể cả nhập XML skeleton), Windows/cmd thật, Python 3.14.
- **Chưa có:** số đo thời gian trước/sau và số nháp hỏng bắt được; sẽ cập nhật sau thí nghiệm 14–15/10.

## Giới hạn
- Chỉ làm nháp cho mặt lớn nhất trong ảnh; ảnh nhiều người chọn "Gán tay".
- MediaPipe yếu với mặt nhỏ, nghiêng mạnh, bị che nhiều: người rà vẫn phải kiểm từng mặt, nhất là điểm `low_conf`.
- Trang rà soát không có công cụ kéo điểm; sửa điểm làm trong CVAT.
- Ảnh người lái xe là dữ liệu nhạy cảm: không commit, không đăng, không đưa vào chat AI ngoài phiên được phép.
- Lượt chạy theo 50 điểm cũ (config version 2) không dùng được với config version 3.

Chi tiết (định nghĩa 50 điểm, dữ liệu, cờ, trang rà soát, `push`/`collect`, rủi ro CVAT thật, mọi số đo):
[`TAI-LIEU-CHI-TIET.md`](TAI-LIEU-CHI-TIET.md).

## Người viết
Vũ Tùng Lâm
