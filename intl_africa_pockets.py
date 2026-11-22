"""
intl_africa_pockets.py — «ΤΣΕΠΕΣ» ΤΗΣ ΑΓΟΡΑΣ ΣΤΗΝ ΑΦΡΙΚΗ (25/9/2026, ερωτημα Στελιου: «στην Ευρωπη πιασαμε μεθοδους που δουλευαν — over κοντινα,
over νοκ-αουτ, dog δυο νεκρες κλπ — εδω δεν υπαρχει τιποτα τετοιο;»).
ΤΥΦΛΑ στοιχηματα ανα κατασταση (χωρις μοντελο), ιδια λογικη με τις τσεπες UEFA (22/9).

ΔΕΔΟΜΕΝΑ: 1.284 αφρικανικα ματς 2015-26 (AFCONQ, AFCON, WCQ_CAF) με γραμμες Nowgoal Crown/SBOBET (οπως intl_africa_lab).
  ΔΕΝ υπαρχει ιστορικο 1Χ2 (Nowgoal) → «Χ» δεν μετριεται· αντ' αυτου AH 0 / κοντινες γραμμες / under.
ΚΑΤΑΣΤΑΣΕΙΣ (προ-δηλωμενες): ολα · νοκ-αουτ AFCON · ομιλοι AFCON · προκριματικα · κοντινα (|ΔElo|<150, H3 επιπεδα προ ματς) ·
  αναντιστοιχια (≥300) · υψομετρο (γηπ ≥1500μ vs αντιπαλος <1000μ) · τελευταια αγωνιστικη ομιλου: ΔΥΟ ζωντανες / γηπ νεκρη / φιλοξ νεκρη / ΔΥΟ νεκρες ·
  γραμμη: φαβορι μεγαλο (≤−1.5) / μικρη γραμμη (|γρ|≤0.25).
ΑΓΟΡΕΣ (τυφλα): γηπεδουχος AH · φιλοξενουμενος AH · φαβορι AH · αουτσαιντερ AH · over · under.
ΤΙΜΗ: closing (τελευταια pre-match) — και «ανοιγμα παραθυρου 72ω» (πρωτη κινηση ≤72ω) για πληροφορια.
ΚΡΙΤΗΡΙΟ «ΤΣΕΠΗ»: ROI > 0 ΚΑΙ στα δυο βιβλια ΚΑΙ θετικο σε ≥4/5 κυκλους ΚΑΙ n ≥ 30 (ανα βιβλιο). ΠΡΟΣΟΧΗ: ~66 δοκιμες → ~3 «τυχαιες» τσεπες αναμενονται.
Εξοδος: intl_africa_pockets_out.txt
"""
import sys, os, json, contextlib, math, collections
import numpy as np, pandas as pd
sys.path.insert(0, '.')
src = open('intl_africa_lab.py', encoding='utf-8').read(); cut = src.index('# ================= 4. ΔΙΑΓΝΩΣΗ ΒΑΣΗΣ')
g = {'__name__': 'pockets'}
with contextlib.redirect_stdout(open(os.devnull, 'w', encoding='utf-8')):
    exec(src[:cut].replace("sys.stdout.reconfigure(encoding='utf-8'); ", ''), g)
sys.stdout.reconfigure(encoding='utf-8')
import picks
A, ROWS, OU, base_rec, M, AFR = (g[k] for k in ('A', 'ROWS', 'OU', 'base_rec', 'M', 'AFR'))
out = []
def P_(s=''):
    print(s, flush=True); out.append(str(s))

# ---- επιπεδα Elo / κατασταση ----
A['R_h'] = [base_rec[m][1] for m in A.mid]; A['R_a'] = [base_rec[m][2] for m in A.mid]; A['gap'] = (A.R_h - A.R_a).abs()
A['alt'] = [(pd.notna(r.elev) and r.elev >= 1500 and g['home_elev'].get(r.aid, 0) < 1000 and r.hsign == 1) for r in A.itertuples()]
RND = {}
import glob
for f in glob.glob('data_AFCON*.json') + glob.glob('data_WCQ_CAF*.json'):
    for mid, v in json.load(open(f, encoding='utf-8')).items():
        RND[str(mid)] = str(v.get('round'))
AFR = AFR.copy(); AFR['rnd'] = AFR.mid.map(RND); AFR['rnum'] = pd.to_numeric(AFR.rnd, errors='coerce'); AFR['gd'] = AFR.hs - AFR.ag
AFR['grpkey'] = AFR.comp + '_' + AFR.season.astype(str)
# νεκρα: ομιλοι απο union-find των ματς με αριθμημενο γυρο, βαθμολογια σειριακα (ζωντανη = μπορει ακομα να πιασει την προκριση/2 πρωτες)
flags = {}
for key, Gm in AFR[AFR.rnum.notna()].groupby('grpkey'):
    Gm = Gm.sort_values('date'); par = {}
    def find(x):
        while par.setdefault(x, x) != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for r in Gm.itertuples(): par[find(r.hid)] = find(r.aid)
    groups = collections.defaultdict(set)
    for r in Gm.itertuples(): groups[find(r.hid)].update([r.hid, r.aid])
    for teams in groups.values():
        teams = sorted(teams); n = len(teams)
        if n < 3 or n > 6: continue
        gm = Gm[Gm.hid.isin(teams) & Gm.aid.isin(teams)].sort_values('date')
        per_team = (n - 1) * (1 if 'AFCON_' in key and 'AFCONQ' not in key else 2); top = 2 if n >= 4 else 1
        pts = collections.Counter(); played = collections.Counter()
        for r in gm.itertuples():
            order = sorted(teams, key=lambda t: -pts[t]); rem = {t: per_team - played[t] for t in teams}; st = {}
            for t in (r.hid, r.aid):
                rank = order.index(t) + 1; alive = False
                if rank <= top and top < n and pts[order[top]] + 3 * rem[order[top]] >= pts[t]: alive = True
                if rank > top and pts[t] + 3 * rem[t] >= pts[order[top - 1]]: alive = True
                if rem[t] <= 0: alive = False
                st[t] = alive
            last = played[r.hid] + 1 >= per_team - 1 and played[r.aid] + 1 >= per_team - 1
            flags[r.mid] = (st[r.hid], st[r.aid], last)
            ph, pa = (3, 0) if r.gd > 0 else ((0, 3) if r.gd < 0 else (1, 1)); pts[r.hid] += ph; pts[r.aid] += pa; played[r.hid] += 1; played[r.aid] += 1
def motiv(m):
    f = flags.get(m)
    if not f or not f[2]: return ''
    ah, aa, _ = f
    return 'δυο ζωντανες' if (ah and aa) else ('γηπ νεκρη' if (not ah and aa) else ('φιλοξ νεκρη' if (ah and not aa) else 'δυο νεκρες'))
A['motiv'] = A.mid.map(motiv)
A['stage'] = np.where(A.comp == 'AFCON', np.where(A.KO > 0, 'νοκ-αουτ AFCON', 'ομιλοι AFCON'), 'προκριματικα')
P_(f'τελευταιες 2 αγωνιστικες ομιλων: {A.motiv.value_counts().to_dict()} · σταδια {A.stage.value_counts().to_dict()} · υψομετρο {int(A.alt.sum())}')

# ---- τυφλα στοιχηματα ----
rows = []
for r in A.itertuples():
    for cid, bk in (('3', 'Crown'), ('31', 'SBOBET')):
        for win, pick in (('closing', -1), ('72ω', 0)):
            ah = ROWS.get((r.mid, cid))
            if ah:
                cand = ah if win == 'closing' else [z for z in ah if z[0] <= 72]
                if cand:
                    h, L, oh, oa = cand[pick]
                    for side, ud, odds in ((1, L, oh), (-1, -L, oa)):
                        role = 'φαβ' if ud < 0 else ('dog' if ud > 0 else 'ισο')
                        rows.append(dict(mid=r.mid, cyc=r.cyc, book=bk, win=win, mkt='AH', who=('γηπ' if side == 1 else 'φιλοξ'), role=role, line=L,
                                         pnl=picks.settle(int(r.gd), side, ud, odds)))
            ou = OU.get((r.mid, cid))
            if ou:
                cand = ou if win == 'closing' else [z for z in ou if z[0] <= 72]
                if cand:
                    h, L, oo, uu = cand[pick]
                    for side, odds in (('over', oo), ('under', uu)):
                        q = round(L * 4) / 4
                        def st_(t, q, o, over):
                            if abs(q * 2 - round(q * 2)) > 1e-9: return 0.5 * st_(t, q - .25, o, over) + 0.5 * st_(t, q + .25, o, over)
                            w = t > q if over else t < q
                            return o - 1 if w else (0.0 if abs(t - q) < 1e-9 else -1.0)
                        rows.append(dict(mid=r.mid, cyc=r.cyc, book=bk, win=win, mkt=side, who='', role='', line=L, pnl=st_(int(r.tot), q, odds, side == 'over')))
BT = pd.DataFrame(rows).merge(A[['mid', 'stage', 'gap', 'alt', 'motiv']], on='mid')
SEG = {'ολα': lambda x: x.mid.notna(), 'νοκ-αουτ AFCON': lambda x: x.stage == 'νοκ-αουτ AFCON', 'ομιλοι AFCON': lambda x: x.stage == 'ομιλοι AFCON',
       'προκριματικα': lambda x: x.stage == 'προκριματικα', 'κοντινα (<150)': lambda x: x.gap < 150, 'αναντιστοιχια (≥300)': lambda x: x.gap >= 300,
       'υψομετρο': lambda x: x.alt, 'τελ. αγων: δυο ζωντανες': lambda x: x.motiv == 'δυο ζωντανες', 'τελ. αγων: γηπ νεκρη': lambda x: x.motiv == 'γηπ νεκρη',
       'τελ. αγων: φιλοξ νεκρη': lambda x: x.motiv == 'φιλοξ νεκρη', 'τελ. αγων: δυο νεκρες': lambda x: x.motiv == 'δυο νεκρες',
       'μεγαλο φαβορι (γρ ≤ −1.5)': lambda x: x.line.abs() >= 1.5, 'μικρη γραμμη (|γρ| ≤ 0.25)': lambda x: x.line.abs() <= 0.25}
MK = {'γηπεδουχος AH': lambda x: (x.mkt == 'AH') & (x.who == 'γηπ'), 'φιλοξενουμενος AH': lambda x: (x.mkt == 'AH') & (x.who == 'φιλοξ'),
      'φαβορι AH': lambda x: (x.mkt == 'AH') & (x.role == 'φαβ'), 'αουτσαιντερ AH': lambda x: (x.mkt == 'AH') & (x.role == 'dog'),
      'over': lambda x: x.mkt == 'over', 'under': lambda x: x.mkt == 'under'}
found = []
for win in ('closing', '72ω'):
    P_('\n' + '=' * 110); P_(f'ΤΥΦΛΑ — {win} · ROI μεσος Crown/SBOBET (n ανα βιβλιο, θετικοι κυκλοι) · ✓ = ΤΣΕΠΗ (και τα 2 βιβλια > 0, ≥4/5 κυκλοι, n≥30)'); P_('=' * 110)
    for sn, sf in SEG.items():
        cells = []
        for mn, mf in MK.items():
            x = BT[(BT.win == win) & sf(BT) & mf(BT)]
            c, s = x[x.book == 'Crown'], x[x.book == 'SBOBET']
            if len(c) < 10 or len(s) < 10:
                cells.append(f'{mn}: —'); continue
            cy = x.groupby('cyc').pnl.mean(); pos = int((cy > 0).sum())
            roi = (c.pnl.mean() + s.pnl.mean()) / 2 * 100
            ok = c.pnl.mean() > 0 and s.pnl.mean() > 0 and pos >= 4 and len(c) >= 30 and len(s) >= 30
            if ok and win == 'closing': found.append((sn, mn, roi, len(c), pos, cy.size))
            cells.append(f"{mn}: {roi:+5.1f}% n{len(c)} {pos}/{cy.size}{' ✓' if ok else ''}")
        P_(f'{sn:26s} ' + ' · '.join(cells))
P_('\nΤΣΕΠΕΣ (closing, κριτηριο): ' + ('ΚΑΜΙΑ' if not found else ' | '.join(f'{a} → {b} {r:+.1f}% (n{n}, {p}/{c})' for a, b, r, n, p, c in found)))
P_(f'(αναμενομενες τυχαιες «τσεπες» με {len(SEG) * len(MK)} δοκιμες: ~{len(SEG) * len(MK) * 0.05:.0f})')
open('intl_africa_pockets_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
