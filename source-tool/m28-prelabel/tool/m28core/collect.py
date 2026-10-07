"""Bước collect: THU nhãn đã sửa từ CVAT về raw/ rồi lập báo cáo outputs/collect_<tag>.md.

Chỉ XUẤT: không bao giờ import_annotations, không tạo/sửa/xoá gì trên CVAT. Chỉ thư viện chuẩn + cvat_sdk (nạp lười).
Nhận nhiều --task. Task bắt đầu `demo-` (và không --skip-export): tìm theo tên, xuất "CVAT for images 1.1" chỉ nhãn vào
raw/<task>_<người>_<ngàyDDMM>.xml + .txt cùng tên (bản server, id, số ảnh, giờ tạo theo giờ Việt Nam, job và stage/state), KHÔNG ghi đè.
Task khác (ví dụ m28-manual): không bao giờ gọi CVAT, chỉ đọc raw/<task>_*_*.xml đã có. --dry-run: chỉ liệt kê job, không ghi file nào.
Mọi đường ghi nằm trong raw/ và outputs/ của thư mục chạy.
"""
import datetime
import glob
import importlib
import json
import os
import re
import sys
import tempfile
import time
import traceback

from . import cvat_io as io_

RAW, OUT = "raw", "outputs"
RAW_RE = re.compile(r"^(?P<task>.+)_(?P<who>[A-Za-z0-9-]+)_(?P<day>\d{4})\.xml$")


def _point_names(cfg_path):
    import json
    try:
        with open(cfg_path, encoding="utf-8") as f:
            return [p["name"] for p in json.load(f)["points"]]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _vn_time(dt):
    if isinstance(dt, datetime.datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(io_.VN_TZ).strftime("%Y-%m-%d %H:%M") + " (giờ Việt Nam, UTC+7)"
    return str(dt)


def _jobs_info(task):
    out = []
    for j in sorted(task.get_jobs(), key=lambda j: j.start_frame):
        out.append(dict(id=j.id, n=j.stop_frame - j.start_frame + 1, stage=str(j.stage), state=str(j.state)))
    return out


def _meta_text(task, version, url, who, jobs):
    lines = [f"task: {task.name}", f"task_id: {task.id}", f"cvat_url: {io_.norm_url(url)}", f"ban_server: {version}",
             f"so_anh: {task.size}", f"task_tao_luc: {_vn_time(getattr(task, 'created_date', None))}", f"nguoi_xuat: {who}",
             f"xuat_luc: {datetime.datetime.now(io_.VN_TZ).strftime('%Y-%m-%d %H:%M')} (giờ Việt Nam, UTC+7)", f"so_job: {len(jobs)}"]
    lines += [f"job {j['id']}: {j['n']} frame, stage {j['stage']}, state {j['state']}" for j in jobs]
    return "\n".join(lines) + "\n"


def _jobs_from_txt(txt_path):
    jobs = []
    try:
        with open(txt_path, encoding="utf-8") as f:
            for ln in f:
                m = re.match(r"job (\d+): (\d+) frame, stage (\S+), state (\S+)", ln.strip())
                if m:
                    jobs.append(dict(id=int(m.group(1)), n=int(m.group(2)), stage=m.group(3), state=m.group(4)))
    except OSError:
        return None
    return jobs


def latest_raw_files(task, raw_dir=RAW):
    """{người: đường dẫn file mới nhất} của raw/<task>_<người>_<DDMM>.xml (mới nhất theo ngày trong tên, rồi theo mtime)."""
    best = {}
    for p in glob.glob(os.path.join(raw_dir, glob.escape(task) + "_*_*.xml")):
        m = RAW_RE.match(os.path.basename(p))
        if not m or m.group("task") != task:
            continue
        day = m.group("day")
        key = (day[2:] + day[:2], os.path.getmtime(p))            # MMDD cho so sánh theo ngày trong năm
        who = m.group("who")
        if who not in best or key > best[who][0]:
            best[who] = (key, p)
    return {w: p for w, (_k, p) in sorted(best.items())}


def push_info(task, runs_dir="runs"):
    """Thông tin Gán tay của task demo-… từ runs/*/push.json bản 2 (phien_ban >= 2) có `task` trùng tên: dict(run, tay_nhap=[tên file],
    n_tay_nhap, n_tay_trong) hoặc None (không có lượt nào, hoặc là lượt cũ/task thí nghiệm m28-…: báo cáo giữ như cũ). Chỉ đọc."""
    best = None
    for p in glob.glob(os.path.join(runs_dir, "*", "push.json")):
        try:
            with open(p, encoding="utf-8") as f:
                st = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(st, dict) or st.get("task") != task or not isinstance(st.get("phien_ban"), int) or st["phien_ban"] < 2:
            continue
        co = st.get("gan_tay_co_nhap")
        if not isinstance(co, list):
            continue
        sa = st.get("so_anh") if isinstance(st.get("so_anh"), dict) else {}
        key = str(st.get("cap_nhat") or "")
        if best is None or key > best[0]:
            tong = sa.get("gan_tay") if isinstance(sa.get("gan_tay"), int) else len(co)
            best = (key, dict(run=os.path.basename(os.path.dirname(p)), tay_nhap=[str(x) for x in co], n_tay_nhap=len(co),
                              n_tay_trong=max(tong - len(co), 0)))
    return best[1] if best else None


def analyze(xml_bytes, point_names, tay_nhap=None):
    """Số liệu của một file xuất: ảnh, mặt có skeleton, mặt đủ điểm, điểm thiếu, điểm low_conf bật.
    tay_nhap (tên file các mặt Gán tay có nháp, từ push.json bản 2): thêm n_low_on_nhan / n_low_on_tay (low_conf bật ở mặt Gán tay có nháp)."""
    ann = io_.parse_annotations(xml_bytes)
    need = set(point_names)
    groups = io_.groups_from_names(point_names)
    n_face = n_full = miss = low_on = low_tay = 0
    gan = set(tay_nhap or ())
    for name, im in ann.items():
        sks = [s for s in im["skeletons"] if s["label"] in groups]        # mỗi mặt có bảy skeleton (mỗi nhóm một, QĐ-004): gộp điểm của cả bảy
        if not sks:
            continue
        n_face += 1
        have = {n for sk in sks for n, p in sk["points"].items() if p.get("x") is not None and n in need}
        if have == need:
            n_full += 1
        miss += len(need - have)
        k = sum(1 for sk in sks for p in sk["points"].values() if p.get("low_conf") == "true")
        low_on += k
        if name in gan:
            low_tay += k
    res = dict(n_images=len(ann), n_face=n_face, n_full=n_full, n_missing=miss, n_low_on=low_on)
    if tay_nhap is not None:
        res.update(n_low_on_nhan=low_on - low_tay, n_low_on_tay=low_tay)
    return res


def _qc_line(paths, out_dir):
    try:
        mod = importlib.import_module("m28core.qc")
    except ModuleNotFoundError as e:
        if e.name != "m28core.qc":
            raise
        return "Chưa có QC của P2 (m28core.qc), bỏ qua."
    run = getattr(mod, "run", None)
    if not callable(run):
        return "m28core.qc không có hàm run(xml_paths, outputs_dir) (chưa khớp giả định), bỏ qua."
    try:
        res = run(list(paths), out_dir)
    except Exception as e:                                       # QC lỗi không làm hỏng việc thu
        return f"QC của P2 báo lỗi ({type(e).__name__}: {io_.scrub(e)[:200]}), bỏ qua."
    return f"QC của P2: {res}" if res else "QC của P2 đã chạy."


def collect(args):
    """Trả True khi xong. Lỗi người dùng sửa được: SystemExit tiếng Việt."""
    t_all = time.time()
    tasks = []
    for t in getattr(args, "task", None) or []:
        io_.safe_file_part(t)
        if t not in tasks:
            tasks.append(t)
    if not tasks:
        raise SystemExit("collect cần ít nhất một --task.")
    reviewer = io_.safe_file_part(getattr(args, "reviewer", None) or "RA")
    skip, dry = bool(getattr(args, "skip_export", False)), bool(getattr(args, "dry_run", False))
    pipe = io_.load_pipeline(getattr(args, "pipeline", None))
    cfg_path = getattr(args, "config", None) or os.path.join("config", "m28_config.json")
    point_names = _point_names(cfg_path)
    if point_names is None:
        raise SystemExit(f"Không đọc được {cfg_path}: cần 50 tên điểm để kiểm nhãn thu về.")
    demo = [t for t in tasks if t.startswith(io_.SAFE_PREFIX)]
    other = [t for t in tasks if t not in demo]
    for t in other:
        print(f"{t}: không phải task {io_.SAFE_PREFIX}…, không gọi CVAT; chỉ đọc raw\\{t}_*_*.xml đã có.")
    day = datetime.datetime.now().strftime("%d%m")
    files, missing, timings, notes, job_rows = {}, [], {}, [], {}
    exporting = [] if skip else demo
    if reviewer == "RA" and exporting and not dry:
        print("Nhắc: chưa có --reviewer nên file raw ghi tên người là RA; nên chạy lại với --reviewer P4 (đúng người xuất).")
    if exporting:
        env = io_.read_env()
        print(io_.status_line(env), flush=True)
        bad = io_.env_problem(env)
        if bad:
            raise SystemExit(bad)
        t0 = time.time()
        try:
            client = io_.connect(env)
        except SystemExit:
            raise
        except Exception as e:
            raise SystemExit(io_.translate_error(e, env, "kết nối") or f"Không kết nối được CVAT: {type(e).__name__}.")
        doing = "kết nối"
        try:
            with client:
                doing = "kiểm bản server"
                ver = io_.check_version(client, pipe["cvat_version"])
                doing = "liệt kê task"
                all_tasks = list(client.tasks.list())
                timings["kết nối"] = time.time() - t0
                for name in exporting:
                    found = [t for t in all_tasks if t.name == name]
                    if not found:
                        print(f"{name}: KHÔNG thấy task tên này trên CVAT, bỏ qua.")
                        missing.append(f"{name} (không có trên CVAT)")
                        continue
                    if len(found) > 1:
                        print(f"{name}: có {len(found)} task trùng tên (id {[t.id for t in found]}), không biết lấy cái nào: bỏ qua. "
                              "Xoá hoặc đổi tên bản thừa trong CVAT.")
                        missing.append(f"{name} (trùng tên {len(found)} task)")
                        continue
                    task = found[0]
                    doing = f"đọc job của {name}"
                    jobs = _jobs_info(task)
                    job_rows[name] = jobs
                    print(f"{name}: id {task.id}, {task.size} ảnh, {len(jobs)} job")
                    for j in jobs:
                        print(f"  job {j['id']}: {j['n']} frame, stage {j['stage']}, state {j['state']}")
                    if dry:
                        continue
                    base = os.path.join(RAW, f"{name}_{reviewer}_{day}")
                    xml_path, txt_path = base + ".xml", base + ".txt"
                    if not io_.inside(xml_path, RAW):
                        raise SystemExit(f"Đường dẫn {xml_path} nằm ngoài raw\\: từ chối.")
                    if os.path.exists(xml_path):
                        print(f"  {xml_path} đã có: KHÔNG ghi đè, dùng file này (muốn xuất lần hai thì đổi --reviewer hoặc chờ sang ngày khác).")
                        files[name] = {reviewer: xml_path}
                        continue
                    doing = f"xuất nhãn của {name}"
                    t1 = time.time()
                    os.makedirs(RAW, exist_ok=True)
                    with tempfile.TemporaryDirectory() as tmp:
                        z = os.path.join(tmp, "export.zip")
                        task.export_dataset(io_.FORMAT_EXPORT, z, include_images=False)
                        data = io_.read_zip_annotations(z)
                    tmpx = xml_path + f".tmp{os.getpid()}"
                    with open(tmpx, "wb") as f:
                        f.write(data)
                    os.replace(tmpx, xml_path)
                    with open(txt_path, "w", encoding="utf-8", newline="\n") as f:
                        f.write(_meta_text(task, ver, env["url"], reviewer, jobs))
                    timings[f"xuất {name}"] = time.time() - t1
                    print(f"  đã ghi {xml_path} và {txt_path}")
                    files[name] = {reviewer: xml_path}
        except SystemExit:
            raise
        except Exception as e:
            msg = io_.translate_error(e, env, doing)
            if msg is None:
                print(io_.scrub("".join(traceback.format_exception(type(e), e, e.__traceback__))), file=sys.stderr, flush=True)
                msg = f"Lỗi không lường trước khi {doing}: {type(e).__name__}: {io_.scrub(e)[:300]}"
            raise SystemExit(io_.scrub(msg))
    if dry:
        print("Chạy thử (--dry-run): chỉ liệt kê job, không ghi file nào.")
        return True
    for name in tasks:                                           # task đọc từ raw/: --skip-export, hoặc không phải demo-
        if name not in files:
            found = latest_raw_files(name)
            if found:
                files[name] = found
            elif not any(m.startswith(name + " ") for m in missing):
                missing.append(f"{name} (chưa có raw\\{name}_*_*.xml)")
    # phân tích và báo cáo
    t2 = time.time()
    lines = [f"# Báo cáo collect: {', '.join(tasks)}", "",
             f"Lập lúc {datetime.datetime.now(io_.VN_TZ).strftime('%Y-%m-%d %H:%M')} (giờ Việt Nam). Chỉ đọc nhãn đã xuất; không sửa gì trên CVAT.", ""]
    all_paths = []
    for name in tasks:
        lines.append(f"## {name}")
        if name not in files:
            lines += ["Chưa có file nhãn nào.", ""]
            continue
        for who, path in files[name].items():
            pinfo = push_info(name) if name.startswith(io_.SAFE_PREFIX) else None        # chỉ task demo-… của m28.py push bản mới
            with open(path, "rb") as f:
                st = analyze(f.read(), point_names, pinfo["tay_nhap"] if pinfo else None)
            all_paths.append(path)
            lines += [f"- Người: **{who}** · file `{path}`",
                      f"  - Ảnh: {st['n_images']} · mặt có skeleton: {st['n_face']} · mặt đủ {len(point_names)} điểm: {st['n_full']}"
                      f" · điểm thiếu: {st['n_missing']} · điểm low_conf đang bật: {st['n_low_on']}"]
            if pinfo:
                lines += [f"  - Gán tay: {pinfo['n_tay_nhap']} có nháp, {pinfo['n_tay_trong']} ảnh trống (theo runs\\{pinfo['run']}\\push.json)",
                          f"  - low_conf đang bật: {st['n_low_on_nhan']} ở mặt Nhận · {st['n_low_on_tay']} ở mặt Gán tay có nháp "
                          "(bật sẵn từ máy, người gán chưa tắt)"]
            jobs = job_rows.get(name) or _jobs_from_txt(os.path.splitext(path)[0] + ".txt")
            if jobs is None:
                lines.append("  - Chưa có thông tin job (không có file .txt cạnh file xuất).")
            else:
                pend = [j for j in jobs if j["state"] != "completed"]
                lines.append(f"  - Job: {len(jobs)}" + (f" · **chưa sửa xong (state khác completed): {len(pend)}** "
                             + ", ".join(f"job {j['id']} ({j['stage']}/{j['state']})" for j in pend) if pend else " · tất cả completed"))
        lines.append("")
    lines += ["## File còn thiếu", ""] + ([f"- {m}" for m in missing] if missing else ["Không thiếu."]) + [""]
    timings["phân tích"] = time.time() - t2
    lines += ["## QC", "", _qc_line(all_paths, OUT), "", "## Thời gian từng bước", ""]
    timings["tổng"] = time.time() - t_all
    lines += [f"- {k}: {v:.1f} giây" for k, v in timings.items()]
    tag = io_.safe_file_part(getattr(args, "tag", None) or tasks[0])
    out_path = os.path.join(OUT, f"collect_{tag}.md")
    if not io_.inside(out_path, OUT):
        raise SystemExit(f"Đường dẫn {out_path} nằm ngoài outputs\\: từ chối.")
    os.makedirs(OUT, exist_ok=True)
    tmp = out_path + f".tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, out_path)
    print(f"collect xong: báo cáo {out_path}" + (f" · còn thiếu: {len(missing)}" if missing else ""))
    return True
