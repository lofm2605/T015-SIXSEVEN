# P4 – CVAT

Bạn giữ phần CVAT của nhóm: sinh label face50, dựng mọi task thí nghiệm trên CVAT của bạn bằng script, nhập nhãn nháp một lần, sao lưu task thành file zip cho từng người (`backups/<Pk>/`), viết `export.py` cho cả nhóm, chạy script QC (kiểm tra chất lượng) và chia xem chéo từ file trong repo. Mỗi người tự cài CVAT trên máy mình (bạn cài trước, tối 5/10, và hỗ trợ 4 bạn), tự khôi phục task, tự gán và tự xuất. Lỗi ở khâu dựng của bạn làm hỏng dữ liệu cả nhóm, nên mọi việc chạy bằng script và kiểm bằng `check_backup.py`, không mở task bằng tay. Trong dự án thật, script sinh label, dựng task và file nhập của bạn dùng lại được cho bộ điểm bất kỳ và cho một CVAT chung (đổi `CVAT_URL` và token). Hàm cvat-cli giao khách hàng là cvat\_func.py của P1 (chạy model trên ảnh mới); hàm phương án B của bạn chỉ đọc kết quả có sẵn.

## Bạn nhận gì và giao gì

| Ngày | Nhận từ ai, cái gì | Giao cho ai, cái gì |
| --- | --- | --- |
| 5/10 | Cả nhóm: bản Windows, RAM, ổ C, ảo hoá (tin nhắn chữ) | Cả nhóm (đầu buổi): "CVAT v2.77.0, cvat-sdk/cvat-cli 2.77.0, Docker Engine trong Ubuntu WSL2". Cả nhóm (cuối buổi): lệnh cài đã chạy thật, ghi vào mục cài CVAT ở tab chung. P5: cách xem tên điểm khi di chuột (skeleton 3 điểm) |
| 6/10 | P3: file cấu hình, bảng 98→50. P1: ảnh cắt, manifest.csv | — |
| 7/10 | – | Cả nhóm: `backups/<Pk>/` có G (2 file mỗi người) và pilot gán tay (P1, P5); `backups/CHECK.txt` |
| 8/10 | P3: mp50.json, phần tập P (buổi thử chưa có cờ) | P1, P5 (trước phút 60): `export.py`. P1, P5 (cuối buổi): `backups/<Pk>/m28-pilot-assisted.zip` có nhãn nháp. Cả nhóm: `backups/all/m28-check.zip` |
| 9/10 | — | P1 (đầu buổi): `image_xml` (write\_xml.py); `export.py` đã giao 8/10. Cả nhóm: `backups/<Pk>/m28-manual.zip` (không nháp). P3 (cuối buổi): danh sách file G còn thiếu (mỗi người tự xuất G) |
| 10/10 | P1: `runs/F5/` có `xml/prelabel.xml` | P5: báo đủ 4 file pilot trong raw/ (P1, P5 tự xuất) |
| 11/10 | P1: `r_list_1810.csv` | Cả nhóm: `push.py` đạt/không |
| 12/10 | P3: mp50.json (từ 7/10). P2: flags.json cho X, D (từ 10/10; nếu họp chọn t\_flip thì bản mới gửi ngay sau họp); nếu họp 12/10 chọn PIPNet thì P2 giao thêm pip50.json cho X, D. P1: config đóng băng | P5: kết quả kiểm trên 5 máy (bản 2.77.0, `m28-check`, `CHECK.txt`). Cả nhóm: `backups/<Pk>/` thêm m28-practice, m28-assisted (dựng sau họp, từ commit có tag) |
| 13/10 | P5: facetimer.py. P1: `m28.py` bản có `all` | Cả nhóm: QC trên 5 file `raw/m28-practice_*` mọi người tự xuất. P1, P2: `autoqc.py` |
| 14, 15/10 | Cả nhóm: tự commit `raw/<task>_<Pk>_<ngày>.xml` (kèm `.txt`) ngay cuối khối | P3, P5: báo đủ 5 file `raw/` mỗi ngày |
| 16/10 | P2: tên mặt đáng ngờ từ bảng ảnh chồng. P1: `runs/R1610/`, tag `pipeline-mvp` | Cả nhóm: qc\_1610.csv, bảng ảnh chồng (`outputs/collect_1610/`, commit), `outputs/collect_1610.md`, 5 file `outputs/review_1610/<chủ mặt>.csv` (mặt của Pk do P(k+2) xem) |
| 17/10 | P1 (16/10): mã lỗi trên mặt của bạn trong `outputs/review_1610/P4.csv`. Cả nhóm: `final/<task>_<Pk>_1710.xml` tự xuất sau khi sửa. P5 (đầu buổi): `triage_P5.csv` | P3, P5: bộ nộp (ghép 10 file `final/` của 5 người), số lỗi đã sửa (từ cột "đã sửa"). P5: timing\_P4.csv, `push.json` |
| 18/10 | — (bạn tự sửa `demo-R1610`; P1 chạy demo nhỏ trên CVAT của P1) | P5: `outputs/collect_demo-R1610.md` |
| 19–21/10 | P3: module đánh giá, gt50.json. P1: cvat\_func.py (cuối 20/10) | P1: kết quả thử cvat\_func.py (21/10). P5: công sửa, bỏ sót, sửa thừa |
| 22–23/10 | P5: khung báo cáo, slide; ảnh demo (22/10, chỉ để trên máy bạn) | P5: phần CVAT, QC, mục Pipeline |

## Lịch của bạn

Tên file là tên gợi ý. raw/ giữ file xuất gốc, không bao giờ sửa.

**T2 5/10**

- [ ] **Đầu buổi (5 phút)** Đăng vào nhóm chat: "CVAT v2.77.0, cvat-sdk/cvat-cli 2.77.0, Docker Engine trong Ubuntu WSL2" và nhờ cả nhóm đăng bản Windows, RAM, ổ C trống, Virtualization (chỉ chữ). Rồi cài CVAT trên máy bạn theo mục cài CVAT ở tab chung (máy đầu tiên của nhóm; khoảng 60 phút, phần lớn là chờ tải) — chạy ở Máy mình — ra CVAT ở `http://localhost:8080`, token `m28-P4` trong biến môi trường — xong khi `curl -s http://localhost:8080/api/server/about` in 2.77.0 và từ điện thoại cùng Wi-Fi mở `http://<IP LAN của laptop>:8080` không kết nối được (thấy trang hay "404" là lộ: sửa ngay). Trong lúc chờ tải, sửa mục cài CVAT ở tab chung cho đúng lệnh bạn chạy.
- [ ] Cài venv chung từ requirements.txt của P2 (có cvat-sdk, cvat-cli 2.77.0) vào đầu buổi 6/10, khi P2 đã push — chạy ở Máy mình — ra venv dùng được — xong khi `python -c "import cvat_sdk"` chạy.
- [ ] (giờ thứ hai) Trên CVAT của bạn: dựng skeleton 3 điểm có checkbox low\_conf (nội dung như dòng 6/10), gán 1 ảnh có bật cờ, rồi sao lưu task (Actions → Backup), xoá, khôi phục (Create from backup) và xuất lại — chạy ở CVAT trên máy mình — ra `skeleton3.json`, ghi chú sao lưu/khôi phục — xong khi biết cờ có hiện không và sau khôi phục tên điểm, cờ còn nguyên. Hết giờ thì phần sao lưu dời lên đầu buổi 6/10.

**T3 6/10**

- [ ] (Đã làm ngày 5/10, bỏ qua dòng này.) Dựng skeleton (nhóm điểm nối nhau) 3 điểm, mỗi điểm checkbox low\_conf (cờ "model không chắc"); chép JSON tab Raw — chạy ở CVAT — ra skeleton3.json — xong khi biết cờ có hiện trên ảnh không và đã gửi P5 cách xem tên điểm.
- [ ] Viết make\_label.py — chạy ở Máy mình — ra face50\_label.json — xong khi dán vào project thử thấy 50 điểm hình mặt.
- [ ] (giờ thứ hai, dời từ 7/10) Trong project thử đó: tạo task 1 ảnh cắt F (có từ đầu buổi), gán tay 1 mặt, xuất mẫu `mau_1mat.xml`. Rồi viết `config/tasks.json` (mỗi người: tên task, khối, danh sách file, có nháp hay không, ngày khôi phục; theo mục Task ở dưới) và bản đầu `tool/build_backups.py` có hàm `create_task(entry)` — chạy ở CVAT trên máy mình và Máy mình — ra `mau_1mat.xml`, `config/tasks.json`, `build_backups.py` bản đầu — xong khi script tạo được 1 task thử từ 1 dòng của `tasks.json` trong project thử, sao lưu ra zip và xoá đúng task đó theo id.

**T4 7/10**

- [ ] Đầu buổi (khoảng 45 phút): làm xong `tool/build_backups.py` (bản đầu và `config/tasks.json` đã có từ 6/10). Lần đầu chạy, script tạo project `m28` trên CVAT của bạn từ `face50_label.json` (label sinh từ config, không tạo tay); với mỗi dòng, script tạo task trong project đó (lexicographical, segment size = số ảnh, image\_quality 95, use\_cache bật), nhập nháp một lần nếu dòng có nháp, sao lưu ra `backups/<Pk>/<task>.zip`, rồi xoá đúng task vừa dựng theo id mà `create_from_data` trả về (không tìm theo tên; task dựng nằm trong project `m28`, task bạn khôi phục để gán thì không); không mở task nào. Chạy cho G (10 file) và pilot gán tay (2 file). `tool/check_backup.py` bản tối thiểu đọc các zip: đúng ảnh của khối, task không nháp có 0 điểm, cùng dấu vân tay label (tên, loại, thuộc tính, không dùng id); phần thông số task và mã băm thêm ngày 9/10 — chạy ở Máy mình + CVAT trên máy mình — ra 12 file zip, `backups/CHECK.txt` — xong khi CHECK.txt sạch, đã commit và báo P1, P5 (gán G 8/10). Script trễ thì dựng tay trong giao diện, trong project `m28` (New task cùng thông số → Actions → Backup), khoảng 3 phút mỗi task; chỉ cho task tuần 1 (G, pilot), task X luôn dựng bằng script.
- [ ] (giờ thứ hai) Bắt đầu write\_xml.py từ `mau_1mat.xml` (mặt mẫu đã gán và xuất ở giờ thứ hai 6/10; đầu buổi hôm nay chỉ dựng và kiểm backup) — chạy ở Máy mình — ra write\_xml.py nháp — xong khi script ghi được 1 mặt.

**T5 8/10**

- [ ] **Đầu buổi, phút 5–60 (làm trước mọi việc khác: P1, P5 cần nó ngay tối nay)** Viết `tool/export.py` bản 1 cho cả nhóm, chỉ làm đúng chuỗi này: `python tool\export.py <task> <Pk> <ngày>` tìm task theo tên trên CVAT ở `CVAT_URL` (0 hoặc 2 task trùng tên thì dừng), xuất "CVAT for images 1.1" chỉ nhãn (`include_images=False`), ghi `raw/<task>_<Pk>_<ngày>.xml` và một file `.txt` cùng tên (bản server, tên task, số ảnh, giờ tạo task theo giờ Việt Nam), không ghi đè file đã có. Kiểm 50 tên điểm, in lệnh git, `--final` và `--check` thêm đầu buổi 9/10 — chạy ở Máy mình và CVAT trên máy mình — ra export.py — xong khi export.py xuất được 1 task trên CVAT của bạn, đã commit trước phút 60 và đã báo P1, P5 trong nhóm chat. Trễ thì P1, P5 không chờ: họ xuất bằng giao diện theo tab chung (mục cài CVAT, "Dùng hằng ngày").
- [ ] (sau phút 60) Thử khứ hồi (nhập rồi xuất lại) 5 mặt F trên CVAT của bạn bằng write\_xml.py và export.py — chạy ở Máy mình và CVAT trên máy mình — ra so\_khu\_hoi.csv — xong khi 250 điểm đúng tên, lệch ≤ 0,01 px, thấy cờ.
- [ ] Dựng `backups/P1/m28-pilot-assisted.zip` (Pb + nháp), `backups/P5/m28-pilot-assisted.zip` (Pa + nháp) và `backups/all/m28-check.zip` (2 mặt F có nháp, bật thử cờ ở vài điểm vì F không có trong flags.json, để 5 máy kiểm cờ hiện) bằng `build_backups.py` — chạy ở Máy mình + CVAT trên máy mình — ra `prelabel_pilot.xml`, 3 file zip, CHECK.txt — xong khi check\_backup báo mỗi mặt có nháp đủ 50 tên điểm có `low_conf`, đã commit và báo P1, P5. Không mở task dựng. Lỗi thì báo P5, sang phương án B.

**T6 9/10 – gán chung**

- [ ] Đầu buổi (khoảng 15 phút) commit `write_xml.py` (có `image_xml`), báo P1. Thêm vào `export.py`: kiểm số ảnh và 50 tên điểm có `low_conf`, in các lệnh git chỉ cho hai file vừa ghi, `--final` (ghi vào `final/`) và `--check` (chỉ in thông tin; từ chối nếu bản server khác 2.77.0, trừ khi thêm `--allow-version` cho máy dự phòng CVAT Online đã duyệt); commit, báo nhóm — chạy ở Máy mình (repo) — xong khi P1 import được `image_xml` và `export.py --check` chạy được trên CVAT của bạn.
- [ ] Đầu khối khôi phục `backups\P4\m28-gold-x.zip` và `backups\P4\m28-gold-y.zip`; gán tay G4 (m28-gold-x) và G5 (m28-gold-y) — chạy ở CVAT trên máy mình — ra 8 mặt, `raw/m28-gold-x_P4_0910.xml`, `raw/m28-gold-y_P4_0910.xml` — xong khi 8 mặt qua checklist cuối mặt, đã tự xuất và commit.
- [ ] Cuối buổi `git pull`, `dir raw\m28-gold-*` (cần 10 file: P1, P5 từ 8/10; P2, P3, P4 tối nay), đăng vào nhóm ai còn thiếu — chạy ở Máy mình — xong khi đã báo P3. Bạn không xuất hộ được, vì CVAT của mỗi người nằm trên máy người đó. Trước 10/10 bạn cũng khôi phục `backups\all\m28-check.zip` trên CVAT của mình như 4 bạn (tab chung, bước 12) và đăng "CVAT ok 2.77.0"; giữ task tới họp 12/10 để chiếu, rồi xoá.
- [ ] (giờ thứ hai) Thêm vào `check_backup.py` phần đọc thông số task (segment size, image\_quality, sorting\_method, storage\_method, thứ tự file) và mã băm từng file. Rồi dựng 5 file `backups/<Pk>/m28-manual.zip` (X1…X5, không nháp; không cần cờ nên dựng sớm) bằng `build_backups.py`, chạy `check_backup.py` (mỗi file 0 điểm; `CHECK.txt` ghi commit đã dựng và thông số task để ngày 12/10 so với `m28-assisted`) và commit. Cùng script cvat-sdk đã chạy từ 7/10 (G, pilot); hôm nay chỉ thêm 5 dòng `m28-manual` — chạy ở Máy mình + CVAT trên máy mình — ra 5 file zip, CHECK.txt — xong khi CHECK.txt sạch. Không ai khôi phục các file này trước buổi của mình (14/10 hoặc 15/10).

**T7 10/10**

- [ ] Không còn xuất pilot: P1, P5 tự xuất 4 file pilot. Cuối buổi `git pull`, kiểm đủ 4 file `raw/m28-pilot-*` và báo P5 — chạy ở Máy mình — xong khi P5 nhận.
- [ ] Viết qc.py, chỉnh ngưỡng trên 40 lượt G — chạy ở Máy mình — ra qc\_G.csv — xong khi mặt đúng (mắt nhắm, miệng khép, nghiêng) không bị báo.

**CN 11/10** (khung chung 2 tiếng)

- [ ] Viết bước push (`tool/m28core/push.py`, khung ở cuối tab) — chạy ở Máy mình + CVAT trên máy mình — ra `push.py`, task `demo-pipe-test` với 5 ảnh cắt F (đúng các ảnh mà `runs/F5/xml/prelabel.xml` dùng) — xong khi 1 ảnh mở ra đủ 50 điểm đúng tên, có `low_conf`, và chạy lần 2 bị từ chối. Xong thì xoá task `demo-pipe-test` (kiểm đúng tên trước khi xoá) và file `push.json` vừa ghi trong `runs/F5/` cho gọn; không commit file này, vì `runs/F5/` là thư mục đã commit (có `push.json` thì push sau đó trên mọi máy bị từ chối). Token đã có từ 5/10. Bước push làm lần lượt:
  1. Kiểm an toàn: tên task bắt đầu bằng `demo-` (nên tên `m28-…` luôn bị từ chối); lượt chạy chưa có `push.json`; có token trong biến môi trường. Sai một điều thì dừng.
  2. Tìm project `m28` theo tên; máy chưa có (ví dụ CVAT của P1 ngày 18/10) thì tạo từ `config/face50_label.json` (`client.projects.create`). Tạo task mới trong project đó và tải ảnh lên (`create_from_data`), chia job bằng `job_file_mapping`: job Nhận và job Gán tay riêng. Ghi ngay `push.json` (id task, `cvat_url`).
  3. Nhập nhãn nháp đúng một lần: `import_annotations("CVAT 1.1", …)`.
  4. Xuất lại chỉ nhãn (`include_images=False`), đọc bằng export.py, kiểm mỗi mặt Nhận đủ 50 tên điểm.

**T2 12/10**

- [ ] 20 phút đầu, họp điểm dừng: trình kết quả kiểm trên 5 máy (mỗi người đã đăng "CVAT ok 2.77.0" sau khi khôi phục `m28-check` và thấy đúng tên, thứ tự, cờ, theo bước 12 ở tab chung; bản server cũng nằm trong file `.txt` kèm các file G trong `raw/`), `CHECK.txt` của các file đã dựng, khứ hồi buổi thử P1, P5; chia sẻ màn hình 1 mặt F có nháp trên CVAT của bạn — chạy ở họp — ra đạt/không — xong khi P5 ghi kết luận.
- [ ] Giờ thứ hai (từ phút 65; P2 commit `flags.json` và P1 gắn tag ngay sau họp, trước phút 60), khi P2 đã commit `flags.json` và P1 đã gắn tag: `git checkout` đúng tag, chạy `build_backups.py` cho 5 `m28-practice` (mỗi người 4 mặt D của mình: 3 có nháp, mặt thứ tư không nháp) và 5 `m28-assisted` (X(k+1) cho Pk, X1 cho P5; có nháp, cờ theo quyết định họp), rồi `check_backup.py`. Script tự tạo, nhập, sao lưu, xoá; bạn không mở task nào, kể cả X5 của bạn. Bạn gán tay X4 ngày 15/10: script không in hay vẽ toạ độ, và bạn không mở zip của người khác. `CHECK.txt` ghi cho từng file: tag git đã dựng, mã băm file nháp đã dùng (`mp50.json` hoặc `pip50.json`, `flags.json`), thông số task (segment size, image\_quality, sorting\_method, storage\_method = "cache" (tức use\_cache bật), thứ tự file), số điểm, dấu vân tay label, mã băm file zip. `check_backup.py` dừng nếu `m28-manual` (dựng 9/10) và `m28-assisted` của cùng khối khác nhau ở bất kỳ thông số nào ngoài nhãn nháp; khác thì dựng lại 5 `m28-manual` từ cùng tag (script tự chạy, khoảng 10 phút) — chạy ở Máy mình + CVAT trên máy mình — ra 10 file zip (15 nếu dựng lại `m28-manual`), `CHECK.txt` — xong khi CHECK.txt sạch, đã commit và báo nhóm: "Không ai khôi phục task tuần 2 tối nay".

**T3 13/10 – gán chung**

- [ ] Đầu buổi khôi phục `backups\P4\m28-practice.zip` (D\_13–D\_16); làm quen 4 mặt D (3 nháp, 1 tay) với facetimer.py, tự xuất và commit; đầu giờ thứ hai (phút 65), khi 4 bạn đã commit file làm quen, `git pull` và chạy qc.py trên 5 file `raw/m28-practice_*` mọi người đã commit — chạy ở CVAT trên máy mình và Máy mình — ra qc\_practice.csv — xong khi qc.py chạy hết 5 file không lỗi; ai thiếu file thì báo người đó.
- [ ] (giờ thứ hai) Bước autoqc: máy tự kiểm nhãn nháp trước khi người rà.
  1. Tách 5 phép kiểm của qc.py thành hàm `check_face(pts)`. Đầu vào là `{tên điểm: [x, y]}`, không cần XML.
  2. Bước autoqc của m28.py ghi `runs/<run>/autoqc/autoqc.csv`, mỗi mặt một dòng: tên file, gợi ý, số cờ, và ba cột trống `decision`, `reason`, `seconds`. File này là mẫu để người rà điền bằng Excel khi không có Gradio.
  3. Cách gợi ý: không thấy mặt (`no_face`), lật gương hoặc dồn cục → nên gán tay; 0 cờ và qua QC → ổn; còn lại → cần xem.

  — chạy ở Máy mình — ra `tool/m28core/autoqc.py` — xong khi 30 mặt D có gợi ý và mặt đúng của G không bị báo lỗi; báo P1, P2.

**T4 14/10 – lượt 1**

- [ ] Đầu buổi khôi phục `backups\P4\m28-assisted.zip` (X5, có nháp), rồi mới bật facetimer; sửa nháp X5, đọc câu chung, không mở đáp án, không xem tổng giờ — chạy ở CVAT trên máy mình + Máy mình (facetimer.py) — ra 10 dòng trong timing\_P4.csv, `raw/m28-assisted_P4_1410.xml` — xong khi Enter mặt thứ 10, đã tự xuất và commit.
- [ ] Cuối buổi `git pull`, kiểm đủ 5 file `raw/*_1410.xml` (mỗi file 10 mặt), nhắc ai còn thiếu — chạy ở Máy mình — xong khi đủ 5 file.
- [ ] (giờ thứ hai, chỉ viết code, không mở ảnh có nhãn nháp) Khung `collect`: với task thí nghiệm, đọc file `raw/<task>_<người>_<ngày>.xml` mọi người đã commit (`--skip-export`; mỗi cặp task, người lấy file mới nhất); chỉ task nằm trên CVAT của chính máy này (task `demo-…`) mới gọi export.py. Rồi chạy qc.py, overlay.py của P2 vẽ vào `outputs/collect_<tag>/`; ghi báo cáo ngắn `outputs/collect_<tag>.md` (không có `--tag` thì dùng tên task): số mặt, file còn thiếu, lỗi QC theo loại, danh sách mặt bị đánh dấu, thời gian từng bước. Ghép theo tên ảnh và tên điểm, không theo id; chỉ xuất, không bao giờ nhập — chạy ở Máy mình — ra `tool/m28core/collect.py` — xong khi `collect --task m28-gold-x --tag thu --skip-export` chạy trên file G có sẵn trong `raw/` và ra `outputs/collect_thu.md`.

**T5 15/10 – lượt 2**

- [ ] Đầu buổi khôi phục `backups\P4\m28-manual.zip` (X4, không nháp); gán tay X4, tự xuất `raw/m28-manual_P4_1510.xml` và commit; cuối buổi kiểm đủ 5 file `raw/*_1510.xml` — chạy ở CVAT trên máy mình và Máy mình — ra timing\_P4.csv, file raw của bạn — xong khi đủ 5 file, mỗi file 10 mặt.

**T6 16/10 – gán chung**

- [ ] Đầu buổi, làm theo thứ tự:
  1. (phút 5–15) Chạy `python tool/m28.py collect --task m28-manual --task m28-assisted --tag 1610 --skip-export` trên file raw/ của 14–15/10. Lệnh ra kết quả QC, bảng ảnh chồng cho P2 quét và `outputs/collect_1610.md`. Commit ngay `outputs/collect_1610/` và `outputs/collect_1610.md`, báo P2 (khoảng phút 15) để P2 `git pull` rồi quét. Collect lỗi thì chạy qc.py như cũ và báo P2 tự chạy overlay.py.
  2. Tạo 5 file `outputs/review_1610/<chủ mặt>.csv` (cột: face\_id, task, điểm, mã lỗi, người xem, đã sửa) từ `collect_1610.md` và danh sách P2 gửi, thêm 1 mặt ngẫu nhiên mỗi task. Người xem cố định: mặt của Pk do P(k+2) xem (P1 xem P4, P2 xem P5, P3 xem P1, P4 xem P2, P5 xem P3). Commit 5 file này (bảng ảnh chồng đã commit từ phút 15), báo nhóm chậm nhất khoảng phút 45.
  3. Xem chéo mặt của P2 (`outputs/review_1610/P2.csv`) trên bảng ảnh chồng và ảnh cắt: mặt bị đánh dấu, cộng 1 mặt ngẫu nhiên mỗi task. Ghi mã SWAP, MIRROR, COLLAPSE, MISPLACED, OCC\_FLAG, RULE vào file đó, commit.

  Mặt bù làm trong tối nay: người bù tự xuất vào `raw/<task>_<Pk>_1610.xml` và commit trước khi `git pull` hay mở bảng ảnh chồng; bạn chạy lại collect và thêm các mặt này vào file xem chéo đầu buổi 17/10.

  — chạy ở Máy mình (xem chéo trên bảng ảnh chồng) — ra qc\_1610.csv, 5 file `outputs/review_1610/`, mã lỗi trên mặt của P2 — xong khi mọi mặt trong `outputs/review_1610/P2.csv` có mã hoặc "OK".
- [ ] (giờ thứ hai) Cài `requirements-ui.txt` theo tab chung; tải WFLW từ MyDrive/M28/ về máy nếu chưa có (push tập R tải ảnh gốc lên CVAT) — chạy ở Máy mình — xong khi `check_mp.py` vẫn in 1.0.1, 478 và có thư mục WFLW\_images.

**T7 17/10**

- [ ] Sửa mặt của bạn theo `outputs/review_1610/P4.csv` trên CVAT của bạn, tự xuất lần 2 vào `final/` (`export.py … --final`); khi P5 báo đã commit `triage_P5.csv` (khoảng phút 25) làm luôn việc push R1610 bên dưới; cuối buổi `git pull`, kiểm đủ 10 file `final/*_1710.xml` và đếm số lỗi đã sửa từ cột "đã sửa" — chạy ở CVAT và Máy mình — ra bộ nộp, số lỗi đã sửa — xong khi P3, P5 nhận.
- [ ] (làm trong lúc chờ cả nhóm sửa, khoảng phút 25) Đẩy tập R khi P5 đã báo commit `triage_P5.csv` (P5 rà lúc đầu buổi): `git pull`, rồi `python tool/m28.py push --run R1610 --images <WFLW_images> --task demo-R1610 --review-file triage_P5.csv` — chạy ở Máy mình + CVAT trên máy mình — ra task `demo-R1610`, `push.json` (commit) — xong khi 1 mặt Nhận mở ra đủ 50 điểm có `low_conf`, mặt Gán tay nằm trong job riêng, không có điểm. Task chỉ nằm trên CVAT của bạn nên không giao job: ngày 18/10 bạn sửa khoảng 5 mặt của job 1, các job còn lại để trống (việc thêm nếu dư giờ).
- [ ] (giờ thứ hai, khoảng 20 phút) Tập dượt demo trên máy bạn: `python tool/m28.py all --run thu1710 --list data/r_list_1810.csv --images <WFLW_images> --box auto --task demo-thu1710` → trang rà soát mở → bấm vài mặt, Xong, Ctrl+C → chạy lại đúng lệnh → task được tạo → chạy lần ba thấy push từ chối. Rồi xoá task `demo-thu1710` trong CVAT (kiểm đúng tên) và thư mục `runs/thu1710` — chạy ở Máy mình + CVAT — xong khi cả chuỗi chạy không lỗi. Lỗi thì báo P1, P2; demo 18/10 vẫn còn `--review excel` và `--review auto`.

**CN 18/10** (khung chung 2 tiếng)

- [ ] Phút 0–30: sửa khoảng 5 mặt đầu của job 1 trong `demo-R1610`, đặt job completed — chạy ở CVAT — xong khi đã lưu.
- [ ] Phút 30–60: demo cho mentor: `python tool/m28.py all --run R1810 --list data/r_list_1810.csv --images <WFLW_images> --box auto --task demo-R1810` → trang rà soát (10 mặt) → Xong → chạy lại → task `demo-R1810`; chạy lại lần nữa để thấy push từ chối; mở CVAT cho mentor xem bộ lọc `low_conf` (bản 2.77.0 của nhóm) — chạy ở Máy mình + CVAT, chia sẻ màn hình (tắt ghi hình và trợ lý AI ghi chú của phần mềm họp) — xong khi mentor đã xem.
- [ ] Phút 60–80: `python tool/m28.py collect --task demo-R1610` (xuất thật từ CVAT của bạn) — chạy ở Máy mình + CVAT trên máy mình — ra `raw/demo-R1610_*`, QC, bảng ảnh chồng, `outputs/collect_demo-R1610.md` (job chưa sửa báo riêng) — xong khi collect chạy hết không lỗi; báo P5.

**T2 19/10**

- [ ] Công sửa: so file nhập với raw/ của m28-assisted theo tên điểm, bằng module của P3 — chạy ở Máy mình — ra cong\_sua.csv (giữ nguyên ≤ 0,5 px / chỉnh nhẹ / sửa ra ngoài sai số) — xong khi tổng ba nhóm bằng số điểm nháp.

**T3 20/10**

- [ ] Bỏ sót: trong điểm nháp sai quá sai số, bao nhiêu % vẫn sai khi xuất; tách có cờ/không cờ, theo vùng — chạy ở Máy mình — ra bo\_sot.csv, thêm sửa thừa (% điểm nháp cách đáp án ≤ 1 px mà vẫn bị dời; hàm correction\_stats của P3 đã tính) — xong khi P5 nhận.

**T4 21/10**

- [ ] Chạy cvat-cli task auto-annotate \<id task> --function-file cvat\_func.py của P1 (bản CLI cũ viết cvat-cli auto-annotate; xem cvat-cli --help của bản đã cài) trên task thử 5 ảnh chưa có nhãn, không dùng --clear-existing — chạy ở Máy mình + CVAT — ra ghi chú đạt/không gửi P1 — xong khi task thử có đủ 50 điểm đúng tên, có cờ.

**T5 22/10**

- [ ] Viết phần CVAT, QC, công sửa, bỏ sót của báo cáo nháp — chạy ở Máy mình — ra đoạn báo cáo — xong khi P5 nhận.
- [ ] Thêm mục Pipeline cùng P1: các bước push/collect, token qua biến môi trường, quy tắc chỉ đẩy vào task mới `demo-…`, một máy cho ảnh khách hàng, thời gian từng bước từ `push.json`, `log.txt` và `outputs/collect_demo-R1610.md`.

**T6 23/10**

- [ ] Slide phần CVAT; trên máy bạn chạy `m28.py all` trên ảnh demo của P5 (cả bốn lệnh trên một máy, như với ảnh khách hàng) và chạy auto-annotate trong demo theo P5; tập dượt — chạy ở CVAT — ra slide — xong khi tập dượt trọn không lỗi.

**T7 24/10**

- [ ] Kiểm repo đủ script, `raw/`, `final/`, các CSV, `CHECK.txt`. Khi P5 xác nhận đã nộp, nhắc cả nhóm dọn máy theo tab chung (thu hồi token, xoá biến môi trường, `docker compose down -v` trong `~/cvat`) và tự làm trên máy bạn; xoá ảnh demo và `runs/` của lượt demo khỏi máy; xoá thư mục `backups/` khỏi nhánh chính (file vẫn còn trong lịch sử git của repo nội bộ) — chạy ở Máy mình — ra danh sách đã kiểm — xong khi P5 xác nhận nộp và cả 5 người đã báo dọn xong.

## Làm thế nào

**Label face50.** Chép đúng cấu trúc JSON của skeleton 3 điểm, đừng đoán, trừ hai chỗ: bỏ mọi khoá `"id"`, và trong `svg` mỗi nút ghi `data-label-name="<tên điểm>"` (không có `data-label-id`). Khi tạo project, CVAT chỉ nối nút với điểm theo tên; `data-label-id` chép từ tab Raw là id của máy cũ, nên project tạo trên máy khác (CVAT của P1 ngày 18/10) sẽ mất cạnh nối. make\_label.py sinh:

- 50 sub-label (điểm con) theo tên và thứ tự config, mỗi điểm một checkbox low\_conf;
- màu theo bên R/L/M; cạnh chỉ nối điểm liền nhau trên cùng đường cong (cột line trong config);
- toạ độ khuôn = hình trung bình 50 điểm trong config.

Cờ không hiện trên ảnh thì thêm thuộc tính chữ low\_conf\_pts cấp skeleton, trước 7/10.

**Task.** Sắp xếp lexicographical (theo tên file). Mỗi task chỉ chứa khối của một người, segment size = số ảnh của task (G 4, P 8, X 10, D 4), nên mỗi task có đúng một job. image\_quality 95, use\_cache bật. Ai nhận gì (thay cho quy tắc giao job): gold-x Gk → Pk; gold-y G(k+1) → Pk, G1 → P5; manual Xk → Pk; assisted X(k+1) → Pk, X1 → P5; pilot-manual Pa → P1, Pb → P5; pilot-assisted Pb → P1, Pa → P5; practice D\_01–D\_04 → P1, D\_05–D\_08 → P2, D\_09–D\_12 → P3, D\_13–D\_16 → P4, D\_17–D\_20 → P5. Ghi đủ vào `config/tasks.json`. `build_backups.py` dùng đúng một hàm `create_task(entry)` cho mọi task, nên hai điều kiện thí nghiệm có cùng thông số và chỉ khác bước nhập nháp. Nếu sao lưu/khôi phục hỏng, mỗi người chạy `build_backups.py --person Pk --local` trên máy mình (cùng hàm; chỉ nhập nháp vào task có nháp của người đó, đầu buổi của task đó). Code kiểm danh sách ảnh dưới đây chưa được kiểm: chạy thử trên task nháp trước.

```python
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
```

**File nhập.** Mỗi point phải có occluded (bị che) = 0, outside (ngoài ảnh) = 0 và low\_conf; thiếu là nhập lỗi. name trùng tên file trong task; id lấy từ danh sách frame của task dựng trên CVAT của bạn. Phần đầu file chép từ mau\_1mat.xml. Nhập một lần vào task dựng, trước khi sao lưu; 5 máy nhận nháp qua file zip, không ai nhập lại.

```python
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
```

**Xuất.** `export.py` là công cụ cả nhóm chạy trên CVAT của mình: tìm task theo tên, xuất "CVAT for images 1.1" chỉ nhãn (`include_images=False`) vào `raw/<task>_<Pk>_<ngày>.xml` (`--final`: `final/`) kèm file `.txt` cùng tên (bản server, số ảnh, giờ tạo task theo giờ Việt Nam), không ghi đè. So điểm theo tên ảnh và tên điểm, không theo vị trí hay id (id khác nhau giữa các máy). Chỉ tính là dời khi lệch > 0,5 px.

**QC 5 kiểm** (CSV: mặt, điểm, lỗi):

1. Thiếu điểm, sai tên so với config, hoặc outside = 1.
2. Gương (mặt bị lật trái–phải): đi từ mắt R sang mắt L rồi xuống miệng; hướng quay phải giống khuôn. Code dưới so hướng này; khác hướng là lỗi.
3. Đường cong: hai đoạn liền nhau quay ngược (góc gãy hơn 90°, thường do hai điểm đổi chỗ), hoặc đường tự cắt.
4. Dồn cục: hai điểm cách nhau < 1% bề rộng hộp mặt, trừ cặp được trùng trong config.
5. Lệch hình: khớp đồng dạng (dời, xoay, co giãn) với hình trung bình F; phần dư > 3 lần độ lệch chuẩn của điểm đó trên F. Bản lật khớp tốt hơn thì báo đảo trái phải.

```python
import numpy as np

def cross_sign(p, eye_R, eye_L, mouth):
    # p: mảng (50, 2); eye_R, eye_L, mouth: danh sách chỉ số điểm lấy từ config
    eR, eL, m = p[eye_R].mean(0), p[eye_L].mean(0), p[mouth].mean(0)
    a, b = eL - eR, m - (eR + eL) / 2
    return np.sign(a[0] * b[1] - a[1] * b[0])

def is_mirrored(p, template, eye_R, eye_L, mouth):
    return cross_sign(p, eye_R, eye_L, mouth) != cross_sign(template, eye_R, eye_L, mouth)
```

**Phương án B.** `cvat-cli task auto-annotate <id task> --function-file <file>.py` chạy một hàm Python trên từng ảnh của task (bản CLI cũ viết `cvat-cli auto-annotate`). Hàm của bạn không chạy model. Nó đọc mp50.json (điểm, của P3) và flags.json (cờ, của P2) theo tên frame, rồi trả skeleton face50 đủ 50 điểm kèm low\_conf. Chạy trên task dựng ở CVAT của bạn, trước khi sao lưu; 5 máy vẫn nhận qua file zip. Chỉ chạy trên task chưa có nhãn, không dùng --clear-existing. Docs: https://docs.cvat.ai/docs/api\_sdk/sdk/auto-annotation/

## Chạy ở đâu

- CVAT trên máy bạn: dựng task, nhập nháp, sao lưu (bằng script), gán. Xem chéo làm trên bảng ảnh chồng.
- Máy mình (Python 3.14, CPU): mọi script. Chúng chỉ xử lý toạ độ, chạy vài giây.
- Colab, Kaggle: không dùng. Bạn không cần GPU, và không được đưa đáp án hay file xuất lên đó.

cvat-sdk lỗi trên 3.14 thì dùng venv 3.12 dự phòng của P2. Không tắt bảo mật Windows.

## Nhờ AI cho đúng

```text
Đây là JSON skeleton 3 điểm chép từ tab Raw của CVAT: <dán JSON>.
Viết make_label.py đọc config (cột: <dán tên cột>) và sinh JSON cùng cấu trúc cho 50 điểm.
Giữ nguyên mọi khoá của mẫu, trừ "id": bỏ mọi khoá "id"; trong svg, mỗi nút ghi data-label-name="<tên điểm>", không ghi data-label-id. Mỗi điểm một checkbox low_conf, màu theo cột bên.
Cạnh chỉ nối điểm liền nhau trên cùng đường cong. In ra số điểm và số cạnh.
```

```text
Đây là file CVAT for images 1.1 mẫu, toạ độ đã thay bằng số giả: <dán XML>.
Viết hàm ghi file cùng cấu trúc cho nhiều ảnh, mỗi point có occluded="0", outside="0", low_conf.
id và name lấy từ danh sách frame của task, không tự đánh số. Báo lỗi nếu ảnh thiếu điểm.
```

```text
Viết hàm numpy kiểm đường gấp khúc (mảng N x 2): hai đoạn liền nhau có tích vô hướng dương,
và đường không tự cắt. Trả về chỉ số điểm lỗi. Kèm 3 test: đường đúng,
hai điểm liền nhau đổi chỗ, đường tự cắt hình số 8.
```

```text
Write a cvat-sdk auto-annotation function using only https://docs.cvat.ai/docs/api_sdk/sdk/auto-annotation/.
Spec: skeleton "face50", 50 keypoints whose names are read from our config file (do not list them here), each with a checkbox attribute low_conf.
detect() runs no model: it reads mp50.json (points) and flags.json (low_conf) and finds each image by frame name, not index.
List every SDK function you use and its doc section.
```

Ba quy tắc:

1. Không dán ảnh, gt50, file xuất thật, dữ liệu khách hàng, mật khẩu hay token. Thay toạ độ bằng số giả. Ảnh WFLW chỉ ở nội bộ (CC BY-NC-ND).
2. Chạy code AI trên 5 mẫu trước, ví dụ khứ hồi 5 mặt F, rồi mở CVAT xem. Sai một mẫu là chưa dùng.
3. Loại code gọi hàm không có trong docs CVAT của phiên bản đang cài, hoặc dùng mp.solutions. MediaPipe chỉ dùng vision.FaceLandmarker với face\_landmarker.task.

## Lỗi hay gặp

1. Nhập nháp lần hai: CVAT xoá nhãn người đã làm. Chỉ nhập một lần, vào task dựng trên CVAT của bạn, trước khi sao lưu; trên máy từng người không ai nhập nháp.
2. Sai tên ảnh trong XML: CVAT lặng lẽ dùng id, nhãn rơi sang ảnh khác. Lấy id và tên từ cvat-sdk.
3. Sai sắp xếp hoặc segment size: task chứa sai ảnh hay sai số ảnh, thí nghiệm hỏng. Kiểm bằng `check_backup.py` trước khi commit file zip.
4. Sửa skeleton khi đã có task: gần như không được. Kiểm label và cờ trước 7/10.
5. Ghi đè raw/ khi xuất lần 2: mất số liệu chất lượng. Xuất lần 2 vào final/.

## Khi bị kẹt

- Cài CVAT, Docker, WSL trên máy bạn: tra mục cài CVAT ở tab chung, rồi hỏi nhóm chat (P5 gom lỗi). Mang bản CVAT (`/api/server/about`), lệnh đã chạy, thông báo lỗi nguyên văn; không chụp ảnh có mặt người.
- Tên điểm, thứ tự, bên, cặp được trùng, khuôn: P3. Mang dòng config liên quan.
- mp50.json (50 điểm): P3. flags.json (cờ), ảnh không thấy mặt: P2. Mang tên ảnh và trường bị thiếu.
- Ảnh cắt, tên file, manifest.csv: P1. Mang tên file và dòng manifest.
- Lịch, quy tắc gán, điểm dừng: P5.

## Phần mới: push và collect (9–18/10)

Hai bước chạm CVAT là của bạn. Ở công ty thật (một CVAT chung), người vận hành giữ quyền tạo task và xuất; ở M28 ai cũng có CVAT riêng. Công cụ chỉ đọc `CVAT_URL` và `CVAT_ACCESS_TOKEN` (thêm `CVAT_ORG` nếu project nằm trong organization); ở công ty đổi các biến này, sửa số bản CVAT trong `config/pipeline.json` và cài `cvat-sdk` cùng bản với server là chạy được với CVAT đó, không sửa code. Nguyên tắc: `push` chỉ tạo task MỚI tên `demo-…` trong project m28 rồi nhập đúng một lần; `collect` chỉ xuất, không bao giờ nhập. Vì vậy nhãn người đã gán không bao giờ bị ghi đè (nhập vào task đã có nhãn mặc định sẽ thay nhãn cũ). Trong công ty gán nhãn, đây là phần người quản lý dự án chạy để mở một lô việc mới và thu kết quả; với ảnh khách hàng, cả bốn lệnh chạy trên máy của người này.

**Token.** Cách tạo token và đặt biến ở tab chung (mục cài CVAT); cả 5 người làm trên CVAT của mình. `CVAT_URL` = `http://localhost:8080` (ghi rõ `http://`; thiếu thì cvat-sdk tự hiểu là https); ở công ty là địa chỉ server chung. Code chỉ in "token: có/thiếu", không in giá trị. Không dùng mật khẩu trong code. Ngày 24/10 mỗi người thu hồi token của mình.

```python
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
```

- XML chỉ có skeleton cho mặt Nhận, luôn đủ 50 điểm; mặt Gán tay không có skeleton; mặt Bỏ không có trong task.
- `push` tải lên đúng ảnh mà XML dùng: `--box wflw` → ảnh cắt trong `runs/<run>/crop/`; `--box auto` → ảnh gốc, đọc từ `--images` (thư mục WFLW\_images trên máy bạn). Tên ảnh trong XML = tên file tải lên (không có thư mục) và không được trùng nhau; `job_file_mapping` cũng dùng tên này.
- Tên định dạng: nhập là `"CVAT 1.1"`, xuất là `"CVAT for images 1.1"`. Không dùng tham số `annotation_path` của `create_from_data`.
- Ở công ty (một CVAT chung), giao job vẫn làm trên giao diện (khoảng 2 phút). Ở M28 task nằm trên CVAT của người push, nên không giao job.
- `job_file_mapping` mà lỗi thì bỏ, dùng một job chung và ghi `manual_list.txt`.
- `push` lỗi giữa chừng: xoá task lỗi trong CVAT (kiểm đúng tên), xoá `push.json`, chạy lại.

**Nhờ AI cho đúng.**

```text
Dùng cvat-sdk 2.77 (Python). Viết hàm tạo task trong project bằng client.tasks.create_from_data
với spec={"name", "project_id"} (không có labels), resource_type=ResourceType.LOCAL,
data_params có job_file_mapping; rồi task.import_annotations("CVAT 1.1", xml);
rồi task.export_dataset("CVAT for images 1.1", path, include_images=False).
Token đọc từ os.environ["CVAT_ACCESS_TOKEN"], không in ra. Giải thích lỗi thường gặp.
```

Ba quy tắc: (1) không dán token, địa chỉ nội bộ hay file XML có toạ độ thật vào chat AI; (2) chỉ thử trên task `demo-…`, không bao giờ trên task `m28-`; (3) chạy lần hai phải bị từ chối, đó là dấu hiệu push an toàn.
