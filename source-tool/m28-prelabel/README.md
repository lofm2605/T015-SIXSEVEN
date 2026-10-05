# m28-prelabel

**Giải quyết:** gán 50 điểm landmark khuôn mặt từ đầu trong CVAT rất chậm (mỗi mặt vài phút, 50 lần kéo
điểm). Đề tài M28 của đội — kế hoạch đầy đủ ở [`de-tai-m28/`](../../de-tai-m28/).

## Pain point
Gán tay 50 điểm/mặt: lâu, dễ lệch giữa người với người, dễ đổi chỗ trái/phải. Đội đo thời gian thật bằng
thí nghiệm ghép cặp 14–15/10 (gán tay so với sửa nhãn nháp, trên cùng khuôn mặt).

## Tool làm gì
Một lệnh `tool/m28.py` chạy offline trên CPU:

| Lệnh | Làm gì | Ai/máy |
|---|---|---|
| `prepare` | Cắt mặt, chạy MediaPipe (ảnh gốc + ảnh lật), đổi 478 → 50 điểm, gắn cờ `low_conf`, tự kiểm (autoqc), vẽ ảnh chồng | Tự động |
| `review` | Trang rà soát Gradio ở 127.0.0.1: mỗi mặt bấm Nhận / Gán tay / Bỏ ảnh | Người rà |
| `push` | Tạo task CVAT mới tên `demo-…`, nhập nhãn nháp đúng một lần | Tự động, trên CVAT của chính máy đó |
| `collect` | Sau khi gán: xuất nhãn, QC, ảnh chồng, báo cáo ngắn | Tự động |
| `all` | Cả chuỗi; dừng ở trang rà soát, gõ lại sau khi rà xong | |

## Cấu trúc (theo kế hoạch)
Mọi đường dẫn trong kế hoạch tính từ thư mục này:

```
m28-prelabel/
├── tool/          m28.py, m28core/, review_app.py, export.py (giao cho khách: không torch, không ảnh)
├── config/        m28_config.json (50 điểm), pipeline.json (không có bí mật)
├── snippets/      đoạn code + prompt mẫu trích từ kế hoạch, CHƯA chạy thử
├── data/          ảnh cắt, manifest, gt*.json        ← KHÔNG commit (repo công khai)
├── raw/ final/    file xuất CVAT                     ← KHÔNG commit
├── outputs/ runs/ backups/                           ← KHÔNG commit
├── requirements.txt / requirements-ui.txt
└── README.md
```

`snippets/<chung|p1…p5>/NN_<tên>.<đuôi>` — số thứ tự theo vị trí trong tab; dòng đầu mỗi file ghi trích
từ mục nào. Đây là điểm xuất phát để viết code thật, không phải code đã kiểm.

## Cài đặt và chạy
```bat
rem Chạy trong cmd, ở thư mục source-tool\m28-prelabel (đường dẫn ngắn, ví dụ C:\m28)
py -3.14 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
curl -L -o face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```
CVAT trên máy mình: xem mục "Cài CVAT trên máy mình (cả 5 người)" trong
[`huong-dan-chung.md`](../../de-tai-m28/huong-dan-chung.md). Token và địa chỉ CVAT chỉ đặt trong biến môi
trường `CVAT_ACCESS_TOKEN`, `CVAT_URL`.

## Đầu vào / đầu ra
- Vào: thư mục ảnh (hoặc danh sách ảnh WFLW + hộp mặt), `config/m28_config.json`.
- Ra: `runs/<run>/…` (ảnh chồng, cờ, `triage_<Pk>.csv`), task CVAT `demo-…`, file xuất `raw/<task>_<Pk>_<ngày>.xml`.

## Đã thử trên
Chưa có — cập nhật sau thí nghiệm 14–15/10 và lượt chạy tập R (16–18/10): thời gian trước/sau, số nháp hỏng
trang rà soát bắt được.

## Giới hạn
- Chỉ làm nháp cho mặt lớn nhất trong ảnh; ảnh nhiều người chọn "Gán tay".
- MediaPipe yếu với mặt nhỏ, nghiêng mạnh, bị che nhiều.
- Python 3.14 + mediapipe 1.0.1 mới thử trên một laptop; máy nào lỗi thì dùng Colab/Kaggle (không đưa
  dữ liệu khách hàng lên đó).

## Người viết
P1 (`m28.py`), P2 (model, trang rà soát), P3 (ánh xạ, đánh giá), P4 (CVAT, `push`/`collect`), P5 (thí nghiệm).
