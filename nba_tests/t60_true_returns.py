# -*- coding: utf-8 -*-
"""t60_true_returns.py — ΠΡΑΓΜΑΤΙΚΕΣ ΕΠΙΣΤΡΟΦΕΣ (22/10/2026, Στελιος: «μονο παικτες που ελειπαν για οποιονδηποτε λογο και στο επομενο ματς
ΟΝΤΩΣ επαιξαν· ποτε βγηκε η ειδηση (π.χ. ‘LeBron James is available’) και τι συμβαινει σε αυτο το ματς»).
ΟΡΙΣΜΟΣ: παικτης ρολου (μ.ο. ≥20′ στα φετινα του ματς με την ομαδα) που ΔΕΝ επαιξε στο αμεσως προηγουμενο ματς της ομαδας και ΕΠΑΙΞΕ
  σε αυτο (box λεπτα > 0) — 1ο ματς μετα την απουσια. Χωρις μεταγραφες (δεν επαιξε για αλλη ομαδα στο μεταξυ).
ΩΡΑ ΕΙΔΗΣΗΣ = η ΠΡΩΤΗ απο: (α) ειδηση NBC «παιζει/επιστρεφει» (ωρα αρχικου tweet αν υπαρχει) για το ματς, (β) η πρωτη επισημη αναφορα
  του ματς που τον εχει Available/Probable ή ΔΕΝ τον εχει καθολου (ενω υπαρχει αναφορα για την ομαδα). Questionable ΔΕΝ ειναι ειδηση επιστροφης.
  Ματς με >1 επιστρεφοντα στην ιδια ομαδα: ενα ρεκορ ανα ομαδα-ματς, αξια = αθροισμα, ωρα = η ΤΕΛΕΥΤΑΙΑ ειδηση (τοτε τα ξερεις ολα).
ΑΞΙΑ = οσο τον μετραει το live: 0.75·(περσινη αξια + 2)·λεπτα/48.
ΜΕΤΡΑΜΕ (πλευρα της ομαδας που επιστρεφει, τιμες Crown, ολα σε ποντους χαντικαπ):
  πριν = δικαιη γραμμη 1′ πριν την ειδηση · κινηση = πριν → κλεισιμο · πραγματικο = τελικη διαφορα − γραμμη «πριν»
  → «η αγορα κινηθηκε X απο τα Y της αξιας του, η ομαδα βελτιωθηκε στην πραγματικοτητα Z».
  + ποντος ΥΠΕΡ / ΚΟΝΤΡΑ στην ομαδα που επιστρεφει στην ειδηση+1′ και στο κλεισιμο (ROI, ανα σεζον).
  + μοντελο τη στιγμη της ειδησης (live αντιγραφο t22 με πιθανοτητες αναφορας): (τελικη − μοντελο) → μετραει σωστα την επιστροφη;
Περιγραφικο (οχι κανονας). Ανα ματς απουσιας (1 / 2-4 / 5-14 / 15+), ανα αξια, ανα πηγη ειδησης.
Εξοδος: t60_true_returns_out.txt"""
import os, sys, io, re, json, contextlib, collections, datetime as dt
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't50_news_5s.py'), encoding='utf-8').read().split("NEWS = [json.loads(l)")[0]
g = {'__file__': os.path.join(SC, 't50_news_5s.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = g['np'], g['pd']
G, SEAS_G, dD, SER, ACT, at_h, GAMES = g['G'], g['SEAS_G'], g['dD'], g['SER'], g['ACT'], g['at_h'], g['GAMES']
TM, RX_IN, t_orig, nkey, team_at, K2P, mins, value = g['TM'], g['RX_IN'], g['t_orig'], g['nkey'], g['team_at'], g['K2P'], g['mins'], g['value']
G22 = g['g']['g']
assert len(G22['G']) == len(G) and (G22['G'].home.values == G.home.values).all()
A2, REP_BY, VNO, status_at = G22['A2'], G22['REP_BY'], G22['VNO'], G22['status_at']
REP = set(G22['REP_SEASONS'])
PROB = {'star': {'Out': 1.0, 'Doubtful': .965, 'Questionable': .42, 'Probable': .04}, 'starter': {'Out': 1.0, 'Doubtful': .963, 'Questionable': .46, 'Probable': .07},
        'role': {'Out': 1.0, 'Doubtful': .962, 'Questionable': .547, 'Probable': .195}}
def p_out(stt, m): return PROB['star' if m >= 30 else ('starter' if m >= 20 else 'role')].get(stt, 0.0)
def abs_P(t, d, s, tau):
    c = 0.0
    for k, stt in status_at(t, d, tau).items():
        pid = K2P.get((k, t, s))
        if pid is None: continue
        m = mins(pid, t, s, d)
        if m is None or m < 20: continue
        c += p_out(stt, m) * 0.75 * (value(pid, s - 1) + 2.0) * m / 48
    return c
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
# ---- εμφανισεις ----
MIN = {}; APP = collections.defaultdict(list); KEY = {}; NM = {}
for r in A2.itertuples(index=False):
    MIN[(r.pid, r.team, r.dd)] = r.MIN; APP[(r.pid, r.team, int(r.s))].append(r.dd); KEY[r.pid] = r.k; NM[r.pid] = r.PLAYER_NAME
for k in APP: APP[k] = sorted(set(APP[k]))
BYP = collections.defaultdict(list)
for (pid, t, s), v in APP.items(): BYP[(pid, s)].append((t, v))
# ---- ειδησεις NBC «παιζει» → (κλειδι, i) : πρωτη ωρα ----
NEWS = [json.loads(l) for f in ('nba_news/nbc_hist.jsonl', 'nba_news/nbc_2526.jsonl') for l in open(os.path.join(ROOT, f), encoding='utf-8')]
NIN = {}
for r in NEWS:
    h = r.get('headline') or ''
    if r.get('type') == 'Recap' or not r.get('player') or not RX_IN.search(h): continue
    tn = dt.datetime.fromisoformat(r['ts']).timestamp(); to, _ = t_orig(r); t0 = to if (to is not None and -300 < tn - to < 86400) else tn
    dd_ = dt.datetime.fromtimestamp(t0, dt.timezone.utc); S = dd_.year + (1 if dd_.month >= 7 else 0)
    k = nkey(r['player']); t = team_at(k, S, t0)
    if t is None: continue
    nxt = next(((tip, i) for tip, i in GAMES.get((t, S), []) if tip > t0), None)
    if not nxt or nxt[0] - t0 > 36 * 3600: continue
    key = (k, nxt[1])
    if key not in NIN or t0 < NIN[key][0]: NIN[key] = (t0, 'tweet' if to is not None and -300 < tn - to < 86400 else 'NBC')
# ---- αναφορες ανα στιγμιοτυπο ----
def report_return_time(t, d, k, tip):
    """πρωτη αναφορα του ματς (≤ τζαμπολ) με τον παικτη Available/Probable ή ΕΚΤΟΣ λιστας."""
    snaps = collections.defaultdict(dict)
    for ep, kk, st in REP_BY.get((t, d), ()):
        if ep <= tip: snaps[ep][kk] = st
    for ep in sorted(snaps):
        st = snaps[ep].get(k)
        if st is None or st in ('Available', 'Probable'): return ep, ('αναφορα: εκτος λιστας' if st is None else f'αναφορα: {st}')
    return None, None
# ---- επιστροφες ----
REC = []
TEAM_PIDS = collections.defaultdict(set)
for (pid, t, s) in APP: TEAM_PIDS[(t, s)].add(pid)
for i in SER:
    s = int(SEAS_G[i]); d = dD[i]; tip = SER[i][1]
    if s not in REP: continue
    for t in (G.home.values[i], G.away.values[i]):
        prev = [ii for tp, ii in GAMES[(t, s)] if tp < tip]
        if not prev: continue
        prev_d = dD[prev[-1]]
        ret = []
        for pid in TEAM_PIDS[(t, s)]:
            if MIN.get((pid, t, d), 0) <= 0: continue                         # ΕΠΑΙΞΕ σε αυτο το ματς
            ap = [x for x in APP[(pid, t, s)] if x < d]
            if not ap or ap[-1] >= prev_d: continue                           # επαιξε και στο προηγουμενο → οχι επιστροφη
            if any(t2 != t and any(ap[-1] < x < d for x in v2) for t2, v2 in BYP[(pid, s)]): continue   # μεταγραφη
            m = mins(pid, t, s, d)
            if m is None or m < 20: continue
            missed = sum(1 for ii in prev if dD[ii] > ap[-1])
            k = KEY[pid]; tn = NIN.get((k, i)); tr, src_r = report_return_time(t, d, k, tip)
            cands = [(x[0], x[1]) for x in (tn,) if x] + ([(tr, src_r)] if tr else [])
            tnews, srcn = min(cands) if cands else (None, 'καμια ειδηση')
            ret.append(dict(pid=pid, name=NM[pid], m=m, missed=missed, val=0.75 * (value(pid, s - 1) + 2.0) * m / 48, tnews=tnews, src=srcn, mt=MIN[(pid, t, d)]))
        if ret: REC.append(dict(i=i, s=s, team=t, home=t == G.home.values[i], tip=tip, d=d, ret=ret))
rows = []
for r in REC:
    known = [x['tnews'] for x in r['ret'] if x['tnews'] is not None]
    if len(known) < len(r['ret']): tnews = None
    else: tnews = max(known)
    sg = 1.0 if r['home'] else -1.0                                           # + = υπερ της ομαδας που επιστρεφει
    c = at_h(r['i'], r['tip'] - 1)
    if c is None: continue
    base = dict(s=r['s'], val=sum(x['val'] for x in r['ret']), n=len(r['ret']), missed=max(x['missed'] for x in r['ret']),
                src=' + '.join(sorted({x['src'].split(':')[0] for x in r['ret']})), names=', '.join(f"{x['name']} ({x['missed']}μ, {x['mt']:.0f}′/{x['m']:.0f}′)" for x in r['ret']),
                date=str(r['d']), team=r['team'], hrs=(r['tip'] - tnews) / 3600 if tnews else np.nan, mt_ratio=np.mean([x['mt'] / x['m'] for x in r['ret']]))
    act = ACT[r['i']]
    if tnews is not None and tnews < r['tip']:
        b0 = at_h(r['i'], tnews - 60); b1 = at_h(r['i'], tnews + 60)
        if b0 is None or b1 is None: continue
        hh, aa = G.home.values[r['i']], G.away.values[r['i']]
        mod = VNO[r['i']] - abs_P(hh, r['d'], r['s'], tnews + 60) + abs_P(aa, r['d'], r['s'], tnews + 60)
        def bet(x, side):                                                       # side +1 = υπερ επιστρεφουσας
            hs = (sg * side) > 0; od = x['oh'] if hs else x['oa']; rr = (act + x['L']) * (1 if hs else -1)
            return (od - 1) if rr > 0 else (0.0 if rr == 0 else -1.0)
        base.update(news=True, move_news=sg * (b1['fair'] - b0['fair']), move=sg * (c['fair'] - b0['fair']), real=sg * (act - b0['fair']),
                    res_mkt=sg * (act - b1['fair']), res_close=sg * (act - c['fair']), res_mod=sg * (act - mod),
                    for1=bet(b1, 1), ag1=bet(b1, -1), forc=bet(c, 1), agc=bet(c, -1))
    else:
        base.update(news=False, res_close=sg * (act - c['fair']), forc=np.nan, agc=np.nan)
    rows.append(base)
E = pd.DataFrame(rows); N_ = E[E.news]
P(f'ΠΡΑΓΜΑΤΙΚΕΣ ΕΠΙΣΤΡΟΦΕΣ (ομαδα-ματς, 5 σεζον): {len(E)} · με ειδηση πριν το ματς {len(N_)} ({100 * len(N_) / len(E):.0f}%) · χωρις ειδηση {len(E) - len(N_)}')
P('  πηγη πρωτης ειδησης: ' + ' · '.join(f'{k} {v}' for k, v in N_.src.value_counts().items()))
P(f'  ωρες πριν το τζαμπολ που βγαινει η ειδηση: διαμεσος {N_.hrs.median():.1f}ω (25% {N_.hrs.quantile(.25):.1f} · 75% {N_.hrs.quantile(.75):.1f})')
P(f'  λεπτα στο ματς της επιστροφης / μεσος ορος πριν: {100 * E.mt_ratio.mean():.0f}%')
P('')
P('ΟΛΑ ΣΕ ΠΟΝΤΟΥΣ ΧΑΝΤΙΚΑΠ, ΠΡΟΣ ΤΗΝ ΟΜΑΔΑ ΠΟΥ ΕΠΙΣΤΡΕΦΕΙ:')
P('  αξια = ποσο τον μετραει το μοντελο · κινηση ειδησης = γραμμη 1′ πριν → 1′ μετα · κινηση ως κλεισιμο = 1′ πριν → κλεισιμο')
P('  πραγματικο = τελικη διαφορα − γραμμη 1′ πριν (ποσο καλυτερα επαιξε απο οσο ελεγε η αγορα ΠΡΙΝ την ειδηση)')
P('  υπολ. αγορας = τελικη − γραμμη κλεισιματος (+ = η αγορα την υποτιμησε) · υπολ. μοντελου = τελικη − μοντελο στην ειδηση')
def line(lab, x):
    if len(x) < 25: return
    se = lambda c: x[c].std() / np.sqrt(len(x))
    ps = x.groupby('s').agc.mean()
    P(f'  {lab:26s} n {len(x):4d} · αξια {x.val.mean():.2f} · κινηση ειδησης {x.move_news.mean():+.2f} · ως κλεισιμο {x.move.mean():+.2f}'
      f' · πραγματικο {x.real.mean():+.2f}±{se("real"):.2f} · υπολ. αγορας {x.res_close.mean():+.2f}±{se("res_close"):.2f} · υπολ. μοντελου {x.res_mod.mean():+.2f}±{se("res_mod"):.2f}')
    P(f'  {"":26s} ROI ΚΟΝΤΡΑ: ειδηση+1′ {100 * x.ag1.mean():+.1f}% · κλεισιμο {100 * x.agc.mean():+.1f}% (θετ. σεζον {int((ps > 0).sum())}/{x.s.nunique()})'
      f' · ROI ΥΠΕΡ: ειδηση+1′ {100 * x.for1.mean():+.1f}% · κλεισιμο {100 * x.forc.mean():+.1f}%')
line('ΟΛΕΣ με ειδηση', N_)
P('  ανα σεζον (πραγματικο / κινηση ως κλεισιμο / ROI κοντρα στο κλεισιμο): ' + ' · '.join(f'{s % 100}: {x.real.mean():+.2f}/{x.move.mean():+.2f}/{100 * x.agc.mean():+.0f}%' for s, x in N_.groupby('s')))
P('  ανα ματς απουσιας:')
for lab, mk in (('ελειψε 1', N_.missed == 1), ('ελειψε 2-4', (N_.missed >= 2) & (N_.missed <= 4)), ('ελειψε 5-14', (N_.missed >= 5) & (N_.missed <= 14)), ('ελειψε 15+', N_.missed >= 15)): line(lab, N_[mk])
P('  ανα αξια:')
for lab, mk in (('αξια <1', N_.val < 1), ('αξια 1-2', (N_.val >= 1) & (N_.val < 2)), ('αξια ≥2', N_.val >= 2)): line(lab, N_[mk])
P('  ανα πηγη:')
for sv in N_.src.unique(): line(sv, N_[N_.src == sv])
P('')
X_ = E[~E.news]
P(f'ΧΩΡΙΣ ειδηση πριν το ματς: n {len(X_)} · αξια {X_.val.mean():.2f} · υπολ. αγορας (τελικη − κλεισιμο) {X_.res_close.mean():+.2f}')
P('')
P('ΠΑΡΑΔΕΙΓΜΑΤΑ (8 τυχαια με ειδηση):')
for r in N_.sample(8, random_state=3).itertuples(index=False):
    P(f'  {r.date} {r.team}: {r.names} · ειδηση {r.hrs:.1f}ω πριν ({r.src}) · αξια {r.val:.2f} · κινηση ως κλεισιμο {r.move:+.1f} · πραγματικο {r.real:+.1f}')
open(os.path.join(SC, 't60_true_returns_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
