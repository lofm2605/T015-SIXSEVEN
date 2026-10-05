"""Đổi 478 điểm MediaPipe sang bộ điểm trong config (BẢN NHÁP cho P3). Chỉ dùng numpy.

    apply_map(pts478, map, config, flipped=False) -> {tên điểm: [x, y]} theo toạ độ ảnh cắt 512, đúng thứ tự config
    flipped=True: pts478 là kết quả MediaPipe trên ảnh lật ngang; hàm đổi sang 50 điểm, lấy x = flip_width - x
                  rồi gán tên theo cặp đối xứng (cột `flip`), nên kết quả đã nằm trên ảnh gốc (đã "bỏ lật").

`map` là nội dung config/map_mp50.json do tool/fit_map.py sinh ra. Config có thể là TẬP CON các điểm của map
(bỏ bớt điểm thì không cần khớp lại); đổi chỉ số wflw của một điểm giữ nguyên tên thì apply_map báo lỗi.

Quy ước toạ độ: pts478 theo pixel kiểu MediaPipe (x = p.x * width, biên pixel). Ảnh lật đúng nghĩa là x' = 512 - x, nhưng
ridge học trên đáp án WFLW (quy ước tâm pixel) nên hằng số bỏ lật tốt nhất lệch khỏi 512 chút ít: fit_map.py ước lượng và
ghi `flip_width` (thường ~511,3) vào map; apply_map dùng số đó khi không truyền `width`.
"""
import numpy as np

OUT = 512


def similarity(src, dst):
    """Procrustes: tìm s, R, t để s * src @ R.T + t gần dst nhất (không lật gương)."""
    src, dst = np.asarray(src, float), np.asarray(dst, float)
    if not (np.isfinite(src).all() and np.isfinite(dst).all()):
        raise ValueError("điểm có NaN/inf")
    ms, md = src.mean(0), dst.mean(0)
    a, b = src - ms, dst - md
    if (a ** 2).sum() < 1e-12:
        raise ValueError("các điểm trùng nhau, không khớp được")
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
