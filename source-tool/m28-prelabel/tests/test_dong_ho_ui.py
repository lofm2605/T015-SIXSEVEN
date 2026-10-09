"""Thử chip đồng hồ ở đầu trang (tool/dong_ho_ui.py) nối vào trang rà soát: dựng build_ui, gọi handler trực tiếp (không trình duyệt), đồng hồ giả. Không ảnh, không mạng.
Không còn tab "Đồng hồ": chip tự chạy khi Nạp ảnh, MỘT nút Dừng/Tiếp tục; Lưu số đo / Bỏ phiên nằm trong hộp Đóng trang."""
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
    assert not [i for i in elem if i and i.startswith('dh-') and i not in ('dh-bar', 'dh-mini-wrap', 'dh-mini-btn', 'dh-luu-btn', 'dh-bo-btn')]
    assert {'dh-bar', 'dh-mini-wrap', 'dh-mini-btn', 'dh-luu-btn', 'dh-bo-btn'} <= set(elem)
    dup = {i for i in elem if i and elem.count(i) > 1}
    assert not [i for i in dup if i.startswith('dh-')]
    buttons = [b for b in demo.blocks.values() if getattr(b, 'elem_id', None) == 'dh-mini-btn']
    assert len(buttons) == 1 and buttons[0].value == 'Dừng' and buttons[0].interactive is False                      # MỘT nút, chưa có phiên thì chưa bấm được
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


def test_auto_start_keeps_an_existing_session_running_or_paused(app):
    root, ctx, g = app
    start_session(ctx, dot='NAP_001', n=3)
    g.tick(20)
    again = dong_ho_ui.auto_start(None, ctx, 'NAP_002', 9)
    assert 'giữ nguyên' in again and 'đang chạy' in again and ctx.dong_ho.xem('P5')['dot'] == 'NAP_001' and ctx.dong_ho.xem('P5')['giay_phien'] == 20
    ctx.dong_ho.tam_dung('P5', ctx.dong_ho.xem('P5')['rev'])
    paused = dong_ho_ui.auto_start(None, ctx, 'NAP_003', 9)
    assert 'tạm dừng' in paused and 'Tiếp tục' in paused and ctx.dong_ho.xem('P5')['trang_thai'] == 'tam_dung'                  # không tự Tiếp tục


def test_auto_start_with_a_reviewer_that_is_not_p1_to_p5_says_why_and_does_not_run(app):
    root, ctx, g = app
    ctx2 = ra.AppCtx(reviewer='Lam', run_dir=os.path.join('runs', '_nap'), nap_only=True)
    ctx2.dong_ho = ctx.dong_ho
    txt = dong_ho_ui.auto_start(None, ctx2, 'NAP_001', 5)
    assert 'P1 đến P5' in txt and 'Cài đặt' in txt
    assert not any(ctx.dong_ho.xem(p).get('co_phien') for p in dong_ho.NGUOI_OK)
    demo, dh, _cb = small(ctx2)
    out = call(demo, 'refresh')
    assert 'P1 đến P5' in out['dh-mini-wrap'] and out['dh-mini-btn']['interactive'] is False


def test_auto_start_does_nothing_while_closing(app):
    root, ctx, g = app
    ctx.closing = True
    assert dong_ho_ui.auto_start(None, ctx, 'NAP_001', 5) is None and not ctx.dong_ho.xem('P5')['co_phien']


# ---------- chip và nút Dừng/Tiếp tục ----------
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
    assert run['dh-mini-btn']['interactive'] is True and run['dh-mini-btn']['value'] == 'Dừng'
    g.tick(75)
    t = call(demo, 'on_tick')
    assert '01:15' in t['dh-mini-wrap'] and 'data-giay="75.000"' in t['dh-mini-wrap']
    p = call(demo, 'on_btn', t['state'])                                            # bấm nút khi đang chạy: Dừng
    assert '⏸ Tạm dừng' in p['dh-mini-wrap'] and 'data-chay="0"' in p['dh-mini-wrap'] and 's-tam_dung' in p['dh-mini-wrap']
    assert p['dh-mini-btn']['value'] == 'Tiếp tục' and p['dh-mini-btn']['interactive'] is True
    g.tick(600)                                                                     # tạm dừng thì không cộng giờ
    assert '01:15' in call(demo, 'on_tick')['dh-mini-wrap']
    r = call(demo, 'on_btn', p['state'])                                            # bấm lại: Tiếp tục
    assert 'data-chay="1"' in r['dh-mini-wrap'] and r['dh-mini-btn']['value'] == 'Dừng' and ctx.dong_ho.xem('P5')['trang_thai'] == 'chay'


def test_button_with_a_stale_rev_is_refused_and_the_chip_reloads(app):
    root, ctx, g = app
    demo, dh, _cb = small(ctx)
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 4)
    cu = call(demo, 'refresh')['state']
    ctx.dong_ho.tam_dung('P5', cu)                                                  # tab khác vừa dừng
    g.tick(5)
    out = call(demo, 'on_btn', cu)                                                  # tab này còn rev cũ: bị từ chối, không đè
    assert ctx.dong_ho.xem('P5')['trang_thai'] == 'tam_dung' and out['dh-mini-btn']['value'] == 'Tiếp tục' and out['state'] == ctx.dong_ho.xem('P5')['rev']


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


# ---------- hộp Đóng trang: Lưu số đo / Bỏ phiên ----------
def test_close_dialog_buttons_show_only_with_a_session(app):
    root, ctx, g = app
    demo, dh, cb = small(ctx)
    luu, bo, ma = cb.show()
    assert luu['visible'] is False and bo['visible'] is False and ma == ''
    start_session(ctx)
    luu, bo, ma = cb.show()
    assert luu['visible'] is True and bo['visible'] is True and bo['value'] == dong_ho_ui.NUT_BO


def test_save_from_the_dialog_writes_timing_csv_and_the_result_package(app):
    root, ctx, g = app
    demo, dh, cb = small(ctx)
    dong_ho_ui.auto_start(None, ctx, 'NAP_001', 4)
    g.tick(95)
    first = call(demo, 'on_luu')                                                   # chưa có nhãn xuất trong raw/: nhắc collect trước, chưa lưu gì
    assert 'collect --reviewer P5' in first['close-body'] and ctx.dong_ho.xem('P5')['co_phien'] and not os.path.exists(os.path.join(root, 'outputs', 'timing', 'timing_P5.csv'))
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
    assert 'Phiên rỗng' in out['close-body'] and 'Bỏ phiên đồng hồ' in out['close-body'] and 'Hủy phiên' not in out['close-body'] and ctx.dong_ho.xem('P5')['co_phien'] and not os.path.exists(os.path.join(root, 'outputs', 'timing', 'timing_P5.csv'))


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
    assert 'P5' in n1 and 'tự tạm dừng' in n1 and 'Lưu số đo' in n1 and '00:30' in n1
    ctx.dong_ho.tam_dung('P5', ctx.dong_ho.xem('P5')['rev'])
    n2 = dong_ho_ui.close_note(ctx)
    assert 'đang tạm dừng' in n2 and 'tự tạm dừng' not in n2 and 'Lưu số đo' in n2


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
    assert 'Đồng hồ của P5 đã tạm dừng lúc 18:30:30' in out and 'bấm Tiếp tục' in out
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
    assert 'Bấm Lưu số đo thêm một lần nữa để lưu kèm cảnh báo.' in t and 'Bấm Bỏ phiên đồng hồ nếu không cần.' in t
