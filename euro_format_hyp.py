"""
euro_format_hyp.py — 5/10/2026 (Στελιος): δυο υποθεσεις για τα ευρωπαικα φαβορι/γκολ.
 Υ1 ΦΟΡΜΑΤ: απο 2425 (league phase 36 ομαδων, διαφορα τερματων = 1ο κριτηριο μετα τους βαθμους) τα φαβορι κυνηγουν περισσοτερα γκολ,
    ενω παλια (ομιλοι, πρωτα η μεταξυ τους ισοβαθμια) το 1-0/2-0 αρκουσε. Ελεγχος: φαβορι κλεισιματος — περιθωριο νικης ΠΑΝΩ απο τη γραμμη
    (GD + γραμμη), P(νικη με 2+ / 3+), τυφλο ROI φαβορι, γκολ ΠΑΝΩ απο τη γραμμη συνολου & τυφλο over — ΠΑΛΙΟ (2122-2324) vs ΝΕΟ (2425-2526),
    ομιλοι/league phase vs νοκ-αουτ, ανα διοργανωση (UEL/UECL αλλαξαν ΚΑΙ αυτες φορματ το 2425 = ελεγχος).
 Υ2 «ΠΑΙΖΟΝΤΑΙ ΠΟΛΥ»: αν ο κοσμος φορτωνει φαβορι/over στο UCL, η γραμμη κινειται προς αυτα ανοιγμα→κλεισιμο και το ROI πεφτει.
Βιβλια Crown & SBOBET (nowgoal_odds), ματς με παραταση εξω. Περιγραφικο — τιποτα live.
"""
import os, sys, json, glob, datetime as dt
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
BOOK = {3: 'Crown', 31: 'SBOBET'}
M = {}
for f in glob.glob('data_Europe_*.json'):
    for mid, r in json.load(open(f, encoding='utf-8')).items():
        try: ko = dt.datetime.strptime(r['date'], '%a, %b %d, %Y, %H:%M UTC').replace(tzinfo=dt.timezone.utc)
        except Exception: continue
        if r.get('hs') is None or any((s.get('min') or 0) > 100 for s in r.get('shots') or []): continue
        M[str(mid)] = dict(ko=int(ko.timestamp()), mon=ko.month, gd=int(r['hs']) - int(r['as']), tg=int(r['hs']) + int(r['as']))
def pl(g):
    try:
        p = [float(x) for x in str(g).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception: return None
def settle_ou(tg, L, o):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; s = 0
    for x in parts:
        m = tg - x; s += ((o - 1) if m > .01 else (0 if abs(m) < .01 else -1)) / len(parts)
    return s
def series(lst, ko, sign):
    out = []
    for t, u, g, d in lst or []:
        gl = pl(g)
        try: out.append((int(t), sign * gl, float(u) + 1, float(d) + 1))
        except (TypeError, ValueError): pass
    return sorted(x for x in out if x[0] <= ko + 900)
rows = []
for f in sorted(glob.glob('nowgoal_odds/*_U*.jsonl')):
    sea, comp = os.path.basename(f)[:-6].split('_', 1)
    for ln in open(f, encoding='utf-8'):
        r = json.loads(ln); m = M.get(str(r['mid']))
        if not m or r['cid'] not in BOOK: continue
        A = series(r.get('ah'), m['ko'], -1); O = series(r.get('ou'), m['ko'], 1)
        if not A or not O: continue
        new = sea in ('2425', '2526')
        phase = 'KO' if (m['mon'] in (2, 3, 4, 5) or (m['mon'] == 1 and not new)) else 'ΟΜΙΛΟΙ/LEAGUE'
        a0, a1, o0, o1 = A[0], A[-1], O[0], O[-1]
        lh = a1[1]; side = 1 if lh < 0 else -1; L = -abs(lh); fo = a1[2] if side == 1 else a1[3]
        L0 = a0[1] * side          # γραμμη ανοιγματος απο τη σκοπια του φαβορι κλεισιματος
        fo0 = a0[2] if side == 1 else a0[3]
        gdf = side * m['gd']
        rows.append(dict(mon=m['mon'], sea=sea, comp=comp, fmt='ΝΕΟ' if new else 'ΠΑΛΙΟ', phase=phase, book=BOOK[r['cid']], L=L, fo=fo,
                         L0=L0, fo0=fo0, gdf=gdf, res=gdf + L, w2=gdf >= 2, w3=gdf >= 3, w1=gdf == 1,
                         roi=picks.settle(m['gd'], side, L, fo) if 1.70 <= fo <= 2.10 else np.nan,
                         roi0=picks.settle(m['gd'], side, L0, fo0) if (L0 <= -0.5 and 1.70 <= fo0 <= 2.10) else np.nan,
                         tl=o1[1], tres=m['tg'] - o1[1], ov=settle_ou(m['tg'], o1[1], o1[2]) if 1.70 <= o1[2] <= 2.10 else np.nan,
                         tl0=o0[1], ov0=settle_ou(m['tg'], o0[1], o0[2]) if 1.70 <= o0[2] <= 2.10 else np.nan))
D = pd.DataFrame(rows)
F = D[D.L <= -0.5]          # πραγματικα φαβορι (κλεισιμο ≤ −0.5)
def pct(x): return f'{100*x:+5.1f}%' if pd.notna(x) else '   —  '
def roi2(d, col):            # μεσος ορος Crown/SBOBET · σημαια αν διαφωνουν >5pp
    a = [d[d.book == b][col].dropna().mean() for b in BOOK.values()]
    m = np.nanmean(a); flag = '*' if all(pd.notna(a)) and abs(a[0] - a[1]) > .05 else ' '
    return pct(m) + flag
cr = lambda d: d[d.book == 'Crown']
print('Υ1 — ΦΑΒΟΡΙ ΚΛΕΙΣΙΜΑΤΟΣ (γραμμη ≤ −0.5). «πανω απο γραμμη» = μεση διαφορα τερματων φαβορι + γραμμη (0 = οσο περιμενε η αγορα)')
print('ROI = τυφλο φαβορι @1.70-2.10, μεσος Crown/SBOBET (* = διαφωνουν >5 μοναδες)')
for comp in ('UCL', 'UEL', 'UECL'):
    print(f'\n[{comp}]                 n   πανω απο γραμμη  νικη 2+  νικη 3+  ROI φαβορι | γκολ πανω απο συνολο  ROI over')
    for fmt in ('ΠΑΛΙΟ', 'ΝΕΟ'):
        for ph in ('ΟΜΙΛΟΙ/LEAGUE', 'KO', 'ΟΛΑ'):
            x = F[(F.comp == comp) & (F.fmt == fmt)]; y = D[(D.comp == comp) & (D.fmt == fmt)]
            if ph != 'ΟΛΑ': x = x[x.phase == ph]; y = y[y.phase == ph]
            c = cr(x); cy = cr(y)
            print(f'  {fmt:5s} {ph:14s} {len(c):4d}   {c.res.mean():+.2f} (±{c.res.std()/np.sqrt(max(len(c),1)):.2f})      {100*c.w2.mean():4.0f}%   {100*c.w3.mean():4.0f}%   {roi2(x, "roi")}   |  {cy.tres.mean():+.2f} (±{cy.tres.std()/np.sqrt(max(len(cy),1)):.2f})        {roi2(y, "ov")}')
print('\nανα σεζον (UCL, ομιλοι/league phase, Crown): πανω απο γραμμη · νικη 2+ · γκολ πανω απο συνολο')
for s in sorted(D.sea.unique()):
    c = cr(F[(F.comp == 'UCL') & (F.sea == s) & (F.phase == 'ΟΜΙΛΟΙ/LEAGUE')]); cy = cr(D[(D.comp == 'UCL') & (D.sea == s) & (D.phase == 'ΟΜΙΛΟΙ/LEAGUE')])
    print(f'  {s}: n{len(c):3d}  {c.res.mean():+.2f}  {100*c.w2.mean():3.0f}%  | γκολ {cy.tres.mean():+.2f} (n{len(cy)})')
print('\nΝΕΟ league phase: αγωνιστικες Σεπ-Δεκ vs Ιανουαριος (7η-8η, οταν η διαφορα τερματων κρινει θεσεις) — Crown, φαβορι')
for comp in ('UCL', 'UEL', 'UECL'):
    for lab, q in (('Σεπ-Δεκ', lambda d: d[d.mon != 1]), ('Ιαν (7η-8η)', lambda d: d[d.mon == 1])):
        x = q(F[(F.comp == comp) & (F.fmt == 'ΝΕΟ') & (F.phase == 'ΟΜΙΛΟΙ/LEAGUE')]); y = q(D[(D.comp == comp) & (D.fmt == 'ΝΕΟ') & (D.phase == 'ΟΜΙΛΟΙ/LEAGUE')])
        c = cr(x); cy = cr(y)
        print(f'  {comp:4s} {lab:12s} n{len(c):4d}  πανω απο γραμμη {c.res.mean():+.2f}  νικη 2+ {100*c.w2.mean():3.0f}%  νικη 3+ {100*c.w3.mean():3.0f}%  ROI φαβ {roi2(x, "roi")} | γκολ {cy.tres.mean():+.2f}  ROI over {roi2(y, "ov")}')
print('\nΥ2 — ΚΙΝΗΣΗ ΑΝΟΙΓΜΑ → ΚΛΕΙΣΙΜΟ (Crown): γραμμη φαβορι (αρνητικο = πηγε ΠΡΟΣ το φαβορι) · γραμμη συνολου (θετικο = πηγε προς over)')
print('                            n   κινηση χαντικαπ  % προς φαβορι  % κοντρα | κινηση συνολου  % προς over  % προς under | ROI φαβ ανοιγμα→κλεισιμο | ROI over ανοιγμα→κλεισιμο')
for comp in ('UCL', 'UEL', 'UECL'):
    for fmt in ('ΠΑΛΙΟ', 'ΝΕΟ', 'ΟΛΑ'):
        x = F[F.comp == comp]; y = D[D.comp == comp]
        if fmt != 'ΟΛΑ': x = x[x.fmt == fmt]; y = y[y.fmt == fmt]
        c = cr(x); cy = cr(y); mv = c.L - c.L0; tm = cy.tl - cy.tl0
        print(f'  {comp:4s} {fmt:5s}              {len(c):4d}   {mv.mean():+.3f}          {100*(mv < 0).mean():3.0f}%        {100*(mv > 0).mean():3.0f}%   |  {tm.mean():+.3f}        {100*(tm > 0).mean():3.0f}%        {100*(tm < 0).mean():3.0f}%      | {roi2(x, "roi0")} → {roi2(x, "roi")}   | {roi2(y, "ov0")} → {roi2(y, "ov")}')
