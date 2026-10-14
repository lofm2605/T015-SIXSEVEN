"""Điểm bị che do MẶT NGHIÊNG (tự che): đặt occluded=1 trong file nháp, giữ nguyên vị trí ước lượng, không dùng outside.

MediaPipe không cho biết điểm nào bị che (visibility/presence của landmark mặt luôn rỗng), nên suy từ góc quay đầu:
  u = (x mũi - trung điểm hai gò má) / nửa bề ngang mặt, tính từ lưới 478 điểm của ảnh gốc (mũi = 1, gò má = 234 và 454).
  u < 0: mũi lệch sang nửa TRÁI ảnh, mặt quay về bên trái ảnh; nửa mặt bên đó nằm xa camera nên bị che (L theo config, side theo bức ảnh). u > 0 thì ngược lại.
  Góc quay ước lượng yaw = (|u| + 0.08) / 0.0405 độ: hồi quy trên 198 ảnh in-cabin (bo200_A) so với ma trận biến đổi mặt của MediaPipe (hệ số tương quan 0.98,
  yaw 0 đến 63 độ); ngoài khoảng đó chỉ là ngoại suy.
  Nửa mặt xa camera: lông mày và mắt bị che từ YAW_MAT độ; môi (các điểm cùng bên) bị che từ YAW_MOI độ. Sống mũi và các điểm trên trục (side M) không bao giờ bị che.
Không phát hiện được tay, kính râm hay khẩu trang che mặt chính diện (cần model riêng; chủ repo chọn chỉ xử lý mặt nghiêng, 14/10/2026).
"""
import numpy as np

NOSE, CHEEK_L, CHEEK_R = 1, 234, 454          # chỉ số trong lưới 478 điểm của MediaPipe
YAW_MAT = 60.0                                # độ: từ đây lông mày và mắt của nửa mặt xa camera bị che
YAW_MOI = 75.0                                # độ: từ đây môi của nửa mặt xa camera bị che
_A, _B = 0.0405, 0.08                         # |u| = _A * yaw - _B (hồi quy nói ở trên)
VUNG_MAT = ("brow", "eye")
VUNG_MOI = ("lip",)


def lech_mui(pts478):
    """u của một mặt (list [x, y] theo pixel, 478 điểm), hoặc None nếu thiếu điểm hay mặt không có bề ngang."""
    p = np.asarray(pts478, float)
    if p.ndim != 2 or len(p) <= CHEEK_R:
        return None
    nua = (p[CHEEK_R, 0] - p[CHEEK_L, 0]) / 2.0
    if abs(nua) < 1e-6:
        return None
    return float((p[NOSE, 0] - (p[CHEEK_L, 0] + p[CHEEK_R, 0]) / 2.0) / nua)


def yaw_uoc_luong(pts478):
    """Góc quay đầu ước lượng theo độ (luôn dương), hoặc None."""
    u = lech_mui(pts478)
    return None if u is None else max(0.0, (abs(u) + _B) / _A)


def diem_bi_che(pts478, cfg):
    """Tên các điểm (trong 50 điểm của config) bị che vì mặt nghiêng, theo thứ tự trong config. Mặt thẳng hoặc không tính được thì []."""
    u = lech_mui(pts478)
    if u is None:
        return []
    yaw = max(0.0, (abs(u) + _B) / _A)
    xa = "L" if u < 0 else "R"
    out = []
    for p in cfg["points"]:
        if p.get("side") != xa:
            continue
        if (p.get("region") in VUNG_MAT and yaw >= YAW_MAT) or (p.get("region") in VUNG_MOI and yaw >= YAW_MOI):
            out.append(p["name"])
    return out
