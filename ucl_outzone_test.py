# -*- coding: utf-8 -*-
"""ucl_outzone_test.py — 19/10/2026 (Στελιος: «στο Κομο και Λιλ εχουμε edge στη νικη αλλα η τιμη ξεπερναει το 2.1 και δεν βγαινει pick· τι δειχνει το
backtest; απλες νικες πανω απο 2.1; να παιζουμε κανονικα −0.25 ή ηταν αρνητικο;»).
Champions League, κατηγορια Α, σημερινη αλυσιδα (harness uel_all_mechanisms), Crown & SBOBET (μεσος), 2022-26 (+ νεα μορφη).
 Α. ΚΥΡΙΑ ΓΡΑΜΜΗ ΕΚΤΟΣ ΖΩΝΗΣ: αποδοση >2.10 (2.10-2.40 · 2.40-2.80 · 2.80-4.00) με edge ≥ κατωφλι live (φαβορι ≤−0.5 & αουτσαιντερ ≥+0.5 → 10%,
    DNB 0 → 4%) — τιμη 48ω πριν & κλεισιμο. Αναφορα: ιδιοι κανονες ΜΕΣΑ στη ζωνη 1.70-2.10.
 Β. ΓΡΑΜΜΕΣ −0.25 / +0.25 (σημερα ΔΕΝ παιζονται), 1.70-2.10, edge ≥4% / ≥10% (σωστα τεταρτα).
 Γ. ΑΠΛΗ ΝΙΚΗ (1Χ2, Pinnacle αλλιως Bet365/Crown — nowgoal_1x2_euro): edge στη νικη ≥4/10%, αποδοσεις 1.70-2.10 · 2.10-2.60 · 2.60-3.50 · ανοιγμα & κλεισιμο.
 Δ. ΠΙΟ ΑΣΦΑΛΗΣ ΓΡΑΜΜΗ οταν η κυρια ειναι εκτος ζωνης (π.χ. −0.5 @2.20 → −0.25): τιμη ΕΚΤΙΜΗΜΕΝΗ απο την κατανομη της αγορας (διαφορα κυριας γραμμης +
    συνολο αγορας, γκανιοτα της κυριας) — edge ≥4/10%.
Edge = ιδιος τυπος με τον scanner (κερδη × 0.97)."""
import sys, json, os
_s = open('uel_all_mechanisms.py', encoding='utf-8').read()
exec(_s[:_s.index("x = A[A.comp == 'EuropaLeague']")])
import euro_shadow_scan as ES
sys.stdout.reconfigure(encoding='utf-8')
x = A[(A.comp == 'ChampionsLeague') & (A.cat == 'A')].reset_index(drop=True)
mids = [str(MIDS[int(i)]) for i in x.i]
NEW = ['2425', '2526']
def ed(pw, pp, o): return pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
def tou_at(mid, bk, h):
    seq = TOU.get((mid, bk)) if 'TOU' in globals() else None
    return None
R = []
for k_ in range(len(x)):
    i = int(x.i[k_]); D_ = ES.eu_dist(x.lh[k_], x.la[k_], .85); gd = GD[i]
    for bk in ('Crown', 'SBOBET'):
        for h in (48, 0):
            s = snapT(mids[k_], bk, h)
            if not s: continue
            L, oh, oa = s; S = 1 / oh + 1 / oa
            mm = implied_margin(i, L, oh, oa); T = x.lh[k_] + x.la[k_]
            DM = ES.eu_dist(max((T + mm) / 2, .05), max((T - mm) / 2, .05), .85)    # κατανομη της ΑΓΟΡΑΣ (για εκτιμηση εναλλακτικων γραμμων)
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if ln <= -0.5: role, th = 'φαβ', .10; pw, pp = cover_q(D_, side, ln)
                elif ln >= 0.5: role, th = 'dog', .10; pw, pp = picks.p_cover(D_, side, ln)
                elif abs(ln) < .01: role, th = 'dnb', .04; pw, pp = cover_q(D_, side, ln)
                else: role, th = 'q25', .04; pw, pp = cover_q(D_, side, ln)
                e = ed(pw, pp, o)
                rec = dict(sea=x.sea[k_], bk=bk, h=h, role=role, ln=ln, o=o, e=e, th=th, pnl=picks.settle(gd, side, ln, o))
                # Δ: πιο ασφαλης γραμμη (+0.25 προς την πλευρα μας) με τιμη απο την κατανομη της αγορας + γκανιοτα κυριας
                ln2 = ln + 0.25
                mw, mp = cover_q(DM, side, ln2); ow, op = cover_q(DM, -side, -ln2)
                if mw > 0 and ow > 0:
                    f1, f2 = 1 + (1 - mw - mp) / mw, 1 + (1 - ow - op) / ow
                    o2 = f1 / S
                    pw2, pp2 = cover_q(D_, side, ln2)
                    rec.update(ln2=ln2, o2=o2, e2=ed(pw2, pp2, o2), pnl2=picks.settle(gd, side, ln2, o2))
                R.append(rec)
D = pd.DataFrame(R)
def cell(y, col='pnl'):
    y = y[y[col].notna()]
    if not len(y): return f'{"—":>40s}'
    m = y.groupby('bk')[col].mean(); n = y.groupby('bk').size().mean(); s = y.groupby('sea')[col].mean()
    return f'{n:4.0f} picks {100 * m.mean():+6.1f}% {m.mean() * n:+6.1f}μ {int((s > 0).sum())}/{len(s)}'
for h in (48, 0):
    lab = 'ΤΙΜΗ 48Ω ΠΡΙΝ' if h == 48 else 'ΚΛΕΙΣΙΜΟ'
    y0 = D[D.h == h]
    print(f'\n{"=" * 120}\n{lab} — Champions League κατηγορια Α · κελι = picks ανα βιβλιο · ROI · μοναδες · θετικες σεζον   [ολες 2022-26 │ νεα μορφη 2024-26]')
    print('Α. ΚΥΡΙΑ ΓΡΑΜΜΗ — κατωφλια live (φαβ/dog 10%, DNB 4%)')
    for role, nm in (('φαβ', 'φαβορι (≤−0.5)'), ('dog', 'αουτσαιντερ (≥+0.5)'), ('dnb', 'DNB (0)')):
        for lo, hi, zl in ((1.70, 2.10, 'ΜΕΣΑ στη ζωνη 1.70-2.10'), (2.10, 2.40, 'εκτος 2.10-2.40'), (2.40, 2.80, 'εκτος 2.40-2.80'), (2.80, 4.00, 'εκτος 2.80-4.00')):
            y = y0[(y0.role == role) & (y0.e >= y0.th) & (y0.o > lo) & (y0.o <= hi)] if lo > 1.70 else y0[(y0.role == role) & (y0.e >= y0.th) & (y0.o >= lo) & (y0.o <= hi)]
            print(f'   {nm:22s} {zl:24s} {cell(y)} │ {cell(y[y.sea.isin(NEW)])}')
    print('Β. ΓΡΑΜΜΕΣ −0.25 / +0.25 (σημερα εκτος), 1.70-2.10')
    for sgn, nm in ((-1, '−0.25 (μικρο φαβορι)'), (1, '+0.25 (μικρο αουτσαιντερ)')):
        for th in (.04, .10):
            y = y0[(y0.role == 'q25') & (np.sign(y0.ln) == sgn) & (y0.e >= th) & (y0.o >= 1.70) & (y0.o <= 2.10)]
            print(f'   {nm:24s} edge ≥{int(th * 100):2d}%          {cell(y)} │ {cell(y[y.sea.isin(NEW)])}')
    print('Δ. ΠΙΟ ΑΣΦΑΛΗΣ ΓΡΑΜΜΗ (+0.25 προς εμας) οταν η κυρια ειναι >2.10 — τιμη εκτιμημενη απο την αγορα')
    for th in (.04, .10):
        y = y0[(y0.o > 2.10) & (y0.o2 >= 1.70) & (y0.o2 <= 2.10) & (y0.e2 >= th)]
        print(f'   edge ≥{int(th * 100):2d}% στη νεα γραμμη    {cell(y, "pnl2")} │ {cell(y[y.sea.isin(NEW)], "pnl2")}   (μεση νεα τιμη {y.o2.mean():.2f})')
# Γ. ΑΠΛΗ ΝΙΚΗ (1Χ2)
X12 = {}
if os.path.exists('nowgoal_1x2_euro.jsonl'):
    for l in open('nowgoal_1x2_euro.jsonl', encoding='utf-8'):
        r = json.loads(l)
        if r.get('book') and r.get('close'): X12[str(r['mid'])] = r
W = []
for k_ in range(len(x)):
    r = X12.get(mids[k_])
    if not r: continue
    i = int(x.i[k_]); D_ = ES.eu_dist(x.lh[k_], x.la[k_], .85)
    ph = sum(p for g, p in D_.items() if g > 0); pa = sum(p for g, p in D_.items() if g < 0)
    for when in ('open', 'close'):
        o3 = r[when]
        for side, p, o in ((1, ph, o3[0]), (-1, pa, o3[2])):
            win = (GD[i] > 0) if side == 1 else (GD[i] < 0)
            W.append(dict(sea=x.sea[k_], bk=r['book'], when=when, o=o, e=p * (o - 1) * (1 - picks.MARGIN) - (1 - p), pnl=(o - 1) if win else -1.0))
W = pd.DataFrame(W)
print(f'\n{"=" * 120}\nΓ. ΑΠΛΗ ΝΙΚΗ (1Χ2) — {len(set(mids) & set(X12))} ματς με τιμες (Pinnacle κυριως) · [ολες │ νεα μορφη]')
if len(W):
    W['bk'] = 'x'
    for when, wl in (('open', 'ανοιγμα'), ('close', 'κλεισιμο')):
        for th in (.04, .10):
            for lo, hi in ((1.70, 2.10), (2.10, 2.60), (2.60, 3.50)):
                y = W[(W.when == when) & (W.e >= th) & (W.o > lo) & (W.o <= hi)]
                print(f'   {wl:9s} edge ≥{int(th * 100):2d}% αποδοση {lo:.2f}-{hi:.2f}  {cell(y)} │ {cell(y[y.sea.isin(NEW)])}')
# --- επικαλυψη με τα ηδη live picks χαντικαπ + t + ποιος παιζει (κλεισιμο, edge ≥10%, 2.10-3.50) ---
OV = []
for k_ in range(len(x)):
    r = X12.get(mids[k_])
    if not r: continue
    i = int(x.i[k_]); D_ = ES.eu_dist(x.lh[k_], x.la[k_], .85)
    ph = sum(p for g, p in D_.items() if g > 0); pa = sum(p for g, p in D_.items() if g < 0)
    c = snapT(mids[k_], 'Crown', 0) or snapT(mids[k_], 'SBOBET', 0)
    for side, p, o in ((1, ph, r['close'][0]), (-1, pa, r['close'][2])):
        e = p * (o - 1) * (1 - picks.MARGIN) - (1 - p)
        if not (e >= .10 and 2.10 < o <= 3.50): continue
        ah_pick = False; ln = None
        if c:
            L, oh, oa = c; ln = L if side == 1 else -L; oo = oh if side == 1 else oa
            if 1.70 <= oo <= 2.10:
                if ln >= 0.5: pw, pp = picks.p_cover(D_, side, ln); ah_pick = ed(pw, pp, oo) >= .10
                elif ln <= -0.5 or abs(ln) < .01: pw, pp = cover_q(D_, side, ln); ah_pick = ed(pw, pp, oo) >= (.10 if ln <= -0.5 else .04)
        win = (GD[i] > 0) if side == 1 else (GD[i] < 0)
        OV.append(dict(sea=x.sea[k_], home=side == 1, ln=ln, ahp=ah_pick, pnl=(o - 1) if win else -1.0, o=o))
OV = pd.DataFrame(OV)
tt = lambda v: v.mean() / (v.std() / np.sqrt(len(v)))
print(f'\nΓ2. ΑΠΛΗ ΝΙΚΗ κλεισιμο edge ≥10% αποδοση 2.10-3.50: {len(OV)} bets · ROI {100 * OV.pnl.mean():+.1f}% (t {tt(OV.pnl):.2f}) · νικες {100 * (OV.pnl > 0).mean():.0f}% · μεση αποδοση {OV.o.mean():.2f}')
for lab, f in (('ΚΑΙ pick χαντικαπ την ιδια ωρα', OV.ahp), ('ΧΩΡΙΣ pick χαντικαπ (νεα)', ~OV.ahp)):
    y = OV[f]; print(f'   {lab:32s} {len(y):3d} · ROI {100 * y.pnl.mean():+6.1f}% (t {tt(y.pnl):.2f}) · ' + ' '.join(f'{s}:{100 * v:+.0f}%' for s, v in y.groupby("sea").pnl.mean().items()))
for lab, f in (('γηπεδουχος', OV.home), ('φιλοξενουμενος', ~OV.home)):
    y = OV[f]; print(f'   {lab:32s} {len(y):3d} · ROI {100 * y.pnl.mean():+6.1f}%')
print('   ανα γραμμη χαντικαπ (της ιδιας ομαδας): ' + ' · '.join(f'{lab} {len(y)}: {100 * y.pnl.mean():+.0f}%' for lab, y in
      (('−0.25/0', OV[OV.ln.between(-0.3, 0.01)]), ('+0.25', OV[OV.ln.between(0.2, 0.3)]), ('+0.5', OV[OV.ln.between(0.45, 0.55)]), ('≥+0.75', OV[OV.ln >= 0.7]), ('≤−0.5', OV[OV.ln <= -0.45]))))
