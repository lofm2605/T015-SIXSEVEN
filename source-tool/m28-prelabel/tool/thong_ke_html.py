"""HTML của trang Thống kê: MỘT nguồn dựng HTML cho cả tab "Thống kê" (thong_ke_ui.py) lẫn bản xuất tĩnh (thong_ke.xuat).

Chỉ HTML + CSS thuần: không JavaScript, không CDN, không font tải về, không ảnh (không <img>), không ảnh mặt. Màu lấy theo Ý NGHĨA và cố định:
  * 7 nhóm điểm: m28core.mau_nhom.GROUP_COLOR (giống label CVAT và ảnh chồng), luôn kèm tên nhóm tiếng Việt (GROUP_VI);
  * Nhận / Gán tay / Bỏ: review_app.STATUS_COLOR (giống viền ảnh nhỏ);
  * một chuỗi số đơn lẻ: một màu trung tính; Đạt / Không đạt / Chưa kết luận luôn có chữ + ký hiệu (✓ ✗ •), không chỉ màu.
Số tiêu đề là ô số kèm n; so sánh độ lớn giữa các nhóm là thanh ngang BẮT ĐẦU TỪ 0, cùng thang trong một bảng, số in cạnh thanh; mục tiêu là một vạch đánh dấu có nhãn chữ.
Chữ dùng màu chữ của theme (var(--body-text-color)...), không dùng màu nhóm cho chữ. Trang dùng dấu phẩy thập phân; CSV giữ dấu chấm.
"""
import html

from m28core import mau_nhom

N_NHO = 5
NEUTRAL = "#64748b"
KET_LUAN = {"dat": ("✓", "Đạt", "ok"), "khong_dat": ("✗", "Không đạt", "bad"), "chua_ket_luan": ("•", "Chưa kết luận", "mid"), "chua_du_du_lieu": ("•", "Chưa đủ dữ liệu", "mid")}
DANH_MUC_MAU_XAM = "#9ca3af"
NGUON_VI = {"yawdd": "YawDD", "drivface": "DrivFace", "khong_ro": "Không rõ nguồn"}


def e(x):
    return html.escape("" if x is None else str(x), quote=True)


def num(x, d=1, suffix=""):
    """Số theo kiểu Việt (dấu phẩy thập phân); None -> '—'."""
    if x is None or (isinstance(x, float) and x != x):
        return "—"
    return (f"{x:.{d}f}".replace(".", ",")) + suffix


def _status_color():
    import review_app                                                        # nạp lười (tránh vòng nhập: review_app nạp thong_ke_ui)
    return review_app.STATUS_COLOR


# ---------- thành phần ----------
def trong(t):
    """Trạng thái trống: vì sao trống, cần file nào, ai làm ra file đó. Không bao giờ có số."""
    return ('<div class="tk-trong" role="status"><b>Chưa có số.</b> ' + e(t["ly_do"]) + f'<div class="tk-can">Cần: {e(t["can"])} · người làm ra: <b>{e(t["ai"])}</b></div></div>')


def tile(gia_tri, nhan, n=None, ghi_chu="", cls="", title=""):
    n_html = "" if n is None else f'<div class="tk-tn">n = {e(n)}' + (" · <b>n quá nhỏ</b>" if isinstance(n, int) and n < N_NHO else "") + "</div>"
    return (f'<div class="tk-tile {e(cls)}" title="{e(title)}"><div class="tk-tv">{gia_tri}</div><div class="tk-tl">{e(nhan)}</div>{n_html}'
            + (f'<div class="tk-tg">{ghi_chu}</div>' if ghi_chu else "") + "</div>")


def tiles(*ts):
    return '<div class="tk-tiles">' + "".join(ts) + "</div>"


def chip(kl):
    sym, vi, cls = KET_LUAN[kl]
    return f'<span class="tk-chip tk-{cls}"><span aria-hidden="true">{sym}</span> {vi}</span>'


def thanh(rows, fmt=lambda v: num(v, 2), vach=None, toi_da=None, don_vi=""):
    """Thanh ngang từ 0. rows: [(nhãn, giá trị|None, màu, ghi chú tooltip, n|None)]. Cùng thang (toi_da, mặc định max giá trị / vạch). vach = (giá trị, nhãn chữ)."""
    vals = [v for _l, v, _c, _t, _n in rows if v is not None]
    top = toi_da or max(vals + ([vach[0]] if vach else []) + [1e-9]) * 1.1
    out = ['<div class="tk-bars">']
    for lab, v, col, tip, n in rows:
        if v is None or (n is not None and n < N_NHO):
            out.append(f'<div class="tk-row"><div class="tk-lab">{lab}</div><div class="tk-bar tk-na"></div><div class="tk-val">'
                       + ("n quá nhỏ" if v is not None or n is not None else "—") + (f" <span class=\"tk-n\">(n = {n})</span>" if n is not None else "") + "</div></div>")
            continue
        w = max(0.0, min(100.0, 100.0 * v / top))
        mark = f'<span class="tk-vach" style="left:{100.0 * vach[0] / top:.2f}%" title="{e(vach[1])}"></span>' if vach else ""
        out.append(f'<div class="tk-row" title="{e(tip)}"><div class="tk-lab">{lab}</div><div class="tk-bar"><span class="tk-fill" style="width:{w:.2f}%;background:{col}"></span>{mark}</div>'
                   f'<div class="tk-val">{fmt(v)}{e(don_vi)}' + (f' <span class="tk-n">(n = {n})</span>' if n is not None else "") + "</div></div>")
    if vach:
        out.append(f'<div class="tk-vach-lab">┃ {e(vach[1])}</div>')
    out.append("</div>")
    return "".join(out)


def bang(cols, rows, cls=""):
    """Bảng HTML. cols: [(tiêu đề, khoá|hàm, căn 'l'|'r')]; rows: list dict. Giá trị là chuỗi thường thì bị escape, là raw(...) thì giữ nguyên.
    Bọc trong khung cuộn ngang để trang hẹp (420 px) không bị tràn."""
    cr = ' class="tk-r"'
    th = "".join('<th scope="col"' + (cr if a == "r" else "") + ">" + e(t) + "</th>" for t, _k, a in cols)
    body = []
    for r in rows:
        tds = []
        for _t, k, a in cols:
            v = k(r) if callable(k) else r.get(k)
            tds.append("<td" + (cr if a == "r" else "") + ">" + (v if isinstance(v, _Raw) else e(v)) + "</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    return '<div class="tk-tw"><table class="tk-table ' + cls + '"><thead><tr>' + th + "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div>"


class _Raw(str):
    """Chuỗi HTML đã an toàn (không escape lại)."""


def raw(s):
    return _Raw(s)


def mau_nhom_chip(g):
    return raw(f'<span class="tk-sw" style="background:{mau_nhom.GROUP_COLOR[g]}" aria-hidden="true"></span>{e(mau_nhom.GROUP_VI.get(g, g))}') if g in mau_nhom.GROUP_COLOR else e(g)


def lab_nhom(g):
    return (f'<span class="tk-sw" style="background:{mau_nhom.GROUP_COLOR[g]}" aria-hidden="true"></span>{e(mau_nhom.GROUP_VI.get(g, g))}') if g in mau_nhom.GROUP_COLOR else e(g)


def muc(tieu_de, noi_dung, ghi_chu="", mid=""):
    return (f'<section class="tk-sec" id="{e(mid)}"><h3>{e(tieu_de)}</h3>' + (f'<p class="tk-ghi">{ghi_chu}</p>' if ghi_chu else "") + noi_dung + "</section>")


# ---------- đầu trang ----------
def phan_dau(st):
    m = st["meta"]
    tf = "chưa chốt (null)" if m["t_flip"] is None else num(m["t_flip"], 4)
    dong = [f"Lập lúc {e(m['ngay'])}", f"commit {e(m['commit'])}", f"config 50 điểm version {e(m['config_version'])}", f"t_flip hiện tại: {e(tf)}",
            f"{len(m['luot'])} lượt" + (": " + e(", ".join(m["luot"])) if m["luot"] else "")]
    out = [f'<div class="tk-meta">{" · ".join(dong)}</div>']
    if not m["gom_ttest"]:
        out.append(f'<div class="tk-note">Ttest đang ẩn ({m["ttest_an"]} mặt): Ttest là tập đo một lần của đề tài; bật ô "Gồm Ttest" chỉ khi đúng buổi đo.</div>')
    else:
        out.append('<div class="tk-note tk-warn">Đang GỒM Ttest: tập đo một lần, không dùng số này để chỉnh ngưỡng hay tinh chỉnh model.</div>')
    if m["nguoi_ra"]:
        out.append(f'<div class="tk-note">Chỉ tính người rà: {e(", ".join(m["nguoi_ra"]))}. triage_auto (máy tự quyết) không bao giờ tính là người rà.</div>')
    for w in m["canh_bao"]:
        out.append(f'<div class="tk-note tk-warn">{e(w)}</div>')
    for l, why in m["luot_bo_qua"].items():
        out.append(f'<div class="tk-note tk-warn">Lượt {e(l)} bỏ qua: {e(why)}.</div>')
    return "".join(out)


# ---------- (4) số lượng ----------
def _stack(d, tong):
    """Thanh chồng 100%: Nhận / Gán tay / Bỏ / Chưa rà (màu STATUS_COLOR, chữ + số trong tooltip và bảng bên cạnh)."""
    sc = _status_color()
    parts = []
    for k, col in (("nhan", sc["nhan"]), ("gan_tay", sc["gan_tay"]), ("bo", sc["bo"]), ("chua_ra", DANH_MUC_MAU_XAM)):
        if d[k]:
            parts.append(f'<span class="tk-seg" style="width:{100.0 * d[k] / tong:.2f}%;background:{col}" title="{e(DANH_MUC_VI[k])}: {d[k]}"></span>')
    return raw('<div class="tk-stack">' + "".join(parts) + "</div>")


DANH_MUC_VI = {"nhan": "Nhận", "gan_tay": "Gán tay", "bo": "Bỏ", "chua_ra": "Chưa rà", "khong_thay_mat": "Không thấy mặt", "xoa_mem": "Đã xoá mềm"}


def _bang_so_luong(rows, ten_cot):
    cols = [(ten_cot, "ten", "l"), ("Tổng", "tong", "r"), ("Cơ cấu", lambda d: _stack(d, d["tong"]) if d["tong"] else "", "l")]
    cols += [(vi, k, "r") for k, vi in DANH_MUC_VI.items()]
    return bang(cols, rows)


def muc_so_luong(st):
    sl = st["so_luong"]
    if sl.get("trong"):
        return muc("4. Số lượng dữ liệu", trong(sl["trong"]), mid="tk-sl")
    t = sl["tong"]
    ts = [tile(num(sl["tong_luot_mat"], 0), "(lượt, mặt) trong bảng", sl["tong_luot_mat"]),
          tile(num(sl["mat_duy_nhat"], 0), "mặt duy nhất (theo tên manifest)", sl["mat_duy_nhat"],
               "Khác số (lượt, mặt) khi một mặt nằm ở nhiều lượt." if sl["khac_don_vi"] else "")]
    if sl["chi_nhan"]:
        ts.append(tile(num(sl["chi_nhan"], 0), "mặt chỉ có nhãn (không có lượt)", sl["chi_nhan"]))
    ghi = "Đơn vị: " + ("(lượt, mặt) — số mặt duy nhất khác nên hiện cả hai." if sl["khac_don_vi"] else "(lượt, mặt) = mặt duy nhất.")
    parts = [tiles(*ts), _bang_so_luong([t], "Tất cả")] if t else [tiles(*ts)]
    parts += ["<h4>Theo nguồn</h4>", _bang_so_luong(sl["theo_nguon"], "Nguồn"), "<h4>Theo đợt (lượt)</h4>", _bang_so_luong(sl["theo_luot"], "Lượt"),
              "<h4>Theo tập gốc (set)</h4>", _bang_so_luong(sl["theo_set"], "Tập")]
    return muc("4. Số lượng dữ liệu", "".join(parts), ghi, "tk-sl")


# ---------- (1) chất lượng nháp ----------
def _tiles_nme(s):
    return tiles(tile(num(s["nme_tb"], 2, "%"), "NME trung bình (% IOD)", s["n"], title="Trung bình, mỗi mặt một NME chính (E điểm-điểm, C tới đường gấp khúc)"),
                 tile(num(s["nme_trung_vi"], 2, "%"), "NME trung vị (% IOD)", s["n"]),
                 tile(num(s["hong_pct"], 1, "%") if s["n"] >= N_NHO else "n quá nhỏ", "mặt hỏng (NME ≥ 10% IOD)", s["n"], f'{s["n_hong"]} mặt', title="Mặt hỏng: NME >= 10% IOD"),
                 tile(num(s["nme_eye_tb"], 2, "%"), "NME vùng mắt (% IOD)", s["n"]),
                 tile(num(s["eye_open_tb"], 2, "%"), "lệch độ mở mắt (% IOD)", s["n"]))


def _bars_nhom(s):
    rows = [(lab_nhom(g), s["nhom"][g], mau_nhom.GROUP_COLOR[g], f"{mau_nhom.GROUP_VI[g]}: trung bình {num(s['nhom'][g], 2)}% IOD", s["nhom_n"][g]) for g in s["nhom"]]
    return thanh(rows, lambda v: num(v, 2), vach=(10.0, "ngưỡng mặt hỏng 10% IOD"), don_vi="%")


def _bars_vung(s):
    ten = {"brow": "lông mày", "nose": "mũi", "eye": "mắt", "lip": "môi"}
    rows = [(e(ten.get(g, g)), v, NEUTRAL, f"{ten.get(g, g)}: trung bình {num(v, 2)}% IOD", s["n"]) for g, v in s["vung"].items()]
    return thanh(rows, lambda v: num(v, 2), don_vi="%")


def _bang_yeu_to(xs):
    return bang([("Yếu tố", "yeu_to", "l"), ("Giá trị", "gia_tri", "l"), ("n", "n", "r"), ("NME TB (% IOD)", lambda x: "n quá nhỏ" if x["nho"] else num(x["nme_tb"], 2), "r"),
                 ("Mặt hỏng", lambda x: "n quá nhỏ" if x["nho"] else num(x["hong_pct"], 1, "%"), "r")], xs)


def _khoi_chat_luong_nhan(cn):
    if cn.get("trong"):
        return trong(cn["trong"])
    rows = []
    for col, ten in (("nme", "NME chính"), ("nme_eye", "NME vùng mắt")):
        v = cn["cot"].get(col)
        if not v or v["ket_luan"] is None:
            rows.append(dict(ten=ten, n=0, hieu="chưa có mặt chấm ở cả hai điều kiện", ktc="—", kl=""))
            continue
        rows.append(dict(ten=ten, n=v["n"], hieu=num(v["tb"], 2, "% IOD"), ktc=f"[{num(v['lo'], 2)}; {num(v['hi'], 2)}]", kl=raw(chip(v["ket_luan"])) if v["n"] >= N_NHO else "n quá nhỏ"))
    return (bang([("Chỉ số", "ten", "l"), ("Số mặt ghép cặp", "n", "r"), ("Hiệu TB (assisted − manual)", "hieu", "r"), ("KTC 90%", "ktc", "r"), ("Kết luận", "kl", "l")], rows)
            + '<p class="tk-ghi">Giao thức P5: hiệu NME ghép cặp theo mặt; bootstrap 2.000 lần, seed 28, cận 5/95; đạt khi cận trên ≤ +0,5% IOD, không đạt khi cận dưới &gt; +0,5% IOD. '
              'Đọc từ outputs\\nme_per_face.csv của eval50 (chất lượng NHÃN người so với đáp án vàng).</p>')


def muc_chat_luong(st):
    cl = st["chat_luong"]
    cn = cl.get("chat_luong_nhan") or {}
    if cl.get("trong"):
        return muc("1. Chất lượng nháp (NME của nháp so với nhãn sửa tay)", trong(cl["trong"]) + "<h4>Chất lượng nhãn</h4>" + _khoi_chat_luong_nhan(cn), mid="tk-cl")
    out = []
    if cl["can_duoi"]:
        out.append(f'<div class="tk-note tk-warn"><b>Chỉ có nhãn assisted: cận dưới.</b> {e(_can_duoi())}</div>')
    if cl["n_khong_nhap"]:
        out.append(f'<div class="tk-note">Có {cl["n_khong_nhap"]} nhãn chưa ghép với nháp của máy. Nếu đó là nhãn thí nghiệm (m28-manual, m28-assisted…), chọn ô '
                   '<b>Lượt chứa nháp</b> (luot_nhap, hoặc --luot-nhap) rồi Làm mới để tính NME cho chúng.</div>')
    for c, s in cl["theo_dieu_kien"].items():
        ten = {"manual": "Nhãn manual — đáp án trung thực cho chất lượng nháp", "assisted": "Nhãn assisted — CẬN DƯỚI (lượng người đã sửa nháp)",
               "khong_ro_dieu_kien": "Nhãn chưa rõ điều kiện (không dùng làm số tiêu đề)"}[c]
        out.append(f"<h4>{e(ten)}</h4>" + _tiles_nme(s) + "<h5>Theo nhóm điểm (NME trung bình, % IOD)</h5>" + _bars_nhom(s) + "<h5>Theo vùng thô</h5>" + _bars_vung(s)
                   + "<h5>Theo điều kiện</h5>" + _bang_yeu_to(cl["yeu_to"][c]))
    out.append("<h4>Chất lượng nhãn</h4>" + _khoi_chat_luong_nhan(cn))
    ghi = (f'{cl["n_nhan"]} nhãn đọc được; {cl["n_khong_nhap"]} nhãn chưa ghép với nháp. Mỗi mặt một NME (mặt manifest ở nhiều lượt chỉ đếm một lần, nhãn mới nhất/final thắng). '
           "Tiêu đề lấy nhãn manual; assisted bị neo theo nháp nên chỉ là cận dưới.")
    return muc("1. Chất lượng nháp (NME của nháp so với nhãn sửa tay)", "".join(out), ghi, "tk-cl")


def _can_duoi():
    return ("NME nháp-vs-assisted đo lượng người đã sửa, không phải sai số thật của nháp (nhãn bị neo theo nháp). Cần nhãn manual (gán từ đầu) để có đáp án trung thực.")


# ---------- (2) cờ ----------
def _bang_nguong(a, t_flip):
    rows = [dict(q=num(q, 2), t=num(t, 4), cho=num(f, 1, "%"), rc=num(c, 1, "%"), pr=num(p, 1, "%"), pf=num(pf, 1)) for q, t, f, c, p, pf in a["table"]]
    cols = [("Phân vị", "q", "r"), ("Ngưỡng t_flip", "t", "r"), ("% điểm bị cờ", "cho", "r"), ("Điểm sai bị bắt (recall)", "rc", "r"), ("Độ chính xác (precision)", "pr", "r"), ("Cờ/mặt", "pf", "r")]
    out = bang(cols, rows)
    if a["at_t"]:
        m = a["at_t"]
        out += (f'<p class="tk-ghi">Tại t_flip hiện hành ({num(t_flip, 4)}): {num(m["flagged_pct"], 1)}% điểm bị cờ, bắt {num(m["caught"], 1)}% điểm sai (recall), '
                f'độ chính xác {num(m["precision"], 1)}%, {num(m["per_face"], 1)} cờ/mặt.</p>')
    else:
        out += '<p class="tk-ghi">t_flip chưa chốt (null): bảng cho các phân vị của điểm số lật để P2 chọn ngưỡng.</p>'
    return out


def _bang_auroc(a):
    def au(v):
        return "n quá nhỏ" if v["nho"] else num(v["auroc"], 3)
    rows = [dict(ten="Toàn bộ", n=a["n_points"], sai=a["n_bad"], pct=num(a["bad_pct"], 1, "%"), au="n quá nhỏ" if a["n_sai_nho"] else num(a["auroc"], 3))]
    rows += [dict(ten=f"Vùng {g}", n=v["n"], sai=v["n_bad"], pct=num(v["bad_pct"], 1, "%"), au=au(v)) for g, v in a["by_region"].items()]
    rows += [dict(ten=raw(lab_nhom(g)), n=v["n"], sai=v["n_bad"], pct=num(v["bad_pct"], 1, "%"), au=au(v)) for g, v in (a["by_group"] or {}).items()]
    return bang([("Phạm vi", "ten", "l"), ("Số điểm", "n", "r"), ("Điểm sai", "sai", "r"), ("% điểm sai", "pct", "r"), ("AUROC", "au", "r")], rows)


def muc_co(st):
    co = st["co"]
    out = []
    kd = co["khong_dap_an"]
    if kd.get("trong"):
        out.append(trong(kd["trong"]))
    else:
        for l in co["luot_toan_false"]:
            out.append(f'<div class="tk-note tk-warn">Lượt {e(l)}: mọi cờ low_conf = false (khả năng chạy khi t_flip = null): số cờ của lượt này không phản ánh cờ thật.</div>')
        out.append(tiles(tile(num(kd["pct"], 1, "%"), "điểm bị cờ", kd["n_mat"], f'{kd["n_diem"]} điểm'),
                         tile(num(kd["co_moi_mat"], 1), "cờ trung bình mỗi mặt (trên 50 điểm)", kd["n_mat"]),
                         tile("chưa chốt (null)" if co["t_flip"] is None else num(co["t_flip"], 4), "t_flip hiện tại của config")))
        out.append("<h5>% điểm bị cờ theo nhóm</h5>" + thanh([(lab_nhom(g), v["pct"], mau_nhom.GROUP_COLOR[g], f"{mau_nhom.GROUP_VI[g]}: {num(v['pct'], 1)}% điểm bị cờ", kd["n_mat"])
                                                              for g, v in kd["theo_nhom"].items()], lambda v: num(v, 1), don_vi="%"))
        ten = {"brow": "lông mày", "nose": "mũi", "eye": "mắt", "lip": "môi"}
        out.append("<h5>% điểm bị cờ theo vùng</h5>" + thanh([(e(ten.get(g, g)), v["pct"], NEUTRAL, "", kd["n_mat"]) for g, v in kd["theo_vung"].items()], lambda v: num(v, 1), don_vi="%"))
        out.append("<h5>Phân bố số cờ mỗi mặt (số mặt)</h5>" + thanh([(e(d["khoang"]), float(d["n"]), NEUTRAL, f'{d["n"]} mặt có {d["khoang"]} cờ', None) for d in kd["phan_bo"]], lambda v: num(v, 0)))
        out.append("<h5>Theo lượt</h5>" + bang([("Lượt", "luot", "l"), ("Số mặt", "n_mat", "r"), ("% điểm bị cờ", lambda r: num(r["pct"], 1, "%"), "r"), ("Cờ/mặt", lambda r: num(r["co_moi_mat"], 1), "r")], kd["theo_luot"]))
    for c in ("manual", "assisted"):
        a = co["co_dap_an"].get(c)
        if not a:
            continue
        ten = "manual (đáp án trung thực)" if c == "manual" else "assisted (cận dưới: nhãn bị neo theo nháp, cờ trông chính xác hơn thật)"
        sai = a["tol"] if not isinstance(co["tolerance"], (int, float)) else co["tolerance"]
        out.append(f"<h4>Có đáp án — nhãn {e(ten)}</h4>" + tiles(
            tile("n quá nhỏ" if a["n_sai_nho"] else num(a["auroc"], 3), "AUROC toàn bộ (0,5 = vô tác dụng)", a["n_bad"], f'{a["n_points"]} điểm, {a["n_faces"]} mặt' + (" · <b>n quá nhỏ</b>" if a["n_sai_nho"] else "")),
            tile(num(a["bad_pct"], 1, "%"), f"điểm sai (lỗi > {num(sai, 1)}% IOD)", a["n_bad"]),
            tile(num(a["low_conf_nhan"]["tb"], 1), "low_conf người gán còn để bật mỗi mặt", a["low_conf_nhan"]["n_nhan"], f'tổng {a["low_conf_nhan"]["tong"]}'))
            + _bang_auroc(a) + _bang_nguong(a, co["t_flip"]))
    if co.get("thieu_dap_an"):
        out.append("<h4>Có đáp án</h4>" + trong(co["thieu_dap_an"]))
    ghi = (f"Điểm sai = lỗi > sai số chấp nhận (config.tolerance theo vùng nếu có, không thì {num(co['tol_mac_dinh'], 1)}% IOD). AUROC cần ít nhất 10 điểm sai. "
           "Cờ bật khi điểm số lật > t_flip (cùng công thức steps.flags).")
    return muc("2. Cờ low_conf", "".join(out), ghi, "tk-co")


# ---------- (3) tốc độ ----------
def _bang_ri(td):
    rows = []
    for p, v in td["nguoi"].items():
        rows.append(dict(p=p, m=num(v["manual"], 1), a=num(v["assisted"], 1), nm=v["n_manual"], na=v["n_assisted"], r=num(v["r"], 3) if v["r"] is not None else "—",
                         ok=raw("✓ nhanh hơn" if (v["r"] is not None and v["r"] < 1) else ("✗ chậm hơn" if v["r"] is not None else "—"))))
    return bang([("Người", "p", "l"), ("Manual: giây/mặt", "m", "r"), ("n", "nm", "r"), ("Assisted: giây/mặt", "a", "r"), ("n", "na", "r"), ("r_i = assisted ÷ manual", "r", "r"), ("r_i < 1", "ok", "l")], rows)


def muc_toc_do(st):
    td = st["toc_do"]
    if td.get("trong"):
        extra = ""
        if td.get("rows") is not None and td.get("nguoi"):
            extra = "<h5>Đã có</h5>" + _bang_ri(td)
        return muc("3. Tốc độ gán (giao thức P5)", trong(td["trong"]) + extra, mid="tk-td")
    ket = KET_LUAN[td["ket_luan"]]
    lo, hi = td["ktc90_pct"]
    out = [tiles(tile(num(td["nhanh_hon_pct"], 1, "%"), "nhanh hơn gán tay (1 − TB nhân r_i)", td["n_nguoi"], chip(td["ket_luan"]), title="Mục tiêu: nhanh hơn >= 20%, và >= 4/5 người có r_i < 1"),
                 tile(f'{num(lo, 1)} – {num(hi, 1)}%', "KTC 90% (bootstrap 2.000 lần, seed 28)", td["n_nguoi"]),
                 tile(num(td["tb_nhan"], 3), "TB nhân của r_i", td["n_nguoi"], f'{td["n_r_nho_hon_1"]}/{td["n_nguoi"]} người có r_i &lt; 1'),
                 tile(num((td["gio"] or {}).get("gio_1000"), 1, " giờ"), "giờ tiết kiệm / 1.000 mặt (trộn)", (td["gio"] or {}).get("n_assisted")))]
    top = max(30.0, (hi or 0) * 1.1, td["nhanh_hon_pct"] * 1.1)
    out.append(thanh([(e("Nhanh hơn gán tay"), max(td["nhanh_hon_pct"], 0.0), NEUTRAL, "1 − TB nhân r_i", td["n_nguoi"])], lambda v: num(v, 1), vach=(20.0, "mục tiêu nhanh hơn 20%"), toi_da=top, don_vi="%"))
    out.append("<h5>Từng người</h5>" + _bang_ri(td))
    if td["thieu"]:
        out.append('<div class="tk-note tk-warn">Không có r_i: ' + e("; ".join(f"{p} — {why}" for p, why in td["thieu"])) + ".</div>")
    ds = td["do_nhay"]
    out.append('<div class="tk-note"><b>Độ nhạy: bỏ ngoại lai.</b> ' + (
        f'Bỏ {ds["n_bo"]} dòng (ngoại lai và gián đoạn): nhanh hơn {num(ds["nhanh_hon_pct"], 1)}% (TB nhân {num(ds["tb_nhan"], 3)}, {ds["n_nguoi"]} người). Chỉ số chính ở trên KHÔNG bỏ các dòng này, đúng giao thức.'
        if ds["tb_nhan"] is not None else f'Bỏ {ds["n_bo"]} dòng thì còn dưới {3} người đủ hai điều kiện: không tính được.') + "</div>")
    if td["ngoai_lai"]:
        out.append("<h5>Dòng ngoại lai (vượt Q3 + 3·IQR trong (người, điều kiện)) — vẫn nằm trong chỉ số chính</h5>"
                   + bang([("Người", "person", "l"), ("Điều kiện", "condition", "l"), ("Mặt", "face_id", "l"), ("Giây", lambda r: num(r["seconds"], 1), "r"), ("Ngưỡng", lambda r: num(r["nguong"], 1), "r")], td["ngoai_lai"]))
    if td["gian_doan"]:
        out.append("<h5>Dòng bị gián đoạn (interrupted = 1) — vẫn nằm trong chỉ số chính</h5>"
                   + bang([("Người", "person", "l"), ("Điều kiện", "condition", "l"), ("Mặt", "face_id", "l"), ("Giây", lambda r: num(r["seconds"], 1), "r")], td["gian_doan"]))
    if td.get("nhom"):
        ten = {"nghieng_che": "Nghiêng hoặc bị che (manifest pose | occlusion = 1)", "con_lai": "Còn lại"}
        out.append("<h5>Giờ tiết kiệm / 1.000 mặt theo nhóm mặt</h5>" + bang(
            [("Nhóm", "ten", "l"), ("Manual: giây/mặt", lambda r: num(r["manual"], 1), "r"), ("n", "n_manual", "r"), ("Assisted: giây/mặt", lambda r: num(r["assisted"], 1), "r"), ("n", "n_assisted", "r"),
             ("Giờ tiết kiệm / 1.000 mặt", lambda r: "n quá nhỏ" if min(r["n_manual"], r["n_assisted"]) < N_NHO else num(r["gio_1000"], 1), "r")],
            [dict(ten=ten[k], **v) for k, v in td["nhom"].items()]))
        if td.get("nhom_khong_manifest"):
            out.append(f'<p class="tk-ghi">{td["nhom_khong_manifest"]} dòng có mặt không nằm trong manifest nên không xếp nhóm.</p>')
    elif td.get("nhom_ly_do"):
        out.append(f'<div class="tk-note">{e(td["nhom_ly_do"])}</div>')
    out.append("<h5>Bảng kiểu M24 (ngày, người, điều kiện; không tính khởi động)</h5>"
               + bang([("Ngày", "date", "l"), ("Người", "person", "l"), ("Điều kiện", "condition", "l"), ("Số ảnh", "so_anh", "r"), ("Số phút", lambda r: num(r["so_phut"], 1), "r")], td["m24"]))
    ghi = (f"{td['n_x']} dòng tính giờ (task m28-manual, m28-assisted, không khởi động); bỏ {td['n_bo_giay']} dòng giây trống/≤ 0, {td['n_warmup']} dòng khởi động, {td['n_khong_tn']} dòng ngoài task thí nghiệm. "
           "Đạt khi TB nhân r_i ≤ 0,80 và ≥ 4/5 người có r_i &lt; 1; Không đạt (đề xuất của P5): cận dưới KTC 90% &gt; 0,80; còn lại Chưa kết luận. "
           "Tệp: " + e(", ".join(td["files"])))
    return muc("3. Tốc độ gán (giao thức P5)", "".join(out), ghi, "tk-td")


def muc_giay_ra(st):
    gr = st["giay_ra"]
    if gr.get("trong"):
        return muc("3b. Giây rà soát mỗi mặt", trong(gr["trong"]), mid="tk-gr")
    t = gr["tong"]
    out = [tiles(tile(num(t["trung_vi"], 1, " giây"), "trung vị giây rà/mặt", t["n"], f'IQR {num(t["q1"], 1)} – {num(t["q3"], 1)}'),
                 tile(num(t["phut_100"], 1, " phút"), "phút cho 100 mặt (trung vị × 100)", t["n"]),
                 tile(num(t["n_ngoai_lai"], 0), f'mặt rà quá {num(gr["nguong_ngoai_lai"], 0)} giây (có thể nghỉ giữa chừng)', None, "đếm riêng, không vào số khác"))]
    cols = [("Người", "nguoi", "l"), ("n", "n", "r"), ("Trung vị (giây)", lambda r: "n quá nhỏ" if r["n"] < N_NHO else num(r["trung_vi"], 1), "r"),
            ("IQR (giây)", lambda r: "n quá nhỏ" if r["n"] < N_NHO else f'{num(r["q1"], 1)} – {num(r["q3"], 1)}', "r"),
            ("Phút / 100 mặt", lambda r: "n quá nhỏ" if r["n"] < N_NHO else num(r["phut_100"], 1), "r"), (f'> {num(gr["nguong_ngoai_lai"], 0)} giây', "n_ngoai_lai", "r")]
    out.append("<h5>Theo người rà</h5>" + bang(cols, gr["theo_nguoi"]))
    out.append("<h5>Theo người rà và lượt</h5>" + bang([cols[0], ("Lượt", "luot", "l")] + cols[1:], gr["theo_luot"]))
    if gr["day_du"]:
        d = gr["day_du"]
        out.append(f'<div class="tk-note"><b>Chi phí đầy đủ (ước lượng):</b> sửa nháp {num(d["sua_nhap"], 1)} giây + rà {num(d["ra"], 1)} giây = {num(d["tong"], 1)} giây/mặt, so với gán tay {num(d["manual"], 1)} giây/mặt '
                   f'→ nhanh hơn {num(d["nhanh_hon_pct"], 1)}%. Đây là phép cộng trung bình với trung vị, chỉ để thấy chi phí đầy đủ, không thay chỉ số chính ở mục 3.</div>')
    ghi = ("Đây là thời gian QUYẾT ĐỊNH Nhận/Gán tay/Bỏ (cột seconds của triage_&lt;người&gt;.csv), <b>không phải</b> thời gian gán điểm. Tổng giây của mặt = tổng các dòng có giây; "
           f'ô trống (lần bấm đầu phiên, Hoàn tác, triage_auto) bị bỏ. Guideline: rà tối đa {num(gr["guideline"], 0)} giây/mặt.')
    return muc("3b. Giây rà soát mỗi mặt (chỉ số KHÁC với tốc độ gán)", "".join(out), ghi, "tk-gr")


# ---------- tiến độ ----------
def muc_tien_do(st):
    td = st["tien_do"]
    out = []
    rows = [dict(luot=r["luot"], task=r["task"] or "—", nguoi=p["nguoi"], da_ra=f'{p["da_ra"]}/{p["tong"]}', nhan=p["nhan"], gan_tay=p["gan_tay"], bo=p["bo"], chua=p["chua_ra"],
                 xong="✓ đã bấm Xong" if r["xong"] else "chưa Xong") for r in td["runs"] for p in r["nguoi"]]
    out.append("<h5>Rà soát (đã rà / tổng, mỗi người mỗi lượt)</h5>" + (bang([("Lượt", "luot", "l"), ("Task CVAT", "task", "l"), ("Người rà", "nguoi", "l"), ("Đã rà", "da_ra", "r"), ("Nhận", "nhan", "r"),
                                                                              ("Gán tay", "gan_tay", "r"), ("Bỏ", "bo", "r"), ("Chưa rà", "chua", "r"), ("Trạng thái", "xong", "l")], rows)
                                                                       if rows else trong(dict(ly_do="Chưa ai rà lượt nào.", can="runs\\<lượt>\\review\\triage_<Pk>.csv", ai="người rà (trang rà soát)"))))
    ck = [dict(luot=r["luot"], nguoi=w, n=n) for r in td["runs"] for w, n in sorted(r["ca_kho"].items())]
    out.append("<h5>Ca khó đã đánh dấu</h5>" + (bang([("Lượt", "luot", "l"), ("Người", "nguoi", "l"), ("Số ca", "n", "r")], ck)
                                                  if ck else trong(dict(ly_do="Chưa ai đánh dấu ca khó.", can="runs\\<lượt>\\ca_kho.csv (phím K ở tab Rà soát)", ai="người rà"))))
    out.append("<h5>File nhãn đã xuất (raw\\ / final\\)</h5>" + (bang([("File", "file", "l"), ("Task", "task", "l"), ("Người", "nguoi", "l"), ("Ngày (DDMM)", "ngay", "l"), ("Thư mục", "kind", "l"),
                                                                       ("Điều kiện", "dieu_kien", "l"), ("Lượt", "luot", "l"), ("Ảnh", "n_anh", "r"), ("Ghép được", "n_khop", "r"), ("Ghi chú", "ghi_chu", "l")], td["nhan"])
                                                                if td["nhan"] else trong(dict(ly_do="Chưa có file nhãn nào.", can="raw\\<task>_<Pk>_<DDMM>.xml (P4: collect hoặc export.py)", ai="P4"))))
    if td["bam_gio"] is None:
        out.append("<h5>Dòng bấm giờ</h5>" + trong(dict(ly_do="Chưa có file bấm giờ nào.", can="timing_P1.csv … timing_P5.csv do facetimer.py ghi", ai="P5")))
    else:
        out.append("<h5>Dòng bấm giờ (người × điều kiện)</h5>" + bang([("Người", "nguoi", "l"), ("Điều kiện", "dieu_kien", "l"), ("Số dòng", "n", "r"), ("Kỳ vọng", lambda r: r["ky_vong"] if r["ky_vong"] is not None else "—", "r"),
                                                                         ("Dòng tính giờ", "n_tinh_gio", "r"), ("Kỳ vọng tính giờ", lambda r: r["ky_vong_tinh_gio"] if r["ky_vong_tinh_gio"] is not None else "—", "r")], td["bam_gio"]))
    return muc("4b. Tiến độ từng thành viên", "".join(out), e(td["ghi_chu_ky_vong"]), "tk-tdo")


def noi_dung(st):
    return (phan_dau(st) + muc_chat_luong(st) + muc_co(st) + muc_toc_do(st) + muc_giay_ra(st) + muc_so_luong(st) + muc_tien_do(st))


# ---------- CSS ----------
CSS = """
.tk-root { font-size: 14px; color: var(--body-text-color); line-height: 1.45; }
.tk-root h2 { margin: 0 0 6px; font-size: 20px; } .tk-root h3 { margin: 22px 0 6px; font-size: 17px; padding-top: 6px; border-top: 1px solid var(--border-color-primary); }
.tk-root h4 { margin: 16px 0 6px; font-size: 15px; } .tk-root h5 { margin: 12px 0 4px; font-size: 13.5px; color: var(--body-text-color-subdued); }
.tk-meta { font-size: 12.5px; color: var(--body-text-color-subdued); margin-bottom: 6px; overflow-wrap: anywhere; }
.tk-ghi { font-size: 12.5px; color: var(--body-text-color-subdued); margin: 4px 0 8px; overflow-wrap: anywhere; }
.tk-note { margin: 6px 0; padding: 7px 10px; border: 1px solid var(--border-color-primary); border-radius: 8px; background: var(--background-fill-secondary); font-size: 13px; overflow-wrap: anywhere; }
.tk-note.tk-warn { border-color: #d97706; background: color-mix(in srgb, #d97706 12%, transparent); }
.tk-trong { margin: 8px 0; padding: 10px 12px; border: 2px dashed var(--border-color-primary); border-radius: 10px; background: var(--background-fill-secondary); overflow-wrap: anywhere; }
.tk-can { margin-top: 4px; font-size: 12.5px; color: var(--body-text-color-subdued); }
.tk-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; margin: 8px 0; }
.tk-tile { padding: 9px 11px; border: 1px solid var(--border-color-primary); border-radius: 10px; background: var(--block-background-fill); min-width: 0; }
.tk-tv { font-size: 22px; font-weight: 800; line-height: 1.15; overflow-wrap: anywhere; } .tk-tl { font-size: 12.5px; color: var(--body-text-color-subdued); }
.tk-tn { font-size: 12px; color: var(--body-text-color-subdued); } .tk-tg { margin-top: 3px; font-size: 12.5px; overflow-wrap: anywhere; }
.tk-bars { display: flex; flex-direction: column; gap: 5px; margin: 6px 0; }
.tk-row { display: grid; grid-template-columns: minmax(90px, 30%) minmax(60px, 1fr) minmax(70px, auto); gap: 8px; align-items: center; }
.tk-lab { font-size: 13px; overflow-wrap: anywhere; } .tk-val { font-size: 13px; font-variant-numeric: tabular-nums; text-align: right; }
.tk-n { color: var(--body-text-color-subdued); font-size: 11.5px; }
.tk-bar { position: relative; height: 14px; border-radius: 3px; background: var(--background-fill-secondary); border: 1px solid var(--border-color-primary); }
.tk-bar.tk-na { background: repeating-linear-gradient(45deg, transparent 0 6px, var(--border-color-primary) 6px 7px); }
.tk-fill { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 2px; }
.tk-vach { position: absolute; top: -3px; bottom: -3px; width: 2px; background: var(--body-text-color); }
.tk-vach-lab { font-size: 12px; color: var(--body-text-color-subdued); }
.tk-sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: baseline; }
.tk-chip { display: inline-block; padding: 1px 9px; border-radius: 999px; font-size: 12.5px; font-weight: 700; border: 1px solid var(--border-color-primary); color: var(--body-text-color); }
.tk-chip.tk-ok { background: color-mix(in srgb, #16a34a 18%, transparent); border-color: #16a34a; }
.tk-chip.tk-bad { background: color-mix(in srgb, #dc2626 16%, transparent); border-color: #dc2626; }
.tk-chip.tk-mid { background: color-mix(in srgb, #d97706 16%, transparent); border-color: #d97706; }
.tk-tw { overflow-x: auto; max-width: 100%; margin: 4px 0 8px; }
.tk-table { border-collapse: collapse; font-size: 13px; width: 100%; }
.tk-table th, .tk-table td { text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--border-color-primary); vertical-align: middle; background: transparent; white-space: nowrap; }
.tk-table th { font-size: 12px; color: var(--body-text-color-subdued); font-weight: 700; } .tk-table .tk-r { text-align: right; font-variant-numeric: tabular-nums; }
.tk-stack { display: flex; height: 12px; min-width: 90px; border-radius: 3px; overflow: hidden; border: 1px solid var(--border-color-primary); }
.tk-seg { display: block; height: 100%; }
@media (max-width: 600px) { .tk-row { grid-template-columns: 1fr; gap: 2px; } .tk-val { text-align: left; } .tk-tv { font-size: 19px; } }
"""

PAGE_VARS = """
:root { --body-text-color: #1f2937; --body-text-color-subdued: #6b7280; --border-color-primary: #d1d5db; --background-fill-primary: #ffffff;
        --background-fill-secondary: #f3f4f6; --block-background-fill: #ffffff; }
@media (prefers-color-scheme: dark) { :root { --body-text-color: #e5e7eb; --body-text-color-subdued: #9ca3af; --border-color-primary: #374151;
        --background-fill-primary: #111827; --background-fill-secondary: #1f2937; --block-background-fill: #111827; } }
body { margin: 0; padding: 16px; background: var(--background-fill-primary); font-family: ui-sans-serif, system-ui, "Segoe UI", sans-serif; }
.tk-page { max-width: 1100px; margin: 0 auto; }
"""

NGUON_DONG = ("Nguồn dữ liệu: YawDD và DrivFace (bộ nghiên cứu công khai, dùng học thuật/nghiên cứu); nhãn 50 điểm do nhóm gán trong CVAT; nháp từ MediaPipe Face Landmarker (Apache-2.0). "
              "Dự án M28 là <b>phi thương mại</b>: không phát tán, không đăng lại, không giao bên thứ ba. Trang này chỉ có số liệu tổng hợp, không có ảnh mặt người lái xe và không có mã tài xế.")


def trang_tinh(st):
    """Một file HTML tự chứa (CSS nội tuyến, sáng/tối theo prefers-color-scheme, rộng 420 px vẫn đọc được). Không ảnh, không script, không đường dẫn tuyệt đối."""
    m = st["meta"]
    files = m["nhan_dung"]
    nhan = ("<h3>Nguồn</h3><p class=\"tk-ghi\">File nhãn đã dùng (tên tương đối): " + (e(", ".join(files)) if files else "chưa có") + ".</p>")
    return ("<!doctype html><html lang=\"vi\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>Thống kê M28</title><style>" + PAGE_VARS + CSS + "</style></head><body><div class=\"tk-page tk-root\"><h2>Thống kê M28 — chỉ số model và tốc độ gán</h2>"
            + f'<p class="tk-ghi">{NGUON_DONG}</p>' + noi_dung(st) + nhan + "</div></body></html>\n")
