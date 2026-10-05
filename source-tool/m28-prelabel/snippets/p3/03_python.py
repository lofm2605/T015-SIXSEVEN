# Trích từ de-tai-m28/p3-anh-xa.md — mục: Làm thế nào › 5. Công sửa (P4 chạy tuần 3). Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
import numpy as np

def correction_stats(pre, out, err_pre, err_out, tol, d):
    """pre, out: dict tên -> (x, y) của file nhập nháp và bản xuất raw/.
    err_pre, err_out: từ point_errors (% IOD); tol: tên -> sai số % IOD; d: IOD (px)."""
    bins = {"giu": 0, "chinh_nhe": 0, "sua": 0}
    miss, over = [0, 0], [0, 0]                     # [tử số, mẫu số]
    for n in err_pre:
        move = np.linalg.norm(np.subtract(out[n], pre[n]))   # px
        if move <= 0.5:
            bins["giu"] += 1
        elif move <= tol[n] / 100 * d:
            bins["chinh_nhe"] += 1
        else:
            bins["sua"] += 1
        if err_pre[n] > tol[n]:                     # điểm nháp sai
            miss[1] += 1
            miss[0] += err_out[n] > tol[n]          # vẫn sai khi xuất = bỏ sót
        if err_pre[n] / 100 * d <= 1.0:             # điểm nháp gần đúng (≤ 1 px)
            over[1] += 1
            over[0] += move > 0.5                   # vẫn bị dời = sửa thừa
    return bins, miss, over
