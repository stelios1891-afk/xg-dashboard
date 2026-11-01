"""goal_view.py — HTML render του Goal Stats πινακα (heatmap) + goal timing."""
import html as _h
import goal_stats as gs

TLOGO = 'https://images.fotmob.com/image_resources/logo/teamlogo/{}.png'

TABLE_CSS = """
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#0a0f1e;font-family:'DM Sans','Segoe UI',sans-serif;color:#e8edf8;padding:2px;}
.scroll{overflow-x:auto;}
table{border-collapse:collapse;table-layout:fixed;width:100%;min-width:940px;font-size:12px;}
th{padding:9px 6px;text-align:right;color:#8fa3c8;font-size:10px;font-weight:600;letter-spacing:.4px;
   text-transform:uppercase;border-bottom:1px solid #1e2d47;position:sticky;top:0;background:#0a0f1e;
   white-space:nowrap;cursor:pointer;user-select:none;height:38px;vertical-align:middle;}
th:hover{color:#cdd8ee;}
th.tm,td.tm{text-align:left;}
th .ar{color:#4b7cf3;}
td{padding:0;text-align:right;border-bottom:1px solid #121b30;font-family:'JetBrains Mono',monospace;height:38px;vertical-align:middle;}
td .cell{padding:6px 8px;border-radius:5px;margin:2px;}
tr:hover td{background:#0f1830;}
.tm{display:flex;align-items:center;gap:9px;padding:0 8px;white-space:nowrap;overflow:hidden;}
.tm img{width:20px;height:20px;object-fit:contain;flex:none;}
.tm .nm{font-family:'DM Sans',sans-serif;font-size:12.5px;font-weight:500;overflow:hidden;text-overflow:ellipsis;}
.gp{color:#8fa3c8;}
.avg .cell{font-weight:700;}
.lgavg td{border-top:2px solid #1e2d47;color:#cdd8ee;font-weight:700;background:#0d1426;}
.lgavg .tm{font-family:'DM Sans',sans-serif;font-size:12px;color:#8fa3c8;text-transform:uppercase;letter-spacing:1px;}
/* timing */
.tim{border-collapse:collapse;table-layout:fixed;width:100%;min-width:900px;font-size:12px;}
.tim th{padding:7px 6px;color:#8fa3c8;font-size:10px;text-transform:uppercase;border-bottom:1px solid #1e2d47;text-align:center;height:34px;}
.tim td{padding:0;text-align:center;border-bottom:1px solid #121b30;font-family:'JetBrains Mono',monospace;height:36px;vertical-align:middle;}
.tim .tm{text-align:left;}
.tim .grp{color:#7ea2ff;font-size:9px;letter-spacing:1px;}
.tim td .cell{padding:6px 4px;border-radius:5px;margin:2px;}
</style>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
"""

_SORT_JS = """
<script>
(function(){
 var tbl=document.getElementById('gs'); if(!tbl) return;
 var tb=tbl.tBodies[0], avg=tb.querySelector('tr.lgavg'), ths=tbl.tHead.rows[0].cells, cur={i:-1,d:-1};
 function sort(i,d){
  var rows=[].slice.call(tb.querySelectorAll('tr:not(.lgavg)'));
  rows.sort(function(a,b){
   var x=a.cells[i].getAttribute('data-v'), y=b.cells[i].getAttribute('data-v');
   if(i===0) return d*String(x).localeCompare(String(y));
   return d*((parseFloat(x)||0)-(parseFloat(y)||0));
  });
  rows.forEach(function(r){tb.insertBefore(r, avg);});
  for(var k=0;k<ths.length;k++){var s=ths[k].querySelector('.ar'); if(s) s.textContent='';}
  var s2=ths[i].querySelector('.ar'); if(s2) s2.textContent=d<0?' ↓':' ↑';
  cur={i:i,d:d};
 }
 for(var k=0;k<ths.length;k++){(function(k){ths[k].onclick=function(){sort(k, cur.i===k?-cur.d:(k===0?1:-1));};})(k);}
 sort(2,-1);
})();
</script>
"""

def _heat(t):
    """t in [0,1] -> hsla κοκκινο(0)→αμπερ→πρασινο(1), διακριτικο σε σκουρο φοντο."""
    t = max(0.0, min(1.0, t))
    hue = t * 135          # 0=red .. 135=green
    return f"hsla({hue:.0f},62%,32%,0.60)"

def _col_heat(vals):
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    return lo, rng

def table_html(rows, filt):
    if not rows:
        return TABLE_CSS + '<p style="color:#8fa3c8;padding:12px">Δεν υπαρχουν δεδομενα.</p>'
    la = gs.league_avg(rows)
    heat = {k: _col_heat([r[k] for r in rows]) for k, _ in gs.COLS if k != 'gp'}

    def cell(r, k):
        v = r[k]
        if k == 'gp':
            return f'<td class="gp" data-v="{v:.0f}"><div class="cell">{v:.0f}</div></td>'
        lo, rng = heat[k]
        bg = _heat((v - lo) / rng)
        txt = f'{v:.2f}' if k == 'avg' else f'{v:.0f}%'
        cls = 'avg' if k == 'avg' else ''
        return f'<td class="{cls}" data-v="{v:.4f}"><div class="cell" style="background:{bg}">{txt}</div></td>'

    # σταθερα column widths (ιδια ευθυγραμμιση σε ολα τα tabs)
    cols = '<col style="width:210px">' + '<col style="width:46px">' + \
           ''.join('<col style="width:60px">' for _ in gs.COLS[1:])
    head = '<th class="tm">Team<span class="ar"></span></th>' + ''.join(
        f'<th>{lbl}<span class="ar"></span></th>' for k, lbl in gs.COLS)
    body = ''
    for r in rows:
        logo = f'<img src="{TLOGO.format(r["tid"])}" onerror="this.style.visibility=\'hidden\'">' if r.get('tid') else ''
        tm = (f'<td class="tm" data-v="{_h.escape(r["team"])}">'
              f'<div class="tm">{logo}<span class="nm">{_h.escape(r["team"])}</span></div></td>')
        body += '<tr>' + tm + ''.join(cell(r, k) for k, _ in gs.COLS) + '</tr>'
    lav = '<tr class="lgavg"><td class="tm"><div class="tm">League average</div></td>'
    for k, _ in gs.COLS:
        v = la[k]
        txt = f'{v:.1f}' if k == 'gp' else (f'{v:.2f}' if k == 'avg' else f'{v:.0f}%')
        lav += f'<td><div class="cell">{txt}</div></td>'
    lav += '</tr>'
    return (TABLE_CSS + '<div class="scroll"><table id="gs"><colgroup>' + cols + '</colgroup>'
            f'<thead><tr>{head}</tr></thead><tbody>{body}{lav}</tbody></table></div>' + _SORT_JS)

def timing_html(rows):
    if not rows:
        return TABLE_CSS + '<p style="color:#8fa3c8;padding:12px">Δεν υπαρχουν δεδομενα.</p>'
    # heatmap ανα ομαδα-set: χρωματισε % κατανομης (0..max% ολων)
    allpct = [x for r in rows for x in r['gf_pct'] + r['ga_pct']]
    hi = max(allpct) or 1.0

    def cells(pcts, counts):
        out = ''
        for p, c in zip(pcts, counts):
            out += f'<td><div class="cell" style="background:{_heat(p/hi)}">{c}</div></td>'
        return out

    head = ('<th class="tm">Team</th>'
            + ''.join(f'<th>{b}</th>' for b in gs.BUCKETS)
            + '<th>Σ</th>' + ''.join(f'<th>{b}</th>' for b in gs.BUCKETS) + '<th>Σ</th>')
    grp = ('<th class="tm"></th><th class="grp" colspan="6">GOALS FOR (ανα λεπτο)</th><th></th>'
           '<th class="grp" colspan="6">GOALS AGAINST</th><th></th>')
    body = ''
    for r in rows:
        logo = f'<img src="{TLOGO.format(r["tid"])}" onerror="this.style.visibility=\'hidden\'">' if r.get('tid') else ''
        tm = f'<td class="tm"><div class="tm">{logo}<span class="nm">{_h.escape(r["team"])}</span></div></td>'
        body += ('<tr>' + tm + cells(r['gf_pct'], r['gf']) + f'<td class="gp"><div class="cell">{r["tot_f"]}</div></td>'
                 + cells(r['ga_pct'], r['ga']) + f'<td class="gp"><div class="cell">{r["tot_a"]}</div></td></tr>')
    return TABLE_CSS + (f'<div class="scroll"><table class="tim"><thead><tr>{grp}</tr><tr>{head}</tr></thead>'
                        f'<tbody>{body}</tbody></table></div>')
