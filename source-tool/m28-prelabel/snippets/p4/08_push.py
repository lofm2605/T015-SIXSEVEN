# Trích từ de-tai-m28/p4-cvat.md — mục: Phần mới: push và collect (9–18/10) › Token. Đoạn mẫu trong kế hoạch, chưa chạy thử như một chương trình hoàn chỉnh.
# tool/m28core/push.py – khung tối thiểu (cvat-sdk 2.77)
import os, sys, json
from cvat_sdk import make_client
from cvat_sdk.core.proxies.tasks import ResourceType

def get_project(client, name, label_json):                # tìm theo tên, không ghi project_id vào file
    found = [p for p in client.projects.list() if p.name == name]
    if len(found) > 1:
        sys.exit(f"Có {len(found)} project tên {name}; xoá bản thừa")
    if found:
        return found[0].id
    labels = json.load(open(label_json, encoding="utf-8"))   # config/face50_label.json
    return client.projects.create({"name": name, "labels": labels}).id

def push(run_dir, task_name, nhan_imgs, tay_imgs, xml_path, project="m28", prefix="demo-",
         label_json="config/face50_label.json"):
    if not task_name.startswith(prefix):                  # prefix đọc từ config/pipeline.json
        sys.exit("Chỉ tạo task demo-…; không bao giờ đẩy vào task m28-")
    pj = os.path.join(run_dir, "push.json")
    if os.path.exists(pj):
        sys.exit("Run này đã push rồi, không tạo task thứ hai")
    url, token = os.environ.get("CVAT_URL", ""), os.environ.get("CVAT_ACCESS_TOKEN")
    print("CVAT:", url, "| token:", "có" if token else "thiếu")   # không in giá trị token
    if not token or not url.startswith(("http://", "https://")):
        sys.exit("Đặt CVAT_URL (ghi rõ http://) và CVAT_ACCESS_TOKEN rồi mở cmd mới")
    groups = [nhan_imgs[i:i + 8] for i in range(0, len(nhan_imgs), 8)]
    if tay_imgs:
        groups.append(tay_imgs)                            # job Gán tay riêng
    names = [[os.path.basename(p) for p in g] for g in groups]
    with make_client(url, access_token=token) as client:
        if os.environ.get("CVAT_ORG"):                     # chỉ ở công ty, khi project nằm trong organization
            client.organization_slug = os.environ["CVAT_ORG"]
        project_id = get_project(client, project, label_json)
        task = client.tasks.create_from_data(
            spec={"name": task_name, "project_id": project_id},   # không truyền labels
            resources=[p for g in groups for p in g],
            resource_type=ResourceType.LOCAL,
            data_params={"image_quality": 95, "job_file_mapping": names})
        info = {"task_id": task.id, "task": task_name, "cvat_url": url, "status": "created"}
        json.dump(info, open(pj, "w"))
        task.import_annotations("CVAT 1.1", xml_path)          # đúng một lần, task còn trống
        info["status"] = "imported"
        json.dump(info, open(pj, "w"))
        check = os.path.join(run_dir, "check.zip")
        task.export_dataset("CVAT for images 1.1", check, include_images=False)
    return check   # đọc bằng export.py, kiểm mỗi mặt Nhận đủ 50 tên điểm + low_conf
