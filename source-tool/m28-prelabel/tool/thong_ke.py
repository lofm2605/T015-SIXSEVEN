"""Thống kê chỉ số của model và của quá trình gán nhãn M28 (đọc dữ liệu đã có; KHÔNG ghi vào runs\\, raw\\, final\\, data\\).

    python tool\\thong_ke.py [--luot R1 R2 ...] [--gom-ttest] [--timing <thư mục|file>] [--out outputs\\thong_ke]
        [--nguoi-ra P2 ...] [--luot-nhap <lượt chứa nháp cho nhãn thí nghiệm>] [--file-nhan raw\\x.xml ...]

Ghi outputs\\thong_ke\\<YYYYMMDD-HHMM>\\: thong_ke.html (một file tự chứa, sáng/tối theo hệ điều hành), mỗi bảng một CSV (utf-8-sig, ô chữ an toàn công thức)
và nme_nhap.csv (NME của nháp so với nhãn, mỗi mặt một dòng). Bốn nhóm số liệu:
  (1) chất lượng nháp: NME nháp so với nhãn sửa tay, TÁCH manual (đáp án trung thực) và assisted (nhãn bị neo theo nháp: chỉ là cận dưới);
  (2) cờ low_conf: % điểm bị cờ; có nhãn thì AUROC, recall, precision (tái dùng flag_eval);
  (3) tốc độ gán: theo ĐÚNG giao thức P5 (m28core.toc_do; TB nhân, KTC 90%, mục tiêu nhanh hơn >= 20%), thêm giây rà soát mỗi mặt (chỉ số KHÁC);
  (4) số lượng dữ liệu và tiến độ.
Quy tắc: mọi ô số đi kèm n; n < N_NHO (5) ghi "n quá nhỏ"; không có dữ liệu thì trạng thái trống có lời giải thích (cần file nào, ai làm ra), không bao giờ hiện 0 hay số giả;
Ttest ẩn mặc định (tập đo một lần); triage_auto (máy tự quyết) không tính là người rà; HTML xuất không có ảnh mặt, không mã tài xế, không đường dẫn tuyệt đối.
"""
import argparse
import csv
import datetime
import io
import json
import os
import shutil
import subprocess
import sys

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)
import ca_kho  # noqa: E402
import dot_anh  # noqa: E402
import nap_anh  # noqa: E402
from m28core import bang_mat, toc_do  # noqa: E402

N_NHO = 5                        # n nhỏ hơn: ghi "n quá nhỏ" thay cho tỉ lệ/khoảng tin cậy
N_SAI_TOI_THIEU = 10             # số điểm sai tối thiểu để báo AUROC
TOL_MAC_DINH = 3.0               # sai số chấp nhận (% IOD) khi config.tolerance còn null (flag_eval)
GIAY_RA_NGOAI_LAI = 120.0        # > ngần này giây rà/mặt: có thể nghỉ giữa chừng (guideline: <= 30 giây)
GIAY_RA_GUIDELINE = 30.0
MUC_TIEU_NHANH_HON = 20.0        # % nhanh hơn gán tay
MUC_TIEU_MAT_HONG = 10.0         # % IOD (eval50.BAD)
NGUONG_HIEU_NME = 0.5            # +0,5% IOD: hiệu NME ghép cặp assisted − manual
DOI_TUONG = {"nhan": "Nhận", "gan_tay": "Gán tay", "bo": "Bỏ", "chua_ra": "Chưa rà", "khong_thay_mat": "Không thấy mặt", "xoa_mem": "Đã xoá mềm"}
NGUON_VI = {"yawdd": "YawDD", "drivface": "DrivFace", "khong_ro": "Không rõ nguồn"}
DIEU_KIEN_VI = {"manual": "Gán tay từ đầu (manual)", "assisted": "Sửa nháp (assisted)", "khong_ro_dieu_kien": "Không rõ điều kiện"}
LOAI_MAT_VI = {"nhan": "Nhận", "gan_tay_co_nhap": "Gán tay có nháp", "gan_tay_trong": "Gán tay ảnh trống", "": "Nhãn thí nghiệm"}
CAN_DUOI = ("Chỉ có nhãn assisted: NME nháp-vs-assisted là CẬN DƯỚI (nhãn bị neo theo nháp, đo lượng người đã sửa chứ không phải sai số thật của nháp).")
KE_HOACH_MAT_MOI_KHOI, KE_HOACH_KHOI_DONG = 10, 2


def _trong(ly_do, can, ai):
    return dict(ly_do=ly_do, can=can, ai=ai)


def _pct(a, b):
    return None if not b else 100.0 * a / b


def _nho(n):
    return n < N_NHO


def _git_commit(project_root):
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=project_root, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else "không rõ"
    except (OSError, subprocess.SubprocessError):
        return "không rõ"


# ---------- (4) số lượng ----------
def _danh_muc(r, nguoi_ra):
    if r["xoa_mem"]:
        return "xoa_mem"
    dec, _who = bang_mat.quyet_dinh_cuoi(r, nguoi_ra)
    if dec:
        return dec
    return "khong_thay_mat" if r["no_face"] else "chua_ra"


def _bang_dem(rows, key, nguoi_ra, ten=lambda v: v):
    out = {}
    for r in rows:
        k = r[key] if key else "(tất cả)"
        d = out.setdefault(k, dict(ten=ten(k), tong=0, **{c: 0 for c in DOI_TUONG}))
        d["tong"] += 1
        d[_danh_muc(r, nguoi_ra)] += 1
    return [out[k] for k in sorted(out)]


def so_luong(bang, rows, nguoi_ra):
    run_rows = [r for r in rows if r["luot"]]
    chi_nhan = [r for r in rows if not r["luot"]]
    if not rows:
        return dict(trong=_trong("Chưa có mặt nào để đếm: chưa có lượt nào trong runs\\ (hoặc lượt đã chọn không có mặt).", "runs\\<lượt> đã chạy prepare (m28.py prepare)", "P1"))
    return dict(trong=None, tong_luot_mat=len(run_rows), mat_duy_nhat=bang.mat_duy_nhat(run_rows), chi_nhan=len(chi_nhan),
                khac_don_vi=len(run_rows) != bang.mat_duy_nhat(run_rows),
                tong=_bang_dem(run_rows, None, nguoi_ra)[0] if run_rows else None,
                theo_nguon=_bang_dem(run_rows, "nguon", nguoi_ra, lambda v: NGUON_VI.get(v, v)),
                theo_luot=_bang_dem(run_rows, "luot", nguoi_ra), theo_set=_bang_dem(run_rows, "set", nguoi_ra, lambda v: v or "(không có trong manifest)"))


# ---------- (1) chất lượng nháp ----------
def _tot_hon(e, cur):
    return (e["kind"] == "final", bang_mat._ngay_key(e["ngay"]), e["file"]) > (cur["kind"] == "final", bang_mat._ngay_key(cur["ngay"]), cur["file"])


def thu_nhan(bang, rows):
    """[(dòng, nhãn)] mỗi (mặt, điều kiện) một nhãn có sai số của nháp: mặt manifest tính theo tên manifest (không đếm hai lần giữa hai lượt), nhãn mới nhất / final thắng."""
    by = {}
    for r in rows:
        for e in r["nhan"]:
            s = e["nme"]
            if not s or not s.get("ok"):
                continue
            k = (r["mat"] if r["trong_manifest"] else (r["luot"], r["mat"]), e["dieu_kien"])
            if k not in by or _tot_hon(e, by[k][1]):
                by[k] = (r, e)
    return [by[k] for k in sorted(by, key=lambda k: (str(k[0]), k[1]))]


def _tb(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else None


def _trung_vi(v):
    v = sorted(x for x in v if x is not None)
    if not v:
        return None
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def tom_tat_nme(cap, bang):
    """cap: [(dòng, nhãn)] cùng một điều kiện. dict(n, nme_tb, nme_trung_vi, hong_pct, n_hong, nme_eye_tb, eye_open_tb, nhom{nhóm: tb}, vung{vùng: tb})."""
    import eval50
    s = [e["nme"] for _r, e in cap]
    nme = [x["nme"] for x in s]
    n_hong = sum(1 for v in nme if v >= eval50.BAD)
    return dict(n=len(s), nme_tb=_tb(nme), nme_trung_vi=_trung_vi(nme), hong_pct=_pct(n_hong, len(s)), n_hong=n_hong, nme_eye_tb=_tb([x["nme_eye"] for x in s]),
                eye_open_tb=_tb([x["eye_open_err"] for x in s]),
                nhom={g: _tb([x["nhom"].get(g) for x in s]) for g in bang.groups},
                nhom_n={g: sum(1 for x in s if x["nhom"].get(g) is not None) for g in bang.groups},
                vung={g: _tb([x["vung"].get(g) for x in s]) for g in bang.regions})


def _yeu_to(r, e, key):
    if key == "loai_mat":
        return LOAI_MAT_VI.get(e["loai_mat"], e["loai_mat"] or "Nhãn thí nghiệm")
    if key == "nguon":
        return NGUON_VI.get(r["nguon"], r["nguon"])
    if key == "nguoi_gan":
        return e["nguoi"]
    v = r.get(key)
    if key in bang_mat.FLAGS_MANIFEST:
        return "không rõ" if v is None else ("có" if v else "không")
    return v if v not in (None, "") else "không rõ"


YEU_TO = [("loai_mat", "Loại mặt trong task"), ("nguon", "Nguồn"), ("camera", "Camera"), ("set", "Tập gốc (set)"), ("pose", "Tư thế (nghiêng)"),
          ("expression", "Biểu cảm"), ("occlusion", "Che / kính râm"), ("illumination", "Tối / sáng"), ("blur", "Mờ"), ("glasses", "Kính"),
          ("nguoi_gan", "Người gán")]


def theo_yeu_to(cap):
    import eval50
    out = []
    for key, ten in YEU_TO:
        d = {}
        for r, e in cap:
            d.setdefault(_yeu_to(r, e, key), []).append(e["nme"]["nme"])
        for v in sorted(d):
            n = len(d[v])
            out.append(dict(yeu_to=ten, gia_tri=v, n=n, nho=_nho(n), nme_tb=None if _nho(n) else _tb(d[v]),
                            hong_pct=None if _nho(n) else _pct(sum(1 for x in d[v] if x >= eval50.BAD), n)))
    return out


def chat_luong_nhan(project_root):
    """Khối "chất lượng nhãn" đúng giao thức P5 (hiệu NME ghép cặp assisted − manual theo mặt, bootstrap 2.000 lần seed 28, cận 5/95, ngưỡng +0,5% IOD) từ
    outputs\\nme_per_face.csv của eval50. Chỉ ĐỌC file đó. Trả dict(trong=None, cot={...}) hoặc dict(trong=<trạng thái trống>)."""
    p = os.path.join(project_root, "outputs", "nme_per_face.csv")
    if not os.path.isfile(p):
        return dict(trong=_trong("Chưa có outputs\\nme_per_face.csv (NME của nhãn người so với đáp án vàng).",
                                 "outputs\\nme_per_face.csv do eval50.py ghi (python tool\\eval50.py --gt <đáp án vàng> --pred <nhãn> --condition manual|assisted --append)", "P3"))
    import numpy as np
    try:
        with open(p, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    except (OSError, UnicodeDecodeError, csv.Error):
        return dict(trong=_trong("Không đọc được outputs\\nme_per_face.csv.", "file CSV UTF-8 do eval50.py ghi", "P3"))
    need = {"face_id", "condition", "nme", "nme_eye"}
    if not rows or not need <= set(rows[0]):
        miss = sorted(need - set(rows[0] if rows else []))
        return dict(trong=_trong(f"outputs\\nme_per_face.csv thiếu cột: {', '.join(miss)}.", "đủ cột face_id, condition, nme, nme_eye", "P3"))
    cond = {}
    for r in rows:
        cond.setdefault(r["condition"], {})[r["face_id"]] = r
    out = dict(trong=None, cot={}, n_trung=len(rows) - sum(len(v) for v in cond.values()))
    rng = np.random.default_rng(toc_do.SEED)
    for col in ("nme", "nme_eye"):
        man, ass = cond.get("manual", {}), cond.get("assisted", {})
        diff = []
        for fid in sorted(set(man) & set(ass)):
            try:
                a, b = float(ass[fid][col]), float(man[fid][col])
            except (TypeError, ValueError):
                continue
            diff.append(a - b)
        diff = np.array(diff, float)
        if len(diff) == 0:
            out["cot"][col] = dict(n=0, ket_luan=None)
            continue
        boot = [rng.choice(diff, len(diff)).mean() for _ in range(toc_do.N_BOOT)]
        lo, hi = np.percentile(boot, [5, 95])
        kl = "dat" if hi <= NGUONG_HIEU_NME else "khong_dat" if lo > NGUONG_HIEU_NME else "chua_ket_luan"
        out["cot"][col] = dict(n=int(len(diff)), tb=float(diff.mean()), lo=float(lo), hi=float(hi), ket_luan=kl)
    if all(v["ket_luan"] is None for v in out["cot"].values()):
        return dict(trong=_trong("Chưa có mặt nào được chấm ở CẢ hai điều kiện manual và assisted trong outputs\\nme_per_face.csv.",
                                 "chạy eval50.py cho cả hai điều kiện (--condition manual rồi --condition assisted --append)", "P3"))
    return out


def chat_luong(bang, rows, project_root):
    cap = thu_nhan(bang, rows)
    n_khong_nhap = sum(1 for r in rows for e in r["nhan"] if e["nme"] is None)
    n_nhan = sum(len(r["nhan"]) for r in rows)
    if not cap:
        if n_nhan:
            return dict(trong=_trong(f"Có {n_nhan} nhãn nhưng chưa nhãn nào ghép được với nháp của máy ({n_khong_nhap} nhãn không có nháp liên kết).",
                                     "lượt chứa nháp: nhãn của task demo-… cần runs\\<lượt>\\push.json; nhãn thí nghiệm (m28-manual, m28-assisted…) cần chọn ô luot_nhap (--luot-nhap)", "P4"),
                        chat_luong_nhan=chat_luong_nhan(project_root))
        return dict(trong=_trong("Chưa có nhãn gán tay / sửa tay nào để so với nháp.",
                                 "raw\\<task>_<Pk>_<DDMM>.xml (P4: collect hoặc export.py; final\\ cho bản sửa lần hai)", "P4"),
                    chat_luong_nhan=chat_luong_nhan(project_root))
    out = dict(trong=None, n_nhan=n_nhan, n_khong_nhap=n_khong_nhap, theo_dieu_kien={}, yeu_to={}, tieu_de=None)
    for c in ("manual", "assisted", "khong_ro_dieu_kien"):
        sub = [x for x in cap if x[1]["dieu_kien"] == c]
        if sub:
            out["theo_dieu_kien"][c] = tom_tat_nme(sub, bang)
            out["yeu_to"][c] = theo_yeu_to(sub)
    out["tieu_de"] = "manual" if "manual" in out["theo_dieu_kien"] else ("assisted" if "assisted" in out["theo_dieu_kien"] else "khong_ro_dieu_kien")
    out["can_duoi"] = out["tieu_de"] == "assisted"
    out["chat_luong_nhan"] = chat_luong_nhan(project_root)
    out["cap"] = cap
    return out


def nme_nhap_rows(bang, cap):
    """Các dòng nme_nhap.csv: cột đầu TRÙNG tên và nghĩa với nme_per_face.csv của eval50 (pred = nháp, gt = nhãn); cột thêm chỉ nối ở cuối."""
    import eval50
    out = []
    for r, e in cap:
        s = e["nme"]
        d = dict(face_id=eval50.stem(r["anh_cvat"]), condition=e["dieu_kien"], nme=f"{s['nme']:.4f}", nme_eye="" if s["nme_eye"] is None else f"{s['nme_eye']:.4f}",
                 nme_p2p=f"{s['nme_p2p']:.4f}")
        for g in sorted(bang.regions):
            d[f"reg_{g}"] = "" if g not in s["vung"] else f"{s['vung'][g]:.4f}"
        d["eye_open_err"] = "" if s["eye_open_err"] is None else f"{s['eye_open_err']:.4f}"
        d["n_missing"] = s["n_missing"]
        d.update(luot=r["luot"], nguoi_gan=e["nguoi"], loai_mat=e["loai_mat"], hong=int(s["hong"]))
        for g in bang.groups:
            d[f"nhom_{g}"] = "" if s["nhom"].get(g) is None else f"{s['nhom'][g]:.4f}"
        out.append(d)
    return out


def nme_nhap_cols(bang):
    return (["face_id", "condition", "nme", "nme_eye", "nme_p2p"] + [f"reg_{g}" for g in sorted(bang.regions)] + ["eye_open_err", "n_missing"]
            + ["luot", "nguoi_gan", "loai_mat", "hong"] + [f"nhom_{g}" for g in bang.groups])


# ---------- (2) cờ low_conf ----------
BINS_CO = [(0, 0), (1, 5), (6, 10), (11, 15), (16, 20), (21, 30), (31, 50)]


def co_lowconf(bang, rows, cap):
    import flag_eval
    cfg = bang.cfg
    fl = [r for r in rows if r["n_co"] is not None and r["co_nhap"] and not r["xoa_mem"]]
    t_flip = cfg.get("t_flip")
    out = dict(trong=None, t_flip=t_flip, tolerance=cfg.get("tolerance"), tol_mac_dinh=TOL_MAC_DINH)
    out["luot_toan_false"] = sorted(l for l, i in bang.runs.items() if i["co_toan_false"] and any(r["luot"] == l for r in fl))
    if not fl:
        out["khong_dap_an"] = dict(trong=_trong("Chưa có mặt nào có cờ low_conf (chưa chạy prepare tới bước flags).", "runs\\<lượt>\\flags\\flags.json (m28.py prepare)", "P1"))
    else:
        names = bang.names
        gi, ri = bang_mat.group_idx(cfg), bang_mat.region_idx(cfg)
        tot_pts = len(fl) * len(names)
        flagged = sum(r["n_co"] for r in fl)
        by_g = {g: dict(pct=_pct(sum(r["n_co_nhom"][g] for r in fl), len(fl) * len(ix)), n_diem=len(fl) * len(ix)) for g, ix in gi.items()}
        by_v = {g: dict(pct=_pct(sum(r["n_co_vung"][g] for r in fl), len(fl) * len(ix)), n_diem=len(fl) * len(ix)) for g, ix in ri.items()}
        by_l = {}
        for r in fl:
            by_l.setdefault(r["luot"], []).append(r["n_co"])
        dist = [dict(khoang=f"{a}" if a == b else f"{a}–{b}", n=sum(1 for r in fl if a <= r["n_co"] <= b)) for a, b in BINS_CO]
        out["khong_dap_an"] = dict(trong=None, n_mat=len(fl), n_diem=tot_pts, pct=_pct(flagged, tot_pts), co_moi_mat=flagged / len(fl), theo_nhom=by_g, theo_vung=by_v,
                                   theo_luot=[dict(luot=l, n_mat=len(v), pct=_pct(sum(v), len(v) * len(names)), co_moi_mat=sum(v) / len(v)) for l, v in sorted(by_l.items())],
                                   phan_bo=dist)
    out["co_dap_an"] = {}
    for c in ("manual", "assisted"):
        pts = []
        for r, e in cap:
            if e["dieu_kien"] != c or r["diem_lat"] is None:
                continue
            err = e["nme"]["loi_diem"]
            for i, p in enumerate(cfg["points"]):
                if p["name"] in err:
                    pts.append((p["region"], r["diem_lat"][i], err[p["name"]], r["mat"] if r["trong_manifest"] else f"{r['luot']}/{r['mat']}", p.get("group") or p["region"]))
        if not pts:
            continue
        a = flag_eval.analyze(pts, TOL_MAC_DINH, cfg, t_flip)
        a["n_sai_nho"] = a["n_bad"] < N_SAI_TOI_THIEU
        a["nho_mat"] = _nho(a["n_faces"])
        for v in list(a["by_region"].values()) + list((a["by_group"] or {}).values()):
            v["nho"] = v["n_bad"] < N_SAI_TOI_THIEU
        n_low = [e["n_low_conf_bat"] for r, e in cap if e["dieu_kien"] == c]
        a["low_conf_nhan"] = dict(n_nhan=len(n_low), tb=_tb(n_low), tong=sum(n_low))
        out["co_dap_an"][c] = a
    if not out["co_dap_an"]:
        out["thieu_dap_an"] = _trong("Chưa có nhãn sửa tay ghép được với nháp (và ảnh lật) nên chưa tính được độ chính xác của cờ (AUROC, recall, precision).",
                                     "raw\\<task>_<Pk>_<DDMM>.xml (P4) và lượt chứa nháp (push.json hoặc luot_nhap)", "P4 / P2")
    return out


# ---------- (3) tốc độ ----------
def toc_do_muc(project_root, timing, manifest):
    try:
        files = toc_do.tim_file(project_root, timing)
    except toc_do.TocDoLoi as e:
        return dict(trong=_trong(str(e), "thư mục/file nằm trong thư mục dự án", "P5"), loi=str(e))
    if not files:
        return dict(trong=_trong("Chưa có file bấm giờ nào.", "timing_P1.csv … timing_P5.csv do facetimer.py ghi (P5: thí nghiệm ghép cặp 14–15/10); đặt ở source-tool\\m28-prelabel\\, "
                                 "outputs\\, raw\\ hoặc final\\", "P5"))
    try:
        rows = toc_do.doc_nhieu(files, lambda p: bang_mat.rel(project_root, p))
    except toc_do.TocDoLoi as e:
        return dict(trong=_trong(str(e), "đủ 12 cột của facetimer.py", "P5"), loi=str(e))
    res = toc_do.phan_tich(rows, manifest)
    res["files"] = [bang_mat.rel(project_root, p) for p in files]
    res["rows"] = rows
    res["trong"] = None if res["ok"] else _trong(res["ly_do_trong"] or "Chưa đủ dữ liệu.", "đủ dòng manual và assisted của ít nhất 3 người", "P5")
    return res


def giay_ra(bang, rows, nguoi_ra, toc):
    per, theo_luot = {}, {}
    for r in rows:
        for who, g in bang_mat.giay_ra(r, nguoi_ra):
            per.setdefault(who, []).append(g)
            theo_luot.setdefault((who, r["luot"]), []).append(g)
    if not per:
        return dict(trong=_trong("Chưa có giây rà soát nào (cột seconds của triage trống hoặc chưa ai rà).", "runs\\<lượt>\\review\\triage_<Pk>.csv do trang rà soát ghi (người rà bấm Nhận/Gán tay/Bỏ)", "P2"))
    allv = [v for vs in per.values() for v in vs]
    out = dict(trong=None, tong=toc_do.tom_tat_giay(allv, GIAY_RA_NGOAI_LAI),
               theo_nguoi=[dict(nguoi=w, **toc_do.tom_tat_giay(v, GIAY_RA_NGOAI_LAI)) for w, v in sorted(per.items())],
               theo_luot=[dict(nguoi=w, luot=l or "(chỉ có nhãn)", **toc_do.tom_tat_giay(v, GIAY_RA_NGOAI_LAI)) for (w, l), v in sorted(theo_luot.items())],
               nguong_ngoai_lai=GIAY_RA_NGOAI_LAI, guideline=GIAY_RA_GUIDELINE, day_du=None)
    if toc.get("ok") and out["tong"]["trung_vi"] is not None and toc["gio"] and toc["gio"]["manual"] and toc["gio"]["assisted"]:
        chi_phi = toc["gio"]["assisted"] + out["tong"]["trung_vi"]
        out["day_du"] = dict(sua_nhap=toc["gio"]["assisted"], ra=out["tong"]["trung_vi"], tong=chi_phi, manual=toc["gio"]["manual"],
                             nhanh_hon_pct=(1 - chi_phi / toc["gio"]["manual"]) * 100)
    return out


# ---------- (4) tiến độ ----------
def tien_do(project_root, bang, rows, toc, nguoi_ra):
    runs = []
    for l, info in sorted(bang.runs.items()):
        rd = os.path.join(bang.runs_root, l)
        per = []
        for who in info["nguoi_ra"]:
            if who == bang_mat.AUTO or (nguoi_ra and who not in nguoi_ra):
                continue
            c = dot_anh.counts(rd, who)
            per.append(dict(nguoi=who, da_ra=c["nhan"] + c["gan_tay"] + c["bo"], tong=c["total"], nhan=c["nhan"], gan_tay=c["gan_tay"], bo=c["bo"], chua_ra=c["chua_ra"]))
        try:
            marks = ca_kho.read_marks(rd) if os.path.isfile(ca_kho.ca_path(rd)) else []
        except nap_anh.RunError:
            marks = []
        ck = {}
        for m in marks:
            ck[m["nguoi"]] = ck.get(m["nguoi"], 0) + 1
        runs.append(dict(luot=l, nguoi=per, xong=os.path.isfile(os.path.join(rd, "review", "done.txt")), ca_kho=ck, task=((dot_anh.read_push(rd) or {}).get("task") or "")))
    labs = [dict(file=i["file"], task=i["task"], nguoi=i["nguoi"], ngay=i["ngay"], kind=i["kind"], dieu_kien=i["dieu_kien"], luot=i["luot"], n_anh=i["n_anh"],
                 n_khop=i["n_khop"], n_cu=i["n_cu"], ghi_chu=i["ghi_chu"]) for i in bang.labels]
    bam = None
    if toc.get("rows") is not None:
        by = {}
        for r in toc["rows"]:
            e = by.setdefault((r["person"], r["condition"]), dict(n=0, n_tinh=0))
            e["n"] += 1
            e["n_tinh"] += int(r["warmup"] == 0)
        ke_hoach = {f"P{k}" for k in range(1, 6)}
        bam = [dict(nguoi=p, dieu_kien=c, n=v["n"], n_tinh_gio=v["n_tinh"], ky_vong=KE_HOACH_MAT_MOI_KHOI if p in ke_hoach and c in toc_do.CONDITIONS else None,
                    ky_vong_tinh_gio=(KE_HOACH_MAT_MOI_KHOI - KE_HOACH_KHOI_DONG) if p in ke_hoach and c in toc_do.CONDITIONS else None) for (p, c), v in sorted(by.items())]
    return dict(trong=None, runs=runs, nhan=labs, bam_gio=bam,
                ghi_chu_ky_vong=("Kỳ vọng suy từ kế hoạch thí nghiệm: Pk gán tay khối Xk và sửa nháp khối X(k+1) (P5 sửa X1), 10 mặt mỗi khối, 2 mặt đầu là khởi động."))


# ---------- tổng hợp ----------
def tinh(project_root, luot=None, gom_ttest=False, nguoi_ra=(), luot_nhap=None, file_nhan=(), timing=None, now=None):
    """(thống kê dict, bảng mặt). Tính khi cần (tab chọn / CLI), không tính lúc mở trang. Chỉ đọc."""
    nguoi_ra = [w for w in (nguoi_ra or ()) if w and w != bang_mat.AUTO]
    bang = bang_mat.dung_bang(project_root, runs=luot or None, luot_nhap=luot_nhap or None, file_nhan=file_nhan or ())
    ttest_an = sum(1 for r in bang.rows if r["set"] == "Ttest") if not gom_ttest else 0
    rows = [r for r in bang.rows if gom_ttest or r["set"] != "Ttest"]
    manifest = bang_mat.read_manifest(project_root)
    now = now or datetime.datetime.now().astimezone()
    st = dict(meta=dict(ngay=now.strftime("%d/%m/%Y %H:%M"), ngay_ts=now.strftime("%Y%m%d-%H%M"), commit=_git_commit(project_root), config_version=bang.config_version,
                        t_flip=bang.t_flip, luot=sorted(bang.runs), luot_bo_qua=dict(bang.luot_bo_qua), gom_ttest=bool(gom_ttest), ttest_an=ttest_an, nguoi_ra=nguoi_ra,
                        luot_nhap=luot_nhap or "", canh_bao=list(bang.warnings), nhan_dung=[i["file"] for i in bang.labels if i["dieu_kien"] != "bo_qua" and not i["ghi_chu"].startswith("không đọc")],
                        co_manifest=bool(manifest)))
    st["so_luong"] = so_luong(bang, rows, nguoi_ra)
    st["chat_luong"] = chat_luong(bang, rows, project_root)
    cap = st["chat_luong"].get("cap", [])
    st["co"] = co_lowconf(bang, rows, cap)
    st["toc_do"] = toc_do_muc(project_root, timing, manifest)
    st["giay_ra"] = giay_ra(bang, rows, nguoi_ra, st["toc_do"])
    st["tien_do"] = tien_do(project_root, bang, rows, st["toc_do"], nguoi_ra)
    st["nme_nhap_rows"] = nme_nhap_rows(bang, cap)
    st["nme_nhap_cols"] = nme_nhap_cols(bang)
    return st, bang


# ---------- bảng CSV ----------
def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.4f}".rstrip("0").rstrip(".") if abs(v) < 1e6 else f"{v:.1f}"
    return v


def bang_csv(st, bang=None):
    """{tên file: (cột, [dict])}: mỗi bảng của trang một CSV (dấu chấm thập phân để máy đọc)."""
    T = {}
    sl = st["so_luong"]
    if not sl.get("trong"):
        cols = ["ten", "tong"] + list(DOI_TUONG)
        for k, key in (("so_luong_theo_nguon", "theo_nguon"), ("so_luong_theo_luot", "theo_luot"), ("so_luong_theo_set", "theo_set")):
            T[k] = (cols, sl[key])
    cl = st["chat_luong"]
    if not cl.get("trong"):
        T["chat_luong_tong"] = (["dieu_kien", "n", "nme_tb", "nme_trung_vi", "hong_pct", "n_hong", "nme_eye_tb", "eye_open_tb"],
                                [dict(dieu_kien=c, **{k: v[k] for k in ("n", "nme_tb", "nme_trung_vi", "hong_pct", "n_hong", "nme_eye_tb", "eye_open_tb")}) for c, v in cl["theo_dieu_kien"].items()])
        T["chat_luong_theo_nhom"] = (["dieu_kien", "nhom", "n", "nme_tb"], [dict(dieu_kien=c, nhom=g, n=v["nhom_n"][g], nme_tb=v["nhom"][g]) for c, v in cl["theo_dieu_kien"].items() for g in v["nhom"]])
        T["chat_luong_theo_vung"] = (["dieu_kien", "vung", "nme_tb"], [dict(dieu_kien=c, vung=g, nme_tb=v["vung"][g]) for c, v in cl["theo_dieu_kien"].items() for g in v["vung"]])
        T["chat_luong_theo_yeu_to"] = (["dieu_kien", "yeu_to", "gia_tri", "n", "nme_tb", "hong_pct"],
                                       [dict(dieu_kien=c, **{k: x[k] for k in ("yeu_to", "gia_tri", "n", "nme_tb", "hong_pct")}) for c, xs in cl["yeu_to"].items() for x in xs])
    cn = cl.get("chat_luong_nhan") or {}
    if cn and not cn.get("trong"):
        T["chat_luong_nhan"] = (["cot", "n", "hieu_tb", "can_duoi_5", "can_tren_95", "ket_luan"],
                                [dict(cot=c, n=v["n"], hieu_tb=v.get("tb"), can_duoi_5=v.get("lo"), can_tren_95=v.get("hi"), ket_luan=v["ket_luan"]) for c, v in cn["cot"].items()])
    co = st["co"]
    kd = co.get("khong_dap_an") or {}
    if kd and not kd.get("trong"):
        T["co_theo_nhom"] = (["nhom", "n_diem", "pct_bi_co"], [dict(nhom=g, n_diem=v["n_diem"], pct_bi_co=v["pct"]) for g, v in kd["theo_nhom"].items()])
        T["co_theo_vung"] = (["vung", "n_diem", "pct_bi_co"], [dict(vung=g, n_diem=v["n_diem"], pct_bi_co=v["pct"]) for g, v in kd["theo_vung"].items()])
        T["co_theo_luot"] = (["luot", "n_mat", "pct_bi_co", "co_moi_mat"], kd["theo_luot"])
        T["co_phan_bo"] = (["khoang", "n"], kd["phan_bo"])
    for c, a in (co.get("co_dap_an") or {}).items():
        T[f"co_dap_an_{c}"] = (["pham_vi", "ten", "auroc", "n_diem", "n_sai", "pct_sai"],
                               [dict(pham_vi="tong", ten="tong", auroc=a["auroc"], n_diem=a["n_points"], n_sai=a["n_bad"], pct_sai=a["bad_pct"])]
                               + [dict(pham_vi="vung", ten=g, auroc=v["auroc"], n_diem=v["n"], n_sai=v["n_bad"], pct_sai=v["bad_pct"]) for g, v in a["by_region"].items()]
                               + [dict(pham_vi="nhom", ten=g, auroc=v["auroc"], n_diem=v["n"], n_sai=v["n_bad"], pct_sai=v["bad_pct"]) for g, v in (a["by_group"] or {}).items()])
        T[f"co_nguong_{c}"] = (["phan_vi", "t_flip", "pct_bi_co", "recall_pct", "precision_pct", "co_moi_mat"], [dict(zip(("phan_vi", "t_flip", "pct_bi_co", "recall_pct", "precision_pct", "co_moi_mat"), r)) for r in a["table"]])
    td = st["toc_do"]
    if td.get("ok"):
        T["toc_do_r_i"] = (["nguoi", "manual_giay_tb", "assisted_giay_tb", "n_manual", "n_assisted", "r_i"],
                           [dict(nguoi=p, manual_giay_tb=e["manual"], assisted_giay_tb=e["assisted"], n_manual=e["n_manual"], n_assisted=e["n_assisted"], r_i=e["r"]) for p, e in td["nguoi"].items()])
        T["toc_do_tong"] = (["tb_nhan", "nhanh_hon_pct", "ktc90_duoi", "ktc90_tren", "ket_luan", "n_nguoi", "n_nguoi_r_nho_hon_1", "gio_tiet_kiem_1000_mat"],
                            [dict(tb_nhan=td["tb_nhan"], nhanh_hon_pct=td["nhanh_hon_pct"], ktc90_duoi=td["ktc90"][0], ktc90_tren=td["ktc90"][1], ket_luan=td["ket_luan"],
                                  n_nguoi=td["n_nguoi"], n_nguoi_r_nho_hon_1=td["n_r_nho_hon_1"], gio_tiet_kiem_1000_mat=(td["gio"] or {}).get("gio_1000"))])
        T["toc_do_m24"] = (["date", "person", "condition", "so_anh", "so_phut"], td["m24"])
        T["toc_do_ngoai_lai"] = (["person", "condition", "face_id", "seconds", "nguong"], td["ngoai_lai"])
        T["toc_do_gian_doan"] = (["person", "condition", "face_id", "seconds", "block"], td["gian_doan"])
        if td.get("nhom"):
            T["toc_do_nhom"] = (["nhom", "manual_giay_tb", "assisted_giay_tb", "n_manual", "n_assisted", "gio_tiet_kiem_1000_mat"],
                                [dict(nhom=k, manual_giay_tb=v["manual"], assisted_giay_tb=v["assisted"], n_manual=v["n_manual"], n_assisted=v["n_assisted"], gio_tiet_kiem_1000_mat=v["gio_1000"])
                                 for k, v in td["nhom"].items()])
    gr = st["giay_ra"]
    if not gr.get("trong"):
        cols = ["nguoi", "n", "trung_vi", "q1", "q3", "phut_100", "n_ngoai_lai"]
        T["giay_ra_theo_nguoi"] = (cols, gr["theo_nguoi"])
        T["giay_ra_theo_luot"] = (["nguoi", "luot"] + cols[1:], gr["theo_luot"])
    td2 = st["tien_do"]
    T["tien_do_ra_soat"] = (["luot", "nguoi", "da_ra", "tong", "nhan", "gan_tay", "bo", "chua_ra", "xong"],
                            [dict(luot=r["luot"], xong=int(r["xong"]), **p) for r in td2["runs"] for p in r["nguoi"]])
    T["tien_do_file_nhan"] = (["file", "task", "nguoi", "ngay", "kind", "dieu_kien", "luot", "n_anh", "n_khop", "n_cu", "ghi_chu"], td2["nhan"])
    if td2["bam_gio"]:
        T["tien_do_bam_gio"] = (["nguoi", "dieu_kien", "n", "n_tinh_gio", "ky_vong", "ky_vong_tinh_gio"], td2["bam_gio"])
    return T


def csv_bytes(cols, rows):
    rows = [{c: _fmt(r.get(c)) for c in cols} for r in rows]
    return ca_kho.csv_text(cols, rows, safe=True).encode("utf-8-sig")


# ---------- xuất tĩnh ----------
def xuat(project_root, st, out_root=None, bang=None, trong_du_an=True):
    """Ghi outputs\\thong_ke\\<YYYYMMDD-HHMM>\\ (hoặc out_root\\...). Trả (thư mục, [tên file]). Chỉ ghi dưới thư mục đó. trong_du_an=True (giao diện): out_root phải nằm
    trong thư mục dự án (realpath + commonpath); CLI cho người dùng tự chọn nơi ghi (ví dụ thư mục tạm khi tự kiểm)."""
    import thong_ke_html
    base = os.path.join(project_root, "outputs", "thong_ke")
    if out_root:
        base = out_root if os.path.isabs(out_root) else os.path.join(project_root, out_root)
        if trong_du_an and not nap_anh._inside(base, project_root):
            raise ValueError("Thư mục xuất nằm ngoài thư mục dự án: từ chối.")
    d = os.path.join(base, st["meta"]["ngay_ts"])
    n = 1
    while os.path.exists(d):
        n += 1
        d = os.path.join(base, f"{st['meta']['ngay_ts']}-{n}")
    files = {"thong_ke.html": thong_ke_html.trang_tinh(st).encode("utf-8")}
    for name, (cols, rows) in bang_csv(st, bang).items():
        files[name + ".csv"] = csv_bytes(cols, rows)
    files["nme_nhap.csv"] = csv_bytes(st["nme_nhap_cols"], st["nme_nhap_rows"])
    tmp = d + f".tmp{os.getpid()}"
    os.makedirs(tmp)
    try:
        for fn, data in files.items():
            with open(os.path.join(tmp, fn), "wb") as f:
                f.write(data)
        os.replace(tmp, d)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return d, sorted(files)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Thống kê chỉ số model và tốc độ gán M28; xuất CSV + HTML tĩnh (không ảnh mặt) vào outputs\\thong_ke\\<ngày-giờ>\\. Chỉ đọc dữ liệu.")
    ap.add_argument("--luot", nargs="*", default=None, help="chỉ các lượt này (mặc định: mọi lượt trong runs\\)")
    ap.add_argument("--gom-ttest", action="store_true", help="gồm cả Ttest (tập đo một lần; mặc định ẩn)")
    ap.add_argument("--timing", default=None, help="thư mục hoặc file timing_P*.csv thêm (trong thư mục dự án); mặc định tìm ở m28-prelabel\\, outputs\\, raw\\, final\\")
    ap.add_argument("--out", default=None, help="thư mục gốc xuất (mặc định outputs\\thong_ke)")
    ap.add_argument("--nguoi-ra", nargs="*", default=None, help="chỉ tính quyết định/giây rà của những người này (triage_auto không tính)")
    ap.add_argument("--luot-nhap", default=None, help="lượt chứa NHÁP cho nhãn thí nghiệm không có push.json (m28-manual, m28-assisted…)")
    ap.add_argument("--file-nhan", nargs="*", default=None, help="thêm file nhãn (trong thư mục dự án)")
    ap.add_argument("--project", default=os.path.dirname(TOOL_DIR), help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    try:
        st, bang = tinh(a.project, a.luot, a.gom_ttest, a.nguoi_ra or (), a.luot_nhap, a.file_nhan or (), a.timing)
        d, files = xuat(a.project, st, a.out, bang, trong_du_an=False)
    except (bang_mat.BangLoi, ValueError, OSError) as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        return 2
    print(f"Đã ghi {bang_mat.rel(a.project, d)} ({len(files)} file: thong_ke.html, nme_nhap.csv và {len(files) - 2} bảng CSV)")
    for w in st["meta"]["canh_bao"]:
        print("Cảnh báo:", w)
    for k, ten in (("chat_luong", "Chất lượng nháp"), ("co", "Cờ low_conf"), ("toc_do", "Tốc độ gán"), ("giay_ra", "Giây rà soát"), ("so_luong", "Số lượng")):
        t = st[k].get("trong")
        if t:
            print(f"{ten}: chưa có số — {t['ly_do']} Cần: {t['can']} ({t['ai']}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
