# P1 – Dữ liệu và đóng gói

Bạn làm ra mọi ảnh nhóm dùng: tải WFLW, cắt mặt, chia tập, ghi manifest.csv (bảng liệt kê từng ảnh cắt). Ngày 12/10, bạn đóng băng config (khoá file cấu hình, không sửa nữa). Từ 8/10 bạn dựng lệnh `m28.py` (pipeline một lệnh); tuần 3 bạn đóng gói công cụ: `m28.py` chạy offline trên CPU, hàm cho cvat-cli và README. Chia tập sai thì mọi số đo đều sai. Gói tốt thì dự án thật dùng lại ngay.

## Bạn nhận gì và giao gì

| Ngày | Nhận từ ai, cái gì | Giao cho ai, cái gì |
| --- | --- | --- |
| 5/10 | P2: venv chung (môi trường Python của nhóm), muộn nhất đầu buổi 6/10 | — |
| 6/10 | — | Đầu buổi, qua `data/`: cả nhóm 616 ảnh cắt và manifest.csv; P2, P3 gt98.json (đáp án 98 điểm theo toạ độ ảnh cắt). Trong buổi: P5 soát manifest.csv |
| 7/10 | P3: gt50.json, config | P3, P5: 10 ảnh chồng F (ảnh có vẽ đáp án). Cả nhóm: 2 file tar WFLW gốc trong MyDrive/M28/ |
| 8/10 | `backups/P1/` (P4 commit 7/10): `m28-gold-x` (G1), `m28-gold-y` (G2), khôi phục trên CVAT của bạn. P4 (trước phút 60): `export.py` | Repo: `raw/m28-gold-x_P1_0810.xml`, `raw/m28-gold-y_P1_0810.xml` (tự xuất) |
| 9/10 | `backups/P1/m28-pilot-manual.zip` (Pa, không nháp); P5: facetimer.py (script bấm giờ từng mặt). Đầu buổi: P2 `run_mp`, code cờ lật; P4 `image_xml` (write\_xml.py). Cuối buổi: P3 `apply_map()` (`mapping.py`), `map_mp50.json` | — (giữ timing\_P1.csv trên máy) |
| 10/10 | `backups/P1/m28-pilot-assisted.zip` (Pb, có nháp; khôi phục đầu buổi) | P5: timing\_P1.csv phần buổi thử, ngay sau khối Pb (khoảng phút 60). Repo: `raw/m28-pilot-manual_P1_0910.xml`, `raw/m28-pilot-assisted_P1_1010.xml` (tự xuất). P4: `runs/F5/` có `xml/prelabel.xml` (commit) |
| 11/10 | P2: `detect_face()`. P3: `test_pipeline.py`, chỗ lệch nếu có (bạn sửa ngày 13/10) | P3: `r_list_1610.csv`. P4: `r_list_1810.csv` |
| 12/10 | Họp: model, cờ cho nháp X, D; P3: sai số; P2: ngưỡng cờ | Cả nhóm, P4 trước: config đóng băng |
| 13/10 | `backups/P1/m28-practice.zip` (D\_01–D\_04). P4: `autoqc.py`. P2: `review_app.py` bản 1 | — (giữ timing\_P1.csv trên máy, gửi P5 ngày 17/10). P4: `m28.py` bản có `all` |
| 14/10 | `backups/P1/m28-manual.zip` (X1, không nháp; khôi phục đầu buổi 14/10) | — (giữ timing\_P1.csv trên máy) |
| 15/10 | `backups/P1/m28-assisted.zip` (X2, có nháp; chỉ khôi phục đầu buổi 15/10) | — (giữ timing\_P1.csv trên máy) |
| 16/10 | P4 (lệnh `collect --skip-export` trên `raw/` cả nhóm đã commit): CSV QC, bảng ảnh chồng, `outputs/review_1610/P4.csv` (mặt P4 gán, bạn xem) | `outputs/review_1610/P4.csv`: mã lỗi. P3, P4, P5: `runs/R1610/` (repo nội bộ), tag `pipeline-mvp` |
| 17/10 | Mã lỗi trên mặt của bạn (`outputs/review_1610/P1.csv`, P3 ghi) | Repo: `final/m28-manual_P1_1710.xml`, `final/m28-assisted_P1_1710.xml` (tự xuất). P5: timing\_P1.csv |
| 18/10 | — | Mentor (trong demo): `all` trên 5 mặt F chạy trên CVAT của bạn (`demo-thuP1`) |
| 19–21/10 | P2 (19/10): tỉ lệ dò mặt trên T-test (cho README 21/10). Code MediaPipe, ánh xạ, ghi XML đã nhận 9/10 | P5: công cụ + README. (Ảnh gốc T-test: P2 lấy từ bản WFLW đã tải ngày 11/10, theo manifest.csv; bạn không cần gửi.) |
| 22–24/10 | P5: khung báo cáo; P2: script, ghi chú README; P3: eval50.py | P5: mục "Công cụ", demo |

## Lịch của bạn

- [ ] **T2 5/10** Tải WFLW về máy (ô Colab chép vào MyDrive/M28/ và chia sẻ quyền xem dời sang 7/10); viết split.py, crop.py — chạy ở Máy mình — ra 2 file tar trên máy, 2 script — xong khi read\_wflw đếm đúng 7.500 và 2.500 dòng. Lúc báo cuối buổi, đăng thêm (chỉ chữ): bản Windows (`winver`), RAM, ổ C còn trống, dòng Virtualization trong Task Manager.
- [ ] **T3 6/10** Đầu buổi chạy split.py, crop.py, giao ngay; rồi kiểm khối X — chạy ở Máy mình — ra 616 ảnh 512 × 512, gt98.json, manifest.csv — xong khi check\_manifest.py không báo lỗi.
- [ ] **T3 6/10** (10 phút cuối) Cài CVAT phần A bước 1–2 (tab chung): kiểm máy, `wsl --install`; khởi động lại máy sau buổi — chạy ở Máy mình — ra WSL2 + Ubuntu — xong khi `wsl -l -v` thấy Ubuntu ở VERSION 2 (tạo user Ubuntu đầu buổi 7/10).
- [ ] **T4 7/10** Chồng gt50 lên 10 mặt F (3 thẳng, 3 nghiêng lớn, 4 bị che), màu theo bên R/L/M — chạy ở Máy mình — ra 10 file overlays/F\_\*.png — xong khi P3 xác nhận khớp; điểm WFLW 0 và 60 nằm nửa trái ảnh.
- [ ] **T4 7/10** (giờ thứ hai) Chạy ô Colab ở tab chung để có bản trong MyDrive/M28/, chia sẻ quyền xem cho 4 bạn (dời từ 5/10) — chạy ở Colab — ra 2 file tar trong MyDrive/M28/ — xong khi 4 bạn mở được thư mục.
- [ ] **T4 7/10** (trong lúc Colab chép) Cài CVAT phần B theo tab chung — chạy ở Máy mình — ra CVAT v2.77.0 ở `http://localhost:8080`, token trong biến môi trường — xong khi `python -m cvat_cli task ls` chạy không lỗi. Kẹt quá 15 phút thì dừng, báo P4, P5. G vẫn phải xuất và commit trước 10/10 (P3 cần), nên khi đó G vào giờ thứ hai 9/10 và P5 dời việc pipeline của tối đó.
- [ ] **T5 8/10** Đầu buổi khôi phục `backups\P1\m28-gold-x.zip` và `backups\P1\m28-gold-y.zip` (lệnh ở tab chung); gán tay G1, G2 theo guideline v1 — chạy ở CVAT trên máy mình — ra 8 mặt đủ 50 điểm, `raw/m28-gold-x_P1_0810.xml`, `raw/m28-gold-y_P1_0810.xml` — xong khi soát checklist cuối mặt cả 8 mặt, đã chạy `export.py` cho 2 task và commit. Xuất ở phần sau buổi (sau phút 65), khi P4 đã báo có `export.py`; P4 chưa báo thì xuất bằng giao diện theo tab chung (mục "Dùng hằng ngày") ngay tối nay (P3 cần file G đầu buổi 10/10).
- [ ] **T5 8/10** (giờ thứ hai) Dựng khung lệnh `tool/m28.py` (code mẫu ở cuối tab). Hôm nay mỗi bước chỉ cần ghi một file nhỏ; code thật thêm sau.
  1. Năm lệnh con: `prepare`, `review`, `push`, `collect`, `all`.
  2. Mỗi bước ghi vào thư mục riêng `runs/<run>/<bước>/`. Hàm của bước trả `True` khi xong thật; chỉ khi đó mới ghi `done.txt`, còn không thì in lý do và dừng. Lần sau bước có `done.txt` được bỏ qua. `--force <bước>` bắt làm lại bước đó.
  3. Ghi nhật ký `log.txt`; ghi bốn dòng `runs/` vào `.gitignore` (xem tab chung). `test_no_torch.py` dời sang CN 11/10.
  4. Tạo `config/pipeline.json` chỉ với giá trị chung: tên project `m28`, tiền tố task `demo-`, bản CVAT `2.77.0`. Không ghi địa chỉ server, project\_id, token hay mật khẩu: code đọc `CVAT_URL`, `CVAT_ACCESS_TOKEN` từ biến môi trường và tìm project theo tên.

  — chạy ở Máy mình — ra `tool/m28.py`, `config/pipeline.json` — xong khi gõ `python tool/m28.py prepare --run thu` hai lần: lần 1 in tên 6 bước, lần 2 in "bỏ qua" cho cả 6 bước.
- [ ] **T6 9/10** Buổi thử: đầu buổi khôi phục `backups\P1\m28-pilot-manual.zip` (Pa, không nháp); gán tay Pa, bật facetimer.py — chạy ở CVAT trên máy mình + Máy mình — ra 8 dòng log, `raw/m28-pilot-manual_P1_0910.xml` — xong khi đủ 8 mặt, đã xuất và commit; giữ log trên máy, gửi P5 phần buổi thử ngay sau khối Pb ngày 10/10 (khoảng phút 60). Trước 10/10 khôi phục thử `backups\all\m28-check.zip` (tab chung, bước 12).
- [ ] **T6 9/10** (giờ thứ hai, sau buổi thử) Bước `crop` và `mediapipe`: gọi `square_crop` (`--box wflw` lấy hộp từ manifest.csv) và `run_mp` của P2 (P2 commit đầu buổi) cho ảnh gốc + ảnh lật. `--list` nhận CSV có cột `wflw_image`, `wflw_line`; `--set` lọc tập khi đọc manifest.csv. Ghi `data/f5_list.csv` (5 mặt F đầu tiên của manifest.csv) — chạy ở Máy mình — ra `runs/F5/crop/`, `runs/F5/mediapipe/pred478.json` — xong khi ảnh cắt trùng ảnh của crop.py và mỗi mặt có 478 điểm hoặc nằm trong `no_face.csv`.
- [ ] **T7 10/10** Buổi thử: đầu buổi khôi phục `backups\P1\m28-pilot-assisted.zip` (Pb, có nháp); sửa nháp Pb, bật facetimer.py — chạy ở CVAT trên máy mình + Máy mình — ra 8 dòng log, `raw/m28-pilot-assisted_P1_1010.xml` — xong khi đủ 8 mặt, đã xuất và commit.
- [ ] **T7 10/10** (giờ thứ hai) Thêm bốn bước còn lại và chạy trên 5 mặt F, tắt mạng:
  1. `map50`: đổi 478 điểm sang 50 điểm bằng `apply_map` của P3 (P3 giao cuối buổi 9/10; bỏ lật).
  2. `flags`: bật cờ `low_conf` theo ngưỡng `t_flip` trong config. Config chưa có số thì để `null` và ghi mọi cờ = false; số thật có ngày 12/10.
  3. `overlays`: vẽ ảnh chồng bằng `draw_overlay` của bạn.
  4. `push --dry-run`: chỉ ghi file XML, chưa gửi lên CVAT, và không ghi `done.txt` của `push` (hàm trả `False`, lệnh dừng ở đây). Dùng `image_xml` của P4, nhưng bỏ cố định 512 và `assert 50`; số điểm lấy từ config.

  Commit `runs/F5/` (ảnh cắt F, giống `data/`), báo P4 — chạy ở Máy mình — ra `runs/F5/xml/prelabel.xml` — xong khi XML có 5 mặt × 50 điểm, điểm nào cũng có `low_conf`, và toạ độ lệch `mp50.json` không quá 0,05 px (chạy lại MediaPipe trên máy khác).
- [ ] **CN 11/10** (khung chung 2 tiếng) Gặp mentor và chọn tập R — chạy ở họp + Máy mình — ra `data/r_list_1610.csv`, `data/r_list_1810.csv` đã commit — xong khi không ảnh nào trùng manifest.csv và đã báo P3, P4. Làm theo thứ tự:
  1. (20 phút, nếu mentor rảnh) Gặp mentor cùng P5: chiếu `prepare` trên 5 mặt F.
  2. Chọn tập R bằng script, seed 18. Lấy ảnh WFLW train thoả cả ba điều kiện: không có trong manifest.csv; ảnh chỉ có một mặt được gán trong WFLW; cạnh hộp mặt ≥ 25% cạnh ngắn của ảnh (mặt lớn). Lấy 50 ảnh: 40 ảnh đầu ghi vào `data/r_list_1610.csv`, 10 ảnh sau vào `data/r_list_1810.csv`. Mỗi dòng chỉ có `wflw_image`, `wflw_line`, seed; không chép ảnh. Thời gian còn lại là dự phòng.
  3. (còn giờ, khoảng 10 phút) Thêm `test_no_torch.py` (dời từ 8/10; code ở cuối tab) — chạy ở Máy mình — xong khi in "ok: không có torch".
  4. (phần dự phòng, khoảng 10 phút) Thử tạo project trên máy thứ hai: chạy `client.projects.create` từ `config/face50_label.json` trên CVAT của bạn với tên `thu-face50` (vài dòng cvat-sdk, token đọc từ biến môi trường), mở project xem 50 điểm hình mặt có cạnh nối, rồi xoá project thử — chạy ở Máy mình + CVAT trên máy mình — xong khi thấy đủ 50 điểm đúng tên và cạnh nối đúng; lỗi thì báo P4 sửa `make_label.py` trước 18/10 (chỉ sửa cách ghi svg, không đổi tên, thứ tự hay số điểm, vì label đã nằm trong mọi file backup; lần tạo project đầu tiên trên máy thứ hai không được rơi vào ngày demo).
- [ ] **T2 12/10** 20 phút đầu: họp điểm dừng, P5 chủ trì — chạy ở họp nhóm — ra quyết định model, cờ cho nháp X, D (t\_flip hay t) — xong khi P5 ghi quyết định.
- [ ] **T2 12/10** Đóng băng config: ghi model, sai số, ngưỡng cờ; không sửa phần 50 điểm — chạy ở Máy mình (repo) — ra commit có tag (nhãn phiên bản trong git), gắn trước phút 60, sau khi P2 commit `flags.json` của họp — xong khi P2, P3 xác nhận số và P4 dựng backup tuần 2 từ đúng commit có tag này.
- [ ] **T2 12/10** (giờ thứ hai, sau khi gắn tag) Thêm `--box auto` vào bước `crop`: gọi `detect_face` của P2 (mặt lớn nhất), đổi toạ độ về ảnh gốc `x_gốc = x_cắt / k + left`, điểm ra ngoài ảnh thì kẹp vào mép — chạy ở Máy mình — ra XML cho 5 ảnh gốc F — xong khi mở ảnh chồng thấy điểm nằm đúng mặt trên ảnh gốc.
- [ ] **T3 13/10** Đầu buổi khôi phục `backups\P1\m28-practice.zip` (D\_01–D\_04); làm quen 4 mặt D (3 nháp, 1 tay); thử facetimer.py; tự xuất `raw/m28-practice_P1_1310.xml` và commit (P4 chạy QC trên file này) — chạy ở CVAT trên máy mình + Máy mình — ra 4 dòng log — xong khi đã sửa ít nhất 3 mặt nháp và file đã lên repo.
- [ ] **T3 13/10** (giờ thứ hai) Lệnh `all`, và sửa lỗi P3 báo ngày 11/10 (nếu có) — chạy ở Máy mình — ra `tool/m28.py` bản có `all` — xong khi `all --run F5 --list data/f5_list.csv --box wflw --review auto --dry-run` chạy tới bước `push`, chỉ ghi XML rồi dừng với dòng báo chạy thử (không ghi `done.txt` của `push`), không lỗi nào khác; báo P4. Cách làm:
  - Lần chạy 1: `prepare` → bước `review` → dừng nếu người rà chưa xong.
  - Lần chạy 2 (gõ lại đúng lệnh): thấy `runs/<run>/review/done.txt` thì bỏ qua prepare và rà, đi tiếp sang `push`.
  - Bước `review` có ba chế độ: `--review auto` (không cần người: ổn và cần xem → Nhận, nên gán tay → Gán tay, no\_face → Bỏ; chưa có `autoqc.csv` thì mọi mặt là Nhận); `--review excel` (in đường dẫn `autoqc.csv` và cách điền; khi có `triage_<Pk>.csv` đủ quyết định thì ghi `done.txt`); `--review ui` (gọi trang rà soát của P2; nối ngày 16/10). Hàm `review` trả `True` chỉ khi đã có `runs/<run>/review/done.txt` (nút Xong ghi) hoặc CSV đủ quyết định; đóng trang hay Ctrl+C trước khi bấm Xong thì trả `False`: lệnh dừng, lần sau mở lại trang và làm tiếp.
  - Mặt Gán tay ghi `manual_list.txt`; mặt Bỏ ghi `rejected.csv` kèm mã lý do.
- [ ] **T4 14/10** Lượt 1: đầu buổi khôi phục `backups\P1\m28-manual.zip` (X1, không nháp), rồi mới bật facetimer; gán tay X1; đọc câu chung; không mở đáp án, không xem tổng giờ — chạy ở CVAT trên máy mình + Máy mình — ra 10 mặt, 10 dòng log, `raw/m28-manual_P1_1410.xml` — xong khi đủ 10 mặt, đã xuất và commit trước phần sau của buổi.
- [ ] **T5 15/10** Lượt 2: đầu buổi khôi phục `backups\P1\m28-assisted.zip` (X2, có nháp; không khôi phục trước hôm nay), rồi mới bật facetimer; sửa nháp X2, cùng quy tắc — chạy ở CVAT trên máy mình + Máy mình — ra 10 mặt, 10 dòng log, `raw/m28-assisted_P1_1510.xml` — xong khi đủ 10 mặt, đã xuất và commit.
- [ ] **T5 15/10** (giờ thứ hai, chỉ viết chữ, không mở ảnh có nhãn nháp) README nháp cho `m28.py`: cài đặt, 4 lệnh, biến môi trường, `--review excel`, quy tắc trang rà soát chỉ ở 127.0.0.1, ảnh khách hàng chỉ trên một máy — chạy ở Máy mình — ra `tool/README.md` nháp — xong khi P4 đọc và hiểu cách chạy push.
- [ ] **T6 16/10** Bù mặt còn thiếu (seq nối tiếp) trên CVAT của bạn, xuất `raw/<task>_P1_1610.xml` và commit trước khi `git pull` hay mở bảng ảnh chồng; rồi xem chéo mặt của P4 trong `outputs/review_1610/P4.csv` (mặt bị đánh dấu, thêm 1 mặt ngẫu nhiên mỗi task) trên bảng ảnh chồng và ảnh cắt trong `data/` — chạy ở Máy mình — ra mã lỗi SWAP, MIRROR, COLLAPSE, MISPLACED, OCC\_FLAG, RULE theo điểm trong file đó — xong khi mọi mặt trong file có dòng ghi và đã commit.
- [ ] **T6 16/10** (giờ thứ hai) Cài `requirements-ui.txt` theo tab chung. Nối `review_app.py` (P2, 13/10) vào `review --review ui` và autoqc (P4, 13/10) vào `prepare`. Chạy `python tool/m28.py prepare --run R1610 --list data/r_list_1610.csv --images <thư mục WFLW_images> --box auto`; commit `runs/R1610/` vào repo nội bộ (ảnh WFLW, giống ảnh cắt; không bao giờ làm vậy với ảnh khách hàng); gắn tag `pipeline-mvp`; báo P3, P4, P5 — chạy ở Máy mình — ra `runs/R1610/` có `no_face.csv`, `log.txt` — xong khi 40 ảnh có nhãn nháp hoặc nằm trong `no_face.csv`, và `runs/R1610/` đã lên repo nội bộ. Không ai mở R1610 trên trang rà soát trước buổi rà của P5 đầu buổi 17/10.
- [ ] **T7 17/10** Sửa lỗi trên mặt của bạn (`outputs/review_1610/P1.csv`) trong CVAT trên máy mình, ghi "đã sửa"; rồi chạy `python tool\export.py m28-manual P1 1710 --final` và `python tool\export.py m28-assisted P1 1710 --final`, commit `final/` — chạy ở CVAT + Máy mình — ra số lỗi đã sửa, 2 file `final/` — xong khi mọi dòng lỗi ghi "đã sửa", 2 file đã lên repo và đã báo P4.
- [ ] **T7 17/10** (giờ thứ hai) Dự phòng: sửa lỗi pipeline nếu P4, P5 báo trong tối nay. Không ai chờ bạn: P4 push từ nhánh main mới nhất — chạy ở Máy mình (repo) — ra commit sửa lỗi nếu có — xong khi không còn lỗi mở trước demo 18/10.
- [ ] **CN 18/10** (khung chung 2 tiếng) Phút 0–30: chạy `python tool\m28.py all --run thuP1 --list data\f5_list.csv --images <WFLW_images> --box wflw --review auto --task demo-thuP1` trên CVAT của bạn (cùng công cụ, chỉ khác `CVAT_URL` và token); mở 1 mặt kiểm 50 điểm có `low_conf`. Phút 30–60: dự demo cho mentor (P5 chủ trì), chiếu phần này và giải thích: ở công ty chỉ cần đổi `CVAT_URL` sang server chung; ghi góp ý — chạy ở Máy mình + CVAT trên máy mình + họp — ra task `demo-thuP1`, danh sách góp ý — xong khi nhóm chốt việc tuần 3; xoá task `demo-thuP1` (kiểm đúng tên) và thư mục `runs/thuP1`. Phần còn lại là dự phòng.
- [ ] **T2 19/10** Thử lệnh `python tool/m28.py prepare` (thay cho việc gom code của kế hoạch cũ; có từ 10/10, `--box auto` từ 12/10) trên 5 ảnh gốc mới, kiểm `no_face.csv`; không chỉnh `detect_face` theo T-test — chạy ở Máy mình — ra XML CVAT 1.1 cho 5 ảnh — xong khi lệnh chạy được lúc tắt mạng.
- [ ] **T3 20/10** Viết cvat\_func.py bản mỏng: `detect()` gọi `prelabel_one()` trong `tool/m28core` (cùng code với prepare), luôn trả đủ 50 điểm + `low_conf`; đầu file thêm đường dẫn tới `tool/` để cvat-cli tìm được m28core — chạy ở Máy mình — ra cvat\_func.py gửi P4 cuối buổi — xong khi hàm chạy trên 5 ảnh ra đủ 50 điểm đúng tên, đúng thứ tự, có cờ. P4 thử trên CVAT ngày 21/10.
- [ ] **T4 21/10** Hoàn thiện README (đã có nháp 15/10; thêm tỉ lệ dò mặt trên T-test của P2), tool/requirements.txt (không torch), requirements-ui.txt; cài lại venv mới; thử một config bớt điểm bằng `prepare --config` (chép config, xoá 10 điểm) — chạy ở Máy mình — ra README.md, XML của config thử — xong khi XML thử có đúng 40 điểm, và một bạn khác cài theo README ra XML cùng tên điểm, toạ độ lệch ≤ 0,05 px (không so hash: MediaPipe trên CPU khác có thể lệch rất nhỏ).
- [ ] **T5 22/10** Viết mục "Công cụ" cho báo cáo nháp — chạy ở Máy mình — ra đoạn văn gửi P5 — xong khi P5 đưa vào bản nháp.
- [ ] **T6 23/10** Demo, tập dượt: cùng P4 chạy `python tool/m28.py all` trên ảnh demo của P5 ở máy P4 (cả bốn lệnh trên một máy, như với ảnh khách hàng; `prepare` chạy được khi tắt mạng), bạn giải thích từng bước — chạy ở máy P4 (họp) — ra demo — xong khi buổi tập chạy không lỗi.
- [ ] **T7 24/10** Nộp: tag bản cuối; kiểm gói không có ảnh WFLW, ảnh cắt, gt, trọng số PIPNet, `runs/`, token; `test_no_torch.py` qua — chạy ở Máy mình (repo) — ra tag cuối — xong khi P5 có link. Khi P5 báo đã nộp: dọn máy theo tab chung (mục cài CVAT, đoạn "Dọn máy 24/10": thu hồi token, xoá `CVAT_URL` và `CVAT_ACCESS_TOKEN`, `docker compose down -v` trong `~/cvat`; khoảng 15 phút) rồi báo P4. Giờ còn lại là dự phòng.

## Làm thế nào

**1. Tải và cắt (5–6/10)**

1. Ảnh: link Google Drive trên https://wywu.github.io/projects/LAB/WFLW.html. Đáp án: https://wywu.github.io/projects/LAB/support/WFLW\_annotations.tar.gz.
2. Drive hết lượt tải thì dùng bản Kaggle `mrriandmstique/wflw-wider-facial-landmarks-in-the-wild` qua `kagglehub.dataset_download`. Bỏ qua nhãn "Apache 2.0" của người đăng; vẫn áp CC BY-NC-ND.
3. Đọc hai file trong `list_98pt_rect_attr_train_test/`. Mỗi dòng: 196 toạ độ, 4 số hộp, 6 cờ, đường dẫn ảnh.

```python
import cv2, numpy as np
ATTRS = ['pose', 'expression', 'illumination', 'makeup', 'occlusion', 'blur']
def read_wflw(txt_path):
    rows = []
    with open(txt_path) as f:
        for i, line in enumerate(f):
            a = line.split()
            assert len(a) == 207, len(a)
            rows.append({'line': i, 'image': a[206],
                         'pts': np.array(a[:196], np.float32).reshape(98, 2),
                         'bbox': np.array(a[196:200], np.float32),
                         **{k: int(v) for k, v in zip(ATTRS, a[200:206])}})
    return rows

def square_crop(img, bbox, pts, side_scale=1.4, out=512):
    x0, y0, x1, y1 = bbox
    side = side_scale * max(x1 - x0, y1 - y0)       # cạnh dài x 1,4, cùng tâm
    left, top = (x0 + x1 - side) / 2, (y0 + y1 - side) / 2
    k = out / side
    M = np.float32([[k, 0, -left * k], [0, k, -top * k]])
    crop = cv2.warpAffine(img, M, (out, out), borderValue=(128, 128, 128))
    gt = (pts - [left, top]) * k                     # gt98 theo toạ độ ảnh cắt
    inside = bool(((gt >= 0) & (gt <= out - 1)).all())
    return crop, gt, (left, top, k), inside
```

Lưu `left, top, k` vào manifest. Đổi ngược: x\_gốc = x\_cắt / k + left.

**2. Chia tập (split.py, 6/10)**

- Chỉ cần file đáp án: tính inside từ hộp và 98 điểm (cùng công thức với square\_crop, không cần ảnh) trước khi chia. Dùng một seed cố định (số khởi tạo ngẫu nhiên, để chạy lại ra đúng kết quả). Ghi seed vào manifest.
- F 300 từ WFLW train. T 200 từ WFLW test, chia tầng theo bộ 6 cờ: T-dev 100, T-test 100. Chia tầng nghĩa là tỉ lệ mỗi loại mặt khó giống nhau ở hai tập.
- G 20, P 16, X 50, D 30 lấy từ phần test còn lại, vì PIPNet đã học trên train. Hỏi P2 xác nhận ngày 5/10.
- G, P, X, D chỉ lấy mặt có `inside = True`.
- Tên file: F\_001, Tdev\_001, Ttest\_001, G1\_01 … G5\_04, Pa\_01 … Pb\_08, X1\_01 … X5\_10, D\_01 … D\_30 (.png).
- Cột manifest.csv: file, set, block, seq, wflw\_split, wflw\_image, wflw\_line, hộp (4 cột), left, top, k, 6 cờ, seed.

Khối X: chọn 10 mặt dễ (6 cờ bằng 0); mỗi khối nhận 2 mặt dễ ở seq 01–02. 40 mặt còn lại xếp theo cờ pose, occlusion rồi chia lần lượt vào khối 1→5, 5→1, 1→5… (như code dưới).

```python
import random
def make_x_blocks(easy, rest, seed):
    rng = random.Random(seed)
    easy, rest = easy[:], rest[:]
    rng.shuffle(easy)
    rng.shuffle(rest)
    rest.sort(key=lambda r: (r['pose'], r['occlusion']), reverse=True)
    blocks = [[] for _ in range(5)]
    for i, r in enumerate(rest):              # chia vòng 0-4, rồi 4-0
        k = i % 5 if (i // 5) % 2 == 0 else 4 - i % 5
        blocks[k].append(r)
    for k in range(5):
        rng.shuffle(blocks[k])                # trộn thứ tự seq 03-10
        blocks[k] = easy[2 * k:2 * k + 2] + blocks[k]
    return blocks

def block_ok(b):                              # 1-2 nghiêng lớn, 2-4 bị che
    pose = sum(r['pose'] for r in b)
    occ = sum(r['occlusion'] for r in b)
    return 1 <= pose <= 2 and 2 <= occ <= 4
```

Khối nào không đạt thì chọn lại 40 mặt với seed khác.

**3. Lệnh m28.py (8–16/10) và đóng gói (19–21/10)**

1. Gói nằm trong thư mục `tool/`: m28.py và m28core/ (bước prepare là công cụ nhãn nháp), review\_app.py của P2, cvat\_func.py, config đóng băng, map\_mp50.json của P3, face\_landmarker.task, `tool/requirements.txt` (không có torch), README.md. File requirements.txt ở gốc repo là venv chung của P2; không ghi đè.
2. Tải sẵn model từ link cố định https://storage.googleapis.com/mediapipe-models/face\_landmarker/face\_landmarker/float16/1/face\_landmarker.task để chạy offline.
3. FaceLandmarker không trả hộp mặt. Chạy nó trên cả ảnh, lấy khung bao 478 điểm làm hộp. Đưa khung bao 478 điểm thẳng vào square\_crop (hàm đã nới 1,4 lần; không nới thêm), rồi chạy lại trên ảnh cắt. Dùng detect\_face() của P2 (có từ 11/10).
4. Chạy FaceLandmarker (Tasks API) trên ảnh cắt và ảnh lật. Đổi sang 50 điểm bằng file ánh xạ. Cờ low\_conf (điểm đáng ngờ): độ lệch gốc/lật lớn hơn ngưỡng t\_flip. P2 chọn t\_flip trên T-dev; bạn ghi nó vào config ngày 12/10.
5. Đổi về toạ độ ảnh gốc. Ghi XML bằng image\_xml của P4, sửa hai chỗ: width, height lấy từ ảnh gốc (không cố định 512); số điểm lấy từ config (bỏ số 50 trong assert).
6. Tên điểm, thứ tự, ngưỡng cờ chỉ đọc từ config. Không thấy mặt: thêm viền xám quanh ảnh rồi chạy lại. Vẫn không thấy: ghi tên ảnh vào no\_face.csv để gán tay.
7. cvat\_func.py theo https://docs.cvat.ai/docs/api\_sdk/sdk/auto-annotation/. Chỉ chạy trên task chưa có nhãn, không dùng `--clear-existing`.
8. README ghi: cài, chạy, cvat-cli, đổi bộ điểm, giây/ảnh, giấy phép. Ghi cả giới hạn: mặt quay > 80°, che quá nửa, một mặt mỗi ảnh, video chỉ keyframe.
9. map\_mp50.json được khớp trên ảnh WFLW (CC BY-NC-ND). Hỏi mentor qua P5 trước khi giao file này cho khách hàng. Nếu không được, khớp lại trên vài chục ảnh khách hàng đã gán.

Thử cài sạch trong cmd. MediaPipe trên Python 3.14 mới thử trên một máy; lỗi import thì dùng Python 3.12.

```bat
py -3.14 -m venv .venv-tool
call .venv-tool\Scripts\activate.bat
cd tool
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import mediapipe as mp; from mediapipe.tasks.python import vision; print(mp.__version__)"
python m28.py prepare --run mau5 --images mau5 --box auto
python m28.py push --run mau5 --dry-run
```

## Chạy ở đâu

| Việc | Ở đâu | Vì sao |
| --- | --- | --- |
| Tải, chia tập, cắt, ảnh chồng | Máy mình | CPU đủ; ảnh cắt chỉ ở repo nội bộ và CVAT |
| Gán, sửa | CVAT trên máy mình (xem chéo: ảnh chồng, Máy mình) | Mỗi người gán trên CVAT của mình (localhost); xem chéo trên ảnh chồng |
| Đóng gói, thử công cụ | Máy mình | Giống dự án thật: Windows, CPU, offline |
| Máy lỗi (vd Windows chặn DLL) | Colab/Kaggle, chỉ ảnh WFLW | Không tắt bảo mật Windows |
| Dữ liệu khách hàng | Chỉ máy mình | Không lên Colab, Kaggle, chat AI |

## Nhờ AI cho đúng

```text
Viết hàm Python split_sets(train_rows, test_rows, seed) cho WFLW. Mỗi row là
dict: line, image, pose, expression, illumination, makeup, occlusion, blur (0/1),
inside (bool). F = 300 mặt ngẫu nhiên từ train. Từ test: T = 200 mặt, chia tầng
theo bộ 6 cờ thành T-dev đúng 100 và T-test đúng 100. G 20, P 16, X 50, D 30 lấy
từ test còn lại, chỉ inside=True. Không tập nào trùng nhau. Chỉ dùng
random.Random(seed). Thêm assert kiểm số lượng và không trùng (image, line).
```

```text
Viết check_manifest.py đọc manifest.csv (cột file, set, block, seq, wflw_image,
wflw_line, pose, occlusion và 4 cờ khác). In lỗi và thoát mã 1 nếu:
số mặt khác F 300, Tdev 100, Ttest 100, G 20, P 16, X 50, D 30; trùng
(wflw_image, wflw_line); khối X nào không có 10 mặt, 1-2 mặt pose=1, 2-4 mặt
occlusion=1; seq 1-2 của khối X có cờ khác 0; tên file sai mẫu X1_01.png.
```

```text
Viết hàm draw_overlay(img_path, pts, sides, out_path) bằng OpenCV. pts là mảng
(50, 2) pixel trên ảnh 512x512; sides là list 50 chữ 'R', 'L', 'M'. Vẽ chấm bán
kính 3 px, màu theo bên, số thứ tự 1-50 cạnh chấm. Không đổi kích thước ảnh.
Chỉ dùng cv2 và numpy.
```

```text
Theo đúng tài liệu https://docs.cvat.ai/docs/api_sdk/sdk/auto-annotation/, viết
module Python cho cvat-cli auto-annotate. Trả về skeleton label "face50"; tên 50
điểm đọc từ file cấu hình; mỗi điểm có checkbox low_conf. Điểm lấy từ hàm có sẵn
prelabel_one(image) -> (pts, flags) trong tool/m28core. Chỉ dùng hàm có trong tài liệu đó và ghi rõ
từng hàm lấy từ mục nào.
```

Ba quy tắc:

1. Không dán ảnh mặt, ảnh cắt, dữ liệu hay định nghĩa điểm của khách hàng vào chat AI. Gemini trong Colab cũng vậy. Chỉ dán tên cột và số giả.
2. Chạy code AI viết trên 5 mẫu trước. So với số bạn tự tính, ví dụ toạ độ một điểm sau khi cắt. Sai một mẫu thì không dùng.
3. Loại ngay code có `mp.solutions` hoặc hàm không có trong tài liệu chính thức. MediaPipe chỉ dùng `vision.FaceLandmarker` với face\_landmarker.task.

## Lỗi hay gặp

1. Kéo giãn mặt. Hộp WFLW thường không vuông. Luôn cắt vuông rồi mới đưa về 512; kiểm bằng ảnh chồng F.
2. Tên file thiếu số 0 (X1\_1.png). CVAT xếp ảnh trong task theo thứ tự tên, nên thứ tự mặt (và seq bấm giờ) bị lệch.
3. Nhìn đáp án G, P, X. Bạn sẽ gán các mặt này. Chỉ kiểm `inside` bằng script; ảnh chồng chỉ làm cho F.
4. Sửa chia tập sau 6/10. P2 phải chạy lại model, P4 phải dựng lại mọi file backup và cả 5 người phải khôi phục lại task. Chỉ sửa trước 7/10 và báo P2.
5. Thêm opencv-python vào requirements.txt. MediaPipe đã kéo opencv-contrib-python; cài cả hai dễ lỗi.

## Khi bị kẹt

Kẹt quá 15 phút thì hỏi ngay.

| Vấn đề | Hỏi ai | Mang theo |
| --- | --- | --- |
| Cài đặt, venv, MediaPipe | P2 | Lệnh đã chạy, lỗi đầy đủ, kết quả `py -0p` |
| Toạ độ, gt98, gt50, config, ánh xạ | P3 | face\_id, ảnh chồng F (qua repo nội bộ) |
| CVAT, tên file, XML, cvat-cli | P4 | Tên task, số job, file XML mẫu |
| Chia tập, khối X, lịch, demo | P5 | manifest.csv, bảng đếm cờ theo khối |
| Giấy phép, ảnh trong báo cáo, demo | Mentor, qua P5 | Câu hỏi viết sẵn |

## Phần mới: lệnh m28.py (8–16/10)

Bạn là chủ của lệnh `tool/m28.py`. Mỗi bước chỉ là một lớp mỏng gọi hàm có sẵn của bạn và của P2, P3, P4; không viết lại model. Lệnh phải dễ: người khác chỉ nhớ `prepare`, `review`, `push`, `collect`, `all`. Trong công ty gán nhãn, đây là lệnh người vận hành chạy mỗi khi khách gửi một thư mục ảnh mới; với ảnh khách hàng, cả bốn lệnh chạy trên một máy.

**Làm thế nào.** Mỗi bước có một thư mục trong `runs/<run>/`. Hàm của bước trả `True` chỉ khi xong thật; khi đó `run_step` mới ghi `done.txt`. Trả `False` (ví dụ rà chưa bấm Xong, `push --dry-run`) thì lệnh in lý do và dừng bằng `SystemExit`, không ghi `done.txt`. Chạy lại thì bước có `done.txt` được bỏ qua, trừ khi tên bước nằm trong `--force`. Đừng làm cache phức tạp (hash, resume): một file `done.txt` là đủ. Hai file cấu hình: `config/m28_config.json` là bộ 50 điểm (đã có, đóng băng 12/10); `config/pipeline.json` chỉ giữ giá trị chung (tên project `m28`, tiền tố task `demo-`, bản CVAT `2.77.0`), không địa chỉ, không project\_id, không token, không mật khẩu. Địa chỉ server và token đọc từ biến môi trường `CVAT_URL`, `CVAT_ACCESS_TOKEN`; project tìm theo tên. Nhờ vậy cùng một lệnh chạy được với CVAT trên máy bạn và với CVAT chung của công ty. Đường dẫn riêng từng máy (thư mục WFLW, thư mục ảnh khách) truyền bằng `--images`, không ghi vào file commit.

```python
# tool/m28.py – khung tối thiểu
import argparse, os
from m28core import steps   # crop, mediapipe, map50, flags, autoqc, overlays (+ review, push, collect)

PREPARE = ["crop", "mediapipe", "map50", "flags", "autoqc", "overlays"]

def run_step(name, args):
    out = os.path.join("runs", args.run, name)
    if os.path.exists(os.path.join(out, "done.txt")) and name not in args.force:
        print("bỏ qua", name); return
    os.makedirs(out, exist_ok=True)
    ok = getattr(steps, name)(args, out)  # True chỉ khi bước xong thật; trả False thì hàm bước đã in lý do
    if not ok:  # ví dụ: rà chưa bấm Xong (kể cả Ctrl+C), CSV thiếu quyết định, push/collect chạy --dry-run
        raise SystemExit(f"Dừng ở bước {name}: chưa xong nên không ghi done.txt (lý do in ở trên).")
    with open(os.path.join(out, "done.txt"), "w", encoding="utf-8") as f:
        f.write("ok")

# Hàm bước trong m28core/steps.py nhận (args, out), trả True chỉ khi xong thật:
#   review: trang đã đóng mà chưa có out/done.txt (nút Xong ghi) → False; excel: CSV còn thiếu dòng → False
#   push, collect: có --dry-run → chỉ ghi XML / in danh sách job rồi trả False (không ghi done.txt)

p = argparse.ArgumentParser(prog="m28")
p.add_argument("cmd", choices=["prepare", "review", "push", "collect", "all"])
p.add_argument("--run")                                # tên lượt chạy, ví dụ R1610 (collect không cần)
p.add_argument("--images")                             # thư mục ảnh (WFLW_images hoặc ảnh khách)
p.add_argument("--list"); p.add_argument("--set", nargs="*")   # CSV có wflw_image, wflw_line; lọc tập
p.add_argument("--box", choices=["wflw", "auto"], default="auto")
p.add_argument("--config", default="config/m28_config.json")
p.add_argument("--review", choices=["ui", "excel", "auto"], default="ui")
p.add_argument("--reviewer", default="RA"); p.add_argument("--review-file")
p.add_argument("--task", action="append", default=[])  # collect nhận nhiều --task
p.add_argument("--tag"); p.add_argument("--skip-export", action="store_true")
p.add_argument("--force", nargs="*", default=[])
p.add_argument("--dry-run", action="store_true")      # push: chỉ ghi XML; collect: chỉ in danh sách job; không ghi done.txt
args = p.parse_args()
if args.cmd != "collect" and not args.run:
    p.error("lệnh này cần --run")
if args.cmd in ("prepare", "all"):
    for s in PREPARE:
        run_step(s, args)
```

`prepare`, `review`, `push`, `all` cần `--run`; `collect` cần `--task`. Bước `review` và `push` viết theo cùng mẫu `run_step` (`done.txt` nằm ở `runs/<run>/review/`, `runs/<run>/push/`). Bước `review` luôn ghi `runs/<run>/review/triage_<reviewer>.csv` (`--reviewer` mặc định là `RA`; `--review auto` ghi `triage_auto.csv`); trong `all`, `push` đọc đúng file đó nếu không có `--review-file`. `push` ghi XML vào `runs/<run>/xml/prelabel.xml` (cùng chỗ với bản `--dry-run` ngày 10/10) và `push.json` vào `runs/<run>/`; với `--dry-run`, `push` dừng sau khi ghi XML và không ghi `done.txt`.

```python
# test_no_torch.py – gói giao khách không được kéo theo torch/PIPNet
import sys
sys.path.insert(0, "tool")
import m28core.steps
assert "torch" not in sys.modules, "tool/ đang import torch"
print("ok: không có torch")
```

**Giữ an toàn.** `push` và `collect` là hàm của P4. Bạn có CVAT và token riêng, nên thử thật được trên CVAT của mình với task `demo-…` (xoá task thử sau khi dùng); chưa có token thì dùng `push --dry-run`. Không bao giờ chạy pipeline trên task `m28-`. `runs/` có ảnh mặt: `.gitignore` ghi `runs/*`, `!runs/F5/`, `!runs/R1610/`, `runs/*/_tmp/`; chỉ hai lượt chạy WFLW này được commit.

**Nhờ AI cho đúng.**

```text
Viết một CLI Python bằng argparse tên m28 với lệnh con prepare, review, push, collect, all.
Mỗi bước ghi vào runs/<run>/<bước>/. Hàm bước trả True chỉ khi xong thật; khi đó mới tạo done.txt, còn False thì thoát bằng SystemExit kèm lý do.
Bước đã có done.txt thì in "bỏ qua",
trừ khi tên bước nằm trong --force. Các hàm bước đã có sẵn trong module m28core.steps, nhận (args, out).
Không dùng thư viện ngoài. Thêm 3 dòng assert để tự kiểm.
```

Ba quy tắc: (1) chỉ dán code và tên file, không dán ảnh, `mp50.json` hay XML xuất; (2) chạy thử trên 5 mặt F trước khi chạy tập R; (3) so kết quả với `mp50.json` của P3, lệch quá 0,05 px là có lỗi.
