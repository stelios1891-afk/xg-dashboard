# -*- coding: utf-8 -*-
"""t83_rest_vs_injury_lines.py — ΞΕΚΟΥΡΑΣΗ vs ΤΡΑΥΜΑΤΙΣΜΟΣ: ΠΟΣΟ ΚΟΥΝΑΕΙ ΤΗ ΓΡΑΜΜΗ Η ΕΙΔΗΣΗ (25/10/2026, Στελιος «ναι κανε αυτη την αναλυση»).
Αφορμη 24/10: Houston (VanVleet/Adams ξεκουραση, 2ο ματς B2B) και Golden State (Curry «μαλλον οχι» στο 2ο ματς B2B) → η γραμμη ΔΕΝ
κουνηθηκε· Dallas (Kyrie γονατο, Christie/Risacher) → κουνηθηκε 2.5 π. Υποθεση: η αγορα βαζει την ξεκουραση του 2ου ματς B2B ΑΠΟ ΤΟ ΑΝΟΙΓΜΑ.
ΠΕΡΙΓΡΑΦΙΚΟ (οχι κανονας). Ειδησεις = ιδιες με t50 (NBC 2021-26, ωρα αρχικου tweet οπου υπαρχει, «εκτος», παικτης ρολου ≥20′, ματς ≤36ω,
ΝΕΑ σε σχεση με την επισημη αναφορα — οχι ηδη Out), αξια χαντικαπ 0.75·(αξια+2)·λεπτα/48 ≥ 0.5 π. Γραμμες Crown (Nowgoal).
ΛΟΓΟΣ: ΞΕΚΟΥΡΑΣΗ αν η ειδηση (τιτλος+αναλυση) γραφει rest / load management / maintenance / «second leg/half of back-to-back»
  Ή ο λογος στην επισημη αναφορα για το ματς περιεχει «Rest»· αλλιως ΤΡΑΥΜΑΤΙΣΜΟΣ/ΑΛΛΟ.
ΟΜΑΔΑ: 2ο ματς back-to-back (επαιξε χθες) ή οχι.
ΜΕΤΡΗΣΕΙΣ (ποντοι, + = κοντρα στην ομαδα που χανει τον παικτη):
  ΠΡΙΝ = κινηση απο το ΑΝΟΙΓΜΑ ως 5′ πριν την ειδηση (ποσο ειχε ηδη «μπει»)· ΜΕΤΑ = απο 5′ πριν την ειδηση ως το ΚΛΕΙΣΙΜΟ· και ως ποσοστο της αξιας.
Εξοδος: nba_tests/t83_rest_vs_injury_lines_out.txt"""
import os, sys, io, re, glob, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
_src = open(os.path.join(SC, 't50_news_5s.py'), encoding='utf-8').read().split('D = pd.DataFrame(N)')[0]
_src = _src.replace("st0=st0 or 'καθολου', hrs=(tip - t0) / 3600,", "st0=st0 or 'καθολου', txt=h + ' ' + str(r.get('analysis') or ''), k=k, hrs=(tip - t0) / 3600,")
assert "txt=h" in _src
G_ = {'__file__': os.path.join(SC, 't50_news_5s.py'), '__name__': 't50'}
with contextlib.redirect_stdout(_B()): exec(_src, G_)
sys.stdout.reconfigure(encoding='utf-8')
np, pd, at_h, rows_of, G, SEAS_G, dD = G_['np'], G_['pd'], G_['at_h'], G_['g']['rows_of'], G_['G'], G_['SEAS_G'], G_['dD']
D = pd.DataFrame(G_['N']); D = D[(D.kind == 'out') & (D.hc.abs() >= 0.5)].reset_index(drop=True)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))

# λογος απο την επισημη αναφορα (οποιαδηποτε αναφορα για το ματς)
REST_OFF = set()
for f in glob.glob(os.path.join(ROOT, 'nba_injrep', 'rows_*.csv')):
    R = pd.read_csv(f, usecols=['game_date', 'team', 'key', 'reason'])
    R = R[R.reason.astype(str).str.contains('Rest', case=False, na=False)]
    for gd, t, k in zip(R.game_date, R.team, R.key):
        try: REST_OFF.add((t, pd.Timestamp(gd).date().isoformat(), k))
        except Exception: pass
RX = re.compile(r'\brest\b|\brested\b|\bresting\b|load management|maintenance|(second|back) (leg|half|end) of (a |the |its |their )?back-to-back', re.I)
# 2ο ματς B2B ανα (ομαδα, ματς)
B2 = {}; last = {}
for i in np.argsort(dD, kind='stable'):
    s, d = SEAS_G[i], dD[i]
    for t in (G.home.values[i], G.away.values[i]):
        B2[(i, t)] = (s, t) in last and int((d - last[(s, t)]).astype(int)) == 1
        last[(s, t)] = d
rec = []
for r in D.itertuples(index=False):
    rr, _ = rows_of(r.i, 'h')
    if not rr: continue
    t_open = rr[0][0]
    if r.t0 - 300 <= t_open: continue                   # ειδηση πριν το ανοιγμα → δεν μετραει «πριν»
    o, b, c = at_h(r.i, t_open), at_h(r.i, r.t0 - 300), at_h(r.i, r.tip)
    if o is None or b is None or c is None: continue
    dirn = -1.0 if r.home else 1.0
    gd = str(dD[r.i])[:10]
    rest = bool(RX.search(r.txt)) or (r.team, gd, r.k) in REST_OFF
    rec.append(dict(S=r.S, val=abs(r.hc), pre=dirn * (b['fair'] - o['fair']), post=dirn * (c['fair'] - b['fair']),
                    rest=rest, b2=B2.get((r.i, r.team), False), st0=r.st0, hrs=r.hrs))
E = pd.DataFrame(rec)
P(f'ειδησεις «εκτος» (νεες, αξια ≥0.5 π., μετα το ανοιγμα Crown): {len(E)} · ξεκουραση {int(E.rest.sum())} · 2ο ματς B2B {int(E.b2.sum())}')
def line(lab, x):
    if len(x) < 5: P(f'   {lab:40s} n {len(x)}'); return
    se = lambda v: v.std(ddof=1) / np.sqrt(len(v))
    P(f"   {lab:40s} n {len(x):4d} · αξια {x.val.mean():4.2f} π. · ΠΡΙΝ (ανοιγμα→ειδηση) {x.pre.mean():+5.2f}±{se(x.pre):.2f} "
      f"({100 * x.pre.sum() / x.val.sum():+4.0f}% της αξιας) · ΜΕΤΑ (ειδηση→κλεισιμο) {x.post.mean():+5.2f}±{se(x.post):.2f} ({100 * x.post.sum() / x.val.sum():+4.0f}%)")
P('\n=== ΚΙΝΗΣΗ ΓΡΑΜΜΗΣ ΚΟΝΤΡΑ ΣΤΗΝ ΟΜΑΔΑ ΠΟΥ ΧΑΝΕΙ ΤΟΝ ΠΑΙΚΤΗ (ποντοι) ===')
for lab, m in (('ΞΕΚΟΥΡΑΣΗ · 2ο ματς B2B', E.rest & E.b2), ('ΞΕΚΟΥΡΑΣΗ · οχι B2B', E.rest & ~E.b2),
               ('ΤΡΑΥΜΑΤΙΣΜΟΣ · 2ο ματς B2B', ~E.rest & E.b2), ('ΤΡΑΥΜΑΤΙΣΜΟΣ · οχι B2B', ~E.rest & ~E.b2)):
    line(lab, E[m])
P('\n=== ΑΝΑ ΣΕΖΟΝ: ΠΡΙΝ / ΜΕΤΑ ως % αξιας ===')
pc = lambda x, c: 100 * x[c].sum() / max(x.val.sum(), 1e-9)
for lab, m in (('ΞΕΚΟΥΡΑΣΗ · 2ο B2B', E.rest & E.b2), ('ΞΕΚΟΥΡΑΣΗ · οχι B2B', E.rest & ~E.b2), ('ΤΡΑΥΜΑΤΙΣΜΟΣ · 2ο B2B', ~E.rest & E.b2), ('ΤΡΑΥΜΑΤΙΣΜΟΣ · οχι B2B', ~E.rest & ~E.b2)):
    P(f'   {lab:24s} ' + ' · '.join(f"{s % 100}: {pc(E[m & (E.S == s)], 'pre'):+4.0f}% / {pc(E[m & (E.S == s)], 'post'):+4.0f}% (n{int((m & (E.S == s)).sum())})" for s in sorted(E.S.unique())))
P('\n=== ΚΑΤΑΣΤΑΣΗ ΣΤΗΝ ΑΝΑΦΟΡΑ ΠΡΙΝ ΤΗΝ ΕΙΔΗΣΗ (ξεκουραση 2ο B2B / τραυματισμος) ===')
for st in ('καθολου', 'Available', 'Probable', 'Questionable', 'Doubtful'):
    line(f'ξεκουραση B2B ← {st}', E[E.rest & E.b2 & (E.st0 == st)]); line(f'τραυματισμος ← {st}', E[~E.rest & (E.st0 == st)])
open(os.path.join(SC, 't83_rest_vs_injury_lines_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
