"""Phần Gradio của khung "Đẩy lên CVAT" (tab Rà soát) và tab "Các đợt" (quản lý đợt, xoá mềm, xoá task) của trang rà soát M28.

Không import gradio ở đầu module (gradio chỉ đến từ tham số `gr`, như _nap_tab/_review_tab trong review_app.py), nên import module này
không kéo gradio hay torch. Logic thuần nằm ở dot_anh.py (đợt, ảnh, xoá mềm) và day_cvat.py (nút đẩy, xác nhận, tiến độ); ở đây chỉ nối
chúng với Gradio.

An toàn:
  * TRANG KHÔNG GỌI MẠNG: push và xoá task chạy bằng tiến trình con (nap_anh.PushJob/DeleteTaskJob); token chỉ đến từ biến môi trường
    của tiến trình trang (kế thừa cho tiến trình con), không bao giờ có ô nhập, không bao giờ hiện trên trang.
  * Tên đợt/ảnh từ trình duyệt chỉ dùng khi là phần tử của danh sách do server tính; mọi lần xoá phải qua hộp xác nhận kèm mã ngẫu nhiên
    (dot_anh.Pending): bấm xác nhận của hộp cũ/trễ không xoá nhầm.
  * Nút Huỷ của hộp xác nhận là nút mặc định (có focus khi hộp mở), Esc = Huỷ; xoá task phải gõ lại đúng tên và tick ô hiểu hậu quả.
"""
import html
import json
import os
import re
import threading

import day_cvat
import dot_anh
import nap_anh
from m28core import dang_chay
from nap_anh import RunError

ACT_KEYS = ("act", "run", "name", "page", "trash", "entry")
ACTS = {"open", "back", "page", "ra", "push", "delimg", "restore", "empty", "delrun", "deltask", "restore_run", "purge_run"}

# ---------- CSS / JS thêm vào CSS và PAGE_JS của review_app ----------
CSS = """
/* ---------- khung Đẩy lên CVAT (tab Rà soát) ---------- */
#push-panel, #push-msg, #push-prog, #push-result, #dot-root, #dot-msg, #dot-job { padding: 0 !important; }
#btn-push { min-height: 48px; font-size: 16px; font-weight: 800; }
#btn-push:not(:disabled) { background: #2563eb !important; border-color: #1d4ed8 !important; color: #fff !important; opacity: 1 !important; }
#btn-push:disabled { opacity: .5; cursor: not-allowed; }
.push-why { margin-top: 0; }
.push-cause { margin-top: 6px; overflow-wrap: anywhere; }
.push-link { overflow-wrap: anywhere; }
#push-log textarea { font-family: var(--font-mono); font-size: 12px; line-height: 1.35; }
.push-done .m28-info { margin: 6px 0; }
/* ---------- hộp xác nhận (modal) ---------- */
#side { z-index: 2; }                                  /* modal nằm trong cột này: phải nổi trên ảnh nhỏ được chọn (z-index 1) của cột trái */
.m28-modal { position: fixed !important; inset: 0 !important; z-index: 100001 !important; display: flex !important; align-items: center;
  justify-content: center; padding: 12px !important; overflow: auto; background: rgba(0, 0, 0, .55) !important; border: 0 !important; }
.m28-modal-box { flex: 0 0 auto !important; width: min(560px, 100%) !important; height: auto !important; min-height: 0 !important;
  max-height: calc(100vh - 24px); overflow: auto; gap: 10px !important; padding: 16px !important; box-sizing: border-box;
  background: var(--block-background-fill) !important; border: 1px solid var(--border-color-primary) !important; border-radius: 14px !important;
  box-shadow: 0 12px 40px rgba(0, 0, 0, .35); }
.modal-title { font-size: 19px; font-weight: 800; overflow-wrap: anywhere; }
.modal-danger { color: #dc2626; }
.m28-modal-btns { gap: 10px; flex-wrap: wrap; margin: 0 !important; width: 100% !important; }
.m28-modal-btns button { min-height: 46px; font-weight: 800; min-width: 120px !important; }
.m28-modal-btns button:focus-visible { outline: 3px solid #2563eb; outline-offset: 2px; }
#push-confirm-ok:not(:disabled) { background: #2563eb !important; border-color: #1d4ed8 !important; color: #fff !important; }
#dot-modal-ok:not(:disabled) { background: #dc2626 !important; border-color: #b91c1c !important; color: #fff !important; }
#dot-modal-ok:disabled { opacity: .45; cursor: not-allowed; }
#push-confirm-title, #dot-modal-title { margin: 0; }
#push-confirm-body, #dot-modal-body { padding: 0 !important; }
.m28-modal-btns button:focus { outline: 3px solid #2563eb; outline-offset: 2px; }
@media (max-width: 600px) { .m28-modal-btns button { flex: 1 1 100% !important; } }
/* ---------- tab Các đợt ---------- */
#tab-dot { padding: 8px 0 0 !important; max-width: 1240px; margin: 0 auto; width: 100%; gap: 10px; }
.dot-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }
.dot-card { display: flex; flex-direction: column; gap: 6px; padding: 12px 14px; border-radius: 12px; background: var(--block-background-fill);
  border: 1px solid var(--border-color-primary); }
.dot-card-head { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 10px; }
.dot-name { all: unset; cursor: pointer; font-size: 20px; font-weight: 800; color: var(--body-text-color); text-decoration: underline;
  text-decoration-color: var(--border-color-primary); text-underline-offset: 3px; }
.dot-name:hover, .dot-name:focus-visible { text-decoration-color: #2563eb; outline: 2px solid #2563eb; outline-offset: 2px; border-radius: 4px; }
.dot-state { margin-left: auto; font-size: 13px; padding: 2px 10px; border-radius: 999px; border: 1px solid var(--cc, #9ca3af);
  background: color-mix(in srgb, var(--cc, #9ca3af) 17%, transparent); overflow-wrap: anywhere; }
.dot-state.st-ok { --cc: #16a34a; } .dot-state.st-warn { --cc: #d97706; } .dot-state.st-info { --cc: #2563eb; }
.dot-active { font-size: 12px; padding: 1px 8px; border-radius: 999px; background: #2563eb; color: #fff; }
.dot-meta, .dot-extra, .dot-muted { font-size: 13px; color: var(--body-text-color-subdued); }
.dot-note { font-size: 14px; padding: 6px 8px; border-left: 4px solid #9ca3af; background: var(--background-fill-secondary); overflow-wrap: anywhere;
  white-space: pre-wrap; }
.dot-counts { display: flex; flex-wrap: wrap; gap: 6px; }
.dot-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
.dot-btn { cursor: pointer; padding: 7px 14px; min-height: 36px; font-size: 14px; font-weight: 700; border-radius: 8px; color: var(--body-text-color);
  background: var(--background-fill-secondary); border: 1px solid var(--border-color-primary); }
.dot-btn:hover:not(:disabled) { filter: brightness(.95); }
.dot-btn:disabled { opacity: .45; cursor: not-allowed; }
.dot-btn-ra:not(:disabled) { background: #16a34a; border-color: #15803d; color: #fff; }
.dot-btn-push:not(:disabled) { background: #2563eb; border-color: #1d4ed8; color: #fff; }
.dot-btn-danger { color: #dc2626; border-color: #dc2626; background: color-mix(in srgb, #dc2626 8%, transparent); }
.dot-btn:focus-visible, .dot-trash:focus-visible { outline: 3px solid #2563eb; outline-offset: 2px; }
.dot-gridhead { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px; margin-bottom: 6px; }
.dot-gridtitle { font-size: 17px; }
.dot-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; margin: 10px 0; }
.dot-thumb { position: relative; border-radius: 10px; overflow: hidden; border: 3px solid var(--tc, #9ca3af); background: var(--background-fill-secondary); }
.dot-thumb.st-nhan { --tc: #16a34a; } .dot-thumb.st-gan_tay { --tc: #d97706; } .dot-thumb.st-bo { --tc: #dc2626; }
.dot-thumb.st-khong_thay_mat, .dot-thumb.st-khong_dung_duoc { --tc: #6b7280; }
.dot-thumb img { display: block; width: 100%; aspect-ratio: 1; object-fit: cover; }
.dot-badge { position: absolute; left: 4px; top: 4px; font-size: 11px; font-weight: 800; padding: 1px 7px; border-radius: 6px; color: #fff;
  background: var(--tc, #6b7280); }
.dot-cap { padding: 3px 6px 5px; font-size: 11.5px; line-height: 1.25; overflow-wrap: anywhere; }
.dot-orig { color: var(--body-text-color-subdued); }
.dot-trash { position: absolute; right: 5px; top: 5px; display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px;
  border-radius: 8px; border: 0; cursor: pointer; background: #dc2626; color: #fff; opacity: 0; transition: opacity .12s; }
.dot-thumb:hover .dot-trash, .dot-thumb:focus-within .dot-trash, .dot-trash:focus-visible { opacity: 1; }
@media (hover: none) { .dot-trash { opacity: 1; } }
.dot-pager { display: flex; align-items: center; justify-content: center; gap: 12px; margin: 6px 0 10px; }
.dot-section { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; padding: 10px 12px; border-radius: 10px;
  border: 1px solid var(--border-color-primary); background: var(--block-background-fill); }
.dot-section-title { font-weight: 800; font-size: 15px; }
.dot-cvat { border-color: #2563eb; }
.dot-warn { padding: 8px 10px; border-radius: 8px; font-size: 13.5px; font-weight: 700; color: var(--body-text-color);
  background: color-mix(in srgb, #dc2626 14%, transparent); border: 1px solid #dc2626; }
.dot-del-row { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 6px 12px; font-size: 14px; overflow-wrap: anywhere; }
.dot-del-row > span:last-child { display: flex; gap: 8px; }
.dot-danger { margin-top: 14px; padding-top: 10px; border-top: 1px dashed var(--border-color-primary); }
#dot-refresh { max-width: 160px; }
#dot-job:not(:has(.html-container > div > *)), #dot-msg:not(:has(.html-container > div > *)), #push-msg:not(:has(.html-container > div > *)), #push-prog:not(:has(.html-container > div > *)),
#push-result:not(:has(.html-container > div > *)), #push-panel:not(:has(.html-container > div > *)) { display: none; }
#dot-intro { align-self: center; }
@media (max-width: 600px) { .dot-cards { grid-template-columns: 1fr; } .dot-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .dot-state { margin-left: 0; } }
"""

JS_BODY = r"""
  // ---- Tab "Các đợt" và hộp xác nhận (modal): chạy một lần, uỷ quyền sự kiện vì HTML được vẽ lại ----
  if (!window.__m28Dot) {
    window.__m28Dot = true;
    const setValue = (el, v) => {
      const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v);
      el.dispatchEvent(new Event('input', { bubbles: true }));
    };
    document.addEventListener('click', (e) => {
      const el = e.target && e.target.closest ? e.target.closest('#dot-root [data-act]') : null;
      if (!el || el.disabled) { return; }
      e.preventDefault();
      const d = el.dataset;
      const payload = JSON.stringify({ act: d.act || '', run: d.run || '', name: d.name || '', page: d.page || '',
                                       trash: d.trash || '', entry: d.entry || '' });
      const box = document.querySelector('#dot-act textarea, #dot-act input');
      const go = document.getElementById('dot-act-go');
      if (!box || !go) { return; }
      setValue(box, payload);
      setTimeout(() => go.click(), 40);
    });
    const modals = () => Array.from(document.querySelectorAll('.m28-modal'));
    const decorate = () => {
      modals().forEach((m) => {
        if (m.dataset.m28) { return; }
        m.dataset.m28 = '1';
        m.setAttribute('role', 'dialog');
        m.setAttribute('aria-modal', 'true');
        setTimeout(() => {                                  // nút Huỷ là mặc định: có focus khi hộp mở (tìm sau khi con đã dựng xong)
          const t = m.querySelector('.modal-title');
          if (t && t.id) { m.setAttribute('aria-labelledby', t.id); }
          const cancel = m.querySelector('button[id$="-cancel"]');
          if (cancel) { cancel.focus(); }
        }, 120);
      });
    };
    new MutationObserver(decorate).observe(document.body, { childList: true, subtree: true });
    decorate();
    document.addEventListener('keydown', (e) => {
      const ms = modals();
      if (!ms.length) { return; }
      const m = ms[ms.length - 1];
      if (e.key === 'Escape') {                            // Esc = Huỷ
        e.preventDefault(); e.stopPropagation();
        const c = m.querySelector('button[id$="-cancel"]');
        if (c) { c.click(); }
        return;
      }
      if (e.key === 'Tab') {                               // giữ focus trong hộp
        const f = Array.from(m.querySelectorAll('button, input, textarea, select, [tabindex]'))
          .filter((x) => !x.disabled && x.offsetParent !== null && x.getAttribute('tabindex') !== '-1');
        if (!f.length) { return; }
        const first = f[0], last = f[f.length - 1];
        if (!m.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
        else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    }, true);
  }
"""


def _e(x):
    return html.escape(str(x), quote=True)


def box(text, level="info"):
    return f'<div class="m28-msg m-{level}" role="status">{_e(text)}</div>' if text else ""


def parse_action(raw):
    """Chuỗi JSON từ trình duyệt -> dict chỉ gồm khoá ACT_KEYS (chuỗi), hoặc None nếu không hợp lệ. Giá trị chưa được tin."""
    try:
        d = json.loads(raw or "")
    except (TypeError, ValueError):
        return None
    if not isinstance(d, dict) or d.get("act") not in ACTS:
        return None
    return {k: (d.get(k) if isinstance(d.get(k), str) else "") for k in ACT_KEYS}


# ---------- khung "Đẩy lên CVAT" trong tab Rà soát ----------
def push_panel(gr, demo, store, ctx):
    """Dựng khung Đẩy lên CVAT TRONG ngữ cảnh hiện tại (cột phải, dưới nút Xong). Trả hàm hook(event) để chạy lại khung sau mỗi sự kiện rà,
    và (hàm làm mới, danh sách output) để tab.select gọi."""
    job, dj = ctx.push_job, ctx.del_job
    pending = ctx.push_pending

    panel = gr.HTML(elem_id="push-panel", apply_default_css=False)
    b_push = gr.Button("Đẩy lên CVAT", elem_id="btn-push", interactive=False)
    msg = gr.HTML(elem_id="push-msg", apply_default_css=False)
    prog = gr.HTML(elem_id="push-prog", apply_default_css=False)
    log_tb = gr.Textbox(label="Log đẩy lên CVAT (đã lọc token)", lines=6, max_lines=12, interactive=False, autoscroll=True,
                        elem_id="push-log", visible=False)
    b_cancel = gr.Button("Huỷ", variant="stop", elem_id="push-cancel", visible=False)
    result = gr.HTML(elem_id="push-result", apply_default_css=False)
    token_tb = gr.Textbox(visible="hidden", elem_id="push-token")
    with gr.Column(visible=False, elem_id="push-confirm", elem_classes=["m28-modal"]) as modal:
        with gr.Column(elem_classes=["m28-modal-box"]):
            confirm_body = gr.HTML(elem_id="push-confirm-body", apply_default_css=False)
            with gr.Row(elem_classes=["m28-modal-btns"]):
                b_ok = gr.Button("Đẩy lên CVAT", variant="primary", elem_id="push-confirm-ok")
                b_no = gr.Button("Huỷ", elem_id="push-confirm-cancel")
    timer = gr.Timer(1.0, active=False)
    outs = [panel, b_push, msg, prog, log_tb, b_cancel, result, timer]
    run = os.path.basename(os.path.normpath(store.run_dir))

    def any_running():
        return ctx.push_job.running or ctx.del_job.running or ctx.job.running

    def model():
        return day_cvat.push_model(store.run_dir, store.reviewer, ctx.project_root, remaining=store.progress()["remaining"],
                                   environ=os.environ, job_running=any_running())

    def render(note=""):
        m = model()
        snap = job.snapshot()
        mine = snap["run"] == run and snap["state"] != "chua"
        other = ""
        for j, what in ((job, "Đang đẩy"), (dj, "Đang xoá task của")):
            s = j.snapshot()
            if s["state"] == "dang_chay" and s["run"] != run:
                other = box(f"{what} lượt {s['run']}: xem tab Các đợt.", "info")
        res = ""
        if mine and snap["state"] == "loi":
            res = day_cvat.error_html(snap, dot_anh.read_push(store.run_dir), run)
        elif mine and snap["state"] == "da_huy":
            res = day_cvat.cancelled_html(dot_anh.read_push(store.run_dir), run)
        running = snap["state"] == "dang_chay" and snap["run"] == run
        lines = "\n".join(snap["lines"]) if mine else ""
        return (day_cvat.panel_html(m), gr.update(interactive=m["enabled"] and not running, visible=m["kind"] != "done" and not running),
                (note and box(note, "warn")) or other, day_cvat.progress_html(snap) if mine else "",
                gr.update(value=lines, visible=bool(lines)), gr.update(visible=running, interactive=running and not snap.get("cancelling")),
                res, gr.Timer(active=job.running))

    def on_refresh():
        return render()

    def on_click():
        m = model()
        if ctx.closing:
            return render(nap_anh.CLOSING_MSG) + (gr.update(visible=False), "", "")
        if not m["enabled"]:
            gr.Warning(m["reason"] or "Chưa đẩy được.", title="Chưa đẩy được")
            return render(m["reason"]) + (gr.update(visible=False), "", "")
        it = pending.open(kind="push", run=run)
        return render() + (gr.update(visible=True), day_cvat.confirm_html(m), it["token"])

    def on_confirm(token):
        it = pending.take(token)
        close = (gr.update(visible=False), "", "")
        if ctx.closing:
            return render(nap_anh.CLOSING_MSG) + close
        if it is None or it.get("run") != run:
            return render("Yêu cầu xác nhận đã cũ hoặc không còn hiệu lực: bấm Đẩy lên CVAT lại.") + close
        m = model()
        if not m["enabled"]:
            return render(m["reason"] or "Chưa đẩy được.") + close
        if ctx.switch_to is not None:
            return render("Trang đang chuyển sang đợt khác.") + close
        try:
            job.start(run, ctx.runs_root, ctx.project_root, store.reviewer, m["task"])
        except RunError as e:
            return render(str(e)) + close
        return render() + close

    def on_dismiss():
        pending.cancel()
        return render() + (gr.update(visible=False), "", "")

    def on_job_cancel():
        job.cancel()
        return render("Đã huỷ việc đẩy lên CVAT.")

    opts = dict(show_progress="hidden", api_visibility="private", concurrency_limit=1)
    modal_outs = outs + [modal, confirm_body, token_tb]
    b_push.click(on_click, None, modal_outs, **dict(opts, concurrency_id="push"))
    b_ok.click(on_confirm, [token_tb], modal_outs, **dict(opts, concurrency_id="push"))
    b_no.click(on_dismiss, None, modal_outs, **dict(opts, concurrency_id="push"))
    b_cancel.click(on_job_cancel, None, outs, **dict(opts, concurrency_id="push_huy"))
    timer.tick(on_refresh, None, outs, **dict(opts, concurrency_id="push_tick"))
    demo.load(on_refresh, None, outs, **dict(opts, concurrency_id="push_view"))

    def hook(ev):
        ev.then(on_refresh, None, outs, **dict(opts, concurrency_id="push_view"))
    return hook, on_refresh, outs, opts


# ---------- tab "Các đợt" ----------
def dot_tab(gr, demo, store, ctx, deps):
    """Dựng NỘI DUNG tab Các đợt (gọi trong `with gr.Tab(...)`). deps: dict(Store, switch_js, run_name). Trả (hàm làm mới, outputs, opts)
    để tab.select làm mới danh sách."""
    Store, switch_js, run_name = deps["Store"], deps["switch_js"], deps["run_name"]
    pending = ctx.dot_pending
    active_dir = store.run_dir if store is not None else None
    reviewer = ctx.reviewer

    with gr.Row():
        gr.HTML('<div class="nap-note">Mỗi <b>đợt</b> là một lượt nạp ảnh (tên do bạn đặt hoặc NAP_xxx). Xoá ở đây là <b>xoá mềm</b> '
                '(thùng rác, khôi phục được); xoá ảnh/đợt cục bộ <b>không</b> xoá gì trên CVAT.</div>', elem_id="dot-intro", apply_default_css=False)
        b_refresh = gr.Button("Làm mới", elem_id="dot-refresh", size="sm")
    job_html = gr.HTML(elem_id="dot-job", apply_default_css=False)
    msg = gr.HTML(elem_id="dot-msg", apply_default_css=False)
    root = gr.HTML(elem_id="dot-root", apply_default_css=False)
    act_tb = gr.Textbox(visible="hidden", elem_id="dot-act")
    act_go = gr.Button(visible="hidden", elem_id="dot-act-go")
    target = gr.Textbox(visible="hidden", elem_id="dot-target")
    token_tb = gr.Textbox(visible="hidden", elem_id="dot-modal-token")
    ses = gr.State(None)
    timer = gr.Timer(1.0, active=False)
    with gr.Column(visible=False, elem_id="dot-modal", elem_classes=["m28-modal"]) as modal:
        with gr.Column(elem_classes=["m28-modal-box"]):
            body = gr.HTML(elem_id="dot-modal-body", apply_default_css=False)
            typed = gr.Textbox(label="Gõ lại đúng tên để xác nhận", elem_id="dot-modal-typed", visible=False, max_lines=1)
            check = gr.Checkbox(label="Tôi hiểu nhãn đã sửa trong CVAT sẽ mất", elem_id="dot-modal-check", visible=False)
            with gr.Row(elem_classes=["m28-modal-btns"]):
                b_ok = gr.Button("Xoá", variant="stop", elem_id="dot-modal-ok")
                b_no = gr.Button("Huỷ", elem_id="dot-modal-cancel")

    outs = [root, ses, msg, job_html, timer, modal, body, typed, check, b_ok, token_tb, target]
    opts = dict(show_progress="hidden", api_visibility="private", concurrency_limit=1)

    def new_ses():
        return dict(view="list", run=None, page=0, was_running=False)

    def ensure(s):
        return s if isinstance(s, dict) and "view" in s else new_ses()

    def any_running():
        return ctx.push_job.running or ctx.del_job.running or ctx.job.running

    def is_active(run):
        return bool(active_dir) and os.path.realpath(os.path.join(ctx.runs_root, run)) == os.path.realpath(active_dir)

    def job_banner():
        out = []
        for j, what in ((ctx.push_job, "Đẩy lên CVAT"), (ctx.del_job, "Xoá task trên CVAT")):
            s = j.snapshot()
            if s["state"] == "chua":
                continue
            out.append(day_cvat.progress_html(s, what))
            if s["state"] == "loi":
                out.append(day_cvat.error_html(s, dot_anh.read_push(s["run_dir"]) if s["run_dir"] else None, s["run"]))
            elif s["state"] == "da_huy":
                out.append(day_cvat.cancelled_html(dot_anh.read_push(s["run_dir"]) if s["run_dir"] else None, s["run"]))
        return "".join(out[-3:])

    def build_root(s):
        if s["view"] == "grid" and s["run"]:
            try:
                run_dir = dot_anh.valid_run(ctx.runs_root, s["run"])
            except RunError:
                s["view"], s["run"] = "list", None
            else:
                info = dot_anh.run_info(run_dir, reviewer)
                return dot_anh.grid_html(info, dot_anh.image_rows(run_dir, reviewer), s["page"], dot_anh.list_trash(run_dir),
                                         active=is_active(s["run"]))
        infos = [dot_anh.run_info(os.path.join(ctx.runs_root, r), reviewer) for r in dot_anh.list_runs(ctx.runs_root)]
        ready = {}
        for i in infos:
            if i["state"] == dot_anh.S_DONE and not (i["push"] or {}).get("trang_thai") == "xong":
                ready[i["name"]] = day_cvat.push_model(os.path.join(ctx.runs_root, i["name"]), reviewer, ctx.project_root,
                                                       job_running=any_running())["enabled"]
        return dot_anh.list_html(infos, run_name(active_dir) if active_dir else None, dot_anh.list_deleted_runs(ctx.runs_root), ready)

    NO_MODAL = (gr.update(visible=False), "", gr.update(visible=False, value=""), gr.update(visible=False, value=False),
                gr.update(interactive=True), "")

    def render(s, note="", level="info", modal=None, switch=""):
        s = ensure(s)
        s["was_running"] = any_running()                    # lần tick đầu thấy việc đã xong thì vẫn vẽ lại danh sách
        if modal is None:
            m = NO_MODAL
        else:
            m = (gr.update(visible=True), modal["body"], gr.update(visible=modal.get("typed", False), value="", label=modal.get("typed_label", "")),
                 gr.update(visible=modal.get("check", False), value=False),
                 gr.update(interactive=modal.get("ok_enabled", True), value=modal.get("ok_label", "Xoá")), modal["token"])
        return (build_root(s), s, box(note, level), job_banner(), gr.Timer(active=any_running()), *m, switch)

    def modal_for(kind, **kw):
        it = pending.open(kind=kind, **kw)
        return it

    def on_load_or_refresh(s):
        return render(s)

    def on_tick(s):
        s = ensure(s)
        running = any_running()
        was = s.get("was_running", False)
        s["was_running"] = running
        if was and not running:                             # việc vừa xong: vẽ lại danh sách
            return render(s)
        return (gr.update(), s, gr.update(), job_banner(), gr.Timer(active=running), gr.update(), gr.update(), gr.update(), gr.update(),
                gr.update(), gr.update(), gr.update())

    def run_of(a):
        """Tên đợt hợp lệ từ hành động (phải nằm trong danh sách đợt do server tính) -> đường dẫn."""
        return dot_anh.valid_run(ctx.runs_root, a["run"])

    def do_act(raw, s):
        s = ensure(s)
        a = parse_action(raw)
        if a is None:
            return render(s, "Hành động không hợp lệ (bỏ qua).", "warn")
        if ctx.closing and a["act"] not in ("back", "open", "page"):      # trang đang đóng: chỉ xem được, không ghi/đẩy/chuyển gì
            return render(s, nap_anh.CLOSING_MSG, "warn")
        try:
            return _dispatch(a, s)
        except RunError as e:
            gr.Warning(str(e), title="Chưa làm được")
            return render(s, str(e), "warn")

    def _dispatch(a, s):
        act = a["act"]
        if act == "back":
            s.update(view="list", run=None, page=0)
            return render(s)
        if act == "open":
            run_of(a)
            s.update(view="grid", run=a["run"], page=0)
            return render(s)
        if act == "page":
            run_of(a)
            try:
                s["page"] = max(0, int(a["page"]))
            except ValueError:
                s["page"] = 0
            return render(s)
        if act == "ra":
            return _switch(a, s)
        if act == "push":
            return _ask_push(a, s)
        if act == "delimg":
            return _ask_delimg(a, s)
        if act == "restore":
            return _restore(a, s)
        if act == "empty":
            run_dir = run_of(a)
            n = len(dot_anh.list_trash(run_dir))
            if not n:
                return render(s, "Thùng rác của đợt đang trống.", "info")
            it = modal_for("empty", run=a["run"])
            body = (f'<div class="modal-title modal-danger" id="dot-modal-title">Dọn thùng rác của đợt {_e(a["run"])}?</div>'
                    f'<div class="nap-box nap-err" role="alert"><b>Xoá vĩnh viễn {n} ảnh trong thùng rác, KHÔNG khôi phục được.</b></div>'
                    '<div class="nap-note">Tên các ảnh này vẫn bị loại khỏi đợt (nằm trong excluded.txt).</div>')
            return render(s, modal=dict(body=body, token=it["token"], ok_label="Dọn vĩnh viễn"))
        if act == "delrun":
            return _ask_delrun(a, s)
        if act == "deltask":
            return _ask_deltask(a, s)
        if act == "restore_run":
            name = dot_anh.restore_run(ctx.runs_root, a["entry"])
            return render(s, f"Đã khôi phục đợt {name}.", "ok")
        if act == "purge_run":
            return _ask_purge(a, s)
        return render(s)

    def _switch(a, s):
        run_dir = run_of(a)
        if ctx.switch_to is not None:
            return render(s, "Đang chuyển sang đợt khác…", "info")
        if any_running():
            raise RunError("Đang có việc chạy (chuẩn bị, đẩy hoặc xoá task): chờ xong rồi chuyển đợt.")
        if is_active(a["run"]):
            raise RunError(f"Đợt {a['run']} đang mở ở tab Rà soát.")
        if not os.path.isfile(os.path.join(run_dir, "flags", "flags.json")):
            raise RunError(f"Đợt {a['run']} chưa có flags.json (prepare chưa xong): chạy lại ở tab Nạp ảnh hoặc bằng python tool\\m28.py prepare.")
        if dot_anh.run_busy(run_dir):
            raise RunError(f"Đợt {a['run']} đang có việc chạy: chờ xong.")
        new_store = Store(run_dir, reviewer)                                   # dựng TRƯỚC: lỗi thì báo ở đây, chưa đóng gì
        if not ctx.begin_switch((run_dir, new_store)):
            raise RunError(nap_anh.CLOSING_MSG)
        threading.Timer(0.8, lambda: demo.close(verbose=False)).start()
        return render(s, f"Đang chuyển sang đợt {a['run']}: trang mất kết nối 1–3 giây rồi tự tải lại.", "ok", switch="Rà soát M28 · " + a["run"])

    def _ask_push(a, s):
        run_dir = run_of(a)
        m = day_cvat.push_model(run_dir, reviewer, ctx.project_root, job_running=any_running())
        if m["kind"] == "done":
            raise RunError("Đợt này đã đẩy lên CVAT rồi.")
        if is_active(a["run"]):
            m = day_cvat.push_model(run_dir, reviewer, ctx.project_root, remaining=store.progress()["remaining"], job_running=any_running())
        if not m["enabled"]:
            raise RunError(m["reason"] or "Chưa đẩy được.")
        it = modal_for("push", run=a["run"])
        return render(s, modal=dict(body=day_cvat.confirm_html(m), token=it["token"], ok_label="Đẩy lên CVAT", ok_enabled=True))

    def _ask_delimg(a, s):
        run_dir = run_of(a)
        names = dot_anh.image_names(run_dir)
        if a["name"] not in names:
            raise RunError(f"Ảnh {a['name']!r} không có trong đợt (có thể đã xoá): bấm Làm mới.")
        busy = dot_anh.run_busy(run_dir)
        if busy:
            raise RunError(f"Đợt {a['run']} đang có việc chạy ({busy[0]}): chờ xong rồi xoá.")
        if is_active(a["run"]) and store is not None and len(store.faces) <= 1 and a["name"] in store.by_name:
            raise RunError("Đợt đang rà chỉ còn một mặt: không xoá được (hàng đợi không được rỗng). Chuyển sang đợt khác rồi xoá cả đợt.")
        rows = {r["name"]: r for r in dot_anh.image_rows(run_dir, reviewer)}
        r = rows[a["name"]]
        ps = dot_anh.read_push(run_dir) or {}
        pushed = ps.get("trang_thai") in ("xong", "da_tao", "da_nhap")
        it = modal_for("delimg", run=a["run"], name=a["name"], decision=r["status"], pushed=ps.get("task") if pushed else None)
        warn = (f'<div class="nap-box nap-err" role="alert"><b>Xoá ở đây KHÔNG xoá ảnh trong task {_e(ps.get("task"))} trên CVAT.</b> '
                'Ảnh vẫn còn trong task đó; muốn bỏ khỏi CVAT phải xoá trong CVAT.</div>') if pushed else ""
        body = (f'<div class="modal-title modal-danger" id="dot-modal-title">Xoá ảnh {_e(a["name"])}?</div>'
                '<table class="m28-info">'
                f'<tr><th>Tên ảnh</th><td><b>{_e(a["name"])}</b></td></tr><tr><th>Tên gốc</th><td>{_e(r["orig"])}</td></tr>'
                f'<tr><th>Đợt</th><td>{_e(a["run"])}</td></tr>'
                f'<tr><th>Quyết định hiện tại</th><td>{_e(dot_anh.DECISION_VI.get(r["status"], r["status_text"]))}</td></tr></table>'
                '<div class="nap-note"><b>Hậu quả:</b> ảnh rời khỏi hàng đợi rà và khỏi lần push sau; chuyển vào thùng rác của đợt, '
                f'<b>khôi phục được</b>.</div>{warn}')
        return render(s, modal=dict(body=body, token=it["token"], ok_label="Xoá ảnh"))

    def _restore(a, s):
        run_dir = run_of(a)
        res = dot_anh.restore_image(run_dir, a["trash"], reviewer=reviewer)
        if is_active(a["run"]) and store is not None:
            store.reload()
        note = f"Đã khôi phục ảnh {res['ten']}."
        if res["mo_lai"]:
            note += " Ảnh này chưa có quyết định nên lượt có lại mặt chưa rà (phải bấm Xong lại)."
        return render(s, note, "ok")

    def _ask_delrun(a, s):
        run_dir = run_of(a)
        if is_active(a["run"]):
            raise RunError(f"Đợt {a['run']} đang mở ở tab Rà soát: chuyển sang đợt khác rồi mới xoá.")
        busy = dot_anh.run_busy(run_dir)
        if busy:
            raise RunError(f"Đợt {a['run']} đang có việc chạy ({busy[0]}): chờ xong rồi xoá.")
        ps = dot_anh.read_push(run_dir) or {}
        pushed = ps.get("trang_thai") in ("xong", "da_tao", "da_nhap")
        it = modal_for("delrun", run=a["run"])
        warn = (f'<div class="nap-box nap-err" role="alert"><b>Xoá đợt ở đây KHÔNG xoá task {_e(ps.get("task"))} trên CVAT.</b> '
                'Muốn xoá task phải dùng nút Xoá task trên CVAT trước (hoặc xoá trong CVAT).</div>') if pushed else ""
        body = (f'<div class="modal-title modal-danger" id="dot-modal-title">Xoá cả đợt {_e(a["run"])}?</div>'
                '<div class="nap-note"><b>Hậu quả:</b> cả thư mục đợt (ảnh, nhãn nháp, kết quả rà) chuyển vào <code>runs\\_trash</code>, '
                f'<b>khôi phục được</b> nếu tên {_e(a["run"])} chưa bị dùng lại. Không đụng gì trên CVAT.</div>{warn}')
        return render(s, modal=dict(body=body, token=it["token"], typed=True, typed_label=f"Gõ lại đúng tên đợt ({a['run']}), phân biệt hoa thường",
                                    ok_label="Xoá cả đợt", ok_enabled=False))

    def _ask_deltask(a, s):
        run_dir = run_of(a)
        m = day_cvat.delete_model(run_dir, ctx.project_root, environ=os.environ, job_running=any_running())
        if not m["ok"]:
            raise RunError(m["reason"] or "Chưa xoá task được.")
        it = modal_for("deltask", run=a["run"], task=m["task"])
        return render(s, modal=dict(body=day_cvat.delete_confirm_html(m), token=it["token"], typed=True, check=True,
                                    typed_label=f"Gõ lại ĐÚNG tên task ({m['task']}), phân biệt hoa thường",
                                    ok_label="Xoá task trên CVAT", ok_enabled=False))

    def _ask_purge(a, s):
        found = {d["entry"]: d for d in dot_anh.list_deleted_runs(ctx.runs_root)}
        if a["entry"] not in found:
            raise RunError("Mục này không còn trong thùng rác đợt: bấm Làm mới.")
        it = modal_for("purge_run", entry=a["entry"])
        body = (f'<div class="modal-title modal-danger" id="dot-modal-title">Xoá vĩnh viễn đợt {_e(found[a["entry"]]["ten"])}?</div>'
                '<div class="nap-box nap-err" role="alert"><b>Xoá hẳn khỏi ổ đĩa, KHÔNG khôi phục được</b> (ảnh, nhãn nháp, kết quả rà của đợt).</div>')
        return render(s, modal=dict(body=body, token=it["token"], ok_label="Xoá vĩnh viễn"))

    def on_typed(typed_v, check_v, token):
        it = pending.item
        if not it or token != it.get("token"):
            return gr.update()                                    # sự kiện của hộp cũ: không đổi gì (server vẫn kiểm lại khi xác nhận)
        if it["kind"] == "delrun":
            return gr.update(interactive=typed_v == it["run"])
        if it["kind"] == "deltask":
            return gr.update(interactive=typed_v == it["task"] and bool(check_v))
        return gr.update(interactive=True)

    def on_ok(typed_v, check_v, token, s):
        s = ensure(s)
        if ctx.closing:
            pending.cancel()
            return render(s, nap_anh.CLOSING_MSG, "warn")
        it = pending.item
        if it and token == it.get("token") and it["kind"] == "delrun" and typed_v != it["run"]:
            return render(s, "Tên gõ lại chưa đúng: chưa xoá gì.", "warn")
        if it and token == it.get("token") and it["kind"] == "deltask" and not (typed_v == it["task"] and check_v):
            return render(s, "Chưa gõ đúng tên task hoặc chưa tick ô xác nhận: chưa xoá gì.", "warn")
        it = pending.take(token)
        if it is None:
            return render(s, "Yêu cầu xác nhận đã cũ hoặc không còn hiệu lực: không xoá gì, hãy thử lại.", "warn")
        try:
            return _execute(it, typed_v, s)
        except RunError as e:
            gr.Warning(str(e), title="Chưa làm được")
            return render(s, str(e), "warn")

    def _execute(it, typed_v, s):
        kind = it["kind"]
        if kind == "delimg":
            run_dir = run_of(it)
            man = dot_anh.soft_delete_image(run_dir, it["name"], reviewer=reviewer, decision=it.get("decision", ""), pushed_task=it.get("pushed"))
            if is_active(it["run"]) and store is not None:
                store.exclude(it["name"])
            return render(s, f"Đã chuyển ảnh {man['ten']} vào thùng rác của đợt (khôi phục được).", "ok")
        if kind == "empty":
            n = dot_anh.empty_trash(run_of(it))
            return render(s, f"Đã dọn thùng rác: xoá vĩnh viễn {n} ảnh.", "ok")
        if kind == "delrun":
            entry = dot_anh.delete_run(ctx.runs_root, it["run"], typed_v, active_run=active_dir)
            s.update(view="list", run=None, page=0)
            return render(s, f"Đã chuyển đợt {it['run']} vào runs\\_trash\\{entry} (khôi phục được ở khu Đợt đã xoá).", "ok")
        if kind == "purge_run":
            name = dot_anh.purge_run(ctx.runs_root, it["entry"])
            return render(s, f"Đã xoá vĩnh viễn đợt {name}.", "ok")
        if kind == "push":
            run_dir = run_of(it)
            rem = store.progress()["remaining"] if is_active(it["run"]) and store is not None else None
            m = day_cvat.push_model(run_dir, reviewer, ctx.project_root, remaining=rem, job_running=any_running())
            if not m["enabled"]:
                raise RunError(m["reason"] or "Chưa đẩy được.")
            ctx.push_job.start(it["run"], ctx.runs_root, ctx.project_root, reviewer, m["task"])
            return render(s, f"Đang đẩy đợt {it['run']} lên CVAT (theo dõi ở khung phía trên).", "ok")
        if kind == "deltask":
            run_dir = run_of(it)
            m = day_cvat.delete_model(run_dir, ctx.project_root, environ=os.environ, job_running=any_running())
            if not m["ok"] or m["task"] != it["task"] or typed_v != it["task"]:
                raise RunError(m["reason"] or "Thông tin task đã đổi: không xoá gì, hãy mở lại hộp xoá task.")
            ctx.del_job.start(it["run"], ctx.runs_root, ctx.project_root, m["task"])
            return render(s, f"Đang xoá task {m['task']} trên CVAT (theo dõi ở khung phía trên).", "ok")
        raise RunError("Yêu cầu không rõ.")

    def on_dismiss(s):
        pending.cancel()
        return render(s)

    do = dict(opts, concurrency_id="dot")
    b_refresh.click(on_load_or_refresh, [ses], outs, **do)
    act_go.click(do_act, [act_tb, ses], outs, **do).then(None, [target], None, js=switch_js)
    b_ok.click(on_ok, [typed, check, token_tb, ses], outs, **do).then(None, [target], None, js=switch_js)
    b_no.click(on_dismiss, [ses], outs, **do)
    typed.change(on_typed, [typed, check, token_tb], [b_ok], **dict(opts, concurrency_id="dot_typed"))
    check.change(on_typed, [typed, check, token_tb], [b_ok], **dict(opts, concurrency_id="dot_typed"))
    timer.tick(on_tick, [ses], outs, **dict(opts, concurrency_id="dot_tick"))
    return on_load_or_refresh, ses, outs, dict(opts, concurrency_id="dot")
