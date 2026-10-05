# Trích từ de-tai-m28/p3-anh-xa.md — mục: Làm thế nào › 3. eval50.py. Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
import numpy as np

def iod(gt98):                       # khoảng cách hai khoé mắt ngoài, theo đáp án
    return np.linalg.norm(gt98[60] - gt98[72])

def point_to_curve(p, curve):        # curve: (m, 2) điểm WFLW dày của đường đó
    a, ab = curve[:-1], curve[1:] - curve[:-1]
    u = ((p - a) * ab).sum(1) / np.maximum((ab ** 2).sum(1), 1e-9)
    proj = a + np.clip(u, 0, 1)[:, None] * ab
    return np.linalg.norm(proj - p, axis=1).min()

def point_errors(pred, gt50, gt98, cfg):
    """pred, gt50: dict tên -> (x, y) trên ảnh cắt 512. Trả dict tên -> lỗi % IOD."""
    d, err = iod(gt98), {}
    for pt in cfg["points"]:
        n, p = pt["name"], np.asarray(pred[pt["name"]], float)
        if pt["type"] == "E":
            err[n] = np.linalg.norm(p - np.asarray(gt50[n])) / d * 100
        elif pt["type"] == "C":
            err[n] = point_to_curve(p, gt98[pt["curve"]]) / d * 100
    return err                       # NME của mặt = trung bình; loại N bỏ qua
