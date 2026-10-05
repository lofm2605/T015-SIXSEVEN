"""Thử split/crop/check_manifest bằng dữ liệu GIẢ (ngẫu nhiên, không phải mặt thật)."""
import csv
import os
import random
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tool'))
import check_manifest  # noqa: E402
import crop  # noqa: E402
import split  # noqa: E402
from wflw import TEST_TXT, TRAIN_TXT, read_wflw  # noqa: E402


def fake_file(path, n, rng, img_prefix):
    with open(path, 'w') as f:
        for i in range(n):
            cx, cy, s = rng.uniform(200, 800), rng.uniform(200, 800), rng.uniform(80, 200)
            pts = [(cx + rng.uniform(-.5, .5) * s * (1.3 if rng.random() < .03 else 1),
                    cy + rng.uniform(-.5, .5) * s) for _ in range(98)]
            box = (cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2)
            fl = [int(rng.random() < p) for p in (.13, .2, .2, .15, .29, .2)]
            if rng.random() < .35:
                fl = [0] * 6
            vals = [v for p in pts for v in p] + list(box) + fl + [f'{img_prefix}/img_{i}.jpg']
            f.write(' '.join(str(v) if isinstance(v, str) else f'{v:.3f}' if isinstance(v, float) else str(v)
                             for v in vals) + '\n')


def make_ann(tmp):
    rng = random.Random(1)
    d = tmp / 'ann'
    d.mkdir()
    fake_file(d / TRAIN_TXT, 7500, rng, 'a')
    fake_file(d / TEST_TXT, 2500, rng, 'b')
    return d


def test_split_manifest_and_crop(tmp_path, monkeypatch):
    ann = make_ann(tmp_path)
    train, test = read_wflw(str(ann / TRAIN_TXT)), read_wflw(str(ann / TEST_TXT))
    for r in train:
        r['_split'] = 'train'
    for r in test:
        r['_split'] = 'test'
    items = split.split_sets(train, test, seed=5)
    out = tmp_path / 'manifest.csv'
    split.write_manifest(items, str(out))
    assert check_manifest.main(str(out)) == 0
    # chạy lại cùng seed ra đúng cùng kết quả
    out2 = tmp_path / 'manifest2.csv'
    split.write_manifest(split.split_sets(train, test, seed=5), str(out2))
    assert out.read_text() == out2.read_text()
    # mọi mặt G, P, X, D phải inside
    by = {(r['_split'], r['line']): r for r in train + test}
    for o in items:
        if o['set'] in 'GPXD' or o['set'] in ('G', 'P', 'X', 'D'):
            assert o['row']['inside']

    # crop: ảnh giả 1000x1000 cho 4 dòng đầu manifest
    imgs = tmp_path / 'imgs'
    rows = list(csv.DictReader(open(out)))
    sub = rows[:4]
    for m in sub:
        p = imgs.joinpath(*m['wflw_image'].split('/'))
        p.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(p), np.random.randint(0, 255, (1000, 1000, 3), np.uint8))
    small = tmp_path / 'small.csv'
    with open(small, 'w', newline='') as f:
        w = csv.DictWriter(f, rows[0].keys())
        w.writeheader()
        w.writerows(sub)
    monkeypatch.setattr(sys, 'argv', ['crop.py', '--manifest', str(small), '--annotations', str(ann),
                                      '--images', str(imgs), '--out', str(tmp_path / 'data')])
    try:
        crop.main()
    except SystemExit as e:
        assert e.code == 0
    import json
    gt = json.load(open(tmp_path / 'data' / 'gt98.json'))
    assert len(gt) == 4 and all(len(v) == 98 for v in gt.values())
    img = cv2.imread(str(tmp_path / 'data' / 'crops' / sub[0]['file']))
    assert img.shape == (512, 512, 3)


def test_check_manifest_catches_errors(tmp_path):
    rows = [dict(file='F_001.png', set='F', block='', seq='1', wflw_image='a', wflw_line='0',
                 pose='0', occlusion='0', expression='0', illumination='0', makeup='0', blur='0')]
    assert check_manifest.check(rows)
