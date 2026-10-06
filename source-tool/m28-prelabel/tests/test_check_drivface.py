"""Thử tool/check_drivface.py bằng dữ liệu GIẢ: file drivPoints giả (CRLF, tên có dấu cách cuối), ảnh xám, landmarker giả. Không ảnh người thật."""
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


def test_ours_five_means_of_eye_points_and_named_vertices():
    p50 = pts50_from_tmpl()
    p478 = np.zeros((478, 2))
    p478[468], p478[473] = [1, 2], [3, 4]
    five = cd.ours_five(p50, CFG, p478)
    eye_r = np.mean([p50[n] for n in ('p33_eye_R', 'p34_eye_R', 'p35_eye_R', 'p36_eye_R')], axis=0)
    eye_l = np.mean([p50[n] for n in ('p37_eye_L', 'p38_eye_L', 'p39_eye_L', 'p40_eye_L')], axis=0)
    assert np.allclose(five['eye_R'], eye_r) and np.allclose(five['eye_L'], eye_l)
    assert np.allclose(five['nose_tip_p29'], p50['p29_nose_M']) and np.allclose(five['nose_base_p31'], p50['p31_nose_M'])
    assert np.allclose(five['mouth_R'], p50['p41_lip_R']) and np.allclose(five['mouth_L'], p50['p45_lip_L'])
    assert np.allclose(five['iris_R'], [1, 2]) and np.allclose(five['iris_L'], [3, 4]) and 'iris_R' not in cd.ours_five(p50, CFG)


def test_point_errors_hand_checked_with_drivface_iod():
    ref = {'RE': (100, 100), 'LE': (200, 100), 'N': (150, 140), 'RM': (110, 180), 'LM': (190, 180)}      # IOD DrivFace = 100
    ours = {'eye_R': np.array([103, 104]), 'eye_L': np.array([200, 100]), 'iris_R': np.array([100, 110]), 'iris_L': np.array([200, 100]),
            'nose_tip_p29': np.array([150, 140]), 'nose_base_p31': np.array([150, 160]), 'mouth_R': np.array([110, 180]), 'mouth_L': np.array([190, 190])}
    err = cd.point_errors(ours, ref)
    assert err['eye_R'] == pytest.approx(5.0) and err['eye_L'] == 0 and err['iris_R'] == pytest.approx(10.0)
    assert err['nose_tip_p29'] == 0 and err['nose_base_p31'] == pytest.approx(20.0) and err['mouth_R'] == 0 and err['mouth_L'] == pytest.approx(10.0)
    off = cd.point_offsets(ours, ref)
    assert off['eye_R'] == pytest.approx((3.0, 4.0)) and off['nose_base_p31'] == pytest.approx((0.0, 20.0))        # có dấu: x sang phải, y xuống
    assert cd.point_errors(ours, dict(ref, LE=(100, 100))) is None                                               # hai tâm mắt trùng: không chuẩn hoá được


def test_stats_and_group_tables():
    s = cd.stats([1, 2, 3, 4, 100])
    assert s['median'] == 3 and s['mean'] == pytest.approx(22.0) and s['n'] == 5 and s['p90'] == pytest.approx(np.percentile([1, 2, 3, 4, 100], 90))
    assert cd.stats([]) == {'n': 0}
    per = [dict(label=1, subject=1, err={'eye_R': 2.0}), dict(label=2, subject=1, err={'eye_R': 4.0}), dict(label=2, subject=2, err={'eye_R': 6.0})]
    by_label = cd.group_table(per, 'label', ['eye_R'])
    assert by_label[1]['eye_R']['median'] == 2.0 and by_label[2]['eye_R']['median'] == 5.0 and by_label[2]['eye_R']['n'] == 2
    assert cd.group_table(per, 'subject', ['eye_R'])[1]['eye_R']['n'] == 2
    lines = []
    cd.format_table('T', cd.summarize(per, ['eye_R']), None, ['eye_R'], out=lines.append)
    assert lines[0] == 'T' and 'eye_R' in lines[2] and '4.0' in lines[2]


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
    pts[468] = np.mean([pts[idx[n]] for n in ('p33_eye_R', 'p34_eye_R', 'p35_eye_R', 'p36_eye_R')], axis=0)
    pts[473] = np.mean([pts[idx[n]] for n in ('p37_eye_L', 'p38_eye_L', 'p39_eye_L', 'p40_eye_L')], axis=0)
    to_frame = lambda v: np.asarray(v) / k + [left, top]                                  # noqa: E731
    five_crop = cd.ours_five(pts50_from_tmpl(), CFG, pts)
    ref = {'RE': tuple(to_frame(five_crop['eye_R'])), 'LE': tuple(to_frame(five_crop['eye_L'])), 'N': tuple(to_frame(five_crop['nose_tip_p29'])),
           'RM': tuple(to_frame(five_crop['mouth_R'])), 'LM': tuple(to_frame(five_crop['mouth_L']))}
    rows = [dict(name='a_001 ', subject=1, label=2, ang=0, box=(0, 0, 1, 1), pts=ref),
            dict(name='ko_co_anh ', subject=1, label=2, ang=0, box=(0, 0, 1, 1), pts=ref),
            dict(name='a_001 ', subject=2, label=1, ang=0, box=(0, 0, 1, 1), pts=ref)]
    monkeypatch.setattr(steps, 'make_landmarker', lambda model: FakeLandmarker())
    monkeypatch.setattr(steps, 'detect_box', lambda lm, rgb, run=None: box)
    monkeypatch.setattr(steps, 'run_mp_padded', lambda lm, rgb, run=None: pts.tolist())
    new, old, no_face, no_img = cd.process(rows, str(img_dir), 'm.task', CFG, MAP)
    assert old is None and no_face == [] and no_img == ['ko_co_anh '] and len(new) == 2 and FakeLandmarker.closed
    e = new[0]['err']
    for n in ('eye_R', 'eye_L', 'iris_R', 'iris_L', 'nose_tip_p29', 'mouth_R', 'mouth_L'):
        assert e[n] == pytest.approx(0.0, abs=1e-6), n                                      # đúng toạ độ khung: x / k + left, y / k + top
    iod_frame = np.hypot(*(np.array(ref['RE']) - np.array(ref['LE'])))
    p31 = np.array(pts50_from_tmpl()['p31_nose_M'])
    p29 = np.array(pts50_from_tmpl()['p29_nose_M'])
    assert e['nose_base_p31'] == pytest.approx(np.linalg.norm(p31 - p29) / k / iod_frame * 100)       # p31 cách p29 một đoạn: lỗi chân giữa so với mũi DrivFace
    assert new[1]['label'] == 1 and new[1]['subject'] == 2
    # thêm ánh xạ cũ: ridge WFLW chạy được trên cùng 478 điểm
    old_map = json.load(open(os.path.join(HERE, '..', 'tool', 'legacy_wflw', 'map_mp50_wflw.json'), encoding='utf-8'))
    old_cfg = json.load(open(os.path.join(HERE, '..', 'tool', 'legacy_wflw', 'm28_config_wflw.json'), encoding='utf-8'))
    pts[:] = np.array(old_map['mean478']) + np.random.default_rng(0).normal(scale=0.5, size=(478, 2))      # hình gần trung bình để ridge cho số hợp lý
    new2, old2, _, _ = cd.process(rows[:1], str(img_dir), 'm.task', CFG, MAP, old_map, old_cfg)
    assert len(new2) == 1 and old2 is not None and len(old2) == 1 and set(old2[0]['err']) >= {'eye_R', 'eye_L', 'nose_tip_p29', 'mouth_R', 'mouth_L'}


def test_process_counts_no_face(tmp_path, monkeypatch):
    img_dir = tmp_path / 'imgs'
    img_dir.mkdir()
    cv2.imwrite(str(img_dir / 'a .jpg'), np.zeros((50, 50, 3), np.uint8))
    rows = [dict(name='a ', subject=1, label=2, ang=0, box=(0, 0, 1, 1), pts={'RE': (1, 1), 'LE': (9, 1), 'N': (5, 5), 'RM': (3, 9), 'LM': (7, 9)})]
    monkeypatch.setattr(steps, 'make_landmarker', lambda model: FakeLandmarker())
    monkeypatch.setattr(steps, 'detect_box', lambda lm, rgb, run=None: None)
    new, old, no_face, no_img = cd.process(rows, str(img_dir), 'm.task', CFG, MAP)
    assert new == [] and no_face == ['a '] and no_img == []


def test_main_stops_when_side_convention_differs_or_folder_is_missing(tmp_path, capsys):
    root = write_drivface(tmp_path / 'df1', ['f1 ,1,1,2,0,0,0,10,10,367,100,323,100,345,130,377,160,313,160'] * 3)       # RE ở bên phải ảnh: lạ
    with pytest.raises(SystemExit) as e:
        cd.main(['--drivface', str(root), '--config', os.path.join(CONFIG, 'm28_config.json'), '--map', os.path.join(CONFIG, 'map_mp50.json')])
    assert e.value.code == 1 and 'KHÔNG như dự kiến' in capsys.readouterr().out
    with pytest.raises(SystemExit, match='drivPoints.txt'):
        cd.main(['--drivface', str(tmp_path / 'khong_co')])


def test_main_prints_tables_and_writes_csv(tmp_path, monkeypatch, capsys):
    root = write_drivface(tmp_path / 'df2', ['f1 ,1,1,2,0,0,0,10,10,323,100,367,100,345,130,333,160,357,160',
                                              'f2 ,2,2,1,-30,0,0,10,10,323,100,367,100,345,130,333,160,357,160'])
    names = [n for n, _ in cd.COMPARE]
    new = [dict(name='f1 ', label=2, subject=1, err={n: 4.0 for n in names}, off={n: (1.0, -1.0) for n in names}),
           dict(name='f2 ', label=1, subject=2, err={n: 6.0 for n in names}, off={n: (2.0, 0.0) for n in names})]
    old = [dict(name='f1 ', label=2, subject=1, err={n: 5.0 for n in names if n not in cd.OLD_ONLY_SKIP}, off={}),
           dict(name='f2 ', label=1, subject=2, err={n: 7.0 for n in names if n not in cd.OLD_ONLY_SKIP}, off={})]
    monkeypatch.setattr(cd, 'process', lambda *a, **k: (new, old, [], []))
    out = tmp_path / 'sub' / 'e.csv'
    assert cd.main(['--drivface', str(root), '--config', os.path.join(CONFIG, 'm28_config.json'), '--map', os.path.join(CONFIG, 'map_mp50.json'),
                    '--out', str(out)]) == 0
    text = capsys.readouterr().out
    assert 'Chấm được 2 ảnh' in text and 'THEO ĐIỂM' in text and 'label 1 nhìn phải' in text and 'tài xế 2' in text and 'Chỉ để tham khảo' in text
    assert 'Lệch có dấu trung vị' in text
    import csv
    rows = list(csv.reader(open(out, encoding='utf-8')))
    assert rows[0][:3] == ['name', 'label', 'subject'] and rows[1][0] == 'f1' and float(rows[1][3]) == 4.0 and len(rows) == 3
