# -*- coding: utf-8 -*-
"""el_domestic_league_test.py — ΔΙΟΡΘΩΣΗ ΔΥΝΑΜΙΚΟΤΗΤΑΣ ΑΝΑ ΛΙΓΚΑ στα φετινα εγχωρια (30/9/2026, αιτημα Στελιου).
Σημερα (live, απο τον 11ο αγωνα): shift = κ·Δ·100/72 με ΙΔΙΟ κ για ολες τις λιγκες (Δ = φετινη αλλαγη μεσα στο πρωταθλημα).
ΕΚΔΟΧΕΣ:
  (α) ιδιο βαρος (σημερα)
  (β) κανονικοποιηση: Δ × (σ_μεσο / σ_λιγκας), σ_λιγκας = διασπορα δυναμης ομαδων της λιγκας στο ΤΕΛΟΣ της περσινης σεζον
      (αδυναμη/ανισορροπη λιγκα με μεγαλες διαφορες → μικροτερο βαρος)
  (γ) μεταφραση ανα λιγκα: Δ × β_λιγκας/β_μεσο, β = ποσο μεταφραζεται 1 ποντος εγχωριας δυναμης σε δυναμη Ευρωλιγκας
      (κλιση: τελικο rating EL ~ τελικο εγχωριο rating των ομαδων EL, ανα λιγκα, μαζεμα 50% προς την κοινη κλιση, ΜΟΝΟ αλλες σεζον)
ΠΛΕΓΜΑ κ {.25, .5, .75, 1, 1.5} ανα εκδοχη, ταβανι 20. ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ: LOSO (κ απο τις αλλες σεζον, ελαχιστο RMSE αγων 11+)·
  (β)/(γ) ΠΕΡΝΑ αν το εκτος-δειγματος RMSE αγων 11+ ειναι καλυτερο απο το (α) σε ≥4/5 σεζον. Επισης b, ROI.
Εξοδος: el_domestic_league_test_out.txt"""
import sys, json, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
NS = {}
src = open('el_domestic_rating_test.py', encoding='utf-8').read().split("PRED = {}")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
# οπως στο live (el_domestic_live) και στο αρχικο τεστ: ΜΟΝΟ κανονικη περιοδος (το bk_domestic εχει πλεον και πλει-οφ)
src = src.replace("G_ = [g for g in DOM[k]['games'] if str(g[4])", "G_ = [g for g in DOM[k]['games'] if (g[-1] if len(g) > 6 else 1) == 1 and str(g[4])")
assert "(g[-1] if len(g) > 6 else 1) == 1 and str(g[4])" in src
exec(src, NS)
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
D, SE5, EM, GN, dnum, IDX, PRC, ACT, SE, RS = (NS[k] for k in ('D', 'SE5', 'EM', 'GN', 'dnum', 'IDX', 'PRC', 'ACT', 'SE', 'RS'))
fit_eff, fit_pace, LUCK, ENDS, cfg, S20, MAP, DOM, D0, tok = (NS[k] for k in ('fit_eff', 'fit_pace', 'LUCK', 'ENDS', 'cfg', 'S20', 'MAP', 'DOM', 'D0', 'tok'))
dom_shift = NS['dom_shift']
# ---- εγχωριο ΤΕΛΟΣ σεζον ανα λιγκα (ιδιο ridge, ταβανι 20) ----
def dom_end(cap=20):
    E = {}
    for L in sorted({k.split('_')[0] for k in DOM}):
        keys = sorted([k for k in DOM if k.startswith(L + '_')], key=lambda k: k.split('_')[1]); prev = {}
        for k in keys:
            G_ = [g for g in DOM[k]['games'] if (g[-1] if len(g) > 6 else 1) == 1 and str(g[4]).strip() not in ('', '-1', 'None') and str(g[5]).strip() not in ('', '-1', 'None')]
            if not G_: prev = {}; continue
            hid = [int(g[2]) for g in G_]; aid = [int(g[3]) for g in G_]; y = np.clip([float(g[4]) - float(g[5]) for g in G_], -cap, cap)
            teams = sorted(set(hid) | set(aid)); ix = {t: i for i, t in enumerate(teams)}; n = len(teams); m = len(y)
            A = np.zeros((m + n, n + 1)); b = np.zeros(m + n); r = np.arange(m)
            A[r, [ix[t] for t in hid]] = 1; A[r, [ix[t] for t in aid]] = -1; A[r, n] = 1; b[:m] = y
            A[m + np.arange(n), np.arange(n)] = math.sqrt(8); b[m:] = math.sqrt(8) * np.array([0.7 * prev.get(t, 0) for t in teams])
            R = np.linalg.lstsq(A, b, rcond=None)[0][:n]
            E[(L, 'E20' + k.split('_')[1][:2])] = {t: float(R[i]) for t, i in ix.items()}; prev = {t: float(R[i]) for t, i in ix.items()}
    return E
DEND = dom_end()
# σ λιγκας (περσινο τελος) — γνωστο πριν τη σεζον
SIG = {}
for (L, es), d in DEND.items():
    y = int(es[1:]); SIG[(L, f'E{y + 1}')] = float(np.std(list(d.values())))
# β ανα λιγκα: τελικο EL net ~ τελικο εγχωριο R (ομαδες EL), ανα σεζον
def map_team(es, code):
    sub = D[D.season == es]
    nm = next((r.hname for r in sub.itertuples() if r.home == code), None)
    if nm is None: return None
    te = tok(nm); best = (0, None)
    for (L, e2), d in DEND.items():
        if e2 != es: continue
        for k in DOM:
            if not k.startswith(L + '_') or ('E20' + k.split('_')[1][:2]) != es: continue
            for t, tn in DOM[k]['teams'].items():
                tt = tok(tn)
                if tt and te:
                    sc = len(te & tt) / min(len(te), len(tt)) + 0.01 * len(te & tt)
                    if sc > best[0] and int(t) in d: best = (sc, (L, int(t)))
    return best[1] if best[0] >= 0.5 else None
PTS = []                                                      # (σεζον EL, λιγκα, R εγχωριο, EL net)
seasons = sorted(D.season.unique())
for es in seasons[:-1]:
    nxt = seasons[seasons.index(es) + 1]; pr = ENDS[nxt]['prior']
    for code in sorted(set(D[D.season == es].home)):
        k = map_team(es, code)
        if k and code in pr and (k[0], es) in DEND:
            PTS.append((es, k[0], DEND[(k[0], es)][k[1]], pr[code][0] - pr[code][1]))
PT = pd.DataFrame(PTS, columns=['es', 'L', 'R', 'net'])
P(f'σημεια για β (ομαδα EL × σεζον): {len(PT)} · ανα λιγκα ' + ' '.join(f'{L}:{n}' for L, n in PT.L.value_counts().items()))
def betas(excl):
    d = PT[PT.es != excl]
    # ιδιο intercept ανα λιγκα, κλιση: κοινη + αποκλιση λιγκας μαζεμενη 50%
    b_all = np.polyfit(d.R - d.groupby('L').R.transform('mean'), d.net - d.groupby('L').net.transform('mean'), 1)[0]
    out_ = {}
    for L, g in d.groupby('L'):
        bl = np.polyfit(g.R - g.R.mean(), g.net - g.net.mean(), 1)[0] if len(g) >= 4 and g.R.std() > 0 else b_all
        out_[L] = 0.5 * bl + 0.5 * b_all
    return out_, b_all
P('β ανα λιγκα (ολες οι σεζον, για αναφορα): ' + ' · '.join(f'{L} {v:.2f}' for L, v in sorted(betas('none')[0].items())) + f' · κοινη {betas("none")[1]:.2f}')
sig_mean = float(np.mean(list(SIG.values())))
P('σ λιγκας (μεσος 2021-25): ' + ' · '.join(f'{L} {np.mean([v for (l, e), v in SIG.items() if l == L and e in SE5]):.1f}' for L in sorted({l for l, e in SIG})))
def mult(variant, Y, L):
    if variant == 'a' or L is None: return 1.0
    if variant == 'b': return sig_mean / SIG.get((L, Y), sig_mean) if SIG.get((L, Y)) else 1.0
    bl, ba = betas(Y); return bl.get(L, ba) / ba if ba else 1.0
def run(kappa, variant):
    EH, EA = LUCK[cfg['lw']]; v = np.full(len(D), np.nan)
    for Y in SE5:
        st = ENDS[Y]; prior = st['prior']
        sidx = np.where(D.season.values == Y)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        e = np.array([EM[Y].get(t, 0.0) for t in teams]) * cfg['we']
        o0b = np.array([cfg['wt'] * prior.get(t, (0, 0, 0))[0] for t in teams]) + e / 2
        d0b = np.array([cfg['wt'] * prior.get(t, (0, 0, 0))[1] for t in teams]) - e / 2
        p0 = np.array([0.7 * prior.get(t, (0, 0, 0))[2] for t in teams])
        ML = np.array([mult(variant, Y, MAP.get((Y, t), (None, None, None))[2]) for t in teams])
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        hb = np.where(D.ff.values[sidx] | D.relocated.values[sidx], 0.0, cfg['h'] / 2); dn = dnum[sidx]
        pred = np.full(len(sidx), np.nan)
        for d in np.unique(dn):
            sh = np.array([kappa * dom_shift(S20, Y, t, d) * 100 / 72 for t in teams]) * ML
            o0 = o0b + sh / 2; d0 = d0b - sh / 2
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                w = 0.5 ** ((d - dn[past]) / cfg['HL'])
                mu, O, Dd = fit_eff(hi[past], ai[past], EH[sidx][past], EA[sidx][past], hb[past], w, n, o0, d0, cfg['lam'], st['mu0'])
                pm, Pc = fit_pace(hi[past], ai[past], D.pace.values[sidx][past], w, n, p0, cfg['lam'], st['pm0'])
            else:
                mu, O, Dd, pm, Pc = st['mu0'], o0, d0, st['pm0'], p0
            hh, aa, hbb = hi[cur], ai[cur], hb[cur]
            pred[cur] = (pm + Pc[hh] + Pc[aa]) * ((mu + O[hh] + Dd[aa] + hbb) - (mu + O[aa] + Dd[hh] - hbb)) / 100
        v[sidx] = pred
    return np.where(GN >= 7, v * cfg['sf'], v)
PRED = {}
for var in ('a', 'b', 'c'):
    for kp in (0.25, 0.5, 0.75, 1.0, 1.5):
        PRED[(var, kp)] = run(kp, var); print(f'  {var} κ {kp} ετοιμο', flush=True)
ACTD = (D.hs - D.as_).values.astype(float); RSM = D.phase.values == 'RS'; SEASD = D.season.values
M11 = RSM & (GN > 10)
def rm(v, ss, msk): m = msk & np.isin(SEASD, ss); return float(np.sqrt(np.mean((ACTD - v)[m] ** 2)))
P('')
P('=== IN-SAMPLE RMSE αγων 11+ (5 σεζον) ===')
for var in ('a', 'b', 'c'):
    P(f'  ({var}) ' + ' · '.join(f'κ {kp}: {rm(PRED[(var, kp)], SE5, M11):.3f}' for kp in (0.25, 0.5, 0.75, 1.0, 1.5)))
held = {}
for var in ('a', 'b', 'c'):
    h = np.full(len(D), np.nan); ch = []
    for Y in SE5:
        tr = [s for s in SE5 if s != Y]
        k = min([k for k in PRED if k[0] == var], key=lambda k: rm(PRED[k], tr, M11)); ch.append(k[1])
        h[SEASD == Y] = PRED[k][SEASD == Y]
    held[var] = (h, ch)
jj = np.array([j for j in range(len(IDX)) if RS[j] and not np.isnan(PRC[j, 0]) and SE[j] in SE5])
L_, OH, OA = PRC[jj, 0], PRC[jj, 1], PRC[jj, 2]; AC = ACT[jj]; SJ = SE[jj]; GJ = GN[IDX[jj]]; MK = -L_
Phi = np.vectorize(lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2))))
isint = np.abs(L_ - np.round(L_)) < 1e-9
def roi(v, msk, thr=0.08):
    m = v[IDX][jj]
    pw = np.where(isint, Phi((m + L_ - 0.5) / 11.5), Phi((m + L_) / 11.5)); pl = np.where(isint, Phi((-m - L_ - 0.5) / 11.5), 1 - pw); pp = 1 - pw - pl
    eh, ea = pw * OH + pp - 1, pl * OA + pp - 1
    side = np.where(eh >= ea, 1, -1); e = np.maximum(eh, ea); od = np.where(side == 1, OH, OA)
    vv = (AC + L_) * side; pr = np.where(vv > 0, od - 1, np.where(vv == 0, 0.0, -1.0)); sel = (e >= thr) & msk
    pos_ = sum(1 for s in SE5 if (sel & (SJ == s)).any() and pr[sel & (SJ == s)].mean() > 0)
    return f'{pr[sel].mean()*100:+.1f}% ({sel.sum()}) {pos_}/5'
P('')
P('=== LOSO (κ απο τις αλλες σεζον) — αγων 11+ ===')
base = held['a'][0]
for var, lab in (('a', '(α) ιδιο βαρος (σημερα)'), ('b', '(β) κανονικοποιηση σ λιγκας'), ('c', '(γ) μεταφραση β ανα λιγκα')):
    h, ch = held[var]
    diffs = [rm(h, [Y], M11) - rm(base, [Y], M11) for Y in SE5]; w_ = sum(d < 0 for d in diffs)
    b = np.polyfit((h[IDX][jj] - MK)[GJ > 10], (AC - MK)[GJ > 10], 1)[0]
    P(f'  {lab:32s} κ {ch} · RMSE 11+ {rm(h, SE5, M11):.3f} · vs (α) ' + ' '.join(f'{d:+.3f}' for d in diffs)
      + (f' → καλυτερο {w_}/5 → {"ΠΕΡΝΑ" if w_ >= 4 else "✗"}' if var != 'a' else '') + f' · b {b:+.3f} · ROI ≥8% {roi(h, GJ > 10)} · ≥5% {roi(h, GJ > 10, 0.05)}')
open('el_domestic_league_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
