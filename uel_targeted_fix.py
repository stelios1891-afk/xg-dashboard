"""uel_targeted_fix.py — 15/10/2026 (Στελιος: «οκ δοκιμασε αυτο» — ΣΤΟΧΕΥΜΕΝΗ διορθωση).
ΜΗΧΑΝΙΣΜΟΣ: μικραινει ΜΟΝΟ η εγχωρια κυριαρχια (t = ποσο πανω/κατω απο τον μεσο της λιγκας του) των ομαδων ΕΚΤΟΣ top-5:
   log λ_γηπ += b·(t_γηπ·[γηπ εκτος top-5] − t_φιλ·[φιλ εκτος top-5])/2 , log λ_φιλ −= το ιδιο
   (b < 0: η κυριαρχη ομαδα μικρης λιγκας κατεβαινει, η «αδυναμη» ανεβαινει — ο μεσος της λιγκας μενει ιδιος)
   top-5 ΑΘΙΚΤΕΣ · διαφορα λιγκας ΑΘΙΚΤΗ · εδρα ΑΘΙΚΤΗ · ΜΙΑ παραμετρος b, απο τις ΑΛΛΕΣ 3 σεζον (LOSO, πιθανοφανεια γκολ, ολες οι κατηγοριες).
Europa League 2223-2526. Ακριβεια (RPS, Δlog-lik ανα σεζον) · picks με τους κανονες UEL (φαβ ≥4% σωστα τεταρτα ≤−0.5 · dog ≥10% p_cover ≥+0.5 ·
1.70-2.10 · πρωτη εμφανιση ≤72ω) σε κατηγορια Α και Β: κοπηκαν / κρατηθηκαν / προστεθηκαν + 10 και 10 με δικαιες αποδοσεις πριν/μετα vs αγορα.
+ ελεγχος: Liverpool / Leverkusen (πρεπει να μενουν ιδιες) και ποιες ομαδες αλλαξαν περισσοτερο.
"""
import sys
exec(open('euro_fix_threshold_timing.py', encoding='utf-8').read().split("for cm in COMP_ONLY:")[0])
NL = chr(10)
x = A[A.comp == 'EuropaLeague'].reset_index(drop=True); seas = sorted(x.sea.unique())
x['nh'] = (~x.lgh.isin(TOP5)).astype(float); x['na'] = (~x.lga.isin(TOP5)).astype(float)
x['zt'] = (x.th * x.nh - x.ta * x.na) / 2
def lamT(y, b): return y.lh.values * np.exp(b * y.zt.values), y.la.values * np.exp(-b * y.zt.values)
GB = np.round(np.arange(-1.2, 0.41, 0.05), 2)
B_ = {}
for s in seas:
    tr = x[x.sea != s]; B_[s] = GB[int(np.argmax([ll(tr, *lamT(tr, b)) for b in GB]))]
lh1 = np.zeros(len(x)); la1 = np.zeros(len(x))
for s in seas:
    te = (x.sea == s).values; a, b = lamT(x[te], B_[s]); lh1[te] = a; la1[te] = b
x['lh1'] = lh1; x['la1'] = la1
print('ΠΑΡΑΜΕΤΡΟΣ b (απο τις αλλες 3 σεζον): ' + ' · '.join(f'{s}: {B_[s]:+.2f}' for s in seas) +
      f'   (−0.50 = η εγχωρια κυριαρχια ομαδων εκτος top-5 μετραει στο μισο)')
R0 = rps(x.lh.values, x.la.values, x.gd.values); R1 = rps(lh1, la1, x.gd.values)
d = {s: ll(x[x.sea == s], lh1[(x.sea == s).values], la1[(x.sea == s).values]) - ll(x[x.sea == s], x.lh.values[(x.sea == s).values], x.la.values[(x.sea == s).values]) for s in seas}
print(f'ΑΚΡΙΒΕΙΑ (ολες οι κατηγοριες, {len(x)} ματς): RPS σημερινο {R0.mean():.4f} → στοχευμενη {R1.mean():.4f} · Δlog-lik ' +
      ' '.join(f'{s[2:]}:{t:+.1f}' for s, t in d.items()) + f' · θετικες {sum(t > 0 for t in d.values())}/4')
for c_ in ('A', 'B'):
    m_ = (x.cat == c_).values
    print(f'   κατηγορια {c_}: RPS {R0[m_].mean():.4f} → {R1[m_].mean():.4f} ({m_.sum()} ματς)')
NM = {}
for i in x.i:
    m = EUM.get(str(MIDS[int(i)]))
    if m: NM[int(i)] = (m['home']['name'], m['away']['name'])
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
                if e >= th: out[side] = dict(kind=kind, ln=ln, o=o, e=e, pnl=picks.settle(GD[i], side, ln, o))
        if out: return out
    return {}
def fair_e(lh, la, side, ln, o):
    f = cover_q if ln <= -0.5 else picks.p_cover; pw, pp = f(sdist(lh, la), side, ln); return (1 - pp) / max(pw, 1e-9), edge(pw, pp, o)
for CAT, lab in (('A', 'ΚΑΤΗΓΟΡΙΑ Α (FotMob και οι 2)'), ('B', 'ΚΑΤΗΓΟΡΙΑ Β (η μια χωρις FotMob)')):
    REC = []
    for r in x[x.cat == CAT].itertuples():
        i = int(r.i); p0 = first_pick(i, r.lh, r.la); p1 = first_pick(i, r.lh1, r.la1); hn, an = NM.get(i, ('?', '?'))
        for side in set(p0) | set(p1):
            a, b = p0.get(side), p1.get(side); pk = a or b
            st = 'κρατηθηκε' if a and b else ('ΚΟΠΗΚΕ' if a else 'ΠΡΟΣΤΕΘΗΚΕ')
            f0, e0 = fair_e(r.lh, r.la, side, pk['ln'], pk['o']); f1, e1 = fair_e(r.lh1, r.la1, side, pk['ln'], pk['o'])
            lg_t = r.lgh if side == 1 else r.lga; t_t = r.th if side == 1 else r.ta; lg_o = r.lga if side == 1 else r.lgh; t_o = r.ta if side == 1 else r.th
            REC.append(dict(st=st, sea=r.sea, match=f'{hn} - {an}', team=hn if side == 1 else an, kind=pk['kind'], ven='εντος' if side == 1 else 'εκτος',
                            ln=pk['ln'], o=pk['o'], f0=f0, f1=f1, e0=e0, e1=e1, score=f'{int(GH[i])}-{int(GA[i])}', pnl=pk['pnl'],
                            lg_t=lg_t, t_t=t_t, lg_o=lg_o, t_o=t_o))
    R = pd.DataFrame(REC)
    print(f'{NL}{"=" * 120}{NL}{lab}')
    for st in ('ΚΟΠΗΚΕ', 'κρατηθηκε', 'ΠΡΟΣΤΕΘΗΚΕ'):
        y = R[R.st == st]
        if len(y): print(f'   {st:11s} {len(y):3d} picks · ROI {100 * y.pnl.mean():+6.1f}% · μοναδες {y.pnl.sum():+5.1f} · (φαβ {(y.kind == "φαβ").sum()} / dog {(y.kind == "dog").sum()})')
    y0 = R[R.st != 'ΠΡΟΣΤΕΘΗΚΕ']; y1 = R[R.st != 'ΚΟΠΗΚΕ']
    print(f'   ΣΗΜΕΡΙΝΟ {len(y0)} picks · ROI {100 * y0.pnl.mean():+6.1f}% · μοναδες {y0.pnl.sum():+5.1f}   →   ΣΤΟΧΕΥΜΕΝΗ {len(y1)} picks · ROI {100 * y1.pnl.mean():+6.1f}% · μοναδες {y1.pnl.sum():+5.1f}')
    for kd in ('φαβ', 'dog'):
        for vn in (None, 'εντος', 'εκτος'):
            a_ = y0[(y0.kind == kd) & ((y0.ven == vn) if vn else True)]; b_ = y1[(y1.kind == kd) & ((y1.ven == vn) if vn else True)]
            print(f'      {kd} {vn or "ολα":6s}: σημερινο {len(a_):3d} picks {100 * a_.pnl.mean():+6.1f}% ({a_.pnl.sum():+5.1f}μ) → στοχευμενη {len(b_):3d} picks {100 * b_.pnl.mean():+6.1f}% ({b_.pnl.sum():+5.1f}μ)'
                  + ' │ ανα σεζον ' + ' '.join(f'{q[2:]}:{100 * a_[a_.sea == q].pnl.mean():+.0f}→{100 * b_[b_.sea == q].pnl.mean():+.0f}' for q in seas))
    R.to_csv(f'uel_targeted_fix_{CAT}.csv', index=False, encoding='utf-8-sig')
    for st in ('ΚΟΠΗΚΕ', 'ΠΡΟΣΤΕΘΗΚΕ'):
        y = R[R.st == st].copy()
        if len(y) == 0: continue
        y['d'] = (y.e0 - y.e1) if st == 'ΚΟΠΗΚΕ' else (y.e1 - y.e0)
        y = y.sort_values('d', ascending=False).drop_duplicates('match').head(10)
        print(f'{NL}   10 ΠΟΥ {"ΚΟΠΗΚΑΝ" if st == "ΚΟΠΗΚΕ" else "ΠΡΟΣΤΕΘΗΚΑΝ"}')
        print(f'   {"σεζ":4s} {"ματς":38s} {"pick":30s} {"αγορα":>6s} │ {"δικαιη ΠΡΙΝ":>11s} {"edge":>5s} │ {"δικαιη ΜΕΤΑ":>11s} {"edge":>5s} │ {"σκορ":5s} {"αποτ":>5s} │ ομαδα pick (λιγκα, κυριαρχια t) vs αντιπαλος')
        for r in y.itertuples():
            pk = f'{r.team[:16]} {r.ln:+.2f} {r.kind} {r.ven}'
            print(f'   {r.sea:4s} {r.match[:38]:38s} {pk[:30]:30s} {r.o:6.2f} │ {r.f0:11.2f} {100 * r.e0:+4.0f}% │ {r.f1:11.2f} {100 * r.e1:+4.0f}% │ {r.score:5s} {r.pnl:+5.2f} │ '
                  f'{r.lg_t[:12]} {r.t_t:+.2f} vs {r.lg_o[:12]} {r.t_o:+.2f}')
print(f'{NL}ΕΛΕΓΧΟΣ top-5: μεγιστη αλλαγη στη διαφορα γκολ σε ματς top-5 vs top-5: {np.abs((x.lh1 - x.la1) - (x.lh - x.la))[(x.nh == 0) & (x.na == 0)].max():.3f} γκολ (πρεπει 0)')
