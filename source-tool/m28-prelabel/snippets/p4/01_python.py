# Trích từ de-tai-m28/p4-cvat.md — mục: Làm thế nào › Task. Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
import os
from cvat_sdk import make_client

TASK_ID = 0  # điền id task trên CVAT của bạn
url, token = os.environ["CVAT_URL"], os.environ["CVAT_ACCESS_TOKEN"]  # url ghi rõ http://localhost:8080
with make_client(url, access_token=token) as client:   # không in token
    task = client.tasks.retrieve(TASK_ID)
    names = [f.name for f in task.get_frames_info()]
    for job in sorted(task.get_jobs(), key=lambda j: j.start_frame):
        imgs = names[job.start_frame:job.stop_frame + 1]
        blocks = sorted({n.split("_")[0] for n in imgs})
        print(job.id, len(imgs), blocks, imgs[0], imgs[-1])  # mỗi task: 1 job, 1 khối, đủ ảnh
