@echo off
rem M28 - mot file de chay: cai moi truong (lan dau), tai model, mo trang ra soat. Nhap doi vao file nay trong Explorer.
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
title M28 - Nhan nhap landmark khuon mat

if not exist ".venv\Scripts\python.exe" call :cai_moi_truong
if errorlevel 1 goto :loi
call ".venv\Scripts\activate.bat"

if exist "face_landmarker.task" goto :co_model
if exist "tool\face_landmarker.task" goto :co_model
echo.
echo Chua co face_landmarker.task, dang tai (khoang 4 MB)...
curl -L -o face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
if errorlevel 1 goto :loi_model
:co_model

:menu
echo.
echo ================= M28 - Nhan nhap landmark khuon mat =================
echo   1. Mo trang ra soat   (Nap anh keo tha, Cac dot, Ca kho, Thong ke, Cai dat)
echo   2. Ra soat lai mot luot co san
echo   3. Chay thu 5 mat F in-cabin (chi can goi du lieu giai nen vao data\)
echo   4. Kiem tra nhanh CVAT   (tao roi xoa task demo-smoke, can CVAT dang chay)
echo   5. Chay test
echo   6. Cai lai moi truong Python
echo   7. Thoat
echo ======================================================================
choice /C 1234567 /N /M "Chon 1-7: "
if errorlevel 7 goto :het
if errorlevel 6 goto :cai_lai
if errorlevel 5 goto :test
if errorlevel 4 goto :smoke
if errorlevel 3 goto :thu5
if errorlevel 2 goto :luot
if errorlevel 1 goto :mo_trang
goto :menu

:hoi_nguoi
set "NGUOI="
set /p NGUOI=Ten nguoi ra (P1-P5, Enter = P1): 
if "%NGUOI%"=="" set "NGUOI=P1"
exit /b 0

:mo_trang
call :hoi_nguoi
echo.
echo Dang mo trang ra soat (chi may nay vao duoc, dia chi http://127.0.0.1:7860). Xong viec bam "Close page" tren trang.
python tool\review_app.py --nap %NGUOI%
goto :menu

:luot
call :hoi_nguoi
set "LUOT="
set /p LUOT=Ten luot (thu muc trong runs\, vi du F5 hoac NAP_001): 
if "%LUOT%"=="" goto :menu
if not exist "runs\%LUOT%" (
  echo Khong thay runs\%LUOT%
  goto :menu
)
python tool\review_app.py runs\%LUOT% %NGUOI%
goto :menu

:thu5
if not exist "data\manifest.csv" (
  echo Chua co data\manifest.csv: giai nen goi du lieu in-cabin (m28_incab_part*.zip^) vao thu muc data\ truoc.
  goto :menu
)
if not exist "data\crops\F_001.png" (
  echo Chua co data\crops\: giai nen du cac phan m28_incab_part*.zip vao thu muc data\ truoc.
  goto :menu
)
python -c "import csv;r=[x for x in csv.DictReader(open('data/manifest.csv',encoding='utf-8')) if x['set']=='F'][:5];w=csv.writer(open('data/f5_list.csv','w',newline=''));w.writerow(['image','face_idx','seed']);[w.writerow([x['image'],x['face_idx'],x['seed']]) for x in r]"
python tool\m28.py all --run F5 --list data\f5_list.csv --images data\crops --box crop --review auto --dry-run
echo.
echo Neu thay "Chay thu (--dry-run)" la dung. Ket qua: runs\F5\xml\prelabel.xml
goto :menu

:smoke
echo.
echo === Kiem tra nhanh CVAT ===
echo Can CVAT dang chay (Ubuntu WSL: docker compose up -d^) va token o tab Cai dat (bat Nho tren may nay^)
echo hoac bien moi truong trong cua so nay. Script se tao roi xoa task demo-smoke (4 anh xam gia, khong phai anh mat^)
echo trong project m28; neu chua co project m28 thi tao roi xoa lai khi con trong. Khong dung task khac.
choice /C CK /N /M "Chay kiem tra nhanh? (C = co, K = khong): "
if errorlevel 2 goto :menu
python tool\cvat_smoke.py
set "MA=%errorlevel%"
echo.
echo Ma thoat: %MA%
if not "%MA%"=="0" echo Co buoc HONG hoac loi: gui P4 file runs\_smoke\bao_cao_GIO.txt (khong gui token, khong gui anh).
pause
goto :menu

:test
python -m pip show pytest >nul 2>&1
if errorlevel 1 python -m pip install pytest
python -m pytest tests -q
goto :menu

:cai_lai
choice /C CK /N /M "Xoa .venv va cai lai tu dau? (C = co, K = khong): "
if errorlevel 2 goto :menu
if exist ".venv" rmdir /s /q ".venv"
call :cai_moi_truong
if errorlevel 1 goto :loi
call ".venv\Scripts\activate.bat"
goto :menu

:cai_moi_truong
echo.
echo === Cai moi truong Python lan dau (vai phut, can mang) ===
set "PYV="
py -3.14 --version >nul 2>&1
if not errorlevel 1 set "PYV=py -3.14"
if not defined PYV py -3.12 --version >nul 2>&1
if not defined PYV if not errorlevel 1 set "PYV=py -3.12"
if not defined PYV python --version >nul 2>&1
if not defined PYV if not errorlevel 1 set "PYV=python"
if not defined PYV (
  echo Khong tim thay Python. Cai Python 3.14 tu python.org (tick "Add python.exe to PATH" va "py launcher"^), roi chay lai file nay.
  exit /b 1
)
echo Dung %PYV%
%PYV% -m venv .venv
if errorlevel 1 exit /b 1
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
findstr /V /I "torch" requirements.txt > "%TEMP%\req_m28.txt"
python -m pip install -r "%TEMP%\req_m28.txt"
if errorlevel 1 exit /b 1
python -m pip install -r requirements-ui.txt
if errorlevel 1 exit /b 1
python -c "import mediapipe as mp; print('mediapipe', mp.__version__)"
if errorlevel 1 (
  echo mediapipe khong import duoc: thu cai Python 3.12 roi chon muc 5 (cai lai moi truong^).
  exit /b 1
)
exit /b 0

:loi_model
echo.
echo Khong tai duoc model. Tai tay file nay roi dat ten face_landmarker.task canh chay.bat:
echo https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
goto :loi

:loi
echo.
echo Co loi o tren. Doc thong bao, sua roi chay lai. Neu khong ro, gui P1: ban Windows (winver), python --version, va noi dung cua so nay (khong gui anh mat hay token).
pause
exit /b 1

:het
endlocal
exit /b 0
