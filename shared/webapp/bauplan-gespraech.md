# Bauplan: echte Web-App nach der Skizze „Gespräch in der Mitte“

Stand 10.11.2026. Jans Okay 10.11.: Umbau ohne Lias Okay ja; lia/chat und agentkit-Test in eigenen Sitzungen ja;
erst Probe in der Test-Instanz, dann umschalten; Wort „Claude“ erstmal okay.
Grundlage: `skizzen/gespraech.html` (Jan 10.11.: „passt erstmal so“), `ui-plan-notion.md`, `../../docs/gespraech-plan.md`.

## 0. Hinweis vorab (Jan entscheidet)
Dieser Bau hebt zwei frühere Festlegungen auf:
- „Kein Bau ohne Lias Okay“ (gespraech-plan 4.3): Lia hat die Skizze noch nicht gesehen.
- „Echte App bleibt Modernist bis nach Lias Test“ (STATUS, Abschnitt Skizze): nach dem Umschalten sieht Lia unter
  lia.meldro.de die ruhige Oberfläche, ohne vorher gefragt zu sein.
Jans Entscheidung vom 10.11. ist: umbauen und echt testen. Ich baue danach, wenn du das hier bestätigst.

## 1. Was neu ist, und wer es baut
Die Web-App ruft Claude nicht selbst. Grund: CLAUDE.md „Agenten rufen Claude nur über agentkit.claude_lauf“, die
Web-App ist kein Agent, und ein claude-Lauf im Web-Prozess (300 MB Grenze, Uvicorn) würde Seiten blockieren. Claude
läuft weiter im Agenten `lia/chat`. Den ändert nach der Regel „ein Chat pro Ordner“ der lia/chat-Chat, nicht ich.

Bedarf an **lia/chat** (eigener Chat, Plan-Schritt 3.1, 3.4, 3.5 aus gespraech-plan):
1. Gespräch als Objekt `data/gespraeche/<id>.json` (Name, Ebene, claude-Sitzung, Einträge, zuletzt).
   Schnittstelle: `gespraech_anlegen(name, ort)`, `gespraeche(ort=None)`, `gespraech(id)`, `umbenennen`,
   `umhaengen(id, ort)`, `loeschen(id)`, `nachricht(id, text, dateien, gruendlich, netz) -> nachricht_id`,
   `antwort_holen(nachricht_id)`. Die alte Spalte „Fragen“ läuft bis zum Umschalten weiter.
2. Ebene: `ort` = `{"ebene": "klasse"|"reihe"|"stunde", "id": <struktur-id>}` oder None (ohne Ort). Heute kennt
   lia/chat nur Reihe und Stunde; Klasse/Kurs ohne Reihe (Kurs 11) ist neu.
3. Verlauf über `claude_lauf.laufen(..., lernsitzung=True)`, dann `sitzung_fortsetzen=<id>`; Sitzung nicht mehr
   nach jedem Lauf löschen, sondern mit dem Gespräch (30 Tage ab letzter Nachricht).
4. Prompt: Länge nach Bedarf, Überschriften und Tabellen, Bausteine als Codeblock ```` ```baustein <art> ````
   (art: reihenfrage, merksatz, arbeitsauftrag, fall, text). Text bis ca. 60.000 Zeichen.
5. Fotos JPG/PNG (bis 5 je Nachricht) über das Werkzeug Read, nur auf den Ordner dieses Gesprächs. Die Pfadgrenze
   prüft vorher der Hauptordner-Chat in agentkit (gespraech-plan 3.2). HEIC: iPhone-Safari wandelt beim Hochladen
   meist selbst in JPG; echtes HEIC bräuchte ein neues Paket, darum vorerst abgelehnt mit Satz für Lia.
6. Abgelegte Dateien der Ebene (und der Ebenen darüber) als Kontext: Text über agentkit.textfassung, Fotos über Read.
7. Zwei Sonderläufe ohne neue Nachricht im Verlauf: „Was haben wir bisher?“ und „Auftrag ordnen“ (Auftragstext aus
   dem Gespräch: entschieden, verworfen, Wunsch).

Bedarf an **Hauptordner/agentkit**: Read mit Pfadgrenze testen (Punkt 5). Sonst nichts; Reihenfrage schreibe ich
über das vorhandene `agentkit.strukturpflege`.

Ich trage beides in die Haupt-STATUS ein und biete dir je eine Sitzung dafür an. Reihenfolge: agentkit-Test,
dann lia/chat. Die Web-App baue ich parallel gegen die vereinbarte Schnittstelle (in Tests mit einem Ersatz).

## 2. Was in shared/webapp passiert

**Ablage der eigenen Dateien am Ort**: `lia/instanz/ablage/<ort-id>/` (wie gespraech-plan 1(b) vorschlägt, damit
später auch lia/unterricht sie lesen kann). Schreibt nur die Web-App, so wie sie heute schon `fassungen/` dort
schreibt. Erlaubt: PDF, Word, PowerPoint, Excel, JPG, PNG, je bis 20 MB, Name bereinigt. Fester Hinweis: keine
Schülerdaten.

**Damit der laufende Dienst nicht kaputt geht** (Vorlagen und CSS wirken sofort): Die neue Oberfläche kommt in
neue Dateien `oberflaeche/` (Vorlagen) und `statisch/ruhig.css`. `vorlagen/` und `stil.css` bleiben unverändert,
bis umgeschaltet ist. Erst der Neustart schaltet um (Python wählt den Ordner). Danach räume ich `vorlagen/` und
`stil.css` in einem eigenen Commit weg (frage dich vorher).

**logik.py** (rein, getestet):
- `markdown_html()` erweitert: Überschriften, Tabellen, Codeblöcke, Bausteine (graue Fläche, Art, Kopieren,
  bei Art reihenfrage und Ebene Reihe „Als Reihenfrage übernehmen“). Escaping wie heute, kein neues Paket.
- Ebenen-Ansicht: was „hier“ hängt und was „darunter“ (Gespräche, Material, Ablage, Stunden bzw. Reihen), Stand
  nur bei wartet, läuft, deine Datei.
- Gesprächsansicht: Nachrichten mit Tagestrennern, Anhänge, rechte Spalte (Reihenfrage, Material, Gespräche).
- Heute: „Wartet auf dich“ zuerst, „Weiter im Gespräch“ (jüngste), „Alle Gespräche“ zugeklappt.
- Seitenleiste: Baum wie heute plus „Gespräche ohne Ort“, roter Punkt bei wartet (auch an zugeklappten Eltern).
- Prüfung der Uploads (Fotos dazu), Text bis 60.000 Zeichen.

**app.py** (dünn), neue Routen, alle POSTs mit Herkunftsprüfung, Token und Doppelklick-Schutz wie bisher:
- `GET /gespraech/<id>`, `POST /gespraech/neu` (Ebene), `POST /gespraech/<id>/nachricht` (Text, Fotos, Dateien),
  `GET /teile/gespraech/<id>/antwort` (htmx alle 2 s, „denkt nach …“ mit Startzeit),
  `POST …/umbenennen`, `…/umhaengen`, `…/loeschen`, `…/bisher`, `…/auftrag` (öffnet „Neu“ mit geordnetem Text und
  Ebene vorbelegt; abschicken wie heute über `/neu`).
- `POST /baustein/reihenfrage` (über strukturpflege, mit Rückgängig).
- `POST /ablage/<ort-id>`, `POST /ablage/<ort-id>/entfernen`, `GET /ablage/<ort-id>/<n>` (Download, Fotos inline).
- `GET /gespraeche` (ohne Ort). Klasse, Reihe, Stunde bekommen die Ebenen-Ansicht.
- „Darüber sprechen“ an Material und Ablage: neues Gespräch an derselben Ebene mit der Datei als Anhang.
- Bleibt wie es ist: Ergebnis, Betrachter, Rückmeldung, final, eigene Fassung, Neu, Struktur pflegen. Sie bekommen
  nur den neuen Rahmen.

**Vorlagen und CSS** nach ui-plan-notion: Inter 400–600, Größen 12/14/16/20/32, 1-px-Linien, graue Flächen,
gedecktes Blau nur Hauptknopf und Fokus, Rot nur „wartet“. Vorschau-Panel rechts (Seitenbilder wie heute im
Betrachter, „Groß ansehen“), mit kleinem Skript; ohne JavaScript öffnet der Link den vorhandenen Betrachter.
Kopieren über die Zwischenablage (geht unter HTTPS und localhost). CSP bleibt `'self'`, keine Inline-Skripte.

**Grenzen, die ich jetzt schon sehe**:
- Vorschau gibt es nur für Material mit Seitenbildern (vom Renderer) und für PDF/Fotos aus der Ablage. Eine
  abgelegte Word-Datei hat keine Seitenbilder; dort Name, Download und „Darüber sprechen“. Seitenbilder für die
  Ablage wären Bedarf an shared/renderer (nicht in diesem Bau).
- Die Skizze zeichnet Beispielseiten; echte Seiten sehen anders aus.

## 3. Schritte (je ein Commit über commit.sh, pruefen.sh grün)
1. Plan und Haupt-STATUS-Eintrag (Bedarf lia/chat, agentkit). Dieser Commit.
2. logik: Markdown mit Überschriften, Tabellen, Bausteinen; Tests.
3. logik: Ebenen, Gesprächsansicht, Heute, Seitenleiste als Daten; Tests mit Ersatz-Schnittstelle.
4. Ablage am Ort (logik, app, Tests über den Socket).
5. Neue Oberfläche: `oberflaeche/`, `ruhig.css`, Skripte (Kopieren, Vorschau, Feld wächst). Alle bisherigen Seiten
   im neuen Rahmen. Tests: jede Seite 200, Rot nur bei wartet, Schriftgrößen, keine IDs im Text (wie heute).
6. Gesprächsrouten gegen die echte lia/chat-Schnittstelle (sobald dort fertig).
7. Probe in der Test-Instanz (Port 8792 über deinen Tunnel, kein Neustart): du und ich führen Gespräche,
   Testaufgaben 1–6. Claude läuft dabei echt über lia/chat auf Lias Kontingent (Cent-Beträge je Nachricht). Die
   Testinstanz ist eine Kopie der echten reihen.toml, die Orte stimmen also. Testgespräche lösche ich danach.
8. Umschalten: `systemctl --user restart webapp.service` (startet den Dienst mit dem neuen Code neu, ca. 2 s
   nicht erreichbar). Nur mit deinem Okay. Danach Abruf aller Seiten, Log ansehen.
9. Mängel aus den echten Läufen beheben (jeder weitere Neustart mit deinem Okay), STATUS neu, Aufräum-Vorschlag.

Neue Pakete: keine. Neustarts: einer zum Umschalten (Schritt 8), weitere nur nach Fixes, je mit Okay.

## 4. Fragen an dich
1. Umbau ohne Lias Okay und ohne ihren Test: so gewollt? (siehe 0)
2. lia/chat und den agentkit-Test in eigenen Sitzungen bauen lassen (je ein Chat pro Ordner)? Ohne sie gibt es
   keine echten Gespräche, nur die Oberfläche.
3. Probe zuerst in der Test-Instanz, dann umschalten (meine Empfehlung), oder gleich am echten Dienst?
4. Wort für Claude in der Oberfläche: „Claude“ wie in der Skizze?
