"""Thử tool/make_label.py: label skeleton face50 sinh từ config/m28_config.json (đúng 50 điểm, cạnh, màu, không có id).

Định dạng bám mã nguồn CVAT v2.77.0 nhưng CHƯA thử trên server CVAT thật (xem README, mục Rủi ro).
"""
import copy
import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
import make_label  # noqa: E402

CONFIG = os.path.join(HERE, '..', 'config', 'm28_config.json')


@pytest.fixture(scope='module')
def cfg():
    with open(CONFIG, encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def label(cfg):
    labels = make_label.build_labels(cfg)
    assert len(labels) == 1
    return labels[0]


def walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


def test_one_skeleton_label_with_50_sublabels_in_config_order(cfg, label):
    assert label['name'] == 'face50' and label['type'] == 'skeleton' and label['attributes'] == []
    assert [s['name'] for s in label['sublabels']] == [p['name'] for p in cfg['points']]
    assert len(label['sublabels']) == 50
    assert all(s['type'] == 'points' for s in label['sublabels'])


def test_each_sublabel_has_one_low_conf_checkbox(label):
    for s in label['sublabels']:
        assert len(s['attributes']) == 1
        a = s['attributes'][0]
        assert (a['name'], a['input_type'], a['mutable'], a['default_value'], a['values']) == ('low_conf', 'checkbox', True, 'false', ['false'])


def test_no_id_keys_anywhere_and_no_label_id_in_svg(label):
    assert not [d for d in walk(label) if 'id' in d]
    assert 'data-label-id' not in label['svg']


def test_colors_follow_side(cfg, label):
    for p, s in zip(cfg['points'], label['sublabels']):
        assert s['color'] == make_label.SIDE_COLOR[p['side']]
    assert len({s['color'] for s in label['sublabels']}) == 3


def svg_items(svg):
    circles = [dict(re.findall(r'([\w-]+)="([^"]*)"', m)) for m in re.findall(r'<circle ([^>]*)></circle>', svg)]
    lines = [dict(re.findall(r'([\w-]+)="([^"]*)"', m)) for m in re.findall(r'<line ([^>]*)></line>', svg)]
    return circles, lines


def test_svg_nodes_use_label_name_in_config_order(cfg, label):
    circles, _ = svg_items(label['svg'])
    assert len(circles) == 50
    for i, (p, c) in enumerate(zip(cfg['points'], circles), 1):
        assert c['data-label-name'] == p['name']
        assert c['data-type'] == 'element node' and c['data-element-id'] == str(i) and c['data-node-id'] == str(i)
        assert 0 <= float(c['cx']) <= 100 and 0 <= float(c['cy']) <= 100


def test_svg_only_uses_attributes_cvat_core_allows(label):
    allowed = {'cx', 'cy', 'r', 'x1', 'y1', 'x2', 'y2', 'data-type', 'data-element-id', 'data-label-name', 'data-node-id',
               'data-node-from', 'data-node-to'}
    circles, lines = svg_items(label['svg'])
    for d in circles + lines:
        assert set(d) <= allowed, set(d) - allowed


def test_edge_count_matches_lines_and_closed(cfg, label):
    _, lines = svg_items(label['svg'])
    groups = {}
    for p in cfg['points']:
        if p.get('line'):
            groups[p['line']] = groups.get(p['line'], 0) + 1
    want = sum(n - 1 for n in groups.values()) + sum(1 for k in groups if cfg['lines'][k]['closed'])
    assert len(lines) == want == 44
    for e in lines:
        assert 1 <= int(e['data-node-from']) <= 50 and 1 <= int(e['data-node-to']) <= 50
        assert e['data-type'] == 'edge'
    ids = {(int(e['data-node-from']), int(e['data-node-to'])) for e in lines}
    assert len(ids) == len(lines)                                    # không cạnh trùng


def test_edges_connect_only_same_line_neighbours(cfg, label):
    _, lines = svg_items(label['svg'])
    pts = cfg['points']
    for e in lines:
        a, b = int(e['data-node-from']), int(e['data-node-to'])
        assert pts[a - 1]['line'] == pts[b - 1]['line'] and pts[a - 1]['line']
    closed_eye = [(int(e['data-node-from']), int(e['data-node-to'])) for e in lines if pts[int(e['data-node-from']) - 1]['line'] == 'eye_R']
    assert (36, 33) in closed_eye                                    # eye_R đóng: điểm cuối nối về điểm đầu


def test_two_runs_give_identical_bytes(tmp_path):
    a, b = tmp_path / 'a.json', tmp_path / 'b.json'
    make_label.main(['--config', CONFIG, '--out', str(a)])
    make_label.main(['--config', CONFIG, '--out', str(b)])
    assert a.read_bytes() == b.read_bytes()
    assert json.loads(a.read_text(encoding='utf-8')) == make_label.build_labels(json.load(open(CONFIG, encoding='utf-8')))


def test_committed_label_file_matches_config(cfg):
    path = os.path.join(HERE, '..', 'config', 'face50_label.json')
    if os.path.exists(path):
        assert json.load(open(path, encoding='utf-8')) == make_label.build_labels(cfg)


def test_bad_configs_are_rejected(cfg):
    short = copy.deepcopy(cfg)
    short['points'] = short['points'][:49]
    with pytest.raises(SystemExit, match='50'):
        make_label.build_labels(short)
    dup = copy.deepcopy(cfg)
    dup['points'][5]['name'] = dup['points'][4]['name']
    with pytest.raises(SystemExit, match='trùng'):
        make_label.build_labels(dup)
    side = copy.deepcopy(cfg)
    side['points'][0]['side'] = 'X'
    with pytest.raises(SystemExit, match='side'):
        make_label.build_labels(side)
    notmpl = copy.deepcopy(cfg)
    del notmpl['points'][7]['tmpl']
    with pytest.raises(SystemExit, match='tmpl'):
        make_label.build_labels(notmpl)
    quote = copy.deepcopy(cfg)
    quote['points'][0]['name'] = 'a"b'
    with pytest.raises(SystemExit, match='không hợp lệ'):
        make_label.build_labels(quote)
