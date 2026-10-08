"""Tab "Thống kê" của trang rà soát M28 (dựng theo mẫu ca_kho.member_tab): chỉ số chất lượng nháp, cờ low_conf, tốc độ gán, số lượng và tiến độ.

Quy ước (giống ca_kho.py):
  * Đầu module KHÔNG nạp gradio (nhận `gr` làm tham số); chỉ thư viện chuẩn và các module tool/ chỉ thư viện chuẩn + numpy nạp lười. Không gọi mạng, không đọc token.
  * Tính KHI CHỌN TAB (tab.select) hoặc bấm Làm mới, không tính lúc mở trang; chỉ ĐỌC runs\\, raw\\, final\\, data\\. Chỉ ghi khi bấm "Xuất CSV + HTML" và chỉ dưới outputs\\thong_ke.
  * Giá trị từ trình duyệt (lượt, người rà, đường dẫn) được kiểm lại ở server: lượt phải là phần tử của danh sách do server tính; đường dẫn bấm giờ phải nằm trong thư mục dự án.
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
            'chỉ dùng nội bộ nhóm; bản HTML xuất không có ảnh, không mã tài xế, không đường dẫn tuyệt đối. '
            '<b>Ttest là tập đo một lần</b>: chỉ bật "Gồm Ttest" đúng buổi đo.</div>')


def reviewers(runs_root):
    """Tên người rà có file triage_<người>.csv ở bất kỳ lượt nào (trừ auto: máy tự quyết, không phải người rà)."""
    out = set()
    for r in dot_anh.list_runs(runs_root):
        for p in glob.glob(os.path.join(glob.escape(os.path.join(runs_root, r, "review")), "triage_*.csv")):
            who = os.path.basename(p)[len("triage_"):-len(".csv")]
            if who and who != bang_mat.AUTO and NGUOI_RE.fullmatch(who):
                out.add(who)
    return sorted(out)


def clean_args(runs_root, luot, nguoi, luot_nhap):
    """Kiểm giá trị từ trình duyệt: lượt phải có trong danh sách server; người rà đúng mẫu tên. Trả (luot|None, nguoi, luot_nhap|None); sai thì RunError."""
    runs = dot_anh.list_runs(runs_root)
    luot = [l for l in (luot or [])]
    bad = [l for l in luot if l not in runs]
    if bad:
        raise nap_anh.RunError(f"Lượt {bad[0]!r} không có trong danh sách lượt: bấm Làm mới.")
    nguoi = [w for w in (nguoi or []) if w]
    for w in nguoi:
        if not NGUOI_RE.fullmatch(w) or w == bang_mat.AUTO:
            raise nap_anh.RunError(f"Tên người rà {w!r} không hợp lệ.")
    if luot_nhap and luot_nhap not in runs:
        raise nap_anh.RunError(f"Lượt chứa nháp {luot_nhap!r} không có trong danh sách lượt: bấm Làm mới.")
    return luot or None, nguoi, luot_nhap or None


def stats_tab(gr, demo, store, ctx):
    """Tab "Thống kê". Trả (hàm làm mới, inputs, outputs, opts) để build_ui nối vào tab.select."""
    opts = dict(show_progress="minimal", api_visibility="private", concurrency_limit=1, concurrency_id="thongke")
    gr.HTML(note_html(), elem_id="tk-note", apply_default_css=False)
    with gr.Row(elem_id="tk-filters"):
        d_luot = gr.Dropdown(choices=[], value=[], multiselect=True, label="Lượt (để trống = tất cả)", elem_id="tk-luot")
        d_nguoi = gr.Dropdown(choices=[], value=[], multiselect=True, label="Người rà (để trống = tất cả; triage_auto không tính)", elem_id="tk-nguoi")
        d_nhap = gr.Dropdown(choices=[("(không)", "")], value="", label="Lượt chứa nháp cho nhãn thí nghiệm (luot_nhap)", elem_id="tk-luotnhap")
        c_ttest = gr.Checkbox(value=False, label="Gồm Ttest", info="Ttest là tập đo một lần của đề tài", elem_id="tk-ttest")
        t_timing = gr.Textbox(value="", label="Thư mục/file bấm giờ thêm (trong thư mục dự án, tuỳ chọn)", elem_id="tk-timing")
    with gr.Row(elem_id="tk-btns"):
        b_refresh = gr.Button("Làm mới", variant="primary", elem_id="tk-refresh")
        b_export = gr.Button("Xuất CSV + HTML", elem_id="tk-export")
    msg = gr.HTML(elem_id="tk-msg", apply_default_css=False)
    download = gr.DownloadButton("Tải thong_ke.html", visible=False, elem_id="tk-download")
    view = gr.HTML(elem_id="tk-view", apply_default_css=False, elem_classes=["tk-root"])
    inputs = [d_luot, d_nguoi, d_nhap, c_ttest, t_timing]
    outs = [d_luot, d_nguoi, d_nhap, msg, view]

    def compute(luot, nguoi, luot_nhap, ttest, timing):
        luot, nguoi, luot_nhap = clean_args(ctx.runs_root, luot, nguoi, luot_nhap)
        return thong_ke.tinh(ctx.project_root, luot, bool(ttest), nguoi, luot_nhap, (), (timing or "").strip() or None)

    def on_refresh(luot, nguoi, luot_nhap, ttest, timing):
        runs = dot_anh.list_runs(ctx.runs_root)
        who = reviewers(ctx.runs_root)
        keep = lambda sel, ok: [x for x in (sel or []) if x in ok]                                           # noqa: E731
        up = (gr.update(choices=runs, value=keep(luot, runs)), gr.update(choices=who, value=keep(nguoi, who)),
              gr.update(choices=[("(không)", "")] + [(r, r) for r in runs], value=luot_nhap if luot_nhap in runs else ""))
        try:
            st, _bang = compute(keep(luot, runs), keep(nguoi, who), luot_nhap if luot_nhap in runs else "", ttest, timing)
        except (nap_anh.RunError, bang_mat.BangLoi, toc_do.TocDoLoi, OSError) as ex:
            gr.Warning(str(ex), title="Chưa tính được thống kê")
            return up + (msg_html(str(ex), "warn"), "")
        return up + ("", f'<div class="tk-root">{thong_ke_html.noi_dung(st)}</div>')

    def on_export(luot, nguoi, luot_nhap, ttest, timing):
        if ctx.closing:
            return msg_html(nap_anh.CLOSING_MSG, "warn"), gr.update(visible=False)
        with _LOCK:
            try:
                st, bang = compute(luot, nguoi, luot_nhap, ttest, timing)
                d, files = thong_ke.xuat(ctx.project_root, st, bang=bang)
            except (nap_anh.RunError, bang_mat.BangLoi, toc_do.TocDoLoi, ValueError, OSError) as ex:
                gr.Warning(str(ex), title="Chưa xuất được")
                return msg_html(str(ex), "warn"), gr.update(visible=False)
        rel = bang_mat.rel(ctx.project_root, d)
        return (msg_html(f"Đã xuất {rel} ({len(files)} file: thong_ke.html, nme_nhap.csv và {len(files) - 2} bảng CSV). Không có ảnh mặt trong bản xuất.", "ok"),
                gr.update(value=os.path.join(d, "thong_ke.html"), visible=True))

    b_refresh.click(on_refresh, inputs, outs, **opts)
    b_export.click(on_export, inputs, [msg, download], **dict(opts, concurrency_id="thongke_xuat"))
    return on_refresh, inputs, outs, opts
