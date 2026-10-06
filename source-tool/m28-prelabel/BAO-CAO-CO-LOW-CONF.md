# Cờ low_conf bắt được bao nhiêu điểm sai? (bản nháp cho P2, ngày 6/10/2026)

Đo bằng `python tool\flag_eval.py --run <run> --set Tdev --tol <số>` trên **T-dev (95 mặt có ảnh gốc và ảnh lật, 4.750 điểm)**, ảnh WFLW thật,
ánh xạ 478→50 bản nháp (`config\map_mp50.json`). Không đọc T-test. Điểm số nghi sai = lệch giữa kết quả ảnh gốc và ảnh lật (đã bỏ lật) / khoảng cách hai mắt.
Điểm "sai" = lỗi so với đáp án WFLW lớn hơn `tol` (% IOD; điểm góc đo điểm-điểm, điểm giữa đường đo tới đường cong).
**`tol` thật chưa có**: P3 tính từ sai số hai người gán cùng mặt G ngày 10/10. Bảng dưới cho ba mức để thấy xu hướng.

| tol (% IOD) | điểm sai | AUROC | bắt được (cờ 15% điểm) | độ chính xác của cờ |
|---|---|---|---|---|
| 3 | 46,8% | 0,70 | 24,9% điểm sai | 77,7% |
| 5 | 27,7% | 0,73 | 34,1% | 63,0% |
| 8 | 14,5% | 0,79 | 47,9% | 46,3% |

Ngưỡng `t_flip` ứng với "cờ 15% số điểm" (quantile 0,85 của điểm số trên T-dev) là **0,0672** (khoảng 7,5 điểm bị cờ trên mỗi mặt).

Đọc kết quả:
- Cờ **có ích nhưng chưa mạnh**: AUROC 0,70–0,79 (0,5 là vô dụng). Lỗi càng lớn thì cờ bắt càng tốt (gần một nửa điểm lệch trên 8% IOD nằm trong 15% điểm bị cờ), lỗi nhỏ thì bắt kém.
- Ở `tol` = 3% gần một nửa số điểm bị coi là sai: một phần là lệch định nghĩa điểm giữa WFLW và MediaPipe, không phải lỗi nháp. P3 sẽ tách phần này ngày 10/10 (điểm lệch định nghĩa).
- Cờ chỉ dùng độ bất nhất gốc/lật của MediaPipe. Cờ gộp có thêm bất đồng với PIPNet (chỉ cho thí nghiệm, PIPNet không vào `tool/`) có thể tốt hơn: P2 đo ngày 8/10.
- Đề xuất cho họp 12/10: dùng `t_flip` = 0,0672 cho công cụ giao đi; ghi rõ cờ không phải đảm bảo, trang rà soát vẫn là hàng rào chính.
- `config\m28_config.json` vẫn để `t_flip: null` theo kế hoạch cho tới khi P2 chốt.
