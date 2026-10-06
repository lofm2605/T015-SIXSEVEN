"""LỊCH SỬ, KHÔNG DÙNG (QĐ-001). Khớp phép đổi 478 -> N điểm (config) và ghi config/map_mp50.json, data/mp50.json (P3, 7/10). Chỉ dùng numpy.
Đã thay bằng chọn đỉnh trực tiếp (tool/make_config.py); giữ để làm số so sánh.

    python tool\\legacy_wflw\\fit_map.py --run <run đã chạy crop+mediapipe cho tập F> [--manifest data\\manifest.csv --gt98 data\\gt98.json]

Theo kế hoạch: chia mặt F một lần theo seed thành 240 khớp / 60 kiểm (chia TRƯỚC khi bỏ mặt no_face, nên số mặt thực có thể
ít hơn) -> hình trung bình (Procrustes về mặt đầu tiên theo mã của tập khớp) -> với mỗi điểm lấy k = 6 đỉnh MediaPipe gần
nhất trên hình trung bình -> ridge, λ trong {0,1; 1; 10; 100} chọn trên 192 khớp / 48 đo (chia trong tập khớp, KHÔNG dùng mặt
kiểm) theo chỉ số CHÍNH (điểm góc E đo điểm-điểm, điểm giữa đường C đo tới đường cong) -> khớp lại trên cả tập khớp ->
báo trên mặt kiểm. Ghi thêm `flip_width` (hằng số bỏ lật tốt nhất) và `defs` (wflw, flip của từng điểm) vào map.
Số trên mặt kiểm nhỏ, dễ hơn T-dev/T-test: dùng trung vị làm số chính.
"""
import argparse
import csv
import json
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from m28core.mapping import similarity, to_mean  # noqa: E402
from make_config_wflw import gt50_from_gt98  # noqa: E402
from mapping_ridge import apply_map, fit_ridge  # noqa: E402

LAMBDAS = (0.1, 1.0, 10.0, 100.0)
K = 6
BAD = 10.0            # mặt hỏng: NME >= 10% IOD (p3-anh-xa.md mục 3)
MIN_FIT = 50


def iod98(g98):
    return float(np.linalg.norm(np.asarray(g98[60]) - np.asarray(g98[72])))


def split_F(files, seed, n_fit=240):
    """Chia các mặt F thành khớp/kiểm một lần theo seed (trước khi bỏ no_face)."""
    f = sorted(files)
    random.Random(seed).shuffle(f)
    return sorted(f[:n_fit]), sorted(f[n_fit:])


def mean_shape(pts_list):
    ref = pts_list[0]
    return np.mean([to_mean(p, *similarity(p, ref)) for p in pts_list], axis=0)


def build_features(pred478, gt50, files, mean478, names):
    """Mỗi mặt: (478 điểm ở khung trung bình, gt50 ở khung trung bình)."""
    out = []
    for f in files:
        p = np.asarray(pred478[f]["orig"], float)
        s, R, t = similarity(p, mean478)
        ym = np.array([to_mean(np.asarray(gt50[f][n], float)[None], s, R, t)[0] for n in names])
        out.append((to_mean(p, s, R, t), ym))
    return out


def fit_all(feats, names, mean478, k, lam, cfg_points=None):
    """Trả mp_map (dict, ghi được ra JSON) khớp trên feats."""
    Y = np.array([y for _, y in feats])                        # (n, N, 2)
    tgt_mean = Y.mean(0)                                       # vị trí trung bình mỗi điểm trên khung trung bình
    pts = {}
    for i, n in enumerate(names):
        idx = np.argsort(np.linalg.norm(mean478 - tgt_mean[i], axis=1))[:k].tolist()
        X = np.array([pm[idx].reshape(-1) for pm, _ in feats])
        mx, W, my = fit_ridge(X, Y[:, i], lam)
        pts[n] = {"idx": idx, "mx": mx.tolist(), "W": W.tolist(), "my": my.tolist()}
    m = {"names": list(names), "k": k, "lambda": lam, "flip_width": 512.0, "mean478": mean478.tolist(), "points": pts}
    if cfg_points:
        m["defs"] = {p["name"]: {"wflw": p["wflw"], "flip": p["flip"]} for p in cfg_points}
    return m


def point_to_curve(p, curve):
    """Khoảng cách ngắn nhất từ điểm p tới đường gấp khúc curve (m, 2); đoạn dài 0 không chia cho 0."""
    a, ab = curve[:-1], curve[1:] - curve[:-1]
    u = ((p - a) * ab).sum(1) / np.maximum((ab ** 2).sum(1), 1e-9)
    return float(np.linalg.norm(a + np.clip(u, 0, 1)[:, None] * ab - p, axis=1).min())


def face_nme(pr, gt50, g98, cfg_points):
    """(NME chính: E điểm-điểm + C tới đường cong; NME phụ: điểm-điểm cả 50 điểm), % IOD."""
    d = iod98(g98)
    g98 = np.asarray(g98, float)
    main_, sec = [], []
    for p in cfg_points:
        pt, gt = np.asarray(pr[p["name"]], float), np.asarray(gt50[p["name"]], float)
        e = float(np.linalg.norm(pt - gt))
        sec.append(e)
        main_.append(e if p["type"] == "E" else point_to_curve(pt, g98[p["curve"]]))
    return float(np.mean(main_) / d * 100), float(np.mean(sec) / d * 100)


def nme(mp_map, cfg, pred478, gt50, gt98, files):
    """{mặt: (chính, phụ)}."""
    return {f: face_nme(apply_map(pred478[f]["orig"], mp_map, cfg), gt50[f], gt98[f], cfg["points"]) for f in files}


def wrong_face(pred478, gt50, gt98, files, names):
    """Mặt mà MediaPipe dò nhầm người (tâm 478 điểm cách tâm đáp án > 0,5 IOD): loại khỏi tập khớp/chọn λ."""
    bad = []
    for f in files:
        c = np.asarray(pred478[f]["orig"], float).mean(0)
        g = np.mean([gt50[f][n] for n in names], axis=0)
        if np.linalg.norm(c - g) > 0.5 * iod98(gt98[f]):
            bad.append(f)
    return bad


def estimate_flip_width(mp_map, cfg, pred478, files):
    """Hằng số w sao cho điểm đã bỏ lật (x' = w - x) trùng điểm của ảnh gốc về trung bình."""
    dx = []
    for f in files:
        if pred478[f].get("flip") is None:
            continue
        o = apply_map(pred478[f]["orig"], mp_map, cfg)
        u = apply_map(pred478[f]["flip"], mp_map, cfg, flipped=True, width=512.0)
        dx += [u[n][0] - o[n][0] for n in o]
    return float(512.0 - np.mean(dx)) if dx else 512.0


def write_json_atomic(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, allow_nan=False)
    os.replace(tmp, path)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")     # Windows: stdout chuyển hướng không bị cp1252
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True)
    p.add_argument("--manifest", default=os.path.join("data", "manifest.csv"))
    p.add_argument("--gt98", default=os.path.join("data", "gt98.json"))
    p.add_argument("--config", default=os.path.join("config", "m28_config.json"))
    p.add_argument("--out", default=os.path.join("config", "map_mp50.json"))
    p.add_argument("--mp50-out", default=os.path.join("data", "mp50.json"), help="nháp 50 điểm cho MỌI mặt có pred478 ('' = không ghi)")
    p.add_argument("--seed", type=int, default=5)
    a = p.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    names = [q["name"] for q in cfg["points"]]
    gt98 = {k[:-4] if k.endswith(".png") else k: v for k, v in json.load(open(a.gt98, encoding="utf-8")).items()}
    gt50 = {k[:-4] if k.endswith(".png") else k: v for k, v in gt50_from_gt98(cfg, gt98).items()}
    pred = json.load(open(os.path.join("runs", a.run, "mediapipe", "pred478.json"), encoding="utf-8"))
    with open(a.manifest, encoding="utf-8") as f:
        F = [r["file"][:-4] for r in csv.DictReader(f) if r["set"] == "F"]
    fit0, check0 = split_F(F, a.seed)
    have = lambda L: [f for f in L if f in pred and f in gt98]                  # noqa: E731  bỏ no_face
    fit_files, check_files = have(fit0), have(check0)
    dropped = wrong_face(pred, gt50, gt98, fit_files, names)
    fit_files = [f for f in fit_files if f not in dropped]
    if len(fit_files) < MIN_FIT or not check_files:
        sys.exit(f"Quá ít mặt F có MediaPipe: khớp {len(fit_files)} (cần >= {MIN_FIT}), kiểm {len(check_files)}. "
                 f"Chạy prepare cho cả tập F (--set F --box wflw) rồi thử lại.")
    print(f"F: khớp {len(fit_files)} mặt, kiểm {len(check_files)} mặt (đã bỏ no_face; loại {len(dropped)} mặt dò nhầm người)")
    mean478 = mean_shape([np.asarray(pred[f]["orig"], float) for f in fit_files])
    n_tr = int(round(len(fit_files) * 0.8))
    tr, va = fit_files[:n_tr], fit_files[n_tr:]
    tr_feats = build_features(pred, gt50, tr, mean478, names)
    scores = {}
    for lam in LAMBDAS:
        m = fit_all(tr_feats, names, mean478, K, lam, cfg["points"])
        scores[lam] = float(np.mean([v[0] for v in nme(m, cfg, pred, gt50, gt98, va).values()]))
        print(f"  lambda={lam:g}: NME chính {scores[lam]:.3f}% IOD trên {len(va)} mặt đo")
    best = min(scores, key=scores.get)
    final = fit_all(build_features(pred, gt50, fit_files, mean478, names), names, mean478, K, best, cfg["points"])
    final["flip_width"] = estimate_flip_width(final, cfg, pred, fit_files)
    res = nme(final, cfg, pred, gt50, gt98, check_files)
    main_v, sec_v = np.array([v[0] for v in res.values()]), np.array([v[1] for v in res.values()])
    final["meta"] = {
        "seed": a.seed, "n_fit": len(fit_files), "n_check": len(check_files), "lambda_scores": {str(k): v for k, v in scores.items()},
        "lambda_at_grid_edge": best in (LAMBDAS[0], LAMBDAS[-1]),
        "nme_main_check_mean": float(main_v.mean()), "nme_main_check_median": float(np.median(main_v)),
        "frac_bad_main_check": float((main_v >= BAD).mean()),
        "nme_p2p_check_mean": float(sec_v.mean()), "nme_p2p_check_median": float(np.median(sec_v)),
        "reference_face": fit_files[0], "fit_files": fit_files, "lambda_train_files": tr, "lambda_eval_files": va,
        "check_files": check_files, "dropped_wrong_face": dropped}
    write_json_atomic(a.out, final)
    print(f"lambda chọn = {best:g}{' (sát mép lưới)' if final['meta']['lambda_at_grid_edge'] else ''}; flip_width = {final['flip_width']:.2f}")
    print(f"{len(check_files)} mặt kiểm: NME chính trung bình {main_v.mean():.2f}%, trung vị {np.median(main_v):.2f}%, "
          f"mặt hỏng {100 * (main_v >= BAD).mean():.1f}%; NME phụ (điểm-điểm 50 điểm) {sec_v.mean():.2f}% / {np.median(sec_v):.2f}% -> {a.out}")
    if a.mp50_out:
        out = {f: {"orig": apply_map(v["orig"], final, cfg),
                   "flip": apply_map(v["flip"], final, cfg, flipped=True) if v.get("flip") else None} for f, v in pred.items()}
        write_json_atomic(a.mp50_out, out)
        print(f"Đã ghi {a.mp50_out}: {len(out)} mặt")


if __name__ == "__main__":
    main()
