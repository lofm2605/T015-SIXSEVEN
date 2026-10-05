# Kế hoạch gán nhãn M28 – Landmark khuôn mặt

Oct 5, 2026

## Mục tiêu

Nhóm làm một công cụ đặt sẵn 50 điểm landmark lên ảnh khuôn mặt để người chỉ cần kiểm tra và sửa, rồi đo xem cách này nhanh hơn gán tay bao nhiêu mà nhãn không kém đi. Mục tiêu là nhanh hơn ít nhất 20%.

Công cụ phải dùng được cho một dự án thật, không chỉ cho thí nghiệm:

- Model mặc định là MediaPipe, giấy phép Apache-2.0, nên dùng cho khách hàng được. PIPNet chỉ dùng để so sánh.
- Chạy offline trên CPU máy thường, vì dữ liệu khách hàng thật thường không được đưa lên Colab, Kaggle hay chat AI.
- Đổi bộ điểm bằng file cấu hình, không sửa code; thêm hoặc đổi định nghĩa điểm thì chạy lại bước khớp trên vài chục mặt đã gán.
- Cũng chạy được bằng lệnh `cvat-cli task auto-annotate`: hàm chạy trên máy mình và đẩy nhãn nháp thẳng vào một task CVAT có sẵn.
- Một pipeline (chuỗi bước tự chạy nối nhau): lệnh `python tool/m28.py all` đi từ thư mục ảnh tới task CVAT có nhãn nháp. Giữa chừng có trang rà soát chạy trên máy (127.0.0.1) để một người duyệt từng mặt trước khi nhập. Thêm theo góp ý mentor ngày 5/10; xem mục "Pipeline một lệnh và trang rà soát trước CVAT".
- Kết quả cuối là một quy tắc: loại mặt nào nên dùng nhãn nháp, tiết kiệm bao nhiêu giờ trên 1.000 khuôn mặt.
- Landmark khuôn mặt dùng cho hệ thống giám sát tài xế (phát hiện buồn ngủ, mất tập trung), nên vùng mắt được báo riêng.

Năm câu hỏi báo cáo phải trả lời:

| Câu hỏi | Đo thế nào | Đạt khi |
| --- | --- | --- |
| Nhanh hơn không? | Mỗi người: số giây trung bình mỗi mặt khi có nhãn nháp chia cho khi gán tay; lấy trung bình nhân của 5 tỉ lệ (nhân 5 số rồi lấy căn bậc 5) | ≤ 0,8, và ít nhất 4 trên 5 người nhanh hơn |
| Nhãn có kém đi không? | So NME trên cùng một mặt được gán theo hai cách | Cận trên khoảng tin cậy 90% của hiệu NME (có nháp trừ gán tay) không quá +0,5% IOD |
| Nhãn nháp dùng được không? | % điểm nháp nằm trong sai số chấp nhận, trên tập T-dev | ≥ 60% |
| Cờ có chỉ đúng điểm sai không? | Cờ bật tối đa khoảng 7 điểm mỗi mặt; đếm số điểm sai mà cờ bắt được, trên tập T-test | Bắt được ≥ 50% số điểm sai; không đạt thì bỏ cờ |
| Pipeline và trang rà soát có ích không? | Chạy m28.py trên 40 ảnh tập R tới task CVAT; đếm nháp hỏng người rà bắt được, so với chế độ tự động | Đạt các mốc trong bảng đo ở mục Pipeline một lệnh |

Mỗi tiêu chí báo một trong ba mức: đạt, chưa kết luận, không đạt. Cách tính chi tiết nằm trong hướng dẫn của P3 và P5.

NME là độ lệch trung bình của các điểm so với đáp án, tính bằng % khoảng cách hai khoé mắt ngoài (IOD, điểm 60 và 72 của đáp án WFLW). Với điểm nằm giữa đường cong (viền mặt, lông mày, môi), chỉ tính độ lệch ra khỏi đường, không tính trượt dọc đường, vì mỗi bộ quy tắc chia điểm dọc đường hơi khác nhau.

Mọi chỗ đều dùng nhãn nháp rồi kiểm tra, trừ hai chỗ phải gán tay để con số không bị sai: nhánh gán tay của thí nghiệm (làm mốc so sánh), và tập G (đo người với người lệch nhau bao nhiêu).

Sản phẩm nộp:

- Công cụ nhãn nháp: lệnh `python tool/m28.py` (prepare → trang rà soát → push → collect) và một hàm cho `cvat-cli task auto-annotate`, dùng chung code; ảnh vào, task CVAT có nhãn 50 điểm ra. Kèm bằng chứng lượt chạy `demo-R1610` (task nằm trên CVAT của P4): `runs/R1610/push.json`, file XML xuất, `outputs/collect_demo-R1610.md` và số đo trong `report_pipeline.md`; task được chiếu khi demo.
- Bộ đánh giá: NME, số điểm phải sửa, thời gian mỗi mặt.
- Guideline 50 điểm kèm bảng ca khó, báo cáo thí nghiệm và quy tắc dùng nhãn nháp.

Phạm vi gồm ảnh tĩnh, một khuôn mặt mỗi ảnh. Video và ảnh hồng ngoại nằm ngoài phạm vi; với video, bản dùng thật chỉ nên đặt nhãn nháp ở keyframe.

## Dữ liệu

Nguồn ảnh là WFLW: 10.000 khuôn mặt (7.500 để huấn luyện, 2.500 để kiểm tra), mỗi mặt có sẵn đáp án 98 điểm và sáu cờ khó: góc nghiêng lớn, biểu cảm, ánh sáng, trang điểm, che khuất, mờ ([trang WFLW](https://wywu.github.io/projects/LAB/WFLW.html)).

- Ảnh WFLW lấy từ WIDER FACE, giấy phép CC BY-NC-ND: không dùng thương mại, không phát hành bản sửa đổi ([trang WIDER FACE](https://shuoyang1213.me/WIDERFACE/)). Ảnh cắt, đáp án và ảnh chồng điểm chỉ để trong CVAT trên máy từng người (chỉ mở được từ chính máy đó) và repo nội bộ; ngày 24/10 mỗi người xoá dữ liệu CVAT trên máy mình (tab Hướng dẫn chung, mục cài CVAT). Demo cho người ngoài dùng ảnh nội bộ có sự đồng ý.
- Đáp án 50 điểm suy từ 98 điểm WFLW bằng bảng ánh xạ của khách hàng. Kế hoạch giả định bộ 50 điểm suy được từ 98 điểm, như đề N1-03C mô tả.
- Mỗi khuôn mặt được cắt thành một ảnh vuông: cạnh bằng 1,4 lần cạnh dài của hộp mặt, cùng tâm, phần ra ngoài ảnh tô xám, đưa về 512 × 512 px. Mặt nào có điểm đáp án rơi ra ngoài ảnh cắt thì thay bằng mặt khác.

| Tập | Nguồn | Số mặt | Dùng để | Người gán |
| --- | --- | --- | --- | --- |
| F | WFLW train | 300 | Khớp cách đổi điểm MediaPipe sang 50 điểm (240 mặt để khớp, 60 mặt để kiểm) | Không ai |
| T-dev | WFLW test | 100 | Chọn model, chọn ngưỡng cờ, kiểm điểm dừng | Không ai |
| T-test | WFLW test | 100 | Kiểm tra cuối, chạy đúng một lần sau khi đã chốt mọi thứ | Không ai |
| G | WFLW test | 20 | Đo người với người lệch nhau bao nhiêu, để đặt sai số chấp nhận | Mỗi mặt 2 người gán tay, 40 lượt |
| P | WFLW test | 16 | Bấm giờ thử ở tuần 1 | P1 và P5; mỗi mặt gán cả hai cách, 32 lượt |
| X | WFLW test | 50 | Thí nghiệm chính | Mỗi mặt gán cả hai cách, do hai người khác nhau, 100 lượt |
| D | WFLW test | 30 | Buổi làm quen 13/10 và dự phòng | Khoảng 20 lượt |
| R | WFLW train (ảnh gốc, chưa cắt) | 50 | Chạy thật pipeline và chấm trang rà soát: 40 ảnh R1610, 10 ảnh demo R1810 | P5 rà; P4 sửa khoảng 5 mặt trên CVAT của P4 |

Các tập không trùng mặt nào; tổng cộng khoảng 192 lượt gán. P1 chia tập bằng một script có seed cố định. Tập X chia thành năm khối X1–X5, mỗi khối 10 mặt, có 1–2 mặt nghiêng lớn và 2–4 mặt bị che; 2 mặt đầu mỗi khối là mặt dễ. File đặt tên theo khối và thứ tự (X1\_01.png đến X5\_10.png, G1\_01.png, Pa\_01.png…).

Nếu lấy được nhãn 50 điểm gán tay ở tuần 2 của khoá học (trước dự án này), dùng thêm làm tập kiểm tra thứ hai.

## Guideline gán 50 điểm

Cả nhóm gán theo một bộ quy tắc duy nhất, và cùng một cách kiểm tra cho cả gán tay lẫn sửa nhãn nháp.

File cấu hình 50 điểm do P3 giữ và là nguồn duy nhất cho CVAT, ánh xạ và đánh giá. Mỗi điểm ghi: tên (ví dụ p01\_jaw\_R), vùng, bên phải/trái/giữa, điểm đối xứng, điểm WFLW tương ứng, và loại điểm (điểm góc hay điểm giữa đường cong). File chốt trong 5–6/10 và không sửa nữa từ khi P4 dựng project trên CVAT của P4 ngày 7/10: mọi task phát cho 5 máy đều mang label sinh từ file này. Nguồn là tài liệu khách hàng nếu có; hiện nhóm chưa có, nên P3 tự chọn 50 trong 98 điểm WFLW (xem mục Rủi ro) và chốt tối 5/10. Khi khách hàng gửi định nghĩa thì chỉ sửa config và khớp lại ánh xạ.

1. Hai lượt nhìn: nhìn cả mặt trước, rồi phóng to từng vùng (vùng chiếm ít nhất nửa màn hình) để đặt điểm. Ở chỗ điểm dày, di chuột lên điểm để xem tên trước khi kéo.
2. Điểm góc (khoé mắt, khoé miệng, đầu và đuôi lông mày): đặt đúng chỗ hai đường viền gặp nhau.
3. Đường cong: đặt các điểm mốc trước (hai đầu, điểm giữa cằm, giữa môi trên và dưới, góc mắt và góc miệng), rồi chia đều các điểm còn lại giữa hai mốc liền nhau.
4. Điểm bị che vẫn đặt ở chỗ ước lượng và bật cờ occluded. Bị che gồm bị vật che (tóc, kính, tay, khẩu trang, điện thoại) và bị chính mặt che (mắt phía xa sau sống mũi, viền hàm phía xa khi mặt nghiêng).
5. Không dùng cờ outside: điểm nào cũng phải có toạ độ.
6. Phải/trái là của người trong ảnh. Mặt nhìn thẳng thì điểm bên phải nằm ở nửa trái ảnh.
7. Khi có nhãn nháp, kiểm tra theo ba bước:
   1. Nhìn cả mặt: hình dạng, phải/trái, điểm dồn cục. Cả vùng lệch thì kéo cả vùng.
   2. Phóng to từng vùng theo thứ tự viền mặt, lông mày, mắt, mũi, miệng, và xem mọi điểm. Cờ low\_conf chỉ để nhắc chú ý, không phải chỉ xem điểm có cờ.
   3. Điểm đúng là điểm nằm đúng chỗ bạn sẽ tự đặt khi phóng to. Nhìn thấy lệch là sửa.
8. Cuối mỗi mặt, dùng chung một checklist cho cả hai cách gán: đã xem mọi vùng khi phóng to, đã bật occluded đúng, không có đường cắt nhau, màu bên đúng.
9. Khi định nghĩa khách hàng khác cách đặt của WFLW: trong thí nghiệm làm theo WFLW, và ghi vào bảng ca khó để báo khách hàng.

Sai số chấp nhận của mỗi vùng bằng 2 lần mức lệch trung vị giữa hai người trên tập G, tính ngày 10/10 và chốt ngày 12/10. Trước đó tạm dùng 3% IOD. Đây là con số để phân tích, không phải ngưỡng để bỏ qua điểm khi gán.

Bảng ca khó do P5 giữ. Mọi dòng đề xuất phải chốt trước 12/10, khi guideline bản 2 được đóng băng. Ca phát sinh trong 14–16/10 trả lời theo bản 2 và chỉ áp dụng cho bộ nhãn nộp sau kiểm tra.

| Ca khó | Quyết định đề xuất | Trạng thái | Người chốt |
| --- | --- | --- | --- |
| Mắt nhắm | Mí trên và mí dưới trùng nhau trên đường khép mi; đặt trên bờ mi, không đặt trên lông mi | Đề xuất |  |
| Miệng khép | Môi trong trên và dưới trùng nhau | Đề xuất |  |
| Râu che môi trên | Ước lượng theo dáng môi, bật occluded | Đề xuất |  |
| Tóc che lông mày | Ước lượng, bật occluded | Đề xuất |  |
| Đuôi lông mày mờ | Đặt ở cụm lông cuối còn thấy | Đề xuất |  |
| Kính trong | Nhìn qua kính thấy rõ thì không bật occluded | Đề xuất |  |
| Gọng kính che khoé mắt | Ước lượng, bật occluded | Đề xuất |  |
| Kính râm | Ước lượng từ gọng, lông mày và mũi, bật occluded | Đề xuất |  |
| Khẩu trang, tay hoặc điện thoại che miệng | Ước lượng theo dáng mặt, bật occluded | Đề xuất |  |
| Mặt nghiêng: viền hàm và mắt phía xa | Đặt theo cách của WFLW (xem trên 3 mặt nghiêng của tập F), bật occluded | Đề xuất |  |
| Điểm rơi vào vùng tô xám ngoài ảnh | Ước lượng, bật occluded | Đề xuất |  |

## Thiết lập CVAT

**Mỗi người một CVAT trên máy mình.** Nhóm dùng CVAT tự cài miễn phí và không có máy chủ chung, nên mỗi người chạy một CVAT bản v2.77.0 trên laptop của mình (Docker Engine trong Ubuntu WSL2, chỉ mở ở `http://localhost:8080`; cách cài ở tab Hướng dẫn chung). Năm CVAT phải giống hệt nhau, nên chỉ P4 dựng task: bằng script, hoặc bằng giao diện khi script trễ (chỉ task tuần 1, trong project `m28`, rồi sao lưu); không ai khác tạo label hay task bằng tay:

- P4 dựng mọi task thí nghiệm một lần trên CVAT của P4 bằng script `tool/build_backups.py`: label sinh từ file cấu hình, nhập nhãn nháp một lần khi task cần. Script sao lưu từng task thành file zip (task backup) vào `backups/<Pk>/` trong repo nội bộ rồi xoá task dựng ngay. P4 không mở task dựng nào.
- Mỗi người chỉ khôi phục (Create from backup) file trong thư mục của mình, đúng buổi ghi trong tab, rồi gán trên CVAT của mình. Mỗi task chỉ chứa khối của chủ máy và có đúng một job, nên không còn bước giao job.
- Gán xong, mỗi người tự xuất nhãn (chỉ nhãn, không ảnh) bằng `tool/export.py` và commit vào `raw/` với tên đã hẹn. P4 chạy QC và chia xem chéo từ file trong repo.

**Ở công ty thật**, CVAT là một server chung (tự host hoặc CVAT Online/Enterprise). Người quản lý tạo project và task một lần, giao job cho từng người theo vai trò, rồi xuất tất cả. Nhóm chạy 5 CVAT chỉ vì đây là bản tự cài miễn phí dùng cho đào tạo. Công cụ của nhóm (`m28.py`, `export.py`) đọc địa chỉ server và token từ biến môi trường `CVAT_URL`, `CVAT_ACCESS_TOKEN` (thêm `CVAT_ORG` khi project của công ty nằm trong một organization). Vì vậy, để chạy với một CVAT khác chỉ cần đổi các biến này, sửa số bản CVAT trong `config/pipeline.json` và cài `cvat-sdk` cùng bản với server, không sửa code. Bước "sao lưu rồi khôi phục" ở M28 thay cho bước "giao job" ở công ty.

- Label `face50` được sinh bằng script từ file cấu hình: 50 điểm đúng tên và thứ tự, mỗi điểm có checkbox `low_conf`, tô màu theo bên phải/trái/giữa, và có cạnh nối các điểm liền nhau trên cùng đường cong. Hai điểm bị đổi chỗ sẽ hiện thành đường gấp khúc lạ.
- Khuôn mặc định của skeleton là hình mặt trung bình 50 điểm. Gán tay trong CVAT nghĩa là vẽ khuôn này vào khung mặt rồi kéo từng điểm.
- Skeleton gần như không sửa được sau khi đã có task, nên file cấu hình phải chốt trước khi P4 dựng project `m28` trên CVAT của P4 ngày 7/10. Mọi task phát cho 5 máy mang cùng label này; sửa sau đó thì P4 phải dựng lại mọi file backup và cả 5 người phải khôi phục lại, kể cả tập G đã gán.
- Ngày 5/10, P4 cài CVAT v2.77.0 trên máy mình trước (máy đầu tiên của nhóm), rồi thử một skeleton 3 điểm để xem điểm có cờ có hiện rõ trên màn hình không, và thử sao lưu rồi khôi phục task đó (tên điểm và cờ còn nguyên không). Kết quả dùng được cho cả nhóm vì 5 máy chạy cùng bản. Nếu cờ không hiện, thêm một dòng chữ trên skeleton liệt kê các điểm có cờ, trước khi dựng project ngày 7/10. Buổi nhập thử 8/10 chỉ kiểm lại.

Bảng dưới cho biết mỗi task chứa tập nào. Cột Job và Giao cho là cách chia khi có một CVAT chung (công ty thật). Ở M28, mỗi task được tách theo người: xem bảng thứ hai.

| Task | Ảnh | Job | Nhãn nháp | Giao cho |
| --- | --- | --- | --- | --- |
| m28-gold-x | G (20 mặt) | 5 job × 4 mặt | Không | Job k cho Pk |
| m28-gold-y | G (cùng 20 ảnh) | 5 job × 4 mặt | Không | Job k cho P(k−1); job 1 cho P5 |
| m28-pilot-manual | P (16 mặt) | 2 job × 8 mặt | Không | Pa cho P1, Pb cho P5 |
| m28-pilot-assisted | P (cùng 16 ảnh) | 2 job × 8 mặt | Có | Pa cho P5, Pb cho P1 |
| m28-manual | X (50 mặt) | 5 job × 10 mặt | Không | Job k cho Pk |
| m28-assisted | X (cùng 50 ảnh) | 5 job × 10 mặt | Có | Job k cho P(k−1); job 1 cho P5 |
| m28-practice | D (30 mặt) | Mỗi người 1 job | Có, trừ 1 mặt mỗi job | Mỗi người |
| demo-pipe-test, demo-R1610, demo-R1810 | F5, tập R (WFLW) | push chia: job Nhận 8 mặt, 1 job Gán tay riêng | Có, trừ job Gán tay | demo-R1610: trên CVAT của P4, P4 sửa job 1; ngoài thí nghiệm |

Ở M28 mỗi khối X nằm trên đúng hai máy: máy người gán tay (task không nháp) và máy người sửa nháp (task có nháp), nên không ai gán cùng một mặt hai lần. Mỗi người có các task sau. Tên task giống nhau trên mọi máy; mỗi task chỉ chứa khối của chủ máy và có đúng một job. File nằm ở `backups/<Pk>/<tên task>.zip`.

| Người | G, không nháp (khôi phục ngày) | Thử nhanh | m28-practice (13/10) | m28-manual, không nháp | m28-assisted, có nháp |
| --- | --- | --- | --- | --- | --- |
| P1 | m28-gold-x G1, m28-gold-y G2 (8/10) | m28-pilot-manual Pa (9/10); m28-pilot-assisted Pb (10/10) | D\_01–D\_04 | X1 (14/10) | X2 (15/10) |
| P2 | G2, G3 (9/10) | — | D\_05–D\_08 | X2 (15/10) | X3 (14/10) |
| P3 | G3, G4 (9/10) | — | D\_09–D\_12 | X3 (14/10) | X4 (15/10) |
| P4 | G4, G5 (9/10) | — | D\_13–D\_16 | X4 (15/10) | X5 (14/10) |
| P5 | G5, G1 (8/10) | m28-pilot-assisted Pa (9/10); m28-pilot-manual Pb (10/10) | D\_17–D\_20 | X5 (14/10) | X1 (15/10) |

Trong m28-practice, 3 mặt đầu có nháp, mặt thứ tư gán tay. Task `demo-…` không nằm trong bảng: `push` tạo chúng trên CVAT của người chạy lệnh (tập R: CVAT của P4).

Quy tắc khi tạo task:

1. Một task = khối của một người = một job (file ảnh đặt tên theo khối, xếp theo tên; segment size bằng số ảnh). Mọi task dựng bằng cùng một hàm, cùng thông số (image\_quality 95, use\_cache bật: trong file zip ghi là `storage_method` "cache"). Task gán tay (`m28-manual`) và task sửa nháp (`m28-assisted`) của cùng khối chỉ khác một điều: có nhập nháp hay không. Trước khi commit, `tool/check_backup.py` của P4 đọc các file zip (không mở CVAT) và kiểm: đúng ảnh, đúng thông số, đúng số điểm, label giống nhau trên mọi file ("dấu vân tay label": tên, loại, thuộc tính, không dùng id). Sai một điều thì dừng. Kết quả ghi vào `backups/CHECK.txt`, kèm tag git đã dựng và mã băm từng file.
2. Nhãn nháp chỉ nhập một lần, trên task dựng ở CVAT của P4, ngay sau khi tạo task và trước khi sao lưu. Không ai nhập nháp trên máy mình. CVAT xoá nhãn cũ mỗi khi nhập lại ([tài liệu CVAT](https://docs.cvat.ai/docs/dataset_management/import-datasets/)); cần sửa thì P4 dựng lại file zip từ đầu. Kiểm nháp bằng `check_backup.py`: task có nháp phải có đủ 50 tên điểm và `low_conf` ở mỗi mặt, task không nháp phải có 0 điểm. Không mở task để kiểm.
3. Nhập và xuất cùng một định dạng XML của CVAT: menu nhập gọi là "CVAT 1.1", menu xuất gọi là "CVAT for images 1.1". Trước khi viết file nhập, gán tay một mặt và xuất ra để lấy đúng cấu trúc XML.

Ngày 5/10, P4 cài CVAT trên máy mình và thử trên một task nháp. CVAT của mỗi người chỉ có một tài khoản admin, nên không cần thử quyền hay vai trò:

- [ ] Tạo task
- [ ] Sao lưu task (Actions → Backup), xoá, rồi khôi phục (Create from backup): tên điểm, thứ tự, cờ low\_conf còn nguyên
- [ ] Nhập nhãn cho cả task (thử thật ngày 8/10: khứ hồi 5 mặt F, tab P4)
- [ ] Xuất nhãn của job

Ghi lại phiên bản (phải là 2.77.0, xem `http://localhost:8080/api/server/about`) và các lệnh cài đã chạy thật vào mục cài CVAT ở tab Hướng dẫn chung, để 4 bạn cài theo. Thử thêm: từ điện thoại cùng Wi-Fi mở `http://<IP LAN của laptop>:8080`. Không kết nối được (bị từ chối hoặc hết giờ) là đạt; thấy trang hay dòng "404 page not found" là CVAT đang lộ ra mạng LAN: sửa ngay.

## Chuỗi nhãn nháp

Nhãn nháp đi qua bốn bước chạy trên CPU rồi mới vào CVAT; nhánh gán tay dùng cùng bộ ảnh và cùng bộ đánh giá.

&#91;embedded content: chuỗi nhãn nháp · hai nhánh, một bộ đánh giá\]

1. Cắt mặt (P1): cắt ảnh vuông quanh hộp mặt và tạo đáp án 50 điểm cho từng ảnh.
2. Chạy model (P2), mỗi ảnh chạy cả bản gốc và bản lật ngang:
   - MediaPipe Face Landmarker là model chính: 478 điểm, giấy phép Apache-2.0, khoảng 0,04 giây mỗi ảnh trên CPU, đã chạy thử được trên một laptop Windows với Python 3.14 ([MediaPipe](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker)).
   - PIPNet ResNet-18 chỉ để so sánh và làm cờ: 98 điểm WFLW, khoảng 0,1 giây mỗi mặt trên CPU ([PIPNet](https://github.com/jhb86253817/PIPNet)).
   - Ghi lại ảnh nào model không tìm thấy mặt.
3. Đổi sang 50 điểm (P3) và gắn cờ (P2): PIPNet chọn thẳng 50 trong 98 điểm; MediaPipe đổi bằng một phép khớp học trên 240 mặt của tập F. Cờ low\_conf bật khi kết quả trên ảnh gốc và ảnh lật, hoặc của hai model, lệch nhau quá ngưỡng; tối đa khoảng 7 điểm mỗi mặt. Công cụ giao khách hàng chỉ dùng độ lệch giữa ảnh gốc và ảnh lật của MediaPipe, vì không được giao PIPNet.
4. Ghi file CVAT (P4): mỗi mặt một skeleton 50 điểm kèm cờ trên từng điểm. P4 ghi file và nhập một lần vào task dựng trên CVAT của P4, rồi sao lưu task; 5 máy nhận cùng nhãn nháp qua file zip, nên không cần ghi file riêng cho từng máy.

Quy tắc chọn model được chốt từ trước: dùng MediaPipe nếu ≥ 60% điểm trên T-dev nằm trong sai số chấp nhận. Chỉ khi không đạt, thí nghiệm mới dùng PIPNet và ghi rõ kết quả là "mức tốt nhất có thể, chỉ dùng nội bộ"; công cụ giao khách hàng vẫn dùng MediaPipe, và báo cáo ghi rõ vùng nào MediaPipe đủ tốt để đặt nhãn nháp (thường là mắt, mũi, môi). PIPNet học từ chính WFLW nên gần như chắc chắn thắng trên WFLW, nhưng trọng số của nó không giao khách hàng được.

Bản dùng thật nhận ảnh bất kỳ và tự dò khung mặt bằng MediaPipe, không cần hộp mặt của WFLW. Tuần 3, P2 chạy model thêm một lần trên T-test với khung tự dò, chỉ để báo chênh lệch; không chọn hay chỉnh gì theo kết quả này. MediaPipe yếu với mặt quay quá 80° hoặc bị che quá nửa (theo [model card](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20MediaPipe%20Face%20Mesh%20V2.pdf)), nên báo cáo tách riêng các loại mặt này.

## Pipeline một lệnh và trang rà soát trước CVAT

- **Máy tự làm:** cắt mặt, chạy MediaPipe, đổi sang 50 điểm, gắn cờ, tự kiểm (autoqc), vẽ ảnh chồng; tạo task CVAT mới và nhập nhãn nháp; sau khi gán thì xuất nhãn, chạy QC và viết báo cáo ngắn.
- **Người làm:** quyết định từng mặt trên trang rà soát (Nhận / Gán tay / Bỏ ảnh, 10–15 giây/mặt), gán và sửa nhãn trong CVAT, xem chéo. Ở công ty thật (một CVAT chung), người quản lý còn giao job trong CVAT. Ở M28 mỗi người dùng CVAT trên máy mình, nên không có bước giao job và xem chéo làm trên ảnh chồng.
- **Lô ảnh của khách (công ty thật: một CVAT chung):** cả bốn lệnh chạy trên một máy (máy người vận hành giữ token CVAT), ảnh không rời máy đó; người vận hành gõ `all` hai lần (lần 1 dừng ở trang rà soát), đội gán nhận task có sẵn nhãn nháp. Công cụ chỉ đọc `CVAT_URL` và `CVAT_ACCESS_TOKEN` (thêm `CVAT_ORG` nếu project nằm trong một organization); đổi các biến này, sửa số bản CVAT trong `config/pipeline.json` và cài `cvat-sdk` cùng bản với server là chạy được với CVAT đó. Ở M28 mỗi người trỏ tới CVAT trên máy mình (`http://localhost:8080`).

Mentor góp ý ngày 5/10: đề tài được đánh giá cao hơn nếu thành **một pipeline tự động** (chuỗi bước tự chạy nối nhau), hoặc có **giao diện trước khi nhập vào CVAT**. Nhóm làm cả hai bằng cách ghép các hàm đã có trong kế hoạch, không viết lại model. Việc mới nằm ở phần sau mỗi tối và hai Chủ nhật 11/10, 18/10.

Bốn lệnh trong một file `tool/m28.py`:

| Lệnh | Làm gì | Tự động hay người | Dùng lại code của |
| --- | --- | --- | --- |
| `prepare` | Làm nhãn nháp cho cả thư mục ảnh: cắt mặt (`--box auto` tự tìm mặt; `--box wflw` dùng hộp có sẵn của WFLW) → chạy MediaPipe trên ảnh và ảnh lật → đổi 478 điểm thành 50 điểm → đánh cờ `low_conf` cho điểm đáng ngờ → tự kiểm (autoqc) và gợi ý mỗi mặt: ổn / cần xem / nên gán tay → vẽ ảnh chồng (ảnh có chấm điểm) | Tự động, offline trên CPU | P1 square\_crop; P2 run\_mp, detect\_face; P3 apply\_map; P4 qc.py |
| `review` | Trang rà soát ở http://127.0.0.1:7860: lưới ảnh chồng, mặt đáng ngờ lên đầu; mỗi mặt bấm Nhận / Gán tay / Bỏ ảnh kèm lý do; ra `triage_<Pk>.csv` | Người, khoảng 10–15 giây/mặt. `--review auto` lấy luôn gợi ý autoqc; `--review excel` là dự phòng khi không có Gradio | P2 (vẽ bằng draw\_overlay của P1) |
| `push` (máy có `CVAT_URL` và token; ở M28: P4 push tập R lên CVAT của P4) | Ghi XML CVAT 1.1, tạo task MỚI tên `demo-…` trong project m28, nhập nhãn đúng một lần, xuất lại (chỉ nhãn) để kiểm đủ 50 tên điểm, ghi `push.json` | Tự động; ở công ty (một CVAT chung) giao job vẫn làm tay trên giao diện CVAT | P4 image\_xml, export.py |
| `collect` (sau khi gán; ở M28 P4 chạy `--skip-export` trên file `raw/` mọi người đã commit, chỉ xuất thật được task trên CVAT của chính máy đó) | Xuất từng job (chỉ nhãn) vào `raw/`, chạy qc.py, vẽ bảng ảnh chồng, ghi báo cáo ngắn `outputs/collect_<tag>.md` (số mặt, lỗi QC theo loại, mặt cần xem chéo, thời gian từng bước) | Tự động; ở M28 xem chéo trên ảnh chồng theo quy tắc cố định (mặt của Pk do P(k+2) xem), chủ mặt sửa trong CVAT của mình | P4 export.py, qc.py; P2 overlay.py |

`all` là cả chuỗi trong một lệnh, gõ hai lần. Lần 1: làm `prepare`, mở trang rà soát rồi dừng chờ người rà. Người rà bấm **Xong** và đóng trang (Ctrl+C trong cửa sổ cmd). Lần 2: gõ lại đúng lệnh đó; các bước đã xong được bỏ qua và lệnh đi tiếp sang `push`. Không cần người rà thì thêm `--review auto`: một lần chạy đi thẳng tới task CVAT.

Ba nút trên trang rà soát làm ba việc khác nhau:

- **Nhận**: ảnh lên task kèm nhãn nháp và cờ `low_conf`.
- **Gán tay**: ảnh lên task không có nhãn nháp, nằm trong một job riêng. Sửa một nhãn nháp quá tệ (lật gương, dồn cục) còn lâu hơn gán từ đầu. Ảnh có nhiều mặt cần gán cũng chọn Gán tay, vì pipeline chỉ làm nháp cho mặt lớn nhất.
- **Bỏ ảnh**: ảnh không lên CVAT; ghi vào `rejected.csv` kèm lý do (không có mặt, sai mặt, quá mờ hay quá nhỏ) để báo lại khách.

Kết quả rà nằm ở `runs/<run>/review/triage_<Pk>.csv`. Nút Xong ghi `runs/<run>/review/done.txt`, và `m28.py` dùng đúng file này để biết bước rà đã xong. Không có Gradio thì dùng `--review excel`: bước `prepare` đã vẽ sẵn ảnh chồng và ghi `autoqc.csv` có gợi ý cho từng mặt; người rà mở file đó bằng Excel, điền cột quyết định, lưu thành `triage_<Pk>.csv`.

Chạy lại có an toàn không? Có:

- Mỗi lần chạy có một tên (ví dụ `R1610`); kết quả nằm trong `runs/R1610/`, mỗi bước một thư mục con.
- Bước nào xong thật thì mới có file `done.txt`; gõ lại lệnh thì bước đó được bỏ qua. Bước chưa xong (rà chưa bấm Xong, chạy `--dry-run`) thì lệnh in lý do rồi dừng, không ghi `done.txt`. Muốn làm lại đúng một bước: thêm `--force <tên bước>`.
- `push` không chạy nếu: lần chạy này đã đẩy rồi (có `push.json`), tên task không bắt đầu bằng `demo-` (ví dụ task thí nghiệm `m28-`), hoặc chưa có token.
- `push` luôn tạo task mới rồi mới nhập nhãn, nên không bao giờ ghi đè nhãn người đã gán (CVAT nhập vào task cũ sẽ xoá nhãn cũ).
- `push` tải lên đúng ảnh mà XML dùng: `--box wflw` → ảnh cắt; `--box auto` → ảnh gốc trong thư mục `--images`. Tên ảnh trong XML trùng tên file tải lên.

Dùng trong công ty gán nhãn thật (một CVAT chung), ví dụ khách gửi 500 ảnh camera trong cabin (mỗi ảnh một tài xế, mặt lớn và rõ). Một lần cho mỗi khách: người quản lý CVAT tạo project có label sinh từ file cấu hình (`make_label.py`) và ghi tên project, tiền tố tên task vào `config/pipeline.json`. Địa chỉ server và token để trong biến môi trường `CVAT_URL`, `CVAT_ACCESS_TOKEN` của người vận hành, không commit. Sau đó, với mỗi lô ảnh:

1. Người vận hành (người giữ token CVAT) chép ảnh vào máy mình và chạy `python tool\m28.py all --run KH01 --images D:\khach\lo1 --box auto --task <tên task>`. Bước chuẩn bị không cần mạng.
2. Trang rà soát mở trên chính máy đó. Người rà ngồi tại máy này, bấm Nhận / Gán tay / Bỏ ảnh, mỗi mặt 10–15 giây, rồi bấm Xong.
3. Gõ lại đúng lệnh ở bước 1: lệnh tạo task mới trong CVAT; mặt Nhận có nhãn nháp, mặt Gán tay nằm trong job riêng.
4. Quản lý giao job trên CVAT; gửi `rejected.csv` cho khách (ảnh bị bỏ và lý do).
5. Gán xong, chạy `collect` trên cùng máy: xuất nhãn, kiểm lỗi, vẽ ảnh chồng, ra báo cáo ngắn.

Ảnh của khách và thư mục `runs/KH01/` không rời máy này: không commit, không gửi qua chat. Mỗi ảnh chỉ có nháp cho mặt lớn nhất; ảnh có nhiều người cần gán thì chọn Gán tay. Khách dùng bộ điểm khác thì đổi file `--config`, không sửa code; tiền tố tên task của dự án ghi trong `config/pipeline.json`.

Giữ an toàn cho thí nghiệm:

- Task X, D, P, G do `tool/build_backups.py` dựng trên CVAT của P4 và phát qua file zip (mục Thiết lập CVAT), không dùng `push`; `push` từ chối mọi tên `m28-`, còn `build_backups.py` không tạo task `demo-…`.
- Pipeline chỉ tạo task tên `demo-…` trong project `m28`. `push` tìm project theo tên, máy nào chưa có thì tạo từ `config/face50_label.json`. Dùng một project cho gọn (CVAT tự cài không giới hạn số task). `push` từ chối mọi tên bắt đầu bằng `m28-`.
- 14–15/10 không ai mở trang rà soát, task `demo-…` hay ảnh chồng có nhãn nháp; phần sau hai tối này chỉ viết code hoặc chữ.
- Bộ lọc `low_conf` trong CVAT chỉ dùng làm hàng đợi từ 16/10.
- Trang rà soát chỉ thử trên mặt F, D và tập R; không bao giờ trên X.

Giữ an toàn dữ liệu và giấy phép:

- Trang rà soát chỉ chạy ở 127.0.0.1, `share=False` ghi rõ trong code; không chạy trên Colab/Kaggle (Colab tự bật link công khai), không tunnel. Gradio báo không vào được localhost thì **không** bật `share=True`; dùng `--review excel`.
- Với ảnh khách hàng, cả bốn lệnh chạy trên một máy và `runs/` không rời máy đó. Chỉ `runs/F5/` và `runs/R1610/` (ảnh WFLW) được commit vào repo nội bộ, như ảnh cắt hiện nay, để P2, P5 thử trang rà soát và P4 thử push (11/10) trên `runs/F5/`, P5 rà R1610 và P4 push tập R lên CVAT của P4. Không ai commit `push.json` vào `runs/F5/` (có file này thì push sau đó bị từ chối trên mọi máy); ai muốn tập push thì chạy lượt mới `all --run thu<Pk>` vào CVAT của mình, như P1 ngày 18/10 (`demo-thuP1`). Task `demo-R1610` chỉ nằm trên CVAT của P4, nên chỉ P4 sửa nó.
- Token CVAT (Personal Access Token: mã truy cập cá nhân thay mật khẩu): mỗi người một token cho CVAT trên máy mình, chỉ nằm trong biến môi trường người dùng `CVAT_ACCESS_TOKEN` (kèm `CVAT_URL=http://localhost:8080`), hạn 25/10, mỗi người tự thu hồi ngày 24/10. Xuất luôn với `include_images=False`. CVAT mỗi máy chỉ nghe ở 127.0.0.1: không mở cho mạng LAN, không chuyển cổng, không tunnel.
- `tool/` chỉ chứa MediaPipe, Gradio (Apache-2.0) và cvat-sdk (MIT). PIPNet, eval50.py, correction\_stats nằm ngoài `tool/`; `test_no_torch.py` kiểm điều này. `map_mp50.json` khớp trên WFLW: chỉ giao cho khách khi mentor đồng ý (xem tab P1).

Tập R (ảnh để chạy thật và chấm trang rà soát): 50 ảnh WFLW gốc, chưa cắt, lấy từ tập train, chưa dùng ở đâu trong dự án, mỗi ảnh có một mặt lớn. WFLW có sẵn đáp án, nên đo được người rà bắt đúng bao nhiêu nháp hỏng. 40 ảnh dùng cho lượt chạy thật `R1610` (16–18/10), 10 ảnh để demo `R1810` (18/10). Vì sao chọn mặt lớn: model tìm mặt của MediaPipe làm tốt với mặt gần camera (như camera trong cabin) và hay sót mặt nhỏ trong ảnh đông người. Số ảnh không tìm thấy mặt vẫn được báo.

| Đo gì | Đạt khi |
| --- | --- |
| Một lệnh chạy trọn | `all` trên ảnh R (tập dượt 17/10, demo 18/10) tới task CVAT không lỗi; chạy lại thì bỏ qua bước đã xong và `push` từ chối |
| Nhập đúng | 100% mặt Nhận có đủ 50 điểm đúng tên và `low_conf` sau khi xuất lại; 0 lần đẩy vào task `m28-` |
| Nhanh | Thời gian máy từ thư mục ảnh tới task (40 ảnh R1610: prepare + push) ≤ 10 phút; trung vị thời gian rà ≤ 15 giây/mặt |
| Rà có ích | Trên R1610, người rà đưa ≥ 70% mặt hỏng (định nghĩa trong eval50.py) sang Gán tay hoặc Bỏ, và ≤ 15% mặt tốt; so với `--review auto`; báo cả số đếm |
| Bớt việc tay | Mỗi lô ảnh mới: trước khoảng 8 bước tay của 4 người (cắt, MediaPipe, đổi điểm, cờ, ghi XML, tạo task, nhập, kiểm), sau còn 3 việc của 2 người (chạy lệnh, rà, giao job) |

Bảng này thành tiêu chí thứ 5 "Pipeline và rà soát" trong bảng kết luận, cũng 3 mức như bốn tiêu chí kia.

Ai xây phần nào:

| Phần | Ai | Xong |
| --- | --- | --- |
| Khung `m28.py`; bước crop, mediapipe, map50, flags; `--box auto`; lệnh `all`; nối trang rà soát | P1 | 8–13/10; nối 16/10 |
| `detect_face()` (tự dò khung mặt); trang rà soát Gradio `review_app.py` | P2 | 11/10; bản 1 13/10, bản 2 16/10 |
| `apply_map()`, `test_pipeline.py`, chấm trang rà soát trên R (`triage_eval`) | P3 | 9/10, 11/10, 17/10 |
| autoqc, `push`, `collect` | P4 | thử 9/10; 11/10, 13–14/10 |
| Quy tắc rà (`guideline_triage.md`), người rà tập R, số liệu pipeline, demo mentor | P5 | 11/10, 17/10, 18–19/10 |

Việc thêm nếu dư giờ (không nằm trong lịch): `review_assign()` tự tạo file xem chéo trong `collect`; P4 sửa nốt job 2 của `demo-R1610`; mỗi người chạy lượt mới `all --run thu<Pk>` trên 5 mặt F vào CVAT của mình để tập (lệnh ở tab chung; không push thẳng `runs/F5/`, thư mục đã commit); bộ lọc trên trang rà soát.

Lượt chạy thật và demo:

- CN 11/10 (20–30 phút, nếu mentor rảnh): trình kế hoạch này; P1 chiếu `prepare` trên 5 mặt F.
- 16/10: P1 chạy `prepare` trên 40 ảnh R (R1610), commit `runs/R1610/`.
- 17/10: đầu buổi P5 rà 40 mặt; phần sau P4 chạy `push` tạo `demo-R1610`, rồi tập dượt `all` trên máy P4; P3 chấm trang rà soát (`triage_R.csv`).
- CN 18/10 (khoảng 30 phút): P4 chạy `all` trên 10 ảnh R mới → trang rà soát → task `demo-R1810` trên CVAT của P4; chạy lại để thấy bước bỏ qua và `push` từ chối. P1 chiếu cùng lệnh `all` trên 5 mặt F vào CVAT của P1: chỉ đổi `CVAT_URL` và token, giống cách công cụ chạy trên server chung của công ty. P3, P5 trình số của R1610. Trước demo, P4 sửa khoảng 5 mặt (job 1) trong `demo-R1610`; sau demo P4 chạy `collect`.
- 23–24/10: P4 chạy cùng chuỗi trên ảnh demo của P5 với `--box auto`, cả bốn lệnh trên máy P4, thêm `cvat-cli task auto-annotate`.

## Thí nghiệm đo

Mỗi mặt trong tập X được gán hai lần bởi hai người khác nhau, một lần gán tay và một lần sửa nhãn nháp, nên hai cách được so trên đúng cùng một khuôn mặt.

| Người | Gán tay | Sửa nhãn nháp | 14/10 làm | 15/10 làm |
| --- | --- | --- | --- | --- |
| P1 | X1 | X2 | Gán tay | Nhãn nháp |
| P2 | X2 | X3 | Nhãn nháp | Gán tay |
| P3 | X3 | X4 | Gán tay | Nhãn nháp |
| P4 | X4 | X5 | Nhãn nháp | Gán tay |
| P5 | X5 | X1 | Gán tay | Nhãn nháp |

Quy tắc khi gán:

1. Bấm giờ từng mặt bằng `facetimer.py`: Enter khi xong một mặt, p khi tạm dừng. Hai mặt đầu mỗi khối là khởi động, không tính; mỗi người còn 8 mặt tính giờ cho mỗi cách.
2. Mỗi khối 10 mặt làm trọn trong một buổi; bị ngắt thì làm tiếp ở buổi bù 16/10.
3. Đầu buổi cả nhóm đọc cùng một câu: "Làm theo nhịp bình thường; mặt xong khi mọi điểm đúng quy tắc."
4. Không mở đáp án WFLW, và không xem tổng thời gian của ai trước 17/10.
5. Đầu buổi, mỗi người khôi phục đúng task của hôm nay từ `backups/<Pk>/` (task gán tay và task sửa nháp khôi phục cùng một cách), rồi mới bật facetimer. Không khôi phục trước buổi, không mở file zip của người khác. Cuối khối, mỗi người tự xuất nhãn (`python tool\export.py <task> <Pk> <ngày>`) và commit trong tối đó. File này dùng để tính chất lượng, trước mọi lần sửa ở bước kiểm tra.
6. Trước 14/10, mỗi người đã sửa ít nhất 3 mặt có nhãn nháp ở buổi làm quen 13/10, và model, ngưỡng cờ, sai số chấp nhận đã chốt trong repo.

Mỗi khối luôn 10 mặt: mỗi tối có 120 phút, đủ cả khi gán tay mất hơn 5 phút mỗi mặt. P5 ghi điều này vào biên bản họp 12/10.

Những gì được đo:

- Thời gian: giây mỗi mặt, theo từng người và từng cách gán.
- Chất lượng: NME của từng mặt ở hai cách gán; vùng mắt báo riêng, kèm sai số độ mở mắt (dùng để phát hiện buồn ngủ).
- Công sửa: mỗi điểm nháp được giữ nguyên, chỉnh nhẹ, hay sửa hẳn.
- Bỏ sót: trong các điểm nháp bị sai, bao nhiêu % vẫn sai khi nộp. Con số cao nghĩa là người gán chỉ liếc qua rồi bấm xong.
- Sửa thừa: điểm nháp đã đúng mà vẫn bị kéo đi.
- Theo loại mặt: dữ liệu người gán chỉ tách hai nhóm (nghiêng hoặc bị che, và còn lại). Kết quả theo đủ sáu cờ khó của WFLW chỉ làm trên model, ở tập T.

Với 5 người và 50 mặt, kết quả là chỉ báo, không phải thống kê chặt. Báo cáo ghi kèm khoảng tin cậy; cách tính nằm trong hướng dẫn của P5.

## Chia việc

Mỗi người có 18 tối × 120 phút (T2–T7) và 2 buổi Chủ nhật 11/10, 18/10 (tối đa 120 phút mỗi buổi). Ở việc chính, P1 và P5 dành 7 buổi cho việc gán và việc chung, 11 buổi cho việc riêng; P2, P3, P4 dành 5 buổi chung và 13 buổi riêng. Phần còn lại của mỗi tối và hai Chủ nhật dành cho pipeline, trang rà soát và dự phòng. Không buổi nào quá 120 phút.

Phần pipeline: P1 dựng lệnh `m28.py` và bước `prepare`; P2 tự dò khung mặt và trang rà soát; P3 hàm `apply_map`, test so với `mp50.json` và chấm trang rà soát trên tập R; P4 autoqc, `push`, `collect`; P5 quy tắc rà, người rà tập R, số liệu pipeline và demo mentor. Chi tiết ở mục "Pipeline một lệnh và trang rà soát trước CVAT" và trong lịch từng người.

| Người | Phụ trách | Đầu ra chính |
| --- | --- | --- |
| P1 – Dữ liệu và đóng gói | Tải WFLW, cắt mặt, chia tập, đóng băng file cấu hình cuối cùng; dựng lệnh m28.py (8–16/10); tuần 3 cvat\_func.py và README | Ảnh cắt, `manifest.csv`, công cụ nhãn nháp dùng được |
| P2 – Model và cờ | Chạy MediaPipe và PIPNet, tính điểm cờ và ngưỡng cờ, làm bảng ảnh chồng điểm để soát; tự dò khung mặt và trang rà soát trước CVAT | `predictions.json`, cờ cho từng điểm |
| P3 – Ánh xạ và đánh giá | File cấu hình 50 điểm, bảng 98 sang 50, đổi điểm MediaPipe, sai số chấp nhận, một module đánh giá dùng chung; apply\_map cho pipeline, chấm trang rà soát | `gt50.json`, module đánh giá |
| P4 – CVAT | Sinh label; dựng task và nhập nháp trên CVAT của P4, phát file backup cho 5 máy (`build_backups.py`, `check_backup.py`); `export.py` cho cả nhóm; hướng dẫn cài CVAT; script kiểm tra; chia xem chéo từ file trong repo; bước push và collect của pipeline | File backup sẵn sàng, `export.py`, báo cáo kiểm tra |
| P5 – Thí nghiệm và báo cáo | Guideline, bảng ca khó, `facetimer.py`, phân tích, báo cáo và demo; quy tắc rà soát, người rà tập R | Guideline bản 2, kết quả, báo cáo |

Mỗi người gán 8 mặt tập G, 20 mặt tập X và 4 mặt làm quen; P1 và P5 gán thêm 16 mặt thử nhanh. Toàn bộ code nằm chung một repo và dùng chung file cấu hình 50 điểm, để thứ tự điểm không lệch giữa CVAT, ánh xạ và đánh giá. Khung M24 dùng lại được phần tạo task, nhập xuất CVAT và tổng hợp thời gian.

Việc cụ thể từng buổi của mỗi người nằm trong các tab riêng: Hướng dẫn từng người (phần chung), P1 – Dữ liệu, P2 – Model, P3 – Ánh xạ, P4 – CVAT, P5 – Thí nghiệm.

## Lịch 3 tuần

Tuần 1 dựng chuỗi và đo thử, 20 phút đầu buổi thứ Hai 12/10 quyết định làm tiếp hay đổi hướng, tuần 2 chạy thí nghiệm, tuần 3 phân tích và báo cáo. CN 11/10 và CN 18/10 là buổi làm: cả nhóm làm cùng một khung 2 tiếng do P5 hẹn trước (đề xuất 9:00–11:00), gặp mentor trong khung đó. 11/10 trình kế hoạch có pipeline; 18/10 demo bản chạy được. Mỗi tối T2–T7 có 120 phút theo nhịp trong tab Hướng dẫn chung.

&#91;embedded content: lịch 3 tuần · 18 tối × 2 tiếng + 2 Chủ nhật mỗi người\]

Tuần 1, từng buổi:

| Buổi | P1 – Dữ liệu | P2 – Model và cờ | P3 – Ánh xạ và đánh giá | P4 – CVAT | P5 – Thí nghiệm |
| --- | --- | --- | --- | --- | --- |
| T2 5/10 | Tải WFLW; viết script cắt ảnh vuông | Dựng môi trường chung; chạy MediaPipe trên 1 ảnh | Chốt file cấu hình 50 điểm; cuối buổi cài CVAT phần A | Cài CVAT v2.77.0 trên máy mình (máy đầu tiên), chốt bản cho cả nhóm; thử skeleton 3 điểm và sao lưu/khôi phục | Hỏi mentor; viết guideline bản 1 |
| T3 6/10 | Cắt toàn bộ 616 ảnh; chia tập ra `manifest.csv`; cuối buổi bắt đầu cài CVAT (phần A) | Chạy MediaPipe trên toàn bộ ảnh, bản gốc và bản lật; trong lúc chạy, cài CVAT phần A | Bảng 98 sang 50 và đáp án `gt50.json` | Skeleton 3 điểm đã thử 5/10; viết script sinh label `face50`; gán tay 1 mặt F, xuất XML mẫu; viết `tasks.json`, `build_backups.py` bản đầu | Soát cách chia tập; viết sẵn bảng ca khó; cài CVAT phần A (phần B tối 7/10) |
| T4 7/10 | Chồng đáp án lên 10 mặt F để soát; cài CVAT phần B trong lúc Colab chép | Chạy PIPNet trên toàn bộ ảnh | Khớp cách đổi MediaPipe sang 50 điểm, áp cho mọi tập | Dựng project `m28` và file backup tuần 1 (G, pilot gán tay) bằng `build_backups.py`, kiểm bằng `check_backup.py`; bắt đầu `write_xml.py` | Viết `facetimer.py`; xong guideline bản 1; cài CVAT phần B |
| T5 8/10 | Gán tập G (8 mặt), tự xuất | Tính điểm cờ trên T-dev; cài CVAT phần B | NME MediaPipe theo vùng trên T-dev (PIPNet, khuôn trung bình dời CN 11/10); cài CVAT phần B | Đầu buổi viết `export.py` cho cả nhóm (P1, P5 xuất G tối nay); nhập thử 5 mặt; dựng backup pilot có nháp (P1, P5) và `m28-check` | Gán tập G (8 mặt), tự xuất |
| T6 9/10 | Thử nhanh: gán tay Pa | Gán tập G (8 mặt), tự xuất | Gán tập G (8 mặt), tự xuất | Gán tập G (8 mặt), tự xuất G của mình; dựng 5 backup `m28-manual` (không nháp) | Thử nhanh: sửa nhãn nháp Pa |
| T7 10/10 | Thử nhanh: sửa nhãn nháp Pb | Chọn ngưỡng cờ trên T-dev; ghi cờ cho X và D | Tính sai số chấp nhận từ G; % điểm T-dev trong sai số | Viết `qc.py` trên 10 file G mọi người đã commit (P1, P5 tự xuất buổi thử) | Thử nhanh: gán tay Pb |

Phần sau của buổi và Chủ nhật, tuần 1 (pipeline và việc dời):

- T2 5/10: P2 thử Gradio trong `.venv` chung, ghim `cvat-sdk==2.77.0`, `cvat-cli==2.77.0`; P4 skeleton 3 điểm, thử sao lưu/khôi phục, kiểm CVAT không lộ ra LAN; cả nhóm đăng bản Windows, RAM, ổ C trống, Virtualization vào nhóm chat (chỉ chữ).
- T3 6/10: P2 chuẩn bị PIPNet; P3 code Procrustes trên điểm giả; P4 mặt mẫu XML, `config/tasks.json`, `build_backups.py` bản đầu (dời từ 7/10).
- T4 7/10: P1 chép WFLW lên MyDrive/M28/; P4 bắt đầu `write_xml.py`; P5 làm nốt cài CVAT phần B.
- T5 8/10: P1 khung `m28.py`.
- T6 9/10: P1 bước cắt + MediaPipe; P3 giao `apply_map`; mỗi người tự xuất G của mình cuối khối; P4 dựng 5 backup `m28-manual` (không nháp) bằng cùng `build_backups.py`.
- T7 10/10: P1 bước đổi 50 điểm, cờ, XML; commit `runs/F5/`.
- CN 11/10 (khung chung 2 tiếng): P1, P5 gặp mentor; P1 chọn tập R, `test_no_torch.py` (dời từ 8/10); P2 `detect_face` và khung trang rà soát; P3 `test_pipeline.py`, NME T-dev phần PIPNet và khuôn trung bình (dời từ 8/10); P4 `push.py` trên CVAT của P4; P5 `guideline_triage.md`.

Tuần 2:

- T2 12/10: 20 phút đầu họp điểm dừng do P5 chủ trì. Họp chốt cờ cho nháp X, D (t\_flip hay t). Ngay sau họp, P2 commit `flags.json`, P1 đóng băng file cấu hình (model, sai số, ngưỡng cờ) và gắn tag. P4 dựng 5 backup `m28-practice` và 5 backup `m28-assisted` từ đúng commit có tag (script tự chạy, P4 không mở task nào) và commit `backups/CHECK.txt`; không đổi cờ sau khi dựng. Không ai khôi phục task tuần 2 tối nay. P3 hoàn thiện module đánh giá; P5 chốt guideline bản 2 và bảng ca khó; P2 làm bảng ảnh chồng điểm.
- Phần sau của buổi 12–15/10: P1 thêm `--box auto` (12/10), lệnh `all` (13/10), README nháp (15/10); P2 trang rà soát bản 1 (13/10); P4 autoqc (13/10), viết `collect` (14/10); P5 kịch bản demo (15/10). 14–15/10 phần sau chỉ viết code hoặc chữ, không mở ảnh có nhãn nháp.
- T3 13/10: đầu buổi mỗi người khôi phục `m28-practice` của mình, làm quen 4 mặt tập D (3 có nhãn nháp, 1 gán tay), bấm giờ, tự xuất và commit; P4 chạy QC trên 5 file. Đây là buổi tập dượt đúng quy trình của 14–15/10.
- T4 14/10: lượt gán thứ nhất theo bảng thí nghiệm. Đầu buổi mỗi người khôi phục đúng task của mình hôm nay, cuối khối tự xuất và commit `raw/<task>_<Pk>_1410.xml`.
- T5 15/10: lượt gán thứ hai. Đầu buổi mỗi người khôi phục đúng task của mình hôm nay, cuối khối tự xuất và commit `raw/<task>_<Pk>_1510.xml`.
- T6 16/10: bù buổi lỡ (người bù tự xuất, commit trước khi mở ảnh chồng); P4 `git pull` rồi chạy `m28.py collect --skip-export` trên 10 file `raw/` (QC, bảng ảnh chồng, báo cáo ngắn), commit bảng ảnh chồng; cả nhóm xem chéo trên ảnh chồng. Phần sau: P1 nối trang rà soát và autoqc vào `m28.py`, chạy `prepare` trên tập R (R1610), gắn tag `pipeline-mvp`; P2 trang rà soát bản 2; P3 chuẩn bị chấm (`gt50_R.py`, `triage_eval.py`, chưa chạy trên R); P1, P4, P5 cài `requirements-ui.txt`; P4 tải WFLW về máy.
- T7 17/10: mỗi người sửa lỗi trên CVAT của mình, tự xuất lần hai vào `final/` và commit; P4 kiểm đủ 10 file, ra số liệu thô.
- T7 17/10, đầu buổi: P5 rà 40 mặt R1610 trên trang rà soát (khoảng 20 phút). Phần sau: P4 chạy `m28.py push` tạo task `demo-R1610`, rồi tập dượt demo; P3 chấm trang rà soát (`triage_R.csv`).
- CN 18/10 (khung chung 2 tiếng): P4 sửa khoảng 5 mặt trong `demo-R1610` (CVAT của P4); P1 chạy thử `all` trên 5 mặt F vào CVAT của P1; 30 phút demo cho mentor (một lệnh → trang rà soát → task CVAT; P1 chỉ ra chỉ cần đổi `CVAT_URL` và token là chạy trên server khác); P4 chạy `collect`; P5 viết nháp `report_pipeline.md`.

Tuần 3:

- T2–T4 19–21/10: phân tích. P5 làm thời gian; P3 làm NME và chạy T-test đúng một lần; P4 làm công sửa và tỉ lệ bỏ sót; P2 làm kết quả theo loại mặt và chạy T-test với khung mặt tự dò (hàm đã có từ 11/10); P1 đóng gói công cụ (m28.py chạy được từ 16/10; tuần 3 thêm cvat\_func.py bản mỏng và README).
- T5 22/10: bản nháp báo cáo, kèm quy tắc dùng nhãn nháp và số giờ tiết kiệm trên 1.000 mặt.
- T6 23/10: slide, demo và tập dượt; P4 chạy `m28.py all` trên ảnh demo, cả bốn lệnh trên máy P4 (như với ảnh khách hàng), thêm `cvat-cli task auto-annotate`.
- T7 24/10: nộp; thời gian còn lại dành cho việc trễ.

## Kiểm soát chất lượng

Mọi file xuất đều qua một script kiểm tra và một lượt xem ảnh chồng điểm. Phần sửa ở bước này không tính vào số liệu thí nghiệm.

Script kiểm tra (P4) có năm phép kiểm, kết quả ra file CSV gồm mặt, điểm và lỗi:

1. Đủ 50 điểm, đúng tên.
2. Không bị lật gương, tức phải và trái không bị đảo.
3. Đúng thứ tự trên mỗi đường cong, đường không tự cắt.
4. Không có điểm dồn cục, trừ các cặp được phép trùng (mí mắt khi nhắm, môi khi khép).
5. Không có điểm lệch xa bất thường so với hình mặt trung bình.

Ngưỡng của script được chỉnh trên tập G trước 14/10, để không báo nhầm mặt nhắm mắt, miệng khép hay mặt nghiêng.

Thứ tự xử lý job thí nghiệm:

1. Mỗi người tự xuất task của mình ngay cuối khối 14/10 và 15/10 (`python tool\export.py`, chỉ nhãn) và commit vào `raw/<task>_<Pk>_<ngày>.xml` trong tối đó. Các file này dùng để tính chất lượng; không ai sửa file trong `raw/`.
2. Ngày 16/10, P4 `git pull`, kiểm đủ 10 file rồi chạy `m28.py collect --skip-export` trên các file `raw/` (script kiểm tra, bảng ảnh chồng bằng overlay.py của P2, báo cáo ngắn) và commit bảng ảnh chồng; P2 quét bảng, mỗi mặt khoảng 10 giây, báo P4 mặt đáng ngờ. `collect` chỉ xuất được từ CVAT trên chính máy chạy nó, nên với task thí nghiệm luôn dùng `--skip-export`.
3. Xem chéo trên ảnh chồng (không ai mở được CVAT máy khác): mọi mặt bị script hoặc bảng ảnh đánh dấu, cộng 1 mặt ngẫu nhiên mỗi task. Mặt của Pk do P(k+2) xem (mặt của P4 do P1 xem, mặt của P5 do P2 xem), nên không ai xem mặt mình hay khối mình đã gán. Ghi mã lỗi cho từng điểm vào `outputs/review_1610/<chủ mặt>.csv`: SWAP (đổi chỗ), MIRROR (lật phải trái), COLLAPSE (dồn cục), MISPLACED (đặt sai), OCC\_FLAG (sai cờ che), RULE (ca chưa có quy tắc, ghi vào bảng ca khó).
4. Ngày 17/10 chủ mặt sửa lỗi trên CVAT của mình, ghi "đã sửa" vào file của mình, rồi tự xuất lần hai vào `final/<task>_<Pk>_1710.xml` làm bộ nộp; P4 kiểm đủ file và ghi riêng số lỗi đã sửa.

## Rủi ro và điểm dừng

20 phút đầu buổi thứ Hai 12/10, nhóm quyết định làm tiếp hay đổi hướng dựa trên ba kiểm tra, để còn hai tuần nếu phải đổi.

| Kiểm tra | Đạt khi | Không đạt thì |
| --- | --- | --- |
| Nhập thử vào CVAT | Cả 5 máy chạy 2.77.0 (máy dự phòng dùng CVAT Online đã được duyệt thì ghi bản server, vẫn phải khôi phục và xuất được `m28-check`); mặt có nháp trong `m28-check` hiện đúng tên, đúng thứ tự 50 điểm và thấy cờ trên cả 5 máy; `backups/CHECK.txt` sạch (cùng dấu vân tay label, task không nháp có 0 điểm); khứ hồi buổi thử của P1, P5 đạt | Sửa file nhập rồi dựng lại backup. Phương án B: P4 dùng `cvat-cli task auto-annotate` với một hàm đọc sẵn kết quả model, chạy trên task dựng ở CVAT của P4 trước khi sao lưu; 5 máy vẫn nhận qua file zip. Một máy lỗi: cài lại đúng v2.77.0 rồi khôi phục lại |
| Nhãn nháp dùng được | ≥ 60% điểm trên T-dev nằm trong sai số chấp nhận | Đổi model theo quy tắc đã chốt, hoặc chỉ đặt nhãn nháp cho mắt, mũi, môi |
| Bấm giờ thử (P1, P5) | Ít nhất một người nhanh hơn khi có nhãn nháp | Cả hai người đều chậm hơn (tỉ lệ > 1,0): chuyển sang M26 hoặc M31. Nhanh hơn nhưng tỉ lệ 0,8–1,0: vẫn làm tiếp, xem lại ba bước kiểm tra nhãn nháp trong guideline |

Mức 0,8 là tiêu chí cuối cho cả 5 người, không áp cho buổi thử hai người. Số phút mỗi mặt khi gán tay ở buổi thử chỉ dùng để ước giờ cho tuần 2; khối luôn 10 mặt.

Kiểm tra thêm cho pipeline và trang rà soát:

| Kiểm tra | Đạt khi | Không đạt thì |
| --- | --- | --- |
| CVAT trên 5 máy (P4 5/10, cả nhóm tới 9/10) | Cả 5 máy chạy v2.77.0 và có token; trên CVAT của P4 tạo task, nhập, sao lưu, xuất bằng cvat-sdk được; mỗi máy khôi phục `m28-check.zip` và xuất được | Sao lưu/khôi phục hỏng: mỗi người chạy `build_backups.py --person Pk --local` trên máy mình (cùng hàm tạo task, chỉ nhập nháp vào task có nháp của mình, đầu buổi của task đó); `push --dry-run` chỉ ghi XML; pipeline vẫn có prepare và trang rà soát |
| Gradio trên Python 3.14 (P2, 5/10) | Cài vào `.venv` chung không đổi numpy, pillow, opencv; trang mở ở 127.0.0.1; `check_mp.py` vẫn in 1.0.1 và 478 | Dựng lại `.venv` từ `requirements.txt`; cả nhóm rà bằng `--review excel` (ảnh chồng và Excel) |
| push.py (P4, 11/10) | Task thử có 50 điểm đúng tên, có `low_conf`; chạy lần 2 bị từ chối | Demo 18/10 dùng `push --dry-run` và nhập tay; sửa push trong tuần 3 |
| Tập dượt `all` (P4, 17/10) | Lần 1 dừng ở trang rà soát, lần 2 tạo task, lần 3 bị từ chối, không lỗi | Demo 18/10 dùng `--review auto` hoặc `--review excel`; ghi lỗi để sửa tuần 3 |
| Thí nghiệm sạch (14–15/10) | Không ai mở trang rà soát, task demo hay ảnh chồng có nháp; task thí nghiệm chỉ được khôi phục đầu buổi của chính nó (ngày 16/10 P5 đọc giờ tạo task trong file `.txt` mà `export.py` ghi kèm mỗi file `raw/`); file zip trong `backups/` khớp mã băm ghi ở `CHECK.txt` | Ghi vào checkpoint, báo mentor, phân tích riêng người đó |
| Lộ ảnh hay token | Không có link công khai; token không có trong repo, log, chat; ảnh khách hàng chỉ ở một máy; CVAT mỗi máy chỉ nghe ở 127.0.0.1 (thử từ điện thoại không vào được) | Thu hồi token ngay trong CVAT, báo mentor |
| Quá tải | Không buổi nào quá 120 phút | Bỏ trước: phần sửa `demo-R1610` ngày 18/10, rồi `collect` (làm tay như cũ). Không bỏ `prepare`, trang rà soát, `push` |
| Mentor không gặp được Chủ nhật | — | Gặp buổi ngày thường gần nhất qua chia sẻ màn hình; tắt ghi hình và trợ lý AI ghi chú của phần mềm họp; không gửi file có ảnh mặt |

Rủi ro còn lại và cách xử lý:

- Không có định nghĩa 50 điểm (đã xác nhận ngày 5/10): nhóm tự chọn 50 trong 98 điểm WFLW (góc mắt, giữa mí, góc miệng, môi, lông mày, mũi, viền mặt lấy cách một điểm), chốt tối 5/10.
- Giấy phép: code PIPNet theo MIT, nhưng trọng số học từ ảnh WIDER FACE (CC BY-NC-ND), nên chỉ dùng demo nội bộ, không giao khách hàng. MediaPipe theo Apache-2.0.
- Máy cá nhân: MediaPipe 1.0.1 mới chạy thử được trên một laptop Windows với Python 3.14; mỗi người kiểm lại trên máy mình ngày 5–6/10. Máy nào báo lỗi (ví dụ Windows chặn file DLL của scipy) thì chạy trên Colab hoặc Kaggle, không tắt bảo mật của Windows.
- Hướng dẫn cũ trên mạng dùng `mp.solutions.face_mesh`, nay đã bị gỡ khỏi MediaPipe; chỉ dùng Tasks API (`FaceLandmarker`), kể cả khi nhờ AI viết code.
- Mặt nghiêng và bị che: nhãn nháp kém hơn nhiều; báo cáo tách theo loại mặt và đề xuất chỉ dùng nhãn nháp khi đạt ngưỡng.
- Số liệu nhiễu vì chỉ có 5 người: báo khoảng tin cậy, kèm tỉ lệ điểm phải sửa làm bằng chứng thứ hai.
- Cài CVAT trên 5 laptop (Windows 11): ảo hoá tắt trong BIOS, thiếu quyền admin, máy 8 GB (một người dùng đo CVAT chạy không tải khoảng 4 GB RAM), ổ C gần đầy (CVAT dừng khi ổ dữ liệu quá 90%), mạng chặn tải. Cách xử lý: P4 cài trong tối 5/10 (máy đầu tiên), cả nhóm khảo sát máy tối 5/10, chia cài làm phần A/B, hạn cài là trước buổi gán G đầu tiên của mỗi người. Hỏng quá 15 phút thì báo ngay trong tối; G của người đó dời sang buổi sau (P3 bắt đầu tính sai số từ các file đã có).
- Năm máy lệch nhau: clone không đúng tag, tự nâng lên v2.78, hay tự sửa label. Cách xử lý: chỉ clone `--branch v2.77.0`; `export.py --check` từ chối máy khác 2.77.0 (trừ máy CVAT Online đã duyệt, chạy với `--allow-version`); chỉ P4 dựng task, không ai tạo label bằng tay; `CHECK.txt` so dấu vân tay label.
- Docker Desktop chỉ miễn phí cho cá nhân, giáo dục và công ty dưới 250 người kèm doanh thu dưới 10 triệu USD (tính theo tổ chức mà mình làm việc cho, không theo chủ laptop), và trang yêu cầu hiện chỉ liệt kê Windows 11 Pro/Enterprise/Education (bản Home chưa ai thử). Vì vậy cả nhóm dùng Docker Engine trong Ubuntu WSL2: miễn phí, chạy cả trên Windows Home.
- Mất dữ liệu CVAT trên một máy (lỡ `docker compose down -v`, hỏng máy). Bản chính là file XML trong `raw/` và `final/`; cài lại đúng bản, khôi phục lại từ `backups/`, và chỉ cho phần sửa 16–17/10 thì nhập lại file `raw/` của chính mình.
- Máy không chạy được Docker (không bật được ảo hoá hay không có quyền admin): người đó dùng tài khoản CVAT Online miễn phí cá nhân, chỉ với ảnh WFLW, khi trưởng nhóm và mentor đồng ý (gói Free cho khoảng 1 project, 3 task: khôi phục từng task đầu buổi, xuất xong thì xoá task; thử trước bằng `m28-check.zip`). Người đó đặt `CVAT_URL=https://app.cvat.ai` và token tạo trên tài khoản đó; `export.py` chạy với `--allow-version` (vẫn ghi bản server vào file `.txt`); ở họp 12/10 tính là "4 máy 2.77.0 + 1 CVAT Online, khôi phục `m28-check` đạt".
- Ảnh mặt nằm trên 5 laptop tới 24/10. Ngày 24/10, sau khi nộp, mỗi người thu hồi token, xoá biến môi trường và chạy `docker compose down -v` trong `~/cvat`; P4 kiểm cả nhóm đã báo xong.

## Câu hỏi cho mentor

Tám câu hỏi này cần có câu trả lời trong buổi đầu tiên, vì chúng quyết định dữ liệu, quyền và cách đo.

- [ ] Định nghĩa bộ 50 điểm của khách hàng và bảng ánh xạ từ 98 điểm WFLW nằm ở đâu?
- [ ] Ở tuần 2 của khoá học (trước dự án này), nhóm đã gán 50 điểm bằng skeleton hay 50 điểm rời? Có lấy được nhãn và số phút mỗi mặt của tuần đó không?
- [ ] Nhóm chạy CVAT tự cài (v2.77.0) trên laptop từng người, chỉ mở trên chính máy đó, và xoá ảnh khỏi CVAT ngày 24/10. Làm như vậy với ảnh WFLW có được không? Chương trình đào tạo này có được dùng Docker Desktop miễn phí không (nhóm mặc định dùng Docker Engine trong WSL2, miễn phí)? Máy nào không chạy được Docker thì người đó có được dùng tài khoản CVAT Online miễn phí cá nhân, chỉ với ảnh WFLW, không (cần trả lời trước 8/10, buổi gán G đầu tiên)?
- [ ] Đề M28 có chấp nhận đo trên ảnh WFLW thay cho ảnh khoang xe không?
- [ ] Dùng ảnh WFLW/WIDER FACE (CC BY-NC-ND) trong chương trình đào tạo của công ty có được không? Ảnh cắt và ảnh chồng điểm có được đưa vào báo cáo, demo không?
- [ ] PIPNet có code MIT nhưng trọng số học từ ảnh WIDER FACE. Có được dùng trong thí nghiệm và demo nội bộ không? File đổi điểm MediaPipe sang 50 điểm được khớp trên ảnh WFLW; có được giao kèm công cụ cho khách hàng không?
- [ ] Có được dùng Colab, Kaggle và trợ lý AI với dữ liệu công khai không, và có quy định nào về dữ liệu khách hàng không?
- [ ] Nếu đã có nhóm nhận N1-03C, nhóm mình có dùng chung bảng ánh xạ 98 sang 50 điểm của họ được không?

Thêm ngày 5/10, về pipeline (cần trả lời trước CN 11/10):

- [ ] Anh có đồng ý hướng mới không: lệnh `m28.py` đi từ thư mục ảnh tới task CVAT, có trang rà soát chạy trên máy trước khi nhập? Anh có thể gặp 20–30 phút trong khung 2 tiếng của nhóm ngày CN 11/10 và CN 18/10 không, hay gặp ngày thường qua chia sẻ màn hình?
- [ ] Task demo nằm trong project m28 trên CVAT của P4, tên bắt đầu bằng `demo-`; như vậy có được không?
- [ ] Nhóm có được dùng ảnh WFLW (tập R, 50 ảnh) cho task demo và buổi demo không? Gói công cụ giao đi có được kèm Gradio (Apache-2.0) và cvat-sdk (MIT) không?
