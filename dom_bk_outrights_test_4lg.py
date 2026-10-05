# -*- coding: utf-8 -*-
"""dom_bk_outrights_test.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ «ΑΠΟ ΤΗΝ ΑΡΧΗ», βημα 8: ΑΠΟΔΟΣΕΙΣ ΠΡΩΤΑΘΛΗΤΗ ως «γνωμη ειδικων» (5/10/2026, Στελιος «ναι»).
Δεδομενα: dom_outrights.json (bwin-group μεσω Wayback, πριν την πρεμιερα· ACB 2020-21 oddschecker· ΛΕΙΠΕΙ ACB 2023-24).
z = −ln(αποδοση) τυποποιημενο μεσα στη σεζον (ομαδα χωρις τιμη → το χαμηλοτερο z) · αφετηρια += κx·z ποντοι/ματς (×100/72 ανα 100 κατοχες), οπως EuroCup.
Βαση: Ισπανια = σημερινη + ποινη νεοφερμενων −8 · Ιταλια = (περσι 1.0, λ 12, HL 120, ωμο).
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση), ανα πρωταθλημα: (Α) πλεγμα κx {0,1,2,3,4,6} πανω στη βαση · LOSO 2021-26 με RMSE ΑΓΩΝ 1-10 → ΑΛΛΑΓΗ αν
  καλυτερο απο κx=0 σε ≥80% των σεζον ΠΟΥ ΕΧΟΥΝ αποδοσεις (Ισπανια 4/4, Ιταλια 4/5) ΚΑΙ το RMSE ολων των ματς να μη χειροτερευει.
  (Β) αναφορα: κοινη επιλογη περσι {.35,.5,.7,1} × κx (μηπως οι αποδοσεις αντικαθιστουν το περσι) · (Γ) Ισπανια: ποινη νεοφερμενων με/χωρις.
Εξοδος: dom_bk_outrights_test_out.txt"""
import sys, json, math, io, contextlib
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
ARGS = ['GBL', 'TBL', 'LNB', 'BBL']
src = open('dom_bk_engine_test.py', encoding='utf-8').read()
head = src.split("LIVE = (.7, 8, 9999, .5, False)")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
mk = src[src.index("# ---- αγορα (για αναφορα) ----"):src.index("for lg in ARGS:\n    P(''); P(f'############")]
NS = {'__name__': 'x'}
sys.argv = [sys.argv[0]] + ARGS
if True:
    exec(head, NS); exec(mk, NS)
G, EFF, YRS, NAME, fit, act, rm, EV, P, out, market_report, MK = (NS[k] for k in ('G', 'EFF', 'YRS', 'NAME', 'fit', 'act', 'rm', 'EV', 'P', 'out', 'market_report', 'MK'))
out.clear()
NAME.update(GBL='Ελλαδα', TBL='Τουρκια', LNB='Γαλλια', BBL='Γερμανια')
BASE = {'GBL': (1.0, 4, 9999, None, True), 'TBL': (1.0, 4, 60, .5, True), 'LNB': (.7, 8, 9999, .5, False), 'BBL': (.7, 8, 9999, .5, False)}
def run(lg, carry, lam, HL, w, team_home, delta, kx=0.0):
    EH, EA, PC = EFF[w]
    idx_all = np.where(G.lg.values == lg)[0]; pred = np.full(len(G), np.nan); gn = np.zeros(len(G), int); new = np.zeros(len(G), bool)
    prior, h0, mu0 = {}, 4.0, float(np.mean(np.r_[EH[idx_all], EA[idx_all]])); fin = {}
    for y in YRS:
        sidx = idx_all[G.y.values[idx_all] == y]
        if not len(sidx): continue
        teams = sorted(set(G.hid.values[sidx]) | set(G.aid.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        hi = np.array([ix[t] for t in G.hid.values[sidx]]); ai = np.array([ix[t] for t in G.aid.values[sidx]])
        isnew = {t: (y > YRS[0] and t not in prior) for t in teams}
        o0 = np.array([delta / 2 if isnew[t] else carry * prior.get(t, (0, 0))[0] for t in teams])
        d0 = np.array([-delta / 2 if isnew[t] else carry * prior.get(t, (0, 0))[1] for t in teams])
        sh = np.array([kx * Z.get((y, t), 0.0) * 100 / 72 / 2 for t in teams]); o0 = o0 + sh; d0 = d0 - sh
        dn = G.d.values[sidx]; eh, ea, pc = EH[sidx], EA[sidx], PC[sidx]
        cnt = {}
        for j, i in enumerate(sidx):
            a_, b_ = G.hid.values[i], G.aid.values[i]; cnt[a_] = cnt.get(a_, 0) + 1; cnt[b_] = cnt.get(b_, 0) + 1; gn[i] = max(cnt[a_], cnt[b_])
            new[i] = isnew[a_] or isnew[b_]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                ww = 0.5 ** ((d - dn[past]) / HL)
                mu, h, O, D, Hh = fit(hi[past], ai[past], eh[past], ea[past], ww, n, o0, d0, h0, mu0, lam, team_home); pace = float(np.mean(pc[past][-200:]))
            else:
                mu, h, O, D, Hh, pace = mu0, h0, o0, d0, np.zeros(n), float(np.mean(PC[idx_all]))
            for j in cur:
                pred[sidx[j]] = pace * ((h + Hh[hi[j]] + O[hi[j]] + D[ai[j]]) - (O[ai[j]] + D[hi[j]])) / 100
        mu, h, O, D, Hh = fit(hi, ai, eh, ea, 0.5 ** ((dn.max() - dn) / HL), n, o0, d0, h0, mu0, lam, team_home)
        prior = {t: (O[i], D[i]) for t, i in ix.items()}; h0, mu0 = h, mu
        pm = float(np.mean(pc))
        for t, i in ix.items(): fin[(y, t)] = ((O[i] - D[i]) * pm / 100, isnew[t])
    return pred, gn, new, fin
# ---- αποδοσεις πρωταθλητη → z ----
import unicodedata, re
ALIAS = {'Barcelona': ['barcelon'], 'Real Madrid': ['real madrid', '=real'], 'Real Betis': ['betis'], 'Baskonia': ['baskonia'], 'Valencia': ['valencia', 'valence'],
         'Unicaja': ['unicaja', 'malaga'], 'Tenerife': ['tenerif'], 'Basket Zaragoza': ['zaragoza'], 'MoraBanc Andorra': ['andorra'], 'Gran Canaria': ['canaria'],
         'San Pablo Burgos': ['burgos'], 'Manresa': ['manresa'], 'Bilbao': ['bilbao'], 'Murcia': ['murcia'], 'Joventut Badalona': ['joventut'],
         'Estudiantes': ['estudiantes'], 'Obradoiro CAB': ['obradoiro', 'obraidoro'], 'Fuenlabrada': ['fuenlabrada', 'feunlabrada'], 'Breogan': ['breog'],
         'Basquet Girona': ['girona'], 'Granada': ['granada'], 'Palencia': ['palencia'], 'Forca Lleida': ['lleida'], 'Leyma Coruna': ['coruna'], 'Gipuzkoa': ['gipuzkoa'],
         'Olimpia Milano': ['milan'], 'Virtus Bologna': ['virtus bologna', '=bologna'], 'Fortitudo Bologna': ['fortitudo'], 'Sassari': ['sassari'],
         'Venezia': ['venezia', 'reyer'], 'Brescia': ['brescia'], 'Brindisi': ['brindisi'], 'Trento': ['trento'], 'Varese': ['varese'], 'Treviso': ['treviso'],
         'Cantu': ['cantu'], 'Reggiana': ['reggian', 'reggio'], 'Pesaro': ['pesaro'], 'Trieste': ['trieste'], 'Cremona': ['cremona'], 'Virtus Roma': ['=roma'],
         'Basket Napoli': ['napol', 'poles'], 'Tortona': ['tortona', 'derthona'], 'Scafati': ['scafati'], 'Verona': ['verona'], 'Pistoia': ['pistoia'],
         'Trapani': ['trapan'], 'Udine': ['udine']}
def norm(s): return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower().strip()
OUTR = json.load(open('dom_outrights.json', encoding='utf-8'))
Z = {}
for lg in ARGS:
    for sea, e in OUTR[lg].items():
        y = int(sea[:4]); m = (G.lg.values == lg) & (G.y.values == y)
        ids = {}
        for nm, tid in zip(np.r_[G.home.values[m], G.away.values[m]], np.r_[G.hid.values[m], G.aid.values[m]]): ids[nm] = tid
        od = e['odds'] if isinstance(e['odds'], dict) else dict(e['odds'])
        got, miss = {}, []
        for on, o in od.items():
            n_ = norm(on); hit = [fs for fs in ids if any((k[1:] == n_) if k.startswith('=') else (k in n_) for k in ALIAS.get(fs, [w for w in norm(fs).split() if len(w) >= 4] or [norm(fs)]))]
            if len(hit) == 1: got[ids[hit[0]]] = float(o)
            else: miss.append(on)
        if len(got) < .8 * len(ids): P(f'  {lg} {sea}: ΛΙΓΕΣ ({len(got)}/{len(ids)}) — εκτος'); continue
        v = {t: -math.log(o) for t, o in got.items()}; mu_, sd_ = np.mean(list(v.values())), np.std(list(v.values()))
        zz = {t: (x - mu_) / sd_ for t, x in v.items()}; zmin = min(zz.values())
        for t in ids.values(): Z[(y, t)] = zz.get(t, zmin)
        P(f'  {lg} {sea}: αντιστοιχιση {len(got)}/{len(ids)}' + (f' · χωρις: {miss}' if miss else '') + (f' · χωρις τιμη (→ min z): {[n for n, t in ids.items() if t not in got]}' if len(got) < len(ids) else ''))
KX = (0, 1, 2, 3, 4, 6); CARS = (.35, .5, .7, 1.0)
BASE = {'GBL': (1.0, 4, 9999, None, True, 0), 'TBL': (1.0, 4, 60, .5, True, 0), 'LNB': (.7, 8, 9999, .5, False, 0), 'BBL': (.7, 8, 9999, .5, False, 0)}
def loso(PR, lg, gn, keys, basek, crit_ys):
    rmm = lambda v, ys, msk=None: rm(v, lg, ys, msk)
    held = np.full(len(G), np.nan); ch = []
    for Y in EV:
        tr = [x for x in EV if x != Y]; k = min(keys, key=lambda k: rmm(PR[k][0], tr, gn <= 10)); ch.append(k)
        mm = (G.lg.values == lg) & (G.y.values == Y); held[mm] = PR[k][0][mm]
    base = PR[basek][0]
    for lab, msk in (('αγων 1-10', gn <= 10), ('ΟΛΑ', None)):
        d = [rmm(held, [Y], msk) - rmm(base, [Y], msk) for Y in EV]
        P(f'    LOSO {lab:10s} {ch} · {rmm(base, EV, msk):.3f} → {rmm(held, EV, msk):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5')
    d10 = [rmm(held, [Y], gn <= 10) - rmm(base, [Y], gn <= 10) for Y in crit_ys]
    need = math.ceil(.8 * len(crit_ys)); ok = sum(x < 0 for x in d10) >= need and rmm(held, EV) <= rmm(base, EV)
    P(f'    ΚΡΙΣΗ (σεζον με αποδοσεις {len(crit_ys)}, χρειαζεται {need}): {sum(x < 0 for x in d10)} → {"ΑΛΛΑΓΗ" if ok else "✗"}')
    return held, base
for lg in ARGS:
    car, lam, HL, w, th, dl = BASE[lg]
    crit = sorted({y for (y, t) in Z if y in EV and ((G.lg.values == lg) & (G.hid.values == t)).any()})
    P(''); P(f'############ {NAME[lg]} · βαση {BASE[lg]} · σεζον με αποδοσεις {crit} ############')
    PR = {kx: run(lg, car, lam, HL, w, th, dl, kx) for kx in KX}
    gn = PR[0][1]
    rmm = lambda v, ys, msk=None: rm(v, lg, ys, msk)
    P('  IN-SAMPLE ανα κx (ποντοι/ματς ανα z): αγων 1-10 · ολα')
    for kx in KX: P(f'    κx {kx}: {rmm(PR[kx][0], EV, gn <= 10):.3f} · {rmm(PR[kx][0], EV):.3f}')
    P('  (Α) ΜΟΝΟ κx, ιδια βαση:')
    held, base = loso(PR, lg, gn, KX, 0, crit)
    market_report(base, lg, 'κx 0 (σημερα)'); market_report(held, lg, 'LOSO κx')
    for kx in (2, 4): market_report(PR[kx][0], lg, f'κx {kx}')
    P('  (Β) ΜΑΖΙ με περσι (περσι × κx) — αναφορα:')
    PRJ = {(c, kx): (PR[kx] if c == car else run(lg, c, lam, HL, w, th, dl, kx)) for c in CARS for kx in KX}
    P('    in-sample αγων 1-10 (κx 0/1/2/3/4/6): ' + ' · '.join(f'περσι {c}: ' + '/'.join(f'{rmm(PRJ[(c, kx)][0], EV, gn <= 10):.2f}' for kx in KX) for c in CARS))
    heldJ, _ = loso(PRJ, lg, gn, list(PRJ), (car, 0), crit)
    market_report(heldJ, lg, 'LOSO περσι×κx')
    if lg == 'ACB':
        P('  (Γ) Ισπανια ΧΩΡΙΣ ποινη νεοφερμενων (μηπως οι αποδοσεις την καλυπτουν):')
        PR0 = {kx: run(lg, car, lam, HL, w, th, 0, kx) for kx in KX}
        P('    in-sample αγων 1-10 δ0: ' + ' · '.join(f'κx {kx} {rmm(PR0[kx][0], EV, gn <= 10):.3f}' for kx in KX))
        P('    in-sample αγων 1-10 δ−8: ' + ' · '.join(f'κx {kx} {rmm(PR[kx][0], EV, gn <= 10):.3f}' for kx in KX))
open('dom_bk_outrights_test_4lg_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
