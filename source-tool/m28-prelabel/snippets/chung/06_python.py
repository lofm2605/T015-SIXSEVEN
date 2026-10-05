# Trích từ de-tai-m28/huong-dan-chung.md — mục: Lấy WFLW một lần, dùng chung. Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
# Ô Colab. Bạn khác (không phải P1): bỏ ba dòng pip, gdown, wget.
from google.colab import drive
drive.mount('/content/drive')
!mkdir -p /content/drive/MyDrive/M28
%cd /content/drive/MyDrive/M28
!pip install -q gdown
!gdown 1hzBd48JIdWTJSsATBEB_eFVvPL1bx6UC -O WFLW_images.tar.gz
!wget -q https://wywu.github.io/projects/LAB/support/WFLW_annotations.tar.gz
!mkdir -p /content/wflw && cp WFLW_*.tar.gz /content/wflw/
%cd /content/wflw
!tar -xzf WFLW_images.tar.gz && tar -xzf WFLW_annotations.tar.gz
!wc -l WFLW_annotations/list_98pt_rect_attr_train_test/*.txt   # 7500 và 2500
