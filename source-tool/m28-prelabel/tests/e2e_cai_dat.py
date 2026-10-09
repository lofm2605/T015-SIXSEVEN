"""Kiểm thử đầu-cuối tab "Cài đặt" (CVAT, người rà, đường dẫn, t_flip) bằng Chromium thật (Playwright) + CVAT GIẢ. TUỲ CHỌN.

Cần playwright và Chromium (KHÔNG chạy `playwright install`), MediaPipe thật (pha E nạp ảnh thật), ảnh in-cabin thật; pytest không gom file này
(tên không khớp test_*.py). Thư mục --work có config/ (m28_config.json, map_mp50.json, face50_label.json, pipeline.json), face_landmarker.task,
r_list.csv và runs/F5 (lượt 5 mặt in-cabin). Ví dụ:

    PYTHONPATH=$S/pwlib PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \\
        python tests/e2e_cai_dat.py --work $S/work --imgs $S/incab_data/frames --shots $S/ui_shots

Cách làm việc (không đụng thư mục --work): dựng thư mục riêng <shots>/cd_work (chép config/, liên kết model, chép runs/F5 thành CD1/CD2/CD3 đã rà
xong hoặc chưa) và thư mục hồ sơ giả <shots>/cd_home (HOME, APPDATA, XDG_CONFIG_HOME trỏ vào đó, M28_CONFIG_DIR rỗng) nên không có gì ghi vào hồ sơ
thật. CVAT GIẢ: PYTHONPATH=tests/fake_cvat, M28_FAKE_CVAT_STATE=<file>; KHÔNG đặt CVAT_URL/CVAT_ACCESS_TOKEN trừ pha C. KHÔNG có CVAT thật:
kết quả chỉ chứng minh logic trang và tiến trình con, không chứng minh server CVAT thật.

Các pha (mỗi pha một lần khởi động trang, cổng 7891-7899, M28_NO_BROWSER=1, mọi tiến trình dọn ở finally):
  A  chưa có token: nút Đẩy khoá -> tab Cài đặt: link sai bị từ chối, Show / Hide token, Save (không Nhớ), ô token rỗng, nguồn "nhập trong phiên này", không có
     cvat.json -> Test CVAT connection (2.77.0, username, project) -> nút Đẩy mở khoá không cần mở lại cmd -> đẩy lên CVAT giả (tiến trình con nhận token qua
     môi trường) -> đường dẫn (Check, Save), người rà (Save name, áp dụng từ lượt sau) -> t_flip (hộp xác nhận, Cancel, Esc, xác nhận, Set null) -> bố cục 1400/420 px
  B  Nhớ trên máy này: cvat.json 0600 -> khởi động lại: nguồn "đã lưu trên máy", nút Đẩy mở khoá ngay
  C  khởi động với biến môi trường + file đã lưu: nguồn "từ biến môi trường"; Forget token (Esc, rồi xác nhận): file mất, token biến môi trường còn
  D  không còn gì: nút Đẩy khoá; Save -> mở; Forget token -> khoá lại
  E  sai token (auth_fail) và khác phiên bản (2.70.0): thông báo đúng nguyên nhân
  F  phím tắt n/g/b/z/k trong các ô của tab Cài đặt không ghi gì vào triage (đối chứng: ở tab Rà soát phím n vẫn ghi)
  G  --images: lượt nạp ảnh thật, ảnh gốc bị chuyển đi -> nút Đẩy khoá -> cài thư mục ảnh -> mở khoá -> đẩy (task dùng ảnh ở thư mục đã cài)
Cuối cùng grep token giả trong HTML, log app, runs/, outputs/, state CVAT giả, mọi file tạm: chỉ được thấy trong cvat.json khi Nhớ bật.
Ảnh chụp: <shots>/caidat_*.png (chỉ chụp khi ô token rỗng và ở chế độ ẩn; có thể có mặt người thật trong lượt F5: để ngoài git).
"""
import argparse
import csv
import itertools
import json
import os
import shutil
import site
import stat
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(CODE, 'tool'))
import e2e_review_ui as base  # noqa: E402
from e2e_review_ui import check, log, read_csv_rows, start, stop_all, wait_port  # noqa: E402
import e2e_dot_push as dp  # noqa: E402

TOKEN, TOKEN2, TOKEN_ENV = 'tok-TEST-123456', 'tok-OTHER-654321', 'tok-ENVV-777777'
URL = 'http://localhost:8080'
FAKE = os.path.join(CODE, 'tests', 'fake_cvat')
SECRETS = (TOKEN, TOKEN2, TOKEN_ENV)
HTML_SEEN = []                                              # mọi HTML đã thấy, để grep cuối cùng


class Env:
    """Thư mục làm việc riêng và hồ sơ giả của e2e."""

    def __init__(self, W, shots):
        self.src, self.shots = W, shots
        self.work = os.path.join(shots, 'cd_work')
        self.home = os.path.join(shots, 'cd_home')
        self.state = os.path.join(shots, 'cd_fake_state.json')
        self.cfg = os.path.join(self.home, 'm28')              # XDG_CONFIG_HOME = home -> <home>/m28
        for d in (self.work, self.home):
            shutil.rmtree(d, ignore_errors=True)
        for f in (self.state,):
            if os.path.exists(f):
                os.remove(f)
        os.makedirs(os.path.join(self.work, 'runs'))
        shutil.copytree(os.path.join(W, 'config'), os.path.join(self.work, 'config'))
        for f in ('face_landmarker.task', 'r_list.csv'):
            shutil.copy(os.path.join(W, f), os.path.join(self.work, f))
        os.makedirs(self.home)
        self.src_config_bytes = open(os.path.join(W, 'config', 'm28_config.json'), 'rb').read()
        shutil.copy(os.path.join(CODE, 'config', 'm28_config.json'), os.path.join(self.work, 'config', 'm28_config.json'))      # bản của repo (t_flip null)
        self.config_bytes = open(os.path.join(self.work, 'config', 'm28_config.json'), 'rb').read()

    def make_run(self, name, decided=True):
        import review_app as ra
        dst = os.path.join(self.work, 'runs', name)
        shutil.copytree(os.path.join(self.src, 'runs', 'F5'), dst, ignore=shutil.ignore_patterns('push', 'xml', 'review', '_tmp', '.dang_chay', 'done.txt'))
        if decided:
            os.makedirs(os.path.join(dst, 'review'), exist_ok=True)
            with open(os.path.join(dst, 'review', 'triage_E2E.csv'), 'w', encoding='utf-8', newline='') as f:
                w = csv.writer(f)
                w.writerow(['name', 'decision', 'reason', 'seconds'])
                for face in ra.load_queue(dst):
                    w.writerow([face.file, 'nhan' if face.has_draft else 'gan_tay', '', '1'])
        return dst

    def app_env(self, cvat=None, control=None):
        e = {'PYTHONPATH': FAKE + os.pathsep + os.environ.get('PYTHONPATH', ''), 'M28_FAKE_CVAT_STATE': self.state,
             'HOME': self.home, 'XDG_CONFIG_HOME': self.home, 'APPDATA': self.home, 'USERPROFILE': self.home, 'M28_CONFIG_DIR': '',
             'PYTHONUSERBASE': site.getuserbase(),        # HOME giả không được làm mất các gói cài ở thư mục người dùng thật
             'CVAT_URL': '', 'CVAT_ACCESS_TOKEN': '', 'CVAT_ORG': '', 'M28_FAKE_CVAT_CONTROL': json.dumps(control) if control else ''}
        e.update(cvat or {})
        return e


class App:
    def __init__(self, pw, env, run, port, name, nap=False, w=1440, h=900):
        self.env, self.port = env, port
        self.log_path = os.path.join(env.shots, f'app_cd_{name}.log')
        args = ['--nap', 'E2E'] if nap else [os.path.join('runs', run), 'E2E']
        self.proc = start([sys.executable, os.path.join(CODE, 'tool', 'review_app.py')] + args, env.work, port, self.env_vars, self.log_path)
        wait_port(port, self.proc)
        self.ui = base.Ui(pw, port, w, h)
        self.pg = self.ui.page
        self.pg.goto(f'http://127.0.0.1:{port}/')
        self.pg.wait_for_selector('#tabs', timeout=30000)
        if not nap:
            self.pg.wait_for_selector('#btn-push', timeout=30000)
            self.pg.wait_for_function("(document.querySelector('#push-panel')?.innerText || '').length > 0 || !document.querySelector('#btn-push').disabled", timeout=20000)

    env_vars = None

    def stop(self):
        try:
            self.ui.close()
        finally:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def html(self):
        h = self.pg.content()
        HTML_SEEN.append(h)
        for t in SECRETS:
            if t in h:
                raise AssertionError(f'token {t!r} có trong HTML của trang')
        return h


PORTS = None


def launch(pw, env, run, port, name, cvat=None, control=None, nap=False, w=1440, h=900):
    """Khởi động trang trên MỘT CỔNG MỚI (cổng truyền vào chỉ để đọc cho rõ; mỗi lần khởi động dùng cổng kế tiếp, không dùng lại)."""
    App.env_vars = env.app_env(cvat, control)
    return App(pw, env, run, next(PORTS), name, nap, w, h)


def to_settings(pg):
    pg.get_by_role('tab', name='Cài đặt').click()
    pg.wait_for_selector('#cd-token input', timeout=20000)
    pg.wait_for_function("(() => { const t = document.querySelector('#cd-cvat-status')?.innerText || ''; return t.includes('○') || t.includes('●'); })()", timeout=20000)


def to_review(pg):
    pg.get_by_role('tab', name='Rà soát').click()
    pg.wait_for_selector('#btn-push', timeout=20000)


def fill(pg, eid, text):
    pg.fill(f'#{eid} input, #{eid} textarea', text)


def txt(pg, sel):
    return pg.inner_text(sel).replace('\xa0', ' ')


def wait_in(pg, sel, text, timeout=30000):
    pg.wait_for_function("([s, t]) => (document.querySelector(s)?.innerText || '').includes(t)", arg=[sel, text], timeout=timeout)


def push_enabled(pg):
    return pg.locator('#btn-push').is_enabled()


def wait_push(pg, enabled, timeout=20000):
    pg.wait_for_function("e => { const b = document.querySelector('#btn-push'); return !!b && (!b.disabled) === e; }", arg=enabled, timeout=timeout)


def token_box_ok(pg):
    v = pg.evaluate("(() => { const el = document.querySelector('#cd-token input'); return el ? [el.type, el.value] : null; })()")
    return v == ['password', '']


def overflow(pg):
    return pg.evaluate('document.documentElement.scrollWidth - window.innerWidth')


def file_text(path):
    return open(path, encoding='utf-8').read() if os.path.exists(path) else None


def mode_of(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def modal_open(pg, sel):
    pg.wait_for_selector(sel, timeout=15000)
    pg.wait_for_timeout(500)


# ---------------------------------------------------------------- pha A
def snap(pg, E, name):
    """Chụp ảnh CHỈ khi ô token đang rỗng và ở chế độ ẩn (kiểm bằng DOM)."""
    check(token_box_ok(pg), f'ô token rỗng và ở chế độ ẩn trước khi chụp {name}')
    pg.screenshot(path=os.path.join(E.shots, name), full_page=True)


def phase_a(pw, E, port):
    log('\n== PHA A: chưa có token -> Cài đặt -> đẩy ==')
    run = E.make_run('CD1')
    triage = os.path.join(run, 'review', 'triage_E2E.csv')
    triage0 = file_text(triage)
    app = launch(pw, E, 'CD1', port, 'a')
    pg = app.pg
    try:
        # 1. nút Đẩy khoá vì thiếu CVAT
        wait_in(pg, '#push-panel', 'Thiếu CVAT_URL và CVAT_ACCESS_TOKEN')
        check(pg.locator('#btn-push').is_disabled(), 'chưa có link/token: nút Đẩy lên CVAT khoá')
        t = txt(pg, '#push-panel')
        check('tab Cài đặt' in t and 'set CVAT_URL=http://localhost:8080' in t, f'hướng dẫn: tab Cài đặt (cách chính) và set trong cmd (thay thế): {t[:160]!r}')
        check(pg.locator('#push-panel input, #push-panel textarea').count() == 0, 'khung Đẩy lên CVAT không có ô nhập nào')
        check(pg.locator('#tab-ra input[type=password]').count() == 0, 'tab Rà soát không có ô password')
        tabs = pg.eval_on_selector_all('#tabs [role=tab]', 'e => e.map(x => x.innerText.trim())')
        check(tabs[-1] == 'Cài đặt' and tabs[:5] == ['Rà soát', 'Nạp ảnh', 'Các đợt', 'Ca khó', 'Họp team'], f'tab Cài đặt ở cuối, tab cũ giữ chỗ: {tabs}')
        check(pg.locator('#tab-ra').is_visible(), 'tab mặc định vẫn là Rà soát')
        # 2. tab Cài đặt
        to_settings(pg)
        check(pg.locator('#cd-token input[type=password]').count() == 1, 'ô token duy nhất, type=password, nằm ở tab Cài đặt')
        st = txt(pg, '#cd-cvat-status')
        check('○ Chưa có link/token' in st, f'trạng thái ban đầu: {st[:60]!r}')
        check(not os.path.exists(E.cfg), 'chưa Save: chưa có thư mục cài đặt nào')
        for bad, want in (('localhost:8080', 'phải bắt đầu bằng http'), ('file:///etc/passwd', 'Chỉ nhận link http'), ('http://u:p@localhost:8080', 'tên đăng nhập')):
            fill(pg, 'cd-url', bad)
            fill(pg, 'cd-token', TOKEN)
            pg.click('#cd-save')
            wait_in(pg, '#cd-cvat-msg', want)
            log(f'  ok   link {bad!r} bị từ chối: {txt(pg, "#cd-cvat-msg")[:70]!r}')
        check('○ Chưa có link/token' in txt(pg, '#cd-cvat-status') and not os.path.exists(E.cfg), 'link sai: không đổi gì, không ghi file')
        fill(pg, 'cd-url', 'http://cvat.example.com')
        fill(pg, 'cd-token', TOKEN)
        pg.click('#cd-save')
        wait_in(pg, '#cd-cvat-msg', 'KHÔNG mã hoá')
        pg.click('#cd-forget')
        modal_open(pg, '#cd-forget-confirm')
        pg.click('#cd-forget-ok')
        wait_in(pg, '#cd-cvat-msg', 'Đã quên')
        check('KHÔNG mã hoá' not in txt(pg, '#cd-cvat-msg'), 'link http ra ngoài mạng nội bộ: có cảnh báo, rồi Quên để làm lại từ đầu')
        # 3. nhập hợp lệ, Show / Hide, Save (Nhớ TẮT)
        fill(pg, 'cd-url', URL + '/')
        fill(pg, 'cd-token', TOKEN)
        check(pg.get_attribute('#cd-token input', 'type') == 'password', 'ô token ban đầu ở chế độ ẩn')
        pg.click('#cd-eye')
        check(pg.get_attribute('#cd-token input', 'type') == 'text' and pg.input_value('#cd-token input') == TOKEN, 'nút hiện/ẩn: đổi sang text ngay ở trình duyệt, giá trị đang gõ giữ nguyên')
        n_req = len(app.ui.requests)
        pg.click('#cd-eye')
        check(pg.get_attribute('#cd-token input', 'type') == 'password' and len(app.ui.requests) == n_req, 'bấm lần hai: về password, không gọi server')
        check(pg.locator('#cd-remember input[type=checkbox]').is_checked() is False, 'ô "Nhớ trên máy này" TẮT mặc định')
        pg.click('#cd-save')
        wait_in(pg, '#cd-cvat-msg', 'Đã lưu cho phiên này')
        pg.wait_for_function("() => document.querySelector('#cd-token input')?.value === ''", timeout=10000)
        ph = pg.get_attribute('#cd-token input', 'placeholder')
        check(token_box_ok(pg) and '••••3456' in ph and TOKEN not in ph, f'sau Save: ô token rỗng, type=password, placeholder che: {ph!r}')
        st = txt(pg, '#cd-cvat-status')
        check('••••3456' in st and 'nhập trong phiên này' in st and '○ Chưa thử' in st and TOKEN not in st, f'trạng thái: {st!r}')
        check(pg.input_value('#cd-url input') == URL, 'ô link chuẩn hoá (bỏ / cuối)')
        check(not os.path.exists(E.cfg) or not os.path.exists(os.path.join(E.cfg, 'cvat.json')), 'Nhớ TẮT: KHÔNG có cvat.json')
        app.html()
        # 4. thử kết nối
        pg.click('#cd-test')
        wait_in(pg, '#cd-cvat-msg', 'Kết nối được', 60000)
        mt = txt(pg, '#cd-cvat-msg')
        check('2.77.0' in mt and 'm28-fake-user' in mt and 'project m28: chưa có' in mt, f'Test CVAT connection: phiên bản, tài khoản, project: {mt[:200]!r}')
        pg.wait_for_function("(document.querySelector('#cd-cvat-status')?.innerText || '').includes('● Đã kết nối')", timeout=10000)
        check('thử lúc' in txt(pg, '#cd-cvat-status'), 'chip "● Đã kết nối" kèm giờ thử')
        calls = [c['m'] for c in dp.fake_state(E.state)['calls']]
        check('users.retrieve_current_user' in calls and 'projects.list' in calls and not any(m in calls for m in ('projects.create', 'tasks.create_from_data')),
              'Test CVAT connection chỉ ĐỌC trên CVAT giả (không tạo gì)')
        mk = [c for c in dp.fake_state(E.state)['calls'] if c['m'] == 'make_client']
        check(mk and all(c['kwargs'].get('access_token') == '<redacted>' for c in mk), 'make_client: token được ghi là <redacted> (token đến SDK qua môi trường tiến trình con)')
        app.html()
        snap(pg, E, 'caidat_ok_desktop.png')
        # 5. quay lại Rà soát: nút Đẩy mở khoá
        to_review(pg)
        wait_push(pg, True)
        check('Sẵn sàng đẩy' in txt(pg, '#push-panel') and 'Thiếu CVAT' not in txt(pg, '#push-panel'), 'đã Save: nút Đẩy mở khoá, không mở lại cmd')
        check(file_text(triage) == triage0, 'chưa ghi gì vào triage_E2E.csv')
        # 6. đẩy lên CVAT giả: tiến trình con nhận token qua môi trường
        pg.click('#btn-push')
        modal_open(pg, '#push-confirm')
        check(URL in pg.inner_text('#push-confirm') and TOKEN not in pg.inner_text('#push-confirm'), 'hộp xác nhận ghi link, không có token')
        pg.click('#push-confirm-ok')
        pg.wait_for_selector('#push-panel .push-done', timeout=180000)
        st = dp.fake_state(E.state)
        check([t['name'] for t in st['tasks']] == ['demo-CD1'], f'CVAT giả có task demo-CD1: {[t["name"] for t in st["tasks"]]}')
        check(dp.n_calls(E.state, 'make_client') >= 2, 'tiến trình con push đã gọi make_client (nhận được token)')
        log_txt = file_text(os.path.join(run, 'push_log.txt')) or ''
        check(TOKEN not in log_txt and len(log_txt) > 0, 'push_log.txt không chứa token')
        app.html()
        # 7. đường dẫn
        to_settings(pg)
        imgs_dir = E.imgs
        fill(pg, 'cd-images', f'  "{imgs_dir}"  ')
        pg.click('#cd-images-check')
        wait_in(pg, '#cd-images-msg', 'Thấy', 30000)
        mt = txt(pg, '#cd-images-msg')
        check('Ổn' in mt and 'ảnh' in mt and 'thư mục con' in mt and 'Ví dụ:' in mt, f'Check thư mục ảnh (có ngoặc kép và khoảng trắng): {mt[:140]!r}')
        check(not os.path.exists(os.path.join(E.cfg, 'cai_dat.json')), 'chỉ Check: chưa lưu gì')
        fill(pg, 'cd-images', 'Z:\\khong\\co\\frames')
        pg.click('#cd-images-check')
        wait_in(pg, '#cd-images-msg', 'Không thấy')
        pg.click('#cd-images-save')
        wait_in(pg, '#cd-images-msg', 'Chưa lưu')
        check(not os.path.exists(os.path.join(E.cfg, 'cai_dat.json')), 'đường dẫn không tồn tại: không lưu')
        fill(pg, 'cd-images', imgs_dir)
        pg.click('#cd-images-save')
        wait_in(pg, '#cd-images-msg', 'Đã lưu thư mục ảnh')
        fill(pg, 'cd-model', os.path.join(E.work, 'face_landmarker.task'))
        pg.click('#cd-model-check')
        wait_in(pg, '#cd-model-msg', 'MB', 30000)
        mt = txt(pg, '#cd-model-msg')
        check('Ổn' in mt and '3,' in mt, f'Check model: {mt[:120]!r}')
        pg.click('#cd-model-save')
        wait_in(pg, '#cd-model-msg', 'Đã lưu đường dẫn model')
        prefs = json.load(open(os.path.join(E.cfg, 'cai_dat.json'), encoding='utf-8'))
        check(prefs['images_dir'] == imgs_dir and prefs['model_path'].endswith('face_landmarker.task') and prefs['version'] == 1, f'cai_dat.json: {prefs}')
        check('cvat.json' not in os.listdir(E.cfg), 'cvat.json vẫn không có (Nhớ tắt)')
        snap(pg, E, 'caidat_paths_desktop.png')
        # 8. người rà
        fill(pg, 'cd-reviewer', 'P 7')
        pg.click('#cd-reviewer-save')
        wait_in(pg, '#cd-reviewer-msg', 'không hợp lệ')
        fill(pg, 'cd-reviewer', 'P7')
        pg.click('#cd-reviewer-save')
        wait_in(pg, '#cd-reviewer-msg', 'Đã lưu tên người rà mặc định: P7')
        it = txt(pg, '#cd-reviewer-info')
        check('triage_E2E.csv' in it and 'từ lượt sau dùng P7' in it, f'giải thích: lượt đang mở vẫn ghi triage_E2E.csv, từ lượt sau dùng P7: {it[:200]!r}')
        check(json.load(open(os.path.join(E.cfg, 'cai_dat.json'), encoding='utf-8'))['reviewer'] == 'P7' and file_text(triage) == triage0, 'cai_dat.json ghi P7; triage_E2E.csv không đổi')
        # 9. t_flip
        cfgp = os.path.join(E.work, 'config', 'm28_config.json')
        ti = txt(pg, '#cd-tflip-info')
        check('chưa đặt (null): mọi cờ = false' in ti and 'mattrai_1' in ti and '0,0672' in ti, f'thông tin t_flip: {ti[:120]!r}')
        fill(pg, 'cd-tflip', '-1')
        pg.click('#cd-tflip-set')
        wait_in(pg, '#cd-tflip-msg', 'lớn hơn 0')
        fill(pg, 'cd-tflip', '0,0672')
        pg.click('#cd-tflip-set')
        modal_open(pg, '#cd-tflip-confirm')
        mt = txt(pg, '#cd-tflip-confirm')
        check('đóng băng 12/10' in mt and '--force flags autoqc overlays' in mt and '0,0672' in mt, f'hộp xác nhận t_flip: {mt[:160]!r}')
        check(pg.evaluate('document.activeElement && document.activeElement.id') == 'cd-tflip-cancel', 'nút Cancel là mặc định (có focus)')
        snap(pg, E, 'caidat_tflip_modal.png')
        pg.keyboard.press('Escape')
        pg.wait_for_function("() => !document.querySelector('#cd-tflip-confirm')", timeout=15000)
        check(open(cfgp, 'rb').read() == E.config_bytes, 'Esc: config không đổi')
        pg.click('#cd-tflip-set')
        modal_open(pg, '#cd-tflip-confirm')
        pg.click('#cd-tflip-cancel')
        pg.wait_for_function("() => !document.querySelector('#cd-tflip-confirm')", timeout=15000)
        check(open(cfgp, 'rb').read() == E.config_bytes, 'Cancel: config không đổi')
        pg.click('#cd-tflip-set')
        modal_open(pg, '#cd-tflip-confirm')
        pg.click('#cd-tflip-ok')
        wait_in(pg, '#cd-tflip-msg', 'Đã ghi')
        mt = txt(pg, '#cd-tflip-msg')
        check('CD1' in mt and 'ngưỡng CŨ' in mt, f'liệt kê lượt đã có flags.json: {mt[:200]!r}')
        new = json.load(open(cfgp, encoding='utf-8'))
        old = json.loads(E.config_bytes.decode('utf-8'))
        check(new['t_flip'] == 0.0672 and {k: v for k, v in new.items() if k != 't_flip'} == {k: v for k, v in old.items() if k != 't_flip'} and list(new) == list(old),
              'xác nhận: t_flip = 0.0672, mọi trường khác và thứ tự khoá giữ nguyên (ghi trên bản sao)')
        check('0,0672' in txt(pg, '#cd-tflip-info'), 'thông tin t_flip cập nhật')
        pg.click('#cd-tflip-null')
        modal_open(pg, '#cd-tflip-confirm')
        pg.click('#cd-tflip-ok')
        pg.wait_for_function("() => (document.querySelector('#cd-tflip-info')?.innerText || '').includes('chưa đặt')", timeout=15000)
        check(open(cfgp, 'rb').read() == E.config_bytes, 'Set null: config về đúng từng byte ban đầu')
        # 10. bố cục
        app.html()
        check(overflow(pg) <= 0, f'1440 px: không cuộn ngang ({overflow(pg)})')
        fill(pg, 'cd-url', URL)
        check(token_box_ok(pg), 'ô token rỗng và ẩn trước khi chụp')
        pg.click('#cd-test')
        wait_in(pg, '#cd-cvat-msg', 'Kết nối được', 60000)
        snap(pg, E, 'caidat_desktop.png')
        pg.set_viewport_size({'width': 420, 'height': 900})
        pg.wait_for_timeout(600)
        check(overflow(pg) <= 1, f'420 px: không cuộn ngang ({overflow(pg)})')
        snap(pg, E, 'caidat_narrow.png')
        fill(pg, 'cd-images', 'D:\\m28\\' + 'rat_dai_' * 12 + 'frames')
        pg.click('#cd-images-check')
        wait_in(pg, '#cd-images-msg', 'Không thấy')
        pg.wait_for_timeout(300)
        check(overflow(pg) <= 1, f'420 px, đường dẫn rất dài: không cuộn ngang ({overflow(pg)})')
        snap(pg, E, 'caidat_narrow_longpath.png')
        pg.set_viewport_size({'width': 1440, 'height': 900})
        check(file_text(triage) == triage0, 'cả pha A: triage_E2E.csv không đổi')
    finally:
        app.stop()


# ---------------------------------------------------------------- pha B
def phase_b(pw, E, port):
    log('\n== PHA B: Nhớ trên máy này, khởi động lại ==')
    E.make_run('CD2')
    shutil.rmtree(E.cfg, ignore_errors=True)
    app = launch(pw, E, 'CD2', port, 'b')
    pg = app.pg
    try:
        wait_push(pg, False)
        to_settings(pg)
        fill(pg, 'cd-url', URL)
        fill(pg, 'cd-token', TOKEN)
        pg.locator('#cd-remember input[type=checkbox]').check()
        pg.click('#cd-save')
        wait_in(pg, '#cd-cvat-msg', 'Nhớ trên máy này')
        pth = os.path.join(E.cfg, 'cvat.json')
        check(os.path.isfile(pth) and json.load(open(pth, encoding='utf-8')) == dict(version=1, url=URL, token=TOKEN, org=''), 'cvat.json có link và token (đúng nơi này, ngoài repo)')
        check(mode_of(pth) == 0o600 and mode_of(E.cfg) == 0o700, f'quyền: file {oct(mode_of(pth))}, thư mục {oct(mode_of(E.cfg))}')
        check(os.listdir(E.cfg) == ['cvat.json'], 'không còn file tạm')
        check(pg.locator('#cd-remember input[type=checkbox]').is_checked() and 'đã lưu trên máy' in txt(pg, '#cd-cvat-status'), 'nguồn: đã lưu trên máy; ô Nhớ bật')
        check(not E.cfg.startswith(CODE) and not os.path.abspath(E.cfg).startswith(os.path.abspath(os.path.join(CODE, '..', '..'))), 'file nằm ngoài repo')
        check(pth in txt(pg, '#cd-remember-note').replace('\n', ''), 'ghi chú hiện đường dẫn thật của cvat.json')
        app.html()
    finally:
        app.stop()
    app = launch(pw, E, 'CD2', port + 1, 'b2')
    pg = app.pg
    try:
        to_settings(pg)
        st = txt(pg, '#cd-cvat-status')
        check('đã lưu trên máy' in st and '••••3456' in st and 'từ biến môi trường' not in st and TOKEN not in st, f'khởi động lại: nguồn "đã lưu trên máy": {st[:120]!r}')
        check(pg.locator('#cd-remember input[type=checkbox]').is_checked() and token_box_ok(pg), 'ô Nhớ bật tự động, ô token rỗng')
        to_review(pg)
        wait_push(pg, True)
        log('  ok   khởi động lại không có biến môi trường: nút Đẩy mở khoá nhờ file đã lưu')
        app.html()
    finally:
        app.stop()


# ---------------------------------------------------------------- pha C
def phase_c(pw, E, port):
    log('\n== PHA C: biến môi trường thắng file; Forget token ==')
    pth = os.path.join(E.cfg, 'cvat.json')
    check(os.path.isfile(pth), 'còn cvat.json từ pha B')
    app = launch(pw, E, 'CD2', port, 'c', cvat=dict(CVAT_URL=URL, CVAT_ACCESS_TOKEN=TOKEN_ENV))
    pg = app.pg
    try:
        to_settings(pg)
        st = txt(pg, '#cd-cvat-status')
        check('từ biến môi trường' in st and '••••7777' in st and 'đã lưu trên máy' not in st and TOKEN_ENV not in st, f'nguồn: từ biến môi trường (thắng file): {st[:140]!r}')
        pg.click('#cd-forget')
        modal_open(pg, '#cd-forget-confirm')
        check(pg.evaluate('document.activeElement && document.activeElement.id') == 'cd-forget-cancel', 'hộp Forget token: nút Cancel có focus')
        mt = txt(pg, '#cd-forget-confirm')
        check('biến môi trường' in mt and 'KHÔNG xoá được' in mt, f'hộp nói rõ token trong cmd không xoá được: {mt[:160]!r}')
        snap(pg, E, 'caidat_forget_modal.png')
        pg.keyboard.press('Escape')
        pg.wait_for_function("() => !document.querySelector('#cd-forget-confirm')", timeout=15000)
        check(os.path.isfile(pth), 'Esc: file vẫn còn')
        pg.click('#cd-forget')
        modal_open(pg, '#cd-forget-confirm')
        pg.click('#cd-forget-ok')
        wait_in(pg, '#cd-cvat-msg', 'Đã quên')
        mt = txt(pg, '#cd-cvat-msg')
        check(not os.path.exists(pth) and 'biến môi trường' in mt and 'set CVAT_ACCESS_TOKEN=' in mt and TOKEN_ENV not in mt, f'Quên: file mất, nhắc token vẫn ở biến môi trường: {mt[:200]!r}')
        st = txt(pg, '#cd-cvat-status')
        check('từ biến môi trường' in st, 'sau Quên: nguồn quay về biến môi trường')
        to_review(pg)
        wait_push(pg, True)
        log('  ok   token biến môi trường còn nên nút Đẩy vẫn mở')
        app.html()
    finally:
        app.stop()


# ---------------------------------------------------------------- pha D
def phase_d(pw, E, port):
    log('\n== PHA D: không còn gì -> Save -> Forget ==')
    check(not os.path.exists(os.path.join(E.cfg, 'cvat.json')), 'không còn cvat.json')
    app = launch(pw, E, 'CD2', port, 'd')
    pg = app.pg
    try:
        wait_in(pg, '#push-panel', 'Thiếu CVAT_URL và CVAT_ACCESS_TOKEN')
        check(pg.locator('#btn-push').is_disabled(), 'không biến môi trường, không file: nút Đẩy khoá, có lý do')
        to_settings(pg)
        fill(pg, 'cd-url', URL)
        fill(pg, 'cd-token', TOKEN2)
        pg.click('#cd-save')
        wait_in(pg, '#cd-cvat-msg', 'Đã lưu cho phiên này')
        to_review(pg)
        wait_push(pg, True)
        to_settings(pg)
        pg.click('#cd-forget')
        modal_open(pg, '#cd-forget-confirm')
        pg.click('#cd-forget-ok')
        wait_in(pg, '#cd-cvat-msg', 'Đã quên')
        check('○ Chưa có link/token' in txt(pg, '#cd-cvat-status') and token_box_ok(pg), 'Quên: về "Chưa có link/token"')
        to_review(pg)
        wait_in(pg, '#push-panel', 'Thiếu CVAT_URL và CVAT_ACCESS_TOKEN')
        check(pg.locator('#btn-push').is_disabled(), 'Forget token: nút Đẩy khoá lại, có lý do')
        # tab thứ hai của trình duyệt giữ rev cũ: bị từ chối nhẹ nhàng
        to_settings(pg)
        fill(pg, 'cd-url', URL)
        fill(pg, 'cd-token', TOKEN)
        pg2 = app.ui.browser.new_page(viewport={'width': 1440, 'height': 900})
        pg2.goto(f'http://127.0.0.1:{app.port}/')
        pg2.wait_for_selector('#tabs', timeout=30000)
        pg2.get_by_role('tab', name='Cài đặt').click()
        pg2.wait_for_selector('#cd-token input', timeout=20000)
        pg2.wait_for_function("(() => { const t = document.querySelector('#cd-cvat-status')?.innerText || ''; return t.includes('○') || t.includes('●'); })()", timeout=20000)
        fill(pg2, 'cd-url', URL)
        fill(pg2, 'cd-token', TOKEN)
        pg2.click('#cd-save')
        wait_in(pg2, '#cd-cvat-msg', 'Đã lưu cho phiên này')
        pg.click('#cd-save')                                   # tab 1 còn rev cũ
        wait_in(pg, '#cd-cvat-msg', 'tab khác')
        check(token_box_ok(pg) and pg.input_value('#cd-url input') == URL, 'tab cũ: Save bị từ chối ("vừa đổi ở tab khác"), ô nhập tải lại từ server, ô token rỗng')
        pg2.close()
        check('••••3456' in txt(pg, '#cd-cvat-status'), 'tab cũ đã tải lại: thấy giá trị do tab kia lưu')
        app.html()
    finally:
        app.stop()


# ---------------------------------------------------------------- pha E
def phase_e(pw, E, port):
    log('\n== PHA E: sai token và khác phiên bản ==')
    for control, want, kind, label in ((dict(auth_fail=True), 'từ chối token', 'sai token', 'e1'), (dict(version='2.70.0'), 'khác phiên bản', 'khác phiên bản', 'e2'),
                                       (dict(connect_fail=True), 'server tắt hoặc sai link', 'server tắt hoặc sai link', 'e3')):
        app = launch(pw, E, 'CD2', port, label, control=control)
        pg = app.pg
        try:
            to_settings(pg)
            fill(pg, 'cd-url', URL)
            fill(pg, 'cd-token', TOKEN)
            pg.click('#cd-test')
            wait_in(pg, '#cd-cvat-msg', want, 60000)
            mt = txt(pg, '#cd-cvat-msg')
            check(kind in mt and 'chưa bấm Save' in mt and TOKEN not in mt, f'{control}: {mt[:200]!r}')
            if label == 'e2':
                check('2.70.0' in mt and 'cvat-sdk' in mt, 'khác phiên bản: nêu phiên bản server và cách sửa')
            fill(pg, 'cd-url', URL)
            pg.click('#cd-save')
            wait_in(pg, '#cd-cvat-msg', 'Đã lưu')
            pg.click('#cd-test')
            pg.wait_for_function("(document.querySelector('#cd-cvat-status')?.innerText || '').includes('● Lỗi')", timeout=60000)
            check(f'● Lỗi: {kind}' in txt(pg, '#cd-cvat-status'), f'chip "● Lỗi: {kind}" sau khi thử giá trị đã lưu')
            app.html()
        finally:
            app.stop()


# ---------------------------------------------------------------- pha F
def phase_f(pw, E, port):
    log('\n== PHA F: phím tắt không chạy ở tab Cài đặt ==')
    run = E.make_run('CD3', decided=False)
    triage = os.path.join(run, 'review', 'triage_E2E.csv')
    app = launch(pw, E, 'CD3', port, 'f')
    pg = app.pg
    try:
        pg.wait_for_selector('#info .face-name', timeout=30000)
        check(not os.path.exists(triage), 'lượt CD3 chưa có triage')
        to_settings(pg)
        for eid in ('cd-url', 'cd-org', 'cd-images', 'cd-model', 'cd-reviewer', 'cd-tflip'):
            pg.click(f'#{eid} input, #{eid} textarea')
            pg.keyboard.type('nNgGbBzZkK012345678')
            fill(pg, eid, '')
        pg.click('#cd-token input')
        pg.keyboard.type('ngbzk')
        pg.keyboard.press('ArrowLeft')
        pg.keyboard.press('ArrowRight')
        pg.click('#cd-eye')
        pg.keyboard.press('n')                                   # focus trên nút (không phải ô gõ): phím tắt vẫn không được chạy ở tab này
        pg.keyboard.press('g')
        pg.keyboard.press('b')
        pg.keyboard.press('z')
        pg.keyboard.press('k')
        pg.wait_for_timeout(1200)
        check(not os.path.exists(triage), 'gõ n/g/b/z/k trong ô token, link, đường dẫn, tên, t_flip và sau khi bấm nút: KHÔNG ghi triage')
        check(not os.path.exists(os.path.join(run, 'ca_kho.csv')), 'phím K không đánh dấu ca khó')
        fill(pg, 'cd-token', '')
        pg.get_by_role('tab', name='Rà soát').click()
        pg.wait_for_selector('#btn-nhan', timeout=15000)
        pg.keyboard.press('n')
        base.Ui.wait_done(app.ui, 1)
        check(os.path.exists(triage) and len(read_csv_rows(triage)) == 2, 'đối chứng: ở tab Rà soát phím N vẫn ghi quyết định')
        app.html()
    finally:
        app.stop()


# ---------------------------------------------------------------- pha G
def phase_g(pw, E, port):
    log('\n== PHA G: --images (ảnh nạp từ tab Nạp ảnh, ảnh gốc bị chuyển đi) ==')
    imgs = dp.pick_images(E.src_w, E.imgs, 2)
    run = 'CDG'
    model_dir = os.path.join(E.shots, 'cd_model')
    shutil.rmtree(model_dir, ignore_errors=True)
    os.makedirs(model_dir)
    model = os.path.join(model_dir, 'face_landmarker.task')
    shutil.move(os.path.join(E.work, 'face_landmarker.task'), model)          # model không còn ở chỗ mặc định: chỉ chạy được nhờ đường dẫn đã cài
    shutil.rmtree(E.cfg, ignore_errors=True)
    app = launch(pw, E, None, port, 'g1', nap=True)
    pg = app.pg
    try:
        base._goto_tab(pg)
        wait_in(pg, '#nap-env', 'face_landmarker.task')
        check('Thiếu face_landmarker.task' in txt(pg, '#nap-env') and 'tab Cài đặt' in txt(pg, '#nap-env'), f'model không ở chỗ mặc định: báo thiếu, gợi ý tab Cài đặt: {txt(pg, "#nap-env")[:160]!r}')
        to_settings(pg)
        fill(pg, 'cd-model', model)
        pg.click('#cd-model-save')
        wait_in(pg, '#cd-model-msg', 'Đã lưu đường dẫn model')
        pg.get_by_role('tab', name='Nạp ảnh').click()
        try:
            wait_in(pg, '#nap-env', 'Đủ model và cấu hình', 10000)
        except Exception:
            log('  nap-env hiện: ' + txt(pg, '#nap-env')[:400])
            raise
        log('  ok   model đã cài: tab Nạp ảnh kiểm lại ngay sau khi Lưu, không cần tải lại trang')
        base._drop(pg, imgs, len(imgs), 0)
        pg.fill('#nap-name textarea, #nap-name input', run)
        pg.click('#nap-start')
        pg.wait_for_function("n => (document.querySelector('#nap-summary')?.innerText || '').includes('Kết quả lượt ' + n) && "
                             "(document.querySelector('#nap-prog')?.innerText || '').includes('Xong')", arg=run, timeout=300000)
        check(os.path.exists(os.path.join(E.work, 'runs', run, 'flags', 'flags.json')), 'prepare thật xong bằng model ở đường dẫn đã cài (MediaPipe trên ảnh in-cabin)')
        app.html()
    finally:
        app.stop()
    rd = os.path.join(E.work, 'runs', run)
    meta = json.load(open(os.path.join(rd, 'crop', 'meta.json'), encoding='utf-8'))
    imgdir = os.path.join(E.shots, 'cd_moved_images')
    shutil.rmtree(imgdir, ignore_errors=True)
    os.makedirs(imgdir)
    for n, m in meta.items():
        shutil.copy(m['src'], os.path.join(imgdir, *m['rel'].split('/')))
    shutil.rmtree(os.path.join(rd, 'inbox'))                     # ảnh gốc "đã bị chuyển đi"
    import review_app as ra
    os.makedirs(os.path.join(rd, 'review'), exist_ok=True)
    with open(os.path.join(rd, 'review', 'triage_E2E.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['name', 'decision', 'reason', 'seconds'])
        for face in ra.load_queue(rd):
            w.writerow([face.file, 'nhan' if face.has_draft else 'gan_tay', '', '1'])
    app = launch(pw, E, run, port + 1, 'g2')
    pg = app.pg
    try:
        to_settings(pg)
        fill(pg, 'cd-url', URL)
        fill(pg, 'cd-token', TOKEN)
        pg.click('#cd-save')
        wait_in(pg, '#cd-cvat-msg', 'Đã lưu cho phiên này')
        fill(pg, 'cd-images', '')
        pg.click('#cd-images-save')
        wait_in(pg, '#cd-images-msg', 'Đã xoá')
        to_review(pg)
        wait_in(pg, '#push-panel', 'Không thấy')
        mt = txt(pg, '#push-panel')
        check(pg.locator('#btn-push').is_disabled() and 'Cài đặt' in mt, f'ảnh gốc không còn: nút Đẩy khoá, gợi ý tab Cài đặt: {mt[:200]!r}')
        to_settings(pg)
        fill(pg, 'cd-images', imgdir)
        pg.click('#cd-images-save')
        wait_in(pg, '#cd-images-msg', 'Đã lưu thư mục ảnh')
        to_review(pg)
        wait_push(pg, True)
        pg.click('#btn-push')
        modal_open(pg, '#push-confirm')
        pg.click('#push-confirm-ok')
        pg.wait_for_selector('#push-panel .push-done', timeout=180000)
        st = dp.fake_state(E.state)
        task = next(t for t in st['tasks'] if t['name'] == f'demo-{run}')
        check(task['files'] and all(os.path.dirname(f) == imgdir for f in task['files']), f'task nhận ảnh từ thư mục đã cài ({len(task["files"])} ảnh)')
        app.html()
    finally:
        app.stop()


# ---------------------------------------------------------------- cuối: grep token
def final_grep(E):
    log('\n== Cuối: grep token giả ==')
    hits = []
    for h in HTML_SEEN:
        if any(t.encode() in h.encode('utf-8') for t in SECRETS):
            hits.append('HTML')
    roots = [E.shots, E.work]
    for root in roots:
        for d, _s, fs in os.walk(root):
            for f in fs:
                p = os.path.join(d, f)
                if f.endswith(('.png', '.jpg', '.task', '.pyc')) or os.path.islink(p):
                    continue
                try:
                    data = open(p, 'rb').read()
                except OSError:
                    continue
                if any(t.encode() in data for t in SECRETS):
                    hits.append(p)
    allowed = [h for h in hits if os.path.basename(h) == 'cvat.json']
    bad = [h for h in hits if h not in allowed]
    check(not bad, f'token giả không xuất hiện ở đâu (HTML, log app, runs/, state CVAT giả, file tạm): {bad[:5]}')
    check(not os.path.exists(os.path.join(E.cfg, 'cvat.json')) or allowed, 'cvat.json (nếu còn) là nơi duy nhất có token')
    check(open(os.path.join(E.work, 'config', 'm28_config.json'), 'rb').read() == E.config_bytes, 'config của thư mục làm việc về đúng như ban đầu')
    check(open(os.path.join(E.src, 'config', 'm28_config.json'), 'rb').read() == E.src_config_bytes, 'config gốc của --work không bị đụng')
    check(open(os.path.join(CODE, 'config', 'm28_config.json'), 'rb').read() == E.config_bytes, 'config của repo không bị đụng')
    real_home = os.path.expanduser('~/.config/m28')
    check(not os.path.exists(real_home), f'không có gì ghi vào hồ sơ thật ({real_home})')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--work', required=True)
    ap.add_argument('--imgs', required=True)
    ap.add_argument('--shots', required=True)
    ap.add_argument('--port', type=int, default=7891)
    ap.add_argument('--phases', default='ABCDEFG')
    a = ap.parse_args()
    W, shots = os.path.abspath(a.work), os.path.abspath(a.shots)
    os.makedirs(shots, exist_ok=True)
    from playwright.sync_api import sync_playwright
    t0 = time.time()
    E = None
    global PORTS
    PORTS = itertools.count(a.port)
    try:
        E = Env(W, shots)
        E.imgs, E.src_w = os.path.abspath(a.imgs), W
        with sync_playwright() as pw:
            for ph in 'ABCDEFG':
                if ph in a.phases:
                    {'A': phase_a, 'B': phase_b, 'C': phase_c, 'D': phase_d, 'E': phase_e, 'F': phase_f, 'G': phase_g}[ph](pw, E, a.port)
        if a.phases == 'ABCDEFG':
            final_grep(E)
    except (AssertionError, RuntimeError) as e:
        log(f'\nHỎNG: {e}')
        return 1
    finally:
        stop_all()
    log(f'\nQUA sau {time.time() - t0:.0f}s. Ảnh chụp ở {shots}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
