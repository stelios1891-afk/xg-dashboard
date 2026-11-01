"""euro_mechanism_audit.py — 15/10/2026 (Στελιος: «εισαι σιγουρος οτι οι μηχανισμοι μας δουλευουν σωστα; παρε καθε μηχανισμο και δες πως επιδρα —
ισως το Europa χρειαζεται πολυ διαφορετικη μεταχειριση απο τις αλλες 2 διοργανωσεις»).
ΕΛΕΓΧΟΣ ΚΑΘΕ ΜΗΧΑΝΙΣΜΟΥ ΧΩΡΙΣΤΑ (ενας-ενας, τα υπολοιπα ως σημερα), σε Europa / Conference / Champions, ολες οι κατηγοριες για την ακριβεια,
picks Α & Β με τους κανονες καθε διοργανωσης (UEL/UECL φαβ ≥4% dog ≥10% · UCL φαβ ≥10% dog ≥4%, πρωτη εμφανιση ≤72ω, Crown & SBOBET):
  1. γ «ξεφουσκωμα λιγκας» (−0.47, live 10/9): γ = 0 / −0.47 / −0.94
  2. ΕΔΡΑ (hf 1.139): 1.00 / 1.139 / 1.25
  3. ΔΙΑΦΟΡΑ ΛΙΓΚΑΣ (ρ = 1.0): 0.5 / 1.0 / 1.5
  4. ΙΣΟΠΑΛΙΕΣ (×0.85): 1.00 / 0.85 / 0.75
  5. xG/γκολ στη δυναμη ομαδας (σημερα 60% xG): 20 / 40 / 60 / 80 / 100% xG (ετοιμα αρχεια euro_blend_dump_*)
  6. ΤΙΜΟΛΟΓΗΣΗ φαβορι: σωστα τεταρτα (σημερα) / σαν μισα (p_cover)
Δεν ελεγχονται εδω (θελουν ξαναχτισιμο): περσινα ευρωπαικα στο prior (w=2), K=8, φετινα ευρωπαικα (M8).
"""
import sys, pickle
exec(open("euro_value_filter_check.py", encoding="utf-8").read().split("# πλευρα ΧΩΡΙΣ FotMob")[0])
import euro_shadow_scan as ES
sys.stdout.reconfigure(encoding='utf-8')
NL = chr(10)
HF0 = 1.139; G0 = -0.47
DUMPS = {s: pickle.load(open(f'euro_blend_dump_{s}.pkl', 'rb')) for s in ('0.2', '0.4', '0.6', '0.8', '1.0')}
DI = {s: {str(m): k for k, m in enumerate(d['MIDS'])} for s, d in DUMPS.items()}
RULES = {'EuropaLeague': (.04, .10), 'ConferenceLeague': (.04, .10), 'ChampionsLeague': (.10, .04)}
HSP = [h for h in HS if h > 0]
import os
ONLY = os.environ.get('AUDIT_ONLY')            # π.χ. 'xG' → μονο Europa, εκδοχες xG, ανα σεζον
for cm, lab in ((('EuropaLeague', 'EUROPA'),) if ONLY else (('EuropaLeague', 'EUROPA'), ('ConferenceLeague', 'CONFERENCE'), ('ChampionsLeague', 'CHAMPIONS'))):
    x = A[A.comp == cm].reset_index(drop=True)
    mids = [str(MIDS[int(i)]) for i in x.i]
    LH, LA, D = x.lh.values, x.la.values, x.D.values
    c0 = G0 * D
    V = {}
    V['ΣΗΜΕΡΙΝΟ'] = (LH, LA, .85, 'q')
    for g in (0.0, -0.94):
        dc = (g - G0) * D; V[f'γ {g:+.2f}'] = (np.maximum(LH - dc / 2, .05), np.maximum(LA + dc / 2, .05), .85, 'q')
    for hf in (1.0, 1.25):
        V[f'εδρα {hf:.2f}'] = (LH * hf / HF0, LA * HF0 / hf, .85, 'q')
    for rho in (0.5, 1.5):
        V[f'λιγκα ρ {rho:.1f}'] = (LH * np.exp((rho - 1) * D), LA * np.exp(-(rho - 1) * D), .85, 'q')
    for ds in (1.0, 0.75):
        V[f'ισοπαλιες ×{ds:.2f}'] = (LH, LA, ds, 'q')
    for s in ('0.2', '0.4', '0.8', '1.0'):
        d = DUMPS[s]; i0 = DI['0.6']; i1 = DI[s]
        r_h = np.array([d['LH'][i1[m]] / DUMPS['0.6']['LH'][i0[m]] if m in i1 and m in i0 and DUMPS['0.6']['LH'][i0[m]] > 0 else 1.0 for m in mids])
        r_a = np.array([d['LA'][i1[m]] / DUMPS['0.6']['LA'][i0[m]] if m in i1 and m in i0 and DUMPS['0.6']['LA'][i0[m]] > 0 else 1.0 for m in mids])
        V[f'xG {int(float(s) * 100)}%'] = (LH * r_h, LA * r_a, .85, 'q')
    V['φαβ σαν μισα'] = (LH, LA, .85, 'p')
    # στιγμιοτυπα
    SN = {}
    for k_, m in enumerate(mids):
        i = int(x.i[k_])
        for bk in ('Crown', 'SBOBET'):
            for h in HSP: SN[(k_, bk, h)] = snapT(m, bk, h)
    th_f, th_d = RULES[cm]
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
                        if ln <= -0.5: f = cover_q if pr == 'q' else picks.p_cover; th = th_f; kind = 'φαβ'
                        elif ln >= 0.5: f = picks.p_cover; th = th_d; kind = 'dog'
                        else: continue
                        if edge(*f(D_, side, ln), o) < th: continue
                        got.add(side)
                        out.append(dict(cat=x.cat[k_], sea=x.sea[k_], bk=bk, kind=kind, ven='εντος' if side == 1 else 'εκτος', pnl=picks.settle(GD[i], side, ln, o)))
        return pd.DataFrame(out)
    def rpsd(lh, la, ds):
        o = []
        for a, b, g in zip(lh, la, x.gd.values):
            D_ = ES.eu_dist(a, b, ds); p1 = sum(p for kk, p in D_.items() if kk > 0); px = D_.get(0, 0)
            o.append(((p1 - (g > 0)) ** 2 + (p1 + px - (g >= 0)) ** 2) / 2)
        return np.mean(o)
    def u(y): return y.groupby('bk').pnl.sum().mean() if len(y) else 0.0
    def cell(y):
        if len(y) == 0: return '—'
        m = y.groupby('bk').pnl.mean(); n = y.groupby('bk').size().mean(); return f'{n:3.0f} {100 * m.mean():+4.0f}% {m.mean() * n:+5.1f}'
    print(f'{NL}{"=" * 150}{NL}{lab}: {len(x)} ματς (ολες οι κατηγοριες για ακριβεια) · picks Α & Β · κελι = picks ανα βιβλιο · ROI · μοναδες')
    print(f'   {"εκδοχη":16s} │ {"RPS":>6s} {"Δlog-lik":>8s} │ {"Α φαβ εντος":>16s} │ {"Α φαβ εκτος":>16s} │ {"Α αουτσαιντερ":>16s} │ {"Β φαβορι":>16s} │ {"Β αουτσαιντερ":>16s} │ {"ΣΥΝΟΛΟ μον.":>11s}')
    base_ll = ll(x, LH, LA)
    if ONLY:
        V = {k: v for k, v in V.items() if k == 'ΣΗΜΕΡΙΝΟ' or k.startswith(ONLY)}
        seas = sorted(x.sea.unique())
        for nm, (lh, la, ds, pr) in V.items():
            P = evaluate(lh, la, ds, pr)
            dl = {q: ll(x[x.sea == q], lh[(x.sea == q).values], la[(x.sea == q).values]) - ll(x[x.sea == q], LH[(x.sea == q).values], LA[(x.sea == q).values]) for q in seas}
            print(f'   {nm:10s} Δlog-lik ' + ' '.join(f'{q[2:]}:{v:+.1f}' for q, v in dl.items()) + ' │ μοναδες ανα σεζον ' +
                  ' '.join(f'{q[2:]}:{u(P[P.sea == q]):+.1f}' for q in seas) + f' │ Α dogs {cell(P[(P.cat == "A") & (P.kind == "dog")])} · Α φαβ εντος {cell(P[(P.cat == "A") & (P.kind == "φαβ") & (P.ven == "εντος")])}')
        continue
    for nm, (lh, la, ds, pr) in V.items():
        P = evaluate(lh, la, ds, pr)
        g = lambda c_, k, v=None: P[(P.cat == c_) & (P.kind == k) & ((P.ven == v) if v else True)] if len(P) else P
        print(f'   {nm:16s} │ {rpsd(lh, la, ds):.4f} {ll(x, lh, la) - base_ll:+8.1f} │ {cell(g("A", "φαβ", "εντος")):>16s} │ {cell(g("A", "φαβ", "εκτος")):>16s} │ '
              f'{cell(g("A", "dog")):>16s} │ {cell(g("B", "φαβ")):>16s} │ {cell(g("B", "dog")):>16s} │ {u(P):+11.1f}')
