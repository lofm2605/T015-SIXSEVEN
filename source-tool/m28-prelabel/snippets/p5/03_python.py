# Trích từ de-tai-m28/p5-thi-nghiem.md — mục: Làm thế nào › Chất lượng. Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
import numpy as np, pandas as pd
n = pd.read_csv("nme_per_face.csv")   # từ module của P3, đơn vị % IOD
rng = np.random.default_rng(28)
for col in ["nme", "nme_eye"]:
    p = n.pivot(index="face_id", columns="condition", values=col).dropna()
    diff = (p["assisted"] - p["manual"]).to_numpy()
    boot = [rng.choice(diff, len(diff)).mean() for _ in range(2000)]
    lo, hi = np.percentile(boot, [5, 95])
    kq = "dat" if hi <= 0.5 else "khong dat" if lo > 0.5 else "chua ket luan"
    print(col, len(diff), f"TB {diff.mean():+.2f}, [{lo:+.2f}, {hi:+.2f}] -> {kq}")
