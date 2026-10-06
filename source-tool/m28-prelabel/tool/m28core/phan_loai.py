"""Phân loại mặt của một lượt thành Nhận / Gán tay / Bỏ / Đã xoá: MỘT hàm thuần dùng chung cho steps.push và trang rà soát
(hộp xác nhận "Đẩy lên CVAT" đếm bằng đúng hàm này, không viết lại logic). Chỉ thư viện chuẩn, không đọc file.

Cũng chứa các hàm đọc thuần dùng chung (read_triage, read_no_face) để trang rà soát và steps đọc đúng như nhau.
"""
import csv
import io
import os

DECISIONS = ("nhan", "gan_tay", "bo")
IMG_EXT = (".png", ".jpg", ".jpeg")


def stem(name):
    """Tên không đuôi ảnh (đuôi .png/.jpg/.jpeg); tên khác giữ nguyên."""
    base, ext = os.path.splitext(str(name).strip())
    return base if ext.lower() in IMG_EXT else str(name).strip()


def read_triage(path):
    """{tên không đuôi: (quyết định, lý do)}. Chịu BOM, dấu ; của Excel, có/không dòng tiêu đề; dòng sau đè dòng trước."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        text = f.read()
    first = text.splitlines()[0] if text.strip() else ""
    delim = ";" if first.count(";") > first.count(",") else ","
    rows = [r for r in csv.reader(io.StringIO(text), delimiter=delim) if any(c.strip() for c in r)]
    ci, di, ri = 0, 1, 2
    if rows and "decision" in [c.strip().lower() for c in rows[0]]:
        h = [c.strip().lower() for c in rows.pop(0)]
        ci, di, ri = h.index("name") if "name" in h else 0, h.index("decision"), h.index("reason") if "reason" in h else -1
    latest = {}
    for r in rows:
        if r[0].strip().lower() == "name":
            continue
        get = lambda i: r[i].strip() if 0 <= i < len(r) else ""      # noqa: E731
        latest[stem(r[ci])] = (get(di).lower(), get(ri))
    return latest


def read_no_face(run_dir):
    """{tên: lý do} từ no_face.csv (một tên chỉ một dòng, dù nằm ở bước nào), CHƯA trừ mặt xoá mềm."""
    path = os.path.join(run_dir, "no_face.csv")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["name"]: r["reason"] for r in reversed(rows)}


def classify(triage, meta, mp50, no_face, excluded=frozenset()):
    """triage {tên: (quyết định, lý do)}; meta/mp50 chứa khoá tên (đúng thứ tự meta.json); no_face {tên: lý do}; excluded: tên bị xoá mềm.

    Trả dict:
      nhan      mặt chọn Nhận và có nháp (mp50), theo thứ tự meta
      tay       mặt chọn Gán tay, và mặt chọn Nhận nhưng không có nháp (đưa sang Gán tay), theo thứ tự meta
      nhan_khong_nhap  tên các mặt chọn Nhận nhưng không có nháp (cảnh báo)
      lost      mặt chọn Gán tay nhưng không có ảnh cắt (không tải lên được)
      rejected  [(tên, lý do)] mặt Bỏ (kèm mặt no_face chưa có quyết định)
      removed   [(tên, "da_xoa")] mặt bị xoá mềm (không tải lên)
    Mặt bị xoá mềm không bao giờ nằm trong nhan/tay/lost/rejected."""
    excluded = set(excluded)
    dec = lambda n: triage.get(n, ("", ""))[0]                    # noqa: E731
    names = [n for n in meta if n not in excluded]
    nhan = [n for n in names if dec(n) == "nhan" and n in mp50]
    tay = [n for n in names if dec(n) == "gan_tay" or (dec(n) == "nhan" and n not in mp50)]
    no_draft = [n for n in names if dec(n) == "nhan" and n not in mp50]
    lost = [n for n in no_face if n not in meta and n not in excluded and dec(n) == "gan_tay"]
    rejected = [(n, triage[n][1]) for n in triage if dec(n) == "bo" and n not in excluded] + \
               [(n, why) for n, why in no_face.items() if dec(n) not in DECISIONS and n not in excluded]
    universe = set(meta) | set(no_face) | set(triage)
    removed = [(n, "da_xoa") for n in sorted(excluded & universe)]
    return dict(nhan=nhan, tay=tay, nhan_khong_nhap=no_draft, lost=lost, rejected=rejected, removed=removed)


def n_jobs(n_nhan, n_tay, job_size=8):
    """Số job dự kiến: nhóm job_size mặt Nhận + một job Gán tay riêng (nếu có)."""
    return -(-n_nhan // job_size) + (1 if n_tay else 0)
