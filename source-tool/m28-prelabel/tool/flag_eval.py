"""Đo cờ low_conf (P2, 8/10 và 10/10): cờ bắt được bao nhiêu điểm sai? Chỉ dùng numpy, chỉ chạy trên T-dev.

    python tool\\flag_eval.py --run <run có pred478 cho Tdev> [--tol 3.0] [--set Tdev]

Điểm sai = lỗi so với đáp án WFLW > tol (% IOD; kế hoạch tạm 3% cho tới khi P3 có sai số vùng ngày 10/10). Lỗi: điểm E đo
điểm-điểm, điểm C đo tới đường cong (cùng chỉ số chính của eval50). Điểm số nghi sai = lệch gốc/lật / khoảng cách hai mắt.
In: tỉ lệ điểm sai, AUROC (toàn bộ và theo vùng), và với từng ngưỡng (phân vị) tỉ lệ điểm bị cờ, % điểm sai bị bắt, độ chính xác.
Không đọc Ttest: T-test chỉ chạy đúng một lần ngày 20/10.
"""
import argparse
import csv
import json
import os
import sys

import numpy as np

from fit_map import iod98, point_to_curve
from m28core.mapping import apply_map

QUANTILES = (0.5, 0.7, 0.8, 0.85, 0.9, 0.95)


def auroc(score, bad):
    """Xác suất điểm sai có điểm số cao hơn điểm đúng (có xử lý hoà). Không cần scipy."""
    score, bad = np.asarray(score, float), np.asarray(bad, bool)
    n1, n0 = int(bad.sum()), int((~bad).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    order = np.argsort(score, kind="mergesort")
    ranks = np.empty(len(score))
    s = score[order]
    i = 0
    while i < len(s):                       # hạng trung bình cho các điểm hoà
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return float((ranks[bad].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def collect_points(files, pred, cfg, mp, gt98):
    """Mỗi điểm của mỗi mặt: (vùng, điểm số nghi sai, lỗi % IOD)."""
    names = [p["name"] for p in cfg["points"]]
    e1, e2 = cfg["iod_points"]
    rows = []
    for f in files:
        o = apply_map(pred[f]["orig"], mp, cfg)
        u = apply_map(pred[f]["flip"], mp, cfg, flipped=True)
        iod_pred = np.linalg.norm(np.array(o[e1]) - np.array(o[e2])) or 1.0
        g98 = np.asarray(gt98[f], float)
        d = iod98(g98)
        for p in cfg["points"]:
            n = p["name"]
            pt = np.array(o[n])
            gt = g98[p["wflw"]]
            e = np.linalg.norm(pt - gt) if p["type"] == "E" else point_to_curve(pt, g98[p["curve"]])
            rows.append((p["region"], float(np.linalg.norm(pt - np.array(u[n])) / iod_pred), float(e / d * 100), f))
    return rows


def report(rows, tol, out=print):
    reg = np.array([r[0] for r in rows])
    score = np.array([r[1] for r in rows])
    err = np.array([r[2] for r in rows])
    bad = err > tol
    out(f"{len(set(r[3] for r in rows))} mặt, {len(rows)} điểm; điểm sai (lỗi > {tol:g}% IOD): {100 * bad.mean():.1f}%")
    out(f"AUROC toàn bộ: {auroc(score, bad):.3f}   (0,5 = cờ không có tác dụng; 1 = hoàn hảo)")
    out("AUROC theo vùng: " + ", ".join(f"{r} {auroc(score[reg == r], bad[reg == r]):.3f} (sai {100 * bad[reg == r].mean():.0f}%)"
                                          for r in sorted(set(reg))))
    out("phân vị  ngưỡng t_flip  điểm bị cờ  % điểm sai bị bắt  độ chính xác  cờ/mặt")
    nface = len(set(r[3] for r in rows))
    table = []
    for q in QUANTILES:
        t = float(np.quantile(score, q))
        flag = score > t
        caught = float((flag & bad).sum() / max(bad.sum(), 1) * 100)
        prec = float((flag & bad).sum() / max(flag.sum(), 1) * 100)
        table.append((q, t, flag.mean() * 100, caught, prec, flag.sum() / nface))
        out(f"{q:7.2f}  {t:12.4f}  {flag.mean() * 100:9.1f}%  {caught:16.1f}%  {prec:11.1f}%  {flag.sum() / nface:6.1f}")
    return table


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True)
    p.add_argument("--set", default="Tdev", choices=["Tdev", "F", "D", "G", "X"], help="Ttest không được phép (chỉ chạy một lần ngày 20/10)")
    p.add_argument("--tol", type=float, default=3.0)
    p.add_argument("--manifest", default=os.path.join("data", "manifest.csv"))
    p.add_argument("--gt98", default=os.path.join("data", "gt98.json"))
    p.add_argument("--config", default=os.path.join("config", "m28_config.json"))
    p.add_argument("--map", default=os.path.join("config", "map_mp50.json"))
    a = p.parse_args()
    cfg, mp = json.load(open(a.config, encoding="utf-8")), json.load(open(a.map, encoding="utf-8"))
    gt98 = {k[:-4] if k.endswith(".png") else k: v for k, v in json.load(open(a.gt98, encoding="utf-8")).items()}
    pred = json.load(open(os.path.join("runs", a.run, "mediapipe", "pred478.json"), encoding="utf-8"))
    with open(a.manifest, encoding="utf-8") as f:
        files = [r["file"][:-4] for r in csv.DictReader(f) if r["set"] == a.set]
    files = [f for f in files if f in pred and pred[f].get("flip") is not None and f in gt98]
    if not files:
        sys.exit("Không có mặt nào có cả ảnh gốc, ảnh lật và đáp án. Chạy prepare cho tập này trước.")
    report(collect_points(files, pred, cfg, mp, gt98), a.tol)


if __name__ == "__main__":
    main()
