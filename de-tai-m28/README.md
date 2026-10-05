# Đề tài M28 — Nhãn nháp landmark khuôn mặt

Kế hoạch 3 tuần (5/10 – 24/10/2026) của đội cho đề tài M28, xuất từ bản gốc trên Claude Docs ngày 05/10/2026.
Bản gốc (có biểu đồ lịch và sơ đồ luồng) và các bình luận nằm ở:
https://claude.ai/code/artifact/72657762-2561-4b97-b0a0-cc9cd9166fee

| File | Nội dung | Ai đọc |
|---|---|---|
| [`ke-hoach.md`](ke-hoach.md) | Mục tiêu, dữ liệu, guideline 50 điểm, pipeline và trang rà soát, thí nghiệm đo, chia việc, lịch, kiểm soát chất lượng, rủi ro, câu hỏi cho mentor | Cả đội, mentor |
| [`huong-dan-chung.md`](huong-dan-chung.md) | Nhịp một buổi, repo và thư mục, dựng môi trường, **cài CVAT trên máy mình**, Colab/Kaggle, dùng AI an toàn, chạy pipeline, bảng thuật ngữ | Cả đội |
| [`p1-du-lieu.md`](p1-du-lieu.md) | P1: tải WFLW, cắt mặt, chia tập, lệnh `m28.py`, đóng gói công cụ | P1 |
| [`p2-model.md`](p2-model.md) | P2: MediaPipe, PIPNet, cờ `low_conf`, tự dò khung mặt, trang rà soát | P2 |
| [`p3-anh-xa.md`](p3-anh-xa.md) | P3: file cấu hình 50 điểm, ánh xạ 478→50, `eval50.py`, chấm trang rà soát | P3 |
| [`p4-cvat.md`](p4-cvat.md) | P4: CVAT tự cài, dựng task và file sao lưu, `export.py`, QC, `push`/`collect` | P4 |
| [`p5-thi-nghiem.md`](p5-thi-nghiem.md) | P5: guideline, bấm giờ, phân tích thời gian và chất lượng, quy tắc rà soát, báo cáo, demo | P5 |

Mỗi tab người có cùng bố cục: **Bạn nhận gì và giao gì** (bảng theo ngày) → **Lịch của bạn** (mỗi dòng:
ngày — việc — chạy ở đâu — ra gì — xong khi nào) → **Làm thế nào** (code mẫu) → **Chạy ở đâu** →
**Nhờ AI cho đúng** → **Lỗi hay gặp** → **Khi bị kẹt**.

Code của đề tài đặt ở [`../source-tool/m28-prelabel/`](../source-tool/m28-prelabel/). Các đoạn code
và prompt mẫu trong kế hoạch đã được tách sẵn vào `snippets/` trong thư mục đó.

## Dùng với Claude trên cloud

1. Vào https://claude.ai/code, chọn repo `lofm2605/T015-SIXSEVEN`, nhánh `main`.
2. Mở đầu bằng một câu như: *"Tôi là P2, hôm nay là T3 6/10. Làm việc của tôi hôm nay theo kế hoạch."*
   Claude đọc `CLAUDE.md` ở gốc repo, rồi tab của bạn trong thư mục này.
3. Phiên cloud **không có** ảnh WFLW, CVAT trên máy bạn hay GPU. Ở đó chỉ viết code, viết test bằng dữ liệu
   giả, sửa tài liệu. Chạy thật trên máy mình (Windows, cmd, Python 3.14).
4. Không dán ảnh mặt, file đáp án, file xuất CVAT hay token vào chat. Repo này đang **công khai**: không
   commit dữ liệu (xem `.gitignore`).

## Cập nhật bản chụp

Khi kế hoạch trên Claude Docs đổi, xuất lại tab đó dạng Markdown và ghi đè file tương ứng ở đây, kèm ngày
và số rev trong commit message. Đừng sửa thẳng các file `.md` này rồi quên bản gốc: hai bản sẽ lệch nhau.
