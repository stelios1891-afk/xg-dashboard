# -*- coding: utf-8 -*-
"""euro_shadow_scan.py — Σκιωδης καταγραφη ευρωπαικων picks (League Phase 2627).

Τρεχει στον scanner μετα το euro_odds_scan. Για καθε επερχομενο καλυμμενο ματς με αποδοσεις:
υπολογιζει με το ΣΗΜΕΡΙΝΟ live stack (projections = V4+prior-EU w=2· pricing με EU draw
scale 0.85) τα edges για OUTSIDER και ΦΑΒΟΡΙ, με ΔΥΟ τιμολογησεις:
  e_live  = picks.p_cover ως εχει (το quarter συμψηφιστικο — οπως η εγχωρια live μηχανη)
  e_clean = σωστο quarter-aware split
Append-on-change στο euro_shadow.jsonl (state: euro_shadow_state.json). ΚΑΜΙΑ κριση εδω —
ο φακελος κρινεται στο τελος της League Phase.
"""
import os, json, datetime, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picks

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ_F = os.path.join(ROOT, 'euro_projections.json')
ODDS_F = os.path.join(ROOT, 'euro_odds_latest.json')
OUT_F = os.path.join(ROOT, 'euro_shadow.jsonl')
ST_F = os.path.join(ROOT, 'euro_shadow_state.json')


def eu_dist(xgh, xga, scale):
    dist = picks.gd_dist(max(xgh, 0.05), max(xga, 0.05))
    px = dist.get(0, 0.0)
    if px <= 0 or px >= 1 or scale == 1.0:
        return dist
    k = (1.0 - scale * px) / (1.0 - px)
    return {g: (p * scale if g == 0 else p * k) for g, p in dist.items()}


def cover_q(dist, side, line):
    parts = [line] if (line * 4) % 2 == 0 else [line - 0.25, line + 0.25]
    pw = pp = 0.0
    for L in parts:
        for k, p in dist.items():
            m = (k if side == 1 else -k) + L
            if m > 0.01:
                pw += p / len(parts)
            elif abs(m) <= 0.01:
                pp += p / len(parts)
    return pw, pp


def edge_of(pw, pp, o):
    return pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        P = json.load(open(PROJ_F, encoding='utf-8'))
        O = json.load(open(ODDS_F, encoding='utf-8')).get('odds', {})
    except Exception as e:
        print(f'λειπουν αρχεια ({e}) — τιποτα')
        return
    scale = float(P.get('eu_draw_scale', 1.0))
    try:
        st = json.load(open(ST_F, encoding='utf-8'))
    except Exception:
        st = {}
    n_new = 0
    with open(OUT_F, 'a', encoding='utf-8') as out:
        for m in P.get('matches', []):
            if not m.get('covered') or m.get('finished'):
                continue
            mk = O.get(str(m['mid']))
            if not mk or mk.get('line') is None:
                continue
            try:
                ko = datetime.datetime.fromisoformat(str(m['utc']).replace('Z', '+00:00'))
            except Exception:
                continue
            if ko < now:
                continue
            lf, oh, oa = float(mk['line']), mk.get('oh'), mk.get('oa')
            if not oh or not oa:
                continue
            dist = eu_dist(m['xgh'], m['xga'], scale)
            rec = dict(t=now.isoformat()[:16], ko=m['utc'], mid=str(m['mid']),
                       comp=m['comp'], rnd=m.get('round'),
                       home=m['home'], away=m['away'], hid=m['hid'], aid=m['aid'],
                       src_h=m.get('src_h'), src_a=m.get('src_a'),
                       xgh=m['xgh'], xga=m['xga'], line=lf, oh=oh, oa=oa,
                       tl=mk.get('tl'), to=mk.get('to'), tu=mk.get('tu'))
            for side, ln, o, tag in ((1, lf, oh, 'h'), (-1, -lf, oa, 'a')):
                pw, pp = picks.p_cover(dist, side, ln)
                rec[f'e_live_{tag}'] = round(edge_of(pw, pp, o), 4)
                pw2, pp2 = cover_q(dist, side, ln)
                rec[f'e_clean_{tag}'] = round(edge_of(pw2, pp2, o), 4)
            rec['dside'] = 1 if lf > 0 else (-1 if lf < 0 else (1 if oh > oa else -1))
            sig = f"{lf}|{oh}|{oa}|{rec['xgh']:.2f}|{rec['xga']:.2f}"
            if st.get(rec['mid']) == sig:
                continue
            st[rec['mid']] = sig
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')
            n_new += 1
    json.dump(st, open(ST_F, 'w', encoding='utf-8'))
    print(f'euro shadow: {n_new} νεες/αλλαγμενες εγγραφες')


if __name__ == '__main__':
    main()
