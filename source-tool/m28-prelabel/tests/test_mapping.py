"""Thử make_config / mapping / fit_map bằng dữ liệu giả (không dùng mặt thật)."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
import fit_map  # noqa: E402
import make_config as mc  # noqa: E402
from m28core import mapping  # noqa: E402


def test_similarity_recovers_params():
    rng = np.random.default_rng(0)
    src = rng.normal(size=(20, 2))
    th = np.deg2rad(30)
    R0 = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    dst = 1.7 * src @ R0.T + np.array([5, -3])
    s, R, t = mapping.similarity(src, dst)
    assert abs(s - 1.7) < 1e-6 and np.abs(R - R0).max() < 1e-6 and np.abs(t - [5, -3]).max() < 1e-6
    back = mapping.from_mean(mapping.to_mean(src, s, R, t), s, R, t)
    assert np.abs(back - src).max() < 1e-9


def test_mirror98_is_involution_and_symmetric_groups():
    m = mc.MIRROR98
    assert len(m) == 98 and all(m[m[i]] == i for i in range(98))
    assert all(m[i] == 32 - i for i in range(33))
    assert m[60] == 72 and m[64] == 68 and m[76] == 82 and m[96] == 97


def test_config_invariants():
    cfg = mc.build_config()
    pts = cfg['points']
    names = [p['name'] for p in pts]
    assert len(pts) == 50 and len(set(names)) == 50
    by = {p['name']: p for p in pts}
    for p in pts:
        q = by[p['flip']]
        assert q['flip'] == p['name'] and q['wflw'] == mc.MIRROR98[p['wflw']]
        assert {p['side'], q['side']} <= {'R', 'L'} if p is not q else p['side'] == 'M'
        assert p['type'] in 'EC' and (p['type'] == 'E') == (p['curve'] is None)
        assert all(0 <= i < 98 for i in (p['curve'] or [])) and p['line'] in cfg['lines']
        if p['coincide']:
            assert by[p['coincide']]['coincide'] == p['name']
    assert sum(p['side'] == 'R' for p in pts) == sum(p['side'] == 'L' for p in pts)   # R nào cũng có cặp L
    assert cfg['iod_points'] == [by[n]['name'] for n in cfg['iod_points']]
    assert [by[n]['wflw'] for n in cfg['iod_points']] == [60, 72]


def _synthetic():
    rng = np.random.default_rng(1)
    cfg = mc.build_config()
    mean478 = rng.uniform(100, 400, size=(478, 2))
    names = [p['name'] for p in cfg['points']]
    # đáp án giả = tổ hợp tuyến tính cố định của 4 đỉnh gần mốc ngẫu nhiên, nên ridge khôi phục được
    idx = {n: rng.choice(478, 4, replace=False) for n in names}
    wts = {n: rng.dirichlet(np.ones(4)) for n in names}
    faces, gt50 = {}, {}
    for i in range(60):
        p = mean478 + rng.normal(scale=2.0, size=mean478.shape)
        s, th, t = rng.uniform(0.8, 1.2), rng.uniform(-0.3, 0.3), rng.uniform(-20, 20, 2)
        R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
        q = s * p @ R.T + t
        f = f'F_{i:03d}'
        faces[f] = {'orig': q.tolist(), 'flip': None}
        gt50[f] = {n: (wts[n] @ q[idx[n]]).tolist() for n in names}
    return cfg, names, mean478, faces, gt50


def test_fit_and_apply_map_recovers_synthetic_truth_under_similarity():
    cfg, names, mean478, faces, gt50 = _synthetic()
    files = sorted(faces)
    m478 = fit_map.mean_shape([np.asarray(faces[f]['orig']) for f in files[:50]])
    feats = fit_map.build_features(faces, gt50, files[:50], m478, names)
    mp_map = fit_map.fit_all(feats, names, m478, 6, 0.1)
    assert mp_map['names'] == names
    err = []
    for f in files[50:]:
        pr = mapping.apply_map(faces[f]['orig'], mp_map, cfg)
        assert list(pr) == names
        err += [np.linalg.norm(np.array(pr[n]) - np.array(gt50[f][n])) for n in names]
    assert np.mean(err) < 3.0       # nhiễu đỉnh 2 px; ridge phải lọc được phần lớn


def test_apply_map_flipped_is_map_then_mirror_and_rename():
    cfg, names, mean478, faces, gt50 = _synthetic()
    files = sorted(faces)
    m478 = fit_map.mean_shape([np.asarray(faces[f]['orig']) for f in files[:50]])
    mp_map = fit_map.fit_all(fit_map.build_features(faces, gt50, files[:50], m478, names), names, m478, 6, 1.0)
    pts = np.asarray(faces[files[0]]['orig'])
    raw = mapping.map_points(pts, mp_map)
    out = mapping.apply_map(pts, mp_map, cfg, flipped=True, width=512)
    flip = {p['name']: p['flip'] for p in cfg['points']}
    for n in names:
        x, y = raw[n]
        assert np.allclose(out[flip[n]], [512 - x, y])
    assert list(out) == names


def test_apply_map_rejects_mismatched_config_and_shape():
    cfg, names, mean478, faces, gt50 = _synthetic()
    files = sorted(faces)
    m478 = fit_map.mean_shape([np.asarray(faces[f]['orig']) for f in files[:50]])
    mp_map = fit_map.fit_all(fit_map.build_features(faces, gt50, files[:50], m478, names), names, m478, 6, 1.0)
    bad = json.loads(json.dumps(cfg))
    bad['points'][0]['name'] = 'khac'
    for call in (lambda: mapping.apply_map(faces[files[0]]['orig'], mp_map, bad),
                 lambda: mapping.apply_map(np.zeros((10, 2)), mp_map, cfg)):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError('phải báo ValueError')


def test_gt50_from_gt98_and_template():
    cfg = mc.build_config()
    g98 = {'F_001.png': (np.arange(196).reshape(98, 2)).tolist()}
    g50 = mc.gt50_from_gt98(cfg, g98)
    p = cfg['points'][0]
    assert g50['F_001.png'][p['name']] == g98['F_001.png'][p['wflw']]
    rows = [{'set': 'F', 'pose': '0', 'file': 'F_001.png'}]
    t = mc.template(rows, g98)
    assert t.shape == (50, 2)


def test_committed_config_matches_map():
    root = os.path.join(HERE, '..', 'config')
    cfg = json.load(open(os.path.join(root, 'm28_config.json'), encoding='utf-8'))
    mp_map = json.load(open(os.path.join(root, 'map_mp50.json')))
    assert [p['name'] for p in cfg['points']] == mp_map['names'] and len(mp_map['mean478']) == 478
    assert cfg['points'] == mc.build_config(np.array([p['tmpl'] for p in cfg['points']]))['points']
    out = mapping.apply_map(mp_map['mean478'], mp_map, cfg)       # hình trung bình vào, ra điểm hợp lý trong ảnh 512
    arr = np.array(list(out.values()))
    assert arr.shape == (50, 2) and np.isfinite(arr).all() and arr.min() > -50 and arr.max() < 562
