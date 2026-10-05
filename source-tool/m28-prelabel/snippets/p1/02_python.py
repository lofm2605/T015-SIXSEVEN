# Trích từ de-tai-m28/p1-du-lieu.md — mục: Làm thế nào › 2. Chia tập (split.py, 6/10). Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
import random
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
    return 1 <= pose <= 2 and 2 <= occ <= 4
