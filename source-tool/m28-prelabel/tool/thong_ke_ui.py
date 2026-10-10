"""Tab "Thống kê" của trang rà soát M28 (dựng theo mẫu ca_kho.member_tab): CHỈ BA CHỈ SỐ của thí nghiệm hai nhóm độc lập (QĐ-006): NME của nháp so với nhãn manual,
tỉ lệ điểm phải sửa, so sánh thời gian manual với assisted. Tab "Lọc dữ liệu" (loc_ui.py) là việc khác và giữ nguyên.

Mục "Nhập tay" (accordion, đóng sẵn; m28core\\nhap_tay.py): người nhóm MANUAL gán thẳng trong CVAT không dùng tool nên không có gói của đồng hồ; nhóm trưởng nhập cho từng người
người, nhóm, đợt/bộ ảnh, thời gian làm (gõ tay), ngày làm và file nhãn xuất từ CVAT ("CVAT for images 1.1", .xml/.zip không kèm ảnh). Mỗi bản là một gói kết quả bình thường
(outputs\\goi_nhom\\ketqua_<Pk>_<DDMM>_<đợt>.zip, nguon_nhap="nhap_tay") nên tính vào ba chỉ số y như gói của đồng hồ; bấm hai lần không nhân đôi; cùng người đã có gói
khác cùng đợt, hoặc trùng tên ảnh dù khác đợt, thì từ chối; "Remove entry" chỉ chuyển file vào outputs\\goi_nhom\\_da_bo (không xoá). Nhóm assisted: đợt phải là tên lượt
(runs\\<lượt>) đã dựng nháp; máy không có nháp đó thì vẫn thêm nhưng thông báo là cảnh báo (NME của nháp và tỉ lệ sửa thiếu mặt của người đó).

Quy ước (giống ca_kho.py):
  * Đầu module KHÔNG nạp gradio (nhận `gr` làm tham số); chỉ thư viện chuẩn và các module tool/ chỉ thư viện chuẩn + numpy nạp lười. Không gọi mạng, không đọc token.
  * Tính KHI CHỌN TAB (tab.select) hoặc bấm Refresh, không tính lúc mở trang; chỉ ĐỌC runs\\, raw\\, data\\, outputs\\. Chỉ ghi khi bấm "Export CSV + HTML" (chỉ dưới outputs\\thong_ke)
    và khi bấm "Add manual entry" / "Remove entry" của mục Nhập tay (chỉ dưới outputs\\goi_nhom). Chỉ tải gói lên (ô "Nạp các gói...") thì không ghi gì.
  * Giá trị từ trình duyệt (lượt chứa nháp, đường dẫn bấm giờ) được kiểm lại ở server: lượt phải là phần tử của danh sách do server tính; đường dẫn bấm giờ phải nằm trong thư mục dự án;
    gói kết quả tải lên (nút "Nạp các gói kết quả của nhóm") được đọc từ file tạm của Gradio, kiểm sha256 và cấu trúc trước khi tin, không lưu vào dự án.
  * Handler: api_visibility="private", concurrency_id riêng (thongke, thongke_xuat, thongke_tay), không chặn tab khác; lỗi -> gr.Warning và thông báo tiếng Việt, không traceback
    lên trang; trang đang đóng (Close page) thì từ chối ghi.
  * Trang không hiện ảnh mặt (chỉ số); bản xuất tĩnh cũng không có ảnh mặt, không mã tài xế.
"""
import datetime
import glob
import html
import os
import re
import sys
import threading

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)
import dot_anh  # noqa: E402
import nap_anh  # noqa: E402
import thong_ke  # noqa: E402
import thong_ke_html  # noqa: E402
from m28core import bang_mat, nhap_tay, nhom as nhom_mod, toc_do  # noqa: E402

SERVE_REL = ("outputs", "thong_ke")
NGUOI_RE = re.compile(r"[A-Za-z0-9_-]{1,32}")
_LOCK = threading.Lock()                                    # một lần xuất tại một thời điểm
CSS = thong_ke_html.CSS + """
#tk-filters { gap: 10px; flex-wrap: wrap; align-items: flex-end; }
#tk-filters > * { min-width: 160px !important; }
#tk-btns { gap: 8px; flex-wrap: wrap; } #tk-btns button { min-width: 0 !important; flex: 1 1 140px !important; }
#tk-refresh, #tk-export { font-weight: 800; }
#tk-view, #tk-msg, #tk-note { padding: 0 !important; } #tab-thongke { padding: 8px 0 0 !important; gap: 10px; max-width: 1120px; margin: 0 auto; width: 100%; }
#tk-msg:not(:has(.html-container > div > *)) { display: none; }
#tk-tay-row, #tk-tay-bo { gap: 10px; flex-wrap: wrap; align-items: flex-end; } #tk-tay-row > * { min-width: 150px !important; }
#tk-tay-bo > * { min-width: 200px !important; } #tk-tay-remove { flex: 0 1 160px !important; min-width: 0 !important; }
#tk-tay-note, #tk-tay-msg, #tk-tay-list { padding: 0 !important; } #tk-tay-msg:not(:has(.html-container > div > *)) { display: none; }
"""


def serve_dir(project_root):
    """<project>\\outputs\\thong_ke (tạo nếu chưa có; lỗi tạo thì vẫn trả đường dẫn)."""
    p = os.path.join(project_root, *SERVE_REL)
    try:
        os.makedirs(p, exist_ok=True)
    except OSError:
        pass
    return p


def msg_html(text, level="info"):
    return f'<div class="m28-msg m-{html.escape(level)}" role="status">{html.escape(text)}</div>' if text else ""


def note_html():
    return ('<div class="nap-box nap-warn"><b>Trang này chỉ có số liệu, không có ảnh mặt.</b> Số liệu tổng hợp vẫn là dữ liệu của dự án phi thương mại (YawDD, DrivFace): '
            'chỉ dùng nội bộ nhóm; bản HTML xuất không có ảnh, không mã tài xế, không đường dẫn tuyệt đối. Ba chỉ số: NME của nháp so với nhãn manual, tỉ lệ điểm phải sửa, '
            'so sánh thời gian manual với assisted (hai nhóm độc lập). <b>Ttest là tập đo một lần</b>: chỉ bật "Gồm Ttest" đúng buổi đo.</div>')


def reviewers(runs_root):
    """Tên người rà có file triage_<người>.csv ở bất kỳ lượt nào (trừ auto: máy tự quyết, không phải người rà). Dùng chung với tab Lọc dữ liệu (loc_ui.py)."""
    out = set()
    for r in dot_anh.list_runs(runs_root):
        for p in glob.glob(os.path.join(glob.escape(os.path.join(runs_root, r, "review")), "triage_*.csv")):
            who = os.path.basename(p)[len("triage_"):-len(".csv")]
            if who and who != bang_mat.AUTO and NGUOI_RE.fullmatch(who):
                out.add(who)
    return sorted(out)


def clean_args(runs_root, luot_nhap):
    """Kiểm giá trị từ trình duyệt: lượt chứa nháp phải có trong danh sách server. Trả luot_nhap|None; sai thì RunError."""
    runs = dot_anh.list_runs(runs_root)
    if luot_nhap and luot_nhap not in runs:
        raise nap_anh.RunError(f"Lượt chứa nháp {luot_nhap!r} không có trong danh sách lượt: bấm Refresh.")
    return luot_nhap or None


def _paths(files, exts):
    out = []
    for f in files or []:
        p = f if isinstance(f, str) else getattr(f, "name", None)
        if p and os.path.isfile(p) and p.lower().endswith(exts):
            out.append(p)
    return out


def goi_paths(files):
    """Đường dẫn các gói tải lên (gr.File trả list đường dẫn hoặc đối tượng có .name)."""
    return _paths(files, (".zip", ".json"))


def nhan_paths(files):
    """Đường dẫn các file nhãn CVAT tải lên ở mục Nhập tay (.xml hoặc .zip); nhap_tay.doc_file_nhan kiểm nội dung."""
    return _paths(files, (".xml", ".zip"))


def tay_note_html():
    return ('<div class="tk-root"><div class="tk-note">Cho người nhóm <b>manual</b> gán tay thẳng trong CVAT, không dùng tool (không có đồng hồ, không có gói kết quả). Mỗi người, mỗi đợt nhập '
            '<b>một lần</b>: thời gian làm (cả buổi, không tính lúc nghỉ) và file nhãn xuất từ CVAT ("CVAT for images 1.1", không kèm ảnh; mỗi job một file cũng được). Bản nhập tay là '
            'một gói kết quả bình thường ghi vào outputs\\goi_nhom: tính vào ba chỉ số y như gói của đồng hồ (giây/mặt = thời gian ÷ số ảnh có nhãn); tool\\tong_ket.py cũng tự đọc. '
            'Một người không gán một ảnh hai lần: bản trùng tên ảnh với gói khác của cùng người (kể cả khác tên đợt) bị từ chối. '
            'Sửa thời gian, đợt hay file của một bản đã thêm: Remove entry rồi thêm lại. '
            'Nếu nhập cho người nhóm <b>assisted</b>: đợt phải là <b>tên lượt</b> đã dựng nháp (thư mục runs\\&lt;lượt&gt;, ví dụ bo200), không phải tên bộ ảnh, '
            'thì gói mới kèm nháp để đo NME của nháp và tỉ lệ điểm phải sửa.</div></div>')


def tay_list_html(rows):
    """Bảng các bản nhập tay (nhap_tay.liet_ke). Không ảnh, không đường dẫn."""
    if not rows:
        return '<div class="tk-root"><div class="tk-note">Chưa có bản nhập tay nào trong outputs\\goi_nhom.</div></div>'
    cols = [("Người", "nguoi", "l"), ("Nhóm", lambda r: thong_ke_html.COND_VI.get(r["nhom"], r["nhom"]), "l"), ("Đợt", "dot", "l"), ("Ngày làm", "ngay", "l"), ("Mặt", "so_mat", "r"),
            ("Thời gian", lambda r: nhap_tay.fmt_giay(r["giay"]), "r"), ("Giây/mặt", lambda r: thong_ke_html.num(r["giay"] / r["so_mat"], 1) if r["so_mat"] else "—", "r"),
            ("Gói", "ten", "l")]
    return f'<div class="tk-root"><h5>Bản nhập tay đang được tính ({len(rows)})</h5>' + thong_ke_html.bang(cols, rows) + "</div>"


def tay_choices(rows):
    return [(f'{r["nguoi"]} · {r["dot"]} · {r["ngay"]} ({r["ten"]})', r["ten"]) for r in rows]


def stats_tab(gr, demo, store, ctx):
    """Tab "Thống kê". Trả (hàm làm mới, inputs, outputs, opts) để build_ui nối vào tab.select."""
    opts = dict(show_progress="minimal", api_visibility="private", concurrency_limit=1, concurrency_id="thongke")
    gr.HTML(note_html(), elem_id="tk-note", apply_default_css=False)
    with gr.Row(elem_id="tk-filters"):
        d_nhap = gr.Dropdown(choices=[("(không)", "")], value="", label="Lượt chứa nháp (cho nhãn trong raw\\ không có push.json)", elem_id="tk-luotnhap")
        s_nguong = gr.Slider(minimum=thong_ke.NGUONG_SUA_MIN, maximum=thong_ke.NGUONG_SUA_MAX, step=0.5, value=thong_ke.NGUONG_SUA, label="Ngưỡng điểm 'đã sửa' (% IOD)", elem_id="tk-nguong")
        c_task = gr.Checkbox(value=False, label="Mọi task", info="gồm cả practice/check/smoke (mặc định bỏ)", elem_id="tk-tatca")
        c_bo = gr.Checkbox(value=True, label="Chỉ bộ ảnh thí nghiệm", info="theo bo_anh trong config\\nhom_thi_nghiem.json (nếu có)", elem_id="tk-chibo")
        c_ttest = gr.Checkbox(value=False, label="Gồm Ttest", info="Ttest là tập đo một lần của đề tài", elem_id="tk-ttest")
        t_timing = gr.Textbox(value="", label="Thư mục/file bấm giờ thêm (trong thư mục dự án, tuỳ chọn)", elem_id="tk-timing")
    f_goi = gr.File(label="Nạp các gói kết quả của nhóm (ketqua_*.zip hoặc .json; chỉ đọc, không lưu vào dự án)", file_count="multiple", file_types=[".zip", ".json"], type="filepath",
                    elem_id="tk-goi", height=120)
    with gr.Accordion("Nhập tay: nhóm gán tay trực tiếp trong CVAT (không dùng tool)", open=False, elem_id="tk-tay") as acc_tay:
        gr.HTML(tay_note_html(), elem_id="tk-tay-note", apply_default_css=False)
        with gr.Row(elem_id="tk-tay-row"):
            d_nguoi = gr.Dropdown(choices=list(nhap_tay.NGUOI), value=None, label="Người", elem_id="tk-tay-nguoi")
            r_nhom = gr.Radio(choices=[("manual (gán tay)", "manual"), ("assisted (dùng tool)", "assisted")], value="manual", label="Nhóm", elem_id="tk-tay-nhom")
            t_dot = gr.Textbox(value=nhom_mod.doc(ctx.project_root)["bo_anh"], label="Đợt / bộ ảnh (hai nhóm phải dùng cùng tên ảnh)", placeholder="ví dụ NAP_001",
                               info="nhóm assisted: gõ tên lượt đã dựng nháp (thư mục runs\\bo200 thì gõ bo200)", elem_id="tk-tay-dot")
            t_gio = gr.Textbox(value="", label="Thời gian làm", placeholder="1:25:30 · 85:30 · 85 (phút)", elem_id="tk-tay-gio")
            t_ngay = gr.Textbox(value="", label="Ngày làm", placeholder="trống = hôm nay; dd/mm/yyyy", elem_id="tk-tay-ngay")
        f_nhan = gr.File(label="File nhãn xuất từ CVAT (CVAT for images 1.1, không kèm ảnh)", file_count="multiple", file_types=[".xml", ".zip"], type="filepath",
                         elem_id="tk-tay-file", height=110)
        t_ghichu = gr.Textbox(value="", label="Ghi chú (tuỳ chọn; không ghi email, đường dẫn)", max_lines=2, elem_id="tk-tay-ghichu")
        b_tay_add = gr.Button("Add manual entry", variant="primary", elem_id="tk-tay-add")
        tay_msg = gr.HTML(elem_id="tk-tay-msg", apply_default_css=False)
        tay_list = gr.HTML(elem_id="tk-tay-list", apply_default_css=False)
        with gr.Row(elem_id="tk-tay-bo"):
            d_tay_bo = gr.Dropdown(choices=[], value=None, label="Bản nhập tay (gỡ thì chuyển vào outputs\\goi_nhom\\_da_bo, không xoá)", elem_id="tk-tay-chon")
            b_tay_bo = gr.Button("Remove entry", elem_id="tk-tay-remove")
    with gr.Row(elem_id="tk-btns"):
        b_refresh = gr.Button("Refresh", variant="primary", elem_id="tk-refresh")
        b_export = gr.Button("Export CSV + HTML", elem_id="tk-export")
    msg = gr.HTML(elem_id="tk-msg", apply_default_css=False)
    download = gr.DownloadButton("Download thong_ke.html", visible=False, elem_id="tk-download")
    view = gr.HTML(elem_id="tk-view", apply_default_css=False, elem_classes=["tk-root"])
    inputs = [d_nhap, s_nguong, c_task, c_bo, c_ttest, t_timing, f_goi]
    outs = [d_nhap, msg, view]

    def compute(luot_nhap, nguong, tat_ca, chi_bo, ttest, timing, files):
        luot_nhap = clean_args(ctx.runs_root, luot_nhap)
        return thong_ke.tinh(ctx.project_root, luot_nhap, nguong if nguong is not None else thong_ke.NGUONG_SUA, bool(tat_ca), bool(ttest), (timing or "").strip() or None,
                             goi_paths(files), bool(chi_bo))

    def on_refresh(luot_nhap, nguong, tat_ca, chi_bo, ttest, timing, files):
        runs = dot_anh.list_runs(ctx.runs_root)
        luot_nhap = luot_nhap if luot_nhap in runs else ""
        up = gr.update(choices=[("(không)", "")] + [(r, r) for r in runs], value=luot_nhap)
        try:
            st = compute(luot_nhap, nguong, tat_ca, chi_bo, ttest, timing, files)
        except (nap_anh.RunError, bang_mat.BangLoi, toc_do.TocDoLoi, OSError) as ex:
            gr.Warning(str(ex), title="Chưa tính được thống kê")
            return up, msg_html(str(ex), "warn"), ""
        return up, "", f'<div class="tk-root">{thong_ke_html.noi_dung(st)}</div>'

    def on_export(luot_nhap, nguong, tat_ca, chi_bo, ttest, timing, files):
        if ctx.closing:
            return msg_html(nap_anh.CLOSING_MSG, "warn"), gr.update(visible=False)
        with _LOCK:
            try:
                st = compute(luot_nhap, nguong, tat_ca, chi_bo, ttest, timing, files)
                d, fl = thong_ke.xuat(ctx.project_root, st)
            except (nap_anh.RunError, bang_mat.BangLoi, toc_do.TocDoLoi, ValueError, OSError) as ex:
                gr.Warning(str(ex), title="Chưa xuất được")
                return msg_html(str(ex), "warn"), gr.update(visible=False)
        rel = bang_mat.rel(ctx.project_root, d)
        return (msg_html(f"Đã xuất {rel} ({len(fl)} file: thong_ke.html và {len(fl) - 1} bảng CSV). Không có ảnh mặt trong bản xuất.", "ok"),
                gr.update(value=os.path.join(d, "thong_ke.html"), visible=True))

    # ---------- mục Nhập tay (nhóm manual gán thẳng trong CVAT) ----------
    tay_opts = dict(opts, concurrency_id="thongke_tay")

    def tay_ds():
        try:
            rows = nhap_tay.liet_ke(ctx.project_root)
        except OSError:
            rows = []
        return tay_list_html(rows), gr.update(choices=tay_choices(rows), value=None)

    def on_tay_list():
        return tay_ds()

    def on_tay_open(dot):
        bo_anh = nhom_mod.doc(ctx.project_root)["bo_anh"]
        return (gr.update(value=bo_anh) if bo_anh and not (dot or "").strip() else gr.update(),) + tay_ds()

    def on_tay_add(nguoi, nhom, dot, gio, ngay, files, ghi_chu, goi_files):
        if ctx.closing:
            return (msg_html(nap_anh.CLOSING_MSG, "warn"),) + tay_ds()
        notes = []
        try:
            cfg = bang_mat.load_cfg(ctx.project_root)
            nd = nhap_tay.tao_noi_dung(ctx.project_root, cfg, nguoi, nhom, dot, str(gio or ""), nhan_paths(files), ngay=str(ngay or "").strip(),
                                       ghi_chu=ghi_chu, now=datetime.datetime.now().astimezone(), thong_bao=notes)
            r = nhap_tay.them(ctx.project_root, nd, nguon_them=goi_paths(goi_files))
        except (nhap_tay.NhapTayLoi, bang_mat.BangLoi, OSError) as ex:
            gr.Warning(str(ex), title="Chưa thêm được bản nhập tay")
            return (msg_html(str(ex), "warn"),) + tay_ds()
        bd = nd["bat_dau"]
        moi_mat = nd["giay_phien"] / nd["so_mat"]
        text = (f"Đã thêm {r['ten']} vào outputs\\goi_nhom: {nd['nguoi']}, nhóm {nd['nhom']}, đợt {nd['dot']}, ngày làm {bd[8:10]}/{bd[5:7]}/{bd[:4]}, {nd['so_mat']} mặt, "
                f"{nhap_tay.fmt_giay(nd['giay_phien'])} = {nhap_tay.gio_bang_chu(nd['giay_phien'])} ({thong_ke_html.num(moi_mat, 1)} giây/mặt). "
                "Thống kê bên dưới đã tính cả bản này." + ("" if not notes else " " + " ".join(notes)))
        canh = []
        if moi_mat < nhap_tay.GIAY_MOI_MAT_NGHI:                            # '1:30' (1 phút 30 giây) gõ thay cho 1 giờ 30 phút: giây/mặt vô lý, thống kê sẽ lệch hẳn
            canh.append(f"Chỉ {thong_ke_html.num(moi_mat, 1)} giây/mặt: gần như chắc gõ nhầm thời gian (1:30 là 1 phút 30 giây; 1 giờ 30 phút thì gõ 1:30:00 hoặc 90). "
                        "Kiểm lại, sai thì Remove entry rồi thêm lại.")
        cau_hinh = nhom_mod.nhom_cua(nhom_mod.doc(ctx.project_root), nd["nguoi"])
        if cau_hinh and cau_hinh != nd["nhom"]:
            canh.append(f"config\\nhom_thi_nghiem.json ghi {nd['nguoi']} ở nhóm {cau_hinh}, bản này lại là nhóm {nd['nhom']}: kiểm lại, sai thì Remove entry rồi thêm lại.")
        if canh:
            text += " " + " ".join(canh)
            gr.Warning(" ".join(canh), title="Đã thêm, nhưng kiểm lại")
            return (msg_html(text, "warn"),) + tay_ds()
        if nd["nhom"] == "assisted" and not nd.get("co_nhap"):                # đã ghi gói nhưng thiếu nháp: thông báo là cảnh báo, không phải "ok"
            gr.Warning(f"Bản nhập tay assisted của {nd['nguoi']} không có nháp của đợt {nd['dot']}: NME của nháp và tỉ lệ điểm phải sửa sẽ thiếu mặt của người này. "
                       "Đợt phải là tên lượt đã dựng nháp (thư mục runs\\bo200 thì đợt là bo200).", title="Đã thêm nhưng thiếu nháp")
            return (msg_html(text, "warn"),) + tay_ds()
        return (msg_html(text, "ok"),) + tay_ds()

    def on_tay_remove(ten):
        if ctx.closing:
            return (msg_html(nap_anh.CLOSING_MSG, "warn"),) + tay_ds()
        try:
            r = nhap_tay.bo(ctx.project_root, ten)
        except (nhap_tay.NhapTayLoi, OSError) as ex:
            gr.Warning(str(ex), title="Chưa gỡ được")
            return (msg_html(str(ex), "warn"),) + tay_ds()
        return (msg_html(f"Đã gỡ {r['ten']}: chuyển vào outputs\\goi_nhom\\_da_bo (không xoá; thống kê không đọc thư mục đó, muốn tính lại thì chép file về outputs\\goi_nhom).",
                         "ok"),) + tay_ds()

    tay_out = [tay_msg, tay_list, d_tay_bo]
    b_tay_add.click(on_tay_add, [d_nguoi, r_nhom, t_dot, t_gio, t_ngay, f_nhan, t_ghichu, f_goi], tay_out, **tay_opts).then(on_refresh, inputs, outs, **opts)
    b_tay_bo.click(on_tay_remove, [d_tay_bo], tay_out, **tay_opts).then(on_refresh, inputs, outs, **opts)
    acc_tay.expand(on_tay_open, [t_dot], [t_dot, tay_list, d_tay_bo], **tay_opts)

    b_refresh.click(on_refresh, inputs, outs, **opts).then(on_tay_list, None, [tay_list, d_tay_bo], **tay_opts)
    b_export.click(on_export, inputs, [msg, download], **dict(opts, concurrency_id="thongke_xuat"))
    return on_refresh, inputs, outs, opts
