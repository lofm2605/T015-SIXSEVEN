import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tool'))
import flag_eval  # noqa: E402


def test_auroc_known_values():
    assert flag_eval.auroc([1, 2, 3, 4], [False, False, True, True]) == 1.0
    assert flag_eval.auroc([4, 3, 2, 1], [False, False, True, True]) == 0.0
    assert flag_eval.auroc([1, 1, 1, 1], [False, True, False, True]) == 0.5       # hoà hết
    assert np.isnan(flag_eval.auroc([1, 2], [False, False]))
    rng = np.random.default_rng(0)
    s = rng.normal(size=400)
    y = rng.random(400) < 0.3
    brute = np.mean([(a > b) + 0.5 * (a == b) for a in s[y] for b in s[~y]])
    assert abs(flag_eval.auroc(s, y) - brute) < 1e-9


def test_report_counts():
    rows = [('eye', 0.1 * i, 1.0 if i < 8 else 5.0, f'F_{i // 5}') for i in range(10)]      # 2 điểm sai, điểm số cao nhất
    lines = []
    table = flag_eval.report(rows, 3.0, out=lines.append)
    assert 'AUROC toàn bộ: 1.000' in lines[1]
    q85 = [t for t in table if t[0] == 0.85][0]
    assert q85[3] > 0 and q85[4] > 0
