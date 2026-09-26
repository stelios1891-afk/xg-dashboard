# -*- coding: utf-8 -*-
"""intl_callups_tm.py — ΤΡΕΧΟΥΣΕΣ ΚΛΗΣΕΙΣ εθνικων απο TRANSFERMARKT (21/9 v2).

Αντικαθιστα το FotMob-based intl_squad_now (η σελιδα squad του FotMob αποδειχθηκε
ΜΠΑΓΙΑΤΙΚΗ — εδειχνε προηγουμενη αποστολη). Επικυρωση πηγης στην Ελλαδα:
το TM kader περιεχει Καρετσα+Ιωαννιδη (κληθεντες) που ελειπαν απο FotMob. ✓

v2 (21/9): το quick-search εδινε ΛΑΘΟΣ ομαδες (France->Inter, England->vereinslos).
 1) Χαρτης ομαδων απο intl_tm_rank_map.json (211 εθνικες, χτισμενος απο τις σελιδες
    TM FIFA World Ranking — αυθεντικος, επιβεβαιωμενα France/England/Greece σωστα).
 2) Παικτες ΜΟΝΟ απο τις hauptlink γραμμες του squad table (οχι ολα τα λινκ σελιδας).
 3) Πυλη μεγεθους 18-35: υποπτη κληση -> ΚΑΜΙΑ σημαια (καλυτερα τιποτα παρα λαθος).
 4) MISSING: παικτες που ξεκινησαν >=2 φορες στη διετια (intl_squads + intl_player_values
    ονοματα) και ΔΕΝ ταιριαζουν με ΚΑΝΕΝΑ ονομα της κλησης (token match, χωρις τονους).
V_call = 80ο εκατοστημοριο των top-11 TM αξιων της κλησης.
Εξοδος: intl_vcall_tm.json {fotmob_tid: {nm, tm, v_call_m, n_sq, missing: [...]}}
"""
import sys, os, json, re, time, random, datetime, unicodedata
import urllib.request
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
       'Accept-Language': 'en-US,en;q=0.9', 'Accept': 'text/html,application/xhtml+xml'}

def get(u):
    time.sleep(0.7 + random.random() * 0.6)
    return urllib.request.urlopen(urllib.request.Request(u, headers=HDR), timeout=30).read().decode('utf-8', 'replace')

_SPECIAL = str.maketrans({'ı': 'i', 'İ': 'I', 'ø': 'o', 'Ø': 'O', 'ł': 'l', 'Ł': 'L', 'đ': 'd', 'Đ': 'D', 'ß': 'ss', 'æ': 'ae', 'Æ': 'Ae', 'ð': 'd', 'þ': 'th', 'ə': 'a', 'Ə': 'A', "'": '', '’': ''})   # 25/9: γραμματα που το NFD δεν «καθαριζει» (Yıldız → yldz)

def norm(s):
    s = unicodedata.normalize('NFD', str(s).translate(_SPECIAL))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return set(w for w in re.findall(r'[a-z]{3,}', s))

import difflib


def name_in_call(name, called_names):
    """25/9: ειναι ο παικτης (ονομα FotMob) στη λιστα κλησης TM; ≥2 κοινα tokens, ή ιδιο επωνυμο, ή σχεδον ιδια γραφη επωνυμου
    (Khaybulaev/Khaybulayev, Qurbanli/Qurbanly) — αλλιως «O'Brien», «Andrews/Andreas Tetteh» εβγαιναν ψευδως εκτος κλησης."""
    t = norm(name)
    if not t:
        return False
    toks = [w for w in re.findall(r'[a-z]{3,}', unicodedata.normalize('NFD', str(name).translate(_SPECIAL)).encode('ascii', 'ignore').decode().lower())]
    sur = toks[-1] if toks else max(t, key=len)
    for c in called_names:
        ct = norm(c); cw = c.split()
        if len(t & ct) >= 2 or max(t, key=len) in ct or sur in ct:
            return True
        if cw and difflib.SequenceMatcher(None, sur, cw[-1]).ratio() >= 0.85 and (len(sur) >= 5 or (toks and toks[0][:1] == cw[0][:1])):
            return True
        if cw and len(toks) >= 2 and toks[0] == cw[0] and difflib.SequenceMatcher(None, sur, cw[-1]).ratio() >= 0.70:   # ιδιο μικρο + παρομοιο επωνυμο (Sadıxov/Sadykhov)
            return True
    return False


# ονομα intl -> ονομα TM rank-map (211 εθνικες απο FIFA ranking σελιδες TM)
RANKMAP = json.load(open('intl_tm_rank_map.json', encoding='utf-8'))
TM_ALIAS = {'Bosnia and Herzegovina': 'Bosnia-Herzegovina', 'Ireland': 'Republic of Ireland'}

def tm_team(nm):
    key = TM_ALIAS.get(nm, nm)
    hit = RANKMAP.get(key)
    if hit is None:
        for k in RANKMAP:                      # χαλαρο ταιριασμα χωρις τονους
            if norm(k) == norm(key):
                hit = RANKMAP[k]; break
    return tuple(hit) if hit else None

if os.path.exists('intl_player_values.json'):
    PV = json.load(open('intl_player_values.json', encoding='utf-8'))
else:   # 25/9: στο GitHub Actions το συμπαγες αρχειο (pid -> [ονομα, τελευταια αξια SciSports])
    PV = {k: {'name': v[0], 'mv_now': v[1]} for k, v in json.load(open('intl_player_values_now.json', encoding='utf-8')).items()}
SQH = json.load(open('intl_squads.json', encoding='utf-8'))
try:      # 26/9: προηγουμενη κληση — για το «ποτε μπηκε καθε παικτης στη λιστα» (seen)
    PREV = json.load(open('intl_vcall_tm.json', encoding='utf-8'))
except Exception:
    PREV = {}
P = pd.read_csv('intl_projections.csv')
M = pd.read_csv('intl_matches.csv', dtype={'mid': str})

NAME2TID = {}
for r in M.itertuples():
    NAME2TID[str(r.hn)] = int(r.hid); NAME2TID[str(r.an)] = int(r.aid)
TIDS = {}
for r in P.itertuples():
    for nm in (r.home, r.away):
        t = NAME2TID.get(str(nm))
        if t:
            TIDS[t] = str(nm)

# played-730d: pid -> starts, με ονοματα απο PV
cut = (datetime.datetime.now() - datetime.timedelta(days=730)).strftime('%Y-%m-%d')
mid2date = dict(zip(M.mid, M.date.astype(str)))
mid2teams = {r.mid: (r.hid, r.aid) for r in M.itertuples()}
played = {}
for mid, rec in SQH.items():
    if str(mid2date.get(str(mid), ''))[:10] < cut:
        continue
    tms = mid2teams.get(str(mid))
    if not tms:
        continue
    for sk, tid in (('h', tms[0]), ('a', tms[1])):
        for pid in ((rec.get(sk) or {}).get('p') or {}):
            played.setdefault(int(tid), {})
            played[int(tid)][int(pid)] = played[int(tid)].get(int(pid), 0) + 1

WIN0 = (datetime.datetime.now() - datetime.timedelta(days=10)).strftime('%Y-%m-%d')   # αρχη τρεχοντος διεθνους παραθυρου (προσεγγιση)
# 25/9 (αποφαση Στελιου: στο μοντελο η αξια της ΚΛΗΣΗΣ): ολοι οι παικτες που εχουν ντυθει ποτε με καθε εθνικη (FotMob) → υποψηφιοι για αντιστοιχιση ονοματων TM
team_pids = {}
for mid, rec in SQH.items():
    tms = mid2teams.get(str(mid)); d_ = str(mid2date.get(str(mid), ''))[:10]
    if not tms:
        continue
    for sk, tid in (('h', tms[0]), ('a', tms[1])):
        for pid in ((rec.get(sk) or {}).get('p') or {}):
            dd = team_pids.setdefault(int(tid), {})
            dd[int(pid)] = max(dd.get(int(pid), ''), d_)


def _toks(name):
    return re.findall(r'[a-z]{2,}', unicodedata.normalize('NFD', str(name).translate(_SPECIAL)).encode('ascii', 'ignore').decode().lower())


def match_score(fm_name, tm_name):
    """ποσο σιγουρα ο παικτης FotMob ειναι ο παικτης TM: 3 ιδια ονοματα · 2 ιδιο επωνυμο+αρχικο · 1.5 παρομοιο επωνυμο+αρχικο · 1 μονο επωνυμο · 0.
    (Αυστηροτερο απο το name_in_call ωστε αδερφια/συνονοματοι — π.χ. Jurrien/Quinten Timber — να μη μπερδευονται.)"""
    f, t = _toks(fm_name), _toks(tm_name)
    if not f or not t:
        return 0
    if len(set(f) & set(t)) >= 2 or f == t:
        return 3
    same_init = f[0][:1] == t[0][:1]
    if f[-1] == t[-1] or f[-1] in t:
        return 2 if same_init else 1
    if same_init and difflib.SequenceMatcher(None, f[-1], t[-1]).ratio() >= 0.85:
        return 1.5
    return 0


def latest_val(pid):
    rec = PV.get(str(pid))
    if not rec:
        return None
    if rec.get('mv_now'):
        return float(rec['mv_now'])
    h = rec.get('hist') or []
    try:
        return float(sorted(h, key=lambda x: x[0])[-1][1]) if h else None
    except Exception:
        return None

def parse_val(s):
    s = s.replace(chr(8364), '').strip().lower()
    try:
        if s.endswith('m'):
            return float(s[:-1])
        if s.endswith('k'):
            return float(s[:-1]) / 1000
    except ValueError:
        pass
    return None

# hauptlink = η στηλη ονοματος του squad table (δοκιμασμενο: δινει καθαρες γραμμες)
RX_PLAYER = re.compile(r'class="hauptlink"[^>]*>\s*<a[^>]*href="/([a-z0-9\-]+)/profil/spieler/(\d+)"')
RX_VAL = re.compile(r'>(€[\d.,]+[mk])</a>')

# 25/9 ΧΕΙΡΟΚΙΝΗΤΕΣ ΑΠΟΥΣΙΕΣ (Στελιος): intl_absences_manual.json {ομαδα: {"out": [ονοματα], "until": "YYYY-MM-DD", "note": ...}} —
# οσοι δηλωθουν βγαινουν ΑΜΕΣΩΣ απο την κληση (αξια κλησης + σημαια «λειπει»), χωρις να περιμενουμε το Transfermarkt. Ληγει μονο του (until).
MANUAL = {}
if os.path.exists('intl_absences_manual.json'):
    _today = datetime.date.today().isoformat()
    MANUAL = {k: v for k, v in json.load(open('intl_absences_manual.json', encoding='utf-8')).items()
              if not k.startswith('_') and str(v.get('until', '9999')) >= _today}
OUT = {}
skipped = []
for tid, nm in sorted(TIDS.items(), key=lambda kv: kv[1]):
    t = tm_team(nm)
    if not t:
        print(f'  {nm}: ΔΕΝ βρεθηκε στον rank-map')
        skipped.append(nm)
        continue
    slug, vid = t
    try:
        h = get(f'https://www.transfermarkt.com/{slug}/kader/verein/{vid}')
    except Exception as e:
        print(f'  {nm}: kader ΣΦΑΛΜΑ {type(e).__name__}')
        skipped.append(nm)
        continue
    rows = RX_PLAYER.findall(h)
    called_names = sorted({sl.replace('-', ' ') for sl, _ in rows})
    if not (18 <= len(called_names) <= 35):
        print(f'  {nm:22s} ΥΠΟΠΤΟ μεγεθος κλησης {len(called_names)} ({slug}/{vid}) — ΠΑΡΑΛΕΙΠΕΤΑΙ, καμια σημαια')
        skipped.append(nm)
        continue
    vals = sorted([v for v in (parse_val(x) for x in RX_VAL.findall(h)) if v], reverse=True)
    v_call = float(np.percentile(vals[:11], 80)) if len(vals) >= 8 else None
    # 25/9: ανα παικτη (γραμμη πινακα): ονομα TM + αξια TM → αντιστοιχιση με παικτη FotMob της ιδιας εθνικης → αξια SciSports (ιδια κλιμακα με το τεστ)
    players = []; used = set(); cands = team_pids.get(tid, {})
    for row in re.split(r'<tr class="(?:odd|even)"', h)[1:]:
        pm = RX_PLAYER.search(row)
        if not pm:
            continue
        tm_nm = pm.group(1).replace('-', ' '); vm = re.search(r'(€[\d.,]+[mk])', row); tmv = parse_val(vm.group(1)) if vm else None
        best = max(((match_score((PV.get(str(p)) or {}).get('name', ''), tm_nm), d_, p) for p, d_ in cands.items() if p not in used), default=(0, '', None))
        pid = best[2] if best[0] >= 1.5 else None      # μονο επωνυμο με αλλο μικρο ονομα = ΑΛΛΟΣ παικτης (Georgiy ≠ Hovhannes Harutyunyan) → αξια TM × K
        if pid is not None:
            used.add(pid)
        players.append(dict(tm=tm_nm, pid=pid, sci=(latest_val(pid) if pid is not None else None), tm_m=tmv))
    manual_out = []
    for mo in (MANUAL.get(nm) or {}).get('out', []):
        hit = [pl_ for pl_ in players if match_score(mo, pl_['tm']) >= 1.5]
        for pl_ in hit:
            players.remove(pl_); manual_out.append(dict(nm=mo, tm=pl_['tm'], mv=round((pl_['sci'] or (pl_['tm_m'] or 0) * 1e6 * 0.69) / 1e6, 1)))
        called_names = [c for c in called_names if not any(match_score(mo, c) >= 1.5 for _ in [0])]
        if not hit:
            manual_out.append(dict(nm=mo, tm=None, mv=None))       # δεν ηταν στη λιστα TM — ηδη εκτος
    if manual_out:
        print(f"  {nm}: χειροκινητα εκτος {[m['nm'] for m in manual_out]}", flush=True)
    # 26/9 (Στελιος, Σεσκο): ΑΝΤΙΣΤΡΟΦΟΣ ελεγχος του Brobbey — βασικος (top-11 αξιας της κλησης) που ΕΙΝΑΙ στη λιστα TM αλλα ΔΕΝ ηταν στην
    # αποστολη FotMob (11 + παγκος) του ΤΕΛΕΥΤΑΙΟΥ ματς της ομαδας σε αυτο το παραθυρο → μετραει ως απων στα επομενα. Μονο αν ηταν στη λιστα
    # TM ΠΡΙΝ απο εκεινο το ματς (seen) — ενας αντικαταστατης που κληθηκε μετα δεν «λειπει». Αν ξαναντυθει σε νεοτερο ματς, ξαναμετραει.
    now_s = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')
    pv_ = PREV.get(str(tid)) or {}
    prev_seen = pv_.get('seen') or {n_: pv_.get('asof') for n_ in (pv_.get('called') or [])}
    seen = {c: (prev_seen.get(c) or now_s) for c in called_names}
    last_m = max(((str(mid2date.get(str(m_), ''))[:16], m_, sk_) for m_, rec_ in SQH.items()
                  if str(mid2date.get(str(m_), ''))[:10] >= WIN0 and mid2teams.get(str(m_))
                  for sk_, t_ in zip(('h', 'a'), mid2teams[str(m_)]) if int(t_) == tid and len((rec_.get(sk_) or {}).get('p') or {}) >= 16),
                 default=None)
    squad_out = []
    SQUAD_RULE = bool(json.load(open('intl_vcall_config.json', encoding='utf-8')).get('squad_rule', False))
    if last_m:
        dressed_last = {int(p_) for p_ in ((SQH[last_m[1]].get(last_m[2]) or {}).get('p') or {})}
        _v = lambda pl_: pl_['sci'] or (pl_['tm_m'] or 0) * 1e6 * 0.69
        top11 = sorted([pl_ for pl_ in players if _v(pl_)], key=lambda pl_: -_v(pl_))[:11]
        for pl_ in top11:
            if pl_['pid'] is None or int(pl_['pid']) in dressed_last:
                continue
            if (seen.get(pl_['tm']) or now_s) >= last_m[0]:
                continue           # μπηκε στη λιστα μετα το ματς (αντικαταστατης) — δεν λειπει
            if SQUAD_RULE:          # 26/9: ΑΠΕΝΕΡΓΟ (Στελιος) — μονο ενδειξη, η αξια κλησης ΔΕΝ αλλαζει
                players.remove(pl_)
                called_names = [c for c in called_names if c != pl_['tm']]
            squad_out.append(dict(nm=(PV.get(str(pl_['pid'])) or {}).get('name') or pl_['tm'], tm=pl_['tm'], pid=pl_['pid'],
                                  mv=round(_v(pl_) / 1e6, 1), match=last_m[0]))
        if squad_out:
            print(f"  {nm}: στην κληση TM αλλα ΕΚΤΟΣ αποστολης {last_m[0][:10]}{' (αφαιρεθηκαν)' if SQUAD_RULE else ' (μονο ενδειξη)'}: {[m_['nm'] for m_ in squad_out]}", flush=True)
    called_tok = [norm(c) for c in called_names]
    miss = []
    pl = played.get(tid) or {}
    topv = max((latest_val(p) or 0) for p in pl) if pl else 0
    # 25/9 (διορθωση Στελιου): η λιστα TM ΕΙΝΑΙ η αποστολη που θα παιξει — οποιος ντυθηκε σε προηγουμενο ματς του παραθυρου αλλα ΔΕΝ ειναι πια
    # στη λιστα, ΑΠΟΧΩΡΗΣΕ (π.χ. Brobbey τραυματιστηκε 24/9) → μετραει ως απουσια, με σημειωση left=True.
    dressed_now = {int(p_) for m_, rec_ in SQH.items() if str(mid2date.get(str(m_), ''))[:10] >= WIN0 and mid2teams.get(str(m_))
                   for sk_, t_ in zip(('h', 'a'), mid2teams[str(m_)]) if int(t_) == tid for p_ in ((rec_.get(sk_) or {}).get('p') or {})}
    for pid, nst in pl.items():
        if nst < 2:
            continue
        v = latest_val(pid)
        if not v or not topv or v < 0.30 * topv:
            continue
        pnm = (PV.get(str(pid)) or {}).get('name', '')
        ptok = norm(pnm)
        if not ptok:
            continue
        # ταιριαζει με καποιον της κλησης; (>=2 κοινα tokens Ή ολο το επωνυμο)
        matched = int(pid) in used or name_in_call(pnm, called_names)      # 25/9: αντιστοιχισμενος παικτης Ή ταιριασμα ονοματος
        if not matched:
            miss.append(dict(pid=pid, nm=pnm, mv=round(v / 1e6, 1), starts=nst, left=int(pid) in dressed_now))
    miss.sort(key=lambda x: -x['mv'])
    miss = [dict(pid=None, nm=m_['nm'], mv=m_['mv'] or 0, starts=None, left=False, manual=True) for m_ in manual_out] + miss      # 25/9: χειροκινητες πρωτες
    miss = [dict(pid=m_['pid'], nm=m_['nm'], mv=m_['mv'], starts=None, left=False, squad=True, info=not SQUAD_RULE) for m_ in squad_out
            if not any(match_score(mo_, m_['tm']) >= 1.5 for mo_ in (MANUAL.get(nm) or {}).get('out', []))] + miss   # 26/9: εκτος αποστολης
    OUT[tid] = dict(nm=nm, tm=f'{slug}/{vid}', v_call_m=v_call, n_sq=len(called_names), missing=miss[:4], dressed_now=len(dressed_now), manual_out=manual_out,
                    called=called_names, asof=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M'), players=players,
                    seen={c: seen.get(c, now_s) for c in called_names} | {m_['tm']: seen.get(m_['tm'], now_s) for m_ in squad_out},
                    squad_out=squad_out)   # 25/9: ολη η λιστα (για επαληθευση)
    print(f'  {nm:22s} κληση {len(called_names):2d} · V_call {v_call if v_call else chr(8212)}M · λειπουν: '
          + (', '.join(f"{m['nm']}({m['mv']}M)" for m in miss[:3]) if miss else chr(8212)), flush=True)

# 25/9: V_call ΣΤΗΝ ΚΛΙΜΑΚΑ ΤΟΥ ΜΟΝΤΕΛΟΥ = αθροισμα 11 μεγαλυτερων αξιων SciSports της κλησης. Παικτης χωρις αντιστοιχιση (πρωτη κληση)
# → αξια TM × K, K = διαμεσος (SciSports / TM) στους αντιστοιχισμενους ολων των ομαδων.
_ratios = [pl['sci'] / (pl['tm_m'] * 1e6) for o in OUT.values() for pl in o['players'] if pl['sci'] and pl['tm_m']]
K_TM = float(np.median(_ratios)) if len(_ratios) >= 50 else 1.0
for o in OUT.values():
    vs = []
    for pl in o['players']:
        pl['v'] = pl['sci'] if pl['sci'] else (pl['tm_m'] * 1e6 * K_TM if pl['tm_m'] else None)
        if pl['v']:
            vs.append(pl['v'])
    vs.sort(reverse=True)
    o['v_call_sci'] = float(sum(vs[:11])) if len(vs) >= 14 else None
    o['n_mapped'] = sum(1 for pl in o['players'] if pl['pid'] is not None); o['k_tm'] = K_TM
print(f'K (SciSports/TM) = {K_TM:.3f} απο {len(_ratios)} αντιστοιχισμενους · αντιστοιχιση: '
      f"{sum(o['n_mapped'] for o in OUT.values())}/{sum(len(o['players']) for o in OUT.values())} παικτες")
if len(OUT) < 0.8 * len(TIDS):     # 25/9: μπλοκαρισμα/σφαλματα TM → ΔΕΝ σβηνεται η προηγουμενη κληση
    print(f'ΣΦΑΛΜΑ: μονο {len(OUT)}/{len(TIDS)} ομαδες απο TM — το intl_vcall_tm.json ΜΕΝΕΙ οπως ηταν'); sys.exit(1)
json.dump(OUT, open('intl_vcall_tm.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(f'ΟΚ {len(OUT)}/{len(TIDS)} ομαδες -> intl_vcall_tm.json' + (f' · ΕΚΤΟΣ: {skipped}' if skipped else ''))
