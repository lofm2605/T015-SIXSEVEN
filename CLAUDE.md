# Bối cảnh cho Claude — đội T015-SIXSEVEN, đề tài M28

File này để mọi phiên Claude (máy cá nhân hay Claude Code trên cloud) hiểu đề tài ngay khi mở repo.
Đọc hết file này trước khi trả lời; khi cần chi tiết thì đọc file tương ứng trong `de-tai-m28/`.

## Đề tài

**M28 – Nhãn nháp landmark khuôn mặt (face landmark pre-labelling).** Công cụ đặt sẵn 50 điểm landmark
lên ảnh mặt để người chỉ kiểm và sửa trong CVAT, rồi đo xem nhanh hơn gán tay bao nhiêu mà nhãn không kém đi
(mục tiêu: nhanh hơn ≥ 20%). Theo góp ý mentor (5/10/2026), đề tài phải thành **một pipeline tự động**
(`tool/m28.py`: `prepare` → `review` → `push` → `collect`, gọi chung là `all`) và có **trang rà soát
trước khi nhập vào CVAT** (Gradio, chỉ chạy ở 127.0.0.1).

- Đội 5 người, gọi là P1–P5. Vai trò: P1 dữ liệu + lệnh `m28.py`; P2 model, cờ `low_conf`, trang rà soát;
  P3 file cấu hình 50 điểm, ánh xạ 478→50, đánh giá; P4 CVAT (dựng task, file sao lưu, `export.py`, QC,
  `push`/`collect`); P5 thí nghiệm bấm giờ, guideline, báo cáo, làm việc với mentor.
- Thời gian: thứ Hai 5/10/2026 → thứ Bảy 24/10/2026. Mỗi người khoảng **2 tiếng mỗi tối (T2–T7)** và thêm
  **Chủ nhật 11/10, 18/10**. Mỗi buổi không quá 120 phút.
- Mốc cố định: họp điểm dừng 12/10; thí nghiệm bấm giờ ghép cặp 14–15/10; demo cho mentor CN 18/10;
  nộp 24/10.

## Nguồn sự thật

- Bản gốc kế hoạch nằm trên Claude Docs (7 tab):
  https://claude.ai/code/artifact/72657762-2561-4b97-b0a0-cc9cd9166fee
- `de-tai-m28/*.md` là **bản chụp** xuất ngày 05/10/2026 (Kế hoạch rev 111, Hướng dẫn chung rev 38,
  P1 rev 51, P2 rev 33, P3 rev 26, P4 rev 54, P5 rev 37). Biểu đồ lịch (Gantt) và sơ đồ luồng chỉ có
  trên bản Claude Docs. Nếu hai bản khác nhau thì bản Claude Docs đúng hơn; báo người dùng để cập nhật
  bản chụp.
- `source-tool/m28-prelabel/` là nơi để code của đề tài. Mọi đường dẫn trong kế hoạch (`tool/`, `config/`,
  `data/`, `raw/`, `final/`, `outputs/`, `runs/`, `backups/`) tính từ thư mục này.
- `source-tool/m28-prelabel/snippets/` chứa các đoạn code và prompt mẫu trích từ kế hoạch, **chưa chạy thử**.
  Dùng làm điểm xuất phát, không coi là code đã kiểm.

## Khi một thành viên nhờ bạn

1. Hỏi (hoặc đọc từ câu hỏi) người đó là P mấy và hôm nay là ngày nào.
2. Mở tab của người đó (`de-tai-m28/p1-du-lieu.md` … `p5-thi-nghiem.md`), tìm dòng lịch của ngày đó
   (dạng `**T3 6/10** việc — chạy ở … — ra … — xong khi …`) và bảng "Bạn nhận gì và giao gì".
3. Làm đúng việc của ngày đó, đúng tên file và thư mục như kế hoạch. Không tự đổi tên điểm, tên file,
   ngày giao nhận; nếu thấy kế hoạch sai thì nói rõ và đề xuất sửa.
4. Code chạy trên Windows, Python 3.14, CPU; lệnh viết cho **cmd** (không phải PowerShell). Phiên Claude
   trên cloud không có CVAT của ai và không có GPU. **Từ 6/10/2026 chủ repo cho phép phiên cloud tải và xử
   lý ảnh của các bộ in-cabin đã chọn (YawDD, DrivFace)** để dựng gói dữ liệu và thử `m28.py` trên dữ liệu thật; cần môi trường cloud cho phép
   các host tải (`archive.ics.uci.edu`, `skuld.cs.umass.edu`...). Host bị chặn thì báo chủ repo sửa Network access, không vòng qua.
   Phiên cloud vẫn **không** được xử lý ảnh hay dữ liệu của khách hàng, hay ảnh người thật ngoài các bộ đã chọn (ảnh đồng đội...).

## Quyết định đã chốt

- **Đổi dữ liệu và mục đích (6/10/2026, chủ repo; ghi ở `so-quyet-dinh.md` QĐ-001):** tập chính là **in-cabin (ảnh tài xế trong xe): YawDD + DrivFace**;
  **bỏ hoàn toàn WFLW**; dự án là **phi thương mại** (học tập/nghiên cứu), nên giấy phép "chỉ dùng nghiên cứu/NC" dùng được, nhưng không phát tán dữ liệu
  và không giao cho bên thứ ba. Hệ quả: không còn đáp án 98 điểm có sẵn; 50 điểm lấy trực tiếp từ đỉnh của MediaPipe (không học trên WFLW), đáp án
  để đo chất lượng là nhãn do nhóm gán tay trong CVAT. Các phần trong `de-tai-m28/` nói về WFLW là bản chụp cũ, bản Claude Docs cần cập nhật theo.

- Model giao khách: **MediaPipe Face Landmarker** (Tasks API, `vision.FaceLandmarker`, file
  `face_landmarker.task`, Apache-2.0). Không dùng `mp.solutions`. PIPNet (trọng số học trên WFLW) chỉ để
  so sánh nội bộ, không bao giờ nằm trong `tool/`.
- 50 điểm do nhóm tự chọn (định nghĩa tham khảo bố cục 98 điểm WFLW, nay đặt trực tiếp lên đỉnh MediaPipe; khách hàng chưa có định nghĩa). File cấu hình
  `config/m28_config.json` là nguồn duy nhất cho CVAT, ánh xạ và đánh giá; phần 50 điểm không đổi
  từ 7/10, P1 đóng băng cả file ngày 12/10.
- **Mỗi người một CVAT tự cài** (v2.77.0, Docker Engine trong Ubuntu WSL2, chỉ mở ở
  `http://localhost:8080`). P4 dựng mọi task một lần bằng script rồi phát file sao lưu (`backups/<Pk>/`);
  mỗi người khôi phục task của mình đúng buổi và tự xuất nhãn bằng `export.py` vào `raw/`. Ở công ty thật
  chỉ có một CVAT chung: cùng công cụ, đổi `CVAT_URL` và token.
- cvat-sdk và cvat-cli cùng bản 2.77.0 với server. Đăng nhập bằng Personal Access Token (biến môi
  trường `CVAT_ACCESS_TOKEN` hoặc nhập ở tab Cài đặt của trang rà soát), địa chỉ trong `CVAT_URL` (hoặc tab Cài đặt).
- Thí nghiệm: mỗi Pk gán tay khối Xk và sửa nhãn nháp khối X(k+1) (P5 sửa X1); hai điều kiện tạo task
  giống hệt nhau, nháp chỉ nằm trong task "assisted", task chỉ khôi phục đầu buổi của chính nó.

## Quy tắc bắt buộc

- **Repo này chuyển sang riêng tư ngày 5/10/2026**, nhưng vẫn không commit ảnh mặt (YawDD, DrivFace, WFLW cũ, ảnh
  cắt, ảnh chồng), file đáp án, file xuất CVAT, file sao lưu task, `runs/`, trọng số PIPNet hay dữ liệu khách
  hàng vào git. `.gitignore` vẫn chặn các thư mục này; chỉ gỡ khi chủ repo yêu cầu rõ. Gói dữ liệu cho đội
  gửi qua file zip (tải về hoặc Drive riêng tư của đội), không đẩy lên git. Nếu repo bị đổi lại thành công
  khai thì dữ liệu phải ra khỏi repo ngay.
- Token CVAT được phép nhập ở tab **Cài đặt** của trang rà soát chạy cục bộ (chỉ 127.0.0.1) và có thể lưu ngoài repo trong thư mục người dùng khi người dùng bật "Nhớ trên máy này". Vẫn **không bao giờ** ghi token, mật khẩu, địa chỉ email riêng vào code, repo, chat, log, `runs/`, `outputs/`.
- Ảnh in-cabin **YawDD** và **DrivFace** (bộ nghiên cứu công khai, có giấy phép dùng học thuật) được phép xử lý trong phiên Claude cloud của chủ repo,
  kèm điều kiện ở trên. **Ảnh, đáp án, file xuất CVAT của khách hàng, và ảnh mặt người thật ngoài các bộ đã chọn** (ảnh đồng đội, bộ khác)
  không bao giờ được đưa vào chat AI nào (kể cả Gemini trong Colab). Ảnh người lái xe là dữ liệu nhạy cảm: chỉ dùng nội bộ nhóm, không đăng,
  không gửi ra ngoài, không đưa vào báo cáo/slide công khai nếu giấy phép bộ đó không cho phép; ghi nguồn khi trích.
- Trang rà soát chỉ chạy `launch(server_name="127.0.0.1", share=False)`; không `share=True`, không tunnel.
- Giấy phép: DrivFace "free for academic usage" (liên hệ tác giả nếu dùng mục đích khác); YawDD theo điều khoản IEEE DataPort/UMass (kiểm và
  ghi vào `source-tool/m28-prelabel/nguon-du-lieu.md` trước khi dùng). Dự án phi thương mại: không bán, không giao thương mại, không đăng lại dữ liệu.

## Quy ước của repo (template khoá 4A)

- `problem-backlog.md`: edge case và pain point, mã `P-001`…; `so-quyet-dinh.md`: quyết định đã chốt,
  mã `QĐ-001`…; `nhat-ky-tuan/`: nhật ký tuần. Ba file đó hiện để trống (đã xoá các ví dụ giả của template).
- Mỗi tool trong `source-tool/` có README riêng theo mẫu trong `source-tool/README.md`.
