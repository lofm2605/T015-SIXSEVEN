"""Thử tab "Cài đặt" của trang rà soát M28: tool/cai_dat.py (logic), tool/cai_dat_thu.py (tiến trình con thử kết nối), tool/cai_dat_ui.py
(HTML thuần và handler Gradio gọi trực tiếp, không trình duyệt) và các chỗ tool dùng cài đặt (nap_anh, day_cvat, review_app).

Token giả: tok-TEST-123456 (và tok-OTHER-654321 khi đổi token). Mọi thứ chạy trong thư mục tạm: conftest.py trỏ M28_CONFIG_DIR vào tmp, nên không
có gì ghi vào HOME thật. Thử kết nối dùng CVAT GIẢ (tests/fake_cvat) qua tiến trình con thật; KHÔNG có CVAT thật nên chưa chứng minh được
users.retrieve_current_user / tiền kiểm /api/server/about trên server thật.
"""
import http.server
import json
import ntpath
import os
import stat
import subprocess
import sys
import threading
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, '..', 'tool')
FAKE = os.path.join(HERE, 'fake_cvat')
REAL_CONFIG = os.path.join(HERE, '..', 'config', 'm28_config.json')
sys.path.insert(0, TOOL)
sys.path.insert(0, HERE)
import cai_dat  # noqa: E402
import cai_dat_thu  # noqa: E402
import cai_dat_ui  # noqa: E402
import day_cvat  # noqa: E402
import nap_anh as na  # noqa: E402
import review_app as ra  # noqa: E402
from m28core import cvat_io  # noqa: E402
from test_dot_anh import ALL_DECIDED, make_dot_run, world  # noqa: E402,F401  (fixture world: thư mục tạm có config/pipeline.json, không biến CVAT)

TOKEN, TOKEN2 = 'tok-TEST-123456', 'tok-OTHER-654321'
URL = 'http://localhost:8080'
PIPE = dict(cvat_version='2.77.0', project='m28', prefix='demo-', job_size=8)
POSIX_ONLY = pytest.mark.skipif(os.name == 'nt', reason='quyền Unix')


@pytest.fixture
def S(tmp_path):
    """Settings riêng: thư mục cài đặt trong tmp (M28_CONFIG_DIR), project_root giả, môi trường rỗng."""
    cfg = tmp_path / 'cfg' / 'm28'
    return cai_dat.Settings(environ={cai_dat.ENV_DIR: str(cfg)}, platform='linux', project_root=str(tmp_path / 'proj'))


def settings_in(tmp_path, env=None, name='cfg'):
    e = {cai_dat.ENV_DIR: str(tmp_path / name / 'm28')}
    e.update(env or {})
    return cai_dat.Settings(environ=e, platform='linux', project_root=str(tmp_path / 'proj'))


def files_under(root):
    return [os.path.join(d, f) for d, _s, fs in os.walk(root) for f in fs]


# ---------- nơi lưu ----------
def test_user_dir_per_platform():
    assert cai_dat.user_dir({'APPDATA': 'C:\\Users\\An\\AppData\\Roaming'}, 'win32') == ntpath.join('C:\\Users\\An\\AppData\\Roaming', 'm28')
    assert cai_dat.user_dir({'USERPROFILE': 'C:\\Users\\An'}, 'win32') == 'C:\\Users\\An\\AppData\\Roaming\\m28'
    with pytest.raises(cai_dat.SettingsError):
        cai_dat.user_dir({}, 'win32')
    assert cai_dat.user_dir({'XDG_CONFIG_HOME': '/x/cfg', 'HOME': '/h'}, 'linux') == '/x/cfg/m28'
    assert cai_dat.user_dir({'HOME': '/home/an'}, 'linux') == '/home/an/.config/m28'
    assert cai_dat.user_dir({'XDG_CONFIG_HOME': 'tuongdoi', 'HOME': '/home/an'}, 'darwin') == '/home/an/.config/m28'      # XDG phải là đường tuyệt đối
    assert cai_dat.user_dir({cai_dat.ENV_DIR: '/tmp/zz', 'HOME': '/h', 'APPDATA': 'C:\\a'}, 'win32') == os.path.abspath('/tmp/zz')


def test_settings_dir_inside_repo_is_refused(tmp_path):
    proj = tmp_path / 'repo' / 'source-tool' / 'm28-prelabel'
    proj.mkdir(parents=True)
    (tmp_path / 'repo' / '.git').mkdir()
    for bad in (proj / 'cfg', tmp_path / 'repo' / 'cfg', tmp_path / 'repo'):
        s = cai_dat.Settings(environ={cai_dat.ENV_DIR: str(bad)}, platform='linux', project_root=str(proj))
        assert s.dir == '' and 'nằm trong repo' in s.dir_error
        r = s.save_cvat(URL, TOKEN, '', True)
        assert r['ok'] and not r['persisted'] and r['level'] == 'warn' and 'repo' in r['msg'] and TOKEN not in r['msg']
        assert not files_under(bad) if os.path.isdir(bad) else True
        assert s.effective()['token'] == TOKEN                                  # phiên vẫn dùng giá trị trong bộ nhớ
    ok = cai_dat.Settings(environ={cai_dat.ENV_DIR: str(tmp_path / 'ngoai' / 'm28')}, platform='linux', project_root=str(proj))
    assert ok.dir_error == ''
    link = tmp_path / 'lk'
    os.symlink(proj, link)                                                       # đi vòng qua symlink cũng bị chặn (realpath)
    s = cai_dat.Settings(environ={cai_dat.ENV_DIR: str(link / 'cfg')}, platform='linux', project_root=str(proj))
    assert s.dir_error


def test_nothing_is_written_to_real_home(tmp_path):
    real = os.path.expanduser('~/.config/m28')
    before = os.path.exists(real)
    home = tmp_path / 'home'
    s = cai_dat.Settings(environ={'HOME': str(home)}, platform='linux', project_root=str(tmp_path / 'proj'))
    assert s.save_cvat(URL, TOKEN, '', True)['persisted'] and s.set_reviewer('P2')['ok']
    assert os.path.isfile(home / '.config' / 'm28' / 'cvat.json')
    assert os.path.exists(real) == before
    assert os.environ[cai_dat.ENV_DIR].startswith(str(tmp_path.parent))        # conftest đã trỏ biến cài đặt vào thư mục tạm


# ---------- ghi nguyên tử, quyền ----------
@POSIX_ONLY
def test_permissions_dir_0700_file_0600(S):
    assert S.save_cvat(URL, TOKEN, '', True)['persisted']
    assert stat.S_IMODE(os.stat(S.dir).st_mode) == 0o700
    assert stat.S_IMODE(os.stat(S.path_cvat()).st_mode) == 0o600
    assert S.set_reviewer('P3')['ok']
    assert stat.S_IMODE(os.stat(S.path_prefs()).st_mode) == 0o600
    d = json.load(open(S.path_cvat(), encoding='utf-8'))
    assert d == dict(version=1, url=URL, token=TOKEN, org='')


@POSIX_ONLY
def test_permission_is_tightened_even_with_loose_umask(S):
    old = os.umask(0)
    try:
        assert S.save_cvat(URL, TOKEN, '', True)['persisted']
    finally:
        os.umask(old)
    assert stat.S_IMODE(os.stat(S.path_cvat()).st_mode) == 0o600 and stat.S_IMODE(os.stat(S.dir).st_mode) == 0o700


def test_atomic_write_failure_keeps_old_file_and_leaves_no_tmp(S, monkeypatch):
    assert S.save_cvat(URL, TOKEN, '', True)['persisted']
    before = open(S.path_cvat(), 'rb').read()

    def boom(src, dst):
        raise OSError(28, 'No space left on device')
    monkeypatch.setattr(os, 'replace', boom)
    r = S.save_cvat(URL, TOKEN2, '', True)
    monkeypatch.undo()
    assert r['ok'] and r['level'] == 'warn' and not r['persisted'] and 'Không ghi được' in r['msg'] and TOKEN2 not in r['msg']
    assert open(S.path_cvat(), 'rb').read() == before
    assert os.listdir(S.dir) == ['cvat.json']                                    # không còn file tạm
    assert S.effective()['token'] == TOKEN2 and S.effective()['source'] == 'session'     # phiên vẫn dùng giá trị mới trong bộ nhớ


def test_atomic_write_exclusive_tmp_and_no_tmp_left_on_error(tmp_path):
    p = tmp_path / 'd' / 'f.json'
    cai_dat.atomic_write(str(p), b'{"a":1}')
    assert p.read_bytes() == b'{"a":1}' and os.listdir(p.parent) == ['f.json']
    with pytest.raises(OSError):
        cai_dat.atomic_write(str(tmp_path / 'd' / 'f.json' / 'x'), b'1')        # f.json là file: không tạo được thư mục con
    assert os.listdir(p.parent) == ['f.json']


def test_unwritable_dir_reports_vietnamese_and_session_still_works(S, monkeypatch):
    def deny(*a, **k):
        raise PermissionError(13, 'Permission denied')
    monkeypatch.setattr(cai_dat.os, 'makedirs', deny)
    r = S.save_cvat(URL, TOKEN, '', True)
    assert r['ok'] and r['level'] == 'warn' and not r['persisted'] and 'Không ghi được' in r['msg'] and 'M28_CONFIG_DIR' in r['msg']
    assert S.effective() == dict(url=URL, token=TOKEN, org='', source='session')
    r2 = S.set_reviewer('P4')
    assert r2['ok'] and r2['level'] == 'warn' and 'Không ghi được' in r2['msg'] and S.default_reviewer() == 'P4'


@POSIX_ONLY
@pytest.mark.skipif(hasattr(os, 'geteuid') and os.geteuid() == 0, reason='root ghi được mọi nơi')
def test_readonly_dir_with_chmod(tmp_path):
    d = tmp_path / 'ro'
    d.mkdir()
    d.chmod(0o500)
    try:
        s = cai_dat.Settings(environ={cai_dat.ENV_DIR: str(d / 'm28')}, platform='linux', project_root=str(tmp_path / 'proj'))
        r = s.save_cvat(URL, TOKEN, '', True)
        assert r['level'] == 'warn' and not r['persisted'] and s.effective()['token'] == TOKEN
    finally:
        d.chmod(0o700)


# ---------- che token, repr ----------
def test_mask_and_no_repr_leak(S):
    assert cai_dat.mask(TOKEN) == '••••3456' and cai_dat.mask('abc') == '••••' and cai_dat.mask('1234567') == '••••' and cai_dat.mask('') == '••••'
    S.save_cvat(URL, TOKEN, 'cty', False)
    for obj in (S, str(S), repr(S), S.snapshot(), repr(S.snapshot())):
        assert TOKEN not in str(obj) and TOKEN not in repr(obj)
    snap = S.snapshot()
    assert snap['token_mask'] == '••••3456' and snap['source'] == 'session' and snap['source_label'] == 'nhập trong phiên này'
    assert 'token' not in snap                                                  # snapshot (đi tới UI) không có khoá token
    assert TOKEN not in json.dumps(snap, default=str)


# ---------- ưu tiên nguồn ----------
def test_source_priority_env_over_file_then_session_then_forget(tmp_path):
    saved = settings_in(tmp_path)
    saved.save_cvat('http://file.local:1', TOKEN2, 'orgfile', True)
    env = {'CVAT_URL': URL, 'CVAT_ACCESS_TOKEN': TOKEN, 'CVAT_ORG': 'orgenv'}
    s = settings_in(tmp_path, env)                                             # lúc khởi động: có cả hai thì biến môi trường thắng file
    e = s.effective()
    assert (e['url'], e['token'], e['org'], e['source']) == (URL, TOKEN, 'orgenv', 'env')
    assert s.snapshot()['source_label'] == 'từ biến môi trường' and s.file_status == 'ok'
    r = s.save_cvat('http://localhost:9999', TOKEN2, '', False)                # Lưu trong phiên: giá trị mới thắng, ghi chú về biến môi trường
    assert r['ok'] and 'cmd không đổi' in r['msg'] and 'chỉ trang này' in r['msg']
    e = s.effective()
    assert (e['url'], e['token'], e['source']) == ('http://localhost:9999', TOKEN2, 'session') and env['CVAT_ACCESS_TOKEN'] == TOKEN
    assert not os.path.exists(s.path_cvat())                                   # bỏ tick Nhớ: file cũ bị xoá
    f = s.forget_cvat()
    assert f['level'] == 'warn' and 'biến môi trường' in f['msg'] and 'set CVAT_ACCESS_TOKEN=' in f['msg'] and TOKEN not in f['msg']
    assert s.effective()['source'] == 'env' and s.effective()['token'] == TOKEN         # Quên → quay về biến môi trường


def test_file_source_and_remember_roundtrip(tmp_path):
    a = settings_in(tmp_path)
    assert a.effective()['source'] is None and not a.snapshot()['has_token']
    r = a.save_cvat(URL + '/', TOKEN, 'cty', True)
    assert r['ok'] and r['persisted'] and a.snapshot()['source_label'] == 'đã lưu trên máy' and a.snapshot()['remember']
    b = settings_in(tmp_path)                                                  # "khởi động lại": nạp từ file
    e = b.effective()
    assert (e['url'], e['token'], e['org'], e['source']) == (URL, TOKEN, 'cty', 'file')            # URL đã bỏ '/' cuối
    assert b.snapshot()['remember'] is True
    f = b.forget_cvat()
    assert f['ok'] and f['level'] == 'ok' and not os.path.exists(b.path_cvat()) and b.effective()['source'] is None and not b.snapshot()['has_token']
    assert settings_in(tmp_path).effective()['source'] is None


def test_save_without_remember_removes_existing_file_and_never_writes_one(tmp_path):
    s = settings_in(tmp_path)
    r = s.save_cvat(URL, TOKEN, '', False)
    assert r['ok'] and not os.path.exists(s.path_cvat()) and 'không ghi ra file' in r['msg']
    s.save_cvat(URL, TOKEN, '', True)
    assert os.path.exists(s.path_cvat())
    r = s.save_cvat(URL, '', '', False)                                        # token trống = giữ token hiện có
    assert r['ok'] and not os.path.exists(s.path_cvat()) and 'xoá file' in r['msg'] and s.effective()['token'] == TOKEN
    assert s.effective()['source'] == 'session'


def test_blank_token_rules(tmp_path):
    s = settings_in(tmp_path)
    assert not s.save_cvat(URL, '', '', False)['ok']                           # chưa có token
    s.save_cvat(URL, TOKEN, '', False)
    r = s.save_cvat('http://other.local:8080', '', '', False)                   # đổi link mà bỏ trống token: không tự gửi token cũ sang link mới
    assert not r['ok'] and 'dán lại token' in r['msg'] and s.effective()['url'] == URL
    r = s.save_cvat(URL + '/', '', 'cty', False)                                # cùng link: giữ token
    assert r['ok'] and s.effective()['token'] == TOKEN and s.effective()['org'] == 'cty'
    env = settings_in(tmp_path, {'CVAT_URL': URL, 'CVAT_ACCESS_TOKEN': TOKEN2}, name='c2')
    r = env.save_cvat(URL, '', '', True)                                        # không tự chép token của cmd ra file
    assert not r['ok'] and 'biến môi trường' in r['msg'] and not os.path.exists(env.path_cvat())
    assert env.save_cvat(URL, '', '', False)['ok']


def test_partial_env_is_reported_not_mixed(tmp_path):
    s = settings_in(tmp_path, {'CVAT_URL': URL})
    e = s.effective()
    assert e['url'] == URL and e['token'] == '' and e['source'] == 'env' and s.snapshot()['env'] == 'partial'
    old = cai_dat.install(s)
    try:
        st = day_cvat.env_state(None)
        assert not st['ok'] and st['reason'] == 'Thiếu CVAT_ACCESS_TOKEN.' and st['source'] == 'env'          # thiếu một nửa: báo rõ, không trộn nguồn
    finally:
        cai_dat.install(old)
    f = settings_in(tmp_path, name='cf')
    f.save_cvat('http://file.local:1', TOKEN2, '', True)
    mix = settings_in(tmp_path, {'CVAT_URL': URL}, name='cf')
    assert mix.effective()['token'] == TOKEN2 and mix.effective()['url'] == 'http://file.local:1' and mix.effective()['source'] == 'file'


def test_stale_rev_is_refused_gently(S):
    r0 = S.rev
    assert S.save_cvat(URL, TOKEN, '', False, rev=r0)['ok'] and S.rev == r0 + 1
    r = S.save_cvat(URL, TOKEN2, '', False, rev=r0)
    assert r['stale'] and not r['ok'] and 'tab khác' in r['msg'] and S.effective()['token'] == TOKEN
    assert S.forget_cvat(rev=r0)['stale'] and S.set_reviewer('P2', rev=r0)['stale'] and S.set_path('images_dir', '', rev=r0)['stale']
    assert S.effective()['token'] == TOKEN


# ---------- kiểm giá trị ----------
def test_check_url_accepts_and_normalizes():
    for u, want in ((URL, URL), ('  http://localhost:8080/  ', URL), ('https://cvat.congty.vn', 'https://cvat.congty.vn'), ('HTTP://192.168.1.5:8080/', 'HTTP://192.168.1.5:8080'),
                    ('http://[::1]:8080', 'http://[::1]:8080'), ('https://x.vn/cvat/', 'https://x.vn/cvat'), ('http://localhost:8080\n', URL)):
        r = cai_dat.check_url(u)
        assert r['ok'] and r['url'] == want, (u, r)


@pytest.mark.parametrize('bad', ['', '   ', 'localhost:8080', 'file:///etc/passwd', 'ftp://host/x', 'http://user:pass@localhost:8080', 'http://u@h',
                                 'http://local host:8080', 'http://local\nhost:8080', 'http://', 'http:///x', 'http://localhost:99999', 'http://localhost:abc',
                                 'http://localhost:8080#frag', 'http://localhost:8080/?q=1', 'javascript://x', 'http://a b', 'http://lo\x00calhost'])
def test_check_url_rejects(bad):
    r = cai_dat.check_url(bad)
    assert not r['ok'] and r['error'] and not r['url'], bad


def test_check_url_warns_only_for_http_outside_private_networks():
    for u in ('http://localhost:8080', 'http://127.0.0.1:8080', 'http://127.5.5.5', 'http://192.168.1.9', 'http://10.1.2.3:8080', 'http://172.16.0.4', 'http://172.31.255.1',
              'http://[::1]:8080', 'http://cvat.local:8080', 'http://cvat-server:8080', 'https://cvat.example.com', 'https://8.8.8.8', 'http://fd00::1'):
        assert cai_dat.check_url(u)['warning'] == '', u
    for u in ('http://cvat.example.com', 'http://8.8.8.8:8080', 'http://172.32.0.1', 'http://203.0.113.7'):
        w = cai_dat.check_url(u)['warning']
        assert 'KHÔNG mã hoá' in w, u


def test_check_url_does_not_resolve_dns(monkeypatch):
    import socket

    def no(*a, **k):
        raise AssertionError('không được phân giải DNS khi kiểm link')
    monkeypatch.setattr(socket, 'getaddrinfo', no)
    monkeypatch.setattr(socket, 'gethostbyname', no)
    assert cai_dat.check_url('http://khong-ton-tai.example.invalid:8080')['ok']


def test_check_token_and_org():
    assert cai_dat.check_token(TOKEN) == (TOKEN, None)
    for bad in ('', '   ', 'ngan', 'co khoang trang 1234', 'abc\x00defghij', 'tok-\tTEST-123', 'x' * 513, 'tiếng-việt-123456'):
        t, why = cai_dat.check_token(bad)
        assert t is None and why and (bad.strip() == '' or bad not in why), bad
    assert cai_dat.check_org('') == ('', None) and cai_dat.check_org(' cty_1.a-b ') == ('cty_1.a-b', None)
    assert cai_dat.check_org('có dấu')[1] and cai_dat.check_org('a b')[1]
    r = cai_dat.Settings(environ={cai_dat.ENV_DIR: '/tmp/x-m28-none'}, platform='linux').save_cvat(URL, 'ngan', '', False)
    assert not r['ok'] and 'ngan' not in r['msg'].replace('ngắn', '')


# ---------- file hỏng ----------
@pytest.mark.parametrize('content', [b'{khong phai json', b'[1, 2, 3]', b'"chuoi"', b'', b'\xff\xfe\x00bad', b'null',
                                     json.dumps(dict(version=1, url=URL, token=12345678, org='')).encode(),
                                     json.dumps(dict(version=1, url=URL, token='tok-\x07-TEST-1234', org='')).encode(),
                                     json.dumps(dict(version=2, url=URL, token=TOKEN, org='')).encode(),
                                     json.dumps(dict(version=1, url='file:///etc/passwd', token=TOKEN, org='')).encode(),
                                     json.dumps(dict(version=1, url=URL, token=TOKEN, org=['x'])).encode()])
def test_corrupt_cvat_file_does_not_break_and_is_not_echoed(tmp_path, content):
    d = tmp_path / 'cfg' / 'm28'
    d.mkdir(parents=True)
    (d / 'cvat.json').write_bytes(content)
    s = settings_in(tmp_path)
    assert s.file_status == 'hong' and s.effective()['source'] is None
    html = cai_dat_ui.status_html(s.snapshot(), PIPE)
    assert 'hỏng' in html and 'Quên token' in html
    for frag in (b'phai json', b'chuoi', b'bad', b'12345678', b'etc/passwd'):
        if frag in content and len(frag) > 3:
            assert frag.decode('latin-1') not in html
    assert TOKEN not in html
    r = s.save_cvat(URL, TOKEN, '', True)                                      # Lưu lại ghi đè file hỏng
    assert r['persisted'] and settings_in(tmp_path).effective()['token'] == TOKEN
    s2 = settings_in(tmp_path)
    (d / 'cvat.json').write_bytes(content)
    s2.load()
    assert s2.forget_cvat()['ok'] and not (d / 'cvat.json').exists() and s2.file_status == 'none'


def test_corrupt_prefs_file(tmp_path):
    d = tmp_path / 'cfg' / 'm28'
    d.mkdir(parents=True)
    for content in (b'{', b'[]', json.dumps(dict(version=1, reviewer='có dấu', images_dir='', model_path='')).encode(),
                    json.dumps(dict(version=1, reviewer=5)).encode()):
        (d / 'cai_dat.json').write_bytes(content)
        s = settings_in(tmp_path)
        assert s.prefs_status == 'hong' and s.default_reviewer() == '' and s.next_reviewer('P2') == 'P2'
        assert s.set_reviewer('P5')['ok'] and settings_in(tmp_path).default_reviewer() == 'P5'


def test_unreadable_file_does_not_raise(tmp_path, monkeypatch):
    d = tmp_path / 'cfg' / 'm28'
    d.mkdir(parents=True)
    (d / 'cvat.json').write_text(json.dumps(dict(version=1, url=URL, token=TOKEN, org='')))
    real_open = open

    def deny(path, *a, **k):
        if str(path).endswith('cvat.json'):
            raise PermissionError(13, 'denied')
        return real_open(path, *a, **k)
    monkeypatch.setattr('builtins.open', deny)
    s = settings_in(tmp_path)
    monkeypatch.undo()
    assert s.file_status == 'khong_doc' and s.effective()['source'] is None
    assert 'không đọc được' in cai_dat_ui.status_html(s.snapshot(), PIPE)


# ---------- người dùng của cài đặt: cvat_env, môi trường tiến trình con ----------
def test_cvat_env_and_child_env_use_saved_values_without_os_environ(S, monkeypatch, world):
    for v in ('CVAT_URL', 'CVAT_ACCESS_TOKEN', 'CVAT_ORG'):
        monkeypatch.delenv(v, raising=False)
    old = cai_dat.install(S)
    try:
        assert cai_dat.cvat_env() == dict(url='', token='', org='') and cai_dat.child_env_updates() == {}
        S.save_cvat(URL, TOKEN, 'cty', False)
        assert cai_dat.cvat_env() == dict(url=URL, token=TOKEN, org='cty')
        assert cai_dat.child_env_updates() == {'CVAT_URL': URL, 'CVAT_ACCESS_TOKEN': TOKEN, 'CVAT_ORG': 'cty'}
        assert cai_dat.cvat_env({'CVAT_URL': 'http://x:1', 'CVAT_ACCESS_TOKEN': 'y'}) == dict(url='http://x:1', token='y', org='')       # test cũ truyền environ
        S.save_cvat(URL, TOKEN, '', False)
        assert 'CVAT_ORG' not in cai_dat.child_env_updates()
    finally:
        cai_dat.install(old)


def _spy_popen(seen):
    def popen(cmd, **kw):
        seen.update(cmd=cmd, **kw)
        return subprocess.Popen([sys.executable, '-c', "import os; print('token', os.environ.get('CVAT_ACCESS_TOKEN', 'KHONG-CO')); print('url', os.environ.get('CVAT_URL', ''))"],
                                **kw)
    return popen


def _wait(job, t=15):
    t0 = time.time()
    while job.running and time.time() - t0 < t:
        time.sleep(0.05)


def test_jobs_get_saved_token_in_env_not_in_argv_and_prepare_gets_none(S, world, monkeypatch):
    monkeypatch.setenv('CVAT_ACCESS_TOKEN', 'tok-ENV-SHOULD-NOT-LEAK-INTO-PREPARE')       # biến cmd có sẵn: prepare cũng không được thừa hưởng
    old = cai_dat.install(S)
    try:
        S.save_cvat(URL, TOKEN, '', False)
        rd = make_dot_run(world, 'Khoi')
        seen = {}
        job = na.PushJob(popen=_spy_popen(seen))
        job.start('Khoi', 'runs', str(world), 'P2', 'demo-Khoi')
        _wait(job)
        assert seen['env']['CVAT_ACCESS_TOKEN'] == TOKEN and seen['env']['CVAT_URL'] == URL
        assert not any(TOKEN in c for c in seen['cmd']) and not any(URL in c for c in seen['cmd'])
        log = open(os.path.join(rd, 'push_log.txt'), encoding='utf-8').read()
        assert TOKEN not in log and 'token ***' in log
        seen2 = {}
        dj = na.DeleteTaskJob(popen=_spy_popen(seen2))
        dj.start('Khoi', 'runs', str(world), 'demo-Khoi')
        _wait(dj)
        assert seen2['env']['CVAT_ACCESS_TOKEN'] == TOKEN and not any(TOKEN in c for c in seen2['cmd'])
        seen3 = {}
        pj = na.PrepareJob(popen=_spy_popen(seen3))
        pj.start('Khoi', 'runs', str(world))
        _wait(pj)
        assert not any(k in seen3['env'] for k in ('CVAT_URL', 'CVAT_ACCESS_TOKEN', 'CVAT_ORG')), 'prepare không cần và không nhận token'
        assert 'tok-ENV-SHOULD' not in open(os.path.join(rd, 'nap_log.txt'), encoding='utf-8').read()
    finally:
        cai_dat.install(old)


def test_push_cmd_images_and_prepare_cmd_model_have_no_token():
    cmd = na.push_cmd('Khoi', 'P2', 'demo-Khoi', tool_dir='T', python='py')
    assert cmd == ['py', '-u', os.path.join('T', 'm28.py'), 'push', '--run', 'Khoi', '--reviewer', 'P2', '--task', 'demo-Khoi']
    cmd = na.push_cmd('Khoi', 'P2', 'demo-Khoi', tool_dir='T', python='py', images='D:\\WFLW\\WFLW_images')
    assert cmd[-2:] == ['--images', 'D:\\WFLW\\WFLW_images'] and na.delete_task_cmd('Khoi', 'demo-Khoi')[-2:] == ['--confirm-name', 'demo-Khoi']
    pc = na.prepare_cmd('NAP_001', tool_dir='T', python='py', model='D:\\m\\face_landmarker.task')
    assert pc[-2:] == ['--model', 'D:\\m\\face_landmarker.task'] and na.prepare_cmd('NAP_001', 'T', 'py')[-1] == 'auto'
    for c in (cmd, pc):
        assert not any(TOKEN in x or 'ACCESS' in x for x in c)
    argv = [cai_dat.PROBE_SCRIPT, '--version', '2.77.0', '--project', 'm28']
    assert not any(TOKEN in x for x in argv)


def test_push_model_unlocks_after_save_without_environment(S, world, monkeypatch):
    for v in ('CVAT_URL', 'CVAT_ACCESS_TOKEN', 'CVAT_ORG'):
        monkeypatch.delenv(v, raising=False)
    rd = make_dot_run(world, 'Cuong', decisions=ALL_DECIDED, done=True)
    old = cai_dat.install(S)
    try:
        m = day_cvat.push_model(rd, 'P2', str(world), remaining=0)
        assert not m['enabled'] and m['env_help'] and 'tab <b>Cài đặt</b>' in day_cvat.panel_html(m)
        S.save_cvat(URL, TOKEN, '', False)
        m = day_cvat.push_model(rd, 'P2', str(world), remaining=0)
        assert m['enabled'] and m['env']['url'] == URL and m['env']['source'] == 'session' and TOKEN not in day_cvat.panel_html(m) + day_cvat.confirm_html(m)
        assert day_cvat.delete_model(rd, str(world))['reason'].startswith('Lượt này chưa có task')       # chưa đẩy: lý do khác, không phải thiếu token
        S.forget_cvat()
        assert not day_cvat.push_model(rd, 'P2', str(world), remaining=0)['enabled']
    finally:
        cai_dat.install(old)


def test_delete_model_uses_same_source(S, world, monkeypatch):
    for v in ('CVAT_URL', 'CVAT_ACCESS_TOKEN', 'CVAT_ORG'):
        monkeypatch.delenv(v, raising=False)
    rd = make_dot_run(world, 'Khoi', decisions=ALL_DECIDED, done=True, push=dict(trang_thai='xong', task='demo-Khoi', task_id=7, cvat_url=URL))
    old = cai_dat.install(S)
    try:
        m = day_cvat.delete_model(rd, str(world))
        assert not m['ok'] and 'Cài đặt' in m['reason']
        S.save_cvat(URL + '/', TOKEN, '', False)
        assert day_cvat.delete_model(rd, str(world))['ok']
        S.save_cvat('http://localhost:9090', TOKEN, '', False)
        assert 'localhost:9090' in day_cvat.delete_model(rd, str(world))['reason']       # id task chỉ có nghĩa đúng server đã đẩy
    finally:
        cai_dat.install(old)


def test_scrub_knows_registered_secrets_and_session_token(S):
    old = cai_dat.install(S)
    try:
        S.save_cvat(URL, TOKEN2, '', False)
        assert TOKEN2 not in cvat_io.scrub(f'lỗi: {TOKEN2} và Authorization: Token {TOKEN2}')
        assert cvat_io.scrub(f'x {TOKEN2}', token=TOKEN).count('***') == 1
        cvat_io.register_secret('abc')
        assert cvat_io.scrub('abc') == 'abc'                                    # quá ngắn thì không đăng ký
    finally:
        cai_dat.install(old)


# ---------- người rà ----------
def test_reviewer_rules_are_the_same_as_review_app(S):
    for name in ('P2', 'P5', 'a_b-c', 'x' * 32, ' P3 '):
        got = S.set_reviewer(name)
        assert got['ok'] and got['name'] == name.strip()
    for name in ('', ' ', 'P 2', 'có dấu', 'x' * 33, 'a/b', '..', None, 5):
        r = S.set_reviewer(name)
        assert not r['ok'] and 'không hợp lệ' in r['msg']
        with pytest.raises(na.RunError):
            ra.check_reviewer(name.strip() if isinstance(name, str) else name)
    assert S.default_reviewer() == 'x' * 32 or S.default_reviewer()
    assert ra.check_reviewer('P2') == 'P2' == cai_dat.check_reviewer('P2')
    assert 'REVIEWER_RE' in open(os.path.join(TOOL, 'cai_dat.py'), encoding='utf-8').read()
    src = open(os.path.join(TOOL, 'cai_dat.py'), encoding='utf-8').read()
    assert 'A-Za-z0-9_-' not in src.replace('[A-Za-z0-9_.-]{1,64}', '')          # không nhân bản regex tên người rà


def test_reviewer_saved_and_read_back_and_applies_from_next_run(tmp_path, world):
    s = settings_in(tmp_path)
    assert s.next_reviewer('P2') == 'P2'
    assert s.set_reviewer('P3')['ok']
    assert settings_in(tmp_path).default_reviewer() == 'P3'
    old = cai_dat.install(s)
    try:
        rd = make_dot_run(world, 'Khoi', decisions={'a1': 'nhan'})
        ctx = ra.AppCtx(reviewer='P2', run_dir=rd)
        assert ctx.reviewer == 'P2' and ctx.next_reviewer() == 'P3'              # lượt đang mở giữ P2, lượt sau dùng P3
        store = ra.Store(rd, ctx.reviewer)
        assert store.path.endswith('triage_P2.csv')
        nxt = ra.Store(make_dot_run(world, 'Nam'), ctx.next_reviewer())
        assert nxt.path.endswith('triage_P3.csv') and store.path.endswith('triage_P2.csv')
    finally:
        cai_dat.install(old)
    html = cai_dat_ui.reviewer_info_html(s.snapshot(), 'P2', 'Khoi', 'P3')
    assert 'triage_P2.csv' in html and 'từ lượt sau dùng <b>P3</b>' in html


# ---------- đường dẫn ----------
def test_clean_path_variants():
    assert cai_dat.clean_path(' "D:\\WFLW\\WFLW_images"  ') == 'D:\\WFLW\\WFLW_images'
    assert cai_dat.clean_path("'D:\\WFLW\\WFLW_images'") == 'D:\\WFLW\\WFLW_images'
    assert cai_dat.clean_path('') == '' and cai_dat.clean_path('   ') == '' and cai_dat.clean_path(None) == ''
    assert cai_dat.clean_path(os.path.join('a', '..', 'b')) == 'b'
    with pytest.raises(cai_dat.SettingsError):
        cai_dat.clean_path('a\x00b')
    with pytest.raises(cai_dat.SettingsError):
        cai_dat.clean_path('x' * 2000)


def test_check_images_dir_missing_file_and_windows_string(tmp_path):
    r = cai_dat.check_images_dir('  "D:\\WFLW\\WFLW_images" ')
    assert r['level'] == 'err' and not r['ok'] and r['path'] == 'D:\\WFLW\\WFLW_images' and 'Không thấy' in r['lines'][0]
    f = tmp_path / 'file.txt'
    f.write_text('x')
    assert cai_dat.check_images_dir(str(f))['level'] == 'err' and 'một file' in cai_dat.check_images_dir(str(f))['lines'][0]
    assert cai_dat.check_images_dir('')['level'] == 'err' and cai_dat.check_images_dir('a\x00')['level'] == 'err'


def test_check_images_dir_counts_capped_and_samples(tmp_path):
    for sub in ('0--Parade', '1--Handshake', '2--x'):
        (tmp_path / sub).mkdir()
        for i in range(12):
            (tmp_path / sub / f'{i}.JPG').write_bytes(b'x')
        (tmp_path / sub / 'ghichu.txt').write_text('x')
    r = cai_dat.check_images_dir(str(tmp_path))
    assert r['level'] == 'ok' and r['n_images'] == 36 and not r['capped'] and r['n_subdirs'] == 3 and len(r['samples']) == 3
    assert any('36 ảnh' in line for line in r['lines'])
    r = cai_dat.check_images_dir(str(tmp_path), limit_files=10)
    assert r['capped'] and r['n_images'] == 10 and any('từ 10' in line and 'trở lên' in line for line in r['lines'])
    ticks = iter(range(0, 1000, 5))
    r = cai_dat.check_images_dir(str(tmp_path), limit_seconds=2, clock=lambda: next(ticks))         # hết giờ: dừng sớm, vẫn có kết quả
    assert r['capped'] and r['n_images'] < 36
    empty = tmp_path / 'trong'
    empty.mkdir()
    assert cai_dat.check_images_dir(str(empty))['level'] == 'warn'
    assert not any(str(k).endswith(('.png', '.jpg')) for k in os.listdir(tmp_path))            # không tạo/đụng ảnh nào


def make_task(path, size=100, ext='.task', prefix=b''):
    """File .task giả: zip (như file thật của MediaPipe, có thể có byte đứng trước PK)."""
    import io
    import zipfile
    p = str(path) + ext
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as z:
        z.writestr('model.tflite', b'x' * size)
    open(p, 'wb').write(prefix + buf.getvalue())
    return p


def test_check_model_variants(tmp_path):
    ok = make_task(tmp_path / 'face_landmarker')
    r = cai_dat.check_model('"' + ok + '"')
    assert r['level'] == 'warn' and r['ok'] and 'nhỏ' not in ''.join(r['lines']) or 'khác xa' in ''.join(r['lines'])        # file giả rất nhỏ: cảnh báo kích thước
    big = make_task(tmp_path / 'big', size=3_700_000)
    r = cai_dat.check_model(big)
    assert r['level'] == 'ok' and '3,5 MB' in r['lines'][0]
    real_like = make_task(tmp_path / 'real_like', size=3_700_000, prefix=b'\x00\x00')       # file thật của MediaPipe có 2 byte 00 trước PK
    assert open(real_like, 'rb').read(4) == b'\x00\x00PK' and cai_dat.check_model(real_like)['level'] == 'ok'
    zbin = make_task(tmp_path / 'zip', size=3_700_000, ext='.bin')
    assert cai_dat.check_model(zbin)['level'] == 'warn' and 'Đuôi file' in ''.join(cai_dat.check_model(zbin)['lines'])        # sai đuôi
    (tmp_path / 'notzip.task').write_bytes(b'MZ' + b'0' * 3_700_000)
    assert cai_dat.check_model(str(tmp_path / 'notzip.task'))['level'] == 'err'
    (tmp_path / 'empty.task').write_bytes(b'')
    assert cai_dat.check_model(str(tmp_path / 'empty.task'))['level'] == 'err'
    assert cai_dat.check_model(str(tmp_path))['level'] == 'err' and cai_dat.check_model(str(tmp_path / 'khong.task'))['level'] == 'err'
    assert cai_dat.check_model('')['level'] == 'err'
    assert 'Không thấy' in cai_dat.check_model('D:\\m\\face_landmarker.task')['lines'][0]


def test_set_path_saves_validates_and_clears(S, tmp_path):
    d = tmp_path / 'WFLW_images'
    (d / 'a').mkdir(parents=True)
    (d / 'a' / '1.jpg').write_bytes(b'x')
    bad = S.set_path('images_dir', str(tmp_path / 'khong'))
    assert not bad['ok'] and bad['level'] == 'err' and S.images_dir() is None
    r = S.set_path('images_dir', f'"{d}"')
    assert r['ok'] and S.images_dir() == str(d) and settings_in(tmp_path).images_dir() == str(d)
    m = make_task(tmp_path / 'fl')
    assert S.set_path('model_path', m)['ok'] and S.model_path() == m
    assert S.set_path('images_dir', '')['ok'] and S.images_dir() is None
    with pytest.raises(ValueError):
        S.set_path('khac', 'x')


def test_preflight_and_prepare_use_configured_model(S, tmp_path, monkeypatch):
    root, tool = tmp_path / 'p', tmp_path / 'tool'
    tool.mkdir()
    (root / 'config').mkdir(parents=True)
    for f in ('m28_config.json', 'map_mp50.json'):
        (root / 'config' / f).write_text('{}')
    old = cai_dat.install(S)
    try:
        assert any('face_landmarker.task' in e and 'Cài đặt' in e for e in na.preflight(str(root), str(tool)))
        m = make_task(tmp_path / 'xx' / 'face_landmarker') if (tmp_path / 'xx').mkdir() is None else None
        assert S.set_path('model_path', m)['ok']
        assert not any('face_landmarker' in e for e in na.preflight(str(root), str(tool)))        # model ở đường dẫn đã cài là đủ
        assert na.configured_model() == m
        os.remove(m)
        assert na.configured_model() is None                                                      # file biến mất: quay về tìm mặc định
        assert any('face_landmarker' in e for e in na.preflight(str(root), str(tool)))
    finally:
        cai_dat.install(old)


# ---------- --images từ trang ----------
def test_plan_counts_and_push_model_use_images_dir(world, S):
    rd = make_dot_run(world, 'Khoi', decisions=ALL_DECIDED, done=True, inbox=False)           # meta.src trỏ vào inbox/ không còn
    m0 = day_cvat.push_model(rd, 'P2', str(world), remaining=0, environ={'CVAT_URL': URL, 'CVAT_ACCESS_TOKEN': TOKEN})
    assert not m0['enabled'] and 'Không thấy' in m0['reason'] and 'Cài đặt' in m0['reason'] and m0['images_dir'] is None
    imgs = world / 'WFLW'
    imgs.mkdir()
    for n in ('a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7'):
        (imgs / f'{n}.jpg').write_bytes(b'x')
    m1 = day_cvat.push_model(rd, 'P2', str(world), remaining=0, environ={'CVAT_URL': URL, 'CVAT_ACCESS_TOKEN': TOKEN}, images_dir=str(imgs))
    assert m1['enabled'] and m1['images_dir'] == str(imgs) and m1['plan']['via_images'] > 0 and not m1['plan']['missing']
    assert '--images' in day_cvat.push_command('Khoi', 'P2', 'demo-Khoi', str(imgs)) and TOKEN not in day_cvat.push_command('Khoi', 'P2', 'demo-Khoi', str(imgs))
    assert day_cvat._under_images(str(imgs), '../x.jpg') is None and day_cvat._under_images(str(imgs), '/etc/passwd') is None
    assert day_cvat._under_images(None, 'a.jpg') is None and day_cvat._under_images(str(imgs), 'a/b.jpg') == os.path.join(str(imgs), 'a', 'b.jpg')
    seen = {}
    old = cai_dat.install(S)
    try:
        S.save_cvat(URL, TOKEN, '', False)
        S.set_path('images_dir', str(imgs))
        m2 = day_cvat.push_model(rd, 'P2', str(world), remaining=0)                              # trên trang: lấy thư mục từ cài đặt
        assert m2['enabled'] and m2['images_dir'] == str(imgs)
        job = na.PushJob(popen=_spy_popen(seen))
        job.start('Khoi', 'runs', str(world), 'P2', m2['task'], images=m2['images_dir'])
        _wait(job)
        assert seen['cmd'][-2:] == ['--images', str(imgs)] and not any(TOKEN in c for c in seen['cmd'])
    finally:
        cai_dat.install(old)
    ok_run = make_dot_run(world, 'Nam', decisions=ALL_DECIDED, done=True)                      # ảnh còn ở chỗ cũ: không cần --images
    m3 = day_cvat.push_model(ok_run, 'P2', str(world), remaining=0, environ={'CVAT_URL': URL, 'CVAT_ACCESS_TOKEN': TOKEN}, images_dir=str(imgs))
    assert m3['enabled'] and m3['images_dir'] is None and m3['plan']['via_images'] == 0


# ---------- t_flip ----------
def test_parse_t_flip():
    assert cai_dat.parse_t_flip('0,0672') == 0.0672 == cai_dat.parse_t_flip('0.0672') == cai_dat.parse_t_flip(0.0672) == cai_dat.parse_t_flip(' 0,0672 ')
    assert cai_dat.parse_t_flip(1) == 1.0 and cai_dat.parse_t_flip('1') == 1.0 and cai_dat.parse_t_flip(None) is None
    for bad in ('', ' ', '0', '-0,1', '-0.1', '1,0001', '2', 'abc', '0,06,72', '1e9', 'nan', 'inf', float('nan'), float('inf'), True, '0,0672abc', '٠'):
        with pytest.raises(ValueError):
            cai_dat.parse_t_flip(bad)


def copy_config(tmp_path, name='m28_config.json'):
    p = tmp_path / name
    p.write_bytes(open(REAL_CONFIG, 'rb').read())
    return str(p)


def test_write_t_flip_changes_only_that_key_and_keeps_format(tmp_path):
    import difflib
    p = copy_config(tmp_path)
    raw0 = open(p, encoding='utf-8').read()
    cfg0 = json.loads(raw0)
    assert cfg0['t_flip'] is None
    for given, want in (('0,0672', 0.0672), ('0.0672', 0.0672), (0.0672, 0.0672), (0.05, 0.05)):
        r = cai_dat.write_t_flip(p, given)
        assert r['new'] == want
        raw = open(p, encoding='utf-8').read()
        cfg = json.loads(raw)
        assert cfg['t_flip'] == want
        assert {k: v for k, v in cfg.items() if k != 't_flip'} == {k: v for k, v in cfg0.items() if k != 't_flip'}          # mọi trường khác y nguyên
        assert list(cfg) == list(cfg0) and [q['name'] for q in cfg['points']] == [q['name'] for q in cfg0['points']]       # thứ tự khoá, tên 50 điểm
        changed = [ln for ln in difflib.unified_diff(raw0.splitlines(), raw.splitlines(), lineterm='', n=0) if ln[:1] in '+-' and ln[:3] not in ('+++', '---')]
        assert len(changed) == 2 and all('t_flip' in ln for ln in changed)                                                  # đúng một dòng đổi
        assert raw.endswith('}') == raw0.endswith('}') and '\r' not in raw
        assert os.listdir(tmp_path) == ['m28_config.json']
    assert cai_dat.write_t_flip(p, None)['new'] is None and open(p, encoding='utf-8').read() == raw0              # null: về đúng từng byte ban đầu
    assert open(p, 'rb').read() == open(REAL_CONFIG, 'rb').read()


def test_write_t_flip_rejects_bad_values_and_keeps_file(tmp_path):
    p = copy_config(tmp_path)
    before = open(p, 'rb').read()
    for bad in ('-1', '0', '1,5', 'chu', ''):
        with pytest.raises(ValueError):
            cai_dat.write_t_flip(p, bad)
    assert open(p, 'rb').read() == before
    open(p, 'w').write('{hong')
    with pytest.raises(cai_dat.SettingsError):
        cai_dat.write_t_flip(p, '0,06')
    with pytest.raises(cai_dat.SettingsError):
        cai_dat.write_t_flip(str(tmp_path / 'khong.json'), '0,06')
    assert open(p).read() == '{hong'


def test_write_t_flip_failure_midway_does_not_corrupt(tmp_path, monkeypatch):
    p = copy_config(tmp_path)
    before = open(p, 'rb').read()
    monkeypatch.setattr(os, 'replace', lambda a, b: (_ for _ in ()).throw(OSError(5, 'I/O error')))
    with pytest.raises(cai_dat.SettingsError) as e:
        cai_dat.write_t_flip(p, '0,0672')
    monkeypatch.undo()
    assert 'file cũ vẫn nguyên' in str(e.value) and open(p, 'rb').read() == before and os.listdir(tmp_path) == ['m28_config.json']


def test_write_t_flip_keeps_trailing_newline_and_rejects_crlf(tmp_path):
    p = tmp_path / 'c.json'
    cfg = json.loads(open(REAL_CONFIG, encoding='utf-8').read())
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    cai_dat.write_t_flip(str(p), '0,1')
    assert p.read_text(encoding='utf-8').endswith('}\n')
    p.write_bytes(p.read_bytes().replace(b'\n', b'\r\n'))
    with pytest.raises(cai_dat.SettingsError):
        cai_dat.write_t_flip(str(p), '0,2')


def test_rerunning_make_config_keeps_t_flip_written_by_the_page(tmp_path):
    import make_config
    p = copy_config(tmp_path)
    cai_dat.write_t_flip(p, '0,0672')
    old = json.load(open(p, encoding='utf-8'))
    fresh = make_config.build_config(None, None)
    kept = make_config.keep_existing(fresh, old, False)
    assert 't_flip' in kept and fresh['t_flip'] == 0.0672 and [q['name'] for q in fresh['points']] == [q['name'] for q in old['points']]
    old['status'] = 'DONG BANG 12/10'
    old['tolerance'] = 0.05
    json.dump(old, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    cai_dat.write_t_flip(p, '0,07')
    after = json.load(open(p, encoding='utf-8'))
    assert after['status'] == 'DONG BANG 12/10' and after['tolerance'] == 0.05 and after['t_flip'] == 0.07


def test_read_t_flip_states(tmp_path):
    p = copy_config(tmp_path)
    r = cai_dat.read_t_flip(p)
    assert r['ok'] and r['t_flip'] is None and not r['frozen'] and r['iod_points'] == ['p33_eye_R', 'p39_eye_L'] and r['n_points'] == 50
    d = json.load(open(p, encoding='utf-8'))
    d['status'], d['t_flip'] = 'DONG BANG 12/10', 0.0672
    json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    r = cai_dat.read_t_flip(p)
    assert r['frozen'] and r['t_flip'] == 0.0672
    assert not cai_dat.read_t_flip(str(tmp_path / 'khong.json'))['ok']
    open(p, 'w').write('[1]')
    assert not cai_dat.read_t_flip(p)['ok']
    d['t_flip'] = 'x'
    json.dump(d, open(p, 'w', encoding='utf-8'))
    assert not cai_dat.read_t_flip(p)['ok']


def test_runs_with_flags_and_busy_runs(world):
    make_dot_run(world, 'Khoi')
    make_dot_run(world, 'Nam')
    os.remove(os.path.join('runs', 'Nam', 'flags', 'flags.json'))
    os.makedirs(os.path.join('runs', '_trash', 'x', 'flags'))
    assert cai_dat.runs_with_flags('runs') == ['Khoi'] and cai_dat.runs_with_flags('khong-co') == []
    from m28core import dang_chay
    assert cai_dat.busy_runs('runs') == []
    dang_chay.acquire(os.path.join('runs', 'Khoi'), 'prepare')
    assert cai_dat.busy_runs('runs') == [('Khoi', 'prepare')]


def test_pipeline_info(tmp_path):
    (tmp_path / 'config').mkdir()
    r = cai_dat.pipeline_info(str(tmp_path))
    assert r['ok'] and r['pipe']['cvat_version'] == '2.77.0' and not r['exists']
    (tmp_path / 'config' / 'pipeline.json').write_text(json.dumps(dict(project='m28', prefix='demo-', cvat_version='2.77.0', job_size=8)))
    assert cai_dat.pipeline_info(str(tmp_path))['exists']
    (tmp_path / 'config' / 'pipeline.json').write_text('{hong')
    r = cai_dat.pipeline_info(str(tmp_path))
    assert not r['ok'] and r['error'] and r['pipe']['job_size'] == 8
    (tmp_path / 'config' / 'pipeline.json').write_text(json.dumps(dict(job_size=0)))
    assert not cai_dat.pipeline_info(str(tmp_path))['ok']
    assert 'hỏng' in cai_dat_ui.pipeline_html(r)


# ---------- thử kết nối: tiến trình con với CVAT GIẢ ----------
def child_environ(tmp_path, control=None, state=None):
    e = dict(os.environ)
    e['PYTHONPATH'] = FAKE + os.pathsep + e.get('PYTHONPATH', '')
    e['M28_FAKE_CVAT_STATE'] = str(state or (tmp_path / 'fake_state.json'))
    e.pop('M28_FAKE_CVAT_CONTROL', None)
    if control is not None:
        e['M28_FAKE_CVAT_CONTROL'] = json.dumps(control)
    return e


def try_cvat(tmp_path, control=None, url=URL, token=TOKEN, org='', timeout=30, state=None):
    return cai_dat.test_connection(url, token, org, PIPE, environ=child_environ(tmp_path, control, state), timeout=timeout)


def test_connection_ok_with_fake_cvat_and_project_states(tmp_path):
    r = try_cvat(tmp_path)
    assert r['ok'] and r['server_version'] == '2.77.0' and r['username'] == 'm28-fake-user' and r['project_found'] is False and r['error_kind'] == ''
    st = tmp_path / 'with_project.json'
    st.write_text(json.dumps(dict(next_project=4, next_task=1, next_job=100, projects=[dict(id=3, name='m28', labels=[])], tasks=[], calls=[], counters={})))
    r = try_cvat(tmp_path, state=st, org='congty')
    assert r['ok'] and r['project_found'] is True and r['project_id'] == 3 and r['org'] == 'congty'
    calls = [c['m'] for c in json.load(open(st))['calls']]
    assert 'users.retrieve_current_user' in calls and 'projects.list' in calls and 'Client.organization_slug' in calls
    assert not any(m in calls for m in ('projects.create', 'tasks.create_from_data', 'Task.remove', 'tasks.remove_by_ids', 'Task.import_annotations'))   # chỉ đọc
    assert TOKEN not in json.dumps(json.load(open(st)))                         # make_client ghi access_token là <redacted>


def test_connection_errors_have_kind_and_vietnamese_message(tmp_path):
    r = try_cvat(tmp_path, dict(auth_fail=True))
    assert not r['ok'] and r['error_kind'] == 'bad_token' and 'token' in r['message'] and 'Cài đặt' in r['message']
    r = try_cvat(tmp_path, dict(connect_fail=True))
    assert r['error_kind'] == 'server_down' and 'server tắt hoặc sai link' in r['message']
    r = try_cvat(tmp_path, dict(version='2.70.0'))
    assert r['error_kind'] == 'version_mismatch' and '2.70.0' in r['message'] and r['server_version'] == '2.70.0'
    for res in (r,):
        assert TOKEN not in json.dumps(res)


def test_connection_invalid_link_or_token_never_starts_a_process(tmp_path):
    def no_popen(*a, **k):
        raise AssertionError('không được khởi tiến trình con khi link/token sai')
    for url in ('localhost:8080', 'file:///etc/passwd', '', 'http://u:p@h'):
        r = cai_dat.test_connection(url, TOKEN, '', PIPE, popen=no_popen)
        assert r['error_kind'] == 'bad_url' and not r['ok'] and r['message']
    assert cai_dat.test_connection(URL, 'ngan', '', PIPE, popen=no_popen)['error_kind'] == 'bad_token'
    assert cai_dat.test_connection(URL, TOKEN, 'tổ chức', PIPE, popen=no_popen)['error_kind'] == 'other'


def test_connection_timeout_kills_hanging_child(tmp_path):
    t0 = time.time()
    r = try_cvat(tmp_path, dict(hang=60), timeout=3)
    assert r['error_kind'] == 'timeout' and 'không trả lời' in r['message'] and time.time() - t0 < 15
    assert not any('cai_dat_thu' in ln for ln in subprocess.run(['ps', '-eo', 'args'], capture_output=True, text=True).stdout.splitlines()
                   if 'pytest' not in ln and 'ps -eo' not in ln)                 # tiến trình con đã bị kill


def test_connection_command_has_no_token_and_env_has_it(tmp_path):
    seen = {}

    def spy(cmd, **kw):
        seen.update(cmd=cmd, **kw)
        return subprocess.Popen([sys.executable, '-c', "print('{\"ok\": true, \"server_version\": \"2.77.0\", \"username\": \"u\"}')"], **kw)
    r = cai_dat.test_connection(URL, TOKEN, 'cty', PIPE, popen=spy, environ={'PATH': os.environ.get('PATH', ''), 'CVAT_ACCESS_TOKEN': 'tok-CMD-OLD-999999'})
    assert r['ok'] and seen['env']['CVAT_ACCESS_TOKEN'] == TOKEN and seen['env']['CVAT_URL'] == URL and seen['env']['CVAT_ORG'] == 'cty'
    assert not any(TOKEN in c or 'cty' in c for c in seen['cmd']) and seen['cmd'][2].endswith(cai_dat.PROBE_SCRIPT)
    assert seen['stdin'] == subprocess.DEVNULL and 'shell' not in seen


def test_connection_garbage_output_is_scrubbed(tmp_path):
    def spy(cmd, **kw):
        return subprocess.Popen([sys.executable, '-c', f"import sys; print('rác {TOKEN} không phải json'); print('lỗi {TOKEN}', file=sys.stderr)"], **kw)
    r = cai_dat.test_connection(URL, TOKEN, '', PIPE, popen=spy)
    assert not r['ok'] and r['error_kind'] == 'other' and TOKEN not in json.dumps(r) and 'không báo kết quả' in r['message']

    def spy2(cmd, **kw):
        return subprocess.Popen([sys.executable, '-c', f"import json; print(json.dumps(dict(ok=False, error_kind='other', message='boom {TOKEN}', username='{TOKEN}')))"], **kw)
    r = cai_dat.test_connection(URL, TOKEN, '', PIPE, popen=spy2)
    assert TOKEN not in json.dumps(r)


# ---------- tiền kiểm redirect (http.server cục bộ) ----------
class _Server:
    def __init__(self, handler):
        self.srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        self.port = self.srv.server_address[1]
        self.t = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.t.start()

    @property
    def url(self):
        return f'http://127.0.0.1:{self.port}'

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


def make_handler(status=200, location=None, body=b'', delay=0):
    seen = []

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append(dict(path=self.path, headers={k.lower(): v for k, v in self.headers.items()}))
            if delay:
                time.sleep(delay)
            self.send_response(status)
            if location:
                self.send_header('Location', location)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass
    H.seen = seen
    return H


def test_probe_blocks_redirect_to_other_host_and_sends_no_token():
    h = make_handler(302, 'http://evil.invalid/api/server/about')
    srv = _Server(h)
    try:
        r = cai_dat_thu.probe(srv.url)
    finally:
        srv.close()
    assert r and not r['ok'] and r['error_kind'] == 'redirect' and 'không gửi token' in r['message'] and 'evil.invalid' in r['message']
    assert len(h.seen) == 1 and h.seen[0]['path'] == '/api/server/about'
    assert not any(k in h.seen[0]['headers'] for k in ('authorization', 'cookie')) and TOKEN not in json.dumps(h.seen)


def test_probe_redirects_scheme_or_port_change_blocked_same_origin_allowed():
    for loc in ('https://127.0.0.1/api/server/about', 'http://127.0.0.1:1/api/server/about', 'http://localhost/api/server/about'):
        srv = _Server(make_handler(301, loc))
        try:
            assert cai_dat_thu.probe(srv.url)['error_kind'] == 'redirect', loc
        finally:
            srv.close()
    srv = _Server(make_handler(301, '/api/server/about/'))
    try:
        assert cai_dat_thu.probe(srv.url) is None                                  # cùng nơi, chỉ đổi đường dẫn: đi tiếp
    finally:
        srv.close()
    srv = _Server(make_handler(302, None))
    try:
        assert cai_dat_thu.probe(srv.url)['error_kind'] == 'redirect'               # 3xx không có Location: không rõ đi đâu, dừng
    finally:
        srv.close()


def test_probe_statuses():
    for status, body, kind in ((404, b'', 'bad_url'), (200, b'<html>khong phai cvat</html>', 'bad_url'), (200, b'{"name": "x"}', 'bad_url'),
                               (200, b'[1]', 'bad_url'), (503, b'', 'other')):
        srv = _Server(make_handler(status, None, body))
        try:
            r = cai_dat_thu.probe(srv.url)
        finally:
            srv.close()
        assert r and r['error_kind'] == kind and not r['ok'], (status, r)
    for status, body in ((200, b'{"name": "Computer Vision Annotation Tool", "version": "2.77.0"}'), (401, b''), (403, b'')):
        srv = _Server(make_handler(status, None, body))
        try:
            assert cai_dat_thu.probe(srv.url) is None, status
        finally:
            srv.close()
    srv = _Server(make_handler(200, None, b'{"version":"2.77.0"}'))
    base = srv.url
    srv.close()
    r = cai_dat_thu.probe(base, timeout=2)                                          # cổng đã đóng: kết nối bị từ chối
    assert r['error_kind'] == 'server_down' and 'server tắt hoặc sai link' in r['message']
    srv = _Server(make_handler(200, None, b'{"version":"2.77.0"}', delay=3))
    try:
        r = cai_dat_thu.probe(srv.url, timeout=0.5)
    finally:
        srv.close()
    assert r['error_kind'] == 'timeout' and 'không trả lời' in r['message']
    assert cai_dat_thu.probe('http://khong-ton-tai.invalid:8080', timeout=3)['error_kind'] == 'server_down'


def test_child_process_stops_at_redirect_before_any_token_use():
    """Chạy cả tiến trình con thật (cvat-sdk THẬT nếu có, không có gói giả): redirect phải dừng trước khi SDK được dùng."""
    pytest.importorskip('cvat_sdk')
    import cvat_sdk
    if getattr(cvat_sdk, 'M28_FAKE_CVAT', False) or 'fake_cvat' in os.path.abspath(cvat_sdk.__file__):
        pytest.skip('cvat_sdk thật chưa cài (đang là gói giả)')
    h = make_handler(302, 'http://evil.invalid/api/server/about')
    srv = _Server(h)
    try:
        env = {k: v for k, v in os.environ.items() if not k.startswith('M28_FAKE')}
        env['PYTHONPATH'] = os.pathsep.join(p for p in env.get('PYTHONPATH', '').split(os.pathsep) if p and 'fake_cvat' not in p)
        env.update(CVAT_URL=srv.url, CVAT_ACCESS_TOKEN=TOKEN)
        p = subprocess.run([sys.executable, '-u', os.path.join(TOOL, 'cai_dat_thu.py'), '--version', '2.77.0', '--project', 'm28'],
                           env=env, capture_output=True, text=True, encoding='utf-8', timeout=60)
    finally:
        srv.close()
    res = json.loads(p.stdout.strip().splitlines()[-1])
    assert res['error_kind'] == 'redirect' and not res['ok'] and TOKEN not in p.stdout + p.stderr
    assert len(h.seen) == 1 and 'authorization' not in h.seen[0]['headers']


def test_fake_sdk_marker_skips_probe_but_real_always_probes(monkeypatch, tmp_path):
    """CVAT thật (không có thuộc tính M28_FAKE_CVAT) luôn qua tiền kiểm; gói giả của test thì bỏ qua."""
    called = []
    monkeypatch.setattr(cai_dat_thu, 'probe', lambda url, **k: called.append(url))
    monkeypatch.syspath_prepend(FAKE)
    for k in [k for k in sys.modules if k == 'cvat_sdk' or k.startswith('cvat_sdk.')]:
        monkeypatch.delitem(sys.modules, k)
    monkeypatch.setenv('M28_FAKE_CVAT_STATE', str(tmp_path / 'st.json'))
    r = cai_dat_thu.check(dict(url=URL, token=TOKEN, org=''), '2.77.0', 'm28')
    assert r['ok'], r
    assert called == []                                                           # gói giả: không tiền kiểm
    import cvat_sdk
    monkeypatch.setattr(cvat_sdk, 'M28_FAKE_CVAT', False)
    called.clear()
    cai_dat_thu.check(dict(url=URL, token=TOKEN, org=''), '2.77.0', 'm28')
    assert called == [URL]                                                        # không có dấu hiệu giả: tiền kiểm chạy
    src = open(os.path.join(TOOL, 'cai_dat_thu.py'), encoding='utf-8').read()
    assert 'M28_TEST_SKIP_PROBE' not in src and 'environ' not in src.split('def check')[1].split('def main')[0]        # không có công tắc bỏ tiền kiểm bằng biến môi trường
    for k in [k for k in sys.modules if k == 'cvat_sdk' or k.startswith('cvat_sdk.')]:
        sys.modules.pop(k, None)


# ---------- ranh giới import ----------
def test_modules_do_not_import_network_or_heavy_packages():
    code = ("import sys; sys.path.insert(0, %r); import cai_dat, cai_dat_ui, day_cvat; "
            "bad = [m for m in ('gradio', 'torch', 'cvat_sdk', 'numpy', 'cv2', 'mediapipe', 'http.client', 'urllib.request', 'requests') if m in sys.modules]; "
            "print('BAD', bad) if bad else print('ok')") % TOOL
    r = subprocess.run([sys.executable, '-I', '-c', code], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0 and r.stdout.strip() == 'ok', r.stdout + r.stderr
    for fn in ('cai_dat.py', 'cai_dat_ui.py'):
        src = open(os.path.join(TOOL, fn), encoding='utf-8').read()
        for net in ('import socket', 'http.client', 'urllib.request', 'urlopen', 'import requests', 'import cvat_sdk', 'from cvat_sdk', 'shell=True', 'share=True',
                    'import torch', 'logging.basicConfig', 'set_debug'):
            assert net not in src, (fn, net)
        assert not any(ln.startswith(('import gradio', 'from gradio')) for ln in src.splitlines())
    thu = open(os.path.join(TOOL, 'cai_dat_thu.py'), encoding='utf-8').read()
    import inspect
    assert 'uthorization' not in inspect.getsource(cai_dat_thu.probe) and 'CVAT_ACCESS_TOKEN' not in inspect.getsource(cai_dat_thu.probe)      # tiền kiểm không mang token
    assert 'import logging' not in thu and 'basicConfig' not in thu and 'set_debug' not in thu and 'print_exc' not in thu
    ui = open(os.path.join(TOOL, 'cai_dat_ui.py'), encoding='utf-8').read()
    assert 'gr.State(token' not in ui and 'allowed_paths' not in ui


# ---------- HTML thuần của tab ----------
def test_status_and_test_html_never_show_token(S):
    S.save_cvat(URL, TOKEN, 'cty', False)
    pi = dict(project='m28')
    snap = S.snapshot()
    h = cai_dat_ui.status_html(snap, pi)
    assert '○ Chưa thử' in h and '••••3456' in h and 'nhập trong phiên này' in h and TOKEN not in h and 'cty' in h
    ok = dict(ok=True, error_kind='', message='', server_version='2.77.0', username='an', project_found=True, project_id=3, org='cty')
    S.record_test(URL, TOKEN, 'cty', ok)
    h = cai_dat_ui.status_html(S.snapshot(), pi)
    assert '● Đã kết nối (thử lúc' in h and '2.77.0' in h and 'an' in h and 'id 3' in h and TOKEN not in h
    S.record_test(URL, TOKEN, 'cty', dict(ok=False, error_kind='bad_token', message='sai', server_version='', username='', project_found=None, project_id=None, org=''))
    assert '● Lỗi: sai token' in cai_dat_ui.status_html(S.snapshot(), pi)
    S.save_cvat(URL, TOKEN2, 'cty', False)                                       # đổi giá trị: kết quả thử cũ không còn đúng
    assert '○ Chưa thử' in cai_dat_ui.status_html(S.snapshot(), pi)
    S.forget_cvat()
    assert '○ Chưa có link/token' in cai_dat_ui.status_html(S.snapshot(), pi)
    t = cai_dat_ui.test_html(ok, 'm28', typed=True)
    assert 'Kết nối được' in t and 'chưa bấm Lưu' in t and 'project m28: đã có (id 3)' in t
    t = cai_dat_ui.test_html(dict(ok, project_found=False, project_id=None), 'm28')
    assert 'chưa có (tool tạo khi đẩy lần đầu)' in t
    t = cai_dat_ui.test_html(dict(ok=False, error_kind='redirect', message='<script>x</script>'), 'm28')
    assert '<script>' not in t and 'link bị chuyển hướng' in t


def test_html_escapes_untrusted_values(S, tmp_path):
    S.save_cvat('http://localhost:8080/"><img src=x onerror=alert(1)>', TOKEN, '', False)       # check_url từ chối: không vào trạng thái
    assert S.effective()['url'] == ''
    r = cai_dat.check_images_dir(str(tmp_path / '<b>x</b>'))
    assert '<b>x</b>' not in cai_dat_ui.check_html(r) and '&lt;b&gt;x&lt;/b&gt;' in cai_dat_ui.check_html(r)
    d = tmp_path / '<i>'
    d.mkdir()
    (d / 'a.jpg').write_bytes(b'x')
    assert '<i>' not in cai_dat_ui.check_html(cai_dat.check_images_dir(str(d)))
    assert '<i>' not in cai_dat_ui.paths_info_html(dict(prefs=dict(images_dir=str(d), model_path='<m>', reviewer='')))


def test_tflip_html_and_confirm_text():
    info = dict(ok=True, error='', t_flip=None, status='NHAP - cho P3 chot, dong bang 12/10', frozen=False, iod_points=['p33_eye_R', 'p39_eye_L'], n_points=50)
    h = cai_dat_ui.tflip_info_html(info)
    assert 'chưa đặt (null): mọi cờ = false' in h and 'p33_eye_R' in h and '0,0672' in h and '15%' in h and 'bản nháp' in h
    info.update(t_flip=0.0672, frozen=True, status='DONG BANG 12/10')
    h = cai_dat_ui.tflip_info_html(info)
    assert '0,0672' in h and 'ĐÃ ĐÓNG BĂNG' in h
    c = cai_dat_ui.tflip_confirm_html(None, 0.0672, 'D:\\WFLW\\WFLW_images')
    assert 'đóng băng 12/10' in c and 'lệch nhau' in c and '--force flags autoqc overlays' in c and 'D:\\WFLW\\WFLW_images' in c and '0,0672' in c


# ---------- giao diện Gradio: dựng được, đủ elem_id, handler gọi trực tiếp ----------
OLD_IDS = ('btn-push', 'push-panel', 'push-msg', 'push-prog', 'push-log', 'push-cancel', 'push-confirm', 'push-confirm-ok', 'push-confirm-cancel', 'push-result',
           'tab-dot', 'dot-root', 'dot-act', 'dot-act-go', 'dot-modal', 'dot-modal-ok', 'dot-modal-cancel', 'btn-nhan', 'btn-xong', 'tab-ra', 'tab-nap', 'shown',
           'tabs', 'btn-dong', 'close-confirm', 'close-confirm-ok', 'tab-cakho', 'tab-hop', 'nap-go', 'progress')
NEW_IDS = ('tab-caidat', 'cd-cvat-status', 'cd-url', 'cd-token', 'cd-eye', 'cd-org', 'cd-remember', 'cd-remember-note', 'cd-save', 'cd-test', 'cd-forget', 'cd-cvat-msg',
           'cd-forget-confirm', 'cd-forget-ok', 'cd-forget-cancel', 'cd-reviewer-info', 'cd-reviewer', 'cd-reviewer-save', 'cd-paths-info', 'cd-images', 'cd-images-check',
           'cd-images-save', 'cd-model', 'cd-model-check', 'cd-model-save', 'cd-tflip-info', 'cd-tflip', 'cd-tflip-ack', 'cd-tflip-set', 'cd-tflip-null', 'cd-tflip-confirm',
           'cd-tflip-ok', 'cd-tflip-cancel', 'cd-pipeline')


def build(world, S=None, reviewer='P2'):
    pytest.importorskip('gradio')
    rd = make_dot_run(world, 'Khoi', decisions=ALL_DECIDED)
    ra.prepare_env(rd)
    ctx = ra.AppCtx(reviewer=reviewer, run_dir=rd)
    store = ra.Store(rd, reviewer)
    demo, _theme = ra.build_ui(store, ctx)
    return demo, ctx, store


def handlers(demo):
    out = {}
    for f in demo.fns.values():
        if f.fn is not None and getattr(f.fn, '__module__', '') == 'cai_dat_ui' and getattr(f.fn, '__name__', '') in ('on_show', 'on_save', 'on_test', 'on_forget_open', 'on_forget_ok', 'on_forget_cancel',
                                                                   'on_reviewer', 'on_tflip', 'on_tf_ok', 'on_tf_cancel', 'on_check', 'on_path_save'):
            out.setdefault(f.fn.__name__, []).append(f)
    return out


def as_map(bf, result):
    return {getattr(c, 'elem_id', None) or id(c): v for c, v in zip(bf.outputs, result)}


def text_of(v):
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False, default=str)
    return str(v)


def test_gradio_tab_builds_with_all_old_and_new_element_ids(world):
    demo, ctx, store = build(world)
    ids = {getattr(b, 'elem_id', None) for b in demo.blocks.values()}
    for want in OLD_IDS + NEW_IDS:
        assert want in ids, want
    tok = next(b for b in demo.blocks.values() if getattr(b, 'elem_id', None) == 'cd-token')
    assert tok.type == 'password' and not tok.value
    labels = [b.label for b in demo.blocks.values() if getattr(b, 'elem_id', None) == 'cd-remember']
    assert labels == ['Nhớ trên máy này'] and next(b for b in demo.blocks.values() if getattr(b, 'elem_id', None) == 'cd-remember').value is False
    tabs = [b for b in demo.blocks.values() if type(b).__name__ == 'Tab']
    assert [t.label for t in tabs][-1] == 'Cài đặt' and [t.label for t in tabs][:5] == ['Rà soát', 'Nạp ảnh', 'Các đợt', 'Ca khó', 'Họp team']
    assert next(b for b in demo.blocks.values() if getattr(b, 'elem_id', None) == 'tabs').selected == 'ra'      # tab mặc định không đổi
    for f in demo.fns.values():                                                                              # mọi handler của tab: riêng tư
        if f.fn is not None and getattr(f.fn, '__module__', '') == 'cai_dat_ui':
            assert f.api_visibility == 'private', f.fn.__name__


def test_gradio_handlers_save_test_forget_without_leaking_token(world, monkeypatch, capsys):
    for v in ('CVAT_URL', 'CVAT_ACCESS_TOKEN', 'CVAT_ORG'):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv('PYTHONPATH', FAKE + os.pathsep + os.environ.get('PYTHONPATH', ''))
    monkeypatch.setenv('M28_FAKE_CVAT_STATE', str(world / 'fake_state.json'))
    demo, ctx, store = build(world)
    H = handlers(demo)
    save, test, fo, fok = H['on_save'][0], H['on_test'][0], H['on_forget_open'][0], H['on_forget_ok'][0]
    seen = []

    def call(bf, *args):
        res = bf.fn(*args)
        m = as_map(bf, res)
        seen.append(json.dumps({str(k): text_of(v) for k, v in m.items()}, ensure_ascii=False))
        return m
    # link sai bị từ chối, không đổi gì
    m = call(save, 'localhost:8080', TOKEN, '', False, None)
    assert 'phải bắt đầu bằng http' in m['cd-cvat-msg'] and cai_dat.get().effective()['source'] is None
    m = call(save, 'file:///etc/passwd', TOKEN, '', False, None)
    assert 'Chỉ nhận link http' in m['cd-cvat-msg']
    st = call(test, '', '', '', None)                                          # chưa có gì để thử
    assert 'Chưa nhập link' in st['cd-cvat-msg'] or 'link' in st['cd-cvat-msg']
    # lưu hợp lệ, không Nhớ
    rev0 = cai_dat.get().rev
    m = call(save, URL, TOKEN, '', False, rev0)
    assert 'Đã lưu cho phiên này' in m['cd-cvat-msg'] and m['cd-token']['value'] == '' and '••••3456' in m['cd-token']['placeholder']
    assert m['cd-url'] == URL and m['cd-remember'] is False and 'nhập trong phiên này' in m['cd-cvat-status'] and '••••3456' in m['cd-cvat-status']
    assert not os.path.exists(cai_dat.get().path_cvat() or '/nonexistent')
    # rev cũ bị từ chối nhẹ nhàng
    m = call(save, URL, TOKEN2, '', False, rev0)
    assert 'tab khác' in m['cd-cvat-msg'] and cai_dat.get().effective()['token'] == TOKEN
    # thử kết nối với CVAT giả
    m = call(test, '', '', '', cai_dat.get().rev)
    assert 'Kết nối được' in m['cd-cvat-msg'] and '2.77.0' in m['cd-cvat-msg'] and 'm28-fake-user' in m['cd-cvat-msg']
    assert '● Đã kết nối' in m['cd-cvat-status']
    # đẩy/xoá đang chạy thì từ chối Lưu và Quên
    ctx.push_job.state = 'dang_chay'
    ctx.push_job.run = 'Khoi'
    m = call(save, URL, TOKEN2, '', False, cai_dat.get().rev)
    assert 'chờ xong' in m['cd-cvat-msg'] and cai_dat.get().effective()['token'] == TOKEN
    m = call(fo, cai_dat.get().rev)
    assert 'chờ xong' in m['cd-cvat-msg']
    ctx.push_job.state = 'chua'
    # đang đóng thì từ chối mọi ghi
    ctx.closing = True
    for bf, args in ((save, (URL, TOKEN2, '', False, None)), (fo, (None,)), (H['on_reviewer'][0], ('P4', None)), (test, ('', '', '', None))):
        assert nap_closing(call(bf, *args))
    assert cai_dat.get().effective()['token'] == TOKEN and cai_dat.get().default_reviewer() == ''
    ctx.closing = False
    # Nhớ trên máy này: file có quyền chặt, rồi Quên
    m = call(save, URL, TOKEN2, '', True, cai_dat.get().rev)
    assert 'Nhớ trên máy này' in m['cd-cvat-msg'] and m['cd-remember'] is True and 'đã lưu trên máy' in m['cd-cvat-status']
    path = cai_dat.get().path_cvat()
    assert os.path.isfile(path) and json.load(open(path))['token'] == TOKEN2
    if os.name != 'nt':
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    m = call(fo, cai_dat.get().rev)
    assert m['cd-forget-confirm']['visible'] is True and 'Quên token' in m['cd-forget-body']
    m = call(fok, cai_dat.get().rev)
    assert not os.path.exists(path) and 'Đã quên' in m['cd-cvat-msg'] and m['cd-forget-confirm']['visible'] is False and '○ Chưa có link/token' in m['cd-cvat-status']
    # token sai ở bước thử (auth_fail): thông báo đúng nguyên nhân
    monkeypatch.setenv('M28_FAKE_CVAT_CONTROL', json.dumps(dict(auth_fail=True)))
    m = call(test, URL, TOKEN, '', None)
    assert 'từ chối token' in m['cd-cvat-msg'] and 'sai token' in m['cd-cvat-msg'] and 'chưa bấm Lưu' in m['cd-cvat-msg']
    monkeypatch.setenv('M28_FAKE_CVAT_CONTROL', json.dumps(dict(version='2.70.0')))
    m = call(test, URL, TOKEN, '', None)
    assert 'khác phiên bản' in m['cd-cvat-msg'] and '2.70.0' in m['cd-cvat-msg']
    out = capsys.readouterr()
    for blob in seen + [out.out, out.err]:
        assert TOKEN not in blob and TOKEN2 not in blob, blob[:200]


def nap_closing(m):
    return any(na.CLOSING_MSG in text_of(v) for v in m.values())


def test_gradio_handler_unexpected_error_is_scrubbed(world, monkeypatch, capsys):
    demo, ctx, store = build(world)
    save = handlers(demo)['on_save'][0]

    def boom(*a, **k):
        raise RuntimeError(f'hỏng bất ngờ {TOKEN}')
    monkeypatch.setattr(cai_dat.Settings, 'save_cvat', boom)
    res = save.fn(URL, TOKEN, '', False, None)
    m = as_map(save, res)
    out = capsys.readouterr()
    assert 'Lỗi không lường trước (RuntimeError)' in m['cd-cvat-msg'] and TOKEN not in m['cd-cvat-msg'] and 'Traceback' not in m['cd-cvat-msg']
    assert TOKEN not in out.err + out.out and 'RuntimeError' in out.err                     # traceback (đã lọc) ra console


def test_gradio_handlers_reviewer_paths_tflip(world, monkeypatch, tmp_path):
    demo, ctx, store = build(world)
    H = handlers(demo)
    rev = H['on_reviewer'][0]
    m = as_map(rev, rev.fn('P3', None))
    assert 'Đã lưu tên người rà mặc định: P3' in m['cd-reviewer-msg'] and m['cd-reviewer'] == 'P3'
    assert 'triage_P2.csv' in m['cd-reviewer-info'] and 'từ lượt sau dùng <b>P3</b>' in m['cd-reviewer-info']
    assert ctx.reviewer == 'P2' and store.reviewer == 'P2' and ctx.next_reviewer() == 'P3'
    m = as_map(rev, rev.fn('P 3!', None))
    assert 'không hợp lệ' in m['cd-reviewer-msg']
    # kiểm đường dẫn
    chk = H['on_check']
    imgs = tmp_path / 'WFLW_images' / '0--Parade'
    imgs.mkdir(parents=True)
    (imgs / 'a.jpg').write_bytes(b'x')
    for bf in chk:
        is_images = getattr(bf.inputs[0], 'elem_id', None) == 'cd-images'
        m = as_map(bf, bf.fn(f'"{imgs.parent}"' if is_images else make_task(tmp_path / 'fl')))
        text = text_of(m.get('cd-images-msg')) + text_of(m.get('cd-model-msg'))
        assert 'nap-box' in text and ('nap-warn' in text or 'nap-ok' in text), text
    # t_flip trên bản sao config trong thư mục tạm của world
    cfg = os.path.join(str(world), 'config', 'm28_config.json')
    open(cfg, 'wb').write(open(REAL_CONFIG, 'rb').read())
    tf = H['on_tflip']
    set_h, null_h = tf[0], tf[1]
    first = as_map(set_h, set_h.fn('', False, None))
    assert 'Chưa nhập t_flip' in first['cd-tflip-msg']
    assert not (isinstance(first['cd-tflip-confirm'], dict) and first['cd-tflip-confirm'].get('visible'))
    bad = as_map(set_h, set_h.fn('-1', False, None))
    assert 'lớn hơn 0' in bad['cd-tflip-msg']
    before = open(cfg, 'rb').read()
    m = as_map(set_h, set_h.fn('0,0672', False, None))
    assert m['cd-tflip-confirm']['visible'] is True and '--force flags autoqc overlays' in m['cd-tflip-body'] and m['cd-tflip-token']
    assert open(cfg, 'rb').read() == before                                    # mới mở hộp xác nhận: chưa ghi gì
    ok_h, cancel_h = H['on_tf_ok'][0], H['on_tf_cancel'][0]
    cancel_h.fn()
    m = as_map(ok_h, ok_h.fn(m['cd-tflip-token'], False))                      # token hộp đã huỷ: không ghi
    assert 'đã cũ' in m['cd-tflip-msg'] and open(cfg, 'rb').read() == before
    m = as_map(set_h, set_h.fn('0,0672', False, None))
    m2 = as_map(ok_h, ok_h.fn(m['cd-tflip-token'], False))
    assert 'Đã ghi' in m2['cd-tflip-msg'] and 'Khoi' in m2['cd-tflip-msg'] and json.load(open(cfg))['t_flip'] == 0.0672
    assert m2['cd-tflip-confirm']['visible'] is False and '0,0672' in m2['cd-tflip-info']
    m3 = as_map(ok_h, ok_h.fn(m['cd-tflip-token'], False))                     # dùng lại mã: không ghi lần hai
    assert 'đã cũ' in m3['cd-tflip-msg']
    m = as_map(null_h, null_h.fn('', False, None))
    ok_h.fn(m['cd-tflip-token'], False)
    assert json.load(open(cfg))['t_flip'] is None and open(cfg, 'rb').read() == before
    # đang có job: từ chối
    ctx.job.state = 'dang_chay'
    ctx.job.run = 'Khoi'
    assert 'chờ xong' in as_map(set_h, set_h.fn('0,05', False, None))['cd-tflip-msg']
    ctx.job.state = 'chua'
    # đã đóng băng: cần tick
    d = json.load(open(cfg))
    d['status'] = 'DONG BANG 12/10'
    json.dump(d, open(cfg, 'w'), ensure_ascii=False, indent=1)
    m = as_map(set_h, set_h.fn('0,05', False, None))
    assert 'đóng băng' in m['cd-tflip-msg'] and not (isinstance(m['cd-tflip-confirm'], dict) and m['cd-tflip-confirm'].get('visible'))
    m = as_map(set_h, set_h.fn('0,05', True, None))
    assert m['cd-tflip-confirm']['visible'] is True
    # đang đóng trang: từ chối
    ctx.closing = True
    assert na.CLOSING_MSG in as_map(set_h, set_h.fn('0,05', True, None))['cd-tflip-msg']
    ctx.closing = False


def test_on_show_reloads_only_when_rev_changed(world):
    demo, ctx, store = build(world)
    show = handlers(demo)['on_show'][0]
    first = as_map(show, show.fn(None))
    assert 'cd-url' in first and first['cd-url'] == ''
    rev = cai_dat.get().rev
    again = as_map(show, show.fn(rev))                                       # cùng rev: chỉ vẽ lại phần hiển thị, KHÔNG đụng ô đang gõ
    assert 'cd-url' in again and again['cd-url'] == {'__type__': 'update'} and again['cd-token'].get('placeholder')
    cai_dat.get().set_reviewer('P4')                                         # đổi từ "tab khác": rev đổi
    reloaded = as_map(show, show.fn(rev))
    assert reloaded['cd-reviewer'] == 'P4'


# ---------- không rò token (kịch bản đầy đủ) ----------
def test_full_scenario_leaves_token_only_in_cvat_json(tmp_path, world, monkeypatch, capsys, caplog):
    import logging
    caplog.set_level(logging.DEBUG)
    for v in ('CVAT_URL', 'CVAT_ACCESS_TOKEN', 'CVAT_ORG'):
        monkeypatch.delenv(v, raising=False)
    cfgdir = tmp_path / 'user_cfg'
    S = cai_dat.Settings(environ={cai_dat.ENV_DIR: str(cfgdir / 'm28')}, platform='linux', project_root=str(tmp_path / 'proj'))
    old = cai_dat.install(S)
    try:
        texts = []
        r = S.save_cvat(URL, TOKEN, 'cty', False)
        texts.append(r['msg'])
        ok = cai_dat.test_connection(URL, TOKEN, 'cty', PIPE, environ=child_environ(tmp_path))
        bad = cai_dat.test_connection(URL, TOKEN, '', PIPE, environ=child_environ(tmp_path, dict(auth_fail=True)))
        down = cai_dat.test_connection(URL, TOKEN, '', PIPE, environ=child_environ(tmp_path, dict(connect_fail=True)))
        S.record_test(URL, TOKEN, 'cty', ok)
        texts += [json.dumps(x) for x in (ok, bad, down)] + [cai_dat_ui.status_html(S.snapshot(), PIPE), cai_dat_ui.test_html(bad, 'm28'), repr(S), json.dumps(S.snapshot(), default=str)]
        rd = make_dot_run(world, 'Khoi')
        job = na.PushJob(popen=_spy_popen({}))
        job.start('Khoi', 'runs', str(world), 'P2', 'demo-Khoi')
        _wait(job)
        texts += list(job.snapshot()['lines'])
        r = S.save_cvat(URL, TOKEN2, 'cty', True)                                 # bật Nhớ: token đổi nằm trong cvat.json (và chỉ ở đó)
        texts.append(r['msg'])
        assert os.path.isfile(S.path_cvat()) and TOKEN2 in open(S.path_cvat(), encoding='utf-8').read()
        texts.append(S.forget_cvat()['msg'])
    finally:
        cai_dat.install(old)
    out = capsys.readouterr()
    blob = '\n'.join(texts + [out.out, out.err, caplog.text])
    assert TOKEN not in blob and TOKEN2 not in blob
    for root in (str(tmp_path), str(world)):
        for f in files_under(root):
            if os.path.basename(f) == 'cvat.json':
                continue
            try:
                data = open(f, 'rb').read()
            except OSError:
                continue
            assert TOKEN.encode() not in data and TOKEN2.encode() not in data, f
    assert not os.path.exists(S.path_cvat())                                   # Quên xong: không còn file nào chứa token
