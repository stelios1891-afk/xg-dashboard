"""
intl_absence_goals_test.py — ΑΠΟΥΣΙΕΣ ΕΠΙΘΕΤΙΚΩΝ/ΑΜΥΝΤΙΚΩΝ ΒΑΣΙΚΩΝ → ΣΥΝΟΛΟ ΓΚΟΛ (25/9/2026, ερωτημα Στελιου: Ουγγαρια−Ουκρανια χωρις Varga, Sallai, Dovbyk
— δεν θα επρεπε να πεφτουν τα γκολ; Σημερα το T δεν εχει ορο απουσιων: η αξια αλλαζει μονο τη διαφορα, και εκει οι απουσιες των 2 πλευρων αλληλοαναιρουνται).

ΟΡΙΣΜΟΙ (walk-forward): βασικος = ≥50% ενδεκαδες 730 ημ. πριν (≥4 ματς)· βαρος = ποσοστο βασικου· απουσια = εκτος αποστολης ματς.
  θεση απο intl_player_values 'pos' (θεση ΣΥΛΛΟΓΟΥ σημερα): ΕΠΙΘ = forward/Striker/Winger/Attacking Midfielder · ΑΜΥΝ = Back/defender/Keeper/Wing-Back · αλλοι = μεσοι.
  Aatt = Σ βαρων επιθετικων που λειπουν (και οι 2 ομαδες) · Adef = ιδιο για αμυντικους.
ΠΡΟ-ΔΗΛΩΣΗ (ΠΡΙΝ τρεξει, ΜΙΑ εκτελεση):
  Βαση = T_ctx του intl_xg_totals (LOSO, 1.107 ματς με closing O/U Crown). Εκδοχη: T + b1·Aatt + b2·Adef, b fit LOSO ανα σεζον (OLS στο υπολοιπο).
  ΚΡΙΤΗΡΙΟ: μικροτερο MAE συνολου γκολ ΚΑΙ καλυτερο σε ≥4/5 σεζον. Δευτερευον: ιδιο με συνολο xG (λιγοτερος θορυβος).
  ΑΝΑΦΟΡΑ: (α) η αγορα: (γραμμη O/U − T) ~ Aatt, Adef · (β) ROI ιστορικων OVER (72ω) με/χωρις επιθετικους εκτος.
"""
import sys, json, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P_(s=''):
    print(s, flush=True); out.append(str(s))

SQ = json.load(open('intl_squads.json', encoding='utf-8'))
PV = json.load(open('intl_player_values.json', encoding='utf-8'))
ATT = {'forward', 'Striker', 'Right Winger', 'Left Winger', 'Attacking Midfielder'}
DEF = {'Center Back', 'defender', 'Left Back', 'Right Back', 'Right Wing-Back', 'Left Wing-Back', 'Keeper', 'keeper'}
POS = {int(k): ('att' if v.get('pos') in ATT else 'def' if v.get('pos') in DEF else 'mid') for k, v in PV.items()}
E = pd.read_csv('intl_callup_test_events.csv', dtype={'mid': str, 'season': str}, parse_dates=['date']).sort_values('date').reset_index(drop=True)
games = {}
for r in E.itertuples():
    s = SQ.get(r.mid) or {}
    for k, tid in (('h', int(r.hid)), ('a', int(r.aid))):
        t = s.get(k) or {}
        if len(t.get('st') or []) >= 8 and len(t.get('p') or {}) >= 14:
            games.setdefault(tid, []).append((r.date, r.mid, set(int(x) for x in t['st']), set(int(x) for x in t['p'])))


def absences(tid, date, mid):
    g = games.get(tid, []); past = [x for x in g if x[0] < date and (date - x[0]).days <= 730]; cur = [x for x in g if x[1] == mid]
    if len(past) < 4 or not cur:
        return None
    cnt = {}
    for _, _, st, _ in past:
        for p in st:
            cnt[p] = cnt.get(p, 0) + 1
    res = {'att': 0.0, 'def': 0.0, 'mid': 0.0}
    for p, c in cnt.items():
        w = c / len(past)
        if w >= 0.5 and p not in cur[0][3]:
            res[POS.get(p, 'mid')] += w
    return res


rows = []
for r in E.itertuples():
    a, b = absences(int(r.hid), r.date, r.mid), absences(int(r.aid), r.date, r.mid)
    if a and b:
        rows.append(dict(mid=r.mid, Aatt=a['att'] + b['att'], Adef=a['def'] + b['def'], Amid=a['mid'] + b['mid']))
A = pd.DataFrame(rows)
X = pd.read_csv('intl_xg_totals.csv', dtype={'mid': str, 'season': str}).merge(A, on='mid')
M = pd.read_csv('intl_matches.csv', dtype={'mid': str})
X = X.merge(M[['mid', 'xg_h', 'xg_a', 'has_xg']], on='mid', how='left'); X['xgtot'] = np.where(X.has_xg, X.xg_h + X.xg_a, np.nan)
P_('ΑΠΟΥΣΙΕΣ ΒΑΣΙΚΩΝ ΑΝΑ ΘΕΣΗ → ΣΥΝΟΛΟ ΓΚΟΛ · βαση T_ctx (LOSO) · ματς με closing O/U')
P_(f'δειγμα {len(X)} ματς · επιθετικοι βασικοι εκτος (και οι 2 ομαδες): μεσος {X.Aatt.mean():.2f} · ≥1: {(X.Aatt >= 1).mean() * 100:.0f}% · ≥2: {(X.Aatt >= 2).mean() * 100:.0f}% · '
   f'αμυντικοι μεσος {X.Adef.mean():.2f}')
SEAS = sorted(X.season.unique())
for target, lab in (('tot', 'ΓΚΟΛ'), ('xgtot', 'xG')):
    D = X.dropna(subset=[target]).copy(); D['res'] = D[target] - D.T_ctx
    if target == 'xgtot':
        k = D[target].mean() / D.T_ctx.mean(); D['res'] = D[target] - k * D.T_ctx      # κλιμακα xG (χωρις πεναλτι) vs γκολ
    pred0 = D[target] - D.res; pred1 = pred0.copy(); per = []
    for s in SEAS:
        tr = D[D.season != s]; te = D.season == s
        Z = np.c_[tr.Aatt, tr.Adef]; bb = np.linalg.lstsq(np.c_[np.ones(len(Z)), Z], tr.res.values, rcond=None)[0]
        pred1[te] = pred0[te] + bb[0] + bb[1] * D.Aatt[te] + bb[2] * D.Adef[te]
        m0 = np.abs(D[target][te] - pred0[te]).mean(); m1 = np.abs(D[target][te] - pred1[te]).mean(); per.append((s, m0, m1))
    Z = np.c_[np.ones(len(D)), D.Aatt, D.Adef]; bb, *_ = np.linalg.lstsq(Z, D.res.values, rcond=None)
    e = D.res.values - Z @ bb; cov = np.linalg.inv(Z.T @ Z) * (e @ e) / (len(D) - 3); se = np.sqrt(np.diag(cov))
    mae0 = np.abs(D[target] - pred0).mean(); mae1 = np.abs(D[target] - pred1).mean(); better = sum(1 for _, a, b in per if b < a)
    P_(f'\n[{lab}] n={len(D)} · MAE βαση {mae0:.4f} → με απουσιες {mae1:.4f} (Δ {mae1 - mae0:+.4f}) · καλυτερο σε {better}/{len(per)} σεζον · '
       f'{"ΠΕΡΝΑ" if (mae1 < mae0 and better >= 4) else "—"}' + ('' if lab == 'ΓΚΟΛ' else ' (δευτερευον)'))
    P_(f'   ανα επιθετικο βασικο εκτος: {bb[1]:+.3f} {lab} (t {bb[1] / se[1]:+.1f}) · ανα αμυντικο: {bb[2]:+.3f} (t {bb[2] / se[2]:+.1f})')
    P_('   ανα σεζον MAE βαση→νεο: ' + ' · '.join(f'{s}: {a:.3f}→{b:.3f}' for s, a, b in per))
D = X.dropna(subset=['ou_line']).copy(); D['r'] = D.ou_line - D.T_ctx
Z = np.c_[np.ones(len(D)), D.Aatt, D.Adef]; bb, *_ = np.linalg.lstsq(Z, D.r.values, rcond=None); e = D.r.values - Z @ bb
se = np.sqrt(np.diag(np.linalg.inv(Z.T @ Z) * (e @ e) / (len(D) - 3)))
P_(f'\n(α) ΑΓΟΡΑ: η γραμμη O/U κινειται {bb[1]:+.3f} γκολ ανα επιθετικο εκτος (t {bb[1] / se[1]:+.1f}) · {bb[2]:+.3f} ανα αμυντικο (t {bb[2] / se[2]:+.1f})')
B = pd.read_csv('intl_window_test_proper_ahproper_bets.csv', dtype={'mid': str, 'season': str})
B = B[(B.win == '72ω') & (B.rule == 'OVER')].merge(A, on='mid')
B['ομαδα'] = np.where(B.Aatt >= 1, 'λειπει ≥1 επιθετικος βασικος', 'χωρις επιθετικες απουσιες')
P_('\n(β) ROI ιστορικων OVER (72ω, σωστος τυπος)')
for mdl in ('M1', 'M2', 'M3'):
    for bk in ('Crown', 'SBOBET'):
        s = B[(B.model == mdl) & (B.book == bk)]
        P_(f'  {mdl} {bk:6s}: ' + ' · '.join(f"{g}: n{len(x)} {x.pnl.mean() * 100:+.1f}%" for g, x in s.groupby('ομαδα')))
open('intl_absence_goals_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
