"""Kiểm thử đầu-cuối tính năng "ca khó và họp team" bằng trình duyệt thật (Chromium qua Playwright). TUỲ CHỌN.

Cần playwright và Chromium, KHÔNG nằm trong requirements, pytest không gom file này (tên không khớp test_*.py).
Chỉ chạy trên Linux (dùng `lsof` để kiểm cổng chỉ bind 127.0.0.1). Cần một thư mục chạy (--work) có config/, data/ (có manifest.csv),
runs/F5 (5 mặt in-cabin đã prepare) và runs/NAP_001 (lượt từ tab Nạp ảnh, có inbox/), face_landmarker.task không bắt buộc. Các lượt chứa ảnh người lái xe
nên chỉ để ngoài git. Ví dụ (Linux cloud):

    cd $W && PYTHONPATH=$S/pwlib PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers python $M/tests/e2e_ca_kho.py --work $W --shots $S/ui_shots

Các bước (mỗi bước dùng app thật, proxy chết để chứng minh không cần mạng, mọi tiến trình dọn ở `finally`, cổng 7881-7889):
  1  chuẩn bị: chép runs/F5 thành CKA, CKB; runs/NAP_001 thành CKN; xoá outputs/ca_kho của thư mục chạy
  2  runs/CKA người P1: phím K mở panel, gõ ghi chú (n, g, k không kích hoạt gì), lưu 3 ca; triage_P1.csv không đổi; K ở tab khác không mở panel;
     rồi runs/CKN người P1 đánh dấu 1 ca
  3  tab Ca khó: 4 ca, sửa, xoá (Không rồi Xác nhận), hộp đỏ về CKN, xuất gói (tải về, mở zip kiểm)
  4  runs/CKB người P3: 2 ca (một ca cùng ảnh F_001.png), xuất gói
  5  `review_app.py --nap P5`: tab Họp team nhập 2 gói + zip độc hại + gói trùng, lưới, nhóm, lọc, chi tiết, trạng thái, trình chiếu, mở lại phiên,
     biên bản (số P, QĐ tiếp theo theo problem-backlog.md và so-quyet-dinh.md hiện có trong repo)
  6  không có request nào ra ngoài 127.0.0.1
  7  ảnh chụp cakho_*.png vào --shots (desktop 1440x900, hẹp 420 px)
"""
import argparse
import csv
import glob
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(CODE, 'tool'))
import e2e_review_ui as base  # noqa: E402
from e2e_review_ui import check, log, listeners, start, stop_all, wait_port, DEAD_PROXY  # noqa: E402

REPO = os.path.abspath(os.path.join(CODE, '..', '..'))
PROXY = dict(HTTP_PROXY=DEAD_PROXY, HTTPS_PROXY=DEAD_PROXY, http_proxy=DEAD_PROXY, https_proxy=DEAD_PROXY)
APP = os.path.join(CODE, 'tool', 'review_app.py')
ALL_REQUESTS = []


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest() if os.path.exists(path) else None


def read_marks(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


class Page:
    def __init__(self, pw, port, w=1440, h=900):
        self.ui = base.Ui(pw, port, w, h)
        self.pg = self.ui.page
        self.port = port
        self.pg.on('request', lambda r: ALL_REQUESTS.append(r.url))

    def open(self, wait='#info .face-name'):
        self.pg.goto(f'http://127.0.0.1:{self.port}/')
        self.pg.wait_for_selector(wait, timeout=60000)

    def tab(self, name):
        self.pg.get_by_role('tab', name=name, exact=True).click()
        self.pg.wait_for_timeout(500)

    def dd_pick(self, sel, text):
        """Chọn một mục trong Dropdown của Gradio theo chữ hiển thị."""
        self.pg.locator(f'{sel} input').first.click()
        item = self.pg.locator(f'{sel} ul[role="listbox"] li, ul[role="listbox"] li').filter(has_text=text).first
        item.wait_for(timeout=10000)
        item.click()
        self.pg.wait_for_timeout(250)

    def shot(self, shots, name, full=False):
        self.pg.screenshot(path=os.path.join(shots, name + '.png'), full_page=full)

    def no_hscroll(self, w):
        return self.pg.evaluate('document.documentElement.scrollWidth') <= w

    def close(self):
        self.ui.close()


def stop(p):
    p.terminate()
    try:
        p.wait(timeout=20)
    except subprocess.TimeoutExpired:
        p.kill()


def run_app(args, W, port, log_path):
    p = start([sys.executable, APP] + args, W, port, PROXY, log_path)
    wait_port(port, p)
    ls = listeners(port)
    check(ls and all(f'127.0.0.1:{port}' in l for l in ls) and not any('*:' in l or '0.0.0.0' in l for l in ls), f'cổng {port} chỉ bind 127.0.0.1')
    return p


# ---------- bước 1 ----------
def step1(W):
    log('\n== BƯỚC 1: chuẩn bị ==')
    runs = os.path.join(W, 'runs')
    for dst, src in (('CKA', 'F5'), ('CKB', 'F5'), ('CKN', 'NAP_001')):
        shutil.rmtree(os.path.join(runs, dst), ignore_errors=True)
        shutil.copytree(os.path.join(runs, src), os.path.join(runs, dst))
        for d in ('review', 'push', 'xml', '_tmp'):
            shutil.rmtree(os.path.join(runs, dst, d), ignore_errors=True)
    shutil.rmtree(os.path.join(W, 'outputs', 'ca_kho'), ignore_errors=True)
    check(os.path.isdir(os.path.join(runs, 'CKN', 'inbox')) and os.path.isfile(os.path.join(W, 'data', 'manifest.csv')), 'CKN có inbox/, W có data/manifest.csv')
    gi = [sha(os.path.join(REPO, f)) for f in ('problem-backlog.md', 'so-quyet-dinh.md')]
    return gi


# ---------- bước 2 ----------
def step2(pw, W, shots):
    log('\n== BƯỚC 2: đánh dấu ca khó ở tab Rà soát (CKA, P1) ==')
    run = os.path.join(W, 'runs', 'CKA')
    marks = os.path.join(run, 'ca_kho.csv')
    tri = os.path.join(run, 'review', 'triage_P1.csv')
    p = run_app(['runs/CKA', 'P1'], W, 7881, os.path.join(shots, 'app_ck1.log'))
    pg = Page(pw, 7881)
    try:
        pg.open()
        ui = pg.ui
        page = pg.pg
        check(page.locator('#btn-cakho').is_visible() and '<kbd>K</kbd>' in page.inner_html('#keys'), 'có nút Ca khó (K) và dòng phím tắt K')
        check(page.locator('#ck-panel').count() == 0 or not page.locator('#ck-panel').first.is_visible(), 'panel ẩn lúc đầu')
        first = ui.cur()
        page.keyboard.press('n')                                   # tạo triage_P1.csv để so hash
        ui.wait_done(1)
        h0, prog0 = sha(tri), ui.progress()
        check(h0 is not None and prog0[0] == 1, f'đã có triage_P1.csv ({prog0})')
        cur = ui.cur()
        page.keyboard.press('k')
        page.wait_for_selector('#ck-panel', state='visible', timeout=10000)
        check(cur in page.inner_text('#ck-panel-face'), f'panel hiện tên mặt đang xem ({cur})')
        page.locator('#ck-loai label:has(input[value="SWAP"])').click()
        page.wait_for_function("!!(document.activeElement && document.activeElement.closest('#ck-note'))", timeout=5000)
        check(True, 'mở panel: focus vào ô ghi chú')
        page.keyboard.type('nkg đổi chỗ mắt', delay=30)
        page.wait_for_timeout(600)
        check(page.locator('#ck-note textarea').input_value() == 'nkg đổi chỗ mắt', 'gõ chữ n, g, k vào ô ghi chú: thành chữ')
        check(sha(tri) == h0 and ui.progress() == prog0 and page.locator('#ck-panel').first.is_visible() and ui.cur() == cur,
              'gõ n/g/k trong ô ghi chú không Nhận/Gán tay và không đóng panel')
        page.screenshot(path=os.path.join(shots, 'cakho_01_panel_desktop.png'))
        page.click('#ck-save')
        page.wait_for_selector('#ck-panel', state='hidden', timeout=10000)
        rows = read_marks(marks)
        check(len(rows) == 1 and rows[0]['anh'] == cur and rows[0]['loai'] == 'SWAP' and rows[0]['nguoi'] == 'P1' and rows[0]['luot'] == 'CKA'
              and rows[0]['ghi_chu'] == 'nkg đổi chỗ mắt' and rows[0]['quyet_dinh_ra'] == '', f'ca 1 đã ghi (mặt chưa rà nên quyet_dinh_ra rỗng): {rows[0]}')
        check('SWAP' in page.inner_text('#ck-badge'), 'nhãn "Đã đánh dấu: SWAP" hiện cạnh nút')
        check(sha(tri) == h0, 'triage_P1.csv không đổi sau khi lưu ca khó')
        # bấm K lần nữa trên mặt đã đánh dấu: là sửa, điền sẵn giá trị cũ
        page.keyboard.press('k')
        page.wait_for_selector('#ck-panel', state='visible')
        check(page.locator('#ck-loai input:checked').get_attribute('value') == 'SWAP' and page.locator('#ck-note textarea').input_value() == 'nkg đổi chỗ mắt'
              and page.locator('#ck-unmark').is_visible(), 'K lần nữa: điền sẵn giá trị cũ, có nút Unmark')
        page.locator('#ck-note textarea').fill('đổi chỗ mắt (đã sửa)')
        page.click('#ck-save')
        page.wait_for_selector('#ck-panel', state='hidden')
        rows = read_marks(marks)
        check(len(rows) == 1 and rows[0]['ghi_chu'] == 'đổi chỗ mắt (đã sửa)' and rows[0]['tao_luc'] != '' , 'bấm K lần nữa là sửa, không thêm dòng')
        # thiếu loại -> cảnh báo
        page.keyboard.press('ArrowRight')
        page.wait_for_function(f"document.querySelector('#info .face-name').innerText.trim() !== '{cur}'")
        second = ui.cur()
        page.keyboard.press('k')
        page.wait_for_selector('#ck-panel', state='visible')
        check(page.locator('#ck-loai input:checked').count() == 0 and not page.locator('#ck-unmark').is_visible(), 'mặt chưa đánh dấu: panel trống, không có Unmark')
        page.click('#ck-save')
        page.wait_for_function("document.querySelector('#ck-msg').innerText.includes('Chọn loại')", timeout=10000)
        check(page.locator('#ck-panel').first.is_visible() and len(read_marks(marks)) == 1, 'thiếu loại: cảnh báo, panel còn mở, chưa ghi')
        page.locator('#ck-loai label:has(input[value="RULE"])').click()
        page.click('#ck-diem input')
        page.keyboard.type('mattrai_1')
        page.locator('#ck-diem ul[role="listbox"] li').first.click()
        page.locator('#ck-note textarea').fill('Chưa có quy tắc cho kính')
        # ảnh đổi giữa chừng: bấm mặt khác trong lưới -> panel tự đóng, Save không ghi sang mặt khác
        page.click('#ck-save')
        page.wait_for_selector('#ck-panel', state='hidden')
        rows = read_marks(marks)
        check(len(rows) == 2 and rows[1]['anh'] == second and rows[1]['loai'] == 'RULE' and rows[1]['diem'] == 'mattrai_1', f'ca 2 (RULE + điểm): {rows[1]}')
        page.keyboard.press('ArrowRight')
        page.wait_for_function(f"document.querySelector('#info .face-name').innerText.trim() !== '{second}'")
        third = ui.cur()
        page.keyboard.press('k')
        page.wait_for_selector('#ck-panel', state='visible')
        page.locator('#ck-loai label:has(input[value="CONG_CU"])').click()
        page.locator('#ck-note textarea').fill('Khó kéo điểm ở màn hẹp')
        page.locator('#grid .thumbnail-item').nth(0).click()                 # bấm ảnh khác khi panel đang mở: panel tự đóng
        page.wait_for_selector('#ck-panel', state='hidden', timeout=10000)
        check(len(read_marks(marks)) == 2, 'ảnh đổi khi panel mở: panel tự đóng, chưa ghi gì')
        ui.wait_cur(first)
        cur3 = ui.cur()
        page.keyboard.press('k')
        page.wait_for_selector('#ck-panel', state='visible')
        page.locator('#ck-loai label:has(input[value="CONG_CU"])').click()
        page.locator('#ck-note textarea').fill('Khó kéo điểm ở màn hẹp')
        page.click('#ck-save')
        page.wait_for_selector('#ck-panel', state='hidden')
        rows = read_marks(marks)
        check(len(rows) == 3 and rows[2]['loai'] == 'CONG_CU' and rows[2]['anh'] == cur3 and rows[2]['quyet_dinh_ra'] == 'nhan' and len({r['anh'] for r in rows}) == 3,
              f'ca 3 (CONG_CU) trên mặt đã Nhận: quyet_dinh_ra={rows[2]["quyet_dinh_ra"]}')
        check(sha(tri) == h0 and ui.progress() == prog0, 'sau 3 ca khó: triage_P1.csv không đổi (cùng hash), tiến độ rà vẫn như cũ')
        check(not os.path.exists(os.path.join(run, 'review', 'done.txt')), 'chưa có done.txt')
        # Unmark hai bước
        page.keyboard.press('k')
        page.wait_for_selector('#ck-panel', state='visible')
        page.click('#ck-unmark')
        page.wait_for_function("document.querySelector('#ck-unmark').innerText.includes('Bấm lần nữa')", timeout=10000)
        check(len(read_marks(marks)) == 3, 'Unmark: bấm lần đầu chỉ xin xác nhận, chưa xoá')
        page.click('#ck-cancel')
        page.wait_for_selector('#ck-panel', state='hidden')
        check(len(read_marks(marks)) == 3, 'Cancel: không bỏ đánh dấu')
        # K ở tab khác không mở panel
        page.get_by_role('tab', name='Ca khó', exact=True).click()
        page.wait_for_timeout(500)
        page.locator('#tab-cakho').click(position={'x': 5, 'y': 5})
        page.keyboard.press('k')
        page.wait_for_timeout(500)
        check(not page.locator('#ck-panel').first.is_visible(), 'K ở tab Ca khó không mở panel')
        pg.tab('Họp team')
        page.keyboard.press('k')
        page.keyboard.press('n')
        page.wait_for_timeout(400)
        check(not page.locator('#ck-panel').first.is_visible() and sha(tri) == h0, 'K và N ở tab Họp team không làm gì')
        check(not [e for e in ui.errors if 'Failed to load resource' not in e and 'ERR_' not in e and 'WebSocket' not in e], f'không lỗi JS: {ui.errors[:2]}')
    finally:
        pg.close()
        stop(p)
    # CKN
    log('  ... mở runs/CKN (lượt Nạp ảnh) người P1')
    p = run_app(['runs/CKN', 'P1'], W, 7882, os.path.join(shots, 'app_ck2.log'))
    pg = Page(pw, 7882)
    try:
        pg.open()
        pg.pg.keyboard.press('k')
        pg.pg.wait_for_selector('#ck-panel', state='visible')
        pg.pg.locator('#ck-loai label:has(input[value="KHAC"])').click()
        pg.pg.locator('#ck-note textarea').fill('Ảnh trong lượt Nạp ảnh')
        pg.pg.click('#ck-save')
        pg.pg.wait_for_selector('#ck-panel', state='hidden')
        rows = read_marks(os.path.join(W, 'runs', 'CKN', 'ca_kho.csv'))
        check(len(rows) == 1 and rows[0]['loai'] == 'KHAC' and rows[0]['luot'] == 'CKN', 'CKN: 1 ca KHAC')
        step3(pw, pg, W, shots)
    finally:
        pg.close()
        stop(p)


# ---------- bước 3 ----------
def nguon_cka(W):
    """Nguồn mong đợi của lượt CKA (bản chép của F5) theo data/manifest.csv của thư mục chạy: yawdd, drivface, yawdd+drivface (manifest in-cabin; khong_ro nếu manifest không có cột source)."""
    import ca_kho
    return ca_kho.run_source(os.path.join(W, 'runs', 'CKA'), W)


def step3(pw, pg, W, shots):
    log('\n== BƯỚC 3: tab Ca khó của P1 ==')
    page = pg.pg
    pg.tab('Ca khó')
    page.wait_for_function("document.querySelectorAll('#ck-list .ck-mcard').length === 4", timeout=20000)
    check(True, 'tab Ca khó thấy 4 ca (3 ở CKA, 1 ở CKN)')
    check('Gói họp chứa ảnh mặt người thật' in page.inner_text('#ck-warn'), 'có hộp cảnh báo riêng tư')
    box = page.inner_text('#ck-ngoai')
    check('CKN' in box and 'khách hàng' in box and page.locator('#ck-ngoai .nap-err').count() == 1, f'hộp đỏ nêu lượt CKN: {box[:90]!r}')
    check(not page.locator('#ck-kem-ngoai input').is_checked() and page.locator('#ck-kem-anh input').is_checked(), 'mặc định: kèm ảnh của bộ dữ liệu (YawDD/DrivFace) bật, ảnh không rõ nguồn tắt')
    page.wait_for_function("Array.from(document.querySelectorAll('#ck-list img')).filter(i => i.complete && i.naturalWidth > 0).length >= 3", timeout=20000)
    check(True, 'ảnh nhỏ của ca tải được (≥ 3)')
    pg.shot(shots, 'cakho_03_tab_desktop')
    marks = os.path.join(W, 'runs', 'CKA', 'ca_kho.csv')
    # sửa 1 ca
    pg.dd_pick('#ck-pick-member', 'CKA/F_004.png')                         # ca CONG_CU trên mặt đã Nhận
    page.wait_for_selector('#ck-edit', state='visible', timeout=10000)
    page.locator('#ck-m-loai label:has(input[value="MISPLACED"])').click()
    page.locator('#ck-m-note textarea').fill('sửa từ tab Ca khó')
    page.click('#ck-m-save')
    page.wait_for_function("document.querySelector('#ck-m-msg').innerText.includes('Đã lưu')", timeout=10000)
    changed = [r for r in read_marks(marks) if r['loai'] == 'MISPLACED']
    check(len(changed) == 1 and changed[0]['ghi_chu'] == 'sửa từ tab Ca khó', 'sửa 1 ca: ghi lại đúng vào runs/CKA/ca_kho.csv')
    # xoá 1 ca: Không rồi Xác nhận
    pg.dd_pick('#ck-pick-member', 'CKN/')
    page.wait_for_selector('#ck-edit', state='visible')
    page.click('#ck-m-del')
    page.wait_for_selector('#ck-m-del-ok', state='visible')
    check(page.locator('#ck-m-del-no').is_visible() and not page.locator('#ck-m-del').is_visible(), 'Delete: hiện Confirm delete và Cancel')
    page.click('#ck-m-del-no')
    page.wait_for_selector('#ck-m-del-ok', state='hidden')
    check(os.path.exists(os.path.join(W, 'runs', 'CKN', 'ca_kho.csv')) and len(read_marks(os.path.join(W, 'runs', 'CKN', 'ca_kho.csv'))) == 1, 'Không: ca còn nguyên')
    page.click('#ck-m-del')
    page.click('#ck-m-del-ok')
    page.wait_for_function("document.querySelectorAll('#ck-list .ck-mcard').length === 3", timeout=10000)
    check(len(read_marks(os.path.join(W, 'runs', 'CKN', 'ca_kho.csv'))) == 0, 'Confirm delete: ca CKN bị xoá (còn 3 ca)')
    page.wait_for_timeout(500)
    check('CKN' not in page.inner_text('#ck-ngoai'), 'hết ca CKN thì hộp đỏ biến mất')
    # khôi phục một ca CKN để kiểm lượt không rõ nguồn không kèm ảnh
    pg.tab('Rà soát')
    page.keyboard.press('k')
    page.wait_for_selector('#ck-panel', state='visible')
    page.locator('#ck-loai label:has(input[value="KHAC"])').click()
    page.locator('#ck-note textarea').fill('Ca CKN lần hai')
    page.click('#ck-save')
    page.wait_for_selector('#ck-panel', state='hidden')
    pg.tab('Ca khó')
    page.wait_for_function("document.querySelectorAll('#ck-list .ck-mcard').length === 4", timeout=20000)
    page.click('#ck-export')
    page.wait_for_selector('#ck-download', state='visible', timeout=30000)
    summ = page.inner_text('#ck-sum')
    check('4 ca' in summ and 'kèm 3 ảnh' in summ and 'CKN' in summ and 'không rõ nguồn' in summ, f'tóm tắt xuất gói: {summ[:200]!r}')
    pg.shot(shots, 'cakho_03b_tab_xuat')
    with page.expect_download(timeout=30000) as dl:
        page.click('#ck-download')
    out = os.path.join(shots, 'goi_P1_tai_ve.zip')
    dl.value.save_as(out)
    with zipfile.ZipFile(out) as zf:
        names = sorted(zf.namelist())
        man = json.loads(zf.read('manifest.json'))
        check(man['nguoi'] == 'P1' and man['so_ca'] == 4 and man['so_anh'] == 3 and man['nguon'] == {'CKA': nguon_cka(W), 'CKN': 'khong_ro'}, f'manifest đúng: {man}')
        imgs = [n for n in names if n.startswith('anh/')]
        check(len(imgs) == 3 and all(n.startswith('anh/CKA__') for n in imgs) and set(names) - set(imgs) == {'manifest.json', 'ca_kho.csv'},
              f'gói chỉ có ảnh CKA, CKN không kèm ảnh: {names}')
    shutil.copy(out, os.path.join(W, 'outputs', 'p1_ban_sao.zip'))
    check(os.path.isfile(os.path.join(W, 'outputs', 'ca_kho', [f for f in os.listdir(os.path.join(W, 'outputs', 'ca_kho')) if f.startswith('ca_kho_P1_')][0])),
          'file gói nằm trong outputs/ca_kho/')
    page.set_viewport_size({'width': 420, 'height': 900})
    page.wait_for_timeout(600)
    check(pg.no_hscroll(420), 'tab Ca khó ở 420 px: không cuộn ngang')
    pg.shot(shots, 'cakho_04_tab_hep', True)
    page.set_viewport_size({'width': 1440, 'height': 900})


# ---------- bước 4 ----------
def step4(pw, W, shots):
    log('\n== BƯỚC 4: runs/CKB người P3 ==')
    p = run_app(['runs/CKB', 'P3'], W, 7883, os.path.join(shots, 'app_ck3.log'))
    pg = Page(pw, 7883)
    try:
        pg.open()
        page = pg.pg
        names = {}
        page.locator('#grid .thumbnail-item').nth(0).click()
        for i, (loai, note) in enumerate([('RULE', 'Kính râm che mắt, chưa có quy tắc'), ('GL_MO_HO', 'Mơ hồ: viền môi | hai cách hiểu')]):
            f = 'F_001.png' if i == 0 else None
            if f:
                page.locator('#grid .thumbnail-item').filter(has=page.locator('img[alt^="F_001"]')).first.click()
                pg.ui.wait_cur('F_001.png')
            page.keyboard.press('k')
            page.wait_for_selector('#ck-panel', state='visible')
            page.locator(f'#ck-loai label:has(input[value="{loai}"])').click()
            page.locator('#ck-note textarea').fill(note)
            page.click('#ck-save')
            page.wait_for_selector('#ck-panel', state='hidden')
            names[loai] = pg.ui.cur()
            if i == 0:
                page.locator('#grid .thumbnail-item').filter(has=page.locator('img[alt^="F_003"]')).first.click()
                pg.ui.wait_cur('F_003.png')
        rows = read_marks(os.path.join(W, 'runs', 'CKB', 'ca_kho.csv'))
        check(len(rows) == 2 and rows[0]['anh'] == 'F_001.png' and rows[1]['anh'] == 'F_003.png' and {r['nguoi'] for r in rows} == {'P3'}, f'CKB: 2 ca của P3: {[(r["anh"], r["loai"]) for r in rows]}')
        pg.tab('Ca khó')
        page.wait_for_function("document.querySelectorAll('#ck-list .ck-mcard').length === 2", timeout=20000)
        check('CKN' not in page.inner_text('#ck-ngoai') and page.locator('#ck-ngoai .nap-err').count() == 0, 'P3 chỉ có lượt bộ dữ liệu: không có hộp đỏ')
        page.click('#ck-export')
        page.wait_for_selector('#ck-download', state='visible', timeout=30000)
        with page.expect_download(timeout=30000) as dl:
            page.click('#ck-download')
        dl.value.save_as(os.path.join(shots, 'goi_P3_tai_ve.zip'))
        with zipfile.ZipFile(os.path.join(shots, 'goi_P3_tai_ve.zip')) as zf:
            check(json.loads(zf.read('manifest.json'))['so_anh'] == 2 and len([n for n in zf.namelist() if n.startswith('anh/')]) == 2, 'gói P3: 2 ca, 2 ảnh')
    finally:
        pg.close()
        stop(p)


# ---------- bước 5 ----------
def make_evil(path):
    with zipfile.ZipFile(path, 'w') as zf:
        man = {'loai_goi': 'm28-ca-kho', 'phien_ban': 1, 'nguoi': 'P2', 'ngay': '2026-10-16', 'luot': ['CKA'], 'nguon': {'CKA': 'yawdd'}, 'so_ca': 0}
        zf.writestr('manifest.json', json.dumps(man))
        zf.writestr('ca_kho.csv', ','.join(['luot', 'anh', 'nguoi', 'loai', 'diem', 'ghi_chu', 'tao_luc', 'sua_luc', 'quyet_dinh_ra', 'thumb']) + '\n')
        zf.writestr('../evil.jpg', b'khong phai anh')


def step5(pw, W, shots, repo_hash):
    log('\n== BƯỚC 5: tab Họp team (review_app.py --nap P5) ==')
    outd = os.path.join(W, 'outputs', 'ca_kho')
    p1 = [os.path.join(outd, f) for f in os.listdir(outd) if f.startswith('ca_kho_P1_')][0]
    p3 = [os.path.join(outd, f) for f in os.listdir(outd) if f.startswith('ca_kho_P3_')][0]
    stage = os.path.join(W, 'outputs', 'nhap')
    os.makedirs(stage, exist_ok=True)
    evil, dup = os.path.join(stage, 'evil.zip'), os.path.join(stage, 'p1_trung.zip')
    make_evil(evil)
    shutil.copy(p1, dup)
    shutil.copy(p1, os.path.join(stage, 'p1.zip'))
    shutil.copy(p3, os.path.join(stage, 'p3.zip'))
    with zipfile.ZipFile(p1) as z1, zipfile.ZipFile(p3) as z3:
        rows1 = list(csv.DictReader(io.StringIO(z1.read('ca_kho.csv').decode('utf-8-sig'))))
        rows3 = list(csv.DictReader(io.StringIO(z3.read('ca_kho.csv').decode('utf-8-sig'))))
    n_cases = len(rows1) + len(rows3)
    allr = rows1 + rows3
    p = run_app(['--nap', 'P5'], W, 7884, os.path.join(shots, 'app_ck4.log'))
    pg = Page(pw, 7884)
    page = pg.pg
    try:
        pg.open('#tabs')
        pg.tab('Họp team')
        check('Gói họp chứa ảnh mặt người thật' in page.inner_text('#hop-warn'), 'tab Họp team có cảnh báo riêng tư trước ô nhập')
        page.click('#hop-new')
        page.wait_for_function("document.querySelector('#hop-msg').innerText.includes('Đã tạo phiên')", timeout=15000)
        sess_name = re.search(r'hop_\d{4}(?:_\d+)?', page.inner_text('#hop-msg')).group(0)
        check(os.path.isfile(os.path.join(outd, sess_name, 'hop.json')), f'tạo phiên {sess_name}')
        page.set_input_files('#hop-drop input[type=file]', [os.path.join(stage, n) for n in ('p1.zip', 'evil.zip', 'p3.zip', 'p1_trung.zip')])
        page.wait_for_timeout(1500)
        page.click('#hop-import')
        page.wait_for_selector('#hop-report table', timeout=30000)
        rep = page.inner_text('#hop-report')
        n_ok = page.locator('#hop-report .ck-ok').count()
        n_bad = page.locator('#hop-report .ck-bad').count()
        n_skip = page.locator('#hop-report .ck-skip').count()
        check((n_ok, n_bad, n_skip) == (2, 1, 1), f'báo đúng: 2 nhập được, 1 lỗi, 1 đã nhập ({n_ok},{n_bad},{n_skip})')
        check('tên không hợp lệ' in rep and 'evil.zip' in rep and 'đã nhập rồi' in rep, 'lỗi nêu lý do và tên file; gói trùng báo đã nhập rồi')
        pg.shot(shots, 'cakho_09_bao_loi_goi')
        check(not os.path.exists(os.path.join(W, 'outputs', 'evil.jpg')) and not os.path.exists(os.path.join(outd, 'evil.jpg'))
              and not os.path.exists(os.path.join(W, 'evil.jpg')), 'không có file evil.jpg nào được tạo ngoài gói')
        hop = json.load(open(os.path.join(outd, sess_name, 'hop.json'), encoding='utf-8'))
        check(len(hop['ca']) == n_cases and len(hop['goi']) == 2, f'hop.json: {n_cases} ca, 2 gói')
        # đếm theo loại / người
        counts = page.inner_text('#hop-counts')
        exp_loai = {}
        for r in allr:
            exp_loai[r['loai']] = exp_loai.get(r['loai'], 0) + 1
        ok = True
        for code, n in exp_loai.items():
            chip = page.locator('#hop-counts .ck-crow').nth(0).locator('.m28-chip', has_text=code).first
            ok &= re.sub(r'\s+', ' ', chip.inner_text()).strip() == f'{code} {n}'
        check(ok, f'đếm theo loại đúng: {exp_loai}')
        check(f'P1 {len(rows1)}' in re.sub(r'\s+', ' ', counts) and f'P3 {len(rows3)}' in re.sub(r'\s+', ' ', counts), 'đếm theo người đúng')
        page.wait_for_function("(() => { const i = document.querySelectorAll('#hop-grid img'); return i.length > 0 && Array.from(i).every(x => x.complete && x.naturalWidth > 0); })()",
                               timeout=30000)
        n_img = page.locator('#hop-grid img').count()
        n_thumb = sum(1 for r in allr if r['thumb'])
        check(n_img == n_thumb and n_thumb == n_cases - 1, f'ảnh trong lưới tải được, naturalWidth > 0 ({n_img} ảnh; ca CKN không kèm ảnh nên {n_cases - n_img} thẻ xám)')
        check(page.locator('#hop-grid .ck-noimg').count() == n_cases - n_thumb, 'ca không kèm ảnh hiện ô xám "Không có ảnh"')
        n_sec = page.locator('#hop-grid .ck-group').count()
        page.locator('#hop-group label:has(input[value="nguoi"])').click()
        page.wait_for_function("document.querySelectorAll('#hop-grid .ck-group').length === 2", timeout=10000)
        titles = page.locator('#hop-grid .ck-group h3').all_inner_texts()
        check(n_sec == len(exp_loai) and titles[0].startswith('P1') and titles[1].startswith('P3'), f'đổi Nhóm theo Người: {titles}')
        page.locator('#hop-group label:has(input[value="loai"])').click()
        pg.dd_pick('#hop-f-nguoi', 'P3')
        page.wait_for_function(f"document.querySelectorAll('#hop-grid .ck-card').length === {len(rows3)}", timeout=10000)
        check(True, f'lọc theo người P3: {len(rows3)} thẻ')
        pg.dd_pick('#hop-f-nguoi', 'Tất cả người')
        page.wait_for_function(f"document.querySelectorAll('#hop-grid .ck-card').length === {n_cases}", timeout=10000)
        page.locator('#hop-q input, #hop-q textarea').first.press_sequentially('kính', delay=40)
        page.wait_for_function("document.querySelectorAll('#hop-grid .ck-card').length === 2", timeout=10000)
        check(True, 'tìm chữ "kính" trong ghi chú: 2 thẻ (ghi chú của P1 và P3)')
        page.locator('#hop-q input, #hop-q textarea').first.press('Control+a')
        page.keyboard.press('Backspace')
        page.wait_for_function(f"document.querySelectorAll('#hop-grid .ck-card').length === {n_cases}", timeout=10000)
        pg.shot(shots, 'cakho_05_hop_luoi_desktop')
        # bấm thẻ cùng ảnh F_001.png (P1 ở CKA và P3 ở CKB): chi tiết có ghi chú của cả hai người
        card = page.locator('#hop-grid .ck-card[data-key^="P1|CKA|F_001"]').first
        card.click()
        page.wait_for_function("document.querySelectorAll('#ck-stage .ck-note').length >= 1", timeout=10000)
        page.wait_for_timeout(600)
        notes = page.locator('#ck-stage .ck-note').count()
        check(notes == 2, f'chi tiết F_001.png: ghi chú của 2 người ({notes})')
        check(page.locator('#ck-stage img').first.evaluate('i => i.complete && i.naturalWidth > 0'), 'ảnh lớn trong chi tiết tải được')
        check(page.locator('#hop-grid .ck-card.sel').count() == 1, 'thẻ đang chọn có viền (lớp sel)')
        sel_border = page.locator('#hop-grid .ck-card.sel').evaluate('e => getComputedStyle(e).borderTopColor')
        check(sel_border.replace(' ', '') == 'rgb(37,99,235)', f'viền thẻ chọn màu xanh dương: {sel_border}')
        pg.shot(shots, 'cakho_06_hop_chitiet')
        # Đang bàn cho ca này
        page.locator('#hop-tt label:has(input[value="dang_ban"])').click()
        page.click('#hop-save')
        page.wait_for_function("document.querySelector('#hop-form-msg').innerText.includes('Đã lưu')", timeout=10000)
        k1 = card.get_attribute('data-key')
        # ca khác: Đã chốt có quyết định + người phụ trách, Save & next
        k2 = page.locator('#hop-grid .ck-card').nth(1).get_attribute('data-key')
        page.locator(f'#hop-grid .ck-card[data-key="{k2}"]').click()
        page.wait_for_function(f"document.querySelector('#hop-grid .ck-card.sel').dataset.key === {json.dumps(k2)}", timeout=10000)
        page.wait_for_timeout(500)
        page.locator('#hop-tt label:has(input[value="da_chot"])').click()
        page.fill('#hop-qd textarea', 'Kính râm: đặt điểm theo viền kính, không đoán')
        pg.dd_pick('#hop-pt', 'P4')
        page.fill('#hop-mg input, #hop-mg textarea', '5.1')
        page.click('#hop-save-next')
        page.wait_for_function("document.querySelector('#hop-form-msg').innerText.includes('Đã lưu')", timeout=10000)
        page.wait_for_timeout(600)
        cur_after = page.locator('#hop-grid .ck-card.sel').first.get_attribute('data-key')
        check(cur_after != k2, f'Save & next: chuyển sang ca khác ({cur_after})')
        hop = json.load(open(os.path.join(outd, sess_name, 'hop.json'), encoding='utf-8'))
        c1, c2 = hop['ca'][k1], hop['ca'][k2]
        check(c1['trang_thai'] == 'dang_ban' and c2['trang_thai'] == 'da_chot' and c2['phu_trach'] == 'P4' and c2['quyet_dinh'].startswith('Kính râm')
              and c2['muc_guideline'] == '5.1', 'hop.json ghi đúng trạng thái, quyết định, phụ trách, mục guideline')
        # trình chiếu
        page.locator(f'#hop-grid .ck-card[data-key="{k2}"]').click()
        page.wait_for_function(f"document.querySelector('#hop-grid .ck-card.sel').dataset.key === {json.dumps(k2)}", timeout=10000)
        page.wait_for_timeout(500)
        page.click('#hop-present')
        page.wait_for_function("document.body.classList.contains('ck-present')", timeout=5000)
        page.wait_for_timeout(500)
        box = page.locator('#ck-stage').bounding_box()
        check(box['x'] <= 1 and box['y'] <= 1 and box['width'] >= 1430 and box['height'] >= 890, f'trình chiếu: #ck-stage phủ toàn màn hình {box}')
        check(not page.locator('#hop-save').is_visible() or page.evaluate("document.elementFromPoint(720, 450).closest('#ck-stage') !== null"),
              'trình chiếu: form bị che, chỉ thấy stage')
        before = page.locator('#ck-stage .face-name').inner_text() + page.locator('#ck-stage .ck-nhead').first.inner_text()
        pg.shot(shots, 'cakho_07_trinhchieu')
        page.keyboard.press('ArrowRight')
        page.wait_for_function("(b) => (document.querySelector('#ck-stage .face-name').innerText + document.querySelector('#ck-stage .ck-nhead').innerText) !== b",
                               arg=before, timeout=10000)
        check(True, '→ trong trình chiếu: đổi sang ca sau')
        page.keyboard.press('ArrowLeft')
        page.wait_for_function("(b) => (document.querySelector('#ck-stage .face-name').innerText + document.querySelector('#ck-stage .ck-nhead').innerText) === b",
                               arg=before, timeout=10000)
        check(True, '← trong trình chiếu: về ca trước')
        page.keyboard.press('k')
        page.keyboard.press('n')
        page.wait_for_timeout(300)
        page.keyboard.press('Escape')
        page.wait_for_function("!document.body.classList.contains('ck-present')", timeout=5000)
        check(True, 'Esc thoát trình chiếu')
        page.keyboard.press('ArrowRight')
        page.wait_for_timeout(300)
        # màn hẹp
        page.set_viewport_size({'width': 420, 'height': 900})
        page.wait_for_timeout(700)
        check(pg.no_hscroll(420), 'tab Họp team ở 420 px: không cuộn ngang')
        pg.shot(shots, 'cakho_08_hop_hep', True)
        page.set_viewport_size({'width': 1440, 'height': 900})
    except Exception:
        pg.shot(shots, 'loi_buoc5')
        raise
    finally:
        pg.close()
        stop(p)
    # mở lại phiên
    log('  ... tắt app, mở lại, chọn phiên cũ')
    p = run_app(['--nap', 'P5'], W, 7885, os.path.join(shots, 'app_ck5.log'))
    pg = Page(pw, 7885)
    page = pg.pg
    try:
        pg.open('#tabs')
        pg.tab('Họp team')
        page.wait_for_function(f"document.querySelectorAll('#hop-grid .ck-card').length === {n_cases}", timeout=30000)
        counts = re.sub(r'\s+', ' ', page.inner_text('#hop-counts'))
        check('Đang bàn 1' in counts and 'Đã chốt 1' in counts and f'Mở {n_cases - 2}' in counts, f'mở lại phiên: trạng thái còn nguyên ({counts[-60:]})')
        pg.dd_pick('#hop-session', sess_name)
        page.wait_for_timeout(600)
        check(page.locator('#hop-grid .ck-card').count() == n_cases, 'chọn lại phiên cũ trong dropdown: vẫn đủ ca')
        page.click('#hop-minutes')
        page.wait_for_selector('#hop-preview', state='visible', timeout=20000)
        page.wait_for_function("document.querySelector('#hop-min-msg').innerText.includes('Đã xuất biên bản')", timeout=20000)
        sd = os.path.join(outd, sess_name)
        tag = re.search(r'hop_(\d{4})', sess_name).group(1)
        md = open(os.path.join(sd, f'bien_ban_{tag}.md'), encoding='utf-8').read()
        cs = list(csv.DictReader(open(os.path.join(sd, f'tong_hop_{tag}.csv'), encoding='utf-8-sig', newline='')))
        import ca_kho
        p0 = ca_kho.next_number(open(os.path.join(REPO, 'problem-backlog.md'), encoding='utf-8').read(), 'P')       # số tiếp theo theo hai file repo hiện có
        q0 = ca_kho.next_number(open(os.path.join(REPO, 'so-quyet-dinh.md'), encoding='utf-8').read(), 'QĐ')
        pc, qc = f'P-{p0:03d}', f'QĐ-{q0:03d}'
        check(pc in md and qc in md and '## Dán vào problem-backlog.md' in md, f'biên bản có {pc} và {qc} (số tiếp theo của hai file repo)')
        check(len(cs) == n_cases and any(r['ma_qd'] == qc for r in cs), f'CSV tổng hợp đủ {n_cases} dòng, có {qc}')
        check(pc in page.inner_text('#hop-preview'), 'xem trước markdown trong trang')
        check(page.locator('#hop-file-md').is_visible() and page.locator('#hop-file-csv').is_visible(), 'hiện hai file để tải')
        gi = [sha(os.path.join(REPO, f)) for f in ('problem-backlog.md', 'so-quyet-dinh.md')]
        check(gi == repo_hash, 'problem-backlog.md và so-quyet-dinh.md không bị đụng tới')
        check(not [e for e in pg.ui.errors if 'Failed to load resource' not in e and 'ERR_' not in e and 'WebSocket' not in e], f'không lỗi JS: {pg.ui.errors[:2]}')
    except Exception:
        pg.shot(shots, 'loi_buoc5b')
        raise
    finally:
        pg.close()
        stop(p)


def step_review_pages(pw, W, shots):
    """Chụp panel ở 420 px (cakho_02) trên CKB."""
    log('\n== ảnh chụp panel ở màn hẹp ==')
    p = run_app(['runs/CKA', 'P1'], W, 7886, os.path.join(shots, 'app_ck6.log'))
    pg = Page(pw, 7886, 420, 900)
    try:
        pg.open()
        page = pg.pg
        page.locator('#grid .thumbnail-item').nth(3).click()
        page.wait_for_timeout(500)
        page.keyboard.press('k')
        page.wait_for_selector('#ck-panel', state='visible')
        page.locator('#ck-loai label:has(input[value="COLLAPSE"])').click()
        page.locator('#ck-note textarea').fill('Các điểm miệng dồn thành một cục')
        check(pg.no_hscroll(420), 'panel ở 420 px: không cuộn ngang')
        pg.shot(shots, 'cakho_02_panel_hep', True)
        box = page.locator('#ck-save').bounding_box()
        check(box and box['width'] > 40, 'nút Save bấm được ở 420 px')
    finally:
        pg.close()
        stop(p)


def step_after_xong(pw, W, shots):
    """Sau Xong: đánh dấu ca khó MỚI bị từ chối (chữ mới), nhưng tab Ca khó xem/sửa/xuất gói vẫn dùng được; trang không tắt."""
    log('\n== sau Xong: Ca khó ==')
    run = os.path.join(W, 'runs', 'CKA')
    marks = os.path.join(run, 'ca_kho.csv')
    p = run_app(['runs/CKA', 'P1'], W, 7887, os.path.join(shots, 'app_ck7.log'))
    pg = Page(pw, 7887)
    try:
        pg.open()
        page = pg.pg
        for _ in range(8):
            if page.locator('#btn-xong').is_enabled():
                break
            page.click('#btn-nhan' if page.locator('#btn-nhan').is_enabled() else '#btn-gantay')
            page.wait_for_timeout(700)
        check(page.locator('#btn-xong').is_enabled(), 'CKA rà hết, nút Xong bật')
        base.click_xong(pg.ui)
        n0 = len(read_marks(marks))
        page.click('#btn-cakho')
        page.wait_for_function("document.body.innerText.includes('Đã bấm Xong: không đánh dấu thêm ca khó mới')", timeout=10000)
        check(not page.locator('#ck-panel').first.is_visible() and len(read_marks(marks)) == n0 and 'trang sắp tắt' not in page.inner_text('body'),
              'sau Xong: đánh dấu ca khó mới bị từ chối với chữ mới, không ghi gì')
        pg.tab('Ca khó')
        page.wait_for_function("document.querySelectorAll('#ck-list .ck-mcard').length >= 1", timeout=20000)
        page.click('#ck-export')
        page.wait_for_selector('#ck-download', state='visible', timeout=30000)
        check('ca' in page.inner_text('#ck-sum') and page.locator('#progress .m28-done-bar').is_visible(), 'sau Xong: xuất gói Ca khó được, dải xanh còn')
        check(p.poll() is None, 'sau Xong: server vẫn chạy')
        pg.shot(shots, 'cakho_05_sau_xong')
    finally:
        pg.close()
        stop(p)
        if os.path.exists(os.path.join(run, 'review', 'done.txt')):
            os.remove(os.path.join(run, 'review', 'done.txt'))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--work', required=True)
    ap.add_argument('--shots', required=True)
    ap.add_argument('--steps', default='123456')
    a = ap.parse_args()
    W, shots = os.path.abspath(a.work), os.path.abspath(a.shots)
    os.makedirs(shots, exist_ok=True)
    from playwright.sync_api import sync_playwright
    t0 = time.time()
    try:
        with sync_playwright() as pw:
            repo_hash = step1(W)
            if '2' in a.steps:
                step2(pw, W, shots)
            if '4' in a.steps:
                step4(pw, W, shots)
            if '5' in a.steps:
                step5(pw, W, shots, repo_hash)
            step_review_pages(pw, W, shots)
            if '6' in a.steps:
                step_after_xong(pw, W, shots)
        out = [u for u in ALL_REQUESTS if not u.startswith(('http://127.0.0.1', 'data:', 'blob:'))]
        check(out == [], f'không request nào ra ngoài 127.0.0.1 (đã thấy {len(ALL_REQUESTS)} request)')
    except (AssertionError, RuntimeError) as e:
        log(f'\nHỎNG: {e}')
        return 1
    finally:
        stop_all()
    log(f'\nQUA hết sau {time.time() - t0:.0f}s. Ảnh chụp ở {shots}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
