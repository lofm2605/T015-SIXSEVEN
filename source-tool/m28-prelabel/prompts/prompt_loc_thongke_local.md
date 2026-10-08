> **GHI CHÚ (09/10/2026, QĐ-006):** Mục 4 của prompt này (trang Thống kê 4 nhóm số liệu) đã bị thay bởi `prompts/prompt_m28_dongho_thongke_job_local.md` và QĐ-006: chạy prompt này thì chỉ làm bộ lọc (mục 2, 3) và tab Lọc dữ liệu, dùng lại `bang_mat`/`thong_ke` đã có; không thêm lại thẻ cờ `low_conf`, số lượng, tiến độ, giây rà vào tab Thống kê (trang chỉ còn ba chỉ số của thí nghiệm hai nhóm độc lập).

> **MÁY UBUNTU (ghi đè, ưu tiên hơn mọi chỗ nói Windows/cmd bên dưới):** chủ repo đã chuyển sang Ubuntu. Cách dùng: ở thư mục repo chạy `git pull`, mở Claude Code rồi gõ
> `Đọc source-tool/m28-prelabel/prompts/prompt_loc_thongke_local.md và thực hiện đúng và đầy đủ.` Khi đọc phần bên dưới, đổi: đường dẫn `\` thành `/`; `cmd` thành bash;
> `%TEMP%\m28_loc_thongke\` thành `/tmp/m28_loc_thongke/` (hoặc `$TMPDIR`); `robocopy` thành `cp -r`; `chay.bat` thành `chay.sh` và `HUONG-DAN-WINDOWS.md` thành `HUONG-DAN-UBUNTU.md`
> (cập nhật CẢ HAI file hướng dẫn nếu cùng có mục tương ứng; nếu thêm mục vào `chay.sh` thì giữ đồng bộ với `chay.bat`); venv `source .venv/bin/activate`; chụp HTML tĩnh bằng
> `chromium`/`google-chrome --headless=new --screenshot=...` nếu có (không có thì ghi "chưa chụp"); Python theo máy (không bắt buộc 3.14). Mọi quy tắc khác giữ nguyên.

> Cách dùng: ở `D:\AI\T015-SIXSEVEN` chạy `git pull`, mở Claude Code trong thư mục đó rồi gõ: `Đọc source-tool\m28-prelabel\prompts\prompt_loc_thongke_local.md và thực hiện đúng và đầy đủ.`

# Prompt chạy LOCAL (Windows): M28, bộ lọc dữ liệu train và trang Thống kê

Bạn là kỹ sư triển khai trong repo đề tài M28 (đội T015-SIXSEVEN), chạy **trên máy Windows của một thành viên** (không phải cloud). Làm **toàn bộ** việc dưới đây
trong phiên này, tự kiểm trên dữ liệu thật của máy, rồi viết báo cáo cuối trung thực. Viết code, tài liệu và báo cáo bằng **tiếng Việt**.
Chủ repo đã trả lời mọi câu hỏi lớn (mục 1). **Chi tiết nhỏ bạn tự quyết**: chọn phương án đơn giản, an toàn, khớp code hiện có; ghi mọi mặc định đã chọn vào
báo cáo (mục 11). Chỉ dừng hỏi khi một việc trái quy tắc ở mục 0A hoặc trái `CLAUDE.md`.

## 0A. Môi trường local và luật làm việc (ưu tiên hơn mọi chỗ khác trong file này)

- **Đường dẫn.** Repo là thư mục hiện tại (ví dụ `D:\AI\T015-SIXSEVEN`); `M` = `source-tool\m28-prelabel`. Mọi lệnh của tool chạy với **cwd = `M`**
  (đường dẫn `runs\`, `raw\`, `final\`, `outputs\`, `data\`, `config\` tính từ `M`). Thư mục tạm của phiên: `%TEMP%\m28_loc_thongke\` (tạo mới, NGOÀI repo) cho script
  tạm, dữ liệu giả, thư mục chạy thử `work\`, ảnh chụp `shots\`, log. Không bao giờ ghi đường dẫn tuyệt đối của máy (`D:\...`, `C:\Users\...`) vào code hay tài liệu của repo.
- **Máy.** Windows, **cmd** (không PowerShell trong tài liệu; trong phiên dùng shell sẵn có cũng được), Python 3.14, CPU, venv `M\.venv` của `chay.bat` nếu có
  (`call .venv\Scripts\activate.bat`). Có CVAT local ở `http://localhost:8080` nhưng **không gọi CVAT** trong phiên này (bộ lọc và thống kê chỉ đọc file đã xuất). Không có cloud,
  không có GPU. **Không cài thêm gói nào** (không matplotlib, không scipy/sklearn, không `playwright install`). Code trong `tool\` chỉ dùng thư viện chuẩn + numpy
  (+ PIL nạp lười nếu thật cần) như hiện có: **không dùng pandas trong `tool\`** dù pandas có trong `requirements.txt`.
- **Git.** Trước khi sửa: `git status` phải sạch (không sạch thì DỪNG và báo, không stash/không xoá). Rồi:
  ```bat
  git checkout main
  git pull
  git checkout -b loc-thongke
  ```
  Nếu nhánh `loc-thongke` đã có: không xoá, không ghi đè; tạo `loc-thongke-2` và ghi vào báo cáo. Commit **nhỏ, theo từng bước ở mục 9**, thông điệp tiếng Việt.
  **KHÔNG push, không tạo PR, không merge.** Người dùng tự đọc rồi quyết.
- **pytest gốc.** Trước khi sửa, trong `M`: `python -m pytest tests -q` và ghi số thật của máy (người điều phối ghi khoảng **665 qua + 1 bỏ qua**; máy này có thể
  khác vì gói/skip, ghi số thật). Sau khi làm xong: số qua **không được ít hơn** số gốc, không test cũ nào bị xoá hay nới lỏng.
- **Quyền riêng tư (giữ nguyên `CLAUDE.md`).** Ảnh, ảnh cắt, ảnh chồng, `runs\`, `data\`, `raw\`, `final\`, `outputs\`, `backups\`, file xuất CVAT, gói train, zip, ảnh chụp
  màn hình: **không bao giờ vào git** (`.gitignore` đã chặn; kiểm `git status` trước mỗi commit). Không ghi token/mật khẩu/email vào code, log, CSV, HTML, báo cáo.
  Không `share=True`, không tunnel, trang chỉ `127.0.0.1`. Ảnh người lái xe chỉ dùng nội bộ nhóm; không đưa ảnh mặt vào chat AI nào ngoài việc **xem ảnh kiểm
  bằng công cụ Read của chính phiên này** (được phép cho YawDD/DrivFace). Không xử lý ảnh khách hàng/ảnh người thật ngoài hai bộ này.
- **Dữ liệu thật trên máy.** `M\data\` (manifest.csv, crops\, có thể có frames\) và `M\runs\` (các lượt đã `prepare`; ví dụ F5, INC3_ALL, NAP_xxx) có sẵn. Có thể
  có `raw\`, `final\`, `timing_P*.csv`, `outputs\nme_per_face.csv` hoặc chưa. **Chỉ đọc** các thư mục đó: bộ lọc và thống kê không được sửa/tạo file nào trong `runs\`,
  `raw\`, `final\`, `data\` (có test kiểm bằng băm trước/sau). Thiếu `data\manifest.csv` thì vẫn làm code + test, ghi rõ phần tự kiểm nào không làm được.
- **Không sửa** `de-tai-m28\` (bản chụp) và `CLAUDE.md` (đề xuất sửa trong báo cáo). Được sửa `so-quyet-dinh.md` **chỉ để thêm QĐ-005** (mục 8).
- **Xem ảnh** (ảnh chụp tab, ảnh HTML xuất) bằng công cụ Read, ghi vào báo cáo điều thấy được. Báo cáo cuối **trung thực**: việc chưa chạy thì nói chưa chạy,
  số từ dữ liệu giả thì gọi là dữ liệu giả.

## 0. Đọc trước khi sửa (bắt buộc, đọc hết chứ không đọc lướt)

- `CLAUDE.md`; `so-quyet-dinh.md` (QĐ-001..QĐ-004 và **mẫu cuối file**: `tests\test_ca_kho.py` đọc mẫu đó).
- Trong `M`: `README.md`, `TAI-LIEU-CHI-TIET.md` (mục Trang rà soát, Ca khó, push và collect, Chạy test), `HUONG-DAN-WINDOWS.md`, `nguon-du-lieu.md` (giấy phép,
  trích dẫn YawDD/DrivFace), `BAO-CAO-CO-LOW-CONF.md`, `chay.bat`, `requirements.txt`, `requirements-ui.txt`, `prompts\prompt_dms_v3_local.md` (để biết lối làm của đội).
- `config\m28_config.json`: 50 điểm DMS, mỗi điểm có `name`, `group` (7 nhóm: `longmaytrai` 5, `longmayphai` 5, `songmui` 4, `mattrai` 8, `matphai` 8, `moingoai` 12,
  `moitrong` 8), `region` (vùng thô `brow`/`nose`/`eye`/`lip`), `type`, `curve`, `coincide`; `iod_points` = [`mattrai_1`, `matphai_1`]; `t_flip` và `tolerance` đang `null`.
  **Thứ tự điểm luôn theo config** (so chuỗi: `moingoai_10` < `moingoai_2` theo chữ cái, không được sắp theo chữ).
- `tool\review_app.py`: `build_ui` (các tab Rà soát, Nạp ảnh, Các đợt, Ca khó, Họp team, Cài đặt; `tab.select` để làm mới lười), `AppCtx` (`runs_root`, `project_root`,
  `tmp_dir`, `closing`), `Store`, `read_rows`/`latest` (triage `name,decision,reason,seconds`; dòng sau đè dòng trước; dòng Hoàn tác có `seconds` trống; giây = thời gian
  từ lần bấm trước, lần bấm đầu tính từ lúc mở phiên), `STATUS_COLOR`, `CSS = CSS + dot_ui.CSS + ca_kho.CSS + cai_dat_ui.CSS`, `main` (`allowed_paths` chỉ gồm thư mục
  của lượt và `outputs\ca_kho`), `_launch` (127.0.0.1, `share=False`, chặn Host lạ).
- `tool\ca_kho.py`: mẫu dựng một tab (`member_tab(gr, demo, store, ctx)` trả `(hàm làm mới, inputs, outputs, opts)`; `opts = dict(show_progress="hidden",
  api_visibility="private", concurrency_limit=1, concurrency_id=...)`; `gr.HTML(..., apply_default_css=False)`; `gr.DownloadButton`; `ctx.closing`), `run_source`
  (nguồn `yawdd`/`drivface`/`khong_ro` của một lượt), `_manifest_data`, `serve_dir`, `_atomic_write`, `csv_text`, `_formula_safe`, `build_package` (zip có giới hạn,
  ghi file tạm rồi `os.replace`), `warn_html`, CSS dùng biến theme.
- `tool\dot_anh.py` (`list_runs`, `read_push`, `run_date`, `_cached`, `read_mp50`, `triage_of`, `other_reviewers`), `tool\nap_anh.py` (`RUN_RE`, `_inside`, `RunError`,
  `check_reviewer`), `tool\m28core\loai_tru.py` (`excluded.txt`), `tool\m28core\phan_loai.py` (`DECISIONS`, `read_triage`, `read_no_face`, `classify`), `tool\m28core\mau_nhom.py`
  (`GROUP_COLOR`, `GROUP_VI`).
- `tool\eval50.py` (`read_labels` đọc XML/zip CVAT bảy skeleton, `read_run_pred`, `point_errors`, `face_scores`, `summarize`, `BAD = 10`, cột `nme_per_face.csv`:
  `face_id,condition,nme,nme_eye,nme_p2p,reg_*,eye_open_err,n_missing` — **giữ nguyên nghĩa các cột này**), `tool\flag_eval.py` (`auroc`, `flip_scores_g`, `tolerance_for`,
  `report`, `report_unlabelled`; cấm `--set Ttest`).
- `tool\m28core\steps.py` (`flags`: `t_flip = null` thì mọi cờ = false, mặt không có ảnh lật thì mọi cờ = true; `review --review auto` ghi `triage_auto.csv` không có giây;
  `_file_name`, `_face_pts`, `read_box_mode`: tên ảnh và toạ độ tải lên CVAT theo chế độ `crop`/`auto`), `tool\m28core\push.py` (`push.json`: `task`, `phien_ban`,
  `gan_tay_co_nhap`, `so_anh`), `tool\m28core\collect.py` (`raw\<task>_<người>_<DDMM>.xml` + `.txt`, `RAW_RE`, `latest_raw_files`, `push_info`, `analyze`: thuộc tính
  `low_conf` trong file xuất), `tool\m28core\cvat_io.py` (`parse_annotations`, `read_zip_annotations`, `groups_from_names`, `merged_face`, `inside`, `safe_file_part`).
- `tool\inc_ingest.py` và `tool\check_manifest.py`: cột manifest (`file, set, block, seq, source, camera, subject, gender, glasses, state, ..., pose, expression,
  illumination, makeup, occlusion, blur, yaw, pitch, roll, jaw_open, luma, contrast, lap_var, gaze_label, ...`), **cách chia theo người**: `GROUP_A = (F, Tdev, Ttest)`
  đôi một không chung người; `GROUP_B = (G, P, X, D)` dùng chung người với nhau nhưng không chung với nhóm A.
- `de-tai-m28\p5-thi-nghiem.md` (chỉ đọc): `facetimer.py` ghi `timing_<Pk>.csv` 12 cột `date, person, condition, task, job, block, seq, face_id, seconds, warmup,
  interrupted, note`; mục "Thời gian" (r_i, trung bình nhân, bootstrap trong khối 2.000 lần seed 28, KTC 90%, luật Đạt) và mục "Chất lượng" (hiệu NME ghép cặp, ngưỡng
  +0,5% IOD); mục "Số liệu (18–19/10)" (giây rà/mặt từ `triage_P5.csv`). `.gitignore` đã chặn `timing_*.csv`.
- `tests\`: `conftest.py`, `test_review_app.py`, `test_ca_kho.py`, `test_eval50.py`, `test_flag_eval.py`, `test_chay_bat.py`, `test_no_torch.py`, `synth_faces.py`
  (cách dựng dữ liệu giả), `e2e_review_ui.py`/`e2e_ca_kho.py` (Playwright, tuỳ chọn, `lsof` chỉ có trên Linux).

## 1. Bối cảnh và yêu cầu (chủ repo đã chốt)

Pipeline M28 đặt nháp 50 điểm bằng MediaPipe, người rà Nhận/Gán tay/Bỏ trên trang Gradio, `push` lên CVAT, người sửa trong CVAT, `collect`/`export.py` xuất nhãn về
`raw\` (bản sửa lần hai ở `final\`). Hai việc mới:

- **A. Bộ lọc dữ liệu** tạo bộ train/finetune cho **một model landmark KHÁC sau này**. MediaPipe không train được; repo chưa có bước train và **prompt này không thêm
  code train, không thêm torch/tf, không viết vòng huấn luyện**. Nguồn: ảnh đã có nhãn sửa tay. Có **CLI** `tool\loc_du_lieu.py` (cấu hình lọc JSON, `--dry-run` xem số
  lượng) và **tab mới** trong trang rà soát.
- **B. Trang Thống kê** chỉ số model: tab mới trong `review_app` (127.0.0.1 như các tab khác) **và** bản xuất CSV + HTML tĩnh để đưa vào báo cáo, gồm đủ 4 nhóm: (1) chất
  lượng nháp, (2) cờ `low_conf`, (3) tốc độ gán, (4) số lượng dữ liệu và tiến độ.

**Không bịa số.** Chỗ nào chưa có dữ liệu thì hiện trạng thái trống rõ ràng (vì sao trống, cần file nào, ai làm ra file đó), không bao giờ hiện 0 hay số mẫu thay cho "chưa có".

## 2. Phần chung: một lớp đọc dữ liệu ("bảng mặt")

Viết **một** module đọc dùng chung cho A và B (mặc định `tool\m28core\bang_mat.py`; tên khác được nếu có lý do). Chỉ thư viện chuẩn ở đầu module, numpy nạp lười
trong hàm; không import gradio, torch, cv2, mediapipe, cvat_sdk; không gọi mạng; **chỉ đọc**. Tái dùng hàm có sẵn (đừng viết lại logic đọc triage, tên ảnh CVAT, toạ độ,
nguồn lượt, NME, AUROC): nếu cần tách một hàm in ra màn hình thành hàm trả dict (ví dụ `flag_eval.report`) thì giữ nguyên đầu ra CLI cũ và test cũ.

Mỗi dòng của bảng là một **(lượt, mặt)**, gồm ít nhất:
- định danh: `luot`, `mat` (tên trong lượt, ví dụ `F_004`), `anh_cvat` (tên ảnh tải lên CVAT theo `steps._file_name` và `crop\box.txt` của lượt);
- từ manifest (khớp `file` = `mat + ".png"`): `nguon` (`yawdd`/`drivface`; lượt không khớp manifest hoặc có `inbox\` → `khong_ro`), `subject`, `set` gốc, `camera`,
  `glasses`, `state`, sáu cờ `pose`…`blur`, các số đo cần dùng (`yaw`, `jaw_open`, `luma`, `lap_var`);
- từ lượt: có nháp (`map50\mp50.json`), `no_face`, xoá mềm (`excluded.txt`), gợi ý autoqc, **cờ máy** từ `flags\flags.json` (tổng và theo 7 nhóm, theo vùng), điểm số lật
  liên tục của từng điểm (`flag_eval.flip_scores_g`, để tính AUROC và để tính lại cờ với `t_flip` khác);
- rà soát: mọi `review\triage_<người>.csv` (quyết định cuối, lý do, tổng giây có giá trị của mặt, số lần đổi ý); `triage_auto.csv` là **máy tự quyết** (không phải người rà);
- nhãn sửa tay (xem dưới): file nhãn, người gán, ngày, `dieu_kien`, `loai_mat`, 50 điểm (thiếu/`outside` = null), số thuộc tính `low_conf` còn bật trong nhãn, số điểm thiếu;
- so sánh nháp với nhãn (khi có cả hai, cùng hệ toạ độ): NME chính/phụ, `nme_eye`, theo vùng, **theo 7 nhóm**, lỗi từng điểm, mặt hỏng (`>= eval50.BAD`) — tính bằng
  `eval50.point_errors`/`face_scores`, không công thức mới.

**Tìm nhãn sửa tay (mặc định, ghi vào README):**
1. Lượt có `push.json` (task `demo-…`): nhãn = `raw\<task>_<người>_<DDMM>.xml` mới nhất **mỗi người** (`collect.latest_raw_files`); có `final\` cùng mẫu tên thì `final\`
   ưu tiên hơn `raw\`. `loai_mat`: mặt Nhận → `nhan` (`dieu_kien = assisted`); mặt Gán tay có trong `push.json.gan_tay_co_nhap` → `gan_tay_co_nhap` (assisted, nháp mọi
   điểm low_conf); Gán tay còn lại → `gan_tay_trong` (`dieu_kien = manual`, gán từ ảnh trống).
2. File nhãn không gắn với `push.json` (task thí nghiệm `m28-manual`, `m28-assisted`, `m28-pilot-*`, `m28-gold-*`…): điều kiện suy từ tên task (`manual`/`gold` → manual,
   `assisted` → assisted; `practice`, `check`, `smoke` → bỏ qua, ghi lý do; không rõ → `khong_ro_dieu_kien`, đếm nhưng không vào số theo điều kiện). Chúng chỉ có nháp và
   cờ khi người dùng chỉ rõ **lượt chứa nháp** (`luot_nhap` trong cấu hình lọc, ô chọn ở tab Thống kê); không chỉ thì các cột nháp để trống, ghi "không có nháp liên kết".
3. Cùng một mặt có nhiều nhãn (thí nghiệm: Pk gán tay Xk, người khác sửa nháp cùng khối; hoặc nhiều lượt chứa cùng mặt manifest): giữ hết trong bảng; khi cần **một** nhãn
   (bộ lọc) thì ưu tiên mặc định `final > manual > assisted`, rồi mới nhất; ghi số mặt trùng và (nếu có ≥ 2 nhãn) **độ lệch giữa hai nhãn người** (NME giữa hai nhãn) để dùng
   làm tín hiệu chất lượng.
4. Ghép tên ảnh nhãn với mặt **theo đúng** `steps._file_name`/`eval50.read_run_pred` (như `flag_eval` làm). Nhãn ở hệ khung gốc mà lượt nháp là `crop` (hoặc ngược lại):
   đổi toạ độ bằng `left/top/k` (ngược đúng `steps._face_pts`), có test khứ hồi. Không ghép được thì ghi lý do, không đoán.
5. Nhãn dùng label `face50` cũ (một skeleton) hoặc tên điểm v2 (`pNN_…`): không đọc được với config v3 → đếm riêng "nhãn cũ", không làm sập.

Số liệu tổng theo **mặt duy nhất** (khoá = tên manifest) khác số theo **(lượt, mặt)**: hiện cả hai khi khác nhau, ghi rõ đơn vị. Cache theo mtime (mp50.json vài MB); đo
và ghi thời gian dựng bảng trên dữ liệu thật vào báo cáo.

## 3. Việc A: bộ lọc dữ liệu train/finetune

### 3.1 Tiêu chí
- **Bắt buộc:** cờ `low_conf` và **số điểm bị cờ**: ngưỡng tối thiểu/tối đa cho **tổng** và **theo từng nhóm** (7 nhóm; cho phép thêm theo vùng thô). Nguồn cờ mặc định
  = `flags.json` của lượt (cờ máy lúc làm nháp). **Bẫy đã biết:** `t_flip` trong repo đang `null` nên lượt chạy trước khi P2 chốt có mọi cờ = false, và `flags.json` không
  ghi `t_flip` đã dùng. Phát hiện "mọi cờ của lượt = false" và báo rõ; cho phép `"co": {"nguon": "tinh_lai", "t_flip": 0.06}` để tính lại cờ từ điểm số lật (đúng công thức
  `steps.flags`, gồm luật "không có ảnh lật = mọi điểm có cờ"). Thuộc tính `low_conf` còn bật trong **nhãn đã sửa** là tín hiệu khác (người gán để lại): tiêu chí riêng,
  không trộn với cờ máy.
- **Thêm (đã chọn làm, đều tuỳ chọn trong cấu hình):** nguồn (chỉ `yawdd`, `drivface`); `set` gốc; `camera`, `glasses`, `state`, sáu cờ manifest (tư thế, biểu cảm,
  tối/sáng, che/kính râm, mờ); **NME của nháp so với nhãn đã sửa** (min/max, % IOD; "nháp sai nhiều = đáng học"); quyết định rà (`nhan`, `gan_tay`, `bo`) và người rà;
  điều kiện/loại mặt của nhãn; số điểm thiếu trong nhãn; độ lệch giữa hai nhãn người khi có.
- **Luật cứng (không tắt được bằng cấu hình):** mặt nguồn `khong_ro` (lượt Nạp ảnh, có thể là ảnh khách hàng) luôn bị loại với lý do rõ; mặt xoá mềm luôn bị loại; mặt
  không có nhãn sửa tay không vào bộ train. Mặc định thêm: loại mặt `Bỏ`; `triage_auto` không tính là quyết định của người.
- Mặt không có nháp (Gán tay ảnh trống, không có lượt nháp) gặp tiêu chí NME/cờ: mặc định **loại với lý do "không đo được"**; cấu hình `"giu_mat_khong_nhap": true` để giữ.

### 3.2 File cấu hình lọc (JSON)
Đặt một file mẫu **không chứa dữ liệu** trong repo (mặc định `config\loc_mau.json`, có test kiểm hợp lệ) và tài liệu hoá từng khoá. Khoá tiếng Việt không dấu, ví dụ
(bạn tự chốt tên cuối cùng):
```json
{"ten": "finetune_v1",
 "nguon_nhan": {"luot": ["INC3_ALL"], "file_nhan": [], "luot_nhap": null, "uu_tien": ["final", "manual", "assisted"]},
 "nguon_du_lieu": ["yawdd", "drivface"],
 "quyet_dinh": ["nhan", "gan_tay"], "nguoi_ra": [],
 "co": {"nguon": "flags_json", "t_flip": null, "tong": {"toi_thieu": 0, "toi_da": 50},
        "theo_nhom": {"mattrai": {"toi_da": 8}, "matphai": {"toi_da": 8}}},
 "nme_nhap": {"toi_thieu": null, "toi_da": null},
 "manifest": {"pose": null, "expression": null, "occlusion": null, "illumination": null, "blur": null, "camera": null, "glasses": null},
 "nhan": {"so_diem_thieu_toi_da": 0, "low_conf_trong_nhan_toi_da": null},
 "chia": {"train": ["F", "G", "P", "X", "D"], "val": ["Tdev"], "test": ["Ttest"], "loc_tap_danh_gia": false},
 "kem_anh": true, "zip": false}
```
Kiểm cấu hình chặt: khoá lạ, tên nhóm lạ, min > max, giá trị sai kiểu → lỗi tiếng Việt nói rõ khoá nào, không chạy tiếp.

### 3.3 Chia train/val/test theo tài xế (không rò rỉ)
- **Tái dùng cách chia của `inc_ingest`**, không chia lại: mặc định `train` = F + G + P + X + D, `val` = Tdev, `test` = Ttest. Đúng vì F, Tdev, Ttest đôi một không chung người
  và nhóm B (G/P/X/D) không chung người với nhóm A.
- **Kiểm lại** trên chính bộ xuất bằng cột `subject`: một `subject` nằm ở hai phần → **lỗi, không ghi gì** (không tự sửa). Kiểm cả khi người dùng đổi ánh xạ `chia`.
- Mặc định `loc_tap_danh_gia = false`: tiêu chí "chọn ca khó" (cờ, NME nháp, manifest) **chỉ áp lên train**; val/test chỉ qua luật cứng và vệ sinh nhãn (đủ điểm, không Bỏ)
  để còn đại diện. Ttest là tập đo một lần của đề tài: không dùng số trên Ttest để chỉnh ngưỡng lọc; README của gói ghi điều này.

### 3.4 Gói xuất (ngoài git)
`outputs\train_sets\<ten>\` (tên theo `[A-Za-z0-9_-]{1,40}`; đường dẫn kiểm bằng realpath + commonpath; đã có thì từ chối trừ khi `--ghi-de`; ghi vào thư mục tạm cùng
cấp rồi `os.replace`):
- `manifest.csv`: một dòng/ảnh: `id`, `anh` (đường dẫn trong gói), `split`, `nguon`, `subject`, `set_goc`, `luot`, `mat`, `task`, `file_nhan`, `nguoi_gan`, `dieu_kien`,
  `loai_mat`, `quyet_dinh`, `nguoi_ra`, `n_co`, `n_co_<nhóm>` ×7, `nme_nhap` (trống nếu không đo), các cờ manifest, `w`, `h`. CSV `utf-8-sig`, ô chữ an toàn công thức
  (`ca_kho._formula_safe`).
- Nhãn 50 điểm **theo thứ tự config**: `nhan.json` (`{"points": [50 tên], "groups": {...}, "iod_points": [...], "config_version": 3, "anh": {id: [[x, y] | null] × 50}}`)
  và `nhan.csv` dạng rộng (`id, x_<tên>, y_<tên>, v_<tên>` với `v` = 1 có điểm, 0 thiếu), cộng cột `low_conf_<tên>` lấy từ nhãn đã sửa.
- Ảnh: mặc định **ảnh cắt 512 của lượt** (`crop\images\<mặt>.png`, chép nguyên, không mã hoá lại) và toạ độ đổi về hệ ảnh cắt đó; ghi `he_toa_do` trong README. Điểm rơi ngoài
  ảnh sau khi đổi: giữ toạ độ, đếm `n_ngoai_anh`.
- `train.txt`, `val.txt`, `test.txt`; `cau_hinh_loc.json` (bản chép cấu hình đã dùng); `bao_cao_loc.md` + `bao_cao_loc.csv`: **bao nhiêu mặt bị loại vì sao**, hai cách đếm:
  thác nước theo thứ tự tiêu chí (tổng các bước = tổng đầu vào) và số mặt không đạt **từng** tiêu chí (chồng lấn); chia theo split, nguồn, lượt.
- `README.md` của gói: ngày tạo, commit git, config version, cấu hình lọc, cách chia, hệ toạ độ, số mặt mỗi phần, và **nguồn + giấy phép**: DrivFace "free for academic
  usage" (trích dẫn Diaz-Chito và cộng sự, Applied Soft Computing 45 (2016) 98-107); YawDD chỉ phi thương mại và nghiên cứu, bắt buộc trích dẫn Abtahi và cộng sự, ACM
  MMSys 2014, chỉ được đăng ảnh của video có "Allow Researchers to use picture in their paper" = Yes; dự án phi thương mại: **không phát tán, không đăng lại, không giao bên
  thứ ba, chỉ dùng nội bộ nhóm**, ảnh người lái xe là dữ liệu nhạy cảm (lấy câu chữ từ `nguon-du-lieu.md`, không tự chế).
- **Tất định:** cùng đầu vào + cùng cấu hình → `manifest.csv`, `nhan.*`, `*.txt` giống hệt từng byte (thứ tự sắp ổn định; ngày giờ chỉ nằm trong README). `zip: true` thì
  thêm `outputs\train_sets\<ten>.zip` (cảnh báo: chứa ảnh mặt, chỉ gửi trong đội).

### 3.5 CLI `tool\loc_du_lieu.py`
```bat
python tool\loc_du_lieu.py --cau-hinh config\loc_mau.json --dry-run
python tool\loc_du_lieu.py --cau-hinh outputs\loc_cua_toi.json --ten finetune_v1 [--ghi-de] [--zip]
```
`--dry-run` in bảng số lượng (vào, bị loại theo lý do, còn lại theo split/nguồn) và **không ghi file nào**. `--help` tiếng Việt. Mã thoát: 0 xong, 1 không còn mặt nào,
2 lỗi cấu hình/dữ liệu. In đường dẫn tương đối.

### 3.6 Tab "Lọc dữ liệu"
Theo mẫu `ca_kho.member_tab` (module riêng, mặc định `tool\loc_ui.py`; không import gradio ở đầu module). Cảnh báo ảnh nhạy cảm (như `ca_kho.warn_html`) ở đầu tab.
Điều khiển cho các tiêu chí chính (lượt, nguồn, quyết định, người rà, cờ tổng + theo nhóm, NME nháp, vài cờ manifest, `luot_nhap`), ô **nạp/lưu cấu hình JSON** (chỉ trong
`outputs\`), nút **"Xem trước số lượng"** (= dry-run, bảng thác nước + theo split/nguồn, không ghi gì), ô tên bộ, nút **"Tạo bộ dữ liệu"** (có xác nhận khi ghi đè), kết quả
(đường dẫn tương đối, số mặt, cảnh báo rò rỉ người nếu có) và nút tải zip khi đã tạo zip. Tab **không hiện ảnh mặt** (chỉ số). Tôn trọng `ctx.closing`, khoá ghi, 
`concurrency_id` riêng; dùng được cả ở chế độ `--nap` (không có lượt đang rà).

## 4. Việc B: trang Thống kê

### 4.1 Nguyên tắc chung
- Mọi ô số đi kèm **n**. Ô có n < 5 ghi "n quá nhỏ" thay cho tỉ lệ/khoảng tin cậy (ngưỡng là hằng số đặt tên rõ ở đầu module). Không có dữ liệu → trạng thái trống có lời
  giải thích (ví dụ: "Chưa có nhãn gán tay: cần `raw\<task>_<Pk>_<DDMM>.xml` (P4 `collect`/`export.py`)"). Không số giả, không 0 thay cho "chưa có".
- **Ttest ẩn mặc định** (ô "Gồm Ttest", có ghi chú "Ttest là tập đo một lần"); `triage_auto` không tính là người rà; lượt dùng tên điểm cũ (v2) bỏ qua có ghi chú.
- Bộ lọc chung ở một hàng trên cùng: lượt (nhiều lượt), gồm Ttest, người rà, `luot_nhap` cho nhãn thí nghiệm, nút "Làm mới", nút "Xuất CSV + HTML".
- Tính **khi chọn tab** (như tab Các đợt), không tính lúc mở trang.

### 4.2 (1) Chất lượng nháp (chỉ khi đã có nhãn sửa tay)
- NME nháp so với nhãn: trung bình, trung vị, % mặt hỏng (≥ 10% IOD, `eval50.BAD`), `nme_eye`, độ mở mắt; **theo 7 nhóm** (màu nhóm), theo 4 vùng thô; theo điều kiện:
  `dieu_kien`/`loai_mat`, nguồn, camera, `set`, tư thế, biểu cảm, che/kính râm, tối, mờ, kính, người gán.
- **Tách manual và assisted, không gộp lặng lẽ:** nhãn manual (gán từ đầu) là đáp án trung thực cho chất lượng nháp; nhãn assisted bị neo theo nháp nên NME nháp-vs-assisted là
  **cận dưới** ("lượng người đã sửa"). Số tiêu đề lấy manual; manual chưa có thì tiêu đề ghi rõ "chỉ có nhãn assisted: cận dưới".
- Nếu có `outputs\nme_per_face.csv` (của `eval50`, chất lượng nhãn người so với đáp án vàng): hiện thêm khối "chất lượng nhãn" đúng giao thức P5 (hiệu ghép cặp assisted − manual
  theo mặt, bootstrap 2.000 lần seed 28, cận 5/95, ngưỡng +0,5% IOD: đạt / không đạt / chưa kết luận). Chỉ **đọc** file đó; không ghi đè, không đổi cột.
- Ghi số theo mặt ra file riêng (mặc định `nme_nhap.csv` trong thư mục xuất), các cột đầu **trùng tên và nghĩa** với `nme_per_face.csv` (pred = nháp, gt = nhãn), cột thêm
  (`luot`, `nguoi_gan`, `loai_mat`, `nhom_<nhóm>`…) chỉ nối ở cuối.

### 4.3 (2) Cờ low_conf
- Không cần đáp án: % điểm bị cờ (tổng, theo nhóm, theo vùng, theo lượt), phân bố số cờ/mặt, `t_flip` hiện tại của config, và cảnh báo khi một lượt có mọi cờ = false
  (khả năng chạy với `t_flip = null`).
- Có đáp án: độ chính xác của cờ so với sai số thật, **tái dùng `flag_eval`**: điểm sai = lỗi > `tolerance_for` (mặc định 3% IOD khi `config.tolerance` null); AUROC của
  điểm số lật (tổng, theo nhóm, theo vùng); tại `t_flip` hiện hành (hoặc các phân vị như `flag_eval` khi `t_flip` null): % điểm bị cờ, recall (% điểm sai bị bắt), precision,
  cờ/mặt. Ghi số điểm sai (n); quá ít điểm sai (< 10) thì "n quá nhỏ" thay cho AUROC. Tách manual/assisted như 4.2. Thêm: số `low_conf` người gán còn để bật trong nhãn.

### 4.4 (3) Tốc độ gán
- **Chỉ số chính theo đúng giao thức P5** (không tự chế): đọc `timing_P*.csv` (12 cột `facetimer.py`; tìm ở `M\`, `M\outputs\`, `M\raw\`, `M\final\` và đường dẫn người
  dùng nhập, chỉ trong thư mục dự án ở giao diện); chỉ `warmup = 0` và task thí nghiệm (`m28-manual`, `m28-assisted`); r_i = giây trung bình/mặt assisted ÷ manual của từng
  người; chỉ số = **trung bình nhân** các r_i; **% nhanh hơn = (1 − TB nhân) × 100**, mục tiêu ≥ 20% (TB nhân ≤ 0,80) và ≥ 4/5 người có r_i < 1; KTC 90% bootstrap bốc lại
  seq trong từng khối, chung cho hai cách, 2.000 lần, seed 28; bảng kiểu M24 và giờ tiết kiệm/1.000 mặt (chung và hai nhóm nghiêng/che theo manifest `pose|occlusion`).
  Chỉ numpy + thư viện chuẩn trong `tool\`; test so với đoạn code P5 (pandas) trên dữ liệu giả nếu máy có pandas, không thì so với số tính tay.
- **Ngoại lai và cỡ mẫu:** dòng `seconds` trống/≤ 0 bị bỏ và đếm; dòng `interrupted = 1` và dòng vượt Q3 + 3·IQR trong (người, điều kiện) được **đánh dấu và liệt kê**
  (ảnh bỏ ngang, nghỉ giữa chừng) nhưng **vẫn nằm trong chỉ số chính** như giao thức; hiện thêm một dòng "độ nhạy: bỏ ngoại lai". Người thiếu một điều kiện → không có r_i,
  ghi lý do; < 3 người có đủ hai điều kiện → không kết luận, ghi "chưa đủ dữ liệu".
- **Giây rà/mặt** (cột `seconds` của `triage_<người>.csv`) là chỉ số **khác**: đó là thời gian quyết định Nhận/Gán tay/Bỏ, **không phải** thời gian gán điểm. Hiện riêng: trung vị,
  IQR, n, phút cho 100 mặt, theo người rà và lượt; tổng giây của mặt = tổng các dòng có giây; bỏ ô trống (lần bấm đầu phiên, Hoàn tác, `triage_auto`); > 120 giây/mặt (guideline:
  ≤ 30 giây) = ngoại lai "có thể nghỉ giữa chừng", đếm riêng, không vào trung bình. Hiện thêm dòng phụ "sửa nháp + rà so với gán tay" (cộng trung vị giây rà vào giây sửa nháp)
  để thấy chi phí đầy đủ; ghi rõ đây là ước lượng.
- Định dạng đã có (`facetimer.py`) nên **không đặt định dạng mới**; ghi định dạng và chỗ đặt file vào README. File thiếu cột → lỗi rõ tên cột thiếu.

### 4.5 (4) Số lượng dữ liệu và tiến độ
- Theo nguồn (YawDD, DrivFace, không rõ), theo đợt (`dot_anh.list_runs`, bỏ `_nap`, `_trash`, `_smoke`), theo `set`, theo quyết định: số và tỉ lệ Nhận/Gán tay/Bỏ/chưa rà/không
  thấy mặt/đã xoá mềm; số mặt duy nhất và số (lượt, mặt).
- Tiến độ từng thành viên: rà soát (đã rà/tổng mỗi lượt, `done.txt`), ca khó đã đánh dấu (`ca_kho.csv`), file nhãn đã xuất (`raw\`/`final\` theo người, task, ngày), dòng bấm
  giờ theo người × điều kiện so với kế hoạch thí nghiệm (Pk gán tay Xk, sửa nháp X(k+1), P5 sửa X1; 10 mặt/khối, 2 khởi động). Chỉ hiện "kỳ vọng" khi suy được từ kế hoạch.

### 4.6 Trình bày (dataviz)
Nếu phiên có skill `dataviz` hoặc `dataviz-style` thì nạp trước khi viết HTML biểu đồ; không có thì theo đúng các luật sau:
- Dựng bằng **HTML/CSS** (thanh ngang, ô số tiêu đề, bảng), không thêm matplotlib (không có trong `requirements`), không JS ngoài, không CDN, không font tải về. Hàm dựng HTML
  là **một nguồn** cho cả tab và bản xuất tĩnh.
- Chọn dạng theo việc của số: một số tiêu đề → ô số (stat tile) kèm n; độ lớn so sánh giữa nhóm → thanh ngang từ **0**, cùng thang trong một bảng, số in cạnh thanh; không
  biểu đồ tròn, không 3D, **không hai trục y**. Mục tiêu (20% nhanh hơn, 10% IOD mặt hỏng) là một vạch đánh dấu có nhãn chữ.
- Màu theo **ý nghĩa và cố định**: 7 nhóm dùng `mau_nhom.GROUP_COLOR` (giống CVAT và ảnh chồng), Nhận/Gán tay/Bỏ dùng `review_app.STATUS_COLOR` (giống viền ảnh nhỏ);
  một chuỗi số đơn lẻ dùng một màu trung tính; Đạt/Chưa đạt/Chưa kết luận luôn có **chữ + ký hiệu**, không chỉ màu. Màu không bao giờ là cách duy nhất để nhận ra nhóm:
  luôn có tên nhóm tiếng Việt (`GROUP_VI`). Chữ dùng màu chữ của theme (`var(--body-text-color)`…), không dùng màu nhóm cho chữ.
- Nhãn tiếng Việt có dấu, đơn vị rõ (% IOD, giây/mặt, phút/100 mặt); trên trang và HTML dùng dấu phẩy thập phân như tài liệu hiện có, **CSV giữ dấu chấm** để máy đọc;
  tooltip bằng thuộc tính `title`; mọi bảng có bản CSV; chạy được ở theme sáng/tối của Gradio và ở bề rộng 420 px.

### 4.7 Xuất tĩnh và CLI
- Nút "Xuất CSV + HTML" và CLI (mặc định `python tool\thong_ke.py [--luot ...] [--gom-ttest] [--timing <thư mục>] [--out outputs\thong_ke]`) ghi
  `outputs\thong_ke\<YYYYMMDD-HHMM>\`: `thong_ke.html` (một file tự chứa, CSS nội tuyến, sáng/tối theo `prefers-color-scheme`), CSV mỗi bảng (`utf-8-sig`, an toàn công
  thức), `nme_nhap.csv`.
- HTML xuất để đưa vào báo cáo nên: **không ảnh mặt** (YawDD chỉ cho đăng ảnh của một số video), không mã tài xế (`subject`), không đường dẫn tuyệt đối, không token/email;
  có dòng nguồn dữ liệu + "phi thương mại", ngày lập, commit, config version, `t_flip`, danh sách file nhãn đã dùng (tên tương đối). Có test kiểm các điều này.

## 5. Ghép vào trang rà soát
- Hai tab mới **"Thống kê"** và **"Lọc dữ liệu"**, đặt trước "Cài đặt" (thứ tự khác thì nêu lý do). Module riêng (mặc định `tool\thong_ke.py` logic + CLI, `tool\thong_ke_ui.py`,
  `tool\loc_ui.py`); `review_app.py` chỉ thêm vài dòng: tạo tab, `tab.select` làm mới, nối CSS, cập nhật docstring đầu file.
- `allowed_paths`: chỉ thêm **đúng** `outputs\thong_ke` và `outputs\train_sets` (như `ca_kho.serve_dir`), không cả `outputs\`. Không mở thêm đường phát `runs\`, `raw\`, `data\`.
- Handler: `api_visibility="private"`, `concurrency_id` riêng, không chặn các tab khác; tôn trọng `ctx.closing`; lỗi → `gr.Warning` + thông báo tiếng Việt, không traceback lên trang.
- Không gọi mạng, không đọc token. Đường dẫn người dùng gõ ở tab (thư mục bấm giờ, file nhãn, file cấu hình) phải nằm trong thư mục dự án (realpath + commonpath).

## 6. Test (pytest; chỉ dữ liệu giả dựng trong `tmp_path`, không ảnh thật, không mạng)
- **Bảng mặt:** triage nhiều người, dòng Hoàn tác, giây trống, `triage_auto`; `flags.json`, autoqc, `no_face`, `excluded.txt`; manifest → nguồn/subject/set; lượt `inbox\` →
  `khong_ro`; `push.json` → task → `raw\` mới nhất mỗi người, `final\` ưu tiên; `gan_tay_co_nhap`; tên task → điều kiện; nhãn bảy skeleton; nhãn `face50` cũ bị đếm riêng;
  ghép tên chế độ crop/auto và đổi toạ độ khứ hồi; thứ tự 50 điểm theo config (`moingoai_10` sau `moingoai_9`).
- **Lọc:** từng tiêu chí; cờ theo nhóm min/max; `t_flip` null → cảnh báo, `tinh_lai` khớp `steps.flags`; thác nước cộng đủ tổng; `khong_ro`/xoá mềm luôn loại; Bỏ loại mặc định;
  `loc_tap_danh_gia`; một `subject` ở hai split → lỗi và không ghi gì; tất định (chạy hai lần giống từng byte); `--dry-run` không ghi file; tên bộ có `..`/`\` bị từ chối; gói
  chỉ nằm dưới `outputs\train_sets`; `runs\ raw\ final\ data\` không đổi (băm trước/sau); README gói có giấy phép, trích dẫn, "phi thương mại"; cấu hình sai → lỗi rõ;
  `config\loc_mau.json` hợp lệ.
- **Thống kê:** NME tổng/theo nhóm khớp `eval50`; tách manual/assisted; trạng thái trống khi chưa có nhãn (không có số nào); % cờ và AUROC khớp `flag_eval`; giao thức P5
  (warmup, r_i, trung bình nhân, luật Đạt, bootstrap seed 28 lặp lại được, ngoại lai đánh dấu mà không bỏ khỏi chỉ số chính, "n quá nhỏ", < 3 người); giây rà (ô trống,
  > 120 giây); đếm theo nguồn/đợt/quyết định/người; Ttest ẩn mặc định; HTML xuất không có `<img`, không đường dẫn tuyệt đối, không "token", không mã `yd_`/`df_`; CSV an toàn
  công thức.
- **Giao diện (không trình duyệt):** dựng `build_ui` có lượt và chế độ `--nap` (store `None`) vẫn chạy với hai tab mới, theo cách `test_cai_dat.py` và `test_cvat_smoke.py`
  đang làm (`pytest.importorskip('gradio')` rồi `review_app.build_ui(...)`); `allowed_paths` đúng như mục 5 (kiểm theo kiểu đọc mã nguồn như `test_review_app.py`).
- `test_no_torch.py`, `test_chay_bat.py` vẫn xanh. Toàn bộ `python -m pytest tests -q` xanh, số qua ≥ số gốc.
- **e2e Playwright** (mặc định `tests\e2e_thong_ke.py`, tên không khớp `test_*.py` nên pytest không gom): mở trang, chọn hai tab, xem trước lọc, tạo bộ nhỏ, xuất thống kê,
  kiểm không request ra ngoài 127.0.0.1, chụp ảnh desktop 1440×900 và hẹp 420 px vào `%TEMP%\m28_loc_thongke\shots\`. **Chỉ chạy nếu** `python -c "from playwright.sync_api import
  sync_playwright"` chạy được **và** Chromium đã có sẵn; không thì bỏ qua và ghi vào báo cáo. Bước kiểm cổng bằng `lsof` của e2e cũ chỉ có trên Linux: trên Windows bỏ bước
  đó (hoặc dùng `netstat -ano`) và ghi rõ.

## 7. Tự kiểm trên máy (bắt buộc)
1. **Dữ liệu thật, chỉ đọc:** chạy `python tool\thong_ke.py` và `python tool\loc_du_lieu.py --cau-hinh config\loc_mau.json --dry-run` với cwd = `M` trên `runs\`, `data\` thật,
   ghi xuất ra `%TEMP%\m28_loc_thongke\out\` (dùng `--out`). Ghi vào báo cáo: số lượt, số mặt theo nguồn/quyết định, % cờ, lượt nào cờ toàn false, có/không nhãn sửa tay,
   có/không file bấm giờ, thời gian chạy. Kiểm băm `runs\`/`raw\`/`data\` trước/sau không đổi.
2. **Chưa có nhãn sửa tay hay file bấm giờ thật** (khả năng cao trước 14–15/10): dựng thư mục chạy giả `%TEMP%\m28_loc_thongke\work\` (chép `config\`, `data\manifest.csv`, và
   một lượt thật bằng `robocopy`, **không** dùng junction/symlink để khỏi ghi nhầm vào `runs\` thật); tạo **nhãn giả** từ `xml\prelabel.xml` (hoặc `eval50.read_run_pred`): nhiễu
   nhỏ đa số mặt, vài mặt lệch lớn, vài điểm thiếu, vài `low_conf` để bật, hai người, một task manual một task assisted; `push.json` và triage giả có giây; `timing_P1..P5.csv`
   giả đúng 12 cột theo câu nhờ AI trong `p5-thi-nghiem.md` (assisted nhanh hơn 25%, seed cố định, thêm 2 dòng ngoại lai và 1 dòng `interrupted`). Chạy CLI, mở trang
   (`python tool\review_app.py --nap P5` với cwd = `work`, cổng khác nếu 7860 bận: `set GRADIO_SERVER_PORT=7861`), tạo một bộ train nhỏ, xuất thống kê. Kiểm: % nhanh hơn
   ra gần 25%, ngoại lai được liệt kê, không rò rỉ người giữa split, README gói đúng. **Mọi số ở bước này là dữ liệu giả**: ghi rõ như vậy trong báo cáo; không để file giả nào
   trong `M`.
3. **Ảnh chụp tab:** có Playwright thì lấy từ e2e. Không có: chụp `thong_ke.html` xuất ra bằng Edge headless (có sẵn trên Windows, không cài gì):
   `"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" --headless=new --disable-gpu --window-size=1440,2400 --screenshot="%TEMP%\m28_loc_thongke\shots\thongke_html.png" "file:///…/thong_ke.html"`
   (cả bản 420 px); tab Gradio thật thì ghi "chưa chụp" và cách người dùng tự xem (`chay.bat` mục 1 → tab Thống kê). **Xem từng ảnh bằng Read**, ghi nhận xét (nhãn đè nhau,
   tràn ngang, màu, trạng thái trống, theme).

## 8. Tài liệu, sổ quyết định, chay.bat
- `README.md` (ngắn: hai bảng lệnh mới, đầu vào/đầu ra, giới hạn), `HUONG-DAN-WINDOWS.md` (mục mới "Thống kê và lọc dữ liệu train", lệnh cmd từng bước, chỗ đặt
  `timing_P*.csv`, cảnh báo dữ liệu nhạy cảm), `TAI-LIEU-CHI-TIET.md` (chi tiết: nguồn nhãn, cách tính từng số, giao thức P5, ngoại lai, khoá cấu hình lọc, cấu trúc gói),
  docstring đầu `review_app.py`. Ghi số test mới.
- `so-quyet-dinh.md`: thêm **QĐ-005** đúng mẫu cuối file và một dòng ở bảng **Danh sách** (không sửa nội dung QĐ cũ). Nội dung: ngày = ngày chạy phiên; người tham gia: chủ repo
  (chốt), P1, P2, P3, P4, P5 (chờ duyệt); xuất phát từ yêu cầu chủ repo; bối cảnh (cần dữ liệu cho model landmark khác sau này, cần số liệu cho báo cáo/demo); phương án:
  không làm (loại), lọc + train ngay (loại: MediaPipe không train được, không GPU, ngoài phạm vi), **bộ lọc chỉ chuẩn bị dữ liệu, chưa train, kèm trang Thống kê (chọn)**;
  quyết định: tiêu chí, chia theo `set` gốc (không rò rỉ người), luật cứng `khong_ro`, tốc độ theo giao thức P5, Ttest ẩn mặc định, xuất tĩnh không ảnh mặt, phi thương mại;
  việc phải làm theo (@P5 duyệt cách tính tốc độ/ngoại lai và bố cục cho báo cáo; @P2 duyệt thống kê cờ và `t_flip` dùng để tính lại; @P4 xác nhận quy ước `raw\`/`final\`,
  tên task thí nghiệm; @P1 duyệt ánh xạ train/val/test; @P3 duyệt NME theo nhóm và `tolerance`; chủ repo cập nhật `CLAUDE.md`/Claude Docs); trạng thái Hiệu lực.
- `chay.bat`: mặc định **không thêm mục** (hai tab mở qua mục 1/2). Chỉ thêm nếu thật cần; khi đó giữ ASCII + CRLF, cập nhật `tests\test_chay_bat.py` giữ đủ mọi kiểm cũ.
- `.gitignore`: kiểm `outputs\`, `timing_*.csv`, `*.zip`, `*.png` đã bị chặn; không gỡ dòng nào.

## 9. Trình tự commit (mỗi bước một commit nhỏ, test liên quan xanh trước khi commit)
1. Bảng mặt (`bang_mat`) + test. 2. Tách hàm trả dict ở `flag_eval`/`eval50` nếu cần (đầu ra CLI không đổi) + test. 3. Bộ lọc: logic, `loc_du_lieu.py`, `config\loc_mau.json` + test.
4. Thống kê: logic + CLI + xuất tĩnh + test. 5. Hai tab + nối vào `review_app` + test giao diện. 6. e2e (nếu có Playwright). 7. Tài liệu + QĐ-005.
Trước mỗi commit: `git status` (không ảnh, không `runs\`/`data\`/`outputs\`/`raw\`/zip, không file trong `%TEMP%`), `git diff --stat`.

## 10. Tự soát trước khi báo cáo
Đọc lại **toàn bộ diff** (`git diff main...HEAD`), rồi ghi Đạt/Chưa/Lý do cho từng mục: (1) đủ tiêu chí bắt buộc (cờ tổng và theo nhóm) và luật cứng; (2) chia theo người, có kiểm
`subject`; (3) gói đúng cấu trúc, tất định, README giấy phép; (4) đủ 4 nhóm thống kê, trạng thái trống không bịa số, n và "n quá nhỏ"; (5) tốc độ đúng giao thức P5, ngoại lai,
giây rà tách riêng; (6) tab chạy 127.0.0.1, `allowed_paths` hẹp, không ảnh trong HTML xuất; (7) chỉ đọc `runs\ raw\ final\ data\`; (8) không thêm gói, không code train,
`test_no_torch` xanh; (9) pytest ≥ gốc; (10) tài liệu + QĐ-005; `de-tai-m28\`, `CLAUDE.md` không đổi; (11) không đường dẫn máy, không token trong repo; không push.

## 11. Báo cáo cuối (tiếng Việt, trung thực, ngắn mà đủ)
1. Tóm tắt; nhánh và `git log --oneline main..HEAD`.
2. **Danh sách file** thêm/sửa theo nhóm (tool, config, tests, tài liệu, sổ quyết định).
3. **Mặc định bạn đã tự chọn** (tên module, khoá cấu hình, ánh xạ split, ưu tiên nhãn, điều kiện theo tên task, ngưỡng n nhỏ và ngoại lai, vị trí tab, thư mục xuất…) và lý do.
4. Số liệu tự kiểm trên **dữ liệu thật** (mục 7.1) và trên **dữ liệu giả** (mục 7.2, ghi rõ là giả), thời gian chạy.
5. **Ảnh chụp tab** đã xem (đường dẫn trong `%TEMP%`, mỗi ảnh một dòng nhận xét); ảnh nào chưa chụp và vì sao.
6. pytest: số gốc → số sau (qua/bỏ qua), test mới; e2e chạy hay bỏ qua (lý do).
7. **Chưa thử:** ví dụ nhãn thật từ CVAT (bảy skeleton xuất thật), file bấm giờ thật 14–15/10, `final\`, lượt chế độ `auto`, Gradio trên trình duyệt thật nếu không có Playwright,
   gói zip lớn.
8. **Việc cần người đồng ý:** P5 (giao thức tốc độ, ngoại lai, giây rà, bố cục cho báo cáo), P2 (thống kê cờ, `t_flip` khi tính lại, AUROC), P4 (quy ước `raw\`/`final\`,
   tên task thí nghiệm, liên kết `push.json`), P1 (ánh xạ train/val/test, dùng Ttest làm test của model sau), P3 (NME theo nhóm, `tolerance` mặc định 3% IOD), chủ repo (QĐ-005,
   luật cứng `khong_ro`, Ttest ẩn mặc định); kèm đề xuất sửa `CLAUDE.md`/Claude Docs.
9. Lệnh người dùng chạy tiếp (cmd): xem commit, chạy test, mở trang, dry-run bộ lọc.
