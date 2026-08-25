"""
streamlit_app.py — LIVE dashboard προβλεψεων (ιδιωτικο, Streamlit Community Cloud).

Layout (εμπνευσμενο απο TeamsLab):
  - ΠΑΝΩ: μπαρα με league logos (κλικ = επιλογη πρωταθληματος).
  - ΑΡΙΣΤΕΡΑ: μενου σελιδων (Match Projections ενεργο· τα υπολοιπα placeholders).
  - ΚΕΝΤΡΟ: το περιεχομενο της σελιδας.

Τρεξε τοπικα:  streamlit run dashboard/streamlit_app.py
"""
import os, sys, json
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_data
import cards
import goal_stats
import goal_view
import trendline
import trend_view
import scatter_view
import xgstats
import xgstats_view
import value_view

st.set_page_config(page_title="xG Model — Live", page_icon="⚽", layout="wide",
                   initial_sidebar_state="expanded")

LEAGUE_LABELS = {'EPL': 'Premier League', 'LaLiga': 'La Liga', 'SerieA': 'Serie A',
                 'Bundesliga': 'Bundesliga', 'Ligue1': 'Ligue 1', 'Eredivisie': 'Eredivisie',
                 'PrimeiraLiga': 'Primeira Liga'}
LEAGUE_COUNTRY = {'EPL': 'ENGLAND', 'LaLiga': 'SPAIN', 'SerieA': 'ITALY', 'Bundesliga': 'GERMANY',
                  'Ligue1': 'FRANCE', 'Eredivisie': 'NETHERLANDS', 'PrimeiraLiga': 'PORTUGAL'}
LEAGUE_LOGO = 'https://images.fotmob.com/image_resources/logo/leaguelogo/dark/{}.png'  # dark-mode variant (ανοιχτοχρωμο σε σκουρο φοντο)

# (id, label, icon)· ενεργα: projections, goals
PAGES = [('summary', 'Summary', '📊'), ('trend', 'Trendline', '📈'), ('pi', 'Pi Rating', '🔵'),
         ('team', 'Team Rating', '🛡️'), ('scatter', 'Scatter Plots', '✳️'),
         ('ave', 'Actual vs Expected', '🎯'), ('value', 'Value Picks', '💰'),
         ('projections', 'Match Projections', '🗓️'),
         ('goals', 'Goal Stats', '⚽'), ('xgstats', 'XG Stats', '📶'),
         ('season', 'Season Projections', '🏆'), ('perf', 'Model Performance', '📐')]
PAGE_LABEL = {p[0]: p[1] for p in PAGES}
ACTIVE_PAGES = {'projections', 'goals', 'trend', 'scatter', 'xgstats', 'value'}

@st.cache_data(ttl=6 * 3600, show_spinner="Υπολογισμος προβλεψεων...")
def load_matches():
    return build_data.build_matches()

st.markdown("""
<style>
.stApp{background:#0a0f1e;}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding-top:1rem;max-width:1250px;}
section[data-testid="stSidebar"]{background:#0d1426;border-right:1px solid #1a2540;}
h1,h2,h3{color:#e8edf8;font-family:'DM Sans',sans-serif;}
/* league logos bar */
.lgbar{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;padding:6px 0 14px;
       border-bottom:1px solid #1a2540;margin-bottom:16px;}
.lgbtn{width:52px;height:44px;display:flex;align-items:center;justify-content:center;border-radius:11px;
       border:1px solid transparent;background:#0f1830;transition:all .15s;}
.lgbtn:hover{border-color:#2d4470;background:#16203a;}
.lgbtn.active{border-color:#4b7cf3;background:#182444;box-shadow:0 0 0 1px #4b7cf3;}
.lgbtn img{width:28px;height:28px;object-fit:contain;}
/* sidebar menu */
.brand{font-family:'Bebas Neue',sans-serif;font-size:23px;letter-spacing:2px;color:#4b7cf3;padding:2px 0 2px;}
.brand span{color:#e8edf8;opacity:.75;}
.brand-sub{font-size:9px;color:#5a6b8c;letter-spacing:2px;margin-bottom:14px;}
.menu{display:flex;flex-direction:column;gap:3px;}
.menu a{display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:9px;text-decoration:none;
        color:#8fa3c8;font-size:13.5px;font-family:'DM Sans',sans-serif;transition:all .12s;}
.menu a:hover{background:#16203a;color:#cdd8ee;}
.menu a.on{background:#1c2a42;color:#e8edf8;font-weight:600;}
.menu a.soon{opacity:.5;}
.menu a .mi{width:18px;text-align:center;}
.menu a .tag{margin-left:auto;font-size:8px;color:#5a6b8c;border:1px solid #26324e;border-radius:4px;padding:1px 4px;}
.lg-title{display:flex;align-items:center;gap:13px;}
.lg-title img{width:40px;height:40px;object-fit:contain;}
.lg-title .nm{font-family:'Bebas Neue',sans-serif;font-size:30px;letter-spacing:1.5px;color:#e8edf8;line-height:1;}
.lg-title .co{font-size:10px;color:#6b7fa3;letter-spacing:2px;}
</style>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;600;700&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

matches, stats = load_matches()
proj = [m for m in matches if m.get('projectable')]
avail_lgs = [lg for lg in build_data.LEAGUE_FOTMOB if any(m['league'] == lg for m in proj)]

qp = st.query_params
league = qp.get('league') or (avail_lgs[0] if avail_lgs else 'EPL')
if league not in avail_lgs:
    league = avail_lgs[0] if avail_lgs else 'EPL'
page = qp.get('page') or 'projections'

# ---------- SIDEBAR: brand + page menu ----------
with st.sidebar:
    st.markdown('<div class="brand">xG<span>MODEL</span></div>'
                '<div class="brand-sub">LIVE PROJECTIONS</div>', unsafe_allow_html=True)
    items = ''
    for pid, label, icon in PAGES:
        cls = 'on' if pid == page else ('soon' if pid not in ACTIVE_PAGES else '')
        tag = '' if pid in ACTIVE_PAGES else '<span class="tag">soon</span>'
        items += f'<a class="{cls}" href="?league={league}&page={pid}" target="_self"><span class="mi">{icon}</span>{label}{tag}</a>'
    st.markdown(f'<div class="menu">{items}</div>', unsafe_allow_html=True)

# ---------- TOP: league logos ----------
bar = '<div class="lgbar">'
for lg in avail_lgs:
    fid = build_data.LEAGUE_FOTMOB[lg]
    cls = 'active' if lg == league else ''
    bar += (f'<a class="lgbtn {cls}" href="?league={lg}&page={page}" target="_self" title="{LEAGUE_LABELS.get(lg, lg)}">'
            f'<img src="{LEAGUE_LOGO.format(fid)}" onerror="this.style.opacity=0"></a>')
bar += '</div>'
st.markdown(bar, unsafe_allow_html=True)

# ---------- MAIN CONTENT ----------
def render_projections(league):
    lg_matches = [m for m in proj if m['league'] == league]
    gws = sorted({m['gw'] for m in lg_matches})
    fid = build_data.LEAGUE_FOTMOB[league]
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(
            f'<div class="lg-title"><img src="{LEAGUE_LOGO.format(fid)}">'
            f'<div><div class="nm">{LEAGUE_LABELS.get(league, league)}</div>'
            f'<div class="co">{LEAGUE_COUNTRY.get(league, "")}</div></div></div>', unsafe_allow_html=True)
    with c2:
        gw = st.selectbox("Αγωνιστικη", gws, format_func=lambda x: f"GW {x}", key=f"gw_{league}")
    sel = sorted([m for m in lg_matches if m['gw'] == gw], key=lambda m: m['utc'])
    ws = [m['warm_cur'] for m in sel if 'warm_cur' in m]
    if ws:
        cur = sum(ws) / len(ws) * 100
        st.caption(f"⚖ Warm-start (K=6): **{cur:.0f}% φετινη 26/27** · **{100-cur:.0f}% περσινη 25/26** "
                   "— το βαρος της φετινης ανεβαινει οσο παιζονται ματς (n/(n+6)).")
    st.components.v1.html(cards.cards_block(sel), height=min(len(sel) * 118 + 40, 6000), scrolling=True)

def _lg_header(league, sub):
    fid = build_data.LEAGUE_FOTMOB[league]
    st.markdown(
        f'<div class="lg-title"><img src="{LEAGUE_LOGO.format(fid)}">'
        f'<div><div class="nm">{LEAGUE_LABELS.get(league, league)}</div>'
        f'<div class="co">{sub}</div></div></div>', unsafe_allow_html=True)

@st.cache_data(ttl=6 * 3600)
def _goal_rows(league, filt):
    return goal_stats.team_stats(league, filt=filt)

@st.cache_data(ttl=6 * 3600)
def _goal_timing(league, filt):
    return goal_stats.team_timing(league, filt=filt)

def render_goals(league):
    _lg_header(league, f"MATCH GOALS STATS · σεζον {goal_stats.SEASON_DEFAULT}")
    st.caption("Υπολογισμενο απο ολα τα αποτελεσματα 2025/26 · ανανεωση μολις τελειωσει η 1η αγωνιστικη 26/27.")
    n = len(_goal_rows(league, 'total'))
    h = n * 40 + 130
    tabs = st.tabs(["Total", "Home", "Away", "Last 8", "Timing (15′)"])
    for tab, filt in zip(tabs[:4], ['total', 'home', 'away', 'last8']):
        with tab:
            st.components.v1.html(goal_view.table_html(_goal_rows(league, filt), filt), height=h, scrolling=True)
    with tabs[4]:
        st.caption("Κατανομη γκολ ανα 15λεπτο — ΥΠΕΡ (αριστερα) & ΚΑΤΑ (δεξια). Χρωμα = ενταση.")
        sub = st.tabs(["Συνολο", "Εντος", "Εκτος"])
        for stab, filt in zip(sub, ['total', 'home', 'away']):
            with stab:
                st.components.v1.html(goal_view.timing_html(_goal_timing(league, filt)), height=h, scrolling=True)

@st.cache_data(ttl=6 * 3600)
def _trend_teams(league):
    return trendline.team_matches(league)

def render_trend(league):
    _lg_header(league, "ROLLING TRENDLINE · σεζον " + trendline.SEASON_DEFAULT)
    st.caption("Rolling average xGF/xGA με linear trend · raw npxG (non-penalty, ασυμπιεστο).")
    data = _trend_teams(league)
    names = sorted(data.keys())
    c1, c2, c3 = st.columns([2, 2, 1.2])
    with c1:
        team = st.selectbox("Ομαδα", names, key=f"tr_team_{league}")
    with c2:
        others = ['— Καμια —'] + [n for n in names if n != team]
        cmp = st.selectbox("Συγκριση με", others, key=f"tr_cmp_{league}")
    with c3:
        window = st.radio("Rolling window", [5, 10], index=1, horizontal=True, key=f"tr_w_{league}")
    s1 = trendline.series(data[team], window)
    s2 = trendline.series(data[cmp], window) if cmp != '— Καμια —' else None
    st.markdown(trend_view.cards_html(team, s1, cmp, s2, window), unsafe_allow_html=True)
    st.plotly_chart(trend_view.make_fig(s1, team, s2, cmp, window),
                    use_container_width=True, config={'displayModeBar': False})

def render_scatter(league):
    _lg_header(league, "SCATTER · npxG For vs Against · σεζον " + trendline.SEASON_DEFAULT)
    st.caption("Μεσο npxG υπερ (x) vs κατα (y). **Πανω-δεξια = καλυτερο** (πολλα υπερ, λιγα κατα).")
    data = _trend_teams(league)
    maxg = scatter_view.max_games(data)
    c1, _ = st.columns([2, 3])
    with c1:
        lo, hi = st.slider("Αγωνιστικες (απο — εως)", 1, maxg, (1, maxg), key=f"sc_gw_{league}")
    st.caption(f"Αγωνιστικες {lo}–{hi}" + ("  ·  full season" if (lo, hi) == (1, maxg) else ""))
    st.plotly_chart(scatter_view.scatter_fig(data, lo, hi),
                    use_container_width=True, config={'displayModeBar': False})

@st.cache_data(ttl=6 * 3600)
def _xgstats(league):
    return xgstats.compute(league)

def render_xgstats(league):
    _lg_header(league, "XG STATS · σεζον " + xgstats.SEASON_DEFAULT + " · all averages per game")
    data = _xgstats(league)
    VLABEL = [('total', 'Overall'), ('home', 'Home'), ('away', 'Away')]
    view = st.tabs(["xG Rankings", "xGD Table"])
    with view[0]:
        subs = st.tabs([l for _, l in VLABEL])
        for stab, (venue, _) in zip(subs, VLABEL):
            with stab:
                rows = data[venue]
                st.components.v1.html(xgstats_view.rankings_html(rows),
                                      height=min(len(rows) * 37 + 60, 1300), scrolling=True)
    with view[1]:
        subs = st.tabs([l for _, l in VLABEL])
        for stab, (venue, _) in zip(subs, VLABEL):
            with stab:
                rows = data[venue]
                c1, c2 = st.columns([5, 6])
                with c1:
                    st.components.v1.html(xgstats_view.xgd_table_html(rows),
                                          height=min(len(rows) * 36 + 70, 1300), scrolling=True)
                with c2:
                    st.plotly_chart(xgstats_view.xgd_bar_fig(rows), use_container_width=True,
                                    config={'displayModeBar': False})

_LATEST_F = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'value_picks_latest.json')

def render_value(league):
    st.markdown('<div class="lg-title"><div><div class="nm" style="color:#34d17a">💰 VALUE PICKS</div>'
                '<div class="co">LIVE · THE ODDS API · PINNACLE/MATCHBOOK AH</div></div></div>', unsafe_allow_html=True)
    st.caption("Μοντελο +handicap value bets · edge ≥10% · odds 1.70–2.10 · staking ⅛ Kelly + cap 20% · "
               "auto-scan (Task Scheduler) → Telegram για νεα/αλλαγες · το dashboard δειχνει το τελευταιο scan.")
    if not os.path.exists(_LATEST_F):
        st.info("Δεν υπαρχει ακομα scan. Τρεξε `python scan_value.py` (η το Task Scheduler) για να γεμισει.")
        return
    with open(_LATEST_F, encoding='utf-8') as fh:
        res = json.load(fh)
    picks = res.get('picks', [])
    if os.environ.get('TOA_KEY'):   # τοπικα μονο· στο cloud σκαναρει το GitHub Actions
        top = st.columns([3, 1])
        top[0].caption(f"🕒 Τελευταιο scan: **{res.get('scanned_at', '—')}**  ·  ratings σεζον {res.get('ratings_season', '')}")
        if top[1].button("🔄 Scan τωρα"):
            try:
                import scan_value
                scan_value.scan(notify_tg=False)
                st.rerun()
            except Exception as e:
                st.error(f"Σφαλμα scan: {e}")
    else:
        st.caption(f"🕒 Τελευταιο scan: **{res.get('scanned_at', '—')}**  ·  ratings σεζον {res.get('ratings_season', '')} "
                   "· auto-scan καθε 30' (GitHub Actions)")
    if not picks:
        st.info("Καμια value pick στο τελευταιο scan (αναμενομενο προεποχικα / χαμηλη ρευστοτητα Betfair).")
        return
    gr, sc, cap = res.get('gross', 0), res.get('scale', 1), res.get('cap', 0.2)
    m1, m2, m3 = st.columns(3)
    m1.metric("Picks", len(picks))
    m2.metric("Συνολικη εκθεση", f"{min(gr, cap)*100:.0f}%", help="⅛ Kelly, μετα το cap 20%")
    m3.metric("Καλυτερο edge", f"{max(p['edge'] for p in picks)*100:.0f}%")
    if res.get('n_new') or res.get('n_changed'):
        st.caption(f"τελευταιο scan: {res.get('n_new', 0)} νεα · {res.get('n_changed', 0)} με αλλαγη odds")
    if sc < 1.0:
        st.caption(f"⚙ Συνολικη εκθεση {gr*100:.0f}% > cap {cap*100:.0f}% → μειωση ολων ×{sc:.2f}.")
    # ---- φιλτρο ανα πρωταθλημα (default: ολα μαζι) ----
    order = list(build_data.LEAGUE_FOTMOB)
    lgs_present = sorted({p['lg'] for p in picks}, key=lambda x: order.index(x) if x in order else 99)
    sel_lg = st.selectbox("Πρωταθλημα", ['Όλα'] + lgs_present,
                          format_func=lambda x: 'Όλα τα πρωταθληματα' if x == 'Όλα' else value_view.LEAGUE_LABELS.get(x, x),
                          key='vp_league')
    shown = picks if sel_lg == 'Όλα' else [p for p in picks if p['lg'] == sel_lg]
    st.components.v1.html(value_view.picks_html(shown), height=min(len(shown) * 150 + 40, 4000), scrolling=True)

RENDER = {'projections': render_projections, 'goals': render_goals, 'trend': render_trend,
          'scatter': render_scatter, 'xgstats': render_xgstats, 'value': render_value}
if page in RENDER:
    RENDER[page](league)
else:
    st.markdown(f"### {PAGE_LABEL.get(page, page)}")
    st.info("🚧 Υπο κατασκευη — θα το φτιαξουμε στη συνεχεια.")

st.caption(f"Ratings warm-start: σεζον {build_data.RATINGS_SEASON_DEFAULT} · ανανεωση δεδομενων καθε 6h · "
           "fair odds απο το μοντελο (οχι αγορας).")
