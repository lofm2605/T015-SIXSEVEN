"""Đồng hồ bấm giờ gán nhãn M28 (logic thuần, chỉ thư viện chuẩn; giao diện ở dong_ho_ui.py). Thay facetimer dòng lệnh của P5.

Đơn vị đo là PHIÊN (QĐ-006): từ lúc bắt đầu nạp ảnh lên tool đến lúc hoàn thành. Thao tác: bắt đầu (tự chạy khi bấm Nạp ảnh), tạm dừng/tiếp tục (nút Dừng/Tiếp tục ở đầu trang), hủy (có xác nhận; hộp Đóng trang: Bỏ phiên đồng hồ), xong (lưu & xuất; hộp Đóng trang: Lưu số đo).
Bấm từng mặt ("Xong mặt này → mặt tiếp") chỉ là TUỲ CHỌN cho ai muốn đo chi tiết; nếu chỉ đo cả phiên thì giây/mặt = giây phiên (không tính lúc tạm dừng) ÷ số mặt
và cột `uoc_luong_chia_deu` = 1 để thống kê biết đây là ước lượng chứ không phải đo từng mặt.

Nguồn sự thật là đồng hồ phía server (`time.monotonic`, cộng dồn các đoạn không tạm dừng). Trạng thái ghi NGUYÊN TỬ ra `outputs/timing/dang_chay_<người>.json` sau
mọi thao tác (đóng tab, đóng trình duyệt, tải lại trang không mất gì); mỗi người một phiên; mỗi thao tác kèm `rev` đã thấy (tab cũ bị từ chối); khoá luồng + file
`.khoa_<người>` (O_EXCL) chống ghi chồng giữa hai tiến trình. Máy khởi động lại (`moc_mono` lệch) thì đoạn đang chạy tính lại bằng giờ thật; trang đã tắt khi đồng hồ
đang chạy thì mở lại hỏi trừ khoảng tắt hay giữ.

Xong (lưu & xuất) ghi (1) gói kết quả `outputs/ket_qua/ketqua_<Pk>_<DDMM>_<đợt>.zip` + `.json` (xem m28core/goi_kq.py) để gửi nhóm trưởng, (2) các dòng vào
`outputs/timing/timing_<người>.csv`: 12 cột đầu ĐÚNG tên, thứ tự, nghĩa của facetimer (date, person, condition, task, job, block, seq, face_id, seconds, warmup,
interrupted, note), cột thêm chỉ nối ở cuối; UTF-8 không BOM, dòng CRLF. Hủy không ghi dòng nào (chỉ nhật ký huy_<người>.csv). Không ảnh mặt, không mạng, không token.
Khác facetimer: ghi lúc Xong (file trạng thái bù lại); chỗ đặt file; cột thêm; có Hủy, Hoàn tác, chặn mặt < 2 giây, tự tạm dừng khi đóng trang; bỏ tích
"Tính mặt đang làm" = phím q (bỏ mặt đang làm).
"""
import csv
import datetime
import glob
import io
import json
import os
import re
import secrets
import sys
import threading
import time
import unicodedata

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)
import ca_kho  # noqa: E402  (clean_text, _formula_safe, _atomic_write)
import dot_anh  # noqa: E402  (Pending: yêu cầu xác nhận dùng một lần)
from m28core import collect as collect_mod  # noqa: E402  (latest_raw_files)
from m28core import dang_chay, goi_kq, nhom as nhom_mod  # noqa: E402

PHIEN_BAN = 1
NGUOI_OK = ("P1", "P2", "P3", "P4", "P5")
DIEU_KIEN = ("manual", "assisted")
THU_MUC = os.path.join("outputs", "timing")
FACETIMER_COLS = ["date", "person", "condition", "task", "job", "block", "seq", "face_id", "seconds", "warmup", "interrupted", "note"]
EXTRA_COLS = ["phien", "dot", "bo_anh", "bat_dau", "ket_thuc", "so_lan_tam_dung", "giay_tam_dung", "so_mat_phien", "giay_phien", "ghi_chu_phien", "sua_tay",
              "canh_bao", "nguon_ghi", "uoc_luong_chia_deu"]
CSV_COLS = FACETIMER_COLS + EXTRA_COLS
HUY_COLS = ["thoi_diem", "nguoi", "dieu_kien", "task", "job", "khoi", "phien", "so_mat_bo", "giay_bo", "ly_do"]
MAT_TOI_THIEU_GIAY = 2.0               # mặt/phiên ngắn hơn: bấm quá nhanh (chống bấm đúp)
MAT_LAU_PHUT = 20                      # một mặt (khi bấm từng mặt) chạy quá ngần này phút: nghi quên bấm
PHIEN_LAU_PHUT = 150                   # buổi tối đa 120 phút: phiên chạy quá ngần này phút thì nghi quên bấm
MOC_LECH_GIAY = 5.0                    # moc_mono lệch hơn ngần này giây: máy khởi động lại (monotonic cũ vô nghĩa)
KHOANG_TAT_TOI_THIEU_GIAY = 90.0       # trang tắt lâu hơn ngần này (nhịp đồng bộ là 60 giây) mới hỏi trừ khoảng tắt
NHIP_DONG_BO_GIAY = 60.0
KHOA_CU_GIAY = 30.0
N_MAT_MAC_DINH, N_MAT_MAX = 10, 5000
TASK_RE = re.compile(r"[A-Za-z0-9_.-]{1,64}")
KHOI_RE = re.compile(r"[A-Za-z0-9_-]{1,20}")
DOT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
JOB_RE = re.compile(r"\d{1,9}")
TRANG_THAI_OK = ("chay", "tam_dung", "du_mat")
CANH_BAO_VI = {
    "qua_dem": "Phiên chạy qua nửa đêm (qua ngày mới).",
    "phien_lau": f"Phiên đã chạy hơn {PHIEN_LAU_PHUT} phút (buổi tối đa 120 phút): có quên bấm Tạm dừng hoặc Xong không?",
    "mat_lau": f"Mặt đang làm đã chạy hơn {MAT_LAU_PHUT} phút: có quên bấm Xong mặt không?",
    "khoi_dong_lai": "Máy có vẻ đã khởi động lại hoặc ngủ khi đồng hồ chạy; thời gian đoạn đó tính theo giờ thật.",
    "khoang_tat": "Trang đã tắt khi đồng hồ đang chạy.",
}
HANH_DONG = {"qua_dem": ("giu", "sua"), "phien_lau": ("sua", "giu"), "mat_lau": ("sua", "giu"), "khoi_dong_lai": ("sua", "giu"), "khoang_tat": ("tru", "giu")}


class DongHoLoi(Exception):
    """Từ chối thao tác (lỗi người dùng sửa được). cu=True: tab đã cũ (rev khác), cần tải lại; hong=True: file trạng thái hỏng; cho=True: cần bấm lần hai."""

    def __init__(self, msg, cu=False, hong=False, cho=False):
        super().__init__(msg)
        self.cu, self.hong, self.cho = cu, hong, cho


class Gio:
    """Nguồn giờ thật; test tiêm bản giả (mono, epoch, now)."""

    def mono(self):
        return time.monotonic()

    def epoch(self):
        return time.time()

    def now(self):
        return datetime.datetime.now().astimezone()


def fmt_giay(s):
    """mm:ss (>= 60 phút: h:mm:ss)."""
    s = max(0, int(round(float(s or 0))))
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


def doc_mm_ss(text):
    """'mm:ss' hoặc 'h:mm:ss' hoặc số giây -> giây (float); None nếu sai."""
    t = str(text or "").strip().replace(",", ".")
    if not t:
        return None
    try:
        if ":" in t:
            parts = [float(x) for x in t.split(":")]
            if len(parts) not in (2, 3) or any(x < 0 for x in parts):
                return None
            sec = 0.0
            for x in parts:
                sec = sec * 60 + x
            return sec
        v = float(t)
        return v if v >= 0 else None
    except ValueError:
        return None


def khong_dau_hoa(text):
    t = unicodedata.normalize("NFD", str(text or ""))
    return "".join(c for c in t if unicodedata.category(c) != "Mn").replace("Đ", "D").replace("đ", "d").strip().upper()


def _clean(s, maxlen, what):
    try:
        return ca_kho.clean_text(s, maxlen, what)
    except Exception as e:                                             # RunError của nap_anh
        raise DongHoLoi(str(e))


class DongHo:
    """Đồng hồ của một thư mục dự án (project_root). Mọi phương thức thao tác nhận `rev` (số lần thao tác mà tab đã thấy); None = không kiểm (chỉ test)."""

    def __init__(self, project_root, gio=None, pid=None):
        self.root = os.path.abspath(project_root)
        self.dir = os.path.join(self.root, THU_MUC)
        self.gio = gio or Gio()
        self.pid = pid if pid is not None else os.getpid()
        self._locks, self._glock = {}, threading.Lock()
        self._cho_xong, self._cho_bd, self._huy = {}, {}, {}
        self.closing = False

    # ---------- đường dẫn, khoá ----------
    def p_state(self, nguoi):
        return os.path.join(self.dir, f"dang_chay_{nguoi}.json")

    def p_csv(self, nguoi):
        return os.path.join(self.dir, f"timing_{nguoi}.csv")

    def p_huy(self, nguoi):
        return os.path.join(self.dir, f"huy_{nguoi}.csv")

    def p_khoa(self, nguoi):
        return os.path.join(self.dir, f".khoa_{nguoi}")

    def rel(self, p):
        try:
            return os.path.relpath(p, self.root)
        except ValueError:
            return os.path.basename(p)

    @staticmethod
    def _nguoi(nguoi):
        if nguoi not in NGUOI_OK:
            raise DongHoLoi("Chọn người P1 đến P5 (đồng hồ chỉ ghi cho P1–P5, đúng tên file timing_P<số>.csv của P5).")
        return nguoi

    def _thread_lock(self, nguoi):
        with self._glock:
            return self._locks.setdefault(nguoi, threading.RLock())

    def _khoa(self, nguoi):
        return _Khoa(self, nguoi)

    # ---------- đọc/ghi trạng thái ----------
    def _kiem_trang_thai(self, st, nguoi):
        def bad(why):
            raise DongHoLoi(f"File trạng thái đồng hồ của {nguoi} hỏng ({why}). Bấm \"Bỏ trạng thái hỏng\" (file chỉ đổi tên, không xoá) rồi Bắt đầu lại.", hong=True)
        if not isinstance(st, dict):
            bad("không phải đối tượng JSON")
        need = ("phien_ban", "rev", "phien", "nguoi", "dieu_kien", "trang_thai", "doan", "bat_dau", "moc_mono", "n_mat", "cat_active", "so_lan_tam_dung")
        miss = [k for k in need if k not in st]
        if miss:
            bad("thiếu khoá " + ", ".join(miss))
        if st["phien_ban"] != PHIEN_BAN or st["nguoi"] != nguoi or st["trang_thai"] not in TRANG_THAI_OK or st["dieu_kien"] not in DIEU_KIEN:
            bad("giá trị lạ")
        segs = st["doan"]
        if not isinstance(segs, list) or not segs:
            bad("không có đoạn chạy")
        for i, g in enumerate(segs):
            if not isinstance(g, dict) or not all(isinstance(g.get(k), (int, float)) for k in ("a", "ea")):
                bad("đoạn chạy sai định dạng")
            if g.get("b") is not None and (not isinstance(g["b"], (int, float)) or g["b"] < g["a"]):
                bad("đoạn chạy ngược")
            if g.get("b") is None and i != len(segs) - 1:
                bad("đoạn mở không nằm cuối")
        if not isinstance(st["mat"], list) if "mat" in st else False:
            bad("danh sách mặt sai")
        return st

    def doc_trang_thai(self, nguoi):
        """Nội dung file trạng thái hoặc None nếu chưa có phiên. Hỏng thì DongHoLoi(hong=True)."""
        p = self.p_state(nguoi)
        if not os.path.exists(p):
            return None
        try:
            with open(p, encoding="utf-8") as f:
                st = json.load(f)
        except (OSError, ValueError) as e:
            raise DongHoLoi(f"File trạng thái đồng hồ của {nguoi} không đọc được ({type(e).__name__}). Bấm \"Bỏ trạng thái hỏng\" (file chỉ đổi tên, không xoá).", hong=True)
        st.setdefault("mat", []) if isinstance(st, dict) else None
        return self._kiem_trang_thai(st, nguoi)

    def _ghi(self, st, nguoi, tang_rev=True, heartbeat=True):
        if tang_rev:
            st["rev"] = int(st.get("rev", 0)) + 1
        st["pid"] = self.pid
        if heartbeat:
            st["lan_cuoi_thay"] = ca_kho.iso(self.gio.now())
            st["lan_cuoi_epoch"] = self.gio.epoch()
        st["moc_mono"] = self.gio.epoch() - self.gio.mono()
        os.makedirs(self.dir, exist_ok=True)
        ca_kho._atomic_write(self.p_state(nguoi), json.dumps(st, ensure_ascii=False, indent=1).encode("utf-8"))

    def _xoa_trang_thai(self, nguoi):
        try:
            os.remove(self.p_state(nguoi))
        except FileNotFoundError:
            pass

    # ---------- tính giờ ----------
    def _giay_doan(self, g, mono, epoch):
        if g.get("gt"):                                     # đoạn tính bằng giờ thật (máy khởi động lại)
            return max(0.0, (g["eb"] if g.get("eb") is not None else epoch) - g["ea"])
        return max(0.0, (g["b"] if g.get("b") is not None else mono) - g["a"])

    def tong_chay(self, st, mono=None, epoch=None):
        """Tổng giây đã chạy của phiên (cộng dồn các đoạn không tạm dừng)."""
        mono = self.gio.mono() if mono is None else mono
        epoch = self.gio.epoch() if epoch is None else epoch
        return sum(self._giay_doan(g, mono, epoch) for g in st["doan"])

    def tong_tam_dung(self, st, mono=None, epoch=None):
        """Tổng giây tạm dừng (khoảng giữa các đoạn chạy, và từ cuối đoạn cuối đến bây giờ nếu đang tạm dừng)."""
        mono = self.gio.mono() if mono is None else mono
        tong = 0.0
        segs = st["doan"]
        for p, n in zip(segs, segs[1:]):
            tong += max(0.0, (n["ea"] - (p["eb"] if p.get("eb") is not None else n["ea"])))
        if st["trang_thai"] == "tam_dung" and segs[-1].get("eb") is not None:
            tong += max(0.0, self.gio.epoch() - segs[-1]["eb"])
        return tong

    def giay_mat_hien_tai(self, st):
        return max(0.0, self.tong_chay(st) - st["cat_active"] - st.get("tru_giay", 0.0))

    def giay_hieu_luc(self, st, tong=None):
        """Giây phiên SAU khi trừ phần đã sửa tay (mặt đã khép và mặt đang làm)."""
        tong = self.tong_chay(st) if tong is None else tong
        return max(0.0, tong - sum(float(m.get("tru", 0.0)) for m in st["mat"]) - st.get("tru_giay", 0.0))

    def _dong_doan(self, st):
        g = st["doan"][-1]
        if g.get("b") is None:
            g["b"], g["eb"] = self.gio.mono(), self.gio.epoch()

    def _mo_doan(self, st):
        st["doan"].append(dict(a=self.gio.mono(), ea=self.gio.epoch(), b=None, eb=None, gt=False))

    # ---------- đồng bộ: khởi động lại máy, trang đã tắt ----------
    def _dong_bo(self, st):
        """Phát hiện máy khởi động lại (moc_mono lệch) và trang đã tắt khi đồng hồ chạy (pid cũ đã chết). Sửa trạng thái trong bộ nhớ; True nếu có thay đổi cần ghi."""
        changed = False
        epoch, mono = self.gio.epoch(), self.gio.mono()
        cur = epoch - mono
        ma = st.setdefault("canh_bao_ma", [])
        if abs(cur - float(st["moc_mono"])) > MOC_LECH_GIAY:
            g = st["doan"][-1]
            if g.get("b") is None:
                mono_el, wall_el = mono - g["a"], epoch - g["ea"]
                # monotonic lùi (máy khởi động lại) hoặc giờ thật đi nhanh hơn monotonic (khởi động lại muộn, máy ngủ): tính đoạn đang chạy bằng giờ thật.
                # Giờ hệ thống bị chỉnh LÙI (monotonic vẫn liền mạch): giữ monotonic, không nghi khởi động lại.
                if mono < g["a"] - 1.0 or wall_el >= mono_el - MOC_LECH_GIAY:
                    g["gt"] = True
                    if "khoi_dong_lai" not in ma:
                        ma.append("khoi_dong_lai")
            st["moc_mono"] = cur
            changed = True
        if st["trang_thai"] == "chay" and st.get("pid") not in (None, self.pid) and not dang_chay.pid_alive(st.get("pid")):
            gap = epoch - float(st.get("lan_cuoi_epoch") or epoch)
            if gap > KHOANG_TAT_TOI_THIEU_GIAY and not st.get("khoang_tat"):
                st["khoang_tat"] = dict(tu=st.get("lan_cuoi_thay", ""), den=ca_kho.iso(self.gio.now()), giay=round(gap, 1), lan_cuoi_epoch=st.get("lan_cuoi_epoch"))
                if "khoang_tat" not in ma:
                    ma.append("khoang_tat")
            st["pid"] = self.pid
            changed = True
        return changed

    def _nap(self, nguoi, bat_buoc=True):
        """(st, đã_đổi). st None nếu chưa có phiên (bat_buoc=False)."""
        st = self.doc_trang_thai(nguoi)
        if st is None:
            if bat_buoc:
                raise DongHoLoi(f"{nguoi} chưa có phiên nào đang chạy (tab này có thể đã cũ): bấm Bắt đầu.", cu=True)
            return None, False
        return st, self._dong_bo(st)

    def _kiem_rev(self, st, rev):
        if rev is not None and rev != st["rev"]:
            raise DongHoLoi("Đồng hồ vừa đổi ở tab khác, đã tải lại: kiểm lại rồi bấm lại.", cu=True)

    def _chan_dong(self):
        if self.closing:
            raise DongHoLoi("Trang đang đóng: không ghi được nữa.")

    # ---------- cảnh báo ----------
    def canh_bao(self, st):
        """Danh sách cảnh báo ĐANG HIỆU LỰC: dict(ma, text, hanh_dong=(...), xu_ly=bool). Tính lại mỗi lần (không lưu), trừ quyết định của người dùng."""
        qd = st.get("quyet_dinh", {})
        out = []

        def them(ma, text=None):
            out.append(dict(ma=ma, text=text or CANH_BAO_VI[ma], hanh_dong=HANH_DONG[ma], xu_ly=ma in qd))
        t = self.giay_mat_hien_tai(st)
        hl = self.giay_hieu_luc(st)
        if hl > PHIEN_LAU_PHUT * 60:
            them("phien_lau", f"Phiên đã chạy {fmt_giay(hl)} (hơn {PHIEN_LAU_PHUT} phút; buổi tối đa 120 phút): có quên bấm Tạm dừng hoặc Xong không?")
        if st["mat"] and t > MAT_LAU_PHUT * 60:
            them("mat_lau", f"Mặt đang làm đã chạy {fmt_giay(t)} (hơn {MAT_LAU_PHUT} phút): có quên bấm Xong mặt không?")
        bd = ca_kho.parse_time(st.get("bat_dau"))
        if bd is not None and bd.date() != self.gio.now().date():
            them("qua_dem")
        if "khoi_dong_lai" in st.get("canh_bao_ma", []):
            them("khoi_dong_lai")
        kt = st.get("khoang_tat")
        if kt:
            them("khoang_tat", f"Trang đã tắt từ khoảng {ca_kho.fmt_date(kt.get('tu'))} {str(kt.get('tu', ''))[11:16]} đến {str(kt.get('den', ''))[11:16]} "
                               f"(khoảng {fmt_giay(kt.get('giay', 0))}); đồng hồ vẫn tính khoảng này.")
        return out

    def _chua_xu_ly(self, st):
        return [c for c in self.canh_bao(st) if not c["xu_ly"]]

    # ---------- khung nhìn cho giao diện ----------
    def xem(self, nguoi):
        """dict mô tả phiên của `nguoi` cho giao diện (không đổi gì). co_phien=False nếu chưa có phiên; lỗi file hỏng -> dict(hong=True, loi=...)."""
        out = dict(co_phien=False, nguoi=nguoi, rev=0, hong=False, loi="")
        try:
            st, changed = self._nap(nguoi, bat_buoc=False)
        except DongHoLoi as e:
            out.update(hong=e.hong, loi=str(e))
            return out
        if st is None:
            return out
        if changed:
            try:
                with self._khoa(nguoi):
                    st2, _c = self._nap(nguoi, bat_buoc=False)
                    if st2 is not None:
                        self._ghi(st2, nguoi, tang_rev=False)
                        st = st2
            except (DongHoLoi, OSError):
                pass
        mono, epoch = self.gio.mono(), self.gio.epoch()
        tong = self.tong_chay(st, mono, epoch)
        mat_hien = max(0.0, tong - st["cat_active"] - st.get("tru_giay", 0.0))
        theo_mat = bool(st["mat"])
        seq = st["seq_dau"] + len(st["mat"])
        out.update(co_phien=True, rev=st["rev"], phien=st["phien"], dieu_kien=st["dieu_kien"], dot=st.get("dot", ""), bo_anh=st.get("bo_anh", ""), task=st.get("task", ""),
                   job=st.get("job", ""), khoi=st.get("khoi", ""), n_mat=st["n_mat"], seq=seq, trang_thai=st["trang_thai"], theo_mat=theo_mat,
                   face_id=f"{st.get('khoi', '')}_{seq:02d}", giay_phien=self.giay_hieu_luc(st, tong), giay_mat=mat_hien, giay_hien_thi=(mat_hien if theo_mat else self.giay_hieu_luc(st, tong)),
                   chay=st["trang_thai"] == "chay", so_lan_tam_dung=st["so_lan_tam_dung"], giay_tam_dung=self.tong_tam_dung(st),
                   mat=[dict(seq=m["seq"], face_id=m["face_id"], giay=m["giay"], tam_dung=m.get("tam_dung", 0), ghi_chu=m.get("ghi_chu", ""), sua_tay=int(m.get("sua_tay", 0)))
                        for m in st["mat"]],
                   canh_bao=self.canh_bao(st), bat_dau=st["bat_dau"], ghi_chu_phien=st.get("ghi_chu_phien", ""), sua_tay=int(bool(st.get("sua_tay"))),
                   ma_canh_bao=list(st.get("canh_bao_ma", [])), lan_cuoi_thay=st.get("lan_cuoi_thay", ""),
                   du_mat=st["trang_thai"] == "du_mat" or (theo_mat and len(st["mat"]) >= st["n_mat"]))
        return out

    # ---------- thao tác ----------
    def bat_dau(self, nguoi, dieu_kien, dot="", task="", job="", khoi="", n_mat=N_MAT_MAC_DINH, seq_dau=None, bo_anh="", ghi_chu="", rev=0):
        """Bắt đầu phiên. Từ chối nếu người này đã có phiên (chạy hoặc tạm dừng), ô sai, hoặc task/điều kiện lệch (m28-manual với assisted...). Seq sắp ghi đã có dòng
        cho cùng người/task/khối thì lần bấm đầu chỉ cảnh báo, bấm lần hai (cùng ô) mới bắt đầu."""
        self._chan_dong()
        self._nguoi(nguoi)
        if dieu_kien not in DIEU_KIEN:
            raise DongHoLoi("Chọn điều kiện manual (gán tay hoàn toàn) hoặc assisted (dùng tool, sửa nháp).")
        dot = _clean(dot, 64, "Đợt").strip()
        if dot and not DOT_RE.fullmatch(dot):
            raise DongHoLoi("Tên đợt chỉ gồm chữ không dấu, số, _ - . (tối đa 64 ký tự), ví dụ NAP_001.")
        task = _clean(task, 64, "Task").strip() or (f"demo-{dot}" if dot else "")
        if task and not TASK_RE.fullmatch(task):
            raise DongHoLoi("Tên task chỉ gồm chữ không dấu, số, _ - . (tối đa 64 ký tự).")
        if (task == "m28-manual" and dieu_kien == "assisted") or (task == "m28-assisted" and dieu_kien == "manual"):
            raise DongHoLoi(f"Task {task} đi với điều kiện {'manual' if task == 'm28-manual' else 'assisted'}, không phải {dieu_kien}: sửa task hoặc điều kiện.")
        job = str(job or "").strip()
        if job and not JOB_RE.fullmatch(job):
            raise DongHoLoi("Job là số job CVAT (chỉ chữ số, tối đa 9 chữ số) hoặc để trống.")
        khoi = (khoi or "").strip() or re.sub(r"[^A-Za-z0-9_-]", "", dot)[:20] or "X"
        if not KHOI_RE.fullmatch(khoi):
            raise DongHoLoi("Khối chỉ gồm chữ không dấu, số, _ - (tối đa 20 ký tự).")
        try:
            n_mat = int(n_mat)
        except (TypeError, ValueError):
            raise DongHoLoi("Số mặt phải là số nguyên.")
        if not 1 <= n_mat <= N_MAT_MAX:
            raise DongHoLoi(f"Số mặt phải từ 1 đến {N_MAT_MAX}.")
        bo_anh = _clean(bo_anh, 64, "Bộ ảnh").strip()
        ghi_chu = _clean(ghi_chu, 200, "Ghi chú phiên")
        seq0 = self.seq_goi_y(nguoi, task, khoi) if seq_dau in (None, "") else seq_dau
        try:
            seq0 = int(seq0)
        except (TypeError, ValueError):
            raise DongHoLoi("Seq bắt đầu phải là số nguyên.")
        if seq0 < 1:
            raise DongHoLoi("Seq bắt đầu phải từ 1.")
        with self._khoa(nguoi):
            cu = self.doc_trang_thai(nguoi) if os.path.exists(self.p_state(nguoi)) else None
            if cu is not None:
                raise DongHoLoi(f"{nguoi} đã có một phiên ({cu['dieu_kien']} · {cu.get('task') or cu.get('dot') or '?'} · bắt đầu {str(cu['bat_dau'])[11:16]}): "
                                "bấm Xong (lưu) hoặc Hủy phiên đó trước khi bắt đầu phiên mới.", cu=True)
            if rev is not None and rev != 0:
                raise DongHoLoi("Đồng hồ vừa đổi ở tab khác, đã tải lại: kiểm lại rồi bấm lại.", cu=True)
            canh = []
            cfg = nhom_mod.doc(self.root)
            g = nhom_mod.nhom_cua(cfg, nguoi)
            if g is None:
                canh.append("chua_co_nhom")
            elif g != dieu_kien:
                canh.append("lech_nhom")
            trung = self._seq_trung(nguoi, task, khoi, seq0, n_mat)
            key = (nguoi, dieu_kien, task, khoi, seq0, n_mat)
            if trung and self._cho_bd.get(nguoi) != key:
                self._cho_bd[nguoi] = key
                raise DongHoLoi(f"Đã có dòng bấm giờ của {nguoi} cho task {task}, khối {khoi}, seq {', '.join(map(str, trung[:6]))}{'…' if len(trung) > 6 else ''}: "
                                "bắt đầu sẽ tạo dòng TRÙNG. Muốn tiếp tục bấm Bắt đầu thêm một lần nữa (hoặc đổi seq bắt đầu).", cho=True)
            self._cho_bd.pop(nguoi, None)
            if trung:
                canh.append("trung_seq")
            now = self.gio.now()
            st = dict(phien_ban=PHIEN_BAN, rev=0, phien=f"{nguoi}-{now.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(2)}", nguoi=nguoi, dieu_kien=dieu_kien,
                      dot=dot, bo_anh=bo_anh or cfg.get("bo_anh", ""), task=task, job=job, khoi=khoi, n_mat=n_mat, seq_dau=seq0, ghi_chu_phien=ghi_chu,
                      bat_dau=ca_kho.iso(now), trang_thai="chay", doan=[], so_lan_tam_dung=0, mat=[], cat_active=0.0, cat_tam_dung=0, cat_iso=ca_kho.iso(now),
                      tru_giay=0.0, sua_tay=0, canh_bao_ma=list(canh), quyet_dinh={}, khoang_tat=None, nhom_cau_hinh=g or "")
            self._mo_doan(st)
            st["moc_mono"] = self.gio.epoch() - self.gio.mono()
            self._ghi(st, nguoi)
            return self.xem(nguoi)

    def seq_goi_y(self, nguoi, task, khoi):
        """seq lớn nhất đã ghi cho cùng người/task/khối + 1 (chưa có thì 1): buổi bù thì mặt đầu tự thành khởi động."""
        best = 0
        for r in self._doc_csv(nguoi)[1]:
            if r.get("person") == nguoi and r.get("task") == task and r.get("block") == khoi:
                try:
                    best = max(best, int(float(r.get("seq") or 0)))
                except ValueError:
                    pass
        return best + 1

    def _seq_trung(self, nguoi, task, khoi, seq0, n):
        want = set(range(seq0, seq0 + n))
        have = set()
        for r in self._doc_csv(nguoi)[1]:
            if r.get("person") == nguoi and r.get("task") == task and r.get("block") == khoi:
                try:
                    s = int(float(r.get("seq") or 0))
                except ValueError:
                    continue
                if s in want:
                    have.add(s)
        return sorted(have)

    def tam_dung(self, nguoi, rev=None):
        self._chan_dong()
        self._nguoi(nguoi)
        with self._khoa(nguoi):
            st, _c = self._nap(nguoi)
            self._kiem_rev(st, rev)
            if st["trang_thai"] != "chay":
                raise DongHoLoi("Đồng hồ không đang chạy nên không tạm dừng được." if st["trang_thai"] == "tam_dung" else "Đã đủ mặt: bấm Xong (lưu).")
            self._tam_dung_trong(st)
            self._ghi(st, nguoi)
        return self.xem(nguoi)

    def _tam_dung_trong(self, st, ma=None):
        self._dong_doan(st)
        st["trang_thai"] = "tam_dung"
        st["so_lan_tam_dung"] += 1
        if ma and ma not in st.setdefault("canh_bao_ma", []):
            st["canh_bao_ma"].append(ma)

    def tiep_tuc(self, nguoi, rev=None):
        self._chan_dong()
        self._nguoi(nguoi)
        with self._khoa(nguoi):
            st, _c = self._nap(nguoi)
            self._kiem_rev(st, rev)
            if st["trang_thai"] == "chay":
                raise DongHoLoi("Đồng hồ đang chạy rồi.")
            if st["trang_thai"] == "du_mat":
                raise DongHoLoi("Đã đủ mặt: bấm Xong (lưu), hoặc Hoàn tác mặt vừa xong để làm tiếp.")
            self._mo_doan(st)
            st["trang_thai"] = "chay"
            self._ghi(st, nguoi)
        return self.xem(nguoi)

    def xong_mat(self, nguoi, rev=None, ghi_chu=""):
        """(Tuỳ chọn) khép mặt đang làm, mở mặt kế. Mặt < 2 giây thì từ chối (chống bấm đúp). Đang tạm dừng thì phải Tiếp tục trước."""
        self._chan_dong()
        self._nguoi(nguoi)
        ghi_chu = _clean(ghi_chu, 200, "Ghi chú mặt")
        with self._khoa(nguoi):
            st, _c = self._nap(nguoi)
            self._kiem_rev(st, rev)
            if st["trang_thai"] == "tam_dung":
                raise DongHoLoi("Đang tạm dừng: bấm Tiếp tục trước khi bấm Xong mặt.")
            if st["trang_thai"] == "du_mat":
                raise DongHoLoi("Đã đủ mặt: bấm Xong (lưu).")
            tong = self.tong_chay(st)
            giay = tong - st["cat_active"] - st.get("tru_giay", 0.0)
            if giay < MAT_TOI_THIEU_GIAY:
                raise DongHoLoi(f"Mặt này mới {giay:.1f} giây (dưới {MAT_TOI_THIEU_GIAY:g} giây): bấm quá nhanh nên không khép (tránh bấm đúp).")
            seq = st["seq_dau"] + len(st["mat"])
            now = ca_kho.iso(self.gio.now())
            sua = st.get("tru_giay", 0.0) > 0
            st["mat"].append(dict(seq=seq, face_id=f"{st['khoi']}_{seq:02d}", giay=round(giay, 1), tam_dung=st["so_lan_tam_dung"] - st["cat_tam_dung"],
                                  bat_dau=st["cat_iso"], ket_thuc=now, ghi_chu=ghi_chu, sua_tay=int(sua), tru=round(st.get("tru_giay", 0.0), 1),
                                  a0=st["cat_active"], a1=tong, t0=st["cat_tam_dung"], iso0=st["cat_iso"]))
            st["cat_active"], st["cat_tam_dung"], st["cat_iso"], st["tru_giay"] = tong, st["so_lan_tam_dung"], now, 0.0
            st.setdefault("quyet_dinh", {}).pop("mat_lau", None)
            if len(st["mat"]) >= st["n_mat"]:
                self._dong_doan(st)
                st["trang_thai"] = "du_mat"
            self._ghi(st, nguoi)
        return self.xem(nguoi)

    def hoan_tac_mat(self, nguoi, rev=None):
        """Gộp mặt vừa khép trở lại thành mặt đang làm (giây, số lần tạm dừng cộng dồn, seq lùi một)."""
        self._chan_dong()
        self._nguoi(nguoi)
        with self._khoa(nguoi):
            st, _c = self._nap(nguoi)
            self._kiem_rev(st, rev)
            if not st["mat"]:
                raise DongHoLoi("Chưa có mặt nào đã khép trong phiên này để hoàn tác.")
            m = st["mat"].pop()
            st["cat_active"], st["cat_tam_dung"], st["cat_iso"] = m["a0"], m["t0"], m["iso0"]
            st["tru_giay"] = float(m.get("tru", 0.0)) + st.get("tru_giay", 0.0)
            if st["trang_thai"] == "du_mat":
                st["trang_thai"] = "tam_dung"
                st["so_lan_tam_dung"] += 1
            self._ghi(st, nguoi)
        return self.xem(nguoi)

    def sua_thoi_gian(self, nguoi, giay, rev=None):
        """Sửa thời gian của đơn vị đang đo (mặt đang làm nếu có bấm từng mặt, không thì cả phiên) xuống `giay` thật (2 giây <= giá trị <= số đo được). Đặt sua_tay = 1."""
        self._chan_dong()
        self._nguoi(nguoi)
        v = giay if isinstance(giay, (int, float)) else doc_mm_ss(giay)
        if v is None:
            raise DongHoLoi("Nhập thời gian dạng mm:ss (ví dụ 12:30) hoặc h:mm:ss.")
        with self._khoa(nguoi):
            st, _c = self._nap(nguoi)
            self._kiem_rev(st, rev)
            do = self.tong_chay(st) - st["cat_active"]
            if v < MAT_TOI_THIEU_GIAY:
                raise DongHoLoi(f"Thời gian sửa phải từ {MAT_TOI_THIEU_GIAY:g} giây trở lên.")
            if v > do + 0.05:
                raise DongHoLoi(f"Thời gian sửa ({fmt_giay(v)}) không được lớn hơn số đo được ({fmt_giay(do)}): chỉ sửa xuống, không sửa lên.")
            goc = do - st.get("tru_giay", 0.0) if st.get("tru_giay") else do
            st["tru_giay"] = max(0.0, do - v)
            st["sua_tay"] = 1
            st.setdefault("ghi_sua", []).append(dict(giay_do_goc=round(goc, 1), giay_sua=round(v, 1)))
            qd = st.setdefault("quyet_dinh", {})
            for c in self.canh_bao(st):
                if c["ma"] in ("phien_lau", "mat_lau", "khoi_dong_lai", "qua_dem"):
                    qd[c["ma"]] = "sua"
            self._ghi(st, nguoi)
        return self.xem(nguoi)

    def giu_canh_bao(self, nguoi, ma, rev=None):
        self._chan_dong()
        self._nguoi(nguoi)
        if ma not in HANH_DONG:
            raise DongHoLoi("Cảnh báo không hợp lệ.")
        with self._khoa(nguoi):
            st, _c = self._nap(nguoi)
            self._kiem_rev(st, rev)
            st.setdefault("quyet_dinh", {})[ma] = "giu"
            if ma not in st.setdefault("canh_bao_ma", []):
                st["canh_bao_ma"].append(ma)
            self._ghi(st, nguoi)
        return self.xem(nguoi)

    def tru_khoang_tat(self, nguoi, rev=None):
        """Trừ khoảng trang tắt (coi như tạm dừng từ lần cuối thấy trang): đóng đoạn chạy tại thời điểm đó; người dùng bấm Tiếp tục để chạy lại."""
        self._chan_dong()
        self._nguoi(nguoi)
        with self._khoa(nguoi):
            st, _c = self._nap(nguoi)
            self._kiem_rev(st, rev)
            kt = st.get("khoang_tat")
            if not kt:
                raise DongHoLoi("Không có khoảng trang tắt nào để trừ.")
            g = st["doan"][-1]
            if g.get("b") is None:
                le = float(kt.get("lan_cuoi_epoch") or g["ea"])
                g["eb"] = max(g["ea"], le)
                g["b"] = g["a"] + max(0.0, g["eb"] - g["ea"])
                st["trang_thai"] = "tam_dung"
                st["so_lan_tam_dung"] += 1
            st.setdefault("quyet_dinh", {})["khoang_tat"] = "tru"
            self._ghi(st, nguoi)
        return self.xem(nguoi)

    def bo_trang_thai_hong(self, nguoi):
        """Đổi tên file trạng thái hỏng thành dang_chay_<người>.hong-<YYYYMMDD-HHMMSS>.json (không xoá)."""
        self._nguoi(nguoi)
        with self._khoa(nguoi):
            p = self.p_state(nguoi)
            if not os.path.exists(p):
                raise DongHoLoi("Không có file trạng thái nào để bỏ.")
            try:
                self.doc_trang_thai(nguoi)
                raise DongHoLoi("File trạng thái vẫn đọc được (không hỏng): dùng Xong hoặc Hủy phiên.")
            except DongHoLoi as e:
                if not e.hong:
                    raise
            dst = os.path.join(self.dir, f"dang_chay_{nguoi}.hong-{self.gio.now().strftime('%Y%m%d-%H%M%S')}.json")
            os.replace(p, dst)
            return os.path.basename(dst)

    # ---------- Hủy (có xác nhận) ----------
    def huy_mo(self, nguoi):
        """Mở yêu cầu hủy: trả dict(ma, tom_tat). Mở yêu cầu mới thì yêu cầu cũ hết hiệu lực."""
        self._chan_dong()
        self._nguoi(nguoi)
        with self._khoa(nguoi):
            st, _c = self._nap(nguoi)
            tong = self.tong_chay(st)
            tt = (f"Bỏ phiên {nguoi} · {st.get('task') or st.get('dot') or '?'} · {st['dieu_kien']}: {len(st['mat'])} mặt đã khép, {fmt_giay(tong)}. "
                  f"KHÔNG ghi dòng nào vào timing_{nguoi}.csv.")
            it = self._huy.setdefault(nguoi, dot_anh.Pending()).open(nguoi=nguoi, phien=st["phien"])
            return dict(ma=it["token"], tom_tat=tt, rev=st["rev"])

    def huy_xac_nhan(self, nguoi, ma, chu, ly_do="", rev=None):
        """Hủy phiên nếu mã yêu cầu còn hiệu lực VÀ chữ gõ là HUY (không phân biệt hoa thường, nhận HỦY/HUỶ). Không ghi dòng nào vào timing_<người>.csv."""
        self._chan_dong()
        self._nguoi(nguoi)
        ly_do = _clean(ly_do, 200, "Lý do")
        with self._khoa(nguoi):
            st, _c = self._nap(nguoi)
            self._kiem_rev(st, rev)
            it = self._huy.get(nguoi)
            req = it.take(ma) if it else None
            if req is None or req.get("phien") != st["phien"]:
                raise DongHoLoi("Yêu cầu hủy đã hết hiệu lực (mở hộp xác nhận lại).")
            if khong_dau_hoa(chu) != "HUY":
                raise DongHoLoi("Chữ xác nhận phải là HUY: chưa hủy gì.")
            tong = self.tong_chay(st)
            row = dict(thoi_diem=ca_kho.iso(self.gio.now()), nguoi=nguoi, dieu_kien=st["dieu_kien"], task=st.get("task", ""), job=st.get("job", ""), khoi=st.get("khoi", ""),
                       phien=st["phien"], so_mat_bo=len(st["mat"]), giay_bo=round(tong, 1), ly_do=ly_do)
            self._noi_huy(nguoi, row)
            self._xoa_trang_thai(nguoi)
            self._cho_xong.pop(nguoi, None)
        return row

    def _noi_huy(self, nguoi, row):
        os.makedirs(self.dir, exist_ok=True)
        p = self.p_huy(nguoi)
        old = ""
        if os.path.exists(p):
            with open(p, encoding="utf-8", newline="") as f:
                old = f.read()
        if not old.strip():
            old = ",".join(HUY_COLS) + "\r\n"
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\r\n").writerow([ca_kho._formula_safe(row.get(c, "")) for c in HUY_COLS])
        ca_kho._atomic_write(p, (old + buf.getvalue()).encode("utf-8"))

    # ---------- Xong (lưu & xuất) ----------
    def xong_luu(self, nguoi, rev=None, tinh_mat_dang_lam=True, so_mat=None, nhan_file="auto", ghi_chu_phien=None, ngay=None):
        """Khép phiên, ghi gói kết quả và các dòng vào timing_<người>.csv một lần, nguyên tử; ghi xong mới xoá file trạng thái. Lỗi ghi thì giữ nguyên trạng thái.
        Còn cảnh báo chưa xử lý thì lần bấm đầu từ chối (cho=True), bấm lần hai (không đổi gì ở giữa) mới lưu. Trả dict(ok, tom_tat, csv, goi, canh_bao, thong_bao)."""
        self._chan_dong()
        self._nguoi(nguoi)
        with self._khoa(nguoi):
            st, _c = self._nap(nguoi)
            self._kiem_rev(st, rev)
            pend = self._chua_xu_ly(st)
            if pend and self._cho_xong.get(nguoi) != (st["phien"], st["rev"]):
                self._cho_xong[nguoi] = (st["phien"], st["rev"])
                raise DongHoLoi("Còn cảnh báo chưa xử lý (" + "; ".join(c["text"] for c in pend[:2]) + "). Chọn Sửa thời gian / Giữ nguyên, hoặc bấm Xong (lưu) thêm một lần "
                                "nữa để lưu kèm cảnh báo.", cho=True)
            tong = self.tong_chay(st)
            tail = tong - st["cat_active"] - st.get("tru_giay", 0.0)
            now_dt = self.gio.now()
            thong_bao = []
            faces = [dict(m) for m in st["mat"]]
            if faces and tinh_mat_dang_lam:
                if tail >= MAT_TOI_THIEU_GIAY:
                    seq = st["seq_dau"] + len(faces)
                    faces.append(dict(seq=seq, face_id=f"{st['khoi']}_{seq:02d}", giay=round(tail, 1), tam_dung=st["so_lan_tam_dung"] - st["cat_tam_dung"],
                                      ket_thuc=ca_kho.iso(now_dt), ghi_chu="", sua_tay=int(st.get("tru_giay", 0) > 0), tru=round(st.get("tru_giay", 0.0), 1)))
                else:
                    thong_bao.append(f"Mặt đang làm mới {tail:.1f} giây (dưới {MAT_TOI_THIEU_GIAY:g} giây) nên không tính.")
            elif faces:
                thong_bao.append("Mặt đang làm không được tính (đã bỏ tích).")
            giay_dem = sum(m["giay"] for m in faces) if faces else max(0.0, tail)
            n_khai = st["n_mat"]
            if so_mat not in (None, ""):
                try:
                    n_khai = int(so_mat)
                except (TypeError, ValueError):
                    raise DongHoLoi("Số mặt phải là số nguyên.")
                if not 1 <= n_khai <= N_MAT_MAX:
                    raise DongHoLoi(f"Số mặt phải từ 1 đến {N_MAT_MAX}.")
            if (faces and not any(m["giay"] > 0 for m in faces)) or giay_dem < MAT_TOI_THIEU_GIAY:
                raise DongHoLoi("Phiên rỗng (chưa đủ 2 giây hoặc không có mặt nào tính giờ): không ghi gì. Bấm Hủy phiên nếu không cần.")
            uoc = not faces
            if uoc and round(giay_dem / n_khai, 1) <= 0:
                raise DongHoLoi(f"Phiên {fmt_giay(giay_dem)} quá ngắn so với {n_khai} mặt (dưới 0,1 giây mỗi mặt): giảm số mặt hoặc Hủy phiên.")
            if ghi_chu_phien is not None:
                st["ghi_chu_phien"] = _clean(ghi_chu_phien, 200, "Ghi chú phiên")
            rows, tom = self._dong_csv(st, faces, uoc, n_khai, giay_dem, now_dt, ngay)
            nd, tb_goi = self._noi_dung_goi(st, faces, uoc, n_khai, giay_dem, now_dt, nhan_file)
            try:
                goi = goi_kq.ghi_goi(self.root, nd, ddmm=(ngay or now_dt).strftime("%d%m"))
            except goi_kq.GoiLoi as e:
                raise DongHoLoi(str(e))
            self._ghi_csv(nguoi, rows)
            self._xoa_trang_thai(nguoi)
            self._cho_xong.pop(nguoi, None)
            tom.update(canh_bao=nd["canh_bao"], co_nhan=nd.get("co_nhan", False), co_nhap=nd.get("co_nhap", False), n_ket_qua=len(nd["ket_qua"]),
                       nhan_file=nd.get("nhan_file", ""))
            return dict(ok=True, tom_tat=tom, csv=self.rel(self.p_csv(nguoi)), goi=goi, canh_bao=nd["canh_bao"], thong_bao=thong_bao + tb_goi)

    def _canh_bao_cuoi(self, st):
        ma = list(dict.fromkeys(st.get("canh_bao_ma", [])))
        for c in self.canh_bao(st):
            if c["ma"] not in ma:
                ma.append(c["ma"])
        if st.get("sua_tay") and "sua_tay" not in ma:
            ma.append("sua_tay")
        return [m for m in ma if m != "sua_tay"]

    def _dong_csv(self, st, faces, uoc, n_khai, giay_dem, now_dt, ngay):
        nguoi = st["nguoi"]
        canh = ";".join(self._canh_bao_cuoi(st))
        so_lan = st["so_lan_tam_dung"]
        gtd = round(self.tong_tam_dung(st), 1)
        bd, kt = st["bat_dau"], ca_kho.iso(now_dt)
        date = (ngay or now_dt).date().isoformat() if hasattr(ngay or now_dt, "date") else str(ngay)
        rows = []
        if uoc:
            moi = round(giay_dem / n_khai, 1)
            for i in range(n_khai):
                seq = st["seq_dau"] + i
                rows.append(dict(date=date, person=nguoi, condition=st["dieu_kien"], task=st.get("task", ""), job=st.get("job", ""), block=st["khoi"], seq=seq,
                                 face_id=f"{st['khoi']}_{seq:02d}", seconds=moi, warmup=0, interrupted=0,
                                 note="ước lượng chia đều" + (f" (sửa tay: đo gốc {st['ghi_sua'][0]['giay_do_goc']} giây)" if st.get("ghi_sua") else "")))
        else:
            for i, m in enumerate(faces):
                seq = m["seq"]
                note = m.get("ghi_chu", "")
                if m.get("sua_tay"):
                    note = (note + " " if note else "") + f"(sửa tay: đo gốc {round(m['giay'] + m.get('tru', 0.0), 1)} giây)"
                d = (ca_kho.parse_time(m.get("ket_thuc")) or now_dt).date().isoformat()
                rows.append(dict(date=d, person=nguoi, condition=st["dieu_kien"], task=st.get("task", ""), job=st.get("job", ""), block=st["khoi"], seq=seq,
                                 face_id=m["face_id"], seconds=round(m["giay"], 1), warmup=int(seq <= 2 or i == 0), interrupted=int(m.get("tam_dung", 0) > 0), note=note))
        n_rows = len(rows)
        for r in rows:
            r.update(phien=st["phien"], dot=st.get("dot", ""), bo_anh=st.get("bo_anh", ""), bat_dau=bd, ket_thuc=kt, so_lan_tam_dung=so_lan, giay_tam_dung=gtd,
                     so_mat_phien=n_rows, giay_phien=round(giay_dem, 1), ghi_chu_phien=st.get("ghi_chu_phien", ""), sua_tay=int(bool(st.get("sua_tay"))), canh_bao=canh,
                     nguon_ghi="dong_ho", uoc_luong_chia_deu=int(uoc))
            for c in ("task", "job", "block", "note", "ghi_chu_phien", "dot", "bo_anh"):
                r[c] = ca_kho._formula_safe(_clean(r.get(c, ""), 200, "Ô chữ"))
        tg_mat = [r["seconds"] for r in rows if r["warmup"] == 0]
        tom = dict(phien=st["phien"], n_mat=n_rows, n_tinh_gio=len(tg_mat), giay_tong=round(giay_dem, 1), phut_moi_mat=round((sum(tg_mat) / len(tg_mat)) / 60, 2) if tg_mat else None,
                   giay_moi_mat=round(sum(tg_mat) / len(tg_mat), 1) if tg_mat else None, uoc_luong=uoc, so_lan_tam_dung=so_lan, giay_tam_dung=gtd)
        return rows, tom

    def _noi_dung_goi(self, st, faces, uoc, n_khai, giay_dem, now_dt, nhan_file):
        cfg_path = os.path.join(self.root, "config", "m28_config.json")
        cfg, thong_bao = None, []
        try:
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, ValueError):
            thong_bao.append("Không đọc được config/m28_config.json: gói chỉ có thời gian, không có nhãn.")
        ket_qua, info = [], dict(co_nhan=False, co_nhap=False, nhan_file="", canh_bao=[])
        if cfg is not None:
            lp = self.tim_nhan(st["nguoi"], st.get("task", ""), nhan_file)
            try:
                ket_qua, info = goi_kq.xay_ket_qua(self.root, cfg, st["dieu_kien"], st.get("dot", ""), lp)
            except Exception as e:                                         # file nhãn hỏng không làm mất thời gian đã đo
                thong_bao.append(f"Không đọc được nhãn ({type(e).__name__}): gói chỉ có thời gian.")
                ket_qua, info = [], dict(co_nhan=False, co_nhap=False, nhan_file="", canh_bao=["nhan_loi"])
        if cfg is not None and not info["co_nhan"]:
            thong_bao.append("Chưa có nhãn đã xuất cho phiên này (raw/<task>_" + st["nguoi"] + "_<DDMM>.xml): gói chỉ có thời gian. Lần sau chạy collect --reviewer "
                             + st["nguoi"] + " TRƯỚC khi bấm Lưu số đo; gói này gửi nhóm trưởng kèm nhãn xuất riêng (raw/).")
        elif st["dieu_kien"] == "assisted" and not info["co_nhap"]:
            thong_bao.append("Không tìm thấy nháp của đợt (runs/<đợt>/xml/prelabel.xml): gói có nhãn cuối nhưng không có nháp, điểm đã sửa và NME của nháp.")
        mat_do = []
        if not uoc:
            mat_do = [dict(seq=m["seq"], face_id=m["face_id"], giay=round(m["giay"], 1), so_lan_tam_dung=int(m.get("tam_dung", 0)), ghi_chu=m.get("ghi_chu", ""),
                           warmup=int(m["seq"] <= 2 or i == 0)) for i, m in enumerate(faces)]
        canh = self._canh_bao_cuoi(st) + [c for c in info.get("canh_bao", []) if c not in ("chua_co_nhan",)]
        nd = dict(phien=st["phien"], nguoi=st["nguoi"], nhom=st["dieu_kien"], dot=st.get("dot", ""), bo_anh=st.get("bo_anh", ""), task=st.get("task", ""), job=st.get("job", ""),
                  so_mat=n_khai, giay_phien=round(giay_dem, 1), giay_tam_dung=round(self.tong_tam_dung(st), 1), so_lan_tam_dung=st["so_lan_tam_dung"],
                  bat_dau=st["bat_dau"], ket_thuc=ca_kho.iso(now_dt), uoc_luong_chia_deu=bool(uoc), mat_do=mat_do, canh_bao=sorted(set(canh)),
                  ghi_chu=st.get("ghi_chu_phien", ""), sua_tay=int(bool(st.get("sua_tay"))), tao_luc=ca_kho.iso(now_dt), nhan_file=info.get("nhan_file", ""),
                  co_nhan=bool(info.get("co_nhan")), co_nhap=bool(info.get("co_nhap")), cau_hinh=dict(so_diem=len(cfg["points"]) if cfg else 0,
                  nguong_sua=goi_kq.NGUONG_SUA_MAC_DINH), ket_qua=ket_qua)
        return nd, thong_bao

    def tim_nhan(self, nguoi, task, nhan_file="auto"):
        """Đường dẫn file nhãn của người: nhan_file cụ thể (tên file trong raw/) hoặc 'auto' = file mới nhất của người cho task."""
        raw = os.path.join(self.root, "raw")
        if nhan_file and nhan_file != "auto":
            p = os.path.join(raw, os.path.basename(nhan_file))
            return p if os.path.isfile(p) else None
        if not task:
            return None
        return collect_mod.latest_raw_files(task, raw).get(nguoi)

    def ung_vien_nhan(self, nguoi):
        """Các file nhãn trong raw/ có tên người này (không tính file _job<id>): [(tên file, mtime)] mới nhất trước."""
        out = []
        for p in glob.glob(os.path.join(glob.escape(os.path.join(self.root, "raw")), "*.xml")):
            m = collect_mod.RAW_RE.match(os.path.basename(p))
            if m and m.group("who") == nguoi:
                out.append((os.path.basename(p), os.path.getmtime(p)))
        return [n for n, _t in sorted(out, key=lambda x: -x[1])]

    # ---------- CSV timing_<người>.csv ----------
    def _doc_csv(self, nguoi):
        """(cột, [dict dòng]) của timing_<người>.csv, ([], []) nếu chưa có. Dòng sai chỉ được bỏ qua."""
        p = self.p_csv(nguoi)
        if not os.path.exists(p):
            return [], []
        try:
            with open(p, encoding="utf-8-sig", newline="") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError):
            return [], []
        if not text.strip():
            return [], []
        delim = ";" if text.splitlines()[0].count(";") > text.splitlines()[0].count(",") else ","
        rd = csv.DictReader(io.StringIO(text), delimiter=delim)
        cols = [(c or "").strip() for c in (rd.fieldnames or [])]
        return cols, [{(k or "").strip(): (v or "").strip() for k, v in r.items() if k is not None} for r in rd]

    def _ghi_csv(self, nguoi, rows):
        """Nối `rows` vào timing_<người>.csv nguyên tử: header đủ cột thì nối; đúng 12 cột facetimer thì giữ .bak rồi nâng cấp header (dòng cũ để trống cột thêm);
        header khác thì từ chối. Lỗi ghi (file đang mở...) thì DongHoLoi, trạng thái được giữ."""
        p = self.p_csv(nguoi)
        os.makedirs(self.dir, exist_ok=True)
        cols, old = self._doc_csv(nguoi)
        existing_text = ""
        if cols:
            if cols == CSV_COLS:
                pass
            elif cols == FACETIMER_COLS:
                bak = p + f".bak-{self.gio.now().strftime('%Y%m%d-%H%M%S')}"
                try:
                    with open(p, "rb") as f, open(bak, "wb") as g:
                        g.write(f.read())
                except OSError as e:
                    raise DongHoLoi(f"Không sao lưu được {self.rel(p)} trước khi thêm cột ({type(e).__name__}): chưa ghi gì, trạng thái vẫn giữ.")
            else:
                thieu = [c for c in FACETIMER_COLS if c not in cols]
                la = [c for c in cols if c not in CSV_COLS]
                raise DongHoLoi(f"{self.rel(p)} có tiêu đề lạ (thiếu cột: {', '.join(thieu) or 'không'}; cột lạ: {', '.join(la) or 'không'}). Không đụng vào file; "
                                "đổi tên hoặc chuyển file đó đi rồi bấm Xong (lưu) lại (trạng thái vẫn giữ).")
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\r\n")
        w.writerow(CSV_COLS)
        for r in old:
            w.writerow([r.get(c, "") for c in CSV_COLS])
        for r in rows:
            w.writerow([r.get(c, "") for c in CSV_COLS])
        existing_text = buf.getvalue()
        try:
            ca_kho._atomic_write(p, existing_text.encode("utf-8"))
        except OSError as e:
            raise DongHoLoi(f"Không ghi được {self.rel(p)} ({type(e).__name__}: file đang mở ở LibreOffice/Excel, hết chỗ hoặc không có quyền?). Chưa mất gì: đóng file rồi bấm Xong (lưu) lại.")

    def gan_day(self, nguoi, k=5):
        """k phiên lưu gần nhất của người (đọc từ CSV): [dict(date, task, khoi, n_mat, giay_tong, giay_moi_mat, uoc_luong)] mới nhất trước."""
        _cols, rows = self._doc_csv(nguoi)
        by = {}
        for r in rows:
            key = r.get("phien") or f"{r.get('date')}|{r.get('task')}|{r.get('block')}"
            by.setdefault(key, []).append(r)
        out = []
        for key, rs in by.items():
            sec = []
            for r in rs:
                try:
                    sec.append((float(r.get("seconds") or 0), int(float(r.get("warmup") or 0))))
                except ValueError:
                    pass
            tinh = [s for s, w in sec if w == 0]
            out.append(dict(phien=key, date=rs[-1].get("date", ""), task=rs[0].get("task", ""), khoi=rs[0].get("block", ""), n_mat=len(rs),
                            giay_tong=round(sum(s for s, _w in sec), 1), giay_moi_mat=round(sum(tinh) / len(tinh), 1) if tinh else None,
                            uoc_luong=str(rs[0].get("uoc_luong_chia_deu", "")) == "1"))
        out.sort(key=lambda d: (d["date"], d["phien"]), reverse=True)
        return out[:k]

    # ---------- đóng trang ----------
    def tu_tam_dung_tat_ca(self, ly_do="tat_trang"):
        """Tự tạm dừng mọi phiên ĐANG CHẠY trong outputs/timing (đóng trang rà soát, Ctrl+C). Trả [(người, giờ)] để in ra terminal. Bỏ qua phiên hỏng."""
        out = []
        for nguoi in NGUOI_OK:
            if not os.path.exists(self.p_state(nguoi)):
                continue
            try:
                with self._khoa(nguoi):
                    st, _c = self._nap(nguoi, bat_buoc=False)
                    if st is None or st["trang_thai"] != "chay":
                        continue
                    self._tam_dung_trong(st, ma=ly_do)
                    self._ghi(st, nguoi)
                    out.append((nguoi, ca_kho.iso(self.gio.now())[11:19]))
            except (DongHoLoi, OSError):
                continue
        return out

    def dang_chay_ai(self):
        """Người có phiên ĐANG CHẠY (trang_thai chay) trong outputs/timing; chỉ đọc, bỏ qua file hỏng."""
        out = []
        for nguoi in NGUOI_OK:
            try:
                st = self.doc_trang_thai(nguoi)
            except DongHoLoi:
                continue
            if st is not None and st["trang_thai"] == "chay":
                out.append(nguoi)
        return out

    def nhip(self, nguoi):
        """Nhịp đồng bộ (gọi từ gr.Timer): cập nhật lan_cuoi_thay tối đa 60 giây một lần, KHÔNG tăng rev. Trả khung nhìn."""
        try:
            st, changed = self._nap(nguoi, bat_buoc=False)
        except DongHoLoi:
            return self.xem(nguoi)
        if st is not None and not self.closing:
            moi = self.gio.epoch() - float(st.get("lan_cuoi_epoch") or 0) >= NHIP_DONG_BO_GIAY
            if moi or changed:
                try:
                    with self._khoa(nguoi):
                        st2, _c = self._nap(nguoi, bat_buoc=False)
                        if st2 is not None:
                            self._ghi(st2, nguoi, tang_rev=False)
                except (DongHoLoi, OSError):
                    pass
        return self.xem(nguoi)

    # ---------- xuất lại gói (khi lúc Xong chưa có nhãn) ----------
    def goi_da_luu(self, nguoi):
        """Các gói đã lưu của người trong outputs/ket_qua: [(tên không đuôi, nội dung)] mới nhất trước. Gói hỏng bị bỏ."""
        out = []
        d = os.path.join(self.root, goi_kq.THU_MUC)
        for p in sorted(glob.glob(os.path.join(glob.escape(d), f"ketqua_{nguoi}_*.json"))):
            try:
                nd, _w = goi_kq.doc_goi(p)
            except goi_kq.GoiLoi:
                continue
            out.append((os.path.basename(p)[:-5], nd))
        out.sort(key=lambda x: str(x[1].get("tao_luc")), reverse=True)
        return out

    def xuat_lai_goi(self, nguoi, ten, nhan_file="auto"):
        """Dựng lại gói của một phiên đã lưu (cùng mã phiên, cùng số đo thời gian) với nhãn hiện có: dùng khi lúc bấm Xong chưa collect. Không đụng timing_<người>.csv."""
        self._chan_dong()
        self._nguoi(nguoi)
        for t, nd in self.goi_da_luu(nguoi):
            if t == ten:
                break
        else:
            raise DongHoLoi("Không thấy gói đó (đã xoá hoặc hỏng).")
        try:
            with open(os.path.join(self.root, "config", "m28_config.json"), encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, ValueError):
            raise DongHoLoi("Không đọc được config/m28_config.json.")
        lp = self.tim_nhan(nguoi, nd.get("task", ""), nhan_file)
        ket_qua, info = goi_kq.xay_ket_qua(self.root, cfg, nd["nhom"], nd.get("dot", ""), lp)
        if not info["co_nhan"]:
            raise DongHoLoi(f"Vẫn chưa có file nhãn raw/{nd.get('task', '')}_{nguoi}_<DDMM>.xml: chạy collect --reviewer {nguoi} trước.")
        nd2 = dict(nd, ket_qua=ket_qua, co_nhan=True, co_nhap=bool(info["co_nhap"]), nhan_file=info["nhan_file"], tao_luc=ca_kho.iso(self.gio.now()))
        nd2["canh_bao"] = sorted(set(c for c in nd.get("canh_bao", []) if c not in ("thieu_nhap", "nhan_rong")) | set(info.get("canh_bao", [])))
        try:
            return goi_kq.ghi_goi(self.root, nd2, ddmm=ten.split("_")[2] if len(ten.split("_")) > 2 else None)
        except goi_kq.GoiLoi as e:
            raise DongHoLoi(str(e))


class _Khoa:
    """Khoá luồng + khoá file O_EXCL cho một người. Khoá file chỉ giữ trong lúc đọc-sửa-ghi; khoá của pid đã chết hoặc cũ hơn 30 giây là khoá mồ côi."""

    def __init__(self, dh, nguoi):
        self.dh, self.nguoi = dh, nguoi

    def __enter__(self):
        self.tl = self.dh._thread_lock(self.nguoi)
        self.tl.acquire()
        try:
            self._lay_file()
        except BaseException:
            self.tl.release()
            raise
        return self

    def _lay_file(self):
        os.makedirs(self.dh.dir, exist_ok=True)
        p = self.dh.p_khoa(self.nguoi)
        t_end = time.time() + 3.0
        while True:
            try:
                fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w") as f:
                    f.write(f"{os.getpid()} {time.time():.0f}")
                self.co = True
                return
            except FileExistsError:
                if self._mo_coi(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
                    continue
                if time.time() > t_end:
                    raise DongHoLoi("Đồng hồ đang bận ở một trang khác (khoá file): thử lại sau vài giây.")
                time.sleep(0.05)

    def _mo_coi(self, p):
        try:
            with open(p, encoding="utf-8") as f:
                pid_s, _s, t_s = f.read().partition(" ")
            cu = time.time() - float(t_s or 0) > KHOA_CU_GIAY
            return cu or not dang_chay.pid_alive(int(pid_s))
        except (OSError, ValueError):
            try:
                return time.time() - os.path.getmtime(p) > KHOA_CU_GIAY
            except OSError:
                return True

    def __exit__(self, *exc):
        try:
            os.remove(self.dh.p_khoa(self.nguoi))
        except OSError:
            pass
        self.tl.release()
        return False
