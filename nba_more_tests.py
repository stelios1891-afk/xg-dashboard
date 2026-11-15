# -*- coding: utf-8 -*-
"""nba_more_tests.py — NBA γυρος διορθωσεων (6/10/2026, Στελιος «τρεξτα ναι» + «οι απουσιες ειναι και για να αποφυγουμε κακα μπετς»).
Βαση: καθαρες προβλεψεις nba_full_clean_test (χαντικαπ με B2B) · συνολα + Φ3 (επιπεδο απο υπολοιπο 150 ματς — περασε 5/5).
  Τ2 ΡΥΘΜΟΣ επιθεσης/αμυνας χωριστα: ΔΕΝ ταυτοποιειται απο box score (καθε ματς δινει μονο το αθροισμα κατοχων) → δεν τρεχει.
  Τ3 ΤΥΧΗ: βαρος τυχης {.25, .35} πανω στις επιλεγμενες μηχανες (σημερα .75 χαντικαπ / .5 συνολα).
  Τ5 ΤΑΞΙΔΙ / JET LAG: ζωνες ωρας που ταξιδεψε ΑΝΑΤΟΛΙΚΑ η καθε ομαδα απο το προηγουμενο ματς (≤2 μερες πριν): χαντικαπ += κ·(ανατ. φιλ − ανατ. γηπ), κ {0,.5,1,1.5}.
  Τ6 ΤΕΛΟΣ ΣΕΖΟΝ (αγωνας ≥71): (α) χαντικαπ: picks εκει; (β) συνολα: + κ {0,1,2,3}.
  Τ7 ΣΥΝΟΛΑ ΑΡΧΗΣ (πρωτες 3 εβδομαδες): η αγορα «αγκυρωνεται» στο περσινο σκορ; πραγματικο − κλεισιμο & τυφλο under/over ανα σεζον.
  Τ8 ΑΠΟΥΣΙΕΣ (Στελιος): ΝΕΑ απουσια = παικτης ≥20′ (μεσος των 10 τελευταιων) που επαιξε σε ενα απο τα 3 τελευταια ματς και ΔΕΝ παιζει.
     (α) ROI picks (ανοιγμα, ≥8%) οταν η ΔΙΚΗ ΜΑΣ πλευρα εχει νεα απουσια / ο αντιπαλος / κανεις · (β) «αργα picks»: pick στο κλεισιμο που ΔΕΝ ηταν στο ανοιγμα
     · (γ) picks ανοιγματος οπου η γραμμη κινηθηκε ≥2 π. ΚΟΝΤΡΑ μας · (δ) φιλτρο «χωρις pick αν η πλευρα μας εχει νεα απουσια ≥Χ′» (Χ LOSO).
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): καθε διορθωση RMSE ΜΠΑΙΝΕΙ αν καλυτερη σε ≥4/5 (LOSO)· καθε φιλτρο picks ΜΠΑΙΝΕΙ αν τα picks που κοβει ειναι χειροτερα
  σε ≥4/5 σεζον ΚΑΙ το ROI που μενει ανεβαινει. Εξοδος: nba_more_tests_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, math, json, pickle, collections
import numpy as np, pandas as pd
from statistics import NormalDist
from multiprocessing import Pool

def _run(cfg):
    import nba_full_clean_test as F
    F._init(); c, mg, tt, fin = F.run_all(cfg); return c, mg, tt

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    D = pickle.load(open('nba_diag_data.pkl', 'rb'))
    G, HH, HT, MKH, MKT, GN, B2H, B2A, EV, SIG, SIGT = (D[k] for k in ('G', 'HH', 'HT', 'MKH', 'MKT', 'GN', 'B2H', 'B2A', 'EV', 'SIG', 'SIGT'))
    S = G.season.values.astype(int); ACT = (G.hs - G.as_).values.astype(float); TOT = (G.hs + G.as_).values.astype(float)
    DT = G.date.values; MON = G.date.dt.month.values; OD = np.isin(MON, [10, 11, 12]); ALLM = np.ones(len(G), bool)
    order = np.argsort(DT, kind='stable')
    lab = lambda y: f'{y - 1}-{str(y)[2:]}'
    def rm(v, tgt, ys, msk=ALLM):
        m = np.isin(S, ys) & np.isfinite(v) & msk; return float(np.sqrt(np.mean((tgt - v)[m] ** 2)))
    def loso(PR, tgt, name, base):
        held = np.full(len(G), np.nan); ch = []
        for Y in EV:
            tr = [x for x in EV if x != Y]; k = min(PR, key=lambda k: rm(PR[k], tgt, tr)); ch.append(k); held[S == Y] = PR[k][S == Y]
        d = [rm(held, tgt, [Y]) - rm(PR[base], tgt, [Y]) for Y in EV]; ok = sum(x < 0 for x in d) >= 4
        P(f'  {name:44s} {rm(PR[base], tgt, EV):.3f} → {rm(held, tgt, EV):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5 · επιλογες {ch}' + ('  <- ΜΠΑΙΝΕΙ' if ok else '  <- ✗'))
        return (held if ok else PR[base]), ok
    nd = NormalDist(); Phi = nd.cdf
    def cover(m_, L, s):
        if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
        pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
    def pick(kind, v, i, wh):
        MK = MKH if kind == 'h' else MKT; L, mk, o1, o2 = MK[i][wh]
        if kind == 'h': pw, pp, pl = cover(v[i], L, SIG)
        else: pw, pp, pl = cover(v[i], -L, SIGT)
        e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
        s_, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e < .08: return None
        q = ((ACT[i] + L) if kind == 'h' else (TOT[i] - L)) * s_
        return s_, (od - 1) if q > 0 else (0 if q == 0 else -1), L
    def roi(kind, v, msk=ALLM, wh='o'):
        MK = MKH if kind == 'h' else MKT; R = collections.defaultdict(list)
        for i in MK:
            if S[i] not in EV or not np.isfinite(v[i]) or not msk[i]: continue
            p = pick(kind, v, i, wh)
            if p: R[S[i]].append(p[1])
        u = [x for Y in EV for x in R[Y]]
        return (np.mean(u) * 100 if u else 0, len(u), sum(1 for Y in EV if R[Y] and np.mean(R[Y]) > 0), {Y: sum(R[Y]) for Y in EV})
    def rs(r): return f'{r[0]:+.1f}% ({r[1]}, {r[2]}/5)'
    # ---------- Φ3 επιπεδο συνολων (βαση) ----------
    RES = np.zeros(len(G))
    for y in sorted(set(S)):
        idx = order[S[order] == y]; ds = DT[idx]
        for jj, i in enumerate(idx):
            past = [TOT[idx[q]] - HT[idx[q]] for q in range(max(0, jj - 400), jj) if ds[q] < ds[jj] and np.isfinite(HT[idx[q]])][-150:]
            RES[i] = np.mean(past) if len(past) >= 30 else 0.0
    HT3 = HT + RES
    P('ΒΑΣΗ: χαντικαπ (με B2B) ROI ≥8% ανοιγμα Οκτ-Δεκ ' + rs(roi('h', HH, OD)) + ' · ολη ' + rs(roi('h', HH)))
    P('      συνολα + Φ3 ROI ≥8% ανοιγμα Οκτ-Δεκ ' + rs(roi('t', HT3, OD)) + ' · ολη ' + rs(roi('t', HT3)))
    # ---------- Τ3 τυχη ----------
    P(''); P('################ Τ3 ΤΥΧΗ ################')
    CH = (0.8, 8, 60, .75, 5.0, 1.0, .75, .25); CT = (0.7, 8, 60, .5, 5.0, 0.0, 0.0, 0.0)
    cfgs = [CH[:3] + (lw,) + CH[4:] for lw in (.25, .35, .5, .75)] + [CT[:3] + (lw,) + CT[4:] for lw in (.25, .35, .5, .75)]
    with Pool(8) as pool: R = {c: (mg, tt) for c, mg, tt in pool.map(_run, cfgs)}
    PRh = {c[3]: R[c][0].astype(float) for c in cfgs if c[:3] == CH[:3] and c[4:] == CH[4:]}
    PRt = {c[3]: R[c][1].astype(float) for c in cfgs if c[:3] == CT[:3] and c[4:] == CT[4:]}
    loso(PRh, ACT, 'τυχη στο χαντικαπ (σταθερη μηχανη, w)', .75)
    tt_, okT3 = loso({k: v + RES * 0 for k, v in PRt.items()}, TOT, 'τυχη στα συνολα (σταθερη μηχανη, w)', .5)
    # ---------- Τ5 ταξιδι ----------
    P(''); P('################ Τ5 ΤΑΞΙΔΙ / JET LAG ################')
    TZ = {'BOS': -5, 'BRK': -5, 'NYK': -5, 'PHI': -5, 'TOR': -5, 'CHI': -6, 'CLE': -5, 'DET': -5, 'IND': -5, 'MIL': -6, 'ATL': -5, 'CHO': -5, 'MIA': -5, 'ORL': -5, 'WAS': -5,
          'DEN': -7, 'MIN': -6, 'OKC': -6, 'POR': -8, 'UTA': -7, 'GSW': -8, 'LAC': -8, 'LAL': -8, 'PHO': -7, 'SAC': -8, 'DAL': -6, 'HOU': -6, 'MEM': -6, 'NOP': -6, 'SAS': -6}
    EH_, EA_ = np.zeros(len(G)), np.zeros(len(G)); lastv = {}
    for i in order:
        h, a = G.home.values[i], G.away.values[i]; here = TZ.get(h, -6)
        for t, arr in ((h, EH_), (a, EA_)):
            k = (S[i], t)
            if k in lastv and (DT[i] - lastv[k][0]) / np.timedelta64(1, 'D') <= 2.01: arr[i] = max(0, here - lastv[k][1])
            lastv[k] = (DT[i], here)
    FE = EA_ - EH_
    for nm_, k in (('γηπ. ταξιδεψε ανατολικα (≥1 ζωνη)', EH_ >= 1), ('φιλ. ταξιδεψε ανατολικα (≥1 ζωνη)', EA_ >= 1), ('φιλ. ≥2 ζωνες ανατολικα', EA_ >= 2)):
        I = [i for i in MKH if S[i] in EV and k[i]]
        P(f'  {nm_:36s} n {len(I):4d} · πραγμ − κλεισ {np.mean([ACT[i] - MKH[i]["c"][1] for i in I]):+.2f} · πραγμ − μοντ {np.mean([ACT[i] - HH[i] for i in I]):+.2f}')
    HHt, okT5 = loso({k: HH + k * FE for k in (0, .5, 1, 1.5)}, ACT, 'χαντικαπ += κ·(ανατ. φιλ − ανατ. γηπ)', 0)
    # ---------- Τ6 τελος σεζον ----------
    P(''); P('################ Τ6 ΤΕΛΟΣ ΣΕΖΟΝ (αγωνας ≥71) ################')
    LATE = GN >= 71
    r_late = roi('h', HHt, LATE); r_rest = roi('h', HHt, ~LATE)
    P(f'  χαντικαπ picks αγωνας ≥71: {rs(r_late)} · ανα σεζον ' + ' '.join(f'{lab(Y)} {r_late[3][Y]:+.1f}u' for Y in EV) + f' · υπολοιπα {rs(r_rest)}')
    worse = sum(1 for Y in EV if r_late[3][Y] < 0)
    P(f'  κανονας «χωρις picks χαντικαπ απο τον αγωνα 71»: αρνητικα σε {worse}/5 σεζον' + (' → ΠΕΡΝΑ' if worse >= 4 and r_rest[0] > roi('h', HHt)[0] else ' → ✗'))
    T6, okT6 = loso({k: HT3 + k * LATE for k in (0, 1, 2, 3)}, TOT, 'συνολα += κ (αγωνας ≥71)', 0)
    P('  συνολα ROI (με Τ6 αν περασε): Οκτ-Δεκ ' + rs(roi('t', T6, OD)) + ' · ολη ' + rs(roi('t', T6)) + ' · αγωνας ≥71 ' + rs(roi('t', T6, LATE)))
    # ---------- Τ7 συνολα αρχης ----------
    P(''); P('################ Τ7 ΣΥΝΟΛΑ ΠΡΩΤΩΝ 3 ΕΒΔΟΜΑΔΩΝ ################')
    first = {y: DT[S == y].min() for y in EV}
    W3 = np.array([S[i] in first and (DT[i] - first[S[i]]) / np.timedelta64(1, 'D') <= 21 for i in range(len(G))])
    for Y in EV:
        I = [i for i in MKT if S[i] == Y and W3[i]]
        uo = [((MKT[i]['o'][3] - 1) if TOT[i] < MKT[i]['o'][0] else (0 if TOT[i] == MKT[i]['o'][0] else -1)) for i in I]
        uc = [((MKT[i]['c'][3] - 1) if TOT[i] < MKT[i]['c'][0] else (0 if TOT[i] == MKT[i]['c'][0] else -1)) for i in I]
        P(f'  {lab(Y)}: n {len(I)} · πραγμ − κλεισιμο {np.mean([TOT[i] - MKT[i]["c"][0] for i in I]):+.2f} · πραγμ − μοντ(Φ3) {np.nanmean([TOT[i] - HT3[i] for i in I]):+.2f} · '
          f'τυφλο UNDER ανοιγμα {np.mean(uo) * 100:+.1f}% · κλεισιμο {np.mean(uc) * 100:+.1f}%')
    P('  συνολα (Φ3) picks πρωτες 3 εβδομαδες: ' + rs(roi('t', HT3, W3)))
    # ---------- Τ8 απουσιες ----------
    P(''); P('################ Τ8 ΑΠΟΥΣΙΕΣ ################')
    PG = pd.read_csv('nba_player_games.csv', low_memory=False, usecols=['PLAYER_ID', 'TEAM_ABBREVIATION', 'GAME_DATE', 'MIN', 'stype'])
    PG = PG[PG.stype.astype(str) != 'PO']
    PG['team'] = PG.TEAM_ABBREVIATION.replace({'BKN': 'BRK', 'CHA': 'CHO', 'PHX': 'PHO'}); PG['d'] = pd.to_datetime(PG.GAME_DATE).values.astype('datetime64[D]')
    PG['MIN'] = pd.to_numeric(PG.MIN, errors='coerce').fillna(0)
    ABS = {}
    for t, g in PG.groupby('team'):
        gd = sorted(g.d.unique()); played = {d: dict(zip(x.PLAYER_ID, x.MIN)) for d, x in g.groupby('d')}
        hist = collections.defaultdict(list)                       # παικτης → [(ημερα, λεπτα)]
        for j, d in enumerate(gd):
            prev3 = gd[max(0, j - 3):j]; cur = played[d]; miss = 0.0; star = 0
            for pid, H in hist.items():
                rec = [m for dd, m in H[-10:]]
                if not rec: continue
                avg = float(np.mean(rec))
                if avg >= 20 and any(pid in played[x] and played[x][pid] > 0 for x in prev3) and cur.get(pid, 0) <= 0:
                    miss += avg; star |= avg >= 32
            ABS[(t, np.datetime64(d, 'D'))] = (miss, star)
            for pid, m in cur.items():
                if m > 0: hist[pid].append((d, m))
    dD = G.date.values.astype('datetime64[D]')
    AH = np.array([ABS.get((G.home.values[i], dD[i]), (0, 0))[0] for i in range(len(G))]); AA = np.array([ABS.get((G.away.values[i], dD[i]), (0, 0))[0] for i in range(len(G))])
    P(f'  νεα απουσια ανα ομαδα-ματς: {np.mean(np.r_[AH, AA] > 0) * 100:.0f}% · μεσα λεπτα οταν υπαρχει {np.mean(np.r_[AH, AA][np.r_[AH, AA] > 0]):.0f}′ · ≥30′ {np.mean(np.r_[AH, AA] >= 30) * 100:.0f}% · αστερας ≥32′ {np.mean([ABS.get((G.home.values[i], dD[i]), (0, 0))[1] for i in range(len(G))]) * 100:.0f}% (γηπ.)')
    P(f'  καλυψη: ματς με στοιχεια απουσιων {np.mean([(G.home.values[i], dD[i]) in ABS for i in range(len(G))]) * 100:.0f}% · ματς με νεα απουσια ≥20′ (καποια πλευρα) {np.mean((AH > 0) | (AA > 0)) * 100:.0f}%')
    # (α) ROI picks χαντικαπ ανοιγματος ανα κατασταση απουσιων της ΔΙΚΗΣ ΜΑΣ πλευρας
    for kind, V, nmk in (('h', HHt, 'ΧΑΝΤΙΚΑΠ'), ('t', T6, 'ΣΥΝΟΛΑ')):
        MK = MKH if kind == 'h' else MKT; C = collections.defaultdict(lambda: collections.defaultdict(list))
        late, late_tot, adv = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
        for i in MK:
            if S[i] not in EV or not np.isfinite(V[i]): continue
            p = pick(kind, V, i, 'o')
            if p:
                s_ = p[0]
                if kind == 'h':
                    mine, opp = (AH[i], AA[i]) if s_ == 1 else (AA[i], AH[i])
                    cat = 'η ΔΙΚΗ ΜΑΣ ομαδα εχει νεα απουσια' if mine > 0 else ('ο ΑΝΤΙΠΑΛΟΣ εχει νεα απουσια' if opp > 0 else 'καμια νεα απουσια')
                else:
                    tot_abs = AH[i] + AA[i]
                    cat = ('απουσια & παιξαμε OVER' if s_ == 1 else 'απουσια & παιξαμε UNDER') if tot_abs > 0 else 'καμια νεα απουσια'
                C[cat][S[i]].append(p[1])
                mv = (MK[i]['c'][1] - MK[i]['o'][1]) if kind == 'h' else (MK[i]['c'][0] - MK[i]['o'][0])
                against = (-mv * s_ if kind == 'h' else -mv * s_)    # χαντικαπ: γραμμη γηπ. L· s_=1 (γηπ.) — αν το L μειωνεται (κλεισ < ανοιγ) η γραμμη φευγει απο εμας
                if kind == 'h': against = (MK[i]['c'][0] - MK[i]['o'][0]) * s_     # γραμμη γηπ. L: για pick γηπ. (s_=1) L↑ = η αγορα φευγει απο εμας
                else: against = (MK[i]['c'][0] - MK[i]['o'][0]) * (-s_)
                if against >= 2: adv[S[i]].append(p[1])
            q = pick(kind, V, i, 'c')
            if q and not (p and p[0] == q[0]): late[S[i]].append(q[1])
        P(f'  [{nmk}] picks ανοιγματος (≥8%) ανα απουσιες:')
        for cat, Rr in C.items():
            u = [x for Y in EV for x in Rr[Y]]
            P(f'     {cat:38s} {np.mean(u) * 100:+.1f}% ({len(u)}, θετ {sum(1 for Y in EV if Rr[Y] and np.mean(Rr[Y]) > 0)}/5) · ' + ' '.join(f'{lab(Y)} {sum(Rr[Y]):+.1f}u' for Y in EV))
        u = [x for Y in EV for x in late[Y]]
        P(f'     «ΑΡΓΑ picks» (στο κλεισιμο, οχι στο ανοιγμα): {np.mean(u) * 100:+.1f}% ({len(u)}, θετ {sum(1 for Y in EV if late[Y] and np.mean(late[Y]) > 0)}/5)')
        u = [x for Y in EV for x in adv[Y]]
        P(f'     picks ανοιγματος οπου η γραμμη πηγε ≥2 π. ΚΟΝΤΡΑ μας: {np.mean(u) * 100:+.1f}% ({len(u)}, θετ {sum(1 for Y in EV if adv[Y] and np.mean(adv[Y]) > 0)}/5)')
    # (δ) φιλτρο χαντικαπ: χωρις pick αν η πλευρα μας εχει νεα απουσια ≥ Χ λεπτα
    P('  [ΦΙΛΤΡΟ χαντικαπ] «χωρις pick αν η πλευρα μας εχει νεα απουσια ≥Χ′»:')
    for X in (20, 30, 50):
        cut, keep = collections.defaultdict(list), collections.defaultdict(list)
        for i in MKH:
            if S[i] not in EV or not np.isfinite(HHt[i]): continue
            p = pick('h', HHt, i, 'o')
            if not p: continue
            mine = AH[i] if p[0] == 1 else AA[i]
            (cut if mine >= X else keep)[S[i]].append(p[1])
        uc = [x for Y in EV for x in cut[Y]]; uk = [x for Y in EV for x in keep[Y]]
        worse = sum(1 for Y in EV if cut[Y] and np.mean(cut[Y]) < np.mean(keep[Y] or [0]))
        ok = worse >= 4 and np.mean(uk) > roi('h', HHt)[0] / 100
        P(f'     Χ {X}′: κοβει {len(uc)} picks ({np.mean(uc) * 100 if uc else 0:+.1f}%) · μενουν {len(uk)} ({np.mean(uk) * 100:+.1f}%) · χειροτερα σε {worse}/5' + (' → ΠΕΡΝΑ' if ok else ' → ✗'))
        for nm2, msk in (('Οκτ-Δεκ', OD),):
            kk = [x for i in MKH if S[i] in EV and np.isfinite(HHt[i]) and msk[i] for p in [pick('h', HHt, i, 'o')] if p and (AH[i] if p[0] == 1 else AA[i]) < X for x in [p[1]]]
            P(f'        {nm2}: με το φιλτρο {np.mean(kk) * 100:+.1f}% ({len(kk)}) vs χωρις {rs(roi("h", HHt, OD))}')
    open('nba_more_tests_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))

if __name__ == '__main__':
    main()
