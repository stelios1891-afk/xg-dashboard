# -*- coding: utf-8 -*-
"""lineup_view.py — Lineup Lab: βοηθητικα (φορτωμα βασης, υπολογισμος Δ/προβολων, HTML)."""
import os, json
import html as _h
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TLOGO = 'https://images.fotmob.com/image_resources/logo/teamlogo/{}.png'
POS_ORD = {0: 0, 1: 1, 2: 2, 3: 3}


SCEN_F = os.path.join(ROOT, 'lineup_scenarios.json')


def load_scenarios():
    try:
        return json.load(open(SCEN_F, encoding='utf-8'))
    except Exception:
        return {}


def save_side(mkey, side, ids, formation):
    """Αποθηκευση σεναριου ΜΙΑΣ ομαδας (side: 'home'/'away')."""
    import datetime
    sc = load_scenarios()
    ent = sc.get(mkey) or {}
    ent[side] = dict(xi=list(ids), f=formation,
                     saved=datetime.datetime.now().isoformat(timespec='minutes'))
    sc[mkey] = ent
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=14)).isoformat()
    sc = {k: v for k, v in sc.items()
          if max((v.get(s, {}).get('saved', '') for s in ('home', 'away')), default='') >= cutoff}
    json.dump(sc, open(SCEN_F, 'w', encoding='utf-8'), ensure_ascii=False)


def delete_side(mkey, side):
    sc = load_scenarios()
    if mkey in sc and side in sc[mkey]:
        del sc[mkey][side]
        if not sc[mkey]:
            del sc[mkey]
        json.dump(sc, open(SCEN_F, 'w', encoding='utf-8'), ensure_ascii=False)


def load_lab():
    return json.load(open(os.path.join(ROOT, 'lineup_lab.json'), encoding='utf-8'))


def team_of(lab, tid):
    return lab['teams'].get(str(tid))


def options(team):
    """Λιστα (label, id) για το multiselect: 11αδα πρωτα, μετα παγκος (κατα συμμετοχες/ρειτινγκ)."""
    pmap = {p['id']: p for p in team['players']}
    xi = [pid for pid in team['xi'] if pid in pmap]
    bench = sorted([p for p in team['players'] if p['id'] not in set(xi)],
                   key=lambda p: (POS_ORD.get(p['pos'], 9), -p['st15'], -p['rt']))
    ordered = [pmap[i] for i in xi] + bench
    labels = {}
    for p in ordered:
        pos = {0: 'GK', 1: 'DEF', 2: 'MID', 3: 'ATT'}.get(p['pos'], '?')
        tag = ' •νεος' if p['new'] else ''
        labels[p['id']] = f"{p['nm']} ({pos} {p['rt']:.2f}{tag})"
    return [(labels[p['id']], p['id']) for p in ordered]


FORMATIONS = {'Αυτοματο': None, '4-3-3': (4, 3, 3), '4-4-2': (4, 4, 2), '4-2-3-1': (4, 5, 1),
              '4-5-1': (4, 5, 1), '3-5-2': (3, 5, 2), '3-4-3': (3, 4, 3),
              '5-3-2': (5, 3, 2), '5-4-1': (5, 4, 1)}


def default_xi(team, counts=None):
    """Προτεινομενη 11αδα: αν counts=(DEF,MID,ATT) γεμιζει καθε γραμμη με τους
    κορυφαιους της (συμμετοχες βασικου -> ρειτινγκ)· αλλιως η αποθηκευμενη."""
    if counts is None:
        return list(team['xi'])
    players = team['players']
    rank = sorted(players, key=lambda p: (-p['st15'], -p['rt']))
    gks = [p for p in rank if p['pos'] == 0]
    xi = [gks[0]['id']] if gks else []
    for pos, need in zip((1, 2, 3), counts):
        xi += [p['id'] for p in rank if p['pos'] == pos][:need]
    if len(xi) < 11:                      # συμπληρωμα αν δεν φτανουν σε καποια γραμμη
        xi += [p['id'] for p in rank if p['id'] not in set(xi) and p['pos'] != 0][:11 - len(xi)]
    return xi[:11]


def xi_strength(team, ids):
    pmap = {p['id']: p for p in team['players']}
    vals = [pmap[i]['rt'] for i in ids if i in pmap]
    return float(np.mean(vals)) if vals else None


def adjust_xg(xg_h, xg_a, d_h, d_a, slope=0.9):
    """Μετρημενη ζυγαρια: Δ ενδεκαδας -> μετατοπιση διαφορας γκολ (συνολο αμεταβλητο)."""
    shift = slope * (d_h - d_a) / 2.0
    return max(xg_h + shift, 0.05), max(xg_a - shift, 0.05)


def ah_fair(xg_h, xg_a, side, hcap):
    """Fair odds για την πλευρα side στο χαντικαπ hcap (σωστος χειρισμος quarter)."""
    import picks as engine
    dist = engine.gd_dist(max(xg_h, 0.05), max(xg_a, 0.05))
    parts = [hcap] if (hcap * 4) % 2 == 0 else [hcap - 0.25, hcap + 0.25]
    pw = pp = 0.0
    for L in parts:
        w, p = engine.p_cover(dist, side, L)
        pw += w / len(parts); pp += p / len(parts)
    if pw <= 0:
        return None
    return (1 - pp) / pw


def latest_market(hid, aid):
    """Τελευταια καταγραφη αγορας (Pinnacle feed) για το ματς: γραμμη + αποδοσεις + 1Χ2."""
    key = f'{hid}_{aid}'
    best = None
    path = os.path.join(ROOT, 'odds_history.jsonl')
    if not os.path.exists(path):
        return None
    for line in open(path, encoding='utf-8'):
        try:
            r = json.loads(line)
        except Exception:
            continue
        if f"{r.get('hid')}_{r.get('aid')}" == key:
            best = r
    return best


def results_table_html(home, away, xh0, xa0, xh, xa, p0, p1, mkt):
    """Επιλογη Γ: πινακας ΠΡΙΝ / ΜΕ ΤΙΣ 11ΑΔΕΣ / ΑΓΟΡΑ σε αποδοσεις 1Χ2 + % αξιας."""
    def cell_before(v):
        return f'<td class="mut">{v:.2f}</td>' if v else '<td class="mut">—</td>'

    def cell_after(v1, v0):
        if not v1:
            return '<td>—</td>'
        d = v1 - (v0 or v1)
        if abs(d) < 0.005:
            arr = ''
        elif d < 0:
            arr = f' <span class="dn">▼ {d:+.2f}</span>'
        else:
            arr = f' <span class="up">▲ {d:+.2f}</span>'
        return f'<td class="big">{v1:.2f}{arr}</td>'

    def cell_mkt(mo, fair):
        if not mo:
            return '<td class="mut">—</td>'
        if fair:
            v = (mo / fair - 1) * 100
            dot = ' 🟢' if v >= 5 else (' 🔴' if v <= -5 else '')
            cls = 'dn' if v >= 5 else ('up' if v <= -5 else 'mut')
            return f'<td>{mo:.2f} <span class="{cls}">{v:+.0f}%{dot}</span></td>'
        return f'<td>{mo:.2f}</td>'

    mh, md, ma = (mkt or (None, None, None))
    css = """<style>
    *{box-sizing:border-box;margin:0;padding:0;}
    body{background:#0a0f1e;font-family:'DM Sans','Segoe UI',sans-serif;color:#e8edf8;padding:2px;}
    .score{color:#8fa3c8;font-size:12.5px;margin:2px 0 10px;}
    .score b{color:#e8edf8;font-family:'JetBrains Mono',monospace;font-size:15px;}
    .score .mut{color:#5a6b8c;}
    table{border-collapse:collapse;width:100%;background:#111827;border:1px solid #1e2d47;border-radius:12px;overflow:hidden;}
    th{font-size:10px;color:#6b7fa3;text-transform:uppercase;letter-spacing:1px;padding:9px 12px;
       border-bottom:1px solid #1e2d47;text-align:center;}
    th:first-child{text-align:left;}
    td{padding:10px 12px;text-align:center;font-family:'JetBrains Mono',monospace;font-size:15.5px;border-bottom:1px solid #121b30;}
    td.lbl{text-align:left;font-family:'DM Sans',sans-serif;font-size:12.5px;color:#8fa3c8;font-weight:600;}
    .dn{color:#34d17a;font-size:11px;} .up{color:#e05563;font-size:11px;}
    .big{font-weight:700;font-size:16.5px;} .mut{color:#5a6b8c;}
    .note{color:#5a6b8c;font-size:10.5px;margin-top:7px;}
    </style>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">"""
    return (css +
        f'<div class="score">Προβλεπομενο σκορ: <b>{xh:.2f} – {xa:.2f}</b> '
        f'<span class="mut">(απο {xh0:.2f} – {xa0:.2f})</span></div>'
        '<table><tr><th></th>'
        f'<th>1 ({_h.escape(home)[:14]})</th><th>X</th><th>2 ({_h.escape(away)[:14]})</th></tr>'
        f'<tr><td class="lbl">Δικα μας — ΠΡΙΝ</td>{cell_before(p0["hw_odds"])}{cell_before(p0["d_odds"])}{cell_before(p0["aw_odds"])}</tr>'
        f'<tr><td class="lbl">Δικα μας — ΜΕ ΤΙΣ 11ΑΔΕΣ</td>'
        f'{cell_after(p1["hw_odds"], p0["hw_odds"])}{cell_after(p1["d_odds"], p0["d_odds"])}{cell_after(p1["aw_odds"], p0["aw_odds"])}</tr>'
        f'<tr><td class="lbl">Αγορα (Pinnacle)</td>'
        f'{cell_mkt(mh, p1["hw_odds"])}{cell_mkt(md, p1["d_odds"])}{cell_mkt(ma, p1["aw_odds"])}</tr></table>'
        '<div class="note">▼ = η αποδοση επεσε (πιθανοτερη εκβαση με τις 11αδες σου) · ▲ = ανεβηκε · '
        'στην «Αγορα»: % αξιας εναντι του fair του σεναριου σου (🟢 η αγορα πληρωνει καλυτερα).</div>')


def strength_bar_html(nm_h, d_h, nm_a, d_a):
    def cell(nm, d):
        col = '#34d17a' if d > 0.015 else ('#e05563' if d < -0.015 else '#8fa3c8')
        word = 'ΕΝΙΣΧΥΜΕΝΗ' if d > 0.015 else ('ΑΠΟΔΥΝΑΜΩΜΕΝΗ' if d < -0.015 else 'κανονικη')
        return (f'<div style="flex:1;background:#111827;border:1px solid #1e2d47;border-radius:10px;'
                f'padding:10px 14px;font-family:DM Sans,sans-serif">'
                f'<div style="color:#6b7fa3;font-size:10px;letter-spacing:1px">{_h.escape(nm).upper()[:20]} · Δ ΕΝΔΕΚΑΔΑΣ</div>'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:20px;font-weight:700;color:{col}">'
                f'{d:+.3f}</span> <span style="color:{col};font-size:11px">{word}</span></div>')
    return ('<div style="display:flex;gap:10px;background:#0a0f1e">' + cell(nm_h, d_h) + cell(nm_a, d_a) + '</div>')
