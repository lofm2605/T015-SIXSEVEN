"""Thử hai tab mới của trang rà soát ("Thống kê", "Lọc dữ liệu"): dựng build_ui có lượt và chế độ --nap, handler gọi trực tiếp (không trình duyệt), allowed_paths hẹp."""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, '..', 'tool')
sys.path.insert(0, TOOL)
sys.path.insert(0, HERE)
gr = pytest.importorskip('gradio')
import loc_du_lieu as ld  # noqa: E402
import loc_ui  # noqa: E402
import nap_anh  # noqa: E402
import review_app as ra  # noqa: E402
import thong_ke_ui  # noqa: E402
from test_bang_mat import tree_hash  # noqa: E402
from test_loc_du_lieu import FACES, GROUPS, REGIONS  # noqa: E402
from thong_ke_fake import Proj  # noqa: E402


@pytest.fixture
def world(tmp_path, monkeypatch):
    p = Proj(tmp_path, t_flip=0.03)
    for i, (n, s) in enumerate(FACES):
        p.add_face(n, 'yawdd' if i % 3 else 'drivface', s)
    d = p.make_run('R1', [n for n, _s in FACES])
    p.write_triage('R1', 'P1', [(n, 'nhan', '', 6.0 + i) for i, (n, _s) in enumerate(FACES)])
    p.write_push('R1', 'demo-R1')
    p.write_label('raw', 'demo-R1', 'P3', '1410', {f'{n}.png': p.label_pts(d[n], flip_err=True) for n, _s in FACES})
    monkeypatch.chdir(p.root)
    ctx = ra.AppCtx(reviewer='P1', run_dir=os.path.join(p.root, 'runs', 'R1'))
    return dict(p=p, root=p.root, ctx=ctx, d=d)


def tab_fns(ctx, builder):
    """Dựng tab trong một Blocks rồi trả (hàm làm mới, demo) để gọi handler trực tiếp."""
    with gr.Blocks() as demo:
        fn, _i, _o, _opts = builder(gr, demo, None, ctx)
    return fn, demo


def handler(demo, module, name):
    fns = [f.fn for f in demo.fns.values() if getattr(f.fn, '__module__', '') == module and f.fn.__name__ == name]
    assert len(fns) == 1, (module, name, len(fns))
    return fns[0]


def text_of(x):
    if isinstance(x, (list, tuple)):
        return ' '.join(text_of(y) for y in x)
    if isinstance(x, dict):
        return ' '.join(text_of(v) for k, v in x.items() if k != '__type__')
    return str(x)


# ---------- dựng giao diện ----------
def test_build_ui_co_hai_tab_moi_co_lượt_va_che_do_nap(world, tmp_path):
    ra.prepare_env(world['ctx'].run_dir)
    store = ra.Store(world['ctx'].run_dir, 'P1')
    demo, _theme = ra.build_ui(store, world['ctx'])
    ids = {getattr(b, 'elem_id', None) for b in demo.blocks.values()}
    for want in ('tab-thongke', 'tab-loc', 'tk-refresh', 'tk-export', 'tk-ttest', 'tk-luotnhap', 'tk-nguong', 'tk-tatca', 'tk-chibo', 'tk-goi', 'tk-view', 'loc-preview', 'loc-create', 'loc-cfg',
                 'loc-load-cfg', 'loc-save-cfg', 'loc-ten', 'loc-warn', 'loc-overwrite-ok', 'tab-caidat', 'tab-hop'):
        assert want in ids, want
    titles = [getattr(b, 'label', None) for b in demo.blocks.values() if getattr(b, 'elem_id', None) in ('tab-hop', 'tab-dongho', 'tab-thongke', 'tab-loc', 'tab-caidat')]
    assert titles == ['Họp team', 'Thống kê', 'Lọc dữ liệu', 'Cài đặt']        # không còn tab Đồng hồ (chip ở đầu trang); Thống kê, Lọc dữ liệu đặt trước "Cài đặt"
    os.makedirs('runs/_nap', exist_ok=True)
    ctx2 = ra.AppCtx(reviewer='P2', run_dir=os.path.join('runs', '_nap'), nap_only=True)
    demo2, _ = ra.build_ui(None, ctx2)                                                        # --nap: store None vẫn dựng đủ
    assert {'tab-thongke', 'tab-loc'} <= {getattr(b, 'elem_id', None) for b in demo2.blocks.values()}


def test_allowed_paths_chi_them_dung_hai_thu_muc_outputs():
    src = open(os.path.join(TOOL, 'review_app.py'), encoding='utf-8').read()
    start = src.index('allowed = [')
    allowed_block = src[start:src.index('_launch(demo, theme, ctx, port, allowed', start)]
    assert 'ca_kho.serve_dir(ctx.project_root)' in allowed_block and 'thong_ke_ui.serve_dir(ctx.project_root)' in allowed_block and 'loc_ui.serve_dir(ctx.project_root)' in allowed_block
    assert allowed_block.count('allowed.append(') == 3                                         # chỉ ca_kho (có sẵn) + thong_ke + train_sets
    for bad in ('"outputs"', "'outputs'", '"runs"', '"raw"', '"data"', '"final"'):
        assert bad not in allowed_block, bad
    assert thong_ke_ui.SERVE_REL == ('outputs', 'thong_ke') and loc_ui.SERVE_REL == ('outputs', 'train_sets')
    assert 'share=False' in src and 'server_name="127.0.0.1"' in src and 'share=True' not in src


def test_khong_tinh_luc_mo_trang_chi_khi_chon_tab():
    for fn in ('thong_ke_ui.py', 'loc_ui.py'):
        src = open(os.path.join(TOOL, fn), encoding='utf-8').read()
        assert 'demo.load(' not in src                                                          # tính khi chọn tab (tab.select ở review_app), không lúc mở trang
        assert src.count('api_visibility="private"') >= 1 and 'share=True' not in src and 'urllib' not in src and 'requests' not in src
    ra_src = open(os.path.join(TOOL, 'review_app.py'), encoding='utf-8').read()
    assert 'tab_tk.select(tk_fn, tk_in, tk_out, **tk_opts)' in ra_src and 'tab_loc.select(lc_fn, lc_in, lc_out, **lc_opts)' in ra_src


def test_hai_module_ui_khong_nap_gradio_o_dau_module():
    import subprocess
    code = ("import sys\nsys.path.insert(0, %r)\nimport thong_ke_ui, loc_ui\nfor m in ('gradio', 'torch', 'cv2', 'mediapipe', 'cvat_sdk', 'pandas'):\n"
            "    assert m not in sys.modules, m\nprint('ok')\n") % TOOL
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0 and 'ok' in r.stdout, r.stderr


# ---------- tab Thống kê ----------
def test_thong_ke_lam_moi_tinh_khi_goi_va_loc_lua_chon_do_server_tinh(world):
    fn, demo = tab_fns(world['ctx'], thong_ke_ui.stats_tab)
    out = fn('', 2.0, False, False, False, '', None)
    nhap, msg, view = out
    assert nhap['choices'][1] == ('R1', 'R1') and msg == ''
    assert 'tk-root' in view and 'So sánh thời gian' in view and 'NME của nháp' in view and 'Tỉ lệ điểm phải sửa' in view
    for gone in ('low_conf', 'AUROC', 'Số lượng dữ liệu', 'Tiến độ', 'giờ tiết kiệm', 'Giây rà'):
        assert gone not in view, gone                                                               # các thẻ bị bỏ không còn trên tab
    assert view.count('Chưa có số') == 3                                                            # chưa có gói/nhãn manual: ba khung trống nói rõ cần gì
    on = fn('R1', 5.0, True, False, True, '', None)                                                 # lượt hợp lệ giữ nguyên, gồm Ttest, mọi task
    assert on[0]['value'] == 'R1' and 'ngưỡng sửa 5,0% IOD' in on[2]
    bad = fn('KHONGCO', 2.0, False, True, False, '', None)                                          # lượt lạ bị bỏ khỏi lựa chọn (server tự tính danh sách)
    assert bad[0]['value'] == ''
    bad = fn('', 2.0, False, True, False, '/etc', None)
    assert 'ngoài thư mục dự án' in bad[1] and bad[2] == ''                                         # đường dẫn bấm giờ ngoài dự án: báo rõ, không traceback
    bad = fn('', 99.0, False, True, False, '', None)
    assert 'Ngưỡng' in bad[1] and bad[2] == ''


def test_thong_ke_clean_args_tu_choi_luot_la(world):
    runs = world['ctx'].runs_root
    assert thong_ke_ui.clean_args(runs, 'R1') == 'R1' and thong_ke_ui.clean_args(runs, '') is None and thong_ke_ui.clean_args(runs, None) is None
    with pytest.raises(nap_anh.RunError, match='nháp'):
        thong_ke_ui.clean_args(runs, 'NOPE')
    with pytest.raises(nap_anh.RunError, match='nháp'):
        thong_ke_ui.clean_args(runs, '../runs')
    assert thong_ke_ui.goi_paths(None) == [] and thong_ke_ui.goi_paths(['/khong/co.zip', __file__]) == []                  # chỉ nhận file .zip/.json có thật
    assert thong_ke_ui.reviewers(runs) == ['P1']                                                                              # tab Lọc dữ liệu vẫn dùng danh sách người rà này


def test_thong_ke_nap_goi_ket_qua_tu_nguoi_khac_qua_o_tai_len(world, tmp_path):
    from tk_fake import mo_phong
    import shutil
    d = tmp_path / 'tai_len'
    d.mkdir()
    ngoai = tmp_path / 'ban_goc'
    ngoai.mkdir()
    import dh_fake
    dh_fake.du_an(ngoai)
    mo_phong(str(ngoai))
    for f in sorted(os.listdir(ngoai / 'outputs' / 'goi_nhom')):
        if f.endswith('.zip'):
            shutil.copy(ngoai / 'outputs' / 'goi_nhom' / f, d)
    files = [str(d / f) for f in sorted(os.listdir(d))]
    fn, demo = tab_fns(world['ctx'], thong_ke_ui.stats_tab)
    nhap, msg, view = fn('', 2.0, False, False, False, '', files)
    assert 'assisted nhanh hơn manual' in view and '4 gói kết quả' in view and 'Chưa có số' not in view
    assert not os.path.exists(os.path.join(world['root'], 'outputs', 'ket_qua')) and not os.path.exists(os.path.join(world['root'], 'outputs', 'goi_nhom'))
    bad = d / 'hong.zip'
    bad.write_bytes(b'PK\x03\x04 hong')
    nhap, msg, view = fn('', 2.0, False, False, False, '', files + [str(bad)])
    assert 'Gói bị loại' in view and 'hong.zip' in view


def test_thong_ke_xuat_ghi_duoi_outputs_thong_ke_va_tu_choi_khi_dong(world):
    fn, demo = tab_fns(world['ctx'], thong_ke_ui.stats_tab)
    export = handler(demo, 'thong_ke_ui', 'on_export')
    before = tree_hash(world['root'])
    msg, dl = export('', 2.0, False, True, False, '', None)
    assert 'Đã xuất outputs/thong_ke/' in msg and 'Không có ảnh mặt' in msg and dl['visible'] is True and dl['value'].endswith('thong_ke.html')
    assert os.path.isfile(dl['value']) and os.path.commonpath([dl['value'], os.path.join(world['root'], 'outputs', 'thong_ke')]) == os.path.join(world['root'], 'outputs', 'thong_ke')
    assert tree_hash(world['root']) == before and world['root'] not in msg                        # chỉ đọc runs/raw/final/data; thông báo không lộ đường dẫn tuyệt đối
    world['ctx'].closing = True
    msg2, dl2 = export('', 2.0, False, True, False, '', None)
    assert 'đang đóng' in msg2 and dl2['visible'] is False
    assert len(os.listdir(os.path.join(world['root'], 'outputs', 'thong_ke'))) == 1                # không ghi thêm khi trang đang đóng


# ---------- tab Thống kê: mục Nhập tay (nhóm manual gán thẳng trong CVAT) ----------
TAY_IDS = ('tk-tay', 'tk-tay-note', 'tk-tay-nguoi', 'tk-tay-nhom', 'tk-tay-dot', 'tk-tay-gio', 'tk-tay-ngay', 'tk-tay-file', 'tk-tay-ghichu', 'tk-tay-add', 'tk-tay-msg',
           'tk-tay-list', 'tk-tay-chon', 'tk-tay-remove')


def nhan_tay_xml(tmp_path, name='annotations.xml', anh=('F_001', 'F_002', 'F_003', 'F_004')):
    from dh_fake import mat_mau, viet_xml
    return viet_xml(os.path.join(str(tmp_path), 'tai_len_tay', name), {f'{a}.png': mat_mau(i + 1, 0.3) for i, a in enumerate(anh)})


def tay_fns(world):
    with gr.Blocks() as demo:
        thong_ke_ui.stats_tab(gr, demo, None, world['ctx'])
    return demo, {n: handler(demo, 'thong_ke_ui', n) for n in ('on_tay_add', 'on_tay_remove', 'on_tay_open', 'on_tay_list')}


def test_nhap_tay_co_du_thanh_phan_dong_san_dat_sau_o_tai_goi_truoc_nut_refresh(world):
    demo, _f = tay_fns(world)
    blocks = list(demo.blocks.values())
    ids = [getattr(b, 'elem_id', None) for b in blocks]
    for want in TAY_IDS:
        assert want in ids, want
    acc = blocks[ids.index('tk-tay')]
    assert type(acc).__name__ == 'Accordion' and acc.open is False and acc.label == 'Nhập tay: nhóm gán tay trực tiếp trong CVAT (không dùng tool)'
    assert ids.index('tk-goi') < ids.index('tk-tay') < ids.index('tk-tay-remove') < ids.index('tk-refresh') < ids.index('tk-export')
    by = dict(zip(ids, blocks))
    assert by['tk-tay-add'].value == 'Add manual entry' and by['tk-tay-add'].variant == 'primary' and by['tk-tay-remove'].value == 'Remove entry'
    assert by['tk-tay-nguoi'].value is None and [c[1] for c in by['tk-tay-nguoi'].choices] == ['P1', 'P2', 'P3', 'P4', 'P5']
    assert by['tk-tay-nhom'].value == 'manual' and [c[1] for c in by['tk-tay-nhom'].choices] == ['manual', 'assisted']
    assert by['tk-tay-gio'].placeholder == '1:25:30 · 85:30 · 85 (phút)' and by['tk-tay-ngay'].placeholder == 'trống = hôm nay; dd/mm/yyyy'
    assert 'cùng tên ảnh' in by['tk-tay-dot'].label and by['tk-tay-file'].file_count == 'multiple' and by['tk-tay-file'].type == 'filepath'
    assert set(by['tk-tay-file'].file_types) == {'.xml', '.zip'} and by['tk-tay-file'].label == 'File nhãn xuất từ CVAT (CVAT for images 1.1, không kèm ảnh)'
    tay = [f for f in demo.fns.values() if getattr(f.fn, '__name__', '').startswith('on_tay_')]
    assert tay and all(f.concurrency_id == 'thongke_tay' and f.concurrency_limit == 1 and f.api_visibility == 'private' for f in tay)


def test_nhap_tay_o_dot_lay_bo_anh_cua_config(world):
    json.dump({'nhom': {}, 'bo_anh': 'NAP_007'}, open(os.path.join(world['root'], 'config', 'nhom_thi_nghiem.json'), 'w'))
    demo, f = tay_fns(world)
    assert [b.value for b in demo.blocks.values() if getattr(b, 'elem_id', None) == 'tk-tay-dot'] == ['NAP_007']
    dot, lst, sel = f['on_tay_open']('')
    assert dot['value'] == 'NAP_007' and 'Chưa có bản nhập tay' in lst and sel['choices'] == []
    dot, lst, sel = f['on_tay_open']('KHAC')                                                         # đã gõ thì giữ nguyên
    assert 'value' not in dot


def test_nhap_tay_add_ghi_vao_goi_nhom_va_hien_danh_sach(world, tmp_path):
    demo, f = tay_fns(world)
    x = nhan_tay_xml(tmp_path)
    before = tree_hash(world['root'], ('runs', 'raw', 'final', 'data', 'config'))
    msg, lst, sel = f['on_tay_add']('P2', 'manual', 'NAP_001', '6:00', '', [x], '', None)
    assert 'm-ok' in msg and 'Đã thêm ketqua_P2_' in msg and '4 mặt' in msg and '90,0 giây/mặt' in msg and world['root'] not in msg and 'annotations.xml: 4 ảnh có nhãn' in msg
    d = os.path.join(world['root'], 'outputs', 'goi_nhom')
    files = sorted(os.listdir(d))
    assert len(files) == 2 and files[0].startswith('ketqua_P2_') and files[0].endswith('_NAP_001.json') and files[1].endswith('.zip')
    assert 'P2' in lst and 'NAP_001' in lst and '06:00' in lst and '90,0' in lst and len(sel['choices']) == 1 and sel['choices'][0][1] == files[0][:-5] and sel['value'] is None
    assert tree_hash(world['root'], ('runs', 'raw', 'final', 'data', 'config')) == before                # chỉ ghi dưới outputs/goi_nhom
    fn, _demo = tab_fns(world['ctx'], thong_ke_ui.stats_tab)
    nhap, m2, view = fn('', 2.0, False, False, False, '', None)
    assert '(nhập tay)' in view and 'manual (gán tay): P2' in view
    msg2, _l, _s = f['on_tay_add']('P2', 'manual', 'NAP_001', '6:00', '', [x], '', None)                 # bấm lần hai: không thêm gói
    assert 'Đã thêm' in msg2 and sorted(os.listdir(d)) == files
    lst2 = f['on_tay_list']()
    assert lst2[0] == lst


@pytest.mark.parametrize('args,match', [(('P2', 'manual', 'NAP_001', 'abc', ''), 'Không đọc được thời gian'), (('P2', 'manual', 'NAP_001', '', ''), 'Chưa nhập thời gian'),
                                        ((None, 'manual', 'NAP_001', '85', ''), 'Chưa chọn người'), (('P2', 'manual', '', '85', ''), 'Chưa nhập đợt'),
                                        (('P2', 'manual', 'NAP_001', '85', '01/01/2099'), 'tương lai')])
def test_nhap_tay_sai_dau_vao_canh_bao_khong_ghi_gi(world, tmp_path, args, match):
    demo, f = tay_fns(world)
    msg, lst, sel = f['on_tay_add'](*args, [nhan_tay_xml(tmp_path)], '', None)
    assert 'm-warn' in msg and match in msg
    assert not os.path.exists(os.path.join(world['root'], 'outputs', 'goi_nhom'))
    msg, lst, sel = f['on_tay_add']('P2', 'manual', 'NAP_001', '85', '', None, '', None)                # chưa chọn file nhãn
    assert 'Chưa chọn file nhãn' in msg and not os.path.exists(os.path.join(world['root'], 'outputs', 'goi_nhom'))
    msg, lst, sel = f['on_tay_add']('P2', 'manual', 'NAP_001', '85', '', [nhan_tay_xml(tmp_path)], 'gửi kien@example.com', None)
    assert 'Ghi chú bị chặn' in msg and not os.path.exists(os.path.join(world['root'], 'outputs', 'goi_nhom'))


def test_nhap_tay_remove_chuyen_vao_da_bo_va_tu_choi_khi_dong(world, tmp_path):
    demo, f = tay_fns(world)
    x = nhan_tay_xml(tmp_path)
    f['on_tay_add']('P1', 'manual', 'NAP_001', '85', '', [x], '', None)
    f['on_tay_add']('P2', 'manual', 'NAP_001', '1:20:00', '', [x], '', None)
    d = os.path.join(world['root'], 'outputs', 'goi_nhom')
    _l, sel = f['on_tay_list']()
    ten = [c[1] for c in sel['choices'] if c[1].startswith('ketqua_P1_')][0]
    msg, lst, sel = f['on_tay_remove'](ten)
    assert 'm-ok' in msg and 'Đã gỡ ' + ten in msg and '_da_bo' in msg and 'không xoá' in msg
    assert sorted(os.listdir(os.path.join(d, '_da_bo'))) == [ten + '.json', ten + '.zip'] and not os.path.exists(os.path.join(d, ten + '.zip'))
    assert [c[1] for c in sel['choices']] == [n[:-4] for n in sorted(os.listdir(d)) if n.endswith('.zip')] and '<td>P1</td>' not in lst and '<td>P2</td>' in lst
    msg, _l, _s = f['on_tay_remove']('../config/m28_config')
    assert 'm-warn' in msg and 'Chọn một bản nhập tay' in msg
    msg, _l, _s = f['on_tay_remove'](None)
    assert 'Chọn một bản nhập tay' in msg
    world['ctx'].closing = True
    left = sorted(os.listdir(d))
    msg, _l, _s = f['on_tay_add']('P3', 'manual', 'NAP_001', '85', '', [x], '', None)
    assert 'đang đóng' in msg and sorted(os.listdir(d)) == left
    ten2 = [x[:-4] for x in left if x.endswith('.zip')][0]
    msg, _l, _s = f['on_tay_remove'](ten2)
    assert 'đang đóng' in msg and sorted(os.listdir(d)) == left


def test_nhap_tay_tu_choi_khi_goi_dang_tai_len_cung_nguoi_cung_dot(world, tmp_path):
    from tk_fake import nd_goi, viet_goi
    import dh_fake
    import shutil
    ngoai = dh_fake.du_an(tmp_path / 'ban_goc')
    r = viet_goi(ngoai, nd_goi('P1', 'manual', 40.0))
    up = tmp_path / 'up'
    up.mkdir()
    shutil.copy(os.path.join(ngoai, r['zip']), up)
    demo, f = tay_fns(world)
    msg, _l, _s = f['on_tay_add']('P1', 'manual', 'NAP_001', '85', '', [nhan_tay_xml(tmp_path)], '', [str(up / 'ketqua_P1_1410_NAP_001.zip')])
    assert 'm-warn' in msg and 'ketqua_P1_1410_NAP_001.zip' in msg and 'tính hai lần' in msg
    assert not os.path.exists(os.path.join(world['root'], 'outputs', 'goi_nhom'))


def test_nhap_tay_cung_nguoi_trung_ten_anh_khac_dot_bi_tu_choi(world, tmp_path):
    """C10: cùng người, cùng file nhãn nhưng gõ tên đợt khác (ví dụ tên bộ ảnh rồi tên lượt): trước đây thành hai gói, giờ tính hai lần. Giờ từ chối, nêu gói đã có."""
    demo, f = tay_fns(world)
    x = nhan_tay_xml(tmp_path)
    msg, _l, _s = f['on_tay_add']('P1', 'manual', 'NAP_001', '85', '', [x], '', None)
    assert 'm-ok' in msg
    d = os.path.join(world['root'], 'outputs', 'goi_nhom')
    files = sorted(os.listdir(d))
    msg, lst, sel = f['on_tay_add']('P1', 'manual', 'NAP_002', '85', '', [x], '', None)
    ten = [n[:-4] for n in files if n.endswith('.zip')][0]
    assert 'm-warn' in msg and f'Đã có gói {ten}.zip của P1 (đợt NAP_001, bản nhập tay khác) trùng 4 ảnh' in msg and 'Remove entry' in msg and 'tính hai lần' in msg
    assert sorted(os.listdir(d)) == files and len(sel['choices']) == 1 and world['root'] not in msg
    msg, _l, _s = f['on_tay_add']('P2', 'manual', 'NAP_002', '85', '', [x], '', None)                   # người khác cùng ảnh: được
    assert 'm-ok' in msg


def test_nhap_tay_assisted_khong_co_nhap_van_ghi_nhung_canh_bao_ten_luot(world, tmp_path):
    """C10: nhập cho người assisted với đợt không phải tên lượt (runs\\<lượt>) thì máy không có nháp: vẫn ghi gói, nhưng thông báo là CẢNH BÁO (m-warn), nói NME của nháp và
    tỉ lệ sửa sẽ thiếu mặt người này và đợt phải là tên lượt. Ghi chú của mục Nhập tay và ô Đợt nói trước điều đó."""
    json.dump({'nhom': {}, 'bo_anh': 'bo200_v1'}, open(os.path.join(world['root'], 'config', 'nhom_thi_nghiem.json'), 'w'))
    demo, f = tay_fns(world)
    by = {getattr(b, 'elem_id', None): b for b in demo.blocks.values()}
    assert 'tên lượt' in by['tk-tay-dot'].info and 'runs\\bo200 thì gõ bo200' in by['tk-tay-dot'].info
    note = thong_ke_ui.tay_note_html()
    assert 'assisted' in note and '<b>tên lượt</b>' in note and 'runs\\&lt;lượt&gt;' in note and 'kể cả khác tên đợt' in note
    msg, lst, sel = f['on_tay_add']('P4', 'assisted', 'bo200_v1', '85', '', [nhan_tay_xml(tmp_path)], '', None)
    assert 'm-warn' in msg and 'Đã thêm ketqua_P4_' in msg and 'không có nháp của đợt bo200_v1' in msg and 'TÊN LƯỢT' in msg
    assert 'không vào NME của nháp và tỉ lệ điểm phải sửa' in msg and 'máy này có nháp ở: R1' in msg and world['root'] not in msg
    assert len(sel['choices']) == 1 and sel['choices'][0][1].endswith('_bo200_v1')                     # gói vẫn được ghi
    msg, _l, _s = f['on_tay_add']('P5', 'manual', 'NAP_003', '85', '', [nhan_tay_xml(tmp_path, anh=('F_201',))], '', None)
    assert 'm-ok' in msg and 'Bộ ảnh ghi trong gói: bo200_v1' in msg and 'đợt giữ đúng như gõ: NAP_003' in msg   # bo_anh lấy từ config: nói rõ


# ---------- tab Lọc dữ liệu ----------
def test_loc_to_cfg_from_cfg_khu_hoi_va_kiem_chat(world):
    v = dict.fromkeys(loc_ui.KEYS)
    v.update(nguon=['yawdd'], quyet_dinh=['nhan'], luot=['R1'], co_nguon='flags_json', co_tong_min=2, co_tong_max=30, nhom_mattrai_max=4, vung_eye_min=1,
             nme_max=9.5, pose='0', camera=['dash'], thieu_diem=2, giu_mat=True, kem_anh=False, zip=True, ten='thu1', set_goc='F, X')
    cfg = loc_ui.cfg_from_values(world['root'], v)
    assert cfg['co']['tong'] == {'toi_thieu': 2, 'toi_da': 30} and cfg['co']['theo_nhom'] == {'mattrai': {'toi_thieu': None, 'toi_da': 4}}
    assert cfg['co']['theo_vung'] == {'eye': {'toi_thieu': 1, 'toi_da': None}} and cfg['nme_nhap'] == {'toi_thieu': None, 'toi_da': 9.5}
    assert cfg['manifest']['pose'] == [0] and cfg['manifest']['camera'] == ['dash'] and cfg['set_goc'] == ['F', 'X'] and cfg['nhan']['so_diem_thieu_toi_da'] == 2
    assert cfg['giu_mat_khong_nhap'] is True and cfg['kem_anh'] is False and cfg['zip'] is True and cfg['nguon_nhan']['luot'] == ['R1']
    back = loc_ui.from_cfg(cfg)
    assert loc_ui.cfg_from_values(world['root'], back) == cfg                                      # nạp lại cho đúng cấu hình cũ
    v2 = dict(v, co_tong_min=9, co_tong_max=3)
    with pytest.raises(ld.CauHinhLoi, match='lớn hơn'):
        loc_ui.cfg_from_values(world['root'], v2)
    with pytest.raises(ld.CauHinhLoi, match='không phải số'):
        loc_ui.cfg_from_values(world['root'], dict(v, nme_max='abc'))
    with pytest.raises(ld.CauHinhLoi, match='ten'):
        loc_ui.cfg_from_values(world['root'], dict(v, ten='../x'))
    assert len(loc_ui.KEYS) == len(set(loc_ui.KEYS)) == 27 + 14 + 8
    assert set(GROUPS) == set(__import__('m28core.mau_nhom', fromlist=['x']).GROUP_COLOR) and REGIONS == ['brow', 'nose', 'eye', 'lip']


def loc_inputs(**over):
    v = dict.fromkeys(loc_ui.KEYS)
    v.update(luot=[], luot_nhap='', nguon=['yawdd', 'drivface'], quyet_dinh=['nhan', 'gan_tay'], nguoi_ra=[], set_goc='', co_nguon='flags_json', thieu_diem=0,
             giu_mat=False, loc_tap_danh_gia=False, kem_anh=True, zip=False, ten='bo_ui', camera=[], glasses=[], pose='', expression='', occlusion='', illumination='', blur='')
    v.update(over)
    return [v[k] for k in loc_ui.KEYS]


def loc_demo(world):
    with gr.Blocks() as demo:
        fn, ins, outs, _opts = loc_ui.loc_tab(gr, demo, None, world['ctx'])
    return fn, demo


def test_loc_xem_truoc_khong_ghi_tao_bo_xac_nhan_ghi_de_va_dong(world):
    fn, demo = loc_demo(world)
    prev, make, over = (handler(demo, 'loc_ui', n) for n in ('on_preview', 'on_make', 'on_overwrite'))
    a = loc_inputs()
    before = tree_hash(world['root'], ('runs', 'raw', 'final', 'data', 'config'))
    msg, res, dl, confirm = prev(*a)
    assert 'dry-run' in msg and 'Bị loại theo thứ tự tiêu chí' in res and 'mặt vào' in res and '<img' not in res and confirm['visible'] is False
    assert not os.path.exists(os.path.join(world['root'], 'outputs'))                              # xem trước không ghi gì
    msg, res, dl, confirm = make(*a)
    assert 'Đã tạo outputs/train_sets/bo_ui' in msg and 'không đưa lên git hay chat AI' in msg and dl['visible'] is False
    base = os.path.join(world['root'], 'outputs', 'train_sets', 'bo_ui')
    assert os.path.isfile(os.path.join(base, 'manifest.csv')) and os.path.isdir(os.path.join(base, 'anh'))
    assert tree_hash(world['root'], ('runs', 'raw', 'final', 'data', 'config')) == before
    marker = os.path.join(base, 'cu.txt')
    open(marker, 'w').write('x')
    msg, res, dl, confirm = make(*a)                                                                  # đã có: hỏi xác nhận, chưa ghi đè
    assert 'đã có' in msg and confirm['visible'] is True and os.path.exists(marker)
    msg, res, dl, confirm = over(*a)
    assert 'Đã tạo' in msg and not os.path.exists(marker) and confirm['visible'] is False
    # tạo kèm zip: nút tải hiện, file zip nằm trong outputs/train_sets
    msg, res, dl, confirm = make(*loc_inputs(ten='bo_zip', zip=True))
    assert dl['visible'] is True and dl['value'] == os.path.join(world['root'], 'outputs', 'train_sets', 'bo_zip.zip') and 'file .zip' in msg
    world['ctx'].closing = True
    msg, res, dl, confirm = make(*loc_inputs(ten='bo_dong'))
    assert 'đang đóng' in msg and not os.path.exists(os.path.join(world['root'], 'outputs', 'train_sets', 'bo_dong'))


def test_loc_tu_choi_ten_xau_luot_la_va_cau_hinh_sai(world):
    fn, demo = loc_demo(world)
    prev, make = handler(demo, 'loc_ui', 'on_preview'), handler(demo, 'loc_ui', 'on_make')
    for bad in ('../x', 'a/b', 'a\\b', ''):
        msg, *_ = make(*loc_inputs(ten=bad))
        assert 'Chưa' in msg or 'ten' in msg or 'Tên' in msg or 'không hợp lệ' in msg, bad
    assert not os.path.exists(os.path.join(world['root'], 'outputs', 'train_sets'))
    msg, res, *_ = prev(*loc_inputs(luot=['../runs']))
    assert 'không có trong danh sách' in msg and res == ''
    msg, res, *_ = prev(*loc_inputs(co_tong_min=9, co_tong_max=3))
    assert 'lớn hơn' in msg
    msg, res, *_ = prev(*loc_inputs(nme_min='abc'))
    assert 'không phải số' in msg


def test_loc_ro_ri_nguoi_hien_loi_va_khong_tao(world):
    p = world['p']
    p.manifest['Tdev_001']['subject'] = p.manifest['F_001']['subject']
    p.write_manifest()
    fn, demo = loc_demo(world)
    msg, res, *_ = handler(demo, 'loc_ui', 'on_preview')(*loc_inputs())
    assert 'rò rỉ người' in res
    msg, res, *_ = handler(demo, 'loc_ui', 'on_make')(*loc_inputs())
    assert 'rò rỉ người' in msg and not os.path.exists(os.path.join(world['root'], 'outputs', 'train_sets', 'bo_ui'))


def test_loc_luu_va_nap_cau_hinh_chi_trong_outputs(world):
    import shutil
    shutil.copy(os.path.join(HERE, '..', 'config', 'loc_mau.json'), os.path.join(world['root'], 'config', 'loc_mau.json'))
    fn, demo = loc_demo(world)
    save, load = handler(demo, 'loc_ui', 'on_save'), handler(demo, 'loc_ui', 'on_load')
    a = loc_inputs(co_tong_max=25, ten='goc')
    msg, sel = save('loc_cua_toi', *a)
    p = os.path.join(world['root'], 'outputs', 'loc_cua_toi.json')
    assert 'Đã lưu outputs' in msg and os.path.isfile(p) and sel['value'] == 'outputs/loc_cua_toi.json'
    cfg = json.load(open(p, encoding='utf-8'))
    assert cfg['co']['tong']['toi_da'] == 25 and cfg['ten'] == 'goc'
    out = load('outputs/loc_cua_toi.json')
    order = [k for k in loc_ui.KEYS]
    vals = dict(zip(order, [u['value'] for u in out[1:]]))
    assert vals['co_tong_max'] == '25' and vals['co_tong_min'] == '' and vals['ten'] == 'goc'          # ô số tuỳ chọn là ô chữ: trống = không giới hạn and 'Đã nạp' in out[0]
    mau = load('config/loc_mau.json')
    assert 'Đã nạp' in mau[0] and dict(zip(order, [u['value'] for u in mau[1:]]))['ten'] == 'finetune_v1'
    for bad in ('../../etc/passwd', '/etc/passwd', 'outputs/khongco.json', 'config/m28_config.json'):
        out = load(bad)
        assert 'không có trong danh sách' in out[0], bad
    for bad in ('../x', 'a/b', 'a\\b', 'x' * 45, 'a b'):
        msg, _ = save(bad, *a)
        assert 'Tên file cấu hình' in msg, bad
    assert not os.path.exists(os.path.join(world['root'], 'x.json')) and not os.path.exists(os.path.join(world['root'], 'outputs', 'x.json'))
    world['ctx'].closing = True
    msg, _ = save('dong', *a)
    assert 'đang đóng' in msg and not os.path.exists(os.path.join(world['root'], 'outputs', 'dong.json'))


def test_loc_lam_moi_danh_sach_luot_nguoi_ra_cau_hinh(world):
    fn, demo = loc_demo(world)
    luot, nhap, nguoi, cfgsel, msg = fn(['R1', 'X'], 'R1', ['P1', 'auto'], None)
    assert luot['choices'] == ['R1'] and luot['value'] == ['R1'] and nhap['value'] == 'R1' and nguoi['choices'] == ['P1'] and nguoi['value'] == ['P1']
    assert ('config\\loc_mau.json (mẫu)', 'config/loc_mau.json') in cfgsel['choices']


def test_loc_ket_qua_html_khong_co_anh_khong_ma_tai_xe(world):
    kq = ld.chay_loc(world['root'], ld.kiem_cau_hinh({}, GROUPS, REGIONS))
    h = loc_ui.kq_html(kq)
    assert '<img' not in h and 'Còn lại' in h and 'train' in h and 'val' in h and 'test' in h
    subjects = {r['subject'] for r in world['p'].manifest.values()}
    assert not any(s in h for s in subjects)


def test_nhap_tay_hien_gio_bang_chu_va_canh_bao_go_nham_hoac_lech_nhom(world, tmp_path):
    """'1:30' là 1 phút 30 giây: thông báo ghi rõ bằng chữ; giây/mặt vô lý (< 5) và nhóm khác config\nhom_thi_nghiem.json thì cảnh báo (gói vẫn ghi, gỡ được)."""
    json.dump({'nhom': {'P3': 'assisted'}, 'bo_anh': ''}, open(os.path.join(world['root'], 'config', 'nhom_thi_nghiem.json'), 'w'))
    _demo, f = tay_fns(world)
    msg, _l, _s = f['on_tay_add']('P2', 'manual', 'NAP_001', '1:20:00', '', [nhan_tay_xml(tmp_path)], '', None)
    assert 'm-ok' in msg and '1:20:00 = 1 giờ 20 phút 0 giây' in msg and 'gõ nhầm' not in msg
    msg, _l, _s = f['on_tay_add']('P1', 'manual', 'NAP_002', '0:12', '', [nhan_tay_xml(tmp_path, 'p1.xml', ('G_001', 'G_002', 'G_003', 'G_004'))], '', None)
    assert 'm-warn' in msg and '00:12 = 12 giây' in msg and 'gõ nhầm thời gian' in msg and '1:30:00' in msg
    msg, _l, _s = f['on_tay_add']('P3', 'manual', 'NAP_003', '85', '', [nhan_tay_xml(tmp_path, 'p3.xml', ('H_001', 'H_002'))], '', None)
    assert 'm-warn' in msg and 'ghi P3 ở nhóm assisted' in msg and len(f['on_tay_list']()[1]['choices']) == 3
