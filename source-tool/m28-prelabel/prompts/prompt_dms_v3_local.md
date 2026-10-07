# Prompt chạy LOCAL (Windows) — M28 giai đoạn 3: định nghĩa 50 điểm DMS (config v3)

> Cách dùng: `git pull` ở `D:\AI\T015-SIXSEVEN`, mở Claude Code trong thư mục đó rồi gõ:
> `Đọc source-tool\m28-prelabel\prompts\prompt_dms_v3_local.md và thực hiện đúng và đầy đủ.`

## 0A. GHI ĐÈ cho môi trường local (ƯU TIÊN hơn mọi chỗ trong bản gốc bên dưới)

Bản gốc bên dưới viết cho phiên cloud Linux. Khi chạy trên máy này, áp dụng các thay đổi sau:

- **Đường dẫn.** Repo là thư mục hiện tại (ví dụ `D:\AI\T015-SIXSEVEN`); `M` = `source-tool\m28-prelabel`. Không có `$S` hay `/tmp/claude-0/...`.
  Thay `$S` bằng thư mục `%TEMP%\m28_dms_v3\` (tạo mới, ngoài repo) cho script tạm, ảnh kiểm (`inc3_*.jpg`), bản sao config v2 (`v2_old\`), log.
- **Dữ liệu.** Thư mục chạy là `M` (cwd = `M`). Dữ liệu in-cabin đã giải nén ở `M\data\` (có `manifest.csv`, `crops\`, `frames\`; gói zip
  `m28_incab_part*`). `M\data\` đã bị `.gitignore` chặn: không được commit. Nếu `data\manifest.csv` hoặc `crops\` thiếu/hỏng thì DỪNG và báo, đừng tự tải lại.
- **Không có bản gốc YawDD/DrivFace** trừ khi thấy `M\data\drivface\` hoặc thư mục DrivFace do người dùng chỉ ra. Nếu không có `drivPoints.txt` thì
  **bỏ mục so DrivFace** (không tải về), ghi rõ vào báo cáo là chưa đo; các việc còn lại (mapping, mirror, flip, pipeline, test) vẫn làm đủ.
- **Lệnh dùng cmd** (không PowerShell, không `&&` kiểu bash trong tài liệu; trong phiên thì dùng shell sẵn có cũng được). Python của máy (3.14), venv của `chay.bat` nếu có.
- **Bỏ phần cloud:** không dùng `/opt/pw-browsers`, `PLAYWRIGHT_BROWSERS_PATH`, `PYTHONPATH=$S/pwlib`, `bsdtar`. `tests/e2e_*.py` chỉ chạy nếu
  Playwright + Chromium đã cài sẵn; nếu chưa có thì bỏ qua và ghi vào báo cáo (không `playwright install`, không cài thêm gì).
- **pytest gốc:** chạy `python -m pytest tests -q` trong `M` trước khi sửa để lấy số gốc của máy (trên cloud là 657 qua + 1 bỏ qua; máy này có thể khác vì
  skip/thiếu gói — ghi số thật). Sau khi làm xong, số qua không được ít hơn số gốc trừ các test cố ý thay bằng test v3 tương đương.
- **Nhánh git:** làm trên nhánh `dms-v3` tạo từ `main` mới nhất (`git checkout -b dms-v3`). Commit nhỏ, rõ ràng bằng tiếng Việt. **KHÔNG push**, không tạo PR; để người dùng đọc rồi tự quyết định. (Ghi đè dòng "không commit" ở bản gốc: local được commit lên nhánh `dms-v3`.)
- **Mọi quy tắc quyền riêng tư giữ nguyên:** không ảnh/`runs/`/`data/`/token vào git; ảnh kiểm chỉ ở `%TEMP%`. Không gọi CVAT thật; không `share=True`.
- **Xem ảnh kiểm** bằng công cụ đọc ảnh của Claude Code (Read); ghi vào báo cáo điều thấy được.
- Cuối cùng in báo cáo theo mẫu ở bản gốc và ghi thêm: số pytest gốc/sau, mục nào bỏ qua vì thiếu dữ liệu local, lệnh người dùng chạy tiếp (`git log --oneline main..dms-v3`, `chay.bat` mục 3 chạy nhanh để thử).

---

# BẢN GỐC (viết cho cloud; đọc cùng mục 0A ở trên)

# Prompt triển khai — M28 in-cabin, Giai đoạn 3: định nghĩa 50 điểm "DMS" (config v3), chiều trái/phải theo ảnh, chạy thật

Bạn là kỹ sư triển khai trong repo `/home/user/T015-SIXSEVEN` (đề tài M28, đội T015-SIXSEVEN). Hôm nay 7/10/2026. Làm **toàn bộ** việc dưới đây trong
phiên này, tự kiểm, rồi viết báo cáo cuối trung thực. **Không commit, không push** (người điều phối commit). Trả lời và viết tài liệu bằng tiếng Việt.

## 0. Đọc trước khi sửa (bắt buộc, đọc hết chứ không đọc lướt)

- `CLAUDE.md` (mục "Quyết định đã chốt", "Quy tắc bắt buộc"), `so-quyet-dinh.md` (QĐ-001, QĐ-002 và mẫu cuối file).
- `source-tool/m28-prelabel/README.md`, `BAO-CAO-CO-LOW-CONF.md`, `HUONG-DAN-WINDOWS.md`, `nguon-du-lieu.md`, `chay.bat`.
- Code (thư mục `source-tool/m28-prelabel/`, gọi tắt là `M`):
  - `tool/make_config.py` (bảng `SPEC`, `COINCIDE`, `CLOSED`, `build_config`, `check_perm`, `build_map`, `estimate_flip_width`, `template`, `keep_existing`, `main`);
  - `tool/m28core/mapping.py` (`apply_map`), `tool/m28core/mirror.py` (`learn_mirror_flip`, `sanity`, `load_mirror`, `IOD_VERTS`), `tool/m28core/steps.py`
    (`map50`, `flags` — dùng `iod_points`, `autoqc`, `overlays`, `build_xml` — skeleton `face50`);
  - `tool/eval50.py` (`region == "eye"`, `coincide`, cột `reg_<region>` của `nme_per_face.csv`), `tool/check_flip.py` (`side_ok` dùng p33/p39, p01/p17),
    `tool/flag_eval.py`, `tool/check_drivface.py` (`side_convention`, `ours_five` dùng line `eye_R/eye_L`, p29, p31, p41, p45), `tool/make_label.py`
    (`SIDE_COLOR`, `edges_of` nối điểm liền nhau trong cùng `line`), `tool/m28core/push.py` (`LABEL = "face50"`, kiểm label project đủ 50 sublabel đúng tên),
    `tool/m28core/cvat_io.py`, `tool/m28core/collect.py`, `tool/cvat_smoke.py`, `tool/cai_dat.py`/`cai_dat_ui.py` (hiện `iod_points`).
- Test có tên điểm v2 viết cứng (grep `p[0-9]{2}_(jaw|brow|nose|eye|lip)_[RLM]`): `tests/test_mapping.py` (~32 chỗ), `test_check_drivface.py` (~22),
  `test_eval50.py`, `test_ca_kho.py`, `test_cai_dat.py`, `test_check_flip.py`, `test_flag_eval.py`, `test_m28.py`, `test_inc_ingest.py`, `e2e_ca_kho.py`, `e2e_cai_dat.py`.
- Config: `config/m28_config.json` (v2), `config/map_mp50.json`, `config/mp_mirror478.json`, `config/face50_label.json`, `config/pipeline.json`.
- `de-tai-m28/` là **bản chụp, KHÔNG sửa**. `tool/legacy_wflw/` **giữ nguyên** (không sửa, không xoá; test legacy vẫn phải qua).

Ghi nhớ: chữ ký `apply_map(pts478, map, config, flipped=False, width=None)` và chỗ gọi trong `steps.map50` GIỮ NGUYÊN. Trước khi làm, chạy
`cd /home/user/T015-SIXSEVEN/source-tool/m28-prelabel && python -m pytest tests -q` để có số gốc (người điều phối ghi: **657 qua + 1 bỏ qua**).

## 1. Bối cảnh

- QĐ-001: bỏ WFLW, dữ liệu in-cabin YawDD + DrivFace, phi thương mại. QĐ-002: 50 điểm đặt **trực tiếp lên đỉnh MediaPipe** Face Landmarker (478 đỉnh có iris),
  config v2 (`mp_idx`, `curve` là tên điểm), `config/mp_mirror478.json` là hoán vị gương 478 đỉnh, `flip_width` ước lượng không cần đáp án. Giai đoạn 2 đã xong
  (commit `56ba446`, gộp `158d440`).
- **Chủ repo vừa chốt định nghĩa mới thay hẳn 50 điểm cũ, gọi là "DMS"** (Driver Monitoring System). Phương pháp chọn đỉnh trực tiếp của QĐ-002 giữ nguyên;
  chỉ đổi tập điểm, tên và quy ước bên.

### 1.1 Định nghĩa DMS (chủ repo chốt — không tự đổi số điểm hay tên nhóm)

| Nhóm (`group`) | Số điểm | Nội dung |
|---|---|---|
| `longmaytrai` | 5 | lông mày bên TRÁI của ảnh |
| `longmayphai` | 5 | lông mày bên PHẢI của ảnh |
| `songmui` | 4 | sống mũi, từ giữa hai mắt xuống chóp mũi |
| `mattrai` | 8 | mắt bên TRÁI của ảnh |
| `matphai` | 8 | mắt bên PHẢI của ảnh |
| `moingoai` | 12 | viền ngoài môi |
| `moitrong` | 8 | viền trong môi |
| **Tổng** | **50** | |

- **KHÔNG có viền hàm/cằm**, không có cánh mũi/chân mũi. **KHÔNG có khung đầu (head box)**: không làm, không đặt chỗ trống, không thêm trường dự phòng.
- **Chiều trái/phải theo BỨC ẢNH, không soi gương**: `matphai`/`longmayphai` nằm ở nửa PHẢI của ảnh (theo người xem), `mattrai`/`longmaytrai` ở nửa TRÁI.
  Quy ước này **ngược** với v2 (v2: `side` theo người trong ảnh, R = nửa trái ảnh). Phải đổi toàn bộ: tên bên, cặp `flip`, `side`, `iod_points`, kiểm bên của
  `check_flip`, ghép bên của `check_drivface`, màu theo bên của `make_label`, tài liệu — và **kiểm lại bằng ảnh thật** (mục 3.2). Lưu ý đỉnh MediaPipe 33
  (khoé ngoài mắt phải CỦA NGƯỜI) nằm ở nửa trái ảnh khi ảnh không lật, nên theo quy ước mới nó thuộc `mattrai` — xác minh bằng ảnh, đừng tin câu này.

### 1.2 Dữ liệu thật trên cloud (KHÔNG đưa vào repo)

Đặt `S=/tmp/claude-0/-home-user-T015-SIXSEVEN/777f6f16-d3e2-509e-b0b3-59b796760279/scratchpad`, `M=/home/user/T015-SIXSEVEN/source-tool/m28-prelabel`.
- `$S/work/` = thư mục chạy thử: `config/` (bản v2 của giai đoạn 2), `face_landmarker.task`, `data` → symlink `$S/incab_data` (`crops/<file>.png` 616 ảnh cắt 512,
  `frames/<nguồn>/<người>/<tên>.jpg` khung gốc, `manifest.csv` có cột `set` (F 300, Tdev 100, Ttest 100, X 50, D 30, G 20, P 16), `source`, `pose`, `yaw`, `glasses`,
  `state`, `expression`, `gaze_label`…). Các lượt giai đoạn 2: `runs/INC2_ALL` (616 mặt, `--box auto`), `runs/INC2_XCROP`, `runs/INC2_TFLIP`. `$S/work/data_wflw`:
  **KHÔNG dùng**. Script và ảnh kiểm giai đoạn 2 ở `$S/inc2/` (ví dụ `vert_pages.py`, `render.py`, `overlay_grids.py`, `df_shots.py`) — được tái dùng/chép sang `$S/inc3/`.
- DrivFace: `$S/incab/drivface/DrivFace/` — ảnh `imgs/DrivImages/` (606 ảnh 640×480, **tên có dấu cách trước `.jpg`**), `drivPoints.txt` (cột `fileName` có dấu
  cách cuối, không có `.jpg`; `subject,imgNum,label(1=lr,2=f,3=lf),ang,xF,yF,wF,hF,xRE,yRE,xLE,yLE,xN,yN,xRM,yRM,xLM,yLM`).
- Ảnh kiểm/lưới: `$S/ui_shots/inc3_*.jpg`. **Phải mở và XEM từng ảnh `inc3_*.jpg` bằng công cụ Read** (không chỉ tạo ra), và ghi vào báo cáo điều thấy được.
  Script tạm để trong `$S/inc3/`, không để trong repo.
- Môi trường: Linux, Python 3.11, mediapipe, opencv, numpy; **không có scipy**; `tool/` chỉ được dùng numpy, cv2, mediapipe như hiện có (không scipy/sklearn/torch).
  Đích thật của đội: Windows + Python 3.14 + cmd → code không dùng gì riêng Linux, lệnh trong tài liệu viết cho **cmd**.

### 1.3 Quy tắc dữ liệu và an toàn (bắt buộc)

- Chỉ xử lý ảnh YawDD và DrivFace. Không đưa vào git: ảnh, ảnh cắt, ảnh chồng, `runs/`, `data/`, file xuất CVAT, đáp án. Ảnh kiểm chỉ ở `$S/`.
- Được sửa `so-quyet-dinh.md` **chỉ để thêm QĐ-003** và đổi dòng trạng thái của QĐ-002 (mục 7.2). Không sửa `de-tai-m28/`, `CLAUDE.md` (đề xuất sửa trong báo cáo).
- Không ghi token/mật khẩu/email ở đâu. Không gọi CVAT thật. Không `share=True`, không tunnel. Không `playwright install` (Chromium ở `/opt/pw-browsers`).
- **Ttest không dùng** để chọn đỉnh, `flip_width`, `tmpl` hay `t_flip`. Chọn đỉnh trên F (và D/X để nhìn ca khó), `t_flip` trên Tdev.
- Không đường dẫn tuyệt đối của cloud (`/tmp/claude-0/...`) trong code hay tài liệu của repo.

## 2. Việc 1 — Quy ước điểm DMS (đặt tên, thứ tự, các trường config)

Quy ước dưới đây là **đề xuất mặc định**; chỉ được đổi khi có lý do kỹ thuật rõ (ghi vào docstring `make_config.py` và báo cáo). Không đổi số điểm/nhóm.

### 2.1 Tên và thứ tự
- Tên điểm `<nhóm>_<k>`, k đếm từ 1, không đệm số 0: `longmaytrai_1` … `moingoai_12`. Thứ tự nhóm trong config (và trong CVAT): `longmaytrai`, `longmayphai`,
  `songmui`, `mattrai`, `matphai`, `moingoai`, `moitrong`. **Chú ý so chuỗi**: `moingoai_10` < `moingoai_2` theo chữ — mọi chỗ code sắp tên theo chữ cái
  (grep `sorted(` và so sánh `<` trên tên, ví dụ `eval50` dùng `p["name"] < p["coincide"]` để bỏ trùng cặp) phải vẫn đúng hoặc chuyển sang thứ tự config.
- Thứ tự trong nhóm đi **theo vòng/dọc đường** để `make_label.edges_of` (nối điểm liền nhau cùng `line`, nối kín khi `closed`) vẽ đúng khung, và để cặp gương rõ:
  - Lông mày 5: `_1` đầu mày (gần sống mũi) → `_5` đuôi mày, cả hai bên theo giải phẫu → cặp `flip`: `longmaytrai_k` ↔ `longmayphai_k`.
  - Sống mũi 4 (side M, tự đối xứng): `_1` giữa hai mắt (gốc mũi) → `_4` chóp mũi.
  - Mắt 8 (2 khoé + 3 mí trên + 3 mí dưới), vòng kín: `_1` khoé ngoài, `_2.._4` mí trên từ ngoài vào trong, `_5` khoé trong, `_6.._8` mí dưới từ trong ra ngoài.
    Cặp `flip`: `mattrai_k` ↔ `matphai_k`. `coincide` (mí trên/dưới khi nhắm): `_2`↔`_8`, `_3`↔`_7`, `_4`↔`_6`.
  - Môi ngoài 12 (2 khoé + 5 trên + 5 dưới), vòng kín: `_1` khoé TRÁI ảnh, `_2.._6` mép trên trái→phải ảnh, `_7` khoé PHẢI ảnh, `_8.._12` mép dưới phải→trái.
    `_4` và `_10` nằm giữa (side M). Cặp `flip`: 1↔7, 2↔6, 3↔5, 8↔12, 9↔11; 4, 10 tự đối xứng.
  - Môi trong 8 (2 khoé + 3 trên + 3 dưới), vòng kín: `_1` khoé trái ảnh, `_2.._4` trên trái→phải, `_5` khoé phải, `_6.._8` dưới phải→trái. `_3`, `_7` side M.
    Cặp `flip`: 1↔5, 2↔4, 6↔8. `coincide` (môi khép): `_2`↔`_8`, `_3`↔`_7`, `_4`↔`_6`.
- Thứ tự trong nhóm môi theo ảnh (trái→phải) còn mắt/mày theo giải phẫu (ngoài/trong, đầu/đuôi): ghi rõ lý do (môi là một nhóm giữa mặt; mắt/mày tách hai nhóm
  nên đánh số theo giải phẫu để `_k` hai bên là cặp gương).

### 2.2 Các trường (config version 3)
- Giữ khung v2: `name`, `region`, `side`, `flip`, `mp_idx`, `type` (E/C), `curve` (danh sách TÊN, chứa chính điểm, E thì `null`), `line`, `anchor`, `coincide`, `tmpl`.
- **Thêm `group`** = một trong 7 tên nhóm ở 1.1 (nguồn duy nhất cho CVAT, báo cáo theo nhóm, `d_flip` theo nhóm).
- `region` giữ **vùng thô** `brow`, `nose`, `eye`, `lip` (không còn `jaw`) để `eval50` (`nme_eye`, độ mở mắt theo `coincide` vùng `eye`) và cột `reg_<region>` của
  `nme_per_face.csv` không đổi nghĩa với P5. Nếu chọn khác thì nói rõ ảnh hưởng tới cột CSV.
- `line` = tên nhóm; `lines`: `mattrai`, `matphai`, `moingoai`, `moitrong` → `closed: true`; `longmaytrai`, `longmayphai`, `songmui` → `closed: false`.
- `type`: E cho khoé mắt (`_1`, `_5`), khoé môi ngoài (`_1`, `_7`), khoé môi trong (`_1`, `_5`), đầu/đuôi mày (`_1`, `_5`), `songmui_1` và `songmui_4` (chóp);
  còn lại C với `curve` dọc đường trong nhóm: mày `[_1.._5]`; sống mũi `[_1.._4]`; mắt mí trên `[_1.._5]`, mí dưới `[_5,_6,_7,_8,_1]`; môi ngoài trên `[_1.._7]`,
  dưới `[_7,_8,..,_12,_1]`; môi trong trên `[_1.._5]`, dưới `[_5,_6,_7,_8,_1]`. Môi trong nay có khoé riêng nên **bỏ ngoại lệ `lip_inner`** (curve qua khoé ngoài)
  trong `build_config`: mọi `curve` phải nằm trong đúng `line` của điểm. Đọc README để giữ đúng nghĩa `anchor` của v2 rồi đặt cho điểm mới (ghi quy tắc).
- `side`: giữ mã `R`/`L`/`M` (để `make_label.SIDE_COLOR`, `check_config` và người đọc cũ không gãy) nhưng **nghĩa mới theo ảnh**: `R` = nửa PHẢI ảnh (`*phai`),
  `L` = nửa TRÁI ảnh (`*trai`), `M` = trên trục. Thêm trường cấp đầu `"side_convention": "image"` (kèm mô tả ngắn) và cho `build_config`/test kiểm trường này;
  `apply_map`/`check_flip`/`check_drivface` nên từ chối hoặc cảnh báo rõ khi gặp config thiếu trường này (config v2 cũ). Nếu bạn thấy đổi mã sang `phai`/`trai`/`giua`
  an toàn hơn thì được, nhưng phải cập nhật mọi chỗ đọc `side` và nói rõ lý do.
- `iod_points` = hai khoé mắt ngoài: `["mattrai_1", "matphai_1"]` (thứ tự trái ảnh, phải ảnh).
- `version: 3`, `status` bắt đầu bằng `NHAP`, `t_flip: null`, `tolerance: null`. `keep_existing` chỉ giữ số cũ khi cùng version và cùng tên điểm (nên v2 → v3 không mang
  `tmpl`/`t_flip` sang — đúng ý; có test).

## 3. Việc 2 — Chọn đỉnh MediaPipe cho 50 điểm, kiểm bằng ảnh thật

### 3.1 Gợi ý khởi đầu (theo topology Face Mesh, CHƯA KIỂM — phải xác minh bằng hình, đừng tin)
Viết theo "nửa ảnh" với ảnh không lật (mặt nhìn thẳng): nửa trái ảnh là mắt/mày phải của người.
- `longmaytrai` (đầu→đuôi): mép trên 107, 66, 105, 63, 70 hoặc mép dưới 55, 65, 52, 53, 46. `longmayphai`: 336, 296, 334, 293, 300 hoặc 285, 295, 282, 283, 276.
  v2 dùng mép trên (nằm cao hơn đường giữa mày vài px). Chọn mép trên, mép dưới hay đỉnh nào gần đường giữa nhất **bằng mắt**, ghi lý do.
- `songmui` (trên trục): ứng viên 168, 6, 197, 195, 5, 4, 1, 19. Gợi ý `_1` = 168, `_4` = 1 (hoặc 4: chọn đỉnh trùng chóp nhìn thấy, cả khi mặt nghiêng/cúi),
  `_2`, `_3` chia đều theo chiều dài sống mũi.
- `mattrai`: khoé ngoài 33, khoé trong 133; mí trên (ngoài→trong) 160, 159, 158 (hoặc 161, 159, 157); mí dưới (trong→ngoài) 153, 145, 144 (hoặc 154, 145, 163).
  `matphai`: 263, 362; trên 387, 386, 385 (hoặc 388, 386, 384); dưới 380, 374, 373 (hoặc 381, 374, 390). Mí trên/dưới cùng vị trí ngang để `coincide` có nghĩa;
  nên khớp các đỉnh EAR quen dùng (33,160,158,133,153,144 / 263,387,385,362,380,373) nếu nhìn ổn.
- `moingoai`: khoé 61 (trái ảnh) / 291; trên 5 (trái→phải) ví dụ 40, 37, **0**, 267, 270 (hoặc 39, 37, 0, 267, 269); dưới 5 (phải→trái) ví dụ 321, 314, **17**, 84, 91
  (hoặc 405, 314, 17, 84, 181). Chia đều theo cung từ khoé tới giữa.
- `moitrong`: khoé 78 / 308; trên 82, **13**, 312 (hoặc 81, 13, 311); dưới 317, **14**, 87 (hoặc 318/402, 14, 178). Kiểm khi ngáp và khi môi khép.
- Điểm side M (`songmui_*`, `moingoai_4`, `moingoai_10`, `moitrong_3`, `moitrong_7`) phải là đỉnh nằm trên trục (`perm[i] == i` của `mp_mirror478.json`); mọi điểm
  p: `perm[mp_idx(p)] == mp_idx(flip(p))` (`check_perm` của `make_config` đã kiểm — giữ).

### 3.2 Kiểm bằng mắt (bắt buộc)
- Vẽ 50 điểm có **tên ngắn/số trong nhóm** (màu theo nhóm; viền hoặc ký hiệu khác nhau cho trái/phải ảnh) lên ảnh cắt in-cabin THẬT, mỗi ô ≥ 400 px, kèm ô phóng to
  vùng mắt (cả 2 mắt) và miệng. Ít nhất 30–40 mặt phủ: F `pose=0`; `pose=1` (YawDD yaw lớn, DrivFace nhìn trái/phải); kính, kính râm; ngáp/miệng há
  (`expression=1`, `state` yawning); mắt nhắm/lim dim nếu có; tối/sáng gắt; camera Dash và Mirror; cả 4 tài xế DrivFace. Ghi `$S/ui_shots/inc3_vertices_*.jpg`; XEM từng ảnh.
- **Ảnh kiểm chiều bên** `inc3_side_*.jpg`: vài mặt thẳng và mặt quay hai phía, ghi chữ "TRÁI ẢNH"/"PHẢI ẢNH" lên ảnh, tô `mattrai`/`longmaytrai` một màu và
  `matphai`/`longmayphai` màu khác, kèm ảnh lật ngang của cùng mặt đã bỏ lật (`apply_map(..., flipped=True)`) để thấy tên vẫn đúng bên. XEM và ghi kết luận.
- `inc3_v2_vs_v3_*.jpg`: cùng mặt, 50 điểm v2 (trái) và DMS v3 (phải). XEM.
- Sửa đỉnh tới khi điểm nằm đúng ý định nghĩa; liệt kê **điểm yếu** và vì sao (lưới 3D: mép mí/môi phía xa khi mặt quay, mày bị kính râm/tóc che, môi trong khi ngáp
  hoặc khi khép, mí khi nhắm, chóp mũi khi cúi…).

### 3.3 Hoán vị gương
`mp_mirror478.json` là tính chất hình học của 478 đỉnh, **không phụ thuộc tên điểm** → **chỉ cập nhật khi cần** (ví dụ đỉnh mới chọn bị ghép gương sai). Hiện
`make_config.py --run` luôn học lại và **ghi đè** file gương: thêm tuỳ chọn (ví dụ `--learn-mirror`; mặc định dùng file có sẵn) hoặc cách tương đương, có test, để
lượt `--run` v3 không vô tình đổi file gương. Nếu bạn quyết định học lại hay sửa cặp nào, ghi lý do, số trước/sau, và chạy lại test sanity cứng của gương.

## 4. Việc 3 — Config v3, map, label CVAT (một nguồn duy nhất)

- Viết lại `SPEC`/`COINCIDE`/`CLOSED`/`_name`/`build_config` trong `make_config.py` cho DMS (tên theo nhóm thay `pNN_vùng_bên`; tuple có `group`); docstring: định nghĩa DMS,
  quy ước tên/thứ tự, quy ước bên theo ảnh, bảng đỉnh và lý do chọn, điểm yếu, trình tự lệnh cmd cho P3. Giữ `check_perm`, `estimate_flip_width`, `template`, `keep_existing`.
- `config/map_mp50.json`: giữ định dạng `kind: "vertex"` (tên mới, `flip` mới); ghi `config_version: 3` vào `meta` (hoặc tăng `version` của map nếu bạn thấy cần — nói lý do).
  `apply_map` phải báo `ValueError` rõ khi config và map lệch tên/`mp_idx`/`flip` (ví dụ config v3 + map v2 cũ), gợi ý chạy lại `make_config.py`.
- **Học lại `flip_width` và `tmpl`** trên lượt thật mới (mục 6): `flip_width` theo 50 đỉnh mới (báo thêm số 478 đỉnh và lệch y, so với số v2 trong map cũ và với 512);
  `tmpl` = trung bình dự đoán trên F `pose=0`, `|yaw| <= 12`.
- `config/face50_label.json` sinh lại bằng `make_label.py`. **Chọn phương án CVAT đơn giản nhất tương thích** `make_label`/`steps.build_xml`/`push`/`collect`/`cvat_io`/
  `eval50`/`cvat_smoke`/QC (mọi chỗ đang giả định đúng MỘT skeleton `face50` đủ 50 điểm mỗi ảnh và `low_conf` mỗi điểm). Khuyến nghị: **giữ một skeleton `face50` với
  50 sublabel mang tên mới**, nhóm thể hiện bằng trường `group` trong config, màu sublabel theo nhóm (hoặc theo bên — chọn và nói lý do), cạnh khung theo `line` = nhóm
  (nhóm không nối với nhau). Phương án 7 skeleton phải đổi mọi chỗ "đúng một skeleton", thêm shape mỗi ảnh và cách ghép nhãn: chỉ chọn nếu bạn chứng minh được lợi
  hơn. Ghi lý do so sánh vào README và báo cáo. Nếu giữ tên label `face50` thì kiểm `push` báo lỗi **rõ ràng** khi project CVAT có label cũ (tên sublabel v2) — thông
  báo nhắc P4 dựng lại project bằng `face50_label.json` mới; có test với fake CVAT.
- `t_flip`, `tolerance` trong config của repo vẫn `null`.

## 5. Việc 4 — Công cụ đo theo định nghĩa mới

- `check_flip.py`: (1) lật hai lần ≤ 0,01 px; (2) `flip` khớp gương, side M trên trục; (3) `d_flip` trên F thẳng/Tdev, chuẩn hoá IOD dự đoán (`iod_points` mới), 20 mặt F
  đầu < 3% IOD; in **theo nhóm** (7) và theo `region`; (4) đối chứng quên đổi tên > 10%; (5) **kiểm bên theo ảnh**: trên F thẳng x(`mattrai_1`) < x(`matphai_1`) và
  x(`longmaytrai_5`) < x(`longmayphai_5`) (thay p33/p39, p01/p17 — không còn viền hàm). Viết bằng `group`/`iod_points` đọc từ config, không cứng tên nếu tránh được.
- `flag_eval.py`: chế độ (a) theo nhóm và vùng, đề xuất `t_flip` = phân vị 0,85 trên Tdev (cờ ≈ 15% điểm), cờ/mặt; so với đề xuất v2 (0,0464). Cấm `--set Ttest` (giữ).
  Chế độ (b) giữ, báo theo nhóm.
- `eval50.py`: không đổi công thức; kiểm `nme_eye` dùng đủ 16 điểm mắt, độ mở mắt dùng 3 cặp `coincide` mỗi mắt; docstring cập nhật (curve trong nhóm, không còn viền).
- `check_drivface.py`: chọn điểm theo `group` thay line/tên cứng: tâm mắt = trung bình **8 điểm** mỗi mắt; mũi = `songmui_4` (chóp) — không còn chân mũi p31; báo thêm
  đỉnh 2 (chân mũi) và 4 như tham chiếu ngoài 50 điểm nếu có `pts478`; khoé miệng = `moingoai_1`/`moingoai_7`; tâm iris 468/473 tham chiếu. **Ghép bên theo vị trí
  trong ảnh**: chạy lại `side_convention` (v2: RE của DrivFace nằm nửa trái ảnh trên ảnh nhìn thẳng) rồi ghép RE/RM với nhóm `*trai`/khoé trái ảnh nếu dữ liệu xác nhận
  — không ghép theo chữ R/L. Báo trung vị/trung bình/P90 theo điểm, theo hướng nhìn, theo tài xế; **so v2 với v3** trên cùng ảnh (v2 lấy từ bản chép config/map cũ);
  ảnh `inc3_drivface_*.jpg` (XEM). Ghi chú: chỉ để tham khảo, không dùng để chỉnh đỉnh trừ lỗi thô.

## 6. Việc 5 — Chạy lại toàn bộ pipeline THẬT (616 mặt)

Trong `$S/work` (cwd = `$S/work`; gọi `python $M/tool/m28.py …`, `python $M/tool/make_config.py …`):
1. Chép config v2 hiện tại (`$M/config/*` và `$S/work/config/*`) sang `$S/inc3/v2_old/` trước khi sửa (để so v2 vs v3 ở ảnh và DrivFace).
2. `prepare --box auto --images data\frames --set F Tdev Ttest G P X D --run INC3_ALL` (cả 616 mặt; báo `no_face`, thời gian). Trình tự phụ thuộc: chạy crop+mediapipe,
   rồi `make_config.py --run INC3_ALL --manifest data\manifest.csv` (không ghi đè gương trừ khi cần, mục 3.3), chép config/map/label mới vào `$S/work/config/`, rồi
   `prepare --run INC3_ALL --force map50 flags autoqc overlays`. Lượt fallback chỉ có gói: `--images data\crops --box wflw --set X --run INC3_XCROP`.
   Ghi đúng trình tự này (lệnh cmd) vào README cho P3.
3. `flags` với `t_flip = null` (mọi cờ false), rồi lượt riêng `INC3_TFLIP` (bản sao run) với `t_flip` đề xuất qua `config\m28_config_tflip.json` **chỉ trong `$S/work`**.
4. Lưới `inc3_overlays_*.jpg` (X, Tdev, mặt khó) và `inc3_flags_tflip_*.jpg` (điểm đỏ). XEM từng ảnh; cờ đỏ có rơi vào điểm thật sự sai không.
5. `review --review auto`, `push --dry-run` (INC3_ALL và INC3_XCROP): `runs\<run>\xml\prelabel.xml` đúng 50 điểm/mặt, tên mới, đúng một skeleton, toạ độ trong ảnh;
   `eval50.py` so `prelabel.xml` với chính nó (NME = 0) và với bản nhiễu giả.
6. `check_flip.py --run INC3_ALL` và `flag_eval.py --run INC3_ALL --set Tdev`, chép số vào báo cáo (so với v2 trên INC2_ALL nếu được).

## 7. Việc 6 — Tài liệu và sổ quyết định

### 7.1 Tài liệu
- `README.md`: thay mô tả 50 điểm v2 (`p01…p50`, viền 17, `iod_points` p33/p39…) bằng định nghĩa DMS (bảng nhóm, quy ước tên/thứ tự, **quy ước bên theo ảnh** nêu rõ
  là ngược v2), bảng điểm→`mp_idx`, phương án CVAT, số mới (`flip_width`, `d_flip`, `t_flip` đề xuất, DrivFace, thời gian, số test). Số v2 chuyển vào mục lịch sử ghi
  "trước QĐ-003, không còn hiệu lực".
- `BAO-CAO-CO-LOW-CONF.md`, `HUONG-DAN-WINDOWS.md`, `nguon-du-lieu.md`: sửa mọi chỗ nhắc 50 điểm cũ, viền hàm/cằm, p-số, số test, kết quả DrivFace.
- Docstring các file `tool/` nhắc p-số hay viền hàm: cập nhật (grep `p[0-9][0-9]`, `jaw`, `viền`, `cằm`, `nửa trái ảnh`; bỏ qua `jawOpen` của `inc_ingest.py` — đó là blendshape).

### 7.2 QĐ-003 (ghi thật vào `so-quyet-dinh.md`)
- Thêm mục **QĐ-003** theo mẫu cuối file và một dòng vào bảng **Danh sách**: "Định nghĩa 50 điểm DMS (7 nhóm, không viền hàm), trái/phải theo ảnh, config v3" —
  ngày 07/10/2026, người tham gia: chủ repo (chốt), P3, P2, P4, P5 (chờ duyệt), xuất phát từ QĐ-002; bối cảnh (mục đích DMS: mắt/miệng/mày/sống mũi; viền hàm
  kém trên mặt quay và không cần cho DMS; nhầm bên R/L theo người gây khó cho người gán); phương án (giữ 50 điểm v2 — loại; DMS + khung đầu — không làm theo chủ repo;
  DMS 7 nhóm, bên theo ảnh — chọn); quyết định (bảng nhóm, quy ước tên/thứ tự/bên, `group`, `side_convention`, `iod_points`, phương án label CVAT, gương giữ/đổi);
  việc phải làm theo (@P3 duyệt đỉnh; @P2 chốt `t_flip` 12/10 với số mới; @P4 dựng lại project/label CVAT bằng `face50_label.json` mới; @P5 guideline gán tay theo DMS và
  cột báo cáo; chủ repo cập nhật bản Claude Docs và `CLAUDE.md`); trạng thái Hiệu lực.
- QĐ-002: **không sửa nội dung**; chỉ đổi trạng thái (trong mục và trong bảng) thành "Bị thay một phần bởi QĐ-003 (định nghĩa 50 điểm, config v2); chọn đỉnh trực tiếp
  vẫn hiệu lực" — đúng quy tắc đầu file.
- `e2e_ca_kho.py` bước 5 tính "QĐ tiếp theo" theo `so-quyet-dinh.md` hiện có: kiểm vẫn đúng sau khi thêm QĐ-003.

## 8. Việc 7 — Test

- Sửa mọi test hardcode tên/số v2 sang v3 **mà không xoá kiểm tra**: mỗi assert cũ phải có assert tương đương cho định nghĩa mới (ví dụ "p33 nửa trái ảnh" → "mattrai_1
  nửa trái ảnh"; "viền 17 điểm" → bỏ được nhưng thay bằng kiểm số điểm theo nhóm). Test nào phải bỏ vì đối tượng không còn (viền, chân mũi) thì liệt kê trong báo cáo.
  Test `legacy_wflw` giữ nguyên.
- Thêm test (chỉ dữ liệu giả, không ảnh thật, không mạng): config v3 hợp lệ (50 điểm; đúng 7 nhóm với số 5/5/4/8/8/12/8; thứ tự nhóm; tên `<nhóm>_<k>` liên tục; không có
  `jaw`; `region` thuộc {brow, nose, eye, lip}; `line == group`; `lines.closed` đúng; `curve` trong nhóm, chứa chính điểm; E/C đúng; `coincide` đối xứng; `side_convention == "image"`;
  side `*trai` = L, `*phai` = R, M đúng danh sách); cặp `flip` (trai_k↔phai_k; môi theo 2.1) khớp `mp_mirror478.json`; side M là điểm cố định; `iod_points`; trên mặt
  giả nhìn thẳng (x tăng sang phải ảnh) `mattrai`/`longmaytrai` có x nhỏ hơn bên phải và `apply_map(flipped=True)` giữ đúng bên; file config/map/label **trong repo**
  nhất quán với nhau và `tmpl` của nhóm trái nằm nửa trái khuôn; `make_label` với tên mới (cạnh đúng theo nhóm, nhóm không nối nhau, vòng kín cho mắt/môi); `apply_map`
  từ chối map v2 với config v3; `push` báo lỗi rõ khi project có label v2; `make_config --run` không ghi đè gương khi không yêu cầu; `check_flip` kiểm bên mới;
  `check_drivface` ghép bên theo vị trí ảnh; `eval50` với 16 điểm mắt và 3 cặp `coincide` mỗi mắt; so chuỗi tên (`moingoai_10` vs `moingoai_2`) không làm sai thứ tự.
- `python -m pytest tests -q` toàn repo **phải xanh** (báo số qua/bỏ qua so với 657 + 1). `test_no_torch.py` còn qua.
- `tests/e2e_ca_kho.py` vẫn chạy (đọc đầu file để biết tham số; `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`, `PYTHONPATH=$S/pwlib`; cần `runs/F5`, `runs/NAP_001` trong
  thư mục chạy — nếu `F5` có tên điểm v2 thì chuẩn bị lại bằng config v3 trong bản sao thư mục chạy, không phá `$S/work`). Chạy thêm `tests/e2e_cai_dat.py` nếu khả thi
  (có tên điểm cứng). Không khả thi thì nói rõ vì sao.

## 9. Tự soát trước khi báo cáo (bắt buộc)

`git status`, `git diff --stat`, đọc lại **toàn bộ diff**, rồi ghi Đạt/Chưa/Lý do cho từng mục:
1. Đúng 7 nhóm, 50 điểm, không viền hàm, không khung đầu; tên/thứ tự/`group`/`region`/`line`/E-C/`curve`/`coincide` theo quy ước đã ghi.
2. Bên theo ảnh: `side_convention`, `side`, `flip`, `iod_points`, `check_flip` (5), `check_drivface`, màu `make_label`, tài liệu — và đã kiểm bằng ảnh `inc3_side_*`.
3. Đỉnh chọn bằng mắt trên ≥ 30 mặt thật đủ loại; side M trên trục; `flip` khớp gương; gương chỉ đổi khi cần (có lý do).
4. `flip_width`, `tmpl` học lại trên INC3_ALL; `t_flip`/`tolerance` vẫn `null` trong repo; `face50_label.json` sinh lại và khớp config.
5. Phương án label CVAT có lý do; `push`/`collect`/`cvat_io`/`eval50` chạy với tên mới; lỗi rõ khi gặp project/map cũ.
6. Pipeline thật: prepare (auto + crop), map50, flags (null và t_flip đề xuất), overlays, review auto, push --dry-run; đã XEM mọi ảnh `inc3_*.jpg`.
7. README, BAO-CAO, HUONG-DAN-WINDOWS, nguon-du-lieu, docstring cập nhật; QĐ-003 + dòng bảng ghi vào `so-quyet-dinh.md`, QĐ-002 chỉ đổi trạng thái.
8. `de-tai-m28/`, `CLAUDE.md`, `tool/legacy_wflw/` không đổi; không còn import gãy (`python -c "import …"` từng file `tool/`, `python tool\<x>.py --help`).
9. pytest xanh; e2e_ca_kho chạy; không ảnh/`runs/`/`data/`/token trong `git status`; không commit; không đường dẫn `/tmp/claude-0/...` trong repo.

## 10. Báo cáo cuối (trung thực, tiếng Việt, ngắn gọn nhưng đủ)

1. Tóm tắt đã làm; **danh sách file thêm/sửa** (theo nhóm: config, tool, tests, tài liệu, sổ quyết định).
2. **Bảng điểm → `mp_idx`**: tên, nhóm, side, type, `flip`, `mp_idx`, ghi chú; quy ước tên/thứ tự; điểm đã đổi so với gợi ý ban đầu và vì sao.
3. **Điểm yếu**: điểm nào, trên loại mặt nào (quay, kính râm, ngáp, nhắm mắt, tối…), mức độ, ảnh minh hoạ.
4. Số liệu: `flip_width` (và lệch y; so v2/512), gương (giữ hay đổi, số cố định/sai số ghép), **`d_flip` trung vị theo nhóm và theo vùng** trên F thẳng và Tdev, tiêu chí
   20 mặt F, đối chứng quên đổi tên, kiểm bên theo ảnh (số mặt đạt), **`t_flip` đề xuất** (phân vị 0,85 Tdev, % điểm bị cờ, cờ/mặt; so 0,0464 của v2), `no_face`, thời gian.
5. **So DrivFace**: bảng % IOD v2 vs v3 (tâm mắt 4 điểm → 8 điểm, chóp mũi, khoé miệng, iris) theo điểm, hướng nhìn, tài xế; kết quả kiểm chiều bên DrivFace; ảnh không thấy mặt.
6. Phương án label CVAT đã chọn và lý do; mẫu `prelabel.xml` (vài dòng đầu, không có dữ liệu nhạy cảm).
7. Nhận xét từng ảnh `inc3_*.jpg` đã xem (một dòng/ảnh).
8. pytest (số qua/bỏ qua, so 657 + 1), test đã sửa/thay/bỏ (kèm lý do), e2e_ca_kho / e2e_cai_dat (chạy hay không, kết quả).
9. **Chưa thử**: Windows + Python 3.14 + cmd; CVAT thật v2.77.0 với label mới; MediaPipe trên Windows (`flip_width`); nhãn gán tay thật theo DMS (eval50/flag_eval chế độ b
   chỉ thử trên nhãn giả); lượt cũ (run v2) không đọc được với config v3 — cách xử lý.
10. **Việc cần người đồng ý**: P3 (đỉnh, quy ước tên/thứ tự, `curve`, `anchor`, đóng băng config 12/10 — lưu ý kế hoạch ghi "50 điểm không đổi từ 7/10" nên phải chốt DMS
    ngay); P2 (`t_flip` mới, cờ theo nhóm); **P4 (dựng lại project/label CVAT bằng `face50_label.json` mới, file sao lưu task, QC theo tên mới)**; P5 (guideline gán tay
    theo DMS và quy ước bên theo ảnh, cột `nme_per_face.csv`); P1 (đóng băng config v3). Kèm danh sách chỗ trong `CLAUDE.md`, bản Claude Docs và bản chụp `de-tai-m28/`
    cần sửa (định nghĩa 50 điểm, "tham khảo bố cục 98 điểm WFLW", viền hàm, quy ước bên).
