# Trích từ de-tai-m28/p3-anh-xa.md — mục: Phần mới: ánh xạ trong pipeline và chấm trang rà soát (9–18/10) › Test so với mp50.json. Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
# test_pipeline.py – so nhãn nháp của pipeline với mp50.json đã đóng băng
import json
ref = json.load(open("data/mp50.json"))           # {ảnh: {"orig": {tên: [x, y]}, "flip": {...}}}
new = json.load(open("runs/DT/map50/mp50.json"))  # cùng dạng, do m28.py ghi (D và T-dev)
worst = 0.0
for img, r in ref.items():
    if img not in new:
        continue
    assert list(new[img]["orig"]) == list(r["orig"]), img   # cùng tên, cùng thứ tự
    for name, (x, y) in r["orig"].items():
        nx, ny = new[img]["orig"][name]
        worst = max(worst, abs(nx - x), abs(ny - y))
n = len(set(ref) & set(new))                      # số ảnh khớp tên
print("so được", n, "/", len(new), "ảnh; lệch lớn nhất (px):", round(worst, 4))
assert n == len(new) > 0, "tên ảnh của pipeline khác tên trong mp50.json"
assert worst <= 0.05
