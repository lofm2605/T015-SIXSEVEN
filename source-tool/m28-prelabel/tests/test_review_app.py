"""Thử tool/review_app.py (trang rà soát) bằng dữ liệu GIẢ dựng trong tmp_path. Không cần trình duyệt, không cần gradio.

Phần giao diện Gradio (bố cục, phím tắt, nút Xong khoá quyết định, nút Đóng trang rà soát) kiểm riêng bằng tests/e2e_review_ui.py (tuỳ chọn).
"""
import csv
import html
import json
import os
import subprocess
import sys
import time
import types

import pytest

TOOL = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tool'))
sys.path.insert(0, TOOL)
import review_app as ra  # noqa: E402
from m28core import steps  # noqa: E402

N_PTS = 50


# ---------- dữ liệu giả ----------
def flags_of(n):
    return [i < n for i in range(N_PTS)]


def make_run(root, faces, run='R1', autoqc=None, no_face=(), crops=(), overlays=()):
    """faces: {tên: số cờ}. autoqc: {tên: (gợi ý, problems)} hoặc None (không có file). no_face: [(tên, lý do, bước)].
    crops/overlays: tên có file ảnh (nội dung giả, chỉ cần tồn tại). Trả đường dẫn runs/<run>."""
    rd = os.path.join(str(root), 'runs', run)
    os.makedirs(os.path.join(rd, 'flags'))
    with open(os.path.join(rd, 'flags', 'flags.json'), 'w', encoding='utf-8') as f:
        json.dump({n: flags_of(k) for n, k in faces.items()}, f)
    if autoqc is not None:
        os.makedirs(os.path.join(rd, 'autoqc'))
        with open(os.path.join(rd, 'autoqc', 'autoqc.csv'), 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['name', 'suggestion', 'n_flags', 'decision', 'reason', 'seconds', 'problems'])
            for n, (sug, probs) in autoqc.items():
                w.writerow([n + '.png', sug, faces.get(n, 0), '', '', '', ';'.join(probs)])
    if no_face:
        with open(os.path.join(rd, 'no_face.csv'), 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['name', 'reason', 'step'])
            w.writerows(no_face)
    for sub, names in (('crop/images', crops), ('overlays', overlays)):
        for n in names:
            p = os.path.join(rd, *sub.split('/'), n + '.png')
            os.makedirs(os.path.dirname(p), exist_ok=True)
            write_png(p)
    return rd


def write_png(path, size=(64, 64), color=(200, 190, 180)):
    """Ảnh thật nhỏ nếu có PIL (test cần mô hình hiển thị), không thì file giả (test hàng đợi chỉ cần file tồn tại)."""
    try:
        from PIL import Image
    except ImportError:
        with open(path, 'wb') as f:
            f.write(b'x')
        return
    Image.new('RGB', size, color).save(path)


def need_pil():
    pytest.importorskip('PIL')


FIVE = {'F_001': 0, 'F_002': 1, 'F_003': 0, 'F_004': 38, 'F_005': 0}
FIVE_QC = {'F_001': ('on', []), 'F_002': ('can_xem', []), 'F_003': ('on', []), 'F_004': ('can_xem', []),
           'F_005': ('on', [])}


@pytest.fixture
def five(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return make_run(tmp_path, FIVE, autoqc=FIVE_QC, overlays=list(FIVE), crops=list(FIVE))


class FakeClock:
    def __init__(self, t=100.0):
        self.t = t

    def __call__(self):
        return self.t


def decide_all(store, decision='nhan'):
    for f in store.faces:
        store.decide(f.name, decision if f.has_draft else 'bo', '' if f.has_draft else 'KHONG_MAT', 1.0)


# ---------- 1. thứ tự hàng đợi ----------
def test_queue_order_and_no_face(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    faces = {'A': 0, 'B': 3, 'C': 7, 'D': 1, 'E': 2}
    qc = {'A': ('on', []), 'B': ('can_xem', []), 'C': ('can_xem', []), 'D': ('nen_gan_tay', ['guong']),
          'E': ('on', [])}
    rd = make_run(tmp_path, faces, autoqc=qc, overlays=list(faces),
                  no_face=[('N1', 'khong_thay_mat', 'mediapipe'), ('N2', 'khong_thay_mat', 'crop')], crops=['N1'])
    q = ra.load_queue(rd)
    assert [f.name for f in q] == ['D', 'N1', 'C', 'B', 'E', 'A']
    n1 = next(f for f in q if f.name == 'N1')
    assert n1.flags is None and not n1.has_draft and n1.no_face_reason == 'khong_thay_mat' and n1.suspicious
    assert 'N2' not in [f.name for f in q]                       # không có ảnh cắt: không vào hàng đợi
    # trùng steps._queue với các mặt có nháp
    args = types.SimpleNamespace(run='R1')
    assert [f.name for f in q if f.has_draft] == steps._queue(args)[0]
    assert next(f for f in q if f.name == 'E').suggestion == 'on' and next(f for f in q if f.name == 'C').n_flags == 7
    store = ra.Store(rd, 'P2')
    assert any('1 mặt không dùng được ở bước crop' in n for n in store.notes)


def test_queue_without_autoqc_orders_by_flags(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rd = make_run(tmp_path, {'A': 0, 'B': 5, 'C': 2, 'D': 5})
    q = ra.load_queue(rd)
    assert [f.name for f in q] == ['B', 'D', 'C', 'A']
    assert all(f.suggestion == '' for f in q)
    assert [f.name for f in q] == steps._queue(types.SimpleNamespace(run='R1'))[0]
    assert ra.SUG_VI[''] == 'chưa có autoqc'


def test_queue_reads_problems_and_tolerates_bad_autoqc(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rd = make_run(tmp_path, {'A': 0, 'B': 1}, autoqc={'A': ('nen_gan_tay', ['diem_ngoai_anh', 'guong']), 'B': ('on', [])})
    a = next(f for f in ra.load_queue(rd) if f.name == 'A')
    assert a.problems == ['diem_ngoai_anh', 'guong'] and a.suggestion == 'nen_gan_tay'
    with open(os.path.join(rd, 'autoqc', 'autoqc.csv'), 'wb') as f:      # file hỏng: coi như chưa có autoqc
        f.write(b'\xff\xfe\x00garbage')
    assert [f.suggestion for f in ra.load_queue(rd)] == ['', '']


# ---------- 2. lỗi trước khi mở trang ----------
def test_run_errors_are_helpful(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ra.RunError) as e:
        ra.load_queue(os.path.join('runs', 'KHONGCO'))
    assert 'Không thấy thư mục lượt chạy' in str(e.value) and 'KHONGCO' in str(e.value) and str(tmp_path) in str(e.value)
    os.makedirs(os.path.join('runs', 'R1'))
    with pytest.raises(ra.RunError) as e:
        ra.load_queue(os.path.join('runs', 'R1'))
    assert 'flags.json' in str(e.value) and 'prepare' in str(e.value) and '--run R1' in str(e.value)
    os.makedirs(os.path.join('runs', 'R1', 'flags'))
    path = os.path.join('runs', 'R1', 'flags', 'flags.json')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('{}')
    with pytest.raises(ra.RunError) as e:
        ra.load_queue(os.path.join('runs', 'R1'))
    assert 'Hàng đợi rỗng' in str(e.value) and 'flags.json' in str(e.value)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('{khong phai json')
    with pytest.raises(ra.RunError) as e:
        ra.load_queue(os.path.join('runs', 'R1'))
    assert 'flags.json' in str(e.value) and 'prepare' in str(e.value)


def test_check_reviewer():
    for ok in ('P2', 'P5', 'E2E', 'a_b-c', 'x' * 32):
        assert ra.check_reviewer(ok) == ok
    for bad in ('', '../x', 'a b', 'P2\n', 'P/2', 'x' * 33, 'Phạm', None):
        with pytest.raises(ra.RunError):
            ra.check_reviewer(bad)


# ---------- 3. đọc/ghi CSV, khớp steps.read_triage ----------
BOM = '﻿'
HDR4 = 'name,decision,reason,seconds'
QC7 = 'name,suggestion,n_flags,decision,reason,seconds,problems'
VARIANTS = {
    'tieu_de': (HDR4 + '\nA.png,nhan,,1.5\nB.png,bo,MO_NHO,2.0\n', ','),
    'bom': (BOM + HDR4 + '\r\nA.png,nhan,,1.5\r\nB.png,bo,MO_NHO,2.0\r\n', ','),
    'cham_phay': ('name;decision;reason;seconds\nA.png;nhan;;1.5\nB.png;bo;MO_NHO;2.0\n', ';'),
    'khong_tieu_de': ('A.png,nhan,,1.5\nB.png,bo,MO_NHO,2.0\n', ','),
    'khong_tieu_de_cham_phay': (BOM + 'A.png;nhan;;1.5\nB.png;bo;MO_NHO;2.0\n', ';'),
    'autoqc_7_cot': (QC7 + '\nA.png,on,0,nhan,,1.5,\nB.png,can_xem,3,bo,MO_NHO,2.0,diem_ngoai_anh\n', ','),
    'autoqc_7_cot_excel': (BOM + QC7.replace(',', ';') + '\r\nA.png;on;0;nhan;;1.5;\r\nB.png;can_xem;3;bo;MO_NHO;2.0;x\r\n', ';'),
    'thieu_xuong_dong_cuoi': (HDR4 + '\nA.png,nhan,,1.5\nB.png,bo,MO_NHO,2.0', ','),
    'chi_co_tieu_de': (HDR4 + '\n', ','),
    'tieu_de_doi_cot': ('seconds,reason,decision,name\n1.5,,nhan,A.png\n2.0,MO_NHO,bo,B.png\n', ','),
}


def write_variant(path, text):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


@pytest.mark.parametrize('kind', list(VARIANTS))
def test_rows_match_read_triage_and_append_keeps_layout(tmp_path, kind):
    text, delim = VARIANTS[kind]
    p = str(tmp_path / 'triage_P2.csv')
    write_variant(p, text)
    before = ra.read_rows(p)
    assert ra.latest(before) == steps.read_triage(p)
    ra.append_row(p, 'C.png', 'gan_tay', 'LECH_VUNG', 3.04)
    ra.append_row(p, 'A.png', 'bo', 'SAI_MAT', 0.25)            # đổi ý: dòng sau đè dòng trước
    ra.append_row(p, 'D.png', '', '', '')                       # chưa rà
    lat = ra.latest(ra.read_rows(p))
    assert lat == steps.read_triage(p)
    assert lat['C'] == ('gan_tay', 'LECH_VUNG') and lat['A'] == ('bo', 'SAI_MAT') and lat['D'] == ('', '')
    if before:
        assert lat['B'] == ('bo', 'MO_NHO')
    raw = open(p, encoding='utf-8-sig', newline='').read()
    assert raw.endswith(('\n', '\r'))                            # file thiếu xuống dòng cuối vẫn không dính dòng
    lines = [l for l in raw.splitlines() if l.strip()]
    assert all(delim in l for l in lines)                       # dùng lại dấu phân cách của file
    assert sum(1 for l in lines if 'decision' in l.lower()) <= 1       # tiêu đề không bị ghi thêm
    rows = ra.read_rows(p)
    assert [r['name'] for r in rows][-3:] == ['C', 'A', 'D']
    assert rows[-3]['seconds'] == '3.0' and rows[-2]['seconds'] == '0.2'    # 3.04 -> 3.0; 0.25 -> 0.2 (làm tròn chẵn)
    if kind == 'tieu_de_doi_cot':
        assert lines[-3] == '3.0,LECH_VUNG,gan_tay,C.png'       # mỗi giá trị đúng vị trí cột của nó


def test_new_file_gets_header_once_and_last_row_wins(tmp_path):
    p = str(tmp_path / 'review' / 'triage_P2.csv')                         # thư mục chưa có
    ra.append_row(p, 'A.png', 'nhan', '', 1.25)
    ra.append_row(p, 'B.png', 'bo', 'MO_NHO', 2)
    ra.append_row(p, 'A.png', 'gan_tay', 'DON_CUC', '')
    lines = open(p, encoding='utf-8', newline='').read().splitlines()
    assert lines[0] == HDR4 and len(lines) == 4 and sum(l.startswith('name,') for l in lines) == 1
    assert lines[1] in ('A.png,nhan,,1.2', 'A.png,nhan,,1.3')      # 1.25 làm tròn chẵn hay lẻ tuỳ nền tảng
    assert lines[2] == 'B.png,bo,MO_NHO,2.0' and lines[3] == 'A.png,gan_tay,DON_CUC,'
    assert ra.latest(ra.read_rows(p)) == {'A': ('gan_tay', 'DON_CUC'), 'B': ('bo', 'MO_NHO')}
    assert ra.latest(ra.read_rows(p)) == steps.read_triage(p)
    assert not open(p, 'rb').read().startswith(b'\xef\xbb\xbf')


def test_append_to_empty_file_and_missing_file(tmp_path):
    assert ra.read_rows(str(tmp_path / 'khongco.csv')) == []
    p = str(tmp_path / 't.csv')
    open(p, 'w').close()
    ra.append_row(p, 'A.png', 'nhan', '', 1)
    assert open(p, encoding='utf-8').read().splitlines()[0] == HDR4


def test_append_into_seven_column_file_writes_each_value_in_its_column(tmp_path):
    p = str(tmp_path / 't.csv')
    write_variant(p, BOM + QC7.replace(',', ';') + '\r\nA.png;on;0;;;;\r\n')
    ra.append_row(p, 'A.png', 'gan_tay', 'MO_NHO', 2.5)
    last = open(p, encoding='utf-8-sig', newline='').read().splitlines()[-1]
    assert last == 'A.png;;;gan_tay;MO_NHO;2.5;'
    assert ra.latest(ra.read_rows(p)) == {'A': ('gan_tay', 'MO_NHO')} == steps.read_triage(p)


def test_append_permission_error_bubbles_up(tmp_path, monkeypatch):
    p = str(tmp_path / 't.csv')
    ra.append_row(p, 'A.png', 'nhan', '', 1)
    real = open

    def locked(path, mode='r', *a, **k):
        if 'a' in mode and str(path) == p:
            raise PermissionError(13, 'Permission denied')
        return real(path, mode, *a, **k)

    monkeypatch.setattr('builtins.open', locked)
    with pytest.raises(PermissionError):
        ra.append_row(p, 'B.png', 'nhan', '', 1)


# ---------- 4. làm tiếp ----------
def test_resume_from_csv(five):
    s1 = ra.Store(five, 'P2', clock=FakeClock())
    first = ra.next_pending(s1.faces, s1.lat)
    assert first == 'F_004'
    s1.decide('F_004', 'nhan', '', 1.0)
    s1.decide('F_002', 'bo', 'MO_NHO', 2.0)
    s2 = ra.Store(five, 'P2')                                     # mở lại: dựng từ cùng CSV
    assert s2.progress() == s1.progress() == dict(total=5, done=2, nhan=1, gan_tay=0, bo=1, remaining=3)
    assert ra.next_pending(s2.faces, s2.lat) == 'F_001'
    assert s2.resumed == 2 and s2.undo_stack == []                # ngăn hoàn tác chỉ sống trong phiên
    assert ra.new_session(s2)['cur'] == 'F_001'
    assert ra.next_pending(s2.faces, s2.lat, 'F_001') == 'F_003'
    assert ra.next_pending(s2.faces, s2.lat, 'F_005') == 'F_001'  # đi vòng lại đầu
    assert ra.next_pending(s2.faces, s2.lat, 'khong_co') == 'F_001'
    for f in s2.faces:
        if not s2.status(f.name):
            s2.decide(f.name, 'nhan', '', 0)
    assert ra.next_pending(s2.faces, s2.lat) is None and ra.next_pending(s2.faces, s2.lat, 'F_001') is None


def test_store_other_reviewer_has_own_file(five):
    ra.Store(five, 'P2').decide('F_004', 'nhan', '', 1)
    assert ra.Store(five, 'P5').progress()['done'] == 0
    assert os.path.exists(os.path.join(five, 'review', 'triage_P2.csv'))


def test_store_rejects_non_utf8_triage(five):
    os.makedirs(os.path.join(five, 'review'))
    with open(os.path.join(five, 'review', 'triage_P2.csv'), 'wb') as f:
        f.write(b'name,decision\nF_004.png,nh\xe2n\n')                 # byte 0xE2 lẻ: không phải UTF-8
    with pytest.raises(ra.RunError) as e:
        ra.Store(five, 'P2')
    assert 'UTF-8' in str(e.value)


# ---------- 5. tiến độ, lọc, phân trang ----------
def test_progress_ignores_unknown_names(five):
    s = ra.Store(five, 'P2')
    s.decide('F_004', 'nhan', '', 1)
    s.decide('F_002', 'gan_tay', 'DON_CUC', 1)
    s.decide('F_001', 'bo', 'MO_NHO', 1)
    lat = dict(s.lat, NGOAI_HANG_DOI=('nhan', ''), F_003=('', ''))     # tên lạ và decision rỗng không được đếm
    assert ra.progress(s.faces, lat) == dict(total=5, done=3, nhan=1, gan_tay=1, bo=1, remaining=2)


def test_filter_modes(five):
    s = ra.Store(five, 'P2')
    s.decide('F_004', 'nhan', '', 1)
    s.decide('F_001', 'bo', 'MO_NHO', 1)
    names = lambda mode: [f.name for f in ra.filter_faces(s.faces, s.lat, mode)]      # noqa: E731
    assert names('tat_ca') == ['F_004', 'F_002', 'F_001', 'F_003', 'F_005']
    assert names('chua_ra') == ['F_002', 'F_003', 'F_005']
    assert names('dang_ngo') == ['F_004', 'F_002']
    assert names('da_ra') == ['F_004', 'F_001']
    assert names('khong_biet') == names('tat_ca')


def test_paging():
    items = [f'F_{i:03d}' for i in range(616)]
    page, p, n = ra.page_slice(items, 0, 24)
    assert n == 26 and p == 0 and len(page) == 24 and page[0] == 'F_000'
    last, p, n = ra.page_slice(items, 25, 24)
    assert p == 25 and len(last) == 616 - 25 * 24 == 16 and last[-1] == 'F_615'
    assert ra.page_slice(items, 99, 24)[1] == 25 and ra.page_slice(items, -5, 24)[1] == 0
    assert ra.page_slice([], 3, 24) == ([], 0, 1)
    assert ra.page_slice(items[:24], 0, 24)[2] == 1 and ra.page_slice(items[:25], 0, 24)[2] == 2
    assert ra.page_of(items, 'F_023', 24) == 0 and ra.page_of(items, 'F_024', 24) == 1
    assert ra.page_of(items, 'F_615', 24) == 25 and ra.page_of(items, 'khong', 24) == 0
    assert ra.PAGE_SIZE == 24


def test_fmt_points():
    assert ra.fmt_points([False] * 50) == ''
    assert ra.fmt_points([i + 1 in (1, 2, 3, 4, 7, 9, 10) for i in range(50)]) == '1–4, 7, 9, 10'
    assert ra.fmt_points([i + 1 in (5, 6) for i in range(50)]) == '5, 6'
    assert ra.fmt_points(flags_of(50)) == '1–50'


# ---------- 6. hoàn tác ----------
def test_undo_restores_previous_state(five):
    s = ra.Store(five, 'P2', clock=FakeClock())
    assert s.undo() is None
    s.decide('F_004', 'nhan', '', 1.0)
    s.decide('F_004', 'bo', 'SAI_MAT', 2.0)                       # đổi A sang Bỏ
    assert s.lat['F_004'] == ('bo', 'SAI_MAT')
    assert s.undo() == 'F_004' and s.lat['F_004'] == ('nhan', '')      # về Nhận
    assert steps.read_triage(s.path)['F_004'] == ('nhan', '')
    assert s.undo() == 'F_004' and s.status('F_004') == ''             # về chưa rà
    assert steps.read_triage(s.path)['F_004'] == ('', '')              # decision rỗng, push coi là chưa có quyết định
    assert s.undo() is None and s.undo_stack == []
    rows = list(csv.reader(open(s.path, encoding='utf-8', newline='')))
    assert rows == [['name', 'decision', 'reason', 'seconds'], ['F_004.png', 'nhan', '', '1.0'],
                    ['F_004.png', 'bo', 'SAI_MAT', '2.0'], ['F_004.png', 'nhan', '', ''], ['F_004.png', '', '', '']]
    assert ra.progress(s.faces, s.lat)['done'] == 0
    assert ra.Store(five, 'P2').progress()['done'] == 0                # mở lại vẫn chưa rà


def test_undo_other_faces_untouched_and_order(five):
    s = ra.Store(five, 'P2')
    s.decide('F_004', 'nhan', '', 1)
    s.decide('F_002', 'gan_tay', 'LECH_VUNG', 1)
    s.decide('F_001', 'bo', 'MO_NHO', 1)
    assert s.undo() == 'F_001' and s.undo() == 'F_002'
    assert s.lat['F_004'] == ('nhan', '') and s.status('F_002') == '' and s.status('F_001') == ''
    assert ra.next_pending(s.faces, s.lat, 'F_004') == 'F_002'


def test_undo_write_failure_keeps_stack(five, monkeypatch):
    s = ra.Store(five, 'P2')
    s.decide('F_004', 'nhan', '', 1)
    monkeypatch.setattr(ra, 'append_row', lambda *a, **k: (_ for _ in ()).throw(PermissionError('khoá')))
    with pytest.raises(PermissionError):
        s.undo()
    assert s.undo_stack and s.lat['F_004'] == ('nhan', '')


# ---------- 7. giây, lý do, no_face ----------
def test_seconds_since():
    assert ra.seconds_since(10.0, 12.34) == 2.3
    assert ra.seconds_since(10.0, 10.04) == 0.0
    assert ra.seconds_since(10.0, 9.0) == 0.0                          # không âm
    assert ra.seconds_since(0.0, 1234.567) == 1234.6                   # không cắt trần
    assert ra.seconds_since(None, 5.0) is None


def test_seconds_use_fake_clock_and_undo_resets_mark(five):
    clock = FakeClock(100.0)
    s = ra.Store(five, 'P2', clock=clock)
    ses = ra.new_session(s)                                            # mốc đầu = lúc trang tải
    assert ses['t'] == 100.0
    clock.t = 103.26
    ra.act_decide(s, ses, 'nhan', '', 'F_004')
    clock.t = 104.0
    ra.act_decide(s, ses, 'gan_tay', 'DON_CUC', 'F_002')
    clock.t = 110.0
    ra.act_undo(s, ses, 'F_001')                                       # Hoàn tác đặt lại mốc
    clock.t = 111.5
    ra.act_decide(s, ses, 'nhan', '', 'F_002')
    clock.t = 150.0
    ra.act_step(s, ses, 1)                                             # chuyển ảnh KHÔNG đặt lại mốc
    clock.t = 160.0
    ra.act_decide(s, ses, 'bo', 'MO_NHO', ses['cur'])
    secs = [r['seconds'] for r in s.rows]
    assert secs == ['3.3', '0.7', '', '1.5', '48.5'], secs


def test_reason_of_nhan_is_blank_and_validation(five):
    s = ra.Store(five, 'P2')
    s.decide('F_004', 'nhan', 'LAT_GUONG', 1)
    assert s.lat['F_004'] == ('nhan', '') and s.rows[-1]['reason'] == ''
    with pytest.raises(ValueError):
        s.decide('F_002', 'khong_biet', '', 1)
    with pytest.raises(ValueError):
        s.decide('F_002', 'bo', 'MA_LA', 1)
    with pytest.raises(ValueError):
        s.decide('KHONG_CO', 'bo', '', 1)
    assert len(s.rows) == 1 and len(s.undo_stack) == 1


def test_no_face_cannot_be_accepted(tmp_path, monkeypatch):
    need_pil()
    monkeypatch.chdir(tmp_path)
    rd = make_run(tmp_path, {'A': 0}, autoqc={'A': ('on', [])}, no_face=[('N1', 'khong_thay_mat', 'mediapipe')],
                  crops=['N1'], overlays=['A'])
    s = ra.Store(rd, 'P2')
    assert [f.name for f in s.faces] == ['N1', 'A']
    with pytest.raises(ValueError) as e:
        s.decide('N1', 'nhan', '', 1)
    assert 'không có nháp' in str(e.value)
    assert not os.path.exists(s.path) and s.undo_stack == []
    s.decide('N1', 'gan_tay', 'NHIEU_MAT', 1)                           # Gán tay và Bỏ thì được
    assert s.lat['N1'] == ('gan_tay', 'NHIEU_MAT')
    ses = ra.new_session(s)
    ses['cur'] = 'N1'
    msg, level, _ = ra.act_decide(s, ses, 'nhan', '', 'N1')
    assert level == 'warn' and 'không có nháp' in msg
    v = ra.make_view(s, ses)
    assert v['nhan_ok'] is False and 'không có nháp' in v['gallery'][0][1] and 'khoá' in v['info']
    assert 'Gán tay mặt này lên CVAT là <b>ảnh trống</b>' in v['info']          # cảnh báo: Gán tay mặt không có nháp lên CVAT là ảnh trống


# ---------- 8. Xong ----------
def test_finish(five):
    s = ra.Store(five, 'P2')
    assert not s.can_finish()
    with pytest.raises(ValueError) as e:
        s.write_done()
    assert '5 mặt chưa rà' in str(e.value)
    assert not os.path.exists(os.path.join(five, 'review', 'done.txt'))
    for f in s.faces[:-1]:
        s.decide(f.name, 'nhan', '', 1)
    assert not s.can_finish() and s.progress()['remaining'] == 1
    s.decide(s.faces[-1].name, 'bo', 'MO_NHO', 1)
    assert s.can_finish()
    path = s.write_done()
    assert path == os.path.join(five, 'review', 'done.txt')
    parts = open(path, encoding='utf-8').read().split('\t')
    assert parts[0] == 'xong' and parts[1] == 'P2' and parts[3] == '5 mặt' and 'T' in parts[2]
    assert [n for n in os.listdir(os.path.join(five, 'review')) if '.tmp' in n] == []      # không để file tạm
    s.undo()                                                                              # hoàn tác sau Xong: lần sau lại bị chặn
    with pytest.raises(ValueError):
        s.write_done()


def test_change_after_done_removes_stale_done_txt(five):
    s = ra.Store(five, 'P2')
    decide_all(s)
    path = s.write_done()
    s2 = ra.Store(five, 'P2')                                          # mở lại lượt đã Xong
    assert s2.had_done and os.path.exists(path)
    s2.decide('F_001', 'bo', 'MO_NHO', 1)                              # đổi ý: done.txt cũ hết đúng
    assert not os.path.exists(path) and s2.had_done
    assert s2.can_finish() and s2.write_done() == path                 # bấm Xong lại thì có lại
    ra.Store(five, 'P2').undo()                                        # ngăn hoàn tác rỗng: không đụng gì
    assert os.path.exists(path)


# ---------- 9. ảnh chồng và ảnh nhỏ ----------
def fake_run_with_images(tmp_path, with_overlay=False, with_crop=True, with_mp50=True):
    pytest.importorskip('PIL')
    from PIL import Image
    pts = [(30 + 40 * (i % 10), 40 + 60 * (i // 10)) for i in range(N_PTS)]       # cách nhau 40 px, không đè số của nhau
    rd = make_run(tmp_path, {'A': 3}, autoqc={'A': ('can_xem', [])})
    if with_crop:
        os.makedirs(os.path.join(rd, 'crop', 'images'))
        Image.new('RGB', (512, 512), (255, 255, 255)).save(os.path.join(rd, 'crop', 'images', 'A.png'))
    if with_overlay:
        os.makedirs(os.path.join(rd, 'overlays'))
        Image.new('RGB', (512, 512), (10, 20, 30)).save(os.path.join(rd, 'overlays', 'A.png'))
    if with_mp50:
        os.makedirs(os.path.join(rd, 'map50'))
        with open(os.path.join(rd, 'map50', 'mp50.json'), 'w', encoding='utf-8') as f:
            json.dump({'A': {'orig': {f'p{i + 1:02d}': list(p) for i, p in enumerate(pts)}, 'flip': None}}, f)
    return rd, pts


def test_overlay_existing_is_used(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rd, _ = fake_run_with_images(tmp_path, with_overlay=True)
    face = ra.load_queue(rd)[0]
    path, warn = ra.overlay_for(face, rd)
    assert path == os.path.join(rd, 'overlays', 'A.png') and warn is None


def test_overlay_redrawn_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from PIL import Image
    rd, pts = fake_run_with_images(tmp_path)
    face = ra.load_queue(rd)[0]
    assert face.overlay is None and face.crop
    path, warn = ra.overlay_for(face, rd)
    assert path == os.path.join(rd, '_tmp', 'overlays', 'A.png') and 'vẽ lại' in warn
    assert not os.path.exists(os.path.join(rd, 'overlays', 'A.png'))        # không ghi vào overlays/
    im = Image.open(path)
    assert im.size == (512, 512)
    for i, (x, y) in enumerate(pts):
        want = (255, 0, 0) if i < 3 else (0, 200, 0)                          # 3 điểm đầu có cờ: đỏ; còn lại xanh
        assert im.convert('RGB').getpixel((x, y)) == want, (i, x, y)
    m = os.path.getmtime(path)
    assert ra.overlay_for(face, rd)[0] == path and os.path.getmtime(path) == m   # cache


def test_overlay_placeholder_when_everything_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from PIL import Image
    rd, _ = fake_run_with_images(tmp_path, with_crop=False)
    face = ra.load_queue(rd)[0]
    path, warn = ra.overlay_for(face, rd)
    im = Image.open(path).convert('RGB')
    assert im.size == (512, 512) and im.getpixel((3, 3)) == im.getpixel((500, 500)) == (214, 214, 214)
    assert len({c for _, c in im.getcolors(maxcolors=512 * 512)}) > 1       # có chữ
    assert warn and 'Thiếu' in warn and 'Nhận' in warn
    store = ra.Store(rd, 'P2')
    assert warn in ra.make_view(store, ra.new_session(store))['info']       # cảnh báo hiện trong bảng thông tin


def test_overlay_for_no_face_uses_crop(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rd = make_run(tmp_path, {'A': 0}, no_face=[('N1', 'khong_thay_mat', 'mediapipe')], crops=['N1'], overlays=['A'])
    face = next(f for f in ra.load_queue(rd) if f.name == 'N1')
    assert ra.overlay_for(face, rd) == (os.path.join(rd, 'crop', 'images', 'N1.png'), None)


def test_thumb_path_has_status_and_small_size(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from PIL import Image
    rd, _ = fake_run_with_images(tmp_path, with_overlay=True)
    face = ra.load_queue(rd)[0]
    paths = {st: ra.thumb_for(face, st, rd) for st in ('', 'nhan', 'gan_tay', 'bo')}
    assert len(set(paths.values())) == 4
    for st, p in paths.items():
        assert os.path.join('_tmp', 'thumbs') in p and p.endswith('.jpg')
        assert (st or 'chua') in os.path.basename(p)
        im = Image.open(p)
        assert im.format == 'JPEG' and max(im.size) <= 200 and min(im.size) >= 100
    green = Image.open(paths['nhan']).convert('RGB').getpixel((88, 2))        # viền 6 px vẽ thẳng vào ảnh
    assert abs(green[0] - 0x16) < 24 and abs(green[1] - 0xa3) < 24 and abs(green[2] - 0x4a) < 24
    grey = Image.open(paths['']).convert('RGB').getpixel((88, 2))
    assert abs(grey[0] - 0x9c) < 24 and abs(grey[2] - 0xaf) < 24
    assert ra.thumb_for(face, 'khong_biet', rd) == paths['']                  # trạng thái lạ = chưa rà


def test_thumb_regenerated_when_source_newer(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rd, _ = fake_run_with_images(tmp_path, with_overlay=True)
    face = ra.load_queue(rd)[0]
    p = ra.thumb_for(face, 'nhan', rd)
    old = os.path.getmtime(p)
    assert ra.thumb_for(face, 'nhan', rd) == p and os.path.getmtime(p) == old          # có cache
    os.utime(p, (old - 100, old - 100))                                                # thumbnail cũ hơn ảnh nguồn
    ra.thumb_for(face, 'nhan', rd)
    assert os.path.getmtime(p) > old - 100


# ---------- 10. Colab / Kaggle ----------
def test_notebook_env():
    assert ra.notebook_env({}, {}) is None
    assert ra.notebook_env({'PATH': '/bin'}, {'os': 1}) is None
    assert ra.notebook_env({}, {'google.colab': object()})
    for var in ('COLAB_RELEASE_TAG', 'COLAB_GPU', 'KAGGLE_KERNEL_RUN_TYPE', 'SPACE_ID'):
        assert 'Colab' in ra.notebook_env({var: ''}, {}), var                   # chỉ cần biến có mặt
    if not any(v in os.environ for v in ra.NOTEBOOK_VARS) and 'google.colab' not in sys.modules:
        assert ra.notebook_env() is None                                        # máy thật


# ---------- 11. không kéo gradio / torch vào khi import ----------
def test_import_loads_neither_gradio_nor_torch():
    code = ("import sys\nsys.path.insert(0, %r)\nimport review_app\n"
            "assert 'gradio' not in sys.modules, 'đã import gradio'\n"
            "assert 'torch' not in sys.modules, 'đã import torch'\nprint('ok')\n") % TOOL
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0 and 'ok' in r.stdout, r.stderr


# ---------- 12. kiểm tĩnh mã nguồn ----------
def test_source_is_local_only_and_env_precedes_import():
    src = open(os.path.join(TOOL, 'review_app.py'), encoding='utf-8').read()
    lines = src.splitlines()
    code_lines = [l for l in lines if not l.lstrip().startswith('#')]
    assert 'server_name="127.0.0.1"' in src and 'share=False' in src
    assert not any('share=True' in l for l in code_lines)
    assert not any(w in src.lower() for w in ('ngrok', 'cloudflared', 'gradio.live', 'share_server'))
    n_import = next(i for i, l in enumerate(lines) if l.strip() == 'import gradio as gr')
    n_temp = next(i for i, l in enumerate(lines) if 'GRADIO_TEMP_DIR' in l and '=' in l and 'env[' in l)
    n_ana = next(i for i, l in enumerate(lines) if 'GRADIO_ANALYTICS_ENABLED' in l and '=' in l and 'env[' in l)
    assert n_temp < n_import and n_ana < n_import
    assert not any(l.lstrip().startswith(('import gradio', 'from gradio', 'import torch', 'from torch'))
                   for l in lines if not l.startswith(' '))                      # không import ở cấp module
    assert 'import torch' not in src and 'GoogleFont' not in src and 'ssr_mode=False' in src


def test_keyboard_js_rules():
    js = ra.PAGE_JS
    assert js.lstrip().startswith('() =>')                                   # launch(js=...) cần một hàm
    for rule in ('e.repeat', 'e.ctrlKey', 'e.altKey', 'e.metaKey', "'TEXTAREA'", "'SELECT'", 'isContentEditable',
                 "'btn-nhan'", "'btn-gantay'", "'btn-bo'", "'btn-undo'", "'btn-prev'", "'btn-next'", '#reason input[type=radio]',
                 "e.key === 'Enter'", "e.key === ' '", 'preventDefault', 'b.disabled'):
        assert rule in js, rule
    text_types = js[js.index('const TEXT = ['):].split(']')[0]
    assert all(t in text_types for t in ('text', 'search', 'number', 'email', 'password'))
    assert 'radio' not in text_types and 'checkbox' not in text_types       # focus ở radio/checkbox: phím tắt vẫn chạy
    assert 'btn-xong' not in js.split('const BY_KEY')[1].split('};')[0]       # không có phím tắt cho Xong (tránh bấm nhầm)


def test_prepare_env_sets_safe_variables(tmp_path):
    env = {'NO_PROXY': 'intranet.local', 'no_proxy': 'localhost'}
    ra.prepare_env(str(tmp_path / 'runs' / 'R1'), env)
    assert env['GRADIO_ANALYTICS_ENABLED'] == 'False' and env['HF_HUB_OFFLINE'] == '1'
    assert env['GRADIO_TEMP_DIR'] == os.path.abspath(str(tmp_path / 'runs' / 'R1' / '_tmp'))
    assert env['NO_PROXY'] == 'intranet.local,localhost,127.0.0.1' and env['no_proxy'] == 'localhost,127.0.0.1'
    ra.prepare_env(str(tmp_path), env)                                           # chạy lại không nhân đôi
    assert env['NO_PROXY'] == 'intranet.local,localhost,127.0.0.1'


# ---------- 13. hiệu năng ----------
def test_performance_616_faces(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    faces = {f'F_{i:03d}': (i * 7) % 11 for i in range(616)}
    qc = {n: (('can_xem' if k > 4 else 'on'), []) for n, k in faces.items()}
    rd = make_run(tmp_path, faces, autoqc=qc, overlays=list(faces)[:100])
    t = time.perf_counter()
    q = ra.load_queue(rd)
    assert len(q) == 616 and time.perf_counter() - t < 1.0
    store = ra.Store(rd, 'P2')
    for f in store.faces[:300]:
        store.decide(f.name, 'nhan', '', 1)
    t = time.perf_counter()
    for mode in ('tat_ca', 'chua_ra', 'dang_ngo', 'da_ra'):
        ra.filter_faces(store.faces, store.lat, mode)
    ra.progress(store.faces, store.lat)
    assert time.perf_counter() - t < 0.05
    assert ra.page_slice(q, 99, ra.PAGE_SIZE)[2] == 26


# ---------- điều khiển và mô hình hiển thị (không cần gradio) ----------
def test_decide_jumps_to_next_pending_and_filter_shrinks(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    ses = ra.new_session(s)
    assert ses['cur'] == 'F_004' and ses['mode'] == 'tat_ca'
    ra.act_filter(s, ses, 'chua_ra')
    seen = []
    for _ in range(5):
        v = ra.make_view(s, ses)
        seen.append((ses['cur'], len(v['gallery'])))
        msg, level, reset = ra.act_decide(s, ses, 'nhan', '', ses['cur'])
        assert level == 'ok' and reset
    assert seen == [('F_004', 5), ('F_002', 4), ('F_001', 3), ('F_003', 2), ('F_005', 1)]   # bộ lọc co lại sau mỗi lần
    assert 'Đã rà hết, bấm Xong' in msg and ses['cur'] == 'F_005'
    v = ra.make_view(s, ses)
    assert v['xong_ok'] and v['xong_label'] == 'Xong'
    assert ses['mode'] == 'tat_ca' and len(v['gallery']) == 5 and v['nhan_ok']      # lọc 'Chưa rà' trống thì về 'Tất cả'


def test_decide_from_old_face_continues_after_it(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    ses = ra.new_session(s)
    ra.act_decide(s, ses, 'nhan', '', 'F_004')
    ra.act_decide(s, ses, 'nhan', '', 'F_002')                      # đứng ở F_001
    ra.make_view(s, ses)                                           # UI luôn vẽ lại sau mỗi sự kiện
    ra.act_select(s, ses, ses['names'].index('F_004'))             # bấm ảnh F_004 trong lưới (đã rà) để đổi ý
    assert ses['cur'] == 'F_004'
    ra.act_decide(s, ses, 'bo', 'SAI_MAT', 'F_004')
    assert s.lat['F_004'] == ('bo', 'SAI_MAT') and ses['cur'] == 'F_001'     # nhảy tới mặt chưa rà kế tiếp sau F_004


def test_stale_click_is_ignored(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    ses = ra.new_session(s)
    ra.act_decide(s, ses, 'nhan', '', 'F_004')
    msg, level, reset = ra.act_decide(s, ses, 'nhan', '', 'F_004')     # bấm lần hai khi trang chưa kịp đổi ảnh
    assert level == 'info' and 'chưa kịp đổi' in msg and not reset and len(s.rows) == 1 and ses['cur'] == 'F_002'
    assert ra.act_undo(s, ses, 'F_004')[1] == 'info' and len(s.rows) == 1


def test_write_failure_keeps_face_and_warns(five, monkeypatch):
    s = ra.Store(five, 'P2', clock=FakeClock())
    ses = ra.new_session(s)

    def locked(*a, **k):
        raise PermissionError(13, 'Permission denied')

    monkeypatch.setattr(ra, 'append_row', locked)
    msg, level, reset = ra.act_decide(s, ses, 'nhan', '', 'F_004')
    assert level == 'warn' and 'Excel' in msg and not reset
    assert ses['cur'] == 'F_004' and s.progress()['done'] == 0 and s.undo_stack == []
    assert ra.act_undo(s, ses, 'F_004')[1] == 'info'                   # ngăn rỗng
    monkeypatch.undo()


def test_prev_next_walk_filtered_list_without_skipping_done(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    ses = ra.new_session(s)
    ra.act_decide(s, ses, 'nhan', '', 'F_004')
    ra.make_view(s, ses)
    ra.act_select(s, ses, 0)                                           # quay lại F_004 (đã rà)
    ra.act_step(s, ses, 1)
    assert ses['cur'] == 'F_002'
    ra.act_step(s, ses, -1)
    assert ses['cur'] == 'F_004'                                       # không bỏ qua mặt đã rà
    ra.act_step(s, ses, -1)
    assert ses['cur'] == 'F_004'                                       # chạm đầu danh sách thì đứng yên
    v = ra.make_view(s, ses)
    assert v['prev_ok'] is False and v['next_ok'] is True
    ra.act_filter(s, ses, 'da_ra')
    assert ses['cur'] == 'F_004'
    ra.act_step(s, ses, 1)
    assert ses['cur'] == 'F_004'                                       # trong 'Đã rà' chỉ có một mặt


def test_gallery_pages_and_selected_index(tmp_path, monkeypatch):
    need_pil()
    monkeypatch.chdir(tmp_path)
    faces = {f'F_{i:03d}': 0 for i in range(60)}
    rd = make_run(tmp_path, faces, overlays=list(faces))
    s = ra.Store(rd, 'P2', clock=FakeClock())
    ses = ra.new_session(s)
    v = ra.make_view(s, ses)
    assert len(v['gallery']) == 24 and v['selected'] == 0 and 'Trang <b>1</b>/3' in v['page_html']
    assert v['page_prev'] is False and v['page_next'] is True
    ra.act_page(s, ses, 1)
    v = ra.make_view(s, ses)
    assert v['selected'] is None and 'Trang <b>2</b>/3' in v['page_html']        # mặt đang xem nằm ở trang khác
    for _ in range(30):
        ra.act_decide(s, ses, 'nhan', '', ses['cur'])
    v = ra.make_view(s, ses)
    assert ses['cur'] == 'F_030' and ses['page'] == 1 and v['selected'] == 6      # lưới chuyển tới trang có mặt đó
    ra.act_page(s, ses, 99)
    assert ra.make_view(s, ses)['page_next'] is False and ses['page'] == 2


def test_caption_and_info_text(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    q = {f.name: f for f in s.faces}
    assert ra.caption(q['F_004'], '') == 'F_004 · 38 cờ · cần xem'
    assert ra.caption(q['F_001'], 'nhan') == 'F_001 · 0 cờ · ổn · Nhận'
    ses = ra.new_session(s)
    info = ra.make_view(s, ses)['info']
    assert 'Điểm nghi sai' in info and 'Gợi ý của máy' in info and 'F_004.png' in info and '38/50' in info and '1–26, 28, 32–36, 38, 39, 44–47' not in info   # F_004 giả chỉ có cờ 1–38
    assert '1–38' in info and '1/5 trong hàng đợi' in info and 'Chưa rà' in info and 'cần xem' in info


def test_header_mentions_run_reviewer_progress(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    ses = ra.new_session(s)
    h = ra.make_view(s, ses)['header']
    assert 'F5' not in h and 'R1' in h and 'P2' in h and 'Đã rà 0/5' in h and 'Còn lại <b>5</b>' in h
    s.decide('F_004', 'nhan', '', 1)
    assert 'Đã rà 1/5' in ra.make_view(s, ses)['header']
    open(os.path.join(five, 'review', 'done.txt'), 'w').write('ok')
    assert 'đã bấm Xong trước đó' in ra.header_html(ra.Store(five, 'P2'), ses)


def test_problems_are_translated(tmp_path, monkeypatch):
    need_pil()
    monkeypatch.chdir(tmp_path)
    rd = make_run(tmp_path, {'A': 0}, autoqc={'A': ('nen_gan_tay', ['diem_ngoai_anh', 'diem_khong_hop_le', 'la'])},
                  overlays=['A'])
    s = ra.Store(rd, 'P2')
    info = ra.make_view(s, ra.new_session(s))['info']
    assert 'điểm ra ngoài ảnh' in info and 'điểm không hợp lệ' in info and 'la' in info and 'nên gán tay' in info


# ---------- phát hiện của đợt kiểm độc lập 6/10 ----------
def test_filter_change_moves_to_a_face_inside_the_list(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    ses = ra.new_session(s)
    ses['cur'] = 'F_005'                                              # mặt ổn, 0 cờ
    ra.act_filter(s, ses, 'dang_ngo')
    v = ra.make_view(s, ses)
    assert ses['cur'] == 'F_004' and v['selected'] == 0 and v['nhan_ok'] and v['shown'] == 'F_004'
    ra.act_decide(s, ses, 'nhan', '', 'F_004')
    ra.act_filter(s, ses, 'da_ra')                                    # đang xem F_002 (chưa rà) -> sang mặt đã rà
    assert ses['cur'] == 'F_004'
    ra.act_filter(s, ses, 'tat_ca')
    assert ses['cur'] == 'F_004'                                      # đã nằm trong danh sách thì giữ


def test_empty_filter_locks_decisions_and_shows_message(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    ses = ra.new_session(s)
    ra.act_filter(s, ses, 'da_ra')                                    # chưa rà mặt nào
    v = ra.make_view(s, ses)
    assert v['gallery'] == [] and 'Chưa rà mặt nào' in v['page_html'] and 'Trang' not in v['page_html']
    assert not (v['nhan_ok'] or v['tay_ok'] or v['bo_ok'] or v['prev_ok'] or v['next_ok'])
    msg, level, reset = ra.act_decide(s, ses, 'nhan', '', ses['cur'])  # ghi nhầm cho mặt vô hình bị chặn
    assert level == 'info' and 'không nằm trong bộ lọc' in msg and s.rows == []


def test_dang_ngo_runs_out_then_switches_to_chua_ra(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    ses = ra.new_session(s)
    ra.act_filter(s, ses, 'dang_ngo')
    ra.act_decide(s, ses, 'nhan', '', 'F_004')
    assert ses['cur'] == 'F_002' and ses['mode'] == 'dang_ngo'
    msg, *_ = ra.act_decide(s, ses, 'nhan', '', 'F_002')
    assert ses['mode'] == 'chua_ra' and ses['cur'] == 'F_001' and 'chuyển sang' in msg


def test_undo_returns_face_into_filter(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    ses = ra.new_session(s)
    ra.act_filter(s, ses, 'da_ra')
    ra.act_filter(s, ses, 'tat_ca')
    ra.act_decide(s, ses, 'nhan', '', 'F_004')
    ra.act_filter(s, ses, 'da_ra')
    ra.act_decide(s, ses, 'bo', 'SAI_MAT', 'F_004')                   # đổi ý trong 'Đã rà': nhảy sang mặt chưa rà
    assert ses['mode'] == 'chua_ra'
    ra.act_undo(s, ses, ses['cur'])
    assert ses['cur'] == 'F_004' and ses['mode'] == 'tat_ca'


def test_repeated_decision_is_not_written_twice(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    ses = ra.new_session(s)
    for n in ('F_004', 'F_002', 'F_001', 'F_003', 'F_005'):
        ra.act_decide(s, ses, 'nhan', '', n)
    assert ses['cur'] == 'F_005' and len(s.rows) == 5
    for _ in range(3):
        msg, level, reset = ra.act_decide(s, ses, 'nhan', '', 'F_005')
        assert level == 'info' and 'đã là Nhận rồi' in msg and not reset
    assert len(s.rows) == 5
    ra.act_decide(s, ses, 'gan_tay', '', 'F_005')                      # đổi quyết định thì ghi
    assert len(s.rows) == 6
    assert ra.act_decide(s, ses, 'gan_tay', '', 'F_005')[1] == 'info'
    assert ra.act_decide(s, ses, 'gan_tay', 'MO_NHO', 'F_005')[1] == 'ok'     # thêm lý do thì ghi
    assert len(s.rows) == 7


def test_skipped_face_is_found_again_after_last_one(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    ses = ra.new_session(s)
    ra.act_decide(s, ses, 'nhan', '', 'F_004')
    ra.act_step(s, ses, 1)                                             # F_002 -> F_001, lướt qua F_002
    assert ses['cur'] == 'F_001'
    for n in ('F_001', 'F_003', 'F_005'):
        ses['cur'] = n
        ra.act_decide(s, ses, 'nhan', '', n)
    assert ses['cur'] == 'F_002' and s.status('F_002') == ''           # vòng lại mặt bị lướt qua, không kẹt ở F_005


def test_decision_without_reason_gets_soft_hint(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    ses = ra.new_session(s)
    msg, level, _ = ra.act_decide(s, ses, 'gan_tay', '', 'F_004')
    assert level == 'ok' and 'Chưa có lý do' in msg and 'Hoàn tác' in msg
    msg, level, _ = ra.act_decide(s, ses, 'bo', 'MO_NHO', 'F_002')
    assert 'Chưa có lý do' not in msg
    assert 'TRƯỚC' in open(os.path.join(TOOL, 'review_app.py'), encoding='utf-8').read()     # nhãn nói rõ thứ tự


def test_finished_blocks_decisions_in_all_tabs_and_shows_done_bar_not_overlay(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    ses = ra.new_session(s)
    other = ra.new_session(s)                                          # tab thứ hai
    decide_all(s)
    assert 'm28-done-bar' not in ra.make_view(s, ses)['header']
    msg, level, ok = ra.act_finish(s, ses)
    assert ok and s.finished and os.path.exists(s.done_path) and not s.closed
    assert 'done.txt' in msg and 'tự tắt' not in msg                   # Xong không còn tắt trang; e2e chờ #msg chứa done.txt
    v = ra.make_view(s, ses)
    assert 'class="m28-done-bar"' in v['header'] and 'role="status"' in v['header'] and not v['nhan_ok'] and not v['xong_ok']
    assert ("Đã ghi xong. Bạn có thể Đẩy lên CVAT, xem Các đợt, xuất Ca khó. "
            "Xong việc bấm 'Đóng trang rà soát' để quay lại cmd.") in html.unescape(v['header'])
    # không còn lớp phủ chặn toàn màn hình (class cũ m28-done không còn nghĩa nào, lớp phủ chỉ có sau khi đóng)
    assert 'class="m28-done"' not in v['header'] and 'm28-closed' not in v['header']
    assert 'm28-done-bar' in ra.make_view(s, other)['header']          # tab kia cũng thấy dải xanh
    assert not ra.make_view(s, other)['nhan_ok']                       # và bị khoá quyết định
    n = len(s.rows)
    m1 = ra.act_decide(s, other, 'bo', '', other['cur'])
    assert m1[1] == 'info' and m1[0] == ra.CLOSED_MSG and 'trang sắp tắt' not in m1[0]
    assert ra.act_undo(s, other, other['cur'])[1] == 'info'
    assert ra.act_finish(s, other)[0] == ra.CLOSED_MSG                 # bấm Xong lần nữa: không ghi lại
    assert len(s.rows) == n and os.path.exists(s.done_path)           # done.txt không bị xoá


def test_done_bar_css_is_inline_not_fullscreen_and_overlay_only_after_close(five):
    css = ra.CSS
    bar = css[css.index('.m28-done-bar {'):css.index('}', css.index('.m28-done-bar {'))]
    assert 'position' not in bar and 'fixed' not in bar and 'var(' in bar          # nằm trong dòng, dùng biến theme
    assert 'm28-done {' not in css and '.m28-done-box' not in css
    assert 'position: fixed' in css[css.index('.m28-closed {'):css.index('}', css.index('.m28-closed {'))]
    assert "'.m28-done-bar'" in ra.PAGE_JS and "'.m28-closed'" in ra.PAGE_JS         # JS: chặn phím tắt sau Xong; chặn hết sau Đóng
    assert "querySelector('.m28-done')" not in ra.PAGE_JS


def test_reload_after_finish_with_new_face_unlocks_and_reopens(five):
    """Sau Xong, khôi phục ảnh làm lượt có lại mặt chưa rà: mở khoá, mất dải xanh, nút Xong khoá lại kèm 'còn N mặt chưa rà'."""
    need_pil()
    import dot_anh
    s = ra.Store(five, 'P2', clock=FakeClock())
    dot_anh.soft_delete_image(five, 'F_005')
    s.exclude('F_005')
    decide_all(s)
    ses = ra.new_session(s)
    assert ra.act_finish(s, ses)[2] and s.finished and os.path.exists(s.done_path)
    folder = dot_anh.list_trash(five)[0]['folder']
    res = dot_anh.restore_image(five, folder, reviewer='P2')
    assert res['mo_lai'] and not os.path.exists(s.done_path)          # dot_anh gỡ done.txt
    s.reload()
    assert s.progress()['remaining'] == 1 and not s.finished
    v = ra.make_view(s, ra.ensure_session(s, ses))
    assert 'm28-done-bar' not in v['header'] and v['nhan_ok'] and v['tay_ok'] and not v['xong_ok']
    assert 'còn 1 mặt chưa rà' in v['xong_label']
    ses2 = ra.ensure_session(s, ses)
    ra.act_filter(s, ses2, 'chua_ra')
    assert ses2['cur'] == 'F_005'                                       # lọc 'Chưa rà' đưa tới mặt vừa khôi phục
    assert ra.act_decide(s, ses2, 'nhan', '', 'F_005')[1] == 'ok'     # ghi được lại
    assert ra.act_finish(s, ses2)[2] and s.finished                   # rà tiếp rồi bấm Xong lại


def test_reload_after_finish_when_soft_delete_keeps_finished(five):
    """Xoá mềm ảnh sau Xong (lượt vẫn rà hết) thì giữ trạng thái đã xong, done.txt còn."""
    need_pil()
    import dot_anh
    s = ra.Store(five, 'P2', clock=FakeClock())
    decide_all(s)
    ses = ra.new_session(s)
    assert ra.act_finish(s, ses)[2]
    dot_anh.soft_delete_image(five, 'F_002', reviewer='P2')
    s.exclude('F_002')
    s.reload()
    assert s.finished and os.path.exists(s.done_path) and s.progress()['remaining'] == 0
    assert 'm28-done-bar' in ra.make_view(s, ra.ensure_session(s, ses))['header']


def test_had_done_is_not_locked_and_no_green_bar_until_done_in_this_session(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    decide_all(s)
    ra.act_finish(s, ra.new_session(s))
    s2 = ra.Store(five, 'P2', clock=FakeClock())                       # mở lại lượt đã Xong (review_app.py runs\X P2)
    assert s2.had_done and not s2.finished
    ses = ra.new_session(s2)
    v = ra.make_view(s2, ses)
    assert 'đã bấm Xong trước đó' in v['header'] and 'm28-done-bar' not in v['header'] and v['nhan_ok']
    ra.act_decide(s2, ses, 'gan_tay', '', ses['cur'])                  # quyết định mới gỡ done.txt như cũ
    assert not os.path.exists(s2.done_path)


# ---------- nút Đóng trang rà soát (logic thuần) ----------
def busy_job(run='NAP_001'):
    return types.SimpleNamespace(running=True, run=run, snapshot=lambda: {'state': 'dang_chay', 'run': run}, cancel=lambda: None)


def test_close_check_refuses_while_jobs_run_or_switching(five):
    s = ra.Store(five, 'P2', clock=FakeClock())
    ctx = ra.AppCtx(reviewer='P2', run_dir=five)
    assert ra.close_check(s, ctx) == (True, '', 'info')
    assert ra.close_check(None, ctx)[0]                                # chế độ --nap
    ctx.job = busy_job('NAP_007')
    ok, msg, lv = ra.close_check(s, ctx)
    assert not ok and lv == 'warn' and 'Đang chuẩn bị lượt NAP_007' in msg and 'chờ xong hoặc bấm Huỷ' in msg
    ctx.job = ra.AppCtx(reviewer='P2', run_dir=five).job
    ctx.push_job = busy_job('R1')
    ok, msg, lv = ra.close_check(s, ctx)
    assert not ok and lv == 'warn' and 'đẩy lượt R1 (CVAT)' in msg
    ctx.push_job = ra.AppCtx(reviewer='P2', run_dir=five).push_job
    ctx.del_job = busy_job('R2')
    ok, msg, lv = ra.close_check(s, ctx)
    assert not ok and 'xoá task của lượt R2 (CVAT)' in msg
    ctx.del_job = ra.AppCtx(reviewer='P2', run_dir=five).del_job
    ctx.switch_to = (five, s)
    ok, msg, lv = ra.close_check(s, ctx)
    assert not ok and lv == 'warn' and 'chuyển' in msg
    assert not ctx.begin_close()                                       # đang chuyển lượt: cũng không đặt cờ đóng được
    ctx.switch_to = None
    assert ra.close_check(s, ctx)[0]


def test_close_flag_is_set_once_and_blocks_every_writer(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    ctx = ra.AppCtx(reviewer='P2', run_dir=five)
    assert ctx.begin_close() is True and ctx.closing
    assert ctx.begin_close() is False                                  # lần hai (tab khác / bấm đúp): không đặt lại
    ok, msg, lv = ra.close_check(s, ctx)
    assert not ok and 'đang đóng' in msg
    assert not ctx.begin_switch(('x', None))                           # Rà lượt này sau khi đóng: từ chối
    assert ctx.switch_to is None
    s.closed = True
    ses = ra.new_session(s)
    n = len(s.rows)
    assert ra.act_decide(s, ses, 'nhan', '', ses['cur'])[0] == ra.CLOSING_MSG
    assert ra.act_undo(s, ses, ses['cur'])[0] == ra.CLOSING_MSG
    assert ra.act_finish(s, ses)[0] == ra.CLOSING_MSG
    assert len(s.rows) == n and not os.path.exists(s.done_path)
    v = ra.make_view(s, ses)
    assert not v['nhan_ok'] and not v['tay_ok'] and not v['xong_ok'] and not v['undo_ok']


def test_begin_switch_then_close_is_refused_and_keeps_first_target(five):
    ctx = ra.AppCtx(reviewer='P2', run_dir=five)
    assert ctx.begin_switch(('A', 1)) and ctx.begin_switch(('B', 2))
    assert ctx.switch_to == ('A', 1)
    assert not ctx.begin_close() and not ctx.closing


def test_close_prompt_three_cases_plus_nap_and_had_done(five):
    need_pil()
    assert ra.close_prompt(None)[0] == 'nap'
    s = ra.Store(five, 'P2', clock=FakeClock())
    kind, q, warn = ra.close_prompt(s)                                 # chưa Xong, còn mặt chưa rà
    assert kind == 'chua_con' and 'chưa bấm Xong, lượt này sẽ còn mặt chưa rà' in warn and '5 mặt' in warn
    assert 'm28 sẽ dừng ở bước review' in warn and 'gõ lại đúng lệnh' in warn
    decide_all(s)                                                      # chưa Xong nhưng đã rà hết
    kind, q, warn = ra.close_prompt(s)
    assert kind == 'chua_het' and 'chưa bấm Xong: m28 sẽ coi như chưa rà xong; bấm Huỷ rồi bấm Xong trước nếu muốn đi tiếp' in warn
    ra.act_finish(s, ra.new_session(s))                                # đã Xong
    kind, q, warn = ra.close_prompt(s)
    assert kind == 'xong' and q == 'Đóng trang rà soát? Lệnh m28 trong cmd sẽ đi tiếp.' and not warn
    s2 = ra.Store(five, 'P2', clock=FakeClock())                       # mở lại lượt đã có done.txt (had_done, chưa bấm Xong ở phiên này)
    assert s2.had_done and not s2.finished and ra.close_prompt(s2)[0] == 'xong'
    os.remove(s2.done_path)                                            # done.txt không còn trên đĩa: không coi là đã Xong
    assert ra.close_prompt(s2)[0] == 'chua_het'
    body = ra.close_body_html(s2)
    assert 'close-confirm-title' in body and 'role="alert"' in body


def test_closed_overlay_exists_only_in_closed_html(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    decide_all(s)
    ra.act_finish(s, ra.new_session(s))
    assert 'm28-closed' not in ra.make_view(s, ra.new_session(s))['header']     # sau Xong chưa có lớp phủ
    assert 'm28-closed' in ra.CLOSED_HTML and 'Đã đóng trang rà soát. ' in ra.CLOSED_HTML.replace('</b><span>', ' ') and 'cmd' in ra.CLOSED_HTML


def test_xong_no_longer_closes_server_source():
    src = open(os.path.join(TOOL, 'review_app.py'), encoding='utf-8').read()
    body = src[src.index('    def on_xong(ses):'):src.index('    def on_reselect(ses):')]
    assert 'demo.close' not in body and 'Timer' not in body and 'job.running' not in body    # Xong không tắt gì, không cần từ chối vì job
    assert src.count('demo.close(verbose=False)') == 3                 # nút Đóng, 'Rà lượt này' (tab Nạp ảnh), KeyboardInterrupt; chuyển lượt từ tab Các đợt nằm ở dot_ui
    assert 'elem_id="btn-dong"' in src and 'close_once' not in src


def test_corrupt_overlay_does_not_break_page(five):
    need_pil()
    s = ra.Store(five, 'P2', clock=FakeClock())
    with open(os.path.join(five, 'overlays', 'F_002.png'), 'wb') as f:
        f.write(b'junk')
    big, warn = ra.overlay_for(s.by_name['F_002'], five)
    assert warn and 'hỏng' in warn and big != os.path.join(five, 'overlays', 'F_002.png')   # không có mp50: ảnh xám
    assert open(os.path.join(five, 'overlays', 'F_002.png'), 'rb').read() == b'junk'        # không ghi đè file gốc
    ses = ra.new_session(s)
    v = ra.make_view(s, ses)                                           # không văng lỗi
    assert len(v['gallery']) == 5 and all(os.path.exists(p) for p, _ in v['gallery'])
    with open(os.path.join(five, 'crop', 'images', 'F_001.png'), 'wb') as f:
        f.write(b'junk')
    with open(os.path.join(five, 'overlays', 'F_001.png'), 'wb') as f:
        f.write(b'junk')
    assert len(ra.make_view(s, ses)['gallery']) == 5


def test_corrupt_overlay_is_redrawn_from_crop_when_possible(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rd, pts = fake_run_with_images(tmp_path, with_overlay=True)
    with open(os.path.join(rd, 'overlays', 'A.png'), 'wb') as f:
        f.write(b'junk')
    s = ra.Store(rd, 'P2')
    big, warn = ra.overlay_for(s.by_name['A'], rd)
    assert '_tmp' in big and 'hỏng' in warn and 'prepare' in warn
    assert os.path.exists(ra.thumb_for(s.by_name['A'], '', rd))


def test_port_is_fixed_so_second_copy_fails_clearly(five, tmp_path):
    src = open(os.path.join(TOOL, 'review_app.py'), encoding='utf-8').read()
    assert 'server_port=port' in src and 'TrustedHostMiddleware' in src and 'DEFAULT_PORT = 7860' in src
    assert 'allowed_paths=[os.path.abspath(run_dir)]' not in src          # chỉ mở overlays, crop/images, _tmp


# ---------- chạy thật như m28 gọi ----------
def run_app(cwd, *args):
    return subprocess.run([sys.executable, os.path.join(TOOL, 'review_app.py'), *args], cwd=str(cwd), capture_output=True,
                          text=True, encoding='utf-8', timeout=60)


def test_cli_errors_exit_2_with_one_line(five, tmp_path):
    for args, word in ((('runs/KHONGCO', 'P2'), 'Không thấy thư mục'), (('runs/R1', '../x'), 'không hợp lệ'),
                       (('runs/R1',), 'Cách dùng')):
        r = run_app(tmp_path, *args)
        assert r.returncode == 2 and word in r.stderr and 'Traceback' not in r.stderr, (args, r.stderr)
        assert len(r.stderr.strip().splitlines()) == 1 and r.stdout == ''
    r = subprocess.run([sys.executable, os.path.join(TOOL, 'review_app.py'), 'runs/R1', 'P2'], cwd=str(tmp_path),
                       capture_output=True, text=True, encoding='utf-8', timeout=60, env=dict(os.environ, COLAB_GPU='1'))
    assert r.returncode == 2 and 'Colab' in r.stderr and 'Traceback' not in r.stderr
    assert not os.path.exists(os.path.join(five, '_tmp'))              # lỗi thì chưa mở server, chưa tạo gì


# ======================= tab Nạp ảnh (tool/nap_anh.py) =======================
import nap_anh as na  # noqa: E402


def _img(path, fmt='JPEG', size=(64, 64), color=(120, 130, 140)):
    from PIL import Image
    os.makedirs(os.path.dirname(str(path)), exist_ok=True)
    Image.new('RGB', size, color).save(str(path), format=fmt)
    return str(path)


def test_clean_stem():
    assert na.clean_stem('Ảnh mặt (1).JPG') == 'Anh_mat_1'
    assert na.clean_stem('Đặng Đình đẹp.png') == 'Dang_Dinh_dep'
    assert na.clean_stem('../../x.png') == 'x'
    assert na.clean_stem('C:\\a\\b.JPG') == 'b'
    assert na.clean_stem('') == 'anh' and na.clean_stem('(((.png') == 'anh'
    assert na.clean_stem('CON.jpg') == 'CON_anh' and na.clean_stem('com1.png') == 'com1_anh'
    long = na.clean_stem('a' * 200 + '.jpg')
    assert long == 'a' * 60
    assert na.clean_stem('a   b__c--d.jpg') == 'a_b_c--d'


def test_unique_stems_case_insensitive():
    assert na.unique_stems(['a', 'A', 'a_2']) == ['a', 'A_2', 'a_2_2']
    assert na.unique_stems(['x', 'x', 'x']) == ['x', 'x_2', 'x_3']
    out = na.unique_stems(['b' * 60, 'B' * 60])
    assert len(out[1]) <= 60 and out[0].lower() != out[1].lower()


def test_check_image_accepts_and_rejects(tmp_path):
    need_pil()
    ok, why = na.check_image(_img(tmp_path / 'a.jpg'))
    assert why is None and ok['ext'] == '.jpg' and (ok['w'], ok['h']) == (64, 64)
    ok, why = na.check_image(_img(tmp_path / 'b.PNG', 'PNG'))
    assert why is None and ok['ext'] == '.png'
    ok, why = na.check_image(_img(tmp_path / 'lie.png', 'JPEG'))          # đuôi .png nhưng ruột JPEG
    assert why is None and ok['ext'] == '.jpg'
    (tmp_path / 'text.jpg').write_text('xin chào, không phải ảnh', encoding='utf-8')
    assert na.check_image(str(tmp_path / 'text.jpg'))[1]
    assert 'GIF' in na.check_image(_img(tmp_path / 'g.jpg', 'GIF'))[1]
    assert na.check_image(_img(tmp_path / 'c.bmp', 'BMP'))[1].startswith('đuôi')
    assert 'lớn hơn' in na.check_image(str(tmp_path / 'a.jpg'), max_bytes=10)[1]
    assert 'quá lớn' in na.check_image(str(tmp_path / 'a.jpg'), max_pixels=100)[1]
    assert 'quá nhỏ' in na.check_image(_img(tmp_path / 's.png', 'PNG', (20, 90)))[1]
    assert na.check_image(str(tmp_path / 'khongco.jpg'))[1]
    (tmp_path / 'empty.jpg').write_bytes(b'')
    assert 'rỗng' in na.check_image(str(tmp_path / 'empty.jpg'))[1]


def test_plan_upload(tmp_path):
    need_pil()
    a = _img(tmp_path / 'd1' / 'mat.jpg', color=(1, 2, 3))
    b = _img(tmp_path / 'd2' / 'mat.jpg', color=(9, 9, 9))
    dup = str(tmp_path / 'trung.jpg')
    open(dup, 'wb').write(open(a, 'rb').read())
    fake = str(tmp_path / 'gia.jpg')
    open(fake, 'w').write('x' * 50)
    plan = na.plan_upload([a, b, dup, fake])
    assert [na.new_name(i) for i in plan['ok']] == ['mat.jpg', 'mat_2.jpg']
    assert all(set(i) >= {'orig', 'stem', 'ext', 'bytes', 'w', 'h', 'sha256', 'src'} for i in plan['ok'])
    rej = dict(plan['rejected'])
    assert 'trùng nội dung với mat.jpg' in rej['trung.jpg'] and 'gia.jpg' in rej
    many = [_img(tmp_path / 'm' / f'i{k}.png', 'PNG', color=(k, k, k)) for k in range(9)]
    plan = na.plan_upload(many, max_files=5)
    assert len(plan['ok']) == 5 and len(plan['rejected']) == 4 and 'vượt 5 ảnh mỗi lần' in plan['rejected'][0][1]
    assert na.plan_upload([]) == dict(ok=[], rejected=[]) and na.plan_upload(None)['ok'] == []


def test_run_names(tmp_path):
    runs = str(tmp_path / 'runs')
    assert na.next_run_name(runs) == 'NAP_001'                           # chưa có thư mục runs
    for d in ('NAP_001', 'nap_007', 'NAP_x', 'F5', '_nap'):
        os.makedirs(os.path.join(runs, d))
    assert na.next_run_name(runs) == 'NAP_008'
    assert na.check_run_name(' KHACH_A ', runs) == 'KHACH_A'
    for bad in ('nap_001', 'NAP_007', 'f5', 'a b', 'ả', '_nap', '', 'x' * 33, 'CON', 'lpt3', '../x', '-a'):
        with pytest.raises(na.RunError):
            na.check_run_name(bad, runs)
    assert ra.RunError is na.RunError


def test_stage_upload(tmp_path):
    need_pil()
    runs = str(tmp_path / 'runs')
    os.makedirs(os.path.join(runs, 'F5'))
    src = _img(tmp_path / 'up' / 'Ảnh mặt.JPG')
    plan = na.plan_upload([src])
    rd = na.stage_upload(runs, 'NAP_001', plan, cleanup_root=str(tmp_path / 'up'))
    assert rd == os.path.join(runs, 'NAP_001') and os.listdir(os.path.join(rd, 'inbox')) == ['Anh_mat.jpg']
    assert na._sha256(os.path.join(rd, 'inbox', 'Anh_mat.jpg')) == plan['ok'][0]['sha256']             # chép nguyên byte
    rows = list(csv.reader(open(os.path.join(rd, 'nap_ten_goc.csv'), encoding='utf-8-sig')))
    assert rows[0] == ['ten_goc', 'ten_moi', 'bytes', 'sha256'] and rows[1][:2] == ['Ảnh mặt.JPG', 'Anh_mat.jpg']
    assert not os.path.exists(src)                                         # bản tạm đã xoá
    assert sorted(os.listdir(runs)) == ['F5', 'NAP_001']
    plan2 = na.plan_upload([_img(tmp_path / 'u2' / 'b.png', 'PNG')])
    for name in ('NAP_001', 'nap_001'):                                    # lượt đã có (kể cả khác hoa thường)
        with pytest.raises(na.RunError):
            na.stage_upload(runs, name, plan2)
    assert os.listdir(os.path.join(rd, 'inbox')) == ['Anh_mat.jpg']        # lượt cũ không bị ghi thêm
    with pytest.raises(na.RunError):
        na.stage_upload(runs, 'NAP_002', dict(ok=[], rejected=[]))
    assert not os.path.exists(os.path.join(runs, 'NAP_002'))
    plan2['ok'][0]['sha256'] = '0' * 64                                    # file đổi giữa lúc kiểm và lúc chép
    with pytest.raises(na.RunError):
        na.stage_upload(runs, 'NAP_003', plan2)
    assert not os.path.exists(os.path.join(runs, 'NAP_003'))               # lượt dở tự dọn
    plan2['ok'][0]['sha256'] = na._sha256(plan2['ok'][0]['src'])
    plan2['ok'][0]['stem'] = '../../thoat'                                 # tên đích thoát khỏi lượt: từ chối
    with pytest.raises(na.RunError):
        na.stage_upload(runs, 'NAP_004', plan2)
    assert not os.path.exists(os.path.join(tmp_path, 'thoat.png')) and not os.path.exists(os.path.join(runs, 'NAP_004'))


def test_prepare_cmd_and_child_env():
    cmd = na.prepare_cmd('NAP_001', tool_dir='T', python='py')
    assert cmd == ['py', '-u', os.path.join('T', 'm28.py'), 'prepare', '--run', 'NAP_001', '--images',
                   os.path.join('runs', 'NAP_001', 'inbox'), '--box', 'auto']
    assert all(isinstance(c, str) for c in cmd)
    base = {'PATH': 'x'}
    env = na.child_env(base)
    assert env['PYTHONUTF8'] == '1' and env['PYTHONIOENCODING'] == 'utf-8' and env['PYTHONUNBUFFERED'] == '1' and env['PATH'] == 'x'
    assert base == {'PATH': 'x'}                                           # không sửa bản gốc


def test_preflight(tmp_path):
    root, tool = tmp_path / 'p', tmp_path / 'tool'
    tool.mkdir()
    (root / 'config').mkdir(parents=True)
    errs = na.preflight(str(root), str(tool))
    assert any('m28_config.json' in e for e in errs) and any('map_mp50.json' in e for e in errs)
    assert any('face_landmarker.task' in e and 'curl' in e for e in errs)
    for f in ('m28_config.json', 'map_mp50.json'):
        (root / 'config' / f).write_text('{}')
    (tool / 'face_landmarker.task').write_bytes(b'x')                       # model ở tool/ cũng được
    errs = na.preflight(str(root), str(tool))
    assert not any('face_landmarker' in e or 'config' in e for e in errs)
    (root / 'face_landmarker.task').write_bytes(b'x')
    (tool / 'face_landmarker.task').unlink()
    assert not any('face_landmarker' in e for e in na.preflight(str(root), str(tool)))
    os.remove(root / 'config' / 'map_mp50.json')
    assert any('map_mp50.json' in e for e in na.preflight(str(root), str(tool)))


def test_parse_progress():
    lines = ['WARNING: noise', 'crop: 5 mặt, 1 không dùng được', 'bỏ qua mediapipe', 'map50: 5 mặt']
    p = na.parse_progress(lines, 6, None)
    assert p['done'] == 3 and p['current'] == 'flags' and p['label'] == 'Bước 4/6 · flags' and abs(p['frac'] - 0.5) < 1e-9
    assert na.parse_progress([], 10, None)['label'] == 'Đang nạp MediaPipe…'
    p = na.parse_progress([], 10, 4)
    assert p['label'] == 'Bước 1/6 · crop (4/10 ảnh)' and 0 < p['frac'] < 1 / 6
    full = ['crop: 1 mặt', 'mediapipe: 1', 'map50: 1', 'flags: tb', 'autoqc: 0/1', 'overlays: 1 ảnh chồng']
    assert na.parse_progress(full)['label'] == 'Xong 6/6 bước' and na.parse_progress(full)['frac'] == 1
    assert na.parse_progress(['bỏ qua crop'] * 2)['done'] == 1


def test_prepare_list_matches_m28():
    code = "import sys; sys.path.insert(0, %r); import m28, nap_anh; print(m28.PREPARE == nap_anh.PREPARE)" % TOOL
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8')
    assert r.stdout.strip() == 'True', r.stderr
    from m28core import steps as st
    assert na.MODEL_URL == st.MODEL_URL and na.NO_FACE_VI == {'khong_thay_mat': 'MediaPipe không thấy mặt', 'khong_doc_duoc_anh': 'không đọc được ảnh'}


def test_read_prepare_result(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rd = make_run(tmp_path, {'a': 0, 'b': 3}, no_face=[('x', 'khong_thay_mat', 'crop'), ('y', 'khong_thay_mat', 'mediapipe'),
                                                    ('z', 'khong_doc_duoc_anh', 'crop')], crops=['y', 'a', 'b'])
    os.makedirs(os.path.join(rd, 'inbox'))
    for n in ('a', 'b', 'x', 'y', 'z'):
        open(os.path.join(rd, 'inbox', n + '.jpg'), 'wb').write(b'x')
    with open(os.path.join(rd, 'nap_ten_goc.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        f.write('ten_goc,ten_moi,bytes,sha256\nẢnh x.JPG,x.jpg,1,0\n')
    with open(os.path.join(rd, 'log.txt'), 'w', encoding='utf-8') as f:
        f.write('t\tcrop\txong\t1s\nt\tmediapipe\tbo_qua\t0s\nt\tmap50\tloi\t0s\n')
    res = na.read_prepare_result(rd)
    assert res['n_inbox'] == 5 and res['n_faces'] == 2 and res['n_queue'] == 3          # a, b + y (không nháp, có ảnh cắt)
    assert [r['name'] for r in res['no_draft']] == ['y'] and sorted(r['name'] for r in res['no_crop']) == ['x', 'z']
    assert next(r for r in res['no_crop'] if r['name'] == 'x')['orig'] == 'Ảnh x.JPG'
    assert next(r for r in res['no_crop'] if r['name'] == 'z')['reason'] == 'không đọc được ảnh'
    assert res['steps']['crop'] == 'xong' and res['steps']['map50'] == 'loi' and res['steps']['flags'] is None
    h = na.summary_html(res, 'P2')
    assert 'Mặt dùng được' in h and 'Ảnh x.JPG' in h and 'mặt lớn nhất' in h and 'm28.py push --run ' + res['run'] + ' --task demo-' in h
    assert '<script' not in na.summary_html(dict(res, no_crop=[dict(name='q', orig='<script>x</script>', reason='r', step='crop')]), 'P2')


def _job_code(body):
    return [sys.executable, '-c', body]


def _make_job(tmp_path, body):
    runs = tmp_path / 'runs'
    (runs / 'NAP_001' / 'inbox').mkdir(parents=True, exist_ok=True)
    job = na.PrepareJob(popen=lambda cmd, **kw: subprocess.Popen(_job_code(body), **kw))
    return job, str(runs)


def _wait(job, timeout=15):
    t = time.time()
    while job.running and time.time() - t < timeout:
        time.sleep(0.05)


def test_prepare_job_success_failure_cancel(tmp_path):
    job, runs = _make_job(tmp_path, "print('crop: 2 mặt, 0 không dùng được'); print('bỏ qua mediapipe')")
    job.start('NAP_001', runs, str(tmp_path))
    _wait(job)
    snap = job.snapshot()
    assert snap['state'] == 'xong' and snap['returncode'] == 0 and snap['lines'][0].startswith('crop: 2 mặt')
    log = open(os.path.join(runs, 'NAP_001', 'nap_log.txt'), encoding='utf-8').read()
    assert 'bỏ qua mediapipe' in log and log.startswith('===')
    job, runs = _make_job(tmp_path, "import sys; print('lỗi giả'); sys.exit(1)")
    job.start('NAP_001', runs, str(tmp_path))
    _wait(job)
    assert job.snapshot()['state'] == 'loi' and job.snapshot()['returncode'] == 1
    job, runs = _make_job(tmp_path, "import time; print('bắt đầu', flush=True); time.sleep(60)")
    job.start('NAP_001', runs, str(tmp_path))
    with pytest.raises(na.RunError):                                       # job đang chạy: start lần hai bị từ chối
        job.start('NAP_001', runs, str(tmp_path))
    t = time.time()
    assert job.cancel() is True
    assert time.time() - t < 10 and job.snapshot()['state'] == 'da_huy'
    assert job.cancel() is False
    job._popen = lambda cmd, **kw: subprocess.Popen(_job_code("print('crop: 1 mặt')"), **kw)
    job.start('NAP_001', runs, str(tmp_path))                              # Thử lại sau khi huỷ
    _wait(job)
    assert job.snapshot()['state'] == 'xong'
    with pytest.raises(na.RunError):
        job.start('NAP_999', runs, str(tmp_path))                          # lượt không có inbox


def test_job_receives_utf8_env_and_cmd(tmp_path):
    seen = {}

    def fake(cmd, **kw):
        seen.update(cmd=cmd, **kw)
        return subprocess.Popen(_job_code("import os; print(os.environ['PYTHONUTF8'], os.environ['PYTHONIOENCODING'])"), **kw)
    runs = tmp_path / 'runs'
    (runs / 'R' / 'inbox').mkdir(parents=True)
    job = na.PrepareJob(popen=fake)
    job.start('R', str(runs), str(tmp_path))
    _wait(job)
    assert seen['cwd'] == str(tmp_path) and seen['stdin'] == subprocess.DEVNULL and seen['stderr'] == subprocess.STDOUT
    assert 'shell' not in seen and seen['cmd'][-2:] == ['--box', 'auto'] and job.snapshot()['lines'] == ['1 utf-8']


def test_runs_layout(tmp_path):
    runs, root, err = na.runs_layout(str(tmp_path / 'runs' / 'F5'))
    assert err is None and root == str(tmp_path) and runs == str(tmp_path / 'runs')
    assert na.runs_layout(str(tmp_path / 'x' / 'F5'))[2]


def test_page_js_only_in_review_tab():
    js = ra.PAGE_JS
    assert "document.getElementById('main')" in js and 'offsetParent === null' in js
    assert js.index("getElementById('main')") < js.index('e.repeat')          # điều kiện tab nằm đầu handler
    assert 'fetch' not in js


def test_nap_modules_static(tmp_path):
    src = open(os.path.join(TOOL, 'nap_anh.py'), encoding='utf-8').read()
    lines = src.splitlines()
    assert 'shell=True' not in src and 'share=True' not in src
    assert not any(l.startswith(('import gradio', 'from gradio', 'import torch', 'from torch', 'import mediapipe', 'import cv2', 'from PIL', 'import PIL'))
                   for l in lines)
    code = ("import sys\nsys.path.insert(0, %r)\nimport nap_anh\nfor m in ('gradio', 'torch', 'mediapipe', 'cv2', 'PIL'):\n"
            "    assert m not in sys.modules, m\nprint('ok')\n") % TOOL
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0 and 'ok' in r.stdout, r.stderr
    app = open(os.path.join(TOOL, 'review_app.py'), encoding='utf-8').read()
    assert 'shell=True' not in app and 'max_file_size="25mb"' in app and 'concurrency_id="nap"' in app
    assert 'concurrency_id="m28"' in app and '"nap_tick"' in app and '"nap_huy"' in app
    assert 'allowed_paths=[os.path.abspath(os.path.join(run_dir, "inbox"' not in app and '"inbox"' not in app.split('allowed = ')[1].split('\n')[0]


def test_parse_argv():
    assert ra.parse_argv(['--nap', 'P2']) == ('nap', None, 'P2')
    assert ra.parse_argv(['runs/F5', 'P2']) == ('run', 'runs/F5', 'P2')
    assert ra.parse_argv(['--nap']) is None and ra.parse_argv([]) is None and ra.parse_argv(['a', 'b', 'c']) is None
    assert '--nap' in ra.VI_USAGE


def test_cli_nap_without_name_exits_2(tmp_path):
    r = run_app(tmp_path, '--nap')
    assert r.returncode == 2 and 'Cách dùng' in r.stderr and 'Traceback' not in r.stderr
    r = run_app(tmp_path, '--nap', '../x')
    assert r.returncode == 2 and 'không hợp lệ' in r.stderr and not os.path.exists(os.path.join(tmp_path, 'runs'))


def test_xong_reloads_page_once_and_new_session_sees_done(five):
    """Xong ghi done.txt rồi trang tải lại (JS); phiên mới sau tải lại phải thấy dải xanh; JS chỉ tải lại khi lần bấm này vừa ghi done.txt."""
    need_pil()
    src = open(os.path.join(TOOL, 'review_app.py'), encoding='utf-8').read()
    assert 'events[8].then(None, None, None, js=XONG_RELOAD_JS)' in src and 'b_xong.click(on_xong' in src
    js = ra.XONG_RELOAD_JS
    assert 'location.reload()' in js and "'done.txt'" in js and '.m28-done-bar' in js          # điều kiện chống vòng lặp
    assert js.count('location.reload()') == 1
    s = ra.Store(five, 'P2', clock=FakeClock())
    decide_all(s)
    ra.act_finish(s, ra.new_session(s))
    fresh = ra.new_session(s)                                          # phiên mới sau tải lại
    v = ra.make_view(s, fresh)
    assert 'm28-done-bar' in v['header'] and not v['nhan_ok'] and v['msg'] == ''     # không có 'done.txt' trong #msg -> JS không tải lại nữa
    s2 = ra.Store(five, 'P2', clock=FakeClock())                       # lượt đã có done.txt từ trước: không bar, không tải lại
    assert 'm28-done-bar' not in ra.make_view(s2, ra.new_session(s2))['header']


# ---------- 10. màu theo nhóm (QĐ-004): ảnh chồng trên trang giống màu label trên CVAT ----------
CFG_NAMES = [pt['name'] for pt in json.load(open(os.path.join(TOOL, '..', 'config', 'm28_config.json'), encoding='utf-8'))['points']]
GRP_PTS = [(30 + 45 * (i % 10), 40 + 80 * (i // 10)) for i in range(N_PTS)]       # cách nhau 45 px: vòng chấm không đè nhau
BG = (120, 130, 140)


def grouped_run(tmp_path, overlay=None, mtime_shift=None):
    """Lượt có tên điểm version 3 trong mp50.json (nhóm đọc được từ tên), ảnh cắt 512 xám, 3 điểm đầu low_conf.
    overlay: None (không có file) hay màu RGB của một ảnh chồng đã có; mtime_shift: giây lệch so với giờ sửa của mau_nhom.py (âm = ảnh chồng cũ hơn)."""
    pytest.importorskip('PIL')
    from PIL import Image
    rd = make_run(tmp_path, {'A': 3}, autoqc={'A': ('can_xem', [])})
    os.makedirs(os.path.join(rd, 'crop', 'images'))
    Image.new('RGB', (512, 512), BG).save(os.path.join(rd, 'crop', 'images', 'A.png'))
    os.makedirs(os.path.join(rd, 'map50'))
    with open(os.path.join(rd, 'map50', 'mp50.json'), 'w', encoding='utf-8') as f:
        json.dump({'A': {'orig': {n: list(pt) for n, pt in zip(CFG_NAMES, GRP_PTS)}, 'flip': None}}, f)
    if overlay is not None:
        os.makedirs(os.path.join(rd, 'overlays'))
        op = os.path.join(rd, 'overlays', 'A.png')
        Image.new('RGB', (512, 512), overlay).save(op)
        t = ra._style_mtime() + mtime_shift
        os.utime(op, (t, t))
    return rd


def px(path, i, dx=0):
    from PIL import Image
    return Image.open(path).convert('RGB').getpixel((GRP_PTS[i][0] + dx, GRP_PTS[i][1]))


def test_redraw_paints_group_colors_and_marks_low_conf_with_a_white_ring(tmp_path, monkeypatch):
    from m28core import mau_nhom
    monkeypatch.chdir(tmp_path)
    rd = grouped_run(tmp_path)
    path, warn = ra.overlay_for(ra.load_queue(rd)[0], rd)
    assert path == os.path.join(rd, '_tmp', 'overlays', 'A.png') and 'vẽ lại' in warn           # không có file ảnh chồng: vẽ lại tạm, kèm cảnh báo cũ
    want = {i: mau_nhom.hex_rgb(mau_nhom.GROUP_COLOR[mau_nhom.group_of(CFG_NAMES[i])]) for i in range(N_PTS)}
    assert px(path, 3) == (0xe7, 0x4c, 0x3c) == want[3]                                         # longmaytrai_4 ổn: đỏ của nhóm
    assert px(path, 5) == (0x34, 0x98, 0xdb) == want[5]                                         # longmayphai_1: xanh dương
    assert px(path, 12) == (0x2e, 0xcc, 0x71) == want[12]                                       # songmui_3: xanh lá
    assert px(path, 20) == want[20] and px(path, 40) == want[40]                                # mắt và môi theo nhóm
    assert len({want[i] for i in range(N_PTS)}) == 7                                            # bảy màu khác nhau
    for i in range(3):                                                                          # 3 điểm đầu low_conf: vẫn màu nhóm ở giữa, vòng trắng bên ngoài
        assert px(path, i) == want[i]
        assert px(path, i, dx=mau_nhom.R_LOW + 1) == (255, 255, 255)
    assert px(path, 3, dx=mau_nhom.R_OK + 2) == BG                                              # chấm ổn nhỏ, không có vòng
    assert px(path, 3, dx=mau_nhom.R_OK + 1) == mau_nhom.DARK                                   # chỉ một viền tối mảnh


def test_page_recolors_an_old_style_overlay_without_a_warning_and_keeps_the_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rd = grouped_run(tmp_path, overlay=(10, 20, 30), mtime_shift=-3600)                         # ảnh chồng chuẩn bị TRƯỚC khi có màu nhóm
    face = ra.load_queue(rd)[0]
    before = open(os.path.join(rd, 'overlays', 'A.png'), 'rb').read()
    path, warn = ra.overlay_for(face, rd)
    assert path == os.path.join(rd, '_tmp', 'overlays', 'A.png') and warn is None
    assert px(path, 5) == (0x34, 0x98, 0xdb)
    assert open(os.path.join(rd, 'overlays', 'A.png'), 'rb').read() == before                   # không ghi đè file gốc
    m = os.path.getmtime(path)
    assert ra.overlay_for(face, rd)[0] == path and os.path.getmtime(path) == m                  # cache
    thumb = ra.thumb_for(face, 'nhan', rd)
    assert os.path.isfile(thumb)


def test_page_keeps_an_overlay_that_is_already_new(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rd = grouped_run(tmp_path, overlay=(10, 20, 30), mtime_shift=+3600)
    path, warn = ra.overlay_for(ra.load_queue(rd)[0], rd)
    assert path == os.path.join(rd, 'overlays', 'A.png') and warn is None


def test_page_keeps_an_old_overlay_of_a_run_with_old_point_names(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rd, _ = fake_run_with_images(tmp_path, with_overlay=True)                                   # mp50.json tên p01…: không có nhóm để tô
    op = os.path.join(rd, 'overlays', 'A.png')
    os.utime(op, (1_000_000_000, 1_000_000_000))
    path, warn = ra.overlay_for(ra.load_queue(rd)[0], rd)
    assert path == op and warn is None


def test_legend_lists_the_seven_group_colors_and_the_low_conf_marker():
    from m28core import mau_nhom
    h = ra.LEGEND_HTML
    for g, c in mau_nhom.GROUP_COLOR.items():
        assert c in h and mau_nhom.GROUP_VI[g] in h
    assert 'low_conf' in h and 'vòng trắng' in h and 'chấm đỏ' not in h and 'chấm xanh' not in h


def test_nap_anh_auto_open_action():
    import nap_anh
    act = nap_anh.auto_open_action
    assert act(None, dict(run='A', state='xong')) == 'none' and act('', {}) == 'none'
    assert act('A', dict(run='A', state='dang_chay')) == 'wait'
    assert act('A', dict(run='A', state='xong')) == 'go'
    assert act('A', dict(run='A', state='loi')) == 'drop' and act('A', dict(run='A', state='da_huy')) == 'drop'
    assert act('A', dict(run='B', state='xong')) == 'drop' and act('A', dict(run='B', state='dang_chay')) == 'drop'    # job đã sang lượt khác
    assert act('A', dict(state='chua')) == 'drop'

