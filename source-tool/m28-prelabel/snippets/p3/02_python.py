# Trích từ de-tai-m28/p3-anh-xa.md — mục: Làm thế nào › 3. eval50.py (viết lại cho đáp án 50 điểm gán tay, QĐ-001). Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
import numpy as np

def iod(gt50, cfg):                  # khoảng cách hai khoé mắt ngoài (cfg["iod_points"]), theo đáp án gán tay
    a, b = cfg["iod_points"]
    return np.linalg.norm(np.asarray(gt50[a], float) - np.asarray(gt50[b], float))

def point_errors(pred, gt50, cfg):
    """pred, gt50: dict tên -> (x, y) trên cùng hệ toạ độ ảnh. Trả dict tên -> lỗi % IOD (điểm-điểm).
    Bản đầy đủ (điểm tới đường gấp khúc cho loại C, điểm thiếu) nằm ở tool/eval50.py."""
    d, err = iod(gt50, cfg), {}
    for pt in cfg["points"]:
        n = pt["name"]
        if n in pred and n in gt50:
            err[n] = np.linalg.norm(np.asarray(pred[n], float) - np.asarray(gt50[n], float)) / d * 100
    return err                       # NME của mặt = trung bình các lỗi
