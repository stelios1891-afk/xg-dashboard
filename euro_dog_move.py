# -*- coding: utf-8 -*-
"""euro_dog_move.py — 5/11/2026 (Στελιος: «προεκυψε νεο μπετ KuPS +1, προεκυψε απο κοντρα κινηση; πως απεδωσαν ιστορικα αυτα;»). Κανονες αουτσαιντερ (ισως και αλλοι), καθαρη μηχανη, 90′.
Για καθε pick: δικαιη υπεροχη υπερ της πλευρας μας στην ΠΡΩΤΗ τιμη ≤72ω vs στη στιγμη του pick (το μοντελο δεν αλλαζει, αρα η κινηση ειναι της αγορας). ΚΟΝΤΡΑ = η αγορα πηγε ≥0.10 γκολ κατα της πλευρας μας πριν μπουμε · ΥΠΕΡ = ≥0.10 υπερ · ΙΔΙΑ. Και: βγηκε απο την πρωτη τιμη ή αργοτερα."""
import sys
_src = open('euro_clean_rules.py', encoding='utf-8').read()
exec(_src[:_src.index('# ---------- ΧΑΝΤΙΚΑΠ LIVE')])
side_nf = lambda i: (1 if FMA[i] else -1)
def start(i, bk):
    for h in H_72:
        s = snap(MIDS[i], bk, h)
        if s: return h, fair(*s)
    return None, None
def classify(z):
    mv = []; lat = []
    for r in z.itertuples():
        h0, f0 = start(r.i, r.bk); f1 = fair(*snap(MIDS[r.i], r.bk, r.h))
        mv.append(r.side * (f1 - f0) if f0 is not None else np.nan); lat.append(h0 - r.h if h0 is not None else np.nan)
    return z.assign(mv=mv, lat=lat)
def sh(z):
    if not len(z): return '—'
    return f"{len(z) / 2:5.1f}p {100 * z.pnl.mean():+6.1f}% {units(z):+6.1f}μ ±{100 * z.groupby('i').pnl.mean().std() / np.sqrt(z.i.nunique()):4.1f} │ " + ' '.join(f"{s[2:]}:{100 * z[z.sea == s].pnl.mean():+.0f}" for s in SEAS if (z.sea == s).any()) + f" │ C{100 * z[z.bk == 'Crown'].pnl.mean():+.0f} S{100 * z[z.bk == 'SBOBET'].pnl.mean():+.0f} │ CLV μετα {z.clv.mean():+.3f} (t {tval(z.clv):+.1f}) │ xG {100 * z.xv.mean():+.1f}%"
for lab, p, t in (('UECL Β αουτσαιντερ ≥10%', seq_ah(P6['INS'], GD, ECB, 'dog', H_72, sidefn=side_nf), .10), ('UECL Α αουτσαιντερ ≥10%', seq_ah(P6['INS'], GD, ECA, 'dog', H_72), .10), ('UECL Α φαβορι ≥4%', seq_ah(P6['INS'], GD, ECA, 'fav', H_72), .04), ('UCL αουτσαιντερ ≥10% (72ω, 4 σεζον)', seq_ah(P6['INS'], GD, UCLA, 'dog', H_72), .10)):
    z = classify(at(p, t)); print(f'\n{lab}: ολα {sh(z)}')
    print(f'   ΚΟΝΤΡΑ (≥0.10 κατα μας)   {sh(z[z.mv <= -.10])}'); print(f'      εκ των οποιων ≥0.25    {sh(z[z.mv <= -.25])}')
    print(f'   ΙΔΙΑ                      {sh(z[z.mv.abs() < .10])}'); print(f'   ΥΠΕΡ (≥0.10 υπερ μας)     {sh(z[z.mv >= .10])}')
    print(f'   βγηκε στην πρωτη τιμη     {sh(z[z.lat == 0])}'); print(f'   βγηκε αργοτερα            {sh(z[z.lat > 0])}')
    print(f'   αργα (≤8ω) & κοντρα       {sh(z[(z.h <= 8) & (z.mv <= -.10)])}'); print(f'   αργα (≤8ω) & οχι κοντρα   {sh(z[(z.h <= 8) & (z.mv > -.10)])}')
    print(f'   εισοδος 12-6ω             {sh(z[(z.h <= 12) & (z.h >= 6)])}')
