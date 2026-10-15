"""Điểm bị che do mặt nghiêng (m28core/che_khuat.py): occluded=1 trong file nháp, vị trí ước lượng giữ nguyên."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
from m28core import che_khuat, steps  # noqa: E402

CFG = json.load(open(os.path.join(HERE, '..', 'config', 'm28_config.json'), encoding='utf-8'))
NAMES = [p['name'] for p in CFG['points']]


def mesh(u, half=100.0):
    """Lưới 478 điểm giả: hai gò má cách nhau 2*half, mũi lệch u * half so với trung điểm."""
    p = np.zeros((478, 2))
    p[che_khuat.CHEEK_L] = [300.0 - half, 200.0]
    p[che_khuat.CHEEK_R] = [300.0 + half, 200.0]
    p[che_khuat.NOSE] = [300.0 + u * half, 220.0]
    return p.tolist()


def yaw_to_u(yaw):
    return che_khuat._A * yaw - che_khuat._B


def test_frontal_and_moderate_turn_have_no_occluded_points():
    assert che_khuat.diem_bi_che(mesh(0.0), CFG) == []
    assert che_khuat.diem_bi_che(mesh(yaw_to_u(40)), CFG) == []
    assert che_khuat.diem_bi_che(mesh(-yaw_to_u(59)), CFG) == []


def test_strong_turn_hides_brow_and_eye_of_the_far_side_only():
    for sign, far, near in ((-1, 'L', 'R'), (1, 'R', 'L')):                  # mũi lệch trái ảnh: nửa trái ảnh xa camera
        occ = che_khuat.diem_bi_che(mesh(sign * yaw_to_u(65)), CFG)
        by = {p['name']: p for p in CFG['points']}
        assert occ and all(by[n]['side'] == far and by[n]['region'] in ('brow', 'eye') for n in occ)
        assert len(occ) == 13                                                  # 5 lông mày + 8 mắt
        assert not any(by[n]['side'] == near for n in occ)


def test_profile_also_hides_far_lip_but_never_the_nose_or_the_axis():
    occ = che_khuat.diem_bi_che(mesh(-yaw_to_u(80)), CFG)
    by = {p['name']: p for p in CFG['points']}
    assert len(occ) == 13 + 8 and sum(by[n]['region'] == 'lip' for n in occ) == 8
    assert not any(by[n]['side'] == 'M' or by[n]['region'] == 'nose' for n in occ)
    assert occ == [n for n in NAMES if n in set(occ)]                          # theo thứ tự trong config


def test_bad_meshes_give_no_occlusion():
    assert che_khuat.diem_bi_che([[0, 0]] * 10, CFG) == []                    # thiếu điểm
    assert che_khuat.diem_bi_che(mesh(3.0, half=0.0), CFG) == []              # bề ngang bằng 0
    assert che_khuat.yaw_uoc_luong(mesh(0.0)) == (che_khuat._B / che_khuat._A)


def test_image_xml_writes_occluded_only_for_listed_points():
    names = ['longmaytrai_1', 'longmaytrai_2', 'matphai_1']
    pts = [(10.0, 20.0), (30.0, 40.0), (50.0, 60.0)]
    xml = steps.image_xml(0, 'F_001.png', names, pts, [False, True, False], 512, 512, occ=['longmaytrai_2', 'matphai_1'])
    assert 'label="longmaytrai_1" occluded="0"' in xml and 'label="longmaytrai_2" occluded="1"' in xml and 'label="matphai_1" occluded="1"' in xml
    assert 'points="30.00,40.00"' in xml and 'outside="1"' not in xml          # vẫn có toạ độ ước lượng, không dùng outside
    assert 'occluded="1"' not in steps.image_xml(0, 'F_001.png', names, pts, [False] * 3, 512, 512)


# ---------- vật thể che mắt (mặt nhìn thẳng) ----------
def mesh_eyes(cx_l=200.0, cx_r=400.0, cy=200.0, rx=40.0, ry=14.0):
    """Lưới 478 giả, mặt thẳng: hai mắt là hai hình elip quanh (cx_l, cy) và (cx_r, cy); gò má và mũi đặt cho u = 0."""
    p = np.zeros((478, 2))
    for idx, cx in ((che_khuat.MAT_TRAI, cx_l), (che_khuat.MAT_PHAI, cx_r)):
        for k, i in enumerate(idx):
            a = 2 * np.pi * k / len(idx)
            p[i] = [cx + rx * np.cos(a), cy + ry * np.sin(a)]
    p[che_khuat.CHEEK_L] = [100.0, 260.0]
    p[che_khuat.CHEEK_R] = [500.0, 260.0]
    p[che_khuat.NOSE] = [300.0, 300.0]
    return p


def stripes(flat=None):
    """Ảnh xám 512 x 512 có vạch dọc tương phản cao (mắt rõ, độ nét lớn); flat = [(x0, x1, giá trị)] phủ phẳng đè lên (vật che)."""
    g = np.tile(np.where((np.arange(512) // 3) % 2 == 0, 20, 235).astype(np.uint8), (512, 1))
    for x0, x1, v in flat or ():
        g[:, x0:x1] = v
    return g


def test_flat_patch_over_an_eye_marks_only_that_eye_occluded():
    p = mesh_eyes()
    assert che_khuat.mat_bi_che(stripes(), p) == set()                                       # mắt rõ cả hai bên
    assert che_khuat.mat_bi_che(stripes([(140, 260, 128)]), p) == {'L'}                       # vật phẳng che mắt nửa trái ảnh
    assert che_khuat.mat_bi_che(stripes([(340, 460, 128)]), p) == {'R'}
    occ = che_khuat.diem_bi_che(p, CFG, stripes([(140, 260, 128)]))
    by = {q['name']: q for q in CFG['points']}
    assert len(occ) == 8 and all(by[n]['region'] == 'eye' and by[n]['side'] == 'L' for n in occ)    # chỉ 8 điểm mắt bên đó, không lông mày, không môi
    assert che_khuat.diem_bi_che(p, CFG) == [] and che_khuat.diem_bi_che(p, CFG, stripes()) == []  # không có ảnh hoặc mắt rõ: không đánh dấu


def test_thresholds_of_the_eye_rule(monkeypatch):
    def fake(values):
        monkeypatch.setattr(che_khuat, 'do_vung_mat', lambda gray, pts: values)
        return che_khuat.mat_bi_che(object(), None)
    G, S, L = che_khuat.GM_PHANG, che_khuat.SANG_KINH, che_khuat.LUM_KINH
    assert fake({'L': (G - 0.1, 0.6, 0.9), 'R': (G + 0.1, 0.6, 0.9)}) == {'L'}                                  # gần như phẳng: bị che
    assert fake({'L': (9.0, L - 0.01, S - 0.01), 'R': (25.0, 0.7, 1.0)}) == {'L'}                                # tròng kính đen một bên, mắt kia sáng (kính phản chiếu): chỉ một
    assert fake({'L': (9.0, L - 0.01, S - 0.01), 'R': (25.0, che_khuat.LUM_KINH_CAP - 0.01, 0.7)}) == {'L', 'R'}   # kính đen: mắt kia đủ tối cũng bị che
    assert fake({'L': (9.0, L + 0.01, S - 0.01), 'R': (9.0, L - 0.01, S + 0.01)}) == set()                       # chỉ tối HOẶC chỉ thiếu chỗ sáng: chưa đủ (ảnh 010)
    assert fake({'L': (6.2, 0.30, 0.56), 'R': (5.3, 0.31, 0.39)}) == set()                                       # số đo thật của ảnh 010 (mắt thật hơi mờ, tối): không báo nhầm
    assert fake({'L': (28.0, 0.7, 1.0), 'R': (30.0, 0.8, 1.1)}) == set()                                         # mắt bình thường


def test_eye_rule_survives_bad_inputs():
    p = mesh_eyes()
    assert che_khuat.do_vung_mat(None, p) == {} and che_khuat.do_vung_mat(np.zeros((512, 512, 3), np.uint8), p) == {}    # không phải ảnh xám
    assert che_khuat.do_vung_mat(stripes(), [[0, 0]] * 10) == {}                                                          # lưới thiếu điểm
    assert che_khuat.do_vung_mat(stripes(), mesh_eyes(cx_l=900.0, cx_r=1300.0)) == {}                                      # mắt nằm ngoài ảnh


# ---------- hiện occluded trong tool (ảnh chồng, khung thông tin, chú giải) ----------
def test_overlay_draws_occluded_points_as_hollow_rings():
    import cv2
    from m28core import mau_nhom
    img = np.full((60, 60, 3), 128, np.uint8)
    solid, hollow = img.copy(), img.copy()
    rgb = mau_nhom.hex_rgb(mau_nhom.GROUP_COLOR['mattrai'])
    steps._draw_dot(cv2, solid, 30, 30, rgb, False, False)
    steps._draw_dot(cv2, hollow, 30, 30, rgb, False, True)
    bgr = (rgb[2], rgb[1], rgb[0])
    assert tuple(solid[30, 30]) == bgr                                                       # điểm thường: chấm đặc, tâm có màu nhóm
    assert tuple(hollow[30, 30]) == (128, 128, 128) and tuple(hollow[30, 30 + mau_nhom.R_OCC]) != (128, 128, 128)   # điểm bị che: tâm rỗng (giữ nền), có vòng quanh
    both = img.copy()
    steps._draw_dot(cv2, both, 30, 30, rgb, True, True)                                       # vừa low_conf vừa occluded: vẫn rỗng, thêm vòng trắng mảnh ngoài
    assert tuple(both[30, 30]) == (128, 128, 128) and (both[30, 30 + mau_nhom.R_OCC + 3:30 + mau_nhom.R_OCC + 6] > 160).all(axis=1).any()      # vòng trắng mảnh (khử răng cưa nên không đúng 255)


def test_review_page_reads_occ_and_shows_it_in_info_and_legend(tmp_path):
    import review_app as ra
    sys.path.insert(0, HERE)
    from test_review_app import make_run
    rd = make_run(tmp_path, {'F_001': 0, 'F_002': 0}, crops=['F_001', 'F_002'], overlays=['F_001', 'F_002'])
    names = [p['name'] for p in CFG['points']]
    os.makedirs(os.path.join(rd, 'map50'))
    mp = {n: dict(orig={k: [1.0, 2.0] for k in names}, flip=None, occ=(names[5:8] if n == 'F_001' else [])) for n in ('F_001', 'F_002')}
    json.dump(mp, open(os.path.join(rd, 'map50', 'mp50.json'), 'w'))
    faces, _notes = ra._load(rd)
    by = {f.name: f for f in faces}
    assert by['F_001'].n_occ == 3 and by['F_001'].occ[5:8] == [True] * 3 and len(by['F_001'].occ) == 50 and by['F_002'].n_occ == 0 and by['F_002'].occ == [False] * 50
    store = ra.Store(rd, 'P1')
    html1 = ra.info_html(store, by['F_001'], '', '')
    html2 = ra.info_html(store, by['F_002'], '', '')
    assert 'Điểm bị che (occluded)' in html1 and '<b>3/50</b>' in html1 and '6–8' in html1 and 'vòng rỗng' in html1
    assert '<b>0/50</b>' in html2 and 'không có điểm nào' in html2.split('Điểm bị che (occluded)')[1].split('</tr>')[0]
    assert 'vòng rỗng = occluded' in ra.LEGEND_HTML and 'dot hollow' in ra.LEGEND_HTML
    os.remove(os.path.join(rd, 'map50', 'mp50.json'))                                         # lượt cũ, chưa có thông tin occ: không hiện gì thêm, không vỡ
    faces, _n = ra._load(rd)
    assert all(f.occ is None for f in faces) and 'Điểm bị che' not in ra.info_html(ra.Store(rd, 'P1'), faces[0], '', '')
