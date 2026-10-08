> **Cách dùng (máy Ubuntu của chủ repo):** ở thư mục repo chạy `git checkout main && git pull`, mở Claude Code trong thư mục đó rồi gõ:
> `Đọc source-tool/m28-prelabel/prompts/prompt_m28_dongho_thongke_job_local.md và thực hiện đúng và đầy đủ.`

# Prompt LOCAL (Ubuntu), ba việc trong một lượt: (1) `collect` xuất nhãn theo từng job, (2) tab "Đồng hồ" bấm giờ, (3) tab "Thống kê" thu gọn, kèm gói kết quả gửi nhóm trưởng

Làm theo thứ tự: **PHẦN 1** (xuất theo job) → **PHẦN 2** (đồng hồ + thống kê). Hai phần bên dưới do hai người soạn riêng; khi mâu thuẫn thì **mục 0Z này thắng**.

## 0Z. GHI ĐÈ (chủ repo chốt ngày 8/10/2026; ưu tiên hơn mọi chỗ trong hai phần bên dưới)

**Môi trường.** Phần 1 viết như chạy trên cloud: bỏ mọi giả định "cloud", "không có CVAT": đây là máy Ubuntu của chủ repo, có CVAT local ở `http://localhost:8080`.
Test vẫn dùng CVAT giả (`tests/fake_cvat`). Được phép thử `collect` trên CVAT local thật CHỈ với task `demo-` mà chính phiên này tạo ra rồi xoá đi; không đụng task có sẵn; không ghi token vào đâu.
Mọi lệnh bash, đường dẫn `/`. Mọi quy tắc của 0A ở Phần 2 (nhánh, KHÔNG push, không ảnh/runs/data/outputs/token vào git…) áp dụng cho cả hai phần. Dùng MỘT nhánh `dong-ho-thongke` cho cả ba việc (Phần 1 commit trước), trừ khi 0B của Phần 2 nói phải chọn nhánh gốc khác.

**Thiết kế thí nghiệm mới: HAI NHÓM ĐỘC LẬP (thay cho ghép cặp Pk gán tay Xk / sửa X(k+1)).** Đội chia làm hai nhóm: nhóm MANUAL gán tay hoàn toàn; nhóm ASSISTED dùng tool (sửa nháp). Hệ quả cho code:
1. File cấu hình `config/nhom_thi_nghiem.json` (có file mẫu, giá trị rỗng/ví dụ; không đoán ai ở nhóm nào): `{"nhom": {"P1": "manual"|"assisted", ...}, "bo_anh": "<tên bộ ảnh chung>"}`. Tab Đồng hồ lấy điều kiện từ đây (người chưa có nhóm thì cho chọn tay và cảnh báo). Kiểm hai nhóm làm CÙNG bộ ảnh (cùng tên ảnh); báo nếu lệch.
2. Thống kê thời gian = so hai nhóm ĐỘC LẬP (không ghép cặp theo người): giây/mặt mỗi nhóm (trung vị, trung bình nhân), % nhanh hơn của assisted so với manual (mục tiêu ≥20%), khoảng tin cậy bằng bootstrap CÓ GỘP THEO NGƯỜI (cluster bootstrap: bốc lại người rồi bốc lại mặt trong người; seed cố định, 2.000 lần), kèm n người và n mặt mỗi nhóm; mỗi nhóm <2 người thì ghi rõ "chỉ có kết quả mô tả, chưa kết luận được". Xoá/thay các chỗ Phần 2 §4.5 đòi ghép cặp, "đủ 5 người", khối Xk/X(k+1). Vẫn loại mặt khởi động (warmup) như P5.
3. NME và tỉ lệ điểm phải sửa chỉ có ở nhóm ASSISTED (cần nháp). Đáp án để đo NME của nháp = nhãn gán tay của nhóm MANUAL trên cùng ảnh (hai nhóm làm chung bộ ảnh): nếu một ảnh có nhiều nhãn manual thì lấy trung bình điểm theo tên điểm và báo số người; ảnh chưa có nhãn manual thì không tính NME (ghi "chưa có đáp án"). Ngoài ra vẫn tính NME của nhãn cuối của nhóm ASSISTED so với nhãn MANUAL (để kiểm "nhanh hơn mà nhãn không kém đi"). Thông báo rõ trên trang các hạn chế của thiết kế hai nhóm: tốc độ từng người khác nhau lẫn vào kết quả; gợi ý (không bắt buộc) một đợt khởi động chung hoặc chia nhóm cân tốc độ.
4. Ghi QĐ mới trong `so-quyet-dinh.md` (số kế tiếp, nêu: đổi từ ghép cặp sang hai nhóm độc lập, lý do, hạn chế trên, cần P5 + mentor đồng ý trước 14/10) và sửa đoạn "Thí nghiệm:" trong `CLAUDE.md` cho khớp (ghi "đổi theo QĐ-xxx"). KHÔNG sửa `de-tai-m28/`. Nêu trong báo cáo các chỗ của kế hoạch gốc cần cập nhật.

**Đồng hồ: đơn vị đo là PHIÊN (từ lúc nạp ảnh lên tool đến lúc hoàn thành), không bắt buộc bấm từng mặt.**
- Chủ repo mô tả: *khi bắt đầu nạp ảnh lên tool thì đồng hồ bắt đầu; khi hoàn thành thì xuất ra file export chứa thời gian và kết quả để gửi nhóm trưởng tổng kết.* Nút: **Bắt đầu, Tạm dừng/Tiếp tục, Hủy (có xác nhận), Xong (lưu & xuất)**. Nối với tab "Nạp ảnh": nạp xong một đợt thì tab Đồng hồ gợi ý "Bắt đầu đồng hồ cho đợt này?" (không tự chạy ngầm; người dùng bấm xác nhận một lần, hoặc có ô tự bắt đầu khi nạp nếu bật).
- Phần 2 §3.1 (bấm từng mặt, mặc định) đổi thành TUỲ CHỌN: giữ nút "Xong mặt này → mặt tiếp" cho ai muốn đo chi tiết; nếu chỉ đo cả phiên thì giây/mặt = giây phiên (không tính lúc tạm dừng) / số mặt đã xử lý, và cột tương ứng trong CSV ghi rõ "uoc_luong_chia_deu" để thống kê biết đây là ước lượng, không phải đo từng mặt.
- **Xong (lưu & xuất)** tạo MỘT file gói kết quả ngoài git: `outputs/ket_qua/ketqua_<Pk>_<DDMM>_<đợt>.zip` (kèm bản `.json` đọc được) để gửi nhóm trưởng, chứa: người, nhóm (manual/assisted), đợt/bộ ảnh, số mặt, giây phiên (không tính tạm dừng), số lần tạm dừng, giờ bắt đầu/kết thúc, và KẾT QUẢ theo mặt: tên ảnh (không đường dẫn tuyệt đối), nhãn cuối 50 điểm (toạ độ) nếu có, và với nhóm assisted thêm nháp 50 điểm + điểm nào đã sửa + NME nháp-so-nhãn-cuối. Gói KHÔNG chứa ảnh, không chứa token/email/tên máy/đường dẫn tuyệt đối, không chứa mã tài xế ngoài tên ảnh; có `sha256` và số phiên bản định dạng.
- Thêm **công cụ tổng kết cho nhóm trưởng**: `tool/tong_ket.py --vao <thư mục chứa các gói> --ra outputs/tong_ket/` (và nút trong tab Thống kê "Nạp các gói kết quả của nhóm"): kiểm sha256/định dạng, loại gói trùng/hỏng với thông báo rõ, gộp các người, rồi tính ba chỉ số của Phần 2 theo thiết kế hai nhóm ở trên, xuất CSV + HTML tĩnh (không ảnh). Nhóm trưởng chỉ cần gói của các thành viên, không cần ảnh hay CVAT.
- Mọi quy tắc quyền riêng tư giữ nguyên: dữ liệu chỉ lưu nội bộ nhóm; không phát tán.

Phần 3 (báo cáo cuối) phải thêm: ba việc đã làm riêng từng việc, mẫu một gói kết quả (với dữ liệu giả, chỉ cấu trúc), mẫu tên file job, và danh sách điểm cần P5/P4/mentor đồng ý.

---

# PHẦN 1 — `collect` xuất nhãn theo từng job

# Prompt chạy CLOUD (Linux): M28, `collect` xuất nhãn theo từng job

Bạn là kỹ sư triển khai trong repo đề tài M28 (đội T015-SIXSEVEN), chạy **trên máy cloud Linux** (Claude Code). Làm **toàn bộ** việc dưới đây trong phiên này,
tự kiểm bằng test và CVAT GIẢ, rồi viết báo cáo cuối trung thực. Viết code, tài liệu và báo cáo bằng **tiếng Việt**.
Chủ repo đã chốt yêu cầu ở mục 1 và mục 3. **Chi tiết nhỏ bạn tự quyết**: chọn cách đơn giản, an toàn, khớp code hiện có, và ghi mọi mặc định đã chọn vào báo cáo.
Bạn **được đổi** một điểm thiết kế ở mục 3 nếu nêu rõ lý do trong báo cáo. Chỉ dừng lại hỏi khi một việc trái mục 0A hoặc trái `CLAUDE.md`.

## 0A. Môi trường và luật làm việc (ưu tiên hơn mọi chỗ khác trong file này)

- **Đường dẫn.** Repo: thư mục hiện tại (máy local), nhánh `main`. Đặt `M` = `source-tool/m28-prelabel`. Mọi lệnh của tool và pytest chạy với **cwd = `M`**
  (`raw/`, `final/`, `outputs/`, `runs/`, `config/` tính từ `M`). Script tạm, dữ liệu giả, thư mục chạy thử: để trong thư mục scratchpad của phiên nếu có, không thì
  `/tmp/m28_xuat_job/` (tạo mới, **ngoài repo**). Không ghi đường dẫn tuyệt đối của máy vào code hay tài liệu.
- **Git: KHÔNG commit, không tạo nhánh, không push, không PR.** Trước khi sửa: `git status` phải sạch (không sạch thì DỪNG và báo, không stash, không xoá). Sửa thẳng
  trên cây làm việc của `main`; cuối phiên ghi `git status` và `git diff --stat` vào báo cáo để chủ repo tự đọc rồi quyết.
- **Không có CVAT thật, không GPU.** Mọi thử nghiệm với CVAT dùng gói giả `tests/fake_cvat/cvat_sdk/` (pytest nạp bằng monkeypatch như `tests/test_push.py`;
  chạy tay qua tiến trình con thì `PYTHONPATH=tests/fake_cvat` và `M28_FAKE_CVAT_STATE=<file json trong thư mục tạm>`, token giả qua biến môi trường).
  Không gọi mạng, không tải dữ liệu, **không cần ảnh mặt nào**: chỉ dùng ảnh giả (`b'x'` hoặc PNG xám) và XML giả như các test hiện có.
- **Code phải chạy trên Windows/cmd, Python 3.14** (máy của đội) dù bạn thử trên Linux: chỉ thư viện chuẩn trong phần tách job (không numpy, không cvat_sdk, không
  lxml), `os.path` thay cho `/` cứng, file văn bản ghi `encoding="utf-8", newline="\n"`, in ra màn hình đường dẫn bằng `os.path.join` (cmd thấy `raw\...`).
- **pytest gốc.** Trước khi sửa, trong `M`: `python -m pytest tests -q`, ghi số thật (người điều phối ghi **665 qua + 1 bỏ qua**). Sau khi xong: số qua **không ít hơn**
  số gốc cộng số test mới, **không test cũ nào bị xoá hay nới lỏng**. Buộc phải sửa một test cũ thì nêu tên và lý do trong báo cáo.
- **Quyền riêng tư (giữ nguyên `CLAUDE.md`).** `raw/`, `final/`, `outputs/`, `runs/`, `data/`, ảnh, zip, file xuất CVAT không bao giờ vào git (`.gitignore` đã chặn;
  không gỡ dòng nào). Không ghi token, mật khẩu, email vào code, log, `.txt`, báo cáo, `outputs/`.
- **Không sửa:** `de-tai-m28/` (bản chụp kế hoạch), `CLAUDE.md`, `so-quyet-dinh.md` (đề xuất trong báo cáo nếu cần). **Tránh sửa `tool/review_app.py`** và mọi phần
  thống kê/lọc dữ liệu: việc đó đang làm ở nhánh khác trên máy khác (nhánh đó **đọc** `collect.latest_raw_files`, `collect.push_info`, `RAW_RE`, nên các hàm này phải
  giữ nguyên hành vi và giá trị trả về). Không sửa `chay.bat`/`chay.sh` (không thêm mục menu).

## 0. Đọc trước khi sửa (đọc hết, không đọc lướt)

- `CLAUDE.md`, `so-quyet-dinh.md` (QĐ-001..QĐ-004).
- Trong `M`: `README.md`, `HUONG-DAN-WINDOWS.md` (mục 7: `push`/`collect`), `HUONG-DAN-UBUNTU.md`, `TAI-LIEU-CHI-TIET.md` (mục "push và collect (CVAT)",
  "Kiểm tra nhanh CVAT", bảng hợp đồng giữa các phần).
- `tool/m28core/collect.py`: `_jobs_info`, `_meta_text`, `_jobs_from_txt`, `RAW_RE`, `latest_raw_files`, `push_info`, `analyze`, `_qc_line`, `collect`.
- `tool/m28core/push.py`: `plan_jobs` (các nhóm `job_size` mặt Nhận rồi **một** job Gán tay ở cuối; trả `groups, kinds`), `_jobs_of` (ghi vào `push.json` khoá `jobs`
  = danh sách `{id, start_frame, stop_frame, n, kind}` với kind `nhan`/`gan_tay`), `_xml_for_frames` (id ảnh = số frame thật của task), `push.json`
  (`task`, `task_id`, `phien_ban`, `gan_tay_co_nhap`, `so_anh`, `job_file_mapping`, `jobs`, `cap_nhat`, `trang_thai`).
- `tool/m28core/steps.py`: `push` (ghi `runs/<run>/push/manual_list.txt` = tên ảnh Gán tay + `co_nhap`/`anh_trong`; XML nháp ở `runs/<run>/xml/prelabel.xml`),
  `read_manual_list`, `collect`.
- `tool/m28core/cvat_io.py` (`parse_annotations`, `MAX_XML`, `safe_file_part`, `inside`, `VN_TZ`, `scrub`), `tool/eval50.py` (`read_labels`, `evaluate`),
  `tool/m28.py` (`build_parser`, `main`), `tool/cvat_smoke.py` (bước 9 `s9`).
- `tests/test_push.py` (fixture `cvat`, `make_run`, `do_push`, `collect_args`, mọi test `test_collect_*`, `test_signatures_match_real_sdk`), `tests/test_gan_tay.py`
  (test collect và `test_collect_push_info_picks_matching_task_version_2_only`), `tests/test_m28.py` (`test_collect_needs_task_and_passes_args`),
  `tests/test_cvat_smoke.py`, `tests/fake_cvat/cvat_sdk/__init__.py` (`create_from_data` chia job theo `job_file_mapping`, job id bắt đầu từ 100;
  `Task.export_dataset` ghi `<image id="<số frame>" name=...>`, **không có `<meta>`**).
- `de-tai-m28/p4-cvat.md` (chỉ đọc): mục `export.py` (dòng có `python tool\export.py <task> <Pk> <ngày>`, `--final`, `--check`), "Tên file … raw/ giữ file xuất gốc,
  không bao giờ sửa", các lệnh đếm file kiểu `dir raw\m28-gold-*`, `raw/*_1410.xml`, `raw/m28-practice_*`, mục "Task" (task thí nghiệm `m28-…` có đúng **một** job).

## 1. Vấn đề (chủ repo nêu)

`push` đẩy mỗi lượt thành **một** task CVAT `demo-…`, chia nhiều job qua `job_file_mapping`: mỗi job `job_size` (mặc định 8) mặt Nhận, cộng **một** job Gán tay riêng ở
cuối. Hiện `collect` chỉ xuất **cả task** ra `raw/<task>_<người>_<DDMM>.xml` (+ `.txt` liệt kê job id, số frame, stage, state); chưa lấy riêng được từng job (ví dụ chỉ
job Gán tay, hay job một người đã sửa). Chủ repo muốn xuất được theo **từng job mà tool đã chia**.

## 2. Những bẫy đã thấy trong code (đọc kỹ, đừng làm hỏng)

1. **`push.json` nằm ở `runs/<run>/push.json`** (`push.pj_path`), không phải `runs/<run>/push/push.json`; thư mục `runs/<run>/push/` chỉ có `done.txt`,
   `manual_list.txt`, `rejected.csv`. `push_info` dò `runs/*/push.json`.
2. **Không đổi giá trị trả về của `push_info`**: `tests/test_gan_tay.py` so bằng `==` với dict 4 khoá, và nhánh thống kê ở máy khác dùng nó. Cần thêm thông tin job thì
   viết **hàm mới** (ví dụ `push_jobs(task, runs_dir="runs", task_id=None)`) hoặc tham số tuỳ chọn mặc định giữ nguyên kết quả cũ. `jobs` kèm `kind` đã có trong
   `push.json` từ bản push đầu tiên (cả `phien_ban` 1), nên đọc `kind` không cần lọc `phien_ban >= 2` như `push_info`; nhưng nếu biết `task_id` (từ `.txt`) thì
   **chỉ** nhận `push.json` có `task_id` trùng (task xoá rồi tạo lại cùng tên sẽ có id khác).
3. **Tương thích ngược của `.txt` có bẫy:** `_jobs_from_txt` dùng `re.match(r"job (\d+): (\d+) frame, stage (\S+), state (\S+)")`. `\S+` ăn cả dấu phẩy/chấm phẩy
   đi liền sau state: viết `state completed, frames 0-7` thì bản cũ đọc ra state `completed,` và báo sai "chưa sửa xong". Trường mới **phải cách state bằng dấu cách**,
   ví dụ `job 101: 8 frame, stage annotation, state completed | frames 0-7 | loai nhan`. Có test chạy **đúng biểu thức cũ** (chép nguyên văn vào test) trên dòng mới.
4. **`RAW_RE`/`latest_raw_files` phải tiếp tục bỏ qua file job**: mẫu `^(?P<task>.+)_(?P<who>[A-Za-z0-9-]+)_(?P<day>\d{4})\.xml$` không khớp
   `…_0810_job101.xml` (cũng không khớp `_job1234.xml`). Giữ đúng như vậy và có test (job id 1, 3, 4, 5 chữ số): nếu file job lọt vào đây, collect, eval và thống kê
   ở nhánh khác sẽ **đếm một mặt hai lần**.
5. **`tool/cvat_smoke.py` bước 9 sẽ HỎNG** nếu tách job bật mặc định: nó đếm `raw/demo-smoke_SMOKE_*.xml` và đòi **đúng 1** file. Sửa bộ lọc để bỏ file `_job<id>`
   (dùng `RAW_RE`), và **nên** thêm kiểm con: tách được 3 file job với số ảnh [1, 1, 2], job cuối là `gan_tay` và chứa đúng ảnh Gán tay. Đây là chỗ duy nhất kiểm được
   giả định "id ảnh = số frame trong task" trên **CVAT thật** (mỗi thành viên chạy `cvat_smoke.py` trên máy mình). `tests/test_cvat_smoke.py` và
   `test_signatures_match_real_sdk` (gọi `cvat_smoke.run`) phải vẫn xanh.
6. **Chuỗi mà test cũ đòi KHÔNG có trong báo cáo:** `test_collect_demo_task_with_old_push_json_or_m28_task_unchanged` đòi `'Gán tay:'` và `'ở mặt Nhận'` không xuất
   hiện khi `push.json` là bản 1 hoặc task `m28-…`. Phần báo cáo theo job ghi loại bằng mã `nhan`/`gan_tay`/`khong_ro` (hoặc chữ khác không chứa đúng hai chuỗi đó).
   Các test khác tìm `'mặt đủ 50 điểm: 3'`, `'chưa sửa xong'`, `'Thời gian từng bước'`: giữ nguyên các dòng cũ, chỉ **thêm** phần mới.
7. **`collect_args()` trong test và `cvat_smoke.s9` dựng `SimpleNamespace` không có thuộc tính mới**: đọc cờ mới bằng `getattr(args, "per_job", None)`,
   `getattr(args, "job", None) or []`.
8. **`--dry-run` không được tạo thư mục `raw/` hay `outputs/`** (test đã kiểm). Lỗi "task trùng tên/không có" thì `raw/` phải rỗng (test đã kiểm).
9. **XML của CVAT giả không có `<meta>`**, của CVAT thật thì có (`<meta><task><size>…</size>…<segments><segment><id/><start/><stop/><url>…/api/jobs/<id></url>…`,
   và `<owner>` có thể kèm **email**). Test phần `<meta>` bằng XML viết tay. Giữ `<meta>` trong file job như file gốc nhưng **không bao giờ** in nội dung `<meta>` ra
   màn hình, `.txt` hay báo cáo.
10. `ElementTree` bỏ chú thích XML khi đọc lại (test `test_collect_does_not_overwrite_raw` thêm `<!-- sửa tay -->` vào file cả task): chấp nhận được cho file job (file
    dẫn xuất), nhưng **mọi phần tử và thuộc tính trong từng `<image>` phải giữ nguyên** (skeleton, points, attribute `low_conf`, box/tag nếu có).
11. **QC/đếm hai lần:** `_qc_line(all_paths, …)` nhận danh sách file; **không** đưa file job vào đó (chỉ file cả task như cũ).
12. **Kế hoạch P4 đếm file bằng glob** (`raw/*_1410.xml`, `dir raw\m28-gold-*`, `raw/m28-practice_*`): tên file job có đuôi `_job<id>` sau ngày nên không khớp
    `*_DDMM.xml`, nhưng **sẽ khớp** `raw\m28-practice_*` nếu tách job cho task `m28-…`. Đó là một lý do để mặc định **không** tách task `m28-…` (task thí nghiệm có
    đúng một job, tách cũng vô nghĩa).

## 3. Thiết kế đã chốt (đổi được nếu nêu lý do)

### 3.1 Tách OFFLINE từ file XML cả task (không gọi thêm API)
- Module logic mới chỉ dùng thư viện chuẩn (mặc định `tool/m28core/tach_job.py`; tên khác được nếu có lý do), không import cvat_sdk. `collect` và CLI ở 3.5 cùng gọi
  module này, không viết hai lần.
- Nguyên tắc: trong file "CVAT for images 1.1" xuất từ task, `<image id>` = **số frame trong task**; job là các khoảng liên tiếp `start_frame..stop_frame`
  (CVAT 2.77 tạo segment kiểu RANGE theo `job_file_mapping`; push đã dựa vào điều này ở `_xml_for_frames`). Ảnh có id trong `[start, stop]` thuộc job đó.
- Ranh giới job lấy từ **file `.txt` cạnh file XML đang tách** (ghi cùng lúc với file đó). `.txt` có `frames a-b` thì dùng; `.txt` cũ không có thì **tính cộng dồn từ `n`**
  theo thứ tự các dòng job (dòng job luôn ghi theo `start_frame` tăng dần) và ghi chú "frame suy ra từ số frame cộng dồn (.txt cũ)". Thiếu `.txt` thì **không đoán**:
  báo "không biết ranh giới job". (Tuỳ chọn, không bắt buộc: khi thiếu `.txt` mà XML có `<meta>…<segments>` với `<url>…/jobs/<id>` thì dùng segment, ghi rõ nguồn.)
- Kiểm **trước khi ghi bất kỳ file job nào** của một file XML (tất cả hoặc không): id ảnh phải là số nguyên, không trùng; khoảng job không chồng nhau; **mọi** ảnh rơi vào
  đúng một job. Ảnh có id **ngoài mọi job** → lỗi rõ (tên ảnh, id, các khoảng job, cách xử lý), không ghi file job nào cho file đó. Phần tử lạ ở gốc (không phải
  `version`, `meta`, `image`) → lỗi rõ, không đoán.
- File job: giữ `<version>`, giữ `<meta>` nhưng **sửa số ảnh** (`meta/task/size`, và `meta/job/size` nếu có) bằng số `<image>` trong file job; mặc định không đụng phần
  còn lại của `<meta>` (nếu bạn lọc `<segments>` còn đúng job đó thì ghi rõ trong `.txt` và tài liệu). Giữ nguyên `id`/`name` ảnh gốc (id **không** đánh lại từ 0).
  Ghi `<?xml … encoding="utf-8"?>`. Đọc qua giới hạn `cvat_io.MAX_XML`.
- **Không ghi đè**, giống quy tắc hiện có: file job đã có thì giữ nguyên, in "đã có: KHÔNG ghi đè", vẫn dùng file đó trong báo cáo. Ghi qua file tạm rồi `os.replace`,
  kiểm tồn tại ngay trước khi thay (hoặc mở độc quyền `"x"`). Đường ghi phải nằm trong thư mục đích (`cvat_io.inside`), phần tên qua `safe_file_part`.
- **Ghi chú trong tài liệu và `.txt`: file job chỉ để đọc/đo (eval50, QC, xem lại), KHÔNG dùng để nhập lại vào CVAT** (nhập file job vào task sẽ thay toàn bộ nhãn
  của task bằng nhãn của một job).

### 3.2 Tên file và `.txt`
- Tên file job = **tên gốc của file cả task + `_job<id>`**: `raw/<task>_<người>_<DDMM>_job<id>.xml` và `.txt` cùng tên. Ngày và người lấy **từ tên file nguồn**
  (không phải ngày hôm nay), để file job luôn đi cặp với file nguồn của nó (kể cả khi tách lại một file cũ bằng CLI). Thêm hằng `JOB_RE` cho mẫu này nếu cần liệt kê.
- `.txt` cả task (do `_meta_text` ghi): giữ mọi dòng cũ; dòng job thêm trường mới **sau dấu cách**:
  `job <id>: <n> frame, stage <stage>, state <state> | frames <a>-<b> | loai <nhan|gan_tay|khong_ro>`. `loai` lấy từ `push.json` (bẫy 2): trùng `task` và (nếu có)
  `task_id`, tra theo **job id**; không có `push.json` hay không thấy job id thì `khong_ro`.
- `_jobs_from_txt` mở rộng: đọc được cả dòng cũ lẫn dòng mới; trả thêm `start`, `stop`, `kind` (mặc định `khong_ro`) và cờ cho biết frame là suy ra; mọi người gọi cũ
  (`collect`, `cvat_smoke`) vẫn chạy (khoá cũ `id`, `n`, `stage`, `state` giữ nguyên nghĩa).
- `.txt` của file job (mặc định, bạn chốt tên khoá): `nguon` (tên file cả task, tương đối), `task`, `task_id`, `job`, `loai`, `frames a-b`, `so_frame_job` (n),
  `so_anh_trong_file`, frame thiếu (nếu có), `stage`, `state`, `tach_luc` (giờ Việt Nam, UTC+7), ghi chú "tách offline từ file cả task, không gọi CVAT; id/name ảnh giữ
  như file cả task; `<meta>` giữ nguyên trừ số ảnh; không dùng để nhập lại vào CVAT", cảnh báo lệch (3.6) nếu có, và **một dòng job đúng định dạng ở trên** để
  `_jobs_from_txt` cũ lẫn mới đều đọc được. Không ghi email, token.

### 3.3 Cờ của `collect`
- `--per-job` / `--no-per-job` (ví dụ `argparse.BooleanOptionalAction`, `dest="per_job"`, mặc định `None` = tự động). **Tự động = BẬT cho task `demo-…`** (cả khi
  vừa xuất lẫn khi đọc `raw/` bằng `--skip-export`), **TẮT cho task khác** (`m28-…`, bẫy 12). `--per-job` bật cho mọi task được nêu: task không đủ thông tin (thiếu
  `.txt`) thì báo rõ trong màn hình và báo cáo, không làm sập lệnh.
- `--job <id>` (`action="append"`, `type=int`, dùng nhiều lần): chỉ ghi file job của các id đó; ngầm bật tách job. **File cả task vẫn được xuất và ghi như cũ** (nó là
  nguồn để tách và là "file xuất gốc" của `raw/`); mặc định này nêu trong báo cáo. Id không thuộc job nào của các task đã nêu → `SystemExit` tiếng Việt liệt kê các job id
  hợp lệ theo task, **trước khi xuất hay ghi bất kỳ file nào** (khi xuất từ CVAT: kiểm sau `get_jobs()`, trước `export_dataset`; tách thành hai lượt "liệt kê job"
  rồi "xuất" trong cùng phiên kết nối nếu cần). `--job` đi cùng `--no-per-job` → lỗi tham số.
- `m28.py`: thêm hai cờ vào `build_parser`, chỉ hợp lệ với lệnh `collect` (lệnh khác → `p.error`, như `--resume`); cập nhật docstring đầu file và `help`.
- `--dry-run`: in thêm `frames a-b`, loại job và tên file job **sẽ** ghi (đánh dấu job được chọn bởi `--job`); không ghi gì, không tạo thư mục.
- Luồng tách trong `collect`: với mỗi file cả task (vừa xuất, hoặc đã có và không ghi đè, hoặc file mới nhất của mỗi người khi đọc `raw/`), tách theo `.txt` **cạnh file
  đó**. File cả task đã có từ trước mà `.txt` của nó ghi `task_id` khác task đang thấy trên CVAT → không tách bằng job của CVAT, dùng `.txt` của chính file đó (hoặc báo
  không tách được). Lỗi tách của một task **không** làm mất file cả task và không chặn task khác: in lỗi rõ, ghi vào báo cáo (mục "Tách job"), `collect` vẫn lập báo
  cáo. (Lỗi người dùng sửa được ngay như `--job` sai thì `SystemExit` như trên.)
- **Luồng cả task không đổi hành vi**: với `--no-per-job`, `raw/` chỉ có đúng hai file như trước, lời gọi CVAT giống hệt (cùng số `export_dataset`), báo cáo giữ mọi
  dòng cũ. Tách job **không** thêm lời gọi CVAT nào (kiểm bằng log của CVAT giả).

### 3.4 Báo cáo `outputs/collect_<tag>.md`
- Giữ nguyên mọi dòng hiện có. Dưới mỗi file cả task, thêm bảng "Theo job" khi có file job: job id, loại (`nhan`/`gan_tay`/`khong_ro`), frame `a-b`, số ảnh trong file /
  số frame của job, **số ảnh có nhãn** (có skeleton), mặt đủ 50 điểm, điểm thiếu, điểm `low_conf` đang bật, stage/state, tên file (ghi "đã có từ trước" nếu không ghi
  mới). Số liệu tính bằng `analyze` trên bytes của file job (job `gan_tay` dùng `tay_nhap` từ `push_info` nếu có, như file cả task).
- Thêm mục "Tách job" khi có lỗi/cảnh báo (thiếu `.txt`, id ngoài mọi job, ảnh lệch job, frame thiếu). Thêm thời gian bước "tách job" vào "Thời gian từng bước".
- QC: chỉ file cả task như cũ (bẫy 11); thêm một câu "file job không đưa vào QC để không đếm hai lần".

### 3.5 Công cụ riêng `tool/tach_job.py` (offline, không CVAT)
```
python tool\tach_job.py --xml raw\<file>.xml [--txt raw\<file>.txt] [--out raw\] [--job ID ...]
```
- `--txt` mặc định: file `.txt` cùng tên cạnh `--xml`. `--out` mặc định: thư mục chứa `--xml`. `--job` lặp được (hoặc `nargs="+"`, bạn chọn, ghi tài liệu). Không cần
  `--config` (tuỳ chọn thêm `--config` để in số mặt đủ 50 điểm; không có config thì chỉ in số ảnh và số ảnh có skeleton).
- In từng job: id, loại, frame, số ảnh, tên file đã ghi / "đã có: KHÔNG ghi đè". `--help` tiếng Việt; `sys.stdout.reconfigure(encoding="utf-8")` như `eval50.main`
  (cmd Windows). Mã thoát (đề xuất): 0 xong (kể cả khi mọi file đã có), 2 lỗi đầu vào (thiếu file, thiếu `.txt`, id ngoài mọi job, `--job` không tồn tại). Hàm
  `main(argv=None)` trả mã để test gọi trực tiếp. Dùng được cho file trong `final/` (`--out final\`).
- Chạy được với file của task lạ (ví dụ `m28-…`) nếu có `.txt` đủ thông tin; không có thì lỗi rõ cần gì.

### 3.6 Kiểm "ảnh thuộc job lệch" (cảnh báo, không chặn)
- Số ảnh của job trong file khác `n` (frame bị xoá trong CVAT, id không liên tục) → ghi file job, kèm cảnh báo "x/n ảnh, thiếu frame …" trong `.txt` và báo cáo.
- Có `push.json` khớp và `runs/<run>/push/manual_list.txt` (đọc bằng `steps.read_manual_list`; nếu import `steps` kéo theo thư viện nặng thì đọc định dạng
  `tên\tloại` trực tiếp, giữ tương thích định dạng cũ một-tên-mỗi-dòng): ảnh trong job `gan_tay` phải đúng các ảnh Gán tay, ảnh trong job `nhan` không được là ảnh Gán
  tay. Lệch → cảnh báo "ảnh lệch job" (số lượng + vài tên ví dụ) trong `.txt` và báo cáo; file vẫn ghi. Không có các file này thì bỏ qua kiểm, ghi "không kiểm được".

### 3.7 Tuỳ chọn tham khảo (KHÔNG làm mặc định)
cvat-sdk 2.77.0 có `Job.export_dataset(...)` để xuất thẳng từng job. **Không** dùng trong bản này; trong báo cáo nêu vì sao chọn tách offline: không tốn thêm lượt xuất
(mỗi lần xuất là một việc nền trên server, chậm với task lớn), chắc chắn khớp từng ảnh với file cả task (cùng một lần xuất), không thêm lời gọi SDK mới (nên
`test_signatures_match_real_sdk` không đổi), thử được hoàn toàn bằng CVAT giả. Không bắt buộc mở rộng CVAT giả; nếu bạn thêm `Job.export_dataset` vào gói giả thì
đồng thời thêm vào bảng chữ ký của `test_signatures_match_real_sdk`, và vẫn không gọi nó từ `tool/`.

## 4. Test (pytest; chỉ dữ liệu giả trong `tmp_path`; giữ xanh toàn bộ)

Đặt test mới trong file mới (mặc định `tests/test_tach_job.py`), tái dùng fixture/hàm của `tests/test_push.py` (`cvat`, `make_run`, `do_push`, `collect_args`) bằng
import như `test_gan_tay.py` đang làm. Tối thiểu:
- **Ranh giới job đúng**: push `n_nhan=19, n_tay=3, job_size=8` qua CVAT giả → 4 job [8, 8, 3, 3]; `collect` mặc định ghi 4 file job, id ảnh trong mỗi file đúng khoảng
  frame của job, tổng ảnh các file job = số ảnh file cả task, mỗi `<image>` giống hệt bản trong file cả task (so `ET.tostring`).
- **Job Gán tay riêng**: file job cuối có `loai gan_tay`, chứa đúng `G_001..G_003` (cả ảnh có nháp lẫn ảnh trống), job `nhan` không có ảnh `G_…`; báo cáo có bảng theo
  job với số ảnh có nhãn đúng (ảnh trống không có skeleton).
- **Không ghi đè**: file job có sẵn (thêm dấu vết) giữ nguyên sau lần `collect`/`tach_job` thứ hai; file job còn thiếu thì được ghi.
- **`.txt` cũ**: dòng job không có `frames`/`loai` → frame tính cộng dồn, loại `khong_ro`, vẫn tách đúng; **biểu thức cũ chép nguyên văn** đọc dòng mới ra đúng
  `state` (không dính dấu `|`).
- **XML id không liên tục** (thiếu một frame giữa job) → tách đúng, cảnh báo "x/n ảnh".
- **Ảnh thuộc job lệch** (tráo một ảnh Gán tay vào khoảng của job Nhận, hoặc `manual_list.txt` không khớp) → cảnh báo trong `.txt` và báo cáo, file vẫn ghi.
- **Id ngoài mọi job** → lỗi rõ (nêu tên ảnh, id, các khoảng), **không** ghi file job nào; trong `collect` file cả task còn nguyên và báo cáo vẫn được lập.
- **`--job`**: chỉ ghi file của job đó (file cả task vẫn ghi); id không tồn tại → `SystemExit` liệt kê id hợp lệ, **không** có lời gọi `Task.export_dataset` mới và
  `raw/` không có file mới; `--job` + `--no-per-job` → lỗi tham số.
- **`--no-per-job`**: `raw/` chỉ có đúng hai file như trước; số lời gọi CVAT bằng luồng cũ. **Tách job không thêm lời gọi CVAT** (so log gói giả có/không tách).
- **`--skip-export`** trên task `demo-…` đã có file trong `raw/` → tách từ file mới nhất của mỗi người, không gọi CVAT; task `m28-…` mặc định không tách, `--per-job`
  thì tách nếu có `.txt`, thiếu `.txt` thì báo rõ, không sập.
- **`--dry-run`**: in frame/loại/tên file job dự kiến, không tạo `raw/`, `outputs/`.
- **`latest_raw_files`/`RAW_RE`** bỏ qua file `_job<id>` (id 1, 3, 4, 5 chữ số); `push_info` trả đúng như cũ.
- **`loai` theo `push.json`**: trùng `task_id` thì lấy kind; `task_id` khác (task tạo lại) hoặc thiếu `push.json` → `khong_ro`.
- **`<meta>`** (XML viết tay có `<meta><task><size>`, `<segments>`, `<owner><email>`): file job có `size` = số ảnh của job, phần còn lại của meta giữ nguyên; stdout,
  `.txt`, báo cáo **không** chứa chuỗi email giả.
- **CLI `tool/tach_job.py`**: `main([...])` với `--xml`, `--txt` tường minh, `--out` thư mục khác, `--job`; mã thoát 0/2; thiếu `.txt` → 2 kèm thông báo rõ;
  `--help` chạy được.
- **eval50/QC với file job**: `eval50.read_labels` + `evaluate` trên file job (ít ảnh hơn) chạy được, chỉ chấm các mặt của job; `collect.analyze` trên file job đúng số;
  `_qc_line` chỉ nhận file cả task.
- **`m28.py`**: `test_collect_needs_task_and_passes_args` mở rộng (hoặc test mới) cho `--per-job`, `--no-per-job`, `--job 101 --job 102`; cờ mới dùng với lệnh khác → lỗi.
- **`cvat_smoke`**: bước 9 vẫn ĐẠT với CVAT giả khi tách job bật; nếu thêm kiểm con tách job thì có test cho trường hợp tách sai → HỎNG.
- `test_no_torch.py`, `test_chay_bat.py`, `test_chay_sh.py` vẫn xanh. Toàn bộ `python -m pytest tests -q` xanh.

## 5. Tài liệu (lệnh cmd ở bản Windows, bash ở bản Ubuntu)
- `README.md`: một dòng trong bảng lệnh/đầu ra cho file job và `tool/tach_job.py`.
- `HUONG-DAN-WINDOWS.md` mục 7 (gạch đầu dòng `collect`): file job `raw\<task>_<người>_<DDMM>_job<id>.xml` (+ `.txt`), mặc định bật cho `demo-…`, `--no-per-job`,
  `--job <id>`, lệnh `python tool\tach_job.py --xml raw\demo-F5_P2_1810.xml` để tách file đã xuất từ trước, "chỉ để đọc/đo, không nhập lại vào CVAT", "không đưa vào
  git". `HUONG-DAN-UBUNTU.md`: cùng nội dung bằng lệnh bash (`python tool/tach_job.py --xml raw/demo-F5_P2_1810.xml`).
- `TAI-LIEU-CHI-TIET.md` mục "push và collect (CVAT)": quy tắc tách, định dạng `.txt` (dòng job mới, tương thích ngược), nguồn `loai`, kiểm lệch, vì sao không dùng
  `Job.export_dataset`, rủi ro chưa thử trên CVAT thật; bảng hợp đồng (`collect(args)` có thêm `per_job`, `job`); mô tả bước 9 của kiểm tra nhanh nếu bạn đổi `s9`.
- Docstring đầu `collect.py`, `m28.py`, module mới, `tool/tach_job.py`.

## 6. Tự kiểm (bắt buộc)
1. `python -m pytest tests -q` trước và sau; ghi số thật.
2. **Chạy tay trên CVAT giả, ngoài repo** (thư mục tạm ở mục 0A, `cwd` = thư mục chạy thử có `config/` chép từ `M`): dựng một lượt giả như `make_run` (19 Nhận, 3 Gán
   tay), đẩy bằng `push.push` với `M28_FAKE_CVAT_STATE`, rồi chạy **đúng lệnh người dùng sẽ gõ** qua tiến trình con với `PYTHONPATH=<M>/tests/fake_cvat`:
   `python <M>/tool/m28.py collect --task demo-Thu --reviewer P4`, `… --no-per-job`, `… --job <id job Gán tay>`, `… --dry-run`,
   `python <M>/tool/tach_job.py --xml raw/<file>.xml --out <thư mục khác>`, `python <M>/tool/eval50.py --gt raw/<file job>.xml --pred runs/<lượt>/xml/prelabel.xml
   --out <tạm>/nme.csv`. Ghi vào báo cáo: danh sách file trong `raw/`, trích `.txt` cả task và một `.txt` job, đoạn "Theo job" của báo cáo collect, kết quả eval50.
3. `python tool/cvat_smoke.py --dry-run` (và chạy đủ với CVAT giả nếu làm được) để chắc bước 9 không hỏng.
4. Sau cùng `git status`: chỉ có file code/test/tài liệu; **không** `raw/`, `runs/`, `outputs/`, ảnh, zip, file tạm trong repo.

## 7. Tự soát trước khi báo cáo
Đọc lại toàn bộ `git diff`, ghi Đạt/Chưa/Lý do cho từng mục: (1) tách offline, không lời gọi CVAT mới; (2) tên file `…_job<id>`, không ghi đè, `RAW_RE` bỏ qua;
(3) `.txt` mới đọc được bằng biểu thức cũ, `.txt` cũ đọc được bằng code mới; (4) `--per-job`/`--no-per-job`/`--job`, mặc định đúng; (5) id ngoài mọi job lỗi rõ, không
ghi nửa vời; (6) báo cáo theo job, QC không đếm hai lần; (7) luồng cả task không đổi (test cũ không sửa); (8) `push_info` không đổi; `review_app.py`, `chay.*`,
`de-tai-m28/`, `CLAUDE.md`, `so-quyet-dinh.md` không đổi; (9) `cvat_smoke` bước 9; (10) tài liệu ba file + chi tiết; (11) không token/email/đường dẫn máy; không commit.

## 8. Báo cáo cuối (tiếng Việt, trung thực, ngắn mà đủ)
1. Tóm tắt; `git status`, `git diff --stat` (không commit).
2. **File đã đổi/thêm** theo nhóm (tool, tests, tài liệu) và mỗi file một dòng đổi gì.
3. **Mẫu tên file xuất**: file cả task, file job, `.txt` của từng loại (kèm một dòng job mẫu), đầu ra của `tach_job.py`.
4. **Mặc định bạn đã chọn** và lý do (tên module, tự động bật cho `demo-…`/tắt cho `m28-…`, `--job` vẫn ghi file cả task, `--job` sai dừng trước khi xuất, xử lý lỗi tách
   trong `collect`, chỉ sửa `size` trong `<meta>`, nguồn `loai`, định nghĩa "lệch", mã thoát CLI, thay đổi `cvat_smoke`), và mọi điểm bạn đã đổi so với mục 3.
5. pytest: số gốc → số sau (qua/bỏ qua), danh sách test mới; kết quả chạy tay ở mục 6 (ghi rõ là **CVAT giả, dữ liệu giả**).
6. Vì sao tách offline thay cho `Job.export_dataset` (mục 3.7).
7. **Chưa thử**: CVAT thật 2.77.0 (id ảnh = số frame và khoảng job của task `job_file_mapping` trên server thật; `<meta>` thật; frame bị xoá; task nhiều job), Windows/cmd,
   Python 3.14, file `final/`. Nêu cách kiểm sớm nhất: mỗi người chạy `cvat_smoke.py` trên máy có CVAT; P4 chạy `collect --task demo-R1610` buổi 18/10.
8. **Việc cần P4 đồng ý**, đối chiếu `de-tai-m28/p4-cvat.md` và nêu khác biệt: kế hoạch có `tool/export.py` riêng (`export.py <task> <Pk> <ngày>`, `--final`, `--check`,
   in lệnh git) cho task thí nghiệm, còn repo hiện **chưa có** `export.py` và `collect` mới là chỗ xuất (chỉ task `demo-…`); kế hoạch nói "`raw/` giữ file xuất gốc" còn
   file job là file **dẫn xuất** đặt cạnh trong `raw/` (đề xuất phương án khác nếu P4 không đồng ý: thư mục con `raw/job/` hoặc `outputs/`); task thí nghiệm `m28-…` có
   một job nên không tách mặc định; các lệnh đếm file theo glob của kế hoạch; kế hoạch bảo commit `raw/` còn `CLAUDE.md` cấm (giữ theo `CLAUDE.md`, đề xuất cập nhật
   bản Claude Docs); `.txt` thêm trường `frames`/`loai` (định dạng P4 nên chốt để `export.py` sau này ghi giống).
9. Đề xuất (không tự làm): có nên bỏ email trong `<owner>`/`<assignee>` của `<meta>` khi tách (chủ repo quyết); có cần QĐ mới trong `so-quyet-dinh.md` cho quy ước file job.
10. Lệnh người dùng chạy tiếp, cả **cmd** và **bash**: chạy test, `collect` có/không tách job, `tach_job.py` trên một file cũ.


---

# PHẦN 2 — Đồng hồ và Thống kê

> **Cách dùng (máy Ubuntu của chủ repo):** ở thư mục repo (ví dụ `~/m28`) chạy `git checkout main && git pull`, mở Claude Code trong thư mục đó rồi gõ:
> `Đọc source-tool/m28-prelabel/prompts/prompt_dong_ho_thongke_local.md và thực hiện đúng và đầy đủ.`

# Prompt chạy LOCAL (Ubuntu): M28, tab "Đồng hồ" bấm giờ gán nhãn và thu gọn tab "Thống kê"

Bạn là kỹ sư triển khai trong repo đề tài M28 (đội T015-SIXSEVEN), chạy **trên máy Ubuntu của chủ repo** (không phải cloud). Làm **toàn bộ** việc dưới đây
trong phiên này, tự kiểm, rồi viết báo cáo cuối trung thực. Code, tài liệu, báo cáo viết bằng **tiếng Việt**. Chủ repo đã chốt các ý lớn (mục 2) và
người viết prompt đã chọn sẵn mặc định cho các chỗ còn mở (đánh dấu "mặc định"). **Chi tiết nhỏ còn lại bạn tự quyết**: chọn cách đơn giản, an toàn, khớp code
hiện có, ghi mọi mặc định vào báo cáo (mục 10). Chỉ dừng hỏi khi một việc trái mục 0A hoặc trái `CLAUDE.md`.

## 0A. Môi trường local và luật làm việc (ưu tiên hơn mọi chỗ khác trong file này)

- **Đường dẫn.** Repo là thư mục hiện tại; `M` = `source-tool/m28-prelabel`. Mọi lệnh của tool chạy với **cwd = `M`** (`runs/`, `raw/`, `final/`, `outputs/`,
  `data/`, `config/` tính từ `M`). Thư mục tạm của phiên: `/tmp/m28_dong_ho/` (`mkdir -p`, NGOÀI repo) cho bản chép prompt, script tạm, dữ liệu giả, thư mục chạy
  thử `work/`, bản xuất `out/`, ảnh chụp `shots/`, log, băm. Không bao giờ ghi đường dẫn tuyệt đối của máy (`/home/...`, `/tmp/...`) vào code hay tài liệu của repo.
- **Máy.** Ubuntu, **bash** (lệnh trong tài liệu Ubuntu viết cho bash, đường dẫn `/`), CPU, không GPU. Python của `.venv` do `chay.sh` tạo: `source .venv/bin/activate`
  trong `M` (bản 3.10–3.14 tuỳ máy: code phải chạy được từ **Python 3.10**, không dùng cú pháp chỉ có từ 3.12). CVAT local có thể đang chạy ở
  `http://127.0.0.1:8080` nhưng phiên này **không gọi CVAT, không đọc hay hỏi token**: đồng hồ và thống kê chỉ đọc/ghi file cục bộ.
- **Không cài gói mới** (không `pip install` gói lạ, không `apt install`, không `playwright install`, không matplotlib/scipy/pandas trong `tool/`). Riêng `pytest` nếu
  thiếu thì cài như `chay.sh` mục 5 (`python -m pip install pytest`) và ghi vào báo cáo. Trong `tool/`: thư viện chuẩn + numpy (nạp lười trong module có giao diện),
  như code hiện có; không JS/CSS/font từ CDN.
- **pytest gốc.** Sau khi chọn nhánh (mục 0B), trước khi sửa: trong `M` chạy `python -m pytest tests -q`, ghi số thật (qua / bỏ qua / lỗi có sẵn). Làm xong: số qua
  **không ít hơn** số gốc; không xoá, không nới lỏng test cũ (test hiển thị của thẻ bị bỏ ở mục 4.1 thì **đổi** thành test kiểm thẻ đó không còn, không xoá).
- **Quyền riêng tư (giữ nguyên `CLAUDE.md`).** Ảnh, ảnh cắt, ảnh chồng, `runs/`, `data/`, `raw/`, `final/`, `outputs/`, `backups/`, file xuất CVAT, `timing_*.csv`, zip, ảnh chụp
  màn hình: **không bao giờ vào git** (`.gitignore` đã chặn; `git status` trước mỗi commit). Không ghi token/mật khẩu/email vào code, log, CSV, HTML, báo cáo. Trang chỉ
  `127.0.0.1`, `share=False`, không tunnel. Ảnh người lái xe (YawDD, DrivFace) chỉ dùng nội bộ; được xem ảnh bằng công cụ Read của chính phiên này; không xử lý ảnh
  khách hàng hay ảnh người thật ngoài hai bộ đó. Hai tab của prompt này **không hiện ảnh mặt nào**.
- **Dữ liệu thật trên máy: CHỈ ĐỌC.** `M/runs/`, `M/raw/`, `M/final/`, `M/data/` và mọi file đang có trong `M/outputs/` (kể cả `outputs/timing/` nếu đã có, và các
  `timing_P*.csv` của facetimer nếu có): không sửa, không tạo, không xoá file nào trong đó khi tự kiểm (kiểm bằng băm trước/sau, mục 6). **Không bấm thử đồng hồ trên
  thư mục thật**: mọi lần thử đồng hồ chạy với cwd = `/tmp/m28_dong_ho/work`.
- **Không sửa** `de-tai-m28/` (bản chụp) và `CLAUDE.md` (đề xuất sửa trong báo cáo). `so-quyet-dinh.md`: chỉ thêm QĐ mới và đổi *trạng thái* QĐ bị thay (mục 7), giữ
  nguyên mẫu cuối file (`tests/test_ca_kho.py` đọc mẫu đó). Không đổi tên điểm, tên file hay ngày giao nhận của kế hoạch.
- **Xem ảnh** (ảnh chụp tab, ảnh HTML xuất) bằng Read và ghi điều thấy được. **Báo cáo trung thực**: chưa chạy thì nói chưa chạy; số từ dữ liệu giả thì gọi là dữ liệu giả.

## 0B. Chọn nhánh gốc (làm trước mọi sửa đổi)

1. `git status` phải sạch (không sạch: DỪNG và báo, không stash, không xoá). Chép prompt ra ngoài, vì đổi nhánh có thể làm file này biến khỏi cây làm việc:
   ```bash
   mkdir -p /tmp/m28_dong_ho && cp source-tool/m28-prelabel/prompts/prompt_dong_ho_thongke_local.md /tmp/m28_dong_ho/prompt.md
   git checkout main && git pull
   git branch --list 'loc-thongke*' 'dong-ho-thongke*'
   for b in $(git branch --list 'loc-thongke*' --format='%(refname:short)'); do
     echo "== $b"; git log --oneline main.."$b" | head -20
     git merge-base --is-ancestor "$b" main && echo "   (đã nằm trong main)"
   done
   git ls-tree -r --name-only main -- source-tool/m28-prelabel/tool | grep -E 'thong_ke|loc_|bang_mat' || echo "main chưa có tab Thống kê"
   ```
2. Bốn trường hợp (prompt `prompts/prompt_loc_thongke_local.md`, nhánh `loc-thongke`, có thể đã chạy, đang chạy hoặc chưa chạy):
   - **TH1** – main đã có tab Thống kê (nhánh lọc đã gộp): `git checkout -b dong-ho-thongke main`.
   - **TH2** – có `loc-thongke` (hoặc `loc-thongke-2`…) **chưa gộp** và có commit tab Thống kê: chọn nhánh mới nhất có tab Thống kê, `git checkout -b dong-ho-thongke <nhánh đó>`;
     nếu main có commit chưa nằm trong nhánh (`git merge-base --is-ancestor main HEAD` sai) thì `git merge --no-ff main -m "Gộp main mới nhất vào dong-ho-thongke"`;
     xung đột thì `git merge --abort`, ghi vào báo cáo và làm tiếp không gộp. **Ghi rõ trong báo cáo**: nhánh gốc, commit gốc, có gộp main không.
   - **TH3** – không có nhánh lọc nào (hoặc có mà chưa có commit nào): `git checkout -b dong-ho-thongke main`. Tab Thống kê làm **mới** theo mục 4 (chỉ bản thu gọn);
     **không** làm tab Lọc dữ liệu (ngoài phạm vi prompt này); thêm ghi chú đầu `prompts/prompt_loc_thongke_local.md` (mục 7).
   - **TH4** – nhánh lọc đang dở (có thay đổi chưa commit, `.git/index.lock`, worktree khác đang mở nhánh đó): **DỪNG**, báo người dùng, không đụng.
   - `dong-ho-thongke` đã có: không xoá, không ghi đè; tạo `dong-ho-thongke-2` và ghi vào báo cáo.
3. Commit **nhỏ** theo mục 8, thông điệp tiếng Việt. **KHÔNG push, không tạo PR, không merge vào main.** Người dùng tự đọc rồi quyết.

## 1. Đọc trước khi sửa (đọc hết, trên nhánh vừa chọn)

- `CLAUDE.md`; `so-quyet-dinh.md` (mọi QĐ, mẫu cuối file).
- Trong `M`: `README.md`, `HUONG-DAN-UBUNTU.md`, `HUONG-DAN-WINDOWS.md`, `TAI-LIEU-CHI-TIET.md` (Trang rà soát, Ca khó, push và collect, Chạy test), `chay.sh`, `chay.bat`,
  `tests/test_chay_sh.py`, `tests/test_chay_bat.py`, `prompts/prompt_loc_thongke_local.md` (đặc tả cũ của bộ lọc và Thống kê 4 nhóm; phần Thống kê bị thay bởi mục 4 dưới đây).
- **Bấm giờ của P5:** `snippets/p5/01_python.py` (facetimer: `timing_<người>.csv`, 12 cột `date, person, condition, task, job, block, seq, face_id, seconds, warmup,
  interrupted, note`; `face_id = f"{block}_{seq:02d}"`; `seconds` làm tròn 0,1, đã trừ tạm dừng; `warmup = int(seq <= 2 or first)`; `interrupted = 1` khi có `p`;
  `q` thoát không ghi mặt đang làm; mỗi Enter ghi ngay một dòng; UTF-8 không BOM, dòng CRLF của `csv.writer`), `snippets/p5/02_python.py` (phân tích thời gian),
  `snippets/p5/03_python.py` (chất lượng), và `../../de-tai-m28/p5-thi-nghiem.md` (chỉ đọc): mục "facetimer.py", "Thời gian" (r_i, trung bình nhân, Đạt khi TB nhân ≤ 0,80
  và ≥ 4/5 người có r_i < 1; đề xuất Không đạt khi cận dưới KTC 90% > 0,80; bootstrap bốc lại mặt trong khối 2.000 lần, seed 28, chung cho hai cách), "Lỗi hay gặp"
  (luôn lọc `warmup = 0`, chỉ số chính là trung bình nhân, phải dùng file raw 14–15/10), lịch 14–15/10 (Pk gán tay khối Xk, sửa nháp X(k+1), P5 sửa nháp X1; khối 10 mặt).
- `tool/review_app.py`: docstring đầu file, `build_ui` (thứ tự tab; `tab.select` làm mới lười), `AppCtx` (`project_root`, `closing`, `begin_close`), `Store(clock=...)`,
  `_close_bar` (hộp xác nhận kiểu `m28-modal`, `close_body_html`, `on_confirm`), `PAGE_JS` (+ `dot_ui.JS_BODY` nối vào), `CSS`, `main` (nhánh `KeyboardInterrupt`,
  `allowed`), `_launch` (127.0.0.1, `share=False`, chặn Host lạ). `gr.Timer` đã dùng ở tab Nạp ảnh (Gradio 6.29.1).
- `tool/ca_kho.py`: mẫu tab `member_tab(gr, demo, store, ctx)` trả `(hàm làm mới, inputs, outputs, opts)` với `opts = dict(show_progress="hidden", api_visibility="private",
  concurrency_limit=1, concurrency_id=...)`; `_atomic_write`, `csv_text`, `_formula_safe`, `clean_text`, `serve_dir`, `msg_html`, `CSS` dùng biến theme.
- `tool/dot_anh.py` (`Pending`: yêu cầu xác nhận có mã dùng một lần), `tool/dot_ui.py` (hộp `m28-modal`, `JS_BODY`), `tool/cai_dat.py` (`get().next_reviewer`, kiểu chống
  ghi chồng bằng `rev`: "vừa đổi ở tab khác, đã tải lại"), `tool/nap_anh.py` (`check_reviewer`, `runs_layout`, `_inside`), `tool/m28core/dang_chay.py` (`pid_alive`).
- `tool/eval50.py` (`read_labels` bảy skeleton, `read_run_pred`, `iod`, `point_errors`, `p2p_errors`, `face_scores`, `BAD = 10`), `tool/m28core/collect.py` (`RAW_RE`,
  `latest_raw_files`, `push_info`), `tool/m28core/push.py` (`push.json`, `gan_tay_co_nhap`), `tool/m28core/mau_nhom.py` (`GROUP_COLOR`, `GROUP_VI`), `config/m28_config.json`
  (50 điểm, 7 nhóm `longmaytrai` 5, `longmayphai` 5, `songmui` 4, `mattrai` 8, `matphai` 8, `moingoai` 12, `moitrong` 8; `iod_points`; **thứ tự điểm luôn theo config**).
- Nếu có: `tool/tach_job.py` và chỗ `collect` gọi nó (file nhãn theo job `raw/*_job<id>.xml`, do một thay đổi khác trên cloud); TH1/TH2: các module của tab Thống kê và
  Lọc dữ liệu đã có (thường `tool/m28core/bang_mat.py`, `tool/thong_ke.py`, `tool/thong_ke_ui.py`, `tool/loc_ui.py`, `tool/loc_du_lieu.py`) và test của chúng.
- `tests/`: `conftest.py`, `test_review_app.py`, `test_cai_dat.py` (năm tab đầu phải là Rà soát, Nạp ảnh, Các đợt, Ca khó, Họp team; tab cuối là Cài đặt), `test_cvat_smoke.py`
  (dựng `build_ui(None, ctx)`), `test_ca_kho.py`, `test_eval50.py`, `test_no_torch.py`, `e2e_review_ui.py` (Playwright tuỳ chọn, `lsof`).

## 2. Bối cảnh và yêu cầu (chủ repo đã chốt)

Chủ repo đã xem trang Thống kê và muốn **thu gọn** nó, đồng thời có **đồng hồ bấm giờ ngay trên trang** thay cho facetimer dòng lệnh. Hai việc:

- **A. Tab "Đồng hồ"** bấm giờ gán nhãn: Bắt đầu, Tạm dừng/Tiếp tục, Hủy (có xác nhận, chủ repo thích xác nhận), Xong (lưu; không bấm Xong thì không có số liệu).
  mm:ss chạy mượt trên trang, nhưng **nguồn sự thật là đồng hồ phía server** (`time.monotonic`, cộng dồn các đoạn không tạm dừng), trạng thái lưu ra file ngoài git
  để tải lại trang/đóng trình duyệt không mất; mỗi người một đồng hồ đang chạy; có khoá chống hai tab ghi chồng. Ghi vào `outputs/timing/timing_<người>.csv` **đúng
  định dạng facetimer của P5**, cột mới chỉ nối ở cuối. Hủy thì không ghi dòng nào.
- **B. Tab "Thống kê" chỉ còn ba chỉ số:** (1) NME nháp so với nhãn đã sửa; (2) tỉ lệ điểm phải sửa (point correction rate) ở task assisted; (3) so sánh thời gian gán tay
  (manual) với dùng tool (assisted) từ các file bấm giờ. Bỏ mọi thứ khác khỏi tab và bản xuất. Tab **"Lọc dữ liệu" giữ nguyên** mọi tiêu chí (kể cả `low_conf`).

**Không bịa số.** Thiếu dữ liệu thì khung trống nói rõ vì sao, cần file nào, ai làm ra file đó; không bao giờ hiện 0 hay số mẫu thay cho "chưa có".

## 3. Việc A: tab "Đồng hồ"

### 3.1 Bấm theo từng mặt (mặc định đã chọn, đọc kỹ)
Chủ repo tả bốn nút và "mỗi lần ghi: số mặt, giây tổng". Nhưng giao thức P5 cần **một dòng mỗi mặt** (`seq`, `face_id`, `warmup` cho seq 1–2 và mặt đầu của mỗi lần chạy,
bootstrap bốc lại **mặt** trong khối, tỉ lệ thử nhanh "tổng giây seq 3–8"); một dòng "N mặt, T giây" không tính được những thứ đó. Vì vậy: **giữ bốn nút của chủ repo
và thêm nút "Xong mặt này → mặt tiếp"** (như phím Enter của facetimer). Một **phiên** = một lần Bắt đầu cho một khối; mỗi "Xong mặt" khép một mặt; **"Xong (lưu)"** khép
mặt đang làm và ghi **mọi mặt của phiên** vào CSV một lần; **"Hủy"** bỏ cả phiên, không ghi dòng nào. "Số mặt" và "giây tổng" của phiên = tổng các dòng mặt (hiện trên tab
và ghi ở cột thêm). Không làm chế độ "cả khối một dòng". Ghi khác biệt này vào báo cáo, mục việc cần chủ repo và P5 đồng ý.

### 3.2 Ô nhập, nút và luồng
- **Ô nhập** (khoá khi đang có phiên):
  - *Người*: chỉ `P1`–`P5` (Dropdown). Mặc định: người rà của trang nếu là P1–P5, không thì tên mặc định ở tab Cài đặt (`cai_dat.get().next_reviewer(...)`), không có thì
    trống và bắt chọn. Tên file `timing_<người>.csv` phải khớp `timing_P*.csv` của P5.
  - *Điều kiện*: `manual` (gán tay) / `assisted` (sửa nháp).
  - *Task*: tự điền `m28-manual` / `m28-assisted` theo điều kiện, sửa được (`[A-Za-z0-9_.-]{1,64}`). `m28-manual` đi với assisted (hoặc ngược lại) → từ chối, giải thích.
  - *Job*: số job CVAT, tuỳ chọn (`\d{1,9}` hoặc trống; facetimer bắt buộc nhưng phân tích P5 không dùng).
  - *Khối*: tự gợi ý theo thiết kế (Pk manual → Xk; Pk assisted → X(k+1); P5 assisted → X1), sửa được (`[A-Za-z0-9_-]{1,20}`); với task thí nghiệm mà khác thiết kế →
    cảnh báo vàng (không chặn) và ghi `canh_bao=lech_thiet_ke`.
  - *Số mặt n* (mặc định 10, "khối luôn 10 mặt"; 1–200) và *seq bắt đầu* (mặc định = seq lớn nhất đã ghi cho cùng người/task/khối + 1, chưa có thì 1; đúng "buổi bù:
    nhập seq tiếp theo, mặt đầu tự thành khởi động").
  - *Ghi chú phiên* (tuỳ chọn) và *Ghi chú mặt này* (gửi kèm khi khép mặt, rồi tự xoá ô).
- **Nút** (server luôn kiểm lại trạng thái, kể cả khi nút trên trang đang khoá):
  - **Bắt đầu**: kiểm ô; người này đã có phiên (chạy hoặc tạm dừng) → từ chối, chỉ ra phiên đó. Các seq sắp bấm đã có dòng cho cùng người/task/khối → cảnh báo "sẽ tạo dòng
    trùng", chỉ bắt đầu khi bấm lần hai. Tạo file trạng thái; mặt đầu `<khối>_<seq:02d>`; đồng hồ chạy.
  - **Xong mặt này → mặt tiếp** (nút to nhất khi đang chạy): khép mặt hiện tại (giây không tính tạm dừng, số lần tạm dừng, giờ bắt đầu/kết thúc, ghi chú mặt), lưu vào file
    trạng thái (chưa vào CSV), mở mặt kế. Đủ n mặt thì đồng hồ dừng và nhắc "Đủ n mặt: bấm Xong (lưu)". Mặt < 2 giây → từ chối "bấm quá nhanh" (chống bấm đúp), không lặng lẽ
    bỏ. Khoá khi đang tạm dừng (bấm Tiếp tục trước).
  - **Tạm dừng / Tiếp tục** (một nút đổi chữ): thời gian tạm dừng không tính; mặt có ≥ 1 lần tạm dừng → `interrupted = 1` như facetimer.
  - **Hoàn tác mặt vừa xong** (chỉ trong phiên, trước khi lưu): gộp mặt vừa khép trở lại thành mặt đang làm (giây và số lần tạm dừng cộng dồn, seq lùi một), chống bấm nhầm.
  - **Xong (lưu)**: ô tích "Tính mặt đang làm là đã xong" (mặc định bật; tắt = phím `q` của facetimer, bỏ mặt đang làm); mặt đang làm < 2 giây thì không tính và nói rõ.
    Ghi mọi mặt của phiên vào CSV (3.4) **một lần, nguyên tử**; ghi xong mới xoá file trạng thái; lỗi ghi → giữ nguyên trạng thái, báo lỗi, bấm lại được. Còn cảnh báo
    chưa xử lý (3.5) → đòi bấm lần hai. Phiên không có mặt nào → không ghi, báo "phiên rỗng", gợi ý Hủy. Ghi xong hiện tóm tắt (số mặt, số mặt tính giờ, tổng, phút/mặt,
    đường dẫn tương đối) và điền sẵn seq cho phiên sau.
  - **Hủy phiên…**: mở hộp xác nhận kiểu `m28-modal` (như "Đóng trang rà soát") với tóm tắt "Bỏ phiên P5 · m28-manual · X5: 3 mặt đã khép, 12:34. KHÔNG ghi dòng nào vào
    timing_P5.csv", ô gõ `HUY` (không phân biệt hoa thường; nhận cả `HỦY`, `HUỶ`), nút "Hủy phiên (không lưu)" và "Quay lại". Server kiểm mã yêu cầu dùng một lần (kiểu
    `dot_anh.Pending`, mở yêu cầu mới thì yêu cầu cũ hết hiệu lực) và chữ gõ; sai thì không hủy. Hủy: **không ghi dòng nào vào `timing_<người>.csv`**; nối một dòng vào nhật ký
    riêng `outputs/timing/huy_<người>.csv` (thời điểm, người, điều kiện, task, job, khối, `phien`, số mặt bỏ, giây bỏ, lý do tuỳ chọn) để biết đã hủy; file này không vào thống kê.
- **Hiển thị**: đồng hồ lớn mm:ss của mặt đang làm (≥ 60 phút thì h:mm:ss), dòng nhỏ tổng phiên và "Mặt X5_03 · 3/10", trạng thái bằng chữ + ký hiệu (▶ Đang chạy,
  ⏸ Tạm dừng, ■ Đủ mặt, chờ lưu), bảng nhỏ các mặt đã khép trong phiên (seq, giây, số lần tạm dừng, ghi chú), và bảng "Đã lưu gần đây" của người đang chọn (5 phiên cuối
  đọc từ CSV: ngày, task, khối, số mặt, giây tổng, giây/mặt không tính khởi động).

### 3.3 Nguồn sự thật, file trạng thái, khoá
- Đồng hồ thật ở server: `time.monotonic()`; tiêm được `clock=` và `wall=` (như `Store(clock=...)`) để test. Trạng thái gồm các đoạn chạy `[mono_bắt_đầu, mono_kết_thúc|null]`
  của mặt đang làm, các mặt đã khép, số lần tạm dừng; giờ thật ISO có múi giờ (`datetime.now().astimezone()`, giây) chỉ dùng cho `bat_dau`/`ket_thuc`/`date`.
- File `outputs/timing/dang_chay_<người>.json` dưới `ctx.project_root` (tạo thư mục nếu chưa có; `outputs/` đã bị `.gitignore` chặn), ghi **nguyên tử** (tạm + fsync +
  `os.replace`, như `ca_kho._atomic_write`) sau **mọi** thao tác. Gồm: `phien_ban`, `rev` (tăng mỗi thao tác người dùng), `pid`, `lan_cuoi_thay` (giờ thật; cập nhật ở nhịp
  đồng bộ tối đa 60 giây một lần và **không tăng `rev`**), `moc_mono` = `time.time() − time.monotonic()` lúc ghi (phát hiện máy khởi động lại), thông tin phiên, mặt, đoạn chạy.
- Đóng tab hay đóng trình duyệt: server giữ trạng thái, đồng hồ vẫn chạy; mở lại tab thì đọc file và hiện đúng. Tắt trang rồi mở lại trong cùng lần khởi động máy: monotonic vẫn
  liên tục. Máy khởi động lại (`moc_mono` lệch > 5 giây): monotonic cũ vô nghĩa → đoạn đang chạy tính lại bằng giờ thật, ghi `canh_bao=khoi_dong_lai` và hiện cảnh báo (3.5).
- **Mỗi người một phiên**: có file trạng thái = đang có phiên; Bắt đầu bị từ chối.
- **Chống hai tab ghi chồng**: mỗi thao tác gửi kèm `rev` mà tab đã thấy (giữ trong `gr.State`); khác `rev` hiện tại → từ chối, tải lại, báo "Đồng hồ vừa đổi ở tab khác, đã tải
  lại: kiểm lại rồi bấm lại" (cùng kiểu `cai_dat`). Trong tiến trình: một `threading.Lock` mỗi người + `concurrency_id="dongho"`. Giữa hai tiến trình (hai trang ở hai cổng):
  file khoá `outputs/timing/.khoa_<người>` tạo bằng `os.open(..., O_CREAT | O_EXCL)` (pid + giờ), chỉ giữ trong lúc đọc-sửa-ghi; khoá của pid đã chết
  (`dang_chay.pid_alive`) hoặc cũ hơn 30 giây là khoá mồ côi.
- File trạng thái hỏng (JSON sai, thiếu khoá, đoạn chạy ngược): không sập; hiện lỗi rõ và nút "Bỏ trạng thái hỏng" đổi tên file thành
  `dang_chay_<người>.hong-<YYYYMMDD-HHMMSS>.json` (không xoá).

### 3.4 File CSV `outputs/timing/timing_<người>.csv`
- **12 cột đầu đúng tên, thứ tự và nghĩa của facetimer**: `date` (ngày máy, ISO, lúc khép mặt), `person`, `condition`, `task`, `job`, `block`, `seq`, `face_id`
  (`<block>_<seq:02d>`), `seconds` (không tính tạm dừng, làm tròn 0,1, > 0), `warmup` (đúng `int(seq <= 2 or first)`, `first` = mặt đầu của phiên), `interrupted`, `note`.
- **Cột thêm ở cuối** (mặc định; đổi tên thì nêu lý do): `phien, bat_dau, ket_thuc, so_lan_tam_dung, giay_tam_dung, so_mat_phien, giay_phien, ghi_chu_phien, sua_tay,
  canh_bao, nguon_ghi` (`nguon_ghi = dong_ho`; `sua_tay` 0/1; `canh_bao` là các mã ngăn bởi `;`: `qua_dem`, `mat_lau`, `khoi_dong_lai`, `tat_trang`, `lech_thiet_ke`, `trung_seq`).
- UTF-8 **không BOM**, dòng CRLF (như facetimer) để `pd.concat` của P5 ghép được với file facetimer. Ô chữ (`task`, `job`, `block`, `note`, `ghi_chu_phien`) qua
  `ca_kho.clean_text` (≤ 200 ký tự) và `ca_kho._formula_safe`; ô số ghi số.
- **Ghi nguyên tử**: dưới khoá, đọc cả file, nối dòng mới, ghi file tạm cùng thư mục, fsync, `os.replace`. File đã có: header đủ cột → nối; header đúng 12 cột facetimer
  (người dùng chép file facetimer vào đây) → giữ bản sao `timing_<người>.csv.bak-<YYYYMMDD-HHMMSS>` rồi viết lại với header đầy đủ, dòng cũ để trống cột thêm; header khác →
  từ chối, không đụng file, giữ trạng thái, báo đúng cột lạ/thiếu. `os.replace` lỗi (file đang mở trong LibreOffice/Excel trên Windows, hết chỗ, không quyền) → giữ trạng thái,
  báo lỗi tiếng Việt, bấm Xong lại được.
- **Liệt kê mọi khác biệt so với facetimer** trong README và báo cáo, ít nhất: ghi lúc Xong (lưu) chứ không sau mỗi mặt (file trạng thái bù lại); chỗ đặt file
  (`outputs/timing/` thay cho thư mục đang đứng); các cột thêm; có Hủy, Hoàn tác, chặn mặt < 2 giây, tự tạm dừng khi đóng trang; `q` = bỏ tích "Tính mặt đang làm".
  Không sửa hay xoá facetimer/file facetimer nào của P5.

### 3.5 Ca bất thường (mỗi ca có test)
- **Quên bấm (chạy qua đêm).** Hằng số đặt tên ở đầu module: `MAT_LAU_PHUT = 20` (một mặt chạy quá 20 phút), `PHIEN_LAU_PHUT = 150` (buổi tối đa 120 phút); hoặc mặt đang
  chạy qua nửa đêm. Hiện dải cảnh báo vàng (chữ + ký hiệu) trên tab, kèm ba lựa chọn: **"Sửa thời gian mặt đang làm"** (nhập mm:ss thật, 2 giây ≤ giá trị ≤ thời gian đo được,
  không cho lớn hơn số đo; đặt `sua_tay = 1`, ghi giây đo gốc vào `canh_bao`/`note` để còn truy), **"Hủy phiên…"**, **"Giữ nguyên"** (ghi `canh_bao`). Lưu phiên còn cảnh báo
  chưa chọn → bấm Xong lần hai.
- **Đồng hồ đang chạy khi đóng trang.** (a) Đóng tab/trình duyệt: server chạy tiếp (người dùng có thể vẫn đang gán trong CVAT). (b) Bấm "Đóng trang rà soát" hoặc Ctrl+C:
  **tự tạm dừng** mọi phiên đang chạy trong `outputs/timing/` của dự án (`canh_bao=tat_trang`), in một dòng ra terminal "Đồng hồ của P5 đã tạm dừng lúc …: mở lại tab Đồng hồ
  để Tiếp tục hoặc Xong (lưu)"; hộp xác nhận đóng trang báo trước điều này khi có đồng hồ đang chạy. (c) Tiến trình chết đột ngột/máy tắt: lần mở sau thấy phiên đang chạy với
  `pid` đã chết → hiện "Trang đã tắt từ khoảng <lan_cuoi_thay> đến <lúc mở lại>; đồng hồ vẫn tính khoảng này" với hai nút **"Trừ khoảng tắt trang (coi như tạm dừng)"** và
  **"Giữ"**; máy khởi động lại → như 3.3.
- **Giây âm hoặc 0.** Không bao giờ ghi. Phép tính ra ≤ 0 (trạng thái hỏng, giờ hệ thống lùi khi phải tính bằng giờ thật) → báo lỗi, đề nghị Sửa thời gian hoặc Hủy.
- **Qua ngày giữa phiên:** `date` theo lúc khép từng mặt; `canh_bao=qua_dem`.
- **Đổi ô Người khi đang có phiên:** tab hiện phiên của người được chọn; không ảnh hưởng phiên người khác.
- **`ctx.closing` đã bật:** mọi nút ghi từ chối (trừ bước tự tạm dừng do chính việc đóng trang gọi).

### 3.6 Giao diện
- **mm:ss mượt bằng JS phía trình duyệt, không gọi server mỗi giây.** HTML đồng hồ mang `data-*` (giây đã chạy lúc server dựng, đang chạy hay không, mã lần dựng). Đoạn JS
  (hằng `JS_BODY` của module giao diện, nối vào `PAGE_JS` giống `dot_ui.JS_BODY`; `<script>` trong `gr.HTML` không chạy) dùng `setInterval` ~250 ms: thấy mã lần dựng mới thì lấy
  mốc `performance.now()`, rồi hiển thị `giây_server + (now − mốc)/1000` khi đang chạy (không dùng `Date.now()`, khỏi lệch khi giờ máy đổi).
- **Đồng bộ với server:** `gr.Timer(15)` (`concurrency_id="dongho_tick"`) đọc lại file trạng thái, vẽ lại đồng hồ/cảnh báo/trạng thái nút (thấy thay đổi từ tab khác), cập nhật
  `lan_cuoi_thay`; không đụng ô người dùng đang gõ. Chọn tab → làm mới (`tab.select`).
- Nút bật/tắt đúng trạng thái (chưa có phiên: Bắt đầu; đang chạy: Xong mặt, Tạm dừng, Hoàn tác khi đã có mặt khép, Xong (lưu), Hủy; tạm dừng: Tiếp tục, Xong (lưu), Hủy).
- Theme sáng/tối của Gradio, bề rộng 420 px không tràn ngang; số dùng `font-variant-numeric: tabular-nums`; trạng thái luôn có chữ + ký hiệu; CSS dùng biến theme như `ca_kho.CSS`;
  `elem_id` tiền tố `dh-`. Không ảnh mặt, không gọi mạng, không token.

### 3.7 Module và nối vào trang
- Logic `tool/dong_ho.py` (chỉ thư viện chuẩn, không import gradio); giao diện `tool/dong_ho_ui.py` (không import gradio ở đầu module), hàm `dong_ho_tab(gr, demo, store, ctx)`
  theo mẫu `ca_kho.member_tab`, `opts` như mục 1.
- `review_app.py` chỉ thêm vài dòng: tab **"Đồng hồ"** (id `dongho`, elem_id `tab-dongho`) đặt sau "Họp team" và trước "Thống kê"/"Lọc dữ liệu"/"Cài đặt" (giữ năm tab đầu và
  "Cài đặt" cuối cùng như `tests/test_cai_dat.py` đòi); `tab.select` làm mới; nối CSS và JS; gọi tự tạm dừng ở `_close_bar.on_confirm` (sau khi `begin_close` thành công) và ở
  nhánh `KeyboardInterrupt` của `main`; một dòng cảnh báo trong `close_body_html` khi có đồng hồ đang chạy; cập nhật docstring đầu file. Chạy được ở chế độ `--nap` (store `None`)
  và sau khi chuyển lượt (Blocks dựng lại; trạng thái nằm trong file nên không mất).
- **Không thêm `allowed_paths`** cho tab này (không phát file nào).

## 4. Việc B: thu gọn tab "Thống kê"

### 4.1 Giữ và bỏ
- Tab chỉ còn **ba nhóm**: (1) NME nháp so với nhãn đã sửa; (2) tỉ lệ điểm phải sửa; (3) so sánh thời gian manual với assisted.
- **Bỏ khỏi tab VÀ khỏi bản xuất**: thẻ cờ `low_conf` (% cờ, AUROC, recall/precision, cảnh báo `t_flip`), thẻ số lượng dữ liệu và tiến độ, giây rà/mặt từ triage, khối chất lượng
  nhãn từ `nme_per_face.csv`, bảng M24, giờ tiết kiệm/1.000 mặt, tách nghiêng/che, mọi bảng/biểu đồ khác, và các ô lọc chỉ phục vụ chúng (ví dụ người rà).
- **Giữ**: tab "Lọc dữ liệu" và CLI lọc **nguyên tiêu chí** (kể cả `low_conf` và số điểm bị cờ); phần tính dùng chung (bảng mặt, cờ, `flag_eval`) nếu Lọc dữ liệu hay code khác
  còn gọi. Chỉ xoá code hiển thị/xuất của thẻ bị bỏ; hàm không còn ai gọi (kiểm bằng grep) thì xoá, nhưng test logic còn dùng thì giữ. Test hiển thị của thẻ bị bỏ đổi thành
  test kiểm thẻ đó **không còn** trên tab và trong HTML xuất.
- **TH3** (chưa có tab Thống kê): làm mới chỉ ba nhóm này với lớp đọc tối thiểu, **đặt tên như đặc tả cũ** (`tool/m28core/bang_mat.py`, `tool/thong_ke.py` logic + CLI,
  `tool/thong_ke_ui.py`) để phiên bộ lọc sau này mở rộng thay vì viết lại. Tái dùng hàm có sẵn (đọc nhãn, ghép tên ảnh, NME), không viết lại.

### 4.2 Đầu vào
- **Nhãn đã sửa = `raw/`** (bản sửa lần đầu: P5 "phải dùng file raw 14–15/10"); ba chỉ số này **không dùng `final/`** (ghi vào README). TH1/TH2: nếu lớp đọc cũ ưu tiên `final/` thì
  thêm tham số chọn nguồn; tab Thống kê dùng `raw/`, Lọc dữ liệu giữ như cũ.
- **File cả task**: `raw/<task>_<người>_<DDMM>.xml` (`collect.RAW_RE`; mới nhất mỗi người theo `collect.latest_raw_files`).
- **File theo job**: kiểm `tool/tach_job.py` có trên nhánh không. **Có**: đọc docstring/hàm của nó để biết đúng mẫu tên (không đoán) và dùng lại regex/hàm của nó. Cùng (task, người,
  ngày): có file cả task thì dùng file cả task (file job chỉ để đối chiếu: ảnh trong job phải có trong file cả task, lệch thì cảnh báo); chỉ có file job thì ghép các job (ảnh
  trùng giữa hai job → cảnh báo, giữ job id nhỏ). **Bẫy**: file job không được bị `RAW_RE`/`latest_raw_files` hiểu thành một task khác (ví dụ task `m28-assisted_job12`) và bị đếm
  hai lần; có test. **Chưa có** `tach_job.py`: chỉ đọc file cả task, ghi "chưa có file theo job" vào báo cáo.
- **Điều kiện của nhãn** (như đặc tả cũ): task `demo-…` có `push.json` (`collect.push_info`): mặt Nhận → assisted; `gan_tay_co_nhap` → assisted (loại mặt riêng); Gán tay ảnh trống →
  manual nhưng không có nháp đã nhập (không vào (1)(2), ghi số đã bỏ). Task thí nghiệm theo tên: `m28-manual`, `m28-pilot-manual`, `m28-gold-*` → manual; `m28-assisted`,
  `m28-pilot-assisted` → assisted; chứa `practice`, `check`, `smoke` → bỏ qua có lý do; không rõ → đếm riêng, không vào số theo điều kiện.
- **Nháp liên kết**: task `demo-…` → lượt trong `push.json`, nháp = đúng toạ độ đã nhập vào CVAT (`eval50.read_run_pred`, cùng tên ảnh và hệ toạ độ như `flag_eval`). Task thí
  nghiệm → chỉ khi người dùng chọn **"Lượt chứa nháp"** (ô ở tab, `--luot-nhap` ở CLI); không chọn thì (1)(2) để trống với lời "không có nháp liên kết: chọn lượt chứa nháp đã
  dùng để dựng task". Không đoán lượt. **Kiểm hợp lý**: ở task assisted, điểm người không sửa gần như trùng toạ độ nháp (≤ 0,05 px sau làm tròn XML); cả task không có điểm nào
  trùng, hoặc > 80% điểm lệch quá ngưỡng → cảnh báo "có thể chọn sai lượt nháp hoặc sai hệ toạ độ".
- Nhãn label `face50` cũ hoặc tên điểm v2 → đếm riêng "nhãn cũ", không sập (như `eval50.read_labels`). Ttest ẩn mặc định khi suy được `set` từ manifest (ô "Gồm Ttest",
  ghi chú "Ttest là tập đo một lần").

### 4.3 (1) NME nháp so với nhãn đã sửa
- Mỗi mặt có cả nháp liên kết và nhãn: `eval50.face_scores(nháp, nhãn, cfg)` (chỉ số chính, % IOD của nhãn; không công thức mới). Theo 7 nhóm: trung bình lỗi chính các điểm
  của nhóm (`group` trong config) cho từng mặt.
- Hiện **trung bình, trung vị, % mặt hỏng (≥ `eval50.BAD` = 10% IOD), n mặt** cho **tổng** và **từng nhóm** (mặt hỏng theo nhóm = NME nhóm ≥ 10%).
- Tách điều kiện, không gộp lặng lẽ: dòng **assisted** "nháp so với nhãn đã sửa" là số chính chủ repo yêu cầu, ghi chú "cận dưới: người sửa bị neo theo nháp"; dòng **manual**
  "nháp so với nhãn gán từ đầu" chỉ khi có nháp liên kết (thường task `m28-manual` + Lượt chứa nháp). Mặt Gán tay ảnh trống của task `demo-…` không tính (nháp đã bị loại khi
  rà → thiên lệch), ghi số đã bỏ. Mặt không chấm được (thiếu `iod_points`) đếm và ghi lý do.
- `N_NHO = 5` (hằng đặt tên): ô có n < 5 ghi "n quá nhỏ" thay cho số.

### 4.4 (2) Tỉ lệ điểm phải sửa (point correction rate)
- **Chỉ mặt assisted có nháp đã nhập** (manual không có nháp: ghi rõ "không áp dụng"). Mỗi điểm: khoảng cách Euclid nháp ↔ nhãn cuối chia IOD của nhãn
  (`eval50.p2p_errors`, % IOD). **Không** dùng lỗi tới đường gấp khúc (kéo điểm trượt dọc mí cũng là đã sửa).
- Điểm **đã sửa** khi khoảng cách > ngưỡng; `NGUONG_SUA = 2.0` % IOD mặc định, chỉnh được ở tab (0,5–10, bước 0,5) và `--nguong-sua` ở CLI; ngưỡng đang dùng in trên tab và
  trong bản xuất.
- Điểm có trong nháp nhưng thiếu/`outside` trong nhãn cuối (người xoá hoặc ẩn): **tính là đã sửa** (mặc định) và đếm riêng "trong đó xoá/ẩn: k". Mặt thiếu IOD trong nhãn: không
  tính, đếm.
- Hiện: tỉ lệ điểm đã sửa **tổng** (điểm sửa / điểm nháp, kèm n điểm, n mặt); **theo 7 nhóm**; và **tỉ lệ MẶT phải sửa ≥ 1 điểm**. Có cả mặt `nhan` và `gan_tay_co_nhap` thì
  thêm hai dòng tách theo loại mặt (nháp của mặt Gán tay đã bị đánh giá kém). n < 5 mặt → "n quá nhỏ".

### 4.5 (3) So sánh thời gian manual với assisted
- **Đọc**: `outputs/timing/timing_P*.csv` (tab Đồng hồ) + `timing_P*.csv` ở thư mục dự án và ở `outputs/` (file facetimer) + `--timing <thư mục>` ở CLI (ở tab chỉ nhận thư mục
  trong dự án, kiểm realpath + commonpath). File chỉ có 12 cột facetimer vẫn đọc được; thiếu cột → bỏ file đó, báo đúng tên cột thiếu, file khác vẫn đọc. Trùng khoá
  (person, task, block, seq) giữa hai file hoặc trong một file → giữ dòng của tab Đồng hồ, rồi dòng sau cùng; liệt kê là "trùng", không lặng lẽ.
- **Lọc đúng P5**: `warmup = 0`; mặc định chỉ task `m28-manual`/`m28-assisted` (ô "Chỉ task thí nghiệm"; bỏ tích thì gồm mọi task có condition manual/assisted và gắn nhãn
  "ngoài thiết kế thí nghiệm: chỉ tham khảo"). `seconds` trống/không phải số/≤ 0 → bỏ và đếm.
- **Tính** bằng numpy (không pandas trong `tool/`), đúng `snippets/p5/02_python.py`:
  - Mỗi điều kiện: giây/mặt **trung bình**, **trung vị**, n mặt.
  - r_i = giây/mặt trung bình assisted ÷ manual của từng người (trung bình, không tổng). Chỉ số chính = **trung bình nhân** các r_i; **% nhanh hơn = (1 − TB nhân) × 100**,
    mục tiêu ≥ 20% (vạch mục tiêu trên thanh).
  - **KTC 90% bootstrap**: 2.000 lần, `np.random.default_rng(28)`; mỗi lần, với từng khối theo thứ tự khối đã sắp, `rng.choice(sorted(các seq duy nhất của khối), len(...))`, đếm
    số lần mỗi seq được bốc làm trọng số cho **mọi dòng của khối** (cả manual lẫn assisted, "chung cho hai cách"); đúng thứ tự gọi RNG của đoạn P5 để số khớp. Lấy phân vị 5/95
    của TB nhân, đổi ra % nhanh hơn. Lần bốc làm một người mất hết mặt của một điều kiện (NaN) → bỏ lần đó và ghi số lần bỏ (đoạn P5 sẽ ra `nan`: nêu khác biệt).
  - **Kết luận** (chữ + ký hiệu): Đạt khi TB nhân ≤ 0,80 **và** ≥ 4/5 người có r_i < 1; Không đạt khi cận dưới KTC > 0,80 (đề xuất của P5, chờ `checkpoint_1210.md`, để hằng số);
    còn lại Chưa kết luận.
  - **Ghép cặp đúng thiết kế**: bảng mỗi người: khối gán tay (mong Xk), giây/mặt manual (n), khối sửa nháp (mong X(k+1); P5 → X1), giây/mặt assisted (n), r_i, cột thiết kế
    "✓ đúng" / "⚠ lệch (khối thật …)". Người thiếu một điều kiện → không có r_i, ghi lý do.
  - **n nhỏ** (`N_NHO = 5`): một điều kiện của một người có < 5 mặt tính giờ → r_i "n quá nhỏ". TB nhân, % nhanh hơn, KTC và kết luận chỉ hiện khi **≥ 5 người** có r_i (thiết
    kế có đúng 5 người, luật Đạt cần 4/5); ít hơn → "n quá nhỏ (k/5 người)" thay cho số; bảng từng người vẫn hiện.
  - **Ngoại lai: đánh dấu, không bỏ ngầm.** Dòng `interrupted = 1`, `sua_tay = 1`, có `canh_bao`, dòng trùng, dòng > Q3 + 3·IQR trong (người, điều kiện) được **đánh dấu và liệt kê**
    (người, khối, seq, giây, lý do) nhưng **vẫn nằm trong chỉ số chính** như giao thức; thêm một dòng **"độ nhạy: bỏ ngoại lai"** (TB nhân và % nhanh hơn khi bỏ chúng, không KTC).

### 4.6 Trình bày, xuất tĩnh, CLI
- Hàng điều khiển trên cùng: Lượt chứa nháp, Ngưỡng sửa (% IOD), Chỉ task thí nghiệm, Gồm Ttest, Làm mới, Xuất CSV + HTML. Tính **khi chọn tab**, không lúc mở trang (cache theo
  mtime nếu cần). Nhóm chưa có dữ liệu → khung trống nói rõ cần gì, ví dụ "Chưa có nhãn đã sửa: cần `raw/<task>_<Pk>_<DDMM>.xml` (P4 `collect` / `export.py`)", "Chưa có dòng
  bấm giờ: dùng tab Đồng hồ (thí nghiệm 14–15/10) hoặc chép `timing_Pk.csv` vào `outputs/timing/`".
- Nếu phiên có skill `dataviz` thì nạp trước khi viết HTML biểu đồ. Không có thì theo đúng: HTML/CSS thuần; ô số tiêu đề kèm n; thanh ngang **từ 0**, cùng thang trong một bảng,
  số in cạnh thanh; vạch mục tiêu có nhãn chữ (20% nhanh hơn; 10% IOD mặt hỏng); không biểu đồ tròn, không 3D, không hai trục; màu 7 nhóm từ `mau_nhom.GROUP_COLOR` luôn kèm tên
  `GROUP_VI`; chữ dùng màu theme (`var(--body-text-color)`), không dùng màu nhóm cho chữ; Đạt/Không đạt/Chưa kết luận có chữ + ký hiệu; dấu phẩy thập phân trên trang/HTML, dấu
  chấm trong CSV; tooltip bằng `title`; theme sáng/tối; 420 px. Một hàm dựng HTML dùng chung cho tab và bản xuất. `elem_id` tiền tố `tk-`.
- **Xuất**: `outputs/thong_ke/<YYYYMMDD-HHMM>/thong_ke.html` (một file, CSS nội tuyến, sáng/tối theo `prefers-color-scheme`) + CSV (`utf-8-sig`, an toàn công thức, dấu chấm),
  mặc định `nme.csv` (tổng và nhóm × điều kiện), `ti_le_sua.csv`, `thoi_gian.csv` (theo điều kiện + chỉ số chính + KTC + kết luận), `thoi_gian_nguoi.csv`, `ngoai_lai.csv`; TH1/TH2
  giữ `nme_nhap.csv` theo mặt nếu đã có (cột đầu trùng tên và nghĩa `nme_per_face.csv`). **Chỉ ba nhóm số này**: không ảnh mặt (`<img`), không mã tài xế (`subject`, `yd_`, `df_`),
  không đường dẫn tuyệt đối, không token/email; có dòng nguồn dữ liệu (YawDD, DrivFace) + "phi thương mại, chỉ dùng nội bộ nhóm", ngày lập, commit, config version, ngưỡng sửa,
  danh sách file nhãn và file bấm giờ đã dùng (tên tương đối).
- **CLI** `python tool/thong_ke.py [--luot-nhap <lượt>] [--nguong-sua 2] [--tat-ca-task] [--gom-ttest] [--timing <thư mục>] [--out outputs/thong_ke]` (TH1/TH2: giữ cờ cũ còn hợp
  lệ, bỏ cờ của thẻ bị bỏ, nêu thay đổi). `--help` tiếng Việt; mã thoát 0 xong, 2 lỗi dữ liệu/tham số; in đường dẫn tương đối.
- `allowed_paths`: chỉ đúng `outputs/thong_ke` nếu tab có nút tải (như `ca_kho.serve_dir`); không `outputs/`, không `outputs/timing`, không `runs/`, `raw/`.
- Handler: `api_visibility="private"`, `concurrency_id` riêng, tôn trọng `ctx.closing`; lỗi → `gr.Warning` + thông báo tiếng Việt, không traceback lên trang.

## 5. Test (pytest; dữ liệu giả trong `tmp_path`, không ảnh thật, không mạng)

- **Đồng hồ (đồng hồ giả tiêm vào):** bắt đầu/tạm dừng/tiếp tục/xong mặt/xong (lưu) cho đúng giây (trừ tạm dừng, làm tròn 0,1); `interrupted`; `warmup` cả khi bắt đầu từ seq
  giữa khối; `face_id`; đủ n mặt thì dừng; mặt < 2 giây bị từ chối; Hoàn tác gộp đúng; bỏ tích "Tính mặt đang làm" = `q`; **Hủy không ghi dòng nào** (file CSV không đổi từng byte)
  và có dòng `huy_<người>.csv`; xác nhận gõ sai / mã hết hạn không hủy; trạng thái khôi phục khi dựng đối tượng mới từ file (giả lập tải lại trang, tắt trang); khởi động lại máy
  (`moc_mono` lệch) → tính bằng giờ thật + `khoi_dong_lai`; `pid` chết → đề nghị trừ khoảng tắt trang; quá 20 phút/150 phút/qua nửa đêm → cảnh báo; sửa tay trong giới hạn,
  ngoài giới hạn bị từ chối; giây ≤ 0 không bao giờ ghi; một phiên mỗi người; `rev` cũ bị từ chối; hai luồng cùng bấm Xong (lưu) → đúng một lần ghi; khoá mồ côi; file trạng
  thái hỏng → không sập, đổi tên khi bấm bỏ; ghi nguyên tử (giả lập lỗi `os.replace` → CSV cũ nguyên vẹn, trạng thái còn); header: đủ → nối, 12 cột → nâng cấp có `.bak`, lạ →
  từ chối; 12 cột đầu đúng facetimer; UTF-8 không BOM, CRLF, chữ Việt; `_formula_safe` cho ghi chú bắt đầu bằng `=`; tự tạm dừng khi đóng trang; người ngoài P1–P5 bị từ chối;
  task/điều kiện lệch bị từ chối; khối lệch thiết kế có cảnh báo; seq trùng cần bấm lần hai.
- **Tương thích P5:** nếu máy có pandas (`pytest.importorskip("pandas")`), chạy logic của `snippets/p5/02_python.py` trên CSV do chính `dong_ho.py` ghi (trộn với một file facetimer
  12 cột) và so: r_i, TB nhân và KTC 90% của `thong_ke` khớp tới 1e-9. Không có pandas: so với số tính tay trên 5 mẫu nhỏ.
- **Thống kê:** NME tổng/nhóm khớp `eval50`; tách manual/assisted; Gán tay ảnh trống bị bỏ có đếm; tỉ lệ sửa với ngưỡng 2% và ngưỡng khác; điểm xoá/ẩn tính là sửa; tỉ lệ mặt ≥ 1
  điểm; cảnh báo sai lượt nháp; file theo job (nếu có `tach_job.py`): ghép, không đếm hai lần, không bị hiểu thành task khác; chỉ đọc `raw/`, không `final/`; thời gian: warmup,
  lọc task, r_i, TB nhân, luật Đạt/Không đạt/Chưa kết luận, bootstrap seed 28 lặp lại được, NaN bị bỏ có đếm, ngoại lai đánh dấu mà vẫn trong chỉ số chính, dòng độ nhạy,
  trùng khoá, thiếu cột, "n quá nhỏ" (< 5 mặt, < 5 người), ghép cặp đúng/lệch thiết kế; trạng thái trống khi chưa có nhãn/nháp/timing (không có số nào); **các thẻ bị bỏ không còn**
  trên tab và HTML xuất; HTML xuất không `<img`, không đường dẫn tuyệt đối, không "token", không `yd_`/`df_`; CSV an toàn công thức; `runs/ raw/ final/ data/` không đổi (băm).
- **Giao diện (không trình duyệt):** `pytest.importorskip("gradio")`, dựng `review_app.build_ui` có lượt và chế độ `--nap` (store `None`) theo cách `test_cai_dat.py`/`test_cvat_smoke.py`;
  có tab Đồng hồ và Thống kê, thứ tự tab đúng; `elem_id` không trùng; `PAGE_JS` chứa JS đồng hồ; đường đóng trang gọi tự tạm dừng; `allowed_paths` không rộng hơn mục 4.6.
- `test_no_torch.py`, `test_chay_sh.py`, `test_chay_bat.py` vẫn xanh. Toàn bộ `python -m pytest tests -q` xanh, số qua ≥ số gốc.
- **e2e Playwright** `tests/e2e_dong_ho.py` (tên không khớp `test_*.py`): **chỉ chạy nếu** `python -c "from playwright.sync_api import sync_playwright"` chạy được **và** Chromium
  của Playwright có sẵn (`ls ~/.cache/ms-playwright/`); không có thì bỏ qua, ghi lý do. Kịch bản: cwd = `/tmp/m28_dong_ho/work`, `--nap P5`, cổng 7861; tab Đồng hồ: Bắt đầu,
  3 giây sau mm:ss đã tăng mà không có request nào mỗi giây (đếm request), Tạm dừng 2 giây số đứng yên, Tiếp tục, Xong mặt × 2, tải lại trang → phiên còn, mở tab thứ hai bấm Tạm
  dừng → tab đầu bấm Xong mặt bị từ chối vì `rev` cũ, Hủy (gõ sai không hủy; gõ `HUY` → không có dòng CSV, có dòng `huy_P5.csv`), phiên mới → Xong (lưu) → CSV đúng; tab Thống kê
  với dữ liệu giả; không request ra ngoài 127.0.0.1; `lsof` (nếu có) thấy cổng chỉ bind 127.0.0.1; chụp 1440×900 và 420 px vào `/tmp/m28_dong_ho/shots/`.

## 6. Tự kiểm trên máy (bắt buộc)

1. **Dữ liệu thật, chỉ đọc** (cwd = `M`): băm trước/sau
   `find runs raw final data outputs -type f -print0 2>/dev/null | sort -z | xargs -0 sha256sum > /tmp/m28_dong_ho/bam_truoc.txt` (rồi `bam_sau.txt`, `diff`); chạy
   `python tool/thong_ke.py --out /tmp/m28_dong_ho/out/that` (và `--luot-nhap` nếu có lượt hợp lý). Ghi vào báo cáo: có/không nhãn `raw/`, file theo job, `timing_P*.csv` (pilot
   9–10/10 của facetimer nếu có), lượt có `push.json`, thời gian chạy, băm không đổi. **Không** mở tab Đồng hồ trên thư mục thật để bấm thử.
2. **Dữ liệu giả ở `/tmp/m28_dong_ho/work/`** (ghi rõ là giả trong báo cáo; không để file giả nào trong `M`): `cp -r` `config/` (và `data/manifest.csv` nếu cần); lượt giả không ảnh
   (dựng như test, hoặc chép từ một lượt thật CHỈ `map50/mp50.json`, `crop/meta.json`, `crop/box.txt`, `xml/prelabel.xml`, `push.json`; không ảnh, không `overlays/`, `cp` không
   symlink); nhãn giả từ nháp: `raw/m28-assisted_P1_1510.xml` (~70% điểm giữ nguyên, một số lệch 1–5% IOD, vài điểm > 10%, vài điểm bị xoá) và `raw/m28-manual_P2_1410.xml`
   (nhiễu mọi điểm); có `tach_job.py` thì thêm file theo job; `outputs/timing/timing_P1..P5.csv` đúng thiết kế (Pk manual Xk, assisted X(k+1), P5 assisted X1, 10 mặt/khối,
   warmup seq 1–2, assisted nhanh hơn 25%, seed cố định, thêm 2 ngoại lai, 1 dòng `interrupted`, 1 dòng `sua_tay`), sinh bằng **chính hàm ghi của `dong_ho.py`** (định dạng thật)
   với đồng hồ giả, cộng một file 12 cột kiểu facetimer. Chạy CLI: % nhanh hơn gần 25%, có KTC và kết luận, ngoại lai được liệt kê; tỉ lệ sửa gần mức đã gieo; NME có số. Có
   pandas thì chạy bản chép của `snippets/p5/02_python.py` (cwd = thư mục timing giả) và so số. Mở trang:
   `cd /tmp/m28_dong_ho/work && M28_NO_BROWSER=1 GRADIO_SERVER_PORT=7861 python <M tuyệt đối>/tool/review_app.py --nap P5` (đường dẫn tuyệt đối chỉ trong lệnh, không vào repo),
   bấm thử đồng hồ (e2e hoặc gọi hàm logic), xuất thống kê.
3. **Ảnh chụp tab**: có Playwright thì lấy từ e2e. Không có: (a) HTML xuất: `chromium --headless=new --disable-gpu --window-size=1440,2400 --screenshot=<png> file://<html>`
   (hoặc `google-chrome`, cả bản 420 px); **Chromium bản snap** (`which chromium` ra `/snap/...`) có `/tmp` riêng nên không đọc/ghi được `/tmp` của máy → dùng thư mục ngoài repo
   trong `$HOME` (ví dụ `~/m28_dong_ho_shots/`) rồi xoá sau; (b) tab Gradio: script tạm trong `/tmp/m28_dong_ho/` dựng `gr.Blocks` chỉ có tab Đồng hồ (và tab Thống kê) với ctx giả,
   `project_root` = `work`, cùng `PAGE_JS`/`CSS`, launch 127.0.0.1 cổng 7862, chụp bằng chromium headless `--virtual-time-budget=15000`; không được thì ghi "chưa chụp" và cách tự xem
   (`./chay.sh` mục 1 → tab Đồng hồ / Thống kê). **Xem từng ảnh bằng Read**, ghi nhận xét (chữ đè, tràn ngang ở 420 px, số chạy, trạng thái trống, màu nhóm, theme).

## 7. Tài liệu, sổ quyết định, chay.sh
- `README.md`: thêm vào bảng (tab Đồng hồ; Thống kê ba chỉ số + CLI), đầu vào/đầu ra (`outputs/timing/timing_<Pk>.csv` và cột, khác biệt với facetimer), giới hạn.
- `HUONG-DAN-UBUNTU.md`: mục mới "Bấm giờ và thống kê" (bash): mở trang, quy trình buổi 14–15/10 với tab Đồng hồ (đầu buổi khôi phục task của hôm nay rồi mới bấm Bắt đầu;
  mặt qua checklist thì bấm Xong mặt; bị gián đoạn bấm Tạm dừng; hết khối bấm Xong (lưu); gửi `outputs/timing/timing_Pk.csv` cho P5 trong đội), quên bấm, Hủy, chỗ đặt file;
  tab Thống kê và CLI; cảnh báo dữ liệu nhạy cảm. `HUONG-DAN-WINDOWS.md`: cùng mục bằng **cmd** (đường dẫn `\`), giữ đồng bộ nội dung.
- `TAI-LIEU-CHI-TIET.md`: chi tiết trạng thái/khoá/CSV/khác biệt facetimer, cách tính ba chỉ số, ngưỡng, ngoại lai, nguồn nhãn (`raw/`, file theo job), bản xuất. Docstring đầu
  `review_app.py`. Ghi số test mới.
- `chay.sh`/`chay.bat`: **không thêm mục menu** (`test_chay_bat.py` đòi `choice /C 1234567`, `test_chay_sh.py` đòi mục 1–7); chỉ sửa dòng mô tả mục 1 thêm "Đồng hồ, Thống kê"
  ở cả hai file (`chay.bat` ASCII không dấu, CRLF; `chay.sh` LF). Test vẫn xanh.
- `so-quyet-dinh.md`: thêm QĐ **số tiếp theo** đúng mẫu cuối file + một dòng ở bảng Danh sách (TH3: QĐ-005; TH1/TH2 đã có QĐ-005 của bộ lọc: QĐ-006, và chỉ đổi **trạng thái**
  QĐ-005 thành "Bị thay một phần bởi QĐ-006 (trang Thống kê chỉ còn ba chỉ số); bộ lọc vẫn hiệu lực"). Nội dung: ngày = ngày chạy phiên; người tham gia: chủ repo (chốt), P5 (chờ
  duyệt: giao thức bấm giờ), P2 (trang), P3 (NME, ngưỡng sửa), P4 (`raw/`, file theo job, tên task); xuất phát: yêu cầu chủ repo sau khi xem trang Thống kê; bối cảnh; phương án:
  (1) giữ facetimer dòng lệnh + Thống kê 4 nhóm (loại: nhiều số không dùng, dễ quên, Ctrl+C mất mặt đang làm), (2) đồng hồ một dòng mỗi phiên (loại: không tính được warmup và
  bootstrap theo mặt), (3) **tab Đồng hồ một dòng mỗi mặt theo định dạng facetimer + Thống kê ba chỉ số (chọn)**; quyết định: **thống kê chỉ ba chỉ số** (NME, tỉ lệ điểm phải sửa
  ngưỡng 2% IOD, thời gian theo giao thức P5), **đồng hồ thay facetimer** cho thí nghiệm (file facetimer cũ vẫn đọc được), ghi ở `outputs/timing/`, Hủy không ghi, Lọc dữ liệu
  giữ nguyên; việc phải làm theo: @P5 duyệt khác biệt với facetimer, đổi câu chung thành "Đầu buổi khôi phục task của hôm nay, rồi mới bấm Bắt đầu ở tab Đồng hồ", chốt luật
  Không đạt; @P3 duyệt ngưỡng 2% IOD và cách tính điểm xoá; @P4 xác nhận mẫu tên file theo job; @P2 duyệt tab; chủ repo cập nhật `CLAUDE.md`/Claude Docs (tab P5 còn ghi
  facetimer.py); trạng thái Hiệu lực.
- `prompts/prompt_loc_thongke_local.md`: thêm **một khối ghi chú ở đầu file** (không sửa phần còn lại): "Mục 4 (trang Thống kê 4 nhóm) đã bị thay bởi
  `prompt_dong_ho_thongke_local.md` và QĐ-00x: chạy prompt này thì chỉ làm bộ lọc (mục 2, 3) và tab Lọc dữ liệu, dùng lại `bang_mat`/`thong_ke` đã có, không thêm lại thẻ cờ,
  số lượng, tiến độ, giây rà vào tab Thống kê."
- `.gitignore`: kiểm `outputs/` và `timing_*.csv` đã bị chặn; không gỡ dòng nào.

## 8. Trình tự commit (mỗi bước một commit nhỏ, test liên quan xanh trước khi commit)
1. `dong_ho.py` + test. 2. `dong_ho_ui.py`, JS, nối `review_app` (tab, tự tạm dừng khi đóng) + test giao diện. 3. Đọc timing + giao thức P5 trong `thong_ke` + test (so đoạn P5).
4. Thu gọn/làm mới tab Thống kê: NME, tỉ lệ sửa, nguồn nhãn `raw/` + file theo job, xuất tĩnh, CLI + test. 5. e2e (nếu có Playwright). 6. Tài liệu, `chay.sh`/`chay.bat`, QĐ,
ghi chú đầu prompt cũ. Trước mỗi commit: `git status` (không ảnh, không `runs/`/`data/`/`outputs/`/`raw/`/`timing_*.csv`/zip, không file trong `/tmp`), `git diff --stat`.

## 9. Tự soát trước khi báo cáo
Đọc lại **toàn bộ diff** (`git diff <gốc>...HEAD`), ghi Đạt/Chưa/Lý do cho từng mục: (1) đủ nút, nút Xong mặt và lý do; Hủy có xác nhận và không ghi dòng nào; (2) nguồn sự thật là
monotonic ở server, file trạng thái nguyên tử, khôi phục sau tải lại/tắt trang/khởi động lại; (3) một phiên mỗi người, `rev` + khoá; (4) CSV 12 cột đầu đúng facetimer, cột thêm ở
cuối, UTF-8, chống công thức, mọi khác biệt đã liệt kê; (5) ca bất thường đủ test; (6) Thống kê chỉ ba chỉ số, thẻ bị bỏ không còn, Lọc dữ liệu nguyên vẹn; (7) NME và tỉ lệ sửa
đúng định nghĩa, ngưỡng chỉnh được; (8) thời gian đúng giao thức P5 (số khớp đoạn P5), ghép cặp thiết kế, "n quá nhỏ", ngoại lai đánh dấu; (9) nhãn từ `raw/`, file theo job không
đếm hai lần; (10) trạng thái trống không bịa số; xuất tĩnh không ảnh/mã tài xế/đường dẫn tuyệt đối; (11) 127.0.0.1, `allowed_paths` hẹp, không gọi CVAT/mạng; (12) chỉ đọc dữ liệu
thật (băm); (13) pytest ≥ gốc, `test_no_torch` xanh, không thêm gói; (14) tài liệu, QĐ, ghi chú prompt cũ; `de-tai-m28/`, `CLAUDE.md` không đổi; không đường dẫn máy/token trong repo;
không push.

## 10. Báo cáo cuối (tiếng Việt, trung thực, ngắn mà đủ)
1. Tóm tắt; trường hợp TH1–TH4, nhánh gốc, commit gốc, có gộp main không; `git log --oneline <gốc>..HEAD`.
2. Danh sách file thêm/sửa theo nhóm (tool, tests, tài liệu, sổ quyết định, prompt cũ).
3. **Mặc định đã chọn** và lý do (nút Xong mặt, ghi lúc Xong (lưu), tên cột thêm, ngưỡng 2 giây/20 phút/150 phút, tự tạm dừng khi đóng trang, nhịp `gr.Timer`, ngưỡng sửa 2% IOD,
   điểm xoá tính là sửa, `raw/` không `final/`, cách ghép file theo job, `N_NHO`, luật Không đạt, vị trí tab, tên module, thư mục xuất…).
4. **Bảng khác biệt với facetimer** (từng dòng).
5. Số liệu tự kiểm trên **dữ liệu thật** (6.1) và trên **dữ liệu giả** (6.2, ghi rõ là giả), so khớp với đoạn P5, thời gian chạy, băm không đổi.
6. **Ảnh chụp** đã xem (đường dẫn trong `/tmp`, mỗi ảnh một dòng nhận xét); ảnh nào chưa chụp và vì sao.
7. pytest: số gốc → số sau (qua/bỏ qua), test mới; e2e chạy hay bỏ qua (lý do).
8. **Chưa thử**: nhãn thật xuất từ CVAT (bảy skeleton), file theo job thật, bấm giờ thật buổi 14–15/10, trình duyệt thật nếu không có Playwright, Windows/cmd, hai trang ở hai cổng.
9. **Việc cần người đồng ý**: chủ repo (nút Xong mặt thay cho "một dòng mỗi phiên", QĐ mới, bỏ các thẻ), P5 (khác biệt facetimer, câu chung buổi thí nghiệm, NaN trong bootstrap,
   luật Không đạt, "n quá nhỏ" khi < 5 người), P3 (ngưỡng 2% IOD, điểm xoá tính là sửa), P4 (mẫu tên file theo job), P2 (tab); kèm đề xuất sửa `CLAUDE.md`/Claude Docs.
10. Lệnh người dùng chạy tiếp (bash): xem commit, chạy test, mở trang (`./chay.sh` mục 1 → tab Đồng hồ / Thống kê), chạy `python tool/thong_ke.py`.
