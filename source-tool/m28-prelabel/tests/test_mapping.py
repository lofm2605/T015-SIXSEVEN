"""Thử config version 2 (chọn đỉnh MediaPipe), hoán vị gương, apply_map và make_config bằng dữ liệu giả + file ĐÃ COMMIT (không dùng mặt thật).

Phần của giai đoạn WFLW (ridge, MIRROR98, fit_map) nằm ở tests/test_legacy_wflw_map.py. Kiểm trên dữ liệu thật (check_flip.py, check_drivface.py) không nằm trong pytest.
"""
import copy
import json
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
import make_config as mc  # noqa: E402
import make_label  # noqa: E402
from m28core import mapping, mirror  # noqa: E402
from synth_faces import synthetic_run  # noqa: E402

COMMITTED = os.path.join(HERE, '..', 'config')
LEGACY = os.path.join(HERE, '..', 'tool', 'legacy_wflw')


def load(*parts):
    with open(os.path.join(*parts), encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def committed():
    return dict(cfg=load(COMMITTED, 'm28_config.json'), mp=load(COMMITTED, 'map_mp50.json'), mir=load(COMMITTED, 'mp_mirror478.json'),
                label=load(COMMITTED, 'face50_label.json'))


def pts478(seed=0):
    return np.random.default_rng(seed).uniform(0, 512, size=(478, 2))


def test_similarity_recovers_params_and_rejects_bad_input():
    rng = np.random.default_rng(0)
    src = rng.normal(size=(20, 2))
    th = np.deg2rad(30)
    R0 = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    dst = 1.7 * src @ R0.T + np.array([5, -3])
    s, R, t = mapping.similarity(src, dst)
    assert abs(s - 1.7) < 1e-6 and np.abs(R - R0).max() < 1e-6 and np.abs(t - [5, -3]).max() < 1e-6
    assert np.abs(mapping.from_mean(mapping.to_mean(src, s, R, t), s, R, t) - src).max() < 1e-9
    s2, R2, _ = mapping.similarity(src * [-1, 1], dst)           # gương phản chiếu: không được trả phép lật (det R = +1)
    assert abs(np.linalg.det(R2) - 1) < 1e-9
    with pytest.raises(ValueError):
        mapping.similarity(np.zeros((5, 2)), dst[:5])
    bad = src.copy()
    bad[0, 0] = np.nan
    with pytest.raises(ValueError):
        mapping.similarity(bad, dst)


# ---------- config version 2 ----------
def test_build_config_v2_structure():
    cfg = mc.build_config()
    pts = cfg['points']
    names = [p['name'] for p in pts]
    assert cfg['version'] == 2 and len(pts) == 50 and len(set(names)) == 50
    assert [n[:3] for n in names] == [f'p{i:02d}' for i in range(1, 51)]
    assert all('wflw' not in p for p in pts)                                     # chỉ số WFLW đã bỏ
    idx = [p['mp_idx'] for p in pts]
    assert len(set(idx)) == 50 and all(isinstance(i, int) and 0 <= i <= 477 for i in idx)
    by = {p['name']: p for p in pts}
    for p in pts:
        q = by[p['flip']]
        assert q['flip'] == p['name']
        assert (p['side'] == 'M') == (q is p) and (p['side'] == 'M' or {p['side'], q['side']} == {'R', 'L'})
        assert p['type'] in ('E', 'C') and (p['type'] == 'E') == (p['curve'] is None)
        assert p['line'] in cfg['lines']
        if p['curve'] is not None:
            assert all(c in by for c in p['curve']) and p['name'] in p['curve']        # curve = TÊN điểm, có chứa chính điểm đó
            assert len(p['curve']) >= 2
            if p['line'] != 'lip_inner':                                               # môi trong: đi qua khoé miệng ngoài (ghi ở make_config)
                assert all(by[c]['line'] == p['line'] for c in p['curve'])
        if p['coincide']:
            assert by[p['coincide']]['coincide'] == p['name']
    assert sum(p['side'] == 'R' for p in pts) == sum(p['side'] == 'L' for p in pts) == 21
    assert cfg['iod_points'] == ['p33_eye_R', 'p39_eye_L'] and by['p33_eye_R']['mp_idx'] == 33 and by['p39_eye_L']['mp_idx'] == 263
    assert cfg['t_flip'] is None and cfg['tolerance'] is None and cfg['status'].startswith('NHAP')   # P2 chốt 12/10, P3 tính 10/10


def test_inner_lip_curves_pass_through_outer_corners():
    by = {p['name']: p for p in mc.build_config()['points']}
    assert by['p49_lip_M']['curve'] == ['p41_lip_R', 'p49_lip_M', 'p45_lip_L'] and by['p50_lip_M']['curve'] == ['p45_lip_L', 'p50_lip_M', 'p41_lip_R']
    assert by['p34_eye_R']['curve'] == ['p33_eye_R', 'p34_eye_R', 'p35_eye_R'] and by['p36_eye_R']['curve'] == ['p35_eye_R', 'p36_eye_R', 'p33_eye_R']
    assert by['p28_nose_M']['curve'] == ['p28_nose_M', 'p29_nose_M'] and by['p31_nose_M']['curve'] == ['p30_nose_R', 'p31_nose_M', 'p32_nose_L']


def test_points_keep_names_order_and_definitions_of_legacy_config():
    """Tên, thứ tự, vùng, side, type, line, anchor, coincide, flip, lines và iod_points giữ nguyên so với config version 1 (P4, P5 đã dùng tên)."""
    old, new = load(LEGACY, 'm28_config_wflw.json'), mc.build_config()
    assert old['version'] == 1 and new['version'] == 2
    for key in ('name', 'region', 'side', 'flip', 'type', 'line', 'anchor', 'coincide'):
        assert [p[key] for p in old['points']] == [p[key] for p in new['points']], key
    assert old['lines'] == new['lines'] and old['iod_points'] == new['iod_points']


def test_committed_config_is_the_generated_one(committed):
    """config\\m28_config.json đã commit = SPEC hiện tại (chỉ khác tmpl, do dữ liệu ước lượng) và khớp map, hoán vị gương."""
    cfg = committed['cfg']
    fresh = mc.build_config(None, None, committed['mir']['perm'])
    strip = lambda c: [{k: v for k, v in p.items() if k != 'tmpl'} for p in c['points']]       # noqa: E731
    assert strip(cfg) == strip(fresh)
    assert {k: v for k, v in cfg.items() if k != 'points'} == {k: v for k, v in fresh.items() if k != 'points'}
    assert cfg['t_flip'] is None and cfg['tolerance'] is None


def test_committed_map_matches_config(committed):
    cfg, mp = committed['cfg'], committed['mp']
    assert mp['version'] == 2 and mp['kind'] == 'vertex' and 'mean478' not in mp
    assert mp['names'] == [p['name'] for p in cfg['points']]
    assert mp['points'] == {p['name']: {'mp_idx': p['mp_idx'], 'flip': p['flip']} for p in cfg['points']}
    assert 505 < mp['flip_width'] < 520                                           # ~512 lý thuyết, ước lượng trên dữ liệu thật
    assert mc.build_map(cfg, mp['flip_width'], mp['meta']) == mp                  # make_config sinh đúng file này
    out = mapping.apply_map(pts478(), mp, cfg)
    assert list(out) == mp['names']


def test_committed_tmpl_is_a_face_shaped_template(committed):
    cfg = committed['cfg']
    by = {p['name']: p for p in cfg['points']}
    for p in cfg['points']:                                                       # khuôn: R ở nửa trái ảnh, L ở nửa phải, M ở giữa
        assert p['tmpl'] is not None and len(p['tmpl']) == 2 and all(0 <= v <= 511 for v in p['tmpl'])
        q = by[p['flip']]
        if p['side'] == 'R':
            assert p['tmpl'][0] < q['tmpl'][0], (p['name'], p['tmpl'], q['tmpl'])
        if p['side'] == 'M':
            assert abs(p['tmpl'][0] - 256) < 30, (p['name'], p['tmpl'])
    ys = {r: [p['tmpl'][1] for p in cfg['points'] if p['region'] == r] for r in ('brow', 'eye', 'nose', 'lip', 'jaw')}
    assert np.mean(ys['brow']) < np.mean(ys['eye']) < np.mean(ys['nose']) < np.mean(ys['lip'])       # từ trán xuống cằm
    assert by['p09_jaw_M']['tmpl'][1] > by['p47_lip_M']['tmpl'][1] > by['p43_lip_M']['tmpl'][1]


def test_committed_label_matches_config(committed):
    assert make_label.build_labels(committed['cfg']) == committed['label']
    sub = committed['label'][0]['sublabels']
    assert [s['name'] for s in sub] == [p['name'] for p in committed['cfg']['points']]


# ---------- hoán vị gương ----------
def test_committed_mirror_is_involution_with_sure_pairs(committed):
    perm = committed['mir']['perm']
    assert len(perm) == 478 and mirror.check_involution(perm) == []
    assert all(perm[perm[i]] == i for i in range(478))
    for a, b in ((33, 263), (133, 362), (61, 291), (159, 386), (145, 374), (70, 300), (468, 473)):
        assert perm[a] == b and perm[b] == a
    for a in (1, 2, 0, 13, 14, 17, 152, 168):
        assert perm[a] == a
    assert mirror.sanity(perm) == []
    assert sorted(committed['mir']['fixed']) == [i for i in range(478) if perm[i] == i] and len(committed['mir']['fixed']) == committed['mir']['meta']['n_fixed']
    assert {perm[i] for i in range(469, 473)} == {474, 475, 476, 477}


def test_config_flip_pairs_match_mirror_and_side_m_points_are_on_the_axis(committed):
    perm, pts = committed['mir']['perm'], committed['cfg']['points']
    by = {p['name']: p for p in pts}
    for p in pts:
        assert perm[p['mp_idx']] == by[p['flip']]['mp_idx'], p['name']
        if p['side'] == 'M':
            assert perm[p['mp_idx']] == p['mp_idx'], p['name']
    assert {p['mp_idx'] for p in pts if p['side'] == 'M'} == {152, 168, 1, 2, 0, 17, 13, 14}


def test_build_config_rejects_flip_that_disagrees_with_mirror(committed):
    perm = list(committed['mir']['perm'])
    mc.build_config(None, None, perm)                                              # đúng: không lỗi
    bad = list(perm)
    a, b = perm[127], perm[93]                                                     # hoán hai cặp: p01<->p17 và p02<->p16 sai chéo
    bad[127], bad[93] = b, a
    with pytest.raises(AssertionError, match='p01_jaw_R'):
        mc.build_config(None, None, bad)
    off_axis = list(perm)
    off_axis[152], off_axis[148] = 148, 152                                        # cằm không còn nằm trên trục
    off_axis[377], off_axis[148] = 377, 148
    with pytest.raises(AssertionError):
        mc.build_config(None, None, off_axis)


def test_mirror_helpers():
    assert mirror.check_involution([1, 0, 2]) == []
    assert mirror.check_involution([1, 2, 0])                                     # vòng 3: không đối hợp
    assert mirror.check_involution([0, 0, 1])                                     # không phải hoán vị
    with pytest.raises(ValueError):
        mirror.load_mirror(os.path.join(LEGACY, 'm28_config_wflw.json'))          # không phải file hoán vị gương


# ---------- apply_map ----------
def test_apply_map_takes_the_right_vertices_in_config_order(committed):
    cfg, mp = committed['cfg'], committed['mp']
    pts = pts478(1)
    out = mapping.apply_map(pts, mp, cfg)
    assert list(out) == [p['name'] for p in cfg['points']]
    for p in cfg['points']:
        assert out[p['name']] == pts[p['mp_idx']].tolist()
    assert mapping.apply_map(pts.tolist(), mp, cfg) == out                         # nhận cả list


def test_apply_map_is_equivariant_under_similarity(committed):
    cfg, mp = committed['cfg'], committed['mp']
    pts = pts478(2)
    th = 0.4
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    a, b = mapping.apply_map(pts, mp, cfg), mapping.apply_map(1.3 * pts @ R.T + [7, -9], mp, cfg)
    assert list(a) == list(b)
    for n in a:
        assert np.allclose(np.array(a[n]) * 1.3 @ R.T + [7, -9], b[n], atol=1e-9)


def test_apply_map_flipped_is_unflip_and_rename(committed):
    cfg, mp = committed['cfg'], committed['mp']
    pts = pts478(3)
    names = [p['name'] for p in cfg['points']]
    idx = {p['name']: p['mp_idx'] for p in cfg['points']}
    flip = {p['name']: p['flip'] for p in cfg['points']}
    for width, expect in ((None, mp['flip_width']), (512, 512.0), (500.5, 500.5)):          # width ghi đè flip_width
        out = mapping.apply_map(pts, mp, cfg, flipped=True, width=width)
        assert list(out) == names
        for n in names:
            x, y = pts[idx[flip[n]]]                                              # điểm n bỏ lật = đỉnh của điểm đối xứng trên ảnh lật
            assert np.allclose(out[n], [expect - x, y])
    # ảnh lật của một mặt đối xứng hoàn hảo: nếu pts_lật[perm[i]] = (w - x_gốc[i], y) thì bỏ lật trả đúng điểm gốc
    perm = np.array(committed['mir']['perm'])
    w = mp['flip_width']
    flipped = np.empty_like(pts)
    flipped[perm] = np.stack([w - pts[:, 0], pts[:, 1]], axis=1)
    back, orig = mapping.apply_map(flipped, mp, cfg, flipped=True), mapping.apply_map(pts, mp, cfg)
    assert all(np.allclose(back[n], orig[n]) for n in names)


def test_apply_map_accepts_subset_config_and_rejects_changed_definition(committed):
    cfg, mp = committed['cfg'], committed['mp']
    pts = pts478(4)
    sub = copy.deepcopy(cfg)
    sub['points'] = [p for p in sub['points'] if p['region'] != 'brow']             # bỏ bớt điểm: không cần sinh lại map
    full, part = mapping.apply_map(pts, mp, cfg), mapping.apply_map(pts, mp, sub)
    assert list(part) == [p['name'] for p in sub['points']] and all(part[n] == full[n] for n in part)
    pf, ff = mapping.apply_map(pts, mp, sub, flipped=True), mapping.apply_map(pts, mp, cfg, flipped=True)
    assert all(pf[n] == ff[n] for n in pf)
    moved = copy.deepcopy(cfg)
    moved['points'][0]['mp_idx'] += 1                                              # đổi định nghĩa, giữ tên
    with pytest.raises(ValueError, match='mp_idx.*make_config'):
        mapping.apply_map(pts, mp, moved)
    reflip = copy.deepcopy(cfg)
    reflip['points'][0]['flip'] = 'p16_jaw_L'
    with pytest.raises(ValueError, match='flip'):
        mapping.apply_map(pts, mp, reflip)
    renamed = copy.deepcopy(cfg)
    renamed['points'][0]['name'] = 'khac'
    with pytest.raises(ValueError, match='khac'):
        mapping.apply_map(pts, mp, renamed)
    old_cfg = copy.deepcopy(cfg)
    del old_cfg['points'][0]['mp_idx']                                              # config kiểu cũ (chỉ số wflw)
    old_cfg['points'][0]['wflw'] = 0
    with pytest.raises(ValueError, match='mp_idx'):
        mapping.apply_map(pts, mp, old_cfg)


def test_apply_map_rejects_old_ridge_map_and_bad_shapes(committed):
    cfg, mp = committed['cfg'], committed['mp']
    ridge = load(LEGACY, 'map_mp50_wflw.json')
    with pytest.raises(ValueError, match='lỗi thời'):
        mapping.apply_map(pts478(), ridge, cfg)
    fake_old = copy.deepcopy(mp)
    fake_old['mean478'] = [[0, 0]] * 478                                           # dù có tên điểm đúng, có mean478 thì vẫn là map cũ
    with pytest.raises(ValueError, match='lỗi thời'):
        mapping.apply_map(pts478(), fake_old, cfg)
    for bad in (np.zeros((10, 2)), np.zeros((478, 3)), np.zeros(478)):
        with pytest.raises(ValueError, match='478'):
            mapping.apply_map(bad, mp, cfg)
    nan = pts478()
    nan[5, 0] = np.nan
    with pytest.raises(ValueError, match='NaN'):
        mapping.apply_map(nan, mp, cfg)
    with pytest.raises(ValueError):
        mapping.apply_map(pts478(), {'version': 2, 'kind': 'vertex'}, cfg)


# ---------- make_config: ước lượng từ dữ liệu ----------
def test_learn_mirror_flip_recovers_permutation_and_flip_width(committed):
    perm = np.array(committed['mir']['perm'])
    origs, flips = synthetic_run(perm)
    res = mirror.learn_mirror_flip(origs, flips, 511.3)
    assert res['perm'] == perm.tolist() and mirror.sanity(res['perm']) == []
    assert res['meta']['n_faces'] == 40 and res['meta']['n_fixed'] == len(committed['mir']['fixed'])
    fw = mc.estimate_flip_width(origs, flips, perm, [p['mp_idx'] for p in committed['cfg']['points']])
    assert abs(fw['w'] - 511.3) < 0.1 and abs(fw['dy_mean']) < 0.1 and fw['n_faces'] == 40 and abs(fw['w_all478'] - 511.3) < 0.1
    with pytest.raises(ValueError):
        mirror.learn_mirror_flip([], [], 512.0)


def test_learn_mirror_from_mean_shape_recovers_permutation_on_symmetric_faces(committed):
    perm = np.array(committed['mir']['perm'])
    origs, _ = synthetic_run(perm, n=30)
    res = mirror.learn_mirror(origs)
    assert res['perm'] == perm.tolist()
    assert res['meta']['resid_median_pct_iod'] < 5


def test_mesh_refinement_fixes_ambiguous_pairs_using_edges():
    perm_true = np.arange(478)
    for a, b in ((10, 11), (20, 21)):
        perm_true[a], perm_true[b] = b, a
    edges = np.array([(10, 12), (11, 12), (20, 22), (21, 22), (10, 20), (11, 21)])
    assert mirror.violations(perm_true, edges) == 0
    wrong = perm_true.copy()
    wrong[10], wrong[21], wrong[11], wrong[20] = 21, 10, 20, 11                     # ghép chéo: 10<->21, 11<->20
    assert mirror.check_involution(wrong) == [] and mirror.violations(wrong, edges) > 0
    S = np.full((478, 478), 1.0)
    np.fill_diagonal(S, 0.0)
    for i, j in ((10, 21), (11, 20)):
        S[i, j] = S[j, i] = 0.0                                                      # hình học ưu ái cặp chéo (sai)
    for i, j in ((10, 11), (20, 21)):
        S[i, j] = S[j, i] = 0.001
    fixed = mirror.refine_with_mesh(wrong, S, edges, mu=0.03)
    assert fixed[10] == 11 and fixed[20] == 21 and mirror.violations(fixed, edges) == 0 and mirror.check_involution(fixed) == []


def write_manifest(tmp_path, names, pose='0', set_name='F', yaw=None):
    import csv
    p = tmp_path / 'manifest.csv'
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['file', 'set', 'pose', 'yaw'])
        for i, n in enumerate(names):
            w.writerow([n + '.png', set_name, pose, yaw[i] if yaw else 0])
    return str(p)


def test_select_faces_filters_by_set_pose_flip_and_yaw():
    rows = [dict(file='F_001.png', set='F', pose='0', yaw='3'), dict(file='F_002.png', set='F', pose='1', yaw='3'),
            dict(file='F_003.png', set='Tdev', pose='0', yaw='3'), dict(file='F_004.png', set='F', pose='0', yaw='25'),
            dict(file='F_005.png', set='F', pose='0', yaw='1'), dict(file='F_006.png', set='F', pose='0', yaw='')]
    pred = {n: {'orig': [], 'flip': [[0, 0]]} for n in ('F_001', 'F_002', 'F_003', 'F_004', 'F_006')}
    pred['F_005'] = {'orig': [], 'flip': None}                                       # không có ảnh lật
    assert mc.select_faces(rows, pred, 'F') == ['F_001', 'F_004', 'F_006']
    assert mc.select_faces(rows, pred, 'F', max_yaw=12) == ['F_001', 'F_006']       # yaw trống: không lọc


def test_main_without_run_regenerates_files_and_keeps_numbers_others_wrote(tmp_path, committed):
    out, mp_out, mir = tmp_path / 'c.json', tmp_path / 'm.json', tmp_path / 'mir.json'
    mir.write_text(json.dumps(committed['mir']), encoding='utf-8')
    base = ['--out', str(out), '--map-out', str(mp_out), '--mirror', str(mir)]
    assert mc.main(base) == 0                                                         # chưa có file cũ: flip_width đặt 512, chưa có tmpl
    cfg = load(str(out))
    assert cfg['points'][0]['tmpl'] is None and load(str(mp_out))['flip_width'] == 512.0
    cfg['t_flip'], cfg['tolerance'], cfg['status'] = 0.07, {'jaw': 3.0}, 'DONG BANG 12/10'
    cfg['points'][0]['tmpl'] = [1.5, 2.5]
    out.write_text(json.dumps(cfg), encoding='utf-8')
    m = load(str(mp_out))
    m['flip_width'] = 513.25
    mp_out.write_text(json.dumps(m), encoding='utf-8')
    assert mc.main(base) == 0                                                         # chạy lại: không xoá số người khác đã ghi
    again, mp2 = load(str(out)), load(str(mp_out))
    assert again['t_flip'] == 0.07 and again['tolerance'] == {'jaw': 3.0} and again['status'] == 'DONG BANG 12/10'
    assert again['points'][0]['tmpl'] == [1.5, 2.5] and mp2['flip_width'] == 513.25
    mc.main(base + ['--t-flip', '0.09'])                                              # --t-flip mới thì ghi đè
    assert load(str(out))['t_flip'] == 0.09
    gt = tmp_path / 'gt50.json'
    mc.main(base + ['--gt50', str(gt)])
    assert load(str(gt)) == {}                                                        # chỉ file mẫu rỗng: đáp án nay từ CVAT


def test_main_without_run_needs_mirror_file(tmp_path):
    with pytest.raises(SystemExit):
        mc.main(['--out', str(tmp_path / 'c.json'), '--map-out', str(tmp_path / 'm.json'), '--mirror', str(tmp_path / 'khong_co.json')])


def test_main_with_run_estimates_mirror_flip_width_and_template(tmp_path, monkeypatch, committed):
    perm = np.array(committed['mir']['perm'])
    names = [f'F_{i + 1:03d}' for i in range(40)]
    origs, flips = synthetic_run(perm, n=40, w=513.2)
    rd = tmp_path / 'runs' / 'R' / 'mediapipe'
    rd.mkdir(parents=True)
    (rd / 'pred478.json').write_text(json.dumps({n: {'orig': o.tolist(), 'flip': f.tolist()} for n, o, f in zip(names, origs, flips)}), encoding='utf-8')
    man = write_manifest(tmp_path, names)
    monkeypatch.chdir(tmp_path)
    args = ['--run', 'R', '--manifest', man, '--no-mesh', '--out', 'c.json', '--map-out', 'm.json', '--mirror', 'mir.json']
    assert mc.main(args) == 0
    cfg, mp, mir = load('c.json'), load('m.json'), load('mir.json')
    assert mir['perm'] == perm.tolist() and abs(mp['flip_width'] - 513.2) < 0.2
    assert mp['meta']['tmpl_faces'] == 40 and 'flip_dy_mean' in mp['meta']
    mean50 = np.mean([[o[p['mp_idx']] for p in cfg['points']] for o in origs], axis=0)       # tmpl = trung bình dự đoán của các mặt thẳng
    assert np.abs(np.array([p['tmpl'] for p in cfg['points']]) - mean50).max() < 0.01 + 1e-9
    few = tmp_path / 'few'
    few.mkdir()
    monkeypatch.chdir(few)
    (few / 'runs' / 'R' / 'mediapipe').mkdir(parents=True)
    (few / 'runs' / 'R' / 'mediapipe' / 'pred478.json').write_text(json.dumps({'F_001': {'orig': origs[0].tolist(), 'flip': flips[0].tolist()}}), encoding='utf-8')
    with pytest.raises(SystemExit, match='>= 30'):                                    # quá ít mặt thẳng: dừng, không ghi bậy
        mc.main(['--run', 'R', '--manifest', write_manifest(few, ['F_001']), '--no-mesh', '--out', 'c.json', '--map-out', 'm.json', '--mirror', 'mir.json'])


def test_template_needs_faces(committed):
    with pytest.raises(ValueError):
        mc.template(committed['cfg'], committed['mp'], [])
    t = mc.template(committed['cfg'], committed['mp'], [pts478(5), pts478(6)])
    assert t.shape == (50, 2)


def test_rerunning_make_config_keeps_values_others_wrote_and_drops_old_version():
    new = mc.build_config(np.arange(100, dtype=float).reshape(50, 2))
    old = json.loads(json.dumps(new))
    old['t_flip'], old['tolerance'], old['status'] = 0.07, {'jaw': 3.0}, 'DONG BANG 12/10'
    fresh = mc.build_config()                                                          # chạy lại không kèm tmpl, t_flip
    kept = mc.keep_existing(fresh, old, t_flip_given=False)
    assert set(kept) == {'t_flip', 'tolerance', 'status', 'tmpl'}
    assert fresh['t_flip'] == 0.07 and fresh['tolerance'] == {'jaw': 3.0} and fresh['points'][0]['tmpl'] == [0.0, 1.0]
    forced = mc.keep_existing(mc.build_config(), old, t_flip_given=True)               # --t-flip mới thì không giữ số cũ
    assert 't_flip' not in forced
    v1 = load(LEGACY, 'm28_config_wflw.json')                                          # tmpl của version 1 là hình học WFLW: không được mang sang
    assert mc.keep_existing(mc.build_config(), v1, False) == []
    assert mc.build_config()['points'][0]['tmpl'] is None
    with pytest.raises(AssertionError):
        mc.build_config(np.zeros((10, 2)))
