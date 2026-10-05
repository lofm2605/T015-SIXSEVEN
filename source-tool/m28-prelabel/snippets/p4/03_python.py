# Trích từ de-tai-m28/p4-cvat.md — mục: Làm thế nào › QC 5 kiểm. Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
import numpy as np

def cross_sign(p, eye_R, eye_L, mouth):
    # p: mảng (50, 2); eye_R, eye_L, mouth: danh sách chỉ số điểm lấy từ config
    eR, eL, m = p[eye_R].mean(0), p[eye_L].mean(0), p[mouth].mean(0)
    a, b = eL - eR, m - (eR + eL) / 2
    return np.sign(a[0] * b[1] - a[1] * b[0])

def is_mirrored(p, template, eye_R, eye_L, mouth):
    return cross_sign(p, eye_R, eye_L, mouth) != cross_sign(template, eye_R, eye_L, mouth)
