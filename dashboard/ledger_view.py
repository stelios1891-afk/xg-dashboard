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
    settled = _jsonl(os.path.join(ROOT, 'clv_ledger.jsonl'))
    done = {f"{b.get('lg')}|{b.get('home')}|{b.get('away')}|{b.get('side')}|{b.get('hcap')}|{b.get('ko')}"
            for b in settled}
    pending = [b for b in _jsonl(os.path.join(ROOT, 'clv_bets.jsonl'))
               if f"{b.get('lg')}|{b.get('home')}|{b.get('away')}|{b.get('side')}|{b.get('hcap')}|{b.get('ko')}" not in done]
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
    settled.sort(key=lambda r: str(r.get('ko') or ''), reverse=True)
    pending.sort(key=lambda r: str(r.get('ko') or ''))
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


def table_html(settled, pending):
    H = [CSS, '<table><tr>',
         '<th style="text-align:left">Ματς</th><th>Pick</th><th>Τιμη</th><th>Κλεισιμο</th>',
         '<th>CLV</th><th>Σκορ</th><th>Τελικα xG</th><th>xG fair</th><th>xG value</th><th>Αποτελεσμα</th></tr>']
    for r in pending:
        team = r['home'] if r['side'] == 1 else r['away']
        tid = r.get('hid') if r['side'] == 1 else r.get('aid')
        ko = str(r.get('ko') or '')
        H.append(
            f'<tr class="pend"><td class="l"><img src="{TLOGO.format(r.get("hid"))}">'
            f'{_h.escape(r["home"])} – {_h.escape(r["away"])}'
            f'<div class="dim">{r["lg"]} · {ko[:10]} {ko[11:16]} · ΕΚΚΡΕΜΕΙ</div></td>'
            f'<td class="pick"><img src="{TLOGO.format(tid)}">{_h.escape(team)} '
            f'{"+" if r["hcap"] >= 0 else ""}{r["hcap"]:g}</td>'
            f'<td>{r["odds"]:.2f}</td><td colspan="7" class="mut">παιζεται…</td></tr>')
    for r in settled:
        team = r['home'] if r['side'] == 1 else r['away']
        tid = r.get('hid') if r['side'] == 1 else r.get('aid')
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
            f'<div class="dim">{r["lg"]} · {ko[:10]} {ko[11:16]}</div></td>'
            f'<td class="pick"><img src="{TLOGO.format(tid)}">{_h.escape(team)} '
            f'{"+" if r["hcap"] >= 0 else ""}{r["hcap"]:g}</td>'
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
