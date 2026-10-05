# Trích từ de-tai-m28/p2-model.md — mục: Phần mới: tự dò khung mặt và trang rà soát (11–17/10) › Trang rà soát. Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
import os, sys, csv
RUN, WHO = sys.argv[1], sys.argv[2]                  # ví dụ runs/R1610 P5
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"     # không gửi thống kê
os.environ["GRADIO_TEMP_DIR"] = os.path.join(RUN, "_tmp")  # xoá sau khi rà
if "google.colab" in sys.modules or "KAGGLE_KERNEL_RUN_TYPE" in os.environ:
    sys.exit("Trang rà soát chỉ chạy trên Máy mình")
import gradio as gr

queue = load_queue(RUN)   # hàm bạn viết: [(ảnh chồng, "R_03 · 4 cờ · cần xem", tên file ảnh gốc), ...], mặt đáng ngờ lên đầu
items = [(p, c) for p, c, _ in queue]
os.makedirs(os.path.join(RUN, "review"), exist_ok=True)
with gr.Blocks() as app:
    grid = gr.Gallery(value=items, columns=5)
    big = gr.Image()
    reason = gr.Dropdown(["", "KHONG_MAT", "SAI_MAT", "MO_NHO", "LAT_GUONG", "DON_CUC", "LECH_VUNG", "QUAY_CHE", "NHIEU_MAT"], label="Lý do")
    with gr.Row():
        b_ok, b_tay, b_bo = gr.Button("Nhận"), gr.Button("Gán tay"), gr.Button("Bỏ ảnh")
    current = gr.State(0)
    def pick(evt: gr.SelectData):
        return items[evt.index][0], evt.index
    grid.select(pick, None, [big, current])
    def save(i, why, decision):
        with open(os.path.join(RUN, "review", f"triage_{WHO}.csv"), "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([queue[i][2], decision, why])   # tên file thật, push và triage_eval cần
    b_ok.click(lambda i, r: save(i, r, "nhan"), [current, reason], None)
    b_tay.click(lambda i, r: save(i, r, "gan_tay"), [current, reason], None)
    b_bo.click(lambda i, r: save(i, r, "bo"), [current, reason], None)
app.launch(server_name="127.0.0.1", share=False)   # luôn ghi rõ share=False
