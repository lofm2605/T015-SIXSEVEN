# Trích từ de-tai-m28/p4-cvat.md — mục: Làm thế nào › File nhập. Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
from xml.sax.saxutils import quoteattr

def image_xml(frame_id, name, names, pts, low):
    # names: 50 tên theo config; pts: 50 cặp (x, y) trên ảnh 512; low: 50 True/False
    assert len(names) == len(pts) == len(low) == 50
    out = [f'<image id="{frame_id}" name={quoteattr(name)} width="512" height="512">',
           '  <skeleton label="face50">']
    for n, (x, y), f in zip(names, pts, low):
        out.append(f'    <points label="{n}" occluded="0" outside="0" points="{x:.2f},{y:.2f}">'
                   f'<attribute name="low_conf">{"true" if f else "false"}</attribute></points>')
    out += ['  </skeleton>', '</image>']
    return "\n".join(out)
