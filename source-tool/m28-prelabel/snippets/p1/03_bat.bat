rem Trích từ de-tai-m28/p1-du-lieu.md — mục: Làm thế nào › 3. Lệnh m28.py (8–16/10) và đóng gói (19–21/10). Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
py -3.14 -m venv .venv-tool
call .venv-tool\Scripts\activate.bat
cd tool
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import mediapipe as mp; from mediapipe.tasks.python import vision; print(mp.__version__)"
python m28.py prepare --run mau5 --images mau5 --box auto
python m28.py push --run mau5 --dry-run
