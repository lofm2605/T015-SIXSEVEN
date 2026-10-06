"""Kiểm phép lật của ánh xạ (P3, tiêu chí 7/10): chạy sau fit_map.py, cần data/ của P1.
WFLW cũ, sẽ thay ở giai đoạn 2 (QĐ-001: tập chính là in-cabin YawDD + DrivFace).

    python tool\\check_flip.py --run <run đã có pred478 cho tập F, Tdev> [--manifest data\\manifest.csv --gt98 data\\gt98.json]

(1) Lật đáp án hai lần: lệch ~0. (2) WFLW 0 và 60 nằm ở nửa trái ảnh cắt (R ở nửa trái) trên mọi ảnh cắt.
(3) Lệch gốc/lật: trung bình 50 điểm trong mỗi mặt (chuẩn hoá IOD đáp án), rồi TRUNG VỊ trên mặt. Tiêu chí kế hoạch: 20 mặt
thẳng F đầu tiên < 3% IOD. In thêm tập rộng hơn để biết biên độ. (4) Đối chứng: quên đổi tên theo cặp thì lệch hàng chục %.
Thoát mã 1 nếu (1), (2) hoặc tiêu chí 20 mặt đầu không đạt.
"""
import argparse
import csv
import json
import os
import sys

import numpy as np

from m28core.mapping import apply_map, map_points
from fit_map import iod98


def d_flip(f, pred, cfg, mp, gt98, rename=True):
    names = [p["name"] for p in cfg["points"]]
    o = apply_map(pred[f]["orig"], mp, cfg)
    if rename:
        u = apply_map(pred[f]["flip"], mp, cfg, flipped=True)
    else:                                           # đối chứng: bỏ lật nhưng quên đổi tên
        raw = map_points(pred[f]["flip"], mp)
        u = {n: [mp.get("flip_width", 512.0) - raw[n][0], raw[n][1]] for n in names}
    return float(np.mean([np.linalg.norm(np.array(o[n]) - np.array(u[n])) for n in names]) / iod98(gt98[f]) * 100)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True)
    p.add_argument("--manifest", default=os.path.join("data", "manifest.csv"))
    p.add_argument("--gt98", default=os.path.join("data", "gt98.json"))
    p.add_argument("--config", default=os.path.join("config", "m28_config.json"))
    p.add_argument("--map", default=os.path.join("config", "map_mp50.json"))
    a = p.parse_args()
    cfg, mp = json.load(open(a.config, encoding="utf-8")), json.load(open(a.map, encoding="utf-8"))
    gt98 = {k[:-4] if k.endswith(".png") else k: v for k, v in json.load(open(a.gt98, encoding="utf-8")).items()}
    pred = json.load(open(os.path.join("runs", a.run, "mediapipe", "pred478.json"), encoding="utf-8"))
    rows = list(csv.DictReader(open(a.manifest, encoding="utf-8")))
    ok = True
    # (1)
    flip = {q["name"]: q["flip"] for q in cfg["points"]}
    g = {q["name"]: gt98[rows[0]["file"][:-4]][q["wflw"]] for q in cfg["points"]}
    once = {flip[n]: [512 - v[0], v[1]] for n, v in g.items()}
    twice = {flip[n]: [512 - v[0], v[1]] for n, v in once.items()}
    err = max(np.linalg.norm(np.array(twice[n]) - np.array(g[n])) for n in g)
    print(f"(1) lật đáp án hai lần: lệch tối đa {err:.2e} px", "đạt" if err <= 0.01 else "KHÔNG ĐẠT")
    ok &= err <= 0.01
    # (2)
    left = sum(gt98[k][0][0] < gt98[k][32][0] and gt98[k][60][0] < gt98[k][72][0] for k in gt98)
    print(f"(2) WFLW 0 và 60 ở nửa trái (x0 < x32 và x60 < x72): {left}/{len(gt98)} ảnh cắt")
    ok &= left == len(gt98)
    # (3)
    def sel(setname, pose0=True):
        return [r["file"][:-4] for r in rows if r["set"] == setname and (r["pose"] == "0" or not pose0)
                and r["file"][:-4] in pred and pred[r["file"][:-4]].get("flip") is not None]
    f20 = sel("F")[:20]
    for label, files in (("20 mặt thẳng F đầu tiên (tiêu chí kế hoạch)", f20), ("mọi mặt thẳng F", sel("F")),
                         ("mọi mặt thẳng Tdev", sel("Tdev"))):
        if files:
            v = [d_flip(f, pred, cfg, mp, gt98) for f in files]
            print(f"(3) lệch gốc/lật, {label}: n={len(files)}, trung vị {np.median(v):.2f}% IOD")
    if f20:
        m20 = float(np.median([d_flip(f, pred, cfg, mp, gt98) for f in f20]))
        ok &= m20 < 3.0
        print("    tiêu chí < 3%:", "đạt" if m20 < 3.0 else "KHÔNG ĐẠT")
        ctrl = float(np.median([d_flip(f, pred, cfg, mp, gt98, rename=False) for f in f20]))
        print(f"(4) đối chứng quên đổi tên theo cặp: trung vị {ctrl:.1f}% IOD (phải lớn hơn hẳn 3%)")
        ok &= ctrl > 10
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
