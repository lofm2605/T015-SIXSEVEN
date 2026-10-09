"""Thử tool/tao_bo200.py (bộ 200 ảnh chung cho hai nhóm MANUAL / ASSISTED) bằng dữ liệu GIẢ.

Không cần MediaPipe, video hay ảnh mặt thật: bảng đo giả (hàng giống cache/bang_do.csv), ảnh nhiễu 512 x 512, bộ dò giả.
"""
import csv
import hashlib
import json
import os
import random
import re
import sys
import zipfile
from collections import Counter
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tool'))
import tao_bo200 as tb  # noqa: E402
from m28core import steps  # noqa: E402
from m28core.cat_mat import crop_geometry, square_crop  # noqa: E402

PROJECT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


# ---------- dữ liệu giả ----------
def _tag_rich(rng):
    """Số đo ngẫu nhiên trải đủ các mức khó và mọi thẻ hiếm (đa số ảnh sạch, một phần có 1-3 yếu tố gây khó)."""
    row = dict(yaw=rng.gauss(0, 5), pitch=rng.gauss(0, 4), roll=rng.gauss(0, 4), jaw_crop=0.01, blink_l=0.05, blink_r=0.05, luma=rng.uniform(95, 140),
               contrast=rng.uniform(35, 55), bright_frac=0.0, lap_var=rng.uniform(250, 500), canh_mat_px=rng.uniform(150, 240), pad_frac=0.0,
               flip_nme=rng.choice([1.0, 1.5, 2.0, 3.0, 9.0]))
    mods = [lambda: row.update(yaw=rng.uniform(22, 30)), lambda: row.update(yaw=rng.uniform(33, 38)), lambda: row.update(yaw=rng.choice([-1, 1]) * rng.uniform(41, 52)),
            lambda: row.update(pitch=rng.uniform(16, 19)), lambda: row.update(pitch=rng.choice([-1, 1]) * rng.uniform(21, 28)), lambda: row.update(roll=17.0),
            lambda: row.update(jaw_crop=0.2), lambda: row.update(jaw_crop=0.7), lambda: row.update(blink_l=0.8, blink_r=0.8), lambda: row.update(blink_l=0.4, blink_r=0.5),
            lambda: row.update(luma=55.0), lambda: row.update(luma=185.0), lambda: row.update(contrast=20.0), lambda: row.update(lap_var=120.0),
            lambda: row.update(canh_mat_px=115.0), lambda: row.update(pad_frac=0.08)]
    for _ in range(rng.choice([0, 0, 0, 1, 1, 1, 2, 2, 3])):
        rng.choice(mods)()
    return row


def fake_rows(n_subj=60, per=14, seed=0):
    """Bảng đo giả: n_subj tài xế (nữ/nam xen kẽ, kính khác nhau), mỗi tài xế per ứng viên trong 2 video cách nhau 3 s; 4 tài xế DrivFace; 10% trùng 616."""
    rng = random.Random(seed)
    rows = []
    for s in range(n_subj):
        drv = s >= n_subj - 4
        subj = f'df_{s - (n_subj - 4) + 1:02d}' if drv else f'yd_{"F" if s % 2 else "M"}{s:03d}'
        glasses = 'unknown' if drv else ['none', 'none', 'none', 'glasses', 'none', 'none', 'glasses', 'sunglasses'][s % 8]
        cam = 'drivface' if drv else ('dash' if s % 6 == 0 else 'mirror')
        for k in range(per):
            vid = f'v{s}_{k % 2}.avi'
            row = _tag_rich(rng)
            name = f'{subj}_{k:03d}'
            row.update(name=name, moi=0, source='drivface' if drv else 'yawdd', camera=cam, subject=subj, gender='unknown' if drv else ('F' if s % 2 else 'M'),
                       glasses=glasses, state='normal', video=f'{name}.jpg' if drv else vid, frame=k * 100 if not drv else k * 5, t_s=None if drv else float(k // 2 * 3),
                       face_idx=0, x0=100.0, y0=100.0, x1=300.0, y1=320.0, left=50.0, top=50.0, k=1.5, jaw_open=0.0, gaze_label=None, gaze_ang=None, w=640, h=480,
                       hash=rng.getrandbits(64), trung_goi616=f'X1_{len(rows) % 50 + 1:02d}.png' if rng.random() < 0.1 else '', mp_ok=1, mp_flip_ok=1,
                       df_err=None, hand_n=0, hand_cov=0.0, box_iou=0.95)
            rows.append(row)
    return rows


def with_bad_drafts(rows, n=12):
    """Thêm ghi nhận 'nháp tệ' (đã xác nhận bằng mắt) cho n ứng viên có yaw lớn nhất: trả sua_the dạng dict (như doc_sua_the)."""
    strong = sorted((r for r in rows if abs(r['yaw']) > 40), key=lambda r: -abs(r['yaw']))[:n]
    sua = {r['name']: dict(them={'nhap_te'}, bo=set(), loai=False, ghi_chu=['nháp sai rõ'], loai_ro=False) for r in strong}
    for r in [r for r in rows if r['name'] not in sua and r['subject'].startswith('yd_')][::37][:14]:       # tay che (gán bằng mắt)
        sua[r['name']] = dict(them={'che_tay'}, bo=set(), loai=False, ghi_chu=['tay che miệng'], loai_ro=False)
    return sua


@pytest.fixture(scope='module')
def tagged():
    rows = fake_rows()
    sua = with_bad_drafts(rows)
    tb.gan_the(rows, sua)
    return rows


@pytest.fixture(scope='module')
def selected(tagged):
    return tb.chon(tagged, seed=3, n_good=2, max_tries=60)


# ---------- thẻ và mức ----------
@pytest.mark.parametrize('field,value,expect,absent', [
    ('yaw', 25.0, 'yaw_vua', 'yaw_lon'), ('yaw', 35.0, 'yaw_lon', 'yaw_vua'), ('yaw', 45.0, 'yaw_manh_phai', 'yaw_manh_trai'), ('yaw', -45.0, 'yaw_manh_trai', 'yaw_manh_phai'),
    ('yaw', 19.9, None, 'yaw_vua'), ('pitch', 16.0, 'pitch_vua', 'pitch_len'), ('pitch', 22.0, 'pitch_xuong', 'pitch_len'), ('pitch', -22.0, 'pitch_len', 'pitch_xuong'),
    ('roll', 16.0, 'nghieng_dau', None), ('jaw_crop', 0.2, 'noi', 'ngap_rong'), ('jaw_crop', 0.55, 'ngap_rong', 'noi'), ('luma', 60.0, 'toi', 'sang_chay'),
    ('luma', 180.0, 'sang_chay', 'toi'), ('bright_frac', 0.09, 'sang_chay', None), ('contrast', 20.0, 'tuong_phan_thap', None), ('lap_var', 100.0, 'mo', None),
    ('canh_mat_px', 120.0, 'mat_nho', None), ('pad_frac', 0.07, 'sat_mep', None), ('glasses', 'glasses', 'kinh_can', 'kinh_ram'), ('glasses', 'sunglasses', 'kinh_ram', 'kinh_can'),
])
def test_the_tu_dong_theo_nguong(field, value, expect, absent):
    base = dict(yaw=0.0, pitch=0.0, roll=0.0, jaw_crop=0.0, luma=120.0, contrast=45.0, bright_frac=0.0, lap_var=400.0, canh_mat_px=200.0, pad_frac=0.0,
                glasses='none', source='yawdd', camera='mirror', video='a.avi')
    tags = tb.the_tu_dong(dict(base, **{field: value}))
    assert expect is None or expect in tags
    assert absent is None or absent not in tags


def test_mat_nham_lim_dim_va_ngoai_le():
    base = dict(yaw=0.0, glasses='none', source='yawdd', camera='mirror', video='a.avi')
    assert 'mat_nham' in tb.the_tu_dong(dict(base, blink_l=0.7, blink_r=0.8))
    assert 'lim_dim' in tb.the_tu_dong(dict(base, blink_l=0.4, blink_r=0.5))
    assert 'lim_dim' not in tb.the_tu_dong(dict(base, blink_l=0.9, blink_r=0.1))            # cần CẢ HAI mắt
    assert not {'mat_nham', 'lim_dim'} & set(tb.the_tu_dong(dict(base, glasses='sunglasses', blink_l=0.9, blink_r=0.9)))   # kính râm: bỏ thẻ mắt
    assert not {'mat_nham', 'lim_dim'} & set(tb.the_tu_dong(dict(base, yaw=50.0, blink_l=0.9, blink_r=0.9)))                # mặt nghiêng: blendshape không tin được


def test_rau_theo_ten_video():
    assert 'rau' in tb.the_tu_dong(dict(source='yawdd', video='Mirror/Male_mirror/3-MaleGlassesBeard-Normal.avi'))
    assert 'rau' in tb.the_tu_dong(dict(source='yawdd', video='Mirror/Male_mirror/3-MaleNoGlassesmoustache-Yawning.avi'))
    assert 'rau' not in tb.the_tu_dong(dict(source='yawdd', video='Mirror/Male_mirror/3-MaleNoGlasses-Yawning.avi'))


def test_muc_theo_quy_tac():
    assert tb.tinh_muc([]) == 'de'
    assert tb.tinh_muc(['noi']) == 'de'                                  # S = 0,5
    assert tb.tinh_muc(['yaw_vua']) == 'vua'
    assert tb.tinh_muc(['yaw_vua', 'kinh_can', 'noi']) == 'vua'          # S = 2,5
    assert tb.tinh_muc(['yaw_lon', 'kinh_can']) == 'kho'                 # S = 3
    assert tb.tinh_muc(['pitch_len', 'mo', 'kinh_can']) == 'kho'         # S = 4,5
    assert tb.tinh_muc(['yaw_manh_phai', 'pitch_len']) == 'rat_kho'      # S = 5
    assert tb.tinh_muc(['che_tay', 'che_tay_mat']) == 'rat_kho'          # tay che mắt
    assert tb.tinh_muc(['yaw_manh_phai'], yaw=46.0) == 'rat_kho'         # |yaw| >= 45
    assert tb.tinh_muc(['yaw_manh_phai'], yaw=42.0) == 'kho'
    assert tb.tinh_muc(['kinh_ram', 'toi']) == 'rat_kho'                 # kính râm + yếu tố >= 1,5
    assert tb.tinh_muc(['kinh_ram', 'noi']) == 'kho'
    assert tb.tinh_muc(['mat_nham']) == 'vua'                            # thẻ hiếm không bao giờ ở mức dễ


# ---------- sửa thẻ ----------
def test_sua_the_them_bo_loai_va_tai_xe(tmp_path):
    path = tmp_path / 'sua.csv'
    path.write_text('# ghi chú\nung_vien,the_them,the_bo,quyet_dinh,ghi_chu\n'
                    'subject:yd_F001,kinh_can,,,kính thuốc cả bộ\n'
                    'a1,che_tay;che_tay_mat,yaw_vua,,tay che mắt\n'
                    'a2,,,loai,hai người trong khung\n'
                    'a3,,kinh_can,,không có kính\n', encoding='utf-8')
    sua = tb.doc_sua_the(str(path))
    base = dict(yaw=25.0, pitch=0.0, roll=0.0, glasses='none', source='yawdd', camera='mirror', video='a.avi', mp_ok=1, moi=0, flip_nme=2.0)
    rows = [dict(base, name=n, subject='yd_F001') for n in ('a1', 'a2', 'a3', 'a4')]
    tb.gan_the(rows, sua)
    by = {r['name']: r for r in rows}
    assert 'che_tay' in by['a1']['the'] and 'che_tay_mat' in by['a1']['the'] and 'yaw_vua' not in by['a1']['the'] and by['a1']['muc'] == 'rat_kho'
    assert by['a2']['loai'] and not by['a1']['loai']
    assert 'kinh_can' not in by['a3']['the'] and 'kinh_can' in by['a4']['the']          # sửa theo ứng viên đè sửa theo tài xế
    assert by['a1']['the_sua'].startswith('+') and 'ghi' not in by['a4']['the_sua']


def test_sua_the_the_la_bi_tu_choi(tmp_path):
    path = tmp_path / 'sua.csv'
    path.write_text('ung_vien,the_them,the_bo,quyet_dinh,ghi_chu\nx,khong_co_the_nay,,,\n', encoding='utf-8')
    with pytest.raises(SystemExit):
        tb.doc_sua_the(str(path))


def test_nhap_tot_te_vua():
    base = dict(yaw=0.0, pitch=0.0, source='yawdd', camera='mirror', video='a.avi', subject='s', mp_ok=1, moi=0)
    rows = [dict(base, name='t', flip_nme=1.0), dict(base, name='v', flip_nme=8.0), dict(base, name='e', flip_nme=30.0)]
    tb.gan_the(rows, {'e': dict(them={'nhap_te'}, bo=set(), loai=False, ghi_chu=[], loai_ro=False)})
    assert [r['nhap'] for r in rows] == ['tot', 'vua', 'te']


# ---------- chọn ----------
def test_chon_dung_han_muc_va_luat_cung(selected, tagged):
    items = selected['items']
    assert len(items) == tb.N_ANH
    assert Counter(c['muc'] for c in items) == Counter(tb.QUOTA)
    per_subject = Counter(c['subject'] for c in items)
    assert max(per_subject.values()) <= tb.K_PER_SUBJECT
    per_video = Counter((c['source'], c['video']) for c in items if c['source'] == 'yawdd')
    assert max(per_video.values()) <= tb.MAX_PER_VIDEO
    for i, c in enumerate(items):
        for d in items[i + 1:]:
            assert tb.gap_ok(c, d), (c['name'], d['name'])
            assert tb.hash_ok(c, d), (c['name'], d['name'])
    assert len({c['name'] for c in items}) == tb.N_ANH
    cnt = Counter(t for c in items for t in c['the'])
    assert all(cnt[t] >= tb.MIN_THE for t in tb.THE_HIEM), {t: cnt[t] for t in tb.THE_HIEM}
    assert sum(1 for c in items if c['nhap'] == 'te') >= tb.MIN_NHAP_TE
    assert all(c['muc'] in ('kho', 'rat_kho') for c in items if c['nhap'] == 'te')
    assert sum(1 for c in items if not c['trung_goi616']) >= 0.8 * tb.N_ANH
    assert selected['seed_dung'] >= selected['seed_goc'] == 3


def test_chon_khong_lay_ung_vien_bi_loai_hoac_mp_khong_thay(tagged):
    rows = [dict(r) for r in tagged]
    for r in rows[::6]:
        r['loai'] = True
    for r in rows[3::9]:
        r['mp_ok'] = 0
    res = tb.chon(rows, seed=1, n_good=1, max_tries=60)
    bad = {r['name'] for r in rows[::6]} | {r['name'] for r in rows[3::9]}
    assert not bad & {c['name'] for c in res['items']}


def test_the_thieu_duoc_bao_dung(tagged):
    rows = [dict(r) for r in tagged]
    keep = 0
    for r in rows:                                           # chỉ để lại 3 ứng viên mang thẻ kinh_ram
        if 'kinh_ram' in r['the']:
            keep += 1
            if keep > 3:
                r['the'] = [t for t in r['the'] if t != 'kinh_ram']
                r['diem'] = tb.tinh_diem(r['the'])
                r['muc'] = tb.tinh_muc(r['the'], r['yaw'])
    res = tb.chon(rows, seed=2, n_good=1, max_tries=80)
    miss = tb.the_thieu(res['items'], res['pool'])
    assert [m[0] for m in miss] == ['kinh_ram']
    t, have, need, in_pool, why = miss[0]
    assert (have, need, in_pool) == (3, tb.MIN_THE, 3) and 'chỉ có 3' in why


def test_chon_bao_loi_khi_khong_du_ung_vien(tagged):
    rows = [r for r in tagged if r['muc'] != 'rat_kho']
    with pytest.raises(SystemExit):
        tb.chon(rows, seed=1, n_good=1, max_tries=3)


def test_quota_tham_so():
    assert tb.doc_quota('de=1,vua=2,kho=3,rat_kho=4') == dict(de=1, vua=2, kho=3, rat_kho=4)
    with pytest.raises(SystemExit):
        tb.doc_quota('de=1,vua=2')
    with pytest.raises(SystemExit):
        tb.doc_quota('xyz=1,vua=2,kho=3,rat_kho=4')


# ---------- đánh số ----------
def test_danh_so_khoi_dong_khoi_va_ke_nhau(selected):
    order = tb.danh_so(selected['items'], seed=3)
    assert len(order) == tb.N_ANH and len({c['name'] for c in order}) == tb.N_ANH
    a, b = order[0], order[1]
    assert a['muc'] == b['muc'] == 'de' and a['subject'] != b['subject'] and a['source'] == b['source'] == 'yawdd'
    assert a['diem'] == 0 and b['diem'] == 0
    assert all(order[i]['subject'] != order[i + 1]['subject'] for i in range(len(order) - 1))
    rest = order[tb.N_WARMUP:]
    size = len(rest) // tb.N_BLOCKS
    tot = Counter(c['muc'] for c in rest)
    for k in range(tb.N_BLOCKS):
        blk = rest[k * size:(k + 1) * size]
        for m in tb.LEVELS:
            expected = tot[m] * len(blk) / len(rest)
            assert abs(sum(1 for c in blk if c['muc'] == m) - expected) <= 1, (k, m)
        assert sum(1 for c in blk if c['nhap'] == 'te') <= tb.MAX_TE_PER_BLOCK


def test_danh_so_cung_seed_cung_thu_tu_khac_seed_khac(selected):
    o1 = [c['name'] for c in tb.danh_so(selected['items'], seed=11)]
    o2 = [c['name'] for c in tb.danh_so(selected['items'], seed=11)]
    o3 = [c['name'] for c in tb.danh_so(selected['items'], seed=12)]
    assert o1 == o2 and o1 != o3
    assert o1 == [c['name'] for c in tb.danh_so(list(reversed(selected['items'])), seed=11)]       # không phụ thuộc thứ tự đầu vào


def test_chon_cung_seed_cung_ket_qua(tagged):
    a = tb.chon(tagged, seed=5, n_good=1, max_tries=60)
    b = tb.chon(tagged, seed=5, n_good=1, max_tries=60)
    assert [c['name'] for c in a['items']] == [c['name'] for c in b['items']]
    c = tb.chon(tagged, seed=6, n_good=1, max_tries=60)
    assert {x['name'] for x in a['items']} != {x['name'] for x in c['items']}


def test_giu_khung_them_theo_khoang_cach_va_hash():
    old = [dict(t=10.0, hash=0)]
    samples = [dict(t=10.5, hash=0xFFFFFFFF, prio=30), dict(t=12.0, hash=0xFFFF, prio=20), dict(t=12.5, hash=0xFFFFFFFFFF, prio=15),
               dict(t=14.0, hash=0xFFFFFFFFFFFFFFFF, prio=10), dict(t=16.0, hash=0b1111, prio=5), dict(t=18.0, hash=0xFFFFFF00, prio=40)]
    kept, near, over = tb.giu_khung(samples, old, ['x'], per_video=2)
    ts = [s['t'] for s in kept]
    assert len(kept) == 2 and ts == sorted(ts)
    assert 10.5 not in ts                                    # cách khung cũ < 2 giây
    assert 18.0 in ts                                        # ưu tiên cao nhất
    assert near >= 1 and over >= 1
    for i, s in enumerate(kept):
        assert all(abs(s['t'] - o['t']) >= tb.MIN_GAP_S for o in old + kept[:i])


# ---------- gói: ảnh, manifest B, zip, rò rỉ ----------
def test_hop_dong_nhat_cat_lai_ra_dung_anh():
    box = tb.hop_dong_nhat()
    left, top, k, _, _ = crop_geometry(box, np.zeros((1, 2), np.float32))
    assert (left, top, k) == (0.0, 0.0, 1.0)
    img = np.random.default_rng(0).integers(0, 256, (512, 512, 3), dtype=np.uint8)
    out = square_crop(img, box, np.zeros((1, 2), np.float32))[0]
    assert np.array_equal(out, img)


def test_manifest_b_doc_duoc_bang_load_items(tmp_path):
    rows = tb.manifest_b_rows(5)
    mp = tmp_path / 'manifest.csv'
    tb.ghi_csv(str(mp), tb.MANIFEST_B_COLS, rows)
    anh = tmp_path / 'anh'
    anh.mkdir()
    for r in rows:
        cv2.imwrite(str(anh / r['file']), np.zeros((512, 512, 3), np.uint8))
    args = SimpleNamespace(manifest=str(mp), list=str(mp), set=None, images=str(anh), box='crop', run=None)
    items = steps.load_items(args)
    assert [it['name'] for it in items] == ['001', '002', '003', '004', '005']
    assert all(it['box'] == tb.hop_dong_nhat() and it['path'] == str(anh / (it['name'] + '.png')) for it in items)
    assert list(rows[0]) == tb.MANIFEST_B_COLS


def _anh_gia(tmp_path, n=12):
    d = tmp_path / 'anh'
    d.mkdir(exist_ok=True)
    rng = np.random.default_rng(1)
    for i in range(1, n + 1):
        cv2.imwrite(str(d / f'{i:03d}.png'), rng.integers(0, 256, (512, 512, 3), dtype=np.uint8), [cv2.IMWRITE_PNG_COMPRESSION, 1])
    return str(d)


def test_png_cv2_khong_kem_metadata(tmp_path):
    d = _anh_gia(tmp_path, 2)
    for n in os.listdir(d):
        assert set(tb.png_chunks(open(os.path.join(d, n), 'rb').read())) <= tb.ANH_PNG_CHUNKS


def test_ghi_zip_tat_dinh_mo_duoc_va_chia_phan(tmp_path):
    d = _anh_gia(tmp_path, 12)
    ents = tb.entries_anh(d, 'bo200_A')
    limit = 2 * 786432 + 4000                                      # ~ 2 ảnh mỗi phần (mỗi ảnh nhiễu ~ 786 KB)
    t1, t2 = tmp_path / 't1', tmp_path / 't2'
    t1.mkdir()
    t2.mkdir()
    p1 = tb.dong_phan_anh('A', ents, str(t1), limit)
    p2 = tb.dong_phan_anh('A', ents, str(t2), limit)
    assert len(p1) >= 5 and [x[2] for x in p1] == [x[2] for x in p2]               # dựng hai lần ra cùng sha256
    assert all(size <= limit for _, size, _ in p1)
    assert os.path.basename(p1[0][0]) == f'm28_bo200_A_part01_of_{len(p1):02d}.zip'
    seen = []
    for path, size, sha in p1:
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            names = [zi.filename for zi in z.infolist()]
            assert names == sorted(names) and all(n.isascii() for n in names)
            assert all(zi.date_time == tb.ZIP_DATE and zi.compress_type == zipfile.ZIP_STORED and (zi.external_attr >> 16) == 0o100644 for zi in z.infolist())
            seen += names
        assert hashlib.sha256(open(path, 'rb').read()).hexdigest() == sha
    assert sorted(seen) == sorted(n for n, _ in ents)


def test_ghi_zip_tu_choi_ten_khong_ascii_va_trung(tmp_path):
    with pytest.raises(UnicodeEncodeError):
        tb.ghi_zip(str(tmp_path / 'x.zip'), [('anh/ảnh.png', b'x')])
    with pytest.raises(ValueError):
        tb.ghi_zip(str(tmp_path / 'y.zip'), [('a', b'1'), ('a', b'2')])


def test_quet_ro_ri_bat_dung_va_khong_bao_nham():
    ok = ('bo200_A/README_A.txt', 'Giải nén vào cùng một thư mục. Dùng project m28 và label face50.'.encode('utf-8'))
    assert not tb.quet_ro_ri([ok], hostname='maychu01')
    bad = {'yd_F035': 'khung yd_F035_mirror_talking_g0_f000510.jpg', 'df_03': 'ảnh df_03_0123', 'avi': 'video 12-Male.avi', 'cam': 'camera Mirror', 'cam2': 'Dash',
           'nguon': 'lấy từ YawDD', 'nguon2': 'drivface', 'the': 'có thẻ yaw_manh_phai', 'muc': 'rat_kho', 'duongdan': 'file /home/user/x.png',
           'duongdan2': r'C:\Users\a', 'host': 'chạy trên maychu01', 'tmp': 'x /tmp/claude-0/y'}
    for k, text in bad.items():
        assert tb.quet_ro_ri([('f.txt', text.encode('utf-8'))], hostname='maychu01'), k
    assert tb.quet_ro_ri([('yd_F035/001.png', b'x')], hostname='maychu01')                  # tên mục cũng bị quét
    notice = 'Nguon: YawDD va DrivFace'.encode()
    assert not tb.quet_ro_ri([('x/NOTICE.txt', notice)], hostname='maychu01')               # NOTICE được nêu tên hai bộ
    assert tb.quet_ro_ri([('x/README_A.txt', notice)], hostname='maychu01')                 # chỗ khác thì không
    assert tb.quet_ro_ri([('x/NOTICE.txt', b'yd_F035')], hostname='maychu01')               # NOTICE vẫn cấm mã tài xế
    # PNG có chunk metadata bị bắt
    import struct
    import zlib
    png = bytearray(b'\x89PNG\r\n\x1a\n')
    for typ, body in ((b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)), (b'tEXt', b'k\x00v'), (b'IEND', b'')):
        png += struct.pack('>I', len(body)) + typ + body + struct.pack('>I', zlib.crc32(typ + body) & 0xFFFFFFFF)
    got = tb.quet_ro_ri([('a/001.png', bytes(png))], hostname='maychu01')
    assert got and got[0][1] == 'metadata_png'


def test_readme_va_notice_khong_ro_ri_va_dien_du_bang():
    parts = [('m28_bo200_A_part01_of_02.zip', 21000000, 'a' * 64), ('m28_bo200_A_part02_of_02.zip', 21000001, 'b' * 64)]
    for kind in ('A', 'B'):
        text = tb.doc_readme(kind, parts, 2)
        assert 'a' * 64 in text and '21000001' in text and 'bo200_v1' in text
        assert 'Lexicographical' in text and 'Image quality = 95' in text and 'Segment size = 8' in text
        assert 'longmaytrai' in text and 'occluded' in text and 'trai' in text
        assert not tb.quet_ro_ri([(f'bo200/README_{kind}.txt', tb.text_crlf(text))], hostname='maychu01'), kind
    b = tb.doc_readme('B', parts, 2)
    assert '--manifest data/bo200/manifest.csv' in b and '--box crop' in b and '--run bo200' in b and '--force mediapipe' in b and 'prelabel.xml' in b
    assert not tb.quet_ro_ri([('x/NOTICE.txt', tb.text_crlf(tb.NOTICE))], hostname='maychu01')
    assert 'YawDD' in tb.NOTICE and 'DrivFace' in tb.NOTICE and 'yd_F' not in tb.NOTICE


def test_info_json_va_sha_anh():
    shas = {f'{i:03d}.png': hashlib.sha256(str(i).encode()).hexdigest() for i in range(1, 201)}
    info = json.loads(tb.info_json(shas))
    assert info['bo_anh'] == 'bo200_v1' and info['so_anh'] == 200 and info['warmup'] == ['001.png', '002.png'] and info['anh'][-1] == '200.png'
    assert info['sha256'] == shas and info['tong_sha256'] == hashlib.sha256(tb.sha_anh_text(shas).encode()).hexdigest()
    assert tb.sha_anh_text(shas).splitlines()[0].endswith('  anh/001.png')
    assert not tb.quet_ro_ri([('bo200_info.json', tb.info_json(shas).encode())], hostname='maychu01')


# ---------- lệnh: dry-run, --out, lưới, đo ----------
def test_out_trong_repo_bi_tu_choi(tmp_path):
    with pytest.raises(SystemExit):
        tb.check_out_dir(os.path.join(tb.repo_root(), 'source-tool', 'm28-prelabel', 'bo200_tam'))
    assert tb.check_out_dir(str(tmp_path / 'ra')) == str(tmp_path / 'ra')
    with pytest.raises(SystemExit):
        tb.main(['chon', '--out', os.path.join(tb.PROJECT, 'x')])


def _ghi_bang(tmp_path, rows):
    cols = tb.CSV_BANG
    out = []
    for r in rows:
        o = {c: ('' if r.get(c) is None else r.get(c)) for c in cols}
        o['khung'] = f'{r["source"]}/{r["subject"]}/{r["name"]}.jpg'
        o['hash'] = r['hash']
        out.append(o)
    d = tmp_path / 'cache'
    d.mkdir(exist_ok=True)
    tb.ghi_csv(str(d / 'bang_do.csv'), cols, out)


def test_chon_dry_run_khong_ghi_file_va_chon_that_ghi_bi_mat(tmp_path):
    rows = fake_rows()
    _ghi_bang(tmp_path, rows)
    sua = tmp_path / 'sua.csv'
    bad = sorted((r for r in rows if abs(r['yaw']) > 40), key=lambda r: -abs(r['yaw']))[:12]
    sua.write_text('ung_vien,the_them,the_bo,quyet_dinh,ghi_chu\n' + ''.join(f'{r["name"]},nhap_te,,,nháp sai\n' for r in bad), encoding='utf-8')
    a = tb.build_parser().parse_args(['chon', '--out', str(tmp_path), '--sua-the', str(sua), '--seed', '4', '--dry-run'])
    a.project = PROJECT
    before = sorted(os.listdir(tmp_path))
    tb.SEEDS_GOOD, old = 1, tb.SEEDS_GOOD
    try:
        tb.cmd_chon(a)
    finally:
        tb.SEEDS_GOOD = old
    assert sorted(os.listdir(tmp_path)) == before and not (tmp_path / 'bi_mat').exists()
    a.dry_run = False
    res, order = tb.cmd_chon(a)
    rows_out = list(csv.DictReader(open(tmp_path / 'bi_mat' / 'bo200_bi_mat.csv', encoding='utf-8')))
    assert [r['so'] for r in rows_out] == [f'{i:03d}' for i in range(1, 201)]
    assert list(rows_out[0]) == tb.BI_MAT_COLS and rows_out[0]['warmup'] == '1' and rows_out[1]['warmup'] == '1' and rows_out[2]['warmup'] == '0'
    assert Counter(r['muc'] for r in rows_out) == Counter(tb.QUOTA)
    assert {'tot', 'vua', 'te'} >= {r['nhap'] for r in rows_out} and sum(r['nhap'] == 'te' for r in rows_out) >= 8
    md = (tmp_path / 'bi_mat' / 'bo200_bi_mat.md').read_text(encoding='utf-8')
    assert 'Seed khởi đầu 4' in md and 'Thẻ thiếu' in md and '| Mức |' in md
    pb = list(csv.DictReader(open(tmp_path / 'bi_mat' / 'phan_bo.csv', encoding='utf-8')))
    assert [r['muc'] for r in pb][-1] == 'tổng' and int(pb[-1]['n']) == 200
    ck = json.load(open(tmp_path / 'cache' / 'chon.json', encoding='utf-8'))
    assert ck['thu_tu'] == [r['ung_vien'] for r in rows_out] and ck['bo_anh'] == 'bo200_v1'
    assert (tmp_path / 'bi_mat' / 'sua_the.csv').exists() and (tmp_path / 'nhat_ky.txt').exists()


def test_ve_luoi_kich_thuoc_va_csv(tmp_path):
    rng = np.random.default_rng(2)
    cells = [dict(img=rng.integers(0, 256, (512, 512, 3), dtype=np.uint8), lines=[f'{i:03d} vua S1', 'y+1 p-2', 'yaw_vua kinh_can'], key=f'k{i}') for i in range(34)]
    outs = tb.ve_luoi(cells, str(tmp_path / 'g'))
    assert len(outs) == 2
    im = cv2.imread(outs[0])
    assert max(im.shape[:2]) <= 1600 and im.shape[1] == 6 * 256
    rows = list(csv.DictReader(open(str(tmp_path / 'g_02.csv'), encoding='utf-8')))
    assert [r['key'] for r in rows] == [f'k{i}' for i in range(30, 34)]
    assert tb.dong_the(['yaw_vua', 'cam_dash', 'kinh_can'], 12) == ['yaw_vua', 'kinh_can']


def test_loc_where():
    rows = [dict(yaw=-45.0, glasses='none'), dict(yaw=10.0, glasses='sunglasses'), dict(yaw=None, glasses='none')]
    assert len(tb.loc_where(rows, ['abs_yaw>=40'])) == 1
    assert len(tb.loc_where(rows, ['glasses==sunglasses'])) == 1
    assert len(tb.loc_where(rows, ['yaw<0', 'glasses==none'])) == 1
    with pytest.raises(SystemExit):
        tb.loc_where(rows, ['hỏng'])


def test_do_measure_voi_bo_do_gia(tmp_path, monkeypatch):
    """do_measure: cắt đúng square_crop, flip_nme = 0 khi ảnh lật trùng ảnh gốc, df_err cho DrivFace, hash khớp measure_face."""
    cfg = json.load(open(os.path.join(PROJECT, 'config', 'm28_config.json'), encoding='utf-8'))
    mp_map = json.load(open(os.path.join(PROJECT, 'config', 'map_mp50.json'), encoding='utf-8'))
    rng = np.random.default_rng(3)
    frame = rng.integers(0, 256, (480, 640, 3), dtype=np.uint8)
    cv2.imwrite(str(tmp_path / 'f.png'), frame)
    pts = rng.uniform(150, 350, (478, 2))

    class FakeDet:
        def detect(self, rgb):
            return dict(pts=pts, matrix=None, jaw_open=0.3, blink_l=0.1, blink_r=0.2)

    calls = []

    def fake_padded(lm, rgb, run=None):
        calls.append(rgb.shape)
        return pts.tolist()                                    # ảnh lật cho cùng điểm: đối xứng giả

    monkeypatch.setattr(tb.steps, 'run_mp_padded', fake_padded)
    t = dict(name='x', path=str(tmp_path / 'f.png'), video='v.jpg', box=[200.0, 160.0, 400.0, 360.0])
    G = dict(det=FakeDet(), lm=object(), hand=None, cfg=cfg, map=mp_map, df={})
    out = tb.do_measure(t, G)
    assert out['mp_ok'] == 1 and out['mp_flip_ok'] == 1 and out['jaw_crop'] == 0.3 and out['blink_l'] == 0.1 and len(out['p50']) == 50 and len(out['p50f']) == 50
    assert out['flip_nme'] >= 0 and 0 < out['box_iou'] <= 1
    expect = tb.ii.measure_face(frame, np.array([[200.0, 160.0], [400.0, 360.0]]), None, None)['hash']
    assert out['hash'] == expect
    # DrivFace: có tham chiếu 5 điểm thì có df_err
    ref = {'EL': (250.0, 250.0), 'ER': (330.0, 250.0), 'N': (290.0, 290.0), 'ML': (260.0, 330.0), 'MR': (320.0, 330.0)}
    out2 = tb.do_measure(t, dict(G, df={'v.jpg': ref}))
    assert out2['df_err'] is not None and out2['df_err'] > 0
    # không đọc được khung
    assert tb.do_measure(dict(t, path=str(tmp_path / 'khong_co.png')), G)['err'] == 'khong_doc_duoc_khung'
    # không thấy mặt
    class NoDet:
        def detect(self, rgb):
            return None
    r = tb.do_measure(t, dict(G, det=NoDet()))
    assert r['mp_ok'] == 0 and 'flip_nme' not in r


def test_doc_bang_ep_kieu(tmp_path):
    rows = fake_rows(n_subj=6, per=3)
    _ghi_bang(tmp_path, rows)
    got = tb.doc_bang(str(tmp_path / 'cache' / 'bang_do.csv'))
    assert len(got) == 18 and isinstance(got[0]['yaw'], float) and isinstance(got[0]['hash'], int) and got[0]['mp_ok'] == 1 and got[0]['moi'] == 0


def test_hop_va_giao_hop():
    assert tb.box_inter_frac((0, 0, 10, 10), (5, 5, 15, 15)) == pytest.approx(0.25)
    assert tb.box_iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert tb.box_iou((0, 0, 1, 1), (5, 5, 6, 6)) == 0.0


# ---------- Table1/Table2 của YawDD ----------
T1 = """  Male
Participant   Action   Facial   Background   Type of   Lighting   Ethnicity   Allow
    1         Talking    No         No        No Glasses      Sunny     Caucasian        No
    1         Normal     No         No        Sun glasses     Sunny     Caucasian        No
                                                                          Middle
    2         Normal     No         Yes       Prescription    Sunny                     Yes
                                                                         Eastern
   30   Talking&Yawning   No   Yes   Prescription   Sunny                Yes
  Female                                                                                Researchers
    1         Yawning    No         No        No Glasses      Sunny     Caucasian       Yes
"""
T2 = """  Male                                                               Another
              Normal-Talking-                                          No                  Middle
    1                            No         Yes       Prescription              Sunny                   Yes
                 Yawning                                                                   Eastern
 Female       Mouth Position    Scarf   Background    Type of       Another   Lighting   Ethnicity      Allow
    2         Normal-Talking-    No        Yes       No Glasses       No       Sunny      Middle        No
"""


def test_table_yawdd_va_dang_anh():
    tab = tb.doc_table_yawdd(T1, T2)
    assert tab[('mirror', 'M', 1, 'talking', 'no glasses')] == 'No'
    assert tab[('mirror', 'M', 1, 'normal', 'sun glasses')] == 'No'
    assert tab[('mirror', 'M', 2, 'normal', 'prescription')] == 'Yes'
    assert tab[('mirror', 'M', 30, 'talking_yawning', 'prescription')] == 'Yes'
    assert tab[('mirror', 'F', 1, 'yawning', 'no glasses')] == 'Yes'
    assert tab[('dash', 'M', 1)] == 'Yes' and tab[('dash', 'F', 2)] == 'No'
    assert tb.dang_anh_cua('Mirror/Male_mirror Avi Videos/2-MaleGlasses-Normal.avi', tab) == 'Yes'
    assert tb.dang_anh_cua('Mirror/Male_mirror Avi Videos/1-MaleSunGlasses-Normal.avi', tab) == 'No'
    assert tb.dang_anh_cua('Dash/Female/2-FemaleNoGlasses.avi', tab) == 'No'
    assert tb.dang_anh_cua('Mirror/Male_mirror Avi Videos/9-MaleGlasses-Normal.avi', tab) == 'chua_doi_chieu'     # không có dòng
    assert tb.dang_anh_cua('khong/phai/video.avi', tab) == 'chua_doi_chieu'
    assert tb.dang_anh_cua('Dash/Female/2-FemaleNoGlasses.avi', {}) == 'chua_doi_chieu'


# ---------- ghi ảnh, thư mục sinh nháp, crop giống từng pixel ----------
def test_ghi_anh_dung_thu_muc_sinh_va_crop_giong_tung_pixel(tmp_path):
    rng = np.random.default_rng(5)
    frames = tmp_path / 'frames'
    frames.mkdir()
    rows = []
    for i in range(4):
        img = rng.integers(0, 256, (240, 320, 3), dtype=np.uint8)
        cv2.imwrite(str(frames / f'c{i}.jpg'), img)
        rows.append(dict(name=f'c{i}', moi=0, x0=60.0 + i, y0=40.0, x1=200.0, y1=190.0 + i))
    a = SimpleNamespace(frames=str(frames), out=str(tmp_path / 'out'), project=PROJECT, candidates=None)
    img_dir = tmp_path / 'img'
    shas = tb.ghi_anh(a, rows, str(img_dir))
    assert sorted(shas) == ['001.png', '002.png', '003.png', '004.png']
    for i, r in enumerate(rows, 1):
        want = square_crop(cv2.imread(str(frames / f'c{i - 1}.jpg')), (r['x0'], r['y0'], r['x1'], r['y1']), np.zeros((1, 2), np.float32))[0]
        assert np.array_equal(cv2.imread(str(img_dir / f'{i:03d}.png')), want)
        assert set(tb.png_chunks(open(img_dir / f'{i:03d}.png', 'rb').read())) <= tb.ANH_PNG_CHUNKS
    sinh = tmp_path / 'sinh'
    mp = tb.dung_thu_muc_sinh(a, str(sinh), str(img_dir))
    assert os.path.exists(mp) and os.path.exists(sinh / 'tool' / 'm28.py') and os.path.exists(sinh / 'config' / 'm28_config.json')
    assert sorted(os.listdir(sinh / 'data' / 'bo200' / 'anh')) == sorted(shas)
    assert not os.path.exists(sinh / 'tool' / '__pycache__')
    # bước crop THẬT của tool (--box crop, manifest gói B) cắt lại ra đúng ảnh cũ, từng pixel
    out = tmp_path / 'run_crop'
    out.mkdir()
    cwd = os.getcwd()
    os.chdir(sinh)
    try:
        os.makedirs(os.path.join('runs', 'bo200'), exist_ok=True)
        args = SimpleNamespace(manifest='data/bo200/manifest.csv', list='data/bo200/manifest.csv', set=None, images='data/bo200/anh', box='crop', run='bo200', model='x.task')
        assert steps.crop(args, str(out)) is True
    finally:
        os.chdir(cwd)
    assert tb.so_pixel(str(img_dir), str(out / 'images')) == []


def test_bao_cao_kiem(tmp_path):
    rb = tb.BaoCaoKiem(str(tmp_path))
    rb.them('muc a', True, 'ok')
    assert rb.ok
    rb.them('muc b', False, 'hong')
    assert not rb.ok
    rb.ghi(str(tmp_path / 'bc.txt'))
    txt = (tmp_path / 'bc.txt').read_text(encoding='utf-8')
    assert '[dat] muc a' in txt and '[KHONG DAT] muc b' in txt and 'TONG: KHONG DAT (1/2 muc)' in txt


def test_chon_khong_qua_muc_nhap_te_toi_da(tagged):
    res = tb.chon(tagged, seed=9, n_good=1, max_tries=60, n_te=9)
    assert sum(1 for c in res['items'] if 'nhap_te' in c['the']) <= 9


def test_khong_import_torch_va_mediapipe_o_dau_file():
    src = open(os.path.join(PROJECT, 'tool', 'tao_bo200.py'), encoding='utf-8').read()
    import re
    head = [ln for ln in src.splitlines() if re.match(r'^(import|from) ', ln)]
    assert not any('torch' in ln or 'mediapipe' in ln for ln in head)


# ---------- đọc ứng viên, bảng đo, trích thêm khung ----------
def _cand_csv(path, names, video='Dash/Female/1-FemaleNoGlasses.avi'):
    cols = tb.ii.CAND_COLUMNS
    rows = [dict(name=n, source='yawdd', camera='dash', subject='yd_F001', gender='F', glasses='none', state='dash', video=video, frame=i * 30, t_s=float(i), image=f'cache/frames/{n}.jpg',
                 face_idx=0, x0=10, y0=10, x1=110, y1=130, left=0, top=0, k=1, yaw=1, pitch=2, roll=3, jaw_open=0.1, luma=100, contrast=40, bright_frac=0, lap_var=300, gaze_label='', gaze_ang='',
                 pad_frac=0, w=320, h=240) for i, n in enumerate(names)]
    tb.ghi_csv(str(path), cols, rows)


def test_ung_vien_tat_ca_va_ghi_bang_do(tmp_path):
    inc = tmp_path / 'inc' / 'cache'
    inc.mkdir(parents=True)
    _cand_csv(inc / 'candidates.csv', ['a', 'b'])
    out = tmp_path / 'out'
    (out / 'cache' / 'new').mkdir(parents=True)
    tb.ghi_csv(str(out / 'cache' / 'new' / 'candidates_new.csv'), tb.ii.CAND_COLUMNS + ['hash', 'the_can'],
               [dict(name='c', source='yawdd', camera='dash', subject='yd_F001', gender='F', glasses='none', state='dash', video='Dash/Female/1-FemaleNoGlasses.avi', frame=900, t_s=30.0,
                     image='cache/new/frames/c.jpg', face_idx=0, x0=1, y0=1, x1=101, y1=121, hash=7, the_can='mat_nham')])
    a = SimpleNamespace(candidates=str(inc / 'candidates.csv'), frames=None, out=str(out), manifest616=None)
    rows = tb.ung_vien_tat_ca(a)
    assert [r['name'] for r in rows] == ['a', 'b', 'c'] and [r['moi'] for r in rows] == [0, 0, 1]
    assert rows[0]['khung_path'] == str(inc / 'frames' / 'a.jpg') and rows[2]['khung_path'] == str(out / 'cache' / 'new' / 'frames' / 'c.jpg')
    meas = {'a': dict(mp_ok=1, mp_flip_ok=1, blink_l=0.1, blink_r=0.2, jaw_crop=0.3, flip_nme=1.5, hash=99, box_iou=0.9), 'b': dict(mp_ok=0)}
    got = tb.ghi_bang_do(a, rows, meas)
    assert [r['mp_ok'] for r in got] == [1, 0, '']
    back = tb.doc_bang(str(out / 'cache' / 'bang_do.csv'))
    assert back[0]['flip_nme'] == 1.5 and back[0]['hash'] == 99 and back[0]['canh_mat_px'] == 120.0 and back[2]['moi'] == 1 and back[1]['mp_ok'] == 0
    assert back[0]['khung'] == 'yawdd/yd_F001/a.jpg'
    _cand_csv(out / 'cache' / 'new' / 'candidates_new.csv', ['a'])
    with pytest.raises(SystemExit):
        tb.ung_vien_tat_ca(a)                                           # trùng tên giữa cũ và mới


def test_them_video_giu_khung_dat_the_can_va_tat_dinh(tmp_path):
    """them_video với bộ dò giả: video MJPG 6 giây (30 fps); jawOpen 0,7 thì mọi khung đạt `ngap_rong`; chỉ giữ khung cách nhau >= 2 giây, tối đa per_video."""
    path = str(tmp_path / 'v.avi')
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'MJPG'), 30.0, (320, 240))
    rng = np.random.default_rng(7)
    for i in range(180):
        vw.write(rng.integers(0, 256, (240, 320, 3), dtype=np.uint8))
    vw.release()

    class FakeDet:
        def detect(self, rgb):
            pts = np.stack([np.linspace(90, 230, 478), np.linspace(60, 200, 478)], 1)
            return dict(pts=pts, matrix=None, jaw_open=0.7, blink_l=0.05, blink_r=0.05)

    tb._G.clear()
    tb._G.update(det=FakeDet(), hand=None)
    v = dict(path=path, camera='dash', state='dash', glasses='none', subject='yd_F001', gender='F', rel='Dash/Female/1-FemaleNoGlasses.avi')
    job = dict(v=v, need=['ngap_rong'], dir=str(tmp_path / 'new'), old=[dict(t=0.0, hash=None)], taken=['yd_F001_dash_dash_g0_f000090'], step=0.5, per_video=2)
    try:
        res = tb.them_video(job)
        res2 = tb.them_video(job)
    finally:
        tb._G.clear()
    assert len(res['rows']) == 2 and res['rej']['khung_doc'] == 12
    ts = [float(r['t_s']) for r in res['rows']]
    assert all(abs(t - 0.0) >= tb.MIN_GAP_S for t in ts) and abs(ts[1] - ts[0]) >= tb.MIN_GAP_S
    for r in res['rows']:
        assert r['the_can'] == 'ngap_rong' and os.path.exists(tmp_path / 'new' / 'frames' / (r['name'] + '.jpg')) and r['image'] == f'cache/new/frames/{r["name"]}.jpg'
        assert re.match(r'^yd_F001_dash_dash_g0_f\d{6}(_v\d+)?$', r['name']) and r['name'] != 'yd_F001_dash_dash_g0_f000090'
        assert isinstance(r['hash'], int)
    assert [r['name'] for r in res['rows']] == [r['name'] for r in res2['rows']]


def test_the_can_them_dem_ung_vien_ngoai_616():
    rows = []
    for i in range(50):
        rows.append(dict(mp_ok=1, loai=False, trung_goi616='', the=['kinh_ram']))
    rows += [dict(mp_ok=1, loai=False, trung_goi616='F_001.png', the=['yaw_manh_trai']) for _ in range(60)]
    rows += [dict(mp_ok=1, loai=False, trung_goi616='', the=['pitch_len']) for _ in range(5)]
    got = tb.the_can_them(rows)
    assert 'kinh_ram' not in got                      # 50 ứng viên ngoài 616 >= 40
    assert 'yaw_manh_trai' in got                     # 60 ứng viên nhưng đều trùng 616
    assert 'pitch_len' in got and 'che_tay' in got    # che_tay luôn trích
