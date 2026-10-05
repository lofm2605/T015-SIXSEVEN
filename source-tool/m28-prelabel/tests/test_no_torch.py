"""Gói tool/ giao khách không được kéo theo torch/PIPNet (theo mẫu p1-du-lieu.md)."""
import os
import re
import subprocess
import sys

TOOL = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tool'))

CODE = """
import sys
sys.path.insert(0, {tool!r})
import m28core.steps
import m28   # chỉ import, không chạy main
assert "torch" not in sys.modules, "tool/ đang import torch"
print("ok: không có torch")
"""


def test_import_does_not_load_torch():
    r = subprocess.run([sys.executable, '-c', CODE.format(tool=TOOL)], capture_output=True, text=True,
                       encoding='utf-8')
    assert r.returncode == 0, r.stderr
    assert 'ok: không có torch' in r.stdout


def test_no_torch_import_in_source():
    bad = []
    for root, _, files in os.walk(TOOL):
        for fn in files:
            if fn.endswith('.py'):
                path = os.path.join(root, fn)
                for i, line in enumerate(open(path, encoding='utf-8'), 1):
                    if re.match(r'\s*(import|from)\s+torch(vision)?\b', line):
                        bad.append(f'{path}:{i}')
    assert not bad, bad
