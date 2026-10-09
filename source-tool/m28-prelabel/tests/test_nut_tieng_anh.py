"""Quy ước nhãn nút (09/10/2026, theo yêu cầu chủ repo): MỌI NÚT trên trang rà soát ghi bằng tiếng Anh (Save, Cancel, Refresh, Push to CVAT, Upload & Open...);
CHỈ có ghi chú, tên mục (tên tab, tiêu đề) và năm nút thuộc từ vựng quyết định của quy trình rà soát (Nhận / Gán tay / Bỏ ảnh / Ca khó / Xong) giữ tiếng Việt.

Test này giữ quy ước đó: quét nhãn của mọi nút Gradio đã dựng, mọi nút HTML dựng sẵn (tab Các đợt, thẻ họp), nhãn nút động (hộp xác nhận, Unmark, Pause/Resume...) và
các câu trên trang nhắc tên nút (không còn "bấm Huỷ", "bấm Làm mới"... của nhãn cũ)."""
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, '..', 'tool')
sys.path.insert(0, TOOL)
sys.path.insert(0, HERE)

# chữ có dấu tiếng Việt (có đ/Đ); ký hiệu như ‹ › ← → & ( ) không tính
VN = re.compile('[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]', re.I)
# từ vựng quyết định của quy trình rà soát: giữ tiếng Việt vì cùng từ với trạng thái, chip, số đếm, CSV và guideline
NUT_VIET_GIU_LAI = {'Nhận (N)', 'Gán tay (G)', 'Bỏ ảnh (B)', 'Ca khó (K)', 'Xong'}
NUT_ANH_PHAI_CO = {'Save', 'Cancel', 'Refresh', 'Delete', 'Close page', 'Pause', 'Push to CVAT', 'Upload & Open', 'Upload & Continue', 'Retry', 'Undo (Z)', '← Prev', 'Next →', '‹ Prev page', 'Next page ›',
                   'Export CSV + HTML', 'Preview', 'Create dataset', 'Overwrite', 'Save config', 'Load', 'Show / Hide', 'Test CVAT connection', 'Forget token',
                   'Run CVAT quick check', 'Save timing', 'Export meeting pack', 'Import packs', 'Present', 'Unmark', 'Confirm delete'}


def src(name):
    with open(os.path.join(TOOL, name), encoding='utf-8') as f:
        return f.read()


def co_dau(text):
    return bool(VN.search(text))


@pytest.fixture
def ctx_run(tmp_path, monkeypatch):
    gr = pytest.importorskip('gradio')  # noqa: F841
    import review_app as ra
    from thong_ke_fake import Proj
    p = Proj(tmp_path, t_flip=0.03)
    p.add_face('F_001')
    p.make_run('R1', ['F_001'])
    monkeypatch.chdir(p.root)
    ctx = ra.AppCtx(reviewer='P1', run_dir=os.path.join(p.root, 'runs', 'R1'))
    return ra, ctx, p


def nhan_nut(demo):
    out = []
    for b in demo.blocks.values():
        if type(b).__name__ in ('Button', 'DownloadButton'):
            out.append((getattr(b, 'elem_id', None), b.value))
    return out


def test_moi_nut_gradio_ghi_tieng_anh_tru_nam_nut_quyet_dinh(ctx_run):
    ra, ctx, p = ctx_run
    ra.prepare_env(ctx.run_dir)
    demo, _ = ra.build_ui(ra.Store(ctx.run_dir, 'P1'), ctx)
    nut = nhan_nut(demo)
    assert len(nut) > 50                                                              # có đủ các tab (Rà soát, Nạp ảnh, Các đợt, Ca khó, Họp team, Thống kê, Lọc dữ liệu, Cài đặt)
    tieng_viet = {(i, v) for i, v in nut if isinstance(v, str) and co_dau(v)}
    assert {v for _i, v in tieng_viet} <= NUT_VIET_GIU_LAI, sorted(tieng_viet)
    assert {i for i, _v in tieng_viet} <= {'btn-nhan', 'btn-gantay', 'btn-bo', 'btn-cakho', 'btn-xong'}
    labels = {v for _i, v in nut}
    assert NUT_ANH_PHAI_CO <= labels, sorted(NUT_ANH_PHAI_CO - labels)
    os.makedirs('runs/_nap', exist_ok=True)
    demo2, _ = ra.build_ui(None, ra.AppCtx(reviewer='P2', run_dir=os.path.join('runs', '_nap'), nap_only=True))      # --nap: cùng quy ước
    assert {v for _i, v in nhan_nut(demo2) if isinstance(v, str) and co_dau(v)} <= NUT_VIET_GIU_LAI


def test_tab_va_muc_van_la_tieng_viet(ctx_run):
    ra, ctx, p = ctx_run
    ra.prepare_env(ctx.run_dir)
    demo, _ = ra.build_ui(ra.Store(ctx.run_dir, 'P1'), ctx)
    tabs = [b.label for b in demo.blocks.values() if type(b).__name__ == 'Tab']
    assert tabs == ['Rà soát', 'Nạp ảnh', 'Các đợt', 'Ca khó', 'Họp team', 'Thống kê', 'Lọc dữ liệu', 'Cài đặt']          # tên mục KHÔNG đổi


def test_nut_html_cua_tab_cac_dot_ghi_tieng_anh():
    s = src('dot_anh.py')
    texts = [t.strip() for t in re.findall(r'>([^<>{}]+)</button>', s)]
    assert {'Review batch', 'Push to CVAT', 'View images', 'Restore', 'Delete permanently…', '‹ Prev page', 'Next page ›', '‹ Batch list', 'Delete batch…',
            'Delete CVAT task…', 'Empty trash…'} <= set(texts), texts
    assert not [t for t in texts if co_dau(t)], texts
    labels = re.findall(r'(?:aria-label|title)="([^"{}]*(?:\{[a-z]+\}[^"{}]*)?)"', s)
    nut_labels = [l for l in labels if l.startswith(('View', 'Delete', 'Xem', 'Xoá'))]
    assert nut_labels and not [l for l in nut_labels if co_dau(l)], nut_labels                    # aria-label/title của nút (icon thùng rác, tên đợt) cũng bằng tiếng Anh


def test_nhan_nut_dong_trong_hop_xac_nhan_va_nut_doi_chu():
    dot_ui = src('dot_ui.py')
    ok = re.findall(r'ok_label="([^"]+)"', dot_ui) + re.findall(r'modal\.get\("ok_label", "([^"]+)"\)', dot_ui)
    assert {'Delete permanently', 'Push to CVAT', 'Delete image', 'Delete batch', 'Delete CVAT task', 'Delete'} <= set(ok), ok
    assert not [t for t in ok if co_dau(t)], ok
    import dong_ho_ui
    for t in (dong_ho_ui.NUT_DUNG, dong_ho_ui.NUT_TIEP, dong_ho_ui.NUT_BAT_DAU, dong_ho_ui.NUT_BO, dong_ho_ui.NUT_BO_LAN_2):
        assert not co_dau(t), t
    assert (dong_ho_ui.NUT_DUNG, dong_ho_ui.NUT_TIEP, dong_ho_ui.NUT_BAT_DAU) == ('Pause', 'Resume', 'Start')           # Start: đợt đang chờ bắt đầu (Upload & Continue lúc đã có đồng hồ ở đợt khác)
    ca_kho = src('ca_kho.py')
    dong = re.findall(r'gr\.update\([^)]*value="([^"]+)"', ca_kho)
    assert {'Unmark', 'Click again to unmark'} <= set(dong), dong
    assert not [t for t in dong if co_dau(t)], dong


def test_cau_tren_trang_khong_con_nhac_ten_nut_cu():
    """Các câu hướng dẫn trên trang phải gọi nút bằng tên mới (Cancel, Refresh, Save, Push to CVAT, Close page...), không còn tên cũ."""
    cu = r'(?:Huỷ|Hủy phiên|Làm mới|Lưu số đo|Lưu tên|Quên token|Thử kết nối CVAT|Đặt t_flip|Để null|Tiếp tục|Rà đợt này|Đẩy lên CVAT|Đóng trang rà soát|Xoá task trên CVAT|Khôi phục|Xuất gói họp|Nhập các gói)'
    rx = re.compile(r'(?:[Bb]ấm|nút) (?:<b>)?' + cu)
    bad = []
    for fn in sorted(f for f in os.listdir(TOOL) if f.endswith('.py')) + ['m28core/' + f for f in sorted(os.listdir(os.path.join(TOOL, 'm28core'))) if f.endswith('.py')]:
        if fn in ('dong_ho.py',):                                                      # lõi đồng hồ giữ câu cũ ('Hủy phiên', 'Xong (lưu)'): dong_ho_ui.vi_hop đổi sang tên mới khi hiện trên trang
            continue
        for i, line in enumerate(src(fn).splitlines(), 1):
            if rx.search(line):
                bad.append(f'{fn}:{i}: {line.strip()[:120]}')
    assert not bad, '\n'.join(bad)


def test_vi_hop_doi_cau_loi_cua_loi_dong_ho_sang_ten_nut_moi():
    import dong_ho_ui
    t = dong_ho_ui.vi_hop('bấm Xong (lưu) hoặc Hủy phiên đó trước khi bắt đầu phiên mới. Hoặc dùng Xong hoặc Hủy phiên.')
    assert 'Save timing' in t and 'Discard session' in t and 'Xong (lưu)' not in t and 'Hủy phiên' not in t and 'dùng Save timing hoặc Discard session' in t


def test_tai_lieu_goi_nut_bang_ten_moi():
    """README và hai hướng dẫn chạy gọi các nút chính bằng tên mới."""
    base = os.path.join(HERE, '..')
    win = open(os.path.join(base, 'HUONG-DAN-WINDOWS.md'), encoding='utf-8').read()
    ubu = open(os.path.join(base, 'HUONG-DAN-UBUNTU.md'), encoding='utf-8').read()
    for t in ('**Pause**', '**Resume**', '**Close page**', '**Save timing**', '**Discard session**', '**Push to CVAT**', '**Delete CVAT task**', '**Review batch**'):
        assert t in win, t
    for t in ('**Pause**', '**Resume**', '**Close page**', '**Save timing**', '**Discard session**', '**Test CVAT connection**', '**Forget token**'):
        assert t in ubu, t
    for t in ('**Lưu số đo**', '**Đóng trang rà soát**', '**Dừng**', '**Tiếp tục**', '**Bỏ phiên đồng hồ**'):
        assert t not in win and t not in ubu, t
