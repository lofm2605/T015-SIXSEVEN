"""Kiểm tĩnh chay.bat (không chạy được cmd ở Linux): nhãn, CRLF, ASCII, không có lệnh nguy hiểm."""
import os
import re

BAT = os.path.join(os.path.dirname(__file__), '..', 'chay.bat')


def _text():
    raw = open(BAT, 'rb').read()
    assert b'\r\n' in raw and b'\n' not in raw.replace(b'\r\n', b''), 'chay.bat phải dùng CRLF'
    raw.decode('ascii')                                        # không dấu: cmd mọi codepage đều đọc được
    return raw.decode('ascii')


def test_all_goto_and_call_targets_exist():
    t = _text()
    labels = set(re.findall(r'^:([a-z_0-9]+)\s*$', t, re.M))
    used = set(re.findall(r'\b(?:goto|call)\s+:([a-z_0-9]+)', t, re.I))
    assert used <= labels, used - labels


def test_menu_covers_choice_range_and_safe_launch():
    t = _text()
    assert 'choice /C 1234567' in t and t.count('if errorlevel') >= 7
    levels = [int(x) for x in re.findall(r'^if errorlevel (\d+) goto :(?!menu)', t.split(':menu', 1)[1].split(':mo_trang')[0], re.M)]
    assert levels == sorted(levels, reverse=True) and levels[0] == 7                         # errorlevel kiểm từ lớn xuống nhỏ
    assert 'tool\\cvat_smoke.py' in t and 'choice /C CK' in t and 'goto :smoke' in t
    assert 'review_app.py --nap' in t and '127.0.0.1' in t
    assert 'share=' not in t.lower() and 'CVAT_ACCESS_TOKEN' not in t    # không đụng token, không chia sẻ
    assert 'findstr /V /I "torch"' in t                             # không cài torch
    assert 'rmdir /s /q ".venv"' in t and 'rmdir /s /q "runs' not in t    # chỉ xoá .venv, không bao giờ xoá runs\


def test_thu5_uses_incabin_package_only():
    """Mục 3 chạy thử 5 mặt F chỉ từ gói in-cabin: không hỏi thư mục ảnh ngoài, dùng ảnh cắt data\\crops."""
    t = _text()
    block = t.split('\n:thu5', 1)[1].split('\n:smoke', 1)[0]
    assert 'D:\\' not in block
    assert "w.writerow(['image','face_idx','seed'])" in block and "x['image'],x['face_idx']" in block
    assert '--images data\\crops' in block and '--box crop' in block and '--dry-run' in block
    menu = t.split(':menu', 1)[1].split(':mo_trang', 1)[0]
    assert 'in-cabin' in menu


def test_default_run_opens_the_review_page_directly_and_menu_is_behind_an_argument():
    t = _text()
    head = t.split('\n:co_model\r\n', 1)[1].split('\r\n:menu\r\n', 1)[0]
    assert 'if /i "%~1"=="menu" goto :menu' in head and 'goto :mo_thang' in head           # không tham số: vào thẳng trang rà soát
    assert 'if /i "%~1"=="luot" goto :luot_dong_lenh' in head
    mo = t.split('\n:mo_thang', 1)[1].split('\n:luot_dong_lenh', 1)[0]
    assert 'python tool\\review_app.py --nap' in mo and mo.rstrip().endswith('goto :het') and 'choice' not in mo and 'set /p' not in mo
    assert 'pause' in mo                                                                    # nhấp đúp: giữ cửa sổ để đọc thông báo lúc tắt trang hoặc lỗi
    luot = t.split('\n:luot_dong_lenh', 1)[1].split('\r\n:menu\r\n', 1)[0]
    assert 'python tool\\review_app.py runs\\%LUOT%' in luot and luot.rstrip().endswith('goto :het')
    assert luot.count('pause') == 3 and 'set /p LUOT=' in luot and 'Chua go ten luot' in luot                            # chay.bat luot (không kèm tên): hỏi tên lượt như chay.sh
    assert ':hoi_nguoi' not in t and 'Ten nguoi ra' not in t
