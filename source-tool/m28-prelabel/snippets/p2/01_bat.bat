rem Trích từ de-tai-m28/p2-model.md — mục: Làm thế nào › Môi trường (5/10). Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
py -3.14 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install mediapipe==1.0.1 torch torchvision
rem Cả nhóm dùng CVAT v2.77.0 trên máy từng người, nên sdk và cli ghim đúng bản này
python -m pip install cvat-sdk==2.77.0 cvat-cli==2.77.0 pandas
python -c "import mediapipe as mp; from mediapipe.tasks.python import vision; print(mp.__version__)"
curl -L -o face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
python -m pip freeze > requirements.txt
