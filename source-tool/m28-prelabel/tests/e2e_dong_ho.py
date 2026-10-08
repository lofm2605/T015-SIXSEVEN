"""Kiểm thử đầu-cuối tab "Đồng hồ" và tab "Thống kê" bằng trình duyệt thật (Chromium qua Playwright). TUỲ CHỌN.

Cần playwright và Chromium, KHÔNG nằm trong requirements, pytest không gom file này (tên không khớp test_*.py). Chỉ chạy trên Linux (dùng `lsof` để kiểm cổng chỉ bind 127.0.0.1).
Chỉ chạy nếu `python -c "from playwright.sync_api import sync_playwright"` chạy được VÀ Chromium của Playwright có sẵn (`ls ~/.cache/ms-playwright/`); không có thì bỏ qua và ghi lý do.
Cần một thư mục chạy GIẢ (--work, ngoài repo, KHÔNG phải thư mục dữ liệu thật) có `config/` chép từ repo; mọi lần bấm đồng hồ chạy ở đó. Ví dụ:

    mkdir -p /tmp/m28_dong_ho/work && cp -r config /tmp/m28_dong_ho/work/config
    python tests/e2e_dong_ho.py --work /tmp/m28_dong_ho/work --shots /tmp/m28_dong_ho/shots

Kịch bản (app thật `review_app.py --nap P5`, cổng 7861, proxy chết để chứng minh không cần mạng):
  1  tab Đồng hồ: Bắt đầu; 3 giây sau mm:ss đã tăng mà KHÔNG có request nào mỗi giây (đếm request); Tạm dừng 2 giây số đứng yên; Tiếp tục; Xong mặt hai lần
  2  tải lại trang: phiên còn, đồng hồ vẫn chạy
  3  mở tab thứ hai bấm Tạm dừng; tab đầu bấm Xong mặt bị từ chối vì rev cũ ("tab khác")
  4  Hủy: gõ sai không hủy; gõ HUY: không có dòng CSV, có dòng huy_P5.csv
  5  phiên mới: Bắt đầu, Xong (lưu): timing_P5.csv đúng 12 cột facetimer + cột thêm, có gói zip trong outputs/ket_qua
  6  tab Thống kê với gói giả của 4 người (outputs/goi_nhom): có ba mục, KTC, không số nào khi thiếu dữ liệu
  7  không request nào ra ngoài 127.0.0.1; `lsof` thấy cổng chỉ bind 127.0.0.1
  8  ảnh chụp dongho_*.png, thongke_*.png vào --shots (desktop 1440x900 và hẹp 420 px)
CHƯA CHẠY ĐƯỢC ở phiên viết file này (máy phiên không có Playwright/Chromium): các bước được kiểm bằng pytest (tests/test_dong_ho*.py, test_thong_ke*.py) và bằng trình duyệt tích hợp.
"""
import argparse
import csv
import glob
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(CODE, 'tool'))
import e2e_review_ui as base  # noqa: E402
from e2e_review_ui import DEAD_PROXY, check, listeners, log, start, stop_all, wait_port  # noqa: E402

PORT = 7861
REQ = []


def clock(pg):
    return pg.locator('#dh-clock').inner_text().strip()


def secs(txt):
    p = [int(x) for x in txt.split(':')]
    return p[0] * 60 + p[1] if len(p) == 2 else p[0] * 3600 + p[1] * 60 + p[2]


def open_tab(pg, name):
    pg.get_by_role('tab', name=name).click()
    pg.wait_for_timeout(600)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--work', required=True)
    ap.add_argument('--shots', required=True)
    a = ap.parse_args()
    W, shots = os.path.abspath(a.work), os.path.abspath(a.shots)
    os.makedirs(shots, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log('Bỏ qua: chưa có playwright.')
        return 0
    if not glob.glob(os.path.expanduser('~/.cache/ms-playwright/chromium*')) and not os.environ.get('PLAYWRIGHT_BROWSERS_PATH'):
        log('Bỏ qua: chưa có Chromium của Playwright.')
        return 0
    for d in ('outputs', 'raw'):
        shutil.rmtree(os.path.join(W, d), ignore_errors=True)
    try:
        sys.path.insert(0, HERE)
        import tk_fake
        tk_fake.mo_phong(W)                                   # gói giả của 4 người ở outputs/goi_nhom
        json.dump({'nhom': {'P1': 'manual', 'P2': 'manual', 'P3': 'assisted', 'P4': 'assisted', 'P5': 'assisted'}, 'bo_anh': 'NAP_001'},
                  open(os.path.join(W, 'config', 'nhom_thi_nghiem.json'), 'w'))
        proc = start([sys.executable, os.path.join(CODE, 'tool', 'review_app.py'), '--nap', 'P5'], W, PORT,
                     dict(HTTP_PROXY=DEAD_PROXY, HTTPS_PROXY=DEAD_PROXY), out=os.path.join(shots, 'server.log'))
        wait_port(PORT, proc)
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            ctx = br.new_context(viewport={'width': 1440, 'height': 900})
            pg = ctx.new_page()
            pg.on('request', lambda r: REQ.append(r.url))
            pg.goto(f'http://127.0.0.1:{PORT}/')
            open_tab(pg, 'Đồng hồ')
            # 1
            pg.locator('#dh-dot textarea, #dh-dot input').first.fill('NAP_001')
            pg.get_by_label('Dùng tool, sửa nháp (assisted)').check()
            pg.locator('#dh-start').click()
            pg.wait_for_selector('#dh-clock[data-chay="1"]')
            t0, n0 = secs(clock(pg)), len(REQ)
            pg.wait_for_timeout(3200)
            t1, n1 = secs(clock(pg)), len(REQ)
            check(t1 - t0 >= 2, f'mm:ss đã tăng sau 3 giây ({t0} -> {t1})')
            check(n1 - n0 <= 1, f'không có request mỗi giây (chỉ {n1 - n0} request trong 3 giây)')
            pg.locator('#dh-pause').click()
            pg.wait_for_selector('#dh-clock[data-chay="0"]')
            a1 = secs(clock(pg))
            pg.wait_for_timeout(2200)
            check(secs(clock(pg)) == a1, 'tạm dừng 2 giây: số đứng yên')
            pg.locator('#dh-pause').click()
            pg.wait_for_selector('#dh-clock[data-chay="1"]')
            for _ in range(2):
                pg.wait_for_timeout(2300)
                pg.locator('#dh-face').click()
                pg.wait_for_timeout(500)
            check('Các mặt đã khép' in pg.locator('#dh-faces').inner_text(), 'bảng các mặt đã khép hiện sau Xong mặt')
            pg.screenshot(path=os.path.join(shots, 'dongho_chay_1440.png'))
            # 2
            pg.reload()
            open_tab(pg, 'Đồng hồ')
            pg.wait_for_selector('#dh-clock[data-chay="1"]')
            check(True, 'tải lại trang: phiên còn, đồng hồ vẫn chạy')
            # 3
            pg2 = ctx.new_page()
            pg2.goto(f'http://127.0.0.1:{PORT}/')
            open_tab(pg2, 'Đồng hồ')
            pg2.wait_for_selector('#dh-clock[data-chay="1"]')
            pg2.locator('#dh-pause').click()
            pg2.wait_for_selector('#dh-clock[data-chay="0"]')
            pg.locator('#dh-face').click()
            pg.wait_for_timeout(1200)
            check('tab khác' in pg.locator('#dh-msg').inner_text(), 'tab cũ bị từ chối vì rev cũ')
            pg2.close()
            # 4
            pg.reload()
            open_tab(pg, 'Đồng hồ')
            pg.locator('#dh-cancel').click()
            pg.locator('#dh-cancel-text textarea, #dh-cancel-text input').first.fill('khong')
            pg.locator('#dh-cancel-ok').click()
            pg.wait_for_timeout(800)
            check(os.path.exists(os.path.join(W, 'outputs', 'timing', 'dang_chay_P5.json')), 'gõ sai: không hủy')
            pg.locator('#dh-cancel').click()
            pg.locator('#dh-cancel-text textarea, #dh-cancel-text input').first.fill('HUY')
            pg.locator('#dh-cancel-ok').click()
            pg.wait_for_timeout(900)
            check(not os.path.exists(os.path.join(W, 'outputs', 'timing', 'timing_P5.csv')) and os.path.exists(os.path.join(W, 'outputs', 'timing', 'huy_P5.csv')),
                  'Hủy: không có dòng CSV, có dòng nhật ký huy_P5.csv')
            # 5
            pg.locator('#dh-dot textarea, #dh-dot input').first.fill('NAP_001')
            pg.locator('#dh-start').click()
            pg.wait_for_selector('#dh-clock[data-chay="1"]')
            pg.wait_for_timeout(2600)
            pg.locator('#dh-done').click()
            pg.wait_for_timeout(1500)
            rows = list(csv.DictReader(open(os.path.join(W, 'outputs', 'timing', 'timing_P5.csv'), encoding='utf-8')))
            check(rows and list(rows[0])[:12] == ['date', 'person', 'condition', 'task', 'job', 'block', 'seq', 'face_id', 'seconds', 'warmup', 'interrupted', 'note'],
                  '12 cột đầu đúng facetimer')
            check(glob.glob(os.path.join(W, 'outputs', 'ket_qua', 'ketqua_P5_*_NAP_001.zip')), 'có gói kết quả zip')
            pg.screenshot(path=os.path.join(shots, 'dongho_xong_1440.png'))
            # 6
            open_tab(pg, 'Thống kê')
            pg.get_by_role('button', name='Làm mới').first.click()
            pg.wait_for_timeout(2500)
            txt = pg.locator('#tk-view').inner_text()
            check('1. NME của nháp' in txt and '2. Tỉ lệ điểm phải sửa' in txt and '3. So sánh thời gian' in txt and 'KTC 90%' in txt, 'tab Thống kê có ba mục và KTC')
            check('low_conf' not in txt and 'AUROC' not in txt, 'thẻ bị bỏ không còn trên tab')
            pg.screenshot(path=os.path.join(shots, 'thongke_1440.png'), full_page=True)
            # 8: hẹp 420 px
            nar = ctx.new_page()
            nar.set_viewport_size({'width': 420, 'height': 860})
            nar.goto(f'http://127.0.0.1:{PORT}/')
            open_tab(nar, 'Đồng hồ')
            check(nar.evaluate('document.documentElement.scrollWidth') <= 421, '420 px không tràn ngang (Đồng hồ)')
            nar.screenshot(path=os.path.join(shots, 'dongho_420.png'), full_page=True)
            open_tab(nar, 'Thống kê')
            nar.get_by_role('button', name='Làm mới').first.click()
            nar.wait_for_timeout(2500)
            check(nar.evaluate('document.documentElement.scrollWidth') <= 421, '420 px không tràn ngang (Thống kê)')
            nar.screenshot(path=os.path.join(shots, 'thongke_420.png'), full_page=True)
            br.close()
        out = [u for u in REQ if not u.startswith(('http://127.0.0.1', 'data:', 'blob:'))]
        check(out == [], f'không request nào ra ngoài 127.0.0.1 (đã thấy {len(REQ)} request)')
        ls = listeners(PORT)
        check(ls and all('127.0.0.1' in l for l in ls), 'cổng chỉ bind 127.0.0.1')
    except (AssertionError, RuntimeError) as e:
        log(f'\nHỎNG: {e}')
        return 1
    finally:
        stop_all()
    log(f'\nQUA hết. Ảnh chụp ở {shots}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
