# Trích từ de-tai-m28/p1-du-lieu.md — mục: Làm thế nào › 1. Tải và cắt (5–6/10). Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
import cv2, numpy as np
ATTRS = ['pose', 'expression', 'illumination', 'makeup', 'occlusion', 'blur']
def read_wflw(txt_path):
    rows = []
    with open(txt_path) as f:
        for i, line in enumerate(f):
            a = line.split()
            assert len(a) == 207, len(a)
            rows.append({'line': i, 'image': a[206],
                         'pts': np.array(a[:196], np.float32).reshape(98, 2),
                         'bbox': np.array(a[196:200], np.float32),
                         **{k: int(v) for k, v in zip(ATTRS, a[200:206])}})
    return rows

def square_crop(img, bbox, pts, side_scale=1.4, out=512):
    x0, y0, x1, y1 = bbox
    side = side_scale * max(x1 - x0, y1 - y0)       # cạnh dài x 1,4, cùng tâm
    left, top = (x0 + x1 - side) / 2, (y0 + y1 - side) / 2
    k = out / side
    M = np.float32([[k, 0, -left * k], [0, k, -top * k]])
    crop = cv2.warpAffine(img, M, (out, out), borderValue=(128, 128, 128))
    gt = (pts - [left, top]) * k                     # gt98 theo toạ độ ảnh cắt
    inside = bool(((gt >= 0) & (gt <= out - 1)).all())
    return crop, gt, (left, top, k), inside
