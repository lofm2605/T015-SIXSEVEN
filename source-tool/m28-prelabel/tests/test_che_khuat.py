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
