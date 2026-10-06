"""Thử tool/eval50.py bằng nhãn GIẢ (XML dựng tay, số tính tay), không ảnh thật, không CVAT."""
import csv
import json
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
import eval50  # noqa: E402
from m28core import cvat_io, steps  # noqa: E402

REAL_CFG = os.path.join(HERE, '..', 'config', 'm28_config.json')


def mini_cfg():
    """4 điểm: a, b (E, vùng eye; a, b là hai khoé mắt ngoài = iod_points), c (C, vùng lip, curve a-c-b), d (E, vùng lip)."""
    pts = [dict(name='a', region='eye', type='E', curve=None, coincide=None),
           dict(name='b', region='eye', type='E', curve=None, coincide=None),
           dict(name='c', region='lip', type='C', curve=['a', 'c', 'b'], coincide=None),
           dict(name='d', region='lip', type='E', curve=None, coincide=None)]
    return dict(points=pts, iod_points=['a', 'b'])


GT = dict(a=[0, 0], b=[100, 0], c=[50, 0], d=[50, 50])


def test_point_to_curve_five_hand_checked_cases():
    curve = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 0.0]])                       # có đoạn dài 0: không chia cho 0
    assert eval50.point_to_curve(np.array([4.0, 3.0]), curve) == pytest.approx(3.0)       # chiếu vuông góc xuống đoạn
    assert eval50.point_to_curve(np.array([14.0, 3.0]), curve) == pytest.approx(5.0)      # ngoài đầu mút: tới đầu mút (4, 3)
    assert eval50.point_to_curve(np.array([-3.0, 4.0]), curve) == pytest.approx(5.0)      # ngoài đầu mút kia
    bent = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0]])                                # gấp khúc: chọn đoạn gần nhất
    assert eval50.point_to_curve(np.array([12.0, 5.0]), bent) == pytest.approx(2.0)
    assert eval50.point_to_curve(np.array([5.0, 0.0]), bent) == pytest.approx(0.0)         # nằm trên đường
    assert eval50.point_to_curve(np.array([3.0, 4.0]), np.array([[0.0, 0.0]])) == pytest.approx(5.0)   # đường chỉ một điểm


def test_iod_and_point_errors_by_hand():
    cfg = mini_cfg()
    assert eval50.iod(GT, cfg) == pytest.approx(100.0)
    assert eval50.iod({'a': [0, 0]}, cfg) is None and eval50.iod({'a': [1, 1], 'b': [1, 1]}, cfg) is None
    pred = dict(a=[3, 4], b=[100, 0], c=[50, 5], d=[50, 60])
    err, missing, d = eval50.point_errors(pred, GT, cfg)
    assert d == pytest.approx(100.0) and missing == []
    assert err == pytest.approx(dict(a=5.0, b=0.0, c=5.0, d=10.0))                  # E điểm-điểm; C tới đường gấp khúc đáp án
    slide = dict(pred, c=[70, 0])                                                      # C trượt dọc đường: lỗi chính 0, điểm-điểm 20
    err2, _, _ = eval50.point_errors(slide, GT, cfg)
    assert err2['c'] == pytest.approx(0.0) and eval50.p2p_errors(slide, GT, cfg)['c'] == pytest.approx(20.0)
    # đường gấp khúc là của ĐÁP ÁN: đáp án c lệch khỏi trục thì đường cong đổi theo
    gt_bent = dict(GT, c=[50, 10])
    err3, _, _ = eval50.point_errors(dict(pred, c=[50, 10]), gt_bent, cfg)
    assert err3['c'] == pytest.approx(0.0)


def test_face_scores_nme_secondary_region_and_eye():
    cfg = mini_cfg()
    pred = dict(a=[3, 4], b=[100, 0], c=[60, 5], d=[50, 60])
    s = eval50.face_scores(pred, GT, cfg)
    assert s['ok'] and s['nme'] == pytest.approx((5 + 0 + 5 + 10) / 4)               # c: tới trục x = 5 dù trượt ngang
    assert s['nme_p2p'] == pytest.approx((5 + 0 + np.hypot(10, 5) + 10) / 4)
    assert s['nme_eye'] == pytest.approx(2.5) and s['region'] == pytest.approx(dict(eye=2.5, lip=7.5))
    assert s['n_missing'] == 0 and s['nme'] <= s['nme_p2p']                            # chỉ số chính không lớn hơn chỉ số phụ
    bad = eval50.face_scores(dict(a=[30, 40], b=[100, 0], c=[50, 0], d=[50, 50]), GT, cfg)   # a lệch 50 = 50% IOD
    assert bad['nme'] == pytest.approx(12.5) and bad['nme'] >= eval50.BAD              # mặt hỏng


def test_missing_points_are_skipped_and_counted_and_missing_iod_point_skips_the_face():
    cfg = mini_cfg()
    pred = dict(a=[3, 4], b=[100, 0], c=[50, 5], d=[50, 60])
    gt_no_d = {k: v for k, v in GT.items() if k != 'd'}
    s = eval50.face_scores(pred, gt_no_d, cfg)
    assert s['n_missing'] == 1 and s['nme'] == pytest.approx((5 + 0 + 5) / 3)
    gt_no_c = {k: v for k, v in GT.items() if k != 'c'}                                 # thiếu c ở đáp án: bỏ c khỏi phép đo
    assert eval50.face_scores(pred, gt_no_c, cfg)['nme'] == pytest.approx((5 + 0 + 10) / 3)
    cfg2 = mini_cfg()
    cfg2['points'][2]['curve'] = ['a', 'c', 'd', 'b']                                   # d thiếu thì bị bỏ khỏi đường gấp khúc (còn a-c-b)
    s2 = eval50.face_scores(pred, gt_no_d, cfg2)
    assert s2['ok'] and s2['nme'] == pytest.approx((5 + 0 + 5) / 3)
    no_iod = eval50.face_scores(pred, {k: v for k, v in GT.items() if k != 'b'}, cfg)
    assert not no_iod['ok'] and 'khoé mắt ngoài' in no_iod['reason']
    only = eval50.face_scores({'a': [0, 0]}, {'a': [0, 0], 'b': [100, 0]}, cfg)       # chỉ a có cả hai: vẫn chấm
    assert only['ok'] and only['nme'] == pytest.approx(0.0) and only['n_missing'] == 3


def xml_of(cfg, faces, order=None, outside=(), skeletons=1, point_order=None):
    """faces: {tên ảnh: {điểm: [x, y]}} -> bytes annotations.xml CVAT. order: thứ tự ảnh; point_order: thứ tự điểm; outside: {(ảnh, điểm)} có outside=1."""
    names = point_order or [p['name'] for p in cfg['points']]
    parts = ['<?xml version="1.0" encoding="utf-8"?>', '<annotations>', '  <version>1.1</version>']
    for i, im in enumerate(order or list(faces)):
        parts.append(f'<image id="{i}" name="{im}" width="640" height="480">')
        for _ in range(skeletons):
            parts.append('<skeleton label="face50">')
            for n in names:
                if n in faces[im]:
                    x, y = faces[im][n]
                    out = '1' if (im, n) in outside else '0'
                    parts.append(f'<points label="{n}" occluded="0" outside="{out}" points="{x},{y}"><attribute name="low_conf">false</attribute></points>')
            parts.append('</skeleton>')
        parts.append('</image>')
    parts.append('</annotations>')
    return '\n'.join(parts).encode('utf-8')


def test_matching_is_by_image_name_and_point_name_not_by_order(tmp_path):
    cfg = mini_cfg()
    faces_gt = {'F_001.png': dict(GT), 'F_002.png': {k: [v[0] * 2, v[1] * 2] for k, v in GT.items()}}
    faces_pr = {'F_002.png': {k: [v[0] * 2 + 2, v[1] * 2] for k, v in GT.items()}, 'F_001.png': dict(GT, d=[50, 60]), 'F_999.png': dict(GT)}
    gt = tmp_path / 'gt.xml'
    pr = tmp_path / 'pr.xml'
    gt.write_bytes(xml_of(cfg, faces_gt))
    pr.write_bytes(xml_of(cfg, faces_pr, order=['F_999.png', 'F_002.png', 'F_001.png'], point_order=['d', 'c', 'b', 'a']))     # thứ tự ảnh và điểm khác hẳn
    res = eval50.evaluate(eval50.read_labels(str(pr), cfg), eval50.read_labels(str(gt), cfg), cfg, 'manual')
    by = {r['face_id']: r for r in res['rows']}
    assert sorted(by) == ['F_001', 'F_002'] and res['extra_pred'] == ['F_999'] and res['missing_pred'] == []
    assert by['F_001']['nme'] == pytest.approx(10 / 4)                                  # chỉ d lệch 10 / IOD 100
    assert by['F_002']['nme'] == pytest.approx(0.75)                                    # a, b, d lệch 2 px, c trượt dọc đường (0); IOD 200: (1+1+0+1)/4
    assert all(r['condition'] == 'manual' for r in res['rows']) and res['summary']['n_faces'] == 2
    s = res['summary']
    assert s['frac_bad'] == 0.0 and s['n_bad'] == 0 and set(s['region_mean']) == {'eye', 'lip'}


def test_hand_checked_two_face_summary():
    cfg = mini_cfg()
    gt = {'f1': dict(GT), 'f2': dict(GT)}
    pred = {'f1': dict(GT, a=[3, 4]), 'f2': dict(GT, a=[30, 40], d=[50, 70])}          # f1: a lệch 5 -> NME 1,25; f2: a 50, d 20 -> NME 17,5
    res = eval50.evaluate(pred, gt, cfg)
    n = {r['face_id']: r['nme'] for r in res['rows']}
    assert n == pytest.approx(dict(f1=1.25, f2=17.5))
    s = res['summary']
    assert s['nme_mean'] == pytest.approx((1.25 + 17.5) / 2) and s['nme_median'] == pytest.approx((1.25 + 17.5) / 2)
    assert s['n_bad'] == 1 and s['frac_bad'] == pytest.approx(0.5)
    assert s['region_mean']['eye'] == pytest.approx((2.5 + 25.0) / 2) and s['region_mean']['lip'] == pytest.approx((0.0 + 10.0) / 2)
    text = eval50.format_summary(res, cfg)
    assert '2 mặt chấm được' in text and 'mặt hỏng' in text and 'eye' in text and 'lip' in text


def test_outside_points_two_skeletons_and_missing_iod_in_xml(tmp_path, capsys):
    cfg = mini_cfg()
    p = tmp_path / 'a.xml'
    p.write_bytes(xml_of(cfg, {'x.png': dict(GT)}, outside={('x.png', 'd')}))
    got = eval50.read_labels(str(p), cfg)
    assert 'd' not in got['x'] and set(got['x']) == {'a', 'b', 'c'}                      # outside="1": bỏ điểm
    p2 = tmp_path / 'b.xml'
    p2.write_bytes(xml_of(cfg, {'x.png': dict(GT), 'y.png': dict(GT)}, skeletons=2))
    warned = []
    assert eval50.read_labels(str(p2), cfg, warn=warned.append) == {} and len(warned) == 2 and 'x.png' in warned[0]      # nhiều hơn một skeleton: báo
    p3 = tmp_path / 'c.xml'
    p3.write_bytes(xml_of(cfg, {'x.png': {k: v for k, v in GT.items() if k != 'a'}}))
    res = eval50.evaluate(eval50.read_labels(str(p3), cfg), eval50.read_labels(str(p3), cfg), cfg)
    assert res['rows'] == [] and res['skipped'] and res['summary']['n_faces'] == 0
    assert 'Không có mặt nào' in eval50.format_summary(res, cfg)


def test_reads_zip_exported_from_cvat_and_strips_extensions(tmp_path):
    cfg = mini_cfg()
    z = tmp_path / 'task.zip'
    z.write_bytes(cvat_io.zip_bytes_with('annotations.xml', xml_of(cfg, {'D_01.png': dict(GT), 'sub\\img 2.JPG': dict(GT)})))
    got = eval50.read_labels(str(z), cfg)
    assert sorted(got) == ['D_01', 'img 2']
    assert eval50.stem('a/b/c.jpeg') == 'c' and eval50.stem('x.PNG') == 'x' and eval50.stem('noext') == 'noext'


def test_nme_per_face_csv_columns_and_append(tmp_path):
    cfg = mini_cfg()
    res = eval50.evaluate({'f1': dict(GT, a=[3, 4])}, {'f1': dict(GT)}, cfg, 'manual')
    out = tmp_path / 'sub' / 'nme_per_face.csv'
    eval50.write_csv(str(out), res['rows'], cfg)
    res2 = eval50.evaluate({'f1': dict(GT, d=[50, 60])}, {'f1': dict(GT)}, cfg, 'assisted')
    eval50.write_csv(str(out), res2['rows'], cfg, append=True)                          # nối, không ghi lại hàng tiêu đề
    rows = list(csv.reader(open(out, encoding='utf-8')))
    assert rows[0][:4] == ['face_id', 'condition', 'nme', 'nme_eye']                  # cột P5 đã hẹn, đúng thứ tự
    assert 'reg_eye' in rows[0] and 'reg_lip' in rows[0] and 'eye_open_err' in rows[0] and rows[0].count('face_id') == 1 and len(set(rows[0])) == len(rows[0])   # không trùng tên cột
    assert [r[1] for r in rows[1:]] == ['manual', 'assisted'] and float(rows[1][2]) == pytest.approx(1.25) and float(rows[2][2]) == pytest.approx(2.5)
    assert float(rows[1][3]) == pytest.approx(2.5)


def test_eye_openness_uses_coincide_pairs():
    cfg = json.load(open(REAL_CFG, encoding='utf-8'))
    pts = {p['name']: [float(p['tmpl'][0]), float(p['tmpl'][1])] for p in cfg['points']}
    pts['p36_eye_R'][0] = pts['p34_eye_R'][0]                                           # mí trên và mí dưới cùng cột: dễ tính tay
    d = eval50.iod(pts, cfg)
    o = eval50.eye_openness(pts, cfg, d)
    assert set(o) == {'p34_eye_R', 'p38_eye_L'} and all(v > 0 for v in o.values())
    wide = dict(pts, p34_eye_R=[pts['p34_eye_R'][0], pts['p34_eye_R'][1] - 10])         # mí trên nhấc lên 10 px: mở hơn đúng 10 / IOD
    assert eval50.eye_openness(wide, cfg, d)['p34_eye_R'] - o['p34_eye_R'] == pytest.approx(10 / d * 100)
    s = eval50.face_scores(wide, pts, cfg)
    assert s['ok'] and s['eye_open_err'] == pytest.approx((10 / d * 100 + 0) / 2) and s['n_missing'] == 0
    assert s['nme'] <= s['nme_p2p'] + 1e-9


def make_run(tmp_path, mode):
    """Lượt giả: 2 mặt, ảnh gốc 640x480; toạ độ ảnh cắt 512. mode wflw: XML theo ảnh cắt; mode auto: theo ảnh gốc."""
    cfg = json.load(open(REAL_CFG, encoding='utf-8'))
    names = [p['name'] for p in cfg['points']]
    rd = tmp_path / 'runs' / 'R'
    (rd / 'crop').mkdir(parents=True)
    (rd / 'map50').mkdir()
    meta = {'F_001': dict(src='/x/frames/a/img_1.jpg', rel='a/img_1.jpg', left=100.0, top=50.0, k=2.0, w=640, h=480),
            'F_002': dict(src='/x/frames/b/img_2.jpg', rel='b/img_2.jpg', left=10.0, top=20.0, k=1.5, w=640, h=480)}
    rng = np.random.default_rng(0)
    mp50 = {n: dict(orig={nm: [float(rng.uniform(50, 450)), float(rng.uniform(50, 450))] for nm in names}, flip=None) for n in meta}
    (rd / 'crop' / 'meta.json').write_text(json.dumps(meta), encoding='utf-8')
    (rd / 'crop' / 'box.txt').write_text(mode, encoding='utf-8')
    (rd / 'map50' / 'mp50.json').write_text(json.dumps(mp50), encoding='utf-8')
    return cfg, names, meta, mp50


def test_run_prediction_matches_push_coordinates_and_file_names(tmp_path, monkeypatch):
    for mode in ('wflw', 'auto'):
        d = tmp_path / mode
        d.mkdir()
        cfg, names, meta, mp50 = make_run(d, mode)
        monkeypatch.chdir(d)
        got = eval50.read_run_pred('R', cfg)
        expect_keys = ['F_001', 'F_002'] if mode == 'wflw' else ['img_1', 'img_2']          # tên ảnh tải lên CVAT, bỏ đuôi
        assert sorted(got) == expect_keys
        for n, key in zip(('F_001', 'F_002'), expect_keys):
            pts, _w, _h = steps._face_pts(mode, n, meta, mp50, names)                         # đúng logic của push (không chép lại)
            assert np.allclose([got[key][nm] for nm in names], pts)
        # nhãn chính là prelabel.xml của push: tự so với chính nó thì NME = 0; thêm nhiễu thì > 0
        steps.build_xml(mode, ['F_001', 'F_002'], meta, mp50, {n: [False] * 50 for n in meta}, cfg, str(d / 'runs' / 'R' / 'xml' / 'prelabel.xml'))
        xml = eval50.read_labels(str(d / 'runs' / 'R' / 'xml' / 'prelabel.xml'), cfg)
        res = eval50.evaluate(got, xml, cfg)
        assert res['summary']['n_faces'] == 2 and res['summary']['nme_mean'] < 0.01      # chỉ lệch do làm tròn 2 chữ số khi ghi XML
        noisy = {k: {n: [v[0] + 1.5, v[1] - 2.0] for n, v in pts.items()} for k, pts in xml.items()}
        assert eval50.evaluate(noisy, xml, cfg)['summary']['nme_mean'] > 0.1


def test_main_end_to_end_and_exit_codes(tmp_path, monkeypatch, capsys):
    cfg, names, meta, mp50 = make_run(tmp_path, 'wflw')
    monkeypatch.chdir(tmp_path)
    shutil_cfg = tmp_path / 'config'
    shutil_cfg.mkdir()
    (shutil_cfg / 'm28_config.json').write_text(json.dumps(cfg), encoding='utf-8')
    steps.build_xml('wflw', ['F_001', 'F_002'], meta, mp50, {n: [False] * 50 for n in meta}, cfg, str(tmp_path / 'gt.xml'))
    assert eval50.main(['--gt', 'gt.xml', '--run', 'R', '--condition', 'manual']) == 0
    out = capsys.readouterr().out
    assert '2 mặt chấm được' in out and 'nme_per_face.csv' in out
    rows = list(csv.DictReader(open(tmp_path / 'outputs' / 'nme_per_face.csv', encoding='utf-8')))
    assert [r['face_id'] for r in rows] == ['F_001', 'F_002'] and {r['condition'] for r in rows} == {'manual'}
    (tmp_path / 'empty.xml').write_text('<annotations></annotations>', encoding='utf-8')
    assert eval50.main(['--gt', 'empty.xml', '--run', 'R']) == 1                         # không ghép được mặt nào
