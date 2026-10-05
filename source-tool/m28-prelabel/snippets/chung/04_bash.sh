# Trích từ de-tai-m28/huong-dan-chung.md — mục: Cài CVAT trên máy mình (cả 5 người) › Phần B. Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
cd ~
git clone --branch v2.77.0 --depth 1 https://github.com/cvat-ai/cvat
cd cvat
git describe --tags      # phải in v2.77.0
echo "$CVAT_VERSION"     # phải in dòng trống
