"""Hàm dùng chung của push.py và collect.py: biến môi trường CVAT, lọc token, kết nối, dịch lỗi, đọc annotations.xml.

Chỉ thư viện chuẩn; `cvat_sdk` nạp LƯỜI trong connect() nên import module này (và test) không cần cài SDK. Không numpy/gradio/torch.
Token chỉ đọc từ CVAT_ACCESS_TOKEN, không bao giờ in/ghi/log: mọi chuỗi đi ra ngoài (thông báo lỗi, push.json, log) qua scrub().
"""
import datetime
import io
import json
import os
import re
import socket
import zipfile
import xml.etree.ElementTree as ET

ENV_URL, ENV_TOKEN, ENV_ORG = "CVAT_URL", "CVAT_ACCESS_TOKEN", "CVAT_ORG"
DEFAULT_PIPELINE = {"project": "m28", "prefix": "demo-", "cvat_version": "2.77.0", "job_size": 8}
SAFE_PREFIX = "demo-"                      # prefix duy nhất được phép; task m28-… không bao giờ bị tạo/đụng/xoá
FORMAT_IMPORT = "CVAT 1.1"
FORMAT_EXPORT = "CVAT for images 1.1"
VN_TZ = datetime.timezone(datetime.timedelta(hours=7))
MAX_XML = 200 * 1024 * 1024
NO_CVAT_MSG = ("Đặt CVAT_URL (ghi rõ http://, ví dụ set CVAT_URL=http://localhost:8080) và CVAT_ACCESS_TOKEN "
               "(set CVAT_ACCESS_TOKEN=<token của bạn>) trong CÙNG cửa sổ cmd rồi chạy lại. Không dán token vào file hay chat.")


# ---------- môi trường, token ----------
def read_env(environ=None):
    e = os.environ if environ is None else environ
    return dict(url=(e.get(ENV_URL) or "").strip(), token=(e.get(ENV_TOKEN) or "").strip(), org=(e.get(ENV_ORG) or "").strip())


def env_problem(env):
    """Lý do tiếng Việt nếu thiếu/sai biến môi trường CVAT, không thì None. Không bao giờ chứa giá trị token."""
    url = env["url"]
    if not url or not env["token"]:
        miss = [n for n, v in ((ENV_URL, url), (ENV_TOKEN, env["token"])) if not v]
        return f"Thiếu {' và '.join(miss)}. " + NO_CVAT_MSG
    if not url.startswith(("http://", "https://")):
        return f"CVAT_URL phải bắt đầu bằng http:// hoặc https:// (đang là {url!r}); thiếu thì cvat-sdk tự hiểu là https. " + NO_CVAT_MSG
    netloc = url.split("://", 1)[1].split("/", 1)[0]
    if "@" in netloc:
        return "CVAT_URL không được chứa tên đăng nhập hoặc mật khẩu (dạng http://user:pass@host). Dùng token ở CVAT_ACCESS_TOKEN."
    return None


def norm_url(url):
    return (url or "").strip().rstrip("/")


def task_url(url, task_id):
    return f"{norm_url(url)}/tasks/{task_id}"


def status_line(env):
    return f"CVAT: {env['url'] or '(thiếu CVAT_URL)'} | token: {'có' if env['token'] else 'thiếu'}"


def scrub(text, token=None):
    """Bỏ token (và dạng 'Authorization: Bearer/Token …') khỏi chuỗi trước khi in/ghi."""
    s = str(text)
    token = (token if token is not None else os.environ.get(ENV_TOKEN, "")) or ""
    if len(token) >= 4:
        s = s.replace(token, "***")
    return re.sub(r"(?i)\b(authorization|bearer|token)(\s*[:=]\s*|\s+)(?!\*\*\*)([A-Za-z0-9._~+/=-]{12,})", r"\1\2***", s)


# ---------- pipeline.json, ghi file ----------
def load_pipeline(path=None):
    p = dict(DEFAULT_PIPELINE)
    path = path or os.path.join("config", "pipeline.json")
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError) as e:
            raise SystemExit(f"Không đọc được {path} ({e}): sửa lại cho đúng JSON hoặc xoá để dùng mặc định.")
        if not isinstance(d, dict):
            raise SystemExit(f"{path} phải là một đối tượng JSON {{...}}.")
        p.update({k: v for k, v in d.items() if k in p})
    if not isinstance(p["job_size"], int) or isinstance(p["job_size"], bool) or not 1 <= p["job_size"] <= 64:
        raise SystemExit(f"job_size trong {path} phải là số nguyên từ 1 đến 64.")
    for k in ("project", "prefix", "cvat_version"):
        if not isinstance(p[k], str) or not p[k].strip():
            raise SystemExit(f"{k} trong {path} phải là chuỗi không rỗng.")
    return p


def atomic_write_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + f".tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


# ---------- kết nối, dịch lỗi ----------
def connect(env):
    """Client đã đăng nhập bằng Personal Access Token (make_client(url, access_token=...), có từ cvat-sdk 2.77). Gọi sau env_problem()."""
    try:
        from cvat_sdk import make_client
    except ImportError:
        raise SystemExit("Chưa cài cvat-sdk: gõ python -m pip install cvat-sdk==2.77.0 (cùng bản với server CVAT).")
    client = make_client(env["url"], access_token=env["token"])
    if env["org"]:
        client.organization_slug = env["org"]
    return client


def server_version(client):
    return str(client.get_server_version())


def _mm(v):
    m = re.match(r"\s*(?:\d+!)?(\d+)\.(\d+)", str(v))
    return (int(m.group(1)), int(m.group(2))) if m else None


def check_version(client, want):
    """Dừng nếu bản server khác bản trong pipeline.json (khoá cvat_version). So (major, minor); trả chuỗi bản server."""
    got = server_version(client)
    if _mm(got) != _mm(want):
        raise SystemExit(f"Bản server CVAT là {got} nhưng config\\pipeline.json ghi cvat_version {want}. cvat-sdk phải cùng bản với "
                         f"server: nếu server đúng là {got}, cài python -m pip install cvat-sdk=={got} rồi sửa cvat_version trong "
                         "config\\pipeline.json (ở công ty làm đúng như vậy); nếu không thì chạy lại đúng bản CVAT của nhóm.")
    return got


def _names(exc):
    return [c.__name__ for c in type(exc).__mro__]


def body_snippet(exc, token=None, n=300):
    body = getattr(exc, "body", None)
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    if not body:
        body = getattr(exc, "reason", "") or ""
    return scrub(str(body), token).replace("\n", " ")[:n]


def translate_error(exc, env, doing):
    """Đổi exception của SDK/urllib3/OSError thành thông báo tiếng Việt (nguyên nhân + cách sửa), đã lọc token.
    Trả chuỗi, hoặc None nếu không nhận ra (người gọi tự xử lý)."""
    token = env.get("token")
    names = _names(exc)
    status = getattr(exc, "status", None)
    url = env.get("url") or "CVAT"
    if isinstance(status, int):
        if status in (401, 403):
            return (f"CVAT từ chối ({status}) khi {doing}: token sai, đã bị thu hồi hoặc hết hạn, hoặc tài khoản không đủ quyền. "
                    "Tạo lại token trong CVAT (Settings > Security), set CVAT_ACCESS_TOKEN=<token mới> trong cmd rồi chạy lại.")
        if status == 404:
            return (f"CVAT báo không tìm thấy (404) khi {doing}: project/task không còn trên server này hoặc CVAT_URL/CVAT_ORG sai. "
                    f"Kiểm {url} và (nếu dùng) CVAT_ORG.")
        return f"CVAT báo lỗi {status} khi {doing}: {body_snippet(exc, token)}"
    if any(n in names for n in ("IncompatibleVersionException",)):
        return (f"cvat-sdk không cùng bản với server CVAT ({scrub(exc, token)[:200]}). Cài python -m pip install cvat-sdk==<bản của server> "
                "và sửa cvat_version trong config\\pipeline.json.")
    if isinstance(exc, (ConnectionError, TimeoutError, socket.gaierror, socket.timeout)) or any(n in names for n in (
            "MaxRetryError", "NewConnectionError", "ProtocolError", "ConnectionError", "ReadTimeoutError", "TimeoutError", "SSLError")):
        return (f"Không kết nối được tới {url} khi {doing}. Nếu CVAT chạy trên máy này: mở Ubuntu (WSL), vào thư mục cvat, "
                "gõ docker compose up -d, chờ 1-2 phút rồi thử lại; kiểm CVAT_URL đúng địa chỉ và có http://.")
    return None


# ---------- đọc annotations.xml (theo TÊN ảnh và TÊN điểm, không theo id) ----------
def parse_annotations(xml_bytes):
    """{tên ảnh: dict(width, height, skeletons=[{label, points={tên điểm: dict(x, y, occluded, outside, low_conf)}}], n_shapes)}.
    low_conf là 'true'/'false' hoặc None nếu điểm không có thuộc tính này."""
    if len(xml_bytes) > MAX_XML:
        raise SystemExit("File annotations.xml quá lớn (hơn 200 MB): không đọc.")
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise SystemExit(f"annotations.xml không phải XML hợp lệ ({e}).")
    out = {}
    for im in root.iter("image"):
        name = im.get("name") or ""
        d = dict(width=im.get("width"), height=im.get("height"), skeletons=[], n_shapes=0)
        for sk in im.findall("skeleton"):
            pts = {}
            for p in sk.findall("points"):
                xy = (p.get("points") or "").split(",")
                try:
                    x, y = float(xy[0]), float(xy[1])
                except (ValueError, IndexError):
                    x = y = None
                lc = None
                for a in p.findall("attribute"):
                    if a.get("name") == "low_conf":
                        lc = (a.text or "").strip().lower()
                pts[p.get("label") or ""] = dict(x=x, y=y, occluded=p.get("occluded"), outside=p.get("outside"), low_conf=lc)
            d["skeletons"].append(dict(label=sk.get("label"), points=pts))
        d["n_shapes"] = sum(1 for tag in ("box", "polygon", "polyline", "points", "mask", "ellipse", "cuboid", "tag")
                            for _ in im.findall(tag)) + len(d["skeletons"])
        out[name] = d
    return out


def read_zip_annotations(zip_path):
    """Đọc annotations.xml trong file zip xuất từ CVAT (không giải nén ra đĩa)."""
    try:
        with zipfile.ZipFile(zip_path) as z:
            try:
                info = z.getinfo("annotations.xml")
            except KeyError:
                raise SystemExit(f"{zip_path} không có annotations.xml (đã xuất đúng định dạng 'CVAT for images 1.1' chưa?).")
            if info.file_size > MAX_XML:
                raise SystemExit("annotations.xml trong zip quá lớn (hơn 200 MB): không đọc.")
            return z.read(info)
    except zipfile.BadZipFile:
        raise SystemExit(f"{zip_path} không phải file zip hợp lệ (tải về dở?).")


def check_faces(ann, want_nhan, want_tay, point_names):
    """So kết quả xuất với kế hoạch. Trả dict(ok, n_nhan, n_day_du, thieu=[...], gan_tay_co_nhan=[...], thieu_anh=[...])."""
    need = set(point_names)
    thieu, full, thieu_anh = [], 0, []
    for name in want_nhan:
        im = ann.get(name)
        if im is None:
            thieu_anh.append(name)
            continue
        sk = [s for s in im["skeletons"] if s["label"] == "face50"]
        ok = False
        if len(sk) == 1 and set(sk[0]["points"]) == need and len(sk[0]["points"]) == len(point_names):
            ok = all(p["low_conf"] in ("true", "false") for p in sk[0]["points"].values())
        if ok:
            full += 1
        else:
            thieu.append(name)
    tay_co = [n for n in want_tay if n in ann and ann[n]["n_shapes"] > 0]
    thieu_anh += [n for n in want_tay if n not in ann]
    good = not thieu and not thieu_anh and not tay_co
    return dict(ok=good, n_nhan=len(want_nhan), n_day_du=full, thieu=thieu[:20], thieu_anh=thieu_anh[:20], gan_tay_co_nhan=tay_co[:20])


def safe_file_part(text):
    """Phần tên file an toàn (task, người rà): chữ, số, _ - . ; không chứa / \\ hoặc .. ; SystemExit nếu không hợp lệ."""
    t = str(text)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", t) or ".." in t:
        raise SystemExit(f"Tên {t!r} không dùng làm tên file được (chỉ chữ không dấu, số, _ - . , tối đa 128 ký tự, không có '..').")
    return t


def inside(path, base):
    try:
        p, b = os.path.realpath(path), os.path.realpath(base)
        return os.path.commonpath([p, b]) == b
    except ValueError:
        return False


def zip_bytes_with(name, data):
    """Zip trong bộ nhớ chỉ có một file (dùng cho bản CVAT giả và test)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(name, data)
    return buf.getvalue()
