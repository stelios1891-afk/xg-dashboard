# -*- coding: utf-8 -*-
"""t44_totals_season_parts.py — ΣΥΝΟΛΑ NBA · ΤΕΣΤ Α-Ε (21/10/2026, Στελιος «οκ τρεξτα ολα» + «το απλο μοντελο τον Οκτ-Δεκ κερδιζε»).
Βαση _t35 · Μ2δ (t39) LOSO 5σ + walk-forward 2024-26 · απλο = live μοντελο μ (μηχανη + Φ3 + απουσιες Out) σ 18.
ΠΡΟ-ΔΗΛΩΜΕΝΑ (γραφτηκαν πριν το τρεξιμο):
 Α ΤΥΦΛΟ OVER vs Μ2δ: ολα τα over στο ανοιγμα (Φεβ-Απρ · Μαρ-Απρ · Οκτ-Νοε) vs picks Μ2δ ιδιας περιοδου (ολα & μονο over).
   Η Μ2δ ΠΡΟΣΘΕΤΕΙ αν ROI ≥ τυφλο + 3pp σε ≥4/5 σεζον (LOSO) ΚΑΙ walk-forward συνολο ≥ +3pp.
 Β ΓΙΑΤΙ ΚΑΝΕΙ ΛΑΘΟΣ ΤΟ ΚΛΕΙΣΙΜΟ Φεβ-Απρ (περιγραφικο): πραγμ − κλεισιμο ανα: ομαδες χωρις κινητρο (0/1/2) · τελικη διαφορα ≥20 ·
   παραταση · αποντες αμυνας που ΠΡΟΣΤΕΘΗΚΑΝ ανοιγμα→Τ−30′ · ρυθμος/αποδοση (κατοχες, ποντοι ανα κατοχη) ανα μηνα.
 Γ ΝΩΡΙΣ ΣΤΗ ΣΕΖΟΝ (Οκτ-Ιαν): (1) καθολου picks · (2) κατωφλι 10% / 12% · (3) μισο βαρος (αγορα + 0.5·(Μ2δ − αγορα)) 6%.
   Μια εκδοχη ΠΕΡΝΑ αν μοναδες ολης σεζον οχι χειροτερες απο Μ2δ σε ≥4/5 (LOSO) ΚΑΙ walk-forward συνολο οχι χειροτερο.
 Δ ΧΡΟΝΟΣ (Οκτ-Ιαν, περιγραφικο): Μ2δ στο ανοιγμα / Τ−2ω / Τ−30′ · ανοιγμα ανα ωρες πριν (≥24 / 12-24 / <12).
 Ε ΑΠΛΟ ΜΟΝΤΕΛΟ Οκτ-Δεκ: μ ≥8% (live) ανα μηνα/σεζον vs Μ2δ· ΥΒΡΙΔΙΟ = απλο ≥8% Οκτ-Δεκ + Μ2δ ≥6% απο Ιαν.
   Το υβριδιο ΠΕΡΝΑ αν μοναδες > Μ2δ σε ≥4/5 (LOSO) ΚΑΙ walk-forward συνολο > Μ2δ. (Σημ.: το απλο ρυθμιστηκε σε αυτες τις σεζον → αισιοδοξο.)
Εξοδος: t44_totals_season_parts_out.txt"""
import os, sys, io, contextlib, pickle
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't36_totals_diag.py'), encoding='utf-8').read().split("P(''); P('=== ΜΗΧΑΝΕΣ (LOSO) ===')")[0]
src = src.replace("out = []\ndef P(s=''): print(s, flush=True); out.append(str(s))", "out = []\ndef P(s=''): pass")
with contextlib.redirect_stdout(_B()): exec(src)
t27 = open(os.path.join(SC, 't27_april_rules.py'), encoding='utf-8').read().split("OLD = pd.read_csv")[0]
ns = {'__file__': os.path.join(SC, 't27_april_rules.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(t27, ns)
sys.stdout.reconfigure(encoding='utf-8')
GRP, PRACT, SEAS, dDg = ns['GRP'], ns['PRACT'], ns['SEAS'], ns['dD']
def nomot(i, t):
    s, d = SEAS[i], dDg[i]; return int(GRP.get((s, d, t), 'νωρις') in ('ΚΛΕΙΔΩΜΕΝΗ', 'ΑΔΙΑΦΟΡΗ', 'TANKING') or (s, d, t) in PRACT)
Gd = pickle.load(open(os.path.join(ROOT, 'nba_diag_data.pkl'), 'rb'))['G'].reset_index(drop=True)
GL = pd.read_csv(os.path.join(ROOT, 'nba_gamelogs.csv'), usecols=['date', 'team', 'game_location', 'overtimes'])
OT = {(d, t) for d, t, loc, o in zip(GL.date, GL.team, GL.game_location, GL.overtimes) if isinstance(o, str) and o.strip()}
out2 = []
def P2(s=''): print(s, flush=True); out2.append(str(s))
def fx(D): return np.c_[feats(D), (D.mon == 4).astype(float)]
def fitp(D, Xf, y, tr, te):
    A_ = np.c_[np.ones(tr.sum()), Xf[tr]]; b = np.linalg.solve(A_.T @ A_ + 50 * np.eye(A_.shape[1]), A_.T @ y[tr])
    return D.fair.values[te] + np.c_[np.ones(te.sum()), Xf[te]] @ b
def build(tau):
    D = X[X.tau == tau].reset_index(drop=True); ys = D.sea.values; y = (D.tot - D.fair).values; Xf = fx(D)
    D['m2'] = 0.0; D['wf'] = np.nan
    for s in SE: D.loc[ys == s, 'm2'] = fitp(D, Xf, y, ys != s, ys == s)
    for s in (2024, 2025, 2026): D.loc[ys == s, 'wf'] = fitp(D, Xf, y, ys < s, ys == s)
    return D
D = build('ανοιγμα')
D['margin'] = np.abs(Gd.hs.values[D.i] - Gd.as_.values[D.i]); D['pace'] = Gd.pace.values[D.i]
D['ot'] = [int((d, h) in OT) for d, h in zip(D.date, D.home)]
D['nchk'] = [nomot(i, h) + nomot(i, a) for i, h, a in zip(D.i, D.home, D.away)]
L30 = X[X.tau == 'Τ−30′'].set_index('i'); D['dld'] = [L30.ld.get(i, np.nan) - ld for i, ld in zip(D.i, D.ld)]
EARLY = (10, 11, 12, 1)
def addm(p, d):
    if not len(p): return p
    m = d.set_index('i'); p['mon'] = m.loc[p.i, 'mon'].values; return p
def units(p, seas):
    return (p.groupby('sea').res.sum().reindex(seas, fill_value=0.0) if len(p) else pd.Series(0.0, index=seas))
def blind_over(d):
    r = np.where(d.tot > d['T'], d.oo - 1, np.where(d.tot == d['T'], 0.0, -1.0))
    return pd.DataFrame(dict(i=d.i.values, sea=d.sea.values, res=r, clv=(d.cfair - d.fair).values, sd=1))
# ================= Α =================
P2('=== Α · ΤΥΦΛΟ OVER (ανοιγμα) vs Μ2δ ===')
for col, lab, seas in (('m2', 'LOSO', SE), ('wf', 'walk-forward', [2024, 2025, 2026])):
    dd = D[D.sea.isin(seas)]; pk = addm(picks(dd, col=col, thr=.06), dd)
    for per, ms in (('Οκτ-Νοε', (10, 11)), ('Φεβ-Απρ', (2, 3, 4)), ('Μαρ-Απρ', (3, 4))):
        b = blind_over(dd[dd.mon.isin(ms)]); p = pk[pk.mon.isin(ms)]; po = p[p.sd == 1]
        rb = b.groupby('sea').res.mean(); rp = p.groupby('sea').res.mean().reindex(rb.index); beat = int(((rp - rb) >= .03).sum())
        P2(f'  {lab:12s} {per}: τυφλο over {cell(b)} | Μ2δ {cell(p)} | Μ2δ μονο over {cell(po)}')
        P2(f'      ανα σεζον Μ2δ − τυφλο (pp): ' + ' · '.join(f'{s}: {100 * (rp[s] - rb[s]):+.0f}' for s in rb.index) + f' → ≥3pp σε {beat}/{len(rb)} · συνολο {100 * (p.res.mean() - b.res.mean()):+.1f}pp')
# ================= Β =================
P2(''); P2('=== Β · ΓΙΑΤΙ ΚΑΝΕΙ ΛΑΘΟΣ ΤΟ ΚΛΕΙΣΙΜΟ: πραγμ − κλεισιμο (ολα τα ματς) ===')
def bias(d): r = d.tot - d.cfair; return f'{r.mean():+5.2f} ± {r.std() / np.sqrt(max(len(r), 1)):.2f} (n {len(r)})'
for per, ms in (('Οκτ-Ιαν', EARLY), ('Φεβ-Απρ', (2, 3, 4))):
    d = D[D.mon.isin(ms)]
    P2(f'  {per}: ολα {bias(d)} · χωρις παρατασεις {bias(d[d.ot == 0])} · παρατασεις {d.ot.mean() * 100:.1f}%')
    P2(f'     ομαδες χωρις κινητρο 0/1/2: ' + ' · '.join(f'{k}: {bias(d[d.nchk == k])}' for k in (0, 1, 2)))
    P2(f'     τελικη διαφορα <10 / 10-19 / ≥20: {bias(d[d.margin < 10])} · {bias(d[(d.margin >= 10) & (d.margin < 20)])} · {bias(d[d.margin >= 20])} · ≥20 = {100 * (d.margin >= 20).mean():.0f}%')
    P2(f'     αποντες αμυνας προστεθηκαν ανοιγμα→Τ−30′ (dLD >0.3 / ≈0): {bias(d[d.dld > .3])} · {bias(d[d.dld.abs() <= .3])}')
P2('  ανα μηνα: κατοχες · ποντοι/100 κατοχες · πραγμ − κλεισιμο · % διαφορα ≥20 · % παραταση · % ματς με ομαδα χωρις κινητρο')
for m in (10, 11, 12, 1, 2, 3, 4):
    d = D[D.mon == m]
    P2(f'    {m:2d}: {d.pace.mean():6.1f} · {100 * (d.tot / d.pace / 2).mean():6.1f} · {(d.tot - d.cfair).mean():+5.2f} · {100 * (d.margin >= 20).mean():3.0f}% · {100 * d.ot.mean():3.1f}% · {100 * (d.nchk > 0).mean():3.0f}%')
d = D[D.mon.isin((2, 3, 4))]
A_ = np.c_[np.ones(len(d)), (d.nchk > 0), (d.margin >= 20), d.ot, np.clip(d.dld.fillna(0), 0, None)].astype(float)
b = np.linalg.lstsq(A_, (d.tot - d.cfair).values, rcond=None)[0]
P2(f'  Φεβ-Απρ μαζι (γραμμικο): σταθερα {b[0]:+.2f} · χωρις κινητρο {b[1]:+.2f} · διαφορα ≥20 {b[2]:+.2f} · παραταση {b[3]:+.2f} · νεοι αποντες αμυνας {b[4]:+.2f}/μοναδα')
# ================= Γ =================
P2(''); P2('=== Γ · ΝΩΡΙΣ ΣΤΗ ΣΕΖΟΝ (Οκτ-Ιαν) ===')
def variant(col, d, kind):
    if kind == 'half':
        d = d.copy(); m = d.mon.isin(EARLY); d.loc[m, col] = d.fair[m] + 0.5 * (d[col][m] - d.fair[m]); return addm(picks(d, col=col, thr=.06), d)
    p = addm(picks(d, col=col, thr=.06), d)
    if kind == 'base': return p
    if kind == 'none': return p[~p.mon.isin(EARLY)]
    th = {'t10': .10, 't12': .12}[kind]; return p[(~p.mon.isin(EARLY)) | (p.e >= th)]
KINDS = (('base', 'Μ2δ (βαση)'), ('none', '(1) καθολου Οκτ-Ιαν'), ('t10', '(2) 10% Οκτ-Ιαν'), ('t12', '(2) 12% Οκτ-Ιαν'), ('half', '(3) μισο βαρος Οκτ-Ιαν'))
for col, lab, seas in (('m2', 'LOSO', SE), ('wf', 'walk-forward', [2024, 2025, 2026])):
    dd = D[D.sea.isin(seas)]; base = units(variant(col, dd, 'base'), seas)
    for k, nm in KINDS:
        p = variant(col, dd, k); u = units(p, seas); nw = int((u >= base - 1e-9).sum())
        P2(f'  {lab:12s} {nm:24s} {cell(p)} · ανα σεζον ' + ' '.join(f'{v:+.1f}' for v in u) + ('' if k == 'base' else f' · − βαση {u.sum() - base.sum():+.1f}μ (οχι χειροτερο {nw}/{len(seas)})'))
# ================= Δ =================
P2(''); P2('=== Δ · ΧΡΟΝΟΣ (Οκτ-Ιαν, Μ2δ LOSO ≥6%) ===')
for tau in ('ανοιγμα', 'Τ−2ω', 'Τ−30′'):
    dd = D if tau == 'ανοιγμα' else build(tau)
    p = addm(picks(dd, col='m2', thr=.06), dd); p = p[p.mon.isin(EARLY)]
    P2(f'  {tau:8s} {cell(p)}')
p = addm(picks(D, col='m2', thr=.06), D); hh = D.set_index('i').hrs; p['hrs'] = hh.loc[p.i].values; p = p[p.mon.isin(EARLY)]
P2('  ανοιγμα ανα ωρες πριν: ' + ' · '.join(f'{lab}: {cell(x)}' for lab, x in (('≥24ω', p[p.hrs >= 24]), ('12-24ω', p[(p.hrs >= 12) & (p.hrs < 24)]), ('<12ω', p[p.hrs < 12]))))
P2(f'  ωρες ανοιγματος Crown (ολα τα ματς Οκτ-Ιαν): διαμεσος {D[D.mon.isin(EARLY)].hrs.median():.1f} · ≥24ω {100 * (D[D.mon.isin(EARLY)].hrs >= 24).mean():.0f}%')
# ================= Ε =================
P2(''); P2('=== Ε · ΑΠΛΟ ΜΟΝΤΕΛΟ (live μ ≥8%) ===')
S = addm(picks(D, col='mu', thr=.08), D)
P2('  ανα μηνα: ' + ' · '.join(f'{m}: {100 * S[S.mon == m].res.mean():+.1f}% ({len(S[S.mon == m])})' for m in (10, 11, 12, 1, 2, 3, 4)))
SE3 = S[S.mon.isin((10, 11, 12))]
P2(f'  Οκτ-Δεκ: {cell(SE3)} · over {cell(SE3[SE3.sd == 1])} · under {cell(SE3[SE3.sd == -1])}')
P2('     ανα σεζον: ' + ' · '.join(f'{s}: {100 * SE3[SE3.sea == s].res.mean():+.1f}% ({len(SE3[SE3.sea == s])})' for s in SE) + f' · αναμενομενο απο κλεισιμο {100 * SE3.evc.mean():+.1f}%')
for col, lab, seas in (('m2', 'LOSO', SE), ('wf', 'walk-forward', [2024, 2025, 2026])):
    dd = D[D.sea.isin(seas)]; m2p = addm(picks(dd, col=col, thr=.06), dd)
    hyb = pd.concat([S[S.mon.isin((10, 11, 12)) & S.sea.isin(seas)], m2p[~m2p.mon.isin((10, 11, 12))]])
    ub, uh = units(m2p, seas), units(hyb, seas)
    P2(f'  {lab:12s} Μ2δ Οκτ-Δεκ {cell(m2p[m2p.mon.isin((10, 11, 12))])} | απλο Οκτ-Δεκ {cell(S[S.mon.isin((10, 11, 12)) & S.sea.isin(seas)])}')
    P2(f'  {lab:12s} ΥΒΡΙΔΙΟ {cell(hyb)} vs Μ2δ {cell(m2p)} · ανα σεζον υβριδιο/Μ2δ ' + ' · '.join(f'{s}: {uh[s]:+.1f}/{ub[s]:+.1f}' for s in seas) + f' → καλυτερο {int((uh > ub).sum())}/{len(seas)}')
open(os.path.join(SC, 't44_totals_season_parts_out.txt'), 'w', encoding='utf-8').write('\n'.join(out2))
