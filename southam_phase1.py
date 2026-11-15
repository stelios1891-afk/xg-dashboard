"""
southam_phase1.py — 5/10/2026 ΦΑΣΗ 1: η μηχανη vs η αγορα (τελικο 1Χ2 Pinnacle, football-data) — Βραζιλια & MLS.
  (α) ΑΚΡΙΒΕΙΑ: RPS μοντελου vs αγορας ανα λιγκα / παραθυρο (1-6, 7-14, 15+) / σεζον (ζευγαρωτο ±SE)
  (β) ΒΑΡΟΣ w: log-linear συνδυασμος p ∝ αγορα^(1−w)·μοντελο^w — βελτιστο w (0 = το μοντελο δεν προσθετει τιποτα), ανα σεζον
  (γ) ΚΛΙΣΗ ΠΛΗΡΟΦΟΡΙΑΣ b: (πραγματικη διαφορα γκολ − αγορα) ~ b·(μοντελο − αγορα) — b>0 = η διαφωνια μας εχει σημα
      (+ ιδιο για ΠΡΑΓΜΑΤΙΚΟ xG διαφορα — λιγοτερος θορυβος)
  (δ) ΒΑΘΜΟΝΟΜΗΣΗ μοντελου: συμπιεση (κλιση πραγματικης vs προβλεπομενης υπεροχης), εδρα μοντελο/αγορα/πραγματικο ανα σεζον
  (ε) ΠΑΡΑΛΛΑΓΕΣ: base / χωρις SoS / μονο φετινα / χωρις γκολ (σκετο xG) — RPS
Μονο κανονικη περιοδος (MLS playoffs χωριστα). Τιποτα live.
"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import southam_common as C

P = pd.read_csv('southam_preds.csv')
P = C.attach_fd(P)
print('ταιριασμα με τελικο 1Χ2 Pinnacle: ' + ' · '.join(f'{lg} {s}: {g.PSCH.notna().mean()*100:.0f}%' for (lg, s), g in P.groupby(['league', 'season'])))
P = P[P.PSCH.notna() & P.PSCD.notna()].copy()
inv = 1 / P[['PSCH', 'PSCD', 'PSCA']].values; q = inv / inv.sum(1, keepdims=True)
P['mH'], P['mD'], P['mA'] = q[:, 0], q[:, 1], q[:, 2]
P['res'] = np.sign(P.hg - P.ag).astype(int)
L = C.market_lambdas(P.mH.values, P.mD.values, P.mA.values); P['mlh'], P['mla'] = L[:, 0], L[:, 1]
for v in ('base', 'nosos', 'insea', 'noblend'):
    ok = P[f'lh_{v}'].notna()
    pr = [C.probs_1x2(a, b) if o else (np.nan,) * 3 for a, b, o in zip(P[f'lh_{v}'], P[f'la_{v}'], ok)]
    P[[f'{v}H', f'{v}D', f'{v}A']] = np.array(pr)
    P[f'rps_{v}'] = [C.rps((a, b, c), r) if o else np.nan for a, b, c, r, o in zip(P[f'{v}H'], P[f'{v}D'], P[f'{v}A'], P.res, ok)]
P['rps_m'] = [C.rps((a, b, c), r) for a, b, c, r in zip(P.mH, P.mD, P.mA, P.res)]
P['win'] = np.where(P.stage == 'playoff', 'playoff', np.where(P.md <= 6, '1-6', np.where(P.md <= 14, '7-14', '15+')))
P.to_csv('southam_phase1_rows.csv', index=False)

def pair(d, a, b='rps_m'):
    x = (d[a] - d[b]).dropna()
    return f'{1000*x.mean():+6.2f} ±{1000*x.std()/np.sqrt(max(len(x),1)):4.2f} (n{len(x)})' if len(x) > 5 else '   —'

print('\n(α) ΑΚΡΙΒΕΙΑ — RPS μοντελου ΜΕΙΟΝ αγορας (×1000· θετικο = η αγορα καλυτερη· CORE7 live ≈ +5)')
for lg in ('Brazil', 'MLS'):
    d = P[P.league == lg]
    print(f'\n  [{lg}]  αγορα RPS {d.rps_m.mean():.4f}')
    for w in ('1-6', '7-14', '15+', 'playoff'):
        x = d[d.win == w]
        if len(x): print(f'    αγων {w:8s} base {pair(x, "rps_base")} · ανα σεζον: ' + ' '.join(f'{s}:{1000*(g.rps_base-g.rps_m).mean():+.1f}' for s, g in x.groupby('season')))

def wfit(d, v='base'):
    lm = np.log(d[['mH', 'mD', 'mA']].values); lq = np.log(np.clip(d[[f'{v}H', f'{v}D', f'{v}A']].values, 1e-9, 1))
    y = d.res.map({1: 0, 0: 1, -1: 2}).values; best = None
    for w in np.arange(-0.3, 1.01, 0.02):
        z = (1 - w) * lm + w * lq; z = z - z.max(1, keepdims=True); p = np.exp(z); p /= p.sum(1, keepdims=True)
        ll = -np.log(p[np.arange(len(y)), y]).mean()
        if best is None or ll < best[1]: best = (w, ll)
    return best[0]
print('\n(β) ΒΑΡΟΣ w του μοντελου σε συνδυασμο με την αγορα (0 = τιποτα · 0.10 = 10% · αρνητικο = βλαπτει)')
for lg in ('Brazil', 'MLS'):
    for w in ('7-14', '15+', 'ΟΛΑ 7+'):
        d = P[(P.league == lg) & (P.win.isin(['7-14', '15+']) if w == 'ΟΛΑ 7+' else P.win == w)]
        print(f'  {lg:6s} {w:7s} w={wfit(d):+.2f} · ανα σεζον: ' + ' '.join(f'{s}:{wfit(g):+.2f}' for s, g in d.groupby('season')))

def bfit(x, y):
    X = np.c_[np.ones(len(x)), x]; c, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ c; se = np.sqrt((r ** 2).sum() / (len(x) - 2) / ((x - x.mean()) ** 2).sum())
    return c[1], se
print('\n(γ) ΚΛΙΣΗ ΠΛΗΡΟΦΟΡΙΑΣ b: (πραγματικο − αγορα) ~ b·(μοντελο − αγορα), υπεροχη γηπεδουχου σε γκολ · ±SE')
print('    b=0: η διαφωνια μας ειναι θορυβος · b=1: η διαφωνια μας ειναι πληρως σωστη · (CORE7 15+: ≈0)')
for lg in ('Brazil', 'MLS'):
    for w in ('7-14', '15+'):
        d = P[(P.league == lg) & (P.win == w)].dropna(subset=['mlh'])
        dm = (d.lh_base - d.la_base) - (d.mlh - d.mla)
        b1, s1 = bfit(dm.values, ((d.hg - d.ag) - (d.mlh - d.mla)).values)
        b2, s2 = bfit(dm.values, ((d.h_xg_act - d.a_xg_act) - (d.mlh - d.mla)).values)
        ps = []
        for s, g in d.groupby('season'):
            gm = (g.lh_base - g.la_base) - (g.mlh - g.mla); ps.append(f'{s}:{bfit(gm.values, ((g.hg-g.ag)-(g.mlh-g.mla)).values)[0]:+.2f}')
        print(f'  {lg:6s} {w:5s} n{len(d):4d} · σε γκολ b={b1:+.2f} ±{s1:.2f} · σε xG b={b2:+.2f} ±{s2:.2f} · μεση |διαφωνια| {dm.abs().mean():.2f} · ανα σεζον (γκολ) {" ".join(ps)}')

print('\n(δ) ΒΑΘΜΟΝΟΜΗΣΗ — κλιση πραγματικης υπεροχης πανω στην προβλεπομενη (1 = σωστο, >1 = το μοντελο ΣΥΜΠΙΕΖΕΙ· CORE7 1.07)')
for lg in ('Brazil', 'MLS'):
    d = P[(P.league == lg) & P.win.isin(['7-14', '15+'])]
    b, s = bfit((d.lh_base - d.la_base).values, (d.hg - d.ag).values)
    bm, sm = bfit((d.mlh - d.mla).values, (d.hg - d.ag).values)
    print(f'  {lg:6s}: μοντελο {b:.2f} ±{s:.2f} · αγορα {bm:.2f} ±{sm:.2f}')
print('\n    ΕΔΡΑ ανα σεζον (μεση υπεροχη γηπεδουχου σε γκολ, αγων 7+): μοντελο / αγορα / πραγματικο / πραγματικο xG')
for lg in ('Brazil', 'MLS'):
    d = P[(P.league == lg) & P.win.isin(['7-14', '15+'])]
    print(f'  {lg:6s} ' + ' · '.join(f'{s}: {(g.lh_base-g.la_base).mean():+.2f}/{(g.mlh-g.mla).mean():+.2f}/{(g.hg-g.ag).mean():+.2f}/{(g.h_xg_act-g.a_xg_act).mean():+.2f}' for s, g in d.groupby('season')))
print('\n    ΓΚΟΛ ανα σεζον (συνολο, αγων 7+): μοντελο / πραγματικα / πραγματικο xG')
for lg in ('Brazil', 'MLS'):
    d = P[(P.league == lg) & P.win.isin(['7-14', '15+'])]
    print(f'  {lg:6s} ' + ' · '.join(f'{s}: {(g.lh_base+g.la_base).mean():.2f}/{(g.hg+g.ag).mean():.2f}/{(g.h_xg_act+g.a_xg_act).mean():.2f}' for s, g in d.groupby('season')))

print('\n(ε) ΠΑΡΑΛΛΑΓΕΣ — RPS μειον αγορας (×1000), αγων 7+, ιδια ματς (οπου υπαρχουν ολες)')
for lg in ('Brazil', 'MLS'):
    d = P[(P.league == lg) & P.win.isin(['7-14', '15+'])].dropna(subset=['rps_insea', 'rps_noblend'])
    print(f'  {lg:6s} n{len(d)}: ' + ' · '.join(f'{v} {1000*(d["rps_"+v]-d.rps_m).mean():+.2f}' for v in ('base', 'nosos', 'insea', 'noblend')))
    for w in ('7-14', '15+'):
        x = d[d.win == w]
        print(f'      {w:5s}: ' + ' · '.join(f'{v} {1000*(x["rps_"+v]-x.rps_m).mean():+.2f}' for v in ('base', 'nosos', 'insea', 'noblend')))
