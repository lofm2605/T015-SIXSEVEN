"""Đồng hồ bấm giờ gán nhãn ở ĐẦU trang rà soát (logic ở dong_ho.py; không import gradio ở đầu module). Không còn tab riêng.

Một chip thấy ở mọi tab: ⏱ mm:ss · trạng thái · người · đợt, kèm MỘT nút Pause/Resume. Đồng hồ tự chạy khi bấm Nạp ảnh (auto_start): người là người rà của trang (P1–P5),
nhóm lấy từ config/nhom_thi_nghiem.json, không có thì assisted. mm:ss chạy mượt bằng JS ở trình duyệt (không gọi server mỗi giây); nguồn sự thật là đồng hồ phía server,
`gr.Timer(15)` chỉ đồng bộ lại. Save timing (timing_<Pk>.csv và gói kết quả) hoặc Discard session nằm trong hộp "Đóng trang rà soát?" khi đang có phiên.
Không ảnh mặt, không mạng, không token, không phát file nào (không thêm allowed_paths).
"""
import html
import json
import os
import sys
import types
import uuid

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)
import cai_dat  # noqa: E402
import dong_ho  # noqa: E402
import nap_anh  # noqa: E402
from dong_ho import DongHo, DongHoLoi, fmt_giay  # noqa: E402
from m28core import nhom as nhom_mod  # noqa: E402

TRANG_THAI_VI = {"chay": "▶ Đang chạy", "tam_dung": "⏸ Tạm dừng", "du_mat": "■ Đủ mặt, chờ lưu", "chua": "• Chưa có phiên"}
DIEU_KIEN_MAC_DINH = "assisted"
OPTS = dict(show_progress="hidden", api_visibility="private", concurrency_limit=1, concurrency_id="dongho")
NUT_DUNG, NUT_TIEP = "Pause", "Resume"
NUT_BO, NUT_BO_LAN_2 = "Discard session (not saved)", "Click again to discard (not saved)"

CSS = """
/* ---------- chip đồng hồ ở đầu trang (màu lấy từ biến theme) ---------- */
#dh-bar { gap: 6px; flex-wrap: nowrap !important; align-items: center; margin: 2px 0 4px; }
#dh-mini-wrap { padding: 0 !important; min-height: 0 !important; flex: 0 1 auto !important; min-width: 0 !important; width: auto !important; }
.dh-mini { display: inline-flex; align-items: center; gap: 8px; padding: 4px 12px; border-radius: 999px; font-size: 14px; color: var(--body-text-color);
  border: 1px solid var(--border-color-primary); background: var(--block-background-fill); font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.dh-mini b { font-size: 16px; white-space: nowrap; flex: none; }
.dh-mini > span:last-child { min-width: 0; }
@media (max-width: 600px) { #dh-bar { flex-wrap: wrap !important; } .dh-mini { border-radius: 16px; } }
.dh-mini.s-chay { border-color: #16a34a; background: color-mix(in srgb, #16a34a 14%, transparent); }
.dh-mini.s-tam_dung, .dh-mini.s-du_mat { border-color: #d97706; background: color-mix(in srgb, #d97706 16%, transparent); }
.dh-mini.s-chua { opacity: .85; border-style: dashed; }
#dh-mini-btn { flex: 0 0 auto !important; width: auto !important; min-width: 84px !important; min-height: 34px !important; font-weight: 800; }
#dh-luu-btn, #dh-bo-btn { font-weight: 800; }
"""

JS_BODY = r"""
  // ---- Chip đồng hồ ở đầu trang: mm:ss chạy mượt ở trình duyệt, KHÔNG gọi server mỗi giây. HTML mang data-* (giây server lúc dựng, đang chạy hay không, mã lần dựng);
  //      thấy mã mới thì lấy mốc performance.now() (đồng hồ đơn điệu của trình duyệt, không dùng giờ hệ thống nên không lệch khi giờ máy đổi), rồi hiển thị giây_server + (now - mốc)/1000. ----
  if (!window.__m28Dh) {
    window.__m28Dh = { mini: { ver: null, t0: 0, g: 0 } };
    const p2 = (n) => String(n).padStart(2, '0');
    const fmt = (s) => {
      s = Math.max(0, Math.round(s));
      const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
      return h ? h + ':' + p2(m) + ':' + p2(x) : p2(m) + ':' + p2(x);
    };
    setInterval(() => {
      const el = document.getElementById('dh-mini-time');
      if (!el) { return; }
      const st = window.__m28Dh.mini;
      if (el.dataset.ver !== st.ver) { st.ver = el.dataset.ver; st.t0 = performance.now(); st.g = parseFloat(el.dataset.giay) || 0; }
      if (el.dataset.chay !== '1') { return; }
      const a = fmt(st.g + (performance.now() - st.t0) / 1000);
      if (el.textContent !== a) { el.textContent = a; }
    }, 250);
  }
"""


def e(x):
    return html.escape("" if x is None else str(x), quote=True)


# ---------- HTML thuần (test không cần gradio) ----------
def mini_html(v, ver=None, ly_do=""):
    """Chip: đang có phiên thì mm:ss tổng phiên (chạy mượt bằng JS) + trạng thái + người + đợt; chưa có thì nói đồng hồ tự chạy khi bấm Nạp ảnh (hoặc lý do chưa chạy được)."""
    ver = ver or uuid.uuid4().hex[:8]
    if not v.get("co_phien"):
        if v.get("hong"):
            ly_do = ly_do or "File trạng thái đồng hồ bị hỏng (đổi tên outputs/timing/dang_chay_<người>.json rồi nạp lại trang)"
        text = ly_do or "Đồng hồ chưa chạy · tự chạy khi bấm Nạp ảnh"
        return f'<div id="dh-mini" class="dh-mini s-chua" role="status"><span aria-hidden="true">⏱</span><span>{e(text)}</span></div>'
    st = v["trang_thai"]
    return (f'<div id="dh-mini" class="dh-mini s-{e(st)}" role="status"><span aria-hidden="true">⏱</span>'
            f'<b id="dh-mini-time" data-ver="{ver}" data-giay="{v["giay_phien"]:.3f}" data-chay="{1 if st == "chay" else 0}">{fmt_giay(v["giay_phien"])}</b>'
            f'<span>{e(TRANG_THAI_VI[st])} · {e(v["nguoi"])} · {e(v.get("dot") or v.get("task") or "")}</span></div>')


def summary_html(r, nguoi):
    """Tóm tắt sau khi lưu số đo: số mặt, tổng, giây/mặt, đường dẫn tương đối (không đường dẫn tuyệt đối)."""
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


def vi_hop(text):
    """Thông báo của dong_ho.py viết cho các nút cũ của tab; ở hộp Đóng trang nút tên khác: đổi chữ cho khớp."""
    text = text.replace("Chọn Sửa thời gian / Giữ nguyên, hoặc bấm Xong (lưu) thêm một lần nữa để lưu kèm cảnh báo.", "Bấm Save timing thêm một lần nữa để lưu kèm cảnh báo.")
    return text.replace("dùng Xong hoặc", "dùng Save timing hoặc").replace("Hủy phiên", "Discard session").replace("Xong (lưu)", "Save timing")


def box_html(text, level="warn"):
    return f'<div class="nap-box nap-{"err" if level == "err" else "warn"}" role="alert">{e(text)}</div>'


# ---------- dùng chung với review_app ----------
def get_dh(ctx):
    """DongHo của thư mục dự án (tạo lười, giữ trong ctx)."""
    d = getattr(ctx, "dong_ho", None)
    if d is None or d.root != os.path.abspath(ctx.project_root):
        d = DongHo(ctx.project_root)
        ctx.dong_ho = d
    return d


def default_person(ctx):
    for cand in (ctx.reviewer, cai_dat.get().next_reviewer(ctx.reviewer)):
        if cand in dong_ho.NGUOI_OK:
            return cand
    return None


def phien_cua(ctx):
    """(người, xem) của phiên mà chip theo dõi: người rà của trang nếu có phiên, không thì người P1–P5 nào đang có phiên, không có thì (người rà mặc định, xem rỗng)."""
    d = get_dh(ctx)
    mac = default_person(ctx)
    for p in ([mac] if mac else []) + [x for x in dong_ho.NGUOI_OK if x != mac]:
        try:
            v = d.xem(p)
        except Exception:
            continue
        if v.get("co_phien") or v.get("hong"):
            return p, v
    return mac, (dict(co_phien=False) if mac is None else d.xem(mac))


def tu_tam_dung(ctx):
    """Gọi khi đóng trang / Ctrl+C: tự tạm dừng mọi đồng hồ đang chạy, đặt cờ đóng, in một dòng ra terminal cho mỗi người. Trả danh sách (người, giờ)."""
    try:
        d = get_dh(ctx)
        got = d.tu_tam_dung_tat_ca()
        d.closing = True
    except Exception:
        return []
    for nguoi, gio in got:
        print(f"Đồng hồ của {nguoi} đã tạm dừng lúc {gio}: mở lại trang rà soát để bấm Resume (hoặc Save timing ở hộp Đóng trang).", flush=True)
    return got


def close_note(ctx):
    """Dòng thêm vào hộp 'Đóng trang rà soát?' khi đang có phiên đồng hồ. Rỗng nếu không."""
    try:
        p, v = phien_cua(ctx)
    except Exception:
        return ""
    if not v.get("co_phien"):
        return ""
    dang = "đang chạy: đóng trang sẽ <b>tự tạm dừng</b> đồng hồ" if v["trang_thai"] == "chay" else "đang tạm dừng"
    return (f'<div class="nap-box nap-warn" role="alert">Đồng hồ của <b>{e(p)}</b> {dang} ({fmt_giay(v["giay_phien"])}, đợt {e(v.get("dot") or v.get("task") or "")}). '
            "Làm xong thì bấm <b>Save timing</b> để ghi dòng bấm giờ và gói kết quả cho nhóm trưởng; chưa xong thì cứ đóng, mở lại trang bấm Resume.</div>")


def so_mat_cua_luot(run_dir):
    """Số mặt của một lượt (đọc map50/mp50.json), hoặc None."""
    try:
        with open(os.path.join(run_dir, "map50", "mp50.json"), encoding="utf-8") as f:
            n = len(json.load(f))
        return n if n > 0 else None
    except (OSError, ValueError, TypeError):
        return None


def auto_start(gr, ctx, run, n_mat=None):
    """Gọi từ tab Nạp ảnh ngay khi bấm Nạp: đồng hồ bắt đầu cho người rà của trang. Nhóm lấy từ config/nhom_thi_nghiem.json, không có thì assisted.
    Đã có phiên thì giữ nguyên (báo, không đè, không tự Resume). Trả thông báo (cũng hiện ở góc trang nếu có gr) hoặc None khi đang đóng trang."""
    if ctx.closing:
        return None

    def noi(text, warn=False):
        if gr is not None:
            (gr.Warning(text, title="Đồng hồ") if warn else gr.Info(text))
        return text
    try:
        d = get_dh(ctx)
        nguoi, v = phien_cua(ctx)
        if nguoi is None:
            return noi("Chưa chạy đồng hồ: tên người rà phải là P1 đến P5 (đặt ở tab Cài đặt).", warn=True)
        if v.get("co_phien"):
            tt = "đang chạy" if v["trang_thai"] == "chay" else "đang tạm dừng (bấm Resume ở đầu trang)"
            return noi(f"Đồng hồ của {nguoi} {tt}, giữ nguyên phiên đợt {v.get('dot') or v.get('task') or ''}.")
        cond = nhom_mod.nhom_cua(nhom_mod.doc(ctx.project_root), nguoi) or DIEU_KIEN_MAC_DINH
        d.bat_dau(nguoi, cond, dot=run, bo_anh=run, n_mat=n_mat or dong_ho.N_MAT_MAC_DINH, rev=0)
        ctx.dh_started = getattr(ctx, "dh_started", set()) | {run}
        return noi(f"Đồng hồ của {nguoi} bắt đầu chạy (đợt {run}, {cond}).")
    except DongHoLoi as ex:
        return noi(f"Chưa chạy được đồng hồ: {ex}", warn=True)


# ---------- chip ----------
def chip(gr, demo, ctx):
    """Dựng chip + nút Pause/Resume (đặt ngay dưới thanh Close page). Trả SimpleNamespace(refresh, outs, opts) để các nơi khác (Nạp ảnh, hộp Đóng trang) làm mới chip bằng .then."""
    d = get_dh(ctx)
    with gr.Row(elem_id="dh-bar"):
        mini = gr.HTML(mini_html(dict(co_phien=False)), elem_id="dh-mini-wrap", apply_default_css=False)
        btn = gr.Button(NUT_DUNG, elem_id="dh-mini-btn", size="sm", interactive=False)
    rev_st = gr.State(0)
    timer = gr.Timer(15)
    outs = [mini, btn, rev_st]

    def hien():
        if ctx.closing:
            return dict(mini=mini_html(dict(co_phien=False), ly_do="Đã đóng trang"), btn=gr.update(interactive=False), rev=0)
        p, v = phien_cua(ctx)
        st = v.get("trang_thai")
        return dict(mini=mini_html(v, ly_do="" if p else "Đồng hồ chưa chạy · tên người rà phải là P1 đến P5 (đặt ở tab Cài đặt)"),
                    btn=gr.update(interactive=bool(v.get("co_phien")) and st in ("chay", "tam_dung"), value=NUT_TIEP if st == "tam_dung" else NUT_DUNG,
                                  variant="primary" if st == "tam_dung" else "secondary"),
                    rev=v.get("rev", 0))

    def pack(up):
        return up["mini"], up["btn"], up["rev"]

    def refresh():
        return pack(hien())

    def on_tick():
        if ctx.closing:
            return gr.skip(), gr.skip(), gr.skip()
        p, v = phien_cua(ctx)
        if p and v.get("co_phien"):
            try:
                d.nhip(p)
            except Exception:
                pass
        return pack(hien())

    def on_btn(rev_v):
        p, v = phien_cua(ctx)
        if ctx.closing:
            gr.Warning(nap_anh.CLOSING_MSG, title="Đồng hồ")
        elif not v.get("co_phien"):
            gr.Warning("Chưa có phiên đồng hồ nào (đồng hồ tự chạy khi bấm Nạp ảnh).", title="Đồng hồ")
        else:
            try:
                d.tiep_tuc(p, rev_v or 0) if v.get("trang_thai") == "tam_dung" else d.tam_dung(p, rev_v or 0)
            except DongHoLoi as ex:
                gr.Warning(str(ex), title="Đồng hồ")
        return pack(hien())

    btn.click(on_btn, [rev_st], outs, **OPTS)
    timer.tick(on_tick, None, outs, **dict(OPTS, concurrency_id="dongho_tick"))
    demo.load(refresh, None, outs, **OPTS)
    return types.SimpleNamespace(refresh=refresh, outs=outs, opts=OPTS, btn=btn, mini=mini)


# ---------- hộp "Đóng trang rà soát?": Save timing / Discard session ----------
def close_buttons(gr, ctx, body, body_fn):
    """Hai nút trong hộp Đóng trang (gọi BÊN TRONG hàng nút của hộp). body: gr.HTML của hộp; body_fn(extra_html) dựng lại nội dung hộp kèm đoạn thêm.
    Trả SimpleNamespace(show, show_outs, events): show() chạy sau khi hộp mở (chỉ hiện hai nút khi đang có phiên); events: sự kiện của hai nút để nối .then làm mới chip."""
    b_luu = gr.Button("Save timing", variant="primary", elem_id="dh-luu-btn", visible=False)
    b_bo = gr.Button(NUT_BO, variant="stop", elem_id="dh-bo-btn", visible=False)
    ma_st = gr.State("")
    show_outs = [b_luu, b_bo, ma_st]
    hide = gr.update(visible=False)

    def show():
        _p, v = phien_cua(ctx)
        co = bool(v.get("co_phien")) and not ctx.closing
        return gr.update(visible=co), gr.update(visible=co, value=NUT_BO), ""

    def on_luu():
        d = get_dh(ctx)
        p, v = phien_cua(ctx)
        if ctx.closing or not v.get("co_phien"):
            return body_fn(box_html("Không có phiên đồng hồ nào để lưu.")), hide, hide, ""
        if not d.ung_vien_nhan(p) and getattr(ctx, "dh_luu_cho", None) != (v["phien"], v["rev"]):       # chưa có nhãn xuất: nhắc collect trước, bấm thêm lần nữa thì lưu chỉ thời gian
            ctx.dh_luu_cho = (v["phien"], v["rev"])
            return (body_fn(box_html("Chưa thấy file nhãn đã xuất của bạn trong raw/ (<task>_" + p + "_<DDMM>.xml), nên gói kết quả sẽ chỉ có thời gian. Chạy "
                                     "python tool/m28.py collect --reviewer " + p + " trước, rồi bấm Save timing; hoặc bấm Save timing thêm lần nữa để lưu chỉ thời gian.")),
                    gr.update(), gr.update(), "")
        try:
            r = d.xong_luu(p, v["rev"], True, None, "auto", None)
        except DongHoLoi as ex:
            text = vi_hop(str(ex))
            gr.Warning(text, title="Đồng hồ")
            return body_fn(box_html(text)), gr.update(), gr.update(), ""
        return body_fn(summary_html(r, p)), hide, hide, ""

    def on_bo(ma_v):
        d = get_dh(ctx)
        p, v = phien_cua(ctx)
        if ctx.closing or not v.get("co_phien"):
            return body_fn(box_html("Không có phiên đồng hồ nào để bỏ.")), hide, hide, ""
        try:
            if not ma_v:                                                       # bấm lần một: nêu sẽ bỏ gì, đổi nhãn nút
                y = d.huy_mo(p)
                return (body_fn(box_html(y["tom_tat"] + " Bấm nút đỏ thêm lần nữa để bỏ phiên (không ghi gì vào timing).", "err")), gr.update(),
                        gr.update(value=NUT_BO_LAN_2), y["ma"])
            d.huy_xac_nhan(p, ma_v, "HUY", rev=v["rev"])
        except DongHoLoi as ex:
            gr.Warning(vi_hop(str(ex)), title="Đồng hồ")
            return body_fn(box_html(vi_hop(str(ex)))), gr.update(), gr.update(value=NUT_BO), ""
        return body_fn(f'<div class="dh-ok" role="status">Đã bỏ phiên đồng hồ của {e(p)}: không ghi dòng nào vào timing (nhật ký huy_{e(p)}.csv có ghi lại).</div>'), hide, hide, ""

    ev_luu = b_luu.click(on_luu, None, [body, b_luu, b_bo, ma_st], **dict(OPTS, concurrency_id="dongho_luu"))
    ev_bo = b_bo.click(on_bo, [ma_st], [body, b_luu, b_bo, ma_st], **dict(OPTS, concurrency_id="dongho_luu"))
    return types.SimpleNamespace(show=show, show_outs=show_outs, events=[ev_luu, ev_bo])
