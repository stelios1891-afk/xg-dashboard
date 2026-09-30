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
        return f"⚠️ Αγορα κοντρα: η τιμη μας ανεβηκε ({d:+.1f} π. τις {DRIFT_H:.0f}ω πριν το alert). Ιστορικα τετοια χαντικαπ −1.4% (135 picks) vs +5.2% οταν η τιμη ειναι σταθερη — παρατηρηση."
    return f"ℹ️ Αγορα κοντρα ({d:+.1f} π. τις {DRIFT_H:.0f}ω πριν το alert) — στα συνολα ιστορικα δεν βλαπτει (+5.3%, 215 picks)· παιζεται νωρις."

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
        base = dict(lg='Euroleague', home=g['home'], away=g['away'], hcode=g['hcode'], acode=g['acode'], code=g['code'], round=g['round'],
                    when=when, el=True, model=proj.get('model', '')[:60])
        # ---- χαντικαπ ----
        if pin.get('line') is not None and pin.get('oh') and pin.get('oa'):
            L, oh, oa = float(pin['line']), float(pin['oh']), float(pin['oa'])
            m = float(g['margin'])
            pw, pp = cover(m, L, sm); pl = 1 - pw - pp
            for side, p_, pu, od, hc in ((1, pw, pp, oh, L), (-1, pl, pp, oa, -L)):
                e = p_ * od + pu - 1
                if e >= HC_MIN:
                    picks.append(dict(base, mkt='hcap', side=side, hcap=hc, odds=od, edge=round(e, 4),
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
    else:
        bet = p['bet']; why = f"μοντελο {p['model_total']:.1f} · αγορα {p['mkt_line']:g}"
        if p.get('old_agree') is not None:
            why += f" · {'✓ συμφωνει και το παλιο' if p['old_agree'] else '✗ μονο με την προετοιμασια'} ({p['total_base']:.1f} χωρις φιλικα)"
    ch = f" (ηταν {prev:.2f})" if prev else ''
    return f"🏀 Euroleague · αγων {p['round']} · {tm}\n{p['home']} - {p['away']}\n{bet} @{p['odds']:.2f}{ch} · edge {p['edge']*100:.0f}% · fair {p['proj_odds']:.2f}\n({why})" + (f"\n{p['mkt_note']}" if p.get('mkt_note') else '')

def main(notify_tg=True):
    picks = compute()
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes')
    state = _load(F('el_value_state.json'), {})
    new, changed, cur = [], [], set()
    for p in picks:
        k = key(p); cur.add(k); prev = state.get(k)
        if prev is None:
            new.append(p); state[k] = dict(odds=p['odds'], edge=p['edge'], when=p['when'], first_seen=now)
            hrs = (dt.datetime.fromisoformat(p['when']).replace(tzinfo=dt.timezone.utc) - dt.datetime.fromisoformat(now)).total_seconds() / 3600
            if p['mkt'] == 'hcap' and hrs < LATE_H: state[k]['paper'] = 'late2h'
        elif abs(p['odds'] - prev.get('odds', p['odds'])) >= ODDS_DELTA:
            changed.append((p, prev.get('odds'))); state[k].update(odds=p['odds'], edge=p['edge'])
    proj_ = _load(F('el_projections.json'), {}); sm_, st_ = float(proj_.get('sigma_margin', 11.5)), float(proj_.get('sigma_total', 16.7))
    for p in picks:
        st0 = state.get(key(p), {})
        if 'drift' not in st0:
            st0['drift'] = drift_before(p, st0.get('first_seen', now), sm_, st_)
            if key(p) in state: state[key(p)]['drift'] = st0['drift']
        p['drift'] = st0['drift']; p['mkt_note'] = drift_note(p)
        if st0.get('paper'):
            if 'late_kind' not in st0:
                d1 = drift_before(p, st0.get('first_seen', now), sm_, st_, hours=1.0)
                st0['late_kind'] = 'αγνωστη' if d1 is None else ('ξαφνικη' if d1 <= -SUDDEN_PTS else 'σταδιακη/ακινητη')
                if key(p) in state: state[key(p)]['late_kind'] = st0['late_kind']
            p['paper'], p['late_kind'] = st0['paper'], st0['late_kind']
            p['mkt_note'] = (f"📝 ΚΑΤΑΓΡΑΦΗ, δεν παιζεται: βγηκε στο τελευταιο 2ωρο (ιστορικα −9%, 1/5 σεζον)· κινηση αγορας: {p['late_kind']}"
                             + (f" ({p['drift']:+.1f} π. τις 3ω πριν)" if p.get('drift') is not None else ''))
    today = now[:10]
    state = {k: v for k, v in state.items() if k in cur or (v.get('when') or '9999')[:10] >= today}
    if new:
        with open(F('el_clv_bets.jsonl'), 'a', encoding='utf-8') as fh:
            for p in new:
                fh.write(json.dumps(dict(seen=now, **{k: p[k] for k in ('lg', 'code', 'round', 'home', 'away', 'mkt', 'side', 'hcap', 'odds', 'edge', 'when')},
                                         bet=p.get('bet'), model_line=p.get('model_line'), model_total=p.get('model_total'), mkt_line=p.get('mkt_line'),
                                         model=p.get('model'), drift=p.get('drift'), old_agree=p.get('old_agree'), total_base=p.get('total_base'),
                                         paper=p.get('paper'), late_kind=p.get('late_kind')), ensure_ascii=False) + '\n')
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
    print(f'[EL picks] {len(picks)} picks · {len(new)} νεα · {len(changed)} αλλαγες')
    for p in picks: print('  ' + line(p).replace('\n', ' | '))
    return picks

if __name__ == '__main__':
    main(notify_tg='--no-tg' not in sys.argv)
