# -*- coding: utf-8 -*-
"""dom_bk_preseason_test.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ «ΑΠΟ ΤΗΝ ΑΡΧΗ», βημα 4: ΦΙΛΙΚΑ & SUPER CUP ΠΡΙΝ ΤΗ ΣΕΖΟΝ (5/10/2026, Στελιος «συνεχισε»).
Σημερα: τιποτα (στην Ευρωλιγκα/EuroCup μπηκε κ .5 μετα απο δικο τους τεστ — εδω ΞΑΝΑ απο την αρχη).
Δεδομενα: fs_bk_preseason.json (Flashscore φιλικα + Super Cups) · κοινη κλιμακα περσινης σεζον (ridge σε ΟΛΑ τα ματς fs_bk_games, ιδια με el_preseason_test).
ΑΠΟΔΟΣΗ ΠΡΟΕΤΟΙΜΑΣΙΑΣ ομαδας: ματς 1 Αυγ … 1ο εγχωριο ματς της, αντιπαλος με περσινο rating: r = Σ[διαφορα − (R_ομ − R_αντ)] / (n + 4) (ταβανι ±20).
Μετατοπιση αφετηριας κ·r (π./ματς → ανα 100 κατοχες: ×100/72), κ ∈ {0 (σημερα), .25, .5, 1}.
Βαση: Ισπανια = σημερινη + ποινη νεοφερμενων −8 · Ιταλια = (περσι 1.0, λ 12, HL 120, χωρις τυχη).
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση), ανα πρωταθλημα: LOSO 2021-26 με RMSE ΑΓΩΝ 1-10 (εκει στοχευει ο μηχανισμος, οπως στην EL) → ΑΛΛΑΓΗ αν
  καλυτερο απο κ=0 σε ≥4/5 σεζον ΚΑΙ το RMSE ολων των ματς να μη χειροτερευει. Αναφορα: Κ2 · ROI.
Εξοδος: dom_bk_preseason_test_out.txt"""
import sys, json, math, io, contextlib
import pandas as pd
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
ARGS = ['ACB', 'LBA']
src = open('dom_bk_engine_test.py', encoding='utf-8').read()
head = src.split("LIVE = (.7, 8, 9999, .5, False)")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
mk = src[src.index("# ---- αγορα (για αναφορα) ----"):src.index("for lg in ARGS:\n    P(''); P(f'############")]
NS = {'__name__': 'x'}
sys.argv = [sys.argv[0]] + ARGS
if True:
    exec(head, NS); exec(mk, NS)
G, EFF, YRS, NAME, fit, act, rm, EV, P, out, market_report, MK = (NS[k] for k in ('G', 'EFF', 'YRS', 'NAME', 'fit', 'act', 'rm', 'EV', 'P', 'out', 'market_report', 'MK'))
out.clear()
BASE = {'ACB': (.7, 8, 9999, .5, False), 'LBA': (1.0, 12, 120, None, False)}
def run(lg, carry, lam, HL, w, team_home, delta, kp=0.0):
    EH, EA, PC = EFF[w]
    idx_all = np.where(G.lg.values == lg)[0]; pred = np.full(len(G), np.nan); gn = np.zeros(len(G), int); new = np.zeros(len(G), bool)
    prior, h0, mu0 = {}, 4.0, float(np.mean(np.r_[EH[idx_all], EA[idx_all]])); fin = {}
    for y in YRS:
        sidx = idx_all[G.y.values[idx_all] == y]
        if not len(sidx): continue
        teams = sorted(set(G.hid.values[sidx]) | set(G.aid.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        hi = np.array([ix[t] for t in G.hid.values[sidx]]); ai = np.array([ix[t] for t in G.aid.values[sidx]])
        isnew = {t: (y > YRS[0] and t not in prior) for t in teams}
        o0 = np.array([delta / 2 if isnew[t] else carry * prior.get(t, (0, 0))[0] for t in teams])
        d0 = np.array([-delta / 2 if isnew[t] else carry * prior.get(t, (0, 0))[1] for t in teams])
        sh = np.array([kp * PRE.get((y, t), 0.0) * 100 / 72 / 2 for t in teams]); o0 = o0 + sh; d0 = d0 - sh
        dn = G.d.values[sidx]; eh, ea, pc = EH[sidx], EA[sidx], PC[sidx]
        cnt = {}
        for j, i in enumerate(sidx):
            a_, b_ = G.hid.values[i], G.aid.values[i]; cnt[a_] = cnt.get(a_, 0) + 1; cnt[b_] = cnt.get(b_, 0) + 1; gn[i] = max(cnt[a_], cnt[b_])
            new[i] = isnew[a_] or isnew[b_]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                ww = 0.5 ** ((d - dn[past]) / HL)
                mu, h, O, D, Hh = fit(hi[past], ai[past], eh[past], ea[past], ww, n, o0, d0, h0, mu0, lam, team_home); pace = float(np.mean(pc[past][-200:]))
            else:
                mu, h, O, D, Hh, pace = mu0, h0, o0, d0, np.zeros(n), float(np.mean(PC[idx_all]))
            for j in cur:
                pred[sidx[j]] = pace * ((h + Hh[hi[j]] + O[hi[j]] + D[ai[j]]) - (O[ai[j]] + D[hi[j]])) / 100
        mu, h, O, D, Hh = fit(hi, ai, eh, ea, 0.5 ** ((dn.max() - dn) / HL), n, o0, d0, h0, mu0, lam, team_home)
        prior = {t: (O[i], D[i]) for t, i in ix.items()}; h0, mu0 = h, mu
        pm = float(np.mean(pc))
        for t, i in ix.items(): fin[(y, t)] = ((O[i] - D[i]) * pm / 100, isnew[t])
    return pred, gn, new, fin
# ---- αποδοση προετοιμασιας ----
import datetime as dt
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
def common(y):
    rows = []
    for key, L in FG.items():
        c, yy = key.split('_')
        if int(yy) != y: continue
        for e in L:
            try: m = float(np.clip(int(e['hs']) - int(e['as_']), -20, 20))
            except Exception: continue
            if e.get('hid') and e.get('aid'): rows.append((e['hid'], e['aid'], m))
    teams = sorted({r[0] for r in rows} | {r[1] for r in rows}); ix = {t: i for i, t in enumerate(teams)}; n = len(teams); k = len(rows)
    A = np.zeros((k + n, n + 1)); b = np.zeros(k + n); r_ = np.arange(k)
    A[r_, [ix[r[0]] for r in rows]] = 1; A[r_, [ix[r[1]] for r in rows]] = -1; A[r_, n] = 1; b[:k] = [r[2] for r in rows]
    A[k + np.arange(n), np.arange(n)] = math.sqrt(2)
    x = np.linalg.lstsq(A, b, rcond=None)[0]
    return {t: x[ix[t]] for t in teams}
PS = json.load(open('fs_bk_preseason.json', encoding='utf-8'))
PRE, NPRE = {}, {}
for y in EV:
    C = common(y - 1); lo = dt.date(y, 8, 1)
    for lg in ARGS:
        m = (G.lg.values == lg) & (G.y.values == y)
        first = {}
        for t_, a_, b_ in zip(G.t.values[m], G.hid.values[m], G.aid.values[m]):
            for tt in (a_, b_): first.setdefault(tt, pd.Timestamp(t_).date())
        acc = {}
        for key, L in PS.items():
            for e in L:
                dd = dt.datetime.utcfromtimestamp(e['ts']).date() if e.get('ts') else None
                if not dd: continue
                try: mg = float(np.clip(int(e['hs']) - int(e['as_']), -20, 20))
                except Exception: continue
                for me, op, sg in ((e.get('hid'), e.get('aid'), 1), (e.get('aid'), e.get('hid'), -1)):
                    if me not in first or not (lo <= dd < first[me]) or me not in C or op not in C: continue
                    acc.setdefault(me, []).append(sg * mg - (C[me] - C[op]))
        for t_, L in acc.items():
            PRE[(y, t_)] = sum(L) / (len(L) + 4.0); NPRE[(y, t_)] = len(L)
BASE = {'ACB': (.7, 8, 9999, .5, False, -8), 'LBA': (1.0, 12, 120, None, False, 0)}
KP = (0, .25, .5, 1.0)
for lg in ARGS:
    P(''); P(f'############ {NAME[lg]} · βαση {BASE[lg]} ############')
    tms = {(y, t) for y in EV for t in set(G.hid.values[(G.lg.values == lg) & (G.y.values == y)])}
    have = [k for k in tms if k in PRE]
    P(f'  ομαδες-σεζον με ματς προετοιμασιας: {len(have)}/{len(tms)} · μεσος αριθμος ματς {np.mean([NPRE[k] for k in have]):.1f} · '
      + ' '.join(f'{y}: {sum(1 for k in have if k[0] == y)}' for y in EV) + f' · sd r {np.std([PRE[k] for k in have]):.2f}')
    PR = {kp: run(lg, *BASE[lg], kp) for kp in KP}
    _, gn, new, fin = PR[0]
    rmm = lambda v, ys, msk=None: rm(v, lg, ys, msk)
    P('  IN-SAMPLE RMSE ανα κ (αγων 1-10 · ολα):')
    for kp in KP:
        P(f'    κ {kp:4.2f}: {rmm(PR[kp][0], EV, gn <= 10):.3f} · {rmm(PR[kp][0], EV):.3f}')
    held = np.full(len(G), np.nan); ch = []
    for Y in EV:
        tr = [x for x in EV if x != Y]; kp = min(KP, key=lambda kp: rmm(PR[kp][0], tr, gn <= 10)); ch.append(kp)
        mm = (G.lg.values == lg) & (G.y.values == Y); held[mm] = PR[kp][0][mm]
    base = PR[0][0]
    for lab, msk in (('αγων 1-10', gn <= 10), ('ΟΛΑ', None)):
        d = [rmm(held, [Y], msk) - rmm(base, [Y], msk) for Y in EV]
        P(f'  LOSO {lab:10s} κ {ch} · {rmm(base, EV, msk):.3f} → {rmm(held, EV, msk):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d)
          + f' → {sum(x < 0 for x in d)}/5')
    d10 = [rmm(held, [Y], gn <= 10) - rmm(base, [Y], gn <= 10) for Y in EV]
    ok = sum(x < 0 for x in d10) >= 4 and rmm(held, EV) <= rmm(base, EV)
    P(f'  ΚΡΙΣΗ: {"ΑΛΛΑΓΗ" if ok else "✗"}')
    market_report(base, lg, 'κ 0 (σημερα)')
    market_report(held, lg, 'LOSO κ')
open('dom_bk_preseason_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
