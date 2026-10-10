"""Thử tool/cvat_smoke.py (kiểm tra nhanh CVAT thật) bằng CVAT GIẢ (tests/fake_cvat/cvat_sdk). Giống test_push.py: chạy trong thư mục tạm có
config/ thật chép vào, gói giả đưa vào bằng monkeypatch. Kết quả CHỨNG MINH logic (đúng bước, dọn dẹp, không rò token, chỉ đụng task của
mình) nhưng KHÔNG chứng minh CVAT thật nhận label skeleton / job_file_mapping / XML nhập: việc đó chỉ máy có CVAT 2.77 hoặc 2.78 thật trả lời được."""
import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import zlib

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, '..', 'tool')
FAKE = os.path.join(HERE, 'fake_cvat')
CONFIG = os.path.join(HERE, '..', 'config')
sys.path.insert(0, TOOL)
import cai_dat  # noqa: E402
import cvat_smoke  # noqa: E402
from m28core import cvat_io  # noqa: E402

TOKEN = 'tok-TEST-123456'
URL = 'http://localhost:8080'


def _purge():
    return {k: sys.modules.pop(k) for k in list(sys.modules) if k == 'cvat_sdk' or k.startswith('cvat_sdk.')}


@pytest.fixture
def cvat(tmp_path, monkeypatch):
    """Thư mục gốc tạm (config/ thật chép vào), env CVAT giả, gói cvat_sdk giả. Trả module giả; cvat.root = thư mục gốc."""
    root = tmp_path / 'root'
    (root / 'config').mkdir(parents=True)
    for f in ('m28_config.json', 'face50_label.json', 'pipeline.json'):
        shutil.copy(os.path.join(CONFIG, f), root / 'config' / f)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('CVAT_URL', URL)
    monkeypatch.setenv('CVAT_ACCESS_TOKEN', TOKEN)
    for k in ('CVAT_ORG', 'M28_FAKE_CVAT_STATE', 'M28_FAKE_CVAT_CONTROL'):
        monkeypatch.delenv(k, raising=False)
    saved = _purge()
    monkeypatch.syspath_prepend(FAKE)
    import cvat_sdk
    cvat_sdk.reset()
    cvat_sdk.root = str(root)
    yield cvat_sdk
    _purge()
    sys.modules.update(saved)


def opts(cvat, **kw):
    d = dict(dry_run=False, url=None, org=None, giu_task=False, giu_project=False, timeout=60, root=cvat.root)
    d.update(kw)
    return argparse.Namespace(**d)


def go(cvat, out=None, **kw):
    code, rep = cvat_smoke.run(opts(cvat, **kw), out=out)
    return code, rep, {b['ma']: b for b in rep.get('buoc', [])}


def marker(cvat):
    return os.path.join(cvat.root, 'runs', '_smoke', cvat_smoke.MARKER)


def ncalls(cvat, method, since=0):
    return sum(1 for c in cvat.calls()[since:] if c['m'] == method)


def tasks_named(cvat, name='demo-smoke'):
    return [t for t in cvat.load()['tasks'] if t['name'] == name]


def seed_project(cvat, **control):
    """Tạo project m28 'có sẵn' bằng chính gói giả (không qua smoke). Trả số lời gọi đã ghi (để lọc log sau đó)."""
    cvat.CONTROL.update(control)
    labels = json.load(open(os.path.join(cvat.root, 'config', 'face50_label.json'), encoding='utf-8'))
    c = cvat.make_client(URL, access_token='x')
    c.projects.create({'name': 'm28', 'labels': labels})
    cvat.CONTROL.clear()
    return len(cvat.calls())


def seed_task(cvat, tid, name, project_id=1):
    st = cvat.load()
    st['tasks'].append(dict(id=tid, name=name, project_id=project_id, frames=['x.png'], jobs=[dict(id=900 + tid, start_frame=0, stop_frame=0,
                            stage='annotation', state='new')], annotations=None, files=[], created='2026-10-01T00:00:00+00:00'))
    st['next_task'] = max(st['next_task'], tid + 1)


def all_files_text(*dirs):
    out = []
    for d in dirs:
        for dp, _dn, fn in os.walk(d):
            for f in fn:
                with open(os.path.join(dp, f), 'rb') as fh:
                    out.append((os.path.join(dp, f), fh.read()))
    return out


# ---------- đường ĐẠT ----------
def test_happy_path(cvat, capsys):
    code, rep, st = go(cvat)
    assert code == 0, rep
    assert [st[i]['ket_qua'] for i in range(1, 13)] == ['ĐẠT'] * 12
    assert tasks_named(cvat) == [] and cvat.load()['projects'] == []                 # project do lần này tạo, rỗng -> đã xoá
    assert ncalls(cvat, 'Task.import_annotations') == 1 and ncalls(cvat, 'tasks.create_from_data') == 1
    assert ncalls(cvat, 'Task.remove') == 1 and ncalls(cvat, 'Project.remove') == 1
    assert not os.path.exists(marker(cvat))
    smoke = os.path.join(cvat.root, 'runs', '_smoke')
    names = sorted(os.listdir(smoke))
    txt = [n for n in names if n.startswith('bao_cao_') and n.endswith('.txt')]
    js = [n for n in names if n.startswith('bao_cao_') and n.endswith('.json')]
    assert len(txt) == 1 and len(js) == 1 and txt[0][:-4] == js[0][:-5]
    r = json.load(open(os.path.join(smoke, js[0]), encoding='utf-8'))
    assert {'thoi_gian', 'may', 'cvat_sdk', 'cvat_url', 'nguon_token', 'to_chuc', 'ban_server', 'tai_khoan', 'project', 'task_id', 'buoc', 'co',
            'tong', 'ma_thoat'} <= set(r)
    assert r['tong'] == 'Tất cả ĐẠT' and r['nguon_token'] == 'từ biến môi trường' and r['project']['da_tao_lan_nay'] is True
    assert [b['ma'] for b in r['buoc']] == list(range(1, 13)) and all({'ten', 'ket_qua', 'ghi_chu', 'giay'} <= set(b) for b in r['buoc'])
    out = capsys.readouterr().out
    assert 'Bước' in out and 'Kết quả' in out and 'Ghi chú' in out and 'Tất cả ĐẠT' in out
    assert out.rstrip().splitlines()[-1] == 'SMOKE_JSON: ' + os.path.join(smoke, js[0])
    assert '[7/12] Tạo task và job' in out


def test_step9_checks_the_job_files_and_fails_when_the_split_is_wrong(cvat, monkeypatch):
    from m28core import tach_job
    code, rep, st = go(cvat)
    assert code == 0 and st[9]['ket_qua'] == 'ĐẠT' and 'tách theo job' in json.dumps(rep, ensure_ascii=False)
    real = tach_job.tach

    def wrong(*a, **k):                                                    # tách sai: job cuối (Gán tay) mất file
        res = real(*a, **k)
        os.remove(res['jobs'][-1]['path'])
        return res
    monkeypatch.setattr(tach_job, 'tach', wrong)
    code, rep, st = go(cvat)
    assert code == 1 and st[9]['ket_qua'] == 'HỎNG' and 'tách job' in st[9]['ghi_chu'] and tasks_named(cvat) == []      # vẫn dọn task sau khi HỎNG

    def swapped(*a, **k):                                                  # tách sai: ảnh Gán tay lọt vào job Nhận đầu tiên
        res = real(*a, **k)
        first = res['jobs'][0]['path']
        data = open(res['jobs'][-1]['path'], 'rb').read()
        open(first, 'wb').write(data)
        return res
    monkeypatch.setattr(tach_job, 'tach', swapped)
    code, rep, st = go(cvat)
    assert code == 1 and st[9]['ket_qua'] == 'HỎNG' and 'tách job' in st[9]['ghi_chu']


def smoke_run_dir(cvat):
    d = os.path.join(cvat.root, 'runs', '_smoke')
    runs = sorted(n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n)))
    return os.path.join(d, runs[-1])


def test_step9_checks_require_completed_and_overwrite_on_server(cvat, capsys):
    """Bước 9 thử hai cờ của nút Merge jobs & Finish: (a) --require-completed thoát mã 3, không ghi gì; (b) --overwrite dời bản cũ vào raw\\_cu."""
    n0 = len(cvat.calls())
    code, rep, st = go(cvat)
    assert code == 0 and st[9]['ket_qua'] == 'ĐẠT', st[9]
    con = '\n'.join(st[9]['con'])
    assert '(a) --require-completed: 3 job chưa completed nên thoát mã 3' in con and 'state new, new, new' in con
    assert '(b) --overwrite: xuất lại; bản cũ (8 file' in con and 'raw\\_cu' in con and 'annotation/new/annotation' in con
    raw = os.path.join(smoke_run_dir(cvat), 'raw')
    cu = sorted(os.listdir(os.path.join(raw, '_cu')))
    assert len(cu) == 8 and all(re.search(r'\.cu\d{6}\.(xml|txt)$', n) for n in cu)              # .xml, .txt và 3 job x (.xml + .txt)
    whole = [n for n in os.listdir(raw) if re.fullmatch(r'demo-smoke_SMOKE_\d{4}\.xml', n)]
    assert len(whole) == 1 and len([n for n in os.listdir(raw) if '_job' in n]) == 6               # bản mới ghi lại đủ
    assert ncalls(cvat, 'Task.export_dataset', n0) == 3 and ncalls(cvat, 'Task.get_jobs', n0) >= 3
    out = capsys.readouterr().out                                                                  # chữ của hai lần thử phụ không in ra màn hình
    assert not [ln for ln in out.splitlines() if ln.startswith('COLLECT_JOBS_PENDING: ')] and 'CHƯA xuất gì' not in out
    assert len([ln for ln in out.splitlines() if ln.startswith('COLLECT_XML: ')]) == 1                # chỉ lần collect chính


def test_step9_fails_when_require_completed_does_not_block(cvat, monkeypatch):
    from m28core import collect
    monkeypatch.setattr(collect, 'jobs_chua_xong', lambda jobs: [])                              # giả: coi mọi job là xong
    code, rep, st = go(cvat)
    assert code == 1 and st[9]['ket_qua'] == 'HỎNG' and '(a) --require-completed' in st[9]['ghi_chu'] and 'không chặn' in st[9]['ghi_chu']
    assert 'Merge jobs & Finish' in st[9]['ghi_chu'] and 'nhãn xuất ra khác' not in st[9]['ghi_chu']
    assert tasks_named(cvat) == [] and st[11]['ket_qua'] == 'ĐẠT'                               # vẫn dọn task


def test_step9_fails_when_require_completed_writes_files(cvat, monkeypatch):
    from m28core import collect
    real = collect.collect

    def leaky(args):
        if getattr(args, 'require_completed', False):
            os.makedirs('raw', exist_ok=True)
            open(os.path.join('raw', 'lot.txt'), 'w').write('x')
        return real(args)
    monkeypatch.setattr(collect, 'collect', leaky)
    code, rep, st = go(cvat)
    assert code == 1 and st[9]['ket_qua'] == 'HỎNG' and 'vẫn ghi hoặc đổi file' in st[9]['ghi_chu']


def test_step9_fails_when_overwrite_does_not_move_old_files(cvat, monkeypatch):
    from m28core import collect
    monkeypatch.setattr(collect, 'cat_ban_cu', lambda *a, **k: [])                              # giả: ghi đè thẳng, không giữ bản cũ
    code, rep, st = go(cvat)
    assert code == 1 and st[9]['ket_qua'] == 'HỎNG' and '(b) --overwrite không chuyển' in st[9]['ghi_chu']
    assert tasks_named(cvat) == []


def test_step9_fails_when_job_state_is_not_plain_text(cvat, monkeypatch):
    from m28core import collect
    monkeypatch.setattr(collect, '_txt', lambda v: f'JobState(value={v!r})')                     # như str() của enum SDK nếu không lấy .value
    code, rep, st = go(cvat)
    assert code == 1 and st[9]['ket_qua'] == 'HỎNG' and 'không phải chữ thường của CVAT' in st[9]['ghi_chu']


def test_step9_fails_when_server_export_breaks_on_overwrite(cvat, monkeypatch):
    from m28core import collect
    real = collect.collect

    def second_export_fails(args):
        if getattr(args, 'overwrite', False):
            cvat.CONTROL['export_fail'] = True
        try:
            return real(args)
        finally:
            cvat.CONTROL.pop('export_fail', None)
    monkeypatch.setattr(collect, 'collect', second_export_fails)
    code, rep, st = go(cvat)
    assert code == 1 and st[9]['ket_qua'] == 'HỎNG' and '(b) --overwrite: collect dừng' in st[9]['ghi_chu'] and '500' in st[9]['ghi_chu']
    raw = os.path.join(smoke_run_dir(cvat), 'raw')
    assert not os.path.exists(os.path.join(raw, '_cu')) and len([n for n in os.listdir(raw) if re.fullmatch(r'demo-smoke_SMOKE_\d{4}\.xml', n)]) == 1
    assert tasks_named(cvat) == [] and TOKEN not in json.dumps(rep)


def test_existing_project_is_left_alone_and_giu_project(cvat):
    code, rep, st = go(cvat, giu_project=True)
    assert code == 0 and st[12]['ket_qua'] == 'BỎ QUA' and 'giữ theo --giu-project' in st[12]['ghi_chu']
    assert len(cvat.load()['projects']) == 1 and tasks_named(cvat) == []
    n0 = len(cvat.calls())
    code, rep, st = go(cvat)                                                          # project có sẵn: không tạo, không xoá
    assert code == 0 and 'có sẵn' in st[5]['ghi_chu'] and 'giữ nguyên' in st[12]['ghi_chu']
    assert ncalls(cvat, 'projects.create', n0) == 0 and ncalls(cvat, 'Project.remove', n0) == 0 and len(cvat.load()['projects']) == 1


def test_svg_with_label_ids_like_real_server(cvat):
    cvat.CONTROL['svg_label_ids'] = True
    code, rep, st = go(cvat)
    assert code == 0 and st[5]['ket_qua'] == 'ĐẠT', rep


def test_foreign_tasks_untouched(cvat):
    seed_project(cvat)
    seed_task(cvat, 50, 'm28-gold')
    seed_task(cvat, 51, 'demo-Khoi')
    n0 = len(cvat.calls())
    code, rep, st = go(cvat)
    assert code == 0 and sorted(t['name'] for t in cvat.load()['tasks']) == ['demo-Khoi', 'm28-gold']
    for c in cvat.calls()[n0:]:
        if c['m'] in ('tasks.retrieve', 'tasks.remove_by_ids'):
            ids = c['args'][0] if isinstance(c['args'][0], list) else [c['args'][0]]
            assert not {50, 51} & set(ids)
    # export: push tự kiểm, collect, collect --overwrite (bước 9b); --require-completed (9a) không xuất
    assert ncalls(cvat, 'Task.remove', n0) == 1 and ncalls(cvat, 'Task.import_annotations', n0) == 1 and ncalls(cvat, 'Task.export_dataset', n0) == 3


# ---------- dry-run ----------
def test_dry_run_makes_no_calls(cvat, monkeypatch):
    before = dict(os.environ)
    code, rep, st = go(cvat, dry_run=True)
    assert code == 0 and cvat.calls() == [] and dict(os.environ) == before
    assert [st[i]['ket_qua'] for i in (1, 2, 3)] == ['ĐẠT'] * 3 and all(st[i]['ket_qua'] == 'BỎ QUA' for i in range(4, 13))
    monkeypatch.delenv('CVAT_ACCESS_TOKEN')
    code, rep, st = go(cvat, dry_run=True)                                            # thiếu token ở dry-run: BỎ QUA, không HỎNG
    assert code == 0 and st[3]['ket_qua'] == 'BỎ QUA' and cvat.calls() == []


def test_missing_token_without_dry_run_fails_step3(cvat, monkeypatch):
    monkeypatch.delenv('CVAT_ACCESS_TOKEN')
    code, rep, st = go(cvat)
    assert code == 1 and st[3]['ket_qua'] == 'HỎNG' and 'CVAT_ACCESS_TOKEN' in st[3]['ghi_chu'] and cvat.calls() == []
    assert all(st[i]['ket_qua'] == 'BỎ QUA' for i in range(4, 13))
    assert 'vì bước 3 hỏng' in st[4]['ghi_chu']


# ---------- từng bước HỎNG ----------
@pytest.mark.parametrize('control, step, text', [
    ({'connect_fail': True}, 4, 'server tắt'),
    ({'auth_fail': True}, 4, 'sai token'),
    ({'version': '2.70.0'}, 4, 'khác phiên bản'),
    ({'label_reject': True}, 5, '400'),
])
def test_connection_and_label_failures(cvat, control, step, text):
    cvat.CONTROL.update(control)
    code, rep, st = go(cvat)
    assert code == 1 and st[step]['ket_qua'] == 'HỎNG' and text in st[step]['ghi_chu']
    assert all(st[i]['ket_qua'] == 'ĐẠT' for i in range(1, step))
    assert all(st[i]['ket_qua'] == 'BỎ QUA' for i in range(step + 1, 13))
    assert tasks_named(cvat) == [] and ncalls(cvat, 'tasks.create_from_data') == 0 and not os.path.exists(marker(cvat))


# ---------- bản server: đúng tập cvat_io.ban_chap_nhan mà push/collect nhận (C8) ----------
def set_pipeline_version(cvat, v):
    p = os.path.join(cvat.root, 'config', 'pipeline.json')
    d = json.load(open(p, encoding='utf-8'))
    d['cvat_version'] = v
    json.dump(d, open(p, 'w', encoding='utf-8'))


def test_server_278_like_the_owner_runs_every_step_including_step9_flags(cvat, capsys):
    """Máy chủ repo chạy CVAT 2.78.0 với cvat-sdk và config\\pipeline.json 2.77.0 (QĐ-009): bước 4 ĐẠT, ghi rõ bản server và lý do được nhận (cvat-sdk 2.77
    khai hỗ trợ); bước 9 (hai cờ của nút Merge jobs & Finish trên server thật) chạy được, không bị BỎ QUA."""
    assert json.load(open(os.path.join(cvat.root, 'config', 'pipeline.json'), encoding='utf-8'))['cvat_version'] == '2.77.0'
    cvat.CONTROL['version'] = '2.78.0'
    code, rep, st = go(cvat)
    assert code == 0 and [st[i]['ket_qua'] for i in range(1, 13)] == ['ĐẠT'] * 12, rep
    assert 'server CVAT 2.78.0 (mới hơn cvat_version 2.77.0' in st[4]['ghi_chu'] and 'cvat-sdk 2.77 khai hỗ trợ bản này nên được nhận' in st[4]['ghi_chu']
    con = '\n'.join(st[9]['con'])
    assert '(a) --require-completed: 3 job chưa completed nên thoát mã 3' in con and '(b) --overwrite: xuất lại' in con
    assert rep['ban_server'] == '2.78.0' and 'cvat_version 2.77.0' in st[1]['ghi_chu']
    out = capsys.readouterr().out
    assert re.search(r'^\[4/12\] Kết nối và phiên bản: ĐẠT\. server CVAT 2\.78\.0 ', out, re.M)
    assert out.index('Lưu ý: server CVAT 2.78.0') < out.index('[4/12] Kết nối và phiên bản: ĐẠT')        # dòng nhắc của check_version in cùng chỗ
    txt = [n for n in os.listdir(os.path.join(cvat.root, 'runs', '_smoke')) if n.endswith('.txt')]
    body = open(os.path.join(cvat.root, 'runs', '_smoke', txt[0]), encoding='utf-8').read()
    assert 'bản server: 2.78.0' in body and 'khai hỗ trợ bản này' in body


@pytest.mark.parametrize('server', ['2.77.4', '2.78.1', '2.79.0', '2.76.9', '3.77.0'])
def test_step4_accepts_exactly_what_push_and_collect_accept(cvat, server):
    ok = cvat_io._mm(server) in cvat_io.ban_chap_nhan('2.77.0')
    cvat.CONTROL['version'] = server
    code, rep, st = go(cvat)
    if ok:
        assert code == 0 and st[4]['ket_qua'] == 'ĐẠT' and st[9]['ket_qua'] == 'ĐẠT', rep
        assert ('mới hơn cvat_version' in st[4]['ghi_chu']) == server.startswith('2.78.')
    else:
        assert code == 1 and st[4]['ket_qua'] == 'HỎNG' and 'khác phiên bản' in st[4]['ghi_chu'] and st[9]['ket_qua'] == 'BỎ QUA'
        assert tasks_named(cvat) == [] and ncalls(cvat, 'tasks.create_from_data') == 0
    assert server.startswith(('2.77.', '2.78.')) == ok


@pytest.mark.parametrize('pipe_ver, server, step, text', [
    ('2.78.0', '2.78.0', None, None),                                  # pipeline.json đã sửa theo gợi ý cũ: vẫn trong bản cvat-sdk 2.77 hỗ trợ
    ('2.78.0', '2.77.0', 4, 'khác phiên bản'),                         # check_version: 2.77 ngoài ban_chap_nhan('2.78.0'), push cũng dừng như vậy
    ('2.79.0', '2.79.0', 1, 'ngoài các bản cvat-sdk 2.77.0 của nhóm hỗ trợ (2.77.x, 2.78.x)'),
    ('2.76.0', '2.76.0', 1, 'trả về 2.77.0'),
])
def test_step1_pipeline_version_follows_the_sdk_supported_set(cvat, pipe_ver, server, step, text):
    set_pipeline_version(cvat, pipe_ver)
    cvat.CONTROL['version'] = server
    code, rep, st = go(cvat)
    if step is None:
        assert code == 0 and [st[i]['ket_qua'] for i in range(1, 13)] == ['ĐẠT'] * 12, rep
        assert 'mới hơn' not in st[4]['ghi_chu']
    else:
        assert code == 1 and st[step]['ket_qua'] == 'HỎNG' and text in st[step]['ghi_chu'], st[step]
        assert st[9]['ket_qua'] == 'BỎ QUA' and tasks_named(cvat) == []


def test_step4_own_check_matches_ban_chap_nhan_even_if_the_connection_check_lets_it_through(cvat, monkeypatch):
    monkeypatch.setattr(cvat_io, 'check_version', lambda client, want: cvat_io.server_version(client))   # giả: lớp kiểm của cai_dat_thu bị bỏ qua
    cvat.CONTROL['version'] = '2.80.0'
    code, rep, st = go(cvat)
    assert code == 1 and st[4]['ket_qua'] == 'HỎNG' and 'server là bản 2.80.0' in st[4]['ghi_chu']
    assert 'push/collect chỉ nhận 2.77.x, 2.78.x' in st[4]['ghi_chu'] and st[5]['ket_qua'] == 'BỎ QUA'
    assert cvat_smoke.ban_text('2.77.0') == '2.77.x, 2.78.x' and cvat_smoke.ban_text('x') == '(không đọc được bản)'


def test_existing_project_with_missing_sublabels_is_not_touched(cvat):
    n0 = seed_project(cvat, project_missing_sublabels=3)
    code, rep, st = go(cvat)
    assert code == 1 and st[5]['ket_qua'] == 'HỎNG' and 'sublabel' in st[5]['ghi_chu'] and 'KHÔNG sửa' in st[5]['ghi_chu']
    assert len(cvat.load()['projects']) == 1 and sum(len(lb['sublabels']) for lb in cvat.load()['projects'][0]['labels']) == 29
    assert ncalls(cvat, 'Project.remove', n0) == 0 and ncalls(cvat, 'projects.create', n0) == 0 and ncalls(cvat, 'tasks.create_from_data') == 0
    assert st[12]['ket_qua'] == 'BỎ QUA' or 'giữ nguyên' in st[12]['ghi_chu']


def test_sublabel_order_mismatch_reported_and_project_removed(cvat):
    cvat.CONTROL['sublabel_order_shuffle'] = True
    code, rep, st = go(cvat)
    assert code == 1 and st[5]['ket_qua'] == 'HỎNG' and 'THỨ TỰ' in st[5]['ghi_chu'] and 'P4' in st[5]['ghi_chu']
    assert cvat.load()['projects'] == [] and 'đã xoá' in st[12]['ghi_chu']             # project do smoke tạo, rỗng: dọn
    assert ncalls(cvat, 'tasks.create_from_data') == 0


def test_import_failure_still_cleans_up(cvat):
    cvat.CONTROL['import_fail_times'] = 1
    code, rep, st = go(cvat)
    assert code == 1 and st[7]['ket_qua'] == 'ĐẠT' and st[8]['ket_qua'] == 'HỎNG' and st[9]['ket_qua'] == 'BỎ QUA'
    assert 'nhập' in st[8]['ghi_chu'] and '500' in st[8]['ghi_chu']
    assert tasks_named(cvat) == [] and not os.path.exists(marker(cvat)) and st[11]['ket_qua'] == 'ĐẠT'


def test_export_missing_point_fails_step9_and_cleans_up(cvat):
    cvat.CONTROL['drop_point'] = True
    code, rep, st = go(cvat)
    assert code == 1 and st[8]['ket_qua'] == 'ĐẠT' and st[9]['ket_qua'] == 'HỎNG'
    assert 'tự kiểm' in st[9]['ghi_chu'] or 'không đạt' in st[9]['ghi_chu'].lower()
    assert tasks_named(cvat) == [] and st[11]['ket_qua'] == 'ĐẠT'


def test_remove_failure_keeps_marker_then_next_run_cleans(cvat):
    cvat.CONTROL['remove_fail'] = True
    code, rep, st = go(cvat)
    assert code == 1 and st[11]['ket_qua'] == 'HỎNG' and '/tasks/' in st[11]['ghi_chu']
    assert os.path.exists(marker(cvat)) and len(tasks_named(cvat)) == 1
    mk = json.load(open(marker(cvat), encoding='utf-8'))
    assert mk['task'] == 'demo-smoke' and mk['task_id'] == tasks_named(cvat)[0]['id'] and mk['cvat_url'] == URL and 'run' in mk
    assert 'project' in mk and 'tao_luc' in mk and 'run_dir' in mk and TOKEN not in json.dumps(mk)
    cvat.CONTROL.clear()
    code, rep, st = go(cvat)                                                          # lần sau tự dọn task cũ rồi ĐẠT
    assert code == 0 and 'đã dọn' in st[6]['ghi_chu'] and tasks_named(cvat) == [] and not os.path.exists(marker(cvat))


def test_remove_failure_prints_hint_for_p4(cvat, capsys):
    cvat.CONTROL['remove_fail'] = True
    go(cvat)
    out = capsys.readouterr().out
    assert 'Có 1 bước HỎNG' in out and 'Gửi cho P4 file runs\\_smoke\\bao_cao_' in out and '(không gửi token, không gửi ảnh)' in out


def test_preexisting_demo_smoke_without_marker_is_not_deleted(cvat):
    seed_project(cvat)
    seed_task(cvat, 60, 'demo-smoke')
    n0 = len(cvat.calls())
    code, rep, st = go(cvat)
    assert code == 1 and st[6]['ket_qua'] == 'HỎNG' and 'KHÔNG xoá' in st[6]['ghi_chu'] and '/tasks/60' in st[6]['ghi_chu']
    assert all(st[i]['ket_qua'] == 'BỎ QUA' for i in range(7, 11))
    assert [t['id'] for t in tasks_named(cvat)] == [60]
    assert ncalls(cvat, 'Task.remove', n0) == 0 and ncalls(cvat, 'tasks.create_from_data', n0) == 0 and ncalls(cvat, 'tasks.remove_by_ids', n0) == 0


def test_marker_for_other_cvat_is_not_touched(cvat):
    os.makedirs(os.path.dirname(marker(cvat)))
    json.dump(dict(tool='cvat_smoke', task='demo-smoke', task_id=5, project='m28', project_id=1, cvat_url='http://khac:8080',
                   run='20261001_101010', run_dir='x', tao_luc='t'), open(marker(cvat), 'w'))
    code, rep, st = go(cvat)
    assert code == 1 and st[6]['ket_qua'] == 'HỎNG' and 'CVAT khác' in st[6]['ghi_chu'] and os.path.exists(marker(cvat))
    assert ncalls(cvat, 'tasks.create_from_data') == 0 and ncalls(cvat, 'Task.remove') == 0


# ---------- --giu-task ----------
def test_giu_task_keeps_task_and_next_run_cleans_it(cvat):
    code, rep, st = go(cvat, giu_task=True)
    assert code == 0 and st[11]['ket_qua'] == 'BỎ QUA' and '/tasks/' in st[11]['ghi_chu'] and os.path.exists(marker(cvat))
    assert len(tasks_named(cvat)) == 1 and len(cvat.load()['projects']) == 1                 # project còn task nên không bị xoá
    code, rep, st = go(cvat)
    assert code == 0 and 'đã dọn' in st[6]['ghi_chu'] and tasks_named(cvat) == [] and not os.path.exists(marker(cvat))


# ---------- lỗi lạ ----------
def test_unexpected_exception_and_ctrl_c_still_clean_up(cvat, monkeypatch):
    from m28core import collect
    monkeypatch.setattr(collect, 'collect', lambda a: (_ for _ in ()).throw(RuntimeError('boom ' + TOKEN)))
    code, rep, st = go(cvat)
    assert code == 1 and st[9]['ket_qua'] == 'HỎNG' and TOKEN not in json.dumps(rep) and 'RuntimeError' in st[9]['ghi_chu']
    assert tasks_named(cvat) == [] and not os.path.exists(marker(cvat))

    def ctrl_c(a):
        raise KeyboardInterrupt
    monkeypatch.setattr(collect, 'collect', ctrl_c)
    code, rep, st = go(cvat)
    assert code == 1 and st[9]['ket_qua'] == 'HỎNG' and 'Ctrl+C' in st[9]['ghi_chu'] and st[10]['ket_qua'] == 'BỎ QUA'
    assert st[11]['ket_qua'] == 'ĐẠT' and tasks_named(cvat) == [] and st[12]['ket_qua'] == 'ĐẠT'


# ---------- không rò token ----------
def test_no_token_leak_anywhere(cvat, tmp_path, capfd):
    runs = [{}, {'connect_fail': True}, {'auth_fail': True}, {'import_fail_times': 1}, {'drop_point': True}, {'remove_fail': True}]
    for ctl in runs:
        cvat.reset()
        cvat.CONTROL.update(ctl)
        cvat_smoke.run(opts(cvat))
    cap = capfd.readouterr()
    assert TOKEN not in cap.out and TOKEN not in cap.err
    for path, data in all_files_text(cvat.root):
        assert TOKEN.encode() not in data, path
    assert TOKEN not in json.dumps(cvat.load(), default=str)
    assert TOKEN not in json.dumps(cvat.calls(), default=str)


def test_subprocess_run_and_no_token_leak(tmp_path):
    root = tmp_path / 'root'
    (root / 'config').mkdir(parents=True)
    for f in ('m28_config.json', 'face50_label.json', 'pipeline.json'):
        shutil.copy(os.path.join(CONFIG, f), root / 'config' / f)
    state = tmp_path / 'fake_state.json'
    env = dict(os.environ, PYTHONPATH=FAKE, M28_FAKE_CVAT_STATE=str(state), CVAT_URL=URL, CVAT_ACCESS_TOKEN=TOKEN,
               M28_CONFIG_DIR=str(tmp_path / 'cfg'), PYTHONUTF8='1')
    env.pop('M28_FAKE_CVAT_CONTROL', None)
    p = subprocess.run([sys.executable, os.path.join(TOOL, 'cvat_smoke.py'), '--root', str(root)], capture_output=True, env=env, cwd=str(tmp_path),
                       timeout=180)
    out, err = p.stdout.decode('utf-8'), p.stderr.decode('utf-8')
    assert p.returncode == 0, out + err
    assert TOKEN not in out and TOKEN not in err and 'Tất cả ĐẠT' in out
    assert out.rstrip().splitlines()[-1].startswith('SMOKE_JSON: ') and os.path.isfile(out.rstrip().splitlines()[-1][len('SMOKE_JSON: '):])
    for path, data in all_files_text(str(root), str(tmp_path / 'cfg')) + [(str(state), state.read_bytes())]:
        assert TOKEN.encode() not in data, path
    assert '--token' not in subprocess.run([sys.executable, os.path.join(TOOL, 'cvat_smoke.py'), '--help'], capture_output=True).stdout.decode()


# ---------- nguồn token, đối số ----------
def test_token_only_in_saved_file(cvat, monkeypatch):
    r = cai_dat.get().save_cvat(URL, TOKEN, '', True)
    assert r['ok'], r
    cai_dat.reset()
    for k in ('CVAT_URL', 'CVAT_ACCESS_TOKEN'):
        monkeypatch.delenv(k)
    code, rep, st = go(cvat)
    assert code == 0 and rep['nguon_token'] == 'đã lưu trên máy' and 'đã lưu trên máy' in st[3]['ghi_chu']
    assert os.environ.get('CVAT_ACCESS_TOKEN') is None                                    # os.environ được khôi phục


def test_env_beats_saved_file(cvat):
    assert cai_dat.get().save_cvat('http://khac:9999', 'file-token-777777', '', True)['ok']
    cai_dat.reset()
    code, rep, st = go(cvat)
    assert code == 0 and rep['nguon_token'] == 'từ biến môi trường' and rep['cvat_url'] == URL


def test_url_override_warns_about_token(cvat, capsys):
    code, rep, st = go(cvat, url='http://localhost:8081')
    assert 'CẢNH BÁO' in capsys.readouterr().out and rep['cvat_url'] == 'http://localhost:8081'


def test_bad_arguments():
    with pytest.raises(SystemExit) as e:
        cvat_smoke.main(['--token', 'x'])
    assert e.value.code == 2
    for bad in (['--timeout', '1'], ['--timeout', '9999'], ['--url', 'localhost:8080'], ['--org', 'a b']):
        with pytest.raises(SystemExit) as e:
            cvat_smoke.main(bad)
        assert e.value.code == 2


def test_run_rejects_bad_timeout(cvat):
    code, rep, _st = go(cvat, timeout=2)
    assert code == 2 and cvat.calls() == []


# ---------- hàm nhỏ ----------
def test_png_and_points_and_compare():
    data = cvat_smoke.png_gray(40, 30, 1)
    assert data[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', data[16:24]) == (40, 30)
    idat = data[data.index(b'IDAT') + 4:data.index(b'IEND') - 8]
    assert len(zlib.decompress(idat)) == 30 * (1 + 40) and data == cvat_smoke.png_gray(40, 30, 1)
    for i, (_n, (w, h), _r) in enumerate(cvat_smoke.IMAGES):
        pts = cvat_smoke.smoke_points(w, h, i)
        assert len(set(pts)) == 50 and all(0 < x < w and 0 < y < h for x, y in pts)
    assert len({s for _n, s, _r in cvat_smoke.IMAGES}) == 4
    assert all(cvat_smoke.smoke_low('tay_nhap', 2)) and {True, False} == set(cvat_smoke.smoke_low('nhan', 0))


def test_check_svg_name_and_id_forms():
    names = ['a', 'b', 'c']
    edges = {frozenset(('a', 'b')), frozenset(('b', 'c'))}
    by_name = ('<line data-type="edge" data-node-from="1" data-node-to="2"></line><line data-type="edge" data-node-from="2" data-node-to="3"></line>'
               '<circle data-node-id="1" data-label-name="a"></circle><circle data-node-id="2" data-label-name="b"></circle>'
               '<circle data-node-id="3" data-label-name="c"></circle>')
    assert cvat_smoke.check_svg(by_name, {}, names, edges) == []
    by_id = by_name.replace('data-label-name="a"', 'data-label-id="11"').replace('data-label-name="b"', 'data-label-id="12"').replace(
        'data-label-name="c"', 'data-label-id="13"')
    assert cvat_smoke.check_svg(by_id, {11: 'a', 12: 'b', 13: 'c'}, names, edges) == []
    assert cvat_smoke.check_svg(by_id, {11: 'a', 12: 'c', 13: 'b'}, names, edges)              # nối nhầm điểm: cặp cạnh khác
    assert cvat_smoke.check_svg('', {}, names, edges)
    assert cvat_smoke.check_svg(by_name, {}, names, edges | {frozenset(('a', 'c'))})


# ---------- SmokeJob (nút ở tab Cài đặt): lệnh, môi trường, khoá, huỷ, đọc báo cáo ----------
import time  # noqa: E402

import cai_dat_ui  # noqa: E402
import nap_anh  # noqa: E402


def _wait(job, t=120):
    t0 = time.time()
    while job.running and time.time() - t0 < t:
        time.sleep(0.05)


def _spy(seen, code):
    def popen(cmd, **kw):
        seen.update(cmd=cmd, **kw)
        return subprocess.Popen([sys.executable, '-c', code], **kw)
    return popen


def test_smoke_job_command_env_lock_and_scrub(cvat):
    runs = os.path.join(cvat.root, 'runs')
    seen = {}
    rep = ("import os,json,sys; d=os.path.join('runs','_smoke'); p=os.path.join(d,'bao_cao_20261006_101010.json'); "
           "json.dump({'buoc':[{'ma':1,'ten':'<b>x</b>','ket_qua':'HỎNG','ghi_chu':'g','con':[]}],'tong':'Có 1 bước HỎNG'}, open(p,'w',encoding='utf-8')); "
           "print('[2/12] XML nháp cục bộ: đang chạy…'); print('token', os.environ['CVAT_ACCESS_TOKEN']); print(open(os.path.join(d,'.dang_chay')).read()); "
           "print('SMOKE_JSON: '+os.path.abspath(p))")
    job = nap_anh.SmokeJob(popen=_spy(seen, rep))
    job.start(runs, cvat.root, giu_task=True)
    with pytest.raises(nap_anh.RunError):
        job.start(runs, cvat.root)                                                    # đang chạy: không chạy hai lần
    _wait(job)
    snap = job.snapshot()
    assert snap['state'] == 'xong' and snap['kind'] == 'cvat_smoke' and snap['run'] == '_smoke'
    cmd = seen['cmd']
    assert cmd[1] == '-u' and cmd[2].endswith('cvat_smoke.py') and '--giu-task' in cmd and cmd[cmd.index('--root') + 1] == cvat.root
    assert not any(TOKEN in c or URL in c for c in cmd)
    assert seen['env']['CVAT_ACCESS_TOKEN'] == TOKEN and seen['env']['CVAT_URL'] == URL and seen['cwd'] == cvat.root and 'shell' not in seen
    log = open(os.path.join(runs, '_smoke', 'smoke_log.txt'), encoding='utf-8').read()
    assert TOKEN not in log and 'token ***' in log and '"kind": "cvat_smoke"' in log
    assert not os.path.exists(os.path.join(runs, '_smoke', '.dang_chay'))             # khoá được gỡ khi xong
    rp = nap_anh.read_smoke_report(snap['run_dir'], snap['lines'])
    assert rp and rp['tong'] == 'Có 1 bước HỎNG'
    h = cai_dat_ui.smoke_result_html(rp, os.path.join(runs, '_smoke', 'bao_cao_20261006_101010.json'))
    assert '<b>x</b>' not in h and '&lt;b&gt;x&lt;/b&gt;' in h and 'Gửi cho P4' in h and 'bao_cao_20261006_101010.txt' in h and 'sm-hong' in h


def test_smoke_job_cancel_and_report_path_safety(cvat, tmp_path):
    runs = os.path.join(cvat.root, 'runs')
    job = nap_anh.SmokeJob(popen=_spy({}, "import time; print('[3/12] Link và token: đang chạy…', flush=True); time.sleep(60)"))
    job.start(runs, cvat.root)
    time.sleep(0.5)
    assert job.cancel() is True and job.snapshot()['state'] == 'da_huy' and job.cancel() is False
    run_dir = os.path.join(runs, '_smoke')
    outside = tmp_path / 'bao_cao_20261006_101010.json'
    outside.write_text('{"buoc": [], "tong": "x"}')
    assert nap_anh.read_smoke_report(run_dir, ['SMOKE_JSON: ' + str(outside)]) is None             # ngoài runs\_smoke
    inside = os.path.join(run_dir, 'khac.json')
    open(inside, 'w').write('{"buoc": []}')
    assert nap_anh.read_smoke_report(run_dir, ['SMOKE_JSON: ' + inside]) is None                    # sai tên
    assert nap_anh.read_smoke_report(run_dir, []) is None


def test_smoke_progress_lines():
    assert nap_anh.smoke_progress([])['k'] == 0
    p = nap_anh.smoke_progress(['[1/12] Cấu hình cục bộ: ĐẠT. ok', '[4/6] tải ảnh: x', '[5/12] Project và label skeleton: đang chạy…'])
    assert p['k'] == 5 and abs(p['frac'] - 4 / 12) < 1e-9 and p['ket_qua'] is None and 'Bước 5/12' in p['label']
    p = nap_anh.smoke_progress(['[12/12] Project sau khi chạy: HỎNG. x'])
    assert p['frac'] == 1.0 and p['ket_qua'] == 'HỎNG'


def test_smoke_job_runs_real_cvat_smoke_against_fake_cvat(cvat, tmp_path, monkeypatch):
    monkeypatch.setenv('PYTHONPATH', FAKE)
    monkeypatch.setenv('M28_FAKE_CVAT_STATE', str(tmp_path / 'st.json'))
    runs = os.path.join(cvat.root, 'runs')
    job = nap_anh.SmokeJob()
    job.start(runs, cvat.root)
    _wait(job)
    snap = job.snapshot()
    assert snap['state'] == 'xong', '\n'.join(snap['lines'][-15:])
    rp = nap_anh.read_smoke_report(snap['run_dir'], snap['lines'])
    assert rp and rp['tong'] == 'Tất cả ĐẠT' and nap_anh.smoke_progress(snap['lines'])['k'] == 12
    html_ = cai_dat_ui.smoke_result_html(rp, 'bao_cao_20261006_101010.json') + cai_dat_ui.smoke_prog_html(snap, nap_anh.smoke_progress(snap['lines']))
    assert TOKEN not in html_ and TOKEN not in '\n'.join(snap['lines'])
    for path, data in all_files_text(cvat.root):
        assert TOKEN.encode() not in data, path


def test_ui_html_confirm_and_progress():
    h = cai_dat_ui.smoke_confirm_html('http://localhost:8080')
    assert 'demo-smoke' in h and 'project m28' in h and 'http://localhost:8080' in h and 'Không đụng task khác' in h and 'XOÁ' in h
    assert '<script' not in cai_dat_ui.smoke_confirm_html('<script>x</script>')
    snap = dict(state='dang_chay', returncode=None, elapsed=75.0, cancelling=False, lines=[])
    assert 'role="progressbar"' in cai_dat_ui.smoke_prog_html(snap, dict(frac=0.5, label='Bước 6/12')) and '01:15' in cai_dat_ui.smoke_prog_html(
        snap, dict(frac=0.5, label='Bước 6/12'))
    assert cai_dat_ui.smoke_prog_html(dict(snap, state='chua'), dict(frac=0, label='')) == ''


def test_smoke_blocks_page_close_and_settings(cvat, tmp_path):
    import review_app as ra
    ctx = ra.AppCtx(reviewer='P1', run_dir=os.path.join(cvat.root, 'runs', '_nap'), nap_only=True)
    assert isinstance(ctx.smoke_job, nap_anh.SmokeJob)
    ctx.smoke_job.state = 'dang_chay'
    ok, why, _lv = ra.close_check(None, ctx)
    assert not ok and 'kiểm tra nhanh' in why
    ctx.smoke_job.state = 'chua'
    assert ra.close_check(None, ctx)[0]


def test_smoke_handlers_in_settings_tab_cross_lock(cvat, monkeypatch):
    """Dựng trang thật (Gradio, không mở trình duyệt, không server) và gọi thẳng các handler: khoá chéo, từ chối khi đóng trang, không chạy hai lần."""
    pytest.importorskip('gradio')
    monkeypatch.setenv('GRADIO_ANALYTICS_ENABLED', 'False')
    import review_app as ra
    ctx = ra.AppCtx(reviewer='P1', run_dir=os.path.join(cvat.root, 'runs', '_nap'), nap_only=True)
    demo = ra.build_ui(None, ctx)
    demo = demo[0] if isinstance(demo, tuple) else demo
    fns = {}
    for f in demo.fns.values():
        fn = getattr(f.fn, '__wrapped__', f.fn)
        if getattr(getattr(fn, '__code__', None), 'co_filename', '').endswith('cai_dat_ui.py'):
            fns.setdefault(getattr(f.fn, '__name__', ''), f.fn)
    MSG = 2                                                                            # chỉ số smoke_msg trong sm_outs
    r = fns['on_smoke_open']()
    assert r[0]['visible'] is True and 'demo-smoke' in r[1] and 'Giữ task' not in r[1]                  # hộp xác nhận mở, chưa chạy gì
    assert ctx.smoke_job.state == 'chua'
    ctx.push_job.state = 'dang_chay'
    ctx.push_job.run = 'Khoi'
    r = fns['on_smoke_open']()
    assert 'chờ xong' in r[MSG] and 'Khoi' in r[MSG]
    r = fns['on_smoke_ok'](False)
    assert 'chờ xong' in r[MSG] and ctx.smoke_job.state == 'chua'                                     # không tự chạy khi đẩy đang chạy
    ctx.push_job.state = 'chua'
    ctx.smoke_job.state = 'dang_chay'
    r = fns['on_smoke_ok'](False)
    assert 'chạy kiểm tra nhanh' in r[MSG] and ctx.smoke_job.state == 'dang_chay'                      # không chạy hai lần
    save = fns['on_save'](URL, '', '', False, None)                                                    # Lưu token bị từ chối khi đang kiểm tra
    assert 'kiểm tra nhanh' in save[6]
    assert 'kiểm tra nhanh' in fns['on_forget_open'](None)[6]
    ctx.smoke_job.state = 'chua'
    ctx.closing = True
    assert 'đóng' in fns['on_smoke_ok'](False)[MSG].lower()
    ctx.closing = False
    ctx.smoke_job.state = 'chua'
