# -*- coding: utf-8 -*-
"""dom_bk_motiv_timing.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ: ΚΙΝΗΤΡΟ ΤΕΛΟΥΣ ΣΕΖΟΝ & ΧΡΟΝΙΣΜΟΣ (7/10/2026, Στελιος «οκ δες και αυτα»).
Προβλεψεις = τελικη βαση dom_bk_mech_v2. Αγορα = nowgoal_dom Crown (cid 3), αλλιως Bet365 (cid 8)· γραμμη → αναμενομενη διαφορα (σ 12.2).
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ΠΡΙΝ την εκτελεση):
 Κ. ΚΙΝΗΤΡΟ (μονο κανονικη περιοδος, ματς με ≤8 εναπομειναντα για την ομαδα): βαθμολογια με νικες ως τη μερα του ματς.
    «νεκρη» = ΔΕΝ μπορει να φτασει τη θεση πλει οφ (νικες + υπολοιπα < νικες της ομαδας στη θεση PO) ΚΑΙ ΣΙΓΟΥΡΑ σωσμενη
    (νικες > νικες + υπολοιπα της πρωτης ομαδας στη ζωνη υποβιβασμου). Θεση PO: 8 (BBL/LNB 10 απο 2023-24, play-in)· υποβιβασμος: 2 τελευταιες.
    ΜΑΤΣ «νεκρη vs παλευει»: ΠΕΡΝΑ αν το υπολοιπο κλεισιματος υπερ της ομαδας που παλευει > 0 σε ≥4/5 σεζον 2021-26
    ΚΑΙ το ROI της ομαδας που παλευει στο ΚΛΕΙΣΙΜΟ > 0 σε ≥4/5 σεζον. (2020-21 = αναφορα εκτος δειγματος.)
 Χ. ΧΡΟΝΙΣΜΟΣ (ολα τα πρωταθληματα): σημεια ανοιγμα, 48ω, 24ω, 12ω, 6ω, 3ω, 1ω, κλεισιμο.
    (α) κινηση της γραμμης ΜΕΤΑ το σημειο προς το μοντελο: μεσος (μ_κλεισ − μ_Τ)·προσημο(μοντ − μ_Τ) για |μοντ − μ_Τ| ≥ 2 (+ = ερχεται προς εμας)
    (β) ROI picks στο σημειο (μιξη 50/50, σ 12.3, edge ≥6% — ιδιο με τα προηγουμενα τεστ, μονο για συγκριση σημειων).
    Σημειο ΚΑΛΥΤΕΡΟ απο το ανοιγμα αν ROI υψηλοτερο σε ≥4/5 σεζον. Εξοδος: dom_bk_motiv_timing_out.txt"""
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
ALLY = [2020] + EV

def _job(lg):
    pr, gn, new, fin = run(lg, *FINAL[lg]); return lg, pr

def cover_roi(m_, L, o1, o2, a):
    """μιξη ηδη μεσα στο m_· → (κερδος μοναδας ή None αν οχι pick)"""
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / 12.3); pl = Phi((-m_ - L - .5) / 12.3)
    else: pw = Phi((m_ + L) / 12.3); pl = 1 - pw
    pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    if e < .06: return None
    v = (a + L) * side
    return (od - 1) if v > 0 else (0 if v == 0 else -1)

def main():
    from multiprocessing import Pool
    sys.stdout.reconfigure(encoding='utf-8')
    O = []
    def W(s=''): print(s, flush=True); O.append(str(s))
    with Pool(6) as pool: res = pool.map(_job, LGS)
    pred = np.full(len(G), np.nan)
    for lg, pr in res: m = G.lg.values == lg; pred[m] = pr[m]
    LGV, YV, HID, AID, TT = G.lg.values, G.y.values, G.hid.values, G.aid.values, G.t.values
    RS = np.array(['lay' not in str(s).lower() and 'final' not in str(s).lower() and 'relegat' not in str(s).lower() for s in G.stage.values])
    # ======================= Κ. ΚΙΝΗΤΡΟ =======================
    status = {}                                                       # i → (κατασταση γηπ, κατασταση φιλοξ)
    for lg in LGS:
        for y in ALLY:
            sidx = np.where((LGV == lg) & (YV == y) & RS)[0]
            if not len(sidx): continue
            sidx = sidx[np.argsort(TT[sidx])]
            teams = sorted(set(HID[sidx]) | set(AID[sidx])); N = len(teams)
            tot = collections.Counter(list(HID[sidx]) + list(AID[sidx]))
            PO = 10 if (lg in ('BBL', 'LNB') and y >= 2023) else 8; REL = 2
            W_ = collections.Counter(); Pl = collections.Counter()
            days = pd.to_datetime(TT[sidx]).normalize()
            for d in sorted(set(days)):
                today = sidx[days == d]
                rank = sorted(teams, key=lambda t: -W_[t]); rem = {t: tot[t] - Pl[t] for t in teams}
                po_w = W_[rank[PO - 1]] if N >= PO else 0
                rel_top = rank[N - REL] if N > REL else None
                def st(t):
                    if rem[t] > 8: return 'early'
                    can_po = W_[t] + rem[t] >= po_w
                    safe = rel_top is not None and W_[t] > W_[rel_top] + rem[rel_top] and t != rel_top
                    return 'dead' if (not can_po and safe) else 'fight'
                for i in today: status[i] = (st(HID[i]), st(AID[i]))
                for i in today:
                    w = HID[i] if G.hs.values[i] > G.as_.values[i] else AID[i]
                    W_[w] += 1; Pl[HID[i]] += 1; Pl[AID[i]] += 1
    W('######## Κ. ΚΙΝΗΤΡΟ ΤΕΛΟΥΣ ΣΕΖΟΝ (τελευταια ≤8 ματς κανονικης) ########')
    rows = []
    for i, (sh, sa) in status.items():
        if i not in MK or YV[i] not in ALLY or 'early' in (sh, sa): continue
        if {sh, sa} != {'dead', 'fight'}: kind = 'both_' + sh
        else: kind = 'dead_vs_fight'
        s_f = (1 if sh == 'fight' else -1) if kind == 'dead_vs_fight' else 1      # προσανατολισμος: υπερ της ομαδας που παλευει
        L, o1, o2 = MK[i]['cl']; v = (act[i] + L) * s_f; od = o1 if s_f == 1 else o2
        rows.append(dict(y=int(YV[i]), lg=LGV[i], kind=kind, home_fight=(sh == 'fight'), rk=(act[i] - MK[i]['mc']) * s_f, rm=(act[i] - pred[i]) * s_f,
                         gap=(pred[i] - MK[i]['mc']) * s_f, u=(od - 1) if v > 0 else (0 if v == 0 else -1), line=MK[i]['mc'] * s_f))
    K = pd.DataFrame(rows)
    for kind in ('dead_vs_fight', 'both_fight', 'both_dead'):
        s = K[K.kind == kind]
        if not len(s): continue
        ins = s[s.y.isin(EV)]; t = ins.rk.mean() / (ins.rk.std() / math.sqrt(len(ins))) if len(ins) > 2 else 0
        py = {Y: s[s.y == Y].rk.mean() for Y in ALLY if (s.y == Y).sum() >= 5}; uy = {Y: s[s.y == Y].u.mean() for Y in ALLY if (s.y == Y).sum() >= 5}
        lab = {'dead_vs_fight': 'ΝΕΚΡΗ vs ΠΑΛΕΥΕΙ (υπερ της που παλευει)', 'both_fight': 'και οι δυο παλευουν (γηπ)', 'both_dead': 'και οι δυο νεκρες (γηπ)'}[kind]
        W(f'  {lab:40s} n {len(ins)} (+2020-21 {(s.y == 2020).sum()}) · υπολοιπο κλεισ. {ins.rk.mean():+.2f} (t {t:+.1f}) · μοντελο {ins.rm.mean():+.2f} · διαφ. μοντ−αγορας {ins.gap.mean():+.2f}')
        W('      ανα σεζον υπολοιπο ' + ' '.join(f'{Y % 100}:{v:+.1f}' for Y, v in py.items()) + ' · ROI κλεισ. ' + ' '.join(f'{Y % 100}:{v*100:+.0f}%' for Y, v in uy.items())
          + f' · ROI 2021-26 {ins.u.mean()*100:+.1f}%')
        if kind == 'dead_vs_fight':
            c1 = sum(1 for Y in EV if py.get(Y, -1) > 0) >= 4; c2 = sum(1 for Y in EV if uy.get(Y, -1) > 0) >= 4
            W(f'      ΚΡΙΣΗ υπολοιπο ≥4/5 {"✓" if c1 else "✗"} · ROI ≥4/5 {"✓" if c2 else "✗"} → ' + ('ΠΕΡΝΑ' if c1 and c2 else '✗'))
            for hf, nm in ((True, 'παλευει ΕΝΤΟΣ'), (False, 'παλευει ΕΚΤΟΣ')):
                q = ins[ins.home_fight == hf]
                if len(q) > 5: W(f'      {nm}: n {len(q)} · υπολοιπο {q.rk.mean():+.2f} · ROI {q.u.mean()*100:+.1f}%')
            for nm, q in (('φαβορι η που παλευει (γραμμη ≥3)', ins[ins.line >= 3]), ('κοντα', ins[ins.line.abs() < 3]), ('αουτσαιντερ η που παλευει', ins[ins.line <= -3])):
                if len(q) > 5: W(f'      {nm}: n {len(q)} · υπολοιπο {q.rk.mean():+.2f} · ROI {q.u.mean()*100:+.1f}%')
    # ======================= Χ. ΧΡΟΝΙΣΜΟΣ =======================
    W(''); W('######## Χ. ΧΡΟΝΙΣΜΟΣ (ολα τα πρωταθληματα, 2021-26) ########')
    D_, ROWS, idx, mu_of = NS['D_'], NS['ROWS'], NS['idx'], NS['mu_of']; globals()['Phi'] = NS['Phi']
    ng2i = {}
    for key, v in D_.items():
        lg, sea = key.split('_')
        if lg not in LGS: continue
        for g in v['games']:
            ng = int(g[0])
            if ng not in ROWS: continue
            try: hs, as_ = int(g[4]), int(g[5])
            except Exception: continue
            dd = pd.Timestamp(g[1]).normalize()
            hit = next((i for i in idx.get((lg, hs, as_), []) if abs((G.t.values[i] - dd) / np.timedelta64(1, 'D')) <= 1.5), None)
            if hit is not None: ng2i[hit] = ng
    PTS = [('ανοιγμα', None), ('48ω', 48), ('24ω', 24), ('12ω', 12), ('6ω', 6), ('3ω', 3), ('1ω', 1), ('κλεισιμο', 0)]
    mv = collections.defaultdict(list); RO = collections.defaultdict(lambda: collections.defaultdict(list)); nav = collections.Counter()
    for i, ng in ng2i.items():
        if YV[i] not in EV or not np.isfinite(pred[i]): continue
        tip = pd.Timestamp(TT[i]).timestamp(); cid = 3 if 3 in ROWS[ng] else 8
        R_ = sorted([x for x in ROWS[ng].get(cid, []) if x[4] == 2 and x[1] is not None and x[2] and x[3] and x[0] + 8 * 3600 <= tip + 600], key=lambda x: x[0])
        if not R_: continue
        def at(h):
            if h is None: return R_[0]
            c = [x for x in R_ if x[0] + 8 * 3600 <= tip - h * 3600]
            return c[-1] if c else None
        xc = R_[-1]; Lc = -xc[1]; muc = mu_of(Lc, 1 + xc[2], 1 + xc[3])
        for lab, h in PTS:
            x = at(h)
            if x is None or (h is not None and h > 0 and x is R_[0] and lab != 'ανοιγμα' and (tip - (x[0] + 8 * 3600)) > (h + 24) * 3600): continue
            L, o1, o2 = -x[1], 1 + x[2], 1 + x[3]; mu = mu_of(L, o1, o2); nav[lab] += 1
            g_ = pred[i] - mu
            if abs(g_) >= 2: mv[lab].append((muc - mu) * np.sign(g_))
            u = cover_roi(mu + .5 * g_, L, o1, o2, act[i])
            if u is not None: RO[lab][int(YV[i])].append(u)
    base = RO['ανοιγμα']
    for lab, h in PTS:
        a = [u for v in RO[lab].values() for u in v]
        better = sum(1 for Y in EV if RO[lab].get(Y) and base.get(Y) and np.mean(RO[lab][Y]) > np.mean(base[Y]))
        W(f'  {lab:9s} ματς {nav[lab]:5d} · κινηση ΠΡΟΣ το μοντελο μετα {np.mean(mv[lab]) if mv[lab] else 0:+.2f} π. (n {len(mv[lab])}) · ROI picks {np.mean(a)*100 if a else 0:+.1f}% ({len(a)}) · '
          + ' '.join(f'{Y % 100}:{np.mean(RO[lab][Y])*100:+.0f}%' for Y in EV if RO[lab].get(Y)) + ('' if lab == 'ανοιγμα' else f' · καλυτερο απο ανοιγμα {better}/5'))
    W(''); W('  ανα πρωταθλημα: κινηση προς μοντελο μετα το ανοιγμα / μετα τις 6ω')
    for lg in LGS:
        c = collections.defaultdict(list)
        for i, ng in ng2i.items():
            if LGV[i] != lg or YV[i] not in EV or not np.isfinite(pred[i]): continue
            tip = pd.Timestamp(TT[i]).timestamp(); cid = 3 if 3 in ROWS[ng] else 8
            R_ = sorted([x for x in ROWS[ng].get(cid, []) if x[4] == 2 and x[1] is not None and x[2] and x[3] and x[0] + 8 * 3600 <= tip + 600], key=lambda x: x[0])
            if not R_: continue
            muc = mu_of(-R_[-1][1], 1 + R_[-1][2], 1 + R_[-1][3])
            for lab, h in (('ανοιγμα', None), ('6ω', 6)):
                x = R_[0] if h is None else next((x for x in reversed(R_) if x[0] + 8 * 3600 <= tip - h * 3600), None)
                if x is None: continue
                mu = mu_of(-x[1], 1 + x[2], 1 + x[3]); g_ = pred[i] - mu
                if abs(g_) >= 2: c[lab].append((muc - mu) * np.sign(g_))
        W(f'  {NAME[lg]:9s} ανοιγμα {np.mean(c["ανοιγμα"]):+.2f} (n {len(c["ανοιγμα"])}) · 6ω {np.mean(c["6ω"]) if c["6ω"] else 0:+.2f} (n {len(c["6ω"])})')
    open('dom_bk_motiv_timing_out.txt', 'w', encoding='utf-8').write(chr(10).join(O))

if __name__ == '__main__':
    main()
