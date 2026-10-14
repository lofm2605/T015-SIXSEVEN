"""Điểm bị che do MẶT NGHIÊNG (tự che): đặt occluded=1 trong file nháp, giữ nguyên vị trí ước lượng, không dùng outside.

MediaPipe không cho biết điểm nào bị che (visibility/presence của landmark mặt luôn rỗng), nên suy từ góc quay đầu:
  u = (x mũi - trung điểm hai gò má) / nửa bề ngang mặt, tính từ lưới 478 điểm của ảnh gốc (mũi = 1, gò má = 234 và 454).
  u < 0: mũi lệch sang nửa TRÁI ảnh, mặt quay về bên trái ảnh; nửa mặt bên đó nằm xa camera nên bị che (L theo config, side theo bức ảnh). u > 0 thì ngược lại.
  Góc quay ước lượng yaw = (|u| + 0.08) / 0.0405 độ: hồi quy trên 198 ảnh in-cabin (bo200_A) so với ma trận biến đổi mặt của MediaPipe (hệ số tương quan 0.98,
  yaw 0 đến 63 độ); ngoài khoảng đó chỉ là ngoại suy.
  Nửa mặt xa camera: lông mày và mắt bị che từ YAW_MAT độ; môi (các điểm cùng bên) bị che từ YAW_MOI độ. Sống mũi và các điểm trên trục (side M) không bao giờ bị che.
VẬT THỂ CHE MẮT (mặt nhìn thẳng; kính râm, chai/cốc, tay...): đo trên ảnh cắt, vùng đa giác của mắt (lưới 478 điểm):
  gm = độ nét = trung bình độ lớn gradient (Sobel, ảnh xám đã làm mờ nhẹ) trong vùng mắt / khoảng cách hai khoé mắt ngoài * 100.
  Mắt bình thường có gm khoảng 25 đến 35 (trung vị 25 đến 34 trên 198 ảnh in-cabin); mắt bị kính đen hay vật mờ che chỉ còn 1 đến 6.
  Mắt bị che khi gm < GM_MAX, hoặc vùng mắt tối (độ sáng vùng / vòng da quanh nó < LUM_TOI) và gm < GM_TOI (mắt kính đen).
  Chỉ áp cho MẮT: đã xem tay các vùng thấp nhất; với miệng và lông mày, độ nét thấp chủ yếu là ảnh mờ hay tối, không phải bị che, nên không đoán.
  Là phép đoán: ảnh quá tối hay quá mờ (mắt nhắm trong bóng tối) vẫn có thể bị đánh dấu nhầm; người rà sửa occluded ngay trong CVAT.
Không phát hiện tay che miệng, khẩu trang, vật che lông mày (chưa có cách đáng tin).
"""
import numpy as np

NOSE, CHEEK_L, CHEEK_R = 1, 234, 454          # chỉ số trong lưới 478 điểm của MediaPipe
YAW_MAT = 60.0                                # độ: từ đây lông mày và mắt của nửa mặt xa camera bị che
YAW_MOI = 75.0                                # độ: từ đây môi của nửa mặt xa camera bị che
_A, _B = 0.0405, 0.08                         # |u| = _A * yaw - _B (hồi quy nói ở trên)
GM_MAX = 6.0                                  # độ nét vùng mắt dưới mức này: bị che
LUM_TOI, GM_TOI = 0.30, 10.0                  # vùng mắt tối hơn 0.30 lần vòng da quanh nó và độ nét dưới 10: kính đen
MAT_TRAI = (33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246)       # mắt của người ở nửa TRÁI ảnh (không soi gương)
MAT_PHAI = (362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398)
KHOE_NGOAI = (33, 263)                        # hai khoé mắt ngoài: đo khoảng cách hai mắt
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


def do_vung_mat(gray, pts478):
    """{'L': (gm, tuong_doi_sang), 'R': (...)}: độ nét và độ sáng tương đối của mắt ở nửa trái, nửa phải ảnh. gray: ảnh xám (numpy 2 chiều). Vùng ngoài ảnh hoặc quá nhỏ thì bỏ."""
    import cv2
    p = np.asarray(pts478, float)
    if gray is None or getattr(gray, "ndim", 0) != 2 or p.ndim != 2 or len(p) <= max(MAT_TRAI + MAT_PHAI):
        return {}
    g = gray.astype(np.float32)
    gm = cv2.magnitude(cv2.Sobel(cv2.GaussianBlur(g, (0, 0), 1.0), cv2.CV_32F, 1, 0), cv2.Sobel(cv2.GaussianBlur(g, (0, 0), 1.0), cv2.CV_32F, 0, 1))
    iod = float(np.linalg.norm(p[KHOE_NGOAI[0]] - p[KHOE_NGOAI[1]]))
    if iod < 8.0:
        return {}
    out = {}
    mx = {id(idx): p[list(idx), 0].mean() for idx in (MAT_TRAI, MAT_PHAI)}
    for idx in (MAT_TRAI, MAT_PHAI):
        pts = p[list(idx)]
        xa = "L" if mx[id(idx)] <= min(mx.values()) else "R"                    # mắt nằm bên trái ảnh hơn là 'L' (theo vị trí thật trong ảnh, không theo tên mắt của MediaPipe)
        m = np.zeros(g.shape, np.uint8)
        cv2.fillPoly(m, [pts.astype(np.int32)], 1)
        k, k2 = max(3, int(0.12 * iod)), max(3, int(0.30 * iod))
        ring = (cv2.dilate(m, np.ones((2 * k2 + 1, 2 * k2 + 1), np.uint8)) - cv2.dilate(m, np.ones((2 * k + 1, 2 * k + 1), np.uint8))).astype(bool)
        m = m.astype(bool)
        if m.sum() < 5 or ring.sum() < 5:
            continue
        out[xa] = (float(gm[m].mean() / iod * 100.0), float(g[m].mean() / (g[ring].mean() + 1e-6)))
    return out


def mat_bi_che(gray, pts478):
    """Các nửa ảnh ('L', 'R') có mắt bị vật thể che theo độ nét và độ sáng (xem đầu file)."""
    return {xa for xa, (gm, lum) in do_vung_mat(gray, pts478).items() if gm < GM_MAX or (lum < LUM_TOI and gm < GM_TOI)}


def diem_bi_che(pts478, cfg, gray=None):
    """Tên các điểm (trong 50 điểm của config) bị che, theo thứ tự trong config: (1) mặt nghiêng (tự che), (2) nếu có ảnh xám `gray` của ảnh cắt: mắt bị vật thể che.
    Mặt thẳng, mắt rõ hoặc không tính được thì []."""
    xa_mat = mat_bi_che(gray, pts478) if gray is not None else set()
    u = lech_mui(pts478)
    yaw, xa = (0.0, None) if u is None else (max(0.0, (abs(u) + _B) / _A), "L" if u < 0 else "R")
    out = []
    for p in cfg["points"]:
        reg, side = p.get("region"), p.get("side")
        if (side == xa and ((reg in VUNG_MAT and yaw >= YAW_MAT) or (reg in VUNG_MOI and yaw >= YAW_MOI))) or (reg == "eye" and side in xa_mat):
            out.append(p["name"])
    return out
