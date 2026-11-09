// Probelauf der Skizze ohne Browser: node skizzen/probelauf.js [datei.html]
// Ersatz-DOM mit wenigen Stellen, das Skript der Skizze läuft in einer eigenen Umgebung (vm).
// Geprüft wird über die gezeichneten HTML-Texte: jede Ansicht zeichnet ohne Fehler, die Bedienelemente der
// Testaufgaben sind da, Rot nur bei "wartet". Dazu die Dichte je Ansicht (sofort sichtbare Bedienelemente).
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const datei = process.argv[2] || path.join(__dirname, 'gespraech.html');
const html = fs.readFileSync(datei, 'utf8');
const skript = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>'));
const css = html.slice(html.indexOf('<style>') + 7, html.indexOf('</style>'));

let fehler = 0;
const fehlt = (text) => { fehler += 1; console.log('FEHLER  ' + text); };
const ok = (bed, text) => { if (!bed) fehlt(text); };

// ---------- Ersatz-DOM ----------
const hoerer = {};
const knoten = {};
const element = (id) => {
  if (!knoten[id]) {
    knoten[id] = { id, innerHTML: '', value: '', files: [], checked: false, textContent: '', dataset: {},
      addEventListener(t, f) { (hoerer[id + ':' + t] = hoerer[id + ':' + t] || []).push(f); },
      focus() {}, select() {}, blur() {}, scrollIntoView() {}, toggleAttribute() {}, setAttribute() {}, removeAttribute() {},
      querySelector() { return null; }, querySelectorAll() { return []; }, closest() { return null; },
      get lastElementChild() { return null; }, classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } } };
  }
  return knoten[id];
};
// Elemente, die im gezeichneten HTML stehen, gibt es; andere nicht (wie im Browser).
const gezeichnet = () => element('wurzel').innerHTML + element('schicht').innerHTML;
const document = {
  querySelector(sel) {
    if (sel.startsWith('#')) {
      const id = sel.slice(1);
      if (['wurzel', 'schicht', 'zuruecksetzen'].includes(id)) return element(id);
      return gezeichnet().includes('id="' + id + '"') ? element(id) : null;
    }
    return null;
  },
  querySelectorAll() { return []; },
  getElementById(id) { return this.querySelector('#' + id); },
  addEventListener(t, f) { (hoerer['doc:' + t] = hoerer['doc:' + t] || []).push(f); },
  get activeElement() { return null; },
  documentElement: { setAttribute() {}, removeAttribute() {}, dataset: {} },
  body: { classList: { add() {}, remove() {}, toggle() {} } }
};
let zeitgeber = [];
const umgebung = {
  document, console, Math, Date, String, Number, Array, Object, JSON, RegExp, Error, Promise,
  location: { hash: '' },
  window: null,
  navigator: { clipboard: { writeText: () => Promise.resolve() } },
  setTimeout: (f) => { zeitgeber.push(f); return zeitgeber.length; },
  clearTimeout: () => {},
  requestAnimationFrame: (f) => { zeitgeber.push(f); return 0; },
  matchMedia: () => ({ matches: false, addEventListener() {} }),
  getComputedStyle: () => ({}),
  FileReader: function () {},
  localStorage: { getItem() { return null; }, setItem() {} }
};
umgebung.window = {
  addEventListener(t, f) { (hoerer['win:' + t] = hoerer['win:' + t] || []).push(f); },
  scrollTo() {}, getSelection: () => ({ removeAllRanges() {}, addRange() {} }),
  matchMedia: umgebung.matchMedia, innerWidth: 1400
};
vm.createContext(umgebung);
try { vm.runInContext(skript, umgebung, { filename: 'gespraech.html' }); } catch (e) { fehlt('Skript startet nicht: ' + e.stack); process.exit(1); }

const ausloesen = (schluessel, e) => (hoerer[schluessel] || []).forEach((f) => f(e));
const zeitAblaufen = () => { while (zeitgeber.length) { const z = zeitgeber; zeitgeber = []; z.forEach((f) => f()); } };
const wurzel = () => element('wurzel').innerHTML;
const schicht = () => element('schicht').innerHTML;

function seite(h) { umgebung.location.hash = '#' + h; ausloesen('win:hashchange', {}); }

// Klick auf ein Element mit data-akt; prüft vorher, dass es gezeichnet ist (außer pruefen: false).
function klick(akt, attr, opt) {
  attr = attr || {}; opt = opt || {};
  const muster = 'data-akt="' + akt + '"';
  const alles = gezeichnet();
  if (opt.pruefen !== false) {
    const passt = alles.split('<').some((tag) => tag.includes(muster) && Object.keys(attr).every((k) => tag.includes('data-' + k + '="' + attr[k] + '"')));
    if (!passt) { fehlt('nicht gezeichnet: ' + muster + ' ' + JSON.stringify(attr) + (opt.wo ? ' (' + opt.wo + ')' : '')); return false; }
  }
  const el = { dataset: Object.assign({ akt }, attr), textContent: opt.text || '', focus() {}, getAttribute: (n) => (attr[n.replace('data-', '')] || null),
    closest(sel) { if (sel === '[data-akt]') return el; return { querySelector: () => ({ textContent: opt.bt || 'Beispieltext' }), dataset: {} }; } };
  const ziel = { closest: (sel) => (sel === '[data-akt]' ? el : el.closest(sel)) };
  try { ausloesen('doc:click', { target: ziel, preventDefault() {}, stopPropagation() {} }); } catch (e) { fehlt('Klick ' + akt + ' wirft: ' + e.message); }
  return true;
}
function taste(key, extra) {
  try { ausloesen('doc:keydown', Object.assign({ key, target: { id: '' }, preventDefault() {} }, extra || {})); } catch (e) { fehlt('Taste ' + key + ' wirft: ' + e.message); }
}

// ---------- Dichte ----------
// Sofort sichtbar = gezeichnet und nicht nur beim Hover (Klasse "hover-akt"); Zugeklapptes zeichnet die Skizze nicht.
function dichte(h) {
  const tags = h.match(/<(button|a|input|select|textarea)\b[^>]*>/g) || [];
  const bedien = tags.filter((t) => !/class="[^"]*\bhover-akt\b/.test(t) && !/type="file"/.test(t)).length;
  const zeilen = (h.match(/class="[^"]*\bzeile\b/g) || []).length;
  const woerter = h.replace(/<svg[\s\S]*?<\/svg>/g, ' ').replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
  return { bedien, zeilen, woerter };
}
const messung = [];
function messen(name) {
  const d = dichte(wurzel() + schicht());
  messung.push([name, d.bedien, d.zeilen, d.woerter]);
}

// Rot nur an "wartet": jeder Inhalt eines roten Elements enthält "wartet", ist eine Zahl oder leer (Punkt).
function rotPruefen(name) {
  const re = /<(\w+)[^>]*class="[^"]*\b(rot|punkt-rot)\b[^"]*"[^>]*>([^<]*)/g;
  let m;
  while ((m = re.exec(wurzel() + schicht()))) {
    const inhalt = m[3].trim();
    if (!/wartet/.test(inhalt) && !/^\d+$/.test(inhalt) && inhalt !== '') fehlt('Rot ohne "wartet" in ' + name + ': ' + inhalt);
  }
}

function ansicht(name, tun) {
  try { tun(); } catch (e) { fehlt(name + ' wirft: ' + e.message); return; }
  zeitAblaufen();
  ok(wurzel().length > 500, name + ': Ansicht leer');
  ok(!/undefined|NaN|\[object /.test(wurzel() + schicht()), name + ': undefined/NaN im HTML');
  rotPruefen(name);
  messen(name);
}

// ---------- Ansichten ----------
const EBENEN = ['e8', 'strafe', 'helfen', 's1', 's2', 's3', 's4', 's5', 'k11', 'k12', 'wahnsinn', 'ohne'];
const GESPRAECHE = ['g1', 'g2', 'g3', 'g4', 'g5', 'g6', 'g7', 'g8', 'g9'];

ansicht('Lückenliste', () => seite('luecken'));
ok(wurzel().includes('Stimmt das? Was fehlt?'), 'Lückenliste: Frage fehlt');
ansicht('Heute', () => { seite('skizze'); klick('heute'); });
EBENEN.forEach((k) => ansicht('Ebene ' + k, () => { klick('ebene', { ziel: k }, { pruefen: false }); }));
GESPRAECHE.forEach((g) => ansicht('Gespräch ' + g, () => { klick('oeffnen', { id: g }, { pruefen: false }); }));

// Überlagerungen
ansicht('Überlagerung Auftrag', () => { klick('oeffnen', { id: 'g1' }, { pruefen: false }); klick('auftrag', {}, { pruefen: false }); });
ok(schicht().includes('data-akt="abschicken"'), 'Auftrag: Abschicken fehlt');
ansicht('Überlagerung Ablegen', () => { taste('Escape'); klick('ebene', { ziel: 'strafe' }, { pruefen: false }); klick('ablegen', {}, { pruefen: false }); });
ok(schicht().includes('Datei ablegen'), 'Ablegen: Fenster fehlt');
ansicht('Überlagerung Verschieben', () => { taste('Escape'); klick('oeffnen', { id: 'g1' }, { pruefen: false }); klick('verschieben', {}, { pruefen: false }); });
ok(schicht().includes('verschiebenok'), 'Verschieben: Fenster fehlt');
taste('Escape');

// ---------- Testaufgaben (STATUS.md) ----------
function zuruecksetzen() { ausloesen('zuruecksetzen:click', {}); seite('skizze'); }
// Menüs oder Zugeklapptes, die der Probelauf öffnen darf, bevor er ein Element sucht. Jede Ansicht kann sie anbieten.
function oeffneFallsNoetig(akt) {
  if (gezeichnet().includes('data-akt="' + akt + '"')) return;
  ['menue', 'anhangmenue', 'darunter', 'optionen'].forEach((m) => {
    if (!gezeichnet().includes('data-akt="' + akt + '"') && gezeichnet().includes('data-akt="' + m + '"')) {
      const t = (gezeichnet().match(new RegExp('<[^>]*data-akt="' + m + '"[^>]*>', 'g')) || []);
      t.forEach((tag) => {
        if (gezeichnet().includes('data-akt="' + akt + '"')) return;
        const attr = {}; (tag.match(/data-(\w+)="([^"]*)"/g) || []).forEach((a) => { const [, k, v] = a.match(/data-(\w+)="([^"]*)"/); if (k !== 'akt') attr[k] = v; });
        klick(m, attr, { pruefen: false });
      });
    }
  });
}

// 1 Reihenfrage übernehmen
zuruecksetzen(); klick('heute');
ok(wurzel().includes('Weiter im Gespräch'), 'T1: "Weiter im Gespräch" fehlt auf Heute');
klick('oeffnen', { id: 'g1' }, { wo: 'T1 Heute' });
const neueFrage = 'Muss jemand ins Gefängnis, auch wenn danach niemand mehr in Gefahr ist?';
klick('reihenfrage', {}, { bt: neueFrage, wo: 'T1 Gespräch' });
ok(wurzel().includes(neueFrage), 'T1: neue Reihenfrage nicht sichtbar');
ok(wurzel().includes('data-akt="rueckgaengig"'), 'T1: Rückgängig fehlt');

// 2 Foto anhängen und senden
ok(wurzel().includes('Foto oder Datei'), 'T2: "Foto oder Datei" fehlt');
oeffneFallsNoetig('beispielfoto');
klick('beispielfoto', {}, { wo: 'T2' });
ok(wurzel().includes('Planung.heic'), 'T2: Anhang nicht sichtbar');
ausloesen('doc:submit', { target: { id: 'eingabe' }, preventDefault() {} }); zeitAblaufen();
ok((wurzel().match(/Planung\.heic/g) || []).length >= 2, 'T2: Foto nicht gesendet');

// 3 Kopieren
ok(wurzel().includes('data-akt="kopieren"'), 'T3: Kopieren fehlt');

// 4 Gespräch an Stunde 3 finden, neues an Stunde 4
zuruecksetzen(); klick('ebene', { ziel: 'strafe' }, { pruefen: false });
ok(wurzel().includes('data-ziel="s3"'), 'T4: Stunde 3 nicht erreichbar von der Reihe');
klick('ebene', { ziel: 's3' }, { pruefen: false });
ok(wurzel().includes('data-id="g2"'), 'T4: Gespräch "Einstieg mit einem Fall" nicht an Stunde 3');
klick('ebene', { ziel: 's4' }, { pruefen: false });
klick('neu', {}, { wo: 'T4 Stunde 4' });
ok(/Stunde 4/.test(wurzel()) && wurzel().includes('Neues Gespräch'), 'T4: neues Gespräch nicht an Stunde 4');

// 5 Daraus Auftrag machen
zuruecksetzen(); klick('oeffnen', { id: 'g1' }, { pruefen: false });
oeffneFallsNoetig('auftrag');
klick('auftrag', {}, { wo: 'T5' });
ok(schicht().includes('Reihenentwurf für die Reihe Straftheorien'), 'T5: Auftragstext nicht vorbelegt');
klick('abschicken', {}, { wo: 'T5' });

// 6 Datei an Kurs 12, Gespräche ohne Ort
zuruecksetzen(); klick('ebene', { ziel: 'k12' }, { pruefen: false });
oeffneFallsNoetig('ablegen');
klick('ablegen', {}, { wo: 'T6 Kurs 12' });
klick('beispieldatei', {}, { wo: 'T6' });
ok(schicht().includes('Bewertungskriterien.pdf'), 'T6: Beispieldatei nicht gewählt');
klick('ablegenok', {}, { wo: 'T6' });
ok(wurzel().includes('Bewertungskriterien.pdf'), 'T6: Datei nicht an Kurs 12 sichtbar');
ok(wurzel().includes('data-ziel="ohne"'), 'T6: "Gespräche ohne Ort" fehlt im Baum');

// ---------- Seitenleiste: auf- und zuklappen ----------
const baumHtml = () => { const h = wurzel(); const a = h.indexOf('<nav class="baum"'); return a < 0 ? '' : h.slice(a, h.indexOf('</nav>', a)); };
zuruecksetzen(); klick('ebene', { ziel: 'k11' }, { pruefen: false });
if (skript.includes("'klappen'")) {
  ok(baumHtml().includes('data-ziel="helfen"'), 'Baum: Reihen der Klasse 8 nicht sichtbar');
  ok(!baumHtml().includes('data-ziel="s1"'), 'Baum: Stunden einer fremden Reihe offen');
  klick('klappen', { ziel: 'e8' }, { wo: 'Baum' });
  ok(!baumHtml().includes('data-ziel="helfen"'), 'Baum: Klasse 8 klappt nicht zu');
  ok(baumHtml().includes('punkt-rot'), 'Baum: roter Punkt fehlt an zugeklappter Klasse mit Wartendem');
  klick('klappen', { ziel: 'e8' }, { wo: 'Baum' });
  klick('klappen', { ziel: 'strafe' }, { wo: 'Baum' });
  ok(baumHtml().includes('data-ziel="s1"'), 'Baum: Reihe klappt nicht auf');
  klick('archiv', {}, { wo: 'Baum' });
  ok(baumHtml().includes('Klasse 7'), 'Baum: Archiv klappt nicht auf');
}

// ---------- Vorschau (ab Schritt 5) ----------
if (skript.includes("'vorschau'")) {
  zuruecksetzen(); klick('ebene', { ziel: 'strafe' }, { pruefen: false });
  const ids = [];
  const re = /data-akt="vorschau"[^>]*data-m="(\d+)"|data-m="(\d+)"[^>]*data-akt="vorschau"/g; let m;
  while ((m = re.exec(wurzel()))) ids.push(m[1] || m[2]);
  ok(ids.length >= 3, 'Vorschau: Material der Reihe nicht klickbar');
  // jedes Material jeder Ebene
  let n = 0;
  EBENEN.forEach((k) => {
    klick('ebene', { ziel: k }, { pruefen: false });
    oeffneFallsNoetig('vorschau');
    const re2 = /<[^>]*data-akt="vorschau"[^>]*>/g; let t;
    const tags = wurzel().match(re2) || [];
    tags.forEach((tag) => {
      const mm = tag.match(/data-m="(\d+)"/); if (!mm) return;
      klick('vorschau', { m: mm[1] }, { pruefen: false }); zeitAblaufen();
      const h = wurzel() + schicht();
      ok(/Seite 1 von \d+/.test(h), 'Vorschau ' + k + '/' + mm[1] + ': Seitenzahl fehlt');
      ok(/<svg/.test(h), 'Vorschau ' + k + '/' + mm[1] + ': Seitenbild fehlt');
      if (h.includes('data-akt="seite"')) { klick('seite', { r: '1' }, { pruefen: false }); ok(/Seite 2 von/.test(wurzel() + schicht()) || /von 1\b/.test(h), 'Vorschau blättert nicht'); }
      klick('gross', {}, { pruefen: false }); ok(/Seite \d+ von/.test(schicht()), 'Groß ansehen fehlt');
      taste('ArrowRight'); taste('Escape');
      klick('vorschauzu', {}, { pruefen: false });
      n += 1; void t;
    });
  });
  ok(n >= 10, 'Vorschau: zu wenige Materialien geöffnet (' + n + ')');
  // Messung einer offenen Vorschau
  ansicht('Vorschau offen', () => { klick('ebene', { ziel: 'strafe' }, { pruefen: false }); klick('vorschau', { m: '1' }, { pruefen: false }); });
  console.log('ok      Vorschau: ' + n + ' Materialien geöffnet');
}

// ---------- Ausgabe ----------
const groessen = Array.from(new Set((css.match(/font-size:\s*(\d+)px/g) || []).map((s) => Number(s.match(/\d+/)[0])))).sort((a, b) => a - b);
console.log('Dichte (sofort sichtbare Bedienelemente / Zeilen / Wörter):');
messung.forEach(([n, b, z, w]) => console.log('  ' + n.padEnd(26) + String(b).padStart(4) + String(z).padStart(5) + String(w).padStart(6)));
console.log('Schriftgrößen im CSS (' + groessen.length + '): ' + groessen.join(', '));
console.log('Linien 3px: ' + (css.match(/3px solid/g) || []).length + ', uppercase: ' + (css.match(/uppercase/g) || []).length);
if (fehler) { console.log('PROBELAUF: ' + fehler + ' Fehler'); process.exit(1); }
console.log('PROBELAUF GRÜN');
