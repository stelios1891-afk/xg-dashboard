"""xgstats_view.py — XG Rankings (For/Against διπλα-διπλα) + xGD table + xGD bar."""
import html as _h
import plotly.graph_objects as go

TLOGO = 'https://images.fotmob.com/image_resources/logo/teamlogo/{}.png'
GREEN, RED = '#34d17a', '#f04f5a'

CSS = """
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#0a0f1e;font-family:'DM Sans','Segoe UI',sans-serif;color:#e8edf8;padding:2px;}
.cols{display:flex;gap:26px;flex-wrap:wrap;}
.col{flex:1;min-width:320px;}
.ch{font-size:11px;font-weight:700;letter-spacing:.6px;color:#7ea2ff;text-transform:uppercase;
    padding:2px 8px 8px;border-bottom:1px solid #1e2d47;margin-bottom:4px;}
.rrow{display:flex;align-items:center;gap:10px;padding:7px 8px;border-bottom:1px solid #121b30;}
.rrow:hover{background:#0f1830;}
.rk{width:20px;text-align:right;color:#5a6b8c;font-size:12px;font-family:'JetBrains Mono',monospace;}
.rrow img{width:20px;height:20px;object-fit:contain;flex:none;}
.nm{flex:1;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.rv{display:flex;align-items:center;gap:8px;font-family:'JetBrains Mono',monospace;font-weight:700;font-size:13.5px;}
.sq{width:11px;height:11px;border-radius:3px;flex:none;}
/* xGD table */
table{border-collapse:collapse;width:100%;font-size:13px;}
th{padding:8px 10px;text-align:right;color:#8fa3c8;font-size:10px;font-weight:600;letter-spacing:.4px;
   text-transform:uppercase;border-bottom:1px solid #1e2d47;}
th.tm{text-align:left;}
td{padding:7px 10px;text-align:right;border-bottom:1px solid #121b30;font-family:'JetBrains Mono',monospace;font-weight:700;}
td.tm{text-align:left;font-family:'DM Sans',sans-serif;font-weight:500;}
tr:hover td{background:#0f1830;}
.tmc{display:flex;align-items:center;gap:9px;}
.tmc img{width:20px;height:20px;object-fit:contain;}
.rkc{color:#5a6b8c;font-family:'JetBrains Mono',monospace;font-weight:400;}
</style>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
"""

def _heat(t):
    t = max(0.0, min(1.0, t))
    return f"hsl({t*130:.0f},66%,56%)"   # 0=κοκκινο .. 1=πρασινο

def _rank_col(rows, key, header, good_high):
    srt = sorted(rows, key=lambda r: r[key], reverse=good_high)
    vals = [r[key] for r in srt]
    lo, hi = min(vals), max(vals); rng = (hi - lo) or 1.0
    out = f'<div class="col"><div class="ch">{header}</div>'
    for i, r in enumerate(srt, 1):
        t = (r[key] - lo) / rng
        if not good_high:
            t = 1 - t
        c = _heat(t)
        logo = f'<img src="{TLOGO.format(r["tid"])}" onerror="this.style.visibility=\'hidden\'">' if r.get('tid') else ''
        out += (f'<div class="rrow"><span class="rk">{i}</span>{logo}'
                f'<span class="nm">{_h.escape(r["team"])}</span>'
                f'<span class="rv"><span class="sq" style="background:{c}"></span>'
                f'<span style="color:{c}">{r[key]:.2f}</span></span></div>')
    return out + '</div>'

def rankings_html(rows):
    return (CSS + '<div class="cols">'
            + _rank_col(rows, 'xgf', 'xG For (attack)', True)
            + _rank_col(rows, 'xga', 'xG Against (defence)', False)
            + '</div>')

def xgd_table_html(rows):
    srt = sorted(rows, key=lambda r: -r['xgd'])
    body = ''
    for i, r in enumerate(srt, 1):
        cx = GREEN if r['xgd'] >= 0 else RED
        cg = GREEN if r['gd'] >= 0 else RED
        logo = f'<img src="{TLOGO.format(r["tid"])}" onerror="this.style.visibility=\'hidden\'">' if r.get('tid') else ''
        body += (f'<tr><td class="tm rkc">{i}</td>'
                 f'<td class="tm"><div class="tmc">{logo}<span>{_h.escape(r["team"])}</span></div></td>'
                 f'<td style="color:{cx}">{r["xgd"]:+.2f}</td>'
                 f'<td style="color:{cg}">{r["gd"]:+.2f}</td></tr>')
    return (CSS + '<table><thead><tr><th class="tm">#</th><th class="tm">Team</th>'
            '<th>xGD</th><th>GD</th></tr></thead><tbody>' + body + '</tbody></table>')

def xgd_bar_fig(rows):
    srt = sorted(rows, key=lambda r: r['xgd'])   # ascending => καλυτερο στην κορυφη (reversed axis)
    names = [r['team'] for r in srt]
    vals = [r['xgd'] for r in srt]
    colors = ['#4b7cf3' if v >= 0 else '#f04f5a' for v in vals]
    fig = go.Figure(go.Bar(x=vals, y=names, orientation='h', marker_color=colors,
                           text=[f'{v:+.2f}' for v in vals], textposition='outside',
                           textfont=dict(size=10, color='#8fa3c8'), cliponaxis=False))
    fig.update_layout(
        height=max(360, len(names) * 26 + 60), margin=dict(l=6, r=30, t=10, b=30),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#8fa3c8', family='DM Sans, sans-serif', size=11), showlegend=False,
        xaxis=dict(title_text='xGD per game', gridcolor='#16223a', zeroline=True,
                   zerolinecolor='#2a3a58', tickfont=dict(color='#6b7fa3')),
        yaxis=dict(tickfont=dict(color='#cdd8ee', size=11), automargin=True))
    return fig
