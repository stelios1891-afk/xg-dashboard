# -*- coding: utf-8 -*-
"""el_expert_accuracy.py — ΤΕΣΤ ΑΚΡΙΒΕΙΑΣ (οχι ROI) για την καταταξη ειδικων (25/9/2026, Στελιος: «οι ειδικοι δεν ειναι για λεφτα
αλλα για να προβλεπουμε σωστοτερα — οι μεγαλες διαφορες ισως ειναι ελλειψη πληροφοριας, οχι δυναμη του μοντελου»).

Ιδια μεθοδος με el_expert_prior_test.py (BasketNews pre-season 2021-2025 → rating ποσοστημοριου → α·ειδικοι + (1−α)·v1 στην αρχη).
ΔΕΙΓΜΑ: ΟΛΑ τα ματς κανονικης περιοδου 2021-2025 (οχι μονο με αποδοσεις).
ΜΕΤΡΑ: λαθος διαφορας (RMSE, MAE) · πιθανοτητα νικης (log-loss, Brier· p = Φ(διαφορα/11.5)) · σωστος νικητης %.
ΙΣΟΡΡΟΠΙΑ: «λαθος ανα ομαδα» = (πραγματικη − προβλεπομενη διαφορα απο τη μερια της ομαδας) στις αγων 1-10, πανω στο
  (rating ειδικων − αρχικο rating v1). Κλιση > 0 = οι ομαδες που οι ειδικοι βλεπουν καλυτερες ΟΝΤΩΣ ξεπερνουν το v1 (= ελλειψη πληροφοριας).
ΕΠΙΛΟΓΗ α: LOSO — ελαχιστο RMSE αγων 1-10 στις αλλες 4 σεζον.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (ΜΙΑ εκτελεση): οι ειδικοι «προβλεπουν καλυτερα» αν στα held-out, αγων 1-10:
  (α) RMSE χαμηλοτερο σε ≥4/5 σεζον, (β) ζευγαρωτη βελτιωση τετραγωνικου λαθους t ≥ 2, (γ) log-loss χαμηλοτερο συνολικα.
Εξοδος: el_expert_accuracy_out.txt"""
import sys, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('el_expert_prior_test.py', encoding='utf-8').read().split("rs_all = D[D.phase == 'RS']")[0]
src = src.replace("sys.stdout.reconfigure(encoding='utf-8')", '').replace("P('θεση ειδικων", "pass  # P('θεση ειδικων")
exec(src)
out.clear()

ALPHAS = [0.0, 0.25, 0.5, 0.75, 1.0]
FULL = {a: (base if a == 0 else run_x(a, mapping)[0])[:, 0] for a in ALPHAS}
rs_all = D[D.phase == 'RS'].sort_values('date'); cnt = {}; RNDD = np.full(len(D), 99)
for i, r in rs_all.iterrows():
    for t in (r.home, r.away): cnt[(r.season, t)] = cnt.get((r.season, t), 0) + 1
    RNDD[D.index.get_loc(i)] = max(cnt[(r.season, r.home)], cnt[(r.season, r.away)])
MASK = (D.phase.values == 'RS') & D.season.isin(ES).values
ACTD = (D.hs - D.as_).values.astype(float); SED = D.season.values
Phi = np.vectorize(lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2))))
def metrics(pred, m):
    e = ACTD[m] - pred[m]; p = np.clip(Phi(pred[m] / 11.5), 1e-4, 1 - 1e-4); y = (ACTD[m] > 0).astype(float)
    return dict(n=m.sum(), rmse=np.sqrt(np.mean(e ** 2)), mae=np.mean(np.abs(e)), ll=-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)),
                brier=np.mean((p - y) ** 2), acc=np.mean((pred[m] > 0) == (ACTD[m] > 0)))
early = MASK & (RNDD <= 10)

P('=== ΑΚΡΙΒΕΙΑ ΑΝΑ α (ολες οι 5 σεζον, κανονικη περιοδος) ===')
for lab, m in (('αγων 1-10', early), ('αγων 11-20', MASK & (RNDD > 10) & (RNDD <= 20)), ('αγων 21+', MASK & (RNDD > 20))):
    P(f'  {lab} ({m.sum()} ματς):')
    for a in ALPHAS:
        r = metrics(FULL[a], m)
        P(f'    α {a:<4}: RMSE {r["rmse"]:.2f} · MAE {r["mae"]:.2f} · log-loss {r["ll"]:.4f} · Brier {r["brier"]:.4f} · σωστος νικητης {r["acc"]*100:.1f}%')
# αγορα (οσα εχουν closing) για συγκριση, αγων 1-10
jm = [j for j in range(len(IDX)) if RS[j] and SE[j] in ES and RNDD[IDX[j]] <= 10]
em = np.array([ACT[j] - MM[j] for j in jm]); ev1 = np.array([ACT[j] - FULL[0.0][IDX[j]] for j in jm])
ee = {a: np.array([ACT[j] - FULL[a][IDX[j]] for j in jm]) for a in ALPHAS}
P(f'  αναφορα — ματς αγων 1-10 με closing ({len(jm)}): RMSE αγορα {np.sqrt(np.mean(em**2)):.2f} · v1 {np.sqrt(np.mean(ev1**2)):.2f} · ' +
  ' · '.join(f'α{a} {np.sqrt(np.mean(ee[a]**2)):.2f}' for a in ALPHAS[1:]))

P('')
P('=== LOSO (α με ελαχιστο RMSE αγων 1-10 στις αλλες 4) — held-out, αγων 1-10 ===')
wins = 0; d_all = []; ll_x = []; ll_v = []
for s in ES:
    tr = early & np.isin(SED, [t for t in ES if t != s]); te = early & (SED == s)
    a = min(ALPHAS[1:], key=lambda a: metrics(FULL[a], tr)['rmse'])
    rx, rv = metrics(FULL[a], te), metrics(FULL[0.0], te)
    wins += rx['rmse'] < rv['rmse']
    d_all.append((ACTD[te] - FULL[0.0][te]) ** 2 - (ACTD[te] - FULL[a][te]) ** 2)
    ll_x.append(rx['ll'] * rx['n']); ll_v.append(rv['ll'] * rv['n'])
    P(f'  {s[-4:]}: α {a} · RMSE {rx["rmse"]:.2f} vs v1 {rv["rmse"]:.2f} · log-loss {rx["ll"]:.4f} vs {rv["ll"]:.4f} · νικητης {rx["acc"]*100:.1f}% vs {rv["acc"]*100:.1f}%')
d = np.concatenate(d_all); t = d.mean() / (d.std(ddof=1) / math.sqrt(len(d)))
llx, llv = sum(ll_x) / early.sum(), sum(ll_v) / early.sum()
P(f'  ΣΥΝΟΛΟ: RMSE καλυτερο σε {wins}/5 · ζευγαρωτη βελτιωση τετρ. λαθους {d.mean():+.2f} (t {t:+.2f}) · log-loss {llx:.4f} vs {llv:.4f}')
ok = wins >= 4 and t >= 2 and llx < llv
P(f'  → (α) {"✓" if wins >= 4 else "✗"}  (β) {"✓" if t >= 2 else "✗"}  (γ) {"✓" if llx < llv else "✗"}  → {"ΟΙ ΕΙΔΙΚΟΙ ΠΡΟΒΛΕΠΟΥΝ ΚΑΛΥΤΕΡΑ" if ok else "ΔΕΝ ΠΕΡΝΑ"}')

P('')
P('=== ΕΛΛΕΙΨΗ ΠΛΗΡΟΦΟΡΙΑΣ; λαθος v1 ανα ομαδα vs «τι λενε οι ειδικοι» ===')
P('  για καθε ματς αγων 1-10, απο τη μερια καθε ομαδας: y = πραγματικη − v1 διαφορα · x = (ειδικοι − v1 αρχικο rating) της ομαδας − του αντιπαλου')
_, _ = None, None
# αρχικα rating v1 και ειδικων ανα σεζον-ομαδα
def start_nets(alpha):
    """αρχικο net (επιθεση−αμυνα) που βαζει το run_x για καθε ομαδα-σεζον (α=0: v1)."""
    res = {}
    for s in ES:
        N = len(RANK[s])
        for t_, r_ in RANK[s].items(): res[(s, t_)] = mapping(s, (r_ - 0.5) / N)
    return res
EXP = start_nets(1.0)
# v1 αρχικο net = 0.7 × net τελους προηγουμενης σεζον (απο run_x)
_, _ = None, None
prev_end = {}
if 'L' not in _PTS:
    ph, pa = points(D, 'L'); _PTS['L'] = (100 * ph / D.poss.values, 100 * pa / D.poss.values)
tmp = {}
def v1_start():
    EH, EA = _PTS['L']; prior = {}; mu0 = float((EH.mean() + EA.mean()) / 2); res = {}
    dnum = np.array([(dd - D.date.iloc[0]).days for dd in D.date])
    for s in SEAS:
        sidx = np.where(D.season.values == s)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t_: i for i, t_ in enumerate(teams)}; n = len(teams)
        for t_ in teams: res[(s, t_)] = 0.7 * (prior.get(t_, (0, 0))[0] - prior.get(t_, (0, 0))[1])
        o0 = np.array([0.7 * prior.get(t_, (0, 0))[0] for t_ in teams]); d0 = np.array([0.7 * prior.get(t_, (0, 0))[1] for t_ in teams])
        hi = np.array([ix[t_] for t_ in D.home.values[sidx]]); ai = np.array([ix[t_] for t_ in D.away.values[sidx]])
        neu = D.ff.values[sidx] | D.relocated.values[sidx]; hb = np.where(neu, 0.0, 3.0); dn = dnum[sidx]
        w = 0.5 ** ((dn.max() - dn) / 120)
        mu, O, Dd = fit_eff(hi, ai, EH[sidx], EA[sidx], hb, w, n, o0, d0, 8, mu0)
        prior = {t_: (O[i], Dd[i]) for t_, i in ix.items()}; mu0 = mu
    return res
V1S = v1_start()
rows = []
for k in np.where(early)[0]:
    s = SED[k]; h, a_ = D.home.values[k], D.away.values[k]
    if (s, h) not in EXP or (s, a_) not in EXP: continue
    x = (EXP[(s, h)] - V1S[(s, h)]) - (EXP[(s, a_)] - V1S[(s, a_)])
    rows.append(dict(s=s, rnd=RNDD[k], x=x, y=ACTD[k] - FULL[0.0][k]))
R = pd.DataFrame(rows)
for lab, m in (('αγων 1-5', R.rnd <= 5), ('αγων 6-10', (R.rnd > 5) & (R.rnd <= 10)), ('αγων 1-10', R.rnd <= 10)):
    x = R[m]; b = np.polyfit(x.x, x.y, 1)[0]
    res = x.y - b * x.x; se = math.sqrt(np.sum(res ** 2) / (len(x) - 2) / np.sum((x.x - x.x.mean()) ** 2))
    pos = sum(1 for s in ES if np.polyfit(x[x.s == s].x, x[x.s == s].y, 1)[0] > 0)
    P(f'  {lab}: κλιση {b:+.2f} (t {b/se:+.1f}) · θετικη σε {pos}/5 σεζον · ({len(x)} ματς)')
P('  (κλιση 1.0 ≈ οι ειδικοι εχουν δικιο ολοκληρο το «κενο»· 0 = καμια πληροφορια· 0.5 = το μισο)')
P('')
P('  ομαδες με μεγαλη διαφωνια ειδικων-v1 (|ειδικοι − v1 αρχικο| ≥ 3 π./100): μεσο λαθος v1 ανα ομαδα, αγων 1-10')
big = []
for (s, t_), ex in EXP.items():
    dl = ex - V1S[(s, t_)]
    if abs(dl) < 3: continue
    m = early & (SED == s) & ((D.home.values == t_) | (D.away.values == t_))
    sg = np.where(D.home.values[m] == t_, 1, -1)
    big.append((s, t_, dl, np.mean(sg * (ACTD[m] - FULL[0.0][m])), np.mean(sg * (ACTD[m] - FULL[0.5][m])), m.sum()))
for s, t_, dl, e1, e5, n in sorted(big, key=lambda z: z[2]):
    P(f'    {s[-4:]} {t_}: ειδικοι {"ΠΑΝΩ" if dl > 0 else "ΚΑΤΩ"} απο v1 κατα {dl:+.1f} → πραγματικο − v1 {e1:+.1f} π./ματς · με ειδικους (α .5) {e5:+.1f} ({n} ματς)')
agree = sum(1 for z in big if np.sign(z[2]) == np.sign(z[3]))
P(f'  → σε {agree}/{len(big)} ομαδες το v1 επεσε εξω ΠΡΟΣ την κατευθυνση που ελεγαν οι ειδικοι · μεσο |λαθος| v1 {np.mean([abs(z[3]) for z in big]):.1f} vs με ειδικους {np.mean([abs(z[4]) for z in big]):.1f}')
open('el_expert_accuracy_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
