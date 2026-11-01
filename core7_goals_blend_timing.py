"""
core7_goals_blend_timing.py — ΤΕΣΤ 1/10/2026 (Στελιος: «δεν εχουμε δοκιμασει διαφορετικο blend xG/γκολ, ουτε τιμες πιο πριν απο το κλεισιμο»).
ΣΥΝΟΛΑ ΓΚΟΛ εγχωριων CORE7, αγων. 7+ (md≥6), 4 σεζον. Μηχανη LIVE (σωστο SoS 0.75) με τελικο μειγμα xG/γκολ BL ∈ {.4,.5,.6 (σημερα),.7,.8,.85,.9,1.0}
(ραμπα 100→BL, core7_mech_variant bl_<BL>) + «αγκυρα συνολων λ.5» πανω στο σημερα (core7_goals_fix_test Λ4).
ΣΤΙΓΜΕΣ ΑΓΟΡΑΣ (Nowgoal Crown & Bet365): ΑΝΟΙΓΜΑ · −48ω · −24ω · −6ω · ΚΛΕΙΣΙΜΟ (ωρα σεντρας FotMob).
ΜΕΤΡΑ: (1) ακριβεια LL συνολου ανα BL (ανα σεζον) · (2) πληροφορια περα απο την αγορα ΤΗ ΣΤΙΓΜΗ Τ:
  y(over) ~ p_αγορας + b·(p_μοντ − p_αγορας) στη γραμμη της στιγμης (Crown)· b>0 = το μοντελο ξερει κατι που η τοτε αγορα δεν ξερει
  (3) picks over/under στην τιμη της στιγμης (1.70-2.10, edge ≥ 5% / 10%) · ROI Crown | Bet365, 15+ και 7-14.
ΠΡΟ-ΔΗΛΩΣΗ: (α) ενα BL ειναι ΑΚΡΙΒΕΣΤΕΡΟ αν LL > σημερα σε ≥3/4 σεζον. (β) ΥΠΟΨΗΦΙΟ ΣΤΟΙΧΗΜΑΤΟΣ (εκδοχη × στιγμη × πλευρα × κατωφλι)
  αν στις 15+: ROI > 0 ΚΑΙ στα 2 βιβλια, θετικο ≥3/4 σεζον (Crown), n ≥ 60 (Crown) ΚΑΙ b της στιγμης > 0 με t ≥ 2.
  Πολλα κελια (~10×5×2×2) → ο,τι περασει = σκια. Δεν αλλαζει τιποτα live.
"""
import sys, os, json, glob, datetime
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
W = pd.read_csv('core7_goals_gap_rows.csv', dtype={'season': str, 'mid': str}).sort_values(['league', 'date']).reset_index(drop=True)
SEAS = sorted(W.season.unique()); N = len(W)
KO = {}
for f in glob.glob('data_*_*.json'):
    try: d = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    if not isinstance(d, dict): continue
    for k, v in d.items():
        try: KO[str(k)] = datetime.datetime.strptime(v['date'], '%a, %b %d, %Y, %H:%M UTC').replace(tzinfo=datetime.timezone.utc).timestamp()
        except Exception: pass
def pl(gs):
    try:
        p = [float(x) for x in str(gs).split('/')]; return sum(p) / len(p)
    except Exception: return None
SER = {}; mids = set(W.mid)
for f in glob.glob('nowgoal_odds/*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        try: r = json.loads(ln)
        except Exception: continue
        if r.get('cid') not in (3, 8) or not r.get('ou') or str(r['mid']) not in mids: continue
        rows = []
        for mt, ov, gl, un in r['ou']:
            L = pl(gl)
            try: oo, uu = float(ov) + 1, float(un) + 1
            except (TypeError, ValueError): continue
            if L is None or mt is None or oo <= 1 or uu <= 1: continue
            rows.append((mt, L, oo, uu))
        if rows: rows.sort(); SER[(str(r['mid']), 'Crown' if r['cid'] == 3 else 'Bet365')] = rows
TIMES = ['ανοιγμα', '−48ω', '−24ω', '−6ω', 'κλεισιμο']
def snap(mid, bk):
    seq = SER.get((mid, bk)); ko = KO.get(mid)
    if not seq: return {}
    out = {'ανοιγμα': seq[0][1:], 'κλεισιμο': seq[-1][1:]}
    if ko:
        for lab, h in (('−48ω', 48), ('−24ω', 24), ('−6ω', 6)):
            prev = [x for x in seq if x[0] <= ko - h * 3600]
            if prev and (ko - prev[-1][0]) / 3600 <= h + 48: out[lab] = prev[-1][1:]
    return out
SN = {(m, bk): snap(m, bk) for m in W.mid for bk in ('Crown', 'Bet365')}
IDX = np.add.outer(np.arange(13), np.arange(13))
def tdist(h, a):
    M = picks.score_matrix_dom(max(h, .05), max(a, .05)); return np.bincount(IDX.ravel(), weights=np.asarray(M).ravel(), minlength=25)
KS = np.arange(25)
def ou_eval(d, L, over, o, tg):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; e = s_ = 0
    for x in parts:
        pw = d[(KS > x + .01) if over else (KS < x - .01)].sum(); pp = d[np.abs(KS - x) < .01].sum()
        e += (pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)) / len(parts)
        m = (tg - x) if over else (x - tg); s_ += ((o - 1) if m > .01 else (0 if abs(m) < .01 else -1)) / len(parts)
    return e, s_
# εκδοχες
key = ['league', 'season', 'h', 'a', 'date']
VARS = {}
for bl in ('0.4', '0.5', '0.6', '0.7', '0.8', '0.85', '0.9', '1.0'):
    P = pd.read_csv(f'core7_mech_preds_bl_{bl}.csv', dtype={'mid': str})[['mid', 'xg_h', 'xg_a']]
    m = W[['mid']].merge(P, on='mid', how='left'); assert m.xg_h.notna().all()
    VARS[f'xG {int(float(bl)*100)}/{100-int(float(bl)*100)}' + (' (ΣΗΜΕΡΑ)' if bl == '0.6' else '')] = (m.xg_h.clip(.05, 6).values, m.xg_a.clip(.05, 6).values)
def tanchor(h, a, lam=0.5):
    T = h + a; out = T.copy()
    for lg, idx in W.groupby('league').groups.items():
        off = {}; cur = None
        for i in idx:
            r = W.loc[i]
            if r.season != cur: off = {}; cur = r.season
            t = T[i] + off.get(r.h, 0) + off.get(r.a, 0); out[i] = t
            if r.md >= 6:
                e = r.T_mkt - t; off[r.h] = off.get(r.h, 0) + lam * e / 2; off[r.a] = off.get(r.a, 0) + lam * e / 2
    s = h - a; return np.maximum((out + s) / 2, .05), np.maximum((out - s) / 2, .05)
BASE = 'xG 60/40 (ΣΗΜΕΡΑ)'
VARS['ΣΗΜΕΡΑ + αγκυρα συνολων'] = tanchor(*VARS[BASE])
if os.environ.get('GBT_TIMES'):           # 1/10: ανα ωρα πριν τη σεντρα — ποσο κοντα στο ματς αντεχει η αγκυρα συνολων;
    AH, AA = VARS['ΣΗΜΕΡΑ + αγκυρα συνολων']; tg = W.tg.values.astype(int)
    HRS = [240, 168, 120, 96, 72, 48, 36, 24, 12, 6, 3, 1, 0]
    rows = []
    for i in range(N):
        ko = KO.get(W.mid[i])
        if not ko: continue
        d = tdist(AH[i], AA[i])
        for bk in ('Crown', 'Bet365'):
            seq = SER.get((W.mid[i], bk))
            if not seq: continue
            Lc = seq[-1][1]
            for h in HRS:
                prev = [x for x in seq if x[0] <= (ko - h * 3600 if h else ko + 600)]
                if not prev or (h and (ko - prev[-1][0]) / 3600 > h + 24): continue
                _, L, oo, uu = prev[-1]
                for over, o in ((True, oo), (False, uu)):
                    if not (1.70 <= o <= 2.10): continue
                    e, s_ = ou_eval(d, L, over, o, tg[i])
                    if e >= 0.05:
                        rows.append(dict(h=h, book=bk, season=W.season[i], win='15+' if W.md[i] >= 14 else '7-14', edge=e, pnl=s_,
                                         clv=(1 if over else -1) * (Lc - L)))
    R = pd.DataFrame(rows)
    def fm(x):
        if len(x) < 5: return f'n{len(x):4d}        —       '
        ps = x.groupby('season').pnl.mean(); return f'n{len(x):4d} {100*x.pnl.mean():+6.1f}% {int((ps > 0).sum())}/4'
    for th in (0.10, 0.05):
        print(chr(10) + f'ΑΓΚΥΡΑ ΣΥΝΟΛΩΝ — pick στην τιμη που ισχυε Χ ωρες πριν (O+U, edge ≥{int(th*100)}%) · Crown | Bet365 · CLV γραμμης ως το κλεισιμο (Crown)')
        for h in HRS:
            x = R[(R.h == h) & (R.edge >= th)]
            c, b = x[x.book == 'Crown'], x[x.book == 'Bet365']
            c15, b15 = c[c.win == '15+'], b[b.win == '15+']
            print(f'  {("κλεισιμο" if h == 0 else f"−{h}ω"):9s} ολα 7+: {fm(c)} | {fm(b)} · CLV {c.clv.mean():+.3f} · μονο 15+: {fm(c15)} | {fm(b15)}')
    sys.exit()
if os.environ.get('GBT_ROBUST'):          # 1/10: ελεγχοι σταθεροτητας για την αγκυρα συνολων στο ανοιγμα
    AH, AA = VARS['ΣΗΜΕΡΑ + αγκυρα συνολων']; tg = W.tg.values.astype(int)
    rows = []
    for i in range(N):
        d = tdist(AH[i], AA[i]); ko = KO.get(W.mid[i])
        for bk in ('Crown', 'Bet365'):
            seq = SER.get((W.mid[i], bk))
            if not seq: continue
            (t0, L0, o0, u0), (t1, L1, o1, u1) = seq[0], seq[-1]
            for over, o in ((True, o0), (False, u0)):
                if not (1.70 <= o <= 2.10): continue
                e, s_ = ou_eval(d, L0, over, o, tg[i])
                if e < 0.05: continue
                sgn = 1 if over else -1
                clv_line = sgn * (L1 - L0)                                   # η γραμμη κινηθηκε ΥΠΕΡ μας (+)
                p0 = (1 / o0) / (1 / o0 + 1 / u0); p1 = (1 / o1) / (1 / o1 + 1 / u1)
                clv_p = sgn * (p1 - p0) if abs(L1 - L0) < 1e-9 else np.nan   # ιδια γραμμη: αλλαγη πιθανοτητας υπερ μας
                rows.append(dict(book=bk, season=W.season[i], league=W.league[i], win='15+' if W.md[i] >= 14 else '7-14',
                                 side='OVER' if over else 'UNDER', edge=e, pnl=s_, clv_line=clv_line, clv_p=clv_p,
                                 hrs=(ko - t0) / 3600 if ko else np.nan, o=o))
    R = pd.DataFrame(rows)
    def fm(x):
        if len(x) < 5: return f'n{len(x):4d}       —      '
        ps = x.groupby('season').pnl.mean(); return f'n{len(x):4d} {100*x.pnl.mean():+6.1f}% {x.pnl.sum():+6.1f}u {int((ps > 0).sum())}/4'
    print('ΑΓΚΥΡΑ ΣΥΝΟΛΩΝ — picks στην τιμη ΑΝΟΙΓΜΑΤΟΣ (edge ≥10% εκτος αν γραφει)')
    for win in ('15+', '7-14', None):
        for side in ('OVER', 'UNDER', None):
            x = R[(R.edge >= .10) & ((R.win == win) if win else True) & ((R.side == side) if side else True)]
            print(f'  {win or "ολα 7+":6s} {side or "O+U":5s} Crown {fm(x[x.book == "Crown"])} | Bet365 {fm(x[x.book == "Bet365"])} · '
                  f'CLV γραμμης {x.clv_line.mean():+.3f} γκολ (υπερ μας {100*(x.clv_line > 0).mean():.0f}% / κοντρα {100*(x.clv_line < 0).mean():.0f}%) · '
                  f'ωρες πριν διαμεσος {x.hrs.median():.0f}')
    x = R[(R.edge >= .10) & (R.book == 'Crown')]
    print('  ανα σεζον (Crown, ολα 7+ O+U): ' + ' · '.join(f'{s}: n{len(y)} {100*y.pnl.mean():+.1f}%' for s, y in x.groupby('season')))
    print('  ανα λιγκα (Crown, ολα 7+ O+U): ' + ' · '.join(f'{k}: n{len(y)} {100*y.pnl.mean():+.0f}%' for k, y in x.groupby('league')))
    print('  ανα ζωνη edge (Crown, ολα 7+): ' + ' · '.join(f'{lo:.0%}-{hi:.0%}: n{len(y)} {100*y.pnl.mean():+.1f}%' for lo, hi in ((.05, .10), (.10, .15), (.15, .25), (.25, 9))
                                                    for y in [R[(R.book == 'Crown') & (R.edge >= lo) & (R.edge < hi)]]))
    print('  ανα ωρες πριν (Crown, ≥10%): ' + ' · '.join(f'{lo}-{hi}ω: n{len(y)} {100*y.pnl.mean():+.1f}% CLV {y.clv_line.mean():+.3f}' for lo, hi in ((0, 48), (48, 96), (96, 168), (168, 9999))
                                                   for y in [x[(x.hrs >= lo) & (x.hrs < hi)]]))
    print('  κινηση πιθανοτητας στην ιδια γραμμη (Crown ≥10%, οσα δεν αλλαξαν γραμμη): ' + f'{100*x.clv_p.mean():+.2f} μον. (n{x.clv_p.notna().sum()})')
    sys.exit()
tg = W.tg.values.astype(int); SEA = W.season.values; M15 = (W.md >= 14).values
RES = {}
for lab, (h, a) in VARS.items():
    ll = np.zeros(N); rows = []; breg = {t: [] for t in TIMES}
    for i in range(N):
        d = tdist(h[i], a[i]); ll[i] = np.log(max(d[tg[i]], 1e-12))
        for bk in ('Crown', 'Bet365'):
            for t, q in SN[(W.mid[i], bk)].items():
                L, oo, uu = q
                if bk == 'Crown' and abs(L * 2 - round(L * 2)) < 1e-9 and (L * 2) % 2 == 1:      # μισες γραμμες (χωρις push) για το b
                    pm = d[KS > L].sum(); pk = (1 / oo) / (1 / oo + 1 / uu); breg[t].append((pk, pm, float(tg[i] > L), M15[i]))
                for over, o in ((True, oo), (False, uu)):
                    if not (1.70 <= o <= 2.10): continue
                    e, s_ = ou_eval(d, L, over, o, tg[i])
                    if e >= 0.05: rows.append((bk, t, SEA[i], '15+' if M15[i] else '7-14', 'OVER' if over else 'UNDER', e, s_))
    bb = {}
    for t, v in breg.items():
        v = np.array(v)
        for win, msk in (('όλα', np.ones(len(v), bool)), ('15+', v[:, 3] == 1)):
            x = v[msk]; X = np.column_stack([np.ones(len(x)), x[:, 0], x[:, 1] - x[:, 0]]); y = x[:, 2]
            b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b; cov = np.linalg.inv(X.T @ X) * (e @ e / (len(y) - 3))
            bb[(t, win)] = (b[2], b[2] / np.sqrt(cov[2, 2]), len(x))
    RES[lab] = dict(ll=ll, b=bb, pk=pd.DataFrame(rows, columns=['book', 'time', 'season', 'win', 'side', 'edge', 'pnl']))
    print(f'{lab} ok', flush=True)
base = RES[BASE]['ll']
print('\n(1) ΑΚΡΙΒΕΙΑ ΣΥΝΟΛΟΥ — LL (μεγαλυτερο = καλυτερο), Δ ×10⁻⁴ vs σημερα · ολα 7+ | 15+ · σεζον καλυτερες')
for lab in RES:
    ll = RES[lab]['ll']; bs = sum(ll[SEA == s].mean() > base[SEA == s].mean() + 1e-12 for s in SEAS)
    print(f'  {lab:26s} {ll.mean():.5f} (Δ {1e4*(ll.mean()-base.mean()):+6.1f}) | 15+ Δ {1e4*(ll[M15].mean()-base[M15].mean()):+6.1f} · {bs}/4 · ανα σεζον ' +
          ' '.join(f'{s}: {1e4*(ll[SEA == s].mean()-base[SEA == s].mean()):+5.1f}' for s in SEAS))
print('\n(2) ΠΛΗΡΟΦΟΡΙΑ ΠΕΡΑ ΑΠΟ ΤΗΝ ΑΓΟΡΑ ΤΗΣ ΣΤΙΓΜΗΣ — b (t) · Crown, μισες γραμμες · ολα 7+ / 15+')
print('  ' + ' ' * 26 + ''.join(f'{t:>22s}' for t in TIMES))
for lab in RES:
    print(f'  {lab:26s}' + ''.join(f'{RES[lab]["b"][(t, "όλα")][0]:+6.2f}({RES[lab]["b"][(t, "όλα")][1]:+4.1f})/{RES[lab]["b"][(t, "15+")][0]:+5.2f}' for t in TIMES))
print(f'  (n ανα στιγμη, ολα: ' + ' · '.join(f'{t} {RES[BASE]["b"][(t, "όλα")][2]}' for t in TIMES) + ')')
def fm(x):
    if len(x) < 5: return f'n{len(x):4d}        —      '
    ps = x.groupby('season').pnl.mean()
    return f'n{len(x):4d} {100*x.pnl.mean():+6.1f}% {int((ps > 0).sum())}/4'
passed = []
for win in ('15+', '7-14'):
    print(f'\n(3) PICKS O/U αγων. {win} στην τιμη της στιγμης — Crown | Bet365 (edge ≥10% · σε [ ] edge ≥5% Crown)')
    for side in ('OVER', 'UNDER'):
        print(f' [{side}]')
        for lab in RES:
            P = RES[lab]['pk']; cells = []
            for t in TIMES:
                x = P[(P.win == win) & (P.side == side) & (P.time == t)]
                c10 = x[(x.edge >= .10) & (x.book == 'Crown')]; b10 = x[(x.edge >= .10) & (x.book == 'Bet365')]; c5 = x[(x.edge >= .05) & (x.book == 'Crown')]
                cells.append(f'{t}: {fm(c10)} | {100*b10.pnl.mean() if len(b10) else 0:+5.1f}% [{100*c5.pnl.mean() if len(c5) else 0:+5.1f}%]')
                if win == '15+':
                    for th in (.05, .10):
                        cc = x[(x.edge >= th) & (x.book == 'Crown')]; b3 = x[(x.edge >= th) & (x.book == 'Bet365')]; bt = RES[lab]['b'][(t, '15+')]
                        if len(cc) >= 60 and cc.pnl.mean() > 0 and len(b3) and b3.pnl.mean() > 0 and int((cc.groupby('season').pnl.mean() > 0).sum()) >= 3 and bt[0] > 0 and bt[1] >= 2:
                            passed.append(f'{lab} · {t} · {side} · ≥{int(th*100)}%')
            print(f'   {lab:26s} ' + ' · '.join(cells))
print('\nΚΡΙΣΗ (α) ακριβεστερα BL: ' + (', '.join(l for l in RES if l != BASE and sum(RES[l]['ll'][SEA == s].mean() > base[SEA == s].mean() for s in SEAS) >= 3) or 'κανενα'))
print(f'ΚΡΙΣΗ (β) υποψηφια στοιχηματος: {passed or "ΚΑΝΕΝΑ"}')
