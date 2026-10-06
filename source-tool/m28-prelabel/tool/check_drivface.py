"""Kiểm nhanh khách quan, KHÔNG cần gán tay: so 50 điểm của ta với 5 điểm mốc của DrivFace (606 ảnh, 4 tài xế). Chỉ để tham khảo.

    python tool\\check_drivface.py --drivface <thư mục DrivFace> [--model face_landmarker.task] [--limit N] [--out outputs\\drivface_errors.csv]

Chạy giống `prepare --box auto`: detect_box -> square_crop 512 -> MediaPipe trên ảnh cắt -> apply_map (ánh xạ chọn đỉnh mới) -> đổi về toạ độ
khung gốc (x / k + left, y / k + top). Cùng 478 điểm đó chạy thêm ánh xạ ridge học trên WFLW cũ (tool\\legacy_wflw: map_mp50_wflw.json) để thấy
thay đổi. Bộ 5 điểm của DrivFace: tâm mắt R/L, mũi, khoé miệng R/L; có định nghĩa riêng (không phải 50 điểm của ta, không phải đáp án). Vì vậy:
  * chỉ để tham khảo, không dùng thay đáp án 50 điểm, không dùng số này chỉnh đỉnh trừ lỗi thô rõ ràng;
  * tâm mắt DrivFace so với trung bình 4 điểm mắt của ta (p33-p36 / p37-p40) và với tâm iris MediaPipe (468 / 473) để biết sai số NỀN của chính đáp án DrivFace;
  * mũi so với CẢ p29 (chóp, đỉnh 1) và p31 (chân giữa, đỉnh 2): xem cái nào khớp định nghĩa DrivFace hơn;
  * khoé miệng so với p41 / p45;
  * quy ước bên được kiểm bằng dữ liệu trước khi ghép (RE có nằm nửa trái ảnh trên ảnh nhìn thẳng không);
  * chuẩn hoá bằng IOD = khoảng cách hai tâm mắt CỦA DRIVFACE (khác IOD khoé mắt ngoài của eval50): ảnh nhìn trái/phải IOD co lại nên % lớn hơn.
Báo trung vị / trung bình / p90 theo điểm, theo nhóm hướng nhìn (label 1 nhìn phải, 2 thẳng, 3 nhìn trái) và theo tài xế.

Dữ liệu DrivFace: "free for academic usage" (liên hệ tác giả nếu dùng mục đích khác), chỉ dùng nội bộ nhóm, không đăng, không commit ảnh hay kết quả theo ảnh.
"""
import argparse
import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

PT_KEYS = ("RE", "LE", "N", "RM", "LM")
# điểm so sánh: (tên, điểm DrivFace tham chiếu)
COMPARE = (("eye_R", "RE"), ("eye_L", "LE"), ("iris_R", "RE"), ("iris_L", "LE"),
           ("nose_tip_p29", "N"), ("nose_base_p31", "N"), ("mouth_R", "RM"), ("mouth_L", "LM"))
OLD_ONLY_SKIP = ("iris_R", "iris_L")        # iris không có trong bộ 50 điểm nên không có bản ridge cũ


def read_drivpoints(path):
    """Đọc drivPoints.txt (CSV; cột fileName có dấu cách cuối và không có .jpg). Trả list dict(name, subject, label, ang, box, pts{RE,LE,N,RM,LM})."""
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            r = {k.strip(): (v if k.strip() == "fileName" else (v or "").strip()) for k, v in r.items() if k}
            if not r.get("fileName") or not r["fileName"].strip():
                continue
            g = lambda k: float(r[k])                         # noqa: E731
            rows.append(dict(name=r["fileName"], subject=int(float(r["subject"])), label=int(float(r["label"])), ang=float(r["ang"]),
                             box=(g("xF"), g("yF"), g("wF"), g("hF")),
                             pts={"RE": (g("xRE"), g("yRE")), "LE": (g("xLE"), g("yLE")), "N": (g("xN"), g("yN")),
                                  "RM": (g("xRM"), g("yRM")), "LM": (g("xLM"), g("yLM"))}))
    return rows


def find_image(img_dir, name):
    """Ảnh của một dòng: tên trong CSV + '.jpg' (tên thật có dấu cách trước .jpg); không có thì thử bỏ/thêm dấu cách."""
    base = name.rstrip()
    for cand in (name + ".jpg", base + " .jpg", base + ".jpg"):
        p = os.path.join(img_dir, cand)
        if os.path.exists(p):
            return p
    return None


def side_convention(rows):
    """Kiểm quy ước bên của DrivFace trên ảnh nhìn thẳng (label 2): tỉ lệ ảnh có RE ở nửa trái hơn LE và RM hơn LM (R = nửa trái ảnh nếu gần 1)."""
    fr = [r for r in rows if r["label"] == 2] or rows
    eye = np.mean([r["pts"]["RE"][0] < r["pts"]["LE"][0] for r in fr])
    mouth = np.mean([r["pts"]["RM"][0] < r["pts"]["LM"][0] for r in fr])
    return float(eye), float(mouth), len(fr)


def ours_five(pts50, cfg, pts478=None):
    """Điểm của ta tương ứng 5 điểm DrivFace (toạ độ bất kỳ, miễn cùng hệ): tâm mắt = trung bình 4 điểm mắt, mũi (p29 chóp, p31 chân giữa),
    khoé miệng p41/p45, tâm iris 468/473 nếu có pts478. Chọn điểm theo region/line/tên trong config (R = bên người, nửa trái ảnh)."""
    def mean_of(prefix_line):
        names = [p["name"] for p in cfg["points"] if p["line"] == prefix_line]
        return np.mean([pts50[n] for n in names], axis=0)
    by_num = {p["name"].split("_")[0]: p["name"] for p in cfg["points"]}
    out = {"eye_R": mean_of("eye_R"), "eye_L": mean_of("eye_L"),
           "nose_tip_p29": np.asarray(pts50[by_num["p29"]], float), "nose_base_p31": np.asarray(pts50[by_num["p31"]], float),
           "mouth_R": np.asarray(pts50[by_num["p41"]], float), "mouth_L": np.asarray(pts50[by_num["p45"]], float)}
    if pts478 is not None:
        out["iris_R"], out["iris_L"] = np.asarray(pts478[468], float), np.asarray(pts478[473], float)
    return out


def point_errors(ours, ref):
    """{tên so sánh: lỗi % IOD DrivFace}, IOD = khoảng cách hai tâm mắt DrivFace (RE, LE)."""
    iod = float(np.hypot(ref["RE"][0] - ref["LE"][0], ref["RE"][1] - ref["LE"][1]))
    if iod <= 1e-9:
        return None
    return {n: float(np.hypot(ours[n][0] - ref[k][0], ours[n][1] - ref[k][1])) / iod * 100 for n, k in COMPARE if n in ours}


def point_offsets(ours, ref):
    """{tên: (dx, dy) % IOD DrivFace}: độ lệch CÓ DẤU (ta - DrivFace, x sang phải, y xuống) để thấy lệch hệ thống (ví dụ DrivFace đặt mốc lệch một bên)."""
    iod = float(np.hypot(ref["RE"][0] - ref["LE"][0], ref["RE"][1] - ref["LE"][1]))
    if iod <= 1e-9:
        return None
    return {n: ((ours[n][0] - ref[k][0]) / iod * 100, (ours[n][1] - ref[k][1]) / iod * 100) for n, k in COMPARE if n in ours}


def stats(values):
    v = np.asarray(values, float)
    return dict(n=len(v), median=float(np.median(v)), mean=float(v.mean()), p90=float(np.percentile(v, 90))) if len(v) else dict(n=0)


def group_table(per_image, key, point_names):
    """per_image: [dict(label, subject, err{tên: %})] -> {nhóm: {điểm: stats}}."""
    groups = {}
    for r in per_image:
        groups.setdefault(r[key], []).append(r)
    return {g: {n: stats([r["err"][n] for r in rs if n in r["err"]]) for n in point_names} for g, rs in sorted(groups.items())}


def summarize(per_image, point_names):
    return {n: stats([r["err"][n] for r in per_image if n in r["err"]]) for n in point_names}


def format_table(title, table_new, table_old, names, out=print):
    out(title)
    out("  điểm              mới: trung vị  trung bình  p90   |  cũ (ridge WFLW): trung vị  trung bình  p90")
    for n in names:
        a = table_new[n]
        if not a["n"]:
            continue
        b = table_old.get(n) if table_old else None
        old = f"{b['median']:10.1f} {b['mean']:11.1f} {b['p90']:6.1f}" if b and b["n"] else "         -           -      -"
        out(f"  {n:<16} {a['median']:11.1f} {a['mean']:11.1f} {a['p90']:6.1f}   |  {old}")


def process(rows, img_dir, model, cfg, new_map, old_map=None, old_cfg=None, limit=None, log=print):
    """Chạy toàn bộ: trả (per_image mới, per_image cũ hoặc None, no_face[], thiếu ảnh[]). Cần cv2 + mediapipe."""
    import cv2
    from m28core import steps
    from m28core.cat_mat import square_crop
    from m28core.mapping import apply_map
    old_apply = None
    if old_map is not None:
        sys.path.insert(0, os.path.join(HERE, "legacy_wflw"))
        import mapping_ridge
        old_apply = mapping_ridge.apply_map
    lm = steps.make_landmarker(model)
    new_res, old_res, no_face, no_img = [], [], [], []
    try:
        for i, r in enumerate(rows[:limit] if limit else rows):
            p = find_image(img_dir, r["name"])
            if p is None:
                no_img.append(r["name"])
                continue
            bgr = cv2.imread(p)
            box = steps.detect_box(lm, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)) if bgr is not None else None
            if box is None:
                no_face.append(r["name"])
                continue
            crop, _, (left, top, k), _ = square_crop(bgr, box, np.zeros((1, 2), np.float32))
            pts = steps.run_mp_padded(lm, cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            if pts is None:
                no_face.append(r["name"])
                continue
            pts = np.asarray(pts, float)
            to_frame = lambda a: {n: (np.asarray(v, float) / k + [left, top]) for n, v in a.items()}  # noqa: E731
            frame478 = pts / k + [left, top]
            for res, fn in ((new_res, lambda: apply_map(pts, new_map, cfg)),
                            (old_res, (lambda: old_apply(pts, old_map, old_cfg)) if old_apply else None)):
                if fn is None:
                    continue
                five = ours_five(to_frame(fn()), cfg, frame478 if res is new_res else None)
                err = point_errors(five, r["pts"])
                if err is not None:
                    res.append(dict(name=r["name"], label=r["label"], subject=r["subject"], err=err, off=point_offsets(five, r["pts"])))
            if (i + 1) % 100 == 0:
                log(f"  ... {i + 1}/{len(rows)} ảnh")
    finally:
        if hasattr(lm, "close"):
            lm.close()
    return new_res, (old_res if old_apply else None), no_face, no_img


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="So 50 điểm của ta với 5 điểm mốc DrivFace (chỉ để tham khảo)")
    ap.add_argument("--drivface", required=True, help="thư mục DrivFace có drivPoints.txt và imgs\\DrivImages")
    ap.add_argument("--model", default="face_landmarker.task")
    ap.add_argument("--config", default=os.path.join("config", "m28_config.json"))
    ap.add_argument("--map", default=os.path.join("config", "map_mp50.json"))
    ap.add_argument("--old-map", default=os.path.join(HERE, "legacy_wflw", "map_mp50_wflw.json"), help="ánh xạ ridge WFLW cũ để so ('' = không so)")
    ap.add_argument("--old-config", default=os.path.join(HERE, "legacy_wflw", "m28_config_wflw.json"))
    ap.add_argument("--limit", type=int, help="chỉ chạy N ảnh đầu (thử nhanh)")
    ap.add_argument("--out", help="ghi lỗi từng ảnh ra CSV (ví dụ outputs\\drivface_errors.csv; không commit)")
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as f:
        cfg = json.load(f)
    with open(a.map, encoding="utf-8") as f:
        new_map = json.load(f)
    old_map = old_cfg = None
    if a.old_map and os.path.exists(a.old_map):
        with open(a.old_map, encoding="utf-8") as f:
            old_map = json.load(f)
        with open(a.old_config, encoding="utf-8") as f:
            old_cfg = json.load(f)
    pts_path = os.path.join(a.drivface, "drivPoints.txt")
    img_dir = os.path.join(a.drivface, "imgs", "DrivImages")
    if not os.path.exists(pts_path) or not os.path.isdir(img_dir):
        sys.exit(f"Không thấy {pts_path} hoặc {img_dir}: --drivface là thư mục DrivFace đã giải nén.")
    rows = read_drivpoints(pts_path)
    eye, mouth, n = side_convention(rows)
    print(f"{len(rows)} dòng drivPoints. Quy ước bên (trên {n} ảnh nhìn thẳng): RE ở nửa trái hơn LE: {100 * eye:.0f}%, RM hơn LM: {100 * mouth:.0f}% "
          f"-> {'RE/RM = bên R của ta (nửa trái ảnh), ghép trực tiếp' if eye > 0.9 and mouth > 0.9 else 'KHÔNG như dự kiến: đổi chiều ghép trước khi tin số'}")
    if not (eye > 0.9 and mouth > 0.9):
        sys.exit(1)
    new_res, old_res, no_face, no_img = process(rows, img_dir, a.model, cfg, new_map, old_map, old_cfg, a.limit)
    print(f"Chấm được {len(new_res)} ảnh; không thấy mặt: {len(no_face)} {no_face[:3]}; không có file ảnh: {len(no_img)}")
    names = [n for n, _ in COMPARE]
    old_sum = summarize(old_res, names) if old_res else None
    format_table(f"\nTHEO ĐIỂM (% IOD DrivFace, {len(new_res)} ảnh):", summarize(new_res, names), old_sum, names)
    label_name = {1: "label 1 nhìn phải", 2: "label 2 thẳng", 3: "label 3 nhìn trái"}
    out_bias = ", ".join(f"{n} ({np.median([r['off'][n][0] for r in new_res if n in r['off']]):+.1f}, {np.median([r['off'][n][1] for r in new_res if n in r['off']]):+.1f})"
                         for n in names)
    print(f"\nLệch có dấu trung vị của ánh xạ mới (dx, dy; % IOD DrivFace; dx > 0: lệch sang phải ảnh, dy > 0: lệch xuống): {out_bias}")
    for key, title in (("label", "hướng nhìn"), ("subject", "tài xế")):
        tn, to = group_table(new_res, key, names), (group_table(old_res, key, names) if old_res else {})
        for g in tn:
            format_table(f"\nNHÓM {title} {label_name.get(g, g) if key == 'label' else 'tài xế ' + str(g)} (n={tn[g][names[0]]['n']}):", tn[g], to.get(g), names)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["name", "label", "subject"] + [f"new_{n}" for n in names] + [f"old_{n}" for n in names])
            olds = {r["name"]: r for r in (old_res or [])}
            for r in new_res:
                o = olds.get(r["name"])
                w.writerow([r["name"].strip(), r["label"], r["subject"]] + [f"{r['err'].get(n, ''):.3f}" if n in r["err"] else "" for n in names]
                           + [f"{o['err'][n]:.3f}" if o and n in o["err"] else "" for n in names])
        print(f"Đã ghi {a.out}")
    print("\nChỉ để tham khảo: 5 điểm DrivFace có định nghĩa riêng, không thay đáp án 50 điểm.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
