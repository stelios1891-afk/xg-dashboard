# -*- coding: utf-8 -*-
"""el_domestic_live.py — ΦΕΤΙΝΑ ΕΓΧΩΡΙΑ στο live χαντικαπ Ευρωλιγκας (30/9/2026, αποφαση Στελιου «περασε το»).
ΙΔΙΟ με το τεστ el_domestic_rating_test.py (LOSO: κ 0.5 + ταβανι 20 σε 5/5 σεζον· αγων 11+ και ολη η σεζον καλυτερα 5/5,
ROI χαντικαπ ≥8% +7.6 → +10.1%):
  ανα εγχωρια λιγκα walk-forward ridge διαφορας: διαφ = R_γηπ − R_φιλ + εδρα (ελευθερη ανα λιγκα), ταβανι ±20,
  αφετηρια R0 = 0.7 × περσινο τελος (βαρος 8 ματς) — αλυσιδα απο 2017-18.
  Δ(ομαδα, μερα) = R(με τα εγχωρια ματς ΠΡΙΝ) − R0 = ποσο καλυτερη/χειροτερη δειχνει ΦΕΤΟΣ στο πρωταθλημα της.
  Η αφετηρια του χαντικαπ μετακινειται κατα κ·Δ·100/72 (μισο επιθεση, μισο αμυνα) — σβηνει μονο του οσο μαζευονται ματς EL.
Πηγη: bk_domestic.json (Nowgoal· ΜΟΝΟ κανονικη περιοδος, οπως στο τεστ) — ανανεωνεται καθε μερα (nowgoal_bk_domestic_fill.py --current)."""
import json, re, math, unicodedata, datetime as dt
import numpy as np

KAPPA, CAP, CARRY, LAM = 0.5, 20.0, 0.7, 8.0
_STOP = {'basketball', 'basket', 'club', 'the', 'sport', 'bc', 'kk', 'fc', 'bk', 'sad', 'baloncesto',
         'istanbul', 'athens', 'belgrade', 'aviv', 'tel', 'kaunas', 'piraeus'}

def _tok(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = s.replace('milano', 'milan').replace('olympiakos', 'olympiacos').replace('olimpia', 'olympia').replace('munchen', 'munich')
    return set(w for w in re.findall(r'[a-z]{3,}', s) if w not in _STOP)

def _fit(hi, ai, y, n, R0):
    m = len(y); A = np.zeros((m + n, n + 1)); b = np.zeros(m + n)
    r = np.arange(m); A[r, hi] = 1; A[r, ai] = -1; A[r, n] = 1; b[:m] = y
    s8 = math.sqrt(LAM); A[m + np.arange(n), np.arange(n)] = s8; b[m:] = s8 * R0
    return np.linalg.lstsq(A, b, rcond=None)[0][:n]

def build_shifts(el_teams, d0, season=None, path='bk_domestic.json'):
    if season is None:
        from el_season import NG as season          # 1/10: τρεχουσα σεζον αυτοματα (ηταν '26-27')
    """el_teams: {κωδικος EL: ονομα} · d0: ημερομηνια-αφετηρια των dnum του el_refresh.
    Επιστρεφει (shift(κωδικος, cut) → ποντοι/100 για την αφετηρια, πινακας αντιστοιχισης, Δ σημερα ανα ομαδα)."""
    DOM = json.load(open(path, encoding='utf-8'))
    d0 = dt.date.fromisoformat(str(d0)[:10])
    series, names = {}, {}
    for L in sorted({k.split('_')[0] for k in DOM}):
        keys = sorted([k for k in DOM if k.startswith(L + '_')], key=lambda k: k.split('_')[1])
        prev_end = {}
        for k in keys:
            G = [g for g in DOM[k]['games'] if (g[-1] if len(g) > 6 else 1) == 1
                 and str(g[4]).strip() not in ('', '-1', 'None') and str(g[5]).strip() not in ('', '-1', 'None')]
            names.update({(L, int(t)): nm for t, nm in DOM[k]['teams'].items()} if k.endswith(season) else {})
            if not G:
                prev_end = {} if not k.endswith(season) else prev_end
                if not k.endswith(season): continue
            gd = np.array([(dt.date.fromisoformat(g[1][:10]) - d0).days for g in G]) if G else np.array([], int)
            hid = [int(g[2]) for g in G]; aid = [int(g[3]) for g in G]
            y = np.clip(np.array([float(g[4]) - float(g[5]) for g in G]), -CAP, CAP) if G else np.array([])
            teams = sorted(set(hid) | set(aid) | ({int(t) for t in DOM[k]['teams']} if k.endswith(season) else set()))
            ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
            hi = np.array([ix[t] for t in hid], int); ai = np.array([ix[t] for t in aid], int)
            R0 = np.array([CARRY * prev_end.get(t, 0.0) for t in teams])
            if k.endswith(season):
                days = sorted(set(gd.tolist()))
                for d in days + [max(days) + 1 if days else 0]:
                    msk = gd < d
                    Rd = _fit(hi[msk], ai[msk], y[msk], n, R0) if msk.any() else R0
                    for t, i in ix.items(): series.setdefault((L, t), []).append((d, float(Rd[i] - R0[i])))
                break
            Rend = _fit(hi, ai, y, n, R0) if len(G) else R0
            prev_end = {t: float(Rend[i]) for t, i in ix.items()}
    # αντιστοιχιση ομαδων EL → εγχωριας ομαδας (τρεχουσα σεζον)
    MAP = {}
    for code, nm in el_teams.items():
        te = _tok(nm); best = (0, None)
        for (L, t), tn in names.items():
            tt = _tok(tn)
            if not tt or not te: continue
            sc = len(te & tt) / min(len(te), len(tt)) + 0.01 * len(te & tt)
            if sc > best[0]: best = (sc, (L, t))
        if best[0] >= 0.5: MAP[code] = best[1]
    def delta(code, cut):
        """Δ σε ποντους/ματς με τα εγχωρια ματς εως cut−2 (ιδια υστερηση με το τεστ)."""
        k = MAP.get(code); v = 0.0
        for d, x in series.get(k, []):
            if d <= cut - 1: v = x
            else: break
        return v
    shift = lambda code, cut: KAPPA * delta(code, cut) * 100 / 72
    info = {c: (MAP[c][0], names.get(MAP[c])) for c in MAP}
    return shift, info, delta
