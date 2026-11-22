# -*- coding: utf-8 -*-
"""t82_b2b_picks_split.py — (25/10/2026) Στελιος: «χθες με πολλα back-to-back δεν πηγαμε καλα (ουτε CLV ουτε αποτελεσματα)· πως αποδιδουμε
οταν ομαδες παιζουν back-to-back σε συγκριση με οταν παιζουν πρωτο ματς;»
ΠΕΡΙΓΡΑΦΙΚΟ (οχι κανονας): picks της LIVE μηχανης (ιδια βαση με t68: CFG_H + αφετηρια + 0.75·απουσιες + B2B 3 + ζωνη 0.68),
edge ≥8% στο ΑΝΟΙΓΜΑ Crown, 5 σεζον 2021-22…2025-26. Καθε pick χωριζεται απο τη ΜΕΡΙΑ ΜΑΣ:
  Α. 2ο ματς back-to-back (επαιξε χθες): εμεις / αντιπαλος / και οι δυο / κανεις
  Β. 1ο ματς back-to-back (παιζει ΚΑΙ αυριο — πιθανη ξεκουραση σταρ αυριο, πιθανη «φειδω» σημερα): εμεις / αντιπαλος
  Γ. Βραδια: ποσες ομαδες της βραδιας ειναι σε 2ο ματς B2B (0-2 / 3-5 / 6+)
Μετρησεις: ROI στην τιμη ανοιγματος, μοναδες, θετικες σεζον, CLV (ποντοι γραμμης ανοιγμα → κλεισιμο, + = υπερ μας).
Εξοδος: nba_tests/t82_b2b_picks_split_out.txt"""
import os, sys, collections
SC = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(SC, 't68_b2b_travel.py'), encoding='utf-8').read().rsplit('# ---------- ΠΕΡΙΓΡΑΦΙΚΟ ----------', 1)[0]
_src = _src.split('import os, sys, io, contextlib', 1)[1]
exec(_src)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))

# ---------- ημερες ως το ΕΠΟΜΕΝΟ ματς καθε ομαδας (1ο ματς back-to-back = αυριο ξαναπαιζει) ----------
NXT = np.full((N, 2), 99); nxt = {}
for i in np.argsort(dD, kind='stable')[::-1]:
    s, d = SEAS_G[i], dD[i]
    for j, t in enumerate((G.home.values[i], G.away.values[i])):
        if (s, t) in nxt: NXT[i, j] = int((nxt[(s, t)] - d).astype(int))
    for t in (G.home.values[i], G.away.values[i]): nxt[(s, t)] = d
# ομαδες σε 2ο ματς B2B ανα βραδια
nb2 = collections.Counter()
for i in range(N): nb2[(SEAS_G[i], str(dD[i])[:10])] += int(GAP[i, 0] == 1) + int(GAP[i, 1] == 1)

def picks(v, thr=.08):
    R = []
    for i, d in MKH.items():
        if SEAS_G[i] not in EV or not np.isfinite(v[i]): continue
        L, mk, o1, o2 = d['o']; Lc = d['c'][0]
        pw, pp, pl = cover(v[i], L, SIG)
        e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; s_, e, od_ = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e < thr: continue
        x = (ACT[i] + L) * s_; u = (od_ - 1) if x > 0 else (0 if x == 0 else -1)
        me, op = (0, 1) if s_ == 1 else (1, 0)
        mon = int(str(dD[i])[5:7])
        R.append(dict(i=i, sea=SEAS_G[i], u=u, clv=s_ * (L - Lc), od=mon in (10, 11, 12),
                      b2_me=GAP[i, me] == 1, b2_op=GAP[i, op] == 1, n1_me=NXT[i, me] == 1, n1_op=NXT[i, op] == 1,
                      night=nb2[(SEAS_G[i], str(dD[i])[:10])], fav=(L * s_) < 0))
    return pd.DataFrame(R)
D = picks(BASE)

def row(lab, d):
    if not len(d): P(f'   {lab:44s} —'); return
    ps = d.groupby('sea').u.sum()
    P(f"   {lab:44s} {100 * d.u.mean():+6.1f}% ({len(d):4d}, {d.u.sum():+6.1f}μ, θετ {int((ps > 0).sum())}/{d.sea.nunique()}) · CLV {d.clv.mean():+.2f} π."
      + ' · ' + ' '.join(f'{s % 100}:{ps.get(s, 0):+.0f}' for s in EV))
for per, M in (('ΟΚΤ-ΔΕΚ', D.od), ('ΟΛΗ Η ΣΕΖΟΝ', D.od | ~D.od)):
    d = D[M]
    P(f'\n================ {per} · picks edge ≥8% ανοιγμα Crown ================')
    row('ΟΛΑ', d)
    P('  Α. 2ο ματς back-to-back (επαιξε χθες)')
    row('κανεις', d[~d.b2_me & ~d.b2_op])
    row('ΕΜΕΙΣ σε B2B (ο αντιπαλος οχι)', d[d.b2_me & ~d.b2_op])
    row('ΑΝΤΙΠΑΛΟΣ σε B2B (εμεις οχι)', d[~d.b2_me & d.b2_op])
    row('ΚΑΙ ΟΙ ΔΥΟ σε B2B', d[d.b2_me & d.b2_op])
    P('  Β. 1ο ματς back-to-back (ξαναπαιζει αυριο)')
    row('κανεις δεν παιζει αυριο', d[~d.n1_me & ~d.n1_op])
    row('ΕΜΕΙΣ παιζουμε και αυριο (ο αντιπαλος οχι)', d[d.n1_me & ~d.n1_op])
    row('ΑΝΤΙΠΑΛΟΣ παιζει και αυριο (εμεις οχι)', d[~d.n1_me & d.n1_op])
    row('ΚΑΙ ΟΙ ΔΥΟ παιζουν και αυριο', d[d.n1_me & d.n1_op])
    P('  Γ. Βραδια: ομαδες σε 2ο ματς B2B εκεινη τη βραδια')
    for lo, hi in ((0, 2), (3, 5), (6, 99)): row(f'{lo}-{hi if hi < 99 else "+"} ομαδες', d[(d.night >= lo) & (d.night <= hi)])
    P('  Δ. 2ο ματς B2B × φαβορι/αουτσαιντερ (η πλευρα μας)')
    for f, lab in ((True, 'φαβορι'), (False, 'αουτσαιντερ')):
        row(f'{lab} · εμεις σε B2B', d[(d.fav == f) & d.b2_me & ~d.b2_op]); row(f'{lab} · αντιπαλος σε B2B', d[(d.fav == f) & ~d.b2_me & d.b2_op])
open(os.path.join(SC, 't82_b2b_picks_split_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
