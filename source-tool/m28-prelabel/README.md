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
| `push` | Tạo task CVAT mới tên `demo-…`, nhập nhãn nháp đúng một lần | Tự động, trên CVAT của chính máy đó |
| `collect` | Sau khi gán: xuất nhãn, QC, ảnh chồng, báo cáo ngắn | Tự động |
| `all` | `prepare` → `review` → `push`; dừng ở trang rà soát, gõ lại đúng lệnh sau khi rà xong (`collect` chạy riêng sau khi có người gán) | |

## Cấu trúc (theo kế hoạch)
Mọi đường dẫn trong kế hoạch tính từ thư mục này:

```
m28-prelabel/
├── tool/          m28.py, m28core/, review_app.py, export.py (giao cho khách: không torch, không ảnh)
├── config/        m28_config.json (50 điểm), pipeline.json (không có bí mật)
├── snippets/      đoạn code + prompt mẫu trích từ kế hoạch, CHƯA chạy thử
├── data/          ảnh cắt, manifest, gt*.json        ← KHÔNG commit (repo công khai)
├── raw/ final/    file xuất CVAT                     ← KHÔNG commit
├── outputs/ runs/ backups/                           ← KHÔNG commit
├── requirements.txt / requirements-ui.txt
└── README.md
```

`snippets/<chung|p1…p5>/NN_<tên>.<đuôi>` — số thứ tự theo vị trí trong tab; dòng đầu mỗi file ghi trích
từ mục nào. Đây là điểm xuất phát để viết code thật, không phải code đã kiểm.

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
python tool\m28.py prepare --run R1610 --list data\r_list_1610.csv --images D:\WFLW\WFLW_images --box auto
python tool\m28.py review  --run R1610 --review ui --reviewer P5
python tool\m28.py push    --run R1610 --images D:\WFLW\WFLW_images --task demo-R1610 --review-file triage_P5.csv
python tool\m28.py collect --task demo-R1610
python tool\m28.py all     --run thuP1 --list data\f5_list.csv --images D:\WFLW\WFLW_images --box wflw --review auto --task demo-thuP1
```
- `--box wflw`: lấy hộp mặt từ `data\manifest.csv`, XML theo toạ độ **ảnh cắt 512**, `push` tải ảnh cắt `runs\<run>\crop\images\`.
  `--box auto`: tự dò mặt, XML theo toạ độ **ảnh gốc** (điểm ra ngoài ảnh kẹp vào mép), `push` tải ảnh gốc (nhớ `--images`).
  `prepare` ghi chế độ vào `runs\<run>\crop\box.txt`; `push` đọc lại từ đó, không cần gõ lại `--box`.
- `--review ui` (mặc định, trang của P2 chỉ ở 127.0.0.1) | `excel` | `auto` (theo gợi ý autoqc, chỉ để chạy thử/demo).
  `--review excel`: mở `runs\<run>\autoqc\autoqc.csv` bằng Excel, điền cột `decision` (`nhan`/`gan_tay`/`bo`) và `reason`,
  lưu CSV UTF-8 thành `runs\<run>\review\triage_<reviewer>.csv`, chạy lại đúng lệnh. Chịu BOM và dấu `;` của Excel.
- `--review-file triage_P5.csv`: không có đường dẫn thì tìm ở thư mục hiện tại, rồi `runs\<run>\review\`.
- `--dry-run`: `push` chỉ ghi `runs\<run>\xml\prelabel.xml` rồi dừng (không token, không `done.txt`).
- `--force <bước>...`: làm lại bước (ví dụ `--force flags`). Làm lại bước đầu thì phải `--force` luôn các bước sau.
- Mỗi bước ghi vào `runs\<run>\<bước>\` (`crop`, `mediapipe`, `map50`, `flags`, `autoqc`, `overlays`, `review`, `push`)
  và để `done.txt` khi xong thật; lần sau in "bỏ qua". `runs\<run>\log.txt` ghi giờ, bước, kết quả (`xong`/`bo_qua`/`dung`/`loi`).
  `runs\<run>\no_face.csv` (cột `name,reason,step`) liệt kê mặt không dùng được.
- Mặt Gán tay lên task không có nháp, ở job riêng (`runs\<run>\push\manual_list.txt`); mặt Bỏ ghi `push\rejected.csv`.
  Mặt `no_face` mặc định là Bỏ. Hai mặt cùng một ảnh gốc ở `--box auto` bị từ chối (CVAT cấm tên ảnh trùng).

## Chạy test
```bat
python -m pytest tests -q
```
Test chỉ dùng dữ liệu giả (ảnh ngẫu nhiên, landmarker/mapping/push/collect giả); không cần mediapipe, CVAT hay mạng.

## Giao diện m28 giả định từ P2/P3/P4
Các dòng dưới là **điều `m28.py` đang giả định, chưa ai xác nhận**. Ai thấy khác thì sửa bảng này hoặc báo P1.

| Ai | Module / khoá | Chữ ký / dạng dữ liệu | m28 dùng ở | Trạng thái |
|---|---|---|---|---|
| P3 | `m28core.mapping.apply_map` | `apply_map(pts478, map, config, flipped=False)` → `{tên điểm: [x, y]}` toạ độ ảnh cắt 512; `flipped=True` nhận 478 điểm ảnh lật và **đã bỏ lật** | bước `map50` | **bản nháp có sẵn** (`tool/m28core/mapping.py`), P3 xác nhận |
| P3 | `config/m28_config.json` khoá `points` | list, mỗi phần tử có `name` (thứ tự = thứ tự điểm trong XML) | `map50`, `flags`, `autoqc`, XML | **bản nháp có sẵn** (`tool/make_config.py`), P3 chốt trước 12/10 |
| P3/P2 | `config` khoá `iod_points` | 2 tên điểm mắt (phải, trái) để tính khoảng cách hai mắt | `flags` | chưa ai xác nhận |
| P3/P2 | `config` khoá `t_flip` | số, hoặc `null` (chưa chốt) thì mọi `low_conf` = false | `flags` | chưa ai xác nhận |
| P3 | `config/map_mp50.json` | nội dung tuỳ P3; m28 chỉ đọc JSON rồi đưa nguyên cho `apply_map` | `map50` | **bản nháp có sẵn** (`tool/fit_map.py` sinh ra) |
| P4 | `m28core.autoqc.run` | `run(name, pts50, config)` → list mã lỗi (chuỗi); mã bắt đầu bằng `guong`, `don_cuc` hoặc `diem_khong_hop_le` thì gợi ý "nen_gan_tay". Module tuỳ chọn | bước `autoqc` | chưa ai xác nhận |
| P4 | `runs/<run>/autoqc/autoqc.csv` | m28 ghi: `name,suggestion,n_flags,decision,reason,seconds,problems` (`suggestion` = `on`/`can_xem`/`nen_gan_tay`; `name` có đuôi `.png`) | `review` (excel, auto), P2 xếp hàng | chưa ai xác nhận |
| P4 | `m28core.push.push` | `push(run_dir, task_name, nhan_imgs, tay_imgs, xml_path, project=, prefix=, label_json=)`; đường ảnh là đường dẫn file đầy đủ; từ chối tên không bắt đầu `demo-`; tự ghi `push.json` | bước `push` | chưa ai xác nhận |
| P4 | `m28core.collect.collect` | `collect(args)` → `True` nếu xong (`args.task` list, `dry_run`, `skip_export`, `tag`) | lệnh `collect` | chưa ai xác nhận |
| P2 | `tool/review_app.py` | `python tool\review_app.py <run_dir> <reviewer>`; ghi `runs/<run>/review/triage_<reviewer>.csv` và `done.txt` khi bấm Xong; `launch(server_name="127.0.0.1", share=False)` | `review --review ui` | chưa ai xác nhận |
| P2/P4 | `triage_<Pk>.csv` | cột `name,decision,reason,seconds` (tên có hay không đuôi ảnh đều được; không tiêu đề thì đọc theo thứ tự cột) | `review`, `push` | chưa ai xác nhận |
| P1/P4 | `config/pipeline.json` | khoá `project` (mặc định `m28`), `prefix` (mặc định `demo-`) | `push` | chưa ai xác nhận |
| P4 | `config/face50_label.json` | label CVAT 50 điểm; m28 chỉ truyền đường dẫn cho `push` | `push` | chưa ai xác nhận |

## Đầu vào / đầu ra
- Vào: thư mục ảnh (hoặc danh sách ảnh WFLW + hộp mặt), `config/m28_config.json`.
- Ra: `runs/<run>/…` (ảnh chồng, cờ, `triage_<Pk>.csv`), task CVAT `demo-…`, file xuất `raw/<task>_<Pk>_<ngày>.xml`.

## Đã thử trên
- Test dữ liệu giả (`tests/`) trên Linux, Python 3.11, bằng landmarker/mapping/push/collect giả.
- **Ảnh WFLW thật, MediaPipe thật** (5/10/2026, Linux cloud, Python 3.11, mediapipe 1.0.1, `face_landmarker.task`
  float16; cần `libegl1`, `libgles2` trên Linux): bước `crop` + `mediapipe` (ảnh gốc + ảnh lật).
  - 616 mặt của `manifest.csv`, `--box wflw`: thấy mặt **592/616** (96,1%); 24 mặt không thấy (F 6, Tdev 3, Ttest 7,
    G 2, X 3, D 3) sau khi thử thêm viền xám; P 0/16. Chạy khoảng 50 giây trên CPU.
  - Tập giống R (train, ảnh một mặt, mặt lớn ≥ 25% cạnh ngắn; 40 mặt, seed 18), `--box auto`: **40/40** thấy mặt;
    hộp tự dò so với hộp WFLW có IoU trung vị 0,70, 2/40 mặt dưới 0,5. Xem bằng mắt: 478 điểm nằm đúng trên mặt.
- **Bản nháp ánh xạ 478→50 (P3 xác nhận/sửa)**: `tool/make_config.py` sinh `config/m28_config.json` (50 điểm chọn từ 98 điểm WFLW:
  viền cách một điểm 17, mày 5×2, mắt 4×2, mũi 5, môi 10; 21 R, 21 L, 8 M) và `data/gt50.json`; `tool/fit_map.py` khớp
  `config/map_mp50.json` (hình trung bình + ridge, k = 6, λ chọn trong {0,1; 1; 10; 100}) và ghi `data/mp50.json` cho mọi mặt;
  `tool/m28core/mapping.py` có `apply_map`; `tool/check_flip.py` kiểm phép lật. Chạy lại `make_config.py` không xoá `t_flip`,
  `tolerance`, `status`, `tmpl` đã có trong file. Bố cục 98 điểm và cặp đối xứng đã kiểm bằng script ngoài repo trên 5.931 mặt thẳng của
  WFLW train; ba người kiểm độc lập tìm ra và đã sửa lỗi bên R/L của môi dưới (WFLW 84 → `p46_lip_L`, 86 → `p48_lip_R`).
  - Kết quả trên 58 mặt F kiểm (số nhỏ, dễ hơn T-dev/T-test; dùng **trung vị**): NME chính (E điểm-điểm, C tới đường cong) trung vị
    **2,87%**, trung bình 3,80% IOD, 5,2% mặt hỏng (≥ 10%); NME phụ (điểm-điểm cả 50 điểm) 5,65% / 4,06% (đây là số ghi trong `map_mp50.json`
    kèm `nme_main_*`). λ chọn = 100 sát mép lưới (λ ~1000–3000 chỉ tốt hơn ~0,04 điểm %: giữ lưới theo kế hoạch). Hằng số bỏ lật ước
    lượng được `flip_width` = 512,97 (không phải 512: bỏ lật lệch ~1 px sang trái trên F, T-dev, T-test nếu dùng 512).
  - `python tool\check_flip.py --run <run>`: lật đáp án hai lần lệch ~0; WFLW 0 và 60 ở nửa trái ảnh cắt 616/616; lệch gốc/lật trung vị
    2,07% IOD trên 20 mặt thẳng F đầu tiên (tiêu chí kế hoạch < 3%: đạt), 2,36% trên mọi mặt thẳng F, **2,80% trên Tdev** (biên mỏng);
    đối chứng quên đổi tên theo cặp: 71%.
  - Khớp trên 235 mặt F (đã bỏ 7 mặt no_face và 1 mặt dò nhầm người từ 240 khớp ban đầu) thay vì 240/60 như kế hoạch; danh sách mặt
    khớp/đo/kiểm ghi trong `meta` của `map_mp50.json`. Mặt tham chiếu Procrustes = mặt đầu theo mã trong tập khớp.
  - `t_flip` để `null` theo kế hoạch (P2 chốt sau họp 12/10); **đề xuất cho P2** 0,0672 (quantile 0,85 lệch gốc/lật trên Tdev, đã tính với
    ánh xạ này). `tmpl` = trung bình đáp án gt98 của các mặt F pose = 0 (không lấy từ meanface.txt của PIPNet vì PIPNet không được vào `tool/`).
  - Quy ước khoá: `gt98.json`, `gt50.json` có đuôi `.png`; `pred478.json`, `mp50.json` không đuôi. 11 mặt ở các tập khác nằm trên cùng
    một ảnh gốc với một mặt F (WFLW tách theo mặt, không theo ảnh); ghi vào `so-quyet-dinh.md` nếu nhóm muốn tách theo ảnh.
- Chạy `all --box wflw --review auto --dry-run` trên 5 mặt F thật: ra XML 5 × 50 điểm, toạ độ khớp `mp50.json`.
- **Chưa chạy**: `autoqc` của P4, `push` thật, `collect`, `review_app.py`, Windows/cmd, Python 3.14, CVAT 2.77.0 (kể cả nhập được XML `<skeleton>` không), CSV do Excel lưu.
- Cập nhật sau thí nghiệm 14–15/10 và lượt chạy tập R (16–18/10): thời gian trước/sau, số nháp hỏng trang rà soát bắt được.

## Giới hạn
- Chỉ làm nháp cho mặt lớn nhất trong ảnh; ảnh nhiều người chọn "Gán tay".
- MediaPipe yếu với mặt nhỏ, nghiêng mạnh, bị che nhiều.
- Python 3.14 + mediapipe 1.0.1 mới thử trên một laptop; máy nào lỗi thì dùng Colab/Kaggle (không đưa
  dữ liệu khách hàng lên đó).

## Người viết
P1 (`m28.py`), P2 (model, trang rà soát), P3 (ánh xạ, đánh giá), P4 (CVAT, `push`/`collect`), P5 (thí nghiệm).
