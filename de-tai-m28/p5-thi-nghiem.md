# P5 – Thí nghiệm và báo cáo

Bạn giữ luật chơi của thí nghiệm: guideline, bảng ca khó, công cụ bấm giờ facetimer.py và họp điểm dừng 12/10. Tuần 3 bạn phân tích thời gian, chất lượng, rồi viết báo cáo và demo. Với dự án thật, kết quả của bạn là quy tắc dùng nhãn nháp và số giờ tiết kiệm trên 1.000 mặt.

## Bạn nhận gì và giao gì

| Ngày | Nhận từ ai, cái gì | Giao cho ai, cái gì |
| --- | --- | --- |
| 5/10 | Mentor: trả lời 8 câu. P4 (đầu buổi): bản CVAT nhóm dùng (v2.77.0). P4 (cuối buổi): cách xem tên điểm khi di chuột, lệnh cài CVAT đã chạy thật (tab chung) | P3: định nghĩa 50 điểm. Cả nhóm: quy định dữ liệu, câu trả lời của mentor về CVAT tự cài. Mentor: 3 câu thêm về pipeline |
| 6/10 | P1: manifest.csv | P1: kết quả soát chia tập |
| 7/10 | P3: file cấu hình 50 điểm | Cả nhóm: guideline v1, facetimer.py |
| 8–10/10 | `backups/P5/`: m28-gold-x (G5), m28-gold-y (G1), m28-pilot-assisted (Pa, có nháp, 9/10), m28-pilot-manual (Pb, 10/10). P4 (8/10, trước phút 60): `export.py`. P1: timing\_P1.csv | Cả nhóm: tỉ lệ thử nhanh P1, P5 |
| 11/10 | Mentor: trả lời 3 câu pipeline, góp ý hướng làm | P2: `guideline_triage.md` (mã lý do cho nút bấm) |
| 12/10 | P3: sai số, % T-dev trong sai số, điểm lệch định nghĩa. P2: ngưỡng cờ. P4: kết quả kiểm 5 máy (bản 2.77.0, `m28-check`, `CHECK.txt`) | Cả nhóm: biên bản điểm dừng (có quyết định cờ cho nháp X, D), guideline v2, bảng ca khó v2 |
| 13–15/10 | `backups/P5/`: m28-practice (D\_17–D\_20, 13/10), m28-manual (X5, 14/10), m28-assisted (X1, 15/10), khôi phục đầu mỗi buổi | Repo: `raw/<task>_P5_<ngày>.xml` (tự xuất cuối khối). Cả nhóm (15/10): kịch bản demo 18/10 |
| 16/10 | P4 (lệnh `collect --skip-export` trên `raw/` cả nhóm đã commit): CSV QC, bảng ảnh chồng (P2 quét, gửi tên mặt đáng ngờ qua P4), `outputs/review_1610/P3.csv` (mặt P3 gán, bạn xem). Repo (14–15/10): file `.txt` kèm mỗi file `raw/` (giờ tạo task, `export.py` tự ghi). P1: `runs/R1610/` (repo nội bộ) | `outputs/review_1610/P3.csv`: mã lỗi; lỗi RULE vào bảng ca khó |
| 17/10 | 4 bạn: timing\_Pk.csv. P2 (16/10): mã lỗi trên mặt của bạn trong `outputs/review_1610/P5.csv`. P3: `outputs/triage_R.csv`. P4: `push.json` | Cả nhóm: timing\_log.csv, timing\_m24.csv. P3, P4 (đầu buổi): `triage_P5.csv`. P2: lỗi trang rà soát |
| 18/10 | P4: `outputs/collect_demo-R1610.md` | Mentor: demo, nháp `report_pipeline.md` |
| 19–21/10 | P3: NME từng mặt X. P4: công sửa, bỏ sót. P2: kết quả theo loại mặt | Cả nhóm: bảng 5 tiêu chí × 3 mức |
| 22–24/10 | P1: công cụ + README | Mentor: báo cáo, slide, demo. P4 (22/10): ảnh demo (chỉ để trên máy P4) |

## Lịch của bạn

### Tuần 1

- [ ] **T2 5/10** Hỏi mentor 8 câu trong kế hoạch và 3 câu thêm về pipeline; viết guideline v1 — chạy ở Máy mình — ra mentor\_answers.md, guideline.md nháp — xong khi đã gửi 11 câu cho mentor (câu về CVAT nay là: nhóm chạy CVAT tự cài trên laptop từng người với ảnh WFLW có được không, và dự phòng tài khoản CVAT Online cá nhân; gửi kèm ghi chú ngắn của trưởng nhóm). Có trả lời thì báo P3, P4 ngay; P3 không chờ, vẫn chốt config tối nay. Lúc báo cuối buổi, đăng thêm (chỉ chữ): bản Windows (`winver`), RAM, ổ C còn trống, dòng Virtualization trong Task Manager.
- [ ] **T3 6/10** Soát manifest.csv (không trùng, đủ 616 ảnh, khối X cân bằng); gieo bảng ca khó — chạy ở Máy mình — ra hard\_cases.csv — xong khi P1 xác nhận, mỗi tình huống có người quyết. Phần sau (khoảng 30 phút): cài CVAT phần A (tab chung; khởi động lại máy cuối buổi; đầu buổi 7/10 mở Ubuntu tạo user Linux rồi mới kiểm) — xong khi `wsl -l -v` thấy Ubuntu ở VERSION 2. Từ tối nay tới 9/10, gom lỗi cài của cả nhóm trong nhóm chat và dời việc khi ai sắp quá 120 phút.
- [ ] **T4 7/10** Viết facetimer.py (khối code dưới mục "facetimer.py", phần Làm thế nào); hoàn tất guideline v1 — chạy ở Máy mình — ra facetimer.py, guideline.md v1 — xong khi 3 mặt thử ra CSV 12 cột, cả nhóm nhận guideline.
- [ ] **T4 7/10** (bắt đầu sớm, làm nốt ở giờ thứ hai) Cài CVAT phần B theo tab chung: đầu buổi chạy tới `docker compose up -d` để ảnh Docker tải chạy nền trong lúc viết facetimer.py và hoàn tất guideline, rồi làm nốt phần B ở giờ thứ hai — chạy ở Máy mình — ra CVAT v2.77.0 ở `http://localhost:8080`, token trong biến môi trường — xong khi `python -m cvat_cli task ls` chạy không lỗi. Kẹt quá 15 phút thì dừng, báo P4.
- [ ] **T5 8/10** CVAT đã cài xong tối 7/10. Đầu buổi khôi phục `backups\P5\m28-gold-x.zip` (G5) và `backups\P5\m28-gold-y.zip` (G1); gán tay G5, G1 — chạy ở CVAT trên máy mình — ra 8 mặt, `raw/m28-gold-x_P5_0810.xml`, `raw/m28-gold-y_P5_0810.xml` — xong khi 8 mặt qua checklist cuối mặt, đã tự xuất bằng `export.py` (P4 báo có trước phút 60; chưa có thì xuất bằng giao diện theo tab chung, mục "Dùng hằng ngày") và commit. CVAT chưa chạy được (cài tối 7/10 lỗi): báo P4, gán G ở đầu buổi 9/10 trước buổi thử.
- [ ] **T6 9/10** Đầu buổi khôi phục `backups\P5\m28-pilot-assisted.zip` (Pa, có nháp); thử nhanh sửa nhãn nháp Pa, bấm giờ — chạy ở CVAT trên máy mình + Máy mình (facetimer.py) — ra 8 dòng timing\_P5.csv, `raw/m28-pilot-assisted_P5_0910.xml` — xong khi đã tự xuất và commit. Khôi phục lỗi: đổi thứ tự (Pb gán tay tối nay, Pa có nháp 10/10) và báo P4. Trước 10/10 khôi phục thử `backups\all\m28-check.zip` (tab chung, bước 12).
- [ ] **T7 10/10** Đầu buổi khôi phục `backups\P5\m28-pilot-manual.zip` (Pb, không nháp); thử nhanh gán tay Pb, tự xuất `raw/m28-pilot-manual_P5_1010.xml` và commit; giờ thứ hai, khi P1 đã gửi timing (khoảng phút 60), tính tỉ lệ thử nhanh P1, P5 — chạy ở CVAT trên máy mình + Máy mình — ra 2 tỉ lệ, phút/mặt — xong khi đã gửi nhóm.
- [ ] **CN 11/10** (khung chung 2 tiếng; bạn hẹn giờ với cả nhóm và mentor trước) Gặp mentor 20–30 phút (nếu mentor rảnh; không thì buổi ngày thường gần nhất qua chia sẻ màn hình): trình kế hoạch có pipeline và trang rà soát, P1 chiếu `prepare` trên 5 mặt F; ghi trả lời 3 câu pipeline. Rồi viết `guideline_triage.md`: khi nào Nhận / Gán tay / Bỏ ảnh, mã lý do, 6 ví dụ tả bằng lời (không dán ảnh) — chạy ở họp + Máy mình — ra `mentor_answers.md` cập nhật, `guideline_triage.md` — xong khi P2 nhận mã lý do cho nút bấm.

### Tuần 2

- [ ] **T2 12/10** Chủ trì 20 phút họp điểm dừng; chốt guideline v2, bảng ca khó v2 — chạy ở họp nhóm + Máy mình — ra checkpoint\_1210.md, v2 đã commit — xong khi mọi dòng ca khó "chốt".
- [ ] **T2 12/10** Thêm vào `checkpoint_1210.md`: khối luôn 10 mặt (bỏ câu kích thước khối cũ); cờ cho nháp X, D dùng `t_flip` hay cờ gộp `t` (chốt trước khi P4 dựng backup tuần 2, không đổi sau); kết quả kiểm 5 máy (bản 2.77.0, `m28-check`, `CHECK.txt`); trạng thái pipeline: prepare, trang rà soát, push.py đạt/không (không chặn thí nghiệm) — chạy ở họp + Máy mình — ra `checkpoint_1210.md` — xong khi `CHECK.txt` của 10 file tuần 2 ghi cùng mã băm `flags.json` ở commit có tag.
- [ ] **T3 13/10** Đầu buổi khôi phục `backups\P5\m28-practice.zip` (D\_17–D\_20); làm quen 4 mặt D (3 nháp, 1 tay), tự xuất `raw/m28-practice_P5_1310.xml` và commit; chép khối code dưới mục "Thời gian" (phần Làm thế nào) vào analyze\_time.py — chạy ở CVAT trên máy mình + Máy mình — ra 4 dòng CSV, analyze\_time.py — xong khi dữ liệu giả cho đúng tỉ lệ.
- [ ] **T4 14/10** Đăng câu chung và nhắc: "Đầu buổi khôi phục task của hôm nay, rồi mới bật facetimer". Khôi phục `backups\P5\m28-manual.zip` (X5, không nháp); gán tay X5 — chạy ở CVAT trên máy mình + Máy mình (facetimer.py) — ra 10 dòng "manual", `raw/m28-manual_P5_1410.xml` — xong khi đã tự xuất và commit.
- [ ] **T5 15/10** Đăng câu chung; khôi phục `backups\P5\m28-assisted.zip` (X1, có nháp; không khôi phục trước hôm nay); sửa nhãn nháp X1 — chạy ở CVAT trên máy mình + Máy mình (facetimer.py) — ra 10 dòng "assisted", `raw/m28-assisted_P5_1510.xml` — xong khi đã tự xuất và commit.
- [ ] **T5 15/10** (giờ thứ hai, chỉ viết chữ) Kịch bản demo 18/10 (30 phút, ai nói gì, chạy lệnh nào) và khung `report_pipeline.md` (các mục, bảng số còn trống) — chạy ở Máy mình — ra 2 file nháp — xong khi P1, P2, P3, P4 đã đọc phần của mình.
- [ ] **T6 16/10** Bù nếu lỡ (tự xuất `raw/<task>_P5_1610.xml`, commit trước khi mở bảng ảnh chồng); xem chéo mặt của P3 trong `outputs/review_1610/P3.csv` (mặt bị đánh dấu + 1 mặt ngẫu nhiên mỗi task) trên bảng ảnh chồng và ảnh cắt — chạy ở Máy mình — ra mã lỗi (SWAP, MIRROR, COLLAPSE, MISPLACED, OCC\_FLAG, RULE) trong file đó — xong khi mọi mặt có mã; lỗi RULE đã vào bảng ca khó. Rồi kiểm sạch thí nghiệm (khoảng 10 phút): đọc 10 file `raw/m28-manual_*.txt`, `raw/m28-assisted_*.txt` (`export.py` ghi kèm, giờ Việt Nam); giờ tạo mỗi task phải rơi đúng ngày gán của task đó; ghi vào checkpoint, máy nào lệch thì báo mentor và phân tích riêng.
- [ ] **T6 16/10** (giờ thứ hai) Cài `requirements-ui.txt` theo tab chung; mở thử trang rà soát với `runs/F5/` (5 mặt F), không mở R1610; mở thẳng bằng `python tool\review_app.py runs\F5 P5` (bản của P2, không chờ P1 nối lệnh tối nay), không commit file mới trong `runs/F5/` — chạy ở Máy mình — xong khi trang mở ở 127.0.0.1.
- [ ] **T7 17/10** (đầu buổi, phút 5–25, trước việc khác) `git pull`, rồi rà 40 mặt R1610 (bạn là người rà duy nhất) theo `guideline_triage.md`: `python tool\m28.py review --run R1610 --reviewer P5`; bấm Xong; commit `runs/R1610/review/triage_P5.csv` và `done.txt` (chỉ tên file, quyết định, lý do, số giây); báo P3, P4. Trang lỗi thì rà bằng `--review excel` — chạy ở Máy mình — ra `triage_P5.csv` — xong khi đủ 40 dòng và P3, P4 đã nhận.
- [ ] **T7 17/10** Sửa mặt của mình bị ghi lỗi (`outputs/review_1610/P5.csv`) trên CVAT của bạn, tự xuất lần 2 vào `final/` và commit; gộp CSV 5 người — chạy ở CVAT + Máy mình — ra timing\_log.csv, timing\_m24.csv — xong khi đủ 100 dòng X, khoảng 80 dòng tính giờ (mỗi người, mỗi cách 7–8 dòng).
- [ ] **CN 18/10** (khung chung 2 tiếng) Chủ trì demo cho mentor (30 phút: một lệnh → trang rà soát → task CVAT → chạy lại bị từ chối → số của P3); viết nháp `report_pipeline.md` (số rà soát, push, thời gian) — chạy ở họp + Máy mình — ra nháp, `checkpoint_1810.md` ghi góp ý — xong khi mentor đã xem. Phần collect bổ sung ngày 19/10.

### Tuần 3

- [ ] **T2 19/10** Thời gian: r\_i, trung bình nhân, KTC 90% — chạy ở Máy mình — ra time\_result.txt — xong khi có kết luận 3 mức.
- [ ] **T2 19/10** Chốt `pipeline_metrics.csv` từ `push.json`, `log.txt`, `triage_P5.csv`, `outputs/triage_R.csv`, `outputs/collect_demo-R1610.md`; thêm phần collect vào `report_pipeline.md` — chạy ở Máy mình — ra bản chốt — xong khi số khớp `report_pipeline.md`.
- [ ] **T3 20/10** Chất lượng: hiệu NME ghép cặp, toàn mặt và vùng mắt (khối code dưới mục "Chất lượng") — chạy ở Máy mình — ra nme\_result.txt — xong khi có 2 kết luận 3 mức.
- [ ] **T4 21/10** Gom kết quả P2, P3, P4; viết quy tắc dùng nháp — chạy ở Máy mình — ra bảng 5 tiêu chí × 3 mức (thêm dòng "Pipeline và rà soát"), giờ tiết kiệm/1.000 mặt — xong khi cả nhóm đã đọc.
- [ ] **T5 22/10** Viết báo cáo nháp; chọn ảnh demo và chép sang máy P4 bằng USB hoặc thư mục nội bộ (không qua chat, email), rồi xoá bản trên máy mình; cả bốn lệnh chạy trên máy P4 và chỉ máy đó giữ ảnh (ảnh nội bộ có sự đồng ý; ảnh WFLW chỉ khi mentor cho phép) — chạy ở Máy mình — ra report.md, thư mục ảnh demo — xong khi đã gửi mentor và P4 đã nhận ảnh.
- [ ] **T6 23/10** Slide; tập dượt demo offline trên CPU ở máy P4 (họp, ảnh demo chỉ ở máy đó) — chạy ở Máy mình (slide) và máy P4 — ra slide + demo — xong khi tập trọn một lần đúng giờ.
- [ ] **T7 24/10** Sửa theo góp ý, nộp — chạy ở Máy mình — ra bản nộp — xong khi đã nộp và đã báo cả nhóm "đã nộp" (mốc để mọi người dọn máy); rồi dọn máy theo tab chung (mục cài CVAT, đoạn "Dọn máy 24/10": thu hồi token, xoá `CVAT_URL` và `CVAT_ACCESS_TOKEN`, `docker compose down -v` trong `~/cvat`; khoảng 15 phút) rồi báo P4; giờ còn lại để dự phòng.

## Làm thế nào

**Guideline, bảng ca khó.** v1 gồm 9 quy tắc của kế hoạch, checklist cuối mặt và câu chung: "Làm theo nhịp bình thường; mặt xong khi mọi điểm đúng quy tắc." Bảng ca khó có cột: id, ngày, face\_id, điểm, tình huống, quyết định, nguồn, người quyết, trạng thái, phiên bản. Ngày 10/10 nhận offset\_G.csv của P3: mỗi điểm lệch định nghĩa ghi một dòng (nguồn: G) để báo khách hàng. Sau 12/10 không sửa; ca mới trả lời theo v2.

**Họp 12/10.** Bốn câu hỏi. (1) Năm máy cùng CVAT 2.77.0 (máy dự phòng CVAT Online đã duyệt: tính "4 máy 2.77.0 + 1 CVAT Online"); `m28-check` hiện đúng tên, thứ tự, thấy cờ trên cả 5 máy; `CHECK.txt` sạch; khứ hồi buổi thử của P1, P5 đạt? Không: sửa file, rồi phương án B (trên CVAT của P4, trước khi sao lưu); một máy hỏng thì cài lại đúng bản. (2) ≥ 60% điểm T-dev trong sai số? Không: đổi model theo quy tắc, hoặc chỉ nháp mắt, mũi, môi. (3) Tỉ lệ thử nhanh P1, P5: chỉ chuyển M26/M31 khi cả hai > 1,0. (4) Cờ cho nháp X, D: dùng t\_flip (giống công cụ giao đi, đề xuất) hay cờ gộp t; chốt trước khi P4 dựng backup tuần 2. Khối luôn 10 mặt vì buổi có 120 phút. Tỉ lệ thử nhanh mỗi người = tổng giây seq 3–8 có nháp ÷ tổng giây seq 3–8 gán tay.

**facetimer.py.** Mở job CVAT ở ảnh đầu, chạy lệnh. Enter khi mặt qua checklist; gõ p khi bị gián đoạn. Buổi bù: nhập seq tiếp theo, mặt đầu tự thành khởi động.

```python
import csv, sys, time, datetime, os
# Ví dụ 14/10: python facetimer.py P5 manual m28-manual <số job trên CVAT của bạn> X5 10
person, cond, task, job, block, n = sys.argv[1:7]
out = f"timing_{person}.csv"
new = not os.path.exists(out)
seq = int(input("Bat dau tu seq (Enter = 1): ") or 1)
first = True
with open(out, "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    if new:
        w.writerow(["date", "person", "condition", "task", "job", "block", "seq",
                    "face_id", "seconds", "warmup", "interrupted", "note"])
    while seq <= int(n):
        face, t0, paused, intr = f"{block}_{seq:02d}", time.perf_counter(), 0.0, 0
        k = input(f"{face}: Enter = xong (go chu = ghi chu), p = dung, q = thoat: ")
        while k.strip() == "p":
            p0 = time.perf_counter(); input("Dang dung. Enter de lam tiep...")
            paused += time.perf_counter() - p0; intr = 1
            k = input(f"{face}: Enter = xong, p = dung, q = thoat: ")
        if k.strip() == "q":
            break
        w.writerow([datetime.date.today().isoformat(), person, cond, task, job, block, seq, face,
                    round(time.perf_counter() - t0 - paused, 1), int(seq <= 2 or first), intr, k.strip()])
        f.flush(); seq += 1; first = False
```

**Thời gian.** r\_i = số giây trung bình mỗi mặt tính giờ khi có nháp ÷ số giây trung bình mỗi mặt tính giờ khi gán tay (thường 8 mặt mỗi cách; buổi bù có thể còn 7, nên dùng trung bình chứ không dùng tổng). Đạt khi trung bình nhân 5 tỉ lệ ≤ 0,80 và ≥ 4/5 người có r\_i < 1. Quy tắc "không đạt" và "chưa kết luận" chốt ở họp 12/10, ghi vào checkpoint\_1210.md. Đề xuất: không đạt khi cận dưới KTC 90% > 0,80; còn lại là chưa kết luận. KTC 90% (khoảng tin cậy) lấy bằng bootstrap: bốc lại mặt trong khối 2.000 lần. Khối code dưới đây cũng ra bảng kiểu M24 và giờ tiết kiệm/1.000 mặt, tính chung cho X và riêng cho hai nhóm mặt (nghiêng hoặc bị che / còn lại).

```python
import glob, numpy as np, pandas as pd
d = pd.concat(pd.read_csv(f) for f in glob.glob("timing_P*.csv")); d.to_csv("timing_log.csv", index=False)
t = d[d.warmup == 0]
m24 = t.groupby(["date", "person", "condition"]).agg(so_anh=("face_id", "count"), so_phut=("seconds", "sum")).reset_index()
m24["so_phut"] = (m24.so_phut / 60).round(1); m24.to_csv("timing_m24.csv", index=False)
x = t[t.task.isin(["m28-manual", "m28-assisted"])].reset_index(drop=True)
def geo(w):                                   # w = số lần mỗi dòng được bốc lại
    s = (x.seconds * w).groupby([x.person, x.condition]).sum().unstack()
    n = pd.Series(w, index=x.index).groupby([x.person, x.condition]).sum().unstack()
    m = s / n                                 # giây trung bình mỗi mặt (7 hay 8 mặt đều công bằng)
    r = m["assisted"] / m["manual"]
    return np.exp(np.log(r).mean()), r
g, r = geo(np.ones(len(x)))
rng, boot = np.random.default_rng(28), []
for _ in range(2000):                         # bốc lại mặt trong từng khối, chung cho hai cách
    w = np.zeros(len(x))
    for b, rows in x.groupby("block").groups.items():
        seqs = sorted(x.seq.loc[rows].unique()); pick = list(rng.choice(seqs, len(seqs)))
        w[rows] = [pick.count(s) for s in x.seq.loc[rows]]
    boot.append(geo(w)[0])
sv = x.groupby("condition").seconds.mean()
print(r.round(2), f"\nTB nhan {g:.2f}, KTC 90% {np.percentile(boot, [5, 95]).round(2)}")
print("Dat" if g <= 0.80 and (r < 1).sum() >= 4 else "Chua dat: doc KTC")
print("Gio tiet kiem / 1.000 mat (tron X):", round((sv["manual"] - sv["assisted"]) * 1000 / 3600, 1))
mf = pd.read_csv("manifest.csv"); mf.index = mf.file.str.replace(".png", "", regex=False)
kho = x.face_id.map(mf.pose | mf.occlusion) == 1      # mặt nghiêng hoặc bị che
for ten, nhom in [("nghieng/che", x[kho]), ("con lai", x[~kho])]:
    sv = nhom.groupby("condition").seconds.mean()
    print(ten, sv.round(1).to_dict(), "gio tiet kiem / 1.000 mat:", round((sv["manual"] - sv["assisted"]) * 1000 / 3600, 1))
```

**Chất lượng.** NME là độ lệch trung bình so với đáp án, tính theo % IOD (khoảng cách hai khoé mắt ngoài). Module của P3 tính NME trên file xuất raw 14–15/10. Hẹn P3 trước 17/10: nme\_per\_face.csv có cột face\_id, condition, nme, nme\_eye. Hiệu = có nháp − gán tay, theo từng mặt. Từ 2.000 lần bốc lại, lấy cận trên (phân vị 95) và cận dưới (phân vị 5) của hiệu. Cận trên ≤ +0,5% IOD: đạt. Cận dưới > +0,5% IOD: không đạt. Còn lại: chưa kết luận.

```python
import numpy as np, pandas as pd
n = pd.read_csv("nme_per_face.csv")   # từ module của P3, đơn vị % IOD
rng = np.random.default_rng(28)
for col in ["nme", "nme_eye"]:
    p = n.pivot(index="face_id", columns="condition", values=col).dropna()
    diff = (p["assisted"] - p["manual"]).to_numpy()
    boot = [rng.choice(diff, len(diff)).mean() for _ in range(2000)]
    lo, hi = np.percentile(boot, [5, 95])
    kq = "dat" if hi <= 0.5 else "khong dat" if lo > 0.5 else "chua ket luan"
    print(col, len(diff), f"TB {diff.mean():+.2f}, [{lo:+.2f}, {hi:+.2f}] -> {kq}")
```

**Quy tắc dùng thật.** Tách hai nhóm: nghiêng hoặc bị che / còn lại. Ảnh khách hàng không có cờ WFLW, nên ghi rõ cách nhận nhóm: người gán nhìn qua thấy mặt quay rõ sang một bên hoặc bị che một phần, hoặc mặt có nhiều điểm cờ low\_conf. Nhóm nào chậm hơn hoặc kém hơn thì gán tay. Vùng mắt không đạt thì ghi rõ cho dự án giám sát tài xế. Báo cáo ghi giấy phép: MediaPipe Apache-2.0; PIPNet và ảnh WFLW chỉ nội bộ.

## Chạy ở đâu

- CVAT trên máy mình: gán, sửa; mỗi người tự xuất bằng `export.py`. Xem chéo làm trên bảng ảnh chồng.
- Máy mình: facetimer.py, phân tích, demo offline. File CSV nhỏ, không cần GPU.
- Colab: chỉ khi máy lỗi cài thư viện, ví dụ Windows chặn DLL. Không tắt bảo mật; chỉ tải CSV số, không tải ảnh.
- Kaggle: bạn không cần.

## Nhờ AI cho đúng

```text
Đây là script Python 3.14 trên Windows, đo giây từng mặt khi gán nhãn (Enter = xong, p = tạm dừng). Tìm lỗi logic: thời gian dừng có bị trừ đúng không, cột warmup có đúng khi bắt đầu từ seq giữa khối không. Không thêm thư viện. <dán facetimer.py>
```

```text
Write Python that makes fake timing_P1.csv … timing_P5.csv for testing. Blocks X1–X5, 10 faces each. Columns: date, person, condition, task, job, block, seq, face_id, seconds, warmup, interrupted, note. Pk does "manual" (task m28-manual) on Xk and "assisted" (task m28-assisted) on X(k+1); P5 does "assisted" on X1. warmup = 1 for seq 1–2. Assisted is 25% faster. Fixed seed.
```

```text
Kiểm tra đoạn code bootstrap sau. Mô tả: r_i = giây trung bình mỗi mặt có nhãn nháp / giây trung bình mỗi mặt gán tay của từng người; chỉ số chính là trung bình nhân 5 tỉ lệ; bốc lại mặt trong từng khối, dùng chung cho hai cách gán. Code có làm khác mô tả không? Chỉ dùng numpy, pandas. <dán code>
```

```text
Giải thích trong 5 câu ngắn, cho người gán nhãn không học thống kê: hiệu NME ghép cặp (có nháp − gán tay) = <TB>% IOD, cận trên một phía 95% = <hi>%, ngưỡng = +0,5%. Không thêm con số tôi không đưa.
```

Ba quy tắc:

1. Không dán ảnh mặt, ảnh chồng, đáp án, tài liệu khách hàng vào chat AI, kể cả Gemini trong Colab.
2. Chạy code AI trên 5 mẫu giả bạn tính tay được. Sai một mẫu là không dùng.
3. Bỏ code dùng mp.solutions hoặc hàm không có trong tài liệu chính thức.

## Lỗi hay gặp

- Tính chất lượng trên file xuất 17/10. Phải dùng file raw 14–15/10.
- Tính cả mặt khởi động. Luôn lọc warmup = 0.
- Lấy trung bình cộng các r\_i. Chỉ số chính là trung bình nhân.
- Đảo dấu hiệu NME. Luôn lấy có nháp − gán tay.
- Xem tổng giờ trước 17/10. Trước đó chỉ đếm số dòng CSV.

## Khi bị kẹt

Tên điểm, sai số, NME: hỏi P3. Cài CVAT, khôi phục backup, `export.py`: hỏi P4. manifest, khối X: hỏi P1. Cờ, ảnh chồng: hỏi P2. Giấy phép, dữ liệu: hỏi mentor. Mang theo face\_id, file CSV, lệnh đã chạy, toàn bộ lỗi. Ảnh CVAT chỉ gửi trong nhóm.

## Phần mới: quy tắc rà soát, người rà, số liệu pipeline, demo (11–19/10)

Bạn giữ phần "vì sao" của pipeline: quy tắc rà để việc rà nhất quán, bạn là người rà duy nhất của tập R, số liệu chứng minh pipeline có ích, và buổi demo cho mentor. Trong công ty gán nhãn, `guideline_triage.md` là tờ hướng dẫn cho người lọc lô ảnh mới.

**guideline\_triage.md (CN 11/10).** Mỗi quyết định một đoạn ngắn:

- Nhận: nháp đúng dáng mặt; điểm sai chỉ cần kéo nhẹ trong CVAT.
- Gán tay: nháp lật gương (trái thành phải), dồn cục, lệch cả một vùng, hoặc mặt quay quá 80° hay bị che quá nửa. Ảnh có nhiều mặt cần gán cũng chọn Gán tay (pipeline chỉ làm nháp cho mặt lớn nhất). Mã lý do: `LAT_GUONG`, `DON_CUC`, `LECH_VUNG`, `QUAY_CHE`, `NHIEU_MAT`.
- Bỏ ảnh: không có mặt, sai mặt (mặt khác mặt cần gán), quá mờ hoặc quá nhỏ. Mã lý do: `KHONG_MAT`, `SAI_MAT`, `MO_NHO`.
- Mỗi mặt rà tối đa 30 giây; phân vân giữa Nhận và Gán tay thì chọn Nhận.

**Số liệu (18–19/10).**

| Số | Lấy từ | Ý nghĩa |
| --- | --- | --- |
| Bước tay mỗi lô | Đếm theo README | Trước khoảng 8 bước của 4 người, sau 3 việc của 2 người |
| Phút tới task | `log.txt`, `push.json` | Thời gian máy từ thư mục ảnh đến task sẵn sàng |
| Giây rà/mặt | `triage_P5.csv` | Trung vị, đổi ra phút cho 100 mặt |
| Bắt nháp hỏng | `outputs/triage_R.csv` của P3 | Số mặt hỏng bị đưa sang Gán tay/Bỏ, so với `--review auto` |
| Nháp hỏng lọt vào CVAT | `outputs/triage_R.csv` | Nhập tất cả so với chỉ nhập mặt Nhận |
| Sau khi gán | `outputs/collect_demo-R1610.md` | Lỗi QC theo loại, thời gian collect |

Giờ tiết kiệm cho đội gán thật = giờ tiết kiệm khi sửa nháp (từ thí nghiệm) + (phút dựng task tiết kiệm mỗi lô × số lô) ÷ 60. Ghi rõ số lô giả định, ví dụ 10 lô × 100 mặt.

**Demo CN 18/10.** Kịch bản 30 phút: (1) 3 phút: mentor góp ý gì, nhóm đổi gì; (2) 10 phút: P4 chạy `all` trên 10 ảnh R mới, P2 giải thích trang rà soát; (3) 7 phút: mở task CVAT, chạy lại để thấy bị từ chối; P1 chiếu cùng lệnh đã chạy trên CVAT của P1 và nói rõ: chỉ đổi `CVAT_URL` và token là chạy trên server khác, ở công ty là server chung; (4) 5 phút: số của P3 và bảng trên; (5) 5 phút: hỏi góp ý. Gặp online thì chia sẻ màn hình; tắt ghi hình và trợ lý AI ghi chú của phần mềm họp; không gửi file có ảnh mặt.

**Nhờ AI cho đúng.**

```text
Có triage.csv (file, decision, reason, seconds). Viết hàm pandas trả: số dòng mỗi decision,
trung vị seconds, phút cho 100 mặt. Thử với 8 dòng số giả.
```

Ba quy tắc: (1) chỉ dán tên cột và số giả; (2) không gửi ảnh chụp trang rà soát cho mentor qua chat, chỉ chiếu trực tiếp; (3) số trong báo cáo phải lấy từ file, không chép tay.
