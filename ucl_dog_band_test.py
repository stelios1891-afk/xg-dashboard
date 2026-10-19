# -*- coding: utf-8 -*-
"""ucl_dog_band_test.py — 19/10/2026 (Στελιος: «τρεξε ενα πληρες τεστ στο παρελθον: αξιζει να συμπεριλαμβανουμε τα picks του 4-10% ή να ξεκιναμε απο το 10%;
ROI αλλα και κινηση αγορας και οτιδηποτε αλλο — με τον σημερινο κανονα live»).
ΣΗΜΕΡΙΝΟΣ ΚΑΝΟΝΑΣ LIVE (αουτσαιντερ Champions League): κατηγορια Α (FotMob και οι 2), γραμμη ≥ +0.5, p_cover, edge ≥4%, 1.70-2.10, ισοπαλιες ×0.85,
  ΕΙΣΟΔΟΣ στην ΠΡΩΤΗ εμφανιση μεσα στις 168ω (σημεια 168/144/120/96/72/60/48/36/24/18/12/8/6/4/2ω), πρωτη εμφανιση <2ω = καταγραφη (εκτος).
  ΤΙΜΙΟΣ ΧΡΟΝΟΣ: για εισοδο ≥96ω το μοντελο ειναι οπως ηταν 4 (≤120ω) ή 7 (>120ω) μερες πριν (euro_variant_build SHIFT, οπως ucl_early_honest).
  Crown & SBOBET ξεχωριστα (μεσος ορος στο ROI), 2022-26 (νεα μορφη = 2024-26).
ΖΩΝΕΣ: «4-10%» = το edge της πρωτης εμφανισης 4-10% · «≥10%» = ≥10%.
ΜΕΤΡΑ: ROI στην εισοδο · ROI στο κλεισιμο (ιδια πλευρα/γραμμη κλεισιματος) · CLV (γκολ, + = η αγορα ηρθε προς εμας) και % προς/κοντρα ·
  ΑΞΙΑ xG (ROI αν το ματς «επαιζε» με τα πραγματικα xG — λιγοτερη τυχη) · βαθμονομηση (υποσχεμενο edge vs πραγματικο) · ανα σεζον · ανα γραμμη ·
  «ΑΝΑΒΑΘΜΙΣΗ»: πόσα 4-10% εφτασαν αργοτερα ≥10% (και ROI αν τα επαιζες τοτε) · συνολικες μοναδες με κανονα ≥4% vs ≥10%.
ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ το τρεξιμο): η ζωνη 4-10% ΜΕΝΕΙ μονο αν ΟΛΑ: (α) ROI εισοδου > 0 στις 4 σεζον μαζι και στη νεα μορφη, (β) θετικη σε ≥3/4 σεζον,
  (γ) CLV ≥ 0 (οχι αρνητικο με t < −1.5), (δ) ΑΞΙΑ xG > 0. Αλλιως → αουτσαιντερ UCL απο 10% (η ζωνη 4-10% σε σκια)."""
import sys, pickle
_s = open('uel_all_mechanisms.py', encoding='utf-8').read()
exec(_s[:_s.index("x = A[A.comp == 'EuropaLeague']")])
import euro_shadow_scan as ES
sys.stdout.reconfigure(encoding='utf-8')
_xs = open('uel_full_review.py', encoding='utf-8').read()
exec(_xs[_xs.index('XG = {}'):_xs.index('# ======================= 1. ΣΥΝΟΛΑ')])     # XG ανα ματς + xg_value
x = A[A.comp == 'ChampionsLeague'].reset_index(drop=True)
mids = [str(MIDS[int(i)]) for i in x.i]; LH, LA = x.lh.values, x.la.values
def ratio(dump, base):
    db = pickle.load(open(f'euro_blend_dump_{base}.pkl', 'rb')); dv = pickle.load(open(f'euro_blend_dump_{dump}.pkl', 'rb'))
    ib = {str(m): k for k, m in enumerate(db['MIDS'])}; iv = {str(m): k for k, m in enumerate(dv['MIDS'])}
    rh = np.array([dv['LH'][iv[m]] / db['LH'][ib[m]] if m in iv and m in ib and db['LH'][ib[m]] > 0 else 1.0 for m in mids])
    ra = np.array([dv['LA'][iv[m]] / db['LA'][ib[m]] if m in iv and m in ib and db['LA'][ib[m]] > 0 else 1.0 for m in mids])
    return LH * rh, LA * ra
H4 = ratio('sh4', 'base06'); H7 = ratio('sh7', 'base06')
HS = (168, 144, 120, 96, 72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2)
def model_at(k_, h):
    if h > 120: return H7[0][k_], H7[1][k_]
    if h >= 96: return H4[0][k_], H4[1][k_]
    return LH[k_], LA[k_]
R = []
for k_ in range(len(x)):
    if x.cat[k_] != 'A': continue
    i = int(x.i[k_])
    for bk in ('Crown', 'SBOBET'):
        c = snapT(mids[k_], bk, 0)
        for side in (1, -1):
            first = None; up = None
            for h in HS:
                s = snapT(mids[k_], bk, h)
                if not s: continue
                L, oh, oa = s; ln = L if side == 1 else -L; o = oh if side == 1 else oa
                if ln < 0.5 or not (1.70 <= o <= 2.10): continue
                lh, la = model_at(k_, h); D_ = ES.eu_dist(lh, la, .85)
                pw, pp = picks.p_cover(D_, side, ln); e = edge(pw, pp, o)
                if e < 0.04: continue
                if first is None:
                    first = dict(h=h, L=L, ln=ln, o=o, e=e, pw=pw, pp=pp)
                if e >= 0.10 and up is None:
                    up = dict(h=h, ln=ln, o=o)
                if first is not None and up is not None: break
            if first is None: continue
            f = first
            cl = side * (implied_margin(i, *c) - implied_margin(i, f['L'], *(snapT(mids[k_], bk, f['h'])[1:]))) if c else np.nan
            if c:
                Lc, ohc, oac = c; lnc = Lc if side == 1 else -Lc; oc = ohc if side == 1 else oac
                pnl_c = picks.settle(GD[i], side, lnc, oc) if lnc >= 0.5 else np.nan
            else:
                pnl_c = np.nan
            R.append(dict(sea=x.sea[k_], bk=bk, band='4-10%' if f['e'] < 0.10 else '≥10%', e=f['e'], h=f['h'], ln=f['ln'], o=f['o'],
                          pnl=picks.settle(GD[i], side, f['ln'], f['o']), pnl_c=pnl_c, clv=cl, xv=xg_value(i, side, f['ln'], f['o']),
                          exp=f['e'], up=up is not None and f['e'] < 0.10, up_h=up['h'] if up else np.nan,
                          pnl_up=picks.settle(GD[i], side, up['ln'], up['o']) if up and f['e'] < 0.10 else np.nan))
D = pd.DataFrame(R); NEW = ['2425', '2526']
def roi(y, col='pnl'):
    y = y[y[col].notna()]
    if not len(y): return np.nan, 0, 0.0
    m = y.groupby('bk')[col].mean(); n = y.groupby('bk').size().mean(); return m.mean(), n, m.mean() * n
def tval(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return v.mean() / (v.std() / np.sqrt(len(v))) if len(v) > 3 and v.std() > 0 else np.nan
print('CHAMPIONS LEAGUE ΑΟΥΤΣΑΙΝΤΕΡ — σημερινος κανονας live (πρωτη εμφανιση ≤168ω, οχι <2ω, τιμιος χρονος) · picks ανα βιβλιο')
verdict = {}
for per, ss in (('ΟΛΕΣ 2022-26', ['2223', '2324', '2425', '2526']), ('ΝΕΑ ΜΟΡΦΗ 2024-26', NEW)):
    print(f'\n{"=" * 130}\n{per}')
    print(f'   {"ζωνη":8s} │ {"picks":>5s} {"ROI εισοδος":>11s} {"μοναδες":>8s} │ {"ROI κλεισιμο":>12s} │ {"CLV γκολ":>8s} {"t":>5s} {"προς/κοντρα":>12s} │ {"ΑΞΙΑ xG":>8s} │ {"υποσχ. edge":>11s} │ ανα σεζον (εισοδος)')
    for band in ('4-10%', '≥10%', 'ΟΛΑ'):
        y = D[D.sea.isin(ss)] if band == 'ΟΛΑ' else D[D.sea.isin(ss) & (D.band == band)]
        r, n, u = roi(y); rc, _, _ = roi(y, 'pnl_c'); xv, _, _ = roi(y, 'xv')
        cl = y.clv.dropna(); s = y.groupby('sea').pnl.mean()
        print(f'   {band:8s} │ {n:5.0f} {100 * r:+10.1f}% {u:+8.1f} │ {100 * rc:+11.1f}% │ {cl.mean():+8.3f} {tval(cl):5.2f} {100 * (cl > 0.01).mean():5.0f}%/{100 * (cl < -0.01).mean():3.0f}% │ '
              f'{100 * xv:+7.1f}% │ {100 * y.exp.mean():+10.1f}% │ ' + ' '.join(f'{k}:{100 * v:+.0f}%' for k, v in s.items()))
        if per == 'ΟΛΕΣ 2022-26' and band == '4-10%':
            verdict.update(a1=r > 0, b=(s > 0).sum() >= 3, c=not (cl.mean() < 0 and tval(cl) < -1.5), d=xv > 0, npos=int((s > 0).sum()))
        if per == 'ΝΕΑ ΜΟΡΦΗ 2024-26' and band == '4-10%':
            verdict.update(a2=r > 0)
y = D[D.band == '4-10%']
print(f'\n{"=" * 130}\nΖΩΝΗ 4-10% — ΛΕΠΤΟΜΕΡΕΙΕΣ (ολες οι σεζον)')
for lab, f in (('edge 4-6%', y.e < .06), ('edge 6-8%', (y.e >= .06) & (y.e < .08)), ('edge 8-10%', y.e >= .08)):
    r, n, u = roi(y[f]); print(f'   {lab:12s} {n:4.0f} picks · ROI {100 * r:+6.1f}% · μοναδες {u:+5.1f} · CLV {y[f].clv.mean():+.3f} · ΑΞΙΑ xG {100 * roi(y[f], "xv")[0]:+.1f}%')
for lab, f in (('γραμμη +0.5/+0.75', y.ln < .9), ('γραμμη +1/+1.25', (y.ln >= .9) & (y.ln < 1.4)), ('γραμμη ≥+1.5', y.ln >= 1.4)):
    r, n, u = roi(y[f]); print(f'   {lab:18s} {n:4.0f} picks · ROI {100 * r:+6.1f}% · CLV {y[f].clv.mean():+.3f}')
for lab, f in (('μπηκε ≥72ω', y.h >= 72), ('μπηκε 24-72ω', (y.h >= 24) & (y.h < 72)), ('μπηκε <24ω', y.h < 24)):
    r, n, u = roi(y[f]); print(f'   {lab:18s} {n:4.0f} picks · ROI {100 * r:+6.1f}% · CLV {y[f].clv.mean():+.3f}')
uu = y[y.up]
print(f'   ΑΝΑΒΑΘΜΙΣΗ: {100 * y.up.mean():.0f}% των 4-10% εφτασαν αργοτερα ≥10% · αν τα επαιζες ΤΟΤΕ: ROI {100 * roi(uu, "pnl_up")[0]:+.1f}% '
      f'({roi(uu, "pnl_up")[1]:.0f} picks) vs στην αρχικη τιμη {100 * roi(uu)[0]:+.1f}% · οσα ΔΕΝ αναβαθμιστηκαν: ROI {100 * roi(y[~y.up])[0]:+.1f}% ({roi(y[~y.up])[1]:.0f})')
print(f'\n{"=" * 130}\nΣΥΝΟΛΙΚΑ (ολες οι σεζον): κανονας ≥4% → {roi(D)[1]:.0f} picks, {roi(D)[2]:+.1f} μοναδες, ROI {100 * roi(D)[0]:+.1f}% · '
      f'κανονας ≥10% → {roi(D[D.band == "≥10%"])[1]:.0f} picks, {roi(D[D.band == "≥10%"])[2]:+.1f} μοναδες, ROI {100 * roi(D[D.band == "≥10%"])[0]:+.1f}%')
ok = all(verdict.get(k) for k in ('a1', 'a2', 'b', 'c', 'd'))
print(f'\nΚΡΙΤΗΡΙΟ ζωνης 4-10%: (α) ROI>0 ολες {"✓" if verdict.get("a1") else "✗"} / νεα μορφη {"✓" if verdict.get("a2") else "✗"} · (β) θετικη σε ≥3/4 σεζον '
      f'{"✓" if verdict.get("b") else "✗"} ({verdict.get("npos")}/4) · (γ) CLV οχι αρνητικο {"✓" if verdict.get("c") else "✗"} · (δ) ΑΞΙΑ xG>0 {"✓" if verdict.get("d") else "✗"}')
print('ΑΠΟΦΑΣΗ: ' + ('η ζωνη 4-10% ΜΕΝΕΙ' if ok else 'αουτσαιντερ UCL απο 10% — η ζωνη 4-10% σε ΣΚΙΑ'))
