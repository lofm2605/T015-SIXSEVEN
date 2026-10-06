"""LỊCH SỬ, KHÔNG DÙNG (QĐ-001: bỏ WFLW). Chia tập WFLW và ghi manifest.csv (P1, 6/10). Chỉ cần file đáp án, không cần ảnh.
Đã thay bằng tool/inc_ingest.py (in-cabin); giữ để tham khảo.

    python tool\\legacy_wflw\\split.py --annotations <thư mục list_98pt_rect_attr_train_test> --out data\\manifest.csv --seed 5

F 300 (train). T 200 (test) chia tầng theo 6 cờ thành Tdev 100 / Ttest 100.
G 20, P 16, X 50, D 30 lấy từ phần test còn lại, chỉ mặt inside=True.
"""
import argparse
import csv
import os
import random
from collections import defaultdict

from wflw import ATTRS, TEST_TXT, TRAIN_TXT, crop_geometry, read_wflw

COLUMNS = ['file', 'set', 'block', 'seq', 'wflw_split', 'wflw_image', 'wflw_line',
           'x0', 'y0', 'x1', 'y1', 'left', 'top', 'k', *ATTRS, 'seed']
N = dict(F=300, T=200, G=20, P=16, X=50, D=30)


def flags(r):
    return tuple(r[a] for a in ATTRS)


def stratified_halves(rows, rng):
    """Chia đôi đúng bằng nhau, mỗi bộ 6 cờ chia đều cho hai nửa."""
    groups = defaultdict(list)
    for r in rows:
        groups[flags(r)].append(r)
    a, b = [], []
    for key in sorted(groups):
        g = groups[key][:]
        rng.shuffle(g)
        for r in g:
            (a if len(a) <= len(b) else b).append(r)
    return a, b


def make_x_blocks(easy, rest, seed):
    rng = random.Random(seed)
    easy, rest = easy[:], rest[:]
    rng.shuffle(easy)
    rng.shuffle(rest)
    rest.sort(key=lambda r: (r['pose'], r['occlusion']), reverse=True)
    blocks = [[] for _ in range(5)]
    for i, r in enumerate(rest):              # chia vòng 0-4, rồi 4-0
        k = i % 5 if (i // 5) % 2 == 0 else 4 - i % 5
        blocks[k].append(r)
    for k in range(5):
        rng.shuffle(blocks[k])                # trộn thứ tự seq 03-10
        blocks[k] = easy[2 * k:2 * k + 2] + blocks[k]
    return blocks


def block_ok(b):                              # 1-2 nghiêng lớn, 2-4 bị che
    pose = sum(r['pose'] for r in b)
    occ = sum(r['occlusion'] for r in b)
    return len(b) == 10 and 1 <= pose <= 2 and 2 <= occ <= 4


def split_sets(train_rows, test_rows, seed, max_tries=500):
    """Trả list dict {row, set, block, seq, file, seed}."""
    rng = random.Random(seed)
    for r in train_rows + test_rows:
        r['inside'] = crop_geometry(r['bbox'], r['pts'])[3]

    train = train_rows[:]
    rng.shuffle(train)
    F = train[:N['F']]

    test = test_rows[:]
    rng.shuffle(test)
    T, rest_test = test[:N['T']], test[N['T']:]
    tdev, ttest = stratified_halves(T, rng)

    pool = [r for r in rest_test if r['inside']]
    easy_pool = [r for r in pool if not any(flags(r))]
    assert len(easy_pool) >= 10, f'chỉ có {len(easy_pool)} mặt dễ (cả 6 cờ = 0), cần 10'
    easy = easy_pool[:10]
    used = {id(r) for r in easy}
    pool = [r for r in pool if id(r) not in used]
    need_other = N['G'] + N['P'] + N['D']
    assert len(pool) >= 40 + need_other, f'không đủ mặt inside: còn {len(pool)}'

    out = []

    def add(rows, name, fmt, blk=lambda i: '', seq=lambda i: i + 1, sd=seed):
        for i, r in enumerate(rows):
            out.append(dict(row=r, set=name, block=blk(i), seq=seq(i), seed=sd,
                            file=fmt(i)))

    add(F, 'F', lambda i: f'F_{i + 1:03d}.png')
    add(tdev, 'Tdev', lambda i: f'Tdev_{i + 1:03d}.png')
    add(ttest, 'Ttest', lambda i: f'Ttest_{i + 1:03d}.png')

    # X: thử lại 40 mặt còn lại với seed khác nếu có khối không đạt
    blocks, x_seed = None, None
    for t in range(max_tries):
        s = seed + t
        r2 = random.Random(s)
        cand = pool[:]
        r2.shuffle(cand)
        rest40 = cand[:40]
        b = make_x_blocks(easy, rest40, s)
        if all(block_ok(x) for x in b):
            blocks, x_seed = b, s
            used |= {id(r) for r in rest40}
            break
    assert blocks, f'không dựng được 5 khối X đạt sau {max_tries} lần thử'
    for k, b in enumerate(blocks, 1):
        add(b, 'X', lambda i, k=k: f'X{k}_{i + 1:02d}.png',
            blk=lambda i, k=k: str(k), sd=x_seed)

    others = [r for r in pool if id(r) not in used]
    G, P, D = (others[:N['G']], others[N['G']:N['G'] + N['P']],
               others[N['G'] + N['P']:need_other])
    for k in range(5):
        add(G[4 * k:4 * k + 4], 'G', lambda i, k=k: f'G{k + 1}_{i + 1:02d}.png',
            blk=lambda i, k=k: str(k + 1))
    for name, rows in (('a', P[:8]), ('b', P[8:])):
        add(rows, 'P', lambda i, n=name: f'P{n}_{i + 1:02d}.png', blk=lambda i, n=name: n)
    add(D, 'D', lambda i: f'D_{i + 1:02d}.png')

    assert len(out) == sum(N.values()), len(out)
    keys = [(o['row']['_split'], o['row']['line']) for o in out]
    assert len(set(keys)) == len(keys), 'trùng (ảnh, dòng) giữa các tập'
    return out


def write_manifest(items, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, COLUMNS)
        w.writeheader()
        for o in items:
            r = o['row']
            left, top, k, _, _ = crop_geometry(r['bbox'], r['pts'])
            x0, y0, x1, y1 = [round(float(v), 2) for v in r['bbox']]
            w.writerow(dict(file=o['file'], set=o['set'], block=o['block'], seq=o['seq'],
                            wflw_split=r['_split'], wflw_image=r['image'], wflw_line=r['line'],
                            x0=x0, y0=y0, x1=x1, y1=y1,
                            left=round(left, 4), top=round(top, 4), k=round(k, 6),
                            **{a: r[a] for a in ATTRS}, seed=o['seed']))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--annotations', required=True, help='thư mục có hai file list_98pt_rect_attr_*.txt')
    p.add_argument('--out', default=os.path.join('data', 'manifest.csv'))
    p.add_argument('--seed', type=int, default=5)
    a = p.parse_args()
    train = read_wflw(os.path.join(a.annotations, TRAIN_TXT))
    test = read_wflw(os.path.join(a.annotations, TEST_TXT))
    for r in train:
        r['_split'] = 'train'
    for r in test:
        r['_split'] = 'test'
    items = split_sets(train, test, a.seed)
    write_manifest(items, a.out)
    print(f'Đã ghi {len(items)} dòng vào {a.out} (seed {a.seed}; seed khối X ghi theo từng dòng)')


if __name__ == '__main__':
    main()
