"""Thử tool/check_flip.py (config version 3, 50 điểm DMS, bên theo ảnh) bằng mặt GIẢ đối xứng (478 điểm tổng hợp + hoán vị gương đã commit), không ảnh thật."""
import csv
import json
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
import check_flip  # noqa: E402
from m28core import mirror  # noqa: E402
from synth_faces import synthetic_run  # noqa: E402

CONFIG = os.path.join(HERE, '..', 'config')
CFG = json.load(open(os.path.join(CONFIG, 'm28_config.json'), encoding='utf-8'))
MAP = json.load(open(os.path.join(CONFIG, 'map_mp50.json'), encoding='utf-8'))
MIR = json.load(open(os.path.join(CONFIG, 'mp_mirror478.json'), encoding='utf-8'))
PERM = np.array(MIR['perm'])
W = MAP['flip_width']


def test_double_flip_returns_to_start_and_detects_a_broken_pair():
    pts = {p['name']: [float(i), float(2 * i)] for i, p in enumerate(CFG['points'])}
    assert check_flip.double_flip_error(pts, CFG, W) < 1e-9
    broken = json.loads(json.dumps(CFG))
    broken['points'][0]['flip'] = 'longmayphai_2'                                      # longmaytrai_1 -> longmayphai_2 nhưng longmayphai_2 -> longmaytrai_2: lật hai lần không về chỗ cũ
    assert check_flip.double_flip_error(pts, broken, W) > 1.0


def test_perm_errors_catches_pair_and_axis_mistakes():
    assert check_flip.perm_errors(CFG, MIR['perm']) == []
    bad = [int(v) for v in mirror._swap_partners(np.asarray(MIR['perm']), 107, 66)]       # longmaytrai_1 (107) ghép nhầm với đỉnh 66 thay vì 336
    errs = check_flip.perm_errors(CFG, bad)
    assert errs and 'longmaytrai_1' in errs[0]
    off = [int(v) for v in mirror._swap_partners(np.asarray(MIR['perm']), 1, 4)]           # chóp mũi (đỉnh 1) không còn trên trục
    assert any('side M' in e and 'songmui_4' in e for e in check_flip.perm_errors(CFG, off))


def test_d_flip_face_small_for_symmetric_faces_and_large_without_renaming():
    origs, flips = synthetic_run(PERM, n=3, w=W)
    for o, f in zip(origs, flips):
        d, reg = check_flip.d_flip_face(o, f, CFG, MAP)
        assert d < 1.0 and set(reg) == {'brow', 'nose', 'eye', 'lip'}                      # chỉ còn nhiễu 0,4 px; không còn vùng jaw
        det = check_flip.d_flip_detail(o, f, CFG, MAP)
        assert det['mean'] == d and det['region'] == reg and list(det['group']) == GROUPS and max(det['group'].values()) < 1.5       # theo từng nhóm trong 7 nhóm
        d_bad, _ = check_flip.d_flip_face(o, f, CFG, MAP, rename=False)
        assert d_bad > 20 > d * 10                                                         # quên đổi tên: lệch hàng chục % IOD
    assert check_flip.side_ok(origs[0], CFG, MAP)
    mirrored = np.stack([W - origs[0][:, 0], origs[0][:, 1]], axis=1)                     # soi gương cả mặt, KHÔNG đổi chỉ số: mattrai nằm nửa phải ảnh
    assert not check_flip.side_ok(mirrored, CFG, MAP)


def test_side_check_uses_config_pairs_not_hardcoded_names():
    assert check_flip.side_pairs(CFG) == [('mattrai_1', 'matphai_1'), ('longmaytrai_5', 'longmayphai_5')]       # khoé mắt ngoài và đuôi lông mày; không còn viền hàm
    origs, _ = synthetic_run(PERM, n=1, w=W)
    o = np.array(origs[0])
    assert check_flip.side_ok(o, CFG, MAP)
    only_brow_swapped = o.copy()
    i, j = CFG['points'][4]['mp_idx'], [p for p in CFG['points'] if p['name'] == 'longmayphai_5'][0]['mp_idx']      # đổi chỗ riêng hai đuôi mày
    only_brow_swapped[[i, j]] = only_brow_swapped[[j, i]]
    assert not check_flip.side_ok(only_brow_swapped, CFG, MAP)                                                   # khoé mắt đúng bên nhưng đuôi mày sai bên: không đạt
    v2 = json.loads(json.dumps(CFG))
    del v2['side_convention']
    with pytest.raises(ValueError, match='side_convention'):
        check_flip.side_ok(o, v2, MAP)


def make_world(tmp_path, n=25, w=W, flip_ok=True, mirrored=False):
    origs, flips = synthetic_run(PERM, n=n, w=w, seed=3)
    if not flip_ok:
        flips = [f[np.random.default_rng(1).permutation(478)] for f in flips]
    if mirrored:                                                                              # đổi bên của cả mặt gốc lẫn lật: R nằm nửa phải
        swap = lambda a: np.stack([w - a[:, 0], a[:, 1]], axis=1)                              # noqa: E731
        origs, flips = [swap(o) for o in origs], [swap(f) for f in flips]
    names = [f'F_{i + 1:03d}' for i in range(n)]
    d = tmp_path / 'runs' / 'R' / 'mediapipe'
    d.mkdir(parents=True)
    json.dump({k: {'orig': o.tolist(), 'flip': f.tolist()} for k, o, f in zip(names, origs, flips)}, open(d / 'pred478.json', 'w'))
    (tmp_path / 'data').mkdir()
    with open(tmp_path / 'data' / 'manifest.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.writer(f)
        wr.writerow(['file', 'set', 'pose'])
        wr.writerows((k + '.png', 'F' if i < n - 5 else 'Tdev', '0') for i, k in enumerate(names))


GROUPS = ['longmaytrai', 'longmayphai', 'songmui', 'mattrai', 'matphai', 'moingoai', 'moitrong']


def args():
    return ['--run', 'R', '--config', os.path.join(CONFIG, 'm28_config.json'), '--map', os.path.join(CONFIG, 'map_mp50.json'),
            '--mirror', os.path.join(CONFIG, 'mp_mirror478.json')]


def test_main_passes_on_good_data(tmp_path, monkeypatch, capsys):
    make_world(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert check_flip.main(args()) == 0
    out = capsys.readouterr().out
    assert '(1) lật 50 điểm hai lần' in out and 'đối hợp: có' in out and '(2) cặp flip của config trùng hoán vị gương' in out
    assert 'mọi mặt thẳng Tdev: n=5' in out and 'tiêu chí 20 mặt đầu < 3% IOD' in out and '(4) đối chứng' in out and '20/20' in out
    assert 'theo nhóm (trung vị): longmaytrai' in out and 'moitrong' in out and 'theo vùng (trung vị): brow' in out and 'jaw' not in out
    assert '(5) kiểm bên theo ảnh: mattrai_1 ở nửa trái hơn matphai_1 và longmaytrai_5 ở nửa trái hơn longmayphai_5 trên 20/20' in out
    assert 'KẾT QUẢ: đạt' in out and 'KHÔNG ĐẠT' not in out


def test_main_fails_when_flipped_predictions_are_inconsistent(tmp_path, monkeypatch, capsys):
    make_world(tmp_path, flip_ok=False)
    monkeypatch.chdir(tmp_path)
    assert check_flip.main(args()) == 1
    assert 'tiêu chí 20 mặt đầu < 3% IOD' in capsys.readouterr().out


def test_main_fails_on_wrong_side_and_on_mirror_file_that_disagrees_with_config(tmp_path, monkeypatch, capsys):
    make_world(tmp_path, mirrored=True)
    monkeypatch.chdir(tmp_path)
    assert check_flip.main(args()) == 1
    out = capsys.readouterr().out
    assert '(5) kiểm bên theo ảnh' in out and '0/20 mặt thẳng F -> KHÔNG ĐẠT' in out
    ident = tmp_path / 'ident.json'
    ident.write_text(json.dumps({'perm': list(range(478)), 'fixed': list(range(478)), 'meta': {}}), encoding='utf-8')
    a = args()
    a[a.index('--mirror') + 1] = str(ident)                                                # hoán vị đồng nhất: là đối hợp nhưng không khớp cặp flip
    assert check_flip.main(a) == 1


def test_main_rejects_old_config_without_image_side_convention(tmp_path, monkeypatch):
    make_world(tmp_path)
    monkeypatch.chdir(tmp_path)
    v2 = json.loads(json.dumps(CFG))
    del v2['side_convention']
    (tmp_path / 'cfg_v2.json').write_text(json.dumps(v2), encoding='utf-8')
    a = args()
    a[a.index('--config') + 1] = str(tmp_path / 'cfg_v2.json')
    with pytest.raises(SystemExit, match=r'side_convention.*version 2.*make_config'):
        check_flip.main(a)


def test_main_needs_straight_faces_with_flip(tmp_path, monkeypatch):
    make_world(tmp_path)
    monkeypatch.chdir(tmp_path)
    with open('data/manifest.csv', 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows([['file', 'set', 'pose'], ['F_001.png', 'F', '1']])
    with pytest.raises(SystemExit, match='Không có mặt F thẳng'):
        check_flip.main(args())
