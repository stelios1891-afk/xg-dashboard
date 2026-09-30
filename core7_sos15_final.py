"""
core7_sos15_final.py — ΤΕΣΤ 1/10/2026 (Στελιος: «τρεξε το τεστ για την 15+ — πως βελτιωνει συνολικα το σωστο SoS και γιατι αξιζει»).
Εκδοχες μηχανης: ΣΗΜΕΡΑ (παλιο SoS 1.5 @7-14) · ΣΩΣΤΟ 1.0 @7-14 · ΣΩΣΤΟ 0.5 / 1.0 / 1.5 ΟΛΗ τη σεζον.
(Με «@7-14» οι ωμες προβλεψεις της 15+ ειναι ΙΔΙΕΣ με σημερα· αλλαζει μονο η αγκυρα, που μαθαινει απο τις 7-14.)
ΜΕΤΡΑ (αγων. 15+, md≥14):
  (Α) ακριβεια: RPS 1Χ2 με την αγκυρα οπως ειναι live (.7), ανα σεζον · πληροφορια ΠΕΡΑ απο το κλεισιμο: gd ~ s_κλεισ + b·(s_μοντ − s_κλεισ)
  (Β) προλαβαινει την αγορα: κινηση Crown ανοιγμα→κλεισιμο ~ (μοντελο − ανοιγμα)
  (Γ) picks στο κλεισιμο, 3 βιβλια (Pinnacle, Crown, Bet365): dogs = κανονας live (αγκυρα w=1 στις κοντες) · φαβορι = αγκυρα .7 + σωστα τεταρτα ≥10%
  (Δ) ανταλλαγη picks vs σημερα (Pinnacle): κοινα / μονο νεα / μονο παλια
ΠΡΟ-ΔΗΛΩΣΗ — μια εκδοχη ΑΝΤΙΚΑΘΙΣΤΑ τη σημερινη αν ΟΛΑ:
  (1) RPS ολα τα ματς md≥6 καλυτερο σε ≥3/4 σεζον (απο core7_sos_current: ✓ για ολες τις «σωστες»)
  (2) RPS 15+ οχι χειροτερο (μεσος ≤ σημερα + 0.00005)
  (3) dogs 15+: μοναδες ≥ σημερα σε ≥2/3 βιβλια
  (4) φαβορι 15+: μοναδες ≥ σημερα σε ≥2/3 βιβλια
Δεν αλλαζει τιποτα live.
"""
import sys, io, os, json, glob, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_anchor_test.py', encoding='utf-8').read()
pre = src[:src.index('res = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 's15'}
with contextlib.redirect_stdout(_Q()):
    exec(pre, g)
D, run, picks, sup = g['D'], g['run'], g['picks'], g['sup']
SEAS = sorted(D.season.unique())
key = ['league', 'season', 'h', 'a', 'date']
VAR = [('ΣΗΜΕΡΑ', 'base'), ('ΣΩΣΤΟ 1.0 @7-14', 'cur_1.0_6_13'),
       ('ΣΩΣΤΟ 0.5 ολη', 'cur_0.5_6_40'), ('ΣΩΣΤΟ 1.0 ολη', 'cur_1.0_6_40'), ('ΣΩΣΤΟ 1.5 ολη', 'cur_1.5_6_40')]
if os.environ.get('SOS15_SET') == 'fav075':    # 1/10: φαβορι 15+ ανα σεζον με 0.75
    VAR = [('ΣΗΜΕΡΑ', 'base'), ('ΣΩΣΤΟ 0.75 @7-14', 'cur_0.75_6_13')]
if os.environ.get('SOS15_SET') == 'w714':      # 1/10: ποιο βαρος στις 7-14 δινει καλυτερη βαση (μεσω αγκυρας) για την 15+
    VAR = [('ΣΗΜΕΡΑ', 'base'), ('0 (χωρις)', 'nosos')] + [(f'ΣΩΣΤΟ {w} @7-14', f'cur_{w}_6_13') for w in ('0.25', '0.5', '0.75', '1.0', '1.25', '1.5', '2.0')]
def load(v):
    P = pd.read_csv(f'core7_mech_preds_{v}.csv', dtype={'season': str, 'mid': str}); P = P[P.md >= 6]; P['date'] = pd.to_datetime(P.date)
    m = D[key].merge(P[['league', 'season', 'home_name', 'away_name', 'date', 'xg_h', 'xg_a', 'mid']],
                     left_on=key, right_on=['league', 'season', 'home_name', 'away_name', 'date'], how='left')
    assert len(m) == len(D) and m.xg_h.notna().mean() > .99
    return m.xg_h.clip(.05, 6).values, m.xg_a.clip(.05, 6).values, m.mid.values
_, _, MID = load('base'); D['mid'] = MID
def parse_line(gs):
    try:
        p = [float(x) for x in str(gs).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception:
        return None
NG = {}
for f in glob.glob('nowgoal_odds/*.jsonl'):
    b = os.path.basename(f)
    if '_U' in b or '_deep' in b: continue
    for ln in open(f, encoding='utf-8'):
        try: r = json.loads(ln)
        except Exception: continue
        if r.get('cid') not in (3, 8) or not r.get('ah'): continue
        rows = []
        for mt, u, gg, dn in r['ah']:
            gl = parse_line(gg)
            try: oh, oa = float(u) + 1, float(dn) + 1
            except (TypeError, ValueError): continue
            if gl is None or mt is None or oh <= 1 or oa <= 1: continue
            rows.append((mt, -gl, oh, oa))
        if len(rows) >= 2:
            rows.sort(); NG[(str(r['mid']), 'Crown' if r['cid'] == 3 else 'Bet365')] = (rows[0][1:], rows[-1][1:])
def ev_ok(dist, side, ln, o):
    parts = [ln] if (ln * 4) % 2 == 0 else [ln - .25, ln + .25]; e = 0
    for L in parts:
        pw = sum(v for k, v in dist.items() if side * k + L > 0.01); pp = sum(v for k, v in dist.items() if abs(side * k + L) < 0.01)
        e += (pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)) / len(parts)
    return e
def rps1(h, a, yy):
    d = picks.gd_dist_dom(h, a); ph = sum(v for k, v in d.items() if k > 0); pdr = d.get(0, 0.0)
    o1, o2 = (1, 1) if yy == 2 else ((0, 1) if yy == 1 else (0, 0)); return ((ph - o1) ** 2 + (ph + pdr - o2) ** 2) / 2
def ols(y, X):
    X = np.column_stack([np.ones(len(y))] + X); b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b; cov = np.linalg.inv(X.T @ X) * (e @ e / (len(y) - X.shape[1])); return b, b / np.sqrt(np.diag(cov))
I15 = np.where((D.md >= 14).values)[0]
RES = {}
for lab, v in VAR:
    xh, xa, _ = load(v); D['xh'] = xh; D['xa'] = xa
    S0, SA = run(0, 0), run(0.5, 0)
    T = xh + xa; S7 = S0 + 0.7 * (SA - S0)
    rp = np.array([rps1(max((T[i] + S7[i]) / 2, .05), max((T[i] - S7[i]) / 2, .05), D.y.iat[i]) for i in I15])
    # πληροφορια περα απο κλεισιμο
    ok = D.s_mkt.iloc[I15].notna().values; ii = I15[ok]
    bI, tI = ols(D.gd.values[ii].astype(float), [D.s_mkt.values[ii], S7[ii] - D.s_mkt.values[ii]])
    # προλαβαινει (Crown)
    mv, dm = [], []
    for i in I15:
        q = NG.get((D.mid.iat[i], 'Crown'))
        if q is None: continue
        s0 = sup(*q[0], 2.7); s1 = sup(*q[1], 2.7); mv.append(s1 - s0); dm.append(S7[i] - s0)
    bA, tA = ols(np.array(mv), [np.array(dm)])
    rows = []
    for i in I15:
        r = D.loc[i]
        quotes = [('Pinnacle', (r.L, r.ah, r.aa) if r.L == r.L else None)]
        for bk in ('Crown', 'Bet365'):
            q = NG.get((r.mid, bk)); quotes.append((bk, q[1] if q else None))
        for bk, q in quotes:
            if q is None or q[0] != q[0]: continue
            L, oh, oa = q
            s = S0[i] + ((SA[i] - S0[i]) if abs(L) in (0.5, 0.75) else 0.0)
            for b in picks.evaluate_bet(max((T[i] + s) / 2, .05), max((T[i] - s) / 2, .05), L, oh, oa):
                rows.append((bk, r.season, r.league, r.mid, 'dog', 'κοντες' if b['hcap'] < 1 else 'βαθιες', picks.settle(r.gd, b['side'], b['hcap'], b['odds'])))
            if abs(L) >= 0.5:
                side = 1 if L < 0 else -1; ud = -abs(L); o = oh if side == 1 else oa
                if 1.70 <= o <= 2.10:
                    dist = picks.gd_dist_dom(max((T[i] + S7[i]) / 2, .05), max((T[i] - S7[i]) / 2, .05))
                    if ev_ok(dist, side, ud, o) >= 0.10:
                        rows.append((bk, r.season, r.league, r.mid, 'fav', 'κοντες' if ud > -1 else 'βαθιες', picks.settle(r.gd, side, ud, o)))
    RES[lab] = dict(rp=rp, info=(bI[2], tI[2]), ant=(bA[1], tA[1], len(mv)),
                    B=pd.DataFrame(rows, columns=['book', 'season', 'league', 'mid', 'role', 'depth', 'pnl']))
    print(f'{lab} ok', flush=True)
BK = ('Pinnacle', 'Crown', 'Bet365')
def fm(d):
    if len(d) < 5: return f'n{len(d):4d}          —        '
    ps = d.groupby('season').pnl.mean()
    return f'n{len(d):4d} {100*d.pnl.mean():+6.1f}% {d.pnl.sum():+6.1f}u {int((ps > 0).sum())}/4'
s15 = D.season.values[I15]; base = RES['ΣΗΜΕΡΑ']
print('\n(Α) ΑΚΡΙΒΕΙΑ 15+ (RPS με αγκυρα .7, μικροτερο = καλυτερο) · πληροφορια περα απο το κλεισιμο (b, t)')
for lab, _ in VAR:
    rp = RES[lab]['rp']; bw = sum(rp[s15 == s].mean() < base['rp'][s15 == s].mean() - 1e-12 for s in SEAS)
    print(f'  {lab:16s} RPS {rp.mean():.5f} (Δ {1e4*(rp.mean()-base["rp"].mean()):+.2f}×10⁻⁴) · καλυτερο {bw}/4 · ' +
          ' '.join(f'{s}: {rp[s15 == s].mean():.4f}' for s in SEAS) + f' · b {RES[lab]["info"][0]:+.3f} (t {RES[lab]["info"][1]:+.1f})')
print('\n(Β) ΠΡΟΛΑΒΑΙΝΕΙ ΤΗΝ ΑΓΟΡΑ στην 15+ (Crown ανοιγμα→κλεισιμο ~ μοντελο−ανοιγμα)')
for lab, _ in VAR:
    b, t, n = RES[lab]['ant']; print(f'  {lab:16s} κλιση {b:+.3f} (t {t:+.1f}) n{n}')
print('\n(Γ) PICKS 15+ στο κλεισιμο — Pinnacle | Crown | Bet365')
for role, dps in (('dog', ('κοντες', 'βαθιες', None)), ('fav', ('κοντες', 'βαθιες', None))):
    for dp in dps:
        print(f' [{"ΑΟΥΤΣΑΙΝΤΕΡ" if role == "dog" else "ΦΑΒΟΡΙ"} {dp or "ΣΥΝΟΛΟ"}]')
        for lab, _ in VAR:
            B = RES[lab]['B']; x = B[(B.role == role) & ((B.depth == dp) if dp else True)]
            print(f'   {lab:16s} ' + ' | '.join(fm(x[x.book == bk]) for bk in BK))
print(' [ΟΛΑ ΤΑ PICKS 15+ (dogs + φαβορι)]')
for lab, _ in VAR:
    B = RES[lab]['B']; print(f'   {lab:16s} ' + ' | '.join(fm(B[B.book == bk]) for bk in BK))
print('\n(Δ) ΑΝΤΑΛΛΑΓΗ vs ΣΗΜΕΡΑ (Pinnacle): κοινα · μονο στη νεα εκδοχη · μονο στη σημερινη')
kb = lambda B, role: B[(B.book == 'Pinnacle') & (B.role == role)].assign(k=lambda d: d.mid + d.depth)
for role in ('dog', 'fav'):
    print(f' [{"ΑΟΥΤΣΑΙΝΤΕΡ" if role == "dog" else "ΦΑΒΟΡΙ"}]')
    b0 = kb(base['B'], role)
    for lab, _ in VAR[1:]:
        b1 = kb(RES[lab]['B'], role)
        print(f'   {lab:16s} κοινα {fm(b1[b1.mid.isin(b0.mid)])} · νεα {fm(b1[~b1.mid.isin(b0.mid)])} · βγηκαν {fm(b0[~b0.mid.isin(b1.mid)])}')
print('\nανα λιγκα (Pinnacle, ολα τα picks 15+, μοναδες): ')
for lab, _ in VAR:
    B = RES[lab]['B']; lg = B[B.book == 'Pinnacle'].groupby('league').pnl.sum()
    print(f'   {lab:16s} ' + ' '.join(f'{k[:10]} {v:+.1f}' for k, v in lg.items()))
print('\nΚΡΙΣΗ (προ-δηλωμενη):')
bu = {(role, bk): base['B'][(base['B'].role == role) & (base['B'].book == bk)].pnl.sum() for role in ('dog', 'fav') for bk in BK}
for lab, _ in VAR[1:]:
    R = RES[lab]; B = R['B']
    c2 = R['rp'].mean() <= base['rp'].mean() + 0.00005
    c3 = sum(B[(B.role == 'dog') & (B.book == bk)].pnl.sum() >= bu[('dog', bk)] - 1e-9 for bk in BK) >= 2
    c4 = sum(B[(B.role == 'fav') & (B.book == bk)].pnl.sum() >= bu[('fav', bk)] - 1e-9 for bk in BK) >= 2
    print(f'  {lab:16s} (1) ακριβεια ολη σεζον ✓ · (2) RPS 15+ {"✓" if c2 else "✗"} · (3) dogs {"✓" if c3 else "✗"} · (4) φαβορι {"✓" if c4 else "✗"} → '
          f'{"ΑΝΤΙΚΑΘΙΣΤΑ" if c2 and c3 and c4 else "οχι"}')

print(chr(10) + 'ΑΝΑ ΣΕΖΟΝ — ΦΑΒΟΡΙ 15+ (picks · μοναδες) Pinnacle | Crown | Bet365')
for lab, _ in VAR:
    B = RES[lab]['B']; F = B[B.role == 'fav']
    print(f'  {lab}')
    for se in SEAS:
        print(f'    {se}: ' + ' | '.join(f"n{len(F[(F.book == bk) & (F.season == se)]):3d} {F[(F.book == bk) & (F.season == se)].pnl.sum():+5.1f}u" for bk in BK))
