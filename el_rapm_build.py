# -*- coding: utf-8 -*-
"""el_rapm_build.py — ΕΥΡΩΛΙΓΚΑ ΒΗΜΑ 1: «διορθωμενο» on/off (RAPM) απο play-by-play (22/10/2026, Στελιος «ναι συμφωνω»).
1. Καθε ματς (el_pbp/*.json, απο el_pbp_fetch.py) → κομματια («stints») οπου οι 10 στο γηπεδο ΔΕΝ αλλαζουν: πεντα γηπ/φιλοξ,
   ποντοι και κατοχες καθε ομαδας (κατοχες = ΠΣ + 0.44·βολες − επιθ. ριμπ + λαθη, απο τις φασεις του PBP).
   Ελεγχος: λεπτα καθε παικτη απο την ανασυσταση vs λεπτα box (αναφερεται η αποκλιση).
2. RAPM ανα σεζον: για καθε κομματι 2 γραμμες (επιθεση γηπ / επιθεση φιλοξ): y = ποντοι/100 κατοχες − μεσος, X = +1 στους 5 επιθετικους
   (συντελεστης O), +1 στους 5 αμυνομενους (συντελεστης D: + = δεχεται περισσοτερα = κακη αμυνα), + εδρα. Βαρος = κατοχες, ridge λ.
3. ΣΤΑΘΕΡΟΤΗΤΑ (το κριτηριο πριν απο οποιοδηποτε τεστ στοιχηματος): συσχετιση ιδιου δεικτη σεζον S ↔ S+1, παικτες ≥500′ και στις δυο:
   PIR/40 · απλο on/off (καθαρο, απο τα ιδια κομματια) · RAPM καθαρο (O − D) για λ ∈ ΛΑΜ · RAPM O, D χωριστα.
   ΣΤΟΧΟΣ (απο πριν): ο νεος δεικτης να ειναι τουλαχιστον οσο σταθερος οσο το PIR/40 (αλλιως σταματαμε σε αυτο το βημα).
Cache: el_pbp_stints.pkl. Εξοδος: el_rapm_build_out.txt (+ el_rapm_season.json: RAPM ανα παικτη-σεζον, για τα επομενα βηματα)."""
import os, sys, json, glob, pickle, collections
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import lsqr
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__))
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def mmss(t):
    try: m, s = str(t).split(':'); return int(m) * 60 + int(s)
    except Exception: return None
Q = ('FirstQuarter', 'SecondQuarter', 'ThirdQuarter', 'ForthQuarter', 'ExtraTime')
def parse(fn):
    d = json.load(open(fn, encoding='utf-8')); b, p = d['box'], d['pbp']
    H, A = (p.get('CodeTeamA') or '').strip(), (p.get('CodeTeamB') or '').strip()
    box = {}; on = {H: set(), A: set()}; name = {}
    for st in b.get('Stats') or []:
        for x in st.get('PlayersStats') or []:
            pid = x['Player_ID'].strip(); tm = x['Team'].strip(); name[pid] = x['Player']
            box[pid] = dict(team=tm, sec=mmss(x.get('Minutes')) or 0, val=x.get('Valuation') or 0,
                            **{k: x.get(k) or 0 for k in ('Points', 'FieldGoalsMade2', 'FieldGoalsAttempted2', 'FieldGoalsMade3', 'FieldGoalsAttempted3',
                                                         'FreeThrowsMade', 'FreeThrowsAttempted', 'OffensiveRebounds', 'DefensiveRebounds', 'Assistances',
                                                         'Steals', 'Turnovers', 'BlocksFavour', 'BlocksAgainst', 'FoulsCommited', 'FoulsReceived', 'Plusminus')})
            if x.get('IsStarter') and tm in on: on[tm].add(pid)
    stints = []; secs = collections.Counter(); bad = 0
    cur = dict(pts={H: 0, A: 0}, fga={H: 0, A: 0}, fta={H: 0, A: 0}, orb={H: 0, A: 0}, to={H: 0, A: 0}, sec=0)
    def close():
        nonlocal cur, bad
        if cur['sec'] > 0 or any(cur['pts'].values()):
            if len(on[H]) == 5 and len(on[A]) == 5:
                poss = {t: cur['fga'][t] + 0.44 * cur['fta'][t] - cur['orb'][t] + cur['to'][t] for t in (H, A)}
                stints.append((tuple(sorted(on[H])), tuple(sorted(on[A])), cur['pts'][H], cur['pts'][A], poss[H], poss[A], cur['sec']))
            else: bad += cur['sec']
        cur = dict(pts={H: 0, A: 0}, fga={H: 0, A: 0}, fta={H: 0, A: 0}, orb={H: 0, A: 0}, to={H: 0, A: 0}, sec=0)
    for qi, k in enumerate(Q):
        plays = p.get(k) or []
        if not plays: continue
        prev = 600 if qi < 4 else 300
        for x in plays:
            t = mmss(x.get('MARKERTIME') or '')
            if t is not None and prev - t > 0:
                dtm = prev - t; cur['sec'] += dtm
                for S in on.values():
                    for pid in S: secs[pid] += dtm
                prev = t
            pt, tm, pid = x.get('PLAYTYPE'), (x.get('CODETEAM') or '').strip(), (x.get('PLAYER_ID') or '').strip()
            if tm not in on: continue
            if pt in ('IN', 'OUT'):
                close()
                (on[tm].add if pt == 'IN' else on[tm].discard)(pid); continue
            if pt == '2FGM': cur['pts'][tm] += 2; cur['fga'][tm] += 1
            elif pt == '3FGM': cur['pts'][tm] += 3; cur['fga'][tm] += 1
            elif pt in ('2FGA', '3FGA'): cur['fga'][tm] += 1
            elif pt == 'FTM': cur['pts'][tm] += 1; cur['fta'][tm] += 1
            elif pt == 'FTA': cur['fta'][tm] += 1
            elif pt == 'O': cur['orb'][tm] += 1
            elif pt == 'TO': cur['to'][tm] += 1
        if prev > 0:
            cur['sec'] += prev
            for S in on.values():
                for pid in S: secs[pid] += prev
        close()
    dev = [abs(secs[pid] - v['sec']) for pid, v in box.items() if v['sec'] > 0]
    return dict(season=d['season'], code=d['code'], H=H, A=A, stints=stints, box=box, name=name, bad=bad, dev=dev)
CACHE = os.path.join(ROOT, 'el_pbp_stints.pkl')
files = sorted(glob.glob(os.path.join(ROOT, 'el_pbp', '*.json')))
C = pickle.load(open(CACHE, 'rb')) if os.path.exists(CACHE) else {}
new = 0
for fn in files:
    k = os.path.basename(fn)[:-5]
    if k in C: continue
    try: C[k] = parse(fn); new += 1
    except Exception as e: P(f'  σφαλμα {k}: {type(e).__name__} {e}')
if new: pickle.dump(C, open(CACHE, 'wb'))
G = list(C.values()); SEAS = sorted({g['season'] for g in G})
NAME = {}
for g in G: NAME.update(g['name'])
P(f'ματς {len(G)} · σεζον {SEAS}')
for s in SEAS:
    x = [g for g in G if g['season'] == s]; dv = [v for g in x for v in g['dev']]
    badsec = sum(g['bad'] for g in x); tot = sum(st[6] for g in x for st in g['stints']) + badsec
    P(f'  {s}: ματς {len(x)} · κομματια {sum(len(g["stints"]) for g in x)} · χρονος χωρις 5+5 {100 * badsec / max(tot, 1):.2f}% · '
      f'λεπτα ανασυστασης vs box: μεση αποκλιση {np.mean(dv):.1f} δευτ. · >60 δευτ. {100 * np.mean(np.array(dv) > 60):.1f}% των παικτων-ματς')
# ---- ανα σεζον: λεπτα, PIR/40, απλο on/off, RAPM ----
LAM = (1000, 3000, 8000)
def season_metrics(s):
    x = [g for g in G if g['season'] == s]
    mins = collections.Counter(); val = collections.Counter(); team_of = {}
    for g in x:
        for pid, v in g['box'].items(): mins[pid] += v['sec'] / 60; val[pid] += v['val']; team_of[pid] = v['team']
    pir40 = {p: val[p] / mins[p] * 40 for p in mins if mins[p] > 0}
    rows, cols, vals, y, w = [], [], [], [], []
    idx = {}
    def ci(key):
        if key not in idx: idx[key] = len(idx)
        return idx[key]
    onp = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])            # pid → [ποντοι υπερ, κατ. υπερ, ποντοι κατα, κατ. κατα] ΜΕΣΑ
    team_tot = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    r = 0; HOME = ci(('HOME',))
    for g in x:
        for h5, a5, ph, pa, qh, qa, sec in g['stints']:
            for off, dff, pts, poss, ishome in ((h5, a5, ph, qh, 1), (a5, h5, pa, qa, 0)):
                if poss <= 0: continue
                for pid in off: rows.append(r); cols.append(ci(('O', pid))); vals.append(1.0)
                for pid in dff: rows.append(r); cols.append(ci(('D', pid))); vals.append(1.0)
                if ishome: rows.append(r); cols.append(HOME); vals.append(1.0)
                y.append(100 * pts / poss); w.append(poss); r += 1
            for pid in h5: o = onp[pid]; o[0] += ph; o[1] += qh; o[2] += pa; o[3] += qa
            for pid in a5: o = onp[pid]; o[0] += pa; o[1] += qa; o[2] += ph; o[3] += qh
            th, ta = team_tot[g['H']], team_tot[g['A']]
            th[0] += ph; th[1] += qh; th[2] += pa; th[3] += qa; ta[0] += pa; ta[1] += qa; ta[2] += ph; ta[3] += qh
    y = np.array(y); w = np.array(w); mu = np.average(y, weights=w)
    X = csr_matrix((vals, (rows, cols)), shape=(r, len(idx)))
    sw = np.sqrt(w); Xw = csr_matrix(X.multiply(sw[:, None])); yw = (y - mu) * sw
    R = {}
    for lam in LAM:
        beta = lsqr(Xw, yw, damp=np.sqrt(lam), atol=1e-8, btol=1e-8, iter_lim=5000)[0]
        R[lam] = {pid: (beta[idx[('O', pid)]] if ('O', pid) in idx else 0.0, beta[idx[('D', pid)]] if ('D', pid) in idx else 0.0) for pid in mins}
        R[lam]['_home'] = beta[HOME]
    onoff = {}
    for pid, o in onp.items():
        t = team_tot[team_of.get(pid)]
        off_ = [t[0] - o[0], t[1] - o[1], t[2] - o[2], t[3] - o[3]]
        if o[1] > 50 and off_[1] > 50:
            onoff[pid] = (100 * o[0] / o[1] - 100 * o[2] / o[3]) - (100 * off_[0] / off_[1] - 100 * off_[2] / off_[3])
    return dict(mins=mins, pir40=pir40, onoff=onoff, R=R, mu=mu, team=team_of)
M = {s: season_metrics(s) for s in SEAS}
P(''); P('ΕΔΡΑ (RAPM, ποντοι/100 κατοχες για τον γηπεδουχο στην επιθεση, λ 3000): ' + ' · '.join(f'{s}: {M[s]["R"][3000]["_home"]:+.1f}' for s in SEAS))
P(''); P('ΣΤΑΘΕΡΟΤΗΤΑ: συσχετιση ιδιου δεικτη σεζον S ↔ S+1 (παικτες ≥500′ και στις δυο σεζον)')
hdr = ['PIR/40', 'απλο on/off'] + [f'RAPM λ{l}' for l in LAM] + ['RAPM O λ3000', 'RAPM D λ3000']
P('  ζευγαρι      n  · ' + ' · '.join(hdr))
allc = collections.defaultdict(list)
for s0, s1 in zip(SEAS, SEAS[1:]):
    a, b = M[s0], M[s1]
    ps = [p for p in a['mins'] if a['mins'][p] >= 500 and b['mins'].get(p, 0) >= 500]
    if len(ps) < 20: continue
    def cr(f):
        u = [f(a, p) for p in ps]; v = [f(b, p) for p in ps]; m = [i for i in range(len(ps)) if u[i] is not None and v[i] is not None]
        return np.corrcoef([u[i] for i in m], [v[i] for i in m])[0, 1] if len(m) > 10 else np.nan
    cs = [cr(lambda M_, p: M_['pir40'].get(p)), cr(lambda M_, p: M_['onoff'].get(p))] + \
         [cr(lambda M_, p, l=l: M_['R'][l][p][0] - M_['R'][l][p][1]) for l in LAM] + \
         [cr(lambda M_, p: M_['R'][3000][p][0]), cr(lambda M_, p: M_['R'][3000][p][1])]
    for h, c in zip(hdr, cs): allc[h].append(c)
    P(f'  {s0}→{s1[-2:]}  {len(ps):3d} · ' + ' · '.join(f'{c:+.2f}' for c in cs))
P('  ΜΕΣΟΣ          · ' + ' · '.join(f'{np.nanmean(allc[h]):+.2f}' for h in hdr))
P(''); P('ΕΛΕΓΧΟΣ ΛΟΓΙΚΗΣ — κορυφη RAPM καθαρο (λ 3000), παικτες ≥800′, τελευταιες 2 σεζον:')
for s in SEAS[-2:]:
    m = M[s]; ps = [p for p in m['mins'] if m['mins'][p] >= 800]
    top = sorted(ps, key=lambda p: -(m['R'][3000][p][0] - m['R'][3000][p][1]))[:8]
    P(f'  {s}: ' + ' · '.join(f"{NAME.get(p, p)} ({m['team'][p]}) {m['R'][3000][p][0] - m['R'][3000][p][1]:+.1f} [O {m['R'][3000][p][0]:+.1f} D {m['R'][3000][p][1]:+.1f}]" for p in top))
json.dump({s: {p: dict(min=round(M[s]['mins'][p]), pir40=round(M[s]['pir40'].get(p, 0), 2), **{f'O{l}': round(M[s]['R'][l][p][0], 3) for l in LAM},
                       **{f'D{l}': round(M[s]['R'][l][p][1], 3) for l in LAM}, team=M[s]['team'].get(p), name=NAME.get(p)) for p in M[s]['mins']} for s in SEAS},
          open(os.path.join(ROOT, 'el_rapm_season.json'), 'w', encoding='utf-8'), ensure_ascii=False)
open(os.path.join(ROOT, 'el_rapm_build_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
