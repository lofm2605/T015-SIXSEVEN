"""Dự án GIẢ dùng chung cho test bảng mặt, bộ lọc và Thống kê (không phải dữ liệu thật, không ảnh thật, không mạng).

Dựng trong một thư mục tạm (project_root): config thật, manifest in-cabin giả, các lượt có crop/meta/mp50/flags/triage dựng như prepare (cờ do steps.flags
thật tính), nhãn CVAT bảy skeleton giả (steps.image_xml thật), file bấm giờ giả đúng 12 cột facetimer. Tên điểm, thứ tự và nhóm lấy từ config thật.
"""
import csv
import json
import os
import sys
import types

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))
from m28core import steps  # noqa: E402

REAL_CFG = os.path.join(HERE, '..', 'config', 'm28_config.json')
MAN_COLS = ['file', 'set', 'block', 'seq', 'source', 'camera', 'subject', 'gender', 'glasses', 'state', 'video', 'frame', 't_s', 'image', 'face_idx',
            'x0', 'y0', 'x1', 'y1', 'left', 'top', 'k', 'pose', 'expression', 'illumination', 'makeup', 'occlusion', 'blur',
            'yaw', 'pitch', 'roll', 'jaw_open', 'luma', 'contrast', 'bright_frac', 'lap_var', 'gaze_label', 'gaze_ang', 'pad_frac', 'seed']
TIMING_COLS = ['date', 'person', 'condition', 'task', 'job', 'block', 'seq', 'face_id', 'seconds', 'warmup', 'interrupted', 'note']


def cfg_real():
    with open(REAL_CFG, encoding='utf-8') as f:
        return json.load(f)


class Proj:
    """Một dự án giả. Dùng với monkeypatch.chdir(proj.root) khi gọi steps.flags (đường dẫn runs\\ tương đối)."""

    def __init__(self, root, t_flip=0.03):
        self.root = str(root)
        self.cfg = cfg_real()
        self.cfg['t_flip'] = t_flip
        self.names = [p['name'] for p in self.cfg['points']]
        os.makedirs(os.path.join(self.root, 'config'), exist_ok=True)
        os.makedirs(os.path.join(self.root, 'runs'), exist_ok=True)
        self.save_cfg()
        self.manifest = {}
        self.rng = np.random.default_rng(7)

    # ---------- config, manifest ----------
    def save_cfg(self):
        with open(os.path.join(self.root, 'config', 'm28_config.json'), 'w', encoding='utf-8') as f:
            json.dump(self.cfg, f)

    def add_face(self, name, source='yawdd', set_='F', subject=None, **kw):
        """Thêm một mặt vào manifest giả. subject mặc định: một người riêng cho mỗi mặt."""
        row = {c: '' for c in MAN_COLS}
        row.update(file=name + '.png', set=set_, source=source, camera=kw.pop('camera', 'dash' if source == 'yawdd' else 'drivface'),
                   subject=subject or (f'yd_M{len(self.manifest) + 1:03d}' if source == 'yawdd' else f'df_{len(self.manifest) + 1:02d}'),
                   glasses='none', state='normal', left='0', top='0', k='1', pose='0', expression='0', illumination='0', makeup='0', occlusion='0',
                   blur='0', yaw='3.5', jaw_open='0.1', luma='120', lap_var='400')
        row.update({k: str(v) for k, v in kw.items()})
        self.manifest[name] = row
        self.write_manifest()
        return row

    def write_manifest(self):
        d = os.path.join(self.root, 'data')
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, 'manifest.csv'), 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, MAN_COLS, lineterminator='\n')
            w.writeheader()
            w.writerows(self.manifest.values())

    def png(self, path, size=(32, 32), color=(120, 130, 140)):
        from PIL import Image
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Image.new('RGB', size, color).save(path)

    # ---------- lượt ----------
    def run_dir(self, run):
        return os.path.join(self.root, 'runs', run)

    def draft(self, sigma=2.0, flip_sigma=None):
        """Nháp 50 điểm (hệ ảnh cắt 512) quanh mẫu tmpl của config, ảnh lật = nháp + nhiễu có độ lớn riêng từng điểm."""
        base = np.array([p['tmpl'] for p in self.cfg['points']], float)
        orig = base + self.rng.normal(0, sigma, base.shape)
        per_point = self.rng.uniform(0.3, 6.0, len(base)) if flip_sigma is None else np.full(len(base), flip_sigma)
        flip = orig + self.rng.normal(0, 1, base.shape) * per_point[:, None]
        return orig, flip, per_point

    def make_run(self, run, faces, mode='crop', no_flip=(), inbox=False, with_flags=True, t_flip='cfg', triage=None, png=True):
        """Dựng runs\\<run>: crop (meta, ảnh, box.txt), map50\\mp50.json, flags\\flags.json (steps.flags thật), autoqc. faces: danh sách tên mặt.
        mode 'auto': tên ảnh CVAT = tên ảnh gốc (inbox/<tên>.png) và meta.rel/src/left/top/k/w/h như prepare thật. Trả {tên: (orig, flip, per_point)}."""
        rd = self.run_dir(run)
        os.makedirs(os.path.join(rd, 'crop', 'images'), exist_ok=True)
        os.makedirs(os.path.join(rd, 'map50'), exist_ok=True)
        meta, mp50, drafts = {}, {}, {}
        for i, n in enumerate(faces):
            o, f, pp = self.draft()
            drafts[n] = (o, f, pp)
            mp50[n] = dict(orig={nm: [float(x), float(y)] for nm, (x, y) in zip(self.names, o)},
                           flip=None if n in no_flip else {nm: [float(x), float(y)] for nm, (x, y) in zip(self.names, f)})
            if mode == 'auto':
                meta[n] = dict(src=f'/x/{n}.png', rel=f'{n}.png', left=-10.0 - i, top=-20.0, k=0.9, w=640, h=480)
            else:
                meta[n] = dict(src=f'/x/{n}.png', rel=f'{n}.png', left=0.0, top=0.0, k=1.0, w=512, h=512)
            if png:
                self.png(os.path.join(rd, 'crop', 'images', n + '.png'))
        with open(os.path.join(rd, 'crop', 'meta.json'), 'w', encoding='utf-8') as f:
            json.dump(meta, f)
        with open(os.path.join(rd, 'crop', 'box.txt'), 'w', encoding='utf-8') as f:
            f.write(mode)
        with open(os.path.join(rd, 'map50', 'mp50.json'), 'w', encoding='utf-8') as f:
            json.dump(mp50, f)
        if inbox:
            os.makedirs(os.path.join(rd, 'inbox'), exist_ok=True)
        if with_flags:
            self.run_flags(run, t_flip)
        if triage:
            for who, rows in triage.items():
                self.write_triage(run, who, rows)
        return drafts

    def run_flags(self, run, t_flip='cfg'):
        """Chạy steps.flags thật (cwd phải là project_root) với t_flip cho trước ('cfg' = trong config)."""
        cwd = os.getcwd()
        os.chdir(self.root)
        try:
            cfgp = os.path.join(self.root, 'config', 'm28_config.json')
            if t_flip != 'cfg':
                old = self.cfg['t_flip']
                self.cfg['t_flip'] = t_flip
                self.save_cfg()
            args = types.SimpleNamespace(run=run, config=cfgp)
            out = os.path.join('runs', run, 'flags')
            os.makedirs(out, exist_ok=True)
            steps.flags(args, out)
            if t_flip != 'cfg':
                self.cfg['t_flip'] = old
                self.save_cfg()
        finally:
            os.chdir(cwd)

    def write_triage(self, run, who, rows):
        """rows: [(tên, quyết định, lý do, giây)] theo thứ tự bấm; giây None/'' = ô trống."""
        d = os.path.join(self.run_dir(run), 'review')
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f'triage_{who}.csv'), 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['name', 'decision', 'reason', 'seconds'])
            for n, dec, why, sec in rows:
                w.writerow([n + '.png', dec, why, '' if sec is None else sec])

    def write_push(self, run, task, gan_tay_co_nhap=(), manual=(), cap_nhat='2026-10-14T10:00:00+07:00'):
        rd = self.run_dir(run)
        with open(os.path.join(rd, 'push.json'), 'w', encoding='utf-8') as f:
            json.dump(dict(tool='m28', phien_ban=2, task=task, trang_thai='xong', cap_nhat=cap_nhat, gan_tay_co_nhap=list(gan_tay_co_nhap),
                           so_anh=dict(nhan=0, gan_tay=len(gan_tay_co_nhap) + len(manual))), f)
        os.makedirs(os.path.join(rd, 'push'), exist_ok=True)
        with open(os.path.join(rd, 'push', 'manual_list.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join([f'{n}\tco_nhap' for n in gan_tay_co_nhap] + [f'{n}\tanh_trong' for n in manual]))

    # ---------- nhãn ----------
    def label_pts(self, drafts_face, sigma=1.0, big=False, miss=(), flip_err=False):
        """Nhãn quanh nháp: nhiễu nhỏ (hoặc 'big': lệch cả một vùng 30 px); miss: tên điểm bị bỏ."""
        o = np.array(drafts_face[0], float)
        pp = drafts_face[2]
        lab = o + self.rng.normal(0, 1, o.shape) * (pp[:, None] if flip_err else sigma)
        if big:
            lab = lab + 30.0
        return {n: (float(x), float(y)) for n, (x, y) in zip(self.names, lab) if n not in miss}

    def write_label(self, folder, task, who, day, faces, low=None, w=512, h=512, old=False):
        """faces: {tên ảnh CVAT: {điểm: (x, y)}}; low: {tên ảnh: {điểm: bool}} (mặc định false). old=True: label face50 một skeleton (nhãn cũ)."""
        d = os.path.join(self.root, folder)
        os.makedirs(d, exist_ok=True)
        parts = ['<?xml version="1.0" encoding="utf-8"?>', '<annotations>', '  <version>1.1</version>']
        for i, (name, pts) in enumerate(faces.items()):
            if old:
                parts.append(f'<image id="{i}" name="{name}" width="{w}" height="{h}"><skeleton label="face50">'
                             + ''.join(f'<points label="p{j:02d}_x" occluded="0" outside="0" points="1,1"/>' for j in range(3)) + '</skeleton></image>')
                continue
            pnames = [n for n in self.names if n in pts]
            lw = [bool((low or {}).get(name, {}).get(n, False)) for n in pnames]
            parts.append(steps.image_xml(i, name, pnames, [pts[n] for n in pnames], lw, w, h))
        parts.append('</annotations>')
        path = os.path.join(d, f'{task}_{who}_{day}.xml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(parts))
        return path

    # ---------- bấm giờ ----------
    def write_timing(self, folder='.', people=('P1', 'P2', 'P3', 'P4', 'P5'), speedup=0.75, seed=28, outliers=True):
        """timing_P1..P5.csv giả (12 cột facetimer): Pk gán tay Xk (m28-manual) và sửa nháp X(k+1) (m28-assisted; P5 sửa X1); 10 mặt/khối, seq 1-2 khởi động;
        assisted nhanh hơn manual theo `speedup` (0,75 = nhanh hơn 25%)."""
        rng = np.random.default_rng(seed)
        d = os.path.join(self.root, folder)
        os.makedirs(d, exist_ok=True)
        paths = []
        for i, p in enumerate(people):
            k = i + 1
            rows = []
            for cond, task, blk in (('manual', 'm28-manual', f'X{k}'), ('assisted', 'm28-assisted', f'X{k % 5 + 1}')):
                base = 50.0 * (0.9 + 0.2 * rng.random())
                for seq in range(1, 11):
                    sec = base * (speedup if cond == 'assisted' else 1.0) * (0.85 + 0.3 * rng.random())
                    rows.append(['2026-10-14' if cond == 'manual' else '2026-10-15', p, cond, task, 100 + k, blk, seq, f'{blk}_{seq:02d}',
                                 round(sec, 1), int(seq <= 2), 0, ''])
            if outliers and i == 0:
                rows[5][8] = 400.0                                  # ngoại lai (ảnh bỏ ngang)
                rows[15][8] = 330.0
                rows[6][10] = 1                                     # một dòng bị gián đoạn
            path = os.path.join(d, f'timing_{p}.csv')
            with open(path, 'w', encoding='utf-8', newline='') as f:
                w = csv.writer(f)
                w.writerow(TIMING_COLS)
                w.writerows(rows)
            paths.append(path)
        return paths


def simple_project(root, n=6, run='R1', t_flip=0.03, mode='crop', source='yawdd', labelled=True, task=None, who='P1', day='1410'):
    """Dự án nhỏ: n mặt F_001.. trong manifest; lượt R1 có nháp + cờ; triage của P1 (mặt 1..n-1 Nhận, mặt n Bỏ); nếu labelled: nhãn push.json task `task`."""
    p = Proj(root, t_flip=t_flip)
    faces = [f'F_{i:03d}' for i in range(1, n + 1)]
    for i, fn in enumerate(faces):
        p.add_face(fn, source=source, set_='F' if i % 2 == 0 else 'Tdev' if i % 3 else 'Ttest')
    drafts = p.make_run(run, faces, mode=mode)
    p.write_triage(run, 'P1', [(fn, 'nhan', '', 5.0 + i) for i, fn in enumerate(faces[:-1])] + [(faces[-1], 'bo', 'KHONG_MAT', 3.0)])
    info = dict(proj=p, faces=faces, drafts=drafts)
    if labelled:
        task = task or f'demo-{run}'
        p.write_push(run, task)
        labs = {}
        for fn in faces[:-1]:
            name = steps._file_name(fn, json.load(open(os.path.join(p.run_dir(run), 'crop', 'meta.json')))[fn], mode)
            labs[name] = p.label_pts(drafts[fn])
        info['label'] = p.write_label('raw', task, who, day, labs)
    return info
