"""Thử m28core/push.py, collect.py và xoá task bằng một CVAT GIẢ: gói `cvat_sdk` giả ở tests/fake_cvat/cvat_sdk/.

Cách chọn (ghi rõ vì không có CVAT thật trên cloud): gói giả giữ "server" trong bộ nhớ (hoặc trong file nếu có biến
M28_FAKE_CVAT_STATE, dùng cho e2e xuyên tiến trình), ghi lại MỌI lời gọi, giả lỗi theo lệnh, và xuất zip annotations.xml từ XML đã
nhập. pytest đưa gói giả vào bằng monkeypatch (sys.path + sys.modules); không có móc test nào trong mã sản phẩm.
Gói giả bám mã nguồn CVAT v2.77.0 (job_file_mapping xếp frame theo thứ tự mapping, không dùng sorting_method/segment_size).
test_signatures_match_real_sdk so từng lời gọi đã ghi với chữ ký của cvat-sdk THẬT (nếu import được).

Kết quả đây CHỨNG MINH logic an toàn (không đụng task lạ, không đẩy hai lần, không nhập hai lần, xoá đúng id) nhưng KHÔNG chứng minh
CVAT thật nhận định dạng label skeleton, job_file_mapping hay XML nhập: việc đó chỉ kiểm được khi có server (xem README, mục Rủi ro).
"""
import csv
import inspect
import json
import os
import sys
import types
import zipfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, '..', 'tool')
FAKE = os.path.join(HERE, 'fake_cvat')
sys.path.insert(0, TOOL)
from m28core import cvat_io, dang_chay, push as pushmod  # noqa: E402
from m28core import steps  # noqa: E402

TOKEN = 'TOKEN-GIA-zq81xk-DAY-LA-CHUOI-NHAN-DIEN'
URL = 'http://localhost:8080'
REAL_LABEL = os.path.join(HERE, '..', 'config', 'face50_label.json')


def _purge():
    return {k: sys.modules.pop(k) for k in list(sys.modules) if k == 'cvat_sdk' or k.startswith('cvat_sdk.')}


@pytest.fixture
def cvat(tmp_path, monkeypatch):
    """Chạy trong thư mục tạm có config/ (label, pipeline), env CVAT giả, gói cvat_sdk giả; trả module giả."""
    monkeypatch.chdir(tmp_path)
    os.makedirs('config')
    with open(REAL_LABEL, encoding='utf-8') as f, open('config/face50_label.json', 'w', encoding='utf-8') as g:
        g.write(f.read())
    json.dump(dict(project='m28', prefix='demo-', cvat_version='2.77.0', job_size=8), open('config/pipeline.json', 'w'))
    monkeypatch.setenv('CVAT_URL', URL)
    monkeypatch.setenv('CVAT_ACCESS_TOKEN', TOKEN)
    monkeypatch.delenv('CVAT_ORG', raising=False)
    monkeypatch.delenv('M28_FAKE_CVAT_STATE', raising=False)
    monkeypatch.delenv('M28_FAKE_CVAT_CONTROL', raising=False)
    saved = _purge()
    monkeypatch.syspath_prepend(FAKE)
    import cvat_sdk
    cvat_sdk.reset()
    yield cvat_sdk
    _purge()
    sys.modules.update(saved)


def point_names():
    return [s['name'] for s in json.load(open('config/face50_label.json', encoding='utf-8'))[0]['sublabels']]


def make_run(run='Khoi', n_nhan=19, n_tay=3, reverse=False):
    """runs/<run>/ có ảnh giả và XML nháp (id 0..n-1 theo thứ tự Nhận). Trả dict(rd, nhan, tay, xml)."""
    rd = os.path.join('runs', run)
    os.makedirs(os.path.join(rd, 'imgs'), exist_ok=True)
    nhan = [os.path.join(rd, 'imgs', f'F_{i:03d}.png') for i in range(1, n_nhan + 1)]
    tay = [os.path.join(rd, 'imgs', f'G_{i:03d}.png') for i in range(1, n_tay + 1)]
    for p in nhan + tay:
        open(p, 'wb').write(b'x')
    if reverse:
        nhan.reverse()                                               # thứ tự Nhận khác thứ tự theo tên file
    names = point_names()
    parts = ['<?xml version="1.0" encoding="utf-8"?>', '<annotations>', '  <version>1.1</version>']
    for i, p in enumerate(nhan):
        parts.append(steps.image_xml(i, os.path.basename(p), names, [(i + k, k) for k in range(50)], [k % 7 == 0 for k in range(50)], 512, 512))
    parts.append('</annotations>')
    xml = os.path.join(rd, 'xml', 'prelabel.xml')
    os.makedirs(os.path.dirname(xml), exist_ok=True)
    open(xml, 'w', encoding='utf-8').write('\n'.join(parts))
    return dict(rd=rd, nhan=nhan, tay=tay, xml=xml)


def do_push(w, name='demo-Khoi', **kw):
    return pushmod.push(w['rd'], name, w['nhan'], w['tay'], w['xml'], **kw)


def spec_of(c):
    """spec của tasks.create_from_data (push gọi bằng từ khoá spec=)."""
    return c['kwargs'].get('spec', c['args'][0] if c['args'] else None)


def resources_of(c):
    return c['kwargs'].get('resources', c['args'][1] if len(c['args']) > 1 else None)


def calls(cvat, method=None):
    cs = cvat.calls()
    return [c for c in cs if method is None or c['m'] == method]


def pj(w):
    return json.load(open(os.path.join(w['rd'], 'push.json'), encoding='utf-8'))


def state(cvat):
    return cvat.load()


# ---------- an toàn: không đụng task không có prefix demo- ----------
def test_unsafe_names_rejected_before_any_cvat_call(cvat):
    w = make_run()
    for task, prefix in (('m28-gold', 'demo-'), ('demo-x', 'm28-'), ('m28-gold', 'm28-'), ('x', ''), ('demo-x', ''), ('Demo-x', 'demo-')):
        with pytest.raises(SystemExit):
            do_push(w, task, prefix=prefix)
    for bad in ('demo-', 'demo-a\nb', 'demo-' + 'x' * 200):
        with pytest.raises(SystemExit):
            do_push(w, bad)
    assert calls(cvat) == [] and not os.path.exists(os.path.join(w['rd'], 'push.json'))


def test_never_touches_foreign_tasks(cvat):
    w = make_run()
    st = state(cvat)
    st['projects'].append(dict(id=1, name='m28', labels=[dict(name='face50', type='skeleton', sublabels=[dict(name=n) for n in point_names()])]))
    st['next_project'] = 2
    st['tasks'].append(dict(id=77, name='m28-gold', project_id=1, frames=['g.png'], jobs=[], annotations=None, files=[],
                            created='2026-10-01T00:00:00+00:00'))
    st['next_task'] = 78
    do_push(w)
    pushmod.delete_task(w['rd'], confirm_name='demo-Khoi')
    for c in calls(cvat):
        if c['m'] in ('tasks.retrieve', 'tasks.remove_by_ids'):
            assert 77 not in (c['args'][0] if isinstance(c['args'][0], list) else [c['args'][0]])
        if c['m'] == 'tasks.create_from_data':
            assert spec_of(c)['name'].startswith('demo-')
    assert [t['name'] for t in state(cvat)['tasks']] == ['m28-gold']                  # task lạ còn nguyên
    assert len(calls(cvat, 'Task.remove')) == 1


def test_second_push_refused_without_new_task(cvat):
    w = make_run()
    do_push(w)
    n = len(calls(cvat, 'tasks.create_from_data'))
    with pytest.raises(SystemExit, match='đã đẩy'):
        do_push(w)
    assert len(calls(cvat, 'tasks.create_from_data')) == n == 1
    assert pj(w)['trang_thai'] == 'xong' and len(state(cvat)['tasks']) == 1


def test_import_exactly_once_on_happy_path(cvat):
    w = make_run()
    res = do_push(w)
    assert len(calls(cvat, 'Task.import_annotations')) == 1
    c = calls(cvat, 'Task.import_annotations')[0]
    assert c['args'][0] == 'CVAT 1.1'
    assert len(calls(cvat, 'Task.export_dataset')) == 1
    e = calls(cvat, 'Task.export_dataset')[0]
    assert e['args'][0] == 'CVAT for images 1.1' and e['kwargs']['include_images'] is False
    assert res == os.path.join(w['rd'], 'check.zip') and os.path.exists(res)
    st = pj(w)
    assert st['trang_thai'] == 'xong' and st['check']['ok'] and st['check']['n_day_du'] == 19
    assert st['task_url'] == f"{URL}/tasks/{st['task_id']}"


def test_create_from_data_arguments(cvat):
    w = make_run()
    do_push(w)
    c = calls(cvat, 'tasks.create_from_data')[0]
    assert spec_of(c) == {'name': 'demo-Khoi', 'project_id': 1}                      # không truyền labels
    assert 'labels' not in spec_of(c)
    assert c['kwargs']['resource_type'] == 'local'
    dp = c['kwargs']['data_params']
    assert dp['image_quality'] == 95 and dp['use_cache'] is True
    assert set(dp) == {'image_quality', 'use_cache', 'job_file_mapping'}              # không sorting_method/segment_size/annotation_path
    assert 'annotation_path' not in c['kwargs']
    assert resources_of(c) == w['nhan'] + w['tay']


def test_job_mapping_19_nhan_3_tay(cvat):
    w = make_run(n_nhan=19, n_tay=3)
    do_push(w)
    dp = calls(cvat, 'tasks.create_from_data')[0]['kwargs']['data_params']
    assert [len(g) for g in dp['job_file_mapping']] == [8, 8, 3, 3]
    assert dp['job_file_mapping'][-1] == [os.path.basename(p) for p in w['tay']]       # Gán tay một job riêng, ở cuối
    jobs = pj(w)['jobs']
    assert [(j['kind'], j['n']) for j in jobs] == [('nhan', 8), ('nhan', 8), ('nhan', 3), ('gan_tay', 3)]
    assert 'canh_bao' not in pj(w)


def test_no_empty_job_without_gan_tay(cvat):
    w = make_run(n_nhan=16, n_tay=0)
    do_push(w)
    dp = calls(cvat, 'tasks.create_from_data')[0]['kwargs']['data_params']
    assert [len(g) for g in dp['job_file_mapping']] == [8, 8]
    assert all(dp['job_file_mapping'])
    assert [j['kind'] for j in pj(w)['jobs']] == ['nhan', 'nhan']


def test_only_gan_tay_has_no_import(cvat):
    w = make_run(n_nhan=0, n_tay=4)
    do_push(w)
    assert calls(cvat, 'Task.import_annotations') == []
    assert pj(w)['trang_thai'] == 'xong' and [j['kind'] for j in pj(w)['jobs']] == ['gan_tay']


def test_job_size_from_pipeline(cvat):
    w = make_run(n_nhan=10, n_tay=1)
    json.dump(dict(project='m28', prefix='demo-', cvat_version='2.77.0', job_size=4), open('config/pipeline.json', 'w'))
    do_push(w)
    dp = calls(cvat, 'tasks.create_from_data')[0]['kwargs']['data_params']
    assert [len(g) for g in dp['job_file_mapping']] == [4, 4, 2, 1]


# ---------- thứ tự frame ----------
def test_xml_ids_rewritten_when_server_orders_frames_differently(cvat, monkeypatch):
    monkeypatch.setenv('M28_FAKE_CVAT_CONTROL', json.dumps({'frames_by_name': True}))
    w = make_run(n_nhan=3, n_tay=0, reverse=True)                  # XML: F_003 id 0, F_002 id 1, F_001 id 2
    do_push(w)
    used = calls(cvat, 'Task.import_annotations')[0]['args'][1]
    assert used.endswith('prelabel_cvat.xml')
    import xml.etree.ElementTree as ET
    ids = {im.get('name'): im.get('id') for im in ET.parse(used).getroot().iter('image')}
    assert ids == {'F_001.png': '0', 'F_002.png': '1', 'F_003.png': '2'}               # id theo frame thật (server xếp theo tên), ghép theo tên
    assert pj(w)['trang_thai'] == 'xong'
    orig = {im.get('name'): im.get('id') for im in ET.parse(w['xml']).getroot().iter('image')}
    assert orig == {'F_003.png': '0', 'F_002.png': '1', 'F_001.png': '2'}              # prelabel.xml gốc không bị sửa


def test_original_xml_used_when_order_matches(cvat):
    w = make_run(n_nhan=3, n_tay=1)
    do_push(w)
    assert calls(cvat, 'Task.import_annotations')[0]['args'][1] == w['xml']
    assert not os.path.exists(os.path.join(w['rd'], 'xml', 'prelabel_cvat.xml'))


# ---------- lỗi giữa chừng, --resume, --cleanup ----------
def test_resume_after_import_failure(cvat, monkeypatch):
    monkeypatch.setenv('M28_FAKE_CVAT_CONTROL', json.dumps({'import_fail_times': 1}))
    w = make_run()
    with pytest.raises(SystemExit, match='500|nhập'):
        do_push(w)
    st = pj(w)
    assert st['trang_thai'] == 'da_tao' and st['loi'] and st['task_id'] == 1
    with pytest.raises(SystemExit, match='--resume'):
        do_push(w)                                                  # không tạo task thứ hai
    assert len(calls(cvat, 'tasks.create_from_data')) == 1
    do_push(w, resume=True)
    assert len(calls(cvat, 'tasks.create_from_data')) == 1 and len(state(cvat)['tasks']) == 1
    imps = calls(cvat, 'Task.import_annotations')
    assert len(imps) == 2                                           # lần 1 lỗi (không lưu), lần 2 (resume) thành công, đúng task đó
    assert pj(w)['trang_thai'] == 'xong' and 'loi' not in pj(w)
    with pytest.raises(SystemExit):
        do_push(w, resume=True)                                     # xong rồi thì --resume cũng từ chối
    assert len(calls(cvat, 'Task.import_annotations')) == 2


def test_resume_does_not_reimport_when_task_already_has_labels(cvat):
    w = make_run()
    do_push(w)
    st = pj(w)
    st['trang_thai'] = 'da_tao'                                     # giả: chết sau khi nhập, trước khi ghi da_nhap
    json.dump(st, open(os.path.join(w['rd'], 'push.json'), 'w'))
    n = len(calls(cvat, 'Task.import_annotations'))
    do_push(w, resume=True)
    assert len(calls(cvat, 'Task.import_annotations')) == n
    assert pj(w)['trang_thai'] == 'xong'


def test_resume_refuses_foreign_or_mismatched_task(cvat):
    w = make_run()
    with pytest.raises(SystemExit, match='--resume chỉ dùng'):
        do_push(w, resume=True)                                     # chưa có push.json
    do_push(w)
    st = pj(w)
    st.update(trang_thai='da_tao', task='demo-Khac')
    json.dump(st, open(os.path.join(w['rd'], 'push.json'), 'w'))
    with pytest.raises(SystemExit, match='đúng task'):
        do_push(w, resume=True)
    st.update(task='demo-Khoi', task_id=999)                        # id không có trên CVAT
    json.dump(st, open(os.path.join(w['rd'], 'push.json'), 'w'))
    with pytest.raises(SystemExit, match='404'):
        do_push(w, resume=True)
    assert calls(cvat, 'Task.remove') == []


def test_failed_check_keeps_task_and_records_reason(cvat, monkeypatch):
    monkeypatch.setenv('M28_FAKE_CVAT_CONTROL', json.dumps({'drop_point': True}))
    w = make_run(n_nhan=3, n_tay=1)
    with pytest.raises(SystemExit, match='KHÔNG đạt'):
        do_push(w)
    st = pj(w)
    assert st['trang_thai'] == 'da_nhap' and not st['check']['ok'] and st['check']['n_day_du'] == 2 and 'KHÔNG đạt' in st['loi']
    assert len(state(cvat)['tasks']) == 1 and calls(cvat, 'Task.remove') == []
    monkeypatch.setenv('M28_FAKE_CVAT_CONTROL', json.dumps({}))
    do_push(w, resume=True)                                         # da_nhap: không nhập lại, chỉ kiểm lại
    assert len(calls(cvat, 'Task.import_annotations')) == 1 and pj(w)['trang_thai'] == 'xong'


def test_dang_tao_state_blocks_and_cleanup_only_lists(cvat):
    w = make_run()
    do_push(w)
    st = pj(w)
    st['trang_thai'] = 'dang_tao'
    st.pop('task_id'), st.pop('jobs')
    json.dump(st, open(os.path.join(w['rd'], 'push.json'), 'w'))
    with pytest.raises(SystemExit, match='--cleanup'):
        do_push(w)
    assert len(calls(cvat, 'tasks.create_from_data')) == 1
    pushmod.cleanup(w['rd'])
    assert calls(cvat, 'Task.remove') == [] and calls(cvat, 'tasks.remove_by_ids') == []      # không tự xoá task nào
    assert len(state(cvat)['tasks']) == 1
    assert not os.path.exists(os.path.join(w['rd'], 'push.json'))


def test_cleanup_removes_exact_id_after_name_check(cvat):
    w = make_run()
    do_push(w)
    pushmod.cleanup(w['rd'], confirm_name='demo-Khoi')
    removes = calls(cvat, 'Task.remove')
    assert len(removes) == 1
    ret = calls(cvat, 'tasks.retrieve')
    assert [c['args'] for c in ret] == [[1]]                         # lấy lại ĐÚNG id trong push.json trước khi xoá
    assert state(cvat)['tasks'] == []
    assert pj(w)['trang_thai'] == 'task_deleted'


# ---------- project ----------
def test_project_created_once_from_label_json(cvat):
    w = make_run(n_nhan=2, n_tay=0)
    do_push(w)
    cr = calls(cvat, 'projects.create')
    assert len(cr) == 1
    spec = cr[0]['args'][0]
    assert spec['name'] == 'm28' and spec['labels'] == json.load(open('config/face50_label.json', encoding='utf-8'))
    w2 = make_run('Nam', 2, 0)
    do_push(w2, 'demo-Nam')
    assert len(calls(cvat, 'projects.create')) == 1                  # lần hai dùng lại project có sẵn
    assert len(state(cvat)['projects']) == 1


def test_two_projects_same_name_stop(cvat):
    w = make_run()
    st = state(cvat)
    st['projects'] += [dict(id=1, name='m28', labels=[]), dict(id=2, name='m28', labels=[])]
    with pytest.raises(SystemExit, match='2 project'):
        do_push(w)
    assert calls(cvat, 'tasks.create_from_data') == [] and not os.path.exists(os.path.join(w['rd'], 'push.json'))


def test_project_missing_sublabels_stops(cvat, monkeypatch):
    monkeypatch.setenv('M28_FAKE_CVAT_CONTROL', json.dumps({'project_missing_sublabels': 3}))
    w = make_run(n_nhan=2, n_tay=0)
    with pytest.raises(SystemExit, match='47 sublabel'):
        do_push(w)                                                  # project vừa tạo thiếu 3 điểm: dừng, chưa tạo task
    assert calls(cvat, 'tasks.create_from_data') == []


def test_project_without_face50_stops(cvat):
    w = make_run()
    state(cvat)['projects'].append(dict(id=1, name='m28', labels=[dict(name='car', type='rectangle')]))
    state(cvat)['next_project'] = 2
    with pytest.raises(SystemExit, match='chưa có label face50'):
        do_push(w)
    assert calls(cvat, 'tasks.create_from_data') == []


def test_same_name_task_in_project_stops(cvat):
    w = make_run(n_nhan=2, n_tay=0)
    do_push(w)
    os.remove(os.path.join(w['rd'], 'push.json'))                    # giả: mất push.json nhưng task còn
    with pytest.raises(SystemExit, match='đã có task tên demo-Khoi'):
        do_push(w)
    assert len(calls(cvat, 'tasks.create_from_data')) == 1


# ---------- môi trường, token, lỗi mạng ----------
def test_missing_env_messages_and_no_connect(cvat, monkeypatch, capsys):
    w = make_run()
    monkeypatch.delenv('CVAT_ACCESS_TOKEN')
    with pytest.raises(SystemExit, match='CVAT_ACCESS_TOKEN'):
        do_push(w)
    monkeypatch.setenv('CVAT_ACCESS_TOKEN', TOKEN)
    monkeypatch.delenv('CVAT_URL')
    with pytest.raises(SystemExit, match='CVAT_URL'):
        do_push(w)
    monkeypatch.setenv('CVAT_URL', 'localhost:8080')
    with pytest.raises(SystemExit, match='http://'):
        do_push(w)
    monkeypatch.setenv('CVAT_URL', 'http://user:pw@localhost:8080')
    with pytest.raises(SystemExit, match='tên đăng nhập'):
        do_push(w)
    assert calls(cvat) == [] and 'token: thiếu' in capsys.readouterr().out


def test_token_never_leaks(cvat, monkeypatch, capsys):
    w = make_run(n_nhan=3, n_tay=1)
    monkeypatch.setenv('M28_FAKE_CVAT_CONTROL', json.dumps({'import_fail_times': 1}))
    with pytest.raises(SystemExit) as e1:
        do_push(w)
    do_push(w, resume=True)
    pushmod.cleanup(w['rd'], confirm_name='demo-Khoi')
    out, err = capsys.readouterr()
    assert TOKEN not in out + err + str(e1.value)
    assert 'token: có' in out
    for root, _d, files in os.walk('.'):
        for fn in files:
            if fn.endswith(('.json', '.txt', '.xml', '.csv')):
                assert TOKEN not in open(os.path.join(root, fn), encoding='utf-8', errors='replace').read(), fn
    assert TOKEN not in json.dumps(calls(cvat))


def test_scrub_removes_token_forms():
    s = cvat_io.scrub(f'lỗi {TOKEN} và Authorization: Bearer abcdefghijklmnop12345', TOKEN)
    assert TOKEN not in s and 'abcdefghijklmnop12345' not in s


@pytest.mark.parametrize('control, match', [({'connect_fail': True}, 'Không kết nối được'), ({'auth_fail': True}, '401|token'),
                                            ({'version': '2.70.0'}, 'Bản server CVAT là 2.70.0')])
def test_errors_are_vietnamese_with_fix(cvat, monkeypatch, control, match, capsys):
    monkeypatch.setenv('M28_FAKE_CVAT_CONTROL', json.dumps(control))
    w = make_run(n_nhan=2, n_tay=0)
    with pytest.raises(SystemExit, match=match) as e:
        do_push(w)
    assert TOKEN not in str(e.value) and TOKEN not in ''.join(capsys.readouterr())
    assert calls(cvat, 'tasks.create_from_data') == []


def test_connect_error_mentions_docker_and_state_file_unchanged(cvat, monkeypatch):
    monkeypatch.setenv('M28_FAKE_CVAT_CONTROL', json.dumps({'connect_fail': True}))
    w = make_run(n_nhan=2, n_tay=0)
    with pytest.raises(SystemExit, match='docker compose up -d'):
        do_push(w)
    assert not os.path.exists(os.path.join(w['rd'], 'push.json'))


def test_cvat_org_sets_organization_slug(cvat, monkeypatch):
    monkeypatch.setenv('CVAT_ORG', 'congty')
    w = make_run(n_nhan=2, n_tay=0)
    do_push(w)
    assert [c['args'] for c in calls(cvat, 'Client.organization_slug')] == [['congty']]


def test_refuses_duplicate_basenames_and_missing_files(cvat):
    w = make_run(n_nhan=2, n_tay=1)
    os.makedirs('other', exist_ok=True)
    open('other/F_001.png', 'wb').write(b'x')
    with pytest.raises(SystemExit, match='trùng'):
        pushmod.push(w['rd'], 'demo-Khoi', w['nhan'] + ['other/F_001.png'], w['tay'], w['xml'])
    with pytest.raises(SystemExit, match='Không thấy'):
        pushmod.push(w['rd'], 'demo-Khoi', w['nhan'] + ['nope.png'], w['tay'], w['xml'])
    with pytest.raises(SystemExit, match='Không có ảnh'):
        pushmod.push(w['rd'], 'demo-Khoi', [], [], w['xml'])
    assert calls(cvat) == []


# ---------- xoá task (chính sách mạnh) ----------
def pj_write(w, **upd):
    st = pj(w)
    st.update(upd)
    json.dump(st, open(os.path.join(w['rd'], 'push.json'), 'w'))


def assert_not_deleted(cvat, w):
    assert calls(cvat, 'Task.remove') == [] and calls(cvat, 'tasks.remove_by_ids') == []
    assert len(state(cvat)['tasks']) == 1


def test_delete_refused_without_or_with_wrong_confirmation(cvat):
    w = make_run(n_nhan=3, n_tay=1)
    do_push(w)
    n_calls = len(calls(cvat))
    for typed in (None, '', 'demo-khoi', 'demo-Khoi ', 'Demo-Khoi', 'demo-Nam'):
        with pytest.raises(SystemExit, match='xác nhận'):
            pushmod.delete_task(w['rd'], confirm_name=typed)
    assert len(calls(cvat)) == n_calls                               # chưa kết nối, chưa gọi gì
    assert_not_deleted(cvat, w) and pj(w)['trang_thai'] == 'xong'


def test_delete_refused_when_task_name_has_no_prefix(cvat):
    w = make_run(n_nhan=3, n_tay=1)
    do_push(w)
    for bad in ('m28-gold', 'manual', 'xdemo-Khoi', ''):
        pj_write(w, task=bad)
        with pytest.raises(SystemExit, match='không bắt đầu'):
            pushmod.delete_task(w['rd'], confirm_name=bad)
    assert_not_deleted(cvat, w)
    with pytest.raises(SystemExit, match='prefix'):
        pushmod.delete_task(w['rd'], confirm_name='m28-gold', prefix='m28-')


def test_delete_refused_when_server_task_name_differs(cvat):
    w = make_run(n_nhan=3, n_tay=1)
    do_push(w)
    state(cvat)['tasks'][0]['name'] = 'demo-Nguoi-Khac'              # id này giờ thuộc task khác
    with pytest.raises(SystemExit, match='không khớp push.json'):
        pushmod.delete_task(w['rd'], confirm_name='demo-Khoi')
    assert_not_deleted(cvat, w) and pj(w)['trang_thai'] == 'xong'


def test_delete_refused_when_server_task_is_m28(cvat):
    w = make_run(n_nhan=3, n_tay=1)
    do_push(w)
    state(cvat)['tasks'][0]['name'] = 'm28-manual'
    pj_write(w, task='m28-manual')
    with pytest.raises(SystemExit):
        pushmod.delete_task(w['rd'], confirm_name='m28-manual')
    assert_not_deleted(cvat, w)


def test_delete_refused_when_task_not_in_project_or_other_server(cvat, monkeypatch):
    w = make_run(n_nhan=3, n_tay=1)
    do_push(w)
    state(cvat)['tasks'][0]['project_id'] = 99
    with pytest.raises(SystemExit, match='không thuộc project'):
        pushmod.delete_task(w['rd'], confirm_name='demo-Khoi')
    state(cvat)['tasks'][0]['project_id'] = 1
    monkeypatch.setenv('CVAT_URL', 'http://localhost:9999')
    with pytest.raises(SystemExit, match='CVAT_URL'):
        pushmod.delete_task(w['rd'], confirm_name='demo-Khoi')
    assert_not_deleted(cvat, w)


def test_delete_refused_without_id_or_for_dang_tao_and_bad_json(cvat):
    w = make_run(n_nhan=3, n_tay=1)
    do_push(w)
    for bad in (None, 0, -3, '12', True):
        pj_write(w, task_id=bad)
        with pytest.raises(SystemExit, match='task_id'):
            pushmod.delete_task(w['rd'], confirm_name='demo-Khoi')
    assert_not_deleted(cvat, w)
    open(os.path.join(w['rd'], 'push.json'), 'w').write('{hỏng')
    with pytest.raises(SystemExit, match='Không đọc được'):
        pushmod.delete_task(w['rd'], confirm_name='demo-Khoi')
    os.remove(os.path.join(w['rd'], 'push.json'))
    with pytest.raises(SystemExit, match='chưa có push.json'):
        pushmod.delete_task(w['rd'], confirm_name='demo-Khoi')
    assert_not_deleted(cvat, w)


def test_delete_refused_while_run_is_busy(cvat):
    w = make_run(n_nhan=3, n_tay=1)
    do_push(w)
    other = os.getpid() + 1
    lock = dang_chay.path(w['rd'])
    json.dump(dict(kind='push', pid=other, t='x'), open(lock, 'w'))
    import unittest.mock as um
    with um.patch.object(dang_chay, 'pid_alive', lambda pid: True):
        with pytest.raises(SystemExit, match='đang có việc khác'):
            pushmod.delete_task(w['rd'], confirm_name='demo-Khoi')
    assert_not_deleted(cvat, w)
    with um.patch.object(dang_chay, 'pid_alive', lambda pid: False):         # khoá mồ côi (tiến trình đã chết) thì bỏ qua
        assert pushmod.delete_task(w['rd'], confirm_name='demo-Khoi') is True
    assert len(calls(cvat, 'Task.remove')) == 1


def test_delete_marks_task_deleted_and_allows_repush(cvat):
    w = make_run(n_nhan=3, n_tay=1)
    do_push(w)
    os.makedirs(os.path.join(w['rd'], 'push'), exist_ok=True)
    open(os.path.join(w['rd'], 'push', 'done.txt'), 'w').write('ok')
    assert pushmod.delete_task(w['rd'], confirm_name='demo-Khoi') is True
    st = pj(w)
    assert st['trang_thai'] == 'task_deleted' and st['task_id'] == 1 and st['task_deleted_at']
    assert not os.path.exists(os.path.join(w['rd'], 'push', 'done.txt'))         # để m28.py push chạy lại được
    assert 'xoa_task' in open(os.path.join(w['rd'], 'log.txt'), encoding='utf-8').read()
    assert not os.path.exists(dang_chay.path(w['rd']))
    assert pushmod.delete_task(w['rd'], confirm_name='demo-Khoi') is False       # xoá lần hai: không gọi gì thêm
    assert len(calls(cvat, 'Task.remove')) == 1
    do_push(w)                                                      # đẩy lại: tạo task mới
    st2 = pj(w)
    assert st2['trang_thai'] == 'xong' and st2['task_id'] == 2 and st2['truoc_do'][0]['task_id'] == 1
    assert [t['id'] for t in state(cvat)['tasks']] == [2]


def test_delete_when_task_already_gone_only_marks(cvat):
    w = make_run(n_nhan=3, n_tay=1)
    do_push(w)
    state(cvat)['tasks'].clear()                                    # ai đó xoá tay trong CVAT
    pushmod.delete_task(w['rd'], confirm_name='demo-Khoi')
    assert calls(cvat, 'Task.remove') == [] and pj(w)['trang_thai'] == 'task_deleted'


def test_delete_cleanup_for_da_tao_after_failed_push(cvat, monkeypatch):
    monkeypatch.setenv('M28_FAKE_CVAT_CONTROL', json.dumps({'import_fail_times': 1}))
    w = make_run(n_nhan=3, n_tay=1)
    with pytest.raises(SystemExit):
        do_push(w)
    with pytest.raises(SystemExit, match='xác nhận'):
        pushmod.cleanup(w['rd'])                                    # không có TTY và không --confirm-name
    assert_not_deleted(cvat, w)
    pushmod.cleanup(w['rd'], confirm_name='demo-Khoi')
    assert pj(w)['trang_thai'] == 'task_deleted' and state(cvat)['tasks'] == []


# ---------- collect ----------
def collect_args(**kw):
    d = dict(task=['demo-Khoi'], reviewer='P4', skip_export=False, dry_run=False, tag=None, pipeline=os.path.join('config', 'pipeline.json'),
             config=os.path.join('config', 'm28_config.json'))
    d.update(kw)
    return types.SimpleNamespace(**d)


@pytest.fixture
def pushed(cvat):
    json.dump(json.load(open(os.path.join(HERE, '..', 'config', 'm28_config.json'), encoding='utf-8')), open('config/m28_config.json', 'w'))
    w = make_run(n_nhan=3, n_tay=1)
    do_push(w)
    return w


def test_collect_exports_labels_only_and_never_imports(cvat, pushed):
    from m28core import collect
    assert collect.collect(collect_args()) is True
    import datetime
    day = datetime.datetime.now().strftime('%d%m')
    xml, txt = f'raw/demo-Khoi_P4_{day}.xml', f'raw/demo-Khoi_P4_{day}.txt'
    assert os.path.exists(xml) and os.path.exists(txt)
    meta = open(txt, encoding='utf-8').read()
    assert 'task: demo-Khoi' in meta and 'ban_server: 2.77.0' in meta and 'UTC+7' in meta and 'so_job: 2' in meta and 'state new' in meta
    ex = calls(cvat, 'Task.export_dataset')
    assert ex[-1]['kwargs']['include_images'] is False and ex[-1]['args'][0] == 'CVAT for images 1.1'
    assert len(calls(cvat, 'Task.import_annotations')) == 1                       # chỉ lần của push, collect không nhập
    rep = open('outputs/collect_demo-Khoi.md', encoding='utf-8').read()
    assert 'mặt đủ 50 điểm: 3' in rep and 'chưa sửa xong' in rep and 'Chưa có QC của P2' in rep and 'Thời gian từng bước' in rep


def test_collect_does_not_overwrite_raw(cvat, pushed, capsys):
    from m28core import collect
    collect.collect(collect_args())
    import datetime
    xml = f"raw/demo-Khoi_P4_{datetime.datetime.now().strftime('%d%m')}.xml"
    open(xml, 'a').write('<!-- sửa tay -->')
    n = len(calls(cvat, 'Task.export_dataset'))
    collect.collect(collect_args())
    assert len(calls(cvat, 'Task.export_dataset')) == n and 'KHÔNG ghi đè' in capsys.readouterr().out
    assert open(xml).read().endswith('<!-- sửa tay -->')


def test_collect_dry_run_writes_nothing(cvat, pushed, capsys):
    from m28core import collect
    assert collect.collect(collect_args(dry_run=True)) is True
    assert not os.path.exists('raw') and not os.path.exists('outputs')
    out = capsys.readouterr().out
    assert 'chạy thử' in out.lower() and 'job' in out and calls(cvat, 'Task.export_dataset')[-1:] == calls(cvat, 'Task.export_dataset')[:1]
    assert len(calls(cvat, 'Task.export_dataset')) == 1                              # chỉ lần của push


def test_collect_m28_task_never_calls_cvat(cvat, capsys):
    from m28core import collect
    json.dump(json.load(open(os.path.join(HERE, '..', 'config', 'm28_config.json'), encoding='utf-8')), open('config/m28_config.json', 'w'))
    os.makedirs('raw')
    xml = ('<annotations><image id="0" name="a.png" width="512" height="512"></image></annotations>')
    open('raw/m28-manual_P1_0810.xml', 'w').write(xml)
    open('raw/m28-manual_P1_1010.xml', 'w').write(xml)
    open('raw/m28-manual_P2_0910.xml', 'w').write(xml)
    assert collect.collect(collect_args(task=['m28-manual'], reviewer='P4')) is True
    assert calls(cvat) == []                                                         # không gọi CVAT, kể cả make_client
    rep = open('outputs/collect_m28-manual.md', encoding='utf-8').read()
    assert 'raw/m28-manual_P1_1010.xml' in rep.replace('\\', '/') and 'raw/m28-manual_P1_0810.xml' not in rep.replace('\\', '/')
    assert 'P2' in rep


def test_collect_skip_export_and_multiple_tasks(cvat, pushed):
    from m28core import collect
    collect.collect(collect_args())
    n = len(calls(cvat))
    assert collect.collect(collect_args(task=['demo-Khoi', 'm28-manual', 'demo-Khong-Co'], skip_export=True, tag='ca-nhom')) is True
    assert len(calls(cvat)) == n                                                     # skip-export: không gọi CVAT
    rep = open('outputs/collect_ca-nhom.md', encoding='utf-8').read()
    assert 'demo-Khoi' in rep and 'm28-manual (chưa có raw' in rep and 'demo-Khong-Co (chưa có raw' in rep


def test_collect_missing_or_duplicate_task_on_cvat(cvat, pushed, capsys):
    from m28core import collect
    st = state(cvat)
    st['tasks'].append(dict(st['tasks'][0], id=50))                                   # hai task cùng tên demo-Khoi
    collect.collect(collect_args(task=['demo-Khoi', 'demo-Nam']))
    out = capsys.readouterr().out
    assert 'trùng tên' in out and 'KHÔNG thấy task' in out
    assert not os.path.exists('raw') or os.listdir('raw') == []                      # không task nào xuất được thì không ghi file


def test_collect_rejects_unsafe_task_names(cvat):
    from m28core import collect
    for bad in ('../x', 'a/b', 'a\\b', '', 'demo-..x'):
        with pytest.raises(SystemExit):
            collect.collect(collect_args(task=[bad]))
    assert calls(cvat) == []


def test_collect_never_calls_forbidden_methods(cvat, pushed):
    from m28core import collect
    before = len(calls(cvat))
    collect.collect(collect_args())
    new = [c['m'] for c in calls(cvat)[before:]]
    assert not [m for m in new if m in ('Task.import_annotations', 'Task.remove', 'tasks.remove_by_ids', 'tasks.create_from_data',
                                        'projects.create')]


# ---------- m28.py (qua steps với CVAT giả) ----------
def test_m28_push_cli_and_skip_second_time(cvat, tmp_path, capsys, monkeypatch):
    import cv2
    import numpy as np
    import test_m28 as tm
    import m28
    # dựng lượt như test_m28 nhưng dùng push THẬT với CVAT giả
    monkeypatch.setattr(steps, 'run_mp', lambda lm, rgb: tm.face478(rgb.shape[1], rgb.shape[0]).tolist())
    monkeypatch.setattr(steps, 'make_landmarker', lambda *a, **k: types.SimpleNamespace(close=lambda: None))
    mapping = types.ModuleType('m28core.mapping')
    mapping.apply_map = lambda pts, mp, cfg, flipped=False: {p['name']: [float(pts[mp['idx'][i]][0]), float(pts[mp['idx'][i]][1])]
                                                              for i, p in enumerate(cfg['points'])}
    monkeypatch.setitem(sys.modules, 'm28core.mapping', mapping)
    monkeypatch.delitem(sys.modules, 'm28core.autoqc', raising=False)
    tm.write_config(tmp_path, t_flip=None)
    json.dump({'idx': tm.IDX}, open('config/map_mp50.json', 'w'))
    names = tm.NAMES
    json.dump([dict(name='face50', type='skeleton', sublabels=[dict(name=n) for n in names])], open('config/face50_label.json', 'w'))
    imgs = tmp_path / 'imgs'
    tm.write_images(imgs)
    base = ['--run', 'A', '--images', str(imgs), '--box', 'auto', '--review', 'auto']
    m28.main(['prepare'] + base)
    m28.main(['review'] + base)
    m28.main(['push'] + base)
    out = capsys.readouterr().out
    assert 'push xong: task demo-A id 1' in out and os.path.exists('runs/A/push/done.txt')
    assert len(calls(cvat, 'tasks.create_from_data')) == 1
    m28.main(['push'] + base)
    assert 'bỏ qua push' in capsys.readouterr().out and len(calls(cvat, 'tasks.create_from_data')) == 1
    with pytest.raises(SystemExit, match='confirm-name|xác nhận'):
        m28.main(['push', '--run', 'A', '--cleanup'])
    m28.main(['push', '--run', 'A', '--cleanup', '--confirm-name', 'demo-A'])
    assert not os.path.exists('runs/A/push/done.txt') and json.load(open('runs/A/push.json'))['trang_thai'] == 'task_deleted'
    m28.main(['push'] + base)                                                         # đẩy lại được sau khi xoá task
    assert len(calls(cvat, 'tasks.create_from_data')) == 2


def test_m28_flags_validation(cvat):
    import m28
    for argv in (['review', '--run', 'A', '--resume'], ['push', '--run', 'A', '--resume', '--cleanup'],
                 ['push', '--run', 'A', '--confirm-name', 'x']):
        with pytest.raises(SystemExit):
            m28.main(argv)


# ---------- chữ ký của cvat-sdk THẬT ----------
def _real_sdk():
    extra = os.environ.get('M28_REAL_CVAT_SDK_PATH')
    saved_path = list(sys.path)
    saved = _purge()
    sys.path[:] = [p for p in sys.path if os.path.abspath(p) != os.path.abspath(FAKE)]
    if extra:
        sys.path.insert(0, extra)
    try:
        import cvat_sdk
        from cvat_sdk.core.proxies import projects, tasks, users
        if not hasattr(cvat_sdk, 'make_client') or 'fake_cvat' in os.path.abspath(cvat_sdk.__file__):
            return None
        return types.SimpleNamespace(sdk=cvat_sdk, tasks=tasks, projects=projects, users=users, restore=lambda: (sys.path.__setitem__(slice(None), saved_path),
                                                                                                          _purge(), sys.modules.update(saved)))
    except ImportError:
        sys.path[:] = saved_path
        sys.modules.update(saved)
        return None


def test_signatures_match_real_sdk(cvat, monkeypatch):
    """Mỗi lời gọi đã ghi trong log của gói giả phải bind được vào chữ ký của phương thức THẬT (cvat-sdk 2.77)."""
    json.dump(json.load(open(os.path.join(HERE, '..', 'config', 'm28_config.json'), encoding='utf-8')), open('config/m28_config.json', 'w'))
    monkeypatch.setenv('CVAT_ORG', 'congty')
    w = make_run(n_nhan=10, n_tay=2)
    do_push(w)
    from m28core import collect
    collect.collect(collect_args(task=['demo-Khoi', 'demo-Khong-Co']))
    pushmod.delete_task(w['rd'], confirm_name='demo-Khoi')
    pushmod.cleanup(w['rd'])                                                          # task_deleted: không gọi gì thêm
    import cai_dat_thu                                                                # "Thử kết nối" của tab Cài đặt: users.retrieve_current_user (chỉ đọc)
    res = cai_dat_thu.check(cvat_io.read_env(), '2.77.0', 'm28')
    assert res['ok'] and res['username'] == 'm28-fake-user' and res['project_found'] is True
    log = list(cvat.calls())
    real = _real_sdk()
    if real is None:
        pytest.skip('Không import được cvat_sdk THẬT (pip install cvat-sdk==2.77.0 hoặc đặt M28_REAL_CVAT_SDK_PATH): chưa kiểm chữ ký')
    try:
        T, P, C = real.tasks, real.projects, real.sdk
        table = {'make_client': C.make_client, 'Client.get_server_version': C.Client.get_server_version,
                 'projects.list': P.ProjectsRepo.list, 'projects.create': P.ProjectsRepo.create, 'Project.get_labels': P.Project.get_labels,
                 'tasks.list': T.TasksRepo.list, 'tasks.retrieve': T.TasksRepo.retrieve, 'tasks.remove_by_ids': T.TasksRepo.remove_by_ids,
                 'tasks.create_from_data': T.TasksRepo.create_from_data, 'Task.get_jobs': T.Task.get_jobs,
                 'Task.get_frames_info': T.Task.get_frames_info, 'Task.get_annotations': T.Task.get_annotations,
                 'Task.import_annotations': T.Task.import_annotations, 'Task.export_dataset': T.Task.export_dataset,
                 'Task.remove': T.Task.remove, 'Task.fetch': T.Task.fetch,
                 'users.retrieve_current_user': real.users.UsersRepo.retrieve_current_user}
        seen = set()
        for c in log:
            m = c['m']
            if m == 'Client.organization_slug':                                       # thuộc tính, không phải phương thức
                assert C.Client.organization_slug.fset is not None
                seen.add(m)
                continue
            assert m in table, f'lời gọi {m} chưa có trong bảng chữ ký'
            sig = inspect.signature(table[m])
            args = list(c['args'])
            if m.startswith(('projects.', 'tasks.', 'Task.', 'Project.', 'Client.', 'users.')):
                args = [None] + args                                                   # self
            sig.bind(*args, **c['kwargs'])
            seen.add(m)
        assert {'make_client', 'tasks.create_from_data', 'Task.import_annotations', 'Task.export_dataset', 'Task.remove', 'projects.create',
                'tasks.list', 'tasks.retrieve', 'Task.get_annotations', 'Task.get_frames_info', 'Task.get_jobs', 'Project.get_labels',
                'Client.organization_slug', 'users.retrieve_current_user'} <= seen
        # make_client thật nhận access_token=
        assert 'access_token' in inspect.signature(C.make_client).parameters
        # ResourceType thật có LOCAL; DataRequest thật có các khoá đã dùng
        from cvat_sdk.api_client import models
        assert T.ResourceType.LOCAL
        assert {'job_file_mapping', 'image_quality', 'use_cache'} <= set(models.DataRequest.openapi_types)
    finally:
        real.restore()
