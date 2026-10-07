# Nguồn dữ liệu cho M28

> **ĐỔI NGÀY 6/10/2026 (QĐ-001):** tập chính là **in-cabin: YawDD + DrivFace**; **WFLW không còn dùng** (các mục A bên dưới giữ để tham khảo lịch sử).
> Dự án phi thương mại: giấy phép "dùng học thuật/nghiên cứu" chấp nhận được; không phát tán, không đăng lại, không giao bên thứ ba.

## Tập chính hiện tại

| Bộ | Nội dung | Giấy phép (ghi ngày 6/10/2026) | Trạng thái |
|---|---|---|---|
| **DrivFace** (UCI) | 606 ảnh 640×480 của 4 tài xế (2 nữ, 2 nam; readme không nói người nào là nữ nên `gender = unknown`) lái xe thật, nhiều ngày, có kính/râu (không ghi theo từng người nên `glasses = unknown`). Đáp án: hộp mặt, mắt phải/trái, mũi, hai khoé miệng; nhãn hướng nhìn 3 lớp (nhìn phải −45..−30°, thẳng −15..15°, nhìn trái 30..45°) | "This database is free for academic usage" (theo `readme.txt` của bộ); mục đích khác liên hệ tác giả (địa chỉ ở readme). Trích dẫn: Diaz-Chito, Hernández-Sabaté, López, *A reduced feature set for driver head pose estimation*, Applied Soft Computing 45 (2016) 98-107 (file `.bib` đi kèm bộ) | **Đã tải trên cloud** (26 MB). MediaPipe dò thấy mặt **606/606**; so với 5 điểm mốc DrivFace (`tool\check_drivface.py`): tâm iris MediaPipe lệch trung vị 5,2% IOD DrivFace (gộp hai mắt; đây là sai số nền của chính 5 điểm mốc, xem bên dưới) |
| **YawDD** | **349 video** quay trong xe thật, 640×480, 30 fps, không tiếng: **Mirror** (camera dưới gương chiếu hậu) 320 video = 156 `Female_mirror` + 164 `Male_mirror Avi Videos`, mỗi người 3-4 video (Normal / Talking / Yawning, đôi khi Talking&Yawning); **Dash** (camera táp-lô) 29 video = 13 `Female` + 16 `Male`, mỗi người một video chứa cả lái xe thường, nói và ngáp. Có kính thuốc / kính râm / không kính, râu, nhiều nền tộc người. (Readme nói 322 + 29; bản tải có 320 + 29.) | Theo `Readme_YawDD.pdf` trong bộ: video **chỉ cho mục đích phi thương mại và nghiên cứu**; dùng được trong bài báo học thuật; chỉ được đăng ảnh chụp màn hình của video có cột "Allow Researchers to use picture in their paper" = **Yes** trong `Table1.pdf` (Mirror) / `Table2.pdf` (Dash); video có "No" thì không được đăng ảnh. Bắt buộc trích dẫn: S. Abtahi, M. Omidyeganeh, S. Shirmohammadi, B. Hariri, "YawDD: A Yawning Detection Dataset", Proc. ACM Multimedia Systems, Singapore, 19-21/3/2014. Giấy phép chính thức trên IEEE DataPort: chưa xác minh | **Đã tải trên cloud** (5,3 GB, 6/10/2026), `cv2.VideoCapture` đọc được; MediaPipe dò thấy mặt ~98% khung |

Tên video YawDD (cần biết khi viết code): Dash `1-FemaleNoGlasses.avi`, `13-MaleNoGlasses .avi` (**dấu cách trước đuôi**), có chỗ `.avi.avi`;
Mirror `1-FemaleNoGlasses-Normal.avi` (trạng thái `Normal|Talking|Yawning|Talking&Yawning`; có chỗ `GlassesBeard`, `Glassesmoustache`, `Talking&yawning` viết thường);
kính `Glasses|NoGlasses|SunGlasses`. Thư mục `Male_mirror Avi Videos` **có dấu cách**. Người ở Dash và Mirror cùng giới + cùng số: tài liệu không nói là cùng hay khác người
(xem `README.md`, mục "Mã người"), nên mã người **gộp** (`yd_M004` dùng chung cho cả hai).

**Tải YawDD (6/10/2026, đã chạy trên cloud).** Dùng **HTTPS** (HTTP cổng 80 bị chặn trên cloud). Link đúng là `user06.tar` (**không phải** `user02`):
```bat
curl -L -o user06.tar https://skuld.cs.umass.edu/traces/mmsys/2014/user06.tar
```
`user06.tar` (5,3 GB) chứa `YawDD dataset.rar`. Giải nén: `tar -xf user06.tar` ra `user06\YawDD dataset.rar`, rồi **rar** giải bằng `bsdtar` (gói `libarchive-tools` trên Linux:
`bsdtar -xf "YawDD dataset.rar" -C <thư mục>`); `7z` và `unrar-free` trên Linux **không** giải được phương pháp nén của file này. Trên Windows dùng **7-Zip bản mới hoặc WinRAR**
(`tar -xf` có sẵn của Windows 10/11 có thể giải được rar vì cùng libarchive: **chưa thử**). Ra thư mục `YawDD dataset\` có `Dash\`, `Mirror\`, `Readme_YawDD.pdf`, `Table1.pdf`, `Table2.pdf`.
Cần Network access của môi trường cloud cho phép `skuld.cs.umass.edu`; bị chặn thì báo chủ repo, không vòng qua.

Cách dùng: **không còn đáp án 98 điểm và không còn ánh xạ học trên WFLW**. 50 điểm đặt trực tiếp lên đỉnh MediaPipe (`config\m28_config.json` version 3 = 50 điểm DMS, QĐ-003, `mp_idx`); đáp án để đo chất lượng là nhãn nhóm gán tay trong CVAT (tập vàng G, tập đo; `tool\eval50.py`). DrivFace cho sẵn nhãn hướng nhìn nên dùng làm cờ "nghiêng"; hộp mặt và 5 điểm mốc dùng làm
**kiểm nhanh khách quan, chỉ để tham khảo** (`python tool\check_drivface.py --drivface <thư mục DrivFace> --model face_landmarker.task`; không thay đáp án 50 điểm, không dùng để chỉnh đỉnh trừ lỗi thô).
**Kết quả 6/10/2026 là của 50 điểm CŨ (version 2, trước QĐ-003), không còn hiệu lực cho định nghĩa DMS; chưa đo lại trên DMS** (ngày 7/10 máy chạy không có DrivFace gốc: cần thư mục DrivFace có `drivPoints.txt` rồi chạy `check_drivface.py`, thêm `--old-config`/`--old-map` để so với bản chép config/map v2). Số cũ trên 606 ảnh (trung vị, % khoảng cách hai tâm mắt DrivFace; v2 chọn đỉnh / ridge WFLW đã bỏ): tâm mắt R 4,6 / 4,0, tâm mắt L 8,2 / 7,0, mũi 4,8 (p29 chóp) / 5,2, khoé miệng R 8,6 / 10,5, khoé miệng L 4,9 / 6,3; tâm iris MediaPipe 4,2 (R) và 6,1 (L). Bản mới của công cụ so tâm mắt DrivFace với trung bình 8 điểm mỗi mắt của DMS, mũi với chóp `songmui_4`, khoé miệng với `moingoai_1`/`moingoai_7`, ghép bên theo vị trí trong ảnh.
Lưu ý: mốc DrivFace có định nghĩa riêng và lệch hệ thống (xem ảnh: tâm mắt bên phải ảnh lệch sang phải 5-7% IOD, khoé miệng trái ảnh lệch vào trong ~8%; mũi khớp chóp mũi (đỉnh 1), không khớp chân mũi (đỉnh 2) thấp hơn ~15% IOD), nên số này là cận trên cho lỗi của ta chứ không phải lỗi thật; đáng chú ý là nó không tệ đi so với ridge cũ.

**Gói dữ liệu cho đội** dựng từ hai bộ này bằng `tool\\inc_ingest.py` (xem `README.md`, mục "Dữ liệu in-cabin"): 616 mặt `F/Tdev/Ttest/G/P/X/D`, tách theo người.

Lệnh tải DrivFace (cmd): `curl -L -O https://archive.ics.uci.edu/static/public/378/drivface.zip` (bên trong có `DrivImages.zip`, `drivPoints.txt`, `readme.txt`; tên file ảnh có **dấu cách trước `.jpg`**).

---

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

## B. Dữ liệu in-cabin (mặt tài xế) — nay là tập chính (YawDD, DrivFace); các bộ còn lại chỉ để tham khảo

Không bộ nào quay ở Việt Nam, không bộ nào có sẵn 98 điểm kiểu WFLW. Nếu dùng thì chỉ để **thử thêm**
xem model có chạy ổn trên mặt tài xế (góc nghiêng, đeo kính, hồng ngoại ban đêm). Đây là ảnh người thật:
tải về máy, không đưa lên repo công khai, không đưa vào chat AI. Muốn đưa vào kế hoạch thì ghi một `QĐ-` trước.

| Bộ | Nội dung | Tải / liên hệ | Thương mại |
|---|---|---|---|
| [DrivFace](https://archive.ics.uci.edu/dataset/378/drivface) | 606 ảnh 640×480 của 4 tài xế, có hộp mặt và điểm mắt/mũi/miệng | `curl -L -O https://archive.ics.uci.edu/static/public/378/drivface.zip` (đã kiểm) | chưa rõ |
| [YawDD](https://ieee-dataport.org/open-access/yawdd-yawning-detection-dataset) | 320 video gương chiếu hậu + 29 video táp-lô (bản đã tải; readme ghi 322 + 29) | ví dụ `curl -L -o user06.tar https://skuld.cs.umass.edu/traces/mmsys/2014/user06.tar` (5,3 GB, đã kiểm) | chưa rõ |
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
