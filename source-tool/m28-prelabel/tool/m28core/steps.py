"""Các bước của m28. Mỗi hàm nhận (args, out) và trả True chỉ khi xong thật.

Phần của P1 (crop, mediapipe, flags, overlays, review auto/excel, ghi XML) viết ở đây.
Phần của người khác gọi qua module riêng, thiếu thì báo rõ tên module cần:
  m28core.mapping.apply_map   (P3)  — 478 điểm → {tên điểm: [x, y]} ảnh cắt 512
  m28core.autoqc.run          (P4, tuỳ chọn) — QC 5 kiểm; thiếu thì chạy kiểm tối thiểu
  m28core.push.push           (P4)  — tạo task CVAT và nhập XML
  m28core.collect.collect     (P4)  — xuất nhãn từ task
  review_app.py               (P2)  — trang rà soát Gradio (--review ui)
Không import torch ở bất cứ đâu trong tool/.
"""
import csv
import glob
import importlib
import io
import json
import os
import re
import subprocess
import sys
from xml.sax.saxutils import quoteattr

import numpy as np

from wflw import SIDE_SCALE, square_crop

OUT = 512
IMG_EXT = (".png", ".jpg", ".jpeg")
NEN_GAN_TAY = ("guong", "don_cuc", "diem_khong_hop_le")   # mã lỗi autoqc làm gợi ý "nên gán tay" (giả định, chờ P4)
DECISIONS = ("nhan", "gan_tay", "bo")
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"


# ---------- tiện ích ----------
def _jload(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _jsave(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


def _run_dir(args):
    return os.path.join("runs", args.run)


def _need(module, why):
    try:
        return importlib.import_module(module)
    except ModuleNotFoundError as e:
        if e.name != module:
            raise
        raise SystemExit(f"Thiếu {module} ({why}). Chưa có thì chờ người phụ trách commit.")


def _need_file(path, why):
    if not os.path.exists(path):
        raise SystemExit(f"Thiếu file {path} ({why}).")
    return path


def make_landmarker(model_path, num_faces=1):
    alt = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), os.path.basename(model_path))
    if not os.path.exists(model_path) and os.path.exists(alt):      # gói giao khách: model nằm cạnh m28.py
        model_path = alt
    _need_file(model_path, f"tải từ {MODEL_URL}")
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision
    opts = vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=model_path),
        running_mode=vision.RunningMode.IMAGE, num_faces=num_faces)
    return vision.FaceLandmarker.create_from_options(opts)


def run_mp(lm, rgb):
    """478 điểm theo pixel, hoặc None nếu không thấy mặt."""
    import mediapipe as mp
    img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
    res = lm.detect(img)
    if not res.face_landmarks:
        return None
    h, w = rgb.shape[:2]
    return [[p.x * w, p.y * h] for p in res.face_landmarks[0]]


def detect_box(lm, rgb, run=None):
    """Khung bao 478 điểm. Không thấy thì thêm viền xám rồi thử lại. Trả (x0, y0, x1, y1) hoặc None."""
    run = run or run_mp                 # tra tên lúc gọi để test thay được run_mp
    pts = run(lm, rgb)
    pad = 0
    if pts is None:
        pad = max(rgb.shape[:2]) // 4
        padded = np.full((rgb.shape[0] + 2 * pad, rgb.shape[1] + 2 * pad, 3), 128, np.uint8)
        padded[pad:pad + rgb.shape[0], pad:pad + rgb.shape[1]] = rgb
        pts = run(lm, padded)
        if pts is None:
            return None
    a = np.asarray(pts, float) - pad
    return (*a.min(0), *a.max(0))


def _read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:      # utf-8-sig: file Excel có BOM
        return list(csv.DictReader(f))


def load_items(args):
    """Danh sách mặt của lượt chạy: dict(name, path, rel, box|None). rel = đường dẫn ảnh gốc tính từ --images."""
    manifest = {}
    if os.path.exists(args.manifest):
        for m in _read_csv(args.manifest):
            manifest[(m["wflw_image"], int(m["wflw_line"]))] = m
    if args.list:
        wanted = [(r["wflw_image"], int(r["wflw_line"])) for r in _read_csv(args.list)]
    elif args.set:
        if not manifest:
            raise SystemExit(f"--set cần {args.manifest} (không thấy file)")
        wanted = list(manifest)
    elif args.images:
        if args.box == "wflw":
            raise SystemExit("--box wflw cần --list (hoặc --set) để lấy hộp mặt từ manifest.csv")
        files = sorted(g for ext in ("jpg", "jpeg", "png")
                       for g in glob.glob(os.path.join(args.images, "**", f"*.{ext}"), recursive=True))
        return _unique([dict(name=os.path.splitext(os.path.basename(p))[0], path=p, box=None,
                             rel=os.path.relpath(p, args.images).replace(os.sep, "/")) for p in files])
    else:
        raise SystemExit("Cần --images (thư mục ảnh), hoặc --list kèm --images, hoặc --set.")
    if not args.images:
        raise SystemExit("Cần --images (thư mục WFLW_images hoặc ảnh khách).")
    items = []
    for key in wanted:
        m = manifest.get(key)
        if args.set and (m is None or m["set"] not in args.set):
            continue
        if args.box == "wflw" and m is None:
            raise SystemExit(f"--box wflw cần {args.manifest} có dòng {key}")
        name = m["file"][:-4] if m else os.path.splitext(os.path.basename(key[0]))[0]
        box = tuple(float(m[c]) for c in ("x0", "y0", "x1", "y1")) if m else None
        items.append(dict(name=name, path=os.path.join(args.images, *key[0].split("/")), box=box, rel=key[0]))
    return _unique(items)


def _unique(items):
    seen = {}
    for it in items:
        if it["name"] in seen:
            raise SystemExit(f"Hai mặt cùng tên {it['name']!r} ({seen[it['name']]} và {it['rel']}): ảnh cắt sẽ đè nhau. "
                             "Dùng --list có manifest.csv (tên F_001…) hoặc đổi tên ảnh.")
        seen[it["name"]] = it["rel"]
    return items


def _stem(name):
    base, ext = os.path.splitext(name.strip())
    return base if ext.lower() in IMG_EXT else name.strip()


def _base(path):
    return re.split(r"[\\/]", path)[-1]


# ---------- prepare ----------
def crop(args, out, landmarker_factory=None):
    import cv2
    items = load_items(args)
    os.makedirs(os.path.join(out, "images"), exist_ok=True)
    meta, no_face = {}, []
    lm = (landmarker_factory or make_landmarker)(args.model) if args.box == "auto" else None
    try:
        for it in items:
            bgr = cv2.imread(it["path"])
            if bgr is None:
                no_face.append((it["name"], "khong_doc_duoc_anh"))
                continue
            box = it["box"] if args.box == "wflw" else detect_box(lm, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            if box is None:
                no_face.append((it["name"], "khong_thay_mat"))
                continue
            img, _, (left, top, k), _ = square_crop(bgr, box, np.zeros((1, 2), np.float32))
            cv2.imwrite(os.path.join(out, "images", it["name"] + ".png"), img)
            meta[it["name"]] = dict(src=os.path.abspath(it["path"]), rel=it["rel"], left=left, top=top, k=k,
                                    w=bgr.shape[1], h=bgr.shape[0])
    finally:
        if lm is not None and hasattr(lm, "close"):
            lm.close()
    _jsave(os.path.join(out, "meta.json"), meta)
    with open(os.path.join(out, "box.txt"), "w", encoding="utf-8") as f:      # push cần biết XML theo ảnh cắt hay ảnh gốc
        f.write(args.box)
    _write_no_face(args, no_face, "crop")
    print(f"crop: {len(meta)} mặt, {len(no_face)} không dùng được")
    return True


def _write_no_face(args, rows, step):
    path = os.path.join(_run_dir(args), "no_face.csv")
    old = []
    if os.path.exists(path):
        with open(path, encoding="utf-8", newline="") as f:
            old = [r for r in csv.reader(f) if r and r[0] != "name" and r[2:3] != [step]]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "reason", "step"])
        w.writerows(old)
        w.writerows([n, why, step] for n, why in rows)


def mediapipe(args, out, landmarker_factory=None):
    import cv2
    rd = _run_dir(args)
    meta = _jload(os.path.join(rd, "crop", "meta.json"))
    pred, no_face = {}, []
    lm = (landmarker_factory or make_landmarker)(args.model)
    try:
        for name in meta:
            rgb = cv2.cvtColor(cv2.imread(os.path.join(rd, "crop", "images", name + ".png")), cv2.COLOR_BGR2RGB)
            orig = run_mp(lm, rgb)
            if orig is None:
                no_face.append((name, "khong_thay_mat"))
                continue
            pred[name] = dict(orig=orig, flip=run_mp(lm, rgb[:, ::-1]))   # flip: toạ độ ảnh lật, chưa bỏ lật
    finally:
        if hasattr(lm, "close"):
            lm.close()
    _jsave(os.path.join(out, "pred478.json"), pred)
    _write_no_face(args, no_face, "mediapipe")
    print(f"mediapipe: {len(pred)} mặt, {len(no_face)} không thấy mặt")
    return True


def map50(args, out):
    mapping = _need("m28core.mapping", "P3: apply_map(pts478, map, config, flipped=False)")
    cfg = _jload(_need_file(args.config, "m28_config.json của P3, đóng băng 12/10"))
    mp_map = _jload(_need_file(args.map, "map_mp50.json của P3"))
    names = [p["name"] for p in cfg["points"]]
    pred = _jload(os.path.join(_run_dir(args), "mediapipe", "pred478.json"))

    def conv(pts, flipped):
        r = mapping.apply_map(np.asarray(pts, float), mp_map, cfg, flipped=flipped)
        miss = [n for n in names if n not in r]
        if miss:
            raise SystemExit(f"apply_map thiếu điểm {miss[:3]}… so với config")
        return {n: [float(r[n][0]), float(r[n][1])] for n in names}

    res = {n: dict(orig=conv(p["orig"], False), flip=conv(p["flip"], True) if p["flip"] else None)
           for n, p in pred.items()}
    _jsave(os.path.join(out, "mp50.json"), res)
    print(f"map50: {len(res)} mặt")
    return True


def flags(args, out):
    """low_conf của từng điểm: lệch giữa ảnh gốc và ảnh lật (đã bỏ lật) / khoảng cách hai mắt > t_flip.
    t_flip = null (chưa họp chốt): mọi cờ = false."""
    cfg = _jload(args.config)
    names = [p["name"] for p in cfg["points"]]
    eye_r, eye_l = cfg["iod_points"]
    t = cfg.get("t_flip")
    mp50 = _jload(os.path.join(_run_dir(args), "map50", "mp50.json"))
    res = {}
    for name, p in mp50.items():
        if t is None:
            res[name] = [False] * len(names)
        elif not p["flip"]:
            res[name] = [True] * len(names)               # không có ảnh lật: coi mọi điểm đáng ngờ
        else:
            o = np.array([p["orig"][n] for n in names], float)
            f = np.array([p["flip"][n] for n in names], float)
            iod = np.linalg.norm(np.array(p["orig"][eye_r]) - np.array(p["orig"][eye_l])) or 1.0
            res[name] = [bool(v) for v in np.linalg.norm(o - f, axis=1) / iod > float(t)]
    _jsave(os.path.join(out, "flags.json"), res)
    n = np.mean([sum(v) for v in res.values()]) if res else 0
    print(f"flags: trung bình {n:.1f} cờ/mặt" + (" (t_flip = null nên mọi cờ = false)" if t is None else ""))
    return True


def autoqc(args, out):
    """Ghi autoqc.csv: name, suggestion (on / can_xem / nen_gan_tay), n_flags, decision, reason, seconds, problems.
    Ba cột decision, reason, seconds để trống: mẫu cho người rà điền bằng Excel (--review excel)."""
    qc = None
    try:
        qc = importlib.import_module("m28core.autoqc")
    except ModuleNotFoundError as e:
        if e.name != "m28core.autoqc":
            raise
    cfg = _jload(args.config)
    names = [p["name"] for p in cfg["points"]]
    rd = _run_dir(args)
    mp50 = _jload(os.path.join(rd, "map50", "mp50.json"))
    fl = _jload(os.path.join(rd, "flags", "flags.json"))
    rows = []
    for name, p in mp50.items():
        a = np.array([p["orig"][n] for n in names], float)
        why = []
        if not np.isfinite(a).all():
            why.append("diem_khong_hop_le")
        elif ((a < -0.1 * OUT) | (a > 1.1 * OUT)).any():
            why.append("diem_ngoai_anh")
        if qc is not None:
            why += list(qc.run(name, a, cfg))
        nf = sum(fl[name])
        sug = "nen_gan_tay" if any(w.startswith(NEN_GAN_TAY) for w in why) else "can_xem" if why or nf else "on"
        rows.append([name + ".png", sug, nf, "", "", "", ";".join(why)])
    with open(os.path.join(out, "autoqc.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "suggestion", "n_flags", "decision", "reason", "seconds", "problems"])
        w.writerows(rows)
    print(f"autoqc: {sum(1 for r in rows if r[1] != 'on')}/{len(rows)} mặt cần xem hoặc nên gán tay"
          + ("" if qc else " (chưa có m28core.autoqc của P4, chỉ kiểm tối thiểu)"))
    return True


def overlays(args, out):
    import cv2
    cfg = _jload(args.config)
    names = [p["name"] for p in cfg["points"]]
    rd = _run_dir(args)
    mp50 = _jload(os.path.join(rd, "map50", "mp50.json"))
    fl = _jload(os.path.join(rd, "flags", "flags.json"))
    for name, p in mp50.items():
        img = cv2.imread(os.path.join(rd, "crop", "images", name + ".png"))
        for i, n in enumerate(names):
            x, y = p["orig"][n]
            col = (0, 0, 255) if fl[name][i] else (0, 200, 0)       # đỏ: low_conf
            cv2.circle(img, (int(round(x)), int(round(y))), 3, col, -1)
            cv2.putText(img, str(i + 1), (int(x) + 4, int(y) - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.35, col, 1)
        cv2.imwrite(os.path.join(out, name + ".png"), img)
    print(f"overlays: {len(mp50)} ảnh chồng")
    return True


# ---------- review ----------
def _autoqc_rows(rd):
    """{tên không đuôi: gợi ý}; chưa có autoqc.csv thì rỗng (mọi mặt coi là Nhận)."""
    path = os.path.join(rd, "autoqc", "autoqc.csv")
    return {_stem(r["name"]): r["suggestion"] for r in _read_csv(path)} if os.path.exists(path) else {}


def _queue(args):
    rd = _run_dir(args)
    fl = _jload(os.path.join(rd, "flags", "flags.json"))
    sug = _autoqc_rows(rd)
    rank = {"nen_gan_tay": 0, "can_xem": 1}
    names = sorted(fl, key=lambda n: (rank.get(sug.get(n), 2), -sum(fl[n]), n))   # đáng ngờ lên đầu
    return names, fl, sug


def _no_face(args):
    """{tên: lý do} từ no_face.csv (một tên chỉ một dòng, dù nằm ở bước nào)."""
    path = os.path.join(_run_dir(args), "no_face.csv")
    return {r["name"]: r["reason"] for r in reversed(_read_csv(path))} if os.path.exists(path) else {}


def triage_path(args, rd):
    """File triage: --review-file (tìm như gõ, rồi trong runs/<run>/review/), không có thì triage_<reviewer|auto>.csv."""
    rev = os.path.join(rd, "review")
    if args.review_file:
        for p in (args.review_file, os.path.join(rev, args.review_file)):
            if os.path.exists(p):
                return p
        return args.review_file if os.path.dirname(args.review_file) else os.path.join(rev, args.review_file)
    return os.path.join(rev, f"triage_{'auto' if args.review == 'auto' else args.reviewer}.csv")


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
        latest[_stem(r[ci])] = (get(di).lower(), get(ri))
    return latest


def review(args, out):
    rd = _run_dir(args)
    names, fl, sug = _queue(args)
    path = triage_path(args, rd)
    if args.review == "auto":
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["name", "decision", "reason", "seconds"])
            for n in names:
                w.writerow([n + ".png", "gan_tay" if sug.get(n) == "nen_gan_tay" else "nhan", "", ""])
            for n, why in _no_face(args).items():
                if n not in fl:
                    w.writerow([n + ".png", "bo", why, ""])
        print(f"review auto: theo gợi ý autoqc (chỉ để chạy thử/demo, không có người rà), ghi {path}")
        return True
    if args.review == "excel":
        if not os.path.exists(path):
            print(f"Chưa có {path}. Mở {os.path.join(rd, 'autoqc', 'autoqc.csv')} bằng Excel, điền cột decision "
                  f"(nhan / gan_tay / bo) và reason, xem ảnh chồng trong {os.path.join(rd, 'overlays')}, "
                  f"lưu dạng CSV UTF-8 thành {path}, rồi chạy lại đúng lệnh.")
            return False
        done = read_triage(path)
        missing = [n for n in names if done.get(n, ("",))[0] not in DECISIONS]
        if missing:
            print(f"Còn {len(missing)} mặt chưa có quyết định (nhan / gan_tay / bo), ví dụ: {missing[:3]}")
            return False
        return True
    app = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "review_app.py")
    _need_file(app, "trang rà soát của P2")
    if os.path.exists(os.path.join(out, "done.txt")):           # --force review: xoá done.txt cũ, chỉ tin nút Xong lần này
        os.remove(os.path.join(out, "done.txt"))
    subprocess.call([sys.executable, app, rd, args.reviewer])
    if not os.path.exists(os.path.join(out, "done.txt")):
        print("Trang rà soát đã đóng mà chưa bấm Xong.")
        return False
    return True


# ---------- push / collect ----------
def image_xml(frame_id, name, point_names, pts, low, width, height):
    out = [f'<image id="{frame_id}" name={quoteattr(name)} width="{width}" height="{height}">',
           '  <skeleton label="face50">']
    for n, (x, y), f in zip(point_names, pts, low):
        out.append(f'    <points label="{n}" occluded="0" outside="0" points="{x:.2f},{y:.2f}">'
                   f'<attribute name="low_conf">{"true" if f else "false"}</attribute></points>')
    out += ['  </skeleton>', '</image>']
    return "\n".join(out)


def _file_name(name, m, mode):
    """Tên file ảnh tải lên CVAT = tên ảnh trong XML."""
    return name + ".png" if mode == "wflw" else _base(m.get("rel") or m["src"])


def _upload_path(args, rd, name, m, mode):
    if mode == "wflw":
        return os.path.abspath(os.path.join(rd, "crop", "images", name + ".png"))
    if args.images and m.get("rel"):
        p = os.path.join(args.images, *m["rel"].split("/"))
        if os.path.exists(p):
            return p
    return m["src"]


def build_xml(mode, nhan, meta, mp50, fl, cfg, path):
    """mode wflw: toạ độ ảnh cắt 512, tên name.png. mode auto: toạ độ ảnh gốc (x_cắt / k + left, kẹp vào mép)."""
    names = [p["name"] for p in cfg["points"]]
    parts = ['<?xml version="1.0" encoding="utf-8"?>', '<annotations>', '  <version>1.1</version>']
    for fid, n in enumerate(nhan):
        m = meta[n]
        if mode == "wflw":
            pts, w, h = [mp50[n]["orig"][p] for p in names], OUT, OUT
        else:
            w, h = m["w"], m["h"]
            pts = [(min(max(mp50[n]["orig"][p][0] / m["k"] + m["left"], 0), w - 1),
                    min(max(mp50[n]["orig"][p][1] / m["k"] + m["top"], 0), h - 1)) for p in names]
        parts.append(image_xml(fid, _file_name(n, m, mode), names, pts, fl[n], w, h))
    parts.append('</annotations>')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


def push(args, out):
    rd = _run_dir(args)
    cfg = _jload(args.config)
    pipe = _jload(args.pipeline) if os.path.exists(args.pipeline) else {}
    triage = read_triage(_need_file(triage_path(args, rd), "kết quả bước review"))
    meta = _jload(os.path.join(rd, "crop", "meta.json"))
    mp50 = _jload(os.path.join(rd, "map50", "mp50.json"))
    fl = _jload(os.path.join(rd, "flags", "flags.json"))
    box_file = os.path.join(rd, "crop", "box.txt")
    mode = open(box_file, encoding="utf-8").read().strip() if os.path.exists(box_file) else args.box
    if len(args.task) > 1:
        raise SystemExit("push chỉ nhận một --task")
    dec = lambda n: triage.get(n, ("", ""))[0]                    # noqa: E731
    nhan = [n for n in meta if dec(n) == "nhan" and n in mp50]
    tay = [n for n in meta if dec(n) == "gan_tay" or (dec(n) == "nhan" and n not in mp50)]
    for n in meta:
        if dec(n) == "nhan" and n not in mp50:
            print(f"Cảnh báo: {n} được chọn Nhận nhưng MediaPipe không thấy mặt, đưa vào Gán tay.")
    no_face = _no_face(args)
    lost = [n for n in no_face if n not in meta and dec(n) == "gan_tay"]
    if lost:
        print(f"Cảnh báo: {len(lost)} mặt chọn Gán tay nhưng không có ảnh cắt (không đọc được/không thấy mặt ở bước crop), "
              f"không tải lên được: {lost[:3]}")
    rejected = [(n, triage[n][1]) for n in triage if dec(n) == "bo"] + \
               [(n, why) for n, why in no_face.items() if dec(n) not in DECISIONS]
    if not nhan and not tay:
        raise SystemExit("Không có mặt nào để đẩy lên (cả nhóm nhận và gán tay đều trống).")
    files = {}
    for n in nhan + tay:
        files.setdefault(_file_name(n, meta[n], mode), []).append(n)
    dup = {f: v for f, v in files.items() if len(v) > 1}
    if dup:
        raise SystemExit(f"Tên ảnh trùng, CVAT không nhận hai ảnh cùng tên: {dup}. Mỗi ảnh gốc chỉ được một mặt "
                         "lên task (chuyển mặt kia sang Bỏ trong triage) hoặc dùng --box wflw (ảnh cắt, tên khác nhau).")
    with open(os.path.join(out, "manual_list.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(_file_name(n, meta[n], mode) for n in tay))
    with open(os.path.join(out, "rejected.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "reason"])
        w.writerows(rejected)
    xml_path = os.path.join(rd, "xml", "prelabel.xml")
    build_xml(mode, nhan, meta, mp50, fl, cfg, xml_path)
    print(f"push: {len(nhan)} mặt nhận, {len(tay)} mặt gán tay, {len(rejected)} bỏ, XML ({mode}): {xml_path}")
    if args.dry_run:
        print("Chạy thử (--dry-run): đã ghi XML, không đẩy lên CVAT.")
        return False
    nhan_imgs = [_upload_path(args, rd, n, meta[n], mode) for n in nhan]
    tay_imgs = [_upload_path(args, rd, n, meta[n], mode) for n in tay]
    gone = [p for p in nhan_imgs + tay_imgs if not os.path.exists(p)]
    if gone:
        raise SystemExit(f"Không thấy {len(gone)} ảnh để tải lên, ví dụ {gone[0]}. Thêm --images <thư mục ảnh gốc> đúng máy này.")
    mod = _need("m28core.push", "P4: push(run_dir, task_name, nhan_imgs, tay_imgs, xml_path, project, prefix, label_json)")
    task_name = args.task[0] if args.task else f"{pipe.get('prefix', 'demo-')}{args.run}"
    mod.push(rd, task_name, nhan_imgs, tay_imgs, xml_path, project=pipe.get("project", "m28"),
             prefix=pipe.get("prefix", "demo-"), label_json=os.path.join("config", "face50_label.json"))
    return True


def collect(args, out):
    mod = _need("m28core.collect", "P4: collect(args)")
    return mod.collect(args)
