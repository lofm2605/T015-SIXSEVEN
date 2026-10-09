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
| [QĐ-005](#qđ-005) | Bộ 200 ảnh chung cho hai nhóm MANUAL / ASSISTED: chọn theo độ khó khi gán 50 điểm DMS, hai gói A/B, nháp thống nhất, PNG | 09/10/2026 | Chủ repo | Hiệu lực |

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

**Bộ 200 ảnh chung cho hai nhóm MANUAL / ASSISTED: chọn theo độ khó khi gán 50 điểm DMS, hai gói A/B, nháp thống nhất, PNG**

- **Ngày:** 09/10/2026
- **Người tham gia:** chủ repo (chốt), nhóm trưởng, P5, P4 (chờ duyệt)
- **Xuất phát từ:** yêu cầu chủ repo ngày 09/10/2026: đội thử gán 50 điểm (định nghĩa DMS, QĐ-003, bảy label skeleton QĐ-004) và thử tool trên một bộ ảnh mới; đội chia hai nhóm, MANUAL gán tay hoàn toàn và ASSISTED dùng tool (sửa nháp).
- **Bối cảnh:** gói 616 mặt của đội đã có kèm manifest ghi nguồn và cờ; thành viên có thể đã gán thử vài mặt trong đó (quen mặt thì làm nhanh hơn), và ảnh cắt trùng từng byte thì tra ngược được nguồn. Muốn so hai nhóm thì phải cùng ảnh; muốn thử gán thì phải phủ mọi độ khó, kể cả kiểu hiếm (mặt nghiêng mạnh, tay che, kính râm, ảnh tối, ngáp rộng).
- **Các phương án đã cân nhắc:**
  1. *Lấy 200 mặt trong gói 616.* Nhanh, nhưng thành viên quen ảnh và ảnh tra ngược được; các kiểu khó hiếm. Loại.
  2. *Mỗi nhóm một bộ ảnh riêng.* Thời gian và chất lượng phụ thuộc ảnh nên không so được hai nhóm. Loại.
  3. *Một bộ 200 ảnh chung, chọn từ 3149 ứng viên đã đo (YawDD + DrivFace) cộng khung trích thêm từ video, theo độ khó ước lượng; hai gói A (ảnh thô, không nháp) và B (cùng ảnh + manifest + `prelabel.xml` + lượt chạy sẵn).* **Chọn.**
  4. *Ảnh JPEG thay PNG.* Nhỏ hơn, nhưng ở chế độ `--box crop` thì `push` luôn tải `<tên>.png` lên CVAT; chỉ PNG mới cho cùng tên ảnh ở task của cả hai nhóm và trong `prelabel.xml` (không phải sửa `steps.py`). Loại.
- **Quyết định:**
  - **Bộ ảnh:** 200 ảnh PNG 512 x 512 (`square_crop`, nén mức 6, không metadata), số 001..200, tên không lộ nguồn/tài xế/độ khó; `bo_anh = "bo200_v1"`. Hai ảnh 001 và 002 là ảnh dễ khởi động (không tính vào số đo). 003..200 xáo theo seed, chia 9 khối liên tiếp, mỗi khối có tỉ lệ mức gần tỉ lệ chung (lệch tối đa 1), tối đa 2 ảnh nháp tệ, không hai ảnh liền nhau cùng tài xế. Ánh xạ số -> khung gốc/tài xế/camera/mức/thẻ/nháp chỉ nằm trong **file bí mật cho nhóm trưởng** (`bo200_bi_mat.csv`, `.md`), không nằm trong gói A hay B.
  - **Độ khó (heuristic, khó khi gán 50 điểm DMS):** mỗi ảnh có các thẻ yếu tố với điểm (góc mặt theo hệ camera `yaw_vua` 1, `yaw_lon` 2, `yaw_manh_*` 3; `pitch_vua` 1, `pitch_len/xuong` 2; kính thuốc 1, kính râm 3; tay che 3; miệng nói 0,5, ngáp rộng 1; mắt lim dim 1, nhắm 1,5; tối, sáng chói, mờ 1,5; tương phản thấp, mặt nhỏ 1; râu, sát mép 0,5; nghiêng đầu 0,5...). Tổng S: **dễ** S <= 0,5, **vừa** 1..2,5, **khó** 3..4,5, **rất khó** S >= 5 hoặc tay che mắt hoặc |yaw| >= 45 hoặc kính râm cộng yếu tố >= 1,5. Ngưỡng và trọng số ghi cứng ở đầu `tool/tao_bo200.py` sau khi hiệu chỉnh bằng mắt trên lưới ảnh (dấu yaw: yaw > 0 = quay về phía PHẢI ảnh; dấu pitch: pitch > 0 = cúi, pitch < 0 = ngẩng). Bảng đầy đủ: `TAI-LIEU-CHI-TIET.md`, mục "Bộ 200 ảnh chung".
  - **Hạn mức và ràng buộc:** dễ 40, vừa 70, khó 60, rất khó 30; mỗi thẻ hiếm (`yaw_manh_trai/phai`, `pitch_len/xuong`, `kinh_ram`, `che_tay`, `ngap_rong`, `mat_nham`, `toi`, `sang_chay`, `mo`) tối thiểu 8; 8-10 ảnh nháp tệ (xác nhận bằng ảnh chồng nháp); mỗi tài xế <= 6 ảnh, mỗi video <= 3 ảnh cách nhau >= 2 giây, không hai ảnh gần trùng (dHash) trong cùng tài xế; ưu tiên ứng viên NGOÀI 616 mặt của gói đội (>= 80%); mục tiêu mềm về giới, camera, số tài xế. Chọn bằng thử seed liên tiếp, lấy lần đạt luật cứng có điểm phạt cân bằng nhỏ nhất.
  - **Kết quả dựng ngày 09/10/2026** (seed khởi đầu 7, seed thực dùng 14): 3169 ứng viên (3149 cũ + 20 khung trích thêm từ video Dash và Mirror ngáp), 91 tài xế (nhiều nhất 6 ảnh), 92 nữ / 92 nam / 16 `unknown` (DrivFace), camera Mirror 149 / Dash 35 / DrivFace 16, YawDD 184 / DrivFace 16, 198/200 ngoài gói 616, 10 ảnh nháp tệ, mọi thẻ hiếm >= 8, không thẻ thiếu.
  - **Gói A (nhóm MANUAL):** ảnh thô + `face50_label.json` + README + NOTICE + `bo200_info.json` + sha256; không nháp, không thông tin độ khó/nguồn. Tạo task CVAT thủ công với sorting Lexicographical, **Image quality 95**, **Segment size 8** (cùng cách chia job và chất lượng ảnh với task mà `m28.py push` tạo cho nhóm ASSISTED).
  - **Gói B (nhóm ASSISTED):** cùng ảnh (giống từng byte gói A) giải nén thẳng vào `source-tool/m28-prelabel/`: `data/bo200/{anh,manifest.csv,prelabel.xml,...}` và lượt chạy sẵn `runs/bo200/{mediapipe,map50,flags,autoqc}`; `manifest.csv` có hộp mặt đặt để bước `crop` cắt lại ra **đúng ảnh cũ từng pixel**. Luôn chạy với `--manifest data/bo200/manifest.csv` (không ghi đè `data/manifest.csv` của gói 616). Nháp CHUNG sinh một lần bằng chính `m28.py` (MediaPipe 1.0.1, Linux, Python 3.11): thành viên dùng lượt chạy sẵn hoặc nhập `prelabel.xml` thì nháp giống nhau ở mọi máy; `low_conf` đều `false` vì `t_flip` chưa chốt.
  - **Tool tái lập:** `tool/tao_bo200.py` (do, them, chon, luoi, goi, kiem, all), đầu ra ngoài repo; test `tests/test_tao_bo200.py` dùng dữ liệu giả. Dựng lại cần `sua_the.csv` (mọi sửa thẻ bằng mắt) và cache đo, cả hai ngoài git.
- **Hạn chế:** độ khó là **ước lượng heuristic** (ví dụ `sang_chay` đánh giá hơi cao với vài tài xế nắng gắt mà mặt vẫn rõ); mọi ảnh đều là ảnh MediaPipe thấy mặt nên ca khó nhất (MediaPipe bỏ cuộc) không có trong bộ; ít tài xế (YawDD 90 người, DrivFace 4); ảnh 640 x 480 phóng lên 512; camera Mirror lệch +23 độ nên ảnh "dễ" hiếm hơn ở Mirror (dễ chỉ chiếm ~14% ứng viên Mirror, ~19% Dash, ~4% DrivFace); nháp sinh trên Linux (máy khác chạy lại MediaPipe có thể lệch nhẹ); `low_conf` chưa bật; một số khung YawDD có vệt xám quanh miệng do nén video; hai nhóm làm cùng ảnh nhưng khác người nên tốc độ từng người lẫn vào kết quả; lượt `bo200` bị `ca_kho.py` coi là nguồn `khong_ro` (tên mặt không có trong `data/manifest.csv`).
- **Việc phải làm theo:**
  - [ ] Nhóm trưởng chốt **quy ước điểm bị che** (kính râm, tay, tóc) trước khi phát gói; bản chụp kế hoạch 5/10 chỉ ghi dạng "Đề xuất" (ước lượng + bật `occluded`, không dùng `outside`) và gói A, gói B đều ghi cùng đề xuất đó
  - [ ] P5 xác nhận cách loại hai ảnh khởi động (001, 002) khỏi số đo, và cách báo kết quả theo mức khó và riêng nhóm nháp tệ
  - [ ] P4 thử tạo task tay (project bảy label, Image quality 95, Segment size 8) và nhập `prelabel.xml` trên CVAT thật; thử `push` và `collect` với bộ 200 (chưa thử CVAT thật)
  - [ ] Điền `"bo_anh": "bo200_v1"` vào `config/nhom_thi_nghiem.json` khi máy làm tool đồng hồ/thống kê gộp code (file đó không sửa ở phiên này)
- **Trạng thái:** Hiệu lực

---

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
