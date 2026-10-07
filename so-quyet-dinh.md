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
| [QĐ-003](#qđ-003) | Định nghĩa 50 điểm DMS (7 nhóm, không viền hàm), trái/phải theo ảnh, config v3 | 07/10/2026 | QĐ-002 | Hiệu lực |

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
- **Trạng thái:** Hiệu lực

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
