# -*- coding: utf-8 -*-
"""abs_build.py — ΦΑΣΗ 0 του εργου απουσιων (20/10/2026, Στελιος: «μεγαλο backtest, βαθια αναλυση, LOSO»).
Για καθε ματς CORE7 (2021-26 + φετος) και καθε ομαδα: ποιοι ΕΛΕΙΠΑΝ πριν το ματς (Sofascore missingPlayers — γνωστο ΠΡΙΝ),
ποσο σημαντικοι ηταν (walk-forward: μονο πληροφορια ΠΡΙΝ το ματς) και τι ενδεκαδα τελικα κατεβηκε (FotMob).
ΠΗΓΕΣ: sofa_hist.jsonl (απουσες + βασικοι Sofascore) · data_{λιγκα}_{σεζον}.json (ματς FotMob, ημερομηνια) · core7_squads.json (βασικοι +
λεπτα FotMob) · player_matches.json (FotMob βαθμολογια/θεση ανα ματς) · core7_player_values.json/euro_player_values.json (αξια ανα ημερομηνια, ονοματα).
ΒΗΜΑΤΑ:
 1. ματς Sofascore → FotMob (λιγκα + ημερομηνια ±1 + ονοματα· μετα μαθαινει αντιστοιχια ομαδων και ξαναπερνα)
 2. παικτης Sofascore → FotMob: απο τους ΒΑΣΙΚΟΥΣ του ιδιου ματς (ονοματα) — ψηφοι σε ολα τα ματς· αλλιως ονομα στο ρόστερ της ομαδας
 3. ανα παικτη πριν το ματς: λεπτα στα 8 τελευταια ματς πρωταθληματος της ομαδας · ικανοτητα (φθινων 0.95 μεσος βαθμολογιων, συρρικνωση
    K=5 προς μεσο θεσης) · αξια (τελευταια τιμη ≤ ημερομηνια)
 4. ανα πλευρα: «πληρης» αναμενομενη 11αδα (1 τερματοφυλακας + 10 με τα περισσοτερα λεπτα) vs «διαθεσιμη» (χωρις τους απουσες, συμπληρωνεται
    με τους επομενους) → Δ ικανοτητας (μεσος 11αδας), Δ αξιας (ln λογου), ανα θεση· ιδια και για την ΠΡΑΓΜΑΤΙΚΗ 11αδα (FotMob).
ΕΞΟΔΟΣ: abs_sides.csv (μια γραμμη ανα ματς-πλευρα) + abs_build_out.txt (καλυψη)."""
import json, glob, re, sys, unicodedata, datetime as dt, math, collections
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
LG = {'EPL': 'EPL', 'LaLiga': 'LaLiga', 'SerieA': 'SerieA', 'Bundesliga': 'Bundesliga', 'Ligue1': 'Ligue1', 'Eredivisie': 'Eredivisie', 'Primeira': 'PrimeiraLiga'}
N_LAST, DECAY, K_SHR = 8, 0.95, 5.0


def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9 ]', '', s).strip()


def ntoks(s):
    return [t for t in norm(s).split() if len(t) > 1]


def name_sim(a, b):
    ta, tb = ntoks(a), ntoks(b)
    if not ta or not tb: return 0
    if norm(a) == norm(b): return 3
    if ta[-1] == tb[-1]: return 2 + (ta[0][0] == tb[0][0])
    if set(ta) & set(tb): return 1
    return 0


# ---------- FotMob ματς ----------
FM = {}                    # mid -> dict(lg, sea, date, hid, aid, hn, an)
for lg, fl in LG.items():
    for f in glob.glob(f'data_{fl}_*.json'):
        sea = re.search(r'_(\d{4})\.json$', f).group(1)
        for k, v in json.load(open(f, encoding='utf-8')).items():
            try: d = dt.datetime.strptime(v['date'], '%a, %b %d, %Y, %H:%M UTC')
            except Exception: continue
            FM[str(k)] = dict(lg=lg, sea=sea, date=d, hid=v['home']['id'], aid=v['away']['id'], hn=v['home']['name'], an=v['away']['name'])
BYDAY = collections.defaultdict(list)
for k, m in FM.items(): BYDAY[(m['lg'], m['date'].date())].append(k)
SQ = json.load(open('core7_squads.json', encoding='utf-8'))
for fn in ('squads_2627.json',):
    try:
        for k, v in json.load(open(fn, encoding='utf-8')).items(): SQ.setdefault(str(k), v)
    except Exception: pass
PM = json.load(open('player_matches.json', encoding='utf-8'))
try:
    for k, v in json.load(open('player_matches_2627.json', encoding='utf-8')).items(): PM.setdefault(str(k), v)
except Exception: pass
for k, sq in SQ.items():                       # φετινα: οι βασικοι απο το player_matches (σημαια βασικου)
    for fs in ('h', 'a'):
        if sq.get(fs) and 'st' not in sq[fs]:
            sq[fs]['st'] = [e[0] for e in ((PM.get(k) or {}).get(fs) or {}).get('p', []) or [] if len(e) > 4 and e[4] == 1]
NAME, VAL = {}, {}
for f in ('core7_player_values.json', 'euro_player_values.json'):
    for k, v in json.load(open(f, encoding='utf-8')).items():
        NAME.setdefault(str(k), v.get('name'))
        if v.get('hist') and str(k) not in VAL: VAL[str(k)] = [(h[0], h[1]) for h in v['hist'] if h[1]]
# ---------- 1. ματς Sofascore → FotMob ----------
S = [json.loads(l) for l in open('sofa_hist.jsonl', encoding='utf-8')]
S = [r for r in S if r['lg'] in LG]
TMAP = collections.defaultdict(collections.Counter)      # sofa team id -> FotMob team id
def find(r, use_tmap):
    d = dt.datetime.utcfromtimestamp(r['ts']).date()
    cands = [k for dd in (-1, 0, 1) for k in BYDAY.get((r['lg'], d + dt.timedelta(days=dd)), [])]
    for k in cands:
        m = FM[k]
        if use_tmap:
            th, ta = TMAP[r['h'][0]].most_common(1), TMAP[r['a'][0]].most_common(1)
            if th and ta and th[0][0] == m['hid'] and ta[0][0] == m['aid']: return k
        h, a = norm(r['h'][1]).replace(' ', ''), norm(r['a'][1]).replace(' ', '')
        hh, aa = norm(m['hn']).replace(' ', ''), norm(m['an']).replace(' ', '')
        if (hh[:5] == h[:5] or hh in h or h in hh) and (aa[:5] == a[:5] or aa in a or a in aa): return k
    return None
MAP = {}
for r in S:
    k = find(r, False)
    if k: MAP[r['e']] = k; TMAP[r['h'][0]][FM[k]['hid']] += 1; TMAP[r['a'][0]][FM[k]['aid']] += 1
for r in S:
    if r['e'] not in MAP:
        k = find(r, True)
        if k: MAP[r['e']] = k
# ---------- 2. παικτες Sofascore → FotMob ----------
PV = collections.defaultdict(collections.Counter)
for r in S:
    k = MAP.get(r['e']); sq = SQ.get(k) if k else None
    if not sq: continue
    for ss, fs in (('sh', 'h'), ('sa', 'a')):
        if not sq.get(fs): continue
        fst = [str(x) for x in sq[fs]['st']]
        for sid, snm in r[ss]:
            best = max(((name_sim(snm, NAME.get(f, '')), f) for f in fst), default=(0, None))
            if best[0] >= 2: PV[sid][best[1]] += 1
PMAP = {sid: c.most_common(1)[0][0] for sid, c in PV.items()}
ROSTER = collections.defaultdict(set)          # FotMob team id -> FotMob player ids
for k, sq in SQ.items():
    for fs in ('h', 'a'):
        if sq.get(fs): ROSTER[sq[fs]['t']] |= set(sq[fs]['p'].keys())
# ---------- 3. ιστορικο ανα ομαδα/παικτη (walk-forward) ----------
ORDER = sorted([k for k in FM if k in SQ], key=lambda k: FM[k]['date'])
TEAM_HIST = collections.defaultdict(list)       # team -> [(date, {pid: minutes})]
PL_RT = {}                                      # pid -> (sum_w*rt, sum_w, pos)
POSM = collections.defaultdict(list)
for k in PM:
    for s in ('h', 'a'):
        for e in ((PM[k] or {}).get(s) or {}).get("p", []) or []:
            if e[1] is not None: POSM[e[3]].append(e[1])
POS_MU = {p: float(np.mean(v)) for p, v in POSM.items()}
PL_POS = {}
def ability(pid):
    s = PL_RT.get(pid)
    pos = PL_POS.get(pid, 2); mu = POS_MU.get(pos, 6.7)
    if not s: return mu
    return (s[0] + K_SHR * mu) / (s[1] + K_SHR)
def value_at(pid, d):
    h = VAL.get(pid)
    if not h: return None
    ds = d.strftime('%Y-%m-%d'); v = None
    for t, x in h:
        if t <= ds: v = x
        else: break
    return v if v is not None else h[0][1]
rows = []
REV = {v: k for k, v in MAP.items()}
SROW = {r['e']: r for r in S}
for k in ORDER:
    m = FM[k]; sq = SQ[k]; srow = SROW.get(REV.get(k))
    for fs, tid in (('h', m['hid']), ('a', m['aid'])):
        side = sq.get(fs)
        if not side: continue
        hist = TEAM_HIST[tid][-N_LAST:]
        mins = collections.Counter(); starts = collections.Counter()
        for _, pmn in hist:
            for pid, mn in pmn.items(): mins[pid] += mn
        if len(hist) >= 3:
            pool = [p for p, mn in mins.most_common() if mn > 0]
            gk = [p for p in pool if PL_POS.get(p) == 0]
            def xi(excl):
                g = [p for p in gk if p not in excl][:1]
                o = [p for p in pool if p not in excl and PL_POS.get(p) != 0][:10]
                return g + o
            miss, doubt, n_unm = set(), set(), 0
            if srow:
                for e in (srow['mh'] if fs == 'h' else srow['ma']):
                    fid = PMAP.get(e[0])
                    if not fid:
                        best = max(((name_sim(e[1], NAME.get(p, '')), p) for p in ROSTER[tid]), default=(0, None))
                        fid = best[1] if best[0] >= 2 else None
                    if not fid: n_unm += 1; continue
                    (miss if e[2] == 'missing' else doubt).add(fid)
            last2 = collections.Counter()
            for _, pmn in hist[-2:]:
                for pid, mn in pmn.items(): last2[pid] += mn
            fresh = {p for p in miss if last2[p] >= 45}            # ΝΕΑ απουσια: επαιξε ≥45′ στα 2 τελευταια ματς (η φορμα της ομαδας ΔΕΝ την εχει)
            full = xi(set()); avail = xi(miss); avail_d = xi(miss | doubt); act = [str(x) for x in side['st']]
            fullr = xi({p for p in miss if p not in fresh}); availf = xi(miss)          # «πληρης» = χωρις τις ΠΑΛΙΕΣ απουσιες
            def A(x): return float(np.mean([ability(p) for p in x])) if x else np.nan
            def V(x):
                vs = [value_at(p, m['date']) for p in x]; vs = [v for v in vs if v]
                return float(np.sum(vs)) if len(vs) >= 9 else np.nan
            def byp(x, pos): return sum(ability(p) for p in x if PL_POS.get(p, 2) == pos)
            reg_out = [p for p in miss if mins[p] >= 0.5 * 90 * len(hist)]
            r = dict(mid=k, lg=m['lg'], sea=m['sea'], date=m['date'].strftime('%Y-%m-%d'), side=fs, team=tid, n_hist=len(hist),
                     sofa=bool(srow), sofa_list=bool(srow and (srow['mh'] if fs == 'h' else srow['ma'])), n_unmapped=n_unm,
                     n_miss=len(miss), n_doubt=len(doubt), n_miss_reg=len(reg_out),
                     miss_min_share=sum(mins[p] for p in miss) / max(90 * len(hist) * 11, 1),
                     A_full=A(full), A_avail=A(avail), A_avail_d=A(avail_d), A_act=A(act),
                     V_full=V(full), V_avail=V(avail), V_avail_d=V(avail_d), V_act=V(act),
                     n_fresh=len(fresh), A_fullr=A(fullr), V_fullr=V(fullr),
                     full_ids='|'.join(full), avail_ids='|'.join(avail), availd_ids='|'.join(avail_d),   # 21/10: λιστες για τη φορμουλα πριν το ματς
                     out_in_xi=len(set(full) - set(avail)), act_vs_full=len(set(full) - set(act)), act_vs_avail=len(set(avail) - set(act)))
            for pos, nm in ((0, 'gk'), (1, 'def'), (2, 'mid'), (3, 'att')):
                r[f'dA_{nm}'] = byp(avail, pos) - byp(full, pos)
                r[f'dAact_{nm}'] = byp(act, pos) - byp(full, pos)
            rows.append(r)
    # ενημερωση ΜΕΤΑ το ματς (walk-forward)
    for fs, tid in (('h', m['hid']), ('a', m['aid'])):
        side = sq.get(fs)
        if side: TEAM_HIST[tid].append((m['date'], {str(p): mn for p, mn in side['p'].items()}))
        pmside = (PM.get(k) or {}).get(fs) or {}
        for e in pmside.get('p', []) or []:
            pid, rt, _, pos = str(e[0]), e[1], e[2], e[3]
            PL_POS[pid] = pos
            if rt is None: continue
            mn = (side or {}).get('p', {}).get(pid, 90) if side else 90
            w = max(mn, 1) / 90.0
            s0 = PL_RT.get(pid, (0.0, 0.0, pos))
            PL_RT[pid] = (s0[0] * DECAY + w * rt, s0[1] * DECAY + w, pos)
D = pd.DataFrame(rows)
D.to_csv('abs_sides.csv', index=False)
print(f'Sofascore ματς {len(S)} · ταιριαξαν με FotMob {len(MAP)} ({100 * len(MAP) / len(S):.1f}%) · παικτες Sofascore→FotMob {len(PMAP)}')
print(f'πλευρες {len(D)} · με Sofascore {D.sofa.mean():.1%} · με λιστα απουσων {D.sofa_list.mean():.1%} · μη αντιστοιχισμενοι απουσες ανα πλευρα {D.n_unmapped.mean():.2f}')
g = D.groupby(['lg', 'sea']).agg(n=('mid', 'size'), lista=('sofa_list', 'mean'), miss=('n_miss', 'mean'), reg=('n_miss_reg', 'mean'),
                                  dA=('A_avail', lambda s: np.nan), unm=('n_unmapped', 'mean'))
D['dA_pre'] = D.A_avail - D.A_full; D['dA_act'] = D.A_act - D.A_full; D['dV_pre'] = np.log(D.V_avail / D.V_full); D['dV_act'] = np.log(D.V_act / D.V_full)
for (lg, sea), q in D.groupby(['lg', 'sea']):
    print(f'   {lg:11s} {sea}: πλευρες {len(q):4d} · λιστα {q.sofa_list.mean():4.0%} · λειπουν {q.n_miss.mean():.1f} (βασικοι {q.n_miss_reg.mean():.2f}) · '
          f'μη αντιστ. {q.n_unmapped.mean():.2f} · Δικαν. πριν {q.dA_pre.mean():+.3f} (sd {q.dA_pre.std():.3f}) · πραγμ. {q.dA_act.mean():+.3f} · '
          f'Δαξια πριν {q.dV_pre.mean():+.3f} · συσχ. πριν↔πραγμ {q[["dA_pre", "dA_act"]].corr().iloc[0, 1]:.2f}')
