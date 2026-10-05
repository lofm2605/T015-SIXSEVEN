"""Kiểm manifest.csv. In lỗi và thoát mã 1 nếu sai (P1 chạy, P5 soát)."""
import csv
import re
import sys
from collections import Counter

EXPECT = {'F': 300, 'Tdev': 100, 'Ttest': 100, 'G': 20, 'P': 16, 'X': 50, 'D': 30}
FLAGS = ['pose', 'expression', 'illumination', 'makeup', 'occlusion', 'blur']
NAME = re.compile(r'^(F_\d{3}|Tdev_\d{3}|Ttest_\d{3}|G[1-5]_\d{2}|P[ab]_\d{2}|X[1-5]_\d{2}|D_\d{2})\.png$')


def check(rows):
    err = []
    cnt = Counter(r['set'] for r in rows)
    for s, n in EXPECT.items():
        if cnt.get(s, 0) != n:
            err.append(f'tập {s}: {cnt.get(s, 0)} mặt, cần {n}')
    for s in cnt.keys() - EXPECT.keys():
        err.append(f'tập lạ: {s}')
    keys = Counter((r['wflw_image'], r['wflw_line']) for r in rows)
    err += [f'trùng (wflw_image, wflw_line): {k}' for k, c in keys.items() if c > 1]
    names = Counter(r['file'] for r in rows)
    err += [f'trùng tên file: {k}' for k, c in names.items() if c > 1]
    err += [f'tên file sai mẫu: {r["file"]}' for r in rows if not NAME.match(r['file'])]
    for k in '12345':
        b = [r for r in rows if r['set'] == 'X' and r['block'] == k]
        if len(b) != 10:
            err.append(f'khối X{k}: {len(b)} mặt, cần 10')
            continue
        pose = sum(int(r['pose']) for r in b)
        occ = sum(int(r['occlusion']) for r in b)
        if not 1 <= pose <= 2:
            err.append(f'khối X{k}: {pose} mặt pose=1, cần 1-2')
        if not 2 <= occ <= 4:
            err.append(f'khối X{k}: {occ} mặt occlusion=1, cần 2-4')
        for r in b:
            if int(r['seq']) <= 2 and any(int(r[f]) for f in FLAGS):
                err.append(f'{r["file"]}: seq 1-2 của khối X phải có cả 6 cờ = 0')
    return err


def main(path='data/manifest.csv'):
    with open(path, encoding='utf-8') as f:
        err = check(list(csv.DictReader(f)))
    for e in err:
        print('LỖI:', e)
    print('manifest.csv đạt' if not err else f'{len(err)} lỗi')
    return 1 if err else 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:2]))
