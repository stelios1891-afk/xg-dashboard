"""core7_totals_gap_samephase.py — 15/10/2026 (Στελιος: «που οφειλεται η τοσο μεγαλη διαφορα με το παρελθον; δειξε τη διαφορα μοντελου-αγορας
ΣΤΗΝ ΙΔΙΑ ΦΑΣΗ που ειμαστε τωρα σε καθε πρωταθλημα — και στο backtest τοσο νωρις θα ειχαμε μεγαλυτερη διαφορα»).
Για καθε λιγκα: οι αγωνιστικες που εχουμε φετος (με σκορ και κλεισιμο Pinnacle) → ΙΔΙΕΣ αγωνιστικες 2223-2526 (Crown κλεισιμο, ιδια live μηχανη
replay core7_mech_preds_bl_0.6). Μοντελο − αγορα, μοντελο − πραγματικα, αγορα − πραγματικα, + πραγματικα γκολ."""
import sys, os, io
_s = open('core7_totals_anchor_md1_test.py', encoding='utf-8').read()
_TO = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s[:_s.index('def anchored')]); sys.stdout = _TO
sys.stdout.reconfigure(encoding='utf-8')
# πραγματικα γκολ για ολες τις αγωνιστικες
TGA = {}
for f in glob.glob('data_*_*.json'):
    try: d = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    if not isinstance(d, dict): continue
    for k, v in d.items():
        try: TGA[str(k)] = int(v['hs']) + int(v['as'])
        except Exception: pass
P['tg'] = P.mid.map(TGA); P['mod'] = P.xg_h + P.xg_a; P['gw'] = P.md + 1
H = P[P.T_mkt.notna() & P.tg.notna()].copy(); H['mkt'] = H.T_mkt
# φετος
_s2 = open('core7_totals_gap_now.py', encoding='utf-8').read()
sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s2[:_s2.index('def line')]); sys.stdout = _TO
F = X
def st(y, mod='mod', mkt='mkt', tg='tg'):
    return (len(y), y[tg].mean(), (y[mod] - y[mkt]).mean(), (y[mod] - y[tg]).mean(), (y[mkt] - y[tg]).mean())
fmt = lambda t: f'n{t[0]:4d} γκολ {t[1]:.2f} │ μοντ−αγορα {t[2]:+.2f} · μοντ−πραγμ {t[3]:+.2f} · αγορα−πραγμ {t[4]:+.2f}'
print('ΙΔΙΑ ΦΑΣΗ ΣΕΖΟΝ: φετος (Pinnacle κλεισιμο) vs ιδιες αγωνιστικες 2223-2526 (Crown κλεισιμο)')
tot_f = []; tot_h = []
for lg in sorted(F.lg.unique()):
    f = F[F.lg == lg]; g0, g1 = int(f.gw.min()), int(f.gw.max())
    h = H[(H.league == lg) & H.gw.between(g0, g1)]
    print(f'\n{lg}  αγωνιστικες {g0}-{g1}')
    print(f'   ΦΕΤΟΣ      {fmt(st(f))}')
    print(f'   ΙΣΤΟΡΙΚΟ   {fmt(st(h))}')
    for s in sorted(h.season.unique()): print(f'     {s}     {fmt(st(h[h.season == s]))}')
    tot_f.append(f); tot_h.append(h)
import pandas as pd
f = pd.concat(tot_f); h = pd.concat(tot_h)
print(f'\nΣΥΝΟΛΟ CORE7 (ιδιες αγωνιστικες ανα λιγκα)')
print(f'   ΦΕΤΟΣ      {fmt(st(f))}')
print(f'   ΙΣΤΟΡΙΚΟ   {fmt(st(h))}')
for s in sorted(h.season.unique()): print(f'     {s}     {fmt(st(h[h.season == s]))}')
