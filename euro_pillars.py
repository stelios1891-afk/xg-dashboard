# -*- coding: utf-8 -*-
"""euro_pillars.py — 5/11/2026 (Στελιος: «οι βασικοι πυλωνες αξιζουν περαιτερω τεστ; καλυτερος ρυθμιστης πρωταθληματων;»). ΑΝΩΤΑΤΟ ΟΡΙΟ του τι δινει καλυτερος ρυθμιστης, με την καθαρη μηχανη.
Στοχος y = 60% xG + 40% γκολ (διαφορα γηπ−φιλ, 90′). Υπεροχη' = c·υπεροχη + d(λιγκα γηπ) − d(λιγκα φιλ), ιδιο συνολο γκολ.
  L(k): d ανα λιγκα μαθαινει απο τα ευρωπαικα· ΚΑΘΕ ΟΜΑΔΑ ΜΕΤΡΑ ΙΣΑ (μια Bodø δεν σερνει τη λιγκα)· d = Σ μεσος ομαδας / (ομαδες + k).
  C: c ανα διοργανωση (μεταφορα δυναμης ομαδας UCL/UEL/UECL). LC(k): και τα δυο.
LOSO: εκπαιδευση στις αλλες 3 σεζον. WF: μονο σε προηγουμενες σεζον. Σημειο αναφορας: RPS αγορας (κλεισιμο).
ΚΡΙΤΗΡΙΑ (γραφτηκαν πριν): Κ1 RPS εκτος δειγματος καλυτερο συνολικα ΚΑΙ ≥3/4 σεζον (k απο τις αλλες σεζον) · Κ2 μοναδες 7 live κανονων χαντικαπ ≥ σημερα · Κ3 αντεχει σε WF (RPS καλυτερο)."""
import sys, json, glob
_src = open('euro_clean_rules.py', encoding='utf-8').read()
exec(_src[:_src.index('# ---------- ΧΑΝΤΙΚΑΠ LIVE')])
LGH = np.array([_V['lg_h'][_VI[m]] if m in _VI else '?' for m in MIDS]); LGA = np.array([_V['lg_a'][_VI[m]] if m in _VI else '?' for m in MIDS])
NMH = {}
for f in glob.glob('data_Europe_*.json'):
    for k_, m in json.load(open(f, encoding='utf-8')).items(): NMH[str(k_)] = (m['home']['name'], m['away']['name'])
HN = np.array([NMH.get(m, ('?', '?'))[0] for m in MIDS]); AN = np.array([NMH.get(m, ('?', '?'))[1] for m in MIDS])
L0 = P6['INS']; S0 = L0[0] - L0[1]; T0 = L0[0] + L0[1]
XDv = np.array([(XG[m][0] - XG[m][1]) if m in XG else np.nan for m in MIDS]); Y = np.where(np.isfinite(XDv), .6 * XDv + .4 * GD, GD.astype(float))
KN = (LGH != '?') & (LGA != '?'); CMPS = ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague')
def fit(tr, k, use_l, use_c):
    d = {}; c = {x: 1.0 for x in CMPS}; a0 = {x: 0.0 for x in CMPS}; idx = np.where(tr & KN)[0]; cross = idx[LGH[idx] != LGA[idx]]
    for _ in range(6):
        Dv = np.array([d.get(LGH[i], 0.) - d.get(LGA[i], 0.) for i in idx])
        if use_c:
            for x in CMPS:
                m = COMP[idx] == x; yy = Y[idx][m] - Dv[m]; ss = S0[idx][m]; c[x] = float(((ss - ss.mean()) * (yy - yy.mean())).sum() / ((ss - ss.mean()) ** 2).sum()); a0[x] = float(ss.mean() * (1 - c[x]))   # 5/11: συμπιεση ΓΥΡΩ απο τον μεσο ορο, αλλιως χανεται και η εδρα
        if use_l:
            cc = np.array([c[x] for x in COMP[cross]]); aa = np.array([a0[x] for x in COMP[cross]]); a = np.mean(Y[cross] - aa - cc * S0[cross])
            newd = {}
            clubs = {}
            for i, q, q0 in zip(cross, cc, aa):
                r = Y[i] - q0 - q * S0[i] - a
                clubs.setdefault(LGH[i], {}).setdefault(HN[i], []).append(r + d.get(LGA[i], 0.))
                clubs.setdefault(LGA[i], {}).setdefault(AN[i], []).append(-r + d.get(LGH[i], 0.))
            for lg, tm in clubs.items():
                newd[lg] = sum(np.mean(v) for v in tm.values()) / (len(tm) + k)
            mu = np.mean(list(newd.values())); d = {g: v - mu for g, v in newd.items()}
    return d, c, a0
def adj(mask, d, c, a0, L):
    h, a = np.array(L[0], float).copy(), np.array(L[1], float).copy()
    for i in np.where(mask)[0]:
        s = a0[COMP[i]] + c[COMP[i]] * (L[0][i] - L[1][i]) + d.get(LGH[i], 0.) - d.get(LGA[i], 0.); t = L[0][i] + L[1][i]
        h[i] = max((t + s) / 2, .05); a[i] = max((t - s) / 2, .05)
    return h, a
def build(k, use_l, use_c, wf=False):
    H6 = np.array(L0[0], float).copy(); A6 = np.array(L0[1], float).copy(); H8 = np.array(P8['INS'][0], float).copy(); A8 = np.array(P8['INS'][1], float).copy()
    for n_, s in enumerate(SEAS):
        tr = np.isin(SEA, SEAS[:n_]) if wf else (SEA != s)
        if not tr.any(): continue
        d, c, a0 = fit(tr, k, use_l, use_c); m = SEA == s
        h, a = adj(m & KN, d, c, a0, L0); H6[m] = h[m]; A6[m] = a[m]
        h, a = adj(m & KN, d, c, a0, P8['INS']); H8[m] = h[m]; A8[m] = a[m]
    return (H6, A6), (H8, A8)
y1 = (GD > 0).astype(float); yx = (GD == 0).astype(float)
def rps(L):
    o = np.zeros(len(MIDS))
    for i in range(len(MIDS)):
        D = sdist(L[0][i], L[1][i]); p1 = sum(p for g, p in D.items() if g > 0); px = D.get(0, 0.)
        o[i] = ((p1 - y1[i]) ** 2 + (p1 + px - y1[i] - yx[i]) ** 2) / 2
    return o
KS = np.full(len(MIDS), np.nan)
for i, m in enumerate(MIDS):
    v = [fair(*snap(m, b, 0)) for b in ('Crown', 'SBOBET') if snap(m, b, 0)]
    if v: KS[i] = np.mean(v)
has = np.isfinite(KS) & KN
R0 = rps(L0); RM = rps((np.maximum((T0 + np.nan_to_num(KS)) / 2, .05), np.maximum((T0 - np.nan_to_num(KS)) / 2, .05)))
print(f'ΔΕΙΓΜΑ RPS: {has.sum()} ματς με κλεισιμο · RPS σημερα {R0[has].mean():.4f} · αγορα {RM[has].mean():.4f} · διαφορα αγορα−μοντελο {1000 * (RM - R0)[has].mean():+.2f}±{1000 * (RM - R0)[has].std() / np.sqrt(has.sum()):.2f} ×10⁻³')
for x in CMPS:
    m = has & (COMP == x); print(f'   {x[:8]:8s} n{m.sum():4d} σημερα {R0[m].mean():.4f} αγορα {RM[m].mean():.4f} · ' + ' '.join(f"{s[2:]}:{1000 * (RM - R0)[m & (SEA == s)].mean():+.2f}" for s in SEAS))
GRID = [('C', 0, False, True)] + [(f'L{k}', k, True, False) for k in (1, 2, 4, 8, 16)] + [(f'LC{k}', k, True, True) for k in (2, 4, 8)]
ENG = {}; RR = {}
print('\nΚ1. RPS ×10⁻³ vs σημερα, εκτος δειγματος (αρνητικο = καλυτερο)')
def row(lab, r):
    d = (r - R0)[has]; sea = SEA[has]; cmp_ = COMP[has]
    return f"   {lab:8s} ΟΛΑ {1000 * d.mean():+.2f}±{1000 * d.std() / np.sqrt(len(d)):.2f} │ " + ' '.join(f"{x[:3]} {1000 * d[cmp_ == x].mean():+.2f}" for x in CMPS) + ' │ ' + ' '.join(f"{s[2:]}:{1000 * d[sea == s].mean():+.2f}" for s in SEAS)
for lab, k, ul, uc in GRID:
    ENG[lab] = build(k, ul, uc); RR[lab] = rps(ENG[lab][0]); print(row(lab, RR[lab]))
FAM = {'L': [g[0] for g in GRID if g[0].startswith('L') and not g[0].startswith('LC')], 'LC': [g[0] for g in GRID if g[0].startswith('LC')]}
VER = {}
for fam, names in FAM.items():
    oos = R0.copy(); ch = {}
    for s in SEAS:
        tr = has & (SEA != s); b = min(names, key=lambda n: RR[n][tr].mean()); ch[s] = b; oos[SEA == s] = RR[b][SEA == s]
    d = (oos - R0)[has]; ok = d.mean() < 0 and sum(d[SEA[has] == s].mean() < 0 for s in SEAS) >= 3
    VER[fam] = (ch, ok, oos); print(f"   {fam} με k απο τις αλλες σεζον: " + ' '.join(f'{s[2:]}→{v}' for s, v in ch.items()) + ' ' + row('', oos).strip() + f" → Κ1 {'✓' if ok else '✗'}")
print('\nΚ3. ΜΟΝΟ ΑΠΟ ΠΡΟΗΓΟΥΜΕΝΕΣ ΣΕΖΟΝ (WF, 2324-2526)')
wfm = has & (SEA != '2223')
for lab, k, ul, uc in (('C', 0, False, True), ('L4', 4, True, False), ('L8', 8, True, False), ('LC4', 4, True, True), ('LC8', 8, True, True)):
    r = rps(build(k, ul, uc, wf=True)[0]); d = (r - R0)[wfm]; print(f"   {lab:5s} {1000 * d.mean():+.2f}±{1000 * d.std() / np.sqrt(len(d)):.2f} │ " + ' '.join(f"{s[2:]}:{1000 * (r - R0)[has & (SEA == s)].mean():+.2f}" for s in SEAS[1:]))
print('\nΚ2. ΜΟΝΑΔΕΣ 7 LIVE ΚΑΝΟΝΩΝ ΧΑΝΤΙΚΑΠ (UCL = νεα μορφη)')
side_nf = lambda i: (1 if FMA[i] else -1); home = lambda i: 1
RULES = (('UCL φαβ', 6, UCLA, 'fav', .04, H_UCL, True, None, True), ('UCL dog', 6, UCLA, 'dog', .10, H_UCL, True, None, True), ('UCL DNB', 6, UCLA, 'dnb', .04, H_UCL, True, None, True), ('UEL φαβ εντ', 8, UELA, 'fav', .04, H_UEL, False, home, False),
         ('UECL Α φαβ', 6, ECA, 'fav', .04, H_72, False, None, False), ('UECL Α dog', 6, ECA, 'dog', .10, H_72, False, None, False), ('UECL Β dog', 6, ECB, 'dog', .10, H_72, False, side_nf, False))
def picks_of(E6, E8):
    out = {}
    for lab, bl, mk, kd, thr, hs, hon, sf, nw in RULES:
        z = at(seq_ah(E6 if bl == 6 else E8, GD, mk, kd, hs, hon, sf), thr); out[lab] = z[z.sea.isin(NEW)] if nw else z
    return out
ZP = {'σημερα': picks_of(L0, P8['INS'])}
for lab, *_ in GRID: ZP[lab] = picks_of(*ENG[lab])
for lab, z in ZP.items():
    print(f"   {lab:7s} ΣΥΝΟΛΟ {sum(len(q) for q in z.values()) / 2:4.0f}p {sum(units(q) for q in z.values()):+6.1f}μ │ " + ' · '.join(f"{n} {len(q) / 2:.0f}p {100 * q.pnl.mean():+.0f}%" for n, q in z.items()))
base = sum(units(q) for q in ZP['σημερα'].values())
for fam in FAM:
    ch = VER[fam][0]; lo = sum(units(ZP[ch[s]][n][ZP[ch[s]][n].sea == s]) for s in SEAS for n in ZP[ch[s]])
    print(f"   {fam} με k απο τις αλλες σεζον: {lo:+.1f}μ vs σημερα {base:+.1f}μ → Κ2 {'✓' if lo >= base else '✗'}")
print('\nΤΙ ΜΑΘΑΙΝΕΙ (ολες οι σεζον)')
d, c, a0 = fit(np.ones(len(MIDS), bool), 4, True, True); print('   c ανα διοργανωση: ' + ' · '.join(f'{x[:3]} {v:.2f}' for x, v in c.items()))
_, c2, _a = fit(np.ones(len(MIDS), bool), 0, False, True); print('   c χωρις d: ' + ' · '.join(f'{x[:3]} {v:.2f}' for x, v in c2.items()))
o = sorted(d.items(), key=lambda kv: -kv[1]); print('   d (γκολ) ψηλα: ' + ' · '.join(f'{g[:14]} {v:+.2f}' for g, v in o[:10])); print('   d (γκολ) χαμηλα: ' + ' · '.join(f'{g[:14]} {v:+.2f}' for g, v in o[-10:]))
for g in ('Belgium', 'Eliteserien', 'DanishSuperLiga', 'Allsvenskan', 'SwissSuperleague', 'EPL', 'Bundesliga'): print(f'   {g}: {d.get(g, 0):+.2f}')
print(f"   St.Truiden–Brann: υπεροχη 1.84 → {a0['ConferenceLeague'] + c['ConferenceLeague'] * 1.84 + d.get('Belgium', 0) - d.get('Eliteserien', 0):+.2f}")
