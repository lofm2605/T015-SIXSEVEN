"""Thử tool/m28core/bang_mat.py (lớp đọc dùng chung của bộ lọc và Thống kê) bằng dự án GIẢ (tests/thong_ke_fake.py). Không ảnh thật, không mạng."""
import hashlib
import json
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
sys.path.insert(0, HERE)
import eval50  # noqa: E402
from m28core import bang_mat as bm  # noqa: E402
from thong_ke_fake import Proj, simple_project  # noqa: E402


def tree_hash(root, subs=('runs', 'raw', 'final', 'data')):
    h = hashlib.sha256()
    for s in subs:
        for dp, dn, fn in sorted(os.walk(os.path.join(root, s))):
            dn.sort()
            for f in sorted(fn):
                p = os.path.join(dp, f)
                h.update(p.encode())
                with open(p, 'rb') as fh:
                    h.update(fh.read())
    return h.hexdigest()


def by(bang, run, mat):
    return next(r for r in bang.rows if r['luot'] == run and r['mat'] == mat)


@pytest.fixture
def simple(tmp_path):
    return simple_project(tmp_path)


def test_thu_tu_50_diem_theo_config_khong_theo_chu_cai(simple):
    b = bm.dung_bang(simple['proj'].root)
    names = [p['name'] for p in simple['proj'].cfg['points']]
    assert b.names == names and len(names) == 50
    assert names.index('moingoai_10') > names.index('moingoai_9') and sorted(names).index('moingoai_10') < sorted(names).index('moingoai_2')
    r = by(b, 'R1', 'F_001')
    assert len(r['diem_lat']) == 50 and len(r['co_may']) == 50
    e = chon = bm.chon_nhan(r)
    assert len(e['pts']) == 50 and e['pts'][names.index('moingoai_10')] is not None
    # danh sách nhóm, số điểm mỗi nhóm đúng bảy nhóm của config
    assert b.groups == ['longmaytrai', 'longmayphai', 'songmui', 'mattrai', 'matphai', 'moingoai', 'moitrong']
    assert r['n_co'] == sum(r['co_may']) == sum(r['n_co_nhom'].values()) == sum(r['n_co_vung'].values())


def test_manifest_nguon_subject_set_va_co(simple):
    p = simple['proj']
    p.manifest['F_001']['pose'] = '1'
    p.manifest['F_001']['camera'] = 'mirror'
    p.write_manifest()
    b = bm.dung_bang(p.root)
    r = by(b, 'R1', 'F_001')
    assert (r['nguon'], r['set'], r['camera'], r['pose'], r['subject']) == ('yawdd', 'F', 'mirror', 1, p.manifest['F_001']['subject'])
    assert r['yaw'] == 3.5 and r['jaw_open'] == 0.1 and r['luma'] == 120 and r['lap_var'] == 400 and r['trong_manifest']
    assert b.runs['R1']['nguon'] == 'yawdd'


def test_luot_inbox_hoac_khong_manifest_la_khong_ro(tmp_path):
    p = Proj(tmp_path)
    for n in ('F_001', 'F_002'):
        p.add_face(n)
    p.make_run('R1', ['F_001', 'F_002'], inbox=True)                       # lượt Nạp ảnh (có inbox\): có thể là ảnh khách hàng
    p.make_run('R2', ['K_001'])                                             # tên không có trong manifest
    b = bm.dung_bang(p.root)
    assert {r['nguon'] for r in b.rows} == {'khong_ro'}
    assert all(not r['trong_manifest'] for r in b.rows if r['luot'] == 'R2')
    # manifest in-cabin có cột source: lượt trộn hai bộ cho nguồn từng mặt
    q = Proj(tmp_path / 'q')
    q.add_face('F_001', 'yawdd')
    q.add_face('F_002', 'drivface')
    q.make_run('R1', ['F_001', 'F_002'])
    bq = bm.dung_bang(q.root)
    assert (by(bq, 'R1', 'F_001')['nguon'], by(bq, 'R1', 'F_002')['nguon']) == ('yawdd', 'drivface') and bq.runs['R1']['nguon'] == 'yawdd+drivface'


def test_khong_manifest_thi_canh_bao_va_khong_ro(tmp_path):
    p = Proj(tmp_path)
    p.make_run('R1', ['F_001'])
    b = bm.dung_bang(p.root)
    assert by(b, 'R1', 'F_001')['nguon'] == 'khong_ro' and any('manifest' in w for w in b.warnings)


def test_triage_nhieu_nguoi_hoan_tac_giay_trong_va_auto(tmp_path):
    p = Proj(tmp_path)
    for n in ('F_001', 'F_002', 'F_003'):
        p.add_face(n)
    p.make_run('R1', ['F_001', 'F_002', 'F_003'], triage={
        'P1': [('F_001', 'nhan', '', None), ('F_001', 'gan_tay', 'DON_CUC', 12.5), ('F_001', '', '', ''),          # dòng Hoàn tác: quyết định trống
               ('F_001', 'bo', 'MO_NHO', 4.0), ('F_002', 'nhan', '', 8.0)],
        'P2': [('F_001', 'nhan', '', 20.0), ('F_003', 'gan_tay', '', 7.0)],
        'auto': [('F_001', 'nhan', '', None), ('F_002', 'gan_tay', '', None), ('F_003', 'bo', '', None)]})
    b = bm.dung_bang(p.root)
    r = by(b, 'R1', 'F_001')
    assert r['ra']['P1']['quyet_dinh'] == 'bo' and r['ra']['P1']['ly_do'] == 'MO_NHO'                        # dòng sau đè dòng trước
    assert r['ra']['P1']['giay'] == pytest.approx(16.5) and r['ra']['P1']['n_doi'] == 2                         # 12.5 + 4.0; nhan->gan_tay->bo = 2 lần đổi ý
    assert r['ra']['P2']['quyet_dinh'] == 'nhan' and r['ra']['auto']['giay'] is None
    assert bm.quyet_dinh_cuoi(r) == ('bo', 'P1')                                                                # theo tên người tăng dần, auto không tính
    assert bm.quyet_dinh_cuoi(r, ['P2']) == ('nhan', 'P2')
    assert bm.quyet_dinh_cuoi(by(b, 'R1', 'F_002'), ['P2']) == ('', '')
    assert bm.quyet_dinh_cuoi(by(b, 'R1', 'F_003')) == ('gan_tay', 'P2')                                        # chỉ auto nói Bỏ: không phải người rà
    assert bm.giay_ra(r) == [('P1', 16.5), ('P2', 20.0)]


def test_flags_autoqc_no_face_va_xoa_mem(tmp_path):
    p = Proj(tmp_path)
    for n in ('F_001', 'F_002', 'F_003'):
        p.add_face(n)
    rd_faces = ['F_001', 'F_002']
    p.make_run('R1', rd_faces, no_flip=('F_002',))
    os.makedirs(os.path.join(p.run_dir('R1'), 'autoqc'))
    with open(os.path.join(p.run_dir('R1'), 'autoqc', 'autoqc.csv'), 'w', encoding='utf-8', newline='') as f:
        f.write('name,suggestion,n_flags,decision,reason,seconds,problems\nF_001.png,can_xem,3,,,,\nF_002.png,nen_gan_tay,50,,,,guong\n')
    with open(os.path.join(p.run_dir('R1'), 'no_face.csv'), 'w', encoding='utf-8', newline='') as f:
        f.write('name,reason,step\nF_003,khong_thay_mat,mediapipe\n')
    with open(os.path.join(p.run_dir('R1'), 'excluded.txt'), 'w', encoding='utf-8') as f:
        f.write('# xoá mềm\nF_002\n')
    b = bm.dung_bang(p.root)
    r1, r2, r3 = by(b, 'R1', 'F_001'), by(b, 'R1', 'F_002'), by(b, 'R1', 'F_003')
    assert r1['autoqc'] == 'can_xem' and r2['autoqc'] == 'nen_gan_tay' and r2['xoa_mem'] and not r1['xoa_mem']
    assert r2['n_co'] == 50 and r2['diem_lat'] is None                              # không có ảnh lật: steps.flags cho mọi cờ = true
    assert r3['no_face'] == 'khong_thay_mat' and not r3['co_nhap'] and r3['co_may'] is None and r3['n_co'] is None


def test_co_tinh_lai_khop_steps_flags(tmp_path):
    p = Proj(tmp_path, t_flip=None)                                               # chạy khi t_flip = null: mọi cờ false (bẫy đã biết)
    for n in ('F_001', 'F_002', 'F_003'):
        p.add_face(n)
    p.make_run('R1', ['F_001', 'F_002', 'F_003'], no_flip=('F_003',))
    b = bm.dung_bang(p.root)
    assert b.runs['R1']['co_toan_false'] is True
    assert by(b, 'R1', 'F_001')['n_co'] == 0 and by(b, 'R1', 'F_002')['n_co'] == 0 and by(b, 'R1', 'F_003')['n_co'] == 0   # t null thắng cả luật 'không ảnh lật'
    assert any('mọi cờ low_conf đều false' in w for w in b.warnings)
    for t in (0.01, 0.03, 0.08):
        p.run_flags('R1', t)                                                         # steps.flags thật với t_flip khác
        with open(os.path.join(p.run_dir('R1'), 'flags', 'flags.json'), encoding='utf-8') as f:
            real = json.load(f)
        bt = bm.dung_bang(p.root)
        for n in ('F_001', 'F_002', 'F_003'):
            r = by(bt, 'R1', n)
            assert r['co_may'] == real[n]                                            # flags.json đọc đúng
            got = bm.flags_tinh_lai(r['diem_lat'], t, 50)
            assert got == real[n], (t, n)                                            # tính lại từ điểm số lật = cờ steps.flags
            assert bm.co_cua_mat(bt, r, 'tinh_lai', t)[0] == sum(real[n])
    r3 = by(bm.dung_bang(p.root), 'R1', 'F_003')
    assert bm.co_cua_mat(b, r3, 'tinh_lai', 0.05)[0] == 50 and bm.co_cua_mat(b, r3, 'tinh_lai', None)[0] is None   # không ảnh lật = true; t null = không tính được
    assert bm.flags_tinh_lai(None, None, 50) == [False] * 50                          # đúng thứ tự kiểm của steps.flags: t null thắng


def test_canh_bao_cac_co_toan_false(tmp_path):
    p = Proj(tmp_path, t_flip=None)
    p.add_face('F_001')
    p.make_run('R1', ['F_001'])
    b = bm.dung_bang(p.root)
    assert b.runs['R1']['co_toan_false'] is True and any('t_flip = null' in w for w in b.warnings)
    p.run_flags('R1', 0.0001)
    assert bm.dung_bang(p.root).runs['R1']['co_toan_false'] is False


def test_push_json_nhan_raw_moi_nhat_final_uu_tien_va_loai_mat(tmp_path):
    p = Proj(tmp_path)
    faces = [f'F_{i:03d}' for i in range(1, 6)]
    for n in faces:
        p.add_face(n)
    d = p.make_run('R1', faces)
    p.write_push('R1', 'demo-R1', gan_tay_co_nhap=['F_004.png'], manual=['F_005.png'])
    old = p.write_label('raw', 'demo-R1', 'P3', '1210', {f'{n}.png': p.label_pts(d[n]) for n in faces[:3]})
    new = p.write_label('raw', 'demo-R1', 'P3', '1410', {f'{n}.png': p.label_pts(d[n]) for n in faces})
    p.write_label('raw', 'demo-R1', 'P4', '1410', {'F_001.png': p.label_pts(d['F_001'])})
    fin = p.write_label('final', 'demo-R1', 'P3', '1410', {f'{n}.png': p.label_pts(d[n], sigma=0.1) for n in faces})
    b = bm.dung_bang(p.root)
    files = {(i['nguoi'], i['kind']): i['file'] for i in b.labels}
    assert files[('P3', 'final')] == 'final/demo-R1_P3_1410.xml' and ('P3', 'raw') not in files             # final ưu tiên hơn raw, raw cũ không đọc
    assert files[('P4', 'raw')] == 'raw/demo-R1_P4_1410.xml'
    assert os.path.exists(old) and os.path.exists(new) and os.path.exists(fin)
    r1, r4, r5 = by(b, 'R1', 'F_001'), by(b, 'R1', 'F_004'), by(b, 'R1', 'F_005')
    assert len(r1['nhan']) == 2 and {e['nguoi'] for e in r1['nhan']} == {'P3', 'P4'}
    assert bm.chon_nhan(r1)['kind'] == 'final'                                                                  # final > raw
    assert r1['nhan'][0]['loai_mat'] == 'nhan' and r1['nhan'][0]['dieu_kien'] == 'assisted'
    assert (r4['nhan'][0]['loai_mat'], r4['nhan'][0]['dieu_kien']) == ('gan_tay_co_nhap', 'assisted')
    assert (r5['nhan'][0]['loai_mat'], r5['nhan'][0]['dieu_kien']) == ('gan_tay_trong', 'manual')
    assert r1['nhan'][0]['nme']['ok'] and r1['lech_nhan'] is not None and r1['lech_nhan'] >= 0                    # hai nhãn người: độ lệch giữa chúng
    assert by(b, 'R1', 'F_002')['lech_nhan'] is None


def test_chon_nhan_theo_thu_tu_uu_tien_roi_moi_nhat():
    mk = lambda kind, dk, ngay, f: dict(kind=kind, dieu_kien=dk, ngay=ngay, file=f)       # noqa: E731
    r = dict(nhan=[mk('raw', 'assisted', '0111', 'a'), mk('raw', 'manual', '2010', 'b'), mk('raw', 'manual', '1410', 'c')])
    assert bm.chon_nhan(r)['file'] == 'b'                                                      # cùng hạng manual: ngày mới hơn (20/10 sau 14/10)
    assert bm.chon_nhan(r, ('assisted', 'manual'))['file'] == 'a'
    r['nhan'].append(mk('final', 'manual', '0101', 'f'))
    assert bm.chon_nhan(r)['file'] == 'f'
    assert bm.chon_nhan(dict(nhan=[])) is None


def test_task_thi_nghiem_dieu_kien_theo_ten_va_luot_nhap(tmp_path):
    p = Proj(tmp_path)
    faces = [f'F_{i:03d}' for i in range(1, 4)]
    for n in faces:
        p.add_face(n)
    d = p.make_run('RX', faces)
    for task, who in (('m28-manual', 'P1'), ('m28-assisted', 'P2'), ('m28-pilot-assisted', 'P3'), ('m28-gold-1', 'P4'), ('m28-practice', 'P5'),
                      ('m28-check', 'P1'), ('m28-smoke', 'P2'), ('m28-xyz', 'P3')):
        p.write_label('raw', task, who, '1410', {f'{n}.png': p.label_pts(d[n]) for n in faces})
    b = bm.dung_bang(p.root)
    dk = {i['task']: i['dieu_kien'] for i in b.labels}
    assert dk == {'m28-manual': 'manual', 'm28-assisted': 'assisted', 'm28-pilot-assisted': 'assisted', 'm28-gold-1': 'manual', 'm28-practice': 'bo_qua',
                  'm28-check': 'bo_qua', 'm28-smoke': 'bo_qua', 'm28-xyz': 'khong_ro_dieu_kien'}
    assert all('bỏ qua' in i['ghi_chu'] for i in b.labels if i['dieu_kien'] == 'bo_qua')
    # không nêu luot_nhap: nhãn có dòng riêng (luot rỗng) và KHÔNG có cột nháp
    lab_only = [r for r in b.rows if r['luot'] == '']
    assert len(lab_only) == 3 and all(not r['co_nhap'] and all(e['nme'] is None for e in r['nhan']) for r in lab_only)
    assert {e['dieu_kien'] for r in lab_only for e in r['nhan']} == {'manual', 'assisted', 'khong_ro_dieu_kien'}
    # nêu luot_nhap: nhãn ghép vào đúng mặt của lượt và có NME của nháp
    b2 = bm.dung_bang(p.root, luot_nhap='RX')
    assert not [r for r in b2.rows if r['luot'] == '']
    r = by(b2, 'RX', 'F_001')
    assert {e['dieu_kien'] for e in r['nhan']} == {'manual', 'assisted', 'khong_ro_dieu_kien'} and all(e['nme']['ok'] for e in r['nhan'])
    assert bm.dung_bang(p.root, luot_nhap='NOPE').warnings[-1].startswith('luot_nhap')


def test_nhan_nme_khop_eval50_tong_va_theo_nhom(tmp_path):
    info = simple_project(tmp_path)
    p, d = info['proj'], info['drafts']
    b = bm.dung_bang(p.root)
    cfg = p.cfg
    for fn in info['faces'][:-1]:
        r = by(b, 'R1', fn)
        e = r['nhan'][0]
        gt = {n: [float(x), float(y)] for n, (x, y) in zip(p.names, e['pts'])}
        pred = {n: [float(x), float(y)] for n, (x, y) in zip(p.names, d[fn][0])}
        s = eval50.face_scores(pred, gt, cfg)
        assert e['nme']['nme'] == pytest.approx(s['nme']) and e['nme']['nme_eye'] == pytest.approx(s['nme_eye'])
        assert e['nme']['hong'] == (s['nme'] >= eval50.BAD)
        for g, ix in bm.group_idx(cfg).items():                                       # trung bình lỗi từng điểm của nhóm
            v = [s['errors'][p.names[i]] for i in ix if p.names[i] in s['errors']]
            assert e['nme']['nhom'][g] == pytest.approx(sum(v) / len(v))
    # so cả với đường CLI cũ: eval50.read_run_pred + read_labels cho cùng số
    pred_up = eval50.read_run_pred('R1', cfg, os.path.join(p.root, 'runs'))
    gt_up = eval50.read_labels(info['label'], cfg)
    res = eval50.evaluate(pred_up, gt_up, cfg)
    assert {x['face_id']: x['nme'] for x in res['rows']}['F_001'] == pytest.approx(by(b, 'R1', 'F_001')['nhan'][0]['nme']['nme'])


def test_nhan_cu_face50_dem_rieng_khong_sap(tmp_path):
    p = Proj(tmp_path)
    p.add_face('F_001')
    d = p.make_run('R1', ['F_001'])
    p.write_push('R1', 'demo-R1')
    p.write_label('raw', 'demo-R1', 'P1', '1410', {'F_001.png': p.label_pts(d['F_001'])}, old=True)
    b = bm.dung_bang(p.root)
    assert b.labels[0]['n_cu'] == 1 and 'cũ' in b.labels[0]['ghi_chu'] and by(b, 'R1', 'F_001')['nhan'] == []


def test_bang_chi_doc_khong_sua_runs_raw_final_data(tmp_path):
    info = simple_project(tmp_path)
    root = info['proj'].root
    info['proj'].write_label('final', 'demo-R1', 'P2', '1410', {'F_001.png': info['proj'].label_pts(info['drafts']['F_001'])})
    before = tree_hash(root)
    bm.dung_bang(root)
    bm.dung_bang(root, luot_nhap='R1')
    assert tree_hash(root) == before


def test_toa_do_khung_crop_va_auto_khu_hoi(tmp_path):
    pts = [[10.0, 20.0], None, [300.0, 400.0]]
    src, dst = (0.0, 0.0, 1.0), (-12.5, -17.25, 0.9683)
    there = bm.den_khung_cat(pts, src, dst)
    back = bm.den_khung_cat(there, dst, src)
    assert back[1] is None and np.allclose(back[0], pts[0]) and np.allclose(back[2], pts[2])
    assert np.allclose(there[0], [(10.0 + 12.5) * 0.9683, (20.0 + 17.25) * 0.9683])
    # lượt auto: nhãn ở hệ ảnh vào; ghép theo tên ảnh gốc và đổi sang hệ ảnh cắt của lượt bằng left/top/k của meta
    p = Proj(tmp_path)
    p.add_face('F_001')
    d = p.make_run('RA', ['F_001'], mode='auto')
    meta = json.load(open(os.path.join(p.run_dir('RA'), 'crop', 'meta.json')))['F_001']
    crop_pts = p.label_pts(d['F_001'], sigma=0.0)
    up = {n: (x / meta['k'] + meta['left'], y / meta['k'] + meta['top']) for n, (x, y) in crop_pts.items()}   # đúng ngược steps._face_pts
    p.write_push('RA', 'demo-RA')
    p.write_label('raw', 'demo-RA', 'P1', '1410', {'F_001.png': up}, w=640, h=480)
    b = bm.dung_bang(p.root)
    e = by(b, 'RA', 'F_001')['nhan'][0]
    got = {n: pt for n, pt in zip(b.names, e['pts'])}
    assert all(np.allclose(got[n], crop_pts[n], atol=0.02) for n in crop_pts)
    assert e["nme"]["nme"] < 0.05 and by(b, 'RA', 'F_001')['anh_cvat'] == 'F_001.png'


def test_ghep_theo_ten_manifest_khi_anh_cvat_la_ten_anh_goc(tmp_path):
    """Lượt auto có ảnh gốc tên khác (IMG_1.png): nhãn đặt tên theo manifest (F_001) ở hệ ảnh cắt manifest -> ghép theo tên mặt, đổi hệ."""
    p = Proj(tmp_path)
    row = p.add_face('F_001', left='5', top='7', k='0.5')
    d = p.make_run('RA', ['F_001'], mode='auto')
    meta_p = os.path.join(p.run_dir('RA'), 'crop', 'meta.json')
    meta = json.load(open(meta_p))
    meta['F_001']['rel'] = 'IMG_1.png'
    json.dump(meta, open(meta_p, 'w'))
    crop_pts = p.label_pts(d['F_001'], sigma=0.0)
    in_man_frame = {n: ((x / meta['F_001']['k'] + meta['F_001']['left'] - 5) * 0.5, (y / meta['F_001']['k'] + meta['F_001']['top'] - 7) * 0.5)
                    for n, (x, y) in crop_pts.items()}
    p.write_label('raw', 'm28-manual', 'P5', '1410', {'F_001.png': in_man_frame})
    b = bm.dung_bang(p.root, luot_nhap='RA')
    r = by(b, 'RA', 'F_001')
    assert r['anh_cvat'] == 'IMG_1.png' and len(r['nhan']) == 1
    got = dict(zip(b.names, r['nhan'][0]['pts']))
    assert all(np.allclose(got[n], crop_pts[n], atol=0.02) for n in crop_pts) and row['k'] == '0.5'


def test_lan_nhan_khong_ghep_duoc_duoc_ghi_ly_do(tmp_path):
    info = simple_project(tmp_path, labelled=False)
    p, d = info['proj'], info['drafts']
    p.write_push('R1', 'demo-R1')
    p.write_label('raw', 'demo-R1', 'P1', '1410', {'F_001.png': p.label_pts(d['F_001']), 'ZZZ.png': p.label_pts(d['F_001'])})
    b = bm.dung_bang(p.root)
    assert b.khong_ghep == [('raw/demo-R1_P1_1410.xml', 'ZZZ', 'không có mặt nào của lượt R1 có tên ảnh CVAT này')]
    assert b.labels[0]['n_khop'] == 1 and b.labels[0]['n_khong_ghep'] == 1


def test_luot_dung_ten_diem_cu_v2_bi_bo_qua_co_ghi_chu(tmp_path):
    p = Proj(tmp_path)
    p.add_face('F_001')
    p.make_run('R1', ['F_001'])
    path = os.path.join(p.run_dir('R1'), 'map50', 'mp50.json')
    mp = json.load(open(path))
    mp['F_001']['orig'] = {f'p{i:02d}_brow_L': [1, 1] for i in range(50)}
    json.dump(mp, open(path, 'w'))
    b = bm.dung_bang(p.root)
    assert 'R1' in b.luot_bo_qua and 'version 2' in b.luot_bo_qua['R1'] and not [r for r in b.rows if r['luot'] == 'R1']
    assert any('Lượt R1 bỏ qua' in w for w in b.warnings)


def test_chon_lot_va_nguoi_khong_co(tmp_path):
    info = simple_project(tmp_path)
    p = info['proj']
    p.add_face('F_900')
    p.make_run('R2', ['F_900'])
    only = bm.dung_bang(p.root, runs=['R2'])
    assert {r['luot'] for r in only.rows} == {'R2'}
    miss = bm.dung_bang(p.root, runs=['R2', 'KHONGCO'])
    assert any('KHONGCO' in w for w in miss.warnings)
    assert bm.dung_bang(p.root).mat_duy_nhat() == 7 and len(bm.dung_bang(p.root).rows) == 7


def test_thieu_config_bao_loi_tieng_viet(tmp_path):
    with pytest.raises(bm.BangLoi, match='config'):
        bm.dung_bang(str(tmp_path))


def test_rel_khong_lo_duong_dan_tuyet_doi(tmp_path):
    assert bm.rel(str(tmp_path), os.path.join(str(tmp_path), 'raw', 'x.xml')) == 'raw/x.xml'
    assert bm.rel(str(tmp_path), '/etc/passwd') == 'passwd'
    with pytest.raises(bm.BangLoi, match='ngoài'):
        bm.tim_file_nhan(str(tmp_path), ['/etc/passwd'])


def test_module_khong_keo_gradio_torch_cv2():
    import subprocess
    code = ("import sys\nsys.path.insert(0, %r)\nfrom m28core import bang_mat\nfor m in ('gradio', 'torch', 'cv2', 'mediapipe', 'cvat_sdk', 'pandas'):\n"
            "    assert m not in sys.modules, m\nprint('ok')\n") % os.path.join(HERE, '..', 'tool')
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0 and 'ok' in r.stdout, r.stderr
