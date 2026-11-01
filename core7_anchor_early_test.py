"""
core7_anchor_early_test.py — 9/10/2026 (Στελιος: «αγκυρα αγορας εχουμε τεσταρει; αν υπερτιμαμε/υποτιμαμε μια ομαδα θα μας γλιτωνε απο κακα μπετς;»).
ΑΓΚΥΡΑ ΑΓΟΡΑΣ ΠΟΥ ΜΑΘΑΙΝΕΙ ΑΠΟ ΝΩΡΙΣ, εφαρμοσμενη στις αγων 6-14 (live σημερα: μαθαινει απο 7η, εφαρμοζεται 15η+ μονο κοντες).
Μηχανισμος (ιδιος με core7_anchor): καθε ομαδα διορθωση o=0 στην αρχη· για καθε ματς με σειρα: s = s_μοντελου + o_h − o_a·
αν αγωνιστικη ≥ Lmin: e = s_αγορας − s, o_h += λe/2, o_a −= λe/2. Αγορα = Pinnacle κλεισιμο (7+), Crown-αντιστροφη (1-6).
Εκδοχες: λ ∈ {0.25, 0.5, 1.0} × μαθηση απο αγων {1, 4}. Χρησεις στις 6-14:
  (Α) ΑΝΤΙΚΑΤΑΣΤΑΣΗ: picks με την αγκυρωμενη υπεροχη (dogs + κοντα φαβορι).
  (Β) ΦΙΛΤΡΟ/ΣΥΝΑΙΝΕΣΗ: κραταω ενα live pick μονο αν και η αγκυρωμενη εκδοχη δινει ιδιο pick (edge ≥ κατωφλι κανονα).
ΠΡΟ-ΔΗΛΩΣΗ: εκδοχη επιλεγεται LOSO (μεγιστες μοναδες στις 3 σεζον)· περνα αν LOSO ROI (μεσος 3 βιβλιων) > σημερα σε ≥3/4 σεζον,
θετικο συνολο, καλυτερο σε ≥2/3 βιβλια. (Β) επιπλεον: τα κομμενα αρνητικα σε ≥3/4 σεζον.
"""
import sys, io, contextlib, itertools
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('core7_early_weakness.py', encoding='utf-8').read()
src = src[:src.index('# ---- PICKS')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'ae'}
exec(src, g)
M, picks = g['M'], g['picks']
M = M.copy(); M['date'] = pd.to_datetime(M.date)
def anchored(lam, lmin):
    S = pd.Series(np.nan, index=M.index)
    for (lg, se), d in M.sort_values('date').groupby(['league', 'season']):
        o = {}
        for mid, r in d.iterrows():
            s = r.s_mod + o.get(r.home, 0.0) - o.get(r.away, 0.0); S[mid] = s
            if r.md >= lmin and r.s_m == r.s_m:
                e = r.s_m - s; o[r.home] = o.get(r.home, 0.0) + lam * e / 2; o[r.away] = o.get(r.away, 0.0) - lam * e / 2
    return S
VAR = {'LIVE': M.s_mod}
for lam, lmin in itertools.product((0.25, 0.5, 1.0), (0, 3)):
    VAR[f'λ{lam}/απο {lmin + 1}η'] = anchored(lam, lmin)
W = M[M.md.between(5, 13)]
def picks_for(sv):
    rows = []
    for mid, r in W.iterrows():
        sp = sv[mid]; T = r['T']; xh_, xa_ = max((T + sp) / 2, .05), max((T - sp) / 2, .05)
        for bk, (L, oh, oa) in (('Pinnacle', (r.pin_L, r.pin_ah, r.pin_aa)), ('Crown', (r.cr_L, r.cr_oh, r.cr_oa)), ('Bet365', (r.b3_L, r.b3_oh, r.b3_oa))):
            if not (L == L and oh == oh): continue
            for b in picks.evaluate_bet(xh_, xa_, L, oh, oa):
                rows.append(dict(mid=mid, book=bk, season=r.season, role='dog', side=b['side'], pnl=picks.settle(r.gd, b['side'], b['hcap'], b['odds'])))
            if r.md >= 6 and abs(L) in (0.5, 0.75):
                side = 1 if L < 0 else -1; o = oh if side == 1 else oa
                if 1.70 <= o <= 2.10 and picks.fav_edge_q(xh_, xa_, side, -abs(L), o) >= 0:
                    rows.append(dict(mid=mid, book=bk, season=r.season, role='fav', side=side, pnl=picks.settle(r.gd, side, -abs(L), o)))
    return pd.DataFrame(rows)
PK = {k: picks_for(v) for k, v in VAR.items()}
def fm(d):
    if len(d) < 6: return f'n{len(d) / 3:5.0f}' + ' ' * 34
    ps = d.groupby('season').pnl.mean(); pb = d.groupby('book').pnl.mean()
    return f'n{len(d) / d.book.nunique():5.0f} {100 * d.pnl.mean():+6.1f}% {d.pnl.sum() / d.book.nunique():+6.1f}u σεζ {int((ps > 0).sum())}/{ps.size} βιβλ {int((pb > 0).sum())}/{pb.size}'
# ακριβεια: RMSE vs πραγματικο στις 6-14
A = W[W.s_m.notna()]
print('ΑΚΡΙΒΕΙΑ αγων 6-14 (RMSE πραγματικο − υπεροχη· αγορα = ' + f'{np.sqrt(np.mean((A.gd - A.s_m) ** 2)):.4f})')
for k, v in VAR.items():
    e = A.gd - v[A.index]; ps = (e ** 2).groupby(A.season).mean() ** .5
    print(f'   {k:16s} {np.sqrt(np.mean(e ** 2)):.4f} · ανα σεζον ' + ' '.join(f'{x:.3f}' for x in ps.values) + f' · |διαφορα απο αγορα| {(v[A.index] - A.s_m).abs().mean():.2f}')
print('\n(Α) ΑΝΤΙΚΑΤΑΣΤΑΣΗ — picks αγων 6-14 με την αγκυρωμενη υπεροχη (ΟΛΑ = dogs + κοντα φαβορι)')
for k, P in PK.items():
    print(f'   {k:16s} ΟΛΑ {fm(P)} · dogs {fm(P[P.role == "dog"])[:30]} · φαβ {fm(P[P.role == "fav"])[:30]}')
# (Β) συναινεση: live pick που υπαρχει και στην εκδοχη
L0 = PK['LIVE']; key = lambda d: set(zip(d.mid, d.book, d.role, d.side))
print('\n(Β) ΦΙΛΤΡΟ — κραταω live pick μονο αν το δινει ΚΑΙ η αγκυρωμενη εκδοχη · κομμενα = όσα η αγκυρα «διαφωνει»')
CONS = {}
for k, P in PK.items():
    if k == 'LIVE': continue
    ks = key(P); m_ = np.array([t in ks for t in zip(L0.mid, L0.book, L0.role, L0.side)])
    CONS[k] = (L0[m_], L0[~m_]); print(f'   {k:16s} μενουν {fm(L0[m_])} · κομμενα {fm(L0[~m_])}')
print(f'   σημερα (LIVE) {fm(L0)}')
def loso(cands, label):
    res = []
    for te in sorted(L0.season.unique()):
        best = max(cands, key=lambda k: cands[k][cands[k].season != te].pnl.sum())
        res.append(cands[best][cands[best].season == te].assign(pick=best)); print(f'     εκτος {te}: {best} → {fm(cands[best][cands[best].season == te])}')
    R = pd.concat(res); ps = R.groupby('season').pnl.mean(); pl = L0.groupby('season').pnl.mean()
    pb = R.groupby('book').pnl.mean(); plb = L0.groupby('book').pnl.mean()
    ok = int((ps > pl.reindex(ps.index)).sum()) >= 3 and R.pnl.mean() > 0 and int((pb > plb.reindex(pb.index)).sum()) >= 2
    print(f'   LOSO {label}: {fm(R)} vs σημερα {fm(L0)} → {"ΠΕΡΝΑ" if ok else "ΔΕΝ ΠΕΡΝΑ"}'); return R
print('\nΚΡΙΣΗ (LOSO)')
loso({k: v for k, v in PK.items() if k != 'LIVE'}, '(Α) αντικατασταση')
R = loso({k: v[0] for k, v in CONS.items()}, '(Β) φιλτρο')
cut = pd.concat([CONS[k][1][CONS[k][1].season == s_] for s_, k in R.groupby('season').pick.first().items()])
pc = cut.groupby('season').pnl.mean()
print(f'   (Β) κομμενα LOSO {fm(cut)} → αρνητικα σε {int((pc < 0).sum())}/{pc.size} σεζον')
