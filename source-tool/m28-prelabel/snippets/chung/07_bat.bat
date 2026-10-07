rem Trích từ de-tai-m28/huong-dan-chung.md — mục: Chạy pipeline và trang rà soát. Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
rem Chạy trong cmd, ở thư mục repo
call .venv\Scripts\activate.bat
rem --images: thư mục khung gốc in-cabin trên máy bạn (data\frames); chỉ có gói thì data\crops kèm --box crop
python tool\m28.py prepare --run R1610 --list data\r_list_1610.csv --images data\frames --box auto
python tool\m28.py review --run R1610 --reviewer P5
rem Máy có CVAT_URL và CVAT_ACCESS_TOKEN (ở M28: CVAT của P4 cho tập R)
python tool\m28.py push --run R1610 --images data\frames --task demo-R1610 --review-file triage_P5.csv
python tool\m28.py collect --task demo-R1610
rem Task thí nghiệm: chỉ đọc file raw/ mọi người đã commit
python tool\m28.py collect --task m28-manual --task m28-assisted --tag 1610 --skip-export
