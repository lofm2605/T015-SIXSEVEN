"""Thử tool/check_drivface.py (50 điểm DMS, ghép bên THEO VỊ TRÍ TRONG ẢNH) bằng dữ liệu GIẢ: file drivPoints giả (CRLF, tên có dấu cách cuối), ảnh xám, landmarker giả. Không ảnh người thật."""
import json
import os
import sys
import types

import cv2
import numpy as np
import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
import check_drivface as cd  # noqa: E402
from m28core import steps  # noqa: E402
from m28core.cat_mat import square_crop  # noqa: E402

CONFIG = os.path.join(HERE, '..', 'config')
CFG = json.load(open(os.path.join(CONFIG, 'm28_config.json'), encoding='utf-8'))
MAP = json.load(open(os.path.join(CONFIG, 'map_mp50.json'), encoding='utf-8'))
HEADER = 'fileName,subject,imgNum,label,ang,xF,yF,wF,hF,xRE,yRE,xLE,yLE,xN,yN,xRM,yRM,xLM,yLM'


def write_drivface(root, lines):
    (root / 'imgs' / 'DrivImages').mkdir(parents=True)
    with open(root / 'drivPoints.txt', 'w', newline='', encoding='utf-8') as f:
        f.write(HEADER + '\r\n' + '\r\n'.join(lines) + '\r\n')                          # CRLF như file thật
    return root


def test_read_drivpoints_keeps_trailing_space_and_parses_numbers(tmp_path):
    root = write_drivface(tmp_path, ['20130529_01_Driv_001_f ,1,1,2,0,292,209,100,112,323,232,367,231,353,254,332,278,361,278',
                                     '20130530_02_Driv_007_lf ,2,7,3,30,10,20,30,40,100,100,150,100,125,130,110,160,140,160'])
    rows = cd.read_drivpoints(str(root / 'drivPoints.txt'))
    assert len(rows) == 2 and rows[0]['name'] == '20130529_01_Driv_001_f ' and rows[0]['label'] == 2 and rows[1]['label'] == 3 and rows[1]['subject'] == 2
    assert rows[0]['pts']['RE'] == (323.0, 232.0) and rows[0]['pts']['LM'] == (361.0, 278.0) and rows[0]['box'] == (292.0, 209.0, 100.0, 112.0)
    assert rows[1]['ang'] == 30.0


def test_find_image_handles_space_before_extension(tmp_path):
    d = tmp_path / 'imgs'
    d.mkdir()
    (d / '20130529_01_Driv_001_f .jpg').write_bytes(b'x')
    (d / 'khac.jpg').write_bytes(b'x')
    assert cd.find_image(str(d), '20130529_01_Driv_001_f ').endswith('001_f .jpg')       # tên thật có dấu cách trước .jpg
    assert cd.find_image(str(d), '20130529_01_Driv_001_f').endswith('001_f .jpg')        # CSV không có dấu cách: vẫn tìm ra
    assert cd.find_image(str(d), 'khac').endswith('khac.jpg') and cd.find_image(str(d), 'khong_co ') is None


def rows_with_sides(flip=False):
    a, b = (367, 323) if flip else (323, 367)
    return [dict(name=f'n{i} ', subject=1, label=2 if i < 8 else 1, ang=0, box=(0, 0, 1, 1),
                 pts={'RE': (a, 100), 'LE': (b, 100), 'N': (345, 130), 'RM': (a + 10, 160), 'LM': (b - 10, 160)}) for i in range(10)]


def test_side_convention_is_checked_on_frontal_images():
    eye, mouth, n = cd.side_convention(rows_with_sides())
    assert eye == 1.0 and mouth == 1.0 and n == 8                                           # chỉ xét ảnh label 2
    eye2, mouth2, _ = cd.side_convention(rows_with_sides(flip=True))
    assert eye2 == 0.0 and mouth2 == 0.0


def pts50_from_tmpl():
    return {p['name']: [float(p['tmpl'][0]), float(p['tmpl'][1])] for p in CFG['points']}


EYE_L = [f'mattrai_{k}' for k in range(1, 9)]             # nửa trái ảnh (người: mắt phải)
EYE_R = [f'matphai_{k}' for k in range(1, 9)]


def test_ours_five_means_of_8_eye_points_nose_tip_and_lip_corners():
    p50 = pts50_from_tmpl()
    p478 = np.zeros((478, 2))
    p478[468], p478[473], p478[2], p478[4] = [1, 2], [3, 4], [5, 6], [7, 8]
    five = cd.ours_five(p50, CFG, p478)
    assert np.allclose(five['eye_trai'], np.mean([p50[n] for n in EYE_L], axis=0)) and np.allclose(five['eye_phai'], np.mean([p50[n] for n in EYE_R], axis=0))      # 8 điểm mỗi mắt
    assert np.allclose(five['nose_tip'], p50['songmui_4'])                                     # chóp mũi; không còn chân mũi p31 trong 50 điểm
    assert np.allclose(five['mouth_trai'], p50['moingoai_1']) and np.allclose(five['mouth_phai'], p50['moingoai_7'])      # hai khoé môi ngoài, trái ảnh trước
    assert np.allclose(five['iris_trai'], [1, 2]) and np.allclose(five['iris_phai'], [3, 4])
    assert np.allclose(five['nose_v2'], [5, 6]) and np.allclose(five['nose_v4'], [7, 8])       # tham chiếu NGOÀI 50 điểm lấy thẳng từ 478 đỉnh
    plain = cd.ours_five(p50, CFG)
    assert not {'iris_trai', 'iris_phai', 'nose_v2', 'nose_v4'} & set(plain) and set(plain) == {'eye_trai', 'eye_phai', 'nose_tip', 'mouth_trai', 'mouth_phai'}
    assert [n for n, _ in cd.COMPARE] == ['eye_trai', 'eye_phai', 'iris_trai', 'iris_phai', 'nose_tip', 'nose_v2', 'nose_v4', 'mouth_trai', 'mouth_phai']


def v2_config():
    """Cấu hình tối thiểu của định nghĩa 50 điểm CŨ (version 2): chỉ các điểm check_drivface cần; side R = nửa trái ảnh."""
    pts = [dict(name=n, line=ln, mp_idx=i) for i, (n, ln) in enumerate(
        [(f'p{k}_eye_R', 'eye_R') for k in (33, 34, 35, 36)] + [(f'p{k}_eye_L', 'eye_L') for k in (37, 38, 39, 40)]
        + [('p29_nose_M', 'nose_bridge'), ('p31_nose_M', 'nose_base'), ('p41_lip_R', 'lip_outer'), ('p45_lip_L', 'lip_outer')])]
    return dict(version=2, points=pts)


def test_old_v2_definition_still_computable_to_compare_with_v3():
    v2 = v2_config()
    p50 = {p['name']: [float(i), float(2 * i)] for i, p in enumerate(v2['points'])}
    five = cd.ours_five(p50, v2)
    assert np.allclose(five['eye_trai'], np.mean([p50[f'p{k}_eye_R'] for k in (33, 34, 35, 36)], axis=0))      # 4 điểm mắt, R = nửa trái ảnh
    assert np.allclose(five['nose_tip'], p50['p29_nose_M']) and np.allclose(five['mouth_trai'], p50['p41_lip_R']) and np.allclose(five['mouth_phai'], p50['p45_lip_L'])
    assert 'nose_v2' not in five                                                              # chân mũi của v2 (p31) nay là đỉnh 2 lấy từ 478 điểm, giống bản mới
    five478 = cd.ours_five(p50, v2, np.arange(956.0).reshape(478, 2))
    assert np.allclose(five478['nose_v2'], [4.0, 5.0]) and np.allclose(five478['iris_trai'], [936.0, 937.0])


def test_image_side_ref_matches_by_position_in_the_image_not_by_letter():
    pts = {'RE': (323, 100), 'LE': (367, 100), 'N': (345, 130), 'RM': (333, 160), 'LM': (357, 160)}
    left = cd.image_side_ref(pts, re_left=True)                                              # RE ở nửa trái ảnh: EL = RE
    assert left == {'EL': (323, 100), 'ER': (367, 100), 'N': (345, 130), 'ML': (333, 160), 'MR': (357, 160)}
    swapped = cd.image_side_ref(dict(pts, RE=(367, 100), LE=(323, 100), RM=(357, 160), LM=(333, 160)), re_left=False)     # RE nằm nửa phải ảnh
    assert swapped == left                                                                    # cùng kết quả: bên của ảnh không phụ thuộc chữ R/L


def test_point_errors_hand_checked_with_drivface_iod():
    ref = cd.image_side_ref({'RE': (100, 100), 'LE': (200, 100), 'N': (150, 140), 'RM': (110, 180), 'LM': (190, 180)})      # IOD DrivFace = 100
    ours = {'eye_trai': np.array([103, 104]), 'eye_phai': np.array([200, 100]), 'iris_trai': np.array([100, 110]), 'iris_phai': np.array([200, 100]),
            'nose_tip': np.array([150, 140]), 'nose_v2': np.array([150, 160]), 'nose_v4': np.array([150, 150]), 'mouth_trai': np.array([110, 180]), 'mouth_phai': np.array([190, 190])}
    err = cd.point_errors(ours, ref)
    assert err['eye_trai'] == pytest.approx(5.0) and err['eye_phai'] == 0 and err['iris_trai'] == pytest.approx(10.0)
    assert err['nose_tip'] == 0 and err['nose_v2'] == pytest.approx(20.0) and err['nose_v4'] == pytest.approx(10.0) and err['mouth_trai'] == 0 and err['mouth_phai'] == pytest.approx(10.0)
    off = cd.point_offsets(ours, ref)
    assert off['eye_trai'] == pytest.approx((3.0, 4.0)) and off['nose_v2'] == pytest.approx((0.0, 20.0))        # có dấu: x sang phải, y xuống
    assert cd.point_errors(ours, dict(ref, ER=(100, 100))) is None                                               # hai tâm mắt trùng: không chuẩn hoá được


def test_stats_and_group_tables():
    s = cd.stats([1, 2, 3, 4, 100])
    assert s['median'] == 3 and s['mean'] == pytest.approx(22.0) and s['n'] == 5 and s['p90'] == pytest.approx(np.percentile([1, 2, 3, 4, 100], 90))
    assert cd.stats([]) == {'n': 0}
    per = [dict(label=1, subject=1, err={'eye_trai': 2.0}), dict(label=2, subject=1, err={'eye_trai': 4.0}), dict(label=2, subject=2, err={'eye_trai': 6.0})]
    by_label = cd.group_table(per, 'label', ['eye_trai'])
    assert by_label[1]['eye_trai']['median'] == 2.0 and by_label[2]['eye_trai']['median'] == 5.0 and by_label[2]['eye_trai']['n'] == 2
    assert cd.group_table(per, 'subject', ['eye_trai'])[1]['eye_trai']['n'] == 2
    lines = []
    cd.format_table('T', cd.summarize(per, ['eye_trai']), None, ['eye_trai'], out=lines.append)
    assert lines[0] == 'T' and 'eye_trai' in lines[2] and '4.0' in lines[2]


class FakeLandmarker:
    closed = False

    def close(self):
        FakeLandmarker.closed = True


def test_process_maps_back_to_frame_coordinates_and_reports_missing(tmp_path, monkeypatch):
    """Landmarker giả trả 478 điểm trong ảnh cắt; kiểm toạ độ đổi về khung (x / k + left) và sai số đúng bằng số tính tay."""
    root = tmp_path / 'df'
    img_dir = root / 'imgs' / 'DrivImages'
    img_dir.mkdir(parents=True)
    cv2.imwrite(str(img_dir / 'a_001 .jpg'), np.full((480, 640, 3), 120, np.uint8))
    box = (200.0, 100.0, 300.0, 230.0)
    _, _, (left, top, k), _ = square_crop(np.zeros((480, 640, 3), np.uint8), box, np.zeros((1, 2), np.float32))
    idx = {p['name']: p['mp_idx'] for p in CFG['points']}
    pts = np.full((478, 2), 256.0)
    for n, v in pts50_from_tmpl().items():
        pts[idx[n]] = v                                                                   # 50 điểm = khuôn tmpl trong ảnh cắt
    pts[468] = np.mean([pts[idx[n]] for n in EYE_L], axis=0)                               # iris = tâm 8 điểm mắt
    pts[473] = np.mean([pts[idx[n]] for n in EYE_R], axis=0)
    to_frame = lambda v: np.asarray(v) / k + [left, top]                                  # noqa: E731
    five_crop = cd.ours_five(pts50_from_tmpl(), CFG, pts)
    ref = {'RE': tuple(to_frame(five_crop['eye_trai'])), 'LE': tuple(to_frame(five_crop['eye_phai'])), 'N': tuple(to_frame(five_crop['nose_tip'])),
           'RM': tuple(to_frame(five_crop['mouth_trai'])), 'LM': tuple(to_frame(five_crop['mouth_phai']))}      # RE/RM nằm nửa trái ảnh (như DrivFace thật)
    rows = [dict(name='a_001 ', subject=1, label=2, ang=0, box=(0, 0, 1, 1), pts=ref),
            dict(name='ko_co_anh ', subject=1, label=2, ang=0, box=(0, 0, 1, 1), pts=ref),
            dict(name='a_001 ', subject=2, label=1, ang=0, box=(0, 0, 1, 1), pts=ref)]
    monkeypatch.setattr(steps, 'make_landmarker', lambda model: FakeLandmarker())
    monkeypatch.setattr(steps, 'detect_box', lambda lm, rgb, run=None: box)
    monkeypatch.setattr(steps, 'run_mp_padded', lambda lm, rgb, run=None: pts.tolist())
    new, old, no_face, no_img = cd.process(rows, str(img_dir), 'm.task', CFG, MAP)
    assert old is None and no_face == [] and no_img == ['ko_co_anh '] and len(new) == 2 and FakeLandmarker.closed
    e = new[0]['err']
    for n in ('eye_trai', 'eye_phai', 'iris_trai', 'iris_phai', 'nose_tip', 'mouth_trai', 'mouth_phai'):
        assert e[n] == pytest.approx(0.0, abs=1e-6), n                                      # đúng toạ độ khung: x / k + left, y / k + top
    iod_frame = np.hypot(*(np.array(ref['RE']) - np.array(ref['LE'])))
    tip = np.array(pts50_from_tmpl()['songmui_4'])
    assert e['nose_v2'] == pytest.approx(np.linalg.norm(pts[2] - tip) / k / iod_frame * 100)      # đỉnh 2 (chân mũi, ngoài 50 điểm) cách chóp một đoạn: lỗi so với mũi DrivFace
    assert e['nose_v4'] == pytest.approx(np.linalg.norm(pts[4] - tip) / k / iod_frame * 100)
    assert new[1]['label'] == 1 and new[1]['subject'] == 2
    # RE/RM nằm nửa PHẢI ảnh (re_left=False): ghép theo vị trí trong ảnh, nên sai số vẫn 0 khi RE đổi sang bên phải
    ref_flipped = dict(ref, RE=ref['LE'], LE=ref['RE'], RM=ref['LM'], LM=ref['RM'])
    new_r, _, _, _ = cd.process([dict(rows[0], pts=ref_flipped)], str(img_dir), 'm.task', CFG, MAP, re_left=False)
    assert new_r[0]['err']['eye_trai'] == pytest.approx(0.0, abs=1e-6) and new_r[0]['err']['mouth_phai'] == pytest.approx(0.0, abs=1e-6)
    new_w, _, _, _ = cd.process([dict(rows[0], pts=ref_flipped)], str(img_dir), 'm.task', CFG, MAP, re_left=True)       # ghép theo chữ R/L sẽ sai lớn
    assert new_w[0]['err']['eye_trai'] > 50
    # so với định nghĩa cũ (version 2, bản chép config + map vertex): chạy được trên cùng 478 điểm, khác ở tâm mắt (4 điểm thay vì 8)
    v2 = v2_config()
    v2_map = dict(version=2, kind='vertex', points={})
    pick = {'p29_nose_M': 'songmui_4', 'p31_nose_M': 'songmui_3', 'p41_lip_R': 'moingoai_1', 'p45_lip_L': 'moingoai_7'}
    for q in v2['points']:
        q['mp_idx'] = idx[pick.get(q['name'], 'mattrai_1' if 'eye_R' in q['name'] else 'matphai_1')]
    new2, old2, _, _ = cd.process(rows[:1], str(img_dir), 'm.task', CFG, MAP, v2_map, v2)
    assert len(new2) == 1 and len(old2) == 1 and set(old2[0]['err']) == set(new2[0]['err']) and old2[0]['err']['nose_tip'] == pytest.approx(0.0, abs=1e-6)
    assert old2[0]['err']['eye_trai'] > new2[0]['err']['eye_trai']                           # v2 ở đây chỉ lấy một đỉnh làm "tâm mắt": lệch hơn trung bình 8 điểm
    # map không phải kind "vertex" (ví dụ bản ridge cũ có mean478) bị từ chối rõ ràng
    with pytest.raises(ValueError, match='không còn hỗ trợ'):
        cd.process(rows[:1], str(img_dir), 'm.task', CFG, MAP, dict(version=1, mean478=[[0, 0]] * 478), v2)


def test_process_counts_no_face(tmp_path, monkeypatch):
    img_dir = tmp_path / 'imgs'
    img_dir.mkdir()
    cv2.imwrite(str(img_dir / 'a .jpg'), np.zeros((50, 50, 3), np.uint8))
    rows = [dict(name='a ', subject=1, label=2, ang=0, box=(0, 0, 1, 1), pts={'RE': (1, 1), 'LE': (9, 1), 'N': (5, 5), 'RM': (3, 9), 'LM': (7, 9)})]
    monkeypatch.setattr(steps, 'make_landmarker', lambda model: FakeLandmarker())
    monkeypatch.setattr(steps, 'detect_box', lambda lm, rgb, run=None: None)
    new, old, no_face, no_img = cd.process(rows, str(img_dir), 'm.task', CFG, MAP)
    assert new == [] and no_face == ['a '] and no_img == []


CFG_ARGS = ['--config', os.path.join(CONFIG, 'm28_config.json'), '--map', os.path.join(CONFIG, 'map_mp50.json')]


def test_main_matches_sides_by_image_position_and_stops_when_inconclusive_or_folder_is_missing(tmp_path, capsys, monkeypatch):
    seen = {}

    def fake_process(*a, **k):
        seen.update(k)
        names = [n for n, _ in cd.COMPARE]
        return [dict(name='f1 ', label=2, subject=1, err={n: 1.0 for n in names}, off={n: (0.0, 0.0) for n in names})], None, [], []
    monkeypatch.setattr(cd, 'process', fake_process)
    # RE ở bên PHẢI ảnh (lạ so với DrivFace thật): vẫn chạy, nhưng đổi chiều ghép (re_left=False) và nói rõ
    right = write_drivface(tmp_path / 'df1', ['f1 ,1,1,2,0,0,0,10,10,367,100,323,100,345,130,377,160,313,160'] * 3)
    assert cd.main(['--drivface', str(right)] + CFG_ARGS) == 0
    out = capsys.readouterr().out
    assert 'VỊ TRÍ TRONG ẢNH' in out and 'nửa PHẢI ảnh' in out and 'ghép với nhóm *phai' in out and seen['re_left'] is False
    # bên lẫn lộn trong dữ liệu: dừng, mã 1
    mixed = write_drivface(tmp_path / 'df2', ['f1 ,1,1,2,0,0,0,10,10,323,100,367,100,345,130,333,160,357,160', 'f2 ,1,2,2,0,0,0,10,10,367,100,323,100,345,130,377,160,313,160'])
    with pytest.raises(SystemExit) as e:
        cd.main(['--drivface', str(mixed)] + CFG_ARGS)
    assert e.value.code == 1 and 'KHÔNG như dự kiến' in capsys.readouterr().out
    with pytest.raises(SystemExit, match='drivPoints.txt'):
        cd.main(['--drivface', str(tmp_path / 'khong_co')])


def test_main_rejects_old_config_and_incomplete_old_args(tmp_path):
    root = write_drivface(tmp_path / 'df3', ['f1 ,1,1,2,0,0,0,10,10,323,100,367,100,345,130,333,160,357,160'])
    v2 = dict(CFG)
    v2.pop('side_convention')
    (tmp_path / 'v2.json').write_text(json.dumps(v2), encoding='utf-8')
    with pytest.raises(SystemExit, match='side_convention'):
        cd.main(['--drivface', str(root), '--config', str(tmp_path / 'v2.json'), '--map', os.path.join(CONFIG, 'map_mp50.json')])
    with pytest.raises(SystemExit, match='--old-map'):
        cd.main(['--drivface', str(root)] + CFG_ARGS + ['--old-map', str(tmp_path / 'khong_co.json')])


def test_main_prints_tables_and_writes_csv(tmp_path, monkeypatch, capsys):
    root = write_drivface(tmp_path / 'df4', ['f1 ,1,1,2,0,0,0,10,10,323,100,367,100,345,130,333,160,357,160',
                                              'f2 ,2,2,1,-30,0,0,10,10,323,100,367,100,345,130,333,160,357,160'])
    names = [n for n, _ in cd.COMPARE]
    new = [dict(name='f1 ', label=2, subject=1, err={n: 4.0 for n in names}, off={n: (1.0, -1.0) for n in names}),
           dict(name='f2 ', label=1, subject=2, err={n: 6.0 for n in names}, off={n: (2.0, 0.0) for n in names})]
    old = [dict(name='f1 ', label=2, subject=1, err={n: 5.0 for n in names}, off={}),
           dict(name='f2 ', label=1, subject=2, err={n: 7.0 for n in names}, off={})]
    monkeypatch.setattr(cd, 'process', lambda *a, **k: (new, old, [], []))
    out = tmp_path / 'sub' / 'e.csv'
    assert cd.main(['--drivface', str(root), '--out', str(out)] + CFG_ARGS) == 0
    text = capsys.readouterr().out
    assert 'Chấm được 2 ảnh' in text and 'THEO ĐIỂM' in text and 'label 1 nhìn phải' in text and 'tài xế 2' in text and 'Chỉ để tham khảo' in text
    assert 'Lệch có dấu trung vị' in text and 'nửa TRÁI ảnh' in text and 'ghép với nhóm *trai' in text and 'eye_trai' in text
    import csv
    rows = list(csv.reader(open(out, encoding='utf-8')))
    assert rows[0][:3] == ['name', 'label', 'subject'] and rows[1][0] == 'f1' and float(rows[1][3]) == 4.0 and len(rows) == 3
