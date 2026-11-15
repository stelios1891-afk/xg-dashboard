"""uel_all_mechanisms.py — 15/10/2026 (Στελιος: «παρε ολους τους μηχανισμους και τεσταρε, απο το ποσο μετραει η περσινη σεζον, μεχρι τη φετινη, ποσο
μετρανε τα ευρωπαικα περσινα και αν μετρανε τα φετινα ευρωπαικα, αξια, αγκυρα, αποδοσεις νικητη, τα παντα ολα» — ΜΟΝΟ Europa League).
Καθε μηχανισμος ΧΩΡΙΣΤΑ (ενας-ενας, ολα τα αλλα ως σημερα), πανω στα ιδια ματς Europa 2223-2526:
  1. K       περσινη σεζον vs φετινη (n/(n+K)): 4 / 8 (σημερα) / 16 / 32            ← ξαναχτισμα (euro_variant_build / euro_blend_dump)
  2. W       περσινα ευρωπαικα στη βαση: 0 / 1 / 2 (σημερα) / 4                     ← ξαναχτισμα
  3. M8      φετινα ευρωπαικα (μεσα στη διοργανωση): 0 / 0.5 (σημερα live) / 1 / 2  ← euro_inseason_eu_preds.pkl
  4. xG      μεριδιο xG στη δυναμη: 20 / 40 / 60 (σημερα) / 80 / 100%
  5. ΑΞΙΑ    μιξη διαφορας με «τι λεει η αξια ενδεκαδας»: 0 / .25 / .5 / .75
  6. ΑΓΚΥΡΑ  μιξη διαφορας με την ΠΡΩΤΗ τιμη αγορας (ανοιγμα): 0 / .15 / .3 / .5
  7. γ −0.47 (0 / −0.94) · 8. ΕΔΡΑ 1.139 (1.00 / 1.25) · 9. ΛΙΓΚΑ ρ 1.0 (0.5 / 1.5) · 10. ΙΣΟΠΑΛΙΕΣ ×0.85 (1.00 / 0.75)
  11. ΤΙΜΟΛΟΓΗΣΗ φαβορι: σωστα τεταρτα (σημερα) / σαν μισα
Ο λογος εκδοχη/βαση εφαρμοζεται πανω στο σημερινο λ (ιδια μεθοδος με euro_mechanism_audit).
ΑΚΡΙΒΕΙΑ: RPS 1Χ2 και Δlog-loss 1Χ2 ανα σεζον (ολες οι κατηγοριες). PICKS: κανονες UEL (φαβ ≥4% σωστα τεταρτα ≤−0.5 · dog ≥10% p_cover ≥+0.5 ·
1.70-2.10 · πρωτη εμφανιση ≤72ω · Crown & SBOBET μεσος) — Α φαβ εντος / Α φαβ εκτος / Α dogs / Β φαβ / Β dogs.
LOSO ανα μηχανισμο: για καθε σεζον η ρυθμιση διαλεγεται απο τις ΑΛΛΕΣ 3 (α: καλυτερη ακριβεια 1Χ2 · β: περισσοτερες μοναδες) → αποτελεσμα στην 4η.
Αποδοσεις νικητη (outrights): ΔΕΝ υπαρχουν ιστορικα για το Europa → δεν ελεγχεται.
"""
import sys, pickle
exec(open("euro_value_filter_check.py", encoding="utf-8").read().split("# πλευρα ΧΩΡΙΣ FotMob")[0])
import euro_shadow_scan as ES
sys.stdout.reconfigure(encoding='utf-8')
NL = chr(10)
HF0 = 1.139; G0 = -0.47
x = A[A.comp == 'EuropaLeague'].reset_index(drop=True); seas = sorted(x.sea.unique())
mids = [str(MIDS[int(i)]) for i in x.i]
LH, LA, D = x.lh.values, x.la.values, x.D.values
def ratio(dump, base):
    db = pickle.load(open(f'euro_blend_dump_{base}.pkl', 'rb')); dv = pickle.load(open(f'euro_blend_dump_{dump}.pkl', 'rb'))
    ib = {str(m): k for k, m in enumerate(db['MIDS'])}; iv = {str(m): k for k, m in enumerate(dv['MIDS'])}
    rh = np.array([dv['LH'][iv[m]] / db['LH'][ib[m]] if m in iv and m in ib and db['LH'][ib[m]] > 0 else 1.0 for m in mids])
    ra = np.array([dv['LA'][iv[m]] / db['LA'][ib[m]] if m in iv and m in ib and db['LA'][ib[m]] > 0 else 1.0 for m in mids])
    return LH * rh, LA * ra
IS = pickle.load(open('euro_inseason_eu_preds.pkl', 'rb')); iis = {str(m): k for k, m in enumerate(IS['mids'])}
def ratio_is(w):
    b = np.array(IS['live']['0.0']); v = np.array(IS['live'][w])
    rh = np.array([v[0][iis[m]] / b[0][iis[m]] if m in iis and b[0][iis[m]] > 0 else 1.0 for m in mids])
    ra = np.array([v[1][iis[m]] / b[1][iis[m]] if m in iis and b[1][iis[m]] > 0 else 1.0 for m in mids])
    return LH * rh, LA * ra
# «τι λεει η αξια» (LOSO ευθεια, ιδια με Φ2) και ΑΝΟΙΓΜΑ αγορας (μεσος Crown/SBOBET)
VM = np.array([VF[s][0] * lv + VF[s][1] for s, lv in zip(x.sea, x.lv_)]); HASV = x.hasv.values
MO = []
for k_, m in enumerate(mids):
    v = []
    for bk in ('Crown', 'SBOBET'):
        s = snapT(m, bk, 'open')
        if s: v.append(implied_margin(int(x.i[k_]), *s))
    MO.append(np.mean(v) if v else np.nan)
MO = np.array(MO)
def mix(lh, la, target, w, ok):
    T = lh + la; mm = np.where(ok, (1 - w) * (lh - la) + w * np.nan_to_num(target), lh - la)
    return np.maximum((T + mm) / 2, .05), np.maximum((T - mm) / 2, .05)
FAM = {}   # οικογενεια → [(ονομα, (lh, la, ds, pricing), σημερινο?)]
FAM['1. περσινη σεζον K'] = [('K 4', (*ratio('K4', 'base06'), .85, 'q'), 0), ('K 8', (LH, LA, .85, 'q'), 1), ('K 16', (*ratio('K16', 'base06'), .85, 'q'), 0), ('K 32', (*ratio('K32', 'base06'), .85, 'q'), 0)]
FAM['2. περσινα ευρωπαικα W'] = [('W 0', (*ratio('W0', 'base06'), .85, 'q'), 0), ('W 1', (*ratio('W1', 'base06'), .85, 'q'), 0), ('W 2', (LH, LA, .85, 'q'), 1), ('W 4', (*ratio('W4', 'base06'), .85, 'q'), 0)]
FAM['3. φετινα ευρωπαικα'] = [('βαρος 0', (LH, LA, .85, 'q'), 0), ('βαρος 0.5', (*ratio_is('0.5'), .85, 'q'), 1), ('βαρος 1', (*ratio_is('1.0'), .85, 'q'), 0), ('βαρος 2', (*ratio_is('2.0'), .85, 'q'), 0)]
FAM['4. μεριδιο xG'] = [('xG 20%', (*ratio('0.2', '0.6'), .85, 'q'), 0), ('xG 40%', (*ratio('0.4', '0.6'), .85, 'q'), 0), ('xG 60%', (LH, LA, .85, 'q'), 1),
                        ('xG 80%', (*ratio('0.8', '0.6'), .85, 'q'), 0), ('xG 100%', (*ratio('1.0', '0.6'), .85, 'q'), 0)]
FAM['5. αξια ενδεκαδας'] = [(f'αξια {w:.2f}', (*mix(LH, LA, VM, w, HASV), .85, 'q'), int(w == 0)) for w in (0, .25, .5, .75)]
FAM['6. αγκυρα στο ανοιγμα'] = [(f'αγκυρα {w:.2f}', (*mix(LH, LA, MO, w, np.isfinite(MO)), .85, 'q'), int(w == 0)) for w in (0, .15, .3, .5)]
def gam(g): dc = (g - G0) * D; return np.maximum(LH - dc / 2, .05), np.maximum(LA + dc / 2, .05)
FAM['7. γ ξεφουσκωμα λιγκας'] = [('γ 0', (*gam(0.0), .85, 'q'), 0), ('γ −0.47', (LH, LA, .85, 'q'), 1), ('γ −0.94', (*gam(-0.94), .85, 'q'), 0)]
FAM['8. εδρα'] = [('εδρα 1.00', (LH / HF0, LA * HF0, .85, 'q'), 0), ('εδρα 1.139', (LH, LA, .85, 'q'), 1), ('εδρα 1.25', (LH * 1.25 / HF0, LA * HF0 / 1.25, .85, 'q'), 0)]
FAM['9. διαφορα λιγκας ρ'] = [('ρ 0.5', (LH * np.exp(-.5 * D), LA * np.exp(.5 * D), .85, 'q'), 0), ('ρ 1.0', (LH, LA, .85, 'q'), 1), ('ρ 1.5', (LH * np.exp(.5 * D), LA * np.exp(-.5 * D), .85, 'q'), 0)]
FAM['10. ισοπαλιες'] = [('×1.00', (LH, LA, 1.0, 'q'), 0), ('×0.85', (LH, LA, .85, 'q'), 1), ('×0.75', (LH, LA, .75, 'q'), 0)]
FAM['11. τιμολογηση φαβορι'] = [('σωστα τεταρτα', (LH, LA, .85, 'q'), 1), ('σαν μισα', (LH, LA, .85, 'p'), 0)]
# στιγμιοτυπα
HSP = [h for h in HS if h > 0]
SN = {(k_, bk, h): snapT(m, bk, h) for k_, m in enumerate(mids) for bk in ('Crown', 'SBOBET') for h in HSP}
def evaluate(lh, la, ds, pr):
    out = []
    for k_ in range(len(x)):
        if x.cat[k_] not in ('A', 'B'): continue
        i = int(x.i[k_]); D_ = ES.eu_dist(lh[k_], la[k_], ds)
        for bk in ('Crown', 'SBOBET'):
            got = set()
            for h in HSP:
                s = SN[(k_, bk, h)]
                if not s: continue
                L, oh, oa = s
                for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                    if side in got or not (1.70 <= o <= 2.10): continue
                    if ln <= -0.5: f = cover_q if pr == 'q' else picks.p_cover; th = .04; kind = 'φαβ'
                    elif ln >= 0.5: f = picks.p_cover; th = .10; kind = 'dog'
                    else: continue
                    if edge(*f(D_, side, ln), o) < th: continue
                    got.add(side)
                    out.append(dict(i=i, side=side, cat=x.cat[k_], sea=x.sea[k_], bk=bk, kind=kind, ven='εντος' if side == 1 else 'εκτος', pnl=picks.settle(GD[i], side, ln, o)))
    return pd.DataFrame(out, columns=['i', 'side', 'cat', 'sea', 'bk', 'kind', 'ven', 'pnl'])
GDv = x.gd.values
def acc(lh, la, ds):
    r = []; l = []
    for a, b, g in zip(lh, la, GDv):
        D_ = ES.eu_dist(a, b, ds); p1 = sum(p for kk, p in D_.items() if kk > 0); px = D_.get(0, 0); p2 = 1 - p1 - px
        r.append(((p1 - (g > 0)) ** 2 + (p1 + px - (g >= 0)) ** 2) / 2); l.append(np.log(max(p1 if g > 0 else (px if g == 0 else p2), 1e-9)))
    return np.array(r), np.array(l)
def u(y): return y.groupby('bk').pnl.sum().mean() if len(y) else 0.0
def cell(y):
    if len(y) == 0: return '—'
    m = y.groupby('bk').pnl.mean(); n = y.groupby('bk').size().mean(); return f'{n:3.0f} {100 * m.mean():+4.0f}% {m.mean() * n:+5.1f}'
GR = (('Α φαβ εντος', lambda P: (P.cat == 'A') & (P.kind == 'φαβ') & (P.ven == 'εντος')), ('Α φαβ εκτος', lambda P: (P.cat == 'A') & (P.kind == 'φαβ') & (P.ven == 'εκτος')),
      ('Α dogs', lambda P: (P.cat == 'A') & (P.kind == 'dog')), ('Β φαβορι', lambda P: (P.cat == 'B') & (P.kind == 'φαβ')), ('Β dogs', lambda P: (P.cat == 'B') & (P.kind == 'dog')))
SEAM = {s: (x.sea == s).values for s in seas}
_, LL0 = acc(LH, LA, .85)
print(f'EUROPA LEAGUE: {len(x)} ματς ({", ".join(f"{s}: {int(m.sum())}" for s, m in SEAM.items())}) · picks Α & Β · κελι = picks ανα βιβλιο · ROI · μοναδες')
print('Δ1Χ2 = διαφορα log-loss 1Χ2 vs σημερινο (θετικο = καλυτερη προβλεψη) ανα σεζον 22/23/24/25')
LOSO = []
for fam, vs in FAM.items():
    print(f'{NL}── {fam} ' + '─' * (150 - len(fam)))
    print(f'   {"ρυθμιση":14s} │ {"RPS":>6s} │ {"Δ1Χ2 ανα σεζον":>27s} │' + '│'.join(f'{g:>16s}' for g, _ in GR) + f'│ {"ΣΥΝΟΛΟ":>16s} │ μοναδες ανα σεζον')
    RES = {}
    for nm, (lh, la, ds, pr), cur in vs:
        r, l = acc(lh, la, ds); P = evaluate(lh, la, ds, pr); RES[nm] = (l, P)
        dl = [l[SEAM[s]].sum() - LL0[SEAM[s]].sum() for s in seas]
        print(f' {"►" if cur else " "} {nm:14s} │ {r.mean():.4f} │ ' + ' '.join(f'{v:+6.1f}' for v in dl) + ' │' +
              '│'.join(f'{cell(P[f(P)]) if len(P) else "—":>16s}' for _, f in GR) + f'│ {cell(P):>16s} │ ' + ' '.join(f'{u(P[P.sea == s]):+5.1f}' for s in seas))
    # LOSO
    cur_nm = [nm for nm, _, c in vs if c][0]
    for crit in ('ακριβεια', 'μοναδες'):
        ch = []; outs = []
        for s in seas:
            if crit == 'ακριβεια': best = max(RES, key=lambda n: RES[n][0][~SEAM[s]].sum())
            else: best = max(RES, key=lambda n: u(RES[n][1][RES[n][1].sea != s]))
            ch.append(best); P = RES[best][1]; outs.append(P[P.sea == s])
        Z = pd.concat(outs); Z0 = RES[cur_nm][1]
        dll = sum(RES[c][0][SEAM[s]].sum() - LL0[SEAM[s]].sum() for c, s in zip(ch, seas))
        LOSO.append((fam, crit, ch, dll, u(Z) - u(Z0), Z, Z0))
        print(f'   LOSO {crit:8s}: ' + ' · '.join(f'{s[2:]}→{c}' for s, c in zip(seas, ch)) + f' │ Δ1Χ2 εκτος δειγματος {dll:+.1f} │ μοναδες {u(Z0):+.1f} → {u(Z):+.1f} │ ' +
              ' · '.join(f'{g} {u(Z0[f(Z0)]):+.1f}→{u(Z[f(Z)]):+.1f}' for g, f in GR))
print(f'{NL}ΣΥΝΟΨΗ LOSO (εκτος δειγματος, vs σημερινο)')
print(f'   {"μηχανισμος":28s} │ {"κριτηριο":9s} │ {"Δ1Χ2":>6s} │ {"Δμοναδες":>8s} │ επιλογες ανα σεζον')
for fam, crit, ch, dll, du, Z, Z0 in LOSO:
    print(f'   {fam:28s} │ {crit:9s} │ {dll:+6.1f} │ {du:+8.1f} │ {", ".join(ch)}')
