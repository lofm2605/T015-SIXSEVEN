# Trích từ de-tai-m28/p2-model.md — mục: Phần mới: tự dò khung mặt và trang rà soát (11–17/10) › Tự dò khung mặt. Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

opts = vision.FaceLandmarkerOptions(
    base_options=mp_python.BaseOptions(model_asset_path="face_landmarker.task"),
    running_mode=vision.RunningMode.IMAGE, num_faces=5)

def detect_face(lm, rgb):                 # rgb: mảng numpy H×W×3, màu RGB (cv2.imread trả BGR: đổi bằng cv2.cvtColor)
    h, w = rgb.shape[:2]
    rgb = np.ascontiguousarray(rgb)       # bắt buộc: mảng cắt/lật chưa copy làm MediaPipe đọc sai ảnh
    res = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    if not res.face_landmarks:
        return None                       # ghi no_face
    boxes = []
    for face in res.face_landmarks:       # toạ độ 0–1, đổi ra pixel
        xs = [p.x * w for p in face]; ys = [p.y * h for p in face]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
    return max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))  # mặt lớn nhất

# Dùng: mở model một lần cho cả thư mục
# with vision.FaceLandmarker.create_from_options(opts) as lm:
#     box = detect_face(lm, rgb)
