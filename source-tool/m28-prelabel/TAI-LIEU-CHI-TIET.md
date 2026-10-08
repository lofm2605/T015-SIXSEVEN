# m28-prelabel

**Giải quyết:** gán 50 điểm landmark khuôn mặt từ đầu trong CVAT rất chậm (mỗi mặt vài phút, 50 lần kéo
điểm). Đề tài M28 của đội — kế hoạch đầy đủ ở [`de-tai-m28/`](../../de-tai-m28/).

## Pain point
Gán tay 50 điểm/mặt: lâu, dễ lệch giữa người với người, dễ đổi chỗ trái/phải. Đội đo thời gian thật bằng
thí nghiệm ghép cặp 14–15/10 (gán tay so với sửa nhãn nháp, trên cùng khuôn mặt).

## Tool làm gì
Một lệnh `tool/m28.py` chạy offline trên CPU:

| Lệnh | Làm gì | Ai/máy |
|---|---|---|
| `prepare` | Cắt mặt, chạy MediaPipe (ảnh gốc + ảnh lật), đổi 478 → 50 điểm, gắn cờ `low_conf`, tự kiểm (autoqc), vẽ ảnh chồng | Tự động |
| `review` | Trang rà soát Gradio ở 127.0.0.1: mỗi mặt bấm Nhận / Gán tay / Bỏ ảnh | Người rà |
| `push` | Tạo task CVAT **mới** tên `demo-…` (mặt Nhận chia job 8 mặt; mặt Gán tay ở một job riêng cuối task, **kèm nháp 50 điểm với mọi điểm `low_conf`** để người gán kiểm kỹ từng điểm, mặt không có nháp thì lên **ảnh trống**), nhập nhãn nháp đúng một lần, xuất lại để kiểm; bản đầu, **chưa thử trên CVAT thật** | Tự động, trên CVAT của chính máy đó (hoặc nút **Đẩy lên CVAT** trên trang rà soát) |
| `collect` | Sau khi gán: xuất nhãn (chỉ đọc, không nhập) về `raw\`, báo cáo ngắn ở `outputs\`; bản đầu, **chưa thử trên CVAT thật** | Tự động |
| `all` | `prepare` → `review` (mở trang; bấm Xong thì đi tiếp) → `push`; đóng trang khi chưa bấm Xong thì dừng, gõ lại đúng lệnh (`collect` chạy riêng sau khi có người gán) | |

## Cấu trúc (theo kế hoạch)
Mọi đường dẫn trong kế hoạch tính từ thư mục này:

```
m28-prelabel/
├── tool/          m28.py, inc_ingest.py (nạp YawDD + DrivFace, chia tập, gói), check_manifest.py, m28core/ (steps, mapping, mirror, cat_mat, push, collect, cvat_io, loai_tru, dang_chay, phan_loai…), review_app.py, day_cvat.py,
│                  dot_anh.py, dot_ui.py, nap_anh.py, ca_kho.py, cai_dat.py, cai_dat_ui.py, cai_dat_thu.py, make_label.py (giao cho khách: không torch, không ảnh)
│                  make_config.py (sinh config + map + hoán vị gương), check_flip.py, flag_eval.py, eval50.py, check_drivface.py (P3/P2: kiểm và đo, xem mục "50 điểm DMS trên đỉnh MediaPipe")
├── config/        m28_config.json (50 điểm DMS, version 3: group, mp_idx, side theo ảnh), map_mp50.json (version 3, chọn đỉnh), mp_mirror478.json (hoán vị gương 478 đỉnh, không đổi ở QĐ-003), pipeline.json (không có bí mật), face50_label.json (sinh bằng make_label.py: bảy label skeleton, mỗi nhóm một, QĐ-004)
├── snippets/      đoạn code + prompt mẫu trích từ kế hoạch, CHƯA chạy thử
├── data/          manifest.csv, crops/ (ảnh cắt; có trong gói), frames/ (khung gốc; chỉ người dựng gói có)   ← KHÔNG commit
├── raw/ final/    file xuất CVAT                     ← KHÔNG commit
├── outputs/ runs/ backups/                           ← KHÔNG commit
├── requirements.txt / requirements-ui.txt
└── README.md
```

`snippets/<chung|p1…p5>/NN_<tên>.<đuôi>` — số thứ tự theo vị trí trong tab; dòng đầu mỗi file ghi trích
từ mục nào. Đây là điểm xuất phát để viết code thật, không phải code đã kiểm.

## Dữ liệu in-cabin (YawDD + DrivFace, từ 6/10/2026, QĐ-001)
Tập chính là ảnh tài xế trong xe; bộ ảnh khuôn mặt cũ đã bỏ hoàn toàn (QĐ-001 trong `so-quyet-dinh.md`). Nguồn, điều khoản, trích dẫn: [`nguon-du-lieu.md`](nguon-du-lieu.md); trong gói zip có `sources\NOTICE.txt`.
Ảnh người lái xe là dữ liệu nhạy cảm: chỉ dùng nội bộ nhóm, không commit, không phát tán, không đưa vào báo cáo/slide công khai (YawDD chỉ cho đăng ảnh của video có "Yes" trong `Table1.pdf`/`Table2.pdf`), không đưa vào chat AI ngoài phiên đã được phép.

**Sơ đồ `data\`** (không commit):
```
data\manifest.csv      616 mặt, cột bên dưới           (có trong gói)
data\crops\<file>.png   ảnh cắt 512 x 512 quanh mặt     (có trong gói)
data\frames\<nguồn>\<mã người>\<tên>.jpg   khung gốc   (CHỈ người dựng gói có; dùng với --images data\frames)
data\cache\            ứng viên, 478 điểm, khung nháp    (CHỈ người dựng gói có)
data\DOC.txt, data\sources\NOTICE.txt                     (có trong gói)
```
**Dựng gói** (P1/chủ repo; có video và ảnh gốc): `python tool\inc_ingest.py all --yawdd "D:\incab\YawDD dataset" --drivface D:\incab\DrivFace --model face_landmarker.task --out data --seed 5`.
`scan` (10-20 phút trên CPU 4 nhân của cloud: 349 video + 606 ảnh) dò mặt và ghi cache theo từng video (chạy lại bỏ qua video đã xong); `split` (vài chục giây) chia tập, ghi khung gốc, ảnh cắt, `manifest.csv`
và **tất định** (cùng cache + cùng seed ⇒ manifest giống từng byte); `pack` ghi `m28_incab_part00_meta.zip` (manifest, DOC, NOTICE) và `m28_incab_partNN_of_MM.zip` (ảnh cắt), mỗi file <= 28 MiB,
không có video/khung gốc/cache. `--limit-videos N` để thử nhanh, `--fresh` để xoá cache.

**Mã người (`subject`).** YawDD `yd_F001`, `yd_M012` (giới + số trong tên video, 3 chữ số); DrivFace `df_01`..`df_04`. Không có tên thật ở đâu cả. **Dash và Mirror cùng giới + cùng số được GỘP làm một người**:
`Readme_YawDD.pdf`, `Table1.pdf`, `Table2.pdf` không nói đó là cùng hay khác người. Xem bằng mắt (lưới ảnh Dash cạnh Mirror cùng mã, 14 cặp nữ + nam 1) và đối chiếu bảng
(ví dụ nữ 3, 4, 5: Mirror "Caucasian", Dash "Middle Eastern"; nam 4: Mirror không râu, Dash có râu) thì **gần như chắc chắn là hai người khác nhau**. Vẫn gộp vì đó là phía an toàn của việc tách người
(không bao giờ rò rỉ người giữa nhóm A và B); cái giá chỉ là số "người" trong manifest ít hơn số người thật (đa dạng người bị đếm thiếu). Muốn tách thì đổi `parse_yawdd` (ví dụ mã `yd_D...` cho Dash) và `SUBJECT_RE` trong `check_manifest.py`.

**Tách theo người.** Nhóm A = F, Tdev, Ttest (đôi một **không chung người**); nhóm B = G, P, X, D (dùng chung người giữa các tập); **không người nào ở cả A và B**.
Chia người vào nhóm bằng tìm kiếm có seed (thử `seed + t`, tối đa 500 lần; lấy 12 lần đạt mọi luật đầu tiên rồi chọn lần cân bằng nhất về giới, Dash, kính râm, loại kính; seed của lần được chọn ghi vào cột `seed`,
chạy lại cùng `--seed` khởi đầu ra đúng kết quả). Luật X và `check_manifest.py` dùng chung một hàm (`x_block_errors`). Mỗi tập trải đều camera/giới/kính/trạng thái (mềm, không cứng), tối đa 3 mặt mỗi video,
hai mặt cùng video cách nhau >= 2 giây (DrivFace: >= 3 ảnh), DrivFace chiếm khoảng 18% (4 tài xế, mỗi tập một tài xế; không để chiếm nhiều hơn), Dash khoảng 10%.
Khối X (đúng luật cũ): 10 mặt dễ (6 cờ = 0), mỗi khối 2 mặt dễ ở `seq` 01-02, 40 mặt còn lại chia vòng 1→5, 5→1; mỗi khối 1-2 mặt `pose`, 2-4 mặt `occlusion`; thêm luật mới: mỗi khối >= 2 giới, >= 2 loại camera,
>= 2 loại kính (không tính `unknown`), không hai khung cùng video; cả X: mỗi người <= 6 mặt, DrivFace <= 10 ảnh.

**Cột `manifest.csv`** (UTF-8, `/` trong đường dẫn; đúng thứ tự này):
`file, set, block, seq` · `source` (yawdd|drivface) · `camera` (dash|mirror|drivface) · `subject` · `gender` (F|M|unknown) · `glasses` (none|glasses|sunglasses|unknown) ·
`state` (normal|talking|yawning|talking_yawning|dash|unknown; Dash không có trạng thái trong tên vì một video chứa cả lái xe thường, nói và ngáp ⇒ `dash`) · `video` (đường dẫn video trong bộ gốc, hoặc tên ảnh DrivFace bỏ dấu cách) ·
`frame` (chỉ số khung; DrivFace = `imgNum`) · `t_s` (giây trong video, để kiểm khoảng cách; trống với DrivFace) · `image` (khung gốc, tương đối so với `data\frames`) · `face_idx` (= 0, mặt lớn nhất) · `x0,y0,x1,y1` (hộp mặt = khung bao 478 điểm,
toạ độ ảnh gốc, 4 chữ số thập phân) · `left, top, k` (cắt lại: `x_gốc = x_cắt / k + left`) · 6 cờ (`pose, expression, illumination, makeup, occlusion, blur`, 0/1) ·
cột đo thô (`yaw, pitch, roll` độ; `jaw_open`; `luma, contrast, bright_frac`; `lap_var`; `gaze_label, gaze_ang` của DrivFace; `pad_frac` = phần viền xám của ảnh cắt) · `seed`.
Với DrivFace, `gender` và `glasses` là `unknown`: readme chỉ nói "2 nữ, 2 nam" và "có kính/râu", không nói người nào. Loại kính YawDD lấy từ tên video, sửa hai chỗ tên sai so với bảng (`GLASSES_FIX`: Mirror nam 5 và Dash nữ 11 là kính râm).

**Sáu cờ** (heuristic, ngưỡng cố định ở đầu `inc_ingest.py`, hiệu chỉnh một lần trên dữ liệu thật 6/10/2026 rồi ghi cứng; cột đo thô để soát lại). Tỉ lệ cờ = 1 trên 616 mặt chọn :

| Cờ | Định nghĩa | Tỉ lệ thực tế (mục tiêu) |
|---|---|---|
| `pose` | YawDD: \|yaw\| >= 32 độ hoặc \|pitch\| >= 18 độ, ước lượng từ ma trận biến đổi mặt của MediaPipe (hệ camera, không trừ độ lệch camera: camera Mirror nằm lệch nên mặt nhìn thẳng đã có yaw ~ +23 độ). DrivFace: `label` 1/3 (nhìn phải/trái theo bộ), vì camera DrivFace cũng lệch trục (yaw nhìn thẳng ~ +10 độ; yaw đo được tương quan 0,90 với góc `ang` của bộ) | 17% (10-30%) |
| `expression` | `jaw_open` (blendshape jawOpen) >= 0,40: miệng mở lớn (ngáp, nói to). Không gán theo nhãn video; khi chọn mặt thì mỗi video lấy mặt miệng mở trước ở vòng đầu. Ngưỡng 0,2 cho 35% mặt: quá nhiều | 25% (15-35%) |
| `illumination` | vùng mặt tối (luma < 70), sáng gắt (luma > 170 hoặc > 8% điểm cháy sáng >= 240) hoặc tương phản thấp (độ lệch chuẩn < 28) | 12% (10-25%) |
| `makeup` | **luôn 0**: không ước lượng được trên bộ này (giữ cột cho khớp kế hoạch) | 0% (0%) |
| `occlusion` | kính râm (từ tên video + `GLASSES_FIX`). Che miệng bằng tay khi ngáp **không** dùng vì chưa có cách ước lượng ổn định. DrivFace không có thông tin kính theo từng người ⇒ 0 | 12% (10-30%) |
| `blur` | phương sai Laplacian vùng mặt (xám, chuẩn hoá về 128 x 128) < 170 (YawDD) hoặc < 75 (DrivFace; mặt nhỏ ~110 px nên Laplacian thấp hơn hẳn). Chủ yếu bắt mặt mờ/mềm của camera Dash và ảnh DrivFace | 12% (10-25%) |

Đã xem lưới ảnh có cờ = 1 và = 0 cho từng cờ (ảnh ở `ui_shots` của phiên dựng): `pose` bắt đúng mặt quay nghiêng; `expression` bắt miệng há rộng, bỏ miệng cười/khép; `illumination` bắt mặt tối, chói nắng, xám phẳng;
`occlusion` toàn kính râm; `blur` bắt ảnh mềm/mờ chuyển động. Cờ chỉ là phân loại thô để chia tập khó/dễ, không phải nhãn đúng sai.

**Định dạng ảnh cắt: giữ PNG.** Đo trên 616 ảnh cắt (ước lượng từ 40 ảnh ngẫu nhiên): PNG mức 6 **128 MiB** (mức 9: 123 MiB nhưng chậm gấp ~8 lần), JPEG q95 31 MiB, JPEG q90 22 MiB. PNG = 5 phần zip 28 MiB (< 12 phần) +
1 phần meta, không mất dữ liệu cho việc gán điểm và không phải đổi đuôi `.png` ở `check_manifest`, `ca_kho.py`, test, tài liệu. Khung gốc JPEG (YawDD: chất lượng 95; DrivFace: giữ nguyên byte gốc).

**Cách dùng với `--list`, `--set`, `--box`:** xem mục "Các lệnh" bên dưới. Người chỉ có gói (không có `data\frames`) chạy `--images data\crops --box crop` (dùng chính ảnh cắt); người dựng gói chạy `--images data\frames --box auto`
(ảnh cắt pipeline sinh ra trùng ảnh cắt của gói: sai khác điểm ảnh trung bình <= 0,0002).
## 50 điểm DMS trên đỉnh MediaPipe (giai đoạn 3, 7/10/2026; QĐ-003 thay định nghĩa 50 điểm của QĐ-002, chờ P3/P2/P4/P5 duyệt)
Phương pháp của QĐ-002 giữ nguyên: **mỗi điểm trong 50 điểm là MỘT đỉnh của lưới 478 điểm MediaPipe** (`mp_idx` trong `config\m28_config.json`), không có số học nào ở giữa, không cần đáp án. Chỉ đổi **tập điểm, tên và quy ước bên**:
chủ repo chốt định nghĩa "DMS" (Driver Monitoring System: mắt, miệng, lông mày, sống mũi), **không có viền hàm/cằm, không có cánh mũi/chân mũi, không có khung đầu**.

| Nhóm (`group`) | Số điểm | Nội dung | Vùng thô (`region`) |
|---|---|---|---|
| `longmaytrai` | 5 | lông mày bên TRÁI của ảnh | brow |
| `longmayphai` | 5 | lông mày bên PHẢI của ảnh | brow |
| `songmui` | 4 | sống mũi, từ giữa hai mắt xuống chóp mũi | nose |
| `mattrai` | 8 | mắt bên TRÁI của ảnh | eye |
| `matphai` | 8 | mắt bên PHẢI của ảnh | eye |
| `moingoai` | 12 | viền ngoài môi | lip |
| `moitrong` | 8 | viền trong môi | lip |
| **Tổng** | **50** | | |

**Quy ước bên theo BỨC ẢNH, không soi gương, NGƯỢC với version 2.** `*trai` nằm ở nửa TRÁI của ảnh (theo người xem), `*phai` ở nửa PHẢI. Version 2 gọi theo người trong ảnh (R = nửa trái ảnh). Mã `side` giữ R/L/M nhưng nghĩa mới:
**R = nửa phải ảnh (`*phai`), L = nửa trái ảnh (`*trai`), M = trên trục**; config có `"side_convention": "image"` và mọi công cụ (`apply_map`, `check_flip`, `check_drivface`, `make_label`) từ chối config thiếu trường này. Trên mặt nhìn thẳng, ảnh không lật,
`mattrai`/`longmaytrai` là mắt/mày PHẢI CỦA NGƯỜI (đỉnh 33, 133…, 107…, 70), `matphai`/`longmayphai` là mắt/mày TRÁI CỦA NGƯỜI (263, 362…, 336…, 300). Đã kiểm bằng ảnh thật: `inc3_side_*` (6 mặt thẳng/quay hai phía, ảnh gốc và ảnh lật đã bỏ lật, tên vẫn đúng bên) và `check_flip.py` mục (5) đạt 248/248 mặt thẳng F.

**Tên và thứ tự.** Tên điểm `<nhóm>_<k>`, k từ 1 không đệm số 0; thứ tự nhóm trong config và trong CVAT như bảng trên. Chú ý so chuỗi: `moingoai_10` < `moingoai_2` theo chữ cái, nên mọi chỗ cần thứ tự dùng thứ tự config (`eval50.eye_openness` đã sửa).
Trong nhóm đi theo vòng hoặc dọc đường để `make_label.edges_of` vẽ đúng khung và để cặp gương rõ: mày `_1` đầu mày (gần sống mũi) → `_5` đuôi (`longmaytrai_k` ↔ `longmayphai_k`); mũi `_1` giữa hai mắt → `_4` chóp; mắt (vòng kín) `_1` khoé ngoài, `_2.._4` mí trên từ ngoài vào, `_5` khoé trong, `_6.._8` mí dưới từ trong ra
(`coincide`: `_2`↔`_8`, `_3`↔`_7`, `_4`↔`_6`); môi ngoài (vòng kín) `_1` khoé TRÁI ảnh, `_2.._6` mép trên trái → phải, `_7` khoé phải ảnh, `_8.._12` mép dưới phải → trái (cặp 1↔7, 2↔6, 3↔5, 8↔12, 9↔11; `_4`, `_10` side M); môi trong (vòng kín) `_1` khoé trái ảnh, `_2.._4` trên, `_5` khoé phải, `_6.._8` dưới phải → trái
(cặp 1↔5, 2↔4, 6↔8; `_3`, `_7` side M; `coincide` như mắt khi môi khép). Môi đánh số theo ảnh vì là một nhóm giữa mặt; mắt và mày tách hai nhóm nên đánh số theo giải phẫu, nhờ đó `_k` hai bên luôn là cặp gương.

**Bảng điểm → `mp_idx`** (chi tiết lý do chọn và điểm yếu: docstring `tool\make_config.py`):

| Nhóm | `_1` … `_n` → đỉnh MediaPipe | side | E (điểm mốc đo điểm-điểm) |
|---|---|---|---|
| `longmaytrai` | 107, 66, 105, 63, 70 (mép trên lông mày) | L | `_1`, `_5` |
| `longmayphai` | 336, 296, 334, 293, 300 | R | `_1`, `_5` |
| `songmui` | 168, 197, 5, 1 | M | `_1` (gốc), `_4` (chóp) |
| `mattrai` | 33, 160, 159, 158, 133, 153, 145, 144 | L | `_1`, `_5` (hai khoé) |
| `matphai` | 263, 387, 386, 385, 362, 380, 374, 373 | R | `_1`, `_5` |
| `moingoai` | 61, 40, 37, 0, 267, 270, 291, 321, 314, 17, 84, 91 | `_1-3,11,12` L; `_4`,`_10` M; `_5-9` R | `_1`, `_7` (hai khoé) |
| `moitrong` | 78, 81, 13, 311, 308, 402, 14, 178 | `_1,2,8` L; `_3`,`_7` M; `_4-6` R | `_1`, `_5` |

Điểm C có `curve` = danh sách TÊN điểm dọc đường **trong cùng nhóm** (mày `[_1.._5]`, mũi `[_1.._4]`, mí trên `[_1.._5]`, mí dưới `[_5,_6,_7,_8,_1]`, môi ngoài trên `[_1.._7]` và dưới `[_7..._12,_1]`, môi trong như mắt); không còn ngoại lệ môi trong đi qua khoé môi ngoài, vì môi trong nay có khoé riêng.
`anchor` giữ nghĩa kế hoạch P3 (điểm mốc đặt trước, các điểm còn lại chia đều): hai đầu đường hở, hai khoé mắt, khoé môi ngoài/trong và điểm giữa môi. Gợi ý ban đầu của prompt giữ nguyên, chỉ môi trong chọn 81/311 và 402/178 (thay 82/312 và 317/87): hai cặp trên/dưới cùng ở 54% cung khoé → giữa nên thẳng đứng và trùng nhau khi môi khép.

**Các file (version 3):**
- `config\m28_config.json` (`version` 3): mỗi điểm có `group` (nguồn duy nhất của nhóm), `mp_idx`, `region`, `side`, `flip`, `type`, `curve`, `line` (= tên nhóm), `anchor`, `coincide`, `tmpl`; `lines` (mắt và môi `closed: true`, mày và sống mũi `false`), `iod_points` = [`mattrai_1`, `matphai_1`], `side_convention`, `side_note`.
  `tmpl` = trung bình **dự đoán** của chính ánh xạ này trên 53 mặt F thẳng (pose = 0, |yaw| ≤ 12 độ), chỉ để dựng khuôn skeleton CVAT. `t_flip` và `tolerance` vẫn `null`, `status` vẫn `NHAP`. `make_config.py` chạy lại không xoá số cũ **chỉ khi cùng version và cùng tên điểm**: v2 → v3 không mang `tmpl`/`t_flip` sang (đúng ý).
- `config\map_mp50.json` (**`version` 3**, `kind` "vertex"): `{names, points: {tên: {mp_idx, flip}}, flip_width, meta}`; `meta.config_version` = 3. Lên version 3 (cùng cấu trúc với version 2) để map của định nghĩa 50 điểm cũ bị từ chối rõ ràng: `apply_map(pts478, map, config, flipped=False, width=None)` giữ chữ ký;
  `mp_idx`/`flip` lệch map, map ridge cũ, map version 2 (tên `pNN_vùng_bên`) hoặc config thiếu `side_convention` → `ValueError` nói chạy lại `make_config.py`.
- `config\mp_mirror478.json`: hoán vị gương 478 đỉnh, tính chất hình học của lưới, **không phụ thuộc tên điểm nên KHÔNG đổi** ở QĐ-003. `make_config.py --run` mặc định chỉ **đọc** file này, kiểm `perm[mp_idx(p)] == mp_idx(flip(p))`, điểm side M nằm trên trục, và báo (không ghi) học lại trong bộ nhớ khác file ở bao nhiêu đỉnh;
  chỉ `--learn-mirror` mới học lại và ghi đè.
- `config\face50_label.json` (`make_label.py`; tên file giữ nguyên): **bảy label skeleton, mỗi nhóm một** (QĐ-004), tên label = tên nhóm, tổng đủ 50 sublabel tên mới (`longmaytrai` 5, `longmayphai` 5, `songmui` 4, `mattrai` 8, `matphai` 8, `moingoai` 12, `moitrong` 8) và 47 cạnh (mày 4+4, sống mũi 3, mắt 8+8 kín, môi ngoài 12 kín, môi trong 8 kín). Mỗi label có **màu riêng theo nhóm** (đúng bảng màu hình minh hoạ DMS của chủ repo, đặt ở chính label nên hiện ở chấm màu trong "Draw new skeleton"): `longmaytrai` #e74c3c đỏ, `longmayphai` #3498db xanh dương, `songmui` #2ecc71 xanh lá, `mattrai` #e67e22 cam, `matphai` #9b59b6 tím, `moingoai` #1abc9c xanh ngọc, `moitrong` #f1c40f vàng. Khuôn svg của mỗi label là hình của chính nhóm, co giãn vào khung 0–100.
  Mỗi mặt trong XML nháp và XML xuất có **bảy** `<skeleton>` (mỗi nhóm một, đúng điểm của nhóm). Tên sublabel vẫn là `<nhóm>_<k>` (50 tên khác nhau) nên mọi chỗ đọc điểm theo tên (collect, eval50, mapping) không đổi; chỉ phần ghép nhãn theo ảnh (`cvat_io.merged_face`) gom bảy skeleton lại thành một mặt 50 điểm, và QC đòi đúng một skeleton cho mỗi nhóm. **Cái giá:** người gán tay vẽ 7 skeleton mỗi mặt thay vì 1, nên thời gian gán tay thay đổi so với kế hoạch gốc; P5 cần biết trước khi bấm giờ ghép cặp 14–15/10 (cả hai điều kiện đều dùng cùng cách dựng nên so sánh vẫn công bằng).
  Màu theo nhóm (bản đầu của giai đoạn 3 tô theo bên của ảnh, QĐ-004 thay): hai nhóm của một cặp trái/phải (mắt cam / tím, lông mày đỏ / xanh dương) khác màu nên bên của ảnh vẫn nhìn ra được. CVAT lưu label và màu lúc TẠO project, nên **P4 phải dựng lại project/label CVAT bằng file này** (xoá project `m28` cũ rỗng để `push` tạo lại, hoặc đổi tên project trong `config\pipeline.json`); project còn label `face50` kiểu một skeleton bị `push` từ chối với thông báo nói rõ (kiểm trên CVAT giả). Task dựng từ label cũ và file sao lưu của chúng phải làm lại.

**Trình tự cho P3 (cmd, từ `source-tool\m28-prelabel`; ví dụ run `INC3_ALL`):**
```bat
rem 1. crop + MediaPipe cho các tập cần dùng (ảnh gốc + lật); dùng config hiện có (map50 và các bước sau chạy được, nhưng sẽ tính lại ở bước 4)
python tool\m28.py prepare --run INC3_ALL --images data\frames --set F Tdev Ttest G P X D --box auto
rem    (người chỉ có gói: --images data\crops --box crop --set F Tdev ...)
rem 2. ước lượng lại flip_width và tmpl từ dữ liệu thật (chỉ khi đổi bảng trong make_config.py hoặc đổi model); KHÔNG ghi đè hoán vị gương. Không có --run thì chỉ sinh lại file từ bảng và GIỮ số đã có
python tool\make_config.py --run INC3_ALL --manifest data\manifest.csv
rem    (chỉ khi thật sự phải học lại hoán vị gương: thêm --learn-mirror)
rem 3. sinh label CVAT từ config
python tool\make_label.py
rem 4. tính lại map50 và các bước sau theo config mới
python tool\m28.py prepare --run INC3_ALL --images data\frames --set F Tdev Ttest G P X D --box auto --force map50 flags autoqc overlays
rem 5. kiểm (không cần đáp án)
python tool\check_flip.py --run INC3_ALL
python tool\flag_eval.py --run INC3_ALL --set Tdev
python tool\check_drivface.py --drivface D:\incab\DrivFace --model face_landmarker.task
rem    so định nghĩa cũ với DMS trên cùng ảnh DrivFace: thêm --old-config <bản chép config v2> --old-map <bản chép map v2>
rem 6. khi nhóm đã gán tay (nhãn CVAT for images 1.1 ở raw\): NME, NME vùng, độ mở mắt, mặt hỏng; ghi cột cho P5
python tool\eval50.py --gt raw\<đáp án>.xml --pred runs\INC3_ALL\xml\prelabel.xml --condition assisted --out outputs\nme_per_face.csv
python tool\eval50.py --gt raw\<đáp án>.xml --pred raw\<nhãn gán tay>.xml --condition manual --out outputs\nme_per_face.csv --append
python tool\flag_eval.py --run INC3_ALL --gt raw\<đáp án>.xml       rem AUROC của cờ theo vùng và theo nhóm (chế độ có đáp án)
```
`nme_per_face.csv` **mất cột `reg_jaw`** (không còn viền hàm); `reg_brow`, `reg_eye`, `reg_lip`, `reg_nose` giữ nghĩa, `nme_eye` nay là trung bình đủ 16 điểm mắt và `eye_open_err` dùng 3 cặp `coincide` mỗi mắt.
`check_drivface.py` đọc `drivPoints.txt` (5 điểm mốc DrivFace) làm kiểm khách quan **chỉ để tham khảo**: tâm mắt DrivFace so với trung bình **8 điểm** mỗi mắt, mũi so với chóp `songmui_4` (và đỉnh 2, 4 là tham chiếu ngoài 50 điểm), khoé miệng so với `moingoai_1`/`moingoai_7`, **ghép bên theo vị trí trong ảnh** (RE/RM ở nửa trái ảnh → nhóm `*trai`), không theo chữ R/L.

**Số liệu của lượt chạy thật 7/10/2026** (máy Windows 11 của chủ repo, Python 3.14.7, mediapipe 1.0.1, CPU; **chỉ có gói** `data\crops` + `manifest.csv`, không có `data\frames` và không có DrivFace gốc nên `--box crop` trên ảnh cắt, **không đo được DrivFace** ở lượt này):
- `prepare --box crop --images data\crops` 616 mặt: `crop` 26,8 giây, `mediapipe` (ảnh gốc + lật) 56,9, `map50` 2,8, `flags` 0,2, `autoqc` 0,2, `overlays` 24,1 giây. Không thấy mặt: **1/616** (`F_192`, bước mediapipe); 9 mặt MediaPipe không thấy mặt trên ảnh LẬT (bị bật cờ cả 50 điểm khi `t_flip` không `null`).
- `make_config.py --run`: hoán vị gương trên 248 mặt F pose = 0 **giữ nguyên**: học lại trong bộ nhớ khác file ở **0/478 đỉnh**, 28 đỉnh trên trục, sai số ghép của file trung vị 1,76% / lớn nhất 3,57% IOD (đúng số của lượt Linux cloud: MediaPipe trên Windows cho hoán vị giống hệt).
  **`flip_width` = 513,40** (trung vị 513,22; trên cả 478 đỉnh 513,42; lệch y trung bình +0,08 px, trung vị tuyệt đối 1,25 px); so với 513,56 của 50 điểm v2 (Linux) và 512 lý thuyết (`x = p.x * width`): dùng 512 sẽ lệch hệ thống ~1,4 px (~0,8% IOD) khi bỏ lật. `tmpl` lấy trên 53 mặt F thẳng.
- `check_flip.py`: lật hai lần lệch 0 px; hoán vị là đối hợp; cặp `flip` trùng hoán vị; **d_flip** (trung vị trên mặt thẳng): 20 mặt F đầu **1,43% IOD** (tiêu chí < 3%: đạt; v2 là 1,82%), mọi mặt thẳng F (248) 1,47%, **Tdev (83) 1,60%** (v2 là 2,03%).
  Theo nhóm (trung vị, F / Tdev): `longmaytrai` 1,62 / 1,52, `longmayphai` 1,61 / 1,89, `songmui` 1,58 / 1,61, `mattrai` 1,11 / 1,12, `matphai` 1,26 / 1,25, `moingoai` 1,41 / 1,62, `moitrong` 1,36 / 1,43; theo vùng: lông mày 1,61 / 1,75, mũi 1,58 / 1,61, mắt 1,25 / 1,27, môi 1,39 / 1,58.
  Đối chứng quên đổi tên theo cặp: 52,2% IOD (> 10%: đạt). Kiểm bên theo ảnh: **248/248** mặt thẳng F có `mattrai_1` ở nửa trái hơn `matphai_1` và `longmaytrai_5` hơn `longmayphai_5`. (Hoán vị học trên F nên số F lạc quan hơn một chút; số Tdev là số trung thực.)
- `flag_eval.py --set Tdev` (chế độ không đáp án; 99 mặt có ảnh lật, 4.950 điểm): điểm số theo nhóm (trung vị / p85 / p95): `longmaytrai` 0,0177/0,0407/0,0612, `longmayphai` 0,0198/0,0456/0,0791, `songmui` 0,0163/0,0351/0,0523, `mattrai` 0,0124/0,0285/0,0462, `matphai` 0,0147/0,0430/0,0660, `moingoai` 0,0158/0,0333/0,0498, `moitrong` 0,0153/0,0311/0,0486.
  **Đề xuất `t_flip` = 0,0357** (phân vị 0,85 trên Tdev; v2 là 0,0464, không còn hiệu lực): 15,0% điểm bị cờ, 7,5 cờ/mặt; theo nhóm: `longmaytrai` 19%, `longmayphai` 25%, `songmui` 14%, `mattrai` 10%, `matphai` 19%, `moingoai` 13%, `moitrong` 11%. Chạy với 0,0357 trên cả 615 mặt: trung vị 1 cờ/mặt, p90 24; mặt `pose` = 1 trung bình 15,5 cờ, `pose` = 0 5,4 cờ.
  Cờ dồn vào mày/mắt PHẢI ảnh: phần lớn mặt Mirror của YawDD có yaw dương (quay về phía phải ảnh) nên mày/mắt phải ảnh là phía XA. `t_flip` trong repo vẫn `null` (P2 chốt 12/10). Không có AUROC (cần nhãn gán tay G/X, dùng `--gt`).
- `review --review auto` và `push --dry-run` trên `INC3_ALL` (615 mặt nhận + 1 bỏ), `INC3_XCROP` (tập X, 50 mặt) và `INC3_AUTO` (`--box auto` trên ảnh cắt, 50 mặt): `prelabel.xml` đúng 50 điểm mỗi mặt, tên mới, đúng thứ tự, đúng bảy skeleton (mỗi nhóm một; bản chạy trước QĐ-004 ghi một skeleton `face50`), toạ độ trong ảnh 512 x 512, không còn tên `pNN_…`. `eval50.py`: `prelabel.xml` so với chính nó NME 0,00%; thêm nhiễu Gauss 3 px: NME 1,59% (615 mặt), 0 mặt hỏng.
- **Điểm yếu đã biết** (xem ảnh kiểm `inc3_vertices_*`, `inc3_flags_tflip_*`): (1) mặt quay mạnh (|yaw| ≳ 30, hầu hết mặt Mirror của YawDD nghiêng 20-30 độ): mắt, mày, môi phía XA cụm lại sát sống mũi/khoé miệng và nằm trên bề mặt 3D bị che, không trên biên nhìn thấy, nên phải sửa tay nhiều; (2) lông mày và mắt sau kính râm hoặc gọng kính (MediaPipe đoán, không thấy);
  (3) mày chọn mép trên: nằm cao hơn đường giữa lông mày ~3-4% IOD (vài pixel); (4) môi trong khi ngáp rộng hoặc tay che miệng, và mắt nhắm (mí trên/dưới trùng nhau theo `coincide`); (5) mặt tối (luma < 70): điểm hợp lý nhưng chỉ là đoán; (6) chóp mũi khi đầu cúi/ngẩng nhiều hoặc nhìn nghiêng hẳn.

**Lịch sử: 50 điểm version 2 (QĐ-002, trước QĐ-003) — số cũ KHÔNG còn hiệu lực.** 50 điểm `p01…p50` gồm viền hàm 17 điểm (p01-p17), mày 5+5, mũi 5, mắt 4+4, môi ngoài 8, môi trong 2; `side` theo người trong ảnh (R = nửa trái ảnh); `iod_points` = p33, p39.
Số đo 6/10/2026 trên Linux cloud (Python 3.11): `flip_width` 513,56; d_flip 20 mặt F đầu 1,82% IOD, Tdev 2,03% (viền hàm 2,45 / 2,41, lông mày 1,59 / 1,74, mắt 1,26 / 1,32, mũi 1,58 / 1,69, môi 1,38 / 1,73); đề xuất `t_flip` 0,0464 (14,9% điểm, 7,5 cờ/mặt; cờ viền 27%);
`check_drivface.py` trên 606 ảnh DrivFace (sai số trung vị % IOD DrivFace, v2 / ridge cũ): tâm mắt R 4,6 / 4,0, tâm mắt L 8,2 / 7,0, mũi p29 (chóp) 4,8 / 5,2, mũi p31 (chân giữa) 17,0 / 17,9, khoé miệng R 8,6 / 10,5, L 4,9 / 6,3, tâm iris 4,2 (R) và 6,1 (L); mốc mũi DrivFace khớp chóp (đỉnh 1), không khớp chân mũi (đỉnh 2, thấp hơn ~15% IOD).
Điểm kém của v2: viền phía xa trong má khi mặt quay (10-50 px trên ảnh cắt 512), nên bị bỏ ở DMS.

## Cài đặt và chạy
```bat
rem Chạy trong cmd, ở thư mục source-tool\m28-prelabel (đường dẫn ngắn, ví dụ C:\m28)
py -3.14 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
curl -L -o face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```
`face_landmarker.task` đặt ở thư mục chạy lệnh (đúng mặc định `--model face_landmarker.task`); không thấy ở đó thì
`m28.py` tìm tiếp trong `tool\` (gói giao khách để model cạnh `m28.py`). File này bị `.gitignore` chặn, đừng commit.

CVAT trên máy mình: xem mục "Cài CVAT trên máy mình (cả 5 người)" trong
[`huong-dan-chung.md`](../../de-tai-m28/huong-dan-chung.md). Token và địa chỉ CVAT chỉ đặt trong biến môi
trường `CVAT_ACCESS_TOKEN`, `CVAT_URL` (không ghi giá trị vào file, code hay chat; `push --dry-run` không cần token).

### Các lệnh (cmd, từ thư mục `source-tool\m28-prelabel`)
```bat
python tool\m28.py prepare --run R1610 --list data\r_list_1610.csv --images data\frames --box auto
python tool\m28.py review  --run R1610 --review ui --reviewer P5
python tool\m28.py push    --run R1610 --images data\frames --task demo-R1610 --review-file triage_P5.csv
python tool\m28.py collect --task demo-R1610
python tool\m28.py all     --run thuP1 --list data\f5_list.csv --images data\crops --box crop --review auto --task demo-thuP1
```
- `--box crop`: dùng ảnh đã cắt sẵn 512 và lấy hộp mặt từ cột `x0,y0,x1,y1` của `data\manifest.csv` (cần `--list` hoặc `--set`), XML theo toạ độ **ảnh cắt 512**, `push` tải ảnh cắt `runs\<run>\crop\images\`.
  `--box auto` (chế độ chính cho in-cabin): tự dò mặt, XML theo toạ độ **ảnh gốc** (điểm ra ngoài ảnh kẹp vào mép), `push` tải ảnh gốc (nhớ `--images data\frames`).
- `--list`: CSV có cột `image,face_idx` (như `manifest.csv`; thiếu hai cột này thì lệnh dừng và báo); khoá nội bộ là `(image, face_idx)`. `--set F Tdev …` lọc theo cột `set` của `manifest.csv`.
- **Người trong đội chỉ có gói (ảnh cắt + manifest, không có khung gốc):** dùng `--images data\crops`. Khi `<images>\<image>` không tồn tại mà `<images>\<file>` (ví dụ `data\crops\F_001.png`) tồn tại,
  `m28.py` dùng chính ảnh cắt đó và đổi hộp mặt sang toạ độ ảnh cắt `((x0-left)*k, (y0-top)*k, (x1-left)*k, (y1-top)*k)`; `square_crop` lại ra (gần như) đúng ảnh cũ.
  Chạy với `--box crop` (XML theo ảnh cắt 512, đúng như đường chạy thử của `chay.bat` mục 3).
  `prepare` ghi chế độ vào `runs\<run>\crop\box.txt`; `push` đọc lại từ đó, không cần gõ lại `--box`.
- `--review ui` (mặc định, trang của P2 chỉ ở 127.0.0.1) | `excel` | `auto` (theo gợi ý autoqc, chỉ để chạy thử/demo).
  `--review excel`: mở `runs\<run>\autoqc\autoqc.csv` bằng Excel, điền cột `decision` (`nhan`/`gan_tay`/`bo`) và `reason`,
  lưu CSV UTF-8 thành `runs\<run>\review\triage_<reviewer>.csv`, chạy lại đúng lệnh. Chịu BOM và dấu `;` của Excel.
- `--review-file triage_P5.csv`: không có đường dẫn thì tìm ở thư mục hiện tại, rồi `runs\<run>\review\`.
- `--dry-run`: `push` chỉ ghi `runs\<run>\xml\prelabel.xml` rồi dừng (không token, không `done.txt`); `collect --dry-run` chỉ liệt kê job, không ghi file nào.
- `push --resume` / `push --cleanup --confirm-name <tên task>`, `collect` nhiều `--task`, `--skip-export`, `--reviewer`: xem mục "push và collect (CVAT)".
- `--force <bước>...`: làm lại bước (ví dụ `--force flags`). Làm lại bước đầu thì phải `--force` luôn các bước sau.
- Mỗi bước ghi vào `runs\<run>\<bước>\` (`crop`, `mediapipe`, `map50`, `flags`, `autoqc`, `overlays`, `review`, `push`)
  và để `done.txt` khi xong thật; lần sau in "bỏ qua". `runs\<run>\log.txt` ghi giờ, bước, kết quả (`xong`/`bo_qua`/`dung`/`loi`).
  `runs\<run>\no_face.csv` (cột `name,reason,step`) liệt kê mặt không dùng được.
- Mặt Gán tay lên task ở job riêng cuối task: **Gán tay có nháp** (nháp của máy, mọi điểm `low_conf=true`) hoặc **Gán tay ảnh trống** (mặt không có nháp). `runs\<run>\push\manual_list.txt` ghi mỗi dòng `<tên ảnh>`, một dấu Tab, rồi `co_nhap` hoặc `anh_trong` (có nháp trước); đọc bằng `steps.read_manual_list` (đọc được cả định dạng cũ, mỗi dòng một tên = `anh_trong`). Mặt Bỏ ghi `push\rejected.csv`.
  Mặt `no_face` mặc định là Bỏ. Hai mặt cùng một ảnh gốc ở `--box auto` bị từ chối (CVAT cấm tên ảnh trùng).

## Trang rà soát
Người rà xem nháp 50 điểm trên ảnh chồng và bấm **Nhận / Gán tay / Bỏ ảnh** cho từng mặt, trước khi nhập vào CVAT
(chấm trên ảnh chồng **tô màu theo nhóm, đúng màu label trên CVAT** (QĐ-004: bảng `GROUP_COLOR` ở `tool\m28core\mau_nhom.py`); điểm `low_conf` là chấm **to hơn, có vòng trắng**, chú giải ngay dưới ảnh. Ảnh chồng của lượt chuẩn bị TRƯỚC khi có màu nhóm tự được trang vẽ lại tạm theo màu mới, không cần chuẩn bị lại)
(sửa điểm vẫn làm trong CVAT, trang này không có công cụ kéo điểm). **Gán tay** = mặt lên CVAT ở job riêng **kèm nháp, mọi điểm đánh dấu `low_conf`**: kiểm kỹ từng điểm, giữ điểm đúng, sửa điểm sai
(mặt không có nháp thì lên ảnh trống). Phân vân Nhận/Gán tay thì chọn Nhận.
```bat
python -m pip install -r requirements-ui.txt
python tool\m28.py review --run R1610 --reviewer P5
rem hoặc chạy thẳng, không qua m28:
python tool\review_app.py runs\R1610 P5
rem chưa có lượt nào (nạp ảnh bằng kéo thả, xem "Tab Nạp ảnh"):
python tool\review_app.py --nap P5
```
- Mở địa chỉ cmd in ra (http://127.0.0.1:7860; trình duyệt tự mở). `set M28_NO_BROWSER=1` để không tự mở, `set GRADIO_SERVER_PORT=7861` để đổi cổng.
  Cổng cố định: mở bản thứ hai khi bản cũ còn chạy thì báo "Cổng 7860 bận" (tránh hai bản cùng ghi một `triage_<Pk>.csv`). **Chỉ mở một tab.**
- Lượt đã bấm Xong từ trước (có `review\done.txt`, kể cả do `--review auto`) thì `m28.py review` chỉ in "bỏ qua review": muốn rà lại thêm `--force review`.
- **Chọn lý do TRƯỚC, rồi mới bấm Gán tay / Bỏ ảnh** (bấm xong là sang mặt khác). Quên thì Hoàn tác (Z), chọn lý do, bấm lại; trang nhắc nhưng không bắt buộc.
- Đổi bộ lọc thì tự chuyển sang mặt đầu của danh sách lọc; lọc ra 0 mặt thì hiện thông báo và khoá N/G/B. Bấm lại đúng quyết định đang có thì không ghi thêm dòng.
- Server chỉ nhận Host `127.0.0.1`/`localhost` và chỉ phát file trong `overlays`, `crop\images`, `_tmp` của lượt. Ảnh chồng hỏng/thiếu thì vẽ lại tạm từ ảnh cắt (hoặc ảnh xám), trang không sập.
- Mặt đáng ngờ (autoqc `nen_gan_tay`/`can_xem`, nhiều cờ `low_conf`) lên đầu. Mặt MediaPipe không thấy mặt (`no_face.csv`) mà còn ảnh cắt
  cũng vào hàng đợi, **không có nháp**: nút Nhận bị khoá, chỉ Gán tay hoặc Bỏ; Gán tay mặt này lên CVAT là **ảnh trống**. Mặt không còn ảnh cắt không vào hàng đợi, `push` tự xếp vào Bỏ.
- Mỗi lần bấm ghi ngay một dòng vào `runs\<run>\review\triage_<người rà>.csv` (`name,decision,reason,seconds`, tên có đuôi `.png`; `seconds` là
  khoảng giữa hai lần bấm quyết định, mốc đầu là lúc trang tải) rồi tự sang mặt chưa rà kế tiếp. Bấm ảnh trong lưới để xem lại và đổi quyết định.
  Đóng ngang chừng (kể cả bị tắt đột ngột) không mất dòng nào đã bấm: gõ lại đúng lệnh thì làm tiếp, bỏ qua mặt đã rà.

| Phím | Việc | Phím | Việc |
|---|---|---|---|
| `N` | Nhận (khoá với mặt không có nháp) | `←` / `→` | Mặt trước / sau trong danh sách đang lọc |
| `G` | Gán tay (lên CVAT kèm nháp, mọi điểm `low_conf`; mặt không có nháp: ảnh trống) | `0` | Lý do "(không)" |
| `B` | Bỏ ảnh | `1`…`8` | Lý do: `LAT_GUONG`, `DON_CUC`, `LECH_VUNG`, `QUAY_CHE`, `NHIEU_MAT`, `KHONG_MAT`, `SAI_MAT`, `MO_NHO` |
| `Z` | Hoàn tác lần bấm gần nhất | | |

- **Xong** chỉ bật khi hết mặt chưa rà. Bấm Xong thì trang ghi `runs\<run>\review\done.txt` (nguyên tử), khoá việc bấm quyết định / đánh dấu Ca khó mới rồi **tự tải lại một lần**
  (server vẫn chạy) để mọi tab đọc lại trạng thái: đầu trang hiện **dải xanh** "Đã ghi xong. Bạn có thể Đẩy lên CVAT, xem Các đợt, xuất Ca khó. Xong việc bấm 'Đóng trang rà soát' để quay lại cmd."
  (không phủ màn hình, không chặn chuột/phím; tab Nạp ảnh, Các đợt, Ca khó, Họp team và khung Đẩy lên CVAT dùng được bình thường). Xong **không** tắt trang.
  Lượt mở lại đã có `done.txt` từ trước thì không khoá, không có dải xanh, không tự tải lại; quyết định mới vẫn gỡ `done.txt`. Sau Xong mà khôi phục (tab Các đợt) một ảnh chưa
  có quyết định thì lượt có lại mặt chưa rà: mở khoá, mất dải xanh, nút Xong khoá lại kèm "còn N mặt chưa rà" để rà tiếp rồi bấm Xong lại; xoá mềm ảnh sau Xong thì giữ trạng thái đã xong.
- **Đóng trang rà soát** (nút ở thanh đầu trang, thấy ở mọi tab, cả chế độ `--nap`) là chỗ duy nhất tắt trang (ngoài Ctrl+C và chuyển lượt). Bấm → hộp xác nhận (nút Huỷ có focus mặc định,
  Esc = Huỷ): đã Xong thì "Lệnh m28 trong cmd sẽ đi tiếp"; **chưa Xong còn mặt chưa rà** thì cảnh báo "chưa bấm Xong, lượt này sẽ còn mặt chưa rà" kèm số mặt, m28 sẽ dừng ở bước review (gõ lại
  đúng lệnh, các lần bấm đã lưu); chưa Xong nhưng đã rà hết thì cảnh báo m28 coi như chưa rà xong, bấm Huỷ rồi Xong trước. **Bị từ chối** khi đang chuẩn bị (prepare), đẩy lên CVAT, xoá task hoặc
  đang chuyển lượt (kiểm lại lúc xác nhận). Xác nhận thì mọi thao tác ghi (quyết định, Ca khó, Nạp ảnh, xoá/khôi phục, Đẩy lên CVAT, Xong) bị từ chối, hiện lớp phủ "Đã đóng trang rà soát",
  server tắt sau ~1 giây, `m28.py review`/`all` đi tiếp nếu có `done.txt` (cmd in "đã bấm Xong"), nếu không thì dừng. Đóng bằng Ctrl+C khi đã bấm Xong: m28 vẫn dừng nhưng báo
  đã bấm Xong, gõ lại đúng lệnh (không thêm `--force review`) là bước review được bỏ qua.
- **Hoàn tác** không xoá dòng nào: nó ghi thêm một dòng trả mặt về trạng thái trước (quyết định và lý do cũ, `seconds` để trống). Nếu trước đó mặt
  chưa rà thì dòng mới có `decision` rỗng. Ai đọc `triage_<Pk>.csv` bằng pandas hay script riêng phải **lấy dòng cuối của mỗi `name`** rồi bỏ dòng
  `decision` rỗng (`read_triage` của `push` làm đúng như vậy). Ngăn hoàn tác chỉ sống trong một phiên; mở lại muốn đổi thì bấm ảnh rồi chọn lại.
- **Chỉ chạy ở 127.0.0.1** (`launch(server_name="127.0.0.1", share=False)`): không `share=True`, không tunnel, không Colab/Kaggle/Spaces (trang tự thoát),
  không gọi mạng. Trên trang có ảnh mặt: không chụp màn hình dán vào chat AI. Trang tự thêm `localhost,127.0.0.1` vào `NO_PROXY` nên máy có proxy công ty
  không phải gõ `set NO_PROXY`.
- Excel đang mở `triage_<Pk>.csv` thì Windows khoá file: trang báo "Không ghi được ... đóng Excel rồi bấm lại" và giữ nguyên mặt, đóng Excel rồi bấm lại.
- Không dùng được trang (không cài được Gradio, trình duyệt lỗi): `--review excel` (xem mục Các lệnh).
- Ảnh tạm và ảnh nhỏ nằm trong `runs\<run>\_tmp`; dọn bằng `rmdir /s /q runs\R1610\_tmp`.

### Tab Nạp ảnh (kéo thả ảnh, không gõ lệnh prepare)
Trang có hai tab: **Rà soát** (như trên) và **Nạp ảnh**. Dùng khi có ảnh mới (ảnh khách, ảnh thử) mà chưa có lượt `runs\<lượt>`:
```bat
python tool\review_app.py --nap P2
rem hoặc từ trang đang rà dở: bấm tab Nạp ảnh
```
- Cách dùng: kéo thả nhiều ảnh vào vùng thả (hoặc bấm để chọn) → xem lưới ảnh nhỏ và danh sách ảnh bị loại → (tuỳ chọn) gõ tên lượt, để trống thì tự đặt
  `NAP_001`, `NAP_002`… → bấm một trong hai nút (giống **Submit & Open / Submit & Continue** khi tạo task trong CVAT): **Nạp & Mở** (chuẩn bị xong thì trang **tự mở rà soát** lượt này, như bấm Rà lượt này) hoặc **Nạp & Tiếp tục** (chuẩn bị xong vẫn ở lại tab Nạp ảnh để nạp thêm đợt khác). Trang chạy `python tool\m28.py prepare --run <lượt> --images runs\<lượt>\inbox --box auto` bằng tiến trình con,
  hiện bước (1–6/6), thanh tiến độ và log. **Huỷ** dừng tiến trình; **Thử lại** chạy lại đúng lệnh trên lượt đó (bước đã xong được bỏ qua).
  Xong thì hiện tóm tắt (mặt dùng được, không thấy mặt, vào hàng đợi rà, lệnh `push` gợi ý) và nút **Rà lượt này**: trang tự chuyển sang rà lượt mới. **Nạp & Mở** làm việc đó tự động khi xong; lỗi, bị huỷ hoặc không có mặt nào để rà thì không tự mở (thông báo hiện ở đầu tab, bấm Rà lượt này tay khi cần).
- Mỗi lần nạp là **một lượt mới**; lượt đang rà dở không bị đụng tới. Ảnh chép nguyên byte vào `runs\<lượt>\inbox\` với tên đã làm sạch (bỏ dấu, ký tự lạ thành `_`,
  tên trùng, không phân biệt hoa thường, thêm `_2`, `_3`…; đuôi theo định dạng thật: `.jpg` hoặc `.png`). Bảng tên gốc → tên mới ở `runs\<lượt>\nap_ten_goc.csv`,
  log của tiến trình con ở `runs\<lượt>\nap_log.txt` (còn sau lỗi/huỷ). Trang chỉ ghi dưới `runs\`.
- Giới hạn: đuôi `.jpg/.jpeg/.png` **và** phải mở được như ảnh JPEG/PNG (không tin đuôi: file chữ đổi tên `.jpg` bị loại); tối đa 25 MB mỗi ảnh, 200 ảnh mỗi lần,
  cạnh ngắn từ 32 px, tối đa 50 triệu điểm ảnh; ảnh trùng nội dung (sha256) trong cùng lần bị loại. Mỗi ảnh bị loại có lý do ghi trên trang.
- `--box auto` chỉ lấy **mặt lớn nhất** của mỗi ảnh; cần mặt khác thì Gán tay trong CVAT. Mặt không có ảnh cắt: `push` tự xếp Bỏ; mặt MediaPipe không thấy: vẫn vào hàng đợi nhưng không có nháp.
- Cần `face_landmarker.task` (ở thư mục chạy lệnh hoặc `tool\`), `config\m28_config.json`, `config\map_mp50.json`, và đã cài mediapipe, opencv. Thiếu thì khung đỏ ở đầu tab
  nói rõ cách sửa và nút Bắt đầu bị khoá. Chạy trang từ thư mục có `runs\` (tab Nạp ảnh báo lỗi nếu thư mục lượt không nằm trong một thư mục tên `runs`).
- **Chuyển lượt**: bấm Rà lượt này thì trang dựng lại và mở lại trên **cùng cổng, cùng tiến trình** (mất kết nối 1–3 giây, trình duyệt tự tải lại; cmd in lượt cũ còn bao nhiêu mặt chưa rà và lệnh mở lại,
  ví dụ `python tool\review_app.py runs\F5 P2`). Các lần bấm của lượt cũ đã ghi từng dòng nên không mất. Nếu bạn mở trang bằng `m28.py review --run <cũ>` thì lệnh đó sẽ báo chưa bấm Xong
  cho lượt cũ: gõ lại sau. Bấm **Đóng trang rà soát** khi đang chuẩn bị bị từ chối (đóng sẽ giết prepare); Xong thì không bị từ chối vì không tắt gì. File tạm/ảnh nhỏ sau khi chuyển vẫn nằm ở `_tmp` của lượt đầu tiên
  (Gradio chỉ đọc `GRADIO_TEMP_DIR` lúc import); vẫn dưới `runs\`, ngoài git.
- `--nap`: chưa có lượt nào thì chạy `python tool\review_app.py --nap <người rà>` (tạo `runs\` nếu chưa có, tab Rà soát chỉ ghi "Chưa có lượt nào").
- **Ảnh mặt người thật chỉ xử lý trên máy này (127.0.0.1)**: không đưa ảnh khách hàng, ảnh chụp màn hình trang, file kết quả vào chat AI hay dịch vụ ngoài. Server vẫn chỉ phát file trong
  `overlays`, `crop\images`, `_tmp` của lượt đang rà (không bao giờ `inbox\` hay cả `runs\`).

### Nút "Đẩy lên CVAT" (tab Rà soát)
Đẩy xong, thẻ kết quả có nút xanh dương **Mở task trên CVAT** (mở tab mới, đúng trang task vừa tạo; chỉ hiện khi địa chỉ là http/https và không chứa tên đăng nhập), tab Các đợt cũng có nút đó cho đợt đã đẩy.
Dưới nút **Xong** có khung **Đẩy lên CVAT**: bấm là đẩy lượt đang rà lên CVAT mà không gõ lệnh. Trang **không gọi mạng**: nó chạy tiến trình con
`python -u tool\m28.py push --run <lượt> --reviewer <người rà> --task demo-<lượt>` (thư mục chạy = thư mục chứa `runs\`), tiến trình con mới gọi CVAT.
- **Khi nào bật:** hết mặt chưa rà (đã trừ ảnh xoá mềm), có ít nhất một mặt Nhận hoặc Gán tay, chưa đẩy xong, ảnh gốc còn đủ, link/token CVAT đủ (tab Cài đặt hoặc biến môi trường) và không có việc nào khác chạy
  cho lượt. Còn mặt chưa rà: nút khoá kèm "Còn N mặt chưa rà". Không cần bấm Xong trước khi đẩy; bấm Xong rồi đẩy vẫn được (Xong không tắt trang). Đang đẩy thì nút Đóng trang rà soát bị từ chối.
- **Link và token CVAT:** lấy từ tab **Cài đặt** (cách chính: nhập link `http://localhost:8080` và token, bấm Lưu) hoặc biến môi trường `CVAT_URL` / `CVAT_ACCESS_TOKEN` (tuỳ chọn `CVAT_ORG`), đọc lại mỗi lần vẽ;
  tiến trình con nhận chúng qua môi trường của nó. Thiếu thì nút khoá và trang hiện hướng dẫn (mở tab Cài đặt; hoặc đóng trang, trong **cùng cửa sổ cmd** gõ `set CVAT_URL=http://localhost:8080` và `set CVAT_ACCESS_TOKEN=<token của bạn>` rồi mở lại).
  **Khung Đẩy lên CVAT không có ô nhập nào** (ô token duy nhất nằm ở tab Cài đặt); token không bao giờ hiện trên trang, không đi qua đối số dòng lệnh, và bị lọc khỏi log (`***`).
- **Hộp xác nhận** (nút **Huỷ** là mặc định có focus, **Esc** = Huỷ): tên task `demo-<lượt>`, số Nhận / Gán tay (tách **có nháp** và **ảnh trống**) / Bỏ (tính bằng đúng `m28core.phan_loai.classify` mà `steps.push` dùng, với `mp50.json` thật và tên 50 điểm của `config\m28_config.json`),
  số job dự kiến, địa chỉ CVAT, và câu "chỉ tạo task MỚI, không đụng task `m28-`". Hộp mở thì phím N/G/B/Z/←/→/0–8 không tác dụng.
- **Đang chạy:** thanh tiến độ theo pha (kiểm tra, kết nối, project, tải ảnh, nhập nhãn, xuất kiểm), log (đã lọc token), thời gian, nút **Huỷ** (`terminate`, 5 giây, `kill`; sau huỷ
  trang đọc `push.json` và nói task đã tạo dở hay chưa, kèm lệnh `--resume` / `--cleanup`). Rà vẫn bấm được trong lúc đẩy (sự kiện riêng `push`, `push_tick`, `push_huy`);
  **Xong** bị từ chối khi đang đẩy.
- **Xong:** thẻ kết quả có tên task, id, link `CVAT_URL/tasks/<id>` (mở tab mới, `rel="noopener"`), số job (Nhận / Gán tay), số Gán tay có nháp / ảnh trống, kết quả kiểm `check.zip` (cả mặt Nhận lẫn mặt Gán tay có nháp). **Lỗi:** nguyên nhân tiếng Việt (dòng cuối của tiến trình
  con) và bước tiếp theo; traceback không hiện trên trang (vẫn nằm trong `runs\<lượt>\push_log.txt`).
- Vì chạy qua `m28.py push` nên `runs\<lượt>\push\done.txt` được ghi: sau đó `m28.py all`/`push` gõ ở cmd in "bỏ qua push". Xoá task rồi (xem dưới) thì `done.txt` bị gỡ và đẩy lại được.

**"Gán tay" trên trang rà soát khác điều kiện "gán tay" của thí nghiệm.** Nút Gán tay chỉ ảnh hưởng task `demo-…` do `m28.py push` tạo: mặt lên job riêng kèm nháp, mọi điểm `low_conf`. Thí nghiệm bấm giờ 14–15/10 dùng task `m28-manual` (không nháp) và `m28-assisted` khôi phục từ `backups\`, không đi qua nút này nên không đổi. Không dùng số đo trên task `demo-…` làm mốc "gán tay" của thí nghiệm.
(Đã kiểm trong code: `push.check_prefix`/`check_task_name` chỉ cho task `demo-…` (`cvat_io.SAFE_PREFIX`); `collect` không gọi CVAT với task không `demo-`; `tool\` không có `build_backups.py` hay `tasks.json`, đường dựng task thí nghiệm là của P4, từ `backups\`.)

### Ca khó và họp team
Ba phần cùng nằm trong trang rà soát (chỉ 127.0.0.1), mã trong `tool/ca_kho.py`:
- **Đánh dấu (tab Rà soát):** phím **K** hoặc nút **Ca khó (K)** mở panel cho mặt đang xem: chọn loại, điểm liên quan (không bắt buộc), ghi chú (tối đa 500 ký tự), **Lưu**.
  Ghi vào `runs/<lượt>/ca_kho.csv` (UTF-8 có BOM; cột `luot,anh,nguoi,loai,diem,ghi_chu,tao_luc,sua_luc,quyet_dinh_ra`; khoá `(nguoi, anh)`: bấm K lần nữa là sửa).
  Không đụng `triage_<người>.csv`, `done.txt`, hàng đợi hay Hoàn tác. Gõ n/g/k trong ô ghi chú không kích hoạt phím tắt. Có **Bỏ đánh dấu** (bấm hai lần).
- **Tab Ca khó (thành viên):** xem/sửa/xoá ca của mình ở mọi lượt, rồi **Xuất gói họp** ra `outputs/ca_kho/ca_kho_<người>_<ddmm>.zip` (tải về qua trang).
  Gói chỉ có `manifest.json`, `ca_kho.csv`, `anh/<lượt>__<tên>.jpg` (ảnh chồng, cạnh dài ≤ 480 px, JPEG q72, không EXIF). Ảnh chỉ kèm cho lượt có nguồn là một bộ dữ liệu đã biết
  (không có `inbox/` và mọi mặt có trong `data/manifest.csv`; nguồn = cột `source` của manifest: `yawdd`, `drivface` hoặc `yawdd+drivface`, manifest không có cột đó thì `khong_ro`); lượt không rõ nguồn (có thể là ảnh khách hàng) mặc định chỉ xuất ca, không kèm ảnh. Tối đa 500 ca và 20 MB mỗi gói.
- **Tab Họp team (người tổ chức, ví dụ P5):** `python tool\review_app.py --nap P5`. Tạo phiên (`outputs/ca_kho/hop_<ddmm>/`, lưu `hop.json` nên mở lại làm tiếp được),
  kéo thả nhiều gói, xem bảng kết quả từng gói (nhập được / lỗi kèm lý do / đã nhập rồi). Gói không bao giờ được giải nén ra đĩa: chỉ đọc mục `manifest.json`, `ca_kho.csv`, `anh/*.jpg`,
  giới hạn byte thật khi giải nén (chống zip bomb), ảnh mã hoá lại. Họp trên lưới ảnh (nhóm theo loại / người / trạng thái, lọc, tìm chữ), đặt trạng thái Mở / Đang bàn / Đã chốt,
  quyết định, người phụ trách, loại backlog, mục guideline; **Trình chiếu** (← → đổi ca, Esc thoát). Cùng một mặt của bộ dữ liệu (cùng tên ảnh, mọi nguồn đã biết) do nhiều người đánh dấu thì ghi chú hiện cạnh nhau.
  **Xuất biên bản**: `bien_ban_<ddmm>.md` (điền sẵn mục P-NNN, QĐ-NNN và dòng bảng Danh sách đúng mẫu `problem-backlog.md`, `so-quyet-dinh.md`; số tiếp theo đọc từ hai file đó) và `tong_hop_<ddmm>.csv`.
  **Code không bao giờ ghi vào hai file đó**: người tổ chức tự chép các khối vào rồi commit.
- Mã loại: SWAP, MIRROR, COLLAPSE, MISPLACED, OCC_FLAG (lỗi đặt điểm, như xem chéo 16/10), RULE, GL_CHUA_NOI, GL_MO_HO, GL_MAU_THUAN, CONG_CU, KHAC.
  Lỗi đặt điểm mặc định không vào backlog (người tổ chức đổi được).
- Gói chứa ảnh mặt người (tài xế, dữ liệu nhạy cảm; YawDD/DrivFace chỉ cho dùng học tập, nghiên cứu): chỉ gửi trong đội, không đăng công khai, không giao bên thứ ba, không commit (`outputs/` và `*.zip` đã bị `.gitignore` chặn).

## Tab Cài đặt (CVAT, người rà, đường dẫn, cờ low_conf)
Tab cuối của trang rà soát (`tool\cai_dat.py` logic, `tool\cai_dat_ui.py` giao diện, `tool\cai_dat_thu.py` tiến trình con thử kết nối). Năm khung:
- **CVAT:** `Link CVAT`, `Token CVAT` (ô password, rỗng sau khi Lưu, chỉ còn dạng `••••3456`; nút **Hiện / ẩn** đổi kiểu ô ngay ở trình duyệt), `Tổ chức` (tuỳ chọn),
  hộp **Nhớ trên máy này** (TẮT mặc định), nút **Lưu**, **Thử kết nối CVAT**, **Quên token** (có hộp xác nhận), **Chạy kiểm tra nhanh CVAT** (tạo rồi xoá task `demo-smoke` giả; xem mục "Kiểm tra nhanh CVAT"). Dòng trạng thái: `○ Chưa có link/token`, `○ Chưa thử`,
  `● Đã kết nối (thử lúc …)`, `● Lỗi: <nguyên nhân>`, kèm nguồn (từ biến môi trường / đã lưu trên máy / nhập trong phiên này). Lưu bị từ chối khi đang đẩy hay xoá task
  (tiến trình con đang dùng token hiện tại), khi đang chạy kiểm tra nhanh và khi trang đang đóng. Lưu xong, khung Đẩy lên CVAT và tab Các đợt thấy giá trị mới ngay (nút Đẩy mở khoá, không cần mở lại cmd).
- **Người rà:** lưu tên mặc định. Lượt đang mở vẫn ghi `triage_<tên cũ>.csv` (phần rà dở nằm ở file đó); tên mới dùng **từ lượt kế tiếp** (Rà lượt này, chuyển đợt).
- **Đường dẫn:** thư mục ảnh (ví dụ `data\frames`) và file `face_landmarker.task`, mỗi ô có **Kiểm** (tồn tại, đọc được, đếm ảnh có giới hạn 5.000 file / 2 giây, 3 tên mẫu; model: kích thước, đuôi `.task`, là zip) và **Lưu**.
  Tab Nạp ảnh dùng model đã cài (`--model`); thư mục ảnh được thêm `--images` vào lệnh `push` của lượt chạy bằng lệnh khi ảnh gốc không còn ở đường dẫn cũ (chỉ khi cần).
- **Cờ low_conf:** xem và đặt `t_flip` trong `config\m28_config.json` (chỉ đổi khoá này, giữ nguyên mọi trường khác và định dạng), luôn qua hộp xác nhận (Huỷ mặc định, Esc = Huỷ); từ chối khi có việc đang chạy;
  khi `status` đã đóng băng (không còn bắt đầu bằng `NHAP`) phải tick thêm ô xác nhận. Sau khi ghi liệt kê các lượt đã có `flags.json` (tính theo ngưỡng cũ; tính lại bằng `prepare --force flags autoqc overlays`).
- **Pipeline:** `config\pipeline.json`, chỉ đọc.

**Nơi lưu (ngoài repo):** Windows `%APPDATA%\m28\` (thiếu thì `%USERPROFILE%\AppData\Roaming\m28`), Linux/macOS `$XDG_CONFIG_HOME/m28/` hoặc `~/.config/m28/`; biến `M28_CONFIG_DIR` ghi đè (chỉ cho test/máy đặc biệt).
Thư mục nằm trong repo bị từ chối. `cvat.json` (link, token, tổ chức) chỉ có khi bật Nhớ; `cai_dat.json` (người rà, đường dẫn) không có bí mật. Ghi nguyên tử (file tạm `O_EXCL` 0600, fsync, `os.replace`);
Linux/macOS thư mục 0700 và file 0600 (kiểm lại bằng `stat`). **Windows không có 0600 thật**: file chỉ được bảo vệ bởi quyền hồ sơ người dùng; **không dùng keyring/DPAPI**. File hỏng không làm vỡ trang
(báo "hỏng", không hiện nội dung; bấm Quên token hoặc Lưu lại).

**Ưu tiên nguồn (quyết định tự chốt, xem báo cáo):** giá trị vừa Lưu trong phiên > biến môi trường `CVAT_URL` + `CVAT_ACCESS_TOKEN` (khi có cả hai) > file đã lưu. Biến môi trường của cmd không đổi; Lưu chỉ đổi giá trị trang này dùng.
Quên token xoá file và giá trị đã nhập; nếu còn biến môi trường thì nguồn quay về đó và trang nói rõ ("đóng cmd hoặc `set CVAT_ACCESS_TOKEN=`").
**Thử kết nối** chạy bằng tiến trình con (trang vẫn không gọi mạng; token qua môi trường của nó, không qua đối số, hết 20 giây thì kill): tiền kiểm `GET <link>/api/server/about` không mang token và **không theo redirect**
(3xx sang địa chỉ khác thì dừng, "không gửi token"), rồi `make_client`, so bản server với `cvat_version`, `users.retrieve_current_user()`, tìm project (chỉ đọc). Lệnh cmd `m28.py push/collect` vẫn cần `set CVAT_URL` / `set CVAT_ACCESS_TOKEN` (tool không đọc `cvat.json`).
**Chưa thử:** CVAT thật (chỉ CVAT giả; `users.retrieve_current_user` chỉ đối chiếu chữ ký), Windows/cmd/Python 3.14, `%APPDATA%` thật, HTTPS tự ký, máy sau proxy công ty.

## Tab Các đợt (quản lý đợt, xoá mềm ảnh)
Tab thứ ba của trang. Mỗi **đợt** là một thư mục lượt `runs\<lượt>` (tên do bạn đặt khi nạp, ví dụ `Khoi`, `Nam`, `Cuong`, hoặc `NAP_001`); thư mục bắt đầu bằng `_` (`_nap`, `_trash`) không phải đợt.
- **Thẻ đợt** (mới nhất lên đầu): tên, ngày nạp, **ghi chú** (ô `Ghi chú` ở tab Nạp ảnh, tối đa 500 ký tự, ghi vào `runs\<lượt>\dot.json` cùng người nạp và số ảnh; lượt cũ không có `dot.json` thì lấy ngày từ `log.txt`/thư mục),
  số ảnh, số Nhận / Gán tay / Bỏ / Chưa rà theo `triage_<người rà hiện tại>.csv` (dòng cuối mỗi tên, đã trừ ảnh xoá mềm; có file của người khác thì ghi "có kết quả của P…"), số ảnh trong thùng rác,
  và trạng thái: Đang chuẩn bị / Chưa prepare xong / Chưa rà / Đang rà / Đã Xong / Đang đẩy / Đã đẩy CVAT: `<task>` (id) / Đẩy dở: `<trạng thái push.json>`.
  Nút **Rà đợt này** chuyển trang sang đợt đó (cùng cơ chế, cùng cổng như "Rà lượt này"; khoá với đợt đang mở, đợt chưa có `flags.json`, hoặc khi đang có việc chạy). Đợt **Đã Xong** chưa đẩy có nút **Đẩy lên CVAT**
  (cùng hộp xác nhận và `PushJob` ở trên). Có nút **Làm mới**; danh sách tự làm mới khi chọn tab (không quét lại mỗi giây).
- **Lưới ảnh** (bấm tên đợt hoặc **Xem ảnh**, 24 ảnh mỗi trang): ảnh gốc trong `inbox\` (đợt nạp) hoặc ảnh cắt (đợt không có `inbox\`), kèm tên, tên gốc, trạng thái (Nhận / Gán tay / Bỏ / Chưa rà / Không thấy mặt / Không dùng được).
  Ảnh nhỏ (~160 px, JPEG, xoay EXIF) được tạo bằng PIL và **nhúng data URI** vào HTML: không mở thêm `allowed_paths`, không bao giờ phát file gốc trong `inbox\`.
- **Xoá ảnh (xoá mềm):** rê chuột (hoặc Tab tới) vào ảnh thì hiện nút thùng rác (màn cảm ứng luôn hiện); bấm → hộp xác nhận (ảnh, tên gốc, đợt, quyết định hiện tại, hậu quả; **Huỷ** mặc định, **Esc** = Huỷ, nút xoá đỏ).
  Đợt đã đẩy CVAT thì hộp thêm khung đỏ: **"Xoá ở đây KHÔNG xoá ảnh trong task <tên> trên CVAT"**.
  Cách làm: tên mặt ghi vào `runs\<lượt>\excluded.txt` **trước** (mỗi dòng một tên không đuôi, dòng `#` là chú thích), rồi `inbox\<file>`, `crop\images\<tên>.png`, `overlays\<tên>.png` chuyển (`os.replace`) vào
  `runs\<lượt>\_trash\<thời điểm>_<tên>\files\…` kèm `manifest.json` (tên, đường dẫn gốc → thùng rác, thời điểm, người rà, quyết định lúc xoá, đã đẩy CVAT chưa); lỗi giữa chừng thì chuyển ngược.
  **Không file kết quả nào bị sửa** (`meta.json`, `flags.json`, `mp50.json`, `pred478.json`, `autoqc.csv`, `no_face.csv`, `triage_*.csv`): loại trừ chỉ là bộ lọc lúc đọc, và **mọi nơi đọc mặt của lượt đều trừ tập này**
  (`steps._queue`, `review`, `push`, `load_items`, các bước `--force`, `review_app._load`/`Store`, `nap_anh.read_prepare_result`, thẻ đợt). `push` ghi mặt đã xoá vào `push\rejected.csv` với lý do `da_xoa` (không tải lên).
  Đợt đang rà: ảnh bỏ khỏi hàng đợi ngay (`Store.exclude`), tab Rà soát vẽ lại khi chọn lại tab, mặt đang xem bị xoá thì nhảy sang mặt chưa rà kế; không xoá được khi đợt chỉ còn một mặt.
- **Thùng rác của đợt:** danh sách ảnh đã xoá, nút **Khôi phục** (file về đúng chỗ cũ, gỡ tên khỏi `excluded.txt`; đích đã có file thì từ chối, không chuyển gì; ảnh chưa có quyết định thì `review\done.txt` bị xoá vì lượt lại có mặt chưa rà)
  và **Dọn thùng rác…** (xoá **vĩnh viễn**, chỉ `rmtree` `runs\<lượt>\_trash`, qua hộp xác nhận nói rõ không khôi phục được; tên vẫn nằm trong `excluded.txt`).
- **Xoá cả đợt:** phải gõ lại đúng tên đợt (phân biệt hoa thường; nút chỉ bật khi khớp, server kiểm lại); đợt chuyển vào `runs\_trash\<lượt>__<YYYYmmdd-HHMMSS>` (khôi phục được ở khu **Đợt đã xoá** nếu tên chưa bị dùng lại;
  **Xoá vĩnh viễn…** cũng qua hộp xác nhận). Tên `NAP_xxx` của đợt đã xoá không bị tự đặt lại. Đợt đã đẩy CVAT thì hộp cảnh báo xoá đợt **không** xoá task trên CVAT.
- **Chặn:** xoá ảnh/đợt/khôi phục/dọn khi lượt đang prepare hoặc đang đẩy (file khoá `runs\<lượt>\.dang_chay` do `PrepareJob`/`PushJob`/`DeleteTaskJob` ghi, kể cả khi một trang khác chạy); không xoá cả đợt đang mở ở tab Rà soát.
- **An toàn đường dẫn:** tên đợt từ trình duyệt phải khớp `RUN_RE` và nằm trong danh sách đợt do server tính; tên ảnh phải là phần tử của danh sách ảnh của đợt đó do server tính (không bao giờ ghép đường dẫn từ chuỗi của trình duyệt);
  mọi nguồn/đích kiểm `realpath` + `commonpath` (liên kết tượng trưng trỏ ra ngoài bị từ chối). Mỗi hộp xác nhận có **mã ngẫu nhiên dùng một lần** (hết hạn 10 phút): bấm xác nhận của hộp cũ hoặc hộp đã bị thay không xoá gì.
- **Xoá task trên CVAT** (nút ở khu "CVAT" của đợt đã đẩy hoặc đẩy dở): xem mục dưới.

## push và collect (CVAT)
Bản đầu của P4, viết theo kế hoạch (`de-tai-m28/p4-cvat.md`, "Phần mới: push và collect"), thử bằng một `cvat_sdk` GIẢ và đối chiếu chữ ký với cvat-sdk 2.77.0 thật; **chưa thử trên server CVAT thật** (xem "Rủi ro").
```bat
python -m pip install cvat-sdk==2.77.0
python tool\make_label.py                          rem sinh config\face50_label.json từ config\m28_config.json (chạy lại ra cùng byte)
set CVAT_URL=http://localhost:8080
set CVAT_ACCESS_TOKEN=<token của bạn, không dán vào file hay chat>
rem (lệnh cmd này vẫn cần set như trên: tool\m28.py không đọc cvat.json của tab Cài đặt)
python tool\m28.py push    --run Khoi --reviewer P2 --task demo-Khoi
python tool\m28.py push    --run Khoi --resume                         rem lần trước dừng sau khi đã tạo task: làm nốt trên ĐÚNG task đó
python tool\m28.py push    --run Khoi --cleanup --confirm-name demo-Khoi   rem xoá ĐÚNG task trong push.json trên CVAT (không hoàn tác)
python tool\m28.py collect --task demo-Khoi demo-Nam --reviewer P4      rem xuất nhãn về raw\ rồi lập outputs\collect_demo-Khoi.md
python tool\m28.py collect --task m28-manual --skip-export              rem chỉ đọc raw\, không gọi CVAT
python tool\m28.py collect --task demo-Khoi --dry-run                   rem chỉ liệt kê job, không ghi file
```
- **`config\pipeline.json`**: `project` (m28), `prefix` (demo-), `cvat_version` (2.77.0; bản server khác thì `push`/`collect` dừng và nói cách sửa; ở công ty đổi cho khớp server và cài `cvat-sdk` cùng bản), `job_size` (8).
- **`push`** (theo thứ tự; sai một điều thì dừng TRƯỚC khi kết nối): prefix phải bắt đầu `demo-` và tên task bắt đầu prefix (task `m28-…` không bao giờ bị tạo hay đụng; `--task m28-gold` và prefix `m28-` bị từ chối); có `CVAT_URL` (`http://`/`https://`, không chứa
  `user:pass@`) và token; có `config\face50_label.json`, XML và mọi ảnh; tên file ảnh không trùng. Rồi: chống đẩy hai lần bằng `runs\<lượt>\push.json` → kết nối (`make_client(url, access_token=…)`, `CVAT_ORG` thì đặt `organization_slug`) → kiểm bản server →
  tìm project theo tên (hơn một thì dừng; chưa có thì tạo từ `face50_label.json`; có rồi thì kiểm đủ bảy label skeleton theo nhóm, 50 sublabel đúng tên; còn label `face50` cũ thì dừng và nói P4 dựng lại) → dừng nếu đã có task cùng tên trong project → `create_from_data` (`spec={"name","project_id"}` không labels, `ResourceType.LOCAL`,
  `image_quality` 95, `use_cache` True, `job_file_mapping` = các nhóm `job_size` mặt Nhận theo thứ tự + **một job Gán tay riêng ở cuối**; không dùng `sorting_method`, `segment_size`, `annotation_path`) → kiểm số job → kiểm tên frame khớp tên ảnh trong XML
  (khác thứ tự thì ghi `runs\<lượt>\xml\prelabel_cvat.xml` với `id` ảnh ghép theo **tên**, không sửa `prelabel.xml`) → `import_annotations("CVAT 1.1", …)` **đúng một lần, chỉ khi task còn 0 nhãn** → `export_dataset("CVAT for images 1.1", check.zip, include_images=False)` → kiểm mỗi mặt Nhận có bảy skeleton (mỗi nhóm một)
  đủ 50 tên điểm kèm `low_conf`, mặt **Gán tay có nháp** có đúng bảy skeleton đủ 50 điểm với **mọi** `low_conf = true`, mặt **Gán tay ảnh trống** không có nhãn. Dòng cuối: `push xong: task <tên> id <id>, <n> job (<a> Nhận, <b> Gán tay), <url>`.
- **Gán tay có nháp / ảnh trống:** `steps.push` phân loại bằng `phan_loai.classify` (`tay_nhap` = mặt Gán tay có nháp hợp lệ trong `mp50.json`: đủ 50 điểm, mỗi điểm 2 số hữu hạn; `tay_trong` = còn lại, gồm mặt chọn Nhận mà không có nháp) và ghi XML = mặt Nhận (id `0…`, cờ thật của `flags.json`)
  rồi mặt Gán tay có nháp (id nối sau, mọi `low_conf=true`). `m28core.push.push` (chữ ký không đổi) suy ra nhóm Gán tay có nháp từ XML: ảnh Gán tay nào có `<image>` trong XML thì được nhập nháp, còn lại là ảnh trống; XML có ảnh không thuộc Nhận ∪ Gán tay, hoặc thiếu mặt Nhận, thì dừng trước khi kết nối.
  Nhập nhãn vẫn đúng một lần (chỉ khi task còn 0 nhãn; chỉ có Gán tay ảnh trống thì không nhập). `steps.push` in thêm dòng `  gán tay: a có nháp (mọi điểm low_conf=true), b ảnh trống` và `log.txt` ghi `gan_tay co_nhap=a anh_trong=b`.
- **`push.json`** (ghi nguyên tử; lượt mới `phien_ban: 2`, thêm `so_anh: {nhan, gan_tay, gan_tay_co_nhap, gan_tay_trong}` và `gan_tay_co_nhap: [tên file…]`; lượt cũ không có các khoá này vẫn đọc và `--cleanup` được; `--resume` lượt cũ giữ nghĩa cũ: mọi Gán tay là ảnh trống, chỉ nhập mặt Nhận; `--resume` lượt mới mà nhóm Gán tay có nháp trong XML đã khác `push.json` thì dừng, không nhập): `trang_thai` `dang_tao` (ghi trước khi gọi `create_from_data`) → `da_tao` (có `task_id`, `jobs`) → `da_nhap` → `xong` (có `check`, `task_url`); lỗi thì giữ trạng thái và ghi `loi` (đã lọc token); `task_deleted` sau khi xoá task.
  `xong` → chạy lại bị từ chối. `da_tao`/`da_nhap` → từ chối, chỉ ra hai cách: `--resume` (làm nốt trên đúng `task_id`, sau khi lấy lại task theo id và kiểm tên, prefix, project; không nhập lại nếu task đã có nhãn) hoặc `--cleanup`.
  `dang_tao` (chết lúc tạo, không có id) → `--cleanup` chỉ **liệt kê** task cùng tên trong project để bạn tự xoá trong CVAT, rồi xoá `push.json`; không tự xoá task nào.
- **Xoá task trên CVAT** (`push --cleanup --confirm-name <tên>` hoặc nút **Xoá task trên CVAT…** ở tab Các đợt): chỉ xoá được task **chính tool đã tạo** (id và tên ghi trong `push.json`), tên bắt đầu đúng `demo-` (không bao giờ task `m28-` hay task lạ).
  Trước khi gọi API tool lấy lại task **theo id** từ CVAT và kiểm tên khớp `push.json`, tên bắt đầu `demo-`, task thuộc project m28, `CVAT_URL` trùng với lúc đẩy; không khớp thì từ chối và không gọi lệnh xoá. Không xoá khi lượt đang đẩy/chuẩn bị (file khoá `.dang_chay`).
  Trên trang: hộp xác nhận nói rõ **không hoàn tác được, mất cả nhãn đã sửa trong CVAT, nên chạy `collect` trước**; phải gõ lại **đúng tên task** (phân biệt hoa thường, không dấu cách thừa) **và** tick "Tôi hiểu nhãn đã sửa trong CVAT sẽ mất" thì nút xoá mới bật; **Huỷ** là mặc định, **Esc** = Huỷ.
  Link/token lấy từ tab Cài đặt hoặc biến môi trường (không nhập ở hộp xoá). Xoá xong: ghi vào `log.txt` (`xoa_task`) và `push_log.txt`, `push.json` đổi thành `task_deleted` (giữ id/tên cũ), `push\done.txt` bị gỡ, đợt **đẩy lại được** (`push.json` mới ghi lịch sử ở `truoc_do`). Task đã mất sẵn trên CVAT (xoá tay) thì chỉ đánh dấu.
- **`collect`** (chỉ xuất; không bao giờ `import_annotations` hay tạo/sửa/xoá gì trên CVAT): nhận nhiều `--task`. Task `demo-…` (không `--skip-export`): tìm theo tên (0 hoặc ≥ 2 task trùng tên thì báo và bỏ), xuất `"CVAT for images 1.1"` chỉ nhãn vào `raw\<task>_<người>_<ngàyDDMM>.xml` kèm `.txt`
  cùng tên (bản server, id, số ảnh, giờ tạo theo giờ Việt Nam UTC+7, số job và stage/state từng job), **không ghi đè** (đã có thì dùng file đó). `<người>` = `--reviewer` (mặc định `RA`: nên đặt `--reviewer P4`). Task không bắt đầu `demo-` (ví dụ `m28-manual`): không gọi CVAT, chỉ đọc
  `raw\<task>_*_*.xml` mới nhất của mỗi người. Báo cáo `outputs\collect_<tag hoặc task đầu>.md`: số ảnh, mặt đủ 50 điểm, điểm thiếu, điểm `low_conf` bật, file còn thiếu, job chưa `completed`; với task `demo-…` có `runs\*\push.json` bản 2 thì thêm dòng "Gán tay: a có nháp, b ảnh trống" và tách điểm `low_conf` bật thành "ở mặt Nhận" và "ở mặt Gán tay có nháp (bật sẵn từ máy, người gán chưa tắt)"; task `m28-…` và lượt cũ: báo cáo như cũ; thời gian từng bước, QC của P2 (nếu có `m28core.qc.run(xml_paths, outputs_dir)`; chưa có thì một dòng "bỏ qua").

## Kiểm tra nhanh CVAT (`tool\cvat_smoke.py`)
Một bài kiểm tra để **từng người chạy trên máy có CVAT 2.77 thật** và gửi báo cáo cho P4 nếu có chỗ HỎNG. Nó đi đúng đường code thật (`push.push`, `push.get_project_id`, `collect.collect`, `push.delete_task`, `cai_dat_thu.check`, `make_label`), không viết lại logic. Dữ liệu là 4 ảnh PNG xám/nhiễu giả (không phải ảnh mặt) sinh trong `runs\_smoke\<giờ>\`.
```bat
python tool\cvat_smoke.py                    rem đầy đủ: tạo task demo-smoke, nhập nhãn, xuất lại, xoá task (và project m28 nếu do lần này tạo)
python tool\cvat_smoke.py --dry-run          rem chỉ kiểm cục bộ (bước 1-3), KHÔNG gọi mạng, thiếu token vẫn chạy được
python tool\cvat_smoke.py --giu-task         rem giữ task demo-smoke để xem bằng mắt trong CVAT (lần chạy sau tự dọn)
python tool\cvat_smoke.py --giu-project      rem giữ project m28 nếu do lần chạy này tạo
python tool\cvat_smoke.py --url http://localhost:8080 --org ten-to-chuc --timeout 120
```
Cũng chạy được bằng menu `chay.bat` (mục "Kiem tra nhanh CVAT") hoặc nút **Chạy kiểm tra nhanh CVAT** ở tab Cài đặt (hộp xác nhận, Huỷ mặc định; thanh tiến độ, log, nút Huỷ kiểm tra, bảng kết quả; khoá chéo với đẩy/xoá task; Lưu/Quên token từ chối khi đang chạy; `SmokeJob` ở `nap_anh.py`, log `runs\_smoke\smoke_log.txt`).
- **Token/link:** chỉ từ biến môi trường `CVAT_URL` + `CVAT_ACCESS_TOKEN` hoặc từ cấu hình tab Cài đặt (đã bật **Nhớ trên máy này**; biến môi trường thắng file). **Không có cờ `--token`.** `--url`/`--org` chỉ ghi đè link/tổ chức; token giữ nguyên nguồn (khác link thì có cảnh báo). Chỉ gọi tới đúng link đó (tiền kiểm không mang token, không theo redirect). `--timeout` (5-600 giây, mặc định 60) là timeout **từng yêu cầu mạng**, không phải tổng.
- **12 bước** (in `[k/12] <tên bước>: …`; kết quả ĐẠT / HỎNG / BỎ QUA; bước hỏng làm bước phụ thuộc BỎ QUA, dọn dẹp luôn chạy): 1 cấu hình cục bộ (bảy label khớp `m28_config.json`, 50 điểm, 47 cạnh), 2 XML nháp cục bộ, 3 link và token, 4 kết nối và phiên bản (server phải là 2.77.x), 5 project m28 và label skeleton (tạo nếu chưa có rồi **đọc lại từ server**: đúng 7 label skeleton theo nhóm, 50 sublabel đúng tên **và thứ tự**, `low_conf` checkbox, svg đúng cặp cạnh), 6 dọn `demo-smoke` cũ, 7 tạo task và job (3 job: Nhận, Nhận, Gán tay; thứ tự frame), 8 nhập XML nháp, 9 xuất và đọc lại bằng `collect.collect` thật (bảy skeleton gộp lại thành 50 điểm đúng tên/thứ tự, `low_conf` giữ nguyên, toạ độ ≤ 0,05 px, kích thước ảnh, Gán tay có nháp đủ điểm `low_conf=true`, Gán tay trống không nhãn), 10 bảo vệ an toàn (push lần hai bị từ chối; tên không prefix `demo-` bị từ chối trước khi kết nối; task khác nguyên vẹn), 11 xoá task `demo-smoke`, 12 project.
- **Dọn dẹp:** chỉ tên `demo-smoke`; chỉ xoá đúng id trong `push.json` (qua `push.delete_task`, kiểm lại id, tên, project, link; sau đó `retrieve` phải ra 404). Project m28 chỉ bị xoá khi **chính lần chạy này tạo** và đang rỗng; project có sẵn thì giữ nguyên, label sai cũng **không sửa/xoá**. Có task `demo-smoke` mà tool không có dấu hiệu đã tạo thì HỎNG và **không xoá** (tự xoá trong giao diện CVAT). `runs\_smoke\dang_mo.json` (id task chưa dọn xong, ghi trước khi push) giúp lần chạy sau tự dọn kể cả khi lần trước bị Ctrl+C hay mất mạng giữa chừng; đánh dấu của CVAT khác thì không đụng. Trên CVAT dùng chung, nếu người khác tạo hoặc xoá task đúng lúc đang chạy thì bước 10(c) (task khác nguyên vẹn) có thể báo nhầm: chạy lại.
- **Đầu ra:** bảng `Bước | Kết quả | Ghi chú` và dòng "Tất cả ĐẠT" hoặc "Có N bước HỎNG"; báo cáo `runs\_smoke\bao_cao_<giờ>.txt` và `.json` (máy, Python, bản cvat-sdk, link, nguồn token là chữ, bản server, tài khoản, project, task, từng bước; không ghi đè; **đọc lại để khẳng định không chứa token**, có thì xoá file); dòng cuối `SMOKE_JSON: <đường dẫn .json>`. Khi có HỎNG, gửi P4 file `.txt` (không gửi token, không gửi ảnh). Mã thoát: 0 không bước nào HỎNG, 1 có HỎNG, 2 sai đối số.
- **Chưa ai chạy trên CVAT thật.** Test (`tests\test_cvat_smoke.py`) chỉ dùng CVAT giả; những gì chỉ CVAT thật trả lời được: svg đổi `data-label-id`, thứ tự sublabel, `job_file_mapping`, nhập skeleton, xoá project, timeout thật.

## Chạy test
```bat
python -m pytest tests -q
```
Test chỉ dùng dữ liệu giả (ảnh ngẫu nhiên, landmarker/mapping giả, mặt tổng hợp đối xứng, **CVAT giả** ở `tests\fake_cvat\cvat_sdk\`) và các file config đã commit; không cần mediapipe (test thử `make_config` với `--no-mesh`; mediapipe chỉ cần khi chạy công cụ trên dữ liệu thật), CVAT thật hay mạng. Hiện **666 qua, 3 bỏ qua** trên máy Windows của chủ repo (Python 3.14.7, 7/10/2026), cộng **11 lỗi CÓ SẴN do Windows** (không do M28; cả 11 đều đã có lúc đo gốc trước khi sửa: 640 qua, 15 lỗi, 3 bỏ qua; 4 lỗi gốc còn lại nay qua: 3 bài `test_cai_dat` đọc `config\m28_config.json` vốn checkout kiểu CRLF nay ghi LF, 1 bài khoá `.dang_chay` chập chờn; xem "Chạy test và báo lỗi" trong `HUONG-DAN-WINDOWS.md`): tạo symlink cần quyền (3 bài: `test_dot_anh` 2, `test_cai_dat::test_settings_dir_inside_repo_is_refused`), dấu `\` trong tên mục zip (`test_ca_kho`), đường dẫn kiểu `D:\` (3 bài: `test_ca_kho::test_html_thoat_ky_tu`, `test_cai_dat` 2), test tự ghi file bằng `write_text` ra CRLF nên `write_t_flip` từ chối (`test_cai_dat` 2), thăm dò cổng đóng trả `timeout` thay vì `server_down` (`test_cai_dat::test_probe_statuses`) và khoá `.dang_chay` báo còn tiến trình `cvat_smoke` cũ (`test_cvat_smoke::test_smoke_job_runs_real_cvat_smoke_against_fake_cvat`). Trên cloud Linux, Python 3.11 (6/10/2026) ra 657 qua, 1 bỏ qua trước giai đoạn 3. `tests\e2e_*.py` cần playwright + Chromium nên chưa chạy ở lượt này.
`tests\test_mapping.py` thử config version 3 (50 điểm DMS: đúng 7 nhóm 5/5/4/8/8/12/8, tên `<nhóm>_<k>` liên tục, không `jaw`, `region`/`line`/`lines.closed`/E-C/`curve` trong nhóm/`coincide` đối xứng/`side` theo ảnh/`side_convention`, cặp `flip` theo quy ước tên và khớp hoán vị gương, điểm side M trên trục), hoán vị gương (đối hợp, cặp chắc chắn, `check_against_data`), `apply_map` (lấy đúng đỉnh, lật + đổi tên, đúng bên trên mặt giả nhìn thẳng, tập con config, từ chối map ridge, map version 2 và config thiếu `side_convention`), `make_config` (ước lượng `flip_width` trên mặt giả, `--run` KHÔNG ghi đè file gương trừ khi `--learn-mirror`, giữ số người khác đã ghi nhưng không mang từ v2 sang v3) và file đã commit nhất quán với nhau (config, map, label, `tmpl` nhóm trái nằm nửa trái khuôn); `tests\test_dms_v3.py` thử cả chuỗi map50 -> flags -> XML -> cvat_io -> eval50 với tên mới và lượt cũ (tên v2) bị báo rõ; `test_eval50.py`, `test_check_flip.py`, `test_flag_eval.py` (hai chế độ), `test_check_drivface.py` thử các công cụ đo bằng nhãn và mặt giả.
`tests\test_push.py` thử push/collect/xoá task bằng gói `cvat_sdk` giả (giữ "server" trong bộ nhớ, ghi mọi lời gọi, giả lỗi theo lệnh) và so từng lời gọi với chữ ký của cvat-sdk **thật** nếu import được
(`pip install cvat-sdk==2.77.0`, hoặc đặt `M28_REAL_CVAT_SDK_PATH=<thư mục chứa gói cvat_sdk>`; không có thì bài đó `skip`). `tests\test_cvat_smoke.py` thử `tool\cvat_smoke.py` và nút kiểm tra nhanh bằng CVAT giả (đường ĐẠT, dry-run, từng bước HỎNG, dọn dẹp, không rò token, `SmokeJob`). `tests\test_gan_tay.py` thử Gán tay có nháp (phân loại, XML, push với CVAT giả, tương thích `push.json` cũ, collect, chữ trên trang). `tests\test_make_label.py` thử bảy label skeleton theo nhóm (màu, cạnh, khuôn svg). `tests\test_dot_anh.py` thử tab Các đợt, xoá mềm,
nút Đẩy, PushJob/DeleteTaskJob. `tests\test_cai_dat.py` thử tab Cài đặt (lưu/nạp/quên, quyền file, ưu tiên nguồn, kiểm link/token/đường dẫn, t_flip, thử kết nối bằng tiến trình con với CVAT giả, tiền kiểm redirect bằng http.server cục bộ, không rò token); `tests\conftest.py` trỏ `M28_CONFIG_DIR` vào thư mục tạm cho mọi test. `tests\test_review_app.py` thử phần logic của trang rà soát mà không cần gradio hay trình duyệt. Kiểm thử trên trình duyệt thật
(tuỳ chọn, cần playwright, không nằm trong requirements): `python tests\e2e_review_ui.py --work <thư mục có runs\F5 và runs\ALL616> --shots <thư mục ảnh chụp>`
(pha F thử tab Nạp ảnh bằng ảnh in-cabin thật: thêm `--imgs <thư mục khung gốc>` nếu không phải `<work>\data\frames`) và
`python tests\e2e_dot_push.py --work <thư mục có config\ và face_landmarker.task> --imgs <thư mục khung gốc> --shots <thư mục ảnh chụp>` (nạp ba đợt Khoi, Nam, Cuong bằng MediaPipe thật, xoá mềm, rà, đẩy lên CVAT giả, xoá task, màn 1440 và 420 px) và
`python tests\e2e_cai_dat.py --work <…> --imgs <thư mục khung gốc> --shots <thư mục ảnh chụp>` (tab Cài đặt, bảy pha A–G, xem đầu file).

## Giao diện m28 giả định từ P2/P3/P4
Các dòng dưới là **điều `m28.py` đang giả định, chưa ai xác nhận**. Ai thấy khác thì sửa bảng này hoặc báo P1.

| Ai | Module / khoá | Chữ ký / dạng dữ liệu | m28 dùng ở | Trạng thái |
|---|---|---|---|---|
| P3 | `m28core.mapping.apply_map` | `apply_map(pts478, map, config, flipped=False, width=None)` → `{tên điểm: [x, y]}` toạ độ ảnh cắt 512; `flipped=True` nhận 478 điểm ảnh lật và **đã bỏ lật**; `mp_idx`/`flip` lệch map, map ridge cũ, map version 2 hoặc config thiếu `side_convention: "image"` → `ValueError` | bước `map50` | **có sẵn** (`tool/m28core/mapping.py`, chọn đỉnh), P3 xác nhận |
| P3 | `config/m28_config.json` khoá `points` | list, mỗi phần tử có `name` (thứ tự = thứ tự điểm trong XML), `mp_idx`, `group`, `curve` (danh sách tên hoặc `null`), `flip`, `side` (theo ảnh)... (version 3, 50 điểm DMS) | `map50`, `flags`, `autoqc`, XML, `eval50.py` | **có sẵn** (`tool/make_config.py`), P3 chốt trước 12/10 |
| P3/P2 | `config` khoá `iod_points` | 2 tên điểm khoé mắt ngoài (`mattrai_1` trái ảnh, `matphai_1` phải ảnh) để tính khoảng cách hai mắt | `flags`, `eval50.py`, `check_flip.py`, `flag_eval.py` | chưa ai xác nhận |
| P3/P2 | `config` khoá `t_flip` | số, hoặc `null` (chưa chốt) thì mọi `low_conf` = false | `flags` | chưa ai xác nhận |
| P3 | `config/map_mp50.json`, `config/mp_mirror478.json` | map version 3 `{names, points: {tên: {mp_idx, flip}}, flip_width, meta}` và hoán vị gương `{perm, fixed, meta}`; m28 chỉ đọc JSON rồi đưa nguyên cho `apply_map` | `map50`, `check_flip.py` | **có sẵn** (`tool/make_config.py` sinh cả hai; không còn `fit_map.py`) |
| P4 | `m28core.autoqc.run` | `run(name, pts50, config)` → list mã lỗi (chuỗi); mã bắt đầu bằng `guong`, `don_cuc` hoặc `diem_khong_hop_le` thì gợi ý "nen_gan_tay". Module tuỳ chọn | bước `autoqc` | chưa ai xác nhận |
| P4 | `runs/<run>/autoqc/autoqc.csv` | m28 ghi: `name,suggestion,n_flags,decision,reason,seconds,problems` (`suggestion` = `on`/`can_xem`/`nen_gan_tay`; `name` có đuôi `.png`) | `review` (excel, auto), P2 xếp hàng | chưa ai xác nhận |
| P4 | `m28core.push.push` | `push(run_dir, task_name, nhan_imgs, tay_imgs, xml_path, project=, prefix=, label_json=, *, resume=False)` trả đường dẫn `check.zip`; đường ảnh là đường dẫn file đầy đủ; ảnh trong `tay_imgs` có `<image>` trong `xml_path` là Gán tay **có nháp** (mọi điểm `low_conf=true`), không có thì là ảnh trống; từ chối tên không bắt đầu `demo-`; tự ghi `push.json`; thêm `cleanup(run_dir, prefix=, confirm_name=)` / `delete_task(...)` | bước `push` | **bản đầu có sẵn** (`tool/m28core/push.py`), **chưa thử trên CVAT thật**; P4 xác nhận |
| P4 | `m28core.collect.collect` | `collect(args)` → `True` nếu xong (`args.task` list, `dry_run`, `skip_export`, `tag`, `reviewer`) | lệnh `collect` | **bản đầu có sẵn** (`tool/m28core/collect.py`), **chưa thử trên CVAT thật**; P4 xác nhận |
| P2 | `tool/review_app.py` | `python tool\review_app.py <run_dir> <reviewer>`; ghi `runs/<run>/review/triage_<reviewer>.csv` và `done.txt` khi bấm Xong; `launch(server_name="127.0.0.1", share=False)` | `review --review ui` | **bản nháp có sẵn** (`tool/review_app.py`, xem mục Trang rà soát), P2 xác nhận |
| P2/P4 | `triage_<Pk>.csv` | cột `name,decision,reason,seconds` (tên có hay không đuôi ảnh đều được; không tiêu đề thì đọc theo thứ tự cột). Dòng sau đè dòng trước; `decision` rỗng (dòng Hoàn tác về chưa rà) nghĩa là chưa rà | `review`, `push` | chưa ai xác nhận |
| P1/P4 | `config/pipeline.json` | khoá `project` (mặc định `m28`), `prefix` (mặc định `demo-`), `cvat_version` (2.77.0), `job_size` (8) | `push`, `collect` | **bản đầu có sẵn** (`config/pipeline.json`), chưa thử trên CVAT thật |
| P4 | `config/face50_label.json` | bảy label skeleton theo nhóm (50 sublabel theo config, màu theo nhóm, checkbox `low_conf`, svg khung 0–100); do `tool/make_label.py` sinh, `push` dùng để tạo project | `push` | **bản đầu có sẵn** (`tool/make_label.py`), **chưa thử trên CVAT thật** |
| P2/P4 | `m28core.qc.run` | `run(xml_paths, outputs_dir)` → chuỗi tóm tắt hoặc `None`; module tuỳ chọn, `collect` gọi nếu có | `collect` | chưa ai xác nhận |

## Đầu vào / đầu ra
- Vào: thư mục ảnh (hoặc danh sách `image,face_idx` + hộp mặt từ `manifest.csv`), `config/m28_config.json`.
- Ra: `runs/<run>/…` (ảnh chồng, cờ, `triage_<Pk>.csv`, `push\manual_list.txt` (loại `co_nhap`/`anh_trong`), `ca_kho.csv`), `outputs/ca_kho/` (gói họp, phiên họp, biên bản), task CVAT `demo-…`, file xuất `raw/<task>_<Pk>_<ngày>.xml`.

## Đã thử trên
- **50 điểm DMS (config version 3, QĐ-003) trên dữ liệu in-cabin thật** (7/10/2026, giai đoạn 3; máy Windows 11 của chủ repo, Python 3.14.7, mediapipe 1.0.1, CPU; chỉ có gói `data\crops`): `prepare --box crop` 616 mặt, `make_config.py --run` (giữ hoán vị gương), `make_label.py`, `check_flip.py`, `flag_eval.py --set Tdev`,
  `review --review auto`, `push --dry-run` (`INC3_ALL`, `INC3_XCROP`, `INC3_AUTO`), `eval50.py` tự so và có nhiễu, ảnh kiểm 46 mặt đủ loại. Số liệu: mục "50 điểm DMS trên đỉnh MediaPipe". **Chưa thử:** `check_drivface.py` (không có DrivFace gốc ở máy này; chỉ thử bằng dữ liệu giả), `--box auto` trên khung gốc (không có `data\frames`),
  CVAT thật v2.77.0 với label mới, nhãn gán tay thật theo DMS (`eval50.py`, `flag_eval.py --gt` mới chạy trên nhãn giả), `tests\e2e_*.py` (không có playwright), lượt cũ (run v2) đọc bằng config v3 (xem "Giới hạn").
- **Ánh xạ chọn đỉnh trên dữ liệu in-cabin thật, 50 điểm version 2 CŨ** (6/10/2026, giai đoạn 2, trước QĐ-003; Linux cloud, Python 3.11, mediapipe 1.0.1): `prepare` 616 mặt (auto và gói), `make_config.py --run`, `check_flip.py`, `flag_eval.py --set Tdev`, `check_drivface.py` (606 ảnh), `review --review auto`, `push --dry-run` (615 mặt tự dò: XML 615 x 50 điểm, 640 x 480; 50 mặt gói: 512 x 512; đủ tên điểm, đúng thứ tự, trong ảnh),
  `eval50.py` (chính `prelabel.xml` so với chính nó: NME 0,00% trên 615 mặt; thêm nhiễu Gauss 3 px: NME 3,04%, đường đọc XML chạy trên file thật), ảnh kiểm 35 mặt đủ loại. Số liệu: mục "50 điểm DMS trên đỉnh MediaPipe", phần "Lịch sử: 50 điểm version 2" (định nghĩa 50 điểm TRƯỚC QĐ-003, không còn hiệu lực). **Chưa thử:** Windows/cmd, Python 3.14, MediaPipe trên Windows (`flip_width` có thể khác), CVAT thật với `face50_label.json` mới (đổi `tmpl`), nhãn gán tay thật (`eval50.py` và `flag_eval.py --gt` mới chỉ chạy trên nhãn giả và trên XML nháp tự so).
- **Dữ liệu in-cabin thật** (6/10/2026, Linux cloud, Python 3.11, mediapipe 1.0.1, 4 nhân CPU, không GPU; Windows, Python 3.14 **chưa thử**): `tool\inc_ingest.py` trên YawDD (349 video: 29 Dash + 320 Mirror, tất cả khớp regex tên) và DrivFace (606/606 ảnh khớp tên, `raw+.jpg`).
  `scan`: 10.377 khung đọc, 3.149 ứng viên (YawDD 2.980 từ 349 video, DrivFace 169), loại: không thấy mặt 44, có điểm ngoài khung ảnh 34, gần trùng 6.597, vượt trần 553; 94 người (90 `yd_`, 4 `df_`).
  `split` seed khởi đầu 5, **seed thực dùng 19**: F 300 (33 người), Tdev 100 (20), Ttest 100 (20), G 20 (11), P 16 (9), X 50 (21), D 30 (16) = 616 mặt, 73 người ở nhóm A, 21 ở nhóm B, 0 người chung; 333 video, tối đa 3 mặt/video;
  `check_manifest.py` đạt. `pack`: 5 phần ảnh (27,8 / 27,8 / 27,8 / 27,8 / 17,0 MiB) + meta 0,18 MiB; giải nén bằng `bsdtar` vào thư mục trống, `check_manifest` đạt, md5 616 ảnh khớp `crops` gốc.
  Pipeline trên 5 mặt F thật: `prepare --box auto --images data\frames` (6 bước xong, ảnh cắt pipeline trùng ảnh cắt trong gói), `review --review auto`, `push --review auto --dry-run` ra XML 5 x 50 điểm (tên ảnh = tên khung gốc);
  và lượt chỉ có gói (`--images data\crops --box crop`, không có khung gốc) ra XML 5 x 50 điểm 512 x 512, ảnh cắt trùng từng điểm ảnh. Ảnh chồng: điểm nằm trên mặt (xem mục "50 điểm DMS trên đỉnh MediaPipe").
  Chưa thử: `cv2` đọc `.avi` YawDD trên Windows (codec), `tar -xf` của Windows với `.rar`, MediaPipe trên Python 3.14, `chay.bat` mục 3 trong cmd thật.
- **Ca khó và họp team** (6/10/2026, Linux cloud, Python 3.11, Gradio 6.29.1, Chromium headless): `tests/test_ca_kho.py` (88 test, gồm zip độc hại, biên bản so khớp mẫu) và `tests/e2e_ca_kho.py` (đánh dấu, tab Ca khó, xuất/tải gói, nhập gói, lưới, trình chiếu, mở lại phiên, biên bản). Chưa thử: Windows/cmd, Python 3.14, kéo thả bằng chuột thật, toàn màn hình thật, Excel mở CSV.
- Test dữ liệu giả (`tests/`) trên Linux, Python 3.11, bằng landmarker/mapping/push/collect giả.
- **Trang rà soát** (`tool/review_app.py`, 5/10/2026): Gradio 6.29.1, Python 3.11, Linux cloud, Chromium headless qua Playwright 1.56.0; trên `runs\F5` thật (5 mặt) và
  lượt 616 mặt (24 mặt không có nháp). Đã thử: phím tắt, hoàn tác, đóng giữa chừng (kill) rồi mở lại, màn 1440x900 và 800x900, chế độ tối (`?__theme=dark`),
  lỗi ghi file (giả lập), nút Xong (dải xanh, tải lại một lần, trang vẫn chạy) rồi nút Đóng trang rà soát (mã thoát 0) và đi tiếp trong `m28.py review` rồi `push --dry-run`, không có request ra ngoài 127.0.0.1 dù đặt proxy chết.
  Số đo trên 616 mặt (CPU cloud, lúc nguội, chưa có ảnh nhỏ nào): từ lệnh chạy đến khi lưới hiện ảnh khoảng 6,5 giây (nạp Gradio chiếm khoảng 4,5 giây), mỗi quyết định
  trung vị 0,11 giây, đổi trang lần đầu tối đa 0,61 giây. `tests\e2e_review_ui.py` tự đo lại các số này.
- **Tab Nạp ảnh** (6/10/2026, `tool/nap_anh.py` + `review_app.py`): Linux cloud, Python 3.11, Gradio 6.29.1, mediapipe 1.0.1, Chromium qua Playwright. Pha F của `tests\e2e_review_ui.py`:
  thả 12 file (6 ảnh in-cabin thật, tên có dấu/đuôi hoa, hai ảnh cùng tên, PNG xám, file chữ đổi đuôi, ảnh trùng; `set_input_files`, không phải kéo chuột thật), prepare thật bằng MediaPipe, Huỷ/Thử lại,
  "Rà lượt này" (relaunch cùng cổng, lượt cũ y nguyên), thiếu model, chế độ `--nap`. **Chưa thử**: Windows/cmd, Python 3.14, relaunch cùng cổng trên Windows, kéo thả bằng chuột thật,
  ảnh > 25 MB thật, đường dẫn dự án có dấu tiếng Việt (`cv2.imread` trên Windows không đọc được đường dẫn Unicode; tên ảnh đã ASCII nhưng thư mục dự án thì không).
- **Đẩy lên CVAT, tab Các đợt, xoá mềm, xoá task** (6/10/2026): Linux cloud, Python 3.11, Gradio 6.29.1, mediapipe 1.0.1, Chromium qua Playwright, ảnh in-cabin thật, **CVAT GIẢ** (không phải server thật). `tests\e2e_dot_push.py`:
  nạp ba đợt Khoi, Nam, Cuong (có ghi chú), thẻ đợt, xoá mềm/khôi phục/dọn thùng rác ảnh của Nam (Huỷ, Esc, Enter ở Huỷ không xoá), rà Khoi, nút Đẩy (khoá khi còn mặt chưa rà; hộp xác nhận; Huỷ/Esc; đẩy; thẻ kết quả; không đẩy lần hai),
  cảnh báo CVAT khi xoá ảnh của đợt đã đẩy, xoá task (gõ tên + tick; Huỷ/Esc không gọi xoá; xoá đúng một lần; đẩy lại được), xoá cả đợt Cuong và khôi phục, trang không có biến CVAT (hướng dẫn `set`), phím tắt không chạy ở tab Các đợt,
  màn 1440 và 420 px, token giả không lộ trong HTML/log/`push.json`. **Chưa thử**: server CVAT thật (cả `push`, `collect`, xoá task, label skeleton), Windows/cmd, Python 3.14.
- **Chưa chạy**: `autoqc` của P4, `push` thật, `collect` thật, trang rà soát trên Windows/Python 3.14/trình duyệt thật có giao diện/máy có proxy công ty/Excel khoá file thật, Windows/cmd, Python 3.14, CVAT 2.77.0 (kể cả nhập được XML `<skeleton>` không), CSV do Excel lưu.
- Cập nhật sau thí nghiệm 14–15/10 và lượt chạy tập R (16–18/10): thời gian trước/sau, số nháp hỏng trang rà soát bắt được.

## Rủi ro: chưa thử trên CVAT thật
Cloud không có CVAT. `push`, `collect`, xoá task và bảy label skeleton chỉ được thử bằng CVAT giả; chữ ký các lời gọi SDK đã đối chiếu với cvat-sdk 2.77.0 thật (`tests\test_push.py::test_signatures_match_real_sdk`) và định dạng label/XML đối chiếu với mã nguồn CVAT v2.77.0
(đọc từ GitHub, tag `v2.77.0`), nhưng **chưa có server nào xác nhận**. Từ nay có công cụ để kiểm các giả định 1-10 ngay trên máy có CVAT thật: `python tool\cvat_smoke.py` (mục "Kiểm tra nhanh CVAT"); **chưa ai chạy nó trên CVAT thật**. Khi có CVAT 2.77.0, kiểm các giả định sau (mỗi mục đều có thể làm `push` lỗi, và lỗi luôn dừng có thông báo, không tạo task thứ hai):
1. **Xác thực**: `make_client(url, access_token=token)` (đúng chữ ký 2.77.0; `Client.login` gán `configuration.access_token`, chưa kiểm server nhận Personal Access Token theo cách đó). Token sai/hết hạn → HTTP 401/403 → thông báo "tạo lại token".
2. **Label skeleton** (`tool\make_label.py`): `projects.create({"name", "labels": [...]})` nhận danh sách label có `type: "skeleton"`, `sublabels` (type `points`, màu theo nhóm, thuộc tính checkbox `low_conf`), `svg` khung `0 0 100 100` (cvat-ui) với `data-label-name="<tên>"` và **không có** `data-label-id`
   (server đổi `data-label-name` thành `data-label-id` khi tạo — `serializers.py`, đã đọc), `data-element-id` = `data-node-id` = 1..n đếm trong từng skeleton (cvat-ui dùng `data-element-id` cho cả hai). Cạnh: chỉ nối hai điểm liền nhau trong cùng `line` của config (+ điểm cuối về đầu với line `closed`): 47 cạnh, chia theo nhóm.
   Chưa kiểm: CVAT hiện đúng 50 điểm và cạnh, checkbox `low_conf` nằm trên từng điểm, màu hiển thị, và `Project.get_labels()` trả `sublabels` lồng trong từng label nhóm (`check_project_labels` chấp nhận cả dạng phẳng `has_parent`).
3. **`job_file_mapping`**: `create_from_data(..., data_params={"image_quality": 95, "use_cache": True, "job_file_mapping": [[tên ảnh…], …]})`. Theo `cvat/apps/engine/task.py` v2.77.0: mapping **không** dùng chung với `sorting_method` khác lexicographical, `segment_size`, `start_frame`, `stop_frame`, `frame_filter`, `filename_pattern`;
   tool không truyền các khoá đó. Tên trong mapping phải đúng **basename** ảnh tải lên (SDK gửi `client_files` bằng đường dẫn tuyệt đối; chưa kiểm server lấy basename). Job tạo theo đúng độ dài từng nhóm (`push` so lại với `Task.get_jobs()`, lệch thì ghi `canh_bao` trong `push.json`, không xoá task).
4. **Thứ tự frame**: theo mã nguồn, với mapping thì frame xếp theo thứ tự nối các nhóm (Nhận trước, Gán tay sau). `push` vẫn đọc `get_frames_info()` và, nếu khác thứ tự XML, ghi `prelabel_cvat.xml` với `id` ảnh theo frame thật (ghép theo tên). Tên frame trên server khác tên file thì `push` dừng (task giữ, `--cleanup` để xoá).
5. **Nhập nhãn**: `import_annotations("CVAT 1.1", xml)` với bảy `<skeleton label="<nhóm>">` (mỗi nhóm một) chứa tổng 50 `<points label=… occluded="0" outside="0">` kèm `<attribute name="low_conf">`; loader trong `dataset_manager/formats/cvat.py` đòi `occluded`, `outside`, `points` trên từng điểm (đã đọc). Chưa kiểm server nhận file có đủ 50 điểm skeleton, và rằng `id` ảnh trong XML không quan trọng bằng `name`.
6. **Xuất**: `export_dataset("CVAT for images 1.1", path, include_images=False)` (tham số `include_images` có trong 2.77.0); kiểm đọc `annotations.xml` trong zip theo **tên ảnh và tên điểm**, thuộc tính `low_conf` là `true`/`false`.
7. **Kiểm bản server**: `make_client` gọi `check_server_version` (SDK 2.77 chấp nhận server 2.77.x và 2.78.x và ném `IncompatibleVersionException` nếu khác); `push` còn so thêm `(major, minor)` của `get_server_version()` với `cvat_version` trong `config\pipeline.json`.
8. **`CVAT_ORG`**: đặt `client.organization_slug`; project phải nằm trong organization đó (chưa thử).
9. **Xoá task**: `Task.remove()` (= `DELETE /api/tasks/<id>`); tool lấy lại task bằng `tasks.retrieve(id)` và so tên, prefix, project trước khi xoá. Chưa kiểm server trả mã gì khi task đã mất (tool coi HTTP 404 là "đã mất").
10. **`collect`**: lấy danh sách task bằng `tasks.list()` rồi lọc theo tên (chưa thử phân trang với server nhiều task); `Job.stage`/`state` chỉ dùng để báo job chưa `completed`.

11. **Gán tay có nháp (lệch kế hoạch, cần P4 và P5 đồng ý).** Thay đổi này lệch `de-tai-m28/p4-cvat.md` dòng 328 ("XML chỉ có skeleton cho mặt Nhận…; mặt Gán tay không có skeleton") và dòng 112 (18/10, `demo-R1610`: "mặt Gán tay nằm trong job riêng, không có điểm"): giờ mặt Gán tay có nháp có skeleton 50 điểm, mọi `low_conf=true`.
    Bản Claude Docs chưa sửa (không sửa `de-tai-m28/`). Chưa kiểm trên CVAT thật rằng 50 điểm `low_conf=true` nhập được và checkbox hiện bật đúng. Với mặt lật gương/dồn cục, nháp có thể sai gần hết và kéo 50 điểm có thể chậm hơn vẽ mới (P5 nên đo).
    `low_conf` của mặt Gán tay trong file xuất không phản ánh độ tin của máy (bật hết). Mặt Nhận vẫn chưa kiểm điểm không hữu hạn (giữ nguyên hành vi cũ; chỉ Gán tay mới kiểm `nhap_hop_le`).

## Giới hạn
- Chỉ làm nháp cho mặt lớn nhất trong ảnh; ảnh nhiều người chọn "Gán tay".
- MediaPipe yếu với mặt nhỏ, nghiêng mạnh, bị che nhiều.
- **Lượt chạy và dữ liệu của 50 điểm cũ (version 2, trước QĐ-003) không dùng được với config version 3.** Lượt cũ có `mp50.json` tên `pNN_vùng_bên`: `m28.py prepare` tự tính lại `map50 flags autoqc overlays` (từ `pred478.json`, không chạy lại MediaPipe), các lệnh khác (`push`, `flags`…) dừng và báo cách xử lý;
  `push` không ghi lại XML của lượt đã đẩy xong (`push.json` trạng thái `xong`). Project CVAT dựng bằng label cũ bị `push` từ chối (P4 dựng lại bằng `config\face50_label.json`). Nhãn CVAT/XML tên cũ không đo được bằng `eval50.py` (báo "nhãn dùng định nghĩa CŨ"), task cũ trên CVAT giữ nguyên tên điểm cũ và cần gán/xuất lại theo DMS nếu muốn đo.
- Python 3.14 + mediapipe 1.0.1 mới thử trên một laptop; máy nào lỗi thì dùng Colab/Kaggle (không đưa
  dữ liệu khách hàng lên đó).

## Người viết
P1 (`m28.py`), P2 (model, trang rà soát), P3 (ánh xạ, đánh giá), P4 (CVAT, `push`/`collect`), P5 (thí nghiệm).
