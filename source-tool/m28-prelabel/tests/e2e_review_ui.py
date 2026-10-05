"""Kiểm thử đầu-cuối trang rà soát bằng trình duyệt thật (Chromium qua Playwright). TUỲ CHỌN.

Cần playwright và Chromium, KHÔNG nằm trong requirements, pytest không gom file này (tên không khớp test_*.py).
Chỉ chạy trên Linux (dùng `lsof` để kiểm cổng chỉ bind 127.0.0.1, và `strace` nếu có để liệt kê mọi connect() của server).
Cần một thư mục chạy (--work) có config/, data/ (hoặc không), runs/F5 (5 mặt, đã prepare) và runs/ALL616 (616 mặt, đã prepare);
các lượt này chứa ảnh WFLW nên chỉ để ngoài git. Ví dụ (Linux cloud):

    PYTHONPATH=$S/pwlib PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \\
        python tests/e2e_review_ui.py --work $W --shots $S/ui_shots

Bốn pha:
  A  chạy app thẳng trên bản chép F5UI: phím tắt, hoàn tác, đóng giữa chừng (kill) rồi mở lại, màn hẹp 800 px, nút Xong tự tắt trang,
     không có request ra ngoài 127.0.0.1, server chỉ bind 127.0.0.1 (đặt proxy chết để chứng minh không cần mạng).
  B  qua m28 thật: `m28.py review --force review` rồi `push --dry-run`, XML/manual_list/rejected khớp CSV.
  C  độ mượt trên ALL616 (616 mặt): mở trang, một quyết định, đổi trang; xoá triage_E2E.csv sau khi đo.
  D  (thêm) lỗi ghi CSV (giả lập Excel khoá file bằng cách đặt một thư mục vào chỗ file): báo "Không ghi được", giữ nguyên mặt, sửa xong bấm lại thì ghi được.
Mọi tiến trình đã mở được dọn ở `finally`. Cổng 7871–7875, M28_NO_BROWSER=1.
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
import sys
import time
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


# ---------- tiến trình ----------
def start(cmd, cwd, port, extra_env=None, out=None):
    env = dict(os.environ, GRADIO_SERVER_PORT=str(port), M28_NO_BROWSER='1', PYTHONUNBUFFERED='1')
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
        pg.click('#btn-xong')
        t = time.time()
        pg.wait_for_function("document.querySelector('#msg').innerText.includes('done.txt')")
        check(os.path.exists(os.path.join(run, 'review', 'done.txt')), 'bấm Xong: review/done.txt xuất hiện')
        code = p.wait(timeout=10)
        check(code == 0, f'tiến trình tự thoát mã 0 sau {time.time() - t:.1f}s')
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
        ui.page.click('#btn-xong')
        ui.page.wait_for_function("document.querySelector('#msg').innerText.includes('done.txt')")
    finally:
        ui.close()
    code = p.wait(timeout=20)
    text = open(out, encoding='utf-8').read()
    check(code == 0 and 'đã đóng mà chưa bấm Xong' not in text, f'm28 review thoát mã {code}, không in "Trang rà soát đã đóng mà chưa bấm Xong"')
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--work', required=True, help='thư mục chạy có config/, runs/F5, runs/ALL616')
    ap.add_argument('--shots', required=True, help='thư mục lưu ảnh chụp (ngoài repo: có mặt người)')
    ap.add_argument('--phases', default='ABCD')
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
    except (AssertionError, RuntimeError) as e:
        log(f'\nHỎNG: {e}')
        return 1
    finally:
        stop_all()
    log(f'\nQUA hết các pha {a.phases} sau {time.time() - t0:.0f}s. Ảnh chụp ở {shots}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
