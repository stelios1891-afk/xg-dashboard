# -*- coding: utf-8 -*-
"""el_star_absence_totals.py — EUROLEAGUE ΣΥΝΟΛΑ: ΜΑΤΣ ΜΕ ΑΠΟΥΣΙΑ ΣΗΜΑΝΤΙΚΟΥ ΣΚΟΡΕΡ — ΠΟΣΟ ΕΠΗΡΕΑΖΕΙ ΣΤΗΝ ΠΡΑΞΗ (27/10/2026, Στελιος «ψαξε
ιστορικα ματς συνολων με τουλ. 1 απουσια σημαντικου παικτη — με τι κριτηρια; μ.ο. ποντων; πρωτοι 2-3 σκορερς; — και πως απεδωσε»). ΠΕΡΙΓΡΑΦΙΚΟ.
1.563 ματς E2021-25 (ιδια βαση με el_absence_onoff_test / el_scoring_absence_test). Απουσια = live ορισμος (≥3/10 φετινα, λεπτα ≥10′, δεν επαιξε σημερα).
«ΣΗΜΑΝΤΙΚΟΣ» (μονο πληροφορια ΠΡΙΝ το ματς, τα 10 τελευταια ματς της ομαδας στη σεζον, ≥3 συμμετοχες, ≥20′ μ.ο.):
  Α = 1ος-2ος σκορερ της ομαδας (ποντοι/ματς) · Β = 1ος-3ος · Γ = ≥12 ποντοι/ματς.
Ομαδες ματς: 0 σημαντικοι απουσες (μετρο) · 1 · 2+ (και οι δυο ομαδες μαζι).
ΜΕΤΡΗΣΕΙΣ: πραγματικο − μοντελο (χωρις διορθωση απουσιων) · − ανοιγμα · − κλεισιμο · κινηση γραμμης · picks μας συνολων (live: μοντελο + on/off) Over/Under ·
  τυφλο Under στο ανοιγμα. + νεα/μακροχρονια απουσια (k 1-3 ματς ή 4-10). Εξοδος: el_star_absence_totals_out.txt"""
import sys, io, contextlib, collections
import numpy as np, pandas as pd
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open('el_scoring_absence_test.py', encoding='utf-8').read().split("FH = np.array([feats(r['ah'])")[0]
_a = "def P(s=''): print(s, flush=True); out.append(str(s))"; _i = src.rfind(_a); src = src[:_i] + "def P(s=''): pass" + src[_i + len(_a):]
ns = {}
with contextlib.redirect_stdout(_B()): exec(src, ns)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
inner = ns['ns']; rows, ys, SE, PL, HELD, YT = inner['rows'], inner['ys'], inner['SE'], inner['PL'], inner['HELD'], inner['YT']
from statistics import NormalDist
Phi = NormalDist().cdf
# ---- ποντοι/ματς ανα ομαδα-σεζον (προηγουμενα ματς) ----
TGP = collections.defaultdict(list)
for k, g in PL.items():
    if 'ph' not in g or 'pa' not in g or g.get('hs') is None: continue
    ts = pd.Timestamp(g['utc']).timestamp()
    for side, tc in (('ph', 'hcode'), ('pa', 'acode')):
        TGP[(g['season'], g[tc])].append((ts, {p[0]: (float(p[3] or 0), float(p[4] or 0)) for p in g[side]}))
for v in TGP.values(): v.sort(key=lambda x: x[0])
def team_rank(sea, team, ts):
    prev = [x for x in TGP.get((sea, team), []) if x[0] < ts - 3600][-10:]
    st = collections.defaultdict(lambda: [0, 0.0, 0.0])
    for _, d in prev:
        for pid, (mn, pt) in d.items():
            if mn > 0: s = st[pid]; s[0] += 1; s[1] += mn; s[2] += pt
    el = {pid: s[2] / s[0] for pid, s in st.items() if s[0] >= 3 and s[1] / s[0] >= 20}
    order = sorted(el, key=lambda p: -el[p]); return {pid: (i + 1, el[pid]) for i, pid in enumerate(order)}
# rows: χρειαζομαστε team codes → ξαναβρισκουμε απο το D (ιδια σειρα με rows δεν υπαρχει) — αποθηκευουμε απο τις απουσιες (sea, ts) & ομαδα
D, REC, NP = inner['D'], inner['REC'], inner['NP']
TEAMS = []
for pos, d_ in REC[23].items():
    sea = D.season.values[pos]
    if sea not in SE: continue
    hc, ac = D.home.values[pos], D.away.values[pos]; t = pd.Timestamp(D.t.values[pos]); key = (sea, hc, ac, t.strftime('%Y-%m-%d %H:%M'))
    if key not in NP or NP[key].get('t_new') is None or NP[key].get('h_new') is None: continue
    ah, aa = inner['absents'](sea, hc, t.timestamp()), inner['absents'](sea, ac, t.timestamp())
    if ah is None or aa is None: continue
    TEAMS.append((sea, hc, ac, t.timestamp()))
assert len(TEAMS) == len(rows), (len(TEAMS), len(rows))
def kinfo(p):                                  # w = λεπτα/40 × (1 ή .5) → k: νεα (1-3) αν w = πληρες
    return 'νεα' if True else ''
REC_ = []
for r, (sea, hc, ac, ts) in zip(rows, TEAMS):
    rk = {hc: team_rank(sea, hc, ts), ac: team_rank(sea, ac, ts)}
    flags = {'Α': 0, 'Β': 0, 'Γ': 0}; new = {'Α': 0, 'Β': 0, 'Γ': 0}
    for team, lst in ((hc, r['ah']), (ac, r['aa'])):
        for p in lst:
            x = rk[team].get(p['pid'])
            if not x: continue
            rank, ppg = x
            h = [m for t_, m in inner['PH'][p['pid']] if t_ < ts - 3600][-10:]; full = p['w'] >= np.mean(h) / 40 - 1e-9 if h else False
            for lab, ok in (('Α', rank <= 2), ('Β', rank <= 3), ('Γ', ppg >= 12)):
                if ok: flags[lab] += 1; new[lab] += full
    REC_.append(dict(flags=flags, new=new))
T0 = np.array([r['T'] for r in rows]); TOT = np.array([r['hs'] + r['as_'] for r in rows])
OP = np.array([r['op'][1] for r in rows]); CL = np.array([r['cl'][1] for r in rows]); LIN = np.array([r['op'][2] for r in rows])
OO = np.array([r['op'][3] for r in rows]); OU = np.array([r['op'][4] for r in rows])
W4 = HELD['W4 μονο on/off']
def pick_res(adj):                              # live picks (ανοιγμα, ≥8%): (πλευρα, αποτελεσμα) ανα ματς ή (0, nan)
    sd_, rs = np.zeros(len(rows)), np.full(len(rows), np.nan)
    for j, r in enumerate(rows):
        T_, oo, ou = r['op'][2], r['op'][3], r['op'][4]; t = r['T'] + adj[j]
        if abs(T_ - round(T_)) < 1e-9: po = 1 - Phi((T_ + .5 - t) / 16.7); pu = Phi((T_ - .5 - t) / 16.7)
        else: po = 1 - Phi((T_ - t) / 16.7); pu = 1 - po
        pp = 1 - po - pu; eo, eu = po * oo + pp - 1, pu * ou + pp - 1
        s, e, od = (1, eo, oo) if eo >= eu else (-1, eu, ou)
        if e < .08: continue
        x = (TOT[j] - T_) * s; sd_[j] = s; rs[j] = (od - 1) if x > 0 else (0 if x == 0 else -1)
    return sd_, rs
SDL, RSL = pick_res(W4)
xu = (LIN - TOT); BU = np.where(xu > 0, OU - 1, np.where(xu == 0, 0.0, -1.0))
def roi(m):
    if not m.any(): return '—'
    ps = pd.Series(RSL[m]).groupby(ys[m]).sum(); return f'{100 * np.nanmean(RSL[m]):+5.1f}% ({int(m.sum())}, θετ {int((ps > 0).sum())}/{len(ps)})'
def block(lab, m):
    pk = m & (SDL != 0)
    P(f'  {lab:22s} ματς {int(m.sum()):4d} · πραγμ − μοντελο {np.mean(TOT[m] - T0[m]):+5.2f} · − ανοιγμα {np.mean(TOT[m] - OP[m]):+5.2f} · − κλεισιμο {np.mean(TOT[m] - CL[m]):+5.2f}'
      f' · κινηση γραμμης {np.mean(CL[m] - OP[m]):+5.2f} · διορθωση on/off {np.mean(W4[m]):+5.2f}')
    P(f'  {"":22s} picks μας: ολα {roi(pk)} · Over {roi(pk & (SDL == 1))} · Under {roi(pk & (SDL == -1))} · τυφλο Under ανοιγμα {100 * BU[m].mean():+5.1f}%')
P(f'el_star_absence_totals · Ευρωλιγκα 2021-25 · ματς {len(rows)} · τιμες Crown (ανοιγμα/κλεισιμο) · μοντελο = live μηχανη χωρις διορθωση απουσιων')
for lab, nm in (('Α', '1ος-2ος σκορερ'), ('Β', '1ος-3ος σκορερ'), ('Γ', '≥12 ποντοι/ματς')):
    f = np.array([x['flags'][lab] for x in REC_]); nw = np.array([x['new'][lab] for x in REC_])
    P(f'\n=== ΟΡΙΣΜΟΣ {lab}: σημαντικος = {nm} (τα 10 τελευταια ματς της ομαδας, ≥3 συμμετοχες, ≥20′) ===')
    block('0 σημαντικοι απουσες', f == 0); block('1 σημαντικος', f == 1); block('2+ σημαντικοι', f >= 2)
    block('  ≥1, ΝΕΑ απουσια (1-3)', (f >= 1) & (nw >= 1)); block('  ≥1, μονο μακροχρονια', (f >= 1) & (nw == 0))
    P('  ανα σεζον (≥1 σημαντικος): πραγμ − κλεισιμο ' + ' · '.join(f"{s[-2:]}: {np.mean((TOT - CL)[(f >= 1) & (ys == s)]):+.2f} ({int(((f >= 1) & (ys == s)).sum())})" for s in SE))
open('el_star_absence_totals_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
