# -*- coding: utf-8 -*-
"""nba_filters_test.py — NBA ΦΙΛΤΡΑ ΑΠΟΦΥΓΗΣ (28/9/2026, προταση Στελιου): tanking · τελευταια 10 ματς · πολλες απουσιες.
Picks: μοντελο «ομαδες + κουραση/ταξιδι/κινητρο» (LOSO) και «μοντελο ομαδων», edge ≥5/8%, τιμες Crown (κλεισιμο ΚΑΙ 09:00 ΝΥ).
Ορισμοι (γνωστα πριν το ματς):
  TANK  = ≥50 ματς & ≥6 νικες πισω απο 10η θεση περιφερειας (ιδιο με nba_gap_fatigue_test) · TANK2 = 4 χειροτερα ρεκορ λιγκας μετα απο ≥40 ματς
  LAST10 = μια απο τις δυο εχει ≤10 ματς ακομα
  ΑΠΟΥΣΙΕΣ = ποσοι απο τους 5 με τα περισσοτερα λεπτα στα τελευταια 10 ματς της ομαδας ΔΕΝ επαιξαν (γνωστο ~30′ πριν → ρεαλιστικο
             μονο για bets κοντα στο κλεισιμο· στις 09:00 = με εκ των υστερων γνωση)
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ:
  Φιλτρο ΠΕΡΝΑ αν: ROI των picks που αφαιρει < ROI αυτων που μενουν σε ≥4/5 σεζον ΚΑΙ το ROI που μενει ανεβαινει συνολικα.
  «Κοντρα» ΠΕΡΝΑ αν: ROI > 0 σε ≥4/5 σεζον ΚΑΙ t ≥ 2.
Εξοδος: nba_filters_test_out.txt"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('nba_smart_money_match.py', encoding='utf-8').read().split("for t, nm, mods, YY in ((21,")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out.clear()
n = len(G)
# ---- TANK2 & LAST10 ----
tank2 = np.zeros((n, 2), bool); last10 = np.zeros(n, bool); gleft = np.zeros((n, 2))
for s, gs in G.groupby('season', sort=True):
    tot = pd.concat([gs.home, gs.away]).value_counts().to_dict(); rec = {}
    for d, blk in gs.groupby('date', sort=True):
        order = sorted(tot, key=lambda t: rec.get(t, [0, 0])[0] / max(1, sum(rec.get(t, [0, 0]))))
        worst4 = set(order[:4])
        for i, r in blk.iterrows():
            for k, t in enumerate((r.home, r.away)):
                gp = sum(rec.get(t, [0, 0])); gleft[i, k] = tot[t] - gp
                tank2[i, k] = gp >= 40 and t in worst4
            last10[i] = min(gleft[i]) <= 10
        for i, r in blk.iterrows():
            hw = r.hs > r.as_
            for t, w in ((r.home, hw), (r.away, not hw)):
                rr = rec.setdefault(t, [0, 0]); rr[0 if w else 1] += 1
TANK = np.column_stack([FT['h_tank'], FT['a_tank']]).astype(bool)
# ---- ΑΠΟΥΣΙΕΣ βασικων ----
played = A.groupby(['gi', 'team']).apply(lambda x: dict(zip(x.PLAYER_ID, x.MIN))).to_dict()
miss = np.zeros((n, 2)); hist = {}
for i, r in G.iterrows():
    for k, t in enumerate((r.home, r.away)):
        H = hist.setdefault((r.season, t), [])
        cur = played.get((i, t), {})
        if len(H) >= 5:
            agg = {}
            for dct in H[-10:]:
                for p, mn in dct.items(): agg[p] = agg.get(p, 0) + mn
            top5 = sorted(agg, key=agg.get, reverse=True)[:5]
            miss[i, k] = sum(1 for p in top5 if p not in cur)
        else:
            miss[i, k] = np.nan
        H.append(cur)
MISSX = np.nanmax(miss, axis=1)
EVS = set(EV)
P(f'συχνοτητα (σεζον-τεστ): TANK {TANK[np.isin(G.season, EV)].any(1).mean():.1%} των ματς · TANK2 {tank2[np.isin(G.season, EV)].any(1).mean():.1%} · '
  f'LAST10 {last10[np.isin(G.season, EV)].mean():.1%} · απουσιες ≥2 {np.mean(MISSX[np.isin(G.season, EV)] >= 2):.1%} · ≥3 {np.mean(MISSX[np.isin(G.season, EV)] >= 3):.1%}')
# η αγορα σε αυτα τα ματς
mmk = np.isin(SE, EV)
for lab, msk in (('ολα', np.ones(n, bool)), ('απουσιες ≥3', MISSX >= 3), ('απουσιες ≥2', MISSX >= 2), ('LAST10', last10), ('TANK', TANK.any(1))):
    k = mmk & msk[IDX]
    P(f'  αγορα (κλεισιμο) σε «{lab}»: {k.sum()} ματς · RMSE {np.sqrt(np.mean((ACT - MM)[k] ** 2)):.2f} · μεση (πραγμ − αγορα) {np.mean((ACT - MM)[k]):+.2f}')
P('')

def picks(m, when, thr):
    rows = []
    for j, i in enumerate(IDX):
        if SE[j] not in EVS: continue
        if when == 'close':
            r = MK[i]; row = (None, None, r['L'], r['oh'], r['oa'])
        else:
            if i not in REC[21]: continue
            s = snap(21, i)
            if not s: continue
            row = s[0]
        side, e, od = edge_pick(21, m[i], row)
        if e < thr: continue
        v = (ACTG[i] + row[2]) * side
        rows.append(dict(i=i, season=G.season[i], side=side, p=(od - 1) if v > 0 else (0 if v == 0 else -1)))
    return pd.DataFrame(rows)
def verdict(D, rm):
    kept, rem = D[~rm], D[rm]
    wins = sum(1 for s in EV if len(rem[rem.season == s]) and rem[rem.season == s].p.mean() < kept[kept.season == s].p.mean())
    ok = wins >= 4 and kept.p.mean() > D.p.mean()
    return (f'αφαιρει {rm.sum()} ({rm.mean():.0%}) ROI {rem.p.mean()*100:+.1f}% · μενουν ROI {kept.p.mean()*100:+.1f}% (ηταν {D.p.mean()*100:+.1f}%) · '
            f'χειροτερα σε {wins}/{len(EV)} → {"ΠΕΡΝΑ" if ok else "✗"}')
for mn in ('ομαδες + κουραση/ταξιδι/κινητρο', 'μοντελο ομαδων'):
    m = MODS[mn]
    for when, wl in (('close', 'τιμη ΚΛΕΙΣΙΜΑΤΟΣ'), ('09', 'τιμη 09:00 ΝΥ')):
        for thr in (0.05, 0.08):
            D = picks(m, when, thr)
            if not len(D): continue
            ii = D.i.values; side = D.side.values
            P(f'=== {mn} · {wl} · edge ≥{thr*100:.0f}%: {len(D)} picks · ROI {D.p.mean()*100:+.1f}% ===')
            P(f'  TANK (οποιαδηποτε)            {verdict(D, TANK[ii].any(1))}')
            onT = np.where(side == 1, TANK[ii, 0], TANK[ii, 1]); agT = np.where(side == 1, TANK[ii, 1], TANK[ii, 0])
            P(f'    ΜΕ την ομαδα tanking         {verdict(D, onT)}')
            P(f'    ΚΟΝΤΡΑ στην ομαδα tanking    {verdict(D, agT)}')
            P(f'  TANK2 (4 χειροτεροι)          {verdict(D, tank2[ii].any(1))}')
            P(f'  LAST10                        {verdict(D, last10[ii])}')
            P(f'  απουσιες ≥3 {"(εκ των υστερων!)" if when == "09" else "":17s} {verdict(D, MISSX[ii] >= 3)}')
            P(f'  απουσιες ≥2 {"(εκ των υστερων!)" if when == "09" else "":17s} {verdict(D, MISSX[ii] >= 2)}')
            P(f'  ΟΛΑ ΜΑΖΙ (TANK/LAST10/απ.≥3)  {verdict(D, TANK[ii].any(1) | last10[ii] | (MISSX[ii] >= 3))}')
            P('')
# ---- ΚΟΝΤΡΑ στο tanking, στα τυφλα (κλεισιμο) ----
P('=== «ΚΟΝΤΡΑ ΣΤΟ TANKING» στα τυφλα — τιμη κλεισιματος, χαντικαπ ===')
def blind(mask_side, lab, restrict=None):
    rows = []
    for j, i in enumerate(IDX):
        if SE[j] not in EVS: continue
        sd = mask_side(i)
        if sd == 0: continue
        if restrict is not None and not restrict(i, sd): continue
        r = MK[i]; od = r['oh'] if sd == 1 else r['oa']; v = (ACTG[i] + r['L']) * sd
        rows.append(dict(season=G.season[i], p=(od - 1) if v > 0 else (0 if v == 0 else -1)))
    D = pd.DataFrame(rows)
    if not len(D): P(f'  {lab}: 0'); return
    per = D.groupby('season').p.mean(); t = D.p.mean() / (D.p.std() / np.sqrt(len(D)))
    ok = (per > 0).sum() >= 4 and t >= 2
    P(f'  {lab:52s} {len(D):5d} bets · ROI {D.p.mean()*100:+.1f}% (t {t:+.1f}) · ' + ' '.join(f'{s}:{v*100:+.0f}%' for s, v in per.items()) +
      f' → {"ΠΕΡΝΑ" if ok else "✗"}')
for Tn, TT in (('TANK', TANK), ('TANK2', tank2)):
    against = lambda i, TT=TT: (-1 if TT[i, 0] and not TT[i, 1] else (1 if TT[i, 1] and not TT[i, 0] else 0))
    blind(against, f'κοντρα σε {Tn} (ολα)')
    blind(lambda i, TT=TT: (-1 if TT[i, 0] and not TT[i, 1] else 0), f'κοντρα σε {Tn} γηπεδουχο (παιζουμε φιλοξ.)')
    blind(lambda i, TT=TT: (1 if TT[i, 1] and not TT[i, 0] else 0), f'κοντρα σε {Tn} φιλοξενουμενη (παιζουμε γηπ.)')
    blind(lambda i, TT=TT: (1 if TT[i, 0] and not TT[i, 1] else (-1 if TT[i, 1] and not TT[i, 0] else 0)), f'ΜΕ την {Tn} (αντιστροφο)')
    mm_ = MODS['ομαδες + κουραση/ταξιδι/κινητρο']
    blind(against, f'κοντρα σε {Tn} ΚΑΙ το μοντελο συμφωνει (edge>0)',
          restrict=lambda i, sd, mm_=mm_: edge_pick(21, mm_[i], (None, None, MK[i]['L'], MK[i]['oh'], MK[i]['oa']))[0] == sd)
    blind(against, f'κοντρα σε {Tn} ΜΟΝΟ τα τελευταια 10 ματς', restrict=lambda i, sd: last10[i])
open('nba_filters_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
