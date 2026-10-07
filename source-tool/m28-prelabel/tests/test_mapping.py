"""Thử config version 3 (50 điểm DMS, QĐ-003, chọn đỉnh MediaPipe), hoán vị gương, apply_map và make_config bằng dữ liệu giả + file ĐÃ COMMIT (không dùng mặt thật).

Kiểm trên dữ liệu thật (check_flip.py, check_drivface.py) không nằm trong pytest.
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
OLD_V1_CFG = dict(version=1, points=[dict(name=f'p{i:02d}_eye_R', side='R', tmpl=[1.0, 2.0]) for i in range(1, 51)])      # config version 1 (định nghĩa 98 điểm cũ), chỉ để kiểm từ chối
GROUPS = ['longmaytrai', 'longmayphai', 'songmui', 'mattrai', 'matphai', 'moingoai', 'moitrong']
COUNTS = [5, 5, 4, 8, 8, 12, 8]
M_NAMES = {'songmui_1', 'songmui_2', 'songmui_3', 'songmui_4', 'moingoai_4', 'moingoai_10', 'moitrong_3', 'moitrong_7'}


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


# ---------- config version 3 (50 điểm DMS) ----------
def test_build_config_v3_structure():
    cfg = mc.build_config()
    pts = cfg['points']
    names = [p['name'] for p in pts]
    assert cfg['version'] == 3 and len(pts) == 50 == cfg['n_points'] and len(set(names)) == 50
    assert cfg['side_convention'] == 'image' and 'BUC ANH' in cfg['side_note']
    # đúng 7 nhóm với số điểm 5/5/4/8/8/12/8, đúng thứ tự nhóm, tên <nhóm>_<k> liên tục từ 1 không đệm số 0
    assert list(dict.fromkeys(p['group'] for p in pts)) == GROUPS
    assert [sum(p['group'] == g for p in pts) for g in GROUPS] == COUNTS
    assert names == [f'{g}_{k}' for g, n in zip(GROUPS, COUNTS) for k in range(1, n + 1)]
    assert all(p['name'] == f"{p['group']}_{i}" for g in GROUPS for i, p in enumerate([q for q in pts if q['group'] == g], 1))
    assert not [p for p in pts if 'jaw' in p['region'] or 'jaw' in p['name'] or 'mp_idx' not in p]   # không viền hàm/cằm, mọi điểm là một đỉnh MediaPipe
    assert {p['region'] for p in pts} == {'brow', 'nose', 'eye', 'lip'}                                # vùng thô, không còn jaw
    assert {p['group']: p['region'] for p in pts} == {'longmaytrai': 'brow', 'longmayphai': 'brow', 'songmui': 'nose', 'mattrai': 'eye', 'matphai': 'eye',
                                                       'moingoai': 'lip', 'moitrong': 'lip'}
    assert all(p['line'] == p['group'] for p in pts)
    assert {k: v['closed'] for k, v in cfg['lines'].items()} == {'longmaytrai': False, 'longmayphai': False, 'songmui': False, 'mattrai': True, 'matphai': True,
                                                                  'moingoai': True, 'moitrong': True}
    assert 'head' not in json.dumps(cfg).lower() and not [k for k in cfg if 'box' in k]               # không khung đầu, không trường dự phòng
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
            assert all(c in by for c in p['curve']) and p['name'] in p['curve']                       # curve = TÊN điểm, có chứa chính điểm đó
            assert len(p['curve']) >= 2
            assert all(by[c]['line'] == p['line'] for c in p['curve'])                                 # mọi curve nằm trong đúng line (không còn ngoại lệ môi trong)
        if p['coincide']:
            assert by[p['coincide']]['coincide'] == p['name']
    # bên theo BỨC ẢNH: *trai = L (nửa trái ảnh), *phai = R (nửa phải ảnh); M = trên trục
    assert {p['name'] for p in pts if p['side'] == 'M'} == M_NAMES
    for g in ('longmaytrai', 'mattrai'):
        assert {p['side'] for p in pts if p['group'] == g} == {'L'}
    for g in ('longmayphai', 'matphai'):
        assert {p['side'] for p in pts if p['group'] == g} == {'R'}
    assert sum(p['side'] == 'R' for p in pts) == sum(p['side'] == 'L' for p in pts) == 21 and sum(p['side'] == 'M' for p in pts) == 8
    assert cfg['iod_points'] == ['mattrai_1', 'matphai_1'] and by['mattrai_1']['mp_idx'] == 33 and by['matphai_1']['mp_idx'] == 263
    assert cfg['t_flip'] is None and cfg['tolerance'] is None and cfg['status'].startswith('NHAP')   # P2 chốt 12/10, P3 tính 10/10


def test_flip_pairs_follow_the_naming_convention():
    by = {p['name']: p for p in mc.build_config()['points']}
    for a, b in (('longmaytrai', 'longmayphai'), ('mattrai', 'matphai')):
        n = 5 if 'may' in a else 8
        assert all(by[f'{a}_{k}']['flip'] == f'{b}_{k}' and by[f'{b}_{k}']['flip'] == f'{a}_{k}' for k in range(1, n + 1))
    assert all(by[f'songmui_{k}']['flip'] == f'songmui_{k}' for k in range(1, 5))
    for g, pairs, selfs in (('moingoai', ((1, 7), (2, 6), (3, 5), (8, 12), (9, 11)), (4, 10)), ('moitrong', ((1, 5), (2, 4), (6, 8)), (3, 7))):
        assert all(by[f'{g}_{a}']['flip'] == f'{g}_{b}' and by[f'{g}_{b}']['flip'] == f'{g}_{a}' for a, b in pairs)
        assert all(by[f'{g}_{k}']['flip'] == f'{g}_{k}' and by[f'{g}_{k}']['side'] == 'M' for k in selfs)
    side = {'moingoai': 'LLLMRRRRRMLL', 'moitrong': 'LLMRRRML'}                                          # theo BỨC ẢNH: đánh số từ khoé trái ảnh, mép trên trái -> phải, mép dưới phải -> trái
    for g, want in side.items():
        assert ''.join(by[f'{g}_{k}']['side'] for k in range(1, len(want) + 1)) == want, g


def test_types_curves_anchors_and_coincide_follow_the_rules():
    by = {p['name']: p for p in mc.build_config()['points']}
    e_names = {'longmaytrai_1', 'longmaytrai_5', 'longmayphai_1', 'longmayphai_5', 'songmui_1', 'songmui_4', 'mattrai_1', 'mattrai_5', 'matphai_1', 'matphai_5',
               'moingoai_1', 'moingoai_7', 'moitrong_1', 'moitrong_5'}
    assert {n for n, p in by.items() if p['type'] == 'E'} == e_names
    assert by['longmaytrai_3']['curve'] == [f'longmaytrai_{k}' for k in range(1, 6)] and by['songmui_2']['curve'] == [f'songmui_{k}' for k in range(1, 5)]
    for g in ('mattrai', 'matphai'):
        assert by[f'{g}_3']['curve'] == [f'{g}_{k}' for k in (1, 2, 3, 4, 5)]                         # mí trên: khoé ngoài -> khoé trong
        assert by[f'{g}_7']['curve'] == [f'{g}_{k}' for k in (5, 6, 7, 8, 1)]                         # mí dưới: khoé trong -> ... -> khoé ngoài
    assert by['moingoai_4']['curve'] == [f'moingoai_{k}' for k in range(1, 8)]
    assert by['moingoai_10']['curve'] == [f'moingoai_{k}' for k in (7, 8, 9, 10, 11, 12, 1)]
    assert by['moitrong_3']['curve'] == [f'moitrong_{k}' for k in range(1, 6)] and by['moitrong_7']['curve'] == [f'moitrong_{k}' for k in (5, 6, 7, 8, 1)]
    assert {n for n, p in by.items() if p['anchor']} == {'longmaytrai_1', 'longmaytrai_5', 'longmayphai_1', 'longmayphai_5', 'songmui_1', 'songmui_4', 'mattrai_1', 'mattrai_5',
                                                         'matphai_1', 'matphai_5', 'moingoai_1', 'moingoai_4', 'moingoai_7', 'moingoai_10', 'moitrong_1', 'moitrong_3',
                                                         'moitrong_5', 'moitrong_7'}
    pairs = {(a, b) for g in ('mattrai', 'matphai', 'moitrong') for a, b in ((2, 8), (3, 7), (4, 6)) for a, b in ((f'{g}_{a}', f'{g}_{b}'),)}
    assert {(n, p['coincide']) for n, p in by.items() if p['coincide'] and n < p['coincide']} == pairs
    assert sum(1 for p in by.values() if p['coincide']) == 18 and not [p for n, p in by.items() if p['group'] in ('moingoai', 'songmui') and p['coincide']]


def test_names_sort_by_config_order_not_by_string():
    names = [p['name'] for p in mc.build_config()['points']]
    assert sorted(names) != names and 'moingoai_10' < 'moingoai_2'                                    # so chuỗi sai thứ tự: mọi chỗ code dùng thứ tự config
    assert names.index('moingoai_2') < names.index('moingoai_10')


def test_v3_replaces_v2_and_reverses_the_side_convention():
    """Định nghĩa mới thay hẳn 50 điểm cũ: không tên nào của config version 1 còn lại; đỉnh 33 (khoé ngoài mắt PHẢI của người, nửa trái ảnh khi ảnh không lật) trước là side R (theo người),
    nay là mattrai_1 side L (theo ảnh)."""
    old, new = copy.deepcopy(OLD_V1_CFG), mc.build_config()
    assert old['version'] == 1 and new['version'] == 3
    assert not {p['name'] for p in old['points']} & {p['name'] for p in new['points']}
    assert [p for p in old['points'] if p['name'] == 'p33_eye_R'][0]['side'] == 'R'                    # v1/v2: R = nửa trái ảnh
    v33 = [p for p in new['points'] if p['mp_idx'] == 33][0]
    assert v33['name'] == 'mattrai_1' and v33['side'] == 'L'                                             # v3: nửa trái ảnh = L
    assert 'side_convention' not in old and new['side_convention'] == 'image'


def test_committed_config_is_the_generated_one(committed):
    """config\\m28_config.json đã commit = SPEC hiện tại (chỉ khác tmpl, do dữ liệu ước lượng) và khớp map, hoán vị gương."""
    cfg = committed['cfg']
    fresh = mc.build_config(None, None, committed['mir']['perm'])
    strip = lambda c: [{k: v for k, v in p.items() if k != 'tmpl'} for p in c['points']]       # noqa: E731
    assert strip(cfg) == strip(fresh)
    assert {k: v for k, v in cfg.items() if k != 'points'} == {k: v for k, v in fresh.items() if k != 'points'}
    assert cfg['t_flip'] is None and cfg['tolerance'] is None and cfg['version'] == 3


def test_committed_map_matches_config(committed):
    cfg, mp = committed['cfg'], committed['mp']
    assert mp['version'] == 3 and mp['kind'] == 'vertex' and 'mean478' not in mp and mp['meta']['config_version'] == 3
    assert mp['names'] == [p['name'] for p in cfg['points']]
    assert mp['points'] == {p['name']: {'mp_idx': p['mp_idx'], 'flip': p['flip']} for p in cfg['points']}
    assert 505 < mp['flip_width'] < 520                                           # ~512 lý thuyết, ước lượng trên dữ liệu thật
    assert mc.build_map(cfg, mp['flip_width'], mp['meta']) == mp                  # make_config sinh đúng file này
    out = mapping.apply_map(pts478(), mp, cfg)
    assert list(out) == mp['names']


def test_committed_tmpl_is_a_face_shaped_template(committed):
    cfg = committed['cfg']
    by = {p['name']: p for p in cfg['points']}
    for p in cfg['points']:                                                       # khuôn: nhóm *trai (side L) ở nửa trái, *phai (side R) ở nửa phải, M ở giữa
        assert p['tmpl'] is not None and len(p['tmpl']) == 2 and all(0 <= v <= 511 for v in p['tmpl'])
        q = by[p['flip']]
        if p['side'] == 'L':
            assert p['tmpl'][0] < q['tmpl'][0], (p['name'], p['tmpl'], q['tmpl'])
            assert p['tmpl'][0] < 256 if p['group'] in ('longmaytrai', 'mattrai') else True
        if p['side'] == 'R' and p['group'] in ('longmayphai', 'matphai'):
            assert p['tmpl'][0] > 256
        if p['side'] == 'M':
            assert abs(p['tmpl'][0] - 256) < 30, (p['name'], p['tmpl'])
    for g in ('longmaytrai', 'mattrai'):
        assert max(p['tmpl'][0] for p in cfg['points'] if p['group'] == g) < min(p['tmpl'][0] for p in cfg['points'] if p['group'] == g.replace('trai', 'phai'))
    ys = {r: [p['tmpl'][1] for p in cfg['points'] if p['region'] == r] for r in ('brow', 'eye', 'nose', 'lip')}
    assert np.mean(ys['brow']) < np.mean(ys['eye']) < np.mean(ys['nose']) < np.mean(ys['lip'])       # từ trán xuống miệng
    assert by['moingoai_10']['tmpl'][1] > by['moingoai_4']['tmpl'][1]                                   # mép dưới thấp hơn mép trên
    assert by['songmui_1']['tmpl'][1] < by['songmui_2']['tmpl'][1] < by['songmui_3']['tmpl'][1] < by['songmui_4']['tmpl'][1] < by['moingoai_4']['tmpl'][1]   # sống mũi từ gốc xuống chóp


def test_committed_label_matches_config(committed):
    assert make_label.build_labels(committed['cfg']) == committed['label']
    assert [lb['name'] for lb in committed['label']] == GROUPS                                   # bảy label skeleton, mỗi nhóm một
    sub = [s for lb in committed['label'] for s in lb['sublabels']]
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
    assert {p['mp_idx'] for p in pts if p['side'] == 'M'} == {168, 197, 5, 1, 0, 17, 13, 14}
    assert all(perm[p['mp_idx']] != p['mp_idx'] for p in pts if p['side'] != 'M')                        # điểm trái/phải không nằm trên trục


def test_build_config_rejects_flip_that_disagrees_with_mirror(committed):
    perm = list(committed['mir']['perm'])
    mc.build_config(None, None, perm)                                              # đúng: không lỗi
    bad = list(perm)
    a, b = perm[107], perm[66]                                                     # hoán hai cặp: longmaytrai_1<->longmayphai_1 và _2<->_2 sai chéo
    bad[107], bad[66] = b, a
    with pytest.raises(AssertionError, match='longmaytrai_1'):
        mc.build_config(None, None, bad)
    off_axis = [int(v) for v in mirror._swap_partners(np.asarray(perm), 1, 4)]    # chóp mũi (đỉnh 1) ghép với đỉnh 4: songmui_4 side M không còn trên trục
    assert mirror.check_involution(off_axis) == [] and off_axis[1] != 1
    with pytest.raises(AssertionError):
        mc.build_config(None, None, off_axis)


def test_mirror_helpers():
    assert mirror.check_involution([1, 0, 2]) == []
    assert mirror.check_involution([1, 2, 0])                                     # vòng 3: không đối hợp
    assert mirror.check_involution([0, 0, 1])                                     # không phải hoán vị
    with pytest.raises(ValueError):
        mirror.load_mirror(os.path.join(COMMITTED, 'm28_config.json'))          # không phải file hoán vị gương


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


def test_apply_map_keeps_names_on_the_right_side_of_a_frontal_face_even_when_unflipped(committed):
    """Mặt giả nhìn thẳng (x tăng sang phải ảnh): mattrai, longmaytrai, nửa trái của môi có x nhỏ hơn bên phải; bỏ lật bằng apply_map(flipped=True) vẫn đúng bên."""
    cfg, mp = committed['cfg'], committed['mp']
    by = {p['name']: p for p in cfg['points']}
    origs, flips = synthetic_run(np.array(committed['mir']['perm']), n=2, w=mp['flip_width'])
    for o, f in zip(origs, flips):
        for pts in (mapping.apply_map(o, mp, cfg), mapping.apply_map(f, mp, cfg, flipped=True)):
            for n, p in by.items():
                if p['side'] == 'L':
                    assert pts[n][0] < pts[p['flip']][0], n                       # điểm side L (nửa trái ảnh) có x nhỏ hơn điểm đối xứng side R
            assert max(pts[n][0] for n in pts if by[n]['group'] in ('mattrai', 'longmaytrai')) < min(pts[n][0] for n in pts if by[n]['group'] in ('matphai', 'longmayphai'))
            assert pts['mattrai_1'][0] < pts['songmui_1'][0] < pts['matphai_1'][0]
            assert all(abs(pts[n][0] - mp['flip_width'] / 2) < 3 for n in M_NAMES)    # điểm side M nằm trên trục dọc của mặt giả


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
    reflip['points'][0]['flip'] = 'longmayphai_2'
    with pytest.raises(ValueError, match='flip'):
        mapping.apply_map(pts, mp, reflip)
    renamed = copy.deepcopy(cfg)
    renamed['points'][0]['name'] = 'khac'
    with pytest.raises(ValueError, match='khac'):
        mapping.apply_map(pts, mp, renamed)
    old_cfg = copy.deepcopy(cfg)
    del old_cfg['points'][0]['mp_idx']                                              # config kiểu cũ (không có chỉ số đỉnh MediaPipe)
    with pytest.raises(ValueError, match='mp_idx'):
        mapping.apply_map(pts, mp, old_cfg)


def test_apply_map_rejects_old_ridge_map_v2_map_and_v2_config(committed):
    cfg, mp = committed['cfg'], committed['mp']
    ridge = dict(version=1, mean478=[[0.0, 0.0]] * 478, points={})                  # map ridge cũ (có mean478)
    with pytest.raises(ValueError, match='không còn hỗ trợ'):
        mapping.apply_map(pts478(), ridge, cfg)
    fake_old = copy.deepcopy(mp)
    fake_old['mean478'] = [[0, 0]] * 478                                           # dù có tên điểm đúng, có mean478 thì vẫn là map cũ
    with pytest.raises(ValueError, match='không còn hỗ trợ'):
        mapping.apply_map(pts478(), fake_old, cfg)
    # map version 2 (cùng cấu trúc, 50 điểm pNN_vùng_bên của QĐ-002) + config version 3: từ chối rõ, gợi ý chạy lại make_config
    v2_map = {'version': 2, 'kind': 'vertex', 'names': [f'p{i:02d}_eye_R' for i in range(1, 51)],
              'points': {f'p{i:02d}_eye_R': {'mp_idx': i, 'flip': f'p{i:02d}_eye_R'} for i in range(1, 51)}, 'flip_width': 513.0, 'meta': {}}
    with pytest.raises(ValueError, match=r'version 2.*QĐ-003.*make_config'):
        mapping.apply_map(pts478(), v2_map, cfg)
    # config version 2 (không có side_convention) + map version 3: từ chối, nói rõ quy ước bên đã đổi
    v2_cfg = copy.deepcopy(cfg)
    del v2_cfg['side_convention']
    with pytest.raises(ValueError, match=r'side_convention.*QĐ-003.*make_config'):
        mapping.apply_map(pts478(), mp, v2_cfg)
    v2_cfg['side_convention'] = 'person'
    with pytest.raises(ValueError, match='side_convention'):
        mapping.apply_map(pts478(), mp, v2_cfg)
    for bad in (np.zeros((10, 2)), np.zeros((478, 3)), np.zeros(478)):
        with pytest.raises(ValueError, match='478'):
            mapping.apply_map(bad, mp, cfg)
    nan = pts478()
    nan[5, 0] = np.nan
    with pytest.raises(ValueError, match='NaN'):
        mapping.apply_map(nan, mp, cfg)
    with pytest.raises(ValueError):
        mapping.apply_map(pts478(), {'version': 3, 'kind': 'vertex'}, cfg)


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


def test_check_against_data_reports_agreement_without_writing(committed):
    perm = np.array(committed['mir']['perm'])
    origs, flips = synthetic_run(perm, n=30)
    ok = mirror.check_against_data(perm, origs, flips)
    assert ok['n_diff'] == 0 and ok['diff'] == [] and ok['n_faces'] == 30 and ok['resid_median_pct_iod'] < 2 and ok['n_fixed_learned'] == len(committed['mir']['fixed'])
    wrong = mirror._swap_partners(perm, 107, 66)                                    # hoán vị có hai cặp ghép sai: phải thấy khác
    bad = mirror.check_against_data(wrong, origs, flips)
    assert bad['n_diff'] > 0 and set(bad['diff']) & {107, 66} and bad['resid_max_pct_iod'] > ok['resid_max_pct_iod']


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
    assert cfg['points'][0]['tmpl'] is None and load(str(mp_out))['flip_width'] == 512.0 and cfg['version'] == 3 and load(str(mp_out))['version'] == 3
    cfg['t_flip'], cfg['tolerance'], cfg['status'] = 0.07, {'eye': 3.0}, 'DONG BANG 12/10'
    cfg['points'][0]['tmpl'] = [1.5, 2.5]
    out.write_text(json.dumps(cfg), encoding='utf-8')
    m = load(str(mp_out))
    m['flip_width'] = 513.25
    mp_out.write_text(json.dumps(m), encoding='utf-8')
    assert mc.main(base) == 0                                                         # chạy lại: không xoá số người khác đã ghi
    again, mp2 = load(str(out)), load(str(mp_out))
    assert again['t_flip'] == 0.07 and again['tolerance'] == {'eye': 3.0} and again['status'] == 'DONG BANG 12/10'
    assert again['points'][0]['tmpl'] == [1.5, 2.5] and mp2['flip_width'] == 513.25
    mc.main(base + ['--t-flip', '0.09'])                                              # --t-flip mới thì ghi đè
    assert load(str(out))['t_flip'] == 0.09
    assert mir.read_text(encoding='utf-8') == json.dumps(committed['mir'])            # không --run: file gương không bị đụng
    gt = tmp_path / 'gt50.json'
    mc.main(base + ['--gt50', str(gt)])
    assert load(str(gt)) == {}                                                        # chỉ file mẫu rỗng: đáp án nay từ CVAT


def test_main_without_run_needs_mirror_file(tmp_path):
    with pytest.raises(SystemExit):
        mc.main(['--out', str(tmp_path / 'c.json'), '--map-out', str(tmp_path / 'm.json'), '--mirror', str(tmp_path / 'khong_co.json')])


def make_run(tmp_path, monkeypatch, committed, n=40, w=513.2, name='R'):
    perm = np.array(committed['mir']['perm'])
    names = [f'F_{i + 1:03d}' for i in range(n)]
    origs, flips = synthetic_run(perm, n=n, w=w)
    rd = tmp_path / 'runs' / name / 'mediapipe'
    rd.mkdir(parents=True)
    (rd / 'pred478.json').write_text(json.dumps({k: {'orig': o.tolist(), 'flip': f.tolist()} for k, o, f in zip(names, origs, flips)}), encoding='utf-8')
    man = write_manifest(tmp_path, names)
    monkeypatch.chdir(tmp_path)
    return perm, origs, flips, man


def test_main_with_run_estimates_flip_width_and_template_and_keeps_the_mirror_file(tmp_path, monkeypatch, committed, capsys):
    perm, origs, flips, man = make_run(tmp_path, monkeypatch, committed)
    (tmp_path / 'mir.json').write_text(json.dumps(committed['mir']), encoding='utf-8')
    before = (tmp_path / 'mir.json').read_bytes()
    args = ['--run', 'R', '--manifest', man, '--no-mesh', '--out', 'c.json', '--map-out', 'm.json', '--mirror', 'mir.json']
    assert mc.main(args) == 0
    out = capsys.readouterr().out
    cfg, mp = load('c.json'), load('m.json')
    assert (tmp_path / 'mir.json').read_bytes() == before                             # --run KHÔNG ghi đè hoán vị gương khi không yêu cầu
    assert 'GIỮ NGUYÊN' in out and 'khác file ở 0/478 đỉnh' in out
    assert abs(mp['flip_width'] - 513.2) < 0.2 and mp['version'] == 3 and mp['meta']['config_version'] == 3
    assert mp['meta']['tmpl_faces'] == 40 and 'flip_dy_mean' in mp['meta']
    mean50 = np.mean([[o[p['mp_idx']] for p in cfg['points']] for o in origs], axis=0)       # tmpl = trung bình dự đoán của các mặt thẳng
    assert np.abs(np.array([p['tmpl'] for p in cfg['points']]) - mean50).max() < 0.01 + 1e-9
    assert mirror.load_mirror('mir.json')['perm'] == perm.tolist()


def test_main_with_run_learn_mirror_overwrites_only_when_asked(tmp_path, monkeypatch, committed, capsys):
    perm, _, _, man = make_run(tmp_path, monkeypatch, committed)
    marker = dict(committed['mir'], meta={'marker': 'cu'})
    (tmp_path / 'mir.json').write_text(json.dumps(marker), encoding='utf-8')
    base = ['--run', 'R', '--manifest', man, '--no-mesh', '--out', 'c.json', '--map-out', 'm.json', '--mirror', 'mir.json']
    mc.main(base)
    assert load('mir.json')['meta'] == {'marker': 'cu'}                               # mặc định giữ nguyên, kể cả meta
    assert mc.main(base + ['--learn-mirror']) == 0
    learned = load('mir.json')
    assert learned['perm'] == perm.tolist() and learned['meta']['n_faces'] == 40 and 'marker' not in learned['meta']      # --learn-mirror: học lại và ghi đè
    assert 'HỌC LẠI và ghi đè' in capsys.readouterr().out
    with pytest.raises(SystemExit):                                                   # --learn-mirror không có --run: argparse từ chối
        mc.main(['--learn-mirror', '--out', 'c2.json', '--map-out', 'm2.json', '--mirror', 'mir.json'])
    os.remove('mir.json')
    with pytest.raises(SystemExit, match='learn-mirror'):                             # --run mà thiếu file gương: nói rõ cách xử lý, không tự học
        mc.main(base)
    assert not os.path.exists('mir.json')


def test_main_with_run_needs_enough_straight_faces(tmp_path, monkeypatch, committed):
    perm, origs, flips, _ = make_run(tmp_path, monkeypatch, committed, n=1)
    (tmp_path / 'mir.json').write_text(json.dumps(committed['mir']), encoding='utf-8')
    with pytest.raises(SystemExit, match='>= 30'):                                    # quá ít mặt thẳng: dừng, không ghi bậy
        mc.main(['--run', 'R', '--manifest', write_manifest(tmp_path, ['F_001']), '--no-mesh', '--out', 'c.json', '--map-out', 'm.json', '--mirror', 'mir.json'])


def test_template_needs_faces(committed):
    with pytest.raises(ValueError):
        mc.template(committed['cfg'], committed['mp'], [])
    t = mc.template(committed['cfg'], committed['mp'], [pts478(5), pts478(6)])
    assert t.shape == (50, 2)


def test_rerunning_make_config_keeps_values_others_wrote_and_drops_old_version():
    new = mc.build_config(np.arange(100, dtype=float).reshape(50, 2))
    old = json.loads(json.dumps(new))
    old['t_flip'], old['tolerance'], old['status'] = 0.07, {'eye': 3.0}, 'DONG BANG 12/10'
    fresh = mc.build_config()                                                          # chạy lại không kèm tmpl, t_flip
    kept = mc.keep_existing(fresh, old, t_flip_given=False)
    assert set(kept) == {'t_flip', 'tolerance', 'status', 'tmpl'}
    assert fresh['t_flip'] == 0.07 and fresh['tolerance'] == {'eye': 3.0} and fresh['points'][0]['tmpl'] == [0.0, 1.0]
    forced = mc.keep_existing(mc.build_config(), old, t_flip_given=True)               # --t-flip mới thì không giữ số cũ
    assert 't_flip' not in forced
    v1 = copy.deepcopy(OLD_V1_CFG)                                                     # tmpl của version 1 là hình học 98 điểm cũ: không được mang sang
    assert mc.keep_existing(mc.build_config(), v1, False) == []
    # version 2 -> 3: tên điểm và hình khuôn khác hẳn, t_flip 0,0464 của định nghĩa cũ không được mang sang
    v2 = dict(version=2, status='DONG BANG 12/10', t_flip=0.0464, tolerance={'jaw': 3.0},
              points=[dict(name=f'p{i:02d}_x', tmpl=[1.0, 2.0]) for i in range(1, 51)])
    fresh2 = mc.build_config()
    assert mc.keep_existing(fresh2, v2, False) == [] and fresh2['t_flip'] is None and fresh2['tolerance'] is None and fresh2['points'][0]['tmpl'] is None
    same_names_other_version = dict(old, version=2)                                    # cùng tên điểm nhưng khác version: cũng không giữ
    assert mc.keep_existing(mc.build_config(), same_names_other_version, False) == []
    assert mc.build_config()['points'][0]['tmpl'] is None
    with pytest.raises(AssertionError):
        mc.build_config(np.zeros((10, 2)))
