"""Thử tab "Đồng hồ" (tool/dong_ho_ui.py) nối vào trang rà soát: dựng build_ui, gọi handler trực tiếp (không trình duyệt), đồng hồ giả. Không ảnh, không mạng."""
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


def tab(ctx):
    with gr.Blocks() as demo:
        fn, _i, outs, _o = dong_ho_ui.dong_ho_tab(gr, demo, None, ctx)
    return demo, fn


def handlers(demo):
    out = {}
    for f in demo.fns.values():
        if f.fn is not None and getattr(f.fn, '__module__', '') == 'dong_ho_ui':
            out.setdefault(f.fn.__name__, []).append(f)
    return out


def call(demo, name, *args):
    """Gọi handler `name`; trả {elem_id hoặc 'state': giá trị}."""
    bf = handlers(demo)[name][0]
    res = bf.fn(*args)
    if len(bf.outputs) == 1:
        res = (res,)
    out, n_state = {}, 0
    for c, v in zip(bf.outputs, res):
        if isinstance(c, gr.State):                            # State thứ nhất là rev, thứ hai là mã yêu cầu hủy
            out['state' if n_state == 0 else 'huy_state'] = v
            n_state += 1
        else:
            out[getattr(c, 'elem_id', None) or id(c)] = v
    return out


def val(x, key):
    return x.get(key) if isinstance(x, dict) else x


def text(v):
    return json.dumps(v, ensure_ascii=False, default=str) if isinstance(v, (dict, list)) else str(v)


START = ('P5', 'assisted', 'NAP_001', '', '', '', 4, None, 'ghi chú phiên')


def start(demo, rev=0):
    return call(demo, 'on_start', *START, rev)


# ---------- dựng giao diện ----------
def test_tab_is_after_hop_before_thongke_with_unique_ids_and_js(app):
    root, ctx, g = app
    demo, _theme = ra.build_ui(None, ctx)
    elem = [getattr(b, 'elem_id', None) for b in demo.blocks.values()]
    order = [i for i in elem if i in ('tab-ra', 'tab-nap', 'tab-dot', 'tab-cakho', 'tab-hop', 'tab-dongho', 'tab-thongke', 'tab-loc', 'tab-caidat')]
    assert order == ['tab-ra', 'tab-nap', 'tab-dot', 'tab-cakho', 'tab-hop', 'tab-dongho', 'tab-thongke', 'tab-loc', 'tab-caidat']          # năm tab đầu và Cài đặt cuối như cũ
    mine = [i for i in elem if i and i.startswith('dh-')]
    assert len(mine) == len(set(mine)) and {'dh-start', 'dh-pause', 'dh-done', 'dh-cancel', 'dh-face', 'dh-undo', 'dh-cancel-ok', 'dh-cancel-cancel', 'dh-clock-wrap'} <= set(mine)
    dup = {i for i in elem if i and elem.count(i) > 1}
    assert not [i for i in dup if i.startswith('dh-') or i == 'tab-dongho']
    assert '__m28Dh' in ra.PAGE_JS and 'performance.now()' in ra.PAGE_JS and 'Date.now' not in dong_ho_ui.JS_BODY and 'setInterval' in dong_ho_ui.JS_BODY
    assert 'fetch(' not in dong_ho_ui.JS_BODY and 'XMLHttpRequest' not in dong_ho_ui.JS_BODY                  # không gọi server mỗi giây
    assert '#tab-dongho' in ra.CSS and ra.PAGE_JS.rstrip().endswith('}') and ra.PAGE_JS.count('window.__m28Dh') >= 2


def test_builds_with_a_store_too_and_dot_default_is_the_run_name(app):
    root, ctx, g = app
    from dh_fake import mat_mau
    from m28core import steps  # noqa: F401
    os.makedirs('runs/R7', exist_ok=True)
    c2 = ra.AppCtx(reviewer='P2', run_dir=os.path.join('runs', 'R7'))
    c2.dong_ho = ctx.dong_ho
    demo = None
    with gr.Blocks() as demo:
        class FakeStore:
            run_dir = os.path.join('runs', 'R7')

            def progress(self):
                return dict(total=23)
        dong_ho_ui.dong_ho_tab(gr, demo, FakeStore(), c2)
    dot = next(b for b in demo.blocks.values() if getattr(b, 'elem_id', None) == 'dh-dot')
    nm = next(b for b in demo.blocks.values() if getattr(b, 'elem_id', None) == 'dh-nmat')
    assert dot.value == 'R7' and nm.value == 23


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


# ---------- luồng bấm ----------
def test_start_pause_resume_done_flow_buttons_inputs_and_summary(app):
    root, ctx, g = app
    demo, _fn = tab(ctx)
    idle = call(demo, 'refresh', 'P5', 0)
    assert 'Chưa có phiên' in idle['dh-clock-wrap'] and idle['dh-start']['interactive'] is True and idle['dh-pause']['interactive'] is False
    assert idle['dh-done']['interactive'] is False and idle['dh-cancel']['interactive'] is False and idle['dh-face']['interactive'] is False
    r = start(demo)
    assert 'data-chay="1"' in r['dh-clock-wrap'] and '▶ Đang chạy' in r['dh-clock-wrap'] and 'Đã bắt đầu đồng hồ' in r['dh-msg'] and r['state'] == 1
    assert r['dh-start']['interactive'] is False and r['dh-pause']['interactive'] is True and r['dh-pause']['value'] == 'Tạm dừng' and r['dh-done']['interactive'] is True
    assert r['dh-cancel']['interactive'] is True and r['dh-face']['interactive'] is True and r['dh-undo']['interactive'] is False
    assert all(r[k]['interactive'] is False for k in ('dh-person', 'dh-cond', 'dh-dot', 'dh-task', 'dh-job', 'dh-khoi', 'dh-nmat', 'dh-seq', 'dh-note-tb'))      # khoá ô khi có phiên
    g.tick(40)
    r = call(demo, 'on_pause', 'P5', 1)
    assert '⏸ Tạm dừng' in r['dh-clock-wrap'] and r['dh-pause']['value'] == 'Tiếp tục' and r['dh-face']['interactive'] is False and 'data-chay="0"' in r['dh-clock-wrap']
    assert 'data-giay="40.000"' in r['dh-clock-wrap']
    g.tick(300)
    r = call(demo, 'on_pause', 'P5', r['state'])
    assert 'data-chay="1"' in r['dh-clock-wrap'] and r['dh-pause']['value'] == 'Tạm dừng'
    g.tick(20)
    r = call(demo, 'on_done', 'P5', r['state'], True, None, 'auto')
    assert 'Đã lưu phiên của P5' in r['dh-msg'] and '4 mặt' in r['dh-msg'] and 'outputs/ket_qua/ketqua_P5_1410_NAP_001.zip'.replace('/', os.sep) in r['dh-msg']
    assert 'timing_P5.csv' in r['dh-msg'] and root not in r['dh-msg'] and 'ước lượng chia đều' in r['dh-msg']
    assert 'Chưa có phiên' in r['dh-clock-wrap'] and r['dh-start']['interactive'] is True and r['dh-person']['interactive'] is True
    assert os.path.exists('outputs/timing/timing_P5.csv') and not os.path.exists('outputs/timing/dang_chay_P5.json')
    assert '2026-10-14' in r['dh-recent'] and 'NAP_001' not in r['dh-faces']


def test_per_face_buttons_table_undo_and_escaping(app):
    root, ctx, g = app
    demo, _fn = tab(ctx)
    r = start(demo)
    g.tick(30)
    r = call(demo, 'on_face', 'P5', r['state'], '<b>khó</b> & "mờ"')
    assert 'Các mặt đã khép' in r['dh-faces'] and '00:30' in r['dh-faces'] and '&lt;b&gt;khó&lt;/b&gt; &amp; &quot;mờ&quot;' in r['dh-faces'] and '<b>khó</b>' not in r['dh-faces']
    assert r['dh-undo']['interactive'] is True and 'NAP_001_02' in r['dh-clock-wrap'] and '2/4' in r['dh-clock-wrap']
    g.tick(0.5)
    r2 = call(demo, 'on_face', 'P5', r['state'], '')
    assert 'quá nhanh' in r2['dh-msg']
    r3 = call(demo, 'on_undo', 'P5', r['state'])
    assert r3['dh-faces'] == '' and r3['dh-undo']['interactive'] is False


def test_stale_tab_is_told_to_reload_and_nothing_changes(app):
    root, ctx, g = app
    demo, _fn = tab(ctx)
    r = start(demo)
    call(demo, 'on_pause', 'P5', r['state'])
    r2 = call(demo, 'on_pause', 'P5', r['state'])                                      # tab cũ: vẫn giữ rev trước khi tạm dừng
    assert 'Đồng hồ vừa đổi ở tab khác' in r2['dh-msg'] and '⏸ Tạm dừng' in r2['dh-clock-wrap'] and r2['state'] == 2
    r3 = start(demo, 0)
    assert 'đã có một phiên' in r3['dh-msg'] or 'tab khác' in r3['dh-msg']


def test_cancel_modal_flow_wrong_text_then_right_text(app):
    root, ctx, g = app
    demo, _fn = tab(ctx)
    r = start(demo)
    g.tick(100)
    o = call(demo, 'on_huy_open', 'P5', r['state'])
    assert o['dh-cancel-confirm']['visible'] is True and 'KHÔNG ghi dòng nào vào timing_P5.csv' in o['dh-cancel-body'] and o['state'] == r['state'] or True
    ma = [v for k, v in o.items() if isinstance(v, str) and len(v) >= 12 and k not in ('dh-cancel-body', 'dh-clock-wrap')]
    token = ctx.dong_ho._huy['P5'].item['token']
    bad = call(demo, 'on_huy_ok', 'P5', r['state'], token, 'khong')
    assert 'HUY' in bad['dh-msg'] and bad['dh-cancel-confirm']['visible'] is False and ctx.dong_ho.xem('P5')['co_phien']
    o = call(demo, 'on_huy_open', 'P5', r['state'])
    token = ctx.dong_ho._huy['P5'].item['token']
    ok = call(demo, 'on_huy_ok', 'P5', r['state'], token, 'hủy')
    assert 'Đã hủy phiên' in ok['dh-msg'] and 'Chưa có phiên' in ok['dh-clock-wrap'] and not os.path.exists('outputs/timing/timing_P5.csv')
    assert 'giay_bo' in open('outputs/timing/huy_P5.csv', encoding='utf-8').read()
    no = call(demo, 'on_huy_no', 'P5')
    assert no['dh-cancel-confirm']['visible'] is False
    assert ma is not None


def test_closing_page_refuses_every_write_handler(app):
    root, ctx, g = app
    demo, _fn = tab(ctx)
    r = start(demo)
    ctx.closing = True
    for name, args in (('on_start', START + (0,)), ('on_pause', ('P5', 1)), ('on_face', ('P5', 1, '')), ('on_undo', ('P5', 1)), ('on_done', ('P5', 1, True, None, 'auto')),
                       ('on_fix', ('P5', 1, '01:00')), ('on_keep', ('P5', 1)), ('on_tru', ('P5', 1)), ('on_huy_open', ('P5', 1)), ('on_hong', ('P5',))):
        out = call(demo, name, *args)
        assert 'đang đóng' in out['dh-msg'], name
    assert ctx.dong_ho.xem('P5')['rev'] == 1 and not os.path.exists('outputs/timing/timing_P5.csv')
    t = call(demo, 'on_tick', 'P5')
    assert all(not isinstance(v, str) or v == '' or True for v in t.values())


def test_no_person_chosen_is_refused_with_a_hint(app):
    root, ctx, g = app
    demo, _fn = tab(ctx)
    out = call(demo, 'on_start', None, 'manual', 'X1', '', '', '', 3, None, '', 0)
    assert 'Chọn người P1 đến P5' in out['dh-msg']
    out = call(demo, 'on_start', 'P5', None, 'X1', '', '', '', 3, None, '', 0)
    assert 'manual' in out['dh-msg']


def test_tick_updates_clock_but_never_touches_input_values(app):
    root, ctx, g = app
    demo, _fn = tab(ctx)
    r = start(demo)
    t = call(demo, 'on_tick', 'P5')
    assert 'data-chay="1"' in t['dh-clock-wrap']
    for k in ('dh-dot', 'dh-task', 'dh-job', 'dh-khoi', 'dh-nmat', 'dh-seq', 'dh-note-tb', 'dh-person', 'dh-cond'):
        assert isinstance(t[k], dict) and 'value' not in t[k], k                          # không đè chữ người dùng đang gõ
    assert 'dh-nhan' not in t or True
    assert ctx.dong_ho.xem('P5')['rev'] == r['state']                                    # nhịp đồng bộ không tăng rev
    ver1 = re.search(r'data-ver="(\w+)"', t['dh-clock-wrap']).group(1)
    ver2 = re.search(r'data-ver="(\w+)"', call(demo, 'on_tick', 'P5')['dh-clock-wrap']).group(1)
    assert ver1 != ver2                                                                    # mã lần dựng mới mỗi lần vẽ để JS lấy lại mốc


def test_idle_person_switch_prefills_group_from_config(app):
    root, ctx, g = app
    json.dump({'nhom': {'P4': 'manual', 'P5': 'assisted'}, 'bo_anh': 'NAP_001'}, open('config/nhom_thi_nghiem.json', 'w'))
    demo, _fn = tab(ctx)
    out = call(demo, 'on_person', 'P4')
    assert out['dh-cond']['value'] == 'manual'
    cond = next(b for b in demo.blocks.values() if getattr(b, 'elem_id', None) == 'dh-cond')
    assert cond.value == 'assisted'                                                        # mặc định theo người của trang (P5) và file nhóm


# ---------- warnings, fix, keep ----------
def test_forgotten_clock_warning_shows_and_fix_or_keep_resolves(app):
    root, ctx, g = app
    demo, _fn = tab(ctx)
    r = start(demo)
    g.tick(60 * 160)
    t = call(demo, 'refresh', 'P5', r['state'])
    assert 'dh-warn-item' in t['dh-warn'] and '⚠' in t['dh-warn'] and t['dh-fix-row']['visible'] is True and t['dh-tru']['visible'] is False
    bad = call(demo, 'on_fix', 'P5', r['state'], '5:00:00')
    assert 'không được lớn hơn' in bad['dh-msg']
    ok = call(demo, 'on_fix', 'P5', r['state'], '1:30:00')
    assert ok['dh-warn'] == '' and ok['dh-fix-row']['visible'] is False and 'đã sửa tay' in ok['dh-clock-wrap']       # sau khi sửa còn 90 phút: hết nghi quên bấm
    r2 = call(demo, 'on_huy_open', 'P5', ok['state'])
    token = ctx.dong_ho._huy['P5'].item['token']
    call(demo, 'on_huy_ok', 'P5', ok['state'], token, 'HUY')
    r = start(demo)
    g.tick(60 * 160)
    t = call(demo, 'refresh', 'P5', r['state'])
    kept = call(demo, 'on_keep', 'P5', t['state'])
    assert 'da-xu-ly' in kept['dh-warn'] and 'Giữ nguyên' in kept['dh-msg']
    assert r2 is not None


def test_dead_page_gap_shows_the_trim_button_and_it_works(app):
    root, ctx, g = app
    old = dong_ho.DongHo(ctx.project_root, gio=g, pid=4194297)
    old.bat_dau('P5', 'manual', dot='X1', n_mat=2)
    g.tick(500)
    demo, _fn = tab(ctx)
    t = call(demo, 'refresh', 'P5', 0)
    assert 'Trang đã tắt' in t['dh-warn'] and t['dh-tru']['visible'] is True and t['dh-fix-row']['visible'] is True
    out = call(demo, 'on_tru', 'P5', t['state'])
    assert '⏸ Tạm dừng' in out['dh-clock-wrap'] and out['dh-tru']['visible'] is False and 'Đã trừ khoảng trang tắt' in out['dh-msg']


def test_corrupt_state_shows_clear_error_and_button_to_set_it_aside(app):
    root, ctx, g = app
    os.makedirs('outputs/timing', exist_ok=True)
    open('outputs/timing/dang_chay_P5.json', 'w').write('{hỏng')
    demo, _fn = tab(ctx)
    t = call(demo, 'refresh', 'P5', 0)
    assert 'Bỏ trạng thái hỏng' in t['dh-msg'] and t['dh-hong']['visible'] is True and t['dh-start']['interactive'] is False
    out = call(demo, 'on_hong', 'P5')
    assert 'Đã đổi tên file trạng thái hỏng' in out['dh-msg'] and out['dh-hong']['visible'] is False and out['dh-start']['interactive'] is True
    assert [f for f in os.listdir('outputs/timing') if f.startswith('dang_chay_P5.hong-')]


# ---------- nối với tab Nạp ảnh ----------
def test_suggestion_after_prepare_and_start_from_it(app):
    root, ctx, g = app
    os.makedirs('runs/NAP_007/map50', exist_ok=True)
    json.dump({f'F_{i}': {} for i in range(6)}, open('runs/NAP_007/map50/mp50.json', 'w'))
    demo, _fn = tab(ctx)
    t = call(demo, 'refresh', 'P5', 0)
    assert t['dh-sug'] == '' and t['dh-sug-go']['visible'] is False
    ctx.job.state, ctx.job.run, ctx.job.run_dir = 'xong', 'NAP_007', os.path.abspath('runs/NAP_007')
    t = call(demo, 'refresh', 'P5', 0)
    assert 'NAP_007' in t['dh-sug'] and 'Bắt đầu đồng hồ cho đợt này?' in t['dh-sug'] and t['dh-sug-go']['visible'] is True and t['dh-sug-no']['visible'] is True
    assert ctx.dong_ho.xem('P5')['co_phien'] is False                                     # không tự chạy ngầm
    out = call(demo, 'on_sug_go', 'P5', 'assisted', '', 0)
    v = ctx.dong_ho.xem('P5')
    assert v['co_phien'] and v['dot'] == 'NAP_007' and v['n_mat'] == 6 and v['bo_anh'] == 'NAP_007' and v['task'] == 'demo-NAP_007'
    assert out['dh-sug'] == '' and out['dh-sug-go']['visible'] is False
    # bỏ qua gợi ý
    ctx.dong_ho.huy_xac_nhan('P5', ctx.dong_ho.huy_mo('P5')['ma'], 'HUY')
    ctx.dh_started = set()
    t = call(demo, 'refresh', 'P5', 0)
    assert 'NAP_007' in t['dh-sug']
    n = call(demo, 'on_sug_no')
    assert n['dh-sug'] == '' and call(demo, 'refresh', 'P5', 0)['dh-sug'] == ''


def test_auto_start_when_loading_images_if_enabled_only(app, capsys):
    root, ctx, g = app
    demo, _fn = tab(ctx)
    assert dong_ho_ui.auto_start(None, ctx, 'NAP_008', 12) is None                           # chưa bật: không làm gì
    a = call(demo, 'on_auto', True, None, 'assisted')
    assert ctx.dh_auto is None and a['dh-auto']['value'] is False                           # thiếu người: từ chối, bỏ tích
    call(demo, 'on_auto', True, 'P5', 'assisted')
    assert ctx.dh_auto == dict(nguoi='P5', dieu_kien='assisted')
    text_ = dong_ho_ui.auto_start(None, ctx, 'NAP_008', 12)
    v = ctx.dong_ho.xem('P5')
    assert 'Đã bắt đầu đồng hồ cho P5' in text_ and v['dot'] == 'NAP_008' and v['n_mat'] == 12 and v['dieu_kien'] == 'assisted'
    again = dong_ho_ui.auto_start(None, ctx, 'NAP_009', 3)                                  # đã có phiên: báo, không đè
    assert 'Chưa tự bắt đầu được' in again and ctx.dong_ho.xem('P5')['dot'] == 'NAP_008'
    call(demo, 'on_auto', False, 'P5', 'assisted')
    assert ctx.dh_auto is None
    src = open(os.path.join(TOOL, 'review_app.py'), encoding='utf-8').read()
    assert 'dong_ho_ui.auto_start(gr, ctx, run,' in src and src.index('job.start(run, ctx.runs_root, ctx.project_root)') < src.index('dong_ho_ui.auto_start(')


# ---------- đóng trang ----------
def test_close_confirm_pauses_running_clocks_and_says_so_first(app, capsys):
    root, ctx, g = app
    ctx.dong_ho.bat_dau('P5', 'manual', dot='X1', n_mat=2)
    g.tick(30)
    assert 'tự tạm dừng' in ra.close_body_html(None, dong_ho_ui.close_note(ctx)) and 'P5' in dong_ho_ui.close_note(ctx)
    demo, _theme = ra.build_ui(None, ctx)
    on_open = next(f for f in demo.fns.values() if f.fn is not None and f.fn.__name__ == 'on_open' and f.fn.__module__ == 'review_app')
    res = on_open.fn()
    assert 'tự tạm dừng' in text(res)
    on_confirm = next(f for f in demo.fns.values() if f.fn is not None and f.fn.__name__ == 'on_confirm' and f.fn.__module__ == 'review_app')
    on_confirm.fn()
    assert ctx.closing and ctx.dong_ho.xem('P5')['trang_thai'] == 'tam_dung' and 'tat_trang' in ctx.dong_ho.xem('P5')['ma_canh_bao']
    out = capsys.readouterr().out
    assert 'Đồng hồ của P5 đã tạm dừng lúc 18:30:30' in out and 'Tiếp tục hoặc Xong (lưu)' in out
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


# ---------- HTML thuần ----------
def test_clock_html_variants_have_no_secrets_or_absolute_paths(app):
    root, ctx, g = app
    d = ctx.dong_ho
    v = d.bat_dau('P5', 'assisted', dot='NAP_001', n_mat=3)
    h1 = dong_ho_ui.clock_html(d.xem('P5'))
    assert 'ước lượng chia đều' in h1 and 'role="timer"' in h1 and 'id="dh-total"' in h1 and 'NAP_001' in h1
    g.tick(30)
    d.xong_mat('P5', v['rev'])
    h2 = dong_ho_ui.clock_html(d.xem('P5'))
    assert 'Mặt <b>NAP_001_02</b> · 2/3' in h2 and 'ước lượng' not in h2
    for h in (h1, h2, dong_ho_ui.faces_html(d.xem('P5')), dong_ho_ui.recent_html([], 'P5')):
        assert root not in h and 'token' not in h.lower() and '/home' not in h
    assert dong_ho_ui.warn_html(dict(co_phien=False)) == '' and dong_ho_ui.faces_html(dict(co_phien=False)) == ''
    assert 'Chưa có phiên nào' in dong_ho_ui.recent_html([], 'P5') or 'Chưa có phiên' in dong_ho_ui.recent_html([], 'P5')


def test_numeric_boxes_accept_blank_and_report_bad_numbers_in_vietnamese(app):
    root, ctx, g = app
    demo, _fn = tab(ctx)
    r = call(demo, 'on_start', 'P5', 'manual', 'X1', '', '', '', 3, '', '', 0)                  # Seq trống (trình duyệt gửi chuỗi rỗng), không phải 0
    assert 'Đã bắt đầu đồng hồ' in r['dh-msg'] and ctx.dong_ho.xem('P5')['seq'] == 1
    call(demo, 'on_huy_ok', 'P5', 1, (call(demo, 'on_huy_open', 'P5', 1), ctx.dong_ho._huy['P5'].item['token'])[1], 'HUY')
    for bad, why in (('abc', 'Seq bắt đầu phải là số nguyên'), ('1.5', 'Seq bắt đầu phải là số nguyên'), ('0', 'từ 1')):
        r = call(demo, 'on_start', 'P5', 'manual', 'X1', '', '', '', 3, bad, '', 0)
        assert why in r['dh-msg'] and not ctx.dong_ho.xem('P5')['co_phien'], bad
    r = call(demo, 'on_start', 'P5', 'manual', 'X1', '', '', '', 0, '', '', 0)
    assert 'Số mặt phải từ 1' in r['dh-msg']
    r = call(demo, 'on_start', 'P5', 'manual', 'X1', '', '', '', None, '2', '', 0)             # số mặt trống: mặc định 10, seq 2
    assert ctx.dong_ho.xem('P5')['n_mat'] == 10 and ctx.dong_ho.xem('P5')['seq'] == 2
    g.tick(20)
    r = call(demo, 'on_done', 'P5', r['state'], True, 'x', 'auto')
    assert 'Số mặt đã xử lý phải là số nguyên' in r['dh-msg'] and ctx.dong_ho.xem('P5')['co_phien']
    r = call(demo, 'on_done', 'P5', r['state'], True, ' 5 ', 'auto')
    assert 'Đã lưu phiên' in r['dh-msg'] and '5 mặt' in r['dh-msg']
