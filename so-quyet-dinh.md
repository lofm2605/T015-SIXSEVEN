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
