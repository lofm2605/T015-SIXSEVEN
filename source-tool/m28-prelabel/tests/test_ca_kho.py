"""Thử tool/ca_kho.py (đánh dấu ca khó, gói họp, phiên họp, biên bản) bằng dữ liệu GIẢ dựng trong tmp_path.
Không cần trình duyệt, không cần gradio. Phần giao diện kiểm riêng bằng tests/e2e_ca_kho.py (tuỳ chọn).
"""
import csv
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import sys
import unicodedata
import warnings
import zipfile

import pytest

TOOL = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tool'))
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.dirname(__file__))
import ca_kho as ck  # noqa: E402
import review_app as ra  # noqa: E402
from test_review_app import make_run, write_png  # noqa: E402

PIL = pytest.importorskip('PIL')
from PIL import Image  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
T0 = datetime.datetime(2026, 10, 16, 20, 30, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
FACES = {'F_001': 0, 'F_002': 1, 'F_003': 0}


def at(minutes=0):
    return T0 + datetime.timedelta(minutes=minutes)


def write_manifest(root, names=('F_001', 'F_002', 'F_003'), source='yawdd'):
    """Manifest tối thiểu; source=None: không có cột `source` (manifest không nói rõ bộ dữ liệu)."""
    d = os.path.join(str(root), 'data')
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'manifest.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['file', 'set', 'block'] + ([] if source is None else ['source']))
        for n in names:
            w.writerow([n + '.png', 'F', ''] + ([] if source is None else [source]))


@pytest.fixture
def proj(tmp_path):
    """tmp_path = project_root; runs/CKA là lượt có manifest (nguồn yawdd), runs/NAP_001 có inbox."""
    write_manifest(tmp_path)
    cka = make_run(tmp_path, FACES, run='CKA', crops=list(FACES), overlays=list(FACES))
    nap = make_run(tmp_path, {'khach_1': 0}, run='NAP_001', crops=['khach_1'], overlays=['khach_1'])
    os.makedirs(os.path.join(nap, 'inbox'))
    return dict(root=str(tmp_path), runs=os.path.join(str(tmp_path), 'runs'), cka=cka, nap=nap)


def big_png(path, size=(1000, 800)):
    img = Image.new('RGB', size, (120, 140, 160))
    img.save(path)


def jpeg_bytes(size=(64, 48)):
    out = io.BytesIO()
    Image.new('RGB', size, (10, 200, 30)).save(out, 'JPEG')
    return out.getvalue()


def mark(proj, anh='F_001.png', nguoi='P1', loai='SWAP', run='CKA', note='', diem='', now=None, **kw):
    return ck.upsert_mark(os.path.join(proj['runs'], run), nguoi, anh, loai, diem, note, now=now or at(), **kw)


def pkg(proj, nguoi='P1', now=None, **kw):
    return ck.build_package(proj['runs'], proj['root'], nguoi, now=now or at(), **kw)


# ---------- ghi nhận ca khó ----------
def test_upsert_tao_sua_giu_khoa_nguoi_anh(proj):
    row, created = mark(proj, note='Mắt trái lệch', diem='mattrai_1;mattrai_2')
    assert created and row['luot'] == 'CKA' and row['loai'] == 'SWAP' and row['tao_luc'] == row['sua_luc']
    row2, created2 = mark(proj, loai='RULE', note='đổi ý', now=at(5))
    assert not created2 and row2['loai'] == 'RULE' and row2['tao_luc'] == row['tao_luc'] and row2['sua_luc'] != row['tao_luc']
    mark(proj, nguoi='P3', loai='MIRROR')                                  # người khác, cùng ảnh: dòng khác
    mark(proj, anh='F_002.png', loai='KHAC')
    rows = ck.read_marks(proj['cka'])
    assert [(r['nguoi'], r['anh'], r['loai']) for r in rows] == [('P1', 'F_001.png', 'RULE'), ('P3', 'F_001.png', 'MIRROR'),
                                                                 ('P1', 'F_002.png', 'KHAC')]
    raw = open(os.path.join(proj['cka'], 'ca_kho.csv'), 'rb').read()
    assert raw.startswith(b'\xef\xbb\xbf')                                  # UTF-8 có BOM cho Excel
    assert 'đổi ý' in raw.decode('utf-8-sig')


def test_upsert_khong_dung_triage_va_done(proj):
    tri = os.path.join(proj['cka'], 'review', 'triage_P1.csv')
    ra.append_row(tri, 'F_001.png', 'nhan', '', 1.0)
    before = open(tri, 'rb').read()
    mark(proj)
    assert open(tri, 'rb').read() == before
    assert not os.path.exists(os.path.join(proj['cka'], 'review', 'done.txt'))
    assert sorted(os.listdir(os.path.join(proj['cka'], 'review'))) == ['triage_P1.csv']


def test_xoa_ca(proj):
    mark(proj)
    mark(proj, anh='F_002.png')
    assert ck.delete_mark(proj['cka'], 'P1', 'F_001.png') is True
    assert ck.delete_mark(proj['cka'], 'P1', 'F_001.png') is False
    assert [r['anh'] for r in ck.read_marks(proj['cka'])] == ['F_002.png']


def test_loi_ghi_thanh_runerror_khong_doi_gi(proj, monkeypatch):
    mark(proj, note='gốc')
    path = os.path.join(proj['cka'], 'ca_kho.csv')
    before = open(path, 'rb').read()

    def boom(*a, **k):
        raise PermissionError('Excel đang mở')
    monkeypatch.setattr(ck.os, 'replace', boom)
    with pytest.raises(ck.RunError, match='Đóng Excel'):
        mark(proj, note='mới')
    monkeypatch.undo()
    assert open(path, 'rb').read() == before
    assert not [f for f in os.listdir(proj['cka']) if '.tmp' in f]          # không để file tạm
    assert ck.get_mark(proj['cka'], 'P1', 'F_001.png')['ghi_chu'] == 'gốc'


@pytest.mark.parametrize('kw,msg', [
    (dict(loai=''), 'Chọn loại'), (dict(loai='LA_HOAC'), 'Chọn loại'), (dict(note='x' * 501), 'tối đa 500'),
    (dict(nguoi='P 1'), 'không hợp lệ'), (dict(anh='../F_001.png'), 'Tên ảnh'), (dict(anh='F_001.jpg'), 'Tên ảnh'),
    (dict(diem='ngoai_ds', known_points=['a', 'b']), 'không có trong config'), (dict(diem='x y'), 'không hợp lệ'),
    (dict(diem=';'.join(f'p{i:02d}_abcdefghij' for i in range(30))), 'tối đa 200'),
])
def test_upsert_tu_choi_dau_vao_xau(proj, kw, msg):
    with pytest.raises(ck.RunError, match=msg):
        mark(proj, **kw)
    assert not os.path.exists(os.path.join(proj['cka'], 'ca_kho.csv'))


def test_ten_luot_va_thu_muc_ngoai_runs(proj, tmp_path):
    with pytest.raises(ck.RunError):
        ck.upsert_mark(os.path.join(proj['runs'], '_nap'), 'P1', 'F_001.png', 'SWAP')           # _nap không hợp lệ (RUN_RE)
    out = tmp_path / 'ngoai' / 'CKX'
    out.mkdir(parents=True)
    with pytest.raises(ck.RunError, match='ngoài'):
        ck.upsert_mark(str(out), 'P1', 'F_001.png', 'SWAP', runs_root=proj['runs'])


def test_doc_file_do_excel_luu_dau_cham_phay(proj):
    p = os.path.join(proj['cka'], 'ca_kho.csv')
    with open(p, 'w', encoding='utf-8-sig', newline='') as f:
        f.write('luot;anh;nguoi;loai;diem;ghi_chu;tao_luc;sua_luc;quyet_dinh_ra\r\nSAI_TEN;F_001.png;P1;SWAP;;ok;2026-10-16T20:30:00+07:00;;\r\n')
    r = ck.read_marks(proj['cka'])
    assert len(r) == 1 and r[0]['luot'] == 'CKA' and r[0]['ghi_chu'] == 'ok'                  # luot luôn theo tên thư mục
    mark(proj, anh='F_002.png')
    assert open(p, encoding='utf-8-sig').read().splitlines()[0].count(',') == 8              # ghi lại dạng chuẩn


# ---------- nguồn của lượt ----------
def test_run_source(proj, tmp_path):
    assert ck.run_source(proj['cka'], proj['root']) == 'yawdd'
    assert ck.run_source(proj['nap'], proj['root']) == 'khong_ro'                              # có inbox/
    make_run(tmp_path, {'F_001': 0, 'F_999': 0}, run='LA', crops=['F_001', 'F_999'])
    assert ck.run_source(os.path.join(proj['runs'], 'LA'), proj['root']) == 'khong_ro'         # có tên lạ
    shutil.rmtree(os.path.join(proj['root'], 'data'))
    assert ck.run_source(proj['cka'], proj['root']) == 'khong_ro'                              # thiếu manifest


def write_manifest_incab(root, sources):
    """Manifest in-cabin tối thiểu (có cột source): sources = {tên mặt không đuôi: 'yawdd' | 'drivface' | ...}."""
    d = os.path.join(str(root), 'data')
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'manifest.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['file', 'set', 'block', 'seq', 'source'])
        for i, (n, src) in enumerate(sources.items()):
            w.writerow([n + '.png', 'F', '', i + 1, src])


@pytest.mark.parametrize('sources,expect', [
    ({'F_001': 'yawdd', 'F_002': 'yawdd', 'F_003': 'yawdd'}, 'yawdd'),
    ({'F_001': 'drivface', 'F_002': 'drivface', 'F_003': 'drivface'}, 'drivface'),
    ({'F_001': 'yawdd', 'F_002': 'drivface', 'F_003': 'yawdd'}, 'yawdd+drivface'),                     # trộn hai bộ: một mã cố định, không phụ thuộc thứ tự
    ({'F_001': 'drivface', 'F_002': 'yawdd', 'F_003': 'drivface'}, 'yawdd+drivface'),
    ({'F_001': 'yawdd', 'F_002': 'yawdd', 'F_003': 'khach_hang'}, 'khong_ro'),                          # nguồn lạ ở một mặt: không chắc, coi là không rõ
    ({'F_001': 'yawdd', 'F_002': 'yawdd', 'F_003': ''}, 'khong_ro'),
    ({'F_001': 'YawDD', 'F_002': 'DRIVFACE', 'F_003': 'yawdd'}, 'yawdd+drivface'),                       # chữ hoa thường không quan trọng
])
def test_run_source_in_cabin_theo_cot_source(proj, sources, expect):
    write_manifest_incab(proj['root'], sources)
    assert ck.run_source(proj['cka'], proj['root']) == expect


def test_run_source_in_cabin_lop_khong_ro_van_giu(proj, tmp_path):
    write_manifest_incab(proj['root'], {'F_001': 'yawdd', 'F_002': 'yawdd', 'F_003': 'yawdd'})
    assert ck.run_source(proj['nap'], proj['root']) == 'khong_ro'                               # có inbox/: ảnh người dùng nạp
    make_run(tmp_path, {'F_001': 0, 'F_999': 0}, run='LA', crops=['F_001', 'F_999'])
    assert ck.run_source(os.path.join(proj['runs'], 'LA'), proj['root']) == 'khong_ro'          # có mặt không nằm trong manifest
    shutil.rmtree(os.path.join(proj['root'], 'data'))
    assert ck.run_source(proj['cka'], proj['root']) == 'khong_ro'                               # không có manifest
    write_manifest(proj['root'], source=None)                                                     # manifest không có cột source: không biết bộ nào -> khong_ro
    assert ck.run_source(proj['cka'], proj['root']) == 'khong_ro'


def test_goi_in_cabin_kem_anh_va_nguon_trong_manifest(proj):
    write_manifest_incab(proj['root'], {'F_001': 'yawdd', 'F_002': 'drivface', 'F_003': 'yawdd'})
    mark(proj)
    mark(proj, anh='khach_1.png', run='NAP_001', loai='CONG_CU')
    info = pkg(proj)
    assert info['nguon'] == {'CKA': 'yawdd+drivface', 'NAP_001': 'khong_ro'} and info['so_anh'] == 1       # lượt bộ dữ liệu có ảnh, lượt không rõ thì không
    assert list(info['bo_anh']) == ['NAP_001']
    with zipfile.ZipFile(info['path']) as zf:
        assert json.loads(zf.read('manifest.json'))['nguon'] == {'CKA': 'yawdd+drivface', 'NAP_001': 'khong_ro'}
        assert 'anh/CKA__F_001.jpg' in zf.namelist() and 'anh/NAP_001__khach_1.jpg' not in zf.namelist()
    assert pkg(proj, kem_khong_ro=True)['so_anh'] == 2                                         # tham số kem_khong_ro: "kèm cả lượt không rõ nguồn"
    k = ck.read_package(info['path'])
    assert k.nguon == {'CKA': 'yawdd+drivface', 'NAP_001': 'khong_ro'}                          # đọc lại gói mới


def test_goi_doc_nguon_hop_le_va_nguon_la_bi_tu_choi(tmp_path):
    for nguon in ('yawdd', 'drivface', 'yawdd+drivface'):
        q = zip_with(tmp_path / f'{nguon}.zip', good_entries(**{'manifest.json': good_manifest(nguon={'CKA': nguon})}))
        assert ck.read_package(q).nguon == {'CKA': nguon}
    bad = zip_with(tmp_path / 'bad.zip', good_entries(**{'manifest.json': good_manifest(nguon={'CKA': 'anh_khach_hang'})}))
    with pytest.raises(ck.GoiLoi, match='nguồn'):
        ck.read_package(bad)


def test_cung_mot_mat_giua_nhieu_nguoi_ap_cho_moi_bo_du_lieu(proj, tmp_path):
    """Hai người đánh dấu cùng F_001.png ở hai lượt khác tên: bộ dữ liệu (yawdd/drivface) thì cùng một mặt, lượt không rõ nguồn thì không."""
    write_manifest_incab(proj['root'], {'F_001': 'yawdd', 'F_002': 'yawdd', 'F_003': 'yawdd'})
    ckb = make_run(tmp_path, FACES, run='CKB', crops=list(FACES), overlays=list(FACES))
    make_run(tmp_path, {'khach_1': 0}, run='NAP_002', crops=['khach_1'], overlays=['khach_1'])
    os.makedirs(os.path.join(proj['runs'], 'NAP_002', 'inbox'))
    mark(proj, nguoi='P1', anh='F_001.png', run='CKA', now=at(0))
    mark(proj, nguoi='P3', anh='F_001.png', run='CKB', now=at(1))
    mark(proj, nguoi='P1', anh='khach_1.png', run='NAP_001', loai='CONG_CU', now=at(2))
    mark(proj, nguoi='P3', anh='khach_1.png', run='NAP_002', loai='CONG_CU', now=at(3))
    out = os.path.join(proj['root'], 'tam')
    os.makedirs(out)
    paths = []
    for who in ('P1', 'P3'):
        src = pkg(proj, nguoi=who, now=at(10), kem_khong_ro=True)['path']
        paths.append(shutil.copy(src, os.path.join(out, who + '.zip')))
    m = meeting(proj)
    m.import_packages([(paths[0], 'p1.zip'), (paths[1], 'p3.zip')], now=at(30))
    assert m.cases['P1|CKA|F_001.png']['nguon'] == m.cases['P3|CKB|F_001.png']['nguon'] == 'yawdd'
    assert sorted(m.same_face('P1|CKA|F_001.png')) == ['P1|CKA|F_001.png', 'P3|CKB|F_001.png']          # khác lượt nhưng cùng ảnh bộ dữ liệu: gộp
    assert m.same_face('P1|NAP_001|khach_1.png') == ['P1|NAP_001|khach_1.png']                           # không rõ nguồn: chỉ gộp trong cùng lượt
    assert ckb and ck.NGUON_VI['yawdd'] == 'YawDD' and ck.NGUON_VI['drivface'] == 'DrivFace'


def test_chu_tren_giao_dien_noi_ve_anh_tai_xe_khong_con_cc_by_nc_nd():
    html = ck.warn_html()
    assert 'tài xế' in html and 'YawDD' in html and 'DrivFace' in html and 'nhạy cảm' in html and 'CC BY' not in html


# ---------- xuất gói ----------
def test_build_package_ba_loai_muc_va_manifest(proj):
    big_png(os.path.join(proj['cka'], 'overlays', 'F_001.png'))
    mark(proj, note='Mắt', diem='mattrai_1')
    mark(proj, anh='F_002.png', loai='RULE')
    info = pkg(proj)
    assert info['so_ca'] == 2 and info['so_anh'] == 2 and not info['replaced'] and info['rel'].endswith('ca_kho_P1_1610.zip')
    assert info['path'] == os.path.join(proj['root'], 'outputs', 'ca_kho', 'ca_kho_P1_1610.zip')
    with zipfile.ZipFile(info['path']) as zf:
        names = sorted(zf.namelist())
        assert names == ['anh/CKA__F_001.jpg', 'anh/CKA__F_002.jpg', 'ca_kho.csv', 'manifest.json']
        man = json.loads(zf.read('manifest.json'))
        assert man == {'loai_goi': 'm28-ca-kho', 'phien_ban': 1, 'nguoi': 'P1', 'ngay': '2026-10-16', 'tao_luc': ck.iso(at()), 'luot': ['CKA'],
                       'nguon': {'CKA': 'yawdd'}, 'so_ca': 2, 'so_anh': 2, 'kem_anh': True}
        blob = json.dumps(man) + zf.read('ca_kho.csv').decode('utf-8-sig')
        assert proj['root'] not in blob and '@' not in blob and 'token' not in blob.lower()
        assert {i.filename: i.compress_type for i in zf.infolist()}['anh/CKA__F_001.jpg'] == zipfile.ZIP_STORED
        assert {i.filename: i.compress_type for i in zf.infolist()}['manifest.json'] == zipfile.ZIP_DEFLATED
        im = Image.open(io.BytesIO(zf.read('anh/CKA__F_001.jpg')))
        assert im.format == 'JPEG' and max(im.size) <= 480 and not im.getexif()
        rows = list(csv.DictReader(io.StringIO(zf.read('ca_kho.csv').decode('utf-8-sig'))))
        assert [r['thumb'] for r in rows] == ['anh/CKA__F_001.jpg', 'anh/CKA__F_002.jpg'] and rows[0]['diem'] == 'mattrai_1'
    assert not [f for f in os.listdir(os.path.dirname(info['path'])) if '.tmp' in f]


def test_luot_khong_ro_mac_dinh_khong_kem_anh_co_co_thi_kem(proj):
    mark(proj)
    mark(proj, anh='khach_1.png', run='NAP_001', loai='CONG_CU')
    info = pkg(proj)
    assert info['so_ca'] == 2 and info['so_anh'] == 1 and list(info['bo_anh']) == ['NAP_001']
    with zipfile.ZipFile(info['path']) as zf:
        assert 'anh/NAP_001__khach_1.jpg' not in zf.namelist()
        assert json.loads(zf.read('manifest.json'))['nguon'] == {'CKA': 'yawdd', 'NAP_001': 'khong_ro'}
    info2 = pkg(proj, kem_khong_ro=True)
    assert info2['so_anh'] == 2 and info2['replaced'] and not info2['bo_anh']                  # cùng ngày thì thay gói cũ
    info3 = pkg(proj, kem_anh=False)
    assert info3['so_anh'] == 0 and set(info3['bo_anh']) == {'CKA', 'NAP_001'}
    info4 = pkg(proj, luot_filter=['CKA'])
    assert info4['so_ca'] == 1 and info4['luot'] == ['CKA']


def test_build_package_khong_ca_tu_choi_va_khong_tao_file(proj):
    with pytest.raises(ck.RunError, match='Chưa có ca khó'):
        pkg(proj)
    mark(proj, nguoi='P3')
    with pytest.raises(ck.RunError, match='Chưa có ca khó'):
        pkg(proj, nguoi='P1')                                                                  # ca của người khác không vào gói
    assert not os.path.exists(os.path.join(proj['root'], 'outputs', 'ca_kho', 'ca_kho_P1_1610.zip'))


def test_build_package_qua_dung_luong(proj, monkeypatch):
    mark(proj)
    monkeypatch.setattr(ck, 'MAX_GOI', 100)
    with pytest.raises(ck.RunError, match='vượt'):
        pkg(proj)
    d = os.path.join(proj['root'], 'outputs', 'ca_kho')
    assert not [f for f in os.listdir(d)]                                                       # không để file tạm hay gói dở
    monkeypatch.undo()
    monkeypatch.setattr(ck, 'MAX_CA', 1)
    mark(proj, anh='F_002.png')
    with pytest.raises(ck.RunError, match='tối đa 1 ca'):
        pkg(proj)


def test_exif_bi_bo_va_xoay(proj, tmp_path):
    img = Image.new('RGB', (200, 100), (1, 2, 3))
    exif = Image.Exif()
    exif[0x0112] = 6                                                                           # xoay 90 độ
    exif[0x010F] = 'camera-bi-mat'
    jp = tmp_path / 'x.jpg'
    img.save(jp, 'JPEG', exif=exif)
    data = ck.encode_jpeg(str(jp), 480, 72)
    out = Image.open(io.BytesIO(data))
    assert out.size == (100, 200) and not out.getexif() and b'camera-bi-mat' not in data


# ---------- nhập gói: zip độc hại ----------
def zip_with(path, entries, manifest=None):
    """entries: [(tên, bytes)] ghi nguyên văn tên (không chuẩn hoá). manifest=None: không thêm."""
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        with zipfile.ZipFile(path, 'w') as zf:
            for name, data in entries:
                zi = zipfile.ZipInfo(name, date_time=(2026, 10, 16, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(zi, data)
    return str(path)


def good_manifest(**kw):
    m = {'loai_goi': 'm28-ca-kho', 'phien_ban': 1, 'nguoi': 'P1', 'ngay': '2026-10-16', 'tao_luc': ck.iso(at()), 'luot': ['CKA'],
         'nguon': {'CKA': 'yawdd'}, 'so_ca': 1, 'so_anh': 1, 'kem_anh': True}
    m.update(kw)
    return json.dumps(m).encode()


def good_csv(rows=None, cols=None):
    rows = rows if rows is not None else [dict(luot='CKA', anh='F_001.png', nguoi='P1', loai='SWAP', diem='', ghi_chu='x', tao_luc=ck.iso(at()),
                                               sua_luc=ck.iso(at()), quyet_dinh_ra='', thumb='anh/CKA__F_001.jpg')]
    return ck.csv_text(cols or ck.PKG_COLS, rows).encode('utf-8-sig')


def good_entries(**over):
    base = {'manifest.json': good_manifest(), 'ca_kho.csv': good_csv(), 'anh/CKA__F_001.jpg': jpeg_bytes()}
    base.update(over)
    return [(k, v) for k, v in base.items() if v is not None]


def test_goi_tot_doc_duoc(tmp_path):
    p = zip_with(tmp_path / 'g.zip', good_entries())
    k = ck.read_package(p)
    assert k.nguoi == 'P1' and k.so_ca == 1 and k.rows[0]['thumb_bytes'][:2] == b'\xff\xd8' and len(k.sha256) == 64
    assert k.sha256 == hashlib.sha256(open(p, 'rb').read()).hexdigest()


@pytest.mark.parametrize('ten', ['../x.jpg', '/abs.jpg', 'anh\\x.jpg', 'C:x.jpg', 'anh/x.py', 'anh/../x.jpg', 'evil.py', 'anh/a b.jpg',
                                 'anh/x.jpg.exe', 'ca_kho.csv.bak', 'anh/' + 'a' * 101 + '.jpg'])
def test_ten_muc_la_bi_tu_choi(tmp_path, ten):
    p = zip_with(tmp_path / 'g.zip', good_entries() + [(ten, b'x')])
    with pytest.raises(ck.GoiLoi, match='tên không hợp lệ'):
        ck.read_package(p)


def test_symlink_bi_tu_choi(tmp_path):
    path = tmp_path / 'g.zip'
    with zipfile.ZipFile(path, 'w') as zf:
        for name, data in good_entries():
            zf.writestr(name, data)
        zi = zipfile.ZipInfo('anh/link.jpg')
        zi.external_attr = (0o120777 << 16)
        zf.writestr(zi, '/etc/passwd')
    with pytest.raises(ck.GoiLoi, match='symlink'):
        ck.read_package(str(path))


def test_muc_trung_ten_bi_tu_choi(tmp_path):
    p = zip_with(tmp_path / 'g.zip', good_entries() + [('manifest.json', good_manifest())])
    with pytest.raises(ck.GoiLoi, match='hai lần'):
        ck.read_package(p)


def test_zip_bomb_anh_qua_lon(tmp_path):
    big = jpeg_bytes((3000, 3000))
    zero = b'\xff\xd8' + b'\0' * (6 * 1024 * 1024)                                             # nén cực nhỏ, giải nén 6 MB
    p = zip_with(tmp_path / 'g.zip', good_entries(**{'anh/CKA__F_001.jpg': zero}))
    assert os.path.getsize(p) < 100 * 1024
    with pytest.raises(ck.GoiLoi, match='lớn hơn'):
        ck.read_package(p)
    del big


def test_zip_bomb_tong_giai_nen(tmp_path, monkeypatch):
    monkeypatch.setattr(ck, 'MAX_TONG', 5 * 1024 * 1024)
    rows = [dict(luot='CKA', anh=f'F_{i:03d}.png', nguoi='P1', loai='SWAP', diem='', ghi_chu='', tao_luc=ck.iso(at()), sua_luc=ck.iso(at()),
                 quyet_dinh_ra='', thumb=f'anh/CKA__F_{i:03d}.jpg') for i in range(1, 9)]
    ents = [('manifest.json', good_manifest(so_ca=8)), ('ca_kho.csv', good_csv(rows))]
    img = jpeg_bytes((1000, 1000)) + b'\0' * (900 * 1024)                                      # ~ 0,9 MB mỗi ảnh, tổng > 5 MB
    ents += [(r['thumb'], img) for r in rows]
    p = zip_with(tmp_path / 'g.zip', ents)
    with pytest.raises(ck.GoiLoi, match='Tổng dung lượng'):
        ck.read_package(p)


def test_khai_file_size_nho_nhung_giai_nen_lon(tmp_path):
    """Header (central directory) khai file_size nhỏ hơn thật: không được đọc quá giới hạn, và gói bị từ chối."""
    path = tmp_path / 'g.zip'
    zero = b'\xff\xd8' + b'\0' * (3 * 1024 * 1024)
    zip_with(path, good_entries(**{'anh/CKA__F_001.jpg': zero}))
    raw = bytearray(open(path, 'rb').read())
    real = len(zero).to_bytes(4, 'little')
    i = raw.rfind(real)                                                                        # file_size trong central directory
    assert i > 0
    raw[i:i + 4] = (100).to_bytes(4, 'little')
    open(path, 'wb').write(bytes(raw))
    with pytest.raises(ck.GoiLoi):
        ck.read_package(str(path))


def test_qua_so_muc(tmp_path):
    ents = good_entries() + [(f'anh/x{i}.jpg', b'x') for i in range(ck.MAX_CA + 3)]
    with pytest.raises(ck.GoiLoi, match='nhiều hơn'):
        ck.read_package(zip_with(tmp_path / 'g.zip', ents))


def test_file_khong_phai_zip_va_qua_to(tmp_path, monkeypatch):
    p = tmp_path / 'g.zip'
    p.write_bytes(b'day khong phai zip')
    with pytest.raises(ck.GoiLoi, match='Không phải file zip'):
        ck.read_package(str(p))
    monkeypatch.setattr(ck, 'MAX_GOI', 10)
    with pytest.raises(ck.GoiLoi, match='lớn hơn'):
        ck.read_package(str(p))


@pytest.mark.parametrize('over,msg', [
    ({'manifest.json': None}, 'Thiếu manifest.json'), ({'ca_kho.csv': None}, 'Thiếu ca_kho.csv'),
    ({'manifest.json': b'{khong json'}, 'không phải JSON'), ({'manifest.json': b'[1, 2]'}, 'đối tượng JSON'),
    ({'manifest.json': good_manifest(loai_goi='khac')}, 'loai_goi'), ({'manifest.json': good_manifest(phien_ban=2)}, 'phiên bản'),
    ({'manifest.json': good_manifest(phien_ban=True)}, 'phiên bản'), ({'manifest.json': good_manifest(nguoi='P 1')}, 'tên người'),
    ({'manifest.json': good_manifest(nguoi='../P1')}, 'tên người'), ({'manifest.json': good_manifest(ngay='16/10/2026')}, 'ngày'),
    ({'manifest.json': good_manifest(so_ca=2)}, 'ghi 2 ca'), ({'manifest.json': good_manifest(nguoi='P3')}, 'khác người'),
    ({'manifest.json': good_manifest(luot=['../x'])}, 'lượt'),
    ({'manifest.json': b'{' + b' ' * (70 * 1024) + b'}'}, 'lớn hơn'),
    ({'ca_kho.csv': good_csv([dict(luot='CKA', anh='F_001.png', nguoi='P1', loai='LA', diem='', ghi_chu='', tao_luc=ck.iso(at()),
                                   sua_luc='', quyet_dinh_ra='', thumb='')])}, 'loại'),
    ({'ca_kho.csv': good_csv(cols=['luot', 'anh', 'nguoi', 'loai'], rows=[dict(luot='CKA', anh='F_001.png', nguoi='P1', loai='SWAP')])},
     'thiếu cột'),
    ({'ca_kho.csv': good_csv([dict(luot='CKA', anh='../F.png', nguoi='P1', loai='SWAP', diem='', ghi_chu='', tao_luc=ck.iso(at()),
                                   sua_luc='', quyet_dinh_ra='', thumb='')])}, 'tên ảnh'),
    ({'ca_kho.csv': good_csv([dict(luot='CKA', anh='F_001.png', nguoi='P1', loai='SWAP', diem='', ghi_chu='x' * 501, tao_luc=ck.iso(at()),
                                   sua_luc='', quyet_dinh_ra='', thumb='')])}, 'ghi chú'),
    ({'ca_kho.csv': good_csv([dict(luot='CKA', anh='F_001.png', nguoi='P1', loai='SWAP', diem='', ghi_chu='', tao_luc='hôm qua',
                                   sua_luc='', quyet_dinh_ra='', thumb='')])}, 'thời gian'),
    ({'ca_kho.csv': good_csv([dict(luot='CKA', anh='F_001.png', nguoi='P1', loai='SWAP', diem='', ghi_chu='', tao_luc=ck.iso(at()),
                                   sua_luc='', quyet_dinh_ra='', thumb='anh/CKA__F_099.jpg')])}, 'không có trong gói'),
    ({'ca_kho.csv': good_csv([dict(luot='CKA', anh='F_001.png', nguoi='P1', loai='SWAP', diem='', ghi_chu='', tao_luc=ck.iso(at()),
                                   sua_luc='', quyet_dinh_ra='', thumb='../etc/x.jpg')])}, 'không có trong gói'),
    ({'anh/CKA__F_001.jpg': b'khong phai anh'}, 'hỏng'),
    ({'anh/CKA__F_001.jpg': (lambda b: (Image.new('RGB', (8, 8)).save(b, 'PNG'), b.getvalue())[1])(io.BytesIO())}, 'không phải JPEG'),
    ({'anh/CKA__F_001.jpg': jpeg_bytes((2500, 2500))}, 'megapixel'),
    ({'anh/CKA__F_001.jpg': jpeg_bytes()[:-30]}, 'hỏng'),
])
def test_goi_sai_bi_tu_choi(tmp_path, over, msg):
    p = zip_with(tmp_path / 'g.zip', good_entries(**over))
    with pytest.raises(ck.GoiLoi, match=msg):
        ck.read_package(p)


def test_trung_khoa_trong_goi_loi_ca_goi(tmp_path):
    r = dict(luot='CKA', anh='F_001.png', nguoi='P1', loai='SWAP', diem='', ghi_chu='', tao_luc=ck.iso(at()), sua_luc=ck.iso(at()),
             quyet_dinh_ra='', thumb='')
    p = zip_with(tmp_path / 'g.zip', good_entries(**{'manifest.json': good_manifest(so_ca=2), 'ca_kho.csv': good_csv([r, dict(r, loai='RULE')])}))
    with pytest.raises(ck.GoiLoi, match='hai lần trong gói'):
        ck.read_package(p)


def test_goi_ma_hoa_bi_tu_choi(tmp_path):
    p = tmp_path / 'g.zip'
    zip_with(p, good_entries())
    raw = bytearray(p.read_bytes())
    for sig, off in ((b'PK\x03\x04', 6), (b'PK\x01\x02', 8)):                                  # đặt cờ mã hoá ở mọi header
        i = 0
        while (i := raw.find(sig, i)) >= 0:
            raw[i + off] |= 1
            i += 4
    p.write_bytes(bytes(raw))
    with pytest.raises(ck.GoiLoi, match='mã hoá'):
        ck.read_package(str(p))


def test_khong_giai_nen_ra_dia(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p = zip_with(tmp_path / 'g.zip', good_entries())
    before = set(os.listdir(tmp_path))
    ck.read_package(p)
    assert set(os.listdir(tmp_path)) == before


# ---------- phiên họp ----------
def make_packages(proj):
    """Hai gói: P1 (2 ca, ảnh bộ dữ liệu) và P3 (2 ca: cùng F_001 + một ca khác); trả (đường dẫn P1, đường dẫn P3)."""
    mark(proj, nguoi='P1', anh='F_001.png', loai='SWAP', note='Hai điểm mắt đổi chỗ', diem='mattrai_1;mattrai_2', now=at(0))
    mark(proj, nguoi='P1', anh='F_002.png', loai='CONG_CU', note='Khó kéo điểm', now=at(1))
    mark(proj, nguoi='P3', anh='F_001.png', loai='RULE', note='Chưa có quy tắc cho kính', now=at(2))
    mark(proj, nguoi='P3', anh='F_003.png', loai='GL_MO_HO', note='Mơ hồ | có dấu ống', now=at(3))
    a = pkg(proj, nguoi='P1', now=at(10))['path']
    b = pkg(proj, nguoi='P3', now=at(10))['path']
    out = os.path.join(proj['root'], 'tam')
    os.makedirs(out, exist_ok=True)
    pa, pb = os.path.join(out, 'a.zip'), os.path.join(out, 'b.zip')
    shutil.copy(a, pa)
    shutil.copy(b, pb)
    return pa, pb


def meeting(proj, now=None):
    return ck.Meeting.create(ck.serve_dir(proj['root']), 'P5', now or at(20))


def test_phien_tao_ten_trung(proj):
    a = meeting(proj)
    b = meeting(proj)
    assert (a.name, b.name) == ('hop_1610', 'hop_1610_2')
    assert ck.Meeting.list_sessions(ck.serve_dir(proj['root'])) == ['hop_1610_2', 'hop_1610'] or set(
        ck.Meeting.list_sessions(ck.serve_dir(proj['root']))) == {'hop_1610', 'hop_1610_2'}
    with pytest.raises(ck.RunError):
        ck.Meeting.load(ck.serve_dir(proj['root']), '../etc')
    with pytest.raises(ck.RunError):
        ck.Meeting.load(ck.serve_dir(proj['root']), 'hop_9999')


def test_nhap_hai_goi_nhap_lai_goi_loi(proj, tmp_path):
    pa, pb = make_packages(proj)
    evil = zip_with(tmp_path / 'evil.zip', good_entries() + [('../evil.jpg', b'x')])
    m = meeting(proj)
    rep = m.import_packages([(pa, 'a.zip'), (evil, 'evil.zip'), (pb, 'b.zip'), (pa, 'a_copy.zip')], now=at(30))
    assert [r['trang_thai'] for r in rep] == ['ok', 'loi', 'ok', 'da_nhap']
    assert (rep[0]['nguoi'], rep[0]['moi'], rep[0]['cap_nhat'], rep[0]['trung']) == ('P1', 2, 0, 0)
    assert 'tên không hợp lệ' in rep[1]['ly_do'] and 'đã nhập rồi' in rep[3]['ly_do']
    assert len(m.cases) == 4 and len(m.data['goi']) == 2
    c = m.cases['P1|CKA|F_001.png']
    assert c['thumb'] == 'anh/P1__CKA__F_001.jpg' and os.path.isfile(os.path.join(m.dir, 'anh', 'P1__CKA__F_001.jpg'))
    assert (c['trang_thai'], c['loai_backlog'], c['ghi_backlog'], c['nguon']) == ('mo', 'Guideline mơ hồ', False, 'yawdd')   # SWAP: lỗi đặt điểm
    assert m.cases['P1|CKA|F_002.png']['loai_backlog'] == 'Pain point công cụ' and m.cases['P1|CKA|F_002.png']['ghi_backlog'] is True
    assert m.cases['P3|CKA|F_001.png']['loai_backlog'] == 'Guideline chưa nói tới'
    assert sorted(os.listdir(os.path.join(m.dir, 'anh'))) == sorted(
        ['P1__CKA__F_001.jpg', 'P1__CKA__F_002.jpg', 'P3__CKA__F_001.jpg', 'P3__CKA__F_003.jpg'])
    assert m.counts() == {'loai': {'SWAP': 1, 'CONG_CU': 1, 'RULE': 1, 'GL_MO_HO': 1}, 'nguoi': {'P1': 2, 'P3': 2}, 'trang_thai': {'mo': 4}}
    assert m.same_face('P1|CKA|F_001.png') == ['P1|CKA|F_001.png', 'P3|CKA|F_001.png']                                    # SWAP trước RULE
    assert m.filtered(nguoi='P3') == ['P3|CKA|F_001.png', 'P3|CKA|F_003.png'] and m.filtered(text='ống') == ['P3|CKA|F_003.png']
    assert m.filtered(loai='SWAP', trang_thai='da_chot') == []


def test_goi_moi_hon_cap_nhat_nhung_giu_truong_nguoi_to_chuc(proj):
    pa, _pb = make_packages(proj)
    m = meeting(proj)
    m.import_packages([(pa, 'a.zip')], now=at(30))
    key = 'P1|CKA|F_001.png'
    m.set_fields(key, 'dang_ban', 'Chốt hai điểm hàm', 'P2', 'Guideline mâu thuẫn', True, '3.2', now=at(31))
    mark(proj, nguoi='P1', anh='F_001.png', loai='MIRROR', note='Sửa lại: lật phải trái', now=at(40))          # sau gói đầu
    newer = pkg(proj, nguoi='P1', now=at(41))['path']
    p2 = os.path.join(proj['root'], 'tam', 'a2.zip')
    shutil.copy(newer, p2)
    rep = m.import_packages([(p2, 'a2.zip')], now=at(50))[0]
    assert (rep['moi'], rep['cap_nhat'], rep['trung']) == (0, 1, 1)
    c = m.cases[key]
    assert (c['loai'], c['ghi_chu']) == ('MIRROR', 'Sửa lại: lật phải trái')                                  # trường thành viên cập nhật
    assert (c['trang_thai'], c['quyet_dinh'], c['phu_trach'], c['loai_backlog'], c['ghi_backlog'], c['muc_guideline']) == (
        'dang_ban', 'Chốt hai điểm hàm', 'P2', 'Guideline mâu thuẫn', True, '3.2')                           # trường người tổ chức giữ nguyên
    # gói cũ hơn (nội dung các ca có sua_luc cũ hơn bản đang có, file khác nên sha256 khác): trùng, giữ bản đang có
    old = os.path.join(proj['root'], 'tam', 'cu.zip')
    zf_in = zipfile.ZipFile(pa)
    ents = [(n, zf_in.read(n)) for n in zf_in.namelist()]
    ents = [(n, good_manifest(so_ca=2, luot=['CKA'], tao_luc='2026-10-01T00:00:00+07:00') if n == 'manifest.json' else d) for n, d in ents]
    zip_with(old, ents)
    rep2 = m.import_packages([(old, 'cu.zip')])[0]
    assert (rep2['trang_thai'], rep2['moi'], rep2['cap_nhat'], rep2['trung']) == ('ok', 0, 0, 2)
    assert m.cases[key]['loai'] == 'MIRROR'                                                                   # bản cũ không đè bản mới


def test_mo_lai_phien_tu_hop_json(proj):
    pa, pb = make_packages(proj)
    m = meeting(proj)
    m.import_packages([(pa, 'a.zip'), (pb, 'b.zip')], now=at(30))
    m.set_fields('P3|CKA|F_003.png', 'da_chot', 'Dùng quy tắc A', 'P4', now=at(31))
    again = ck.Meeting.load(ck.serve_dir(proj['root']), m.name)
    assert again.data == m.data and again.cases['P3|CKA|F_003.png']['trang_thai'] == 'da_chot'
    assert again.import_packages([(pa, 'a.zip')])[0]['trang_thai'] == 'da_nhap'                               # sha256 còn nhớ sau khi mở lại


def test_set_fields_kiem_tra(proj):
    pa, _ = make_packages(proj)
    m = meeting(proj)
    m.import_packages([(pa, 'a.zip')])
    key = 'P1|CKA|F_001.png'
    with pytest.raises(ck.RunError):
        m.set_fields(key, trang_thai='la')
    with pytest.raises(ck.RunError):
        m.set_fields(key, loai_backlog='Khác')
    with pytest.raises(ck.RunError):
        m.set_fields(key, phu_trach='P 3; rm')
    with pytest.raises(ck.RunError):
        m.set_fields(key, muc_guideline='<b>')
    with pytest.raises(ck.RunError):
        m.set_fields('khong|co|ca', trang_thai='mo')
    assert m.set_fields(key, trang_thai='da_chot', quyet_dinh='')[0].startswith('Đã chốt nhưng chưa có quyết định')
    assert m.set_fields(key, muc_guideline='§4.1')[0:1] != [] and m.cases[key]['muc_guideline'] == '4.1'


def test_nhap_vao_thu_muc_phien_khong_ghi_ngoai(proj, tmp_path):
    pa, pb = make_packages(proj)
    m = meeting(proj)
    before = {os.path.join(d, f) for d, _s, fs in os.walk(proj['root']) for f in fs}
    m.import_packages([(pa, 'a.zip'), (pb, 'b.zip')])
    new = {os.path.join(d, f) for d, _s, fs in os.walk(proj['root']) for f in fs} - before
    assert new and all(os.path.commonpath([p, m.dir]) == m.dir for p in new)


# ---------- đánh số ----------
def test_next_number():
    assert ck.next_number('', 'P') == 1 and ck.next_number('', 'QĐ') == 1
    doc = '# Backlog\n\n## P-007\n\nx\n\n| Mã | Tóm tắt |\n|---|---|\n| P-009 | a |\n| [P-004](x) | b |\n'
    assert ck.next_number(doc, 'P') == 10
    fenced = '```markdown\n## P-NNN\n## P-123\n| P-500 |\n```\n\n## P-002\n'
    assert ck.next_number(fenced, 'P') == 3
    assert ck.next_number('```markdown\n## P-099\n', 'P') == 1                                                # khối chưa đóng cũng bị bỏ qua
    assert ck.next_number('## P-5\nxem P-77 ở trên\n', 'P') == 6                                               # nhắc tới trong văn bản không tính
    qd = '## QĐ-003\n\n| QĐ-010 | x |\n'
    assert ck.next_number(qd, 'QĐ') == 11
    assert ck.next_number(unicodedata.normalize('NFD', qd), 'QĐ') == 11
    assert ck.next_number('## P-004\n', 'QĐ') == 1                                                             # không lẫn tiền tố


def test_repo_that_dang_trong_va_tim_duoc():
    pb, qd = ck.find_repo_docs()
    assert pb and qd and os.path.basename(pb) == 'problem-backlog.md' and os.path.dirname(os.path.abspath(pb)) == REPO
    assert ck.next_number(ck.read_text(pb), 'P') >= 1 and ck.next_number(ck.read_text(qd), 'QĐ') >= 1
    assert ck.find_repo_docs('/')[0] is None


# ---------- biên bản ----------
TEMPLATE_RE = re.compile(r'```markdown\n(.*?)```', re.DOTALL)


def template_labels(path, head):
    text = open(path, encoding='utf-8').read()
    block = [b for b in TEMPLATE_RE.findall(text) if b.startswith(head)][0]
    return [m.group(1) for m in re.finditer(r'^- \*\*(.+?):\*\*', block, re.MULTILINE)], block


def sample_meeting(proj, backlog_nums=(7, 9)):
    pa, pb = make_packages(proj)
    m = meeting(proj)
    m.import_packages([(pa, 'a.zip'), (pb, 'b.zip')], now=at(30))
    return m


def minutes_of(m, backlog='', qd=''):
    return ck.build_minutes(m, backlog, qd, now=at(60))


def test_bien_ban_khop_mau_repo(proj):
    m = sample_meeting(proj)
    k_chot = 'P3|CKA|F_001.png'                                                     # RULE: vào backlog, đã chốt có quyết định
    m.set_fields(k_chot, 'da_chot', 'Kính râm: đặt điểm theo viền kính', 'P4', None, None, '5.1', now=at(31))
    m.set_fields('P1|CKA|F_002.png', 'dang_ban', now=at(32))                         # CONG_CU: pain point
    m.set_fields('P1|CKA|F_001.png', 'da_chot', 'Chỉ sửa trong CVAT', now=at(33))    # SWAP: không vào backlog, vẫn có QĐ
    res = minutes_of(m)
    md = res['md']
    pb_labels, pb_block = template_labels(os.path.join(REPO, 'problem-backlog.md'), '## P-NNN')
    qd_labels, qd_block = template_labels(os.path.join(REPO, 'so-quyet-dinh.md'), '## QĐ-NNN')
    fenced = TEMPLATE_RE.findall(md)
    p_blocks = [b for b in fenced if '## P-001' in b][0].split('\n\n## ')
    qd_blocks = [b for b in fenced if '## QĐ-001' in b][0].split('\n\n## ')
    assert len(p_blocks) == res['n_p'] == 3 and len(qd_blocks) == res['n_qd'] == 2
    for blk in p_blocks:
        labels = [x.strip() for x in re.findall(r'^- \*\*(.+?):\*\*', blk, re.MULTILINE)]
        want = ['Hướng đang cân nhắc' if 'Pain point' in blk and x == 'Các cách hiểu' else x for x in pb_labels]
        assert labels == want, blk                                                  # đủ nhãn, đúng thứ tự mẫu
    for blk in qd_blocks:
        assert re.findall(r'^- \*\*(.+?):\*\*', blk, re.MULTILINE) == qd_labels
    # từng dòng cấu trúc của mẫu P có mặt (trừ phần ghi chú trong ngoặc của mẫu)
    p1 = p_blocks[0] if p_blocks[0].startswith('## P-001') else '## ' + p_blocks[0]
    assert re.search(r'^## P-001\n\n\*\*.+\*\*\n\n- \*\*Loại:\*\* .+\n- \*\*Mục guideline:\*\* §.*\n- \*\*Người phát hiện:\*\* @P\d · \d\d/\d\d/\d{4}\n'
                     r'- \*\*Link CVAT:\*\* \(bỏ trống nếu không có\)\n  - Không có link CVAT; ảnh F_\d+\.png, lượt CKA, mã [A-Z_]+, điểm .+\n'
                     r'- \*\*Mô tả:\*\* .*\n- \*\*(Các cách hiểu|Hướng đang cân nhắc):\*\*\n  1\.\n  2\.\n- \*\*Xử lý tạm trong lúc chờ:\*\*\n'
                     r'- \*\*Kết quả:\*\* (🔴 Mở|🗣️ Đang bàn|✅ Đã chốt)', p1)
    assert '- **Người tham gia:** @P5 (chốt), @P1, @P3' in md and '- **Trạng thái:** Hiệu lực' in md
    assert '  - [ ] Áp dụng quyết định (@P4)' in md and '  - [ ] Áp dụng quyết định (@P5)' in md              # phụ trách, mặc định người tổ chức
    # mã: backlog theo thứ tự loại (RULE, GL_MO_HO, CONG_CU; SWAP không vào), QĐ theo thứ tự loại (SWAP, RULE)
    assert '| P-001 | Chưa có quy tắc cho kính | Guideline chưa nói tới | §5.1 | ✅ Đã chốt | QĐ-002 |' in md
    assert '| P-003 | Khó kéo điểm | Pain point công cụ | § | 🗣️ Đang bàn |  |' in md
    assert '| QĐ-001 | Chỉ sửa trong CVAT | 16/10/2026 | Họp ca khó 16/10 | Hiệu lực |' in md
    assert '| QĐ-002 | Kính râm: đặt điểm theo viền kính | 16/10/2026 | P-001 | Hiệu lực |' in md
    assert '- **Xuất phát từ:** [P-001](problem-backlog.md#p-001)' in md
    assert '- **Xuất phát từ:** Họp ca khó 16/10 (ca SWAP F_001.png của P1)' in md
    assert '- **Kết quả:** ✅ Đã chốt (QĐ-002)' in md and '- **Kết quả:** 🗣️ Đang bàn' in md and '- **Hướng đang cân nhắc:**' in md
    assert '"## Dán' not in md and md.count('## Dán vào problem-backlog.md') == 1 and md.count('## Dán vào so-quyet-dinh.md') == 1
    assert proj['root'] not in md and not re.search(r'!\[|(?<![\w/])/(tmp|home|Users)/|[A-Z]:\\\\', md)       # không ảnh, không đường dẫn tuyệt đối


def test_bien_ban_dem_so_tiep_tu_file_repo(proj):
    m = sample_meeting(proj)
    m.set_fields('P3|CKA|F_001.png', 'da_chot', 'X', now=at(31))
    backlog = '## P-007\n\n| P-009 | a |\n```\n## P-999\n```\n'
    qd = '| QĐ-004 | y |\n## QĐ-002\n'
    res = minutes_of(m, backlog, qd)
    assert (res['p_first'], res['qd_first']) == (10, 5)
    assert '| P-010 |' in res['md'] and '## P-010' in res['md'] and '| QĐ-005 |' in res['md'] and '## QĐ-005' in res['md'] and 'P-999' not in res['md']
    empty = minutes_of(m)
    assert (empty['p_first'], empty['qd_first']) == (1, 1) and '## P-001' in empty['md'] and '## QĐ-001' in empty['md']


def test_bien_ban_ca_chot_thieu_quyet_dinh_khong_tao_qd(proj):
    m = sample_meeting(proj)
    m.set_fields('P3|CKA|F_001.png', 'da_chot', now=at(31))
    res = minutes_of(m)
    assert res['n_qd'] == 0 and res['warnings'] and 'chưa có quyết định' in res['warnings'][0]
    assert '## Cần xem lại' in res['md'] and '- **Kết quả:** ✅ Đã chốt\n' in res['md'] and 'QĐ-001' not in res['md'].split('## Dán vào so-quyet-dinh.md')[1]


def test_bang_dung_so_cot_va_escape_ong(proj):
    m = sample_meeting(proj)
    m.cases['P3|CKA|F_003.png']['ghi_chu'] = 'A | B\nC'
    res = minutes_of(m)
    rows = [l for l in res['md'].splitlines() if l.startswith('| P-')]
    assert rows
    for l in rows:
        assert len(re.split(r'(?<!\\)\|', l.strip().strip('|'))) == 6, l
    assert '| A \\| B |' in res['md']                                                                          # ô bảng: | thành \\|
    assert '**A | B**' in res['md']                                                                          # tiêu đề đậm không phải ô bảng
    assert '- **Mô tả:** A | B C' in res['md']


def test_csv_tong_hop_chong_cong_thuc(proj):
    m = sample_meeting(proj)
    m.cases['P1|CKA|F_002.png']['ghi_chu'] = '=HYPERLINK("http://x","y")'
    m.cases['P3|CKA|F_003.png']['ghi_chu'] = '-1+1'
    m.cases['P3|CKA|F_001.png']['ghi_chu'] = '@SUM(A1)'
    res = minutes_of(m)
    rows = list(csv.DictReader(io.StringIO(res['csv'])))
    assert list(rows[0].keys()) == ck.TONG_HOP_COLS and len(rows) == 4
    notes = {r['anh'] + r['nguoi']: r['ghi_chu'] for r in rows}
    assert notes['F_002.pngP1'].startswith("'=") and notes['F_003.pngP3'] == "'-1+1" and notes['F_001.pngP3'] == "'@SUM(A1)"
    assert all(not r[c].startswith(('=', '+', '-', '@')) for r in rows for c in ck.TONG_HOP_COLS)
    assert {r['ma_p'] for r in rows} - {''} == {'P-001', 'P-002', 'P-003'} and [r['ma_p'] for r in rows if r['loai'] == 'SWAP'] == ['']


def test_write_minutes_khong_dung_repo_docs(proj, tmp_path):
    m = sample_meeting(proj)
    docs = tmp_path / 'docs'
    docs.mkdir()
    pb, qd = docs / 'problem-backlog.md', docs / 'so-quyet-dinh.md'
    shutil.copy(os.path.join(REPO, 'problem-backlog.md'), pb)
    shutil.copy(os.path.join(REPO, 'so-quyet-dinh.md'), qd)
    h = [hashlib.sha256(p.read_bytes()).hexdigest() for p in (pb, qd)]
    res = ck.write_minutes(m, str(pb), str(qd), now=at(60))
    assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in (pb, qd)] == h
    assert os.path.basename(res['md_path']) == 'bien_ban_1610.md' and os.path.basename(res['csv_path']) == 'tong_hop_1610.csv'
    assert os.path.dirname(res['md_path']) == m.dir and open(res['md_path'], encoding='utf-8').read() == res['md']
    assert open(res['csv_path'], 'rb').read().startswith(b'\xef\xbb\xbf')
    assert '## P-001' in res['md']


# ---------- HTML ----------
def test_html_thoat_ky_tu(proj):
    mark(proj, note='<script>alert(1)</script>', diem='mattrai_1')
    rows = ck.read_marks(proj['cka'])
    assert '<script>' not in ck.list_html(rows) and '&lt;script&gt;' in ck.list_html(rows)
    pa = pkg(proj)['path']
    m = meeting(proj)
    m.import_packages([(pa, 'a"><img src=x onerror=1>.zip')])
    key = next(iter(m.cases))
    serve = ck.serve_dir(proj['root'])
    for h in (ck.grid_html(m, [key], serve, key), ck.stage_html(m, key, serve), ck.counts_html(m), ck.report_html(
            [dict(ten='<b>x</b>', nguoi='<i>', trang_thai='loi', moi=0, cap_nhat=0, trung=0, ly_do='<script>')])):
        assert '<script' not in h and 'onerror=1>' not in h and '<b>x' not in h
    m.cases['P1|a"b|F_001.png'] = m.cases.pop(key)
    key = 'P1|a"b|F_001.png'
    g = ck.grid_html(m, [key], serve, key)
    assert 'data-key="P1|a&quot;b|F_001.png"' in g
    assert 'src="/gradio_api/file=' in g and ck.file_url('/a b/c ñ.jpg') == '/gradio_api/file=/a%20b/c%20%C3%B1.jpg'


def test_nhom_theo(proj):
    m = sample_meeting(proj)
    serve = ck.serve_dir(proj['root'])
    keys = m.filtered()
    by_loai = ck.grid_html(m, keys, serve, '', 'loai')
    by_nguoi = ck.grid_html(m, keys, serve, '', 'nguoi')
    by_tt = ck.grid_html(m, keys, serve, '', 'trang_thai')
    assert by_loai.count('<section') == 4 and by_nguoi.count('<section') == 2 and by_tt.count('<section') == 1
    assert by_loai.count('<button') == 4 and 'SWAP — Đổi chỗ hai điểm' in by_loai and '>Mở <' in by_tt
    assert 'Không có ca nào khớp' in ck.grid_html(m, [], serve) and 'Chọn hoặc tạo một phiên' in ck.grid_html(None, [], serve)


def test_thumb_nho_cho_danh_sach(proj, tmp_path):
    out = str(tmp_path / 'tmp')
    p = ck.small_thumb(proj['cka'], 'F_001.png', out)
    assert p and os.path.isfile(p) and max(Image.open(p).size) <= 112
    assert ck.small_thumb(proj['cka'], 'F_404.png', out) is None


# ---------- nối vào trang rà soát ----------
def test_phim_K_va_nut_trong_review_app():
    assert "k: 'btn-cakho'" in ra.PAGE_JS and "KeyK: 'btn-cakho'" in ra.PAGE_JS
    assert '<kbd>K</kbd> Ca khó' in ra.KEYS_HTML
    assert ra.CSS.count('#btn-cakho') >= 1 and 'body.ck-present' in ra.CSS
    # cổng chặn phím cũ vẫn còn
    for needle in ("mainEl.offsetParent === null", 'e.repeat || e.ctrlKey || e.altKey || e.metaKey || typing(e.target)'):
        assert needle in ra.PAGE_JS


def test_ca_kho_khong_import_gradio_hay_review_app():
    src = open(os.path.join(TOOL, 'ca_kho.py'), encoding='utf-8').read()
    head = src.split('\n# ---------- hằng số')[0]
    assert not re.search(r'^\s*(import|from)\s+(gradio|torch|review_app|PIL|mediapipe|cv2)\b', head, re.MULTILINE)
    assert 'extractall(' not in src and '.extract(' not in src
    assert 'requests' not in src and 'urllib.request' not in src and 'socket' not in src


def test_serve_dir_chi_outputs_ca_kho(tmp_path):
    p = ck.serve_dir(str(tmp_path))
    assert p == os.path.join(str(tmp_path), 'outputs', 'ca_kho') and os.path.isdir(p)
