"""Mặt giả dùng chung cho các test hoán vị gương / lật (không phải mặt thật)."""
import numpy as np


def synthetic_run(perm, n=40, w=511.3, seed=0, noise=0.4):
    """Mặt giả đối xứng theo perm (ảnh lật ngang có đỉnh perm[i] ở (w - x_i, y_i)); trả (origs, flips)."""
    perm = np.asarray(perm)
    rng = np.random.default_rng(seed)
    base = rng.uniform(40, 470, size=(478, 2))
    for i in range(478):
        j = perm[i]
        if j == i:
            base[i, 0] = w / 2
        elif i < j:
            base[i, 0] = rng.uniform(40, w / 2 - 8)                       # đỉnh nhỏ hơn của cặp nằm nửa trái ảnh (như R trên mặt thẳng)
            base[j] = [w - base[i, 0], base[i, 1]]
    origs, flips = [], []
    for _ in range(n):
        o = base + rng.normal(scale=noise, size=base.shape)
        f = np.empty_like(o)
        f[perm] = np.stack([w - o[:, 0], o[:, 1]], axis=1) + rng.normal(scale=noise, size=o.shape)
        origs.append(o)
        flips.append(f)
    return origs, flips
