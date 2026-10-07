"""Thử 50 điểm DMS (config version 3, QĐ-003) xuyên suốt pipeline bằng mặt GIẢ và các file config/map/label ĐÃ COMMIT: map50 -> flags -> XML -> cvat_io -> eval50.

Không ảnh thật, không mạng, không CVAT. Kiểm cả đường lỗi khi gặp lượt chạy bằng định nghĩa 50 điểm CŨ (version 2).
"""
import json
import os
import re
import sys
import types

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
import eval50  # noqa: E402
import make_config as mc  # noqa: E402
from m28core import cvat_io, steps  # noqa: E402
from synth_faces import synthetic_run  # noqa: E402

CONFIG_DIR = os.path.join(HERE, '..', 'config')
CFG = json.load(open(os.path.join(CONFIG_DIR, 'm28_config.json'), encoding='utf-8'))
MAP = json.load(open(os.path.join(CONFIG_DIR, 'map_mp50.json'), encoding='utf-8'))
PERM = np.array(json.load(open(os.path.join(CONFIG_DIR, 'mp_mirror478.json'), encoding='utf-8'))['perm'])
NAMES = [p['name'] for p in CFG['points']]
GROUP_LABELS = ['longmaytrai', 'longmayphai', 'songmui', 'mattrai', 'matphai', 'moingoai', 'moitrong']


def make_run(tmp_path, n=3, t_flip=None):
    """Lượt giả: pred478 của n mặt đối xứng (có cả ảnh lật), crop/meta.json, chế độ crop; trả (args, thư mục lượt)."""
    rd = tmp_path / 'runs' / 'R'
    (rd / 'mediapipe').mkdir(parents=True)
    (rd / 'crop').mkdir()
    origs, flips = synthetic_run(PERM, n=n, w=MAP['flip_width'])
    names = [f'F_{i + 1:03d}' for i in range(n)]
    (rd / 'mediapipe' / 'pred478.json').write_text(json.dumps({k: {'orig': o.tolist(), 'flip': f.tolist()} for k, o, f in zip(names, origs, flips)}), encoding='utf-8')
    meta = {k: dict(src=f'/x/{k}.jpg', rel=f'{k}.jpg', left=0.0, top=0.0, k=1.0, w=512, h=512) for k in names}
    (rd / 'crop' / 'meta.json').write_text(json.dumps(meta), encoding='utf-8')
    (rd / 'crop' / 'box.txt').write_text('crop', encoding='utf-8')
    cfg = dict(CFG, t_flip=t_flip)
    cfg_path = tmp_path / 'cfg.json'
    cfg_path.write_text(json.dumps(cfg), encoding='utf-8')
    args = types.SimpleNamespace(run='R', config=str(cfg_path), map=os.path.join(CONFIG_DIR, 'map_mp50.json'))
    return args, rd, names, meta


def test_map50_flags_xml_cvat_io_and_eval50_all_work_with_the_new_names(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    args, rd, names, meta = make_run(tmp_path, t_flip=0.05)
    out_map, out_flag = tmp_path / 'o_map', tmp_path / 'o_flag'
    out_map.mkdir(), out_flag.mkdir()
    assert steps.map50(args, str(out_map))
    mp50 = json.load(open(out_map / 'mp50.json', encoding='utf-8'))
    assert list(mp50['F_001']['orig']) == NAMES and list(mp50['F_001']['flip']) == NAMES                  # đúng 50 tên mới, đúng thứ tự config
    assert not [k for k in mp50['F_001']['orig'] if re.match(r'p\d\d_', k)]
    (rd / 'map50').mkdir()
    (rd / 'map50' / 'mp50.json').write_text(json.dumps(mp50), encoding='utf-8')
    assert steps.flags(args, str(out_flag))
    fl = json.load(open(out_flag / 'flags.json', encoding='utf-8'))
    assert all(len(v) == 50 and not any(v) for v in fl.values())                                           # mặt giả đối xứng: lật khớp, không cờ nào
    # XML theo ảnh cắt: đúng một skeleton face50 mỗi ảnh, đủ 50 điểm tên mới đúng thứ tự, kèm low_conf
    xml = tmp_path / 'xml' / 'prelabel.xml'
    steps.build_xml('crop', list(names), meta, mp50, fl, CFG, str(xml))
    ann = cvat_io.parse_annotations(xml.read_bytes())
    assert sorted(ann) == [f'{n}.png' for n in names]
    for im in ann.values():                                                                              # BẢY skeleton mỗi mặt, mỗi nhóm một, label = tên nhóm (QĐ-004)
        assert [sk['label'] for sk in im['skeletons']] == GROUP_LABELS
        assert [n for sk in im['skeletons'] for n in sk['points']] == NAMES
        assert all(n.rsplit('_', 1)[0] == sk['label'] for sk in im['skeletons'] for n in sk['points'])
    res = cvat_io.check_faces(ann, [f'{n}.png' for n in names], [], NAMES, [])
    assert res['n_day_du'] == 3 and res['n_nhan'] == 3                                                    # kiểm sau khi nhập của push chạy với tên mới
    # eval50: nháp so với chính nó = 0, và đọc đúng nhãn có tên mới
    gt = eval50.read_labels(str(xml), CFG)
    assert all(set(v) == set(NAMES) for v in gt.values())
    r = eval50.evaluate(gt, gt, CFG)
    assert r['summary']['n_faces'] == 3 and r['summary']['nme_mean'] == 0 and set(r['summary']['region_mean']) == {'brow', 'nose', 'eye', 'lip'}
    assert r['rows'][0]['nme_eye'] == 0 and r['rows'][0]['eye_open_err'] == 0


def test_flags_mark_the_right_points_when_the_flipped_prediction_disagrees(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    args, rd, names, meta = make_run(tmp_path, n=2, t_flip=0.05)
    out = tmp_path / 'o'
    out.mkdir()
    steps.map50(args, str(out))
    mp50 = json.load(open(out / 'mp50.json', encoding='utf-8'))
    iod = np.linalg.norm(np.array(mp50['F_001']['orig']['mattrai_1']) - np.array(mp50['F_001']['orig']['matphai_1']))
    mp50['F_001']['flip']['moingoai_4'][0] += 0.2 * iod                                                   # ảnh lật lệch 20% IOD ở một điểm giữa môi
    (rd / 'map50').mkdir()
    (rd / 'map50' / 'mp50.json').write_text(json.dumps(mp50), encoding='utf-8')
    out2 = tmp_path / 'o2'
    out2.mkdir()
    steps.flags(args, str(out2))
    fl = json.load(open(out2 / 'flags.json', encoding='utf-8'))
    assert [n for n, f in zip(NAMES, fl['F_001']) if f] == ['moingoai_4'] and not any(fl['F_002'])


def test_old_v2_run_is_reported_clearly_not_with_a_keyerror(tmp_path, monkeypatch):
    """Lượt chạy bằng định nghĩa 50 điểm cũ (mp50.json tên pNN_vùng_bên) không đọc được bằng config version 3: nói rõ cách xử lý."""
    monkeypatch.chdir(tmp_path)
    args, rd, names, meta = make_run(tmp_path, t_flip=0.05)
    (rd / 'map50').mkdir()
    (rd / 'flags').mkdir()
    old = {n: dict(orig={f'p{i:02d}_jaw_R': [1.0, 1.0] for i in range(1, 51)}, flip=None) for n in names}
    (rd / 'map50' / 'mp50.json').write_text(json.dumps(old), encoding='utf-8')
    (rd / 'flags' / 'flags.json').write_text(json.dumps({n: [False] * 50 for n in names}), encoding='utf-8')
    out = tmp_path / 'o'
    out.mkdir()
    for step in (steps.flags, steps.autoqc, steps.overlays):
        with pytest.raises(SystemExit) as e:
            step(args, str(out))
        msg = str(e.value)
        assert 'CŨ' in msg and 'version 2' in msg and 'QĐ-003' in msg and 'p01_jaw_R' in msg and 'prepare --run R --force map50 flags autoqc overlays' in msg and 'longmaytrai_1' in msg


def test_apply_map_rejects_the_old_committed_pair_but_accepts_the_new_one():
    """Cặp config + map của định nghĩa cũ (đã chép từ lịch sử git) không còn dùng được với công cụ mới; cặp mới thì có."""
    from m28core import mapping
    pts = np.random.default_rng(0).uniform(0, 512, size=(478, 2))
    assert list(mapping.apply_map(pts, MAP, CFG)) == NAMES
    old_cfg = dict(CFG)
    old_cfg.pop('side_convention')
    with pytest.raises(ValueError, match='side_convention'):
        mapping.apply_map(pts, MAP, old_cfg)
    assert mc.build_map(CFG, MAP['flip_width'], MAP['meta'])['version'] == 3


def test_stale_run_detection_and_m28_recomputes_only_the_name_dependent_steps(tmp_path, monkeypatch, capsys):
    """Lượt có mp50.json tên cũ (version 2): stale_derived_steps trả bốn bước phụ thuộc tên; m28.py prepare tự thêm chúng vào --force (crop, mediapipe giữ nguyên)."""
    import m28
    monkeypatch.chdir(tmp_path)
    args, rd, names, meta = make_run(tmp_path, t_flip=None)
    assert steps.stale_derived_steps(args) == []                                            # chưa chạy map50: không có gì cũ
    (rd / 'map50').mkdir()
    cur = {n: dict(orig={k: [1.0, 1.0] for k in NAMES}, flip=None) for n in names}
    (rd / 'map50' / 'mp50.json').write_text(json.dumps(cur), encoding='utf-8')
    assert steps.stale_derived_steps(args) == []                                            # tên khớp config hiện tại
    old = {n: dict(orig={f'p{i:02d}_jaw_R': [1.0, 1.0] for i in range(1, 51)}, flip=None) for n in names}
    (rd / 'map50' / 'mp50.json').write_text(json.dumps(old), encoding='utf-8')
    assert steps.stale_derived_steps(args) == ['map50', 'flags', 'autoqc', 'overlays']
    seen = []
    monkeypatch.setattr(m28, 'run_step', lambda name, a: seen.append((name, tuple(a.force))))
    m28.main(['prepare', '--run', 'R', '--config', args.config, '--map', args.map])
    assert [n for n, _ in seen] == m28.PREPARE and all(set(f) == {'autoqc', 'flags', 'map50', 'overlays'} for _, f in seen)
    assert 'tính lại map50, flags, autoqc, overlays' in capsys.readouterr().out
    (rd / 'map50' / 'mp50.json').write_text(json.dumps(cur), encoding='utf-8')               # lượt hợp lệ: không ép chạy lại gì
    seen.clear()
    m28.main(['prepare', '--run', 'R', '--config', args.config, '--map', args.map])
    assert all(f == () for _, f in seen)


def test_overlays_step_paints_group_colors_with_a_ring_on_low_conf_points(tmp_path, monkeypatch):
    """steps.overlays (cv2) vẽ chấm màu NHÓM như label trên CVAT (QĐ-004); điểm low_conf to hơn, có vòng trắng."""
    cv2 = pytest.importorskip('cv2')
    from m28core import mau_nhom
    monkeypatch.chdir(tmp_path)
    args, rd, names, meta = make_run(tmp_path, n=1)
    pts = [(30 + 45 * (i % 10), 40 + 80 * (i // 10)) for i in range(50)]
    (rd / 'map50').mkdir()
    (rd / 'map50' / 'mp50.json').write_text(json.dumps({'F_001': dict(orig={n: list(p) for n, p in zip(NAMES, pts)}, flip=None)}), encoding='utf-8')
    (rd / 'flags').mkdir()
    flags = [i in (0, 12, 33) for i in range(50)]
    (rd / 'flags' / 'flags.json').write_text(json.dumps({'F_001': flags}), encoding='utf-8')
    (rd / 'crop' / 'images').mkdir()
    cv2.imwrite(str(rd / 'crop' / 'images' / 'F_001.png'), np.full((512, 512, 3), 128, np.uint8))
    out = tmp_path / 'o'
    out.mkdir()
    assert steps.overlays(args, str(out))
    img = cv2.imread(str(out / 'F_001.png'))

    def at(i, dx=0):
        b, g, r = (int(v) for v in img[pts[i][1], pts[i][0] + dx])
        return (r, g, b)
    for i, n in enumerate(NAMES):
        assert at(i) == mau_nhom.hex_rgb(mau_nhom.GROUP_COLOR[mau_nhom.group_of(n)]), n          # giữa chấm = màu nhóm, cả điểm ổn lẫn low_conf
    for i in (0, 12, 33):
        assert min(at(i, mau_nhom.R_LOW + 1)) >= 200, i                                            # vòng trắng quanh điểm low_conf (cạnh khử răng cưa nên có sai số nhỏ)
    assert at(1, -(mau_nhom.R_OK + 3)) == (128, 128, 128)                                                    # chấm ổn: ngoài viền (bên trái, xa số thứ tự) là nền, không có vòng trắng
    assert max(abs(c - d) for c, d in zip(at(1, -(mau_nhom.R_OK + 1)), mau_nhom.DARK)) <= 60                # một viền tối mảnh (hoà với màu chấm ở mép nên cho sai số)


def test_group_colors_have_a_single_source_shared_by_label_and_overlays():
    import make_label
    from m28core import mau_nhom
    assert make_label.GROUP_COLOR is mau_nhom.GROUP_COLOR and set(mau_nhom.GROUP_VI) == set(mau_nhom.GROUP_COLOR) == set(GROUP_LABELS)
    assert [mau_nhom.group_of(n) for n in NAMES][:6] == ['longmaytrai'] * 5 + ['longmayphai'] and mau_nhom.group_of('p01_jaw_R') is None
    assert mau_nhom.all_grouped(NAMES) and not mau_nhom.all_grouped(['p01_jaw_R', 'p02_jaw_R']) and not mau_nhom.all_grouped([])
    assert mau_nhom.dot_rgb(None, True) == mau_nhom.FALLBACK_LOW and mau_nhom.dot_rgb(None, False) == mau_nhom.FALLBACK_OK        # tên cũ: đỏ / xanh như bản cũ

