# -*- coding: utf-8 -*-
"""sofa_receiver.py — 20/10/2026: τοπικος «παραληπτης» για το κατεβασμα ιστορικου απουσιων Sofascore.
Το Sofascore μπλοκαρει τα απλα αιτηματα (403) αλλα απαντα μεσα απο τον browser· ο browser κανει τα fetch και στελνει εδω
(POST JSON, 127.0.0.1:8765) καθε παρτιδα → προσθηκη στο αρχειο του πεδιου 'file' (μονο sofa_*.jsonl). Τρεχει μονο οσο κατεβαζουμε."""
import json, os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))


class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Private-Network', 'true')

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0)); body = json.loads(self.rfile.read(n) or b'{}')
        f = os.path.basename(str(body.get('file', 'sofa_hist.jsonl')))
        ok = f.startswith('sofa_') and f.endswith('.jsonl')
        if ok:
            with open(os.path.join(ROOT, f), 'a', encoding='utf-8') as out:
                for r in body.get('rows', []):
                    out.write(json.dumps(r, ensure_ascii=False) + '\n')
        self.send_response(200 if ok else 400); self._cors(); self.end_headers()
        self.wfile.write(json.dumps({'ok': ok, 'n': len(body.get('rows', []))}).encode())

    def do_GET(self):
        self.send_response(200); self._cors(); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
        self.wfile.write('<!doctype html><title>sofa receiver</title><p>ok</p>'.encode())

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    print('sofa_receiver 127.0.0.1:8765', flush=True)
    HTTPServer(('127.0.0.1', 8765), H).serve_forever()
