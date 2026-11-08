"""
euro_blind75_test.py — 5/10/2026 (Στελιος «τρεξτο»): ΠΡΟ-ΔΗΛΩΜΕΝΟ τεστ «ΤΥΦΛΟ φαβορι −0.75» στην Ευρωπη (UCL/UEL/UECL).
Αφορμη: euro_fav_quarters (29/9) — ολα τα φαβορι στο −0.75 @1.70-2.10, Crown closing, 2223-2526: n156 +11.4% 4/4, μοντελο δεν ξεχωριζει.
Κανονας: φαβορι γραμμης −0.75, τιμη 1.70-2.10, ΧΩΡΙΣ μοντελο. Βιβλια: Crown (cid 3) & SBOBET (cid 31) απο nowgoal_odds/*_U*.jsonl.
Χρονοι: closing (≤ σεντρα+15′), −24ω, −72ω (τελευταια γραμμη πριν απο τη στιγμη αυτη). Σεζον 2122 (ΑΘΙΚΤΗ) + 2223-2526.
Ελεγχοι: ιδιος κανονας στο −0.5 και −1.0. Ματς με παραταση εξαιρουνται (το σκορ FotMob περιλαμβανει παραταση· AH κρινεται στο 90′).
ΚΡΙΤΗΡΙΑ (δηλωμενα ΠΡΙΝ): (1) ROI>0 ΚΑΙ στα 2 βιβλια (closing) · (2) ≥4/5 σεζον θετικες (Crown closing) · (3) 2122 θετικη (Crown)
  · (4) θετικο στις 72ω (Crown) · (5) −0.75 καλυτερο απο −0.5 ΚΑΙ −1.0 (Crown closing). Ολα → ΠΕΡΝΑ, αλλιως ΚΛΕΙΝΕΙ. Live: τιποτα.
"""
import os, sys, json, glob, datetime as dt
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
BOOK = {3: 'Crown', 31: 'SBOBET'}
COMPN = {'UCL': 'UCL', 'UEL': 'UEL', 'UECL': 'UECL'}
M = {}; n_et = 0
for f in glob.glob('data_Europe_*.json'):
    for mid, r in json.load(open(f, encoding='utf-8')).items():
        try:
            ko = dt.datetime.strptime(r['date'], '%a, %b %d, %Y, %H:%M UTC').replace(tzinfo=dt.timezone.utc)
        except Exception:
            continue
        if r.get('hs') is None: continue
        et = any((s.get('min') or 0) > 100 for s in r.get('shots') or [])
        n_et += et
        M[str(mid)] = dict(ko=int(ko.timestamp()), gd=int(r['hs']) - int(r['as']), et=et)
def pl(g):
    try:
        p = [float(x) for x in str(g).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception:
        return None
rows = []
for f in sorted(glob.glob('nowgoal_odds/*_U*.jsonl')):
    sea, comp = os.path.basename(f)[:-6].split('_', 1)
    for ln in open(f, encoding='utf-8'):
        r = json.loads(ln); m = M.get(str(r['mid']))
        if not m or m['et'] or r['cid'] not in BOOK: continue
        H = []
        for t, u, g, d in r.get('ah') or []:
            gl = pl(g)
            try: H.append((int(t), -gl, float(u) + 1, float(d) + 1))
            except (TypeError, ValueError): pass
        H.sort()
        for win, cut in (('closing', m['ko'] + 900), ('24ω', m['ko'] - 24 * 3600), ('72ω', m['ko'] - 72 * 3600)):
            h = [x for x in H if x[0] <= cut]
            if not h: continue
            _, lh, oh, oa = h[-1]
            for side, L, o in ((1, lh, oh), (-1, -lh, oa)):
                if L in (-0.5, -0.75, -1.0) and 1.70 <= o <= 2.10:
                    rows.append(dict(mid=str(r['mid']), sea=sea, comp=comp, book=BOOK[r['cid']], win=win, line=L, odds=o,
                                     pnl=picks.settle(m['gd'], side, L, o)))
B = pd.DataFrame(rows)
def st(d):
    if len(d) < 3: return f'n{len(d):4d}' + ' ' * 30
    ps = d.groupby('sea').pnl.mean(); se = d.pnl.std() / np.sqrt(len(d))
    return f'n{len(d):4d} {100*d.pnl.mean():+6.1f}% (±{100*se:4.1f}) {d.pnl.sum():+6.1f}u {int((ps > 0).sum())}/{len(ps)}'
print(f'Ματς με σκορ: {len(M)} · εξαιρεθηκαν με παραταση: {n_et}')
for win in ('closing', '24ω', '72ω'):
    print(f'\n===== {win} — Crown | SBOBET =====')
    for L in (-0.75, -0.5, -1.0):
        for comp in ('ΟΛΑ', 'UCL', 'UEL', 'UECL'):
            x = B[(B.win == win) & (B.line == L)]
            if comp != 'ΟΛΑ': x = x[x.comp == comp]
            print(f'  {L:+.2f} {comp:5s} {st(x[x.book == "Crown"])} | {st(x[x.book == "SBOBET"])}')
print('\nΑΝΑ ΣΕΖΟΝ −0.75 ΟΛΑ (closing) — Crown | SBOBET')
for s in sorted(B.sea.unique()):
    x = B[(B.win == 'closing') & (B.line == -0.75) & (B.sea == s)]
    print(f'  {s}: {st(x[x.book == "Crown"])} | {st(x[x.book == "SBOBET"])}')
print('\nΑΝΑ ΣΕΖΟΝ −0.75 UCL (closing) — Crown | SBOBET')
for s in sorted(B.sea.unique()):
    x = B[(B.win == 'closing') & (B.line == -0.75) & (B.sea == s) & (B.comp == 'UCL')]
    print(f'  {s}: {st(x[x.book == "Crown"])} | {st(x[x.book == "SBOBET"])}')
# ΚΡΙΣΗ
for scope in ('ΟΛΑ', 'UCL'):
    def sub(win, L, book):
        x = B[(B.win == win) & (B.line == L) & (B.book == book)]
        return x if scope == 'ΟΛΑ' else x[x.comp == scope]
    c, s_ = sub('closing', -0.75, 'Crown'), sub('closing', -0.75, 'SBOBET')
    ps = c.groupby('sea').pnl.mean()
    k = [('ROI>0 και στα 2 βιβλια', c.pnl.mean() > 0 and s_.pnl.mean() > 0),
         ('≥4/5 σεζον θετικες', int((ps > 0).sum()) >= 4),
         ('2122 θετικη', ps.get('2122', -1) > 0),
         ('θετικο στις 72ω', sub('72ω', -0.75, 'Crown').pnl.mean() > 0),
         ('καλυτερο απο −0.5 και −1.0', c.pnl.mean() > max(sub('closing', -0.5, 'Crown').pnl.mean(), sub('closing', -1.0, 'Crown').pnl.mean()))]
    print(f'\nΚΡΙΣΗ [{scope}]: ' + ' · '.join(f"{a} {'✓' if b else '✗'}" for a, b in k) + f"  → {'ΠΕΡΝΑ' if all(b for _, b in k) else 'ΚΛΕΙΝΕΙ'}")
