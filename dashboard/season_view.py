"""
season_view.py — 🏆 SEASON PROJECTIONS tab (22/9/2026, αιτημα Στελιου, οπως teamslab page_season_projections).
Διαβαζει season_projections.json (season_sim_2627.py: Monte Carlo 10.000 runs, μεθοδος M2 ρ=0.15 s0=0.10 που
περασε την επικυρωση 5 σεζον — season_sim_validate_out.txt) και δειχνει ανα λιγκα:
  πινακας: rating (total/att/def) · μεση προσομοιωμενη σεζον (W-D-L, GD, pts, 80% ευρος) · πιθανοτητες τελους
  (τιτλος / UCL / Ευρωπη / υποβιβασμος) · heatmap κατανομης θεσης.
"""
import os, json
import plotly.graph_objects as go

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ_F = os.path.join(ROOT, 'season_projections.json')
LOGO = 'https://images.fotmob.com/image_resources/logo/teamlogo/{}.png'

LEAGUE_LABELS = {'EPL': 'Premier League', 'LaLiga': 'La Liga', 'SerieA': 'Serie A', 'Bundesliga': 'Bundesliga',
                 'Ligue1': 'Ligue 1', 'Eredivisie': 'Eredivisie', 'PrimeiraLiga': 'Primeira Liga'}


def load():
    try:
        with open(PROJ_F, encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return None


def _teams(L):
    t = L['teams']
    rows = list(t.values()) if isinstance(t, dict) else list(t)
    if isinstance(t, dict):
        for name, r in t.items():
            r.setdefault('name', name)
    return sorted(rows, key=lambda r: (-r['e_pts'], -r.get('e_gd', 0)))


def _pct(p, hi_good=True):
    """κελι πιθανοτητας με χρωμα: πρασινο για καλες (τιτλος/UCL), κοκκινο για υποβιβασμο."""
    if p is None:
        return '<td class="p dim">—</td>'
    v = p * 100
    txt = '<1%' if 0 < v < 1 else (f'{v:.0f}%' if v >= 1 else '0%')
    a = min(v / 100, 1.0) ** 0.6
    col = f'rgba(52,209,122,{0.08 + 0.55 * a:.2f})' if hi_good else f'rgba(255,107,107,{0.08 + 0.55 * a:.2f})'
    cls = 'p' if v >= 1 else 'p dim'
    return f'<td class="{cls}" style="background:{col}">{txt}</td>'


def _rating(v, kind):
    if kind == 'tot':
        col = '#34d17a' if v > 0.15 else ('#ff6b6b' if v < -0.15 else '#cdd8ee')
        return f'<td class="r" style="color:{col}">{v:+.2f}</td>'
    # att: πιο ψηλο = καλυτερο· def: πιο χαμηλο = καλυτερο (xG κατα ανα ματς)
    good = (v >= 1.5) if kind == 'att' else (v <= 1.15)
    bad = (v <= 1.1) if kind == 'att' else (v >= 1.5)
    bg = 'rgba(52,209,122,.25)' if good else ('rgba(255,107,107,.25)' if bad else 'rgba(243,199,75,.18)')
    return f'<td class="r"><span class="pill" style="background:{bg}">{v:.2f}</span></td>'


def table_html(lg, L):
    rows = _teams(L)
    s = L.get('slots', {})
    ucl, eur, rel = s.get('ucl', 4), s.get('eur', 6), s.get('rel', 3)
    has_po = s.get('rel_po', False)
    n = len(rows)
    css = """<style>
body{margin:0;background:#0a0f1e;font-family:'DM Sans',sans-serif;color:#cdd8ee;}
table{border-collapse:collapse;width:100%;font-size:12px;table-layout:auto;}
th{background:#16203a;color:#8fa3c8;font-weight:600;padding:5px 3px;text-align:center;font-size:9.5px;letter-spacing:.5px;text-transform:uppercase;border-bottom:1px solid #26324e;white-space:nowrap;}
th.l{text-align:left;} th.grp{background:#0f1830;color:#6b7fa3;border-bottom:none;font-size:9px;letter-spacing:1.2px;}
td{padding:4px 3px;border-bottom:1px solid #1a2540;text-align:center;font-family:monospace;white-space:nowrap;}
td.t{text-align:left;font-family:'DM Sans',sans-serif;font-weight:600;color:#e8edf8;white-space:nowrap;padding-right:8px;}
td.t img{width:17px;height:17px;vertical-align:middle;margin-right:5px;}
td.t .now{color:#6b7fa3;font-weight:400;font-size:10.5px;margin-left:5px;}
td.pos{color:#8fa3c8;width:18px;}
td.p{font-weight:700;color:#e8edf8;min-width:34px;} td.p.dim{color:#5a6b8c;font-weight:400;}
.pts{font-weight:700;color:#f3c74b;} .rng{color:#8fa3c8;font-size:10px;margin-left:3px;}
.pill{display:inline-block;padding:1px 6px;border-radius:9px;font-weight:600;color:#e8edf8;}
tr.cut-ucl td{border-bottom:2px solid #4b7cf3;} tr.cut-eur td{border-bottom:2px solid #f3c74b;} tr.cut-rel td{border-bottom:2px solid #ff6b6b;}
</style>"""
    h = css + '<table><tr>'
    h += '<th class="grp" colspan="2"></th><th class="grp" colspan="3">Rating</th><th class="grp" colspan="3">Μεση προσομοιωμενη σεζον</th>'
    h += f'<th class="grp" colspan="{4 + (1 if has_po else 0)}">Πιθανοτητες τελους σεζον</th></tr>'
    h += '<tr><th>#</th><th class="l">Ομαδα · βαθμοι τωρα</th><th>Total</th><th>Att</th><th>Def</th>'
    h += '<th>W-D-L</th><th>GD</th><th>Pts · 80%</th>'
    h += f'<th>Τιτλος</th><th>UCL ({ucl})</th><th>Ευρωπη ({eur})</th>'
    if has_po:
        h += '<th>Playoff</th>'
    h += f'<th>Υποβ. ({rel})</th></tr>'
    for i, r in enumerate(rows, 1):
        cls = 'cut-ucl' if i == ucl else ('cut-eur' if i == eur else ('cut-rel' if i == n - rel else ''))
        h += f'<tr class="{cls}"><td class="pos">{i}</td>'
        logo = f'<img src="{LOGO.format(r["id"])}" onerror="this.style.display=\'none\'">' if r.get('id') else ''
        h += (f'<td class="t">{logo}{r["name"]}<span class="now">{r["pts_now"]}β {r["w"]}-{r["d"]}-{r["l"]}</span></td>')
        h += _rating(r['rating_total'], 'tot') + _rating(r['rating_att'], 'att') + _rating(r['rating_def'], 'def')
        h += f'<td>{r["e_w"]:.0f}-{r["e_d"]:.0f}-{r["e_l"]:.0f}</td>'
        gd = r['e_gd']
        h += f'<td style="color:{"#34d17a" if gd > 0 else ("#ff6b6b" if gd < 0 else "#cdd8ee")}">{gd:+.0f}</td>'
        h += f'<td><span class="pts">{r["e_pts"]:.1f}</span> <span class="rng">{r["pts_p10"]:.0f}–{r["pts_p90"]:.0f}</span></td>'
        h += _pct(r['p_title']) + _pct(r['p_ucl']) + _pct(r['p_eur'])
        if has_po:
            h += _pct(r.get('p_rel_po'), hi_good=False)
        h += _pct(r['p_rel'], hi_good=False) + '</tr>'
    h += '</table>'
    return h


def heatmap_fig(lg, L):
    rows = _teams(L)
    n = len(rows)
    z = [[p * 100 for p in r['pos_dist'][:n]] for r in rows]
    names = [r['name'] for r in rows]
    fig = go.Figure(data=go.Heatmap(
        z=z, x=[str(i) for i in range(1, n + 1)], y=names,
        colorscale=[[0, '#0d1426'], [0.15, '#1c2a42'], [0.4, '#2d5fbf'], [0.7, '#4b7cf3'], [1, '#9fc2ff']],
        zmin=0, zmax=max(45, max(max(row) for row in z)),
        text=[[('' if v < 2.5 else f'{v:.0f}') for v in row] for row in z], texttemplate='%{text}',
        textfont=dict(size=10, color='#e8edf8'),
        hovertemplate='%{y} · θεση %{x}: %{z:.1f}%<extra></extra>', showscale=False))
    fig.update_layout(paper_bgcolor='#0a0f1e', plot_bgcolor='#0a0f1e', margin=dict(l=10, r=10, t=30, b=30),
                      height=28 * n + 80, font=dict(family='DM Sans', color='#cdd8ee', size=11),
                      xaxis=dict(title='Τελικη θεση', side='top', tickfont=dict(size=10)),
                      yaxis=dict(autorange='reversed', tickfont=dict(size=11)))
    return fig
