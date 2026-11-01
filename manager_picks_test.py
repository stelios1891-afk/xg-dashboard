"""
manager_picks_test.py — 5/10/2026 (Στελιος «τρεξε τα τεστ»): ΑΛΛΑΓΗ ΠΡΟΠΟΝΗΤΗ ως ΦΙΛΤΡΟ/ΣΗΜΑΝΣΗ πανω στα ΠΡΑΓΜΑΤΙΚΑ picks CORE7.
Picks: μηχανη live (σωστο SoS, νεες κοκκινες) + κανονες live — dogs 15+ (αγκυρα στις κοντες), φαβορι 15+ (αγκυρα .7, σωστα τεταρτα ≥10%),
dogs 7-14 (ιδιος κανονας, χαρτινα) · κλεισιμο Pinnacle / Crown / Bet365 · 2223-2526.
Σημαιες (απο manager_study, καθαρισμενες αλλαγες):
  ΝΕΟΣ 1-8  = η ομαδα ειναι στα 1-8 πρωτα ματς μετα απο αλλαγη μεσα στη σεζον · υποτυποι: μονιμος-μετα-απο-προσωρινο / «κακη και στα δυο»
  ΚΑΛΟΚ.    = η ομαδα αλλαξε προπονητη το καλοκαιρι (φετινη σεζον)
Για καθε σημαια: picks ΥΠΕΡ της σημασμενης ομαδας και picks ΚΟΝΤΡΑ της (ο αντιπαλος εχει τη σημαια).
ΠΡΟ-ΔΗΛΩΣΗ ΦΙΛΤΡΟΥ (κοβουμε picks ΥΠΕΡ σημασμενης ομαδας): (1) τα κομμενα picks αρνητικα σε ≥2/3 βιβλια, (2) αρνητικα σε ≥3/4 σεζον
(μεσος βιβλιων), (3) n ≥ 20 ανα βιβλιο, (4) οι μοναδες των υπολοιπων ≥ σημερα σε ≥2/3 βιβλια. Αλλιως: μονο πληροφορια (⚠).
"""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
def grab(path, stop, name):
    s = open(path, encoding='utf-8').read(); s = s[:s.index(stop)].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
    g = {'__name__': name}
    with contextlib.redirect_stdout(_Q()): exec(s, g)
    return g
gm = grab('manager_study.py', '# ---- μετα-παραθυρα ----', 'ms')
T, E = gm['T'], gm['E']
gs = grab('core7_sos15_final.py', 'RES = {}', 'sf')
D, run_L, load, NG, picks, ev_ok = gs['D'], gs['run_L'], gs['load'], gs['NG'], gs['picks'], gs['ev_ok']
xh, xa, _ = load('cur_0.75_6_13~emps'); D['xh'] = xh; D['xa'] = xa
S0, SA = run_L(0, 0, 6), run_L(0.5, 0, 6); S7 = S0 + 0.7 * (SA - S0); Tt = xh + xa
# ---- picks με πλευρα ----
P = []
for i in np.where((D.md >= 6).values)[0]:
    r = D.loc[i]; per = '15+' if r.md >= 14 else '7-14'
    quotes = [('Pinnacle', (r.L, r.ah, r.aa) if r.L == r.L else None)] + [(bk, (NG.get((r.mid, bk)) or (None, None))[1]) for bk in ('Crown', 'Bet365')]
    for bk, q in quotes:
        if q is None or q[0] != q[0]: continue
        L, oh, oa = q
        s = S0[i] + ((SA[i] - S0[i]) if abs(L) in (0.5, 0.75) else 0.0)
        for b in picks.evaluate_bet(max((Tt[i] + s) / 2, .05), max((Tt[i] - s) / 2, .05), L, oh, oa):
            P.append(dict(mid=r.mid, book=bk, season=r.season, per=per, role='dog', home=b['side'] == 1, pnl=picks.settle(r.gd, b['side'], b['hcap'], b['odds'])))
        if per == '15+' and abs(L) >= 0.5:
            side = 1 if L < 0 else -1; ud = -abs(L); o = oh if side == 1 else oa
            if 1.70 <= o <= 2.10:
                dist = picks.gd_dist_dom(max((Tt[i] + S7[i]) / 2, .05), max((Tt[i] - S7[i]) / 2, .05))
                if ev_ok(dist, side, ud, o) >= 0.10:
                    P.append(dict(mid=r.mid, book=bk, season=r.season, per=per, role='fav', home=side == 1, pnl=picks.settle(r.gd, side, ud, o)))
P = pd.DataFrame(P)
# ---- σημαιες ανα (mid, ομαδα) ----
TT = {t: g_.reset_index(drop=True) for t, g_ in T.groupby('team')}
FL = {}
SUMMER = set(zip(E[E.summer].team, E[E.summer].sea))
for e in E[~E.summer].itertuples():
    g_ = TT[e.team]
    for j in range(e.k, min(e.k + 8, len(g_))):
        r = g_.loc[j]
        if r.sea != e.sea: break
        perm_after = e.caretaker and r.coach == e.new
        bad = -0.35 < e.pre_luck < 0.20
        FL[(r.mid, e.team)] = dict(new18=True, perm_after_ct=perm_after, bad_both=bad, unlucky=e.pre_luck <= -0.35)
HOME = T.set_index(['mid', 'home']).team.to_dict()
def flags(mid, home):
    t = HOME.get((mid, home)); f = FL.get((mid, t), {})
    sea = T.loc[(T.mid == mid)].sea.iloc[0] if False else None
    return t, f
rows = []
SEA_OF = T.drop_duplicates('mid').set_index('mid').sea.to_dict()
for r in P.itertuples():
    tb, fb = HOME.get((r.mid, r.home)), None
    to = HOME.get((r.mid, not r.home))
    fb = FL.get((r.mid, tb), {}); fo = FL.get((r.mid, to), {})
    s = SEA_OF.get(r.mid)
    rows.append(dict(**r._asdict(), b_new18=bool(fb.get('new18')), b_perm=bool(fb.get('perm_after_ct')), b_bad=bool(fb.get('bad_both')), b_unl=bool(fb.get('unlucky')),
                     o_new18=bool(fo.get('new18')), o_perm=bool(fo.get('perm_after_ct')), o_bad=bool(fo.get('bad_both')),
                     b_summer=(tb, s) in SUMMER, o_summer=(to, s) in SUMMER))
X = pd.DataFrame(rows)
BK = ('Pinnacle', 'Crown', 'Bet365')
def fm(d):
    if len(d) < 5: return f'n{len(d):4d}' + ' ' * 22
    ps = d.groupby('season').pnl.mean()
    return f'n{len(d):4d} {100*d.pnl.mean():+6.1f}% {d.pnl.sum():+6.1f}u {int((ps > 0).sum())}/{ps.size}'
def block(sub, lab):
    print(f'\n[{lab}] σημερα: ' + ' | '.join(fm(sub[sub.book == b]) for b in BK))
    for col, nm in (('b_new18', 'ΥΠΕΡ ομαδας με ΝΕΟ προπονητη (ματς 1-8)'), ('b_perm', '   … μονιμος μετα απο προσωρινο'), ('b_bad', '   … ηταν «κακη και στα δυο»'),
                    ('b_unl', '   … ηταν «ατυχη»'), ('o_new18', 'ΚΟΝΤΡΑ σε ομαδα με ΝΕΟ προπονητη (1-8)'), ('o_perm', '   … μονιμος μετα απο προσωρινο'),
                    ('o_bad', '   … «κακη και στα δυο»'), ('b_summer', 'ΥΠΕΡ ομαδας με ΚΑΛΟΚΑΙΡΙΝΗ αλλαγη'), ('o_summer', 'ΚΟΝΤΡΑ σε ομαδα με ΚΑΛΟΚΑΙΡΙΝΗ αλλαγη')):
        x = sub[sub[col]]
        print(f'   {nm:44s} ' + ' | '.join(fm(x[x.book == b]) for b in BK))
    # κριτηρια φιλτρου
    for col, nm in (('b_new18', 'κοψιμο ΥΠΕΡ νεου 1-8'), ('b_perm', 'κοψιμο ΥΠΕΡ μονιμου-μετα-προσωρινο'), ('b_bad', 'κοψιμο ΥΠΕΡ «κακη και στα δυο»'), ('b_summer', 'κοψιμο ΥΠΕΡ καλοκαιρινης')):
        cut = sub[sub[col]]; keep = sub[~sub[col]]
        c1 = sum(cut[cut.book == b].pnl.sum() < 0 for b in BK) >= 2
        ps = cut.groupby('season').pnl.mean(); c2 = int((ps < 0).sum()) >= 3
        c3 = min(len(cut[cut.book == b]) for b in BK) >= 20
        c4 = sum(keep[keep.book == b].pnl.sum() >= sub[sub.book == b].pnl.sum() for b in BK) >= 2
        print(f'   ΚΡΙΣΗ {nm:36s}: (1){"✓" if c1 else "✗"} (2){"✓" if c2 else "✗"} ({int((ps < 0).sum())}/{ps.size}) (3){"✓" if c3 else "✗"} (4){"✓" if c4 else "✗"} → '
              + ('ΠΕΡΝΑ' if (c1 and c2 and c3 and c4) else 'οχι') + ' · μετα: ' + ' | '.join(fm(keep[keep.book == b]) for b in BK))
block(X[(X.role == 'dog') & (X.per == '15+')], 'ΑΟΥΤΣΑΙΝΤΕΡ 15+ (live)')
block(X[(X.role == 'fav') & (X.per == '15+')], 'ΦΑΒΟΡΙ 15+ (live)')
block(X[(X.role == 'dog') & (X.per == '7-14')], 'ΑΟΥΤΣΑΙΝΤΕΡ 7-14 (χαρτινα)')
block(X[X.per == '15+'], 'ΟΛΑ ΤΑ PICKS 15+')
