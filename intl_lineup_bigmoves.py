"""
intl_lineup_bigmoves.py — 2 ΤΕΣΤ 28/9/2026 (Στελιος: «η εμπειρια μου λεει οτι κουνιεται»).
Κινηση = υπεροχη αγορας (γκολ) απο την τιμη ≥70′ πριν (πριν τις ενδεκαδες) → κλεισιμο, ΜΟ Crown/SBOBET (Nowgoal), αγωνιστικα εθνικων 2020-2026.
Χαρακτηριστικα ενδεκαδας ανα ομαδα (vs ΣΥΝΗΘΙΣΜΕΝΗ 11αδα = οι 11 με τα περισσοτερα λεπτα στα 6 προηγουμενα ματς ≤400 ημ.):
  βασικοι στον ΠΑΓΚΟ (ντυθηκαν, δεν ξεκινησαν) · βασικοι ΕΚΤΟΣ αποστολης · ΣΤΑΡ (top-3 αξιας της συνηθισμενης) στον παγκο / εκτος ·
  ΤΕΡΜΑΤΟΦΥΛΑΚΑΣ αλλαξε · βασικος ΕΠΙΘΕΤΙΚΟΣ (Striker/forward με τα περισσοτερα λεπτα) δεν ξεκινα · ΑΡΧΗΓΟΣ δεν ξεκινα ·
  «ελαφροτητα» = ln(αξια 11αδας / αξια συνηθισμενης 11αδας με βαση την αποστολη).
ΤΕΣΤ 1: ΜΕΓΑΛΕΣ κινησεις (≥0.25 γκολ): τι ειχε η ομαδα που «χτυπηθηκε» vs η αλλη ομαδα vs ματς χωρις κινηση (<0.05).
ΤΕΣΤ 2: ΜΟΝΟ ομαδες με αλλαγες της τελευταιας στιγμης: ποσο κινηθηκε η γραμμη ΚΟΝΤΡΑ τους (vs ομαδες χωρις αλλαγες)
         + αν παιζαμε κοντρα τους στην τιμη «πριν»: CLV / ROI.
Περιγραφικο — δεν αλλαζει τιποτα live.
"""
import sys, json, glob, bisect
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks, intl_pricing as ip
import os
ALL_TYPES = os.environ.get('ALL_TYPES') == '1'

src = open('intl_lineup_move_test.py', encoding='utf-8').read()
g = {'__name__': 'bigmoves'}
exec(src[:src.index("X = pd.read_csv('intl_xi60_rows.csv'")].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), g)
ROWS, sup, fair_at, PRE_MIN = g['ROWS'], g['sup'], g['fair_at'], g['PRE_MIN']

M = pd.read_csv('intl_matches.csv', dtype={'mid': str, 'season': str}); M['dt'] = pd.to_datetime(M.date); M = M.sort_values('dt')
M['gd'] = M.hs - M['as']
PV = json.load(open('intl_player_values.json', encoding='utf-8')); SQ = json.load(open('intl_squads.json', encoding='utf-8'))
RT = json.load(open('intl_player_ratings.json', encoding='utf-8'))
HV = {}
for pid, v in PV.items():
    h = sorted((d, float(x)) for d, x in (v.get('hist') or []) if d and x)
    if h: HV[int(pid)] = ([d for d, _ in h], [x for _, x in h])
    elif v.get('mv_now'): HV[int(pid)] = (['2026-09-19'], [float(v['mv_now'])])
def val(pid, dstr):
    h = HV.get(int(pid))
    if not h: return None
    i = bisect.bisect_right(h[0], dstr) - 1
    return h[1][i] if i >= 0 else h[1][0]
def pos(pid):
    p = str((PV.get(str(pid)) or {}).get('pos') or '').lower()
    if 'keeper' in p or 'goalkeeper' in p: return 'GK'
    if 'striker' in p or 'forward' in p or 'winger' in p: return 'FW'
    return 'OT'

# ---- κινηση αγορας ανα ματς (ΜΟ βιβλιων) ----
MOVE = {}
for (mid, bk), ah in ROWS.items():
    pre = [z for z in ah if z[0] >= PRE_MIN]
    if not pre or pre[-1][0] > 24 * 60 or ah[-1][0] > 30:
        continue
    p, c = pre[-1], ah[-1]
    MOVE.setdefault(mid, []).append((sup(c[1], c[2], c[3]) - sup(p[1], p[2], p[3]), bk, p, c))

# ---- χαρακτηριστικα ενδεκαδας ----
HIST = {}; CAPT = {}; rows = []
COMP = set(M[M.ctype.isin(['nl', 'qual', 'tourn'])].mid)
for r in M.itertuples():
    s = SQ.get(r.mid)
    if not s: continue
    dstr = r.dt.strftime('%Y-%m-%d'); feats = {}
    for side, tid in (('h', r.hid), ('a', r.aid)):
        t = s.get(side) or {}; mins = {int(k): (v or 0) for k, v in (t.get('p') or {}).items()}; st = set(int(x) for x in (t.get('st') or []))
        past = [p for d, p in HIST.get(tid, []) if (r.dt - d).days <= 400][-6:]
        cpast = [c for d, c in CAPT.get(tid, []) if (r.dt - d).days <= 400][-6:]
        if len(past) >= 3 and len(st) >= 10 and len(mins) >= 14:
            tot = {}
            for p in past:
                for k, m_ in p.items(): tot[k] = tot.get(k, 0) + m_
            U = [k for k, _ in sorted(tot.items(), key=lambda kv: -kv[1])[:11]]
            uv = {k: (val(k, dstr) or 0) for k in U}
            key = sorted(U, key=lambda k: -uv[k])[:3]
            gk = [k for k in U if pos(k) == 'GK'][:1]
            fw = sorted([k for k in U if pos(k) == 'FW'], key=lambda k: -tot[k])[:1]
            capt = max(set(cpast), key=cpast.count) if cpast else None
            inq = [k for k in U if k in mins]
            rest = sorted([k for k in mins if k not in inq], key=lambda k: -(val(k, dstr) or 0))[:11 - len(inq)]
            ev = [val(k, dstr) for k in inq + rest]; xv = [val(k, dstr) for k in st]
            light = np.nan
            if sum(1 for x in ev if x) >= 9 and sum(1 for x in xv if x) >= 9:
                light = np.log((sum(x for x in xv if x) / sum(1 for x in xv if x)) / (sum(x for x in ev if x) / sum(1 for x in ev if x)))
            feats[side] = dict(
                bench=sum(1 for k in U if k in mins and k not in st), out=sum(1 for k in U if k not in mins),
                key_bench=int(any(k in mins and k not in st for k in key)), key_out=int(any(k not in mins for k in key)),
                gk=int(bool(gk) and gk[0] not in st), fw=int(bool(fw) and fw[0] not in st),
                capt=int(capt is not None and capt not in st), light=light)
        if mins and (r.ctype in ('nl', 'qual', 'tourn') or ALL_TYPES): HIST.setdefault(tid, []).append((r.dt, mins))   # 28/9: συνηθισμενη 11αδα ΜΟΝΟ απο επισημα
        rt = (RT.get(r.mid) or {}).get(side) or {}
        cs = [int(k) for k, v in rt.items() if v and len(v) > 1 and v[1]]
        if cs: CAPT.setdefault(tid, []).append((r.dt, cs[0]))
    if len(feats) == 2 and r.mid in COMP and r.mid in MOVE:
        mv = MOVE[r.mid]
        rows.append(dict(mid=r.mid, season=r.season, gd=int(r.gd), move=float(np.mean([x[0] for x in mv])), books=mv,
                         **{f'{k}_{sd}': v for sd in ('h', 'a') for k, v in feats[sd].items()}))
D = pd.DataFrame(rows)
print(f'αγωνιστικα ματς με ενδεκαδες + κινηση γραμμης: {len(D)}')
F = ['bench', 'out', 'key_bench', 'key_out', 'gk', 'fw', 'capt']
LAB = {'bench': 'βασικοι στον παγκο (μεσος αρ.)', 'out': 'βασικοι εκτος αποστολης (μεσος αρ.)', 'key_bench': 'ΣΤΑΡ (top-3 αξιας) στον παγκο',
       'key_out': 'ΣΤΑΡ εκτος αποστολης', 'gk': 'αλλαξε ο τερματοφυλακας', 'fw': 'βασικος επιθετικος δεν ξεκινα', 'capt': 'αρχηγος δεν ξεκινα',
       'light': '«ελαφροτητα» 11αδας (ln, <0 = ελαφρια)'}

# ---- ΤΕΣΤ 1 ----
def team_view(d, who):
    """who='hit' → η ομαδα ΚΟΝΤΡΑ στην οποια πηγε η γραμμη· 'other' → η αλλη."""
    out = {}
    for f in F + ['light']:
        vals = np.where((d.move < 0) == (who == 'hit'), d[f'{f}_h'], d[f'{f}_a'])
        out[f] = np.nanmean(vals)
    return out
big = D[D.move.abs() >= .25]; calm = D[D.move.abs() < .05]
print(f'\nΤΕΣΤ 1 — ΜΕΓΑΛΕΣ ΚΙΝΗΣΕΙΣ (≥0.25 γκολ στα τελευταια 70′): {len(big)} ματς ({100*len(big)/len(D):.1f}%) · ηρεμα ματς (<0.05): {len(calm)}')
th, to = team_view(big, 'hit'), team_view(big, 'other')
tc = {f: np.nanmean(np.concatenate([calm[f'{f}_h'].values, calm[f'{f}_a'].values])) for f in F + ['light']}
print(f"  {'':40s} {'ομαδα που «χτυπηθηκε»':>22s} {'η αλλη ομαδα':>14s} {'ηρεμα ματς':>12s}")
for f in F + ['light']:
    fmt = (lambda x: f'{x:.2f}') if f in ('bench', 'out', 'light') else (lambda x: f'{100*x:.0f}%')
    print(f"  {LAB[f]:40s} {fmt(th[f]):>22s} {fmt(to[f]):>14s} {fmt(tc[f]):>12s}")
# ποσες μεγαλες κινησεις «εξηγουνται» απο την ενδεκαδα;
def flag(d, sd):
    return ((d[f'bench_{sd}'] >= 2) | (d[f'key_bench_{sd}'] == 1) | (d[f'key_out_{sd}'] == 1) | (d[f'gk_{sd}'] == 1) | (d[f'fw_{sd}'] == 1) | (d[f'capt_{sd}'] == 1))
hit_home = big.move < 0
fh, fa = flag(big, 'h'), flag(big, 'a')
hit_flag = np.where(hit_home, fh, fa); oth_flag = np.where(hit_home, fa, fh)
print(f"  εξηγηση: η «χτυπημενη» ομαδα ειχε αλλαγη της τελευταιας στιγμης (παγκος≥2 / σταρ / ΤΦ / επιθετικος / αρχηγος): {100*hit_flag.mean():.0f}% "
      f"· η αλλη: {100*oth_flag.mean():.0f}% · ΚΑΜΙΑ απο τις δυο: {100*((~hit_flag) & (~oth_flag)).mean():.0f}%")
print('  οι 12 μεγαλυτερες κινησεις:')
MN = dict(zip(M.mid, M.hn + ' – ' + M.an)); MD = dict(zip(M.mid, M.date.str[:10]))
for r in big.reindex(big.move.abs().sort_values(ascending=False).index).head(12).itertuples():
    hs = 'h' if r.move < 0 else 'a'; os_ = 'a' if hs == 'h' else 'h'
    desc = lambda sd: f"παγκος {getattr(r, 'bench_' + sd)} εκτος {getattr(r, 'out_' + sd)}" + (' ΣΤΑΡ-παγκος' if getattr(r, 'key_bench_' + sd) else '') + (' ΣΤΑΡ-εκτος' if getattr(r, 'key_out_' + sd) else '') + (' ΤΦ' if getattr(r, 'gk_' + sd) else '') + (' ΕΠΙΘ' if getattr(r, 'fw_' + sd) else '') + (' ΑΡΧ' if getattr(r, 'capt_' + sd) else '')
    print(f"    {MD[r.mid]} {MN[r.mid]:38s} κινηση {r.move:+.2f} κοντρα στη {'γηπεδουχο' if hs == 'h' else 'φιλοξενουμενη'} · χτυπημενη: {desc(hs)} · αλλη: {desc(os_)}")

# ---- ΤΕΣΤ 2 ----
print('\nΤΕΣΤ 2 — ΜΟΝΟ ομαδες με αλλαγες της τελευταιας στιγμης: κινηση ΚΟΝΤΡΑ τους (γκολ) · % με κινηση κοντρα ≥0.10 · CLV / ROI αν παιζαμε κοντρα τους στην τιμη «πριν»')
TM = []
for r in D.itertuples():
    for sd, sgn in (('h', -1), ('a', 1)):       # κινηση κοντρα στη γηπεδουχο = −move
        TM.append(dict(r=r, sd=sd, against=sgn * r.move, **{f: getattr(r, f'{f}_{sd}') for f in F + ['light']}))
T = pd.DataFrame(TM)
def bets_against(sub):
    out = []
    for x in sub.itertuples():
        r = x.r; side = -1 if x.sd == 'h' else 1        # πονταρουμε την ΑΛΛΗ ομαδα
        for mv, bk, p, c in r.books:
            L, oh, oa = p[1], p[2], p[3]; ud, odds = (L, oh) if side == 1 else (-L, oa)
            s_cl = sup(c[1], c[2], c[3]); fc = fair_at(s_cl, side, ud)
            out.append((odds / fc - 1 if fc else np.nan, picks.settle(r.gd, side, ud, odds), r.season))
    return out
def line(lbl, sub):
    if len(sub) < 10:
        print(f'  {lbl:52s} n {len(sub):4d} —'); return
    a = sub.against; b = bets_against(sub); clv = np.nanmean([z[0] for z in b]); pnl = np.array([z[1] for z in b])
    seas = pd.DataFrame(b, columns=['c', 'p', 's']).groupby('s').p.mean()
    print(f'  {lbl:52s} n {len(sub):4d} · κινηση κοντρα {a.mean():+.3f} (±{a.std()/np.sqrt(len(a)):.3f}) · ≥0.10 κοντρα {100*(a >= .10).mean():4.1f}% '
          f'(υπερ {100*(a <= -.10).mean():4.1f}%) · CLV {clv*100:+.1f}% · ROI {pnl.mean()*100:+.1f}% (±{pnl.std()/np.sqrt(len(pnl))*100:.1f}) {int((seas > 0).sum())}/{len(seas)}')
none = T[(T.bench == 0) & (T.out == 0) & (T.gk == 0) & (T.fw == 0) & (T.capt == 0)]
line('ΚΑΜΙΑ αλλαγη (ιδια 11αδα με τη συνηθισμενη)', none)
line('1 βασικος στον παγκο', T[T.bench == 1])
line('2 βασικοι στον παγκο', T[T.bench == 2])
line('3+ βασικοι στον παγκο (ροτεισον)', T[T.bench >= 3])
line('5+ βασικοι στον παγκο (βαρυ ροτεισον)', T[T.bench >= 5])
line('ΣΤΑΡ (top-3 αξιας) στον παγκο', T[T.key_bench == 1])
line('ΣΤΑΡ εκτος αποστολης', T[T.key_out == 1])
line('αλλαξε ο τερματοφυλακας', T[T.gk == 1])
line('βασικος επιθετικος δεν ξεκινα', T[T.fw == 1])
line('αρχηγος δεν ξεκινα', T[T.capt == 1])
line('11αδα ≥30% ελαφρυτερη σε αξια', T[T.light <= -0.36])
line('ΟΠΟΙΑΔΗΠΟΤΕ απο τα παραπανω (παγκος≥2/σταρ/ΤΦ/επιθ/αρχ)', T[(T.bench >= 2) | (T.key_bench == 1) | (T.key_out == 1) | (T.gk == 1) | (T.fw == 1) | (T.capt == 1)])
D.drop(columns=['books']).to_csv('intl_lineup_bigmoves_rows' + ('_all' if ALL_TYPES else '') + '.csv', index=False)
