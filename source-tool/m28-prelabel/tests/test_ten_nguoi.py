"""Đặt tên người cho từng gói (nhóm trưởng, tab Thống kê): m28core/ten_nguoi.py, thong_ke.tinh dùng tên mới, file gói gốc không bị sửa."""
import hashlib
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
sys.path.insert(0, HERE)
import thong_ke as tk  # noqa: E402
import thong_ke_html as th  # noqa: E402
from dh_fake import du_an  # noqa: E402
from m28core import ten_nguoi  # noqa: E402
from tk_fake import mo_phong  # noqa: E402


@pytest.fixture
def world(tmp_path):
    """4 người (P1, P2 manual; P3, P4 assisted), gói trong outputs\\goi_nhom."""
    root = du_an(tmp_path)
    mo_phong(root)
    return root


def phien_of(root, nguoi):
    p = os.path.join(root, 'outputs', 'goi_nhom', f'ketqua_{nguoi}_1410_NAP_001.json')
    return json.load(open(p, encoding='utf-8'))['noi_dung']['phien'], p


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def test_dat_ten_doi_nguoi_trong_thong_ke_khong_sua_file_goc(world):
    ph, f = phien_of(world, 'P1')
    before = sha(f)
    st0 = tk.tinh(world)
    assert st0['nhom']['nguoi']['manual'] == ['P1', 'P2'] and st0['nguon']['doi_ten'] == []
    assert ten_nguoi.dat(world, ph, '  Cuong ', goi='ketqua_P1_1410_NAP_001.zip', goc='P1') == 'Cuong'
    st = tk.tinh(world)
    assert st['nhom']['nguoi']['manual'] == ['Cuong', 'P2'] and st['nhom']['nguoi']['assisted'] == ['P3', 'P4']
    assert [(a, b) for _t, a, b in st['nguon']['doi_ten']] == [('P1', 'Cuong')]
    assert 'Tên người do nhóm trưởng đặt' in th.noi_dung(st) and 'P1 → Cuong' in th.noi_dung(st)
    assert sha(f) == before                                                            # file gói gốc không bị sửa
    assert os.path.isfile(os.path.join(world, 'outputs', 'thong_ke', 'ten_nguoi.json'))


def test_hai_goi_cung_ten_moi_la_mot_nguoi_va_bo_ten_ve_lai_ten_goc(world):
    ph1, _ = phien_of(world, 'P1')
    ph2, _ = phien_of(world, 'P2')
    ten_nguoi.dat(world, ph1, 'Lan')
    ten_nguoi.dat(world, ph2, 'Lan')
    assert tk.tinh(world)['nhom']['nguoi']['manual'] == ['Lan']
    assert ten_nguoi.bo(world, ph1) and not ten_nguoi.bo(world, ph1)
    assert tk.tinh(world)['nhom']['nguoi']['manual'] == ['Lan', 'P1']
    ten_nguoi.bo(world, ph2)
    assert tk.tinh(world)['nhom']['nguoi']['manual'] == ['P1', 'P2']


@pytest.mark.parametrize('ten', ['', ' ', 'a b', 'x' * 33, '../P1', 'Nguyễn', None, 5])
def test_ten_sai_bi_tu_choi_va_khong_ghi_gi(world, ten):
    ph, _ = phien_of(world, 'P1')
    with pytest.raises(ten_nguoi.TenNguoiLoi):
        ten_nguoi.dat(world, ph, ten)
    assert ten_nguoi.doc(world) == {} and not os.path.exists(os.path.join(world, 'outputs', 'thong_ke', 'ten_nguoi.json'))


def test_ma_phien_sai_bi_tu_choi_va_file_hong_khong_lam_vo(world):
    for ph in ('', None, 'a b', '../x'):
        with pytest.raises(ten_nguoi.TenNguoiLoi):
            ten_nguoi.dat(world, ph, 'Cuong')
    p = os.path.join(world, 'outputs', 'thong_ke')
    os.makedirs(p, exist_ok=True)
    open(os.path.join(p, 'ten_nguoi.json'), 'w', encoding='utf-8').write('{hỏng')
    assert ten_nguoi.doc(world) == {} and tk.tinh(world)['nguon']['doi_ten'] == []
    json.dump({'ten': {'P1-x': {'ten': 'Ok'}, 'a b': {'ten': 'Sai'}, 'P2-y': {'ten': 'a b'}, 'P3-z': 'chuỗi'}}, open(os.path.join(p, 'ten_nguoi.json'), 'w', encoding='utf-8'))
    assert list(ten_nguoi.doc(world)) == ['P1-x']                                      # chỉ giữ dòng hợp lệ


def test_ap_dung_khong_sua_doi_tuong_cu():
    nd = {'phien': 'P1-1', 'nguoi': 'P1'}
    out, doi = ten_nguoi.ap_dung([('a.zip', nd)], {'P1-1': {'ten': 'Cuong', 'goi': '', 'goc': 'P1'}})
    assert nd['nguoi'] == 'P1' and out[0][1]['nguoi'] == 'Cuong' and out[0][1]['nguoi_goc'] == 'P1' and doi == [('a.zip', 'P1', 'Cuong')]
    out, doi = ten_nguoi.ap_dung([('a.zip', nd)], {'P1-1': {'ten': 'P1', 'goi': '', 'goc': 'P1'}})                    # đặt trùng tên gốc: không tính là đổi
    assert doi == [] and out[0][1] is nd


def test_dong_bi_danh_dau_vao_log_gop_theo_nhom_va_ban_xuat_van_du_bang(world):
    from tk_fake import nd_goi, viet_goi
    nd = nd_goi('P5', 'assisted', 6.2, n_nguoi_seed=4)
    nd['canh_bao'] = ['chua_co_nhom']                                                   # gói có cảnh báo: mọi dòng thời gian của nó bị đánh dấu
    viet_goi(world, nd, 'outputs/goi_nhom')
    st = tk.tinh(world)
    dau = [o for o in st['thoi_gian']['danh_dau'] if o['person'] == 'P5']
    assert len(dau) == 8                                                                # 8 mặt, mỗi mặt một dòng bị đánh dấu
    chinh, log = th.noi_dung_gon(st)
    full = th.noi_dung(st)
    assert 'Dòng bị đánh dấu' not in chinh and 'Dòng bị đánh dấu — vẫn nằm trong chỉ số chính' in full and full.count('NAP_001_0') >= 8   # trang chính ẩn, bản xuất giữ bảng từng mặt
    assert 'Dòng thời gian bị đánh dấu' in log and 'vẫn nằm trong chỉ số chính' in log
    bang_log = log[log.index('Dòng thời gian bị đánh dấu'):]
    assert 'NAP_001_0' not in bang_log                                                  # không liệt kê từng mặt
    assert bang_log.count('>P5<') == 1 and '>8<' in bang_log and 'chua_co_nhom' in bang_log          # một dòng gộp cho P5: 8 mặt
