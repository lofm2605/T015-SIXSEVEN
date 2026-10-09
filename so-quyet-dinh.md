# Sổ quyết định

Ghi lại những gì đội đã chốt, và **vì sao**. Ba tuần sau không ai còn nhớ vì sao box lại vẽ
kiểu này — người mới vào đội lại càng không.

**Quyết định đã ghi thì không sửa nội dung.** Đổi ý thì ghi một quyết định mới, và chuyển
trạng thái quyết định cũ thành *Bị thay bởi QĐ-xxx*. Nhờ vậy vẫn truy được vì sao các job
cũ được gán theo cách cũ.

> Mẫu trống để copy nằm cuối file.

## Danh sách

| Mã | Quyết định | Ngày | Xuất phát từ | Trạng thái |
|---|---|---|---|---|
| [QĐ-001](#qđ-001) | Tập chính là in-cabin (YawDD + DrivFace), bỏ WFLW, dự án phi thương mại | 06/10/2026 | Chủ repo | Hiệu lực |
| [QĐ-002](#qđ-002) | Ánh xạ 478→50 bằng chọn đỉnh MediaPipe trực tiếp | 06/10/2026 | QĐ-001 | Bị thay một phần bởi QĐ-003 (định nghĩa 50 điểm, config v2); chọn đỉnh trực tiếp vẫn hiệu lực |
| [QĐ-003](#qđ-003) | Định nghĩa 50 điểm DMS (7 nhóm, không viền hàm), trái/phải theo ảnh, config v3 | 07/10/2026 | QĐ-002 | Bị thay một phần bởi QĐ-004 (cách dựng label CVAT: bảy label theo nhóm, màu theo nhóm); phần còn lại hiệu lực |
| [QĐ-004](#qđ-004) | Tách label `face50` thành bảy label skeleton theo nhóm, mỗi nhóm một màu (bảng màu hình minh hoạ DMS) | 07/10/2026 | QĐ-003 | Hiệu lực |
| [QĐ-005](#qđ-005) | Bộ lọc dữ liệu train chỉ chuẩn bị dữ liệu (chưa train), kèm trang Thống kê chỉ số model và tốc độ gán | 08/10/2026 | Chủ repo | Bị thay một phần bởi QĐ-006 (trang Thống kê chỉ còn ba chỉ số, thiết kế hai nhóm độc lập); bộ lọc vẫn hiệu lực |
| [QĐ-006](#qđ-006) | Thí nghiệm hai nhóm độc lập (manual / assisted) thay cho ghép cặp; đồng hồ bấm giờ theo phiên thay facetimer; Thống kê chỉ ba chỉ số; gói kết quả cho nhóm trưởng | 09/10/2026 | Chủ repo | Hiệu lực (chờ P5 và mentor đồng ý trước 14/10); phần đồng hồ bổ sung bởi QĐ-007 (mỗi đợt một phiên) |
| [QĐ-007](#qđ-007) | Đồng hồ bấm giờ tính MỖI ĐỢT MỘT PHIÊN (giờ đợt này không lẫn vào đợt khác) | 09/10/2026 | Chủ repo | Hiệu lực (chờ P5 duyệt gói theo đợt) |

**Trạng thái:** Hiệu lực · Bị thay bởi QĐ-xxx · Huỷ (ghi lý do)

## QĐ-001

**Tập chính là in-cabin (YawDD + DrivFace), bỏ hoàn toàn WFLW, dự án phi thương mại**

- **Ngày:** 06/10/2026
- **Người tham gia:** chủ repo (chốt)
- **Xuất phát từ:** Họp/hỏi đáp trong phiên làm việc; catalogue đề tài ghi nguồn "WFLW / in-cabin"
- **Bối cảnh:** kế hoạch ban đầu dùng WFLW vì có đáp án 98 điểm sẵn. Chủ repo muốn dùng ảnh trong xe (in-cabin) và chuyển dự án sang phi thương mại.
- **Các phương án đã cân nhắc:**
  1. *Chỉ WFLW* — có đáp án sẵn, đo được NME và cờ dễ dàng, nhưng không phải ảnh trong xe. Loại.
  2. *WFLW để khớp ánh xạ + in-cabin để đo* — giữ được phép khớp 478→50, cần gán tay ~100–150 mặt in-cabin. Cân nhắc, không chọn.
  3. *Bỏ WFLW hoàn toàn, in-cabin YawDD + DrivFace* — **Chọn.** Không còn đáp án có sẵn: 50 điểm đặt trực tiếp lên đỉnh MediaPipe (không học), đáp án để đo chất lượng là nhãn nhóm gán tay trong CVAT.
- **Quyết định:** tập chính YawDD (video trong xe, trích khung hình) + DrivFace (606 ảnh, 4 tài xế, có hộp mặt, 5 điểm mốc, hướng nhìn). Dự án phi thương mại,
  nên giấy phép "dùng học thuật/nghiên cứu" chấp nhận được; không phát tán dữ liệu, không giao bên thứ ba. Phiên cloud được xử lý hai bộ này.
- **Việc phải làm theo:**
  - [ ] Cập nhật bản gốc kế hoạch trên Claude Docs (tab Kế hoạch, P1, P3, P5): bỏ WFLW, thay đường dữ liệu, mốc, tiêu chí đo
  - [ ] Dựng gói dữ liệu in-cabin (DrivFace đã tải thử được; YawDD cần mở host `skuld.cs.umass.edu`)
  - [ ] Thay phép khớp 478→50 bằng chọn đỉnh trực tiếp, kiểm bằng mắt trên mặt tài xế
  - [ ] Gán tay tập vàng (G) và tập đo bằng CVAT để lấy sai số chấp nhận và NME
  - [ ] Kiểm điều khoản YawDD, ghi vào `source-tool/m28-prelabel/nguon-du-lieu.md`
- **Trạng thái:** Hiệu lực

---

## QĐ-002

**Ánh xạ 478→50 bằng chọn đỉnh MediaPipe trực tiếp**

- **Ngày:** 06/10/2026
- **Người tham gia:** chủ repo (chốt), P3, P2, P4 (chờ duyệt)
- **Xuất phát từ:** QĐ-001
- **Bối cảnh:** bỏ WFLW thì không còn đáp án 50 điểm để học phép khớp; ridge học trên WFLW lệch ở hàm và lông mày trên mặt tài xế. So 5 điểm DrivFace: bản mới tốt hơn ở khoé miệng (8,6 và 4,9 so với 10,5 và 6,3% IOD), ngang ở mũi, hơi kém ở tâm mắt.
- **Các phương án đã cân nhắc:**
  1. *Giữ ridge WFLW.* Loại: học trên dữ liệu đã bỏ.
  2. *Học ridge trên nhãn in-cabin nhóm tự gán.* Chưa có nhãn; xét lại sau khi có tập gán tay.
  3. *Chọn đỉnh trực tiếp.* **Chọn.** Đơn giản, không cần đáp án; nhược điểm: viền L co vào má khi mặt quay trên ~25–30°.
- **Quyết định:** config version 2 (`mp_idx` thay `wflw`, `curve` là danh sách tên điểm); `config/mp_mirror478.json` là hoán vị gương; `flip_width` ước lượng không cần đáp án; công cụ WFLW dời vào `tool/legacy_wflw/`; đáp án đo là nhãn gán tay, đo bằng `tool/eval50.py`.
- **Việc phải làm theo:**
  - [ ] Duyệt đỉnh và `curve` p49/p50 (@P3)
  - [ ] Chốt `t_flip` ngày 12/10, đề xuất 0,0464 (@P2)
  - [ ] Dựng lại label CVAT bằng `face50_label.json` mới (@P4)
  - [ ] Cập nhật bản Claude Docs (chủ repo)
- **Trạng thái:** Bị thay một phần bởi QĐ-003 (định nghĩa 50 điểm, config v2); chọn đỉnh trực tiếp vẫn hiệu lực

---

## QĐ-003

**Định nghĩa 50 điểm DMS (7 nhóm, không viền hàm), trái/phải theo ảnh, config v3**

- **Ngày:** 07/10/2026
- **Người tham gia:** chủ repo (chốt), P3, P2, P4, P5 (chờ duyệt)
- **Xuất phát từ:** QĐ-002
- **Bối cảnh:** mục đích của công cụ là theo dõi người lái (DMS, Driver Monitoring System): cần mắt, miệng, lông mày, sống mũi. Viền hàm/cằm của 50 điểm cũ kém nhất trên mặt quay (đỉnh viền phía xa nằm
  trong má, không trên biên nhìn thấy) và không cần cho DMS. Quy ước bên cũ theo NGƯỜI trong ảnh (R = nửa trái ảnh) làm người gán dễ nhầm trái/phải khi nhìn ảnh.
- **Các phương án đã cân nhắc:**
  1. *Giữ 50 điểm cũ (config v2).* Loại: tốn 17 điểm cho viền hàm, bên theo người gây nhầm.
  2. *DMS cộng khung đầu (head box).* Không làm theo chủ repo: không đặt chỗ trống, không thêm trường dự phòng.
  3. *DMS 7 nhóm, bên theo bức ảnh.* **Chọn.** Phương pháp chọn đỉnh trực tiếp của QĐ-002 giữ nguyên, chỉ đổi tập điểm, tên và quy ước bên.
- **Quyết định:**
  - 50 điểm = `longmaytrai` 5, `longmayphai` 5, `songmui` 4, `mattrai` 8, `matphai` 8, `moingoai` 12, `moitrong` 8. Không viền hàm/cằm, không cánh mũi/chân mũi, không khung đầu.
  - Tên `<nhóm>_<k>` (k từ 1), thứ tự nhóm như trên cả trong config lẫn CVAT. Mày: `_1` đầu mày -> `_5` đuôi, `longmaytrai_k` <-> `longmayphai_k`. Mũi: `_1` giữa hai mắt -> `_4` chóp. Mắt (vòng kín): `_1` khoé ngoài,
    `_2.._4` mí trên vào trong, `_5` khoé trong, `_6.._8` mí dưới ra ngoài. Môi (vòng kín): `_1` khoé TRÁI ảnh, mép trên trái -> phải, khoé phải ảnh, mép dưới phải -> trái.
  - **Trái/phải theo BỨC ẢNH, không soi gương** (NGƯỢC với v2): `*trai` ở nửa trái ảnh, `*phai` ở nửa phải ảnh. Mã `side` giữ R/L/M nhưng R = nửa phải ảnh, L = nửa trái ảnh. Config có `side_convention: "image"`;
    công cụ từ chối config thiếu trường này.
  - Config `version: 3` thêm trường `group`; `region` giữ vùng thô brow/nose/eye/lip (không còn `jaw`, nên `nme_per_face.csv` mất cột `reg_jaw`, các cột còn lại giữ nghĩa); `iod_points` = [`mattrai_1`, `matphai_1`];
    `t_flip` và `tolerance` vẫn `null`. Map `map_mp50.json` lên `version: 3`.
  - Label CVAT: giữ MỘT skeleton `face50` đủ 50 sublabel tên mới (push, collect, eval50, QC đều giả định một skeleton mỗi ảnh); nhóm thể hiện bằng cạnh, màu theo bên của ảnh. Project CVAT dựng từ label cũ bị `push` từ chối rõ ràng.
  - `mp_mirror478.json` KHÔNG đổi (tính chất hình học của 478 đỉnh, không phụ thuộc tên điểm); `make_config.py --run` không còn ghi đè file gương trừ khi thêm `--learn-mirror`.
  - Bản chụp `de-tai-m28/` không sửa; `CLAUDE.md` và bản Claude Docs do chủ repo cập nhật (định nghĩa 50 điểm, "tham khảo bố cục 98 điểm WFLW", viền hàm, quy ước bên).
- **Việc phải làm theo:**
  - [ ] Duyệt đỉnh, quy ước tên/thứ tự, `curve`, `anchor`; đóng băng config v3 trước 12/10 (@P3, @P1)
  - [ ] Chốt `t_flip` ngày 12/10 với số đo trên định nghĩa mới (@P2)
  - [ ] Dựng lại project/label CVAT bằng `config/face50_label.json` mới, file sao lưu task, QC theo tên mới (@P4)
  - [ ] Viết lại guideline gán tay theo DMS và quy ước bên theo ảnh; cột báo cáo `nme_per_face.csv` (@P5)
  - [ ] Cập nhật bản Claude Docs và `CLAUDE.md` (chủ repo)
- **Trạng thái:** Bị thay một phần bởi QĐ-004 (cách dựng label CVAT: bảy label theo nhóm, màu theo nhóm); phần còn lại hiệu lực

---

## QĐ-004

**Tách label `face50` thành bảy label skeleton theo nhóm, mỗi nhóm một màu (bảng màu hình minh hoạ DMS)**

- **Ngày:** 07/10/2026
- **Người tham gia:** chủ repo (chốt), P4, P5 (chờ duyệt)
- **Xuất phát từ:** QĐ-003
- **Bối cảnh:** QĐ-003 dựng MỘT label skeleton `face50` đủ 50 sublabel, tô sublabel theo bên của ảnh (L xanh dương, R đỏ, M xanh lá). Chủ repo gửi hình minh hoạ DMS tô theo nhóm, rồi chỉ ra trong CVAT ("Draw new skeleton") rằng mình muốn **mỗi nhóm một label riêng**, mỗi label một màu như hình, chứ không phải một label `face50` duy nhất.
- **Các phương án đã cân nhắc:**
  1. *Một skeleton `face50`, tô sublabel theo bên của ảnh (QĐ-003).* Bên trái/phải thấy ngay, nhưng bảy nhóm lẫn màu và người vẽ phải đặt 50 điểm một lượt. Loại.
  2. *Một skeleton `face50`, chỉ đổi màu sublabel theo nhóm.* Giữ nguyên mọi chỗ "đúng một skeleton mỗi ảnh", nhưng CVAT vẫn chỉ có một label nên chấm màu của label và danh sách "Draw new skeleton" không theo nhóm; không đúng điều chủ repo yêu cầu. Loại (làm tạm trong buổi đầu của QĐ-004 rồi bỏ).
  3. *Bảy label skeleton, mỗi nhóm một, tên label = tên nhóm, màu của label và của sublabel = màu nhóm.* **Chọn.** Đúng yêu cầu; cặp trái/phải của mắt và lông mày khác màu nên bên của ảnh vẫn nhìn ra; mỗi nhóm có khuôn svg riêng, co giãn kín khung nên dễ đặt hơn khuôn cả mặt.
- **Quyết định:** bảy label `longmaytrai` #e74c3c, `longmayphai` #3498db, `songmui` #2ecc71, `mattrai` #e67e22, `matphai` #9b59b6, `moingoai` #1abc9c, `moitrong` #f1c40f (bảng `GROUP_COLOR` trong `tool/make_label.py`), 5 + 5 + 4 + 8 + 8 + 12 + 8 = 50 sublabel và 47 cạnh, mỗi sublabel vẫn kèm `low_conf`.
  Tên sublabel giữ nguyên `<nhóm>_<k>` (50 tên khác nhau), thứ tự theo config; nhóm của một điểm suy ra từ tên (`cvat_io.group_of_name`). `config/face50_label.json` giữ tên file và được sinh lại. Khuôn svg của mỗi label là `tmpl` của chính nhóm, co giãn vào khung 0–100.
  Mỗi mặt trong XML nháp và XML xuất có **bảy** `<skeleton>` (mỗi nhóm một, đúng điểm của nhóm). `cvat_io.merged_face` gom bảy skeleton lại thành một mặt 50 điểm; `push`, `collect`, `eval50`, `cvat_smoke` và QC đều đòi đúng một skeleton cho mỗi nhóm. Project CVAT còn label `face50` cũ bị `push` từ chối với thông báo nói rõ. Hình minh hoạ có khung "head (ước lượng minh hoạ)": đó chỉ là hình vẽ, **không** thêm khung đầu vào label hay config.
  Ảnh chồng (`overlays`, trang rà soát) cũng tô chấm theo màu nhóm để giống CVAT; vì màu đỏ/xanh cũ không còn dành cho low_conf, điểm `low_conf` là chấm to hơn có vòng trắng (`tool/m28core/mau_nhom.py`, một nguồn màu cho label, ảnh chồng và chú giải).
- **Cái giá:** người gán tay vẽ 7 skeleton mỗi mặt thay vì 1 (thêm thao tác chọn label), nên thời gian gán tay có thể đổi so với kế hoạch gốc. Hai điều kiện thí nghiệm bấm giờ dùng chung một cách dựng nên so sánh vẫn công bằng, nhưng P5 cần biết trước buổi ghép cặp 14–15/10 và có thể đo lại thời gian một mặt gán tay.
- **Việc phải làm theo:**
  - [ ] Dựng lại project/label CVAT bằng `config/face50_label.json` mới: CVAT lưu label và màu lúc tạo, project cũ giữ label `face50`; task dựng từ label cũ và file sao lưu của chúng phải làm lại (@P4 và mỗi người có CVAT riêng)
  - [ ] Chạy mục kiểm tra nhanh CVAT (`chay.bat`, mục 4) trên CVAT thật: lần đầu thử bảy label, nhập XML bảy skeleton và xuất lại (@P4)
  - [ ] Cập nhật guideline gán tay: mỗi mặt chọn lần lượt bảy label, mỗi lần đặt đủ điểm của nhóm (@P5)
- **Trạng thái:** Hiệu lực

## QĐ-005

**Bộ lọc dữ liệu train chỉ chuẩn bị dữ liệu (chưa train), kèm trang Thống kê chỉ số model và tốc độ gán**

- **Ngày:** 08/10/2026
- **Người tham gia:** chủ repo (chốt), P1, P2, P3, P4, P5 (chờ duyệt)
- **Xuất phát từ:** yêu cầu của chủ repo (phiên làm việc 08/10/2026)
- **Bối cảnh:** sau này đội cần dữ liệu train/finetune cho một model landmark KHÁC (MediaPipe không train được), lấy từ ảnh đã có nhãn sửa tay; đồng thời báo cáo và buổi demo cần số liệu của model và của quá trình gán (chất lượng nháp, cờ `low_conf`, tốc độ, số lượng, tiến độ). Dữ liệu đã nằm rải trong `runs\`, `raw\`, `final\`, `timing_P*.csv`, nhưng chưa có chỗ tổng hợp.
- **Các phương án đã cân nhắc:**
  1. *Không làm* — vẫn phải tự ghép dữ liệu bằng tay mỗi lần cần số hay bộ train; dễ lẫn manual với assisted, dễ rò rỉ người giữa train và test. Loại.
  2. *Lọc dữ liệu và train ngay* — MediaPipe không train được, máy đội không có GPU, repo chưa có bước train, và model đích chưa chọn: ngoài phạm vi. Loại.
  3. *Bộ lọc chỉ chuẩn bị dữ liệu, chưa train, kèm trang Thống kê.* **Chọn.** Công cụ chỉ đọc dữ liệu có sẵn, ghi dưới `outputs\` (ngoài git), không thêm gói, không thêm code train.
- **Quyết định:**
  - Một lớp đọc dùng chung (`tool\m28core\bang_mat.py`, bảng mặt: mỗi dòng một (lượt, mặt)) cho cả bộ lọc (`tool\loc_du_lieu.py`, tab **Lọc dữ liệu**) và Thống kê (`tool\thong_ke.py`, tab **Thống kê**); hai tab đặt trước **Cài đặt**.
  - **Tiêu chí lọc:** cờ `low_conf` (tổng và theo từng nhóm/vùng; nguồn cờ mặc định là `flags.json`, hoặc tính lại từ điểm số lật với `t_flip` cụ thể vì lượt chạy khi `t_flip = null` có mọi cờ = false), NME của nháp so với nhãn đã sửa, cờ manifest, quyết định rà và người rà, vệ sinh nhãn (đủ điểm, `low_conf` còn bật trong nhãn, độ lệch hai nhãn người).
  - **Chia theo `set` gốc, không rò rỉ người:** train = F, G, P, X, D; val = Tdev; test = Ttest (đúng cách chia theo người của `inc_ingest.py`), rồi kiểm lại trên chính bộ xuất bằng cột `subject`; một tài xế ở hai phần là lỗi, không ghi gì. Tiêu chí chọn ca khó chỉ áp lên train. Ttest là tập đo một lần: không dùng số trên Ttest để chỉnh ngưỡng lọc; Thống kê ẩn Ttest mặc định.
  - **Luật cứng không tắt được:** mặt nguồn không rõ (`khong_ro`: lượt Nạp ảnh hoặc không khớp manifest, có thể là ảnh khách hàng) luôn bị loại; mặt xoá mềm, mặt chưa có nhãn sửa tay, mặt `Bỏ` cũng bị loại.
  - **Tốc độ gán theo đúng giao thức P5** (`timing_P*.csv` của `facetimer.py`, trung bình nhân r_i, KTC 90% bootstrap seed 28, mục tiêu nhanh hơn ≥ 20% và ≥ 4/5 người có r_i < 1); ngoại lai và dòng gián đoạn được đánh dấu nhưng vẫn nằm trong chỉ số chính; giây rà soát là chỉ số khác (thời gian quyết định Nhận/Gán tay/Bỏ). manual và assisted luôn tách riêng; assisted chỉ là cận dưới của chất lượng nháp.
  - **Xuất tĩnh** (`outputs\thong_ke\<ngày-giờ>\`) không ảnh mặt, không mã tài xế, không đường dẫn tuyệt đối. Gói train (`outputs\train_sets\<tên>\`, có `README.md` ghi giấy phép và trích dẫn) chứa ảnh mặt người lái xe: dự án phi thương mại, chỉ dùng nội bộ nhóm, không phát tán, không giao bên thứ ba, không vào git hay chat AI.
- **Việc phải làm theo:**
  - [ ] Duyệt cách tính tốc độ, ngoại lai, giây rà soát và bố cục trang cho báo cáo (@P5)
  - [ ] Duyệt thống kê cờ, AUROC và `t_flip` dùng để tính lại cờ (@P2)
  - [ ] Xác nhận quy ước `raw\`/`final\`, tên task thí nghiệm (`m28-manual`, `m28-assisted`) và liên kết `push.json` (@P4)
  - [ ] Duyệt ánh xạ train/val/test theo `set` gốc; chốt có dùng Ttest làm test của model sau này không (@P1)
  - [ ] Duyệt NME theo nhóm và `tolerance` mặc định 3% IOD khi config còn null (@P3)
  - [ ] Cập nhật `CLAUDE.md` và bản Claude Docs về hai tab mới và luật cứng `khong_ro` (chủ repo)
- **Trạng thái:** Bị thay một phần bởi QĐ-006 (trang Thống kê chỉ còn ba chỉ số, thiết kế hai nhóm độc lập); bộ lọc vẫn hiệu lực

## QĐ-006

**Thí nghiệm hai nhóm độc lập (manual / assisted) thay cho ghép cặp; đồng hồ bấm giờ theo phiên thay facetimer; Thống kê chỉ ba chỉ số; gói kết quả cho nhóm trưởng**

- **Ngày:** 09/10/2026
- **Người tham gia:** chủ repo (chốt), P5 (chờ đồng ý: giao thức bấm giờ và luật kết luận), mentor (chờ đồng ý thiết kế mới, trước 14/10), P2 (trang rà soát), P3 (NME, ngưỡng sửa), P4 (`raw/`, tên file theo job, tên task)
- **Xuất phát từ:** yêu cầu của chủ repo sau khi xem trang Thống kê (QĐ-005) và chốt cách chia đội ngày 08/10/2026
- **Bối cảnh:** kế hoạch gốc ghép cặp theo người: mỗi Pk gán tay khối Xk (manual) và sửa nháp khối X(k+1) (assisted), P5 sửa X1, so sánh bằng trung bình nhân của r_i theo người. Chủ repo chia đội thành **hai nhóm**: một nhóm gán tay hoàn toàn, một nhóm dùng tool (sửa nháp), cả hai làm **cùng một bộ ảnh**; mỗi người chỉ làm một điều kiện. Chủ repo cũng muốn bấm giờ ngay trên trang (thay `facetimer.py` dòng lệnh), đo **cả phiên** từ lúc nạp ảnh lên tool đến lúc hoàn thành, và xuất một file kết quả để gửi nhóm trưởng tổng kết; trang Thống kê bốn nhóm số liệu thì quá nhiều số không dùng.
- **Các phương án đã cân nhắc:**
  1. *Giữ ghép cặp theo người và Thống kê bốn nhóm.* Loại: đội đã chia hai nhóm, không ai làm cả hai điều kiện; nhiều số không dùng.
  2. *Hai nhóm độc lập, đồng hồ đo từng mặt như facetimer, Thống kê giữ cờ và số lượng.* Loại: bắt người gán bấm mỗi mặt (dễ quên, Ctrl+C mất mặt đang làm); số thừa.
  3. *Hai nhóm độc lập, đồng hồ đo PHIÊN (bấm từng mặt chỉ là tuỳ chọn), Thống kê chỉ ba chỉ số, gói kết quả cho nhóm trưởng.* **Chọn.**
- **Quyết định:**
  - **Nhóm:** `config/nhom_thi_nghiem.json` (file mẫu trống, không đoán ai ở nhóm nào): `{"nhom": {"P1": "manual" | "assisted", ...}, "bo_anh": "<tên bộ ảnh chung>"}`. Người chưa có nhóm thì đồng hồ mặc định `assisted` và dòng bấm giờ ghi cờ `chua_co_nhom`. Thống kê kiểm hai nhóm làm cùng tên ảnh, báo nếu lệch.
  - **Đồng hồ** (`tool/dong_ho.py`, `dong_ho_ui.py`; **bỏ tab riêng theo chủ repo ngày 09/10/2026**, chỉ còn chip ⏱ ở đầu trang tự chạy khi bấm Nạp ảnh với MỘT nút Dừng/Tiếp tục; **Lưu số đo** (ghi timing và gói kết quả) và **Bỏ phiên đồng hồ** nằm trong hộp Đóng trang rà soát; sửa thời gian, bấm từng mặt, xuất lại gói còn trong logic và test nhưng không còn nút): đo cả phiên. Nguồn sự thật là đồng hồ phía server (`time.monotonic`), trạng thái ghi nguyên tử ra file nên đóng tab không mất; đóng trang thì tự tạm dừng. Nối với tab Nạp ảnh (bấm Nạp là đồng hồ chạy). Giây/mặt = giây phiên (không tính lúc tạm dừng) ÷ số mặt, đánh dấu `uoc_luong_chia_deu` trừ khi người gán bấm từng mặt. `outputs/timing/timing_<Pk>.csv` giữ đúng 12 cột facetimer, cột thêm nối cuối.
  - **Xong** ghi gói `outputs/ket_qua/ketqua_<Pk>_<DDMM>_<đợt>.zip` (+ `.json`): người, nhóm, đợt, số mặt, giây phiên, số lần tạm dừng, giờ bắt đầu/kết thúc và KẾT QUẢ theo mặt (tên ảnh, nhãn cuối 50 điểm; nhóm assisted thêm nháp, điểm đã sửa, NME nháp-so-nhãn-cuối); không ảnh, token, email, tên máy, đường dẫn tuyệt đối; có sha256 và số phiên bản định dạng. `tool/tong_ket.py` của nhóm trưởng kiểm, loại gói hỏng/trùng, gộp và tính ba chỉ số (chỉ cần gói, không cần ảnh hay CVAT).
  - **Ba chỉ số** (`m28core/so_sanh.py`): (1) NME của nháp, đáp án là nhãn gán tay của nhóm **manual** trên cùng ảnh (nhiều người thì trung bình theo tên điểm; ảnh chưa có đáp án thì không chấm), kèm NME của nhãn cuối nhóm assisted để kiểm "nhanh hơn mà nhãn không kém đi"; (2) tỉ lệ điểm phải sửa (nhóm assisted, ngưỡng mặc định 2% IOD, điểm xoá/ẩn tính là đã sửa); (3) giây/mặt mỗi nhóm (trung vị, trung bình nhân), % nhanh hơn của assisted so với manual (mục tiêu ≥ 20%), KTC 90% bằng cluster bootstrap (bốc người rồi bốc mặt trong người, seed 28, 2.000 lần); mỗi nhóm dưới 2 người thì chỉ có kết quả mô tả. Đạt khi cận dưới KTC ≥ 20%, Không đạt khi cận trên < 20%, còn lại Chưa kết luận. Mặt khởi động bị loại như P5; dòng gián đoạn, sửa tay, có cảnh báo, ngoại lai được đánh dấu và vẫn nằm trong chỉ số chính, kèm một dòng độ nhạy.
  - **Hạn chế (ghi trên trang):** tốc độ từng người khác nhau lẫn vào kết quả (nên có một đợt khởi động chung hoặc chia nhóm cân tốc độ); ít người mỗi nhóm thì khoảng tin cậy rất rộng; giây/mặt là ước lượng chia đều nếu không bấm từng mặt; đáp án NME cũng là nhãn người.
  - Tab **Lọc dữ liệu** và `bang_mat.py` giữ nguyên. `toc_do.py` (giao thức ghép cặp cũ của P5) không còn được trang dùng, chỉ giữ bộ đọc file và để đối chiếu với đoạn pandas của P5.
- **Việc phải làm theo:**
  - [ ] Đồng ý bỏ ghép cặp, luật Đạt/Không đạt mới, và quy ước giây/mặt ước lượng chia đều (@P5, mentor, trước 14/10)
  - [ ] Điền `config/nhom_thi_nghiem.json` khi cả đội chốt ai ở nhóm nào và tên bộ ảnh chung (chủ repo, nhóm trưởng)
  - [ ] Đổi câu hướng dẫn buổi thí nghiệm: "Đầu buổi khôi phục task của hôm nay, rồi bấm Nạp ảnh (đồng hồ tự chạy), và lúc xong chạy collect rồi bấm Lưu số đo ở hộp Đóng trang" và cho người gán gửi gói `outputs/ket_qua/*.zip` cho nhóm trưởng sau khi bấm Lưu số đo (@P5)
  - [ ] Duyệt ngưỡng sửa 2% IOD và cách tính điểm xoá/ẩn là đã sửa (@P3)
  - [ ] Xác nhận mẫu tên file theo job `<task>_<người>_<DDMM>_job<id>.xml` và task `demo-…` cho thí nghiệm (@P4)
  - [ ] Duyệt chip đồng hồ ở đầu trang và hộp Đóng trang (@P2)
  - [ ] Cập nhật `CLAUDE.md` (đã sửa đoạn Thí nghiệm) và bản Claude Docs: tab P5 còn ghi `facetimer.py` và ghép cặp, Kế hoạch còn "đủ 5 người" (chủ repo)
- **Trạng thái:** Hiệu lực (chờ P5 và mentor đồng ý trước 14/10)

## QĐ-007

**Đồng hồ bấm giờ tính MỖI ĐỢT MỘT PHIÊN (giờ đợt này không lẫn vào đợt khác)**

- **Ngày:** 09/10/2026
- **Người tham gia:** chủ repo (chốt), P5 (chờ đồng ý: dòng bấm giờ và gói kết quả theo đợt), P2 (chip, hộp Đóng trang, thẻ đợt)
- **Xuất phát từ:** chủ repo dùng thử trang thật và báo "đồng hồ đang sai vì không phân ra cho mỗi đợt"
- **Bối cảnh:** QĐ-006 đo "cả phiên" nhưng mỗi người chỉ có MỘT phiên: nạp đợt thứ hai khi phiên của đợt đầu còn đó thì phiên cũ được giữ nguyên, chip vẫn ghi đợt đầu và giờ làm đợt hai bị cộng vào đợt đầu (file trạng thái thật của chủ repo chỉ có một phiên "Nap1" dù đã có thêm đợt NAP_002). Gói kết quả đã đặt tên theo đợt (`ketqua_<Pk>_<DDMM>_<đợt>`), nháp và nhãn cũng lấy theo đợt, nên số đo phải theo đợt mới khớp.
- **Các phương án đã cân nhắc:**
  1. *Nạp đợt mới thì tự lưu phiên cũ.* Loại: lúc đó chưa chạy `collect` nên gói thiếu nhãn, và giao diện không còn nút xuất lại gói.
  2. *Giữ MỘT phiên, chia giờ cho từng đợt bên trong theo mốc chuyển trang.* Loại: phải nhân đôi cảnh báo, tạm dừng, dòng CSV và gói theo đợt bên trong một phiên; mốc "chuyển" không rõ khi Upload & Continue.
  3. *Mỗi (người, đợt) một phiên, một tệp trạng thái mỗi người, mỗi người chỉ một phiên chạy tại một lúc.* **Chọn.**
- **Quyết định:**
  - Phiên theo khoá **(người, đợt)**: mỗi đợt có giây, số lần tạm dừng, cảnh báo, dòng `timing_<Pk>.csv` (cột `dot`, `phien` riêng) và gói `ketqua_<Pk>_<DDMM>_<đợt>.zip` riêng. Bắt đầu hoặc tiếp tục một phiên thì phiên đang chạy ở đợt khác của người đó tự tạm dừng (giữ nguyên giây).
  - **Upload & Open:** đồng hồ chuyển sang đợt mới ngay. **Upload & Continue** lúc người đó đã có đồng hồ ở đợt khác: đồng hồ cũ giữ nguyên, đợt mới **chờ** ở 00:00 (nút **Start**); chưa có đồng hồ nào thì chạy ngay như trước.
  - **Chip** theo phiên đang chạy, không thì theo đợt của trang (không mượn giờ đợt khác), giờ các đợt khác ghi mờ cạnh chip và trên thẻ ở tab Các đợt. **Chuyển trang** sang đợt khác lúc đồng hồ đang chạy: đồng hồ cũ tạm dừng, đợt mới đã có phiên thì chạy tiếp, chưa có thì không tự tạo.
  - **Hộp Đóng trang:** từ hai đợt trở lên có ô "Đợt cần lưu / bỏ"; **Save timing** và **Discard session** chỉ tác động đợt đang chọn, nhắc `collect` theo task của đợt đó.
  - Tệp `outputs/timing/dang_chay_<Pk>.json` chứa các phiên theo đợt (`phien_ban_tep` 2); tệp cũ một phiên vẫn đọc được. Giờ đã cộng dồn trong phiên cũ không tách ngược được.
- **Việc phải làm theo:**
  - [ ] Đồng ý dòng bấm giờ và gói theo đợt (mỗi đợt một gói, nhóm trưởng nhận nhiều gói của một người) (@P5, mentor, trước 14/10)
  - [ ] Duyệt chip có giờ đợt khác ghi mờ, ô chọn đợt trong hộp Đóng trang và chip giờ trên thẻ đợt (@P2)
  - [ ] Kiểm `thong_ke` / `tong_ket` với một người có hai gói (hai đợt) khi có số đo thật (@P5)
- **Trạng thái:** Hiệu lực (chờ P5 duyệt gói theo đợt)

## Mẫu để copy

```markdown
## QĐ-NNN

**Quyết định trong một dòng**

- **Ngày:** dd/mm/yyyy
- **Người tham gia:** @ (chốt), @, @
- **Xuất phát từ:** [P-NNN](problem-backlog.md#p-nnn) | Họp tuần NN | …
- **Bối cảnh:** vì sao phải quyết định
- **Các phương án đã cân nhắc:**
  1. *Phương án* — ưu / nhược. Loại hoặc **Chọn.**
  2. *Phương án* — ưu / nhược. Loại hoặc **Chọn.**
- **Quyết định:** đủ rõ để người không dự họp vẫn làm đúng
- **Việc phải làm theo:**
  - [ ] việc (@người phụ trách)
- **Trạng thái:** Hiệu lực
```

Nhớ thêm một dòng vào bảng **Danh sách** ở đầu file, và đóng mục P-xxx tương ứng trong backlog.
