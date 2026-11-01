"""uel_fix_cut_picks.py — 15/10/2026 (Στελιος: «δειξε μου ποια σημεια κοπηκαν/διορθωθηκαν συγκεκριμενα — τα ματς, τι προβλεψη ειχαν πριν και τι μετα —
και αναλυσε ποιες ομαδες διορθωσε και γιατι, τι ειδους ομαδες υπερεκτιμουσε το μοντελο και πως το Elo τις διορθωσε»).
Europa League κατηγορια Α 2223-2526, Crown (αλλιως SBOBET), κανονες picks UEL (φαβ ≥4% σωστα τεταρτα ≤−0.5 · dog ≥10% p_cover ≥+0.5 · 1.70-2.10 ·
πρωτη εμφανιση ≤72ω χωρις τελευταια τιμη) με ΣΗΜΕΡΙΝΟ (Μ) και ΔΙΟΡΘΩΜΕΝΟ (ΒΕ: τεντωμα + λιγο Elo, παραμετροι LOSO οπως euro_fix_threshold_timing).
Για καθε ματς: διαφορα γκολ (σκοπια γηπεδουχου) σημερινο → μετα το κομματι «δυναμη ομαδας» → μετα «διαφορα λιγκας» → μετα Elo (= διορθωμενο),
αγορα, πραγματικο, xG · ομαδες: λιγκα, εγχωρια κυριαρχια t, Elo.
"""
import sys
exec(open('euro_fix_threshold_timing.py', encoding='utf-8').read().split("for cm in COMP_ONLY:")[0])
NL = chr(10)
cm = 'EuropaLeague'
x = A[A.comp == cm].reset_index(drop=True); seas = sorted(x.sea.unique())
P = {}
for s in seas:
    te = (x.sea == s).values; P[s] = fitV(x[~te], 'BE')
print('Παραμετροι διορθωσης (απο τις αλλες 3 σεζον): ' + ' · '.join(f'{s}: δυναμη ομαδας {P[s][0]:+.2f} · διαφορα λιγκας {P[s][1]:+.2f} · βαρος Elo {P[s][2]:.2f}' for s in seas))
# βηματα διορθωσης ανα ματς
rows = []
for k_, r in x.iterrows():
    bt, bD, w, h, k, c = P[r.sea]
    zt = bt * r['dt'] / 2; zl = bD * r['D']
    lh1, la1 = r.lh * np.exp(zt), r.la * np.exp(-zt)                       # μονο δυναμη ομαδας
    lh2, la2 = r.lh * np.exp(zt + zl), r.la * np.exp(-zt - zl)             # + διαφορα λιγκας
    T = lh2 + la2; me = h + k * r.de
    m3 = (1 - w) * (lh2 - la2) + w * me                                   # + Elo
    lh3, la3 = max((T + m3) / 2, .05), max((T - m3) / 2, .05)
    rows.append(dict(k=k_, m0=r.lh - r.la, m1=lh1 - la1, m2=lh2 - la2, m3=lh3 - la3, melo=me, lh3=lh3, la3=la3))
Z = pd.DataFrame(rows).set_index('k'); x = x.join(Z)
NM = {}; ELO = {}
for mid in x.i:
    m = EUM.get(str(MIDS[int(mid)]))
    if m: NM[int(mid)] = (m['home']['name'], m['away']['name'])
CPm = {int(r.i): CP[str(MIDS[int(r.i)])] for r in x.itertuples()}
def first_pick(i, lh, la):
    D_ = sdist(lh, la); mid = str(MIDS[i]); out = {}
    for bk in ('Crown', 'SBOBET'):
        for h_ in [hh for hh in HS if hh > 0]:
            s = snapT(mid, bk, h_)
            if not s: continue
            L, oh, oa = s
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if side in out or not (1.70 <= o <= 2.10): continue
                if ln <= -0.5: f = cover_q; th = .04; kind = 'φαβ'
                elif ln >= 0.5: f = picks.p_cover; th = .10; kind = 'dog'
                else: continue
                e = edge(*f(D_, side, ln), o)
                if e >= th: out[side] = dict(kind=kind, ln=ln, o=o, e=e, h=h_, mk=implied_margin(i, L, oh, oa), pnl=picks.settle(GD[i], side, ln, o))
        if out: return bk, out
    return None, {}
xa_ = x[x.cat == 'A']
REC = []
for r in xa_.itertuples():
    i = int(r.i)
    b0, p0 = first_pick(i, r.lh, r.la); b1, p1 = first_pick(i, r.lh3, r.la3)
    for side in set(p0) | set(p1):
        a, b = p0.get(side), p1.get(side)
        status = 'ΚΡΑΤΗΘΗΚΕ' if a and b else ('ΚΟΠΗΚΕ' if a else 'ΠΡΟΣΤΕΘΗΚΕ')
        pk = a or b; c_ = CPm[i]; hn, an = NM.get(i, ('?', '?'))
        team = hn if side == 1 else an; opp = an if side == 1 else hn
        REC.append(dict(status=status, sea=r.sea, home=hn, away=an, team=team, opp=opp, side=side, kind=pk['kind'], venue='εντος' if side == 1 else 'εκτος',
                        ln=pk['ln'], o=pk['o'], e0=a['e'] if a else np.nan, e1=b['e'] if b else np.nan, pnl=pk['pnl'],
                        m0=side * r.m0, m1=side * r.m1, m2=side * r.m2, m3=side * r.m3, mk=side * pk['mk'], gd=side * GD[i],
                        xg=side * (r.lvl if np.isfinite(r.lvl) else np.nan), lg_t=r.lgh if side == 1 else r.lga, lg_o=r.lga if side == 1 else r.lgh,
                        t_t=r.th if side == 1 else r.ta, t_o=r.ta if side == 1 else r.th,
                        el_t=c_['elh'] if side == 1 else c_['ela'], el_o=c_['ela'] if side == 1 else c_['elh'], melo=side * r.melo))
Rr = pd.DataFrame(REC)
def summ(y, lab):
    if len(y) == 0: print(f'   {lab}: κανενα'); return
    print(f'   {lab:12s} {len(y):3d} picks · ROI {100 * y.pnl.mean():+6.1f}% · μονάδες {y.pnl.sum():+5.1f} · (φαβ {(y.kind == "φαβ").sum()} / dog {(y.kind == "dog").sum()} · εκτος {(y.venue == "εκτος").sum()})')
print(f'{NL}ΣΥΝΟΨΗ (ενα βιβλιο ανα ματς):')
for st in ('ΚΟΠΗΚΕ', 'ΚΡΑΤΗΘΗΚΕ', 'ΠΡΟΣΤΕΘΗΚΕ'): summ(Rr[Rr.status == st], st)
summ(Rr[Rr.status != 'ΠΡΟΣΤΕΘΗΚΕ'], 'ΣΗΜΕΡΙΝΟ ολα'); summ(Rr[Rr.status != 'ΚΟΠΗΚΕ'], 'ΔΙΟΡΘ. ολα')
def show(y, title):
    print(f'{NL}{title} — διαφορα γκολ υπερ της ομαδας του pick: σημερινο → −δυναμη ομαδας → −διαφορα λιγκας → +Elo (=διορθωμενο) │ αγορα │ πραγμ.')
    for r in y.sort_values(['kind', 'sea']).itertuples():
        print(f'   {r.sea} {r.home[:18]:18s}-{r.away[:18]:18s} │ {r.kind} {r.venue} {r.team[:16]:16s} {r.ln:+.2f}@{r.o:.2f} │ '
              f'{r.m0:+.2f} → {r.m1:+.2f} → {r.m2:+.2f} → {r.m3:+.2f} │ αγ {r.mk:+.2f} │ {int(r.gd):+d} ({r.pnl:+.2f}) │ '
              f'{r.lg_t[:12]} t{r.t_t:+.2f} Elo{r.el_t:.0f} vs {r.lg_o[:12]} t{r.t_o:+.2f} Elo{r.el_o:.0f}')
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
show(Rr[Rr.status == 'ΚΟΠΗΚΕ'], 'ΚΟΠΗΚΑΝ')
show(Rr[Rr.status == 'ΠΡΟΣΤΕΘΗΚΑΝ'.replace('ΚΑΝ', 'ΚΕ')], 'ΠΡΟΣΤΕΘΗΚΑΝ')
print(f'{NL}ΤΙ ΕΙΔΟΥΣ ΟΜΑΔΕΣ ΚΟΠΗΚΑΝ (η ομαδα του pick):')
C_ = Rr[Rr.status == 'ΚΟΠΗΚΕ']; K_ = Rr[Rr.status == 'ΚΡΑΤΗΘΗΚΕ']
for lab, f in (('ομαδα του pick εκτος top-5', lambda y: ~y.lg_t.isin(TOP5)), ('ομαδα του pick ΠΟΛΥ κυριαρχη εκτος top-5 (t≥0.9)', lambda y: ~y.lg_t.isin(TOP5) & (y.t_t >= .9)),
               ('αντιπαλος top-5', lambda y: y.lg_o.isin(TOP5)), ('pick εκτος εδρας', lambda y: y.venue == 'εκτος'), ('αουτσαιντερ', lambda y: y.kind == 'dog')):
    print(f'   {lab:52s} κοπηκαν {100 * f(C_).mean():3.0f}% · κρατηθηκαν {100 * f(K_).mean():3.0f}%')
print(f'   μεση πτωση διαφορας στα κομμενα: απο δυναμη ομαδας {(C_.m1 - C_.m0).mean():+.2f} · απο διαφορα λιγκας {(C_.m2 - C_.m1).mean():+.2f} · απο Elo {(C_.m3 - C_.m2).mean():+.2f}'
      f' │ μοντελο {C_.m0.mean():+.2f} → {C_.m3.mean():+.2f} · αγορα {C_.mk.mean():+.2f} · πραγματικο {C_.gd.mean():+.2f}')
Rr.to_csv('uel_fix_cut_picks.csv', index=False, encoding='utf-8-sig')
