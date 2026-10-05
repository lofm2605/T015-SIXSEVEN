# P3 – Ánh xạ và đánh giá

Bạn giữ file cấu hình 50 điểm, làm đáp án 50 điểm và đổi 478 điểm MediaPipe sang 50 điểm. Bạn viết module đánh giá duy nhất mà cả nhóm dùng. Trong dự án thật, đổi bộ điểm không cần sửa code: sửa file cấu hình, rồi chạy lại bước khớp ánh xạ 478→N trên vài chục mặt đã gán theo bộ điểm mới (bỏ bớt điểm thì không cần khớp lại). Mọi con số chất lượng của nhóm đều ra từ module của bạn. Bạn cũng chấm xem trang rà soát trước CVAT có bắt được nháp hỏng không.

## Bạn nhận gì và giao gì

| Ngày | Nhận từ ai, cái gì | Giao cho ai, cái gì |
| --- | --- | --- |
| 5/10 | P5: định nghĩa 50 điểm, nếu có | P2, P4, P5: config bản 1 |
| 6/10 | P1: manifest.csv, gt98 theo ảnh cắt | P1, P4, P5: config bản 2, gt50.json |
| 7/10 | P2: MediaPipe 478 điểm. P1: 10 ảnh chồng F | P2, P4: mp50.json |
| 8/10 | P2: PIPNet 98 điểm | P2 (đầu buổi): eval50.py bản nháp có point\_errors. P2, P5: nme\_tdev.csv |
| 9/10 | `backups/P3/`: m28-gold-x (G3), m28-gold-y (G4). Cả nhóm (cuối khối 9/10; P1, P5 từ 8/10): 10 file `raw/m28-gold-*_<Pk>_*.xml` | Repo: `raw/m28-gold-x_P3_0910.xml`, `raw/m28-gold-y_P3_0910.xml` (tự xuất). P1 (cuối buổi): `apply_map()` trong `tool/m28core/mapping.py`, `map_mp50.json` (dời từ 19/10) |
| 10/10 | — (10 file xuất G do từng người tự commit cuối buổi 9/10; phút 0 `git pull` rồi `dir raw\m28-gold-*`; thiếu file của ai thì nhắn thẳng người đó xuất ngay, trong lúc chờ làm phần % T-dev) | P1, P2: sai số. P5: tdev\_in\_tol.csv, offset\_G.csv |
| 11/10 | P1: `r_list_1610.csv` (dùng ngày 16/10) | P1: `test_pipeline.py`, chỗ lệch nếu có (P1 sửa 13/10) |
| 12/10 | — | P4, P5: eval50.py |
| 13–15/10 | `backups/P3/`: m28-practice (D\_09–D\_12, 13/10), m28-manual (X3, 14/10), m28-assisted (X4, 15/10), khôi phục đầu mỗi buổi | Repo: `raw/<task>_P3_<ngày>.xml` (tự xuất cuối khối); giữ timing\_P3.csv trên máy, gửi P5 ngày 17/10 |
| 16/10 | P4 (lệnh `collect --skip-export` trên `raw/` cả nhóm đã commit): CSV QC, bảng ảnh chồng, `outputs/review_1610/P1.csv` (mặt P1 gán, bạn xem). P1: `runs/R1610/` (repo nội bộ) | `outputs/review_1610/P1.csv`: mã lỗi. P5: lỗi RULE |
| 17/10 | P5 (người xem mặt của bạn): mã lỗi trong `outputs/review_1610/P3.csv`. P5 (đầu buổi): `triage_P5.csv` | P5: nme\_per\_face.csv bản thô, timing\_P3.csv, `outputs/triage_R.csv` |
| 18/10 | — | Mentor (trong demo): số chấm trang rà soát |
| 19/10 | Repo: `raw/` của cả nhóm; nháp gốc (`mp50.json` hoặc `pip50.json`, `flags.json`) ở commit có tag 12/10 | P5: nme\_per\_face.csv |
| 20/10 | — (dùng config đóng băng từ 12/10) | P2: lỗi từng điểm T-test (ttest\_point\_err.csv) để đo cờ. P2, P5: ttest\_nme.csv |
| 21–24/10 | P4: công sửa, bỏ sót | P5: bảng, mục báo cáo, slide. P1: eval50.py |

## Lịch của bạn

File để trong `config/`, `data/`, `outputs/` như tab chung.

### Tuần 1

- [ ] **T2 5/10** Chốt config bản 1: tên, thứ tự, vùng, bên, cặp lật, mốc, cặp được trùng — chạy ở Máy mình — ra config/m28\_config.json — xong khi đủ 50 điểm, R nào cũng có cặp L. Cuối buổi (10 phút): đăng vào nhóm chat (chỉ chữ) bản Windows (`winver`), RAM, ổ C còn trống, dòng Virtualization; rồi cài CVAT phần A bước 1–2 (tab chung: kiểm máy, `wsl --install`), khởi động lại máy sau buổi; đầu buổi 6/10 mở Ubuntu tạo user Linux và kiểm `wsl -l -v` (Ubuntu ở VERSION 2), khoảng 5 phút.
- [ ] **T3 6/10** Thêm chỉ số WFLW, loại, curve, line, khuôn; sinh gt50 — chạy ở Máy mình — ra data/gt50.json — xong khi đủ 616 ảnh × 50 điểm.
- [ ] **T3 6/10** (giờ thứ hai) Chép và thử `similarity()`, `to_mean()`, `fit_ridge()` (code ở mục Làm thế nào) trên 20 điểm giả, theo prompt mẫu ở mục Nhờ AI — chạy ở Máy mình — ra code đã có test — xong khi test khôi phục s, R, t sai ≤ 1e-6. Hình trung bình 240 mặt F chạy đầu buổi 7/10 (khoảng 10 phút), khi đã có predictions.json của P2.
- [ ] **T4 7/10** Đầu buổi tính hình trung bình 240 mặt F (code Procrustes đã có từ 6/10); khớp ánh xạ 478→50 với k = 6 cố định, 4 giá trị λ, chia một lần (không chạy lưới 5 phần × 4 λ × 3 k); áp mọi tập; xem 10 ảnh chồng F — chạy ở Máy mình — ra map\_mp50.json, mp50.json — xong khi đã ghi NME 60 mặt kiểm, phép thử lật đạt, WFLW 0 và 60 ở nửa trái ảnh.
- [ ] **T5 8/10** Đầu buổi commit eval50.py bản nháp có point\_errors (code ở mục 3), báo P2. Rồi cài CVAT phần B (tab chung; phần A đã làm 5/10) xen với NME: tới `docker compose up -d` → trong lúc tải ảnh Docker, tính NME trên T-dev theo vùng cho MediaPipe → làm nốt phần B — chạy ở Máy mình — ra nme\_tdev.csv bản 1 (MediaPipe), CVAT v2.77.0 ở `http://localhost:8080` — xong khi P2, P5 đã nhận bản 1 và `python -m cvat_cli task ls` chạy không lỗi. Kẹt quá 15 phút thì báo P4, P5. Khi đó đầu buổi 10/10 bạn vẫn tính sai số trên các khối G đã đủ hai người (ngưỡng cờ của P2 không cần sai số), gán G của bạn ở giờ thứ hai 10/10 (P5 dời việc còn lại), và tính lại sai số đủ 20 mặt ngày CN 11/10, trước họp 12/10.
- [ ] **T6 9/10** Đầu buổi khôi phục `backups\P3\m28-gold-x.zip` và `backups\P3\m28-gold-y.zip`; gán tay G3 (m28-gold-x), G4 (m28-gold-y) — chạy ở CVAT trên máy mình — ra 8 mặt, `raw/m28-gold-x_P3_0910.xml`, `raw/m28-gold-y_P3_0910.xml` — xong khi 8 mặt qua checklist cuối mặt, đã tự xuất và commit. Trước 10/10 khôi phục thử `backups\all\m28-check.zip` (tab chung, bước 12).
- [ ] **T6 9/10** (giờ thứ hai) Gói `apply_map(pts478, map, config)`: nhận 478 điểm MediaPipe, trả `{tên điểm: [x, y]}` đúng thứ tự config, kèm hàm bỏ lật; đặt trong `tool/m28core/mapping.py` (dùng `similarity`, `to_mean`, `from_mean` và `map_mp50.json` đã có từ 7/10); giao P1 cuối buổi (dời từ 19/10) — chạy ở Máy mình (repo) — ra `mapping.py`, commit, tin báo P1 — xong khi `apply_map` trên 5 mặt F khớp `mp50.json` ≤ 0,001 px và P1 import được.
- [ ] **T7 10/10** Sai số từng vùng ngay đầu buổi (`git pull`; 10 file G do từng người tự commit cuối buổi 9/10; thiếu file nào thì nhắn người đó, làm % T-dev trước trong lúc chờ), rồi % T-dev trong sai số, điểm lệch định nghĩa — chạy ở Máy mình — ra tolerance trong config, tdev\_in\_tol.csv, offset\_G.csv — xong khi đã commit, P2 và P5 đã nhận.
- [ ] **CN 11/10** (khung chung 2 tiếng) Tải WFLW từ MyDrive/M28/ về máy nếu chưa có (có từ 7/10; khoảng 10 phút, phần lớn là chờ). Viết `test_pipeline.py` để chắc pipeline ra đúng số đã đóng băng, kiểm hai lần: (a) chỉ chạy bước đổi điểm trên `predictions.json` đã lưu của P2: kết quả gần như trùng `mp50.json` (lệch ≤ 0,001 px); (b) chạy lại cả `python tool\m28.py prepare --run DT --list data\manifest.csv --set D Tdev --images <WFLW_images> --box wflw` (không bao giờ trên X): lệch ≤ 0,05 px, tên điểm đúng thứ tự config — chạy ở Máy mình — ra `test_pipeline.py` — xong khi (a) và (b) đều qua, hoặc đã báo P1 chỗ lệch (P1 sửa ngày 13/10).
- [ ] **CN 11/10** (sau `test_pipeline.py`) NME trên T-dev theo vùng cho PIPNet và khuôn trung bình đặt vào hộp (dời từ 8/10), thêm vào nme\_tdev.csv — chạy ở Máy mình — ra nme\_tdev.csv đủ — xong khi P2, P5 đã nhận, trước họp 12/10.

### Tuần 2

Buổi gán: đọc câu chung, bật facetimer.py, không mở đáp án.

- [ ] **T2 12/10** Họp điểm dừng 20 phút đầu: trình % T-dev trong sai số (mốc ≥ 60%); rồi hoàn thiện eval50.py — chạy ở Máy mình — ra eval50.py, test\_eval50.py — xong khi nhóm chốt model, test qua trên 5 mặt.
- [ ] **T3 13/10** Đầu buổi khôi phục `backups\P3\m28-practice.zip` (D\_09–D\_12); làm quen 4 mặt D (3 nháp, 1 tay) — chạy ở CVAT trên máy mình — ra 4 mặt đã lưu, `raw/m28-practice_P3_1310.xml` — xong khi sửa đủ 3 mặt nháp, đã tự xuất và commit, eval50.py đã commit.
- [ ] **T4 14/10** Đầu buổi khôi phục `backups\P3\m28-manual.zip` (X3, không nháp), rồi mới bật facetimer; gán tay X3 — chạy ở CVAT trên máy mình — ra 10 mặt, 10 dòng bấm giờ, `raw/m28-manual_P3_1410.xml` — xong khi đã tự xuất và commit.
- [ ] **T5 15/10** Đầu buổi khôi phục `backups\P3\m28-assisted.zip` (X4, có nháp; không khôi phục trước hôm nay), rồi mới bật facetimer; sửa nhãn nháp X4, xem mọi điểm — chạy ở CVAT trên máy mình — ra 10 mặt, 10 dòng bấm giờ, `raw/m28-assisted_P3_1510.xml` — xong khi đã tự xuất và commit.
- [ ] **T6 16/10** Bù buổi lỡ (tự xuất `raw/<task>_P3_1610.xml`, commit trước khi mở bảng ảnh chồng); xem chéo mặt của P1 trong `outputs/review_1610/P1.csv` trên bảng ảnh chồng và ảnh cắt — chạy ở Máy mình — ra mã lỗi từng điểm trong file đó, đã commit — xong khi mặt nào cũng có mã hoặc "OK".
- [ ] **T6 16/10** (giờ thứ hai) Chuẩn bị chấm trang rà soát, chưa chạy trên R — chạy ở Máy mình — ra `gt50_R.py`, `triage_eval.py` — xong khi 8 dòng giả cho đúng số. Không chạy trên R trước khi P5 rà xong; không cho ai xem đáp án R.
  1. Viết `gt50_R.py`: đọc `r_list_1610.csv` và dòng WFLW tương ứng, ghi đáp án `gt50_R.json` và `gt98_R.json` theo toạ độ ảnh gốc (`gt50[tên] = gt98[wflw]`, giống gt50.json; eval50.py cần gt98 cho điểm C và IOD). Thêm hàm khớp mặt: mặt pipeline tìm được có tâm gần tâm hộp WFLW thì là đúng mặt; xa quá thì ghi "sai mặt".
  2. Viết `triage_eval()`: đếm mặt hỏng (định nghĩa trong eval50.py) bị chuyển sang Gán tay/Bỏ; đếm mặt tốt bị chuyển sang Gán tay/Bỏ; so người rà với gợi ý autoqc (chế độ `--review auto`). Thử trên 8 dòng giả có đáp án biết trước.
- [ ] **T7 17/10** Sửa mặt bị ghi lỗi trong `outputs/review_1610/P3.csv` trên CVAT của bạn, rồi tự xuất lần 2 (`export.py … --final`) và commit `final/`; chạy eval50.py trên `raw/` (ghép theo tên ảnh và tên điểm) — chạy ở CVAT + Máy mình — ra nme\_per\_face.csv bản thô, 2 file `final/` — xong khi đủ 100 lượt X.
- [ ] **T7 17/10** (giờ thứ hai, sau khi P5 đã commit `triage_P5.csv` lúc đầu buổi) Chạy `gt50_R.py` rồi `triage_eval` trên R1610 đúng một lần — chạy ở Máy mình — ra `outputs/triage_R.csv` (số nháp hỏng, số bị bắt, số mặt tốt bị đẩy sang tay; P5 so với `--review auto`) — xong khi đã commit và báo P5.
- [ ] **CN 18/10** (khung chung 2 tiếng) Trình số chấm trang rà soát trong buổi demo (khoảng 5 phút), báo cả số đếm (ví dụ 6/8) — chạy ở họp — xong khi mentor đã xem. Phần còn lại là dự phòng.

### Tuần 3

- [ ] **T2 19/10** NME ghép cặp trên X, theo vùng, vùng mắt, độ mở mắt — chạy ở Máy mình — ra nme\_per\_face.csv — xong khi P5 đã nhận.
- [ ] **T3 20/10** Chạy T-test đúng 1 lần, config đã đóng băng — chạy ở Máy mình — ra ttest\_nme.csv — xong khi commit ghi bản config, P2 và P5 đã nhận.
- [ ] **T4 21/10** Bảng chất lượng chính/phụ, có và không có mặt hỏng — chạy ở Máy mình — ra bảng cho P5 — xong khi số khớp nme\_per\_face.csv.
- [ ] **T5 22/10** Viết mục "Chất lượng nhãn" — chạy ở Máy mình — ra đoạn văn + bảng — xong khi P5 ghép vào báo cáo nháp.
- [ ] **T6 23/10** 2 slide (chất lượng; đổi bộ điểm bằng config), tập dượt — chạy ở Máy mình — ra 2 slide — xong khi tập trọn một lần đúng giờ.
- [ ] **T7 24/10** Chạy lại test trên bản clone mới; nộp; dự phòng — chạy ở Máy mình — ra repo chạy được — xong khi test qua. Khi P5 báo đã nộp: dọn máy theo tab chung (mục cài CVAT, đoạn "Dọn máy 24/10": thu hồi token, xoá `CVAT_URL` và `CVAT_ACCESS_TOKEN`, `docker compose down -v` trong `~/cvat`; khoảng 15 phút) rồi báo P4.

## Làm thế nào

**1. Config (5–6/10).** Mỗi điểm có: name (p01\_jaw\_R), region, side, flip, wflw, type, curve, line, anchor, coincide, tmpl. anchor = 1 nếu là điểm mốc, đặt trước rồi mới chia đều các điểm còn lại (hai đầu đường, giữa cằm, giữa môi, góc mắt, góc miệng). coincide = tên điểm được phép trùng với điểm này (mí trên/dưới khi nhắm, môi trong khi khép); QC của P4 bỏ qua cặp này khi tìm điểm dồn cục.

- side: R/L theo người trong ảnh; mặt thẳng thì R ở nửa trái ảnh.
- flip: cặp đối xứng, theo Mirror98.txt của WFLW.
- type: E = góc (khoé mắt, khoé miệng, đầu/đuôi lông mày, chóp mũi); C = giữa đường cong (viền, lông mày, môi); N = không tính.
- curve (điểm C): chỉ số WFLW của cả đường. tmpl: khuôn từ meanface.txt của PIPNet.
- line: tên đường 50 điểm chứa điểm này (vd jaw, brow\_R, lip\_outer), xếp theo thứ tự trên đường. P4 dùng cột này để nối cạnh label và kiểm thứ tự trong QC.

Nhóm chưa có định nghĩa của khách hàng (đã xác nhận 5/10), nên bạn tự chọn 50/98 và chốt tối 5/10, viền mặt lấy cách một điểm. gt50\[tên\] = gt98\[wflw\], toạ độ ảnh cắt 512.

**2. MediaPipe 478 → 50 (7/10).** Procrustes: xoay, co giãn, dời để hai hình khớp nhất. Ridge: hồi quy tuyến tính có phạt hệ số lớn, chống học vẹt.

1. Bỏ ảnh no\_face. Dùng similarity đưa 478 điểm MediaPipe của từng mặt trong 240 mặt F về khớp với mặt F đầu tiên, rồi lấy trung bình từng điểm: đó là hình trung bình. Phép đưa về khung trung bình luôn tính từ 478 điểm MediaPipe (không từ gt50), rồi áp cùng phép đó cho gt50; vì ảnh khách hàng không có đáp án.
2. `similarity` rồi `to_mean` đưa 478 điểm và gt50 của từng mặt về khung đó.
3. Với mỗi điểm trong 50 điểm: hồi quy ridge từ k = 6 điểm MediaPipe gần nó nhất trên hình trung bình. λ là độ mạnh của phạt. Thử λ = 0,1; 1; 10; 100. Chia 240 mặt thành 2 phần một lần: 192 mặt để khớp, 48 mặt để đo; cố định k = 6 (bản rút gọn để vừa buổi). Với mỗi λ: khớp trên 192 mặt, đo NME trên 48 mặt. Giữ λ có NME nhỏ nhất. Không dùng 60 mặt kiểm để chọn λ.
4. Báo NME trên 60 mặt kiểm. `from_mean` đưa kết quả về ảnh cắt.
5. Ảnh lật: đổi sang 50 trước, rồi x = 512 − x, đổi tên theo cột flip.
6. Kiểm: lật đáp án hai lần lệch ≤ 0,01 px; trung vị lệch gốc/lật trên 20 mặt thẳng F < 3% IOD (quên đổi cặp thì lệch hàng chục %).

```python
import numpy as np

def similarity(src, dst):
    """Procrustes: tìm s, R, t để s * src @ R.T + t gần dst nhất."""
    ms, md = src.mean(0), dst.mean(0)
    a, b = src - ms, dst - md
    U, S, Vt = np.linalg.svd(b.T @ a)
    k = np.sign(np.linalg.det(U @ Vt))             # chặn phép lật gương
    R = U @ np.diag([1.0, k]) @ Vt
    s = (S[0] + k * S[1]) / (a ** 2).sum()
    return s, R, md - s * R @ ms

def to_mean(p, s, R, t):                           # ảnh cắt -> khung hình trung bình
    return s * p @ R.T + t

def from_mean(q, s, R, t):                         # khung hình trung bình -> ảnh cắt
    return (q - t) @ R / s

def fit_ridge(X, Y, lam):
    """X: (n, 2k) toạ độ k đỉnh gần nhất; Y: (n, 2) điểm đáp án; cùng khung trung bình."""
    mx, my = X.mean(0), Y.mean(0)
    A = X - mx
    W = np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ (Y - my))
    return mx, W, my                               # dự đoán: (X_moi - mx) @ W + my
```

**3. eval50.py.** NME (độ lệch trung bình so với đáp án) tính bằng % IOD (khoảng cách hai khoé mắt ngoài, GT98\[60\]–GT98\[72\]). Chỉ số chính: điểm E đo điểm–điểm, điểm C đo tới đường cong. Chỉ số phụ: điểm–điểm cả 50 điểm. Báo trung bình, trung vị, % mặt hỏng (NME ≥ 10%), vùng mắt, độ mở mắt. Ghép điểm theo tên. Cột nme\_per\_face.csv: face\_id, condition (ghi đúng `manual` hoặc `assisted`), nme, nme\_eye, như đã hẹn P5.

```python
import numpy as np

def iod(gt98):                       # khoảng cách hai khoé mắt ngoài, theo đáp án
    return np.linalg.norm(gt98[60] - gt98[72])

def point_to_curve(p, curve):        # curve: (m, 2) điểm WFLW dày của đường đó
    a, ab = curve[:-1], curve[1:] - curve[:-1]
    u = ((p - a) * ab).sum(1) / np.maximum((ab ** 2).sum(1), 1e-9)
    proj = a + np.clip(u, 0, 1)[:, None] * ab
    return np.linalg.norm(proj - p, axis=1).min()

def point_errors(pred, gt50, gt98, cfg):
    """pred, gt50: dict tên -> (x, y) trên ảnh cắt 512. Trả dict tên -> lỗi % IOD."""
    d, err = iod(gt98), {}
    for pt in cfg["points"]:
        n, p = pt["name"], np.asarray(pred[pt["name"]], float)
        if pt["type"] == "E":
            err[n] = np.linalg.norm(p - np.asarray(gt50[n])) / d * 100
        elif pt["type"] == "C":
            err[n] = point_to_curve(p, gt98[pt["curve"]]) / d * 100
    return err                       # NME của mặt = trung bình; loại N bỏ qua
```

**4. Sai số chấp nhận (10/10).** Đo lệch giữa hai người gán cùng mặt G. Điểm C chỉ lấy phần lệch theo pháp tuyến (vuông góc với đường cong). Sai số vùng = 2 × trung vị, theo % IOD; trước đó tạm 3%. Đây là số để phân tích, không phải ngưỡng bỏ qua. Điểm lệch định nghĩa: lấy lệch có dấu (người − đáp án, giữ hướng lệch), tính trung bình trên G. Trị tuyệt đối > 1,5% IOD là lệch định nghĩa: cả nhóm đặt điểm đó lệch cùng một hướng so với WFLW, tức quy tắc của nhóm khác WFLW ở điểm đó. P5 ghi các điểm này vào bảng ca khó để báo khách hàng; khi đọc NME so với WFLW thì nhớ phần lệch này không phải lỗi gán.

**5. Công sửa (P4 chạy tuần 3).** So nhãn nháp (lấy từ `mp50.json`, hoặc `pip50.json` nếu họp chọn PIPNet, và `flags.json` ở commit có tag 12/10; trùng với nháp trong file backup) với `raw/m28-assisted_*` theo tên ảnh và tên điểm, không theo frame id (mỗi máy một id). Giữ: dời ≤ 0,5 px. Chỉnh nhẹ: dời hơn, trong sai số. Sửa: dời quá sai số. Bỏ sót: điểm nháp sai, xuất vẫn sai. Sửa thừa: điểm nháp cách đáp án ≤ 1 px vẫn bị dời. Tách có cờ/không cờ, theo vùng.

```python
import numpy as np

def correction_stats(pre, out, err_pre, err_out, tol, d):
    """pre, out: dict tên -> (x, y) của file nhập nháp và bản xuất raw/.
    err_pre, err_out: từ point_errors (% IOD); tol: tên -> sai số % IOD; d: IOD (px)."""
    bins = {"giu": 0, "chinh_nhe": 0, "sua": 0}
    miss, over = [0, 0], [0, 0]                     # [tử số, mẫu số]
    for n in err_pre:
        move = np.linalg.norm(np.subtract(out[n], pre[n]))   # px
        if move <= 0.5:
            bins["giu"] += 1
        elif move <= tol[n] / 100 * d:
            bins["chinh_nhe"] += 1
        else:
            bins["sua"] += 1
        if err_pre[n] > tol[n]:                     # điểm nháp sai
            miss[1] += 1
            miss[0] += err_out[n] > tol[n]          # vẫn sai khi xuất = bỏ sót
        if err_pre[n] / 100 * d <= 1.0:             # điểm nháp gần đúng (≤ 1 px)
            over[1] += 1
            over[0] += move > 0.5                   # vẫn bị dời = sửa thừa
    return bins, miss, over
```

## Chạy ở đâu

- **Máy mình (.venv chung):** mọi phép tính. Chỉ numpy trên file điểm, chạy vài giây. Code này sẽ vào công cụ offline CPU. Không thêm scipy, vì có máy Windows chặn DLL của nó.
- **CVAT (trên máy mình, localhost):** gán và sửa. Xem chéo làm trên bảng ảnh chồng ở Máy mình.
- **Colab:** chỉ khi .venv lỗi, báo P2 trước. Đáp án chỉ ở repo nội bộ, nên hỏi mentor trước khi đưa lên. Bạn không cần Kaggle hay GPU.

## Nhờ AI cho đúng

```text
Viết hàm Python chỉ dùng numpy: point_to_curve(p, curve) trả khoảng cách ngắn nhất từ điểm p (2,) tới đường gấp khúc curve (m, 2). Không chia cho 0 khi đoạn dài 0. Viết 5 test có đáp án tính tay: điểm trên đường, giữa một đoạn, ngoài đầu mút, đoạn thẳng đứng, đường chỉ 2 điểm.
```

```text
Write a numpy-only function similarity(src, dst) for 2D Procrustes (Umeyama), no reflection: return s, R, t so that s * src @ R.T + t is closest to dst. Add a test: 20 random points, apply s=1.7, rotation 30 degrees, t=(5,-3), check the recovered values within 1e-6.
```

```text
Viết hàm Python dùng xml.etree.ElementTree đọc file "CVAT for images 1.1". Mỗi <image name=...> có <skeleton label="face50"> chứa 50 <points label="pNN_..." occluded="0|1" outside="0" points="x,y">; mỗi points có <attribute name="low_conf">true|false</attribute>. Trả dict: tên ảnh -> tên điểm -> {x, y, occluded, low_conf}. Báo lỗi nếu thiếu điểm hoặc outside="1". Không dùng thư viện ngoài.
```

```text
Two annotators labelled the same faces: dict face -> point name -> (x, y). Each point has type "E" or "C" and a region. For E, use the distance between the two annotators. For C, use only the component along the normal of the nearest segment of a reference polyline ((m, 2) array). Return the median per region. numpy only, with tests on hand-made points.
```

Ba quy tắc:

1. Chỉ dán code và số tự đặt. Không dán ảnh mặt, gt50.json, file xuất CVAT hay dữ liệu khách hàng, kể cả vào Gemini trong Colab. Ảnh WFLW (CC BY-NC-ND) chỉ để nội bộ.
2. Chạy code AI trên 5 mẫu đã biết đáp án. Sai một mẫu là không dùng.
3. Bỏ code dùng mp.solutions hoặc hàm không có trong tài liệu chính thức. MediaPipe chỉ dùng vision.FaceLandmarker với face\_landmarker.task.

## Lỗi hay gặp

- **Sửa config sau 7/10.** Skeleton CVAT gần như không sửa được khi đã có task, mà từ 7/10 label này nằm trong mọi file backup phát cho 5 máy: sửa là P4 dựng lại hết và cả 5 người khôi phục lại, kể cả G đã gán. Không đổi tên, thứ tự, số điểm, cặp lật nữa.
- **Nhầm R/L.** Kiểm bằng ảnh chồng F và phép thử lật.
- **Sai hệ toạ độ.** Mọi file điểm ở ảnh cắt 512 (trừ gt50\_R, gt98\_R của tập R: toạ độ ảnh gốc). IOD lấy từ đáp án của chính mặt đó.
- **Dùng tập kiểm để chọn.** 60 mặt kiểm F và T-test không dùng để chỉnh gì. T-test chạy đúng 1 lần.
- **Nhìn đáp án trước khi gán.** Bạn có gt50.json. Không mở đáp án của G, D, X trước buổi gán.

## Khi bị kẹt

- Ảnh cắt, gt98, manifest.csv: P1.
- predictions.json, no\_face, cờ: P2.
- Label face50, file backup, cài CVAT, `export.py`: P4.
- Quy tắc đặt điểm, khoảng tin cậy, báo cáo: P5.
- Định nghĩa 50 điểm, giấy phép: mentor, qua P5.

Mang theo: face\_id, tên file và commit, lệnh đã chạy, toàn bộ thông báo lỗi, kết quả mong đợi và kết quả thật.

## Phần mới: ánh xạ trong pipeline và chấm trang rà soát (9–18/10)

Bạn giữ cho pipeline ra đúng như chuỗi đã đóng băng, và đo xem trang rà soát có bắt được nháp hỏng không. Đây là con số mentor sẽ hỏi: "giao diện này có đáng công không?". Trong dự án thật, con số này quyết định công ty có cần một người rà trước khi giao lô ảnh cho đội gán hay không.

**Test so với mp50.json.** So theo tên điểm, không so hash file (MediaPipe trên CPU khác có thể lệch ở chữ số cuối).

```python
# test_pipeline.py – so nhãn nháp của pipeline với mp50.json đã đóng băng
import json
ref = json.load(open("data/mp50.json"))           # {ảnh: {"orig": {tên: [x, y]}, "flip": {...}}}
new = json.load(open("runs/DT/map50/mp50.json"))  # cùng dạng, do m28.py ghi (D và T-dev)
worst = 0.0
for img, r in ref.items():
    if img not in new:
        continue
    assert list(new[img]["orig"]) == list(r["orig"]), img   # cùng tên, cùng thứ tự
    for name, (x, y) in r["orig"].items():
        nx, ny = new[img]["orig"][name]
        worst = max(worst, abs(nx - x), abs(ny - y))
n = len(set(ref) & set(new))                      # số ảnh khớp tên
print("so được", n, "/", len(new), "ảnh; lệch lớn nhất (px):", round(worst, 4))
assert n == len(new) > 0, "tên ảnh của pipeline khác tên trong mp50.json"
assert worst <= 0.05
```

**Chấm trang rà soát.** Một mặt là "hỏng" theo định nghĩa mặt hỏng trong eval50.py. Người rà "bắt được" khi chọn Gán tay hoặc Bỏ ảnh. Chỉ có một người rà (P5); so P5 với chế độ `--review auto` (lấy gợi ý autoqc). Báo cả số đếm (ví dụ 6/8), vì 40 mặt chỉ có vài mặt hỏng. Không tính trước khi P5 đã commit file rà: người rà không được thấy đáp án hay số chấm trước khi rà.

**Nhờ AI cho đúng.**

```text
Có ba bảng: triage.csv và auto.csv (file, decision ∈ {nhan, gan_tay, bo}) và truth.csv (file, hong ∈ {0,1}).
Viết hàm Python trả, cho từng bảng triage và auto: số mặt hỏng, số mặt hỏng có decision khác "nhan",
số mặt tốt có decision khác "nhan". Dùng pandas. Thử với 8 dòng số giả.
```

Ba quy tắc: (1) chỉ dán tên cột và số giả, không dán gt hay toạ độ thật; (2) không cho P5 xem đáp án hay ảnh chồng đáp án của R; (3) chạy `triage_eval` trên R đúng một lần, sau khi P5 đã commit `triage_P5.csv`.
