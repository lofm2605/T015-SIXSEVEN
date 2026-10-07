# Cờ low_conf trên dữ liệu in-cabin, định nghĩa 50 điểm DMS (bản nháp cho P2, ngày 7/10/2026, giai đoạn 3)

**Chưa đo được cờ "bắt được bao nhiêu điểm sai"**: bộ in-cabin không có đáp án 50 điểm (QĐ-001), nên AUROC và "% điểm sai bị bắt" cần nhãn gán tay G/X theo định nghĩa DMS (chế độ có đáp án, sau 14-15/10). Hiện chỉ có chế độ (a): phân bố điểm số nghi sai
và đề xuất ngưỡng, không cần đáp án.

Đo bằng `python tool\flag_eval.py --run <run> --set Tdev` trên **Tdev: 99 mặt có ảnh lật (100 mặt, 1 mặt MediaPipe không thấy mặt trên ảnh lật), 4.950 điểm**, ánh xạ chọn đỉnh của **50 điểm DMS** (`config\m28_config.json` và `config\map_mp50.json` version 3, QĐ-003). Không đọc Ttest.
Điểm số nghi sai của mỗi điểm = lệch giữa kết quả ảnh gốc và ảnh lật (đã bỏ lật) / khoảng cách hai khoé mắt ngoài dự đoán (`iod_points` = `mattrai_1`, `matphai_1`); cờ bật khi điểm số > `t_flip` (đúng như `steps.flags`).
Số đo trên máy Windows của chủ repo (Python 3.14, mediapipe 1.0.1, ảnh cắt trong gói `data\crops`).

| phân vị | ngưỡng `t_flip` | điểm bị cờ | cờ/mặt |
|---|---|---|---|
| 0,50 | 0,0155 | 50% | 25,0 |
| 0,70 | 0,0233 | 30% | 15,0 |
| 0,80 | 0,0302 | 20% | 10,0 |
| **0,85** | **0,0357** | **15%** | **7,5** |
| 0,90 | 0,0436 | 10% | 5,0 |
| 0,95 | 0,0551 | 5% | 2,5 |

Điểm số theo nhóm (trung vị / phân vị 0,85 / phân vị 0,95): `longmaytrai` 0,0177 / 0,0407 / 0,0612; `longmayphai` 0,0198 / 0,0456 / 0,0791; `songmui` 0,0163 / 0,0351 / 0,0523; `mattrai` 0,0124 / 0,0285 / 0,0462; `matphai` 0,0147 / 0,0430 / 0,0660;
`moingoai` 0,0158 / 0,0333 / 0,0498; `moitrong` 0,0153 / 0,0311 / 0,0486. Theo vùng thô: lông mày 0,0188 / 0,0436 / 0,0702; mắt 0,0134 / 0,0345 / 0,0561; môi 0,0155 / 0,0326 / 0,0495; mũi 0,0163 / 0,0351 / 0,0523 (không còn vùng viền).

**Đề xuất `t_flip` = 0,0357** (phân vị 0,85 trên Tdev; kế hoạch P2: cờ <= 15% số điểm): 15,0% điểm bị cờ, 7,5 cờ/mặt. Theo nhóm tỉ lệ bị cờ: `longmaytrai` 19%, `longmayphai` 25%, `songmui` 14%, `mattrai` 10%, `matphai` 19%, `moingoai` 13%, `moitrong` 11%; theo vùng: lông mày 22%, mắt 14%, môi 12%, mũi 14%.
So với đề xuất 0,0464 của định nghĩa 50 điểm CŨ (version 2, có viền hàm): **không dùng được số cũ**; ngưỡng mới thấp hơn, phù hợp với việc điểm số của viền hàm (cao nhất ở v2: phân vị 0,85 là 0,0655, 27% bị cờ) không còn trong bộ điểm. `config\m28_config.json` vẫn để `t_flip: null` theo kế hoạch cho tới khi P2 chốt ngày 12/10; chốt rồi thì ghi bằng tab Cài đặt hoặc
`python tool\make_config.py --t-flip <số>`. (Đổi `t_flip` cần chạy lại `prepare --force flags autoqc overlays` cho các lượt đã chạy.)

Cờ trông thế nào (chạy thử với 0,0357 trên cả 615 mặt, lượt `INC3_TFLIP` chỉ ở máy chạy, ảnh `inc3_flags_tflip_*` ở báo cáo giai đoạn 3):
- Cờ **dồn vào mặt khó**: trung vị 1 cờ/mặt, phân vị 90 là 24 cờ/mặt; mặt `pose` = 1 trung bình 15,5 cờ, mặt `pose` = 0 trung bình 5,4 cờ. 9 mặt MediaPipe không thấy mặt trên ảnh lật bị bật cả 50 cờ (coi mọi điểm đáng ngờ).
- Cờ đỏ rơi đúng chỗ yếu đã biết: mặt quay mạnh (mày, mắt, môi phía XA, thường là phía PHẢI ảnh vì phần lớn mặt Mirror của YawDD quay về phía phải: `longmayphai` 25%, `matphai` 19%), mặt đeo kính râm, miệng ngáp rộng hoặc tay che miệng, mặt rất tối.
  Mặt nhìn thẳng thường không có cờ (trong lưới kiểm 21 mặt: 5/6 mặt X và 3/3 mặt F thẳng không cờ, `X1_06` có 3 cờ ở chóp mũi và môi trong dưới; `Tdev_088` kính râm 21 cờ, `Tdev_013` và `Tdev_007` quay 11 và 6 cờ). Chưa đo được cờ có rơi vào điểm "thật sự sai" hay không (cần đáp án); mới xem bằng mắt trên 21 mặt.

Việc cần làm tiếp:
- Khi nhóm gán tay xong G/X: `python tool\flag_eval.py --run <run> --gt raw\<đáp án>.xml` cho AUROC toàn bộ, theo vùng và theo nhóm, % điểm sai bắt được, độ chính xác (sai số chấp nhận lấy `config.tolerance` theo vùng của P3 nếu có, không thì `--tol`, mặc định 3% IOD).
- P2 chốt ngưỡng ngày 12/10 trên Tdev (không dùng Ttest để chọn ngưỡng).
- Cờ chỉ dùng độ bất nhất gốc/lật của MediaPipe. Cờ gộp có thêm bất đồng với PIPNet (chỉ cho thí nghiệm, PIPNet không vào `tool/`; PIPNet học trên bộ ảnh khác mặt tài xế nên cũng không còn là so sánh công bằng) có thể khác.

## Lịch sử (50 điểm version 2, QĐ-002, trước QĐ-003): số cũ KHÔNG còn hiệu lực

Đo 6/10/2026 trên Tdev (99 mặt có ảnh lật, 4.950 điểm) với 50 điểm cũ `p01…p50` (viền hàm 17 điểm): đề xuất `t_flip` = 0,0464 (phân vị 0,85): 14,9% điểm bị cờ, ~7,5 cờ/mặt; điểm số theo vùng (trung vị / phân vị 0,85 / phân vị 0,95): viền 0,0275 / 0,0655 / 0,1139,
lông mày 0,0189 / 0,0435 / 0,0701, mũi 0,0170 / 0,0353 / 0,0509, mắt 0,0135 / 0,0341 / 0,0559, môi 0,0160 / 0,0335 / 0,0501; tỉ lệ bị cờ theo vùng: viền 27%, lông mày 13%, mắt 9%, mũi 6%, môi 6% (cờ dồn vào viền khi mặt nghiêng). Trên 615 mặt với 0,0464: trung vị 1 cờ/mặt, p90 21,6; `pose` = 1 trung bình 14,3 cờ, `pose` = 0 4,6 cờ.

Chưa có số AUROC / % điểm sai bắt được trên tập in-cabin: cần chạy lại `flag_eval` (có `--gt`) trên tập in-cabin khi có nhãn gán tay G/X (số đo cũ trên bộ ảnh đã bỏ không còn hiệu lực và đã xoá).
