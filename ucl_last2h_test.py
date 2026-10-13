# -*- coding: utf-8 -*-
"""ucl_last2h_test.py — CHAMPIONS LEAGUE: PICKS ΠΟΥ ΠΡΩΤΟΒΓΑΙΝΟΥΝ ΣΤΟ ΤΕΛΕΥΤΑΙΟ 2ΩΡΟ (13/10/2026, Στελιος «κανε και ενα τελευταιο τεστ
για πολυ κοντα στην εναρξη του αγωνα, δηλαδη το τελ 2ωρο»). Αναλογο του κανονα Ευρωλιγκας (χαντικαπ <2ω = καταγραφη).
Πηγη: ucl_bb_timing_alerts.pkl (σημερινοι κανονες, ΚΑΘΕ αλλαγη τιμης ≤72ω, Crown & SBOBET, μεσος ορος).
Περιγραφη: 2-1ω / 1ω-σεντρα (οι ενδεκαδες βγαινουν ~1ω πριν) · ROI στην εμφανιση, στο κλεισιμο · κινηση πριν/μετα · ανα βιβλιο & σεζον.
ΠΡΟ-ΔΗΛΩΜΕΝΟΣ ΚΑΝΟΝΑΣ: pick που πρωτοβγαινει < 2ω πριν τη σεντρα → καταγραφη. ΠΕΡΝΑ (ανα αγορα) αν ΟΛΑ:
  (1) κομμενα ROI < 0 ΚΑΙ χειροτερα απο οσα μενουν, στην εμφανιση ΚΑΙ στο κλεισιμο,
  (2) χειροτερα σε ≥3 σεζον (χαντικαπ, ολες οι σεζον) / και στις 2 σεζον νεας μορφης (συνολα) — σεζον με ≥1 κομμενο ανα βιβλιο,
  (3) ιδια φορα με οριο 1ω και 3ω, (4) μοναδες με τον κανονα ≥ χωρις, (5) χειροτερα ΚΑΙ στα 2 βιβλια.
Εξοδος: ucl_last2h_test_out.txt"""
import sys
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
X = pd.read_pickle('ucl_bb_timing_alerts.pkl')
NEW = ['2425', '2526']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
NAME = dict(fav='ΦΑΒΟΡΙ', dog='ΑΟΥΤΣΑΪΝΤΕΡ', over='OVER', under='UNDER')
def cell(d, col='pa'):
    if not len(d): return '—'
    g = d.groupby('bk')[col]; ps = d.groupby('sea')[col].mean()
    return f'{100*g.mean().mean():+6.1f}% ({g.size().mean():.0f}, {g.sum().mean():+5.1f}μ, {int((ps > 0).sum())}/{ps.size})'
def books(d, col='pa'):
    return ' '.join(f'{b[0]} {100*v:+.0f}' for b, v in d.groupby('bk')[col].mean().items()) if len(d) else '—'
def seas(d):
    return ' '.join(f'{s}:{100*v:+.0f}' for s, v in d.groupby('sea').pa.mean().items()) if len(d) else ''
P('CHAMPIONS LEAGUE · PICKS ΠΟΥ ΠΡΩΤΟΒΓΑΙΝΟΥΝ ΣΤΟ ΤΕΛΕΥΤΑΙΟ 2ΩΡΟ · μεσος Crown/SBOBET')
P('ROI στην εμφανιση (picks ανα βιβλιο, μοναδες, θετικες σεζον) | αν περιμενα κλεισιμο | κινηση πριν (72ω→εμφανιση, γκολ, − = κοντρα) | κινηση μετα | ανα βιβλιο | ανα σεζον')
for m, ss, sl, need in (('fav', None, 'ολες οι σεζον', 3), ('dog', None, 'ολες οι σεζον', 3),
                        ('fav', NEW, 'νεα μορφη', 2), ('dog', NEW, 'νεα μορφη', 2),
                        ('over', NEW, 'νεα μορφη', 2), ('under', NEW, 'νεα μορφη', 2), ('under', None, 'ολες οι σεζον (πλαισιο)', 3)):
    D = X[(X.mk == m) & (X.sea.isin(ss) if ss else True)]
    P(''); P(f'=== {NAME[m]} · {sl} ===')
    for lab, msk in (('2ω ως 1ω πριν', (D.hrs < 2) & (D.hrs >= 1)), ('τελευταια 1ω', D.hrs < 1), ('ΤΕΛΕΥΤΑΙΟ 2ΩΡΟ', D.hrs < 2),
                     ('2-6ω πριν', (D.hrs >= 2) & (D.hrs < 6)), ('νωριτερα (≥2ω)', D.hrs >= 2)):
        d = D[msk]
        P(f'  {lab:<16} {cell(d):<30} | {cell(d, "pc"):<30} | {d.mv.mean() if len(d) else 0:+.2f} | {d.mv_after.mean() if len(d) else 0:+.2f} | {books(d)} | {seas(d)}')
    res = {}
    for h in (2, 1, 3):
        cut = D[(D.hrs < h) & ~D.at_open]; keep = D.drop(cut.index)
        ys = [s for s in sorted(D.sea.unique()) if (cut.sea == s).sum() / 2 >= 1]
        worse = sum(1 for s in ys if cut[cut.sea == s].pa.mean() < keep[keep.sea == s].pa.mean())
        bw = len(cut) > 0 and all(cut[cut.bk == b].pa.mean() < keep[keep.bk == b].pa.mean() for b in ('Crown', 'SBOBET') if (cut.bk == b).any())
        res[h] = dict(cut=cut, keep=keep, worse=worse, ny=len(ys), bw=bw, u0=D.groupby('bk').pa.sum().mean(), u1=keep.groupby('bk').pa.sum().mean())
        P(f'  κανονας <{h}ω: κοβει {cell(cut)} · κλεισ {cell(cut, "pc")} | μενουν {cell(keep)} · κλεισ {cell(keep, "pc")} | '
          f'χειροτερα σε {worse}/{len(ys)} σεζον · βιβλια {"✓" if bw else "✗"} · μοναδες {res[h]["u0"]:+.1f} → {res[h]["u1"]:+.1f}')
    r = res[2]; c, k = r['cut'], r['keep']
    if not len(c):
        P('  ΚΡΙΣΗ: κανενα κομμενο'); continue
    c1 = c.pa.mean() < 0 and c.pc.mean() < 0 and c.pa.mean() < k.pa.mean() and c.pc.mean() < k.pc.mean()
    c2 = r['worse'] >= need
    c3 = all(len(res[h]['cut']) and res[h]['cut'].pa.mean() < res[h]['keep'].pa.mean() for h in (1, 3))
    c4 = r['u1'] >= r['u0']; c5 = r['bw']
    P(f'  ΚΡΙΣΗ <2ω: (1) {"✓" if c1 else "✗"} · (2) {r["worse"]}/{r["ny"]} σεζον (≥{need}) {"✓" if c2 else "✗"} · (3) 1ω & 3ω {"✓" if c3 else "✗"} · '
      f'(4) μοναδες {"✓" if c4 else "✗"} · (5) 2 βιβλια {"✓" if c5 else "✗"} → {"ΠΕΡΝΑ" if all((c1, c2, c3, c4, c5)) else "ΔΕΝ ΠΕΡΝΑ"}')
P(''); P('=== ΧΑΝΤΙΚΑΠ ΜΑΖΙ (φαβορι + αουτσαιντερ, οπως ο κανονας Ευρωλιγκας) ===')
for sl, ss in (('ολες οι σεζον', None), ('νεα μορφη', NEW)):
    D = X[X.mk.isin(['fav', 'dog']) & (X.sea.isin(ss) if ss else True)]
    c = D[D.hrs < 2]; k = D[D.hrs >= 2]
    P(f'  {sl:<14} τελευταιο 2ωρο {cell(c)} · κλεισ {cell(c, "pc")} | νωριτερα {cell(k)} · κλεισ {cell(k, "pc")} | {books(c)} | {seas(c)}')
open('ucl_last2h_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
