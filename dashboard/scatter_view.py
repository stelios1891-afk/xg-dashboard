"""scatter_view.py — Scatter: npxG For (x) vs npxG Against (y, ανεστραμμενος). Πανω-δεξια = καλυτερο."""
import numpy as np
import plotly.graph_objects as go
import trendline

TLOGO = 'https://images.fotmob.com/image_resources/logo/teamlogo/{}.png'

def max_games(data):
    return max((len(d['xgf']) for d in data.values()), default=1)

def _points(data, gw_lo, gw_hi):
    pts = []
    for name, d in data.items():
        xgf = d['xgf'][gw_lo - 1:gw_hi]; xga = d['xga'][gw_lo - 1:gw_hi]
        if not xgf:
            continue
        pts.append(dict(team=name, tid=d['tid'],
                        xgf=float(np.mean(xgf)), xga=float(np.mean(xga))))
    return pts

def scatter_fig(data, gw_lo, gw_hi):
    pts = _points(data, gw_lo, gw_hi)
    if not pts:
        return go.Figure()
    xs = [p['xgf'] for p in pts]; ys = [p['xga'] for p in pts]
    axgf, axga = sum(xs) / len(xs), sum(ys) / len(ys)
    # στενα padding => ο x κολλαει στα δεδομενα (ομαδες απλωνονται· κακη τερμα αριστερα, καλη δεξια)
    padx = max(0.07, (max(xs) - min(xs)) * 0.08)
    pady = max(0.10, (max(ys) - min(ys)) * 0.10)
    xr = [min(xs) - padx, max(xs) + padx]
    yr = [min(ys) - pady, max(ys) + pady]
    xspan, yspan = xr[1] - xr[0], yr[1] - yr[0]
    # ΟΧΙ ισος αξονας· logos ~τετραγωνα με διορθωση aspect (πλατος:υψος πλοτ ~1.75)
    ASPECT = 1.75; base = 0.062
    sizey = yspan * base; sizex = xspan * base / ASPECT

    fig = go.Figure()
    # αορατα markers για hover
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode='markers', marker=dict(size=30, color='rgba(0,0,0,0)'),
        text=[f"<b>{p['team']}</b><br>npxG For {p['xgf']:.2f}<br>npxG Against {p['xga']:.2f}"
              f"<br>xGD {p['xgf']-p['xga']:+.2f}" for p in pts],
        hoverinfo='text', showlegend=False))
    # logos ως markers
    fig.update_layout(images=[dict(source=TLOGO.format(p['tid']), x=p['xgf'], y=p['xga'],
                                   xref='x', yref='y', sizex=sizex, sizey=sizey,
                                   xanchor='center', yanchor='middle', layer='above')
                              for p in pts])
    # γραμμες μεσου ορου (τεταρτημορια)
    fig.add_hline(y=axga, line=dict(color='#2a3a58', dash='dot', width=1))
    fig.add_vline(x=axgf, line=dict(color='#2a3a58', dash='dot', width=1))

    fig.update_layout(
        height=620, margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#8fa3c8', family='DM Sans, sans-serif', size=12), showlegend=False,
        xaxis=dict(title_text='npxG For (per game) →', range=xr, gridcolor='#16223a',
                   zeroline=False, linecolor='#1e2d47', tickfont=dict(color='#6b7fa3')),
        # ανεστραμμενος: μικρο xGA (καλη αμυνα) στην ΚΟΡΥΦΗ· ΟΧΙ scaleanchor (ο x να απλωνεται)
        yaxis=dict(title_text='← npxG Against (per game)', range=[yr[1], yr[0]], gridcolor='#16223a',
                   zeroline=False, linecolor='#1e2d47', tickfont=dict(color='#6b7fa3')))
    return fig
