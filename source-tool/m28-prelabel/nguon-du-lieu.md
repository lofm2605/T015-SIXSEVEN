# Nguồn dữ liệu cho M28

> **ĐỔI NGÀY 6/10/2026 (QĐ-001):** tập chính là **in-cabin: YawDD + DrivFace**; bộ ảnh khuôn mặt cũ đã bỏ hoàn toàn (xem `so-quyet-dinh.md`).
> Dự án phi thương mại: giấy phép "dùng học thuật/nghiên cứu" chấp nhận được; không phát tán, không đăng lại, không giao bên thứ ba.

## Tập chính hiện tại

| Bộ | Nội dung | Giấy phép (ghi ngày 6/10/2026) | Trạng thái |
|---|---|---|---|
| **DrivFace** (UCI) | 606 ảnh 640×480 của 4 tài xế (2 nữ, 2 nam; readme không nói người nào là nữ nên `gender = unknown`) lái xe thật, nhiều ngày, có kính/râu (không ghi theo từng người nên `glasses = unknown`). Đáp án: hộp mặt, mắt phải/trái, mũi, hai khoé miệng; nhãn hướng nhìn 3 lớp (nhìn phải −45..−30°, thẳng −15..15°, nhìn trái 30..45°) | "This database is free for academic usage" (theo `readme.txt` của bộ); mục đích khác liên hệ tác giả (địa chỉ ở readme). Trích dẫn: Diaz-Chito, Hernández-Sabaté, López, *A reduced feature set for driver head pose estimation*, Applied Soft Computing 45 (2016) 98-107 (file `.bib` đi kèm bộ) | **Đã tải trên cloud** (26 MB). MediaPipe dò thấy mặt **606/606**; so với 5 điểm mốc DrivFace (`tool\check_drivface.py`): tâm iris MediaPipe lệch trung vị 5,2% IOD DrivFace (gộp hai mắt; đây là sai số nền của chính 5 điểm mốc, xem bên dưới) |
| **YawDD** | **349 video** quay trong xe thật, 640×480, 30 fps, không tiếng: **Mirror** (camera dưới gương chiếu hậu) 320 video = 156 `Female_mirror` + 164 `Male_mirror Avi Videos`, mỗi người 3-4 video (Normal / Talking / Yawning, đôi khi Talking&Yawning); **Dash** (camera táp-lô) 29 video = 13 `Female` + 16 `Male`, mỗi người một video chứa cả lái xe thường, nói và ngáp. Có kính thuốc / kính râm / không kính, râu, nhiều nền tộc người. (Readme nói 322 + 29; bản tải có 320 + 29.) | Theo `Readme_YawDD.pdf` trong bộ: video **chỉ cho mục đích phi thương mại và nghiên cứu**; dùng được trong bài báo học thuật; chỉ được đăng ảnh chụp màn hình của video có cột "Allow Researchers to use picture in their paper" = **Yes** trong `Table1.pdf` (Mirror) / `Table2.pdf` (Dash); video có "No" thì không được đăng ảnh. Bắt buộc trích dẫn: S. Abtahi, M. Omidyeganeh, S. Shirmohammadi, B. Hariri, "YawDD: A Yawning Detection Dataset", Proc. ACM Multimedia Systems, Singapore, 19-21/3/2014. Giấy phép chính thức trên IEEE DataPort: chưa xác minh | **Đã tải trên cloud** (5,3 GB, 6/10/2026), `cv2.VideoCapture` đọc được; MediaPipe dò thấy mặt ~98% khung |

Tên video YawDD (cần biết khi viết code): Dash `1-FemaleNoGlasses.avi`, `13-MaleNoGlasses .avi` (**dấu cách trước đuôi**), có chỗ `.avi.avi`;
Mirror `1-FemaleNoGlasses-Normal.avi` (trạng thái `Normal|Talking|Yawning|Talking&Yawning`; có chỗ `GlassesBeard`, `Glassesmoustache`, `Talking&yawning` viết thường);
kính `Glasses|NoGlasses|SunGlasses`. Thư mục `Male_mirror Avi Videos` **có dấu cách**. Người ở Dash và Mirror cùng giới + cùng số: tài liệu không nói là cùng hay khác người
(xem `TAI-LIEU-CHI-TIET.md`, mục "Mã người"), nên mã người **gộp** (`yd_M004` dùng chung cho cả hai).

**Tải YawDD (6/10/2026, đã chạy trên cloud).** Dùng **HTTPS** (HTTP cổng 80 bị chặn trên cloud). Link đúng là `user06.tar` (**không phải** `user02`):
```bat
curl -L -o user06.tar https://skuld.cs.umass.edu/traces/mmsys/2014/user06.tar
```
`user06.tar` (5,3 GB) chứa `YawDD dataset.rar`. Giải nén: `tar -xf user06.tar` ra `user06\YawDD dataset.rar`, rồi **rar** giải bằng `bsdtar` (gói `libarchive-tools` trên Linux:
`bsdtar -xf "YawDD dataset.rar" -C <thư mục>`); `7z` và `unrar-free` trên Linux **không** giải được phương pháp nén của file này. Trên Windows dùng **7-Zip bản mới hoặc WinRAR**
(`tar -xf` có sẵn của Windows 10/11 có thể giải được rar vì cùng libarchive: **chưa thử**). Ra thư mục `YawDD dataset\` có `Dash\`, `Mirror\`, `Readme_YawDD.pdf`, `Table1.pdf`, `Table2.pdf`.
Cần Network access của môi trường cloud cho phép `skuld.cs.umass.edu`; bị chặn thì báo chủ repo, không vòng qua.

Cách dùng: **không còn đáp án 98 điểm và không còn ánh xạ học trên bộ ảnh khác**. 50 điểm đặt trực tiếp lên đỉnh MediaPipe (`config\m28_config.json` version 3 = 50 điểm DMS, QĐ-003, `mp_idx`); đáp án để đo chất lượng là nhãn nhóm gán tay trong CVAT (tập vàng G, tập đo; `tool\eval50.py`). DrivFace cho sẵn nhãn hướng nhìn nên dùng làm cờ "nghiêng"; hộp mặt và 5 điểm mốc dùng làm
**kiểm nhanh khách quan, chỉ để tham khảo** (`python tool\check_drivface.py --drivface <thư mục DrivFace> --model face_landmarker.task`; không thay đáp án 50 điểm, không dùng để chỉnh đỉnh trừ lỗi thô).
**Kết quả 6/10/2026 là của 50 điểm CŨ (version 2, trước QĐ-003), không còn hiệu lực cho định nghĩa DMS; chưa đo lại trên DMS** (ngày 7/10 máy chạy không có DrivFace gốc: cần thư mục DrivFace có `drivPoints.txt` rồi chạy `check_drivface.py`, thêm `--old-config`/`--old-map` để so với bản chép config/map v2). Số cũ trên 606 ảnh (trung vị, % khoảng cách hai tâm mắt DrivFace; v2 chọn đỉnh / ridge đã bỏ): tâm mắt R 4,6 / 4,0, tâm mắt L 8,2 / 7,0, mũi 4,8 (p29 chóp) / 5,2, khoé miệng R 8,6 / 10,5, khoé miệng L 4,9 / 6,3; tâm iris MediaPipe 4,2 (R) và 6,1 (L). Bản mới của công cụ so tâm mắt DrivFace với trung bình 8 điểm mỗi mắt của DMS, mũi với chóp `songmui_4`, khoé miệng với `moingoai_1`/`moingoai_7`, ghép bên theo vị trí trong ảnh.
Lưu ý: mốc DrivFace có định nghĩa riêng và lệch hệ thống (xem ảnh: tâm mắt bên phải ảnh lệch sang phải 5-7% IOD, khoé miệng trái ảnh lệch vào trong ~8%; mũi khớp chóp mũi (đỉnh 1), không khớp chân mũi (đỉnh 2) thấp hơn ~15% IOD), nên số này là cận trên cho lỗi của ta chứ không phải lỗi thật; đáng chú ý là nó không tệ đi so với ridge cũ.

**Gói dữ liệu cho đội** dựng từ hai bộ này bằng `tool\\inc_ingest.py` (xem `TAI-LIEU-CHI-TIET.md`, mục "Dữ liệu in-cabin"): 616 mặt `F/Tdev/Ttest/G/P/X/D`, tách theo người.

Lệnh tải DrivFace (cmd): `curl -L -O https://archive.ics.uci.edu/static/public/378/drivface.zip` (bên trong có `DrivImages.zip`, `drivPoints.txt`, `readme.txt`; tên file ảnh có **dấu cách trước `.jpg`**).

## Bộ 200 ảnh thử gán nhãn (bo200, dựng 9/10/2026, QĐ-005)
Bộ 200 ảnh chung cho hai nhóm thử gán 50 điểm (MANUAL gán tay, ASSISTED sửa nháp) lấy **từ hai bộ trên: YawDD (184 ảnh) và DrivFace (16 ảnh)**, do `tool\tao_bo200.py` chọn từ 3149 ứng viên của gói in-cabin cộng 20 khung trích thêm
từ chính các video YawDD đó (9 trong số này vào bộ). Không có nguồn nào khác, không có ảnh khách hàng, không có ảnh đồng đội.
- **Điều khoản (không đổi so với phần trên):** YawDD chỉ cho mục đích phi thương mại và nghiên cứu, bắt buộc trích dẫn (Abtahi và cộng sự, ACM MMSys 2014); chỉ được đăng ảnh chụp màn hình của video có cột
  "Allow Researchers to use picture in their paper" = **Yes** trong `Table1.pdf` (Mirror) / `Table2.pdf` (Dash). DrivFace "free for academic usage" (Diaz-Chito và cộng sự, Applied Soft Computing 2016). Dự án phi thương mại.
- **Chỉ dùng nội bộ nhóm, phi thương mại. Không phát tán, không đăng lại, không đưa vào báo cáo hay slide công khai, không đưa vào chat AI ngoài phiên đã được chủ repo cho phép, không commit.** Gói A và gói B chứa `NOTICE.txt`
  nêu tên hai bộ và điều khoản nhưng **không** ghi nguồn của từng ảnh (ảnh đánh số 001-200).
- **Trước khi đưa bất kỳ ảnh nào ra ngoài nhóm** phải tra file bí mật của nhóm trưởng (`bo200_bi_mat.csv`: số ảnh -> tài xế, video, khung gốc; cột `duoc_dang_anh` đã đối chiếu `Table1.pdf`/`Table2.pdf`: trong bộ này 140 ảnh YawDD ở video
  "Yes", 43 ảnh ở video "No" tuyệt đối không được đưa vào bài báo hay ấn phẩm, 1 ảnh chưa đối chiếu được; ảnh DrivFace ghi `khong_ap_dung`) rồi đối chiếu lại trực tiếp với hai file PDF của bộ YawDD.
- Ảnh trong bộ đã bị cắt vuông 512 x 512 quanh mặt và chỉ có trong zip nội bộ nhóm (`m28_bo200_A_*`, `m28_bo200_B_*`) và trong thư mục dựng ngoài repo; `.gitignore` chặn `data\`, `runs\`, `*.png`, `*.zip`.

---

Gộp từ lượt tìm ngày 05/10/2026 (bản gốc nằm ở phiên Claude của một thành viên, file `du_lieu_face_landmark.md`).
"Đã kiểm" nghĩa là đã gửi request thật (lấy 1 byte đầu hoặc kích thước file), **chưa tải trọn file**.
Lệnh viết cho **cmd** (Windows 10 trở lên có sẵn `curl`). Repo này công khai: file này chỉ chứa link và lệnh;
**không commit dữ liệu tải về** (`.gitignore` đã chặn `data/`, `raw/`, `runs/`).

## A. Dữ liệu in-cabin (mặt tài xế): YawDD, DrivFace là tập chính; các bộ còn lại chỉ để tham khảo

Không bộ nào quay ở Việt Nam, không bộ nào có sẵn 50 điểm của nhóm. Nếu dùng thì chỉ để **thử thêm**
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

## B. Bổ sung — chưa có kết quả

Đang chờ lượt tìm: 300W, COFW, AFLW2000-3D, 300VW, dữ liệu in-cabin có điểm mốc, và trọng số model (STAR,
HRNet, PIPNet, MediaPipe, InsightFace). Khi có, thêm vào đây. Nhắc lại: PIPNet và các trọng số học trên bộ ảnh khác
chỉ để so sánh nội bộ, không nằm trong `tool/`; giấy phép từng bộ phải kiểm trước khi dùng.
