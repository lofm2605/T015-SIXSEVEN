"""Tab "Đồng hồ" của trang rà soát: bấm giờ gán nhãn theo PHIÊN (logic ở dong_ho.py; không import gradio ở đầu module).

Bốn nút chính: Bắt đầu, Tạm dừng/Tiếp tục, Hủy (hộp xác nhận gõ HUY), Xong (lưu & xuất gói kết quả). "Xong mặt này → mặt tiếp" và "Hoàn tác" là tuỳ chọn cho ai
muốn đo từng mặt. mm:ss chạy mượt bằng JS phía trình duyệt (không gọi server mỗi giây); nguồn sự thật là đồng hồ phía server, `gr.Timer(15)` chỉ đồng bộ lại.
Nối với tab "Nạp ảnh": nạp xong một đợt thì tab này gợi ý "Bắt đầu đồng hồ cho đợt này?" (không tự chạy ngầm), hoặc bật ô "Tự bắt đầu khi nạp ảnh".
Không ảnh mặt, không mạng, không token, không phát file nào (không thêm allowed_paths).
"""
import html
import json
import os
import re
import sys
import uuid

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)
import cai_dat  # noqa: E402
import ca_kho  # noqa: E402
import dong_ho  # noqa: E402
import nap_anh  # noqa: E402
from dong_ho import DongHo, DongHoLoi, fmt_giay  # noqa: E402
from m28core import nhom as nhom_mod  # noqa: E402

COND_CHOICES = [("Gán tay hoàn toàn (manual)", "manual"), ("Dùng tool, sửa nháp (assisted)", "assisted")]
COND_VI = {"manual": "manual (gán tay hoàn toàn)", "assisted": "assisted (dùng tool, sửa nháp)"}
TRANG_THAI_VI = {"chay": "▶ Đang chạy", "tam_dung": "⏸ Tạm dừng", "du_mat": "■ Đủ mặt, chờ lưu", "chua": "• Chưa có phiên"}
HAN_CHE = ("Thiết kế hai nhóm độc lập: tốc độ từng người khác nhau nên lẫn vào kết quả (nên có một đợt khởi động chung hoặc chia nhóm cân tốc độ). "
           "Đồng hồ chỉ đo cả phiên (từ lúc nạp ảnh đến lúc Xong); giây/mặt là ước lượng chia đều trừ khi bạn bấm từng mặt.")
OPTS = dict(show_progress="hidden", api_visibility="private", concurrency_limit=1, concurrency_id="dongho")

CSS = """
/* ---------- tab Đồng hồ (màu lấy từ biến theme) ---------- */
#tab-dongho { padding: 8px 0 0 !important; max-width: 760px; margin: 0 auto; width: 100%; gap: 10px; }
#dh-msg, #dh-warn, #dh-sug, #dh-faces, #dh-recent, #dh-clock-wrap, #dh-han-che { padding: 0 !important; min-height: 0 !important; }
#dh-sug:not(:has(.html-container > div > *)), #dh-warn:not(:has(.html-container > div > *)), #dh-msg:not(:has(.html-container > div > *)),
#dh-faces:not(:has(.html-container > div > *)) { display: none; }
.dh-clock-box { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 14px 10px; border-radius: 14px;
  background: var(--block-background-fill); border: 1px solid var(--border-color-primary); text-align: center; }
.dh-clock { font-size: clamp(44px, 14vw, 84px); font-weight: 800; line-height: 1.05; color: var(--body-text-color); font-variant-numeric: tabular-nums;
  letter-spacing: .02em; }
.dh-clock.dh-idle { opacity: .55; }
.dh-sub { font-size: 14px; color: var(--body-text-color-subdued); font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.dh-state { display: inline-block; padding: 2px 12px; border-radius: 999px; font-size: 14px; font-weight: 800;
  border: 1px solid var(--border-color-primary); color: var(--body-text-color); }
.dh-state.s-chay { background: color-mix(in srgb, #16a34a 18%, transparent); border-color: #16a34a; }
.dh-state.s-tam_dung { background: color-mix(in srgb, #d97706 20%, transparent); border-color: #d97706; }
.dh-state.s-du_mat { background: color-mix(in srgb, #2563eb 18%, transparent); border-color: #2563eb; }
.dh-warn-item { display: flex; gap: 8px; align-items: flex-start; padding: 8px 10px; border-radius: 8px; font-size: 14px; line-height: 1.45;
  background: color-mix(in srgb, #d97706 14%, transparent); border-left: 5px solid #d97706; color: var(--body-text-color); margin-bottom: 6px; }
.dh-warn-item.da-xu-ly { background: transparent; border-left-color: #16a34a; opacity: .8; }
.dh-table { width: 100%; border-collapse: collapse; font-size: 13.5px; font-variant-numeric: tabular-nums; }
.dh-table th, .dh-table td { padding: 4px 8px; text-align: left; border-bottom: 1px solid var(--border-color-primary); overflow-wrap: anywhere; }
.dh-table th { font-weight: 800; color: var(--body-text-color-subdued); }
.dh-h { font-size: 15px; font-weight: 800; margin: 6px 0 4px; color: var(--body-text-color); }
.dh-ok { padding: 10px 12px; border-radius: 10px; border-left: 5px solid #16a34a; background: color-mix(in srgb, #16a34a 12%, transparent);
  color: var(--body-text-color); font-size: 14px; line-height: 1.5; overflow-wrap: anywhere; }
.dh-sug { padding: 10px 12px; border-radius: 10px; border-left: 5px solid #2563eb; background: color-mix(in srgb, #2563eb 12%, transparent);
  color: var(--body-text-color); font-size: 14px; }
#dh-btns, #dh-btns2, #dh-fix-row { gap: 8px; flex-wrap: wrap; }
#dh-btns button, #dh-btns2 button, #dh-fix-row button { min-width: 0 !important; flex: 1 1 120px !important; min-height: 44px; font-weight: 800; }
#dh-start, #dh-done { font-weight: 800; }
#dh-face { min-height: 56px !important; font-size: 17px; }
#dh-cancel-ok { background: #dc2626 !important; border-color: #b91c1c !important; color: #fff !important; }
.dh-chip-est { font-size: 12px; padding: 1px 8px; border-radius: 999px; border: 1px dashed var(--border-color-primary); }
@media (max-width: 600px) { #dh-btns button, #dh-btns2 button, #dh-fix-row button { flex: 1 1 100% !important; } }
"""

JS_BODY = r"""
  // ---- Tab "Đồng hồ": mm:ss chạy mượt ở trình duyệt, KHÔNG gọi server mỗi giây. HTML mang data-* (giây server lúc dựng, đang chạy hay không, mã lần dựng);
  //      thấy mã mới thì lấy mốc performance.now() (đồng hồ đơn điệu của trình duyệt, không dùng giờ hệ thống nên không lệch khi giờ máy đổi), rồi hiển thị giây_server + (now - mốc)/1000. ----
  if (!window.__m28Dh) {
    window.__m28Dh = { ver: null, t0: 0, g: 0, gp: 0 };
    const p2 = (n) => String(n).padStart(2, '0');
    const fmt = (s) => {
      s = Math.max(0, Math.round(s));
      const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
      return h ? h + ':' + p2(m) + ':' + p2(x) : p2(m) + ':' + p2(x);
    };
    setInterval(() => {
      const el = document.getElementById('dh-clock');
      if (!el) { return; }
      const st = window.__m28Dh;
      if (el.dataset.ver !== st.ver) {
        st.ver = el.dataset.ver; st.t0 = performance.now();
        st.g = parseFloat(el.dataset.giay) || 0; st.gp = parseFloat(el.dataset.giayPhien) || 0;
      }
      if (el.dataset.chay !== '1') { return; }
      const dt = (performance.now() - st.t0) / 1000;
      const a = fmt(st.g + dt);
      if (el.textContent !== a) { el.textContent = a; }
      const tp = document.getElementById('dh-total');
      if (tp) { const b = fmt(st.gp + dt); if (tp.textContent !== b) { tp.textContent = b; } }
    }, 250);
  }
"""


def e(x):
    return html.escape("" if x is None else str(x), quote=True)


def msg_html(text, level="info"):
    return f'<div class="m28-msg m-{e(level)}" role="status">{e(text)}</div>' if text else ""


# ---------- HTML thuần (test không cần gradio) ----------
def clock_html(v, ver=None):
    ver = ver or uuid.uuid4().hex[:8]
    if not v.get("co_phien"):
        return ('<div class="dh-clock-box"><div id="dh-clock" class="dh-clock dh-idle" data-ver="%s" data-giay="0" data-giay-phien="0" data-chay="0">00:00</div>'
                '<span class="dh-state">%s</span><div class="dh-sub">Chọn người, điều kiện rồi bấm Bắt đầu (hoặc bấm Bắt đầu đồng hồ khi vừa nạp ảnh xong).</div></div>' % (ver, TRANG_THAI_VI["chua"]))
    st = v["trang_thai"]
    theo_mat = v["theo_mat"]
    big = fmt_giay(v["giay_hien_thi"])
    if theo_mat:
        mat_line = f"Mặt <b>{e(v['face_id'])}</b> · {len(v['mat']) + (0 if v['du_mat'] else 1)}/{v['n_mat']}" if not v["du_mat"] else f"Đủ {v['n_mat']} mặt: bấm Xong (lưu)."
        total = f'Tổng phiên <span id="dh-total">{fmt_giay(v["giay_phien"])}</span>'
    else:
        mat_line = f'Cả phiên · khai <b>{v["n_mat"]}</b> mặt <span class="dh-chip-est" title="giây/mặt = giây phiên chia đều số mặt">ước lượng chia đều</span>'
        total = f'<span id="dh-total" hidden>{fmt_giay(v["giay_phien"])}</span>Bấm <b>Xong mặt này</b> nếu muốn đo từng mặt'
    tp = f"{v['so_lan_tam_dung']} lần tạm dừng"
    if v.get("sua_tay"):
        tp += " · đã sửa tay thời gian"
    return ('<div class="dh-clock-box"><div id="dh-clock" class="dh-clock" data-ver="%s" data-giay="%.3f" data-giay-phien="%.3f" data-chay="%d" role="timer" aria-live="off">%s</div>'
            '<span class="dh-state s-%s">%s</span><div class="dh-sub">%s</div><div class="dh-sub">%s · %s</div>'
            '<div class="dh-sub">%s · %s · %s</div></div>'
            % (ver, v["giay_hien_thi"], v["giay_phien"], 1 if st == "chay" else 0, big, e(st), e(TRANG_THAI_VI[st]), mat_line, total, e(tp),
               e(v["nguoi"]), e(COND_VI.get(v["dieu_kien"], v["dieu_kien"])), e(v.get("task") or v.get("dot") or "")))


def warn_html(v):
    if not v.get("co_phien"):
        return ""
    out = []
    for c in v["canh_bao"]:
        if c["xu_ly"]:
            out.append(f'<div class="dh-warn-item da-xu-ly" role="status"><span>✓</span><span>{e(c["text"])} (đã xử lý)</span></div>')
        else:
            out.append(f'<div class="dh-warn-item" role="alert"><span>⚠</span><span>{e(c["text"])}</span></div>')
    return "".join(out)


def faces_html(v):
    if not v.get("co_phien") or not v["mat"]:
        return ""
    rows = "".join(f'<tr><td>{m["seq"]}</td><td>{e(m["face_id"])}</td><td>{fmt_giay(m["giay"])}</td><td>{m["tam_dung"] or ""}</td><td>{"✎" if m.get("sua_tay") else ""}</td>'
                   f'<td>{e(m["ghi_chu"])}</td></tr>' for m in v["mat"])
    return ('<div class="dh-h">Các mặt đã khép trong phiên</div><table class="dh-table"><thead><tr><th>seq</th><th>mặt</th><th>thời gian</th><th>tạm dừng</th><th>sửa</th>'
            f'<th>ghi chú</th></tr></thead><tbody>{rows}</tbody></table>')


def recent_html(rows, nguoi):
    if not rows:
        return f'<div class="dh-h">Đã lưu gần đây ({e(nguoi)})</div><div class="dh-sub">Chưa có phiên nào được lưu trong outputs/timing/timing_{e(nguoi)}.csv.</div>'
    tr = "".join(f'<tr><td>{e(r["date"])}</td><td>{e(r["task"])}</td><td>{e(r["khoi"])}</td><td>{r["n_mat"]}</td><td>{fmt_giay(r["giay_tong"])}</td>'
                 f'<td>{"" if r["giay_moi_mat"] is None else str(r["giay_moi_mat"]).replace(".", ",") + " giây"}{" ≈" if r["uoc_luong"] else ""}</td></tr>' for r in rows)
    return (f'<div class="dh-h">Đã lưu gần đây ({e(nguoi)})</div><table class="dh-table"><thead><tr><th>ngày</th><th>task</th><th>khối</th><th>số mặt</th><th>giây tổng</th>'
            f'<th>mỗi mặt (không tính khởi động)</th></tr></thead><tbody>{tr}</tbody></table>')


def summary_html(r, nguoi):
    """Tóm tắt sau khi bấm Xong (lưu): số mặt, số mặt tính giờ, tổng, giây/mặt, đường dẫn tương đối (không đường dẫn tuyệt đối)."""
    t = r["tom_tat"]
    est = " (ước lượng chia đều)" if t["uoc_luong"] else ""
    lines = [f'<b>Đã lưu phiên của {e(nguoi)}.</b> {t["n_mat"]} mặt ({t["n_tinh_gio"]} mặt tính giờ), tổng {fmt_giay(t["giay_tong"])}, '
             f'{"" if t["giay_moi_mat"] is None else str(t["giay_moi_mat"]).replace(".", ",") + " giây/mặt"}{est}; {t["so_lan_tam_dung"]} lần tạm dừng.',
             f'Dòng bấm giờ: <code>{e(r["csv"])}</code>',
             f'<b>Gói kết quả gửi nhóm trưởng:</b> <code>{e(r["goi"]["zip"])}</code> (kèm <code>{e(os.path.basename(r["goi"]["json"]))}</code> đọc được)']
    if t.get("co_nhan"):
        lines.append(f'Gói có nhãn cuối của {t["n_ket_qua"]} mặt (từ <code>{e(t.get("nhan_file", ""))}</code>)' + (", kèm nháp và điểm đã sửa" if t.get("co_nhap") else "") + ".")
    if r.get("canh_bao"):
        lines.append("Cảnh báo đã ghi kèm: " + e(", ".join(r["canh_bao"])))
    lines += [e(x) for x in r.get("thong_bao", [])]
    return '<div class="dh-ok" role="status">' + "<br>".join(lines) + "</div>"


def suggestion_html(run):
    return (f'<div class="dh-sug" role="status"><b>Vừa nạp xong đợt {e(run)}.</b> Bắt đầu đồng hồ cho đợt này? '
            "(Đồng hồ không tự chạy ngầm: bấm nút bên dưới, hoặc bỏ qua.)</div>")


def close_note(ctx):
    """Dòng thêm vào hộp xác nhận Đóng trang: có đồng hồ đang chạy thì báo sẽ tự tạm dừng. Rỗng nếu không."""
    try:
        ai = get_dh(ctx).dang_chay_ai()
    except Exception:
        return ""
    if not ai:
        return ""
    return (f'<div class="nap-box nap-warn" role="alert">Đồng hồ của <b>{e(", ".join(ai))}</b> đang chạy: đóng trang sẽ <b>tự tạm dừng</b> đồng hồ '
            "(mở lại trang và tab Đồng hồ để Tiếp tục hoặc Xong).</div>")


# ---------- dùng chung với review_app ----------
def get_dh(ctx):
    """DongHo của thư mục dự án (tạo lười, giữ trong ctx)."""
    d = getattr(ctx, "dong_ho", None)
    if d is None or d.root != os.path.abspath(ctx.project_root):
        d = DongHo(ctx.project_root)
        ctx.dong_ho = d
    return d


def tu_tam_dung(ctx):
    """Gọi khi đóng trang / Ctrl+C: tự tạm dừng mọi đồng hồ đang chạy, đặt cờ đóng, in một dòng ra terminal cho mỗi người. Trả danh sách (người, giờ)."""
    try:
        d = get_dh(ctx)
        got = d.tu_tam_dung_tat_ca()
        d.closing = True
    except Exception:
        return []
    for nguoi, gio in got:
        print(f"Đồng hồ của {nguoi} đã tạm dừng lúc {gio}: mở lại trang và tab Đồng hồ để Tiếp tục hoặc Xong (lưu).", flush=True)
    return got


def default_person(ctx):
    for cand in (ctx.reviewer, cai_dat.get().next_reviewer(ctx.reviewer)):
        if cand in dong_ho.NGUOI_OK:
            return cand
    return None


def so_mat_cua_luot(run_dir):
    """Số mặt của một lượt (đọc map50/mp50.json), hoặc None."""
    try:
        with open(os.path.join(run_dir, "map50", "mp50.json"), encoding="utf-8") as f:
            n = len(json.load(f))
        return n if n > 0 else None
    except (OSError, ValueError, TypeError):
        return None


def auto_start(gr, ctx, run, n_mat=None):
    """Gọi từ tab Nạp ảnh ngay khi bấm Nạp (nếu ô 'Tự bắt đầu đồng hồ khi nạp ảnh' đang bật). Không làm gì khi chưa bật. Trả thông báo hoặc None."""
    cfg = getattr(ctx, "dh_auto", None)
    if not cfg or ctx.closing:
        return None
    try:
        d = get_dh(ctx)
        v = d.bat_dau(cfg["nguoi"], cfg["dieu_kien"], dot=run, n_mat=n_mat or dong_ho.N_MAT_MAC_DINH, bo_anh=run, rev=0)
        ctx.dh_started = getattr(ctx, "dh_started", set()) | {run}
        text = f"Đã bắt đầu đồng hồ cho {cfg['nguoi']} (đợt {run}); xem tab Đồng hồ."
        if gr is not None:
            gr.Info(text)
        return text
    except DongHoLoi as ex:
        text = f"Chưa tự bắt đầu được đồng hồ: {ex}"
        if gr is not None:
            gr.Warning(text, title="Đồng hồ")
        return text


# ---------- tab ----------
def dong_ho_tab(gr, demo, store, ctx):
    """Dựng tab. Trả (hàm làm mới, inputs, outputs, opts) để build_ui nối vào tab.select."""
    d = get_dh(ctx)
    cfg_nhom = nhom_mod.doc(ctx.project_root) if ctx.project_root else nhom_mod.doc(".")
    dot_mac_dinh = "" if store is None else os.path.basename(os.path.normpath(store.run_dir))
    if dot_mac_dinh.startswith("_"):
        dot_mac_dinh = ""
    nguoi0 = default_person(ctx)
    cond0 = nhom_mod.nhom_cua(cfg_nhom, nguoi0) if nguoi0 else None
    n_mac_dinh = (store.progress()["total"] if store is not None else None) or dong_ho.N_MAT_MAC_DINH

    gr.HTML(f'<div class="nap-box nap-warn"><b>Đồng hồ đo cả phiên</b> từ lúc nạp ảnh đến lúc bấm <b>Xong</b>; không bấm Xong thì không có số liệu. {e(HAN_CHE)}</div>',
            elem_id="dh-han-che", apply_default_css=False)
    sug = gr.HTML(elem_id="dh-sug", apply_default_css=False)
    with gr.Row():
        b_sug = gr.Button("Bắt đầu đồng hồ cho đợt này", variant="primary", elem_id="dh-sug-go", visible=False)
        b_sug_no = gr.Button("Bỏ qua gợi ý", elem_id="dh-sug-no", visible=False)
    with gr.Row():
        person = gr.Dropdown(choices=list(dong_ho.NGUOI_OK), value=nguoi0, label="Người (P1–P5)", elem_id="dh-person", scale=1, min_width=120)
        cond = gr.Radio(choices=COND_CHOICES, value=cond0, label="Nhóm (điều kiện)", elem_id="dh-cond", scale=3)
    with gr.Row():
        dot = gr.Textbox(label="Đợt (tên lượt, ví dụ NAP_001)", value=dot_mac_dinh, max_lines=1, elem_id="dh-dot", scale=2)
        task = gr.Textbox(label="Task CVAT (trống = demo-<đợt>)", max_lines=1, elem_id="dh-task", scale=2)
        job = gr.Textbox(label="Job (số, không bắt buộc)", max_lines=1, elem_id="dh-job", scale=1, min_width=90)
    with gr.Row():
        khoi = gr.Textbox(label="Khối (trống = lấy từ tên đợt)", max_lines=1, elem_id="dh-khoi", scale=2)
        n_mat = gr.Number(label="Số mặt của đợt", value=n_mac_dinh, precision=0, elem_id="dh-nmat", scale=1, min_width=110)       # giới hạn kiểm ở server (thông báo tiếng Việt)
        seq = gr.Textbox(label="Seq bắt đầu (trống = tiếp theo)", value="", max_lines=1, elem_id="dh-seq", scale=1, min_width=130)
    note = gr.Textbox(label="Ghi chú phiên (không bắt buộc, không ghi đường dẫn hay email)", max_lines=1, max_length=200, elem_id="dh-note-tb")
    auto_cb = gr.Checkbox(value=False, label="Tự bắt đầu đồng hồ khi bấm Nạp ảnh (tab Nạp ảnh)", elem_id="dh-auto")
    clock = gr.HTML(elem_id="dh-clock-wrap", apply_default_css=False)
    warn = gr.HTML(elem_id="dh-warn", apply_default_css=False)
    with gr.Row(visible=False, elem_id="dh-fix-row") as fix_row:
        fix_tb = gr.Textbox(label="Thời gian thật (mm:ss hoặc h:mm:ss)", max_lines=1, elem_id="dh-fix-tb", scale=2, min_width=160)
        b_fix = gr.Button("Sửa thời gian", elem_id="dh-fix")
        b_keep = gr.Button("Giữ nguyên", elem_id="dh-keep")
        b_tru = gr.Button("Trừ khoảng tắt trang (coi như tạm dừng)", elem_id="dh-tru", visible=False)
    with gr.Row(elem_id="dh-btns"):
        b_start = gr.Button("Bắt đầu", variant="primary", elem_id="dh-start")
        b_pause = gr.Button("Tạm dừng", elem_id="dh-pause", interactive=False)
        b_done = gr.Button("Xong (lưu & xuất)", variant="primary", elem_id="dh-done", interactive=False)
        b_cancel = gr.Button("Hủy phiên…", variant="stop", elem_id="dh-cancel", interactive=False)
    face_note = gr.Textbox(label="Ghi chú mặt này (tuỳ chọn, gửi kèm khi bấm Xong mặt)", max_lines=1, max_length=200, elem_id="dh-face-note")
    with gr.Row(elem_id="dh-btns2"):
        b_face = gr.Button("Xong mặt này → mặt tiếp (tuỳ chọn)", elem_id="dh-face", interactive=False)
        b_undo = gr.Button("Hoàn tác mặt vừa xong", elem_id="dh-undo", interactive=False)
    with gr.Row():
        tinh_mat = gr.Checkbox(value=True, label="Khi Xong: tính mặt đang làm là đã xong (bỏ tích = bỏ mặt đang làm)", elem_id="dh-tinh-mat")
        so_mat_xong = gr.Textbox(label="Số mặt đã xử lý (khi Xong; trống = như đã khai)", value="", max_lines=1, elem_id="dh-somat-xong", min_width=160)
    nhan_dd = gr.Dropdown(choices=[("Tự chọn file mới nhất của task", "auto")], value="auto", label="File nhãn lấy vào gói (raw/)", elem_id="dh-nhan")
    msg = gr.HTML(elem_id="dh-msg", apply_default_css=False)
    faces = gr.HTML(elem_id="dh-faces", apply_default_css=False)
    recent = gr.HTML(elem_id="dh-recent", apply_default_css=False)
    with gr.Group():
        gr.Markdown("### Gói kết quả đã lưu (gửi nhóm trưởng)")
        goi_dd = gr.Dropdown(choices=[], value=None, label="Gói của người đang chọn (outputs/ket_qua)", elem_id="dh-goi")
        b_reexp = gr.Button("Xuất lại gói với nhãn mới (sau khi collect)", elem_id="dh-reexport")
    b_hong = gr.Button("Bỏ trạng thái hỏng (đổi tên file, không xoá)", elem_id="dh-hong", visible=False)
    rev_st = gr.State(0)
    huy_st = gr.State("")
    timer = gr.Timer(15)
    with gr.Column(visible=False, elem_id="dh-cancel-confirm", elem_classes=["m28-modal"]) as modal:
        with gr.Column(elem_classes=["m28-modal-box"]):
            modal_body = gr.HTML(elem_id="dh-cancel-body", apply_default_css=False)
            huy_tb = gr.Textbox(label="Gõ HUY để xác nhận (không phân biệt hoa thường)", max_lines=1, elem_id="dh-cancel-text")
            with gr.Row(elem_classes=["m28-modal-btns"]):
                b_huy_ok = gr.Button("Hủy phiên (không lưu)", variant="stop", elem_id="dh-cancel-ok")
                b_huy_no = gr.Button("Quay lại", elem_id="dh-cancel-cancel")

    COMP = dict(clock=clock, warn=warn, faces=faces, recent=recent, msg=msg, sug=sug, b_sug=b_sug, b_sug_no=b_sug_no, b_start=b_start, b_pause=b_pause, b_done=b_done,
                b_cancel=b_cancel, b_face=b_face, b_undo=b_undo, fix_row=fix_row, b_tru=b_tru, b_hong=b_hong, person=person, cond=cond, dot=dot, task=task, job=job,
                khoi=khoi, n_mat=n_mat, seq=seq, note=note, auto_cb=auto_cb, rev=rev_st, nhan=nhan_dd, goi=goi_dd, modal=modal, modal_body=modal_body, huy_tb=huy_tb,
                huy_st=huy_st)
    ORDER = list(COMP)
    OUTS = [COMP[k] for k in ORDER]

    def pack(**kw):
        return tuple(kw.get(k, gr.skip()) for k in ORDER)

    # ---------- dựng cập nhật ----------
    def suggestion(v, person_v):
        """(html, hiện nút) của gợi ý 'Bắt đầu đồng hồ cho đợt này'."""
        snap = ctx.job.snapshot()
        run = snap.get("run")
        if (v.get("co_phien") or snap.get("state") != "xong" or not run or run in getattr(ctx, "dh_started", set())
                or run in getattr(ctx, "dh_dismissed", set()) or ctx.closing):
            return "", False
        return suggestion_html(run), True

    def nhan_choices(person_v):
        names = d.ung_vien_nhan(person_v) if person_v in dong_ho.NGUOI_OK else []
        return [("Tự chọn file mới nhất của task", "auto")] + [(n, n) for n in names]

    def goi_choices(person_v):
        if person_v not in dong_ho.NGUOI_OK:
            return []
        return [(f"{t} · {n.get('nhom')} · {n.get('so_mat')} mặt", t) for t, n in d.goi_da_luu(person_v)]

    def view_updates(person_v, msg_text="", level="info", html_msg=None, with_inputs=True, keep_choices=False):
        if person_v not in dong_ho.NGUOI_OK:
            v = dict(co_phien=False, nguoi=person_v, rev=0, hong=False, loi="")
        else:
            v = d.xem(person_v)
        co, st = v.get("co_phien", False), v.get("trang_thai")
        sug_text, sug_show = suggestion(v, person_v)
        warns = [c for c in v.get("canh_bao", []) if not c["xu_ly"]]
        has_tru = any(c["ma"] == "khoang_tat" for c in warns)
        up = dict(clock=clock_html(v), warn=warn_html(v), faces=faces_html(v), recent=recent_html(d.gan_day(person_v), person_v) if person_v in dong_ho.NGUOI_OK else "",
                  sug=sug_text, b_sug=gr.update(visible=sug_show), b_sug_no=gr.update(visible=sug_show),
                  b_start=gr.update(interactive=not co and not v.get("hong") and not ctx.closing),
                  b_pause=gr.update(interactive=co and st in ("chay", "tam_dung"), value="Tiếp tục" if st == "tam_dung" else "Tạm dừng",
                                    variant="primary" if st == "tam_dung" else "secondary"),
                  b_done=gr.update(interactive=co), b_cancel=gr.update(interactive=co),
                  b_face=gr.update(interactive=co and st == "chay"), b_undo=gr.update(interactive=co and bool(v.get("mat"))),
                  fix_row=gr.update(visible=bool(warns)), b_tru=gr.update(visible=has_tru), b_hong=gr.update(visible=bool(v.get("hong"))),
                  rev=v.get("rev", 0))
        if msg_text or html_msg:
            up["msg"] = html_msg if html_msg is not None else msg_html(msg_text, level)
        elif v.get("loi"):
            up["msg"] = msg_html(v["loi"], "warn")
        if with_inputs:
            lock = gr.update(interactive=not co)
            up.update(person=gr.update(interactive=not co), cond=lock, dot=lock, task=lock, job=lock, khoi=lock, n_mat=lock, seq=lock, note=lock)
        if not keep_choices:
            up["nhan"] = gr.update(choices=nhan_choices(person_v))
            up["goi"] = gr.update(choices=goi_choices(person_v))
        return up

    def refresh(person_v, rev_v=None):
        return pack(**view_updates(person_v, keep_choices=False))

    def guard(person_v):
        if ctx.closing:
            return nap_anh.CLOSING_MSG
        if ctx.layout_error:
            return ctx.layout_error
        if person_v not in dong_ho.NGUOI_OK:
            return "Chọn người P1 đến P5 trước."
        return None

    def run_op(person_v, fn, ok_text="", extra=None):
        err = guard(person_v)
        if err:
            gr.Warning(err, title="Đồng hồ")
            return pack(**view_updates(person_v, err, "warn"))
        try:
            res = fn()
        except DongHoLoi as ex:
            gr.Warning(str(ex), title="Đồng hồ")
            up = view_updates(person_v, str(ex), "warn")
            return pack(**up)
        up = view_updates(person_v, ok_text, "ok")
        if extra:
            up.update(extra(res))
        return pack(**up)

    # ---------- sự kiện ----------
    def on_person(person_v):
        up = view_updates(person_v, keep_choices=False)
        g = nhom_mod.nhom_cua(nhom_mod.doc(ctx.project_root), person_v) if person_v in dong_ho.NGUOI_OK else None
        if g and not (person_v in dong_ho.NGUOI_OK and d.xem(person_v).get("co_phien")):
            up["cond"] = gr.update(value=g, interactive=True)
        return pack(**up)

    def on_tick(person_v):
        if ctx.closing or person_v not in dong_ho.NGUOI_OK:
            return pack()
        try:
            d.nhip(person_v)
        except Exception:
            pass
        up = view_updates(person_v, with_inputs=True, keep_choices=True)
        return pack(**up)

    def val_int(x, what="Giá trị"):
        """Ô số: trống = None; không phải số nguyên thì DongHoLoi (thông báo tiếng Việt, không traceback)."""
        t = str(x if x is not None else "").strip()
        if not t:
            return None
        try:
            f = float(t.replace(",", "."))
        except ValueError:
            raise DongHoLoi(f"{what} phải là số nguyên.")
        if f != int(f):
            raise DongHoLoi(f"{what} phải là số nguyên.")
        return int(f)

    def on_start(person_v, cond_v, dot_v, task_v, job_v, khoi_v, n_v, seq_v, note_v, rev_v):
        return run_op(person_v, lambda: d.bat_dau(person_v, cond_v, dot=dot_v, task=task_v, job=job_v, khoi=khoi_v, n_mat=(dong_ho.N_MAT_MAC_DINH if val_int(n_v, "Số mặt") is None else val_int(n_v, "Số mặt")),
                                                  seq_dau=val_int(seq_v, "Seq bắt đầu"), ghi_chu=note_v, rev=rev_v or 0), "Đã bắt đầu đồng hồ.")

    def on_pause(person_v, rev_v):
        def fn():
            v = d.xem(person_v)
            return d.tiep_tuc(person_v, rev_v) if v.get("trang_thai") == "tam_dung" else d.tam_dung(person_v, rev_v)
        return run_op(person_v, fn)

    def on_face(person_v, rev_v, face_note_v):
        up_after = lambda _r: dict(msg=msg_html("Đã khép mặt, đồng hồ chạy tiếp cho mặt kế.", "ok"))      # noqa: E731
        return run_op(person_v, lambda: d.xong_mat(person_v, rev_v, face_note_v or ""), "", up_after)

    def on_undo(person_v, rev_v):
        return run_op(person_v, lambda: d.hoan_tac_mat(person_v, rev_v), "Đã gộp mặt vừa xong trở lại thành mặt đang làm.")

    def on_done(person_v, rev_v, tinh_v, somat_v, nhan_v):
        def after(res):
            return dict(msg=summary_html(res, person_v), seq=gr.update(value=""), note=gr.update(value=""))
        return run_op(person_v, lambda: d.xong_luu(person_v, rev_v, bool(tinh_v), val_int(somat_v, "Số mặt đã xử lý"), nhan_v or "auto", None), "", after)

    def on_fix(person_v, rev_v, fix_v):
        return run_op(person_v, lambda: d.sua_thoi_gian(person_v, fix_v, rev_v), "Đã sửa thời gian (ghi sua_tay = 1, số đo gốc được giữ trong ghi chú).")

    def on_keep(person_v, rev_v):
        def fn():
            v = d.xem(person_v)
            r = rev_v
            for c in v["canh_bao"]:
                if not c["xu_ly"]:
                    v = d.giu_canh_bao(person_v, c["ma"], r)
                    r = v["rev"]
            return v
        return run_op(person_v, fn, "Giữ nguyên: cảnh báo được ghi kèm vào dòng bấm giờ.")

    def on_tru(person_v, rev_v):
        return run_op(person_v, lambda: d.tru_khoang_tat(person_v, rev_v), "Đã trừ khoảng trang tắt: đồng hồ tạm dừng, bấm Tiếp tục khi sẵn sàng.")

    def on_hong(person_v):
        return run_op(person_v, lambda: d.bo_trang_thai_hong(person_v), "Đã đổi tên file trạng thái hỏng (không xoá); có thể Bắt đầu lại.")

    def on_huy_open(person_v, rev_v):
        err = guard(person_v)
        if err:
            gr.Warning(err, title="Đồng hồ")
            return pack(**view_updates(person_v, err, "warn"))
        try:
            y = d.huy_mo(person_v)
        except DongHoLoi as ex:
            gr.Warning(str(ex), title="Đồng hồ")
            return pack(**view_updates(person_v, str(ex), "warn"))
        body = (f'<div class="modal-title" id="dh-cancel-title">Hủy phiên?</div><div class="nap-box nap-err" role="alert">{e(y["tom_tat"])}</div>')
        up = view_updates(person_v, with_inputs=False, keep_choices=True)
        up.update(modal=gr.update(visible=True), modal_body=body, huy_st=y["ma"], huy_tb=gr.update(value=""))
        return pack(**up)

    def on_huy_ok(person_v, rev_v, ma_v, chu_v):
        err = guard(person_v)
        if err:
            gr.Warning(err, title="Đồng hồ")
            up = view_updates(person_v, err, "warn")
            up.update(modal=gr.update(visible=False), huy_st="")
            return pack(**up)
        try:
            d.huy_xac_nhan(person_v, ma_v, chu_v, rev=rev_v)
        except DongHoLoi as ex:
            gr.Warning(str(ex), title="Đồng hồ")
            up = view_updates(person_v, str(ex), "warn", keep_choices=True)
            up.update(modal=gr.update(visible=False), huy_st="")           # mã dùng một lần: gõ sai thì hộp đóng, bấm Hủy phiên… để mở lại
            return pack(**up)
        up = view_updates(person_v, "Đã hủy phiên: không ghi dòng nào vào timing; đã ghi nhật ký huy_%s.csv." % person_v, "ok")
        up.update(modal=gr.update(visible=False), huy_st="", huy_tb=gr.update(value=""))
        return pack(**up)

    def on_huy_no(person_v):
        up = view_updates(person_v, with_inputs=False, keep_choices=True)
        up.update(modal=gr.update(visible=False), huy_st="")
        return pack(**up)

    def on_sug_go(person_v, cond_v, note_v, rev_v):
        snap = ctx.job.snapshot()
        run = snap.get("run")
        if not run:
            return pack(**view_updates(person_v))
        n = so_mat_cua_luot(snap.get("run_dir") or "") or dong_ho.N_MAT_MAC_DINH

        def fn():
            v = d.bat_dau(person_v, cond_v, dot=run, bo_anh=run, n_mat=n, ghi_chu=note_v, rev=rev_v or 0)
            ctx.dh_started = getattr(ctx, "dh_started", set()) | {run}
            return v
        res = run_op(person_v, fn, f"Đã bắt đầu đồng hồ cho đợt {run} ({n} mặt).")
        return res

    def on_sug_no():
        snap = ctx.job.snapshot()
        if snap.get("run"):
            ctx.dh_dismissed = getattr(ctx, "dh_dismissed", set()) | {snap["run"]}
        return pack(sug="", b_sug=gr.update(visible=False), b_sug_no=gr.update(visible=False))

    def on_auto(auto_v, person_v, cond_v):
        if not auto_v:
            ctx.dh_auto = None
            return gr.skip()
        if person_v not in dong_ho.NGUOI_OK or cond_v not in dong_ho.DIEU_KIEN:
            gr.Warning("Chọn người và nhóm trước khi bật tự bắt đầu.", title="Đồng hồ")
            ctx.dh_auto = None
            return gr.update(value=False)
        ctx.dh_auto = dict(nguoi=person_v, dieu_kien=cond_v)
        return gr.skip()

    def on_reexport(person_v, goi_v, nhan_v):
        err = guard(person_v)
        if err or not goi_v:
            text = err or "Chọn một gói đã lưu trước."
            gr.Warning(text, title="Đồng hồ")
            return pack(**view_updates(person_v, text, "warn"))

        def fn():
            return d.xuat_lai_goi(person_v, goi_v, nhan_v or "auto")
        return run_op(person_v, fn, f"Đã xuất lại gói {goi_v} với nhãn hiện có (cùng mã phiên, cùng số đo thời gian).")

    # ---------- nối sự kiện ----------
    refresh_in = [person, rev_st]
    person.input(on_person, [person], OUTS, **OPTS)
    timer.tick(on_tick, [person], OUTS, **dict(OPTS, concurrency_id="dongho_tick"))
    b_start.click(on_start, [person, cond, dot, task, job, khoi, n_mat, seq, note, rev_st], OUTS, **OPTS)
    b_pause.click(on_pause, [person, rev_st], OUTS, **OPTS)
    b_face.click(on_face, [person, rev_st, face_note], OUTS, **OPTS)
    b_undo.click(on_undo, [person, rev_st], OUTS, **OPTS)
    b_done.click(on_done, [person, rev_st, tinh_mat, so_mat_xong, nhan_dd], OUTS, **OPTS)
    b_fix.click(on_fix, [person, rev_st, fix_tb], OUTS, **OPTS)
    b_keep.click(on_keep, [person, rev_st], OUTS, **OPTS)
    b_tru.click(on_tru, [person, rev_st], OUTS, **OPTS)
    b_hong.click(on_hong, [person], OUTS, **OPTS)
    b_cancel.click(on_huy_open, [person, rev_st], OUTS, **OPTS)
    b_huy_ok.click(on_huy_ok, [person, rev_st, huy_st, huy_tb], OUTS, **OPTS)
    b_huy_no.click(on_huy_no, [person], OUTS, **OPTS)
    b_sug.click(on_sug_go, [person, cond, note, rev_st], OUTS, **OPTS)
    b_sug_no.click(on_sug_no, None, OUTS, **OPTS)
    auto_cb.input(on_auto, [auto_cb, person, cond], [auto_cb], **OPTS)
    b_reexp.click(on_reexport, [person, goi_dd, nhan_dd], OUTS, **OPTS)
    demo.load(refresh, refresh_in, OUTS, **OPTS)
    return refresh, refresh_in, OUTS, OPTS
