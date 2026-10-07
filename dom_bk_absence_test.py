# -*- coding: utf-8 -*-
"""dom_bk_absence_test.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ: ΑΠΟΥΣΙΕΣ ΠΑΙΚΤΩΝ (8/10/2026, Στελιος «τρεξτο ναι» — και «γιατι 20′; μπορει να παιζει ο 6ος-7ος»).
Δεδομενα: fs_bk_players.jsonl (Flashscore, λεπτα ανα παικτη, 10.023 ματς 6 λιγκες 2020-26) · προβλεψεις = τελικη βαση dom_bk_mech_v2 · αγορα nowgoal (MK).
ΝΕΑ ΑΠΟΥΣΙΑ (ιδιος ορισμος με NBA, κατωφλι C ανα παικτη ΤΩΡΑ ΜΕΤΑΒΛΗΤΟ): παικτης με μεσο ορο ≥C′ στα 10 τελευταια ματς που επαιξε, που
  επαιξε σε ενα απο τα 3 τελευταια ματς της ομαδας και ΔΕΝ παιζει σημερα· λεπτα απουσιας ομαδας = αθροισμα των μεσων ορων τους. C {15, 20, 25, 30}.
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ΠΡΙΝ την εκτελεση):
 Α ΑΓΟΡΑ: υπολοιπο κλεισιματος (πραγμ − κλεισ) πανω στη διαφορα λεπτων απουσιας (φιλοξ − γηπ): κλιση ≈ 0 → η αγορα τις τιμολογει σωστα.
 Β ΔΙΟΡΘΩΣΗ ΠΡΟΒΛΕΨΗΣ: μοντελο + β·(φιλοξ − γηπ λεπτα)/10, β LOSO → ΠΕΡΝΑ αν RMSE καλυτερο σε ≥4/5 σεζον (ανα C, ολα τα πρωταθληματα μαζι).
 Γ PICKS (μιξη 50/50, σ 12.3, ≥6%, ανοιγμα — ιδιος κανονας με τα προηγουμενα εγχωρια τεστ): ROI οταν η ΔΙΚΗ ΜΑΣ πλευρα / ο αντιπαλος / κανεις εχει απουσια.
 Δ ΦΙΛΤΡΟ «χωρις pick αν η πλευρα μας λειπει ≥Χ′» Χ {20, 30, 50}: ΠΕΡΝΑ αν τα picks που κοβει ειναι χειροτερα σε ≥4/5 σεζον ΚΑΙ το ROI που μενει ανεβαινει.
Εξοδος: dom_bk_absence_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, io, contextlib, math, json, collections
import numpy as np, pandas as pd
LGS = ['ACB', 'LBA', 'GBL', 'TBL', 'LNB', 'BBL']
class _Buf(io.StringIO):
    def reconfigure(self, **k): pass
_src = open('dom_bk_outrights_test_4lg.py', encoding='utf-8').read()
_src = _src.replace("ARGS = ['GBL', 'TBL', 'LNB', 'BBL']", f"ARGS = {LGS!r}", 1).replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass').split("KX = (0, 1, 2, 3, 4, 6)")[0]
with contextlib.redirect_stdout(_Buf()):
    exec(_src, globals())
FINAL = {'ACB': (.7, 12, 9999, .5, False, -8, 2), 'LBA': (1.0, 12, 120, None, False, 0, 0), 'GBL': (1.0, 4, 9999, None, True, 0, 0),
         'TBL': (1.0, 4, 60, .5, True, -8, 1), 'LNB': (1.0, 8, 9999, .5, True, 0, 0), 'BBL': (.85, 8, 9999, .5, False, -4, 0)}
CS = (15, 20, 25, 30); XS = (20, 30, 50)

def _job(lg):
    pr, gn, new, fin = run(lg, *FINAL[lg]); return lg, pr

def main():
    from multiprocessing import Pool
    sys.stdout.reconfigure(encoding='utf-8')
    O = []
    def W(s=''): print(s, flush=True); O.append(str(s))
    Phi_ = NS['Phi']
    with Pool(6) as pool: res = pool.map(_job, LGS)
    pred = np.full(len(G), np.nan)
    for lg, pr in res: m = G.lg.values == lg; pred[m] = pr[m]
    gidx = {i_: k for k, i_ in enumerate(G.id.values)}
    # ---- παικτες: ομαδα → λιστα (ts, {παικτης: λεπτα}) ----
    PL = {}
    for ln in open('fs_bk_players.jsonl', encoding='utf-8'):
        r = json.loads(ln)
        if not r['p']: continue
        tm = collections.defaultdict(lambda: [0.0, {}])
        for pid, nm, t3, mn, pts in r['p']:
            tm[t3][0] += pts or 0; tm[t3][1][pid] = mn or 0.0
        if len(tm) != 2: continue
        (a3, A), (b3, Bv) = tm.items()
        try: hs, as_ = int(r['hs']), int(r['as_'])
        except Exception: continue
        if abs(A[0] - hs) < .5 and abs(Bv[0] - as_) < .5: home, away = A[1], Bv[1]
        elif abs(Bv[0] - hs) < .5 and abs(A[0] - as_) < .5: home, away = Bv[1], A[1]
        else: continue
        PL[r['id']] = (r['ts'], r['hid'], r['aid'], home, away)
    W(f'ματς με παικτες & σωστη αντιστοιχιση γηπ/φιλοξ: {len(PL)}')
    team_games = collections.defaultdict(list)
    for gid, (ts, h, a, hp, ap) in PL.items():
        team_games[h].append((ts, gid, hp)); team_games[a].append((ts, gid, ap))
    for v in team_games.values(): v.sort()
    def missing(team, ts, today, C):
        g = [x for x in team_games[team] if x[0] < ts - 3600]
        if len(g) < 3: return None
        last3 = [x[2] for x in g[-3:]]; hist = collections.defaultdict(list)
        for _, _, pl in g:
            for p, mn in pl.items():
                if mn > 0: hist[p].append(mn)
        tot = 0.0
        for p in set().union(*[set(k for k, v in x.items() if v > 0) for x in last3]):
            if p in today and today[p] > 0: continue
            rec = hist[p][-10:]; avg = sum(rec) / len(rec)
            if avg >= C: tot += avg
        return tot
    rows = []
    for gid, (ts, h, a, hp, ap) in PL.items():
        k = gidx.get(gid)
        if k is None or k not in MK or not np.isfinite(pred[k]) or int(G.y.values[k]) not in EV: continue
        r = dict(y=int(G.y.values[k]), lg=G.lg.values[k], act=act[k], pr=pred[k], mc=MK[k]['mc'], mo=MK[k]['mo'], op=MK[k]['op'])
        ok = True
        for C in CS:
            mh, ma = missing(h, ts, hp, C), missing(a, ts, ap, C)
            if mh is None or ma is None: ok = False; break
            r[f'h{C}'], r[f'a{C}'] = mh, ma
        if ok: rows.append(r)
    R = pd.DataFrame(rows)
    W(f'ματς με αγορα, προβλεψη & ιστορικο παικτων: {len(R)}')
    for C in CS:
        W(f'  C {C}′: ματς με απουσια (καποια πλευρα) {((R[f"h{C}"] > 0) | (R[f"a{C}"] > 0)).mean():.0%} · μεσα λεπτα οταν υπαρχει '
          f'{np.mean([x for x in list(R[f"h{C}"]) + list(R[f"a{C}"]) if x > 0]):.0f}′')
    # ---- Α αγορα ----
    W(''); W('## Α. Η ΑΓΟΡΑ ΤΙΜΟΛΟΓΕΙ ΤΙΣ ΑΠΟΥΣΙΕΣ; (κλιση υπολοιπου ανα 10′ διαφορας απουσιας φιλοξ − γηπ· 0 = σωστα· + = η αγορα τις υποτιμα)')
    for C in CS:
        x = (R[f'a{C}'] - R[f'h{C}']) / 10
        for nm, col in (('κλεισιμο', 'mc'), ('ανοιγμα', 'mo'), ('ΜΟΝΤΕΛΟ μας', 'pr')):
            z = R.act - R[col]; b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x)
            se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
            ys = sum(np.polyfit(x[R.y == Y], z[R.y == Y], 1)[0] > 0 for Y in EV)
            W(f'  C {C}′ {nm:12s} κλιση {b:+.2f} π. ανα 10′ (t {b / se:+.1f}, θετ {ys}/5)')
    # ---- Β διορθωση προβλεψης ----
    W(''); W('## Β. ΔΙΟΡΘΩΣΗ ΠΡΟΒΛΕΨΗΣ: μοντελο + β·(φιλοξ − γηπ)/10 (LOSO, ≥4/5)')
    BS = (0, .5, 1, 1.5, 2, 3)
    rmy = lambda p, m: float(np.sqrt(np.mean((R.act[m] - p[m]) ** 2)))
    for C in CS:
        x = (R[f'a{C}'] - R[f'h{C}']) / 10; P_ = {b: R.pr + b * x for b in BS}; ch, d = [], []
        for Y in EV:
            tr = R.y.isin([z for z in EV if z != Y]); te = R.y == Y
            b = min(BS, key=lambda b: rmy(P_[b], tr)); ch.append(b); d.append(rmy(P_[b], te) - rmy(P_[0], te))
        W(f'  C {C}′: LOSO β {ch} · ' + ' '.join(f'{v:+.3f}' for v in d) + f' → {sum(v < 0 for v in d)}/5' + ('  <- ΠΕΡΝΑ' if sum(v < 0 for v in d) >= 4 else '  ✗'))
    # ---- Γ/Δ picks ----
    def picks():
        out = []
        for _, r in R.iterrows():
            L, o1, o2 = r.op; mm = r.mo + .5 * (r.pr - r.mo)
            if abs(L - round(L)) < 1e-9: pw = Phi_((mm + L - .5) / 12.3); pl = Phi_((-mm - L - .5) / 12.3)
            else: pw = Phi_((mm + L) / 12.3); pl = 1 - pw
            pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
            side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
            if e < .06: continue
            v = (r.act + L) * side; u = (od - 1) if v > 0 else (0 if v == 0 else -1)
            d_ = dict(y=r.y, u=u)
            for C in CS:
                d_[f'us{C}'] = r[f'h{C}'] if side == 1 else r[f'a{C}']; d_[f'op{C}'] = r[f'a{C}'] if side == 1 else r[f'h{C}']
            out.append(d_)
        return pd.DataFrame(out)
    K = picks()
    def cell(s):
        if not len(s): return '—'
        return f'{s.u.mean()*100:+.1f}% ({len(s)}, θετ {sum(1 for Y in EV if (s.y == Y).sum() >= 5 and s[s.y == Y].u.mean() > 0)}/5)'
    W(''); W(f'## Γ. PICKS (μιξη 50/50 ≥6%, ανοιγμα): ολα {cell(K)}')
    for C in CS:
        W(f'  C {C}′: η ΔΙΚΗ ΜΑΣ πλευρα εχει απουσια {cell(K[K[f"us{C}"] > 0])} · ο ΑΝΤΙΠΑΛΟΣ {cell(K[(K[f"op{C}"] > 0) & (K[f"us{C}"] == 0)])} · κανεις {cell(K[(K[f"us{C}"] == 0) & (K[f"op{C}"] == 0)])}')
    W(''); W('## Δ. ΦΙΛΤΡΟ «χωρις pick αν η πλευρα μας λειπει ≥Χ′»')
    for C in CS:
        for X in XS:
            cut = K[K[f'us{C}'] >= X]; keep = K[K[f'us{C}'] < X]
            worse = sum(1 for Y in EV if (cut.y == Y).sum() >= 3 and cut[cut.y == Y].u.mean() < K[K.y == Y].u.mean())
            ny = sum(1 for Y in EV if (cut.y == Y).sum() >= 3)
            ok = ny >= 4 and worse >= 4 and len(keep) and keep.u.mean() > K.u.mean()
            W(f'  C {C}′ Χ {X}′: κοβει {cell(cut)} · μενουν {cell(keep)} · χειροτερα σε {worse}/{ny}' + ('  <- ΠΕΡΝΑ' if ok else '  ✗'))
    open('dom_bk_absence_out.txt', 'w', encoding='utf-8').write(chr(10).join(O))

if __name__ == '__main__':
    main()
