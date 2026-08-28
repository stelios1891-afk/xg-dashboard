# -*- coding: utf-8 -*-
"""moves_view.py — Market Watch tab (α λα steamwatch): Biggest Movers των επερχομενων
ματς + διαγραμμα κινησης ανα ματς (1Χ2 & χαντικαπ), απο το δικο μας odds_history
(Pinnacle/Matchbook snapshots του scanner — αλλαγες μονο)."""
import os, json, datetime
import html as _h

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST_F = os.path.join(ROOT, 'odds_history.jsonl')
UTC = datetime.timezone.utc
try:
    from zoneinfo import ZoneInfo
    ATHENS = ZoneInfo('Europe/Athens')
except Exception:
    ATHENS = UTC
TLOGO = 'https://images.fotmob.com/image_resources/logo/teamlogo/{}.png'
C_HOME, C_DRAW, C_AWAY = '#34d17a', '#f3c74b', '#e05563'


def _dt(s):
    try:
        d = datetime.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
        return d.replace(tzinfo=UTC) if d.tzinfo is None else d.astimezone(UTC)
    except (ValueError, TypeError):
        return None


def load_history():
    """{key: {'meta':…, 'snaps': [σε χρονικη σειρα]}} απο το odds_history.jsonl."""
    H = {}
    if not os.path.exists(HIST_F):
        return H
    for line in open(HIST_F, encoding='utf-8'):
        try:
            r = json.loads(line)
        except Exception:
            continue
        t = _dt(r.get('t'))
        if t is None:
            continue
        key = f"{r.get('hid')}_{r.get('aid')}"
        d = H.setdefault(key, dict(meta=dict(lg=r.get('lg'), home=r.get('home'), away=r.get('away'),
                                             hid=r.get('hid'), aid=r.get('aid'), ko=r.get('ko')),
                                   snaps=[]))
        if r.get('ko'):
            d['meta']['ko'] = r['ko']
        d['snaps'].append(dict(t=t, line=r.get('line'), oh=r.get('oh'), oa=r.get('oa'),
                               h2h=r.get('h2h')))
    for d in H.values():
        d['snaps'].sort(key=lambda s: s['t'])
    return H


def upcoming(H, horizon_days=8):
    now = datetime.datetime.now(UTC)
    out = []
    for key, d in H.items():
        ko = _dt(d['meta'].get('ko'))
        if ko and now - datetime.timedelta(minutes=30) < ko < now + datetime.timedelta(days=horizon_days):
            out.append((key, d, ko))
    out.sort(key=lambda x: x[2])
    return out


# ---------- Biggest Movers ----------
def movers_rows(H, hours=48, top=12, min_move=0.01):
    """Μεγαλυτερες κινησεις 1Χ2 στα επερχομενα: ποια πλευρα «πηρε χρημα» (επεσε η αποδοση)."""
    now = datetime.datetime.now(UTC)
    rows = []
    for key, d, ko in upcoming(H):
        snaps = [s for s in d['snaps'] if s.get('h2h')]
        if len(snaps) < 2:
            continue
        cur = snaps[-1]
        base = None
        for s in snaps:                     # πρωτο snapshot μεσα στο παραθυρο των Χ ωρων
            if s['t'] >= now - datetime.timedelta(hours=hours):
                base = s; break
        if base is None or base is cur:
            base = snaps[0]
        if base is cur:
            continue
        best = None
        for i, side in enumerate(('H', 'D', 'A')):
            b, c = base['h2h'][i], cur['h2h'][i]
            if not b or not c:
                continue
            mv = (c - b) / b
            if best is None or mv < best[0]:      # πιο αρνητικο = μαζεψε χρημα
                best = (mv, side, b, c, i)
        if best is None or best[0] > -min_move:
            continue
        mv, side, b, c, i = best
        spark = [s['h2h'][i] for s in snaps if s.get('h2h') and s['h2h'][i]]
        m = d['meta']
        backed = m['home'] if side == 'H' else (m['away'] if side == 'A' else 'Ισοπαλια')
        rows.append(dict(key=key, lg=m['lg'], home=m['home'], away=m['away'], hid=m['hid'],
                         ko=ko, side=side, backed=backed, move=mv, before=b, now=c, spark=spark))
    rows.sort(key=lambda r: r['move'])
    return rows[:top]


def _spark_svg(vals, color='#34d17a', w=96, h=26):
    if len(vals) < 2:
        return ''
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1e-9
    pts = []
    for i, v in enumerate(vals):
        x = 2 + i * (w - 4) / (len(vals) - 1)
        y = h - 3 - (v - lo) / rng * (h - 6)
        pts.append(f'{x:.1f},{y:.1f}')
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" '
            f'stroke-width="1.6" stroke-linejoin="round"/></svg>')


CSS = """
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#0a0f1e;font-family:'DM Sans','Segoe UI',sans-serif;color:#e8edf8;padding:2px;}
table{width:100%;border-collapse:collapse;}
th{font-size:9.5px;color:#6b7fa3;text-transform:uppercase;letter-spacing:.8px;text-align:left;
   padding:8px 8px;border-bottom:1px solid #1e2d47;}
th.c,td.c{text-align:center;}
td{padding:9px 8px;border-bottom:1px solid #121b30;font-size:12.5px;vertical-align:middle;}
td img{width:17px;height:17px;object-fit:contain;vertical-align:-4px;margin-right:6px;}
.mt{font-weight:700;color:#e8edf8;}
.dim{color:#5a6b8c;font-size:10px;font-family:'JetBrains Mono',monospace;}
.tagH,.tagD,.tagA{display:inline-block;border-radius:5px;padding:2px 7px;font-size:10px;font-weight:700;margin-right:6px;}
.tagH{background:#10251b;color:#34d17a;border:1px solid #1e4a33;}
.tagD{background:#2b2410;color:#f3c74b;border:1px solid #4a3e1e;}
.tagA{background:#2a1418;color:#e05563;border:1px solid #4a1e26;}
.mv{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:14px;color:#34d17a;}
.od{font-family:'JetBrains Mono',monospace;color:#8fa3c8;}
.odb{font-family:'JetBrains Mono',monospace;font-weight:700;color:#e8edf8;font-size:14px;}
</style>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
"""

_DAYS = ['Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ']


def _kofmt(ko):
    k = ko.astimezone(ATHENS)
    return f'{_DAYS[k.weekday()]} {k.day}/{k.month} {k:%H:%M}'


def movers_html(rows):
    H = [CSS, '<table><tr><th>Ματς</th><th>Πηρε χρημα</th><th class="c">Κινηση</th>'
              '<th class="c">Πριν</th><th class="c">Τωρα</th><th class="c">Πορεια</th></tr>']
    tagcls = {'H': 'tagH', 'D': 'tagD', 'A': 'tagA'}
    sparkc = {'H': C_HOME, 'D': C_DRAW, 'A': C_AWAY}
    for r in rows:
        H.append(
            f'<tr><td><span class="mt"><img src="{TLOGO.format(r["hid"])}">'
            f'{_h.escape(r["home"])} – {_h.escape(r["away"])}</span>'
            f'<div class="dim">{r["lg"]} · {_kofmt(r["ko"])}</div></td>'
            f'<td><span class="{tagcls[r["side"]]}">{r["side"]}</span>{_h.escape(str(r["backed"]))}</td>'
            f'<td class="c"><span class="mv">↓{abs(r["move"])*100:.1f}%</span></td>'
            f'<td class="c od">{r["before"]:.2f}</td>'
            f'<td class="c odb">{r["now"]:.2f}</td>'
            f'<td class="c">{_spark_svg(r["spark"], sparkc[r["side"]])}</td></tr>')
    H.append('</table>')
    return ''.join(H)


# ---------- λιστα ματς πρωταθληματος ----------
def league_html(H, lg):
    rows = []
    for key, d, ko in upcoming(H):
        if d['meta']['lg'] != lg:
            continue
        snaps = [s for s in d['snaps'] if s.get('h2h')]
        cells = ''
        if len(snaps) >= 2:
            b, c = snaps[0], snaps[-1]
            for i, col in ((0, C_HOME), (1, C_DRAW), (2, C_AWAY)):
                bb, cc = b['h2h'][i], c['h2h'][i]
                mv = (cc - bb) / bb * 100 if bb and cc else 0
                arrow = ('<span style="color:#e05563">↑</span>' if mv > 0.5 else
                         ('<span style="color:#34d17a">↓</span>' if mv < -0.5 else
                          '<span style="color:#5a6b8c">·</span>'))
                cells += f'<td class="c odb">{cc:.2f} <span class="dim">{arrow}{abs(mv):.1f}%</span></td>'
        elif snaps:
            c = snaps[-1]
            cells = ''.join(f'<td class="c odb">{c["h2h"][i]:.2f}</td>' for i in range(3))
        else:
            cells = '<td class="c dim" colspan="3">—</td>'
        last = d['snaps'][-1]
        ah = (f'{last["line"]:+g} <span class="dim">({last["oh"]:.2f}/{last["oa"]:.2f})</span>'
              if last.get('line') is not None else '—')
        m = d['meta']
        rows.append(f'<tr><td><span class="mt"><img src="{TLOGO.format(m["hid"])}">'
                    f'{_h.escape(m["home"])} – {_h.escape(m["away"])}</span>'
                    f'<div class="dim">{_kofmt(ko)} · {len(d["snaps"])} καταγραφες</div></td>'
                    f'{cells}<td class="c od">{ah}</td></tr>')
    if not rows:
        return CSS + '<div class="dim" style="padding:14px">Δεν υπαρχουν καταγραφες για επερχομενα ματς εδω ακομα.</div>'
    return (CSS + '<table><tr><th>Ματς</th><th class="c">1</th><th class="c">Χ</th>'
                  '<th class="c">2</th><th class="c">Γραμμη AH</th></tr>' + ''.join(rows) + '</table>')


# ---------- διαγραμμα ματς ----------
def match_fig(d, market='1x2'):
    import plotly.graph_objects as go
    snaps = d['snaps']
    fig = go.Figure()
    lay = dict(paper_bgcolor='#0a0f1e', plot_bgcolor='#0d1426', height=380,
               margin=dict(l=10, r=10, t=16, b=10),
               font=dict(color='#8fa3c8', family='DM Sans', size=11),
               xaxis=dict(gridcolor='#121b30'), yaxis=dict(gridcolor='#16203a', title='αποδοση'),
               legend=dict(orientation='h', y=1.1, bgcolor='rgba(0,0,0,0)'),
               hovermode='x unified')
    # changes-only αποθηκευση: τραβα την τελευταια τιμη μεχρι τωρα (η τη σεντρα)
    now = datetime.datetime.now(UTC)
    ko = _dt(d['meta'].get('ko'))
    end = min(now, ko) if ko else now
    if snaps and end > snaps[-1]['t']:
        snaps = snaps + [dict(snaps[-1], t=end)]
    xs = [s['t'].astimezone(ATHENS) for s in snaps]
    if market == '1x2':
        m = d['meta']
        for i, (nm, col) in enumerate(((m['home'], C_HOME), ('Ισοπαλια', C_DRAW), (m['away'], C_AWAY))):
            ys = [s['h2h'][i] if s.get('h2h') else None for s in snaps]
            if not any(ys):
                continue
            fig.add_trace(go.Scatter(x=xs, y=ys, name=str(nm), mode='lines',
                                     line=dict(color=col, width=2, shape='hv'), connectgaps=True))
    else:
        fig.add_trace(go.Scatter(x=xs, y=[s.get('oh') for s in snaps], name='Γηπεδουχος',
                                 mode='lines', line=dict(color=C_HOME, width=2, shape='hv')))
        fig.add_trace(go.Scatter(x=xs, y=[s.get('oa') for s in snaps], name='Φιλοξενουμενος',
                                 mode='lines', line=dict(color=C_AWAY, width=2, shape='hv')))
        fig.add_trace(go.Scatter(x=xs, y=[s.get('line') for s in snaps], name='Γραμμη',
                                 mode='lines', line=dict(color='#7ea2ff', width=1.5, dash='dot', shape='hv'),
                                 yaxis='y2'))
        lay['yaxis2'] = dict(overlaying='y', side='right', showgrid=False, title='γραμμη',
                             zerolinecolor='#26324e')
    fig.update_layout(**lay)
    return fig
