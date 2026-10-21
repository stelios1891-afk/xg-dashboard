# -*- coding: utf-8 -*-
"""t48_news_prices.py — ΕΙΔΗΣΕΙΣ → ΤΙΜΕΣ (NBC, 2025-26) (21/10/2026, Στελιος «οκ ξεκινα»).
ΕΙΔΗΣΗ: NBC player news (nba_news/nbc_2526.jsonl) με τιτλο «εκτος» (out / will not play / will miss / ruled out) ή «παιζει»
  (will play / available / will return / off the injury report / cleared). Ωρα t0 = ωρα του αρχικου tweet/Bluesky (απο το ID) αν υπαρχει
  συνδεσμος, αλλιως η ωρα του NBC. Ματς = το επομενο ματς κανονικης περιοδου της ομαδας, τζαμπολ ≤36ω μετα το t0.
ΜΟΝΟ ΝΕΑ: «εκτος» μετρα αν η επισημη αναφορα ως το t0 ΔΕΝ τον ειχε Out · «παιζει» μετρα αν τον ειχε Out/Doubtful/Questionable.
  Παικτης ρολου (μ.ο. ≥20′ φετος στην ομαδα, οπως το live) · πρωτη ειδηση ανα παικτη/ματς/κατευθυνση.
ΑΞΙΑ (οπως live): χαντικαπ 0.75·(αξια+2)·λεπτα/48 · συνολα −0.5·επιθεση + 1.0·αμυνα (t35, odval) ·  «παιζει» = ιδια με αντιθετο προσημο.
ΓΡΑΜΜΕΣ: Crown (Nowgoal, καθε αλλαγη με ωρα) · δικαιη τιμη σε t0−60′/−15′/−5′/0/+1/+2/+5/+8/+10/+15/+30′ και κλεισιμο.
ΠΕΡΙΓΡΑΦΙΚΑ: ποσο της κινησης (ως το κλεισιμο) εχει γινει σε καθε στιγμη · κινηση ΠΡΙΝ το t0 · μεγεθος κινησης vs αξια.
ΣΤΡΑΤΗΓΙΚΗ Α (ΠΡΟ-ΔΗΛΩΜΕΝΗ, γραφτηκε πριν το τρεξιμο): ποντο στην πλευρα που ευνοει η ειδηση, στην τιμη Crown του t0+k (k = 1 «ταχυτητα X»,
  8 «ταχυτητα NBC», 15 «επισημη αναφορα»), οταν |αξια| ≥ 1.0 π. Χωριστα χαντικαπ / συνολα.
  ΠΕΡΝΑ (για k) αν: n ≥ 80 ΚΑΙ CLV > 0 ΚΑΙ ROI > 0 ΚΑΙ θετικο ROI και στα 2 μισα της σεζον (Οκτ-Ιαν / Φεβ-Απρ).
  Αξια «X αντι NBC» = μοναδες(k=1) − μοναδες(k=8).
ΣΤΡΑΤΗΓΙΚΗ Β (περιγραφικη): ιδια, μονο οταν η ειδηση ειναι ΚΟΝΤΡΑ σε pick ανοιγματος του live μοντελου (edge ≥8%) → «καλυψη».
Εξοδος: t48_news_prices_out.txt"""
import os, sys, io, re, json, contextlib, collections, datetime as dt
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
g = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = g['np'], __import__('pandas'); nt = g['nt']
G, SEAS_G, dD, SER, SHIFT, ACT = g['G'], g['SEAS_G'], g['dD'], g['SER'], g['SHIFT'], g['ACT']
status_at, K2P, mins, value, nkey, line_at, VNO = g['status_at'], g['K2P'], g['mins'], g['value'], g['nkey'], g['line_at'], g['VNO']
abs_cost, W_A, cover_, SIG_ = g['abs_cost'], g['W_A'], g['cover_'], g['SIG_']
odval, mk_t, SIGT = nt['odval'], nt['mk_t'], nt['SIGT']; TOT = np.asarray(nt['TOT'], float)
S = 2026
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
# ---------- ειδησεις ----------
TM = {'BKN': 'BRK', 'CHA': 'CHO', 'PHX': 'PHO'}
RX_OUT = re.compile(r"\b(will not play|won.t play|ruled out|will miss|will sit|is out|are out|out for|not playing|will be held out|has been ruled out)\b", re.I)
RX_IN = re.compile(r"\b(will play|is available|will be available|will return|off the injury report|cleared to play|will make his return|upgraded to available|is playing|will suit up)\b", re.I)
B32 = '234567abcdefghijklmnopqrstuvwxyz'
def t_orig(r):
    url = next((s for s in (r.get('source') or []) if isinstance(s, str) and s.startswith('http')), '')
    m = re.search(r'(?:x|twitter)\.com/[^/]+/status/(\d+)', url)
    if m: return ((int(m.group(1)) >> 22) + 1288834974657) / 1000, 'X'
    m = re.search(r'bsky\.app/profile/[^/]+/post/([a-z2-7]{13})', url)
    if m:
        v = 0
        for c in m.group(1): v = v * 32 + B32.index(c)
        return (v >> 10) / 1e6, 'Bluesky'
    return None, None
GAMES = collections.defaultdict(list)                    # ομαδα → [(tip, i)] σεζον 2026
for i, (sw, tip, r21, r23) in SER.items():
    if int(SEAS_G[i]) != S: continue
    GAMES[G.home.values[i]].append((tip, i)); GAMES[G.away.values[i]].append((tip, i))
for k in GAMES: GAMES[k].sort()
NEWS = [json.loads(l) for l in open(os.path.join(ROOT, 'nba_news/nbc_2526.jsonl'), encoding='utf-8')]
N = []; cnt = collections.Counter(); seen = set()
for r in sorted(NEWS, key=lambda x: x['ts']):
    h = r.get('headline') or ''
    if r.get('type') == 'Recap' or not r.get('player'): continue
    kind = 'out' if RX_OUT.search(h) else ('in' if RX_IN.search(h) else None)
    if not kind: continue
    cnt['κατηγορια ' + kind] += 1
    t = TM.get(r.get('team'), r.get('team')); tn = dt.datetime.fromisoformat(r['ts']).timestamp()
    to, src = t_orig(r)
    t0 = to if (to is not None and -300 < tn - to < 86400) else tn
    nxt = next(((tip, i) for tip, i in GAMES.get(t, []) if tip > t0), None)
    if not nxt or nxt[0] - t0 > 36 * 3600: cnt['χωρις ματς ≤36ω'] += 1; continue
    tip, i = nxt; d = dD[i]; k = nkey(r['player'])
    pid = K2P.get((k, t, S)); m = mins(pid, t, S, d) if pid is not None else None
    if pid is None or m is None or m < 20: cnt['οχι παικτης ρολου'] += 1; continue
    st0 = status_at(t, d, t0).get(k)
    if kind == 'out' and st0 == 'Out': cnt['ηδη Out στην αναφορα'] += 1; continue
    if kind == 'in' and st0 not in ('Out', 'Doubtful', 'Questionable'): cnt['«παιζει» χωρις να ηταν αμφιβολος'] += 1; continue
    key = (k, i, kind)
    if key in seen: cnt['διπλη'] += 1; continue
    seen.add(key)
    sgn = 1.0 if kind == 'out' else -1.0
    hc = sgn * 0.75 * (value(pid, S - 1) + 2.0) * m / 48            # ποντοι που ΧΑΝΕΙ η ομαδα (out +)
    o_, d_ = odval(pid, S - 1); tt = sgn * (-0.5 * (o_ + 0.5) * m / 48 + 1.0 * (d_ + 0.5) * m / 48)   # + = περισσοτεροι ποντοι
    home = G.home.values[i] == t
    N.append(dict(i=i, t0=t0, tn=tn, src=src or 'NBC', kind=kind, team=t, home=home, player=r['player'], mins=m, hc=hc, tt=tt,
                  st0=st0, hrs=(tip - t0) / 3600, mon=int(G.date.dt.month.values[i]), tip=tip))
    cnt['ΚΡΑΤΗΘΗΚΕ'] += 1
P('ΕΙΔΗΣΕΙΣ NBC 2025-26 · ' + ' · '.join(f'{k} {v}' for k, v in cnt.items()))
D = pd.DataFrame(N)
P(f'κρατηθηκαν {len(D)} · εκτος {int((D.kind == "out").sum())} / παιζει {int((D.kind == "in").sum())} · ωρα απο tweet {100 * (D.src != "NBC").mean():.0f}% · '
  f'ωρες πριν το τζαμπολ: διαμεσος {D.hrs.median():.1f} · <3ω {100 * (D.hrs < 3).mean():.0f}% · |αξια χαντικαπ| ≥1 π. {int((D.hc.abs() >= 1).sum())} · |αξια συνολου| ≥1 π. {int((D.tt.abs() >= 1).sum())}')
# ---------- γραμμες ----------
def rows_of(i, which):
    sw, tip, r21, r23 = SER[i]; rr = r21 if which == 'h' else r23
    rr = [[x[0] + SHIFT] + list(x[1:]) for x in (rr or [])]; return [x for x in rr if x[0] <= tip + 900], sw
def at_h(i, tau):
    rr, sw = rows_of(i, 'h'); ln = line_at(rr, tau, sw)
    return None if not ln else dict(L=ln[0], oh=ln[1], oa=ln[2], fair=ln[3], ts=ln[4])     # fair = αναμενομενη διαφορα γηπ
def at_t(i, tau):
    rr, _ = rows_of(i, 't'); pre = [x for x in rr if x[0] <= tau]
    if not pre: return None
    x = pre[-1]; return dict(T=float(x[1]), oo=1 + x[2], ou=1 + x[3], fair=mk_t(x), ts=x[0])
KS = (-60, -15, -5, 0, 1, 2, 5, 8, 10, 15, 30)
for mk, col, at, nm in (('h', 'hc', at_h, 'ΧΑΝΤΙΚΑΠ'), ('t', 'tt', at_t, 'ΣΥΝΟΛΑ')):
    P(''); P(f'################ {nm} ################')
    recs = []
    for r in D.itertuples(index=False):
        val = getattr(r, col)
        if abs(val) < 1.0: continue
        # κατευθυνση: χαντικαπ → + = καλο για την ΑΛΛΗ ομαδα απ' οτι ο παικτης (out)· σε ορους «δικαιη διαφορα γηπ»: out γηπ → μειωνεται
        dirn = (-1.0 if r.home else 1.0) if mk == 'h' else 1.0
        sgn = np.sign(val)                                              # χαντικαπ: + ομαδα χανει · συνολα: + περισσοτεροι ποντοι
        c = at(r.i, r.tip)
        if c is None: continue
        F = {}
        for k in KS:
            x = at(r.i, r.t0 + k * 60)
            F[k] = None if x is None or r.t0 + k * 60 > r.tip else x
        if F[0] is None: continue
        base = F[0]['fair']; mv = lambda x: dirn * sgn * (x['fair'] - base)      # κινηση προς την πλευρα της ειδησης (π.)
        rec = dict(i=r.i, t0=r.t0, nh=(dirn * sgn) > 0, mon=r.mon, kind=r.kind, val=abs(val), hrs=r.hrs, src=r.src, close=mv(c), **{f'm{k}': (mv(F[k]) if F[k] else np.nan) for k in KS})
        for k in (1, 8, 15):
            x = F.get(k)
            if x is None: continue
            if mk == 'h':
                # πλευρα: αν η ειδηση βλαπτει τη γηπεδουχο (dirn·sgn < 0 σε ορους fair) → φιλοξενουμενη
                side_home = (dirn * sgn) > 0
                L, od = (x['L'], x['oh']) if side_home else (-x['L'], x['oa'])
                res_ = (ACT[r.i] + x['L']) * (1 if side_home else -1)
            else:
                side_over = sgn > 0; L = x['T']; od = x['oo'] if side_over else x['ou']
                res_ = (TOT[r.i] - x['T']) * (1 if side_over else -1)
            rec[f'r{k}'] = (od - 1) if res_ > 0 else (0.0 if res_ == 0 else -1.0)
            rec[f'c{k}'] = mv(c) - mv(x)                                  # CLV σε ποντους (κινηση απο το t0+k ως το κλεισιμο προς εμας)
        recs.append(rec)
    E = pd.DataFrame(recs)
    if not len(E): P('  —'); continue
    P(f'  ειδησεις με |αξια| ≥1 π. και ανοιχτη γραμμη: {len(E)} (εκτος {int((E.kind == "out").sum())} / παιζει {int((E.kind == "in").sum())}) · μεση αξια {E.val.mean():.1f} π.')
    P('  === ΚΙΝΗΣΗ ΤΗΣ ΓΡΑΜΜΗΣ προς την πλευρα της ειδησης (π., σε σχεση με τη στιγμη του tweet/t0) ===')
    P('    ' + ' · '.join(f"{('+' if k > 0 else '') + str(k)}′ {E[f'm{k}'].mean():+.2f}" for k in KS) + f' · κλεισιμο {E.close.mean():+.2f} (αξια {E.val.mean():.2f})')
    sh = E[E.close.abs() > 0.25]
    P('    % της τελικης κινησης που εχει γινει: ' + ' · '.join(f"+{k}′ {100 * np.nanmedian(sh[f'm{k}'] / sh.close):.0f}%" for k in (1, 2, 5, 8, 10, 15, 30)) + f'  (διαμεσος, n {len(sh)})')
    pre = E['m-15'].dropna()
    P(f'    κινηση ΠΡΙΝ το tweet (−15′ → 0): {(-pre).mean():+.2f} π. · {100 * (-pre > 0.4).mean():.0f}% των ειδησεων ειχαν ηδη κινηση ≥0.5 π. προς την ειδηση')
    for lab, m_ in (('απο tweet (X/Bluesky)', E.src != 'NBC'), ('μονο ωρα NBC', E.src == 'NBC'), ('<3ω πριν', E.hrs < 3), ('3-12ω', (E.hrs >= 3) & (E.hrs < 12)), ('≥12ω', E.hrs >= 12),
                    ('εκτος', E.kind == 'out'), ('παιζει', E.kind == 'in')):
        x = E[m_]
        if len(x): P(f'    {lab:22s} n {len(x):4d} · +1′ {x.m1.mean():+.2f} · +8′ {x.m8.mean():+.2f} · +15′ {x.m15.mean():+.2f} · κλεισιμο {x.close.mean():+.2f} · αξια {x.val.mean():.2f}')
    P('  === ΣΤΡΑΤΗΓΙΚΗ Α: ποντο στην πλευρα της ειδησης στο t0+k ===')
    for k, lab in ((1, 'ταχυτητα X (+1′)'), (8, 'ταχυτητα NBC (+8′)'), (15, '+15′')):
        x = E.dropna(subset=[f'r{k}'])
        h1, h2 = x[x.mon.isin((10, 11, 12, 1))], x[x.mon.isin((2, 3, 4))]
        roi = 100 * x[f'r{k}'].mean(); ok = len(x) >= 80 and x[f'c{k}'].mean() > 0 and roi > 0 and h1[f'r{k}'].mean() > 0 and h2[f'r{k}'].mean() > 0
        P(f'    {lab:20s} n {len(x):4d} · ROI {roi:+6.1f}% · μοναδες {x[f"r{k}"].sum():+6.1f} · CLV {x[f"c{k}"].mean():+.2f} π. · Οκτ-Ιαν {100 * h1[f"r{k}"].mean():+.1f}% ({len(h1)}) · Φεβ-Απρ {100 * h2[f"r{k}"].mean():+.1f}% ({len(h2)}) → {"ΠΕΡΝΑ" if ok else "ΔΕΝ περνα"}')
        for lab2, m_ in (('  εκτος', x.kind == 'out'), ('  παιζει', x.kind == 'in'), ('  αξια ≥2 π.', x.val >= 2), ('  <3ω πριν', x.hrs < 3)):
            y = x[m_]
            if len(y): P(f'      {lab2:16s} n {len(y):4d} · ROI {100 * y[f"r{k}"].mean():+6.1f}% · CLV {y[f"c{k}"].mean():+.2f}')
    x1, x8 = E.dropna(subset=['r1', 'r8']), None
    P(f'    αξια «X αντι NBC» (ιδιες ειδησεις): μοναδες +1′ {x1.r1.sum():+.1f} vs +8′ {x1.r8.sum():+.1f} → {x1.r1.sum() - x1.r8.sum():+.1f} μοναδες · CLV {x1.c1.mean():+.2f} vs {x1.c8.mean():+.2f} π.')
    if mk == 'h':
        # ΣΤΡΑΤΗΓΙΚΗ Β: picks ανοιγματος live (edge ≥8%, μοντελο οπως t22 Α) και ειδηση ΚΟΝΤΡΑ
        B = []
        for r in E.itertuples(index=False):
            rr, sw = rows_of(r.i, 'h')
            if not rr or rr[0][0] >= r.t0: continue
            o = line_at(rr, rr[0][0], sw); h_, a_, d_ = G.home.values[r.i], G.away.values[r.i], dD[r.i]
            ch, _ = abs_cost(h_, d_, S, rr[0][0], W_A); ca, _ = abs_cost(a_, d_, S, rr[0][0], W_A); mu = VNO[r.i] - ch + ca
            pw, pp, pl = cover_(mu, o[0], SIG_); e1, e2 = pw * o[1] + pp - 1, pl * o[2] + pp - 1
            if max(e1, e2) < .08: continue
            pick_home = e1 >= e2
            x = (ACT[r.i] + o[0]) * (1 if pick_home else -1); od = o[1] if pick_home else o[2]
            pres = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0)
            B.append(dict(against=(pick_home != r.nh), pres=pres, r1=getattr(r, 'r1', np.nan), r8=getattr(r, 'r8', np.nan), r15=getattr(r, 'r15', np.nan)))
        B = pd.DataFrame(B)
        P(f'  === ΣΤΡΑΤΗΓΙΚΗ Β (περιγραφικη): ειδησεις σε ματς με pick ανοιγματος (live, ≥8%) ===')
        if len(B):
            for lab, m_ in (('ειδηση ΚΟΝΤΡΑ στο pick', B.against), ('ειδηση ΥΠΕΡ του pick', ~B.against)):
                y = B[m_]
                if len(y): P(f'    {lab:24s} n {len(y):3d} · το pick μονο του {100 * y.pres.mean():+.1f}% · καλυψη/ποντο στην ειδηση +1′ {100 * y.r1.mean():+.1f}% · +8′ {100 * y.r8.mean():+.1f}% · +15′ {100 * y.r15.mean():+.1f}%')
open(os.path.join(SC, 't48_news_prices_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
