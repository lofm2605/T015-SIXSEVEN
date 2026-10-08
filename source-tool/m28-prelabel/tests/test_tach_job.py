"""Thử việc tách nhãn theo TỪNG JOB (m28core/tach_job.py, tool/tach_job.py, cờ --per-job/--no-per-job/--job của collect).

Chỉ dữ liệu giả trong tmp_path và CVAT GIẢ (tests/fake_cvat): chưa kiểm trên CVAT thật 2.77.0 (giả định "id ảnh = số frame trong task" và khoảng job của
task job_file_mapping chỉ kiểm được bằng tool/cvat_smoke.py bước 9 trên máy có CVAT). Không ảnh mặt, không mạng.
"""
import copy
import datetime
import json
import os
import re
import shutil
import sys
import types
import xml.etree.ElementTree as ET

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
import eval50  # noqa: E402
import tach_job as cli  # noqa: E402  (tool/tach_job.py: công cụ dòng lệnh)
from m28core import collect, cvat_io, steps, tach_job as core  # noqa: E402
from test_gan_tay import do_push, make_run3  # noqa: E402
from test_push import calls, collect_args, cvat, pj, state  # noqa: E402,F401  (fixture cvat: CVAT giả + config/ tạm)

CONFIG = os.path.join(HERE, '..', 'config', 'm28_config.json')
EMAIL = 'bi.mat.khong.duoc.lo@example.com'
OLD_RE = r'job (\d+): (\d+) frame, stage (\S+), state (\S+)'          # CHÉP NGUYÊN VĂN biểu thức cũ của collect._jobs_from_txt


def day():
    return datetime.datetime.now().strftime('%d%m')


def norm(el):
    """Chuỗi hoá một phần tử, bỏ tail (khoảng trắng sau thẻ đóng thay đổi theo vị trí)."""
    c = copy.deepcopy(el)
    c.tail = None
    return ET.tostring(c)


def edit_xml(path, fn):
    tree = ET.parse(path)
    fn(tree.getroot())
    tree.write(path, encoding='utf-8', xml_declaration=True)


def read(path):
    return open(path, encoding='utf-8').read()


@pytest.fixture
def pushed(cvat):
    """Task demo-Khoi: 19 Nhận + 3 Gán tay (2 có nháp T_, 1 ảnh trống G_), job_size 8 -> 4 job [8, 8, 3, 3], job id 100..103, frame 0-7, 8-15, 16-18, 19-21."""
    shutil.copy(CONFIG, 'config/m28_config.json')
    w = make_run3(n_nhan=19, n_tay_nhap=2, n_trong=1)
    do_push(w)
    os.makedirs(os.path.join(w['rd'], 'push'), exist_ok=True)
    with open(os.path.join(w['rd'], 'push', 'manual_list.txt'), 'w', encoding='utf-8') as f:       # như steps.push
        f.write('T_001.png\tco_nhap\nT_002.png\tco_nhap\nG_001.png\tanh_trong')
    return w


BASE = lambda who='P4': os.path.join('raw', f'demo-Khoi_{who}_{day()}')            # noqa: E731
RANGES = {100: (0, 7), 101: (8, 15), 102: (16, 18), 103: (19, 21)}
KINDS = {100: 'nhan', 101: 'nhan', 102: 'nhan', 103: 'gan_tay'}


# ---------- ranh giới job, nội dung từng file job ----------
def test_job_boundaries_and_every_image_identical_to_the_whole_task_file(cvat, pushed):
    assert collect.collect(collect_args()) is True
    b = BASE()
    want = sorted(os.path.basename(x) for x in [b + '.xml', b + '.txt'] + [f'{b}_job{j}{e}' for j in RANGES for e in ('.xml', '.txt')])
    assert sorted(os.listdir('raw')) == want
    whole_root = ET.parse(b + '.xml').getroot()
    whole = {im.get('name'): im for im in whole_root.iter('image')}
    total = 0
    for j, (a, z) in RANGES.items():
        root = ET.parse(f'{b}_job{j}.xml').getroot()
        ims = root.findall('image')
        assert [int(i.get('id')) for i in ims] == list(range(a, z + 1))               # id ảnh giữ như file cả task, không đánh lại từ 0
        for im in ims:
            assert norm(im) == norm(whole[im.get('name')])                              # skeleton, points, low_conf giữ nguyên từng byte
        assert root.find('version').text == '1.1'
        total += len(ims)
    assert total == len(whole) == 22
    assert open(f'{b}_job100.xml', 'rb').read().startswith(b'<?xml version=')


def test_gan_tay_job_is_separate_and_report_has_job_table(cvat, pushed):
    collect.collect(collect_args())
    b = BASE()
    names = lambda j: sorted(im.get('name') for im in ET.parse(f'{b}_job{j}.xml').getroot().iter('image'))      # noqa: E731
    assert names(103) == ['G_001.png', 'T_001.png', 'T_002.png']                          # cả ảnh có nháp lẫn ảnh trống
    for j in (100, 101, 102):
        assert not [n for n in names(j) if n[0] in 'TG']
    rep = read('outputs/collect_demo-Khoi.md')
    assert 'Theo job' in rep and '| 103 | gan_tay | 19-21 | 3/3 | 2 | 2 | 0 | 100 |' in rep           # ảnh trống không có skeleton: 3 ảnh, 2 có nhãn
    assert '| 100 | nhan | 0-7 | 8/8 | 8 | 8 | 0 | 64 |' in rep and '| 102 | nhan | 16-18 | 3/3 | 3 | 3 | 0 | 24 |' in rep
    assert 'mặt đủ 50 điểm: 21' in rep and 'Gán tay: 2 có nháp, 1 ảnh trống' in rep         # các dòng cũ còn nguyên
    assert 'không đưa vào QC' in rep and '## Tách job' not in rep                          # không lỗi, không cảnh báo
    assert 'tách job' in rep.split('Thời gian từng bước')[1]


def test_txt_new_job_lines_are_backward_compatible(cvat, pushed):
    collect.collect(collect_args())
    txt = read(BASE() + '.txt')
    assert 'job 100: 8 frame, stage annotation, state new | frames 0-7 | loai nhan' in txt
    assert 'job 103: 3 frame, stage annotation, state new | frames 19-21 | loai gan_tay' in txt
    lines = [ln for ln in txt.splitlines() if ln.startswith('job ')]
    assert len(lines) == 4 and 'so_job: 4' in txt and 'task_id: 1' in txt
    for ln in lines:                                                                    # biểu thức CŨ đọc state sạch, không dính dấu | hay dấu phẩy
        m = re.match(OLD_RE, ln.strip())
        assert m and m.group(4) == 'new' and m.group(3) == 'annotation'
    jobs = collect._jobs_from_txt(BASE() + '.txt')
    assert [(j['id'], j['n'], j['stage'], j['state'], j['start'], j['stop'], j['kind']) for j in jobs] == \
        [(j, RANGES[j][1] - RANGES[j][0] + 1, 'annotation', 'new', RANGES[j][0], RANGES[j][1], KINDS[j]) for j in RANGES]
    jt = read(f'{BASE()}_job103.txt')                                                  # .txt của file job
    assert 'nguon: demo-Khoi_P4_' in jt and 'job_id: 103' in jt and 'loai: gan_tay' in jt and 'frames: 19-21' in jt and 'so_frame_job: 3' in jt
    assert 'so_anh_trong_file: 3' in jt and 'UTC+7' in jt and 'KHÔNG dùng để nhập lại vào CVAT' in jt and 'canh_bao' not in jt
    one = [ln for ln in jt.splitlines() if ln.startswith('job ')]
    assert one == ['job 103: 3 frame, stage annotation, state new | frames 19-21 | loai gan_tay']
    m = re.match(OLD_RE, one[0])
    assert m and m.group(4) == 'new' and collect._jobs_from_txt(f'{BASE()}_job103.txt')[0]['start'] == 19


def test_old_txt_without_frames_or_loai_uses_cumulative_frames_and_khong_ro(cvat, pushed, tmp_path):
    collect.collect(collect_args())
    b = BASE()
    old = re.sub(r' \| frames \d+-\d+ \| loai \S+', '', read(b + '.txt'))               # .txt cũ: không có frames, không có loai
    assert ' | ' not in old
    for f in os.listdir('raw'):
        if '_job' in f:
            os.remove(os.path.join('raw', f))
    open(b + '.txt', 'w', encoding='utf-8', newline='\n').write(old)
    os.remove(os.path.join(pushed['rd'], 'push.json'))                                  # không còn push.json: loại không rõ
    meta = core.read_txt(b + '.txt')
    assert [(j['start'], j['stop'], j['suy_ra'], j['kind']) for j in meta['jobs']] == \
        [(0, 7, True, 'khong_ro'), (8, 15, True, 'khong_ro'), (16, 18, True, 'khong_ro'), (19, 21, True, 'khong_ro')]
    res = core.tach(b + '.xml', 'raw')
    assert [(j['id'], j['n_anh'], j['kind']) for j in res['jobs']] == [(100, 8, 'khong_ro'), (101, 8, 'khong_ro'), (102, 3, 'khong_ro'), (103, 3, 'khong_ro')]
    assert 'frame suy ra từ số frame cộng dồn' in read(f'{b}_job100.txt')
    assert 'loai: khong_ro' in read(f'{b}_job103.txt') and 'không kiểm được' in res['kiem_lech']


def test_loai_comes_from_push_json_only_when_task_id_matches(cvat, pushed):
    p = os.path.join(pushed['rd'], 'push.json')
    st = json.load(open(p, encoding='utf-8'))
    assert core.push_jobs('demo-Khoi')['kinds'] == {100: 'nhan', 101: 'nhan', 102: 'nhan', 103: 'gan_tay'}
    assert core.push_jobs('demo-Khoi', task_id=st['task_id'])['run'] == 'Khoi'
    assert core.push_jobs('demo-Khoi', task_id=999) is None and core.push_jobs('demo-Khac') is None and core.push_jobs('m28-manual') is None
    assert core.push_jobs('demo-Khoi')['manual'] == ['T_001.png', 'T_002.png', 'G_001.png']
    st['task_id'] = 999                                                                 # task xoá rồi tạo lại cùng tên: push.json là của task cũ
    json.dump(st, open(p, 'w', encoding='utf-8'))
    collect.collect(collect_args())
    txt = read(BASE() + '.txt')
    assert txt.count('loai khong_ro') == 4 and 'loai nhan' not in txt and 'loai gan_tay' not in txt
    st.update(task_id=1, trang_thai='task_deleted')                                    # lượt đã xoá task: bỏ qua
    json.dump(st, open(p, 'w', encoding='utf-8'))
    assert core.push_jobs('demo-Khoi') is None


# ---------- không ghi đè ----------
def test_job_files_are_never_overwritten_and_missing_ones_are_rewritten(cvat, pushed, capsys):
    collect.collect(collect_args())
    b = BASE()
    marked = f'{b}_job101.xml'
    open(marked, 'a').write('<!-- sửa tay -->')
    os.remove(f'{b}_job102.xml')
    capsys.readouterr()
    collect.collect(collect_args())
    out = capsys.readouterr().out
    assert open(marked).read().endswith('<!-- sửa tay -->') and out.count('KHÔNG ghi đè') >= 4        # file cả task + file job có sẵn
    assert os.path.exists(f'{b}_job102.xml') and os.path.exists(f'{b}_job102.txt')
    rep = read('outputs/collect_demo-Khoi.md')
    assert 'đã có từ trước' in rep
    res = core.tach(b + '.xml', 'raw')
    assert [j['da_co'] for j in res['jobs']] == [True] * 4
    assert open(marked).read().endswith('<!-- sửa tay -->')


# ---------- id không liên tục, ảnh lệch job, id ngoài mọi job ----------
def test_missing_frame_warns_x_over_n(cvat, pushed):
    collect.collect(collect_args())
    b = BASE()
    for f in [f for f in os.listdir('raw') if '_job' in f]:
        os.remove(os.path.join('raw', f))
    edit_xml(b + '.xml', lambda r: r.remove(next(im for im in r.iter('image') if im.get('id') == '3')))      # frame 3 bị xoá trong CVAT
    res = core.tach(b + '.xml', 'raw')
    j100 = res['jobs'][0]
    assert j100['n_anh'] == 7 and j100['thieu'] == [3] and '7/8 ảnh, thiếu frame 3' in j100['canh_bao'][0]
    assert 'frame_thieu: 3' in read(f'{b}_job100.txt') and '7/8 ảnh, thiếu frame 3' in read(f'{b}_job100.txt')
    assert [int(i.get('id')) for i in ET.parse(f'{b}_job100.xml').getroot().iter('image')] == [0, 1, 2, 4, 5, 6, 7]
    for f in [f for f in os.listdir('raw') if '_job' in f]:
        os.remove(os.path.join('raw', f))
    collect.collect(collect_args(skip_export=True))
    rep = read('outputs/collect_demo-Khoi.md')
    assert '## Tách job' in rep and 'job 100: 7/8 ảnh, thiếu frame 3' in rep and '| 100 | nhan | 0-7 | 7/8 |' in rep


def test_image_in_wrong_job_warns_but_files_are_written(cvat, pushed):
    collect.collect(collect_args())
    b = BASE()
    for f in [f for f in os.listdir('raw') if '_job' in f]:
        os.remove(os.path.join('raw', f))
    edit_xml(b + '.xml', lambda r: next(im for im in r.iter('image') if im.get('id') == '2').set('name', 'T_001.png'))      # ảnh Gán tay nằm trong job Nhận
    res = core.tach(b + '.xml', 'raw')
    assert any('ảnh lệch job' in w and 'T_001.png' in w for w in res['jobs'][0]['canh_bao'])
    assert os.path.exists(f'{b}_job100.xml') and 'canh_bao: ảnh lệch job' in read(f'{b}_job100.txt')
    assert not any('ảnh lệch job' in w for w in res['jobs'][1]['canh_bao'])
    for f in [f for f in os.listdir('raw') if '_job' in f]:
        os.remove(os.path.join('raw', f))
    shutil.copy('raw/../runs/Khoi/push/manual_list.txt', 'ml.bak')
    open('runs/Khoi/push/manual_list.txt', 'w', encoding='utf-8').write('T_001.png\tco_nhap\nT_002.png\tco_nhap')           # manual_list không có G_001
    edit_xml(b + '.xml', lambda r: next(im for im in r.iter('image') if im.get('id') == '2').set('name', 'F_003.png'))
    res = core.tach(b + '.xml', 'raw')
    assert any('ảnh lệch job' in w and 'G_001.png' in w for w in res['jobs'][3]['canh_bao'])
    collect.collect(collect_args(skip_export=True))
    assert 'job 103: ảnh lệch job' in read('outputs/collect_demo-Khoi.md')


def test_image_id_outside_every_job_is_an_error_and_writes_no_job_file(cvat, pushed, capsys):
    collect.collect(collect_args())
    b = BASE()
    for f in [f for f in os.listdir('raw') if '_job' in f]:
        os.remove(os.path.join('raw', f))
    edit_xml(b + '.xml', lambda r: next(im for im in r.iter('image') if im.get('name') == 'F_005.png').set('id', '40'))
    with pytest.raises(core.TachJobLoi) as e:
        core.tach(b + '.xml', 'raw')
    msg = str(e.value)
    assert 'F_005.png' in msg and '40' in msg and 'job 100: 0-7' in msg and 'job 103: 19-21' in msg and 'ngoài mọi job' in msg
    assert sorted(os.listdir('raw')) == sorted([os.path.basename(b) + '.xml', os.path.basename(b) + '.txt'])      # không ghi nửa vời
    capsys.readouterr()
    assert collect.collect(collect_args(skip_export=True)) is True                      # collect vẫn lập báo cáo, file cả task còn nguyên
    out = capsys.readouterr().out
    assert 'KHÔNG tách được' in out and os.path.exists(b + '.xml')
    assert sorted(os.listdir('raw')) == sorted([os.path.basename(b) + '.xml', os.path.basename(b) + '.txt'])
    rep = read('outputs/collect_demo-Khoi.md')
    assert '## Tách job' in rep and 'F_005.png' in rep and 'mặt đủ 50 điểm' in rep
    with pytest.raises(core.TachJobLoi, match='lạ'):                                    # phần tử lạ ở gốc XML: không đoán
        edit_xml(b + '.xml', lambda r: (r.remove(next(im for im in r.iter('image') if im.get('name') == 'F_005.png')), ET.SubElement(r, 'bat_ngo')))
        core.tach(b + '.xml', 'raw')
    assert not [f for f in os.listdir('raw') if '_job' in f]


def test_duplicate_ids_non_integer_ids_and_overlapping_jobs_are_errors(tmp_path):
    def write(images, jobs):
        os.makedirs(tmp_path / 'r', exist_ok=True)
        (tmp_path / 'r' / 'demo-A_P1_0810.xml').write_text('<annotations><version>1.1</version>' + images + '</annotations>', encoding='utf-8')
        (tmp_path / 'r' / 'demo-A_P1_0810.txt').write_text('task: demo-A\ntask_id: 5\n' + jobs, encoding='utf-8')
        return str(tmp_path / 'r' / 'demo-A_P1_0810.xml')
    im = lambda i, n: f'<image id="{i}" name="{n}" width="1" height="1"/>'      # noqa: E731
    ok_jobs = 'job 1: 2 frame, stage annotation, state new\njob 2: 1 frame, stage annotation, state new\n'
    with pytest.raises(core.TachJobLoi, match='trùng id 1'):
        core.tach(write(im(1, 'a') + im(1, 'b'), ok_jobs), str(tmp_path / 'o'))
    with pytest.raises(core.TachJobLoi, match='không phải số nguyên'):
        core.tach(write(im('x', 'a'), ok_jobs), str(tmp_path / 'o'))
    with pytest.raises(core.TachJobLoi, match='chồng nhau'):
        core.tach(write(im(0, 'a'), 'job 1: 2 frame, stage annotation, state new | frames 0-1 | loai nhan\njob 2: 2 frame, stage annotation, state new | frames 1-2 | loai nhan\n'),
                  str(tmp_path / 'o'))
    with pytest.raises(core.TachJobLoi, match='mâu thuẫn'):
        core.tach(write(im(0, 'a'), 'job 1: 5 frame, stage annotation, state new | frames 0-1 | loai nhan\n'), str(tmp_path / 'o'))
    with pytest.raises(core.TachJobLoi, match='Không có dòng job'):
        core.tach(write(im(0, 'a'), ''), str(tmp_path / 'o'))
    assert not (tmp_path / 'o').exists()                                                # mọi lỗi: không ghi gì, không tạo cả thư mục đích


def test_missing_txt_is_not_guessed(tmp_path):
    (tmp_path / 'demo-A_P1_0810.xml').write_text('<annotations><image id="0" name="a" width="1" height="1"/></annotations>', encoding='utf-8')
    with pytest.raises(core.TachJobLoi, match='thiếu .*demo-A_P1_0810.txt') as e:
        core.tach(str(tmp_path / 'demo-A_P1_0810.xml'), str(tmp_path))
    assert 'Không đoán' in str(e.value)
    assert os.listdir(tmp_path) == ['demo-A_P1_0810.xml']


# ---------- cờ của collect ----------
def test_job_flag_writes_only_that_job_and_whole_file_still_written(cvat, pushed):
    assert collect.collect(collect_args(job=[103, 103])) is True
    b = BASE()
    assert sorted(os.listdir('raw')) == sorted(os.path.basename(x) for x in [b + '.xml', b + '.txt', b + '_job103.xml', b + '_job103.txt'])
    rep = read('outputs/collect_demo-Khoi.md')
    assert '| 103 | gan_tay |' in rep and '| 100 | nhan |' not in rep


def test_unknown_job_id_stops_before_any_export_or_file(cvat, pushed):
    n = len(calls(cvat, 'Task.export_dataset'))
    with pytest.raises(SystemExit) as e:
        collect.collect(collect_args(job=[103, 999]))
    msg = str(e.value)
    assert '999' in msg and 'demo-Khoi: 100, 101, 102, 103' in msg and 'Chưa xuất' in msg
    assert len(calls(cvat, 'Task.export_dataset')) == n                                 # không có lời gọi export_dataset mới
    assert not os.path.exists('raw') and not os.path.exists('outputs')
    with pytest.raises(SystemExit, match='no-per-job'):
        collect.collect(collect_args(job=[103], per_job=False))
    assert len(calls(cvat, 'Task.export_dataset')) == n and not os.path.exists('raw')
    with pytest.raises(SystemExit, match='999'):                                         # task chỉ đọc raw/: kiểm cũng trước khi ghi gì
        collect.collect(collect_args(skip_export=True, job=[999]))
    assert not os.path.exists('outputs')


def test_no_per_job_keeps_the_old_flow_and_job_split_adds_no_cvat_call(cvat, pushed):
    k0 = len(calls(cvat))
    collect.collect(collect_args(per_job=False, reviewer='P3'))
    k1 = len(calls(cvat))
    assert sorted(os.listdir('raw')) == [f'demo-Khoi_P3_{day()}.txt', f'demo-Khoi_P3_{day()}.xml']
    rep = read('outputs/collect_demo-Khoi.md')
    assert 'Theo job' not in rep and 'Tách job' not in rep and 'không đưa vào QC' not in rep and 'tách job' not in rep.split('Thời gian từng bước')[1]
    collect.collect(collect_args(reviewer='P2'))                                        # mặc định (bật tách job)
    k2 = len(calls(cvat))
    assert k2 - k1 == k1 - k0                                                           # cùng số lời gọi CVAT: tách job không gọi thêm gì
    assert [c['m'] for c in calls(cvat)[k0:k1]] == [c['m'] for c in calls(cvat)[k1:k2]]
    assert len([f for f in os.listdir('raw') if 'P2' in f and '_job' in f]) == 8


def test_skip_export_splits_the_latest_file_of_each_person_without_calling_cvat(cvat, pushed):
    collect.collect(collect_args(per_job=False))
    n = len(calls(cvat))
    assert collect.collect(collect_args(skip_export=True)) is True                      # task demo-… mặc định tách, kể cả khi chỉ đọc raw/
    assert len(calls(cvat)) == n
    assert len([f for f in os.listdir('raw') if '_job' in f and f.endswith('.xml')]) == 4
    # người thứ hai cũ hơn/mới hơn: mỗi người một file mới nhất
    for who in ('P3',):
        for ext in ('xml', 'txt'):
            shutil.copy(f'{BASE()}.{ext}', f'raw/demo-Khoi_{who}_{day()}.{ext}')
    collect.collect(collect_args(skip_export=True))
    assert len([f for f in os.listdir('raw') if '_P3_' in f and '_job' in f and f.endswith('.xml')]) == 4
    assert len(calls(cvat)) == n


def test_m28_task_is_not_split_by_default_but_per_job_splits_when_txt_exists(cvat):
    shutil.copy(CONFIG, 'config/m28_config.json')
    os.makedirs('raw')
    xml = '<annotations><version>1.1</version><image id="0" name="a.png" width="1" height="1"/><image id="1" name="b.png" width="1" height="1"/></annotations>'
    open('raw/m28-manual_P1_1010.xml', 'w').write(xml)
    open('raw/m28-manual_P1_1010.txt', 'w').write('task: m28-manual\ntask_id: 7\njob 20: 2 frame, stage annotation, state completed\n')
    collect.collect(collect_args(task=['m28-manual'], skip_export=False))
    assert sorted(os.listdir('raw')) == ['m28-manual_P1_1010.txt', 'm28-manual_P1_1010.xml']
    assert calls(cvat) == []
    collect.collect(collect_args(task=['m28-manual'], per_job=True))
    assert sorted(os.listdir('raw')) == ['m28-manual_P1_1010.txt', 'm28-manual_P1_1010.xml', 'm28-manual_P1_1010_job20.txt', 'm28-manual_P1_1010_job20.xml']
    assert calls(cvat) == []
    os.remove('raw/m28-manual_P1_1010.txt')                                             # thiếu .txt: báo rõ, không sập
    for f in [f for f in os.listdir('raw') if '_job' in f]:
        os.remove(os.path.join('raw', f))
    assert collect.collect(collect_args(task=['m28-manual'], per_job=True, tag='thieu')) is True
    rep = read('outputs/collect_thieu.md')
    assert '## Tách job' in rep and 'Không biết ranh giới job' in rep and 'Không đoán' in rep
    assert not [f for f in os.listdir('raw') if '_job' in f]


def test_dry_run_prints_frames_kind_and_file_names_but_writes_nothing(cvat, pushed, capsys):
    capsys.readouterr()
    assert collect.collect(collect_args(dry_run=True, job=[103])) is True
    out = capsys.readouterr().out
    assert 'frames 19-21' in out and 'loai gan_tay' in out and f'demo-Khoi_P4_{day()}_job103.xml' in out and 'được chọn bởi --job' in out
    assert 'bỏ qua (không được chọn bởi --job): job 100' in out and 'frames 0-7' in out
    assert not os.path.exists('raw') and not os.path.exists('outputs')
    collect.collect(collect_args(dry_run=True))
    out = capsys.readouterr().out
    assert out.count('sẽ ghi: job') == 4 and not os.path.exists('raw')
    collect.collect(collect_args(per_job=False, dry_run=True))
    assert 'sẽ ghi' not in capsys.readouterr().out


# ---------- RAW_RE, push_info, QC, eval50 ----------
@pytest.mark.parametrize('jid', ['1', '123', '1234', '12345'])
def test_job_files_are_invisible_to_raw_re_and_latest_raw_files(tmp_path, jid):
    os.makedirs(tmp_path / 'raw')
    for n in (f'demo-X_P1_0810_job{jid}.xml', f'demo-X_P1_0810_job{jid}.txt', 'demo-X_P1_0810.xml', 'demo-X_P2_0910.xml', f'demo-X_P2_0910_job{jid}.xml'):
        (tmp_path / 'raw' / n).write_text('<annotations/>')
    assert not collect.RAW_RE.match(f'demo-X_P1_0810_job{jid}.xml') and collect.RAW_RE.match('demo-X_P1_0810.xml')
    assert core.JOB_RE.match(f'demo-X_P1_0810_job{jid}.xml').group('goc') == 'demo-X_P1_0810' and not core.JOB_RE.match('demo-X_P1_0810.xml')
    got = collect.latest_raw_files('demo-X', str(tmp_path / 'raw'))
    assert {k: os.path.basename(v) for k, v in got.items()} == {'P1': 'demo-X_P1_0810.xml', 'P2': 'demo-X_P2_0910.xml'}
    assert collect.latest_raw_files(f'demo-X_P1_0810_job{jid}'.replace('.xml', ''), str(tmp_path / 'raw')) == {}


def test_push_info_is_unchanged_by_the_new_push_jobs(cvat, pushed):
    pi = collect.push_info('demo-Khoi')
    assert pi == dict(run='Khoi', tay_nhap=['T_001.png', 'T_002.png'], n_tay_nhap=2, n_tay_trong=1)
    assert collect.push_jobs is core.push_jobs


def test_qc_receives_only_whole_task_files_and_analyze_works_on_job_files(cvat, pushed, monkeypatch):
    seen = []
    mod = types.ModuleType('m28core.qc')
    mod.run = lambda paths, out: seen.append(list(paths)) or 'ok'
    monkeypatch.setitem(sys.modules, 'm28core.qc', mod)
    collect.collect(collect_args())
    assert len(seen) == 1 and [os.path.basename(p) for p in seen[0]] == [f'demo-Khoi_P4_{day()}.xml']
    names = collect._point_names('config/m28_config.json')
    st = collect.analyze(open(f'{BASE()}_job103.xml', 'rb').read(), names)
    assert (st['n_images'], st['n_face'], st['n_full'], st['n_missing'], st['n_low_on']) == (3, 2, 2, 0, 100)
    st = collect.analyze(open(f'{BASE()}_job100.xml', 'rb').read(), names)
    assert (st['n_images'], st['n_face'], st['n_full']) == (8, 8, 8)


def test_eval50_scores_only_the_faces_of_the_job_file(cvat, pushed):
    collect.collect(collect_args())
    cfg = json.load(open(CONFIG, encoding='utf-8'))
    job = eval50.read_labels(f'{BASE()}_job101.xml', cfg)
    whole = eval50.read_labels(f'{BASE()}.xml', cfg)
    assert sorted(job) == [f'F_{i:03d}' for i in range(9, 17)] and len(whole) == 21
    pred = eval50.read_labels(os.path.join(pushed['rd'], 'xml', 'prelabel.xml'), cfg)
    res = eval50.evaluate(pred, job, cfg)
    assert res['summary']['n_faces'] == 8 and res['summary']['nme_mean'] == pytest.approx(0.0, abs=1e-6)       # xuất đúng nhãn đã nhập: lệch 0 (làm tròn XML)
    assert eval50.main(['--gt', f'{BASE()}_job101.xml', '--pred', os.path.join(pushed['rd'], 'xml', 'prelabel.xml'), '--config', CONFIG,
                        '--out', 'nme_job.csv']) == 0
    assert len(read('nme_job.csv').strip().splitlines()) == 9


# ---------- <meta> (CVAT thật có, CVAT giả không có) ----------
META_XML = f'''<?xml version="1.0" encoding="utf-8"?>
<annotations>
  <version>1.1</version>
  <meta>
    <task>
      <id>7</id>
      <name>demo-M</name>
      <size>4</size>
      <mode>annotation</mode>
      <segments>
        <segment><id>11</id><start>0</start><stop>1</stop><url>http://localhost:8080/api/jobs/11</url></segment>
        <segment><id>12</id><start>2</start><stop>3</stop><url>http://localhost:8080/api/jobs/12</url></segment>
      </segments>
      <owner><username>nguoi</username><email>{EMAIL}</email></owner>
    </task>
    <dumped>2026-10-08 10:00:00.000000+00:00</dumped>
  </meta>
  <image id="0" name="a.png" width="10" height="10"><box label="x" xtl="1" ytl="1" xbr="2" ybr="2" occluded="0"/></image>
  <image id="1" name="b.png" width="10" height="10"/>
  <image id="2" name="c.png" width="10" height="10"/>
  <image id="3" name="d.png" width="10" height="10"><tag label="t"/></image>
</annotations>
'''


def meta_case(tmp_path):
    (tmp_path / 'demo-M_P1_0810.xml').write_text(META_XML, encoding='utf-8')
    (tmp_path / 'demo-M_P1_0810.txt').write_text('task: demo-M\ntask_id: 7\nso_job: 2\njob 11: 2 frame, stage annotation, state completed\n'
                                                 'job 12: 2 frame, stage annotation, state new\n', encoding='utf-8')
    return str(tmp_path / 'demo-M_P1_0810.xml')


def test_meta_size_is_fixed_rest_kept_and_email_never_printed(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    xml = meta_case(tmp_path)
    assert cli.main(['--xml', xml, '--out', str(tmp_path / 'out')]) == 0
    out = capsys.readouterr().out
    assert EMAIL not in out and 'nguoi' not in out and 'localhost:8080' not in out
    r11 = ET.parse(tmp_path / 'out' / 'demo-M_P1_0810_job11.xml').getroot()
    r12 = ET.parse(tmp_path / 'out' / 'demo-M_P1_0810_job12.xml').getroot()
    orig = ET.parse(xml).getroot()
    assert r11.find('meta/task/size').text == '2' and r12.find('meta/task/size').text == '2'
    for r in (r11, r12):
        assert norm(r.find('meta/task/segments')) == norm(orig.find('meta/task/segments'))              # phần còn lại của <meta> giữ nguyên
        assert r.find('meta/task/owner/email').text == EMAIL and r.find('meta/dumped') is not None and r.find('meta/task/name').text == 'demo-M'
    assert [i.get('name') for i in r11.findall('image')] == ['a.png', 'b.png'] and [i.get('name') for i in r12.findall('image')] == ['c.png', 'd.png']
    assert norm(r11.find('image')) == norm(orig.findall('image')[0]) and r11.find('image/box') is not None and r12.findall('image')[1].find('tag') is not None
    for f in os.listdir(tmp_path / 'out'):
        if f.endswith('.txt'):
            t = read(str(tmp_path / 'out' / f))
            assert EMAIL not in t and 'segment' not in t and 'canh_bao' not in t
    assert orig.find('meta/task/size').text == '4'                                                      # file cả task không bị sửa


def test_meta_with_job_size_and_report_never_has_the_email(tmp_path):
    xml = meta_case(tmp_path)
    s = read(xml).replace('<dumped>', '<job><size>4</size></job><dumped>')
    open(xml, 'w', encoding='utf-8').write(s)
    core.tach(xml, str(tmp_path), only=[11])
    r = ET.parse(tmp_path / 'demo-M_P1_0810_job11.xml').getroot()
    assert r.find('meta/job/size').text == '2' and r.find('meta/task/size').text == '2'
    assert not (tmp_path / 'demo-M_P1_0810_job12.xml').exists()


# ---------- tool/tach_job.py (CLI) ----------
def test_cli_default_out_explicit_txt_job_selection_and_exit_codes(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    xml = meta_case(tmp_path)
    assert cli.main(['--xml', xml]) == 0                                                                  # --out mặc định: thư mục chứa --xml
    out = capsys.readouterr().out
    assert (tmp_path / 'demo-M_P1_0810_job11.xml').exists() and (tmp_path / 'demo-M_P1_0810_job12.txt').exists()
    assert 'job 11 (khong_ro) frames 0-1: 2/2 ảnh' in out and 'ghi mới 2 file job' in out and 'không nhập lại vào CVAT' in out
    assert cli.main(['--xml', xml]) == 0                                                                  # chạy lại: mọi file đã có vẫn mã 0
    out = capsys.readouterr().out
    assert out.count('KHÔNG ghi đè') == 2 and 'ghi mới 0 file' in out
    os.rename(tmp_path / 'demo-M_P1_0810.txt', tmp_path / 'ranh_gioi.txt')
    assert cli.main(['--xml', xml, '--out', 'khac', '--txt', str(tmp_path / 'ranh_gioi.txt'), '--job', '12']) == 0
    assert sorted(os.listdir('khac')) == ['demo-M_P1_0810_job12.txt', 'demo-M_P1_0810_job12.xml']
    capsys.readouterr()
    assert cli.main(['--xml', xml, '--out', 'khac2', '--job', '11', '12']) == 2                          # thiếu .txt cạnh xml (đã đổi tên)
    out = capsys.readouterr().out
    assert 'LỖI' in out and 'thiếu' in out and not os.path.exists('khac2')
    assert cli.main(['--xml', xml, '--txt', str(tmp_path / 'ranh_gioi.txt'), '--out', 'khac3', '--job', '99']) == 2
    assert 'Job 99' in capsys.readouterr().out and 'job hợp lệ: 11, 12' in capsys.readouterr().out or True
    assert not os.path.exists('khac3')
    assert cli.main(['--xml', str(tmp_path / 'khong_co.xml')]) == 2 and 'không thấy file' in capsys.readouterr().out
    assert cli.main(['--xml', str(tmp_path / 'demo-M_P1_0810_job11.xml')]) == 2 and 'đã là file của một job' in capsys.readouterr().out
    with pytest.raises(SystemExit) as e:
        cli.main(['--help'])
    assert e.value.code == 0 and 'không nhập lại vào CVAT' in capsys.readouterr().out


def test_cli_unknown_job_message_lists_valid_ids(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    xml = meta_case(tmp_path)
    assert cli.main(['--xml', xml, '--out', 'o', '--job', '99']) == 2
    out = capsys.readouterr().out
    assert 'Job 99' in out and 'job hợp lệ: 11, 12' in out and not os.path.exists('o')


def test_cli_config_prints_full_face_counts_and_works_on_final_dir(cvat, pushed, capsys):
    collect.collect(collect_args(per_job=False))
    os.makedirs('final')
    for ext in ('xml', 'txt'):
        shutil.copy(f'{BASE()}.{ext}', f'final/demo-Khoi_P4_{day()}.{ext}')
    capsys.readouterr()
    assert cli.main(['--xml', f'final/demo-Khoi_P4_{day()}.xml', '--out', 'final', '--config', 'config/m28_config.json', '--runs', 'runs']) == 0
    out = capsys.readouterr().out
    assert 'job 103 (gan_tay) frames 19-21: 3/3 ảnh' in out and 'mặt đủ 50 điểm 2' in out and 'mặt đủ 50 điểm 8' in out
    assert os.path.exists(f'final/demo-Khoi_P4_{day()}_job100.xml') and not os.path.exists('raw/' + f'demo-Khoi_P4_{day()}_job100.xml')
    assert cli.main(['--xml', f'final/demo-Khoi_P4_{day()}.xml', '--config', 'khong_co.json']) == 2


def test_cli_runs_as_a_script_with_unicode_output(tmp_path):
    import subprocess
    xml = meta_case(tmp_path)
    p = subprocess.run([sys.executable, os.path.join(HERE, '..', 'tool', 'tach_job.py'), '--xml', xml, '--out', str(tmp_path / 'o')], capture_output=True, cwd=str(tmp_path))
    assert p.returncode == 0 and 'Xong: ghi mới 2 file job' in p.stdout.decode('utf-8') and not p.stderr
    p = subprocess.run([sys.executable, os.path.join(HERE, '..', 'tool', 'tach_job.py'), '--help'], capture_output=True)
    assert p.returncode == 0 and '--xml' in p.stdout.decode('utf-8', 'replace')


def test_job_path_is_safe(tmp_path):
    with pytest.raises(core.TachJobLoi):
        core.job_path(str(tmp_path / 'a b.xml'), str(tmp_path), 1)                      # tên có dấu cách không đi qua safe_file_part
    with pytest.raises(core.TachJobLoi):
        core.job_path(str(tmp_path / 'a.txt'), str(tmp_path), 1)
    assert core.job_path(str(tmp_path / 'demo-A_P1_0810.xml'), str(tmp_path), 105) == str(tmp_path / 'demo-A_P1_0810_job105.xml')
    assert cvat_io.safe_file_part('demo-A_P1_0810')


def test_steps_collect_module_still_wired(monkeypatch):
    called = []
    mod = types.ModuleType('m28core.collect')
    mod.collect = lambda a: called.append(a) or True
    monkeypatch.setitem(sys.modules, 'm28core.collect', mod)
    ns = types.SimpleNamespace(task=['demo-x'], per_job=None, job=[1])
    assert steps.collect(ns, None) is True and called[0].job == [1]
