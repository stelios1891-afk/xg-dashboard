# -*- coding: utf-8 -*-
"""bk_steam_lag.py — STEAM «ΜΕ ΚΑΘΥΣΤΕΡΗΣΗ ΒΙΒΛΙΟΥ» (17/10/2026, συνεχεια bk_steam_follow). Το κλασικο steam-chasing: το ενα βιβλιο κινειται
απότομα (alert), το αλλο ΔΕΝ εχει ακομα ακολουθησει → πονταρεις στο αργο βιβλιο, στην παλια του τιμη.
ΠΡΟ-ΔΗΛΩΜΕΝΟ: ALERT = Crown κινηθηκε ≥1.5 π. σε 60′ (ιδιο με bk_steam_follow). Bet365 «δεν ακολουθησε» = η δικαιη τιμη του Bet365 στο alert+5′
  εχει κινηθει < μισο της κινησης του Crown (ιδια φορα) απο το ιδιο σημειο (alert − 60′). Ποντος στο Bet365 στο +5′ / +15′ / +60′.
  Αναστροφα: alert στο Bet365 → ποντος στο Crown. ΚΡΙΤΗΡΙΟ: ROI +5′ > 0, ≥ 2/3 σεζον θετικες, και στις 2 αγορες ή στις 3 διοργανωσεις.
Εξοδος: bk_steam_lag_out.txt"""
import sys, io, contextlib, math
import numpy as np, pandas as pd
_src = open('bk_steam_follow.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1).split("for cid in (3, 8):\n    print(f'\\n{\"#\"")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(_src)
sys.stdout.reconfigure(encoding='utf-8')

def lag_alerts(src, dst, X=1.5, W=3600):
    out = []
    for (c, ng, t, cb), (sea, rows) in SERIES.items():
        if cb != src: continue
        oth = SERIES.get((c, ng, t, dst))
        if not oth: continue
        orows = oth[1]; g = S[(c, ng)]; y = g['hs'] - g['as_'] if t == 21 else g['hs'] + g['as_']
        t0 = rows[0][0]
        for i in range(1, len(rows)):
            ts = rows[i][0]
            if ts - W < t0: continue
            dF = rows[i][4] - at(rows, ts - W)[4]
            if abs(dF) < X: continue
            sd = 1 if dF > 0 else -1
            ob = at(orows, ts - W); oa = at(orows, ts + 300) if ts + 300 < g['tip'] else None
            if ob is None or oa is None: break
            moved = sd * (oa[4] - ob[4])
            rec = dict(comp=c, sea=sea, t=t, side=sd, dF=dF, hrs=(g['tip'] - ts) / 3600, follow=moved / abs(dF), gap=sd * (rows[i][4] - oa[4]))
            cl = orows[-1]
            for lab, dl in (('+5′', 300), ('+15′', 900), ('+60′', 3600), ('κλεισιμο', None)):
                q = cl if dl is None else (at(orows, ts + dl) if ts + dl < g['tip'] else None)
                rec['pnl_' + lab] = np.nan if q is None else settle(y, q[1], q[2] if sd == 1 else q[3], sd)
                rec['clv_' + lab] = np.nan if q is None else sd * (cl[4] - q[4])
            rec['pnl_src'] = settle(y, rows[i][1], rows[i][2] if sd == 1 else rows[i][3], sd)
            out.append(rec); break
    return pd.DataFrame(out)

H2 = (f'   {"":34s} │ {"ROI +5′":>13s} {"+15′":>13s} {"+60′":>13s} {"κλεισιμο":>13s} │ {"θετ.σεζ":>7s} {"t":>5s} │ {"CLV +5′":>7s} {"διαφορα τιμης":>13s} │ {"ROI στο βιβλιο του alert":>24s}')
def r2(lab, y):
    if len(y) < 8: print(f'   {lab:34s} │ λιγα ({len(y)})'); return
    s = y.groupby('sea')['pnl_+5′'].mean(); s = s[y.groupby('sea').size() >= 5]
    print(f'   {lab:34s} │ {cell(y, "+5′"):>13s} {cell(y, "+15′"):>13s} {cell(y, "+60′"):>13s} {cell(y, "κλεισιμο"):>13s} │ {int((s > 0).sum())}/{len(s):<5d} '
          f'{tstat(y["pnl_+5′"]):5.2f} │ {y["clv_+5′"].mean():+7.2f} {y.gap.mean():+13.2f} │ {cell(y, "src"):>24s}')

for src, dst in ((3, 8), (8, 3)):
    A = lag_alerts(src, dst)
    print(f'\n{"#" * 140}\nALERT στο {BOOK[src]} (≥1.5 π. σε 60′) → ΠΟΝΤΟΣ στο {BOOK[dst]} · «διαφορα τιμης» = ποσους ποντους πιο φθηνα παιρνεις στο {BOOK[dst]}')
    for t, nm in ((21, 'ΧΑΝΤΙΚΑΠ'), (23, 'ΣΥΝΟΛΑ')):
        y0 = A[A.t == t]
        print(f'\n== {nm} ==\n{H2}')
        r2(f'ΟΛΑ τα alerts', y0)
        nf = y0[y0.follow < 0.5]
        r2(f'{BOOK[dst]} ΔΕΝ ακολουθησε (<½)', nf)
        r2(f'{BOOK[dst]} ακολουθησε (≥½)', y0[y0.follow >= 0.5])
        print(f'   — «δεν ακολουθησε», ανα διοργανωση / ωρα / μεγεθος —')
        for c, cn, _ in COMPS: r2(f'  {cn}', nf[nf.comp == c])
        for lab, lo, hi in (('6-24ω', 6, 24), ('2-6ω', 2, 6), ('<2ω', 0, 2)): r2(f'  {lab}', nf[(nf.hrs >= lo) & (nf.hrs < hi)])
        for lab, lo, hi in (('διαφορα τιμης 0.75-1.5', .75, 1.5), ('διαφορα τιμης ≥1.5', 1.5, 1e9)): r2(f'  {lab}', nf[(nf.gap >= lo) & (nf.gap < hi)])
        print(f'   — ανα σεζον («δεν ακολουθησε») —')
        for s in sorted(nf.sea.unique()): r2(f'  {s}', nf[nf.sea == s])
    A.to_pickle(f'bk_steam_lag_{BOOK[src]}_to_{BOOK[dst]}.pkl')
