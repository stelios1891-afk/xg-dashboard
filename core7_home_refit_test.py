# -*- coding: utf-8 -*-
"""core7_home_refit_test.py — ΔΙΟΡΘΩΣΗ ΕΔΡΑΣ στη μηχανη CORE7 (10/10/2026, Στελιος: «τρεξτο αναλυτικα, ειναι σημαντικο»).
Ευρημα: η μηχανη δινει στον γηπεδουχο ~+0.27-0.28 γκολ, η αγορα (Pinnacle) +0.33-0.34, το πραγματικο +0.34-0.39, σε ΚΑΘΕ σεζον.
Η εδρα μπαινει ως σταθερος συντελεστης λιγκας HFA_FIX (EPL 1.10 …): xG γηπ × hf, xG φιλ ÷ hf. Εδω: επιπλεον πολλαπλασιαστης k
  (xG γηπ × k, xG φιλ ÷ k) ≡ hf × k. Μηχανη = LIVE (core7_mech_preds_cur_0.75_6_13~emps: SoS 0.75, κοκκινες emps, DC).
ΕΚΔΟΧΕΣ (καθε σεζον-τεστ με k απο τις ΑΛΛΕΣ 3 σεζον, LOSO):
  L  live (k = 1)
  A  ΚΟΙΝΟ k για ολες τις λιγκες (το καλυτερο RPS στις αλλες σεζον, πλεγμα 1.00-1.12 ανα .01)
  B  k ΑΝΑ ΛΙΓΚΑ (καλυτερο RPS της λιγκας στις αλλες σεζον), μαζεμενο 50% προς το Α
  C  k ΑΝΑ ΛΙΓΚΑ ωστε η μεση υπεροχη γηπ. του μοντελου = της αγορας (Pinnacle κλεισιμο) στις αλλες σεζον
PICKS οπως το live: dogs 15+ (evaluate_bet· κοντες γραμμες με αγκυρα λ .5) · φαβορι 15+ (evaluate_fav, αγκυρα ×0.7) ·
  κοντα φαβορι 7-14 (fav714: −0.5/−0.75, 1.70-2.10, edge ≥0, σωστα τεταρτα) · dogs 7-14 (καταγραφη, αναφορα).
  Αγκυρα: offsets ομαδων απο Pinnacle κλεισιμο των ΠΡΟΗΓΟΥΜΕΝΩΝ ματς (core7_anchor.run λ .5), πανω στη ΔΙΟΡΘΩΜΕΝΗ μηχανη.
  Τιμες: Pinnacle κλεισιμο (football-data) · Crown & Bet365 ανοιγμα/κλεισιμο (nowgoal). (φιλτρο προπονητη: εκτος)
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (ΠΡΙΝ την εκτελεση) — μια εκδοχη ΑΝΤΙΚΑΘΙΣΤΑ το live αν ΟΛΑ:
  (1) RPS LOSO καλυτερο σε ≥3/4 σεζον ΚΑΙ στον μεσο ορο,
  (2) η μεση υπεροχη γηπ. του μοντελου πλησιαζει την πραγματικη (|μοντ − πραγμ| μικροτερο),
  (3) dogs 15+ (το βασικο live) μοναδες ≥ live − 2 σε ΚΑΘΕ βιβλιο κλεισιματος (Pinnacle/Crown/Bet365),
  (4) αθροισμα μοναδων των 3 live κανονων (dogs 15+, φαβ 15+, κοντα φαβ 7-14) ≥ live σε ≥2/3 βιβλια κλεισιματος.
Εξοδος: core7_home_refit_out.txt"""
import sys, io, contextlib
import numpy as np, pandas as pd
src = open('core7_714_shortfav_test.py', encoding='utf-8').read().split("rows = []\nfor r in W.itertuples():")[0]
src = src.replace("core7_mech_preds_cur_1.0_6_13.csv", "core7_mech_preds_cur_0.75_6_13~emps.csv")
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
g = {'__name__': 'hr'}
with contextlib.redirect_stdout(_Q()):
    exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
D, NG, picks = g['D'], g['NG'], g['picks']
D = D[D.xh.notna()].reset_index(drop=True)
SEAS = sorted(D.season.unique()); LGS = sorted(D.league.unique())
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
P(f'ματς {len(D)} · με Pinnacle κλεισιμο {D.s_mkt.notna().sum()} · σεζον {SEAS} · md 0-{D.md.max()}')
y = D.y.values; GD = D.gd.values.astype(float); MK = D.s_mkt.values
def sk(k):
    k = np.asarray(k, float) if np.ndim(k) else np.full(len(D), float(k))
    return D.xh.values * k, D.xa.values / k
def probs(xh, xa):
    o = np.zeros((len(xh), 3))
    for i, (a, b) in enumerate(zip(xh, xa)):
        d = picks.gd_dist_dom(max(a, .05), max(b, .05))
        o[i] = (sum(v for k, v in d.items() if k > 0), d.get(0, 0.0), sum(v for k, v in d.items() if k < 0))
    return o
def rps_v(pm):
    o = np.zeros_like(pm); o[np.arange(len(y)), 2 - y] = 1
    return ((np.cumsum(pm, 1) - np.cumsum(o, 1)) ** 2)[:, :2].sum(1) / 2
KS = np.round(np.arange(1.00, 1.121, .01), 3)
RV = {}
for k in KS:
    xh, xa = sk(k); RV[k] = rps_v(probs(xh, xa)); print(f'  k {k} ok', flush=True)
def m_rps(k, mask): return float(RV[k][mask].mean())
SEA = D.season.values; LGV = D.league.values
# ---- LOSO k ανα εκδοχη ----
kA, kB, kC = np.ones(len(D)), np.ones(len(D)), np.ones(len(D)); chA = {}; chB = {}; chC = {}
for s in SEAS:
    tr = SEA != s; te = SEA == s
    a = min(KS, key=lambda k: m_rps(k, tr)); chA[s] = a; kA[te] = a
    for lg in LGS:
        ml = tr & (LGV == lg); b = min(KS, key=lambda k: m_rps(k, ml)); bb = a + .5 * (b - a); chB[(s, lg)] = round(bb, 3)
        kB[te & (LGV == lg)] = bb
        mm = ml & ~np.isnan(MK); tgt = MK[mm].mean()
        c = min(np.round(np.arange(.95, 1.25, .005), 3), key=lambda k: abs((D.xh.values[mm] * k - D.xa.values[mm] / k).mean() - tgt))
        chC[(s, lg)] = c; kC[te & (LGV == lg)] = c
P('\nΕΠΙΛΟΓΕΣ k (LOSO): Α κοινο ' + ' · '.join(f'{s}: {chA[s]}' for s in SEAS))
P('  Β ανα λιγκα (μεσος 4 folds): ' + ' · '.join(f'{lg} {np.mean([chB[(s, lg)] for s in SEAS]):.3f}' for lg in LGS))
P('  Γ (=αγορα) ανα λιγκα: ' + ' · '.join(f'{lg} {np.mean([chC[(s, lg)] for s in SEAS]):.3f}' for lg in LGS))
VAR = {'L live': np.ones(len(D)), 'A κοινο k': kA, 'B ανα λιγκα': kB, 'C =αγορα': kC}
# ---- ακριβεια ----
P('\n=== 1. ΑΚΡΙΒΕΙΑ (RPS ×1000, χαμηλοτερο = καλυτερο) ===')
WIN = np.where(D.md >= 14, '15+', np.where(D.md >= 6, '7-14', '1-6'))
RS = {}
for nm, kv in VAR.items():
    xh, xa = sk(kv); r = rps_v(probs(xh, xa)); RS[nm] = r
base = RS['L live']
P('  εκδοχη        ΟΛΑ    ' + '  '.join(SEAS) + '   | 1-6   7-14  15+   | καλυτερο απο live σε')
for nm, r in RS.items():
    per = [r[SEA == s].mean() * 1000 for s in SEAS]; w = sum(r[SEA == s].mean() < base[SEA == s].mean() for s in SEAS)
    P(f'  {nm:12s} {r.mean()*1000:7.3f} ' + ' '.join(f'{v:7.3f}' for v in per) + ' | ' + ' '.join(f'{r[WIN == w_].mean()*1000:6.2f}' for w_ in ('1-6', '7-14', '15+'))
      + (f' | {w}/4 σεζον · διαφορα {1000*(r.mean() - base.mean()):+.3f}' if nm != 'L live' else ''))
P('\n=== 2. ΕΔΡΑ: μεση υπεροχη γηπεδουχου (γκολ) — μοντελο vs αγορα vs πραγματικο ===')
mm = ~np.isnan(MK)
P(f'  πραγματικο {GD.mean():+.3f} · αγορα Pinnacle {np.nanmean(MK):+.3f} (στα ματς με αγορα· πραγμ εκει {GD[mm].mean():+.3f})')
for nm, kv in VAR.items():
    xh, xa = sk(kv); s = xh - xa
    P(f'  {nm:12s} μοντελο {s.mean():+.3f} · μοντ−πραγμ {s.mean() - GD.mean():+.3f} · ανα σεζον ' + ' '.join(f'{x}: {s[SEA == x].mean() - GD[SEA == x].mean():+.2f}' for x in SEAS)
      + ' · ανα λιγκα ' + ' '.join(f'{lg[:4]} {s[LGV == lg].mean() - GD[LGV == lg].mean():+.2f}' for lg in LGS))
P('  (πραγμ − αγορα ανα λιγκα: ' + ' '.join(f'{lg[:4]} {GD[mm & (LGV == lg)].mean() - MK[mm & (LGV == lg)].mean():+.2f}' for lg in LGS) + ')')
# ---- αγκυρα (offsets απο Pinnacle κλεισιμο προηγουμενων ματς) ----
def offsets(s_model):
    o_h = np.zeros(len(D)); o_a = np.zeros(len(D))
    for lg in LGS:
        idx = np.where(LGV == lg)[0]; idx = idx[np.argsort(D.date.values[idx], kind='stable')]
        off = {}; cur = None
        for i in idx:
            if SEA[i] != cur: off = {}; cur = SEA[i]
            h, a = D.h.values[i], D.a.values[i]; o_h[i], o_a[i] = off.get(h, 0.0), off.get(a, 0.0)
            if D.md.values[i] >= 6 and MK[i] == MK[i]:
                e = MK[i] - (s_model[i] + o_h[i] - o_a[i]); off[h] = off.get(h, 0.0) + .25 * e; off[a] = off.get(a, 0.0) - .25 * e
    return o_h, o_a
def quotes(i):
    r = D.iloc[i]; q = []
    if r.L == r.L: q.append(('Pinnacle', 'κλεισ', (r.L, r.ah, r.aa)))
    for bk in ('Crown', 'Bet365'):
        x = NG.get((r.mid, bk))
        if x: q += [(bk, 'κλεισ', x[1]), (bk, 'ανοιγ', x[0])]
    return q
def all_picks(kv):
    xh, xa = sk(kv); s0 = xh - xa; T = xh + xa; oh_, oa_ = offsets(s0); rows = []
    for i in range(len(D)):
        md = D.md.values[i]
        if md < 6: continue
        for bk, when, (L, h_o, a_o) in quotes(i):
            if not (L == L and h_o == h_o and a_o == a_o): continue
            line = float(L)
            if md >= 14:
                s = s0[i] + ((oh_[i] - oa_[i]) if abs(line) in (0.5, 0.75) else 0.0)
                for b in picks.evaluate_bet(max((T[i] + s) / 2, .05), max((T[i] - s) / 2, .05), line, h_o, a_o):
                    rows.append(dict(rule='dogs 15+', bk=bk, when=when, sea=SEA[i], home=b['side'] == 1, pnl=picks.settle(GD[i], b['side'], b['hcap'], b['odds'])))
                s = s0[i] + .7 * (oh_[i] - oa_[i])
                for b in picks.evaluate_fav(max((T[i] + s) / 2, .05), max((T[i] - s) / 2, .05), line, h_o, a_o):
                    rows.append(dict(rule='φαβ 15+', bk=bk, when=when, sea=SEA[i], home=b['side'] == 1, pnl=picks.settle(GD[i], b['side'], b['hcap'], b['odds'])))
            else:
                for b in picks.evaluate_bet(xh[i], xa[i], line, h_o, a_o):
                    rows.append(dict(rule='dogs 7-14', bk=bk, when=when, sea=SEA[i], home=b['side'] == 1, pnl=picks.settle(GD[i], b['side'], b['hcap'], b['odds'])))
                if abs(line) in (0.5, 0.75):
                    side = 1 if line < 0 else -1; o = h_o if side == 1 else a_o; ud = -abs(line)
                    if 1.70 <= o <= 2.10 and picks.fav_edge_q(xh[i], xa[i], side, ud, o) >= 0:
                        rows.append(dict(rule='κοντα φαβ 7-14', bk=bk, when=when, sea=SEA[i], home=side == 1, pnl=picks.settle(GD[i], side, ud, o)))
    return pd.DataFrame(rows)
PK = {}
for nm, kv in VAR.items():
    PK[nm] = all_picks(kv); print(f'  picks {nm} ok', flush=True)
def cell(d):
    if not len(d): return '      —           '
    ps = d.groupby('sea').pnl.mean()
    return f'n{len(d):4d} {100*d.pnl.mean():+6.1f}% {d.pnl.sum():+6.1f}u {int((ps > 0).sum())}/4'
RULES = ['dogs 15+', 'φαβ 15+', 'κοντα φαβ 7-14', 'dogs 7-14']
for when in ('κλεισ', 'ανοιγ'):
    P(f'\n=== 3. PICKS — {"ΚΛΕΙΣΙΜΟ" if when == "κλεισ" else "ΑΝΟΙΓΜΑ"} ===')
    for rule in RULES:
        P(f'  [{rule}]')
        for bk in (('Pinnacle', 'Crown', 'Bet365') if when == 'κλεισ' else ('Crown', 'Bet365')):
            P(f'    {bk:8s} ' + ' | '.join(f'{nm.split()[0]}: {cell(PK[nm][(PK[nm].rule == rule) & (PK[nm].bk == bk) & (PK[nm].when == when)])}' for nm in VAR))
P('\n=== 4. ΕΝΤΟΣ / ΕΚΤΟΣ (κλεισιμο, Pinnacle | Crown) ===')
for rule in RULES:
    for lab, hv in (('εντος', True), ('εκτος', False)):
        cells = []
        for nm in VAR:
            d = PK[nm]; cells.append(f'{nm.split()[0]}: ' + ' / '.join(f'{100*x.pnl.mean():+.1f}% n{len(x)}' if len(x) else '—' for x in
                                       [d[(d.rule == rule) & (d.bk == bk) & (d.when == 'κλεισ') & (d.home == hv)] for bk in ('Pinnacle', 'Crown')]))
        P(f'  {rule:15s} {lab}: ' + ' | '.join(cells))
# ---- ΚΡΙΣΗ ----
P('\n=== ΚΡΙΣΗ (προ-δηλωμενα) ===')
gd_live = abs(VAR and (sk(1.0)[0] - sk(1.0)[1]).mean() - GD.mean())
for nm in list(VAR)[1:]:
    r = RS[nm]; w = sum(r[SEA == s].mean() < base[SEA == s].mean() for s in SEAS); c1 = w >= 3 and r.mean() < base.mean()
    xh, xa = sk(VAR[nm]); c2 = abs((xh - xa).mean() - GD.mean()) < gd_live
    def units(d, rule, bk): return d[(d.rule == rule) & (d.bk == bk) & (d.when == 'κλεισ')].pnl.sum()
    c3 = all(units(PK[nm], 'dogs 15+', bk) >= units(PK['L live'], 'dogs 15+', bk) - 2 for bk in ('Pinnacle', 'Crown', 'Bet365'))
    tot = lambda d, bk: sum(units(d, rr, bk) for rr in ('dogs 15+', 'φαβ 15+', 'κοντα φαβ 7-14'))
    c4n = sum(tot(PK[nm], bk) >= tot(PK['L live'], bk) for bk in ('Pinnacle', 'Crown', 'Bet365')); c4 = c4n >= 2
    P(f'  {nm:12s} (1) RPS {w}/4, {1000*(r.mean()-base.mean()):+.3f} {"✓" if c1 else "✗"} · (2) εδρα {"✓" if c2 else "✗"} · (3) dogs 15+ ≥ live−2 σε 3 βιβλια {"✓" if c3 else "✗"} '
      f'· (4) 3 κανονες μαζι ≥ live σε {c4n}/3 {"✓" if c4 else "✗"} → {"ΠΕΡΝΑ" if c1 and c2 and c3 and c4 else "ΔΕΝ ΠΕΡΝΑ"}')
    P('       μοναδες 3 κανονων (Pin/Crown/B365): live ' + ' / '.join(f'{tot(PK["L live"], bk):+.1f}' for bk in ('Pinnacle', 'Crown', 'Bet365'))
      + f' → {nm.split()[0]} ' + ' / '.join(f'{tot(PK[nm], bk):+.1f}' for bk in ('Pinnacle', 'Crown', 'Bet365')))
open('core7_home_refit_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
