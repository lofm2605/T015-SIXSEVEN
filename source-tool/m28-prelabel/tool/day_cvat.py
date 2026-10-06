"""Nút "Đẩy lên CVAT" và "Xoá task trên CVAT" của trang rà soát M28: logic thuần (khi nào bật, hộp xác nhận, tiến độ, kết quả, lỗi).

Quy ước (giống nap_anh.py):
  * Chỉ thư viện chuẩn. Không import gradio, numpy, steps, torch, cvat_sdk. TRANG KHÔNG GỌI MẠNG: chỉ tiến trình con
    (`m28.py push ...`, xem nap_anh.PushJob/DeleteTaskJob) gọi CVAT. Trang chỉ đọc biến môi trường CVAT_URL và CVAT_ACCESS_TOKEN
    (đọc lại mỗi lần vẽ); token KHÔNG bao giờ nhập vào trang, không bao giờ hiện lên trang, không đi qua đối số dòng lệnh.
  * Số Nhận / Gán tay / Bỏ trong hộp xác nhận tính bằng ĐÚNG hàm m28core.phan_loai.classify mà steps.push dùng.
"""
import html
import json
import os
import re
import sys

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)
import dot_anh  # noqa: E402
from m28core import cvat_io, loai_tru, phan_loai  # noqa: E402

PHASES = ["kiểm tra", "kết nối", "project", "tải ảnh", "nhập nhãn", "xuất kiểm"]
PHASE_RE = re.compile(r"^\[(\d)/6\]")
STATE_VI = {"dang_chay": "Đang chạy", "xong": "Xong", "loi": "Lỗi", "da_huy": "Đã huỷ", "chua": ""}
ENV_HELP = ("Đóng trang (Ctrl+C), trong <b>cùng cửa sổ cmd</b> gõ <code>set CVAT_URL=http://localhost:8080</code> và "
            "<code>set CVAT_ACCESS_TOKEN=&lt;token của bạn&gt;</code> rồi mở lại trang. Trang không có ô nhập token: không dán token vào chat hay file.")


def _e(x):
    return html.escape(str(x), quote=True)


# ---------- môi trường ----------
def env_state(environ=None):
    """dict(ok, url, reason|None). Đọc os.environ mỗi lần gọi. reason KHÔNG chứa giá trị token."""
    env = cvat_io.read_env(environ)
    bad = cvat_io.env_problem(env)
    reason = None
    if bad:
        if not env["url"] or not env["token"]:
            miss = " và ".join(n for n, v in (("CVAT_URL", env["url"]), ("CVAT_ACCESS_TOKEN", env["token"])) if not v)
            reason = f"Thiếu {miss}."
        elif not env["url"].startswith(("http://", "https://")):
            reason = f"CVAT_URL phải bắt đầu bằng http:// (đang là {env['url']})."
        else:
            reason = "CVAT_URL không được chứa tên đăng nhập hay mật khẩu."
    return dict(ok=bad is None, url=cvat_io.norm_url(env["url"]), org=env["org"], reason=reason)


def pipeline_of(project_root):
    """{project, prefix, job_size, cvat_version} đọc config/pipeline.json; hỏng/thiếu thì mặc định (trang không vỡ)."""
    try:
        return cvat_io.load_pipeline(os.path.join(project_root, "config", "pipeline.json"))
    except SystemExit:
        return dict(cvat_io.DEFAULT_PIPELINE)


def task_name(run, pipe):
    return f"{pipe['prefix']}{run}"


# ---------- kế hoạch đẩy (cùng hàm phân loại với steps.push) ----------
def _no_face(run_dir):
    return phan_loai.read_no_face(run_dir)


def plan_counts(run_dir, reviewer, project_root=None, pipe=None):
    """Số Nhận / Gán tay / Bỏ / xoá mềm sẽ đẩy, số job dự kiến, số mặt chưa rà, ảnh thiếu. Cùng hàm với steps.push."""
    pipe = pipe or dict(cvat_io.DEFAULT_PIPELINE)
    excluded = loai_tru.read_excluded(run_dir)
    names, unusable = dot_anh.queue_names(run_dir, excluded)
    tri, err = dot_anh.triage_of(run_dir, reviewer)
    meta_all = dot_anh.read_meta(run_dir)
    meta = {k: v for k, v in meta_all.items() if k not in excluded}      # chỉ để kiểm ảnh thiếu; classify nhận meta đầy đủ
    mp50 = {n: 1 for n in dot_anh.read_mp50_names(run_dir) if n not in excluded}
    pl = phan_loai.classify(tri, meta_all, mp50, _no_face(run_dir), excluded)
    remaining = sum(1 for n in names if tri.get(n, ("", ""))[0] not in phan_loai.DECISIONS)
    mode = "auto"
    try:
        with open(os.path.join(run_dir, "crop", "box.txt"), encoding="utf-8") as f:
            mode = f.read().strip() or "auto"
    except OSError:
        pass
    missing = []
    for n in pl["nhan"] + pl["tay"]:
        m = meta.get(n) or {}
        path = (os.path.join(run_dir, "crop", "images", n + ".png") if mode == "wflw" else m.get("src"))
        if not path or not os.path.exists(path):
            missing.append(n)
    return dict(nhan=len(pl["nhan"]), tay=len(pl["tay"]), bo=len(pl["rejected"]), xoa=len(pl["removed"]), lost=len(pl["lost"]),
                nhan_khong_nhap=len(pl["nhan_khong_nhap"]), jobs=phan_loai.n_jobs(len(pl["nhan"]), len(pl["tay"]), pipe["job_size"]),
                remaining=remaining, missing=missing, loi_triage=err)


# ---------- mô hình nút Đẩy ----------
def push_model(run_dir, reviewer, project_root, *, remaining=None, environ=None, job_running=False):
    """Mô hình của khung "Đẩy lên CVAT" cho một lượt.
    remaining: số mặt chưa rà theo trang (đợt đang rà); None thì tính từ triage_<người rà>.csv.
    Trả dict(kind: "done"|"button", enabled, reason, task, plan, env, push, pipe)."""
    pipe = pipeline_of(project_root)
    run = os.path.basename(os.path.normpath(run_dir))
    env = env_state(environ)
    ps = dot_anh.read_push(run_dir)
    st = (ps or {}).get("trang_thai")
    plan = plan_counts(run_dir, reviewer, project_root, pipe)
    rem = plan["remaining"] if remaining is None else remaining
    m = dict(kind="button", enabled=False, reason="", task=task_name(run, pipe), plan=plan, env=env, push=ps, pipe=pipe, run=run, remaining=rem)
    if st == "xong":
        m["kind"] = "done"
        return m
    busy = dot_anh.run_busy(run_dir)
    if job_running or busy:
        m["reason"] = "Đang có việc chạy cho lượt này (" + (busy[0] if busy else "đẩy lên CVAT") + "): chờ xong."
    elif st in ("dang_tao", "da_tao", "da_nhap", "hong"):
        m["reason"] = {"dang_tao": "Lần đẩy trước dừng giữa lúc tạo task (chưa có id).", "da_tao": "Lần đẩy trước dừng sau khi đã tạo task, chưa nhập nhãn.",
                       "da_nhap": "Lần đẩy trước đã nhập nhãn nhưng chưa kiểm xong.", "hong": "push.json bị hỏng."}[st]
        m["partial"] = True
    elif rem > 0:
        m["reason"] = f"Còn {rem} mặt chưa rà."
    elif plan["nhan"] + plan["tay"] == 0:
        m["reason"] = "Không có mặt nào để đẩy (cả Nhận và Gán tay đều trống)."
    elif plan["missing"]:
        m["reason"] = f"Không thấy {len(plan['missing'])} ảnh để tải lên (ví dụ {plan['missing'][0]}): ảnh gốc đã bị chuyển đi?"
    elif not env["ok"]:
        m["reason"] = env["reason"]
        m["env_help"] = True
    else:
        m["enabled"] = True
    return m


def push_command(run, reviewer, task):
    """Lệnh cmd tương đương (để người dùng chạy tay nếu muốn)."""
    return f"python tool\\m28.py push --run {run} --reviewer {reviewer} --task {task}"


def panel_html(m):
    """Nội dung khung (trên nút Đẩy): lý do khoá, hướng dẫn set, hoặc thẻ kết quả khi đã đẩy."""
    if m["kind"] == "done":
        return result_html(m["push"], m["run"])
    out = []
    if m["reason"]:
        out.append(f'<div class="m28-warn push-why" role="status">{_e(m["reason"])}</div>')
    if m.get("env_help"):
        out.append(f'<div class="nap-note push-envhelp">{ENV_HELP}</div>')
    if m.get("partial"):
        run, ps = m["run"], m["push"] or {}
        out.append('<div class="nap-note">Xem lại bằng một trong hai lệnh (cmd): '
                   f'<code>python tool\\m28.py push --run {_e(run)} --resume</code> làm nốt trên đúng task đã tạo, hoặc xoá task dở rồi đẩy lại bằng nút '
                   '<b>Xoá task trên CVAT</b> ở tab Các đợt.</div>')
        if ps.get("loi"):
            out.append(f'<div class="m28-warn">{_e(ps["loi"])}</div>')
    if m["enabled"]:
        p = m["plan"]
        out.append(f'<div class="nap-note">Sẵn sàng đẩy: <b>{p["nhan"]}</b> Nhận, <b>{p["tay"]}</b> Gán tay, <b>{p["bo"]}</b> Bỏ '
                   f'(task <b>{_e(m["task"])}</b>).</div>')
    return "".join(out)


def confirm_html(m):
    """Nội dung hộp xác nhận trước khi đẩy."""
    p = m["plan"]
    rows = [("Tên task", f'<b>{_e(m["task"])}</b>'), ("Mặt Nhận (có nháp 50 điểm)", f'<b>{p["nhan"]}</b>'),
            ("Mặt Gán tay (không có nháp)", f'<b>{p["tay"]}</b>'), ("Mặt Bỏ (không tải lên)", f'<b>{p["bo"]}</b>')]
    if p["xoa"]:
        rows.append(("Ảnh đã xoá (không tải lên)", f'<b>{p["xoa"]}</b>'))
    rows += [("Số job dự kiến", f'<b>{p["jobs"]}</b> (mỗi job Nhận {m["pipe"]["job_size"]} mặt + một job Gán tay riêng ở cuối)'),
             ("Địa chỉ CVAT", f'<code>{_e(m["env"]["url"])}</code>' + (f' · tổ chức {_e(m["env"]["org"])}' if m["env"]["org"] else ""))]
    body = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
    extra = ""
    if p["nhan_khong_nhap"]:
        extra = f'<div class="m28-warn">{p["nhan_khong_nhap"]} mặt chọn Nhận nhưng không có nháp: tự đưa sang Gán tay.</div>'
    return ('<div class="modal-title" id="push-confirm-title">Đẩy lên CVAT?</div>'
            f'<table class="m28-info">{body}</table>{extra}'
            f'<div class="nap-note">Chỉ tạo task <b>MỚI</b> trong project <b>{_e(m["pipe"]["project"])}</b>, nhập nhãn nháp đúng một lần rồi xuất lại để kiểm. '
            f'<b>Không đụng task {_e("m28-")}…</b> và không sửa nhãn đã có. Đẩy xong không đẩy lại lần hai được (trừ khi xoá task).</div>')


# ---------- tiến độ, kết quả, lỗi ----------
def parse_phase(lines, state="dang_chay"):
    """Pha hiện tại 1..6 theo dòng '[k/6] …' child in ra (0 = chưa có). Trả dict(k, total, frac, label)."""
    k = 0
    for ln in lines:
        mm = PHASE_RE.match(ln.strip())
        if mm:
            k = max(k, int(mm.group(1)))
    total = len(PHASES)
    if state == "xong":
        return dict(k=total, total=total, frac=1.0, label=f"Xong {total}/{total} bước")
    if k == 0:
        return dict(k=0, total=total, frac=0.0, label="Đang khởi động…")
    return dict(k=k, total=total, frac=(k - 0.5) / total, label=f"Bước {k}/{total} · {PHASES[k - 1]}")


def _mmss(sec):
    sec = int(sec)
    return f"{sec // 60:02d}:{sec % 60:02d}"


def progress_html(snap, what="Đẩy lên CVAT"):
    """Thanh tiến độ (kiểu .nap-prog) + trạng thái + thời gian."""
    st = snap["state"]
    if st == "chua":
        return ""
    ph = parse_phase(snap["lines"], st)
    pct = 100 if st == "xong" else round(100 * ph["frac"])
    label = ph["label"] if st == "dang_chay" else STATE_VI[st] + (f" (mã thoát {snap['returncode']})" if st == "loi" and snap["returncode"] is not None else "")
    if st == "dang_chay" and snap.get("cancelling"):
        label = "Đang huỷ…"
    cls = {"xong": "nap-st-ok", "loi": "nap-st-err", "da_huy": "nap-st-warn"}.get(st, "")
    return (f'<div class="nap-prog {cls}"><div class="nap-prog-top"><span class="nap-run">{_e(what)} · lượt <b>{_e(snap["run"])}</b></span>'
            f'<span class="nap-label">{_e(label)}</span><span class="nap-time">{_mmss(snap["elapsed"])}</span></div>'
            f'<div class="m28-bar" role="progressbar" aria-valuenow="{pct}" aria-valuemin="0" aria-valuemax="100"><i style="width:{pct}%"></i></div></div>')


def last_message(lines):
    """Dòng cuối có nghĩa của tiến trình con (thường là dòng SystemExit tiếng Việt); bỏ dòng traceback."""
    for ln in reversed(lines):
        s = ln.strip()
        if not s or s.startswith(("File \"", "Traceback", "^", "~")) or re.match(r"^\s*(at |\.\.\.)", s):
            continue
        return s
    return ""


def result_html(ps, run):
    """Thẻ kết quả khi push xong: tên task, id, link (mở tab mới), số job Nhận/Gán tay, kết quả kiểm check.zip."""
    ps = ps or {}
    jobs = ps.get("jobs") or []
    n_nhan = sum(1 for j in jobs if j.get("kind") == "nhan")
    n_tay = sum(1 for j in jobs if j.get("kind") == "gan_tay")
    chk = ps.get("check") or {}
    url = str(ps.get("task_url") or "")
    link = (f'<a class="push-link" href="{_e(url)}" target="_blank" rel="noopener">{_e(url)}</a>' if url.startswith(("http://", "https://")) else "")
    kiem = (f'Kiểm sau khi nhập: <b>{chk.get("n_day_du", "?")}/{chk.get("n_nhan", "?")}</b> mặt Nhận có đủ 50 điểm kèm low_conf'
            + (" (đạt)" if chk.get("ok") else " (KHÔNG đạt)")) if chk else ""
    warn = "".join(f'<div class="m28-warn">{_e(w)}</div>' for w in ps.get("canh_bao", []))
    return (f'<div class="nap-box nap-ok push-done" role="status"><b>Đã đẩy lên CVAT.</b>'
            f'<table class="m28-info"><tr><th>Task</th><td><b>{_e(ps.get("task", "?"))}</b> (id {_e(ps.get("task_id", "?"))})</td></tr>'
            f'<tr><th>Mở trong CVAT</th><td>{link}</td></tr>'
            f'<tr><th>Số job</th><td><b>{len(jobs)}</b> ({n_nhan} Nhận, {n_tay} Gán tay)</td></tr></table>{kiem}{warn}</div>')


def next_step(ps, run):
    """Bước tiếp theo theo push.json sau khi dừng/lỗi/huỷ (tiếng Việt, kèm lệnh cmd)."""
    st = (ps or {}).get("trang_thai")
    tname = (ps or {}).get("task", f"demo-{run}")
    if st is None or st == "task_deleted":
        return "Chưa tạo task nào trên CVAT: sửa nguyên nhân rồi bấm Đẩy lên CVAT lại."
    if st == "dang_tao":
        return (f"Dừng lúc đang tạo task, chưa có id: chạy python tool\\m28.py push --run {run} --cleanup để xem task cùng tên trên CVAT "
                "(tool không tự xoá) rồi tự xoá trong giao diện CVAT nếu thừa.")
    if st in ("da_tao", "da_nhap"):
        return (f"Task {tname} (id {ps.get('task_id')}) đã tạo trên CVAT, chưa xong: chạy python tool\\m28.py push --run {run} --resume "
                f"để làm nốt, hoặc xoá task dở bằng nút Xoá task trên CVAT (tab Các đợt) / python tool\\m28.py push --run {run} --cleanup --confirm-name {tname}.")
    return ""


def error_html(snap, ps, run):
    """Nguyên nhân (dòng cuối của tiến trình con) + bước tiếp theo. Không hiện traceback (nằm trong push_log.txt)."""
    cause = last_message(snap["lines"]) or "Tiến trình push kết thúc với lỗi."
    if cause.startswith(("Exception", "ValueError", "KeyError", "TypeError", "OSError")) or "Error:" in cause[:40]:
        cause = "Lỗi không lường trước (" + cause[:160] + "). Chi tiết trong runs\\" + run + "\\push_log.txt."
    cause = cvat_io.scrub(cause)
    return (f'<div class="nap-box nap-err" role="alert"><b>Đẩy lên CVAT không xong.</b><div class="push-cause">{_e(cause)}</div>'
            f'<div class="nap-note">{_e(next_step(ps, run))}</div></div>')


def cancelled_html(ps, run):
    return (f'<div class="nap-box nap-warn" role="status"><b>Đã huỷ.</b> {_e(next_step(ps, run) or "Không có gì dở trên CVAT.")}</div>')


# ---------- xoá task trên CVAT ----------
def delete_model(run_dir, project_root, *, environ=None, job_running=False):
    """Mô hình nút Xoá task: dict(ok, reason, task, task_id, url, state, run). ok chỉ khi mọi điều kiện an toàn đã thoả
    (sau đó tiến trình con còn kiểm lại với CVAT thật)."""
    pipe = pipeline_of(project_root)
    run = os.path.basename(os.path.normpath(run_dir))
    ps = dot_anh.read_push(run_dir) or {}
    st, name, tid = ps.get("trang_thai"), ps.get("task"), ps.get("task_id")
    env = env_state(environ)
    m = dict(ok=False, reason="", task=name, task_id=tid, url=ps.get("cvat_url", ""), state=st, run=run, env=env, pipe=pipe)
    if st not in ("xong", "da_tao", "da_nhap"):
        m["reason"] = "Lượt này chưa có task nào của tool trên CVAT (push.json không ghi id)."
    elif not isinstance(name, str) or not name.startswith("demo-") or not name.startswith(pipe["prefix"]):
        m["reason"] = "Tên task trong push.json không bắt đầu bằng demo-: từ chối xoá."
    elif not isinstance(tid, int) or isinstance(tid, bool) or tid <= 0:
        m["reason"] = "push.json không có id task hợp lệ."
    elif job_running or dot_anh.run_busy(run_dir):
        m["reason"] = "Lượt đang có việc chạy (đẩy lên CVAT hoặc chuẩn bị): chờ xong rồi xoá."
    elif not env["ok"]:
        m["reason"] = env["reason"] + " " + "Đặt biến môi trường như hướng dẫn ở khung Đẩy lên CVAT rồi mở lại trang."
    elif env["url"] != cvat_io.norm_url(ps.get("cvat_url")):
        m["reason"] = f"Task này nằm ở {cvat_io.norm_url(ps.get('cvat_url'))} nhưng CVAT_URL đang là {env['url']}: id task chỉ có nghĩa trên đúng server đã đẩy."
    else:
        m["ok"] = True
    return m


def delete_confirm_ok(model, typed, checked):
    """Nút xác nhận chỉ bật khi gõ ĐÚNG tên task (phân biệt hoa thường, không bỏ khoảng trắng) và tick ô hiểu hậu quả."""
    return bool(model.get("ok")) and typed == model.get("task") and bool(checked)


def delete_confirm_html(m):
    from m28core.push import delete_warning
    lines = delete_warning(m["task"], m["task_id"], m["url"])
    items = "".join(f"<li>{_e(x)}</li>" for x in lines)
    return ('<div class="modal-title modal-danger" id="task-modal-title">Xoá task trên CVAT?</div>'
            f'<div class="nap-box nap-err" role="alert"><b>Không hoàn tác được.</b><ul>{items}</ul></div>'
            f'<div class="nap-note">Nếu cần giữ nhãn đã sửa: đóng hộp này, chạy <code>python tool\\m28.py collect --task {_e(m["task"])} --reviewer {_e("<tên bạn>")}</code> '
            'trước, rồi quay lại xoá. Token không nhập ở trang này (chỉ đọc từ biến môi trường).</div>')
