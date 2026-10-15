"""Thử tool/tong_ket.py (công cụ của nhóm trưởng): gộp gói kết quả của thành viên, loại gói hỏng/trùng với lý do, tính ba chỉ số, xuất CSV + HTML. Dữ liệu giả."""
import csv
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
sys.path.insert(0, HERE)
import tong_ket  # noqa: E402
from dh_fake import du_an  # noqa: E402
from tk_fake import ANH, mo_phong, nd_goi, viet_goi  # noqa: E402


@pytest.fixture
def lead(tmp_path):
    """Máy nhóm trưởng: chỉ có repo (config) và một thư mục chứa gói thành viên gửi tới; KHÔNG có raw\\, runs\\ hay CVAT. Trả (project, thư mục gói)."""
    root = du_an(tmp_path / 'truong')
    ban = du_an(tmp_path / 'thanh_vien')
    mo_phong(ban)
    nhan = tmp_path / 'goi_nhan_duoc'
    nhan.mkdir()
    for f in sorted(os.listdir(os.path.join(ban, 'outputs', 'goi_nhom'))):
        shutil.copy(os.path.join(ban, 'outputs', 'goi_nhom', f), nhan)
    return root, str(nhan)


def test_tong_ket_gop_4_nguoi_ghi_html_csv_va_danh_sach_goi(lead, capsys):
    root, goi = lead
    assert tong_ket.main(['--project', root, '--vao', goi, '--ra', 'outputs/tong_ket']) == 0
    out = capsys.readouterr().out
    assert 'Đã dùng 4 gói' in out and 'bản trùng, bỏ: ketqua_P1_1410_NAP_001.json' in out and 'Đã ghi outputs/tong_ket/' in out and root not in out
    assert 'NME của nháp so với nhãn manual: 8 mặt' in out and 'assisted nhanh hơn manual 30,0%' in out and 'Tỉ lệ điểm phải sửa' in out
    base = os.path.join(root, 'outputs', 'tong_ket')
    d = os.path.join(base, os.listdir(base)[0])
    files = sorted(os.listdir(d))
    assert {'thong_ke.html', 'nme.csv', 'nme_nhap.csv', 'ti_le_sua.csv', 'thoi_gian.csv', 'thoi_gian_nguoi.csv', 'goi_da_dung.csv', 'goi_bi_loai.csv'} <= set(files)
    html = open(os.path.join(d, 'thong_ke.html'), encoding='utf-8').read()
    assert 'Tổng kết thí nghiệm M28' in html and '<img' not in html and '<script' not in html and root not in html and '/tmp' not in html and 'token' not in html.lower()
    assert 'low_conf' not in html and 'AUROC' not in html
    dung = list(csv.DictReader(open(os.path.join(d, 'goi_da_dung.csv'), encoding='utf-8-sig')))
    assert [r['ten_goi'] for r in dung] == [f'ketqua_P{i}_1410_NAP_001.zip' for i in (1, 2, 3, 4)]
    loai = list(csv.DictReader(open(os.path.join(d, 'goi_bi_loai.csv'), encoding='utf-8-sig')))
    assert len(loai) == 4 and all('trùng nội dung' in r['ly_do'] for r in loai)


def test_tong_ket_khong_dung_raw_runs_timing_cua_may_nhom_truong(lead):
    root, goi = lead
    import dh_fake
    from dh_fake import viet_nhan
    viet_nhan(root, 'demo-X', 'P9', '0101', {'a.png': dh_fake.mat_mau(1)})                       # nhãn rác trong raw\ của máy nhóm trưởng
    os.makedirs(os.path.join(root, 'outputs', 'ket_qua'))
    shutil.copy(os.path.join(goi, 'ketqua_P1_1410_NAP_001.zip'), os.path.join(root, 'outputs', 'ket_qua'))
    open(os.path.join(root, 'timing_P1.csv'), 'w', encoding='utf-8').write('date,person,condition,task,job,block,seq,face_id,seconds,warmup,interrupted,note\n'
                                                                           '2026-10-14,P1,manual,t,1,X,3,X_03,1,0,0,\n')
    assert tong_ket.main(['--project', root, '--vao', goi, '--ra', 'ra']) == 0
    d = os.path.join(root, 'ra', os.listdir(os.path.join(root, 'ra'))[0])
    html = open(os.path.join(d, 'thong_ke.html'), encoding='utf-8').read()
    assert 'P9' not in html and '0 file nhãn trong raw' in html and '0 file bấm giờ' in html and '4 gói kết quả' in html


def test_tong_ket_chi_tu_doc_ban_nhap_tay_khong_doc_goi_khac_trong_goi_nhom_cua_du_an(lead, capsys):
    root, goi = lead
    os.makedirs(os.path.join(root, 'outputs', 'goi_nhom'))
    viet_goi(root, nd_goi('P5', 'assisted', 30.0, n_nguoi_seed=4), 'outputs/goi_nhom')                 # gói đồng hồ nằm sẵn trong outputs/goi_nhom: không tự đọc (như trước)
    assert tong_ket.nhap_tay_them(root, [goi]) == []
    assert tong_ket.main(['--project', root, '--vao', goi, '--ra', 'ra']) == 0
    out = capsys.readouterr().out
    assert 'Đã dùng 4 gói' in out and 'Đọc thêm' not in out and 'P5' not in out.split('Đã dùng')[1].split('\n')[0]


def test_tong_ket_loai_goi_hong_sua_tay_trung_nhung_van_ra_ket_qua(lead, capsys):
    root, goi = lead
    open(os.path.join(goi, 'hong.zip'), 'wb').write(b'PK\x03\x04 hong')
    p = os.path.join(goi, 'ketqua_P2_1410_NAP_001.json')
    text = open(p, encoding='utf-8').read()
    open(os.path.join(goi, 'sua_tay.json'), 'w', encoding='utf-8').write(text.replace('"nguoi": "P2"', '"nguoi": "P3"', 1))            # sửa nội dung nhưng giữ sha256 cũ
    open(os.path.join(goi, 'ghi_chu.json'), 'w', encoding='utf-8').write('{"khong": "phai goi"}')
    assert tong_ket.main(['--project', root, '--vao', goi, '--ra', 'ra']) == 0
    out = capsys.readouterr().out
    assert 'Đã dùng 4 gói' in out and 'hong.zip' in out and 'sha256 không khớp' in out and 'không phải gói kết quả M28' in out
    d = os.path.join(root, 'ra', os.listdir(os.path.join(root, 'ra'))[0])
    loai = {r['ten_goi']: r['ly_do'] for r in csv.DictReader(open(os.path.join(d, 'goi_bi_loai.csv'), encoding='utf-8-sig'))}
    assert {'hong.zip', 'sua_tay.json', 'ghi_chu.json'} <= set(loai) and 'zip' in loai['hong.zip']


def test_tong_ket_hai_ban_cung_phien_giu_ban_moi(lead, tmp_path):
    root, goi = lead
    cu = json.load(open(os.path.join(goi, 'ketqua_P1_1410_NAP_001.json'), encoding='utf-8'))['noi_dung']
    from m28core import goi_kq
    moi = dict(cu, giay_phien=cu['giay_phien'] * 2, tao_luc='2026-10-15T08:00:00+07:00')
    json.dump(goi_kq.dong_goi(moi), open(os.path.join(goi, 'ban_moi_P1.json'), 'w', encoding='utf-8'))
    for f in ('ketqua_P1_1410_NAP_001.zip', 'ketqua_P1_1410_NAP_001.json'):
        os.remove(os.path.join(goi, f))
    json.dump(goi_kq.dong_goi(cu), open(os.path.join(goi, 'ketqua_P1_1410_NAP_001.json'), 'w', encoding='utf-8'))
    assert tong_ket.main(['--project', root, '--vao', goi, '--ra', 'ra']) == 0
    d = os.path.join(root, 'ra', os.listdir(os.path.join(root, 'ra'))[0])
    dung = [r['ten_goi'] for r in csv.DictReader(open(os.path.join(d, 'goi_da_dung.csv'), encoding='utf-8-sig'))]
    assert 'ban_moi_P1.json' in dung and 'ketqua_P1_1410_NAP_001.json' not in dung
    loai = [r['ly_do'] for r in csv.DictReader(open(os.path.join(d, 'goi_bi_loai.csv'), encoding='utf-8-sig'))]
    assert any('cũ hơn' in w for w in loai)


def test_tong_ket_ma_thoat_khi_khong_co_goi_nao_hay_duong_dan_sai(tmp_path, capsys):
    root = du_an(tmp_path / 'p')
    rong = tmp_path / 'rong'
    rong.mkdir()
    assert tong_ket.main(['--project', root, '--vao', str(rong)]) == 2
    assert 'không có gói nào dùng được' in capsys.readouterr().err
    open(rong / 'x.zip', 'wb').write(b'PK\x03\x04 hong')
    assert tong_ket.main(['--project', root, '--vao', str(rong)]) == 2
    err = capsys.readouterr().err
    assert 'bị loại' in err and 'x.zip' in err
    assert tong_ket.main(['--project', root, '--vao', str(tmp_path / 'khong_co')]) == 2 and 'không thấy' in capsys.readouterr().err
    assert not os.path.exists(os.path.join(root, 'outputs', 'tong_ket'))                          # lỗi thì không tạo thư mục kết quả
    with pytest.raises(SystemExit) as e:
        tong_ket.main(['--help'])
    out = capsys.readouterr().out
    assert e.value.code == 0 and '--vao' in out and '--ra' in out and 'nhóm trưởng' in out.lower() + 'nhóm trưởng'
    assert '--khong-nhap-tay' in out and 'goi_nhom' in out                                       # bản nhập tay (nhóm manual gán thẳng trong CVAT) nằm ở outputs\goi_nhom


def test_tong_ket_nhieu_vao_file_le_va_nguong_sua(lead, capsys):
    root, goi = lead
    one = os.path.join(goi, 'ketqua_P3_1410_NAP_001.zip')
    assert tong_ket.main(['--project', root, '--vao', one, '--vao', os.path.join(goi, 'ketqua_P1_1410_NAP_001.zip'), '--vao', os.path.join(goi, 'ketqua_P2_1410_NAP_001.zip'),
                          '--nguong-sua', '10', '--ra', 'ra']) == 0
    out = capsys.readouterr().out
    assert 'Đã dùng 3 gói' in out and 'ngưỡng 10,0% IOD' in out
    assert tong_ket.main(['--project', root, '--vao', goi, '--nguong-sua', '0.1', '--ra', 'ra']) == 2


def test_tong_ket_chay_nhu_script_va_khong_nap_gradio(lead):
    root, goi = lead
    r = subprocess.run([sys.executable, os.path.join(HERE, '..', 'tool', 'tong_ket.py'), '--project', root, '--vao', goi, '--ra', 'ra'], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0 and 'Đã dùng 4 gói' in r.stdout
    code = "import sys\nsys.path.insert(0, %r)\nimport tong_ket\nfor m in ('gradio', 'torch', 'cv2', 'mediapipe', 'cvat_sdk', 'pandas'):\n    assert m not in sys.modules, m\nprint('ok')\n" % os.path.join(HERE, '..', 'tool')
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0 and 'ok' in r.stdout, r.stderr


def test_tong_ket_dung_ten_nguoi_nhom_truong_da_dat(lead, capsys):
    """Nhóm trưởng đặt tên cho gói ở tab Thống kê (outputs\\ten_nguoi.json của dự án): tong_ket.py chạy trên cùng dự án cũng dùng tên đó."""
    from m28core import ten_nguoi
    root, goi = lead
    ph = json.load(open(os.path.join(goi, 'ketqua_P3_1410_NAP_001.json'), encoding='utf-8'))['noi_dung']['phien']
    ten_nguoi.dat(root, ph, 'Cuong', goi='ketqua_P3_1410_NAP_001.zip', goc='P3')
    assert tong_ket.main(['--project', root, '--vao', goi, '--ra', 'outputs/tong_ket']) == 0
    capsys.readouterr()
    base = os.path.join(root, 'outputs', 'tong_ket')
    html = open(os.path.join(base, os.listdir(base)[0], 'thong_ke.html'), encoding='utf-8').read()
    assert 'Tên người do nhóm trưởng đặt' in html and 'P3 → Cuong' in html
    rows = list(csv.DictReader(open(os.path.join(base, os.listdir(base)[0], 'thoi_gian_nguoi.csv'), encoding='utf-8-sig')))
    nguoi = {r.get('nguoi') or r.get('person') for r in rows}
    assert 'Cuong' in nguoi and 'P3' not in nguoi
