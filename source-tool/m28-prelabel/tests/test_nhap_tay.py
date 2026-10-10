"""Thử m28core/nhap_tay.py (mục "Nhập tay" của tab Thống kê, QĐ-006): nhóm trưởng nhập thời gian + file nhãn CVAT cho người nhóm manual gán thẳng trong CVAT; bản nhập tay là gói
kết quả bình thường trong outputs/goi_nhom, thong_ke.tinh và tool/tong_ket.py tính như gói của đồng hồ. Dữ liệu giả (nhãn quanh mẫu tmpl của config), không ảnh, không mạng."""
import datetime
import json
import os
import shutil
import sys
import zipfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
sys.path.insert(0, HERE)
import thong_ke as tk  # noqa: E402
import thong_ke_html as th  # noqa: E402
import tong_ket  # noqa: E402
from dh_fake import VN, cfg_real, du_an, mat_mau, viet_nhap, viet_xml  # noqa: E402
from m28core import cvat_io, goi_kq, nhap_tay as nt  # noqa: E402
from tk_fake import ANH, nd_goi, nhieu, viet_goi  # noqa: E402

CFG = cfg_real()
NOW = datetime.datetime(2026, 10, 14, 20, 5, 0, tzinfo=VN)
GOI_NHOM = os.path.join('outputs', 'goi_nhom')


def mats(anh=ANH, sigma=0.4, seed=0):
    """Nhãn giả của các ảnh (tên có đuôi .png), cùng cách đánh số với tk_fake (ảnh thứ i quanh mat_mau(i + 1))."""
    return {f'{a}.png': nhieu(mat_mau(i + 1), sigma, 100 * seed + i) for i, a in enumerate(anh)}


def xml_file(tmp_path, name, m, **kw):
    return viet_xml(os.path.join(str(tmp_path), 'tai_len', name), m, **kw)


def zip_file(tmp_path, name, entries):
    p = os.path.join(str(tmp_path), 'tai_len', name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with zipfile.ZipFile(p, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, data in entries.items():
            z.writestr(n, data)
    return p


def nd_tay(root, files, nguoi='P1', nhom='manual', dot='NAP_001', giay='5:20', ngay='14/10/2026', now=NOW, **kw):
    return nt.tao_noi_dung(root, CFG, nguoi, nhom, dot, giay, files, ngay=ngay, now=now, **kw)


def goi_files(root, thu_muc=GOI_NHOM):
    d = os.path.join(root, thu_muc)
    return sorted(f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))) if os.path.isdir(d) else []


# ---------- thời gian, ngày ----------
@pytest.mark.parametrize('text,giay', [('1:25:30', 5130), ('85:30', 5130), ('85', 5100), ('85,5', 5130), ('85.5', 5130), ('85 phút', 5100), ('85p', 5100), (' 85 PHÚT ', 5100),
                                       ('85 phut', 5100), ('85min', 5100), ('0:00:30', 30), ('2:05', 125), ('1440', 86400), ('24:00:00', 86400)])
def test_doc_thoi_gian_hms_mmss_va_so_tron_la_phut(text, giay):
    assert nt.doc_thoi_gian(text) == pytest.approx(giay)


@pytest.mark.parametrize('text,match', [('', 'Chưa nhập'), (None, 'Chưa nhập'), ('0', 'lớn hơn 0'), ('0:00', 'lớn hơn 0'), ('-5', 'Không đọc được'), ('abc', 'Không đọc được'),
                                        ('1:75:00', 'nhỏ hơn 60'), ('85:61', 'nhỏ hơn 60'), ('25:00:00', '24 giờ'), ('1441', '24 giờ'), ('5100 giây', 'Không đọc được')])
def test_doc_thoi_gian_sai_bao_ro(text, match):
    with pytest.raises(nt.NhapTayLoi, match=match):
        nt.doc_thoi_gian(text)


def test_doc_ngay_trong_la_hom_nay_va_ba_dang():
    d = datetime.date
    assert nt.doc_ngay('', NOW) == d(2026, 10, 14) and nt.doc_ngay(None, NOW) == d(2026, 10, 14)
    assert nt.doc_ngay('13/10/2026', NOW) == d(2026, 10, 13) and nt.doc_ngay('3/10/2026', NOW) == d(2026, 10, 3)
    assert nt.doc_ngay('13/10', NOW) == d(2026, 10, 13) and nt.doc_ngay('2026-10-12', NOW) == d(2026, 10, 12) and nt.doc_ngay('14/10/2026', NOW) == d(2026, 10, 14)
    for bad, match in (('31/02/2026', 'không có thật'), ('15/10/2026', 'tương lai'), ('2026-11-01', 'tương lai'), ('hôm qua', 'Không đọc được'), ('14/10/26', 'Không đọc được')):
        with pytest.raises(nt.NhapTayLoi, match=match):
            nt.doc_ngay(bad, NOW)


# ---------- file nhãn ----------
def test_doc_xml_va_zip_cho_cung_nhan(tmp_path):
    m = mats(ANH[:3])
    px = xml_file(tmp_path, 'annotations.xml', m)
    lab, info = nt.doc_file_nhan([px], CFG)
    assert sorted(lab) == ['F_001', 'F_002', 'F_003'] and len(lab['F_001']) == 50
    assert info['file'] == ['annotations.xml'] and info['theo_file'] == [('annotations.xml', 3, 3)] and info['n_anh'] == 3 and len(info['sha256'][0]) == 64
    data = open(px, 'rb').read()
    pz = zip_file(tmp_path, 'job_12_annotations_cvat for images 1.1.zip', {'annotations.xml': data})
    lab2, info2 = nt.doc_file_nhan([pz], CFG)
    assert lab2 == lab and info2['sha256'] == info['sha256'] and info2['file'] == ['job_12_annotations_cvat for images 1.1.zip']


def test_zip_kem_anh_thieu_annotations_ten_la_va_zip_hong_bi_tu_choi(tmp_path):
    data = open(xml_file(tmp_path, 'a.xml', mats(ANH[:1])), 'rb').read()
    cases = [({'annotations.xml': data, 'images/F_001.png': b'x'}, 'kèm ảnh'), ({'labels.xml': data}, 'không có annotations.xml'),
             ({'annotations.xml': data, '../evil.txt': b'x'}, 'đường dẫn lạ'), ({'sub/annotations.xml': data}, 'không có annotations.xml')]
    for i, (entries, match) in enumerate(cases):
        with pytest.raises(nt.NhapTayLoi, match=match):
            nt.doc_file_nhan([zip_file(tmp_path, f'z{i}.zip', entries)], CFG)
    bad = os.path.join(str(tmp_path), 'tai_len', 'hong.zip')
    open(bad, 'wb').write(b'PK\x03\x04 hong')
    with pytest.raises(nt.NhapTayLoi, match='zip hợp lệ'):
        nt.doc_file_nhan([bad], CFG)
    txt = os.path.join(str(tmp_path), 'tai_len', 'nhan.txt')
    open(txt, 'wb').write(data)
    with pytest.raises(nt.NhapTayLoi, match='chỉ nhận file .xml hoặc .zip'):
        nt.doc_file_nhan([txt], CFG)
    with pytest.raises(nt.NhapTayLoi, match='Chưa chọn file nhãn'):
        nt.doc_file_nhan([], CFG)


def test_nhieu_file_theo_job_gop_theo_ten_anh_va_trung_ten_bao_ca_hai_file(tmp_path):
    a = xml_file(tmp_path, 'job_1.xml', mats(ANH[:4]))
    b = xml_file(tmp_path, 'job_2.xml', mats(ANH[4:]))
    lab, info = nt.doc_file_nhan([a, b], CFG)
    assert sorted(lab) == ANH and info['file'] == ['job_1.xml', 'job_2.xml'] and info['n_anh'] == 8
    c = xml_file(tmp_path, 'job_3.xml', mats(ANH[3:5], seed=9))                                   # F_004 đã có ở job_1
    with pytest.raises(nt.NhapTayLoi, match=r'Ảnh F_004 có trong cả job_1\.xml và job_3\.xml'):
        nt.doc_file_nhan([a, c], CFG)
    with pytest.raises(nt.NhapTayLoi, match='chọn hai lần'):
        nt.doc_file_nhan([a, a], CFG)
    d1 = xml_file(tmp_path / 'x1', 'annotations.xml', mats(ANH[:2]))                               # hai file cùng tên (mỗi job một annotations.xml): tên hiển thị kèm số thứ tự
    d2 = xml_file(tmp_path / 'x2', 'annotations.xml', mats(ANH[1:3], seed=3))
    with pytest.raises(nt.NhapTayLoi, match=r'annotations\.xml \(file thứ 1\) và annotations\.xml \(file thứ 2\)'):
        nt.doc_file_nhan([d1, d2], CFG)


def test_ban_video_khong_skeleton_nhan_cu_va_xml_hong_thanh_loi_ro_khong_systemexit(tmp_path):
    d = os.path.join(str(tmp_path), 'tai_len')
    os.makedirs(d)

    def f(name, text):
        p = os.path.join(d, name)
        open(p, 'w', encoding='utf-8').write(text)
        return p
    video = f('video.xml', '<annotations><version>1.1</version><meta><task><owner><email>chu.task@example.com</email></owner></task></meta>'
                           '<track id="0" label="mattrai" source="manual"><skeleton frame="0" keyframe="1"/></track></annotations>')
    box = f('box.xml', '<annotations><version>1.1</version><meta><owner><email>chu.task@example.com</email></owner></meta>'
                       '<image id="0" name="F_001.png" width="512" height="512"><box label="mat" xtl="1" ytl="1" xbr="9" ybr="9"/></image></annotations>')
    cu = f('cu.xml', '<annotations><version>1.1</version><image id="0" name="a.png" width="1" height="1"><skeleton label="face50"/></image></annotations>')
    hong = f('hong.xml', '<annotations><image name="F_001.png"')
    rong = f('rong.xml', '<annotations><version>1.1</version></annotations>')
    for p, match in ((video, 'CVAT for video'), (box, 'không có skeleton nào của bảy nhóm'), (cu, 'face50 CŨ'), (hong, 'không phải XML hợp lệ'), (rong, 'không có ảnh nào')):
        try:
            nt.doc_file_nhan([p], CFG)
        except nt.NhapTayLoi as e:
            msg = str(e)
        except BaseException as e:                                                                     # SystemExit của bộ đọc không được lọt ra
            pytest.fail(f'{os.path.basename(p)}: {type(e).__name__}')
        else:
            pytest.fail(f'{os.path.basename(p)} không bị từ chối')
        assert match in msg, (p, msg)
        assert '@' not in msg and d not in msg and str(tmp_path) not in msg                            # không lộ <meta> (email) hay đường dẫn tuyệt đối


def test_nhan_co_meta_email_khong_vao_goi(tmp_path):
    root = du_an(tmp_path / 'p')
    p = xml_file(tmp_path, 'nhan.xml', mats(ANH[:2]))
    text = open(p, encoding='utf-8').read().replace('<version>1.1</version>', '<version>1.1</version><meta><task><owner><username>kien</username>'
                                                                              '<email>chu.task@example.com</email></owner></task></meta>')
    open(p, 'w', encoding='utf-8').write(text)
    nd = nd_tay(root, [p])
    assert 'example.com' not in json.dumps(nd) and goi_kq.kiem_rieng_tu(nd) == [] and nd['so_mat'] == 2


# ---------- dựng gói ----------
def test_noi_dung_qua_kiem_cau_truc_rieng_tu_va_doc_bytes(tmp_path):
    root = du_an(tmp_path / 'p')
    files = [xml_file(tmp_path, 'job_1.xml', mats(ANH[:5])), xml_file(tmp_path, 'job_2.xml', mats(ANH[5:]))]
    notes = []
    nd = nd_tay(root, files, ghi_chu='  P1 làm ở phòng lab, máy 2 \x07 ', thong_bao=notes)
    names = {p['name'] for p in CFG['points']}
    assert goi_kq.kiem_cau_truc(nd, names) == [] and goi_kq.kiem_rieng_tu(nd) == []
    assert goi_kq.PHIEN_RE.fullmatch(nd['phien']) and nd['phien'].startswith('P1-tay-NAP_001-') and len(nd['phien'].rsplit('-', 1)[1]) == 8
    assert (nd['nguoi'], nd['nhom'], nd['dot'], nd['bo_anh'], nd['so_mat'], nd['giay_phien']) == ('P1', 'manual', 'NAP_001', 'NAP_001', 8, 320.0)
    assert (nd['giay_tam_dung'], nd['so_lan_tam_dung'], nd['uoc_luong_chia_deu'], nd['mat_do'], nd['canh_bao'], nd['sua_tay']) == (0.0, 0, True, [], [], 0)
    assert nd['bat_dau'] == nd['ket_thuc'] == '2026-10-14T20:05:00+07:00' and nd['tao_luc'] == '2026-10-14T20:05:00+07:00'
    assert nd['nguon_nhap'] == 'nhap_tay' and nd['co_nhan'] is True and nd['co_nhap'] is False and nd['nhan_file'] == 'job_1.xml; job_2.xml'
    assert nd['cau_hinh'] == dict(so_diem=50, nguong_sua=goi_kq.NGUONG_SUA_MAC_DINH) and nd['ghi_chu'] == 'P1 làm ở phòng lab, máy 2'
    assert [r['anh'] for r in nd['ket_qua']] == ANH and all('nhap' not in r and len(r['nhan_cuoi']) == 50 for r in nd['ket_qua'])
    assert any('job_1.xml: 5 ảnh có nhãn' in n for n in notes)
    back, _w = goi_kq.doc_bytes(goi_kq.canonical(goi_kq.dong_goi(nd)), 'x.json', names)
    assert back == nd
    r = nt.them(root, nd)
    assert r['ten'] == 'ketqua_P1_1410_NAP_001' and r['zip'] == os.path.join(GOI_NHOM, 'ketqua_P1_1410_NAP_001.zip')
    a, _w = goi_kq.doc_goi(os.path.join(root, r['zip']), names)
    assert a == nd
    rows = tk.hang_thoi_gian_goi(a, r['ten'])
    assert len(rows) == 8 and all(x['seconds'] == pytest.approx(40.0) and x['uoc_luong'] and x['condition'] == 'manual' and x['date'] == '2026-10-14' for x in rows)


def test_ngay_lam_khac_hom_nay_va_bo_anh_tu_config(tmp_path):
    root = du_an(tmp_path / 'p')
    json.dump({'nhom': {}, 'bo_anh': 'BO_CHUNG'}, open(os.path.join(root, 'config', 'nhom_thi_nghiem.json'), 'w'))
    nd = nd_tay(root, [xml_file(tmp_path, 'a.xml', mats(ANH[:2]))], ngay='12/10/2026', giay=12.0 * 60)
    assert nd['bat_dau'].startswith('2026-10-12T20:05:00') and nd['bo_anh'] == 'BO_CHUNG' and nd['giay_phien'] == 720.0
    assert nt.them(root, nd)['ten'] == 'ketqua_P1_1210_NAP_001'                                       # DDMM trong tên gói = ngày làm
    nd2 = nd_tay(root, [xml_file(tmp_path, 'b.xml', mats(ANH[:2]))], dot='NAP_002', bo_anh='KHAC')
    assert nd2['bo_anh'] == 'KHAC'


@pytest.mark.parametrize('kw,match', [(dict(nguoi=None), 'Chưa chọn người'), (dict(nguoi='P9'), 'Chưa chọn người'), (dict(nhom='ca_hai'), 'manual hoặc assisted'),
                                      (dict(dot=''), 'Chưa nhập đợt'), (dict(dot='../runs'), 'không hợp lệ'), (dict(dot='đợt 1'), 'không hợp lệ'),
                                      (dict(giay='abc'), 'Không đọc được thời gian'), (dict(giay=0), 'lớn hơn 0'), (dict(giay=float('nan')), 'lớn hơn 0'),
                                      (dict(ngay='20/10/2026'), 'tương lai'), (dict(task='a/b'), 'task'), (dict(ghi_chu='x' * 201), 'tối đa 200')])
def test_dau_vao_sai_bao_ro_khong_ghi_gi(tmp_path, kw, match):
    root = du_an(tmp_path / 'p')
    with pytest.raises(nt.NhapTayLoi, match=match):
        nd_tay(root, [xml_file(tmp_path, 'a.xml', mats(ANH[:2]))], **kw)
    assert goi_files(root) == []


def test_rieng_tu_ghi_chu_co_email_hay_duong_dan_va_ten_file_co_email_bi_tu_choi(tmp_path):
    root = du_an(tmp_path / 'p')
    f = xml_file(tmp_path, 'a.xml', mats(ANH[:2]))
    for note in ('gửi lại cho kien.nguyen@example.com', 'file ở C:\\Users\\kien\\Desktop\\nhan.xml', 'xem /home/kien/raw'):
        with pytest.raises(nt.NhapTayLoi, match='Ghi chú bị chặn') as e:
            nd_tay(root, [f], ghi_chu=note)
        assert 'example.com' not in str(e.value) and 'kien' not in str(e.value)
    g = xml_file(tmp_path, 'kien.nguyen@example.com.xml', mats(ANH[:2]))
    with pytest.raises(nt.NhapTayLoi, match='có địa chỉ email'):
        nd_tay(root, [g])
    assert goi_files(root) == []


def test_assisted_kem_nhap_cua_dot_neu_may_co_runs(tmp_path):
    root = du_an(tmp_path / 'p')
    anh = {f'{a}.png': mat_mau(i + 1) for i, a in enumerate(ANH[:3])}
    viet_nhap(root, 'NAP_001', anh)
    sua = {k: {n: (x + (8.0 if n == 'songmui_1' else 0.0), y) for n, (x, y) in v.items()} for k, v in anh.items()}
    notes = []
    nd = nd_tay(root, [xml_file(tmp_path, 'a.xml', sua)], nguoi='P3', nhom='assisted', thong_bao=notes)
    assert nd['co_nhap'] is True and all(r['diem_da_sua'] == ['songmui_1'] and len(r['nhap']) == 50 and r['nme_nhap_so_nhan_cuoi'] > 0 for r in nd['ket_qua'])
    assert any('Có nháp của đợt NAP_001 cho 3/3 mặt' in n for n in notes) and goi_kq.kiem_cau_truc(nd) == []
    notes = []
    nd2 = nd_tay(root, [xml_file(tmp_path, 'b.xml', sua)], nguoi='P3', nhom='assisted', dot='KHONG_CO', thong_bao=notes)
    assert nd2['co_nhap'] is False and all('nhap' not in r for r in nd2['ket_qua']) and nd2['canh_bao'] == []
    assert any('không có nháp' in n and 'TÊN LƯỢT' in n and 'máy này có nháp ở: NAP_001.' in n for n in notes)       # gợi ý lượt có nháp trên máy này
    os.makedirs(os.path.join(root, 'runs', 'HONG', 'xml'))
    open(os.path.join(root, 'runs', 'HONG', 'xml', 'prelabel.xml'), 'w').write('<annotations><image')       # nháp hỏng: vẫn nhận nhãn + thời gian, không SystemExit
    notes = []
    nd3 = nd_tay(root, [xml_file(tmp_path, 'c.xml', sua)], nguoi='P3', nhom='assisted', dot='HONG', thong_bao=notes)
    assert nd3['co_nhap'] is False and any('không đọc được' in n for n in notes)


def test_giay_moi_mat_la_thi_nhac_kiem_lai(tmp_path):
    root = du_an(tmp_path / 'p')
    notes = []
    nd_tay(root, [xml_file(tmp_path, 'a.xml', mats(ANH[:8]))], giay=40.0, thong_bao=notes)              # 40 giây cho 8 mặt: nghi gõ giây thay vì phút
    assert any('Giây/mặt = 5,0' in n and 'PHÚT' in n for n in notes)


# ---------- ghi: tất định, không nhân đôi, từ chối khi trùng người + đợt ----------
def test_phien_tat_dinh_bam_hai_lan_khong_nhan_doi(tmp_path):
    root = du_an(tmp_path / 'p')
    f = xml_file(tmp_path, 'a.xml', mats())
    nd1 = nd_tay(root, [f])
    nd2 = nd_tay(root, [f], now=NOW + datetime.timedelta(minutes=3), ghi_chu='lần hai')
    assert nd1['phien'] == nd2['phien'] and nd1['tao_luc'] != nd2['tao_luc']
    r1, r2 = nt.them(root, nd1), nt.them(root, nd2)
    assert r1 == r2 and goi_files(root) == ['ketqua_P1_1410_NAP_001.json', 'ketqua_P1_1410_NAP_001.zip']
    assert goi_kq.doc_goi(os.path.join(root, r2['zip']))[0]['ghi_chu'] == 'lần hai'                    # cùng phiên: ghi lại đúng gói đó
    q = goi_kq.quet([os.path.join(root, GOI_NHOM)])
    assert len(q['tot']) == 1
    zf = zip_file(tmp_path, 'a.zip', {'annotations.xml': open(f, 'rb').read()})                          # cùng nội dung nhãn, gói lại bằng zip: vẫn cùng phiên
    assert nd_tay(root, [zf])['phien'] == nd1['phien']
    assert nd_tay(root, [f], giay='5:21')['phien'] != nd1['phien'] and nd_tay(root, [f], nhom='assisted')['phien'] != nd1['phien']
    assert nd_tay(root, [f], nguoi='P2')['phien'] != nd1['phien']


def test_doi_ngay_lam_cung_phien_ban_cu_chuyen_vao_da_bo(tmp_path):
    root = du_an(tmp_path / 'p')
    f = xml_file(tmp_path, 'a.xml', mats())
    nt.them(root, nd_tay(root, [f], ngay='13/10/2026'))
    r = nt.them(root, nd_tay(root, [f], ngay='14/10/2026'))
    assert r['ten'] == 'ketqua_P1_1410_NAP_001' and goi_files(root) == ['ketqua_P1_1410_NAP_001.json', 'ketqua_P1_1410_NAP_001.zip']
    assert sorted(os.listdir(os.path.join(root, GOI_NHOM, '_da_bo'))) == ['ketqua_P1_1310_NAP_001.json', 'ketqua_P1_1310_NAP_001.zip']
    assert [x['ten'] for x in nt.liet_ke(root)] == ['ketqua_P1_1410_NAP_001']


def test_tu_choi_khi_da_co_goi_cung_nguoi_cung_dot_phien_khac(tmp_path):
    root = du_an(tmp_path / 'p')
    f = xml_file(tmp_path, 'a.xml', mats())
    viet_goi(root, nd_goi('P1', 'manual', 40.0))                                                          # gói của đồng hồ trong outputs/ket_qua
    with pytest.raises(nt.NhapTayLoi, match=r'Đã có gói ketqua_P1_1410_NAP_001\.zip của P1 cho đợt NAP_001 \(gói của đồng hồ\).*tính hai lần') as e:
        nt.them(root, nd_tay(root, [f]))
    assert 'outputs\\ket_qua' in str(e.value) and goi_files(root) == []
    g = xml_file(tmp_path, 'b.xml', mats(['F_101', 'F_102']))                                             # đợt khác với ảnh khác (người khác: được)
    assert nt.them(root, nd_tay(root, [g], dot='NAP_002'))['ten'] == 'ketqua_P1_1410_NAP_002'
    assert nt.them(root, nd_tay(root, [f], nguoi='P2'))['ten'] == 'ketqua_P2_1410_NAP_001'
    with pytest.raises(nt.NhapTayLoi, match=r'bản nhập tay khác.*Remove entry'):                         # bản nhập tay cũ của P2, giờ gõ khác: phải gỡ trước
        nt.them(root, nd_tay(root, [f], nguoi='P2', giay='6:00'))
    ngoai = tmp_path / 'tai_len_goi'                                                                      # gói đang tải lên ở tab (chưa lưu vào dự án) cũng tính
    ngoai.mkdir()
    other = du_an(tmp_path / 'khac')
    shutil.copy(os.path.join(other, viet_goi(other, nd_goi('P4', 'manual', 30.0, n_nguoi_seed=3))['zip']), ngoai)
    with pytest.raises(nt.NhapTayLoi, match='ketqua_P4_1410_NAP_001.zip'):
        nt.them(root, nd_tay(root, [f], nguoi='P4'), nguon_them=[str(ngoai / 'ketqua_P4_1410_NAP_001.zip')])
    assert nt.them(root, nd_tay(root, [f], nguoi='P4'))['ten'] == 'ketqua_P4_1410_NAP_001'
    with pytest.raises(nt.NhapTayLoi, match='Chỉ thêm được bản nhập tay'):
        nt.them(root, nd_goi('P5', 'manual', 40.0))


def test_tu_choi_khi_trung_ten_anh_voi_goi_cung_nguoi_du_khac_dot(tmp_path):
    """C10: config bo_anh = bo200_v1 (ô Đợt mặc định), nháp ở runs/bo200. Nhập P3 assisted với đợt mặc định (không có nháp) rồi nhập lại với đợt bo200: trước đây được nhận
    (so đúng chuỗi đợt) nên giờ của P3 bị tính hai lần và mặt lấy từ gói không nháp. Một người không gán một ảnh hai lần: trùng tên ảnh với gói khác của cùng người thì từ chối."""
    root = du_an(tmp_path / 'p')
    json.dump({'nhom': {}, 'bo_anh': 'bo200_v1'}, open(os.path.join(root, 'config', 'nhom_thi_nghiem.json'), 'w'))
    anh = {f'{a}.png': mat_mau(i + 1) for i, a in enumerate(ANH)}
    viet_nhap(root, 'bo200', anh)
    f = xml_file(tmp_path, 'p3.xml', anh)
    notes = []
    nd1 = nd_tay(root, [f], nguoi='P3', nhom='assisted', dot='bo200_v1', thong_bao=notes)
    assert nd1['co_nhap'] is False and nd1['dot'] == 'bo200_v1' and nd1['bo_anh'] == 'bo200_v1'
    canh = [n for n in notes if 'không có nháp' in n]
    assert len(canh) == 1 and 'TÊN LƯỢT' in canh[0] and 'không vào NME của nháp và tỉ lệ điểm phải sửa' in canh[0] and 'máy này có nháp ở: bo200' in canh[0]
    assert 'Remove entry' in canh[0] and not any('Bộ ảnh ghi trong gói' in n for n in notes)              # đợt = bo_anh của config: không cần nhắc
    assert nt.them(root, nd1)['ten'] == 'ketqua_P3_1410_bo200_v1'                                          # vẫn ghi gói (nhãn cuối + thời gian)
    notes = []
    nd2 = nd_tay(root, [f], nguoi='P3', nhom='assisted', dot='bo200', thong_bao=notes)
    assert nd2['co_nhap'] is True and nd2['dot'] == 'bo200' and nd2['bo_anh'] == 'bo200_v1' and nd2['phien'] != nd1['phien']
    assert any('Bộ ảnh ghi trong gói: bo200_v1' in n and 'bo200.' in n for n in notes)                    # bo_anh lấy từ config: nói rõ, không lặng lẽ
    with pytest.raises(nt.NhapTayLoi, match=r'Đã có gói ketqua_P3_1410_bo200_v1\.zip của P3 \(đợt bo200_v1, bản nhập tay khác\) trùng 8 ảnh.*'
                                            r'tính hai lần.*Remove entry ở danh sách bản nhập tay') as e:
        nt.them(root, nd2)
    assert 'F_001, F_002, F_003' in str(e.value) and 'Không ghi gì' in str(e.value)
    assert [x['ten'] for x in nt.liet_ke(root)] == ['ketqua_P3_1410_bo200_v1']
    nt.bo(root, 'ketqua_P3_1410_bo200_v1')                                                               # gỡ bản sai rồi thêm lại với đúng tên lượt: được, có nháp
    assert nt.them(root, nd2)['ten'] == 'ketqua_P3_1410_bo200'
    st = tk.tinh(root)
    assert st['sua']['trong'] is None and st['sua']['n_mat'] == 8 and st['meta']['n_mat_trung'] == 0
    p = xml_file(tmp_path, 'mot_anh.xml', {'F_008.png': anh['F_008.png'], 'F_101.png': mat_mau(20)})       # trùng chỉ một ảnh, đợt khác, nhóm manual: vẫn từ chối
    with pytest.raises(nt.NhapTayLoi, match=r'ketqua_P3_1410_bo200\.zip của P3 \(đợt bo200, bản nhập tay khác\) trùng 1 ảnh với bản này \(ví dụ F_008\)'):
        nt.them(root, nd_tay(root, [p], nguoi='P3', dot='NAP_009'))
    assert nt.them(root, nd_tay(root, [p], nguoi='P1', dot='NAP_009'))['ten'] == 'ketqua_P1_1410_NAP_009'      # người khác cùng ảnh: được


def test_trung_ten_anh_voi_goi_dong_ho_hay_goi_dang_tai_len_cua_cung_nguoi_khac_dot(tmp_path):
    root = du_an(tmp_path / 'p')
    f = xml_file(tmp_path, 'a.xml', mats(ANH[2:5]))
    viet_goi(root, nd_goi('P2', 'manual', 40.0, dot='NAP_001'))                                           # gói đồng hồ của P2 (8 ảnh) trong outputs/ket_qua
    with pytest.raises(nt.NhapTayLoi, match=r'ketqua_P2_1410_NAP_001\.zip của P2 \(đợt NAP_001, gói của đồng hồ\) trùng 3 ảnh') as e:
        nt.them(root, nd_tay(root, [f], nguoi='P2', dot='NAP_005'))
    assert 'outputs\\ket_qua' in str(e.value) and goi_files(root) == []
    ngoai = tmp_path / 'tai_len_goi'
    ngoai.mkdir()
    other = du_an(tmp_path / 'khac')
    shutil.copy(os.path.join(other, viet_goi(other, nd_goi('P4', 'manual', 30.0, dot='NAP_003', bo_anh='NAP_003'))['zip']), ngoai)
    with pytest.raises(nt.NhapTayLoi, match=r'ketqua_P4_1410_NAP_003\.zip.*trùng 3 ảnh.*bỏ nó khỏi ô tải lên'):
        nt.them(root, nd_tay(root, [f], nguoi='P4', dot='NAP_005'), nguon_them=[str(ngoai / 'ketqua_P4_1410_NAP_003.zip')])
    assert nt.them(root, nd_tay(root, [f], nguoi='P4', dot='NAP_005'))['ten'] == 'ketqua_P4_1410_NAP_005'       # không còn gói tải lên đó: được
    nd = nd_tay(root, [f], nguoi='P4', dot='NAP_005', now=NOW + datetime.timedelta(minutes=2))               # bấm lại (cùng phiên): ghi lại, không bị coi là trùng ảnh
    assert nt.them(root, nd)['ten'] == 'ketqua_P4_1410_NAP_005'


def test_liet_ke_va_go_mem_vao_da_bo(tmp_path):
    root = du_an(tmp_path / 'p')
    f = xml_file(tmp_path, 'a.xml', mats())
    assert nt.liet_ke(root) == []
    nt.them(root, nd_tay(root, [f], nguoi='P2', giay='7:20'))
    nt.them(root, nd_tay(root, [f], nguoi='P1'))
    viet_goi(root, nd_goi('P3', 'assisted', 28.0, n_nguoi_seed=2), GOI_NHOM)                             # gói đồng hồ trong cùng thư mục: không phải bản nhập tay
    ds = nt.liet_ke(root)
    assert [(x['ten'], x['nguoi'], x['nhom'], x['dot'], x['giay'], x['so_mat'], x['ngay']) for x in ds] == [
        ('ketqua_P1_1410_NAP_001', 'P1', 'manual', 'NAP_001', 320.0, 8, '14/10/2026'), ('ketqua_P2_1410_NAP_001', 'P2', 'manual', 'NAP_001', 440.0, 8, '14/10/2026')]
    assert all(x['tao_luc'] == '2026-10-14T20:05:00+07:00' for x in ds)
    for bad in ('ketqua_P3_1410_NAP_001', '../ketqua_P1_1410_NAP_001', 'ketqua_P1_1410_NAP_001.zip', '', None):
        with pytest.raises(nt.NhapTayLoi, match='Chọn một bản nhập tay'):
            nt.bo(root, bad)
    r = nt.bo(root, 'ketqua_P1_1410_NAP_001')
    assert r['ten'] == 'ketqua_P1_1410_NAP_001' and sorted(r['da_bo']) == [os.path.join(GOI_NHOM, '_da_bo', 'ketqua_P1_1410_NAP_001' + e) for e in ('.json', '.zip')]
    assert [x['nguoi'] for x in nt.liet_ke(root)] == ['P2'] and 'ketqua_P1_1410_NAP_001.zip' not in goi_files(root)
    assert len(tk.tinh(root)['nguon']['goi']) == 2                                                       # thống kê không đọc _da_bo
    nt.them(root, nd_tay(root, [f], nguoi='P1'))                                                         # gỡ rồi thêm lại được; gỡ lần hai không ghi đè bản trong _da_bo
    nt.bo(root, 'ketqua_P1_1410_NAP_001')
    assert sorted(os.listdir(os.path.join(root, GOI_NHOM, '_da_bo'))) == ['ketqua_P1_1410_NAP_001-bo2.json', 'ketqua_P1_1410_NAP_001-bo2.zip',
                                                                          'ketqua_P1_1410_NAP_001.json', 'ketqua_P1_1410_NAP_001.zip']
    assert sorted(nt.file_goi(root)) == ['ketqua_P2_1410_NAP_001']


def test_thu_muc_doc_trung_thu_muc_cua_thong_ke():
    assert nt.THU_MUC_DOC == tk.THU_MUC_GOI and nt.THU_MUC == tk.THU_MUC_GOI[1] and nt.NGUON == tk.NGUON_NHAP_TAY


def test_module_chi_thu_vien_chuan_khong_nap_numpy_gradio():
    import subprocess
    code = ("import sys\nsys.path.insert(0, %r)\nfrom m28core import nhap_tay\nfor m in ('numpy', 'gradio', 'cvat_sdk', 'eval50'):\n    assert m not in sys.modules, m\nprint('ok')\n"
            % os.path.join(HERE, '..', 'tool'))
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0 and 'ok' in r.stdout, r.stderr


# ---------- đầu-cuối: thống kê và tổng kết tính bản nhập tay như gói ----------
@pytest.fixture
def hai_nhom(tmp_path):
    """P1, P2 manual nhập tay (40 và 55 giây/mặt, 8 ảnh chung); P3, P4 assisted có gói đồng hồ (28 và 38,5 giây/mặt) trong outputs/goi_nhom."""
    root = du_an(tmp_path / 'p')
    for nguoi, giay, seed in (('P1', '5:20', 0), ('P2', '7:20', 1)):
        nt.them(root, nd_tay(root, [xml_file(tmp_path / nguoi, 'annotations.xml', mats(seed=seed))], nguoi=nguoi, giay=giay))
    for i, (p, b) in enumerate((('P3', 28.0), ('P4', 38.5))):
        viet_goi(root, nd_goi(p, 'assisted', b, n_nguoi_seed=2 + i), GOI_NHOM)
    return root


def test_dau_cuoi_thong_ke_tinh_nme_va_thoi_gian_gom_ban_nhap_tay(hai_nhom):
    st = tk.tinh(hai_nhom)
    ng = st['nguon']
    assert len(ng['goi']) == 4 and sorted(ng['goi_nhap_tay']) == ['ketqua_P1_1410_NAP_001.zip', 'ketqua_P2_1410_NAP_001.zip']           # .json đi kèm là bản trùng
    assert st['nhom']['nguoi'] == {'manual': ['P1', 'P2'], 'assisted': ['P3', 'P4']} and st['kiem']['lech'] is False and st['kiem']['chung'] == 8
    assert st['nme']['trong'] is None and st['nme']['n_nguoi_manual'] == 2 and st['nme']['nhap']['tong']['n'] == 8 and st['nme']['nhap']['tong']['tb'] > 0
    assert st['nme']['n_nguoi_ref'] == [2]                                                                # đáp án = trung bình nhãn của hai người manual nhập tay
    assert st['sua']['trong'] is None and st['sua']['n_mat'] == 16
    tg = st['thoi_gian']
    assert tg['trong'] is None and tg['nhom']['manual']['n_nguoi'] == 2 and tg['nhom']['manual']['n_mat'] == 16
    assert tg['nhom']['manual']['nguoi']['P1']['trung_vi'] == pytest.approx(40.0) and tg['nhom']['manual']['nguoi']['P2']['trung_vi'] == pytest.approx(55.0)
    assert tg['nhanh_hon_pct'] == pytest.approx(30.0, abs=0.01) and tg['n_uoc_luong'] >= 16
    assert not tg['do_nhay'] or tg['do_nhay']['n_bo'] == 0                                                # bản nhập tay không có cờ: không bị loại khỏi phép thử độ nhạy
    h = th.noi_dung(st)
    assert '(nhập tay)' in h and 'trong đó 2 bản nhập tay' in h and h.count('(nhập tay)') == 2


def test_dau_cuoi_tong_ket_tu_doc_ban_nhap_tay_cua_nhom_truong(hai_nhom, tmp_path, capsys):
    import csv
    vao = tmp_path / 'goi_nhan'
    vao.mkdir()
    for f in os.listdir(os.path.join(hai_nhom, GOI_NHOM)):
        if f.startswith(('ketqua_P3', 'ketqua_P4')) and f.endswith('.zip'):
            shutil.copy(os.path.join(hai_nhom, GOI_NHOM, f), vao)
    assert tong_ket.main(['--project', hai_nhom, '--vao', str(vao), '--ra', 'ra']) == 0
    out = capsys.readouterr().out
    assert 'Đọc thêm 2 bản nhập tay' in out and 'Đã dùng 4 gói' in out and 'ketqua_P1_1410_NAP_001.zip (nhập tay)' in out and 'assisted nhanh hơn manual 30,0%' in out
    d = os.path.join(hai_nhom, 'ra', os.listdir(os.path.join(hai_nhom, 'ra'))[0])
    dung = {r['ten_goi']: r['nguon'] for r in csv.DictReader(open(os.path.join(d, 'goi_da_dung.csv'), encoding='utf-8-sig'))}
    assert dung == {'ketqua_P1_1410_NAP_001.zip': 'nhap_tay', 'ketqua_P2_1410_NAP_001.zip': 'nhap_tay', 'ketqua_P3_1410_NAP_001.zip': 'dong_ho', 'ketqua_P4_1410_NAP_001.zip': 'dong_ho'}
    assert tong_ket.main(['--project', hai_nhom, '--vao', str(vao), '--ra', 'ra', '--khong-nhap-tay']) == 0
    out = capsys.readouterr().out
    assert 'Đọc thêm' not in out and 'Đã dùng 2 gói' in out
    assert tong_ket.main(['--project', hai_nhom, '--vao', os.path.join(hai_nhom, GOI_NHOM), '--ra', 'ra']) == 0       # đã nêu outputs/goi_nhom: không đọc thêm lần nữa
    out = capsys.readouterr().out
    assert 'Đọc thêm' not in out and 'Đã dùng 4 gói' in out
