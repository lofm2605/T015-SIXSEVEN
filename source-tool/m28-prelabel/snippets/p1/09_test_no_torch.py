# Trích từ de-tai-m28/p1-du-lieu.md — mục: Phần mới: lệnh m28.py (8–16/10) › Làm thế nào. Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
# test_no_torch.py – gói giao khách không được kéo theo torch/PIPNet
import sys
sys.path.insert(0, "tool")
import m28core.steps
assert "torch" not in sys.modules, "tool/ đang import torch"
print("ok: không có torch")
