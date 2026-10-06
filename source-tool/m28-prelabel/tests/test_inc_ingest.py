"""Thử inc_ingest.py (nạp YawDD + DrivFace, chia tập, gói) và check_manifest in-cabin bằng dữ liệu GIẢ.

Video giả (MJPG .avi, ảnh nhiễu), ảnh DrivFace giả, bộ dò mặt giả: không cần MediaPipe thật, không cần model, không có ảnh mặt thật.
"""
import copy
import csv
import os
import random
import subprocess
import sys
import zipfile
import zlib
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tool'))
import check_manifest as cm  # noqa: E402
import inc_ingest as ii  # noqa: E402
from m28core.cat_mat import crop_geometry, square_crop  # noqa: E402

W, H = 320, 240


@pytest.fixture(autouse=True, scope='module')
def _fast_png():
    """Ghi 616 PNG ở mức nén 6 mất ~45 giây: test dùng mức 1 (nội dung điểm ảnh y hệt, chỉ khác dung lượng)."""
    old = ii.PNG_COMPRESSION
    ii.PNG_COMPRESSION = 1
    yield
    ii.PNG_COMPRESSION = old


# ---------- bộ dò mặt giả: mã hoá hành vi vào ba ô góc của ảnh ----------
class Pt:
    def __init__(self, x, y):
        self.x, self.y = x, y


class Cat:
    def __init__(self, name, score):
        self.category_name, self.score = name, score


def _blocks(rgb):
    g = rgb.mean(axis=2)
    return int((g < 40).sum() > 100), int((g > 235).sum() > 100), g[2:14, 18:30].mean(), g[2:14, 34:46].mean()


class FakeLM:
    """Dấu đen (>= 100 điểm tối) = không thấy mặt, dấu trắng = mặt chạm mép (điểm ngoài khung). Ô B (x 18..30): yaw = (B - 128) * 0,5 độ.
    Ô C (x 34..46): jawOpen = (C - 50) / 180."""

    def __init__(self):
        self.closed = False

    def detect(self, rgb):
        dark, bright, b, c = _blocks(rgb)
        if dark:
            return SimpleNamespace(face_landmarks=[], facial_transformation_matrixes=[], face_blendshapes=[])
        i = np.arange(478)
        fx = 0.5 + (((i * 37) % 478) / 477 - .5) * 0.5
        fy = 0.5 + (((i * 91) % 478) / 477 - .5) * 0.7
        if bright:
            fx = fx - 0.45
        face = [Pt(float(x), float(y)) for x, y in zip(fx, fy)]
        yaw = math_rad((b - 128) * 0.5)
        M = np.eye(4)
        M[0, 0], M[0, 2], M[2, 0], M[2, 2] = np.cos(yaw), np.sin(yaw), -np.sin(yaw), np.cos(yaw)
        return SimpleNamespace(face_landmarks=[face], facial_transformation_matrixes=[M],
                               face_blendshapes=[[Cat('browDownLeft', 0.1), Cat('jawOpen', max(0.0, (float(c) - 50) / 180.0))]])

    def close(self):
        self.closed = True


def math_rad(d):
    return d * np.pi / 180.0


def make_det(_model=None):
    return ii.FaceDetector(FakeLM(), wrap=lambda rgb: rgb)


def frame(mark=None, b=128, c=50, seed=0, w=W, h=H):
    """Ảnh nhiễu (mỗi seed một ảnh khác hẳn → dHash khác); ô B, C mã hoá yaw và jawOpen; mark='dark'|'bright' = dấu không có mặt / chạm mép."""
    rng = np.random.RandomState(seed)
    img = rng.randint(60, 200, (h, w, 3)).astype(np.uint8)
    img[2:14, 18:30], img[2:14, 34:46] = b, c
    if mark:
        img[2:14, 50:62] = 0 if mark == 'dark' else 255
    return img


def write_video(path, frames, fps=10):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'MJPG'), fps, (W, H))
    assert vw.isOpened()
    for f in frames:
        vw.write(f)
    vw.release()


def video_frames(spec, fps=10):
    """spec: list (giây, kwargs frame); mỗi giây = fps khung cùng nội dung (mỗi giây seed riêng)."""
    out = []
    for sec, kw in enumerate(spec):
        img = frame(seed=sec * 7 + zlib.crc32(str(kw).encode()) % 5, **kw)
        out += [img] * fps
    return out


def make_yawdd(root):
    v = lambda *p: os.path.join(root, *p)      # noqa: E731
    normal = [dict()] * 8
    yawn = [dict(c=230), dict(), dict(c=225), dict(), dict(c=220), dict(), dict(), dict()]
    write_video(v('Mirror', 'Female_mirror', '1-FemaleNoGlasses-Normal.avi'), video_frames(normal))
    write_video(v('Mirror', 'Female_mirror', '1-FemaleNoGlasses-Yawning.avi'), video_frames(yawn))
    write_video(v('Mirror', 'Male_mirror Avi Videos', '2-MaleSunGlasses-Talking.avi'),
                video_frames([dict(), dict(mark='dark'), dict(mark='bright'), dict(), dict()]))
    write_video(v('Dash', 'Female', '1-FemaleGlasses.avi.avi'), video_frames([dict()] * 6))
    write_video(v('Dash', 'Male', '13-MaleNoGlasses .avi'), video_frames([dict(b=190)] * 4))
    write_video(v('Dash', 'Male', 'khong_hop_le.avi'), video_frames([dict()] * 2))
    return root


def make_drivface(root, subjects=4, n=12):
    img_dir = os.path.join(root, 'imgs', 'DrivImages')
    os.makedirs(img_dir, exist_ok=True)
    rows = []
    for s in range(1, subjects + 1):
        for i in range(1, n + 1):
            label = 1 if i == 1 else 3 if i == n else 2
            name = f'20130529_{s:02d}_Driv_{i:03d}_f '           # có dấu cách cuối, không có .jpg (như bộ thật)
            cv2.imwrite(os.path.join(img_dir, name + '.jpg'), frame(seed=100 * s + i))
            rows.append([name, s, i, label, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    with open(os.path.join(root, 'drivPoints.txt'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow('fileName,subject,imgNum,label,ang,xF,yF,wF,hF,xRE,yRE,xLE,yLE,xN,yN,xRM,yRM,xLM,yLM'.split(','))
        w.writerows(rows)
    return root


# ---------- 1. Tên video ----------
def test_parse_yawdd_name_variants():
    p = ii.parse_yawdd
    a = p('Mirror/Female_mirror/1-FemaleNoGlasses-Normal.avi')
    assert (a['camera'], a['gender'], a['num'], a['glasses'], a['state'], a['subject']) == ('mirror', 'F', 1, 'none', 'normal', 'yd_F001')
    b = p('Dash/Male/13-MaleNoGlasses .avi')                                # dấu cách trước đuôi
    assert (b['camera'], b['state'], b['subject'], b['glasses']) == ('dash', 'dash', 'yd_M013', 'none')
    assert p('Dash/Female/8-FemaleGlasses.avi.avi')['glasses'] == 'glasses'   # .avi.avi
    assert p('Mirror/Male_mirror Avi Videos/1-MaleSunGlasses-Yawning.avi')['glasses'] == 'sunglasses'
    assert p('Mirror/Male_mirror Avi Videos/23-MaleGlassesBeard-Talking&Yawning.avi')['state'] == 'talking_yawning'
    assert p('Mirror/Male_mirror Avi Videos/20-MaleGlasses-Talking&yawning.avi')['state'] == 'talking_yawning'   # hoa/thường lẫn lộn
    assert p('mirror/female_mirror/1-FEMALENOGLASSES-normal.AVI')['subject'] == 'yd_F001'
    assert p('Mirror/x/1-FemaleNoGlasses.avi') is None                      # Mirror thiếu trạng thái
    assert p('Other/x/1-FemaleNoGlasses-Normal.avi') is None                # thư mục lạ
    assert p('Mirror/x/abc.avi') is None


def test_glasses_fix_for_names_that_disagree_with_tables():
    p = ii.parse_yawdd
    assert p('Mirror/Male_mirror Avi Videos/5-MaleNoGlasses-Yawning.avi')['glasses'] == 'sunglasses'      # Table1: Sun glasses
    assert p('Dash/Female/11-FemaleGlasses.avi.avi')['glasses'] == 'sunglasses'                          # Table2: Sun Glasses
    assert p('Mirror/Female_mirror/5-FemaleNoGlasses-Yawning.avi')['glasses'] == 'none'                  # chỉ sửa đúng cặp (camera, giới, số)
    assert p('Dash/Male/5-MaleGlasses.avi')['glasses'] == 'glasses'


def test_dash_and_mirror_same_number_merge_into_one_subject():
    assert ii.parse_yawdd('Dash/Female/3-FemaleGlasses.avi')['subject'] == ii.parse_yawdd('Mirror/Female_mirror/3-FemaleNoGlasses-Talking.avi')['subject']


def test_list_yawdd_warns_and_skips_unmatched(tmp_path):
    root = make_yawdd(str(tmp_path / 'YawDD dataset'))
    vids, bad = ii.list_yawdd(root)
    assert len(vids) == 5 and bad == ['Dash/Male/khong_hop_le.avi']
    assert {v['subject'] for v in vids} == {'yd_F001', 'yd_M002', 'yd_M013'}


def test_read_drivface_matches_trailing_space_name(tmp_path):
    root = make_drivface(str(tmp_path / 'DrivFace'), subjects=2, n=3)
    items, stats = ii.read_drivface(root)
    assert len(items) == 6 and stats['raw+.jpg'] == 6
    assert items[0]['subject'] == 'df_01' and items[0]['file'].endswith(' .jpg')


# ---------- 2. Đo và cờ ----------
def test_euler_deg_axes():
    assert ii.euler_deg(None) is None
    assert np.allclose(ii.euler_deg(np.eye(4)), (0, 0, 0), atol=1e-9)
    t = math_rad(30)
    M = np.eye(4)
    M[0, 0], M[0, 2], M[2, 0], M[2, 2] = np.cos(t), np.sin(t), -np.sin(t), np.cos(t)
    yaw, pitch, roll = ii.euler_deg(M * 1.0)
    assert round(yaw) == 30 and abs(pitch) < 1e-6 and abs(roll) < 1e-6


def test_compute_flags_thresholds_and_rules():
    base = dict(source='yawdd', glasses='none', yaw=0, pitch=0, jaw_open=0.0, luma=120, contrast=50, bright_frac=0, lap_var=300, gaze_label='')
    assert ii.compute_flags(base) == dict(pose=0, expression=0, illumination=0, makeup=0, occlusion=0, blur=0)
    assert ii.compute_flags(dict(base, yaw=-ii.POSE_YAW_DEG))['pose'] == 1
    assert ii.compute_flags(dict(base, pitch=ii.POSE_PITCH_DEG))['pose'] == 1
    assert ii.compute_flags(dict(base, jaw_open=ii.EXPR_JAW_OPEN))['expression'] == 1
    assert ii.compute_flags(dict(base, luma=ii.LUMA_DARK - 1))['illumination'] == 1
    assert ii.compute_flags(dict(base, contrast=ii.CONTRAST_LOW - 1))['illumination'] == 1
    assert ii.compute_flags(dict(base, bright_frac=ii.BRIGHT_FRAC_MAX + .01))['illumination'] == 1
    assert ii.compute_flags(dict(base, lap_var=ii.BLUR_LAP_VAR['yawdd'] - 1))['blur'] == 1
    assert ii.compute_flags(dict(base, lap_var=ii.BLUR_LAP_VAR['yawdd'] + 1))['blur'] == 0
    assert ii.compute_flags(dict(base, source='drivface', gaze_label='2', lap_var=ii.BLUR_LAP_VAR['drivface'] - 1))['blur'] == 1
    assert ii.compute_flags(dict(base, glasses='sunglasses'))['occlusion'] == 1
    assert ii.compute_flags(dict(base, glasses='glasses'))['occlusion'] == 0
    assert ii.compute_flags(dict(base, yaw=90, jaw_open=1, glasses='sunglasses'))['makeup'] == 0     # makeup luôn 0
    df = dict(base, source='drivface', yaw=27, gaze_label='2')
    assert ii.compute_flags(df)['pose'] == 0                                  # DrivFace: chỉ theo nhãn, bỏ qua yaw
    assert ii.compute_flags(dict(df, gaze_label='1'))['pose'] == 1 and ii.compute_flags(dict(df, gaze_label='3'))['pose'] == 1


# ---------- 3. scan ----------
@pytest.fixture
def scanned(tmp_path):
    yd = make_yawdd(str(tmp_path / 'YawDD dataset'))
    df = make_drivface(str(tmp_path / 'DrivFace'))
    out = str(tmp_path / 'out')
    logs = []
    rows, stats = ii.scan(yd, df, 'khong_can_model', out, make_detector=make_det, log=logs.append)
    return dict(rows=rows, stats=stats, out=out, yd=yd, df=df, logs=logs, tmp=tmp_path)


def test_scan_candidates_and_rejects(scanned):
    rows, st = scanned['rows'], scanned['stats']
    assert any('khong_hop_le.avi' in m and 'CẢNH BÁO' in m for m in scanned['logs'])      # in cảnh báo, không đoán
    assert st['videos_bad'] == ['Dash/Male/khong_hop_le.avi']
    assert st['rejects']['khong_thay_mat'] >= 1 and st['rejects']['diem_ngoai_khung'] >= 1   # video giả có khung loại
    by_video = {}
    for r in rows:
        by_video.setdefault(r['video'], []).append(r)
    assert len(by_video['Mirror/Female_mirror/1-FemaleNoGlasses-Normal.avi']) >= 3
    sun = by_video['Mirror/Male_mirror Avi Videos/2-MaleSunGlasses-Talking.avi']
    assert [r['frame'] for r in sun] == [0, 30] and all(r['glasses'] == 'sunglasses' and r['subject'] == 'yd_M002' for r in sun)   # 5 giây, 2 khung loại, 1 khung gần quá
    names = [r['name'] for r in rows]
    assert len(set(names)) == len(names)
    for r in rows:
        assert os.path.exists(os.path.join(scanned['out'], r['image'])) and ' ' not in r['name']
    dash = by_video['Dash/Male/13-MaleNoGlasses .avi']
    assert all(r['state'] == 'dash' and r['camera'] == 'dash' for r in dash)
    assert os.path.exists(os.path.join(scanned['out'], 'cache', 'candidates.csv'))
    assert len(np.load(os.path.join(scanned['out'], 'cache', 'pts478.npz')).files) == len(rows)


def test_scan_gap_and_near_duplicates(scanned):
    rows = scanned['rows']
    for v in {r['video'] for r in rows if r['source'] == 'yawdd'}:
        t = sorted(float(r['t_s']) for r in rows if r['video'] == v)
        assert all(b - a >= ii.MIN_GAP_S - 1e-6 for a, b in zip(t, t[1:])), v
    dash = [r for r in rows if r['video'].endswith('13-MaleNoGlasses .avi')]
    assert len(dash) >= 1


def test_scan_near_duplicate_frames_dropped(tmp_path):
    root = str(tmp_path / 'YawDD dataset')
    img = frame(seed=1)
    write_video(os.path.join(root, 'Mirror', 'Female_mirror', '3-FemaleNoGlasses-Normal.avi'), [img] * (10 * 8))       # mọi giây giống hệt
    rows, st = ii.scan(root, None, '', str(tmp_path / 'o'), make_detector=make_det, log=lambda m: None)
    assert len(rows) == 1 and st['rejects']['gan_trung'] >= 3


def test_scan_prefers_open_mouth_frames_for_yawning(scanned):
    yaw = [r for r in scanned['rows'] if r['video'].endswith('1-FemaleNoGlasses-Yawning.avi')]
    assert any(float(r['jaw_open']) > 0.9 for r in yaw)                          # có khung há miệng thật (jawOpen ~ 1,0)
    assert any(float(r['jaw_open']) < 0.2 for r in yaw)                          # và khung trải đều theo thời gian


def test_scan_pose_from_matrix_and_drivface_rows(scanned):
    dash = [r for r in scanned['rows'] if r['video'].endswith('13-MaleNoGlasses .avi')]
    assert all(abs(float(r['yaw']) - 31.0) < 3 for r in dash)                    # (190 - 128) * 0,5 độ
    df = [r for r in scanned['rows'] if r['source'] == 'drivface']
    assert {r['subject'] for r in df} == {'df_01', 'df_02', 'df_03', 'df_04'}
    assert all(r['gender'] == 'unknown' and r['glasses'] == 'unknown' and r['t_s'] == '' for r in df)
    assert any(str(r['gaze_label']) == '1' for r in df) and any(str(r['gaze_label']) == '3' for r in df)   # ảnh nhìn phải/trái được giữ
    assert all(' ' not in r['video'] and r['name'].startswith(r['subject'] + '_') for r in df)


def test_scan_resumes_from_shards_without_detector(scanned):
    called = []
    rows2, _ = ii.scan(scanned['yd'], scanned['df'], '', scanned['out'], make_detector=lambda m: called.append(m) or make_det(),
                       log=lambda m: None)
    assert not called and [r['name'] for r in rows2] == [r['name'] for r in scanned['rows']]


def test_sample_video_reads_sequentially_without_frame_count(tmp_path, monkeypatch):
    p = str(tmp_path / 'v' / 'a.avi')
    write_video(p, [frame(seed=i) for i in range(35)], fps=10)
    real = cv2.VideoCapture

    class Cap:
        def __init__(self, path):
            self.c = real(path)

        def get(self, prop):
            assert prop != cv2.CAP_PROP_FRAME_COUNT                    # không tin số khung của header
            return self.c.get(prop)

        def set(self, *a):
            raise AssertionError('không được tua bằng CAP_PROP_POS_FRAMES')

        def __getattr__(self, n):
            return getattr(self.c, n)

    monkeypatch.setattr(ii.cv2, 'VideoCapture', Cap)
    got = list(ii.sample_video(p))
    assert [g[0] for g in got] == [0, 10, 20, 30] and abs(got[1][1] - 1.0) < 1e-6


# ---------- 4. Tổng hợp ứng viên giả cho chia tập ----------
def synth_pool(seed=1, n_yd=64, n_dash=20, with_sun=14, frames=8):
    """Ứng viên giả (dict như read_candidates): nhiều người, nhiều video, cờ rải tự nhiên."""
    rng = random.Random(seed)
    out = []

    def cand(src, cam, subj, gender, glasses, state, video, i, t):
        yaw = rng.gauss(10, 14)
        x0, y0, x1, y1 = 100.0, 60.0, 220.0, 180.0
        left, top, k, _, _ = crop_geometry((x0, y0, x1, y1), np.zeros((1, 2), np.float32))
        c = dict(name=f'{subj}_{cam}_{state}_{video.split("/")[-1][:8]}_{i}', source=src, camera=cam, subject=subj, gender=gender,
                 glasses=glasses, state=state, video=video, frame=i * 30 if src == 'yawdd' else i, t_s=f'{t:.3f}' if src == 'yawdd' else '',
                 image='', face_idx='0', x0=str(x0), y0=str(y0), x1=str(x1), y1=str(y1), left=f'{left:.4f}', top=f'{top:.4f}', k=f'{k:.6f}',
                 yaw=f'{yaw:.2f}', pitch=f'{rng.gauss(-2, 6):.2f}', roll='0', jaw_open=f'{max(0, rng.gauss(0.15, 0.2)):.3f}',
                 luma=f'{rng.gauss(110, 25):.1f}', contrast=f'{rng.gauss(45, 8):.1f}', bright_frac='0.0',
                 lap_var=f'{abs(rng.gauss(200, 120)):.1f}', gaze_label='', gaze_ang='', pad_frac='0.0', w='320', h='240')
        c.update({k: str(v) for k, v in ii.compute_flags(c).items()})
        c['_flags'] = {k: int(c[k]) for k in cm.FLAGS}
        return c

    for n in range(1, n_yd + 1):
        g = 'F' if n % 2 else 'M'
        subj = f'yd_{g}{n:03d}'
        sun = n <= with_sun
        for state in ('normal', 'talking', 'yawning'):
            gl = 'sunglasses' if sun else ('glasses' if n % 3 == 0 else 'none')
            vid = f'Mirror/{g}/{n}-{g}{gl}-{state}.avi'
            out += [cand('yawdd', 'mirror', subj, g, gl, state, vid, i, 2.0 * i) for i in range(frames)]
        if n <= n_dash:
            out += [cand('yawdd', 'dash', subj, g, 'none', 'dash', f'Dash/{g}/{n}-{g}NoGlasses.avi', i, 2.0 * i) for i in range(frames * 3)]
    for s in range(1, 5):
        for i in range(1, 61):
            c = cand('drivface', 'drivface', f'df_{s:02d}', 'unknown', 'unknown', 'unknown', f'2013_{s:02d}_{i:03d}.jpg', i * 3, 0)
            lab = 1 if i % 9 == 0 else 3 if i % 11 == 0 else 2
            c.update(gaze_label=str(lab))
            c.update({k: str(v) for k, v in ii.compute_flags(c).items()})
            c['_flags'] = {k: int(c[k]) for k in cm.FLAGS}
            out.append(c)
    for c in out:
        c['image'] = ii.frame_rel(c)
    return out


@pytest.fixture(scope='module')
def pool_and_items():
    pool = synth_pool()
    items = ii.split_sets(pool, 5)
    return pool, items


def test_split_counts_and_names(pool_and_items):
    _, items = pool_and_items
    assert len(items) == 616
    from collections import Counter
    assert Counter(o['set'] for o in items) == Counter(cm.EXPECT)
    names = [o['file'] for o in items]
    assert len(set(names)) == 616 and all(cm.NAME.match(n) for n in names)
    assert 'F_001.png' in names and 'F_300.png' in names and 'Tdev_100.png' in names and 'Ttest_100.png' in names
    assert 'G1_01.png' in names and 'G5_04.png' in names and 'Pa_01.png' in names and 'Pb_08.png' in names
    assert 'X1_01.png' in names and 'X5_10.png' in names and 'D_01.png' in names and 'D_30.png' in names
    keys = [(o['c']['image'], o['c']['face_idx']) for o in items]
    assert len(set(keys)) == 616


def test_split_separates_people(pool_and_items):
    _, items = pool_and_items
    people = {}
    for o in items:
        people.setdefault(o['set'], set()).add(o['c']['subject'])
    a = [people[s] for s in cm.GROUP_A]
    b = set().union(*(people[s] for s in cm.GROUP_B))
    assert not (set().union(*a) & b)                                   # nhóm A và B không chung người
    assert not (a[0] & a[1]) and not (a[0] & a[2]) and not (a[1] & a[2])  # F, Tdev, Ttest đôi một rời


def test_split_x_blocks_rules(pool_and_items):
    _, items = pool_and_items
    for k in '12345':
        b = [o for o in items if o['set'] == 'X' and o['block'] == k]
        assert len(b) == 10
        assert [o['seq'] for o in b] == list(range(1, 11))
        pose = sum(o['c']['_flags']['pose'] for o in b)
        occ = sum(o['c']['_flags']['occlusion'] for o in b)
        assert 1 <= pose <= 2 and 2 <= occ <= 4
        assert all(not any(o['c']['_flags'].values()) for o in b if o['seq'] <= 2)
        assert len({o['c']['video'] for o in b}) == 10                    # không hai khung cùng video
        assert len({o['c']['gender'] for o in b} - {'unknown'}) >= 2
        assert len({o['c']['camera'] for o in b}) >= 2
        assert len({o['c']['glasses'] for o in b} - {'unknown'}) >= 2
    from collections import Counter
    xs = [o['c'] for o in items if o['set'] == 'X']
    assert max(Counter(c['subject'] for c in xs).values()) <= ii.X_MAX_PER_PERSON          # X không toàn một vài người
    assert sum(c['source'] == 'drivface' for c in xs) <= ii.X_MAX_DF


def test_split_per_video_and_gap_limits(pool_and_items):
    _, items = pool_and_items
    from collections import Counter
    per = Counter((o['c']['source'], o['c']['video']) for o in items)
    assert max(per.values()) <= cm.MAX_PER_VIDEO


def test_split_df_share_and_dash_present(pool_and_items):
    _, items = pool_and_items
    df = sum(o['c']['source'] == 'drivface' for o in items) / 616
    assert 0.10 <= df <= 0.30
    for s in cm.EXPECT:
        rows = [o for o in items if o['set'] == s]
        assert any(o['c']['camera'] == 'mirror' for o in rows)
    assert any(o['c']['camera'] == 'dash' for o in items)


def test_split_deterministic_and_manifest_columns(pool_and_items, tmp_path):
    pool, items = pool_and_items
    p1, p2 = tmp_path / 'm1.csv', tmp_path / 'm2.csv'
    ii.write_manifest(items, str(p1))
    ii.write_manifest(ii.split_sets(synth_pool(), 5), str(p2))
    assert p1.read_bytes() == p2.read_bytes()                                # cùng cache + cùng seed ⇒ giống từng byte
    with open(p1, encoding='utf-8', newline='') as f:
        head = next(csv.reader(f))
    assert head == cm.INC_COLUMNS and head[:6] == ['file', 'set', 'block', 'seq', 'source', 'camera'] and head[-1] == 'seed'
    assert cm.main(str(p1)) == 0


def test_manifest_has_no_names_only_codes(pool_and_items, tmp_path):
    _, items = pool_and_items
    p = tmp_path / 'm.csv'
    ii.write_manifest(items, str(p))
    rows = list(csv.DictReader(open(p, encoding='utf-8')))
    for r in rows:
        assert cm.SUBJECT_RE.match(r['subject'])
        assert r['subject'] not in r['video'] and 'Female' not in r['subject'] and 'Male' not in r['subject']
        assert r['makeup'] == '0' and r['face_idx'] == '0'


def test_split_gives_clear_assertion_when_pool_too_small():
    pool = synth_pool(n_yd=8, n_dash=2, with_sun=1)
    with pytest.raises(AssertionError, match='không chia được'):
        ii.split_sets(pool, 5, max_tries=3)


# ---------- 5. split lệnh thật (ghi khung, ảnh cắt), pack ----------
@pytest.fixture(scope='module')
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp('built')
    pool = synth_pool()
    os.makedirs(out / 'cache' / 'frames')
    for i, c in enumerate(pool):
        g = (np.add.outer(np.arange(H) * (i % 5 + 1), np.arange(W) * (i % 7 + 1)) % 256).astype(np.uint8)       # ảnh trơn: PNG nén nhanh
        cv2.imwrite(str(out / 'cache' / 'frames' / (c['name'] + '.jpg')), np.dstack([g, g[::-1], g[:, ::-1]]), [cv2.IMWRITE_JPEG_QUALITY, 90])
    with open(out / 'cache' / 'candidates.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, ii.CAND_COLUMNS)
        w.writeheader()
        w.writerows([{k: c[k] for k in ii.CAND_COLUMNS} for c in pool])
    items = ii.split(str(out), 5, log=lambda m: None)
    return str(out), items


def test_split_command_writes_frames_crops_manifest(built):
    out, items = built
    rows = list(csv.DictReader(open(os.path.join(out, 'manifest.csv'), encoding='utf-8')))
    assert len(rows) == 616 and len(os.listdir(os.path.join(out, 'crops'))) == 616
    for r in rows[:50] + rows[-10:]:
        assert os.path.exists(os.path.join(out, 'frames', *r['image'].split('/')))
        assert r['image'] == f"{r['source']}/{r['subject']}/{os.path.basename(r['image'])}"
        crop = cv2.imread(os.path.join(out, 'crops', r['file']))
        assert crop.shape == (512, 512, 3)


def test_crop_equals_pipeline_crop(built):
    """Ảnh cắt trong gói = ảnh `m28.py prepare --box wflw` tạo từ khung gốc + hộp trong manifest (square_crop)."""
    out, _ = built
    r = next(csv.DictReader(open(os.path.join(out, 'manifest.csv'), encoding='utf-8')))
    bgr = cv2.imread(os.path.join(out, 'frames', *r['image'].split('/')))
    box = tuple(float(r[k]) for k in ('x0', 'y0', 'x1', 'y1'))
    want, _, (left, top, k), _ = square_crop(bgr, box, np.zeros((1, 2), np.float32))
    got = cv2.imread(os.path.join(out, 'crops', r['file']))
    assert np.array_equal(got, want)
    assert abs(left - float(r['left'])) < 1e-3 and abs(top - float(r['top'])) < 1e-3 and abs(k - float(r['k'])) < 1e-5


def test_split_rerun_is_byte_identical(built):
    out, _ = built
    before = open(os.path.join(out, 'manifest.csv'), 'rb').read()
    ii.split(out, 5, log=lambda m: None)
    assert open(os.path.join(out, 'manifest.csv'), 'rb').read() == before


def test_deal_gpd_spreads_drivface_and_dash_proportionally():
    got = [dict(source='drivface', camera='drivface')] * 12 + [dict(source='yawdd', camera='dash')] * 6 + [dict(source='yawdd', camera='mirror')] * 48
    g, p, d = ii.deal_gpd(got)
    assert (len(g), len(p), len(d)) == (20, 16, 30)
    assert [sum(c['source'] == 'drivface' for c in x) for x in (g, p, d)] == [4, 3, 5]      # tỉ lệ 20:16:30, không dồn vào một tập
    assert all(sum(c['camera'] == 'dash' for c in x) >= 1 for x in (g, p, d))


def test_split_picks_best_balanced_of_several_valid_runs(pool_and_items):
    pool, items = pool_and_items
    first = ii.split_sets(pool, 5, n_good=1)                                 # lần đạt luật đầu tiên
    assert ii.balance_penalty(items) <= ii.balance_penalty(first) + 1e-9
    assert items[0]['seed'] >= 5 and len({o['seed'] for o in items}) == 1    # một seed thực dùng cho cả manifest


def test_plan_parts_respects_limit():
    files = [(f'crops/{i}.png', 1000 + i) for i in range(50)]
    parts = ii.plan_parts(files, 12000)
    assert sum(len(p) for p in parts) == 50 and len(parts) > 1
    with pytest.raises(ValueError):
        ii.plan_parts([('crops/x.png', 99999)], 5000)


def test_pack_parts_meta_and_extract(built, tmp_path):
    out, _ = built
    limit = 4 * 1024 * 1024
    made = ii.pack(out, str(tmp_path / 'parts'), seed=5, limit=limit, log=lambda m: None)
    assert os.path.basename(made[0]) == 'm28_incab_part00_meta.zip' and len(made) >= 3
    for p in made:
        assert os.path.getsize(p) <= limit
    n_parts = len(made) - 1
    assert all(os.path.basename(p) == f'm28_incab_part{i:02d}_of_{n_parts:02d}.zip' for i, p in enumerate(made[1:], 1))
    with zipfile.ZipFile(made[0]) as z:
        assert sorted(z.namelist()) == ['DOC.txt', 'manifest.csv', 'sources/NOTICE.txt']
        assert 'YawDD' in z.read('sources/NOTICE.txt').decode('utf-8') and 'DrivFace' in z.read('sources/NOTICE.txt').decode('utf-8')
        doc = z.read('DOC.txt').decode('utf-8')
        seed = open(os.path.join(out, 'manifest.csv'), encoding='utf-8').read().split('\n')[1].split(',')[-1]
        assert 'check_manifest' in doc and 'tar -xf' in doc and 'seed khoi dau 5' in doc and f'dung seed {seed}' in doc and '--seed 5' in doc
    dest = tmp_path / 'data'
    dest.mkdir()
    for p in made:
        with zipfile.ZipFile(p) as z:
            z.extractall(dest)
    assert not (dest / 'frames').exists() and not (dest / 'cache').exists()
    assert len(os.listdir(dest / 'crops')) == 616
    assert cm.main(str(dest / 'manifest.csv')) == 0
    for n in ('F_001.png', 'X3_05.png', 'D_30.png'):
        assert (dest / 'crops' / n).read_bytes() == open(os.path.join(out, 'crops', n), 'rb').read()
    for p in made:                                                         # không đưa file nào ngoài meta + crops
        with zipfile.ZipFile(p) as z:
            assert all(n.startswith(('crops/', 'sources/')) or n in ('DOC.txt', 'manifest.csv') for n in z.namelist())


def test_cli_rejects_scan_without_sources():
    with pytest.raises(SystemExit):
        ii.main(['scan', '--out', 'x'])


# ---------- 6. check_manifest bắt lỗi in-cabin ----------
@pytest.fixture(scope='module')
def good_rows(pool_and_items):
    _, items = pool_and_items
    return ii.manifest_rows(items)


def test_check_manifest_accepts_good_incabin(good_rows):
    assert cm.check(copy.deepcopy(good_rows)) == []
    assert cm.kind_of(good_rows).startswith('in-cabin')


def test_check_manifest_catches_person_leak_between_A_and_B(good_rows):
    rows = copy.deepcopy(good_rows)
    f_subject = next(r['subject'] for r in rows if r['set'] == 'F')
    next(r for r in rows if r['set'] == 'D')['subject'] = f_subject
    assert any('nhóm A' in e and 'B' in e for e in cm.check(rows))


def test_check_manifest_catches_tdev_ttest_shared_person(good_rows):
    rows = copy.deepcopy(good_rows)
    s = next(r['subject'] for r in rows if r['set'] == 'Tdev')
    next(r for r in rows if r['set'] == 'Ttest')['subject'] = s
    assert any('Tdev và Ttest chung người' in e for e in cm.check(rows))


def test_check_manifest_catches_missing_column(good_rows):
    rows = copy.deepcopy(good_rows)
    for r in rows:
        del r['subject']
    assert any('thiếu cột' in e and 'subject' in e for e in cm.check(rows))


def test_check_manifest_catches_bad_x_blocks(good_rows):
    rows = copy.deepcopy(good_rows)
    x1 = [r for r in rows if r['set'] == 'X' and r['block'] == '1']
    for r in x1:
        r['pose'] = '0'
    assert any('X1' in e and 'pose' in e for e in cm.check(rows))
    rows = copy.deepcopy(good_rows)
    x2 = [r for r in rows if r['set'] == 'X' and r['block'] == '2']
    x2[0]['video'] = x2[1]['video']
    assert any('X2' in e and 'cùng video' in e for e in cm.check(rows))
    rows = copy.deepcopy(good_rows)
    for r in (r for r in rows if r['set'] == 'X' and r['block'] == '3'):
        r['gender'] = 'F'
    assert any('X3' in e and 'gender' in e for e in cm.check(rows))
    rows = copy.deepcopy(good_rows)
    next(r for r in rows if r['set'] == 'X' and r['block'] == '4' and r['seq'] == '1')['blur'] = '1'
    assert any('seq 1-2' in e for e in cm.check(rows))


def test_check_manifest_catches_value_and_gap_errors(good_rows):
    rows = copy.deepcopy(good_rows)
    rows[0]['subject'] = 'Nguyen Van A'
    rows[1]['glasses'] = 'kinh_lam'
    rows[2]['makeup'] = '1'
    rows[3]['pose'] = '2'
    errs = cm.check(rows)
    assert any('subject' in e for e in errs) and any('glasses' in e for e in errs)
    assert any('makeup' in e for e in errs) and any('cờ pose' in e for e in errs)
    rows = copy.deepcopy(good_rows)
    yd = [r for r in rows if r['source'] == 'yawdd']
    a = yd[0]
    b = next(r for r in yd[1:] if r['video'] != a['video'])
    b['video'], b['t_s'] = a['video'], str(float(a['t_s']) + 0.5)
    assert any('cách nhau' in e for e in cm.check(rows))


def test_check_manifest_catches_duplicates_counts_and_names(good_rows):
    rows = copy.deepcopy(good_rows)
    rows[1]['image'], rows[1]['face_idx'] = rows[0]['image'], rows[0]['face_idx']
    rows[2]['file'] = rows[3]['file']
    rows[4]['file'] = 'F-5.png'
    rows[5]['set'] = 'Z'
    errs = '\n'.join(cm.check(rows))
    assert 'trùng (image, face_idx)' in errs and 'trùng tên file' in errs and 'sai mẫu' in errs and 'tập lạ' in errs


def test_check_manifest_main_exit_codes(good_rows, tmp_path):
    bad = copy.deepcopy(good_rows)
    bad = [r for r in bad if r['file'] != 'F_001.png']
    p = tmp_path / 'bad.csv'
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, cm.INC_COLUMNS)
        w.writeheader()
        w.writerows(bad)
    assert cm.main(str(p)) == 1
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), '..', 'tool', 'check_manifest.py'), str(p)],
                       capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 1 and 'in-cabin' in r.stdout and 'F 299' in r.stdout.replace('tập F: 299 mặt', 'F 299')
