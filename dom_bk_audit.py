# -*- coding: utf-8 -*-
"""dom_bk_audit.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ: ΕΛΕΓΧΟΣ ΟΡΘΟΤΗΤΑΣ (10/10/2026, Στελιος: «εισαι σιγουρος οτι τα καναμε ολα σωστα; — τρεξτα ολα»).
Βαση = ΤΕΛΙΚΗ μηχανη dom_bk_mech_v2 (FINAL του dom_bk_miss_analysis). Ελεγχοι:
 Α ΔΕΔΟΜΕΝΑ ανα πρωταθλημα-σεζον: ματς, ομαδες, ματς ανα ομαδα (κανονικη), box %, διπλα ματς, αντιστοιχιση αγορας %.
 Β ΜΕΡΟΛΗΨΙΑ ΕΔΡΑΣ: μεση διαφορα πραγμ/μοντ/κλεισ. ΥΠΟΘΕΣΗ (πριν την εκτελεση): η «τυχη» (3P%/FT% προς τον μεσο λιγκας) τραβαει και το
   ΠΡΑΓΜΑΤΙΚΟ πλεονεκτημα εδρας στο σουτ προς τον μεσο → η μηχανη υποτιμα την εδρα οπου τυχη ≠ ωμο (ACB/TBL/LNB/BBL).
   ΔΙΟΡΘΩΣΗ Β1: ο «μεσος» της τυχης ξεχωριστα για γηπεδουχους και φιλοξενουμενους της λιγκας.
   ΠΡΟ-ΔΗΛΩΜΕΝΟ: Β1 ΜΠΑΙΝΕΙ αν RMSE ΟΛΩΝ των ματς καλυτερο σε ≥4/5 σεζον (2021-25) στο πρωταθλημα (μονο οσα εχουν τυχη).
 Γ ΤΟΥΡΚΙΑ/ΕΛΛΑΔΑ: τα 15 ματς με τη μεγαλυτερη διαφωνια μοντελου−κλεισιματος ανα σεζον με το μεγαλυτερο χασμα (ονοματα/ημερομηνιες) + τι λεει η αγορα.
 Δ ΔΙΑΡΡΟΗ: αποδοσεις νικητη μετα την πρεμιερα (ημερες) — ποσα ματς επηρεαζουν.
Εξοδος: dom_bk_audit_out.txt · dom_bk_audit_R.pkl (ανα ματς: προβλεψη FINAL & Β1, αγορα, ονοματα)"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, io, contextlib, math, json, collections, pickle
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
poss = lambda b: b['fga'] + 0.44 * b['fta'] - b['orb'] + b['tov']
def effs_ha(w):
    """Β1: τυχη με ΞΕΧΩΡΙΣΤΟ μεσο ορο γηπεδουχων / φιλοξενουμενων (3P%, FT%) ανα λιγκα-σεζον."""
    EH, EA, PC = np.zeros(len(G)), np.zeros(len(G)), np.zeros(len(G))
    for (lg, y), g in G.groupby(['lg', 'y']):
        bx = g[g.ok]
        if len(bx):
            p3h = sum(b['fg3'] for b in bx.hb) / max(1, sum(b['fg3a'] for b in bx.hb)); p3a = sum(b['fg3'] for b in bx.ab) / max(1, sum(b['fg3a'] for b in bx.ab))
            fth = sum(b['ft'] for b in bx.hb) / max(1, sum(b['fta'] for b in bx.hb)); fta = sum(b['ft'] for b in bx.ab) / max(1, sum(b['fta'] for b in bx.ab))
            pace = float(np.mean([(poss(h) + poss(a)) / 2 for h, a in zip(bx.hb, bx.ab)]))
        else:
            p3h = p3a = fth = fta = None; pace = 72.0
        for i, r in g.iterrows():
            if r.ok and w is not None:
                ps = (poss(r.hb) + poss(r.ab)) / 2
                def adj(pts, b, p3, ftp):
                    p3g = b['fg3'] / b['fg3a'] if b['fg3a'] else p3; ftg = b['ft'] / b['fta'] if b['fta'] else ftp
                    return pts - 3 * b['fg3'] + 3 * b['fg3a'] * (w * p3g + (1 - w) * p3) - b['ft'] + b['fta'] * (w * ftg + (1 - w) * ftp)
                EH[i], EA[i], PC[i] = 100 * adj(r.hs, r.hb, p3h, fth) / ps, 100 * adj(r.as_, r.ab, p3a, fta) / ps, ps
            else:
                ps = (poss(r.hb) + poss(r.ab)) / 2 if r.ok else pace
                EH[i], EA[i], PC[i] = 100 * r.hs / ps, 100 * r.as_ / ps, ps
    return EH, EA, PC

def _job(a):
    lg, var = a
    if var == 'B1':
        global EFF
        EFF = dict(EFF); EFF[.5] = effs_ha(.5); EFF[.25] = effs_ha(.25)
    pr, gn, new, fin = run(lg, *FINAL[lg])
    return lg, var, pr, gn

def main():
    from multiprocessing import Pool
    sys.stdout.reconfigure(encoding='utf-8')
    O = []
    def W(s=''): print(s, flush=True); O.append(str(s))
    jobs = [(lg, 'F') for lg in LGS] + [(lg, 'B1') for lg in LGS if FINAL[lg][3] is not None]
    with Pool(len(jobs)) as pool: res = pool.map(_job, jobs)
    PR = {(lg, v): (pr, gn) for lg, v, pr, gn in res}
    # ---- Α ΔΕΔΟΜΕΝΑ ----
    W('=== Α. ΔΕΔΟΜΕΝΑ ανα πρωταθλημα-σεζον (κανονικη + πλει οφ) ===')
    W('  λιγκα σεζον · ματς · ομαδες · ματς/ομαδα min-max · box % · διπλα (ιδιες ομαδες ιδια μερα) · με αγορα %')
    for lg in LGS:
        for y in EV:
            m = (G.lg.values == lg) & (G.y.values == y)
            if not m.any(): continue
            g = G[m]; c = collections.Counter(list(g.hid) + list(g.aid))
            dup = g.duplicated(subset=['hid', 'aid', 'd']).sum() + g.assign(k=[tuple(sorted(p)) for p in zip(g.hid, g.aid)]).duplicated(subset=['k', 'd']).sum()
            mk = np.mean([i in MK for i in np.where(m)[0]])
            W(f'  {lg} {y} · {m.sum():4d} · {len(c):2d} · {min(c.values())}-{max(c.values())} · box {g.ok.mean():4.0%} · διπλα {dup} · αγορα {mk:4.0%}')
    # ---- Β ΕΔΡΑ ----
    W(''); W('=== Β. ΜΕΡΟΛΗΨΙΑ ΕΔΡΑΣ (μεση διαφορα γηπ., ματς με αγορα) & ΔΙΟΡΘΩΣΗ Β1 (τυχη με χωριστο μεσο γηπ./φιλοξ.) ===')
    rows = []
    for lg in LGS:
        ii = np.array([i for i in MK if G.lg.values[i] == lg and G.y.values[i] in EV])
        a = act[ii]; mf = PR[(lg, 'F')][0][ii]; mc = np.array([MK[i]['mc'] for i in ii]); mo = np.array([MK[i]['mo'] for i in ii]); yy = G.y.values[ii]
        line = f'  {NAME[lg]:9s} τυχη {FINAL[lg][3]} · πραγμ {a.mean():+.2f} · μοντελο {mf.mean():+.2f} · κλεισ. {mc.mean():+.2f} · RMSE μοντ {np.sqrt(np.mean((a - mf) ** 2)):.3f} κλεισ {np.sqrt(np.mean((a - mc) ** 2)):.3f}'
        if (lg, 'B1') in PR:
            mb = PR[(lg, 'B1')][0][ii]
            d = [np.sqrt(np.mean((a - mb)[yy == y] ** 2)) - np.sqrt(np.mean((a - mf)[yy == y] ** 2)) for y in EV]
            # ολα τα ματς (και χωρις αγορα) για το κριτηριο
            mm = (G.lg.values == lg) & np.isin(G.y.values, EV)
            dall = [rm(PR[(lg, 'B1')][0], lg, [y]) - rm(PR[(lg, 'F')][0], lg, [y]) for y in EV]
            ok = sum(x < 0 for x in dall) >= 4
            line += (f'\n            Β1: μοντελο {mb.mean():+.2f} · RMSE {np.sqrt(np.mean((a - mb) ** 2)):.3f} · ΟΛΑ τα ματς ανα σεζον ' + ' '.join(f'{x:+.3f}' for x in dall)
                     + f' → {sum(x < 0 for x in dall)}/5 ' + ('<- ΜΠΑΙΝΕΙ' if ok else '✗'))
        else:
            mb = mf
        W(line)
        for k, i in enumerate(ii):
            rows.append(dict(i=int(i), lg=lg, y=int(G.y.values[i]), d=str(G.t.values[i])[:10], home=G.home.values[i], away=G.away.values[i], act=float(a[k]),
                             pf=float(mf[k]), pb=float(mb[k]), mc=float(mc[k]), mo=float(mo[k]), gn=int(PR[(lg, 'F')][1][i]), stage=G.stage.values[i]))
    R = pd.DataFrame(rows); pickle.dump(R, open('dom_bk_audit_R.pkl', 'wb'))
    # ---- Γ ΤΟΥΡΚΙΑ / ΕΛΛΑΔΑ ----
    W(''); W('=== Γ. ΜΕΓΑΛΕΣ ΔΙΑΦΩΝΙΕΣ μοντελου−κλεισιματος (Τουρκια/Ελλαδα + Γαλλια) ===')
    for lg in ('TBL', 'GBL', 'LNB'):
        x = R[R.lg == lg].copy(); x['gap'] = x.pf - x.mc
        for y in EV:
            z = x[x.y == y]
            W(f'  {NAME[lg]} {y}: |μοντ−κλεισ| μεσο {z.gap.abs().mean():.2f} · ≥6 π.: {int((z.gap.abs() >= 6).sum())} ματς · σε αυτα λαθος μοντ {np.sqrt(np.mean((z.act - z.pf)[z.gap.abs() >= 6] ** 2)) if (z.gap.abs() >= 6).any() else 0:.1f} vs κλεισ {np.sqrt(np.mean((z.act - z.mc)[z.gap.abs() >= 6] ** 2)) if (z.gap.abs() >= 6).any() else 0:.1f}')
        top = x.reindex(x.gap.abs().sort_values(ascending=False).index).head(15)
        for r in top.itertuples():
            W(f'      {r.d} {r.home[:22]:22s} – {r.away[:22]:22s} αγων {r.gn:2d} · μοντ {r.pf:+5.1f} · κλεισ {r.mc:+5.1f} · πραγμ {r.act:+4.0f} · {r.stage[:20]}')
        # ποιες ομαδες κουβαλανε τη διαφωνια
        tg = collections.defaultdict(list)
        for r in x.itertuples(): tg[r.home].append(r.gap); tg[r.away].append(-r.gap)
        bad = sorted(((np.mean(v), len(v), t) for t, v in tg.items() if len(v) >= 15), key=lambda q: -abs(q[0]))[:8]
        W('      ομαδες με μεγαλυτερη μεση διαφωνια (μοντελο − αγορα υπερ της ομαδας): ' + ' · '.join(f'{t[:18]} {m:+.1f} ({n})' for m, n, t in bad))
    # ---- Δ ΔΙΑΡΡΟΗ αποδοσεων νικητη ----
    W(''); W('=== Δ. ΑΠΟΔΟΣΕΙΣ ΝΙΚΗΤΗ: ημερομηνια vs πρεμιερα (θετικο = ΜΕΤΑ την πρεμιερα → μικρη διαρροη) ===')
    for lg in LGS:
        cells = []
        for sea, e in sorted(OUTR.get(lg, {}).items()):
            if not isinstance(e, dict) or 'days_vs_start' not in e: continue
            used = FINAL[lg][6] > 0
            cells.append(f"{sea[:4]}:{e['days_vs_start']:+d}" + ('' if used else ''))
        W(f'  {NAME[lg]:9s} (κx {FINAL[lg][6]}) ' + ' · '.join(cells))
    open('dom_bk_audit_out.txt', 'w', encoding='utf-8').write('\n'.join(O))

if __name__ == '__main__':
    main()
