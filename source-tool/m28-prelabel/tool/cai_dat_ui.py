"""Tab "Cài đặt" của trang rà soát M28 (Gradio): CVAT (link, token, tổ chức, Nhớ trên máy này, Thử kết nối, Quên token), người rà, đường dẫn
(thư mục ảnh, file face_landmarker.task), cờ low_conf (t_flip) và pipeline (chỉ đọc).

Không import gradio ở đầu module (gradio chỉ đến từ tham số `gr`, như dot_ui.py); phần dựng HTML thuần ở đầu file để test không cần trình duyệt.
Logic nằm ở cai_dat.py; tab này chỉ nối với Gradio. An toàn:
  * Token chỉ đi MỘT chiều vào server qua ô Token (type="password") của handler Gradio sẵn có (api_visibility="private", cổng 127.0.0.1);
    không bao giờ ở gr.State, value của Textbox, HTML, elem_classes, data-*, giá trị trả về của handler. Về trình duyệt chỉ có dạng che.
  * Mọi handler bọc try/except: lỗi lạ chỉ hiện thông báo đã lọc token, traceback (đã lọc) chỉ ra console.
  * Handler GHI từ chối khi trang đang đóng (ctx.closing); Lưu / Quên token còn từ chối khi đang đẩy hay xoá task trên CVAT.
  * Mỗi lần ghi tăng `rev`; tab trình duyệt giữ `rev` cũ bị từ chối nhẹ nhàng và tải lại (nhiều tab trình duyệt cùng mở).
  * Thử kết nối chạy bằng tiến trình con (cai_dat.test_connection): trang vẫn không gọi mạng.
  * "Chạy kiểm tra nhanh CVAT" chạy tool/cvat_smoke.py bằng tiến trình con (nap_anh.SmokeJob, token qua môi trường của nó): tạo task demo-smoke
    giả, nhập nhãn, xuất lại, xoá. Có hộp xác nhận (Huỷ mặc định), khoá chéo với đẩy/xoá task, Lưu/Quên token từ chối khi đang chạy.
"""
import functools
import html
import os
import sys
import time
import traceback

import cai_dat
import day_cvat
import dot_anh
import nap_anh
from m28core import cvat_io
from nap_anh import RunError

KIND_VI = {"bad_url": "sai link", "bad_token": "sai token", "server_down": "server tắt hoặc sai link", "version_mismatch": "khác phiên bản",
           "redirect": "link bị chuyển hướng", "timeout": "server không trả lời", "no_sdk": "thiếu cvat-sdk", "other": "lỗi khác"}

CSS = """
/* ---------- tab Cài đặt ---------- */
#tab-caidat { padding: 8px 0 0 !important; max-width: 920px; margin: 0 auto; width: 100%; gap: 12px; }
#tab-caidat .cd-sec { gap: 8px; padding: 12px 14px; border-radius: 12px; border: 1px solid var(--border-color-primary);
  background: var(--block-background-fill); }
.cd-sec-title { font-size: 17px; font-weight: 800; }
#cd-cvat-status, #cd-cvat-msg, #cd-reviewer-info, #cd-reviewer-msg, #cd-paths-info, #cd-images-msg, #cd-model-msg, #cd-tflip-info, #cd-tflip-msg,
#cd-pipeline, #cd-remember-note, #cd-top, #cd-forget-body, #cd-tflip-body { padding: 0 !important; }
#cd-cvat-msg:not(:has(.html-container > div > *)), #cd-reviewer-msg:not(:has(.html-container > div > *)), #cd-images-msg:not(:has(.html-container > div > *)),
#cd-model-msg:not(:has(.html-container > div > *)), #cd-tflip-msg:not(:has(.html-container > div > *)) { display: none; }
.cd-chip { display: inline-flex; align-items: center; gap: 6px; padding: 3px 12px; border-radius: 999px; font-size: 14px; font-weight: 800;
  border: 1px solid var(--cc, #9ca3af); background: color-mix(in srgb, var(--cc, #9ca3af) 16%, transparent); overflow-wrap: anywhere; }
.cd-chip.st-ok { --cc: #16a34a; } .cd-chip.st-err { --cc: #dc2626; } .cd-chip.st-idle, .cd-chip.st-none { --cc: #9ca3af; }
.cd-kv { width: 100%; border-collapse: collapse; font-size: 14px; margin-top: 6px; }
.cd-kv th { text-align: left; font-weight: 600; color: var(--body-text-color-subdued); width: 1%; white-space: nowrap; padding: 4px 12px 4px 0;
  vertical-align: top; border: 0; background: transparent; }
.cd-kv td { padding: 4px 0; vertical-align: top; border: 0; background: transparent; overflow-wrap: anywhere; word-break: break-word; }
.cd-kv code, .cd-path { font-family: var(--font-mono); font-size: 12.5px; overflow-wrap: anywhere; word-break: break-all; }
#cd-token-row { align-items: flex-end; gap: 8px; flex-wrap: nowrap; }
#cd-token-row #cd-eye { flex: 0 0 auto !important; min-width: 0 !important; width: auto !important; }
#cd-cvat-btns, #cd-reviewer-btns, #cd-images-btns, #cd-model-btns, #cd-tflip-btns { gap: 8px; flex-wrap: wrap; }
#cd-cvat-btns button, #cd-reviewer-btns button, #cd-images-btns button, #cd-model-btns button, #cd-tflip-btns button { min-height: 42px; font-weight: 800;
  min-width: 110px !important; flex: 0 1 auto !important; }
#cd-save:not(:disabled), #cd-forget-ok:not(:disabled) { color: #fff !important; }
#cd-save:not(:disabled) { background: #16a34a !important; border-color: #15803d !important; }
#cd-forget-ok:not(:disabled) { background: #dc2626 !important; border-color: #b91c1c !important; }
#cd-tflip-ok:not(:disabled) { background: #d97706 !important; border-color: #b45309 !important; color: #fff !important; }
.m28-msg.m-err { border-left-color: #dc2626; }
.sm-tbl { width: 100%; border-collapse: collapse; font-size: 13.5px; margin-top: 6px; }
.sm-tbl th { text-align: left; padding: 4px 8px; border-bottom: 2px solid var(--border-color-primary); white-space: nowrap; }
.sm-tbl td { padding: 4px 8px; vertical-align: top; border-bottom: 1px solid var(--border-color-primary); overflow-wrap: anywhere; }
.sm-tbl .sm-sub td { border-bottom: 0; padding-top: 0; color: var(--body-text-color-subdued); }
.sm-kq { font-weight: 800; white-space: nowrap; } .sm-kq.sm-dat { color: #16a34a; } .sm-kq.sm-hong { color: #dc2626; } .sm-kq.sm-bo { color: #6b7280; }
#cd-smoke-msg:not(:has(.html-container > div > *)), #cd-smoke-result:not(:has(.html-container > div > *)), #cd-smoke-prog:not(:has(.html-container > div > *)) { display: none; }
#cd-smoke-msg, #cd-smoke-prog, #cd-smoke-result, #cd-smoke-body { padding: 0 !important; }
.cd-note { font-size: 13.5px; line-height: 1.55; color: var(--body-text-color-subdued); overflow-wrap: anywhere; }
.cd-note code { font-family: var(--font-mono); font-size: 12.5px; }
@media (max-width: 600px) {
  #cd-token-row { flex-wrap: wrap; }
  #cd-cvat-btns button, #cd-reviewer-btns button, #cd-images-btns button, #cd-model-btns button, #cd-tflip-btns button { flex: 1 1 100% !important; }
}
"""

EYE_JS = """() => { const el = document.querySelector('#cd-token input'); if (el) { el.type = (el.type === 'password') ? 'text' : 'password'; } }"""
HIDE_JS = """() => { const el = document.querySelector('#cd-token input'); if (el) { el.type = 'password'; } }"""


def _e(x):
    return html.escape(str(x), quote=True)


def msg_html(text, level="info"):
    return f'<div class="m28-msg m-{level}" role="status">{_e(text)}</div>' if text else ""


def box_html(level, title, lines=()):
    """Khung nap-box (ok | warn | err) với tiêu đề đậm và danh sách dòng. Mọi chuỗi được escape."""
    cls = {"ok": "nap-ok", "warn": "nap-warn", "err": "nap-err"}.get(level, "")
    items = "".join(f"<li>{_e(x)}</li>" for x in lines)
    return (f'<div class="nap-box {cls}" role="{"alert" if level == "err" else "status"}"><b>{_e(title)}</b>'
            + (f"<ul>{items}</ul>" if items else "") + "</div>")


def check_html(res):
    """Kết quả check_images_dir / check_model thành khung ok/warn/err."""
    title = {"ok": "Ổn", "warn": "Dùng được, nhưng cần xem lại", "err": "Chưa dùng được"}[res["level"]]
    return box_html(res["level"], title, [res["path"]] * bool(res["path"]) + res["lines"])


def test_html(res, project, typed=False):
    """Kết quả thử kết nối. `project` là tên project trong pipeline.json. typed=True: giá trị đang gõ, chưa Lưu."""
    extra = ["Đây là giá trị đang gõ trong ô, chưa bấm Lưu."] if typed else []
    if res["ok"]:
        pf = res.get("project_found")
        proj = (f"project {project}: đã có (id {res.get('project_id')})" if pf
                else f"project {project}: chưa có (tool tạo khi đẩy lần đầu)")
        lines = [f"CVAT phiên bản {res['server_version']}", f"Đăng nhập bằng token: tài khoản {res['username'] or '?'}", proj]
        if res.get("org"):
            lines.append(f"Tổ chức: {res['org']}")
        return box_html("ok", "Kết nối được", lines + extra)
    return box_html("err", f"Chưa kết nối được ({KIND_VI.get(res['error_kind'], 'lỗi khác')})", [res["message"]] + extra)


def status_html(snap, pipe):
    """Dòng trạng thái CVAT + bảng giá trị (token chỉ dạng che). snap = cai_dat.Settings.snapshot()."""
    t = snap["test"]
    if not snap["url"] or not snap["has_token"]:
        chip, cls = "○ Chưa có link/token", "st-none"
    elif t is None:
        chip, cls = "○ Chưa thử", "st-idle"
    elif t["result"]["ok"]:
        chip, cls = f"● Đã kết nối (thử lúc {t['when']})", "st-ok"
    else:
        chip, cls = f"● Lỗi: {KIND_VI.get(t['result']['error_kind'], 'lỗi khác')} (thử lúc {t['when']})", "st-err"
    rows = [("Link", f'<code>{_e(snap["url"])}</code>' if snap["url"] else "(chưa có)"),
            ("Token", (f'<code>{_e(snap["token_mask"])}</code> · {_e(snap["source_label"])}') if snap["has_token"] else "(chưa có)")]
    if snap["url"] and not snap["has_token"]:
        rows[0] = ("Link", f'<code>{_e(snap["url"])}</code> · {_e(snap["source_label"])}')
    if snap["org"]:
        rows.append(("Tổ chức", f'<code>{_e(snap["org"])}</code>'))
    if t and t["result"]["ok"]:
        r = t["result"]
        rows.append(("Server", f"CVAT {_e(r['server_version'])} · tài khoản <b>{_e(r['username'] or '?')}</b> · project {_e(pipe['project'])}: "
                               + (f"đã có (id {_e(r.get('project_id'))})" if r.get("project_found") else "chưa có (tạo khi đẩy lần đầu)")))
    out = [f'<div><span class="cd-chip {cls}" role="status">{_e(chip)}</span></div>',
           "<table class=\"cd-kv\">" + "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows) + "</table>"]
    if snap["dir_error"]:
        out.append(box_html("err", "Không lưu được ra file", [snap["dir_error"]]))
    if snap["file_status"] in ("hong", "khong_doc"):
        out.append(box_html("warn", "File cvat.json " + ("hỏng" if snap["file_status"] == "hong" else "không đọc được"),
                            [f"Đã bỏ qua file này (không hiện nội dung). Bấm Quên token để xoá, hoặc nhập lại rồi bấm Lưu để ghi lại: {snap['file_path']}"]))
    if snap["env"] == "partial" and snap["source"] != "env":
        out.append(f'<div class="cd-note">Biến môi trường trong cmd chỉ có một trong CVAT_URL / CVAT_ACCESS_TOKEN nên không dùng.</div>')
    if snap["source"] == "env":
        out.append('<div class="cd-note">Đang dùng biến môi trường của cmd. Nhập và Lưu ở đây thì chỉ trang này dùng giá trị mới '
                   "(biến trong cmd không đổi).</div>")
    return "".join(out)


def remember_note_html(snap):
    d = snap["dir"] or "(không xác định được thư mục)"
    path = snap["file_path"] or os.path.join(d, cai_dat.FILE_CVAT)
    return (f'<div class="cd-note">Bật thì lưu link, token, tổ chức vào <code class="cd-path">{_e(path)}</code>: file nằm NGOÀI repo, trong hồ sơ của bạn '
            "(không bao giờ vào repo, runs\\, outputs\\). Linux/macOS: quyền chỉ chủ máy (0600). Windows: dựa vào quyền hồ sơ người dùng "
            "(không có 0600 thật, không dùng keyring/DPAPI). Dùng máy chung thì để TẮT hoặc bấm Quên token khi xong.</div>")


def reviewer_info_html(snap, ctx_reviewer, run_name, next_name):
    saved = snap["prefs"]["reviewer"]
    cur = (f"Lượt đang mở: <b>{_e(run_name)}</b>, đang ghi vào <code>triage_{_e(ctx_reviewer)}.csv</code> (tên <b>{_e(ctx_reviewer)}</b>). "
           if run_name else f"Chưa mở lượt nào (tên của trang: <b>{_e(ctx_reviewer)}</b>). ")
    out = [cur + f"Tên mặc định đã lưu: <b>{_e(saved) if saved else '(chưa lưu: dùng tên của trang)'}</b>."]
    if next_name != ctx_reviewer:
        out.append(f"Lượt đang mở vẫn ghi vào <code>triage_{_e(ctx_reviewer)}.csv</code>; từ lượt sau dùng <b>{_e(next_name)}</b>.")
    out.append("Đổi tên KHÔNG áp dụng ngay cho lượt đang mở vì phần rà dở nằm ở file theo tên cũ. Tên mới có hiệu lực ở lượt kế tiếp "
               "(bấm <b>Rà lượt này</b> ở tab Nạp ảnh, hoặc chuyển đợt ở tab Các đợt). Mở lại trang bằng dòng lệnh thì tên là tên trong lệnh.")
    return "".join(f'<div class="cd-note">{x}</div>' for x in out)


def paths_info_html(snap, run="<lượt>"):
    imgs = snap["prefs"]["images_dir"]
    mod = snap["prefs"]["model_path"]
    ex_img = imgs or "<thư mục ảnh>"
    rows = [("Thư mục ảnh", f'<code class="cd-path">{_e(imgs)}</code>' if imgs else "(chưa cài)"),
            ("Model", f'<code class="cd-path">{_e(mod)}</code>' if mod else "(chưa cài: tìm face_landmarker.task như cũ)")]
    cmd = f'python tool\\m28.py prepare --run {run} --list data\\r_list.csv --images "{ex_img}" --box auto'
    return ("<table class=\"cd-kv\">" + "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows) + "</table>"
            '<div class="cd-note">Model đã cài: tab Nạp ảnh dùng nó (thêm <code>--model</code> khi chạy prepare). Thư mục ảnh: khi đẩy một lượt '
            "chạy bằng lệnh mà ảnh gốc không còn ở đường dẫn cũ, trang thêm <code>--images</code> cho lệnh push; ảnh nạp từ tab Nạp ảnh "
            f'không cần.<br>Lệnh gợi ý (cmd): <code class="cd-path">{_e(cmd)}</code></div>')


def fmt_t(v):
    return "chưa đặt (null): mọi cờ = false" if v is None else cai_dat.fmt_vi(v)


def tflip_info_html(info):
    if not info["ok"]:
        return box_html("err", "Không đọc được cấu hình", [info["error"]])
    st = "ĐÃ ĐÓNG BĂNG" if info["frozen"] else "bản nháp (chưa đóng băng)"
    rows = [("t_flip hiện tại", f"<b>{_e(fmt_t(info['t_flip']))}</b>"), ("status của config", f"<code>{_e(info['status'])}</code> · {st}"),
            ("iod_points", "<code>" + _e(", ".join(map(str, info["iod_points"]))) + "</code> (hai điểm đo khoảng cách hai mắt)")]
    return ("<table class=\"cd-kv\">" + "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows) + "</table>"
            '<div class="cd-note">Điểm số của một điểm = độ lệch giữa kết quả ảnh gốc và ảnh lật ÷ khoảng cách hai mắt; lớn hơn t_flip thì điểm bị cờ '
            "low_conf (chấm đỏ). Theo BAO-CAO-CO-LOW-CONF.md, <b>0,0672</b> ứng với cờ khoảng 15% số điểm trên T-dev (~7,5 điểm mỗi mặt), "
            "đề xuất cho họp 12/10. Ghi vào <code>config\\m28_config.json</code>, giữ nguyên mọi trường khác.</div>")


def pipeline_html(pi):
    if not pi["ok"]:
        return box_html("warn", "config\\pipeline.json hỏng, đang dùng giá trị mặc định", [pi["error"]]) + _pipe_table(pi["pipe"])
    return _pipe_table(pi["pipe"], pi["exists"])


def _pipe_table(p, exists=True):
    rows = [("cvat_version", p["cvat_version"]), ("job_size", p["job_size"]), ("project", p["project"]), ("prefix", p["prefix"])]
    return ("<table class=\"cd-kv\">" + "".join(f"<tr><th>{k}</th><td><code>{_e(v)}</code></td></tr>" for k, v in rows) + "</table>"
            + ('<div class="cd-note">Chỉ đọc (config\\pipeline.json). ' if exists else '<div class="cd-note">Chưa có config\\pipeline.json, dùng mặc định. ')
            + "Task tool tạo luôn bắt đầu bằng <code>" + _e(p["prefix"]) + "</code>.</div>")


def tflip_confirm_html(old, new, images_dir):
    img = images_dir or "<thư mục ảnh>"
    cmd1 = "python tool\\m28.py prepare --run <lượt> --images runs\\<lượt>\\inbox --box auto --force flags autoqc overlays"
    cmd2 = f'python tool\\m28.py prepare --run <lượt> --list <danh sách> --images "{img}" --box auto --force flags autoqc overlays'
    return ('<div class="modal-title" id="cd-tflip-title">Đổi t_flip?</div>'
            f'<table class="m28-info"><tr><th>Từ</th><td><b>{_e(fmt_t(old))}</b></td></tr><tr><th>Thành</th><td><b>{_e(fmt_t(new))}</b></td></tr></table>'
            '<div class="nap-box nap-warn" role="alert"><b>P2 chốt sau họp 12/10, file đóng băng 12/10; đổi giữa chừng làm các lượt đã chạy lệch nhau.</b> '
            "Cờ của lượt cũ chỉ tính lại khi chạy lại <code>prepare</code> với <code>--force flags autoqc overlays</code>, ví dụ:"
            f'<br><code class="cd-path">{_e(cmd1)}</code><br><code class="cd-path">{_e(cmd2)}</code></div>')


def smoke_confirm_html(url):
    lines = [f"Sẽ TẠO task demo-smoke (4 ảnh xám giả, không phải ảnh mặt) trong project m28 trên {url or '(chưa có link)'}, nhập nhãn nháp, "
             "xuất lại, rồi XOÁ task đó.",
             "Nếu chưa có project m28 thì tạo rồi xoá lại khi còn trống. Không đụng task khác.",
             "Mất khoảng 1-2 phút. Bấm Huỷ giữa chừng có thể để lại task demo-smoke; lần chạy sau tự dọn nhờ runs\\_smoke\\dang_mo.json."]
    return '<div class="modal-title" id="cd-smoke-title">Chạy kiểm tra nhanh CVAT?</div>' + box_html("warn", "Sẽ làm:", lines)


def smoke_prog_html(snap, prog):
    """Thanh tiến độ của kiểm tra nhanh (cùng kiểu .nap-prog), nhãn từ dòng [k/12] của cvat_smoke.py."""
    st = snap["state"]
    if st == "chua":
        return ""
    pct = 100 if st == "xong" else round(100 * prog["frac"])
    label = prog["label"] if st == "dang_chay" else nap_anh.STATE_VI[st] + (
        f" (mã thoát {snap['returncode']})" if st == "loi" and snap["returncode"] is not None else "")
    if st == "dang_chay" and snap.get("cancelling"):
        label = "Đang huỷ…"
    cls = {"xong": "nap-st-ok", "loi": "nap-st-err", "da_huy": "nap-st-warn"}.get(st, "")
    mm = int(snap["elapsed"])
    return (f'<div class="nap-prog {cls}"><div class="nap-prog-top"><span class="nap-run">Kiểm tra nhanh <b>CVAT</b></span>'
            f'<span class="nap-label">{_e(label)}</span><span class="nap-time">{mm // 60:02d}:{mm % 60:02d}</span></div>'
            f'<div class="m28-bar" role="progressbar" aria-valuenow="{pct}" aria-valuemin="0" aria-valuemax="100"><i style="width:{pct}%"></i></div></div>')


def smoke_result_html(rep, json_path=""):
    """Bảng Bước / Kết quả / Ghi chú từ báo cáo .json của cvat_smoke.py (mọi chuỗi được escape) + dòng tổng + đường dẫn báo cáo."""
    cls = {"ĐẠT": "sm-dat", "HỎNG": "sm-hong", "BỎ QUA": "sm-bo"}
    rows = []
    for b in rep.get("buoc", []):
        rows.append(f'<tr><td>{_e(b.get("ma"))}. {_e(b.get("ten"))}</td><td class="sm-kq {cls.get(b.get("ket_qua"), "")}">{_e(b.get("ket_qua"))}</td>'
                    f'<td>{_e(b.get("ghi_chu"))}</td></tr>')
        rows += [f'<tr class="sm-sub"><td></td><td></td><td>- {_e(x)}</td></tr>' for x in b.get("con", [])]
    bad = sum(1 for b in rep.get("buoc", []) if b.get("ket_qua") == "HỎNG")
    txt = os.path.basename(json_path)[:-5] + ".txt" if json_path else ""
    lines = [rep.get("tong", "")]
    if txt:
        lines.append(f"Báo cáo: runs\\_smoke\\{txt}")
    if bad and txt:
        lines.append(f"Gửi cho P4 file runs\\_smoke\\{txt} (không gửi token, không gửi ảnh).")
    box = box_html("err" if bad else "ok", lines[0], lines[1:])
    return box + '<table class="sm-tbl"><tr><th>Bước</th><th>Kết quả</th><th>Ghi chú</th></tr>' + "".join(rows) + "</table>"


# ---------- tab ----------
def settings_tab(gr, demo, store, ctx, after_cvat=None, run_name=None, after_model=None):
    """Dựng NỘI DUNG tab Cài đặt (gọi trong `with gr.Tab(...)`). after_cvat(ev): gắn thêm .then(...) làm mới khung Đẩy lên CVAT và tab Các đợt
    sau Lưu/Quên token. after_model(ev): gắn thêm .then(...) kiểm lại model/cấu hình ở tab Nạp ảnh sau khi Lưu đường dẫn model. Trả (hàm làm mới,
    inputs, outputs, opts) để tab.select gọi."""
    S = cai_dat.get()
    pending = dot_anh.Pending()
    run_label = run_name(store.run_dir) if (store is not None and run_name) else ""
    config_path = os.path.join(ctx.project_root or S.project_root, "config", "m28_config.json")

    gr.HTML('<div class="cd-note">Trang này chỉ chạy ở máy bạn (127.0.0.1). Token chỉ dán vào ô Token bên dưới: không dán vào chat, file hay lệnh. '
            "Token không bao giờ hiện lại (chỉ còn 4 ký tự cuối), không vào log, runs\\, outputs\\ hay git.</div>", elem_id="cd-top", apply_default_css=False)
    # --- CVAT ---
    with gr.Column(elem_classes=["cd-sec"]):
        gr.HTML('<div class="cd-sec-title">CVAT</div>', apply_default_css=False)
        st_html = gr.HTML(elem_id="cd-cvat-status", apply_default_css=False)
        url_tb = gr.Textbox(label="Link CVAT (CVAT_URL)", placeholder="http://localhost:8080", max_lines=1, elem_id="cd-url")
        with gr.Row(elem_id="cd-token-row"):
            token_tb = gr.Textbox(label="Token CVAT", type="password", max_lines=1, elem_id="cd-token", scale=5)
            b_eye = gr.Button("Hiện / ẩn", elem_id="cd-eye", size="sm")
        org_tb = gr.Textbox(label="Tổ chức (CVAT_ORG), để trống nếu không dùng", max_lines=1, elem_id="cd-org")
        remember = gr.Checkbox(label="Nhớ trên máy này", value=False, elem_id="cd-remember")
        rem_note = gr.HTML(elem_id="cd-remember-note", apply_default_css=False)
        with gr.Row(elem_id="cd-cvat-btns"):
            b_save = gr.Button("Lưu", variant="primary", elem_id="cd-save")
            b_test = gr.Button("Thử kết nối CVAT", elem_id="cd-test")
            b_forget = gr.Button("Quên token", variant="stop", elem_id="cd-forget")
            b_smoke = gr.Button("Chạy kiểm tra nhanh CVAT", elem_id="cd-smoke")
        cvat_msg = gr.HTML(elem_id="cd-cvat-msg", apply_default_css=False)
        smoke_msg = gr.HTML(elem_id="cd-smoke-msg", apply_default_css=False)
        smoke_prog = gr.HTML(elem_id="cd-smoke-prog", apply_default_css=False)
        smoke_log = gr.Textbox(label="Log kiểm tra nhanh CVAT (đã lọc token)", lines=6, max_lines=12, interactive=False, autoscroll=True,
                               elem_id="cd-smoke-log", visible=False)
        b_smoke_stop = gr.Button("Huỷ kiểm tra", variant="stop", elem_id="cd-smoke-stop", visible=False)
        smoke_result = gr.HTML(elem_id="cd-smoke-result", apply_default_css=False)
        smoke_timer = gr.Timer(1.0, active=False)
    with gr.Column(visible=False, elem_id="cd-forget-confirm", elem_classes=["m28-modal"]) as forget_modal:
        with gr.Column(elem_classes=["m28-modal-box"]):
            forget_body = gr.HTML(elem_id="cd-forget-body", apply_default_css=False)
            with gr.Row(elem_classes=["m28-modal-btns"]):
                b_forget_ok = gr.Button("Quên token", variant="stop", elem_id="cd-forget-ok")
                b_forget_no = gr.Button("Huỷ", elem_id="cd-forget-cancel")
    with gr.Column(visible=False, elem_id="cd-smoke-confirm", elem_classes=["m28-modal"]) as smoke_modal:
        with gr.Column(elem_classes=["m28-modal-box"]):
            smoke_body = gr.HTML(elem_id="cd-smoke-body", apply_default_css=False)
            smoke_keep = gr.Checkbox(label="Giữ task để xem bằng mắt (--giu-task)", value=False, elem_id="cd-smoke-keep")
            with gr.Row(elem_classes=["m28-modal-btns"]):
                b_smoke_ok = gr.Button("Chạy kiểm tra", variant="primary", elem_id="cd-smoke-ok")
                b_smoke_no = gr.Button("Huỷ", elem_id="cd-smoke-cancel")
    # --- Người rà ---
    with gr.Column(elem_classes=["cd-sec"]):
        gr.HTML('<div class="cd-sec-title">Người rà</div>', apply_default_css=False)
        rev_info = gr.HTML(elem_id="cd-reviewer-info", apply_default_css=False)
        rev_tb = gr.Textbox(label="Tên người rà mặc định (dùng từ lượt sau)", max_lines=1, elem_id="cd-reviewer", placeholder="ví dụ P2")
        with gr.Row(elem_id="cd-reviewer-btns"):
            b_rev = gr.Button("Lưu tên", elem_id="cd-reviewer-save")
        rev_msg = gr.HTML(elem_id="cd-reviewer-msg", apply_default_css=False)
    # --- Đường dẫn ---
    with gr.Column(elem_classes=["cd-sec"]):
        gr.HTML('<div class="cd-sec-title">Đường dẫn</div>', apply_default_css=False)
        paths_info = gr.HTML(elem_id="cd-paths-info", apply_default_css=False)
        img_tb = gr.Textbox(label="Thư mục ảnh", max_lines=1, elem_id="cd-images", placeholder="D:\\m28\\data\\frames")
        with gr.Row(elem_id="cd-images-btns"):
            b_img_check = gr.Button("Kiểm", elem_id="cd-images-check")
            b_img_save = gr.Button("Lưu", elem_id="cd-images-save")
        img_msg = gr.HTML(elem_id="cd-images-msg", apply_default_css=False)
        mod_tb = gr.Textbox(label="File face_landmarker.task", max_lines=1, elem_id="cd-model", placeholder="D:\\m28\\face_landmarker.task")
        with gr.Row(elem_id="cd-model-btns"):
            b_mod_check = gr.Button("Kiểm", elem_id="cd-model-check")
            b_mod_save = gr.Button("Lưu", elem_id="cd-model-save")
        mod_msg = gr.HTML(elem_id="cd-model-msg", apply_default_css=False)
    # --- t_flip ---
    with gr.Column(elem_classes=["cd-sec"]):
        gr.HTML('<div class="cd-sec-title">Cờ low_conf (t_flip)</div>', apply_default_css=False)
        tf_info = gr.HTML(elem_id="cd-tflip-info", apply_default_css=False)
        tf_tb = gr.Textbox(label="t_flip mới (số trong (0; 1], dấu phẩy hay chấm đều được)", max_lines=1, elem_id="cd-tflip", placeholder="0,0672")
        tf_ack = gr.Checkbox(label="Tôi là P2/P1 và biết file cấu hình đã đóng băng", value=False, elem_id="cd-tflip-ack", visible=False)
        with gr.Row(elem_id="cd-tflip-btns"):
            b_tf_set = gr.Button("Đặt t_flip", elem_id="cd-tflip-set")
            b_tf_null = gr.Button("Để null", elem_id="cd-tflip-null")
        tf_msg = gr.HTML(elem_id="cd-tflip-msg", apply_default_css=False)
        tf_token = gr.Textbox(visible="hidden", elem_id="cd-tflip-token")
    with gr.Column(visible=False, elem_id="cd-tflip-confirm", elem_classes=["m28-modal"]) as tf_modal:
        with gr.Column(elem_classes=["m28-modal-box"]):
            tf_body = gr.HTML(elem_id="cd-tflip-body", apply_default_css=False)
            with gr.Row(elem_classes=["m28-modal-btns"]):
                b_tf_ok = gr.Button("Đổi t_flip", variant="primary", elem_id="cd-tflip-ok")
                b_tf_no = gr.Button("Huỷ", elem_id="cd-tflip-cancel")
    # --- Pipeline ---
    with gr.Column(elem_classes=["cd-sec"]):
        gr.HTML('<div class="cd-sec-title">Pipeline (chỉ đọc)</div>', apply_default_css=False)
        pipe_html = gr.HTML(elem_id="cd-pipeline", apply_default_css=False)
    rev_state = gr.State(None)

    outs = [st_html, url_tb, token_tb, org_tb, remember, rem_note, cvat_msg, forget_modal, forget_body, rev_info, rev_tb, rev_msg, paths_info, img_tb,
            img_msg, mod_tb, mod_msg, tf_info, tf_tb, tf_ack, tf_msg, tf_modal, tf_body, tf_token, pipe_html, rev_state]
    opts = dict(show_progress="hidden", api_visibility="private", concurrency_limit=1)

    # ---------- dựng giá trị hiển thị ----------
    def pipe_info():
        return cai_dat.pipeline_info(ctx.project_root or S.project_root)

    def ret(d):
        return tuple(d.get(c, gr.update()) for c in outs)

    def view(full=False, over=None):
        """dict {component: cập nhật} cho mọi phần hiển thị; full=True thì nạp lại cả các ô nhập từ server (ô token luôn để trống,
        chỉ có placeholder dạng che). over: ghi đè/thêm (thông báo, hộp xác nhận)."""
        snap = S.snapshot()
        pi = pipe_info()
        tinfo = cai_dat.read_t_flip(config_path)
        hint = (f"đã có token {snap['token_mask']} — để trống nếu không đổi" if snap["has_token"]
                else "dán token CVAT (Settings > Security trong CVAT)")
        d = {st_html: status_html(snap, pi["pipe"]), rem_note: remember_note_html(snap),
             rev_info: reviewer_info_html(snap, ctx.reviewer, run_label, S.next_reviewer(ctx.reviewer)),
             paths_info: paths_info_html(snap), tf_info: tflip_info_html(tinfo), pipe_html: pipeline_html(pi), rev_state: snap["rev"],
             tf_ack: gr.update(visible=bool(tinfo["frozen"])), token_tb: gr.update(placeholder=hint)}
        if full:
            d.update({url_tb: snap["url"], token_tb: gr.update(value="", placeholder=hint), org_tb: snap["org"], remember: snap["remember"],
                      rev_tb: snap["prefs"]["reviewer"], img_tb: snap["prefs"]["images_dir"], mod_tb: snap["prefs"]["model_path"]})
        d.update(over or {})
        return d

    def refuse_why(cvat_busy=False):
        """Lý do từ chối ghi (trang đang đóng; hoặc, với cài đặt CVAT, đang đẩy/xoá task) hoặc ''."""
        if ctx.closing:
            return nap_anh.CLOSING_MSG
        if cvat_busy:
            for j, what in ((ctx.push_job, "đẩy"), (ctx.del_job, "xoá task")):
                if j.running:
                    return f"Đang {what} lượt {j.run} lên CVAT: chờ xong rồi mới đổi cài đặt CVAT (tiến trình con đang dùng token hiện tại)."
            if ctx.smoke_job.running:
                return "Đang chạy kiểm tra nhanh CVAT: chờ xong hoặc bấm Huỷ kiểm tra rồi mới đổi cài đặt CVAT (tiến trình con đang dùng token hiện tại)."
        return ""

    def safe_with(where):
        """Bọc handler: lỗi lạ chỉ hiện thông báo đã lọc token ở `where` (không traceback ra trình duyệt); traceback đã lọc ra console."""
        def deco(fn):
            @functools.wraps(fn)
            def wrapper(*a):
                try:
                    return fn(*a)
                except Exception as exc:               # noqa: BLE001 - Gradio (show_error=True) sẽ hiện traceback có thể chứa token
                    print(cvat_io.scrub(traceback.format_exc()), file=sys.stderr, flush=True)
                    text = cvat_io.scrub(f"Lỗi không lường trước ({exc.__class__.__name__}). Chi tiết (đã lọc token) ở cửa sổ cmd.")
                    return ret(view(over={where: msg_html(text, "err")}))
            return wrapper
        return deco

    def reload_all(r, where):
        """Nạp lại toàn bộ (kể cả ô nhập) kèm thông báo của kết quả r."""
        return ret(view(full=True, over={where: msg_html(r["msg"], r["level"])}))

    # ---------- tải / chọn tab ----------
    def on_show(rev):
        snap = S.snapshot()
        return ret(view(full=(rev is None or rev != snap["rev"])))

    # ---------- CVAT ----------
    def note(c, text, level):
        return {c: msg_html(text, level)}

    @safe_with(cvat_msg)
    def on_save(url, token, org, rem, rev):
        cvat_io.register_secret((token or "").strip())
        why = refuse_why(cvat_busy=True)
        if why:
            return ret(view(over=note(cvat_msg, why, "warn")))
        r = S.save_cvat(url, token, org, bool(rem), rev)
        if r["stale"] or r["ok"]:
            return reload_all(r, cvat_msg)
        return ret(view(over=note(cvat_msg, r["msg"], r["level"])))

    @safe_with(cvat_msg)
    def on_test(url, token, org, rev):
        cvat_io.register_secret((token or "").strip())
        why = refuse_why()
        if why:
            return ret(view(over=note(cvat_msg, why, "warn")))
        eff = S.cvat_env()
        url_v = (url or "").strip() or eff["url"]
        tok_v = (token or "").strip() or eff["token"]
        org_v = (org or "").strip()
        typed = ((url or "").strip() != "" and cvat_io.norm_url(url) != cvat_io.norm_url(eff["url"])) or \
                ((token or "").strip() != "" and (token or "").strip() != eff["token"])
        chk = cai_dat.check_url(url_v)
        pipe = pipe_info()["pipe"]
        res = cai_dat.test_connection(url_v, tok_v, org_v, pipe, project_root=ctx.project_root or None)
        S.record_test(chk["url"] if chk["ok"] else url_v, tok_v, org_v, res)
        body = test_html(res, pipe["project"], typed=typed)
        if chk["ok"] and chk["warning"]:
            body += box_html("warn", "Cảnh báo", [chk["warning"]])
        return ret(view(over={cvat_msg: body}))

    @safe_with(cvat_msg)
    def on_forget_open(rev):
        why = refuse_why(cvat_busy=True)
        if why:
            return ret(view(over=note(cvat_msg, why, "warn")))
        snap = S.snapshot()
        lines = ["Xoá file " + (snap["file_path"] or "đã lưu") + " nếu có, và token đã nhập trong phiên này."]
        if snap["env"] != "none":
            lines.append("Token trong biến môi trường của cmd KHÔNG xoá được từ trang: nó vẫn còn trong cmd đang chạy trang này (đóng cmd, hoặc gõ "
                         "set CVAT_ACCESS_TOKEN= rồi mở lại trang để bỏ), và trang vẫn dùng nó.")
        lines.append("Nút Đẩy lên CVAT sẽ khoá lại nếu không còn nguồn token nào. Nên thu hồi token trong CVAT khi xong việc (Settings > Security).")
        body = '<div class="modal-title modal-danger" id="cd-forget-title">Quên token?</div>' + box_html("warn", "Sẽ làm:", lines)
        return ret(view(over={forget_modal: gr.update(visible=True), forget_body: body}))

    @safe_with(cvat_msg)
    def on_forget_ok(rev):
        hide = {forget_modal: gr.update(visible=False), forget_body: ""}
        why = refuse_why(cvat_busy=True)
        if why:
            return ret(view(over={**note(cvat_msg, why, "warn"), **hide}))
        r = S.forget_cvat(rev)
        return ret(view(full=True, over={**note(cvat_msg, r["msg"], r["level"]), **hide}))

    def on_forget_cancel():
        return ret({forget_modal: gr.update(visible=False), forget_body: ""})

    # ---------- người rà ----------
    @safe_with(rev_msg)
    def on_reviewer(name, rev):
        why = refuse_why()
        if why:
            return ret(view(over=note(rev_msg, why, "warn")))
        r = S.set_reviewer(name, rev)
        if r["stale"]:
            return reload_all(r, rev_msg)
        return ret(view(full=r["ok"], over=note(rev_msg, r["msg"], r["level"])))

    # ---------- đường dẫn ----------
    def path_check(kind, msg_c):
        @safe_with(msg_c)
        def on_check(value):
            res = cai_dat.check_images_dir(value) if kind == "images_dir" else cai_dat.check_model(value)
            return ret(view(over={msg_c: check_html(res)}))
        return on_check

    def path_save(kind, msg_c):
        @safe_with(msg_c)
        def on_path_save(value, rev):
            why = refuse_why()
            if why:
                return ret(view(over=note(msg_c, why, "warn")))
            r = S.set_path(kind, value, rev)
            if r["stale"]:
                return reload_all(r, msg_c)
            body = (check_html(r["check"]) if r.get("check") else "") + msg_html(r["msg"], r["level"])
            return ret(view(full=r["ok"], over={msg_c: body}))
        return on_path_save

    # ---------- t_flip ----------
    def tflip_busy():
        for j, what in ((ctx.job, "chuẩn bị ảnh"), (ctx.push_job, "đẩy lên CVAT"), (ctx.del_job, "xoá task"), (ctx.smoke_job, "kiểm tra nhanh CVAT")):
            if j.running:
                return f"Đang {what} (lượt {j.run}): chờ xong rồi đổi t_flip."
        b = cai_dat.busy_runs(ctx.runs_root)
        if b:
            return f"Lượt {b[0][0]} đang có việc chạy ({b[0][1]}): chờ xong rồi đổi t_flip."
        return ""

    def tflip_open(is_null):
        @safe_with(tf_msg)
        def on_tflip(text, ack, rev):
            why = refuse_why() or tflip_busy()
            if why:
                return ret(view(over=note(tf_msg, why, "warn")))
            info = cai_dat.read_t_flip(config_path)
            if not info["ok"]:
                return ret(view(over=note(tf_msg, info["error"], "err")))
            if not is_null and not str(text or "").strip():
                return ret(view(over=note(tf_msg, "Chưa nhập t_flip mới (hoặc bấm Để null).", "err")))
            try:
                new = None if is_null else cai_dat.parse_t_flip(text)
            except ValueError as e:
                return ret(view(over=note(tf_msg, str(e), "err")))
            if info["frozen"] and not ack:
                return ret(view(over=note(tf_msg, f"Cấu hình đã đóng băng (status: {info['status']}). Đổi giữa chừng làm các lượt đã chạy lệch "
                                                  "nhau: chỉ P1/P2 mới làm, và phải tick ô xác nhận ở trên.", "warn")))
            if info["t_flip"] == new:
                return ret(view(over=note(tf_msg, f"t_flip đã là {fmt_t(new)}: không có gì để đổi.", "info")))
            it = pending.open(kind="tflip", value=new, old=info["t_flip"])
            return ret(view(over={tf_modal: gr.update(visible=True), tf_body: tflip_confirm_html(info["t_flip"], new, S.images_dir()),
                                  tf_token: it["token"]}))
        return on_tflip

    @safe_with(tf_msg)
    def on_tf_ok(token, ack):
        hide = {tf_modal: gr.update(visible=False), tf_body: "", tf_token: ""}
        it = pending.take(token)
        why = refuse_why() or tflip_busy()
        if why:
            return ret(view(over={**note(tf_msg, why, "warn"), **hide}))
        if it is None:
            return ret(view(over={**note(tf_msg, "Yêu cầu xác nhận đã cũ hoặc không còn hiệu lực: không ghi gì, bấm Đặt t_flip lại.", "warn"), **hide}))
        info = cai_dat.read_t_flip(config_path)
        if info["ok"] and info["frozen"] and not ack:
            return ret(view(over={**note(tf_msg, "Cấu hình đã đóng băng: tick ô xác nhận rồi bấm lại.", "warn"), **hide}))
        try:
            r = cai_dat.write_t_flip(config_path, it["value"])
        except (RunError, ValueError) as e:
            return ret(view(over={**note(tf_msg, str(e), "err"), **hide}))
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{stamp}] t_flip trong {os.path.normpath(config_path)} đổi: {fmt_t(r['old'])} -> {fmt_t(r['new'])} (từ tab Cài đặt)", flush=True)
        runs = cai_dat.runs_with_flags(ctx.runs_root)
        lines = [f"Đã đổi t_flip: {fmt_t(r['old'])} → {fmt_t(r['new'])} (lúc {stamp}); các trường khác của config giữ nguyên."]
        if runs:
            lines.append("Các lượt đã có flags.json, tính theo ngưỡng CŨ (chỉ tính lại khi chạy lại prepare với --force flags autoqc overlays): "
                         + ", ".join(runs))
        else:
            lines.append("Chưa có lượt nào có flags.json: chưa lượt nào cần tính lại.")
        return ret(view(over={**{tf_msg: box_html("ok", "Đã ghi", lines)}, **hide}))

    def on_tf_cancel():
        pending.cancel()
        return ret({tf_modal: gr.update(visible=False), tf_body: "", tf_token: ""})

    # ---------- kiểm tra nhanh CVAT (tiến trình con cvat_smoke.py; trang không gọi mạng) ----------
    sm_outs = [smoke_modal, smoke_body, smoke_msg, smoke_prog, smoke_log, b_smoke_stop, smoke_result, smoke_timer, b_smoke]
    sm_job = ctx.smoke_job

    def smoke_busy():
        """Lý do không chạy được kiểm tra nhanh lúc này (đang đóng, đang chuyển lượt, đẩy/xoá task/kiểm tra nhanh khác đang chạy) hoặc ''."""
        if ctx.closing:
            return nap_anh.CLOSING_MSG
        if ctx.switch_to is not None:
            return "Trang đang chuyển sang lượt khác: chờ rồi thử lại."
        for j, what in ((ctx.push_job, "đẩy lượt"), (ctx.del_job, "xoá task của lượt"), (sm_job, "chạy kiểm tra nhanh CVAT")):
            if j.running:
                return f"Đang {what}" + ("" if j is sm_job else f" {j.run} (CVAT)") + ": chờ xong hoặc bấm Huỷ rồi mới chạy kiểm tra nhanh."
        return ""

    def smoke_render(note="", level="warn", modal=None):
        snap = sm_job.snapshot()
        running = snap["state"] == "dang_chay"
        result = ""
        if snap["state"] == "chua":
            pass
        elif snap["state"] in ("xong", "loi") and snap["run_dir"]:
            rep = nap_anh.read_smoke_report(snap["run_dir"], snap["lines"])
            if rep:
                jp = next((ln[len("SMOKE_JSON: "):].strip() for ln in reversed(snap["lines"]) if ln.startswith("SMOKE_JSON: ")), "")
                result = smoke_result_html(rep, jp)
            else:
                result = box_html("err", "Kiểm tra nhanh dừng, chưa có báo cáo", [day_cvat.last_message(snap["lines"]) or "Xem log bên trên."])
        elif snap["state"] == "da_huy":
            result = box_html("warn", "Đã huỷ kiểm tra nhanh", ["Nếu task demo-smoke còn dở trên CVAT thì lần chạy sau tự dọn "
                                                                  "(runs\\_smoke\\dang_mo.json), hoặc xoá tay trong CVAT."])
        lines = "\n".join(snap["lines"][-80:])
        m = modal or {}
        return (m.get("modal", gr.update()), m.get("body", gr.update()), msg_html(note, level) if note else "",
                smoke_prog_html(snap, nap_anh.smoke_progress(snap["lines"])), gr.update(value=lines, visible=bool(lines)),
                gr.update(visible=running, interactive=running and not snap.get("cancelling")), result, gr.Timer(active=running),
                gr.update(interactive=not running))

    def smoke_safe(fn):
        @functools.wraps(fn)
        def wrapper(*a):
            try:
                return fn(*a)
            except Exception as exc:                       # noqa: BLE001 - như safe_with: chỉ thông báo đã lọc token, traceback đã lọc ra console
                print(cvat_io.scrub(traceback.format_exc()), file=sys.stderr, flush=True)
                return smoke_render(cvat_io.scrub(f"Lỗi không lường trước ({exc.__class__.__name__}). Chi tiết (đã lọc token) ở cửa sổ cmd."), "err")
        return wrapper

    @smoke_safe
    def on_smoke_open():
        why = smoke_busy()
        if why:
            return smoke_render(why)
        eff = S.cvat_env()
        if not eff["url"] or not eff["token"]:
            return smoke_render("Chưa có link và token CVAT: nhập và Lưu ở khung CVAT (hoặc đặt CVAT_URL, CVAT_ACCESS_TOKEN trong cmd) rồi chạy lại.")
        return smoke_render(modal=dict(modal=gr.update(visible=True), body=smoke_confirm_html(cvat_io.norm_url(eff["url"]))))

    @smoke_safe
    def on_smoke_ok(keep):
        hide = dict(modal=gr.update(visible=False), body="")
        why = smoke_busy()
        if why:
            return smoke_render(why, modal=hide)
        eff = S.cvat_env()
        if not eff["url"] or not eff["token"]:
            return smoke_render("Chưa có link và token CVAT.", modal=hide)
        try:
            sm_job.start(ctx.runs_root, ctx.project_root, giu_task=bool(keep))
        except RunError as e:
            return smoke_render(str(e), modal=hide)
        return smoke_render(modal=hide)

    @smoke_safe
    def on_smoke_cancel_dialog():
        return smoke_render(modal=dict(modal=gr.update(visible=False), body=""))

    @smoke_safe
    def on_smoke_stop():
        sm_job.cancel()
        return smoke_render()

    @smoke_safe
    def on_smoke_tick():
        return smoke_render()

    # ---------- nối sự kiện ----------
    wr = dict(opts, concurrency_id="cd")
    ev_save = b_save.click(on_save, [url_tb, token_tb, org_tb, remember, rev_state], outs, **wr)
    b_test.click(on_test, [url_tb, token_tb, org_tb, rev_state], outs, **dict(opts, concurrency_id="cd_test"))
    b_eye.click(None, None, None, js=EYE_JS)
    b_forget.click(on_forget_open, [rev_state], outs, **wr)
    ev_forget = b_forget_ok.click(on_forget_ok, [rev_state], outs, **wr)
    b_forget_no.click(on_forget_cancel, None, outs, **wr)
    ev_save.then(None, None, None, js=HIDE_JS)
    ev_forget.then(None, None, None, js=HIDE_JS)
    if after_cvat is not None:
        after_cvat(ev_save)
        after_cvat(ev_forget)
    b_rev.click(on_reviewer, [rev_tb, rev_state], outs, **wr)
    b_img_check.click(path_check("images_dir", img_msg), [img_tb], outs, **wr)
    b_img_save.click(path_save("images_dir", img_msg), [img_tb, rev_state], outs, **wr)
    b_mod_check.click(path_check("model_path", mod_msg), [mod_tb], outs, **wr)
    ev_model = b_mod_save.click(path_save("model_path", mod_msg), [mod_tb, rev_state], outs, **wr)
    if after_model is not None:
        after_model(ev_model)
    b_tf_set.click(tflip_open(False), [tf_tb, tf_ack, rev_state], outs, **wr)
    b_tf_null.click(tflip_open(True), [tf_tb, tf_ack, rev_state], outs, **wr)
    b_tf_ok.click(on_tf_ok, [tf_token, tf_ack], outs, **wr)
    b_tf_no.click(on_tf_cancel, None, outs, **wr)
    sm_opts = dict(opts, concurrency_id="cd_smoke")
    b_smoke.click(on_smoke_open, None, sm_outs, **sm_opts)
    b_smoke_ok.click(on_smoke_ok, [smoke_keep], sm_outs, **sm_opts)
    b_smoke_no.click(on_smoke_cancel_dialog, None, sm_outs, **sm_opts)
    b_smoke_stop.click(on_smoke_stop, None, sm_outs, **dict(opts, concurrency_id="cd_smoke_huy"))
    smoke_timer.tick(on_smoke_tick, None, sm_outs, **dict(opts, concurrency_id="cd_smoke_tick"))
    demo.load(on_smoke_tick, None, sm_outs, **dict(opts, concurrency_id="cd_smoke_tick"))
    demo.load(on_show, [rev_state], outs, **dict(opts, concurrency_id="cd"))
    return on_show, [rev_state], outs, dict(opts, concurrency_id="cd")
