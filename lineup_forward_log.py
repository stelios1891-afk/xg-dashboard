# -*- coding: utf-8 -*-
"""lineup_forward_log.py — FORWARD ΤΕΣΤ ενδεκαδων: καταγραφη τη στιγμη της προβλεψης.

Για καθε επερχομενο ματς CORE7 (επομενες ~5 μερες) που εχει projected 11αδες:
γραφει ΤΩΡΑ το Δ ενδεκαδας (projected XI ability − baseline αναμενομενης) και για τις
δυο ομαδες, με χρονοσημανση. ΚΑΜΙΑ αναδρομικη ανακατασκευη: το Δ υπολογιζεται με τη
βαση παικτων ΟΠΩΣ ΕΙΝΑΙ σημερα (proαγωνιστικα δεδομενα μονο).
Αποδοσεις -> odds_history.jsonl (γραφεται ηδη απο scanner) · αποτελεσματα -> data-refresh.
Η αξιολογηση γινεται αργοτερα απο το lineup_forward_report.py.
Τρεχει σε data-refresh (καθημερινα) + predicted11-refresh (Παρ/Σαβ) μετα τους συλλεκτες.
"""
import sys, os, json, datetime
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard'))

OUT = 'lineup_forward.jsonl'
HORIZON_DAYS = 5

import build_data  # noqa: E402  (φερνει και το FotMob layer)
import picks       # noqa: E402

SLOPE = 0.9        # shift = SLOPE*(dh-da)/2 (ιδιο με predicted11_retro / Lineup Lab)

LAB = json.load(open('lineup_lab.json', encoding='utf-8'))


def xi_ability(tid, pids):
    t = LAB['teams'].get(str(tid))
    if not t:
        return None, 0
    pmap = {p['id']: p['rt'] for p in t['players']}
    vals = [pmap[i] for i in pids if i in pmap]
    if not vals:
        return None, 0
    return sum(vals) / len(vals), len(vals)


def load_projected_match():
    """predicted11 (ανα ματς): {(home_tid, away_tid): (ts, src, pids_h, pids_a)} — τελευταιο snapshot."""
    out = {}
    try:
        for line in open('projected_lineups.jsonl', encoding='utf-8'):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            k = (str(r.get('home_tid')), str(r.get('away_tid')))
            if None in k:
                continue
            if k not in out or (r.get('ts') or '') >= (out[k][0] or ''):
                ph = [int(p['pid']) for p in (r.get('xi_home') or []) if p.get('pid')]
                pa = [int(p['pid']) for p in (r.get('xi_away') or []) if p.get('pid')]
                out[k] = (r.get('ts'), r.get('src'), ph, pa)
    except FileNotFoundError:
        pass
    return out


def load_projected_team():
    """fantasy-coach/ligainsider (ανα ομαδα): {tid: (ts, src, pids)} — τελευταιο snapshot."""
    out = {}
    try:
        for line in open('projected_fc.jsonl', encoding='utf-8'):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            t = r.get('tid')
            if not t:
                continue
            if t not in out or (r.get('ts') or '') >= (out[t][0] or ''):
                out[t] = (r.get('ts'), r.get('src'),
                          [int(p['pid']) for p in (r.get('xi') or []) if p.get('pid')])
    except FileNotFoundError:
        pass
    return out


if __name__ == '__main__':
    pm = load_projected_match()
    pt = load_projected_team()
    now = datetime.datetime.now(datetime.timezone.utc)
    ts = now.isoformat(timespec='minutes')
    horizon = now + datetime.timedelta(days=HORIZON_DAYS)
    # ratings ΧΩΡΙΣ ενδεκαδες (live engine) — κλειδωνονται ΚΑΙ αυτα τη στιγμη της προβλεψης,
    # ωστε η συγκριση ΧΩΡΙΣ vs ΜΕ να μη χρειαζεται καμια αναδρομικη ανακατασκευη.
    Mp, id2name = picks.load_matches(list(build_data.LEAGUE_FOTMOB), [build_data.RATINGS_SEASON_DEFAULT])
    Mc, id2c = picks.load_matches(list(build_data.LEAGUE_FOTMOB), [build_data.CURRENT_SEASON])
    id2name.update(id2c)
    name2id = {v: k for k, v in id2name.items()}
    n = 0
    with open(OUT, 'a', encoding='utf-8') as fh:
        for lg in list(build_data.LEAGUE_FOTMOB):
            try:
                LR = build_data.league_ratings(lg, Mp, Mc, id2name=id2name, name2id=name2id)
                fixtures = LR['fixtures']
            except Exception as e:
                print(f'{lg}: fixtures σφαλμα {type(e).__name__}', flush=True)
                continue
            for f in fixtures:
                try:
                    ko = datetime.datetime.fromisoformat(str(f.get('utc')).replace('Z', '+00:00'))
                except Exception:
                    continue
                if not (now < ko <= horizon):
                    continue
                hid, aid = str(f.get('home_id')), str(f.get('away_id'))
                rec = pm.get((hid, aid))
                if rec:
                    pts, src, ph, pa = rec
                else:
                    th, ta = pt.get(hid), pt.get(aid)
                    if not th or not ta:
                        continue
                    pts, src, ph, pa = min(th[0] or '', ta[0] or ''), th[1], th[2], ta[2]
                bh = (LAB['teams'].get(hid) or {}).get('base')
                ba = (LAB['teams'].get(aid) or {}).get('base')
                ah, nh = xi_ability(hid, ph)
                aa, na = xi_ability(aid, pa)
                if None in (bh, ba, ah, aa) or nh < 8 or na < 8:
                    continue
                # xg μοντελου ΧΩΡΙΣ ενδεκαδες (live engine, κλειδωμα τωρα) + ΜΕ (shift)
                xh = xa = x2h = x2a = None
                rh = LR['blended'].get(int(hid)); ra = LR['blended'].get(int(aid))
                if rh and ra:
                    pf = build_data._predict_ratings(rh, ra, LR['lg_shots'], LR['lg_xgps'], LR['hf'])
                    xh, xa = pf['home_adj_xg'], pf['away_adj_xg']
                    sh = SLOPE * ((ah - bh) - (aa - ba)) / 2
                    x2h = round(max(xh + sh, 0.05), 3); x2a = round(max(xa - sh, 0.05), 3)
                fh.write(json.dumps(dict(
                    ts=ts, snap_ts=pts, src=src, lg=lg, fid=f.get('fid'),
                    home_id=int(hid), away_id=int(aid),
                    home=f.get('home_name'), away=f.get('away_name'), ko=str(f.get('utc')),
                    dh=round(ah - bh, 4), da=round(aa - ba, 4),
                    nh=nh, na=na,
                    xg_h=xh, xg_a=xa, xg2_h=x2h, xg2_a=x2a), ensure_ascii=False) + '\n')
                n += 1
    print(f'lineup_forward: {n} ματς καταγραφηκαν ({ts})')
