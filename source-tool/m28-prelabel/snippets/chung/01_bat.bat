rem Trích từ de-tai-m28/huong-dan-chung.md — mục: Dựng môi trường (Windows, Python 3.14). Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
rem Chạy trong cmd, không dùng PowerShell
py -3.14 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import mediapipe as mp; from mediapipe.tasks.python import vision; print(mp.__version__)"
curl -L -o face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
