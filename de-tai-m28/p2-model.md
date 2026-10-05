# P2 – Model và cờ

Bạn chạy hai model đặt sẵn điểm (MediaPipe và PIPNet) trên mọi ảnh cắt. Bạn làm cờ low\_conf (đánh dấu điểm nên nhìn kỹ), bảng ảnh chồng cho buổi xem chéo và trang rà soát trước khi nhập CVAT (phần mentor muốn thấy). Trong dự án thật, MediaPipe (Apache-2.0) chạy offline trên CPU nên giao được. Cờ giúp người kiểm tra ít bỏ sót điểm sai.

## Bạn nhận gì và giao gì

| Ngày | Nhận từ ai, cái gì | Giao cho ai, cái gì |
| --- | --- | --- |
| 5/10 | P4: bản CVAT nhóm chốt (2.77.0) | Cả nhóm: venv chung, requirements.txt, face\_landmarker.task; `requirements-ui.txt` nếu Gradio cài được (không thì báo dùng `--review excel`) |
| 6/10 | P1: 616 ảnh cắt 512, manifest.csv | P3: predictions.json phần MediaPipe (gốc + lật, no\_face) |
| 7/10 | P1: phép biến đổi cắt, gt98; 2 file tar WFLW gốc trong MyDrive/M28/ | P3: predictions.json thêm PIPNet 98 điểm |
| 8/10 | P3: mp50.json (từ 7/10, gốc + lật đã bỏ lật), gt50.json, config, eval50.py bản nháp có point\_errors (lỗi từng điểm). Điểm PIPNet 50 bạn tự lấy theo cột wflw | — |
| 9/10 | `backups/P2/`: `m28-gold-x` (G2), `m28-gold-y` (G3), khôi phục trên CVAT của bạn | Repo: `raw/m28-gold-x_P2_0910.xml`, `raw/m28-gold-y_P2_0910.xml` (tự xuất). P1 (đầu buổi): `run_mp`, code cờ lật (dời từ 19/10) |
| 10/10 | P3: sai số chấp nhận theo vùng (đầu buổi) | Repo (commit; P4 dựng backup từ đây): flags.json cho X, D. P1: ngưỡng cờ, offset.npy. P5: số liệu cờ |
| 11/10 | P5: `guideline_triage.md` (mã lý do cho nút bấm) | P1: `detect_face()` (`tool/m28core/detect.py`) |
| 12/10 | — | Họp điểm dừng: số liệu cờ. Cả nhóm: overlay.py. Repo (commit ngay sau họp, trước khi P1 gắn tag và P4 dựng backup tuần 2; nếu họp chọn t\_flip): flags.json mới cho X, D; nếu họp chọn PIPNet: pip50.json cho X, D |
| 13–15/10 | `backups/P2/`: m28-practice (D\_05–D\_08, 13/10), m28-assisted (X3, 14/10), m28-manual (X2, 15/10), khôi phục đầu mỗi buổi; P4: `autoqc.py` (13/10, dùng từ bản 2) | Repo: `raw/<task>_P2_<ngày>.xml` (tự xuất cuối khối). P5: timing\_P2.csv, gửi ngày 17/10. P1 (13/10): `review_app.py` bản 1 |
| 16/10 | P4 (lệnh `collect --skip-export` trên `raw/` cả nhóm đã commit, đầu buổi): CSV QC, bảng ảnh chồng; `outputs/review_1610/P5.csv` (mặt P5 gán, bạn xem) | P4: tên mặt đáng ngờ từ bảng ảnh chồng. Cả nhóm: mã lỗi xem chéo, `review_app.py` bản 2 |
| 17/10 | P4 (người xem mặt của bạn): mã lỗi trong `outputs/review_1610/P2.csv`. P5 (đầu buổi): lỗi trang rà soát khi rà R1610 | Repo: `final/m28-manual_P2_1710.xml`, `final/m28-assisted_P2_1710.xml` (tự xuất lần 2). Cả nhóm: bản sửa trang rà soát (trước demo 18/10) |
| 19–21/10 | P3: kết quả T-test (chạy 1 lần). Ảnh gốc T-test: bản WFLW bạn đã tải ngày 11/10, theo cột wflw\_image của manifest.csv | P5: bảng theo thuộc tính, chênh lệch khung tự dò, kết quả cờ T-test. P1 (19/10): tỉ lệ dò mặt trên T-test (cho README) |
| 22–24/10 | P5: khung báo cáo, slide | P5: phần "Model và cờ". P1: script, ghi chú README, mục "Trang rà soát" |

## Lịch của bạn

**T2 5/10**

- [ ] Dựng venv chung Python 3.14 (mediapipe 1.0.1, torch CPU, cvat-sdk và cvat-cli 2.77.0), chạy lại test M24 — chạy ở Máy mình — ra requirements.txt trong repo — xong khi test M24 qua và lệnh kiểm in 1.0.1. Lúc báo cuối buổi, đăng thêm (chỉ chữ): bản Windows (`winver`), RAM, ổ C còn trống, dòng Virtualization trong Task Manager.
- [ ] Chạy FaceLandmarker trên 1 ảnh — chạy ở Máy mình — ra ảnh vẽ điểm — xong khi đủ 478 điểm.
- [ ] (giờ thứ hai) Thử trang rà soát trong `.venv` chung, sau khi đã `pip freeze > requirements.txt`: tạo `requirements-ui.txt` (gradio); chạy `python -m pip install --dry-run -r requirements-ui.txt` để xem gói nào sẽ bị đổi; không có numpy, pillow, opencv bị đổi thì cài thật, rồi ghi đúng bản đã cài vào `requirements-ui.txt` thành `gradio==<bản>` (xem bằng `pip show gradio`, ví dụ 6.29.1) để ngày 16/10 cả nhóm cài đúng bản đã thử; chạy app 5 dòng với `launch(server_name="127.0.0.1", share=False)` — chạy ở Máy mình — ra `requirements-ui.txt` — xong khi trang mở ở http://127.0.0.1:7860 và đoạn chạy FaceLandmarker trên 1 ảnh của tối nay vẫn in 1.0.1, 478 (`check_mp.py` đọc `data/X1_01.png`, chỉ có từ 6/10; chạy nó đầu buổi 6/10). Hỏng thì xoá `.venv`, dựng lại từ `requirements.txt`, báo cả nhóm dùng `--review excel`.

**T3 6/10**

- [ ] MediaPipe trên 616 ảnh cắt, gốc + lật, ghi no\_face — chạy ở Máy mình — ra predictions.json (mục mediapipe) — xong khi đủ 616 mục và đã báo P3 số no\_face.
- [ ] (trong lúc MediaPipe chạy) Cài CVAT phần A bước 1–2 (tab chung): kiểm máy, `wsl --install` (tải chạy nền); khởi động lại máy sau buổi, tạo user Ubuntu đầu buổi 7/10 — chạy ở Máy mình — ra WSL2 + Ubuntu — xong khi `wsl -l -v` thấy Ubuntu ở VERSION 2.
- [ ] (giờ thứ hai) Chuẩn bị PIPNet (dời từ 7/10): tải trọng số torchlm, chép networks.py, meanface — chạy ở Máy mình — ra thư mục `pipnet/` — xong khi nạp trọng số không lỗi.

**T4 7/10**

- [ ] PIPNet trên 616 ảnh, gốc + lật, không biên dịch (trọng số và networks.py đã chuẩn bị 6/10) — chạy ở Máy mình — ra predictions.json (mục pipnet) — xong khi NME 98 điểm trên T-dev gần 4,6%.

**T5 8/10**

- [ ] Đọc mp50.json (P3 đã bỏ lật); chọn 50 trong 98 điểm PIPNet theo cột wflw của config; tính điểm cờ trên T-dev với sai số tạm 3% IOD — chạy ở Máy mình — ra flag\_tdev.csv — xong khi có cờ/mặt, % bắt, AUROC theo vùng.
- [ ] Cài CVAT phần B (tab chung); để `docker compose up -d` tải ảnh (khoảng 1,5 GB) chạy nền trong lúc tính điểm cờ — chạy ở Máy mình — ra CVAT v2.77.0 ở `http://localhost:8080`, token trong biến môi trường — xong khi `python -m cvat_cli task ls` chạy không lỗi. Máy 8 GB: đừng chạy PIPNet hay torch cùng lúc với CVAT.

**T6 9/10**

- [ ] Đầu buổi commit `run_mp` và code cờ lật (đã viết 6/10; dời từ 19/10), báo P1 — chạy ở Máy mình (repo) — ra commit, tin báo P1 — xong khi P1 gọi được `run_mp` từ m28.py.
- [ ] Đầu khối khôi phục `backups\P2\m28-gold-x.zip` và `backups\P2\m28-gold-y.zip`; gán tay G2 (m28-gold-x) và G3 (m28-gold-y), 8 mặt — chạy ở CVAT trên máy mình — ra 8 mặt đủ 50 điểm, `raw/m28-gold-x_P2_0910.xml`, `raw/m28-gold-y_P2_0910.xml` — xong khi đã xuất bằng `export.py` và commit trong tối nay (P3 dùng đầu buổi 10/10). Trước 10/10 khôi phục thử `backups\all\m28-check.zip` (tab chung, bước 12).

**T7 10/10**

- [ ] Chọn ngưỡng để cờ ≤ 15% số điểm (\~7 điểm/mặt; ngưỡng không cần sai số nên làm ngay đầu buổi), rồi ở giờ thứ hai tính lại % bắt và AUROC với sai số P3 commit đầu buổi — chạy ở Máy mình — ra ngưỡng t (cờ gộp, cho thí nghiệm), ngưỡng t\_flip = np.quantile(d\_flip, 0.85) (chỉ lệch lật MediaPipe, cho công cụ giao đi; cũng cờ ≤ 15% số điểm); gửi t và t\_flip cho P1 ghi vào config; offset.npy để trong outputs/, chỉ dùng cho thí nghiệm — xong khi đã ghi % bắt và AUROC.
- [ ] Ghi cờ cho 50 mặt X và 30 mặt D — chạy ở Máy mình — ra flags.json commit vào repo (P4 dựng backup từ file này) — xong khi P4 đọc được đủ 80 mặt.

**CN 11/10** (khung chung 2 tiếng)

- [ ] Tải WFLW từ MyDrive/M28/ về máy nếu chưa có (có từ 7/10; khoảng 10 phút, phần lớn là chờ). Viết `detect_face()` (dời từ 19/10, code mẫu cuối tab): FaceLandmarker trên cả ảnh gốc, `num_faces=5`, chọn mặt lớn nhất, hộp = khung bao 478 điểm, không thấy mặt thì trả None — chạy ở Máy mình — ra `tool/m28core/detect.py` — xong khi 5 ảnh gốc F ra hộp đúng mặt; báo P1.
- [ ] Khung trang rà soát `tool/review_app.py` với 5 ảnh giả (chấm màu trên nền trắng): lưới ảnh, bấm ảnh xem lớn, 3 nút Nhận / Gán tay / Bỏ ảnh và ô lý do, ghi CSV — chạy ở Máy mình — ra `review_app.py` bản nháp — xong khi bấm 5 ảnh giả ra CSV 5 dòng.

**T2 12/10**

- [ ] 20 phút đầu: họp điểm dừng (P5 chủ trì) — chạy ở họp nhóm — ra số liệu cờ và số no\_face đã trình bày — xong khi P5 ghi kết luận.
- [ ] Nếu họp chọn cờ `t_flip` cho nháp X, D: ghi lại `flags.json` bằng `t_flip` ngay sau họp (code có sẵn) và commit ngay (trước phút 45), trước khi P1 gắn tag (trước phút 60) và P4 dựng backup tuần 2 (từ phút 65) — chạy ở Máy mình — ra `flags.json` mới — xong khi P4 đọc được đủ 80 mặt.
- [ ] Viết overlay.py, thử trên file xuất G — chạy ở Máy mình — ra 1 bảng PNG cho 1 job — xong khi đọc rõ số điểm trên laptop.

**T3 13/10**

- [ ] Đầu buổi khôi phục `backups\P2\m28-practice.zip` (D\_05–D\_08); làm quen 4 mặt D (3 có nhãn nháp, 1 gán tay), thử facetimer.py — chạy ở CVAT trên máy mình — ra 4 mặt đã lưu, 4 dòng timing, `raw/m28-practice_P2_1310.xml` — xong khi đã tự xuất và commit (P4 chạy QC trên file này).
- [ ] (giờ thứ hai, sau buổi làm quen) Trang rà soát bản 1 (`review_app.py`, code mẫu cuối tab):
  1. Đọc `runs/<run>/`: ảnh chồng, cờ, và gợi ý trong `autoqc.csv` nếu đã có (chưa có thì xếp theo số cờ). Mặt đáng ngờ lên đầu.
  2. Ba nút Nhận / Gán tay / Bỏ ảnh; ô lý do dùng mã trong `guideline_triage.md` của P5.
  3. Ghi `runs/<run>/review/triage_<Pk>.csv`; cột đầu là tên file ảnh thật.

  Thử trên 5 mặt `runs/F5/`, rồi trên 30 mặt D. Tạo lượt chạy D bằng `python tool\m28.py prepare --run D30 --list data\manifest.csv --set D --images <WFLW_images> --box wflw`. Chỉ chạy trên Máy mình, không chạy trên Colab/Kaggle — ra `review_app.py` bản 1 — xong khi `triage_P2.csv` có đủ dòng; báo P1.

**T4 14/10**

- [ ] Lượt 1: đầu buổi khôi phục `backups\P2\m28-assisted.zip` (X3, có nháp), rồi mới bật facetimer; sửa nhãn nháp X3 — chạy ở CVAT trên máy mình — ra 10 mặt, 10 dòng timing, `raw/m28-assisted_P2_1410.xml` — xong khi đã tự xuất và commit trước phần sau của buổi.

**T5 15/10**

- [ ] Lượt 2: đầu buổi khôi phục `backups\P2\m28-manual.zip` (X2, không nháp), rồi mới bật facetimer; gán tay X2 — chạy ở CVAT trên máy mình — ra 10 mặt, 10 dòng timing, `raw/m28-manual_P2_1510.xml` — xong khi đã tự xuất và commit.

Quy tắc buổi X: đọc câu chung đầu buổi. Enter = xong mặt, p = tạm dừng. Làm trọn khối trong 1 buổi. Không mở đáp án, ảnh chồng hay flags.json. Xem mọi điểm; cờ chỉ để nhắc.

**T6 16/10**

- [ ] Bù buổi lỡ nếu có. Đầu buổi (khoảng phút 15, sau khi P4 chạy `collect` ngay đầu buổi) `git pull` khi P4 báo đã commit `outputs/collect_1610/`, rồi quét 10 bảng ảnh chồng do collect vẽ (overlay.py của bạn chạy bên trong collect; chưa có thì tự chạy overlay.py trên raw/ như cũ), mỗi mặt khoảng 10 giây, gửi P4 tên mặt đáng ngờ — chạy ở Máy mình — ra danh sách mặt đáng ngờ — xong khi P4 đã thêm vào danh sách xem chéo.
- [ ] Xem chéo mặt của P5 trong `outputs/review_1610/P5.csv` (mặt bị QC hoặc bảng ảnh chồng đánh dấu, thêm 1 mặt ngẫu nhiên mỗi task) trên bảng ảnh chồng và ảnh cắt — chạy ở Máy mình — ra mã lỗi theo điểm (SWAP, MIRROR, COLLAPSE, MISPLACED, OCC\_FLAG, RULE) trong file đó, đã commit — xong khi xem hết mặt trong file.
- [ ] (giờ thứ hai) Trang rà soát bản 2 — chạy ở Máy mình — ra `review_app.py` bản 2 — xong khi rà trọn 30 mặt D, đóng giữa chừng rồi mở lại vẫn đúng mặt; báo P1, P5. Thêm:
  - Nút **Xong** ghi `runs/<run>/review/done.txt` (đúng file `m28.py` dùng để biết bước rà đã xong).
  - Mở lại thì làm tiếp từ CSV, bỏ qua mặt đã rà.
  - Cột số giây: thời gian giữa hai lần bấm.
  - An toàn: đặt `GRADIO_ANALYTICS_ENABLED=False` (tắt gửi thống kê) và `GRADIO_TEMP_DIR=runs/<run>/_tmp` (ảnh tạm nằm trong runs/) trước khi `import gradio`; chạy trong Colab/Kaggle thì thoát ngay.

**T7 17/10**

- [ ] Sửa lỗi ghi trong `outputs/review_1610/P2.csv` trên X2, X3 của bạn, ghi "đã sửa" — chạy ở CVAT trên máy mình — ra số lỗi đã sửa, `final/m28-manual_P2_1710.xml`, `final/m28-assisted_P2_1710.xml` (`export.py … --final`) — xong khi hết lỗi mở và 2 file đã lên repo.
- [ ] (giờ thứ hai) Sửa lỗi trang rà soát P5 báo khi rà R1610 đầu buổi; viết 5 dòng hướng dẫn dùng trong README — chạy ở Máy mình — ra commit — xong khi lỗi đã sửa trước demo 18/10. P5 không chờ bạn: lỗi chặn thì P5 rà bằng `--review excel`.

**CN 18/10** (khung chung 2 tiếng)

- [ ] Trình phần trang rà soát trong demo cho mentor (khoảng 10 trong 30 phút); ghi góp ý về trang rà soát — chạy ở họp — xong khi mentor đã xem. Phần còn lại là dự phòng.

**T2 19/10**

- [ ] Hàm lấy hộp `detect_face()` đã viết ngày CN 11/10 (FaceLandmarker trên cả ảnh gốc, num\_faces=5); hôm nay chỉ chạy đo. Khi đo T-test: chọn mặt có tâm gần tâm hộp WFLW nhất. Trong công cụ của P1 (ảnh khách hàng không có hộp WFLW): chọn mặt lớn nhất, ghi cách chọn vào README. Hộp = khung bao 478 điểm, đưa thẳng vào square\_crop của P1 (hàm đã nới 1,4 lần, không nhân thêm). Chạy lại 100 mặt T-test — chạy ở Máy mình — ra predictions\_ttest\_detbox.json — xong khi 100 mặt có điểm hoặc no\_face; đã gửi P1 tỉ lệ dò mặt cho README.

**T3 20/10**

- [ ] Kết quả theo 6 thuộc tính WFLW trên T: NME hai model, tỉ lệ dò được; NME khung tự dò cạnh khung WFLW — chạy ở Máy mình — ra by\_attribute.csv — xong khi mỗi dòng có số mặt.

**T4 21/10**

- [ ] Cờ trên T-test (kết quả của P3): % bắt, AUROC theo vùng, khoảng tin cậy (KTC) bootstrap theo mặt — chạy ở Máy mình — ra flags\_ttest.csv và kết luận giữ/bỏ cờ. Báo cả cờ gộp (ngưỡng t) và cờ t\_flip. Giữ hay bỏ cờ trong công cụ giao đi quyết theo cờ t\_flip: giữ khi trên T-test cờ bắt ≥ 50% điểm sai và trung bình ≤ \~7 cờ/mặt. Không đạt thì bỏ cờ — xong khi P5 nhận.
- [ ] Mục "Trang rà soát" trong README và `requirements-ui.txt` (gradio, không torch); ghi rõ chỉ chạy ở 127.0.0.1, không share, không Colab, và cách dùng `--review excel` khi không có Gradio — chạy ở Máy mình — ra đoạn README — xong khi P1 ghép vào gói `tool/`.

**T5 22/10**

- [ ] Viết phần "Model và cờ" của báo cáo nháp (NME, tỉ lệ dò, cờ, giấy phép) — chạy ở Máy mình — ra phần báo cáo — xong khi P5 ghép vào.

**T6 23/10**

- [ ] Làm 1–2 slide model và cờ, 1 slide trang rà soát, tập dượt phần rà soát trong demo `m28.py all` trên máy P4 (họp; ảnh demo chỉ ở máy đó) — chạy ở Máy mình (slide) và máy P4 — ra slide — xong khi tập dượt không lỗi.

**T7 24/10**

- [ ] Commit cuối: script, predictions.json, flags.json, phiên bản mediapipe, URL model — chạy ở Máy mình — ra commit trong repo nội bộ — xong khi P1 xác nhận gói công cụ đủ phần của bạn. Khi P5 báo đã nộp: dọn máy theo tab chung (mục cài CVAT, đoạn "Dọn máy 24/10": thu hồi token, xoá `CVAT_URL` và `CVAT_ACCESS_TOKEN`, `docker compose down -v` trong `~/cvat`; khoảng 15 phút) rồi báo P4.

## Làm thế nào

**Môi trường (5/10).** Không cài thêm opencv-python cạnh mediapipe (rút từ một lần cài thử, chưa kiểm chứng chính thức). Mở cmd (không dùng PowerShell) để chạy khối dưới. Lỗi import trên mọi máy thì cả nhóm chuyển sang venv Python 3.12 (cài Python 3.12, rồi đổi dòng đầu thành py -3.12 -m venv .venv); lỗi chỉ trên một máy thì máy đó dùng Colab/Kaggle.

```bat
py -3.14 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install mediapipe==1.0.1 torch torchvision
rem Cả nhóm dùng CVAT v2.77.0 trên máy từng người, nên sdk và cli ghim đúng bản này
python -m pip install cvat-sdk==2.77.0 cvat-cli==2.77.0 pandas
python -c "import mediapipe as mp; from mediapipe.tasks.python import vision; print(mp.__version__)"
curl -L -o face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
python -m pip freeze > requirements.txt
```

**MediaPipe gốc + lật (6/10).** Chỉ dùng Tasks API ([hướng dẫn Python](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/python)). Bản lật lưu theo toạ độ ảnh lật. P3 đổi bản lật sang 50 điểm rồi bỏ lật (x → 512 − x, đổi cặp theo cột flip). Kết quả nằm trong mp50.json. Bạn không bỏ lật lần nữa. Không thấy mặt: thêm viền xám, chạy lại. Vẫn không thấy: ghi no\_face, dùng điểm PIPNet, bật low\_conf cả 50 điểm.

```python
import cv2, numpy as np, mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

opts = vision.FaceLandmarkerOptions(
    base_options=mp_python.BaseOptions(model_asset_path="face_landmarker.task"),
    running_mode=vision.RunningMode.IMAGE, num_faces=1)

def run_mp(lm, rgb):
    img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
    res = lm.detect(img)
    if not res.face_landmarks:
        return None                                   # ghi no_face
    h, w = rgb.shape[:2]
    return [[p.x * w, p.y * h] for p in res.face_landmarks[0]]  # 478 điểm, pixel

with vision.FaceLandmarker.create_from_options(opts) as lm:
    rgb = cv2.cvtColor(cv2.imread("data/X1_01.png"), cv2.COLOR_BGR2RGB)
    orig = run_mp(lm, rgb)
    flip = run_mp(lm, rgb[:, ::-1])                   # toạ độ ảnh lật, chưa bỏ lật
    print(mp.__version__, None if orig is None else len(orig))
```

**PIPNet không biên dịch (7/10).**

1. Tải trọng số torchlm: https://github.com/xlite-dev/torchlm/releases/download/torchlm-0.1.6-alpha/pipnet\_resnet18\_10x98x32x256\_wflw.pth (đúng 49.393.015 byte).
2. Từ https://github.com/jhb86253817/PIPNet chỉ lấy lib/networks.py, data/WFLW/meanface.txt, hai hàm get\_meanface() và forward\_pip(). Bỏ dòng import scipy. Không chạy make.sh.
3. Tạo Pip\_resnet18(models.resnet18(weights=None), 10, num\_lms=98, input\_size=256, net\_stride=32), nạp bằng torch.load(..., map\_location="cpu", weights\_only=True).
4. Hộp WFLW (đổi sang ảnh 512 bằng phép biến đổi của P1) nới ngang 10% mỗi bên, dời cạnh trên xuống 10% chiều cao, kéo cạnh dưới xuống thêm 10% (đúng như lib/demo.py của PIPNet; PIPNet nhạy với cách cắt), rồi đưa về 256 × 256. Đổi điểm về ảnh 512. Bản lật: x → bề rộng hộp − x, đổi cặp bằng bảng cặp WFLW của HRNet.

**Cờ và ngưỡng (8 và 10/10).** Hai model luôn lệch nhau một chút ở từng điểm, vì cách đặt điểm khác nhau. Trước khi so, trừ độ lệch trung bình đó (offset) của từng điểm. Chỉ đo offset trên T-dev. Chia cho IOD dự đoán, vì ảnh thật không có đáp án. AUROC (khả năng xếp điểm sai trên điểm đúng; 0,5 = đoán mò) tính riêng từng vùng. Báo riêng bản cờ chỉ dùng lệch lật MediaPipe: bản này giao được vì không cần PIPNet.

```python
import numpy as np
# mpo, mpf, pip: (mặt, 50, 2) ảnh 512; mpf đã bỏ lật. bad: lỗi nháp > sai số vùng (hàm P3)
# EYE_R, EYE_L: chỉ số trong 50 điểm ứng với WFLW 60, 72; REGIONS: chỉ số điểm từng vùng
iod = np.linalg.norm(mpo[:, EYE_R] - mpo[:, EYE_L], axis=1)[:, None]
d_flip = np.linalg.norm(mpo - mpf, axis=2) / iod
offset = (mpo - pip).mean(axis=0)            # chỉ đo trên T-dev, lưu offset.npy
d_model = np.linalg.norm(mpo - pip - offset, axis=2) / iod
score = np.maximum(d_flip, d_model)

t = np.quantile(score, 0.85)                 # cờ <= 15% số điểm
flag = score > t
print("cờ/mặt", flag.sum(1).mean(), "bắt", flag[bad].mean())

def auroc(s, y):                             # y: True = điểm sai; không cần scipy
    r = s.argsort().argsort() + 1.0
    n1 = y.sum(); n0 = y.size - n1
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
print("AUROC vùng", np.nanmean([auroc(score[:, R].ravel(), bad[:, R].ravel()) for R in REGIONS]))
```

Với X, D và T-test: nạp offset.npy và ngưỡng t đã lưu, không tính lại (nếu họp 12/10 chọn t\_flip cho nháp X, D thì X, D dùng t\_flip).

**Bảng ảnh chồng (12 và 16/10).** Đọc file xuất CVAT for images 1.1. Ghép điểm theo tên (p01\_jaw\_R…), không theo vị trí. Vẽ số điểm, màu theo bên R/L/M, cạnh nối điểm liền nhau trên đường cong. Không vẽ low\_conf. Xếp nhiều mặt một trang để quét \~10 giây/mặt.

## Chạy ở đâu

| Việc | Nơi | Vì sao |
| --- | --- | --- |
| MediaPipe, PIPNet, cờ, bảng ảnh chồng | Máy mình (CPU) | MediaPipe \~0,04 s/ảnh, PIPNet \~0,1 s/mặt: vài phút. Dự án thật cũng chạy offline. |
| Như trên, khi máy lỗi (vd Windows chặn DLL scipy) | Colab hoặc Kaggle | Không tắt bảo mật Windows. Colab: lưu kết quả vào Drive. Kaggle: ghi vào /kaggle/working. Chỉ đưa WFLW lên, không đưa dữ liệu khách hàng. |
| Gán G, D, X, sửa (xem chéo làm trên ảnh chồng, ở Máy mình) | CVAT | CVAT trên máy mình; task khôi phục từ `backups/P2/` |

## Nhờ AI cho đúng

```text
I have PIPNet's MIT code: Pip_resnet18 from lib/networks.py, plus get_meanface() and forward_pip() copied from lib/functions.py (pasted below).
Write a CPU function pipnet98(img_bgr, box) that widens the box by 10% on the left and on the right, moves the top edge down by 10% of the box height and the bottom edge down by 10% of the box height (exactly as PIPNet's lib/demo.py does), crops, resizes to 256x256, converts BGR to RGB, normalises with ImageNet mean/std, runs forward_pip and returns 98 (x, y) points in input-image pixels plus 98 heatmap scores.
Do not import scipy, torchlm or FaceBoxes. Load weights with torch.load(path, map_location="cpu", weights_only=True).
```

```text
Chỉ dùng numpy (không scipy, không sklearn). Input: score và bad dạng (số mặt, 50), regions = dict tên vùng -> chỉ số điểm, ngưỡng t.
Viết hàm trả về: số cờ trung bình mỗi mặt, % điểm sai bị cờ, AUROC từng vùng (công thức hạng Mann-Whitney) và trung bình.
Thêm khoảng tin cậy 95% bằng bootstrap 2.000 lần, lấy mẫu lại theo mặt. Thêm 3 test với dữ liệu giả có đáp án biết trước.
```

```text
Write a Python script (opencv + numpy only) that reads a CVAT for images 1.1 XML export. Each image has one <skeleton label="face50"> with 50 <points label="pNN_..."> children.
Match points by label name, not by order. Draw each point with its number, coloured by side (R/L/M) from our config (column names pasted below), and draw lines between consecutive points of the same curve.
Ignore the low_conf attribute. Put 6 faces per PNG page with the file name above each face.
```

Ba quy tắc:

1. Không dán ảnh mặt, ảnh cắt, ảnh chồng, dữ liệu hay định nghĩa điểm của khách hàng vào chat AI, kể cả Gemini trong Colab. Chỉ dán mã, tên cột, thông báo lỗi. Ảnh WFLW chỉ ở nội bộ (CC BY-NC-ND).
2. Chạy code AI trên 5 mẫu T-dev trước khi chạy hết. Đếm điểm (478 / 98 / 50) và vẽ lên ảnh. Mặt nhìn thẳng: điểm WFLW 0 và 60 nằm nửa trái ảnh. Lật hai lần phải lệch ≤ 0,01 px.
3. Bỏ code có mp.solutions, face\_mesh, scipy.integrate, make.sh hoặc hàm không có trong tài liệu. Gọi thử; gặp AttributeError là API bịa.

## Lỗi hay gặp

1. Lật mà quên đổi cặp trái/phải: mọi điểm hai bên đều lệch lớn. Kiểm: trung vị lệch gốc/lật trên 20 mặt thẳng của F < 3% IOD (quên đổi cặp thì lệch hàng chục %).
2. Cho PIPNet ảnh 512 (hộp 1,4 lần). PIPNet học trên hộp 1,2 lần, 256 px; cắt sai thì NME T-dev vượt xa \~4,6%.
3. Đo offset hay chọn ngưỡng trên F hoặc T-test. Trên F offset gần 0 vì PIPNet học trên WFLW train. T-test chỉ chạy 1 lần.
4. AUROC gộp mọi điểm cao giả, vì viền mặt luôn sai nhiều hơn. Tính trong từng vùng.
5. Bỏ lặng lẽ ảnh no\_face, khiến P4 nhập thiếu mặt. Ghi no\_face từng ảnh, từng model.

## Khi bị kẹt

- Ảnh cắt, manifest.csv, phép biến đổi, gt98: P1.
- Config, cặp lật, đổi sang 50 điểm, sai số, hàm lỗi: P3.
- Cài CVAT, khôi phục backup, `export.py`, nháp trong file backup: P4.
- Lịch, điểm dừng, báo cáo: P5. Giấy phép, quyền dữ liệu: P5 hỏi mentor.

Mang theo: lệnh đã chạy, toàn văn lỗi, phiên bản Python/mediapipe/torch, một face\_id, việc đã thử. Không gửi ảnh mặt ra ngoài CVAT và repo nội bộ. Kẹt quá 15 phút thì hỏi.

## Phần mới: tự dò khung mặt và trang rà soát (11–17/10)

Bạn làm hai phần: `detect_face()` (cho ảnh khách hàng không có hộp mặt) và trang rà soát trước CVAT, phần mentor muốn thấy. Trang rà soát chỉ để phân loại nhanh; sửa điểm vẫn làm trong CVAT. Đừng làm thêm công cụ kéo điểm. Trong công ty gán nhãn, đây là bước một người lọc nhanh lô ảnh mới trước khi giao cho đội gán; với ảnh khách hàng, trang chạy trên đúng máy giữ ảnh.

**Tự dò khung mặt.** FaceLandmarker không trả hộp, nên lấy khung bao 478 điểm. Model dò mặt của nó hợp với mặt gần camera (như camera trong cabin); mặt nhỏ trong ảnh đông người hay bị sót.

```python
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

opts = vision.FaceLandmarkerOptions(
    base_options=mp_python.BaseOptions(model_asset_path="face_landmarker.task"),
    running_mode=vision.RunningMode.IMAGE, num_faces=5)

def detect_face(lm, rgb):                 # rgb: mảng numpy H×W×3, màu RGB (cv2.imread trả BGR: đổi bằng cv2.cvtColor)
    h, w = rgb.shape[:2]
    rgb = np.ascontiguousarray(rgb)       # bắt buộc: mảng cắt/lật chưa copy làm MediaPipe đọc sai ảnh
    res = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    if not res.face_landmarks:
        return None                       # ghi no_face
    boxes = []
    for face in res.face_landmarks:       # toạ độ 0–1, đổi ra pixel
        xs = [p.x * w for p in face]; ys = [p.y * h for p in face]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
    return max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))  # mặt lớn nhất

# Dùng: mở model một lần cho cả thư mục
# with vision.FaceLandmarker.create_from_options(opts) as lm:
#     box = detect_face(lm, rgb)
```

**Trang rà soát.** Gradio Blocks: `gr.Gallery` cho lưới, `gr.Image` cho ảnh lớn, 3 nút. Ảnh chồng lấy từ `runs/<run>/overlays/` (vẽ bằng `draw_overlay` của P1), vì `gr.AnnotatedImage` không vẽ được điểm.

```python
import os, sys, csv
RUN, WHO = sys.argv[1], sys.argv[2]                  # ví dụ runs/R1610 P5
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"     # không gửi thống kê
os.environ["GRADIO_TEMP_DIR"] = os.path.join(RUN, "_tmp")  # xoá sau khi rà
if "google.colab" in sys.modules or "KAGGLE_KERNEL_RUN_TYPE" in os.environ:
    sys.exit("Trang rà soát chỉ chạy trên Máy mình")
import gradio as gr

queue = load_queue(RUN)   # hàm bạn viết: [(ảnh chồng, "R_03 · 4 cờ · cần xem", tên file ảnh gốc), ...], mặt đáng ngờ lên đầu
items = [(p, c) for p, c, _ in queue]
os.makedirs(os.path.join(RUN, "review"), exist_ok=True)
with gr.Blocks() as app:
    grid = gr.Gallery(value=items, columns=5)
    big = gr.Image()
    reason = gr.Dropdown(["", "KHONG_MAT", "SAI_MAT", "MO_NHO", "LAT_GUONG", "DON_CUC", "LECH_VUNG", "QUAY_CHE", "NHIEU_MAT"], label="Lý do")
    with gr.Row():
        b_ok, b_tay, b_bo = gr.Button("Nhận"), gr.Button("Gán tay"), gr.Button("Bỏ ảnh")
    current = gr.State(0)
    def pick(evt: gr.SelectData):
        return items[evt.index][0], evt.index
    grid.select(pick, None, [big, current])
    def save(i, why, decision):
        with open(os.path.join(RUN, "review", f"triage_{WHO}.csv"), "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([queue[i][2], decision, why])   # tên file thật, push và triage_eval cần
    b_ok.click(lambda i, r: save(i, r, "nhan"), [current, reason], None)
    b_tay.click(lambda i, r: save(i, r, "gan_tay"), [current, reason], None)
    b_bo.click(lambda i, r: save(i, r, "bo"), [current, reason], None)
app.launch(server_name="127.0.0.1", share=False)   # luôn ghi rõ share=False
```

Bản 1 chưa có cột số giây và nút Xong; bản 2 (16/10) thêm. `push` lấy quyết định cuối cùng của mỗi tên file nếu một mặt bị bấm hai lần. Chạy từ thư mục repo để Gradio được đọc ảnh trong `runs/`.

**Nhờ AI cho đúng.**

```text
Viết app Gradio Blocks (Python 3.14) để phân loại ảnh: Gallery 5 cột từ danh sách (đường dẫn, chú thích),
bấm ảnh thì hiện lớn, 3 nút Nhận / Gán tay / Bỏ ảnh và Dropdown lý do, ghi CSV (tên ảnh, quyết định, lý do, số giây).
Mở lại thì bỏ qua ảnh đã có trong CSV. launch(server_name="127.0.0.1", share=False). Không dùng share, không tunnel.
Thử bằng 5 ảnh giả: chấm màu trên nền trắng.
```

Ba quy tắc: (1) không chụp trang rà soát dán vào chat AI, vì trên đó có ảnh mặt; (2) thử bằng ảnh giả trước, rồi `runs/F5/` và 30 mặt D; bạn không cần mở R1610; (3) không bao giờ đổi sang `share=True`, kể cả khi Gradio gợi ý.
