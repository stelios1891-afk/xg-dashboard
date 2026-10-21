# -*- coding: utf-8 -*-
"""nba_roster_now.py — ΡΟΣΤΕΡ «1ου ΜΑΤΣ» ΜΕ ΤΑ ΤΩΡΙΝΑ «Out» (21/10/2026, Στελιος «κανε το 4»).
Για ομαδα που ΔΕΝ εχει παιξει ακομα ματς κανονικης περιοδου, οι απουσιες μετρανε μονο μεσα απο την αφετηρια (ρόστερ ESPN χωρις «Out»,
nba_live_roster). Μεχρι τωρα αυτο ξαναχτιζοταν μονο στο πρωινο nba_refresh → μια ειδηση «Out» (π.χ. Podziemski 20/10 23:50Z) εμπαινε
την επομενη μερα. Τωρα ο scanner (nba_odds_scan) ξαναϋπολογιζει σε ΚΑΘΕ τρεξιμο:
  Δ_τωρα = αξια(ρόστερ ESPN με αξια − ΤΩΡΙΝΑ «Out») − αξια περσινης ομαδας   (ιδια φορμουλα με nba_live_roster.team_value)
  διορθωση περιθωριου = Δ_τωρα − Δ που εχει ηδη η μηχανη (nba_state.json 'roster')   (β = 1.0, μοναδα ≈ ποντοι)
και αντιστροφα αν καποιος βγει απο τη λιστα (επιστροφη). Μετα το 1ο ματς: τιποτα (η αφετηρια = οσοι επαιξαν· απουσιες = nba_absence)."""
import os, json
from nba_absence import nk
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)


def _load(n, d):
    try:
        with open(F(n), encoding='utf-8') as fh: return json.load(fh)
    except Exception: return d


class RosterNow:
    def __init__(self, st, out_set, off=None):
        self.st = st or {}; self.out = out_set or set(); self.off = off          # off: nba_injrep_live.Official (μονο με διακοπτη «official»)
        RL = _load('nba_roster_live.json', {}); self.ALL, self.OLD, self.ROS = RL.get('all', {}), RL.get('old', {}), RL.get('roster', {})
        self.PL = _load('nba_roster_base.json', {}).get('players', {})

    def team_value(self, names):
        vals = [self.PL.get(nk(n), [-1.0, 15.0, 0.0])[:2] for n in names]
        if not vals: return None
        w = [x[1] for x in vals]; tot = sum(w)
        return sum(5 * wi / tot * x[0] for wi, x in zip(w, vals)) if tot else None

    def team(self, t, gdate=None):
        """(διορθωση για την ομαδα, νεα Out, επιστροφες) — 0 αν εχει ηδη παιξει ή λειπουν δεδομενα."""
        if int((self.st.get('gp') or {}).get(t, 0)) > 0 or t not in self.ALL or t not in self.OLD: return 0.0, [], []
        if self.off is not None and gdate and self.off.covers(t, gdate):
            # 21/10: επισημη αναφορα — Out (p=1) εξω· Doubtful/Questionable/Probable: p × (αξια χωρις αυτον − αξια)· ρολος απο περσινα λεπτα/ματς
            import nba_injrep_live as IL
            stt = self.off.status(t, gdate)
            P_ = {n: IL.prob(stt[IL.ckey(n)][0], self.PL.get(nk(n), [0, 15.0])[1]) for n in self.ALL[t] if IL.ckey(n) in stt}
            now = [n for n in self.ALL[t] if P_.get(n, 0.0) < 1.0]
            v0 = v = self.team_value(now)
            if v is None: return 0.0, [], []
            for n in now:
                p = P_.get(n, 0.0)
                if 0 < p < 1:
                    v2 = self.team_value([x for x in now if x != n])
                    if v2 is not None: v += p * (v2 - v0)
        else:
            now = [n for n in self.ALL[t] if (t, nk(n)) not in self.out]
            v = self.team_value(now)
            if v is None: return 0.0, [], []
        d_state = float((self.st.get('roster') or {}).get(t, 0.0))
        snap = set(self.ROS.get(t, [])); cur = set(now)
        return v - float(self.OLD[t]) - d_state, sorted(snap - cur), sorted(cur - snap)

    def adjust(self, h, a, gdate=None):
        dh, oh, rh = self.team(h, gdate); da, oa, ra = self.team(a, gdate)
        det = [[h, n, 'Out'] for n in oh] + [[h, n, 'επιστροφη'] for n in rh] + [[a, n, 'Out'] for n in oa] + [[a, n, 'επιστροφη'] for n in ra]
        return dh - da, det
