"""Thử chip đồng hồ ở đầu trang (tool/dong_ho_ui.py) nối vào trang rà soát: dựng build_ui, gọi handler trực tiếp (không trình duyệt), đồng hồ giả. Không ảnh, không mạng.
Không còn tab "Đồng hồ": chip tự chạy khi Nạp ảnh, MỘT nút Pause/Resume; Save timing / Discard session nằm trong hộp Đóng trang."""
import csv
import glob
import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, '..', 'tool')
sys.path.insert(0, TOOL)
sys.path.insert(0, HERE)
gr = pytest.importorskip('gradio')
import dong_ho  # noqa: E402
import dong_ho_ui  # noqa: E402
import review_app as ra  # noqa: E402
from dh_fake import FakeGio, du_an  # noqa: E402


@pytest.fixture
def app(tmp_path, monkeypatch):
    root = du_an(tmp_path)
    monkeypatch.chdir(root)
    os.makedirs('runs/_nap', exist_ok=True)
    ctx = ra.AppCtx(reviewer='P5', run_dir=os.path.join('runs', '_nap'), nap_only=True)
    g = FakeGio()
    ctx.dong_ho = dong_ho.DongHo(ctx.project_root, gio=g, pid=os.getpid())
    return root, ctx, g


def small(ctx):
    """Chip + hai nút của hộp Đóng trang trong một Blocks nhỏ (hộp giả trả 'BODY' + đoạn thêm)."""
    with gr.Blocks() as demo:
        dh = dong_ho_ui.chip(gr, demo, ctx)
        body = gr.HTML(elem_id='close-body')
        cb = dong_ho_ui.close_buttons(gr, ctx, body, lambda extra: 'BODY ' + extra)
    return demo, dh, cb


def handlers(demo):
    out = {}
    for f in demo.fns.values():
        if f.fn is not None and getattr(f.fn, '__module__', '') == 'dong_ho_ui':
            out.setdefault(f.fn.__name__, []).append(f)
    return out


def call(demo, name, *args):
    """Gọi handler `name`; trả {elem_id: giá trị} (State là 'state')."""
    bf = handlers(demo)[name][0]
    res = bf.fn(*args)
    if len(bf.outputs) == 1:
        res = (res,)
    out = {}
    for c, v in zip(bf.outputs, res):
        if isinstance(c, gr.State):
            out['state'] = v
        else:
            out[getattr(c, 'elem_id', None) or id(c)] = v
    return out


def start_session(ctx, dot='NAP_001', n=4, cond='assisted'):
    return ctx.dong_ho.bat_dau('P5', cond, dot=dot, bo_anh=dot, n_mat=n)


# ---------- dựng giao diện ----------
def test_no_clock_tab_chip_is_on_every_page_and_ids_are_unique(app):
    root, ctx, g = app
    demo, _theme = ra.build_ui(None, ctx)
    elem = [getattr(b, 'elem_id', None) for b in demo.blocks.values()]
    order = [i for i in elem if i in ('tab-ra', 'tab-nap', 'tab-dot', 'tab-cakho', 'tab-hop', 'tab-dongho', 'tab-thongke', 'tab-loc', 'tab-caidat')]
    assert order == ['tab-ra', 'tab-nap', 'tab-dot', 'tab-cakho', 'tab-hop', 'tab-thongke', 'tab-loc', 'tab-caidat']          # không còn tab Đồng hồ
    assert not [i for i in elem if i and i.startswith('dh-') and i not in ('dh-bar', 'dh-mini-wrap', 'dh-mini-btn', 'dh-luu-btn', 'dh-bo-btn', 'dh-dot-dd')]
    assert {'dh-bar', 'dh-mini-wrap', 'dh-mini-btn', 'dh-luu-btn', 'dh-bo-btn', 'dh-dot-dd'} <= set(elem)
    dup = {i for i in elem if i and elem.count(i) > 1}
    assert not [i for i in dup if i.startswith('dh-')]
    buttons = [b for b in demo.blocks.values() if getattr(b, 'elem_id', None) == 'dh-mini-btn']
    assert len(buttons) == 1 and buttons[0].value == 'Pause' and buttons[0].interactive is False                      # MỘT nút, chưa có phiên thì chưa bấm được
    js = dong_ho_ui.JS_BODY
    assert '__m28Dh' in ra.PAGE_JS and 'performance.now()' in ra.PAGE_JS and 'Date.now' not in js and 'setInterval' in js
    assert 'fetch(' not in js and 'XMLHttpRequest' not in js and "'Đồng hồ'" not in js                              # không gọi server mỗi giây, không tìm tab Đồng hồ
    assert '#dh-mini-wrap' in ra.CSS and '#tab-dongho' not in ra.CSS and ra.PAGE_JS.rstrip().endswith('}') and ra.PAGE_JS.count('window.__m28Dh') >= 2


def test_builds_with_a_store_too(app):
    root, ctx, g = app
    os.makedirs('runs/R7', exist_ok=True)
    c2 = ra.AppCtx(reviewer='P2', run_dir=os.path.join('runs', 'R7'))
    c2.dong_ho = ctx.dong_ho
    with gr.Blocks() as demo:
        dong_ho_ui.chip(gr, demo, c2)
    assert 'dh-mini-btn' in [getattr(b, 'elem_id', None) for b in demo.blocks.values()]


def test_allowed_paths_not_widened_and_no_network_in_module():
    src = open(os.path.join(TOOL, 'review_app.py'), encoding='utf-8').read()
    block = src[src.index('allowed = ['):src.index('_launch(demo, theme, ctx, port, allowed', src.index('allowed = ['))]
    assert 'dong_ho' not in block and block.count('allowed.append(') == 3
    ui = open(os.path.join(TOOL, 'dong_ho_ui.py'), encoding='utf-8').read()
    assert 'urllib' not in ui and 'requests' not in ui and 'share=True' not in ui and ui.count('api_visibility="private"') >= 1
    for f in ('dong_ho.py', 'dong_ho_ui.py'):
        assert not re.search(r'(?m)^(import|from) gradio', open(os.path.join(TOOL, f), encoding='utf-8').read())


def test_modules_import_without_gradio_torch_cv2():
    import subprocess
    code = ("import sys\nsys.path.insert(0, %r)\nimport dong_ho, dong_ho_ui\nfor m in ('gradio', 'torch', 'cv2', 'mediapipe', 'cvat_sdk', 'pandas', 'numpy'):\n"
            "    assert m not in sys.modules, m\nprint('ok')\n") % TOOL
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0 and 'ok' in r.stdout, r.stderr


# ---------- tự chạy khi bấm Nạp ảnh ----------
def test_nap_anh_starts_the_clock_for_the_page_reviewer_and_wires_the_chip(app):
    root, ctx, g = app
    txt = dong_ho_ui.auto_start(None, ctx, 'NAP_008', 12)
    v = ctx.dong_ho.xem('P5')
    assert 'Đồng hồ của P5 bắt đầu chạy' in txt and v['co_phien'] and v['trang_thai'] == 'chay'
    assert v['dot'] == 'NAP_008' and v['n_mat'] == 12 and v['dieu_kien'] == 'assisted' and 'NAP_008' in ctx.dh_started          # không có file nhóm: mặc định assisted
    src = open(os.path.join(TOOL, 'review_app.py'), encoding='utf-8').read()
    assert 'dong_ho_ui.auto_start(gr, ctx, run,' in src and src.index('job.start(run, ctx.runs_root, ctx.project_root)') < src.index('dong_ho_ui.auto_start(')
    assert 'for ev in (ev_start, ev_open):' in src and 'ev.then(dh.refresh, None, dh.outs, **dh.opts)' in src                  # chip cập nhật ngay sau Upload & Continue / Upload & Open


def test_auto_start_takes_the_group_from_the_config_file(app):
    root, ctx, g = app
    json.dump({'nhom': {'P5': 'manual'}, 'bo_anh': 'NAP_001'}, open(os.path.join(root, 'config', 'nhom_thi_nghiem.json'), 'w'))
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 5)
    assert ctx.dong_ho.xem('P5')['dieu_kien'] == 'manual'


def test_auto_start_keeps_the_session_of_the_same_dot_running_or_paused(app):
    root, ctx, g = app
    start_session(ctx, dot='NAP_001', n=3)
    g.tick(20)
    again = dong_ho_ui.auto_start(None, ctx, 'NAP_001', 9)                         # nạp lại cùng tên đợt: giữ phiên, không đè
    assert 'giữ nguyên' in again and 'đang chạy' in again and ctx.dong_ho.xem('P5')['dot'] == 'NAP_001' and ctx.dong_ho.xem('P5')['giay_phien'] == 20
    ctx.dong_ho.tam_dung('P5', ctx.dong_ho.xem('P5')['rev'])
    paused = dong_ho_ui.auto_start(None, ctx, 'NAP_001', 9)
    assert 'tạm dừng' in paused and 'Resume' in paused and ctx.dong_ho.xem('P5')['trang_thai'] == 'tam_dung'                  # không tự Resume


def test_auto_start_with_an_invalid_reviewer_name_says_why_and_does_not_run(app):
    root, ctx, g = app
    ctx2 = ra.AppCtx(reviewer='Lam Tran', run_dir=os.path.join('runs', '_nap'), nap_only=True)
    ctx2.dong_ho = ctx.dong_ho
    txt = dong_ho_ui.auto_start(None, ctx2, 'NAP_001', 5)
    assert 'không hợp lệ' in txt and 'Cài đặt' in txt
    assert ctx.dong_ho.cac_nguoi() == []
    demo, dh, _cb = small(ctx2)
    out = call(demo, 'refresh')
    assert 'không hợp lệ' in out['dh-mini-wrap'] and out['dh-mini-btn']['interactive'] is False


def test_auto_start_without_a_name_runs_later_when_the_name_is_saved_in_settings(app):
    """Lỗi: bấm Nạp ảnh lúc chưa có tên hợp lệ thì đồng hồ báo cần tên và không tạo phiên; đặt tên ở Cài đặt xong đồng hồ vẫn không chạy (nút Start khoá vì chưa có phiên)."""
    import cai_dat
    root, ctx, g = app
    os.makedirs(os.path.join('runs', 'NAP_001'), exist_ok=True)
    ctx2 = ra.AppCtx(reviewer='Lam Tran', run_dir=os.path.join('runs', '_nap'), nap_only=True)
    ctx2.dong_ho = ctx.dong_ho
    assert 'không hợp lệ' in dong_ho_ui.auto_start(None, ctx2, 'NAP_001', 5)
    assert dong_ho_ui.bu_khi_co_ten(None, ctx2) is None                              # tên vẫn chưa hợp lệ: không chạy, vẫn nhớ lần Nạp ảnh đó
    assert ctx.dong_ho.cac_nguoi() == []
    assert cai_dat.get().set_reviewer('P3')['ok']                                    # Save name ở tab Cài đặt
    txt = dong_ho_ui.bu_khi_co_ten(None, ctx2)
    assert 'P3' in txt and 'NAP_001' in txt
    v = ctx.dong_ho.xem('P3')
    assert v['co_phien'] and v['dot'] == 'NAP_001' and v['trang_thai'] == 'chay'
    assert dong_ho_ui.bu_khi_co_ten(None, ctx2) is None                              # chỉ chạy bù một lần
    assert len([s for s in ctx.dong_ho.liet_ke('P3')]) == 1


def test_late_start_is_skipped_when_the_run_was_deleted_meanwhile(app):
    import cai_dat
    root, ctx, g = app
    ctx2 = ra.AppCtx(reviewer='Lam Tran', run_dir=os.path.join('runs', '_nap'), nap_only=True)
    ctx2.dong_ho = ctx.dong_ho
    dong_ho_ui.auto_start(None, ctx2, 'NAP_404', 5)                                  # thư mục runs/NAP_404 không tồn tại
    assert cai_dat.get().set_reviewer('P2')['ok']
    assert dong_ho_ui.bu_khi_co_ten(None, ctx2) is None
    assert ctx.dong_ho.cac_nguoi() == []


def test_auto_start_does_nothing_while_closing(app):
    root, ctx, g = app
    ctx.closing = True
    assert dong_ho_ui.auto_start(None, ctx, 'NAP_001', 5) is None and not ctx.dong_ho.xem('P5')['co_phien']


# ---------- chip và nút Pause/Resume ----------
def test_chip_idle_then_running_then_pause_resume_with_one_button(app):
    root, ctx, g = app
    demo, dh, _cb = small(ctx)
    idle = call(demo, 'refresh')
    assert 'Đồng hồ chưa chạy' in idle['dh-mini-wrap'] and 'tự chạy khi bấm Nạp ảnh' in idle['dh-mini-wrap'] and 'dh-mini-time' not in idle['dh-mini-wrap']
    assert idle['dh-mini-btn']['interactive'] is False
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 4)
    run = call(demo, 'refresh')
    assert 'dh-mini-time' in run['dh-mini-wrap'] and 'data-chay="1"' in run['dh-mini-wrap'] and '▶ Đang chạy' in run['dh-mini-wrap'] and 's-chay' in run['dh-mini-wrap']
    assert 'P5' in run['dh-mini-wrap'] and 'NAP_001' in run['dh-mini-wrap']
    assert run['dh-mini-btn']['interactive'] is True and run['dh-mini-btn']['value'] == 'Pause'
    g.tick(75)
    t = call(demo, 'on_tick')
    assert '01:15' in t['dh-mini-wrap'] and 'data-giay="75.000"' in t['dh-mini-wrap']
    p = call(demo, 'on_btn', t['state'])                                            # bấm nút khi đang chạy: Pause
    assert '⏸ Tạm dừng' in p['dh-mini-wrap'] and 'data-chay="0"' in p['dh-mini-wrap'] and 's-tam_dung' in p['dh-mini-wrap']
    assert p['dh-mini-btn']['value'] == 'Resume' and p['dh-mini-btn']['interactive'] is True
    g.tick(600)                                                                     # tạm dừng thì không cộng giờ
    assert '01:15' in call(demo, 'on_tick')['dh-mini-wrap']
    r = call(demo, 'on_btn', p['state'])                                            # bấm lại: Resume
    assert 'data-chay="1"' in r['dh-mini-wrap'] and r['dh-mini-btn']['value'] == 'Pause' and ctx.dong_ho.xem('P5')['trang_thai'] == 'chay'


def test_button_with_a_stale_rev_is_refused_and_the_chip_reloads(app):
    root, ctx, g = app
    demo, dh, _cb = small(ctx)
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 4)
    cu = call(demo, 'refresh')['state']
    assert cu == ('NAP_001', ctx.dong_ho.xem('P5')['rev'])                          # State của nút = (đợt, rev) của phiên đang hiện
    ctx.dong_ho.tam_dung('P5', cu[1])                                               # tab khác vừa dừng
    g.tick(5)
    out = call(demo, 'on_btn', cu)                                                  # tab này còn rev cũ: bị từ chối, không đè
    assert ctx.dong_ho.xem('P5')['trang_thai'] == 'tam_dung' and out['dh-mini-btn']['value'] == 'Resume' and out['state'] == ('NAP_001', ctx.dong_ho.xem('P5')['rev'])


def test_button_without_a_session_or_while_closing_does_nothing(app):
    root, ctx, g = app
    demo, dh, _cb = small(ctx)
    out = call(demo, 'on_btn', 0)
    assert not ctx.dong_ho.xem('P5')['co_phien'] and out['dh-mini-btn']['interactive'] is False
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 4)
    ctx.closing = True
    out = call(demo, 'on_btn', ctx.dong_ho.xem('P5')['rev'])
    assert ctx.dong_ho.xem('P5')['trang_thai'] == 'chay' and 'Đã đóng trang' in out['dh-mini-wrap']
    assert call(demo, 'on_tick')                                                    # đang đóng: nhịp không làm gì, không lỗi


def test_chip_follows_another_person_who_has_a_session(app):
    root, ctx, g = app
    demo, dh, _cb = small(ctx)
    ctx.dong_ho.bat_dau('P3', 'manual', dot='X9', n_mat=2)
    out = call(demo, 'refresh')
    assert 'P3' in out['dh-mini-wrap'] and 'X9' in out['dh-mini-wrap'] and out['dh-mini-btn']['interactive'] is True


def test_mini_html_has_no_secrets_or_absolute_paths(app):
    root, ctx, g = app
    start_session(ctx)
    for h in (dong_ho_ui.mini_html(ctx.dong_ho.xem('P5')), dong_ho_ui.mini_html(dict(co_phien=False)), dong_ho_ui.mini_html(dict(co_phien=False, hong=True))):
        assert root not in h and 'token' not in h.lower() and '/home' not in h and 'id="dh-mini"' in h
    assert 'bị hỏng' in dong_ho_ui.mini_html(dict(co_phien=False, hong=True))


# ---------- hộp Đóng trang: Save timing / Discard session ----------
def test_close_dialog_buttons_show_only_with_a_session(app):
    root, ctx, g = app
    demo, dh, cb = small(ctx)
    luu, bo, ma, dd = cb.show()
    assert luu['visible'] is False and bo['visible'] is False and ma == '' and dd['visible'] is False
    start_session(ctx)
    luu, bo, ma, dd = cb.show()
    assert luu['visible'] is True and bo['visible'] is True and bo['value'] == dong_ho_ui.NUT_BO and dd['visible'] is False        # một đợt: không cần ô chọn đợt


def test_save_from_the_dialog_writes_timing_csv_and_the_result_package(app):
    root, ctx, g = app
    demo, dh, cb = small(ctx)
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 4)
    g.tick(95)
    first = call(demo, 'on_luu')                                                   # đợt chưa đẩy CVAT: chưa có nhãn để gộp, chỉ nhắc đẩy rồi Merge, hoặc lưu chỉ thời gian
    assert 'chưa đẩy lên CVAT xong' in first['close-body'] and 'Push to CVAT' in first['close-body'] and 'collect --task' not in first['close-body']
    assert ctx.dong_ho.xem('P5')['co_phien'] and not os.path.exists(os.path.join(root, 'outputs', 'timing', 'timing_P5.csv'))
    out = call(demo, 'on_luu')                                                     # bấm thêm lần nữa: lưu (gói chỉ có thời gian)
    assert 'Đã lưu phiên của P5' in out['close-body'] and 'ket_qua' in out['close-body'] and root not in out['close-body']
    assert out['dh-luu-btn']['visible'] is False and out['dh-bo-btn']['visible'] is False
    assert not ctx.dong_ho.xem('P5')['co_phien']
    rows = list(csv.DictReader(open(os.path.join(root, 'outputs', 'timing', 'timing_P5.csv'), encoding='utf-8')))
    assert rows and list(rows[0])[:12] == ['date', 'person', 'condition', 'task', 'job', 'block', 'seq', 'face_id', 'seconds', 'warmup', 'interrupted', 'note']
    assert glob.glob(os.path.join(root, 'outputs', 'ket_qua', 'ketqua_P5_*_NAP_001.zip'))
    assert 'Đồng hồ chưa chạy' in call(demo, 'refresh')['dh-mini-wrap']


def test_save_too_short_session_explains_and_keeps_the_session(app):
    root, ctx, g = app
    demo, dh, cb = small(ctx)
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 4)
    g.tick(1)
    call(demo, 'on_luu')
    out = call(demo, 'on_luu')
    assert 'Phiên rỗng' in out['close-body'] and 'Discard session' in out['close-body'] and 'Hủy phiên' not in out['close-body'] and ctx.dong_ho.xem('P5')['co_phien'] and not os.path.exists(os.path.join(root, 'outputs', 'timing', 'timing_P5.csv'))


def test_save_with_nothing_to_save_says_so(app):
    root, ctx, g = app
    demo, dh, cb = small(ctx)
    out = call(demo, 'on_luu')
    assert 'Không có phiên đồng hồ nào để lưu' in out['close-body'] and out['dh-luu-btn']['visible'] is False


def test_discard_needs_two_clicks_and_writes_no_timing_row(app):
    root, ctx, g = app
    demo, dh, cb = small(ctx)
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 4)
    g.tick(30)
    one = call(demo, 'on_bo', '')
    assert ctx.dong_ho.xem('P5')['co_phien'] and one['state'] and one['dh-bo-btn']['value'] == dong_ho_ui.NUT_BO_LAN_2          # lần một: chưa bỏ, chờ bấm thêm
    two = call(demo, 'on_bo', one['state'])
    assert not ctx.dong_ho.xem('P5')['co_phien'] and 'Đã bỏ phiên đồng hồ của P5' in two['close-body']
    assert not os.path.exists(os.path.join(root, 'outputs', 'timing', 'timing_P5.csv')) and os.path.exists(os.path.join(root, 'outputs', 'timing', 'huy_P5.csv'))


def test_discard_with_a_wrong_code_keeps_the_session(app):
    root, ctx, g = app
    demo, dh, cb = small(ctx)
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 4)
    g.tick(30)
    out = call(demo, 'on_bo', 'ma-sai')
    assert ctx.dong_ho.xem('P5')['co_phien'] and out['dh-bo-btn']['value'] == dong_ho_ui.NUT_BO and out['state'] == ''


def test_close_note_names_the_person_the_state_and_the_save_button(app):
    root, ctx, g = app
    assert dong_ho_ui.close_note(ctx) == ''
    start_session(ctx)
    g.tick(30)
    n1 = dong_ho_ui.close_note(ctx)
    assert 'P5' in n1 and 'tự tạm dừng' in n1 and 'Save timing' in n1 and '00:30' in n1
    ctx.dong_ho.tam_dung('P5', ctx.dong_ho.xem('P5')['rev'])
    n2 = dong_ho_ui.close_note(ctx)
    assert 'đang tạm dừng' in n2 and 'tự tạm dừng' not in n2 and 'Save timing' in n2


# ---------- đóng trang ----------
def test_close_confirm_pauses_running_clocks_and_says_so_first(app, capsys):
    root, ctx, g = app
    ctx.dong_ho.bat_dau('P5', 'manual', dot='X1', n_mat=2)
    g.tick(30)
    assert 'tự tạm dừng' in ra.close_body_html(None, dong_ho_ui.close_note(ctx)) and 'P5' in dong_ho_ui.close_note(ctx)
    demo, _theme = ra.build_ui(None, ctx)
    on_open = next(f for f in demo.fns.values() if f.fn is not None and f.fn.__name__ == 'on_open' and f.fn.__module__ == 'review_app')
    res = on_open.fn()
    assert 'tự tạm dừng' in json.dumps(res, ensure_ascii=False, default=str)
    on_confirm = next(f for f in demo.fns.values() if f.fn is not None and f.fn.__name__ == 'on_confirm' and f.fn.__module__ == 'review_app')
    on_confirm.fn()
    assert ctx.closing and ctx.dong_ho.xem('P5')['trang_thai'] == 'tam_dung' and 'tat_trang' in ctx.dong_ho.xem('P5')['ma_canh_bao']
    out = capsys.readouterr().out
    assert 'Đồng hồ của P5 đã tạm dừng lúc 18:30:30' in out and 'bấm Resume' in out
    with pytest.raises(dong_ho.DongHoLoi, match='đang đóng'):
        ctx.dong_ho.tiep_tuc('P5')


def test_ctrl_c_path_pauses_clock_and_main_calls_it():
    src = open(os.path.join(TOOL, 'review_app.py'), encoding='utf-8').read()
    branch = src[src.index('except KeyboardInterrupt:'):]
    assert 'dong_ho_ui.tu_tam_dung(ctx)' in branch[:200]
    i = src.index('def on_confirm')
    assert 'dong_ho_ui.tu_tam_dung(ctx)' in src[i:src.index('def on_cancel', i)]


def test_tu_tam_dung_with_nothing_running_prints_nothing(app, capsys):
    root, ctx, g = app
    assert dong_ho_ui.tu_tam_dung(ctx) == [] and capsys.readouterr().out == ''


def test_save_with_a_collected_label_file_goes_through_in_one_click(app):
    root, ctx, g = app
    demo, dh, cb = small(ctx)
    os.makedirs(os.path.join(root, 'raw'), exist_ok=True)
    open(os.path.join(root, 'raw', 'demo-NAP_001_P5_0910.xml'), 'w', encoding='utf-8').write('<annotations></annotations>')
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 4)
    g.tick(95)
    out = call(demo, 'on_luu')
    assert 'Đã lưu phiên của P5' in out['close-body'] and not ctx.dong_ho.xem('P5')['co_phien']


def test_messages_for_the_old_buttons_are_reworded_for_the_dialog():
    t = dong_ho_ui.vi_hop('Còn cảnh báo chưa xử lý (a). Chọn Sửa thời gian / Giữ nguyên, hoặc bấm Xong (lưu) thêm một lần nữa để lưu kèm cảnh báo. Bấm Hủy phiên nếu không cần.')
    assert 'Sửa thời gian' not in t and 'Xong (lưu)' not in t and 'Hủy phiên' not in t
    assert 'Bấm Save timing thêm một lần nữa để lưu kèm cảnh báo.' in t and 'Bấm Discard session nếu không cần.' in t


# ---------- MỖI ĐỢT MỘT ĐỒNG HỒ (QĐ-007) ----------
def page_ctx(root, ctx, name, reviewer='P5'):
    """Ctx của một trang đang mở đợt `name` (chung DongHo với ctx)."""
    os.makedirs(os.path.join('runs', name), exist_ok=True)
    c = ra.AppCtx(reviewer=reviewer, run_dir=os.path.join('runs', name))
    c.dong_ho = ctx.dong_ho
    return c


def test_upload_and_open_moves_the_clock_to_the_new_dot_and_keeps_the_old_seconds(app):
    """Ca thật: nạp đợt thứ hai khi đang có phiên ở đợt đầu. Trước đây đồng hồ vẫn ghi đợt đầu và cộng dồn giờ của cả hai đợt."""
    root, ctx, g = app
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 5)
    g.tick(90)
    txt = dong_ho_ui.auto_start(None, ctx, 'NAP_002', 7, True)
    a, b = ctx.dong_ho.xem('P5', 'NAP_001'), ctx.dong_ho.xem('P5', 'NAP_002')
    assert 'bắt đầu chạy (đợt NAP_002' in txt and 'Đồng hồ đợt NAP_001 tạm dừng ở 01:30' in txt
    assert a['trang_thai'] == 'tam_dung' and a['giay_phien'] == pytest.approx(90.0) and b['chay'] and b['giay_phien'] == 0 and b['n_mat'] == 7 and b['task'] == 'demo-NAP_002'
    g.tick(20)
    assert ctx.dong_ho.xem('P5', 'NAP_001')['giay_phien'] == pytest.approx(90.0) and ctx.dong_ho.xem('P5', 'NAP_002')['giay_phien'] == pytest.approx(20.0)
    assert {'NAP_001', 'NAP_002'} <= ctx.dh_started


def test_upload_and_continue_leaves_the_running_clock_and_the_new_dot_waits(app):
    root, ctx, g = app
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 5)
    g.tick(30)
    txt = dong_ho_ui.auto_start(None, ctx, 'NAP_002', 7, False)
    a, b = ctx.dong_ho.xem('P5', 'NAP_001'), ctx.dong_ho.xem('P5', 'NAP_002')
    assert 'đang chờ ở 00:00' in txt and 'đợt NAP_001 giữ nguyên' in txt and 'Start' in txt
    assert a['chay'] and a['giay_phien'] == pytest.approx(30.0) and b['cho'] and b['trang_thai'] == 'tam_dung' and b['giay_phien'] == 0


def test_upload_and_continue_still_starts_the_clock_when_nothing_else_has_one(app):
    root, ctx, g = app
    txt = dong_ho_ui.auto_start(None, ctx, 'NAP_001', 5, False)
    assert 'bắt đầu chạy' in txt and ctx.dong_ho.xem('P5', 'NAP_001')['chay']
    ctx.dong_ho.tam_dung('P5', dot='NAP_001')                                         # có phiên nhưng đang nghỉ: Continue vẫn để đợt mới chờ, không đụng phiên cũ
    txt = dong_ho_ui.auto_start(None, ctx, 'NAP_002', 5, False)
    assert 'đang chờ' in txt and 'các đợt khác giữ nguyên' in txt and ctx.dong_ho.xem('P5', 'NAP_002')['cho'] and ctx.dong_ho.xem('P5', 'NAP_001')['trang_thai'] == 'tam_dung'


def test_chip_shows_the_running_dot_else_the_page_dot_and_lists_the_others(app):
    root, ctx, g = app
    c1, c2, c3 = (page_ctx(root, ctx, n) for n in ('NAP_001', 'NAP_002', 'NAP_003'))
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 5)
    g.tick(60)
    dong_ho_ui.auto_start(None, ctx, 'NAP_002', 7, True)
    g.tick(15)
    d2, d1, d3 = small(c2)[0], small(c1)[0], small(c3)[0]
    o2 = call(d2, 'refresh')                                                          # trang ở NAP_002 đang chạy: 00:15, đợt khác NAP_001 01:00
    assert '00:15' in o2['dh-mini-wrap'] and 'NAP_002' in o2['dh-mini-wrap'] and 'đợt khác: NAP_001 01:00 ⏸' in o2['dh-mini-wrap'] and o2['state'][0] == 'NAP_002'
    o1 = call(d1, 'refresh')                                                          # trang ở NAP_001 nhưng đồng hồ đang chạy ở NAP_002: chip theo phiên đang chạy
    assert '00:15' in o1['dh-mini-wrap'] and 'NAP_002' in o1['dh-mini-wrap'] and o1['state'][0] == 'NAP_002'
    ctx.dong_ho.tam_dung('P5', dot='NAP_002')
    o1 = call(d1, 'refresh')                                                          # không chạy: chip theo đợt của trang, giờ RIÊNG của đợt đó
    assert '01:00' in o1['dh-mini-wrap'] and 'data-giay="60.000"' in o1['dh-mini-wrap'] and 'đợt khác: NAP_002 00:15 ⏸' in o1['dh-mini-wrap'] and o1['state'][0] == 'NAP_001'
    assert o1['dh-mini-btn']['value'] == 'Resume'
    o3 = call(d3, 'refresh')                                                          # trang ở đợt chưa có đồng hồ: chip nói rõ, KHÔNG mượn giờ đợt khác, nút khoá
    assert 'chưa chạy cho đợt NAP_003' in o3['dh-mini-wrap'] and 'dh-mini-time' not in o3['dh-mini-wrap'] and o3['dh-mini-btn']['interactive'] is False
    assert 'NAP_001' in o3['dh-mini-wrap'] and 'NAP_002' in o3['dh-mini-wrap'] and o3['state'] == (None, 0)


def test_waiting_dot_shows_start_and_start_pauses_the_other_dot(app):
    root, ctx, g = app
    c2 = page_ctx(root, ctx, 'NAP_002')
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 5)
    g.tick(40)
    dong_ho_ui.auto_start(None, ctx, 'NAP_002', 7, False)
    ctx.dong_ho.tam_dung('P5', dot='NAP_001')
    demo = small(c2)[0]
    out = call(demo, 'refresh')
    assert out['dh-mini-btn']['value'] == 'Start' and out['dh-mini-btn']['interactive'] is True and 'Chờ bắt đầu' in out['dh-mini-wrap'] and '00:00' in out['dh-mini-wrap']
    out = call(demo, 'on_btn', out['state'])
    assert out['dh-mini-btn']['value'] == 'Pause' and ctx.dong_ho.xem('P5', 'NAP_002')['chay'] and ctx.dong_ho.xem('P5', 'NAP_001')['giay_phien'] == pytest.approx(40.0)


def test_button_is_refused_when_the_shown_dot_changed_under_the_tab(app):
    root, ctx, g = app
    c1 = page_ctx(root, ctx, 'NAP_001')
    demo = small(c1)[0]
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 5)
    shown = call(demo, 'refresh')['state']                                             # tab này đang hiện NAP_001
    g.tick(20)
    dong_ho_ui.auto_start(None, ctx, 'NAP_002', 7, True)                               # tab khác: đồng hồ chuyển sang NAP_002
    out = call(demo, 'on_btn', shown)
    assert ctx.dong_ho.xem('P5', 'NAP_002')['chay'] and ctx.dong_ho.xem('P5', 'NAP_001')['trang_thai'] == 'tam_dung'          # không đụng gì
    assert out['state'][0] == 'NAP_002'                                                # chip tải lại và theo phiên đang chạy


def test_page_switch_moves_the_running_clock_to_the_new_page(app):
    root, ctx, g = app
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 5)
    g.tick(40)
    dong_ho_ui.auto_start(None, ctx, 'NAP_002', 7, False)                              # Upload & Continue: NAP_002 chờ, NAP_001 vẫn chạy
    g.tick(10)
    c2 = page_ctx(root, ctx, 'NAP_002')
    msg = dong_ho_ui.theo_trang(c2)                                                    # Review batch sang NAP_002
    a, b = ctx.dong_ho.xem('P5', 'NAP_001'), ctx.dong_ho.xem('P5', 'NAP_002')
    assert 'chuyển từ đợt NAP_001' in msg and 'sang đợt NAP_002' in msg and a['trang_thai'] == 'tam_dung' and a['giay_phien'] == pytest.approx(50.0)
    assert b['chay'] and not b['cho'] and b['giay_phien'] == 0
    g.tick(5)
    c3 = page_ctx(root, ctx, 'NAP_003')                                                # Review batch sang đợt chưa có đồng hồ: tạo phiên mới, chạy ngay, đợt đang chạy tạm dừng
    msg = dong_ho_ui.theo_trang(c3)
    assert 'bắt đầu chạy ở đợt NAP_003' in msg and 'NAP_002 tạm dừng ở 00:05' in msg
    v3 = ctx.dong_ho.xem('P5', 'NAP_003')
    assert v3['co_phien'] and v3['chay'] and ctx.dong_ho.xem('P5', 'NAP_002')['trang_thai'] == 'tam_dung' and ctx.dong_ho.dang_chay_ai() == ['P5']
    assert dong_ho_ui.theo_trang(c3) == ''                                             # đợt đã có phiên đang chạy: không làm gì, không tạo thêm
    assert len(ctx.dong_ho.liet_ke('P5')) == 3
    msg = dong_ho_ui.theo_trang(c2)                                                    # quay lại NAP_002 (phiên tạm dừng): phiên đó chạy tiếp, NAP_003 tạm dừng
    assert 'chuyển từ đợt NAP_003' in msg and 'sang đợt NAP_002' in msg
    ctx.dong_ho.tam_dung('P5', None, dot='NAP_002')
    assert dong_ho_ui.theo_trang(c3) == '' and dong_ho_ui.theo_trang(c2) == ''          # không có gì đang chạy: không làm gì (không tự Resume)
    ctx.dong_ho.goi_da_luu = lambda nguoi: [('ketqua_P5_x', {'dot': 'NAP_004'})]        # đợt đã Merge jobs & Finish (có gói): mở lại không tạo đồng hồ thứ hai
    assert dong_ho_ui.theo_trang(page_ctx(root, ctx, 'NAP_004')) == '' and not ctx.dong_ho.xem('P5', 'NAP_004')['co_phien']
    ctx.closing = True
    c2.closing = True
    assert dong_ho_ui.theo_trang(c2) == ''


def test_page_switch_in_main_loop_calls_theo_trang():
    src = open(os.path.join(TOOL, 'review_app.py'), encoding='utf-8').read()
    assert 'dong_ho_ui.auto_start(gr, ctx, run, len(plan_st["plan"]["ok"]), open_after)' in src
    i = src.index('ctx = AppCtx(reviewer=new_store.reviewer, run_dir=new_dir)')
    assert 'dong_ho_ui.theo_trang(ctx)' in src[i:i + 600]


def test_close_dialog_lists_every_dot_and_saves_only_the_selected_one(app):
    root, ctx, g = app
    c2 = page_ctx(root, ctx, 'NAP_002')
    demo, dh, cb = small(c2)
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 4)
    g.tick(95)
    dong_ho_ui.auto_start(None, ctx, 'NAP_002', 6, True)
    g.tick(50)
    note = dong_ho_ui.close_note(c2)
    assert '2 đợt' in note and 'mỗi đợt tính giờ riêng' in note and 'NAP_001' in note and '01:35' in note and 'NAP_002' in note and '00:50' in note and 'tự tạm dừng' in note
    luu, bo, ma, dd = cb.show()
    assert luu['visible'] and bo['visible'] and dd['visible'] is True and dd['value'] == 'NAP_002' and [c[1] for c in dd['choices']] == ['NAP_001', 'NAP_002']
    os.makedirs(os.path.join(root, 'runs', 'NAP_001'), exist_ok=True)
    json.dump(dict(task='demo-NAP_001', trang_thai='xong'), open(os.path.join(root, 'runs', 'NAP_001', 'push.json'), 'w'))   # NAP_001 đã đẩy CVAT xong
    first = call(demo, 'on_luu', 'NAP_001')                                            # chưa có nhãn xuất của NAP_001: nhắc Merge jobs & Finish (hoặc collect), chưa lưu gì
    assert 'collect --task demo-NAP_001 --reviewer P5 --overwrite' in first['close-body'] and 'Merge jobs &amp; Finish ở thẻ đợt NAP_001' in first['close-body']
    assert 'NAP_001' in first['close-body'] and ctx.dong_ho.xem('P5', 'NAP_001')['co_phien']
    out = call(demo, 'on_luu', 'NAP_001')
    assert 'Đã lưu phiên của P5 (đợt NAP_001)' in out['close-body'] and root not in out['close-body']
    assert out['dh-luu-btn']['visible'] is True and out['dh-dot-dd']['visible'] is False                 # còn NAP_002 chưa lưu, hết cần ô chọn
    assert not ctx.dong_ho.xem('P5', 'NAP_001')['co_phien'] and ctx.dong_ho.xem('P5', 'NAP_002')['co_phien']
    assert glob.glob(os.path.join(root, 'outputs', 'ket_qua', 'ketqua_P5_*_NAP_001.zip')) and not glob.glob(os.path.join(root, 'outputs', 'ket_qua', 'ketqua_P5_*_NAP_002.zip'))
    rows = list(csv.DictReader(open(os.path.join(root, 'outputs', 'timing', 'timing_P5.csv'), encoding='utf-8')))
    assert rows and {r['dot'] for r in rows} == {'NAP_001'} and {r['giay_phien'] for r in rows} == {'95.0'}      # giờ của NAP_002 không lẫn vào
    assert 'NAP_002' in call(demo, 'refresh')['dh-mini-wrap']


def test_save_uses_the_label_file_of_the_selected_dot_only(app):
    root, ctx, g = app
    demo, dh, cb = small(ctx)
    os.makedirs(os.path.join(root, 'raw'), exist_ok=True)
    open(os.path.join(root, 'raw', 'demo-NAP_002_P5_0910.xml'), 'w', encoding='utf-8').write('<annotations></annotations>')       # chỉ có nhãn của NAP_002
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 4)
    g.tick(95)
    dong_ho_ui.auto_start(None, ctx, 'NAP_002', 4, True)
    g.tick(95)
    assert 'chưa có nhãn để gộp' in call(demo, 'on_luu', 'NAP_001')['close-body']      # NAP_001 chưa có nhãn của chính nó (và chưa đẩy CVAT)
    assert 'Đã lưu phiên của P5 (đợt NAP_002)' in call(demo, 'on_luu', 'NAP_002')['close-body']        # NAP_002 có: lưu ngay một lần bấm


def test_discard_acts_on_the_selected_dot_and_names_it(app):
    root, ctx, g = app
    demo, dh, cb = small(ctx)
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 4)
    g.tick(30)
    dong_ho_ui.auto_start(None, ctx, 'NAP_002', 4, True)
    g.tick(30)
    one = call(demo, 'on_bo', '', 'NAP_001')
    assert 'NAP_001' in one['close-body'] and one['dh-bo-btn']['value'] == dong_ho_ui.NUT_BO_LAN_2 and one['state']
    two = call(demo, 'on_bo', one['state'], 'NAP_001')
    assert 'Đã bỏ phiên đồng hồ của P5 (đợt NAP_001)' in two['close-body']
    assert not ctx.dong_ho.xem('P5', 'NAP_001')['co_phien'] and ctx.dong_ho.xem('P5', 'NAP_002')['chay']
    assert two['dh-luu-btn']['visible'] is True and two['dh-bo-btn']['value'] == dong_ho_ui.NUT_BO          # còn NAP_002: giữ hai nút
    assert not os.path.exists(os.path.join(root, 'outputs', 'timing', 'timing_P5.csv'))


def test_mini_html_lists_at_most_three_other_dots_and_escapes_names(app):
    root, ctx, g = app
    v = dict(co_phien=True, trang_thai='chay', giay_phien=5.0, nguoi='P5', dot='X', task='demo-X', cho=False,
             cac_dot=[dict(dot=f'D{i}', giay_phien=60.0 * i, chay=False, bat_dau=f'2026-10-14T18:3{i}:00+07:00') for i in range(5)] + [dict(dot='<b>', giay_phien=1.0, chay=False, bat_dau='2026-10-14T18:00:00+07:00')])
    h = dong_ho_ui.mini_html(v)
    assert h.count(' ⏸') == 3 and '+3 đợt' in h and '&lt;b&gt;' in h and '<b>' not in h.replace('<b id="dh-mini-time"', '').replace('</b>', '')
    assert dong_ho_ui.khac_html([]) == '' and 'đợt khác' not in dong_ho_ui.mini_html(dict(co_phien=True, trang_thai='chay', giay_phien=1.0, nguoi='P5', dot='X', cho=False))


def test_the_pause_message_names_the_dot(app, capsys):
    root, ctx, g = app
    dong_ho_ui.auto_start(None, ctx, 'NAP_007', 3)
    g.tick(5)
    got = dong_ho_ui.tu_tam_dung(ctx)
    assert got == [('P5', '18:30:05', 'NAP_007')] and 'lúc 18:30:05 (đợt NAP_007)' in capsys.readouterr().out


def test_clock_bar_is_hidden_outside_the_three_batch_tabs():
    """Thanh đồng hồ (#dh-bar) chỉ hiện ở Rà soát, Nạp ảnh, Các đợt: JS gắn m28-dh-hide theo tab đang chọn, CSS ẩn; đồng hồ vẫn chạy ngầm."""
    js, css = dong_ho_ui.JS_BODY, dong_ho_ui.CSS
    assert "['Rà soát', 'Nạp ảnh', 'Các đợt']" in js and "#tabs button[role=\"tab\"][aria-selected=\"true\"]" in js and 'm28-dh-hide' in js
    assert '#dh-bar.m28-dh-hide { display: none !important; }' in css
    for tab in ('Ca khó', 'Họp team', 'Thống kê', 'Lọc dữ liệu', 'Cài đặt'):
        assert f"'{tab}'" not in js.split('const SHOW')[1].split(';')[0]
    assert 'setInterval' in js and 'dh-mini-time' in js                      # bộ đếm mm:ss không gắn với việc ẩn/hiện thanh
