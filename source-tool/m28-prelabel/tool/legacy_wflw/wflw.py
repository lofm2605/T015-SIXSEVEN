"""LỊCH SỬ, KHÔNG DÙNG (QĐ-001: bỏ WFLW). Đọc nhãn WFLW. Dùng chung cho split.py, crop.py (P1) trong thư mục này.

Phần cắt mặt vuông (OUT, SIDE_SCALE, crop_geometry, square_crop) đã tách sang tool/m28core/cat_mat.py; ở đây chỉ nhập lại để
split.py/crop.py cũ chạy như trước.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from m28core.cat_mat import OUT, SIDE_SCALE, crop_geometry, square_crop  # noqa: E402,F401

ATTRS = ['pose', 'expression', 'illumination', 'makeup', 'occlusion', 'blur']
TRAIN_TXT = 'list_98pt_rect_attr_train.txt'
TEST_TXT = 'list_98pt_rect_attr_test.txt'


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
