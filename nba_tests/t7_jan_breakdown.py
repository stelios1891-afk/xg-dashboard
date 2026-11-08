# -*- coding: utf-8 -*-
"""t7_jan_breakdown.py — Τεστ 7 (Στελιος 20/10): τι αλλαζει απο Γεναρη και μετα; ΠΕΡΙΓΡΑΦΙΚΟ, οχι κανονας.
Βαση = production CFG_H + απουσιες (K=2, 0.75·LOSS) + B2B 3.0 (ιδια με timing_abs_test V_OPEN).
Picks στο ΑΝΟΙΓΜΑ (MKH 'o'), edge ≥8% και ≥5%. Περιοδοι: Οκτ-Δεκ (ΟΔ) / Ιαν-Φεβ (ΙΦ) / Μαρ-Απρ (ΜΑ).
Ανα κατηγορια: n, ROI, CLV (δικαιη γραμμη κλεισ. − ανοιγμ. προς εμας, π.), gap = μοντελο − κλεισιμο (προς εμας),
real = πραγματικο − κλεισιμο (προς εμας). Αν gap>0 και real≈0 → το μοντελο βλεπει κατι που δεν υπαρχει.
Κατηγοριες: (a) φαβ/αουτσ, γηπ/φιλ, μεγεθος γραμμης · (b) ποιοτητα δικης μας/αντιπαλου (θεση στη λιγκα πριν το ματς),
TANK (≥50 ματς & ≥6 πισω απο 10η), ELIM (μαθηματικα εκτος 10ης), LOCK (κλειδωμενη θεση), LATE_TOP · (c) ανταλλαγες παικτη ≥20′
(αλλαγη ομαδας στο nba_player_games), 10/30 ματς μετα + παραθυρο προθεσμιας · (d) σταρ (top-2 λεπτα) εκτος — «ξεκουραση»
(επαιξε προηγ. ΚΑΙ επομενο) vs «τραυματισμος» (box score = εκ των υστερων, μονο περιγραφη), B2B, τελευταια 10 · (e) μοντελο vs
φορμα 20 ματς (διορθωμενη για αντιπαλο)."""
import os, sys, collections
sys.stdout.reconfigure(encoding="utf-8")
SC = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(SC, 'absence_test.py'), encoding='utf-8').read().split("print('υπολογισμος απουσιων")[0]
exec(src)
sys.stdout.reconfigure(encoding='utf-8')
n = len(G); HOME = G.home.values; AWAY = G.away.values; MONS = G.date.dt.month.values
# ---------- βαση: απουσιες K=2 + B2B ----------
LH = np.zeros(n); LA = np.zeros(n)
for i in range(n):
    LH[i], _ = team_loss(HOME[i], dD[i], 2); LA[i], _ = team_loss(AWAY[i], dD[i], 2)
B2H = np.zeros(n); B2A = np.zeros(n); last = {}
for i in np.argsort(dD, kind='stable'):
    s, h_, a_, d = SEAS_G[i], HOME[i], AWAY[i], dD[i]
    B2H[i] = float(last.get((s, h_)) == d - np.timedelta64(1, 'D')); B2A[i] = float(last.get((s, a_)) == d - np.timedelta64(1, 'D'))
    last[(s, h_)] = d; last[(s, a_)] = d
V = MG + 3.0 * (B2A - B2H) + 0.75 * (LH - LA)
PER = np.where(np.isin(MONS, [10, 11, 12]), 0, np.where(np.isin(MONS, [1, 2]), 1, np.where(np.isin(MONS, [3, 4]), 2, -1)))
PN = ['ΟΔ', 'ΙΦ', 'ΜΑ']

# ---------- βαθμολογια πριν τη μερα: θεση λιγκας, TANK, ELIM, LOCK, LATE_TOP, ματς που μενουν ----------
EAST = {'ATL', 'BOS', 'BRK', 'CHO', 'CHI', 'CLE', 'DET', 'IND', 'MIA', 'MIL', 'NYK', 'ORL', 'PHI', 'TOR', 'WAS'}
QUAL = np.full((n, 2), 'mid', object); TANK = np.zeros((n, 2), bool); ELIM = np.zeros((n, 2), bool); LOCK = np.zeros((n, 2), bool)
LTOP = np.zeros((n, 2), bool); GLEFT = np.zeros((n, 2)); GP = np.zeros((n, 2))
for s in np.unique(SEAS_G):
    idx = np.where(SEAS_G == s)[0]; tot = collections.Counter(list(HOME[idx]) + list(AWAY[idx])); rec = {t: [0, 0, 0.0] for t in tot}
    for d in np.unique(dD[idx]):
        cur = idx[dD[idx] == d]
        wp = {t: (r[0] / max(1, r[0] + r[1]), r[2] / max(1, r[0] + r[1])) for t, r in rec.items()}
        order = sorted(rec, key=lambda t: wp[t], reverse=True); rk = {t: j + 1 for j, t in enumerate(order)}
        st = {}
        for conf in (EAST, set(rec) - EAST):
            rows = sorted([t for t in rec if t in conf], key=lambda t: wp[t], reverse=True)
            w10, l10 = rec[rows[9]][0], rec[rows[9]][1]
            for j, t in enumerate(rows):
                w, l = rec[t][0], rec[t][1]; rem = tot[t] - w - l
                gb = ((w10 - w) + (l - l10)) / 2
                elim = j >= 10 and w + rem < w10
                below = rows[j + 1:]; above = rows[:j]
                lock = (w + l >= 60) and all(rec[u][0] + tot[u] - rec[u][0] - rec[u][1] < w for u in below) and all(w + rem < rec[v][0] for v in above)
                st[t] = (gb, elim, lock, rem)
        for i in cur:
            for k, t in enumerate((HOME[i], AWAY[i])):
                gp = rec[t][0] + rec[t][1]; GP[i, k] = gp; gb, el, lk, rem = st[t]; GLEFT[i, k] = rem
                QUAL[i, k] = 'early' if gp < 10 else ('top8' if rk[t] <= 8 else ('bot8' if rk[t] >= 23 else 'mid'))
                TANK[i, k] = gp >= 50 and gb >= 6; ELIM[i, k] = el; LOCK[i, k] = lk
                LTOP[i, k] = gp >= tot[t] - 5 and rec[t][0] / max(1, gp) >= .62
        for i in cur:
            m = ACT[i]
            rec[HOME[i]][0 if m > 0 else 1] += 1; rec[AWAY[i]][0 if m < 0 else 1] += 1; rec[HOME[i]][2] += m; rec[AWAY[i]][2] -= m

# ---------- ανταλλαγες (παικτης ≥20′ αλλαζει ομαδα μεσα στη σεζον) ----------
A2 = A[['pid', 'team', 'd', 'MIN', 's']].sort_values('d')
EVT = collections.defaultdict(list)                # (s, team) → ημερες γεγονοτος
DEADL = {2022: '2022-02-10', 2023: '2023-02-09', 2024: '2024-02-08', 2025: '2025-02-06', 2026: '2026-02-05'}
DEADL = {k: np.datetime64(v) for k, v in DEADL.items()}
DLT = collections.defaultdict(set)                 # (s) → ομαδες με ανταλλαγη ±5 μερες απο την προθεσμια
ntr = 0
for (p, s), g in A2.groupby(['pid', 's']):
    tm_, dd, mm = g.team.values, g.d.values, g.MIN.values
    for j in range(1, len(tm_)):
        if tm_[j] != tm_[j - 1]:
            old = mm[:j][tm_[:j] == tm_[j - 1]][-10:]; new = mm[j:][tm_[j:] == tm_[j]][:10]
            if max(old.mean() if len(old) else 0, new.mean() if len(new) else 0) < 20: continue
            e = dd[j]; ntr += 1
            for t in (tm_[j - 1], tm_[j]):
                EVT[(s, t)].append(e)
                if s in DEADL and abs((e - DEADL[s]).astype(int)) <= 7: DLT[s].add(t)
TGI = {}                                           # (s, team) → ταξινομημενες ημερες ματς
for s in np.unique(SEAS_G):
    idx = np.where(SEAS_G == s)[0]
    for t in set(HOME[idx]) | set(AWAY[idx]): TGI[(s, t)] = np.sort(dD[idx][(HOME[idx] == t) | (AWAY[idx] == t)])
def since_trade(s, t, d):
    """ποσα ματς της ομαδας απο το πιο προσφατο γεγονος (0 = πρωτο ματς μετα)· None αν κανενα."""
    ev = [e for e in EVT.get((s, t), []) if e <= d]
    if not ev: return None
    days = TGI[(s, t)]; return int(((days >= max(ev)) & (days < d)).sum())
TR = np.full((n, 2), 999)
for i in range(n):
    for k, t in enumerate((HOME[i], AWAY[i])):
        x = since_trade(SEAS_G[i], t, dD[i]); TR[i, k] = 999 if x is None else x
DLW = np.zeros((n, 2), bool)
for i in range(n):
    s = SEAS_G[i]
    if s in DEADL and DEADL[s] <= dD[i] < DEADL[s] + np.timedelta64(21, 'D'):
        for k, t in enumerate((HOME[i], AWAY[i])): DLW[i, k] = t in DLT[s]

# ---------- σταρ (top-2 λεπτα, 10 τελευταια) εκτος: «ξεκουραση» (μοναδικο DNP) vs «τραυματισμος» ----------
STR = np.zeros((n, 2), int); STI = np.zeros((n, 2), int)
for (t, s), g in A2.groupby(['team', 's']):
    days = TGI.get((s, t))
    if days is None: continue
    pl = {d: set(x.pid) for d, x in g.groupby('d')}; mins = {d: dict(zip(x.pid, x.MIN)) for d, x in g.groupby('d')}
    for j in range(5, len(days)):
        d = days[j]; agg = collections.Counter()
        for dd_ in days[max(0, j - 10):j]:
            for p, m in mins.get(dd_, {}).items(): agg[p] += m
        top2 = [p for p, _ in agg.most_common(2)]
        for p in top2:
            if p in pl.get(d, set()): continue
            prv = p in pl.get(days[j - 1], set()); nxt = j + 1 < len(days) and p in pl.get(days[j + 1], set())
            ii = np.where((dD == d) & (SEAS_G == s) & ((HOME == t) | (AWAY == t)))[0]
            for i in ii:
                k = 0 if HOME[i] == t else 1
                if prv and nxt: STR[i, k] += 1
                else: STI[i, k] += 1

# ---------- φορμα 20 ματς διορθωμενη για αντιπαλο ----------
HCA = float(np.mean(ACT[np.isin(SEAS_G, EV)]))
R20 = np.full((n, 2), np.nan)
for s in np.unique(SEAS_G):
    idx = np.where(SEAS_G == s)[0]; idx = idx[np.argsort(dD[idx], kind='stable')]
    tm = collections.defaultdict(list); hist = collections.defaultdict(list)
    for d in np.unique(dD[idx]):
        cur = idx[dD[idx] == d]
        avg = {t: np.mean(v) for t, v in tm.items()}
        for i in cur:
            for k, t in enumerate((HOME[i], AWAY[i])):
                if len(hist[t]) >= 10: R20[i, k] = np.mean(hist[t][-20:])
        for i in cur:
            h_, a_, m = HOME[i], AWAY[i], ACT[i]
            hist[h_].append(m - HCA + avg.get(a_, 0)); hist[a_].append(-m + HCA + avg.get(h_, 0))
        for i in cur:
            tm[HOME[i]].append(ACT[i]); tm[AWAY[i]].append(-ACT[i])
ROLL = R20[:, 0] - R20[:, 1] + HCA

# ---------- picks ----------
def picks(thr):
    out = []
    for i, d in MKH.items():
        if SEAS_G[i] not in EV or not np.isfinite(V[i]) or PER[i] < 0: continue
        L, mko, oh, oa = d['o']; mkc = d['c'][1]
        pw, pp, pl = cover(V[i], L, SIG); e1, e2 = pw * oh + pp - 1, pl * oa + pp - 1
        s_, e, od_ = (1, e1, oh) if e1 >= e2 else (-1, e2, oa)
        if e < thr: continue
        x = (ACT[i] + L) * s_; u = (od_ - 1) if x > 0 else (0.0 if x == 0 else -1.0)
        k = 0 if s_ == 1 else 1
        out.append(dict(i=i, s=s_, k=k, o=1 - k, Ls=L * s_, u=u, clv=s_ * (mkc - mko), gap=s_ * (V[i] - mkc), real=s_ * (ACT[i] - mkc),
                        rd=s_ * (V[i] - ROLL[i]) if np.isfinite(ROLL[i]) else np.nan))
    return out

def cats(p):
    i, k, o, Ls = p['i'], p['k'], p['o'], p['Ls']; c = []
    c.append('a:φαβορι' if Ls < 0 else ('a:αουτσαιντερ' if Ls > 0 else 'a:pk'))
    c.append('a:γηπεδουχος' if k == 0 else 'a:φιλοξενουμενος')
    a = abs(Ls); c.append('a:γραμμη pk-3' if a <= 3 else ('a:γραμμη 3.5-7' if a <= 7 else ('a:γραμμη 7.5-12' if a <= 12 else 'a:γραμμη 12.5+')))
    c.append(f'a:{"φαβ" if Ls < 0 else "αουτ"} {"γηπ" if k == 0 else "φιλ"}')
    c.append(f'b:εμεις {QUAL[i, k]}'); c.append(f'b:αντιπ {QUAL[i, o]}')
    if QUAL[i, k] == 'bot8' and Ls > 0: c.append('b:αουτσ. bot8 (εμεις)')
    if QUAL[i, o] == 'top8' and Ls > 0: c.append('b:αουτσ. vs top8')
    for nm, M in (('TANK', TANK), ('ELIM', ELIM), ('LOCK', LOCK), ('LATE_TOP', LTOP)):
        if M[i, k]: c.append(f'b:εμεις {nm}')
        if M[i, o]: c.append(f'b:αντιπ {nm}')
    if TANK[i].any() or ELIM[i].any() or LOCK[i].any() or LTOP[i].any(): c.append('b:καποια «αδιαφορη» (T/E/L/LT)')
    for nm, kk in (('εμεις', k), ('αντιπ', o)):
        if TR[i, kk] < 10: c.append(f'c:{nm} ανταλλ. ≤10 ματς')
        if TR[i, kk] < 30: c.append(f'c:{nm} ανταλλ. ≤30 ματς')
        if DLW[i, kk]: c.append(f'c:{nm} προθεσμια+21μ')
    if (TR[i] < 30).any(): c.append('c:καποια ανταλλ. ≤30')
    for nm, kk in (('εμεις', k), ('αντιπ', o)):
        if STR[i, kk]: c.append(f'd:{nm} σταρ «ξεκουραση»')
        if STI[i, kk]: c.append(f'd:{nm} σταρ «τραυματ.»')
    if B2H[i] if k == 0 else B2A[i]: c.append('d:εμεις B2B')
    if B2A[i] if k == 0 else B2H[i]: c.append('d:αντιπ B2B')
    if GLEFT[i].min() <= 10: c.append('d:τελευταια 10')
    rd = p['rd']
    if np.isfinite(rd): c.append('e:μοντ−φορμα ≤0' if rd <= 0 else ('e:μοντ−φορμα 0-3' if rd <= 3 else ('e:μοντ−φορμα 3-6' if rd <= 6 else 'e:μοντ−φορμα >6')))
    else: c.append('e:μοντ−φορμα n/a')
    return c

def table(thr):
    P = picks(thr); CC = [cats(p) for p in P]
    def st(sel):
        if not sel: return (0, 0.0, 0.0, 0.0, np.nan, np.nan, np.nan)
        u = np.array([P[j]['u'] for j in sel]); cl = np.array([P[j]['clv'] for j in sel])
        return (len(sel), u.mean() * 100, u.sum(), cl.mean(), np.mean([P[j]['gap'] for j in sel]), np.mean([P[j]['real'] for j in sel]), np.mean(cl > 0) * 100)
    print(f'\n================ EDGE ≥{thr * 100:.0f}% (ανοιγμα) — n/ROI/CLV(π.) ανα περιοδο · Ιαν+ μοναδες ανα σεζον {" ".join(str(Y)[2:] for Y in EV)} · gap/real Ιαν+ ================')
    print(f'{"κατηγορια":30s}|{"ΟΔ n  ROI   CLV":>17s} |{"ΙΦ n  ROI   CLV":>17s} |{"ΜΑ n  ROI   CLV":>17s} | Ιαν+ u    ανα σεζον (u)            θετ | gap real')
    allc = ['ΟΛΑ'] + sorted({c for cc in CC for c in cc})
    JAN = {}
    for c in allc:
        sel = [j for j in range(len(P)) if c == 'ΟΛΑ' or c in CC[j]]
        cols = []
        for q in range(3):
            n_, r, u, cl, *_ = st([j for j in sel if PER[P[j]['i']] == q]); cols.append(f'{n_:4d} {r:+5.1f} {cl:+5.2f}' if n_ else f'{0:4d}{"":12s}')
        js = [j for j in sel if PER[P[j]['i']] >= 1]; n_, r, u, cl, gp_, re_, cp = st(js)
        ps = {Y: sum(P[j]['u'] for j in js if SEAS_G[P[j]['i']] == Y) for Y in EV}
        JAN[c] = (n_, r, u, cl, ps, js)
        print(f'{c[:30]:30s}|{cols[0]:>17s} |{cols[1]:>17s} |{cols[2]:>17s} | {u:+6.1f}  ' + ' '.join(f'{ps[Y]:+5.1f}' for Y in EV)
              + f'  {sum(ps[Y] > 0 for Y in EV)}/5 | {gp_:+4.1f} {re_:+5.2f}')
    # ποιες κατηγοριες «εξηγουν» την απωλεια Ιαν+: μοναδες, και ROI των υπολοιπων Ιαν+ picks αν αφαιρεθουν
    nA, rA, uA, *_ , jsA = JAN['ΟΛΑ']
    print(f'\n  ΚΑΤΑΤΑΞΗ Ιαν+ (≥{thr * 100:.0f}%): συνολο {nA} picks {rA:+.1f}% {uA:+.1f}u — κατηγοριες με τις μεγαλυτερες απωλειες (n≥25)')
    print(f'  {"κατηγορια":30s}   n   ROI     u   μεριδιο | υπολοιπα Ιαν+ n ROI | CLV  %CLV>0 | θετ σεζον')
    rank = sorted([c for c in allc if c != 'ΟΛΑ' and JAN[c][0] >= 25], key=lambda c: JAN[c][2])[:12]
    for c in rank:
        n_, r, u, cl, ps, js = JAN[c]; rest = [j for j in jsA if j not in set(js)]
        ur = np.array([P[j]['u'] for j in rest]); cp = np.mean([P[j]['clv'] > 0 for j in js]) * 100
        print(f'  {c[:30]:30s} {n_:4d} {r:+5.1f} {u:+6.1f}  {u / uA * 100 if uA < 0 else 0:5.0f}%  | {len(rest):5d} {ur.mean() * 100:+5.1f} | {cl:+4.2f} {cp:4.0f}% | {sum(ps[Y] > 0 for Y in EV)}/5')
    return P

ev_m = np.isin(SEAS_G, EV)
print(f'EVAL={EV} · picks απο MKH={len(MKH)} · ανταλλαγες παικτη ≥20′: {ntr} · HCA {HCA:.2f}')
print('σφαλμα ανα περιοδο (ολα τα ματς με αγορα): RMSE μοντελο / ανοιγμα / κλεισιμο')
mi = np.array(list(MKH.keys())); mo = np.array([MKH[i]['o'][1] for i in mi]); mc = np.array([MKH[i]['c'][1] for i in mi])
for q in range(3):
    m = ev_m[mi] & (PER[mi] == q) & np.isfinite(V[mi])
    r = lambda x: np.sqrt(np.mean((ACT[mi][m] - x[m]) ** 2))
    print(f'  {PN[q]}: n {m.sum():5d} · μοντελο {r(V[mi]):.2f} · ανοιγμα {r(mo):.2f} · κλεισιμο {r(mc):.2f} · φορμα20 {np.sqrt(np.nanmean((ACT[mi][m] - ROLL[mi][m]) ** 2)):.2f}')
for thr in (.08, .05): table(thr)

# ---------- διασταυρωσεις (επικαλυψεις των μεγαλων κατηγοριων), Ιαν+ ----------
for thr in (.08, .05):
    P = picks(thr); CC = [set(cats(p)) for p in P]
    J = [j for j in range(len(P)) if PER[P[j]['i']] >= 1]
    IND = lambda c: bool(c & {'b:καποια «αδιαφορη» (T/E/L/LT)', 'd:τελευταια 10'})
    combos = [('αουτ γηπ & αδιαφορη/τελ.10', lambda c: 'a:αουτ γηπ' in c and IND(c)),
              ('αουτ γηπ & ΟΧΙ αδιαφ/τελ.10', lambda c: 'a:αουτ γηπ' in c and not IND(c)),
              ('αουτ φιλ & αδιαφορη/τελ.10', lambda c: 'a:αουτ φιλ' in c and IND(c)),
              ('φαβορι & αδιαφορη/τελ.10', lambda c: 'a:φαβορι' in c and IND(c)),
              ('αουτσ & αντιπ mid', lambda c: 'a:αουτσαιντερ' in c and 'b:αντιπ mid' in c),
              ('αουτσ & αντιπ top8', lambda c: 'a:αουτσαιντερ' in c and 'b:αντιπ top8' in c),
              ('αουτσ & αντιπ bot8', lambda c: 'a:αουτσαιντερ' in c and 'b:αντιπ bot8' in c),
              ('αουτ γηπ & εμεις bot8', lambda c: 'a:αουτ γηπ' in c and 'b:εμεις bot8' in c),
              ('αουτ γηπ & εμεις mid/top8', lambda c: 'a:αουτ γηπ' in c and 'b:εμεις bot8' not in c),
              ('ανταλλ≤30 & ΟΧΙ αδιαφ/τελ.10', lambda c: 'c:καποια ανταλλ. ≤30' in c and not IND(c)),
              ('ΚΑΜΙΑ απο: αουτ γηπ/αδιαφ/τελ10', lambda c: 'a:αουτ γηπ' not in c and not IND(c))]
    print(f'\n  ΔΙΑΣΤΑΥΡΩΣΕΙΣ Ιαν+ edge ≥{thr * 100:.0f}%:  n  ROI   u | ανα σεζον | θετ | CLV  gap  real')
    for nm, f in combos:
        js = [j for j in J if f(CC[j])]
        if not js: continue
        u = np.array([P[j]['u'] for j in js]); ps = {Y: sum(P[j]['u'] for j in js if SEAS_G[P[j]['i']] == Y) for Y in EV}
        print(f'  {nm:32s} {len(js):4d} {u.mean() * 100:+5.1f} {u.sum():+6.1f} | ' + ' '.join(f'{ps[Y]:+5.1f}' for Y in EV)
              + f' | {sum(ps[Y] > 0 for Y in EV)}/5 | {np.mean([P[j]["clv"] for j in js]):+.2f} {np.mean([P[j]["gap"] for j in js]):+.1f} {np.mean([P[j]["real"] for j in js]):+.2f}')
