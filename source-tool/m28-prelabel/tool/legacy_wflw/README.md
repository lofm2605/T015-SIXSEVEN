# tool/legacy_wflw — lịch sử, không dùng (QĐ-001)

Công cụ của giai đoạn dùng WFLW (đáp án 98 điểm có sẵn). Từ 6/10/2026 đề tài dùng ảnh in-cabin YawDD + DrivFace, không còn đáp án
98 điểm và không học phép khớp nào (xem `so-quyet-dinh.md` QĐ-001, QĐ-002 dự thảo). Thư mục này được giữ (bằng `git mv`, nên lịch sử
còn nguyên) để:

- đọc lại cách làm cũ (`split.py`, `crop.py`, `wflw.py`, `fit_map.py`);
- `tool/check_drivface.py` chạy được ánh xạ ridge cũ (`mapping_ridge.py` + `map_mp50_wflw.json`) làm số so sánh với ánh xạ chọn đỉnh mới;
- các test của phần cũ (`tests/test_legacy_wflw_*.py`) còn kiểm được cái đã làm.

Không file nào trong `tool/` (ngoài `check_drivface.py`) import từ đây; gói giao khách không cần thư mục này.
Phần dùng chung (`OUT`, `SIDE_SCALE`, `crop_geometry`, `square_crop`) đã tách ra `tool/m28core/cat_mat.py`.
`map_mp50_wflw.json` là bản `config/map_mp50.json` cũ (ridge học trên WFLW), `m28_config_wflw.json` là config version 1 cũ.
