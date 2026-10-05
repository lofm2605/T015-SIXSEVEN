"""Khớp phép đổi 478 -> N điểm (config) và ghi config/map_mp50.json (P3, 7/10). Chỉ dùng numpy.

    python tool\\fit_map.py --run <run đã chạy crop+mediapipe cho tập F> --manifest data\\manifest.csv --gt98 data\\gt98.json

Các bước theo kế hoạch: bỏ mặt no_face -> hình trung bình (Procrustes về mặt F đầu tiên) -> với mỗi điểm lấy
k = 6 đỉnh MediaPipe gần nhất trên hình trung bình -> ridge, λ trong {0,1; 1; 10; 100}, chia một lần 240 mặt khớp /
60 mặt kiểm (chia TRƯỚC khi bỏ no_face), chọn λ trên phần dành riêng (192 khớp / 48 đo trong 240), báo NME trên 60 mặt kiểm.
"""
import argparse
import csv
import json
import os
import random

import numpy as np

from m28core.mapping import apply_map, fit_ridge, from_mean, similarity, to_mean

LAMBDAS = (0.1, 1.0, 10.0, 100.0)
K = 6


def iod98(g98):
    return float(np.linalg.norm(np.asarray(g98[60]) - np.asarray(g98[72])))


def split_F(files, seed, n_fit=240):
    """Chia các mặt F thành khớp/kiểm một lần theo seed (trước khi bỏ no_face)."""
    f = sorted(files)
    random.Random(seed).shuffle(f)
    return f[:n_fit], f[n_fit:]


def mean_shape(pts_list):
    ref = pts_list[0]
    aligned = [to_mean(p, *similarity(p, ref)) for p in pts_list]
    return np.mean(aligned, axis=0)


def build_features(pred478, gt50, files, mean478, names):
    """Mỗi mặt: s, R, t từ 478 điểm; X = toạ độ đỉnh gần nhất... (chưa chọn đỉnh) ; Y = gt50 ở khung trung bình."""
    out = []
    for f in files:
        p = np.asarray(pred478[f]["orig"], float)
        s, R, t = similarity(p, mean478)
        pm = to_mean(p, s, R, t)
        ym = np.array([to_mean(np.asarray(gt50[f][n], float)[None], s, R, t)[0] for n in names])
        out.append((pm, ym, (s, R, t)))
    return out


def fit_all(feats, names, mean478, k, lam):
    """Trả mp_map (dict) khớp trên feats."""
    Y = np.array([y for _, y, _ in feats])                     # (n, N, 2)
    tgt_mean = Y.mean(0)                                       # vị trí trung bình mỗi điểm trên khung trung bình
    pts = {}
    for i, n in enumerate(names):
        idx = np.argsort(np.linalg.norm(mean478 - tgt_mean[i], axis=1))[:k].tolist()
        X = np.array([pm[idx].reshape(-1) for pm, _, _ in feats])
        mx, W, my = fit_ridge(X, Y[:, i], lam)
        pts[n] = {"idx": idx, "mx": mx.tolist(), "W": W.tolist(), "my": my.tolist()}
    return {"names": list(names), "k": k, "lambda": lam, "mean478": mean478.tolist(), "points": pts}


def nme(mp_map, cfg, pred478, gt50, gt98, files, flipped=False, types=("E", "C")):
    """NME điểm-điểm trung bình, % IOD, cho từng mặt. (Điểm C đo tới đường cong là việc của eval50.py.)"""
    names = [p["name"] for p in cfg["points"]]
    res = {}
    for f in files:
        key = "flip" if flipped else "orig"
        pr = apply_map(pred478[f][key], mp_map, cfg, flipped=flipped)
        d = np.mean([np.linalg.norm(np.asarray(pr[n]) - np.asarray(gt50[f][n])) for n in names])
        res[f] = float(d / iod98(gt98[f]) * 100)
    return res


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True)
    p.add_argument("--manifest", default=os.path.join("data", "manifest.csv"))
    p.add_argument("--gt98", default=os.path.join("data", "gt98.json"))
    p.add_argument("--config", default=os.path.join("config", "m28_config.json"))
    p.add_argument("--out", default=os.path.join("config", "map_mp50.json"))
    p.add_argument("--seed", type=int, default=5)
    a = p.parse_args()
    from make_config import gt50_from_gt98
    cfg = json.load(open(a.config, encoding="utf-8"))
    names = [q["name"] for q in cfg["points"]]
    gt98 = {k[:-4] if k.endswith(".png") else k: v for k, v in json.load(open(a.gt98, encoding="utf-8")).items()}
    gt50 = gt50_from_gt98(cfg, gt98)
    pred = json.load(open(os.path.join("runs", a.run, "mediapipe", "pred478.json"), encoding="utf-8"))
    with open(a.manifest, encoding="utf-8") as f:
        F = [r["file"][:-4] for r in csv.DictReader(f) if r["set"] == "F"]
    fit_files, check_files = split_F(F, a.seed)
    have = lambda L: [f for f in L if f in pred]                      # noqa: E731  bỏ no_face
    fit_files, check_files = have(fit_files), have(check_files)
    print(f"F: khớp {len(fit_files)} mặt, kiểm {len(check_files)} mặt (đã bỏ no_face)")
    mean478 = mean_shape([np.asarray(pred[f]["orig"], float) for f in fit_files])
    n_tr = int(round(len(fit_files) * 0.8))
    tr, va = fit_files[:n_tr], fit_files[n_tr:]
    tr_feats = build_features(pred, gt50, tr, mean478, names)
    scores = {}
    for lam in LAMBDAS:
        m = fit_all(tr_feats, names, mean478, K, lam)
        scores[lam] = float(np.mean(list(nme(m, cfg, pred, gt50, gt98, va).values())))
        print(f"  λ={lam:g}: NME {scores[lam]:.3f}% IOD trên {len(va)} mặt đo")
    best = min(scores, key=scores.get)
    final = fit_all(build_features(pred, gt50, fit_files, mean478, names), names, mean478, K, best)
    res = nme(final, cfg, pred, gt50, gt98, check_files)
    final["meta"] = {"seed": a.seed, "n_fit": len(fit_files), "n_check": len(check_files), "lambda_scores": scores,
                     "nme_check_mean": float(np.mean(list(res.values()))),
                     "nme_check_median": float(np.median(list(res.values())))}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(final, open(a.out, "w"))
    print(f"λ chọn = {best:g}; NME {len(check_files)} mặt kiểm: trung bình {final['meta']['nme_check_mean']:.3f}%, "
          f"trung vị {final['meta']['nme_check_median']:.3f}% IOD -> {a.out}")


if __name__ == "__main__":
    main()
