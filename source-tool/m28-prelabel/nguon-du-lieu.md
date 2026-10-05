# Nguồn dữ liệu cho M28

Gộp từ lượt tìm ngày 05/10/2026 (bản gốc nằm ở phiên Claude của một thành viên, file `du_lieu_face_landmark.md`).
"Đã kiểm" nghĩa là đã gửi request thật (lấy 1 byte đầu hoặc kích thước file), **chưa tải trọn file**.
Lệnh viết cho **cmd** (Windows 10 trở lên có sẵn `curl`). Repo này công khai: file này chỉ chứa link và lệnh;
**không commit dữ liệu tải về** (`.gitignore` đã chặn `data/`, `raw/`, `runs/`).

## A. WFLW — nguồn chính của đề tài (98 điểm, 10.000 ảnh: 7.500 train / 2.500 test)

Mỗi dòng nhãn gốc có 207 trường: 196 toạ độ của 98 điểm, 4 số hộp mặt, 6 cờ 0/1 (tư thế, biểu cảm,
ánh sáng, trang điểm, che khuất, mờ), rồi đường dẫn ảnh. Khớp với cột `pose`, `occlusion` và 4 cờ khác của `manifest.csv` (tab P1).

| Nguồn | Kích thước | Trạng thái | Lệnh tải |
|---|---|---|---|
| Nhãn gốc (tải trước) | 16.329.835 B | Đã kiểm: HTTP 200, gzip, liệt kê được | `curl -L -O https://wywu.github.io/projects/LAB/support/WFLW_annotations.tar.gz` |
| Ảnh gốc (Google Drive) | 743.030.592 B | Đã kiểm: Range 0-0 trả 206 | `curl -L -o WFLW_images.tar.gz "https://drive.usercontent.google.com/download?id=1hzBd48JIdWTJSsATBEB_eFVvPL1bx6UC&export=download&confirm=t"` |
| Nhãn mmpose (JSON kiểu COCO, 6 tập test theo thuộc tính) | 40.835.584 B | Đã kiểm: HTTP 200 | `curl -L -O https://download.openmmlab.com/mmpose/datasets/wflw_annotations.tar` |
| [Kaggle mrriandmstique](https://www.kaggle.com/datasets/mrriandmstique/wflw-wider-facial-landmarks-in-the-wild) (dự phòng khi Drive hết lượt, theo tab P1) | ~784 MB | Chỉ đọc trang, cần tài khoản | `kagglehub.dataset_download("mrriandmstique/wflw-wider-facial-landmarks-in-the-wild")` |
| [HF duongnguy/WFLW_augmented](https://huggingface.co/datasets/duongnguy/WFLW_augmented) | test 8,9 MB, train 269,6 MB | Đã kiểm, không license | **Không dùng**: bản augment của bên thứ ba, nhãn chuẩn hoá 0–1, mất 6 cờ thuộc tính |
| Metadata `train.tsv/test.tsv` (STAR/ADNet), CSV nhãn HRNet | chưa đo | Chỉ đọc README | Chỉ cần khi so sánh model nội bộ |

**Giấy phép:** WFLW không có giấy phép riêng; ảnh lấy từ WIDER FACE (CC BY-NC-ND) → chỉ dùng nghiên cứu/nội bộ,
không phát tán, không đăng bản đã sửa. Nhãn "Apache 2.0" trên Kaggle do người đăng lại tự gắn, không đổi điều này.

## B. Dữ liệu in-cabin (mặt tài xế) — ngoài phạm vi kế hoạch M28

Không bộ nào quay ở Việt Nam, không bộ nào có sẵn 98 điểm kiểu WFLW. Nếu dùng thì chỉ để **thử thêm**
xem model có chạy ổn trên mặt tài xế (góc nghiêng, đeo kính, hồng ngoại ban đêm). Đây là ảnh người thật:
tải về máy, không đưa lên repo công khai, không đưa vào chat AI. Muốn đưa vào kế hoạch thì ghi một `QĐ-` trước.

| Bộ | Nội dung | Tải / liên hệ | Thương mại |
|---|---|---|---|
| [DrivFace](https://archive.ics.uci.edu/dataset/378/drivface) | 606 ảnh 640×480 của 4 tài xế, có hộp mặt và điểm mắt/mũi/miệng | `curl -L -O https://archive.ics.uci.edu/static/public/378/drivface.zip` (đã kiểm) | chưa rõ |
| [YawDD](https://ieee-dataport.org/open-access/yawdd-yawning-detection-dataset) | 322 video gương chiếu hậu + 29 video táp-lô | ví dụ `curl -L -o user06.tar http://skuld.cs.umass.edu/traces/mmsys/2014/user06.tar` (5,3 GB, đã kiểm) | chưa rõ |
| [akahana/Driver-Drowsiness-Dataset](https://huggingface.co/datasets/akahana/Driver-Drowsiness-Dataset) | 41.793 ảnh mặt buồn ngủ/không (parquet), 2,76 GB | file thử 277 MB: `.../resolve/main/data/test-00000-of-00002.parquet` (đã kiểm) | chưa rõ (nhiều khả năng trích từ UTA-RLDD) |
| [Drive&Act](https://driveandact.com/) | 12 giờ video cabin, pose 3D; Đức | `a_column_driver.zip` 2,67 GB (đã kiểm) | không |
| [DriverMVT](https://zenodo.org/records/6542011) | 1.506 video, 9 tài xế, ~150 GB; Nga | Zenodo, 4 phần zip (đã kiểm HEAD) | được (CC BY 4.0) |
| [NTHU-DDD](http://cv.cs.nthu.edu.tw/php/callforpaper/datasets/DDD/) | video hồng ngoại 36 người, Đài Loan | ký thoả thuận, gửi email tới chủ bộ | hỏi chủ bộ |
| [DMD (Vicomtech)](https://dmd.vicomtech.org/) | video RGB tài xế trong xe thật; Tây Ban Nha | trang tải chưa kiểm được | không (CC BY-NC-ND 4.0) |
| [UTA-RLDD](https://sites.google.com/view/utarldd/home) | 180 video, 60 người, ~111 GB | Google Drive folder, chưa liệt kê được | chưa rõ |

## C. Bổ sung — chưa có kết quả

Đang chờ lượt tìm: 300W, COFW, AFLW2000-3D, 300VW, dữ liệu in-cabin có điểm mốc, và trọng số model (STAR,
HRNet-WFLW, PIPNet, MediaPipe, InsightFace). Khi có, thêm vào đây. Nhắc lại: PIPNet và các trọng số học trên WFLW
chỉ để so sánh nội bộ, không nằm trong `tool/`; giấy phép từng bộ phải kiểm trước khi dùng.
