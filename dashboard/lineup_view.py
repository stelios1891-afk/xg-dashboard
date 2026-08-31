# -*- coding: utf-8 -*-
"""lineup_view.py — Lineup Lab: βοηθητικα (φορτωμα βασης, υπολογισμος Δ/προβολων, HTML)."""
import os, json
import html as _h
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TLOGO = 'https://images.fotmob.com/image_resources/logo/teamlogo/{}.png'
POS_ORD = {0: 0, 1: 1, 2: 2, 3: 3}


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
