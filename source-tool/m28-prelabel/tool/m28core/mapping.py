"""Đổi 478 điểm MediaPipe sang bộ điểm trong config (BẢN NHÁP cho P3). Chỉ dùng numpy.

    apply_map(pts478, map, config, flipped=False) -> {tên điểm: [x, y]} theo toạ độ ảnh cắt 512, đúng thứ tự config
    flipped=True: pts478 là kết quả MediaPipe trên ảnh lật ngang; hàm đổi sang 50 điểm, lấy x = width - x
                  rồi gán tên theo cột `flip` của config, nên kết quả đã nằm trên ảnh gốc (đã "bỏ lật").

`map` là nội dung config/map_mp50.json do tool/fit_map.py sinh ra.
"""
import numpy as np

OUT = 512


def similarity(src, dst):
    """Procrustes: tìm s, R, t để s * src @ R.T + t gần dst nhất (không lật gương)."""
    ms, md = src.mean(0), dst.mean(0)
    a, b = src - ms, dst - md
    U, S, Vt = np.linalg.svd(b.T @ a)
    k = np.sign(np.linalg.det(U @ Vt))
    R = U @ np.diag([1.0, k]) @ Vt
    s = (S[0] + k * S[1]) / (a ** 2).sum()
    return s, R, md - s * R @ ms


def to_mean(p, s, R, t):                           # ảnh cắt -> khung hình trung bình
    return s * p @ R.T + t


def from_mean(q, s, R, t):                         # khung hình trung bình -> ảnh cắt
    return (q - t) @ R / s


def fit_ridge(X, Y, lam):
    """X: (n, 2k) toạ độ k đỉnh gần nhất; Y: (n, 2) điểm đáp án; cùng khung trung bình."""
    mx, my = X.mean(0), Y.mean(0)
    A = X - mx
    W = np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ (Y - my))
    return mx, W, my                               # dự đoán: (X_moi - mx) @ W + my


def map_points(pts478, mp_map):
    """478 điểm (ảnh bất kỳ, toạ độ pixel) -> {tên: [x, y]} theo đúng toạ độ đầu vào, đúng thứ tự mp_map['names']."""
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


def apply_map(pts478, mp_map, config, flipped=False, width=OUT):
    names = [p["name"] for p in config["points"]]
    if names != mp_map["names"]:
        raise ValueError("config và map_mp50.json không cùng danh sách/thứ tự điểm: chạy lại tool/fit_map.py")
    res = map_points(pts478, mp_map)
    if not flipped:
        return {n: [float(res[n][0]), float(res[n][1])] for n in names}
    flip = {p["name"]: p["flip"] for p in config["points"]}
    back = {flip[n]: [float(width - res[n][0]), float(res[n][1])] for n in names}   # x' = width - x, đổi tên theo cặp đối xứng
    return {n: back[n] for n in names}
