"""trend_view.py — Plotly figure + stat cards για τη σελιδα Trendline."""
import plotly.graph_objects as go

# team1: xGF γαλαζιο / xGA κοκκινο · team2: xGF χρυσο / xGA μωβ
C1F, C1A = '#38bdf8', '#f04f5a'
C2F, C2A = '#f5b731', '#a855f7'
GREEN = '#34d17a'

def make_fig(s1, n1, s2, n2, window):
    fig = go.Figure()
    single = s2 is None

    # --- Differential bars (μονο single team, δευτερος αξονας) ---
    if single:
        fig.add_trace(go.Bar(x=s1['x'], y=s1['diff'], name=f"Differential ({s1['season_xgd']:+.2f})",
                             yaxis='y2', marker_color='rgba(150,170,205,0.16)',
                             marker_line_width=0, hoverinfo='skip'))

    def add(s, name, cf, ca, lbl_for, lbl_ag):
        fig.add_trace(go.Scatter(x=s['x'], y=s['trend_f'], mode='lines', showlegend=False,
                                 line=dict(color=cf, width=1.3, dash='dash'), opacity=.5, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=s['x'], y=s['trend_a'], mode='lines', showlegend=False,
                                 line=dict(color=ca, width=1.3, dash='dash'), opacity=.5, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=s['x'], y=s['xgf'], name=lbl_for, mode='lines+markers',
                                 line=dict(color=cf, width=2.6), marker=dict(size=5)))
        fig.add_trace(go.Scatter(x=s['x'], y=s['xga'], name=lbl_ag, mode='lines+markers',
                                 line=dict(color=ca, width=2.6), marker=dict(size=5)))

    if single:
        add(s1, n1, C1F, C1A, f"For ({s1['season_xgf']:.2f})", f"Against ({s1['season_xga']:.2f})")
    else:
        add(s1, n1, C1F, C1A, f"{n1} xGF ({s1['season_xgf']:.2f})", f"{n1} xGA ({s1['season_xga']:.2f})")
        add(s2, n2, C2F, C2A, f"{n2} xGF ({s2['season_xgf']:.2f})", f"{n2} xGA ({s2['season_xga']:.2f})")

    # --- σταθερος/padded αξονας Y (οχι auto-zoom· floor <=0.5, ceiling >=2.0) ---
    vals = s1['xgf'] + s1['xga'] + (s2['xgf'] + s2['xga'] if s2 else [])
    lo, hi = (min(vals), max(vals)) if vals else (0.5, 2.0)
    ylo = max(0.0, min(0.5, lo - 0.2)); yhi = max(2.0, hi + 0.2)
    dmax = max((abs(d) for d in s1['diff']), default=1.0) if single else 1.0
    y2 = max(1.2, dmax * 1.45)

    fig.update_layout(
        height=470, margin=dict(l=10, r=10, t=54, b=10), bargap=0.25,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#8fa3c8', family='DM Sans, sans-serif', size=12),
        legend=dict(orientation='h', y=1.13, x=0.5, xanchor='center', bgcolor='rgba(0,0,0,0)',
                    font=dict(size=11)),
        hovermode='x unified',
        title=dict(text=f'ROLLING {window}-GAME npxG', x=0.01, y=0.97,
                   font=dict(color='#e8edf8', size=15, family='Bebas Neue, sans-serif')),
        yaxis=dict(title_text='npxG (rolling avg)', range=[ylo, yhi], gridcolor='#16223a',
                   zeroline=False, linecolor='#1e2d47', tickfont=dict(color='#6b7fa3')),
        yaxis2=dict(title_text='Differential', range=[-y2, y2], overlaying='y', side='right',
                    showgrid=False, zeroline=True, zerolinecolor='#1e2d47',
                    tickfont=dict(color='#5a6b8c'), visible=single),
        xaxis=dict(title_text='Games Played', gridcolor='#16223a', zeroline=False,
                   linecolor='#1e2d47', tickfont=dict(color='#6b7fa3')))
    return fig

def _card(title, tcolor, value, vcolor, sub):
    return (f'<div class="tcard"><div class="tt" style="color:{tcolor}">{title}</div>'
            f'<div class="tv" style="color:{vcolor}">{value}</div><div class="ts">{sub}</div></div>')

CARD_CSS = """
<style>
.tcards{display:flex;gap:12px;flex-wrap:wrap;margin:6px 0 4px;}
.tcard{background:#0d1426;border:1px solid #1a2540;border-radius:12px;padding:13px 16px;min-width:150px;flex:1;}
.tcard .tt{font-size:10.5px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;margin-bottom:5px;}
.tcard .tv{font-family:'JetBrains Mono',monospace;font-size:30px;font-weight:700;line-height:1;}
.tcard .ts{font-size:10px;color:#5a6b8c;margin-top:5px;}
</style>
"""

RED = '#f04f5a'
def _xgd_c(v):
    return GREEN if v >= 0 else RED

def cards_html(n1, s1, n2, s2, window):
    w = window
    d1 = _xgd_c(s1['last_xgd'])
    cs = _card(f'{n1} xGF', C1F, f"{s1['last_xgf']:.2f}", C1F, f'Latest {w}-game avg')
    cs += _card(f'{n1} xGA', C1A, f"{s1['last_xga']:.2f}", C1A, f'Latest {w}-game avg')
    cs += _card(f'{n1} xGD', d1, f"{s1['last_xgd']:+.2f}", d1, 'For minus Against')
    if s2:
        d2 = _xgd_c(s2['last_xgd'])
        cs += _card(f'{n2} xGF', C2F, f"{s2['last_xgf']:.2f}", C2F, f'Latest {w}-game avg')
        cs += _card(f'{n2} xGA', C2A, f"{s2['last_xga']:.2f}", C2A, f'Latest {w}-game avg')
        cs += _card(f'{n2} xGD', d2, f"{s2['last_xgd']:+.2f}", d2, 'For minus Against')
    return CARD_CSS + f'<div class="tcards">{cs}</div>'
