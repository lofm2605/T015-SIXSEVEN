import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tool'))
import flag_eval  # noqa: E402


def test_auroc_known_values():
    assert flag_eval.auroc([1, 2, 3, 4], [False, False, True, True]) == 1.0
    assert flag_eval.auroc([4, 3, 2, 1], [False, False, True, True]) == 0.0
    assert flag_eval.auroc([1, 1, 1, 1], [False, True, False, True]) == 0.5       # hoà hết
    assert np.isnan(flag_eval.auroc([1, 2], [False, False]))
    rng = np.random.default_rng(0)
    s = rng.normal(size=400)
    y = rng.random(400) < 0.3
    brute = np.mean([(a > b) + 0.5 * (a == b) for a in s[y] for b in s[~y]])
    assert abs(flag_eval.auroc(s, y) - brute) < 1e-9


def test_report_counts():
    rows = [('eye', 0.1 * i, 1.0 if i < 8 else 5.0, f'F_{i // 5}') for i in range(10)]      # 2 điểm sai, điểm số cao nhất
    lines = []
    table = flag_eval.report(rows, 3.0, out=lines.append)
    assert 'AUROC toàn bộ: 1.000' in lines[1]
    q85 = [t for t in table if t[0] == 0.85][0]
    assert q85[3] > 0 and q85[4] > 0


# ---------- chế độ (a): không đáp án ----------
import csv  # noqa: E402
import json  # noqa: E402
import types  # noqa: E402

import pytest  # noqa: E402

from m28core import steps  # noqa: E402

CFG = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'config', 'm28_config.json'), encoding='utf-8'))
NAMES = [p['name'] for p in CFG['points']]
TMPL = {p['name']: [float(p['tmpl'][0]), float(p['tmpl'][1])] for p in CFG['points']}
IOD = float(np.hypot(*(np.array(TMPL['p33_eye_R']) - np.array(TMPL['p39_eye_L']))))


def known_scores_mp50(n_faces=4, shift=None):
    """mp50 giả: điểm thứ k của mọi mặt lệch gốc/lật đúng k/100 IOD dự đoán (điểm số 0,00 ... 0,49): biết trước phân vị."""
    mp50 = {}
    for f in range(n_faces):
        orig = {n: list(TMPL[n]) for n in NAMES}
        flip = {n: [TMPL[n][0] + (k / 100) * IOD, TMPL[n][1]] for k, n in enumerate(NAMES)}
        mp50[f'F_{f + 1:03d}'] = dict(orig=orig, flip=flip)
    mp50['F_999'] = dict(orig={n: list(TMPL[n]) for n in NAMES}, flip=None)             # không có ảnh lật: bị bỏ
    return mp50


def test_flip_scores_are_offset_over_predicted_iod():
    f = known_scores_mp50(1)
    sc = flag_eval.flip_scores(f['F_001'], CFG)
    assert [round(v, 6) for _, v in sc] == [round(k / 100, 6) for k in range(50)]
    assert [r for r, _ in sc] == [p['region'] for p in CFG['points']]
    assert flag_eval.flip_scores(f['F_999'], CFG) is None


def test_unlabelled_mode_suggests_85th_percentile_with_known_value():
    mp50 = known_scores_mp50(1)                                                           # một mặt: phân vị nội suy giữa hai điểm số khác nhau (không trùng giá trị)
    rows, skipped = flag_eval.collect_scores(sorted(mp50), mp50, CFG)
    assert skipped == 1 and len(rows) == 50
    lines = []
    res = flag_eval.report_unlabelled(rows, out=lines.append)
    expect = float(np.quantile(np.arange(50) / 100, 0.85))                              # 0,4165
    assert res['t_flip'] == pytest.approx(round(expect, 4)) and res['t_flip'] == pytest.approx(0.4165)
    assert res['flags_per_face'] == pytest.approx(8.0) and res['flagged_pct'] == pytest.approx(16.0)       # 0,42 ... 0,49
    text = '\n'.join(lines)
    assert 'ĐỀ XUẤT t_flip = 0.4165' in text and 'không tính được AUROC' in text and 'chưa ghi vào config' in text
    assert any(l.startswith('   0.85') for l in lines)
    assert set(res['by_region']) == {'jaw', 'brow', 'nose', 'eye', 'lip'}
    # cùng ngưỡng đưa vào steps.flags thì cờ/mặt đúng bằng số đề xuất báo
    assert [len(t) for t in res['table']] == [4] * 6 and abs(res['table'][3][1] - expect) < 1e-9


def test_suggested_threshold_matches_steps_flags(tmp_path, monkeypatch):
    mp50 = known_scores_mp50(1)
    rows, _ = flag_eval.collect_scores(sorted(mp50), mp50, CFG)
    t = flag_eval.report_unlabelled(rows, out=lambda *_: None)['t_flip']
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'runs' / 'R' / 'map50').mkdir(parents=True)
    json.dump(mp50, open(tmp_path / 'runs' / 'R' / 'map50' / 'mp50.json', 'w'))
    cfg = dict(CFG, t_flip=t)
    json.dump(cfg, open(tmp_path / 'cfg.json', 'w'))
    out = tmp_path / 'flags_out'
    out.mkdir()
    args = types.SimpleNamespace(run='R', config='cfg.json')
    assert steps.flags(args, str(out))
    fl = json.load(open(out / 'flags.json'))
    assert sum(sum(v) for k, v in fl.items() if k != 'F_999') == 8       # = cờ/mặt của chế độ (a)
    assert all(all(v) for k, v in fl.items() if k == 'F_999')                                  # không ảnh lật: mọi điểm đáng ngờ


def write_manifest(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['file', 'set'])
        w.writerows(rows)


def test_main_unlabelled_filters_by_set_and_refuses_ttest(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'runs' / 'R' / 'map50').mkdir(parents=True)
    (tmp_path / 'config').mkdir()
    mp50 = known_scores_mp50(3)
    json.dump(mp50, open(tmp_path / 'runs' / 'R' / 'map50' / 'mp50.json', 'w'))
    json.dump(CFG, open(tmp_path / 'config' / 'm28_config.json', 'w'))
    (tmp_path / 'data').mkdir()
    write_manifest(tmp_path / 'data' / 'manifest.csv', [('F_001.png', 'Tdev'), ('F_002.png', 'Tdev'), ('F_003.png', 'Ttest'), ('F_999.png', 'Tdev')])
    assert flag_eval.main(['--run', 'R', '--set', 'Tdev']) == 0
    out = capsys.readouterr().out
    assert '2 mặt, 100 điểm' in out and 'Bỏ 1 mặt không có ảnh lật' in out and 'ĐỀ XUẤT t_flip' in out      # Ttest (F_003) không được đọc
    with pytest.raises(SystemExit) as e:
        flag_eval.main(['--run', 'R', '--set', 'Ttest'])                                   # argparse từ chối: Ttest không nằm trong choices
    assert e.value.code == 2


# ---------- chế độ (b): có đáp án ----------
BAD5 = [p['name'] for p in CFG['points'] if p['type'] == 'E' and p['name'] not in CFG['iod_points']][:5]       # 5 điểm E (p18, p22, p23, p27, p29)


def labelled_run(tmp_path, tol_region=None):
    """Lượt wflw 3 mặt; đáp án = dự đoán trừ 5 điểm đầu lệch 10% IOD; ảnh lật lệch lớn đúng ở 5 điểm đó (điểm số cao nhất) -> AUROC = 1."""
    rd = tmp_path / 'runs' / 'R'
    (rd / 'crop').mkdir(parents=True)
    (rd / 'map50').mkdir()
    meta, mp50, gt = {}, {}, {}
    for f in range(3):
        n = f'F_{f + 1:03d}'
        meta[n] = dict(src=f'/x/{n}.jpg', rel=f'{n}.jpg', left=0.0, top=0.0, k=1.0, w=512, h=512)
        orig = {nm: list(TMPL[nm]) for nm in NAMES}
        flip = {nm: [TMPL[nm][0] + (0.5 * IOD if nm in BAD5 else 0.0), TMPL[nm][1]] for nm in NAMES}
        mp50[n] = dict(orig=orig, flip=flip)
        gt[n] = {nm: [TMPL[nm][0], TMPL[nm][1] + (0.10 * IOD if nm in BAD5 else 0.0)] for nm in NAMES}
    (rd / 'crop' / 'meta.json').write_text(json.dumps(meta), encoding='utf-8')
    (rd / 'crop' / 'box.txt').write_text('wflw', encoding='utf-8')
    (rd / 'map50' / 'mp50.json').write_text(json.dumps(mp50), encoding='utf-8')
    gt_mp50 = {n: dict(orig=gt[n], flip=None) for n in gt}
    steps.build_xml('wflw', list(gt), meta, gt_mp50, {n: [False] * 50 for n in gt}, CFG, str(tmp_path / 'gt.xml'))
    cfg = dict(CFG, tolerance=tol_region)
    (tmp_path / 'config').mkdir(exist_ok=True)
    json.dump(cfg, open(tmp_path / 'config' / 'm28_config.json', 'w'))
    return meta, mp50


def test_labelled_mode_auroc_and_wrong_points(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    labelled_run(tmp_path)
    assert flag_eval.main(['--run', 'R', '--gt', 'gt.xml', '--manifest', 'khong_co.csv']) == 0
    out = capsys.readouterr().out
    assert '3 mặt, 150 điểm' in out and 'điểm sai' in out and '10.0%' in out                 # 5/50 = 10% điểm sai (E đo điểm-điểm: đúng 10% IOD)
    assert 'AUROC toàn bộ: 1.000' in out and 'AUROC theo vùng' in out
    (tmp_path / 'ngoai.xml').write_text('<annotations></annotations>', encoding='utf-8')
    with pytest.raises(SystemExit, match='Không ghép được'):
        flag_eval.main(['--run', 'R', '--gt', 'ngoai.xml'])


def test_labelled_mode_uses_tolerance_by_region_and_drops_ttest(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    labelled_run(tmp_path, tol_region={'brow': 50.0, 'nose': 50.0})                        # lông mày và mũi chấp nhận tới 50% IOD: 5 điểm sai không còn sai
    (tmp_path / 'data').mkdir()
    write_manifest(tmp_path / 'data' / 'manifest.csv', [('F_001.png', 'Tdev'), ('F_002.png', 'Tdev'), ('F_003.png', 'Ttest')])
    assert flag_eval.main(['--run', 'R', '--gt', 'gt.xml']) == 0
    out = capsys.readouterr().out
    assert 'Bỏ 1 mặt thuộc Ttest' in out and '2 mặt, 100 điểm' in out and 'điểm sai (lỗi > sai số chấp nhận, mặc định 3% IOD): 0.0%' in out


def test_tolerance_for_and_report_with_hand_rows():
    assert flag_eval.tolerance_for({'tolerance': None}, 'jaw', 3.0) == 3.0
    assert flag_eval.tolerance_for({'tolerance': {'jaw': 5.5}}, 'jaw', 3.0) == 5.5 and flag_eval.tolerance_for({'tolerance': {'jaw': 5.5}}, 'eye', 3.0) == 3.0
    assert flag_eval.tolerance_for({'tolerance': 4}, 'eye', 3.0) == 4.0
    rows = [('eye', 0.1 * i, 1.0 if i < 8 else 5.0, f'F_{i // 5}') for i in range(10)]
    lines = []
    flag_eval.report(rows, 3.0, out=lines.append, cfg={'tolerance': {'eye': 10.0}})        # eye chấp nhận 10%: không còn điểm sai
    assert '0.0%' in lines[0] and 'nan' in lines[1]
