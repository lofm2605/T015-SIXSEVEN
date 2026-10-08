"""Thử bộ lọc dữ liệu train/finetune (tool/loc_du_lieu.py) bằng dự án GIẢ: tiêu chí, luật cứng, chia theo người, gói xuất, tất định, chỉ ghi dưới outputs\\train_sets."""
import csv
import hashlib
import json
import os
import sys
import zipfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
sys.path.insert(0, HERE)
import loc_du_lieu as ld  # noqa: E402
from m28core import bang_mat as bm  # noqa: E402
from thong_ke_fake import Proj  # noqa: E402
from test_bang_mat import tree_hash  # noqa: E402

GROUPS = ['longmaytrai', 'longmayphai', 'songmui', 'mattrai', 'matphai', 'moingoai', 'moitrong']
REGIONS = ['brow', 'nose', 'eye', 'lip']
FACES = [('F_001', 'F'), ('F_002', 'F'), ('F_003', 'F'), ('F_004', 'F'), ('F_005', 'F'), ('F_006', 'F'),
         ('X1_01', 'X'), ('X1_02', 'X'), ('G1_01', 'G'), ('Tdev_001', 'Tdev'), ('Tdev_002', 'Tdev'), ('Ttest_001', 'Ttest')]


def cfg_of(**over):
    base = json.loads(json.dumps(ld.MAC_DINH))
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k].update(v)
        else:
            base[k] = v
    return ld.kiem_cau_hinh(base, GROUPS, REGIONS)


@pytest.fixture
def world(tmp_path):
    """12 mặt, mỗi mặt một tài xế riêng; lượt R1 (nháp + cờ t_flip 0,03) có triage P1 và nhãn raw của P3 (push.json demo-R1)."""
    p = Proj(tmp_path, t_flip=0.03)
    for i, (n, s) in enumerate(FACES):
        p.add_face(n, 'yawdd' if i % 3 else 'drivface', s)
    d = p.make_run('R1', [n for n, _s in FACES])
    tri = [(n, 'nhan', '', 6.0 + i) for i, (n, _s) in enumerate(FACES)]
    tri[4] = ('F_005', 'gan_tay', 'DON_CUC', 20.0)
    tri[5] = ('F_006', 'bo', 'MO_NHO', 4.0)
    p.write_triage('R1', 'P1', tri)
    p.write_push('R1', 'demo-R1', gan_tay_co_nhap=['F_005.png'])
    p.write_label('raw', 'demo-R1', 'P3', '1410', {f'{n}.png': p.label_pts(d[n]) for n, _s in FACES})
    return dict(p=p, root=p.root, drafts=d)


def run(w, cfg, **kw):
    return ld.chay_loc(w['root'], cfg, **kw)


def kept(kq):
    return sorted(m['row']['mat'] for m in kq.giu)


def ktrain(kq):
    """Mặt còn lại của phần train (nơi tiêu chí chọn ca khó áp dụng); val/test chỉ qua luật cứng và vệ sinh nhãn."""
    return {m['row']['mat'] for m in kq.giu if m['dg']['phan'] == 'train'}


def why(kq, mat):
    return next(m['ly_do'] for m in kq.mat if m['row']['mat'] == mat)


def test_mac_dinh_loc_va_chia_theo_set_goc(world):
    kq = run(world, cfg_of())
    assert kept(kq) == sorted(n for n, _ in FACES if n != 'F_006')                                   # chỉ F_006 (Bỏ) bị loại
    assert why(kq, 'F_006') == 'bo_anh'
    ph = {m['row']['mat']: m['dg']['phan'] for m in kq.giu}
    assert ph['F_001'] == ph['G1_01'] == ph['X1_01'] == 'train' and ph['Tdev_001'] == 'val' and ph['Ttest_001'] == 'test'
    assert not kq.ro_ri and kq.tong == 12 and sum(kq.thac.values()) + len(kq.giu) == kq.tong


def test_mau_cau_hinh_hop_le_va_dry_run_khong_ghi(world, capsys):
    mau = os.path.join(HERE, '..', 'config', 'loc_mau.json')
    with open(mau, encoding='utf-8') as f:
        raw = json.load(f)
    cfg = ld.kiem_cau_hinh(raw, GROUPS, REGIONS)
    assert cfg['ten'] == 'finetune_v1' and cfg['co']['theo_nhom']['mattrai'] == {'toi_thieu': None, 'toi_da': 8}
    assert set(raw) == set(ld.MAC_DINH)                                                               # mẫu liệt kê đủ mọi khoá cấp một
    before = tree_hash(world['root'], ('runs', 'raw', 'final', 'data', 'config'))
    code = ld.main(['--cau-hinh', mau, '--dry-run', '--project', world['root']])
    out = capsys.readouterr().out
    assert code == 0 and 'Vào: 12' in out and 'Chạy thử (--dry-run)' in out
    assert not os.path.exists(os.path.join(world['root'], 'outputs')) and tree_hash(world['root'], ('runs', 'raw', 'final', 'data', 'config')) == before


@pytest.mark.parametrize('raw,msg', [
    ({'khoa_la': 1}, "khoá lạ 'khoa_la'"),
    ({'co': {'theo_nhom': {'mat_xa': {'toi_da': 1}}}}, "co.theo_nhom"),
    ({'co': {'tong': {'toi_thieu': 9, 'toi_da': 3}}}, 'toi_thieu (9) lớn hơn toi_da (3)'),
    ({'co': {'tong': {'toi_da': 'nhieu'}}}, 'co.tong.toi_da'),
    ({'co': {'nguon': 'tinh_lai'}}, 'co.t_flip'),
    ({'co': {'nguon': 'ngau_nhien'}}, 'co.nguon'),
    ({'nme_nhap': {'toi_thieu': 5, 'toi_da': 1}}, 'nme_nhap'),
    ({'quyet_dinh': ['nhan', 'dung']}, "giá trị lạ 'dung'"),
    ({'nguon_du_lieu': []}, 'nguon_du_lieu'),
    ({'nguon_du_lieu': ['khach_hang']}, "'khach_hang'"),
    ({'ten': '../x'}, 'ten'),
    ({'ten': 'a' * 41}, 'ten'),
    ({'zip': 'co'}, 'zip'),
    ({'manifest': {'pose': 2}}, 'manifest.pose'),
    ({'manifest': {'tu_the': 1}}, 'manifest'),
    ({'chia': {'train': ['F'], 'val': ['F']}}, 'một tập chỉ thuộc một phần'),
    ({'chia': {'train': []}}, 'chia.train'),
    ({'nguoi_ra': ['auto']}, 'triage_auto'),
    ({'nhan': {'so_diem_thieu_toi_da': -1}}, 'không được âm'),
    ({'nhan': {'dieu_kien': ['tuy_y']}}, "'tuy_y'"),
    ([], 'đối tượng'),
])
def test_cau_hinh_sai_bao_loi_ro_khoa(raw, msg):
    with pytest.raises(ld.CauHinhLoi) as e:
        ld.kiem_cau_hinh(raw, GROUPS, REGIONS)
    assert msg in str(e.value)


def test_doc_cau_hinh_file_hong(tmp_path):
    p = tmp_path / 'x.json'
    p.write_text('{khong phai json', encoding='utf-8')
    with pytest.raises(ld.CauHinhLoi, match='JSON'):
        ld.doc_cau_hinh(str(p), GROUPS, REGIONS)
    with pytest.raises(ld.CauHinhLoi, match='Không đọc được'):
        ld.doc_cau_hinh(str(tmp_path / 'khong_co.json'), GROUPS, REGIONS)


def test_nguon_du_lieu_va_set_goc(world):
    nguon = {r['mat']: r['nguon'] for r in bm.dung_bang(world['root']).rows}
    kq = run(world, cfg_of(nguon_du_lieu=['yawdd']))
    assert all(nguon[m] == 'yawdd' for m in kept(kq)) and {m for m in nguon if nguon[m] == 'drivface'} <= {m['row']['mat'] for m in kq.mat if m['ly_do'] == 'nguon'}
    kq = run(world, cfg_of(set_goc=['F', 'Tdev']))
    assert kept(kq) == sorted(n for n, s in FACES if s in ('F', 'Tdev') and n != 'F_006')
    assert why(kq, 'X1_01') == 'set_goc'
    kq = run(world, cfg_of(chia={'train': ['F'], 'val': [], 'test': []}))
    assert why(kq, 'Tdev_001') == 'set_ngoai_chia' and why(kq, 'X1_01') == 'set_ngoai_chia'


def test_quyet_dinh_va_nguoi_ra(world):
    p = world['p']
    p.write_triage('R1', 'P2', [('F_001', 'gan_tay', '', 5.0), ('F_002', 'bo', '', 5.0)])
    only_nhan = run(world, cfg_of(quyet_dinh=['nhan']))
    assert why(only_nhan, 'F_005') == 'quyet_dinh' and why(only_nhan, 'F_001') == ''
    p2 = run(world, cfg_of(nguoi_ra=['P2'], quyet_dinh=['gan_tay']))
    train = [m['row']['mat'] for m in p2.giu if m['dg']['phan'] == 'train']
    assert train == ['F_001']                                                                          # train: chỉ mặt P2 chọn Gán tay; mặt P2 chưa rà bị loại
    assert {m['row']['mat'] for m in p2.giu if m['dg']['phan'] != 'train'} == {'Tdev_001', 'Tdev_002', 'Ttest_001'}     # val/test không bị tiêu chí quyết định
    assert why(p2, 'F_003') == 'quyet_dinh'
    assert why(run(world, cfg_of(quyet_dinh=['nhan', 'gan_tay', 'bo'])), 'F_006') == ''           # liệt kê bo thì train nhận
    kq = run(world, cfg_of(quyet_dinh=['nhan', 'gan_tay', 'bo']))
    assert why(kq, 'F_006') == '' and 'F_006' in kept(kq)


def test_bo_khong_vao_val_test_du_liet_ke(world):
    p = world['p']
    p.write_triage('R1', 'P1', [(n, 'bo' if n == 'Tdev_002' else 'nhan', '', 3.0) for n, _s in FACES])
    kq = run(world, cfg_of(quyet_dinh=['nhan', 'gan_tay', 'bo']))
    assert why(kq, 'Tdev_002') == 'bo_anh'                                                           # Bỏ không bao giờ vào val/test
    assert why(kq, 'F_006') == ''


def test_triage_auto_khong_phai_nguoi_ra(world):
    p = world['p']
    import shutil
    shutil.move(os.path.join(p.run_dir('R1'), 'review', 'triage_P1.csv'), os.path.join(p.run_dir('R1'), 'review', 'triage_auto.csv'))
    kq = run(world, cfg_of())
    assert ktrain(kq) == set() and all(m['ly_do'] == 'quyet_dinh' for m in kq.mat if m['row']['set'] in ('F', 'G', 'X'))   # train: không có người rà -> loại
    assert ktrain(run(world, cfg_of(quyet_dinh=[]))) != set()                                                            # tắt tiêu chí quyết định thì không cần triage


def test_co_tong_theo_nhom_theo_vung_khop_flags_json(world):
    root = world['root']
    with open(os.path.join(root, 'runs', 'R1', 'flags', 'flags.json'), encoding='utf-8') as f:
        fl = json.load(f)
    names = world['p'].names
    cfg0 = world['p'].cfg
    gi = bm.group_idx(cfg0)
    tong = {n: sum(v) for n, v in fl.items()}
    t_mid = sorted(tong.values())[len(tong) // 2]
    kq = run(world, cfg_of(co={'tong': {'toi_da': t_mid}}))
    sets = {n: s for n, s in FACES}
    tr = {m for m in tong if sets[m] in ('F', 'G', 'X')}
    ok = {m for m in tong if tong[m] <= t_mid}
    assert ktrain(kq) == (ok & tr) - {'F_006'}
    assert all(why(kq, m) in ('co_ngoai_khoang', 'bo_anh') for m in tr if m not in ok)
    kq = run(world, cfg_of(co={'tong': {'toi_thieu': t_mid + 1}}))
    assert ktrain(kq) == ({m for m in tong if tong[m] >= t_mid + 1} & tr) - {'F_006'}
    ng = {n: sum(fl[n][i] for i in gi['mattrai']) for n in fl}
    kq = run(world, cfg_of(co={'theo_nhom': {'mattrai': {'toi_da': 3}}}))
    assert ktrain(kq) == ({m for m in ng if ng[m] <= 3} & tr) - {'F_006'}
    kq = run(world, cfg_of(co={'theo_nhom': {'mattrai': {'toi_thieu': 2, 'toi_da': 6}, 'matphai': {'toi_da': 5}}}))
    good = {m for m in fl if 2 <= ng[m] <= 6 and sum(fl[m][i] for i in gi['matphai']) <= 5}
    assert ktrain(kq) == (good & tr) - {'F_006'}
    ri = bm.region_idx(cfg0)
    ev = {n: sum(fl[n][i] for i in ri['eye']) for n in fl}
    kq = run(world, cfg_of(co={'theo_vung': {'eye': {'toi_da': 4}}}))
    assert ktrain(kq) == ({m for m in ev if ev[m] <= 4} & tr) - {'F_006'} and len(names) == 50


def test_co_t_flip_null_canh_bao_va_tinh_lai_khop_steps_flags(world):
    p = world['p']
    p.run_flags('R1', None)                                                                            # chạy khi t_flip = null: mọi cờ false
    cfg = cfg_of(co={'tong': {'toi_thieu': 1}})
    kq = run(world, cfg)
    assert ktrain(kq) == set() and any('mọi cờ = false' in w for w in kq.canh_bao)                          # cảnh báo rõ, không lặng lẽ loại hết
    cfg2 = cfg_of(co={'nguon': 'tinh_lai', 't_flip': 0.05, 'tong': {'toi_thieu': 1}})
    kq2 = run(world, cfg2)
    p.run_flags('R1', 0.05)                                                                            # steps.flags thật với đúng t_flip đó
    with open(os.path.join(world['root'], 'runs', 'R1', 'flags', 'flags.json'), encoding='utf-8') as f:
        fl = json.load(f)
    want = {n for n in fl if sum(fl[n]) >= 1 and n != 'F_006' and dict(FACES)[n] in ('F', 'G', 'X')}
    assert ktrain(kq2) == want and want
    for m in kq2.giu:
        assert m['dg']['co'][0] == sum(fl[m['row']['mat']])                                           # số cờ tính lại = số cờ steps.flags


def test_nme_nhap_min_max_va_mat_khong_do_duoc(world):
    kq = run(world, cfg_of())
    nme = {m['row']['mat']: m['dg']['nhan']['nme']['nme'] for m in kq.mat if m['dg']['nhan']}
    mid = sorted(nme.values())[len(nme) // 2]
    hi = run(world, cfg_of(nme_nhap={'toi_thieu': mid}))
    tr = {n for n, s_ in FACES if s_ in ('F', 'G', 'X')}
    assert ktrain(hi) == ({m for m in nme if nme[m] >= mid} & tr) - {'F_006'}
    lo = run(world, cfg_of(nme_nhap={'toi_da': mid}))
    assert ktrain(lo) == ({m for m in nme if nme[m] <= mid} & tr) - {'F_006'}
    # mặt chỉ có nhãn (không có nháp): "không đo được" -> loại, trừ khi giu_mat_khong_nhap
    p = world['p']
    p.add_face('X9_01', 'yawdd', 'X')
    lab = {'X9_01.png': {n: (float(10 + i), float(20 + i)) for i, n in enumerate(p.names)}}
    for i, n in enumerate(p.names):
        lab['X9_01.png'][n] = (float(p.cfg['points'][i]['tmpl'][0]), float(p.cfg['points'][i]['tmpl'][1]))
    p.write_label('raw', 'm28-manual', 'P5', '1410', lab)
    os.makedirs(os.path.join(world['root'], 'data', 'crops'), exist_ok=True)
    p.png(os.path.join(world['root'], 'data', 'crops', 'X9_01.png'), size=(512, 512))
    base = cfg_of(nme_nhap={'toi_da': 100.0}, quyet_dinh=[])
    k1 = run(world, base)
    assert why(k1, 'X9_01') == 'nme_khong_do_duoc'
    k2 = run(world, cfg_of(nme_nhap={'toi_da': 100.0}, quyet_dinh=[], giu_mat_khong_nhap=True))
    assert why(k2, 'X9_01') == '' and any('giu_mat_khong_nhap' in w for w in k2.canh_bao)


def test_manifest_cac_co_va_chuoi(world):
    p = world['p']
    p.manifest['F_001']['pose'] = '1'
    p.manifest['F_002']['camera'] = 'mirror'
    p.manifest['F_003']['glasses'] = 'sunglasses'
    p.manifest['F_004']['blur'] = '1'
    p.write_manifest()
    kq = run(world, cfg_of(manifest={'pose': 0}))
    assert why(kq, 'F_001') == 'manifest' and why(kq, 'F_002') == ''
    kq = run(world, cfg_of(manifest={'pose': [0, 1], 'blur': 0, 'glasses': ['none']}))
    assert why(kq, 'F_003') == 'manifest' and why(kq, 'F_004') == 'manifest' and why(kq, 'F_001') == ''
    kq = run(world, cfg_of(manifest={'camera': 'mirror'}))
    assert [m['row']['mat'] for m in kq.giu if m['dg']['phan'] == 'train'] == ['F_002']                # chuỗi đơn = danh sách một phần tử; val/test không bị lọc
    assert 'Tdev_001' in kept(kq)


def test_ve_sinh_nhan_thieu_diem_low_conf_lech_nhan_dieu_kien(world):
    p, d = world['p'], world['drafts']
    miss = ('mattrai_3', 'moingoai_10')
    lab = {f'{n}.png': p.label_pts(d[n]) for n, _s in FACES}
    lab['F_001.png'] = p.label_pts(d['F_001'], miss=miss)
    low = {'F_002.png': {'mattrai_1': True, 'mattrai_2': True}}
    # nhãn thứ hai của người khác cho F_003, lệch rất nhiều
    p.write_label('raw', 'demo-R1', 'P3', '1510', lab, low=low)                                         # ngày mới hơn: thay nhãn cũ của P3
    p.write_label('raw', 'demo-R1', 'P4', '1510', {'F_003.png': p.label_pts(d['F_003'], big=True)})
    kq = run(world, cfg_of())
    assert why(kq, 'F_001') == 'thieu_diem'
    assert why(run(world, cfg_of(nhan={'so_diem_thieu_toi_da': 2})), 'F_001') == ''
    assert why(kq, 'F_002') == '' and why(run(world, cfg_of(nhan={'low_conf_trong_nhan_toi_da': 1})), 'F_002') == 'low_conf_nhan'
    r3 = next(m['row'] for m in kq.mat if m['row']['mat'] == 'F_003')
    assert r3['lech_nhan'] and r3['lech_nhan'] > 10
    assert why(run(world, cfg_of(nhan={'lech_nhan_toi_da': 5.0})), 'F_003') == 'lech_nhan'
    assert why(run(world, cfg_of(nhan={'lech_nhan_toi_da': 5.0})), 'F_004') == ''                       # không có nhãn thứ hai: không phạt
    k = run(world, cfg_of(nhan={'loai_mat': ['nhan']}))
    assert why(k, 'F_005') == 'dieu_kien' and why(k, 'F_001') != 'dieu_kien'                           # F_005 là Gán tay có nháp
    k = run(world, cfg_of(nhan={'dieu_kien': ['manual'], 'so_diem_thieu_toi_da': 5}))
    assert why(k, 'F_001') == 'dieu_kien'                                                               # mọi nhãn Nhận là assisted


def test_loc_tap_danh_gia_mac_dinh_chi_ap_len_train(world):
    cfg = dict(co={'tong': {'toi_da': 0}})
    kq = run(world, cfg_of(**cfg))
    val = [m for m in kq.mat if m['dg']['phan'] == 'val']
    assert val and all(not m['ly_do'] for m in val)                                                     # val/test không bị tiêu chí ca khó
    kq2 = run(world, cfg_of(chia={'loc_tap_danh_gia': True}, **cfg))
    assert any(m['ly_do'] == 'co_ngoai_khoang' for m in kq2.mat if m['dg']['phan'] in ('val', 'test'))


def test_luat_cung_khong_tat_duoc(tmp_path):
    p = Proj(tmp_path)
    for n, s in (('F_001', 'F'), ('F_002', 'F'), ('F_003', 'F'), ('F_004', 'F')):
        p.add_face(n, 'yawdd', s)
    d = p.make_run('R1', ['F_001', 'F_002'], inbox=True)                                                # lượt Nạp ảnh: không rõ nguồn
    d2 = p.make_run('R2', ['F_003', 'F_004'])
    p.write_push('R1', 'demo-R1')
    p.write_push('R2', 'demo-R2')
    p.write_label('raw', 'demo-R1', 'P1', '1410', {f'{n}.png': p.label_pts(d[n]) for n in d})
    p.write_label('raw', 'demo-R2', 'P1', '1410', {'F_003.png': p.label_pts(d2['F_003'])})             # F_004 chưa có nhãn
    with open(os.path.join(p.run_dir('R2'), 'excluded.txt'), 'w', encoding='utf-8') as f:
        f.write('F_003\n')
    p.write_triage('R1', 'P1', [('F_001', 'nhan', '', 3.0)])
    p.write_triage('R2', 'P1', [('F_003', 'nhan', '', 3.0), ('F_004', 'nhan', '', 3.0)])
    cfg = cfg_of(quyet_dinh=[], giu_mat_khong_nhap=True, nguon_du_lieu=['yawdd', 'drivface'], set_goc=[], chia={'loc_tap_danh_gia': True})
    kq = ld.chay_loc(p.root, cfg)
    assert kq.giu == []
    assert {m['row']['mat']: m['ly_do'] for m in kq.mat} == {'F_001': 'khong_ro', 'F_002': 'khong_ro', 'F_003': 'xoa_mem', 'F_004': 'khong_co_nhan'}
    assert kq.tung_tieu_chi['khong_ro'] == 2 and kq.tung_tieu_chi['xoa_mem'] == 1 and kq.tung_tieu_chi['khong_co_nhan'] >= 1


def test_thac_nuoc_cong_du_tong_va_chong_lan(world):
    p = world['p']
    p.manifest['F_001']['pose'] = '1'
    p.write_manifest()
    kq = run(world, cfg_of(quyet_dinh=['nhan'], manifest={'pose': 0}))
    assert sum(kq.thac.values()) + len(kq.giu) == kq.tong
    assert kq.tung_tieu_chi['quyet_dinh'] >= kq.thac['quyet_dinh']                                      # chồng lấn >= thác nước
    assert kq.thac['bo_anh'] == 1 and kq.thac['quyet_dinh'] == 1 and kq.thac['manifest'] == 1           # F_006 Bỏ; F_005 Gán tay bị 'quyet_dinh'; F_001 pose
    txt = ld.bang_so_luong_text(kq)
    assert 'Quyết định Bỏ ảnh' in txt and 'Vào: 12' in txt and 'còn lại: ' in txt


def test_trung_mat_giu_ban_tot_hon(tmp_path):
    p = Proj(tmp_path)
    p.add_face('F_001', 'yawdd', 'F')
    d1 = p.make_run('R1', ['F_001'])
    d2 = p.make_run('R2', ['F_001'])
    for r, d, ng in (('R1', d1, '1410'), ('R2', d2, '1510')):
        p.write_push(r, 'demo-' + r, cap_nhat=f'2026-10-{ng[:2]}T10:00:00+07:00')
        p.write_label('raw', 'demo-' + r, 'P1', ng, {'F_001.png': p.label_pts(d['F_001'])})
        p.write_triage(r, 'P1', [('F_001', 'nhan', '', 3.0)])
    kq = ld.chay_loc(p.root, cfg_of())
    assert len(kq.giu) == 1 and kq.giu[0]['row']['luot'] == 'R2' and kq.thac['trung_mat'] == 1          # nhãn mới hơn thắng
    info = ld.ghi_bo(kq, 'bo1')
    with open(os.path.join(info['path'], 'manifest.csv'), encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    assert [r['mat'] for r in rows] == ['F_001'] and rows[0]['luot'] == 'R2'


# ---------- chia theo người, rò rỉ ----------
def test_ro_ri_nguoi_giua_hai_phan_la_loi_va_khong_ghi_gi(world):
    p = world['p']
    p.manifest['Tdev_001']['subject'] = p.manifest['F_001']['subject']                                  # cùng tài xế ở train và val
    p.write_manifest()
    kq = run(world, cfg_of())
    assert kq.ro_ri == {p.manifest['F_001']['subject']: ['train', 'val']}
    with pytest.raises(ld.DuLieuLoi, match='rò rỉ người'):
        ld.ghi_bo(kq, 'rori')
    assert not os.path.exists(os.path.join(world['root'], 'outputs'))                                   # không ghi gì
    assert ld.main(['--cau-hinh', _save(world, cfg_of()), '--ten', 'rori', '--project', world['root']]) == 2
    assert not os.path.exists(os.path.join(world['root'], 'outputs', 'train_sets', 'rori'))
    # người đổi ánh xạ chia: kiểm lại vẫn bắt
    p.manifest['Tdev_001']['subject'] = 'yd_M999'
    p.manifest['X1_01']['subject'] = 'yd_M999'                                                          # X (train) và Tdev (val) cùng người
    p.write_manifest()
    assert list(run(world, cfg_of()).ro_ri) == ['yd_M999']
    assert run(world, cfg_of(chia={'train': ['F', 'X', 'G'], 'val': [], 'test': ['Ttest', 'Tdev']})).ro_ri
    p.manifest['X1_01']['subject'] = 'yd_M998'
    p.write_manifest()
    assert not run(world, cfg_of(chia={'train': ['F', 'X', 'G', 'Tdev'], 'val': [], 'test': ['Ttest']})).ro_ri


def _save(world, cfg, name='cfg.json'):
    path = os.path.join(world['root'], name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f)
    return path


# ---------- gói xuất ----------
def test_goi_xuat_cau_truc_nhan_json_csv_va_anh(world):
    kq = run(world, cfg_of(ten='goi1'))
    info = ld.ghi_bo(kq, 'goi1')
    d = info['path']
    assert info['rel'] == 'outputs/train_sets/goi1' and info['so_mat'] == 11 and info['theo_phan'] == {'train': 8, 'val': 2, 'test': 1}
    assert sorted(os.listdir(d)) == sorted(['manifest.csv', 'nhan.json', 'nhan.csv', 'train.txt', 'val.txt', 'test.txt', 'cau_hinh_loc.json',
                                            'bao_cao_loc.md', 'bao_cao_loc.csv', 'README.md', 'anh'])
    with open(os.path.join(d, 'manifest.csv'), encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    cols = list(rows[0])
    for c in ['id', 'anh', 'split', 'nguon', 'subject', 'set_goc', 'luot', 'mat', 'task', 'file_nhan', 'nguoi_gan', 'dieu_kien', 'loai_mat', 'quyet_dinh',
              'nguoi_ra', 'n_co'] + [f'n_co_{g}' for g in GROUPS] + ['nme_nhap', 'pose', 'expression', 'illumination', 'makeup', 'occlusion', 'blur',
                                                                    'camera', 'glasses', 'state', 'w', 'h']:
        assert c in cols, c
    assert open(os.path.join(d, 'manifest.csv'), 'rb').read(3) == b'\xef\xbb\xbf'                       # utf-8-sig
    r = {x['mat']: x for x in rows}['F_001']
    assert (r['split'], r['luot'], r['task'], r['file_nhan'], r['nguoi_gan'], r['loai_mat'], r['quyet_dinh'], r['nguoi_ra']) == \
        ('train', 'R1', 'demo-R1', 'raw/demo-R1_P3_1410.xml', 'P3', 'nhan', 'nhan', 'P1')
    assert (r['w'], r['h']) == ('32', '32') and r['anh'] == 'anh/F_001.png' and float(r['nme_nhap']) >= 0
    assert {x['mat']: x['loai_mat'] for x in rows}['F_005'] == 'gan_tay_co_nhap'
    nh = json.load(open(os.path.join(d, 'nhan.json'), encoding='utf-8'))
    names = world['p'].names
    assert nh['points'] == names and nh['config_version'] == 3 and nh['iod_points'] == ['mattrai_1', 'matphai_1'] and list(nh['groups']) == GROUPS
    assert len(nh['anh']['F_001']) == 50 and set(nh['anh']) == {x['id'] for x in rows}
    with open(os.path.join(d, 'nhan.csv'), encoding='utf-8-sig', newline='') as f:
        nr = list(csv.DictReader(f))
    assert list(nr[0])[:7] == ['id', 'x_longmaytrai_1', 'y_longmaytrai_1', 'v_longmaytrai_1', 'x_longmaytrai_2', 'y_longmaytrai_2', 'v_longmaytrai_2']
    assert len(nr[0]) == 1 + 150 + 50 and list(nr[0])[-1] == 'low_conf_moitrong_8'
    f1 = next(x for x in nr if x['id'] == 'F_001')
    assert float(f1['x_moingoai_10']) == pytest.approx(nh['anh']['F_001'][names.index('moingoai_10')][0]) and f1['v_moingoai_10'] == '1'
    src = os.path.join(world['root'], 'runs', 'R1', 'crop', 'images', 'F_001.png')
    assert open(os.path.join(d, 'anh', 'F_001.png'), 'rb').read() == open(src, 'rb').read()             # chép nguyên byte, không mã hoá lại
    assert open(os.path.join(d, 'train.txt'), encoding='utf-8').read().split() == sorted(f'anh/{x["mat"]}.png' for x in rows if x['split'] == 'train')
    assert open(os.path.join(d, 'test.txt'), encoding='utf-8').read().split() == ['anh/Ttest_001.png']
    assert json.load(open(os.path.join(d, 'cau_hinh_loc.json'), encoding='utf-8'))['ten'] == 'goi1'
    rep = open(os.path.join(d, 'bao_cao_loc.md'), encoding='utf-8').read()
    assert 'Quyết định Bỏ ảnh' in rep and 'Còn lại' in rep


def test_goi_nhan_thieu_diem_v0_va_low_conf(world):
    p, d = world['p'], world['drafts']
    miss = ('mattrai_3',)
    lab = {f'{n}.png': p.label_pts(d[n]) for n, _s in FACES}
    lab['F_001.png'] = p.label_pts(d['F_001'], miss=miss)
    p.write_label('raw', 'demo-R1', 'P3', '1510', lab, low={'F_001.png': {'mattrai_1': True}})
    kq = run(world, cfg_of(nhan={'so_diem_thieu_toi_da': 1}))
    info = ld.ghi_bo(kq, 'thieu')
    with open(os.path.join(info['path'], 'nhan.csv'), encoding='utf-8-sig', newline='') as f:
        r = next(x for x in csv.DictReader(f) if x['id'] == 'F_001')
    assert (r['x_mattrai_3'], r['y_mattrai_3'], r['v_mattrai_3']) == ('', '', '0') and r['low_conf_mattrai_1'] == '1' and r['low_conf_mattrai_2'] == '0'
    nh = json.load(open(os.path.join(info['path'], 'nhan.json'), encoding='utf-8'))
    assert nh['anh']['F_001'][world['p'].names.index('mattrai_3')] is None


def test_tat_dinh_hai_lan_giong_het_tung_byte(world):
    cfg = cfg_of(co={'tong': {'toi_da': 40}}, nme_nhap={'toi_da': 50.0})
    a = ld.ghi_bo(run(world, cfg), 'lan_a', now=None)
    b = ld.ghi_bo(run(world, cfg), 'lan_b')
    for fn in ('manifest.csv', 'nhan.json', 'nhan.csv', 'train.txt', 'val.txt', 'test.txt', 'bao_cao_loc.md', 'bao_cao_loc.csv'):
        assert open(os.path.join(a['path'], fn), 'rb').read() == open(os.path.join(b['path'], fn), 'rb').read(), fn
    ra, rb = (open(os.path.join(x['path'], 'README.md'), encoding='utf-8').read() for x in (a, b))
    assert 'lan_a' in ra and 'lan_b' in rb


def test_ten_goi_an_toan_ghi_de_va_khong_con_mat(world):
    kq = run(world, cfg_of())
    for bad in ('../x', 'a\\b', 'a/b', '', 'x' * 41, '..', 'a b', 'tên'):
        with pytest.raises(ld.DuLieuLoi, match='Tên bộ'):
            ld.ghi_bo(kq, bad)
    ld.ghi_bo(kq, 'ok1')
    with pytest.raises(ld.DuLieuLoi, match='đã có'):
        ld.ghi_bo(kq, 'ok1')
    marker = os.path.join(world['root'], 'outputs', 'train_sets', 'ok1', 'cu.txt')
    open(marker, 'w').write('x')
    ld.ghi_bo(kq, 'ok1', ghi_de=True)
    assert not os.path.exists(marker) and os.path.exists(os.path.join(world['root'], 'outputs', 'train_sets', 'ok1', 'manifest.csv'))
    leftovers = [x for x in os.listdir(os.path.join(world['root'], 'outputs', 'train_sets')) if x.startswith('.')]
    assert leftovers == []                                                                              # không để thư mục tạm
    empty = run(world, cfg_of(quyet_dinh=['nhan'], nme_nhap={'toi_thieu': 1e9}, chia={'loc_tap_danh_gia': True}))
    assert empty.giu == []
    with pytest.raises(ld.KhongConMat):
        ld.ghi_bo(empty, 'rong')
    assert ld.main(['--cau-hinh', _save(world, cfg_of(nme_nhap={'toi_thieu': 1e9}, chia={'loc_tap_danh_gia': True})), '--project', world['root'], '--ten', 'rong']) == 1


def test_chi_ghi_duoi_outputs_train_sets_va_runs_raw_final_data_khong_doi(world):
    p = world['p']
    p.write_label('final', 'demo-R1', 'P3', '1610', {'F_001.png': p.label_pts(world['drafts']['F_001'])})
    before = tree_hash(world['root'])
    snapshot = {os.path.relpath(os.path.join(dp, f), world['root']) for dp, _d, fs in os.walk(world['root']) for f in fs}
    ld.ghi_bo(run(world, cfg_of()), 'chi_doc', zip_=True)
    assert tree_hash(world['root']) == before
    new = {os.path.relpath(os.path.join(dp, f), world['root']) for dp, _d, fs in os.walk(world['root']) for f in fs} - snapshot
    assert new and all(x.startswith(os.path.join('outputs', 'train_sets') + os.sep) for x in new)
    z = os.path.join(world['root'], 'outputs', 'train_sets', 'chi_doc.zip')
    with zipfile.ZipFile(z) as zf:
        assert 'chi_doc/manifest.csv' in zf.namelist() and 'chi_doc/anh/F_001.png' in zf.namelist()


def test_readme_goi_co_giay_phep_trich_dan_phi_thuong_mai(world):
    info = ld.ghi_bo(run(world, cfg_of()), 'rd')
    t = open(os.path.join(info['path'], 'README.md'), encoding='utf-8').read()
    for s in ('phi thương mại', 'không phát tán', 'free for academic usage', 'Diaz-Chito', 'Applied Soft Computing 45 (2016) 98-107', 'Abtahi',
              'ACM Multimedia Systems', 'Allow Researchers to use picture in their paper', 'Ttest là tập đo một lần', 'he_toa_do', 'config 50 điểm version 3',
              'Apache-2.0', 'Đã kiểm trên chính bộ này bằng cột `subject`'):
        assert s in t, s


def test_manifest_csv_an_toan_cong_thuc(world):
    p = world['p']
    p.manifest['F_001']['camera'] = '=HYPERLINK("x")'
    p.write_manifest()
    info = ld.ghi_bo(run(world, cfg_of()), 'fx')
    with open(os.path.join(info['path'], 'manifest.csv'), encoding='utf-8-sig', newline='') as f:
        r = next(x for x in csv.DictReader(f) if x['mat'] == 'F_001')
    assert r['camera'].startswith("'=")


def test_mat_chi_co_nhan_dung_anh_data_crops_va_giu_khi_cho_phep(world):
    p = world['p']
    p.add_face('X9_01', 'yawdd', 'X')
    lab = {'X9_01.png': {n: (float(q['tmpl'][0]), float(q['tmpl'][1])) for n, q in zip(p.names, p.cfg['points'])}}
    p.write_label('raw', 'm28-manual', 'P5', '1410', lab)
    cfg = cfg_of(quyet_dinh=[], giu_mat_khong_nhap=True)
    kq = run(world, cfg)
    assert why(kq, 'X9_01') == 'anh_thieu'                                                              # chưa có data\crops\X9_01.png
    os.makedirs(os.path.join(world['root'], 'data', 'crops'))
    p.png(os.path.join(world['root'], 'data', 'crops', 'X9_01.png'), size=(512, 512))
    kq = run(world, cfg)
    assert why(kq, 'X9_01') == ''
    info = ld.ghi_bo(kq, 'solo')
    rows = list(csv.DictReader(open(os.path.join(info['path'], 'manifest.csv'), encoding='utf-8-sig', newline='')))
    r = next(x for x in rows if x['mat'] == 'X9_01')
    assert (r['luot'], r['dieu_kien'], r['loai_mat'], r['nme_nhap'], r['w'], r['h'], r['quyet_dinh']) == ('', 'manual', '', '', '512', '512', '')


def test_kem_anh_false_khong_chep_anh(world):
    info = ld.ghi_bo(run(world, cfg_of(kem_anh=False)), 'khong_anh')
    assert not os.path.exists(os.path.join(info['path'], 'anh'))
    rows = list(csv.DictReader(open(os.path.join(info['path'], 'manifest.csv'), encoding='utf-8-sig', newline='')))
    assert rows[0]['anh'] == ''
    assert open(os.path.join(info['path'], 'train.txt'), encoding='utf-8').read().split() == sorted(r['id'] for r in rows if r['split'] == 'train')


def test_cli_ma_thoat_va_help_tieng_viet(world, capsys):
    path = _save(world, cfg_of())
    assert ld.main(['--cau-hinh', path, '--dry-run', '--project', world['root']]) == 0
    assert ld.main(['--cau-hinh', os.path.join(world['root'], 'khong_co.json'), '--project', world['root']]) == 2
    err = capsys.readouterr().err
    assert 'Lỗi:' in err and 'Không đọc được file cấu hình' in err
    assert ld.main(['--cau-hinh', path, '--project', world['root'], '--ten', 'cli1', '--zip']) == 0
    out = capsys.readouterr().out
    assert 'outputs/train_sets/cli1' in out and os.path.exists(os.path.join(world['root'], 'outputs', 'train_sets', 'cli1.zip')) and world['root'] not in out
    with pytest.raises(SystemExit):
        ld.main(['--help'])
    assert 'Lọc dữ liệu' in capsys.readouterr().out


def test_module_khong_keo_gradio_torch():
    import subprocess
    code = ("import sys\nsys.path.insert(0, %r)\nimport loc_du_lieu\nfor m in ('gradio', 'torch', 'cv2', 'mediapipe', 'cvat_sdk', 'pandas'):\n"
            "    assert m not in sys.modules, m\nprint('ok')\n") % os.path.join(HERE, '..', 'tool')
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0 and 'ok' in r.stdout, r.stderr
