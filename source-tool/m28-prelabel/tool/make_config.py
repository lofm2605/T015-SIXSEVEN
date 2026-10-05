"""Sinh config/m28_config.json (BẢN NHÁP, P3 chốt) và data/gt50.json từ danh sách 50 điểm WFLW.

    python tool\\make_config.py --out config\\m28_config.json [--manifest data\\manifest.csv --gt98 data\\gt98.json --gt50 data\\gt50.json]

Bố cục 98 điểm WFLW (đã kiểm trên 5.931 mặt thẳng của tập train, xem tests/test_mapping.py):
  0-32 viền mặt (16 = cằm) · 33-41 lông mày ảnh-trái (33-37 mép trên từ đuôi vào đầu, 38-41 mép dưới)
  42-50 lông mày ảnh-phải · 51-54 sống mũi (54 = chóp) · 55-59 chân mũi · 60-67 mắt ảnh-trái (60 khoé ngoài,
  61-63 mí trên, 64 khoé trong, 65-67 mí dưới) · 68-75 mắt ảnh-phải · 76-87 môi ngoài · 88-95 môi trong · 96-97 đồng tử.
Quy ước: side theo người trong ảnh; mặt thẳng thì R ở nửa trái ảnh (WFLW 0-32 bắt đầu ở nửa trái ảnh).
"""
import argparse
import csv
import json
import os

import numpy as np

# Cặp đối xứng WFLW (Mirror98). Viền i <-> 32-i; còn lại kiểm trên dữ liệu trong tests/test_mapping.py.
MIRROR98 = [0] * 98
for i in range(33):
    MIRROR98[i] = 32 - i
for a, b in zip(range(33, 42), [46, 45, 44, 43, 42, 50, 49, 48, 47]):
    MIRROR98[a] = b
    MIRROR98[b] = a
for i in (51, 52, 53, 54, 57):
    MIRROR98[i] = i
for a, b in ((55, 59), (56, 58), (60, 72), (61, 71), (62, 70), (63, 69), (64, 68), (65, 75), (66, 74), (67, 73),
             (76, 82), (77, 81), (78, 80), (83, 87), (84, 86), (88, 92), (89, 91), (93, 95), (96, 97)):
    MIRROR98[a], MIRROR98[b] = b, a
for i in (79, 85, 90, 94):
    MIRROR98[i] = i

OUT = 512
CONTOUR = list(range(0, 33))
# (chỉ số WFLW, vùng, type, curve, line, anchor). Thứ tự = thứ tự điểm trong config (và trong CVAT).
SPEC = (
    [(i, "jaw", "C", CONTOUR, "jaw", i in (0, 16, 32)) for i in range(0, 33, 2)]
    + [(i, "brow", "E" if i in (33, 37) else "C", None if i in (33, 37) else list(range(33, 38)), "brow_R", i in (33, 37))
       for i in range(33, 38)]
    + [(i, "brow", "E" if i in (42, 46) else "C", None if i in (42, 46) else list(range(42, 47)), "brow_L", i in (42, 46))
       for i in range(42, 47)]
    + [(51, "nose", "C", [51, 52, 53, 54], "nose_bridge", False), (54, "nose", "E", None, "nose_bridge", True),
       (55, "nose", "E", None, "nose_base", True), (57, "nose", "C", [55, 56, 57, 58, 59], "nose_base", False),
       (59, "nose", "E", None, "nose_base", True)]
    + [(60, "eye", "E", None, "eye_R", True), (62, "eye", "C", [60, 61, 62, 63, 64], "eye_R", False),
       (64, "eye", "E", None, "eye_R", True), (66, "eye", "C", [64, 65, 66, 67, 60], "eye_R", False),
       (68, "eye", "E", None, "eye_L", True), (70, "eye", "C", [68, 69, 70, 71, 72], "eye_L", False),
       (72, "eye", "E", None, "eye_L", True), (74, "eye", "C", [72, 73, 74, 75, 68], "eye_L", False)]
    + [(76, "lip", "E", None, "lip_outer", True), (77, "lip", "C", list(range(76, 83)), "lip_outer", False),
       (79, "lip", "C", list(range(76, 83)), "lip_outer", True), (81, "lip", "C", list(range(76, 83)), "lip_outer", False),
       (82, "lip", "E", None, "lip_outer", True),
       (84, "lip", "C", [82, 83, 84, 85, 86, 87, 76], "lip_outer", False),
       (85, "lip", "C", [82, 83, 84, 85, 86, 87, 76], "lip_outer", True),
       (86, "lip", "C", [82, 83, 84, 85, 86, 87, 76], "lip_outer", False),
       (90, "lip", "C", [88, 89, 90, 91, 92], "lip_inner", False), (94, "lip", "C", [92, 93, 94, 95, 88], "lip_inner", False)]
)
COINCIDE = ((62, 66), (70, 74), (90, 94))        # mí trên/dưới khi nhắm, môi trong khi khép
CLOSED = {"jaw": False, "brow_R": False, "brow_L": False, "nose_bridge": False, "nose_base": False,
          "eye_R": True, "eye_L": True, "lip_outer": True, "lip_inner": False}


def side_of(w):
    m = MIRROR98[w]
    if m == w:
        return "M"
    return "R" if w < m else "L"     # chỉ số nhỏ hơn nằm nửa trái ảnh = R (viền, mày, mắt, môi đều đánh số từ trái ảnh)


def build_config(tmpl=None, t_flip=None):
    names = {}
    pts = []
    for n, (w, region, typ, curve, line, anchor) in enumerate(SPEC, 1):
        names[w] = f"p{n:02d}_{region}_{side_of(w)}"
    for w, region, typ, curve, line, anchor in SPEC:
        assert MIRROR98[w] in names, f"điểm {w} không có cặp đối xứng {MIRROR98[w]} trong bộ 50"
        pts.append({"name": names[w], "region": region, "side": side_of(w), "flip": names[MIRROR98[w]], "wflw": w,
                    "type": typ, "curve": curve, "line": line, "anchor": int(anchor), "coincide": None,
                    "tmpl": None})
    by = {p["wflw"]: p for p in pts}
    for a, b in COINCIDE:
        by[a]["coincide"], by[b]["coincide"] = by[b]["name"], by[a]["name"]
    if tmpl is not None:
        for p, t in zip(pts, tmpl):
            p["tmpl"] = [round(float(t[0]), 2), round(float(t[1]), 2)]
    return {"version": 1, "status": "NHAP - cho P3 chot, dong bang 12/10", "n_points": len(pts), "points": pts,
            "lines": {k: {"closed": v} for k, v in CLOSED.items()},
            "iod_points": [by[60]["name"], by[72]["name"]], "t_flip": t_flip, "tolerance": None}


def gt50_from_gt98(cfg, gt98):
    """gt98: {file: [[x, y] * 98]} theo ảnh cắt -> {file: {tên điểm: [x, y]}}."""
    return {f: {p["name"]: list(map(float, g[p["wflw"]])) for p in cfg["points"]} for f, g in gt98.items()}


def template(manifest_rows, gt98):
    """Khuôn trung bình 50 điểm (toạ độ ảnh cắt 512): trung bình đáp án các mặt F có pose = 0."""
    rows = [r for r in manifest_rows if r["set"] == "F" and r["pose"] == "0" and r["file"] in gt98]
    ws = [w for w, *_ in SPEC]
    return np.mean([np.asarray(gt98[r["file"]])[ws] for r in rows], axis=0)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=os.path.join("config", "m28_config.json"))
    p.add_argument("--manifest")
    p.add_argument("--gt98")
    p.add_argument("--gt50")
    p.add_argument("--t-flip", type=float, help="ngưỡng cờ low_conf do P2 chọn trên T-dev (null = chưa có)")
    a = p.parse_args()
    tmpl, gt98 = None, None
    if a.gt98:
        gt98 = json.load(open(a.gt98, encoding="utf-8"))
    if a.gt98 and a.manifest:
        with open(a.manifest, encoding="utf-8") as f:
            tmpl = template(list(csv.DictReader(f)), gt98)
    cfg = build_config(tmpl, a.t_flip)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(cfg, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Đã ghi {a.out}: {cfg['n_points']} điểm" + (", có khuôn tmpl" if tmpl is not None else ", chưa có tmpl"))
    if a.gt50 and gt98:
        json.dump(gt50_from_gt98(cfg, gt98), open(a.gt50, "w", encoding="utf-8"))
        print(f"Đã ghi {a.gt50}: {len(gt98)} ảnh x {cfg['n_points']} điểm")


if __name__ == "__main__":
    main()
