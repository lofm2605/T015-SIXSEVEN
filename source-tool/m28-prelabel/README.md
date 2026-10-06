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
├── tool/          m28.py, m28core/ (steps, push, collect, cvat_io, loai_tru, dang_chay, phan_loai…), review_app.py, day_cvat.py,
│                  dot_anh.py, dot_ui.py, nap_anh.py, ca_kho.py, cai_dat.py, cai_dat_ui.py, cai_dat_thu.py, make_label.py (giao cho khách: không torch, không ảnh)
├── config/        m28_config.json (50 điểm), pipeline.json (không có bí mật), face50_label.json (sinh bằng make_label.py)
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
  `NAP_001`, `NAP_002`… → **Bắt đầu chuẩn bị**. Trang chạy `python tool\m28.py prepare --run <lượt> --images runs\<lượt>\inbox --box auto` bằng tiến trình con,
  hiện bước (1–6/6), thanh tiến độ và log. **Huỷ** dừng tiến trình; **Thử lại** chạy lại đúng lệnh trên lượt đó (bước đã xong được bỏ qua).
  Xong thì hiện tóm tắt (mặt dùng được, không thấy mặt, vào hàng đợi rà, lệnh `push` gợi ý) và nút **Rà lượt này**: trang tự chuyển sang rà lượt mới.
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
  Gói chỉ có `manifest.json`, `ca_kho.csv`, `anh/<lượt>__<tên>.jpg` (ảnh chồng, cạnh dài ≤ 480 px, JPEG q72, không EXIF). Ảnh chỉ kèm cho lượt **WFLW**
  (không có `inbox/` và mọi mặt có trong `data/manifest.csv`); lượt không rõ nguồn (có thể là ảnh khách hàng) mặc định chỉ xuất ca, không kèm ảnh. Tối đa 500 ca và 20 MB mỗi gói.
- **Tab Họp team (người tổ chức, ví dụ P5):** `python tool\review_app.py --nap P5`. Tạo phiên (`outputs/ca_kho/hop_<ddmm>/`, lưu `hop.json` nên mở lại làm tiếp được),
  kéo thả nhiều gói, xem bảng kết quả từng gói (nhập được / lỗi kèm lý do / đã nhập rồi). Gói không bao giờ được giải nén ra đĩa: chỉ đọc mục `manifest.json`, `ca_kho.csv`, `anh/*.jpg`,
  giới hạn byte thật khi giải nén (chống zip bomb), ảnh mã hoá lại. Họp trên lưới ảnh (nhóm theo loại / người / trạng thái, lọc, tìm chữ), đặt trạng thái Mở / Đang bàn / Đã chốt,
  quyết định, người phụ trách, loại backlog, mục guideline; **Trình chiếu** (← → đổi ca, Esc thoát). Cùng một mặt WFLW (cùng tên ảnh) do nhiều người đánh dấu thì ghi chú hiện cạnh nhau.
  **Xuất biên bản**: `bien_ban_<ddmm>.md` (điền sẵn mục P-NNN, QĐ-NNN và dòng bảng Danh sách đúng mẫu `problem-backlog.md`, `so-quyet-dinh.md`; số tiếp theo đọc từ hai file đó) và `tong_hop_<ddmm>.csv`.
  **Code không bao giờ ghi vào hai file đó**: người tổ chức tự chép các khối vào rồi commit.
- Mã loại: SWAP, MIRROR, COLLAPSE, MISPLACED, OCC_FLAG (lỗi đặt điểm, như xem chéo 16/10), RULE, GL_CHUA_NOI, GL_MO_HO, GL_MAU_THUAN, CONG_CU, KHAC.
  Lỗi đặt điểm mặc định không vào backlog (người tổ chức đổi được).
- Gói chứa ảnh mặt người: chỉ gửi trong đội, không đăng công khai, không đưa vào chat AI, không commit (`outputs/` và `*.zip` đã bị `.gitignore` chặn).

## Tab Cài đặt (CVAT, người rà, đường dẫn, cờ low_conf)
Tab cuối của trang rà soát (`tool\cai_dat.py` logic, `tool\cai_dat_ui.py` giao diện, `tool\cai_dat_thu.py` tiến trình con thử kết nối). Năm khung:
- **CVAT:** `Link CVAT`, `Token CVAT` (ô password, rỗng sau khi Lưu, chỉ còn dạng `••••3456`; nút **Hiện / ẩn** đổi kiểu ô ngay ở trình duyệt), `Tổ chức` (tuỳ chọn),
  hộp **Nhớ trên máy này** (TẮT mặc định), nút **Lưu**, **Thử kết nối CVAT**, **Quên token** (có hộp xác nhận). Dòng trạng thái: `○ Chưa có link/token`, `○ Chưa thử`,
  `● Đã kết nối (thử lúc …)`, `● Lỗi: <nguyên nhân>`, kèm nguồn (từ biến môi trường / đã lưu trên máy / nhập trong phiên này). Lưu bị từ chối khi đang đẩy hay xoá task
  (tiến trình con đang dùng token hiện tại) và khi trang đang đóng. Lưu xong, khung Đẩy lên CVAT và tab Các đợt thấy giá trị mới ngay (nút Đẩy mở khoá, không cần mở lại cmd).
- **Người rà:** lưu tên mặc định. Lượt đang mở vẫn ghi `triage_<tên cũ>.csv` (phần rà dở nằm ở file đó); tên mới dùng **từ lượt kế tiếp** (Rà lượt này, chuyển đợt).
- **Đường dẫn:** thư mục `WFLW_images` và file `face_landmarker.task`, mỗi ô có **Kiểm** (tồn tại, đọc được, đếm ảnh có giới hạn 5.000 file / 2 giây, 3 tên mẫu; model: kích thước, đuôi `.task`, là zip) và **Lưu**.
  Tab Nạp ảnh dùng model đã cài (`--model`); thư mục WFLW được thêm `--images` vào lệnh `push` của lượt chạy bằng lệnh trên ảnh WFLW khi ảnh gốc không còn ở đường dẫn cũ (chỉ khi cần).
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
- **Lưới ảnh** (bấm tên đợt hoặc **Xem ảnh**, 24 ảnh mỗi trang): ảnh gốc trong `inbox\` (đợt nạp) hoặc ảnh cắt (đợt từ WFLW), kèm tên, tên gốc, trạng thái (Nhận / Gán tay / Bỏ / Chưa rà / Không thấy mặt / Không dùng được).
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
  tìm project theo tên (hơn một thì dừng; chưa có thì tạo từ `face50_label.json`; có rồi thì kiểm label `face50` đủ 50 sublabel đúng tên) → dừng nếu đã có task cùng tên trong project → `create_from_data` (`spec={"name","project_id"}` không labels, `ResourceType.LOCAL`,
  `image_quality` 95, `use_cache` True, `job_file_mapping` = các nhóm `job_size` mặt Nhận theo thứ tự + **một job Gán tay riêng ở cuối**; không dùng `sorting_method`, `segment_size`, `annotation_path`) → kiểm số job → kiểm tên frame khớp tên ảnh trong XML
  (khác thứ tự thì ghi `runs\<lượt>\xml\prelabel_cvat.xml` với `id` ảnh ghép theo **tên**, không sửa `prelabel.xml`) → `import_annotations("CVAT 1.1", …)` **đúng một lần, chỉ khi task còn 0 nhãn** → `export_dataset("CVAT for images 1.1", check.zip, include_images=False)` → kiểm mỗi mặt Nhận có skeleton
  `face50` đủ 50 tên điểm kèm `low_conf`, mặt **Gán tay có nháp** có đúng một skeleton `face50` đủ 50 điểm với **mọi** `low_conf = true`, mặt **Gán tay ảnh trống** không có nhãn. Dòng cuối: `push xong: task <tên> id <id>, <n> job (<a> Nhận, <b> Gán tay), <url>`.
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

## Chạy test
```bat
python -m pytest tests -q
```
Test chỉ dùng dữ liệu giả (ảnh ngẫu nhiên, landmarker/mapping giả, **CVAT giả** ở `tests\fake_cvat\cvat_sdk\`); không cần mediapipe, CVAT thật hay mạng.
`tests\test_push.py` thử push/collect/xoá task bằng gói `cvat_sdk` giả (giữ "server" trong bộ nhớ, ghi mọi lời gọi, giả lỗi theo lệnh) và so từng lời gọi với chữ ký của cvat-sdk **thật** nếu import được
(`pip install cvat-sdk==2.77.0`, hoặc đặt `M28_REAL_CVAT_SDK_PATH=<thư mục chứa gói cvat_sdk>`; không có thì bài đó `skip`). `tests\test_gan_tay.py` thử Gán tay có nháp (phân loại, XML, push với CVAT giả, tương thích `push.json` cũ, collect, chữ trên trang). `tests\test_make_label.py` thử label skeleton. `tests\test_dot_anh.py` thử tab Các đợt, xoá mềm,
nút Đẩy, PushJob/DeleteTaskJob. `tests\test_cai_dat.py` thử tab Cài đặt (lưu/nạp/quên, quyền file, ưu tiên nguồn, kiểm link/token/đường dẫn, t_flip, thử kết nối bằng tiến trình con với CVAT giả, tiền kiểm redirect bằng http.server cục bộ, không rò token); `tests\conftest.py` trỏ `M28_CONFIG_DIR` vào thư mục tạm cho mọi test. `tests\test_review_app.py` thử phần logic của trang rà soát mà không cần gradio hay trình duyệt. Kiểm thử trên trình duyệt thật
(tuỳ chọn, cần playwright, không nằm trong requirements): `python tests\e2e_review_ui.py --work <thư mục có runs\F5 và runs\ALL616> --shots <thư mục ảnh chụp>`
(pha F thử tab Nạp ảnh bằng ảnh WFLW thật: thêm `--wflw <WFLW_images>` nếu không nằm cạnh thư mục work) và
`python tests\e2e_dot_push.py --work <thư mục có config\ và face_landmarker.task> --wflw <WFLW_images> --shots <thư mục ảnh chụp>` (nạp ba đợt Khoi, Nam, Cuong bằng MediaPipe thật, xoá mềm, rà, đẩy lên CVAT giả, xoá task, màn 1440 và 420 px) và
`python tests\e2e_cai_dat.py --work <…> --wflw <WFLW_images> --shots <thư mục ảnh chụp>` (tab Cài đặt, bảy pha A–G, xem đầu file).

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
| P4 | `m28core.push.push` | `push(run_dir, task_name, nhan_imgs, tay_imgs, xml_path, project=, prefix=, label_json=, *, resume=False)` trả đường dẫn `check.zip`; đường ảnh là đường dẫn file đầy đủ; ảnh trong `tay_imgs` có `<image>` trong `xml_path` là Gán tay **có nháp** (mọi điểm `low_conf=true`), không có thì là ảnh trống; từ chối tên không bắt đầu `demo-`; tự ghi `push.json`; thêm `cleanup(run_dir, prefix=, confirm_name=)` / `delete_task(...)` | bước `push` | **bản đầu có sẵn** (`tool/m28core/push.py`), **chưa thử trên CVAT thật**; P4 xác nhận |
| P4 | `m28core.collect.collect` | `collect(args)` → `True` nếu xong (`args.task` list, `dry_run`, `skip_export`, `tag`, `reviewer`) | lệnh `collect` | **bản đầu có sẵn** (`tool/m28core/collect.py`), **chưa thử trên CVAT thật**; P4 xác nhận |
| P2 | `tool/review_app.py` | `python tool\review_app.py <run_dir> <reviewer>`; ghi `runs/<run>/review/triage_<reviewer>.csv` và `done.txt` khi bấm Xong; `launch(server_name="127.0.0.1", share=False)` | `review --review ui` | **bản nháp có sẵn** (`tool/review_app.py`, xem mục Trang rà soát), P2 xác nhận |
| P2/P4 | `triage_<Pk>.csv` | cột `name,decision,reason,seconds` (tên có hay không đuôi ảnh đều được; không tiêu đề thì đọc theo thứ tự cột). Dòng sau đè dòng trước; `decision` rỗng (dòng Hoàn tác về chưa rà) nghĩa là chưa rà | `review`, `push` | chưa ai xác nhận |
| P1/P4 | `config/pipeline.json` | khoá `project` (mặc định `m28`), `prefix` (mặc định `demo-`), `cvat_version` (2.77.0), `job_size` (8) | `push`, `collect` | **bản đầu có sẵn** (`config/pipeline.json`), chưa thử trên CVAT thật |
| P4 | `config/face50_label.json` | label skeleton `face50` (50 sublabel theo config, checkbox `low_conf`, svg khung 0–100); do `tool/make_label.py` sinh, `push` dùng để tạo project | `push` | **bản đầu có sẵn** (`tool/make_label.py`), **chưa thử trên CVAT thật** |
| P2/P4 | `m28core.qc.run` | `run(xml_paths, outputs_dir)` → chuỗi tóm tắt hoặc `None`; module tuỳ chọn, `collect` gọi nếu có | `collect` | chưa ai xác nhận |

## Đầu vào / đầu ra
- Vào: thư mục ảnh (hoặc danh sách ảnh WFLW + hộp mặt), `config/m28_config.json`.
- Ra: `runs/<run>/…` (ảnh chồng, cờ, `triage_<Pk>.csv`, `push\manual_list.txt` (loại `co_nhap`/`anh_trong`), `ca_kho.csv`), `outputs/ca_kho/` (gói họp, phiên họp, biên bản), task CVAT `demo-…`, file xuất `raw/<task>_<Pk>_<ngày>.xml`.

## Đã thử trên
- **Ca khó và họp team** (6/10/2026, Linux cloud, Python 3.11, Gradio 6.29.1, Chromium headless): `tests/test_ca_kho.py` (88 test, gồm zip độc hại, biên bản so khớp mẫu) và `tests/e2e_ca_kho.py` (đánh dấu, tab Ca khó, xuất/tải gói, nhập gói, lưới, trình chiếu, mở lại phiên, biên bản). Chưa thử: Windows/cmd, Python 3.14, kéo thả bằng chuột thật, toàn màn hình thật, Excel mở CSV.
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
  - Khớp trên 235 mặt F (đã bỏ 4 mặt no_face và 1 mặt dò nhầm người từ 240 khớp ban đầu; 58 mặt kiểm sau khi bỏ 2 mặt no_face) thay vì 240/60 như kế hoạch; danh sách mặt
    khớp/đo/kiểm ghi trong `meta` của `map_mp50.json`. Mặt tham chiếu Procrustes = mặt đầu theo mã trong tập khớp.
  - `t_flip` để `null` theo kế hoạch (P2 chốt sau họp 12/10); **đề xuất cho P2** 0,0672 (quantile 0,85 lệch gốc/lật trên Tdev, đã tính với
    ánh xạ này). `tmpl` = trung bình đáp án gt98 của các mặt F pose = 0 (không lấy từ meanface.txt của PIPNet vì PIPNet không được vào `tool/`).
  - Quy ước khoá: `gt98.json`, `gt50.json` có đuôi `.png`; `pred478.json`, `mp50.json` không đuôi. 11 mặt ở các tập khác nằm trên cùng
    một ảnh gốc với một mặt F (WFLW tách theo mặt, không theo ảnh); ghi vào `so-quyet-dinh.md` nếu nhóm muốn tách theo ảnh.
- Chạy `all --box wflw --review auto --dry-run` trên 5 mặt F thật: ra XML 5 × 50 điểm, toạ độ khớp `mp50.json`.
- **Trang rà soát** (`tool/review_app.py`, 5/10/2026): Gradio 6.29.1, Python 3.11, Linux cloud, Chromium headless qua Playwright 1.56.0; trên `runs\F5` thật (5 mặt) và
  lượt 616 mặt WFLW (24 mặt không có nháp). Đã thử: phím tắt, hoàn tác, đóng giữa chừng (kill) rồi mở lại, màn 1440x900 và 800x900, chế độ tối (`?__theme=dark`),
  lỗi ghi file (giả lập), nút Xong (dải xanh, tải lại một lần, trang vẫn chạy) rồi nút Đóng trang rà soát (mã thoát 0) và đi tiếp trong `m28.py review` rồi `push --dry-run`, không có request ra ngoài 127.0.0.1 dù đặt proxy chết.
  Số đo trên 616 mặt (CPU cloud, lúc nguội, chưa có ảnh nhỏ nào): từ lệnh chạy đến khi lưới hiện ảnh khoảng 6,5 giây (nạp Gradio chiếm khoảng 4,5 giây), mỗi quyết định
  trung vị 0,11 giây, đổi trang lần đầu tối đa 0,61 giây. `tests\e2e_review_ui.py` tự đo lại các số này.
- **Tab Nạp ảnh** (6/10/2026, `tool/nap_anh.py` + `review_app.py`): Linux cloud, Python 3.11, Gradio 6.29.1, mediapipe 1.0.1, Chromium qua Playwright. Pha F của `tests\e2e_review_ui.py`:
  thả 12 file (6 ảnh WFLW thật, tên có dấu/đuôi hoa, hai ảnh cùng tên, PNG xám, file chữ đổi đuôi, ảnh trùng; `set_input_files`, không phải kéo chuột thật), prepare thật bằng MediaPipe, Huỷ/Thử lại,
  "Rà lượt này" (relaunch cùng cổng, lượt cũ y nguyên), thiếu model, chế độ `--nap`. **Chưa thử**: Windows/cmd, Python 3.14, relaunch cùng cổng trên Windows, kéo thả bằng chuột thật,
  ảnh > 25 MB thật, đường dẫn dự án có dấu tiếng Việt (`cv2.imread` trên Windows không đọc được đường dẫn Unicode; tên ảnh đã ASCII nhưng thư mục dự án thì không).
- **Đẩy lên CVAT, tab Các đợt, xoá mềm, xoá task** (6/10/2026): Linux cloud, Python 3.11, Gradio 6.29.1, mediapipe 1.0.1, Chromium qua Playwright, ảnh WFLW thật, **CVAT GIẢ** (không phải server thật). `tests\e2e_dot_push.py`:
  nạp ba đợt Khoi, Nam, Cuong (có ghi chú), thẻ đợt, xoá mềm/khôi phục/dọn thùng rác ảnh của Nam (Huỷ, Esc, Enter ở Huỷ không xoá), rà Khoi, nút Đẩy (khoá khi còn mặt chưa rà; hộp xác nhận; Huỷ/Esc; đẩy; thẻ kết quả; không đẩy lần hai),
  cảnh báo CVAT khi xoá ảnh của đợt đã đẩy, xoá task (gõ tên + tick; Huỷ/Esc không gọi xoá; xoá đúng một lần; đẩy lại được), xoá cả đợt Cuong và khôi phục, trang không có biến CVAT (hướng dẫn `set`), phím tắt không chạy ở tab Các đợt,
  màn 1440 và 420 px, token giả không lộ trong HTML/log/`push.json`. **Chưa thử**: server CVAT thật (cả `push`, `collect`, xoá task, label skeleton), Windows/cmd, Python 3.14.
- **Chưa chạy**: `autoqc` của P4, `push` thật, `collect` thật, trang rà soát trên Windows/Python 3.14/trình duyệt thật có giao diện/máy có proxy công ty/Excel khoá file thật, Windows/cmd, Python 3.14, CVAT 2.77.0 (kể cả nhập được XML `<skeleton>` không), CSV do Excel lưu.
- Cập nhật sau thí nghiệm 14–15/10 và lượt chạy tập R (16–18/10): thời gian trước/sau, số nháp hỏng trang rà soát bắt được.

## Rủi ro: chưa thử trên CVAT thật
Cloud không có CVAT. `push`, `collect`, xoá task và label `face50` chỉ được thử bằng CVAT giả; chữ ký các lời gọi SDK đã đối chiếu với cvat-sdk 2.77.0 thật (`tests\test_push.py::test_signatures_match_real_sdk`) và định dạng label/XML đối chiếu với mã nguồn CVAT v2.77.0
(đọc từ GitHub, tag `v2.77.0`), nhưng **chưa có server nào xác nhận**. Khi có CVAT 2.77.0, kiểm các giả định sau (mỗi mục đều có thể làm `push` lỗi, và lỗi luôn dừng có thông báo, không tạo task thứ hai):
1. **Xác thực**: `make_client(url, access_token=token)` (đúng chữ ký 2.77.0; `Client.login` gán `configuration.access_token`, chưa kiểm server nhận Personal Access Token theo cách đó). Token sai/hết hạn → HTTP 401/403 → thông báo "tạo lại token".
2. **Label skeleton** (`tool\make_label.py`): `projects.create({"name", "labels": [...]})` nhận danh sách label có `type: "skeleton"`, `sublabels` (type `points`, màu theo bên R/L/M, thuộc tính checkbox `low_conf`), `svg` khung `0 0 100 100` (cvat-ui) với `data-label-name="<tên>"` và **không có** `data-label-id`
   (server đổi `data-label-name` thành `data-label-id` khi tạo — `serializers.py`, đã đọc), `data-element-id` = `data-node-id` = 1..50 (cvat-ui dùng `data-element-id` cho cả hai). Cạnh: chỉ nối hai điểm liền nhau trong cùng `line` của config (+ điểm cuối về đầu với line `closed`): 44 cạnh.
   Chưa kiểm: CVAT hiện đúng 50 điểm và cạnh, checkbox `low_conf` nằm trên từng điểm, màu hiển thị, và `Project.get_labels()` trả `sublabels` lồng trong label `face50` (`check_project_labels` chấp nhận cả dạng phẳng `has_parent`).
3. **`job_file_mapping`**: `create_from_data(..., data_params={"image_quality": 95, "use_cache": True, "job_file_mapping": [[tên ảnh…], …]})`. Theo `cvat/apps/engine/task.py` v2.77.0: mapping **không** dùng chung với `sorting_method` khác lexicographical, `segment_size`, `start_frame`, `stop_frame`, `frame_filter`, `filename_pattern`;
   tool không truyền các khoá đó. Tên trong mapping phải đúng **basename** ảnh tải lên (SDK gửi `client_files` bằng đường dẫn tuyệt đối; chưa kiểm server lấy basename). Job tạo theo đúng độ dài từng nhóm (`push` so lại với `Task.get_jobs()`, lệch thì ghi `canh_bao` trong `push.json`, không xoá task).
4. **Thứ tự frame**: theo mã nguồn, với mapping thì frame xếp theo thứ tự nối các nhóm (Nhận trước, Gán tay sau). `push` vẫn đọc `get_frames_info()` và, nếu khác thứ tự XML, ghi `prelabel_cvat.xml` với `id` ảnh theo frame thật (ghép theo tên). Tên frame trên server khác tên file thì `push` dừng (task giữ, `--cleanup` để xoá).
5. **Nhập nhãn**: `import_annotations("CVAT 1.1", xml)` với `<skeleton label="face50">` chứa 50 `<points label=… occluded="0" outside="0">` kèm `<attribute name="low_conf">`; loader trong `dataset_manager/formats/cvat.py` đòi `occluded`, `outside`, `points` trên từng điểm (đã đọc). Chưa kiểm server nhận file có đủ 50 điểm skeleton, và rằng `id` ảnh trong XML không quan trọng bằng `name`.
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
- Python 3.14 + mediapipe 1.0.1 mới thử trên một laptop; máy nào lỗi thì dùng Colab/Kaggle (không đưa
  dữ liệu khách hàng lên đó).

## Người viết
P1 (`m28.py`), P2 (model, trang rà soát), P3 (ánh xạ, đánh giá), P4 (CVAT, `push`/`collect`), P5 (thí nghiệm).
