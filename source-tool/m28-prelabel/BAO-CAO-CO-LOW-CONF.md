# Cờ low_conf trên dữ liệu in-cabin (bản nháp cho P2, ngày 6/10/2026, giai đoạn 2)

**Chưa đo được cờ "bắt được bao nhiêu điểm sai"**: bộ in-cabin không có đáp án 50 điểm (QĐ-001), nên AUROC và "% điểm sai bị bắt" cần nhãn gán tay G/X (chế độ có đáp án, sau 14-15/10). Hiện chỉ có chế độ (a): phân bố điểm số nghi sai
và đề xuất ngưỡng, không cần đáp án.

Đo bằng `python tool\flag_eval.py --run <run> --set Tdev` trên **Tdev: 99 mặt có ảnh lật (100 mặt, 1 mặt MediaPipe không thấy mặt trên ảnh lật), 4.950 điểm**, ánh xạ chọn đỉnh (`config\map_mp50.json` version 2). Không đọc Ttest.
Điểm số nghi sai của mỗi điểm = lệch giữa kết quả ảnh gốc và ảnh lật (đã bỏ lật) / khoảng cách hai khoé mắt ngoài dự đoán; cờ bật khi điểm số > `t_flip` (đúng như `steps.flags`).

| phân vị | ngưỡng `t_flip` | điểm bị cờ | cờ/mặt |
|---|---|---|---|
| 0,50 | 0,0196 | 50% | 25,0 |
| 0,70 | 0,0300 | 30% | 15,0 |
| 0,80 | 0,0395 | 20% | 10,0 |
| **0,85** | **0,0464** | **15%** | **7,5** |
| 0,90 | 0,0568 | 10% | 5,0 |
| 0,95 | 0,0805 | 5% | 2,5 |

Điểm số theo vùng (trung vị / phân vị 0,85 / phân vị 0,95): viền 0,0275 / 0,0655 / 0,1139; lông mày 0,0189 / 0,0435 / 0,0701; mũi 0,0170 / 0,0353 / 0,0509; mắt 0,0135 / 0,0341 / 0,0559; môi 0,0160 / 0,0335 / 0,0501.

**Đề xuất `t_flip` = 0,0464** (phân vị 0,85 trên Tdev; kế hoạch P2: cờ <= 15% số điểm): 14,9% điểm bị cờ, ~7,5 cờ/mặt. Theo vùng tỉ lệ bị cờ: viền 27%, lông mày 13%, mắt 9%, mũi 6%, môi 6%.
(Trên F, chỉ để tham khảo: 0,0390.) `config\m28_config.json` vẫn để `t_flip: null` theo kế hoạch cho tới khi P2 chốt ngày 12/10; chốt rồi thì ghi bằng tab Cài đặt hoặc `python tool\make_config.py --t-flip <số>`.

Cờ trông thế nào (chạy thử với 0,0464 trên cả 615 mặt, ảnh đỏ/xanh ở báo cáo giai đoạn 2):
- Cờ **dồn vào mặt khó**: trung vị 1 cờ/mặt, phân vị 90 là 21,6 cờ/mặt; mặt `pose` = 1 trung bình 14,3 cờ, mặt `pose` = 0 trung bình 4,6 cờ. 8 mặt MediaPipe không thấy mặt trên ảnh lật (đều đeo kính hoặc kính râm) bị bật cả 50 cờ (coi mọi điểm đáng ngờ).
- Trên mặt quay 25-30 độ, cờ đỏ rơi vào viền phía xa (p10-p16) và vùng đầu lông mày/khoé mắt phía xa: đúng chỗ ánh xạ chọn đỉnh đặt điểm trong má thay vì trên đường viền nhìn thấy (xem README, "điểm kém đã biết"), nên cờ bắt đúng vùng yếu nhưng cũng bật nhiều ở viền (27%).
  Mặt nhìn thẳng thường ít hoặc không có cờ. Chưa đo được cờ có rơi vào điểm "thật sự sai" hay không (cần đáp án); mới xem bằng mắt trên 12 mặt.

Việc cần làm tiếp:
- Khi nhóm gán tay xong G/X: `python tool\flag_eval.py --run <run> --gt raw\<đáp án>.xml` cho AUROC toàn bộ và theo vùng, % điểm sai bị bắt, độ chính xác (sai số chấp nhận lấy `config.tolerance` theo vùng của P3 nếu có, không thì `--tol`, mặc định 3% IOD).
- P2 chốt ngưỡng ngày 12/10 trên Tdev (không dùng Ttest để chọn ngưỡng).
- Cờ chỉ dùng độ bất nhất gốc/lật của MediaPipe. Cờ gộp có thêm bất đồng với PIPNet (chỉ cho thí nghiệm, PIPNet không vào `tool/`; PIPNet học trên WFLW nên cũng không còn là so sánh công bằng trên mặt tài xế) có thể khác.

## Lịch sử (WFLW, trước QĐ-001): số cũ KHÔNG còn hiệu lực

Bản cũ (6/10/2026 sáng) đo trên T-dev của WFLW (95 mặt, 4.750 điểm) với ánh xạ ridge học trên WFLW và đáp án 98 điểm của WFLW. Giữ lại để so, **không dùng cho in-cabin**:

| tol (% IOD) | điểm sai | AUROC | bắt được (cờ 15% điểm) | độ chính xác của cờ |
|---|---|---|---|---|
| 3 | 46,8% | 0,70 | 24,9% điểm sai | 77,7% |
| 5 | 27,7% | 0,73 | 34,1% | 63,0% |
| 8 | 14,5% | 0,79 | 47,9% | 46,3% |

`t_flip` ứng với cờ 15% khi đó là 0,0672 (khoảng 7,5 điểm/mặt). Nhận xét cũ: AUROC 0,70-0,79 (có ích nhưng chưa mạnh), lỗi càng lớn cờ bắt càng tốt.
