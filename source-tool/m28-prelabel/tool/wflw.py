"""Đọc nhãn WFLW và cắt mặt vuông. Dùng chung cho split.py, crop.py (P1)."""
import numpy as np

ATTRS = ['pose', 'expression', 'illumination', 'makeup', 'occlusion', 'blur']
TRAIN_TXT = 'list_98pt_rect_attr_train.txt'
TEST_TXT = 'list_98pt_rect_attr_test.txt'
OUT = 512
SIDE_SCALE = 1.4


def read_wflw(txt_path):
    """Mỗi dòng: 196 toạ độ, 4 số hộp, 6 cờ, đường dẫn ảnh (207 trường)."""
    rows = []
    with open(txt_path, encoding='utf-8') as f:
        for i, line in enumerate(f):
            a = line.split()
            assert len(a) == 207, f'{txt_path} dòng {i}: {len(a)} trường, cần 207'
            rows.append({'line': i, 'image': a[206],
                         'pts': np.array(a[:196], np.float32).reshape(98, 2),
                         'bbox': np.array(a[196:200], np.float32),
                         **{k: int(v) for k, v in zip(ATTRS, a[200:206])}})
    return rows


def crop_geometry(bbox, pts, side_scale=SIDE_SCALE, out=OUT):
    """Cạnh dài x 1,4, cùng tâm. Trả (left, top, k, inside, gt). Không cần ảnh."""
    x0, y0, x1, y1 = [float(v) for v in bbox]
    side = side_scale * max(x1 - x0, y1 - y0)
    left, top = (x0 + x1 - side) / 2, (y0 + y1 - side) / 2
    k = out / side
    gt = (pts - np.float32([left, top])) * k
    inside = bool(((gt >= 0) & (gt <= out - 1)).all())
    return left, top, k, inside, gt


def square_crop(img, bbox, pts, side_scale=SIDE_SCALE, out=OUT):
    import cv2
    left, top, k, inside, gt = crop_geometry(bbox, pts, side_scale, out)
    M = np.float32([[k, 0, -left * k], [0, k, -top * k]])
    crop = cv2.warpAffine(img, M, (out, out), borderValue=(128, 128, 128))
    return crop, gt, (left, top, k), inside
