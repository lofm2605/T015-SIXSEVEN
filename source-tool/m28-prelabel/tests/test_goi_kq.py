"""Thử m28core/goi_kq.py (gói kết quả gửi nhóm trưởng) và m28core/nhom.py (nhóm thí nghiệm): dữ liệu giả, không ảnh, không mạng."""
import json
import os
import socket
import sys
import zipfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
sys.path.insert(0, HERE)
from dh_fake import cfg_real, du_an, mat_mau, viet_nhan, viet_nhap  # noqa: E402
from m28core import goi_kq, nhom  # noqa: E402


def nd_mau(nguoi='P5', nhom_='assisted', phien=None, dot='NAP_001', ket_qua=None, giay=100.0, bat_dau='2026-10-14T18:30:00+07:00', tao_luc='2026-10-14T19:30:00+07:00', **kw):
    d = dict(phien=phien or f'{nguoi}-20261014-183000-ab12', nguoi=nguoi, nhom=nhom_, dot=dot, bo_anh=dot, task=f'demo-{dot}', job='', so_mat=4, giay_phien=giay,
             giay_tam_dung=5.0, so_lan_tam_dung=1, bat_dau=bat_dau, ket_thuc='2026-10-14T19:10:00+07:00', uoc_luong_chia_deu=True, mat_do=[], canh_bao=[], ghi_chu='',
             sua_tay=0, tao_luc=tao_luc, nhan_file='', co_nhan=bool(ket_qua), co_nhap=False, cau_hinh=dict(so_diem=50, nguong_sua=2.0), ket_qua=ket_qua or [])
    d.update(kw)
    return d


def mat_kq(anh='F_001', nhap=False):
    pts = {k: [round(x, 2), round(y, 2)] for k, (x, y) in mat_mau(1).items()}
    r = dict(anh=anh, nhan_cuoi=pts)
    if nhap:
        r.update(nhap=pts, diem_da_sua=[], nme_nhap_so_nhan_cuoi=0.0)
    return r


def ghi(root, nd, ddmm='1410'):
    return goi_kq.ghi_goi(root, nd, ddmm=ddmm)


def test_roundtrip_zip_and_json_have_same_content_and_sha(tmp_path):
    root = du_an(tmp_path)
    nd = nd_mau(ket_qua=[mat_kq('F_001', True), mat_kq('F_002', True)])
    r = ghi(root, nd)
    assert r['ten'] == 'ketqua_P5_1410_NAP_001' and r['zip'] == os.path.join('outputs', 'ket_qua', 'ketqua_P5_1410_NAP_001.zip')
    a, _w = goi_kq.doc_goi(os.path.join(root, r['zip']))
    b, _w = goi_kq.doc_goi(os.path.join(root, r['json']))
    assert a == b == nd
    vo = json.load(open(os.path.join(root, r['json']), encoding='utf-8'))
    assert vo['dinh_dang'] == 'm28-ketqua' and vo['phien_ban_dinh_dang'] == 1 and vo['sha256'] == goi_kq.sha256_noi_dung(nd) and len(vo['sha256']) == 64
    with zipfile.ZipFile(os.path.join(root, r['zip'])) as z:
        assert sorted(z.namelist()) == ['DOC-TOI.txt', 'ketqua.json']


def test_tampered_sha_wrong_format_newer_version_bad_zip_are_refused_with_reason(tmp_path):
    root = du_an(tmp_path)
    r = ghi(root, nd_mau(ket_qua=[mat_kq()]))
    p = os.path.join(root, r['json'])
    vo = json.load(open(p, encoding='utf-8'))

    def thu(obj, match, name='x.json'):
        q = os.path.join(str(tmp_path), name)
        open(q, 'w', encoding='utf-8').write(json.dumps(obj) if not isinstance(obj, str) else obj)
        with pytest.raises(goi_kq.GoiLoi, match=match):
            goi_kq.doc_goi(q)
    bad = json.loads(json.dumps(vo))
    bad['noi_dung']['giay_phien'] = 1.0
    thu(bad, 'sha256 không khớp')
    thu(dict(vo, dinh_dang='khac'), 'không phải gói kết quả M28')
    thu(dict(vo, phien_ban_dinh_dang=99), 'mới hơn')
    thu(dict(vo, phien_ban_dinh_dang='a'), 'số phiên bản')
    thu('{hỏng', 'không phải JSON')
    thu([], 'không phải gói')
    thu({k: v for k, v in vo.items() if k != 'noi_dung'}, 'thiếu phần nội dung')
    open(os.path.join(str(tmp_path), 'z.zip'), 'wb').write(b'PK\x03\x04 hong')
    with pytest.raises(goi_kq.GoiLoi, match='zip'):
        goi_kq.doc_goi(os.path.join(str(tmp_path), 'z.zip'))
    with pytest.raises(goi_kq.GoiLoi, match='Không đọc được'):
        goi_kq.doc_goi(os.path.join(str(tmp_path), 'khong_co.json'))


def test_zip_with_path_traversal_or_missing_json_or_too_big_is_refused(tmp_path, monkeypatch):
    root = du_an(tmp_path)
    r = ghi(root, nd_mau(ket_qua=[mat_kq()]))
    good = open(os.path.join(root, r['json']), 'rb').read()
    p = os.path.join(str(tmp_path), 'bad.zip')
    with zipfile.ZipFile(p, 'w') as z:
        z.writestr('../ketqua.json', good)
    with pytest.raises(goi_kq.GoiLoi, match='đường dẫn'):
        goi_kq.doc_goi(p)
    with zipfile.ZipFile(p, 'w') as z:
        z.writestr('khac.txt', 'x')
    with pytest.raises(goi_kq.GoiLoi, match='không có ketqua.json'):
        goi_kq.doc_goi(p)
    monkeypatch.setattr(goi_kq, 'MAX_BYTE', 100)
    with pytest.raises(goi_kq.GoiLoi, match='quá lớn'):
        goi_kq.doc_goi(os.path.join(root, r['json']))


@pytest.mark.parametrize('field, value, match', [
    ('nguoi', 'a b', 'tên người'), ('nhom', 'tay', 'manual hoặc assisted'), ('phien', 'a b', 'mã phiên'), ('so_mat', -1, 'so_mat'), ('giay_phien', -3, 'giay_phien'),
    ('uoc_luong_chia_deu', 'co', 'uoc_luong_chia_deu'), ('mat_do', [dict(giay=0)], 'mat_do'), ('ket_qua', [dict(anh='a/b', nhan_cuoi={})], 'đường dẫn'),
    ('ket_qua', [dict(anh='a', nhan_cuoi={'diem_la': [1, 2]})], 'sai định dạng'), ('ket_qua', [dict(anh='a', nhan_cuoi={'songmui_1': [1, 'x']})], 'sai định dạng'),
    ('ket_qua', [dict(anh='a', nhan_cuoi={}), dict(anh='a', nhan_cuoi={})], 'lặp lại'),
])
def test_structure_validation_rejects(tmp_path, field, value, match):
    nd = nd_mau(**{field: value})
    names = {p['name'] for p in cfg_real()['points']}
    probs = goi_kq.kiem_cau_truc(nd, names)
    assert probs and match in ' '.join(probs), probs
    vo = goi_kq.dong_goi(nd)
    p = os.path.join(str(tmp_path), 'x.json')
    json.dump(vo, open(p, 'w', encoding='utf-8'))
    with pytest.raises(goi_kq.GoiLoi, match=match):
        goi_kq.doc_goi(p, names)


def test_draft_in_a_manual_package_is_refused(tmp_path):
    nd = nd_mau(nhom_='manual', ket_qua=[mat_kq('F_001', True)])
    assert any('không phải nhóm assisted' in p for p in goi_kq.kiem_cau_truc(nd))


def test_privacy_scan_blocks_paths_emails_hostname_token_on_write_and_on_read(tmp_path, monkeypatch):
    root = du_an(tmp_path)
    monkeypatch.setattr(socket, 'gethostname', lambda: 'may-cua-lam')
    for text, why in (('/home/ten/anh.png', 'đường dẫn tuyệt đối'), ('C:\\Users\\a\\x', 'đường dẫn tuyệt đối'), ('xem /tmp/abc', 'đường dẫn tuyệt đối'),
                      ('lien he a.b@example.com', 'email'), ('tại máy-cua-lam'.replace('máy', 'may'), 'tên máy')):
        with pytest.raises(goi_kq.GoiLoi, match=why):
            ghi(root, nd_mau(ghi_chu=text))
    from m28core import cvat_io
    cvat_io.register_secret('tok-RAT-BI-MAT-123456')
    with pytest.raises(goi_kq.GoiLoi, match='token'):
        ghi(root, nd_mau(ghi_chu='dán nhầm tok-RAT-BI-MAT-123456'))
    assert not os.path.exists(os.path.join(root, 'outputs', 'ket_qua')) or not os.listdir(os.path.join(root, 'outputs', 'ket_qua'))
    vo = goi_kq.dong_goi(nd_mau(ghi_chu='gửi /home/ai/x'))                                         # gói viết tay có sha đúng nhưng nội dung nhạy cảm: đọc cũng chặn
    p = os.path.join(str(tmp_path), 'leak.json')
    json.dump(vo, open(p, 'w', encoding='utf-8'))
    with pytest.raises(goi_kq.GoiLoi, match='đường dẫn tuyệt đối'):
        goi_kq.doc_goi(p)
    assert goi_kq.kiem_rieng_tu(nd_mau()) == []


def test_name_collision_other_phien_gets_suffix_same_phien_rewrites(tmp_path):
    root = du_an(tmp_path)
    a = ghi(root, nd_mau(phien='P5-A-1111'))
    b = ghi(root, nd_mau(phien='P5-B-2222'))
    c = ghi(root, nd_mau(phien='P5-A-1111', giay=123.0))
    assert (a['ten'], b['ten'], c['ten']) == ('ketqua_P5_1410_NAP_001', 'ketqua_P5_1410_NAP_001-2', 'ketqua_P5_1410_NAP_001')
    assert goi_kq.doc_goi(os.path.join(root, c['zip']))[0]['giay_phien'] == 123.0
    assert goi_kq.ten_goi('P1', '0101', 'a b/c') == 'ketqua_P1_0101_a-b-c' and goi_kq.ten_goi('P1', '0101', '') == 'ketqua_P1_0101_dot'


def test_quet_merges_people_drops_bad_and_duplicates_with_reasons(tmp_path):
    root = du_an(tmp_path)
    d = os.path.join(str(tmp_path), 'goi')
    os.makedirs(d)
    n1 = nd_mau('P1', 'manual', phien='P1-1', bat_dau='2026-10-14T18:00:00+07:00')
    n2 = nd_mau('P2', 'assisted', phien='P2-1', bat_dau='2026-10-14T18:10:00+07:00')
    for nd in (n1, n2):
        r = ghi(root, nd)
        for ext in ('zip', 'json'):
            os.replace(os.path.join(root, r[ext]), os.path.join(d, os.path.basename(r[ext])))
    import shutil
    shutil.copy(os.path.join(d, 'ketqua_P1_1410_NAP_001.zip'), os.path.join(d, 'ban_chep_cua_P1.zip'))             # chép trùng
    open(os.path.join(d, 'hong.zip'), 'wb').write(b'PK\x03\x04 hong')
    open(os.path.join(d, 'ghi_chu.json'), 'w').write('{"a": 1}')
    open(os.path.join(d, 'doc_lai.txt'), 'w').write('bỏ qua file không phải zip/json')
    nd_cu = nd_mau('P2', 'assisted', phien='P2-1', giay=999.0, tao_luc='2026-10-14T10:00:00+07:00', bat_dau='2026-10-14T18:10:00+07:00')       # cùng phiên nhưng cũ hơn
    vo = goi_kq.dong_goi(nd_cu)
    json.dump(vo, open(os.path.join(d, 'cu_P2.json'), 'w', encoding='utf-8'))
    res = goi_kq.quet([d])
    assert [n['nguoi'] for _t, n in res['tot']] == ['P1', 'P2'] and {t for t, _n in res['tot']} == {'ketqua_P1_1410_NAP_001.zip', 'ketqua_P2_1410_NAP_001.zip'}
    ht = dict(res['hong'])
    assert 'hong.zip' in ht and 'zip' in ht['hong.zip'] and 'ghi_chu.json' in ht and 'không phải gói' in ht['ghi_chu.json'] and 'doc_lai.txt' not in ht
    tr = ' | '.join(f'{a}: {b}' for a, b in res['trung'])
    assert 'ban_chep_cua_P1.zip' in tr and 'trùng nội dung' in tr and 'cu_P2.json' in tr and 'cũ hơn' in tr
    assert goi_kq.quet([os.path.join(d, 'ketqua_P1_1410_NAP_001.zip'), os.path.join(d, 'khong_co')])['tot'][0][1]['nguoi'] == 'P1'


def test_quet_same_person_batch_and_start_time_under_two_phien_ids_is_a_copy(tmp_path):
    root = du_an(tmp_path)
    d = os.path.join(str(tmp_path), 'goi')
    os.makedirs(d)
    for ph in ('P1-a', 'P1-b'):
        r = ghi(root, nd_mau('P1', 'manual', phien=ph))
        os.replace(os.path.join(root, r['json']), os.path.join(d, f'ketqua_{ph}.json'))
        os.remove(os.path.join(root, r['zip']))
        for f in os.listdir(os.path.join(root, 'outputs', 'ket_qua')):
            os.remove(os.path.join(root, 'outputs', 'ket_qua', f))
    res = goi_kq.quet([d])
    assert len(res['tot']) == 1 and any('cùng người, đợt và giờ bắt đầu' in w for _t, w in res['trung'])


# ---------- xay_ket_qua ----------
def test_xay_ket_qua_final_draft_changed_points_and_nme(tmp_path):
    root = du_an(tmp_path)
    cfg = cfg_real()
    anh = {f'F_{i:03d}.png': mat_mau(i) for i in range(1, 3)}
    nhan = {k: {n: (x + (8.0 if n == 'songmui_1' else 0.1), y) for n, (x, y) in v.items()} for k, v in anh.items()}
    viet_nhap(root, 'NAP_001', anh)
    lp = viet_nhan(root, 'demo-NAP_001', 'P5', '1410', nhan, thieu={'F_002.png': ['moingoai_1']})
    kq, info = goi_kq.xay_ket_qua(root, cfg, 'assisted', 'NAP_001', lp)
    assert info['co_nhan'] and info['co_nhap'] and info['nhan_file'] == 'demo-NAP_001_P5_1410.xml' and info['canh_bao'] == []
    assert [k['anh'] for k in kq] == ['F_001', 'F_002'] and kq[0]['diem_da_sua'] == ['songmui_1'] and sorted(kq[1]['diem_da_sua']) == ['moingoai_1', 'songmui_1']
    assert 0 < kq[0]['nme_nhap_so_nhan_cuoi'] < 5 and 'moingoai_1' in kq[1]['nhap'] and 'moingoai_1' not in kq[1]['nhan_cuoi']
    assert all(len(v) == 2 and v == [round(v[0], 2), round(v[1], 2)] for v in kq[0]['nhan_cuoi'].values())
    # nhóm manual: không có nháp dù có lượt
    kq2, info2 = goi_kq.xay_ket_qua(root, cfg, 'manual', 'NAP_001', lp)
    assert 'nhap' not in kq2[0] and info2['co_nhap'] is False and info2['canh_bao'] == []
    # không có lượt: assisted vẫn có nhãn, báo thiếu nháp
    kq3, info3 = goi_kq.xay_ket_qua(root, cfg, 'assisted', 'KHONG_CO', lp)
    assert 'nhap' not in kq3[0] and info3['canh_bao'] == ['thieu_nhap']
    kq4, info4 = goi_kq.xay_ket_qua(root, cfg, 'assisted', '../etc', lp)                                    # tên đợt xấu không đi ra ngoài runs/
    assert info4['co_nhap'] is False
    assert goi_kq.xay_ket_qua(root, cfg, 'assisted', 'NAP_001', None) == ([], dict(co_nhan=False, co_nhap=False, nhan_file='', canh_bao=['chua_co_nhan']))


def test_ket_qua_tu_nhan_da_doc_trung_xay_ket_qua_tu_file(tmp_path):
    import eval50
    root = du_an(tmp_path)
    cfg = cfg_real()
    anh = {f'F_{i:03d}.png': mat_mau(i) for i in range(1, 4)}
    viet_nhap(root, 'NAP_001', anh)
    lp = viet_nhan(root, 'demo-NAP_001', 'P5', '1410', {k: {n: (x + (6.0 if n == 'mattrai_3' else 0.0), y) for n, (x, y) in v.items()} for k, v in anh.items()})
    labels = eval50.read_labels(lp, cfg, warn=lambda *_a: None)
    for dk in ('assisted', 'manual'):
        kq, info = goi_kq.xay_ket_qua(root, cfg, dk, 'NAP_001', lp)
        kq2, co_nhap = goi_kq.ket_qua_tu_nhan(root, cfg, dk, 'NAP_001', labels)
        assert kq2 == kq and co_nhap == info['co_nhap'] == (dk == 'assisted')
    assert goi_kq.ket_qua_tu_nhan(root, cfg, 'assisted', 'KHONG_CO', labels)[1] is False


def test_ghi_goi_thu_muc_khac_mac_dinh_van_la_outputs_ket_qua(tmp_path):
    root = du_an(tmp_path)
    r = goi_kq.ghi_goi(root, nd_mau(ket_qua=[mat_kq()]), ddmm='1410', thu_muc=os.path.join('outputs', 'goi_nhom'))
    assert r == dict(ten='ketqua_P5_1410_NAP_001', zip=os.path.join('outputs', 'goi_nhom', 'ketqua_P5_1410_NAP_001.zip'),
                     json=os.path.join('outputs', 'goi_nhom', 'ketqua_P5_1410_NAP_001.json'))
    assert sorted(os.listdir(os.path.join(root, 'outputs', 'goi_nhom'))) == ['ketqua_P5_1410_NAP_001.json', 'ketqua_P5_1410_NAP_001.zip']
    assert not os.path.exists(os.path.join(root, 'outputs', 'ket_qua'))
    assert ghi(root, nd_mau(ket_qua=[mat_kq()]))['zip'] == os.path.join('outputs', 'ket_qua', 'ketqua_P5_1410_NAP_001.zip')


def test_xay_ket_qua_old_label_or_empty_file(tmp_path):
    root = du_an(tmp_path)
    p = os.path.join(root, 'raw', 'demo-X_P5_1410.xml')
    open(p, 'w').write('<annotations><version>1.1</version><image id="0" name="a.png" width="1" height="1"><skeleton label="face50"/></image></annotations>')
    kq, info = goi_kq.xay_ket_qua(root, cfg_real(), 'manual', 'X', p)
    assert kq == [] and info['canh_bao'] == ['nhan_rong'] and info['co_nhan'] is False


# ---------- nhom.py ----------
def test_nhom_config_sample_is_empty_and_errors_do_not_crash(tmp_path):
    real = nhom.doc(os.path.join(HERE, '..'))
    assert real['co_file'] and real['nhom'] == {} and real['bo_anh'] == '' and real['loi'] == []               # file mẫu trong repo: trống, không đoán ai ở nhóm nào
    root = str(tmp_path)
    assert nhom.doc(root) == dict(nhom={}, bo_anh='', co_file=False, loi=[], duong_dan=nhom.FILE_REL)
    os.makedirs(os.path.join(root, 'config'))
    p = os.path.join(root, 'config', 'nhom_thi_nghiem.json')
    open(p, 'w', encoding='utf-8').write(json.dumps({'nhom': {'P1': 'manual', 'P2': 'assisted', 'a b': 'manual', 'P3': 'lạ', '../x': 'manual'}, 'bo_anh': 'NAP_001'}))
    c = nhom.doc(root)
    assert c['nhom'] == {'P1': 'manual', 'P2': 'assisted'} and c['bo_anh'] == 'NAP_001' and len(c['loi']) == 3
    assert nhom.nhom_cua(c, 'P1') == 'manual' and nhom.nhom_cua(c, 'P5') is None and nhom.dem_nguoi(c) == dict(manual=1, assisted=1)
    for bad, why in (('{hỏng', 'không đọc được'), ('[]', 'sai định dạng'), (json.dumps({'nhom': []}), 'phải là đối tượng'), (json.dumps({'nhom': {}, 'bo_anh': 'a b'}), 'bo_anh')):
        open(p, 'w', encoding='utf-8').write(bad)
        c = nhom.doc(root)
        assert c['nhom'] == {} and why in ' '.join(c['loi']), (bad, c)
