# -*- coding: utf-8 -*-
"""flashscore_bk_players.py — ΠΑΙΚΤΕΣ ΑΝΑ ΜΑΤΣ (λεπτα) για τα 6 εγχωρια μπασκετ, 2020-21 → σημερα (7/10/2026, Στελιος «ξεκινα το κατεβασμα»).
Σκοπος: απουσιες πριν το ματς (βασικοι που ελειπαν) → τεστ «ποσο αλλαζει το αποτελεσμα / το τιμολογει η αγορα;».
Πηγη: Flashscore feed df_psn_1_{matchId} (ιδια headers με df_st_1_)· ids απο fs_bk_games.json (ACB/LBA/GBL/TBL/LNB/BBL).
Μορφη feed: εγγραφες '~', πεδια '¬', κλειδι/τιμη '÷'· PJ ονομα · PK /player/{slug}/{id}/ · PN ομαδα (3 γραμματα) · PC = PTS|REB|AST|MIN|… (MIN «mm:ss» ή ακεραιος).
Καθε παικτης εμφανιζεται 2 φορες → κραταμε μια. Μονο οσοι επαιξαν (οχι DNP). Ευγενικα (~0.7″ + δικτυο), συνεχιζει απο εκει που εμεινε.
Εξοδος: fs_bk_players.jsonl {id, lg, y, ts, hid, aid, hs, as_, p: [[player_id, ονομα, ομαδα3, λεπτα, ποντοι]]}
Χρηση: python flashscore_bk_players.py [ACB LBA ...]"""
import sys, os, json, time, re
import requests
sys.stdout.reconfigure(encoding='utf-8')
LGS = [a for a in sys.argv[1:] if not a.startswith('-')] or ['ACB', 'LBA', 'GBL', 'TBL', 'LNB', 'BBL']
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'}
HF = {**H, 'x-fsign': 'SW9D1eZo', 'Referer': 'https://www.flashscore.com/'}
FULL = '--full' in sys.argv     # 8/10: ΟΛΑ τα στατιστικα (PC) ανα παικτη → fs_bk_players_full.jsonl (για «αξια» παικτη: +/-, ριμπ., ασιστ)
OUT = 'fs_bk_players_full.jsonl' if FULL else 'fs_bk_players.jsonl'
S = requests.Session()

def get(u):
    for a in range(5):
        try:
            time.sleep(0.7)
            r = S.get(u, headers=HF, timeout=30)
            if r.status_code == 200: return r.text
            if r.status_code in (403, 429): print(f'  {r.status_code} → παυση', flush=True); time.sleep(60 * (a + 1))
            elif r.status_code == 404: return ''
        except Exception as e:
            print('  σφαλμα', e, flush=True); time.sleep(10 * (a + 1))
    return None

def mins(x):
    x = (x or '').strip()
    if ':' in x:
        m, s = x.split(':', 1)
        try: return round(int(m) + int(s) / 60, 2)
        except ValueError: return None
    try: return float(x)
    except ValueError: return None

def parse(txt):
    out, seen = [], set()
    for rec in txt.split('~'):
        f = {}
        for kv in rec.split('¬'):
            if '÷' in kv: k, v = kv.split('÷', 1); f[k] = v
        if not ('PJ' in f and 'PC' in f): continue
        m = re.search(r'/player/[^/]+/([^/]+)/', f.get('PK', ''))
        pid = m.group(1) if m else f['PJ']
        if pid in seen: continue
        seen.add(pid); pc = f['PC'].split('|')
        try: pts = float(pc[0])
        except (ValueError, IndexError): pts = None
        out.append([pid, f['PJ'], f.get('PN', ''), mins(pc[3]) if len(pc) > 3 else None, pts] + ([f['PC']] if FULL else []))
    return out

def main():
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    done = set()
    if os.path.exists(OUT):
        for ln in open(OUT, encoding='utf-8'):
            try: done.add(json.loads(ln)['id'])
            except Exception: pass
    todo = []
    for key, L in FG.items():
        lg, y = key.split('_')
        if lg not in LGS: continue
        for e in L:
            if e.get('id') and e['id'] not in done and e.get('hs') not in (None, ''):
                todo.append((lg, int(y), e))
    print(f'παικτες: {len(done)} ηδη · {len(todo)} να κατεβουν', flush=True)
    t0 = time.time(); n_ok = n_empty = 0
    with open(OUT, 'a', encoding='utf-8') as fh:
        for k, (lg, y, e) in enumerate(todo):
            txt = get(f'https://global.flashscore.ninja/2/x/feed/df_psn_1_{e["id"]}')
            if txt is None: continue
            p = parse(txt)
            if p: n_ok += 1
            else: n_empty += 1
            fh.write(json.dumps(dict(id=e['id'], lg=lg, y=y, ts=e.get('ts'), hid=e.get('hid'), aid=e.get('aid'), hs=e.get('hs'), as_=e.get('as_'), p=p), ensure_ascii=False) + '\n')
            if k % 100 == 0:
                fh.flush(); el = time.time() - t0
                print(f'  {k + 1}/{len(todo)} · με παικτες {n_ok} · κενα {n_empty} · {el / 60:.0f}′ · υπολοιπο ~{el / (k + 1) * (len(todo) - k - 1) / 60:.0f}′', flush=True)
    print(f'ΤΕΛΟΣ: με παικτες {n_ok} · κενα {n_empty}', flush=True)

if __name__ == '__main__':
    main()
