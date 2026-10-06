"""LỊCH SỬ, KHÔNG DÙNG (QĐ-001). Ánh xạ ridge 478 -> 50 học trên đáp án WFLW (bản cũ của tool/m28core/mapping.py).

Giữ lại để tool/check_drivface.py còn chạy ánh xạ cũ làm số so sánh (map cũ: tool/legacy_wflw/map_mp50_wflw.json) và để fit_map.py
cũ còn chạy. Không có chỗ nào trong pipeline m28 dùng file này. Chữ ký giữ như bản cũ.

Quy ước toạ độ: pts478 theo pixel kiểu MediaPipe (x = p.x * width, biên pixel). Ảnh lật đúng nghĩa là x' = 512 - x, nhưng ridge
học trên đáp án WFLW (quy ước tâm pixel) nên hằng số bỏ lật tốt nhất lệch khỏi 512 chút ít: fit_map.py ước lượng và ghi `flip_width`.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from m28core.mapping import from_mean, similarity, to_mean  # noqa: E402

OUT = 512


def fit_ridge(X, Y, lam):
    """X: (n, 2k) toạ độ k đỉnh gần nhất; Y: (n, 2) điểm đáp án; cùng khung trung bình."""
    if lam <= 0:
        raise ValueError("λ phải > 0")
    mx, my = X.mean(0), Y.mean(0)
    A = X - mx
    W = np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ (Y - my))
    return mx, W, my                               # dự đoán: (X_moi - mx) @ W + my


def map_points(pts478, mp_map):
    """478 điểm (toạ độ pixel bất kỳ) -> {tên: [x, y]} cho MỌI điểm của map, cùng toạ độ đầu vào."""
    pts = np.asarray(pts478, float)
    if pts.shape != (len(mp_map["mean478"]), 2):
        raise ValueError(f"cần {len(mp_map['mean478'])} điểm MediaPipe, nhận {pts.shape}")
    s, R, t = similarity(pts, np.asarray(mp_map["mean478"], float))
    out = {}
    for name in mp_map["names"]:
        m = mp_map["points"][name]
        x = to_mean(pts[m["idx"]], s, R, t).reshape(-1)
        y = (x - np.asarray(m["mx"])) @ np.asarray(m["W"]) + np.asarray(m["my"])
        out[name] = from_mean(y[None], s, R, t)[0]
    return out


def apply_map(pts478, mp_map, config, flipped=False, width=None):
    names = [p["name"] for p in config["points"]]
    absent = [n for n in names if n not in mp_map["points"]]
    if absent:
        raise ValueError(f"map_mp50.json không có điểm {absent[:3]}...: chạy lại tool/fit_map.py")
    defs = mp_map.get("defs") or {}
    for p in config["points"]:
        if p["name"] in defs and defs[p["name"]]["wflw"] != p["wflw"]:
            raise ValueError(f"điểm {p['name']} đổi chỉ số wflw so với map: chạy lại tool/fit_map.py")
    res = map_points(pts478, mp_map)
    if not flipped:
        return {n: [float(res[n][0]), float(res[n][1])] for n in names}
    w = float(mp_map.get("flip_width", OUT) if width is None else width)
    flip_of = {n: defs[n]["flip"] for n in defs} if defs else {p["name"]: p["flip"] for p in config["points"]}
    back = {flip_of[n]: [w - float(res[n][0]), float(res[n][1])] for n in mp_map["names"]}   # bỏ lật + đổi tên theo cặp
    return {n: back[n] for n in names}
