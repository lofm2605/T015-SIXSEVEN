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


def test_default_run_opens_the_review_page_directly_and_menu_is_behind_an_argument():
    """Bấm chạy là vào thẳng trang rà soát, không hiện menu và không hỏi gì; menu và rà lại lượt qua tham số."""
    t = _text()
    tail = t.split('\nmenu() {', 1)[1]
    assert 'while true; do' in tail.split('\n}\n', 1)[0]                             # vòng menu nằm gọn trong hàm menu()
    dispatch = tail.split('\n}\n', 1)[1]
    assert 'case "${1:-}" in' in dispatch and 'menu) menu ;;' in dispatch and 'luot) luot "${2:-}" ;;' in dispatch and '*) mo_trang ;;' in dispatch
    assert 'while true' not in dispatch and 'read -r' not in dispatch                 # mặc định không hỏi gì
    assert 'LUOT="${1:-}"' in t and 'read -r -p "Tên lượt' in t                       # ./chay.sh luot NAP_001 không hỏi; menu mục 2 vẫn hỏi
    assert 'hoi_nguoi' not in t and 'Tên người rà (' not in t


@pytest.mark.skipif(shutil.which('bash') is None, reason='không có bash')
def test_running_without_args_never_waits_for_input(tmp_path):
    """Chạy thật với python giả: không có tham số thì gọi đúng review_app.py --nap rồi thoát, stdin đóng cũng không treo."""
    import stat
    d = tmp_path / 'm28'
    (d / 'tool').mkdir(parents=True)
    (d / '.venv' / 'bin').mkdir(parents=True)
    fake = d / '.venv' / 'bin' / 'python'
    fake.write_text('#!/usr/bin/env bash\necho "PY $@" >> "$(dirname "$0")/../../calls.txt"\n')
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    (d / '.venv' / 'bin' / 'activate').write_text(f'export PATH="{d / ".venv" / "bin"}:$PATH"\n')
    (d / 'face_landmarker.task').write_text('x')
    shutil.copy(SH, d / 'chay.sh')
    for args, want in (([], 'PY tool/review_app.py --nap'), (['luot', 'R1'], 'PY tool/review_app.py runs/R1')):
        if args:
            (d / 'runs' / 'R1').mkdir(parents=True, exist_ok=True)
        (d / 'calls.txt').unlink(missing_ok=True)
        r = subprocess.run(['bash', str(d / 'chay.sh')] + args, cwd=str(d), stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
        assert r.returncode == 0 and 'Chọn 1-7' not in r.stdout, (args, r.stdout, r.stderr)
        assert (d / 'calls.txt').read_text().strip() == want, (args, (d / 'calls.txt').read_text())
