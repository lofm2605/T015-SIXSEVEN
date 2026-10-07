"""Kiểm tĩnh chay.sh (bản Ubuntu của chay.bat): shebang, LF, cú pháp bash, không đụng token, không xoá runs/."""
import os
import re
import shutil
import subprocess

import pytest

SH = os.path.join(os.path.dirname(__file__), '..', 'chay.sh')


def _text():
    raw = open(SH, 'rb').read()
    assert b'\r' not in raw, 'chay.sh phải dùng LF'
    assert raw.startswith(b'#!/usr/bin/env bash')
    return raw.decode('utf-8')


@pytest.mark.skipif(shutil.which('bash') is None, reason='không có bash')
def test_bash_syntax_ok():
    assert subprocess.run(['bash', '-n', SH], capture_output=True).returncode == 0


def test_menu_covers_choices_and_safe_launch():
    t = _text()
    for n in range(1, 8):
        assert re.search(rf'^\s+{n}\) ', t, re.M), n
    assert 'review_app.py --nap' in t and '127.0.0.1' in t
    assert 'share=' not in t.lower() and 'CVAT_ACCESS_TOKEN=' not in t and 'export CVAT_ACCESS_TOKEN' not in t    # không đụng token, không chia sẻ
    assert 'grep -v -i "torch"' in t                                # không cài torch
    assert 'rm -rf .venv' in t and 'rm -rf runs' not in t          # chỉ xoá .venv, không bao giờ xoá runs/


def test_thu5_uses_incabin_package_only():
    t = _text()
    block = t.split('thu5() {', 1)[1].split('\nsmoke()', 1)[0]
    assert "w.writerow(['image','face_idx','seed'])" in block and "x['image'],x['face_idx']" in block
    assert '--images data/crops' in block and '--box crop' in block and '--dry-run' in block
