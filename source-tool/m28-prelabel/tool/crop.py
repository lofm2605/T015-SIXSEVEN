"""Cắt mặt 512 x 512 theo manifest.csv và ghi gt98.json (P1, 6/10).

    python tool\\crop.py --manifest data\\manifest.csv --annotations <list_98pt...> --images <WFLW_images> --out data

Ra data\\crops\\<file>.png và data\\gt98.json (98 điểm theo toạ độ ảnh cắt, khoá là tên file).
Ảnh mặt WFLW (CC BY-NC-ND): chỉ để trên máy và repo riêng tư.
"""
import argparse
import csv
import json
import os

import cv2

from wflw import TEST_TXT, TRAIN_TXT, read_wflw, square_crop


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', default=os.path.join('data', 'manifest.csv'))
    p.add_argument('--annotations', required=True)
    p.add_argument('--images', required=True, help='thư mục WFLW_images')
    p.add_argument('--out', default='data')
    a = p.parse_args()

    rows = {'train': read_wflw(os.path.join(a.annotations, TRAIN_TXT)),
            'test': read_wflw(os.path.join(a.annotations, TEST_TXT))}
    os.makedirs(os.path.join(a.out, 'crops'), exist_ok=True)
    gt98, bad = {}, []
    with open(a.manifest, encoding='utf-8') as f:
        for m in csv.DictReader(f):
            r = rows[m['wflw_split']][int(m['wflw_line'])]
            assert r['image'] == m['wflw_image'], (m['file'], r['image'], m['wflw_image'])
            img = cv2.imread(os.path.join(a.images, *m['wflw_image'].split('/')))
            if img is None:
                bad.append(m['file'])
                continue
            crop, gt, _, _ = square_crop(img, r['bbox'], r['pts'])
            cv2.imwrite(os.path.join(a.out, 'crops', m['file']), crop)
            gt98[m['file']] = [[round(float(x), 3), round(float(y), 3)] for x, y in gt]
    with open(os.path.join(a.out, 'gt98.json'), 'w', encoding='utf-8') as f:
        json.dump(gt98, f)
    print(f'Đã cắt {len(gt98)} ảnh; không đọc được {len(bad)}: {bad[:5]}')
    raise SystemExit(1 if bad else 0)


if __name__ == '__main__':
    main()
