"""Bước collect: THU nhãn đã sửa từ CVAT về raw/ rồi lập báo cáo outputs/collect_<tag>.md.

Chỉ XUẤT: không bao giờ import_annotations, không tạo/sửa/xoá gì trên CVAT. Chỉ thư viện chuẩn + cvat_sdk (nạp lười).
Nhận nhiều --task. Task bắt đầu `demo-` (và không --skip-export): tìm theo tên, xuất "CVAT for images 1.1" chỉ nhãn vào
raw/<task>_<người>_<ngàyDDMM>.xml + .txt cùng tên (bản server, id, số ảnh, giờ tạo theo giờ Việt Nam, job với frame, loại và stage/state), KHÔNG ghi đè.
Task khác (ví dụ m28-manual): không bao giờ gọi CVAT, chỉ đọc raw/<task>_*_*.xml đã có. --dry-run: chỉ liệt kê job, không ghi file nào.
Tách theo JOB (--per-job / --no-per-job / --job <id>): từ file cả task vừa xuất (hoặc đã có trong raw/) tách OFFLINE ra
raw/<task>_<người>_<DDMM>_job<id>.xml (+ .txt) cho từng job mà push đã chia (module m28core/tach_job.py, không thêm lời gọi CVAT nào).
Mặc định bật cho task demo-…, tắt cho task khác; --job <id> (nhiều lần được) chỉ ghi file của job đó (file cả task vẫn xuất như cũ) và tự bật tách.
File job chỉ để đọc/đo (eval50, QC), KHÔNG nhập lại vào CVAT; RAW_RE/latest_raw_files bỏ qua chúng nên không đếm một mặt hai lần.
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
from . import tach_job
from .tach_job import push_jobs  # noqa: F401  (tra loại job từ push.json; dùng cả ở đây lẫn trong tach_job)

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


def _jobs_info(task, kinds=None):
    """[dict(id, n, stage, state, start, stop, kind)] của task theo start_frame; kinds = {job_id: nhan|gan_tay} từ push.json (thiếu thì khong_ro)."""
    out = []
    for j in sorted(task.get_jobs(), key=lambda j: j.start_frame):
        out.append(dict(id=j.id, n=j.stop_frame - j.start_frame + 1, stage=str(j.stage), state=str(j.state),
                        start=j.start_frame, stop=j.stop_frame, kind=(kinds or {}).get(j.id, "khong_ro")))
    return out


def _meta_text(task, version, url, who, jobs):
    lines = [f"task: {task.name}", f"task_id: {task.id}", f"cvat_url: {io_.norm_url(url)}", f"ban_server: {version}",
             f"so_anh: {task.size}", f"task_tao_luc: {_vn_time(getattr(task, 'created_date', None))}", f"nguoi_xuat: {who}",
             f"xuat_luc: {datetime.datetime.now(io_.VN_TZ).strftime('%Y-%m-%d %H:%M')} (giờ Việt Nam, UTC+7)", f"so_job: {len(jobs)}"]
    lines += [tach_job.job_line(j) for j in jobs]       # job <id>: <n> frame, stage <s>, state <t> | frames <a>-<b> | loai <nhan|gan_tay|khong_ro>
    return "\n".join(lines) + "\n"


def _jobs_from_txt(txt_path):
    """[dict(id, n, stage, state, start, stop, kind, suy_ra)] đọc từ .txt cạnh file xuất (dòng job cũ lẫn mới), None nếu không mở được file.
    Khoá cũ id, n, stage, state giữ nguyên nghĩa; start/stop tính cộng dồn từ n khi .txt cũ không có `frames` (suy_ra=True); kind mặc định khong_ro."""
    meta = tach_job.read_txt(txt_path)
    return None if meta is None else meta["jobs"]


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




# ---------- tách theo job (offline, từ file cả task) ----------
def _tach_mode(args):
    """(per_job, job_ids): per_job None = tự động (bật cho demo-…, tắt cho task khác), True/False theo cờ; job_ids = danh sách --job (không trùng)."""
    per_job = getattr(args, "per_job", None)
    ids = []
    for x in getattr(args, "job", None) or []:
        try:
            i = int(x)
        except (TypeError, ValueError):
            raise SystemExit(f"--job cần số nguyên (job id), không phải {x!r}.")
        if i not in ids:
            ids.append(i)
    if per_job is False and ids:
        raise SystemExit("--job tự bật tách job nên không đi cùng --no-per-job: bỏ một trong hai.")
    return per_job, ids


def _tach_on(name, per_job, ids):
    if per_job is False:
        return False
    return bool(per_job or ids) or name.startswith(io_.SAFE_PREFIX)


def _txt_job_ids(paths):
    ids = set()
    for p in paths:
        meta = tach_job.read_txt(os.path.splitext(p)[0] + ".txt")
        if meta:
            ids |= {j["id"] for j in meta["jobs"]}
    return ids


def _check_job_ids(ids, valid):
    """valid = {task: {job id}}. Id không thuộc job nào của các task đã nêu thì SystemExit (gọi TRƯỚC khi xuất hay ghi bất kỳ file nào)."""
    known = set()
    for v in valid.values():
        known |= v
    bad = [i for i in ids if i not in known]
    if bad:
        have = "; ".join(f"{t}: {', '.join(str(i) for i in sorted(v))}" for t, v in valid.items() if v) or "chưa thấy job nào (task chưa xuất, thiếu file .txt)"
        raise SystemExit(f"--job {', '.join(str(i) for i in bad)} không thuộc job nào của các task đã nêu. Job hợp lệ: {have}. Chưa xuất và chưa ghi file nào.")


def _job_files_text(res):
    """Một dòng mỗi job của kết quả tách để in ra màn hình."""
    out = []
    for j in res["jobs"]:
        s = f"    job {j['id']} ({j['kind']}) frames {j['start']}-{j['stop']}: {j['n_anh']}/{j['n']} ảnh -> {j['path']}"
        out.append(s + (" đã có: KHÔNG ghi đè" if j["da_co"] else ""))
        out += [f"      cảnh báo: {w}" for w in j["canh_bao"]]
    return out


def _job_table(res, point_names):
    """Bảng markdown 'Theo job' cho một file cả task đã tách (số liệu tính bằng analyze trên bytes của chính file job)."""
    head = [f"  - Theo job (file job chỉ để đọc/đo, không nhập lại vào CVAT; {res['kiem_lech']}):", "",
            f"    | job | loại | frame | ảnh/frame | ảnh có nhãn | mặt đủ {len(point_names)} điểm | điểm thiếu | low_conf bật | stage/state | file |",
            "    |---|---|---|---|---|---|---|---|---|---|"]
    for j in res["jobs"]:
        try:
            with open(j["path"], "rb") as f:
                st = analyze(f.read(), point_names)
            cells = [str(st["n_face"]), str(st["n_full"]), str(st["n_missing"]), str(st["n_low_on"])]
        except (OSError, SystemExit):
            cells = ["?"] * 4
        name = f"`{j['path']}`" + (" (đã có từ trước)" if j["da_co"] else "")
        head.append(f"    | {j['id']} | {j['kind']} | {j['start']}-{j['stop']} | {j['n_anh']}/{j['n']} | " + " | ".join(cells)
                    + f" | {j['stage']}/{j['state']} | {name} |")
    return head + [""]


def _dry_plan(name, base_xml, jobs, ids):
    """In kế hoạch tách job (dry-run): frame, loại và tên file job sẽ ghi; đánh dấu job được chọn bởi --job."""
    for j in jobs:
        sel = not ids or j["id"] in ids
        dest = tach_job.job_path(base_xml, RAW, j["id"])
        print(f"    {'sẽ ghi' if sel else 'bỏ qua (không được chọn bởi --job)'}: job {j['id']} ({j['kind']}) frames {j['start']}-{j['stop']} -> {dest}"
              + ("  [được chọn bởi --job]" if ids and sel else ""))


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
    per_job, job_ids = _tach_mode(args)
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

    def valid_ids(found):
        """{task: {job id hợp lệ}}: job trên CVAT (task vừa liệt kê) cộng job trong .txt của file sẽ dùng/tách (file đã có hoặc file mới nhất trong raw/)."""
        out = {}
        for name in tasks:
            v = {j["id"] for j in found[name][1]} if name in found else set()
            if name in exporting:
                target = os.path.join(RAW, f"{name}_{reviewer}_{day}.xml")
                v |= _txt_job_ids([target] if os.path.exists(target) else [])
            else:
                v |= _txt_job_ids(latest_raw_files(name).values())
            out[name] = v
        return out

    if job_ids and not exporting:
        _check_job_ids(job_ids, valid_ids({}))                      # không phải xuất: kiểm ngay, trước khi ghi bất kỳ file nào
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
                found_tasks = {}
                for name in exporting:                          # lượt 1: liệt kê job của mọi task (chưa xuất gì)
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
                    jobs = _jobs_info(task, (push_jobs(name, task_id=task.id) or {}).get("kinds"))
                    job_rows[name] = jobs
                    found_tasks[name] = (task, jobs)
                    print(f"{name}: id {task.id}, {task.size} ảnh, {len(jobs)} job")
                    for j in jobs:
                        print(f"  {tach_job.job_line(j)}")
                    if dry and _tach_on(name, per_job, job_ids):
                        _dry_plan(name, os.path.join(RAW, f"{name}_{reviewer}_{day}.xml"), jobs, job_ids)
                if job_ids:
                    _check_job_ids(job_ids, valid_ids(found_tasks))         # trước export_dataset đầu tiên
                for name, (task, jobs) in found_tasks.items():              # lượt 2: xuất
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
        for name in tasks:                                       # task đọc từ raw/: in kế hoạch tách job từ .txt (chỉ đọc)
            if name in exporting or not _tach_on(name, per_job, job_ids):
                continue
            for who, p in latest_raw_files(name).items():
                meta = tach_job.read_txt(os.path.splitext(p)[0] + ".txt")
                print(f"{name} ({who}): " + (f"{len(meta['jobs'])} job theo .txt" if meta else "chưa có .txt cạnh file xuất: không biết ranh giới job"))
                if meta and meta["jobs"]:
                    try:
                        _dry_plan(name, p, meta["jobs"], job_ids)
                    except tach_job.TachJobLoi as e:
                        print(f"    {io_.scrub(e)}")
        print("Chạy thử (--dry-run): chỉ liệt kê job, không ghi file nào.")
        return True
    for name in tasks:                                           # task đọc từ raw/: --skip-export, hoặc không phải demo-
        if name not in files:
            found = latest_raw_files(name)
            if found:
                files[name] = found
            elif not any(m.startswith(name + " ") for m in missing):
                missing.append(f"{name} (chưa có raw\\{name}_*_*.xml)")
    # tách theo job (offline, không gọi thêm CVAT): từ chính file cả task đã có/vừa xuất, theo .txt cạnh nó
    t_split = time.time()
    split_res, split_notes, split_on = {}, {}, False
    for name in tasks:
        if name not in files or not _tach_on(name, per_job, job_ids):
            continue
        for who, path in files[name].items():
            split_on = True
            meta = tach_job.read_txt(os.path.splitext(path)[0] + ".txt")
            only = None
            if job_ids and meta is not None:
                only = [i for i in job_ids if i in {j["id"] for j in meta["jobs"]}]
                if not only:
                    print(f"  tách job {name} ({who}): không có job nào trong --job {job_ids} (job của file này: "
                          f"{', '.join(str(j['id']) for j in meta['jobs'])}): không ghi file job.")
                    continue
            try:
                res = tach_job.tach(path, RAW, only=only)
            except tach_job.TachJobLoi as e:
                msg = io_.scrub(str(e))
                print(f"  tách job {name} ({who}): KHÔNG tách được: {msg}")
                split_notes.setdefault((name, who), []).append(msg)
                continue
            except Exception as e:                                # lỗi tách không làm mất file cả task, không chặn task khác
                msg = f"Lỗi không lường trước khi tách job ({type(e).__name__}): {io_.scrub(e)[:300]}"
                print(f"  tách job {name} ({who}): {msg}")
                split_notes.setdefault((name, who), []).append(msg)
                continue
            split_res[(name, who)] = res
            print(f"  tách job {name} ({who}): {len(res['jobs'])} job từ {res['nguon']}")
            for ln in _job_files_text(res):
                print(ln)
            warns = [f"job {j['id']}: {w}" for j in res["jobs"] for w in j["canh_bao"]]
            suy = [str(j["id"]) for j in res["jobs"] if j["suy_ra"]]
            if suy:
                warns.append(f"frame của job {', '.join(suy)} suy ra từ số frame cộng dồn (.txt cũ không có trường frames)")
            if warns:
                split_notes[(name, who)] = warns
    if split_on:
        timings["tách job"] = time.time() - t_split
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
            if (name, who) in split_res:
                lines += _job_table(split_res[(name, who)], point_names)
        lines.append("")
    lines += ["## File còn thiếu", ""] + ([f"- {m}" for m in missing] if missing else ["Không thiếu."]) + [""]
    if split_notes:
        lines += ["## Tách job", ""]
        for (name, who), msgs in split_notes.items():
            lines += [f"- {name} ({who}): {m}" for m in msgs]
        lines.append("")
    timings["phân tích"] = time.time() - t2
    lines += ["## QC", "", _qc_line(all_paths, OUT)]
    if split_res:
        lines += ["", "File job không đưa vào QC để không đếm hai lần (QC chỉ nhận file cả task)."]
    lines += ["", "## Thời gian từng bước", ""]
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
