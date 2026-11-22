"""uel_elo_why.py — 15/10/2026 (Στελιος: «για ποιο λογο ακριβως η μιξη Elo χαλαει τα φαβορι και βελτιωνει τα αουτσαιντερ; γιατι μειωνει τη χασουρα
στα αουτσαιντερ εκτος και βελτιωνει πολυ τα αουτσαιντερ εντος;»).
Europa κατηγορια Α (ιδια δεδομενα/παραμετροι με uel_elo_by_market). Απο τη σκοπια του ΓΗΠΕΔΟΥΧΟΥ, ανα τυπο ματς (κατα την αγορα στο κλεισιμο):
διαφορα ΣΗΜΕΡΙΝΟΥ / ΜΙΞΗΣ Elo / ΜΟΝΟ Elo / ΑΓΟΡΑΣ / πραγματικη (γκολ) — και ποσο απλωμενες ειναι οι διαφορες (τυπ. αποκλιση).
"""
import sys
src = open('uel_elo_by_market.py', encoding='utf-8').read().split("PK = {v: picks_for(v) for v in ('M', 'E')}")[0]
exec(src)
PE = {}
for s in seas:
    te = (x.sea == s).values; PE[s] = fit(x[~te], False, True)
h_, k_, w_ = np.mean([PE[s][0] for s in seas]), np.mean([PE[s][1] for s in seas]), np.mean([PE[s][2] for s in seas])
x['mM'] = LV['M'][0] - LV['M'][1]; x['mE'] = LV['E'][0] - LV['E'][1]
x['mElo'] = [PE[s][0] + PE[s][1] * d for s, d in zip(x.sea, x.de)]
x['mk'] = mk_all
y = x[(x.cat == 'A') & x.mk.notna()].copy()
print(f'Europa Α: {len(y)} ματς · μεσες παραμετροι μιξης: βαρος Elo w {w_:.2f} · Elo κλιση k {k_:.2f} γκολ ανα 100 Elo · εδρα στο Elo h {h_:.2f}')
print(f'   ΑΠΛΩΜΑ διαφορων (τυπ. αποκλιση): σημερινο {y.mM.std():.2f} · μονο Elo {y.mElo.std():.2f} · μιξη {y.mE.std():.2f} · αγορα {y.mk.std():.2f} · (πραγματικα γκολ {y.gd.std():.2f})')
print(f'   ΕΔΡΑ (μεση διαφορα γηπεδουχου): σημερινο {y.mM.mean():+.2f} · μονο Elo {y.mElo.mean():+.2f} · μιξη {y.mE.mean():+.2f} · αγορα {y.mk.mean():+.2f} · '
      f'πραγματικο {y.gd.mean():+.2f} · xG ισοπ./90 {np.average(y.lvl[y.lw > .2], weights=y.lw[y.lw > .2]):+.2f}')
print('\nΑΝΑ ΤΥΠΟ ΜΑΤΣ (κατα την αγορα) — διαφορα απο τη σκοπια του γηπεδουχου')
G = (('ΜΕΓΑΛΟ φαβορι εντος (αγορα ≥ +1.0)', y.mk >= 1.0), ('φαβορι εντος (+0.4…+1.0)', (y.mk >= .4) & (y.mk < 1.0)), ('ισορροπημενα (−0.4…+0.4)', y.mk.abs() < .4),
     ('φαβορι εκτος (−1.0…−0.4)', (y.mk <= -.4) & (y.mk > -1.0)), ('ΜΕΓΑΛΟ φαβορι εκτος (αγορα ≤ −1.0)', y.mk <= -1.0))
for lab, m_ in G:
    z = y[m_]
    print(f'   {lab:36s} n{len(z):3d} · σημερινο {z.mM.mean():+.2f} · μιξη {z.mE.mean():+.2f} · μονο Elo {z.mElo.mean():+.2f} · ΑΓΟΡΑ {z.mk.mean():+.2f} · '
          f'πραγμ. {z.gd.mean():+.2f} │ σημερινο−αγορα {(z.mM - z.mk).mean():+.2f} → μιξη−αγορα {(z.mE - z.mk).mean():+.2f}')
print('\nΠΟΥ ΔΙΑΦΩΝΕΙ ΤΟ Elo ΜΕ ΤΟ ΜΟΝΤΕΛΟ (μιξη − σημερινο, σκοπια γηπεδουχου) ανα δυναμη ομαδων εκτος top-5')
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
for lab, m_ in (('γηπεδουχος ΠΟΛΥ κυριαρχη εκτος top-5 (t ≥0.9)', (~y.lgh.isin(TOP5)) & (y.th >= .9)),
                ('φιλοξενουμενος ΠΟΛΥ κυριαρχη εκτος top-5 (t ≥0.9)', (~y.lga.isin(TOP5)) & (y.ta >= .9)),
                ('γηπεδουχος top-5', y.lgh.isin(TOP5)), ('φιλοξενουμενος top-5', y.lga.isin(TOP5))):
    z = y[m_]
    print(f'   {lab:52s} n{len(z):3d} · αλλαγη απο τη μιξη {(z.mE - z.mM).mean():+.2f} · (σημερινο−αγορα {(z.mM - z.mk).mean():+.2f} → μιξη−αγορα {(z.mE - z.mk).mean():+.2f} · πραγμ−αγορα {(z.gd - z.mk).mean():+.2f})')
