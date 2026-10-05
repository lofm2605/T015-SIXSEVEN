# Trích từ de-tai-m28/p2-model.md — mục: Làm thế nào › Cờ và ngưỡng (8 và 10/10). Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
import numpy as np
# mpo, mpf, pip: (mặt, 50, 2) ảnh 512; mpf đã bỏ lật. bad: lỗi nháp > sai số vùng (hàm P3)
# EYE_R, EYE_L: chỉ số trong 50 điểm ứng với WFLW 60, 72; REGIONS: chỉ số điểm từng vùng
iod = np.linalg.norm(mpo[:, EYE_R] - mpo[:, EYE_L], axis=1)[:, None]
d_flip = np.linalg.norm(mpo - mpf, axis=2) / iod
offset = (mpo - pip).mean(axis=0)            # chỉ đo trên T-dev, lưu offset.npy
d_model = np.linalg.norm(mpo - pip - offset, axis=2) / iod
score = np.maximum(d_flip, d_model)

t = np.quantile(score, 0.85)                 # cờ <= 15% số điểm
flag = score > t
print("cờ/mặt", flag.sum(1).mean(), "bắt", flag[bad].mean())

def auroc(s, y):                             # y: True = điểm sai; không cần scipy
    r = s.argsort().argsort() + 1.0
    n1 = y.sum(); n0 = y.size - n1
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
print("AUROC vùng", np.nanmean([auroc(score[:, R].ravel(), bad[:, R].ravel()) for R in REGIONS]))
