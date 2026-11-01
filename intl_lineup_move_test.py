"""
intl_lineup_move_test.py — ΤΕΣΤ 28/9/2026 (Στελιος: «ο στοχος ειναι να πιασουμε την πληροφορια ΠΡΙΝ κουνηθει η αγορα», αφορμη Γεωργια−Ουκρανια).
Για καθε αγωνιστικο ματς εθνικων με ιστορικο γραμμων Nowgoal (Crown cid 3, SBOBET cid 31, ωρα καθε κινησης):
  «ΠΡΙΝ» = τελευταια τιμη AH ≥70′ πριν τη σεντρα (πριν τις ενδεκαδες) · «ΚΛΕΙΣΙΜΟ» = τελευταια πριν τη σεντρα.
  Υπεροχη αγορας (γκολ) απο τη γραμμη AH (σωστα τεταρτα, T=2.6).
  ΕΚΠΛΗΞΗ ΕΝΔΕΚΑΔΑΣ (γηπ − φιλοξ) = ln(XI_h/XI_a) − ln(V23_h/V23_a): ποσο πιο «ελαφρια/βαρια» ειναι η 11αδα απ' οτι οι 23 της αποστολης.
ΕΡΩΤΗΣΕΙΣ
  Α. Κουνιεται η γραμμη (ΠΡΙΝ → ΚΛΕΙΣΙΜΟ) με την εκπληξη; ποσο; (γκολ ανα μοναδα ln)· και ΠΟΤΕ (λεπτα πριν τη σεντρα που γινεται η μιση κινηση).
  Β. Αν παιζαμε ΣΤΗΝ ΤΙΜΗ «ΠΡΙΝ» κοντρα στην ομαδα με την ελαφρια 11αδα (|εκπληξη| ≥ 0.2 / 0.3 / 0.5): CLV (vs κλεισιμο) και ROI.
  Γ. Με το ΜΟΝΤΕΛΟ: εκδοχη «11αδα» (w=0) vs «23» (w=1) στην τιμη «ΠΡΙΝ» (κανονες live: |γραμμη|≥0.5, 1.70-2.10, edge≥10%, κουρεμα 3%)·
     τα ΝΕΑ picks που βγαζει η εκδοχη 11αδας (οχι η 23): CLV και ROI.
Περιγραφικο — δεν αλλαζει τιποτα live. Ευνοικο αποτελεσμα = (Α) καθαρη κινηση με την εκπληξη ΚΑΙ (Β/Γ) θετικο CLV στην τιμη «ΠΡΙΝ».
"""
import sys, json, glob
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks, intl_pricing as ip

PRE_MIN = 70
M = pd.read_csv('intl_matches.csv', dtype={'mid': str, 'season': str})
KO = {m: pd.Timestamp(d).tz_localize('UTC').timestamp() for m, d in zip(M.mid, M.date)}

def hk(v):
    v = float(v); return v + 1 if v < 1.5 else v

def line_of(s):
    s = str(s)
    if '/' in s:
        a, b = s.split('/'); return (float(a) + float(b)) / 2
    return float(s)

def ok_row(x):
    return x[1] in ('', None) and not x[7] and x[4] not in (None, '') and x[5] not in (None, '', '0') and x[6] not in (None, '', '0')

ROWS = {}
for f in glob.glob('nowgoal_intl_odds/*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        r = json.loads(ln)
        if r.get('cid') not in (3, 31):
            continue
        mid = str(r['mid']); k = KO.get(mid)
        if k is None:
            continue
        ah = []
        for x in (r.get('ah') or []):
            if ok_row(x) and x[0] < k:
                try: ah.append(((k - x[0]) / 60, -line_of(x[4]), hk(x[5]), hk(x[6])))       # λεπτα πριν, γραμμη γηπεδουχου
                except Exception: pass
        ah.sort(key=lambda z: -z[0])
        if ah:
            ROWS[(mid, 'Crown' if r['cid'] == 3 else 'SBOBET')] = ah

T0 = 2.6
_cache = {}
def sup(line, oh, oa):
    key = (line, oh, oa)
    if key in _cache: return _cache[key]
    kk = 1 / oh + 1 / oa; tgt = (1 / oh) / kk; lo, hi = -5.0, 5.0
    parts = [line] if (line * 4) % 2 == 0 else [line - .25, line + .25]
    for _ in range(40):
        md = (lo + hi) / 2; d = picks.gd_dist(max((T0 + md) / 2, .1), max((T0 - md) / 2, .1))
        c = [picks.p_cover(d, 1, L) for L in parts]; pe = sum(a for a, _ in c) / max(sum(1 - b for _, b in c), 1e-9)
        lo, hi = (md, hi) if pe < tgt else (lo, md)
    _cache[key] = (lo + hi) / 2; return _cache[key]

def dist_s(s):
    return picks.gd_dist(max((T0 + s) / 2, .1), max((T0 - s) / 2, .1))

def fair_at(s, side, ud):
    return ip.ah_fair(dist_s(s), side, ud)

X = pd.read_csv('intl_xi60_rows.csv', dtype={'mid': str, 'season': str})      # απο intl_xi60_test.py (11αδα, 23, Elo diff, γκολ)
X['surp_v23'] = np.log(X.xi_h / X.xi_a) - np.log(X.v23_h / X.v23_a)
# ---- ΕΚΠΛΗΞΗ vs ΣΥΝΗΘΙΣΜΕΝΗ 11αδα (28/9 διορθωση): E = αξια της «αναμενομενης» 11αδας με βαση την αποστολη =
#      οι 11 με τα περισσοτερα λεπτα στα 6 προηγουμενα ματς (≤400 ημ.) που ΕΙΝΑΙ στην αποστολη + για οσους λειπουν απο την αποστολη
#      οι ακριβοτεροι των υπολοιπων ντυμενων. Εκπληξη ομαδας = ln(XI / E) (<0 = πιο ελαφρια 11αδα απο τη συνηθισμενη, π.χ. Ουκρανια).
import bisect
PV = json.load(open('intl_player_values.json', encoding='utf-8')); SQ = json.load(open('intl_squads.json', encoding='utf-8'))
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
MS = M.copy(); MS['dt'] = pd.to_datetime(MS.date); MS = MS.sort_values('dt')
HIST = {}; SURP = {}
for r in MS.itertuples():
    s = SQ.get(r.mid)
    if not s: continue
    dstr = r.dt.strftime('%Y-%m-%d'); out = {}
    for side, tid in (('h', r.hid), ('a', r.aid)):
        t = s.get(side) or {}; mins = {int(k): (v or 0) for k, v in (t.get('p') or {}).items()}; st = [int(x) for x in (t.get('st') or [])]
        past = [p for d, p in HIST.get(tid, []) if (r.dt - d).days <= 400][-6:]
        if len(past) >= 3 and len(st) >= 10 and len(mins) >= 14:
            tot = {}
            for p in past:
                for k, m_ in p.items(): tot[k] = tot.get(k, 0) + m_
            exp = [k for k, _ in sorted(tot.items(), key=lambda kv: -kv[1])[:11]]
            inq = [k for k in exp if k in mins]
            rest = sorted([k for k in mins if k not in inq], key=lambda k: -(val(k, dstr) or 0))[:11 - len(inq)]
            ev = [val(k, dstr) for k in inq + rest]; xv = [val(k, dstr) for k in st]
            if sum(1 for x in ev if x) >= 9 and sum(1 for x in xv if x) >= 9:
                E = sum(x for x in ev if x) * 11 / sum(1 for x in ev if x); XI = sum(x for x in xv if x) * 11 / sum(1 for x in xv if x)
                out[side] = np.log(XI / E)
        if mins: HIST.setdefault(tid, []).append((r.dt, mins))
    if len(out) == 2: SURP[r.mid] = (out['h'], out['a'])
X['sh'] = X.mid.map(lambda m: SURP.get(m, (np.nan, np.nan))[0]); X['sa'] = X.mid.map(lambda m: SURP.get(m, (np.nan, np.nan))[1])
X = X[X.sh.notna()].copy()
X['surp'] = X.sh - X.sa
print(f"εκπληξη vs συνηθισμενη 11αδα (ανα ομαδα): μεσο {pd.concat([X.sh, X.sa]).mean():+.3f} · p10 {pd.concat([X.sh, X.sa]).quantile(.1):+.3f} · "
      f"ομαδες-ματς με 11αδα ≥30% ελαφρυτερη (ln ≤ −0.36): {int((pd.concat([X.sh, X.sa]) <= -0.36).sum())}")
# μοντελο: υπεροχη = OLS γκολ ~ Elo + ln(αξια) ανα εκδοχη, LOSO (ιδιο με intl_xi60_test)
SEAS = sorted(X.season.unique())
for w in (1.0, 0.0):
    L = f'L{w}'; X[f'm{w}'] = np.nan
    for s_ in SEAS:
        tr = X[X.season != s_]; te = X.season == s_
        b = np.linalg.lstsq(np.column_stack([tr['diff'], tr[L]]), tr.gd.values, rcond=None)[0]
        X.loc[te, f'm{w}'] = X.loc[te, 'diff'] * b[0] + X.loc[te, L] * b[1]
X = X.rename(columns={'m1.0': 'm1', 'm0.0': 'm0'})

recs = []
for r in X.itertuples():
    for bk in ('Crown', 'SBOBET'):
        ah = ROWS.get((r.mid, bk))
        if not ah:
            continue
        pre = [z for z in ah if z[0] >= PRE_MIN]
        if not pre or pre[-1][0] > 24 * 60:
            continue
        p = pre[-1]; c = ah[-1]
        if c[0] > 30:          # το «κλεισιμο» πρεπει να ειναι κοντα στη σεντρα
            continue
        s_pre, s_cl = sup(p[1], p[2], p[3]), sup(c[1], c[2], c[3])
        # ποτε εγινε η μιση κινηση (αν κινηθηκε ≥0.10)
        half = None
        if abs(s_cl - s_pre) >= 0.10:
            for z in ah:
                if z[0] < PRE_MIN and abs(sup(z[1], z[2], z[3]) - s_pre) >= 0.5 * abs(s_cl - s_pre):
                    half = z[0]; break
        recs.append(dict(mid=r.mid, season=r.season, book=bk, gd=r.gd, surp=r.surp, rot_h=r.rot_h, rot_a=r.rot_a,
                         m1=r.m1, m0=r.m0,
                         s_pre=s_pre, s_cl=s_cl, move=s_cl - s_pre, half=half, pre=p, cl=c))
R = pd.DataFrame(recs)
print(f'ματς×βιβλιο με τιμη «ΠΡΙΝ» (≥{PRE_MIN}′) και κλεισιμο: {len(R)} (ματς {R.mid.nunique()}) · Crown {int((R.book=="Crown").sum())} / SBOBET {int((R.book=="SBOBET").sum())}')
print(f'εκπληξη 11αδας: sd {R.surp.std():.3f} · |εκπληξη|≥0.2: {int((R.surp.abs()>=.2).sum())} · ≥0.3: {int((R.surp.abs()>=.3).sum())} · ≥0.5: {int((R.surp.abs()>=.5).sum())}')

print('\nΑ. ΚΙΝΗΣΗ ΓΡΑΜΜΗΣ «ΠΡΙΝ» → ΚΛΕΙΣΙΜΟ (υπεροχη γηπεδουχου σε γκολ)')
for bk in ('Crown', 'SBOBET'):
    d = R[R.book == bk]; A = np.column_stack([np.ones(len(d)), d.surp]); b, *_ = np.linalg.lstsq(A, d.move, rcond=None)
    e = d.move - A @ b; se = np.sqrt(np.sum(e**2) / (len(d) - 2) / np.sum((d.surp - d.surp.mean())**2))
    print(f'  {bk:7s}: κινηση = {b[1]:+.3f} × εκπληξη (t {b[1]/se:+.1f}) · μεση |κινηση| {d.move.abs().mean():.3f}')
print('  ανα μεγεθος εκπληξης (κινηση ΚΟΝΤΡΑ στην ομαδα με την ελαφρια 11αδα, ΜΟ βιβλιων):')
for lo, hi in ((0, .1), (.1, .2), (.2, .3), (.3, .5), (.5, 9)):
    m = (R.surp.abs() >= lo) & (R.surp.abs() < hi); d = R[m]
    if len(d):
        mv = np.sign(d.surp) * d.move
        print(f'    |εκπληξη| {lo:.1f}-{hi if hi < 9 else "∞"}: n {len(d):4d} · κινηση {mv.mean():+.3f} γκολ (±{mv.std()/np.sqrt(len(d)):.3f})')
H = R[(R.surp.abs() >= .3) & R.half.notna()]
if len(H):
    print(f'  ΠΟΤΕ (|εκπληξη|≥0.3 και κινηση ≥0.10, n={len(H)}): η μιση κινηση εγινε — διαμεσος {H.half.median():.0f}′ πριν τη σεντρα · '
          f'≥60′ πριν: {100*(H.half>=60).mean():.0f}% · 45-60′: {100*((H.half>=45)&(H.half<60)).mean():.0f}% · 30-45′: {100*((H.half>=30)&(H.half<45)).mean():.0f}% · <30′: {100*(H.half<30).mean():.0f}%')

def bet_eval(sel, label):
    out = []
    for r, side in sel:
        L, oh, oa = r.pre[1], r.pre[2], r.pre[3]
        ud, odds = (L, oh) if side == 1 else (-L, oa)
        fc = fair_at(r.s_cl, side, ud)
        out.append(dict(book=r.book, season=r.season, clv=odds / fc - 1 if fc else np.nan, pnl=picks.settle(r.gd, side, ud, odds)))
    o = pd.DataFrame(out)
    if not len(o):
        print(f'  {label}: —'); return
    s = []
    for bk in ('Crown', 'SBOBET'):
        q = o[o.book == bk]
        if len(q): s.append(f"{bk} n{len(q)} CLV {q.clv.mean()*100:+.1f}% ROI {q.pnl.mean()*100:+.1f}% (±{q.pnl.std()/np.sqrt(len(q))*100:.1f})")
    pos = sum(o.groupby('season').pnl.mean() > 0); ns = o.season.nunique()
    print(f'  {label}: ' + ' · '.join(s) + f' · σεζον θετικες {pos}/{ns}')

print('\nΒ. ΠΟΝΤΑΡΙΣΜΑ ΣΤΗΝ ΤΙΜΗ «ΠΡΙΝ» κοντρα στην ομαδα με την ελαφρια 11αδα (handicap της γραμμης εκεινης της στιγμης)')
for thr in (.2, .3, .5):
    sel = [(r, 1 if r.surp > 0 else -1) for r in R.itertuples() if abs(r.surp) >= thr]
    bet_eval(sel, f'|εκπληξη|≥{thr}')

print('\nΓ. ΜΟΝΤΕΛΟ στην τιμη «ΠΡΙΝ» (κανονες live) — εκδοχη 23 (w=1) vs 11αδα (w=0)')
def model_picks(col):
    sel = []
    for r in R.itertuples():
        L, oh, oa = r.pre[1], r.pre[2], r.pre[3]; d = dist_s(getattr(r, col))
        for side, ud, odds in ((1, L, oh), (-1, -L, oa)):
            if abs(ud) >= .5 and 1.70 <= odds <= 2.10 and ip.ah_ev(d, side, ud, odds, picks.MARGIN) >= .10:
                sel.append((r, side)); break
    return sel
P1, P0 = model_picks('m1'), model_picks('m0')
k1 = {(r.mid, r.book, s) for r, s in P1}; k0 = {(r.mid, r.book, s) for r, s in P0}
bet_eval(P1, 'εκδοχη 23 (σημερα)')
bet_eval(P0, 'εκδοχη 11αδας    ')
bet_eval([(r, s) for r, s in P0 if (r.mid, r.book, s) not in k1], 'ΝΕΑ picks μονο με 11αδα')
bet_eval([(r, s) for r, s in P1 if (r.mid, r.book, s) not in k0], 'picks που ΧΑΝΟΝΤΑΙ με 11αδα')
