// FightOdds: αργή συλλογή μέσα από τον browser. Κάθε σελίδα φορτώνει κανονικά σε iframe, μία τη φορά, με παύση.
// foRun("event", ["/mma-events/{id}/{slug}/fights", ...]) -> σύνδεσμοι αγώνων (localStorage e:{path})
// foRun("fight", ["/fights/{slug-id}/odds", ...])        -> ημερομηνία + 8 τιμές Pinnacle (localStorage f:{path})
// foDump(i, size) -> κομμάτι i από gzip+base64 όλων των αποθηκευμένων, για ανάγνωση έξω από τον browser.
// Σταματά μόνο του σε έλεγχο bot ή σε 8 συνεχόμενες κενές σελίδες: δεν παρακάμπτει τίποτα.
window.foRun = async function (kind, keys, gap = 3000) {
  const S = window.foS = { kind, total: keys.length, pages: 0, skip: 0, ok: 0, empty: 0, run: 0, stop: false, state: "τρέχει", err: null, last: null };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const tag = kind === "event" ? "e:" : "f:";
  const read = d => {
    if (kind === "event") {
      const f = [...new Set([...d.querySelectorAll("a")].map(a => a.getAttribute("href")))].filter(h => h && /^\/fights\/.+\/odds$/.test(h));
      return f.length ? f : null;
    }
    const r = [...d.querySelectorAll("tr")].map(x => [...x.children].map(c => c.innerText.trim())).filter(c => c.length >= 9);
    if (r.length < 3) return null;
    const p = r.find(c => c[0] === "Pinnacle");
    return [(d.body.innerText.match(/\d{4}-\d{2}-\d{2}/) || [""])[0], p ? p.slice(1, 9) : null];
  };
  try {
    const fr = document.createElement("iframe");
    fr.style.cssText = "position:fixed;left:0;top:0;width:1200px;height:800px;opacity:.01;pointer-events:none";
    document.body.appendChild(fr);
    for (const k of keys) {
      if (S.stop) break;
      if (localStorage.getItem(tag + k) !== null) { S.skip++; continue; }
      fr.src = k; S.pages++; S.last = k;
      let v = null; const t0 = Date.now();
      while (!v && !S.stop && Date.now() - t0 < 15000) {
        await sleep(500);
        const d = fr.contentDocument;
        if (!d || !d.body || d.location.pathname !== k) continue;
        if (/verify you are human|just a moment|checking your browser|access denied/i.test((d.body.innerText || "") + d.title)) {
          S.state = "ΣΤΑΜΑΤΗΣΕ: έλεγχος bot στο " + k; S.stop = true; break;
        }
        v = read(d);
      }
      if (S.stop) break;
      localStorage.setItem(tag + k, JSON.stringify(v));
      if (v) { S.ok++; S.run = 0; } else { S.empty++; S.run++; }
      if (S.run >= 8) { S.state = "ΣΤΑΜΑΤΗΣΕ: 8 συνεχόμενες κενές, τελευταία " + k; S.stop = true; break; }
      await sleep(gap);
    }
    if (!S.stop) S.state = "τέλος";
    fr.remove();
  } catch (e) { S.err = String(e); S.state = "ΣΦΑΛΜΑ"; }
  return S;
};
window.foDump = async function (i, size = 20000) {
  if (!window.foB64) {
    const o = {};
    for (let n = 0; n < localStorage.length; n++) { const k = localStorage.key(n); if (/^f:/.test(k)) o[k.slice(2)] = JSON.parse(localStorage.getItem(k)); }
    const gz = new Blob([JSON.stringify(o)]).stream().pipeThrough(new CompressionStream("gzip"));
    const bytes = new Uint8Array(await new Response(gz).arrayBuffer());
    let s = ""; for (let n = 0; n < bytes.length; n += 8192) s += String.fromCharCode(...bytes.subarray(n, n + 8192));
    window.foB64 = btoa(s);
  }
  return "FOCHUNK|" + i + "|" + Math.ceil(window.foB64.length / size) + "|" + window.foB64.slice(i * size, (i + 1) * size);
};
