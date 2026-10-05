# Trích từ de-tai-m28/p2-model.md — mục: Làm thế nào › MediaPipe gốc + lật (6/10). Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
import cv2, numpy as np, mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

opts = vision.FaceLandmarkerOptions(
    base_options=mp_python.BaseOptions(model_asset_path="face_landmarker.task"),
    running_mode=vision.RunningMode.IMAGE, num_faces=1)

def run_mp(lm, rgb):
    img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
    res = lm.detect(img)
    if not res.face_landmarks:
        return None                                   # ghi no_face
    h, w = rgb.shape[:2]
    return [[p.x * w, p.y * h] for p in res.face_landmarks[0]]  # 478 điểm, pixel

with vision.FaceLandmarker.create_from_options(opts) as lm:
    rgb = cv2.cvtColor(cv2.imread("data/X1_01.png"), cv2.COLOR_BGR2RGB)
    orig = run_mp(lm, rgb)
    flip = run_mp(lm, rgb[:, ::-1])                   # toạ độ ảnh lật, chưa bỏ lật
    print(mp.__version__, None if orig is None else len(orig))
