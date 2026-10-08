"""Đồ giả dùng chung cho test đồng hồ, gói kết quả, so sánh hai nhóm và tổng kết (KHÔNG ảnh mặt, KHÔNG mạng, KHÔNG dữ liệu thật).

FakeGio: đồng hồ giả (monotonic + giờ thật) để test cộng dồn giây, tạm dừng, máy khởi động lại. dựng_du_an: thư mục tạm có config thật. nhan_xml/nhap_xml: nhãn CVAT
bảy skeleton giả (steps.image_xml thật) quanh mẫu `tmpl` của config.
"""
import datetime
import json
import os
import shutil
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
from m28core import steps  # noqa: E402

REAL_CFG = os.path.join(HERE, '..', 'config', 'm28_config.json')
VN = datetime.timezone(datetime.timedelta(hours=7))


class FakeGio:
    """mono/epoch/now giả. tick(s): thời gian trôi s giây cả monotonic lẫn giờ thật. reboot(): monotonic về gần 0 còn giờ thật vẫn trôi."""

    def __init__(self, start='2026-10-14T18:30:00+07:00'):
        self.e = datetime.datetime.fromisoformat(start).timestamp()
        self.m = 1000.0

    def mono(self):
        return self.m

    def epoch(self):
        return self.e

    def now(self):
        return datetime.datetime.fromtimestamp(self.e, VN)

    def tick(self, s):
        self.m += s
        self.e += s

    def reboot(self, gap=600.0, new_mono=5.0):
        self.e += gap
        self.m = new_mono

    def skip_wall(self, s):
        """Giờ thật nhảy s giây mà monotonic KHÔNG chạy (ví dụ máy ngủ trên Linux)."""
        self.e += s


def cfg_real():
    with open(REAL_CFG, encoding='utf-8') as f:
        return json.load(f)


def du_an(root):
    """Thư mục dự án giả có config thật, raw/, runs/, outputs/ (chưa có gì trong đó). Trả đường dẫn."""
    root = str(root)
    os.makedirs(os.path.join(root, 'config'), exist_ok=True)
    shutil.copy(REAL_CFG, os.path.join(root, 'config', 'm28_config.json'))
    for d in ('raw', 'runs'):
        os.makedirs(os.path.join(root, d), exist_ok=True)
    return root


def ten_diem():
    return [p['name'] for p in cfg_real()['points']]


def mat_mau(seed=0, sigma=0.0, shift=(0.0, 0.0)):
    """Một mặt giả: {tên điểm: (x, y)} quanh mẫu tmpl (hệ 512x512); sigma = độ nhiễu px."""
    rng = np.random.default_rng(seed)
    base = np.array([p['tmpl'] for p in cfg_real()['points']], float)
    pts = base + rng.normal(0, sigma, base.shape) + np.array(shift)
    return {n: (float(x), float(y)) for n, (x, y) in zip(ten_diem(), pts)}


def viet_xml(path, mats, w=512, h=512, thieu=None):
    """Ghi file 'CVAT for images 1.1' giả. mats: {tên ảnh có đuôi: {điểm: (x, y)}}; thieu: {tên ảnh: [tên điểm bỏ]}."""
    names = ten_diem()
    parts = ['<?xml version="1.0" encoding="utf-8"?>', '<annotations>', '  <version>1.1</version>']
    for i, (anh, pts) in enumerate(mats.items()):
        bo = set((thieu or {}).get(anh, ()))
        pn = [n for n in names if n in pts and n not in bo]
        parts.append(steps.image_xml(i, anh, pn, [pts[n] for n in pn], [False] * len(pn), w, h))
    parts.append('</annotations>')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(parts))
    return path


def viet_nhan(root, task, nguoi, day, mats, **kw):
    return viet_xml(os.path.join(root, 'raw', f'{task}_{nguoi}_{day}.xml'), mats, **kw)


def viet_nhap(root, dot, mats):
    return viet_xml(os.path.join(root, 'runs', dot, 'xml', 'prelabel.xml'), mats)
