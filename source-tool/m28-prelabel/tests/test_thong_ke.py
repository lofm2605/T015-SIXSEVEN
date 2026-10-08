"""Thử tool/thong_ke.py (4 nhóm số liệu, trạng thái trống, tách manual/assisted, xuất CSV + HTML tĩnh) bằng dự án GIẢ. Mọi số là dữ liệu giả."""
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
import flag_eval  # noqa: E402
import thong_ke as tk  # noqa: E402
import thong_ke_html as th  # noqa: E402
from m28core import bang_mat as bm  # noqa: E402
from test_bang_mat import tree_hash  # noqa: E402
from thong_ke_fake import Proj  # noqa: E402

F_FACES = [f'F_{i:03d}' for i in range(1, 9)]
X_FACES = [f'X1_{i:02d}' for i in range(1, 7)]
EXTRA = [('Tdev_001', 'Tdev'), ('Ttest_001', 'Ttest')]


@pytest.fixture
def world(tmp_path):
    """Lượt R1 (F + Tdev + Ttest, nhãn Nhận assisted của P3 qua push.json), lượt RX (khối X, nhãn thí nghiệm manual P5 và assisted P1 qua luot_nhap)."""
    p = Proj(tmp_path, t_flip=0.04)
    for n in F_FACES:
        p.add_face(n, 'yawdd', 'F', pose=int(n.endswith('3')))
    for n in X_FACES:
        p.add_face(n, 'drivface', 'X')
    for n, s in EXTRA:
        p.add_face(n, 'yawdd', s)
    d1 = p.make_run('R1', F_FACES + [n for n, _s in EXTRA])
    dx = p.make_run('RX', X_FACES)
    p.write_triage('R1', 'P2', [(n, 'nhan', '', 5.0 + i) for i, n in enumerate(F_FACES[:6])] + [(F_FACES[6], 'gan_tay', '', 40.0), (F_FACES[7], 'bo', '', 200.0),
                                                                                              ('Tdev_001', 'nhan', '', 6.0), ('Ttest_001', 'nhan', '', 7.0)])
    p.write_triage('R1', 'auto', [(n, 'nhan', '', None) for n in F_FACES])
    p.write_push('R1', 'demo-R1', gan_tay_co_nhap=[f'{F_FACES[6]}.png'])
    lab1 = {f'{n}.png': p.label_pts(d1[n], flip_err=True) for n in F_FACES[:7] + ['Tdev_001', 'Ttest_001']}
    lab1['F_002.png'] = p.label_pts(d1['F_002'], big=True)                                      # một mặt hỏng (lệch cả mặt 30 px)
    p.write_label('raw', 'demo-R1', 'P3', '1410', lab1)
    p.write_label('raw', 'm28-manual', 'P5', '1410', {f'{n}.png': p.label_pts(dx[n], flip_err=True) for n in X_FACES})
    p.write_label('raw', 'm28-assisted', 'P1', '1510', {f'{n}.png': p.label_pts(dx[n], sigma=0.3) for n in X_FACES})
    return dict(p=p, root=p.root, d1=d1, dx=dx)


def stats(w, **kw):
    kw.setdefault('luot_nhap', 'RX')
    st, bang = tk.tinh(w['root'], **kw)
    return st, bang


def test_nme_tong_va_theo_nhom_khop_eval50(world):
    st, bang = stats(world)
    cfg = world['p'].cfg
    cl = st['chat_luong']
    assert cl['trong'] is None and set(cl['theo_dieu_kien']) == {'manual', 'assisted'}
    # mặt Nhận assisted (R1, P3) + assisted thí nghiệm RX (P1): lấy riêng nhãn manual làm kỳ vọng
    man_path = os.path.join(world['root'], 'raw', 'm28-manual_P5_1410.xml')
    gt = eval50.read_labels(man_path, cfg)
    exp, exp_group = [], {g: [] for g in bm.groups_of(cfg)}
    gi = bm.group_idx(cfg)
    for n in X_FACES:
        pred = {nm: [float(x), float(y)] for nm, (x, y) in zip(world['p'].names, world['dx'][n][0])}
        s = eval50.face_scores(pred, gt[n], cfg)
        exp.append(s['nme'])
        for g, ix in gi.items():
            exp_group[g].append(np.mean([s['errors'][world['p'].names[i]] for i in ix]))
    m = cl['theo_dieu_kien']['manual']
    assert m['n'] == 6 and m['nme_tb'] == pytest.approx(np.mean(exp)) and m['nme_trung_vi'] == pytest.approx(np.median(exp))
    assert m['hong_pct'] == pytest.approx(100 * np.mean([v >= eval50.BAD for v in exp]))
    for g in exp_group:
        assert m['nhom'][g] == pytest.approx(np.mean(exp_group[g])), g
    assert cl['tieu_de'] == 'manual' and cl['can_duoi'] is False
    a = cl['theo_dieu_kien']['assisted']
    ass_rows = [float(r['nme']) for r in st['nme_nhap_rows'] if r['condition'] == 'assisted']
    assert a['n'] == 7 + 1 + 6 == len(ass_rows)                                                   # R1: F_001..F_007 + Tdev_001 (Ttest ẩn) và 6 mặt RX do P1 sửa nháp
    assert a['nme_tb'] == pytest.approx(np.mean(ass_rows), abs=1e-3)                              # tách điều kiện: assisted không lẫn vào manual
    assert m['n'] == len([r for r in st['nme_nhap_rows'] if r['condition'] == 'manual']) == 6
    assert a['hong_pct'] > 0                                                                       # F_002 bị lệch 30 px: một mặt hỏng


def test_ttest_an_mac_dinh_va_gom_khi_bat(world):
    st, _ = stats(world)
    assert st['meta']['gom_ttest'] is False and st['meta']['ttest_an'] == 1
    assert sum(1 for r in st['nme_nhap_rows'] if r['face_id'] == 'Ttest_001') == 0
    assert all(r['ten'] != 'Ttest' for r in st['so_luong']['theo_set'])
    st2, _ = stats(world, gom_ttest=True)
    assert any(r['face_id'] == 'Ttest_001' for r in st2['nme_nhap_rows']) and any(r['ten'] == 'Ttest' for r in st2['so_luong']['theo_set'])
    assert 'Ttest đang ẩn' in th.phan_dau(st) and 'GỒM Ttest' in th.phan_dau(st2)


def test_chi_nhan_assisted_thi_tieu_de_ghi_can_duoi(world):
    os.remove(os.path.join(world['root'], 'raw', 'm28-manual_P5_1410.xml'))
    st, _ = stats(world)
    cl = st['chat_luong']
    assert cl['tieu_de'] == 'assisted' and cl['can_duoi'] is True and 'manual' not in cl['theo_dieu_kien']
    html = th.muc_chat_luong(st)
    assert 'cận dưới' in html.lower() and 'CẬN DƯỚI' in html


def test_nme_nhap_csv_cot_dau_trung_eval50_va_so_theo_mat(world, tmp_path):
    st, bang = stats(world)
    cols = st['nme_nhap_cols']
    out = tmp_path / 'ref.csv'
    cap = st['chat_luong']['cap']
    rows = [dict(face_id=eval50.stem(r['anh_cvat']), condition=e['dieu_kien'], **e['nme']) for r, e in cap]
    eval50.write_csv(str(out), [dict(face_id=r['face_id'], condition=r['condition'], nme=r['nme'], nme_eye=r['nme_eye'], nme_p2p=r['nme_p2p'], region=r['vung'],
                                     eye_open_err=r['eye_open_err'], n_missing=r['n_missing']) for r in rows], world['p'].cfg)
    ref_head = out.read_text(encoding='utf-8').splitlines()[0].split(',')
    assert cols[:len(ref_head)] == ref_head and ref_head[:5] == ['face_id', 'condition', 'nme', 'nme_eye', 'nme_p2p']                # trùng tên và thứ tự cột của nme_per_face.csv
    assert cols[len(ref_head):len(ref_head) + 4] == ['luot', 'nguoi_gan', 'loai_mat', 'hong']
    ref_rows = list(csv.DictReader(out.open(encoding='utf-8')))
    mine = {(r['face_id'], r['condition']): r for r in st['nme_nhap_rows']}
    for rr in ref_rows:
        m = mine[(rr['face_id'], rr['condition'])]
        for c in ref_head:
            assert str(m[c]) == rr[c], c                                                              # cùng số, cùng định dạng 4 chữ số


def test_trang_thai_trong_khi_chua_co_nhan_khong_co_so_nao(tmp_path):
    p = Proj(tmp_path)
    for n in ('F_001', 'F_002', 'F_003'):
        p.add_face(n)
    p.make_run('R1', ['F_001', 'F_002', 'F_003'])
    st, _ = tk.tinh(p.root)
    cl = st['chat_luong']
    assert cl['trong'] and 'raw' in cl['trong']['can'] and cl['trong']['ai'] == 'P4' and 'theo_dieu_kien' not in cl
    assert st['toc_do']['trong'] and st['toc_do']['trong']['ai'] == 'P5' and 'timing_P1.csv' in st['toc_do']['trong']['can']
    assert st['giay_ra']['trong'] and 'triage_<Pk>.csv' in st['giay_ra']['trong']['can']
    assert st['co']['thieu_dap_an']['ai'] == 'P4 / P2' and st['co']['co_dap_an'] == {}
    html = th.noi_dung(st)
    assert html.count('Chưa có số') >= 4 and 'AUROC' not in th.muc_chat_luong(st)
    assert not re.search(r'NME trung bình|nhanh hơn gán tay \(1|TB nhân của', html)             # không có ô số nào của mục chưa có dữ liệu
    # chưa có triage: số rà bằng 0 KHÔNG được hiện như một con số
    assert 'Chưa ai rà lượt nào' in html


def test_co_lowconf_ty_le_va_auroc_khop_flag_eval(world):
    st, bang = stats(world)
    co = st['co']
    cfg = world['p'].cfg
    # không đáp án: % điểm bị cờ khớp flags.json
    fl = json.load(open(os.path.join(world['root'], 'runs', 'R1', 'flags', 'flags.json'), encoding='utf-8'))
    flx = json.load(open(os.path.join(world['root'], 'runs', 'RX', 'flags', 'flags.json'), encoding='utf-8'))
    allf = [v for k, v in fl.items() if k != 'Ttest_001'] + list(flx.values())                                       # Ttest ẩn
    kd = co['khong_dap_an']
    assert kd['n_mat'] == len(allf) and kd['n_diem'] == 50 * len(allf)
    assert kd['pct'] == pytest.approx(100 * sum(sum(v) for v in allf) / (50 * len(allf)))
    assert sum(d['n'] for d in kd['phan_bo']) == len(allf)
    gi = bm.group_idx(cfg)
    for g, ix in gi.items():
        assert kd['theo_nhom'][g]['pct'] == pytest.approx(100 * sum(sum(v[i] for i in ix) for v in allf) / (len(ix) * len(allf)))
    # có đáp án (manual: nhãn thí nghiệm X): AUROC khớp flag_eval tính trực tiếp trên các điểm
    a = co['co_dap_an']['manual']
    gt = eval50.read_labels(os.path.join(world['root'], 'raw', 'm28-manual_P5_1410.xml'), cfg)
    pts = []
    for n in X_FACES:
        sc = flag_eval.flip_scores_g({'orig': {nm: list(map(float, xy)) for nm, xy in zip(world['p'].names, world['dx'][n][0])},
                                      'flip': {nm: list(map(float, xy)) for nm, xy in zip(world['p'].names, world['dx'][n][1])}}, cfg)
        pred = {nm: [float(x), float(y)] for nm, (x, y) in zip(world['p'].names, world['dx'][n][0])}
        err, _m, _d = eval50.point_errors(pred, gt[n], cfg)
        pts += [(reg, s, err[nm], n, grp) for (reg, s, grp), nm in zip(sc, world['p'].names) if nm in err]
    ref = flag_eval.analyze(pts, tk.TOL_MAC_DINH, cfg, cfg['t_flip'])
    assert a['auroc'] == pytest.approx(ref['auroc']) and a['n_bad'] == ref['n_bad'] and a['n_points'] == len(pts)
    assert a['by_group']['mattrai']['auroc'] == pytest.approx(ref['by_group']['mattrai']['auroc'])
    assert a['at_t'] == {k: pytest.approx(v) for k, v in ref['at_t'].items()}
    assert a['auroc'] > 0.6                                                                                    # lỗi tỉ lệ với độ nghi sai của điểm số lật
    assert 'assisted' in co['co_dap_an'] and a['low_conf_nhan']['n_nhan'] == 6


def test_co_toan_false_canh_bao_va_n_sai_nho(tmp_path):
    p = Proj(tmp_path, t_flip=None)
    for n in ('F_001', 'F_002'):
        p.add_face(n)
    d = p.make_run('R1', ['F_001', 'F_002'])
    p.write_push('R1', 'demo-R1')
    p.write_label('raw', 'demo-R1', 'P1', '1410', {f'{n}.png': p.label_pts(d[n], sigma=0.2) for n in d})
    st, _ = tk.tinh(p.root)
    assert st['co']['luot_toan_false'] == ['R1'] and st['co']['t_flip'] is None
    a = st['co']['co_dap_an']['assisted']
    assert a['n_sai_nho'] is True and a['at_t'] is None and a['n_faces'] == 2                                  # t_flip null: chỉ có bảng phân vị
    html = th.muc_co(st)
    assert 'mọi cờ low_conf = false' in html and 'n quá nhỏ' in html and 'chưa chốt (null)' in html


def test_so_luong_theo_nguon_dot_set_quyet_dinh_va_nguoi_ra(world):
    st, bang = stats(world)
    sl = st['so_luong']
    byn = {r['ten']: r for r in sl['theo_nguon']}
    assert set(byn) == {'YawDD', 'DrivFace'} and byn['DrivFace']['tong'] == 6 and byn['YawDD']['tong'] == 8 + 1                            # Ttest ẩn
    assert sl['tong_luot_mat'] == 8 + 1 + 6 and sl['mat_duy_nhat'] == sl['tong_luot_mat']
    r1 = next(r for r in sl['theo_luot'] if r['ten'] == 'R1')
    assert (r1['nhan'], r1['gan_tay'], r1['bo'], r1['chua_ra']) == (6 + 1, 1, 1, 0) and r1['tong'] == 9                                   # triage_auto không tính
    rx = next(r for r in sl['theo_luot'] if r['ten'] == 'RX')
    assert rx['chua_ra'] == 6 and rx['tong'] == 6
    assert {r['ten'] for r in sl['theo_set']} == {'F', 'X', 'Tdev'}
    st2, _ = stats(world, nguoi_ra=['P9'])
    assert next(r for r in st2['so_luong']['theo_luot'] if r['ten'] == 'R1')['chua_ra'] == 9
    st3, _ = stats(world, nguoi_ra=['auto'])                                                                                               # chỉ có auto: không phải người rà
    assert st3['meta']['nguoi_ra'] == [] and next(r for r in st3['so_luong']['theo_luot'] if r['ten'] == 'R1')['nhan'] == 7


def test_so_luong_nhieu_luot_cung_mat_hien_ca_hai_don_vi(tmp_path):
    p = Proj(tmp_path)
    p.add_face('F_001')
    p.make_run('R1', ['F_001'])
    p.make_run('R2', ['F_001'])
    st, _ = tk.tinh(p.root)
    sl = st['so_luong']
    assert sl['tong_luot_mat'] == 2 and sl['mat_duy_nhat'] == 1 and sl['khac_don_vi'] is True
    assert 'mặt duy nhất' in th.muc_so_luong(st) and 'Khác số (lượt, mặt)' in th.muc_so_luong(st)


def test_tien_do_ra_soat_ca_kho_nhan_va_bam_gio(world):
    p = world['p']
    from datetime import datetime
    with open(os.path.join(p.run_dir('R1'), 'ca_kho.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        f.write('luot,anh,nguoi,loai,diem,ghi_chu,tao_luc,sua_luc,quyet_dinh_ra\nR1,F_001.png,P2,SWAP,,,2026-10-14T10:00:00+07:00,2026-10-14T10:00:00+07:00,\n'
                'R1,F_002.png,P2,RULE,,,2026-10-14T10:00:00+07:00,2026-10-14T10:00:00+07:00,\n')
    os.makedirs(os.path.join(p.run_dir('R1'), 'review'), exist_ok=True)
    open(os.path.join(p.run_dir('R1'), 'review', 'done.txt'), 'w').write('xong')
    p.write_timing(folder='.')
    st, _ = stats(world)
    td = st['tien_do']
    r1 = next(r for r in td['runs'] if r['luot'] == 'R1')
    assert r1['xong'] and r1['ca_kho'] == {'P2': 2} and r1['task'] == 'demo-R1'
    pp = next(x for x in r1['nguoi'] if x['nguoi'] == 'P2')
    assert (pp['da_ra'], pp['tong'], pp['nhan'], pp['gan_tay'], pp['bo']) == (10, 10, 8, 1, 1) or pp['tong'] == 10
    assert all(x['nguoi'] != 'auto' for r in td['runs'] for x in r['nguoi'])
    assert {i['file'] for i in td['nhan']} == {'raw/demo-R1_P3_1410.xml', 'raw/m28-manual_P5_1410.xml', 'raw/m28-assisted_P1_1510.xml'}
    kv = {(b['nguoi'], b['dieu_kien']): b for b in td['bam_gio']}
    assert kv[('P1', 'manual')]['n'] == 10 and kv[('P1', 'manual')]['ky_vong'] == 10 and kv[('P1', 'manual')]['n_tinh_gio'] == 8 and kv[('P1', 'manual')]['ky_vong_tinh_gio'] == 8
    st0, _ = tk.tinh(p.root)
    assert 'Chỉ hiện' not in th.muc_tien_do(st0) and 'kỳ vọng' in th.muc_tien_do(st0).lower()


def test_toc_do_trong_thong_ke_va_giay_ra(world):
    p = world['p']
    p.write_timing(folder='.')
    st, _ = stats(world)
    td = st['toc_do']
    assert td['ok'] and td['ket_luan'] == 'dat' and 15 < td['nhanh_hon_pct'] < 35 and td['n_nguoi'] == 5
    gr = st['giay_ra']
    # triage P2 ở R1: chỉ mặt có giây; Ttest ẩn (giây 7.0); 200 giây > 120 là ngoại lai đếm riêng, không vào trung vị
    assert gr['tong']['n_ngoai_lai'] == 1 and gr['tong']['tong'] == 9 and gr['tong']['n'] == 8
    assert gr['tong']['trung_vi'] == pytest.approx(np.median([5, 6, 7, 8, 9, 10, 40, 6]))
    assert [x['nguoi'] for x in gr['theo_nguoi']] == ['P2'] and gr['theo_nguoi'][0]['phut_100'] == pytest.approx(gr['tong']['trung_vi'] * 100 / 60)
    assert gr['day_du']['tong'] == pytest.approx(td['gio']['assisted'] + gr['tong']['trung_vi']) and gr['day_du']['manual'] == pytest.approx(td['gio']['manual'])
    html = th.muc_giay_ra(st)
    assert 'không phải' in html and 'thời gian gán điểm' in html and 'ước lượng' in html


def test_toc_do_thieu_cot_hien_loi_ro(world):
    p = world['p']
    open(os.path.join(world['root'], 'timing_P1.csv'), 'w', encoding='utf-8').write('date,person\n2026-10-14,P1\n')
    st, _ = stats(world)
    assert st['toc_do']['loi'] and 'thiếu cột' in st['toc_do']['loi'] and 'seconds' in st['toc_do']['loi']
    assert 'thiếu cột' in th.muc_toc_do(st)


def test_xuat_tinh_html_csv_khong_anh_khong_ma_tai_xe_khong_duong_dan(world, tmp_path):
    p = world['p']
    p.write_timing(folder='.')
    st, bang = stats(world)
    d, files = tk.xuat(world['root'], st, bang=bang)
    assert d.replace(os.sep, '/').endswith(st['meta']['ngay_ts']) and os.path.dirname(d) == os.path.join(world['root'], 'outputs', 'thong_ke')
    html = open(os.path.join(d, 'thong_ke.html'), encoding='utf-8').read()
    assert '<img' not in html and '<script' not in html and 'http://' not in html and 'https://' not in html
    assert world['root'] not in html and str(tmp_path) not in html and '/tmp/' not in html
    assert 'token' not in html.lower()
    subjects = {r['subject'] for r in p.manifest.values()}
    assert not any(s in html for s in subjects) and not re.search(r'\b(yd_|df_)[A-Z0-9]', html)
    for s in ('phi thương mại', 'Lập lúc', 'commit', 'config 50 điểm version 3', 't_flip hiện tại', 'raw/demo-R1_P3_1410.xml', 'YawDD', 'prefers-color-scheme', 'viewport'):
        assert s in html, s
    assert 'nme_nhap.csv' in files and 'thong_ke.html' in files and any(f.startswith('toc_do_') for f in files) and any(f.startswith('chat_luong_') for f in files)
    for f in files:
        if f.endswith('.csv'):
            raw = open(os.path.join(d, f), 'rb').read()
            assert raw.startswith(b'\xef\xbb\xbf'), f                                              # utf-8-sig
            assert b'/tmp' not in raw and not re.search(rb'(yd_|df_)[A-Z0-9]', raw)
    # CSV giữ dấu chấm thập phân, HTML dùng dấu phẩy
    r_i = list(csv.DictReader(open(os.path.join(d, 'toc_do_r_i.csv'), encoding='utf-8-sig')))
    assert '.' in r_i[0]['r_i'] and ',' not in r_i[0]['r_i']
    assert re.search(r'\d,\d', html) and not re.search(r'NME trung bình[^<]*\d\.\d', html)
    # lần xuất thứ hai cùng phút không ghi đè
    d2, _ = tk.xuat(world['root'], st, bang=bang)
    assert d2 != d and os.path.isdir(d)
    # chỉ ghi dưới outputs\thong_ke
    with pytest.raises(ValueError, match='ngoài'):
        tk.xuat(world['root'], st, out_root=os.path.join(os.path.dirname(world['root']), 'ngoai_du_an'), bang=bang)


def test_csv_an_toan_cong_thuc(world):
    st, bang = stats(world)
    cols, rows = tk.bang_csv(st, bang)['tien_do_file_nhan']
    rows = [dict(r, ghi_chu='=cmd()', task='+x') for r in rows]
    raw = tk.csv_bytes(cols, rows).decode('utf-8-sig')
    assert "'=cmd()" in raw and "'+x" in raw


def test_thong_ke_chi_doc_khong_sua_runs_raw_final_data(world):
    world['p'].write_timing(folder='.')
    before = tree_hash(world['root'])
    st, bang = stats(world)
    tk.xuat(world['root'], st, bang=bang)
    assert tree_hash(world['root']) == before
    assert tk.main(['--project', world['root'], '--luot-nhap', 'RX', '--timing', '.']) == 0
    assert tree_hash(world['root']) == before


def test_cli_in_ket_qua_tuong_doi_va_loi(world, capsys):
    assert tk.main(['--project', world['root'], '--luot', 'R1']) == 0
    out = capsys.readouterr().out
    assert 'Đã ghi outputs/thong_ke/' in out and world['root'] not in out
    assert tk.main(['--project', world['root'], '--out', '../ngoai']) == 0                      # CLI cho tự chọn nơi ghi
    shutil_out = os.path.abspath(os.path.join(world['root'], '..', 'ngoai'))
    assert os.path.isdir(shutil_out)
    import shutil
    shutil.rmtree(shutil_out)
    assert tk.main(['--project', os.path.join(world['root'], 'khong_co')]) == 2


def test_html_nhom_dung_mau_group_color_co_ten_nhom_va_vach_muc_tieu(world):
    from m28core import mau_nhom
    st, _ = stats(world)
    html = th.muc_chat_luong(st)
    for g, c in mau_nhom.GROUP_COLOR.items():
        assert c in html and mau_nhom.GROUP_VI[g] in html                                         # màu nhóm luôn đi kèm tên nhóm tiếng Việt
    assert 'ngưỡng mặt hỏng 10% IOD' in html and 'tk-vach' in html
    world['p'].write_timing(folder='.')
    st2, _ = stats(world)
    h2 = th.muc_toc_do(st2)
    assert 'mục tiêu nhanh hơn 20%' in h2 and '✓' in h2 and 'Đạt' in h2
    assert 'pie' not in html.lower() and 'conic-gradient' not in html and 'y2' not in html


def test_html_khong_ma_loi_n_nho_o_cac_o_nho(tmp_path):
    p = Proj(tmp_path)
    for n in ('F_001', 'F_002'):
        p.add_face(n)
    d = p.make_run('R1', ['F_001', 'F_002'])
    p.write_push('R1', 'demo-R1')
    p.write_label('raw', 'demo-R1', 'P1', '1410', {f'{n}.png': p.label_pts(d[n]) for n in d})
    st, _ = tk.tinh(p.root)
    html = th.muc_chat_luong(st)
    assert 'n quá nhỏ' in html                                                                  # n = 2 < 5: không in tỉ lệ mặt hỏng, NME theo yếu tố
    assert all(x['nme_tb'] is None for x in st['chat_luong']['yeu_to']['assisted'])


def test_module_thong_ke_khong_keo_gradio_torch():
    import subprocess
    code = ("import sys\nsys.path.insert(0, %r)\nimport thong_ke, thong_ke_html\nfor m in ('gradio', 'torch', 'cv2', 'mediapipe', 'cvat_sdk', 'pandas', 'PIL'):\n"
            "    assert m not in sys.modules, m\nprint('ok')\n") % os.path.join(HERE, '..', 'tool')
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0 and 'ok' in r.stdout, r.stderr


def test_cli_mac_dinh_dung_thu_muc_hien_tai_co_config(world, monkeypatch, capsys):
    monkeypatch.chdir(world['root'])
    assert bm.mac_dinh_du_an() == world['root']
    assert tk.main(['--luot', 'R1']) == 0                                                       # không cần --project: gốc dự án = thư mục hiện tại
    assert os.path.isdir(os.path.join(world['root'], 'outputs', 'thong_ke'))
    monkeypatch.chdir(os.path.dirname(world['root']))                                           # thư mục không có config: rơi về bản m28-prelabel chứa tool\
    assert os.path.isfile(os.path.join(bm.mac_dinh_du_an(), 'config', 'm28_config.json')) and bm.mac_dinh_du_an() != world['root']


def test_mat_xoa_mem_chi_duoc_dem_khong_vao_so_do(world):
    with open(os.path.join(world['root'], 'runs', 'R1', 'excluded.txt'), 'w', encoding='utf-8') as f:
        f.write('F_001\n')
    st, _ = stats(world)
    assert not any(r['face_id'] == 'F_001' for r in st['nme_nhap_rows'])                       # không vào NME
    r1 = next(r for r in st['so_luong']['theo_luot'] if r['ten'] == 'R1')
    assert r1['xoa_mem'] == 1 and r1['tong'] == 9                                                # vẫn được đếm là "đã xoá mềm"
    assert st['co']['khong_dap_an']['n_mat'] == (9 - 1) + 6                                       # R1 còn 8 (bỏ F_001; Ttest ẩn) + RX 6
    assert st['giay_ra']['tong']['tong'] == 8                                                     # giây rà của mặt xoá mềm cũng không tính


def test_nhan_thi_nghiem_chua_co_luot_nhap_thi_goi_y_chon_luot_chua_nhap(world):
    st, _ = stats(world, luot_nhap='')
    cl = st['chat_luong']
    assert cl['n_khong_nhap'] == 12 and set(cl['theo_dieu_kien']) == {'assisted'}                  # 12 nhãn m28-manual/m28-assisted chưa có nháp liên kết
    html = th.muc_chat_luong(st)
    assert 'Lượt chứa nháp' in html and 'luot_nhap' in html and '12 nhãn chưa ghép với nháp' in html
    st2, _ = stats(world)                                                                          # chọn đúng lượt chứa nháp: gợi ý biến mất
    assert st2['chat_luong']['n_khong_nhap'] == 0 and 'chưa ghép với nháp của máy. Nếu đó là nhãn thí nghiệm' not in th.muc_chat_luong(st2)


def test_it_hon_3_nguoi_thi_trang_khong_ket_luan_va_khong_co_so_tieu_de(world):
    world['p'].write_timing(folder='.', people=('P1', 'P2'))
    st, _ = stats(world)
    td = st['toc_do']
    assert td['ok'] is False and td['trong'] and td['n_nguoi'] == 2 and td['tb_nhan'] is None
    html = th.muc_toc_do(st)
    assert 'Chưa có số' in html and 'Chưa đủ dữ liệu' in html and 'mới có 2 người' in html and 'P5' in html
    assert 'TB nhân của r_i' not in html and 'nhanh hơn gán tay (1' not in html and 'KTC 90%' not in html            # không có số tiêu đề nào
    assert 'r_i = assisted ÷ manual' in html                                                                         # nhưng vẫn cho thấy r_i từng người đã có
    assert 'toc_do_tong' not in tk.bang_csv(st) and 'toc_do_r_i' not in tk.bang_csv(st)                                # không xuất bảng kết luận khi chưa đủ dữ liệu
