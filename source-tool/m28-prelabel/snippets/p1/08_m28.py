# Trích từ de-tai-m28/p1-du-lieu.md — mục: Phần mới: lệnh m28.py (8–16/10) › Làm thế nào. Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
# tool/m28.py – khung tối thiểu
import argparse, os
from m28core import steps   # crop, mediapipe, map50, flags, autoqc, overlays (+ review, push, collect)

PREPARE = ["crop", "mediapipe", "map50", "flags", "autoqc", "overlays"]

def run_step(name, args):
    out = os.path.join("runs", args.run, name)
    if os.path.exists(os.path.join(out, "done.txt")) and name not in args.force:
        print("bỏ qua", name); return
    os.makedirs(out, exist_ok=True)
    ok = getattr(steps, name)(args, out)  # True chỉ khi bước xong thật; trả False thì hàm bước đã in lý do
    if not ok:  # ví dụ: rà chưa bấm Xong (kể cả Ctrl+C), CSV thiếu quyết định, push/collect chạy --dry-run
        raise SystemExit(f"Dừng ở bước {name}: chưa xong nên không ghi done.txt (lý do in ở trên).")
    with open(os.path.join(out, "done.txt"), "w", encoding="utf-8") as f:
        f.write("ok")

# Hàm bước trong m28core/steps.py nhận (args, out), trả True chỉ khi xong thật:
#   review: trang đã đóng mà chưa có out/done.txt (nút Xong ghi) → False; excel: CSV còn thiếu dòng → False
#   push, collect: có --dry-run → chỉ ghi XML / in danh sách job rồi trả False (không ghi done.txt)

p = argparse.ArgumentParser(prog="m28")
p.add_argument("cmd", choices=["prepare", "review", "push", "collect", "all"])
p.add_argument("--run")                                # tên lượt chạy, ví dụ R1610 (collect không cần)
p.add_argument("--images")                             # thư mục ảnh (WFLW_images hoặc ảnh khách)
p.add_argument("--list"); p.add_argument("--set", nargs="*")   # CSV có wflw_image, wflw_line; lọc tập
p.add_argument("--box", choices=["wflw", "auto"], default="auto")
p.add_argument("--config", default="config/m28_config.json")
p.add_argument("--review", choices=["ui", "excel", "auto"], default="ui")
p.add_argument("--reviewer", default="RA"); p.add_argument("--review-file")
p.add_argument("--task", action="append", default=[])  # collect nhận nhiều --task
p.add_argument("--tag"); p.add_argument("--skip-export", action="store_true")
p.add_argument("--force", nargs="*", default=[])
p.add_argument("--dry-run", action="store_true")      # push: chỉ ghi XML; collect: chỉ in danh sách job; không ghi done.txt
args = p.parse_args()
if args.cmd != "collect" and not args.run:
    p.error("lệnh này cần --run")
if args.cmd in ("prepare", "all"):
    for s in PREPARE:
        run_step(s, args)
