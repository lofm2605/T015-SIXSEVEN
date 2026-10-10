"""Ca khó và họp team của trang rà soát M28: logic thuần, HTML thuần, và ba hàm dựng giao diện nhận `gr` làm tham số.

Luồng:
  1. Tab "Rà soát": phím K (nút "Ca khó") ghi mặt đang xem là ca khó vào runs/<lượt>/ca_kho.csv
     (không đụng triage_<người>.csv, done.txt, hàng đợi hay hoàn tác).
  2. Tab "Ca khó": thành viên xem/sửa/xoá ca của mình rồi "Export meeting pack" ra outputs/ca_kho/ca_kho_<người>_<ddmm>.zip.
  3. Tab "Họp team": người tổ chức nhập các gói zip, họp trên lưới ảnh, đặt trạng thái / quyết định, rồi xuất biên bản
     markdown điền sẵn theo mẫu problem-backlog.md (P-NNN) và so-quyet-dinh.md (QĐ-NNN) để TỰ dán vào repo.
     Code này chỉ ĐỌC hai file đó (để đánh số tiếp), không bao giờ ghi vào chúng.

Quy ước (giống nap_anh.py):
  * Đầu module chỉ thư viện chuẩn (và nap_anh, cũng chỉ thư viện chuẩn). PIL nạp lười trong hàm. Không import gradio ở đầu module,
    không import review_app (tránh vòng lặp). Không gọi mạng. Không import torch.
  * Chỉ ghi dưới runs/<lượt>/ca_kho.csv và outputs/ca_kho/ (mọi đường dẫn đích kiểm bằng realpath + commonpath).
  * Gói họp chứa ảnh mặt người thật: chỉ gửi trong đội, không đưa vào git hay chat AI. Gói nhận về KHÔNG BAO GIỜ được giải nén ra đĩa
    (không extractall): chỉ đọc từng mục có tên hợp lệ vào bộ nhớ, giới hạn byte thật sự đọc được, ảnh mã hoá lại thành JPEG mới.
"""
import csv
import datetime
import hashlib
import html
import io
import json
import os
import re
import sys
import threading
import unicodedata
import urllib.parse
import zipfile
import zlib

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)
import nap_anh  # noqa: E402  (RUN_RE, RunError, _inside; chỉ thư viện chuẩn)

RunError = nap_anh.RunError
_inside = nap_anh._inside
RUN_RE = nap_anh.RUN_RE


class GoiLoi(Exception):
    """Gói họp không hợp lệ. Thông điệp tiếng Việt nói rõ vì sao."""


# ---------- hằng số ----------
LOAI = [  # (mã, nhãn tiếng Việt, nhóm)  nhóm: loi = lỗi đặt điểm (mã xem chéo), gl = guideline, cc = công cụ
    ("SWAP", "Đổi chỗ hai điểm", "loi"), ("MIRROR", "Lật phải trái", "loi"), ("COLLAPSE", "Dồn cục", "loi"),
    ("MISPLACED", "Đặt sai chỗ", "loi"), ("OCC_FLAG", "Sai cờ che", "loi"),
    ("RULE", "Ca chưa có quy tắc", "gl"), ("GL_CHUA_NOI", "Guideline chưa nói tới", "gl"),
    ("GL_MO_HO", "Guideline mơ hồ", "gl"), ("GL_MAU_THUAN", "Guideline mâu thuẫn", "gl"),
    ("CONG_CU", "Pain point công cụ", "cc"), ("KHAC", "Khác", "gl")]
LOAI_CODES = [c for c, _t, _g in LOAI]
LOAI_VI = {c: t for c, t, _g in LOAI}
LOAI_NHOM = {c: g for c, _t, g in LOAI}
LOAI_ORDER = {c: i for i, c in enumerate(LOAI_CODES)}
BACKLOG_LOAI = ["Guideline chưa nói tới", "Guideline mơ hồ", "Guideline mâu thuẫn", "Pain point công cụ"]    # đúng chữ trong problem-backlog.md
BACKLOG_DEFAULT = {"RULE": "Guideline chưa nói tới", "GL_CHUA_NOI": "Guideline chưa nói tới", "KHAC": "Guideline chưa nói tới",
                   "GL_MO_HO": "Guideline mơ hồ", "GL_MAU_THUAN": "Guideline mâu thuẫn", "CONG_CU": "Pain point công cụ"}
TRANG_THAI = [("mo", "Mở", "🔴 Mở"), ("dang_ban", "Đang bàn", "🗣️ Đang bàn"), ("da_chot", "Đã chốt", "✅ Đã chốt")]
TT_CODES = [c for c, _t, _i in TRANG_THAI]
TT_VI = {c: t for c, t, _i in TRANG_THAI}
TT_ICON = {c: i for c, _t, i in TRANG_THAI}
TT_COLOR = {"mo": "#dc2626", "dang_ban": "#d97706", "da_chot": "#16a34a"}       # như STATUS_COLOR của review_app: đỏ / vàng / xanh
DECISION_VI = {"nhan": "Nhận", "gan_tay": "Gán tay", "bo": "Bỏ ảnh", "": ""}
NGUON_VI = {"yawdd": "YawDD", "drivface": "DrivFace", "yawdd+drivface": "YawDD + DrivFace", "khong_ro": "không rõ nguồn"}
NGUON_BO_DU_LIEU = ("yawdd", "drivface", "yawdd+drivface")   # nguồn là một bộ dữ liệu đã biết (ảnh chồng được phép kèm); còn lại là khong_ro
NGUON_IN_CABIN = ("yawdd", "drivface")                                 # giá trị cột `source` của manifest in-cabin (QĐ-001)

MAX_GOI = 20 * 1024 * 1024         # tổng dung lượng một gói (dưới giới hạn upload 25 MB của trang)
MAX_CA = 500                       # số ca tối đa mỗi gói
MAX_MANIFEST = 64 * 1024
MAX_CSV = 2 * 1024 * 1024
MAX_IMG_BYTES = 1024 * 1024        # mỗi ảnh trong gói
MAX_TONG = 60 * 1024 * 1024        # tổng byte giải nén
MAX_IMG_PIXELS = 4_000_000
IMG_SIDES = ((480, 72), (360, 60))  # (cạnh dài, chất lượng JPEG): thử lại cỡ sau nếu gói quá lớn
NOTE_MAX = 500
DIEM_MAX = 200
QD_MAX = 500
LOAI_FILE = "m28-ca-kho"
PHIEN_BAN = 1
CSV_COLS = ["luot", "anh", "nguoi", "loai", "diem", "ghi_chu", "tao_luc", "sua_luc", "quyet_dinh_ra"]
PKG_COLS = CSV_COLS + ["thumb"]
TONG_HOP_COLS = ["ma_p", "ma_qd", "ngay", "nguoi", "luot", "anh", "diem", "loai", "ghi_chu", "trang_thai", "quyet_dinh", "phu_trach",
                 "loai_backlog", "muc_guideline"]
ANH_RE = re.compile(r"[A-Za-z0-9_.-]{1,100}\.png")
NGUOI_RE = re.compile(r"[A-Za-z0-9_-]{1,32}")
POINT_RE = re.compile(r"[A-Za-z0-9_.-]{1,40}")
ENTRY_RE = re.compile(r"(manifest\.json|ca_kho\.csv|anh/[A-Za-z0-9_-]{1,100}\.jpg)")
HOP_RE = re.compile(r"hop_\d{4}(?:_\d{1,3})?")
NEW_SESSION = "__moi__"
DECISIONS_OK = ("nhan", "gan_tay", "bo")
SERVE_REL = ("outputs", "ca_kho")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_LOCK = threading.RLock()          # mọi lần đọc-sửa-ghi ca_kho.csv
_PKG_LOCK = threading.Lock()       # dựng gói zip


# ---------- tiện ích ----------
def now_local():
    return datetime.datetime.now().astimezone()


def iso(dt):
    return dt.isoformat(timespec="seconds")


def ddmm(dt):
    return dt.strftime("%d%m")


def fmt_date(value):
    """dd/mm/yyyy từ ISO (datetime hoặc chuỗi); không đọc được thì chuỗi rỗng."""
    dt = parse_time(value) if isinstance(value, str) else value
    return dt.strftime("%d/%m/%Y") if dt else ""


def parse_time(s):
    try:
        dt = datetime.datetime.fromisoformat(str(s).strip())
    except (ValueError, TypeError):
        return None
    return dt if dt.tzinfo else dt.astimezone()


def _ts(s):
    dt = parse_time(s)
    return dt.timestamp() if dt else 0.0


def check_name(nguoi):
    """Cùng quy tắc check_reviewer của review_app (chép sang đây để không import review_app)."""
    if not isinstance(nguoi, str) or not NGUOI_RE.fullmatch(nguoi):
        raise RunError(f"Tên người {nguoi!r} không hợp lệ: chỉ dùng chữ không dấu, số, gạch dưới, gạch ngang (tối đa 32 ký tự), ví dụ P2.")
    return nguoi


def clean_text(s, maxlen, what="Văn bản"):
    s = unicodedata.normalize("NFC", "" if s is None else str(s))
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = _CTRL.sub(" ", s).strip()
    if len(s) > maxlen:
        raise RunError(f"{what} dài {len(s)} ký tự, tối đa {maxlen}.")
    return s


def clean_diem(diem, known=None):
    """Danh sách điểm (list hoặc chuỗi cách nhau bằng ; hoặc ,) -> 'mattrai_1;mattrai_2'. Có `known` (tên trong config) thì chỉ nhận tên đó."""
    if isinstance(diem, str):
        parts = re.split(r"[;,]", diem)
    else:
        parts = list(diem or [])
    out = []
    for p in parts:
        p = str(p).strip()
        if not p:
            continue
        if not POINT_RE.fullmatch(p):
            raise RunError(f"Tên điểm {p!r} không hợp lệ: chỉ chữ không dấu, số, gạch dưới, gạch ngang, chấm.")
        if known and p not in known:
            raise RunError(f"Điểm {p!r} không có trong config/m28_config.json.")
        if p not in out:
            out.append(p)
    s = ";".join(out)
    if len(s) > DIEM_MAX:
        raise RunError(f"Danh sách điểm dài {len(s)} ký tự, tối đa {DIEM_MAX}: chọn ít điểm hơn.")
    return s


def _stem(anh):
    return anh[:-4] if anh.lower().endswith(".png") else anh


def _delim(text):
    first = text.splitlines()[0] if text.strip() else ""
    return ";" if first.count(";") > first.count(",") else ","


def serve_dir(project_root):
    """<project>/outputs/ca_kho (tạo nếu chưa có; lỗi tạo thì vẫn trả đường dẫn)."""
    p = os.path.join(project_root, *SERVE_REL)
    try:
        os.makedirs(p, exist_ok=True)
    except OSError:
        pass
    return p


def load_point_names(project_root):
    """Tên 50 điểm từ config/m28_config.json (points[].name); thiếu file hoặc hỏng thì []."""
    try:
        with open(os.path.join(project_root, "config", "m28_config.json"), encoding="utf-8") as f:
            return [str(p["name"]) for p in json.load(f)["points"]]
    except (OSError, ValueError, KeyError, TypeError):
        return []


def _atomic_write(path, data, mode="wb", encoding=None):
    tmp = path + f".tmp{os.getpid()}"
    try:
        with open(tmp, mode, encoding=encoding, newline="" if "b" not in mode else None) as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def csv_text(cols, rows, safe=False):
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\r\n")
    w.writerow(cols)
    for r in rows:
        w.writerow([_formula_safe(r.get(c, "")) if safe else ("" if r.get(c) is None else r.get(c, "")) for c in cols])
    return out.getvalue()


def _formula_safe(v):
    """Ô bắt đầu bằng = + - @ (hoặc tab/CR) thì thêm ' phía trước: Excel không coi là công thức."""
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


# ---------- ghi nhận ca khó của một lượt: runs/<lượt>/ca_kho.csv ----------
def ca_path(run_dir):
    return os.path.join(run_dir, "ca_kho.csv")


def run_label(run_dir):
    return os.path.basename(os.path.normpath(run_dir))


def check_run_dir(run_dir, runs_root=None):
    name = run_label(run_dir)
    if not RUN_RE.fullmatch(name):
        raise RunError(f"Tên lượt {name!r} không hợp lệ cho ca khó.")
    if runs_root is not None and not _inside(run_dir, runs_root):
        raise RunError("Lượt nằm ngoài thư mục runs.")
    return name


def _norm_row(r, luot):
    row = {c: ("" if r.get(c) is None else str(r.get(c))) for c in CSV_COLS}
    row["luot"] = luot
    return row


def read_marks(run_dir):
    """Các ca khó đã ghi của lượt (list dict theo CSV_COLS), thứ tự trong file. Không có file thì []. `luot` luôn là tên thư mục."""
    p = ca_path(run_dir)
    if not os.path.exists(p):
        return []
    luot = run_label(run_dir)
    try:
        with open(p, encoding="utf-8-sig", newline="") as f:
            text = f.read()
    except UnicodeDecodeError:
        raise RunError(f"{os.path.join(luot, 'ca_kho.csv')} không phải UTF-8: mở bằng Excel rồi lưu lại dạng 'CSV UTF-8'.")
    except OSError as e:
        raise RunError(f"Không đọc được ca_kho.csv của lượt {luot} ({type(e).__name__}). Đóng Excel nếu đang mở file này.")
    out, seen = [], {}
    try:
        rows = list(csv.DictReader(io.StringIO(text), delimiter=_delim(text)))
    except csv.Error:
        raise RunError(f"ca_kho.csv của lượt {luot} sai định dạng CSV.")
    for r in rows:
        r = {(k or "").strip().lower(): v for k, v in r.items() if k is not None}
        row = _norm_row(r, luot)
        if not row["nguoi"].strip() or not row["anh"].strip():
            continue
        k = (row["nguoi"], row["anh"])
        if k in seen:
            out[seen[k]] = row                       # trùng khoá: dòng sau đè
        else:
            seen[k] = len(out)
            out.append(row)
    return out


def _write_marks(run_dir, rows):
    p = ca_path(run_dir)
    if os.path.lexists(p) and not _inside(p, run_dir):
        raise RunError("ca_kho.csv là liên kết trỏ ra ngoài thư mục lượt: không ghi.")
    try:
        _atomic_write(p, csv_text(CSV_COLS, rows), "w", "utf-8-sig")
    except OSError:
        raise RunError(f"Không ghi được ca_kho.csv của lượt {run_label(run_dir)}. Đóng Excel nếu đang mở file này rồi bấm lại.")


def get_mark(run_dir, nguoi, anh):
    for r in read_marks(run_dir):
        if r["nguoi"] == nguoi and r["anh"] == anh:
            return r
    return None


def upsert_mark(run_dir, nguoi, anh, loai, diem="", ghi_chu="", quyet_dinh_ra="", now=None, known_points=None, runs_root=None):
    """Thêm hoặc sửa ca khó (khoá (nguoi, anh) trong file). Trả (dòng, đã_tạo_mới). Lỗi ghi -> RunError, không đổi gì."""
    check_run_dir(run_dir, runs_root)
    check_name(nguoi)
    if not isinstance(anh, str) or not ANH_RE.fullmatch(anh):
        raise RunError(f"Tên ảnh {anh!r} không hợp lệ.")
    if loai not in LOAI_CODES:
        raise RunError("Chọn loại ca khó trước khi lưu.")
    diem = clean_diem(diem, known_points)
    ghi_chu = clean_text(ghi_chu, NOTE_MAX, "Ghi chú")
    quyet_dinh_ra = quyet_dinh_ra if quyet_dinh_ra in DECISIONS_OK else ""
    when = iso(now or now_local())
    with _LOCK:
        rows = read_marks(run_dir)
        for r in rows:
            if r["nguoi"] == nguoi and r["anh"] == anh:
                r.update(loai=loai, diem=diem, ghi_chu=ghi_chu, sua_luc=when, quyet_dinh_ra=quyet_dinh_ra)
                _write_marks(run_dir, rows)
                return dict(r), False
        row = dict(luot=run_label(run_dir), anh=anh, nguoi=nguoi, loai=loai, diem=diem, ghi_chu=ghi_chu, tao_luc=when, sua_luc=when,
                   quyet_dinh_ra=quyet_dinh_ra)
        rows.append(row)
        _write_marks(run_dir, rows)
        return dict(row), True


def delete_mark(run_dir, nguoi, anh, runs_root=None):
    check_run_dir(run_dir, runs_root)
    with _LOCK:
        rows = read_marks(run_dir)
        keep = [r for r in rows if not (r["nguoi"] == nguoi and r["anh"] == anh)]
        if len(keep) == len(rows):
            return False
        _write_marks(run_dir, keep)
        return True


def runs_with_marks(runs_root):
    """Tên các lượt dưới runs_root có ca_kho.csv (bỏ _nap và thư mục bắt đầu bằng _), theo thứ tự tên."""
    try:
        names = sorted(os.listdir(runs_root))
    except OSError:
        return []
    out = []
    for d in names:
        p = os.path.join(runs_root, d)
        if d.startswith("_") or not RUN_RE.fullmatch(d) or not os.path.isdir(p) or os.path.islink(p):
            continue
        if os.path.isfile(ca_path(p)):
            out.append(d)
    return out


def member_rows(runs_root, nguoi, luot=None):
    """Ca của `nguoi` ở mọi lượt (hoặc một lượt), mới sửa nhất trước. Lượt hỏng bị bỏ qua (kèm cảnh báo trong warnings)."""
    rows, warnings = [], []
    for d in runs_with_marks(runs_root):
        if luot and d != luot:
            continue
        try:
            for r in read_marks(os.path.join(runs_root, d)):
                if r["nguoi"] == nguoi:
                    rows.append(r)
        except RunError as e:
            warnings.append(str(e))
    rows.sort(key=lambda r: (-_ts(r["sua_luc"]), r["luot"], r["anh"]))
    return rows, warnings


_MANIFEST = {}


def _manifest_data(project_root):
    """(tập `file` của data/manifest.csv, {file: source} hoặc None nếu manifest không có cột `source`); None nếu không đọc được manifest."""
    p = os.path.join(project_root, "data", "manifest.csv")
    try:
        m = os.path.getmtime(p)
    except OSError:
        return None
    if _MANIFEST.get(p, (None,))[0] != m:
        try:
            with open(p, encoding="utf-8-sig", newline="") as f:
                text = f.read()
            reader = csv.DictReader(io.StringIO(text), delimiter=_delim(text))
            has_source = "source" in (reader.fieldnames or [])
            files, src = set(), {}
            for r in reader:
                name = (r.get("file") or "").strip()
                if name:
                    files.add(name)
                    if has_source:
                        src[name] = (r.get("source") or "").strip().lower()
            _MANIFEST[p] = (m, (files, src if has_source else None))
        except (OSError, csv.Error, UnicodeDecodeError):
            return None
    return _MANIFEST[p][1]


def _manifest_files(project_root):
    data = _manifest_data(project_root)
    return None if data is None else data[0]


def _run_faces(run_dir):
    names = set()
    try:
        with open(os.path.join(run_dir, "flags", "flags.json"), encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            names |= set(d)
    except (OSError, ValueError):
        pass
    try:
        with open(os.path.join(run_dir, "no_face.csv"), encoding="utf-8-sig", newline="") as f:
            names |= {_stem((r.get("name") or "").strip()) for r in csv.DictReader(f)}
    except (OSError, csv.Error, UnicodeDecodeError):
        pass
    try:
        names |= {_stem(x) for x in os.listdir(os.path.join(run_dir, "crop", "images")) if x.lower().endswith(".png")}
    except OSError:
        pass
    return {n for n in names if n}


def run_source(run_dir, project_root):
    """Nguồn của một lượt, chỉ khi lượt KHÔNG có inbox/ và MỌI mặt của lượt (tên X.png) có trong cột `file` của data/manifest.csv:
      * manifest có cột `source` (in-cabin): tập giá trị `source` của các mặt đó: 'yawdd', 'drivface' hoặc 'yawdd+drivface' (cả hai);
        giá trị lạ hoặc trống ở một mặt thì 'khong_ro';
      * manifest không có cột `source`: 'khong_ro' (không biết bộ nào; lượt cũ trước QĐ-001 cũng rơi vào đây).
    Còn lại (lượt Nạp ảnh, không có manifest, tên lạ, lượt rỗng) là 'khong_ro' = có thể là ảnh khách hàng."""
    if os.path.exists(os.path.join(run_dir, "inbox")):
        return "khong_ro"
    data = _manifest_data(project_root)
    faces = _run_faces(run_dir)
    if not data or not data[0] or not faces:
        return "khong_ro"
    files, src = data
    if not all(n + ".png" in files for n in faces):
        return "khong_ro"
    if src is None:
        return "khong_ro"
    vals = {src.get(n + ".png", "") for n in faces}
    if not vals or not vals <= set(NGUON_IN_CABIN):
        return "khong_ro"
    return "+".join(v for v in NGUON_IN_CABIN if v in vals)


# ---------- ảnh ----------
def source_image(run_dir, anh):
    """Ảnh chồng của mặt, thiếu thì ảnh cắt, thiếu cả hai thì None."""
    s = _stem(anh)
    if not ANH_RE.fullmatch(anh):
        return None
    for sub in ("overlays", os.path.join("crop", "images")):
        p = os.path.join(run_dir, sub, s + ".png")
        if os.path.isfile(p) and _inside(p, run_dir):
            return p
    return None


def encode_jpeg(src, max_side, quality):
    """Mở ảnh (đường dẫn hoặc bytes), xoay theo EXIF, RGB, cạnh dài tối đa max_side, JPEG tối ưu, KHÔNG EXIF. Trả bytes."""
    from PIL import Image, ImageOps
    with Image.open(io.BytesIO(src) if isinstance(src, (bytes, bytearray)) else src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        im.save(out, "JPEG", quality=quality, optimize=True)
        return out.getvalue()


def small_thumb(run_dir, anh, out_dir, size=112):
    """Ảnh nhỏ (JPEG) của ca cho danh sách thành viên, tạo vào out_dir. Không có ảnh nguồn hoặc hỏng thì None."""
    src = source_image(run_dir, anh)
    if not src:
        return None
    out = os.path.join(out_dir, re.sub(r"[^\w.-]", "_", f"{run_label(run_dir)}__{_stem(anh)}") + ".jpg")
    try:
        if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
            return out
        os.makedirs(out_dir, exist_ok=True)
        _atomic_write(out, encode_jpeg(src, size, 80))
        return out
    except (OSError, ValueError, SyntaxError):
        return None
    except Exception:                                    # PIL: ảnh hỏng, quá lớn...
        return None


def file_url(path):
    """URL phát file của Gradio cho một đường dẫn tuyệt đối (dùng dấu / cả trên Windows)."""
    p = os.path.abspath(path).replace("\\", "/")
    return "/gradio_api/file=" + urllib.parse.quote(p, safe="/:")


def jpg_name(luot, anh, used):
    """Tên mục ảnh trong gói: anh/<luot>__<stem>.jpg, khớp ENTRY_RE, không trùng."""
    base = re.sub(r"[^A-Za-z0-9_-]", "_", f"{luot}__{_stem(anh)}")
    if len(base) > 100:
        base = base[:90] + "_" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:8]
    name, n = base, 1
    while name in used:
        n += 1
        name = f"{base[:94]}_{n}"
    used.add(name)
    return f"anh/{name}.jpg"


# ---------- xuất gói họp ----------
def build_package(runs_root, project_root, nguoi, luot_filter=None, kem_anh=True, kem_khong_ro=False, now=None):
    """Ghi outputs/ca_kho/ca_kho_<người>_<ddmm>.zip gồm đúng ba loại mục: manifest.json, ca_kho.csv, anh/<lượt>__<stem>.jpg.
    Ảnh chỉ kèm cho lượt có nguồn là một bộ dữ liệu đã biết (yawdd, drivface hoặc cả hai), không kèm lượt 'khong_ro' trừ khi `kem_khong_ro`
    (tên tham số giữ như cũ vì có chỗ gọi: nghĩa là "kèm cả lượt không rõ nguồn"). Trả dict(path, rel, so_ca, so_anh, bytes, replaced, luot, bo_anh, nguon).
    0 ca -> RunError, không tạo file. Quá MAX_GOI sau khi thử ảnh nhỏ hơn -> RunError."""
    now = now or now_local()
    check_name(nguoi)
    rows, _warn = member_rows(runs_root, nguoi)
    if luot_filter:
        want = set(luot_filter if not isinstance(luot_filter, str) else [luot_filter])
        rows = [r for r in rows if r["luot"] in want]
    if not rows:
        raise RunError("Chưa có ca khó nào để xuất: bấm K ở tab Rà soát để đánh dấu trước.")
    if len(rows) > MAX_CA:
        raise RunError(f"Có {len(rows)} ca, tối đa {MAX_CA} ca mỗi gói: chọn từng lượt rồi xuất lần lượt.")
    rows.sort(key=lambda r: (r["luot"], r["anh"]))
    luots = sorted({r["luot"] for r in rows})
    nguon = {l: run_source(os.path.join(runs_root, l), project_root) for l in luots}
    bo_anh = {}
    for l in luots:
        if not kem_anh:
            bo_anh[l] = "không chọn kèm ảnh"
        elif nguon[l] not in NGUON_BO_DU_LIEU and not kem_khong_ro:
            bo_anh[l] = "không rõ nguồn (có thể là ảnh khách hàng)"
    out_dir = serve_dir(project_root)
    path = os.path.join(out_dir, f"ca_kho_{nguoi}_{ddmm(now)}.zip")
    if not _inside(path, out_dir):
        raise RunError("Đường dẫn gói nằm ngoài outputs/ca_kho.")
    with _PKG_LOCK:
        replaced = os.path.exists(path)
        last_size = 0
        for max_side, quality in IMG_SIDES:
            tmp = path + f".tmp{os.getpid()}"
            try:
                info = _write_zip(tmp, rows, runs_root, nguoi, luots, nguon, bo_anh, now, max_side, quality)
                last_size = os.path.getsize(tmp)
                if last_size <= MAX_GOI:
                    os.replace(tmp, path)
                    info.update(path=path, rel=os.path.join("outputs", "ca_kho", os.path.basename(path)), bytes=last_size,
                                replaced=replaced, luot=luots, bo_anh=bo_anh, nguon=nguon, so_ca=len(rows))
                    return info
            except OSError as e:
                raise RunError(f"Không ghi được gói họp ({type(e).__name__}). Đóng file zip cũ nếu đang mở rồi bấm lại.")
            finally:
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
        raise RunError(f"Gói họp lớn {last_size / 1048576:.1f} MB, vượt {MAX_GOI // 1048576} MB dù đã thu nhỏ ảnh: "
                       "chọn từng lượt rồi xuất lần lượt, hoặc bỏ chọn kèm ảnh.")


def _write_zip(tmp, rows, runs_root, nguoi, luots, nguon, bo_anh, now, max_side, quality):
    used, images, out_rows = set(), {}, []
    for r in rows:
        thumb = ""
        if r["luot"] not in bo_anh:
            src = source_image(os.path.join(runs_root, r["luot"]), r["anh"])
            if src:
                try:
                    data = encode_jpeg(src, max_side, quality)
                    thumb = jpg_name(r["luot"], r["anh"], used)
                    images[thumb] = data
                except Exception:                       # ảnh hỏng: ca vẫn xuất, không kèm ảnh
                    thumb = ""
        out_rows.append(dict(r, thumb=thumb))
    manifest = {"loai_goi": LOAI_FILE, "phien_ban": PHIEN_BAN, "nguoi": nguoi, "ngay": now.strftime("%Y-%m-%d"), "tao_luc": iso(now),
                "luot": luots, "nguon": nguon, "so_ca": len(rows), "so_anh": len(images), "kem_anh": bool(images)}
    dt = (max(now.year, 1980), now.month, now.day, now.hour, now.minute, now.second)

    def put(zf, name, data, ctype):
        zi = zipfile.ZipInfo(name, date_time=dt)
        zi.compress_type = ctype
        zi.external_attr = 0o644 << 16
        zf.writestr(zi, data)

    with zipfile.ZipFile(tmp, "w") as zf:
        put(zf, "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1).encode("utf-8"), zipfile.ZIP_DEFLATED)
        put(zf, "ca_kho.csv", csv_text(PKG_COLS, out_rows).encode("utf-8-sig"), zipfile.ZIP_DEFLATED)
        for name, data in images.items():
            put(zf, name, data, zipfile.ZIP_STORED)
    return {"so_anh": len(images), "kem_anh": manifest["kem_anh"]}


# ---------- nhập gói họp ----------
def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _short(name):
    s = repr(str(name))
    return s if len(s) <= 60 else s[:57] + "…'"


def _read_entry(zf, info, limit, what, budget):
    """Đọc một mục có giới hạn byte THẬT SỰ đọc được (không tin file_size khai báo) và tổng giải nén."""
    try:
        with zf.open(info) as f:
            data = f.read(limit + 1)
    except (zipfile.BadZipFile, zlib.error, EOFError, NotImplementedError, RuntimeError, OSError) as e:
        raise GoiLoi(f"Không giải nén được {what} ({type(e).__name__}): gói hỏng.")
    if len(data) > limit:
        raise GoiLoi(f"{what} lớn hơn {limit // 1024} KB sau khi giải nén: từ chối.")
    budget[0] += len(data)
    if budget[0] > MAX_TONG:
        raise GoiLoi(f"Tổng dung lượng giải nén vượt {MAX_TONG // 1048576} MB: từ chối (nghi zip bomb).")
    return data


def _reencode_checked(data, what):
    """Ảnh trong gói: phải là JPEG đọc được, ≤ MAX_IMG_PIXELS; mã hoá lại thành JPEG mới (không chép byte gốc, không EXIF)."""
    from PIL import Image
    try:
        with Image.open(io.BytesIO(data)) as im:
            fmt, (w, h) = im.format, im.size
            if fmt != "JPEG":
                raise GoiLoi(f"{what} không phải JPEG.")
            if w < 1 or h < 1 or w * h > MAX_IMG_PIXELS:
                raise GoiLoi(f"{what} có kích thước {w}x{h} vượt giới hạn {MAX_IMG_PIXELS // 1000000} megapixel.")
            im.verify()
        return encode_jpeg(data, IMG_SIDES[0][0], IMG_SIDES[0][1])
    except GoiLoi:
        raise
    except Exception:
        raise GoiLoi(f"{what} hỏng hoặc không đọc được.")


class Package:
    """Gói đã kiểm: nguoi, ngay, luot, nguon, rows (đã làm sạch, thêm `thumb_bytes`), sha256, so_ca."""

    def __init__(self, nguoi, ngay, luot, nguon, rows, sha256):
        self.nguoi, self.ngay, self.luot, self.nguon, self.rows, self.sha256 = nguoi, ngay, luot, nguon, rows, sha256
        self.so_ca = len(rows)


def read_package(path):
    """Kiểm và đọc một gói họp. Sai thì GoiLoi (tiếng Việt). KHÔNG extractall, KHÔNG chạy hay import gì từ gói."""
    try:
        size = os.path.getsize(path)
    except OSError:
        raise GoiLoi("Không đọc được file gói.")
    if size > MAX_GOI:
        raise GoiLoi(f"File gói {size / 1048576:.1f} MB, lớn hơn {MAX_GOI // 1048576} MB: từ chối.")
    sha = _sha256(path)
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError, EOFError, zlib.error):
        raise GoiLoi("Không phải file zip hợp lệ.")
    with zf:
        infos = zf.infolist()
        if len(infos) > MAX_CA + 2:
            raise GoiLoi(f"Gói có {len(infos)} mục, nhiều hơn {MAX_CA + 2}: từ chối.")
        entries = {}
        for info in infos:
            name = info.filename
            if info.is_dir():
                continue                                   # mục thư mục: bỏ qua (không bao giờ giải nén ra đĩa)
            if info.flag_bits & 0x1:
                raise GoiLoi(f"Mục {_short(name)} bị mã hoá: từ chối.")
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise GoiLoi(f"Mục {_short(name)} là liên kết (symlink): từ chối.")
            if not ENTRY_RE.fullmatch(name):
                raise GoiLoi(f"Mục {_short(name)} có tên không hợp lệ: gói chỉ được có manifest.json, ca_kho.csv và anh/<tên>.jpg.")
            if name in entries:
                raise GoiLoi(f"Mục {_short(name)} xuất hiện hai lần: từ chối.")
            if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise GoiLoi(f"Mục {_short(name)} dùng kiểu nén lạ: từ chối.")
            entries[name] = info
        for need in ("manifest.json", "ca_kho.csv"):
            if need not in entries:
                raise GoiLoi(f"Thiếu {need} trong gói.")
        budget = [0]
        man = _manifest_check(_read_entry(zf, entries["manifest.json"], MAX_MANIFEST, "manifest.json", budget))
        rows = _csv_check(_read_entry(zf, entries["ca_kho.csv"], MAX_CSV, "ca_kho.csv", budget), man, set(entries))
        cache = {}
        for r in rows:
            t = r["thumb"]
            if t:
                if t not in cache:
                    cache[t] = _reencode_checked(_read_entry(zf, entries[t], MAX_IMG_BYTES, t, budget), t)
                r["thumb_bytes"] = cache[t]
            else:
                r["thumb_bytes"] = b""
    return Package(man["nguoi"], man["ngay"], man["luot"], man["nguon"], rows, sha)


def _manifest_check(raw):
    try:
        m = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        raise GoiLoi("manifest.json không phải JSON hợp lệ.")
    if not isinstance(m, dict):
        raise GoiLoi("manifest.json phải là một đối tượng JSON.")
    if m.get("loai_goi") != LOAI_FILE:
        raise GoiLoi(f"manifest.json: loai_goi phải là {LOAI_FILE!r}: đây không phải gói họp ca khó.")
    if m.get("phien_ban") != PHIEN_BAN or isinstance(m.get("phien_ban"), bool):
        raise GoiLoi(f"manifest.json: phiên bản gói {m.get('phien_ban')!r} chưa được hỗ trợ (cần {PHIEN_BAN}).")
    if not isinstance(m.get("nguoi"), str) or not NGUOI_RE.fullmatch(m["nguoi"]):
        raise GoiLoi("manifest.json: tên người không hợp lệ (chỉ chữ không dấu, số, _ và -, tối đa 32 ký tự).")
    ngay = m.get("ngay")
    try:
        datetime.date.fromisoformat(ngay)
    except (TypeError, ValueError):
        raise GoiLoi("manifest.json: ngày phải dạng yyyy-mm-dd.")
    so_ca = m.get("so_ca")
    if not isinstance(so_ca, int) or isinstance(so_ca, bool) or not 0 <= so_ca <= MAX_CA:
        raise GoiLoi("manifest.json: so_ca không hợp lệ.")
    luot = m.get("luot", [])
    if not isinstance(luot, list) or any(not isinstance(x, str) or not RUN_RE.fullmatch(x) for x in luot):
        raise GoiLoi("manifest.json: danh sách lượt không hợp lệ.")
    nguon = m.get("nguon", {})
    if not isinstance(nguon, dict) or any(k not in luot or v not in NGUON_VI for k, v in nguon.items()):
        raise GoiLoi("manifest.json: nguồn của lượt không hợp lệ.")
    return dict(nguoi=m["nguoi"], ngay=ngay, so_ca=so_ca, luot=luot, nguon=nguon)


def _csv_check(raw, man, entry_names):
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise GoiLoi("ca_kho.csv không phải UTF-8.")
    try:
        rd = csv.DictReader(io.StringIO(text, newline=""))
        missing = [c for c in PKG_COLS if c not in (rd.fieldnames or [])]
        if missing:
            raise GoiLoi("ca_kho.csv thiếu cột: " + ", ".join(missing) + ".")
        rows, keys = [], set()
        for i, r in enumerate(rd, start=2):
            if None in r:
                raise GoiLoi(f"ca_kho.csv dòng {i} thừa cột.")
            row = {c: (r.get(c) or "") for c in PKG_COLS}
            if row["nguoi"] != man["nguoi"]:
                raise GoiLoi(f"ca_kho.csv dòng {i}: người {row['nguoi'][:20]!r} khác người trong manifest ({man['nguoi']}).")
            if row["loai"] not in LOAI_CODES:
                raise GoiLoi(f"ca_kho.csv dòng {i}: loại {row['loai'][:30]!r} không có trong danh sách loại.")
            if not RUN_RE.fullmatch(row["luot"]):
                raise GoiLoi(f"ca_kho.csv dòng {i}: tên lượt không hợp lệ.")
            if not ANH_RE.fullmatch(row["anh"]):
                raise GoiLoi(f"ca_kho.csv dòng {i}: tên ảnh không hợp lệ.")
            if len(row["ghi_chu"]) > NOTE_MAX:
                raise GoiLoi(f"ca_kho.csv dòng {i}: ghi chú dài hơn {NOTE_MAX} ký tự.")
            if len(row["diem"]) > DIEM_MAX or any(p and not POINT_RE.fullmatch(p) for p in row["diem"].split(";")):
                raise GoiLoi(f"ca_kho.csv dòng {i}: danh sách điểm không hợp lệ.")
            if row["quyet_dinh_ra"] not in ("",) + DECISIONS_OK:
                raise GoiLoi(f"ca_kho.csv dòng {i}: quyet_dinh_ra không hợp lệ.")
            for c in ("tao_luc", "sua_luc"):
                if len(row[c]) > 40 or (row[c] and parse_time(row[c]) is None):
                    raise GoiLoi(f"ca_kho.csv dòng {i}: {c} không phải thời gian ISO.")
            if not row["tao_luc"]:
                raise GoiLoi(f"ca_kho.csv dòng {i}: thiếu tao_luc.")
            row["sua_luc"] = row["sua_luc"] or row["tao_luc"]
            t = row["thumb"]
            if t and (not t.startswith("anh/") or t not in entry_names):
                raise GoiLoi(f"ca_kho.csv dòng {i}: ảnh {t[:40]!r} không có trong gói.")
            row["ghi_chu"] = clean_text(row["ghi_chu"], NOTE_MAX)
            k = (row["nguoi"], row["luot"], row["anh"])
            if k in keys:
                raise GoiLoi(f"ca_kho.csv: ca {row['luot']}/{row['anh']} của {row['nguoi']} xuất hiện hai lần trong gói: từ chối cả gói.")
            keys.add(k)
            rows.append(row)
    except csv.Error:
        raise GoiLoi("ca_kho.csv sai định dạng CSV.")
    if len(rows) != man["so_ca"]:
        raise GoiLoi(f"manifest.json ghi {man['so_ca']} ca nhưng ca_kho.csv có {len(rows)} dòng.")
    return rows


# ---------- phiên họp ----------
def case_key(nguoi, luot, anh):
    return f"{nguoi}|{luot}|{anh}"


def default_backlog(loai):
    """(loai_backlog, ghi_backlog) mặc định theo loại ca."""
    if LOAI_NHOM.get(loai) == "loi":
        return "Guideline mơ hồ", False
    return BACKLOG_DEFAULT.get(loai, "Guideline chưa nói tới"), True


def _case_image_name(c):
    base = re.sub(r"[^A-Za-z0-9_-]", "_", f"{c['nguoi']}__{c['luot']}__{_stem(c['anh'])}")
    if len(base) > 100:
        base = base[:90] + "_" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:8]
    return f"anh/{base}.jpg"


class Meeting:
    """Một phiên họp: outputs/ca_kho/hop_<ddmm>/{hop.json, anh/}. Có khoá; ghi hop.json nguyên tử."""
    ORG_FIELDS = ("trang_thai", "quyet_dinh", "phu_trach", "loai_backlog", "ghi_backlog", "muc_guideline", "sua_hop_luc")

    def __init__(self, dir_path, data):
        self.dir, self.data = dir_path, data
        self.lock = threading.RLock()

    @property
    def name(self):
        return os.path.basename(self.dir)

    @property
    def cases(self):
        return self.data["ca"]

    # --- tạo / mở / liệt kê ---
    @classmethod
    def create(cls, serve, organizer, now=None):
        now = now or now_local()
        check_name(organizer)
        os.makedirs(serve, exist_ok=True)
        base, n = f"hop_{ddmm(now)}", 1
        with _PKG_LOCK:
            while True:
                name = base if n == 1 else f"{base}_{n}"
                path = os.path.join(serve, name)
                try:
                    os.makedirs(path)
                    break
                except FileExistsError:
                    n += 1
        os.makedirs(os.path.join(path, "anh"), exist_ok=True)
        m = cls(path, {"phien_ban": PHIEN_BAN, "ngay": now.strftime("%Y-%m-%d"), "nguoi_to_chuc": organizer, "tao_luc": iso(now),
                       "goi": [], "ca": {}})
        m.save()
        return m

    @classmethod
    def load(cls, serve, name):
        if not isinstance(name, str) or not HOP_RE.fullmatch(name):
            raise RunError(f"Tên phiên {name!r} không hợp lệ.")
        path = os.path.join(serve, name)
        if not _inside(path, serve):
            raise RunError("Phiên nằm ngoài outputs/ca_kho.")
        try:
            with open(os.path.join(path, "hop.json"), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            raise RunError(f"Không đọc được {name}/hop.json: phiên chưa có hoặc file hỏng.")
        if not isinstance(data, dict) or not isinstance(data.get("ca"), dict) or not isinstance(data.get("goi"), list):
            raise RunError(f"{name}/hop.json sai định dạng.")
        data.setdefault("nguoi_to_chuc", "")
        return cls(path, data)

    @staticmethod
    def list_sessions(serve):
        """Tên các phiên hop_* (mới nhất trước)."""
        out = []
        try:
            names = os.listdir(serve)
        except OSError:
            return []
        for d in names:
            p = os.path.join(serve, d, "hop.json")
            if HOP_RE.fullmatch(d) and os.path.isfile(p):
                try:
                    with open(p, encoding="utf-8") as f:
                        t = _ts(json.load(f).get("tao_luc", ""))
                except (OSError, ValueError, AttributeError):
                    t = 0.0
                out.append((t or os.path.getmtime(p), d))
        return [d for _t, d in sorted(out, reverse=True)]

    def save(self):
        with self.lock:
            _atomic_write(os.path.join(self.dir, "hop.json"), json.dumps(self.data, ensure_ascii=False, indent=1).encode("utf-8"))

    # --- nhập gói ---
    def import_packages(self, items, now=None):
        """items: [(đường dẫn file, tên hiển thị)]. Trả danh sách báo cáo, mỗi gói một dict
        (ten, nguoi, trang_thai: ok|da_nhap|loi, moi, cap_nhat, trung, ly_do). Gói lỗi không làm hỏng gói khác."""
        now = now or now_local()
        report = []
        for path, ten in items:
            ten = os.path.basename(str(ten))[:120]
            rep = dict(ten=ten, nguoi="", trang_thai="loi", moi=0, cap_nhat=0, trung=0, ly_do="")
            try:
                pkg = read_package(path)
                rep["nguoi"] = pkg.nguoi
                with self.lock:
                    if any(g.get("sha256") == pkg.sha256 for g in self.data["goi"]):
                        rep.update(trang_thai="da_nhap", ly_do="đã nhập rồi, bỏ qua")
                    else:
                        self._merge(pkg, rep, ten, now)
            except GoiLoi as e:
                rep["ly_do"] = str(e)
            except (OSError, RunError) as e:
                rep["ly_do"] = f"Không ghi được vào phiên họp ({type(e).__name__}): kiểm thư mục outputs\\ca_kho."
            except Exception as e:                       # PIL, bộ nhớ... không làm sập cả lần nhập
                rep["ly_do"] = f"Lỗi không rõ khi đọc gói ({type(e).__name__})."
            report.append(rep)
        return report

    def _merge(self, pkg, rep, ten, now):
        img_dir = os.path.join(self.dir, "anh")
        os.makedirs(img_dir, exist_ok=True)
        pending, changed = [], []
        for r in pkg.rows:
            key = case_key(r["nguoi"], r["luot"], r["anh"])
            nguon = pkg.nguon.get(r["luot"], "khong_ro")
            cur = self.cases.get(key)
            thumb_rel = ""
            if r["thumb_bytes"]:
                thumb_rel = _case_image_name(r)
            if cur is None:
                bl, ghi = default_backlog(r["loai"])
                new = {c: r[c] for c in CSV_COLS}
                new.update(thumb=thumb_rel, nguon=nguon, trang_thai="mo", quyet_dinh="", phu_trach="", loai_backlog=bl, ghi_backlog=ghi,
                           muc_guideline="", sua_hop_luc="")
                pending.append((key, new, r["thumb_bytes"], thumb_rel))
                rep["moi"] += 1
            elif _ts(r["sua_luc"]) > _ts(cur["sua_luc"]):
                upd = {c: r[c] for c in ("loai", "diem", "ghi_chu", "sua_luc", "quyet_dinh_ra")}
                upd["nguon"] = nguon
                if thumb_rel:
                    upd["thumb"] = thumb_rel
                pending.append((key, upd, r["thumb_bytes"], thumb_rel))
                rep["cap_nhat"] += 1
            else:
                rep["trung"] += 1
        for key, fields, data, rel in pending:                    # ghi ảnh trước, rồi mới đổi bộ nhớ và hop.json
            if data and rel:
                _atomic_write(os.path.join(self.dir, *rel.split("/")), data)
        for key, fields, _d, _r in pending:
            cur = self.cases.get(key)
            if cur is None:
                self.cases[key] = fields
            else:
                cur.update(fields)
                if not cur.get("sua_hop_luc"):                    # người tổ chức chưa đụng tới: gợi ý backlog theo loại mới
                    cur["loai_backlog"], cur["ghi_backlog"] = default_backlog(cur["loai"])
        self.data["goi"].append(dict(ten=ten, sha256=pkg.sha256, nguoi=pkg.nguoi, so_ca=pkg.so_ca, nhap_luc=iso(now), ket_qua="ok"))
        self.save()
        rep["trang_thai"] = "ok"

    # --- đọc ---
    def nguoi_list(self):
        return sorted({c["nguoi"] for c in self.cases.values()})

    def sorted_keys(self, keys=None):
        ks = list(self.cases) if keys is None else list(keys)
        return sorted(ks, key=lambda k: (LOAI_ORDER.get(self.cases[k]["loai"], 99), self.cases[k]["nguoi"], self.cases[k]["luot"],
                                         self.cases[k]["anh"]))

    def filtered(self, loai="", nguoi="", trang_thai="", text=""):
        text = unicodedata.normalize("NFC", (text or "")).strip().lower()
        out = []
        for k, c in self.cases.items():
            if loai and c["loai"] != loai:
                continue
            if nguoi and c["nguoi"] != nguoi:
                continue
            if trang_thai and c["trang_thai"] != trang_thai:
                continue
            if text and text not in (c["ghi_chu"] + " " + c["quyet_dinh"] + " " + c["anh"]).lower():
                continue
            out.append(k)
        return self.sorted_keys(out)

    def counts(self):
        by = {"loai": {}, "nguoi": {}, "trang_thai": {}}
        for c in self.cases.values():
            for f in by:
                by[f][c[f]] = by[f].get(c[f], 0) + 1
        return by

    def face_id(self, c):
        """Cùng một mặt: ảnh của bộ dữ liệu (YawDD, DrivFace) lấy theo tên ảnh (mọi người dùng chung data/manifest.csv), còn lại theo (lượt, ảnh)."""
        return ("bo_du_lieu", c["anh"]) if c.get("nguon") in NGUON_BO_DU_LIEU else (c["luot"], c["anh"])

    def same_face(self, key):
        c = self.cases.get(key)
        if not c:
            return []
        fid = self.face_id(c)
        return self.sorted_keys([k for k, x in self.cases.items() if self.face_id(x) == fid])

    # --- sửa trường của người tổ chức ---
    def set_fields(self, key, trang_thai=None, quyet_dinh=None, phu_trach=None, loai_backlog=None, ghi_backlog=None,
                   muc_guideline=None, now=None):
        """Đặt trường của người tổ chức rồi lưu. Trả danh sách cảnh báo (rỗng nếu ổn)."""
        with self.lock:
            c = self.cases.get(key)
            if c is None:
                raise RunError("Ca này không còn trong phiên họp.")
            new = {}
            if trang_thai is not None:
                if trang_thai not in TT_CODES:
                    raise RunError("Trạng thái không hợp lệ.")
                new["trang_thai"] = trang_thai
            if quyet_dinh is not None:
                new["quyet_dinh"] = clean_text(quyet_dinh, QD_MAX, "Quyết định")
            if phu_trach is not None:
                p = (phu_trach or "").strip()
                if p and not NGUOI_RE.fullmatch(p):
                    raise RunError("Người phụ trách chỉ gồm chữ không dấu, số, _ và - (tối đa 32 ký tự), ví dụ P3.")
                new["phu_trach"] = p
            if loai_backlog is not None:
                if loai_backlog not in BACKLOG_LOAI:
                    raise RunError("Loại backlog không hợp lệ.")
                new["loai_backlog"] = loai_backlog
            if ghi_backlog is not None:
                new["ghi_backlog"] = bool(ghi_backlog)
            if muc_guideline is not None:
                m = clean_text(muc_guideline, 40, "Mục guideline").lstrip("§").strip()
                if m and not re.fullmatch(r"[0-9A-Za-z.,()\- ]{1,40}", m):
                    raise RunError("Mục guideline chỉ gồm số, chữ không dấu, dấu chấm, phẩy, gạch (ví dụ 3.2).")
                new["muc_guideline"] = m
            c.update(new)
            c["sua_hop_luc"] = iso(now or now_local())
            self.save()
            warn = []
            if c["trang_thai"] == "da_chot" and not c["quyet_dinh"]:
                warn.append("Đã chốt nhưng chưa có quyết định: biên bản sẽ không tạo QĐ cho ca này.")
            return warn


# ---------- biên bản ----------
def find_repo_docs(start=TOOL_DIR):
    """(đường dẫn problem-backlog.md, đường dẫn so-quyet-dinh.md): đi lên tối đa 4 cấp từ `start`, mỗi cấp xem thư mục đó rồi thư mục con report-tool/
    (bố cục repo project của khoá); không thấy thì None."""
    cur = os.path.abspath(start)
    for _ in range(5):
        for d in (cur, os.path.join(cur, "report-tool")):
            pb, qd = os.path.join(d, "problem-backlog.md"), os.path.join(d, "so-quyet-dinh.md")
            if os.path.isfile(pb) or os.path.isfile(qd):
                return (pb if os.path.isfile(pb) else None), (qd if os.path.isfile(qd) else None)
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return None, None


def read_text(path):
    if not path:
        return ""
    try:
        with open(path, encoding="utf-8-sig") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return ""


_FENCE = re.compile(r"```.*?(?:```|\Z)", re.DOTALL)


def next_number(text, prefix):
    """Số lớn nhất + 1 của P-(\\d+) (prefix 'P') hoặc QĐ-(\\d+) (prefix 'QĐ') ở tiêu đề `## P-012` hoặc ô đầu bảng `| P-012 |`.
    Bỏ qua nội dung trong khối ``` (mẫu P-NNN). Không có thì 1."""
    text = unicodedata.normalize("NFC", text or "")
    text = _FENCE.sub("", text)
    pre = "P" if prefix == "P" else "QĐ"
    pat = re.compile(r"^(?:##[ \t]+|\|[ \t]*\[?)" + re.escape(pre) + r"-(\d+)\b", re.MULTILINE | re.IGNORECASE)
    nums = [int(m.group(1)) for m in pat.finditer(text)]
    return (max(nums) + 1) if nums else 1


def _one_line(s):
    return re.sub(r"\s+", " ", (s or "").replace("\n", " ")).strip()


def _cell(s):
    return _one_line(s).replace("|", "\\|")


def _summary(c):
    first = _one_line((c["ghi_chu"] or "").split("\n", 1)[0])
    if not first:
        return f"{LOAI_VI[c['loai']]} ở {c['anh']} (lượt {c['luot']})"
    return first if len(first) <= 90 else first[:89].rstrip() + "…"


def _short_line(s, n=90):
    s = _one_line(s)
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


def _p_block(code, c, qd_code):
    ket = TT_ICON[c["trang_thai"]] + (f" ({qd_code})" if c["trang_thai"] == "da_chot" and qd_code else "")
    diem = c["diem"].replace(";", ", ") or "—"
    cach = "Hướng đang cân nhắc" if c["loai_backlog"] == "Pain point công cụ" else "Các cách hiểu"
    lines = [f"## {code}", "", f"**{_summary(c)}**", "",
             f"- **Loại:** {c['loai_backlog']}",
             f"- **Mục guideline:** §{c['muc_guideline']}",
             f"- **Người phát hiện:** @{c['nguoi']} · {fmt_date(c['tao_luc'])}",
             "- **Link CVAT:** (bỏ trống nếu không có)",
             f"  - Không có link CVAT; ảnh {c['anh']}, lượt {c['luot']}, mã {c['loai']}, điểm {diem} (ảnh chồng trong gói họp, không dán vào repo)",
             f"- **Mô tả:** {_one_line(c['ghi_chu'])}",
             f"- **{cach}:**", "  1.", "  2.",
             "- **Xử lý tạm trong lúc chờ:**",
             f"- **Kết quả:** {ket}"]
    return "\n".join(lines)


def _qd_block(code, c, p_code, day, people, organizer):
    nguon = f"[{p_code}](problem-backlog.md#{p_code.lower()})" if p_code else f"Họp ca khó {day[:5]} (ca {c['loai']} {c['anh']} của {c['nguoi']})"
    boi = _one_line(c["ghi_chu"]) or f"Họp ca khó {day[:5]}: {LOAI_VI[c['loai']]} ở {c['anh']} (lượt {c['luot']})"
    ai = c["phu_trach"] or organizer
    lines = [f"## {code}", "", f"**{_short_line(c['quyet_dinh'])}**", "",
             f"- **Ngày:** {day}",
             "- **Người tham gia:** " + ", ".join([f"@{organizer} (chốt)"] + [f"@{p}" for p in people if p != organizer]),
             f"- **Xuất phát từ:** {nguon}",
             f"- **Bối cảnh:** {boi}",
             "- **Các phương án đã cân nhắc:**", "  1.", "  2.",
             f"- **Quyết định:** {_one_line(c['quyet_dinh'])}",
             "- **Việc phải làm theo:**",
             f"  - [ ] Áp dụng quyết định (@{ai})",
             "- **Trạng thái:** Hiệu lực"]
    return "\n".join(lines)


def build_minutes(meeting, backlog_text="", qd_text="", now=None, found=True):
    """Biên bản markdown điền sẵn đúng mẫu P-NNN / QĐ-NNN, và CSV tổng hợp. KHÔNG ghi vào repo.
    Trả dict(md, csv, p_first, qd_first, n_p, n_qd, warnings, rows)."""
    now = now or now_local()
    d = meeting.data
    day_dt = datetime.date.fromisoformat(d["ngay"])
    day = day_dt.strftime("%d/%m/%Y")
    organizer = d.get("nguoi_to_chuc") or "P5"
    p_next, qd_next = next_number(backlog_text, "P"), next_number(qd_text, "QĐ")
    keys = meeting.sorted_keys()
    cases = [(k, meeting.cases[k]) for k in keys]
    people = sorted({g["nguoi"] for g in d["goi"]} | {c["nguoi"] for _k, c in cases})
    warnings, p_code, qd_code = [], {}, {}
    n = p_next
    for k, c in cases:
        if c["ghi_backlog"]:
            p_code[k] = f"P-{n:03d}"
            n += 1
    m = qd_next
    for k, c in cases:
        if c["trang_thai"] == "da_chot":
            if c["quyet_dinh"]:
                qd_code[k] = f"QĐ-{m:03d}"
                m += 1
            else:
                warnings.append(f"Ca {c['anh']} của {c['nguoi']} (lượt {c['luot']}) đã chốt nhưng chưa có quyết định: không tạo QĐ.")
    p_rows, p_blocks, q_rows, q_blocks = [], [], [], []
    for k, c in cases:
        if k in p_code:
            qd = qd_code.get(k, "")
            p_rows.append(f"| {p_code[k]} | {_cell(_summary(c))} | {c['loai_backlog']} | §{_cell(c['muc_guideline'])} | "
                          f"{TT_ICON[c['trang_thai']]} | {qd} |")
            p_blocks.append(_p_block(p_code[k], c, qd))
        if k in qd_code:
            src = p_code.get(k) or f"Họp ca khó {day[:5]}"
            q_rows.append(f"| {qd_code[k]} | {_cell(_short_line(c['quyet_dinh']))} | {day} | {src} | Hiệu lực |")
            q_blocks.append(_qd_block(qd_code[k], c, p_code.get(k, ""), day, people, organizer))
    cnt = {}
    for _k, c in cases:
        cnt.setdefault(c["loai"], {t: 0 for t in TT_CODES})[c["trang_thai"]] += 1
    head = "| Loại | " + " | ".join(TT_ICON[t] for t in TT_CODES) + " | Tổng |\n|---|" + "---|" * (len(TT_CODES) + 1)
    body = []
    tot = {t: 0 for t in TT_CODES}
    for code in LOAI_CODES:
        if code in cnt:
            body.append(f"| {code} — {LOAI_VI[code]} | " + " | ".join(str(cnt[code][t]) for t in TT_CODES) + f" | {sum(cnt[code].values())} |")
            for t in TT_CODES:
                tot[t] += cnt[code][t]
    body.append("| **Tổng** | " + " | ".join(str(tot[t]) for t in TT_CODES) + f" | {sum(tot.values())} |")
    goi_lines = [f"- @{g['nguoi']}: {g['so_ca']} ca (gói {g['ten']})" for g in d["goi"]] or ["- (chưa nhập gói nào)"]
    note_num = ("Số P/QĐ tính từ nội dung problem-backlog.md và so-quyet-dinh.md lúc xuất; nếu ai đã thêm mục từ đó tới giờ thì xuất lại "
                "trước khi dán.")
    if not found:
        note_num += " Không tìm thấy hai file trong repo trên máy này nên đánh số từ P-001 và QĐ-001: kiểm lại số trước khi dán."
    md = [f"# Biên bản họp ca khó {day}", "",
          f"- **Người tổ chức:** @{organizer}",
          f"- **Phiên họp:** {meeting.name}",
          f"- **Xuất lúc:** {now.strftime('%d/%m/%Y %H:%M')}",
          f"- **Số ca:** {len(cases)} · vào backlog {len(p_code)} · quyết định mới {len(qd_code)}",
          "- **Gói đã nhập:**", *["  " + x for x in goi_lines], "",
          "## Đếm theo loại và trạng thái", "", head, *body, ""]
    if warnings:
        md += ["## Cần xem lại", "", *[f"- {w}" for w in warnings], ""]
    md += ["## Dán vào problem-backlog.md", "", note_num, ""]
    if p_rows:
        md += ["### A. Dòng bảng Danh sách (dán vào cuối bảng)", "", "```markdown", *p_rows, "```", "",
               "### B. Các mục P (dán vào trước dòng `---` của phần Mẫu để copy, hoặc cuối file)", "", "```markdown",
               "\n\n".join(p_blocks), "```", ""]
    else:
        md += ["(Không có ca nào cần ghi vào backlog.)", ""]
    md += ["## Dán vào so-quyet-dinh.md", "", note_num, ""]
    if q_rows:
        md += ["### A. Dòng bảng Danh sách (dán vào cuối bảng)", "", "```markdown", *q_rows, "```", "",
               "### B. Các mục QĐ", "", "```markdown", "\n\n".join(q_blocks), "```", ""]
    else:
        md += ["(Chưa có quyết định nào để ghi vào sổ quyết định.)", ""]
    rows = []
    for k, c in cases:
        rows.append(dict(ma_p=p_code.get(k, ""), ma_qd=qd_code.get(k, ""), ngay=fmt_date(c["tao_luc"]), nguoi=c["nguoi"], luot=c["luot"],
                         anh=c["anh"], diem=c["diem"], loai=c["loai"], ghi_chu=c["ghi_chu"], trang_thai=TT_VI[c["trang_thai"]],
                         quyet_dinh=c["quyet_dinh"], phu_trach=c["phu_trach"], loai_backlog=c["loai_backlog"] if k in p_code else "",
                         muc_guideline=c["muc_guideline"]))
    return dict(md="\n".join(md).rstrip() + "\n", csv=csv_text(TONG_HOP_COLS, rows, safe=True), p_first=p_next, qd_first=qd_next,
                n_p=len(p_code), n_qd=len(qd_code), warnings=warnings, rows=rows)


def write_minutes(meeting, backlog_path, qd_path, now=None):
    """Ghi bien_ban_<ddmm>.md và tong_hop_<ddmm>.csv trong thư mục phiên. Chỉ ĐỌC hai file repo. Trả dict kết quả + đường dẫn."""
    res = build_minutes(meeting, read_text(backlog_path), read_text(qd_path), now, found=bool(backlog_path and qd_path))
    day = meeting.data["ngay"]
    tag = day[8:10] + day[5:7]
    p_md = os.path.join(meeting.dir, f"bien_ban_{tag}.md")
    p_csv = os.path.join(meeting.dir, f"tong_hop_{tag}.csv")
    try:
        _atomic_write(p_md, res["md"].encode("utf-8"))
        _atomic_write(p_csv, res["csv"].encode("utf-8-sig"))
    except OSError as e:
        raise RunError(f"Không ghi được biên bản ({type(e).__name__}). Đóng file cũ nếu đang mở bằng Word hoặc Excel.")
    res.update(md_path=p_md, csv_path=p_csv)
    return res


# ---------- HTML thuần ----------
def e(x):
    return html.escape("" if x is None else str(x), quote=True)


def chip_loai(code):
    return f'<span class="m28-chip ck-l-{e(LOAI_NHOM.get(code, "gl"))}" title="{e(LOAI_VI.get(code, code))}">{e(code)}</span>'


def _fmt_dt(s):
    dt = parse_time(s)
    return dt.strftime("%d/%m %H:%M") if dt else ""


def warn_html():
    return ('<div class="nap-box nap-warn"><b>Gói họp chứa ảnh mặt người thật (tài xế trong xe).</b> Ảnh người lái xe là dữ liệu nhạy cảm, '
            'YawDD và DrivFace chỉ cho dùng học tập, nghiên cứu: chỉ gửi trong đội (Drive riêng tư của đội hoặc gửi trực tiếp), không đăng '
            'công khai, không giao bên thứ ba, không đưa vào chat AI nào. Ảnh khách hàng không bao giờ rời máy.</div>')


def msg_html(text, level="info"):
    return f'<div class="m28-msg m-{e(level)}" role="status">{e(text)}</div>' if text else ""


def list_html(rows, thumbs=None, sources=None):
    """Thẻ ca khó của thành viên. thumbs: {(luot, anh): đường dẫn ảnh nhỏ}."""
    if not rows:
        return '<div class="m28-empty">Chưa có ca khó nào. Ở tab Rà soát, bấm K (hoặc nút Ca khó) khi gặp một mặt khó.</div>'
    thumbs, sources = thumbs or {}, sources or {}
    out = []
    for r in rows:
        t = thumbs.get((r["luot"], r["anh"]))
        img = (f'<img src="{e(file_url(t))}" alt="" loading="lazy">' if t else '<span class="ck-noimg">Không có ảnh</span>')
        src = sources.get(r["luot"], "")
        diem = r["diem"].replace(";", ", ")
        out.append(
            f'<div class="ck-mcard"><div class="ck-mimg">{img}</div><div class="ck-mbody">'
            f'<div class="ck-mtop"><b>{e(r["anh"])}</b> <span class="ck-sub">lượt {e(r["luot"])}'
            f'{" · " + e(NGUON_VI.get(src, src)) if src else ""}</span></div>'
            f'<div>{chip_loai(r["loai"])} <span class="ck-sub">{e(LOAI_VI.get(r["loai"], ""))}</span></div>'
            + (f'<div class="ck-sub">Điểm: <span class="m28-pts">{e(diem)}</span></div>' if diem else "")
            + (f'<div class="ck-mnote">{e(r["ghi_chu"])}</div>' if r["ghi_chu"] else "")
            + f'<div class="ck-sub">sửa {e(_fmt_dt(r["sua_luc"]))}</div></div></div>')
    return f'<div class="ck-mlist" role="list">{"".join(out)}</div>'


def ngoai_html(luots):
    """Hộp đỏ về các lượt không rõ nguồn trong lựa chọn xuất."""
    if not luots:
        return ""
    return ('<div class="nap-box nap-err" role="alert"><b>Lượt không rõ nguồn: ' + ", ".join(e(l) for l in luots) + ".</b> Có thể là ảnh khách hàng "
            "— chỉ bật ô bên dưới nếu chắc chắn không phải; ảnh khách hàng không được rời máy. Mặc định các lượt này xuất ca khó "
            "nhưng không kèm ảnh.</div>")


def package_summary_html(info):
    lines = [f"<b>Đã xuất {info['so_ca']} ca, kèm {info['so_anh']} ảnh, {info['bytes'] / 1048576:.2f} MB</b> → "
             f"<code>{e(info['rel'])}</code>"]
    if info["replaced"]:
        lines.append("Cùng ngày đã có gói của bạn: gói cũ đã được thay bằng gói này.")
    for l, why in info["bo_anh"].items():
        lines.append(f"Lượt {e(l)}: không kèm ảnh, vì {e(why)}.")
    lines.append("Gửi file này cho người tổ chức qua kênh nội bộ của đội (không đăng công khai, không commit).")
    return '<div class="nap-box nap-ok">' + "<br>".join(lines) + "</div>"


def counts_html(meeting):
    if meeting is None or not meeting.cases:
        return ""
    c = meeting.counts()
    parts = []
    for code in LOAI_CODES:
        if code in c["loai"]:
            parts.append(f'<span class="m28-chip ck-l-{LOAI_NHOM[code]}" title="{e(LOAI_VI[code])}">{e(code)} <b>{c["loai"][code]}</b></span>')
    row1 = " ".join(parts)
    row2 = " ".join(f'<span class="m28-chip c-chua">{e(n)} <b>{v}</b></span>' for n, v in sorted(c["nguoi"].items()))
    row3 = " ".join(f'<span class="m28-chip" style="--cc:{TT_COLOR[t]}">{e(TT_VI[t])} <b>{c["trang_thai"].get(t, 0)}</b></span>' for t in TT_CODES)
    return (f'<div class="ck-counts"><div class="ck-crow"><span class="ck-clab">Loại</span>{row1}</div>'
            f'<div class="ck-crow"><span class="ck-clab">Người</span>{row2}</div>'
            f'<div class="ck-crow"><span class="ck-clab">Trạng thái</span>{row3}</div></div>')


def report_html(report):
    if not report:
        return ""
    rows = []
    for r in report:
        if r["trang_thai"] == "ok":
            st = f'<span class="ck-ok">Nhập được</span> — mới {r["moi"]}, cập nhật {r["cap_nhat"]}, trùng {r["trung"]}'
        elif r["trang_thai"] == "da_nhap":
            st = f'<span class="ck-skip">Bỏ qua</span> — {e(r["ly_do"])}'
        else:
            st = f'<span class="ck-bad">Lỗi</span> — {e(r["ly_do"])}'
        rows.append(f'<tr><td>{e(r["ten"])}</td><td>{e(r["nguoi"]) or "—"}</td><td>{st}</td></tr>')
    return ('<table class="ck-report" role="table"><thead><tr><th>File</th><th>Người</th><th>Kết quả</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>")


GROUPS = [("loai", "Loại"), ("nguoi", "Người"), ("trang_thai", "Trạng thái")]


def _group_title(by, v):
    if by == "loai":
        return f"{v} — {LOAI_VI.get(v, v)}"
    if by == "trang_thai":
        return TT_VI.get(v, v)
    return v


def grid_html(meeting, keys, serve, selected="", group_by="loai"):
    """Lưới thẻ theo nhóm. Mỗi thẻ là <button class="ck-card" data-key=...> (JS ủy quyền ghi data-key vào #hop-pick)."""
    if meeting is None:
        return '<div class="m28-empty">Chọn hoặc tạo một phiên họp, rồi nhập các gói zip.</div>'
    if not keys:
        return '<div class="m28-empty">' + ("Chưa có ca nào: nhập các gói zip ở phía trên." if not meeting.cases
                                           else "Không có ca nào khớp bộ lọc.") + "</div>"
    group_by = group_by if group_by in dict(GROUPS) else "loai"
    groups = {}
    for k in keys:
        groups.setdefault(meeting.cases[k][group_by], []).append(k)
    order = (LOAI_CODES if group_by == "loai" else TT_CODES if group_by == "trang_thai" else sorted(groups))
    out = []
    for g in order:
        if g not in groups:
            continue
        cards = []
        for k in groups[g]:
            c = meeting.cases[k]
            if c.get("thumb"):
                p = os.path.join(meeting.dir, *c["thumb"].split("/"))
                img = f'<img src="{e(file_url(p))}" alt="" loading="lazy">' if _inside(p, serve) else '<span class="ck-noimg">Không có ảnh</span>'
            else:
                img = '<span class="ck-noimg">Không có ảnh</span>'
            sel = " sel" if k == selected else ""
            cards.append(
                f'<button type="button" class="ck-card{sel}" data-key="{e(k)}" title="{e(c["anh"])} · {e(LOAI_VI.get(c["loai"], ""))}">'
                f'<span class="ck-img">{img}</span>'
                f'<span class="ck-meta">{chip_loai(c["loai"])}<i class="ck-dot" style="background:{TT_COLOR[c["trang_thai"]]}" '
                f'title="{e(TT_VI[c["trang_thai"]])}"></i></span>'
                f'<span class="ck-sub">{e(c["nguoi"])} · {e(c["anh"])}</span><span class="ck-sub">{e(c["luot"])}</span></button>')
        out.append(f'<section class="ck-group"><h3>{e(_group_title(group_by, g))} <span class="ck-n">{len(groups[g])}</span></h3>'
                   f'<div class="ck-cards">{"".join(cards)}</div></section>')
    return "".join(out)


def stage_html(meeting, key, serve):
    """Ảnh lớn + ghi chú từng người cùng một mặt + quyết định của ca đang chọn (chỉ đọc; dùng cả cho trình chiếu)."""
    c = meeting.cases.get(key) if meeting else None
    if not c:
        return '<div class="m28-empty">Bấm một thẻ ở lưới để xem chi tiết.</div>'
    if c.get("thumb"):
        p = os.path.join(meeting.dir, *c["thumb"].split("/"))
        img = f'<img src="{e(file_url(p))}" alt="Ảnh chồng {e(c["anh"])}">' if _inside(p, serve) else '<div class="ck-noimg">Không có ảnh</div>'
    else:
        img = '<div class="ck-noimg">Gói không kèm ảnh (lượt không rõ nguồn hoặc người gửi tắt ảnh)</div>'
    notes = []
    for k in meeting.same_face(key):
        x = meeting.cases[k]
        diem = x["diem"].replace(";", ", ")
        tri = DECISION_VI.get(x["quyet_dinh_ra"], "")
        notes.append(
            f'<div class="ck-note{" cur" if k == key else ""}"><div class="ck-nhead"><b>@{e(x["nguoi"])}</b> {chip_loai(x["loai"])}'
            f' <span class="ck-sub">{e(LOAI_VI.get(x["loai"], ""))}</span></div>'
            + (f'<div class="ck-sub">Điểm: <span class="m28-pts">{e(diem)}</span></div>' if diem else "")
            + (f'<div class="ck-ntext">{e(x["ghi_chu"])}</div>' if x["ghi_chu"] else '<div class="ck-ntext ck-sub">(không ghi chú)</div>')
            + (f'<div class="ck-sub">Lúc rà chọn: {e(tri)}</div>' if tri else "") + "</div>")
    dec = ""
    if c["quyet_dinh"] or c["phu_trach"] or c["trang_thai"] != "mo":
        dec = (f'<div class="ck-decision"><b>{e(TT_ICON[c["trang_thai"]])}</b>'
               + (f'<div class="ck-dtext">{e(c["quyet_dinh"])}</div>' if c["quyet_dinh"] else "")
               + (f'<div class="ck-sub">Phụ trách: @{e(c["phu_trach"])}</div>' if c["phu_trach"] else "") + "</div>")
    return (f'<div class="ck-stage-in"><div class="ck-stage-img">{img}</div><div class="ck-stage-side">'
            f'<div class="ck-st-head"><span class="face-name">{e(c["anh"])}</span> <span class="ck-sub">lượt {e(c["luot"])}</span></div>'
            f'<div class="ck-notes">{"".join(notes)}</div>{dec}</div></div>')


# ---------- CSS và JS ----------
CSS = """
/* ---------- Ca khó và Họp team (màu lấy từ biến theme; màu trạng thái dùng nền trong suốt) ---------- */
#ck-row { gap: 10px; align-items: center; flex-wrap: nowrap; }
#ck-row > * { min-width: 0; }
#btn-cakho { flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; white-space: nowrap; padding: 0 16px !important;
  background: var(--background-fill-secondary) !important; color: var(--body-text-color) !important;
  border: 1px solid var(--border-color-primary) !important; }
#ck-badge, #ck-msg, #ck-m-msg, #ck-ngoai, #ck-sum, #ck-list, #hop-msg, #hop-report, #hop-counts, #ck-warn, #hop-warn, #hop-hint { padding: 0 !important; }
#btn-cakho { min-height: 40px; font-weight: 700; }
#ck-panel { background: var(--block-background-fill) !important; padding: 10px 12px !important; gap: 8px; border: 1px solid var(--border-color-primary); border-radius: 10px; }
#ck-panel-face { font-size: 15px; padding: 0 !important; }
#ck-loai .wrap { display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 5px; }
#ck-loai label { padding: 4px 8px; font-size: 13px; line-height: 1.2; min-height: 32px; align-items: center; }
#ck-loai label:has(input:checked), #ck-m-loai label:has(input:checked), #hop-tt label:has(input:checked) {
  background: color-mix(in srgb, #2563eb 16%, transparent) !important; border-color: #2563eb !important; color: var(--body-text-color) !important; }
#ck-m-loai .wrap { display: grid !important; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 5px; }
#ck-m-loai label { padding: 4px 8px; font-size: 13px; line-height: 1.2; min-height: 32px; align-items: center; }
#ck-btns, #ck-m-btns, #hop-btns, #hop-nav { gap: 8px; flex-wrap: wrap; }
#ck-btns button, #ck-m-btns button, #hop-btns button, #hop-nav button { min-width: 0 !important; flex: 1 1 110px !important; }
#ck-save, #ck-m-save, #hop-save, #hop-import, #ck-export, #hop-minutes { font-weight: 800; }
#ck-unmark.armed, #ck-m-del-ok { background: #dc2626 !important; border-color: #b91c1c !important; color: #fff !important; }
.m28-chip.ck-l-loi { --cc: #7c3aed; } .m28-chip.ck-l-gl { --cc: #2563eb; } .m28-chip.ck-l-cc { --cc: #0891b2; }
.ck-sub { font-size: 12.5px; color: var(--body-text-color-subdued); overflow-wrap: anywhere; }
.ck-noimg { display: flex; align-items: center; justify-content: center; text-align: center; width: 100%; height: 100%; min-height: 70px;
  font-size: 11.5px; color: var(--body-text-color-subdued); background: var(--background-fill-secondary); padding: 4px; }
.ck-mlist { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 10px; }
.ck-mcard { display: flex; gap: 10px; padding: 8px; border: 1px solid var(--border-color-primary); border-radius: 10px;
  background: var(--block-background-fill); min-width: 0; }
.ck-mimg { flex: 0 0 84px; width: 84px; height: 84px; border-radius: 8px; overflow: hidden; background: var(--background-fill-secondary); }
.ck-mimg img { width: 100%; height: 100%; object-fit: cover; display: block; }
.ck-mbody { display: flex; flex-direction: column; gap: 3px; min-width: 0; font-size: 13.5px; }
.ck-mnote { overflow-wrap: anywhere; font-size: 13px; }
#ck-ngoai-cb { padding: 0 !important; }
#hop-main { gap: 14px; align-items: flex-start; flex-wrap: wrap; }
#hop-left { gap: 8px; min-width: 0; }
#hop-right { gap: 10px; min-width: 0; }
@media (min-width: 1100px) { #hop-right { position: sticky; top: 8px; align-self: flex-start; } }
#hop-grid { max-height: 74vh !important; overflow-y: auto !important; padding: 4px !important; }
.ck-group h3 { margin: 8px 0 6px; font-size: 14px; font-weight: 800; }
.ck-n { display: inline-block; min-width: 22px; padding: 0 6px; margin-left: 4px; border-radius: 999px; font-size: 12px; text-align: center;
  background: var(--background-fill-secondary); border: 1px solid var(--border-color-primary); }
.ck-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(118px, 1fr)); gap: 8px; }
.ck-card { display: flex; flex-direction: column; gap: 3px; padding: 5px; text-align: left; cursor: pointer; min-width: 0;
  border: 2px solid var(--border-color-primary); border-radius: 10px; background: var(--block-background-fill); color: var(--body-text-color); }
.ck-card:hover { border-color: var(--body-text-color-subdued); }
.ck-card.sel { border-color: #2563eb; box-shadow: 0 0 0 2px color-mix(in srgb, #2563eb 35%, transparent); }
.ck-img { display: block; width: 100%; aspect-ratio: 1; border-radius: 6px; overflow: hidden; background: var(--background-fill-secondary); }
.ck-img img { width: 100%; height: 100%; object-fit: cover; display: block; }
.ck-meta { display: flex; align-items: center; justify-content: space-between; gap: 4px; }
.ck-meta .m28-chip { padding: 0 7px; font-size: 11px; line-height: 17px; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.ck-dot { display: inline-block; flex: 0 0 auto; width: 11px; height: 11px; border-radius: 50%; }
.ck-card .ck-sub { font-size: 11.5px; line-height: 1.25; }
.ck-counts { display: flex; flex-direction: column; gap: 4px; }
.ck-crow { display: flex; flex-wrap: wrap; gap: 5px; align-items: center; }
.ck-clab { flex: 0 0 74px; font-size: 12.5px; font-weight: 700; color: var(--body-text-color-subdued); }
#ck-stage { padding: 0 !important; }
.ck-stage-in { display: flex; flex-direction: column; gap: 10px; }
.ck-stage-img { border-radius: 10px; overflow: hidden; background: var(--background-fill-secondary); display: flex; justify-content: center; }
.ck-stage-img img { display: block; width: 100%; max-height: min(420px, 48vh); object-fit: contain; }
.ck-st-head .face-name { font-weight: 800; font-size: 17px; }
.ck-notes { display: flex; flex-direction: column; gap: 6px; }
.ck-note { padding: 7px 10px; border: 1px solid var(--border-color-primary); border-radius: 8px; background: var(--block-background-fill); }
.ck-note.cur { border-color: #2563eb; border-left-width: 5px; }
.ck-ntext, .ck-dtext { overflow-wrap: anywhere; white-space: pre-wrap; font-size: 14px; margin: 2px 0; }
.ck-decision { padding: 8px 10px; border-radius: 8px; border: 1px solid #16a34a; background: color-mix(in srgb, #16a34a 12%, transparent); }
.ck-report { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.ck-report th, .ck-report td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border-color-primary); vertical-align: top;
  overflow-wrap: anywhere; background: transparent; }
.ck-ok { color: #16a34a; font-weight: 800; } .ck-bad { color: #dc2626; font-weight: 800; } .ck-skip { color: #d97706; font-weight: 800; }
#hop-drop { min-height: 120px; border: 2px dashed var(--border-color-primary) !important; border-radius: 12px; }
#hop-drop [data-testid="upload-text"] { font-size: 0 !important; }
#hop-drop [data-testid="upload-text"] .or { display: none; }
#hop-drop [data-testid="upload-text"]::after { content: "Kéo thả các gói .zip vào đây\\A hoặc bấm để chọn"; white-space: pre; display: block;
  font-size: 17px; font-weight: 700; line-height: 1.5; text-align: center; color: var(--body-text-color); }
#hop-tt .wrap { display: flex; flex-wrap: wrap; gap: 6px; }
#hop-tt label { padding: 5px 10px; font-size: 13.5px; }
#hop-preview { max-height: 360px; overflow: auto; }
#tab-cakho, #tab-hop { padding: 8px 0 0 !important; gap: 10px; }
#tab-cakho { max-width: 1120px; margin: 0 auto; width: 100%; }
#hop-filters { gap: 8px; flex-wrap: wrap; }
#hop-filters > * { min-width: 130px !important; }
@media (max-width: 600px) {
  #ck-loai .wrap { grid-template-columns: 1fr; }
  #ck-m-loai .wrap { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .ck-mlist { grid-template-columns: 1fr; }
  .ck-cards { grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); }
  #ck-row { flex-wrap: wrap; }
}
/* Trình chiếu: chỉ #ck-stage toàn màn hình, chữ to */
body.ck-present { overflow: hidden !important; }
body.ck-present #ck-stage { position: fixed !important; inset: 0 !important; z-index: 100000 !important; margin: 0 !important; padding: 28px 36px !important;
  background: var(--background-fill-primary) !important; overflow: auto; width: auto !important; max-width: none !important; border: 0 !important; }
body.ck-present #ck-stage .ck-stage-in { flex-direction: row !important; gap: 32px; height: 100%; align-items: stretch; }
body.ck-present #hop-right, body.ck-present #hop-left, body.ck-present #hop-main, body.ck-present #tab-hop { position: static !important; transform: none !important; }
body.ck-present #ck-stage .ck-stage-img { flex: 1 1 56%; min-width: 0; background: transparent; align-items: center; }
body.ck-present #ck-stage .ck-stage-img img { width: 100% !important; max-height: none !important; height: calc(100vh - 72px) !important; object-fit: contain; }
body.ck-present #ck-stage .ck-stage-side { flex: 1 1 44%; min-width: 0; display: flex; flex-direction: column; gap: 14px; overflow: auto; }
body.ck-present #ck-stage .ck-st-head .face-name { font-size: 36px !important; }
body.ck-present #ck-stage .ck-ntext, body.ck-present #ck-stage .ck-dtext { font-size: 26px !important; line-height: 1.4 !important; }
body.ck-present #ck-stage .ck-sub { font-size: 18px !important; }
body.ck-present #ck-stage .ck-note .m28-chip { font-size: 18px !important; line-height: 30px !important; }
body.ck-present #ck-stage .ck-nhead b { font-size: 24px !important; }
body.ck-present #ck-stage .ck-decision b { font-size: 28px !important; }
body.ck-present #ck-present-hint { display: block; }
#ck-present-hint { display: none; position: fixed; right: 18px; bottom: 12px; z-index: 100001; font-size: 13px; color: var(--body-text-color-subdued); }
@media (max-width: 800px) { body.ck-present #ck-stage .ck-stage-in { flex-direction: column !important; } }
"""

MEETING_JS = r"""() => {
  if (window.__ckInit) { return; }
  window.__ckInit = true;
  const setVal = (el, v) => {
    const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v);
    el.dispatchEvent(new Event('input', { bubbles: true }));
  };
  document.addEventListener('click', (e) => {
    const card = e.target && e.target.closest ? e.target.closest('#hop-grid .ck-card') : null;
    if (!card) { return; }
    e.preventDefault();
    document.querySelectorAll('#hop-grid .ck-card.sel').forEach((c) => c.classList.remove('sel'));
    card.classList.add('sel');
    const box = document.querySelector('#hop-pick textarea, #hop-pick input');
    const go = document.getElementById('hop-pick-go');
    if (box && go) { setVal(box, card.getAttribute('data-key') || ''); setTimeout(() => go.click(), 40); }
  });
  const press = (id) => { const b = document.getElementById(id); if (b && !b.disabled) { b.click(); } };
  const present = (on) => {
    document.body.classList.toggle('ck-present', on);
    if (on) {
      try { const p = document.documentElement.requestFullscreen && document.documentElement.requestFullscreen(); if (p && p.catch) { p.catch(() => {}); } } catch (err) { /* headless hoặc bị chặn */ }
    } else {
      try { if (document.fullscreenElement) { const p = document.exitFullscreen(); if (p && p.catch) { p.catch(() => {}); } } } catch (err) { /* bỏ qua */ }
    }
  };
  window.__ckPresent = present;
  document.addEventListener('fullscreenchange', () => { if (!document.fullscreenElement && document.body.classList.contains('ck-present')) { present(false); } });
  document.addEventListener('keydown', (e) => {
    if (document.body.classList.contains('ck-present')) {         // chỉ trong trình chiếu
      if (e.key === 'Escape') { e.preventDefault(); present(false); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); press('hop-prev'); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); press('hop-next'); }
      return;
    }
    if (e.key === 'Escape' && e.target && e.target.closest && e.target.closest('#ck-panel')) { press('ck-cancel'); }   // thoát panel Ca khó
  });
}"""

FOCUS_NOTE_JS = "() => { setTimeout(() => { const t = document.querySelector('#ck-note textarea'); if (t) { t.focus(); } }, 150); }"
PRESENT_JS = "() => { if (window.__ckPresent) { window.__ckPresent(true); } }"


# ---------- giao diện Gradio ----------
def _loai_choices():
    return [(f"{c} — {t}", c) for c, t, _g in LOAI]


def _decision_of(store, name):
    with store.lock:
        d = store.lat.get(name, ("", ""))[0]
    return d if d in DECISIONS_OK else ""


def mark_panel(gr, demo, store, ctx, shown):
    """Nút "Ca khó (K)" và panel đánh dấu ở tab Rà soát. Không đụng triage, done.txt, hàng đợi hay hoàn tác."""
    points = load_point_names(ctx.project_root)
    opts = dict(show_progress="hidden", api_visibility="private", concurrency_limit=1, concurrency_id="cakho")
    opened = gr.State("")
    with gr.Row(elem_id="ck-row"):
        b_open = gr.Button("Ca khó (K)", elem_id="btn-cakho")
        badge = gr.HTML(elem_id="ck-badge", apply_default_css=False)
    with gr.Group(visible=False, elem_id="ck-panel") as panel:
        face_html = gr.HTML(elem_id="ck-panel-face", apply_default_css=False)
        loai = gr.Radio(choices=_loai_choices(), value=None, label="Loại ca khó", elem_id="ck-loai")
        diem = gr.Dropdown(choices=points, value=[], multiselect=True, allow_custom_value=not points, label="Điểm liên quan (không bắt buộc)",
                           elem_id="ck-diem")
        note = gr.Textbox(label=f"Ghi chú (tối đa {NOTE_MAX} ký tự)", lines=2, max_lines=4, max_length=NOTE_MAX, elem_id="ck-note")
        with gr.Row(elem_id="ck-btns"):
            b_save = gr.Button("Save", variant="primary", elem_id="ck-save")
            b_cancel = gr.Button("Cancel", elem_id="ck-cancel")
            b_unmark = gr.Button("Unmark", elem_id="ck-unmark", visible=False)
        msg = gr.HTML(elem_id="ck-msg", apply_default_css=False)
    armed = gr.State(False)

    def face_of(name):
        return store.by_name.get(name)

    def badge_for(name):
        f = face_of(name)
        if not f:
            return ""
        r = get_mark(store.run_dir, ctx.reviewer, f.file)
        return f'<span class="m28-chip c-gan_tay">Đã đánh dấu: {e(r["loai"])}</span>' if r else ""

    def hide(m="", level="info", name=""):
        return (gr.update(visible=False), badge_for(name), "", False, gr.update(value="Unmark", elem_classes=[]), msg_html(m, level))

    hide_outs = [panel, badge, opened, armed, b_unmark, msg]
    keep = gr.update()

    def on_open(sh):
        if ctx.closing:
            return hide(nap_anh.CLOSING_MSG, "info", sh) + (keep,) * 4
        if store.finished:
            gr.Info("Đã bấm Xong: không đánh dấu thêm ca khó mới ở lượt này được (xem/sửa/xuất ở tab Ca khó vẫn dùng được).")
            return hide("Đã bấm Xong: không đánh dấu thêm ca khó mới ở lượt này được (xem/sửa/xuất ở tab Ca khó vẫn dùng được).", "info", sh) + (keep,) * 4
        f = face_of(sh)
        if not sh or f is None:
            return hide("Chưa có mặt nào đang xem.", "warn", sh) + (keep,) * 4
        r = get_mark(store.run_dir, ctx.reviewer, f.file)
        vals = [x for x in (r["diem"].split(";") if r else []) if x]
        choices = list(dict.fromkeys(points + vals)) if points else vals
        return (gr.update(visible=True), badge_for(sh), sh, False, gr.update(visible=bool(r), value="Unmark", elem_classes=[]), "",
                f'<b>{e(f.file)}</b> · lượt {e(run_label(store.run_dir))}' + (' · <span class="ck-sub">đã đánh dấu, đang sửa</span>' if r else ""),
                gr.update(value=r["loai"] if r else None), gr.update(choices=choices, value=vals), gr.update(value=r["ghi_chu"] if r else ""))

    def on_save(sh, op, lo, dm, nt):
        if ctx.closing:
            return hide(nap_anh.CLOSING_MSG, "info", sh)
        if store.finished:
            gr.Info("Đã bấm Xong: không đánh dấu thêm ca khó mới ở lượt này được (xem/sửa/xuất ở tab Ca khó vẫn dùng được).")
            return hide("Đã bấm Xong: không đánh dấu thêm ca khó mới ở lượt này được (xem/sửa/xuất ở tab Ca khó vẫn dùng được).", "info", sh)
        if not op or sh != op:
            return hide("Ảnh đã đổi, mở lại Ca khó.", "warn", sh)
        f = face_of(op)
        if f is None:
            return hide("Mặt này không còn trong hàng đợi.", "warn", sh)
        if not lo:
            return (keep, badge_for(op), op, False, keep, msg_html("Chọn loại ca khó trước khi lưu.", "warn"))
        try:
            row, created = upsert_mark(store.run_dir, ctx.reviewer, f.file, lo, dm or [], nt, _decision_of(store, op), known_points=points or None,
                                       runs_root=ctx.runs_root)
        except RunError as ex:
            gr.Warning(str(ex), title="Chưa lưu được")
            return (keep, badge_for(op), op, False, keep, msg_html(str(ex), "warn"))
        return hide(f"Đã {'đánh dấu' if created else 'sửa'} ca khó {f.file}: {row['loai']}.", "ok", op)

    def on_cancel(sh):
        return hide("", "info", sh)

    def on_unmark(sh, op, arm):
        if ctx.closing:
            return hide(nap_anh.CLOSING_MSG, "info", sh)
        if store.finished:
            gr.Info("Đã bấm Xong: không đánh dấu thêm ca khó mới ở lượt này được (xem/sửa/xuất ở tab Ca khó vẫn dùng được).")
            return hide("Đã bấm Xong: không đánh dấu thêm ca khó mới ở lượt này được (xem/sửa/xuất ở tab Ca khó vẫn dùng được).", "info", sh)
        if not op or sh != op:
            return hide("Ảnh đã đổi, mở lại Ca khó.", "warn", sh)
        if not arm:
            return (keep, badge_for(op), op, True, gr.update(value="Click again to unmark", elem_classes=["armed"]), "")
        f = face_of(op)
        try:
            ok = delete_mark(store.run_dir, ctx.reviewer, f.file, runs_root=ctx.runs_root) if f else False
        except RunError as ex:
            gr.Warning(str(ex), title="Chưa bỏ được")
            return (keep, badge_for(op), op, False, gr.update(value="Unmark", elem_classes=[]), msg_html(str(ex), "warn"))
        return hide(f"Đã bỏ đánh dấu {f.file}." if ok else "Mặt này chưa có đánh dấu.", "ok" if ok else "info", op)

    def on_shown(sh, op):
        """Mặt đang xem đổi: cập nhật nhãn; panel đang mở cho mặt khác thì đóng."""
        if op and sh != op:
            return (gr.update(visible=False), badge_for(sh), "", False)
        return (keep, badge_for(sh), keep, keep)

    open_outs = hide_outs + [face_html, loai, diem, note]
    b_open.click(on_open, [shown], open_outs, **opts).then(None, None, None, js=FOCUS_NOTE_JS)
    b_save.click(on_save, [shown, opened, loai, diem, note], hide_outs, **opts)
    b_cancel.click(on_cancel, [shown], hide_outs, **opts)
    b_unmark.click(on_unmark, [shown, opened, armed], hide_outs, **opts)
    shown.change(on_shown, [shown, opened], [panel, badge, opened, armed], **opts)


def member_tab(gr, demo, store, ctx):
    """Tab "Ca khó" của thành viên: xem/sửa/xoá ca của mình, xuất gói họp. Trả (hàm làm mới, inputs, outputs, opts) để build_ui nối vào tab.select."""
    points = load_point_names(ctx.project_root)
    opts = dict(show_progress="hidden", api_visibility="private", concurrency_limit=1, concurrency_id="cakho")
    thumb_dir = os.path.join(ctx.tmp_dir, "ca_kho")
    gr.HTML(warn_html(), elem_id="ck-warn", apply_default_css=False)
    with gr.Row():
        run_dd = gr.Dropdown(choices=[("Tất cả lượt", "")], value="", label="Lọc theo lượt", elem_id="ck-run", scale=3)
        b_refresh = gr.Button("Refresh", elem_id="ck-refresh", scale=1, min_width=120)
    note_html = gr.HTML(elem_id="ck-m-msg", apply_default_css=False)
    list_view = gr.HTML(elem_id="ck-list", apply_default_css=False)
    pick = gr.Dropdown(choices=[], value=None, label="Chọn ca để sửa hoặc xoá (lượt/ảnh)", elem_id="ck-pick-member", filterable=True)
    with gr.Group(visible=False, elem_id="ck-edit") as edit:
        m_loai = gr.Radio(choices=_loai_choices(), value=None, label="Loại ca khó", elem_id="ck-m-loai")
        m_diem = gr.Dropdown(choices=points, value=[], multiselect=True, allow_custom_value=not points, label="Điểm liên quan", elem_id="ck-m-diem")
        m_note = gr.Textbox(label=f"Ghi chú (tối đa {NOTE_MAX} ký tự)", lines=2, max_lines=4, max_length=NOTE_MAX, elem_id="ck-m-note")
        with gr.Row(elem_id="ck-m-btns"):
            m_save = gr.Button("Save", variant="primary", elem_id="ck-m-save")
            m_del = gr.Button("Delete", variant="stop", elem_id="ck-m-del")
            m_ok = gr.Button("Confirm delete", elem_id="ck-m-del-ok", visible=False)
            m_no = gr.Button("Cancel", elem_id="ck-m-del-no", visible=False)
    gr.Markdown("### Xuất gói họp")
    kem = gr.Checkbox(value=True, label="Kèm ảnh chồng (lượt YawDD/DrivFace)", elem_id="ck-kem-anh")
    ngoai_box = gr.HTML(elem_id="ck-ngoai", apply_default_css=False)
    kem_ngoai = gr.Checkbox(value=False, label="Kèm cả ảnh của lượt không rõ nguồn", elem_id="ck-kem-ngoai")
    b_export = gr.Button("Export meeting pack", variant="primary", elem_id="ck-export")
    summary = gr.HTML(elem_id="ck-sum", apply_default_css=False)
    download = gr.DownloadButton("Download pack", visible=False, elem_id="ck-download")

    def sources(luots):
        return {l: run_source(os.path.join(ctx.runs_root, l), ctx.project_root) for l in luots}

    def snapshot(luot):
        rows, warns = member_rows(ctx.runs_root, ctx.reviewer, luot or None)
        allr, _w = member_rows(ctx.runs_root, ctx.reviewer)
        counts = {}
        for r in allr:
            counts[r["luot"]] = counts.get(r["luot"], 0) + 1
        src = sources(sorted(counts))
        return rows, warns, counts, src

    def render(luot="", sel=None, msg=""):
        rows, warns, counts, src = snapshot(luot)
        if luot and luot not in counts:
            luot = ""
            rows, warns, counts, src = snapshot("")
        thumbs = {(r["luot"], r["anh"]): small_thumb(os.path.join(ctx.runs_root, r["luot"]), r["anh"], thumb_dir) for r in rows}
        choices = [("Tất cả lượt", "")] + [(f"{l} · {NGUON_VI[src[l]]} · {counts[l]} ca", l) for l in sorted(counts)]
        pick_choices = [(f"{r['luot']}/{r['anh']} · {r['loai']}", f"{r['luot']}/{r['anh']}") for r in rows]
        keep = sel if sel in [v for _l, v in pick_choices] else None
        sel_luots = [luot] if luot else sorted(counts)
        unk = [l for l in sel_luots if src.get(l) == "khong_ro"]
        text = msg_html(msg) + "".join(msg_html(w, "warn") for w in warns)
        return (gr.update(choices=choices, value=luot), text, list_html(rows, thumbs, src), gr.update(choices=pick_choices, value=keep),
                ngoai_html(unk), gr.update(visible=bool(keep)))

    ref_outs = [run_dd, note_html, list_view, pick, ngoai_box, edit]

    def on_refresh(luot):
        return render(luot or "")

    def split_pick(v):
        if not v or "/" not in v:
            return None, None
        luot, anh = v.split("/", 1)
        return (luot, anh) if RUN_RE.fullmatch(luot) and ANH_RE.fullmatch(anh) else (None, None)

    def on_pick(v, luot):
        l, a = split_pick(v)
        r = get_mark(os.path.join(ctx.runs_root, l), ctx.reviewer, a) if l else None
        if not r:
            return (gr.update(visible=False), gr.update(), gr.update(), gr.update(), gr.update(visible=True), gr.update(visible=False),
                    gr.update(visible=False))
        vals = [x for x in r["diem"].split(";") if x]
        return (gr.update(visible=True), gr.update(value=r["loai"]), gr.update(choices=list(dict.fromkeys(points + vals)) if points else vals, value=vals),
                gr.update(value=r["ghi_chu"]), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False))

    pick_outs = [edit, m_loai, m_diem, m_note, m_del, m_ok, m_no]

    def on_save(v, luot, lo, dm, nt):
        if ctx.closing:
            return render(luot or "", v, nap_anh.CLOSING_MSG)
        l, a = split_pick(v)
        if not l:
            return render(luot or "", None, "Chọn một ca trước.")
        r = get_mark(os.path.join(ctx.runs_root, l), ctx.reviewer, a)
        if not r:
            return render(luot or "", None, "Ca này không còn nữa.")
        try:
            upsert_mark(os.path.join(ctx.runs_root, l), ctx.reviewer, a, lo, dm or [], nt, r["quyet_dinh_ra"], known_points=points or None,
                        runs_root=ctx.runs_root)
        except RunError as ex:
            gr.Warning(str(ex), title="Chưa lưu được")
            return render(luot or "", v, str(ex))
        return render(luot or "", v, f"Đã lưu ca {l}/{a}.")

    def on_del(v):
        return gr.update(visible=False), gr.update(visible=True), gr.update(visible=True)

    def on_del_no():
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)

    def on_del_ok(v, luot):
        l, a = split_pick(v)
        msg = "Chọn một ca trước."
        if ctx.closing:
            msg = nap_anh.CLOSING_MSG
        elif l:
            try:
                msg = f"Đã xoá ca {l}/{a}." if delete_mark(os.path.join(ctx.runs_root, l), ctx.reviewer, a, runs_root=ctx.runs_root) else "Ca này không còn nữa."
            except RunError as ex:
                gr.Warning(str(ex), title="Chưa xoá được")
                msg = str(ex)
        return render(luot or "", None, msg) + (gr.update(visible=True), gr.update(visible=False), gr.update(visible=False))

    def on_export(luot, kem_anh, kem_n):
        if ctx.closing:
            return msg_html(nap_anh.CLOSING_MSG, "warn"), gr.update(visible=False)
        try:
            info = build_package(ctx.runs_root, ctx.project_root, ctx.reviewer, [luot] if luot else None, bool(kem_anh), bool(kem_n))
        except RunError as ex:
            gr.Warning(str(ex), title="Chưa xuất được")
            return msg_html(str(ex), "warn"), gr.update(visible=False)
        return package_summary_html(info), gr.update(value=info["path"], visible=True)

    run_dd.input(on_refresh, [run_dd], ref_outs, **opts)
    b_refresh.click(on_refresh, [run_dd], ref_outs, **opts)
    pick.input(on_pick, [pick, run_dd], pick_outs, **opts)
    m_save.click(on_save, [pick, run_dd, m_loai, m_diem, m_note], ref_outs, **opts)
    m_del.click(on_del, [pick], [m_del, m_ok, m_no], **opts)
    m_no.click(on_del_no, None, [m_del, m_ok, m_no], **opts)
    m_ok.click(on_del_ok, [pick, run_dd], ref_outs + [m_del, m_ok, m_no], **opts)
    b_export.click(on_export, [run_dd, kem, kem_ngoai], [summary, download], **opts)
    demo.load(on_refresh, [run_dd], ref_outs, **opts)
    return on_refresh, [run_dd], ref_outs, opts


def meeting_tab(gr, demo, ctx):
    """Tab "Họp team": nhập gói, họp trên lưới ảnh, lưu phiên, trình chiếu, xuất biên bản."""
    opts = dict(show_progress="hidden", api_visibility="private", concurrency_limit=1, concurrency_id="hop")
    registry = {}
    state = {}

    def serve():
        return serve_dir(ctx.project_root)

    def get_meeting(name):
        if not name or name == NEW_SESSION:
            return None
        m = registry.get(name)
        if m is None:
            m = registry[name] = Meeting.load(serve(), name)
        return m

    def session_choices():
        return [("➕ Tạo phiên mới hôm nay", NEW_SESSION)] + [(n, n) for n in Meeting.list_sessions(serve())]

    gr.HTML(warn_html(), elem_id="hop-warn", apply_default_css=False)
    with gr.Row():
        sess = gr.Dropdown(choices=session_choices(), value=None, label="Phiên họp", elem_id="hop-session", scale=3)
        b_new = gr.Button("New session today", elem_id="hop-new", scale=1, min_width=170)
    msg = gr.HTML(elem_id="hop-msg", apply_default_css=False)
    drop = gr.File(label="Gói họp (.zip)", file_count="multiple", file_types=[".zip"], type="filepath", elem_id="hop-drop", height=150)
    b_import = gr.Button("Import packs", variant="primary", elem_id="hop-import")
    report = gr.HTML(elem_id="hop-report", apply_default_css=False)
    counts = gr.HTML(elem_id="hop-counts", apply_default_css=False)
    with gr.Row(elem_id="hop-filters"):
        f_loai = gr.Dropdown(choices=[("Tất cả loại", "")], value="", label="Loại", elem_id="hop-f-loai")
        f_nguoi = gr.Dropdown(choices=[("Tất cả người", "")], value="", label="Người", elem_id="hop-f-nguoi")
        f_tt = gr.Dropdown(choices=[("Tất cả trạng thái", "")] + [(t, c) for c, t, _i in TRANG_THAI], value="", label="Trạng thái", elem_id="hop-f-tt")
        f_q = gr.Textbox(label="Tìm trong ghi chú", max_lines=1, elem_id="hop-q")
        f_group = gr.Radio(choices=[(t, c) for c, t in GROUPS], value="loai", label="Nhóm theo", elem_id="hop-group")
    with gr.Row(elem_id="hop-main", equal_height=False):
        with gr.Column(scale=5, min_width=360, elem_id="hop-left"):
            grid = gr.HTML(elem_id="hop-grid", apply_default_css=False)
        with gr.Column(scale=4, min_width=360, elem_id="hop-right"):
            stage = gr.HTML(elem_id="ck-stage", apply_default_css=False)
            gr.HTML('<div id="ck-present-hint">← → đổi ca · Esc thoát</div>', apply_default_css=False)
            with gr.Row(elem_id="hop-nav"):
                b_prev = gr.Button("← Previous case", elem_id="hop-prev")
                b_next = gr.Button("Next case →", elem_id="hop-next")
                b_present = gr.Button("Present", elem_id="hop-present")
            with gr.Group(elem_id="hop-form"):
                tt = gr.Radio(choices=[(t, c) for c, t, _i in TRANG_THAI], value="mo", label="Trạng thái", elem_id="hop-tt")
                qd = gr.Textbox(label=f"Quyết định (tối đa {QD_MAX} ký tự)", lines=2, max_lines=4, max_length=QD_MAX, elem_id="hop-qd")
                pt = gr.Dropdown(choices=["", "P1", "P2", "P3", "P4", "P5"], value="", allow_custom_value=True, label="Người phụ trách",
                                 elem_id="hop-pt")
                bl = gr.Dropdown(choices=BACKLOG_LOAI, value=BACKLOG_LOAI[0], label="Loại backlog", elem_id="hop-bl")
                gb = gr.Checkbox(value=True, label="Ghi vào backlog", elem_id="hop-gb")
                mg = gr.Textbox(label="Mục guideline (§)", max_lines=1, max_length=40, elem_id="hop-mg")
                with gr.Row(elem_id="hop-btns"):
                    b_save = gr.Button("Save", variant="primary", elem_id="hop-save")
                    b_save_next = gr.Button("Save & next", elem_id="hop-save-next")
            form_msg = gr.HTML(elem_id="hop-form-msg", apply_default_css=False)
    b_min = gr.Button("Export minutes", variant="primary", elem_id="hop-minutes")
    min_msg = gr.HTML(elem_id="hop-min-msg", apply_default_css=False)
    with gr.Row():
        f_md = gr.File(label="Biên bản (.md)", interactive=False, visible=False, elem_id="hop-file-md")
        f_csv = gr.File(label="Tổng hợp (.csv)", interactive=False, visible=False, elem_id="hop-file-csv")
    preview = gr.Code(language="markdown", label="Xem trước biên bản", interactive=False, visible=False, elem_id="hop-preview")
    pick = gr.Textbox(visible="hidden", elem_id="hop-pick")
    pick_go = gr.Button(visible="hidden", elem_id="hop-pick-go")
    key_state = gr.State("")

    filters = [sess, key_state, f_loai, f_nguoi, f_tt, f_q, f_group]
    form_outs = [tt, qd, pt, bl, gb, mg]
    view_outs = [sess, counts, f_loai, f_nguoi, grid, stage, key_state, b_prev, b_next] + form_outs + [form_msg, msg]

    def view(name, key, loai, nguoi, ttf, q, group, m=None, msg_text="", level="info", sess_update=None, fill_form=True, target="top"):
        """Tuple cập nhật đúng thứ tự view_outs. target: thông báo hiện ở #hop-msg (top, đầu tab) hay #hop-form-msg (form, dưới form)."""
        try:
            mt = get_meeting(name)
        except RunError as ex:
            mt, msg_text, level = None, str(ex), "warn"
        sv = serve()
        text = msg_html(msg_text, level)
        tail = (text, gr.update()) if target == "form" else (gr.update(), text)
        if mt is None:
            empty = gr.update()
            return (sess_update or gr.update(), "", gr.update(choices=[("Tất cả loại", "")], value=""),
                    gr.update(choices=[("Tất cả người", "")], value=""), grid_html(None, [], sv), stage_html(None, "", sv), "",
                    gr.update(interactive=False), gr.update(interactive=False)) + (empty,) * 6 + tail
        loai_c = [("Tất cả loại", "")] + [(f"{c} — {LOAI_VI[c]}", c) for c in LOAI_CODES if c in mt.counts()["loai"]]
        nguoi_c = [("Tất cả người", "")] + [(n, n) for n in mt.nguoi_list()]
        loai = loai if loai in dict((v, l) for l, v in loai_c) else ""
        nguoi = nguoi if nguoi in dict((v, l) for l, v in nguoi_c) else ""
        keys = mt.filtered(loai, nguoi, ttf, q)
        if key not in mt.cases:
            key = ""
        pos = keys.index(key) if key in keys else None
        c = mt.cases.get(key)
        form = ((gr.update(value=c["trang_thai"]), gr.update(value=c["quyet_dinh"]), gr.update(value=c["phu_trach"]),
                 gr.update(value=c["loai_backlog"]), gr.update(value=c["ghi_backlog"]), gr.update(value=c["muc_guideline"]))
                if (c and fill_form) else (gr.update(),) * 6)
        return (sess_update or gr.update(), counts_html(mt), gr.update(choices=loai_c, value=loai), gr.update(choices=nguoi_c, value=nguoi),
                grid_html(mt, keys, sv, key, group), stage_html(mt, key, sv), key,
                gr.update(interactive=bool(keys) and (pos is None or pos > 0)),
                gr.update(interactive=bool(keys) and (pos is None or pos < len(keys) - 1))) + form + tail

    def on_sess(name, key, loai, nguoi, ttf, q, group):
        if name == NEW_SESSION:
            return on_new(key, loai, nguoi, ttf, q, group)
        return view(name, "", loai, nguoi, ttf, q, group or "loai", fill_form=False)

    def on_new(key, loai, nguoi, ttf, q, group):
        try:
            m = Meeting.create(serve(), ctx.reviewer)
        except (RunError, OSError) as ex:
            gr.Warning(str(ex), title="Chưa tạo được phiên")
            return view(None, "", loai, nguoi, ttf, q, group or "loai", msg_text=f"Không tạo được phiên mới: {ex}", level="warn")
        registry[m.name] = m
        up = gr.update(choices=session_choices(), value=m.name)
        return view(m.name, "", loai, nguoi, ttf, q, group or "loai", msg_text=f"Đã tạo phiên {m.name}. Kéo thả các gói .zip vào ô bên dưới rồi bấm Import packs.",
                    level="ok", sess_update=up, fill_form=False)

    def on_import(files, name, key, loai, nguoi, ttf, q, group):
        paths = [f if isinstance(f, str) else getattr(f, "name", str(f)) for f in (files or [])]
        if not paths:
            return (gr.update(), "") + view(name, key, loai, nguoi, ttf, q, group, msg_text="Chưa chọn gói nào.", level="warn")
        note = ""
        up = None
        try:
            m = get_meeting(name)
        except RunError as ex:
            return (gr.update(), "") + view(None, "", "", "", "", "", group, msg_text=str(ex), level="warn")
        if m is None:
            try:
                m = Meeting.create(serve(), ctx.reviewer)
            except (RunError, OSError) as ex:
                return (gr.update(), "") + view(None, "", "", "", "", "", group, msg_text=f"Không tạo được phiên: {ex}", level="warn")
            registry[m.name] = m
            name, note = m.name, f"Chưa chọn phiên nên đã tạo {m.name}. "
            up = gr.update(choices=session_choices(), value=m.name)
        rep = m.import_packages([(p, os.path.basename(p)) for p in paths])
        ok, bad = sum(1 for r in rep if r["trang_thai"] == "ok"), sum(1 for r in rep if r["trang_thai"] == "loi")
        text = note + f"Nhập xong {len(rep)} gói: {ok} được nhập, {bad} lỗi, {len(rep) - ok - bad} đã nhập từ trước."
        lv = "warn" if bad else "ok"
        return (gr.update(value=None), report_html(rep)) + view(name, key, loai, nguoi, ttf, q, group, msg_text=text, level=lv, sess_update=up,
                                                                 fill_form=False)

    def on_filter(name, key, loai, nguoi, ttf, q, group):
        return view(name, key, loai, nguoi, ttf, q, group, fill_form=False)

    def on_pick(k, name, key, loai, nguoi, ttf, q, group):
        return view(name, k, loai, nguoi, ttf, q, group, target="form")

    def step(delta):
        def h(name, key, loai, nguoi, ttf, q, group):
            try:
                m = get_meeting(name)
            except RunError:
                m = None
            if m is None:
                return view(name, key, loai, nguoi, ttf, q, group, target="form")
            keys = m.filtered(loai, nguoi, ttf, q)
            if not keys:
                return view(name, key, loai, nguoi, ttf, q, group, target="form")
            if key in keys:
                i = min(max(keys.index(key) + delta, 0), len(keys) - 1)
            else:
                i = 0 if delta > 0 else len(keys) - 1
            return view(name, keys[i], loai, nguoi, ttf, q, group, target="form")
        return h

    def save(go_next):
        def h(name, key, loai, nguoi, ttf, q, group, v_tt, v_qd, v_pt, v_bl, v_gb, v_mg):
            try:
                m = get_meeting(name)
            except RunError as ex:
                return view(None, "", "", "", "", "", group, msg_text=str(ex), level="warn")
            if m is None or key not in m.cases:
                return view(name, key, loai, nguoi, ttf, q, group, msg_text="Chọn một ca ở lưới trước.", level="warn", target="form")
            keys = m.filtered(loai, nguoi, ttf, q)
            nxt = None
            if go_next and key in keys:
                i = keys.index(key)
                nxt = keys[i + 1] if i + 1 < len(keys) else None
            try:
                warns = m.set_fields(key, v_tt, v_qd, v_pt, v_bl, v_gb, v_mg)
            except (RunError, OSError) as ex:
                gr.Warning(str(ex), title="Chưa lưu được")
                return view(name, key, loai, nguoi, ttf, q, group, msg_text=str(ex), level="warn", fill_form=False, target="form")
            if warns:
                gr.Warning(warns[0], title="Lưu rồi, nhưng lưu ý")
            text = "Đã lưu. " + " ".join(warns)
            if go_next and nxt is None:
                text += " Đây là ca cuối danh sách đã lọc."
            return view(name, nxt or key, loai, nguoi, ttf, q, group, msg_text=text.strip(), level="warn" if warns else "ok", target="form")
        return h

    def on_minutes(name):
        try:
            m = get_meeting(name)
        except RunError as ex:
            return msg_html(str(ex), "warn"), gr.update(), gr.update(), gr.update()
        if m is None or not m.cases:
            return msg_html("Chưa có ca nào để lập biên bản: chọn phiên và nhập gói trước.", "warn"), gr.update(), gr.update(), gr.update()
        pb, qdp = find_repo_docs()
        try:
            res = write_minutes(m, pb, qdp)
        except RunError as ex:
            gr.Warning(str(ex), title="Chưa xuất được")
            return msg_html(str(ex), "warn"), gr.update(), gr.update(), gr.update()
        text = (f"Đã xuất biên bản: {res['n_p']} mục P (từ P-{res['p_first']:03d}), {res['n_qd']} mục QĐ (từ QĐ-{res['qd_first']:03d}). "
                "Tự chép các khối vào problem-backlog.md và so-quyet-dinh.md rồi commit hai file đó.")
        if not (pb and qdp):
            text += " Không thấy hai file trong repo trên máy này: đánh số từ 001, kiểm lại trước khi dán."
        text += "".join(" " + w for w in res["warnings"])
        return (msg_html(text, "warn" if (res["warnings"] or not (pb and qdp)) else "ok"), gr.update(value=res["md_path"], visible=True),
                gr.update(value=res["csv_path"], visible=True), gr.update(value=res["md"], visible=True))

    def on_load(group):
        names = Meeting.list_sessions(serve())
        return view(names[0] if names else None, "", "", "", "", "", group or "loai",
                    sess_update=gr.update(choices=session_choices(), value=names[0] if names else None), fill_form=False)

    demo.load(None, None, None, js=MEETING_JS)
    demo.load(on_load, [f_group], view_outs, **opts)
    sess.input(on_sess, filters, view_outs, **opts)
    b_new.click(on_new, filters[1:], view_outs, **opts)
    b_import.click(on_import, [drop] + filters, [drop, report] + view_outs, **opts)
    for c in (f_loai, f_nguoi, f_tt, f_group):                 # always_last: bấm liền tay thì lần cuối cùng luôn được xử lý
        c.input(on_filter, filters, view_outs, trigger_mode="always_last", **opts)
    f_q.change(on_filter, filters, view_outs, trigger_mode="always_last", **opts)        # .change (không phải .input): xoá hết chữ cũng chạy
    pick_go.click(on_pick, [pick] + filters, view_outs, trigger_mode="always_last", **opts)     # JS ghi data-key vào #hop-pick rồi bấm nút ẩn
    b_prev.click(step(-1), filters, view_outs, trigger_mode="multiple", **opts)
    b_next.click(step(1), filters, view_outs, trigger_mode="multiple", **opts)
    fields = [tt, qd, pt, bl, gb, mg]
    b_save.click(save(False), filters + fields, view_outs, **opts)
    b_save_next.click(save(True), filters + fields, view_outs, **opts)
    b_present.click(None, None, None, js=PRESENT_JS)
    b_min.click(on_minutes, [sess], [min_msg, f_md, f_csv, preview], **opts)
    return None
