"""Thử tab "Các đợt", xoá mềm, thùng rác, nút Đẩy lên CVAT và PushJob/DeleteTaskJob (logic thuần, không trình duyệt, không mạng).

Phần Gradio (modal, lưới, phím Esc, ảnh chụp) kiểm riêng bằng tests/e2e_dot_push.py (tuỳ chọn, cần Playwright).
"""
import csv
import json
import os
import subprocess
import sys
import threading
import time

import pytest

TOOL = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tool'))
sys.path.insert(0, TOOL)
import day_cvat  # noqa: E402
import dot_anh  # noqa: E402
import dot_ui  # noqa: E402
import nap_anh as na  # noqa: E402
import review_app as ra  # noqa: E402
from m28core import dang_chay, loai_tru, phan_loai  # noqa: E402

PIL = pytest.importorskip('PIL')
from PIL import Image  # noqa: E402

NAMES = [f'a{i}' for i in range(1, 7)]           # a1..a6; a6 không có nháp (no_face mediapipe, có ảnh cắt)
TOKEN = 'TOKEN-GIA-zq81xk-DAY-LA-CHUOI-NHAN-DIEN'


def jpg(path, color=(120, 150, 200), size=(80, 60)):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.new('RGB', size, color).save(path, format='JPEG')


def make_dot_run(root, run='Khoi', names=NAMES, reviewer='P2', decisions=None, note='', inbox=True, date='2026-10-06T09:30:00', no_draft=('a6',),
                 unusable=('a7',), push=None, done=False):
    """Đợt nạp đầy đủ: inbox, crop, overlays, flags/meta/mp50, no_face, triage, dot.json. Trả đường dẫn runs/<run>."""
    root = str(root)
    rd = os.path.join(root, 'runs', run)
    os.makedirs(rd, exist_ok=True)
    flags, meta, mp50 = {}, {}, {}
    for n in names:
        if inbox:
            jpg(os.path.join(rd, 'inbox', n + '.jpg'))
        jpg(os.path.join(rd, 'crop', 'images', n + '.png'))
        os.makedirs(os.path.join(rd, 'overlays'), exist_ok=True)
        jpg(os.path.join(rd, 'overlays', n + '.png'))
        meta[n] = dict(src=os.path.abspath(os.path.join(rd, 'inbox', n + '.jpg')), rel=n + '.jpg', left=0, top=0, k=1, w=80, h=60)
        if n not in no_draft:
            flags[n] = [False] * 50
            mp50[n] = dict(orig={f'p{i}': [1, 1] for i in range(50)}, flip=None)
    for sub, d in (('flags', flags), ('crop', meta), ('map50', mp50)):
        os.makedirs(os.path.join(rd, sub), exist_ok=True)
        json.dump(d, open(os.path.join(rd, sub, {'flags': 'flags.json', 'crop': 'meta.json', 'map50': 'mp50.json'}[sub]), 'w'))
    with open(os.path.join(rd, 'crop', 'box.txt'), 'w') as f:
        f.write('auto')
    nf = [(n, 'khong_thay_mat', 'mediapipe') for n in no_draft]
    for n in unusable:
        if inbox:
            jpg(os.path.join(rd, 'inbox', n + '.jpg'))
        nf.append((n, 'khong_doc_duoc_anh', 'crop'))
    with open(os.path.join(rd, 'no_face.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['name', 'reason', 'step'])
        w.writerows(nf)
    if inbox:
        with open(os.path.join(rd, 'nap_ten_goc.csv'), 'w', encoding='utf-8-sig', newline='') as f:
            f.write('ten_goc,ten_moi,bytes,sha256\n' + ''.join(f'Ảnh {n}.JPG,{n}.jpg,1,0\n' for n in list(names) + list(unusable)))
    if date:
        json.dump(dict(ten=run, ngay_nap=date, ghi_chu=note, nguoi_nap=reviewer, so_anh=len(names)), open(os.path.join(rd, 'dot.json'), 'w'))
    if decisions:
        os.makedirs(os.path.join(rd, 'review'), exist_ok=True)
        with open(os.path.join(rd, 'review', f'triage_{reviewer}.csv'), 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['name', 'decision', 'reason', 'seconds'])
            for n, d in decisions.items():
                w.writerow([n + '.png', d, '', ''])
        if done:
            open(os.path.join(rd, 'review', 'done.txt'), 'w').write('xong')
    if push:
        json.dump(push, open(os.path.join(rd, 'push.json'), 'w'))
    return rd


ALL_DECIDED = {'a1': 'nhan', 'a2': 'nhan', 'a3': 'gan_tay', 'a4': 'bo', 'a5': 'nhan', 'a6': 'gan_tay'}


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for v in ('CVAT_URL', 'CVAT_ACCESS_TOKEN', 'CVAT_ORG'):
        monkeypatch.delenv(v, raising=False)
    os.makedirs('config')
    json.dump(dict(project='m28', prefix='demo-', cvat_version='2.77.0', job_size=4), open('config/pipeline.json', 'w'))
    return tmp_path


def runs_root(root):
    return os.path.join(str(root), 'runs')


# ---------- loai_tru ----------
def test_loai_tru_read_add_remove(tmp_path):
    rd = str(tmp_path / 'r')
    assert loai_tru.read_excluded(rd) == set()
    loai_tru.add(rd, ['a', 'b.png', ' c.jpg '])
    assert loai_tru.read_excluded(rd) == {'a', 'b', 'c'}
    txt = open(loai_tru.path(rd), encoding='utf-8').read()
    assert txt.splitlines()[0].startswith('#') and 'a\n' in txt
    loai_tru.remove(rd, ['b'])
    assert loai_tru.read_excluded(rd) == {'a', 'c'}
    open(loai_tru.path(rd), 'a', encoding='utf-8').write('# ghi chú\n\n  \nd\n')
    assert loai_tru.read_excluded(rd) == {'a', 'c', 'd'}
    assert not [f for f in os.listdir(rd) if '.tmp' in f or f.endswith('.lock')]


def test_loai_tru_concurrent_adds_lose_nothing(tmp_path):
    rd = str(tmp_path / 'r')
    ts = [threading.Thread(target=loai_tru.add, args=(rd, [f'n{i}'])) for i in range(30)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert loai_tru.read_excluded(rd) == {f'n{i}' for i in range(30)}


# ---------- danh sách đợt, thẻ ----------
def test_list_runs_skips_underscore_and_non_runs_newest_first(world):
    make_dot_run(world, 'Cu', date='2026-10-01T08:00:00')
    make_dot_run(world, 'Moi', date='2026-10-05T08:00:00')
    for junk in ('_nap', '_trash', 'khong_phai'):
        os.makedirs(os.path.join('runs', junk, 'x'))
    os.makedirs('runs/_nap/inbox')                                  # có inbox nhưng tên bắt đầu _ : không phải đợt
    open('runs/file.txt', 'w').write('x')
    assert dot_anh.list_runs('runs') == ['Moi', 'Cu']
    assert dot_anh.list_runs(str(world / 'khong_co')) == []


def test_run_info_counts_note_and_other_reviewers(world):
    rd = make_dot_run(world, 'Khoi', decisions={'a1': 'nhan', 'a2': 'gan_tay', 'a3': 'bo'}, note='ảnh <b>sáng</b>')
    os.makedirs(os.path.join(rd, 'review'), exist_ok=True)
    open(os.path.join(rd, 'review', 'triage_P5.csv'), 'w').write('name,decision\na1.png,nhan\n')
    i = dot_anh.run_info(rd, 'P2')
    assert (i['nhan'], i['gan_tay'], i['bo'], i['chua_ra']) == (1, 1, 1, 3) and i['khong_dung_duoc'] == 1 and i['total'] == 6
    assert i['so_anh'] == 7 and i['nguoi_khac'] == ['P5'] and i['trash'] == 0 and i['ghi_chu'] == 'ảnh <b>sáng</b>'
    assert dot_anh.run_info(rd, 'P5')['nhan'] == 1 and dot_anh.run_info(rd, 'P9')['chua_ra'] == 6
    h = dot_anh.card_html(i)
    assert '&lt;b&gt;sáng&lt;/b&gt;' in h and '<b>sáng</b>' not in h and 'có kết quả của P5' in h and 'data-act="ra"' in h


def test_counts_subtract_soft_deleted(world):
    rd = make_dot_run(world, 'Khoi', decisions={'a1': 'nhan', 'a2': 'nhan'})
    dot_anh.soft_delete_image(rd, 'a1', reviewer='P2', decision='nhan')
    dot_anh.soft_delete_image(rd, 'a6')
    i = dot_anh.run_info(rd, 'P2')
    assert (i['nhan'], i['total'], i['chua_ra'], i['trash'], i['so_anh']) == (1, 4, 3, 2, 5)


@pytest.mark.parametrize('kw, expect', [
    (dict(decisions=ALL_DECIDED, done=True), ('da_xong', 'Đã Xong')),
    (dict(decisions=ALL_DECIDED), ('dang_ra', 'Đang rà')),
    (dict(decisions={'a1': 'nhan'}), ('dang_ra', 'Đang rà')),
    (dict(), ('chua_ra', 'Chưa rà')),
    (dict(push=dict(trang_thai='xong', task='demo-Khoi', task_id=7), decisions=ALL_DECIDED, done=True), ('da_day', 'Đã đẩy CVAT: demo-Khoi (id 7)')),
    (dict(push=dict(trang_thai='da_tao', task='demo-Khoi', task_id=7)), ('day_do', 'Đẩy dở: đã tạo task, chưa nhập nhãn')),
    (dict(push=dict(trang_thai='dang_tao', task='demo-Khoi')), ('day_do', 'Đẩy dở: đang tạo task, chưa có id')),
    (dict(push=dict(trang_thai='task_deleted', task='demo-Khoi', task_id=7), decisions=ALL_DECIDED, done=True), ('da_xong', 'Đã Xong')),
])
def test_run_state(world, kw, expect):
    rd = make_dot_run(world, 'Khoi', **kw)
    i = dot_anh.run_info(rd, 'P2')
    assert (i['state'], i['state_text']) == expect


def test_run_state_not_prepared_and_busy(world, monkeypatch):
    rd = make_dot_run(world, 'Khoi')
    os.remove(os.path.join(rd, 'flags', 'flags.json'))
    assert dot_anh.run_info(rd, 'P2')['state_text'] == 'Chưa prepare xong'
    rd = make_dot_run(world, 'Nam')
    for kind, text in (('prepare', 'Đang chuẩn bị'), ('push', 'Đang đẩy lên CVAT'), ('xoa_task', 'Đang xoá task trên CVAT')):
        assert dang_chay.acquire(rd, kind)
        assert dot_anh.run_info(rd, 'P2')['state_text'] == text
        dang_chay.release(rd)
    assert dot_anh.run_info(rd, 'P2')['state_text'] == 'Chưa rà'


def test_old_run_without_dot_json_uses_log_then_mtime(world):
    rd = make_dot_run(world, 'Cu', date=None)
    assert dot_anh.run_date(rd) != '' and dot_anh.read_dot(rd) == {}
    open(os.path.join(rd, 'log.txt'), 'w', encoding='utf-8').write('2026-09-30 10:15:00\tcrop\txong\t1.0s\n')
    assert dot_anh.run_date(rd) == '2026-09-30T10:15:00' and dot_anh.fmt_date(dot_anh.run_date(rd)) == '30/09/2026 10:15'
    assert dot_anh.run_info(rd, 'P2')['ghi_chu'] == ''


def test_run_without_inbox_counts_crops(world):
    rd = make_dot_run(world, 'F5', inbox=False, unusable=())
    i = dot_anh.run_info(rd, 'P2')
    assert i['so_anh'] == 6 and dot_anh.image_names(rd) == NAMES
    assert dot_anh.image_source(rd, 'a1').endswith(os.path.join('crop', 'images', 'a1.png'))


# ---------- lưới ảnh ----------
def test_image_rows_status_and_original_names(world):
    rd = make_dot_run(world, 'Khoi', decisions={'a1': 'nhan', 'a2': 'bo', 'a3': 'gan_tay'})
    rows = {r['name']: r for r in dot_anh.image_rows(rd, 'P2')}
    assert [r for r in rows] == ['a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7']
    assert rows['a1']['status_text'] == 'Nhận' and rows['a2']['status_text'] == 'Bỏ' and rows['a3']['status_text'] == 'Gán tay'
    assert rows['a4']['status_text'] == 'Chưa rà' and rows['a6']['status_text'] == 'Không thấy mặt' and rows['a7']['status_text'] == 'Không dùng được'
    assert rows['a1']['orig'] == 'Ảnh a1.JPG' and rows['a1']['src'].endswith('inbox' + os.sep + 'a1.jpg')


def test_natural_sort_and_paging(world):
    names = [f'img{i}' for i in (1, 2, 10, 11, 3)]
    rd = make_dot_run(world, 'Khoi', names=names, no_draft=(), unusable=())
    assert dot_anh.image_names(rd) == ['img1', 'img2', 'img3', 'img10', 'img11']
    items, page, n = dot_anh.page_slice(list(range(50)), 1, 24)
    assert items == list(range(24, 48)) and page == 1 and n == 3
    assert dot_anh.page_slice(list(range(50)), 99, 24)[1:] == (2, 3) and dot_anh.page_slice([], 5)[1:] == (0, 1)


def test_grid_uses_data_uri_and_never_original_path(world):
    rd = make_dot_run(world, 'Khoi', decisions={'a1': 'nhan'})
    info = dot_anh.run_info(rd, 'P2')
    h = dot_anh.grid_html(info, dot_anh.image_rows(rd, 'P2'), 0, [])
    assert h.count('src="data:image/jpeg;base64,') == 6 + 0 or 'data:image' in h
    assert 'inbox' not in h and rd not in h and 'file=' not in h and '/gradio_api' not in h
    assert 'aria-label="Delete image a1"' in h and 'class="dot-trash"' in h and 'data-act="delimg"' in h


def test_thumb_cache_and_placeholder(world, tmp_path):
    p = str(tmp_path / 'x.jpg')
    jpg(p, size=(400, 300))
    u1 = dot_anh.thumb_data_uri(p)
    assert u1.startswith('data:image/jpeg;base64,') and dot_anh.thumb_data_uri(p) is u1
    import base64
    import io
    im = Image.open(io.BytesIO(base64.b64decode(u1.split(',', 1)[1])))
    assert max(im.size) <= dot_anh.THUMB_PX
    assert dot_anh.thumb_data_uri(None) == dot_anh.thumb_data_uri(str(tmp_path / 'khong_co.jpg')) and 'svg' in dot_anh.thumb_data_uri(None)
    bad = str(tmp_path / 'bad.jpg')
    open(bad, 'wb').write(b'khong phai anh')
    assert 'svg' in dot_anh.thumb_data_uri(bad)


def test_thumb_applies_exif_orientation(world, tmp_path):
    p = str(tmp_path / 'e.jpg')
    im = Image.new('RGB', (200, 100), (10, 20, 30))
    exif = Image.Exif()
    exif[0x0112] = 6                                                # xoay 90 độ: ảnh hiển thị là 100x200
    im.save(p, format='JPEG', exif=exif)
    import base64
    import io
    out = Image.open(io.BytesIO(base64.b64decode(dot_anh.thumb_data_uri(p).split(',', 1)[1])))
    assert out.size[0] < out.size[1]


# ---------- xoá mềm / khôi phục / dọn ----------
def files_of(rd, n):
    return [p for p in (os.path.join(rd, 'inbox', n + '.jpg'), os.path.join(rd, 'crop', 'images', n + '.png'),
                        os.path.join(rd, 'overlays', n + '.png'))]


def test_soft_delete_moves_files_and_writes_manifest(world):
    rd = make_dot_run(world, 'Khoi', decisions={'a1': 'nhan'}, push=dict(trang_thai='xong', task='demo-Khoi', task_id=3))
    before = {f: open(os.path.join(rd, f), 'rb').read() for f in ('flags/flags.json', 'crop/meta.json', 'map50/mp50.json', 'no_face.csv',
                                                                   'review/triage_P2.csv')}
    man = dot_anh.soft_delete_image(rd, 'a1', reviewer='P2', decision='nhan', pushed_task='demo-Khoi')
    assert all(not os.path.exists(p) for p in files_of(rd, 'a1'))
    assert loai_tru.read_excluded(rd) == {'a1'}
    t = dot_anh.list_trash(rd)
    assert len(t) == 1 and t[0]['ten'] == 'a1' and t[0]['quyet_dinh'] == 'nhan' and t[0]['da_day_cvat'] and t[0]['task'] == 'demo-Khoi' and t[0]['n_files'] == 3
    folder = os.path.join(rd, '_trash', t[0]['folder'])
    m = json.load(open(os.path.join(folder, 'manifest.json'), encoding='utf-8'))
    assert m['nguoi_ra'] == 'P2' and {f['goc'] for f in m['files']} == {'inbox/a1.jpg', 'crop/images/a1.png', 'overlays/a1.png'}
    assert all(os.path.exists(os.path.join(folder, *f['thung_rac'].split('/'))) for f in m['files'])
    assert man['ten'] == 'a1' and 'a1' not in dot_anh.image_names(rd)
    after = {f: open(os.path.join(rd, f), 'rb').read() for f in before}
    assert after == before                                          # file kết quả KHÔNG bị sửa
    with pytest.raises(na.RunError, match='thùng rác'):
        dot_anh.soft_delete_image(rd, 'a1')


def test_soft_delete_orders_excluded_before_move(world, monkeypatch):
    rd = make_dot_run(world, 'Khoi')
    seen = []
    real = os.replace

    def spy(src, dst):
        if '_trash' in str(dst):                                    # chỉ tính các lần chuyển file vào thùng rác
            seen.append(set(loai_tru.read_excluded(rd)))
        return real(src, dst)
    monkeypatch.setattr(os, 'replace', spy)
    dot_anh.soft_delete_image(rd, 'a2')
    assert len(seen) >= 3 and all('a2' in s for s in seen)          # tên đã nằm trong excluded.txt trước mỗi lần chuyển file


def test_soft_delete_rolls_back_on_error(world, monkeypatch):
    rd = make_dot_run(world, 'Khoi')
    real = os.replace
    n = {'k': 0}

    def flaky(src, dst):
        n['k'] += 1
        if n['k'] == 2:
            raise OSError('đĩa đầy giả')
        return real(src, dst)
    monkeypatch.setattr(os, 'replace', flaky)
    with pytest.raises(na.RunError, match='hoàn lại'):
        dot_anh.soft_delete_image(rd, 'a2')
    monkeypatch.setattr(os, 'replace', real)
    assert all(os.path.exists(p) for p in files_of(rd, 'a2'))
    assert loai_tru.read_excluded(rd) == set() and dot_anh.list_trash(rd) == []
    assert not os.path.exists(os.path.join(rd, '_trash')) or os.listdir(os.path.join(rd, '_trash')) == []


def test_restore_returns_files_and_reopens_when_undecided(world):
    rd = make_dot_run(world, 'Khoi', decisions={n: 'nhan' for n in ('a1', 'a2', 'a3', 'a4', 'a5')} | {'a6': 'gan_tay'}, done=True)
    snap = {p: open(p, 'rb').read() for p in files_of(rd, 'a1')}
    dot_anh.soft_delete_image(rd, 'a1', reviewer='P2', decision='nhan')
    folder = dot_anh.list_trash(rd)[0]['folder']
    res = dot_anh.restore_image(rd, folder, reviewer='P2')
    assert res == dict(ten='a1', mo_lai=False)                      # a1 đã có quyết định: không mở lại
    assert {p: open(p, 'rb').read() for p in files_of(rd, 'a1')} == snap
    assert loai_tru.read_excluded(rd) == set() and dot_anh.list_trash(rd) == [] and not os.path.exists(os.path.join(rd, '_trash', folder))
    assert os.path.exists(os.path.join(rd, 'review', 'done.txt'))
    # mặt chưa có quyết định thì khôi phục xong lượt có lại mặt chưa rà: done.txt bị xoá
    rd2 = make_dot_run(world, 'Nam', decisions={'a1': 'nhan'}, done=True)
    dot_anh.soft_delete_image(rd2, 'a3')
    assert os.path.exists(os.path.join(rd2, 'review', 'done.txt'))
    res = dot_anh.restore_image(rd2, dot_anh.list_trash(rd2)[0]['folder'], reviewer='P2')
    assert res['mo_lai'] is True and not os.path.exists(os.path.join(rd2, 'review', 'done.txt'))


def test_restore_refuses_when_destination_exists_and_moves_nothing(world):
    rd = make_dot_run(world, 'Khoi')
    dot_anh.soft_delete_image(rd, 'a2')
    jpg(os.path.join(rd, 'crop', 'images', 'a2.png'))               # ai đó tạo lại file cùng tên
    item = dot_anh.list_trash(rd)[0]
    with pytest.raises(na.RunError, match='đã có file'):
        dot_anh.restore_image(rd, item['folder'])
    assert loai_tru.read_excluded(rd) == {'a2'} and len(dot_anh.list_trash(rd)) == 1
    assert not os.path.exists(os.path.join(rd, 'inbox', 'a2.jpg'))   # không chuyển file nào về khi một đích bị trùng


def test_restore_unknown_folder_and_tampered_manifest(world, tmp_path):
    rd = make_dot_run(world, 'Khoi')
    with pytest.raises(na.RunError):
        dot_anh.restore_image(rd, '20260101-000000_zzz')
    with pytest.raises(na.RunError):
        dot_anh.restore_image(rd, '../../etc')
    dot_anh.soft_delete_image(rd, 'a2')
    item = dot_anh.list_trash(rd)[0]
    mp = os.path.join(rd, '_trash', item['folder'], 'manifest.json')
    m = json.load(open(mp, encoding='utf-8'))
    m['files'][0]['goc'] = '../../ngoai.jpg'
    json.dump(m, open(mp, 'w'))
    with pytest.raises(na.RunError, match='ngoài'):
        dot_anh.restore_image(rd, item['folder'])
    assert not os.path.exists(str(tmp_path / 'ngoai.jpg'))


def test_empty_trash_only_touches_trash(world):
    rd = make_dot_run(world, 'Khoi')
    dot_anh.soft_delete_image(rd, 'a1')
    dot_anh.soft_delete_image(rd, 'a2')
    keep = {p for p in files_of(rd, 'a3')} | {os.path.join(rd, 'flags', 'flags.json'), os.path.join(rd, 'dot.json')}
    assert dot_anh.empty_trash(rd) == 2
    assert not os.path.exists(os.path.join(rd, '_trash')) and all(os.path.exists(p) for p in keep)
    assert loai_tru.read_excluded(rd) == {'a1', 'a2'}               # tên vẫn bị loại sau khi dọn
    assert dot_anh.empty_trash(rd) == 0


def test_empty_trash_refuses_symlinked_trash(world, tmp_path):
    rd = make_dot_run(world, 'Khoi')
    out = tmp_path / 'ngoai'
    out.mkdir()
    (out / 'giu.txt').write_text('x')
    os.symlink(str(out), os.path.join(rd, '_trash'))
    with pytest.raises(na.RunError):
        dot_anh.empty_trash(rd)
    assert (out / 'giu.txt').exists()


@pytest.mark.parametrize('bad', ['../x', '..', '.', '/etc/passwd', 'a/b', 'a\\b', '', 'C:\\Windows', 'a b', None, 5, 'x' * 100])
def test_path_traversal_names_rejected(world, bad):
    rd = make_dot_run(world, 'Khoi')
    with pytest.raises(na.RunError):
        dot_anh.soft_delete_image(rd, bad)
    assert loai_tru.read_excluded(rd) == set()
    with pytest.raises(na.RunError):
        dot_anh.valid_run('runs', bad)


def test_valid_run_only_from_server_list(world, tmp_path):
    make_dot_run(world, 'Khoi')
    os.makedirs('runs/_trash/zzz')
    assert dot_anh.valid_run('runs', 'Khoi').endswith('Khoi')
    for bad in ('_trash', '_nap', 'khong_co', 'Khoi/..', '../runs/Khoi', 'khoi ', 'KHOI'):
        with pytest.raises(na.RunError):
            dot_anh.valid_run('runs', bad)


def test_symlink_pointing_outside_is_refused(world, tmp_path):
    rd = make_dot_run(world, 'Khoi')
    secret = tmp_path / 'bi_mat.jpg'
    secret.write_bytes(b'bi mat')
    os.remove(os.path.join(rd, 'inbox', 'a3.jpg'))
    os.symlink(str(secret), os.path.join(rd, 'inbox', 'a3.jpg'))
    with pytest.raises(na.RunError, match='ngoài'):
        dot_anh.soft_delete_image(rd, 'a3')
    assert secret.read_bytes() == b'bi mat' and loai_tru.read_excluded(rd) == set()
    assert os.path.islink(os.path.join(rd, 'inbox', 'a3.jpg')) and os.path.exists(os.path.join(rd, 'crop', 'images', 'a3.png'))


def test_busy_run_blocks_delete_restore_empty(world, monkeypatch):
    rd = make_dot_run(world, 'Khoi')
    dot_anh.soft_delete_image(rd, 'a2')
    item = dot_anh.list_trash(rd)[0]
    assert dang_chay.acquire(rd, 'push')
    for fn in (lambda: dot_anh.soft_delete_image(rd, 'a3'), lambda: dot_anh.restore_image(rd, item['folder']),
               lambda: dot_anh.empty_trash(rd), lambda: dot_anh.delete_run('runs', 'Khoi', 'Khoi')):
        with pytest.raises(na.RunError, match='việc'):
            fn()
    dang_chay.release(rd)
    assert loai_tru.read_excluded(rd) == {'a2'} and os.path.isdir(rd)
    dot_anh.soft_delete_image(rd, 'a3')


# ---------- xoá cả đợt ----------
def test_delete_run_needs_exact_name_and_is_soft(world):
    rd = make_dot_run(world, 'Khoi')
    for typed in ('khoi', 'Khoi ', '', 'Nam'):
        with pytest.raises(na.RunError, match='gõ lại đúng tên'):
            dot_anh.delete_run('runs', 'Khoi', typed)
    assert os.path.isdir(rd)
    entry = dot_anh.delete_run('runs', 'Khoi', 'Khoi')
    assert not os.path.exists(rd) and os.path.isdir(os.path.join('runs', '_trash', entry)) and dot_anh.list_runs('runs') == []
    d = dot_anh.list_deleted_runs('runs')
    assert len(d) == 1 and d[0]['ten'] == 'Khoi' and d[0]['entry'] == entry
    assert dot_anh.restore_run('runs', entry) == 'Khoi'
    assert os.path.isdir(rd) and not os.path.exists(os.path.join(rd, 'xoa_dot.json')) and dot_anh.list_deleted_runs('runs') == []
    assert dot_anh.run_info(rd, 'P2')['so_anh'] == 7


def test_delete_run_refuses_active_busy_and_unknown(world):
    rd = make_dot_run(world, 'Khoi')
    with pytest.raises(na.RunError, match='đang mở'):
        dot_anh.delete_run('runs', 'Khoi', 'Khoi', active_run=rd)
    with pytest.raises(na.RunError, match='không có trong danh sách'):
        dot_anh.delete_run('runs', '_trash', '_trash')
    with pytest.raises(na.RunError):
        dot_anh.delete_run('runs', '../runs/Khoi', '../runs/Khoi')
    assert os.path.isdir(rd) and not os.path.exists('runs/_trash')


def test_restore_deleted_run_refused_when_name_reused_and_purge(world):
    make_dot_run(world, 'Khoi')
    entry = dot_anh.delete_run('runs', 'Khoi', 'Khoi')
    make_dot_run(world, 'khoi')                                     # tên dùng lại (không phân biệt hoa thường)
    with pytest.raises(na.RunError, match='dùng lại'):
        dot_anh.restore_run('runs', entry)
    assert dot_anh.purge_run('runs', entry) == 'Khoi'
    assert not os.path.exists(os.path.join('runs', '_trash', entry)) and os.path.isdir('runs/khoi')
    for bad in ('../khoi', 'khoi__20260101-000000', 'x'):
        with pytest.raises(na.RunError):
            dot_anh.purge_run('runs', bad)
    assert os.path.isdir('runs/khoi')


def test_new_run_names_skip_deleted_runs_and_trash_is_not_a_valid_name(world):
    make_dot_run(world, 'NAP_001')
    make_dot_run(world, 'NAP_002')
    assert na.next_run_name('runs') == 'NAP_003'
    dot_anh.delete_run('runs', 'NAP_002', 'NAP_002')
    assert na.next_run_name('runs') == 'NAP_003'                    # NAP_002 đã xoá mềm: không dùng lại tên (khôi phục còn được)
    for bad in ('_trash', '_nap', '__x'):
        with pytest.raises(na.RunError):
            na.check_run_name(bad, 'runs')


# ---------- yêu cầu chờ xác nhận ----------
def test_pending_token_one_shot_stale_and_replaced():
    t = {'now': 0.0}
    p = dot_anh.Pending(clock=lambda: t['now'])
    a = p.open(kind='delimg', run='R', name='a1')
    assert p.take('sai') is None and p.item is None                 # mã sai: yêu cầu bị huỷ luôn
    a = p.open(kind='delimg', run='R', name='a1')
    b = p.open(kind='delimg', run='R', name='a2')                   # hộp mới thay hộp cũ
    assert p.take(a['token']) is None
    b = p.open(kind='delimg', run='R', name='a2')
    assert p.take(b['token'])['name'] == 'a2' and p.take(b['token']) is None      # dùng một lần
    c = p.open(kind='empty', run='R')
    t['now'] += dot_anh.TOKEN_TTL + 1
    assert p.take(c['token']) is None                               # quá hạn
    assert p.take(None) is None and p.take('') is None
    p.open(kind='x')
    p.cancel()
    assert p.item is None


# ---------- khớp với hàng đợi của review_app ----------
@pytest.mark.parametrize('with_excluded', [False, True])
def test_queue_names_equal_review_app_queue(world, with_excluded):
    rd = make_dot_run(world, 'Khoi')
    os.remove(os.path.join(rd, 'crop', 'images', 'a6.png'))         # a6: no_face không có ảnh cắt -> không vào hàng đợi
    if with_excluded:
        loai_tru.add(rd, ['a2', 'a7'])
    names, unusable = dot_anh.queue_names(rd)
    assert sorted(names) == sorted(f.name for f in ra.load_queue(rd))
    assert unusable == (2 if not with_excluded else 1)              # a6 và a7 (a7 bị xoá thì còn a6)


def test_review_app_load_and_store_respect_exclusion(world):
    rd = make_dot_run(world, 'Khoi', decisions={'a1': 'nhan'})
    loai_tru.add(rd, ['a2', 'a6'])
    assert sorted(f.name for f in ra.load_queue(rd)) == ['a1', 'a3', 'a4', 'a5']
    s = ra.Store(rd, 'P2')
    p = s.progress()
    assert (p['total'], p['done'], p['remaining']) == (4, 1, 3) and 'a2' not in s.by_name
    assert 'a2' in json.load(open(os.path.join(rd, 'flags', 'flags.json')))          # file kết quả không bị sửa


def test_store_exclude_and_reload(world):
    rd = make_dot_run(world, 'Khoi', decisions={'a1': 'nhan', 'a2': 'nhan'}, done=True)
    s = ra.Store(rd, 'P2')
    s.decide('a3', 'nhan')
    s.decide('a4', 'bo', 'MO_NHO')
    assert [u[0] for u in s.undo_stack] == ['a3', 'a4']
    loai_tru.add(rd, ['a3'])
    assert s.exclude('a3') is True and s.exclude('a3') is False and 'a3' not in s.by_name
    assert [u[0] for u in s.undo_stack] == ['a4']                    # hoàn tác của mặt đã xoá bị bỏ
    assert s.undo() == 'a4'
    p = s.progress()
    assert p['total'] == 5 and p['remaining'] == 3                   # a1 a2 a4 a5 a6 (a3 không còn tính); a1 a2 đã rà, a4 vừa hoàn tác
    # khôi phục: file về chỗ cũ, gỡ khỏi danh sách, Store.reload thấy lại
    loai_tru.remove(rd, ['a3'])
    s.reload()
    assert 'a3' in s.by_name and s.status('a3') == 'nhan'
    # không bao giờ làm hàng đợi rỗng
    rd2 = make_dot_run(world, 'Nam', names=['x1'], no_draft=(), unusable=())
    s2 = ra.Store(rd2, 'P2')
    with pytest.raises(ValueError):
        s2.exclude('x1')


def test_read_prepare_result_excludes(world):
    rd = make_dot_run(world, 'Khoi')
    loai_tru.add(rd, ['a2', 'a6', 'a7'])
    res = na.read_prepare_result(rd)
    assert res['n_faces'] == 4 and res['n_queue'] == 4 and not res['no_draft'] and not res['no_crop']


def test_stage_upload_writes_dot_json_and_cleans_note(tmp_path):
    runs = str(tmp_path / 'runs')
    src = tmp_path / 'in.jpg'
    jpg(str(src))
    plan = na.plan_upload([str(src)])
    note = '  Ảnh buổi sáng\x00\x07 <script>x</script>  ' + 'y' * 600
    rd = na.stage_upload(runs, 'Khoi', plan, note=note, reviewer='P4')
    d = json.load(open(os.path.join(rd, 'dot.json'), encoding='utf-8'))
    assert d['ten'] == 'Khoi' and d['nguoi_nap'] == 'P4' and d['so_anh'] == 1 and len(d['ghi_chu']) == na.NOTE_MAX
    assert d['ghi_chu'].startswith('Ảnh buổi sáng') and '\x00' not in d['ghi_chu']
    assert d['ngay_nap'][:4] == '2026' or len(d['ngay_nap']) >= 19
    rd2 = na.stage_upload(runs, 'Nam', na.plan_upload([str(src)]))                      # tham số mới là tuỳ chọn
    d2 = json.load(open(os.path.join(rd2, 'dot.json'), encoding='utf-8'))
    assert d2['ghi_chu'] == '' and d2['nguoi_nap'] == ''
    assert os.path.exists(os.path.join(rd, 'inbox', 'in.jpg')) and os.path.exists(os.path.join(rd, 'nap_ten_goc.csv'))
    assert '&lt;script&gt;' in dot_anh.card_html(dict(dot_anh.run_info(make_dot_run(tmp_path, 'Z'), 'P2'), ghi_chu=d['ghi_chu']))


# ---------- day_cvat: nút Đẩy ----------
def env_ok():
    return {'CVAT_URL': 'http://localhost:8080', 'CVAT_ACCESS_TOKEN': TOKEN}


def model(rd, rev='P2', remaining=None, env=None, job=False, root=None):
    return day_cvat.push_model(rd, rev, root or os.getcwd(), remaining=remaining, environ=env_ok() if env is None else env, job_running=job)


def test_push_button_enabled_only_when_everything_ready(world):
    rd = make_dot_run(world, 'Khoi', decisions=ALL_DECIDED, done=True)
    m = model(rd)
    assert m['kind'] == 'button' and m['enabled'] and m['task'] == 'demo-Khoi'
    assert (m['plan']['nhan'], m['plan']['tay'], m['plan']['bo'], m['plan']['jobs']) == (3, 2, 2, 2)      # a1 a2 a5 | a3 a6 | a4 a7 | 1 job Nhận + 1 Gán tay
    p = day_cvat.panel_html(m)
    assert 'Sẵn sàng đẩy' in p and TOKEN not in p


def test_push_button_locked_with_reasons(world):
    rd = make_dot_run(world, 'Khoi', decisions={'a1': 'nhan', 'a2': 'nhan'})
    m = model(rd)
    assert not m['enabled'] and m['reason'] == 'Còn 4 mặt chưa rà.'
    assert model(rd, remaining=0)['enabled'] is True                 # số mặt chưa rà do trang báo (Store) là số được tin
    rd = make_dot_run(world, 'Nam', decisions={n: 'bo' for n in ALL_DECIDED})
    assert 'Không có mặt nào để đẩy' in model(rd)['reason']
    rd = make_dot_run(world, 'Cuong', decisions=ALL_DECIDED, done=True)
    m = model(rd, env={})
    assert not m['enabled'] and m['reason'] == 'Thiếu CVAT_URL và CVAT_ACCESS_TOKEN.' and m['env_help']
    h = day_cvat.panel_html(m)
    assert 'set CVAT_URL=http://localhost:8080' in h and 'set CVAT_ACCESS_TOKEN=' in h and 'cùng cửa sổ cmd' in h
    assert 'tab <b>Cài đặt</b>' in h and 'bấm <b>Save</b>' in h and 'type="password"' not in h      # ô nhập token chỉ ở tab Cài đặt, không ở khung Đẩy
    m = model(rd, env={'CVAT_URL': 'localhost:8080', 'CVAT_ACCESS_TOKEN': TOKEN})
    assert not m['enabled'] and 'http://' in m['reason'] and TOKEN not in day_cvat.panel_html(m)
    m = model(rd, env={'CVAT_URL': 'http://localhost:8080'})
    assert not m['enabled'] and m['reason'] == 'Thiếu CVAT_ACCESS_TOKEN.'
    assert not model(rd, job=True)['enabled']
    assert dang_chay.acquire(rd, 'prepare')
    assert not model(rd)['enabled'] and 'Đang có việc chạy' in model(rd)['reason'] and 'prepare' in model(rd)['reason']
    dang_chay.release(rd)
    assert model(rd)['enabled']


def test_push_button_locked_when_files_missing_or_partial_push(world):
    rd = make_dot_run(world, 'Khoi', decisions=ALL_DECIDED, done=True)
    os.remove(os.path.join(rd, 'inbox', 'a1.jpg'))
    m = model(rd)
    assert not m['enabled'] and 'Không thấy 1 ảnh' in m['reason']
    rd = make_dot_run(world, 'Nam', decisions=ALL_DECIDED, done=True, push=dict(trang_thai='da_tao', task='demo-Nam', task_id=4, loi='lỗi giả'))
    m = model(rd)
    assert not m['enabled'] and m['partial'] and 'dở' in m['reason'] or 'dừng' in m['reason']
    h = day_cvat.panel_html(m)
    assert '--resume' in h and 'Delete CVAT task' in h and 'lỗi giả' in h


def test_push_done_card_has_link_and_counts(world):
    ps = dict(trang_thai='xong', task='demo-Khoi', task_id=12, task_url='http://localhost:8080/tasks/12',
              jobs=[dict(kind='nhan', n=4), dict(kind='nhan', n=4), dict(kind='gan_tay', n=2)], check=dict(ok=True, n_nhan=8, n_day_du=8))
    rd = make_dot_run(world, 'Khoi', decisions=ALL_DECIDED, done=True, push=ps)
    m = model(rd)
    assert m['kind'] == 'done'
    h = day_cvat.panel_html(m)
    assert 'href="http://localhost:8080/tasks/12"' in h and 'target="_blank"' in h and 'rel="noopener"' in h
    assert '<b>3</b> (2 Nhận, 1 Gán tay)' in h and '8/8' in h and 'demo-Khoi' in h
    bad = day_cvat.result_html(dict(ps, task_url='javascript:alert(1)', task='<x>'), 'Khoi')
    assert 'href=' not in bad and 'javascript:' not in bad                  # chỉ link http/https mới thành liên kết
    assert '&lt;x&gt;' in bad and '<x>' not in bad


def test_push_confirm_html_numbers_and_safety_text(world):
    rd = make_dot_run(world, 'Khoi', decisions=ALL_DECIDED, done=True)
    dot_anh.soft_delete_image(rd, 'a1')
    m = model(rd)
    h = day_cvat.confirm_html(m)
    for s in ('demo-Khoi', '<b>2</b>', 'http://localhost:8080', 'Không đụng task m28-', 'MỚI'):
        assert s in h, s
    assert TOKEN not in h
    assert m['plan']['xoa'] == 1 and 'Ảnh đã xoá' in h


def test_env_state_reads_environ_each_time_and_hides_token(monkeypatch):
    monkeypatch.delenv('CVAT_URL', raising=False)
    monkeypatch.delenv('CVAT_ACCESS_TOKEN', raising=False)
    assert day_cvat.env_state()['ok'] is False
    monkeypatch.setenv('CVAT_URL', 'http://localhost:8080/')
    monkeypatch.setenv('CVAT_ACCESS_TOKEN', TOKEN)
    s = day_cvat.env_state()
    assert s['ok'] and s['url'] == 'http://localhost:8080' and TOKEN not in json.dumps(s)
    monkeypatch.setenv('CVAT_URL', 'http://u:p@host')
    assert not day_cvat.env_state()['ok'] and 'mật khẩu' in day_cvat.env_state()['reason']


def test_phase_parsing_and_progress_html():
    assert day_cvat.parse_phase([])['k'] == 0 and day_cvat.parse_phase([])['label'] == 'Đang khởi động…'
    lines = ['CVAT: x | token: có', '[1/6] kiểm tra: ổn', '[2/6] kết nối: ok', '[3/6] project: m28 (id 1)', 'đang làm gì đó']
    ph = day_cvat.parse_phase(lines)
    assert ph['k'] == 3 and ph['label'] == 'Bước 3/6 · project' and 0.4 < ph['frac'] < 0.5
    assert day_cvat.parse_phase(lines, 'xong')['frac'] == 1.0
    snap = dict(state='dang_chay', returncode=None, run='Khoi', lines=lines, elapsed=75.0, cancelling=False)
    h = day_cvat.progress_html(snap)
    assert 'Bước 3/6' in h and '01:15' in h and 'role="progressbar"' in h and day_cvat.progress_html(dict(snap, state='chua')) == ''
    assert 'Đang huỷ' in day_cvat.progress_html(dict(snap, cancelling=True))


def test_error_and_next_step_texts(world, monkeypatch):
    monkeypatch.setenv('CVAT_ACCESS_TOKEN', TOKEN)
    snap = dict(state='loi', returncode=1, run='Khoi', lines=['[1/6] kiểm tra: ổn', 'Traceback (most recent call last):', '  File "x.py", line 1',
                                                              'Không kết nối được tới http://localhost:8080 khi kết nối. Mở Ubuntu...'], elapsed=1)
    h = day_cvat.error_html(snap, None, 'Khoi')
    assert 'Không kết nối được' in h and 'Traceback' not in h and 'File "' not in h and 'Chưa tạo task nào' in h
    ps = dict(trang_thai='da_tao', task='demo-Khoi', task_id=9)
    h = day_cvat.error_html(snap, ps, 'Khoi')
    assert '--resume' in h and '--cleanup --confirm-name demo-Khoi' in h and 'id 9' in h
    assert '--cleanup' in day_cvat.next_step(dict(trang_thai='dang_tao', task='demo-Khoi'), 'Khoi')
    assert 'Đã huỷ' in day_cvat.cancelled_html(None, 'Khoi')
    leak = dict(snap, lines=[f'lỗi {TOKEN}'])
    assert TOKEN not in day_cvat.error_html(leak, None, 'Khoi') and '***' in day_cvat.error_html(leak, None, 'Khoi')


# ---------- day_cvat: xoá task ----------
def test_delete_model_gates(world):
    ps = dict(trang_thai='xong', task='demo-Khoi', task_id=12, cvat_url='http://localhost:8080')
    rd = make_dot_run(world, 'Khoi', push=ps)
    ok = lambda **kw: day_cvat.delete_model(rd, os.getcwd(), environ=kw.pop('env', env_ok()), **kw)  # noqa: E731
    m = ok()
    assert m['ok'] and m['task'] == 'demo-Khoi' and m['task_id'] == 12
    assert not ok(env={})['ok'] and 'Thiếu CVAT_URL' in ok(env={})['reason']
    assert not ok(job_running=True)['ok']
    assert not ok(env={'CVAT_URL': 'http://localhost:9999', 'CVAT_ACCESS_TOKEN': TOKEN})['ok']
    assert 'localhost:9999' in ok(env={'CVAT_URL': 'http://localhost:9999', 'CVAT_ACCESS_TOKEN': TOKEN})['reason']
    for bad_ps in (dict(ps, task='m28-gold'), dict(ps, task='manual'), dict(ps, task_id=0), dict(ps, task_id='12'), dict(ps, trang_thai='dang_tao'),
                   dict(ps, trang_thai='task_deleted'), dict(ps, task=None)):
        json.dump(bad_ps, open(os.path.join(rd, 'push.json'), 'w'))
        assert not ok()['ok'], bad_ps
    os.remove(os.path.join(rd, 'push.json'))
    assert not ok()['ok']


def test_delete_confirm_requires_exact_name_and_checkbox(world):
    m = dict(ok=True, task='demo-Khoi')
    assert day_cvat.delete_confirm_ok(m, 'demo-Khoi', True)
    for typed, chk in (('demo-khoi', True), ('demo-Khoi ', True), ('', True), (None, True), ('demo-Khoi', False), ('demo-Khoi', None)):
        assert not day_cvat.delete_confirm_ok(m, typed, chk), (typed, chk)
    assert not day_cvat.delete_confirm_ok(dict(m, ok=False), 'demo-Khoi', True)


def test_delete_confirm_html_describes_consequences(world):
    m = dict(task='demo-Khoi', task_id=12, url='http://localhost:8080')
    h = day_cvat.delete_confirm_html(m)
    for s in ('KHÔNG HOÀN TÁC', 'nhãn đã sửa', 'collect', 'demo-Khoi', 'id 12', 'tab Cài đặt', 'không nhập ở hộp này'):
        assert s in h, s


# ---------- jobs (tiến trình con giả) ----------
def _fake_popen(body, seen=None):
    def popen(cmd, **kw):
        if seen is not None:
            seen.update(cmd=cmd, **kw)
        return subprocess.Popen([sys.executable, '-c', body], **kw)
    return popen


def _wait(job, timeout=15):
    t = time.time()
    while job.running and time.time() - t < timeout:
        time.sleep(0.05)


def test_push_job_command_env_lock_and_log_scrub(world, monkeypatch):
    monkeypatch.setenv('CVAT_ACCESS_TOKEN', TOKEN)
    monkeypatch.setenv('CVAT_URL', 'http://localhost:8080')
    rd = make_dot_run(world, 'Khoi')
    seen = {}
    job = na.PushJob(popen=_fake_popen("import os,time; print('[1/6] kiểm tra: ổn', flush=True); print('token', os.environ['CVAT_ACCESS_TOKEN']); "
                                       "print(open('runs/Khoi/.dang_chay').read()); time.sleep(0.2)", seen))
    job.start('Khoi', 'runs', str(world), 'P2', 'demo-Khoi')
    assert dang_chay.busy(rd)[0] == 'push'
    with pytest.raises(na.RunError):
        job.start('Khoi', 'runs', str(world), 'P2', 'demo-Khoi')
    _wait(job)
    snap = job.snapshot()
    assert snap['state'] == 'xong' and snap['kind'] == 'push'
    cmd = seen['cmd']
    assert cmd[-8:] == ['push', '--run', 'Khoi', '--reviewer', 'P2', '--task', 'demo-Khoi'][-8:] or cmd[2].endswith('m28.py')
    assert cmd[3:] == ['push', '--run', 'Khoi', '--reviewer', 'P2', '--task', 'demo-Khoi'] and cmd[1] == '-u'
    assert not any(TOKEN in c for c in cmd) and seen['env']['CVAT_ACCESS_TOKEN'] == TOKEN and seen['env']['PYTHONUTF8'] == '1'
    assert seen['cwd'] == str(world) and seen['stdin'] == subprocess.DEVNULL and 'shell' not in seen
    log = open(os.path.join(rd, 'push_log.txt'), encoding='utf-8').read()
    assert TOKEN not in log and 'token ***' in log and '[1/6] kiểm tra' in log
    assert TOKEN not in '\n'.join(snap['lines'])
    assert dang_chay.busy(rd) is None                                # khoá được gỡ khi xong
    assert 'push_log.txt' in os.listdir(rd)


def test_push_job_failure_and_cancel_reads_push_json(world):
    rd = make_dot_run(world, 'Khoi')
    job = na.PushJob(popen=_fake_popen("import sys; print('Lỗi giả có nguyên nhân'); sys.exit(1)"))
    job.start('Khoi', 'runs', str(world), 'P2', 'demo-Khoi')
    _wait(job)
    snap = job.snapshot()
    assert snap['state'] == 'loi' and snap['returncode'] == 1 and 'Lỗi giả' in day_cvat.error_html(snap, None, 'Khoi')
    job = na.PushJob(popen=_fake_popen("import time; print('bắt đầu', flush=True); time.sleep(60)"))
    job.start('Khoi', 'runs', str(world), 'P2', 'demo-Khoi')
    json.dump(dict(trang_thai='da_tao', task='demo-Khoi', task_id=5), open(os.path.join(rd, 'push.json'), 'w'))
    t = time.time()
    assert job.cancel() is True and time.time() - t < 10 and job.snapshot()['state'] == 'da_huy'
    assert job.cancel() is False and dang_chay.busy(rd) is None
    h = day_cvat.cancelled_html(dot_anh.read_push(rd), 'Khoi')
    assert 'id 5' in h and '--resume' in h and '--cleanup' in h


def test_push_job_rejects_bad_task_run_reviewer(world):
    make_dot_run(world, 'Khoi')
    job = na.PushJob(popen=_fake_popen('pass'))
    for task in ('m28-gold', 'demo-', 'demo- x', 'demo-a/b', 'x', '', 'demo-' + 'a' * 200):
        with pytest.raises(na.RunError):
            job.start('Khoi', 'runs', str(world), 'P2', task)
    with pytest.raises(na.RunError):
        job.start('Khoi', 'runs', str(world), 'P 2', 'demo-Khoi')
    for run in ('../Khoi', 'Nam', '_trash', ''):
        with pytest.raises(na.RunError):
            job.start(run, 'runs', str(world), 'P2', 'demo-Khoi')
    assert job.state == 'chua' and dang_chay.busy(os.path.join('runs', 'Khoi')) is None


def test_delete_task_job_command_and_shared_log(world, monkeypatch):
    monkeypatch.setenv('CVAT_ACCESS_TOKEN', TOKEN)
    rd = make_dot_run(world, 'Khoi')
    seen = {}
    job = na.DeleteTaskJob(popen=_fake_popen("print('Đã xoá task demo-Khoi')", seen))
    job.start('Khoi', 'runs', str(world), 'demo-Khoi')
    _wait(job)
    assert job.snapshot()['state'] == 'xong' and job.snapshot()['kind'] == 'xoa_task'
    assert seen['cmd'][3:] == ['push', '--run', 'Khoi', '--cleanup', '--confirm-name', 'demo-Khoi']
    assert not any(TOKEN in c for c in seen['cmd'])
    assert 'Đã xoá task' in open(os.path.join(rd, 'push_log.txt'), encoding='utf-8').read()
    for bad in ('m28-gold', 'x', 'demo-'):
        with pytest.raises(na.RunError):
            job.start('Khoi', 'runs', str(world), bad)


def test_job_start_refused_when_other_live_lock(world, monkeypatch):
    rd = make_dot_run(world, 'Khoi')
    json.dump(dict(kind='prepare', pid=os.getpid() + 7, t='x'), open(dang_chay.path(rd), 'w'))
    monkeypatch.setattr(dang_chay, 'pid_alive', lambda pid: True)
    job = na.PushJob(popen=_fake_popen('pass'))
    with pytest.raises(na.RunError, match='việc khác'):
        job.start('Khoi', 'runs', str(world), 'P2', 'demo-Khoi')
    monkeypatch.setattr(dang_chay, 'pid_alive', lambda pid: False)            # khoá mồ côi: bỏ qua
    job.start('Khoi', 'runs', str(world), 'P2', 'demo-Khoi')
    _wait(job)
    assert job.snapshot()['state'] == 'xong'


def test_prepare_job_keeps_api_and_writes_lock(world):
    make_dot_run(world, 'NAP_001')
    job = na.PrepareJob(popen=_fake_popen("print('crop: 2 mặt')"))
    job.start('NAP_001', 'runs', str(world))
    _wait(job)
    snap = job.snapshot()
    assert snap['state'] == 'xong' and snap['lines'][0].startswith('crop: 2') and os.path.exists('runs/NAP_001/nap_log.txt')
    assert dang_chay.busy('runs/NAP_001') is None


def test_dang_chay_guard_uses_parent_lock_and_refuses_foreign(world, monkeypatch):
    rd = make_dot_run(world, 'Khoi')
    with dang_chay.Guard(rd, 'push', 'x') as g:
        assert g.own and dang_chay.busy(rd) == ('push', os.getpid())
    assert dang_chay.busy(rd) is None
    json.dump(dict(kind='push', pid=os.getppid(), t='x'), open(dang_chay.path(rd), 'w'))
    with dang_chay.Guard(rd, 'push', 'x') as g:                      # khoá do tiến trình cha (trang) giữ: dùng tiếp, không xoá
        assert not g.own
    assert os.path.exists(dang_chay.path(rd))
    json.dump(dict(kind='push', pid=os.getpid() + 5, t='x'), open(dang_chay.path(rd), 'w'))
    monkeypatch.setattr(dang_chay, 'pid_alive', lambda pid: True)
    with pytest.raises(SystemExit, match='đang có việc khác'):
        with dang_chay.Guard(rd, 'push', 'x'):
            pass


def test_pid_alive_never_kills_on_windows_path():
    assert dang_chay.pid_alive(os.getpid()) and not dang_chay.pid_alive(0) and not dang_chay.pid_alive('x') and not dang_chay.pid_alive(-3)
    src = open(os.path.join(TOOL, 'm28core', 'dang_chay.py'), encoding='utf-8').read()
    assert 'win32' in src and 'OpenProcess' in src                  # Windows dùng OpenProcess, không dùng os.kill(pid, 0) (ở đó nó giết tiến trình)


# ---------- dot_ui: hành động từ trình duyệt ----------
def test_parse_action_validates():
    ok = dot_ui.parse_action(json.dumps(dict(act='delimg', run='Khoi', name='a1')))
    assert ok == dict(act='delimg', run='Khoi', name='a1', page='', trash='', entry='')
    assert set(ok) == set(dot_ui.ACT_KEYS)
    for bad in ('', 'x', 'null', '[]', json.dumps(dict(act='rm -rf')), json.dumps(dict(act='delimg', run=5)), json.dumps({})):
        r = dot_ui.parse_action(bad)
        assert r is None or r['run'] == ''
    assert dot_ui.parse_action(json.dumps(dict(act='open', evil='x')))['run'] == '' and 'evil' not in dot_ui.parse_action(json.dumps(dict(act='open', evil='x')))
    assert dot_ui.parse_action(None) is None


# ---------- kiểm tĩnh ----------
def test_new_modules_are_stdlib_only_and_local_only():
    code = ("import sys\nsys.path.insert(0, %r)\nimport day_cvat, dot_anh, dot_ui, nap_anh\nimport m28core.push, m28core.collect, m28core.cvat_io\n"
            "for m in ('gradio', 'torch', 'numpy', 'cv2', 'mediapipe', 'cvat_sdk', 'PIL'):\n    assert m not in sys.modules, m\nprint('ok')\n") % TOOL
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0 and 'ok' in r.stdout, r.stderr
    for fn in ('dot_anh.py', 'dot_ui.py', 'day_cvat.py', os.path.join('m28core', 'push.py'), os.path.join('m28core', 'collect.py'),
               os.path.join('m28core', 'cvat_io.py'), os.path.join('m28core', 'loai_tru.py')):
        src = open(os.path.join(TOOL, fn), encoding='utf-8').read()
        assert 'shell=True' not in src and 'share=True' not in src and 'import torch' not in src and 'from torch' not in src
        assert not any(l.startswith(('import gradio', 'from gradio')) for l in src.splitlines())
    for fn in ('dot_ui.py', 'day_cvat.py', 'dot_anh.py'):                # trang không gọi mạng: chỉ tiến trình con gọi CVAT
        src = open(os.path.join(TOOL, fn), encoding='utf-8').read()
        for net in ('import urllib', 'import requests', 'import socket', 'http.client', 'import cvat_sdk', 'from cvat_sdk', 'urlopen'):
            assert net not in src, (fn, net)


def test_page_has_no_token_input_and_modal_rules():
    ui = open(os.path.join(TOOL, 'dot_ui.py'), encoding='utf-8').read()
    assert 'type="password"' not in ui and 'CVAT_ACCESS_TOKEN' not in ui and 'token_input' not in ui
    js = dot_ui.JS_BODY
    for rule in ("e.key === 'Escape'", 'button[id$="-cancel"]', "'aria-modal'", "'role', 'dialog'", 'focus()', "e.key === 'Tab'", '#dot-root [data-act]'):
        assert rule in js, rule
    assert ra.PAGE_JS.count('window.__m28Dot') >= 1 and "document.querySelector('.m28-modal')" in ra.PAGE_JS
    assert ra.PAGE_JS.index("document.querySelector('.m28-modal')") < ra.PAGE_JS.index('e.repeat')       # modal mở: phím tắt N/G/B/Z không chạy


def test_gradio_ui_builds_with_all_element_ids(world):
    pytest.importorskip('gradio')
    rd = make_dot_run(world, 'Khoi', decisions=ALL_DECIDED)
    ra.prepare_env(rd)
    store = ra.Store(rd, 'P2')
    demo, _theme = ra.build_ui(store)
    ids = {getattr(b, 'elem_id', None) for b in demo.blocks.values()}
    for want in ('btn-push', 'push-panel', 'push-msg', 'push-prog', 'push-log', 'push-cancel', 'push-confirm', 'push-confirm-ok',
                 'push-confirm-cancel', 'push-result', 'tab-dot', 'dot-root', 'dot-act', 'dot-act-go', 'dot-modal', 'dot-modal-ok', 'dot-modal-cancel',
                 'dot-modal-typed', 'dot-modal-check', 'nap-ghichu', 'nap-start-open', 'nap-start', 'nap-btn-note', 'btn-nhan', 'btn-xong', 'tab-ra', 'tab-nap', 'shown'):
        assert want in ids, want
    assert not {'nap-go', 'nap-oldnote'} & ids                                       # bỏ nút Rà lượt này: mở lượt bằng Upload & Open hoặc tab Các đợt
    labels = {getattr(b, 'elem_id', None): getattr(b, 'value', None) for b in demo.blocks.values()}
    assert [labels[i] for i in ('nap-start-open', 'nap-start', 'nap-cancel', 'nap-retry')] == ['Upload & Open', 'Upload & Continue', 'Cancel', 'Retry']   # tab Nạp ảnh: nút tiếng Anh
    os.makedirs('runs/_nap', exist_ok=True)
    demo2, _ = ra.build_ui(None, ra.AppCtx(reviewer='P2', run_dir=os.path.join('runs', '_nap'), nap_only=True))   # --nap: có tab Các đợt
    assert 'tab-dot' in {getattr(b, 'elem_id', None) for b in demo2.blocks.values()}


def test_nap_tab_auto_open_handler_only_acts_on_the_run_that_asked_for_it(tmp_path, monkeypatch):
    """Upload & Open: on_auto_open không làm gì khi không có yêu cầu hoặc lượt còn chạy; lượt lỗi hoặc job đã sang lượt khác thì bỏ yêu cầu."""
    pytest.importorskip('gradio')
    monkeypatch.chdir(tmp_path)
    os.makedirs('runs/_nap')
    ctx = ra.AppCtx(reviewer='P2', run_dir=os.path.join('runs', '_nap'), nap_only=True)
    demo, _ = ra.build_ui(None, ctx)
    fns = [f.fn for f in demo.fns.values() if getattr(f.fn, '__name__', '') == 'on_auto_open']
    assert len(fns) == 1
    on_auto_open = fns[0]
    snap = {'state': 'dang_chay', 'run': 'NAP_001'}
    ctx.job.snapshot = lambda: dict(snap)                                                        # job giả: không chạy prepare thật
    assert ctx.auto_open is None and on_auto_open(None)[1] == ''
    ctx.auto_open = 'NAP_001'
    assert on_auto_open(None)[1] == '' and ctx.auto_open == 'NAP_001'                           # còn chạy: chờ, giữ yêu cầu
    snap.update(state='loi')
    assert on_auto_open(None)[1] == '' and ctx.auto_open is None                                # lỗi: bỏ yêu cầu, không chuyển trang
    ctx.auto_open = 'NAP_001'
    snap.update(state='xong', run='NAP_002')
    assert on_auto_open(None)[1] == '' and ctx.auto_open is None                                # job đã sang lượt khác: bỏ
    ctx.auto_open = 'NAP_002'
    ctx.closing = True
    msg, target = on_auto_open(None)                                                             # xong và đúng lượt: đi qua on_go (trang đang đóng thì on_go từ chối)
    assert ctx.auto_open is None and target == ''


def test_guard_accepts_page_pid_from_env_when_parent_is_launcher(tmp_path, monkeypatch):
    """Windows: python.exe của .venv là bộ khởi chạy nên getppid() KHÔNG phải trang; trang báo pid của mình qua M28_LOCK_OWNER."""
    monkeypatch.chdir(tmp_path)
    rd = os.path.join('runs', 'Khoi')
    os.makedirs(rd)
    page_pid = os.getppid() + 100000                     # một pid khác cha trực tiếp
    monkeypatch.setattr(dang_chay, 'pid_alive', lambda pid: True)
    json.dump(dict(kind='push', pid=page_pid, t='x'), open(dang_chay.path(rd), 'w'))
    with pytest.raises(SystemExit):                      # chưa khai báo chủ khoá: bị từ chối như cũ
        with dang_chay.Guard(rd, 'push', 'x'):
            pass
    monkeypatch.setenv(dang_chay.OWNER_ENV, str(page_pid))
    with dang_chay.Guard(rd, 'push', 'x') as g:
        assert not g.own                                 # dùng tiếp khoá của trang, không xoá khi thoát
    assert dang_chay.busy(rd) == ('push', page_pid)
    monkeypatch.setenv(dang_chay.OWNER_ENV, 'abc')       # giá trị hỏng: bỏ qua, không crash
    assert dang_chay.owners() == {os.getppid()}


def test_review_app_main_marks_lock_owner():
    src = open(os.path.join(os.path.dirname(__file__), '..', 'tool', 'review_app.py'), encoding='utf-8').read()
    assert 'dang_chay.mark_owner()' in src


# ---------- giờ RIÊNG của từng đợt trên thẻ đợt (QĐ-007) ----------
def test_card_shows_each_dot_own_clock_chip_and_nothing_when_there_is_none(world):
    i = dot_anh.run_info(make_dot_run(world, 'Khoi'), 'P2')
    assert 'c-gio' not in dot_anh.card_html(i)                                                       # chưa có đồng hồ: không có chip (không hiện 00:00 giả)
    g = [dict(nguoi='P2', giay=75, tt='chay'), dict(nguoi='P3', giay=42.2, tt='tam_dung'), dict(nguoi='P2', giay=0, tt='cho'), dict(nguoi='P2', giay=3725, tt='da_luu'), dict(nguoi='P9', giay=1, tt='la')]
    h = dot_anh.card_html(dict(i, gio=g))
    assert '⏱ P2 ▶ 01:15' in h and '⏱ P3 ⏸ 00:42' in h and '⏱ P2 ⏸ chờ bắt đầu' in h and '⏱ P2 ✓ đã lưu 1:02:05' in h and 'P9' not in h
    assert '<script' not in dot_anh.card_html(dict(i, gio=[dict(nguoi='<script>', giay=1, tt='chay')]))      # tên người đi qua escape


def test_batch_list_gives_every_dot_its_own_time(world):
    pytest.importorskip('gradio')
    import re

    import dong_ho
    from dh_fake import FakeGio
    rd1 = make_dot_run(world, 'Khoi', decisions=ALL_DECIDED)
    make_dot_run(world, 'Nam')
    make_dot_run(world, 'Chua')                                                                      # đợt chưa có đồng hồ nào
    ra.prepare_env(rd1)
    ctx = ra.AppCtx(reviewer='P2', run_dir=rd1)
    g = FakeGio()
    d = ctx.dong_ho = dong_ho.DongHo(ctx.project_root, gio=g, pid=os.getpid())
    d.bat_dau('P2', 'assisted', dot='Khoi', n_mat=3)
    g.tick(75)
    d.bat_dau('P2', 'assisted', dot='Nam', n_mat=2, cho=True)                                        # Upload & Continue: Nam chờ, Khoi vẫn chạy
    demo, _ = ra.build_ui(ra.Store(rd1, 'P2'), ctx)
    refresh = next(f.fn for f in demo.fns.values() if getattr(f.fn, '__name__', '') == 'on_load_or_refresh')

    def cards():
        parts = refresh(None)[0].split('<div class="dot-card"')[1:]
        return {re.search(r'data-run="([^"]+)"', p).group(1): p for p in parts}
    c = cards()
    assert '⏱ P2 ▶ 01:15' in c['Khoi'] and '⏱ P2 ⏸ chờ bắt đầu' in c['Nam'] and 'c-gio' not in c['Chua']
    assert '⏱' not in c['Nam'].replace('⏱ P2 ⏸ chờ bắt đầu', '') and '01:15' not in c['Nam']                  # giờ của Khoi không lẫn sang Nam
    d.xong_luu('P2', d.xem('P2', 'Khoi')['rev'], dot='Khoi', so_mat=3)                               # lưu số đo của Khoi: thẻ ghi 'đã lưu' kèm giờ của riêng đợt đó
    c = cards()
    assert '⏱ P2 ✓ đã lưu 01:15' in c['Khoi'] and '▶' not in c['Khoi'] and '⏸ chờ bắt đầu' in c['Nam']
    assert 'dong_ho_ui.gio_cac_dot(ctx)' in open(os.path.join(TOOL, 'dot_ui.py'), encoding='utf-8').read()
