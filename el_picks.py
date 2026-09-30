# -*- coding: utf-8 -*-
"""el_picks.py — VALUE PICKS Ευρωλιγκας + Telegram (25/9/2026, αποφαση Στελιου).
Διαβαζει: el_projections.json (μοντελο v3: χαντικαπ v1+ειδικοι · συνολο v2+παρατασεις) + el_odds_latest.json (Pinnacle, scanner).
Κανονες (ιστορικο ROI 6 σεζον, Pinnacle closing): edge ≥ 8% σε χαντικαπ ΚΑΙ σε συνολο (over/under), μονο ματς που δεν αρχισαν.
  edge = P(μοντελο)·αποδοση + P(push) − 1 · διαφορα ~ N(margin, 11.5) · συνολο ~ N(total, 16.7) · ακεραιες γραμμες: διορθωση ±0.5.
Γραφει: el_value_latest.json (dashboard, tab Value Picks) · el_clv_bets.jsonl (ημερολογιο: καθε ΝΕΟ pick με την τιμη εισοδου)
Telegram: ΜΟΝΟ νεα picks ή αλλαγη αποδοσης ≥ 0.05 (state: el_value_state.json) — οπως το ποδοσφαιρο (notify.py).
Χρηση: python el_picks.py [--no-tg]"""
import os, sys, json, math, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
HC_MIN, TOT_MIN = 0.08, 0.08
ODDS_DELTA = 0.05
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
# 30/9/2026 (Στελιος): σημειωση «αγορα κοντρα» — ποσο κινηθηκε η αγορα τις 3 ωρες ΠΡΙΝ την πρωτη εμφανιση του pick.
# el_line_timing.py (Crown 2021-25): χαντικαπ με την τιμη μας να ΑΝΕΒΑΙΝΕΙ >=0.5 π. -> -1.4% (135, 2/5) vs σταθερη +5.2%·
# συνολα ιδια περιπτωση +5.3% (215) = κανενα προβλημα. ΠΑΡΑΤΗΡΗΣΗ (οχι προ-δηλωμενο τεστ) -> μονο σημειωση, το pick μενει.
DRIFT_H, DRIFT_MIN = 3.0, 0.5
# 1/10/2026 (Στελιος «περασε το»): ΧΑΝΤΙΚΑΠ που γεννιουνται στο ΤΕΛΕΥΤΑΙΟ 2ΩΡΟ = ΚΑΤΑΓΡΑΦΗ, ΟΧΙ ΠΑΙΧΝΙΔΙ (paper).
# el_alert_types.py (Crown καθε αλλαγη τιμης, E2021-25, live μοντελο): τελευταιο 2ωρο −9.0% (75, 1/5) · παλιο μοντελο −17.1% (1/5)·
# ολες οι αλλες ωρες θετικες (ανοιγμα +7.5% 5/5, ≥12ω +24.8%, 6-12ω +14.6%, 2-6ω +8.6%). Μεσα στο 2ωρο: ξαφνικο αλμα ≥1π/1ω +27.7% (16)
# vs σταδιακη κοντρα −22.6% (38) / ακινητη −12.3% (21) → λιγα για κανονα· καταγραφεται το ειδος για κριση με πραγματικα δεδομενα.
# Οχι Telegram, οχι «παιζεται» στο dashboard· γραφεται στο el_clv_bets.jsonl με paper='late2h'. Συνολα: ΚΑΜΙΑ αλλαγη (2ωρο +4.5%).
LATE_H, SUDDEN_PTS = 2.0, 1.0
# 1/10/2026 (Στελιος «ναι»): ΣΥΝΟΛΑ που γεννιουνται αφου η αγορα κινηθηκε ≥1.5 π. ΚΟΝΤΡΑ απο την πρωτη τιμη που ειδε ο scanner
# (αναμενομενο συνολο, με αποδοσεις) = ΚΑΤΑΓΡΑΦΗ (paper='move15'). el_alert_types_totals.py (Crown, 5 σεζον, live μοντελο):
# κοντρα 1.5-2 −2.9% (54) · 2-3 −25.1% (44, 1/5)· κανονας «χωρις» ολα +7.1 → +9.7% (5/5 σεζον βελτιωση· παλιο μοντελο 4/5)· ορια 1/1.5/2 ιδια.
MOVE_PTS = 1.5
from statistics import NormalDist as _ND
def _mu(row, mkt, sm, st):
    try:
        if mkt == 'hcap':
            L, o1, o2 = float(row['line']), float(row['oh']), float(row['oa'])
            p = (1 / o1) / (1 / o1 + 1 / o2); return -L + sm * _ND().inv_cdf(min(max(p, 1e-4), 1 - 1e-4))
        T, o1, o2 = float(row['tl']), float(row['to']), float(row['tu'])
        p = (1 / o1) / (1 / o1 + 1 / o2); return T + st * _ND().inv_cdf(min(max(p, 1e-4), 1 - 1e-4))
    except Exception:
        return None
_HIST = None
def drift_before(p, first_seen, sm, st, hours=DRIFT_H):
    """+ = η αγορα ηρθε ΠΡΟΣ την πλευρα μας, - = εφυγε (η τιμη μας ανεβηκε) τις DRIFT_H ωρες πριν την πρωτη εμφανιση."""
    global _HIST
    if _HIST is None:
        _HIST = {}
        try:
            for ln in open(F('el_odds_hist.jsonl'), encoding='utf-8'):
                try:
                    r = json.loads(ln); _HIST.setdefault(int(r['code']), []).append(r)
                except Exception:
                    pass
            for v in _HIST.values(): v.sort(key=lambda r: r['t'])
        except FileNotFoundError:
            pass
    key_ = 'line' if p['mkt'] == 'hcap' else 'tl'
    H = [r for r in _HIST.get(int(p['code']), []) if r.get(key_) is not None]
    if not H: return None
    t_alert = dt.datetime.fromisoformat(first_seen).astimezone(dt.timezone.utc)
    ts = lambda r: dt.datetime.fromisoformat(r['t']).replace(tzinfo=dt.timezone.utc)
    now_rows = [r for r in H if ts(r) <= t_alert + dt.timedelta(minutes=15)]
    prev_rows = [r for r in H if ts(r) <= t_alert - dt.timedelta(hours=hours)]
    if not now_rows: return None
    a, b = (prev_rows[-1] if prev_rows else H[0]), now_rows[-1]
    m0, m1 = _mu(a, p['mkt'], sm, st), _mu(b, p['mkt'], sm, st)
    if m0 is None or m1 is None: return None
    s_ = p['side'] if p['mkt'] == 'hcap' else (1 if str(p.get('bet', '')).startswith('Over') else -1)
    return round((m1 - m0) * s_, 1)
def drift_note(p):
    d = p.get('drift')
    if d is None or d > -DRIFT_MIN: return None
    if p['mkt'] == 'hcap':
        # 1/10/2026: αντικαθιστα την παλια «⚠️ −1.4%» (el_line_timing, δεν ξεχωριζε ωρα/ειδος). el_alert_types.py (live μοντελο):
        # πριν το τελευταιο 2ωρο η κοντρα ΔΕΝ βλαπτει — ≥6ω σταδιακη +12.9% (70) / ξαφνικη +36.5% (28)· 2-6ω σταδιακη −3.6% (47, 2/5) / ξαφνικη +44% (20).
        kind = p.get('kind1h') or 'σταδιακη'; h = p.get('hrs_birth')
        if h is not None and h < 6:
            hist = 'ξαφνικη +44% (20 picks)' if kind == 'ξαφνικη' else 'σταδιακη −3.6% (47 picks, 2/5 σεζον)'
            return f"ℹ️ Αγορα κοντρα ({d:+.1f} π. τις {DRIFT_H:.0f}ω πριν, {kind}) — ιστορικα 2-6ω πριν: {hist}."
        hist = 'ξαφνικη +36.5% (28 picks)' if kind == 'ξαφνικη' else 'σταδιακη +12.9% (70 picks)'
        return f"ℹ️ Αγορα κοντρα ({d:+.1f} π. τις {DRIFT_H:.0f}ω πριν, {kind}) — ιστορικα ≥6ω πριν δεν βλαπτει: {hist}."
    mo = p.get('move_open')      # 1/10: el_alert_types_totals — κοντρα απο το ανοιγμα <1.5 π. ιστορικα +9% (216 picks)· ≥1.5 → καταγραφη
    return (f"ℹ️ Αγορα κοντρα ({d:+.1f} π. τις {DRIFT_H:.0f}ω πριν" + (f" · {mo:+.1f} απο το ανοιγμα" if mo is not None else '')
            + ") — στα συνολα κοντρα κατω απο 1.5 π. απο το ανοιγμα ιστορικα δεν βλαπτει (+9%, 216 picks).")

def _load(p, d):
    try: return json.load(open(p, encoding='utf-8'))
    except Exception: return d
def _is_int(x): return abs(x - round(x)) < 1e-9
def cover(mu, L, sig):
    """P(νικη), P(push) για «mu + L > 0»."""
    if _is_int(L):
        pw = Phi((mu + L - 0.5) / sig); pl = Phi((-mu - L - 0.5) / sig); return pw, 1 - pw - pl
    return Phi((mu + L) / sig), 0.0

def compute():
    proj = _load(F('el_projections.json'), {}); odds = _load(F('el_odds_latest.json'), {}).get('odds', {})
    sm, st = float(proj.get('sigma_margin', 11.5)), float(proj.get('sigma_total', 16.7))
    games = {str(g['code']): g for g in proj.get('games', [])}
    now = dt.datetime.now(dt.timezone.utc)
    picks = []
    for code, o in odds.items():
        g = games.get(str(code)); pin = o.get('pin') or {}
        if not g or g.get('played'): continue
        ko = dt.datetime.fromisoformat(o['commence'].replace('Z', '+00:00'))
        if ko <= now: continue
        when = ko.strftime('%Y-%m-%dT%H:%M')
        base = dict(lg='Euroleague', home=g['home'], away=g['away'], hcode=g['hcode'], acode=g['acode'], code=g['code'], round=g['round'], coach_notes=g.get('coach_notes'),
                    when=when, el=True, model=proj.get('model', '')[:60])
        # ---- χαντικαπ ----
        if pin.get('line') is not None and pin.get('oh') and pin.get('oa'):
            L, oh, oa = float(pin['line']), float(pin['oh']), float(pin['oa'])
            m = float(g['margin'])
            pw, pp = cover(m, L, sm); pl = 1 - pw - pp
            for side, p_, pu, od, hc in ((1, pw, pp, oh, L), (-1, pl, pp, oa, -L)):
                e = p_ * od + pu - 1
                if e >= HC_MIN:
                    picks.append(dict(base, mkt='hcap', side=side, hcap=hc, odds=od, edge=round(e, 4), travel=g.get('travel'),
                                      proj_odds=round((p_ + (1 - p_ - pu)) / p_, 2) if p_ > 0 else None, model_line=round(-m, 1), mkt_line=L))
        # ---- συνολο ----
        if pin.get('tl') is not None and pin.get('to') and pin.get('tu'):
            T, ov, un = float(pin['tl']), float(pin['to']), float(pin['tu'])
            t = float(g['total'])
            po, pq = cover(t, -T, st); pu_ = 1 - po - pq
            for nm, p_, od in (('Over', po, ov), ('Under', pu_, un)):
                e = p_ * od + pq - 1
                if e >= TOT_MIN:
                    pk = dict(base, mkt='total', side=0, hcap=T, bet=f'{nm} {T:g}', odds=od, edge=round(e, 4),
                              proj_odds=round((p_ + (1 - p_ - pq)) / p_, 2) if p_ > 0 else None, model_total=round(t, 1), mkt_line=T)
                    # 1/10/2026: αγων 1-10 το συνολο εχει ταση ποντων προετοιμασιας· ενδειξη αν ΣΥΜΦΩΝΕΙ και το παλιο (χωρις προετοιμασια)
                    # — μονο καταγραφη για κριση με πραγματικα δεδομενα (el_preseason_totals_deep.py F/G), δεν αλλαζει τα picks
                    tb = g.get('total_base')
                    if tb is not None and abs(float(tb) - t) >= 0.05:
                        bo, bq = cover(float(tb), -T, st); bp = bo if nm == 'Over' else 1 - bo - bq
                        pk['old_agree'] = bool(bp * od + bq - 1 >= TOT_MIN); pk['total_base'] = round(float(tb), 1)
                    picks.append(pk)
    return picks

def key(p): return f"EL|{p['code']}|{p['mkt']}|{p.get('bet') or p['side']}|{p['hcap']:g}"
def line(p, prev=None):
    t = dt.datetime.fromisoformat(p['when']).replace(tzinfo=dt.timezone.utc)
    try:
        from zoneinfo import ZoneInfo; t = t.astimezone(ZoneInfo('Europe/Athens'))
    except Exception:
        t = t + dt.timedelta(hours=3)
    tm = f"{['Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ'][t.weekday()]} {t:%d/%m %H:%M}"
    if p['mkt'] == 'hcap':
        team = p['home'] if p['side'] == 1 else p['away']
        bet = f"{team} {'+' if p['hcap'] >= 0 else ''}{p['hcap']:g}"
        why = f"μοντελο {p['model_line']:+.1f} · αγορα {p['mkt_line']:+.1f}"
        if p.get('travel'): why += f" · {p['travel']['note']}"
    else:
        bet = p['bet']; why = f"μοντελο {p['model_total']:.1f} · αγορα {p['mkt_line']:g}"
        if p.get('old_agree') is not None:
            why += f" · {'✓ συμφωνει και το παλιο' if p['old_agree'] else '✗ μονο με την προετοιμασια'} ({p['total_base']:.1f} χωρις φιλικα)"
    ch = f" (ηταν {prev:.2f})" if prev else ''
    if p.get('coach_notes'): why += ' · ' + ' · '.join(p['coach_notes'])
    return f"🏀 Euroleague · αγων {p['round']} · {tm}\n{p['home']} - {p['away']}\n{bet} @{p['odds']:.2f}{ch} · edge {p['edge']*100:.0f}% · fair {p['proj_odds']:.2f}\n({why})" + (f"\n{p['mkt_note']}" if p.get('mkt_note') else '')

# 1/10/2026 (Στελιος): ELEGXOS KLEISIMATOS — στο τελευταιο μισαωρο πριν το τζαμπολ (scanner καθε 15'), για καθε pick που ΠΑΙΞΑΜΕ
# (πρωτη εγγραφη, οχι paper): ποσο κινηθηκε η αγορα απο την εισοδο μας (αναμενομενη διαφορα/συνολο, με αποδοσεις).
# el_alert_types (picks στο ανοιγμα, κινηση ως το κλεισιμο): κοντρα ≥1.5π συνολα −10.7% (39) / χαντικαπ −17.4% (38)·
# προς εμας ≥1.5π συνολα +31.4% (115) / χαντικαπ +28.4% (48). Μονο ΕΝΗΜΕΡΩΣΗ στο info bot· προς εμας → γραμμη middle.
CLOSE_MIN, CLOSE_PTS = 35, 1.5
def _rng(a, b):
    lo, hi = math.floor(min(a, b)) + 1, math.ceil(max(a, b)) - 1        # ακεραια αποτελεσματα ΑΝΑΜΕΣΑ στις δυο γραμμες
    return f'{lo}' if lo == hi else f'{lo}-{hi}'
def close_check(state, now, sm, st):
    msgs = []
    try:
        odds = _load(F('el_odds_latest.json'), {}).get('odds', {})
        bets = {}
        for ln in open(F('el_clv_bets.jsonl'), encoding='utf-8'):
            try: b = json.loads(ln)
            except Exception: continue
            if b.get('paper'): continue
            d = (b.get('bet') or '').split(' ')[0] if b['mkt'] == 'total' else b['side']
            k = f"CLOSE|{b['code']}|{b['mkt']}|{d}"
            if k not in bets or b['seen'] < bets[k]['seen']: bets[k] = b
    except FileNotFoundError:
        return msgs
    tnow = dt.datetime.fromisoformat(now)
    for k, b in bets.items():
        if k in state: continue
        ko = dt.datetime.fromisoformat(b['when']).replace(tzinfo=dt.timezone.utc)
        mins = (ko - tnow).total_seconds() / 60
        if not (0 < mins <= CLOSE_MIN): continue
        o = odds.get(str(b['code']), {}).get('pin') or {}
        p = dict(b, side=b['side'] if b['mkt'] == 'hcap' else (1 if str(b.get('bet', '')).startswith('Over') else -1))
        m0 = drift_before(dict(p, side=p['side']), b['seen'], sm, st, hours=0.0)   # μονο για να φορτωσει το ιστορικο
        H = [r for r in (_HIST or {}).get(int(b['code']), []) if r.get('line' if b['mkt'] == 'hcap' else 'tl') is not None]
        ts = lambda r: dt.datetime.fromisoformat(r['t']).replace(tzinfo=dt.timezone.utc)
        ent = [r for r in H if ts(r) <= dt.datetime.fromisoformat(b['seen']) + dt.timedelta(minutes=15)]
        if not ent or not o: continue
        mu0, mu1 = _mu(ent[-1], b['mkt'], sm, st), _mu(o, b['mkt'], sm, st)
        if mu0 is None or mu1 is None: continue
        mv = round((mu1 - mu0) * p['side'], 1)                     # + = η αγορα ηρθε ΠΡΟΣ εμας
        state[k] = dict(when=b['when'], mv=mv, checked=now)
        if abs(mv) < CLOSE_PTS: continue
        if b['mkt'] == 'hcap':
            team = b['home'] if b['side'] == 1 else b['away']; other = b['away'] if b['side'] == 1 else b['home']
            h1 = float(b['hcap']); h2 = float(o['line']) * (1 if b['side'] == 1 else -1)
            bet = f"{team} {'+' if h1 >= 0 else ''}{h1:g} @{b['odds']:.2f}"; now_l = f"{team} {'+' if h2 >= 0 else ''}{h2:g}"
            mid = (f"middle: {other} {'+' if -h2 >= 0 else ''}{-h2:g} → κερδιζουν ΚΑΙ τα δυο αν {team} νικησει με {_rng(-h1, -h2)}"
                   if mv > 0 and h2 < h1 else '')
            hist = ('χαντικαπ +28.4% (48 picks)' if mv > 0 else 'χαντικαπ −17.4% (38 picks)')
        else:
            T1 = float(b['hcap']); T2 = float(o['tl']); over = p['side'] == 1
            bet = f"{b['bet']} @{b['odds']:.2f}"; now_l = f"συνολο {T2:g}"
            mid = ((f"middle: {'Under' if over else 'Over'} {T2:g} → κερδιζουν ΚΑΙ τα δυο αν το συνολο βγει {_rng(T1, T2)}")
                   if mv > 0 and ((over and T2 > T1) or (not over and T2 < T1)) else '')
            hist = ('συνολα +31.4% (115 picks)' if mv > 0 else 'συνολα −10.7% (39 picks)')
        head = '✅ ΚΛΕΙΣΙΜΟ ΥΠΕΡ ΜΑΣ' if mv > 0 else '⚠️ ΚΛΕΙΣΙΜΟ ΚΟΝΤΡΑ'
        tail = f"\n{mid}" if mid else ("\n(κοντρα: καλυψη ΠΡΙΝ το ματς κλειδωνει τη ζημια + πληρωνει γκανιοτα ξανα)" if mv < 0 else '')
        msgs.append(f"🏀 {head} · {b['home']} - {b['away']} (σε {mins:.0f}')\nπαιξαμε {bet} · τωρα {now_l} · κινηση {mv:+.1f} π. "
                    f"{'προς εμας' if mv > 0 else 'κοντρα'}\nιστορικα: {hist}" + tail)
    return msgs

def main(notify_tg=True):
    picks = compute()
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes')
    state = _load(F('el_value_state.json'), {})
    new, changed, cur = [], [], set()
    proj_ = _load(F('el_projections.json'), {}); sm_, st_ = float(proj_.get('sigma_margin', 11.5)), float(proj_.get('sigma_total', 16.7))
    for p in picks:
        k = key(p); cur.add(k); prev = state.get(k)
        if prev is None:
            new.append(p); state[k] = dict(odds=p['odds'], edge=p['edge'], when=p['when'], first_seen=now)
            hrs = (dt.datetime.fromisoformat(p['when']).replace(tzinfo=dt.timezone.utc) - dt.datetime.fromisoformat(now)).total_seconds() / 3600
            if p['mkt'] == 'hcap' and hrs < LATE_H: state[k]['paper'] = 'late2h'
            if p['mkt'] == 'total':
                d_open = drift_before(p, now, sm_, st_, hours=1e4)       # απο την ΠΡΩΤΗ τιμη του ιστορικου ως τωρα (+ = προς εμας)
                state[k]['move_open'] = d_open
                if d_open is not None and d_open <= -MOVE_PTS: state[k]['paper'] = 'move15'
        elif abs(p['odds'] - prev.get('odds', p['odds'])) >= ODDS_DELTA:
            changed.append((p, prev.get('odds'))); state[k].update(odds=p['odds'], edge=p['edge'])
    for p in picks:
        st0 = state.get(key(p), {})
        if 'drift' not in st0:
            st0['drift'] = drift_before(p, st0.get('first_seen', now), sm_, st_)
            if key(p) in state: state[key(p)]['drift'] = st0['drift']
        if 'kind1h' not in st0:
            d1 = drift_before(p, st0.get('first_seen', now), sm_, st_, hours=1.0)
            st0['kind1h'] = None if d1 is None else ('ξαφνικη' if d1 <= -SUDDEN_PTS else 'σταδιακη')
            if key(p) in state: state[key(p)]['kind1h'] = st0['kind1h']
        p['kind1h'] = st0['kind1h']
        try:
            p['hrs_birth'] = (dt.datetime.fromisoformat(p['when']).replace(tzinfo=dt.timezone.utc)
                              - dt.datetime.fromisoformat(st0.get('first_seen', now))).total_seconds() / 3600
        except Exception:
            p['hrs_birth'] = None
        p['move_open'] = st0.get('move_open')
        p['drift'] = st0['drift']; p['mkt_note'] = drift_note(p)
        if st0.get('paper'):
            if 'late_kind' not in st0:
                d1 = drift_before(p, st0.get('first_seen', now), sm_, st_, hours=1.0)
                st0['late_kind'] = 'αγνωστη' if d1 is None else ('ξαφνικη' if d1 <= -SUDDEN_PTS else 'σταδιακη/ακινητη')
                if key(p) in state: state[key(p)]['late_kind'] = st0['late_kind']
            p['paper'], p['late_kind'] = st0['paper'], st0['late_kind']
            if st0['paper'] == 'move15':
                p['mkt_note'] = (f"📝 ΚΑΤΑΓΡΑΦΗ, δεν παιζεται: βγηκε αφου η αγορα κινηθηκε {st0.get('move_open') or 0:+.1f} π. κοντρα απο το ανοιγμα "
                                 f"(ιστορικα κοντρα ≥1.5 π. −10%, 1/5 σεζον)· κινηση: {p['late_kind']}")
            else:
                p['mkt_note'] = (f"📝 ΚΑΤΑΓΡΑΦΗ, δεν παιζεται: βγηκε στο τελευταιο 2ωρο (ιστορικα −9%, 1/5 σεζον)· κινηση αγορας: {p['late_kind']}"
                                 + (f" ({p['drift']:+.1f} π. τις 3ω πριν)" if p.get('drift') is not None else ''))
    today = now[:10]
    close_msgs = close_check(state, now, sm_, st_)
    state = {k: v for k, v in state.items() if k in cur or (v.get('when') or '9999')[:10] >= today}
    if new:
        with open(F('el_clv_bets.jsonl'), 'a', encoding='utf-8') as fh:
            for p in new:
                fh.write(json.dumps(dict(seen=now, **{k: p[k] for k in ('lg', 'code', 'round', 'home', 'away', 'mkt', 'side', 'hcap', 'odds', 'edge', 'when')},
                                         bet=p.get('bet'), model_line=p.get('model_line'), model_total=p.get('model_total'), mkt_line=p.get('mkt_line'),
                                         model=p.get('model'), drift=p.get('drift'), old_agree=p.get('old_agree'), total_base=p.get('total_base'),
                                         paper=p.get('paper'), late_kind=p.get('late_kind'), move_open=state.get(key(p), {}).get('move_open')), ensure_ascii=False) + '\n')
    json.dump(state, open(F('el_value_state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(dict(scanned_at=now, hc_min=HC_MIN, tot_min=TOT_MIN, n_new=len(new), n_changed=len(changed), picks=picks),
              open(F('el_value_latest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    new_tg = [p for p in new if not p.get('paper')]; changed = [(p, pr) for p, pr in changed if not p.get('paper')]
    if notify_tg and (new_tg or changed):
        msg = []
        if new_tg: msg += [f'🏀 {len(new_tg)} ΝΕΑ value picks Ευρωλιγκας', ''] + [line(p) + '\n' for p in sorted(new_tg, key=lambda x: x['when'])]
        if changed: msg += [f'🔄 {len(changed)} ΑΛΛΑΞΑΝ odds'] + [line(p, pr) for p, pr in changed]
        try:
            import notify; notify.send('\n'.join(msg))
        except Exception as e:
            print('Telegram σφαλμα:', e)
    if close_msgs:
        print('\n'.join(close_msgs))
        if notify_tg:
            try:
                import notify; notify.send('\n\n'.join(close_msgs), channel='info')
            except Exception as e:
                print('Telegram σφαλμα (κλεισιμο):', e)
    print(f'[EL picks] {len(picks)} picks · {len(new)} νεα · {len(changed)} αλλαγες · ελεγχοι κλεισιματος {len(close_msgs)}')
    for p in picks: print('  ' + line(p).replace('\n', ' | '))
    return picks

if __name__ == '__main__':
    main(notify_tg='--no-tg' not in sys.argv)
