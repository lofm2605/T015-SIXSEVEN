"""Thử hợp đồng của nút Merge jobs & Finish: collect --overwrite / --require-completed (m28core/collect.py, m28.py) và CollectJob, collect_cmd,
read_collect_result (tool/nap_anh.py), bằng CVAT GIẢ (tests/fake_cvat/cvat_sdk) và tiến trình con giả. Không mạng, không ảnh mặt.

Hợp đồng (trang rà soát dựng UI trên đó, không đổi): dòng máy đọc `COLLECT_XML: {task, nguoi, xml, jobs, moi}` và
`COLLECT_JOBS_PENDING: {task, jobs, pending}` (JSON một dòng), mã thoát 3 (EXIT_CHUA_XONG) khi --require-completed chặn, bản cũ dời vào raw/_cu/.
Phần kiểm trên CVAT THẬT nằm ở tool/cvat_smoke.py bước 9 (tests/test_cvat_smoke.py thử bằng CVAT giả).
"""
import datetime
import json
import os
import re
import subprocess
import sys
import time
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
from test_push import FAKE, TOKEN, URL, calls, collect_args, cvat, do_push, make_run, pj, pushed, state  # noqa: E402,F401  (cvat, pushed: fixture)
import m28  # noqa: E402
import nap_anh as na  # noqa: E402
from m28core import collect, dang_chay  # noqa: E402

TASK = 'demo-Khoi'


def day():
    return datetime.datetime.now().strftime('%d%m')


def base(who='P4', task=TASK):
    return f'raw/{task}_{who}_{day()}'


def lines_of(out, prefix):
    """Các dòng máy đọc `<prefix>{JSON}` (đã parse) trong stdout."""
    return [json.loads(ln[len(prefix):]) for ln in out.splitlines() if ln.startswith(prefix)]


def job_ids(cvat_mod, task=TASK):
    t = next(t for t in state(cvat_mod)['tasks'] if t['name'] == task)
    return [j['id'] for j in t['jobs']]


def set_jobs(cvat_mod, task=TASK, **upd):
    for t in state(cvat_mod)['tasks']:
        if t['name'] == task:
            for j in t['jobs']:
                j.update(upd)


def raw_files():
    out = []
    for dp, _dn, fn in os.walk('raw'):
        out += [os.path.relpath(os.path.join(dp, f)).replace('\\', '/') for f in fn]
    return sorted(out)


def read(p, mode='rb'):
    with open(p, mode) as f:
        return f.read()


# ---------- cat_ban_cu (thuần) ----------
def test_cat_ban_cu_moves_xml_txt_and_job_files_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs('raw')
    b = 'raw/demo-A_P1_1110'
    mine = [b + '.xml', b + '.txt', b + '_job100.xml', b + '_job100.txt', b + '_job101.xml']
    others = ['raw/demo-A_P2_1110.xml', 'raw/demo-A_P1_0910.xml', 'raw/demo-AB_P1_1110.xml', 'raw/demo-A_P1_1110x.xml']
    for p in mine + others:
        open(p, 'w').write(p)
    moved = collect.cat_ban_cu(b, 'raw', stamp='101010')
    assert [os.path.basename(p) for p in moved] == ['demo-A_P1_1110.cu101010.xml', 'demo-A_P1_1110.cu101010.txt', 'demo-A_P1_1110_job100.cu101010.txt',
                                                    'demo-A_P1_1110_job100.cu101010.xml', 'demo-A_P1_1110_job101.cu101010.xml']
    assert all(os.path.dirname(p) == os.path.join('raw', '_cu') for p in moved)
    assert not any(os.path.exists(p) for p in mine) and all(read(p, 'r') == p for p in others)
    for p in mine:                                                                     # nội dung giữ nguyên, không xoá gì
        s, e = os.path.splitext(os.path.basename(p))
        assert read(os.path.join('raw', '_cu', f'{s}.cu101010{e}'), 'r') == p
    for p in mine[:2]:                                                                 # trùng giờ: thêm -2, không ghi đè bản trong _cu
        open(p, 'w').write('lần hai')
    again = collect.cat_ban_cu(b, 'raw', stamp='101010')
    assert [os.path.basename(p) for p in again] == ['demo-A_P1_1110.cu101010-2.xml', 'demo-A_P1_1110.cu101010-2.txt']
    assert read('raw/_cu/demo-A_P1_1110.cu101010.xml', 'r') == mine[0] and read(again[0], 'r') == 'lần hai'
    assert collect.cat_ban_cu(b, 'raw') == []                                          # không còn gì: không tạo gì


def test_jobs_info_reads_enum_value_and_type():
    class E:                                                                           # như ModelSimple của cvat-sdk: chữ thật ở .value
        def __init__(self, v):
            self.value = v

        def __str__(self):
            return f'E({self.value!r})'
    jobs = [types.SimpleNamespace(id=7, start_frame=4, stop_frame=5, stage=E('validation'), state=E('in progress'), type=E('ground_truth')),
            types.SimpleNamespace(id=5, start_frame=0, stop_frame=3, stage='annotation', state='new'),                    # không có type: annotation
            types.SimpleNamespace(id=9, start_frame=6, stop_frame=6, stage='annotation', state='completed', type=None)]
    got = collect._jobs_info(types.SimpleNamespace(get_jobs=lambda: jobs), {5: 'nhan'})
    assert [(j['id'], j['n'], j['stage'], j['state'], j['type'], j['kind']) for j in got] == [
        (5, 4, 'annotation', 'new', 'annotation', 'nhan'), (7, 2, 'validation', 'in progress', 'ground_truth', 'khong_ro'),
        (9, 1, 'annotation', 'completed', 'annotation', 'khong_ro')]
    json.dumps(got)                                                                    # dòng máy đọc: JSON được
    assert [j['id'] for j in collect.jobs_chua_xong(got)] == [5]                       # job ground_truth bỏ qua, completed không tính
    assert [j['id'] for j in collect.jobs_chua_xong([dict(id=1, state='new'), dict(id=2, state='new', type='consensus_replica'),
                                                     dict(id=3, state='rejected', type='annotation'), dict(id=4, state='completed')])] == [1, 3]


# ---------- --overwrite ----------
def test_overwrite_moves_old_files_into_cu_and_writes_fresh(cvat, pushed, capsys):
    assert collect.collect(collect_args()) is True                                    # lần đầu: cả task + file từng job (mặc định cho demo-)
    b = base()
    first = raw_files()
    assert {b + '.xml', b + '.txt'} <= set(first) and len([p for p in first if '_job' in p]) == 4
    open(b + '.xml', 'ab').write('<!-- bản cũ -->'.encode('utf-8'))
    old = {p: read(p) for p in first}
    n_ex = len(calls(cvat, 'Task.export_dataset'))
    capsys.readouterr()
    assert collect.collect(collect_args(overwrite=True)) is True
    out = capsys.readouterr().out
    assert len(calls(cvat, 'Task.export_dataset')) == n_ex + 1                        # xuất lại đúng một lần
    cu = [p for p in raw_files() if p.startswith('raw/_cu/')]
    assert len(cu) == len(first)
    for p, data in old.items():                                                        # mỗi file cũ có đúng một bản trong raw/_cu, nguyên byte
        s, e = os.path.splitext(os.path.basename(p))
        hit = [q for q in cu if re.fullmatch(re.escape(f'raw/_cu/{s}.cu') + r'\d{6}' + re.escape(e), q)]
        assert len(hit) == 1, (p, cu)
        assert read(hit[0]) == data
    assert set(first) <= set(raw_files())                                             # bản mới ghi lại đủ: cả task, .txt, file job
    assert not read(b + '.xml').endswith('<!-- bản cũ -->'.encode('utf-8')) and b'<annotations>' in read(b + '.xml')
    assert 'task: demo-Khoi' in read(b + '.txt', 'r') and not [p for p in raw_files() if '.tmp' in p]
    assert '--overwrite: bản cũ chuyển vào' in out and 'KHÔNG ghi đè' not in out
    xl = lines_of(out, collect.DONG_XML)
    assert len(xl) == 1 and xl[0]['moi'] is True and xl[0]['xml'] == b + '.xml' and xl[0]['task'] == TASK and xl[0]['nguoi'] == 'P4'
    assert [j['id'] for j in xl[0]['jobs']] == job_ids(cvat) and {j['state'] for j in xl[0]['jobs']} == {'new'}


def test_overwrite_also_moves_leftover_txt_and_job_files_when_xml_is_gone(cvat, pushed, capsys):
    collect.collect(collect_args())
    b = base()
    os.remove(b + '.xml')                                                              # người dùng lỡ xoá file cả task, .txt và file job còn
    left = raw_files()
    capsys.readouterr()
    collect.collect(collect_args(overwrite=True))
    cu = [p for p in raw_files() if p.startswith('raw/_cu/')]
    assert len(cu) == len(left) and os.path.exists(b + '.xml')
    out = capsys.readouterr().out
    assert 'đã có: KHÔNG ghi đè' not in out                                           # file job mới ghi lại, không vấp file job cũ


def test_overwrite_export_failure_keeps_old_files_in_place(cvat, pushed):
    collect.collect(collect_args())
    before = {p: read(p) for p in raw_files()}
    cvat.CONTROL['export_fail'] = True
    with pytest.raises(SystemExit) as e:
        collect.collect(collect_args(overwrite=True))
    assert isinstance(e.value.code, str) and ('500' in e.value.code or 'xuất' in e.value.code)
    assert {p: read(p) for p in raw_files()} == before                                # không dời, không ghi gì
    assert not os.path.exists(os.path.join('raw', '_cu'))
    assert TOKEN not in e.value.code


def test_without_overwrite_keeps_old_file_and_hints_overwrite(cvat, pushed, capsys):
    collect.collect(collect_args())
    b = base()
    open(b + '.xml', 'ab').write(b'<!-- sua tay -->')
    n_ex = len(calls(cvat, 'Task.export_dataset'))
    capsys.readouterr()
    assert collect.collect(collect_args()) is True
    out = capsys.readouterr().out
    assert len(calls(cvat, 'Task.export_dataset')) == n_ex and read(b + '.xml').endswith(b'<!-- sua tay -->')
    assert 'KHÔNG ghi đè' in out and '--overwrite' in out and os.path.join('raw', '_cu') in out
    assert not os.path.exists(os.path.join('raw', '_cu'))
    xl = lines_of(out, collect.DONG_XML)
    assert len(xl) == 1 and xl[0]['moi'] is False and xl[0]['xml'] == b + '.xml'


def test_overwrite_dry_run_writes_and_moves_nothing(cvat, pushed, capsys):
    collect.collect(collect_args())
    before = {p: read(p) for p in raw_files()}
    n_ex = len(calls(cvat, 'Task.export_dataset'))
    capsys.readouterr()
    assert collect.collect(collect_args(overwrite=True, dry_run=True)) is True
    out = capsys.readouterr().out
    assert 'sẽ xuất lại' in out and 'Chạy thử' in out
    assert {p: read(p) for p in raw_files()} == before and len(calls(cvat, 'Task.export_dataset')) == n_ex
    assert lines_of(out, collect.DONG_XML) == []


# ---------- --require-completed ----------
def test_require_completed_with_new_jobs_exits_3_and_writes_nothing(cvat, pushed, capsys):
    n_ex = len(calls(cvat, 'Task.export_dataset'))
    capsys.readouterr()
    with pytest.raises(SystemExit) as e:
        collect.collect(collect_args(require_completed=True, overwrite=True, per_job=False))
    assert e.value.code == collect.EXIT_CHUA_XONG == 3
    assert not os.path.exists('raw') and not os.path.exists('outputs')
    assert len(calls(cvat, 'Task.export_dataset')) == n_ex                            # chưa xuất gì
    out = capsys.readouterr().out
    ids = job_ids(cvat)
    pend = lines_of(out, collect.DONG_CHUA_XONG)
    assert len(pend) == 1 and pend[0]['task'] == TASK and pend[0]['pending'] == ids
    kinds = {j['id']: j['kind'] for j in pj(pushed)['jobs']}
    assert [(j['id'], j['state'], j['type'], j['kind']) for j in pend[0]['jobs']] == [(i, 'new', 'annotation', kinds[i]) for i in ids]
    assert f'{len(ids)}/{len(ids)} job chưa completed' in out and 'CHƯA xuất gì' in out and 'Finish the job' in out
    assert lines_of(out, collect.DONG_XML) == []


def test_require_completed_blocks_before_moving_old_file(cvat, pushed, capsys):
    collect.collect(collect_args(per_job=False))
    before = {p: read(p) for p in raw_files()}
    set_jobs(cvat, state='completed')
    state(cvat)['tasks'][0]['jobs'][-1]['state'] = 'in progress'                       # một job còn đang sửa
    with pytest.raises(SystemExit) as e:
        collect.collect(collect_args(require_completed=True, overwrite=True, per_job=False))
    assert e.value.code == 3 and {p: read(p) for p in raw_files()} == before
    pend = lines_of(capsys.readouterr().out, collect.DONG_CHUA_XONG)
    assert pend[0]['pending'] == [job_ids(cvat)[-1]] and pend[0]['jobs'][-1]['state'] == 'in progress'


def test_require_completed_all_completed_exports_and_reports(cvat, pushed, capsys):
    set_jobs(cvat, state='completed', stage='acceptance')
    capsys.readouterr()
    assert collect.collect(collect_args(require_completed=True, overwrite=True, per_job=False)) is True
    out = capsys.readouterr().out
    b = base()
    assert raw_files() == sorted([b + '.xml', b + '.txt'])                            # --no-per-job: không file job
    assert lines_of(out, collect.DONG_CHUA_XONG) == []
    xl = lines_of(out, collect.DONG_XML)
    assert len(xl) == 1 and xl[0]['moi'] is True and {(j['stage'], j['state']) for j in xl[0]['jobs']} == {('acceptance', 'completed')}
    assert 'tất cả completed' in read('outputs/collect_demo-Khoi.md', 'r')
    assert 'state completed' in read(b + '.txt', 'r')


def test_require_completed_ignores_ground_truth_jobs(cvat, pushed, capsys):
    set_jobs(cvat, state='completed')
    t = state(cvat)['tasks'][0]
    t['jobs'].append(dict(id=999, start_frame=0, stop_frame=0, stage='annotation', state='new', type='ground_truth'))
    capsys.readouterr()
    assert collect.collect(collect_args(require_completed=True, overwrite=True, per_job=False)) is True
    out = capsys.readouterr().out
    xl = lines_of(out, collect.DONG_XML)
    assert {j['id']: j['type'] for j in xl[0]['jobs']}[999] == 'ground_truth'
    assert 'tất cả completed' in read('outputs/collect_demo-Khoi.md', 'r')          # báo cáo cùng quy tắc: job ground_truth không tính
    t['jobs'][0]['state'] = 'new'                                                      # job annotation chưa xong: chỉ job đó bị nêu
    with pytest.raises(SystemExit) as e:
        collect.collect(collect_args(require_completed=True, overwrite=True, per_job=False))
    assert e.value.code == 3
    assert lines_of(capsys.readouterr().out, collect.DONG_CHUA_XONG)[0]['pending'] == [t['jobs'][0]['id']]


def test_require_completed_dry_run_prints_but_returns(cvat, pushed, capsys):
    capsys.readouterr()
    assert collect.collect(collect_args(require_completed=True, dry_run=True)) is True
    out = capsys.readouterr().out
    pend = lines_of(out, collect.DONG_CHUA_XONG)
    assert len(pend) == 1 and pend[0]['pending'] == job_ids(cvat)
    assert 'Chạy thử' in out and 'CHƯA xuất gì' not in out
    assert not os.path.exists('raw') and not os.path.exists('outputs')


# ---------- task thiếu / trùng tên trên CVAT (C9/C12) ----------
def outputs_files():
    return sorted(os.path.join(dp, f) for dp, _dn, fn in os.walk('outputs') for f in fn)


def snapshot():
    return {p: read(p) for p in raw_files() + outputs_files()}


@pytest.mark.parametrize('flags', [dict(overwrite=True), dict(require_completed=True), dict(overwrite=True, require_completed=True, per_job=False)])
def test_button_mode_task_missing_on_cvat_stops_with_the_real_cause(cvat, pushed, capsys, flags):
    """Task bị xoá/đổi tên trong CVAT (push.json vẫn 'xong'): chế độ của nút phải DỪNG với lý do thật (mã khác 0), không 'collect xong … còn thiếu: 1',
    không dựng lại báo cáo từ file raw cũ của người khác, không xuất, không ghi file nào."""
    collect.collect(collect_args(reviewer='P2'))                                          # file raw cũ của người khác + báo cáo cũ
    state(cvat)['tasks'][0]['name'] = 'demo-Khac'
    before, n_ex = snapshot(), len(calls(cvat, 'Task.export_dataset'))
    capsys.readouterr()
    with pytest.raises(SystemExit) as e:
        collect.collect(collect_args(**flags))
    msg = e.value.code
    assert isinstance(msg, str) and '\n' not in msg
    assert 'task demo-Khoi không thấy trên CVAT' in msg and URL in msg and 'đã bị xoá hoặc đổi tên' in msg
    assert 'chưa xuất và chưa ghi file nào' in msg and 'Cách sửa' in msg and 'đẩy lại đợt' in msg and 'Merge jobs & Finish' in msg
    assert ('--overwrite' in msg) == bool(flags.get('overwrite')) and ('--require-completed' in msg) == bool(flags.get('require_completed'))
    assert snapshot() == before and len(calls(cvat, 'Task.export_dataset')) == n_ex
    out = capsys.readouterr().out
    assert 'demo-Khoi: KHÔNG thấy task tên này trên CVAT.' in out and 'bỏ qua' not in out and 'collect xong' not in out
    assert lines_of(out, collect.DONG_XML) == [] and lines_of(out, collect.DONG_CHUA_XONG) == [] and TOKEN not in msg + out


def test_button_mode_duplicate_task_name_stops_and_names_the_task_to_keep(cvat, pushed, capsys):
    st = state(cvat)
    keep = pj(pushed)['task_id']
    st['tasks'].append(dict(st['tasks'][0], id=keep + 50))                                # bản thừa cùng tên (ví dụ khôi phục file sao lưu)
    set_jobs(cvat, state='completed')                                                     # job xong cả: trước đây sẽ gộp mà không nói gì
    n_ex = len(calls(cvat, 'Task.export_dataset'))                                        # lần xuất kiểm của push
    with pytest.raises(SystemExit) as e:
        collect.collect(collect_args(overwrite=True, require_completed=True, per_job=False))
    msg = e.value.code
    assert isinstance(msg, str) and '\n' not in msg
    assert f'task demo-Khoi trùng tên 2 task trên CVAT (id {keep}, {keep + 50})' in msg and 'xoá hoặc đổi tên bản thừa' in msg
    assert f'giữ task id {keep} (theo runs\\Khoi\\push.json)' in msg and 'không thấy' not in msg
    assert not os.path.exists('raw') and not os.path.exists('outputs') and len(calls(cvat, 'Task.export_dataset')) == n_ex
    out = capsys.readouterr().out
    assert 'trùng tên' in out and 'bỏ qua' not in out and lines_of(out, collect.DONG_XML) == []


def test_button_mode_blocks_every_task_when_one_is_missing(cvat, pushed):
    n_ex = len(calls(cvat, 'Task.export_dataset'))
    with pytest.raises(SystemExit) as e:
        collect.collect(collect_args(task=[TASK, 'demo-Nam'], overwrite=True))
    assert 'task demo-Nam không thấy trên CVAT' in e.value.code and 'demo-Khoi' not in e.value.code.split('Cách sửa')[0]
    assert not os.path.exists('raw') and not os.path.exists('outputs') and len(calls(cvat, 'Task.export_dataset')) == n_ex     # demo-Khoi cũng chưa xuất


def test_plain_collect_keeps_skipping_a_missing_task_with_exit_0(cvat, pushed, capsys):
    """Không có --overwrite/--require-completed: giữ cách cũ (in 'bỏ qua', ghi 'File còn thiếu', thoát 0)."""
    state(cvat)['tasks'][0]['name'] = 'demo-Khac'
    capsys.readouterr()
    assert m28.main(['collect', '--task', TASK, '--reviewer', 'P4']) is None
    out = capsys.readouterr().out
    assert 'KHÔNG thấy task tên này trên CVAT, bỏ qua.' in out and out.rstrip().splitlines()[-1].endswith('còn thiếu: 1')
    assert 'demo-Khoi (không có trên CVAT)' in read('outputs/collect_demo-Khoi.md', 'r') and not os.path.exists('raw')


def test_button_mode_dry_run_only_warns_for_a_missing_task(cvat, pushed, capsys):
    state(cvat)['tasks'][0]['name'] = 'demo-Khac'
    capsys.readouterr()
    assert collect.collect(collect_args(overwrite=True, require_completed=True, dry_run=True)) is True
    out = capsys.readouterr().out
    assert 'bỏ qua. Chạy thật với --overwrite/--require-completed sẽ dừng ở đây.' in out and 'Chạy thử' in out
    assert not os.path.exists('raw') and not os.path.exists('outputs')


def test_merge_child_for_a_missing_task_exits_1_and_last_line_is_the_cause(cvat, tmp_path, monkeypatch):
    """Tiến trình con THẬT (m28.py collect của nút) với CVAT giả: task đã bị đổi tên trong CVAT -> mã 1, dòng cuối (thứ trang lấy làm nguyên nhân) là lý do thật."""
    import day_cvat
    monkeypatch.setenv('PYTHONPATH', FAKE)
    st_file = str(tmp_path / 'cvat_state.json')
    monkeypatch.setenv('M28_FAKE_CVAT_STATE', st_file)
    json.dump(json.load(open(os.path.join(HERE, '..', 'config', 'm28_config.json'), encoding='utf-8')), open('config/m28_config.json', 'w'))
    do_push(make_run(n_nhan=2, n_tay=1), TASK)
    st = json.load(open(st_file, encoding='utf-8'))
    st['tasks'][0]['name'] = 'demo-Khoi-cu'
    json.dump(st, open(st_file, 'w', encoding='utf-8'))
    job = na.CollectJob()
    job.start('Khoi', 'runs', os.getcwd(), 'P3', TASK)
    _wait(job)
    snap = job.snapshot()
    assert snap['state'] == 'loi' and snap['returncode'] == 1, '\n'.join(snap['lines'][-15:])
    cause = day_cvat.last_message(snap['lines'])
    assert cause.startswith('collect --overwrite --require-completed dừng') and 'task demo-Khoi không thấy trên CVAT' in cause and 'collect xong' not in cause
    assert na.read_collect_result(snap['lines'], os.getcwd(), TASK, 'P3') == dict(xml=None, xml_rel='', jobs=[], pending=None)
    assert not os.path.exists('raw') and not os.path.exists('outputs') and dang_chay.busy(os.path.join('runs', 'Khoi')) is None


def test_new_flags_refused_with_skip_export(cvat):
    for flag in ('overwrite', 'require_completed'):
        with pytest.raises(SystemExit) as e:
            collect.collect(collect_args(skip_export=True, **{flag: True}))
        assert '--skip-export' in str(e.value.code) and e.value.code != 3
    assert calls(cvat) == [] and not os.path.exists('raw')


# ---------- m28.py: cờ và mã thoát ----------
def test_m28_cli_merge_command_exit_code_3_then_exports(cvat, pushed, capsys):
    argv = na.collect_cmd(TASK, 'P1')[3:]
    a = m28.build_parser().parse_args(argv)
    assert a.cmd == 'collect' and a.task == [TASK] and a.reviewer == 'P1' and a.overwrite and a.require_completed and a.per_job is False
    with pytest.raises(SystemExit) as e:
        m28.main(argv)
    assert e.value.code == 3 and not os.path.exists('raw')
    set_jobs(cvat, state='completed')
    m28.main(argv)
    assert raw_files() == sorted([base('P1') + '.xml', base('P1') + '.txt'])
    m28.main(na.collect_cmd(TASK, 'P1', force=True)[3:])                               # gộp lại: bản cũ vào raw/_cu
    assert len([p for p in raw_files() if p.startswith('raw/_cu/')]) == 2
    for bad in (['collect', '--task', TASK, '--overwrite', '--skip-export'], ['collect', '--task', TASK, '--require-completed', '--skip-export']):
        with pytest.raises(SystemExit) as e:
            m28.main(bad)
        assert e.value.code == 2


# ---------- collect_cmd ----------
def test_collect_cmd_argv_without_token(monkeypatch):
    monkeypatch.setenv('CVAT_ACCESS_TOKEN', TOKEN)
    cmd = na.collect_cmd(TASK, 'P3')
    assert cmd[0] == sys.executable and cmd[1] == '-u' and cmd[2] == os.path.join(na.TOOL_DIR, 'm28.py')
    assert cmd[3:] == ['collect', '--task', TASK, '--reviewer', 'P3', '--overwrite', '--no-per-job', '--require-completed']
    cmd = na.collect_cmd(TASK, 'P3', tool_dir='T', python='py', force=True)
    assert cmd == ['py', '-u', os.path.join('T', 'm28.py'), 'collect', '--task', TASK, '--reviewer', 'P3', '--overwrite', '--no-per-job']
    assert not any(TOKEN in c or 'token' in c.lower() for c in na.collect_cmd(TASK, 'P3') + cmd)
    assert (na.EXIT_CHUA_XONG, na.DONG_XML, na.DONG_CHUA_XONG) == (collect.EXIT_CHUA_XONG, collect.DONG_XML, collect.DONG_CHUA_XONG)


# ---------- CollectJob (tiến trình con giả) ----------
def _fake_popen(body, seen=None):
    def popen(cmd, **kw):
        if seen is not None:
            seen.update(cmd=cmd, **kw)
        return subprocess.Popen([sys.executable, '-c', body], **kw)
    return popen


def _wait(job, timeout=60):
    t = time.time()
    while job.running and time.time() - t < timeout:
        time.sleep(0.05)


@pytest.fixture
def page(tmp_path, monkeypatch):
    """Thư mục dự án tạm có runs/Khoi (một đợt), không biến CVAT_* nào."""
    monkeypatch.chdir(tmp_path)
    for v in ('CVAT_URL', 'CVAT_ACCESS_TOKEN', 'CVAT_ORG'):
        monkeypatch.delenv(v, raising=False)
    os.makedirs(os.path.join('runs', 'Khoi'))
    return tmp_path


def test_collect_job_command_env_lock_and_log_scrub(page, monkeypatch):
    monkeypatch.setenv('CVAT_ACCESS_TOKEN', TOKEN)
    monkeypatch.setenv('CVAT_URL', URL)
    rd = os.path.join('runs', 'Khoi')
    seen = {}
    job = na.CollectJob(popen=_fake_popen("import os,time; print('token', os.environ['CVAT_ACCESS_TOKEN'], flush=True); "
                                          "print(open('runs/Khoi/.dang_chay').read(), flush=True); time.sleep(0.3)", seen))
    assert job.snapshot()['kind'] == 'collect' and job.snapshot()['person'] is None
    job.start('Khoi', 'runs', str(page), 'P1', TASK)
    assert dang_chay.busy(rd)[0] == 'collect'
    with pytest.raises(na.RunError, match='Đang gộp'):
        job.start('Khoi', 'runs', str(page), 'P1', TASK)
    _wait(job)
    snap = job.snapshot()
    assert snap['state'] == 'xong' and snap['kind'] == 'collect' and snap['run'] == 'Khoi'
    assert (snap['person'], snap['task'], snap['force']) == ('P1', TASK, False)
    cmd = seen['cmd']
    assert cmd[1] == '-u' and cmd[2].endswith('m28.py')
    assert cmd[3:] == ['collect', '--task', TASK, '--reviewer', 'P1', '--overwrite', '--no-per-job', '--require-completed']
    assert not any(TOKEN in c for c in cmd) and seen['env']['CVAT_ACCESS_TOKEN'] == TOKEN and seen['env']['CVAT_URL'] == URL
    assert seen['env']['PYTHONUTF8'] == '1' and seen['cwd'] == str(page) and seen['stdin'] == subprocess.DEVNULL and 'shell' not in seen
    log = read(os.path.join(rd, 'collect_log.txt'), 'r')
    assert TOKEN not in log and 'token ***' in log and '"kind": "collect"' in log and '--require-completed' in log
    assert TOKEN not in '\n'.join(snap['lines'])
    assert dang_chay.busy(rd) is None                                                  # khoá được gỡ khi xong


def test_collect_job_force_drops_require_completed_and_exit_3_is_loi(page):
    seen = {}
    job = na.CollectJob(popen=_fake_popen("print('x')", seen))
    job.start('Khoi', 'runs', str(page), 'P5', TASK, force=True)
    _wait(job)
    assert '--require-completed' not in seen['cmd'] and seen['cmd'][-2:] == ['--overwrite', '--no-per-job']
    assert job.snapshot()['force'] is True and job.snapshot()['person'] == 'P5'
    assert '--require-completed' not in read(os.path.join('runs', 'Khoi', 'collect_log.txt'), 'r').splitlines()[0]
    job = na.CollectJob(popen=_fake_popen("import sys; print('COLLECT_JOBS_PENDING: {}'); sys.exit(3)"))
    job.start('Khoi', 'runs', str(page), 'P1', TASK)
    _wait(job)
    snap = job.snapshot()
    assert snap['state'] == 'loi' and snap['returncode'] == na.EXIT_CHUA_XONG and dang_chay.busy(os.path.join('runs', 'Khoi')) is None


def test_collect_job_rejects_bad_person_task_run(page):
    job = na.CollectJob(popen=_fake_popen('pass'))
    for person in ('P1 ', 'a b', '../P1', 'x' * 33, '', None, 1):
        with pytest.raises(na.RunError, match='chữ, số'):
            job.start('Khoi', 'runs', str(page), person, TASK)
    for task in ('m28-manual', 'demo-', 'demo-a/b', 'demo- x', '', None, 'demo-' + 'a' * 200):
        with pytest.raises(na.RunError):
            job.start('Khoi', 'runs', str(page), 'P1', task)
    for run in ('../Khoi', 'Nam', '', '_trash'):
        with pytest.raises(na.RunError):
            job.start(run, 'runs', str(page), 'P1', TASK)
    assert job.state == 'chua' and dang_chay.busy(os.path.join('runs', 'Khoi')) is None
    assert not os.path.exists(os.path.join('runs', 'Khoi', 'collect_log.txt'))


def test_collect_job_refused_when_run_busy(page, monkeypatch):
    rd = os.path.join('runs', 'Khoi')
    json.dump(dict(kind='push', pid=os.getpid() + 7, t='x'), open(dang_chay.path(rd), 'w'))
    monkeypatch.setattr(dang_chay, 'pid_alive', lambda pid: True)
    job = na.CollectJob(popen=_fake_popen('pass'))
    with pytest.raises(na.RunError, match='việc khác'):
        job.start('Khoi', 'runs', str(page), 'P1', TASK)


def test_collect_job_end_to_end_with_real_m28_child_against_fake_cvat(cvat, tmp_path, monkeypatch):
    """Tiến trình con THẬT (python tool\\m28.py collect ...) với CVAT giả dùng chung qua file trạng thái: mã 3 khi job mới, gộp khi completed,
    --overwrite dời bản cũ khi bấm lại với force."""
    monkeypatch.setenv('PYTHONPATH', FAKE)
    st_file = str(tmp_path / 'cvat_state.json')
    monkeypatch.setenv('M28_FAKE_CVAT_STATE', st_file)
    json.dump(json.load(open(os.path.join(HERE, '..', 'config', 'm28_config.json'), encoding='utf-8')), open('config/m28_config.json', 'w'))
    w = make_run(n_nhan=3, n_tay=1)
    do_push(w, TASK)
    root = os.getcwd()
    job = na.CollectJob()
    job.start('Khoi', 'runs', root, 'P2', TASK)
    _wait(job)
    snap = job.snapshot()
    assert snap['returncode'] == 3 and snap['state'] == 'loi', '\n'.join(snap['lines'][-15:])
    r = na.read_collect_result(snap['lines'], root, TASK, 'P2')
    ids = job_ids(cvat)
    assert r['xml'] is None and [j['id'] for j in r['pending']] == ids and {j['state'] for j in r['jobs']} == {'new'}
    assert not os.path.exists('raw')
    st = json.load(open(st_file, encoding='utf-8'))
    for j in st['tasks'][0]['jobs']:
        j['state'] = 'completed'
    json.dump(st, open(st_file, 'w', encoding='utf-8'))
    job.start('Khoi', 'runs', root, 'P2', TASK)
    _wait(job)
    snap = job.snapshot()
    assert snap['state'] == 'xong', '\n'.join(snap['lines'][-15:])
    r = na.read_collect_result(snap['lines'], root, TASK, 'P2')
    assert r['pending'] is None and r['xml'] == os.path.join(root, 'raw', f'{TASK}_P2_{day()}.xml') and os.path.isfile(r['xml'])
    assert r['xml_rel'] == os.path.join('raw', f'{TASK}_P2_{day()}.xml') and {j['state'] for j in r['jobs']} == {'completed'}
    assert raw_files() == sorted([base('P2') + '.xml', base('P2') + '.txt'])
    job.start('Khoi', 'runs', root, 'P2', TASK, force=True)
    _wait(job)
    snap = job.snapshot()
    assert snap['state'] == 'xong' and na.read_collect_result(snap['lines'], root, TASK, 'P2')['xml'] == r['xml']
    assert len([p for p in raw_files() if p.startswith('raw/_cu/')]) == 2
    log = read(os.path.join('runs', 'Khoi', 'collect_log.txt'), 'r')
    assert TOKEN not in log and log.count('=== ') == 3 and 'COLLECT_XML: ' in log and 'COLLECT_JOBS_PENDING: ' in log
    assert dang_chay.busy(os.path.join('runs', 'Khoi')) is None


# ---------- read_collect_result ----------
def _xml_line(task=TASK, nguoi='P1', xml=None, jobs=None, moi=True):
    xml = xml if xml is not None else f'raw/{task}_{nguoi}_1110.xml'
    return collect.DONG_XML + json.dumps(dict(task=task, nguoi=nguoi, xml=xml, jobs=jobs if jobs is not None else [dict(id=100, state='new')], moi=moi))


@pytest.fixture
def proj(tmp_path):
    os.makedirs(tmp_path / 'raw' / '_cu')
    for n in (f'{TASK}_P1_1110.xml', f'{TASK}_P2_1110.xml', f'{TASK}_P1_1110_job100.xml', f'{TASK}_P1_1110.txt', f'_cu/{TASK}_P1_1110.xml'):
        (tmp_path / 'raw' / n).write_text('<annotations/>')
    os.makedirs(tmp_path / 'other')
    (tmp_path / 'other' / f'{TASK}_P1_1110.xml').write_text('<annotations/>')
    return str(tmp_path)


def test_read_collect_result_accepts_valid_line_and_sanitizes_jobs(proj):
    jobs = [dict(id=100, state='new', stage='annotation', type='annotation', start=0, stop=2, n=3, kind='nhan', extra='x'),
            dict(id=True, state='new'), dict(id='101'), 'rác', dict(id=102, state=123, stage=None, kind='la', start='0', stop=True, n=False),
            dict(id=103, state='x' * 100, type='ground_truth', kind='gan_tay')]
    r = na.read_collect_result(['dòng thường', _xml_line(jobs=jobs)], proj, TASK, 'P1')
    assert r['xml'] == os.path.join(proj, 'raw', f'{TASK}_P1_1110.xml') and r['xml_rel'] == os.path.join('raw', f'{TASK}_P1_1110.xml')
    assert r['pending'] is None
    assert r['jobs'] == [dict(id=100, state='new', stage='annotation', type='annotation', start=0, stop=2, n=3, kind='nhan'),
                         dict(id=102, state='123', stage='None', type='annotation', start=None, stop=None, n=None, kind='khong_ro'),
                         dict(id=103, state='x' * 40, stage='', type='ground_truth', start=None, stop=None, n=None, kind='gan_tay')]
    assert na.read_collect_result([_xml_line(jobs='không phải danh sách')], proj, TASK, 'P1')['jobs'] == []
    for xml in (f'raw\\{TASK}_P1_1110.xml', f'raw/./{TASK}_P1_1110.xml', f'raw/_cu/../{TASK}_P1_1110.xml'):      # dấu \ của Windows, đường vòng
        r = na.read_collect_result([_xml_line(xml=xml)], proj, TASK, 'P1')
        assert r['xml'] == os.path.join(proj, 'raw', f'{TASK}_P1_1110.xml'), xml
    r = na.read_collect_result([_xml_line(xml=f'raw/{TASK}_P2_1110.xml', nguoi='P2'), _xml_line()], proj, TASK, 'P1')
    assert r['xml'].endswith(f'{TASK}_P1_1110.xml')                                   # dòng của người khác bỏ qua, dòng hợp lệ cuối được dùng


@pytest.mark.parametrize('line', [
    _xml_line(xml=f'other/{TASK}_P1_1110.xml'),                       # ngoài raw/
    _xml_line(xml=f'raw/../other/{TASK}_P1_1110.xml'),                # đi vòng ra ngoài raw/
    _xml_line(xml=f'raw/_cu/{TASK}_P1_1110.xml'),                     # thư mục con của raw/ (bản cũ)
    _xml_line(xml=f'/etc/{TASK}_P1_1110.xml'),
    _xml_line(nguoi='P2', xml=f'raw/{TASK}_P2_1110.xml'),             # sai người
    _xml_line(task='demo-Nam', xml=f'raw/{TASK}_P1_1110.xml'),        # sai task
    _xml_line(xml=f'raw/{TASK}_P1_1110_job100.xml'),                  # tên không đúng mẫu (file job)
    _xml_line(xml=f'raw/{TASK}_P1_1110.txt'),
    _xml_line(xml=f'raw/{TASK}_P2_1110.xml'),                         # file của người khác dù dòng ghi nguoi=P1
    _xml_line(xml=f'raw/{TASK}_P1_0101.xml'),                         # đúng mẫu nhưng file không có
    collect.DONG_XML + '{"task": "demo-Khoi", "nguoi": "P1", "xml": ',  # JSON hỏng
    collect.DONG_XML + json.dumps([TASK, 'P1', f'raw/{TASK}_P1_1110.xml']),
    collect.DONG_XML + json.dumps(dict(task=TASK, nguoi='P1', xml=5)),
    '  ' + _xml_line(),                                               # không bắt đầu bằng tiền tố
])
def test_read_collect_result_rejects_bad_lines(proj, line):
    r = na.read_collect_result([line], proj, TASK, 'P1')
    assert r == dict(xml=None, xml_rel='', jobs=[], pending=None)


def test_read_collect_result_pending(proj):
    jobs = [dict(id=100, state='new', stage='annotation', type='annotation'), dict(id=101, state='completed', stage='acceptance'),
            dict(id=1, state='new')]
    line = collect.DONG_CHUA_XONG + json.dumps(dict(task=TASK, jobs=jobs, pending=[100, True, '101', 999]))
    r = na.read_collect_result(['x', line], proj, TASK, 'P1')
    assert r['xml'] is None and [j['id'] for j in r['jobs']] == [100, 101, 1] and [j['id'] for j in r['pending']] == [100]
    assert na.read_collect_result([line], proj, 'demo-Nam', 'P1')['pending'] is None                    # dòng của task khác
    bad = collect.DONG_CHUA_XONG + json.dumps(dict(task=TASK, jobs=jobs, pending='100'))
    assert na.read_collect_result([bad], proj, TASK, 'P1')['pending'] == []
    assert na.read_collect_result([collect.DONG_CHUA_XONG + '{hỏng'], proj, TASK, 'P1')['pending'] is None
    real = collect.DONG_CHUA_XONG + json.dumps(dict(task=TASK, jobs=[dict(id=100, n=3, stage='annotation', state='new', start=0, stop=2, kind='nhan',
                                                                       type='annotation')], pending=[100]), ensure_ascii=False, separators=(',', ':'))
    r = na.read_collect_result([real], proj, TASK, 'P1')
    assert r['pending'] == [dict(id=100, state='new', stage='annotation', type='annotation', start=0, stop=2, n=3, kind='nhan')]
