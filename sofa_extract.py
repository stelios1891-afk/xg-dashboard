# -*- coding: utf-8 -*-
"""sofa_extract.py — 20/10/2026: παιρνει τα «SOFADUMP» που επιστρεφει ο browser (σωζονται ως αρχεια tool-results) και τα γραφει
στο sofa_hist.jsonl (ενα ματς ανα γραμμη, χωρις διπλα). Χρηση: python sofa_extract.py <αρχειο> [<αρχειο> ...]
Πεδια ανα ματς: e (Sofascore id), ts (σεντρα unix), lg, s (σεζον), rnd, h/a [id, ονομα], sc [σκορ 90′], conf (επισημες ενδεκαδες),
mh/ma = ΑΠΟΝΤΕΣ [id, ονομα, type missing|doubtful, reason (1 τραυμ. · 3 τιμωρ. · 0 αλλο), θεση, αναμενομενη επιστροφη], sh/sa = βασικοι [id, ονομα]."""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'sofa_hist.jsonl')


def payload(path):
    raw = open(path, encoding='utf-8').read()
    try:
        arr = json.loads(raw); texts = [x.get('text', '') for x in arr] if isinstance(arr, list) else [raw]
    except Exception:
        texts = [raw]
    for t in texts:
        t = t.strip()
        if t.startswith('"'):
            try: t = json.JSONDecoder().raw_decode(t)[0]          # το κειμενο = JSON string + «(captured at origin ...)»
            except Exception: pass
        i = t.find('SOFADUMP')
        if i >= 0:
            body = t[i + len('SOFADUMP'):]
            j = body.rfind('}')
            yield json.loads(body[:j + 1])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    have = set()
    if os.path.exists(OUT):
        for l in open(OUT, encoding='utf-8'):
            try: have.add(json.loads(l)['e'])
            except Exception: pass
    n_new = 0
    with open(OUT, 'a', encoding='utf-8') as out:
        for p in sys.argv[1:]:
            for d in payload(p):
                for key, rows in d.items():
                    k = 0
                    for r in rows:
                        if r['e'] in have: continue
                        have.add(r['e']); out.write(json.dumps(r, ensure_ascii=False) + '\n'); k += 1; n_new += 1
                    print(f'{key}: {len(rows)} ματς · νεα {k}')
    print(f'ΣΥΝΟΛΟ νεα {n_new} · στο αρχειο {len(have)}')
