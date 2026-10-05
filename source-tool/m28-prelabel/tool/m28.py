"""m28 — pipeline nhãn nháp landmark khuôn mặt: prepare → review → push → collect (all = prepare → review → push).

    python tool\\m28.py prepare --run R1610 --list data\\r_list_1610.csv --images <WFLW_images> --box auto
    python tool\\m28.py review  --run R1610 --review ui --reviewer P5
    python tool\\m28.py push    --run R1610 --task demo-R1610 [--dry-run]
    python tool\\m28.py collect --task demo-R1610
    python tool\\m28.py all     --run thuP1 --list data\\f5_list.csv --images <WFLW_images> --box wflw --review auto --task demo-thuP1

Mỗi bước ghi vào runs/<run>/<bước>/ và để lại done.txt khi xong thật; chạy lại thì bước đã xong được bỏ qua
(trừ khi tên bước nằm trong --force). Địa chỉ CVAT và token đọc từ CVAT_URL, CVAT_ACCESS_TOKEN.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m28core import steps  # noqa: E402

PREPARE = ["crop", "mediapipe", "map50", "flags", "autoqc", "overlays"]


def _log(args, name, status, t0):
    os.makedirs(os.path.join("runs", args.run), exist_ok=True)
    with open(os.path.join("runs", args.run, "log.txt"), "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{name}\t{status}\t{time.time() - t0:.1f}s\n")


def run_step(name, args):
    t0 = time.time()
    out = os.path.join("runs", args.run, name)
    if os.path.exists(os.path.join(out, "done.txt")) and name not in args.force:
        print("bỏ qua", name)
        _log(args, name, "bo_qua", t0)
        return
    os.makedirs(out, exist_ok=True)
    status = "loi"
    try:
        ok = getattr(steps, name)(args, out)   # True chỉ khi bước xong thật; False thì hàm bước đã in lý do
        status = "xong" if ok else "dung"
    finally:
        _log(args, name, status, t0)
    if not ok:
        raise SystemExit(f"Dừng ở bước {name}: chưa xong nên không ghi done.txt (lý do in ở trên).")
    with open(os.path.join(out, "done.txt"), "w", encoding="utf-8") as f:
        f.write("ok")


def build_parser():
    p = argparse.ArgumentParser(prog="m28")
    p.add_argument("cmd", choices=["prepare", "review", "push", "collect", "all"])
    p.add_argument("--run", help="tên lượt chạy, ví dụ R1610 (collect không cần)")
    p.add_argument("--images", help="thư mục ảnh (WFLW_images hoặc ảnh khách)")
    p.add_argument("--list", help="CSV có cột wflw_image, wflw_line")
    p.add_argument("--set", nargs="*", help="lọc theo cột set của manifest.csv")
    p.add_argument("--manifest", default=os.path.join("data", "manifest.csv"))
    p.add_argument("--box", choices=["wflw", "auto"], default="auto")
    p.add_argument("--config", default=os.path.join("config", "m28_config.json"))
    p.add_argument("--map", default=os.path.join("config", "map_mp50.json"))
    p.add_argument("--pipeline", default=os.path.join("config", "pipeline.json"))
    p.add_argument("--model", default="face_landmarker.task", help="mặc định ở thư mục chạy lệnh, không có thì tìm trong tool/")
    p.add_argument("--review", choices=["ui", "excel", "auto"], default="ui")
    p.add_argument("--reviewer", default="RA")
    p.add_argument("--review-file")
    p.add_argument("--task", action="append", default=[], help="push: tên task (một, mặc định demo-<run>); collect: nhiều task")
    p.add_argument("--tag")
    p.add_argument("--skip-export", action="store_true")
    p.add_argument("--force", nargs="*", default=[])
    p.add_argument("--dry-run", action="store_true",
                   help="push: chỉ ghi XML; collect: chỉ in danh sách job; không ghi done.txt")
    return p


def main(argv=None):
    p = build_parser()
    args = p.parse_args(argv)
    if args.cmd == "collect":
        if not args.task:
            p.error("collect cần --task")
        if not steps.collect(args, None):
            raise SystemExit("collect chưa xong (lý do in ở trên).")
        return
    if not args.run:
        p.error("lệnh này cần --run")
    if args.cmd in ("prepare", "all"):
        for s in PREPARE:
            run_step(s, args)
    if args.cmd in ("review", "all"):
        run_step("review", args)
    if args.cmd in ("push", "all"):
        run_step("push", args)          # all dừng ở push; collect chạy riêng sau khi có người gán


if __name__ == "__main__":
    main()
