"""value_view.py — HTML cards για τα live Value Picks."""
import html as _h
import build_data

TLOGO = 'https://images.fotmob.com/image_resources/logo/teamlogo/{}.png'
LLOGO = 'https://images.fotmob.com/image_resources/logo/leaguelogo/dark/{}.png'
LEAGUE_LABELS = {'EPL': 'Premier League', 'LaLiga': 'La Liga', 'SerieA': 'Serie A',
                 'Bundesliga': 'Bundesliga', 'Ligue1': 'Ligue 1', 'Eredivisie': 'Eredivisie',
                 'PrimeiraLiga': 'Primeira',
                 'ChampionsLeague': 'Champions League', 'EuropaLeague': 'Europa League',
                 'ConferenceLeague': 'Conference League'}
EURO_FOTMOB = {'ChampionsLeague': 42, 'EuropaLeague': 73, 'ConferenceLeague': 10216}

CSS = """
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#0a0f1e;font-family:'DM Sans','Segoe UI',sans-serif;color:#e8edf8;padding:2px;}
.wrap{display:flex;flex-direction:column;gap:9px;}
.pc{background:#111827;border:1px solid #1e2d47;border-left:3px solid #4b7cf3;border-radius:12px;padding:12px 15px;}
.pc.hi{border-left-color:#34d17a;}
.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:9px;}
.lg{display:flex;align-items:center;gap:7px;font-size:10px;color:#6b7fa3;text-transform:uppercase;letter-spacing:.6px;}
.lg img{width:16px;height:16px;object-fit:contain;}
.when{font-size:10px;color:#5a6b8c;font-family:'JetBrains Mono',monospace;}
.mrow{display:flex;align-items:center;gap:10px;}
.tm{display:flex;align-items:center;gap:7px;font-size:14px;}
.tm img{width:22px;height:22px;object-fit:contain;}
.tm.pick{font-weight:700;color:#e8edf8;}
.tm.dim{color:#6b7fa3;}
.vs{color:#5a6b8c;font-size:11px;}
.bet{margin-left:auto;background:#182444;border:1px solid #2d4470;border-radius:8px;padding:5px 11px;
     font-family:'JetBrains Mono',monospace;font-weight:700;font-size:13px;color:#7ea2ff;white-space:nowrap;}
.stats{display:flex;gap:20px;margin-top:10px;padding-top:9px;border-top:1px solid #121b30;flex-wrap:wrap;}
.st{display:flex;flex-direction:column;gap:1px;}
.st .k{font-size:9px;color:#6b7fa3;text-transform:uppercase;letter-spacing:.5px;}
.st .v{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:14px;}
.v.edge{color:#34d17a;}.v.stake{color:#7ea2ff;}
.tag{font-size:8.5px;padding:1px 6px;border-radius:4px;margin-left:6px;}
.tag.watch{background:rgba(245,183,49,.14);color:#f5b731;border:1px solid rgba(245,183,49,.3);}
.tag.lc{background:rgba(240,79,90,.12);color:#f04f5a;border:1px solid rgba(240,79,90,.3);}
.tag.eu{background:rgba(126,162,255,.12);color:#7ea2ff;border:1px solid rgba(126,162,255,.3);}
.tag.t75{background:rgba(52,209,122,.12);color:#34d17a;border:1px solid rgba(52,209,122,.3);}
.bet.ov{color:#3ec98f;border-color:#2d6e57;}
</style>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
"""

WATCH = {'PrimeiraLiga'}

def _logo(tid, cls='', tpl=TLOGO):
    return f'<img class="{cls}" src="{tpl.format(tid)}" onerror="this.style.visibility=\'hidden\'">' if tid else ''

def pick_card(p):
    side = p['side']
    over = side == 0                     # ευρωπαϊκο pick στα γκολ (Over)
    hcls = 'pick' if side == 1 else 'dim'
    acls = 'pick' if side == -1 else 'dim'
    hi = 'hi' if p['edge'] >= 0.15 else ''
    lid = build_data.LEAGUE_FOTMOB.get(p['lg']) or EURO_FOTMOB.get(p['lg'])
    tags = ''
    if p['lg'] in WATCH:
        tags += '<span class="tag watch">watch</span>'
    if p.get('hnote') or p.get('anote'):
        tags += '<span class="tag lc">low-conf</span>'
    if p.get('eu'):
        tags += '<span class="tag eu">EU beta</span>'
    if p.get('tag75'):
        tags += '<span class="tag t75">🎯 −0.75</span>'
    if over:
        bet = _h.escape(p.get('bet') or f"Over {p['hcap']:g}")
    else:
        pick_team = p['home'] if side == 1 else p['away']
        bet = f"{_h.escape(pick_team)} {'+' if p['hcap'] >= 0 else ''}{p['hcap']:g}"
    proj = f"{p['proj_odds']:.2f}" if p.get('proj_odds') else '—'
    stake_k, stake_v = ('Ποντ.', '~¼ μον.') if p.get('eu') else \
        ('Ποντ. (καβα)', f"{p['stake_final']*100:.1f}%")
    return f"""
<div class="pc {hi}">
  <div class="top">
    <div class="lg">{_logo(lid, tpl=LLOGO)}{LEAGUE_LABELS.get(p['lg'], p['lg'])}{tags}</div>
    <div class="when">{_h.escape((p.get('when') or '').replace('T', ' '))}</div>
  </div>
  <div class="mrow">
    <div class="tm {hcls}">{_logo(p.get('home_id'))}{_h.escape(p['home'])}</div>
    <span class="vs">vs</span>
    <div class="tm {acls}">{_logo(p.get('away_id'))}{_h.escape(p['away'])}</div>
    <div class="bet {'ov' if over else ''}">{bet}</div>
  </div>
  <div class="stats">
    <div class="st"><span class="k">Projection</span><span class="v">{proj}</span></div>
    <div class="st"><span class="k">Market</span><span class="v">{p['odds']:.2f}</span></div>
    <div class="st"><span class="k">Edge</span><span class="v edge">{p['edge']*100:.0f}%</span></div>
    <div class="st"><span class="k">{stake_k}</span><span class="v stake">{stake_v}</span></div>
  </div>
</div>"""

def picks_html(picks):
    picks = sorted(picks, key=lambda p: (p.get('when') or '9999'))   # χρονολογικα: νωριτερο πανω, πιο μετα κατω
    return CSS + '<div class="wrap">' + ''.join(pick_card(p) for p in picks) + '</div>'
