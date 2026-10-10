"""Thử tool/m28core/toc_do.py: giao thức tốc độ của P5 (khởi động, r_i, trung bình nhân, bootstrap seed 28, ngoại lai, n nhỏ, < 3 người) bằng file bấm giờ GIẢ."""
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
sys.path.insert(0, HERE)
from m28core import toc_do as td  # noqa: E402
from thong_ke_fake import Proj, TIMING_COLS  # noqa: E402


def rows_of(proj, **kw):
    proj.write_timing(**kw)
    return td.doc_nhieu(td.tim_file(proj.root))


@pytest.fixture
def proj(tmp_path):
    return Proj(tmp_path)


def test_giao_thuc_ri_trung_binh_nhan_tay(tmp_path):
    """Số tính tay: 3 người, mỗi người 2 mặt manual (10, 20 giây -> TB 15) và 2 mặt assisted; khởi động và task khác không tính."""
    def row(p, cond, seq, sec, warm=0, task=None, block='X1', intr=0):
        return dict(date='2026-10-14', person=p, condition=cond, task=task or f'm28-{cond}', job='1', block=block, seq=seq, face_id=f'{block}_{seq:02d}',
                    seconds=sec, warmup=warm, interrupted=intr, note='', file='t.csv')
    rows = []
    for p, ratio in (('P1', 0.5), ('P2', 0.8), ('P3', 1.25)):
        rows += [row(p, 'manual', 3, 10.0), row(p, 'manual', 4, 20.0), row(p, 'assisted', 3, 10.0 * ratio), row(p, 'assisted', 4, 20.0 * ratio)]
        rows += [row(p, 'manual', 1, 999.0, warm=1), row(p, 'assisted', 1, 999.0, warm=1)]          # khởi động: bỏ
        rows.append(row(p, 'manual', 5, 888.0, task='m28-pilot-manual'))                           # task khác: không vào chỉ số, vẫn vào bảng M24
    res = td.phan_tich(rows)
    assert res['n_warmup'] == 6 and res['n_khong_tn'] == 3 and res['n_x'] == 12
    assert {p: round(e['r'], 6) for p, e in res['nguoi'].items()} == {'P1': 0.5, 'P2': 0.8, 'P3': 1.25}
    g = (0.5 * 0.8 * 1.25) ** (1 / 3)                                                                 # trung bình nhân = 0,7937
    assert res['tb_nhan'] == pytest.approx(g) and res['nhanh_hon_pct'] == pytest.approx((1 - g) * 100)
    assert res['n_r_nho_hon_1'] == 2 and res['ket_luan'] == 'chua_ket_luan'                            # TB nhân <= 0,8 nhưng chỉ 2/3 người nhanh hơn (< 4/5)
    m24 = {(r['person'], r['condition']): (r['so_anh'], r['so_phut']) for r in res['m24']}
    assert m24[('P1', 'manual')] == (3, round((10 + 20 + 888) / 60, 1))                               # M24 gồm cả task khác, không gồm khởi động
    # giờ tiết kiệm trộn: manual 15 giây, assisted TB(5, 10, 8, 16, 12.5, 25) = 12.75 -> (15 - 12.75) * 1000 / 3600
    assert res['gio']['gio_1000'] == pytest.approx((15 - 12.75) * 1000 / 3600)


def test_luat_dat_khong_dat_chua_ket_luan():
    def mk(ratios):
        out = []
        for i, r in enumerate(ratios):
            p = f'P{i + 1}'
            for seq in range(3, 11):
                for cond, f in (('manual', 1.0), ('assisted', r)):
                    out.append(dict(date='d', person=p, condition=cond, task=f'm28-{cond}', job='1', block=f'X{i + 1}', seq=seq, face_id=f'X{i + 1}_{seq:02d}',
                                    seconds=50.0 * f, warmup=0, interrupted=0, note='', file='t'))
        return out
    assert td.phan_tich(mk([0.7, 0.75, 0.78, 0.6, 0.9]))['ket_luan'] == 'dat'                           # TB nhân < 0,8 và 5/5 người nhanh hơn
    assert td.phan_tich(mk([0.7, 0.7, 0.7, 0.65, 1.4]))['ket_luan'] == 'dat'                           # 4/5 người nhanh hơn và TB nhân 0,792 <= 0,8
    assert td.phan_tich(mk([0.7, 0.7, 0.7, 0.7, 1.4]))['ket_luan'] != 'dat'                            # TB nhân 0,804 > 0,8: không đạt dù 4/5 người nhanh hơn
    kdat = td.phan_tich(mk([0.9, 0.95, 1.1, 0.85, 1.0]))                                                  # TB nhân ~ 0,96; mỗi người một khối riêng nên không có sai số bootstrap
    assert kdat['ket_luan'] == 'khong_dat' and kdat['ktc90'][0] > 0.80                                   # cận dưới KTC > 0,80 (đề xuất của P5)
    sat = td.phan_tich(mk([0.8, 0.8, 0.8, 0.8, 0.8]))
    assert sat['ket_luan'] == 'dat'                                                                       # đúng 0,80 vẫn đạt (<=)


def test_it_hon_3_nguoi_khong_ket_luan(proj):
    rows = rows_of(proj, people=('P1', 'P2'))
    res = td.phan_tich(rows)
    assert res['ok'] is False and res['ket_luan'] == 'chua_du_du_lieu' and res['tb_nhan'] is None and res['nhanh_hon_pct'] is None
    assert 'Chưa đủ dữ liệu' in res['ly_do_trong'] and '2 người' in res['ly_do_trong']
    assert td.phan_tich([])['ly_do_trong'] == 'Chưa có dòng bấm giờ nào.'


def test_nguoi_thieu_mot_dieu_kien_khong_co_ri(proj):
    rows = rows_of(proj)
    rows = [r for r in rows if not (r['person'] == 'P3' and r['condition'] == 'assisted')]
    res = td.phan_tich(rows)
    assert res['nguoi']['P3']['r'] is None and res['n_nguoi'] == 4 and res['ok']
    assert res['thieu'] == [('P3', 'thiếu assisted (cần cả hai điều kiện, không tính warmup)')]


def test_ngoai_lai_va_gian_doan_danh_dau_nhung_van_trong_chi_so_chinh(proj):
    rows = rows_of(proj)
    res = td.phan_tich(rows)
    assert {(o['person'], o['condition'], o['face_id']) for o in res['ngoai_lai']} == {('P1', 'manual', 'X1_06'), ('P1', 'assisted', 'X2_06')}
    assert [(g['person'], g['face_id']) for g in res['gian_doan']] == [('P1', 'X1_07')]
    # chỉ số chính tính trên TẤT CẢ (kể cả ngoại lai): bỏ chúng đi thì khác
    no_out = [r for r in rows if r['seconds'] not in (400.0, 330.0)]
    assert td.phan_tich(no_out)['tb_nhan'] != pytest.approx(res['tb_nhan'])
    assert res['do_nhay']['n_bo'] == 3 and res['do_nhay']['tb_nhan'] == pytest.approx(td.phan_tich([r for r in rows if r['seconds'] not in (400.0, 330.0) and not r['interrupted']])['tb_nhan'])
    # ngưỡng Q3 + 3·IQR trên 8 giá trị của (người, điều kiện)
    v = np.array([r['seconds'] for r in rows if r['person'] == 'P1' and r['condition'] == 'manual' and r['warmup'] == 0])
    q1, q3 = np.percentile(v, [25, 75])
    assert [o['nguong'] for o in res['ngoai_lai'] if o['condition'] == 'manual'] == [pytest.approx(q3 + 3 * (q3 - q1))]


def test_giay_trong_hoac_khong_duong_bi_bo_va_dem(proj):
    rows = rows_of(proj, outliers=False)
    rows[10]['seconds'] = None
    rows[11]['seconds'] = 0.0
    rows[12]['seconds'] = -3.0
    res = td.phan_tich(rows)
    assert res['n_bo_giay'] == 3 and res['ok']


def test_bootstrap_lap_lai_duoc_seed_28_va_khop_code_pandas_cua_p5(proj):
    rows = rows_of(proj)
    a, b = td.phan_tich(rows), td.phan_tich(rows)
    assert a['ktc90'] == b['ktc90'] and a['tb_nhan'] == b['tb_nhan']                                 # seed 28: lặp lại từng chữ số
    assert td.phan_tich(rows, n_boot=2000, seed=29)['ktc90'] != a['ktc90']
    pd = pytest.importorskip('pandas')
    r_ref, g_ref, ktc_ref, gio_ref = td.pandas_tham_chieu(proj.root)
    assert {p: e['r'] for p, e in a['nguoi'].items()} == pytest.approx(r_ref)
    assert a['tb_nhan'] == pytest.approx(g_ref)
    assert list(a['ktc90']) == pytest.approx(ktc_ref, abs=1e-9)                                       # cùng chuỗi số ngẫu nhiên, cùng KTC
    assert a['gio']['gio_1000'] == pytest.approx(gio_ref) and pd is not None


def test_nhom_nghieng_che_theo_manifest(proj):
    for i in range(1, 6):
        for s in range(1, 11):
            proj.add_face(f'X{i}_{s:02d}', 'yawdd', 'X', pose=int(s % 5 == 0), occlusion=int(s == 7))
    from m28core import bang_mat
    rows = rows_of(proj, outliers=False)
    res = td.phan_tich(rows, bang_mat.read_manifest(proj.root))
    assert res['nhom']['nghieng_che']['n_manual'] > 0 and res['nhom']['con_lai']['n_assisted'] > 0
    kho = [r for r in rows if r['warmup'] == 0 and (int(r['seq']) % 5 == 0 or r['seq'] == 7)]
    sv = {c: np.mean([r['seconds'] for r in kho if r['condition'] == c]) for c in ('manual', 'assisted')}
    assert res['nhom']['nghieng_che']['gio_1000'] == pytest.approx((sv['manual'] - sv['assisted']) * 1000 / 3600)
    assert td.phan_tich(rows, None)['nhom'] is None and 'manifest' in td.phan_tich(rows, None)['nhom_ly_do']


def test_doc_file_thieu_cot_bao_ten_cot(tmp_path):
    p = tmp_path / 'timing_P1.csv'
    p.write_text('date,person,condition,task\n2026-10-14,P1,manual,m28-manual\n', encoding='utf-8')
    with pytest.raises(td.TocDoLoi) as e:
        td.doc_file(str(p))
    for c in ('job', 'block', 'seq', 'face_id', 'seconds', 'warmup', 'interrupted', 'note'):
        assert c in str(e.value)
    assert 'timing_P1.csv' in str(e.value)


def test_tim_file_chi_trong_du_an(tmp_path):
    p = Proj(tmp_path)
    p.write_timing(folder='.', people=('P1',))
    p.write_timing(folder='outputs', people=('P2',))
    p.write_timing(folder='raw', people=('P3',))
    p.write_timing(folder='sub', people=('P4',))
    names = [os.path.basename(x) for x in td.tim_file(p.root)]
    assert names == ['timing_P1.csv', 'timing_P2.csv', 'timing_P3.csv']
    assert [os.path.basename(x) for x in td.tim_file(p.root, 'sub')] == ['timing_P1.csv', 'timing_P2.csv', 'timing_P3.csv', 'timing_P4.csv']
    with pytest.raises(td.TocDoLoi, match='ngoài'):
        td.tim_file(p.root, '/etc')
    with pytest.raises(td.TocDoLoi):
        td.tim_file(p.root, 'khong_co')


def test_giay_ra_tom_tat_bo_ngoai_lai_dem_rieng():
    s = td.tom_tat_giay([5, 8, 10, 12, 15, 200, 300], nguong=120)
    assert s['n'] == 5 and s['n_ngoai_lai'] == 2 and s['tong'] == 7 and s['trung_vi'] == 10 and s['phut_100'] == pytest.approx(10 * 100 / 60)
    assert (s['q1'], s['q3']) == (8, 12)
    e = td.tom_tat_giay([], 120)
    assert e['n'] == 0 and e['trung_vi'] is None and e['phut_100'] is None
    assert td.tom_tat_giay([None, 500], 120)['trung_vi'] is None


def test_timing_cols_khop_facetimer():
    p = os.path.join(HERE, '..', '..', '..', 'de-tai-m28', 'p5-thi-nghiem.md')
    if not os.path.isfile(p):
        pytest.skip('repo này không có bản chụp kế hoạch de-tai-m28/')
    src = open(p, encoding='utf-8').read()
    assert '"date", "person", "condition", "task", "job", "block", "seq"' in src and td.TIMING_COLS == TIMING_COLS
    assert len(td.TIMING_COLS) == 12
