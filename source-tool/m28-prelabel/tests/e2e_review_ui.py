"""Kiểm thử đầu-cuối trang rà soát bằng trình duyệt thật (Chromium qua Playwright). TUỲ CHỌN.

Cần playwright và Chromium, KHÔNG nằm trong requirements, pytest không gom file này (tên không khớp test_*.py).
Chỉ chạy trên Linux (dùng `lsof` để kiểm cổng chỉ bind 127.0.0.1, và `strace` nếu có để liệt kê mọi connect() của server).
Cần một thư mục chạy (--work) có config/, data/ (hoặc không), runs/F5 (5 mặt, đã prepare) và runs/ALL616 (616 mặt, đã prepare);
các lượt này chứa ảnh WFLW nên chỉ để ngoài git. Ví dụ (Linux cloud):

    PYTHONPATH=$S/pwlib PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \\
        python tests/e2e_review_ui.py --work $W --shots $S/ui_shots

Sáu pha (A-F):
  A  chạy app thẳng trên bản chép F5UI: phím tắt, hoàn tác, đóng giữa chừng (kill) rồi mở lại, màn hẹp 800 px, nút Xong chỉ ghi done.txt
     (dải xanh, KHÔNG tắt: tiến trình còn chạy sau 3 giây, tab Các đợt mở được) rồi nút "Đóng trang rà soát" (hộp xác nhận, Huỷ, xác nhận)
     tắt tiến trình mã 0 với lớp phủ "Đã đóng", không có request ra ngoài 127.0.0.1, server chỉ bind 127.0.0.1 (proxy chết).
  B  qua m28 thật: `m28.py review --force review` (Xong, đợi, Đóng) rồi `push --dry-run`, XML/manual_list/rejected khớp CSV.
  C  độ mượt trên ALL616 (616 mặt): mở trang, một quyết định, đổi trang; xoá triage_E2E.csv sau khi đo.
  D  (thêm) lỗi ghi CSV (giả lập Excel khoá file bằng cách đặt một thư mục vào chỗ file): báo "Không ghi được", giữ nguyên mặt, sửa xong bấm lại thì ghi được.
  E  sửa theo đợt kiểm 6/10: đổi bộ lọc, lưới rỗng, dải xanh sau Xong (không lớp phủ), phím tắt/tab cũ không ghi sau Xong, gõ chữ ở tab khác
     được, hộp Đóng (cảnh báo khi chưa Xong, Huỷ, Esc, focus mặc định ở Huỷ), Host lạ bị chặn, cổng bận, tab thứ hai sau Xong, bấm lặp.
  F  tab "Nạp ảnh": kéo thả (set_input_files) ảnh WFLW thật + ảnh xấu vào trang đang rà dở F5UP, tạo lượt NAP_001, prepare thật (MediaPipe),
     tóm tắt, màn hẹp 420 px, "Rà lượt này" (trang tự tải lại cùng cổng, lượt F5UP không bị đụng), Huỷ rồi Thử lại (NAP_002), thiếu model
     (khung đỏ, khoá nút), nút Đóng bị từ chối khi prepare đang chạy, và chế độ `review_app.py --nap` từ trang trống (Đóng ở chế độ này). Cần thêm --wflw (mặc định <work>/../wflw/WFLW_images).
Mọi tiến trình đã mở được dọn ở `finally`. Cổng 7871–7879, M28_NO_BROWSER=1.
"""
import argparse
import csv
import json
import os
import re
import shutil
import socket
import statistics
import subprocess
import tempfile
import sys
import time
import urllib.error
import urllib.request

CODE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(CODE, 'tool'))
from m28core import steps  # noqa: E402

DEAD_PROXY = 'http://127.0.0.1:9'
PROCS = []


def log(*a):
    print(*a, flush=True)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    log('  ok  ', msg)


DONE_BAR = ("Đã ghi xong. Bạn có thể Đẩy lên CVAT, xem Các đợt, xuất Ca khó. "
            "Xong việc bấm 'Đóng trang rà soát' để quay lại cmd.")


def open_close_box(pg):
    """Bấm 'Đóng trang rà soát' ở thanh đầu trang; trả chữ trong hộp xác nhận."""
    pg.click('#btn-dong')
    pg.wait_for_selector('#close-confirm', state='visible', timeout=10000)
    pg.wait_for_timeout(400)
    return pg.inner_text('#close-confirm')


def confirm_close(pg):
    pg.click('#close-confirm-ok')
    pg.wait_for_selector('.m28-closed', state='visible', timeout=10000)


def click_xong(ui):
    """Bấm Xong: trang phải tải lại ĐÚNG MỘT lần (server còn sống), mở lại đúng lượt, tab Rà soát, thấy dải xanh và nút Đóng."""
    pg = ui.page
    n0 = len(ui.loads)
    pg.click('#btn-xong')
    pg.wait_for_function("() => !!document.querySelector('#progress .m28-done-bar')", timeout=15000)
    t = time.time()
    while len(ui.loads) <= n0 and time.time() - t < 15:
        pg.wait_for_timeout(100)
    check(len(ui.loads) == n0 + 1, 'bấm Xong: trang tải lại sau khi ghi done.txt')
    pg.wait_for_selector('#info .face-name', timeout=30000)
    pg.wait_for_selector('#progress .m28-done-bar', state='visible', timeout=15000)
    pg.wait_for_timeout(3000)
    check(len(ui.loads) == n0 + 1, 'trang chỉ tải lại một lần (không vòng lặp reload)')
    check(pg.locator('#tab-ra').is_visible() and pg.locator('#btn-dong').is_visible() and pg.locator('#btn-nhan').is_disabled(),
          'sau tải lại: tab Rà soát, thấy nút Đóng, quyết định vẫn khoá')


def big_fixed(pg):
    """Số phần tử position:fixed phủ gần hết khung nhìn (lớp chặn toàn màn hình)."""
    return pg.evaluate("""() => Array.from(document.querySelectorAll('body *')).filter(e => {
        if (getComputedStyle(e).position !== 'fixed') { return false; }
        const r = e.getBoundingClientRect(); return r.width >= innerWidth * 0.8 && r.height >= innerHeight * 0.8; }).length""")


# ---------- tiến trình ----------
def start(cmd, cwd, port, extra_env=None, out=None):
    env = dict(os.environ, GRADIO_SERVER_PORT=str(port), M28_NO_BROWSER='1', PYTHONUNBUFFERED='1')
    env.setdefault('M28_CONFIG_DIR', os.path.join(tempfile.gettempdir(), 'm28-e2e-cfg'))     # tab Cài đặt: không đọc/ghi hồ sơ người dùng thật
    for k in ('NO_PROXY', 'no_proxy', 'GRADIO_SERVER_NAME'):
        env.pop(k, None)                           # để app tự thêm localhost vào NO_PROXY
    env.update(extra_env or {})
    p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=open(out, 'w', encoding='utf-8') if out else subprocess.DEVNULL,
                         stderr=subprocess.STDOUT)
    PROCS.append(p)
    return p


def wait_port(port, proc, timeout=60):
    t = time.time()
    while time.time() - t < timeout:
        if proc.poll() is not None:
            raise RuntimeError(f'tiến trình thoát sớm, mã {proc.returncode}')
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=1).read(10)
            return time.time() - t
        except Exception:
            time.sleep(0.15)
    raise RuntimeError(f'cổng {port} không mở sau {timeout}s')


def listeners(port):
    r = subprocess.run(['lsof', '-nP', f'-iTCP:{port}', '-sTCP:LISTEN'], capture_output=True, text=True)
    return [l for l in r.stdout.splitlines()[1:] if l.strip()]


def stop_all():
    for p in PROCS:
        if p.poll() is None:
            p.terminate()
    for p in PROCS:
        try:
            p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            p.kill()


# ---------- trình duyệt ----------
class Ui:
    def __init__(self, pw, port, w=1440, h=900):
        self.browser = pw.chromium.launch()
        self.page = self.browser.new_page(viewport={'width': w, 'height': h})
        self.requests, self.errors = [], []
        self.loads = []                              # mỗi lần trang tải xong (kể cả tải lại sau Xong)
        self.page.on('load', lambda _p: self.loads.append(time.time()))
        self.page.on('request', lambda r: self.requests.append(r.url))
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.page.on('console', lambda m: self.errors.append(m.text) if m.type == 'error' else None)
        self.port = port

    def open(self):
        t = time.perf_counter()
        self.page.goto(f'http://127.0.0.1:{self.port}/')
        self.page.wait_for_selector('#info .face-name', timeout=30000)
        self.page.wait_for_function("() => { const i = document.querySelectorAll('#grid img'); "
                                    "return i.length > 0 && Array.from(i).every(x => x.complete && x.naturalWidth > 0); }",
                                    timeout=30000)
        return time.perf_counter() - t

    def progress(self):
        m = re.search(r'Đã rà (\d+)/(\d+)', self.page.inner_text('#progress'))
        return int(m.group(1)), int(m.group(2))

    def cur(self):
        return self.page.inner_text('#info .face-name').strip()

    def wait_done(self, n, timeout=15000):
        self.page.wait_for_function(
            "n => { const m = /Đã rà (\\d+)/.exec(document.querySelector('#progress').innerText); return m && +m[1] === n; }",
            arg=n, timeout=timeout)

    def wait_cur(self, name, timeout=15000):
        self.page.wait_for_function("n => document.querySelector('#info .face-name')?.innerText.trim() === n",
                                    arg=name, timeout=timeout)

    def pick_reason(self, code):
        self.page.locator(f'#reason label:has(input[value="{code}"])').click()

    def external(self):
        return [u for u in self.requests if not u.startswith(('http://127.0.0.1', 'data:', 'blob:'))]

    def close(self):
        self.browser.close()


def read_csv_rows(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.reader(f))


def inside(box, vw, vh):
    return box and box['x'] >= 0 and box['y'] >= 0 and box['x'] + box['width'] <= vw and box['y'] + box['height'] <= vh


# ---------- pha A ----------
def phase_a(pw, W, shots, ports):
    log('\n== PHA A: chạy app thẳng trên runs/F5UI ==')
    run = os.path.join(W, 'runs', 'F5UI')
    shutil.rmtree(run, ignore_errors=True)
    shutil.copytree(os.path.join(W, 'runs', 'F5'), run)
    for d in ('review', 'push', 'xml', '_tmp'):
        shutil.rmtree(os.path.join(run, d), ignore_errors=True)
    csv_path = os.path.join(run, 'review', 'triage_P2.csv')
    cmd = [sys.executable, os.path.join(CODE, 'tool', 'review_app.py'), 'runs/F5UI', 'P2']
    proxy = dict(HTTP_PROXY=DEAD_PROXY, HTTPS_PROXY=DEAD_PROXY, http_proxy=DEAD_PROXY, https_proxy=DEAD_PROXY)
    p = start(cmd, W, ports[0], proxy, os.path.join(shots, 'app_a1.log'))
    wait_port(ports[0], p)
    ls = listeners(ports[0])
    check(ls and all(f'127.0.0.1:{ports[0]}' in l for l in ls) and not any(f'*:{ports[0]}' in l or '0.0.0.0' in l for l in ls),
          f'server chỉ bind 127.0.0.1: {ls[0].split()[-2] if ls else ls}')
    ui = Ui(pw, ports[0])
    pg = ui.page
    try:
        ui.open()
        head = pg.inner_text('#progress')
        check('F5UI' in head and 'P2' in head and ui.progress() == (0, 5), f'tiêu đề có F5UI, P2, 0/5: {head.splitlines()[:3]}')
        check(pg.title() == 'Rà soát M28 · F5UI', f'tiêu đề tab: {pg.title()}')
        check(pg.locator('#btn-xong').is_disabled(), 'nút Xong đang khoá')
        check(ui.cur() == 'F_004.png', f'mặt đầu là F_004 (đáng ngờ nhất): {ui.cur()}')
        check(len(pg.locator('#grid img').all()) == 5, 'lưới có 5 ảnh nhỏ')
        boxes = {s: pg.locator(s).first.bounding_box() for s in ('#big', '#btn-nhan', '#btn-gantay', '#btn-bo')}
        check(all(inside(b, 1440, 900) for b in boxes.values()),
              'ảnh lớn và 3 nút quyết định nằm trong khung nhìn 1440x900 ' + str({k: (round(v['y']), round(v['y'] + v['height'])) for k, v in boxes.items()}))
        check(boxes['#btn-nhan']['height'] >= 54, f"nút quyết định cao {boxes['#btn-nhan']['height']:.0f}px")
        check(pg.evaluate("document.documentElement.scrollWidth") <= 1440, 'không có cuộn ngang ở 1440')
        pg.screenshot(path=os.path.join(shots, '01_desktop_dau.png'))

        pg.keyboard.press('n')
        ui.wait_done(1)
        check(ui.cur() == 'F_002.png', 'bấm N: F_004 Nhận, tự sang F_002')
        rows = read_csv_rows(csv_path)
        check(rows[0] == ['name', 'decision', 'reason', 'seconds'] and len(rows) == 2 and rows[1][:3] == ['F_004.png', 'nhan', ''],
              f'CSV có tiêu đề + 1 dòng: {rows}')
        pg.keyboard.press('3')
        pg.keyboard.press('g')
        ui.wait_done(2)
        ui.wait_cur('F_001.png')
        check(read_csv_rows(csv_path)[-1][:3] == ['F_002.png', 'gan_tay', 'LECH_VUNG'], 'phím 3 rồi G: F_002 Gán tay, LECH_VUNG')
        check(pg.locator('#reason input:checked').get_attribute('value') == '', 'lý do tự đặt lại "(không)" sau quyết định')
        pg.keyboard.press('z')
        ui.wait_done(1)
        ui.wait_cur('F_002.png')
        check(ui.progress() == (1, 5), 'bấm Z: F_002 về chưa rà, tiến độ 1/5')
        ui.pick_reason('MO_NHO')                       # chọn bằng chuột: focus nằm trên ô radio
        pg.click('#btn-bo')
        ui.wait_done(2)
        ui.wait_cur('F_001.png')
        rows = read_csv_rows(csv_path)
        check(rows[-1][:3] == ['F_002.png', 'bo', 'MO_NHO'], f'F_002 Bỏ ảnh, MO_NHO: {rows[-1]}')
        before = len(rows)
        check(pg.evaluate('document.activeElement && document.activeElement.id') == 'btn-bo', 'focus đang nằm trên nút Bỏ ảnh (sau khi bấm chuột)')
        pg.keyboard.press('Enter')                      # focus đang ở nút Bỏ: Enter/Space không được quyết định nhầm F_001
        pg.keyboard.press('Space')
        pg.wait_for_timeout(900)
        check(len(read_csv_rows(csv_path)) == before and ui.cur() == 'F_001.png', 'Enter/Space trên nút quyết định không làm gì')
        check(ui.external() == [], f'không có request ra ngoài 127.0.0.1 (đã thấy {len(ui.requests)} request)')
        check(not ui.errors, f'không có lỗi JS/console: {ui.errors[:2]}')
    finally:
        ui.close()
    p.kill()                                           # giả lập sập
    p.wait()
    log('  ...  đã kill app, chạy lại')
    trace = os.path.join(shots, 'strace_a2.txt')
    cmd2 = ['strace', '-f', '-e', 'trace=connect', '-o', trace] + cmd if shutil.which('strace') else cmd
    p = start(cmd2, W, ports[1], proxy, os.path.join(shots, 'app_a2.log'))        # strace: liệt kê mọi connect() của server
    wait_port(ports[1], p)
    ui = Ui(pw, ports[1])
    pg = ui.page
    try:
        ui.open()
        check(ui.progress() == (2, 5) and ui.cur() == 'F_001.png', f'mở lại: tiến độ 2/5, đứng ở F_001 ({ui.progress()}, {ui.cur()})')
        check('Làm tiếp' in pg.inner_text('#notes'), 'có ghi chú làm tiếp từ lần trước')
        pg.set_viewport_size({'width': 800, 'height': 900})
        pg.wait_for_timeout(500)
        pg.locator('#filter label:has(input[value="chua_ra"])').click()
        pg.wait_for_function("document.querySelectorAll('#grid img').length === 3")
        pg.wait_for_timeout(400)
        check(pg.evaluate("document.documentElement.scrollWidth") <= 800, 'ở 800 px không có cuộn ngang')
        yb = {s: pg.locator(s).first.bounding_box() for s in ('#big', '#grid', '#info')}
        pg.screenshot(path=os.path.join(shots, '02_hep_800.png'), full_page=True)
        check(yb['#big']['y'] < yb['#info']['y'] < yb['#grid']['y'], 'ở 800 px các cột xếp chồng: ảnh lớn, thông tin, rồi lưới')
        for s in ('#btn-nhan', '#btn-gantay', '#btn-bo'):
            pg.locator(s).click(trial=True)             # trial: Playwright kiểm nút nhìn thấy, ổn định, không bị che
        check(True, 'ở 800 px ba nút quyết định bấm được')
        pg.set_viewport_size({'width': 1440, 'height': 900})
        pg.wait_for_timeout(500)
        pg.keyboard.press('ArrowRight')                 # bộ lọc "Chưa rà" còn hiệu lực: F_001, F_003, F_005
        ui.wait_cur('F_003.png')
        pg.keyboard.press('ArrowLeft')
        ui.wait_cur('F_001.png')
        check(True, '← / → đi trong danh sách đã lọc')
        pg.keyboard.press('n')
        ui.wait_done(3)
        ui.wait_cur('F_003.png')
        pg.wait_for_function("document.querySelectorAll('#grid img').length === 2")
        check(True, 'bộ lọc "Chưa rà" tự co lại sau mỗi quyết định (3 -> 2 ảnh), tự sang F_003')
        pg.locator('#filter label:has(input[value="tat_ca"])').click()
        pg.wait_for_function("document.querySelectorAll('#grid img').length === 5")
        pg.locator('#grid .thumbnail-item').nth(4).click()
        ui.wait_cur('F_005.png')
        check(pg.locator('#grid .thumbnail-item.m28-cur').count() == 1 and pg.evaluate("Array.from(document.querySelectorAll('#grid .thumbnail-item')).findIndex(e => e.classList.contains('m28-cur'))") == 4,
              'bấm ảnh trong lưới: xem mặt đó, đúng ảnh đó được đánh dấu')
        ui.pick_reason('NHIEU_MAT')
        pg.keyboard.press('g')                          # focus ở ô radio mà phím tắt vẫn chạy
        ui.wait_done(4)
        check(read_csv_rows(csv_path)[-1][:3] == ['F_005.png', 'gan_tay', 'NHIEU_MAT'], 'chọn lý do bằng chuột rồi phím G: vẫn ghi')
        ui.wait_cur('F_003.png')                        # sau F_005 đi vòng lại đầu: mặt chưa rà duy nhất
        pg.keyboard.press('ArrowLeft')                  # focus ở radio: ← vẫn là "Trước" (F_003 -> F_001), không đổi lý do
        ui.wait_cur('F_001.png')
        check(pg.locator('#reason input:checked').get_attribute('value') == '', '← khi focus ở radio không đổi lý do')
        pg.keyboard.press('ArrowRight')
        ui.wait_cur('F_003.png')
        pg.click('#btn-nhan')
        ui.wait_done(5)
        pg.wait_for_function("!document.querySelector('#btn-xong').disabled")
        check('Đã rà hết' in pg.inner_text('#msg'), 'rà hết: có dòng "Đã rà hết, bấm Xong"')
        check(not pg.locator('#btn-xong').is_disabled() and pg.inner_text('#btn-xong').strip() == 'Xong', 'nút Xong bật lên')
        pg.screenshot(path=os.path.join(shots, '03_desktop_xong.png'))
        t = time.time()
        click_xong(ui)
        check(os.path.exists(os.path.join(run, 'review', 'done.txt')), 'bấm Xong: review/done.txt xuất hiện')
        check(pg.inner_text('#progress .m28-done-bar').strip() == DONE_BAR, 'bấm Xong: dải xanh ở đầu trang đúng chữ')
        check(pg.locator('#progress .m28-done-bar').get_attribute('role') == 'status', 'dải xanh có role=status')
        check(pg.locator('.m28-done, .m28-closed, .m28-modal').count() == 0 and big_fixed(pg) == 0, 'sau Xong không có lớp phủ/hộp nào chặn màn hình')
        check(pg.locator('#btn-nhan').is_disabled() and pg.locator('#btn-xong').is_disabled() and pg.locator('#btn-undo').is_disabled(),
              'sau Xong: Nhận/Hoàn tác/Xong bị khoá')
        check(pg.locator('#btn-dong').is_visible(), 'nút Đóng trang rà soát thấy được sau Xong')
        pg.screenshot(path=os.path.join(shots, '03b_sau_xong_dai_xanh.png'))
        n_csv = len(read_csv_rows(csv_path))
        for k in ('n', 'g', 'b', 'z', 'k', '3', 'ArrowLeft'):
            pg.keyboard.press(k)
        pg.wait_for_timeout(3200)
        check(p.poll() is None, f'Xong KHÔNG tắt: tiến trình vẫn chạy sau {time.time() - t:.1f}s')
        check(len(read_csv_rows(csv_path)) == n_csv and os.path.exists(os.path.join(run, 'review', 'done.txt')),
              'phím N/G/B/Z/K/3/← sau Xong không ghi gì, done.txt còn')
        pg.get_by_role('tab', name='Các đợt').click()
        pg.wait_for_selector('#dot-root .dot-card', timeout=15000)
        check('F5UI' in pg.inner_text('#dot-root') and pg.locator('#progress .m28-done-bar').is_visible() and pg.locator('#btn-dong').is_visible(),
              'sau Xong: tab Các đợt mở được, dải xanh và nút Đóng vẫn ở đầu trang')
        pg.get_by_role('tab', name='Rà soát').click()
        pg.wait_for_selector('#info .face-name')
        box = open_close_box(pg)
        check('Lệnh m28 trong cmd sẽ đi tiếp' in box and 'chưa bấm Xong' not in box, f'hộp Đóng sau Xong: {box!r}')
        check(pg.evaluate('document.activeElement && document.activeElement.id') == 'close-confirm-cancel', 'hộp Đóng: nút Huỷ có focus mặc định')
        pg.screenshot(path=os.path.join(shots, '03c_hop_dong.png'))
        pg.click('#close-confirm-cancel')
        pg.wait_for_selector('#close-confirm', state='hidden', timeout=10000)
        pg.wait_for_timeout(1500)
        check(p.poll() is None and pg.locator('.m28-closed').count() == 0, 'Huỷ ở hộp Đóng: trang và tiến trình còn nguyên')
        open_close_box(pg)
        confirm_close(pg)
        code = p.wait(timeout=15)
        check(code == 0, f'xác nhận Đóng: tiến trình thoát mã 0 sau {time.time() - t:.1f}s kể từ Xong')
        check('Đã đóng trang rà soát' in pg.inner_text('.m28-closed'), 'lớp phủ "Đã đóng trang rà soát" hiện sau khi đóng')
        pg.screenshot(path=os.path.join(shots, '03d_sau_dong.png'))
        log_a = open(os.path.join(shots, 'app_a2.log'), encoding='utf-8').read()
        check('đã bấm Xong' in log_a.splitlines()[-1] and 'F5UI' in log_a.splitlines()[-1], f'cmd in dòng đã đóng sau Xong: {log_a.splitlines()[-1]!r}')
        check(ui.external() == [], 'cuối pha: vẫn không có request ra ngoài 127.0.0.1')
    finally:
        ui.close()
    if os.path.exists(trace):
        outside = []
        for line in open(trace, encoding='utf-8', errors='replace'):
            m = re.search(r'connect\(\d+, \{sa_family=AF_INET6?, sin6?_port=htons\((\d+)\).*?(?:inet_addr\("([^"]+)"\)|inet_pton\(AF_INET6, "([^"]+)")', line)
            if m and (m.group(2) or m.group(3)) not in ('127.0.0.1', '::1'):
                outside.append(line.strip())
        n_conn = sum(1 for l in open(trace, encoding='utf-8', errors='replace') if 'connect(' in l)
        check(outside == [], f'strace: server không connect() tới địa chỉ nào ngoài 127.0.0.1/::1 ({n_conn} lệnh connect, kể cả đóng trang)')
    rows = read_csv_rows(csv_path)
    check(rows[0] == ['name', 'decision', 'reason', 'seconds'], 'CSV: tiêu đề name,decision,reason,seconds')
    check(all(r[0].endswith('.png') for r in rows[1:]), 'CSV: mọi name có đuôi .png')
    tri = steps.read_triage(csv_path)
    check(sorted(tri) == [f'F_00{i}' for i in range(1, 6)] and all(v[0] in steps.DECISIONS for v in tri.values()),
          f'read_triage ra đủ 5 mặt, decision hợp lệ: {tri}')
    check(tri['F_002'] == ('bo', 'MO_NHO'), 'F_002 cuối cùng là bo/MO_NHO')
    secs = [r[3] for r in rows[1:] if r[1]]
    check(all(re.fullmatch(r'\d+(\.\d)?', s) and float(s) >= 0 for s in secs), f'cột seconds là số >= 0 trên mọi dòng quyết định: {secs}')
    return tri


# ---------- pha B ----------
def phase_b(pw, W, shots, port, tri):
    log('\n== PHA B: qua m28 thật (review --force review, rồi push --dry-run) ==')
    run = os.path.join(W, 'runs', 'F5UI')
    out = os.path.join(shots, 'm28_review.log')
    p = start([sys.executable, os.path.join(CODE, 'tool', 'm28.py'), 'review', '--run', 'F5UI', '--reviewer', 'P2',
               '--force', 'review'], W, port, out=out)
    wait_port(port, p)
    ui = Ui(pw, port)
    try:
        ui.open()
        check(ui.progress() == (5, 5) and not ui.page.locator('#btn-xong').is_disabled(), 'mở qua m28: tiến độ 5/5, nút Xong đang bật')
        check(not os.path.exists(os.path.join(run, 'review', 'done.txt')), 'm28 đã xoá done.txt cũ trước khi mở trang')
        click_xong(ui)
        check(os.path.exists(os.path.join(run, 'review', 'done.txt')), 'bấm Xong: done.txt có')
        check(p.poll() is None, 'sau Xong, `m28.py review` vẫn đang chờ (chưa bấm Đóng)')
        open_close_box(ui.page)
        confirm_close(ui.page)
    finally:
        ui.close()
    code = p.wait(timeout=20)
    text = open(out, encoding='utf-8').read()
    check(code == 0 and 'đã đóng mà chưa bấm Xong' not in text, f'm28 review thoát mã {code}, không in "Trang rà soát đã đóng mà chưa bấm Xong"')
    check('đã bấm Xong' in text, 'cmd in dòng "Đã đóng trang rà soát: lượt F5UI đã bấm Xong"')
    lines = open(os.path.join(run, 'log.txt'), encoding='utf-8').read().splitlines()
    check(lines[-1].split('\t')[1:3] == ['review', 'xong'], f'log.txt có dòng review xong: {lines[-1]}')
    check(open(os.path.join(run, 'review', 'done.txt'), encoding='utf-8').read() == 'ok', 'review/done.txt có nội dung ok (m28 ghi đè)')
    r = subprocess.run([sys.executable, os.path.join(CODE, 'tool', 'm28.py'), 'push', '--run', 'F5UI', '--reviewer', 'P2', '--dry-run'],
                       cwd=W, capture_output=True, text=True, encoding='utf-8', timeout=120)
    check(r.returncode != 0 and 'dry-run' in r.stdout, f'push --dry-run dừng có chủ ý (mã {r.returncode})')
    nhan = sorted(n for n, (d, _) in tri.items() if d == 'nhan')
    tay = sorted(n + '.png' for n, (d, _) in tri.items() if d == 'gan_tay')
    bo = sorted((n, w) for n, (d, w) in tri.items() if d == 'bo')                 # rejected.csv ghi tên không đuôi
    xml = open(os.path.join(run, 'xml', 'prelabel.xml'), encoding='utf-8').read()
    names = sorted(re.findall(r'<image id="\d+" name="([^"]+)"', xml))
    check(names == [n + '.png' for n in nhan], f'prelabel.xml có {len(names)} <image> = số mặt Nhận ({nhan})')
    check(sorted(open(os.path.join(run, 'push', 'manual_list.txt'), encoding='utf-8').read().split()) == tay, f'manual_list.txt = các mặt Gán tay {tay}')
    rej = sorted((r_[0], r_[1]) for r_ in read_csv_rows(os.path.join(run, 'push', 'rejected.csv'))[1:])
    check(rej == bo, f'rejected.csv = các mặt Bỏ ảnh kèm lý do {bo}')


# ---------- pha C ----------
def phase_c(pw, W, shots, port):
    log('\n== PHA C: độ mượt trên ALL616 (616 mặt) ==')
    run = os.path.join(W, 'runs', 'ALL616')
    csv_path = os.path.join(run, 'review', 'triage_E2E.csv')
    if os.path.exists(csv_path):
        os.remove(csv_path)
    shutil.rmtree(os.path.join(run, '_tmp'), ignore_errors=True)       # đo lúc nguội: chưa có ảnh nhỏ nào
    t0 = time.perf_counter()
    p = start([sys.executable, os.path.join(CODE, 'tool', 'review_app.py'), 'runs/ALL616', 'E2E'], W, port, out=os.path.join(shots, 'app_c.log'))
    boot = wait_port(port, p)
    ui = Ui(pw, port)
    res = {}
    try:
        t_open = ui.open()
        res['khởi động server (s)'] = round(boot + 0.0, 2)
        res['mở trang đến khi lưới hiện ảnh (s)'] = round(t_open, 2)
        res['tổng từ lệnh chạy đến lưới hiện ảnh (s)'] = round(time.perf_counter() - t0, 2)
        pg = ui.page
        n_grid = pg.locator('#grid img').count()
        check(n_grid == 24, f'lưới chỉ có 24 ảnh nhỏ mỗi trang (616 mặt, {n_grid} ảnh)')
        check('1</b>/26' in pg.inner_html('#pagelbl') or '26' in pg.inner_text('#pagelbl'), f"có 26 trang: {pg.inner_text('#pagelbl')}")
        big_src = pg.locator('#big img').get_attribute('src')
        check(os.path.join('_tmp') in big_src or '/gradio_api/file=' in big_src, 'ảnh lớn là ảnh chồng')
        check('không có nháp' in pg.locator('#grid .caption-label').first.inner_text(),
              f"24 mặt MediaPipe không thấy mặt đứng đầu hàng đợi, không có nháp: {pg.locator('#grid .caption-label').first.inner_text()!r}")
        check(pg.locator('#btn-nhan').is_disabled(), 'mặt không có nháp: nút Nhận bị khoá')
        pg.keyboard.press('n')
        pg.wait_for_timeout(600)
        check(ui.progress() == (0, 616), 'mặt không có nháp: phím N không làm gì')
        pages = []

        def next_page(i):
            t = time.perf_counter()
            pg.click('#btn-pagenext')
            pg.wait_for_function("n => document.querySelector('#pagelbl').innerText.includes('Trang ' + n + '/')", arg=i)
            pg.wait_for_function("() => { const i = document.querySelectorAll('#grid img'); "
                                 "return i.length > 0 && Array.from(i).every(x => x.complete && x.naturalWidth > 0); }")
            pages.append(time.perf_counter() - t)

        next_page(2)                                                    # trang 2: mặt thứ 25 trở đi đã có nháp
        pg.locator('#grid .thumbnail-item').nth(0).click()
        pg.wait_for_function("document.querySelector('#info .face-name') && !document.querySelector('#btn-nhan').disabled")
        lat = []
        for i in range(10):
            t = time.perf_counter()
            pg.keyboard.press('n')
            ui.wait_done(i + 1)
            lat.append(time.perf_counter() - t)
        res['quyết định, trung vị (s)'] = round(statistics.median(lat), 2)
        res['quyết định, lớn nhất (s)'] = round(max(lat), 2)
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(shots, '04_all616.png'))
        for i in range(3, 27):
            next_page(i)
        check('26' in pg.inner_text('#pagelbl') and pg.locator('#grid img').count() == 16, f'trang cuối có 16 ảnh: {pg.inner_text("#pagelbl")}')
        res['đổi trang lần đầu, trung vị (s)'] = round(statistics.median(pages), 2)
        res['đổi trang lần đầu, lớn nhất (s)'] = round(max(pages), 2)
        res['đổi trang cuối (s)'] = round(pages[-1], 2)
        t = time.perf_counter()
        for i in range(25, 0, -1):
            pg.click('#btn-pageprev')
            pg.wait_for_function("n => document.querySelector('#pagelbl').innerText.includes('Trang ' + n + '/')", arg=i)
        res['về trang 1 sau 25 lần bấm (s)'] = round(time.perf_counter() - t, 2)
        check(ui.external() == [], 'không có request ra ngoài')
        check(not ui.errors, f'không lỗi JS/console: {ui.errors[:2]}')
    finally:
        ui.close()
    log('\n  số đo ALL616:')
    for k, v in res.items():
        log(f'    {k}: {v}')
    check(res['tổng từ lệnh chạy đến lưới hiện ảnh (s)'] <= 8, 'lần mở đầu <= 8 s')
    check(res['quyết định, trung vị (s)'] <= 1.5, 'mỗi quyết định <= 1,5 s (trung vị)')
    check(res['đổi trang lần đầu, lớn nhất (s)'] <= 2, 'đổi trang <= 2 s')
    if os.path.exists(csv_path):
        os.remove(csv_path)                                            # không bấm Xong, không để lại dấu vết
    return res


# ---------- pha D ----------
def phase_d(pw, W, shots, port):
    log('\n== PHA D: lỗi ghi CSV (giả lập file bị khoá) ==')
    run = os.path.join(W, 'runs', 'F5LOCK')
    shutil.rmtree(run, ignore_errors=True)
    shutil.copytree(os.path.join(W, 'runs', 'F5'), run)
    for d in ('review', 'push', 'xml', '_tmp'):
        shutil.rmtree(os.path.join(run, d), ignore_errors=True)
    blocker = os.path.join(run, 'review', 'triage_P2.csv')
    p = start([sys.executable, os.path.join(CODE, 'tool', 'review_app.py'), 'runs/F5LOCK', 'P2'], W, port, out=os.path.join(shots, 'app_d.log'))
    wait_port(port, p)
    ui = Ui(pw, port)
    pg = ui.page
    try:
        ui.open()
        os.makedirs(blocker)                           # open(..., "a") và đọc đều lỗi OSError, như PermissionError khi Excel khoá file
        pg.keyboard.press('n')
        pg.wait_for_selector('.toast-message-text', timeout=10000)
        toast = pg.inner_text('.toast-message-text').strip()
        check('Không ghi được' in toast and 'đóng Excel rồi bấm lại' in toast, f'ghi lỗi: hiện cảnh báo (toast) "{toast[:90]}..."')
        check('Excel' in pg.inner_text('#msg') and ui.progress() == (0, 5) and ui.cur() == 'F_004.png', 'giữ nguyên mặt F_004, tiến độ 0/5')
        check(not pg.locator('#btn-xong').is_enabled(), 'trang không sập, nút Xong vẫn khoá')
        pg.screenshot(path=os.path.join(shots, '05_loi_ghi.png'))
        shutil.rmtree(blocker)
        pg.keyboard.press('n')
        ui.wait_done(1)
        check(ui.cur() == 'F_002.png' and steps.read_triage(blocker)['F_004'][0] == 'nhan', 'sửa xong bấm lại: ghi được, sang F_002')
        check(not ui.errors or all('500' in e or 'Failed to load resource' in e for e in ui.errors), f'không lỗi JS: {ui.errors[:2]}')
    finally:
        ui.close()
        p.terminate()
    shutil.rmtree(run, ignore_errors=True)


# ---------- pha E ----------
def phase_e(pw, W, shots, port):
    log('\n== PHA E: sửa theo đợt kiểm 6/10 (bộ lọc, lưới rỗng, lớp phủ Xong, Host, cổng, hai tab) ==')
    run = os.path.join(W, 'runs', 'F5UX')
    shutil.rmtree(run, ignore_errors=True)
    shutil.copytree(os.path.join(W, 'runs', 'F5'), run)
    for d in ('review', 'push', 'xml', '_tmp'):
        shutil.rmtree(os.path.join(run, d), ignore_errors=True)
    csv_path = os.path.join(run, 'review', 'triage_P2.csv')
    cmd = [sys.executable, os.path.join(CODE, 'tool', 'review_app.py'), 'runs/F5UX', 'P2']
    p = start(cmd, W, port, None, os.path.join(shots, 'app_e.log'))
    wait_port(port, p)
    # bản thứ hai trên cùng cổng: lỗi rõ ràng mã 2, không tự nhảy sang cổng khác
    p2 = start(cmd, W, port, None, os.path.join(shots, 'app_e2.log'))
    p2.wait(timeout=60)
    msg2 = open(os.path.join(shots, 'app_e2.log'), encoding='utf-8').read()
    check(p2.returncode == 2 and f'Cổng {port} bận' in msg2, f'bản thứ hai thoát mã 2 báo cổng bận: {msg2.strip()[:90]!r}')
    check(len(listeners(port + 1)) == 0, 'không có server nào mở ở cổng kế bên')
    # Host lạ và file ngoài thư mục ảnh
    def get(path, host=None):
        req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', headers={'Host': host} if host else {})
        try:
            return urllib.request.urlopen(req, timeout=5).status
        except urllib.error.HTTPError as e:
            return e.code
    img = f'/gradio_api/file={os.path.abspath(os.path.join(run, "crop", "images", "F_001.png"))}'
    csv_url = f'/gradio_api/file={os.path.abspath(os.path.join(run, "flags", "flags.json"))}'
    check(get(img) == 200, 'ảnh cắt vẫn lấy được với Host 127.0.0.1')
    check(get(img, f'evil.example:{port}') == 400, 'Host lạ (DNS rebinding) bị từ chối 400')
    check(get(csv_url) == 403, 'flags.json (ngoài overlays, crop/images, _tmp) không lấy được qua /file= (403)')
    ui = Ui(pw, port)
    pg = ui.page
    other = ui.browser.new_page(viewport={'width': 1440, 'height': 900})        # tab thứ hai, mở sớm (trạng thái cũ)
    try:
        ui.open()
        other.goto(f'http://127.0.0.1:{port}/')
        other.wait_for_selector('#info .face-name', timeout=30000)
        ys = []
        for name in ('F_001', 'F_004', 'F_005'):
            pg.locator(f'#grid .thumbnail-item:has(img[alt^="{name}"])').first.click()
            ui.wait_cur(name + '.png')
            pg.wait_for_timeout(250)
            ys.append(round(pg.locator('#btn-xong').bounding_box()['y']))
        check(max(ys) - min(ys) <= 2, f'nút Xong không nhảy lên xuống giữa các mặt: y={ys}')
        txt = pg.inner_text('#info')
        check('Điểm nghi sai' in txt and 'Gợi ý của máy' in txt and 'low_conf' not in txt.split('Điểm nghi sai')[0],
              'cột thông tin dùng chữ dễ hiểu (Điểm nghi sai, Gợi ý của máy)')
        # đang xem F_005 (0 cờ) rồi lọc Đáng ngờ: phải sang mặt có trong danh sách
        pg.locator('#filter label:has-text("Đáng ngờ")').click()
        ui.wait_cur('F_004.png')
        check(pg.locator('#grid .thumbnail-item.m28-cur').count() == 1, 'đổi bộ lọc: mặt đang xem được viền xanh trong lưới')
        check(len(pg.locator('#grid img').all()) == 2 and not pg.locator('#btn-bo').is_disabled(),
              'bộ lọc Đáng ngờ: 2 ảnh, nút quyết định bật')
        pg.screenshot(path=os.path.join(shots, 'after_01_loc_dangngo.png'))
        pg.locator('#filter label:has-text("Tất cả")').click()
        pg.wait_for_function("document.querySelectorAll('#grid img').length === 5")
        pg.wait_for_timeout(800)                         # chờ lần vẽ lại của bộ lọc xong, kẻo nó xoá dòng nhắc của quyết định kế tiếp (flake cũ)
        # Gán tay không lý do: nhắc mềm
        pg.keyboard.press('g')
        ui.wait_done(1)
        pg.wait_for_function("document.querySelector('#msg').innerText.includes('Chưa có lý do')", timeout=10000)
        check('Chưa có lý do' in pg.inner_text('#msg'), 'Gán tay không lý do: có nhắc "Chưa có lý do"')
        box = open_close_box(pg)                        # chưa bấm Xong, còn mặt chưa rà: cảnh báo
        check('chưa bấm Xong, lượt này sẽ còn mặt chưa rà' in box and '4 mặt' in box and 'dừng ở bước review' in box, f'hộp Đóng chưa Xong, còn mặt: {box!r}')
        pg.screenshot(path=os.path.join(shots, 'after_02b_dong_chua_xong.png'))
        pg.keyboard.press('Escape')                     # Esc = Huỷ
        pg.wait_for_selector('#close-confirm', state='hidden', timeout=10000)
        check(p.poll() is None, 'Esc ở hộp Đóng: không đóng')
        check('TRƯỚC' in pg.inner_text('#reason'), 'nhãn lý do ghi rõ chọn TRƯỚC')
        pg.screenshot(path=os.path.join(shots, 'after_02_nhac_ly_do.png'))
        # rà hết mặt còn lại
        for _ in range(4):
            pg.keyboard.press('n')
            pg.wait_for_timeout(500)
        ui.wait_done(5)
        n_rows = len(read_csv_rows(csv_path))
        for _ in range(4):
            pg.keyboard.press('n')
            pg.wait_for_timeout(300)
        check(len(read_csv_rows(csv_path)) == n_rows, f'bấm N lặp ở mặt đã Nhận không ghi thêm dòng ({n_rows} dòng)')
        check('đã là Nhận rồi' in pg.inner_text('#msg'), 'báo "đã là Nhận rồi"')
        # lưới rỗng
        pg.locator('#filter label:has-text("Chưa rà")').click()
        pg.wait_for_selector('.m28-empty', timeout=10000)
        check(pg.locator('#grid img').count() == 0 or not pg.locator('#grid').is_visible(), 'lọc rỗng: không còn lưới/biểu tượng ảnh hỏng')
        check('không còn mặt chưa rà' in pg.inner_text('.m28-empty') and 'Trang' not in pg.inner_text('#pagelbl'),
              'lọc rỗng: thông báo rõ, không có số trang')
        check(pg.locator('#btn-nhan').is_disabled() and pg.locator('#btn-bo').is_disabled(), 'lọc rỗng: N/G/B bị khoá')
        pg.screenshot(path=os.path.join(shots, 'after_03_loc_rong.png'))
        pg.locator('#filter label:has-text("Tất cả")').click()
        pg.wait_for_timeout(500)
        # 500 px: nút không xuống dòng lệch nhau
        pg.set_viewport_size({'width': 500, 'height': 900})
        pg.wait_for_timeout(500)
        hs = [pg.locator(s).first.bounding_box()['height'] for s in ('#btn-nhan', '#btn-gantay', '#btn-bo', '#btn-prev', '#btn-undo', '#btn-next')]
        check(max(hs[:3]) - min(hs[:3]) < 2 and max(hs[3:]) - min(hs[3:]) < 2, f'500px: nút cùng hàng cao bằng nhau {hs}')
        pg.screenshot(path=os.path.join(shots, 'after_04_500px.png'), full_page=True)
        pg.set_viewport_size({'width': 1440, 'height': 900})
        pg.wait_for_timeout(400)
        box = open_close_box(pg)                        # chưa bấm Xong nhưng đã rà hết
        check('chưa bấm Xong: m28 sẽ coi như chưa rà xong; bấm Huỷ rồi bấm Xong trước nếu muốn đi tiếp' in box, f'hộp Đóng chưa Xong, rà hết: {box!r}')
        pg.click('#close-confirm-cancel')
        pg.wait_for_selector('#close-confirm', state='hidden', timeout=10000)
        # Xong: dải xanh (không lớp phủ), tab cũ không ghi được, trang vẫn dùng được
        click_xong(ui)
        check(pg.inner_text('#progress .m28-done-bar').strip() == DONE_BAR, 'bấm Xong: dải xanh đúng chữ ở đầu trang')
        check(big_fixed(pg) == 0 and pg.locator('.m28-done, .m28-closed').count() == 0, 'không có lớp phủ chặn nào sau Xong')
        pg.screenshot(path=os.path.join(shots, 'after_05_xong_dai_xanh.png'))
        before = read_csv_rows(csv_path)
        other.click('#btn-bo')
        other.wait_for_selector('#progress .m28-done-bar', state='visible', timeout=10000)
        other.wait_for_timeout(600)
        check(read_csv_rows(csv_path) == before, 'tab cũ bấm Bỏ sau Xong: không ghi gì')
        check(other.locator('#btn-bo').is_disabled() and other.locator('#btn-xong').is_disabled(), 'tab cũ cũng thấy dải xanh và bị khoá quyết định')
        check(os.path.exists(os.path.join(run, 'review', 'done.txt')), 'done.txt không bị xoá')
        pg.get_by_role('tab', name='Nạp ảnh').click()   # gõ chữ ở tab khác sau Xong phải gõ được; phím tắt không ghi gì
        pg.fill('#nap-name textarea, #nap-name input', '')
        pg.click('#nap-name textarea, #nap-name input')
        pg.keyboard.type('nbgz k12')
        check(pg.input_value('#nap-name textarea, #nap-name input') == 'nbgz k12', 'sau Xong: gõ chữ (kể cả n b g z k) ở ô tên lượt tab Nạp ảnh được')
        pg.fill('#nap-name textarea, #nap-name input', '')
        pg.get_by_role('tab', name='Ca khó').click()
        pg.wait_for_selector('#ck-export', timeout=10000)
        check(pg.locator('#ck-export').is_enabled() and pg.locator('#progress .m28-done-bar').is_visible(), 'sau Xong: tab Ca khó dùng được, dải xanh còn ở đầu trang')
        pg.get_by_role('tab', name='Rà soát').click()
        pg.wait_for_selector('#info .face-name')
        pg.keyboard.press('b')
        pg.keyboard.press('n')
        pg.wait_for_timeout(800)
        check(read_csv_rows(csv_path) == before and p.poll() is None, 'phím B/N ở tab Rà soát sau Xong: không ghi, trang còn sống')
        t = time.time()
        pg.wait_for_timeout(2500)
        check(p.poll() is None, f'Xong KHÔNG tắt tiến trình ({time.time() - t + 3:.0f}s sau khi bấm)')
        box = open_close_box(pg)
        check('Lệnh m28 trong cmd sẽ đi tiếp' in box, f'hộp Đóng sau Xong: {box!r}')
        pg.keyboard.press('b')                           # hộp đang mở: phím tắt không làm gì
        pg.wait_for_timeout(500)
        check(read_csv_rows(csv_path) == before, 'hộp Đóng đang mở: phím B không ghi')
        pg.keyboard.press('Tab')
        pg.keyboard.press('Tab')
        pg.keyboard.press('Tab')
        check(pg.evaluate("document.activeElement && document.activeElement.closest('#close-confirm') !== null"), 'Tab giữ focus trong hộp Đóng')
        pg.keyboard.press('Escape')
        pg.wait_for_selector('#close-confirm', state='hidden', timeout=10000)
        pg.wait_for_timeout(1500)
        check(p.poll() is None, 'Esc ở hộp Đóng: không đóng')
        open_close_box(pg)
        confirm_close(pg)
        pg.screenshot(path=os.path.join(shots, 'after_06_sau_dong.png'))
        t = time.time()
        while p.poll() is None and time.time() - t < 10:
            time.sleep(0.2)
        check(p.returncode == 0 and os.path.exists(os.path.join(run, 'review', 'done.txt')), 'xác nhận Đóng: tiến trình thoát mã 0, done.txt còn')
        check(not ui.external(), 'không có request ra ngoài 127.0.0.1')
        check(not ui.errors or all('Failed to load resource' in e or 'ERR_' in e for e in ui.errors), f'không lỗi JS: {ui.errors[:2]}')
    finally:
        ui.close()


# ---------- pha F ----------
def _sha(path):
    import hashlib
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def make_nap_inputs(W, wflw, shots):
    """Bộ file thả vào tab Nạp ảnh (ngoài repo, có mặt người thật): 6 ảnh WFLW, một bản chép đổi tên có dấu và đuôi hoa,
    hai ảnh cùng tên ở hai thư mục, PNG xám không có mặt, file text đổi đuôi .jpg, một bản chép y nguyên (trùng nội dung)."""
    from PIL import Image
    d = os.path.join(shots, '_nap_in')
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    rows = read_csv_rows(os.path.join(W, 'r_list.csv'))[1:]
    picked, seen = [], set()
    for r in rows:
        sub = r[0].split('/')[0]
        if sub not in seen and os.path.exists(os.path.join(wflw, *r[0].split('/'))):
            seen.add(sub)
            picked.append(os.path.join(wflw, *r[0].split('/')))
        if len(picked) == 9:
            break
    check(len(picked) == 9, f'tìm được 9 ảnh WFLW ở 9 thư mục con khác nhau ({wflw})')
    six = []
    for src in picked[:6]:
        dst = os.path.join(d, os.path.basename(src))
        shutil.copyfile(src, dst)
        six.append(dst)
    accent = os.path.join(d, 'Ảnh mặt (1).JPG')
    with open(accent, 'wb') as f:
        f.write(open(six[0], 'rb').read() + b'\0')          # cùng ảnh nhưng khác byte: không bị coi là trùng nội dung
    same = []
    for k, src in enumerate(picked[6:8], 1):
        os.makedirs(os.path.join(d, f'thu_muc_{k}'))
        same.append(os.path.join(d, f'thu_muc_{k}', 'mat.jpg'))
        shutil.copyfile(src, same[-1])
    gray = os.path.join(d, 'xam.png')
    Image.new('RGB', (400, 400), (128, 128, 128)).save(gray)
    fake = os.path.join(d, 'gia.jpg')
    open(fake, 'w', encoding='utf-8').write('đây là file chữ, không phải ảnh\n' * 20)
    dup = os.path.join(d, 'trung.jpg')
    shutil.copyfile(six[1], dup)
    files = six + [accent] + same + [gray, fake, dup]
    return dict(files=files, n_ok=10, n_rej=2, accent=accent, six=six)


def _open_nap(pg, port):
    pg.goto(f'http://127.0.0.1:{port}/')
    pg.wait_for_selector('#tabs', timeout=30000)


def _goto_tab(pg):
    pg.get_by_role('tab', name='Nạp ảnh').click()
    pg.wait_for_selector('#nap-drop', timeout=15000)


def _drop(pg, files, n_ok, n_rej):
    pg.set_input_files('#nap-drop input[type=file]', files)
    pg.wait_for_function("([a, b]) => { const t = document.querySelector('#nap-count')?.innerText || ''; "
                         "return t.includes(a + ' ảnh hợp lệ') && t.includes(b + ' bị loại'); }", arg=[n_ok, n_rej], timeout=60000)


def phase_f(pw, W, shots, ports, wflw):
    log('\n== PHA F: tab Nạp ảnh (kéo thả -> prepare -> rà lượt mới) ==')
    port, port_nomodel, port_nap = ports
    inp = make_nap_inputs(W, wflw, shots)
    runs = os.path.join(W, 'runs')
    for d in os.listdir(runs):
        if d.upper().startswith('NAP_'):
            shutil.rmtree(os.path.join(runs, d), ignore_errors=True)
    run = os.path.join(runs, 'F5UP')
    shutil.rmtree(run, ignore_errors=True)
    shutil.copytree(os.path.join(runs, 'F5'), run)
    for d in ('review', 'push', 'xml', '_tmp'):
        shutil.rmtree(os.path.join(run, d), ignore_errors=True)
    f5_csv = os.path.join(run, 'review', 'triage_P2.csv')
    out_log = os.path.join(shots, 'app_f.log')
    p = start([sys.executable, os.path.join(CODE, 'tool', 'review_app.py'), 'runs/F5UP', 'P2'], W, port, None, out_log)
    wait_port(port, p)
    ui = Ui(pw, port)
    pg = ui.page
    try:
        # 1. rà dở F5UP: hai quyết định Nhận
        ui.open()
        pg.keyboard.press('n')
        ui.wait_done(1)
        ui.wait_cur('F_002.png')
        pg.keyboard.press('n')
        ui.wait_done(2)
        before = open(f5_csv, encoding='utf-8', newline='').read()
        check(len(read_csv_rows(f5_csv)) == 3, f'F5UP: 2 dòng quyết định sau header: {before!r}')
        # 2. mở tab Nạp ảnh, thả file
        _goto_tab(pg)
        env = pg.inner_text('#nap-env')
        check('Đủ model và cấu hình' in env, f'khung môi trường xanh: {env!r}')
        check(pg.locator('#nap-start').is_disabled(), 'chưa chọn ảnh: nút Bắt đầu khoá')
        check('NAP_001' in (pg.locator('#nap-name textarea, #nap-name input').first.get_attribute('placeholder') or ''), 'ô tên lượt gợi ý NAP_001')
        _drop(pg, inp['files'], inp['n_ok'], inp['n_rej'])
        pg.wait_for_function("document.querySelectorAll('#nap-list img').length === 10", timeout=30000)
        caps = ' | '.join(pg.locator('#nap-list .caption-label').all_inner_texts())
        check('Anh_mat_1.jpg' in caps and 'mat.jpg' in caps and 'mat_2.jpg' in caps and 'xam.png' in caps,
              f'lưới 10 ảnh hợp lệ, tên sạch Anh_mat_1, mat, mat_2: {caps[:200]}')
        check('MB' in caps or 'KB' in caps, 'chú thích có dung lượng')
        rej = pg.inner_text('#nap-rejected')
        check('gia.jpg' in rej and 'trung.jpg' in rej and 'trùng nội dung' in rej, f'danh sách bị loại có gia.jpg và trung.jpg: {rej!r}')
        check(pg.locator('#nap-start').is_enabled(), 'có ảnh hợp lệ: nút Bắt đầu bật')
        pg.locator('#nap-count').click()                 # đưa focus ra khỏi ô nhập rồi thử phím tắt của tab Rà soát
        pg.keyboard.press('n')
        pg.keyboard.press('g')
        pg.wait_for_timeout(1000)
        check(open(f5_csv, encoding='utf-8', newline='').read() == before, 'phím N/G ở tab Nạp ảnh không ghi gì vào triage của F5UP')
        pg.screenshot(path=os.path.join(shots, 'upload_01_chon_desktop.png'))
        # 3. bắt đầu
        pg.click('#nap-start')
        pg.wait_for_selector('#nap-prog .nap-label', timeout=30000)
        check(pg.locator('#nap-start').is_disabled(), 'đang chạy: nút Bắt đầu khoá')
        pg.wait_for_function("document.querySelectorAll('#nap-list img').length === 0 || !document.querySelector('#nap-list img')?.offsetParent",
                             timeout=15000)
        check('Chưa chọn ảnh nào' in pg.inner_text('#nap-count'), 'sau khi bắt đầu: vùng thả và lưới đã xoá')
        pg.click('#btn-dong')                            # prepare đang chạy: Đóng bị từ chối, không mở hộp
        pg.wait_for_function("document.querySelector('#close-msg')?.innerText.includes('Đang chuẩn bị lượt NAP_001')", timeout=10000)
        check(pg.locator('#close-confirm').count() == 0 or not pg.locator('#close-confirm').is_visible(), 'prepare đang chạy: Đóng bị từ chối, không mở hộp')
        check(p.poll() is None and pg.locator('.m28-closed').count() == 0, 'prepare đang chạy: trang và server còn nguyên sau khi bấm Đóng')
        pg.screenshot(path=os.path.join(shots, 'upload_02b_dong_bi_tu_choi.png'))
        pg.screenshot(path=os.path.join(shots, 'upload_02_dang_chay.png'))
        label = pg.inner_text('#nap-prog .nap-label')
        check(label.startswith(('Đang nạp MediaPipe', 'Bước')), f'nhãn tiến độ: {label!r}')
        pg.wait_for_selector('#nap-summary .nap-sum', timeout=300000)
        n1 = os.path.join(runs, 'NAP_001')
        names = sorted(os.listdir(os.path.join(n1, 'inbox')))
        check(len(names) == 10 and all(re.fullmatch(r'[A-Za-z0-9_-]+\.(jpg|png)', n) for n in names), f'NAP_001/inbox: 10 file tên ASCII, đuôi thường: {names}')
        check({'Anh_mat_1.jpg', 'mat.jpg', 'mat_2.jpg', 'xam.png'} <= set(names) and not any(n.startswith(('gia', 'trung')) for n in names),
              'inbox có Anh_mat_1, mat, mat_2, xam; không có gia, trung')
        check(_sha(os.path.join(n1, 'inbox', 'Anh_mat_1.jpg')) == _sha(inp['accent']), 'ảnh được chép nguyên byte (sha256 khớp)')
        tab = read_csv_rows(os.path.join(n1, 'nap_ten_goc.csv'))
        check(tab[0] == ['ten_goc', 'ten_moi', 'bytes', 'sha256'] and len(tab) == 11 and ['Ảnh mặt (1).JPG', 'Anh_mat_1.jpg'] == tab[[r[1] for r in tab].index('Anh_mat_1.jpg')][:2],
              'nap_ten_goc.csv: 10 dòng, tên gốc có dấu ghi đúng')
        check(os.path.getsize(os.path.join(n1, 'nap_log.txt')) > 0, 'nap_log.txt có nội dung')
        flags = json.load(open(os.path.join(n1, 'flags', 'flags.json'), encoding='utf-8'))
        check(len(flags) >= 5, f'flags.json có {len(flags)} mặt (>= 5)')
        nf = read_csv_rows(os.path.join(n1, 'no_face.csv'))
        check('xam' in [r[0] for r in nf[1:]], f'ảnh xám nằm trong no_face.csv: {nf[1:]}')
        summ = pg.inner_text('#nap-summary')
        check('Mặt dùng được' in summ and 'Không thấy mặt' in summ and 'Vào hàng đợi rà' in summ and 'xam.png' in summ
              and 'mặt lớn nhất' in summ and 'm28.py push --run NAP_001' in summ, f'tóm tắt có thẻ số, xam.png, ghi chú nhiều mặt, lệnh push: {summ[:160]!r}')
        check('Xong' in pg.inner_text('#nap-prog') and pg.locator('#nap-go').is_enabled(), 'nút Rà lượt này bật')
        pg.screenshot(path=os.path.join(shots, 'upload_03_ket_qua_desktop.png'), full_page=True)
        pg.set_viewport_size({'width': 420, 'height': 900})
        pg.wait_for_timeout(600)
        check(pg.evaluate('document.documentElement.scrollWidth') <= 420, f"420 px: không cuộn ngang (scrollWidth {pg.evaluate('document.documentElement.scrollWidth')})")
        check(pg.locator('#nap-go').bounding_box()['height'] >= 48, 'nút Rà lượt này đủ to ở màn hẹp')
        pg.screenshot(path=os.path.join(shots, 'upload_04_hep.png'), full_page=True)
        pg.set_viewport_size({'width': 1440, 'height': 900})
        pg.wait_for_timeout(400)
        # 5. chuyển sang NAP_001
        pg.click('#nap-go')
        pg.wait_for_function("document.title === 'Rà soát M28 · NAP_001'", timeout=60000)
        pg.wait_for_selector('#info .face-name', timeout=60000)
        pg.wait_for_function("() => { const i = document.querySelector('#big img'); return i && i.complete && i.naturalWidth > 0; }", timeout=30000)
        check('NAP_001' in pg.inner_text('#progress') and ui.progress()[1] >= 5, f'#progress ghi NAP_001: {pg.inner_text("#progress")[:60]!r}')
        ls = listeners(port)
        check(ls and all(f'127.0.0.1:{port}' in l for l in ls) and not any(f'*:{port}' in l or '0.0.0.0' in l for l in ls), 'sau khi chuyển: server vẫn chỉ bind 127.0.0.1')

        def get(path, host=None):
            req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', headers={'Host': host} if host else {})
            try:
                return urllib.request.urlopen(req, timeout=5).status
            except urllib.error.HTTPError as e:
                return e.code
        check(get('/', f'evil.example:{port}') == 400, 'sau khi chuyển: Host lạ vẫn bị 400')
        check(get('/gradio_api/file=' + os.path.abspath(os.path.join(n1, 'inbox', 'mat.jpg'))) == 403, 'inbox/ không phát được qua /file= (403)')
        check(get('/gradio_api/file=' + os.path.abspath(os.path.join(run, 'flags', 'flags.json'))) == 403, 'lượt cũ ngoài thư mục cho phép vẫn 403')
        pg.screenshot(path=os.path.join(shots, 'upload_05_sau_chuyen.png'))
        pg.keyboard.press('n')
        ui.wait_done(1)
        rows = read_csv_rows(os.path.join(n1, 'review', 'triage_P2.csv'))
        check(len(rows) == 2 and rows[1][1] == 'nhan', f'NAP_001/review/triage_P2.csv có đúng 1 dòng nhan: {rows}')
        check(open(f5_csv, encoding='utf-8', newline='').read() == before, 'triage của F5UP y nguyên sau khi chuyển và rà lượt mới')
        txt = open(out_log, encoding='utf-8').read()
        check('Chuyển sang lượt NAP_001' in txt and 'F5UP còn 3 mặt chưa rà' in txt and 'review_app.py runs\\F5UP P2' in txt,
              'cmd in lượt cũ còn 3 mặt và lệnh mở lại')
        # 4. Huỷ và Thử lại (từ trang NAP_001)
        _goto_tab(pg)
        note = pg.inner_text('#nap-oldnote')
        check('NAP_001' in note and 'chưa rà' in note and 'triage_P2.csv' in note, f'ghi chú lượt đang rà dở: {note[:120]!r}')
        check('NAP_002' in (pg.locator('#nap-name textarea, #nap-name input').first.get_attribute('placeholder') or ''), 'ô tên lượt gợi ý NAP_002')
        _drop(pg, inp['six'][:3], 3, 0)
        pg.click('#nap-start')
        pg.wait_for_function("!document.querySelector('#nap-cancel').disabled", timeout=30000)
        pg.click('#nap-cancel')
        pg.wait_for_function("(document.querySelector('#nap-summary')?.innerText || '').includes('Đã huỷ')", timeout=30000)
        n2 = os.path.join(runs, 'NAP_002')
        check(os.path.isdir(os.path.join(n2, 'inbox')) and os.path.getsize(os.path.join(n2, 'nap_log.txt')) > 0, 'NAP_002: sau Huỷ còn inbox và log')
        check(pg.locator('#nap-retry').is_enabled() and pg.locator('#nap-cancel').is_disabled() and pg.locator('#nap-go').is_disabled(),
              'sau Huỷ: Thử lại bật, Huỷ và Rà lượt này khoá')
        pg.click('#nap-retry')
        pg.wait_for_selector('#nap-summary .nap-sum', timeout=300000)
        check(len(json.load(open(os.path.join(n2, 'flags', 'flags.json'), encoding='utf-8'))) >= 2, 'Thử lại: NAP_002 chạy xong, có flags.json')
        pg.screenshot(path=os.path.join(shots, 'upload_07_huy_thu_lai.png'), full_page=True)
        check(ui.external() == [], 'không có request ra ngoài 127.0.0.1')
        check(not ui.errors or all('Failed to load resource' in e or 'ERR_' in e or 'WebSocket' in e for e in ui.errors), f'không lỗi JS: {ui.errors[:3]}')
    finally:
        ui.close()
        p.terminate()
        try:
            p.wait(timeout=20)
        except subprocess.TimeoutExpired:
            p.kill()
    # 6. thiếu model
    W2 = os.path.join(os.path.dirname(W), 'work_nomodel')
    shutil.rmtree(W2, ignore_errors=True)
    os.makedirs(W2)
    shutil.copytree(os.path.join(W, 'config'), os.path.join(W2, 'config'))
    p = start([sys.executable, os.path.join(CODE, 'tool', 'review_app.py'), '--nap', 'P2'], W2, port_nomodel, None, os.path.join(shots, 'app_f2.log'))
    wait_port(port_nomodel, p)
    ui = Ui(pw, port_nomodel)
    pg = ui.page
    try:
        _open_nap(pg, port_nomodel)
        pg.wait_for_selector('#nap-drop', timeout=30000)                   # chế độ --nap: tab Nạp ảnh mở sẵn
        env = pg.inner_text('#nap-env')
        check('Thiếu face_landmarker.task' in env and 'curl' in env, f'khung đỏ báo thiếu model kèm lệnh curl: {env[:120]!r}')
        pg.set_input_files('#nap-drop input[type=file]', inp['six'][:1])
        pg.wait_for_function("(document.querySelector('#nap-count')?.innerText || '').includes('1 ảnh hợp lệ')", timeout=30000)
        check(pg.locator('#nap-start').is_disabled(), 'thiếu model: nút Bắt đầu vẫn khoá dù có ảnh')
        pg.get_by_role('tab', name='Rà soát').click()
        check('Chưa có lượt nào' in pg.inner_text('#tab-ra'), 'tab Rà soát ghi "Chưa có lượt nào"')
        pg.get_by_role('tab', name='Nạp ảnh').click()
        pg.screenshot(path=os.path.join(shots, 'upload_06_thieu_model.png'))
        box = open_close_box(pg)                         # chế độ --nap (chưa có lượt): hộp xác nhận đơn giản, đóng được ở mọi tab
        check('Đóng trang rà soát?' in box and 'chưa bấm Xong' not in box, f'--nap: hộp Đóng đơn giản: {box!r}')
        confirm_close(pg)
        check(p.wait(timeout=15) == 0, '--nap: xác nhận Đóng, tiến trình thoát mã 0')
    finally:
        ui.close()
        p.terminate()
    check([d for d in os.listdir(os.path.join(W2, 'runs')) if d.startswith('NAP_')] == [], 'thiếu model: không có thư mục NAP_xxx')
    # 7. --nap có model: từ trang trống nạp ảnh rồi chuyển sang rà
    W3 = os.path.join(os.path.dirname(W), 'work_nap')
    shutil.rmtree(W3, ignore_errors=True)
    os.makedirs(W3)
    shutil.copytree(os.path.join(W, 'config'), os.path.join(W3, 'config'))
    shutil.copyfile(os.path.join(W, 'face_landmarker.task'), os.path.join(W3, 'face_landmarker.task'))
    p = start([sys.executable, os.path.join(CODE, 'tool', 'review_app.py'), '--nap', 'P2'], W3, port_nap, None, os.path.join(shots, 'app_f3.log'))
    wait_port(port_nap, p)
    ui = Ui(pw, port_nap)
    pg = ui.page
    try:
        _open_nap(pg, port_nap)
        pg.wait_for_selector('#nap-drop', timeout=30000)
        check(pg.title() == 'Rà soát M28 · Nạp ảnh' and 'Đủ model và cấu hình' in pg.inner_text('#nap-env'), 'chế độ --nap: tiêu đề và môi trường đủ')
        _drop(pg, inp['six'][:4], 4, 0)
        pg.fill('#nap-name textarea, #nap-name input', 'KHACH_A')
        pg.click('#nap-start')
        pg.wait_for_selector('#nap-summary .nap-sum', timeout=300000)
        pg.click('#nap-go')
        pg.wait_for_function("document.title === 'Rà soát M28 · KHACH_A'", timeout=60000)
        pg.wait_for_selector('#info .face-name', timeout=60000)
        check(os.path.isdir(os.path.join(W3, 'runs', 'KHACH_A', 'inbox')) and ui.progress()[1] >= 3, f'từ trang trống sang lượt KHACH_A: {ui.progress()}')
        check(not os.path.exists(os.path.join(W3, 'runs', 'KHACH_A', 'review', 'triage_P2.csv')), 'chưa bấm gì thì chưa có triage')
        pg.screenshot(path=os.path.join(shots, 'upload_08_nap_sang_ra.png'))
    finally:
        ui.close()
        p.terminate()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--work', required=True, help='thư mục chạy có config/, runs/F5, runs/ALL616')
    ap.add_argument('--shots', required=True, help='thư mục lưu ảnh chụp (ngoài repo: có mặt người)')
    ap.add_argument('--phases', default='ABCDEF')
    ap.add_argument('--wflw', help='thư mục WFLW_images (mặc định <work>/../wflw/WFLW_images), cho pha F')
    a = ap.parse_args()
    W, shots = os.path.abspath(a.work), os.path.abspath(a.shots)
    os.makedirs(shots, exist_ok=True)
    from playwright.sync_api import sync_playwright
    t0 = time.time()
    try:
        with sync_playwright() as pw:
            tri = None
            if 'A' in a.phases:
                tri = phase_a(pw, W, shots, (7871, 7872))
            if 'B' in a.phases:
                phase_b(pw, W, shots, 7873, tri or steps.read_triage(os.path.join(W, 'runs', 'F5UI', 'review', 'triage_P2.csv')))
            if 'C' in a.phases:
                phase_c(pw, W, shots, 7874)
            if 'D' in a.phases:
                phase_d(pw, W, shots, 7875)
            if 'E' in a.phases:
                phase_e(pw, W, shots, 7876)
            if 'F' in a.phases:
                phase_f(pw, W, shots, (7877, 7878, 7879), a.wflw or os.path.join(os.path.dirname(W), 'wflw', 'WFLW_images'))
    except (AssertionError, RuntimeError) as e:
        log(f'\nHỎNG: {e}')
        return 1
    finally:
        stop_all()
    log(f'\nQUA hết các pha {a.phases} sau {time.time() - t0:.0f}s. Ảnh chụp ở {shots}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
