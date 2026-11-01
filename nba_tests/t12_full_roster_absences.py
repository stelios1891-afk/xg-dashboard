# -*- coding: utf-8 -*-
"""t12_full_roster_absences.py — ΑΦΕΤΗΡΙΑ ΜΕ ΟΛΟΥΣ ΔΙΑΘΕΣΙΜΟΥΣ + ΚΑΘΕ ΑΠΟΥΣΙΑ ΙΔΙΑ (20/10/2026, Στελιος:
«η δυναμη της ομαδας ειναι Χ με ολους τους παικτες διαθεσιμους (ικανοτητα + ποιοι ηρθαν/εφυγαν)· αν καποιος λειπει 1 μηνα,
να μετραει σε καθε ματς ως εξω, οχι να εχει διαφορετικη αφετηρια η ομαδα»).
ΣΗΜΕΡΑ (LIVE-like, «C»): αφετηρια ροστερ = οσοι επαιξαν στο 1ο ματς (W1) · απουσια (0.75·(αξια+2)·λεπτα/48) ΜΟΝΟ για οσους επαιξαν φετος.
ΠΡΟΤΑΣΗ («S»): αφετηρια = ΟΛΟ το ροστερ (υγιεις + τραυματιες) · απουσια σε ΚΑΘΕ ματς που λειπει παικτης ρολου, και για οσους δεν
  εχουν παιξει ακομα φετος (ρολος = περσινα λεπτα/ματς ≥20, λεπτα = περσινα· μολις παιξει φετος → μ.ο. 10 τελευταιων, οπως το live).
  «Ολο το ροστερ» (χωρις ESPN ιστορικο) ≈ οσοι εμφανιστηκαν για την ομαδα στους 25 πρωτους αγωνες της ή ηταν εκει περσι, με το φιλτρο
  του live (περσινα λεπτα ή φετινος draft). Παραλλαγες: S-top12 (οι 12 με τα περισσοτερα περσινα λεπτα) · S-F10 (μονο 10 πρωτοι αγωνες).
Απουσια = ΔΕΝ επαιξε στον αγωνα (εκ των υστερων, ιδιο και για τις 2 εκδοχες — συγκρινουμε ΤΙΜΟΛΟΓΗΣΗ, οχι πληροφορια· ≈ λιστα ESPN Out).
Ανταλλαγη: παυει να μετραει μολις παιξει σε αλλη ομαδα. Μηχανη: production CFG_H + B2B 3.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (πριν το τρεξιμο, ιδιο με t3/t4/t11): η S περνα αν RMSE (ολα) καλυτερο απο τη C σε ≥4/5 σεζον ΚΑΙ ROI ανοιγματος
  edge ≥8% Οκτ-Δεκ οχι χειροτερο (> −1.5pp) ΚΑΙ ολης της σεζον οχι χειροτερο (> −1.5pp). Εξοδος: t12_full_roster_absences_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
ns = {'__file__': os.path.join(SC, 'ablate.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()):
    exec(open(os.path.join(SC, 'ablate.py'), encoding='utf-8').read().split("print(f'EVAL=")[0], ns)
    rs = open('nba_roster_adj2.py', encoding='utf-8').read().split('OUT = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
    NS = {}; exec(rs, NS)
sys.stdout.reconfigure(encoding='utf-8')
np = ns['np']; G = ns['G']; SEAS_G = ns['SEAS_G']; EV = ns['EV']; ACT = ns['ACT']; F = ns['F']; C = ns['C']
rm, roi_od, ALL, MKH = ns['rm'], ns['roi_od'], ns['ALL'], ns['MKH']
F._W['Z'] = {'C': ns['Cbundle'], 'P': ns['ZP']}
A_, MPT, GPT, shrunk, PJ, PID2NAME = NS['A'], NS['MPT'], NS['GPT'], NS['shrunk'], NS['PJ'], NS['PID2NAME']
REP, K = -2.0, 0.75
def v1(p, s):
    v = shrunk(p, s - 1); return v if v is not None else -1.0
def mpg1(p, s):
    return MPT[(p, s - 1)] / GPT[(p, s - 1)] if (p, s - 1) in MPT else None
def drafted(p, s): return (PJ['draft'].get(PID2NAME.get(p, '')) or [0])[0] == s - 1
dD = G.date.values.astype('datetime64[D]')
B2H = np.zeros(len(G)); B2A = np.zeros(len(G)); last = {}
GN = np.zeros(len(G), int); cnt = collections.Counter()
for i in np.argsort(dD, kind='stable'):
    s, h_, a_, d = SEAS_G[i], G.home.values[i], G.away.values[i], dD[i]
    B2H[i] = float(last.get((s, h_)) == d - np.timedelta64(1, 'D')); B2A[i] = float(last.get((s, a_)) == d - np.timedelta64(1, 'D'))
    last[(s, h_)] = d; last[(s, a_)] = d
    GN[i] = min(cnt[(s, h_)], cnt[(s, a_)]) + 1; cnt[(s, h_)] += 1; cnt[(s, a_)] += 1
EARLY = GN <= 15

# ---------- εμφανισεις ----------
A2 = A_.copy(); A2['d'] = ns['pd'].Series([np.datetime64(str(x)[:10], 'D') for x in A2.date], dtype=object, index=A2.index)
appear = collections.defaultdict(list)
for r in A2[['pid', 'team', 'd']].itertuples(index=False): appear[r.pid].append((r.d, r.team))
for v in appear.values(): v.sort()
def traded_away(p, t, d):
    """εχει παιξει για ΑΛΛΗ ομαδα πριν τη d, μετα την πρωτη του εμφανιση εδω (ή φετος πριν ερθει) → οχι πια δικος μας"""
    mine = [x for x in appear[p] if x[1] == t and x[0] < d]
    other = [x for x in appear[p] if x[1] != t and x[0] < d]
    if not other: return False
    return (not mine) or other[-1][0] > mine[-1][0]

def rosters(kind):
    """(s, t) → λιστα pid ροστερ αφετηριας"""
    out = {}
    for s in sorted(A2.s.unique()):
        if s - 1 not in set(A2.s): continue
        cur = A2[A2.s == s]; prev = A2[A2.s == s - 1]
        for t in sorted(cur.team.unique()):
            tg = cur[cur.team == t].sort_values(['date', 'GAME_ID']); gids = tg.GAME_ID.drop_duplicates().tolist()
            if kind == 'W1':
                out[(s, t)] = list(tg[tg.GAME_ID == gids[0]].pid.unique()); continue
            nwin = 10 if kind == 'F10' else 25
            early = set(tg[tg.GAME_ID.isin(gids[:nwin])].pid.unique())
            lastyr = set(prev[prev.team == t].pid.unique()) if kind != 'F10' else set()
            # περσινοι που ΔΕΝ ανταλλαχτηκαν: πρωτη φετινη εμφανιση εδω (ή καμια ακομα αλλα και καμια αλλου)
            # 20/10 ΔΙΟΡΘΩΣΗ (ελεγχος μετα το bug του t15): περσινος παικτης μενει στο ροστερ ΜΟΝΟ αν παιζει για την ομαδα καποια στιγμη ΦΕΤΟΣ
            # (πριν: εμεναν και οσοι αποσυρθηκαν / εμειναν ελευθεροι / πηγαν εξωτερικο → χρεωνονταν «απουσα» σε ΚΑΘΕ ματς → αδικο για την εκδοχη S)
            here = set(tg.pid.unique())
            keep_ly = {p for p in lastyr if p in here and not any(tt != t for dd, tt in appear[p] if dd > np.datetime64(f'{s - 1}-07-01'))}
            pids = [p for p in (early | keep_ly) if (p, s - 1) in MPT or drafted(p, s)]
            if kind == 'Ftop12': pids = sorted(pids, key=lambda p: -(mpg1(p, s) or 15.0))[:12]
            out[(s, t)] = pids
    return out
def tv(pids, s):
    vals = [(v1(p, s), mpg1(p, s) or 15.0) for p in pids]; w = np.array([x[1] for x in vals]); w = 5 * w / w.sum()
    return float(np.sum(w * np.array([x[0] for x in vals])))
def radj(R):
    out = {}
    for (s, t), pids in R.items():
        prev = A2[(A2.s == s - 1) & (A2.team == t)].groupby('pid').MIN.sum()
        old = float(np.sum(5 * prev.values / prev.values.sum() * np.array([v1(p, s) for p in prev.index]))) if len(prev) else 0.0
        out[f'{s}|{t}'] = tv(pids, s) - old
    return out
def absences(R, include_unplayed):
    """διορθωση γηπεδουχου ανα αγωνα (−: χανει ο γηπ)."""
    played = {(t, d): set(x.pid) for (t, d), x in A2.groupby(['team', 'd'])}
    hist = collections.defaultdict(list)                       # (s, t, pid) → λεπτα φετος για την ομαδα (μεχρι πριν τη μερα)
    for r in A2.sort_values('d')[['s', 'team', 'pid', 'd', 'MIN']].itertuples(index=False): hist[(r.s, r.team, r.pid)].append((r.d, r.MIN))
    adj = np.zeros(len(G)); nab = np.zeros(len(G))
    for i in range(len(G)):
        s, d = SEAS_G[i], dD[i]
        for side, t in ((1, G.home.values[i]), (-1, G.away.values[i])):
            if (t, d) not in played: continue
            pl = played[(t, d)]
            cand = set(R.get((s, t), []))
            # + οσοι εχουν ηδη παιξει φετος για την ομαδα (π.χ. ηρθαν με ανταλλαγη) — μεσω ROSTER_PLAYED/HFIRST πιο κατω
            tot = 0.0
            for p in cand | {p for p in ROSTER_PLAYED.get((s, t), ()) if HFIRST.get((s, t, p), d) < d}:
                if p in pl or traded_away(p, t, d): continue
                H = [m for dd, m in hist.get((s, t, p), []) if dd < d]
                if H:
                    avg = float(np.mean(H[-10:]))
                elif include_unplayed:
                    avg = mpg1(p, s) or 0.0
                else:
                    continue
                if avg < 20: continue
                tot += (v1(p, s) - REP) * avg / 48; nab[i] += 1
            adj[i] += -side * K * tot
    return adj, nab
ROSTER_PLAYED = collections.defaultdict(set); HFIRST = {}
for r in A2.sort_values('d')[['s', 'team', 'pid', 'd']].itertuples(index=False):
    ROSTER_PLAYED[(r.s, r.team)].add(r.pid); HFIRST.setdefault((r.s, r.team, r.pid), r.d)

out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def run(R2):
    C._RADJ2 = {'V0|W1': R2}
    _, mg, _, _ = F.run_all((0.8, 8, 60, .75, 5.0, 1.0, .75, .25)); return np.asarray(mg, float)
P('NBA · ΑΦΕΤΗΡΙΑ ΜΕ ΟΛΟΥΣ + ΚΑΘΕ ΑΠΟΥΣΙΑ ΙΔΙΑ (Στελιος) vs ΣΗΜΕΡΑ · 5 σεζον · αντικαταστατης −2 · απουσια = δεν επαιξε (ιδιο και στα 2)')
VER = {}
for lab, kind, inc in (('C  σημερα: W1 + απουσιες μονο φετινων', 'W1', False), ('S  ολο το ροστερ + ΟΛΕΣ οι απουσιες', 'Fall', True),
                       ('S-top12 (12 με τα περισσοτ. λεπτα)', 'Ftop12', True), ('S-F10 (ροστερ 10 πρωτων αγωνων)', 'F10', True),
                       ('Χ  ολο το ροστερ, απουσιες μονο φετινων', 'Fall', False)):
    R = rosters(kind); mg = run(radj(R)); ab, nab = absences(R, inc)
    VER[lab] = mg + 3.0 * (B2A - B2H) + ab
    P(f'  υπολογιστηκε: {lab} · μεσος αριθμος απωντων ρολου/ματς {nab[np.isin(SEAS_G, EV)].mean():.2f}')
base = VER['C  σημερα: W1 + απουσιες μονο φετινων']; base_s = {Y: rm(base, [Y]) for Y in EV}
CLS = np.full(len(G), np.nan)
for i, d in MKH.items():
    L, mk, o1, o2 = d['c']; CLS[i] = mk
P(''); P(f'{"εκδοχη":42s} | RMSE ολα | καλ. | αγων 1-15 | αποστ. κλεισ. | ROI Οκτ-Δεκ ≥8% (picks, μον., θετ.) | ROI ολη ≥8% (picks, μον., θετ.)')
RES = {}
for lab, v in VER.items():
    n1, r1, u1, ps1, _ = roi_od(v); n2, r2, u2, ps2, _ = roi_od(v, msk=ALL); RES[lab] = (r1, r2, ps1, ps2)
    bet = sum(rm(v, [Y]) < base_s[Y] - 1e-5 for Y in EV)
    P(f'{lab:42s} | {rm(v, EV):8.4f} | {bet}/5  | {rm(v, EV, EARLY):9.3f} | {rm(v, EV, np.isfinite(CLS), CLS):13.3f} | '
      f'{r1:+6.1f}% ({n1:4d}, {u1:+6.1f}u, {sum(ps1[Y] > 0 for Y in EV)}/5) | {r2:+6.1f}% ({n2:4d}, {u2:+6.1f}u, {sum(ps2[Y] > 0 for Y in EV)}/5)')
P('')
rb1, rb2 = RES['C  σημερα: W1 + απουσιες μονο φετινων'][:2]
for lab in [x for x in VER if x.startswith('S')]:
    v = VER[lab]; r1, r2 = RES[lab][:2]
    c1 = sum(rm(v, [Y]) < base_s[Y] - 1e-5 for Y in EV) >= 4; c2 = r1 - rb1 > -1.5; c3 = r2 - rb2 > -1.5
    P(f'ΚΡΙΤΗΡΙΑ {lab:36s}: (1) RMSE ≥4/5 {"✓" if c1 else "✗"} · (2) Οκτ-Δεκ {r1 - rb1:+.1f}pp {"✓" if c2 else "✗"} · (3) ολη {r2 - rb2:+.1f}pp {"✓" if c3 else "✗"} '
      f'→ {"ΠΕΡΝΑΕΙ" if c1 and c2 and c3 else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
P(''); P('ανα σεζον: RMSE και μοναδες Οκτ-Δεκ / ολη')
for lab, v in VER.items():
    r1, r2, ps1, ps2 = RES[lab]
    P(f'  {lab[:28]:28s} ' + ' · '.join(f'{Y}: {rm(v, [Y]):.3f} {ps1[Y]:+5.1f}u/{ps2[Y]:+5.1f}u' for Y in EV))
open(os.path.join(SC, 't12_full_roster_absences_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
