"""Bước push: tạo task MỚI `demo-…` trong project m28 trên CVAT, tải ảnh, nhập nhãn nháp ĐÚNG MỘT LẦN, xuất lại để kiểm.
Thêm: xoá đúng task mà chính tool đã tạo (delete_task / cleanup).

Chỉ thư viện chuẩn + cvat_sdk (nạp lười trong hàm, nên import module này khi chưa cài SDK vẫn chạy). Không numpy/gradio/torch.
CVAT_URL, CVAT_ACCESS_TOKEN (và tuỳ chọn CVAT_ORG) đọc từ biến môi trường; chỉ in "token: có/thiếu", không bao giờ in/ghi giá trị token.

Nguyên tắc an toàn (kiểm TRƯỚC khi kết nối):
  * prefix phải bắt đầu bằng `demo-` và tên task phải bắt đầu bằng prefix: task `m28-…` không bao giờ bị tạo, nhập, xuất hay xoá.
  * runs/<lượt>/push.json chống đẩy hai lần. trang_thai: dang_tao -> da_tao -> da_nhap -> xong; hoặc task_deleted sau khi xoá task
    (lúc đó đẩy lại được). dang_tao/da_tao/da_nhap dở thì --resume (chỉ làm phần còn lại trên ĐÚNG task_id) hoặc --cleanup.
  * Xoá task chỉ theo id ghi trong push.json, sau khi lấy lại task theo id từ CVAT và kiểm tên khớp push.json, tên bắt đầu `demo-`,
    thuộc project m28, cùng CVAT_URL với lúc push; phải có xác nhận gõ lại đúng tên task. Không bao giờ tìm task theo tên để xoá.

Hợp đồng với steps.push: push(run_dir, task_name, nhan_imgs, tay_imgs, xml_path, project=, prefix=, label_json=) trả đường dẫn
check.zip; lỗi là SystemExit("<lý do tiếng Việt>"). In các dòng "[k/6] <pha> …" cho trang rà soát đọc tiến độ, và dòng cuối
"push xong: task <tên> id <id>, <n> job (<a> Nhận, <b> Gán tay), <url>".
"""
import json
import os
import sys
import time
import traceback
import xml.etree.ElementTree as ET

from . import cvat_io as io_
from . import dang_chay

PUSH_JSON = "push.json"
S_DANG_TAO, S_DA_TAO, S_DA_NHAP, S_XONG, S_DELETED = "dang_tao", "da_tao", "da_nhap", "xong", "task_deleted"
STATE_VI = {S_DANG_TAO: "đang tạo task (chưa có id)", S_DA_TAO: "đã tạo task, chưa nhập nhãn", S_DA_NHAP: "đã nhập nhãn, chưa kiểm xong",
            S_XONG: "xong", S_DELETED: "task đã xoá trên CVAT"}
PHASES = ["kiểm tra", "kết nối", "project", "tải ảnh", "nhập nhãn", "xuất kiểm"]      # [k/6] theo thứ tự này
MAX_NAME = 128
LABEL = "face50"


def _say(k, text):
    print(f"[{k}/{len(PHASES)}] {PHASES[k - 1]}: {text}", flush=True)


# ---------- push.json ----------
def pj_path(run_dir):
    return os.path.join(run_dir, PUSH_JSON)


def read_state(run_dir):
    """Nội dung push.json hoặc None nếu chưa có. File hỏng thì SystemExit (không đoán)."""
    p = pj_path(run_dir)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            st = json.load(f)
    except (OSError, ValueError) as e:
        raise SystemExit(f"Không đọc được {p} ({e}). Mở file xem task đã tạo trên CVAT chưa, sửa tay cho đúng JSON hoặc xoá file "
                         "(chỉ xoá khi chắc chắn chưa có task nào trên CVAT).")
    if not isinstance(st, dict):
        raise SystemExit(f"{p} sai định dạng (cần đối tượng JSON).")
    return st


def write_state(run_dir, st):
    st["cap_nhat"] = io_.now_iso()
    io_.atomic_write_json(pj_path(run_dir), st)


def _run_name(run_dir):
    return os.path.basename(os.path.normpath(run_dir))


def _fail(run_dir, st, msg):
    """Ghi lý do vào push.json (nếu đã có file) rồi dừng với thông báo tiếng Việt đã lọc token."""
    msg = io_.scrub(msg)
    if st is not None and os.path.exists(pj_path(run_dir)):
        try:
            st["loi"] = msg[:600]
            write_state(run_dir, st)
        except OSError:
            pass
    raise SystemExit(msg)


# ---------- kiểm an toàn (trước khi kết nối) ----------
def check_prefix(prefix):
    if not isinstance(prefix, str) or not prefix.startswith(io_.SAFE_PREFIX):
        raise SystemExit(f"prefix {prefix!r} bị từ chối: chỉ được dùng prefix bắt đầu bằng {io_.SAFE_PREFIX!r}. "
                         "Task m28-… không bao giờ bị tạo hoặc đụng tới.")


def check_task_name(task_name, prefix):
    check_prefix(prefix)
    if not isinstance(task_name, str) or not task_name.startswith(prefix):
        raise SystemExit(f"Chỉ tạo task {prefix}… (đang là {task_name!r}); không bao giờ đẩy vào task m28-…")
    if len(task_name) <= len(prefix) or any(ord(c) < 32 or ord(c) == 127 for c in task_name) or len(task_name) > MAX_NAME:
        raise SystemExit(f"Tên task {task_name!r} không hợp lệ: cần có chữ sau {prefix}, không ký tự điều khiển, tối đa {MAX_NAME} ký tự.")


def load_label_names(label_json):
    """(danh sách label để tạo project, tên 50 điểm theo thứ tự) từ config/face50_label.json."""
    if not os.path.isfile(label_json):
        raise SystemExit(f"Thiếu {label_json}: chạy python tool\\make_label.py để sinh từ config\\m28_config.json.")
    try:
        with open(label_json, encoding="utf-8") as f:
            labels = json.load(f)
        lb = next(x for x in labels if x.get("name") == LABEL)
        names = [s["name"] for s in lb["sublabels"]]
    except (OSError, ValueError, StopIteration, KeyError, TypeError, AttributeError) as e:
        raise SystemExit(f"{label_json} sai định dạng ({type(e).__name__}): chạy lại python tool\\make_label.py.")
    if len(names) != 50 or len(set(names)) != 50:
        raise SystemExit(f"{label_json} phải có label {LABEL} với đúng 50 sublabel khác tên: chạy lại python tool\\make_label.py.")
    return labels, names


def check_inputs(task_name, prefix, label_json, xml_path, nhan_imgs, tay_imgs):
    check_task_name(task_name, prefix)
    if not nhan_imgs and not tay_imgs:
        raise SystemExit("Không có ảnh nào để đẩy lên (cả Nhận và Gán tay đều trống).")
    if nhan_imgs and not os.path.isfile(xml_path):
        raise SystemExit(f"Thiếu file nhãn nháp {xml_path}: chạy lại bước push để steps ghi XML.")
    missing = [p for p in list(nhan_imgs) + list(tay_imgs) if not os.path.isfile(p)]
    if missing:
        raise SystemExit(f"Không thấy {len(missing)} ảnh để tải lên, ví dụ {missing[0]}.")
    base = [os.path.basename(p) for p in list(nhan_imgs) + list(tay_imgs)]
    dup = sorted({b for b in base if base.count(b) > 1})
    if dup:
        raise SystemExit(f"Tên ảnh trùng, CVAT không nhận hai ảnh cùng tên: {dup[:3]}.")
    return load_label_names(label_json)


def plan_jobs(nhan_imgs, tay_imgs, job_size=8):
    """Chia job: các nhóm job_size mặt Nhận (theo thứ tự đã nhận) + MỘT job Gán tay riêng ở cuối (nếu có).
    Trả (job_file_mapping theo tên file, danh sách kind)."""
    nb = [os.path.basename(p) for p in nhan_imgs]
    tb = [os.path.basename(p) for p in tay_imgs]
    groups = [nb[i:i + job_size] for i in range(0, len(nb), job_size)]
    kinds = ["nhan"] * len(groups)
    if tb:
        groups.append(tb)
        kinds.append("gan_tay")
    return groups, kinds


# ---------- cổng push.json ----------
def _gate(run_dir, task_name, resume):
    """Quyết định theo push.json: ('new', None, truoc_do) | ('resume', st, None)."""
    st = read_state(run_dir)
    run = _run_name(run_dir)
    state = st.get("trang_thai") if st else None
    if resume:
        if state not in (S_DA_TAO, S_DA_NHAP):
            raise SystemExit("--resume chỉ dùng khi lần push trước dừng sau lúc đã tạo task (push.json ghi da_tao hoặc da_nhap); "
                             f"lượt {run} đang ở trạng thái {STATE_VI.get(state, 'chưa push') if st else 'chưa push'}.")
        if st.get("task") != task_name:
            raise SystemExit(f"--resume phải đúng task đã tạo: push.json ghi {st.get('task')!r}, còn lệnh này là {task_name!r}.")
        return "resume", st, None
    if st is None:
        return "new", None, []
    if state == S_DELETED:
        old = {k: st[k] for k in ("task", "task_id", "cvat_url", "task_deleted_at") if k in st}
        return "new", None, list(st.get("truoc_do", [])) + [old]
    name, tid = st.get("task"), st.get("task_id")
    if state == S_XONG:
        raise SystemExit(f"Lượt này đã đẩy lên CVAT: task {name} id {tid}. Không tạo task thứ hai. Muốn đẩy lại thì xoá task đó trước "
                         f"(nút Xoá task trong tab Các đợt, hoặc python tool\\m28.py push --run {run} --cleanup --confirm-name {name}).")
    if state in (S_DA_TAO, S_DA_NHAP):
        raise SystemExit(f"Lần push trước dừng giữa chừng: task {name} id {tid} ({STATE_VI[state]}). Chọn một: "
                         f"python tool\\m28.py push --run {run} --resume (làm nốt phần còn lại trên đúng task đó) hoặc "
                         f"python tool\\m28.py push --run {run} --cleanup --confirm-name {name} (xoá task dở trên CVAT).")
    if state == S_DANG_TAO:
        raise SystemExit(f"Lần push trước chết giữa lúc tạo task {name} (chưa có id). Chạy python tool\\m28.py push --run {run} "
                         "--cleanup: chỉ LIỆT KÊ task cùng tên trên CVAT để bạn tự xoá trong giao diện, rồi xoá push.json.")
    raise SystemExit(f"push.json của lượt {run} có trạng thái lạ {state!r}: mở file kiểm tay.")


# ---------- đọc đối tượng SDK ----------
def _lget(o, key, default=None):
    try:
        return o[key]
    except Exception:
        return getattr(o, key, default)


def project_label_names(project):
    """Tên sublabel của label face50 trong project (đọc từ project.get_labels()); None nếu không có label face50."""
    labels = list(project.get_labels())
    for lb in labels:
        if _lget(lb, "name") == LABEL and str(_lget(lb, "type") or "").lower().endswith("skeleton"):
            subs = _lget(lb, "sublabels")
            if subs:
                return [_lget(s, "name") for s in subs]
            flat = [_lget(s, "name") for s in labels if _lget(s, "has_parent")]
            return flat
    return None


def find_project(client, name):
    found = [p for p in client.projects.list() if p.name == name]
    if len(found) > 1:
        raise SystemExit(f"Có {len(found)} project tên {name} trên CVAT; xoá bản thừa (giữ một) rồi chạy lại.")
    return found[0] if found else None


def check_project_labels(project, point_names):
    got = project_label_names(project)
    if got is None:
        raise SystemExit(f"Project {project.name} đã có nhưng chưa có label {LABEL} (skeleton): xoá project rỗng đó để tool tạo lại "
                         "từ config\\face50_label.json, hoặc import label này vào project. Chưa tạo task nào.")
    miss = [n for n in point_names if n not in set(got)]
    if miss or len(got) != len(point_names):
        raise SystemExit(f"Label {LABEL} trong project {project.name} có {len(got)} sublabel, thiếu {len(miss)} tên so với config "
                         f"(ví dụ {miss[:3]}). Sửa label cho đủ 50 điểm đúng tên hoặc tạo project mới; chưa tạo task nào.")


def get_project_id(client, name, labels, point_names):
    """Tìm project theo tên; chưa có thì tạo từ label_json. Có rồi thì kiểm label face50 đủ 50 sublabel đúng tên."""
    proj = find_project(client, name)
    if proj is None:
        proj = client.projects.create({"name": name, "labels": labels})
        print(f"  đã tạo project {name} (id {proj.id}) từ label {LABEL}", flush=True)
    check_project_labels(proj, point_names)
    return proj.id


def _frame_names(task):
    return [f.name for f in task.get_frames_info()]


def _n_annotations(task):
    a = task.get_annotations()
    return sum(len(_lget(a, k) or []) for k in ("shapes", "tracks", "tags"))


def _jobs_of(task, kinds):
    jobs = sorted(task.get_jobs(), key=lambda j: j.start_frame)
    out = []
    for i, j in enumerate(jobs):
        out.append(dict(id=j.id, start_frame=j.start_frame, stop_frame=j.stop_frame, n=j.stop_frame - j.start_frame + 1,
                        kind=kinds[i] if i < len(kinds) else "?"))
    return out


def _xml_for_frames(xml_path, frames, run_dir):
    """Ghép id ảnh trong XML theo THỨ TỰ FRAME THẬT của task (ghép theo tên ảnh). Giống nhau thì dùng nguyên XML;
    khác thì ghi bản tạm runs/<lượt>/xml/prelabel_cvat.xml (không sửa prelabel.xml gốc)."""
    tree = ET.parse(xml_path)
    idx = {n: i for i, n in enumerate(frames)}
    changed = False
    for im in tree.getroot().iter("image"):
        n = im.get("name")
        if n not in idx:
            raise SystemExit(f"Ảnh {n} có trong XML nhãn nháp nhưng không có trong task trên CVAT: dừng, chưa nhập nhãn.")
        if im.get("id") != str(idx[n]):
            im.set("id", str(idx[n]))
            changed = True
    if not changed:
        return xml_path
    out = os.path.join(run_dir, "xml", "prelabel_cvat.xml")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tree.write(out, encoding="utf-8", xml_declaration=True)
    return out


def _verify_identity(client, st, prefix, project):
    """Lấy lại task theo id từ CVAT và kiểm: tên khớp push.json, bắt đầu prefix, thuộc project m28. Trả task. Không khớp thì SystemExit."""
    tid = st.get("task_id")
    if not isinstance(tid, int) or isinstance(tid, bool) or tid <= 0:
        raise SystemExit("push.json không có task_id hợp lệ: không biết task nào của tool.")
    name = st.get("task")
    if not isinstance(name, str) or not name.startswith(prefix):
        raise SystemExit(f"push.json ghi tên task {name!r} không bắt đầu bằng {prefix}: từ chối đụng vào task này.")
    task = client.tasks.retrieve(tid)
    if task.name != name:
        raise SystemExit(f"Task id {tid} trên CVAT tên {task.name!r}, không khớp push.json ({name!r}): có thể id đã thuộc task khác. "
                         "Từ chối, không làm gì trên task đó.")
    if not str(task.name).startswith(prefix):
        raise SystemExit(f"Task id {tid} có tên không bắt đầu bằng {prefix}: từ chối.")
    proj = find_project(client, project)
    if proj is None or task.project_id != proj.id:
        raise SystemExit(f"Task id {tid} không thuộc project {project} trên CVAT này: từ chối.")
    return task


# ---------- push ----------
def push(run_dir, task_name, nhan_imgs, tay_imgs, xml_path, project="m28", prefix="demo-",
         label_json=os.path.join("config", "face50_label.json"), *, resume=False, pipeline=None):
    """Xem docstring module. resume=True: chỉ làm phần còn lại trên đúng task_id trong push.json."""
    labels, point_names = check_inputs(task_name, prefix, label_json, xml_path, nhan_imgs, tay_imgs)
    env = io_.read_env()
    print(io_.status_line(env), flush=True)
    bad = io_.env_problem(env)
    if bad:
        raise SystemExit(bad)
    pipe = io_.load_pipeline(pipeline)
    with dang_chay.Guard(run_dir, "push", "chạy push lại"):
        mode, st, truoc = _gate(run_dir, task_name, resume)
        _say(1, f"ổn: task {task_name}, {len(nhan_imgs)} Nhận, {len(tay_imgs)} Gán tay" + (" (làm tiếp --resume)" if resume else ""))
        return _run(run_dir, task_name, nhan_imgs, tay_imgs, xml_path, project, prefix, labels, point_names, env, pipe, mode, st, truoc)


class _Doing:
    """Việc đang làm với CVAT (để thông báo lỗi nói đúng bước)."""
    what = "làm việc với CVAT"

    def __call__(self, what):
        self.what = what


def _note_loi(run_dir, msg):
    """SystemExit giữa chừng khi đã có push.json: ghi lý do vào file (nếu chưa có)."""
    if isinstance(msg, str) and os.path.exists(pj_path(run_dir)):
        try:
            cur = read_state(run_dir)
            if cur and cur.get("trang_thai") != S_XONG and cur.get("loi") != io_.scrub(msg)[:600]:
                cur["loi"] = io_.scrub(msg)[:600]
                write_state(run_dir, cur)
        except (OSError, SystemExit):
            pass


def _run(run_dir, task_name, nhan_imgs, tay_imgs, xml_path, project, prefix, labels, point_names, env, pipe, mode, st, truoc):
    t0 = time.time()
    doing = _Doing()
    doing("kết nối")
    try:
        client = io_.connect(env)
    except SystemExit:
        raise
    except Exception as e:
        _fail(run_dir, st, io_.translate_error(e, env, "kết nối") or f"Không kết nối được CVAT: {type(e).__name__}.")
    try:
        with client:
            return _steps(client, run_dir, task_name, nhan_imgs, tay_imgs, xml_path, project, prefix, labels, point_names, env, pipe,
                          mode, st, truoc, t0, doing)
    except SystemExit as e:
        _note_loi(run_dir, e.code)
        raise
    except Exception as e:                                        # lỗi mạng/HTTP/SDK: đổi sang thông báo tiếng Việt
        msg = io_.translate_error(e, env, doing.what)
        if msg is None:
            print(io_.scrub("".join(traceback.format_exception(type(e), e, e.__traceback__))), file=sys.stderr, flush=True)
            msg = f"Lỗi không lường trước khi {doing.what}: {type(e).__name__}: {io_.scrub(e)[:300]}"
        _fail(run_dir, read_state(run_dir) if os.path.exists(pj_path(run_dir)) else None, msg)


def _steps(client, run_dir, task_name, nhan_imgs, tay_imgs, xml_path, project, prefix, labels, point_names, env, pipe, mode, st, truoc,
           t0, doing):
    from cvat_sdk.core.proxies.tasks import ResourceType

    doing("kiểm bản server")
    ver = io_.check_version(client, pipe["cvat_version"])
    _say(2, f"{env['url']} | token: có | bản server {ver}" + (f" | tổ chức {env['org']}" if env["org"] else ""))
    doing("tìm project")
    groups, kinds = plan_jobs(nhan_imgs, tay_imgs, pipe["job_size"])
    if mode == "resume":
        task = _verify_identity(client, st, prefix, project)
        _say(3, f"project {project} (id {task.project_id}), làm tiếp task id {task.id}")
        _say(4, f"bỏ qua tạo task (đã có id {task.id})")
    else:
        project_id = get_project_id(client, project, labels, point_names)
        _say(3, f"project {project} (id {project_id}), label {LABEL} đủ {len(point_names)} điểm")
        same = [t for t in client.tasks.list() if t.name == task_name and t.project_id == project_id]
        if same:
            raise SystemExit(f"Trong project {project} đã có task tên {task_name} (id {same[0].id}): dừng để không có hai task cùng tên. "
                             "Đổi tên task (--task demo-…) hoặc xoá task cũ trong CVAT.")
        st = dict(tool="m28", phien_ban=1, task=task_name, project=project, cvat_url=io_.norm_url(env["url"]), trang_thai=S_DANG_TAO,
                  bat_dau=io_.now_iso(), so_anh=dict(nhan=len(nhan_imgs), gan_tay=len(tay_imgs)),
                  job_file_mapping=[len(g) for g in groups])
        if truoc:
            st["truoc_do"] = truoc
        write_state(run_dir, st)                                  # TRƯỚC khi gọi create_from_data: chết giữa chừng vẫn biết
        doing("tạo task và tải ảnh")
        _say(4, f"tạo task {task_name}: {len(nhan_imgs) + len(tay_imgs)} ảnh, {len(groups)} job dự kiến (mỗi job Nhận {pipe['job_size']} mặt)")
        task = client.tasks.create_from_data(
            spec={"name": task_name, "project_id": project_id},          # không truyền labels: task dùng label của project
            resources=list(nhan_imgs) + list(tay_imgs), resource_type=ResourceType.LOCAL,
            data_params={"image_quality": 95, "use_cache": True, "job_file_mapping": groups})
        jobs = _jobs_of(task, kinds)
        st.update(trang_thai=S_DA_TAO, task_id=task.id, jobs=jobs)
        got, want = [(j["kind"], j["n"]) for j in jobs], [(k, len(g)) for k, g in zip(kinds, groups)]
        if got != want:
            st["canh_bao"] = [f"Job trên CVAT {got} khác kế hoạch {want}: kiểm lại trong CVAT (task giữ nguyên, không xoá)."]
            print("Cảnh báo:", st["canh_bao"][0], flush=True)
        write_state(run_dir, st)
        _say(4, f"đã tạo task id {task.id}, {len(jobs)} job")
    nhan_names = [os.path.basename(p) for p in nhan_imgs]
    tay_names = [os.path.basename(p) for p in tay_imgs]
    doing("đọc danh sách frame")
    frames = _frame_names(task)
    if sorted(frames) != sorted(nhan_names + tay_names):
        _fail(run_dir, st, f"Ảnh trong task trên CVAT ({len(frames)}) không khớp ảnh đã tải ({len(nhan_names) + len(tay_names)}): kiểm task "
                           f"id {task.id} trong CVAT, rồi --cleanup và push lại.")
    # nhập nhãn đúng một lần, chỉ khi task còn 0 nhãn
    if st["trang_thai"] == S_DA_TAO:
        if nhan_imgs:
            doing("kiểm nhãn đã có trong task")
            n_ann = _n_annotations(task)
            if n_ann > 0:
                _say(5, f"task đã có {n_ann} nhãn: KHÔNG nhập lại (nhập sẽ ghi đè nhãn đã có)")
            else:
                xml_use = _xml_for_frames(xml_path, frames, run_dir)
                doing("nhập nhãn nháp")
                _say(5, f"nhập {len(nhan_imgs)} mặt bằng {io_.FORMAT_IMPORT}"
                        + ("" if xml_use == xml_path else " (id ảnh đã ghép theo frame thật)"))
                task.import_annotations(io_.FORMAT_IMPORT, xml_use)
        else:
            _say(5, "không có mặt Nhận, không nhập nhãn")
        st["trang_thai"] = S_DA_NHAP
        write_state(run_dir, st)
    else:
        _say(5, "đã nhập nhãn ở lần trước, bỏ qua")
    doing("xuất nhãn để kiểm")
    check_path = os.path.join(run_dir, "check.zip")
    _say(6, f"xuất {io_.FORMAT_EXPORT} (chỉ nhãn) để kiểm")
    task.export_dataset(io_.FORMAT_EXPORT, check_path, include_images=False)
    res = io_.check_faces(io_.parse_annotations(io_.read_zip_annotations(check_path)), nhan_names, tay_names, point_names)
    st["check"] = res
    if not res["ok"]:
        _fail(run_dir, st, f"Kiểm sau khi nhập KHÔNG đạt: {res['n_day_du']}/{res['n_nhan']} mặt Nhận có đủ {len(point_names)} điểm kèm low_conf"
                           f" (thiếu: {res['thieu'][:3] + res['thieu_anh'][:3]}; Gán tay lỡ có nhãn: {res['gan_tay_co_nhan'][:3]}). "
                           f"Task id {task.id} được giữ nguyên để bạn xem; chạy --resume để kiểm lại hoặc --cleanup để xoá.")
    url = io_.task_url(env["url"], task.id)
    st.update(trang_thai=S_XONG, task_url=url, thoi_gian_giay=round(time.time() - t0, 1))
    st.pop("loi", None)
    write_state(run_dir, st)
    n_nhan_jobs = sum(1 for j in st["jobs"] if j["kind"] == "nhan")
    n_tay_jobs = sum(1 for j in st["jobs"] if j["kind"] == "gan_tay")
    print(f"push xong: task {task_name} id {task.id}, {len(st['jobs'])} job ({n_nhan_jobs} Nhận, {n_tay_jobs} Gán tay), {url}", flush=True)
    return check_path


# ---------- xoá task ----------
def delete_warning(task_name, task_id, url):
    """Mô tả hậu quả của việc xoá task (dùng ở cmd và ở hộp xác nhận trên trang)."""
    return [f"Xoá task {task_name} (id {task_id}) trên CVAT {url} KHÔNG HOÀN TÁC ĐƯỢC.",
            "Mất cả nhãn đã sửa trong CVAT, các job và ảnh của task đó.",
            "Nếu cần giữ nhãn đã sửa: chạy collect (hoặc export) trước, rồi mới xoá.",
            "Chỉ xoá đúng task này; không đụng project hay task nào khác. Lượt này sau đó đẩy lại lên CVAT được."]


def _log(run_dir, step, status, secs, detail=""):
    try:
        with open(os.path.join(run_dir, "log.txt"), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{step}\t{status}\t{secs:.1f}s" + (f"\t{detail}" if detail else "") + "\n")
    except OSError:
        pass


def delete_task(run_dir, *, confirm_name=None, prefix="demo-", project="m28", pipeline=None):
    """Xoá ĐÚNG task ghi trong runs/<lượt>/push.json trên CVAT, rồi đánh dấu push.json trang_thai "task_deleted" để đẩy lại được.

    Từ chối (SystemExit, không gọi lệnh xoá nào) khi: tên task không bắt đầu `demo-`/prefix; không có id; confirm_name không đúng tên
    task trong push.json; CVAT_URL khác lúc push; lượt đang push/prepare; task lấy lại theo id có tên khác push.json hoặc không thuộc
    project m28. Task đã mất sẵn trên CVAT (404) thì chỉ đánh dấu, không gọi xoá."""
    t0 = time.time()
    check_prefix(prefix)
    st = read_state(run_dir)
    run = _run_name(run_dir)
    if st is None:
        raise SystemExit(f"Lượt {run} chưa có push.json: không có task nào của tool để xoá.")
    state = st.get("trang_thai")
    name, tid = st.get("task"), st.get("task_id")
    if state == S_DELETED:
        print(f"Task {name} đã được đánh dấu xoá từ trước: không có gì làm thêm.")
        return False
    if not isinstance(name, str) or not name.startswith(prefix):
        raise SystemExit(f"push.json ghi tên task {name!r} không bắt đầu bằng {prefix}: từ chối xoá.")
    if state == S_DANG_TAO:
        return _cleanup_dang_tao(run_dir, st, name, project, prefix, pipeline)
    if state not in (S_DA_TAO, S_DA_NHAP, S_XONG):
        raise SystemExit(f"push.json có trạng thái lạ {state!r}: mở file kiểm tay, không xoá gì.")
    if not isinstance(tid, int) or isinstance(tid, bool) or tid <= 0:
        raise SystemExit("push.json không có task_id hợp lệ: không biết xoá task nào.")
    if confirm_name is None or confirm_name != name:
        raise SystemExit(f"Chưa xác nhận: cần gõ lại ĐÚNG tên task ({name}) bằng --confirm-name (phân biệt hoa thường). "
                         + " ".join(delete_warning(name, tid, st.get("cvat_url", ""))))
    env = io_.read_env()
    print(io_.status_line(env), flush=True)
    bad = io_.env_problem(env)
    if bad:
        raise SystemExit(bad)
    if io_.norm_url(env["url"]) != io_.norm_url(st.get("cvat_url")):
        raise SystemExit(f"push.json ghi task này ở {st.get('cvat_url')} nhưng CVAT_URL đang là {io_.norm_url(env['url'])}: id task chỉ có "
                         "nghĩa trên đúng server đã push. Đặt lại CVAT_URL cho đúng rồi chạy lại.")
    pipe = io_.load_pipeline(pipeline)
    with dang_chay.Guard(run_dir, "xoa_task", "xoá task"):
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
                io_.check_version(client, pipe["cvat_version"])
                doing = "lấy lại task theo id"
                gone = False
                try:
                    task = _verify_identity(client, st, prefix, project or pipe["project"])
                except Exception as e:
                    if getattr(e, "status", None) == 404:
                        gone = True
                    else:
                        raise
                if gone:
                    print(f"Task id {tid} không còn trên CVAT (đã xoá tay?): chỉ đánh dấu push.json, không gọi lệnh xoá.", flush=True)
                else:
                    print(f"Đã kiểm: task id {tid} tên {name} thuộc project {project or pipe['project']}. Xoá…", flush=True)
                    doing = "xoá task"
                    task.remove()
        except SystemExit:
            raise
        except Exception as e:
            msg = io_.translate_error(e, env, doing)
            if msg is None:
                print(io_.scrub("".join(traceback.format_exception(type(e), e, e.__traceback__))), file=sys.stderr, flush=True)
                msg = f"Lỗi không lường trước khi {doing}: {type(e).__name__}: {io_.scrub(e)[:300]}"
            raise SystemExit(io_.scrub(msg))
        when = io_.now_iso()
        st.update(trang_thai=S_DELETED, task_deleted_at=when)
        st.pop("loi", None)
        if gone:
            st["ghi_chu_xoa"] = "task không còn trên CVAT lúc xoá"
        write_state(run_dir, st)
        done = os.path.join(run_dir, "push", "done.txt")
        try:
            if os.path.exists(done):
                os.remove(done)                                   # để m28.py push chạy lại được
        except OSError:
            pass
        _log(run_dir, "xoa_task", "xong", time.time() - t0, f"{name} id {tid}")
        print(f"Đã xoá task {name} (id {tid}) trên CVAT; push.json ghi {S_DELETED}. Lượt {run} đẩy lại được.", flush=True)
        return True


def _cleanup_dang_tao(run_dir, st, name, project, prefix, pipeline):
    """push.json dang_tao (chết giữa lúc tạo, không có id): CHỈ liệt kê task cùng tên trong project, không xoá task nào, rồi xoá push.json."""
    run = _run_name(run_dir)
    env = io_.read_env()
    print(io_.status_line(env), flush=True)
    if io_.env_problem(env) is None:
        pipe = io_.load_pipeline(pipeline)
        try:
            client = io_.connect(env)
            with client:
                proj = find_project(client, project or pipe["project"])
                same = [t for t in client.tasks.list() if t.name == name and (proj is None or t.project_id == proj.id)]
            if same:
                print(f"Có {len(same)} task tên {name} trên CVAT (tool KHÔNG tự xoá, hãy kiểm và tự xoá trong giao diện CVAT nếu thừa):")
                for t in same:
                    print(f"  id {t.id}, tạo lúc {getattr(t, 'created_date', '?')}")
            else:
                print(f"Không thấy task tên {name} trong project trên CVAT.")
        except SystemExit:
            raise
        except Exception as e:
            print(io_.translate_error(e, env, "liệt kê task") or f"Không liệt kê được task ({type(e).__name__}).")
    else:
        print("Chưa có CVAT_URL/CVAT_ACCESS_TOKEN nên không liệt kê được task cùng tên trên CVAT (tự kiểm trong giao diện).")
    try:
        os.remove(pj_path(run_dir))
    except OSError as e:
        raise SystemExit(f"Không xoá được push.json ({e}).")
    _log(run_dir, "xoa_task", "dang_tao", 0.0, name)
    print(f"Đã xoá push.json của lượt {run} (không xoá task nào trên CVAT). Chạy lại push khi sẵn sàng.")
    return True


def cleanup(run_dir, prefix="demo-", *, confirm_name=None, project="m28", pipeline=None):
    """Cho `m28.py push --cleanup`: như delete_task. Gõ ở cmd thật (có bàn phím) mà thiếu --confirm-name thì hỏi gõ lại tên."""
    st = read_state(run_dir)
    if (confirm_name is None and st and st.get("trang_thai") in (S_DA_TAO, S_DA_NHAP, S_XONG)
            and sys.stdin is not None and sys.stdin.isatty()):
        print("\n".join(delete_warning(st.get("task"), st.get("task_id"), st.get("cvat_url", ""))))
        confirm_name = input("Gõ lại ĐÚNG tên task để xoá (Enter để huỷ): ").strip() or None
    return delete_task(run_dir, confirm_name=confirm_name, prefix=prefix, project=project, pipeline=pipeline)
