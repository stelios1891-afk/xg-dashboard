"""core7_totals_league_anchor.py — 15/10/2026 (Στελιος: «δοκιμασε» — αγκυρα ΕΠΙΠΕΔΟΥ ΛΙΓΚΑΣ στα συνολα).
Ιδεα: φετος ολη η λιγκα σκοραρει περισσοτερο· το μοντελο (περσινο prior + περσινοι μεσοι) δεν το βλεπει, η αγορα ναι. Αντι για διορθωση ανα ομαδα
(θορυβος στα πρωτα ματς), ΜΙΑ διορθωση ανα λιγκα-σεζον που μαθαινει απο την 1η αγωνιστικη:
   off_λιγκας(t) = Σ (συνολο αγορας κλεισιμο − συνολο μοντελου) / (n + n0)   πανω σε ΟΛΑ τα ματς της λιγκας που ΤΕΛΕΙΩΣΑΝ πριν τη στιγμη t
   (n0 = «σμικρυνση»: με λιγα ματς η διορθωση μενει κοντα στο 0)
ΤΙΜΙΟΣ ΧΡΟΝΟΣ (ιδιος με core7_totals_anchor_md1_test Γ): pick στην τιμη 06:00 UTC μετα το προηγουμενο ματς ΚΑΙ των δυο ομαδων· η διορθωση λιγκας
χρησιμοποιει μονο ματς με σεντρα+2ω πριν απο εκεινη τη στιγμη.
ΕΚΔΟΧΕΣ:  Γ1 = σημερινη προταση (αγκυρα ομαδας απο 7η) · Λ(n0) = μονο λιγκα · Λ+Γ1 = λιγκα + αγκυρα ομαδας απο 7η (μαθαινει το υπολοιπο)
ΚΑΝΟΝΕΣ picks ιδιοι: edge ≥10%, 1.70-2.10, Crown | Bet365, καλυτερη πλευρα. Αγωνιστικες 7+ (και 4-6 ενημερωτικα).
ΑΚΡΙΒΕΙΑ: μεροληψια (μοντελο − πραγματικα), απισταση απο αγορα, log-πιθανοφανεια συνολου γκολ vs Γ1 ανα σεζον.
LOSO: n0 απο τις αλλες 3 σεζον (μοναδες, μεσος βιβλιων).
"""
import sys, os
_s = open('core7_totals_anchor_md1_test.py', encoding='utf-8').read()
_TO = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s[:_s.index('rows = []; prestale = []')]); sys.stdout = _TO
sys.stdout.reconfigure(encoding='utf-8')
TGA = {}
for f in glob.glob('data_*_*.json'):
    try: d = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    if not isinstance(d, dict): continue
    for k, v in d.items():
        try: TGA[str(k)] = int(v['hs']) + int(v['as'])
        except Exception: pass
P['tg'] = P.mid.map(TGA)
RAW = (P.xg_h + P.xg_a).values
def pick_time(prev, ko):
    t_av = prev + 2 * 3600
    d0 = datetime.datetime.fromtimestamp(t_av, datetime.timezone.utc); nxt = d0.replace(hour=6, minute=0, second=0)
    if nxt.timestamp() <= t_av: nxt += datetime.timedelta(days=1)
    return nxt.timestamp()
PT = np.array([pick_time(r.prev, r.ko) for r in P.itertuples()])
# ανα λιγκα-σεζον: λιστα (σεντρα+2ω, λαθος συνολου) για ματς με κλεισιμο
GRP = {}
for i, r in enumerate(P.itertuples()):
    if r.T_mkt == r.T_mkt: GRP.setdefault((r.league, r.season), []).append((r.ko + 2 * 3600, r.T_mkt - RAW[i]))
for k in GRP: GRP[k].sort()
def league_off(n0):
    out = np.zeros(len(P))
    for i, r in enumerate(P.itertuples()):
        lst = GRP.get((r.league, r.season), []); e = [x[1] for x in lst if x[0] <= PT[i]]
        out[i] = sum(e) / (len(e) + n0) if (len(e) + n0) > 0 else 0.0
    return out
def team_anchor(base, start_md=6, lam=0.5):
    """αγκυρα ομαδας (ιδια με το τεστ) πανω σε βαση base· μαθαινει (αγορα − base − off ομαδων)"""
    out = np.zeros(len(P)); off = {}; cur = None
    for i, r in enumerate(P.itertuples()):
        k = (r.league, r.season)
        if k != cur: off = {}; cur = k
        t = base[i] + off.get(r.home, 0) + off.get(r.away, 0); out[i] = t
        if r.md >= start_md and r.T_mkt == r.T_mkt:
            e = r.T_mkt - t; off[r.home] = off.get(r.home, 0) + lam * e / 2; off[r.away] = off.get(r.away, 0) + lam * e / 2
    return out
N0S = (0, 10, 30, 60)
V = {'Γ1 ομαδα απο 7η (σημερινη προταση)': team_anchor(RAW)}
LO = {n0: league_off(n0) for n0 in N0S}
for n0 in N0S: V[f'Λ λιγκα n0={n0}'] = RAW + LO[n0]
for n0 in N0S: V[f'Λ+Γ1 n0={n0}'] = team_anchor(RAW + LO[n0])
def run(T):
    rows = []
    for i, r in enumerate(P.itertuples()):
        if r.md < 3 or r.mid not in TGA: continue
        s = r.xg_h - r.xg_a; d = tdist((T[i] + s) / 2, (T[i] - s) / 2)
        for bk in ('Crown', 'Bet365'):
            seq = SER.get((r.mid, bk))
            if not seq: continue
            q = price_at(seq, 'fair', r.prev, r.ko)
            if q is None: continue
            t0, L, oo, uu = q; best = None
            for over, o in ((True, oo), (False, uu)):
                if not (1.70 <= o <= 2.10): continue
                e, pnl = ou_eval(d, L, over, o, int(TGA[r.mid]))
                if e >= .10 and (best is None or e > best[0]): best = (e, pnl, 'OVER' if over else 'UNDER')
            if best: rows.append(dict(book=bk, season=r.season, league=r.league, md=r.md, side=best[2], pnl=best[1], hrs=(r.ko - t0) / 3600))
    return pd.DataFrame(rows)
SEAS = sorted(P.season.unique())
def fm(x):
    if len(x) < 5: return f'n{len(x):4d}            —           '
    ps = x.groupby('season').pnl.mean(); return f'n{len(x):4d} {100 * x.pnl.mean():+6.1f}% {x.pnl.sum():+6.1f}μ {int((ps > 0).sum())}/{len(ps)}'
def u2(x): return x.groupby('book').pnl.sum().mean() if len(x) else 0.0
ok = P.tg.notna().values & (P.md >= 6).values
okm = ok & P.T_mkt.notna().values
TG_ = P.tg.values
def llT(T, m):
    return np.array([np.log(max(tdist(T[i] / 2, T[i] / 2)[int(TG_[i])], 1e-9)) for i in np.where(m)[0]]).sum()
R = {}
print('ΑΓΚΥΡΑ ΕΠΙΠΕΔΟΥ ΛΙΓΚΑΣ — συνολα CORE7 2223-2526, τιμιος χρονος, edge ≥10%, 1.70-2.10 · Crown | Bet365: n, ROI, μοναδες, θετικες σεζον')
print(f'{NL}ΑΚΡΙΒΕΙΑ (αγωνιστικες 7+): μεροληψια (μοντελο − πραγματικα) · μεση αποσταση απο αγορα (κλεισιμο) · Δ log-πιθ. συνολου vs Γ1 ανα σεζον')
LL0 = {s: llT(V['Γ1 ομαδα απο 7η (σημερινη προταση)'], ok & (P.season == s).values) for s in SEAS}
for nm, T in V.items():
    for lab, m in (('7-14', ok & P.md.between(6, 13).values), ('15+', ok & (P.md >= 14).values)):
        mm = m & P.T_mkt.notna().values
        bias = (T[m] - TG_[m]).mean(); dist = np.abs(T[mm] - P.T_mkt.values[mm]).mean()
        if lab == '7-14': line = f'   {nm:38s} 7-14: μεροληψια {bias:+.2f} αποσταση αγορας {dist:.2f}'
        else: line += f' │ 15+: μεροληψια {bias:+.2f} αποσταση αγορας {dist:.2f}'
    dl = [llT(T, ok & (P.season == s).values) - LL0[s] for s in SEAS]
    print(line + ' │ Δlog-πιθ. ' + ' '.join(f'{v:+5.1f}' for v in dl))
# πρωιμη φαση: ποσο κλεινει το κενο
print(f'{NL}ΜΕΡΟΛΗΨΙΑ ΣΤΙΣ ΠΡΩΤΕΣ ΑΓΩΝΙΣΤΙΚΕΣ (μοντελο − αγορα κλεισιμο): αγων. 4-6 · 7-9')
for nm in ('Γ1 ομαδα απο 7η (σημερινη προταση)', 'Λ λιγκα n0=10', 'Λ λιγκα n0=30'):
    T = V[nm]; m1 = P.md.between(3, 5).values & P.T_mkt.notna().values; m2 = P.md.between(6, 8).values & P.T_mkt.notna().values
    print(f'   {nm:38s} 4-6: {(T[m1] - P.T_mkt.values[m1]).mean():+.2f} · 7-9: {(T[m2] - P.T_mkt.values[m2]).mean():+.2f}')
print(f'{NL}PICKS')
for nm, T in V.items():
    x = run(T); R[nm] = x
    print(f'{NL}{nm}')
    for wl, m in (('4-6 (ενημ.)', x.md.between(3, 5)), ('7-14', x.md.between(6, 13)), ('15+', x.md >= 14), ('ολα 7+', x.md >= 6)):
        y = x[m]
        print(f'   {wl:12s} Crown {fm(y[y.book == "Crown"])} | Bet365 {fm(y[y.book == "Bet365"])}')
    y = x[x.md >= 6]
    print(f'   7+ ανα πλευρα (Crown): ' + ' · '.join(f'{sd} {fm(y[(y.book == "Crown") & (y.side == sd)])}' for sd in ('OVER', 'UNDER')) +
          f' │ ≥120ω (Crown): {fm(y[(y.book == "Crown") & (y.hrs >= 120)])}')
    print(f'   7+ ανα σεζον (μοναδες, μεσος βιβλιων): ' + ' '.join(f'{s}: {u2(y[y.season == s]):+5.1f}' for s in SEAS))
print(f'{NL}LOSO: n0 απο τις αλλες 3 σεζον (μοναδες 7+, μεσος βιβλιων)')
for fam in ('Λ λιγκα', 'Λ+Γ1'):
    ch = []; outs = []
    for s in SEAS:
        best = max(N0S, key=lambda n0: u2(R[f'{fam} n0={n0}'][(R[f'{fam} n0={n0}'].md >= 6) & (R[f'{fam} n0={n0}'].season != s)]))
        ch.append(best); x = R[f'{fam} n0={best}']; outs.append(x[(x.md >= 6) & (x.season == s)])
    Z = pd.concat(outs)
    print(f'   {fam:8s} επιλογες ' + ', '.join(f'{s}→{c}' for s, c in zip(SEAS, ch)) + f' │ Crown {fm(Z[Z.book == "Crown"])} | Bet365 {fm(Z[Z.book == "Bet365"])}')
x = R['Γ1 ομαδα απο 7η (σημερινη προταση)']; x = x[x.md >= 6]
print(f'   Γ1 (αναφορα)                                     │ Crown {fm(x[x.book == "Crown"])} | Bet365 {fm(x[x.book == "Bet365"])}')
