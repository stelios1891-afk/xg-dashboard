# -*- coding: utf-8 -*-
"""el_early_over_rule_test.py — ΚΑΝΟΝΑΣ «ΠΡΩΙΜΑ OVER ΔΕΝ ΠΑΙΖΟΝΤΑΙ» (25/9/2026, αιτημα Στελιου).
Βαση: live συνολα (v2 + Κ2), picks edge ≥8% (οπως live) — αναφορα και ≥10%.
Κανονας: over συνολου στις αγωνιστικες ≤ R → μονο καταγραφη (δεν μετρανε). Under & χαντικαπ ανεπηρεαστα.
LOSO: για τη σεζον-εξω, απο τις ΑΛΛΕΣ 5: μονάδες των πρωιμων over για R=6 και R=10· αν καποιο < 0 → εφαρμοζεται το R με
  τις πιο αρνητικες μοναδες, αλλιως κανενας κανονας. Κρινεται στη σεζον-εξω.
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (ΜΙΑ εκτελεση, edge ≥8%): ROI συνολων ΜΕ κανονα > ΧΩΡΙΣ · μοναδες οχι λιγοτερες · κερδοφορες σεζον οχι λιγοτερες.
Εξοδος: el_early_over_rule_test_out.txt"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
_o3 = []
src = open('el_total_curve_test.py', encoding='utf-8').read().split("VARS = {")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out = _o3
def P(s=''):
    print(s, flush=True); out.append(str(s))
jj = [j for j in range(len(IDX)) if RS[j] and not np.isnan(PRC[j, 0])]
BT = tot_bets(C2); BT['rnd'] = RND[jj]
def units(b): return b.p.sum()
res = {}
for thr in (0.08, 0.10):
    b = BT[BT.edge >= thr]
    kept, dec = [], []
    for s in SS:
        tr = b[b.season != s]
        u = {R: units(tr[(tr.role == 'over') & (tr.rnd <= R)]) for R in (6, 10)}
        R = min(u, key=u.get) if min(u.values()) < 0 else None
        te = b[b.season == s]
        kept.append(te if R is None else te[~((te.role == 'over') & (te.rnd <= R))])
        dec.append((s, R, u))
    K = pd.concat(kept)
    res[thr] = (b, K, dec)
P('=== LOSO αποφασεις (μοναδες πρωιμων over στις αλλες 5 σεζον, edge ≥8%) ===')
for s, R, u in res[0.08][2]:
    P(f'  {s[-4:]} εξω: ως 6η {u[6]:+.1f}u · ως 10η {u[10]:+.1f}u → κανονας: {"οχι" if R is None else f"over ως την {R}η δεν παιζονται"}')
P('')
for thr in (0.08, 0.10):
    b, K, _ = res[thr]
    pb = sum(1 for s in SS if b[b.season == s].p.mean() > 0); pk = sum(1 for s in SS if len(K[K.season == s]) and K[K.season == s].p.mean() > 0)
    P(f'=== edge ≥{thr*100:.0f}% ===')
    P(f'  ΧΩΡΙΣ κανονα: {b.p.mean()*100:+.2f}% ({len(b)} στοιχηματα, {units(b):+.1f}u) · κερδοφορες σεζον {pb}/6')
    P(f'  ΜΕ κανονα:    {K.p.mean()*100:+.2f}% ({len(K)} στοιχηματα, {units(K):+.1f}u) · κερδοφορες σεζον {pk}/6')
    P('  ανα σεζον (χωρις → με): ' + ' · '.join(f'{s[-2:]}: {b[b.season == s].p.mean()*100:+.1f}% → {K[K.season == s].p.mean()*100:+.1f}%' for s in SS))
    cut = len(b) - len(K)
    P(f'  κομμενα στοιχηματα: {cut} · μοναδες τους {units(b) - units(K):+.1f}u')
    P('')
b, K, _ = res[0.08]
pb = sum(1 for s in SS if b[b.season == s].p.mean() > 0); pk = sum(1 for s in SS if len(K[K.season == s]) and K[K.season == s].p.mean() > 0)
ok = (K.p.mean() > b.p.mean()) and (units(K) >= units(b)) and (pk >= pb)
P(f'ΚΡΙΤΗΡΙΑ (≥8%): ROI {"✓" if K.p.mean() > b.p.mean() else "✗"} · μοναδες {"✓" if units(K) >= units(b) else "✗"} · σεζον {"✓" if pk >= pb else "✗"} → {"ΠΕΡΝΑ" if ok else "ΔΕΝ ΠΕΡΝΑ"}')
open('el_early_over_rule_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
