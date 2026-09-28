"""
core7_fav_window.py — 28/9/2026 ΤΕΣΤ 1: ΠΟΤΕ παιζονται τα ΦΑΒΟΡΙ στα εγχωρια (παραθυρο, οπως intl_window_test). ΜΟΝΟ τεστ.
Γραμμες: Nowgoal pre-match AH με ωρα καθε κινησης (Crown cid 3 [+deep], Bet365 cid 8), σεζον 2425-2526 (μονο αυτες κατεβασμενες).
Μοντελα φαβορι: A = σημερα+αγκυρα · D = χωρις συμπ.+πεν.0.76+αγκυρα (αγκυρα απο closing Pinnacle, core7_fav_tests). Αναφορα: LIVE dogs.
Κανονας: φαβορι γραμμη ≤ −0.5, 1.70-2.10, edge≥10% (p_cover, κουρεμα 3%). «Παραθυρο Χω» = ξεκινας να κοιτας Χ ωρες πριν τη σεντρα
(σεντρα ≈ τελευταια pre-match κινηση) και παιζεις την ΠΡΩΤΗ κινηση που περναει ο κανονας· «κλεισιμο» = τελευταια κινηση.
CLV = τιμη / τιμη κλεισιματος (μονο οταν η γραμμη του κλεισιματος ειναι ιδια).
"""
import sys, io, json, glob, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_fav_tests.py', encoding='utf-8').read()
g = {'__name__': 'win'}
with contextlib.redirect_stdout(_Q()):
    exec(src[:src.index("print('T2.")].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), g)
picks, MOD = g['picks'], g['MOD']
picks.DRAW_BOOST = 1.13
LIVE = g['load']('base').assign(s=lambda d: d.s0)      # σημερινο χωρις αγκυρα (για dogs)

def hk(v):
    v = float(v); return v + 1 if v < 1.5 else v
def line_of(s):
    s = str(s)
    if '/' in s:
        a, b = s.split('/'); return (float(a) + float(b)) / 2
    return float(s)
AH = {}
for f in glob.glob('nowgoal_odds/2425_*.jsonl') + glob.glob('nowgoal_odds/2526_*.jsonl'):
    bk = 'Crown'
    for ln in open(f, encoding='utf-8'):
        r = json.loads(ln)
        if r.get('cid') not in (3, 8): continue
        b = 'Crown' if r['cid'] == 3 else 'Bet365'
        rows = AH.setdefault((str(r['mid']), b), {})
        for x in (r.get('ah') or []):
            try:
                if x[1] in ('', None) or x[3] in ('', None) or x[2] in ('', None): continue
                rows[int(x[0])] = (-line_of(x[2]), hk(x[1]), hk(x[3]))
            except Exception:
                pass
print(f'ματς×βιβλιο με ιστορικο γραμμων: {len(AH)}')
WINS = [('72ω', 72), ('48ω', 48), ('24ω', 24), ('12ω', 12), ('6ω', 6), ('2ω', 2), ('κλεισιμο', None)]

def scan(Q, role):
    Z = Q[(Q.md >= 6) & Q.season.isin(['2425', '2526'])]
    out = []
    for r in Z.itertuples():
        lh, la = max((r.T + r.s) / 2, .05), max((r.T - r.s) / 2, .05); dist = picks.gd_dist(lh, la)
        for bk in ('Crown', 'Bet365'):
            mv = AH.get((r.mid, bk))
            if not mv or len(mv) < 2: continue
            ts = sorted(mv); ko = ts[-1]; cl = mv[ko]
            for wlab, W in WINS:
                cand = [ko] if W is None else [t for t in ts if ko - t <= W * 3600]
                for t in cand:
                    L, oh, oa = mv[t]; hit = None
                    for side, ud, odds in ((1, L, oh), (-1, -L, oa)):
                        ok = (ud <= -0.5) if role == 'fav' else (ud >= 0.5)
                        if ok and 1.70 <= odds <= 2.10:
                            pw, pp = picks.p_cover(dist, side, ud)
                            if pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp) >= 0.10:
                                hit = (side, ud, odds); break
                    if hit:
                        side, ud, odds = hit
                        cl_odds = (cl[1] if side == 1 else cl[2]) if abs((cl[0] if side == 1 else -cl[0]) - ud) < 1e-9 else np.nan
                        out.append(dict(book=bk, win=wlab, season=r.season, hrs=(ko - t) / 3600, pnl=picks.settle(r.gd, side, ud, odds),
                                        clv=odds / cl_odds - 1 if cl_odds == cl_odds else np.nan, w714=r.md <= 13))
                        break
    return pd.DataFrame(out)
for lab, Q, role in (('ΦΑΒΟΡΙ · A σημερα+αγκυρα', MOD['A σημερα+αγκυρα'], 'fav'), ('ΦΑΒΟΡΙ · D χωρις συμπ.+πεν.0.76+αγκυρα', MOD['D χωρις συμπ.+πεν.0.76+αγκυρα'], 'fav'),
                     ('ΦΑΒΟΡΙ · σημερινο ΧΩΡΙΣ αγκυρα', LIVE, 'fav'), ('ΑΟΥΤΣΑΙΝΤΕΡ · σημερινο (live)', LIVE, 'dog')):
    B = scan(Q, role)
    print(f'\n=== {lab} === (ROI μεσος Crown/Bet365 · n · μοναδες · CLV οπου ιδια γραμμη)')
    for part, m in (('15+', ~B.w714), ('7-14', B.w714)):
        cells = []
        for wlab, _ in WINS:
            d = B[m & (B.win == wlab)]
            if not len(d): cells.append(f'{wlab}: —'); continue
            roi = np.mean([d[d.book == b].pnl.mean() for b in ('Crown', 'Bet365') if (d.book == b).any()])
            cells.append(f"{wlab}: {100*roi:+.1f}% n{len(d)} {d.pnl.sum()/d.book.nunique():+.0f}u CLV {100*d.clv.mean():+.1f}%")
        print(f'  [{part}] ' + ' | '.join(cells))
