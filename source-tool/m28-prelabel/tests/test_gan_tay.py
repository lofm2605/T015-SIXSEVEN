"""Nút "Gán tay" đẩy mặt sang CVAT KÈM nháp 50 điểm, mọi điểm low_conf=true (mặt không có nháp vẫn là ảnh trống).

Thử bằng CVAT GIẢ (tests/fake_cvat) và dữ liệu giả: phân loại (phan_loai), ghi XML (steps.build_xml), push (m28core.push) cùng kiểm sau nhập
(cvat_io.check_faces), tương thích push.json cũ, collect, chữ trên trang. Chưa kiểm trên CVAT thật (xem README, mục Rủi ro).
"""
import json
import math
import os
import sys
import xml.etree.ElementTree as ET

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
from m28core import cvat_io, phan_loai, steps  # noqa: E402
from m28core import push as pushmod  # noqa: E402
from test_dot_anh import ALL_DECIDED, make_dot_run, world  # noqa: E402,F401  (fixture world: thư mục tạm có config/pipeline.json)
from test_push import cvat, calls, collect_args, pj, point_names, state  # noqa: E402,F401  (fixture cvat: CVAT giả + config/ tạm)

NAMES = [f'p{i + 1:02d}' for i in range(50)]


def entry(shift=0.0, names=NAMES):
    return dict(orig={n: [10.0 + i + shift, 20.0 + i] for i, n in enumerate(names)}, flip=None)


# ---------- phan_loai ----------
def test_nhap_hop_le_cases():
    ok = entry()
    assert phan_loai.nhap_hop_le(ok) and phan_loai.nhap_hop_le(ok, NAMES)
    assert not phan_loai.nhap_hop_le(None) and not phan_loai.nhap_hop_le(1) and not phan_loai.nhap_hop_le({}) and not phan_loai.nhap_hop_le({'orig': []})
    short = entry()
    del short['orig']['p50']
    assert not phan_loai.nhap_hop_le(short) and not phan_loai.nhap_hop_le(short, NAMES)            # thiếu điểm
    assert phan_loai.nhap_hop_le(short, NAMES[:49])                                                # đòi đủ tên trong point_names
    other = entry(names=[f'q{i}' for i in range(50)])
    assert phan_loai.nhap_hop_le(other) and not phan_loai.nhap_hop_le(other, NAMES)               # khác tên: đủ 50 khoá nhưng sai tên
    for bad in (float('nan'), float('inf'), -math.inf, None, True, 'x'):
        e = entry()
        e['orig']['p07'] = [bad, 1.0]
        assert not phan_loai.nhap_hop_le(e) and not phan_loai.nhap_hop_le(e, NAMES), bad
    for bad in ([1.0], [1, 2, 3], None, 5):
        e = entry()
        e['orig']['p07'] = bad
        assert not phan_loai.nhap_hop_le(e), bad
    e = entry()
    e['orig']['p07'] = [1, 2]                                                                      # số nguyên hữu hạn vẫn hợp lệ
    assert phan_loai.nhap_hop_le(e)


def test_classify_splits_tay_nhap_and_tay_trong():
    bad = entry()
    bad['orig']['p03'] = [float('nan'), 0.0]
    meta = {n: {} for n in ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h')}
    mp50 = {'a': entry(), 'b': entry(), 'c': entry(), 'd': entry(), 'f': bad, 'g': entry()}       # e, h: không có nháp
    tri = dict(a=('nhan', ''), b=('gan_tay', ''), c=('gan_tay', ''), d=('bo', ''), e=('nhan', ''), f=('gan_tay', ''), g=('gan_tay', ''),
               h=('gan_tay', ''))
    pl = phan_loai.classify(tri, meta, mp50, {}, {'c'}, NAMES)
    assert pl['nhan'] == ['a']
    assert pl['tay_nhap'] == ['b', 'g']                                    # theo thứ tự meta, nháp hợp lệ
    assert pl['tay_trong'] == ['e', 'f', 'h']                              # Nhận không nháp (e), nháp NaN (f), không nháp (h)
    assert pl['tay'] == pl['tay_nhap'] + pl['tay_trong']
    assert pl['nhan_khong_nhap'] == ['e']
    assert 'c' not in pl['nhan'] + pl['tay'] and ('c', 'da_xoa') in pl['removed']       # mặt xoá mềm không ở đâu cả
    assert [n for n, _ in pl['rejected']] == ['d']
    pl2 = phan_loai.classify(tri, meta, mp50, {}, {'c'})                   # point_names=None: kiểm đúng 50 khoá, kết quả như trên
    assert (pl2['tay_nhap'], pl2['tay_trong']) == (pl['tay_nhap'], pl['tay_trong'])
    pl3 = phan_loai.classify(tri, meta, {k: 1 for k in mp50}, {}, {'c'})   # mp50 giả (chỉ có tên): không ai có nháp hợp lệ, `tay` vẫn như cũ
    assert pl3['tay_nhap'] == [] and pl3['tay'] == pl3['tay_trong'] == ['b', 'e', 'f', 'g', 'h'] and pl3['nhan'] == ['a']


# ---------- build_xml ----------
def _cfg():
    return dict(points=[dict(name=n) for n in NAMES])


def _meta(auto=True):
    m = {}
    for i, n in enumerate(('n1', 'n2', 't1', 't2', 'x1')):
        m[n] = dict(src=f'/anh/{n}.jpg', rel=f'{n}.jpg', w=640, h=480, k=2.0, left=30.0 + i, top=-5.0)
    return m


def _xml_images(path):
    return {im.get('name'): im for im in ET.parse(path).getroot().findall('image')}


@pytest.mark.parametrize('mode', ['crop', 'auto'])
def test_build_xml_tay_nhap_after_nhan_all_low_conf(tmp_path, mode):
    meta, cfg = _meta(), _cfg()
    mp50 = {n: entry(i) for i, n in enumerate(('n1', 'n2', 't1', 't2'))}
    mp50['t2']['orig']['p01'] = [-500.0, 9999.0]                                  # ngoài ảnh: chế độ auto phải kẹp mép
    fl = {'n1': [i % 3 == 0 for i in range(50)], 'n2': [False] * 50}
    path = str(tmp_path / 'x' / 'p.xml')
    steps.build_xml(mode, ['n1', 'n2'], meta, mp50, fl, cfg, path, tay_nhap=['t1', 't2'])
    ims = _xml_images(path)
    ext = '.png' if mode == 'crop' else '.jpg'
    assert list(ims) == ['n1' + ext, 'n2' + ext, 't1' + ext, 't2' + ext]          # Nhận trước, Gán tay có nháp nối sau; x1 (không nháp) không có
    assert [im.get('id') for im in ims.values()] == ['0', '1', '2', '3']             # id Nhận 0..len-1, Gán tay len(nhan)+i
    for n, im in ims.items():
        pts = im.find('skeleton').findall('points')
        assert [p.get('label') for p in pts] == NAMES                              # đúng 50 điểm theo thứ tự config
        low = [p.find('attribute').text for p in pts]
        if n.startswith('t'):
            assert low == ['true'] * 50                                            # Gán tay có nháp: MỌI điểm low_conf=true
        elif n.startswith('n1'):
            assert low == ['true' if f else 'false' for f in fl['n1']]               # Nhận giữ cờ thật
        else:
            assert low == ['false'] * 50
    if mode == 'crop':
        assert (ims['t1.png'].get('width'), ims['t1.png'].get('height')) == ('512', '512')
        xy = [float(v) for v in ims['t1.png'].find('skeleton').findall('points')[4].get('points').split(',')]
        assert xy == [pytest.approx(10.0 + 4 + 2), pytest.approx(20.0 + 4)]        # nháp t1 = entry(shift 2) giữ nguyên toạ độ ảnh cắt
    else:
        assert (ims['t1.jpg'].get('width'), ims['t1.jpg'].get('height')) == ('640', '480')
        xy = [float(v) for v in ims['t1.jpg'].find('skeleton').findall('points')[4].get('points').split(',')]
        left, top = 30.0 + 2, -5.0                                                  # t1 là meta thứ 3 (i=2)
        assert xy == [pytest.approx((10.0 + 4 + 2) / 2.0 + left), pytest.approx(max((20.0 + 4) / 2.0 + top, 0))]
        corner = [float(v) for v in ims['t2.jpg'].find('skeleton').findall('points')[0].get('points').split(',')]
        assert corner == [0.0, 479.0]                                               # kẹp vào mép ảnh gốc (0..w-1, 0..h-1)


def test_build_xml_default_keeps_old_behaviour_and_skips_invalid_draft(tmp_path):
    meta, cfg = _meta(), _cfg()
    bad = entry()
    bad['orig']['p05'] = [float('nan'), 1.0]
    mp50 = {'n1': entry(), 't1': entry(), 't2': bad}
    fl = {'n1': [False] * 50}
    p1 = str(tmp_path / 'a.xml')
    steps.build_xml('auto', ['n1'], meta, mp50, fl, _cfg(), p1)                    # không truyền tay_nhap: như cũ, chỉ Nhận
    assert list(_xml_images(p1)) == ['n1.jpg']
    pl = phan_loai.classify(dict(n1=('nhan', ''), t1=('gan_tay', ''), t2=('gan_tay', '')), meta, mp50, {}, frozenset(), NAMES)
    p2 = str(tmp_path / 'b.xml')
    steps.build_xml('auto', pl['nhan'], meta, mp50, fl, cfg, p2, pl['tay_nhap'])
    assert list(_xml_images(p2)) == ['n1.jpg', 't1.jpg']                           # t2 (nháp NaN) là ảnh trống: không có trong XML
    assert 'nan' not in open(p2, encoding='utf-8').read().lower()


# ---------- push với CVAT giả ----------
def make_run3(run='Khoi', n_nhan=19, n_tay_nhap=2, n_trong=1):
    """runs/<run>: ảnh giả F_ (Nhận), T_ (Gán tay có nháp), G_ (ảnh trống); XML = Nhận (cờ k%7==0) rồi Gán tay có nháp (mọi cờ true)."""
    rd = os.path.join('runs', run)
    os.makedirs(os.path.join(rd, 'imgs'), exist_ok=True)

    def mk(prefix, n):
        ps = [os.path.join(rd, 'imgs', f'{prefix}_{i:03d}.png') for i in range(1, n + 1)]
        for p in ps:
            open(p, 'wb').write(b'x')
        return ps

    nhan, t_nhap, t_trong = mk('F', n_nhan), mk('T', n_tay_nhap), mk('G', n_trong)
    names = point_names()
    parts = ['<?xml version="1.0" encoding="utf-8"?>', '<annotations>', '  <version>1.1</version>']
    for i, p in enumerate(nhan + t_nhap):
        low = [k % 7 == 0 for k in range(50)] if p in nhan else [True] * 50
        parts.append(steps.image_xml(i, os.path.basename(p), names, [(i + k, k) for k in range(50)], low, 512, 512))
    parts.append('</annotations>')
    xml = os.path.join(rd, 'xml', 'prelabel.xml')
    os.makedirs(os.path.dirname(xml), exist_ok=True)
    open(xml, 'w', encoding='utf-8').write('\n'.join(parts))
    return dict(rd=rd, nhan=nhan, tay=t_nhap + t_trong, tay_nhap=t_nhap, tay_trong=t_trong, xml=xml)


def do_push(w, name='demo-Khoi', **kw):
    return pushmod.push(w['rd'], name, w['nhan'], w['tay'], w['xml'], **kw)


def task_ann(cvat_mod):
    return state(cvat_mod)['tasks'][0]['annotations']['by_name']


def test_push_19_nhan_2_tay_nhap_1_anh_trong(cvat):
    w = make_run3()
    do_push(w)
    dp = calls(cvat, 'tasks.create_from_data')[0]['kwargs']['data_params']
    assert [len(g) for g in dp['job_file_mapping']] == [8, 8, 3, 3]
    tay_names = [os.path.basename(p) for p in w['tay']]
    assert tay_names == ['T_001.png', 'T_002.png', 'G_001.png']
    assert dp['job_file_mapping'][-1] == tay_names                                 # job cuối: có nháp trước, ảnh trống sau
    st = pj(w)
    assert [(j['kind'], j['n']) for j in st['jobs']] == [('nhan', 8), ('nhan', 8), ('nhan', 3), ('gan_tay', 3)]
    assert st['phien_ban'] == 2 and st['trang_thai'] == 'xong'
    assert st['so_anh'] == dict(nhan=19, gan_tay=3, gan_tay_co_nhap=2, gan_tay_trong=1)
    assert st['gan_tay_co_nhap'] == ['T_001.png', 'T_002.png']
    assert st['check']['ok'] and st['check']['n_tay_nhap'] == 2 and st['check']['n_tay_nhap_day_du'] == 2 and st['check']['tay_nhap_thieu'] == []
    assert len(calls(cvat, 'Task.import_annotations')) == 1
    ann = task_ann(cvat)
    for t in ('T_001.png', 'T_002.png'):
        (sk,) = ann[t]
        assert sk['label'] == 'face50' and [p['label'] for p in sk['points']] == point_names()
        assert [p['low_conf'] for p in sk['points']] == ['true'] * 50                # CVAT giả: 50 điểm toàn true
    assert 'G_001.png' not in ann                                                     # ảnh trống: không có nhãn
    assert len(ann) == 21
    (sk,) = ann['F_001.png']
    assert [p['low_conf'] for p in sk['points']] == ['true' if k % 7 == 0 else 'false' for k in range(50)]   # Nhận giữ cờ thật


def test_push_only_tay_nhap_imports_exactly_once(cvat):
    w = make_run3(n_nhan=0, n_tay_nhap=3, n_trong=0)
    do_push(w)
    assert len(calls(cvat, 'Task.import_annotations')) == 1
    st = pj(w)
    assert st['trang_thai'] == 'xong' and [j['kind'] for j in st['jobs']] == ['gan_tay'] and st['check']['ok']
    assert sorted(task_ann(cvat)) == ['T_001.png', 'T_002.png', 'T_003.png']
    with pytest.raises(SystemExit, match='đã đẩy'):
        do_push(w)
    assert len(calls(cvat, 'Task.import_annotations')) == 1


def test_push_only_tay_trong_does_not_import(cvat):
    w = make_run3(n_nhan=0, n_tay_nhap=0, n_trong=3)
    do_push(w)
    assert calls(cvat, 'Task.import_annotations') == []
    st = pj(w)
    assert st['trang_thai'] == 'xong' and st['so_anh']['gan_tay_trong'] == 3 and st['gan_tay_co_nhap'] == []


def test_check_faces_flags_bad_tay_nhap_and_non_empty_blank():
    def sk(low, drop=0):
        pts = {n: dict(x=1.0, y=2.0, occluded='0', outside='0', low_conf=low) for n in NAMES[drop:]}
        return dict(width='512', height='512', skeletons=[dict(label='face50', points=pts)], n_shapes=1)

    blank = dict(width='512', height='512', skeletons=[], n_shapes=0)
    ann = dict(F=sk('false'), T=sk('true'), G=blank)
    res = cvat_io.check_faces(ann, ['F'], ['T', 'G'], NAMES, ['T'])
    assert res['ok'] and res['n_tay_nhap'] == 1 and res['n_tay_nhap_day_du'] == 1 and res['tay_nhap_thieu'] == [] and res['gan_tay_co_nhan'] == []
    one_false = sk('true')
    one_false['skeletons'][0]['points'][NAMES[7]]['low_conf'] = 'false'
    res = cvat_io.check_faces(dict(ann, T=one_false), ['F'], ['T', 'G'], NAMES, ['T'])
    assert not res['ok'] and res['tay_nhap_thieu'] == ['T'] and res['n_tay_nhap_day_du'] == 0
    res = cvat_io.check_faces(dict(ann, T=sk('true', drop=1)), ['F'], ['T', 'G'], NAMES, ['T'])
    assert not res['ok'] and res['tay_nhap_thieu'] == ['T']                          # thiếu điểm
    res = cvat_io.check_faces(dict(ann, T=blank), ['F'], ['T', 'G'], NAMES, ['T'])
    assert not res['ok'] and res['tay_nhap_thieu'] == ['T']                          # có nháp mà CVAT không có skeleton
    res = cvat_io.check_faces(dict(ann, G=sk('true')), ['F'], ['T', 'G'], NAMES, ['T'])
    assert not res['ok'] and res['gan_tay_co_nhan'] == ['G']                          # ảnh trống lại có shape
    res = cvat_io.check_faces({k: v for k, v in ann.items() if k != 'T'}, ['F'], ['T', 'G'], NAMES, ['T'])
    assert not res['ok'] and res['thieu_anh'] == ['T']
    res = cvat_io.check_faces(dict(ann, T=sk('true')), ['F'], ['T', 'G'], NAMES)       # không khai want_tay_nhap: T coi là ảnh trống (luật cũ)
    assert not res['ok'] and res['gan_tay_co_nhan'] == ['T']


def test_push_check_fails_when_tay_nhap_loses_a_point(cvat, monkeypatch):
    monkeypatch.setenv('M28_FAKE_CVAT_CONTROL', json.dumps({'drop_point': True}))     # xuất thiếu một điểm ở skeleton đầu tiên
    w = make_run3(n_nhan=0, n_tay_nhap=2, n_trong=1)
    with pytest.raises(SystemExit, match='KHÔNG đạt') as e:
        do_push(w)
    assert 'Gán tay có nháp' in str(e.value) and '1/2' in str(e.value)
    st = pj(w)
    assert st['trang_thai'] == 'da_nhap' and not st['check']['ok'] and st['check']['tay_nhap_thieu'] == ['T_001.png']


def test_push_stops_before_connecting_when_xml_has_foreign_image(cvat):
    w = make_run3(n_nhan=2, n_tay_nhap=1, n_trong=1)
    names = point_names()
    extra = steps.image_xml(9, 'LA.png', names, [(k, k) for k in range(50)], [False] * 50, 512, 512)
    txt = open(w['xml'], encoding='utf-8').read().replace('</annotations>', extra + '\n</annotations>')
    open(w['xml'], 'w', encoding='utf-8').write(txt)
    with pytest.raises(SystemExit, match='LA.png'):
        do_push(w)
    assert calls(cvat) == [] and not os.path.exists(os.path.join(w['rd'], 'push.json'))
    w2 = make_run3('Nam', n_nhan=2, n_tay_nhap=1, n_trong=0)                          # XML thiếu một mặt Nhận
    txt = open(w2['xml'], encoding='utf-8').read()
    i = txt.index('<image id="1"')
    j = txt.index('</image>', i) + len('</image>')
    open(w2['xml'], 'w', encoding='utf-8').write(txt[:i] + txt[j:])
    with pytest.raises(SystemExit, match='không có trong XML'):
        do_push(w2, 'demo-Nam')
    assert calls(cvat) == []


def test_push_without_xml_and_only_tay_means_all_blank(cvat):
    w = make_run3(n_nhan=0, n_tay_nhap=0, n_trong=2)
    os.remove(w['xml'])                                                               # người gọi cũ: không có XML
    do_push(w)
    assert pj(w)['gan_tay_co_nhap'] == [] and calls(cvat, 'Task.import_annotations') == []


# ---------- tương thích push.json cũ, manual_list cũ ----------
def test_legacy_resume_imports_only_nhan_and_checks_by_old_rule(cvat, capsys):
    w = make_run3(n_nhan=3, n_tay_nhap=2, n_trong=1)
    do_push(w)
    st = pj(w)
    st.update(trang_thai='da_tao', phien_ban=1)                                       # giả: lượt đẩy bằng bản cũ, chết trước khi nhập
    for k in ('gan_tay_co_nhap', 'check'):
        st.pop(k, None)
    st['so_anh'] = dict(nhan=3, gan_tay=3)
    json.dump(st, open(os.path.join(w['rd'], 'push.json'), 'w'))
    s = state(cvat)
    s['tasks'][0]['annotations'] = None                                               # task chưa có nhãn
    cvat.save(s)
    n_imp = len(calls(cvat, 'Task.import_annotations'))
    capsys.readouterr()
    do_push(w, resume=True)
    out = capsys.readouterr().out
    assert 'lượt đẩy bằng bản cũ' in out and 'Gán tay giữ ảnh trống' in out
    used = calls(cvat, 'Task.import_annotations')[n_imp:][0]['args'][1]
    assert used.endswith('prelabel_cvat.xml')
    assert sorted(im.get('name') for im in ET.parse(used).getroot().iter('image')) == ['F_001.png', 'F_002.png', 'F_003.png']
    assert sorted(task_ann(cvat)) == ['F_001.png', 'F_002.png', 'F_003.png']          # Gán tay không có nhãn như bản cũ
    assert len(ET.parse(w['xml']).getroot().findall('image')) == 5                    # prelabel.xml gốc không bị sửa
    st = pj(w)
    assert st['trang_thai'] == 'xong' and st['check']['ok'] and st['phien_ban'] == 1 and 'n_tay_nhap' in st['check']
    assert st['check']['n_tay_nhap'] == 0


def test_resume_version2_with_different_tay_nhap_set_stops(cvat):
    w = make_run3(n_nhan=3, n_tay_nhap=2, n_trong=1)
    do_push(w)
    st = pj(w)
    st.update(trang_thai='da_tao', gan_tay_co_nhap=['T_001.png'])                     # push.json nói 1 mặt, XML hiện tại có 2
    json.dump(st, open(os.path.join(w['rd'], 'push.json'), 'w'))
    n = len(calls(cvat, 'Task.import_annotations'))
    with pytest.raises(SystemExit, match='--cleanup'):
        do_push(w, resume=True)
    assert len(calls(cvat, 'Task.import_annotations')) == n and pj(w)['trang_thai'] == 'da_tao'


def test_resume_version2_same_set_imports_with_tay_nhap(cvat):
    w = make_run3(n_nhan=3, n_tay_nhap=2, n_trong=1)
    do_push(w)
    st = pj(w)
    st['trang_thai'] = 'da_tao'
    json.dump(st, open(os.path.join(w['rd'], 'push.json'), 'w'))
    s = state(cvat)
    s['tasks'][0]['annotations'] = None
    cvat.save(s)
    do_push(w, resume=True)
    assert len(task_ann(cvat)) == 5 and pj(w)['check']['ok'] and pj(w)['check']['n_tay_nhap_day_du'] == 2


def test_read_manual_list_new_and_old_format(tmp_path):
    p = tmp_path / 'm.txt'
    p.write_text('a.png\tco_nhap\nb.png\tanh_trong', encoding='utf-8')
    assert steps.read_manual_list(str(p)) == [('a.png', 'co_nhap'), ('b.png', 'anh_trong')]
    p.write_text('x.png\ny.png\n\n', encoding='utf-8')                                 # định dạng cũ: mỗi dòng một tên, bản cũ luôn đẩy ảnh trống
    assert steps.read_manual_list(str(p)) == [('x.png', 'anh_trong'), ('y.png', 'anh_trong')]
    p.write_text('z.png\tla\n', encoding='utf-8')
    assert steps.read_manual_list(str(p)) == [('z.png', 'anh_trong')]
    p.write_text('', encoding='utf-8')
    assert steps.read_manual_list(str(p)) == []


# ---------- collect ----------
@pytest.fixture
def pushed3(cvat):
    json.dump(json.load(open(os.path.join(HERE, '..', 'config', 'm28_config.json'), encoding='utf-8')), open('config/m28_config.json', 'w'))
    w = make_run3(n_nhan=3, n_tay_nhap=2, n_trong=1)
    do_push(w)
    return w


def test_collect_demo_task_reports_gan_tay_split(cvat, pushed3):
    from m28core import collect
    assert collect.collect(collect_args()) is True
    rep = open('outputs/collect_demo-Khoi.md', encoding='utf-8').read()
    assert 'Gán tay: 2 có nháp, 1 ảnh trống' in rep
    assert 'low_conf đang bật: 24 ở mặt Nhận · 100 ở mặt Gán tay có nháp' in rep and 'người gán chưa tắt' in rep
    assert 'điểm low_conf đang bật: 124' in rep                                       # dòng cũ vẫn có và là tổng
    assert 'mặt đủ 50 điểm: 5' in rep


def test_collect_demo_task_with_old_push_json_or_m28_task_unchanged(cvat, pushed3):
    from m28core import collect
    st = pj(pushed3)
    st['phien_ban'] = 1
    json.dump(st, open(os.path.join(pushed3['rd'], 'push.json'), 'w'))
    collect.collect(collect_args())
    rep = open('outputs/collect_demo-Khoi.md', encoding='utf-8').read()
    assert 'Gán tay:' not in rep and 'ở mặt Nhận' not in rep and 'điểm low_conf đang bật: 124' in rep
    os.makedirs('raw', exist_ok=True)
    open('raw/m28-manual_P1_1010.xml', 'w').write('<annotations><image id="0" name="a.png" width="512" height="512"></image></annotations>')
    n = len(calls(cvat))
    collect.collect(collect_args(task=['m28-manual']))
    assert len(calls(cvat)) == n                                                      # task thí nghiệm: không gọi CVAT
    assert 'Gán tay:' not in open('outputs/collect_m28-manual.md', encoding='utf-8').read()


def test_collect_push_info_picks_matching_task_version_2_only(tmp_path):
    from m28core import collect
    runs = tmp_path / 'runs'
    for run, ps in (('A', dict(task='demo-A', phien_ban=2, gan_tay_co_nhap=['a.png'], so_anh=dict(gan_tay=3), cap_nhat='2026-10-06T10:00:00')),
                    ('B', dict(task='demo-B', phien_ban=1)), ('C', dict(task='demo-C', phien_ban=2, gan_tay_co_nhap=[]))):
        (runs / run).mkdir(parents=True)
        json.dump(ps, open(runs / run / 'push.json', 'w'))
    (runs / 'D').mkdir()
    (runs / 'D' / 'push.json').write_text('{hỏng', encoding='utf-8')
    assert collect.push_info('demo-A', str(runs)) == dict(run='A', tay_nhap=['a.png'], n_tay_nhap=1, n_tay_trong=2)
    assert collect.push_info('demo-B', str(runs)) is None and collect.push_info('m28-manual', str(runs)) is None
    assert collect.push_info('demo-C', str(runs))['n_tay_trong'] == 0


# ---------- chữ trên trang ----------
def _model(plan_over=None):
    plan = dict(nhan=7, tay=5, tay_nhap=3, tay_trong=2, bo=1, xoa=0, lost=0, nhan_khong_nhap=1, jobs=2, remaining=0, missing=[], via_images=0, loi_triage=None)
    plan.update(plan_over or {})
    return dict(kind='button', enabled=True, reason='', task='demo-Khoi', plan=plan, env=dict(ok=True, url='http://localhost:8080', org=None),
                push=None, pipe=dict(project='m28', prefix='demo-', job_size=8), run='Khoi', remaining=0, images_dir=None)


def test_confirm_and_panel_html_show_split():
    import day_cvat
    html_ = day_cvat.confirm_html(_model())
    assert 'Mặt Nhận (có nháp 50 điểm, cờ của máy)' in html_ and 'Mặt Gán tay (job riêng cuối task)' in html_ and 'Mặt Bỏ' in html_ and 'Số job dự kiến' in html_
    assert '<b>5</b> (3 có nháp — mọi điểm low_conf, kiểm kỹ từng điểm · 2 ảnh trống)' in html_
    assert 'ảnh trống' in html_ and 'không có nháp: tự đưa sang Gán tay' in html_
    import re
    cell = re.search(r'<th>Mặt Gán tay[^<]*</th><td>(.*?)</td>', html_).group(1)
    assert int(re.sub(r'<[^>]+>', '', cell).split()[0]) == 5                       # e2e đọc int(v.split()[0]) trên text của ô
    pn = day_cvat.panel_html(_model())
    assert 'Gán tay (3 có nháp, 2 ảnh trống)' in pn


def test_result_html_new_and_old_push_json():
    import day_cvat
    new = dict(trang_thai='xong', task='demo-Khoi', task_id=4, task_url='http://localhost:8080/tasks/4', phien_ban=2,
               jobs=[dict(kind='nhan'), dict(kind='gan_tay')], so_anh=dict(nhan=7, gan_tay=5, gan_tay_co_nhap=3, gan_tay_trong=2),
               check=dict(ok=True, n_nhan=7, n_day_du=7, n_tay_nhap=3, n_tay_nhap_day_du=3, tay_nhap_thieu=[]))
    h = day_cvat.result_html(new, 'Khoi')
    assert 'Gán tay có nháp: <b>3/3</b>' in h and '3 có nháp · 2 ảnh trống' in h
    old = dict(trang_thai='xong', task='demo-Khoi', task_id=4, task_url='http://localhost:8080/tasks/4', jobs=[dict(kind='nhan'), dict(kind='gan_tay')],
               so_anh=dict(nhan=7, gan_tay=2), check=dict(ok=True, n_nhan=7, n_day_du=7))
    h = day_cvat.result_html(old, 'Khoi')
    assert 'Đã đẩy lên CVAT' in h and 'Gán tay có nháp' not in h and '1 Gán tay' in h
    assert 'Đã đẩy lên CVAT' in day_cvat.result_html(dict(trang_thai='xong'), 'Khoi')       # push.json rất cũ/thiếu khoá: không lỗi


def test_guide_html_mentions_draft_and_blank_image_warning():
    import review_app
    g = review_app.GUIDE_HTML
    assert 'kèm nháp' in g and 'low_conf' in g and 'ảnh trống' in g and 'Phân vân Nhận/Gán tay → chọn Nhận' in g
    assert review_app.GUIDE_HTML.count('<div') == review_app.GUIDE_HTML.count('</div>')



def test_old_push_json_xong_still_works_in_run_info_and_push_model(tmp_path, world):
    import day_cvat
    import dot_anh
    old = dict(tool='m28', phien_ban=1, trang_thai='xong', task='demo-Khoi', task_id=3, cvat_url='http://localhost:8080',
               task_url='http://localhost:8080/tasks/3', jobs=[dict(kind='nhan', n=4), dict(kind='gan_tay', n=1)], so_anh=dict(nhan=4, gan_tay=1),
               check=dict(ok=True, n_nhan=4, n_day_du=4))
    rd = make_dot_run(world, 'Khoi', decisions=ALL_DECIDED, done=True, push=old)
    info = dot_anh.run_info(rd, 'P2')
    assert info['push']['trang_thai'] == 'xong' and info['gan_tay'] == 2
    assert dot_anh.card_html(info)
    m = day_cvat.push_model(rd, 'P2', str(world), remaining=0, environ={})
    assert m['kind'] == 'done' and 'Đã đẩy lên CVAT' in day_cvat.panel_html(m)
    p = day_cvat.plan_counts(rd, 'P2', str(world))
    assert (p['tay'], p['tay_nhap'], p['tay_trong']) == (2, 1, 1)                      # a3 có nháp, a6 (no_draft) ảnh trống
