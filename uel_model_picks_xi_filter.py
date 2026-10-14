"""uel_model_picks_xi_filter.py — 14/10/2026 (Στελιος: «νομιζα οτι κραταει τα μπετς του μοντελου και βαζει ενα εξτρα φιλτρο για την ενδεκαδα —
αν ειναι κατω απο 85% κοβεται»). ΕΚΔΟΧΗ Γ: τα picks του ΜΟΝΤΕΛΟΥ στο Europa League (κανονες UEL: φαβ ≥4% σωστα τεταρτα · dog ≥10% p_cover ·
γραμμη ≥|0.5| · 1.70-2.10 · πρωτη εμφανιση ≤72ω · FotMob+FotMob) + ΦΙΛΤΡΟ ΕΝΔΕΚΑΔΑΣ:
  pick στο ΦΑΒΟΡΙ → περναει αν η ενδεκαδα του φαβορι ≥ τ · pick στον ΑΟΥΤΣΑΙΝΤΕΡ → περναει αν ο ΑΝΤΙΠΑΛΟΣ (φαβορι) κανει rotation (< τ) ή αν ειναι πληρης;
  (το δευτερο το δειχνω και ανα ενδεκαδα του αντιπαλου). Τιμη: στην ΕΙΣΟΔΟ του μοντελου και — ρεαλιστικα, αφου την ενδεκαδα την ξερουμε 1ω πριν —
  στην τιμη 1ω πριν (ιδια πλευρα, γραμμη 1ω). ΧΩΡΙΣ τα ματς του live κανονα «φαβορι εντος 12-36ω».
"""
import sys
src = open('uel_lineup_rule2.py', encoding='utf-8').read().split('# ---------- φαβορι αγορας με την τιμη 1ω')[0]
exec(src)
HS = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
rows = []
for i in range(len(MIDS)):
    if COMP[i] != 'EuropaLeague' or SRCC[i] != 'FF' or LH_N[i] <= 0: continue
    j = VI.get(str(MIDS[i]))
    if j is None: continue
    ko = pd.Timestamp(V6['date'][j]); rh, ra = ratio(MIDS[i], 'h', ko), ratio(MIDS[i], 'a', ko)
    D = sdist(LH_N[i], LA_N[i])
    for bk in ('Crown', 'SBOBET'):
        got = set()
        for h in HS:
            s = snap_ah(MIDS[i], bk, h)
            if not s: continue
            L, oh, oa = s
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if side in got or not (1.70 <= o <= 2.10): continue
                if ln <= -0.5: pw, pp = cover_q(D, side, ln); th = .04; kind = 'φαβορι'
                elif ln >= 0.5: pw, pp = picks.p_cover(D, side, ln); th = .10; kind = 'αουτσαιντερ'
                else: continue
                if edge(pw, pp, o) < th: continue
                got.add(side)
                if kind == 'φαβορι' and side == 1 and (i, bk) in HF: continue
                s1 = snap_ah(MIDS[i], bk, 1); p1 = np.nan
                if s1:
                    L1, a1, b1 = s1; l1 = L1 if side == 1 else -L1; o1 = a1 if side == 1 else b1
                    if 1.70 <= o1 <= 2.10: p1 = picks.settle(GD[i], side, l1, o1)
                own = rh if side == 1 else ra; opp = ra if side == 1 else rh
                rows.append(dict(sea=SEA[i], bk=bk, kind=kind, h=h, own=own, opp=opp, pnl=picks.settle(GD[i], side, ln, o), p1=p1))
P = pd.DataFrame(rows)
def cc(x, col='pnl'):
    x = x.dropna(subset=[col])
    if len(x) < 6: return f'n{len(x) / 2:3.0f} (λιγα)'
    m = x.groupby('bk')[col].mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea')[col].mean()
    return f'{n:4.0f} picks {100 * m.mean():+6.1f}% (' + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')'
print('EUROPA LEAGUE — picks ΜΟΝΤΕΛΟΥ (χωρις τα «φαβορι εντος 12-36ω») + φιλτρο ενδεκαδας · τιμη ΕΙΣΟΔΟΥ μοντελου | τιμη 1ω πριν (οταν ξερουμε την ενδεκαδα)')
for kind in ('φαβορι', 'αουτσαιντερ'):
    x = P[P.kind == kind]; col = 'own' if kind == 'φαβορι' else 'opp'
    who = 'του φαβορι (η ομαδα μας)' if kind == 'φαβορι' else 'του ΑΝΤΙΠΑΛΟΥ φαβορι'
    print(f'\n  {kind.upper()} — ενδεκαδα {who}:')
    print(f'     ολα (χωρις φιλτρο)          εισοδος {cc(x)} | 1ω {cc(x, "p1")}')
    print(f'     ενδεκαδα αγνωστη            εισοδος {cc(x[x[col].isna()])}')
    for lo, hi, l in ((0, .85, '<85% (rotation)'), (.85, 1.0, '85-100%'), (1.0, 9, '≥100% (πληρης)')):
        y = x[(x[col] >= lo) & (x[col] < hi)]
        print(f'     {l:28s} εισοδος {cc(y)} | 1ω {cc(y, "p1")}')
