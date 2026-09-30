"""value_view.py — HTML cards για τα live Value Picks."""
import html as _h
import json as _json
import build_data

TLOGO = 'https://images.fotmob.com/image_resources/logo/teamlogo/{}.png'
LLOGO = 'https://images.fotmob.com/image_resources/logo/leaguelogo/dark/{}.png'
LEAGUE_LABELS = {'Euroleague': 'Euroleague', 'EPL': 'Premier League', 'LaLiga': 'La Liga', 'SerieA': 'Serie A',
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
.tag.np{background:rgba(160,160,160,.14);color:#b9b9b9;border:1px dashed rgba(180,180,180,.45);}
.pc.np{opacity:.72;}
.bet.ov{color:#3ec98f;border-color:#2d6e57;}
.cbtn{margin-left:8px;background:#0f1a30;border:1px solid #2d4470;border-radius:8px;padding:4px 8px;cursor:pointer;font-size:14px;line-height:1;color:#7ea2ff;}
.cbtn:hover,.cbtn.on{background:#182444;border-color:#4b7cf3;}
.calc{display:none;margin-top:10px;padding:9px 11px;background:#0c1426;border:1px solid #1e2d47;border-radius:9px;}
.calc.on{display:block;}
.crow{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:11px;color:#8da0c4;}
.calc select,.calc input{background:#111c33;border:1px solid #2d4470;border-radius:6px;color:#e8edf8;font-family:'JetBrains Mono',monospace;
     font-size:13px;padding:4px 6px;}
.calc input{width:74px;}
.cres{display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;font-family:'JetBrains Mono',monospace;font-size:12.5px;}
.cm{display:flex;flex-direction:column;gap:1px;}
.cm .n{font-size:9px;color:#6b7fa3;text-transform:uppercase;letter-spacing:.5px;}
.cm .e{font-weight:700;}
.cm .q{font-size:10px;color:#6b7fa3;}
.g{color:#34d17a;}.a{color:#f5b731;}.r{color:#f04f5a;}
.csum{margin-top:7px;font-size:11.5px;font-weight:700;}
.cnote{font-size:10px;color:#f5b731;margin-left:8px;font-weight:400;}
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
    if p.get('intl'):
        tags += f'<span class="tag eu" title="συναινεση μοντελων εθνικων">ΕΘΝ. · {_h.escape(p.get("models") or "")}</span>'
        if p.get('late'):
            tags += f'<span class="tag lc">{_h.escape(p["late"])}</span>'
    if p.get('el'):
        tags += '<span class="tag eu">🏀 μπασκετ</span>'
        if p.get('mkt_note') and not p.get('paper_late'):          # 30/9: «αγορα κοντρα» — η τιμη μας ανεβαινε τις 3ω πριν το alert
            short = 'ℹ αγορα κοντρα ' + f"{p.get('drift') or 0:+.1f}π"
            tags += f'<span class="tag lc" title="{_h.escape(p["mkt_note"])}">{_h.escape(short)}</span>'
        if p.get('coach_notes'):             # 1/10: νεος προπονητης (10 ματς μετα την αλλαγη) — μονο ενδειξη
            tags += f'<span class="tag lc" title="{_h.escape(" | ".join(p["coach_notes"]))}">🔄 νεος προπονητης</span>'
        if p.get('travel'):                  # 1/10: ταξιδι 2ου ματς διαβολοβδομαδας (διορθωση μοντελου υπερ γηπεδουχου)
            tags += f'<span class="tag eu" title="{_h.escape(p["travel"].get("note", ""))}">🧳 ταξιδι +{p["travel"].get("adj", 0):g}</span>'
        if p.get('old_agree') is not None:   # 1/10: συνολα αγων 1-10 — συμφωνει και το μοντελο χωρις προετοιμασια; (μονο ενδειξη)
            tags += (f'<span class="tag eu" title="Συνολο χωρις την ταση ποντων των φιλικων: {p.get("total_base")}">'
                     + ('✓ και το παλιο' if p['old_agree'] else '✗ μονο με φιλικα') + '</span>')
    if p.get('role') == 'fav':         # 1/10: φαβορι 15η+ (αγκυρα .7 + σωστα τεταρτα)
        tags += '<span class="tag eu" title="Φαβορι 15η+: αγκυρα αγορας ×0.7 σε ολες τις γραμμες, σωστα τεταρτα, edge ≥10%">⭐ φαβορι</span>'
    if p.get('anchor'):                # 29/9: αγκυρα αγορας στις κοντες γραμμες (15η+)· 1/10 και στα φαβορι (×0.7)
        a = p['anchor']
        tags += (f'<span class="tag eu" title="Αγκυρα αγορας (15η+{", ×" + format(a["w"], "g") + " φαβορι" if a.get("w") else ", κοντη γραμμη"}): διορθωση υπεροχης {a.get("shift", 0):+.2f} γκολ '
                 f'(γηπ {a.get("o_h", 0):+.2f} · φιλ {a.get("o_a", 0):+.2f})">⚓ αγκυρα {a.get("shift", 0):+.2f}</span>')
    if p.get('tag75'):
        tags += '<span class="tag t75">🎯 −0.75</span>'
    if p.get('paper_late'):              # 1/10: EL χαντικαπ τελευταιου 2ωρου = καταγραφη (ιστορικα −9%, 1/5)
        tags += f'<span class="tag np" title="{_h.escape(p.get("mkt_note") or "")}">📝 καταγραφη · δεν παιζεται</span>'
    if p.get('no_play'):
        tags += '<span class="tag np" title="UEL κλειστο 11/9 (b=0.02 στο κλεισιμο) — μονο για παρακολουθηση">👁 ΣΚΙΑ · δεν παιζεται</span>'
    if over:
        bet = _h.escape(p.get('bet') or f"Over {p['hcap']:g}")
    else:
        pick_team = p['home'] if side == 1 else p['away']
        bet = f"{_h.escape(pick_team)} {'+' if p['hcap'] >= 0 else ''}{p['hcap']:g}"
    proj = f"{p['proj_odds']:.2f}" if p.get('proj_odds') else '—'
    stake_k, stake_v = ('Ποντ.', '~¼ μον.') if (p.get('eu') or p.get('intl') or p.get('el')) else \
        ('Ποντ. (καβα)', f"{p['stake_final']*100:.1f}%")
    if p.get('no_play'):
        stake_k, stake_v = 'Ποντ.', '— (σκια)'
    if p.get('paper_late'):
        stake_k, stake_v = 'Ποντ.', '— (καταγραφη)'
    return f"""
<div class="pc {hi} {'np' if (p.get('no_play') or p.get('paper_late')) else ''}">
  <div class="top">
    <div class="lg">{_logo(lid, tpl=LLOGO)}{LEAGUE_LABELS.get(p['lg'], p['lg'])}{tags}</div>
    <div class="when">{_h.escape((p.get('when') or '').replace('T', ' '))}</div>
  </div>
  <div class="mrow">
    <div class="tm {hcls}">{_logo(p.get('home_id'))}{_h.escape(p['home'])}</div>
    <span class="vs">vs</span>
    <div class="tm {acls}">{_logo(p.get('away_id'))}{_h.escape(p['away'])}</div>
    <div class="bet {'ov' if over else ''}">{bet}</div>{_calc_btn(p)}
  </div>
  <div class="stats">
    <div class="st"><span class="k">Projection</span><span class="v">{proj}</span></div>
    <div class="st"><span class="k">Market</span><span class="v">{p['odds']:.2f}</span></div>
    <div class="st"><span class="k">Edge</span><span class="v edge">{p['edge']*100:.0f}%</span></div>
    <div class="st"><span class="k">{stake_k}</span><span class="v stake">{stake_v}</span></div>
  </div>{_calc_panel(p)}
</div>"""

_CID = [0]


def _calc_btn(p):
    """28/9/2026: κουμπι «κομπιουτερακι» (edge στην τιμη που βρισκεις τωρα) — μονο οπου υπαρχουν δεδομενα μοντελου."""
    if not p.get('calc'):
        return ''
    _CID[0] += 1; p['_cid'] = _CID[0]
    return f'<button class="cbtn" title="Κομπιουτερακι: βαλε την τιμη που βρισκεις τωρα → edge ανα μοντελο" onclick="vpToggle({_CID[0]})">🧮</button>'


def _calc_panel(p):
    c = p.get('calc')
    if not c or not p.get('_cid'):
        return ''
    i = p['_cid']
    opts = ''.join(f'<option value="{k}"{" selected" if k == c["def"] else ""}>{_h.escape(L["lab"])}</option>'
                   for k, L in enumerate(c['lines']))
    pr = f"{c['price']:.2f}" if c.get('price') else ''
    return (f'<div class="calc" id="vpc{i}" data-c="{_h.escape(_json.dumps(c, ensure_ascii=False))}">'
            f'<div class="crow">Γραμμη <select onchange="vpCalc({i})">{opts}</select>'
            f'Τιμη που βρισκω <input type="number" step="0.01" min="1.01" value="{pr}" oninput="vpCalc({i})">'
            f'<span style="margin-left:auto">οριο pick {c["thr"]*100:.0f}%</span></div>'
            f'<div class="cres" id="vpr{i}"></div><div class="csum" id="vps{i}"></div></div>')


CALC_JS = """
<script>
function vpToggle(i){var p=document.getElementById('vpc'+i);p.classList.toggle('on');
  var b=p.parentNode.querySelector('.cbtn');if(b)b.classList.toggle('on');if(p.classList.contains('on'))vpCalc(i);}
function vpFmt(x){return (x+0.004).toFixed(2);}
function vpCalc(i){
  var p=document.getElementById('vpc'+i),c=JSON.parse(p.dataset.c),L=c.lines[+p.querySelector('select').value];
  var o=parseFloat(p.querySelector('input').value),out='',ok=0,mins=[],eds=[],T=Math.round(c.thr*100);
  for(var k=0;k<c.models.length;k++){
    var a=L.c[k][0],b=L.c[k][1],mn=a>0?(c.thr-b)/a:null,m0=a>0?-b/a:null;mins.push(mn);
    var e=(o>1)?(a*o+b):null,cls=e===null?'':(e>=c.thr?'g':(e>=0?'a':'r'));
    if(e!==null){eds.push(e);}
    if(e!==null&&e>=c.thr)ok++;
    out+='<div class="cm"><span class="n">'+c.models[k]+'</span><span class="e '+cls+'">'+
      (e===null?'—':((e>=0?'+':'')+(e*100).toFixed(1)+'%'))+(e!==null&&e>=c.thr?' ✓':'')+'</span>'+
      '<span class="q">'+(mn&&mn>1?('για '+T+'%: ≥'+vpFmt(mn)):'')+(m0&&m0>1?(' · 0%: ≥'+vpFmt(m0)):'')+'</span></div>';
  }
  // 28/9: ΣΥΝΟΛΟ = ιδιος κανονας με την καρτα: το ΜΙΚΡΟΤΕΡΟ edge απο τα μοντελα που περνουν το οριο (αν ≥need)·
  // αλλιως το need-οστο καλυτερο (ποσο λειπει για συναινεση)
  if(c.models.length>1&&eds.length>=c.need){
    var pas=eds.filter(function(x){return x>=c.thr;}),srt=eds.slice().sort(function(x,y){return y-x;});
    var tot=pas.length>=c.need?Math.min.apply(null,pas):srt[c.need-1],tc=tot>=c.thr?'g':(tot>=0?'a':'r');
    out='<div class="cm" style="padding-right:14px;border-right:1px solid #1e2d47"><span class="n">Συνολο</span><span class="e '+tc+'" style="font-size:15px">'+
      ((tot>=0?'+':'')+(tot*100).toFixed(1)+'%')+(tot>=c.thr?' ✓':'')+'</span><span class="q">'+
      (pas.length>=c.need?'μικροτερο των '+pas.length+' που συμφωνουν':(c.need+'ο καλυτερο · οχι συναινεση'))+'</span></div>'+out;
  }
  document.getElementById('vpr'+i).innerHTML=out;
  var notes='';
  if(c.rng&&o>1&&(o<c.rng[0]||o>c.rng[1]))notes+='τιμη εκτος '+c.rng[0].toFixed(2)+'–'+c.rng[1].toFixed(2)+' ';
  if(c.minabs&&Math.abs(L.l)<c.minabs)notes+='γραμμη κατω απο ±'+c.minabs+' ';
  var s=mins.filter(function(x){return x&&x>1;}).sort(function(x,y){return x-y;}),need=s.length>=c.need?s[c.need-1]:null;
  var multi=c.models.length>1,pass=ok>=c.need;
  var head=multi?('συναινεση '+ok+'/'+c.models.length+' '+(pass?'✓':'✗')):(pass?'✓ περνα το οριο':'✗ κατω απο το οριο');
  document.getElementById('vps'+i).innerHTML='<span class="'+(pass?'g':'r')+'">'+head+'</span>'+
    (need?'<span style="color:#8da0c4;font-weight:400;margin-left:8px">'+(multi?'συναινεση (≥'+c.need+' μοντελα)':'οριο')+' απο ≥'+vpFmt(need)+'</span>':'')+
    (notes?'<span class="cnote">⚠ '+notes+'</span>':'');
}
</script>"""


def picks_html(picks):
    picks = sorted(picks, key=lambda p: (p.get('when') or '9999'))   # χρονολογικα: νωριτερο πανω, πιο μετα κατω
    return CSS + '<div class="wrap">' + ''.join(pick_card(p) for p in picks) + '</div>' + CALC_JS
