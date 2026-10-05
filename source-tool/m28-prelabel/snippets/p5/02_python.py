# Trích từ de-tai-m28/p5-thi-nghiem.md — mục: Làm thế nào › Thời gian. Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
import glob, numpy as np, pandas as pd
d = pd.concat(pd.read_csv(f) for f in glob.glob("timing_P*.csv")); d.to_csv("timing_log.csv", index=False)
t = d[d.warmup == 0]
m24 = t.groupby(["date", "person", "condition"]).agg(so_anh=("face_id", "count"), so_phut=("seconds", "sum")).reset_index()
m24["so_phut"] = (m24.so_phut / 60).round(1); m24.to_csv("timing_m24.csv", index=False)
x = t[t.task.isin(["m28-manual", "m28-assisted"])].reset_index(drop=True)
def geo(w):                                   # w = số lần mỗi dòng được bốc lại
    s = (x.seconds * w).groupby([x.person, x.condition]).sum().unstack()
    n = pd.Series(w, index=x.index).groupby([x.person, x.condition]).sum().unstack()
    m = s / n                                 # giây trung bình mỗi mặt (7 hay 8 mặt đều công bằng)
    r = m["assisted"] / m["manual"]
    return np.exp(np.log(r).mean()), r
g, r = geo(np.ones(len(x)))
rng, boot = np.random.default_rng(28), []
for _ in range(2000):                         # bốc lại mặt trong từng khối, chung cho hai cách
    w = np.zeros(len(x))
    for b, rows in x.groupby("block").groups.items():
        seqs = sorted(x.seq.loc[rows].unique()); pick = list(rng.choice(seqs, len(seqs)))
        w[rows] = [pick.count(s) for s in x.seq.loc[rows]]
    boot.append(geo(w)[0])
sv = x.groupby("condition").seconds.mean()
print(r.round(2), f"\nTB nhan {g:.2f}, KTC 90% {np.percentile(boot, [5, 95]).round(2)}")
print("Dat" if g <= 0.80 and (r < 1).sum() >= 4 else "Chua dat: doc KTC")
print("Gio tiet kiem / 1.000 mat (tron X):", round((sv["manual"] - sv["assisted"]) * 1000 / 3600, 1))
mf = pd.read_csv("manifest.csv"); mf.index = mf.file.str.replace(".png", "", regex=False)
kho = x.face_id.map(mf.pose | mf.occlusion) == 1      # mặt nghiêng hoặc bị che
for ten, nhom in [("nghieng/che", x[kho]), ("con lai", x[~kho])]:
    sv = nhom.groupby("condition").seconds.mean()
    print(ten, sv.round(1).to_dict(), "gio tiet kiem / 1.000 mat:", round((sv["manual"] - sv["assisted"]) * 1000 / 3600, 1))
