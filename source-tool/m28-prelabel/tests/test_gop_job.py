"""Thử nút "Merge jobs & Finish" (tool/gop_job.py + tab Các đợt của dot_ui): mô hình nút, thẻ đợt, và cả luồng qua handler THẬT của tab (do_act -> on_ok -> on_tick /
on_dismiss) với nap_anh.CollectJob thật chạy tiến trình con GIẢ: in đúng dòng máy đọc của m28.py collect (COLLECT_XML / COLLECT_JOBS_PENDING) và ghi file gộp giả
(dh_fake.viet_xml). Không mạng, không ảnh mặt, đồng hồ giả (FakeGio)."""
import csv
import glob
import json
import os
import subprocess
import sys
import threading
import time
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, '..', 'tool')
sys.path.insert(0, TOOL)
sys.path.insert(0, HERE)
import day_cvat  # noqa: E402
import dong_ho  # noqa: E402
import dong_ho_ui  # noqa: E402
import dot_anh  # noqa: E402
import dot_ui  # noqa: E402
import gop_job  # noqa: E402
import nap_anh as na  # noqa: E402
from dh_fake import FakeGio, du_an, mat_mau, viet_xml  # noqa: E402
from m28core import dang_chay, goi_kq  # noqa: E402

TOKEN = 'TOKEN-GIA-gop9x-KHONG-PHAI-THAT-0123'
URL = 'http://localhost:8080'
RUN, TASK = 'NAP_001', 'demo-NAP_001'
XML_NAME = 'demo-NAP_001_P5_1110.xml'
DONE_JOBS = [dict(id=11, n=2, stage='acceptance', state='completed', start=0, stop=1, kind='nhan', type='annotation'),
             dict(id=12, n=1, stage='acceptance', state='completed', start=2, stop=2, kind='gan_tay', type='annotation')]
OPEN_JOBS = [DONE_JOBS[0], dict(DONE_JOBS[1], stage='annotation', state='in progress')]
OUT = ['root', 'ses', 'msg', 'job', 'timer', 'modal', 'body', 'typed', 'check', 'ok', 'token', 'target', 'cancel']

# Tiến trình con giả của `m28.py collect` (chạy trong thư mục dự án như tiến trình thật): in dòng máy đọc, ghi file gộp vào raw/.
CHILD = r'''
import json, os, shutil, sys, time
mode, src, task, who, jobs = {mode!r}, {src!r}, {task!r}, {who!r}, json.loads({jobs!r})
time.sleep(0.4)
print('CVAT: http://localhost:8080 | token: có', flush=True)
print(task + ': id 7, 3 ảnh, ' + str(len(jobs)) + ' job', flush=True)
if mode == 'pending':
    print('COLLECT_JOBS_PENDING: ' + json.dumps(dict(task=task, jobs=jobs, pending=[j['id'] for j in jobs if j['state'] != 'completed'])), flush=True)
    print('--require-completed: CHƯA xuất gì.', flush=True)
    sys.exit(3)
if mode == 'error':
    print('Không kết nối được tới http://localhost:8080 khi kết nối, token ' + os.environ.get('CVAT_ACCESS_TOKEN', ''), flush=True)
    sys.exit(1)
if mode == 'notask':
    print(task + ': KHÔNG thấy task tên này trên CVAT, bỏ qua.', flush=True)
    sys.exit(0)
if mode == 'hang':                                    # bản xuất của CVAT kẹt trong hàng đợi (worker export dừng): tiến trình con không tự thoát
    time.sleep(120)
    sys.exit(0)
os.makedirs('raw', exist_ok=True)
dst = os.path.join('raw', task + '_' + who + '_1110.xml')
shutil.copyfile(src, dst)
print('  đã ghi ' + dst, flush=True)
print('COLLECT_XML: ' + json.dumps(dict(task=task, nguoi=who, xml=dst.replace(os.sep, '/'), jobs=jobs, moi=True)), flush=True)
'''


def fake_collect(mode, jobs, src, seen):
    """popen giả cho CollectJob. mode(cmd) -> 'ok' | 'pending' | 'error' | 'notask' | 'hang'; seen: danh sách nhận (cmd, env) của mỗi lần chạy."""
    def popen(cmd, **kw):
        seen.append(dict(cmd=list(cmd), env=dict(kw.get('env') or {})))
        m = mode(cmd)
        body = CHILD.format(mode=m, src=src, task=TASK, who=cmd[cmd.index('--reviewer') + 1], jobs=json.dumps(jobs))
        return subprocess.Popen([sys.executable, '-c', body], **kw)
    return popen


@pytest.fixture
def proj(tmp_path, monkeypatch):
    root = du_an(tmp_path / 'p')
    monkeypatch.chdir(root)
    monkeypatch.setenv('CVAT_URL', URL)
    monkeypatch.setenv('CVAT_ACCESS_TOKEN', TOKEN)
    monkeypatch.delenv('CVAT_ORG', raising=False)
    os.makedirs(os.path.join(root, 'runs', RUN, 'inbox'))
    os.makedirs(os.path.join(root, 'runs', '_nap'))
    push(root)
    src = viet_xml(str(tmp_path / 'src' / 'gop.xml'), {f'f{i}.png': mat_mau(i) for i in (1, 2, 3)})
    empty = viet_xml(str(tmp_path / 'src' / 'rong.xml'), {})
    return types.SimpleNamespace(root=root, src=src, empty=empty)


def push(root, **kw):
    ps = dict(trang_thai='xong', task=TASK, task_id=7, cvat_url=URL, task_url=URL + '/tasks/7', jobs=[dict(kind='nhan'), dict(kind='gan_tay')])
    ps.update(kw)
    json.dump(ps, open(os.path.join(root, 'runs', RUN, 'push.json'), 'w'))
    return ps


def env_ok():
    return {'CVAT_URL': URL, 'CVAT_ACCESS_TOKEN': TOKEN}


def make_app(p, mode=lambda cmd: 'ok', jobs=DONE_JOBS, src=None, reviewer='P5'):
    gr = pytest.importorskip('gradio')  # noqa: F841
    import review_app as ra
    ctx = ra.AppCtx(reviewer=reviewer, run_dir=os.path.join('runs', '_nap'), nap_only=True)
    g = FakeGio()
    ctx.dong_ho = dong_ho.DongHo(ctx.project_root, gio=g, pid=os.getpid())
    seen = []
    ctx.collect_job = na.CollectJob(popen=fake_collect(mode, jobs, src or p.src, seen))
    demo, _theme = ra.build_ui(None, ctx)
    return types.SimpleNamespace(ctx=ctx, g=g, demo=demo, seen=seen, d=ctx.dong_ho, ses=None)


def H(app, name):
    for f in app.demo.fns.values():
        fn = f.fn
        if fn is not None and getattr(fn, '__module__', '') == 'dot_ui' and fn.__qualname__ == f'dot_tab.<locals>.{name}':
            return f
    raise KeyError(name)


def call(app, name, *args):
    res = H(app, name).fn(*args)
    out = dict(zip(OUT, res))
    app.ses = out['ses']
    return out


def click(app, run=RUN):
    return call(app, 'do_act', json.dumps(dict(act='finish', run=run)), app.ses)


def ok(app, r):
    return call(app, 'on_ok', '', False, r['token'], app.ses)


def tick(app):
    return call(app, 'on_tick', app.ses)


def wait(app, timeout=20):
    t = time.time()
    while app.ctx.collect_job.running and time.time() - t < timeout:
        time.sleep(0.05)
    assert not app.ctx.collect_job.running


def shown(r):
    return isinstance(r['modal'], dict) and r['modal'].get('visible') is True


def timing_rows(root):
    p = os.path.join(root, 'outputs', 'timing', 'timing_P5.csv')
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def packages(root):
    return sorted(glob.glob(os.path.join(root, 'outputs', 'ket_qua', f'ketqua_P5_*_{RUN}.json')))


def gop_json(root):
    p = os.path.join(root, 'runs', RUN, 'gop_job.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None


def start_clock(app, secs):
    dong_ho_ui.auto_start(None, app.ctx, RUN, 4)
    app.g.tick(secs)


def to_waiting(app, secs=100):
    """Đưa yêu cầu gộp tới hộp thứ hai (còn job chưa Finish: chờ chọn Merge anyway / Cancel); trả output của nhịp đã mở hộp. Đồng hồ chạy lúc bấm."""
    start_clock(app, secs)
    ok(app, click(app))
    wait(app)
    r = tick(app)
    assert shown(r) and r['ok']['value'] == 'Merge anyway' and gop_job.waiting(app.ctx)
    return r


def clock(app):
    return app.d.xem('P5', RUN)['trang_thai']


def second_run(root, name='NAP_002'):
    os.makedirs(os.path.join(root, 'runs', name, 'inbox'))
    return name


def nap_fn(app, name):
    return next(f.fn for f in app.demo.fns.values() if getattr(f.fn, '__name__', '') == name and getattr(f.fn, '__module__', '') == 'review_app')


# ---------- finish_model: khi nào bật, lý do ----------
def test_finish_model_reasons(proj):
    rd = os.path.join(proj.root, 'runs', RUN)
    d = dong_ho.DongHo(proj.root, gio=FakeGio(), pid=os.getpid())

    def m(person='P5', env=None, **kw):
        return gop_job.finish_model(rd, proj.root, person, d, environ=env_ok() if env is None else env, **kw)
    assert m()['enabled'] and m()['task'] == TASK and m()['url'] == URL and not m()['co_phien'] and m()['goi_da_luu'] is None
    assert 'Thiếu CVAT_URL' in m(env={})['reason'] and 'tab Cài đặt' in m(env={})['reason']
    r = m(env={'CVAT_URL': 'http://localhost:9999', 'CVAT_ACCESS_TOKEN': TOKEN})
    assert not r['enabled'] and 'localhost:9999' in r['reason'] and URL in r['reason'] and 'đúng server' in r['reason']
    for who in ('a b', None, 'x' * 33, ''):
        assert not m(who)['enabled'] and 'chữ không dấu, số' in m(who)['reason'], who
    assert not m(job_running=True)['enabled'] and 'Đang có việc chạy' in m(job_running=True)['reason']
    assert dang_chay.acquire(rd, 'collect')
    assert 'Đang có việc chạy cho đợt này (collect)' in m()['reason']
    dang_chay.release(rd)
    for ps, want in ((dict(trang_thai='da_tao'), 'chưa xong'), (dict(trang_thai='task_deleted'), 'đã xoá'), (dict(task='m28-gold'), 'demo-'),
                     (dict(cvat_url=''), 'không ghi địa chỉ')):
        push(proj.root, **ps)
        assert not m()['enabled'] and want in m()['reason'], ps
    os.remove(os.path.join(rd, 'push.json'))
    assert not m()['enabled'] and 'chưa đẩy lên CVAT' in m()['reason'] and 'Push to CVAT' in m()['reason']
    push(proj.root)
    d.bat_dau('P5', 'assisted', dot=RUN, n_mat=3)
    d.gio.tick(65)
    v = m()
    assert v['enabled'] and v['co_phien'] and v['trang_thai'] == 'chay' and round(v['giay_phien']) == 65 and v['canh_bao_chua_xu_ly'] == []
    h = gop_job.confirm_html(v)
    for s in ('Gộp job và kết thúc đợt NAP_001', 'raw\\demo-NAP_001_P5_&lt;DDMM&gt;.xml', 'raw\\_cu\\', 'DỪNG', 'gói kết quả gửi nhóm trưởng', '01:05',
              'Nhớ bấm Save trong từng job CVAT (nhãn chưa Save không được xuất).', 'modal-finish', URL):
        assert s in h, s
    assert TOKEN not in h and TOKEN not in json.dumps({k: v[k] for k in v if k not in ('env',)}, default=str)


def test_merge_button_on_card_grid_and_busy_state(proj):
    rd = os.path.join(proj.root, 'runs', RUN)
    info = dot_anh.run_info(rd, 'P5')
    h = dot_anh.card_html(info)
    assert 'data-act="finish" data-run="NAP_001">Merge jobs & Finish</button>' in h                    # nhãn nút viết thẳng, tiếng Anh
    assert 'data-act="finish"' in dot_anh.push_section_html(info) and 'Merge jobs &amp; Finish' in dot_anh.push_section_html(info)
    for st in ('da_tao', 'da_nhap', 'task_deleted', 'dang_tao'):
        push(proj.root, trang_thai=st)
        assert 'data-act="finish"' not in dot_anh.card_html(dot_anh.run_info(rd, 'P5')), st
    os.remove(os.path.join(rd, 'push.json'))
    assert 'data-act="finish"' not in dot_anh.card_html(dot_anh.run_info(rd, 'P5'))
    push(proj.root)
    assert dang_chay.acquire(rd, 'collect')
    i = dot_anh.run_info(rd, 'P5')
    assert dot_anh.run_state(rd, i) == (dot_anh.S_COLLECTING, 'Đang gộp job (CVAT)')
    h = dot_anh.card_html(dict(i, ready=True))
    assert 'Đang gộp job (CVAT)' in h and 'st-info' in h and 'data-act="ra" data-run="NAP_001" disabled' in h
    assert 'data-act="finish" data-run="NAP_001" disabled' in h
    dang_chay.release(rd)
    gop_job.write_gop(rd, dict(task=TASK, nguoi='P5', xml='raw/' + XML_NAME, luc='2026-10-11T21:05:00+07:00', so_anh_co_nhan=3, jobs=[],
                               jobs_chua_xong=[12], goi='ketqua_P5_1110_NAP_001'))
    h = dot_anh.card_html(dot_anh.run_info(rd, 'P5'))
    assert f'Đã gộp job: raw/{XML_NAME} · 11/10/2026 21:05' in h and '1 job chưa Finish' in h and 'gói ketqua_P5_1110_NAP_001' in h
    assert 'Đã gộp job' in dot_anh.push_section_html(dot_anh.run_info(rd, 'P5'))
    assert day_cvat.FINISH_HINT.replace('&', '&amp;') in day_cvat.result_html(dict(trang_thai='xong', task=TASK), RUN)
    assert day_cvat.next_step(dict(trang_thai='xong'), RUN) == day_cvat.FINISH_HINT
    assert 'tab Các đợt' in day_cvat.FINISH_HINT and 'Merge jobs & Finish' in day_cvat.FINISH_HINT
    assert dot_ui.parse_action(json.dumps(dict(act='finish', run=RUN)))['act'] == 'finish'


def test_progress_label_and_banner():
    assert gop_job.progress([])[0] == 'Đang khởi động…'
    lab, fr = gop_job.progress(['CVAT: http://x | token: có', 'demo-A: id 7, 3 ảnh, 2 job'])
    assert 'xuất nhãn cả task' in lab and 0 < fr < 1
    snap = dict(state='dang_chay', returncode=None, run=RUN, lines=['CVAT: x'], elapsed=5.0, cancelling=False)
    h = day_cvat.progress_html(snap, 'Gộp job', label='Đang kết nối CVAT…', frac=0.2)
    assert 'Gộp job · lượt <b>NAP_001</b>' in h and 'Đang kết nối CVAT…' in h and 'aria-valuenow="20"' in h


# ---------- cả luồng qua handler thật ----------
def test_all_jobs_completed_pauses_at_click_and_saves_once(proj):
    """(a) mọi job đã completed: OK -> đồng hồ dừng ngay; job xong -> lưu MỘT lần (CSV + gói có nhãn của file gộp, số mặt = số ảnh có nhãn), ghi gop_job.json."""
    app = make_app(proj)
    start_clock(app, 300)
    r = click(app)
    assert shown(r) and r['ok']['value'] == 'Merge jobs & Finish' and r['token']
    assert '05:00' in r['body'] and 'đang chạy: tạm dừng ngay' in r['body'] and 'raw\\demo-NAP_001_P5_&lt;DDMM&gt;.xml' in r['body']
    assert app.d.xem('P5', RUN)['trang_thai'] == 'chay' and not app.seen                               # mới mở hộp: chưa dừng, chưa chạy gì
    r2 = ok(app, r)
    v = app.d.xem('P5', RUN)
    assert v['trang_thai'] == 'tam_dung' and round(v['giay_phien']) == 300                              # dừng NGAY khi bấm OK
    assert app.ctx.gop['phase'] == 'chay' and app.ctx.gop['was_running'] and 'đồng hồ của đợt đã tạm dừng' in r2['msg']
    assert 'Gộp job · lượt <b>NAP_001</b>' in r2['job'] and r2['timer'].active is True
    cmd = app.seen[0]['cmd']
    assert cmd[3:] == ['collect', '--task', TASK, '--reviewer', 'P5', '--overwrite', '--no-per-job', '--require-completed']
    assert not any(TOKEN in c for c in cmd) and app.seen[0]['env']['CVAT_ACCESS_TOKEN'] == TOKEN and app.seen[0]['env']['CVAT_URL'] == URL
    app.g.tick(500)                                                                                       # giây xuất / chờ: không tính
    wait(app)
    r3 = tick(app)
    rows = timing_rows(proj.root)
    assert len(rows) == 3 and {x['giay_phien'] for x in rows} == {'300.0'} and {x['so_mat_phien'] for x in rows} == {'3'} and {x['dot'] for x in rows} == {RUN}
    pk = packages(proj.root)
    assert len(pk) == 1
    nd, _w = goi_kq.doc_goi(pk[0])
    assert nd['co_nhan'] and len(nd['ket_qua']) == 3 and nd['so_mat'] == 3 and nd['nhan_file'] == XML_NAME and nd['giay_phien'] == 300.0
    gj = gop_json(proj.root)
    assert gj == dict(task=TASK, nguoi='P5', xml='raw/' + XML_NAME, luc=gj['luc'], so_anh_co_nhan=3, jobs=gj['jobs'], jobs_chua_xong=[],
                      goi=os.path.basename(pk[0])[:-5])
    assert [j['id'] for j in gj['jobs']] == [11, 12] and gj['luc'].startswith('2026-10-14T18:43:20')
    assert f'File gộp: <code>raw\\{XML_NAME}</code> (3 ảnh có nhãn, 2 job)' in r3['msg'] and 'Gói kết quả gửi nhóm trưởng' in r3['msg']
    assert proj.root not in r3['msg'] and TOKEN not in r3['msg'] and not shown(r3) and r3['timer'].active is False
    assert app.ctx.gop is None and not app.d.xem('P5', RUN)['co_phien']
    assert f'Đã gộp job: raw/{XML_NAME}' in r3['root']
    r4 = tick(app)                                                                                        # nhịp sau: không lưu lần hai
    assert len(timing_rows(proj.root)) == 3 and len(packages(proj.root)) == 1 and 'File gộp' not in str(r4['msg'])
    log = open(os.path.join(proj.root, 'runs', RUN, 'collect_log.txt'), encoding='utf-8').read()
    assert 'COLLECT_XML' in log and TOKEN not in log and dang_chay.busy(os.path.join(proj.root, 'runs', RUN)) is None


def test_pending_jobs_ask_again_cancel_resumes_then_merge_anyway(proj):
    """(b) còn job chưa Finish: hỏi lần hai; Cancel = quay lại CVAT (đồng hồ chạy lại, không lưu gì); Merge anyway -> chạy không --require-completed -> lưu, ghi job chưa xong."""
    app = make_app(proj, mode=lambda cmd: 'pending' if '--require-completed' in cmd else 'ok', jobs=OPEN_JOBS)
    start_clock(app, 120)
    ok(app, click(app))
    wait(app)
    r = tick(app)
    assert shown(r) and r['ok']['value'] == 'Merge anyway' and app.ctx.gop['phase'] == 'hoi'
    for s in ('Còn 1 job chưa bấm Finish the job trong CVAT. Gộp luôn (nhãn hiện có trên server) hay quay lại CVAT sửa tiếp?', 'job 12', 'frame 2–2',
              'annotation/in progress'):
        assert s in r['body'], s
    assert 'job 11' not in r['body'] and app.d.xem('P5', RUN)['trang_thai'] == 'tam_dung' and not timing_rows(proj.root)
    r = call(app, 'on_dismiss', r['token'], app.ses)                                                      # Cancel: quay lại CVAT
    assert not shown(r) and app.ctx.gop is None and 'quay lại CVAT' in r['msg'] and 'chạy tiếp' in r['msg']
    assert app.d.xem('P5', RUN)['trang_thai'] == 'chay' and not timing_rows(proj.root) and gop_json(proj.root) is None
    app.g.tick(60)
    ok(app, click(app))
    wait(app)
    r = tick(app)
    assert shown(r) and r['ok']['value'] == 'Merge anyway'
    r = ok(app, r)                                                                                        # Merge anyway
    assert '--require-completed' not in app.seen[-1]['cmd'] and app.seen[-1]['cmd'][3:8] == ['collect', '--task', TASK, '--reviewer', 'P5']
    assert len(app.seen) == 3 and app.d.xem('P5', RUN)['trang_thai'] == 'tam_dung'
    wait(app)
    r = tick(app)
    rows = timing_rows(proj.root)
    assert rows and {x['giay_phien'] for x in rows} == {'180.0'}                                          # 120 + 60 giây sau khi quay lại CVAT
    gj = gop_json(proj.root)
    assert gj['jobs_chua_xong'] == [12] and gj['so_anh_co_nhan'] == 3 and gj['goi']
    assert 'Gộp khi còn 1 job chưa Finish the job trên CVAT (job 12)' in r['msg'] and app.ctx.gop is None
    assert 'gộp khi còn 1 job chưa Finish' in r['root']


def test_error_resumes_the_clock_and_shows_the_scrubbed_cause(proj):
    """(c) lỗi (không kết nối được CVAT): đồng hồ chạy lại như lúc bấm, báo dòng lỗi cuối đã lọc token, không ghi gì."""
    app = make_app(proj, mode=lambda cmd: 'error')
    start_clock(app, 90)
    ok(app, click(app))
    assert app.d.xem('P5', RUN)['trang_thai'] == 'tam_dung'
    wait(app)
    r = tick(app)
    assert 'Gộp job của đợt NAP_001 không xong' in r['msg'] and 'Không kết nối được tới http://localhost:8080' in r['msg']
    assert TOKEN not in r['msg'] and 'collect_log.txt' in r['msg'] and 'chạy tiếp' in r['msg'] and not shown(r)
    assert app.d.xem('P5', RUN)['trang_thai'] == 'chay' and app.ctx.gop is None
    assert not timing_rows(proj.root) and gop_json(proj.root) is None and not packages(proj.root)


def test_task_missing_on_cvat_is_an_error_and_paused_clock_stays_paused(proj):
    app = make_app(proj, mode=lambda cmd: 'notask')
    start_clock(app, 90)
    app.d.tam_dung('P5', None, dot=RUN)                                                                   # lúc bấm đồng hồ đang tạm dừng: lỗi thì giữ tạm dừng
    r = click(app)
    assert 'đang tạm dừng' in r['body']
    ok(app, r)
    assert app.ctx.gop['was_running'] is False
    wait(app)
    r = tick(app)
    assert 'KHÔNG thấy task tên này trên CVAT' in r['msg'] and app.d.xem('P5', RUN)['trang_thai'] == 'tam_dung' and app.ctx.gop is None


def test_no_session_but_saved_package_gets_the_merged_labels(proj):
    """(d) không còn phiên (đã Save timing trước, gói chỉ có thời gian): chỉ xuất file gộp và gắn nhãn vào gói đã lưu của đợt (xuat_lai_goi)."""
    app = make_app(proj)
    start_clock(app, 100)
    saved = app.d.xong_luu('P5', None, True, 3, 'auto', dot=RUN)
    nd0, _w = goi_kq.doc_goi(os.path.join(proj.root, saved['goi']['json']))
    assert not nd0['co_nhan'] and len(timing_rows(proj.root)) == 3
    r = click(app)
    assert shown(r) and 'Không có phiên đồng hồ đang mở của P5 cho đợt NAP_001' in r['body'] and saved['goi']['ten'] in r['body']
    ok(app, r)
    wait(app)
    r = tick(app)
    nd, _w = goi_kq.doc_goi(os.path.join(proj.root, saved['goi']['json']))
    assert nd['co_nhan'] and len(nd['ket_qua']) == 3 and nd['nhan_file'] == XML_NAME and nd['phien'] == nd0['phien'] and nd['giay_phien'] == 100.0
    assert len(timing_rows(proj.root)) == 3 and len(packages(proj.root)) == 1                              # không thêm dòng bấm giờ
    assert gop_json(proj.root)['goi'] == saved['goi']['ten'] and 'đã gắn nhãn từ file gộp' in r['msg'] and saved['goi']['ten'] in r['msg']


def test_no_session_and_no_package_only_exports(proj):
    app = make_app(proj)
    r = click(app)
    assert shown(r) and 'chỉ xuất file gộp.' in r['body']
    ok(app, r)
    wait(app)
    r = tick(app)
    assert 'chỉ xuất file gộp' in r['msg'] and gop_json(proj.root)['goi'] == '' and not timing_rows(proj.root)
    assert os.path.exists(os.path.join(proj.root, 'raw', XML_NAME))


def test_finalized_exactly_once_with_two_tabs_ticking(proj):
    """(e) hai tab cùng tick (hai luồng cùng lúc, rồi thêm lần nữa): kết quả chỉ được xử lý một lần."""
    app = make_app(proj)
    start_clock(app, 200)
    calls = []
    orig = app.d.xong_luu

    def counted(*a, **k):
        calls.append(1)
        time.sleep(0.2)                                                                                   # giữ lâu để luồng kia chen vào
        return orig(*a, **k)
    app.d.xong_luu = counted
    ok(app, click(app))
    wait(app)
    fn = H(app, 'on_tick').fn
    barrier = threading.Barrier(3)
    got = []

    def tab():
        barrier.wait()
        got.append(dict(zip(OUT, fn(None))))
    threads = [threading.Thread(target=tab) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert sum('File gộp' in str(x['msg']) for x in got) == 1 and len(calls) == 1
    tick(app)
    assert gop_job.poll(app.ctx, app.d) is None and len(calls) == 1
    assert len(timing_rows(proj.root)) == 3 and len(packages(proj.root)) == 1


def test_clock_warning_is_accepted_by_the_single_confirmation(proj):
    """(f) phiên quá 150 phút: hộp xác nhận liệt kê cảnh báo; bấm OK một lần là lưu kèm cảnh báo (không phải bấm Save timing lần hai)."""
    app = make_app(proj)
    start_clock(app, 151 * 60)
    r = click(app)
    assert 'Cảnh báo của đồng hồ' in r['body'] and 'hơn 150 phút' in r['body'] and 'đồng ý lưu kèm cảnh báo' in r['body']
    calls = []
    orig = app.d.xong_luu
    app.d.xong_luu = lambda *a, **k: (calls.append(1), orig(*a, **k))[1]
    ok(app, r)
    wait(app)
    r = tick(app)
    rows = timing_rows(proj.root)
    assert rows and 'phien_lau' in rows[0]['canh_bao'] and len(calls) == 2 and 'File gộp' in r['msg'] and not app.d.xem('P5', RUN)['co_phien']


def test_invalid_reviewer_name_is_refused(proj):
    """(g) tên người rà của trang không hợp lệ (có dấu cách): từ chối, không mở hộp, không chạy gì."""
    app = make_app(proj, reviewer='a b')
    r = click(app)
    assert not shown(r) and 'chữ không dấu, số' in r['msg'] and not app.seen and app.ctx.gop is None


def test_cvat_link_mismatch_is_refused(proj):
    """(h) CVAT_URL khác server đã đẩy (push.json cvat_url): từ chối."""
    push(proj.root, cvat_url='http://localhost:9999')
    app = make_app(proj)
    r = click(app)
    assert not shown(r) and 'localhost:9999' in r['msg'] and 'đúng server' in r['msg'] and not app.seen


def test_zero_labels_saves_nothing_and_the_clock_runs_again(proj):
    """File gộp không có nhãn nào (thường do chưa Save trong CVAT): không dừng đồng hồ, không ghi dòng bấm giờ hay gói rỗng, không ghi gop_job.json."""
    app = make_app(proj, src=proj.empty)
    start_clock(app, 60)
    ok(app, click(app))
    wait(app)
    r = tick(app)
    assert 'không có nhãn nào' in r['msg'] and 'Save' in r['msg'] and 'chạy tiếp' in r['msg']
    assert not timing_rows(proj.root) and not packages(proj.root) and not os.path.exists(os.path.join(proj.root, 'runs', RUN, gop_job.GOP_FILE))
    v = app.d.xem('P5', RUN)
    assert v['co_phien'] and v['trang_thai'] == 'chay' and app.ctx.gop is None


def test_stale_token_and_refresh_while_waiting(proj):
    """OK của hộp cũ không chạy gì; tải lại tab khi đang chờ chọn Merge anyway / Cancel thì nhắc, bấm nút lại thì mở lại đúng hộp đó."""
    app = make_app(proj, mode=lambda cmd: 'pending' if '--require-completed' in cmd else 'ok', jobs=OPEN_JOBS)
    start_clock(app, 30)
    r = click(app)
    click(app)                                                                                            # mở hộp mới: mã của hộp cũ hết hiệu lực
    r2 = ok(app, r)
    assert 'đã cũ' in r2['msg'] and not app.seen and app.d.xem('P5', RUN)['trang_thai'] == 'chay'
    ok(app, click(app))
    wait(app)
    tick(app)
    assert gop_job.waiting(app.ctx)
    r = call(app, 'on_load_or_refresh', None)
    assert 'đang chờ bạn chọn' in r['msg'] and not shown(r)
    r = click(app)
    assert shown(r) and r['ok']['value'] == 'Merge anyway' and 'job 12' in r['body']


def test_busy_checks_include_the_collect_job(proj):
    import review_app as ra
    app = make_app(proj)
    ctx = app.ctx
    assert ra.close_check(None, ctx)[0]
    ctx.collect_job.state, ctx.collect_job.run = 'dang_chay', RUN
    ok_, msg, lv = ra.close_check(None, ctx)
    assert not ok_ and lv == 'warn' and 'gộp job CVAT của lượt NAP_001' in msg
    r = call(app, 'do_act', json.dumps(dict(act='ra', run=RUN)), None)
    assert 'gộp job' in r['msg']
    r = click(app)
    assert not shown(r) and 'Đang có việc chạy' in r['msg']
    ctx.collect_job.state = 'chua'


def test_module_has_no_gradio_numpy_or_network():
    code = ("import sys\nsys.path.insert(0, %r)\nimport gop_job, dot_ui\nfor m in ('gradio', 'numpy', 'torch', 'cv2', 'cvat_sdk'):\n    assert m not in sys.modules, m\n"
            "print('ok')\n") % TOOL
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0 and 'ok' in r.stdout, r.stderr
    src = open(os.path.join(TOOL, 'gop_job.py'), encoding='utf-8').read()
    imports = [ln.split('#')[0] for ln in src.splitlines() if ln.startswith(('import ', 'from '))]
    assert not [ln for ln in imports if any(m in ln for m in ('gradio', 'urllib', 'requests', 'socket', 'cvat_sdk', 'subprocess', 'numpy'))], imports
    for bad in ('shell=True', 'os.environ', 'share=True'):
        assert bad not in src, bad
    ui = open(os.path.join(TOOL, 'dot_ui.py'), encoding='utf-8').read()
    assert 'ok_label="Merge jobs & Finish"' in ui and 'ok_label="Merge anyway"' in ui


# ---------- nút Cancel của job gộp (bản xuất của CVAT kẹt) ----------
def test_cancel_button_stops_a_hung_merge_and_resumes_the_clock(proj):
    """Tiến trình con collect không tự thoát (worker export của CVAT dừng): nút Cancel ở khung gộp job của tab Các đợt huỷ nó; kết quả 'huỷ' xử lý ngay, đồng hồ
    chạy lại như lúc bấm, không ghi gì, trang hết bị khoá (Close page)."""
    import review_app as ra
    app = make_app(proj, mode=lambda cmd: 'hang')
    btn = next(b for b in app.demo.blocks.values() if getattr(b, 'elem_id', None) == 'dot-gop-cancel')
    assert type(btn).__name__ == 'Button' and btn.value == 'Cancel' and btn.visible is False                 # nhãn nút tiếng Anh; chỉ hiện khi job gộp chạy
    r = call(app, 'on_load_or_refresh', None)
    assert r['cancel']['visible'] is False
    start_clock(app, 200)
    r = ok(app, click(app))
    assert app.ctx.collect_job.running and r['cancel']['visible'] is True and r['cancel']['interactive'] is True and clock(app) == 'tam_dung'
    r = tick(app)
    assert r['cancel']['visible'] is True and r['timer'].active is True and 'Gộp job · lượt <b>NAP_001</b>' in r['job']
    ok_, msg, _lv = ra.close_check(None, app.ctx)
    assert not ok_ and 'bấm Cancel ở khung gộp job' in msg                                                     # câu nhắc nút có thật
    t = time.time()
    r = call(app, 'on_gop_cancel', app.ses)
    assert time.time() - t < 15 and not app.ctx.collect_job.running and app.ctx.collect_job.state == 'da_huy'
    assert 'Đã huỷ gộp job của đợt NAP_001' in r['msg'] and 'chạy tiếp' in r['msg'] and r['cancel']['visible'] is False and r['timer'].active is False
    assert app.ctx.gop is None and clock(app) == 'chay' and round(app.d.xem('P5', RUN)['giay_phien']) == 200
    assert not timing_rows(proj.root) and gop_json(proj.root) is None and not packages(proj.root) and ra.close_check(None, app.ctx)[0]
    r = call(app, 'on_gop_cancel', app.ses)                                                                     # bấm lần nữa: không còn gì để huỷ
    assert 'Không có job gộp nào đang chạy' in r['msg'] and clock(app) == 'chay'
    r = click(app)                                                                                              # không kẹt: Merge jobs & Finish mở lại được
    assert shown(r) and r['ok']['value'] == 'Merge jobs & Finish'


# ---------- yêu cầu gộp dở (ctx.gop) chặn chuyển đợt ----------
def test_switching_batch_is_refused_while_a_merge_request_is_unfinished(proj):
    """Chuyển đợt dựng ctx mới nên mất ctx.gop: Review batch, Upload & Open (tự chuyển khi prepare xong) đều bị từ chối khi yêu cầu gộp còn dở; job đã dừng mà
    chưa xử lý thì xử lý trước (hiện hộp thứ hai). Chọn xong (Cancel) thì chuyển được."""
    app = make_app(proj, mode=lambda cmd: 'pending' if '--require-completed' in cmd else 'ok', jobs=OPEN_JOBS)
    other = second_run(proj.root)
    start_clock(app, 100)
    ok(app, click(app))
    wait(app)                                                                                                   # job đã dừng (mã 3), chưa nhịp nào xử lý
    ra_act = json.dumps(dict(act='ra', run=other))
    r = call(app, 'do_act', ra_act, app.ses)
    assert shown(r) and r['ok']['value'] == 'Merge anyway' and app.ctx.switch_to is None and r['target'] == '' and gop_job.waiting(app.ctx)
    r = call(app, 'do_act', ra_act, app.ses)
    assert shown(r) and 'trước rồi mới chuyển đợt' in r['body'] and app.ctx.switch_to is None and r['target'] == ''
    assert clock(app) == 'tam_dung' and gop_job.waiting(app.ctx)
    on_auto_open = nap_fn(app, 'on_auto_open')                                                                  # tab Nạp ảnh: Upload & Open, prepare vừa xong
    app.ctx.job.snapshot = lambda: dict(state='xong', run=other, run_dir=os.path.join('runs', other), lines=[])
    app.ctx.auto_open = other
    msg, target = on_auto_open(None)
    assert target == '' and app.ctx.switch_to is None and 'Merge anyway hoặc Cancel' in msg and f'Mở lượt {other} ở tab Các đợt' in msg
    del app.ctx.job.snapshot
    res = nap_fn(app, 'on_start_open')(None, '', '', None)                                                      # bấm Upload & Open lúc yêu cầu còn chờ
    assert 'Merge anyway hoặc Cancel' in res[7] and 'Upload &amp; Continue' in res[7] and app.ctx.job.state == 'chua'
    assert gop_job.waiting(app.ctx) and clock(app) == 'tam_dung'
    r = call(app, 'on_dismiss', r['token'], app.ses)                                                            # Cancel = quay lại CVAT
    assert app.ctx.gop is None and clock(app) == 'chay'
    r = call(app, 'do_act', ra_act, app.ses)
    assert 'flags.json' in r['msg'] and 'Merge anyway' not in r['msg']                                         # qua được kiểm yêu cầu gộp (dừng ở kiểm kế tiếp)


def test_upload_and_open_shows_an_unprocessed_merge_result_before_switching(proj):
    app = make_app(proj)
    other = second_run(proj.root)
    start_clock(app, 150)
    ok(app, click(app))
    wait(app)                                                                                                   # gộp xong, chưa tab nào xử lý
    on_auto_open = nap_fn(app, 'on_auto_open')
    app.ctx.job.snapshot = lambda: dict(state='xong', run=other, run_dir=os.path.join(proj.root, 'runs', other), lines=[])
    app.ctx.auto_open = other
    msg, target = on_auto_open(None)
    assert target == '' and f'Đã gộp job của đợt NAP_001: raw\\{XML_NAME}' in msg and 'Gói kết quả: ketqua_P5_' in msg and f'Mở lượt {other}' in msg
    assert app.ctx.gop is None and len(timing_rows(proj.root)) == 3 and len(packages(proj.root)) == 1           # xử lý đúng một lần
    app.ctx.auto_open = other
    msg, target = on_auto_open(None)
    assert 'Đã gộp job' not in msg and 'Merge' not in msg and len(timing_rows(proj.root)) == 3                 # lần sau: qua kiểm yêu cầu gộp


# ---------- Merge anyway bị từ chối vì lý do tạm thời ----------
def test_merge_anyway_refused_for_a_temporary_reason_keeps_the_request_waiting(proj):
    app = make_app(proj, mode=lambda cmd: 'pending' if '--require-completed' in cmd else 'ok', jobs=OPEN_JOBS)
    r = to_waiting(app, 120)
    app.ctx.smoke_job.state = 'dang_chay'                                                                      # việc khác đang chạy (kiểm tra nhanh CVAT)
    r = ok(app, r)                                                                                              # Merge anyway
    assert shown(r) and r['ok']['value'] == 'Merge anyway' and 'Đang có việc chạy' in r['body'] and 'vẫn chờ' in r['body'] and 'Merge anyway lại' in r['body']
    assert gop_job.waiting(app.ctx) and clock(app) == 'tam_dung' and len(app.seen) == 1 and 'chạy tiếp' not in r['msg']
    app.ctx.smoke_job.state = 'chua'
    r = ok(app, r)                                                                                              # việc kia xong: bấm Merge anyway lại
    assert len(app.seen) == 2 and '--require-completed' not in app.seen[-1]['cmd']
    wait(app)
    r = tick(app)
    assert 'Gộp khi còn 1 job chưa Finish' in r['msg'] and app.ctx.gop is None and {x['giay_phien'] for x in timing_rows(proj.root)} == {'120.0'}


def test_waiting_dialog_comes_back_when_the_other_job_ends(proj):
    """Merge anyway bị từ chối tạm thời (việc khác đang chạy): khi việc kia xong, nhịp đầu tiên KHÔNG được đóng hộp thứ hai mà mở lại nó, kèm câu nói việc kia đã xong."""
    app = make_app(proj, mode=lambda cmd: 'pending' if '--require-completed' in cmd else 'ok', jobs=OPEN_JOBS)
    r = to_waiting(app, 60)
    app.ctx.smoke_job.state = 'dang_chay'
    r = ok(app, r)
    assert shown(r) and 'Merge anyway lại' in r['body']
    tick(app)                                                                                                   # việc kia còn chạy: hộp giữ nguyên
    app.ctx.smoke_job.state = 'chua'
    r = tick(app)                                                                                               # việc kia vừa xong
    assert shown(r) and r['ok']['value'] == 'Merge anyway' and 'Việc kia đã xong' in r['body'] and gop_job.waiting(app.ctx) and clock(app) == 'tam_dung'
    r = call(app, 'on_dismiss', r['token'], app.ses)                                                            # Cancel của hộp mở lại vẫn quay lại CVAT được
    assert app.ctx.gop is None and clock(app) == 'chay'


def test_merge_anyway_when_the_child_cannot_start_keeps_waiting_then_cancel_still_works(proj):
    app = make_app(proj, mode=lambda cmd: 'pending' if '--require-completed' in cmd else 'ok', jobs=OPEN_JOBS)
    r = to_waiting(app)

    def busy(*a, **k):
        raise na.RunError('Lượt NAP_001 đang có việc khác chạy (push): chờ xong rồi thử lại.')
    app.ctx.collect_job.start = busy                                                                            # khoá .dang_chay bận đúng lúc bấm
    r = ok(app, r)
    g = gop_job.waiting(app.ctx)
    assert shown(r) and 'đang có việc khác chạy' in r['body'] and 'vẫn chờ' in r['body'] and g and g['force'] is False and clock(app) == 'tam_dung'
    del app.ctx.collect_job.start
    r = call(app, 'on_dismiss', r['token'], app.ses)
    assert app.ctx.gop is None and 'quay lại CVAT' in r['msg'] and clock(app) == 'chay'


def test_merge_anyway_after_the_task_was_deleted_abandons_the_request(proj):
    app = make_app(proj, mode=lambda cmd: 'pending' if '--require-completed' in cmd else 'ok', jobs=OPEN_JOBS)
    r = to_waiting(app)
    push(proj.root, trang_thai='task_deleted')                                                                 # thay đổi lâu dài: bỏ yêu cầu, đồng hồ chạy lại
    r = ok(app, r)
    assert not shown(r) and app.ctx.gop is None and 'đã xoá' in r['msg'] and clock(app) == 'chay' and len(app.seen) == 1


# ---------- Cancel của hộp thứ hai khi tab khác đã thay yêu cầu xác nhận dùng chung ----------
def test_cancel_on_the_second_modal_works_after_another_tab_replaced_the_shared_pending(proj):
    app = make_app(proj, mode=lambda cmd: 'pending' if '--require-completed' in cmd else 'ok', jobs=OPEN_JOBS)
    r = to_waiting(app, 90)
    other = app.ctx.dot_pending.open(kind='delimg', run=RUN, name='f1.png')                                     # tab khác mở một hộp khác của tab Các đợt
    r2 = call(app, 'on_dismiss', r['token'], app.ses)
    assert not shown(r2) and app.ctx.gop is None and 'quay lại CVAT' in r2['msg'] and 'chạy tiếp' in r2['msg'] and clock(app) == 'chay'
    assert app.ctx.dot_pending.item is other                                                                    # không bỏ hộp đang mở ở tab kia
    app.g.tick(30)
    ok(app, click(app))
    wait(app)
    r = tick(app)
    assert gop_job.waiting(app.ctx)
    app.ctx.dot_pending.cancel()                                                                                # tab kia mở rồi Cancel hộp của nó
    r2 = call(app, 'on_dismiss', r['token'], app.ses)
    assert app.ctx.gop is None and 'quay lại CVAT' in r2['msg'] and clock(app) == 'chay'
    r3 = call(app, 'on_dismiss', r['token'], app.ses)                                                           # bấm lại hộp cũ: không làm gì
    assert app.ctx.gop is None and 'quay lại CVAT' not in str(r3['msg'])


# ---------- nhịp của tab chạy đến khi kết quả gộp được xử lý ----------
def test_tab_timer_stays_on_until_the_merge_result_is_processed(proj, monkeypatch):
    app = make_app(proj, mode=lambda cmd: 'error')
    start_clock(app, 60)
    ok(app, click(app))
    wait(app)                                                                                                   # tiến trình con đã thoát, chưa nhịp nào xử lý
    for act in (dict(act='back', run=''), dict(act='open', run=RUN), dict(act='back', run='')):                 # hành động không gọi poll
        r = call(app, 'do_act', json.dumps(act), app.ses)
        assert r['timer'].active is True and app.ctx.gop['phase'] == 'chay' and clock(app) == 'tam_dung', act
    calls = []
    real = gop_job.poll

    def late(ctx, d):                                                                                           # tiến trình con thoát ngay SAU lần poll của nhịp
        calls.append(1)
        return None if len(calls) == 1 else real(ctx, d)
    monkeypatch.setattr(gop_job, 'poll', late)
    r = tick(app)
    assert r['timer'].active is True and app.ctx.gop['phase'] == 'chay'
    r = tick(app)
    assert 'Gộp job của đợt NAP_001 không xong' in r['msg'] and r['timer'].active is False and app.ctx.gop is None and clock(app) == 'chay'


# ---------- không xoá đợt / task / ảnh khi yêu cầu gộp của đợt đó còn dở ----------
def test_deleting_the_batch_task_or_images_is_refused_while_a_merge_request_is_pending(proj):
    app = make_app(proj, mode=lambda cmd: 'pending' if '--require-completed' in cmd else 'ok', jobs=OPEN_JOBS)
    rd = os.path.join(proj.root, 'runs', RUN)
    r = call(app, 'do_act', json.dumps(dict(act='delrun', run=RUN)), app.ses)                                  # chưa gộp: hộp xoá đợt mở được
    assert shown(r) and r['ok']['value'] == 'Delete batch'
    call(app, 'on_dismiss', r['token'], app.ses)
    to_waiting(app)
    for act, what in (('deltask', 'xoá task trên CVAT'), ('delrun', 'xoá đợt'), ('delimg', 'xoá ảnh của đợt')):
        r = call(app, 'do_act', json.dumps(dict(act=act, run=RUN, name='f1.png')), app.ses)
        assert not shown(r) and 'Merge anyway hoặc Cancel' in r['msg'] and what in r['msg'], act
    g = app.ctx.gop                                                                                             # hộp xoá mở TRƯỚC, rồi tab khác bấm Merge jobs & Finish
    app.ctx.gop = None
    r = call(app, 'do_act', json.dumps(dict(act='delrun', run=RUN)), app.ses)
    assert shown(r)
    app.ctx.gop = g
    r = call(app, 'on_ok', RUN, False, r['token'], app.ses)
    assert 'xoá đợt' in r['msg'] and 'Merge anyway hoặc Cancel' in r['msg']
    assert os.path.isdir(rd) and dot_anh.read_push(rd)['trang_thai'] == 'xong' and gop_job.waiting(app.ctx)


# ---------- khung Các đợt: xoá task lỗi / huỷ không nhắc Merge jobs & Finish ----------
def test_failed_or_cancelled_delete_task_banner_does_not_suggest_merge(proj):
    app = make_app(proj)
    dj = app.ctx.del_job
    dj.state, dj.run, dj.run_dir, dj.returncode = 'loi', RUN, os.path.join(proj.root, 'runs', RUN), 1
    dj.lines.append('Không kết nối được tới http://localhost:8080 khi kết nối.')
    r = call(app, 'on_load_or_refresh', None)
    assert 'Xoá task trên CVAT không xong' in r['job'] and 'Không kết nối được' in r['job'] and 'Delete CVAT task lại' in r['job']
    assert 'Merge jobs' not in r['job'] and 'Đẩy lên CVAT không xong' not in r['job']
    dj.state = 'da_huy'
    r = call(app, 'on_load_or_refresh', None)
    assert 'Đã huỷ' in r['job'] and 'vẫn còn trên CVAT' in r['job'] and 'Merge jobs' not in r['job']
    dj.state = 'chua'


# ---------- lỗi lúc cho đồng hồ chạy lại / lưu giữa chừng: ctx.gop không bao giờ kẹt ----------
def test_clock_file_locked_while_resuming_never_leaves_the_request_stuck(proj):
    app = make_app(proj, mode=lambda cmd: 'error')
    start_clock(app, 90)
    ok(app, click(app))
    wait(app)

    def locked(*a, **k):
        raise PermissionError(13, 'file trạng thái đang bị khoá')
    app.d.tiep_tuc = locked                                                                                     # antivirus / OneDrive giữ file trạng thái đồng hồ
    r = tick(app)
    assert 'Gộp job của đợt NAP_001 không xong' in r['msg'] and 'chưa chạy lại được (PermissionError)' in r['msg'] and 'Resume' in r['msg']
    assert app.ctx.gop is None and clock(app) == 'tam_dung' and r['timer'].active is False
    del app.d.tiep_tuc
    r = click(app)                                                                                              # không kẹt: bấm lại được ngay
    assert shown(r) and r['ok']['value'] == 'Merge jobs & Finish'


def test_poll_releases_the_request_even_if_reporting_the_error_fails(proj, monkeypatch):
    app = make_app(proj, mode=lambda cmd: 'error')
    start_clock(app, 30)
    ok(app, click(app))
    wait(app)

    def boom(exc):
        def f(*a, **k):
            raise exc
        return f
    monkeypatch.setattr(gop_job, 'finalize', boom(ValueError('x')))
    monkeypatch.setattr(gop_job, '_fail', boom(RuntimeError('y')))
    with pytest.raises(RuntimeError):
        gop_job.poll(app.ctx, app.d)
    assert app.ctx.gop is None


def test_save_failing_half_way_is_reported_and_the_clock_is_not_restarted(proj):
    app = make_app(proj)
    start_clock(app, 120)
    ok(app, click(app))
    wait(app)

    def half(*a, **k):
        raise PermissionError(13, 'locked')
    app.d.xong_luu = half                                                                                       # dòng bấm giờ/gói có thể đã ghi rồi mới lỗi
    r = tick(app)
    assert 'Lưu đồng hồ chưa trọn (PermissionError)' in r['msg'] and 'không tự chạy lại' in r['msg']
    assert app.ctx.gop is None and clock(app) == 'tam_dung' and gop_json(proj.root)['goi'] == ''


def test_unexpected_error_after_saving_does_not_restart_the_clock(proj, monkeypatch):
    app = make_app(proj)
    start_clock(app, 120)
    ok(app, click(app))
    wait(app)
    monkeypatch.setattr(gop_job, '_save', lambda *a, **k: dict(goi=dict(ten='ketqua_gia')))
    monkeypatch.setattr(gop_job, 'write_gop', lambda *a, **k: (_ for _ in ()).throw(TypeError('x')))
    r = tick(app)
    assert 'Lỗi không lường trước khi gộp job của đợt NAP_001 (TypeError)' in r['msg'] and app.ctx.gop is None and clock(app) == 'tam_dung'


# ---------- tab Nạp ảnh: phải có link/token CVAT trước khi nạp ----------
def test_upload_without_cvat_opens_the_settings_dialog_and_stages_nothing(proj, monkeypatch):
    """Chưa có CVAT_URL / token: bấm Upload & Continue hay Upload & Open thì KHÔNG nạp gì, mở hộp (OK sang tab Cài đặt / Cancel), nói rõ thiếu gì."""
    monkeypatch.delenv('CVAT_URL', raising=False)
    monkeypatch.delenv('CVAT_ACCESS_TOKEN', raising=False)
    app = make_app(proj)
    import review_app as ra
    for name in ('on_start', 'on_start_open'):
        res = nap_fn(app, name)(None, '', '', None)
        modal, body = res[-2], res[-1]
        assert modal == {'__type__': 'update', 'visible': True}
        assert 'Chưa kết nối CVAT' in body and 'link CVAT' in body and 'token CVAT' in body and 'OK' in body and 'Cancel' in body
    assert sorted(os.listdir(os.path.join(proj.root, 'runs'))) == sorted(['_nap', RUN])                   # không tạo lượt NAP_xxx nào
    blocks = {getattr(b, 'elem_id', None): b for b in app.demo.blocks.values()}
    assert blocks['nap-cvat-ok'].value == 'OK' and blocks['nap-cvat-cancel'].value == 'Cancel' and blocks['nap-cvat'].visible is False
    assert '#cd-url' in ra.CVAT_SANG_CAI_DAT_JS and '#cd-reviewer' in ra.CVAT_SANG_CAI_DAT_JS
    src = open(os.path.join(os.path.dirname(ra.__file__), 'review_app.py'), encoding='utf-8').read()
    assert 'return gr.Tabs(selected="caidat"), ("ten" if chua_dat_ten(ctx) else "cvat")' in src   # chuyển tab ở server: chạy cả khi tab nằm trong menu "More tabs"
    assert 'nap_ok.click(on_nap_ok, None, [tabs, o_thieu]' in src and '.then(None, o_thieu, None, js=CVAT_SANG_CAI_DAT_JS)' in src   # server chọn ô cần điền


def test_upload_with_cvat_does_not_show_the_dialog(proj):
    app = make_app(proj)
    res = nap_fn(app, 'on_start')(None, '', '', None)                                               # có CVAT (fixture): không hộp; thiếu ảnh thì báo như cũ
    assert res[-2] == {'__type__': 'update'} and res[-1] == {'__type__': 'update'}


def _app_auto(proj):
    """Trang mở bằng menu (không ghi tên), chưa lưu tên nào: người rà là tên mặc định P1."""
    gr = pytest.importorskip('gradio')  # noqa: F841
    import review_app as ra
    ctx = ra.AppCtx(reviewer='P1', run_dir=os.path.join('runs', '_nap'), nap_only=True, reviewer_auto=True, reviewer_mac_dinh=True)
    ctx.dong_ho = dong_ho.DongHo(ctx.project_root, gio=FakeGio(), pid=os.getpid())
    demo, _theme = ra.build_ui(None, ctx)
    return types.SimpleNamespace(ctx=ctx, demo=demo)


def test_upload_is_blocked_until_a_name_is_saved(proj, monkeypatch):
    """Chưa đặt tên (tên mặc định P1) thì không nạp: mọi người cùng để P1 thì thống kê gộp họ làm một. Hộp nói thiếu tên (và CVAT nếu cũng thiếu)."""
    import cai_dat
    app = _app_auto(proj)
    res = nap_fn(app, 'on_start')(None, '', '', None)
    assert res[-2] == {'__type__': 'update', 'visible': True} and 'Chưa đặt tên người rà' in res[-1] and 'Save name' in res[-1] and 'CVAT' not in res[-1].split('</div>')[0]
    monkeypatch.delenv('CVAT_URL', raising=False)
    res = nap_fn(app, 'on_start_open')(None, '', '', None)
    assert 'Chưa đặt tên người rà và chưa kết nối CVAT' in res[-1] and 'link CVAT' in res[-1]
    monkeypatch.setenv('CVAT_URL', URL)
    assert cai_dat.get().set_reviewer('Lan')['ok']
    res = nap_fn(app, 'on_start')(None, '', '', None)
    assert res[-2] == {'__type__': 'update'}                                                     # đã đặt tên và có CVAT: không hộp
    assert sorted(os.listdir(os.path.join(proj.root, 'runs'))) == sorted(['_nap', RUN])


def test_review_batch_is_refused_until_a_name_is_saved(proj):
    app = _app_auto(proj)
    f = next(x for x in app.demo.fns.values() if getattr(x.fn, '__name__', '') == 'do_act')
    out = f.fn(json.dumps(dict(act='ra', run=RUN)), None)
    assert any(isinstance(v, str) and 'Chưa đặt tên người rà' in v for v in out) and app.ctx.switch_to is None


def test_push_and_merge_on_the_batch_card_are_refused_until_a_name_is_saved(proj):
    """Push to CVAT và Merge jobs & Finish ở thẻ đợt cũng ghi tên người: chưa đặt tên thì từ chối như Review batch, không mở hộp xác nhận."""
    app = _app_auto(proj)
    f = next(x for x in app.demo.fns.values() if getattr(x.fn, '__name__', '') == 'do_act')
    for act, nut in (('push', 'Push to CVAT'), ('finish', 'Merge jobs &amp; Finish')):
        out = f.fn(json.dumps(dict(act=act, run=RUN)), None)
        assert any(isinstance(v, str) and 'Chưa đặt tên người rà' in v and nut in v for v in out), act
    assert app.ctx.push_pending.take('x') is None and not app.ctx.push_job.running and not app.ctx.collect_job.running


def test_push_panel_refuses_without_a_name():
    import dot_ui
    import cai_dat
    ctx = types.SimpleNamespace(reviewer='P1', reviewer_auto=True)
    if cai_dat.get().default_reviewer():
        pytest.skip('máy này đã lưu tên người rà')
    with pytest.raises(dot_ui.RunError, match='Chưa đặt tên người rà'):
        dot_ui.chan_khi_chua_dat_ten(ctx, 'bấm Push to CVAT')
    dot_ui.chan_khi_chua_dat_ten(types.SimpleNamespace(reviewer='P5', reviewer_auto=False), 'bấm Push to CVAT')     # ghi tên rõ khi mở: không chặn


def test_header_says_no_name_instead_of_the_placeholder(proj):
    """Chưa đặt tên: đầu trang ghi "chưa đặt tên", không ghi tên tạm P1 như thể đó là tên thật; lưu tên xong thì ghi tên."""
    import cai_dat
    import review_app as ra
    app = _app_auto(proj)
    assert 'chưa đặt tên' in ra.head_nap(app.ctx) and '<b>P1</b>' not in ra.head_nap(app.ctx)
    assert cai_dat.get().set_reviewer('Lan')['ok']
    app.ctx.reviewer = 'Lan'
    assert '<b>Lan</b>' in ra.head_nap(app.ctx) and 'chưa đặt tên' not in ra.head_nap(app.ctx)


def test_ok_of_the_dialog_points_at_the_missing_field(proj, monkeypatch):
    """OK của hộp: chuyển sang tab Cài đặt và nói JS ô nào còn thiếu. Chưa đặt tên thì ô tên trước; đã có tên (kể cả ghi tên rõ khi mở) thì ô link CVAT."""
    import cai_dat
    app = _app_auto(proj)
    f = next(x for x in app.demo.fns.values() if getattr(x.fn, '__name__', '') == 'on_nap_ok')
    tab, thieu = f.fn()
    assert thieu == 'ten' and getattr(tab, 'selected', None) == 'caidat'
    assert cai_dat.get().set_reviewer('Lan')['ok']
    assert f.fn()[1] == 'cvat'
    app2 = make_app(proj)                                                    # mở kèm tên (P5), chưa lưu tên mặc định nào: hộp chỉ nói thiếu CVAT
    f2 = next((x for x in app2.demo.fns.values() if getattr(x.fn, '__name__', '') == 'on_nap_ok'), None)
    assert f2 is None or f2.fn()[1] == 'cvat'
