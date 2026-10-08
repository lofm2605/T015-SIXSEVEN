"""Tab "Thống kê" của trang rà soát M28 (dựng theo mẫu ca_kho.member_tab): CHỈ BA CHỈ SỐ của thí nghiệm hai nhóm độc lập (QĐ-006): NME của nháp so với nhãn manual,
tỉ lệ điểm phải sửa, so sánh thời gian manual với assisted. Tab "Lọc dữ liệu" (loc_ui.py) là việc khác và giữ nguyên.

Quy ước (giống ca_kho.py):
  * Đầu module KHÔNG nạp gradio (nhận `gr` làm tham số); chỉ thư viện chuẩn và các module tool/ chỉ thư viện chuẩn + numpy nạp lười. Không gọi mạng, không đọc token.
  * Tính KHI CHỌN TAB (tab.select) hoặc bấm Làm mới, không tính lúc mở trang; chỉ ĐỌC runs\\, raw\\, data\\, outputs\\. Chỉ ghi khi bấm "Xuất CSV + HTML" và chỉ dưới outputs\\thong_ke.
  * Giá trị từ trình duyệt (lượt chứa nháp, đường dẫn bấm giờ) được kiểm lại ở server: lượt phải là phần tử của danh sách do server tính; đường dẫn bấm giờ phải nằm trong thư mục dự án;
    gói kết quả tải lên (nút "Nạp các gói kết quả của nhóm") được đọc từ file tạm của Gradio, kiểm sha256 và cấu trúc trước khi tin, không lưu vào dự án.
  * Handler: api_visibility="private", concurrency_id riêng, không chặn tab khác; lỗi -> gr.Warning và thông báo tiếng Việt, không traceback lên trang.
  * Trang không hiện ảnh mặt (chỉ số); bản xuất tĩnh cũng không có ảnh mặt, không mã tài xế.
"""
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
from m28core import bang_mat, toc_do  # noqa: E402

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
        raise nap_anh.RunError(f"Lượt chứa nháp {luot_nhap!r} không có trong danh sách lượt: bấm Làm mới.")
    return luot_nhap or None


def goi_paths(files):
    """Đường dẫn các gói tải lên (gr.File trả list đường dẫn hoặc đối tượng có .name)."""
    out = []
    for f in files or []:
        p = f if isinstance(f, str) else getattr(f, "name", None)
        if p and os.path.isfile(p) and p.lower().endswith((".zip", ".json")):
            out.append(p)
    return out


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
                    elem_id="tk-goi")
    with gr.Row(elem_id="tk-btns"):
        b_refresh = gr.Button("Làm mới", variant="primary", elem_id="tk-refresh")
        b_export = gr.Button("Xuất CSV + HTML", elem_id="tk-export")
    msg = gr.HTML(elem_id="tk-msg", apply_default_css=False)
    download = gr.DownloadButton("Tải thong_ke.html", visible=False, elem_id="tk-download")
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

    b_refresh.click(on_refresh, inputs, outs, **opts)
    b_export.click(on_export, inputs, [msg, download], **dict(opts, concurrency_id="thongke_xuat"))
    return on_refresh, inputs, outs, opts
