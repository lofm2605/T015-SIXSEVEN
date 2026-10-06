"""Sinh config/face50_label.json: danh sách label (một skeleton face50, 50 điểm) để tạo project m28 trên CVAT.

    python tool\\make_label.py [--config config\\m28_config.json] [--out config\\face50_label.json]

Nguồn duy nhất là config/m28_config.json (points[].name/side/line/tmpl, lines{tên: {closed}}). Chạy hai lần ra cùng byte.
Định dạng bám mã nguồn CVAT v2.77.0 (đã đọc, xem README mục Rủi ro), CHƯA thử trên server CVAT thật:
  * Label: type "skeleton", svg, sublabels (type "points"); không có khoá "id" ở đâu cả (server tự cấp).
  * svg: khung vẽ viewBox 0 0 100 100 (cvat-ui skeleton-configurator). Mỗi điểm một <circle> có data-type="element node",
    data-element-id, data-node-id (cùng số 1..50 theo thứ tự config) và data-label-name="<tên điểm>". KHÔNG có data-label-id:
    khi tạo project, server tự đổi data-label-name="<tên>" thành data-label-id="<id mới>" (serializers.py, create_labels),
    nên project tạo trên máy khác vẫn nối đúng nút với điểm. Cạnh: <line> data-type="edge" data-node-from/data-node-to.
  * Chỉ dùng các thuộc tính mà cvat-core cho phép khi đọc svg (cx, cy, r, x1, y1, x2, y2, data-*), vì phần còn lại bị lọc.
  * Toạ độ khuôn = hình trung bình `tmpl` (ảnh cắt 512x512) co giãn đều vào khung 0-100, chừa lề.
  * Mỗi điểm có một thuộc tính checkbox low_conf (mutable, mặc định false) để đánh dấu điểm đáng ngờ.
"""
import argparse
import json
import os
import sys

LABEL_NAME = "face50"
N_POINTS = 50
SIDE_COLOR = {"R": "#e03131", "L": "#1971c2", "M": "#2f9e44"}     # bên phải / bên trái của người trong ảnh / giữa
CANVAS = 100.0                                                    # viewBox 0 0 100 100 của cvat-ui
MARGIN = 6.0
NODE_R = 0.75                                                     # bán kính nút như cvat-ui vẽ (r: 0.75)
LOW_CONF = "low_conf"


def check_config(cfg):
    """Sai thì SystemExit tiếng Việt."""
    pts = cfg.get("points") if isinstance(cfg, dict) else None
    if not isinstance(pts, list) or len(pts) != N_POINTS:
        raise SystemExit(f"Config phải có đúng {N_POINTS} điểm trong 'points' (đang có "
                         f"{len(pts) if isinstance(pts, list) else 'không có'}).")
    seen = set()
    lines = cfg.get("lines") or {}
    for i, p in enumerate(pts, 1):
        name = p.get("name") if isinstance(p, dict) else None
        if not isinstance(name, str) or not name.strip() or len(name) > 64 or '"' in name or "<" in name or "&" in name:
            raise SystemExit(f"Điểm số {i}: tên {name!r} không hợp lệ (cần chữ không rỗng, tối đa 64 ký tự, không có \" < &).")
        if name in seen:
            raise SystemExit(f"Tên điểm trùng trong config: {name}. CVAT nối nút với điểm theo tên nên mỗi tên chỉ một lần.")
        seen.add(name)
        if p.get("side") not in SIDE_COLOR:
            raise SystemExit(f"Điểm {name}: side {p.get('side')!r} không hợp lệ (chỉ R, L hoặc M).")
        t = p.get("tmpl")
        if not (isinstance(t, (list, tuple)) and len(t) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in t)):
            raise SystemExit(f"Điểm {name}: thiếu 'tmpl' [x, y] (hình trung bình 512x512), không dựng được khuôn skeleton.")
        ln = p.get("line")
        if ln and ln not in lines:
            raise SystemExit(f"Điểm {name}: line {ln!r} không có trong 'lines' của config.")


def _canvas_coords(points):
    """Co giãn đều hình trung bình vào khung 0-100 (chừa lề), giữ tỉ lệ, đặt giữa khung."""
    xs = [p["tmpl"][0] for p in points]
    ys = [p["tmpl"][1] for p in points]
    x0, y0, w, h = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    k = (CANVAS - 2 * MARGIN) / max(w, h, 1e-9)
    ox, oy = (CANVAS - k * w) / 2, (CANVAS - k * h) / 2
    return [(ox + k * (p["tmpl"][0] - x0), oy + k * (p["tmpl"][1] - y0)) for p in points]


def edges_of(points, lines):
    """Danh sách cạnh (số nút từ, số nút đến), nút đánh số 1..50 theo thứ tự config. Chỉ nối hai điểm liền nhau trong
    cùng `line`; line closed thì nối thêm điểm cuối về điểm đầu; điểm không có line thì không có cạnh."""
    groups = {}
    for i, p in enumerate(points, 1):
        if p.get("line"):
            groups.setdefault(p["line"], []).append(i)
    out = []
    for name, ids in groups.items():
        out += list(zip(ids, ids[1:]))
        if len(ids) > 2 and (lines.get(name) or {}).get("closed"):
            out.append((ids[-1], ids[0]))
    return out


def _fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def build_svg(points, lines):
    xy = _canvas_coords(points)
    parts = []
    for a, b in edges_of(points, lines):
        (x1, y1), (x2, y2) = xy[a - 1], xy[b - 1]
        parts.append(f'<line x1="{_fmt(x1)}" y1="{_fmt(y1)}" x2="{_fmt(x2)}" y2="{_fmt(y2)}" data-type="edge" '
                     f'data-node-from="{a}" data-node-to="{b}"></line>')
    for i, (p, (x, y)) in enumerate(zip(points, xy), 1):
        parts.append(f'<circle r="{NODE_R}" cx="{_fmt(x)}" cy="{_fmt(y)}" data-type="element node" data-element-id="{i}" '
                     f'data-node-id="{i}" data-label-name="{p["name"]}"></circle>')
    return "\n".join(parts)


def build_labels(cfg):
    """Danh sách label dùng làm `labels` khi tạo project: đúng một label face50 kiểu skeleton."""
    check_config(cfg)
    points, lines = cfg["points"], cfg.get("lines") or {}
    sub = [dict(name=p["name"], type="points", color=SIDE_COLOR[p["side"]],
                attributes=[dict(name=LOW_CONF, mutable=True, input_type="checkbox", default_value="false", values=["false"])])
           for p in points]
    return [dict(name=LABEL_NAME, type="skeleton", attributes=[], sublabels=sub, svg=build_svg(points, lines))]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Sinh config/face50_label.json từ config/m28_config.json")
    ap.add_argument("--config", default=os.path.join("config", "m28_config.json"))
    ap.add_argument("--out", default=os.path.join("config", "face50_label.json"))
    args = ap.parse_args(argv)
    if not os.path.isfile(args.config):
        raise SystemExit(f"Không thấy {args.config}: chạy từ thư mục source-tool\\m28-prelabel hoặc dùng --config.")
    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)
    labels = build_labels(cfg)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(labels, f, ensure_ascii=False, indent=1)
        f.write("\n")
    n_edge = len(edges_of(cfg["points"], cfg.get("lines") or {}))
    print(f"Đã ghi {args.out}: label {LABEL_NAME}, {N_POINTS} điểm, {n_edge} cạnh. Chưa thử trên server CVAT thật: "
          "mở project m28 trong CVAT, kiểm đủ 50 điểm và cạnh nối (xem README mục Rủi ro).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
