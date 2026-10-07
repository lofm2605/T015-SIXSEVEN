"""Thử tool/make_label.py: BẢY label skeleton (mỗi nhóm của 50 điểm DMS một label, QĐ-004) sinh từ config/m28_config.json version 3
(đúng 50 điểm tên mới, cạnh theo nhóm, màu theo nhóm, không có id, khuôn svg riêng từng nhóm).

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
GROUPS = ['longmaytrai', 'longmayphai', 'songmui', 'mattrai', 'matphai', 'moingoai', 'moitrong']
COUNTS = [5, 5, 4, 8, 8, 12, 8]
# bảng màu của hình minh hoạ DMS (chủ repo, 7/10/2026): mã đọc từ ký hiệu chú giải của hình
FIGURE = {'matphai': '#9b59b6', 'longmaytrai': '#e74c3c', 'songmui': '#2ecc71', 'longmayphai': '#3498db',
          'moitrong': '#f1c40f', 'mattrai': '#e67e22', 'moingoai': '#1abc9c'}


@pytest.fixture(scope='module')
def cfg():
    with open(CONFIG, encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def labels(cfg):
    out = make_label.build_labels(cfg)
    assert len(out) == 7
    return out


def walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


def test_seven_skeleton_labels_one_per_group_with_50_sublabels_in_config_order(cfg, labels):
    assert [lb['name'] for lb in labels] == GROUPS                                              # tên label = tên nhóm, thứ tự nhóm của config
    assert all(lb['type'] == 'skeleton' and lb['attributes'] == [] for lb in labels)
    assert [len(lb['sublabels']) for lb in labels] == COUNTS and sum(COUNTS) == 50
    assert [s['name'] for lb in labels for s in lb['sublabels']] == [p['name'] for p in cfg['points']]   # 50 tên theo thứ tự config, mỗi tên đúng một lần
    assert all(s['type'] == 'points' for lb in labels for s in lb['sublabels'])
    for lb in labels:                                                                           # mỗi skeleton chỉ có điểm của nhóm mình
        assert {make_label.groups_of(cfg['points'])[lb['name']][i]['name'] for i in range(len(lb['sublabels']))} == {s['name'] for s in lb['sublabels']}
        assert all(s['name'].rsplit('_', 1)[0] == lb['name'] for s in lb['sublabels'])
    assert 'face50' not in [lb['name'] for lb in labels]                                        # không còn label một-skeleton cũ


def test_each_sublabel_has_one_low_conf_checkbox(labels):
    for lb in labels:
        for s in lb['sublabels']:
            assert len(s['attributes']) == 1
            a = s['attributes'][0]
            assert (a['name'], a['input_type'], a['mutable'], a['default_value'], a['values']) == ('low_conf', 'checkbox', True, 'false', ['false'])


def test_no_id_keys_anywhere_and_no_label_id_in_svg(labels):
    assert not [d for lb in labels for d in walk(lb) if 'id' in d]
    assert all('data-label-id' not in lb['svg'] for lb in labels)


def test_colors_follow_group_as_in_the_reference_figure(cfg, labels):
    assert make_label.GROUP_COLOR == FIGURE                                                      # đúng bảng màu của hình, không màu nào khác
    for lb in labels:
        assert lb['color'] == FIGURE[lb['name']]                                                 # màu của chính label skeleton (chấm màu trong "Draw new skeleton")
        assert {s['color'] for s in lb['sublabels']} == {FIGURE[lb['name']]}                     # mọi sublabel cùng màu nhóm
    assert len({lb['color'] for lb in labels}) == 7                                              # bảy nhóm bảy màu khác nhau
    # trái/phải của bức ảnh vẫn nhìn ra được vì hai nhóm của cặp khác màu: mắt cam / tím, lông mày đỏ / xanh dương
    assert FIGURE['mattrai'] != FIGURE['matphai'] and FIGURE['longmaytrai'] != FIGURE['longmayphai']
    assert [lb['color'] for lb in labels if lb['name'] == 'moingoai'] == ['#1abc9c']


def svg_items(svg):
    circles = [dict(re.findall(r'([\w-]+)="([^"]*)"', m)) for m in re.findall(r'<circle ([^>]*)></circle>', svg)]
    lines = [dict(re.findall(r'([\w-]+)="([^"]*)"', m)) for m in re.findall(r'<line ([^>]*)></line>', svg)]
    return circles, lines


def test_svg_nodes_use_label_name_in_group_order_numbered_within_the_skeleton(cfg, labels):
    for lb in labels:
        circles, _ = svg_items(lb['svg'])
        assert len(circles) == len(lb['sublabels'])
        for i, (s, c) in enumerate(zip(lb['sublabels'], circles), 1):
            assert c['data-label-name'] == s['name']
            assert c['data-type'] == 'element node' and c['data-element-id'] == str(i) and c['data-node-id'] == str(i)   # đếm từ 1 TRONG skeleton
            assert 0 <= float(c['cx']) <= 100 and 0 <= float(c['cy']) <= 100


def test_svg_template_is_the_group_shape_scaled_to_the_frame(cfg, labels):
    """Khuôn mỗi label là tmpl của chính nhóm co giãn vào khung 0-100: hình đo được khác nhau giữa các nhóm và lấp đầy khung (không còn nằm lọt thỏm như khi cả mặt chung một khuôn)."""
    for lb in labels:
        circles, _ = svg_items(lb['svg'])
        xs, ys = [float(c['cx']) for c in circles], [float(c['cy']) for c in circles]
        assert max(max(xs) - min(xs), max(ys) - min(ys)) == pytest.approx(100 - 2 * make_label.MARGIN, abs=0.05), lb['name']
    mattrai = {p['name']: p['tmpl'] for p in cfg['points'] if p['group'] == 'mattrai'}
    circles, _ = svg_items([lb for lb in labels if lb['name'] == 'mattrai'][0]['svg'])
    assert float(circles[0]['cx']) < float(circles[4]['cx']) and mattrai['mattrai_1'][0] < mattrai['mattrai_5'][0]       # khoé ngoài (trái ảnh) ở bên trái của khuôn


def test_svg_only_uses_attributes_cvat_core_allows(labels):
    allowed = {'cx', 'cy', 'r', 'x1', 'y1', 'x2', 'y2', 'data-type', 'data-element-id', 'data-label-name', 'data-node-id',
               'data-node-from', 'data-node-to'}
    for lb in labels:
        circles, lines = svg_items(lb['svg'])
        for d in circles + lines:
            assert set(d) <= allowed, set(d) - allowed


def test_edge_count_matches_lines_and_closed(cfg, labels):
    total = 0
    for lb, n in zip(labels, COUNTS):
        _, lines = svg_items(lb['svg'])
        closed = cfg['lines'][lb['name']]['closed']
        want = n - 1 + (1 if closed and n > 2 else 0)
        assert len(lines) == want, lb['name']
        for e in lines:
            assert 1 <= int(e['data-node-from']) <= n and 1 <= int(e['data-node-to']) <= n and e['data-type'] == 'edge'
        ids = {(int(e['data-node-from']), int(e['data-node-to'])) for e in lines}
        assert len(ids) == len(lines)                                                            # không cạnh trùng
        assert all((k, k + 1) in ids for k in range(1, n))                                       # nối điểm liền nhau theo thứ tự
        assert ((n, 1) in ids) == (closed and n > 2)                                             # mắt và môi đóng kín; mày và sống mũi hở
        total += len(lines)
    assert total == 47                                                                           # mày 4 + 4, sống mũi 3, mắt 8 + 8, môi ngoài 12, môi trong 8
    assert len(make_label.edge_names(cfg['points'], cfg['lines'])) == 47


def test_edges_connect_only_neighbours_inside_one_skeleton(cfg, labels):
    names = {p['name']: p for p in cfg['points']}
    edges = make_label.edge_names(cfg['points'], cfg['lines'])
    for e in edges:
        a, b = sorted(e)
        assert names[a]['group'] == names[b]['group'] and names[a]['line'] == names[b]['line']   # nhóm không nối với nhau (hai mắt, hai mày, môi ngoài với môi trong)
    assert frozenset(('mattrai_8', 'mattrai_1')) in edges and frozenset(('moitrong_8', 'moitrong_1')) in edges   # vòng kín
    assert frozenset(('longmaytrai_5', 'longmaytrai_1')) not in edges and frozenset(('songmui_4', 'songmui_1')) not in edges   # đường hở


def test_two_runs_give_identical_bytes(tmp_path):
    a, b = tmp_path / 'a.json', tmp_path / 'b.json'
    make_label.main(['--config', CONFIG, '--out', str(a)])
    make_label.main(['--config', CONFIG, '--out', str(b)])
    assert a.read_bytes() == b.read_bytes()
    assert json.loads(a.read_text(encoding='utf-8')) == make_label.build_labels(json.load(open(CONFIG, encoding='utf-8')))


def test_committed_label_file_matches_config(cfg):
    path = os.path.join(HERE, '..', 'config', 'face50_label.json')
    if os.path.exists(path):
        got = json.load(open(path, encoding='utf-8'))
        assert got == make_label.build_labels(cfg) and [lb['name'] for lb in got] == GROUPS


def test_old_v2_config_is_rejected_with_a_clear_message(cfg):
    v2 = copy.deepcopy(cfg)
    del v2['side_convention']                                        # config version 2 không có trường này (side theo người trong ảnh)
    with pytest.raises(SystemExit, match='side_convention.*version 2.*QĐ-003'):
        make_label.build_labels(v2)
    wrong = copy.deepcopy(cfg)
    wrong['side_convention'] = 'person'
    with pytest.raises(SystemExit, match='side_convention'):
        make_label.build_labels(wrong)


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
    nogroup = copy.deepcopy(cfg)
    del nogroup['points'][3]['group']
    with pytest.raises(SystemExit, match='group.*màu'):                                          # không có nhóm thì không có label và màu
        make_label.build_labels(nogroup)
    notmpl = copy.deepcopy(cfg)
    del notmpl['points'][7]['tmpl']
    with pytest.raises(SystemExit, match='tmpl'):
        make_label.build_labels(notmpl)
    quote = copy.deepcopy(cfg)
    quote['points'][0]['name'] = 'a"b'
    with pytest.raises(SystemExit, match='không hợp lệ'):
        make_label.build_labels(quote)
