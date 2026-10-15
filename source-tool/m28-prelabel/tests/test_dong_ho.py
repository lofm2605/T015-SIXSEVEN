"""Thử tool/dong_ho.py (logic đồng hồ bấm giờ, QĐ-006): đồng hồ GIẢ tiêm vào, thư mục tạm, không ảnh, không mạng, không CVAT.

Phiên là đơn vị đo; bấm từng mặt là tuỳ chọn. Mỗi ca bất thường (quên bấm, đóng trang, máy khởi động lại, giây <= 0...) có một test ở đây.
"""
import csv
import io
import json
import os
import sys
import threading
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
sys.path.insert(0, HERE)
import dong_ho  # noqa: E402
from dong_ho import DongHo, DongHoLoi  # noqa: E402
from dh_fake import FakeGio, du_an, mat_mau, viet_nhan, viet_nhap  # noqa: E402
from m28core import goi_kq  # noqa: E402

DEAD_PID = 4194297                                       # gần như chắc chắn không có tiến trình nào


@pytest.fixture
def dh(tmp_path):
    root = du_an(tmp_path)
    g = FakeGio()
    return DongHo(root, gio=g, pid=os.getpid()), g, root


def doc_csv(root, nguoi='P5'):
    with open(os.path.join(root, 'outputs', 'timing', f'timing_{nguoi}.csv'), encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def chay_xong_3_mat(d, g, **kw):
    """Phiên 3 mặt: mặt 1 có tạm dừng 100 giây giữa chừng (15,04 giây tính giờ), mặt 2 = 20 giây, mặt 3 = 30 giây."""
    v = d.bat_dau('P5', 'assisted', dot='NAP_001', task='demo-NAP_001', n_mat=3, **kw)
    g.tick(10)
    v = d.tam_dung('P5', v['rev'])
    g.tick(100)
    v = d.tiep_tuc('P5', v['rev'])
    g.tick(5.04)
    v = d.xong_mat('P5', v['rev'])
    g.tick(20)
    v = d.xong_mat('P5', v['rev'], 'khó')
    g.tick(30)
    return d.xong_mat('P5', v['rev'])


# ---------- đúng giây, tạm dừng, cờ ----------
def test_pause_resume_done_seconds_rounding_interrupted_warmup_face_id(dh):
    d, g, root = dh
    v = chay_xong_3_mat(d, g)
    assert v['trang_thai'] == 'du_mat' and not v['chay'] and [m['giay'] for m in v['mat']] == [15.0, 20.0, 30.0]       # 15,04 làm tròn 0,1; trừ 100 giây tạm dừng
    assert [m['tam_dung'] for m in v['mat']] == [1, 0, 0] and v['giay_phien'] == pytest.approx(65.04)
    r = d.xong_luu('P5', v['rev'])
    assert r['ok'] and r['tom_tat']['n_mat'] == 3 and not os.path.exists(d.p_state('P5'))
    rows = doc_csv(root)
    assert [x['seconds'] for x in rows] == ['15.0', '20.0', '30.0']
    assert [x['warmup'] for x in rows] == ['1', '1', '0'] and [x['interrupted'] for x in rows] == ['1', '0', '0']        # seq 1, 2 là khởi động; chỉ mặt có tạm dừng bị gián đoạn
    assert [x['face_id'] for x in rows] == ['NAP_001_01', 'NAP_001_02', 'NAP_001_03'] and [x['seq'] for x in rows] == ['1', '2', '3']
    assert rows[1]['note'] == 'khó' and rows[0]['uoc_luong_chia_deu'] == '0' and rows[0]['nguon_ghi'] == 'dong_ho' and rows[0]['date'] == '2026-10-14'
    assert rows[0]['so_lan_tam_dung'] == '1' and float(rows[0]['giay_tam_dung']) == pytest.approx(100.0) and rows[0]['so_mat_phien'] == '3'


def test_warmup_when_starting_from_the_middle_of_a_block(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'manual', dot='NAP_001', n_mat=3, seq_dau=5)
    for _ in range(3):
        g.tick(12)
        v = d.xong_mat('P5', v['rev'])
    assert v['mat'][0]['face_id'] == 'NAP_001_05'
    d.xong_luu('P5', v['rev'])
    assert [x['warmup'] for x in doc_csv(root)] == ['1', '0', '0']                 # buổi bù: mặt đầu của phiên tự thành khởi động dù seq > 2


def test_session_only_gives_even_split_estimate_flagged(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'assisted', dot='NAP_001', task='demo-NAP_001', n_mat=4)
    g.tick(60)
    v = d.tam_dung('P5', v['rev'])
    g.tick(500)
    v = d.tiep_tuc('P5', v['rev'])
    g.tick(40)
    assert v['theo_mat'] is False
    r = d.xong_luu('P5', d.xem('P5')['rev'])
    rows = doc_csv(root)
    assert len(rows) == 4 and {x['seconds'] for x in rows} == {'25.0'} and {x['uoc_luong_chia_deu'] for x in rows} == {'1'}
    assert {x['warmup'] for x in rows} == {'0'} and {x['giay_phien'] for x in rows} == {'100.0'} and r['tom_tat']['uoc_luong'] is True
    assert r['tom_tat']['giay_moi_mat'] == 25.0 and rows[0]['note'] == 'ước lượng chia đều'
    nd, _w = goi_kq.doc_goi(os.path.join(root, r['goi']['zip']))
    assert nd['uoc_luong_chia_deu'] is True and nd['mat_do'] == [] and nd['giay_phien'] == 100.0 and nd['so_mat'] == 4 and nd['giay_tam_dung'] == 500.0


def test_all_faces_done_stops_clock_and_blocks_resume(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'manual', dot='X1', n_mat=2)
    for _ in range(2):
        g.tick(10)
        v = d.xong_mat('P5', v['rev'])
    assert v['trang_thai'] == 'du_mat' and v['du_mat']
    g.tick(500)
    assert d.xem('P5')['giay_phien'] == pytest.approx(20.0)                         # đồng hồ đã dừng
    with pytest.raises(DongHoLoi, match='Xong'):
        d.tiep_tuc('P5', v['rev'])
    with pytest.raises(DongHoLoi, match='Xong'):
        d.xong_mat('P5', v['rev'])
    with pytest.raises(DongHoLoi, match='Xong'):
        d.tam_dung('P5', v['rev'])


def test_face_under_two_seconds_is_rejected_not_silently_dropped(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'manual', dot='X1', n_mat=5)
    g.tick(1.5)
    with pytest.raises(DongHoLoi, match='quá nhanh'):
        d.xong_mat('P5', v['rev'])
    assert d.xem('P5')['mat'] == [] and d.xem('P5')['rev'] == v['rev']             # không đổi gì
    g.tick(1)
    assert d.xong_mat('P5', v['rev'])['mat'][0]['giay'] == 2.5


def test_xong_mat_refused_while_paused(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'manual', dot='X1', n_mat=5)
    g.tick(10)
    v = d.tam_dung('P5', v['rev'])
    with pytest.raises(DongHoLoi, match='Tiếp tục'):
        d.xong_mat('P5', v['rev'])
    with pytest.raises(DongHoLoi):
        d.tam_dung('P5', v['rev'])


def test_undo_merges_last_face_back(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'manual', dot='X1', n_mat=5)
    g.tick(10)
    v = d.xong_mat('P5', v['rev'])
    g.tick(5)
    v = d.tam_dung('P5', v['rev'])
    v = d.tiep_tuc('P5', v['rev'])
    g.tick(7)
    v = d.xong_mat('P5', v['rev'])
    assert [m['giay'] for m in v['mat']] == [10.0, 12.0]
    g.tick(4)
    v = d.hoan_tac_mat('P5', v['rev'])
    assert [m['giay'] for m in v['mat']] == [10.0] and v['seq'] == 2 and v['giay_mat'] == pytest.approx(16.0)       # 12 + 4 gộp lại thành mặt đang làm
    v = d.xong_mat('P5', v['rev'])
    assert v['mat'][1]['giay'] == 16.0 and v['mat'][1]['tam_dung'] == 1             # số lần tạm dừng cộng dồn
    d.hoan_tac_mat('P5', v['rev'])
    v = d.hoan_tac_mat('P5', d.xem('P5')['rev'])
    with pytest.raises(DongHoLoi, match='Chưa có mặt'):
        d.hoan_tac_mat('P5', v['rev'])


def test_undo_from_full_state_reopens_for_resume(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'manual', dot='X1', n_mat=1)
    g.tick(10)
    v = d.xong_mat('P5', v['rev'])
    assert v['trang_thai'] == 'du_mat'
    v = d.hoan_tac_mat('P5', v['rev'])
    assert v['trang_thai'] == 'tam_dung'
    v = d.tiep_tuc('P5', v['rev'])
    assert v['chay'] and v['mat'] == []


def test_unticking_current_face_is_the_q_key_of_facetimer(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'manual', dot='X1', n_mat=5)
    for _ in range(2):
        g.tick(12)
        v = d.xong_mat('P5', v['rev'])
    g.tick(30)
    r = d.xong_luu('P5', v['rev'], tinh_mat_dang_lam=False)
    assert [x['seconds'] for x in doc_csv(root)] == ['12.0', '12.0'] and any('không được tính' in t for t in r['thong_bao'])


def test_current_face_under_two_seconds_not_counted_and_said(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'manual', dot='X1', n_mat=5)
    g.tick(12)
    v = d.xong_mat('P5', v['rev'])
    g.tick(1)
    r = d.xong_luu('P5', v['rev'])
    assert len(doc_csv(root)) == 1 and any('dưới 2 giây' in t for t in r['thong_bao'])


# ---------- Hủy ----------
def test_cancel_writes_no_timing_row_and_logs_a_line(dh):
    d, g, root = dh
    v = d.bat_bau = None
    v = d.bat_dau('P5', 'manual', dot='X1', task='m28-manual', n_mat=5)
    g.tick(20)
    v = d.xong_mat('P5', v['rev'])
    open(d.p_csv('P5'), 'w', encoding='utf-8').write('')                          # file timing có sẵn không đổi từng byte
    before = open(d.p_csv('P5'), 'rb').read()
    y = d.huy_mo('P5')
    assert 'KHÔNG ghi dòng nào vào timing_P5.csv' in y['tom_tat'] and '1 mặt đã khép' in y['tom_tat'] and 'm28-manual' in y['tom_tat']
    row = d.huy_xac_nhan('P5', y['ma'], 'huỷ', ly_do='bấm nhầm')
    assert row['so_mat_bo'] == 1 and row['giay_bo'] == 20.0 and row['ly_do'] == 'bấm nhầm'
    assert open(d.p_csv('P5'), 'rb').read() == before and not os.path.exists(d.p_state('P5'))
    lines = open(d.p_huy('P5'), encoding='utf-8', newline='').read().split('\r\n')
    assert lines[0] == ','.join(dong_ho.HUY_COLS) and 'P5,manual,m28-manual' in lines[1]


@pytest.mark.parametrize('chu', ['HUY', 'huy', 'HỦY', 'HUỶ', ' hủy ', 'Huy'])
def test_cancel_accepts_all_spellings_of_huy(dh, chu):
    d, g, root = dh
    d.bat_dau('P5', 'manual', dot='X1', n_mat=5)
    y = d.huy_mo('P5')
    d.huy_xac_nhan('P5', y['ma'], chu)
    assert d.xem('P5')['co_phien'] is False


def test_cancel_wrong_text_old_or_expired_code_does_not_cancel(dh):
    d, g, root = dh
    d.bat_dau('P5', 'manual', dot='X1', n_mat=5)
    y1 = d.huy_mo('P5')
    for chu in ('', 'huỷ phiên', 'KHONG', 'HU'):
        with pytest.raises(DongHoLoi, match='HUY'):
            d.huy_xac_nhan('P5', y1['ma'], chu)
        y1 = d.huy_mo('P5')                                                          # mã dùng một lần: gõ sai thì phải mở lại
    y2 = d.huy_mo('P5')
    with pytest.raises(DongHoLoi, match='hết hiệu lực'):
        d.huy_xac_nhan('P5', y1['ma'], 'HUY')                                       # yêu cầu cũ bị thay bởi yêu cầu mới
    with pytest.raises(DongHoLoi, match='hết hiệu lực'):
        d.huy_xac_nhan('P5', 'ma-bia-dat', 'HUY')
    with pytest.raises(DongHoLoi, match='hết hiệu lực'):
        d.huy_xac_nhan('P5', None, 'HUY')
    assert d.xem('P5')['co_phien'] and not os.path.exists(d.p_huy('P5'))
    d._huy['P5'].clock = lambda: time.monotonic() + dot_anh_ttl() + 5               # quá hạn
    with pytest.raises(DongHoLoi, match='hết hiệu lực'):
        d.huy_xac_nhan('P5', y2['ma'], 'HUY')
    assert d.xem('P5')['co_phien']


def dot_anh_ttl():
    import dot_anh
    return dot_anh.TOKEN_TTL


# ---------- khôi phục, một phiên mỗi người, rev, khoá ----------
def test_state_restored_by_a_new_object_after_page_reload_and_server_restart(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'assisted', dot='NAP_001', n_mat=4)
    g.tick(7)
    v = d.xong_mat('P5', v['rev']) if False else v
    d2 = DongHo(root, gio=g, pid=os.getpid())                                       # tải lại trang = đọc file trạng thái
    g.tick(5)
    w = d2.xem('P5')
    assert w['co_phien'] and w['chay'] and w['giay_phien'] == pytest.approx(12.0) and w['rev'] == v['rev'] and w['dot'] == 'NAP_001' and w['n_mat'] == 4
    w = d2.tam_dung('P5', w['rev'])
    d3 = DongHo(root, gio=g, pid=os.getpid())
    g.tick(1000)
    assert d3.xem('P5')['trang_thai'] == 'tam_dung' and d3.xem('P5')['giay_phien'] == pytest.approx(12.0)


def test_one_session_per_person_and_dot_and_other_people_independent(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'assisted', dot='NAP_001', task='demo-NAP_001')
    with pytest.raises(DongHoLoi, match='đã có đồng hồ của đợt NAP_001'):
        d.bat_dau('P5', 'manual', dot='NAP_001', rev=0)                              # cùng đợt thì không bắt đầu lại (bấm Xong hoặc Hủy trước)
    d.bat_dau('P4', 'manual', dot='X3')
    assert d.xem('P4')['dieu_kien'] == 'manual' and d.xem('P5')['dieu_kien'] == 'assisted'
    d.tam_dung('P4', d.xem('P4')['rev'])
    assert d.xem('P5')['chay']                                                       # phiên người khác không ảnh hưởng


def test_stale_rev_is_rejected_and_nothing_changes(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'manual', dot='X1', n_mat=5)
    v1 = d.tam_dung('P5', v['rev'])
    with pytest.raises(DongHoLoi, match='tab khác') as e:
        d.tiep_tuc('P5', v['rev'])                                                   # tab cũ vẫn giữ rev trước khi tạm dừng
    assert e.value.cu and d.xem('P5')['trang_thai'] == 'tam_dung'
    with pytest.raises(DongHoLoi) as e2:
        d.bat_dau('P3', 'manual', dot='X1', rev=7)                                   # tab cũ nghĩ có phiên mà thực tế không có
    assert e2.value.cu
    with pytest.raises(DongHoLoi, match='chưa có phiên') as e3:
        d.tam_dung('P2', 0)
    assert e3.value.cu
    d.tiep_tuc('P5', v1['rev'])


def test_two_threads_pressing_done_write_exactly_once(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'manual', dot='X1', n_mat=3)
    g.tick(30)
    rev = d.xem('P5')['rev']
    d2 = DongHo(root, gio=g, pid=os.getpid())
    out, bar = [], threading.Barrier(2)

    def go(obj):
        bar.wait()
        try:
            out.append(obj.xong_luu('P5', rev))
        except DongHoLoi as e:
            out.append(e)
    ts = [threading.Thread(target=go, args=(o,)) for o in (d, d2)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sum(1 for o in out if isinstance(o, dict)) == 1 and sum(1 for o in out if isinstance(o, DongHoLoi)) == 1
    assert len(doc_csv(root)) == 3 and len(os.listdir(os.path.join(root, 'outputs', 'ket_qua'))) == 2


def test_orphan_lock_of_dead_pid_and_stale_lock_are_removed(dh):
    d, g, root = dh
    os.makedirs(d.dir, exist_ok=True)
    open(d.p_khoa('P5'), 'w').write(f'{DEAD_PID} {time.time():.0f}')
    d.bat_dau('P5', 'manual', dot='X1')
    assert not os.path.exists(d.p_khoa('P5'))
    open(d.p_khoa('P5'), 'w').write(f'{os.getpid()} {time.time() - 100:.0f}')       # còn sống nhưng cũ hơn 30 giây
    d.tam_dung('P5', d.xem('P5')['rev'])
    assert not os.path.exists(d.p_khoa('P5'))
    open(d.p_khoa('P5'), 'w').write(f'{os.getpid()} {time.time():.0f}')              # khoá còn mới của tiến trình sống: bận
    t0 = time.time()
    with pytest.raises(DongHoLoi, match='bận'):
        d.tiep_tuc('P5', d.xem('P5')['rev'])
    assert time.time() - t0 < 6
    os.remove(d.p_khoa('P5'))


def test_corrupt_state_file_does_not_crash_and_is_renamed_not_deleted(dh):
    d, g, root = dh
    os.makedirs(d.dir, exist_ok=True)
    for bad in ('{không phải json', '[]', json.dumps({'phien_ban': 1}), json.dumps({'phien_ban': 1, 'rev': 1, 'phien': 'x', 'nguoi': 'P5', 'dieu_kien': 'manual', 'trang_thai': 'chay',
                'doan': [{'a': 5, 'ea': 5, 'b': 1, 'eb': 1}], 'bat_dau': 'x', 'moc_mono': 0, 'n_mat': 1, 'cat_active': 0, 'so_lan_tam_dung': 0})):
        open(d.p_state('P5'), 'w', encoding='utf-8').write(bad)
        w = d.xem('P5')
        assert w['hong'] and not w['co_phien'] and 'Bỏ trạng thái hỏng' in w['loi']
        with pytest.raises(DongHoLoi) as e:
            d.tam_dung('P5')
        assert e.value.hong
        with pytest.raises(DongHoLoi) as e:
            d.bat_dau('P5', 'manual', dot='X1')                                      # có file hỏng cũng không bắt đầu đè lên
        assert e.value.hong
        ten = d.bo_trang_thai_hong('P5')
        assert ten.startswith('dang_chay_P5.hong-') and os.path.exists(os.path.join(d.dir, ten)) and not os.path.exists(d.p_state('P5'))
        assert d.xem('P5')['co_phien'] is False and not d.xem('P5')['hong']
    with pytest.raises(DongHoLoi, match='Không có file'):
        d.bo_trang_thai_hong('P5')


# ---------- máy khởi động lại, trang đã tắt, đóng trang ----------
def test_machine_reboot_uses_wall_clock_and_flags_khoi_dong_lai(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'manual', dot='X1', n_mat=2)
    g.tick(100)
    g.reboot(gap=600, new_mono=5.0)                                                  # monotonic cũ vô nghĩa, giờ thật trôi 600 giây
    d2 = DongHo(root, gio=g, pid=os.getpid())
    w = d2.xem('P5')
    assert w['giay_phien'] == pytest.approx(700.0) and 'khoi_dong_lai' in w['ma_canh_bao'] and any(c['ma'] == 'khoi_dong_lai' for c in w['canh_bao'])
    g.tick(30)
    assert d2.xem('P5')['giay_phien'] == pytest.approx(730.0)                         # sau đó vẫn chạy tiếp bình thường
    with pytest.raises(DongHoLoi, match='cảnh báo chưa xử lý') as e:
        d2.xong_luu('P5', d2.xem('P5')['rev'])
    assert e.value.cho
    r = d2.xong_luu('P5', d2.xem('P5')['rev'])                                       # bấm lần hai (không đổi gì ở giữa) thì lưu kèm cảnh báo
    assert 'khoi_dong_lai' in doc_csv(root)[0]['canh_bao'] and r['ok']


def test_dead_page_asks_to_subtract_the_gap_or_keep_it(dh):
    d1, g, root = dh
    d1 = DongHo(root, gio=g, pid=DEAD_PID)                                           # trang cũ (đã chết)
    v = d1.bat_dau('P5', 'manual', dot='X1', n_mat=2)
    g.tick(60)
    d1.nhip('P5')                                                                    # nhịp đồng bộ cuối: lan_cuoi_thay ở giây 60
    g.tick(1000)
    d2 = DongHo(root, gio=g, pid=os.getpid())
    w = d2.xem('P5')
    kt = [c for c in w['canh_bao'] if c['ma'] == 'khoang_tat']
    assert kt and set(kt[0]['hanh_dong']) == {'tru', 'giu'} and 'đồng hồ vẫn tính khoảng này' in kt[0]['text'] and w['giay_phien'] == pytest.approx(1060.0)
    w = d2.tru_khoang_tat('P5', w['rev'])
    assert w['trang_thai'] == 'tam_dung' and w['giay_phien'] == pytest.approx(60.0) and not [c for c in w['canh_bao'] if not c['xu_ly']]
    w = d2.tiep_tuc('P5', w['rev'])
    g.tick(10)
    assert d2.xem('P5')['giay_phien'] == pytest.approx(70.0)
    # nhánh "Giữ"
    d3 = DongHo(root, gio=g, pid=DEAD_PID)
    d3.huy_mo('P5')
    y = d3.huy_mo('P5')
    d3.huy_xac_nhan('P5', y['ma'], 'HUY')
    d3.bat_dau('P5', 'manual', dot='X2', n_mat=2)
    g.tick(500)
    d4 = DongHo(root, gio=g, pid=os.getpid())
    w = d4.xem('P5')
    w = d4.giu_canh_bao('P5', 'khoang_tat', w['rev'])
    assert w['giay_phien'] == pytest.approx(500.0) and 'khoang_tat' in w['ma_canh_bao'] and all(c['xu_ly'] for c in w['canh_bao'])


def test_page_alive_in_another_process_is_not_flagged(dh):
    d1, g, root = dh
    d1 = DongHo(root, gio=g, pid=os.getppid())                                       # tiến trình cha còn sống: giống trang thứ hai ở cổng khác
    d1.bat_dau('P5', 'manual', dot='X1')
    g.tick(1000)
    w = DongHo(root, gio=g, pid=os.getpid()).xem('P5')
    assert not [c for c in w['canh_bao'] if c['ma'] == 'khoang_tat']


def test_short_gap_between_heartbeats_is_not_flagged(dh):
    d1, g, root = dh
    d1 = DongHo(root, gio=g, pid=DEAD_PID)
    d1.bat_dau('P5', 'manual', dot='X1')
    g.tick(40)
    assert not [c for c in DongHo(root, gio=g, pid=os.getpid()).xem('P5')['canh_bao'] if c['ma'] == 'khoang_tat']


def test_closing_page_auto_pauses_running_sessions_only(dh):
    d, g, root = dh
    d.bat_dau('P5', 'manual', dot='X1')
    d.bat_dau('P4', 'assisted', dot='X2')
    d.tam_dung('P4', d.xem('P4')['rev'])
    g.tick(25)
    assert d.dang_chay_ai() == ['P5']
    got = d.tu_tam_dung_tat_ca()
    assert [n for n, _t, _d in got] == ['P5'] and got[0][1] == '18:30:25' and got[0][2] == 'X1'            # (người, giờ, đợt)
    w = d.xem('P5')
    assert w['trang_thai'] == 'tam_dung' and 'tat_trang' in w['ma_canh_bao'] and w['giay_phien'] == pytest.approx(25.0)
    g.tick(900)
    assert d.xem('P5')['giay_phien'] == pytest.approx(25.0) and d.dang_chay_ai() == []
    d.tiep_tuc('P5', w['rev'])
    g.tick(5)
    d.xong_luu('P5', d.xem('P5')['rev'], so_mat=2)
    assert 'tat_trang' in doc_csv(root)[0]['canh_bao']


def test_closing_flag_refuses_writes_but_not_the_auto_pause(dh):
    d, g, root = dh
    d.bat_dau('P5', 'manual', dot='X1')
    d.closing = True
    for fn in (lambda: d.bat_dau('P4', 'manual', dot='X1'), lambda: d.tam_dung('P5'), lambda: d.xong_mat('P5'), lambda: d.huy_mo('P5'),
               lambda: d.xong_luu('P5'), lambda: d.tiep_tuc('P5')):
        with pytest.raises(DongHoLoi, match='đang đóng'):
            fn()
    assert d.tu_tam_dung_tat_ca() and d.xem('P5')['trang_thai'] == 'tam_dung'


# ---------- quên bấm ----------
def test_forgotten_clock_warns_after_20_minutes_per_face_and_150_minutes_per_session(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'manual', dot='X1', n_mat=5)
    g.tick(60 * 149)
    assert not d.xem('P5')['canh_bao']                                                # mới 149 phút, chưa bấm từng mặt
    g.tick(120)
    w = d.xem('P5')
    assert [c['ma'] for c in w['canh_bao']] == ['phien_lau'] and set(w['canh_bao'][0]['hanh_dong']) == {'sua', 'giu'}
    d.huy_mo('P5')
    d.huy_xac_nhan('P5', d.huy_mo('P5')['ma'], 'HUY')
    v = d.bat_dau('P5', 'manual', dot='X1', n_mat=5)
    g.tick(30)
    v = d.xong_mat('P5', v['rev'])
    g.tick(19 * 60)
    assert not [c for c in d.xem('P5')['canh_bao'] if c['ma'] == 'mat_lau']
    g.tick(120)
    w = d.xem('P5')
    assert any(c['ma'] == 'mat_lau' and 'Xong mặt' in c['text'] for c in w['canh_bao'])
    w = d.xong_mat('P5', w['rev'])                                                    # bấm Xong mặt thì cảnh báo mặt lâu hết (mặt mới)
    assert not [c for c in w['canh_bao'] if c['ma'] == 'mat_lau']


def test_session_over_midnight_is_flagged_and_keep_records_it(tmp_path):
    root = du_an(tmp_path)
    g = FakeGio('2026-10-14T23:55:00+07:00')
    d = DongHo(root, gio=g, pid=os.getpid())
    d.bat_dau('P5', 'manual', dot='X1', n_mat=2)
    g.tick(120)
    assert not d.xem('P5')['canh_bao']
    g.tick(600)                                                                       # 00:07 ngày 15
    w = d.xem('P5')
    assert [c['ma'] for c in w['canh_bao']] == ['qua_dem']
    with pytest.raises(DongHoLoi, match='cảnh báo chưa xử lý'):
        d.xong_luu('P5', w['rev'])
    w = d.giu_canh_bao('P5', 'qua_dem', w['rev'])
    assert all(c['xu_ly'] for c in w['canh_bao'])
    r = d.xong_luu('P5', w['rev'])                                                    # đã chọn Giữ nguyên thì lưu ngay, không cần bấm hai lần
    rows = doc_csv(root)
    assert 'qua_dem' in rows[0]['canh_bao'] and rows[0]['date'] == '2026-10-15' and r['ok']


def test_fix_time_within_limits_sets_sua_tay_and_keeps_original_in_note(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'manual', dot='X1', n_mat=3)
    g.tick(1800)                                                                       # quên bấm: đo được 30 phút
    w = d.xem('P5')
    assert [c['ma'] for c in w['canh_bao']] == []
    g.tick(60 * 125)
    w = d.xem('P5')
    assert [c['ma'] for c in w['canh_bao']] == ['phien_lau']
    for bad, why in (('2:36:00', 'không được lớn hơn'), ('0:01', '2 giây'), ('abc', 'mm:ss'), ('', 'mm:ss')):
        with pytest.raises(DongHoLoi, match=why):
            d.sua_thoi_gian('P5', bad, w['rev'])
    w = d.sua_thoi_gian('P5', '45:00', w['rev'])                                      # đúng giờ thật là 45 phút
    assert w['giay_hien_thi'] == pytest.approx(2700.0) and w['sua_tay'] == 1 and not [c for c in w['canh_bao'] if not c['xu_ly']]
    r = d.xong_luu('P5', w['rev'])
    rows = doc_csv(root)
    assert len(rows) == 3 and {x['sua_tay'] for x in rows} == {'1'} and {x['seconds'] for x in rows} == {'900.0'} and 'đo gốc 9300.0 giây' in rows[0]['note']
    assert r['tom_tat']['giay_tong'] == 2700.0


def test_fix_time_applies_to_the_current_face_when_clicking_faces(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'manual', dot='X1', n_mat=3)
    g.tick(40)
    v = d.xong_mat('P5', v['rev'])
    g.tick(25 * 60)
    w = d.xem('P5')
    assert any(c['ma'] == 'mat_lau' for c in w['canh_bao'])
    w = d.sua_thoi_gian('P5', '01:30', w['rev'])
    assert w['giay_mat'] == pytest.approx(90.0) and w['giay_phien'] == pytest.approx(130.0)
    w = d.xong_mat('P5', w['rev'])
    assert w['mat'][1]['giay'] == 90.0 and w['mat'][1]['sua_tay'] == 1 and w['mat'][0]['sua_tay'] == 0
    w = d.hoan_tac_mat('P5', w['rev'])                                                 # hoàn tác trả lại phần đã trừ để sửa tiếp
    assert w['giay_mat'] == pytest.approx(90.0)


def test_done_with_pending_warning_needs_second_press_and_keep_choice(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'manual', dot='X1', n_mat=2)
    g.tick(60 * 160)
    w = d.xem('P5')
    with pytest.raises(DongHoLoi) as e:
        d.xong_luu('P5', w['rev'])
    assert e.value.cho and not doc_csv_exists(root)
    r = d.xong_luu('P5', w['rev'])
    assert r['ok'] and doc_csv(root)
    d.bat_dau('P5', 'manual', dot='X1', n_mat=2, seq_dau=10)
    g.tick(60 * 160)
    w = d.xem('P5')
    with pytest.raises(DongHoLoi):
        d.xong_luu('P5', w['rev'])
    w = d.giu_canh_bao('P5', 'phien_lau', w['rev'])
    d.xong_luu('P5', w['rev'])                                                         # sau khi đổi thì phải bấm lại từ đầu: lần đầu sau Giữ nguyên là lưu luôn
    assert 'phien_lau' in doc_csv(root)[-1]['canh_bao']


def doc_csv_exists(root):
    return os.path.exists(os.path.join(root, 'outputs', 'timing', 'timing_P5.csv'))


# ---------- không bao giờ ghi giây <= 0 ----------
def test_seconds_never_zero_or_negative_are_ever_written(dh):
    d, g, root = dh
    d.bat_dau('P5', 'manual', dot='X1', n_mat=5000)
    g.tick(3)
    with pytest.raises(DongHoLoi, match='quá ngắn'):
        d.xong_luu('P5', d.xem('P5')['rev'])
    assert not doc_csv_exists(root) and d.xem('P5')['co_phien']
    with pytest.raises(DongHoLoi, match='Phiên rỗng'):
        d2 = DongHo(root, gio=FakeGio(), pid=os.getpid())
        d2.bat_dau('P4', 'manual', dot='X1', n_mat=2)
        d2.xong_luu('P4', d2.xem('P4')['rev'])                                        # chưa quá 2 giây
    assert not os.path.exists(os.path.join(root, 'outputs', 'timing', 'timing_P4.csv'))
    d.huy_xac_nhan('P5', d.huy_mo('P5')['ma'], 'HUY')
    d.bat_dau('P5', 'manual', dot='X1', n_mat=2)
    g.tick(100)
    g.e -= 5000                                                                        # giờ hệ thống lùi mạnh (đồng hồ chỉnh tay)
    assert d.xem('P5')['giay_phien'] == pytest.approx(100.0)                           # đồng hồ monotonic không bị ảnh hưởng
    d.xong_luu('P5', d.xem('P5')['rev'])
    assert all(float(x['seconds']) > 0 for x in doc_csv(root))


def test_reboot_with_wall_clock_going_backwards_never_writes_negative(dh):
    d, g, root = dh
    d.bat_dau('P5', 'manual', dot='X1', n_mat=2)
    g.tick(10)
    g.reboot(gap=-3600, new_mono=5.0)                                                  # giờ thật lùi 1 giờ sau khởi động lại
    w = DongHo(root, gio=g, pid=os.getpid()).xem('P5')
    assert w['giay_phien'] >= 0 and 'khoi_dong_lai' in w['ma_canh_bao']
    with pytest.raises(DongHoLoi):
        DongHo(root, gio=g, pid=os.getpid()).xong_luu('P5', w['rev'], tinh_mat_dang_lam=True)    # còn cảnh báo chưa xử lý hoặc phiên rỗng
    rows_before = doc_csv_exists(root)
    assert not rows_before


# ---------- ô nhập ----------
def test_bad_person_names_and_bad_inputs_are_refused(dh):
    d, g, root = dh
    for nguoi in ('', 'P5 ', '../P5', 'a b', 'x' * 33, None):
        with pytest.raises(DongHoLoi, match='chữ không dấu, số'):
            d.bat_dau(nguoi, 'manual', dot='X1')
    assert d.bat_dau('Lam-Tran-2', 'manual', dot='X9')['co_phien'] and d.cac_nguoi() == ['Lam-Tran-2']     # tên bất kỳ (chữ, số, _, -) chạy được; không còn P1–P5
    for kw, why in ((dict(dieu_kien='lạ'), 'manual'), (dict(dot='a/b'), 'Tên đợt'), (dict(task='a b'), 'task'), (dict(job='12a'), 'Job'), (dict(khoi='a b'), 'Khối'),
                    (dict(n_mat=0), 'Số mặt'), (dict(n_mat=999999), 'Số mặt'), (dict(n_mat='x'), 'số nguyên'), (dict(seq_dau=0), 'từ 1'), (dict(seq_dau='x'), 'số nguyên')):
        a = dict(dieu_kien='manual', dot='X1', n_mat=3)
        a.update(kw)
        with pytest.raises(DongHoLoi, match=why):
            d.bat_dau('P5', **a)
    assert not d.xem('P5')['co_phien']


def test_task_and_condition_mismatch_refused(dh):
    d, g, root = dh
    with pytest.raises(DongHoLoi, match='m28-manual đi với điều kiện manual'):
        d.bat_dau('P5', 'assisted', task='m28-manual', dot='X1')
    with pytest.raises(DongHoLoi, match='m28-assisted đi với điều kiện assisted'):
        d.bat_dau('P5', 'manual', task='m28-assisted', dot='X1')
    d.bat_dau('P5', 'manual', task='m28-manual', dot='X1', job='123')
    assert d.xem('P5')['job'] == '123'


def test_group_from_config_warns_when_different_or_missing(dh):
    d, g, root = dh
    d.bat_dau('P5', 'manual', dot='X1')
    assert 'chua_co_nhom' in d.xem('P5')['ma_canh_bao']
    d.huy_xac_nhan('P5', d.huy_mo('P5')['ma'], 'HUY')
    json.dump({'nhom': {'P5': 'assisted', 'P4': 'manual'}, 'bo_anh': 'NAP_001'}, open(os.path.join(root, 'config', 'nhom_thi_nghiem.json'), 'w'))
    d.bat_dau('P5', 'manual', dot='X1')
    w = d.xem('P5')
    assert 'lech_nhom' in w['ma_canh_bao'] and w['bo_anh'] == 'NAP_001'               # lệch nhóm chỉ cảnh báo, không chặn
    d.bat_dau('P4', 'manual', dot='X1')
    assert d.xem('P4')['ma_canh_bao'] == []


def test_duplicate_seq_needs_second_press_and_is_flagged(dh):
    d, g, root = dh
    d.bat_dau('P5', 'manual', dot='X1', n_mat=2)
    g.tick(20)
    d.xong_luu('P5', d.xem('P5')['rev'])
    assert d.seq_goi_y('P5', 'demo-X1', 'X1') == 3                                    # buổi bù: seq tiếp theo
    with pytest.raises(DongHoLoi, match='TRÙNG') as e:
        d.bat_dau('P5', 'manual', dot='X1', n_mat=2, seq_dau=1)
    assert e.value.cho and not d.xem('P5')['co_phien']
    d.bat_dau('P5', 'manual', dot='X1', n_mat=2, seq_dau=1)
    assert 'trung_seq' in d.xem('P5')['ma_canh_bao']
    d.huy_xac_nhan('P5', d.huy_mo('P5')['ma'], 'HUY')
    v = d.bat_dau('P5', 'manual', dot='X1', n_mat=2)                                  # không nêu seq: tự điền, không trùng
    assert v['seq'] == 3 and 'trung_seq' not in v['ma_canh_bao']


# ---------- file CSV ----------
def test_csv_first_12_columns_are_facetimer_utf8_no_bom_crlf_vietnamese(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'assisted', dot='NAP_001', task='demo-NAP_001', n_mat=2, ghi_chu='ảnh ban đêm, tối')
    g.tick(12.34)
    v = d.xong_mat('P5', v['rev'], 'khó, mờ "một chút"')
    g.tick(8)
    d.xong_luu('P5', v['rev'])
    raw = open(os.path.join(root, 'outputs', 'timing', 'timing_P5.csv'), 'rb').read()
    assert not raw.startswith(b'\xef\xbb\xbf') and raw.startswith(b'date,person,condition,task,job,block,seq,face_id,seconds,warmup,interrupted,note,phien,')
    assert raw.count(b'\r\n') == 3 and b'\n' not in raw.replace(b'\r\n', b'')
    head = raw.decode('utf-8').split('\r\n')[0].split(',')
    assert head[:12] == dong_ho.FACETIMER_COLS and head[12:] == dong_ho.EXTRA_COLS
    rows = doc_csv(root)
    assert rows[0]['note'] == 'khó, mờ "một chút"' and rows[0]['ghi_chu_phien'] == 'ảnh ban đêm, tối'
    assert rows[0]['condition'] == 'assisted' and rows[0]['person'] == 'P5' and rows[0]['task'] == 'demo-NAP_001' and rows[0]['block'] == 'NAP_001'


def test_formula_safe_notes(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'manual', dot='X1', n_mat=1, ghi_chu='=HYPERLINK("x")')
    g.tick(10)
    v = d.xong_mat('P5', v['rev'], '+cmd|calc')
    d.xong_luu('P5', v['rev'])
    r = doc_csv(root)[0]
    assert r['note'] == "'+cmd|calc" and r['ghi_chu_phien'] == "'=HYPERLINK(\"x\")"


def test_existing_facetimer_file_is_upgraded_with_backup_old_rows_kept(dh):
    d, g, root = dh
    os.makedirs(d.dir, exist_ok=True)
    old = 'date,person,condition,task,job,block,seq,face_id,seconds,warmup,interrupted,note\r\n2026-10-09,P5,manual,m28-manual,123,X5,1,X5_01,41.0,1,0,\r\n'
    open(d.p_csv('P5'), 'w', encoding='utf-8', newline='').write(old)
    d.bat_dau('P5', 'manual', task='m28-manual', dot='X5', n_mat=2, seq_dau=2)
    g.tick(20)
    d.xong_luu('P5', d.xem('P5')['rev'])
    baks = [f for f in os.listdir(d.dir) if f.startswith('timing_P5.csv.bak-')]
    assert len(baks) == 1 and open(os.path.join(d.dir, baks[0]), encoding='utf-8', newline='').read() == old
    rows = doc_csv(root)
    assert len(rows) == 3 and rows[0]['seconds'] == '41.0' and rows[0]['phien'] == '' and rows[0]['uoc_luong_chia_deu'] == '' and rows[1]['nguon_ghi'] == 'dong_ho'


def test_existing_full_header_appends_and_foreign_header_is_refused_untouched(dh):
    d, g, root = dh
    for i in range(2):
        d.bat_dau('P5', 'manual', dot=f'X{i}', n_mat=2)
        g.tick(20)
        d.xong_luu('P5', d.xem('P5')['rev'])
    assert len(doc_csv(root)) == 4 and not [f for f in os.listdir(d.dir) if '.bak-' in f]
    foreign = 'ngay,nguoi,giay\r\n2026-10-01,P5,3\r\n'
    open(d.p_csv('P5'), 'w', encoding='utf-8', newline='').write(foreign)
    d.bat_dau('P5', 'manual', dot='X9', n_mat=2)
    g.tick(20)
    with pytest.raises(DongHoLoi, match='tiêu đề lạ') as e:
        d.xong_luu('P5', d.xem('P5')['rev'])
    assert 'cột lạ: ngay, nguoi, giay' in str(e.value) and 'thiếu cột: date' in str(e.value)
    assert open(d.p_csv('P5'), encoding='utf-8', newline='').read() == foreign and d.xem('P5')['co_phien']          # giữ nguyên file và trạng thái


def test_replace_failure_keeps_old_csv_and_state_and_retry_works(dh, monkeypatch):
    d, g, root = dh
    d.bat_dau('P5', 'manual', dot='X1', n_mat=2)
    g.tick(20)
    d.xong_luu('P5', d.xem('P5')['rev'])
    before = open(d.p_csv('P5'), 'rb').read()
    d.bat_dau('P5', 'manual', dot='X1', n_mat=2, seq_dau=3)
    g.tick(20)
    real = os.replace

    def boom(a, b):
        if str(b).endswith('timing_P5.csv'):
            raise PermissionError('file đang mở')
        return real(a, b)
    monkeypatch.setattr(os, 'replace', boom)
    with pytest.raises(DongHoLoi, match='Không ghi được'):
        d.xong_luu('P5', d.xem('P5')['rev'])
    assert open(d.p_csv('P5'), 'rb').read() == before and d.xem('P5')['co_phien']
    assert not [f for f in os.listdir(d.dir) if '.tmp' in f]
    monkeypatch.setattr(os, 'replace', real)
    d.xong_luu('P5', d.xem('P5')['rev'])
    assert len(doc_csv(root)) == 4 and not d.xem('P5')['co_phien']
    assert len([f for f in os.listdir(os.path.join(root, 'outputs', 'ket_qua')) if f.endswith('.zip')]) == 2          # ghi lại gói của đúng phiên đó, không nhân đôi


def test_recent_sessions_listing(dh):
    d, g, root = dh
    for i in range(3):
        d.bat_dau('P5', 'manual', dot=f'X{i}', n_mat=4)
        g.tick(40 + i * 40)
        d.xong_luu('P5', d.xem('P5')['rev'])
        g.tick(86400)
    ls = d.gan_day('P5', 5)
    assert [x['khoi'] for x in ls] == ['X2', 'X1', 'X0'] and ls[0]['n_mat'] == 4 and ls[0]['giay_tong'] == 120.0 and ls[0]['giay_moi_mat'] == 30.0 and ls[0]['uoc_luong']
    assert len(d.gan_day('P5', 2)) == 2 and d.gan_day('P1') == []


# ---------- gói kết quả ----------
def test_done_writes_clean_package_with_labels_and_draft(dh):
    d, g, root = dh
    anh = {f'F_{i:03d}.png': mat_mau(i) for i in range(1, 4)}
    nhan = {k: {n: (x + (6.0 if n.endswith('_3') else 0.2), y) for n, (x, y) in v.items()} for k, v in anh.items()}        # sửa các điểm *_3 rõ rệt, còn lại 0,2 px
    viet_nhap(root, 'NAP_001', anh)
    viet_nhan(root, 'demo-NAP_001', 'P5', '1410', nhan, thieu={'F_002.png': ['songmui_2']})
    viet_nhan(root, 'demo-NAP_001', 'P4', '1410', {'khac.png': mat_mau(9)})
    v = d.bat_dau('P5', 'assisted', dot='NAP_001', task='demo-NAP_001', n_mat=3, bo_anh='NAP_001', ghi_chu='ghi chú không có đường dẫn')
    g.tick(90)
    r = d.xong_luu('P5', v['rev'])
    assert r['goi']['zip'].endswith('ketqua_P5_1410_NAP_001.zip') and r['goi']['json'].endswith('ketqua_P5_1410_NAP_001.json')
    nd, _w = goi_kq.doc_goi(os.path.join(root, r['goi']['zip']))
    assert nd['nguoi'] == 'P5' and nd['nhom'] == 'assisted' and nd['dot'] == 'NAP_001' and nd['bo_anh'] == 'NAP_001' and nd['so_mat'] == 3 and nd['giay_phien'] == 90.0
    assert nd['co_nhan'] and nd['co_nhap'] and nd['nhan_file'] == 'demo-NAP_001_P5_1410.xml' and [k['anh'] for k in nd['ket_qua']] == ['F_001', 'F_002', 'F_003']
    f2 = nd['ket_qua'][1]
    assert 'songmui_2' not in f2['nhan_cuoi'] and 'songmui_2' in f2['nhap'] and 'songmui_2' in f2['diem_da_sua']      # điểm bị xoá/ẩn tính là đã sửa
    assert all(n.endswith('_3') for n in nd['ket_qua'][0]['diem_da_sua']) and len(nd['ket_qua'][0]['diem_da_sua']) == 7        # mỗi trong 7 nhóm có một điểm *_3
    assert nd['ket_qua'][0]['nme_nhap_so_nhan_cuoi'] > 0
    text = open(os.path.join(root, r['goi']['json']), encoding='utf-8').read()
    assert root not in text and '/tmp' not in text and '@' not in text and 'token' not in text.lower()


def test_package_without_labels_has_time_only_and_a_hint_then_reexport_after_collect(dh):
    d, g, root = dh
    v = d.bat_dau('P5', 'assisted', dot='NAP_001', task='demo-NAP_001', n_mat=2)
    g.tick(60)
    r = d.xong_luu('P5', v['rev'])
    assert any('Merge jobs & Finish' in t for t in r['thong_bao'])
    nd, _w = goi_kq.doc_goi(os.path.join(root, r['goi']['zip']))
    assert nd['ket_qua'] == [] and nd['co_nhan'] is False
    ls = d.goi_da_luu('P5')
    assert [t for t, _n in ls] == ['ketqua_P5_1410_NAP_001']
    with pytest.raises(DongHoLoi, match='chưa có file nhãn'):
        d.xuat_lai_goi('P5', 'ketqua_P5_1410_NAP_001')
    anh = {f'F_{i:03d}.png': mat_mau(i) for i in range(1, 3)}
    viet_nhap(root, 'NAP_001', anh)
    viet_nhan(root, 'demo-NAP_001', 'P5', '1410', anh)
    d.xuat_lai_goi('P5', 'ketqua_P5_1410_NAP_001')
    nd2, _w = goi_kq.doc_goi(os.path.join(root, r['goi']['zip']))
    assert nd2['phien'] == nd['phien'] and nd2['giay_phien'] == nd['giay_phien'] and nd2['co_nhan'] and len(nd2['ket_qua']) == 2           # cùng phiên, cùng số đo
    assert len(os.listdir(os.path.join(root, 'outputs', 'ket_qua'))) == 2
    assert len(doc_csv(root)) == 2                                                    # xuất lại gói không đụng timing_<người>.csv


def test_second_session_same_day_same_batch_gets_a_new_package_name(dh):
    d, g, root = dh
    for i in range(2):
        d.bat_dau('P5', 'manual', dot='NAP_001', n_mat=2, seq_dau=1 + 2 * i)
        g.tick(30)
        d.xong_luu('P5', d.xem('P5')['rev'])
    assert sorted(os.listdir(os.path.join(root, 'outputs', 'ket_qua'))) == ['ketqua_P5_1410_NAP_001-2.json', 'ketqua_P5_1410_NAP_001-2.zip',
                                                                           'ketqua_P5_1410_NAP_001.json', 'ketqua_P5_1410_NAP_001.zip']


def test_note_with_path_or_email_blocks_the_package_before_any_write(dh):
    d, g, root = dh
    d.bat_dau('P5', 'manual', dot='X1', n_mat=2, ghi_chu='xem /home/ten/anh.png')
    g.tick(30)
    with pytest.raises(DongHoLoi, match='đường dẫn tuyệt đối'):
        d.xong_luu('P5', d.xem('P5')['rev'])
    assert not doc_csv_exists(root) and d.xem('P5')['co_phien'] and not os.path.isdir(os.path.join(root, 'outputs', 'ket_qua'))
    d.xong_luu('P5', d.xem('P5')['rev'], ghi_chu_phien='đã bỏ đường dẫn')
    assert doc_csv(root)[0]['ghi_chu_phien'] == 'đã bỏ đường dẫn'


# ---------- tương thích P5 / thống kê cũ ----------
def test_timing_csv_is_readable_by_pandas_with_a_facetimer_file_and_by_the_old_reader(dh):
    pd = pytest.importorskip('pandas')
    d, g, root = dh
    v = d.bat_dau('P5', 'manual', task='m28-manual', dot='X5', job='9', n_mat=3)
    for _ in range(3):
        g.tick(30)
        v = d.xong_mat('P5', v['rev'])
    d.xong_luu('P5', v['rev'])
    fac = os.path.join(root, 'timing_P4.csv')
    open(fac, 'w', encoding='utf-8', newline='').write('date,person,condition,task,job,block,seq,face_id,seconds,warmup,interrupted,note\r\n'
                                                       '2026-10-14,P4,assisted,m28-assisted,5,X5,1,X5_01,20.5,1,0,\r\n2026-10-14,P4,assisted,m28-assisted,5,X5,3,X5_03,22.5,0,0,\r\n')
    dd = pd.concat(pd.read_csv(f) for f in (fac, d.p_csv('P5')))
    t = dd[dd.warmup == 0]
    x = t[t.task.isin(['m28-manual', 'm28-assisted'])]
    assert sorted(x.person.unique()) == ['P4', 'P5'] and list(x.groupby('condition').seconds.mean().round(1)) == [22.5, 30.0]
    from m28core import toc_do
    rows = toc_do.doc_file(d.p_csv('P5'))
    assert [r['seconds'] for r in rows] == [30.0, 30.0, 30.0] and rows[0]['person'] == 'P5' and rows[0]['condition'] == 'manual'


def test_fmt_and_parse_helpers():
    assert dong_ho.fmt_giay(0) == '00:00' and dong_ho.fmt_giay(65) == '01:05' and dong_ho.fmt_giay(3600) == '1:00:00' and dong_ho.fmt_giay(3725.4) == '1:02:05'
    assert dong_ho.doc_mm_ss('12:30') == 750 and dong_ho.doc_mm_ss('1:02:03') == 3723 and dong_ho.doc_mm_ss('90') == 90 and dong_ho.doc_mm_ss('1,5') == 1.5
    assert dong_ho.doc_mm_ss('') is None and dong_ho.doc_mm_ss('a:b') is None and dong_ho.doc_mm_ss('-5') is None and dong_ho.doc_mm_ss('1:2:3:4') is None
    assert dong_ho.khong_dau_hoa('Hủy') == 'HUY' and dong_ho.khong_dau_hoa('huỷ') == 'HUY'


def test_module_imports_no_gradio_or_numpy_at_top():
    src = open(os.path.join(HERE, '..', 'tool', 'dong_ho.py'), encoding='utf-8').read()
    head = src.split('class DongHoLoi')[0]
    assert 'import gradio' not in src and 'import numpy' not in head and 'import torch' not in src


# ---------- MỖI ĐỢT MỘT ĐỒNG HỒ (QĐ-007): giờ đợt này không lẫn vào đợt khác ----------
def test_each_dot_keeps_its_own_seconds_and_only_one_clock_runs(dh):
    """Ca thật: nạp đợt A, làm một lúc, nạp tiếp đợt B. Trước đây giờ của B bị cộng vào phiên của A (chip vẫn ghi đợt A)."""
    d, g, root = dh
    d.bat_dau('P5', 'assisted', dot='A', n_mat=3)
    g.tick(60)
    d.bat_dau('P5', 'assisted', dot='B', n_mat=2)                                     # nạp đợt B: A tự tạm dừng, giữ nguyên 60 giây
    a, b = d.xem('P5', 'A'), d.xem('P5', 'B')
    assert a['trang_thai'] == 'tam_dung' and a['giay_phien'] == pytest.approx(60.0) and b['chay'] and b['giay_phien'] == 0
    g.tick(25)
    a, b = d.xem('P5', 'A'), d.xem('P5', 'B')
    assert a['giay_phien'] == pytest.approx(60.0) and b['giay_phien'] == pytest.approx(25.0)           # giờ không lẫn
    assert [s['dot'] for s in d.liet_ke('P5')] == ['A', 'B'] and d.dang_chay_ai() == ['P5']
    assert [c['dot'] for c in b['cac_dot']] == ['A'] and b['cac_dot'][0]['giay_phien'] == pytest.approx(60.0)       # chip ghi mờ đợt khác
    d.tiep_tuc('P5', a['rev'], dot='A')                                              # chạy tiếp A thì B tự tạm dừng
    g.tick(10)
    a, b = d.xem('P5', 'A'), d.xem('P5', 'B')
    assert a['chay'] and a['giay_phien'] == pytest.approx(70.0) and b['trang_thai'] == 'tam_dung' and b['giay_phien'] == pytest.approx(25.0)
    assert sum(1 for s in d.liet_ke('P5') if s['chay']) == 1


def test_calls_without_a_dot_need_exactly_one_session(dh):
    d, g, root = dh
    d.bat_dau('P5', 'manual', dot='A')
    d.tam_dung('P5')                                                                 # một phiên: không cần nêu đợt
    d.bat_dau('P5', 'manual', dot='B')
    for fn in (lambda: d.tam_dung('P5'), lambda: d.tiep_tuc('P5'), lambda: d.huy_mo('P5'), lambda: d.xong_luu('P5')):
        with pytest.raises(DongHoLoi, match='chỉ rõ đợt'):
            fn()
    with pytest.raises(DongHoLoi, match='chưa có đồng hồ cho đợt Z'):
        d.tam_dung('P5', dot='Z')
    assert d.xem('P5', 'Z')['co_phien'] is False and len(d.xem('P5', 'Z')['cac_dot']) == 2


def test_view_follows_running_then_page_dot_and_never_borrows_another_dot(dh):
    d, g, root = dh
    d.bat_dau('P5', 'assisted', dot='A')
    d.bat_dau('P5', 'assisted', dot='B')                                              # B chạy, A tạm dừng
    assert d.chon_dot('P5', 'A') == 'B' and d.chon_dot('P5', None) == 'B'              # đang chạy luôn thắng
    d.tam_dung('P5', d.xem('P5', 'B')['rev'], dot='B')
    assert d.chon_dot('P5', 'A') == 'A' and d.chon_dot('P5', 'B') == 'B'               # không chạy: theo đợt của trang
    assert d.chon_dot('P5', 'C') is None                                              # trang ở đợt C chưa có đồng hồ: KHÔNG mượn A hoặc B
    v = d.xem_theo_trang('P5', 'C')
    assert v['co_phien'] is False and sorted(c['dot'] for c in v['cac_dot']) == ['A', 'B']
    assert d.chon_dot('P5', None) in ('A', 'B') and d.chon_dot('P4', 'A') is None


def test_waiting_dot_does_not_count_time_and_starts_from_zero_when_resumed(dh):
    """Upload & Continue lúc đang có đồng hồ ở đợt khác: đợt mới chờ ở 00:00, đồng hồ cũ không bị đụng tới."""
    d, g, root = dh
    d.bat_dau('P5', 'assisted', dot='A')
    g.tick(30)
    d.bat_dau('P5', 'assisted', dot='B', cho=True)
    a, b = d.xem('P5', 'A'), d.xem('P5', 'B')
    assert a['chay'] and a['giay_phien'] == pytest.approx(30.0) and b['cho'] and b['trang_thai'] == 'tam_dung' and b['giay_phien'] == 0
    g.tick(500)
    b = d.xem('P5', 'B')
    assert b['giay_phien'] == 0 and b['giay_tam_dung'] == 0 and d.xem('P5', 'A')['chay']                 # chờ không phải tạm dừng, không tính giờ
    d.tiep_tuc('P5', b['rev'], dot='B')                                              # chạy lần đầu: A tạm dừng, giờ bắt đầu thật là lúc này
    g.tick(12)
    a, b = d.xem('P5', 'A'), d.xem('P5', 'B')
    assert b['chay'] and not b['cho'] and b['giay_phien'] == pytest.approx(12.0) and b['bat_dau'] > '2026-10-14T18:30:00+07:00'
    assert a['trang_thai'] == 'tam_dung' and a['giay_phien'] == pytest.approx(530.0)                  # A chạy suốt lúc B chờ (30 + 500 giây), tạm dừng đúng lúc B chạy


def test_save_one_dot_keeps_the_other_and_each_dot_gets_its_own_rows_and_package(dh):
    d, g, root = dh
    d.bat_dau('P5', 'assisted', dot='A', n_mat=2)
    g.tick(40)
    d.bat_dau('P5', 'assisted', dot='B', n_mat=3)
    g.tick(90)
    ra = d.xong_luu('P5', d.xem('P5', 'A')['rev'], dot='A')
    assert ra['ok'] and ra['tom_tat']['dot'] == 'A' and d.xem('P5', 'A')['co_phien'] is False
    assert d.xem('P5', 'B')['chay'] and d.xem('P5', 'B')['giay_phien'] == pytest.approx(90.0)        # B giữ nguyên, vẫn chạy
    rows = doc_csv(root)
    assert len(rows) == 2 and {r['dot'] for r in rows} == {'A'} and {r['seconds'] for r in rows} == {'20.0'} and {r['giay_phien'] for r in rows} == {'40.0'}
    g.tick(10)
    rb = d.xong_luu('P5', d.xem('P5', 'B')['rev'], dot='B')
    rows = doc_csv(root)
    assert len(rows) == 5 and [r['dot'] for r in rows] == ['A', 'A', 'B', 'B', 'B'] and {r['seconds'] for r in rows if r['dot'] == 'B'} == {'33.3'}
    assert len({r['phien'] for r in rows}) == 2 and {r['task'] for r in rows} == {'demo-A', 'demo-B'}
    pa, _w = goi_kq.doc_goi(os.path.join(root, ra['goi']['zip']))
    pb, _w = goi_kq.doc_goi(os.path.join(root, rb['goi']['zip']))
    assert ra['goi']['ten'] == 'ketqua_P5_1410_A' and rb['goi']['ten'] == 'ketqua_P5_1410_B'
    assert (pa['dot'], pa['giay_phien'], pa['so_mat']) == ('A', 40.0, 2) and (pb['dot'], pb['giay_phien'], pb['so_mat']) == ('B', 100.0, 3) and pa['phien'] != pb['phien']
    assert not os.path.exists(d.p_state('P5')) and d.liet_ke('P5') == []                # hết phiên: bỏ file trạng thái


def test_cancel_one_dot_keeps_the_other_and_a_request_is_for_one_dot_only(dh):
    d, g, root = dh
    d.bat_dau('P5', 'manual', dot='A', n_mat=2)
    d.bat_dau('P5', 'manual', dot='B', n_mat=2)
    g.tick(20)
    y = d.huy_mo('P5', dot='A')
    with pytest.raises(DongHoLoi, match='hết hiệu lực'):
        d.huy_xac_nhan('P5', y['ma'], 'HUY', dot='B')                                # mã mở cho A không huỷ được B
    assert d.xem('P5', 'A')['co_phien'] and d.xem('P5', 'B')['co_phien']
    y = d.huy_mo('P5', dot='A')
    row = d.huy_xac_nhan('P5', y['ma'], 'HUY', dot='A')
    assert row['task'] == 'demo-A' and d.xem('P5', 'A')['co_phien'] is False and d.xem('P5', 'B')['chay']
    assert not os.path.exists(os.path.join(root, 'outputs', 'timing', 'timing_P5.csv'))


def test_closing_pauses_only_the_running_dot_and_reports_which(dh):
    d, g, root = dh
    d.bat_dau('P5', 'assisted', dot='A')
    d.bat_dau('P5', 'assisted', dot='B', cho=True)
    g.tick(25)
    got = d.tu_tam_dung_tat_ca()
    assert got == [('P5', '18:30:25', 'A')]
    a, b = d.xem('P5', 'A'), d.xem('P5', 'B')
    assert a['trang_thai'] == 'tam_dung' and 'tat_trang' in a['ma_canh_bao'] and b['cho'] and 'tat_trang' not in b['ma_canh_bao']
    assert d.dang_chay_ai() == [] and d.tu_tam_dung_tat_ca() == []


def test_old_single_session_file_is_read_and_rewritten_in_the_new_format(dh):
    """Tệp trạng thái cũ (một phiên ở đầu tệp, trước QĐ-007) vẫn đọc được; ghi lần đầu thì sang định dạng mới và thêm đợt khác được."""
    d, g, root = dh
    d.bat_dau('P5', 'assisted', dot='Nap1', n_mat=7)
    g.tick(20)
    d.tam_dung('P5', d.xem('P5')['rev'])
    new = json.load(open(d.p_state('P5'), encoding='utf-8'))
    assert new['phien_ban_tep'] == 2 and list(new['cac_dot']) == ['Nap1']
    json.dump(new['cac_dot']['Nap1'], open(d.p_state('P5'), 'w', encoding='utf-8'), ensure_ascii=False)         # dạng cũ: chính phiên đó ở đầu tệp
    d2 = DongHo(root, gio=g, pid=os.getpid())
    w = d2.xem('P5')
    assert w['co_phien'] and w['dot'] == 'Nap1' and w['trang_thai'] == 'tam_dung' and w['giay_phien'] == pytest.approx(20.0)
    d2.bat_dau('P5', 'assisted', dot='NAP_002', n_mat=7)                              # thêm đợt thứ hai
    g.tick(5)
    now = json.load(open(d2.p_state('P5'), encoding='utf-8'))
    assert now['phien_ban_tep'] == 2 and sorted(now['cac_dot']) == ['NAP_002', 'Nap1']
    assert d2.xem('P5', 'Nap1')['giay_phien'] == pytest.approx(20.0) and d2.xem('P5', 'NAP_002')['giay_phien'] == pytest.approx(5.0)


def test_mismatched_dot_key_or_bad_container_is_reported_as_corrupt_not_crash(dh):
    d, g, root = dh
    d.bat_dau('P5', 'manual', dot='A')
    good = json.load(open(d.p_state('P5'), encoding='utf-8'))
    bad = json.loads(json.dumps(good))
    bad['cac_dot']['KHAC'] = bad['cac_dot'].pop('A')                                    # khoá đợt không khớp với đợt ghi trong phiên
    for content in (bad, dict(good, phien_ban_tep=9), dict(good, cac_dot=[1, 2]), dict(good, cac_dot={'A': 'x'})):
        json.dump(content, open(d.p_state('P5'), 'w', encoding='utf-8'))
        w = d.xem('P5')
        assert w['hong'] is True and w['co_phien'] is False and 'hỏng' in w['loi']
    ten = d.bo_trang_thai_hong('P5')
    assert ten.startswith('dang_chay_P5.hong-') and d.xem('P5')['hong'] is False


def test_rev_is_per_dot_so_a_stale_tab_cannot_act_on_the_other_dot(dh):
    d, g, root = dh
    d.bat_dau('P5', 'manual', dot='A')
    a_rev = d.xem('P5', 'A')['rev']
    d.bat_dau('P5', 'manual', dot='B')                                                # A bị tạm dừng bởi thao tác này: rev của A đã đổi
    assert d.xem('P5', 'A')['rev'] == a_rev + 1
    with pytest.raises(DongHoLoi) as e:
        d.tiep_tuc('P5', a_rev, dot='A')                                              # tab cũ còn rev cũ của A
    assert e.value.cu and d.xem('P5', 'A')['trang_thai'] == 'tam_dung' and d.xem('P5', 'B')['chay']


def test_heartbeat_touches_the_running_dot_without_changing_any_rev(dh):
    d, g, root = dh
    d.bat_dau('P5', 'manual', dot='A')
    d.bat_dau('P5', 'manual', dot='B')
    revs = {s['dot']: s['rev'] for s in d.liet_ke('P5')}
    g.tick(70)
    v = d.nhip('P5', 'B')
    assert v['dot'] == 'B' and {s['dot']: s['rev'] for s in d.liet_ke('P5')} == revs
    assert d.xem('P5', 'B')['lan_cuoi_thay'] > '2026-10-14T18:30:00+07:00' and d.xem('P5', 'B')['giay_phien'] == pytest.approx(70.0)


def test_names_differing_only_in_case_are_refused_for_new_sessions(dh):
    """Windows coi dang_chay_p1.json và dang_chay_P1.json là một file: tên mới chỉ khác chữ hoa/thường với tên đã có thì từ chối; tên đã có file vẫn dùng được."""
    d, g, root = dh
    assert d.bat_dau('P1', 'manual', dot='X1')['co_phien']
    with pytest.raises(DongHoLoi, match='chữ hoa/thường'):
        d.bat_dau('p1', 'manual', dot='X2')
    assert d.cac_nguoi() == ['P1']
    if os.path.normcase('A') == 'A' and not os.path.exists(d.p_state('p1')):     # máy phân biệt hoa/thường (Linux): lỡ có cả hai thì tên đã có vẫn dùng được
        open(d.p_state('p1'), 'w').write('{}')
        d.bat_dau('P1', 'manual', dot='X3')


def test_state_file_of_a_case_variant_is_reported_as_a_case_problem_not_corruption(dh):
    """Windows mở dang_chay_P1.json khi hỏi 'p1': báo lệch chữ hoa/thường (không bảo 'Bỏ trạng thái hỏng', vì làm theo sẽ giấu phiên thật của P1)."""
    d, g, root = dh
    d.bat_dau('P1', 'manual', dot='X1')
    raw = open(d.p_state('P1'), encoding='utf-8').read()
    os.makedirs(d.dir, exist_ok=True)
    open(os.path.join(d.dir, 'dang_chay_q1.json'), 'w', encoding='utf-8').write(raw.replace('"nguoi": "P1"', '"nguoi": "Q1"'))   # như Windows: tên file và tên trong file khác hoa/thường
    with pytest.raises(DongHoLoi) as e:
        d._doc_tep('q1')
    assert 'chữ hoa/thường' in str(e.value) and 'KHÔNG hỏng' in str(e.value) and not getattr(e.value, 'hong', False)


def test_lock_just_created_but_still_empty_is_not_an_orphan(dh):
    """Trang khác vừa tạo file khoá (O_EXCL) mà chưa kịp ghi pid: không được coi là khoá mồ côi rồi xoá, nếu không hai trang cùng ghi (Xong lưu hai lần)."""
    from dong_ho import _Khoa
    d, g, root = dh
    os.makedirs(d.dir, exist_ok=True)
    open(d.p_khoa('P5'), 'w').close()
    assert _Khoa(d, 'P5')._mo_coi(d.p_khoa('P5')) is False
    old = time.time() - 120
    os.utime(d.p_khoa('P5'), (old, old))
    assert _Khoa(d, 'P5')._mo_coi(d.p_khoa('P5')) is True                                # rỗng mà đã cũ: mồ côi


def test_orphan_lock_that_cannot_be_removed_times_out_instead_of_spinning(dh, monkeypatch):
    """Khoá mồ côi mà không xoá được (thư mục, không có quyền, Windows đang chờ xoá): báo bận sau ~3 giây, không quay vòng mãi giữ khoá luồng."""
    from dong_ho import _Khoa
    d, g, root = dh
    os.makedirs(d.dir, exist_ok=True)
    open(d.p_khoa('P5'), 'w').write(f'{DEAD_PID} {time.time():.0f}')
    real = os.remove

    def khong_xoa(p, *a, **k):
        if p == d.p_khoa('P5'):
            raise PermissionError('không có quyền')
        return real(p, *a, **k)
    monkeypatch.setattr(os, 'remove', khong_xoa)
    t0 = time.time()
    with pytest.raises(DongHoLoi, match='đang bận'):
        with _Khoa(d, 'P5'):
            pass
    assert time.time() - t0 < 10


def test_lock_survives_windows_sharing_errors(dh, monkeypatch):
    """Windows: tạo khoá gặp "Access denied" (file khoá cũ đang chờ xoá) thì chờ như khoá bận; xoá khoá lúc thả bị antivirus giữ một chút thì thử lại, không để khoá sót."""
    from dong_ho import _Khoa
    d, g, root = dh
    os.makedirs(d.dir, exist_ok=True)
    real_open, real_remove = os.open, os.remove
    lan = {'open': 0, 'remove': 0, 'da_khoa': False}

    def mo(p, *a, **k):
        if p == d.p_khoa('P5') and lan['open'] < 2:
            lan['open'] += 1
            raise PermissionError('[WinError 5] Access is denied')
        return real_open(p, *a, **k)

    def xoa(p, *a, **k):
        if p == d.p_khoa('P5') and lan['da_khoa'] and lan['remove'] < 2:          # chỉ lúc THẢ khoá
            lan['remove'] += 1
            raise PermissionError('[WinError 32] used by another process')
        return real_remove(p, *a, **k)
    monkeypatch.setattr(os, 'open', mo)
    monkeypatch.setattr(os, 'remove', xoa)
    with _Khoa(d, 'P5'):
        assert os.path.exists(d.p_khoa('P5'))
        lan['da_khoa'] = True
    assert (lan['open'], lan['remove']) == (2, 2) and not os.path.exists(d.p_khoa('P5'))
