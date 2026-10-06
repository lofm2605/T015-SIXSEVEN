"""Đổi 478 điểm MediaPipe sang 50 điểm của config bằng CHỌN ĐỈNH trực tiếp (không học phép khớp nào). Chỉ dùng numpy.

    apply_map(pts478, map, config, flipped=False, width=None) -> {tên điểm: [x, y]} theo toạ độ ảnh cắt 512, đúng thứ tự config
    flipped=True: pts478 là kết quả MediaPipe trên ảnh lật ngang; điểm n (đã bỏ lật) = [w - x, y] của đỉnh mp_idx(flip(n)) trên ảnh lật,
                  với w = width nếu có, không thì map["flip_width"]. Kết quả nằm trên ảnh gốc, cùng tên điểm như bản không lật.

Vì sao chọn đỉnh (QĐ-001, QĐ-002 dự thảo): bỏ WFLW thì không còn đáp án 50 điểm để học phép khớp ridge như trước (ridge học trên WFLW lệch ở
hàm và lông mày khi gặp mặt tài xế). Mỗi điểm của config là MỘT đỉnh MediaPipe (config `mp_idx`), nên điểm nháp nằm đúng trên lưới mặt
của model, không có số học nào cần nhóm kiểm lại, và đổi định nghĩa một điểm chỉ là đổi một chỉ số.

Định dạng config/map_mp50.json (version 2, kind "vertex"), do tool/make_config.py sinh cùng m28_config.json:
    {"version": 2, "kind": "vertex", "names": [tên điểm theo thứ tự config],
     "points": {tên: {"mp_idx": đỉnh 0-477, "flip": tên điểm đối xứng}}, "flip_width": w, "meta": {...}}
Không có mean478, ridge hay ma trận nào. Map kiểu cũ (ridge, có `mean478`/`W`) bị từ chối bằng ValueError rõ ràng.
Config có thể là TẬP CON các điểm của map; `mp_idx` hoặc `flip` của một điểm trong config lệch với map thì báo lỗi (chạy lại make_config.py).

Quy ước toạ độ: pts478 theo pixel kiểu MediaPipe (x = p.x * width, biên pixel). Ảnh lật đúng nghĩa là x' = width - x; `flip_width` là
số ước lượng trên dữ liệu thật (make_config.py, mặt thẳng của tập F, không cần đáp án) và có thể lệch khỏi 512 chút ít.
Ánh xạ cũ (ridge) nằm ở tool/legacy_wflw/mapping_ridge.py, chỉ để so sánh (tool/check_drivface.py).
"""
import numpy as np

OUT = 512
N_VERT = 478


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


def _check_map(mp_map):
    if not isinstance(mp_map, dict):
        raise ValueError("map_mp50.json không phải đối tượng JSON")
    if "mean478" in mp_map or any(isinstance(v, dict) and "W" in v for v in (mp_map.get("points") or {}).values()) \
            or mp_map.get("version") != 2 or mp_map.get("kind") != "vertex":
        raise ValueError("map_mp50.json là bản cũ (ánh xạ ridge học trên WFLW, đã lỗi thời theo QĐ-001): "
                         "chạy lại tool\\make_config.py để sinh map version 2 (chọn đỉnh)")
    if not isinstance(mp_map.get("points"), dict) or not isinstance(mp_map.get("names"), list):
        raise ValueError("map_mp50.json thiếu 'names' hoặc 'points': chạy lại tool\\make_config.py")


def vertex_table(mp_map, config):
    """[(tên, mp_idx, tên đối xứng)] cho các điểm của config, đã kiểm khớp với map. ValueError nếu lệch."""
    _check_map(mp_map)
    out = []
    for p in config["points"]:
        n = p["name"]
        m = mp_map["points"].get(n)
        if m is None:
            raise ValueError(f"map_mp50.json không có điểm {n}: chạy lại tool\\make_config.py")
        if "mp_idx" not in p:
            raise ValueError(f"điểm {n} trong config không có 'mp_idx' (config kiểu cũ?): chạy lại tool\\make_config.py")
        if int(m["mp_idx"]) != int(p["mp_idx"]):
            raise ValueError(f"điểm {n}: mp_idx của config ({p['mp_idx']}) lệch với map ({m['mp_idx']}): chạy lại tool\\make_config.py")
        if m["flip"] != p["flip"]:
            raise ValueError(f"điểm {n}: cặp flip của config ({p['flip']}) lệch với map ({m['flip']}): chạy lại tool\\make_config.py")
        if p["flip"] not in mp_map["points"]:
            raise ValueError(f"điểm {n}: cặp flip {p['flip']} không có trong map: chạy lại tool\\make_config.py")
        out.append((n, int(m["mp_idx"]), p["flip"]))
    return out


def apply_map(pts478, mp_map, config, flipped=False, width=None):
    pts = np.asarray(pts478, float)
    if pts.shape != (N_VERT, 2):
        raise ValueError(f"cần {N_VERT} điểm MediaPipe dạng (478, 2), nhận {pts.shape}")
    if not np.isfinite(pts).all():
        raise ValueError("điểm MediaPipe có NaN/inf")
    table = vertex_table(mp_map, config)
    if not flipped:
        return {n: [float(pts[i][0]), float(pts[i][1])] for n, i, _ in table}
    w = float(mp_map.get("flip_width", OUT) if width is None else width)
    idx = {n: int(mp_map["points"][n]["mp_idx"]) for n in mp_map["points"]}
    # điểm n của ảnh gốc = đỉnh của điểm đối xứng trên ảnh lật, đổi x -> w - x
    out = {}
    for n, _, fl in table:
        j = idx[fl]
        out[n] = [w - float(pts[j][0]), float(pts[j][1])]
    return out
