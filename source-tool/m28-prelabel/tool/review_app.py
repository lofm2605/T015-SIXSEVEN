"""Trang rà soát nhãn nháp M28 (Gradio, chỉ chạy ở 127.0.0.1) — phần của P2.

Người rà xem nháp 50 điểm trên ảnh chồng và bấm Nhận / Gán tay / Bỏ ảnh TRƯỚC khi nhập vào CVAT.
Sửa điểm không làm ở đây (làm trong CVAT).

    python tool\\review_app.py runs\\F5 P2            # chạy thẳng, từ thư mục source-tool\\m28-prelabel
    python tool\\m28.py review --run F5 --reviewer P2  # qua m28 (bước review --review ui)

Đọc  runs/<run>/flags/flags.json, overlays/, autoqc/autoqc.csv, no_face.csv, map50/mp50.json, crop/images/.
Ghi  runs/<run>/review/triage_<người rà>.csv (name,decision,reason,seconds; chỉ nối thêm dòng, mỗi dòng fsync)
     và runs/<run>/review/done.txt khi bấm Xong (m28 chỉ cần file này có mặt).

Quy ước:
  * Đầu module không nạp gradio, cũng không bao giờ nạp torch: phần logic thuần (hàng đợi, đọc/ghi CSV, hoàn tác,
    ảnh chồng, ảnh nhỏ) chỉ dùng thư viện chuẩn và PIL (nạp lười), test không cần trình duyệt.
  * Chỉ launch(server_name="127.0.0.1", share=False). Không tunnel, không Colab/Kaggle, không gọi mạng.
  * Đóng ngang chừng không mất gì: mỗi lần bấm là một dòng CSV đã fsync; mở lại thì làm tiếp.
"""
import csv
import dataclasses
import datetime
import html
import io
import json
import os
import re
import sys
import threading
import time

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)
from m28core.steps import DECISIONS, _stem  # noqa: E402  (dùng chung quy ước tên/quyết định với push)

# ---------- hằng số (P5 chốt guideline_triage.md thì sửa ở đây) ----------
REASONS = [
    ("", "(không)"),
    ("LAT_GUONG", "lật gương"),
    ("DON_CUC", "điểm dồn cục"),
    ("LECH_VUNG", "lệch cả một vùng"),
    ("QUAY_CHE", "quay > 80° hoặc che quá nửa"),
    ("NHIEU_MAT", "ảnh nhiều mặt cần gán"),
    ("KHONG_MAT", "không có mặt"),
    ("SAI_MAT", "sai mặt"),
    ("MO_NHO", "quá mờ hoặc quá nhỏ"),
]
REASON_CODES = [c for c, _ in REASONS]
LABELS = {"nhan": "Nhận", "gan_tay": "Gán tay", "bo": "Bỏ ảnh"}
SUG_VI = {"on": "ổn", "can_xem": "cần xem", "nen_gan_tay": "nên gán tay", "": "chưa có autoqc"}
PROBLEMS_VI = {"diem_ngoai_anh": "điểm ra ngoài ảnh", "diem_khong_hop_le": "điểm không hợp lệ"}
NO_FACE_VI = {"khong_thay_mat": "MediaPipe không thấy mặt", "khong_doc_duoc_anh": "không đọc được ảnh"}
EMPTY_VI = {"tat_ca": "Không có mặt nào trong lượt này.", "chua_ra": "Đã rà hết: không còn mặt chưa rà. Bấm Xong ở cột bên phải.",
            "dang_ngo": "Không có mặt đáng ngờ nào.", "da_ra": "Chưa rà mặt nào."}
DEFAULT_PORT = 7860
PAGE_SIZE = 24
FILTERS = [("tat_ca", "Tất cả"), ("chua_ra", "Chưa rà"), ("dang_ngo", "Đáng ngờ"), ("da_ra", "Đã rà")]
HEADER = ["name", "decision", "reason", "seconds"]

THUMB = 176          # cạnh ảnh nhỏ gồm cả viền (px)
BORDER = 6           # bề dày viền trạng thái vẽ thẳng vào ảnh nhỏ
STATUS_COLOR = {"": "#9ca3af", "nhan": "#16a34a", "gan_tay": "#d97706", "bo": "#dc2626"}
STATUS_LETTER = {"": "", "nhan": "N", "gan_tay": "G", "bo": "B"}
RED, GREEN = (255, 0, 0), (0, 200, 0)     # như steps.overlays (BGR 0,0,255 và 0,200,0), ở đây là RGB
NOTEBOOK_VARS = ("COLAB_RELEASE_TAG", "COLAB_GPU", "KAGGLE_KERNEL_RUN_TYPE", "SPACE_ID")
VI_USAGE = "Cách dùng: python tool\\review_app.py <thư mục lượt chạy> <người rà>, ví dụ python tool\\review_app.py runs\\R1610 P5"


class RunError(Exception):
    """Lỗi người dùng sửa được (thiếu file, sai tên...). Thông điệp tiếng Việt, nói rõ cách sửa."""


# ---------- kiểm tra đầu vào ----------
def run_name(run_dir):
    return os.path.basename(os.path.normpath(run_dir)) or str(run_dir)


def _shown(path):
    return os.path.normpath(path)


def check_reviewer(name):
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", name):
        raise RunError(f"Tên người rà {name!r} không hợp lệ: chỉ dùng chữ không dấu, số, gạch dưới, gạch ngang "
                       "(tối đa 32 ký tự), ví dụ P2. Tên này nằm trong tên file triage_<tên>.csv.")
    return name


def notebook_env(environ=None, modules=None):
    """Thông điệp lỗi nếu đang chạy trong Colab/Kaggle/Spaces, không thì None."""
    environ = os.environ if environ is None else environ
    modules = sys.modules if modules is None else modules
    if "google.colab" in modules or any(v in environ for v in NOTEBOOK_VARS):
        return ("Trang rà soát chỉ chạy trên máy của bạn (127.0.0.1), không chạy trong Colab/Kaggle/Spaces vì trên "
                "trang có ảnh mặt. Dùng --review excel nếu không mở được trang.")
    return None


# ---------- đọc dữ liệu của lượt chạy ----------
@dataclasses.dataclass
class Face:
    name: str                        # không đuôi, ví dụ F_004
    file: str                        # name + ".png": tên ghi vào CSV
    overlay: object = None           # đường dẫn overlays/<tên>.png nếu có
    crop: object = None              # đường dẫn crop/images/<tên>.png nếu có
    flags: object = None             # list[bool] 50 phần tử, None = không có nháp
    n_flags: int = 0
    suggestion: str = ""             # on | can_xem | nen_gan_tay | "" (chưa có autoqc)
    problems: list = dataclasses.field(default_factory=list)
    no_face_reason: object = None    # có = MediaPipe không thấy mặt, không có nháp

    @property
    def has_draft(self):
        return self.flags is not None

    @property
    def rank(self):
        return 0 if (self.suggestion == "nen_gan_tay" or not self.has_draft) else 1 if self.suggestion == "can_xem" else 2

    @property
    def suspicious(self):
        return self.suggestion in ("can_xem", "nen_gan_tay") or self.n_flags > 0 or not self.has_draft


def _jload(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _text(path):
    with open(path, encoding="utf-8-sig", newline="") as f:          # utf-8-sig: file Excel có BOM
        return f.read()


def _delim(text):
    first = text.splitlines()[0] if text.strip() else ""
    return ";" if first.count(";") > first.count(",") else ","


def _dict_rows(path):
    """CSV có tiêu đề -> list dict (khoá thường, bỏ khoảng trắng). Không có file hoặc hỏng thì []."""
    if not os.path.exists(path):
        return []
    try:
        text = _text(path)
        rows = csv.DictReader(io.StringIO(text), delimiter=_delim(text))
        return [{(k or "").strip().lower(): (v or "") for k, v in r.items() if k is not None} for r in rows]
    except (OSError, ValueError, csv.Error):
        return []


def _read_autoqc(run_dir):
    out = {}
    for r in _dict_rows(os.path.join(run_dir, "autoqc", "autoqc.csv")):
        n = _stem(r.get("name", ""))
        if n:
            sug = r.get("suggestion", "").strip()
            out[n] = (sug if sug in ("on", "can_xem", "nen_gan_tay") else "",
                      [p.strip() for p in r.get("problems", "").split(";") if p.strip()])
    return out


def _read_no_face(run_dir):
    """{tên: (lý do, bước)}; mỗi tên một dòng, đọc từ cuối lên như steps._no_face."""
    rows = _dict_rows(os.path.join(run_dir, "no_face.csv"))
    out = {}
    for r in reversed(rows):
        n = _stem(r.get("name", ""))
        if n:
            out[n] = (r.get("reason", "").strip(), r.get("step", "").strip())
    return out


def _load(run_dir):
    """(hàng đợi, ghi chú). Xem load_queue."""
    run = run_name(run_dir)
    if not os.path.isdir(run_dir):
        raise RunError(f"Không thấy thư mục lượt chạy {_shown(run_dir)} (đang đứng ở {os.getcwd()}). "
                       "Chạy lệnh từ thư mục source-tool\\m28-prelabel hoặc kiểm tên --run.")
    fpath = os.path.join(run_dir, "flags", "flags.json")
    if not os.path.isfile(fpath):
        raise RunError(f"Thiếu {_shown(fpath)}: chạy python tool\\m28.py prepare --run {run} ... trước.")
    try:
        fl = _jload(fpath)
    except (OSError, ValueError) as e:
        raise RunError(f"Không đọc được {_shown(fpath)} ({e}): chạy lại python tool\\m28.py prepare --run {run} ... "
                       "--force flags.")
    if not isinstance(fl, dict) or any(not isinstance(v, list) for v in fl.values()):
        raise RunError(f"{_shown(fpath)} sai định dạng (cần {{tên mặt: [cờ low_conf của 50 điểm]}}): chạy lại "
                       f"python tool\\m28.py prepare --run {run} ... --force flags.")
    qc, nf = _read_autoqc(run_dir), _read_no_face(run_dir)

    def path_of(sub, name):
        p = os.path.join(run_dir, sub, name + ".png")
        return p if os.path.isfile(p) else None

    faces = []
    for name, v in fl.items():
        fl_b = [bool(x) for x in v]
        sug, probs = qc.get(name, ("", []))
        faces.append(Face(name, name + ".png", path_of("overlays", name), path_of(os.path.join("crop", "images"), name),
                          fl_b, sum(fl_b), sug, probs, None))
    unusable = 0
    for name, (why, _step) in nf.items():
        if name in fl:
            continue
        crop = path_of(os.path.join("crop", "images"), name)
        if crop is None:
            unusable += 1                      # không có ảnh cắt: không rà được, push tự xếp vào Bỏ
            continue
        faces.append(Face(name, name + ".png", None, crop, None, 0, "", [], why or "khong_thay_mat"))
    faces.sort(key=lambda f: (f.rank, -f.n_flags, f.name))
    if not faces:
        raise RunError(f"Hàng đợi rỗng: {_shown(fpath)} không có mặt nào"
                       + (f" và {unusable} mặt trong no_face.csv không có ảnh cắt" if unusable else "")
                       + f". Kiểm lại bước prepare của lượt {run}.")
    notes = []
    if unusable:
        notes.append(f"{unusable} mặt không dùng được ở bước crop (no_face.csv), push tự xếp vào Bỏ.")
    return faces, notes


def load_queue(run_dir):
    """Hàng đợi rà: mọi mặt trong flags.json, cộng mặt no_face còn ảnh cắt (không có nháp, chỉ Gán tay hoặc Bỏ).
    Thứ tự (rank, -số cờ, tên): nen_gan_tay/no_face, rồi can_xem, rồi còn lại (trùng steps._queue)."""
    return _load(run_dir)[0]


# ---------- đọc/ghi triage CSV ----------
def _parse(text):
    """Giống hệt steps.read_triage: (dấu phân cách, tiêu đề|None, (name, decision, reason, seconds), các dòng dữ liệu)."""
    delim = _delim(text)
    rows = [r for r in csv.reader(io.StringIO(text), delimiter=delim) if any(c.strip() for c in r)]
    ci, di, ri, si, header = 0, 1, 2, 3, None
    if rows and "decision" in [c.strip().lower() for c in rows[0]]:
        header = [c.strip().lower() for c in rows.pop(0)]
        ci = header.index("name") if "name" in header else 0
        di = header.index("decision")
        ri = header.index("reason") if "reason" in header else -1
        si = header.index("seconds") if "seconds" in header else -1
    return delim, header, (ci, di, ri, si), rows


def read_rows(path):
    """Các dòng của triage CSV theo thứ tự trong file: dict(name, decision, reason, seconds). Không có file thì []."""
    if not os.path.exists(path):
        return []
    _d, _h, (ci, di, ri, si), rows = _parse(_text(path))
    out = []
    for r in rows:
        if r[0].strip().lower() == "name":
            continue
        get = lambda i: r[i].strip() if 0 <= i < len(r) else ""      # noqa: E731
        out.append(dict(name=_stem(get(ci)), decision=get(di).lower(), reason=get(ri), seconds=get(si)))
    return out


def latest(rows):
    """{tên: (decision, reason)}, dòng sau đè dòng trước. decision không thuộc DECISIONS (kể cả rỗng) = chưa rà."""
    return {r["name"]: (r["decision"], r["reason"]) for r in rows}


def _fmt_seconds(s):
    if s is None or s == "":
        return ""
    return s if isinstance(s, str) else f"{float(s):.1f}"


def append_row(path, file, decision, reason="", seconds=""):
    """Nối một dòng vào triage CSV rồi fsync. File mới/rỗng: ghi tiêu đề trước. File đã có: dùng lại dấu phân cách
    và tiêu đề của nó (tiêu đề 7 cột kiểu autoqc thì ghi 7 cột, mỗi giá trị đúng cột; không tiêu đề thì theo vị trí).
    PermissionError (Windows khoá file khi Excel đang mở) cứ để bay lên cho UI báo."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    delim, eol, header, idx = ",", "\r\n", None, (0, 1, 2, 3)
    text = _text(path) if os.path.exists(path) else ""
    if text.strip():
        delim, header, idx, _rows = _parse(text)
        eol = "\r\n" if "\r\n" in text else "\n" if "\n" in text else "\r\n"
    vals = (file, decision, reason, _fmt_seconds(seconds))
    out = io.StringIO()
    w = csv.writer(out, delimiter=delim, lineterminator=eol)
    if header is None and not text.strip():
        w.writerow(HEADER)
        w.writerow(vals)
    elif header is None:                                  # có dữ liệu nhưng không có tiêu đề: theo vị trí
        w.writerow(vals)
    else:
        row = [""] * max([len(header)] + [i + 1 for i in idx])
        for i, v in zip(idx, vals):
            if i >= 0:
                row[i] = v
        w.writerow(row)
    pre = eol if text and not text.endswith(("\n", "\r")) else ""      # file thiếu xuống dòng cuối: thêm trước khi nối
    with open(path, "a", encoding="utf-8", newline="") as f:
        f.write(pre + out.getvalue())
        f.flush()
        os.fsync(f.fileno())


# ---------- hàng đợi, tiến độ, lọc, phân trang ----------
def _status(lat, name):
    d = lat.get(name, ("", ""))[0]
    return d if d in DECISIONS else ""


def next_pending(queue, lat, start_name=None):
    """Mặt chưa rà kế tiếp SAU start_name theo thứ tự hàng đợi, đi vòng lại đầu. start_name=None: tìm từ đầu."""
    n = len(queue)
    names = [f.name for f in queue]
    i0 = names.index(start_name) if start_name in names else -1
    for k in range(1, n + 1):
        name = names[(i0 + k) % n]
        if not _status(lat, name):
            return name
    return None


def progress(queue, lat):
    c = {"nhan": 0, "gan_tay": 0, "bo": 0}
    for f in queue:
        s = _status(lat, f.name)
        if s:
            c[s] += 1
    done = sum(c.values())
    return dict(total=len(queue), done=done, nhan=c["nhan"], gan_tay=c["gan_tay"], bo=c["bo"],
                remaining=len(queue) - done)


def filter_faces(queue, lat, mode):
    """mode: tat_ca | chua_ra | dang_ngo | da_ra."""
    if mode == "chua_ra":
        return [f for f in queue if not _status(lat, f.name)]
    if mode == "da_ra":
        return [f for f in queue if _status(lat, f.name)]
    if mode == "dang_ngo":
        return [f for f in queue if f.suspicious]
    return list(queue)


def _nm(x):
    return x if isinstance(x, str) else x.name


def page_of(items, name, size=PAGE_SIZE):
    """Chỉ số trang (từ 0) chứa mặt `name` trong danh sách; không thấy thì 0."""
    for i, x in enumerate(items):
        if _nm(x) == name:
            return i // size
    return 0


def page_slice(items, page, size=PAGE_SIZE):
    """(các phần tử của trang, trang đã kẹp vào [0, n_pages-1], n_pages). Danh sách rỗng: 1 trang."""
    n_pages = max(1, -(-len(items) // size))
    page = min(max(int(page), 0), n_pages - 1)
    return list(items[page * size:(page + 1) * size]), page, n_pages


def seconds_since(t_prev, t_now):
    """Số giây giữa hai lần bấm, làm tròn 1 chữ số, không âm. Chưa có mốc trước thì None (ghi ô trống)."""
    if t_prev is None or t_now is None:
        return None
    return round(max(0.0, float(t_now) - float(t_prev)), 1)


def fmt_points(flags):
    """Số điểm có cờ (đánh số từ 1 như trên ảnh chồng), gộp dãy liền nhau từ 3 điểm: '1–26, 28, 32–36'."""
    nums = [i + 1 for i, f in enumerate(flags or []) if f]
    parts, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        if j - i >= 2:
            parts.append(f"{nums[i]}–{nums[j]}")
        else:
            parts += [str(x) for x in nums[i:j + 1]]
        i = j + 1
    return ", ".join(parts)


# ---------- trạng thái phía server ----------
class Store:
    """Hàng đợi + triage CSV + ngăn hoàn tác của một lượt rà. Bọc bằng khoá: handler Gradio chạy ở nhiều luồng."""

    def __init__(self, run_dir, reviewer, clock=time.monotonic):
        check_reviewer(reviewer)
        self.run_dir, self.reviewer, self.clock = run_dir, reviewer, clock
        self.lock = threading.RLock()
        self.faces, self.notes = _load(run_dir)
        self.by_name = {f.name: f for f in self.faces}
        self.path = os.path.join(run_dir, "review", f"triage_{reviewer}.csv")
        self.done_path = os.path.join(run_dir, "review", "done.txt")
        self.had_done = os.path.exists(self.done_path)
        try:
            self.rows = read_rows(self.path)
        except UnicodeDecodeError:
            raise RunError(f"{_shown(self.path)} không phải UTF-8: mở bằng Excel rồi lưu lại dạng 'CSV UTF-8', "
                           "hoặc đổi tên file cũ đi để rà lại từ đầu.")
        except OSError as e:
            raise RunError(f"Không đọc được {_shown(self.path)} ({e}). Đóng Excel nếu đang mở file này rồi chạy lại.")
        self.lat = latest(self.rows)
        self.resumed = self.progress()["done"]          # số mặt đã rà từ lần chạy trước
        self.undo_stack = []
        self.finished = False            # đã bấm Xong thật: mọi tab từ chối ghi thêm trong 2 giây trang còn mở

    def status(self, name):
        return _status(self.lat, name)

    def _reopen(self):
        """Có thay đổi sau khi đã bấm Xong (mở lại lượt cũ): done.txt cũ hết đúng, xoá để phải bấm Xong lại."""
        try:
            if os.path.exists(self.done_path):
                os.remove(self.done_path)
        except OSError:
            pass

    def progress(self):
        return progress(self.faces, self.lat)

    def decide(self, name, decision, reason="", seconds=None):
        """Ghi một quyết định (CSV rồi bộ nhớ) và đẩy trạng thái cũ vào ngăn hoàn tác."""
        face = self.by_name.get(name)
        if face is None:
            raise ValueError(f"Không có mặt {name!r} trong hàng đợi.")
        if decision not in DECISIONS:
            raise ValueError(f"Quyết định {decision!r} không hợp lệ (nhan, gan_tay, bo).")
        if reason not in REASON_CODES:
            raise ValueError(f"Mã lý do {reason!r} không có trong danh sách lý do.")
        if decision == "nhan" and not face.has_draft:
            raise ValueError(f"{face.file} không có nháp (MediaPipe không thấy mặt): chỉ chọn được Gán tay hoặc Bỏ ảnh.")
        if decision == "nhan":
            reason = ""
        with self.lock:
            old = self.lat.get(name, ("", ""))
            old = old if old[0] in DECISIONS else ("", "")
            append_row(self.path, face.file, decision, reason, seconds)       # lỗi ghi thì chưa đổi gì trong bộ nhớ
            self.rows.append(dict(name=name, decision=decision, reason=reason, seconds=_fmt_seconds(seconds)))
            self.lat[name] = (decision, reason)
            self.undo_stack.append((name, old[0], old[1]))
            self._reopen()

    def undo(self):
        """Hoàn tác lần bấm gần nhất: ghi một dòng trả mặt về trạng thái trước (seconds trống). Trả tên mặt hoặc None."""
        with self.lock:
            if not self.undo_stack:
                return None
            name, dec, why = self.undo_stack[-1]
            append_row(self.path, self.by_name[name].file, dec, why, "")
            self.undo_stack.pop()
            self.rows.append(dict(name=name, decision=dec, reason=why, seconds=""))
            self.lat[name] = (dec, why)
            self._reopen()
            return name

    def can_finish(self):
        with self.lock:
            return self.progress()["remaining"] == 0

    def write_done(self):
        """Ghi review/done.txt nguyên tử (file tạm rồi os.replace). Còn mặt chưa rà thì từ chối."""
        with self.lock:
            left = self.progress()["remaining"]
            if left:
                raise ValueError(f"Còn {left} mặt chưa rà, chưa bấm Xong được.")
            os.makedirs(os.path.dirname(self.done_path), exist_ok=True)
            tmp = self.done_path + f".tmp{os.getpid()}"
            when = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                f.write(f"xong\t{self.reviewer}\t{when}\t{len(self.faces)} mặt")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.done_path)
            return self.done_path


# ---------- ảnh chồng và ảnh nhỏ (PIL nạp lười) ----------
_FONTS = {}


def _font(size, bold=False):
    from PIL import ImageFont
    key = (size, bold)
    if key not in _FONTS:
        names = (["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else
                 ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"])
        font = None
        for n in names:
            try:
                font = ImageFont.truetype(n, size)
                break
            except OSError:
                continue
        if font is None:
            try:
                font = ImageFont.load_default(size=size)
            except TypeError:
                font = ImageFont.load_default()
        _FONTS[key] = font
    return _FONTS[key]


def _text_at(draw, xy, text, fill, font, anchor):
    try:
        draw.text(xy, text, fill=fill, font=font, anchor=anchor)
    except ValueError:                                    # phông bitmap cũ không hỗ trợ anchor
        draw.text(xy, text, fill=fill, font=font)


def _save(img, path, fmt, **kw):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + f".tmp{os.getpid()}"
    img.save(tmp, format=fmt, **kw)
    os.replace(tmp, path)


def _tmp(run_dir, *parts):
    return os.path.join(run_dir, "_tmp", *parts)


def _safe(name):
    return re.sub(r"[^\w.-]", "_", name)


_MP50 = {}          # đường dẫn -> (mtime, dữ liệu): mp50.json của lượt 616 mặt vài MB, chỉ nạp một lần


def _mp50(run_dir):
    p = os.path.join(run_dir, "map50", "mp50.json")
    try:
        m = os.path.getmtime(p)
    except OSError:
        return None
    if p not in _MP50 or _MP50[p][0] != m:
        try:
            _MP50[p] = (m, _jload(p))
        except (OSError, ValueError):
            return None
    return _MP50[p][1]


def _redraw_overlay(face, run_dir, pts):
    """Vẽ lại ảnh chồng như steps.overlays: chấm bán kính 3 (đỏ = low_conf, xanh = ổn) và số thứ tự i+1."""
    from PIL import Image, ImageDraw
    out = _tmp(run_dir, "overlays", face.name + ".png")
    src_m = max(os.path.getmtime(face.crop), os.path.getmtime(os.path.join(run_dir, "map50", "mp50.json")))
    if os.path.exists(out) and os.path.getmtime(out) >= src_m:
        return out
    img = Image.open(face.crop).convert("RGB")
    d = ImageDraw.Draw(img)
    font = _font(10)
    for i, (x, y) in enumerate(pts):
        col = RED if face.flags[i] else GREEN
        cx, cy = int(round(x)), int(round(y))
        d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=col)
        _text_at(d, (int(x) + 4, int(y) - 3), str(i + 1), col, font, "ls")
    _save(img, out, "PNG")
    return out


_IMG_OK = {}        # đường dẫn -> ((mtime_ns, size), đọc được không)


def _img_ok(path):
    """Ảnh mở và giải mã được (ảnh chồng bị cắt dở sau một lần prepare bị ngắt thì không). Có cache theo mtime/size."""
    try:
        st = os.stat(path)
    except OSError:
        return False
    key = (st.st_mtime_ns, st.st_size)
    c = _IMG_OK.get(path)
    if c and c[0] == key:
        return c[1]
    try:
        from PIL import Image
    except ImportError:
        return True
    try:
        with Image.open(path) as im:
            im.load()
        ok = True
    except Exception:                                   # OSError, SyntaxError, ValueError, ảnh quá lớn...
        ok = False
    _IMG_OK[path] = (key, ok)
    return ok


def _placeholder(run_dir):
    from PIL import Image, ImageDraw
    out = _tmp(run_dir, "overlays", "_khong_co_anh.png")
    if not os.path.exists(out):
        img = Image.new("RGB", (512, 512), (214, 214, 214))
        _text_at(ImageDraw.Draw(img), (256, 256), "Không có ảnh chồng", (70, 70, 70), _font(30, True), "mm")
        _save(img, out, "PNG")
    return out


def overlay_for(face, run_dir):
    """(đường dẫn ảnh lớn, cảnh báo|None).
    Có overlays/<tên>.png đọc được thì dùng; thiếu hoặc hỏng mà có ảnh cắt và mp50.json thì vẽ lại vào runs/<run>/_tmp/overlays/
    (không đụng file gốc); mặt không có nháp (no_face) dùng ảnh cắt; thiếu cả hai thì ảnh xám 512 kèm cảnh báo."""
    bad = False
    if face.overlay and os.path.isfile(face.overlay):
        if _img_ok(face.overlay):
            return face.overlay, None
        bad = True
    crop_ok = bool(face.crop and os.path.isfile(face.crop) and _img_ok(face.crop))
    if not face.has_draft:
        if crop_ok:
            return face.crop, None
        return _placeholder(run_dir), f"Thiếu hoặc hỏng ảnh cắt của {face.file} (crop/images): không xem được mặt này."
    if crop_ok:
        mp = _mp50(run_dir)
        orig = (mp or {}).get(face.name, {}).get("orig")
        if orig and len(list(orig.values())) == len(face.flags):
            try:
                what = "hỏng" if bad else "thiếu"
                return (_redraw_overlay(face, run_dir, list(orig.values())),
                        f"Ảnh chồng overlays/{face.file} {what}: trang vẽ lại tạm từ ảnh cắt và mp50.json "
                        f"(chạy lại prepare --force overlays để sửa hẳn)." if bad else
                        f"Thiếu overlays/{face.file}: ảnh chồng này do trang vẽ lại tạm từ ảnh cắt và mp50.json.")
            except (OSError, ValueError, KeyError):
                pass
    head = f"Ảnh chồng overlays/{face.file} hỏng" if bad else f"Thiếu ảnh chồng overlays/{face.file}"
    return (_placeholder(run_dir),
            f"{head} và không vẽ lại được (thiếu ảnh cắt hoặc map50/mp50.json). "
            "Không xem được nháp: đừng chọn Nhận, chạy lại python tool\\m28.py prepare ... --force overlays.")


def _build_thumb(src, out, status):
    from PIL import Image, ImageDraw, ImageOps
    im = Image.open(src).convert("RGB")
    im.thumbnail((THUMB - 2 * BORDER, THUMB - 2 * BORDER), Image.Resampling.LANCZOS)
    im = ImageOps.expand(im, border=BORDER, fill=STATUS_COLOR[status])
    if STATUS_LETTER[status]:
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 25, 25], fill=STATUS_COLOR[status])
        _text_at(d, (13, 13), STATUS_LETTER[status], "white", _font(18, True), "mm")
    _save(im, out, "JPEG", quality=85)


def thumb_for(face, status, run_dir):
    """Ảnh nhỏ JPEG ~176 px (chất lượng 85) có viền 6 px theo trạng thái vẽ thẳng vào ảnh và nhãn N/G/B ở góc.
    Tên file chứa trạng thái nên URL đổi theo, trình duyệt không giữ ảnh cũ. Tạo lười, có cache theo mtime.
    Một ảnh hỏng không làm sập cả trang: rơi về ảnh xám 'Không có ảnh chồng'."""
    status = status if status in DECISIONS else ""
    src, _warn = overlay_for(face, run_dir)
    out = _tmp(run_dir, "thumbs", f"{_safe(face.name)}__{status or 'chua'}.jpg")
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
        return out
    try:
        _build_thumb(src, out, status)
    except (OSError, SyntaxError, ValueError):
        _build_thumb(_placeholder(run_dir), out, status)
    return out


# ---------- phiên làm việc của một tab trình duyệt (dict thuần, để trong gr.State) ----------
def new_session(store):
    cur = next_pending(store.faces, store.lat, None) or store.faces[0].name
    ses = dict(cur=cur, mode="tat_ca", page=0, names=[], t=store.clock(), finished=False)
    _follow(store, ses)
    return ses


def ensure_session(store, ses):
    if not isinstance(ses, dict) or ses.get("cur") not in store.by_name:
        return new_session(store)
    return ses


def _filtered(store, ses):
    return filter_faces(store.faces, store.lat, ses["mode"])


def _follow(store, ses):
    """Đưa trang của lưới tới trang có mặt đang xem (nếu mặt đó nằm trong danh sách đã lọc)."""
    items = _filtered(store, ses)
    if any(f.name == ses["cur"] for f in items):
        ses["page"] = page_of(items, ses["cur"], PAGE_SIZE)


def act_select(store, ses, index):
    names = ses.get("names", [])
    if isinstance(index, int) and 0 <= index < len(names):
        ses["cur"] = names[index]
    return "", "info"


def act_filter(store, ses, mode):
    """Đổi bộ lọc. Mặt đang xem không nằm trong danh sách mới thì chuyển sang mặt chưa rà đầu tiên của danh sách
    (không có mặt chưa rà thì mặt đầu); danh sách rỗng thì giữ mặt cũ nhưng khoá N/G/B (xem make_view)."""
    ses["mode"] = mode if mode in dict(FILTERS) else "tat_ca"
    items = _filtered(store, ses)
    if items and not any(f.name == ses["cur"] for f in items):
        ses["cur"] = next_pending(items, store.lat, None) or items[0].name
    ses["page"] = page_of(items, ses["cur"], PAGE_SIZE) if any(f.name == ses["cur"] for f in items) else 0
    return "", "info"


def act_page(store, ses, delta):
    ses["page"] = ses.get("page", 0) + delta
    return "", "info"


def act_step(store, ses, delta):
    """← / →: đi trong danh sách đã lọc, không bỏ qua mặt đã rà."""
    items = _filtered(store, ses)
    if not items:
        return "Danh sách đang lọc trống.", "info"
    names = [f.name for f in items]
    if ses["cur"] in names:
        i = names.index(ses["cur"]) + delta
    else:
        i = 0 if delta > 0 else len(names) - 1
    ses["cur"] = names[min(max(i, 0), len(names) - 1)]
    _follow(store, ses)
    return "", "info"


STALE_MSG = "Bỏ qua một lần bấm vì ảnh chưa kịp đổi. Nhìn ảnh rồi bấm lại."
CLOSED_MSG = "Đã bấm Xong, trang sắp tắt: không ghi thêm được."


def act_decide(store, ses, decision, reason, shown):
    """Bấm Nhận / Gán tay / Bỏ ảnh cho mặt `shown` (mặt người rà đang nhìn thấy khi bấm). Trả (thông báo, mức, đặt lại lý do).
    Nếu `shown` khác mặt hiện hành của server (bấm quá nhanh khi trang chưa kịp đổi ảnh) thì bỏ qua, không ghi gì.
    Bấm đúng quyết định (và lý do) mặt đó đang có thì không ghi thêm dòng nào."""
    if store.finished:
        return CLOSED_MSG, "info", False
    if shown != ses["cur"]:
        return STALE_MSG, "info", False
    name = ses["cur"]
    before = _filtered(store, ses)
    if not any(f.name == name for f in before):
        return "Mặt đang xem không nằm trong bộ lọc này: chọn một ảnh trong lưới trước.", "info", False
    if decision in DECISIONS and store.status(name) == decision:
        cur_reason = store.lat[name][1]
        if decision == "nhan" or (reason or "") == cur_reason:
            return f"{name}.png đã là {LABELS[decision]}" + (f" ({cur_reason})" if cur_reason else "") + " rồi, không ghi thêm.", "info", False
    now = store.clock()
    try:
        store.decide(name, decision, reason, seconds_since(ses.get("t"), now))
    except ValueError as e:
        return str(e), "warn", False
    except OSError as e:
        return (f"Không ghi được {_shown(store.path)}. Nếu đang mở bằng Excel thì đóng Excel rồi bấm lại. ({type(e).__name__})",
                "warn", False)
    ses["t"] = now
    why = store.lat[name][1]
    msg = f"Đã ghi {name}.png: {LABELS[decision]}" + (f" ({why})" if why else "") + "."
    if decision != "nhan" and not why:
        msg += " Chưa có lý do: bấm Hoàn tác (Z), chọn lý do (0–8) rồi bấm lại nếu muốn ghi lý do."
    nxt = next_pending(before, store.lat, name)                  # trước hết trong danh sách đang lọc
    if nxt is None:
        nxt = next_pending(store.faces, store.lat, name)
        if nxt is not None and not any(f.name == nxt for f in _filtered(store, ses)):
            ses["mode"] = "chua_ra"
            msg += " Bộ lọc hiện tại hết mặt chưa rà, chuyển sang 'Chưa rà'."
    if nxt:
        ses["cur"] = nxt
    else:
        msg += " Đã rà hết, bấm Xong."
        if not any(f.name == name for f in _filtered(store, ses)):
            ses["mode"] = "tat_ca"                                # bộ lọc 'Chưa rà' trống thì quay về Tất cả
    _follow(store, ses)
    return msg, "ok", True


def act_undo(store, ses, shown):
    if store.finished:
        return CLOSED_MSG, "info", False
    if shown != ses["cur"]:
        return STALE_MSG, "info", False
    try:
        name = store.undo()
    except OSError as e:
        return (f"Không ghi được {_shown(store.path)}. Nếu đang mở bằng Excel thì đóng Excel rồi bấm lại. ({type(e).__name__})",
                "warn", False)
    if name is None:
        return "Chưa có gì để hoàn tác.", "info", False
    ses["cur"] = name
    ses["t"] = store.clock()
    if not any(f.name == name for f in _filtered(store, ses)):
        ses["mode"] = "tat_ca"                                    # mặt vừa hoàn tác rời bộ lọc đang chọn
    _follow(store, ses)
    return f"Đã hoàn tác {name}.png: về trạng thái trước đó.", "ok", True


def act_finish(store, ses):
    """Trả (thông báo, mức, đã xong thật). Xong thật thì UI tự tắt trang sau 2 giây."""
    if store.finished:
        return CLOSED_MSG, "info", False
    try:
        path = store.write_done()
    except ValueError as e:
        return str(e), "warn", False
    except OSError as e:
        return f"Không ghi được {_shown(store.done_path)} ({e}).", "warn", False
    ses["finished"] = True
    store.finished = True
    return (f"Đã ghi {_shown(path)}. Trang tự tắt sau 2 giây, quay lại cửa sổ cmd."), "ok", True


# ---------- mô hình hiển thị (thuần, test không cần gradio) ----------
def caption(face, status):
    base = face.name
    if not face.has_draft:
        base += " · không có nháp"
    else:
        base += f" · {face.n_flags} cờ · {SUG_VI[face.suggestion]}"
    return base + (f" · {LABELS[status]}" if status else "")


def _chip(status, extra=""):
    cls = status or "chua"
    txt = LABELS.get(status, "Chưa rà") + (f" · {extra}" if extra else "")
    return f'<span class="m28-chip c-{cls}">{html.escape(txt)}</span>'


def notes_html(store):
    """Ghi chú cố định của phiên (không đổi khi đang rà): làm tiếp từ lần trước, mặt không dùng được ở bước crop."""
    notes = []
    if store.resumed:
        notes.append(f"Làm tiếp từ {os.path.basename(store.path)}: đã có {store.resumed} mặt rà từ lần trước.")
    notes += store.notes
    return "".join(f'<div class="m28-note">{html.escape(n)}</div>' for n in notes)


def header_html(store, ses):
    p = store.progress()
    pct = round(100 * p["done"] / p["total"]) if p["total"] else 0
    chips = "".join(f'<span class="m28-chip c-{k}">{html.escape(t)} <b>{p[k]}</b></span>' for k, t in
                    (("nhan", "Nhận"), ("gan_tay", "Gán tay"), ("bo", "Bỏ")))
    chips += f'<span class="m28-chip c-chua">Còn lại <b>{p["remaining"]}</b></span>'
    again = ('<span class="m28-chip c-gan_tay">Lượt này đã bấm Xong trước đó</span>'
             if store.had_done and not (ses.get("finished") or store.finished) else "")
    done = ('<div class="m28-done" role="alert"><div class="m28-done-box"><b>Đã ghi xong.</b>'
            '<span>Đóng tab này và quay lại cửa sổ cmd. Trang đã tắt, bấm gì cũng không còn tác dụng.</span></div></div>'
            if (ses.get("finished") or store.finished) else "")
    return (f'<div class="m28-head"><div class="m28-top"><div class="m28-title">Rà soát nhãn nháp M28</div>'
            f'<div class="m28-sub">lượt <b>{html.escape(run_name(store.run_dir))}</b> · người rà '
            f'<b>{html.escape(store.reviewer)}</b></div>{again}</div>'
            f'<div class="m28-prog"><span class="m28-count">Đã rà {p["done"]}/{p["total"]}</span>'
            f'<div class="m28-bar" role="progressbar" aria-valuenow="{p["done"]}" aria-valuemax="{p["total"]}">'
            f'<i style="width:{pct}%"></i></div><div class="m28-chips">{chips}</div></div></div>{done}')


def info_html(store, face, status, warn):
    lat = store.lat.get(face.name, ("", ""))
    pos = [f.name for f in store.faces].index(face.name) + 1
    rows = [("Tên file", f'<span class="face-name">{html.escape(face.file)}</span>'),
            ("Vị trí", f"{pos}/{len(store.faces)} trong hàng đợi"),
            ("Trạng thái", _chip(status, lat[1] if status else ""))]
    if face.has_draft:
        pts = fmt_points(face.flags)
        rows.append(("Điểm nghi sai", f"<b>{face.n_flags}/{len(face.flags)}</b>"
                     + (f' · điểm <span class="m28-pts">{html.escape(pts)}</span>' if pts else " · không có điểm nào")))
        rows.append(("Gợi ý của máy", html.escape(SUG_VI[face.suggestion])))
        probs = ", ".join(PROBLEMS_VI.get(p, p) for p in face.problems)
        rows.append(("Vấn đề", html.escape(probs) if probs else "không"))
    else:
        why = NO_FACE_VI.get(face.no_face_reason, face.no_face_reason)
        rows.append(("Không có nháp", html.escape(f"{why} ({face.no_face_reason})")))
    body = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
    warns = ""
    if not face.has_draft:
        warns += '<div class="m28-warn">Mặt này không có nháp: chỉ chọn Gán tay hoặc Bỏ ảnh (nút Nhận đã khoá).</div>'
    if warn:
        warns += f'<div class="m28-warn">{html.escape(warn)}</div>'
    return f'<table class="m28-info">{body}</table>{warns}'


def _msg_html(msg, level):
    if not msg:
        return ""
    return f'<div class="m28-msg m-{level}" role="status">{html.escape(msg)}</div>'


def make_view(store, ses, msg="", level="info"):
    """Mọi thứ UI cần vẽ, tính từ (store, ses). Cập nhật ses["page"] (kẹp) và ses["names"] (tên trên trang)."""
    items = _filtered(store, ses)
    page_items, page, n_pages = page_slice(items, ses["page"], PAGE_SIZE)
    ses["page"], ses["names"] = page, [f.name for f in page_items]
    face = store.by_name[ses["cur"]]
    status = store.status(face.name)
    big, warn = overlay_for(face, store.run_dir)
    p = store.progress()
    counts = {m: len(filter_faces(store.faces, store.lat, m)) for m, _ in FILTERS}
    cur_i = ses["names"].index(face.name) if face.name in ses["names"] else None
    names_all = [f.name for f in items]
    pos = names_all.index(face.name) if face.name in names_all else None
    fin = bool(ses.get("finished") or store.finished)
    incl = pos is not None                       # mặt đang xem nằm trong danh sách đã lọc (N/G/B chỉ bật khi đúng)
    return dict(
        header=header_html(store, ses),
        filter_choices=[(f"{t} ({counts[m]})", m) for m, t in FILTERS], filter_value=ses["mode"],
        gallery=[(thumb_for(f, store.status(f.name), store.run_dir), caption(f, store.status(f.name)))
                 for f in page_items],
        selected=cur_i,
        page_html=(f'<div class="m28-page">Trang <b>{page + 1}</b>/{n_pages}</div>' if items else
                   f'<div class="m28-empty">{html.escape(EMPTY_VI.get(ses["mode"], EMPTY_VI["tat_ca"]))}</div>'),
        page_prev=page > 0 and not fin, page_next=page < n_pages - 1 and not fin,
        big=big, info=info_html(store, face, status, warn),
        nhan_ok=face.has_draft and not fin and incl, tay_ok=not fin and incl, bo_ok=not fin and incl,
        undo_ok=bool(store.undo_stack) and not fin,
        prev_ok=bool(items) and not fin and (pos is None or pos > 0),
        next_ok=bool(items) and not fin and (pos is None or pos < len(items) - 1),
        xong_label="Xong" if p["remaining"] == 0 else f"Xong (còn {p['remaining']} mặt chưa rà)",
        xong_ok=p["remaining"] == 0 and not fin,
        shown=face.name, msg=_msg_html(msg, level))


# ---------- giao diện Gradio ----------
GUIDE_HTML = ('<div class="m28-guide"><b>Nhận</b>: đúng dáng mặt, chỉ cần kéo nhẹ · <b>Gán tay</b>: lật gương, dồn cục, '
              'lệch cả vùng, quay/che nhiều, nhiều mặt · <b>Bỏ</b>: không mặt, sai mặt, mờ/nhỏ · '
              '<b>Phân vân Nhận/Gán tay → chọn Nhận</b></div>')
KEYS_HTML = ('<div class="m28-keys"><b>Chỉ mở một tab. Chọn lý do (nếu có) trước, rồi mới bấm Gán tay / Bỏ ảnh.</b><br>'
             '<kbd>N</kbd> Nhận · <kbd>G</kbd> Gán tay · <kbd>B</kbd> Bỏ ảnh · '
             '<kbd>Z</kbd> Hoàn tác · <kbd>←</kbd> <kbd>→</kbd> Trước/Sau · <kbd>0</kbd>–<kbd>8</kbd> chọn lý do '
             '(0 = không)</div>')
LEGEND_HTML = ('<div class="m28-legend"><span><i class="dot red"></i>chấm đỏ = low_conf (nhìn kỹ)</span>'
               '<span><i class="dot green"></i>chấm xanh = ổn</span></div>')

CSS = """
/* Màu lấy từ biến của theme Gradio nên chế độ tối không hỏng; màu trạng thái dùng nền trong suốt. */
.gradio-container { max-width: 1560px !important; }
#progress, #pagelbl, #info, #msg, #legend, #guide, #keys, #notes { padding: 0 !important; }
#msg { min-height: 64px; }
#info { min-height: 250px; }
#msg .progress-text, #msg .meta-text-center, #msg .meta-text, #msg .generating, #msg .eta-bar { display: none !important; }
.m28-empty { padding: 28px 12px; text-align: center; font-size: 15px; color: var(--body-text-color-subdued);
  border: 1px dashed var(--border-color-primary); border-radius: 10px; }
.m28-done { position: fixed; inset: 0; z-index: 100000; display: flex; align-items: center; justify-content: center;
  background: color-mix(in srgb, var(--background-fill-primary) 96%, transparent); }
.m28-done-box { display: flex; flex-direction: column; gap: 8px; padding: 28px 36px; text-align: center; max-width: 560px;
  background: var(--block-background-fill); border: 2px solid #16a34a; border-radius: 16px; font-size: 17px; }
.m28-done-box b { font-size: 26px; color: #16a34a; }
.m28-head { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 28px; padding: 10px 16px;
  background: var(--block-background-fill); border: 1px solid var(--border-color-primary);
  border-radius: var(--radius-lg); }
.m28-top { display: flex; align-items: baseline; gap: 4px 14px; flex-wrap: wrap; }
.m28-title { font-size: 20px; font-weight: 800; letter-spacing: -.01em; }
.m28-sub { color: var(--body-text-color-subdued); font-size: 14px; }
.m28-prog { display: flex; align-items: center; gap: 10px 14px; flex: 1 1 460px; flex-wrap: wrap; min-width: 0; }
.m28-count { font-weight: 800; font-size: 17px; white-space: nowrap; }
.m28-bar { flex: 1 1 140px; min-width: 100px; height: 12px; border-radius: 999px; overflow: hidden;
  background: var(--border-color-primary); }
.m28-bar > i { display: block; height: 100%; background: #16a34a; border-radius: 999px; transition: width .25s; }
.m28-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.m28-chip { display: inline-flex; align-items: center; gap: 5px; padding: 2px 11px; border-radius: 999px;
  font-size: 13px; line-height: 20px; border: 1px solid var(--cc, #9ca3af); color: var(--body-text-color);
  background: color-mix(in srgb, var(--cc, #9ca3af) 17%, transparent); white-space: nowrap; }
.m28-chip b { font-weight: 800; }
.c-nhan { --cc: #16a34a; } .c-gan_tay { --cc: #d97706; } .c-bo { --cc: #dc2626; } .c-chua { --cc: #9ca3af; }
.m28-note { font-size: 13px; line-height: 1.5; color: var(--body-text-color-subdued); }

#main { gap: 16px; align-items: flex-start; flex-wrap: wrap; }
#left, #center, #side { gap: 10px; }
@media (min-width: 1100px) {
  #center, #side { position: sticky; top: 8px; align-self: flex-start; }
}
@media (max-width: 1099px) {
  #center { order: 1; } #side { order: 2; } #left { order: 3; }
}

#filter { padding: 6px 8px !important; }
#filter .wrap { gap: 4px; flex-wrap: nowrap; }
#filter label { padding: 5px 9px; font-size: 12.5px; white-space: nowrap; }
#filter input[type=radio] { display: none; }
#grid { padding: 0 !important; border: 0 !important; background: transparent !important; }
#grid .gallery-container, #grid .grid-wrap { height: auto !important; min-height: 0 !important; max-height: none !important;
  overflow: visible !important; }
#grid .grid-wrap { padding: 2px !important; }
#grid .grid-container { gap: 8px !important; }
#grid .thumbnail-item { border-radius: 8px !important; overflow: hidden; padding: 0 !important;
  border: 0 !important; background: var(--background-fill-secondary); box-shadow: none !important; }
#grid .thumbnail-item img { width: 100% !important; height: 100% !important; object-fit: contain !important; }
#grid .thumbnail-item.selected { outline: none !important; box-shadow: none !important; }
#grid .thumbnail-item.m28-cur { outline: 4px solid #2563eb !important; outline-offset: 1px; z-index: 1; }
#grid .caption-label { left: 3px !important; right: 3px !important; bottom: 3px !important; width: auto !important;
  max-width: none !important; white-space: normal !important; text-align: left !important; font-size: 9.5px !important;
  line-height: 1.15 !important; padding: 1px 4px !important; border-radius: 4px !important;
  background: color-mix(in srgb, var(--block-background-fill) 90%, transparent) !important;
  color: var(--body-text-color) !important; }
#pager { align-items: center; gap: 8px; flex-wrap: nowrap; }
#pager button { flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; padding: 0 14px !important;
  white-space: nowrap; }
#pager > :nth-child(2) { flex: 1 1 auto !important; }
.m28-page { text-align: center; font-size: 14px; white-space: nowrap; color: var(--body-text-color-subdued); }
.m28-page b { color: var(--body-text-color); }

#big { height: min(512px, 52vh, calc(100vw - 48px)) !important; padding: 0 !important; }
#big .image-container, #big .image-frame, #big .upload-container { height: 100% !important; }
#big img { width: 100% !important; height: 100% !important; object-fit: contain !important; }
.m28-legend { display: flex; flex-wrap: wrap; gap: 2px 16px; font-size: 13px; color: var(--body-text-color-subdued); }
.m28-legend .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: -1px; }
.m28-legend .red { background: #ef0000; } .m28-legend .green { background: #00c800; }

#decide { gap: 10px; flex-wrap: nowrap; }
#decide button { min-height: 56px; font-size: 18px; font-weight: 800; min-width: 0 !important; color: #fff; }
#btn-nhan { background: #16a34a !important; border-color: #15803d !important; }
#btn-gantay { background: #d97706 !important; border-color: #b45309 !important; }
#btn-bo { background: #dc2626 !important; border-color: #b91c1c !important; }
#decide button:hover:not(:disabled) { filter: brightness(.92); }
#decide button:disabled, #nav button:disabled { opacity: .4; cursor: not-allowed; }
#reason { padding: 8px 10px !important; }
#reason .wrap { display: grid !important; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }
#reason label { padding: 5px 8px; font-size: 13px; line-height: 1.2; min-height: 34px; align-items: center; }
#nav { gap: 10px; flex-wrap: nowrap; }
#nav button { min-width: 0 !important; }
#nav button, #pager button { background: var(--background-fill-secondary) !important; color: var(--body-text-color) !important;
  border: 1px solid var(--border-color-primary) !important; }
#nav button:disabled, #pager button:disabled { opacity: .4; }
#reason [data-testid="block-info"], #reason legend, #reason > label > span, #reason .block-info { background: transparent !important;
  color: var(--body-text-color) !important; font-weight: 700; padding-left: 0 !important; }
#reason label.selected, #reason label:has(input:checked) { background: color-mix(in srgb, #2563eb 16%, transparent) !important;
  border-color: #2563eb !important; color: var(--body-text-color) !important; }
#reason input[type=radio]:checked { accent-color: #2563eb; background-color: #2563eb !important; }
@media (max-width: 600px) {
  #decide, #nav { gap: 6px; }
  #decide button { font-size: 15px; white-space: nowrap; padding: 0 4px !important; }
  #nav button { font-size: 14px; white-space: nowrap; padding: 0 6px !important; }
  #reason .wrap { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
#btn-xong { min-height: 48px; font-size: 17px; font-weight: 800; transition: none !important; }
#btn-xong:not(:disabled) { background: #16a34a !important; border-color: #15803d !important; color: #fff !important; opacity: 1 !important; }
#btn-xong:disabled { background: var(--background-fill-secondary) !important; color: var(--body-text-color-subdued) !important;
  border: 1px dashed var(--border-color-primary) !important; opacity: 1; }

.m28-info { width: 100%; border-collapse: collapse; font-size: 14px; }
.m28-info th { text-align: left; font-weight: 600; color: var(--body-text-color-subdued); width: 1%; white-space: nowrap;
  padding: 6px 12px 6px 0; vertical-align: top; border: 0; background: transparent; }
.m28-info td { padding: 6px 0; vertical-align: top; border: 0; background: transparent; overflow-wrap: anywhere; }
.m28-info tr + tr > * { border-top: 1px solid var(--border-color-primary); }
.m28-info .face-name { font-weight: 800; font-size: 16px; }
.m28-pts { font-family: var(--font-mono); font-size: 12.5px; }
.m28-warn { margin-top: 8px; padding: 8px 10px; border-radius: 8px; font-size: 13px; color: var(--body-text-color);
  background: color-mix(in srgb, #d97706 16%, transparent); border: 1px solid #d97706; }
.m28-msg { padding: 8px 10px; border-radius: 8px; font-size: 14px; border-left: 5px solid #9ca3af;
  background: var(--background-fill-secondary); }
.m28-msg.m-ok { border-left-color: #16a34a; } .m28-msg.m-warn { border-left-color: #d97706; }
.m28-guide, .m28-keys { font-size: 13px; line-height: 1.5; color: var(--body-text-color-subdued); }
.m28-guide b { color: var(--body-text-color); }
kbd { display: inline-block; min-width: 20px; padding: 0 5px; text-align: center; font: 600 12px var(--font-mono);
  border: 1px solid var(--border-color-primary); border-bottom-width: 2px; border-radius: 5px;
  background: var(--background-fill-secondary); color: var(--body-text-color); }
"""

PAGE_JS = r"""() => {
  if (window.__m28Keys) { return; }
  window.__m28Keys = true;
  const TEXT = ['text', 'search', 'number', 'email', 'password', 'url', 'tel'];
  const BY_KEY = { n: 'btn-nhan', g: 'btn-gantay', b: 'btn-bo', z: 'btn-undo' };
  const BY_CODE = { KeyN: 'btn-nhan', KeyG: 'btn-gantay', KeyB: 'btn-bo', KeyZ: 'btn-undo' };
  const DECIDE = '#btn-nhan, #btn-gantay, #btn-bo';
  const press = (id) => { const b = document.getElementById(id); if (b && !b.disabled) { b.click(); } };
  const typing = (t) => {
    if (!t || !t.tagName) { return false; }
    if (t.isContentEditable) { return true; }
    if (t.tagName === 'TEXTAREA' || t.tagName === 'SELECT') { return true; }
    if (t.tagName === 'INPUT') { return TEXT.indexOf((t.getAttribute('type') || 'text').toLowerCase()) >= 0; }
    return false;
  };
  const onDecide = (t) => !!(t && t.closest && t.closest(DECIDE));
  document.addEventListener('keydown', (e) => {
    if (e.repeat || e.ctrlKey || e.altKey || e.metaKey || typing(e.target)) { return; }
    if (document.querySelector('.m28-done')) { e.preventDefault(); return; }
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault();
      press(e.key === 'ArrowLeft' ? 'btn-prev' : 'btn-next');
      return;
    }
    if ((e.key === 'Enter' || e.key === ' ') && onDecide(e.target)) { e.preventDefault(); return; }
    const k = e.key.length === 1 ? e.key.toLowerCase() : '';       // e.code là dự phòng khi bộ gõ/bố cục phím làm e.key lạ
    const id = BY_KEY[k] || BY_CODE[e.code];
    if (id) { e.preventDefault(); press(id); return; }
    const m = /^[0-8]$/.test(k) ? [k, k] : /^(?:Digit|Numpad)([0-8])$/.exec(e.code || '');
    if (m) {
      const radios = document.querySelectorAll('#reason input[type=radio]');
      const r = radios[parseInt(m[1], 10)];
      if (r && !r.disabled) { e.preventDefault(); r.click(); }
    }
  });
  document.addEventListener('keyup', (e) => {
    if (e.key === ' ' && onDecide(e.target)) { e.preventDefault(); }
  });
  // Đánh dấu ảnh nhỏ của mặt đang xem. Gradio bỏ qua selected_index=None khi lưới đổi trang nên để lại viền cũ sai chỗ,
  // vì vậy viền xanh dương tự vẽ bằng lớp m28-cur (CSS ẩn viền .selected của Gradio).
  let queued = false;
  const mark = () => {
    queued = false;
    const el = document.querySelector('#info .face-name');
    const cur = el ? el.textContent.trim().replace(/\.png$/i, '') : '';
    document.querySelectorAll('#grid .thumbnail-item').forEach((t) => {
      const img = t.querySelector('img');
      const alt = img ? (img.getAttribute('alt') || '') : '';
      t.classList.toggle('m28-cur', !!cur && (alt === cur || alt.indexOf(cur + ' ') === 0));
    });
  };
  new MutationObserver(() => { if (!queued) { queued = true; requestAnimationFrame(mark); } })
    .observe(document.body, { childList: true, subtree: true, characterData: true });
  mark();
}"""


def prepare_env(run_dir, environ=None):
    """Đặt biến môi trường an toàn TRƯỚC khi import gradio (Gradio đọc chúng lúc import)."""
    env = os.environ if environ is None else environ
    env["GRADIO_ANALYTICS_ENABLED"] = "False"
    env["GRADIO_TEMP_DIR"] = os.path.abspath(os.path.join(run_dir, "_tmp"))
    env["HF_HUB_OFFLINE"] = "1"
    env["HF_HUB_DISABLE_TELEMETRY"] = "1"
    for k in ("NO_PROXY", "no_proxy"):          # máy công ty có proxy: không được đưa localhost qua proxy
        have = [x.strip() for x in env.get(k, "").split(",") if x.strip()]
        env[k] = ",".join(have + [h for h in ("localhost", "127.0.0.1") if h not in have])


def build_ui(store):
    """Dựng Blocks. Chỉ gọi sau khi đã đặt biến môi trường an toàn (xem prepare_env)."""
    import gradio as gr

    run = run_name(store.run_dir)
    theme = gr.themes.Soft(primary_hue="emerald", font=["ui-sans-serif", "system-ui", "Segoe UI", "sans-serif"],
                           font_mono=["ui-monospace", "Consolas", "monospace"])
    close_once = {"started": False}

    def apply(v, reset_reason):
        """Đổi mô hình hiển thị thành tuple cập nhật, đúng thứ tự `outs`."""
        return (v["header"],
                gr.update(choices=v["filter_choices"], value=v["filter_value"]),
                gr.update(value=v["gallery"], visible=bool(v["gallery"]),
                  selected_index=-1 if v["selected"] is None else v["selected"]),   # None bị bỏ qua: -1 = không ảnh nào
                v["page_html"], gr.update(interactive=v["page_prev"]), gr.update(interactive=v["page_next"]),
                v["big"], v["info"],
                gr.update(value="") if reset_reason else gr.update(),
                gr.update(interactive=v["nhan_ok"]), gr.update(interactive=v["tay_ok"]), gr.update(interactive=v["bo_ok"]),
                gr.update(interactive=v["undo_ok"]), gr.update(interactive=v["prev_ok"]),
                gr.update(interactive=v["next_ok"]),
                gr.update(value=v["xong_label"], interactive=v["xong_ok"]),
                v["shown"], v["msg"])

    with gr.Blocks(title=f"Rà soát M28 · {run}", fill_width=True) as demo:
        ses_state = gr.State(None)
        shown = gr.Textbox(visible="hidden", elem_id="shown")
        header = gr.HTML(elem_id="progress", apply_default_css=False)
        with gr.Row(elem_id="main", equal_height=False):
            with gr.Column(scale=4, min_width=400, elem_id="left"):
                flt = gr.Radio(choices=[(t, m) for m, t in FILTERS], value="tat_ca", label="Lọc", show_label=False,
                               elem_id="filter")
                with gr.Row(elem_id="pager"):
                    b_pp = gr.Button("‹ Trang trước", elem_id="btn-pageprev", size="sm")
                    page_lbl = gr.HTML(elem_id="pagelbl", apply_default_css=False)
                    b_pn = gr.Button("Trang sau ›", elem_id="btn-pagenext", size="sm")
                grid = gr.Gallery(show_label=False, allow_preview=False, columns=4, object_fit="contain", buttons=[],
                                  elem_id="grid", height="auto")
            with gr.Column(scale=5, min_width=400, elem_id="center"):
                big = gr.Image(type="filepath", interactive=False, buttons=[], elem_id="big",
                               show_label=False)
                with gr.Row(elem_id="decide"):
                    b_nhan = gr.Button("Nhận (N)", variant="primary", elem_id="btn-nhan")
                    b_tay = gr.Button("Gán tay (G)", elem_id="btn-gantay")
                    b_bo = gr.Button("Bỏ ảnh (B)", variant="stop", elem_id="btn-bo")
                reason = gr.Radio(choices=[(f"{i} · {t}" if c else t, c) for i, (c, t) in enumerate(REASONS)],
                                  value="", label="Lý do: chọn TRƯỚC khi bấm Gán tay / Bỏ ảnh (phím 0–8)", elem_id="reason")
                with gr.Row(elem_id="nav"):
                    b_prev = gr.Button("← Trước", elem_id="btn-prev")
                    b_undo = gr.Button("Hoàn tác (Z)", elem_id="btn-undo")
                    b_next = gr.Button("Sau →", elem_id="btn-next")
            with gr.Column(scale=3, min_width=340, elem_id="side"):
                info = gr.HTML(elem_id="info", apply_default_css=False)
                gr.HTML(LEGEND_HTML, elem_id="legend", apply_default_css=False)
                msg = gr.HTML(elem_id="msg", apply_default_css=False)
                b_xong = gr.Button("Xong", variant="primary", elem_id="btn-xong", interactive=False)
                gr.HTML(GUIDE_HTML, elem_id="guide", apply_default_css=False)
                gr.HTML(KEYS_HTML, elem_id="keys", apply_default_css=False)
                gr.HTML(notes_html(store), elem_id="notes", apply_default_css=False)

        outs = [header, flt, grid, page_lbl, b_pp, b_pn, big, info, reason, b_nhan, b_tay, b_bo, b_undo, b_prev, b_next,
                b_xong, shown, msg]
        opts = dict(show_progress="hidden", api_visibility="private", concurrency_limit=1, concurrency_id="m28")

        def render(ses, m="", level="info", reset=True):
            v = make_view(store, ses, m, level)
            if level == "warn" and m:
                gr.Warning(m, title="Cảnh báo")
            return (ses,) + apply(v, reset)

        all_outs = [ses_state] + outs

        def on_load():
            return render(new_session(store))

        def on_select(ses, evt: gr.SelectData):
            ses = ensure_session(store, ses)
            m, lv = act_select(store, ses, evt.index)
            return render(ses, m, lv)

        def on_filter(mode, ses):
            ses = ensure_session(store, ses)
            m, lv = act_filter(store, ses, mode)
            return render(ses, m, lv)

        def on_page(delta):
            def h(ses):
                ses = ensure_session(store, ses)
                m, lv = act_page(store, ses, delta)
                return render(ses, m, lv, reset=False)
            return h

        def on_step(delta):
            def h(ses):
                ses = ensure_session(store, ses)
                m, lv = act_step(store, ses, delta)
                return render(ses, m, lv)
            return h

        def on_decide(decision):
            def h(why, sh, ses):
                ses = ensure_session(store, ses)
                m, lv, reset = act_decide(store, ses, decision, why, sh)
                return render(ses, m, lv, reset)
            return h

        def on_undo(sh, ses):
            ses = ensure_session(store, ses)
            m, lv, reset = act_undo(store, ses, sh)
            return render(ses, m, lv, reset)

        def on_xong(ses):
            ses = ensure_session(store, ses)
            m, lv, ok = act_finish(store, ses)
            if ok and not close_once["started"]:
                close_once["started"] = True
                threading.Timer(2.0, lambda: demo.close(verbose=False)).start()
            return render(ses, m, lv, reset=False)

        demo.load(on_load, None, all_outs, **opts)
        grid.select(on_select, [ses_state], all_outs, **opts)
        flt.input(on_filter, [flt, ses_state], all_outs, **opts)
        b_pp.click(on_page(-1), [ses_state], all_outs, trigger_mode="multiple", **opts)
        b_pn.click(on_page(1), [ses_state], all_outs, trigger_mode="multiple", **opts)
        b_prev.click(on_step(-1), [ses_state], all_outs, trigger_mode="multiple", **opts)
        b_next.click(on_step(1), [ses_state], all_outs, trigger_mode="multiple", **opts)
        b_nhan.click(on_decide("nhan"), [reason, shown, ses_state], all_outs, **opts)
        b_tay.click(on_decide("gan_tay"), [reason, shown, ses_state], all_outs, **opts)
        b_bo.click(on_decide("bo"), [reason, shown, ses_state], all_outs, **opts)
        b_undo.click(on_undo, [shown, ses_state], all_outs, **opts)
        b_xong.click(on_xong, [ses_state], all_outs, **opts)
    demo.queue(default_concurrency_limit=1)
    return demo, theme


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")      # cmd Windows không chết vì chữ có dấu
        except (AttributeError, ValueError):
            pass
    argv = sys.argv[1:] if argv is None else list(argv)
    if len(argv) != 2:
        print(VI_USAGE, file=sys.stderr)
        return 2
    run_dir, reviewer = argv
    try:
        check_reviewer(reviewer)
        bad = notebook_env()
        if bad:
            raise RunError(bad)
        store = Store(run_dir, reviewer)
        prepare_env(run_dir)
    except RunError as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        return 2
    demo, theme = build_ui(store)
    inbrowser = os.environ.get("M28_NO_BROWSER") != "1"
    try:                                                  # cổng cố định: bản thứ hai không tự nhảy sang cổng khác
        port = int(os.environ.get("GRADIO_SERVER_PORT") or DEFAULT_PORT)
    except ValueError:
        print(f"Lỗi: GRADIO_SERVER_PORT={os.environ.get('GRADIO_SERVER_PORT')!r} không phải số.", file=sys.stderr)
        return 2
    from starlette.middleware import Middleware
    from starlette.middleware.trustedhost import TrustedHostMiddleware
    # Chỉ nhận Host là localhost/127.0.0.1: chặn DNS rebinding từ trang web lạ đọc ảnh mặt qua 127.0.0.1.
    guard = [Middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])]
    allowed = [os.path.abspath(os.path.join(run_dir, d)) for d in ("overlays", os.path.join("crop", "images"), "_tmp")]
    # share=False và 127.0.0.1: chỉ máy này vào được. Gradio có in dòng gợi ý tạo public link: KHÔNG làm theo,
    # nên quiet=True để tắt dòng đó và tự in địa chỉ bằng tiếng Việt.
    try:
        _app, url, _share = demo.launch(server_name="127.0.0.1", server_port=port, share=False, ssr_mode=False,
                                        mcp_server=False, pwa=False, enable_monitoring=False, footer_links=[],
                                        show_error=True, quiet=True, allowed_paths=allowed, inbrowser=inbrowser,
                                        theme=theme, css=CSS, js=PAGE_JS, prevent_thread_lock=True,
                                        app_kwargs={"middleware": guard})
    except OSError as e:
        print(f"Lỗi: không mở được trang rà soát ({e}). Cổng {port} bận: có thể trang rà soát cũ còn mở (đóng nó trước, "
              "tránh hai bản cùng ghi một file) hoặc chương trình khác dùng cổng; đổi cổng bằng set GRADIO_SERVER_PORT=7861.",
              file=sys.stderr)
        return 2
    p = store.progress()
    print(f"Trang rà soát lượt {run_name(run_dir)}, người rà {reviewer}: còn {p['remaining']}/{p['total']} mặt chưa rà.\n"
          f"Mở {url} nếu trình duyệt chưa tự mở (chỉ máy này vào được). Rà xong bấm Xong, trang tự tắt; "
          "Ctrl+C để đóng giữa chừng (gõ lại đúng lệnh để làm tiếp).", flush=True)
    try:
        while demo.is_running:                    # bấm Xong thì demo.close() chạy và vòng này kết thúc
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("Đã đóng trang rà soát (chưa bấm Xong).", flush=True)
        demo.close(verbose=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
