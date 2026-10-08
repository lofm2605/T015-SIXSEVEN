"""Thế giới giả cho test Thống kê và tổng kết hai nhóm (QĐ-006): gói kết quả của 4-5 người, nhãn raw\\, dòng bấm giờ. Dữ liệu giả, không ảnh thật, không mạng."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
sys.path.insert(0, HERE)
from dh_fake import cfg_real, du_an, mat_mau, ten_diem  # noqa: E402,F401
from m28core import goi_kq  # noqa: E402

ANH = [f'F_{i:03d}' for i in range(1, 9)]


def r2(pts):
    return {k: [round(x, 2), round(y, 2)] for k, (x, y) in pts.items()}


def nhieu(base, sigma, seed):
    rng = np.random.default_rng(seed)
    return {k: (x + float(rng.normal(0, sigma)), y + float(rng.normal(0, sigma))) for k, (x, y) in base.items()}


def nd_goi(nguoi, nhom, base_giay, n_nguoi_seed=0, anh=ANH, dot='NAP_001', bo_anh='NAP_001', sua_k=3, uoc=True, so_mat=None, phien=None, bat_dau='2026-10-14T18:30:00+07:00'):
    """Nội dung gói của một người: nhóm manual có nhãn (nhiễu nhỏ quanh mẫu), nhóm assisted có nháp (nhiễu lớn hơn) và nhãn cuối (nháp, sửa `sua_k` điểm mỗi mặt)."""
    so_mat = so_mat or len(anh)
    ket_qua = []
    for i, a in enumerate(anh):
        base = mat_mau(i + 1, 0.0)
        if nhom == 'manual':
            ket_qua.append(dict(anh=a, nhan_cuoi=r2(nhieu(base, 0.4, 100 * n_nguoi_seed + i))))
        else:
            nhap = nhieu(base, 2.0, 7 + i)
            fin = dict(nhap)
            for k in list(fin)[:sua_k]:
                x, y = fin[k]
                fin[k] = (x + 9.0, y + 3.0)
            ket_qua.append(dict(anh=a, nhan_cuoi=r2(fin), nhap=r2(nhap), diem_da_sua=[], nme_nhap_so_nhan_cuoi=None))       # điểm không sửa giữ NGUYÊN toạ độ nháp, như CVAT
    giay_phien = round(base_giay * so_mat, 1)
    mat_do = []
    if not uoc:
        rng = np.random.default_rng(300 + n_nguoi_seed)
        for i in range(so_mat):
            g = round(float(base_giay * (0.9 + 0.2 * rng.random())), 1)
            mat_do.append(dict(seq=i + 1, face_id=f'{dot}_{i + 1:02d}', giay=g, so_lan_tam_dung=0, ghi_chu='', warmup=int(i < 2)))
        giay_phien = round(sum(m['giay'] for m in mat_do), 1)
    return dict(phien=phien or f'{nguoi}-20261014-183000-aa{n_nguoi_seed:02d}', nguoi=nguoi, nhom=nhom, dot=dot, bo_anh=bo_anh, task=f'demo-{dot}', job='', so_mat=so_mat,
                giay_phien=giay_phien, giay_tam_dung=0.0, so_lan_tam_dung=0, bat_dau=bat_dau, ket_thuc='2026-10-14T19:10:00+07:00', uoc_luong_chia_deu=bool(uoc), mat_do=mat_do,
                canh_bao=[], ghi_chu='', sua_tay=0, tao_luc='2026-10-14T19:10:00+07:00', nhan_file='demo.xml', co_nhan=True, co_nhap=nhom == 'assisted',
                cau_hinh=dict(so_diem=50, nguong_sua=2.0), ket_qua=ket_qua)


def viet_goi(root, nd, thu_muc='outputs/ket_qua', ddmm='1410'):
    """Ghi gói vào thu_muc của dự án (zip + json). Trả dict(ten, zip, json)."""
    r = goi_kq.ghi_goi(root, nd, ddmm=ddmm)
    if thu_muc != 'outputs/ket_qua':
        d = os.path.join(root, thu_muc)
        os.makedirs(d, exist_ok=True)
        for ext in ('zip', 'json'):
            os.replace(os.path.join(root, r[ext]), os.path.join(d, os.path.basename(r[ext])))
    return r


def mo_phong(root, speed=0.7, tmp_thu_muc='outputs/goi_nhom', uoc=True):
    """4 người: P1, P2 manual (giây/mặt ~40, 55), P3, P4 assisted (~ speed x), cùng 8 ảnh. Gói ghi vào outputs/goi_nhom."""
    spec = [('P1', 'manual', 40.0), ('P2', 'manual', 55.0), ('P3', 'assisted', 40.0 * speed), ('P4', 'assisted', 55.0 * speed)]
    out = []
    for i, (p, g, b) in enumerate(spec):
        out.append(viet_goi(root, nd_goi(p, g, b, n_nguoi_seed=i, uoc=uoc), tmp_thu_muc))
    return out
