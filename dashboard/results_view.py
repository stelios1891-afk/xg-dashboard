# -*- coding: utf-8 -*-
"""results_view.py — Results tab: αποτελεσματα ανα αγωνιστικη + λεπτομερειες ματς
(σκορ, ΠΡΑΓΜΑΤΙΚΟ xG απο shotmap FotMob — οχι compressed/0.25 πεναλτι — και xG chart ανα λεπτο)."""
import html as _h

import build_data


def season_matches(league):
    """Ολα τα ματς της σεζον με round/σκορ/κατασταση απο το FotMob leagues endpoint."""
    lid = build_data.LEAGUE_FOTMOB[league]
    d = build_data._fotmob(
        f'https://www.fotmob.com/api/data/leagues?id={lid}&season={build_data.CURRENT_FOTMOB_SEASON}')
    out = []
    for m in d.get('fixtures', {}).get('allMatches', []):
        st = m.get('status', {})
        h, a = m.get('home', {}), m.get('away', {})
        score = (st.get('scoreStr') or '').replace(' ', '')
        hs = as_ = None
        if '-' in score:
            try:
                hs, as_ = [int(x) for x in score.split('-')]
            except ValueError:
                pass
        out.append(dict(gw=int(m.get('round') or 0), fid=str(m.get('id')),
                        utc=st.get('utcTime', ''), finished=bool(st.get('finished')),
                        home=h.get('name'), away=a.get('name'),
                        home_id=h.get('id'), away_id=a.get('id'), hs=hs, aw=as_))
    return out


OUTCOME = {'Goal': '⚽ Γκολ', 'AttemptSaved': 'Αποκρουση', 'Miss': 'Αουτ', 'Post': 'Δοκαρι', 'Blocked': 'Κοντρα'}


def match_detail(fid):
    j = build_data._fotmob(f'https://www.fotmob.com/api/data/matchDetails?matchId={fid}')
    hdr = j.get('header') or {}
    teams = hdr.get('teams') or []
    if len(teams) < 2:
        return None
    c = j.get('content') or {}
    shots = []
    for s in ((c.get('shotmap') or {}).get('shots') or []):
        if s.get('expectedGoals') is None:
            continue
        shots.append(dict(
            team=s.get('teamId'), player=s.get('playerName'),
            minute=(s.get('min') or 0) + (s.get('minAdded') or 0) / 10.0,
            min_lbl='%d%s' % (s.get('min') or 0, "+%d" % s['minAdded'] if s.get('minAdded') else ''),
            xg=float(s['expectedGoals']), xgot=float(s.get('expectedGoalsOnTarget') or 0),
            goal=s.get('eventType') == 'Goal' and not s.get('isOwnGoal'),
            og=bool(s.get('isOwnGoal')), outcome=s.get('eventType'),
            pen=s.get('situation') == 'Penalty', ontarget=bool(s.get('isOnTarget'))))
    return dict(home=dict(name=teams[0].get('name'), id=teams[0].get('id'), score=teams[0].get('score')),
                away=dict(name=teams[1].get('name'), id=teams[1].get('id'), score=teams[1].get('score')),
                shots=shots)


def team_stats(det, side):
    tid = det[side]['id']
    sh = [s for s in det['shots'] if s['team'] == tid]
    return dict(xg=sum(s['xg'] for s in sh), xgot=sum(s['xgot'] for s in sh),
                shots=len(sh), ontarget=sum(1 for s in sh if s['ontarget']),
                big=sum(1 for s in sh if s['xg'] >= 0.3),
                pens=sum(1 for s in sh if s['pen']))


HOME_C, AWAY_C = '#4da3ff', '#ffb84d'


def xg_fig(det):
    import plotly.graph_objects as go
    fig = go.Figure()
    end = max([s['minute'] for s in det['shots']] + [90]) + 2
    for side, color in (('home', HOME_C), ('away', AWAY_C)):
        tid = det[side]['id']
        sh = sorted([s for s in det['shots'] if s['team'] == tid], key=lambda s: s['minute'])
        xs, ys = [0.0], [0.0]
        cum = 0.0
        for s in sh:
            xs.append(s['minute']); ys.append(cum)
            cum += s['xg']
            xs.append(s['minute']); ys.append(cum)
        xs.append(end); ys.append(cum)
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines', name=det[side]['name'],
            line=dict(color=color, width=2.6, shape='linear'),
            hoverinfo='skip'))
        # σουτ ως σημεια (hover: λεπτο, παικτης, xG, εκβαση)
        cum = 0.0; px, py, txt, size, symb = [], [], [], [], []
        for s in sh:
            cum += s['xg']
            px.append(s['minute']); py.append(cum)
            txt.append("%s' %s — xG %.2f · %s%s" % (
                s['min_lbl'], s['player'], s['xg'],
                OUTCOME.get(s['outcome'], s['outcome']), ' (πεναλτι)' if s['pen'] else ''))
            size.append(13 if s['goal'] else 6)
            symb.append('circle')
        fig.add_trace(go.Scatter(
            x=px, y=py, mode='markers', showlegend=False,
            marker=dict(color=color, size=size, symbol=symb,
                        line=dict(color='#0a0f1e', width=1)),
            hovertext=txt, hoverinfo='text'))
        # ετικετες στα γκολ
        cum = 0.0
        for s in sh:
            cum += s['xg']
            if s['goal']:
                fig.add_annotation(x=s['minute'], y=cum, text="⚽ %s %s'" % ((s['player'] or '').split()[-1], s['min_lbl']),
                                   font=dict(size=10, color=color), showarrow=True,
                                   arrowcolor=color, arrowwidth=1, ax=0, ay=-26, bgcolor='rgba(10,15,30,.75)')
    fig.add_vline(x=45.5, line_dash='dot', line_color='#33405e')
    fig.update_layout(
        template=None, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#8fa3c8', size=12), height=380,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation='h', y=1.08, x=0),
        xaxis=dict(title='Λεπτο', gridcolor='#141d33', zeroline=False, range=[0, end]),
        yaxis=dict(title='xG (σωρευτικο)', gridcolor='#141d33', zeroline=False, rangemode='tozero'),
        hoverlabel=dict(bgcolor='#111827', font=dict(color='#e8edf8')))
    return fig


def round_table_html(matches):
    rows = []
    for m in sorted(matches, key=lambda x: x['utc']):
        sc = '%d – %d' % (m['hs'], m['aw']) if m['hs'] is not None else str(m['utc'])[11:16]
        rows.append(
            f'<tr><td class="d">{str(m["utc"])[5:10]}</td>'
            f'<td class="t r">{_h.escape(m["home"] or "")}</td>'
            f'<td class="s">{sc}</td>'
            f'<td class="t">{_h.escape(m["away"] or "")}</td></tr>')
    css = """<style>
    *{box-sizing:border-box;margin:0;padding:0;}
    body{background:#0a0f1e;font-family:'DM Sans','Segoe UI',sans-serif;color:#e8edf8;}
    table{width:100%;border-collapse:collapse;background:#111827;border:1px solid #1e2d47;border-radius:12px;overflow:hidden;}
    td{padding:8px 10px;font-size:13.5px;border-bottom:1px solid #121b30;}
    td.d{color:#5a6b8c;font-size:11px;width:56px;}
    td.t{width:40%;} td.t.r{text-align:right;}
    td.s{text-align:center;font-family:'JetBrains Mono',monospace;font-weight:700;color:#e8edf8;width:70px;background:#0d1526;}
    </style><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=JetBrains+Mono:wght@700&display=swap" rel="stylesheet">"""
    return css + '<table>' + ''.join(rows) + '</table>'


def chances_html(det):
    def side_rows(side, color):
        tid = det[side]['id']
        sh = sorted([s for s in det['shots'] if s['team'] == tid], key=lambda s: -s['xg'])[:5]
        r = ''
        for s in sh:
            mark = '⚽ ' if s['goal'] else ''
            r += (f'<tr><td class="m">{s["min_lbl"]}\'</td><td>{mark}{_h.escape(s["player"] or "")}'
                  f'{" (πεν.)" if s["pen"] else ""}</td>'
                  f'<td class="x" style="color:{color}">{s["xg"]:.2f}</td>'
                  f'<td class="o">{OUTCOME.get(s["outcome"], s["outcome"])}</td></tr>')
        return r
    css = """<style>
    *{box-sizing:border-box;margin:0;padding:0;}
    body{background:#0a0f1e;font-family:'DM Sans','Segoe UI',sans-serif;color:#e8edf8;}
    .wrap{display:flex;gap:14px;} .col{flex:1;background:#111827;border:1px solid #1e2d47;border-radius:12px;padding:10px 12px;}
    h4{font-size:11px;color:#6b7fa3;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;}
    table{width:100%;border-collapse:collapse;} td{padding:5px 4px;font-size:12.5px;border-bottom:1px solid #121b30;}
    td.m{color:#5a6b8c;width:38px;font-family:'JetBrains Mono',monospace;font-size:11px;}
    td.x{font-family:'JetBrains Mono',monospace;font-weight:700;width:52px;text-align:right;}
    td.o{color:#8fa3c8;font-size:11.5px;text-align:right;}
    </style><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">"""
    return (css + '<div class="wrap">'
            f'<div class="col"><h4>Μεγαλες φασεις — {_h.escape(det["home"]["name"])}</h4><table>{side_rows("home", HOME_C)}</table></div>'
            f'<div class="col"><h4>Μεγαλες φασεις — {_h.escape(det["away"]["name"])}</h4><table>{side_rows("away", AWAY_C)}</table></div>'
            '</div>')
