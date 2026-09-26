# -*- coding: utf-8 -*-
"""ledger_view.py — Pick History / CLV tab: καθε pick του scanner με τιμη εισοδου,
κλεισιμο, CLV, τελικο σκορ, τελικα xG και «xG-value» (ποσο καλο ηταν το bet με βαση
το πως πραγματικα παιχτηκε το ματς, οχι μονο το σκορ)."""
import os, json, datetime
import html as _h

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TLOGO = 'https://images.fotmob.com/image_resources/logo/teamlogo/{}.png'
UTC = datetime.timezone.utc


def _jsonl(path):
    out = []
    if os.path.exists(path):
        for line in open(path, encoding='utf-8'):
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def _xg_index(current_season):
    """(hid, aid, date) -> (xg_h, xg_a) απο το teamgame_inputs.csv (μοντελο-xG ανα ματς)."""
    import pandas as pd
    idx = {}
    try:
        TG = pd.read_csv(os.path.join(ROOT, 'teamgame_inputs.csv'))
    except FileNotFoundError:
        return idx
    TG = TG[(TG.season.astype(str) == str(current_season)) & (TG.is_home == 1)]
    TGa = pd.read_csv(os.path.join(ROOT, 'teamgame_inputs.csv'))
    TGa = TGa[(TGa.season.astype(str) == str(current_season)) & (TGa.is_home == 0)]
    axg = dict(zip(TGa.mid.astype(str), TGa.xg_model))
    for r in TG.itertuples():
        xa = axg.get(str(r.mid))
        if xa is None:
            continue
        idx[(int(r.team), int(r.opp), str(r.date)[:10])] = (float(r.xg_model), float(xa))
    return idx


def prepare(current_season):
    """Ολα τα picks (settled + pending) εμπλουτισμενα με τελικα xG & xG-fair odds."""
    import picks as engine
    import clv_ledger
    settled = [b for b in _jsonl(os.path.join(ROOT, 'clv_ledger.jsonl')) if clv_ledger.counts(b)]   # 26/9: μονο εισοδοι ≤72ω
    done = {clv_ledger._bet_key(b) for b in settled}
    pending = [b for b in _jsonl(os.path.join(ROOT, 'clv_bets.jsonl'))
               if clv_ledger.counts(b) and clv_ledger._bet_key(b) not in done]
    xgi = _xg_index(current_season)
    for r in settled:
        ko = str(r.get('ko') or '')[:10]
        xg = None
        for off in (0, 1, -1):
            if ko:
                d = (datetime.date.fromisoformat(ko) + datetime.timedelta(days=off)).isoformat() \
                    if off else ko
                xg = xgi.get((r.get('hid'), r.get('aid'), d))
                if xg:
                    break
        r['xg_h'], r['xg_a'] = (round(xg[0], 2), round(xg[1], 2)) if xg else (None, None)
        r['xg_fair'] = r['xg_value'] = None
        if xg:
            try:
                dist = engine.gd_dist(max(xg[0], 0.05), max(xg[1], 0.05))
                pw, pp = engine.p_cover(dist, r['side'], r['hcap'])
                if pw > 0:
                    fair = (1 - pp) / pw
                    r['xg_fair'] = round(fair, 2)
                    r['xg_value'] = round(r['odds'] / fair - 1, 4)
            except Exception:
                pass
    settled, pending = _first_alert(settled), _first_alert(pending)
    for fn in (_intl_rows, _euro_rows):
        try:
            s_i, p_i = fn()
            settled += s_i; pending += p_i
        except Exception:
            pass
    settled.sort(key=lambda r: str(r.get('ko') or ''), reverse=True)
    pending.sort(key=lambda r: str(r.get('ko') or ''))
    return settled, pending


def _first_alert(rows):
    """26/9/2026 (Στελιος): ΕΝΑ pick ανα ματς & πλευρα. Ο scanner γραφει νεα εγγραφη καθε φορα που αλλαζει η γραμμη
    (π.χ. Union +3 → +3.25 → +3.5 → +3.75 = 4 εγγραφες), ενω στην πραξη παιζεται μια φορα — στο ΠΡΩΤΟ alert.
    Κραταμε το πρωτο (τιμη/γραμμη τη στιγμη που ηρθε το alert)· οι μεταγενεστερες γραμμες φαινονται ως σημειωση (later).
    Το αρχειο (clv_ledger/clv_bets) μενει ακεραιο."""
    g = {}
    for r in rows:
        g.setdefault((r.get('lg'), r.get('home'), r.get('away'), str(r.get('ko'))[:16], r.get('side')), []).append(r)
    out = []
    for v in g.values():
        v.sort(key=lambda r: str(r.get('seen') or ''))
        r = dict(v[0]); r['later'] = [(x['hcap'], x['odds']) for x in v[1:]]
        out.append(r)
    return out


def _intl_xg():
    """(hid, aid, ημερα) -> (xG γηπ., xG φιλοξ.) απο το intl_matches.csv (FotMob)."""
    import csv
    idx = {}
    try:
        for m in csv.DictReader(open(os.path.join(ROOT, 'intl_matches.csv'), encoding='utf-8')):
            if m.get('has_xg') == 'True' and m.get('xg_h') and m.get('xg_a'):
                idx[(int(m['hid']), int(m['aid']), m['date'][:10])] = (float(m['xg_h']), float(m['xg_a']))
    except Exception:
        pass
    return idx


def _intl_xg_value(r, xg):
    """xG fair / xG value ενος εθνικου pick απο τα ΤΕΛΙΚΑ xG (ιδια λογικη με τα εγχωρια· over: Poisson με συνολο xG)."""
    import picks as engine, intl_pricing as ip
    r['xg_h'], r['xg_a'] = round(xg[0], 2), round(xg[1], 2)
    if r['mkt'] == 'OVER':
        fair = ip.over_fair(max(xg[0] + xg[1], 0.1), r['hcap'])
    else:
        dist = engine.gd_dist(max(xg[0], 0.05), max(xg[1], 0.05))
        pw, pp = engine.p_cover(dist, r['side'], r['hcap'])
        fair = (1 - pp) / pw if pw > 0 else None
    if fair:
        r['xg_fair'] = round(fair, 2); r['xg_value'] = round(r['odds'] / fair - 1, 4)


# ---------- ΕΘΝΙΚΕΣ (26/9/2026, Στελιος): τα picks ΣΥΝΑΙΝΕΣΗΣ στο ιδιο ιστορικο ----------
# Τιμη = πρωτη εμφανιση (intl_picks_ledger.jsonl, Odds API) · κλεισιμο = τελευταια καταγραφη πριν τη σεντρα (intl_closing.jsonl).
# Ιδια γραμμη → CLV = τιμη/κλεισιμο − 1 (οπως τα εγχωρια). Αλλη γραμμη → ≈εκτιμηση: το κλεισιμο μεταφρασμενο στη γραμμη μας
# (AH: υπεροχη που δικαιολογει το κλεισιμο με συνολο απο το κλεισιμο O/U· over: συνολο T απο το κλεισιμο O/U), με την ιδια γκανιοτα.
def _ou_T(line, over, under):
    """συνολο γκολ T (Poisson) που δικαιολογει το κλεισιμο O/U (χωρις γκανιοτα)."""
    import intl_pricing as ip
    pi = (1 / over) / (1 / over + 1 / under)
    lo, hi = 0.3, 7.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if 1 / ip.over_fair(mid, line) < pi:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _intl_close(r, c):
    """συμπληρωνει close_line / close_odds / clv_pct ή clv_est_pct σε ενα εθνικο pick."""
    import intl_pricing as ip
    r['close_odds'] = r['clv'] = None
    if not c:
        return
    if r['mkt'] == 'OVER':
        if not (c.get('ou_line') is not None and c.get('over') and c.get('under')):
            return
        r['close_line'] = float(c['ou_line']); r['close_odds'] = float(c['over'])
        if abs(r['close_line'] - r['hcap']) < 0.01:
            r['clv'] = round(r['odds'] - r['close_odds'], 3); r['clv_pct'] = round(r['odds'] / r['close_odds'] - 1, 4)
        else:
            T = _ou_T(r['close_line'], c['over'], c['under'])
            eq = r['close_odds'] * ip.over_fair(T, r['hcap']) / ip.over_fair(T, r['close_line'])
            r['close_eq'] = round(eq, 3); r['clv_est_pct'] = round(r['odds'] / eq - 1, 4)
        return
    if not (c.get('line') is not None and c.get('oh') and c.get('oa')):
        return
    cl = float(c['line'])
    r['close_line'] = cl if r['side'] == 1 else -cl
    co, co_opp = (float(c['oh']), float(c['oa'])) if r['side'] == 1 else (float(c['oa']), float(c['oh']))
    r['close_odds'] = co
    if abs(r['close_line'] - r['hcap']) < 0.01:
        r['clv'] = round(r['odds'] - co, 3); r['clv_pct'] = round(r['odds'] / co - 1, 4)
        return
    import clv_ledger
    T = _ou_T(float(c['ou_line']), c['over'], c['under']) if (c.get('ou_line') is not None and c.get('over') and c.get('under')) else 2.5
    eq = clv_ledger._equiv_close_odds(T / 2, T / 2, r['side'], r['hcap'], r['close_line'], co, co_opp)
    if eq:
        r['close_eq'] = round(eq, 3); r['clv_est_pct'] = round(r['odds'] / eq - 1, 4)


# ---------- ΕΥΡΩΠΑΪΚΑ (26/9/2026, Στελιος): euro_picks_ledger.jsonl — ιδιος κανονας εισοδου ≤72ω, κλεισιμο/σκορ/xG στο ιδιο το αρχειο ----------
EURO_LG = {'ChampionsLeague': 'UCL', 'EuropaLeague': 'UEL', 'ConferenceLeague': 'UECL'}


def _euro_rows():
    settled, pending = [], []
    for p in _jsonl(os.path.join(ROOT, 'euro_picks_ledger.jsonl')):
        ou = p.get('mkt') == 'OVER'
        r = dict(lg=EURO_LG.get(p.get('comp'), p.get('comp')), home=p['home'], away=p['away'], hid=p.get('hid'), aid=p.get('aid'),
                 ko=p['ko'], euro=True, mkt=p.get('mkt'), side=(0 if ou else (1 if p.get('side') == 1 else -1)), hcap=float(p['line']),
                 odds=float(p['odds']), edge=p.get('edge'), seen=p.get('seen'), no_play=bool(p.get('no_play')),
                 bet_label=(f"Over {float(p['line']):g}" if ou else None),
                 score=(p.get('score') or '').replace('-', ' - ') or None, pnl=p.get('pnl'),
                 xg_h=None, xg_a=None, xg_fair=None, xg_value=None)
        if p.get('pnl') is None:
            pending.append(r); continue
        c = p.get('close') or {}
        try:
            _intl_close(r, dict(line=c.get('line'), oh=c.get('oh'), oa=c.get('oa'), ou_line=c.get('tl'), over=c.get('to'), under=c.get('tu')))
        except Exception:
            r['close_odds'] = None; r['clv'] = None
        if p.get('xg_h') is not None and p.get('xg_a') is not None:
            try:
                _intl_xg_value(r, (p['xg_h'], p['xg_a']))
            except Exception:
                pass
        settled.append(r)
    return settled, pending


def _intl_rows():
    rows = [r for r in _jsonl(os.path.join(ROOT, 'intl_picks_ledger.jsonl')) if r.get('stream') == 'ΣΥΝΑΙΝΕΣΗ' and not r.get('removed')]   # removed: βγηκε απο τον Στελιο (26/9, over παλιου T)
    closing = {}
    for c in _jsonl(os.path.join(ROOT, 'intl_closing.jsonl')):
        closing[(int(c['hid']), int(c['aid']), str(c['ko'])[:10])] = c
    xgi = _intl_xg()
    settled, pending = [], []
    for p in rows:
        ko = str(p.get('ko') or '').replace(' ', 'T')
        ou = p.get('mkt') == 'OVER'
        r = dict(lg=p.get('comp'), home=p['home'], away=p['away'], hid=p.get('hid'), aid=p.get('aid'), ko=ko, intl=True,
                 mkt=p.get('mkt'), side=(0 if ou else (1 if p.get('side') == 1 else -1)), hcap=float(p['line']),
                 odds=float(p['odds']), edge=p.get('edge'), book=p.get('book'), seen=p.get('first_seen'),
                 bet_label=(f"Over {float(p['line']):g}" if ou else None), score=(p.get('result') or '').replace('-', ' - ') or None,
                 pnl=p.get('pnl'), xg_h=None, xg_a=None, xg_fair=None, xg_value=None)
        if p.get('pnl') is None:
            pending.append(r); continue
        try:
            _intl_close(r, closing.get((int(p['hid']), int(p['aid']), ko[:10])))
        except Exception:
            r['close_odds'] = None; r['clv'] = None
        xg = xgi.get((int(p['hid']), int(p['aid']), ko[:10]))
        if xg:
            try:
                _intl_xg_value(r, xg)
            except Exception:
                pass
        settled.append(r)
    return settled, pending


def summary(settled):
    pnl = [r['pnl'] for r in settled if r.get('pnl') is not None]
    # CLV: ακριβες οπου η γραμμη εμεινε ιδια, αλλιως η ≈εκτιμηση (μεταφραση στη γραμμη μας)
    clv = [r['clv_pct'] if r.get('clv_pct') is not None else r.get('clv_est_pct')
           for r in settled]
    clv = [v for v in clv if v is not None]
    xv = [r['xg_value'] for r in settled if r.get('xg_value') is not None]
    beat = sum(1 for r in settled
               if ((r.get('clv_pct') if r.get('clv_pct') is not None else r.get('clv_est_pct')) or 0) > 0)
    return dict(n=len(settled), units=sum(pnl), roi=(sum(pnl) / len(pnl) if pnl else 0),
                clv=(sum(clv) / len(clv) if clv else None), nclv=len(clv), beat=beat,
                xgv=(sum(xv) / len(xv) if xv else None), nxg=len(xv))


CSS = """
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#0a0f1e;font-family:'DM Sans','Segoe UI',sans-serif;color:#e8edf8;padding:2px;}
table{width:100%;border-collapse:collapse;font-size:12px;}
th{font-size:9.5px;color:#6b7fa3;text-transform:uppercase;letter-spacing:.7px;text-align:center;
   padding:7px 6px;border-bottom:1px solid #1e2d47;position:sticky;top:0;background:#0a0f1e;}
td{padding:8px 6px;border-bottom:1px solid #121b30;text-align:center;white-space:nowrap;
   font-family:'JetBrains Mono',monospace;font-size:11.5px;color:#c7d3ea;}
td.l{text-align:left;font-family:'DM Sans',sans-serif;font-size:12.5px;}
td img{width:17px;height:17px;object-fit:contain;vertical-align:-4px;margin-right:6px;}
.pick{font-weight:700;color:#e8edf8;}
.dim{color:#5a6b8c;font-size:10px;}
.pos{color:#34d17a;font-weight:700;}
.neg{color:#e05563;font-weight:700;}
.mut{color:#6b7fa3;}
.win{background:#10251b;color:#34d17a;border:1px solid #1e4a33;border-radius:6px;padding:2px 8px;font-weight:700;}
.loss{background:#2a1418;color:#e05563;border:1px solid #4a1e26;border-radius:6px;padding:2px 8px;font-weight:700;}
.push{background:#1a2233;color:#8fa3c8;border:1px solid #26324e;border-radius:6px;padding:2px 8px;}
.half{opacity:.85;}
.pend td{opacity:.55;}
</style>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
"""


def _res_chip(pnl, odds):
    if pnl is None:
        return '<span class="mut">—</span>'
    if pnl == 0:
        return '<span class="push">PUSH</span>'
    if pnl > 0:
        return f'<span class="win{" half" if pnl < odds - 1.01 else ""}">WIN {pnl:+.2f}</span>'
    return f'<span class="loss{" half" if pnl > -0.99 else ""}">LOSS {pnl:+.2f}</span>'


def _pct(v, flip=False):
    if v is None:
        return '<span class="mut">—</span>'
    cls = 'pos' if (v > 0) != flip else ('neg' if v != 0 else 'mut')
    return f'<span class="{cls}">{v * 100:+.1f}%</span>'


def _pick_cell(r):
    if r.get('bet_label'):
        return f'⚽ {_h.escape(r["bet_label"])}'
    team = r['home'] if r['side'] == 1 else r['away']
    tid = r.get('hid') if r['side'] == 1 else r.get('aid')
    out = f'<img src="{TLOGO.format(tid)}">{_h.escape(team)} {"+" if r["hcap"] >= 0 else ""}{r["hcap"]:g}'
    if r.get('later'):
        out += ('<div class="dim">μετα: ' + ' → '.join(f'{"+" if h >= 0 else ""}{h:g} @{o:.2f}' for h, o in r['later']) + '</div>')
    return out


def _when(r):
    """ποτε μπηκε το pick (ωρες πριν τη σεντρα) + σημα «καταγραφη» για τα paper (αγωνιστικη <15, δεν παιζονται)."""
    try:
        ko = datetime.datetime.fromisoformat(str(r['ko'])[:16]).replace(tzinfo=UTC)
        se = datetime.datetime.fromisoformat(str(r['seen']).replace(' ', 'T')[:16]).replace(tzinfo=UTC)
        hb = (ko - se).total_seconds() / 3600
        t = f' · alert {hb / 24:.1f} μερ. πριν' if hb >= 48 else f' · alert {hb:.0f}ω πριν'
    except Exception:
        t = ''
    if r.get('no_play'):
        return t + ' · 👁 σκια (UEL, δεν παιζεται)'
    return t + (' · 📝 καταγραφη (αγων. &lt;15)' if r.get('paper') else '')


def table_html(settled, pending):
    H = [CSS, '<table><tr>',
         '<th style="text-align:left">Ματς</th><th>Pick</th><th>Τιμη</th><th>Κλεισιμο</th>',
         '<th>CLV</th><th>Σκορ</th><th>Τελικα xG</th><th>xG fair</th><th>xG value</th><th>Αποτελεσμα</th></tr>']
    for r in pending:
        ko = str(r.get('ko') or '')
        H.append(
            f'<tr class="pend"><td class="l"><img src="{TLOGO.format(r.get("hid"))}">'
            f'{_h.escape(r["home"])} – {_h.escape(r["away"])}'
            f'<div class="dim">{"🌐 " if r.get("intl") else ("🇪🇺 " if r.get("euro") else "")}{r["lg"]} · {ko[:10]} {ko[11:16]}{_when(r)} · ΕΚΚΡΕΜΕΙ</div></td>'
            f'<td class="pick">{_pick_cell(r)}</td>'
            f'<td>{r["odds"]:.2f}</td><td colspan="7" class="mut">παιζεται…</td></tr>')
    for r in settled:
        ko = str(r.get('ko') or '')
        if r.get('clv') is not None:
            closes = f'{r["close_odds"]:.2f}'
            clv = _pct(r.get('clv_pct'))
        elif r.get('close_odds') is not None:
            closes = (f'{r["close_odds"]:.2f}<div class="dim">γραμμη {"+" if r["close_line"] >= 0 else ""}'
                      f'{r["close_line"]:g}</div>')
            if r.get('clv_est_pct') is not None:
                clv = '≈' + _pct(r['clv_est_pct'])     # εκτιμηση: κλεισιμο μεταφρασμενο στη γραμμη μας
            else:
                clv = '<span class="mut">αλλη γραμμη</span>'
        else:
            closes = '<span class="mut">—</span>'; clv = '<span class="mut">—</span>'
        xg = (f'{r["xg_h"]:.2f} – {r["xg_a"]:.2f}' if r.get('xg_h') is not None
              else '<span class="mut">—</span>')
        H.append(
            f'<tr><td class="l"><img src="{TLOGO.format(r.get("hid"))}">'
            f'{_h.escape(r["home"])} – {_h.escape(r["away"])}'
            f'<div class="dim">{"🌐 " if r.get("intl") else ("🇪🇺 " if r.get("euro") else "")}{r["lg"]} · {ko[:10]} {ko[11:16]}{_when(r)}</div></td>'
            f'<td class="pick">{_pick_cell(r)}</td>'
            f'<td>{r["odds"]:.2f}</td><td>{closes}</td><td>{clv}</td>'
            f'<td>{_h.escape(str(r.get("score") or "—"))}</td><td>{xg}</td>'
            f'<td>{("%.2f" % r["xg_fair"]) if r.get("xg_fair") else "—"}</td>'
            f'<td>{_pct(r.get("xg_value"))}</td>'
            f'<td>{_res_chip(r.get("pnl"), r.get("odds", 2))}</td></tr>')
    H.append('</table>')
    return ''.join(H)


def cum_fig(settled):
    """Σωρευτικες μοναδες + σωρευτικο CLV, με τη σειρα των ματς."""
    import plotly.graph_objects as go
    rows = [r for r in settled if r.get('pnl') is not None]
    rows.sort(key=lambda r: str(r.get('ko') or ''))
    if not rows:
        return None
    x = list(range(1, len(rows) + 1))
    cum = []; s = 0.0
    for r in rows:
        s += r['pnl']; cum.append(round(s, 2))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=cum, mode='lines+markers', name='Μοναδες',
                             line=dict(color='#34d17a', width=2), marker=dict(size=5)))
    def _c(r):
        v = r.get('clv_pct')
        return v if v is not None else r.get('clv_est_pct')
    cl = [r for r in rows if _c(r) is not None]
    if cl:
        s = 0.0; cc = []
        for r in rows:
            s += (_c(r) or 0) * 100; cc.append(round(s, 1))
        fig.add_trace(go.Scatter(x=x, y=cc, mode='lines', name='Σωρ. CLV %',
                                 line=dict(color='#7ea2ff', width=1.5, dash='dot'), yaxis='y2'))
    fig.update_layout(paper_bgcolor='#0a0f1e', plot_bgcolor='#0a0f1e', height=300,
                      margin=dict(l=10, r=10, t=10, b=10),
                      font=dict(color='#8fa3c8', family='DM Sans', size=11),
                      xaxis=dict(gridcolor='#121b30', title='bet #'),
                      yaxis=dict(gridcolor='#121b30', title='μοναδες', zerolinecolor='#26324e'),
                      yaxis2=dict(overlaying='y', side='right', showgrid=False, title='CLV %'),
                      legend=dict(orientation='h', y=1.12, bgcolor='rgba(0,0,0,0)'))
    return fig
