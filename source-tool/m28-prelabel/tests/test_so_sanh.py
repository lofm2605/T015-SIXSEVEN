"""Thử m28core/so_sanh.py: ba chỉ số theo thiết kế HAI NHÓM ĐỘC LẬP (QĐ-006), số tính tay trên dữ liệu giả nhỏ. Không ảnh, không mạng."""
import math
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
sys.path.insert(0, HERE)
import eval50  # noqa: E402
from dh_fake import cfg_real, mat_mau  # noqa: E402
from m28core import so_sanh  # noqa: E402

CFG = cfg_real()


def pts(seed=0, **kw):
    return {k: list(v) for k, v in mat_mau(seed, **kw).items()}


def dich(p, dx=0.0, dy=0.0, ten=None):
    return {k: [x + (dx if (ten is None or k in ten) else 0.0), y + (dy if (ten is None or k in ten) else 0.0)] for k, (x, y) in p.items()}


# ---------- (2) điểm đã sửa ----------
def test_diem_sua_threshold_deleted_and_missing_iod():
    gt = pts(1)
    iod = eval50.iod(gt, CFG)
    nhap = dich(gt, ten=['songmui_1'], dx=0.03 * iod)                           # 3% IOD > 2%
    nhap = {**nhap, **dich({'songmui_2': gt['songmui_2']}, dx=0.015 * iod)}      # 1,5% IOD <= 2%
    r = so_sanh.diem_sua(nhap, gt, CFG, 2.0)
    assert r['ok'] and r['sua'] == {'songmui_1'} and r['xoa'] == set() and r['n_nhap'] == 50 and r['khoang_cach']['songmui_1'] == pytest.approx(3.0)
    assert so_sanh.diem_sua(nhap, gt, CFG, 1.0)['sua'] == {'songmui_1', 'songmui_2'}            # ngưỡng chỉnh được
    assert so_sanh.diem_sua(nhap, gt, CFG, 0.5)['sua'] >= {'songmui_1', 'songmui_2'}
    fin = {k: v for k, v in gt.items() if k != 'matphai_5'}
    r = so_sanh.diem_sua(gt, fin, CFG, 2.0)
    assert r['xoa'] == {'matphai_5'} and r['sua'] == set()                                      # xoá/ẩn tính là đã sửa, đếm riêng
    no_iod = {k: v for k, v in gt.items() if k != 'mattrai_1'}
    r = so_sanh.diem_sua(gt, no_iod, CFG, 2.0)
    assert not r['ok'] and 'iod_points' in r['ly_do']
    r = so_sanh.diem_sua({k: v for k, v in gt.items() if k != 'songmui_3'}, gt, CFG, 2.0)       # điểm không có trong nháp thì không tính
    assert r['n_nhap'] == 49


def test_ti_le_sua_total_by_group_faces_and_skipped():
    gt1, gt2 = pts(1), pts(2)
    iod1 = eval50.iod(gt1, CFG)
    mats = [dict(nguoi='P2', anh='A', nhap=dich(gt1, ten=['songmui_1', 'mattrai_2', 'mattrai_3'], dx=0.05 * iod1), nhan=gt1),            # 3 điểm sửa
            dict(nguoi='P2', anh='B', nhap=gt2, nhan={k: v for k, v in gt2.items() if k != 'moitrong_1'}),                              # 1 xoá
            dict(nguoi='P3', anh='C', nhap=gt2, nhan={k: v for k, v in gt2.items() if k != 'matphai_1'})]                              # thiếu IOD: bỏ
    r = so_sanh.ti_le_sua(mats, CFG, 2.0)
    assert r['n_mat'] == 2 and r['n_diem'] == 100 and r['n_sua'] == 4 and r['n_xoa'] == 1 and r['ti_le'] == pytest.approx(4.0) and r['n_mat_phai_sua'] == 2
    assert r['ti_le_mat'] == pytest.approx(100.0) and r['bo_qua'][0][0] == 'C'
    g = r['nhom']
    assert g['songmui']['n_diem'] == 8 and g['songmui']['n_sua'] == 1 and g['songmui']['ti_le'] == pytest.approx(12.5)
    assert g['mattrai']['n_sua'] == 2 and g['moitrong']['n_sua'] == 1 and g['longmaytrai']['ti_le'] == 0.0
    assert sum(e['n_sua'] for e in g.values()) == 4 and sum(e['n_diem'] for e in g.values()) == 100
    assert so_sanh.ti_le_sua([], CFG)['ti_le'] is None and so_sanh.ti_le_sua([], CFG)['ti_le_mat'] is None


# ---------- (1) NME ----------
def test_tham_chieu_averages_manual_labels_by_point_name_and_counts_people():
    a, b = pts(1), pts(1)
    b = dich(b, dx=2.0, dy=4.0)
    b.pop('songmui_1')
    ref = so_sanh.tham_chieu([dict(nguoi='P1', anh='X', nhan=a), dict(nguoi='P2', anh='X', nhan=b), dict(nguoi='P1', anh='Y', nhan=a), dict(nguoi='P3', anh='Z', nhan=None)], CFG)
    assert set(ref) == {'X', 'Y'} and ref['X']['n_nguoi'] == 2 and ref['Y']['n_nguoi'] == 1
    assert ref['X']['diem']['songmui_2'] == pytest.approx([a['songmui_2'][0] + 1.0, a['songmui_2'][1] + 2.0])         # trung bình hai người
    assert ref['X']['diem']['songmui_1'] == a['songmui_1']                                                            # điểm chỉ một người có thì lấy của người đó
    assert so_sanh.tham_chieu([dict(nguoi='P1', anh='X', nhan=a), dict(nguoi='P1', anh='X', nhan=b)], CFG)['X']['n_nguoi'] == 1       # cùng một người hai nhãn: đếm một người


def test_nme_nhom_matches_eval50_per_face_and_group_means():
    gt = pts(3)
    pred = dich(gt, dx=1.5, dy=-0.5)
    pred = {**pred, **dich({k: gt[k] for k in ('matphai_3',)}, dx=40.0)}                             # một điểm hỏng nặng
    ref = {'A': dict(diem=gt, n_nguoi=2)}
    r = so_sanh.nme_nhom([dict(nguoi='P2', anh='A', diem=pred), dict(nguoi='P2', anh='B', diem=pred)], ref, CFG, bad=10.0)
    s = eval50.face_scores(pred, gt, CFG)
    assert r['tong']['n'] == 1 and r['tong']['tb'] == pytest.approx(s['nme']) and r['tong']['trung_vi'] == pytest.approx(s['nme'])
    assert r['chua_co_dap_an'] == ['B'] and r['khong_cham_duoc'] == [] and r['mat'][0]['n_ref'] == 2
    for g in ('longmaytrai', 'matphai', 'moingoai'):
        ns = [p['name'] for p in CFG['points'] if p['group'] == g]
        assert r['nhom'][g]['tb'] == pytest.approx(np.mean([s['errors'][n] for n in ns])) and r['nhom'][g]['n'] == 1
    assert r['nhom']['matphai']['tb'] > r['nhom']['longmaytrai']['tb']
    assert (r['tong']['n_hong'] == 1) == (s['nme'] >= 10.0)
    assert set(r['nhom']) == {'longmaytrai', 'longmayphai', 'songmui', 'mattrai', 'matphai', 'moingoai', 'moitrong'}


def test_nme_nhom_unscorable_reference_is_counted_not_crashing():
    gt = pts(3)
    bad_ref = {k: v for k, v in gt.items() if k != 'matphai_1'}
    r = so_sanh.nme_nhom([dict(nguoi='P2', anh='A', diem=gt)], {'A': dict(diem=bad_ref, n_nguoi=1)}, CFG, 10.0)
    assert r['tong']['n'] == 0 and r['tong']['tb'] is None and r['khong_cham_duoc'][0][0] == 'A'
    assert so_sanh.tom_tat([], 10.0)['n'] == 0 and so_sanh.tom_tat([3.0, 12.0, None], 10.0) == dict(n=2, tb=7.5, trung_vi=7.5, n_hong=1, ti_le_hong=50.0)


# ---------- (3) thời gian ----------
def hang(nguoi, cond, giays, **kw):
    return [dict(person=nguoi, condition=cond, seconds=s, face_id=f'{nguoi}_{i:02d}', **kw) for i, s in enumerate(giays)]


def hai_nhom(man, ass):
    rows = []
    for i, g in enumerate(man):
        rows += hang(f'P{i + 1}', 'manual', g)
    for i, g in enumerate(ass):
        rows += hang(f'P{i + 4}', 'assisted', g)
    return rows


def test_time_group_summaries_and_percent_faster_by_hand():
    rows = hai_nhom([[10, 10], [20, 20]], [[8, 8], [16, 16]])
    r = so_sanh.thoi_gian(rows, n_boot=200)
    m, a = r['nhom']['manual'], r['nhom']['assisted']
    assert (m['n_nguoi'], m['n_mat'], a['n_nguoi'], a['n_mat']) == (2, 4, 2, 4)
    assert m['trung_vi'] == 15.0 and a['trung_vi'] == 12.0 and m['tb_cong'] == 15.0
    assert m['tb_nhan'] == pytest.approx((10 * 10 * 20 * 20) ** 0.25) and a['tb_nhan'] == pytest.approx((8 * 8 * 16 * 16) ** 0.25)
    assert r['nhanh_hon_pct'] == pytest.approx(20.0) and r['nhanh_hon_trung_vi_pct'] == pytest.approx(20.0)                 # (1 - 11,3137/14,1421) = 20%
    assert m['nguoi']['P1']['tb_nhan'] == pytest.approx(10.0) and a['nguoi']['P5']['tb_nhan'] == pytest.approx(16.0)


def test_one_person_per_group_is_descriptive_only_with_stated_reason():
    r = so_sanh.thoi_gian(hai_nhom([[10, 12, 11]], [[5, 6, 5]]))
    assert r['ket_luan'] == 'chi_mo_ta' and r['ktc90_pct'] is None and r['nhanh_hon_pct'] == pytest.approx(51.6, abs=0.1) and r['n_boot'] == 0
    assert 'chỉ có kết quả mô tả, chưa kết luận được' in r['ly_do'] and 'manual 1 người, assisted 1 người' in r['ly_do']
    r = so_sanh.thoi_gian(hai_nhom([[10, 12], [11, 11]], [[5, 6]]))                                                  # một nhóm đủ, nhóm kia 1 người
    assert r['ket_luan'] == 'chi_mo_ta' and r['nhanh_hon_pct'] is not None and r['ktc90_pct'] is None


def test_missing_a_group_or_no_rows():
    r = so_sanh.thoi_gian(hang('P1', 'manual', [10, 11]))
    assert r['ket_luan'] == 'chua_du_du_lieu' and r['nhanh_hon_pct'] is None and 'assisted' in r['ly_do'] and r['nhom']['assisted']['n_mat'] == 0
    assert so_sanh.thoi_gian([])['ket_luan'] == 'chua_du_du_lieu'
    r = so_sanh.thoi_gian([dict(person='P1', condition='manual', seconds=0), dict(person='P1', condition='khac', seconds=5), dict(person='P1', condition='manual', seconds=None)])
    assert r['nhom']['manual']['n_mat'] == 0                                                                           # giây <= 0 / không rõ nhóm / trống bị bỏ


def test_verdict_rules_dat_khong_dat_chua_ket_luan():
    nhanh = so_sanh.thoi_gian(hai_nhom([[100, 101, 99], [98, 100, 102], [101, 99, 100]], [[50, 51, 49], [48, 50, 52], [51, 49, 50]]))
    assert nhanh['ket_luan'] == 'dat' and nhanh['ktc90_pct'][0] >= 20 and nhanh['nhanh_hon_pct'] == pytest.approx(50.0, abs=1.0) and nhanh['n_boot'] == 2000
    cham = so_sanh.thoi_gian(hai_nhom([[100, 101, 99], [98, 100, 102], [101, 99, 100]], [[99, 101, 100], [100, 98, 102], [101, 100, 99]]))
    assert cham['ket_luan'] == 'khong_dat' and cham['ktc90_pct'][1] < 20 and abs(cham['nhanh_hon_pct']) < 2
    rong = so_sanh.thoi_gian(hai_nhom([[40, 42], [200, 210]], [[30, 32], [190, 195]]))                                 # người rất khác tốc độ: khoảng rộng
    assert rong['ket_luan'] == 'chua_ket_luan' and rong['ktc90_pct'][0] < 20 <= rong['ktc90_pct'][1] + 100
    assert so_sanh.KET_LUAN_VI['chi_mo_ta'].startswith('Chỉ có kết quả mô tả')


def test_bootstrap_is_reproducible_clustered_by_person_and_matches_an_independent_implementation():
    rows = hai_nhom([[10, 12, 9, 11], [20, 22, 19], [15, 14]], [[8, 7, 9], [16, 15, 17, 18], [12, 11]])
    r1 = so_sanh.thoi_gian(rows, n_boot=300)
    r2 = so_sanh.thoi_gian(rows, n_boot=300)
    assert r1['ktc90_pct'] == r2['ktc90_pct'] and r1['n_boot'] == 300 and r1['bo_lan'] == 0
    # cài đặt độc lập: cùng seed 28, cùng thứ tự gọi rng (manual rồi assisted; người theo tên; bốc người rồi bốc mặt từng người đã bốc)
    gom = {c: {} for c in ('manual', 'assisted')}
    for x in rows:
        gom[x['condition']].setdefault(x['person'], []).append(x['seconds'])
    rng = np.random.default_rng(28)
    out = []
    for _ in range(300):
        gm = {}
        for c in ('manual', 'assisted'):
            names = sorted(gom[c])
            logs = {p: np.log(gom[c][p]) for p in names}
            tong, n = 0.0, 0
            for i in rng.integers(0, len(names), len(names)):
                lg = logs[names[i]]
                tong += lg[rng.integers(0, len(lg), len(lg))].sum()
                n += len(lg)
            gm[c] = math.exp(tong / n)
        out.append((1 - gm['assisted'] / gm['manual']) * 100)
    assert r1['ktc90_pct'] == pytest.approx((np.percentile(out, 5), np.percentile(out, 95)))
    # bốc theo cụm: khoảng rộng hơn khi người khác nhau nhiều so với khi mọi người giống nhau
    dong = so_sanh.thoi_gian(hai_nhom([[10] * 6, [10] * 6, [10] * 6], [[5] * 6, [5] * 6, [5] * 6]), n_boot=200)
    assert dong['ktc90_pct'][0] == pytest.approx(50.0) and dong['ktc90_pct'][1] == pytest.approx(50.0)
    kh = so_sanh.thoi_gian(hai_nhom([[10] * 6, [30] * 6, [20] * 6], [[5] * 6, [25] * 6, [15] * 6]), n_boot=200)
    assert kh['ktc90_pct'][1] - kh['ktc90_pct'][0] > 20


def test_flagged_rows_stay_in_main_index_and_get_a_sensitivity_line():
    rows = hai_nhom([[10, 11, 10, 12, 11, 10], [20, 21, 20, 22, 21, 20]], [[8, 9, 8, 9, 8, 9], [16, 17, 16, 17, 16, 17]])
    rows[2]['interrupted'] = 1
    rows[8]['sua_tay'] = 1
    rows[14]['canh_bao'] = 'qua_dem'
    rows[1]['uoc_luong'] = True
    rows.append(dict(person='P1', condition='manual', seconds=300.0, face_id='P1_99'))                              # vượt Q3 + 3·IQR
    base = so_sanh.thoi_gian(hai_nhom([[10, 11, 10, 12, 11, 10], [20, 21, 20, 22, 21, 20]], [[8, 9, 8, 9, 8, 9], [16, 17, 16, 17, 16, 17]]), n_boot=50)
    r = so_sanh.thoi_gian(rows, n_boot=50)
    assert r['nhom']['manual']['n_mat'] == 13 and r['nhom']['manual']['nguoi']['P1']['n_mat'] == 7                    # ngoại lai VẪN nằm trong chỉ số chính
    assert [o['face_id'] for o in r['ngoai_lai']] == ['P1_99'] and r['ngoai_lai'][0]['nguong'] < 300
    why = {d['face_id']: d['ly_do'] for d in r['danh_dau']}
    assert 'gián đoạn' in why['P1_02'] and 'sửa tay' in why['P2_02'] and 'qua_dem' in why['P4_02'] and 'Q3' in why['P1_99'] and 'P1_01' not in why        # ước lượng chỉ đếm riêng
    assert r['n_uoc_luong'] == 1
    d = r['do_nhay']
    assert d['n_bo'] == 4 and d['nhanh_hon_pct'] == pytest.approx(base['nhanh_hon_pct'], abs=3.0) and d['n_nguoi'] == dict(manual=2, assisted=2)
    assert r['nhanh_hon_pct'] != d['nhanh_hon_pct']


def test_sensitivity_without_enough_data_after_dropping_is_none():
    rows = hang('P1', 'manual', [10, 11], interrupted=1) + hang('P2', 'manual', [12], interrupted=1) + hai_nhom([], [[5, 6], [7, 8]])
    r = so_sanh.thoi_gian(rows, n_boot=20)
    assert r['do_nhay']['nhanh_hon_pct'] is None and r['do_nhay']['n_nguoi']['manual'] == 0


def test_n_nho_constant():
    assert so_sanh.n_nho(4) and not so_sanh.n_nho(5)
