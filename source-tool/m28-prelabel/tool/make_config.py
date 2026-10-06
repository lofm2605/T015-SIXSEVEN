"""Sinh config/m28_config.json (BẢN NHÁP, P3 chốt), config/map_mp50.json và config/mp_mirror478.json: 50 điểm đặt TRỰC TIẾP lên đỉnh MediaPipe.

    python tool\\make_config.py                     (sinh lại file từ bảng SPEC dưới đây, giữ số đã có: flip_width, tmpl, t_flip, tolerance, status)
    python tool\\make_config.py --run INC2_ALL --manifest data\\manifest.csv     (ước lượng lại hoán vị gương, flip_width, tmpl từ dữ liệu thật)

Config version 2 (QĐ-001: bỏ WFLW, không còn đáp án 98 điểm và không học phép khớp nào):
  * mỗi điểm có `mp_idx` (một đỉnh MediaPipe 0-477) thay cho `wflw` (chỉ số WFLW) của version 1;
  * `curve` của điểm C là DANH SÁCH TÊN điểm theo thứ tự dọc đường (có chứa chính điểm đó); eval50 đo khoảng cách từ điểm dự đoán tới đường
    gấp khúc nối các điểm ĐÁP ÁN 50 điểm theo tên đó. Điểm E có curve = null;
  * `tmpl` = trung bình 50 điểm (toạ độ ảnh cắt 512) do CHÍNH ánh xạ mới dự đoán trên các mặt F thẳng (pose = 0 và |yaw| <= --max-yaw, mặc
    định 12 độ). Không có đáp án nên dùng dự đoán; chỉ để dựng khuôn skeleton CVAT (make_label.py), không dùng để đo gì;
  * tên điểm, thứ tự, vùng, side, type, line, anchor, coincide, cặp flip và `lines` GIỮ NGUYÊN so với version 1 (P4, P5 đã dùng tên).

Thứ tự trình tự cho P3 (mọi lệnh chạy từ source-tool\\m28-prelabel, cmd):
  1. python tool\\m28.py prepare --run <run> --images data\\frames --set F Tdev --box auto   (hoặc --images data\\crops --box wflw nếu chỉ có gói)
  2. python tool\\make_config.py --run <run> --manifest data\\manifest.csv
  3. python tool\\m28.py prepare --run <run> --force map50 flags autoqc overlays
  4. python tool\\check_flip.py --run <run>

Chọn đỉnh (xem ảnh kiểm trong báo cáo giai đoạn 2; chọn theo topology Face Mesh rồi kiểm bằng mắt trên mặt tài xế, KHÔNG dùng dữ liệu WFLW):
  * viền 17 điểm: oval mặt (đoạn từ thái dương R qua cằm 152 sang L). p01/p17 = 127/356 (ngang khoé mắt ngoài, hơi trên khi đầu nghiêng).
    Giữa p01 và cằm có 11 đỉnh oval, chọn 8 sao cho đường gấp khúc 17 điểm lệch oval ít nhất (đỉnh dày ở cằm, thưa ở má thẳng);
  * mày: mép TRÊN của lông mày (70,63,105,66,107 và 300,293,334,296,336), đuôi và đầu là E. Mép trên đúng với "mép trên" của bố cục 98 điểm cũ,
    nhưng nằm cao hơn đường giữa lông mày vài pixel (xem ghi chú điểm kém trong báo cáo);
  * mũi: p28 = 168 (sống mũi, giữa hai mắt), p29 = 1 (chóp), p31 = 2 (chân giữa, dưới chóp), p30/p32 = 98/327 (cánh mũi);
  * mắt: khoé 33/133 và 263/362; giữa mí trên 159/386; giữa mí dưới 145/374 (cặp trên/dưới cùng "đỉnh giữa theo thứ tự lưới", khớp EAR chuẩn);
  * môi ngoài: khoé 61/291; mép trên 40, 0, 270; mép dưới 405, 17, 181 (cách đều khoé và giữa); môi trong: p49 = 13, p50 = 14 (giữa môi trong trên/dưới).
  Môi trong p49/p50 chỉ có hai điểm nên chọn phương án (a): type C với curve [p41, p49, p45] / [p45, p50, p41] (đi qua hai khoé miệng ngoài).
  Lý do: độ mở miệng (chiều dọc) là cái cần đo, còn trượt ngang dọc theo mép môi thì người gán tay tự đặt "giữa" không chính xác; (a) tha trượt
  ngang nhỏ nhưng vẫn phạt đủ lỗi dọc. Phương án (b) đổi sang E sẽ phạt cả trượt ngang. Lưu ý đường gấp khúc thưa: lỗi dọc đường chỉ bằng 0 quanh
  điểm đáp án (eval50 ghi rõ điều này).
  Điểm side M phải là đỉnh nằm trên trục đối xứng (perm[mp_idx] == mp_idx): 152, 168, 1, 2, 0, 17, 13, 14. Mọi điểm p thoả perm[mp_idx(p)] == mp_idx(flip(p)):
  make_config.py kiểm khi sinh (assert có thông báo rõ).
Không có điểm nào đổi định nghĩa so với bố cục cũ trừ chỗ chỉ số thay bằng đỉnh MediaPipe gần nghĩa nhất; không điểm nào phải đổi sang ý khác.

Quy ước bên: `side` theo người trong ảnh; mặt thẳng thì R ở nửa trái ảnh.
"""
import argparse
import csv
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m28core import mirror as mirror_mod  # noqa: E402
from m28core.mapping import apply_map  # noqa: E402

VERSION = 2
STATUS = "NHAP - cho P3 chot, dong bang 12/10"

# (p, mp_idx, region, side, flip_p, type, curve [số p] hoặc None, line, anchor). Thứ tự = thứ tự điểm trong config (và trong CVAT).
_J = list(range(1, 18))
SPEC = (
    # viền mặt: p01 (thái dương R) ... p09 cằm ... p17 (thái dương L)
    [(1, 127, "jaw", "R", 17, "C", _J, "jaw", 1), (2, 93, "jaw", "R", 16, "C", _J, "jaw", 0), (3, 132, "jaw", "R", 15, "C", _J, "jaw", 0),
     (4, 58, "jaw", "R", 14, "C", _J, "jaw", 0), (5, 172, "jaw", "R", 13, "C", _J, "jaw", 0), (6, 136, "jaw", "R", 12, "C", _J, "jaw", 0),
     (7, 150, "jaw", "R", 11, "C", _J, "jaw", 0), (8, 176, "jaw", "R", 10, "C", _J, "jaw", 0), (9, 152, "jaw", "M", 9, "C", _J, "jaw", 1),
     (10, 400, "jaw", "L", 8, "C", _J, "jaw", 0), (11, 379, "jaw", "L", 7, "C", _J, "jaw", 0), (12, 365, "jaw", "L", 6, "C", _J, "jaw", 0),
     (13, 397, "jaw", "L", 5, "C", _J, "jaw", 0), (14, 288, "jaw", "L", 4, "C", _J, "jaw", 0), (15, 361, "jaw", "L", 3, "C", _J, "jaw", 0),
     (16, 323, "jaw", "L", 2, "C", _J, "jaw", 0), (17, 356, "jaw", "L", 1, "C", _J, "jaw", 1)]
    # lông mày R (đuôi -> đầu) và L (đầu -> đuôi): mép trên
    + [(18, 70, "brow", "R", 27, "E", None, "brow_R", 1), (19, 63, "brow", "R", 26, "C", [18, 19, 20, 21, 22], "brow_R", 0),
       (20, 105, "brow", "R", 25, "C", [18, 19, 20, 21, 22], "brow_R", 0), (21, 66, "brow", "R", 24, "C", [18, 19, 20, 21, 22], "brow_R", 0),
       (22, 107, "brow", "R", 23, "E", None, "brow_R", 1),
       (23, 336, "brow", "L", 22, "E", None, "brow_L", 1), (24, 296, "brow", "L", 21, "C", [23, 24, 25, 26, 27], "brow_L", 0),
       (25, 334, "brow", "L", 20, "C", [23, 24, 25, 26, 27], "brow_L", 0), (26, 293, "brow", "L", 19, "C", [23, 24, 25, 26, 27], "brow_L", 0),
       (27, 300, "brow", "L", 18, "E", None, "brow_L", 1)]
    # mũi
    + [(28, 168, "nose", "M", 28, "C", [28, 29], "nose_bridge", 1), (29, 1, "nose", "M", 29, "E", None, "nose_bridge", 1),
       (30, 98, "nose", "R", 32, "E", None, "nose_base", 1), (31, 2, "nose", "M", 31, "C", [30, 31, 32], "nose_base", 0),
       (32, 327, "nose", "L", 30, "E", None, "nose_base", 1)]
    # mắt R (p33-p36: khoé ngoài, giữa mí trên, khoé trong, giữa mí dưới), mắt L (p37-p40: khoé trong, giữa mí trên, khoé ngoài, giữa mí dưới)
    + [(33, 33, "eye", "R", 39, "E", None, "eye_R", 1), (34, 159, "eye", "R", 38, "C", [33, 34, 35], "eye_R", 0),
       (35, 133, "eye", "R", 37, "E", None, "eye_R", 1), (36, 145, "eye", "R", 40, "C", [35, 36, 33], "eye_R", 0),
       (37, 362, "eye", "L", 35, "E", None, "eye_L", 1), (38, 386, "eye", "L", 34, "C", [37, 38, 39], "eye_L", 0),
       (39, 263, "eye", "L", 33, "E", None, "eye_L", 1), (40, 374, "eye", "L", 36, "C", [39, 40, 37], "eye_L", 0)]
    # môi ngoài (p41-p48: khoé R, ba điểm mép trên, khoé L, ba điểm mép dưới từ L sang R) và môi trong (p49 trên, p50 dưới)
    + [(41, 61, "lip", "R", 45, "E", None, "lip_outer", 1), (42, 40, "lip", "R", 44, "C", [41, 42, 43, 44, 45], "lip_outer", 0),
       (43, 0, "lip", "M", 43, "C", [41, 42, 43, 44, 45], "lip_outer", 1), (44, 270, "lip", "L", 42, "C", [41, 42, 43, 44, 45], "lip_outer", 0),
       (45, 291, "lip", "L", 41, "E", None, "lip_outer", 1), (46, 405, "lip", "L", 48, "C", [45, 46, 47, 48, 41], "lip_outer", 0),
       (47, 17, "lip", "M", 47, "C", [45, 46, 47, 48, 41], "lip_outer", 1), (48, 181, "lip", "R", 46, "C", [45, 46, 47, 48, 41], "lip_outer", 0),
       (49, 13, "lip", "M", 49, "C", [41, 49, 45], "lip_inner", 1), (50, 14, "lip", "M", 50, "C", [45, 50, 41], "lip_inner", 1)]
)
COINCIDE = ((34, 36), (38, 40), (49, 50))        # mí trên/dưới khi nhắm, môi trong khi khép
CLOSED = {"jaw": False, "brow_R": False, "brow_L": False, "nose_bridge": False, "nose_base": False,
          "eye_R": True, "eye_L": True, "lip_outer": True, "lip_inner": False}


def _name(p):
    row = SPEC[p - 1]
    return f"p{p:02d}_{row[2]}_{row[3]}"


def build_config(tmpl=None, t_flip=None, perm=None):
    """Config version 2. perm: hoán vị gương 478 đỉnh (config/mp_mirror478.json); có thì kiểm nhất quán với cặp flip và điểm side M."""
    assert [r[0] for r in SPEC] == list(range(1, 51)), "SPEC phải đủ p01..p50 theo thứ tự"
    idx = [r[1] for r in SPEC]
    assert len(set(idx)) == 50 and all(0 <= i < 478 for i in idx), "mp_idx phải là 50 đỉnh khác nhau trong 0-477"
    pts = []
    for p, mp, region, side, flip_p, typ, curve, line, anchor in SPEC:
        assert SPEC[flip_p - 1][4] == p, f"cặp flip của p{p:02d} không đối xứng (p{flip_p:02d} không trỏ ngược lại)"
        assert (flip_p == p) == (side == "M"), f"p{p:02d}: side {side} không khớp với flip (M khi và chỉ khi tự đối xứng)"
        assert (curve is None) == (typ == "E"), f"p{p:02d}: type {typ} và curve không khớp"
        if curve is not None:
            assert p in curve, f"p{p:02d}: curve phải chứa chính điểm đó"
        pts.append({"name": _name(p), "region": region, "side": side, "flip": _name(flip_p), "mp_idx": mp, "type": typ,
                    "curve": None if curve is None else [_name(c) for c in curve], "line": line, "anchor": int(anchor),
                    "coincide": None, "tmpl": None})
    by = {p["name"]: p for p in pts}
    for a, b in COINCIDE:
        by[_name(a)]["coincide"], by[_name(b)]["coincide"] = _name(b), _name(a)
    for p in pts:
        if p["curve"] and p["line"] != "lip_inner":                # curve đi dọc đúng line của điểm (trừ môi trong: đi qua khoé miệng ngoài)
            assert all(by[c]["line"] == p["line"] for c in p["curve"]), f"{p['name']}: curve ra ngoài line {p['line']}"
    if perm is not None:
        check_perm(pts, perm)
    if tmpl is not None:
        tmpl = np.asarray(tmpl, float)
        assert tmpl.shape == (len(pts), 2), f"tmpl phải có hình ({len(pts)}, 2), nhận {tmpl.shape}"
        for p, t in zip(pts, tmpl):
            p["tmpl"] = [round(float(t[0]), 2), round(float(t[1]), 2)]
    return {"version": VERSION, "status": STATUS, "n_points": len(pts), "points": pts,
            "lines": {k: {"closed": v} for k, v in CLOSED.items()},
            "iod_points": [_name(33), _name(39)], "t_flip": t_flip, "tolerance": None}


def check_perm(points, perm):
    """Với mọi điểm p: perm[mp_idx(p)] == mp_idx(flip(p)); điểm side M nằm trên trục (perm[mp_idx] == mp_idx). Sai thì AssertionError rõ ràng."""
    by = {p["name"]: p for p in points}
    for p in points:
        q = by[p["flip"]]
        assert perm[p["mp_idx"]] == q["mp_idx"], (
            f"{p['name']} (đỉnh {p['mp_idx']}) có đối xứng gương là đỉnh {perm[p['mp_idx']]} theo mp_mirror478.json, "
            f"nhưng flip {q['name']} dùng đỉnh {q['mp_idx']}: sửa SPEC hoặc học lại hoán vị gương")
        if p["side"] == "M":
            assert perm[p["mp_idx"]] == p["mp_idx"], (
                f"{p['name']} có side M nhưng đỉnh {p['mp_idx']} không nằm trên trục đối xứng (đối xứng với đỉnh {perm[p['mp_idx']]})")


def build_map(cfg, flip_width=512.0, meta=None):
    """map_mp50.json version 2 (kind vertex) từ config."""
    return {"version": 2, "kind": "vertex", "names": [p["name"] for p in cfg["points"]],
            "points": {p["name"]: {"mp_idx": p["mp_idx"], "flip": p["flip"]} for p in cfg["points"]},
            "flip_width": float(flip_width), "meta": meta or {}}


def gt50_template():
    """Đáp án 50 điểm nay đến từ nhãn nhóm gán tay trong CVAT (tool\\eval50.py), không còn sinh từ đáp án WFLW: chỉ ghi file mẫu rỗng."""
    return {}


# ---------- ước lượng từ dữ liệu thật (cần pred478.json của một lượt chạy) ----------
def read_manifest(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def select_faces(rows, pred, set_name="F", max_yaw=None):
    """Tên mặt (không đuôi) của tập set_name có pose = 0, có cả ảnh gốc và ảnh lật trong pred. max_yaw: chỉ giữ |yaw| <= max_yaw (nếu manifest có cột yaw)."""
    out = []
    for r in rows:
        name = r["file"][:-4] if r["file"].lower().endswith(".png") else r["file"]
        if r.get("set") != set_name or r.get("pose") != "0" or name not in pred or not pred[name].get("flip"):
            continue
        if max_yaw is not None and r.get("yaw") not in (None, ""):
            if abs(float(r["yaw"])) > max_yaw:
                continue
        out.append(name)
    return out


def estimate_flip_width(origs, flips, perm, idx50=None):
    """w sao cho điểm đã bỏ lật (x' = w - x_lật) trùng điểm của ảnh gốc về trung bình (bình phương tối thiểu): w = trung bình của
    x_gốc(i) + x_lật(perm[i]). Trả dict: w (50 điểm nếu có idx50, không thì 478), trung vị, độ lệch y (trung bình có dấu và trung vị tuyệt đối),
    w trên 478 đỉnh. Không cần đáp án."""
    perm = np.asarray(perm, int)
    sel = np.arange(478) if idx50 is None else np.asarray(idx50, int)
    s_main, s_all, dy = [], [], []
    for o, f in zip(origs, flips):
        o, f = np.asarray(o, float), np.asarray(f, float)
        s_main.append(o[sel, 0] + f[perm[sel], 0])
        s_all.append(o[:, 0] + f[perm, 0])
        dy.append(o[sel, 1] - f[perm[sel], 1])
    s_main, s_all, dy = np.concatenate(s_main), np.concatenate(s_all), np.concatenate(dy)
    return {"w": float(s_main.mean()), "w_median": float(np.median(s_main)), "w_all478": float(s_all.mean()),
            "w_all478_median": float(np.median(s_all)), "w_std": float(s_main.std()),
            "dy_mean": float(dy.mean()), "dy_median_abs": float(np.median(np.abs(dy))), "n_faces": len(origs)}


def template(cfg, mp_map, origs):
    """Khuôn trung bình 50 điểm (toạ độ ảnh cắt 512) do ánh xạ dự đoán trên các mặt origs (không có đáp án)."""
    if not origs:
        raise ValueError("không có mặt F nào có pose = 0 (và ảnh lật) trong lượt chạy để lấy trung bình khuôn")
    names = [p["name"] for p in cfg["points"]]
    return np.mean([[apply_map(o, mp_map, cfg)[n] for n in names] for o in origs], axis=0)


def keep_existing(cfg, old, t_flip_given):
    """Chạy lại không được xoá số người khác đã ghi: t_flip (P2), tolerance (P3, 10/10), status, tmpl.
    Chỉ giữ khi old cùng version và cùng tên điểm (tmpl của config version 1 là hình học WFLW, không được mang sang)."""
    kept = []
    if old and old.get("version") == cfg["version"] and [p["name"] for p in old.get("points", [])] == [p["name"] for p in cfg["points"]]:
        if not t_flip_given and old.get("t_flip") is not None:
            cfg["t_flip"] = old["t_flip"]
            kept.append("t_flip")
        if old.get("tolerance") is not None:
            cfg["tolerance"] = old["tolerance"]
            kept.append("tolerance")
        if not str(old.get("status", "NHAP")).startswith("NHAP"):
            cfg["status"] = old["status"]
            kept.append("status")
        if cfg["points"][0]["tmpl"] is None and old["points"][0].get("tmpl") is not None:
            for p, q in zip(cfg["points"], old["points"]):
                p["tmpl"] = q["tmpl"]
            kept.append("tmpl")
    return kept


def _load(path):
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def _dump(path, obj, indent=1):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)
        f.write("\n")
    os.replace(tmp, path)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")     # Windows: stdout chuyển hướng không bị cp1252
    ap = argparse.ArgumentParser(description="Sinh config version 2 (chọn đỉnh MediaPipe), map_mp50.json và mp_mirror478.json")
    ap.add_argument("--out", default=os.path.join("config", "m28_config.json"))
    ap.add_argument("--map-out", default=os.path.join("config", "map_mp50.json"))
    ap.add_argument("--mirror", default=os.path.join("config", "mp_mirror478.json"), help="hoán vị gương 478 đỉnh (đọc; --run thì ghi lại)")
    ap.add_argument("--run", help="lượt đã chạy crop + mediapipe cho tập F: ước lượng lại hoán vị gương, flip_width và tmpl từ dữ liệu thật")
    ap.add_argument("--manifest", default=os.path.join("data", "manifest.csv"))
    ap.add_argument("--max-yaw", type=float, default=12.0, help="tmpl chỉ lấy mặt F pose = 0 có |yaw| <= số này (độ); cần cột yaw của manifest")
    ap.add_argument("--no-mesh", action="store_true", help="không sửa hoán vị gương bằng lưới tam giác MediaPipe (không import mediapipe)")
    ap.add_argument("--t-flip", type=float, help="ngưỡng cờ low_conf do P2 chọn trên T-dev; bỏ trống = giữ số đã có (hoặc null)")
    ap.add_argument("--gt50", help="ghi file đáp án mẫu rỗng {} (đáp án nay đến từ nhãn gán tay trong CVAT, đo bằng tool\\eval50.py)")
    a = ap.parse_args(argv)

    old_cfg, old_map = _load(a.out), _load(a.map_out)
    mir = None
    flip_width, map_meta, tmpl, msgs = 512.0, {}, None, []
    if a.run:
        pred_path = os.path.join("runs", a.run, "mediapipe", "pred478.json")
        if not os.path.exists(pred_path):
            sys.exit(f"Không thấy {pred_path}: chạy prepare (crop, mediapipe) cho tập F trước.")
        pred = _load(pred_path)
        rows = read_manifest(a.manifest)
        names_pose0 = select_faces(rows, pred, "F")
        if len(names_pose0) < 30:
            sys.exit(f"Chỉ có {len(names_pose0)} mặt F pose = 0 có cả ảnh gốc và ảnh lật trong {pred_path} (cần >= 30): chạy prepare --set F.")
        origs = [pred[n]["orig"] for n in names_pose0]
        flips = [pred[n]["flip"] for n in names_pose0]
        edges = None if a.no_mesh else mirror_mod.tessellation_edges()
        mir = mirror_mod.learn_mirror_flip(origs, flips, 512.0, edges)
        bad = mirror_mod.sanity(mir["perm"])
        if bad:
            sys.exit("Hoán vị gương học được không đạt kiểm cứng:\n  " + "\n  ".join(bad))
        meta = mir["meta"]
        msgs.append(f"hoán vị gương: {meta['n_faces']} mặt F pose=0, {meta['n_fixed']} đỉnh trên trục, sai số ghép trung vị "
                    f"{meta['resid_median_pct_iod']:.2f}% / lớn nhất {meta['resid_max_pct_iod']:.2f}% IOD"
                    + (f", cạnh lưới vỡ {meta['mesh_violations_before_refine']} -> {meta['mesh_violations_after_refine']}" if edges is not None else ""))
        _dump(a.mirror, {"perm": mir["perm"], "fixed": mir["fixed"], "meta": meta}, indent=None)
        perm = mir["perm"]
        cfg = build_config(None, a.t_flip, perm)
        idx50 = [p["mp_idx"] for p in cfg["points"]]
        fw = estimate_flip_width(origs, flips, perm, idx50)
        flip_width = fw["w"]
        map_meta = {"flip_width_source": f"{fw['n_faces']} mặt F pose=0 của lượt {a.run} (không cần đáp án)",
                    "flip_width_median": round(fw["w_median"], 4), "flip_width_std": round(fw["w_std"], 4),
                    "flip_width_478": round(fw["w_all478"], 4), "flip_dy_mean": round(fw["dy_mean"], 4),
                    "flip_dy_median_abs": round(fw["dy_median_abs"], 4), "date": time.strftime("%Y-%m-%d"),
                    "mirror_file": os.path.basename(a.mirror)}
        msgs.append(f"flip_width = {flip_width:.3f} (trung vị {fw['w_median']:.3f}, 478 đỉnh {fw['w_all478']:.3f}; lệch y trung bình {fw['dy_mean']:+.3f} px, "
                    f"trung vị tuyệt đối {fw['dy_median_abs']:.3f} px)")
        mp_map = build_map(cfg, flip_width, map_meta)
        straight = select_faces(rows, pred, "F", a.max_yaw)
        if len(straight) < 10:
            straight = names_pose0
            msgs.append(f"CHÚ Ý: chỉ {len(straight)} mặt có |yaw| <= {a.max_yaw:g}, tmpl lấy trên mọi mặt F pose=0")
        tmpl = template(cfg, mp_map, [pred[n]["orig"] for n in straight])
        map_meta["tmpl_faces"] = len(straight)
        cfg = build_config(tmpl, a.t_flip, perm)
        msgs.append(f"tmpl: trung bình dự đoán của {len(straight)} mặt F pose=0 (|yaw| <= {a.max_yaw:g})")
    else:
        if not os.path.exists(a.mirror):
            sys.exit(f"Không thấy {a.mirror}: chạy với --run <lượt có pred478 của tập F> để học hoán vị gương, hoặc lấy file từ repo.")
        mir = mirror_mod.load_mirror(a.mirror)
        cfg = build_config(None, a.t_flip, mir["perm"])
        if old_map and old_map.get("version") == 2 and "flip_width" in old_map:
            flip_width, map_meta = float(old_map["flip_width"]), old_map.get("meta") or {}
            msgs.append(f"giữ flip_width = {flip_width:.3f} của map cũ")
        else:
            msgs.append("CHÚ Ý: chưa có flip_width ước lượng (đặt 512): chạy lại với --run")
    kept = keep_existing(cfg, old_cfg, a.t_flip is not None)
    mp_map = build_map(cfg, flip_width, map_meta)
    _dump(a.out, cfg)
    _dump(a.map_out, mp_map)
    print(f"Đã ghi {a.out}: {cfg['n_points']} điểm" + (", có khuôn tmpl" if cfg["points"][0]["tmpl"] else ", chưa có tmpl")
          + (f"; giữ lại từ file cũ: {', '.join(kept)}" if kept else "") + f"; {a.map_out}; {a.mirror}")
    for m in msgs:
        print("  " + m)
    if a.gt50:
        _dump(a.gt50, gt50_template())
        print(f"Đã ghi {a.gt50} (mẫu rỗng): đáp án 50 điểm nay là nhãn nhóm gán tay trong CVAT, đo bằng tool\\eval50.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
