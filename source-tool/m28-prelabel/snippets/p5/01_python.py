# Trích từ de-tai-m28/p5-thi-nghiem.md — mục: Làm thế nào › facetimer.py. Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
import csv, sys, time, datetime, os
# Ví dụ 14/10: python facetimer.py P5 manual m28-manual <số job trên CVAT của bạn> X5 10
person, cond, task, job, block, n = sys.argv[1:7]
out = f"timing_{person}.csv"
new = not os.path.exists(out)
seq = int(input("Bat dau tu seq (Enter = 1): ") or 1)
first = True
with open(out, "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    if new:
        w.writerow(["date", "person", "condition", "task", "job", "block", "seq",
                    "face_id", "seconds", "warmup", "interrupted", "note"])
    while seq <= int(n):
        face, t0, paused, intr = f"{block}_{seq:02d}", time.perf_counter(), 0.0, 0
        k = input(f"{face}: Enter = xong (go chu = ghi chu), p = dung, q = thoat: ")
        while k.strip() == "p":
            p0 = time.perf_counter(); input("Dang dung. Enter de lam tiep...")
            paused += time.perf_counter() - p0; intr = 1
            k = input(f"{face}: Enter = xong, p = dung, q = thoat: ")
        if k.strip() == "q":
            break
        w.writerow([datetime.date.today().isoformat(), person, cond, task, job, block, seq, face,
                    round(time.perf_counter() - t0 - paused, 1), int(seq <= 2 or first), intr, k.strip()])
        f.flush(); seq += 1; first = False
