# -*- coding: utf-8 -*-
"""el_value_system_bigabs_test.py — ΧΑΝΤΙΚΑΠ Ευρωλιγκας: ποιο συστημα αξιας χειριζεται καλυτερα τις ΣΗΜΑΝΤΙΚΕΣ απουσιες
(23/10/2026, Στελιος «ναι» στον ορισμο). ΙΔΙΕΣ προβλεψεις (7 υποψηφιοι, LOSO) με el_value_system_page_test (ρεαλιστικη γνωση) και
el_value_system_test (πληρης γνωση)· αλλαζει ΜΟΝΟ το υποσυνολο ματς που κρινεται.
ΟΡΙΣΜΟΣ (με λεπτα, ουδετερος): λεπτα απουσιας ομαδας = Σ βαρος × μ.ο. λεπτων × g(k) (βαρος = 1 ή πιθ. GTD της σελιδας).
  ΚΥΡΙΟ «ανισορροπια ≥25′»: |λεπτα απουσιας γηπ − φιλ| ≥ 25 · ΔΕΥΤΕΡΟ «πολλες απουσιες»: ≥2 βασικοι (≥20′, k 1-3, βαρος ≥.5) ή ≥45′ συνολο.
ΚΡΙΤΗΡΙΑ (κυριο δειγμα, ρεαλιστικη γνωση): RMSE καλυτερο απο PIR ≥4/5 σεζον · μοναδες ≥ PIR & θετικες ≥4/5 · τυχη (καλυτερος απο 6) < 0.10.
Εξοδος: el_value_system_bigabs_test_out.txt"""
import os, sys, io, contextlib, math, time
import numpy as np
ROOT = r'C:\Users\steli\My Drive\Betting Model'; os.chdir(ROOT)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
T0 = time.time()
NS = {'__name__': 'p'}
with contextlib.redirect_stdout(_B()): exec(open('el_value_system_page_test.py', encoding='utf-8').read(), NS)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def save(): open('el_value_system_bigabs_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
V = NS['V']; SE, Yh, ysh, hrows, hkeys, gk, rmse, AB = V['SE'], V['Yh'], V['ysh'], V['hrows'], V['hkeys'], V['gk'], V['rmse'], NS['AB']
per_match = V['per_match']; NAME = V['NAME']
ORDER = ['1 PIR (live)', '2 απλο on/off', '3 RAPM', '4 δικο box', '5 συνδυασμος Σ', '6 PIR + αμυνα Σ', '7 PIR + Σ']
def masks(getter):
    imb = np.zeros(len(hrows), bool); many = np.zeros(len(hrows), bool); diff = np.zeros(len(hrows))
    for i in range(len(hrows)):
        (A_, H_) = getter(i)
        ma = sum(w * p['min'] * gk(p['k']) for p, w in A_); mh = sum(w * p['min'] * gk(p['k']) for p, w in H_)
        st = sum(1 for p, w in A_ + H_ if p['min'] >= 20 and p['k'] <= 3 and w >= .5)
        diff[i] = ma - mh; imb[i] = abs(ma - mh) >= 25; many[i] = st >= 2 or ma + mh >= 45
    return imb, many, diff
MR = masks(lambda i: AB[i])
MF = masks(lambda i: ([(p, 1.0) for p in hrows[i]['aa'] if gk(p['k']) > 0], [(p, 1.0) for p in hrows[i]['ah'] if gk(p['k']) > 0]))
SETS = {'ΡΕΑΛΙΣΤΙΚΗ γνωση': ({c: NS['CAND'][c][0] for c in ORDER}, MR), 'ΠΛΗΡΗΣ γνωση': ({c: V['CAND'][c][0] for c in ORDER}, MF)}
VERD = None
for know, (H, (imb, many, diff)) in SETS.items():
    for sub, m in (('ανισορροπια ≥25′', imb), ('πολλες απουσιες', many)):
        main = know.startswith('ΡΕΑΛ') and sub.startswith('ανισ')
        P(''); P(f'################ {know} · {sub}: {int(m.sum())} ματς ' + '(' + ' '.join(f'{s[-2:]}:{int((m & (ysh == s)).sum())}' for s in SE) + ')' + (' ← ΚΥΡΙΟ' if main else ' (πληροφορια)') + ' ################')
        hL = H[ORDER[0]]; uL, pkL, _ = per_match(hL); R = {}
        P(f'  {"υποψηφιος":18s} | RMSE υποσ. | ΔRMSE 21 22 23 24 25 (καλ.) | κλιση | picks | μοναδες | ROI    | θετ | πιο κοντα απο PIR | Δμον vs PIR ± σφ.')
        for c in ORDER:
            h = H[c]; u, pk, cl = per_match(h); d = [rmse(Yh - h, m & (ysh == s)) - rmse(Yh - hL, m & (ysh == s)) for s in SE]
            n = int(((pk != 0) & m).sum()); per = {s: u[m & (ysh == s)].sum() for s in SE}
            du = (u - uL)[m]; closer = np.mean(np.abs(Yh - h)[m] < np.abs(Yh - hL)[m]) if c != ORDER[0] else float('nan')
            sl = float(np.polyfit(h[m], Yh[m], 1)[0]) if np.std(h[m]) > 0 else float('nan')
            R[c] = dict(u=u, nb=sum(x < 0 for x in d), U=u[m].sum(), pos=sum(per[s] > 0 for s in SE))
            P(f'  {c:18s} | {rmse(Yh - h, m):.3f}     | ' + ' '.join(f'{x:+.3f}' for x in d) + f' ({R[c]["nb"]}/5) | {sl:5.2f} | {n:5d} | {u[m].sum():+7.1f} | {u[m].sum() / max(n, 1) * 100:+5.1f}% | '
              f'{R[c]["pos"]}/5 | ' + (f'{closer:.0%}' if c != ORDER[0] else '—') + ' | ' + (f'{du.sum():+6.1f} ± {du.std(ddof=1) * math.sqrt(len(du)):4.1f}' if c != ORDER[0] else '—'))
        C6 = ORDER[1:]
        Dm = np.c_[[(R[c]['u'] - uL)[m] for c in C6]].T; obs = Dm.sum(0); Dc = Dm - Dm.mean(0)
        rng = np.random.default_rng(20261023); MX = np.empty(5000)
        for b in range(5000): MX[b] = Dc[rng.integers(0, len(Dm), len(Dm))].sum(0).max()
        PV = {c: float(np.mean(MX >= obs[j])) for j, c in enumerate(C6)}
        P('  τυχη (καλυτερος απο 6, bootstrap 5000): ' + ' · '.join(f'{c.split(" ", 1)[1]} {PV[c]:.2f}' for c in C6))
        if main:
            VERD = []
            for c in C6:
                a = R[c]['nb'] >= 4; b = R[c]['U'] >= R[ORDER[0]]['U'] and R[c]['pos'] >= 4; d_ = PV[c] < 0.10
                VERD.append(f'  {c:18s} RMSE {R[c]["nb"]}/5 {"✓" if a else "✗"} · μοναδες {R[c]["U"]:+.1f} vs {R[ORDER[0]]["U"]:+.1f}, θετ {R[c]["pos"]}/5 {"✓" if b else "✗"} · τυχη {PV[c]:.2f} {"✓" if d_ else "✗"} → '
                            + ('ΧΕΙΡΙΖΕΤΑΙ ΚΑΛΥΤΕΡΑ' if a and b and d_ else 'οχι'))
            # παραδειγματα: 3 ματς με τη μεγαλυτερη ανισορροπια
            P('  ΠΑΡΑΔΕΙΓΜΑΤΑ (3 μεγαλυτερες ανισορροπιες· διορθωση απουσιων υπερ γηπεδουχου, ποντοι · πραγματικο − μοντελο χωρις απουσιες):')
            import datetime as dt
            for i in np.argsort(-np.abs(diff) * m)[:3]:
                sea, hc, ac, ts = hkeys[i]; A_, H_ = AB[i]
                ab = ', '.join(f'{NAME.get(p["pid"], p["pid"])} ({"γηπ" if side == "H" else "φιλ"} {p["min"]:.0f}′' + (f' ×{w:.2f}' if w < 1 else '') + ')' for side, L in (('H', H_), ('A', A_)) for p, w in L)
                P(f'    {sea} {hc}-{ac} {dt.datetime.fromtimestamp(ts, dt.timezone.utc):%Y-%m-%d} · ανισορροπια {diff[i]:+.0f}′ (+ = λειπουν περισσοτερα στον φιλοξ.) · αποντες: {ab}')
                P('      ' + ' · '.join(f'{c.split(" ", 1)[1]} {H[c][i]:+.2f}' for c in ORDER) + f' · ΠΡΑΓΜΑΤΙΚΟ {Yh[i]:+.1f}')
        save()
P(''); P('################ ΚΡΙΣΗ (κυριο: ρεαλιστικη γνωση, ανισορροπια ≥25′) ################')
for v in VERD: P(v)
P(f'\n(χρονος {time.time() - T0:.0f} δευτ.)'); save()
