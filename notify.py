"""
notify.py  -  Αποστολη ειδοποιησεων στο Telegram (value picks + μπλοκαρισματα δικλειδας).

Διαβαζει 2 environment variables (ΟΧΙ απο αρχειο):
    TELEGRAM_TOKEN    - το token του bot (απο τον @BotFather)
    TELEGRAM_CHAT_ID  - το chat id σου (το βρισκουμε αυτοματα με `python notify.py chat-id`)

Χρηση:
    python notify.py chat-id     # βρισκει & δειχνει το chat id (αφου στειλεις μηνυμα στο bot)
    python notify.py test        # στελνει ενα δοκιμαστικο μηνυμα
Και ως module:  import notify;  notify.send("κειμενο")
"""
import os, sys, requests

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

API = 'https://api.telegram.org/bot{token}/{method}'


def _token():
    t = os.environ.get('TELEGRAM_TOKEN')
    if not t:
        print("ΣΦΑΛΜΑ: λειπει το TELEGRAM_TOKEN (environment variable).")
    return t


def send(text, silent=False):
    """Στελνει κειμενο στο chat σου. Επιστρεφει True/False. Δεν σκαει αν δεν ειναι ρυθμισμενο."""
    token = os.environ.get('TELEGRAM_TOKEN')
    chat = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat:
        print("  (Telegram δεν ειναι ρυθμισμενο — λειπει TELEGRAM_TOKEN ή TELEGRAM_CHAT_ID· παραλειπω.)")
        return False
    # Telegram οριο 4096 χαρακτηρες — σπαμε σε κομματια αν χρειαστει
    ok = True
    for chunk in _split(text, 3900):
        try:
            r = requests.post(API.format(token=token, method='sendMessage'),
                              json={'chat_id': chat, 'text': chunk,
                                    'disable_web_page_preview': True,
                                    'disable_notification': silent}, timeout=20)
            if r.status_code != 200:
                print(f"  Telegram σφαλμα HTTP {r.status_code}: {r.text[:200]}")
                ok = False
        except Exception as e:
            print(f"  Telegram εξαιρεση: {e}")
            ok = False
    return ok


def _split(text, n):
    lines = text.split('\n')
    buf, out = '', []
    for ln in lines:
        if len(buf) + len(ln) + 1 > n:
            out.append(buf); buf = ln
        else:
            buf = ln if not buf else buf + '\n' + ln
    if buf:
        out.append(buf)
    return out or ['']


def get_chat_id():
    token = _token()
    if not token:
        return
    r = requests.get(API.format(token=token, method='getUpdates'), timeout=20).json()
    if not r.get('ok'):
        print(f"Σφαλμα: {r}"); return
    updates = r.get('result', [])
    if not updates:
        print("Δεν βρεθηκαν μηνυματα. Ανοιξε το bot στο Telegram και στειλε του ενα μηνυμα (π.χ. 'γεια'),")
        print("μετα ξανατρεξε:  python notify.py chat-id")
        return
    seen = {}
    for u in updates:
        msg = u.get('message') or u.get('channel_post') or {}
        ch = msg.get('chat', {})
        if ch.get('id'):
            seen[ch['id']] = ch.get('first_name') or ch.get('title') or ch.get('username') or ''
    print("Βρεθηκαν chat id:")
    for cid, name in seen.items():
        print(f"   CHAT_ID = {cid}   ({name})")
    print("\nΒαλε το σωστο ως TELEGRAM_CHAT_ID.")


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'chat-id':
        get_chat_id()
    elif cmd == 'test':
        ok = send("✅ Betting Model — δοκιμαστικο μηνυμα. Αν το βλεπεις, το Telegram δουλευει!")
        print("Εσταλη." if ok else "Δεν εσταλη (δες πανω).")
    else:
        print(__doc__)
