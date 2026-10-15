"""Kiểm thử đầu-cuối tab "Các đợt", xoá mềm, nút "Push to CVAT" và "Delete CVAT task" bằng Chromium thật (Playwright) + CVAT GIẢ. TUỲ CHỌN.

Cần playwright và Chromium (KHÔNG chạy `playwright install`), MediaPipe thật, ảnh in-cabin thật, pytest không gom file này (tên không khớp test_*.py).
Thư mục chạy (--work) có config/ (m28_config.json, map_mp50.json, face50_label.json, pipeline.json), face_landmarker.task và r_list.csv. Ví dụ:

    PYTHONPATH=$S/pwlib PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \\
        python tests/e2e_dot_push.py --work $S/work --imgs $S/incab_data/frames --shots $S/ui_shots

CVAT GIẢ: trang và tiến trình con chạy với PYTHONPATH=tests/fake_cvat (gói cvat_sdk giả giữ trạng thái trong file M28_FAKE_CVAT_STATE),
CVAT_URL=http://localhost:8080, CVAT_ACCESS_TOKEN = chuỗi giả dễ nhận. KHÔNG có CVAT thật: kết quả chỉ chứng minh logic trang và tiến trình,
không chứng minh server CVAT thật nhận định dạng nhãn/XML.

Kịch bản (một mạch): nạp 3 đợt Khoi, Nam, Cuong (prepare thật) -> thẻ đợt -> xoá mềm/khôi phục ảnh của Nam (Cancel, Esc, Delete, Restore)
-> rà đợt Khoi (có Gán tay và Bỏ) -> nút Push to CVAT (khoá khi còn mặt chưa rà; hộp xác nhận; Cancel/Esc; đẩy; thẻ kết quả; không đẩy lần hai)
-> thẻ Khoi ghi Đã đẩy CVAT, cảnh báo CVAT khi xoá ảnh -> xoá TASK trên CVAT (hộp xác nhận gõ lại tên + tick, Cancel/Esc không xoá, xoá thật
đúng một lần, đợt đẩy lại được) -> xoá cả đợt Cuong, khôi phục -> trang không có biến CVAT -> phím tắt không chạy ở tab Các đợt, bí mật không lộ.
Cổng 7881-7889, M28_NO_BROWSER=1 (CVAT_URL / CVAT_ACCESS_TOKEN lấy từ biến môi trường như trước; tab Cài đặt chỉ được kiểm là có đúng một ô password), mọi tiến trình được dọn ở finally. Ảnh chụp: <shots>/push_*.png (có mặt người thật: để ngoài git).
"""
import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import e2e_review_ui as base  # noqa: E402
from e2e_review_ui import check, log, read_csv_rows, start, stop_all, wait_port  # noqa: E402
from m28core import steps  # noqa: E402  (đã thêm tool/ vào sys.path ở e2e_review_ui): read_manual_list

TOKEN = 'TOKEN-GIA-e2e-8f3k2m9q-KHONG-PHAI-THAT'
URL = 'http://localhost:8080'
FAKE = os.path.join(CODE, 'tests', 'fake_cvat')
NOTE = 'Ảnh buổi sáng <b>camera 1</b> & "cửa vào"'


def app_env(W, state, with_cvat=True):
    env = {'PYTHONPATH': FAKE + os.pathsep + os.environ.get('PYTHONPATH', '')}
    if with_cvat:
        env.update(CVAT_URL=URL, CVAT_ACCESS_TOKEN=TOKEN, M28_FAKE_CVAT_STATE=state)
    return env


def fake_state(state):
    return json.load(open(state, encoding='utf-8')) if os.path.exists(state) else dict(tasks=[], calls=[], projects=[])


def n_calls(state, name):
    return sum(1 for c in fake_state(state)['calls'] if c['m'] == name)


def pick_images(W, imgs_dir, n):
    rows = read_csv_rows(os.path.join(W, 'r_list.csv'))[1:]
    out, seen = [], set()
    for r in rows:
        sub = r[0].split('/')[0]
        p = os.path.join(imgs_dir, *r[0].split('/'))
        if sub not in seen and os.path.exists(p):
            seen.add(sub)
            out.append(p)
        if len(out) == n:
            return out
    raise RuntimeError(f'không đủ {n} ảnh in-cabin ở {imgs_dir}')


def reset_runs(W):
    runs = os.path.join(W, 'runs')
    for n in ('Khoi', 'Nam', 'Cuong'):
        shutil.rmtree(os.path.join(runs, n), ignore_errors=True)
    trash = os.path.join(runs, '_trash')
    if os.path.isdir(trash):
        for d in os.listdir(trash):
            if re.match(r'(Khoi|Nam|Cuong)__', d):
                shutil.rmtree(os.path.join(trash, d), ignore_errors=True)


def goto_dot(pg):
    pg.get_by_role('tab', name='Các đợt').click()
    pg.wait_for_selector('#dot-root .dot-card, #dot-root .dot-detail, #dot-root .m28-empty', timeout=30000)
    pg.wait_for_timeout(300)


def card(pg, name):
    return pg.locator(f'.dot-card:has(.dot-name:text-is("{name}"))')


def wait_msg(pg, text, sel='#dot-msg', timeout=20000):
    pg.wait_for_function("([s, t]) => (document.querySelector(s)?.innerText || '').includes(t)", arg=[sel, text], timeout=timeout)


def open_grid(pg, name):
    """Mở lưới ảnh của đợt `name` (tab Các đợt nhớ chế độ xem lần trước: đang ở lưới của đợt khác thì quay về danh sách trước)."""
    if pg.locator('.dot-detail').count():
        if f'Đợt {name} ' in pg.inner_text('.dot-gridtitle').replace('\xa0', ' ') + ' ':
            pg.wait_for_selector('.dot-detail .dot-thumb', timeout=30000)
            return
        back_to_list(pg)
    card(pg, name).locator('.dot-name').click()
    pg.wait_for_selector('.dot-detail .dot-thumb', timeout=30000)
    pg.wait_for_timeout(500)


def back_to_list(pg):
    pg.click('button[data-act=back]')
    pg.wait_for_selector('#dot-root .dot-card', timeout=15000)


def thumbs(pg):
    return pg.locator('.dot-thumb').count()


def overflow(pg):
    return pg.evaluate('document.documentElement.scrollWidth - window.innerWidth')


def modal_open(pg, sel):
    pg.wait_for_selector(sel, timeout=15000)
    pg.wait_for_timeout(500)


def modal_gone(pg, sel):
    pg.wait_for_function("s => !document.querySelector(s)", arg=sel, timeout=15000)


def focus_id(pg):
    return pg.evaluate('document.activeElement && document.activeElement.id')


def inbox_file(run_dir, name):
    d = os.path.join(run_dir, 'inbox')
    for f in os.listdir(d) if os.path.isdir(d) else []:
        if os.path.splitext(f)[0] == name:
            return os.path.join(d, f)
    return None


def excluded_names(run_dir):
    p = os.path.join(run_dir, 'excluded.txt')
    if not os.path.exists(p):
        return set()
    return {ln.strip() for ln in open(p, encoding='utf-8') if ln.strip() and not ln.startswith('#')}


def tree_text(path):
    out = []
    for root, _d, files in os.walk(path):
        for fn in files:
            if fn.endswith(('.json', '.txt', '.csv', '.xml', '.log', '.md')):
                out.append((os.path.join(root, fn), open(os.path.join(root, fn), encoding='utf-8', errors='replace').read()))
    return out


def run(pw, W, imgs_dir, shots, port):
    state = os.path.join(shots, 'fake_cvat_state.json')
    runs = os.path.join(W, 'runs')
    reset_runs(W)
    if os.path.exists(state):
        os.remove(state)
    for f in ('face50_label.json', 'pipeline.json'):
        shutil.copy(os.path.join(CODE, 'config', f), os.path.join(W, 'config', f))
    imgs = pick_images(W, imgs_dir, 10)
    sets = {'Khoi': imgs[:4], 'Nam': imgs[4:7], 'Cuong': imgs[7:10]}
    out_log = os.path.join(shots, 'app_dot_push.log')
    p = start([sys.executable, os.path.join(CODE, 'tool', 'review_app.py'), '--nap', 'E2E'], W, port, app_env(W, state), out_log)
    wait_port(port, p)
    ui = base.Ui(pw, port)
    pg = ui.page
    shot = lambda n: pg.screenshot(path=os.path.join(shots, n), full_page=True)       # noqa: E731
    try:
        pg.goto(f'http://127.0.0.1:{port}/')
        pg.wait_for_selector('#tabs', timeout=30000)
        # ---------- 1. nạp ba đợt ----------
        log('\n-- 1. nạp 3 đợt Khoi, Nam, Cuong (prepare thật, mất vài chục giây) --')
        for name, files in sets.items():
            base._goto_tab(pg)
            base._drop(pg, files, len(files), 0)
            pg.fill('#nap-name textarea, #nap-name input', name)
            pg.fill('#nap-ghichu textarea', NOTE if name == 'Khoi' else f'ghi chú của {name}')
            pg.click('#nap-start')
            pg.wait_for_function("n => (document.querySelector('#nap-summary')?.innerText || '').includes('Kết quả lượt ' + n) && "
                                 "(document.querySelector('#nap-prog')?.innerText || '').includes('Xong')", arg=name, timeout=300000)
            dj = json.load(open(os.path.join(runs, name, 'dot.json'), encoding='utf-8'))
            check(dj['ten'] == name and dj['so_anh'] == len(files) and dj['nguoi_nap'] == 'E2E' and dj['ghi_chu'].startswith(('Ảnh buổi', 'ghi chú')),
                  f'{name}: dot.json ghi tên, số ảnh, người nạp, ghi chú ({dj["ghi_chu"][:30]!r})')
            check(os.path.isdir(os.path.join(runs, name, 'inbox')) and os.path.exists(os.path.join(runs, name, 'flags', 'flags.json')),
                  f'{name}: prepare xong (inbox + flags.json)')
        # ---------- 2. tab Các đợt ----------
        log('\n-- 2. tab Các đợt: thẻ đợt --')
        goto_dot(pg)
        for name, files in sets.items():
            c = card(pg, name)
            check(c.count() == 1, f'có thẻ {name}')
            txt = c.inner_text()
            check(f'{len(files)} ảnh' in txt and 'người nạp E2E' in txt, f'thẻ {name} ghi {len(files)} ảnh và người nạp: {txt[:80]!r}')
        kt = card(pg, 'Khoi').inner_text()
        check('Ảnh buổi sáng <b>camera 1</b>' in kt and card(pg, 'Khoi').locator('.dot-note b').count() == 0, 'ghi chú hiện đúng chữ, HTML bị escape')
        check('Chưa rà' in kt and 'Review batch' in kt, f'Khoi chưa rà: {kt!r}')
        check(overflow(pg) <= 0, f'1440 px: không cuộn ngang ({overflow(pg)})')
        shot('push_dots_desktop.png')
        pg.set_viewport_size({'width': 420, 'height': 900})
        pg.wait_for_timeout(500)
        check(overflow(pg) <= 1, f'420 px: không cuộn ngang ({overflow(pg)})')
        shot('push_dots_narrow.png')
        pg.set_viewport_size({'width': 1440, 'height': 900})
        pg.wait_for_timeout(300)
        # ---------- 3. xoá mềm ảnh của Nam ----------
        log('\n-- 3. xoá mềm / khôi phục ảnh của Nam --')
        nam = os.path.join(runs, 'Nam')
        open_grid(pg, 'Nam')
        n0 = thumbs(pg)
        check(n0 == 3, f'Nam có {n0} ảnh trong lưới')
        t0 = pg.locator('.dot-thumb').first
        name0 = t0.locator('img').get_attribute('alt')
        check(not any('inbox' in (s or '') or s.startswith('/gradio_api/file=') for s in pg.eval_on_selector_all('.dot-thumb img', 'e => e.map(x => x.src.slice(0, 60))')),
              'ảnh nhỏ nhúng data URI, không phát file inbox')
        op = pg.evaluate("el => getComputedStyle(el).opacity", t0.locator('.dot-trash').element_handle())
        t0.hover()
        pg.wait_for_timeout(400)
        op2 = pg.evaluate("el => getComputedStyle(el).opacity", t0.locator('.dot-trash').element_handle())
        check(float(op) < 0.5 and float(op2) > 0.9, f'nút thùng rác chỉ hiện khi rê chuột (opacity {op} -> {op2})')
        check(t0.locator('.dot-trash').get_attribute('aria-label') == f'Delete image {name0}', 'nút thùng rác có aria-label')
        shot('push_trash_hover.png')
        # Cancel
        t0.locator('.dot-trash').click()
        modal_open(pg, '#dot-modal')
        check(pg.get_attribute('#dot-modal', 'role') == 'dialog' and pg.get_attribute('#dot-modal', 'aria-modal') == 'true', 'modal role=dialog aria-modal=true')
        check(focus_id(pg) == 'dot-modal-cancel', f'nút Cancel có focus khi hộp mở (focus: {focus_id(pg)!r})')
        mt = pg.inner_text('#dot-modal')
        check(name0 in mt and 'Tên gốc' in mt and 'Nam' in mt and 'Quyết định hiện tại' in mt and 'khôi phục được' in mt, f'modal nêu ảnh, đợt, quyết định, hậu quả: {mt[:120]!r}')
        shot('push_delete_modal.png')
        pg.click('#dot-modal-cancel')
        modal_gone(pg, '#dot-modal')
        check(thumbs(pg) == n0 and inbox_file(nam, name0) is not None and not os.path.exists(os.path.join(nam, 'excluded.txt')), 'Cancel: ảnh còn nguyên')
        # Esc
        t0.hover()
        t0.locator('.dot-trash').click()
        modal_open(pg, '#dot-modal')
        pg.keyboard.press('Escape')
        modal_gone(pg, '#dot-modal')
        check(thumbs(pg) == n0 and not os.path.exists(os.path.join(nam, 'excluded.txt')), 'Esc: ảnh còn nguyên, chưa có excluded.txt')
        # Enter khi focus ở Cancel không xoá
        t0.hover()
        t0.locator('.dot-trash').click()
        modal_open(pg, '#dot-modal')
        pg.keyboard.press('Enter')
        modal_gone(pg, '#dot-modal')
        check(thumbs(pg) == n0 and not os.path.exists(os.path.join(nam, 'excluded.txt')), 'Enter khi focus ở Cancel: không xoá')
        before = {f: base._sha(os.path.join(nam, *f.split('/'))) for f in (os.path.relpath(inbox_file(nam, name0), nam).replace(os.sep, '/'),
                                                                          'crop/images/%s.png' % name0, 'overlays/%s.png' % name0)
                  if os.path.exists(os.path.join(nam, *f.split('/')))}
        check(len(before) >= 2, f'ghi nhớ sha256 của các file ảnh trước khi xoá: {sorted(before)}')
        # Xoá
        t0.hover()
        t0.locator('.dot-trash').click()
        modal_open(pg, '#dot-modal')
        pg.click('#dot-modal-ok')
        modal_gone(pg, '#dot-modal')
        pg.wait_for_function("n => document.querySelectorAll('.dot-thumb').length === n", arg=n0 - 1, timeout=15000)
        tr = [d for d in os.listdir(os.path.join(nam, '_trash'))]
        check(name0 in excluded_names(nam) and len(tr) == 1 and os.path.exists(os.path.join(nam, '_trash', tr[0], 'manifest.json')),
              f'Xoá: tên trong excluded.txt, file ở _trash/{tr}')
        check(inbox_file(nam, name0) is None and not os.path.exists(os.path.join(nam, 'overlays', name0 + '.png')), 'file ảnh đã rời inbox và overlays')
        check('Thùng rác của đợt (1)' in pg.inner_text('.dot-detail') and pg.locator('button[data-act=restore]').count() == 1, 'khu Thùng rác liệt kê 1 ảnh')
        back_to_list(pg)
        check('1 ảnh trong thùng rác' in card(pg, 'Nam').inner_text() and '<b>2</b> ảnh' in card(pg, 'Nam').inner_html(),
              'thẻ Nam: còn 2 ảnh, 1 ảnh trong thùng rác')
        open_grid(pg, 'Nam')
        pg.click('button[data-act=restore]')
        pg.wait_for_function("n => document.querySelectorAll('.dot-thumb').length === n", arg=n0, timeout=15000)
        check(name0 not in excluded_names(nam), 'Restore: tên gỡ khỏi excluded.txt')
        after = {f: base._sha(os.path.join(nam, *f.split('/'))) for f in before}
        check(after == before, 'Restore: file trở lại đúng chỗ, đúng nội dung (sha256 khớp)')
        check(not os.listdir(os.path.join(nam, '_trash')), 'thùng rác của Nam trống sau khi khôi phục')
        # dọn thùng rác qua modal
        t0.hover()
        t0.locator('.dot-trash').click()
        modal_open(pg, '#dot-modal')
        pg.click('#dot-modal-ok')
        pg.wait_for_function("n => document.querySelectorAll('.dot-thumb').length === n", arg=n0 - 1, timeout=15000)
        pg.click('button[data-act=empty]')
        modal_open(pg, '#dot-modal')
        check('KHÔNG khôi phục được' in pg.inner_text('#dot-modal'), 'modal dọn thùng rác nói rõ không khôi phục được')
        pg.keyboard.press('Escape')
        modal_gone(pg, '#dot-modal')
        check(len(os.listdir(os.path.join(nam, '_trash'))) == 1, 'Esc ở modal dọn: thùng rác còn')
        pg.click('button[data-act=empty]')
        modal_open(pg, '#dot-modal')
        pg.click('#dot-modal-ok')
        pg.wait_for_function("() => (document.querySelector('.dot-detail')?.innerText || '').includes('Trống')", timeout=15000)
        check(not os.path.exists(os.path.join(nam, '_trash')) and name0 in excluded_names(nam), 'Dọn: _trash đã xoá vĩnh viễn, tên vẫn nằm trong excluded.txt')
        back_to_list(pg)
        # ---------- 4. rà đợt Khoi ----------
        log('\n-- 4. rà đợt Khoi --')
        # Một mặt của Khoi giả làm "MediaPipe không thấy mặt" (bỏ khỏi mp50.json/flags.json, thêm vào no_face.csv, còn ảnh cắt):
        # mặt này chỉ chọn được Gán tay, và lên CVAT là ảnh trống; ba mặt còn lại có nháp.
        kr = os.path.join(runs, 'Khoi')
        no_draft = sorted(json.load(open(os.path.join(kr, 'crop', 'meta.json'), encoding='utf-8')))[-1]
        for sub, fn in (('map50', 'mp50.json'), ('flags', 'flags.json')):
            pth = os.path.join(kr, sub, fn)
            dd = json.load(open(pth, encoding='utf-8'))
            dd.pop(no_draft)
            json.dump(dd, open(pth, 'w', encoding='utf-8'))
        with open(os.path.join(kr, 'no_face.csv'), 'a', encoding='utf-8', newline='') as f:
            f.write(f'{no_draft},khong_thay_mat,mediapipe\n')
        card(pg, 'Khoi').locator('button[data-act=ra]').click()
        pg.wait_for_function("document.title === 'Rà soát M28 · Khoi'", timeout=60000)
        pg.wait_for_selector('#info .face-name', timeout=60000)
        pg.wait_for_function("() => { const i = document.querySelector('#big img'); return i && i.complete && i.naturalWidth > 0; }", timeout=30000)
        ui.page = pg
        pg.wait_for_selector('#btn-push', timeout=30000)
        n_faces = ui.progress()[1]
        check(n_faces == 4, f'Khoi có {n_faces} mặt trong hàng đợi')
        check(pg.locator('#btn-push').is_disabled(), 'còn mặt chưa rà: nút Push to CVAT khoá')
        pg.wait_for_function("(document.querySelector('#push-panel')?.innerText || '').includes('chưa rà')", timeout=15000)
        check(f'Còn {n_faces} mặt chưa rà' in pg.inner_text('#push-panel'), f'lý do khoá: {pg.inner_text("#push-panel")!r}')
        draft_keys = iter(['g', 'b', 'n', 'n'])                  # mặt có nháp: Gán tay (có nháp), Bỏ, Nhận; mặt không có nháp: Gán tay (ảnh trống)
        shot_nd = False
        for i in range(n_faces):
            if 'không có nháp' in pg.inner_text('#info'):
                k = 'g'
                if not shot_nd:
                    check('Gán tay mặt này lên CVAT là ảnh trống' in pg.inner_text('#info'), 'mặt không có nháp: cảnh báo ghi rõ Gán tay là ảnh trống')
                    shot('gantay_khong_nhap.png')
                    shot_nd = True
            else:
                k = next(draft_keys)
            pg.keyboard.press(k)
            ui.wait_done(i + 1)
            if i == 0:
                pg.wait_for_function("(document.querySelector('#push-panel')?.innerText || '').includes('Còn 3 mặt')", timeout=15000)
        pg.wait_for_function("() => { const b = document.querySelector('#btn-push'); return !!b && !b.disabled; }", timeout=20000)
        tri = read_csv_rows(os.path.join(runs, 'Khoi', 'review', 'triage_E2E.csv'))
        decs = [r[1] for r in tri[1:]]
        check('gan_tay' in decs and 'bo' in decs, f'đã rà hết, có Gán tay và Bỏ: {decs}')
        n_nhan, n_tay, n_bo = decs.count('nhan'), decs.count('gan_tay'), decs.count('bo')
        check(shot_nd and n_tay == 2 and n_nhan == 1 and n_bo == 1, f'Khoi: 1 Nhận, 2 Gán tay (1 có nháp, 1 ảnh trống), 1 Bỏ: {decs}')
        shot('gantay_guide.png')
        # bấm Xong TRƯỚC khi đẩy: trang tải lại một lần, vẫn còn server, Push to CVAT và tab Các đợt dùng được sau Xong
        base.click_xong(ui)
        check(os.path.exists(os.path.join(runs, 'Khoi', 'review', 'done.txt')), 'Khoi: bấm Xong ghi review/done.txt')
        pg.wait_for_function("() => { const b = document.querySelector('#btn-push'); return !!b && !b.disabled; }", timeout=20000)
        check(pg.locator('#btn-push').is_enabled(), 'sau Xong: nút Push to CVAT vẫn bật')
        pg.get_by_role('tab', name='Các đợt').click()
        pg.wait_for_selector('#dot-root .dot-card', timeout=15000)
        check(card(pg, 'Khoi').count() == 1 and pg.locator('#progress .m28-done-bar').is_visible(), 'sau Xong: tab Các đợt mở được, dải xanh còn ở đầu trang')
        pg.get_by_role('tab', name='Rà soát').click()
        pg.wait_for_selector('#btn-push', timeout=15000)
        # phím tắt không chạy khi hộp xác nhận đang mở
        # ---------- 5. đẩy lên CVAT ----------
        log('\n-- 5. đẩy lên CVAT (CVAT giả) --')
        pg.click('#btn-push')
        modal_open(pg, '#push-confirm')
        check(pg.get_attribute('#push-confirm', 'role') == 'dialog' and pg.get_attribute('#push-confirm', 'aria-modal') == 'true', 'hộp xác nhận role=dialog')
        check(focus_id(pg) == 'push-confirm-cancel', f'nút Cancel là mặc định có focus ({focus_id(pg)!r})')
        ct = pg.inner_text('#push-confirm')
        for want in ('demo-Khoi', URL, 'Không đụng task m28-', 'MỚI'):
            check(want in ct, f'hộp xác nhận có {want!r}')
        rows = dict(pg.evaluate("Array.from(document.querySelectorAll('#push-confirm table tr')).map(r => [r.querySelector('th').innerText, "
                                "r.querySelector('td').innerText])"))
        nums = [int(next(v for k, v in rows.items() if k.startswith(w)).split()[0]) for w in ('Mặt Nhận', 'Mặt Gán tay', 'Mặt Bỏ')]
        check(nums == [n_nhan, n_tay, n_bo], f'hộp xác nhận đúng số Nhận/Gán tay/Bỏ {nums} == {[n_nhan, n_tay, n_bo]}')
        gt = next(v for k, v in rows.items() if k.startswith('Mặt Gán tay'))
        check('1 có nháp' in gt and 'low_conf' in gt and '1 ảnh trống' in gt, f'hộp xác nhận tách Gán tay có nháp / ảnh trống: {gt!r}')
        shot('gantay_confirm.png')
        check(int(rows['Số job dự kiến'].split()[0]) == (1 if n_nhan else 0) + (1 if n_tay else 0), f'hộp xác nhận ghi số job dự kiến: {rows["Số job dự kiến"]!r}')
        shot('push_confirm.png')
        before_csv = open(os.path.join(runs, 'Khoi', 'review', 'triage_E2E.csv'), encoding='utf-8').read()
        pg.keyboard.press('n')                                   # modal mở: phím tắt không tác dụng
        pg.keyboard.press('g')
        pg.wait_for_timeout(500)
        check(open(os.path.join(runs, 'Khoi', 'review', 'triage_E2E.csv'), encoding='utf-8').read() == before_csv, 'modal mở: phím N/G không ghi gì')
        pg.keyboard.press('Escape')
        modal_gone(pg, '#push-confirm')
        check(not fake_state(state)['tasks'] and not os.path.exists(os.path.join(runs, 'Khoi', 'push.json')), 'Esc: chưa đẩy gì')
        pg.click('#btn-push')
        modal_open(pg, '#push-confirm')
        pg.click('#push-confirm-cancel')
        modal_gone(pg, '#push-confirm')
        check(not fake_state(state)['tasks'], 'Cancel: chưa đẩy gì')
        pg.click('#btn-push')
        modal_open(pg, '#push-confirm')
        pg.click('#push-confirm-ok')
        modal_gone(pg, '#push-confirm')
        pg.wait_for_selector('#push-prog .nap-prog', timeout=15000)
        pg.click('#btn-dong')                                    # đang đẩy: Đóng bị từ chối (nếu CVAT giả chưa kịp xong)
        pg.wait_for_timeout(700)
        if pg.locator('#push-cancel').is_visible():
            pg.wait_for_function("(document.querySelector('#close-msg')?.innerText || '').includes('Đang đẩy lượt Khoi')", timeout=10000)
            check(not pg.locator('#close-confirm').is_visible() and p.poll() is None, 'đang đẩy lên CVAT: Đóng bị từ chối, không mở hộp')
        else:
            if pg.locator('#close-confirm').is_visible():
                pg.click('#close-confirm-cancel')
                modal_gone(pg, '#close-confirm')
            log('  ...  push xong quá nhanh: không bắt được lúc đang chạy (logic từ chối được kiểm bằng pytest test_close_check_refuses_while_jobs_run_or_switching)')
        pg.wait_for_selector('#push-panel .push-done', timeout=180000)
        check(pg.locator('#btn-push').is_hidden(), 'sau khi đẩy: nút Đẩy ẩn, thẻ kết quả thay vào')
        ps = json.load(open(os.path.join(runs, 'Khoi', 'push.json'), encoding='utf-8'))
        check(ps['trang_thai'] == 'xong' and ps['task'] == 'demo-Khoi' and ps['check']['ok'], f'push.json xong: {ps["trang_thai"]}')
        st = fake_state(state)
        check([t['name'] for t in st['tasks']] == ['demo-Khoi'], f'CVAT giả có đúng một task demo-Khoi: {[t["name"] for t in st["tasks"]]}')
        check(n_calls(state, 'tasks.create_from_data') == 1 and n_calls(state, 'Task.import_annotations') == 1, 'đúng một lần tạo task, đúng một lần nhập nhãn')
        card_txt = pg.inner_text('#push-panel')
        check('1 có nháp' in card_txt and '1 ảnh trống' in card_txt and 'Gán tay có nháp: 1/1' in card_txt, f'thẻ kết quả tách Gán tay: {card_txt[:300]!r}')
        shot('gantay_ket_qua.png')
        check(ps['phien_ban'] == 2 and ps['so_anh'] == dict(nhan=1, gan_tay=2, gan_tay_co_nhap=1, gan_tay_trong=1) and len(ps['gan_tay_co_nhap']) == 1,
              f'push.json bản 2 ghi so_anh và gan_tay_co_nhap: {ps["so_anh"]} {ps["gan_tay_co_nhap"]}')
        ml = steps.read_manual_list(os.path.join(runs, 'Khoi', 'push', 'manual_list.txt'))
        check([k for _n, k in ml] == ['co_nhap', 'anh_trong'] and [n for n, k in ml if k == 'co_nhap'] == ps['gan_tay_co_nhap'],
              f'manual_list.txt ghi đúng loại (có nháp trước): {ml}')
        ann = st['tasks'][0]['annotations']['by_name']
        ten_trong = [n for n, k in ml if k == 'anh_trong'][0]
        ten_nhap = ps['gan_tay_co_nhap'][0]
        check(ten_trong not in ann and len(ann[ten_nhap]) == 1 and len(ann[ten_nhap][0]['points']) == 50 and
              all(pt['low_conf'] == 'true' for pt in ann[ten_nhap][0]['points']),
              'CVAT giả: Gán tay có nháp có 50 điểm toàn low_conf true; Gán tay ảnh trống không có nhãn')
        check(len(ann) == 2, f'CVAT giả: chỉ 2 ảnh có nhãn (1 Nhận + 1 Gán tay có nháp): {sorted(ann)}')
        check(re.search(r'\tpush\t\w+\t[\d.]+s\tgan_tay co_nhap=1 anh_trong=1', open(os.path.join(runs, 'Khoi', 'log.txt'), encoding='utf-8').read()) is not None,
              'log.txt ghi chi tiết bước push: gan_tay co_nhap=1 anh_trong=1')
        link = pg.locator('#push-panel a.push-link')
        check(link.get_attribute('href') == f'{URL}/tasks/{ps["task_id"]}' and link.get_attribute('target') == '_blank' and 'noopener' in link.get_attribute('rel'),
              'thẻ kết quả có link CVAT mở tab mới, rel=noopener')
        jobs_expect = -(-n_nhan // 8) + (1 if n_tay else 0)
        check(f'{jobs_expect} ({-(-n_nhan // 8)} Nhận, {1 if n_tay else 0} Gán tay)' in card_txt.replace('\n', ' '), f'thẻ ghi số job: {card_txt[:200]!r}')
        check(os.path.exists(os.path.join(runs, 'Khoi', 'push', 'done.txt')) and os.path.getsize(os.path.join(runs, 'Khoi', 'push_log.txt')) > 0,
              'push/done.txt và push_log.txt có mặt')
        shot('push_done.png')
        r2 = subprocess.run([sys.executable, os.path.join(CODE, 'tool', 'm28.py'), 'push', '--run', 'Khoi', '--reviewer', 'E2E', '--task', 'demo-Khoi'], cwd=W,
                            env=dict(os.environ, **app_env(W, state)), capture_output=True, text=True, encoding='utf-8')
        check(r2.returncode == 0 and 'bỏ qua push' in r2.stdout, 'chạy lại m28.py push từ cmd: "bỏ qua push"')
        r3 = subprocess.run([sys.executable, os.path.join(CODE, 'tool', 'm28.py'), 'push', '--run', 'Khoi', '--reviewer', 'E2E', '--task', 'demo-Khoi',
                             '--force', 'push'], cwd=W, env=dict(os.environ, **app_env(W, state)), capture_output=True, text=True, encoding='utf-8')
        check(r3.returncode != 0 and 'đã đẩy lên CVAT' in r3.stderr and n_calls(state, 'tasks.create_from_data') == 1, 'ép chạy lại push: bị từ chối, không tạo task thứ hai')
        # ---------- 6. thẻ Khoi, cảnh báo CVAT, Rà soát khi xoá ảnh ----------
        log('\n-- 6. thẻ Khoi sau khi đẩy; xoá ảnh của đợt đang rà --')
        goto_dot(pg)
        kt = card(pg, 'Khoi').inner_text()
        check('Đã đẩy CVAT: demo-Khoi' in kt and 'đang mở' in kt, f'thẻ Khoi: {kt[:120]!r}')
        check(card(pg, 'Khoi').locator('button[data-act=push]').count() == 0, 'đợt đã đẩy: không còn nút Đẩy trên thẻ')
        check(card(pg, 'Khoi').locator('button[data-act=ra]').is_disabled(), 'đợt đang mở: nút Review batch khoá')
        open_grid(pg, 'Khoi')
        check('Đã đẩy lên CVAT' in pg.inner_text('.dot-cvat') and 'Delete CVAT task' in pg.inner_text('.dot-cvat'), 'khu CVAT của đợt có link và nút Delete CVAT task')
        check(pg.locator('button[data-act=delrun]').is_disabled(), 'đợt đang rà: không xoá cả đợt')
        t0 = pg.locator('.dot-thumb').first
        keep_name = t0.locator('img').get_attribute('alt')
        t0.hover()
        t0.locator('.dot-trash').click()
        modal_open(pg, '#dot-modal')
        mt = pg.inner_text('#dot-modal')
        check('KHÔNG xoá ảnh trong task demo-Khoi' in mt, f'cảnh báo CVAT khi xoá ảnh của đợt đã đẩy: {mt[:200]!r}')
        shot('push_delete_modal_cvat.png')
        pg.click('#dot-modal-ok')
        modal_gone(pg, '#dot-modal')
        pg.wait_for_function("n => document.querySelectorAll('.dot-thumb').length === n", arg=3, timeout=15000)
        pg.get_by_role('tab', name='Rà soát').click()
        pg.wait_for_function("() => { const m = /Đã rà (\\d+)\\/(\\d+)/.exec(document.querySelector('#progress').innerText); return m && +m[2] === 3; }", timeout=20000)
        check(keep_name not in pg.inner_text('#info'), 'Rà soát vẽ lại: mặt đã xoá không còn')
        check(ui.progress()[1] == 3, f'#progress: còn 3 mặt trong hàng đợi ({ui.progress()})')
        goto_dot(pg)
        open_grid(pg, 'Khoi')
        pg.click('button[data-act=restore]')
        pg.wait_for_function("n => document.querySelectorAll('.dot-thumb').length === n", arg=4, timeout=15000)
        pg.get_by_role('tab', name='Rà soát').click()
        pg.wait_for_function("() => { const m = /Đã rà (\\d+)\\/(\\d+)/.exec(document.querySelector('#progress').innerText); return m && +m[2] === 4; }", timeout=20000)
        check(ui.progress()[1] == 4 and ui.progress()[0] == 4, f'khôi phục ảnh có quyết định: lại 4/4 ({ui.progress()})')
        # ---------- 7. xoá task trên CVAT ----------
        log('\n-- 7. xoá task trên CVAT (chính sách mạnh) --')
        goto_dot(pg)
        open_grid(pg, 'Khoi')
        task_id = ps['task_id']
        pg.click('button[data-act=deltask]')
        modal_open(pg, '#dot-modal')
        mt = pg.inner_text('#dot-modal')
        for want in ('KHÔNG HOÀN TÁC', 'nhãn đã sửa', 'collect', 'demo-Khoi', f'id {task_id}'):
            check(want in mt, f'modal xoá task có {want!r}')
        check(focus_id(pg) == 'dot-modal-cancel', 'nút Cancel là mặc định có focus')
        check(pg.locator('#dot-modal-ok').is_disabled(), 'chưa gõ tên, chưa tick: nút xoá khoá')
        pg.fill('#dot-modal-typed textarea, #dot-modal-typed input', 'demo-khoi')
        pg.wait_for_timeout(400)
        check(pg.locator('#dot-modal-ok').is_disabled(), 'gõ sai hoa thường: nút xoá khoá')
        pg.fill('#dot-modal-typed textarea, #dot-modal-typed input', 'demo-Khoi')
        pg.wait_for_timeout(400)
        check(pg.locator('#dot-modal-ok').is_disabled(), 'gõ đúng nhưng chưa tick: nút xoá khoá')
        pg.check('#dot-modal-check input')
        pg.wait_for_function("!document.querySelector('#dot-modal-ok').disabled", timeout=10000)
        shot('push_delete_task_modal.png')
        pg.fill('#dot-modal-typed textarea, #dot-modal-typed input', 'demo-Khoi ')
        pg.wait_for_timeout(400)
        check(pg.locator('#dot-modal-ok').is_disabled(), 'thêm dấu cách: nút xoá lại khoá')
        pg.keyboard.press('Escape')
        modal_gone(pg, '#dot-modal')
        check(len(fake_state(state)['tasks']) == 1 and n_calls(state, 'Task.remove') == 0, 'Esc: task còn nguyên, chưa gọi xoá')
        pg.click('button[data-act=deltask]')
        modal_open(pg, '#dot-modal')
        pg.click('#dot-modal-cancel')
        modal_gone(pg, '#dot-modal')
        check(n_calls(state, 'Task.remove') == 0, 'Cancel: chưa gọi xoá')
        pg.click('button[data-act=deltask]')
        modal_open(pg, '#dot-modal')
        pg.fill('#dot-modal-typed textarea, #dot-modal-typed input', 'demo-Khoi')
        pg.check('#dot-modal-check input')
        pg.wait_for_function("!document.querySelector('#dot-modal-ok').disabled", timeout=10000)
        pg.click('#dot-modal-ok')
        modal_gone(pg, '#dot-modal')
        pg.wait_for_function("() => (document.querySelector('#dot-job')?.innerText || '').includes('Xoá task')", timeout=20000)
        t = time.time()
        while time.time() - t < 120 and json.load(open(os.path.join(runs, 'Khoi', 'push.json'), encoding='utf-8')).get('trang_thai') != 'task_deleted':
            time.sleep(0.5)
        ps2 = json.load(open(os.path.join(runs, 'Khoi', 'push.json'), encoding='utf-8'))
        check(ps2['trang_thai'] == 'task_deleted' and ps2['task_id'] == task_id, f'push.json đánh dấu task_deleted: {ps2["trang_thai"]}')
        st = fake_state(state)
        check(st['tasks'] == [] and n_calls(state, 'Task.remove') == 1, 'CVAT giả: task đã xoá, đúng một lần gọi xoá')
        rm_idx = [i for i, c in enumerate(st['calls']) if c['m'] == 'Task.remove'][0]
        check(any(c['m'] == 'tasks.retrieve' and c['args'] == [task_id] for c in st['calls'][:rm_idx]), 'trước khi xoá đã lấy lại task theo id từ CVAT')
        check(all(c['m'] != 'tasks.remove_by_ids' for c in st['calls']), 'không dùng xoá hàng loạt theo danh sách')
        check('xoa_task' in open(os.path.join(runs, 'Khoi', 'log.txt'), encoding='utf-8').read(), 'đã ghi vào log.txt (xoa_task)')
        check('Đã xoá task demo-Khoi' in open(os.path.join(runs, 'Khoi', 'push_log.txt'), encoding='utf-8').read(), 'đã ghi vào push_log.txt')
        check(not os.path.exists(os.path.join(runs, 'Khoi', 'push', 'done.txt')), 'push/done.txt đã gỡ: đẩy lại được')
        pg.wait_for_function("() => (document.querySelector('#dot-job')?.innerText || '').includes('Xong')", timeout=30000)
        goto_dot(pg)
        if pg.locator('.dot-detail').count():
            pg.wait_for_function("() => (document.querySelector('.dot-cvat')?.innerText || '').includes('đã được xoá')", timeout=20000)
            check('Đẩy lại được' in pg.inner_text('.dot-cvat') or 'đẩy lại được' in pg.inner_text('.dot-cvat'), 'khu CVAT của đợt ghi task đã xoá, đợt đẩy lại được')
            back_to_list(pg)
        check('task trên CVAT đã xoá, đẩy lại được' in card(pg, 'Khoi').inner_text(), 'thẻ Khoi ghi task đã xoá, đẩy lại được')
        pg.get_by_role('tab', name='Rà soát').click()
        pg.wait_for_function("() => { const b = document.querySelector('#btn-push'); return !!b && !b.disabled; }", timeout=30000)
        check(pg.locator('#btn-push').is_visible(), 'sau khi xoá task: nút Push to CVAT lại bật')
        # đẩy lại một lần để chứng minh đợt đẩy lại được
        pg.click('#btn-push')
        modal_open(pg, '#push-confirm')
        pg.click('#push-confirm-ok')
        pg.wait_for_selector('#push-panel .push-done', timeout=180000)
        st = fake_state(state)
        check([t['name'] for t in st['tasks']] == ['demo-Khoi'] and n_calls(state, 'tasks.create_from_data') == 2, 'đẩy lại sau khi xoá task: tạo task mới')
        ps3 = json.load(open(os.path.join(runs, 'Khoi', 'push.json'), encoding='utf-8'))
        check(ps3['trang_thai'] == 'xong' and ps3['truoc_do'][0]['task_id'] == task_id, 'push.json mới giữ lịch sử task đã xoá (truoc_do)')
        # ---------- 8. xoá cả đợt Cuong ----------
        log('\n-- 8. xoá cả đợt Cuong (xoá mềm) --')
        goto_dot(pg)
        open_grid(pg, 'Cuong')
        pg.click('button[data-act=delrun]')
        modal_open(pg, '#dot-modal')
        check(pg.locator('#dot-modal-ok').is_disabled() and pg.locator('#dot-modal-typed').count() == 1, 'xoá cả đợt: phải gõ tên, nút khoá')
        pg.fill('#dot-modal-typed textarea, #dot-modal-typed input', 'cuong')
        pg.wait_for_timeout(400)
        check(pg.locator('#dot-modal-ok').is_disabled(), 'gõ sai hoa thường: nút khoá')
        pg.fill('#dot-modal-typed textarea, #dot-modal-typed input', 'Cuong')
        pg.wait_for_function("!document.querySelector('#dot-modal-ok').disabled", timeout=10000)
        pg.click('#dot-modal-ok')
        modal_gone(pg, '#dot-modal')
        pg.wait_for_selector('#dot-root .dot-card', timeout=15000)
        check(card(pg, 'Cuong').count() == 0 and not os.path.exists(os.path.join(runs, 'Cuong')) and
              any(d.startswith('Cuong__') for d in os.listdir(os.path.join(runs, '_trash'))), 'đợt Cuong chuyển vào runs/_trash (xoá mềm)')
        check('Đợt đã xoá' in pg.inner_text('#dot-root') and 'Cuong' in pg.inner_text('.dot-del-row'), 'khu Đợt đã xoá liệt kê Cuong')
        shot('push_deleted_runs.png')
        pg.click('button[data-act=restore_run]')
        pg.wait_for_function("() => !!document.querySelector('.dot-card .dot-name') && "
                             "Array.from(document.querySelectorAll('.dot-name')).some(e => e.textContent.trim() === 'Cuong')", timeout=15000)
        check(os.path.isdir(os.path.join(runs, 'Cuong', 'inbox')), 'khôi phục đợt Cuong về runs/Cuong')
        # ---------- 9. phím tắt ở tab Các đợt, màn hẹp ----------
        log('\n-- 9. phím tắt, màn hẹp --')
        csv_before = open(os.path.join(runs, 'Khoi', 'review', 'triage_E2E.csv'), encoding='utf-8').read()
        pg.locator('#dot-root').click(position={'x': 5, 'y': 5})
        for k in ('n', 'g', 'b', 'z', 'ArrowLeft', '0', '3'):
            pg.keyboard.press(k)
        pg.wait_for_timeout(800)
        check(open(os.path.join(runs, 'Khoi', 'review', 'triage_E2E.csv'), encoding='utf-8').read() == csv_before, 'tab Các đợt: phím N/G/B/Z/←/0-8 không ghi gì vào triage')
        pg.set_viewport_size({'width': 420, 'height': 900})
        pg.wait_for_timeout(400)
        open_grid(pg, 'Nam')
        check(overflow(pg) <= 1, f'420 px: lưới ảnh không cuộn ngang ({overflow(pg)})')
        pg.locator('.dot-thumb').first.locator('.dot-trash').click()
        modal_open(pg, '#dot-modal')
        box = pg.locator('#dot-modal .m28-modal-box').bounding_box()
        check(box['x'] >= 0 and box['x'] + box['width'] <= 420 and box['y'] >= 0 and box['y'] + box['height'] <= 900, f'420 px: modal vừa màn hình {box}')
        shot('push_modal_narrow.png')
        pg.keyboard.press('Escape')
        modal_gone(pg, '#dot-modal')
        pg.get_by_role('tab', name='Rà soát').click()
        pg.wait_for_selector('#push-panel .push-done', timeout=20000)
        check(overflow(pg) <= 1, f'420 px: tab Rà soát có khung Đẩy không cuộn ngang ({overflow(pg)})')
        shot('push_review_narrow.png')
        shot('gantay_hep.png')
        pg.set_viewport_size({'width': 1440, 'height': 900})
        pg.wait_for_timeout(300)
        # ---------- 10. bí mật, mạng ----------
        log('\n-- 10. token không lộ, không gọi ra ngoài --')
        html_all = pg.content()
        check(TOKEN not in html_all, 'token giả không có trong HTML trang')
        leaks = [f for f, t in tree_text(os.path.join(runs, 'Khoi')) + tree_text(os.path.join(runs, 'Nam')) + [(out_log, open(out_log, encoding='utf-8').read())]
                 if TOKEN in t]
        check(not leaks, f'token giả không có trong push.json, log, XML, CSV: {leaks}')
        check(TOKEN not in json.dumps(fake_state(state)['calls']), 'token giả không có trong nhật ký lời gọi')
        check(ui.external() == [], f'không có request ra ngoài 127.0.0.1: {ui.external()[:3]}')
        check(not ui.errors or all('Failed to load resource' in e or 'ERR_' in e or 'WebSocket' in e for e in ui.errors), f'không lỗi JS: {ui.errors[:3]}')
    finally:
        ui.close()
        p.terminate()
        try:
            p.wait(timeout=20)
        except subprocess.TimeoutExpired:
            p.kill()
    # ---------- 11. trang không có biến CVAT ----------
    log('\n-- 11. mở trang KHÔNG có CVAT_URL / CVAT_ACCESS_TOKEN --')
    r4 = subprocess.run([sys.executable, os.path.join(CODE, 'tool', 'm28.py'), 'push', '--run', 'Khoi', '--cleanup', '--confirm-name', 'demo-Khoi'], cwd=W,
                        env=dict(os.environ, **app_env(W, state)), capture_output=True, text=True, encoding='utf-8')
    check(r4.returncode == 0 and 'Đã xoá task demo-Khoi' in r4.stdout and TOKEN not in r4.stdout + r4.stderr, 'CLI push --cleanup --confirm-name xoá task, không lộ token')
    check(fake_state(state)['tasks'] == [] and n_calls(state, 'Task.remove') == 2, 'CVAT giả: hai task đã từng bị xoá, mỗi task đúng một lần gọi xoá')
    r5 = subprocess.run([sys.executable, os.path.join(CODE, 'tool', 'm28.py'), 'push', '--run', 'Khoi', '--cleanup'], cwd=W,
                        env=dict(os.environ, **app_env(W, state)), capture_output=True, text=True, encoding='utf-8')
    check(r5.returncode == 0 and n_calls(state, 'Task.remove') == 2, 'xoá lần hai (đã task_deleted): không gọi xoá thêm')
    port2 = port + 1
    p2 = start([sys.executable, os.path.join(CODE, 'tool', 'review_app.py'), 'runs/Khoi', 'E2E'], W, port2, app_env(W, state, with_cvat=False),
               os.path.join(shots, 'app_dot_push_noenv.log'))
    env_ui = None
    try:
        wait_port(port2, p2)
        env_ui = base.Ui(pw, port2)
        g = env_ui.page
        env_ui.open()
        g.wait_for_selector('#push-panel', timeout=20000)
        g.wait_for_function("(document.querySelector('#push-panel')?.innerText || '').includes('CVAT_URL')", timeout=20000)
        txt = g.inner_text('#push-panel')
        check(g.locator('#btn-push').is_disabled(), 'thiếu biến môi trường: nút Đẩy khoá')
        check('set CVAT_URL=http://localhost:8080' in txt and 'set CVAT_ACCESS_TOKEN=' in txt and 'cùng cửa sổ cmd' in txt, f'hướng dẫn set trong cmd: {txt[:200]!r}')
        check('tab Cài đặt' in txt, 'hướng dẫn chính: mở tab Cài đặt')
        check(g.locator('#push-panel input, #push-panel textarea').count() == 0 and g.locator('#tab-ra input[type=password], #tab-dot input[type=password]').count() == 0,
              'khung Đẩy lên CVAT và các tab khác không có ô nhập token/URL nào (ô nhập chỉ nằm ở tab Cài đặt)')
        g.get_by_role('tab', name='Cài đặt').click()
        g.wait_for_selector('#cd-token input', timeout=20000)
        check(g.locator('input[type=password]').count() == 1 and g.locator('#tab-caidat input[type=password]').count() == 1, 'đúng một ô password trên trang, nằm ở tab Cài đặt')
        g.get_by_role('tab', name='Rà soát').click()
        g.get_by_role('tab', name='Các đợt').click()
        g.wait_for_selector('#dot-root .dot-card', timeout=20000)
        open_grid(g, 'Khoi')
        g.get_by_role('tab', name='Rà soát').click()
        g.screenshot(path=os.path.join(shots, 'push_no_env.png'), full_page=True)
    finally:
        if env_ui:
            env_ui.close()
        p2.terminate()
        try:
            p2.wait(timeout=20)
        except subprocess.TimeoutExpired:
            p2.kill()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--work', required=True, help='thư mục chạy có config/, face_landmarker.task, r_list.csv')
    ap.add_argument('--imgs', required=True, help='thư mục ảnh khung gốc in-cabin')
    ap.add_argument('--shots', required=True, help='thư mục lưu ảnh chụp (ngoài repo: có mặt người)')
    ap.add_argument('--port', type=int, default=7881)
    a = ap.parse_args()
    W, shots = os.path.abspath(a.work), os.path.abspath(a.shots)
    os.makedirs(shots, exist_ok=True)
    from playwright.sync_api import sync_playwright
    t0 = time.time()
    try:
        with sync_playwright() as pw:
            run(pw, W, os.path.abspath(a.imgs), shots, a.port)
    except (AssertionError, RuntimeError) as e:
        log(f'\nHỎNG: {e}')
        return 1
    finally:
        stop_all()
    log(f'\nQUA sau {time.time() - t0:.0f}s. Ảnh chụp ở {shots}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
