"""core7_totals_anchor_md1_test.py — 12/10/2026 (Στελιος: «ξανατρεξε το backtest απο την αρχη της χρονιας και ξεκινημα στοιχηματων απο εκει που βρισκομαστε σημερα»).
ΑΓΚΥΡΑ ΣΥΝΟΛΩΝ ΣΤΟ ΑΝΟΙΓΜΑ (core7_goals_blend_timing GBT_ROBUST) — 3 ερωτησεις, CORE7 2223-2526, μηχανη live (xG 60/40, SoS 0.75):
  Α. ΟΠΩΣ ΗΤΑΝ: η αγκυρα μαθαινει απο την 7η αγωνιστικη, pick στην πρωτη τιμη (ανοιγμα).
  Β. ΑΠΟ ΤΗΝ 1η: η αγκυρα μαθαινει απο την 1η αγωνιστικη (κλεισιμο Crown, υπεροχη μοντελου), picks παλι μονο 7η+.
  Γ. ΤΙΜΙΟΣ ΧΡΟΝΟΣ: το ανοιγμα βγαινει συνηθως ~10 μερες πριν, δηλ. ΠΡΙΝ παιχτει η προηγουμενη αγωνιστικη — το Α/Β ομως χρησιμοποιουσαν
     ηδη το αποτελεσμα/κλεισιμο εκεινης (γνωση απο το μελλον). Εδω: τιμη που ισχυε τη στιγμη που η πληροφορια ηταν διαθεσιμη
     = 06:00 UTC μετα το προηγουμενο ματς ΚΑΙ των δυο ομαδων (+2ω). Αν η γραμμη δεν ειχε ανοιξει → η πρωτη τιμη μετα.
  Πανω απο ολα: μονο η 7η αγωνιστικη (εκει που ειναι σημερα EPL/SerieA/Ligue1).
ΚΑΝΟΝΕΣ picks ιδιοι: edge ≥10%, τιμη 1.70-2.10, Crown | Bet365 (Nowgoal), καλυτερη πλευρα. Ενημερωτικο — τιποτα live.
"""
import sys, json, glob, datetime
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
NL = chr(10)
W = pd.read_csv('core7_goals_gap_rows.csv', dtype={'season': str, 'mid': str})
P = pd.read_csv('core7_mech_preds_bl_0.6.csv', dtype={'mid': str, 'season': str})
P = P[P.season.isin(W.season.unique())].copy()
TG = dict(zip(W.mid, W.tg)); TMK = dict(zip(W.mid, W.T_mkt))
KO = {}
for f in glob.glob('data_*_*.json'):
    try: d = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    if not isinstance(d, dict): continue
    for k, v in d.items():
        try: KO[str(k)] = datetime.datetime.strptime(v['date'], '%a, %b %d, %Y, %H:%M UTC').replace(tzinfo=datetime.timezone.utc).timestamp()
        except Exception: pass
def pl(gs):
    try:
        p = [float(x) for x in str(gs).split('/')]; return sum(p) / len(p)
    except Exception: return None
SER = {}; mids = set(P.mid)
for f in glob.glob('nowgoal_odds/*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        try: r = json.loads(ln)
        except Exception: continue
        if r.get('cid') not in (3, 8) or not r.get('ou') or str(r['mid']) not in mids: continue
        rows = []
        for mt, ov, gl, un in r['ou']:
            L = pl(gl)
            try: oo, uu = float(ov) + 1, float(un) + 1
            except (TypeError, ValueError): continue
            if L is None or mt is None or oo <= 1 or uu <= 1: continue
            rows.append((mt, L, oo, uu))
        if rows: rows.sort(); SER[(str(r['mid']), 'Crown' if r['cid'] == 3 else 'Bet365')] = rows
IDX = np.add.outer(np.arange(13), np.arange(13)); KS = np.arange(25)
def tdist(h, a):
    M = picks.score_matrix_dom(max(h, .05), max(a, .05)); return np.bincount(IDX.ravel(), weights=np.asarray(M).ravel(), minlength=25)
def probs(d, L):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; po = pu = 0
    for x in parts: po += d[KS > x + .01].sum() / len(parts); pu += d[KS < x - .01].sum() / len(parts)
    return po, pu
def t_mkt(L, o, u, s):
    q = (1 / o) / (1 / o + 1 / u); lo, hi = 0.8, 7.0
    for _ in range(30):
        T = (lo + hi) / 2; po, pu = probs(tdist((T + s) / 2, (T - s) / 2), L)
        if po / max(po + pu, 1e-9) < q: lo = T
        else: hi = T
    return (lo + hi) / 2
def ou_eval(d, L, over, o, tg):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; e = s_ = 0
    for x in parts:
        pw = d[(KS > x + .01) if over else (KS < x - .01)].sum(); pp = d[np.abs(KS - x) < .01].sum()
        e += (pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)) / len(parts)
        m = (tg - x) if over else (x - tg); s_ += ((o - 1) if m > .01 else (0 if abs(m) < .01 else -1)) / len(parts)
    return e, s_
# ---- σειρα ματς, προηγουμενο ματς καθε ομαδας ----
P['ko'] = P.mid.map(KO)
P = P[P.ko.notna()].sort_values(['league', 'season', 'ko']).reset_index(drop=True)
prev_ko = {}; PREV = []
for r in P.itertuples():
    k = (r.league, r.season)
    PREV.append(max(prev_ko.get((k, r.home), -1), prev_ko.get((k, r.away), -1)))
    prev_ko[(k, r.home)] = r.ko; prev_ko[(k, r.away)] = r.ko
P['prev'] = PREV
# T_mkt (κλεισιμο Crown): για αγων. 7+ το ιδιο με το τεστ· για 1-6 λυνω με υπεροχη μοντελου
tm = []
for r in P.itertuples():
    if r.mid in TMK: tm.append(TMK[r.mid]); continue
    seq = SER.get((r.mid, 'Crown'))
    tm.append(t_mkt(seq[-1][1], seq[-1][2], seq[-1][3], r.xg_h - r.xg_a) if seq else np.nan)
P['T_mkt'] = tm
def anchored(start_md, lam=0.5):
    out = np.zeros(len(P)); off = {}; cur = None
    for i, r in enumerate(P.itertuples()):
        k = (r.league, r.season)
        if k != cur: off = {}; cur = k
        t = r.xg_h + r.xg_a + off.get(r.home, 0) + off.get(r.away, 0); out[i] = t
        if r.md >= start_md and r.T_mkt == r.T_mkt:
            e = r.T_mkt - t; off[r.home] = off.get(r.home, 0) + lam * e / 2; off[r.away] = off.get(r.away, 0) + lam * e / 2
    return out
def price_at(seq, mode, prev, ko):
    if mode == 'open': return seq[0]
    t_av = prev + 2 * 3600                                             # τελος προηγουμενου ματς
    d0 = datetime.datetime.fromtimestamp(t_av, datetime.timezone.utc)
    nxt = d0.replace(hour=6, minute=0, second=0)
    if nxt.timestamp() <= t_av: nxt += datetime.timedelta(days=1)    # επομενο πρωινο refresh
    t_av = nxt.timestamp()
    if t_av >= ko: return None
    before = [x for x in seq if x[0] <= t_av]
    return before[-1] if before else seq[0]
rows = []; prestale = []
for lab, smd, mode in (('Α. οπως ηταν (αγκυρα απο 7η, ανοιγμα)', 6, 'open'), ('Β. αγκυρα απο 1η, ανοιγμα', 0, 'open'),
                       ('Γ1. αγκυρα απο 7η, τιμιος χρονος', 6, 'fair'), ('Γ2. αγκυρα απο 1η, τιμιος χρονος', 0, 'fair')):
    T = anchored(smd)
    for i, r in enumerate(P.itertuples()):
        if r.md < 6 or r.mid not in TG: continue
        s = r.xg_h - r.xg_a; d = tdist((T[i] + s) / 2, (T[i] - s) / 2)
        for bk in ('Crown', 'Bet365'):
            seq = SER.get((r.mid, bk))
            if not seq: continue
            q = price_at(seq, mode, r.prev, r.ko)
            if q is None: continue
            t0, L, oo, uu = q
            if mode == 'open' and smd == 6: prestale.append((bk, r.md, t0 < r.prev + 2 * 3600, (r.ko - t0) / 3600))
            best = None
            for over, o in ((True, oo), (False, uu)):
                if not (1.70 <= o <= 2.10): continue
                e, pnl = ou_eval(d, L, over, o, int(TG[r.mid]))
                if e >= .10 and (best is None or e > best[0]): best = (e, pnl, 'OVER' if over else 'UNDER', over, L)
            if best:
                Lc = seq[-1][1]
                rows.append(dict(var=lab, book=bk, season=r.season, league=r.league, md=r.md, side=best[2], edge=best[0], pnl=best[1],
                                 clv=(1 if best[3] else -1) * (Lc - best[4]), hrs=(r.ko - t0) / 3600))
R = pd.DataFrame(rows)
def fm(x):
    if len(x) < 5: return f'n{len(x):4d}           —        '
    ps = x.groupby('season').pnl.mean(); return f'n{len(x):4d} {100 * x.pnl.mean():+6.1f}% {x.pnl.sum():+6.1f}μ {int((ps > 0).sum())}/4'
S = pd.DataFrame(prestale, columns=['book', 'md', 'stale', 'hrs'])
c = S[S.book == 'Crown']
print('ΠΟΤΕ ΒΓΑΙΝΕΙ ΤΟ ΑΝΟΙΓΜΑ (Crown, αγων. 7+): διαμεσος ' + f'{c.hrs.median():.0f}ω πριν τη σεντρα · ' +
      f'{100 * c.stale.mean():.0f}% των ματς: η γραμμη ανοιξε ΠΡΙΝ τελειωσει το προηγουμενο ματς των ομαδων')
print(NL + 'ΑΠΟΤΕΛΕΣΜΑΤΑ (edge ≥10%, 1.70-2.10) · Crown | Bet365 · n, απόδοση, μονάδες, θετικες σεζον · CLV γραμμης (γκολ, Crown)')
for v in R['var'].unique():
    x = R[R['var'] == v]; print(NL + v)
    for wl, m in (('μονο 7η', x.md == 6), ('7-14', x.md.between(6, 13)), ('15+', x.md >= 14), ('ολα 7+', x.md >= 6)):
        y = x[m]; cc = y[y.book == 'Crown']
        print(f'   {wl:8s} Crown {fm(cc)} | Bet365 {fm(y[y.book == "Bet365"])} · CLV {cc.clv.mean():+.3f} · ωρες πριν {cc.hrs.median():.0f}')
    y = x[x.md.between(6, 13) & (x.book == 'Crown')]
    print('   7-14 Crown ανα πλευρα: ' + ' · '.join(f'{sd} {fm(y[y.side == sd])}' for sd in ('OVER', 'UNDER')))
    y = x[(x.md >= 14) & (x.book == 'Crown')]
    print('   15+  Crown ανα πλευρα: ' + ' · '.join(f'{sd} {fm(y[y.side == sd])}' for sd in ('OVER', 'UNDER')))
    y = x[(x.md == 6) & (x.book == 'Crown')]
    print('   7η   Crown ανα πλευρα: ' + ' · '.join(f'{sd} {fm(y[y.side == sd])}' for sd in ('OVER', 'UNDER')) +
          f' · picks ανα λιγκα-σεζον στην 7η: {len(y) / max(y.groupby(["league", "season"]).ngroups, 1):.1f}')
R.to_csv('core7_totals_anchor_md1_rows.csv', index=False)
