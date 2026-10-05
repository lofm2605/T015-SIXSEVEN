"""Thử m28.py và m28core/steps.py bằng dữ liệu GIẢ (ảnh ngẫu nhiên, landmarker/mapping/push/collect giả).

Chưa chạy MediaPipe thật, CVAT thật, ảnh mặt thật. Cấu trúc config/mapping giả là GIẢ ĐỊNH (xem README).
"""
import csv
import json
import os
import sys
import types
import xml.etree.ElementTree as ET

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tool'))
import m28  # noqa: E402
from m28core import steps  # noqa: E402

REGIONS = ['jaw', 'brow', 'eye', 'nose', 'mouth']
NAMES = [f'p{i + 1:02d}_{REGIONS[i // 10]}_{"R" if i % 2 == 0 else "L"}' for i in range(50)]
IDX = list(range(10, 10 + 50 * 7, 7))          # 50 chỉ số cố định trong 478
EYE_R, EYE_L = NAMES[30], NAMES[40]
OFF_BIG, OFF_SMALL = 30.0, 2.0                  # độ lệch lật giả: p01..p03 lệch lớn, p04 lệch nhỏ
SIZES = {'sub/face_a.png': (480, 640), 'sub/face_b.png': (700, 500), 'face_c.png': (333, 555)}  # (h, w)


def face478(w, h):
    """478 điểm giả, xác định theo kích thước ảnh."""
    i = np.arange(478)
    fx, fy = ((i * 37) % 478) / 477 - .5, ((i * 91) % 478) / 477 - .5
    s = .5 * min(w, h)
    return np.stack([w / 2 + fx * s, h / 2 + fy * s], 1)


def crop_pts():
    return face478(512, 512)[IDX]


def iod():
    p = crop_pts()
    return float(np.linalg.norm(p[30] - p[40]))


class Calls:
    def __init__(self):
        self.mp = 0
        self.lm = 0
        self.push = []
        self.collect = []


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = Calls()

    def fake_run_mp(lm, rgb):
        calls.mp += 1
        if (rgb == 0).mean() > .1:                  # ảnh đen = không có mặt (kể cả sau khi thêm viền xám)
            return None
        h, w = rgb.shape[:2]
        return face478(w, h).tolist()

    class FakeLM:
        def close(self):
            pass

    def fake_make(model_path, num_faces=1):
        calls.lm += 1
        return FakeLM()

    monkeypatch.setattr(steps, 'run_mp', fake_run_mp)
    monkeypatch.setattr(steps, 'make_landmarker', fake_make)

    def apply_map(pts478, mp_map, config, flipped=False):
        names = [p['name'] for p in config['points']]
        out = {n: [float(pts478[mp_map['idx'][i]][0]), float(pts478[mp_map['idx'][i]][1])] for i, n in enumerate(names)}
        if flipped:
            for n in names[:3]:
                out[n][0] += OFF_BIG
            out[names[3]][0] += OFF_SMALL
        return out

    mapping = types.ModuleType('m28core.mapping')
    mapping.apply_map = apply_map
    monkeypatch.setitem(sys.modules, 'm28core.mapping', mapping)

    def fake_push(run_dir, task_name, nhan_imgs, tay_imgs, xml_path, project='m28', prefix='demo-', label_json=None):
        if not task_name.startswith(prefix):
            sys.exit('Chỉ tạo task demo-…')
        calls.push.append(dict(run_dir=run_dir, task=task_name, nhan=list(nhan_imgs), tay=list(tay_imgs),
                               xml=xml_path, project=project, prefix=prefix, label_json=label_json))

    pushmod = types.ModuleType('m28core.push')
    pushmod.push = fake_push
    monkeypatch.setitem(sys.modules, 'm28core.push', pushmod)
    colmod = types.ModuleType('m28core.collect')
    colmod.collect = lambda args: calls.collect.append(args) or True
    monkeypatch.setitem(sys.modules, 'm28core.collect', colmod)
    monkeypatch.delitem(sys.modules, 'm28core.autoqc', raising=False)

    write_config(tmp_path, t_flip=10.0 / iod())
    os.makedirs('config', exist_ok=True)
    json.dump({'idx': IDX}, open('config/map_mp50.json', 'w'))
    return calls


def write_config(tmp_path, t_flip):
    os.makedirs('config', exist_ok=True)
    cfg = {'points': [dict(name=n, region=n.split('_')[1], side=n[-1], flip=NAMES[i ^ 1]) for i, n in enumerate(NAMES)],
           'iod_points': [EYE_R, EYE_L], 't_flip': t_flip}
    json.dump(cfg, open('config/m28_config.json', 'w'))


def write_images(root, extra_black=None, corrupt=None):
    for rel, (h, w) in SIZES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(p), np.random.randint(0, 255, (h, w, 3), np.uint8))
    if extra_black:
        cv2.imwrite(str(root / extra_black), np.zeros((300, 400, 3), np.uint8))
    if corrupt:
        (root / corrupt).write_bytes(b'khong phai anh')


def write_manifest(tmp_path, rows):
    """rows: [(file, wflw_image, wflw_line, (h, w))]; hộp mặt giữa ảnh."""
    os.makedirs('data', exist_ok=True)
    with open('data/manifest.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['file', 'set', 'block', 'seq', 'wflw_image', 'wflw_line', 'x0', 'y0', 'x1', 'y1'])
        for fn, img, line, (h, wd) in rows:
            w.writerow([fn, 'F', '', 1, img, line, wd * .25, h * .25, wd * .75, h * .75])
    with open('data/list.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['wflw_image', 'wflw_line'])
        w.writerows((img, line) for _, img, line, _ in rows)


def wflw_setup(tmp_path):
    """Lượt wflw: 3 mặt tốt, 1 ảnh đen (no_face ở mediapipe), 1 file hỏng (no_face ở crop)."""
    imgs = tmp_path / 'imgs'
    write_images(imgs, extra_black='black.png', corrupt='bad.png')
    rows = [(f'F_{i + 1:03d}.png', rel, i, SIZES[rel]) for i, rel in enumerate(SIZES)]
    rows += [('F_004.png', 'black.png', 3, (300, 400)), ('F_005.png', 'bad.png', 4, (300, 400))]
    write_manifest(tmp_path, rows)
    return imgs


def prep_args(run, imgs, *more):
    return ['prepare', '--run', run, '--list', os.path.join('data', 'list.csv'), '--images', str(imgs), *more]


def read_xml(run):
    root = ET.parse(os.path.join('runs', run, 'xml', 'prelabel.xml')).getroot()
    return {im.get('name'): im for im in root.findall('image')}


def no_face_rows(run):
    with open(os.path.join('runs', run, 'no_face.csv'), encoding='utf-8', newline='') as f:
        return list(csv.reader(f))


def parse(argv):
    return m28.build_parser().parse_args(argv)


# 1 ---------------------------------------------------------------------------
def test_prepare_auto_six_steps(tmp_path, world):
    imgs = tmp_path / 'imgs'
    write_images(imgs)
    m28.main(['prepare', '--run', 'A', '--images', str(imgs), '--box', 'auto'])
    for s in m28.PREPARE:
        assert (tmp_path / 'runs' / 'A' / s / 'done.txt').exists(), s
    assert (tmp_path / 'runs' / 'A' / 'log.txt').exists()
    assert len(list((tmp_path / 'runs' / 'A' / 'overlays').glob('*.png'))) == 3
    assert (tmp_path / 'runs' / 'A' / 'autoqc' / 'autoqc.csv').exists()


def test_prepare_wflw_six_steps(tmp_path, world):
    imgs = wflw_setup(tmp_path)
    m28.main(prep_args('W', imgs, '--box', 'wflw'))
    for s in m28.PREPARE:
        assert (tmp_path / 'runs' / 'W' / s / 'done.txt').exists(), s
    assert (tmp_path / 'runs' / 'W' / 'crop' / 'images' / 'F_001.png').exists()
    assert world.lm == 1                              # --box wflw không dựng landmarker ở bước crop


def test_set_filter_and_missing_inputs(tmp_path, world):
    imgs = wflw_setup(tmp_path)
    m28.main(['prepare', '--run', 'S', '--set', 'F', '--images', str(imgs), '--box', 'wflw'])
    assert len(json.load(open('runs/S/crop/meta.json'))) == 4        # 3 mặt + ảnh đen; file hỏng không đọc được
    with pytest.raises(SystemExit, match='--images'):
        m28.main(['prepare', '--run', 'X'])               # không --images, không --list
    with pytest.raises(SystemExit, match='--list'):
        m28.main(['prepare', '--run', 'X2', '--images', str(imgs), '--box', 'wflw'])


# 2 ---------------------------------------------------------------------------
def to_review_auto(run, imgs, box, *more):
    m28.main(prep_args(run, imgs, '--box', box, *more) if os.path.exists('data/list.csv')
             else ['prepare', '--run', run, '--images', str(imgs), '--box', box, *more])
    m28.main(['review', '--run', run, '--review', 'auto'])


def test_xml_coordinates_auto(tmp_path, world):
    imgs = tmp_path / 'imgs'
    write_images(imgs)
    m28.main(['prepare', '--run', 'A', '--images', str(imgs), '--box', 'auto'])
    m28.main(['review', '--run', 'A', '--review', 'auto'])
    with pytest.raises(SystemExit):
        m28.main(['push', '--run', 'A', '--review', 'auto', '--dry-run'])
    ims = read_xml('A')
    assert sorted(ims) == ['face_a.png', 'face_b.png', 'face_c.png']
    for rel, (h, w) in SIZES.items():
        im = ims[os.path.basename(rel)]
        assert (im.get('width'), im.get('height')) == (str(w), str(h))       # ảnh gốc
        P = face478(w, h)
        (x0, y0), (x1, y1) = P.min(0), P.max(0)
        side = 1.4 * max(x1 - x0, y1 - y0)
        left, top, k = (x0 + x1 - side) / 2, (y0 + y1 - side) / 2, 512 / side
        want = crop_pts() / k + np.array([left, top])
        pts = im.findall('skeleton/points')
        assert [p.get('label') for p in pts] == NAMES
        got = np.array([[float(v) for v in p.get('points').split(',')] for p in pts])
        assert np.abs(got - want).max() <= 0.05
        assert all(p.find('attribute').get('name') == 'low_conf' for p in pts)


def test_xml_coordinates_wflw(tmp_path, world):
    imgs = wflw_setup(tmp_path)
    to_review_auto('W', imgs, 'wflw')
    with pytest.raises(SystemExit):
        m28.main(['push', '--run', 'W', '--review', 'auto', '--dry-run'])    # không gõ lại --box: lấy từ crop/box.txt
    ims = read_xml('W')
    assert sorted(ims) == ['F_001.png', 'F_002.png', 'F_003.png']             # tên = tên file ảnh cắt
    for im in ims.values():
        assert (im.get('width'), im.get('height')) == ('512', '512')
        pts = im.findall('skeleton/points')
        assert [p.get('label') for p in pts] == NAMES
        got = np.array([[float(v) for v in p.get('points').split(',')] for p in pts])
        assert np.abs(got - crop_pts()).max() <= 0.05                         # toạ độ ảnh cắt 512


def test_build_xml_clamps_to_image_edge(tmp_path):
    cfg = dict(points=[dict(name=n) for n in NAMES])
    mp = {'a': dict(orig={n: [-50.0, 9999.0] for n in NAMES})}
    meta = {'a': dict(src='x/a.png', rel='a.png', left=0, top=0, k=1.0, w=100, h=80)}
    steps.build_xml('auto', ['a'], meta, mp, {'a': [False] * 50}, cfg, str(tmp_path / 'o' / 'p.xml'))
    p = ET.parse(str(tmp_path / 'o' / 'p.xml')).getroot().find('image/skeleton/points')
    assert p.get('points') == '0.00,79.00'


# 3 ---------------------------------------------------------------------------
def test_low_conf_by_flip_offset(tmp_path, world):
    imgs = tmp_path / 'imgs'
    write_images(imgs)
    m28.main(['prepare', '--run', 'A', '--images', str(imgs)])
    fl = json.load(open('runs/A/flags/flags.json'))
    assert len(fl) == 3
    for v in fl.values():
        assert v == [True] * 3 + [False] * 47      # 30/IOD > t, 2/IOD < t, còn lại không lệch


def test_t_flip_null_all_false(tmp_path, world):
    write_config(tmp_path, None)
    imgs = tmp_path / 'imgs'
    write_images(imgs)
    m28.main(['prepare', '--run', 'A', '--images', str(imgs)])
    fl = json.load(open('runs/A/flags/flags.json'))
    assert all(not any(v) for v in fl.values())
    m28.main(['review', '--run', 'A', '--review', 'auto'])
    with pytest.raises(SystemExit):
        m28.main(['push', '--run', 'A', '--review', 'auto', '--dry-run'])
    for im in read_xml('A').values():
        assert [p.find('attribute').text for p in im.findall('skeleton/points')] == ['false'] * 50


# 4 ---------------------------------------------------------------------------
def test_no_face_csv_and_rerun_keeps_other_step(tmp_path, world):
    imgs = wflw_setup(tmp_path)
    m28.main(prep_args('W', imgs, '--box', 'wflw'))
    rows = no_face_rows('W')
    assert rows[0] == ['name', 'reason', 'step']
    assert sorted(rows[1:]) == sorted([['F_004', 'khong_thay_mat', 'mediapipe'], ['F_005', 'khong_doc_duoc_anh', 'crop']])
    m28.main(prep_args('W', imgs, '--box', 'wflw', '--force', 'mediapipe'))
    assert sorted(no_face_rows('W')[1:]) == sorted(rows[1:])                   # không mất dòng của bước crop
    m28.main(prep_args('W', imgs, '--box', 'wflw', '--force', 'crop'))
    assert sorted(no_face_rows('W')[1:]) == sorted(rows[1:])                   # crop chạy lại: mediapipe còn nguyên


def test_no_face_auto(tmp_path, world):
    imgs = tmp_path / 'imgs'
    write_images(imgs, extra_black='black.png', corrupt='bad.png')
    m28.main(['prepare', '--run', 'A', '--images', str(imgs), '--box', 'auto'])
    assert sorted(no_face_rows('A')[1:]) == [['bad', 'khong_doc_duoc_anh', 'crop'], ['black', 'khong_thay_mat', 'crop']]
    assert len(json.load(open('runs/A/crop/meta.json'))) == 3


def test_detect_box_retries_with_gray_border():
    calls = []

    def run(lm, rgb):
        calls.append(rgb.shape)
        return None if len(calls) == 1 else [[60.0, 70.0], [100.0, 90.0]]

    box = steps.detect_box(None, np.zeros((100, 200, 3), np.uint8), run=run)
    assert calls[1] == (100 + 2 * 50, 200 + 2 * 50, 3)
    assert box == (10.0, 20.0, 50.0, 40.0)                                      # trừ viền đã thêm
    assert steps.detect_box(None, np.zeros((10, 10, 3), np.uint8), run=lambda lm, r: None) is None


# 5 ---------------------------------------------------------------------------
def test_done_skip_and_force(tmp_path, world, capsys):
    imgs = tmp_path / 'imgs'
    write_images(imgs)
    argv = ['prepare', '--run', 'A', '--images', str(imgs), '--box', 'auto']
    m28.main(argv)
    capsys.readouterr()
    n_mp, n_lm = world.mp, world.lm
    m28.main(argv)
    out = capsys.readouterr().out
    assert out.count('bỏ qua') == 6
    assert (world.mp, world.lm) == (n_mp, n_lm)                                # không gọi landmarker
    m28.main(argv + ['--force', 'flags'])
    out = capsys.readouterr().out
    assert out.count('bỏ qua') == 5 and 'flags:' in out and 'bỏ qua flags' not in out
    assert (world.mp, world.lm) == (n_mp, n_lm)


# 6 ---------------------------------------------------------------------------
def test_review_auto_decisions(tmp_path, world, monkeypatch):
    imgs = wflw_setup(tmp_path)
    qc = types.ModuleType('m28core.autoqc')
    qc.run = lambda name, pts, cfg: ['guong'] if name == 'F_002' else []
    monkeypatch.setitem(sys.modules, 'm28core.autoqc', qc)
    m28.main(prep_args('W', imgs, '--box', 'wflw'))
    sug = {r['name']: r['suggestion'] for r in csv.DictReader(open('runs/W/autoqc/autoqc.csv'))}
    assert sug == {'F_001.png': 'can_xem', 'F_002.png': 'nen_gan_tay', 'F_003.png': 'can_xem'}
    m28.main(['review', '--run', 'W', '--review', 'auto'])
    t = steps.read_triage('runs/W/review/triage_auto.csv')
    assert t['F_001'][0] == 'nhan' and t['F_003'][0] == 'nhan'
    assert t['F_002'][0] == 'gan_tay'
    assert t['F_004'] == ('bo', 'khong_thay_mat')                              # no_face → Bỏ (theo P1 13/10)
    assert t['F_005'] == ('bo', 'khong_doc_duoc_anh')
    assert os.path.exists('runs/W/review/done.txt')


def test_review_excel_flow(tmp_path, world, capsys):
    imgs = wflw_setup(tmp_path)
    m28.main(prep_args('W', imgs, '--box', 'wflw'))
    with pytest.raises(SystemExit):
        m28.main(['review', '--run', 'W', '--review', 'excel', '--reviewer', 'P5'])
    assert 'autoqc.csv' in capsys.readouterr().out
    assert not os.path.exists('runs/W/review/done.txt')
    args = parse(['review', '--run', 'W', '--review', 'excel', '--reviewer', 'P5'])
    out = 'runs/W/review'
    path = os.path.join(out, 'triage_P5.csv')
    with open(path, 'w', encoding='utf-8', newline='') as f:                   # thiếu F_003
        f.write('name,decision,reason,seconds\nF_001.png,nhan,,\nF_002.png,gan_tay,lat guong,\n')
    assert steps.review(args, out) is False
    assert not os.path.exists(os.path.join(out, 'done.txt'))
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:               # kiểu Excel: BOM, dấu ;, chữ hoa
        f.write('name;decision;reason;seconds\nF_001.png;Nhan;;\nF_002.png;gan_tay;lat;\nF_003.png; bo ;mo;\n')
    assert steps.review(args, out) is True
    m28.main(['review', '--run', 'W', '--review', 'excel', '--reviewer', 'P5'])
    assert os.path.exists(os.path.join(out, 'done.txt'))                       # mặt no_face không bắt buộc có quyết định


def test_read_triage_formats(tmp_path):
    p = tmp_path / 't.csv'
    p.write_bytes('\ufeffa.png,nhan\nb,gan_tay,lý do\na.png,bo,đổi ý\n'.encode('utf-8'))   # không tiêu đề, dòng sau đè
    assert steps.read_triage(str(p)) == {'a': ('bo', 'đổi ý'), 'b': ('gan_tay', 'lý do')}
    p.write_text('file,reason,decision\nx.jpg,r,nhan\n', encoding='utf-8')                  # cột đảo, có tiêu đề
    assert steps.read_triage(str(p)) == {'x': ('nhan', 'r')}


# 7, 8 ------------------------------------------------------------------------
def test_push_dry_run(tmp_path, world):
    imgs = wflw_setup(tmp_path)
    to_review_auto('W', imgs, 'wflw')
    with pytest.raises(SystemExit):
        m28.main(['push', '--run', 'W', '--review', 'auto', '--dry-run'])
    assert os.path.exists('runs/W/xml/prelabel.xml')
    assert not os.path.exists('runs/W/push/done.txt')
    assert world.push == []


def test_push_real_with_fake_push(tmp_path, world, monkeypatch, capsys):
    imgs = tmp_path / 'imgs'
    write_images(imgs)
    qc = types.ModuleType('m28core.autoqc')
    qc.run = lambda name, pts, cfg: ['don_cuc'] if name == 'face_b' else []
    monkeypatch.setitem(sys.modules, 'm28core.autoqc', qc)
    json.dump({'project': 'm28', 'prefix': 'demo-'}, open('config/pipeline.json', 'w'))
    to_review_auto('A', imgs, 'auto')
    m28.main(['push', '--run', 'A', '--review', 'auto', '--images', str(imgs), '--task', 'demo-A'])
    assert len(world.push) == 1
    c = world.push[0]
    assert (c['task'], c['project'], c['prefix']) == ('demo-A', 'm28', 'demo-')
    assert c['run_dir'] == os.path.join('runs', 'A') and c['xml'] == os.path.join('runs', 'A', 'xml', 'prelabel.xml')
    assert sorted(os.path.basename(p) for p in c['nhan']) == ['face_a.png', 'face_c.png']
    assert [os.path.basename(p) for p in c['tay']] == ['face_b.png']
    assert not set(c['nhan']) & set(c['tay']) and all(os.path.exists(p) for p in c['nhan'] + c['tay'])
    assert sorted(read_xml('A')) == sorted(os.path.basename(p) for p in c['nhan'])   # ảnh tải lên = ảnh XML dùng
    assert os.path.exists('runs/A/push/done.txt')
    assert open('runs/A/push/manual_list.txt').read() == 'face_b.png'
    m28.main(['push', '--run', 'A', '--review', 'auto', '--images', str(imgs), '--task', 'demo-A'])
    assert len(world.push) == 1 and 'bỏ qua push' in capsys.readouterr().out


def test_push_wflw_uploads_crops_and_default_task_name(tmp_path, world):
    imgs = wflw_setup(tmp_path)
    to_review_auto('W', imgs, 'wflw')
    m28.main(['push', '--run', 'W', '--review', 'auto'])
    c = world.push[0]
    assert c['task'] == 'demo-W'
    assert sorted(os.path.basename(p) for p in c['nhan']) == ['F_001.png', 'F_002.png', 'F_003.png']
    assert all(os.path.dirname(p) == os.path.abspath('runs/W/crop/images') for p in c['nhan'])
    assert c['tay'] == []
    assert open('runs/W/push/rejected.csv').read().splitlines() == ['name,reason', 'F_004,khong_thay_mat', 'F_005,khong_doc_duoc_anh']


def test_push_refuses_non_demo_task(tmp_path, world):
    imgs = tmp_path / 'imgs'
    write_images(imgs)
    to_review_auto('A', imgs, 'auto')
    with pytest.raises(SystemExit):
        m28.main(['push', '--run', 'A', '--review', 'auto', '--task', 'm28-gold'])
    assert world.push == [] and not os.path.exists('runs/A/push/done.txt')


def test_push_review_file_bare_name_found_in_review_dir(tmp_path, world):
    imgs = tmp_path / 'imgs'
    write_images(imgs)
    m28.main(['prepare', '--run', 'A', '--images', str(imgs)])
    os.makedirs('runs/A/review')
    open('runs/A/review/triage_P5.csv', 'w').write('name,decision\nface_a,nhan\nface_b,bo\nface_c,gan_tay\n')
    m28.main(['push', '--run', 'A', '--review-file', 'triage_P5.csv', '--images', str(imgs)])
    c = world.push[0]
    assert [os.path.basename(p) for p in c['nhan']] == ['face_a.png'] and [os.path.basename(p) for p in c['tay']] == ['face_c.png']


def test_push_duplicate_image_name_detected(tmp_path, world):
    imgs = tmp_path / 'imgs'
    write_images(imgs)
    write_manifest(tmp_path, [('F_001.png', 'sub/face_a.png', 0, SIZES['sub/face_a.png']),
                              ('F_002.png', 'sub/face_a.png', 1, SIZES['sub/face_a.png'])])   # hai mặt, một ảnh gốc
    m28.main(prep_args('A', imgs, '--box', 'auto'))
    m28.main(['review', '--run', 'A', '--review', 'auto'])
    with pytest.raises(SystemExit, match='trùng'):
        m28.main(['push', '--run', 'A', '--review', 'auto', '--dry-run'])
    assert world.push == []
    m28.main(['prepare', '--run', 'B', '--list', 'data/list.csv', '--images', str(imgs), '--box', 'wflw'])  # ảnh cắt: tên khác nhau
    m28.main(['review', '--run', 'B', '--review', 'auto'])
    with pytest.raises(SystemExit):
        m28.main(['push', '--run', 'B', '--review', 'auto', '--dry-run'])
    assert sorted(read_xml('B')) == ['F_001.png', 'F_002.png']


def test_duplicate_names_without_manifest(tmp_path, world):
    imgs = tmp_path / 'imgs'
    for d in ('x', 'y'):
        (imgs / d).mkdir(parents=True)
        cv2.imwrite(str(imgs / d / 'same.png'), np.random.randint(0, 255, (100, 100, 3), np.uint8))
    with pytest.raises(SystemExit, match='cùng tên'):
        m28.main(['prepare', '--run', 'A', '--images', str(imgs)])


def test_push_needs_images_on_other_machine(tmp_path, world):
    imgs = tmp_path / 'imgs'
    write_images(imgs)
    to_review_auto('A', imgs, 'auto')
    meta = json.load(open('runs/A/crop/meta.json'))
    for m in meta.values():
        m['src'] = 'D:\\khac\\may\\' + m['rel'].replace('/', '\\')            # run chép từ máy khác
    json.dump(meta, open('runs/A/crop/meta.json', 'w'))
    with pytest.raises(SystemExit, match='--images'):
        m28.main(['push', '--run', 'A', '--review', 'auto'])
    m28.main(['push', '--run', 'A', '--review', 'auto', '--images', str(imgs)])
    assert all(p.startswith(str(imgs)) for p in world.push[0]['nhan'])


# 9 ---------------------------------------------------------------------------
def test_missing_mapping_module(tmp_path, world, monkeypatch):
    monkeypatch.delitem(sys.modules, 'm28core.mapping')
    imgs = tmp_path / 'imgs'
    write_images(imgs)
    with pytest.raises(SystemExit, match='m28core.mapping'):
        m28.main(['prepare', '--run', 'A', '--images', str(imgs)])
    assert not os.path.exists('runs/A/map50/done.txt')


def test_missing_push_module(tmp_path, world, monkeypatch):
    imgs = tmp_path / 'imgs'
    write_images(imgs)
    to_review_auto('A', imgs, 'auto')
    monkeypatch.delitem(sys.modules, 'm28core.push')
    with pytest.raises(SystemExit, match='m28core.push'):
        m28.main(['push', '--run', 'A', '--review', 'auto', '--images', str(imgs)])


# 10 --------------------------------------------------------------------------
def test_all_auto_dry_run_stops_at_push(tmp_path, world, capsys):
    imgs = wflw_setup(tmp_path)
    with pytest.raises(SystemExit, match='push'):
        m28.main(['all', '--run', 'F5', '--list', 'data/list.csv', '--images', str(imgs), '--box', 'wflw',
                  '--review', 'auto', '--dry-run'])
    assert 'Chạy thử' in capsys.readouterr().out
    assert os.path.exists('runs/F5/xml/prelabel.xml') and os.path.exists('runs/F5/review/done.txt')
    assert not os.path.exists('runs/F5/push/done.txt') and world.push == []


def test_all_real_then_rerun_skips_everything(tmp_path, world, capsys):
    imgs = wflw_setup(tmp_path)
    argv = ['all', '--run', 'F5', '--list', 'data/list.csv', '--images', str(imgs), '--box', 'wflw',
            '--review', 'auto', '--task', 'demo-F5']
    m28.main(argv)
    assert len(world.push) == 1 and world.collect == []                         # all không gọi collect
    capsys.readouterr()
    m28.main(argv)
    assert capsys.readouterr().out.count('bỏ qua') == 8 and len(world.push) == 1


# collect, cờ CLI ------------------------------------------------------------
def test_collect_needs_task_and_passes_args(tmp_path, world):
    with pytest.raises(SystemExit) as e:
        m28.main(['collect'])
    assert e.value.code == 2
    m28.main(['collect', '--task', 'demo-x', '--task', 'demo-y', '--dry-run', '--skip-export', '--tag', 't'])
    a = world.collect[0]
    assert a.task == ['demo-x', 'demo-y'] and a.dry_run and a.skip_export and a.tag == 't'


def test_run_required_and_log(tmp_path, world):
    with pytest.raises(SystemExit) as e:
        m28.main(['prepare'])
    assert e.value.code == 2
    imgs = tmp_path / 'imgs'
    write_images(imgs)
    m28.main(['prepare', '--run', 'A', '--images', str(imgs)])
    lines = open('runs/A/log.txt', encoding='utf-8').read().splitlines()
    assert [l.split('\t')[1:3] for l in lines] == [[s, 'xong'] for s in m28.PREPARE]


def test_review_ui_needs_app_and_stale_done_removed(tmp_path, world, monkeypatch):
    imgs = tmp_path / 'imgs'
    write_images(imgs)
    m28.main(['prepare', '--run', 'A', '--images', str(imgs)])
    with pytest.raises(SystemExit, match='review_app.py'):
        m28.main(['review', '--run', 'A', '--review', 'ui'])
    # có app giả đóng mà không bấm Xong: done.txt cũ (từ --force) không được tính
    app = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(steps.__file__))), 'review_app.py')
    calls = []
    monkeypatch.setattr(steps, '_need_file', lambda p, why: p)
    monkeypatch.setattr(steps.subprocess, 'call', lambda cmd: calls.append(cmd) or 0)
    os.makedirs('runs/A/review', exist_ok=True)
    open('runs/A/review/done.txt', 'w').write('ok')
    args = parse(['review', '--run', 'A', '--review', 'ui', '--reviewer', 'P5'])
    assert steps.review(args, 'runs/A/review') is False
    assert calls[0][1:] == [app, os.path.join('runs', 'A'), 'P5']
