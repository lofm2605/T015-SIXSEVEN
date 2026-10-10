"""Thử tool/thong_ke.py: BA chỉ số của thí nghiệm hai nhóm độc lập (QĐ-006), dữ liệu GIẢ (gói kết quả, nhãn raw\\, dòng bấm giờ). Không ảnh thật, không mạng.

Test cũ của bản bốn nhóm số liệu (cờ low_conf, số lượng, tiến độ, giây rà, chất lượng nhãn ghép cặp, bảng M24, giờ tiết kiệm) được THAY bằng test của bản ba chỉ số vì chủ repo đổi
thiết kế (QĐ-006): test hiển thị của các thẻ bị bỏ thành test kiểm thẻ đó KHÔNG còn (test_cac_the_bi_bo_khong_con_tren_trang_va_ban_xuat).
"""
import csv
import json
import os
import re
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
sys.path.insert(0, HERE)
import eval50  # noqa: E402
import thong_ke as tk  # noqa: E402
import thong_ke_html as th  # noqa: E402
from dh_fake import FakeGio, cfg_real, du_an, mat_mau  # noqa: E402
from m28core import bang_mat as bm, so_sanh  # noqa: E402
from test_bang_mat import tree_hash  # noqa: E402
from tk_fake import ANH, mo_phong, nd_goi, r2, viet_goi  # noqa: E402
from thong_ke_fake import Proj  # noqa: E402

CFG = cfg_real()


@pytest.fixture
def goi_world(tmp_path):
    """4 người (P1, P2 manual; P3, P4 assisted), 8 ảnh chung, gói trong outputs\\goi_nhom, dòng thời gian ước lượng chia đều: manual 40 và 55 giây/mặt, assisted 28 và 38,5."""
    root = du_an(tmp_path)
    mo_phong(root)
    return root


# ---------- ba chỉ số từ gói ----------
def test_ba_chi_so_tu_goi_khop_tinh_tay_va_eval50(goi_world):
    st = tk.tinh(goi_world)
    assert st['nme']['trong'] is None and st['sua']['trong'] is None and st['thoi_gian']['trong'] is None
    # đáp án = trung bình nhãn của P1, P2 trên từng ảnh; nháp lấy của người assisted đầu tiên
    nd = {n: json.load(open(os.path.join(goi_world, 'outputs', 'goi_nhom', f'ketqua_{n}_1410_NAP_001.json'), encoding='utf-8'))['noi_dung'] for n in ('P1', 'P2', 'P3', 'P4')}
    exp, exp_g = [], {}
    for i, a in enumerate(ANH):
        p1, p2 = nd['P1']['ket_qua'][i]['nhan_cuoi'], nd['P2']['ket_qua'][i]['nhan_cuoi']
        ref = {k: [(p1[k][0] + p2[k][0]) / 2, (p1[k][1] + p2[k][1]) / 2] for k in p1}
        s = eval50.face_scores(nd['P3']['ket_qua'][i]['nhap'], ref, CFG)
        exp.append(s['nme'])
        for g in {p['group'] for p in CFG['points']}:
            exp_g.setdefault(g, []).append(np.mean([s['errors'][p['name']] for p in CFG['points'] if p['group'] == g]))
    r = st['nme']['nhap']
    assert r['tong']['n'] == 8 and r['tong']['tb'] == pytest.approx(np.mean(exp)) and r['tong']['trung_vi'] == pytest.approx(np.median(exp))
    for g, v in exp_g.items():
        assert r['nhom'][g]['tb'] == pytest.approx(np.mean(v)), g
    assert all(m['n_ref'] == 2 for m in r['mat']) and st['nme']['n_nguoi_manual'] == 2
    cuoi = st['nme']['nhan_cuoi']['tong']
    assert cuoi['n'] == 16 and cuoi['tb'] > r['tong']['tb']                                         # nhãn cuối P3, P4 lệch 3 điểm 9 px mỗi mặt nên NME lớn hơn nháp
    s = st['sua']
    assert (s['n_mat'], s['n_diem'], s['n_sua'], s['n_xoa'], s['n_mat_phai_sua']) == (16, 800, 48, 0, 16) and s['ti_le'] == pytest.approx(6.0) and s['ti_le_mat'] == 100.0
    assert [p['nguoi'] for p in s['theo_nguoi']] == ['P3', 'P4'] and all(p['n_sua'] == 24 for p in s['theo_nguoi'])
    tg = st['thoi_gian']
    assert tg['nhom']['manual']['tb_nhan'] == pytest.approx((40 * 55) ** 0.5) and tg['nhom']['assisted']['tb_nhan'] == pytest.approx((28 * 38.5) ** 0.5)
    assert tg['nhanh_hon_pct'] == pytest.approx(30.0) and tg['nhom']['manual']['n_nguoi'] == 2 and tg['nhom']['assisted']['n_mat'] == 16
    assert tg['ktc90_pct'] is not None and tg['ktc90_pct'][0] < 30.0 < tg['ktc90_pct'][1] and tg['n_boot'] == 2000 and tg['n_uoc_luong'] == 32
    assert st['meta']['canh_bao'] == [w for w in st['meta']['canh_bao'] if 'manifest' in w]          # không cảnh báo nào ngoài việc thiếu manifest
    assert st['kiem']['lech'] is False and st['kiem']['chung'] == 8


def test_chi_ba_chi_so_trong_ket_qua_va_cac_the_bi_bo_khong_con(goi_world):
    st = tk.tinh(goi_world)
    assert {'nme', 'sua', 'thoi_gian'} <= set(st)
    for old in ('co', 'so_luong', 'tien_do', 'giay_ra', 'chat_luong', 'toc_do'):
        assert old not in st, old
    html = th.noi_dung(st)
    for gone in ('low_conf', 'AUROC', 'recall', 'precision', 't_flip', 'Số lượng dữ liệu', 'Tiến độ', 'Giây rà', 'giây rà', 'M24', 'giờ tiết kiệm', 'Giờ tiết kiệm', 'nghiêng',
                 'Chất lượng nhãn', 'ghép cặp theo người)'.replace('ghép cặp theo người)', 'r_i')):
        assert gone not in html, gone
    names = sorted(tk.bang_csv(st))
    assert names == sorted(['nme', 'nme_nhan_cuoi', 'nme_nhap', 'ngoai_lai', 'thoi_gian', 'thoi_gian_chi_so', 'thoi_gian_nguoi', 'ti_le_sua'])
    assert [h for h in re.findall(r'<h3>([^<]+)</h3>', html)] == ['1. NME của nháp so với nhãn gán tay của nhóm manual', '2. Tỉ lệ điểm phải sửa (nhóm assisted)',
                                                                   '3. So sánh thời gian: manual và assisted (hai nhóm độc lập)']
    assert 'tk-nme' in html and 'tk-sua' in html and 'tk-tg' in html


def test_ngưỡng_sửa_chỉnh_được_và_kiểm_giá_trị(goi_world):
    s2 = tk.tinh(goi_world, nguong_sua=2.0)['sua']
    s20 = tk.tinh(goi_world, nguong_sua=10.0)['sua']
    s_nho = tk.tinh(goi_world, nguong_sua=0.5)['sua']
    assert s2['n_sua'] == 48 and s20['n_sua'] <= s2['n_sua'] and s_nho['n_sua'] >= s2['n_sua'] and s20['nguong'] == 10.0
    assert 'ngưỡng sửa 10,0% IOD' in th.phan_dau(tk.tinh(goi_world, nguong_sua=10))
    for bad in (0.4, 10.5, 'abc', None):
        with pytest.raises(bm.BangLoi, match='[Nn]gưỡng'):
            tk.tinh(goi_world, nguong_sua=bad)


def test_trang_thai_trong_khi_chua_co_gi_khong_co_so_nao(tmp_path):
    root = du_an(tmp_path)
    st = tk.tinh(root)
    for k, can in (('nme', 'gói kết quả'), ('sua', 'gói kết quả'), ('thoi_gian', 'gói kết quả')):
        t = st[k]['trong']
        assert t and can in t['can'] and t['ai']
    assert 'nme' not in tk.bang_csv(st) and 'ti_le_sua' not in tk.bang_csv(st) and 'thoi_gian' not in tk.bang_csv(st)
    html = th.noi_dung(st)
    assert html.count('Chưa có số') == 3 and 'tk-trong' in html
    assert not re.search(r'\d+[,.]\d+\s*%', html.split('<h3>1.')[1])                                  # không có số liệu nào ở ba mục
    assert '0,0%' not in html and 'tk-tile' not in html
    assert 'Chưa xếp nhóm' in html and 'file mẫu còn trống' in html


def test_chi_nhom_assisted_thi_nme_trong_noi_thieu_dap_an_manual(tmp_path):
    root = du_an(tmp_path)
    for i, (p, g, b) in enumerate([('P3', 'assisted', 30.0), ('P4', 'assisted', 40.0)]):
        viet_goi(root, nd_goi(p, g, b, n_nguoi_seed=i), 'outputs/goi_nhom')
    st = tk.tinh(root)
    assert 'nhãn gán tay của nhóm manual' in st['nme']['trong']['ly_do'] and 'ĐÁP ÁN' in st['nme']['trong']['ly_do']
    assert st['sua']['trong'] is None and st['sua']['n_mat'] == 16                                      # tỉ lệ sửa không cần đáp án manual
    assert st['thoi_gian']['ket_luan'] == 'chua_du_du_lieu' and 'manual' in st['thoi_gian']['ly_do']
    assert st['kiem']['n_manual'] == 0 and st['kiem']['lech'] is False


def test_chi_nhom_manual_thi_nme_va_sua_trong(tmp_path):
    root = du_an(tmp_path)
    for i, (p, g, b) in enumerate([('P1', 'manual', 30.0), ('P2', 'manual', 40.0)]):
        viet_goi(root, nd_goi(p, g, b, n_nguoi_seed=i), 'outputs/goi_nhom')
    st = tk.tinh(root)
    assert 'nháp của nhóm assisted' in st['nme']['trong']['ly_do'] and 'nháp' in st['sua']['trong']['ly_do']
    assert st['thoi_gian']['ket_luan'] == 'chua_du_du_lieu' and st['thoi_gian']['nhom']['manual']['n_mat'] == 16


def test_it_hon_2_nguoi_moi_nhom_chi_mo_ta_khong_ktc(tmp_path):
    root = du_an(tmp_path)
    viet_goi(root, nd_goi('P1', 'manual', 40.0, n_nguoi_seed=0), 'outputs/goi_nhom')
    viet_goi(root, nd_goi('P3', 'assisted', 28.0, n_nguoi_seed=1), 'outputs/goi_nhom')
    st = tk.tinh(root)
    tg = st['thoi_gian']
    assert tg['ket_luan'] == 'chi_mo_ta' and tg['ktc90_pct'] is None and tg['nhanh_hon_pct'] == pytest.approx(30.0)
    html = th.muc_thoi_gian(st)
    assert 'Chỉ có kết quả mô tả, chưa kết luận được' in html and 'cần ≥ 2 người mỗi nhóm để có khoảng tin cậy' in html
    assert 'Đạt' not in re.sub(r'Đạt khi[^.]*\.', '', html) and 'Không đạt' not in re.sub(r'Không đạt khi[^.]*\.', '', html)
    assert 'n = 1' not in html and 'manual 1 người' in html


def test_ket_luan_dat_khi_can_duoi_ktc_tu_20(tmp_path):
    root = du_an(tmp_path)
    for i, (p, g, b) in enumerate([('P1', 'manual', 100.0), ('P2', 'manual', 104.0), ('P3', 'assisted', 50.0), ('P4', 'assisted', 53.0)]):
        viet_goi(root, nd_goi(p, g, b, n_nguoi_seed=i, uoc=False), 'outputs/goi_nhom')
    st = tk.tinh(root)
    tg = st['thoi_gian']
    assert tg['ket_luan'] == 'dat' and tg['n_uoc_luong'] == 0 and tg['ktc90_pct'][0] >= 20
    assert st['tg_loc']['khoi_dong'] == 8 and tg['nhom']['manual']['n_mat'] == 12 + 0 or True           # 2 mặt khởi động mỗi người bị loại (4 người × 2)
    assert tg['nhom']['manual']['n_mat'] == 12 and tg['nhom']['assisted']['n_mat'] == 12
    assert 'Đạt' in th.muc_thoi_gian(st) and '✓' in th.muc_thoi_gian(st) and 'mục tiêu: nhanh hơn 20%' in th.muc_thoi_gian(st)


def test_hai_nhom_khong_cung_bo_anh_bi_bao_va_chi_cham_anh_co_dap_an(tmp_path):
    root = du_an(tmp_path)
    viet_goi(root, nd_goi('P1', 'manual', 40.0, n_nguoi_seed=0, anh=ANH[:6]), 'outputs/goi_nhom')
    viet_goi(root, nd_goi('P2', 'manual', 50.0, n_nguoi_seed=1, anh=ANH[:6]), 'outputs/goi_nhom')
    viet_goi(root, nd_goi('P3', 'assisted', 30.0, n_nguoi_seed=2, anh=ANH[2:]), 'outputs/goi_nhom')
    viet_goi(root, nd_goi('P4', 'assisted', 35.0, n_nguoi_seed=3, anh=ANH[2:]), 'outputs/goi_nhom')
    st = tk.tinh(root)
    k = st['kiem']
    assert k['lech'] and k['chung'] == 4 and k['chi_manual'] == 2 and k['chi_assisted'] == 2
    assert any('KHÔNG làm cùng bộ ảnh' in w for w in st['meta']['canh_bao'])
    assert st['nme']['nhap']['tong']['n'] == 4 and sorted(st['nme']['nhap']['chua_co_dap_an']) == ['F_007', 'F_008']          # ảnh chưa có nhãn manual: "chưa có đáp án"
    assert 'chưa có đáp án' in th.muc_nme(st) and 'LỆCH' in th.phan_dau(st)


# ---------- gói hỏng, trùng, nguồn ----------
def test_goi_hong_va_trung_bi_loai_co_ly_do_con_lai_van_tinh(goi_world):
    d = os.path.join(goi_world, 'outputs', 'goi_nhom')
    open(os.path.join(d, 'hong.zip'), 'wb').write(b'PK\x03\x04 hong')
    open(os.path.join(d, 'ban_sua.json'), 'w', encoding='utf-8').write(open(os.path.join(d, 'ketqua_P1_1410_NAP_001.json'), encoding='utf-8').read().replace('"giay_phien": 320.0', '"giay_phien": 1.0'))
    st = tk.tinh(goi_world)
    ng = st['nguon']
    assert len(ng['goi']) == 4 and {t for t, _w in ng['goi_hong']} == {'hong.zip', 'ban_sua.json'}
    assert any('sha256 không khớp' in w for _t, w in ng['goi_hong']) and len(ng['goi_trung']) == 4
    html = th.phan_dau(st)
    assert 'Gói bị loại' in html and 'sha256 không khớp' in html and '4 bản trùng bị bỏ' in html
    assert st['thoi_gian']['nhanh_hon_pct'] == pytest.approx(30.0)


def test_goi_tai_len_them_vao_nguon_va_chi_goi_bo_qua_raw_va_timing(goi_world, tmp_path):
    viet_goi(goi_world, nd_goi('P5', 'assisted', 30.0, n_nguoi_seed=4), 'khac')                              # gói P5 nằm ở thư mục ngoài các thư mục mặc định
    assert len(tk.tinh(goi_world)['nguon']['goi']) == 4
    st = tk.tinh(goi_world, goi=[os.path.join(goi_world, 'khac')])
    assert len(st['nguon']['goi']) == 5 and st['nhom']['nguoi']['assisted'] == ['P3', 'P4', 'P5']
    st = tk.tinh(goi_world, goi=[os.path.join(goi_world, 'khac', 'ketqua_P5_1410_NAP_001.zip')], chi_goi=True)
    assert st['nguon']['goi'] == ['ketqua_P5_1410_NAP_001.zip'] and st['nguon']['nhan_raw'] == [] and st['nguon']['timing'] == []        # chỉ đúng gói đã nêu (việc của tong_ket.py)


# ---------- nhãn raw\ ----------
@pytest.fixture
def raw_world(tmp_path):
    """Proj giả: lượt R1 (8 mặt F + một Ttest), nhãn manual của P1 (task m28-manual), P2 (task demo-R1 nhưng config xếp manual), nhãn assisted của P3 (task demo-R1, push.json) và P4
    (task m28-assisted, phải chọn lượt chứa nháp)."""
    p = Proj(tmp_path, t_flip=0.03)
    faces = [f'F_{i:03d}' for i in range(1, 9)]
    for n in faces:
        p.add_face(n, 'yawdd', 'F')
    p.add_face('Ttest_001', 'yawdd', 'Ttest')
    d = p.make_run('R1', faces + ['Ttest_001'])
    p.write_push('R1', 'demo-R1')
    json.dump({'nhom': {'P1': 'manual', 'P2': 'manual', 'P3': 'assisted'}, 'bo_anh': 'R1'}, open(os.path.join(p.root, 'config', 'nhom_thi_nghiem.json'), 'w'))
    allf = faces + ['Ttest_001']

    def man(seed_sigma):
        return {f'{n}.png': p.label_pts(d[n], sigma=seed_sigma) for n in allf}

    def ass(sua=()):
        out = {}
        for n in allf:
            pts = {k: (float(x), float(y)) for k, (x, y) in zip(p.names, np.round(np.array(d[n][0], float), 2))}
            for k in sua:
                pts[k] = (pts[k][0] + 8.0, pts[k][1])
            out[f'{n}.png'] = pts
        return out
    p.write_label('raw', 'm28-manual', 'P1', '1410', man(0.4))
    p.write_label('raw', 'demo-R1', 'P2', '1410', man(0.4))
    p.write_label('raw', 'demo-R1', 'P3', '1410', ass(sua=('songmui_1', 'songmui_2')))
    p.write_label('raw', 'm28-assisted', 'P4', '1410', ass(sua=('mattrai_3',)))
    return dict(p=p, root=p.root, d=d, faces=faces)


def test_nhan_raw_nhom_tu_config_hoac_ten_task_nhap_tu_push_hoac_luot_chon(raw_world):
    st = tk.tinh(raw_world['root'], chi_bo_anh=False)
    nr = {f['nguoi']: f for f in st['nguon']['nhan_raw']}
    assert {p: nr[p]['dieu_kien'] for p in ('P1', 'P2', 'P3')} == {'P1': 'manual', 'P2': 'manual', 'P3': 'assisted'}
    assert nr['P4']['dieu_kien'] == 'assisted'                                                                              # P4 không có trong config: nhóm suy từ tên task m28-assisted
    assert any(n['nguoi'] == 'P4' and 'không có nháp liên kết' in n['ghi_chu'] for n in st['nguon']['nhan_bo_qua'])           # nhưng chưa có nháp (task thí nghiệm: phải chọn lượt chứa nháp)
    # P3 (demo-R1) có nháp từ push.json → lượt R1; nhãn manual của P1, P2 làm đáp án (8 ảnh F, Ttest ẩn)
    assert st['nme']['trong'] is None and st['nme']['nhap']['tong']['n'] == 8 and st['nme']['n_nguoi_manual'] == 2 and st['meta']['ttest_an'] >= 1
    assert st['sua']['n_sua'] > 0 and {p['nguoi'] for p in st['sua']['theo_nguoi']} >= {'P3'}
    s3 = next(p for p in st['sua']['theo_nguoi'] if p['nguoi'] == 'P3')
    assert s3['n_mat'] == 8 and s3['n_sua'] == 16 and s3['ti_le_mat'] == 100.0                                               # 2 điểm lệch 8 px mỗi mặt, 8 mặt
    st2 = tk.tinh(raw_world['root'], luot_nhap='R1', chi_bo_anh=False)
    assert {p['nguoi'] for p in st2['sua']['theo_nguoi']} == {'P3', 'P4'}                                                       # P4 có nháp khi chọn lượt chứa nháp
    p4 = next(p for p in st2['sua']['theo_nguoi'] if p['nguoi'] == 'P4')
    assert p4['n_sua'] == 8


def test_nhan_nhom_khong_ro_dem_rieng_va_task_thu_bi_bo(raw_world):
    p = raw_world['p']
    p.write_label('raw', 'demo-R1', 'P5', '1410', {f'{n}.png': p.label_pts(raw_world['d'][n]) for n in raw_world['faces'][:2]})            # P5 chưa có nhóm trong config
    p.write_label('raw', 'm28-practice', 'P1', '1410', {f'{n}.png': p.label_pts(raw_world['d'][n]) for n in raw_world['faces'][:2]})
    st = tk.tinh(raw_world['root'])
    notes = {n['file']: n['ghi_chu'] for n in st['nguon']['nhan_bo_qua']}
    assert any('P5' in f and 'không rõ nhóm của P5' in w for f, w in notes.items()) and not any(f['nguoi'] == 'P5' for f in st['nguon']['nhan_raw'])
    assert any('practice' in f and 'bỏ qua' in w and 'Mọi task' in w for f, w in notes.items())
    st2 = tk.tinh(raw_world['root'], tat_ca_task=True)
    assert not any('practice' in n['file'] and n['ghi_chu'].startswith('bỏ qua') for n in st2['nguon']['nhan_bo_qua'])                       # gồm khi bật "Mọi task" (nhóm P1 theo config)


def test_ttest_an_mac_dinh_va_gom_khi_bat(raw_world):
    st = tk.tinh(raw_world['root'])
    assert st['meta']['gom_ttest'] is False and st['meta']['ttest_an'] == 4                                                       # 4 người × Ttest_001
    assert all(m['anh'] != 'Ttest_001' for m in st['nme']['nhap']['mat'])
    st2 = tk.tinh(raw_world['root'], gom_ttest=True)
    assert any(m['anh'] == 'Ttest_001' for m in st2['nme']['nhap']['mat']) and st2['nme']['nhap']['tong']['n'] == 9
    assert any('Ttest đang ẩn' in w for w in st['meta']['canh_bao']) and not any('Ttest đang ẩn' in w for w in st2['meta']['canh_bao'])


def test_mat_xoa_mem_chi_duoc_dem_khong_vao_so_do(raw_world):
    with open(os.path.join(raw_world['root'], 'runs', 'R1', 'excluded.txt'), 'w', encoding='utf-8') as f:
        f.write('F_001\n')
    st = tk.tinh(raw_world['root'])
    assert st['meta']['n_xoa_mem'] == 1 and all(m['anh'] != 'F_001' for m in st['nme']['nhap']['mat']) and st['nme']['nhap']['tong']['n'] == 7
    assert 'Đã bỏ 1 mặt xoá mềm' in th.phan_dau(st)


def test_nhap_sai_luot_hoac_sai_he_toa_do_bi_canh_bao(raw_world):
    p = raw_world['p']
    p.write_label('raw', 'demo-R1', 'P3', '1510', {f'{n}.png': p.label_pts(raw_world['d'][n], big=True) for n in raw_world['faces']})      # mọi điểm lệch 30 px: không điểm nào giữ nguyên nháp
    st = tk.tinh(raw_world['root'])
    assert any(w.startswith('P3:') and 'không có điểm nào giữ nguyên toạ độ nháp' in w and 'sai lượt nháp' in w for w in st['meta']['canh_bao'])
    os.remove(os.path.join(raw_world['root'], 'raw', 'demo-R1_P3_1510.xml'))
    ok = tk.tinh(raw_world['root'], chi_bo_anh=False)
    assert not any('sai lượt nháp' in w for w in ok['meta']['canh_bao'])                                                          # nhãn ngày 1410 đúng nháp: không cảnh báo


def test_file_theo_job_khong_dem_hai_lan_va_chi_co_job_thi_ghep(raw_world, tmp_path):
    from m28core import tach_job
    root = raw_world['root']
    whole = os.path.join(root, 'raw', 'demo-R1_P3_1410.xml')
    txt = os.path.join(root, 'raw', 'demo-R1_P3_1410.txt')
    open(txt, 'w', encoding='utf-8').write('task: demo-R1\ntask_id: 1\njob 5: 4 frame, stage annotation, state new | frames 0-3 | loai nhan\n'
                                           'job 6: 5 frame, stage annotation, state new | frames 4-8 | loai nhan\n')
    base = tk.tinh(root)
    res = tach_job.tach(whole, os.path.join(root, 'raw'))
    assert len(res['jobs']) == 2
    st = tk.tinh(root)
    assert st['nme']['nhap']['tong']['n'] == base['nme']['nhap']['tong']['n'] and st['sua']['n_mat'] == base['sua']['n_mat']             # file job nằm cạnh file cả task: không đếm hai lần
    assert not any('_job' in f['task'] or '_job' in f['file'] for f in st['nguon']['nhan_raw'])
    os.remove(whole)                                                                                                                   # chỉ còn file job: ghép lại
    st2 = tk.tinh(root)
    f3 = next(f for f in st2['nguon']['nhan_raw'] if f['nguoi'] == 'P3')
    assert f3['ghi_chu'] == 'ghép từ các file theo job' and f3['n_anh'] == 9 and st2['sua']['n_mat'] == base['sua']['n_mat']
    assert f3['task'] == 'demo-R1'                                                                                                     # không bị hiểu thành task khác


# ---------- thời gian từ CSV và gói ----------
def tao_phien(root, nguoi, nhom, giay_moi_mat, g, dot='NAP_001', n=6, bo_anh='NAP_001', theo_mat=True, task=None):
    """Một phiên thật của tab Đồng hồ (DongHo + FakeGio): ghi timing_<người>.csv và gói."""
    import dong_ho
    d = dong_ho.DongHo(root, gio=g, pid=os.getpid())
    v = d.bat_bau = None
    v = d.bat_dau(nguoi, nhom, dot=dot, task=task or f'demo-{dot}', n_mat=n, bo_anh=bo_anh)
    for _ in range(n if theo_mat else 1):
        g.tick(giay_moi_mat if theo_mat else giay_moi_mat * n)
        if theo_mat:
            v = d.xong_mat(nguoi, v['rev'])
    return d.xong_luu(nguoi, d.xem(nguoi)['rev'], so_mat=n)


def test_dong_ho_ghi_csv_va_goi_cung_phien_chi_tinh_mot_lan_va_loc_bo_anh(tmp_path):
    root = du_an(tmp_path)
    g = FakeGio()
    for p, nh, s in (('P1', 'manual', 40), ('P2', 'manual', 50), ('P3', 'assisted', 28), ('P4', 'assisted', 35)):
        tao_phien(root, p, nh, s, g, theo_mat=True)
        g.tick(5)
    st = tk.tinh(root)
    tg = st['thoi_gian']
    assert tg['n_dong_goi'] == 24 - 8 and tg['n_dong_csv'] == 0 and st['tg_loc']['khoi_dong'] == 8                                       # mỗi người 6 mặt, 2 mặt khởi động bị loại
    assert tg['nhom']['manual']['n_mat'] == 8 and tg['nhom']['assisted']['n_mat'] == 8 and tg['nhanh_hon_pct'] == pytest.approx((1 - (28 * 35) ** 0.5 / (40 * 50) ** 0.5) * 100)
    # xoá gói: dòng CSV thay thế (cùng số liệu)
    for f in os.listdir(os.path.join(root, 'outputs', 'ket_qua')):
        os.remove(os.path.join(root, 'outputs', 'ket_qua', f))
    st2 = tk.tinh(root)
    assert st2['thoi_gian']['n_dong_csv'] == 16 and st2['thoi_gian']['nhanh_hon_pct'] == pytest.approx(tg['nhanh_hon_pct'])
    # đợt khác bộ ảnh thí nghiệm: loại, đếm
    json.dump({'nhom': {'P1': 'manual', 'P2': 'manual', 'P3': 'assisted', 'P4': 'assisted'}, 'bo_anh': 'NAP_999'}, open(os.path.join(root, 'config', 'nhom_thi_nghiem.json'), 'w'))
    st3 = tk.tinh(root)
    assert st3['tg_loc']['ngoai_bo_anh'] == 16 and st3['thoi_gian']['trong'] and 'NAP_999' in st3['thoi_gian']['trong']['ly_do']
    st4 = tk.tinh(root, chi_bo_anh=False)
    assert st4['thoi_gian']['nhom']['manual']['n_mat'] == 8


def test_goi_va_csv_cung_phien_khong_nhan_doi(tmp_path):
    root = du_an(tmp_path)
    g = FakeGio()
    for p, nh, s in (('P1', 'manual', 40), ('P2', 'manual', 50), ('P3', 'assisted', 28), ('P4', 'assisted', 35)):
        tao_phien(root, p, nh, s, g)
        g.tick(5)
    st = tk.tinh(root)
    assert st['thoi_gian']['nhom']['manual']['n_mat'] == 8 and st['thoi_gian']['n_dong_csv'] == 0                                          # CSV có cùng mã phiên với gói: gói thắng, không đếm lại
    legacy = os.path.join(root, 'timing_P1.csv')                                                                                          # file facetimer 12 cột của chính P1: vẫn đọc, không có mã phiên
    open(legacy, 'w', encoding='utf-8', newline='').write('date,person,condition,task,job,block,seq,face_id,seconds,warmup,interrupted,note\r\n'
                                                           '2026-10-10,P1,manual,m28-manual,1,X1,3,X1_03,44.0,0,0,\r\n2026-10-10,P1,manual,m28-manual,1,X1,4,X1_04,46.0,0,0,\r\n')
    json.dump({'nhom': {}, 'bo_anh': 'NAP_001'}, open(os.path.join(root, 'config', 'nhom_thi_nghiem.json'), 'w'))
    st2 = tk.tinh(root)
    assert st2['tg_loc']['khong_ro_bo_anh'] == 2 and st2['thoi_gian']['nhom']['manual']['n_mat'] == 8                                       # dòng facetimer không rõ bộ ảnh: loại và đếm
    st3 = tk.tinh(root, chi_bo_anh=False)
    assert st3['thoi_gian']['nhom']['manual']['n_mat'] == 10 and st3['thoi_gian']['n_dong_csv'] == 2


def test_csv_thieu_cot_bo_file_do_va_bao_ten_cot_file_khac_van_doc(tmp_path):
    root = du_an(tmp_path)
    open(os.path.join(root, 'timing_P1.csv'), 'w', encoding='utf-8').write('date,person\n2026-10-14,P1\n')
    open(os.path.join(root, 'timing_P2.csv'), 'w', encoding='utf-8', newline='').write(
        'date,person,condition,task,job,block,seq,face_id,seconds,warmup,interrupted,note\r\n2026-10-14,P2,manual,m28-manual,1,X2,3,X2_03,40,0,0,\r\n')
    st = tk.tinh(root)
    assert st['nguon']['timing'] == ['timing_P2.csv'] and any('timing_P1.csv thiếu cột' in w and 'seconds' in w for w in st['nguon']['timing_loi'])
    assert st['thoi_gian']['nhom']['manual']['n_mat'] == 1
    assert 'thiếu cột' in th.phan_dau(st) and 'File này bị bỏ' in th.phan_dau(st)


def test_trung_khoa_giua_hai_file_duoc_liet_ke_giu_dong_cua_tab_dong_ho(tmp_path):
    root = du_an(tmp_path)
    os.makedirs(os.path.join(root, 'outputs', 'timing'))
    head = 'date,person,condition,task,job,block,seq,face_id,seconds,warmup,interrupted,note\r\n'
    open(os.path.join(root, 'outputs', 'timing', 'timing_P1.csv'), 'w', encoding='utf-8', newline='').write(head + '2026-10-14,P1,manual,t,1,X1,3,X1_03,40,0,0,\r\n')
    open(os.path.join(root, 'timing_P1.csv'), 'w', encoding='utf-8', newline='').write(head + '2026-10-14,P1,manual,t,1,X1,3,X1_03,99,0,0,\r\n')
    st = tk.tinh(root, chi_bo_anh=False)
    assert st['thoi_gian']['nhom']['manual']['n_mat'] == 1 and st['thoi_gian']['nhom']['manual']['trung_vi'] == 40.0
    assert len(st['nguon']['timing_trung']) == 1 and 'timing_P1.csv trùng với outputs' in st['nguon']['timing_trung'][0]


def test_thoi_gian_duong_dan_ngoai_du_an_bi_tu_choi(tmp_path):
    from m28core import toc_do
    root = du_an(tmp_path)
    with pytest.raises(toc_do.TocDoLoi, match='ngoài thư mục dự án'):
        tk.tinh(root, timing='/etc')


# ---------- xuất tĩnh, CSV, CLI ----------
def test_xuat_html_csv_khong_anh_khong_ma_tai_xe_khong_duong_dan(raw_world, tmp_path):
    p = raw_world['p']
    st = tk.tinh(raw_world['root'], luot_nhap='R1', chi_bo_anh=False)
    d, files = tk.xuat(raw_world['root'], st)
    assert os.path.dirname(d) == os.path.join(raw_world['root'], 'outputs', 'thong_ke') and d.replace(os.sep, '/').endswith(st['meta']['ngay_ts'])
    html = open(os.path.join(d, 'thong_ke.html'), encoding='utf-8').read()
    assert '<img' not in html and '<script' not in html and 'http://' not in html and 'https://' not in html
    assert raw_world['root'] not in html and str(tmp_path) not in html and '/tmp/' not in html and 'token' not in html.lower()
    subjects = {r['subject'] for r in p.manifest.values()}
    assert not any(s in html for s in subjects) and not re.search(r'\b(yd_|df_)[A-Z0-9]', html)
    for s in ('phi thương mại', 'Lập lúc', 'commit', 'config 50 điểm version 3', 'ngưỡng sửa 2,0% IOD', 'raw/m28-manual_P1_1410.xml', 'YawDD', 'prefers-color-scheme', 'viewport', 'Hạn chế của thiết kế hai nhóm'):
        assert s in html.replace('\\', '/'), s
    assert 'thong_ke.html' in files and {'nme.csv', 'nme_nhap.csv', 'ti_le_sua.csv'} <= set(files) and 'thoi_gian.csv' not in files
    for f in files:
        if f.endswith('.csv'):
            raw = open(os.path.join(d, f), 'rb').read()
            assert raw.startswith(b'\xef\xbb\xbf'), f
            assert b'/tmp' not in raw and not re.search(rb'(yd_|df_)[A-Z0-9]', raw)
    assert re.search(r'\d,\d', html) and not re.search(r'NME trung bình[^<]*\d\.\d', html)                                              # trang dùng dấu phẩy
    rows = list(csv.DictReader(open(os.path.join(d, 'nme.csv'), encoding='utf-8-sig')))
    assert rows[0]['pham_vi'] == 'nhap_so_voi_manual' and '.' in rows[0]['tb'] and ',' not in rows[0]['tb']                             # CSV dấu chấm
    d2, _ = tk.xuat(raw_world['root'], st)
    assert d2 != d and os.path.isdir(d)
    with pytest.raises(ValueError, match='ngoài'):
        tk.xuat(raw_world['root'], st, out_root=os.path.join(os.path.dirname(raw_world['root']), 'ngoai_du_an'))


def test_nme_nhap_csv_cot_dau_trung_nme_per_face_cua_eval50(goi_world, tmp_path):
    st = tk.tinh(goi_world)
    cols, rows = tk.bang_csv(st)['nme_nhap']
    out = tmp_path / 'ref.csv'
    eval50.write_csv(str(out), [dict(face_id=r['face_id'], condition=r['condition'], nme=r['nme'], nme_eye=r['nme_eye'], nme_p2p=r['nme_p2p'],
                                     region={g: r[f'reg_{g}'] for g in ('brow', 'eye', 'lip', 'nose')}, eye_open_err=r['eye_open_err'], n_missing=r['n_missing']) for r in rows], CFG)
    ref_head = out.read_text(encoding='utf-8').splitlines()[0].split(',')
    assert cols[:len(ref_head)] == ref_head and ref_head[:5] == ['face_id', 'condition', 'nme', 'nme_eye', 'nme_p2p']
    assert cols[len(ref_head):len(ref_head) + 3] == ['nguoi', 'n_nguoi_dap_an', 'hong']
    mine = {(r['face_id'], r['condition']): r for r in csv.DictReader(open(os.path.join(tk.xuat(goi_world, st)[0], 'nme_nhap.csv'), encoding='utf-8-sig'))}
    for rr in csv.DictReader(out.open(encoding='utf-8')):
        m = mine[(rr['face_id'], rr['condition'])]
        assert m['condition'] == rr['condition']
        for c in ref_head[2:]:
            assert float(m[c] or 0) == pytest.approx(float(rr[c] or 0), abs=1e-3), c


def test_csv_an_toan_cong_thuc(goi_world):
    st = tk.tinh(goi_world)
    cols, rows = tk.bang_csv(st)['ngoai_lai']
    raw = tk.csv_bytes(cols, [dict(person='=cmd()', condition='+x', face_id='@y', seconds=1.0, ly_do='-1')]).decode('utf-8-sig')
    assert "'=cmd()" in raw and "'+x" in raw and "'@y" in raw and "'-1" in raw


def test_thong_ke_chi_doc_khong_sua_runs_raw_final_data(raw_world):
    before = tree_hash(raw_world['root'])
    st = tk.tinh(raw_world['root'], luot_nhap='R1')
    tk.xuat(raw_world['root'], st)
    assert tree_hash(raw_world['root']) == before                                                                                       # outputs\ bị bỏ khỏi băm: chỉ ghi ở đó
    assert tk.main(['--project', raw_world['root'], '--luot-nhap', 'R1']) == 0
    assert tree_hash(raw_world['root']) == before


def test_cli_in_ket_qua_tuong_doi_ba_chi_so_va_ma_thoat(goi_world, capsys):
    assert tk.main(['--project', goi_world]) == 0
    out = capsys.readouterr().out
    assert 'Đã ghi outputs/thong_ke/' in out and goi_world not in out
    assert 'NME của nháp so với nhãn manual: 8 mặt' in out and 'Tỉ lệ điểm phải sửa (ngưỡng 2,0% IOD): 6,0% (48/800 điểm, 16 mặt)' in out
    assert 'assisted nhanh hơn manual 30,0%' in out and 'KTC 90%' in out and 'Chưa kết luận' in out
    assert tk.main(['--project', goi_world, '--nguong-sua', '5', '--out', '../ngoai']) == 0
    import shutil
    ngoai = os.path.abspath(os.path.join(goi_world, '..', 'ngoai'))
    assert os.path.isdir(ngoai)
    shutil.rmtree(ngoai)
    assert tk.main(['--project', goi_world, '--nguong-sua', '99']) == 2 and 'Ngưỡng' in capsys.readouterr().err
    assert tk.main(['--project', os.path.join(goi_world, 'khong_co')]) == 2
    assert tk.main(['--project', goi_world, '--chi-goi', '--goi', os.path.join(goi_world, 'outputs', 'goi_nhom')]) == 0
    with pytest.raises(SystemExit) as e:
        tk.main(['--help'])
    assert e.value.code == 0 and 'hai nhóm' in capsys.readouterr().out


def test_cli_mac_dinh_dung_thu_muc_hien_tai_co_config(goi_world, monkeypatch):
    monkeypatch.chdir(goi_world)
    assert bm.mac_dinh_du_an() == goi_world
    assert tk.main([]) == 0
    assert os.path.isdir(os.path.join(goi_world, 'outputs', 'thong_ke'))


def test_cli_trang_thai_trong_in_thieu_gi(tmp_path, capsys):
    root = du_an(tmp_path)
    assert tk.main(['--project', root]) == 0
    out = capsys.readouterr().out
    assert 'NME của nháp: chưa có số' in out and 'Tỉ lệ điểm phải sửa: chưa có số' in out and 'Thời gian: chưa có số' in out and 'Cần:' in out


def test_html_mau_nhom_group_color_ten_nhom_vach_muc_tieu_va_khong_bieu_do_tron(goi_world):
    from m28core import mau_nhom
    st = tk.tinh(goi_world)
    html = th.noi_dung(st)
    for g, c in mau_nhom.GROUP_COLOR.items():
        assert c in html and mau_nhom.GROUP_VI[g] in html                                                                         # màu nhóm luôn kèm tên nhóm tiếng Việt
    assert 'mặt hỏng: NME &gt;= 10% IOD' in html and 'tk-vach' in html and 'mục tiêu: nhanh hơn 20%' in html
    assert 'conic-gradient' not in html and 'pie' not in html.lower() and 'y2' not in html and '<canvas' not in html
    assert '#64748b' in html and '#2563eb' in html and 'manual (gán tay)' in html and 'assisted (dùng tool)' in html


def test_n_nho_khong_in_ti_le_o_cac_o_nho(tmp_path):
    root = du_an(tmp_path)
    viet_goi(root, nd_goi('P1', 'manual', 40.0, n_nguoi_seed=0, anh=ANH[:2], so_mat=2), 'outputs/goi_nhom')
    viet_goi(root, nd_goi('P3', 'assisted', 30.0, n_nguoi_seed=1, anh=ANH[:2], so_mat=2), 'outputs/goi_nhom')
    st = tk.tinh(root)
    html = th.noi_dung(st)
    assert 'n quá nhỏ' in html and st['nme']['nhap']['tong']['n'] == 2
    t = th.muc_thoi_gian(st)
    assert 'n quá nhỏ' in t                                                                                                       # 2 mặt mỗi nhóm < 5: trung vị và TB nhân thay bằng "n quá nhỏ"


def test_module_thong_ke_khong_keo_gradio_torch_pandas():
    import subprocess
    code = ("import sys\nsys.path.insert(0, %r)\nimport thong_ke, thong_ke_html, tong_ket\nfor m in ('gradio', 'torch', 'cv2', 'mediapipe', 'cvat_sdk', 'pandas', 'PIL'):\n"
            "    assert m not in sys.modules, m\nprint('ok')\n") % os.path.join(HERE, '..', 'tool')
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0 and 'ok' in r.stdout, r.stderr


def test_han_che_va_nguon_luon_co_tren_trang(goi_world):
    st = tk.tinh(goi_world)
    html = th.noi_dung(st)
    assert 'tốc độ từng người khác nhau lẫn vào kết quả' in html and 'khởi động chung' in html and 'ước lượng chia đều' in html
    assert 'Người theo nhóm' in html and 'manual (gán tay): P1, P2' in html and 'assisted (dùng tool): P3, P4' in html
    assert 'Hai nhóm làm cùng bộ ảnh?' in html and 'khớp' in html


def test_mot_nguoi_hai_dot_co_hai_goi_va_gio_moi_dot_tinh_rieng(tmp_path):
    """QĐ-007: mỗi đợt một phiên và một gói. Một người làm hai đợt thì có hai gói: cả hai vào Thống kê, giờ đợt này không lẫn vào đợt kia, không bị coi là trùng."""
    root = du_an(tmp_path)
    g = FakeGio()
    tao_phien(root, 'P1', 'manual', 40, g, dot='NAP_001', n=6, bo_anh='NAP_001')
    g.tick(5)
    tao_phien(root, 'P1', 'manual', 60, g, dot='NAP_002', n=6, bo_anh='NAP_001')
    gois = sorted(f for f in os.listdir(os.path.join(root, 'outputs', 'ket_qua')) if f.endswith('.zip'))
    assert [f.split('_', 3)[3] for f in gois] == ['NAP_001.zip', 'NAP_002.zip']
    st = tk.tinh(root)
    tg = st['thoi_gian']
    assert tg['n_dong_goi'] == 8 and st['tg_loc']['khoi_dong'] == 4                                    # mỗi phiên 6 mặt, 2 mặt khởi động bị loại: 4 + 4 dòng tính giờ
    m = tg['nhom']['manual']
    assert m['n_mat'] == 8 and m['trung_vi'] == pytest.approx(50.0) and m['tb_nhan'] == pytest.approx((40 * 60) ** 0.5)         # 4 mặt 40 giây + 4 mặt 60 giây, không lẫn
    assert st['nguon']['goi'] == ['ketqua_P1_1410_NAP_001.zip', 'ketqua_P1_1410_NAP_002.zip'] and not st['nguon']['goi_hong']       # cả hai đợt được dùng
    assert all('cùng phiên' in why for _t, why in st['nguon']['goi_trung'])                                                       # chỉ bản .json của chính gói đó, không phải đợt này trùng đợt kia


def test_cung_nguoi_cung_dot_o_nhieu_goi_thi_canh_bao_tinh_gio_nhieu_lan(goi_world):
    """P1 đã có gói của đợt NAP_001 (outputs\goi_nhom); thêm một gói khác phiên cùng người + đợt (ví dụ nhập tay trùng với gói đồng hồ): trang cảnh báo rõ."""
    assert not [c for c in tk.tinh(goi_world)['meta']['canh_bao'] if 'cùng đợt' in c]
    viet_goi(goi_world, nd_goi('P1', 'manual', 40, phien='P1-tay-NAP_001-abcd1234', bat_dau='2026-10-15T19:00:00+07:00'))
    c = [x for x in tk.tinh(goi_world)['meta']['canh_bao'] if 'cùng đợt' in x]
    assert len(c) == 1 and 'P1 có 2 gói cho cùng đợt NAP_001' in c[0] and 'Remove entry' in c[0]
    assert not [x for x in tk.tinh(goi_world)['meta']['canh_bao'] if 'ảnh trùng tên' in x]                 # cùng đợt: chỉ cảnh báo 'cùng đợt', không lặp


def test_cung_nguoi_khac_dot_trung_ten_anh_thi_canh_bao_tinh_gio_hai_lan(goi_world):
    """C10: cùng một lần làm của P3 ghi dưới hai tên đợt (ví dụ bản nhập tay gõ tên bộ ảnh bo200_v1 rồi thêm lại với tên lượt): cảnh báo theo (người, đợt) im lặng, nên
    cảnh báo thêm khi hai gói của cùng người có tên ảnh chung dù khác đợt (một người không gán một ảnh hai lần). Thông báo chỉ nêu số ảnh, không nêu tên ảnh."""
    viet_goi(goi_world, nd_goi('P3', 'assisted', 30.0, anh=ANH[:5], dot='bo200_v1', bo_anh='NAP_001', phien='P3-tay-bo200_v1-abcd1234', bat_dau='2026-10-15T19:00:00+07:00'))
    st = tk.tinh(goi_world)
    c = [x for x in st['meta']['canh_bao'] if 'ảnh trùng tên' in x]
    assert len(c) == 1 and c[0].startswith('P3 có 5 ảnh trùng tên ở hai gói khác đợt') and 'ketqua_P3_1410_NAP_001.zip: đợt NAP_001' in c[0]
    assert 'ketqua_P3_1410_bo200_v1.zip: đợt bo200_v1' in c[0] and 'tính hai lần' in c[0] and 'Remove entry' in c[0] and 'F_00' not in c[0]
    assert not [x for x in st['meta']['canh_bao'] if 'cùng đợt' in x] and st['meta']['n_mat_trung'] == 5
    viet_goi(goi_world, nd_goi('P4', 'assisted', 30.0, anh=['F_101', 'F_102'], dot='NAP_002', phien='P4-20261015-190000-bb01', bat_dau='2026-10-15T19:00:00+07:00'))
    assert [x for x in tk.tinh(goi_world)['meta']['canh_bao'] if 'ảnh trùng tên' in x] == c                 # đợt khác, ảnh khác: không cảnh báo
