"""Đặt tên người cho từng gói (nhóm trưởng, tab Thống kê): m28core/ten_nguoi.py, thong_ke.tinh dùng tên mới, file gói gốc không bị sửa."""
import hashlib
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
sys.path.insert(0, HERE)
import thong_ke as tk  # noqa: E402
import thong_ke_html as th  # noqa: E402
from dh_fake import du_an  # noqa: E402
from m28core import ten_nguoi  # noqa: E402
from tk_fake import mo_phong  # noqa: E402


@pytest.fixture
def world(tmp_path):
    """4 người (P1, P2 manual; P3, P4 assisted), gói trong outputs\\goi_nhom."""
    root = du_an(tmp_path)
    mo_phong(root)
    return root


def phien_of(root, nguoi):
    p = os.path.join(root, 'outputs', 'goi_nhom', f'ketqua_{nguoi}_1410_NAP_001.json')
    return json.load(open(p, encoding='utf-8'))['noi_dung']['phien'], p


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def test_dat_ten_doi_nguoi_trong_thong_ke_khong_sua_file_goc(world):
    ph, f = phien_of(world, 'P1')
    before = sha(f)
    st0 = tk.tinh(world)
    assert st0['nhom']['nguoi']['manual'] == ['P1', 'P2'] and st0['nguon']['doi_ten'] == []
    assert ten_nguoi.dat(world, ph, '  Cuong ', goi='ketqua_P1_1410_NAP_001.zip', goc='P1') == 'Cuong'
    st = tk.tinh(world)
    assert st['nhom']['nguoi']['manual'] == ['Cuong', 'P2'] and st['nhom']['nguoi']['assisted'] == ['P3', 'P4']
    assert [(a, b) for _t, a, b in st['nguon']['doi_ten']] == [('P1', 'Cuong')]
    assert 'Tên người do nhóm trưởng đặt' in th.noi_dung(st) and 'P1 → Cuong' in th.noi_dung(st)
    assert sha(f) == before                                                            # file gói gốc không bị sửa
    assert os.path.isfile(os.path.join(world, 'outputs', 'ten_nguoi.json'))


def test_hai_goi_cung_ten_moi_la_mot_nguoi_va_bo_ten_ve_lai_ten_goc(world):
    ph1, _ = phien_of(world, 'P1')
    ph2, _ = phien_of(world, 'P2')
    ten_nguoi.dat(world, ph1, 'Lan')
    ten_nguoi.dat(world, ph2, 'Lan')
    assert tk.tinh(world)['nhom']['nguoi']['manual'] == ['Lan']
    assert ten_nguoi.bo(world, ph1) and not ten_nguoi.bo(world, ph1)
    assert tk.tinh(world)['nhom']['nguoi']['manual'] == ['Lan', 'P1']
    ten_nguoi.bo(world, ph2)
    assert tk.tinh(world)['nhom']['nguoi']['manual'] == ['P1', 'P2']


@pytest.mark.parametrize('ten', ['', ' ', 'a b', 'x' * 33, '../P1', 'Nguyễn', None, 5])
def test_ten_sai_bi_tu_choi_va_khong_ghi_gi(world, ten):
    ph, _ = phien_of(world, 'P1')
    with pytest.raises(ten_nguoi.TenNguoiLoi):
        ten_nguoi.dat(world, ph, ten)
    assert ten_nguoi.doc(world) == {} and not os.path.exists(os.path.join(world, 'outputs', 'ten_nguoi.json'))


def test_ma_phien_sai_bi_tu_choi_va_file_hong_khong_lam_vo(world):
    for ph in ('', None, 'a b', '../x'):
        with pytest.raises(ten_nguoi.TenNguoiLoi):
            ten_nguoi.dat(world, ph, 'Cuong')
    p = os.path.join(world, 'outputs')
    os.makedirs(p, exist_ok=True)
    open(os.path.join(p, 'ten_nguoi.json'), 'w', encoding='utf-8').write('{hỏng')
    assert ten_nguoi.doc(world) == {} and tk.tinh(world)['nguon']['doi_ten'] == []
    json.dump({'ten': {'P1-x': {'ten': 'Ok'}, 'a b': {'ten': 'Sai'}, 'P2-y': {'ten': 'a b'}, 'P3-z': 'chuỗi'}}, open(os.path.join(p, 'ten_nguoi.json'), 'w', encoding='utf-8'))
    assert list(ten_nguoi.doc(world)) == ['P1-x']                                      # chỉ giữ dòng hợp lệ


def test_ap_dung_khong_sua_doi_tuong_cu():
    nd = {'phien': 'P1-1', 'nguoi': 'P1'}
    out, doi = ten_nguoi.ap_dung([('a.zip', nd)], {'P1-1': {'ten': 'Cuong', 'goi': '', 'goc': 'P1'}})
    assert nd['nguoi'] == 'P1' and out[0][1]['nguoi'] == 'Cuong' and out[0][1]['nguoi_goc'] == 'P1' and doi == [('a.zip', 'P1', 'Cuong')]
    out, doi = ten_nguoi.ap_dung([('a.zip', nd)], {'P1-1': {'ten': 'P1', 'goi': '', 'goc': 'P1'}})                    # đặt trùng tên gốc: không tính là đổi
    assert doi == [] and out[0][1] is nd


def test_dong_bi_danh_dau_vao_log_gop_theo_nhom_va_ban_xuat_van_du_bang(world):
    from tk_fake import nd_goi, viet_goi
    nd = nd_goi('P5', 'assisted', 6.2, n_nguoi_seed=4)
    nd['canh_bao'] = ['chua_co_nhom']                                                   # gói có cảnh báo: mọi dòng thời gian của nó bị đánh dấu
    viet_goi(world, nd, 'outputs/goi_nhom')
    st = tk.tinh(world)
    dau = [o for o in st['thoi_gian']['danh_dau'] if o['person'] == 'P5']
    assert len(dau) == 8                                                                # 8 mặt, mỗi mặt một dòng bị đánh dấu
    chinh, log = th.noi_dung_gon(st)
    full = th.noi_dung(st)
    assert 'Dòng bị đánh dấu' not in chinh and 'Dòng bị đánh dấu — vẫn nằm trong chỉ số chính' in full and full.count('NAP_001_0') >= 8   # trang chính ẩn, bản xuất giữ bảng từng mặt
    assert 'Dòng thời gian bị đánh dấu' in log and 'vẫn nằm trong chỉ số chính' in log
    bang_log = log[log.index('Dòng thời gian bị đánh dấu'):]
    assert 'NAP_001_0' not in bang_log                                                  # không liệt kê từng mặt
    assert bang_log.count('>P5<') == 1 and '>8<' in bang_log and 'chua_co_nhom' in bang_log          # một dòng gộp cho P5: 8 mặt


# ---------- gói nạp ở tab Thống kê được LƯU (outputs/goi_da_nap), gỡ được ----------
def test_luu_goi_nap_luu_mot_lan_bo_qua_ban_trung_va_goi_hong(world, tmp_path):
    from tk_fake import nd_goi, viet_goi
    ngoai = tmp_path / 'ngoai'
    r = viet_goi(world, nd_goi('P9', 'assisted', 20.0, n_nguoi_seed=5), 'tam_ngoai')                       # gói của người khác, nằm ngoài các thư mục gói mặc định
    src = os.path.join(world, 'tam_ngoai')
    files = [os.path.join(src, f) for f in sorted(os.listdir(src))]                                         # .json và .zip của CÙNG một phiên
    bad = os.path.join(src, 'hong.zip')
    open(bad, 'wb').write(b'PK\x03\x04 hong')
    names = {p['name'] for p in tk.bang_mat.load_cfg(world)['points']}
    res = tk.luu_goi_nap(world, files + [bad], names)
    d = os.path.join(world, 'outputs', 'goi_da_nap')
    assert len(res['luu']) == 1 and len(res['co_san']) == 1 and [t for t, _w in res['loi']] == ['hong.zip']      # cùng phiên: chỉ chép một file
    assert sorted(os.listdir(d)) == res['luu'] and sha(os.path.join(d, res['luu'][0])) == sha(os.path.join(src, res['luu'][0]))   # giữ nguyên byte
    st = tk.tinh(world)                                                                                       # không truyền file nào: vẫn thấy P9 (đã lưu)
    assert 'P9' in st['nhom']['nguoi']['assisted'] and any('P9' in t for t in st['nguon']['goi'])
    again = tk.luu_goi_nap(world, files, names)                                                               # nạp lại: không chép thêm
    assert again['luu'] == [] and len(again['co_san']) == 2 and sorted(os.listdir(d)) == res['luu']
    own = tk.luu_goi_nap(world, [os.path.join(world, 'outputs', 'goi_nhom', 'ketqua_P1_1410_NAP_001.zip')], names)   # gói đã có trong thư mục mặc định
    assert own['luu'] == [] and own['co_san'] == ['ketqua_P1_1410_NAP_001.zip']
    ph = json.load(open([f for f in files if f.endswith('.json')][0], encoding='utf-8'))['noi_dung']['phien']
    moved = tk.bo_goi_nap(world, ph, names)
    assert moved == res['luu'] and os.listdir(d) == ['_da_bo'] and os.listdir(os.path.join(d, '_da_bo')) == res['luu']     # chuyển, không xoá
    assert 'P9' not in tk.tinh(world)['nhom']['nguoi']['assisted']
    assert tk.bo_goi_nap(world, phien_of(world, 'P1')[0], names) == []                                         # gói trong goi_nhom: không gỡ ở đây
    assert tk.bo_goi_nap(world, '', names) == [] and tk.bo_goi_nap(world, None, names) == []


def test_ten_file_la_bi_doi_khi_luu(world, tmp_path):
    from tk_fake import nd_goi, viet_goi
    viet_goi(world, nd_goi('P8', 'assisted', 20.0, n_nguoi_seed=6), 'tam2')
    src = os.path.join(world, 'tam2')
    z = [f for f in os.listdir(src) if f.endswith('.zip')][0]
    la = os.path.join(src, 'gói của tôi (1).zip')
    os.replace(os.path.join(src, z), la)
    res = tk.luu_goi_nap(world, [la])
    assert len(res['luu']) == 1 and res['luu'][0].startswith('ketqua_') and res['luu'][0].endswith('.zip') and ' ' not in res['luu'][0]


def test_dat_ten_khong_lam_dem_trung_mat_co_nhan_raw_cua_ten_goc(world):
    """Nhóm trưởng đặt tên cho gói của P1: nhãn raw\\<task>_P1_<DDMM>.xml của cùng các mặt vẫn được bỏ (đã có trong gói), không thành người thứ hai."""
    import shutil
    from thong_ke_fake import Proj  # noqa: F401  (chỉ để chắc module giả có sẵn)
    st0 = tk.tinh(world)
    n_manual0 = sorted(st0['nhom']['nguoi']['manual'])
    # chép nhãn cuối của gói P1 thành một file raw cùng người, cùng ảnh
    ph, f = phien_of(world, 'P1')
    nd = json.load(open(f, encoding='utf-8'))['noi_dung']
    nd['nhan_file'] = 'm28-manual_P1_1410.xml'                                      # gói dựng từ đúng file raw này
    from tk_fake import viet_goi
    viet_goi(world, nd, 'outputs/goi_nhom')
    names = [p['name'] for p in tk.bang_mat.load_cfg(world)['points']]
    from m28core import steps
    xml = ['<?xml version="1.0" encoding="utf-8"?>', '<annotations>', '  <version>1.1</version>']
    for i, r in enumerate(nd['ket_qua']):
        pts = [tuple(r['nhan_cuoi'][n]) for n in names]
        xml.append(steps.image_xml(i, r['anh'], names, pts, [False] * len(names), 512, 512))
    xml.append('</annotations>')
    os.makedirs(os.path.join(world, 'raw'), exist_ok=True)
    open(os.path.join(world, 'raw', f"m28-manual_P1_1410.xml"), 'w', encoding='utf-8').write('\n'.join(xml))
    st1 = tk.tinh(world)
    assert sorted(st1['nhom']['nguoi']['manual']) == n_manual0                       # raw trùng mặt với gói: không thêm người
    ten_nguoi.dat(world, ph, 'Cuong')
    st2 = tk.tinh(world)
    assert sorted(st2['nhom']['nguoi']['manual']) == sorted(['Cuong' if x == 'P1' else x for x in n_manual0])   # không có cả Cuong lẫn P1


def test_ban_moi_hon_cua_cung_goi_duoc_luu_va_thay_ban_cu(world):
    """Đồng đội xuất lại gói (cùng mã phiên, tao_luc mới hơn, ví dụ kèm nhãn): Load & Calculate lưu bản mới, chuyển bản cũ trong goi_da_nap vào _da_bo; bản cũ hơn thì bỏ qua."""
    from tk_fake import nd_goi, viet_goi
    from m28core import goi_kq
    names = {p['name'] for p in tk.bang_mat.load_cfg(world)['points']}
    cu = nd_goi('P9', 'assisted', 20.0, n_nguoi_seed=5)
    viet_goi(world, cu, 'v1')
    v1 = [os.path.join(world, 'v1', f) for f in os.listdir(os.path.join(world, 'v1')) if f.endswith('.zip')]
    assert len(tk.luu_goi_nap(world, v1, names)['luu']) == 1
    moi = dict(cu, tao_luc='2026-10-15T09:00:00+07:00', ghi_chu='xuất lại có nhãn')
    viet_goi(world, moi, 'v2')
    v2 = [os.path.join(world, 'v2', f) for f in os.listdir(os.path.join(world, 'v2')) if f.endswith('.zip')]
    r = tk.luu_goi_nap(world, v2, names)
    assert r['moi_hon'] and not r['luu'] and not r['co_san']
    d = os.path.join(world, 'outputs', 'goi_da_nap')
    con = [f for f in os.listdir(d) if f != '_da_bo']
    assert len(con) == 1 and len(os.listdir(os.path.join(d, '_da_bo'))) == 1                                       # bản cũ chuyển, không xoá
    dung = {nd['phien']: nd for _t, nd in goi_kq.quet([d], names)['tot']}[cu['phien']]
    assert dung['ghi_chu'] == 'xuất lại có nhãn'                                                                   # thống kê dùng bản mới
    r = tk.luu_goi_nap(world, v1, names)                                                                            # nạp lại bản cũ: không đè bản mới
    assert r['co_san'] and not r['luu'] and not r['moi_hon'] and len([f for f in os.listdir(d) if f != '_da_bo']) == 1


def test_ten_dat_o_cho_cu_van_doc_duoc_va_ghi_lan_sau_thi_chuyen(world):
    ph, _f = phien_of(world, 'P1')
    cu = os.path.join(world, 'outputs', 'thong_ke', 'ten_nguoi.json')
    os.makedirs(os.path.dirname(cu), exist_ok=True)
    json.dump({'phien_ban': 1, 'ten': {ph: {'ten': 'Cuong', 'goi': 'x.zip', 'goc': 'P1'}}}, open(cu, 'w', encoding='utf-8'))
    assert ten_nguoi.doc(world)[ph]['ten'] == 'Cuong' and 'Cuong' in tk.tinh(world)['nhom']['nguoi']['manual']     # chưa có file mới: đọc chỗ cũ
    ph2, _f2 = phien_of(world, 'P2')
    ten_nguoi.dat(world, ph2, 'Lan')
    assert not os.path.exists(cu) and set(ten_nguoi.doc(world)) == {ph, ph2}                                            # ghi lần sau: chuyển hẳn, không mất tên cũ


def test_moi_hon_so_theo_thoi_diem_that_ke_ca_khac_mui_gio():
    a = {'tao_luc': '2026-10-15T01:00:00+00:00'}                                        # = 08:00 giờ VN
    b = {'tao_luc': '2026-10-15T07:30:00+07:00'}                                        # = 00:30 UTC
    assert tk._moi_hon(a, b) and not tk._moi_hon(b, a)                                  # so chuỗi sẽ sai ('01' < '07')
    assert tk._moi_hon({'tao_luc': '2026-10-15T01:00:00+00:00'}, {}) and not tk._moi_hon({}, {'tao_luc': '2026-10-15T01:00:00+00:00'})
    assert not tk._moi_hon({}, {})


def test_ten_cu_co_gach_duoi_van_doc_duoc(world):
    ph, _f = phien_of(world, 'P1')
    os.makedirs(os.path.join(world, 'outputs'), exist_ok=True)
    json.dump({'phien_ban': 1, 'ten': {ph: {'ten': 'Lan_2', 'goi': '', 'goc': 'P1'}}}, open(os.path.join(world, 'outputs', 'ten_nguoi.json'), 'w', encoding='utf-8'))
    assert ten_nguoi.doc(world)[ph]['ten'] == 'Lan_2' and 'Lan_2' in tk.tinh(world)['nhom']['nguoi']['manual']


def test_log_bao_so_mat_trung_bi_bo(world):
    """Hai gói cùng tên người (ví dụ cùng để mặc định P1) trên cùng ảnh: các mặt trùng bị bỏ khỏi số đo; Log phải nói rõ để nhóm trưởng đặt tên cho từng gói."""
    from tk_fake import nd_goi, viet_goi
    viet_goi(world, nd_goi('P3', 'assisted', 25.0, n_nguoi_seed=9, phien='P3-20261014-200000-zz99', bat_dau='2026-10-14T20:00:00+07:00', dot='NAP_009'), 'outputs/goi_nhom')
    st = tk.tinh(world)
    assert st['meta']['n_mat_trung'] > 0
    chinh, log = th.noi_dung_gon(st)
    assert f"Đã bỏ {st['meta']['n_mat_trung']} mặt trùng" in log and 'Gói đã nạp' in log
    assert f"Đã bỏ {st['meta']['n_mat_trung']} mặt trùng" in chinh and 'Gói đã nạp' in chinh            # cảnh báo cả ở trang chính: nhóm trưởng không mở Log vẫn thấy


def test_dat_ten_khong_giau_nhan_raw_cua_nguoi_that_cung_ten_goc(world):
    """Gói làm với tên mặc định P1 (người khác) được đặt tên Lan; file raw của người P1 THẬT (file khác, không phải file gói đã dùng) vẫn được tính, không bị bỏ im lặng."""
    ph, f = phien_of(world, 'P1')
    nd = json.load(open(f, encoding='utf-8'))['noi_dung']
    names = [p['name'] for p in tk.bang_mat.load_cfg(world)['points']]
    from m28core import steps
    xml = ['<?xml version="1.0" encoding="utf-8"?>', '<annotations>', '  <version>1.1</version>']
    for i, r in enumerate(nd['ket_qua']):
        pts = [(x + 3.0, y + 2.0) for x, y in (tuple(r['nhan_cuoi'][n]) for n in names)]
        xml.append(steps.image_xml(i, r['anh'], names, pts, [False] * len(names), 512, 512))
    xml.append('</annotations>')
    os.makedirs(os.path.join(world, 'raw'), exist_ok=True)
    open(os.path.join(world, 'raw', 'm28-manual_P1_1510.xml'), 'w', encoding='utf-8').write('\n'.join(xml))   # nhan_file của gói là 'demo.xml': không phải file này
    ten_nguoi.dat(world, ph, 'Lan')
    st = tk.tinh(world)
    ng = st['nhom']['nguoi']['manual']
    assert 'Lan' in ng and 'P1' in ng                                                 # hai người: gói (Lan) và nhãn raw của P1 thật


def test_luu_loi_giu_ten_file_tai_len_va_bao_chua_luu(world, tmp_path, monkeypatch):
    """Chép vào goi_da_nap lỗi (đĩa đầy...) với file tải lên tên lạ (ketqua (1).zip): lỗi mang tên file TẢI LÊN để tab vẫn tính từ file đó, và chua_luu báo giữ ô nạp."""
    import shutil
    from tk_fake import nd_goi, viet_goi
    import thong_ke_ui
    r = viet_goi(world, nd_goi('P9', 'assisted', 20.0, n_nguoi_seed=5), 'tam_ngoai')
    la = tmp_path / 'ketqua (1).zip'
    shutil.copy(os.path.join(world, 'tam_ngoai', os.path.basename(r['zip'])), la)
    names = {p['name'] for p in tk.bang_mat.load_cfg(world)['points']}

    def hong(*_a, **_k):
        raise OSError('đĩa đầy')
    monkeypatch.setattr(tk, '_chuyen_vao', hong)
    res = tk.luu_goi_nap(world, [str(la)], names)
    assert [t for t, _w in res['loi']] == ['ketqua (1).zip'] and res['chua_luu'] == ['ketqua (1).zip'] and res['luu'] == []
    assert thong_ke_ui.nap_note(dict(luu=[], moi_hon=[], da_bo=[], co_san=[], loi=[]), [str(la)]) == ('', 'info')    # không làm gì (trang đang đóng): không câu cụt
    t, _lv = thong_ke_ui.nap_note(dict(luu=['a.zip'], moi_hon=[], da_bo=[], co_san=[], loi=[]), [str(la)], tinh_xong=False)
    assert 'Đã lưu 1 gói' in t and 'đã tính lại' not in t
