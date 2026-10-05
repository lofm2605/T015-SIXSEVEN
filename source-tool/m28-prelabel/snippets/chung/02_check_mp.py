# Trích từ de-tai-m28/huong-dan-chung.md — mục: Dựng môi trường (Windows, Python 3.14). Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
# check_mp.py
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

opts = vision.FaceLandmarkerOptions(
    base_options=mp_python.BaseOptions(model_asset_path="face_landmarker.task"),
    running_mode=vision.RunningMode.IMAGE, num_faces=1)
with vision.FaceLandmarker.create_from_options(opts) as lm:
    res = lm.detect(mp.Image.create_from_file("data/X1_01.png"))
    print(mp.__version__, len(res.face_landmarks[0]) if res.face_landmarks else "no face")
