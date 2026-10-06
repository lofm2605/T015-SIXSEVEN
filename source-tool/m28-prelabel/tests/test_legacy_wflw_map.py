"""LỊCH SỬ (QĐ-001): thử make_config_wflw (MIRROR98, gt50_from_gt98, template), ánh xạ ridge và fit_map của giai đoạn WFLW bằng dữ liệu giả.

Phần này đã chuyển vào tool/legacy_wflw/ nhưng các kiểm tra vẫn có giá trị (similarity, ridge, point_to_curve, wrong_face), nên giữ lại.
Test của ánh xạ mới (chọn đỉnh) nằm ở tests/test_mapping.py.
"""
import json
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
sys.path.insert(0, os.path.join(HERE, '..', 'tool', 'legacy_wflw'))
import fit_map  # noqa: E402
import make_config_wflw as mc  # noqa: E402
import mapping_ridge as mapping  # noqa: E402
from m28core import mapping as mapping_new  # noqa: E402

COMMITTED = os.path.join(HERE, '..', 'tool', 'legacy_wflw')


def test_similarity_recovers_params_and_rejects_bad_input():
    rng = np.random.default_rng(0)
    src = rng.normal(size=(20, 2))
    th = np.deg2rad(30)
    R0 = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    dst = 1.7 * src @ R0.T + np.array([5, -3])
    s, R, t = mapping_new.similarity(src, dst)
    assert abs(s - 1.7) < 1e-6 and np.abs(R - R0).max() < 1e-6 and np.abs(t - [5, -3]).max() < 1e-6
    assert np.abs(mapping_new.from_mean(mapping_new.to_mean(src, s, R, t), s, R, t) - src).max() < 1e-9
    # gương phản chiếu: không được trả phép lật (det R = +1), kết quả vẫn là phép quay
    s2, R2, _ = mapping_new.similarity(src * [-1, 1], dst)
    assert abs(np.linalg.det(R2) - 1) < 1e-9
    with pytest.raises(ValueError):
        mapping_new.similarity(np.zeros((5, 2)), dst[:5])
    bad = src.copy()
    bad[0, 0] = np.nan
    with pytest.raises(ValueError):
        mapping_new.similarity(bad, dst)
    with pytest.raises(ValueError):
        mapping.fit_ridge(np.zeros((4, 4)), np.zeros((4, 2)), 0)


def test_mirror98_is_involution_and_symmetric_groups():
    m = mc.MIRROR98
    assert len(m) == 98 and all(m[m[i]] == i for i in range(98))
    assert all(m[i] == 32 - i for i in range(33))
    assert m[60] == 72 and m[64] == 68 and m[76] == 82 and m[96] == 97 and m[84] == 86


def test_config_invariants():
    cfg = mc.build_config()
    pts = cfg['points']
    names = [p['name'] for p in pts]
    assert len(pts) == 50 and len(set(names)) == 50
    by = {p['name']: p for p in pts}
    for p in pts:
        q = by[p['flip']]
        assert q['flip'] == p['name'] and q['wflw'] == mc.MIRROR98[p['wflw']]
        if p is q:
            assert p['side'] == 'M'
        else:
            assert {p['side'], q['side']} == {'R', 'L'}
        assert p['type'] in ('E', 'C') and (p['type'] == 'E') == (p['curve'] is None)
        assert all(0 <= i < 98 for i in (p['curve'] or [])) and p['line'] in cfg['lines']
        if p['coincide']:
            assert by[p['coincide']]['coincide'] == p['name']
    assert sum(p['side'] == 'R' for p in pts) == sum(p['side'] == 'L' for p in pts) == 21
    assert [by[n]['wflw'] for n in cfg['iod_points']] == [60, 72]
    assert cfg['t_flip'] is None            # P2 chốt sau họp 12/10


def test_lower_lip_sides_follow_image_position_not_index_order():
    by = {p['wflw']: p for p in mc.build_config()['points']}
    assert by[84]['side'] == 'L' and by[86]['side'] == 'R'      # môi dưới đánh số từ phải sang trái
    assert by[77]['side'] == 'R' and by[81]['side'] == 'L'


def test_legacy_config_matches_legacy_map_and_is_geometrically_consistent():
    cfg = json.load(open(os.path.join(COMMITTED, 'm28_config_wflw.json'), encoding='utf-8'))
    mp_map = json.load(open(os.path.join(COMMITTED, 'map_mp50_wflw.json')))
    pts = cfg['points']
    assert [p['name'] for p in pts] == mp_map['names'] and len(mp_map['mean478']) == 478
    assert mp_map['defs'] == {p['name']: {'wflw': p['wflw'], 'flip': p['flip']} for p in pts}
    by = {p['name']: p for p in pts}
    for p in pts:                                     # khuôn: R ở nửa trái ảnh, L ở nửa phải, M ở giữa
        q = by[p['flip']]
        if p['side'] == 'R':
            assert p['tmpl'][0] < q['tmpl'][0], (p['name'], p['tmpl'], q['tmpl'])
        if p['side'] == 'M':
            assert abs(p['tmpl'][0] - 256) < 30
    out = mapping.apply_map(mp_map['mean478'], mp_map, cfg)       # hình trung bình vào, ra điểm hợp lý trong ảnh 512
    arr = np.array(list(out.values()))
    assert arr.shape == (50, 2) and np.isfinite(arr).all() and arr.min() > -50 and arr.max() < 562


def _synthetic(n=60, noise=2.0, seed=1):
    """Đáp án = tổ hợp 6 đỉnh gần một vị trí cố định, nên ridge (k = 6) khôi phục được."""
    rng = np.random.default_rng(seed)
    cfg = mc.build_config()
    mean478 = rng.uniform(100, 400, size=(478, 2))
    names = [p['name'] for p in cfg['points']]
    idx, wts = {}, {}
    for nme_ in names:
        c = rng.uniform(150, 350, 2)
        idx[nme_] = np.argsort(np.linalg.norm(mean478 - c, axis=1))[:6]
        wts[nme_] = rng.dirichlet(np.ones(6))
    faces, gt50 = {}, {}
    for i in range(n):
        p = mean478 + rng.normal(scale=noise, size=mean478.shape)
        s, th, t = rng.uniform(0.8, 1.2), rng.uniform(-0.3, 0.3), rng.uniform(-20, 20, 2)
        R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
        q = s * p @ R.T + t
        f = f'F_{i:03d}'
        faces[f] = {'orig': q.tolist(), 'flip': None}
        gt50[f] = {n_: (wts[n_] @ q[idx[n_]]).tolist() for n_ in names}
    return cfg, names, mean478, faces, gt50


def _fit(cfg, names, faces, gt50, lam, n_fit=50):
    files = sorted(faces)
    m478 = fit_map.mean_shape([np.asarray(faces[f]['orig']) for f in files[:n_fit]])
    feats = fit_map.build_features(faces, gt50, files[:n_fit], m478, names)
    return fit_map.fit_all(feats, names, m478, 6, lam, cfg['points']), files[n_fit:]


def _err(mp_map, cfg, faces, gt50, files, names):
    return np.mean([np.linalg.norm(np.array(mapping.apply_map(faces[f]['orig'], mp_map, cfg)[n]) - np.array(gt50[f][n]))
                    for f in files for n in names])


def test_fit_recovers_synthetic_truth_better_than_intercept_only():
    cfg, names, mean478, faces, gt50 = _synthetic()
    good, held = _fit(cfg, names, faces, gt50, 0.1)
    flat, _ = _fit(cfg, names, faces, gt50, 1e12)            # λ rất lớn: chỉ còn vị trí trung bình
    e_good, e_flat = _err(good, cfg, faces, gt50, held, names), _err(flat, cfg, faces, gt50, held, names)
    assert e_good < 1.5 and e_good < 0.6 * e_flat, (e_good, e_flat)


def test_apply_map_is_similarity_invariant():
    cfg, names, mean478, faces, gt50 = _synthetic()
    mp_map, _ = _fit(cfg, names, faces, gt50, 1.0)
    pts = np.asarray(faces['F_000']['orig'])
    th = 0.4
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    a = mapping.apply_map(pts, mp_map, cfg)
    b = mapping.apply_map(1.3 * pts @ R.T + [7, -9], mp_map, cfg)
    for n in names:
        assert np.allclose(np.array(a[n]) * 1.3 @ R.T + [7, -9], b[n], atol=1e-6)


def test_apply_map_flipped_is_map_then_mirror_and_rename():
    cfg, names, mean478, faces, gt50 = _synthetic()
    mp_map, _ = _fit(cfg, names, faces, gt50, 1.0)
    mp_map['flip_width'] = 511.5
    pts = np.asarray(faces['F_000']['orig'])
    raw = mapping.map_points(pts, mp_map)
    flip = {p['name']: p['flip'] for p in cfg['points']}
    for width, expect in ((None, 511.5), (512, 512.0)):
        out = mapping.apply_map(pts, mp_map, cfg, flipped=True, width=width)
        assert list(out) == names
        for n in names:
            assert np.allclose(out[flip[n]], [expect - raw[n][0], raw[n][1]])


def test_apply_map_accepts_subset_config_and_rejects_changed_definition():
    cfg, names, mean478, faces, gt50 = _synthetic()
    mp_map, _ = _fit(cfg, names, faces, gt50, 1.0)
    pts = faces['F_000']['orig']
    sub = json.loads(json.dumps(cfg))
    sub['points'] = [p for p in sub['points'] if p['region'] != 'brow']          # bỏ bớt điểm: không cần khớp lại
    full = mapping.apply_map(pts, mp_map, cfg)
    part = mapping.apply_map(pts, mp_map, sub)
    assert list(part) == [p['name'] for p in sub['points']] and all(part[n] == full[n] for n in part)
    pf, ff = mapping.apply_map(pts, mp_map, sub, flipped=True), mapping.apply_map(pts, mp_map, cfg, flipped=True)
    assert all(pf[n] == ff[n] for n in pf)
    moved = json.loads(json.dumps(cfg))
    moved['points'][0]['wflw'] += 2                                          # đổi định nghĩa, giữ tên
    renamed = json.loads(json.dumps(cfg))
    renamed['points'][0]['name'] = 'khac'
    for bad in (moved, renamed):
        with pytest.raises(ValueError):
            mapping.apply_map(pts, mp_map, bad)
    with pytest.raises(ValueError):
        mapping.apply_map(np.zeros((10, 2)), mp_map, cfg)
    nan = np.asarray(pts).copy()
    nan[0, 0] = np.nan
    with pytest.raises(ValueError):
        mapping.apply_map(nan, mp_map, cfg)


def test_gt50_from_gt98_and_template():
    cfg = mc.build_config()
    g98 = {'F_001.png': (np.arange(196).reshape(98, 2)).tolist()}
    g50 = mc.gt50_from_gt98(cfg, g98)
    p = cfg['points'][0]
    assert g50['F_001.png'][p['name']] == g98['F_001.png'][p['wflw']]
    t = mc.template([{'set': 'F', 'pose': '0', 'file': 'F_001.png'}], g98)
    assert t.shape == (50, 2)
    with pytest.raises(ValueError):
        mc.template([], g98)
    with pytest.raises(AssertionError):
        mc.build_config(np.zeros((10, 2)))


def test_rerunning_make_config_keeps_values_others_wrote():
    new = mc.build_config(np.arange(100, dtype=float).reshape(50, 2))
    old = json.loads(json.dumps(new))
    old['t_flip'], old['tolerance'], old['status'] = 0.07, {'jaw': 3.0}, 'DONG BANG 12/10'
    fresh = mc.build_config()                                       # chạy lại không kèm tmpl, t_flip
    kept = mc.keep_existing(fresh, old, t_flip_given=False)
    assert set(kept) == {'t_flip', 'tolerance', 'status', 'tmpl'}
    assert fresh['t_flip'] == 0.07 and fresh['tolerance'] == {'jaw': 3.0} and fresh['points'][0]['tmpl'] == [0.0, 1.0]
    forced = mc.keep_existing(mc.build_config(), old, t_flip_given=True)   # --t-flip mới thì không giữ số cũ
    assert 't_flip' not in forced


def test_split_point_to_curve_and_face_nme():
    f = [f'F_{i:03d}' for i in range(300)]
    fit, chk = fit_map.split_F(f, 5)
    assert len(fit) == 240 and len(chk) == 60 and not set(fit) & set(chk)
    assert fit_map.split_F(f, 5) == (fit, chk) and fit_map.split_F(f, 6)[0] != fit
    curve = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 0.0]])        # có đoạn dài 0
    assert fit_map.point_to_curve(np.array([4.0, 3.0]), curve) == pytest.approx(3.0)
    assert fit_map.point_to_curve(np.array([14.0, 3.0]), curve) == pytest.approx(5.0)
    g98 = np.zeros((98, 2))
    g98[60], g98[72] = [0, 0], [100, 0]
    pts = [{'name': 'a', 'type': 'E', 'curve': None}, {'name': 'b', 'type': 'C', 'curve': [0, 1]}]
    g98[0], g98[1] = [0, 0], [10, 0]
    main_, sec = fit_map.face_nme({'a': [3, 4], 'b': [5, 2]}, {'a': [0, 0], 'b': [5, 0]}, g98, pts)
    assert main_ == pytest.approx((5 + 2) / 2) and sec == pytest.approx((5 + 2) / 2)
    main2, sec2 = fit_map.face_nme({'a': [0, 0], 'b': [5, 2]}, {'a': [0, 0], 'b': [8, 0]}, g98, pts)
    assert main2 == pytest.approx(1.0) and sec2 == pytest.approx((0 + np.hypot(3, 2)) / 2)   # C: tới đường, không tới điểm đáp án


def test_wrong_face_is_detected_by_centre_distance():
    cfg, names, mean478, faces, gt50 = _synthetic(n=8)
    g98 = {f: np.zeros((98, 2)) for f in faces}
    for f in g98:
        g98[f][60], g98[f][72] = [200, 250], [300, 250]                      # IOD = 100
    pred = {f: {'orig': np.asarray(faces[f]['orig']).tolist()} for f in faces}
    gt = {f: {n: np.asarray(faces[f]['orig']).mean(0).tolist() for n in names} for f in faces}
    assert fit_map.wrong_face(pred, gt, g98, list(faces), names) == []
    pred['F_001']['orig'] = (np.asarray(pred['F_001']['orig']) + [200, 0]).tolist()    # dò nhầm người: lệch 2 IOD
    assert fit_map.wrong_face(pred, gt, g98, list(faces), names) == ['F_001']
