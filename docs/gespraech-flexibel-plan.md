# Plan: Gespräch wie eine Claude-Code-Sitzung (Punkt 37)

Stand 10.11.2026. Nur Plan, nichts gebaut. Grundlage: Punkt 37 und 36 der Haupt-STATUS, `docs/gespraech-plan.md`,
`shared/webapp/bauplan-gespraech.md`, `lia/chat/STATUS.md`, `agentkit.claude_lauf`, `strukturpflege`, `feedback`.
Die Entscheidungen trifft Jan, Fragen am Ende (Abschnitt 8).

## 0. Anlass und Jans Antworten (10.11.2026)

Probe der neuen Web-App in der Test-Instanz abgebrochen: Das Gespräch ist zu starr und überfordernd. Heute bekommt
Claude je Nachricht nur einen Ortstext (Fach, Klasse, Reihe, Lerngruppe, Notizen, Stundenliste), liest außer Fotos
und abgelegten Dateien nichts selbst, kann nur Text antworten und kennt die Agenten nicht.

Jans Antworten auf die zwei offenen Fragen aus Punkt 37:
- **Überfordernd** war alles vier: Länge der Antworten, Gliederung (Überschriften, Tabellen, Bausteinblöcke), die
  Oberfläche ringsum (Spalten, Knöpfe, Schalter) und dass Claude nichts tun kann.
- **Unintuitiv** sind alle Bearbeiten-Flächen: Stunden in der Reihe, Reihen und Klassen, Dateien und Ablage, die
  Masken allgemein. Wunsch: Drag and Drop.

Folgerung: Der Hauptweg wird „Lia sagt es, Claude macht es“. Drag and Drop ist der zweite Weg für direkte Handgriffe
(Abschnitt 6, Schritt 10). Die Masken bleiben nur als Notweg, bis beides trägt. Antworten werden kurz und
gesprächig: erst nachfragen statt alles auf einmal, Tabellen und Überschriften nur auf Wunsch.

Zielbild in einem Beispiel (Stunde ohne Reihe):
> Lia: Ich will morgen in der 8 mit dem Fall vom Ladendiebstahl anfangen.
> Claude: (liest reihen.toml, sieht: die Stunde am 11.11. hängt an keiner Reihe; die Reihe „Straftheorien“ in der
> 8 hat laut Reihenentwurf als Stunde 1 „Einstieg über einen Fall“) Die Stunde morgen hängt an keiner Reihe. Laut
> deinem Reihenentwurf zu Straftheorien ist Stunde 1 genau so ein Fall-Einstieg. Soll ich sie dort als Stunde 1
> einhängen?
> Lia: Ja.
> Claude: Erledigt: „Einstieg: Ladendiebstahl“ ist Stunde 1 von Straftheorien. (Darunter eine stille Zeile
> „Geändert: Stunde eingehängt · rückgängig“.)

---

## 1. Lesen: Claude kennt alles am Ort

### Was Claude lesen und durchsuchen darf
Drei Ordner, alle über `claude_lauf.laufen(..., lese_ordner=[...])` mit Read, Grep und Glob:
1. **`lia/instanz/`**: reihen.toml, regeln.md, lerngruppen.toml (geht heute schon als Ortstext mit), `ablage/`,
   `fassungen/`, `auftraege/` (Aufträge mit Text, Stand, Ergebnis und Pfaden). Gesperrt: `.env`, `.env.*` (schon so),
   dazu neu `zentrale/`, `meldungen/`, `freigabe/`, `verbrauch/`, `ausfall/` (Technik und Jans Kanal, nichts für
   das Gespräch).
2. **Lesesicht** `lia/chat/data/lesesicht/` (neu, nicht im Repo, Ordner 0700): Python legt dort lesbare Fassungen
   an, weil Read keine Word- und PowerPoint-Dateien lesen kann und die Ergebnisse der Agenten verstreut in
   `lia/<agent>/data/` liegen (zusammen über 600 MB, viel davon Zwischenstände).
   - `orte.md`: Baum Fach › Klasse › Reihe › Stunde mit ids, Terminen, Reihenfragen (aus agentkit.struktur), damit
     Claude ids nicht aus der TOML-Datei raten muss.
   - `ergebnisse/<auftrag-id>.md`: je erledigtem Auftrag Agent, Ort, Auftragstext, Ergebnistext und der Text der
     Ergebnisdateien (agentkit.textfassung; Fotos und PDF als Kopie, die liest Read selbst).
   - `ablage/<ort-id>/<datei>.md`: Text der abgelegten Word-, PowerPoint- und Excel-Dateien.
   - `faehigkeiten.md`: was jeder Agent kann (Abschnitt 3).
   Aufgebaut vor jedem Lauf, nur Neues (Signatur aus Pfad, Größe, Änderungszeit, wie heute `signatur()` in
   gespraechlauf.py). Kein Claude, keine Kosten. Gelöscht wird, was es in der Quelle nicht mehr gibt.
3. **Gesprächsordner** `lia/chat/data/gespraeche/<id>/` (wie heute: Fotos und Dateien dieses Gesprächs).

Die Ergebnisordner der Agenten selbst bekommt Claude nicht: Dort liegen Arbeitsstände, Rohdaten, Logs anderer
Läufe. Was Lia zu sehen bekam, steht in der Lesesicht.

### Was sich in agentkit.claude_lauf ändert (Hauptordner)
Probe 10.11.2026 im Scratchpad (claude 2.1.304, Agenten-Konto, Sonnet, zwei Läufe zusammen 0,085 USD), Aufbau wie
`lese_ordner`, aber Grep und Glob nicht gesperrt:
- Grep und Glob halten sich an `Read(//<ordner>/**)`: Grep im erlaubten Ordner ging, Grep im Ordner darüber wurde
  abgelehnt. Eine eigene Erlaubnis für Grep und Glob ist nicht nötig.
- `.env` blieb zu: Grep direkt auf `.env` abgelehnt, Grep mit Muster `.env*` und Glob `.*` fanden nichts.
- Ein Symlink im erlaubten Ordner auf eine Datei außerhalb: Read abgelehnt, Grep folgt ihm nicht.

Änderungen:
1. `lese_ordner` mit Suche: Grep und Glob aus `NUR_LESEN_VERBOTEN` nehmen, wenn der Agent sie unter `[werkzeuge]`
   hat (neuer Schalter oder fest für lese_ordner, Entscheidung im Bau). Tests ohne Netz plus eine echte Probe wie
   oben.
2. `lese_sperren=[ordner, ...]`: weitere `Read(//<ordner>/**)`-Sperren innerhalb der Lese-Ordner (für `zentrale/`
   usw.). Geprüft wie `lese_ordner_pruefen`.
3. Prompt über stdin statt als Argument (Punkt 35). Wird mit Lesen weniger dringend, weil Kontext nicht mehr in den
   Prompt kopiert wird, gehört aber in denselben Schritt.
4. Probe als Skript `agentkit/probe_rechte.py` (echter Lauf, wenige Cent, nicht in pruefen.sh), damit nach jedem
   claude-Update geprüft werden kann, ob die Grenzen noch halten.

### Was sich in lia/chat ändert
- Ortstext bleibt kurz (wo das Gespräch hängt, ids), der Rest wird gelesen. Prompt neu: kurz antworten, nachfragen,
  aus dem Ort heraus belegen („laut Reihenentwurf …“), Überschriften und Tabellen nur, wenn Lia etwas Längeres will.
  Bausteinblöcke entfallen als Pflichtform (Kopieren geht auch aus normalem Text).
- Gesprächsläufe mit den drei Lese-Ordnern, Lesesicht vor dem Lauf aktualisieren.
- Ablage-Text und Ablage-Fotos gehen nicht mehr in den Prompt (Claude liest sie bei Bedarf), damit fällt auch das
  Kopieren der Ablage-Fotos in den Gesprächsordner weg.

---

## 2. Handeln ohne Knöpfe: wenige Werkzeuge, Python prüft

### Geht das mit claude -p? Ja (Probe 10.11.2026)
Ein eigener MCP-Server, nur mit Python-Bordmitteln (JSON-RPC über stdin/stdout, rund 40 Zeilen, kein neues Paket),
wurde von `claude -p` mit `--strict-mcp-config --mcp-config <json>` gestartet und war verbunden:
- Erlaubtes Werkzeug (`allow: mcp__lia__notiz_ablegen`, Modus dontAsk) rief Claude auf, Python schrieb die Datei.
- Werkzeug unter `deny` (`mcp__lia__mail_senden`) war für Claude gar nicht sichtbar; die Datei, die es angelegt
  hätte, entstand nicht.
- Lehnte Python einen Aufruf ab (Text zu lang, `isError`), bekam Claude den Satz und gab ihn weiter.
- Der Server läuft als Kindprozess von claude und endet mit dem Lauf. Was er Python-seitig tun will, muss im Aufruf
  selbst fertig werden (siehe Commit unten).

### Werkzeugkasten (agentkit, Hauptordner)
`shared/agentkit/werkzeugkasten/`: ein MCP-Server mit festen Werkzeugen. `claude_lauf.laufen(..., werkzeuge=[...],
werkzeug_kontext={...})` baut die MCP-Konfiguration selbst (nur dieser Server, nie ein anderer) und erlaubt genau
die genannten Werkzeuge. Der Kontext (Instanz, Gespräch, Person) geht als Startargument an den Server, Claude kann ihn
nicht ändern. Werkzeuge:

| Werkzeug | macht (Python) | Rückgängig |
|---|---|---|
| `struktur_aendern(operation, argumente)` | `strukturpflege.ausfuehren`, alle 29 Operationen außer `lerngruppe_setzen`, von „Claude im Gespräch (Lia)“ | `strukturpflege.rueckgaengig` |
| `rueckgaengig(aktion)` | macht eine Handlung aus diesem Werkzeugkasten zurück | – |
| `datei_ablegen(quelle, ort)` | Anhang dieses Gesprächs oder Text, den Claude geschrieben hat (als .md), in `lia/instanz/ablage/<ort-id>/` | in einen Papierkorb der Ablage, 30 Tage |
| `gespraech_umhaengen(ort)` | Gespräch an einen anderen Ort hängen (`schnittstelle.umhaengen`) | zurückhängen |
| `auftrag_geben(agent, text, ort, art?, dateien?)` | `agentkit.auftraege.neuer_auftrag`, quelle „gespraech“, nur Agenten, die laut Fähigkeiten Aufträge annehmen (Abschnitt 3) | `auftraege.zurueckziehen`, solange nicht fertig |
| `merken(text, bezug?)` | Feedback an den Feedback-Dienst (Abschnitt 4) | wie Jans Stopp |
| `ausbau_vorschlagen(ordner, was_fehlt, beispiel)` | Ausbau-Vorschlag an Jan (Abschnitt 3) | zurückziehen, solange Jan nicht entschieden hat |

Für jede Handlung gilt:
- **Prüfen:** Python prüft Form und Grenzen (ids, Längen, Endungen, höchstens 20 schreibende Aufrufe je Nachricht)
  und antwortet mit einem Satz, den Claude Lia sagen kann. strukturpflege prüft wie heute Konflikte mit
  gleichzeitigen Änderungen der Web-App (Sperre, `gesehen`).
- **Protokoll:** jede Handlung als Zeile in `lia/chat/data/handlungen.jsonl` (Gespräch, Nachricht, Werkzeug,
  Ergebnis, Aktions-id; nie der Text der Lerngruppe) und als Ereignis für den Leitstand (agentkit.ereignis). Das
  Gespräch bekommt zu Claudes Antwort die Liste der Handlungen, die Web-App zeigt sie als eine stille Zeile.
- **Rückgängig:** jede Handlung hat eine Gegen-Handlung. Lia sagt „mach das rückgängig“ oder klickt in der stillen
  Zeile (Entscheidung 8.3).
- **Nach außen nie:** Im Werkzeugkasten gibt es kein Werkzeug, das Mails, Nachrichten, Abgaben oder Käufe auslöst.
  Aufträge an Agenten laufen wie heute; was dort nach außen geht, geht weiter nur über die Freigabe.
- **Nachfragen** (Prompt, Entscheidung 8.2): eine einzelne, rückgängig machbare Änderung macht Claude direkt und
  sagt es. Mehrere Änderungen auf einmal, Löschen, Archivieren und Aufträge kündigt er in einem Satz an und wartet
  auf Lias Ja im Gespräch.

Commit: strukturpflege committet reihen.toml in einem Hintergrund-Faden. Im Server-Prozess würde der Faden mit dem
Lauf sterben. Darum schreibt das Werkzeug nur und reiht den Commit ein (`commit=True`, Warteschlange wie heute),
lia/chat stößt nach dem Lauf `strukturpflege.anstossen()` an und wartet darauf (der oneshot-Dienst hält so lange).

Ablage: `shared/webapp/ablage.py` (Prüfung von Namen, Endungen, Größe) zieht nach `agentkit.ablage`, damit Web-App
und Werkzeug dieselbe Prüfung nutzen. Die Web-App stellt danach im eigenen Chat um.

---

## 3. Flexible Agenten

### Fähigkeiten maschinenlesbar
Jeder Agent bekommt `faehigkeiten.toml` in seinem Ordner (Vorlage in `shared/vorlagen/`), gepflegt vom Chat dieses
Ordners:
```toml
agent = "unterricht"
wofuer = "Material für Ethik-Stunden: Arbeitsblatt, Präsentation, Reihenentwurf, LEK"
nimmt_auftraege = true          # sonst nur Nachbesserungen (wie theater heute)
quelle = "portal-material"      # wie der Agent Aufträge erkennt

[[kann]]
art = "arbeitsblatt"
beschreibung = "Arbeitsblatt als Word, mit Text, Merksatz, Aufgaben, auf Wunsch Varianten"
braucht = ["thema"]             # ohne das fragt Claude nach
ergebnis = ["docx", "pdf"]
dauer = "5-15 min"
faecher = ["Ethik"]

[[kann_nicht]]
beschreibung = "Noten berechnen, Schülerdaten verarbeiten"
```
`agentkit.faehigkeiten` liest und prüft die Dateien (Schema, Pflichtfelder) und schreibt `faehigkeiten.md` in die
Lesesicht. Ein Test in pruefen.sh verlangt die Datei für jeden Agenten, der Aufträge annimmt. Später können die
Vorlagen der Galerie „Neu“ (`VORLAGEN` in shared/webapp/logik.py) aus diesen Dateien kommen statt aus Code.

### Wie Claude prüft, ob ein Auftrag geht
Claude liest `faehigkeiten.md` und sagt im Gespräch eins von drei Dingen:
- **geht**: nennt Agent und Ergebnis, fragt Fehlendes (`braucht`) nach, gibt den Auftrag nach Lias Ja
  (`auftrag_geben`). Python prüft noch einmal: Agent nimmt Aufträge an, `art` steht unter `kann`, Ort gibt es.
- **geht teilweise**: sagt, was davon geht, und bietet an, den Rest als Ausbau vorzuschlagen.
- **geht nicht**: sagt es ehrlich, hilft im Gespräch selbst, so weit es reicht, und schlägt den Ausbau vor.
Scheitert ein Auftrag (Abschluss „fehlgeschlagen“ mit Grund; einen eigenen Abschluss „geht nicht“ gibt es in
agentkit.auftraege noch nicht, er käme in Schritt 7 dazu), sieht Claude das in der Lesesicht und kann daraus ebenfalls
einen Ausbau vorschlagen. Ist ein Auftrag fertig, schreibt lia/chat eine kurze Notiz ins Gespräch, aus dem er
kam („Arbeitsblatt ist fertig“), mit Link auf das Ergebnis.

### Lücke wird Ausbau-Auftrag (mit Jans Zustimmung)
- Werkzeug `ausbau_vorschlagen` legt einen Eintrag in eine neue Warteschlange `shared/ausbau/` (agentkit.ausbau,
  Muster wie auftraege): Ordner, was fehlt, Beispiel aus dem Gespräch (ohne Namen), wer es wollte, Gespräch-id.
  Lia hört: „Das kann noch keiner deiner Agenten. Ich habe Jan vorgeschlagen, das einzubauen.“
- Jan bekommt über die Zentrale eine Meldung mit „Einverstanden“ / „Verwerfen“.
- **Stufe 1 (Vorschlag für jetzt):** Bei „Einverstanden“ schreibt Python den Ausbau als Punkt in die STATUS.md des
  zuständigen Ordners (Abschnitt „Ausbau-Aufträge“). Jan startet dort eine Claude-Code-Sitzung („Ausbau-Auftrag X“),
  die wie immer erst plant und auf sein Okay wartet. Wird `faehigkeiten.toml` erweitert und der Eintrag erledigt,
  bekommt das Gespräch, aus dem der Wunsch kam, eine Notiz („geht jetzt“).
- **Stufe 2 (später, eigener Plan):** Nach Jans Einverstanden startet ein Lauf von Claude Code im Ordner selbst, in
  einem eigenen git-Worktree auf eigenem Zweig, mit Tests und pruefen.sh. Er endet mit einem Zweig zur Durchsicht;
  übernommen wird nur nach Jans Okay. Das ist „Agenten ändern Code“ und braucht eine Änderung in CLAUDE.md und
  eigene Grenzen (Speicher, Kosten, Rechte).

---

## 4. Lernen und Automatik

### Was es schon gibt (agentkit.feedback, shared/feedback)
- Feedback zu einem **Ergebnis** (Bezug: Auftrag) wird zugeordnet als Nachbesserung, Regel, Notiz oder keine.
  Regeln landen in `<instanz>/regeln.md` oder unter „Gelernte Regeln“ in der STATUS.md des Agenten, wirken sofort
  (claude_lauf liest sie bei jedem Lauf, auch für lia/chat) und Jan hat den Stopp-Knopf.
- Lias Fassungen (eigene Fassung gegen final, Kommentare) fließen in die Zuordnung ein (`fassung_abschnitt`).
- Grenzen nach CLAUDE.md in `entscheiden()`: was nach außen geht, Datenschutz, Regeln ändern oder löschen,
  Widersprüche werden ein Vorschlag an Jan; Lias Nachbesserungen laufen ohne Grenze.

### Was fehlt
1. **Feedback zum Gespräch selbst** („antworte kürzer“, „keine Tabellen“): feedback.py kennt nur den Bezug auf einen
   Auftrag. Neu: Bezug „Gespräch“ (Ausschnitt der letzten Einträge statt Auftrag und Ergebnis), Ziel meist
   „Gelernte Regeln“ von lia/chat.
2. **Feedback aus dem Gespräch zu einem Ergebnis** („das Arbeitsblatt war zu schwer“): Werkzeug `merken` mit Bezug
   auf den Auftrag, den Claude in der Lesesicht findet. Läuft dann durch den vorhandenen Ablauf.
3. **Lia nimmt eigenes Gelerntes zurück** („vergiss das wieder“): heute ist Löschen einer Regel immer ein Vorschlag an
   Jan. Vorschlag: Regeln, die aus Lias eigenem Feedback stammen, darf sie selbst zurücknehmen (wie Jans Stopp),
   Jan erfährt es (Entscheidung 8.8).
4. **Leise Signale** (Lia macht eine Handlung rückgängig, korrigiert Claude): nicht automatisch zur Regel. Claude darf
   im Gespräch fragen „Soll ich mir merken, dass …?“, erst Lias Ja wird Feedback.
5. **Lückenübersicht für Jan:** Ausbau-Vorschläge, abgelehnte Aufträge, „geht nicht“ aus Gesprächen einmal die Woche
   als kurze Meldung (Agent lia/auswertung oder Zentrale, eigener kleiner Schritt).

### Stufen der Automatik
1. Claude liest alles am Ort (Abschnitt 1).
2. Claude ändert Lias eigene Daten mit Rückgängig (Struktur, Ablage, Ort des Gesprächs).
3. Claude gibt Aufträge an Lias Agenten und merkt sich Feedback.
4. Claude schlägt Ausbau vor, Jan entscheidet, Ausbau in einer Sitzung (Stufe 1 aus Abschnitt 3).
5. Später: Ausbau-Läufe auf eigenem Zweig (Stufe 2), eigener Plan.
Jede Stufe erst nach einer Probe mit Jan, dann zwei Wochen echter Betrieb und Blick auf Protokoll und Kosten.

---

## 5. Vorschlag für CLAUDE.md (Jan entscheidet, Entscheidung 8.7)

1. Architektur, nach „Grundsatz: Claude denkt, Python handelt“ ergänzen:
   „In Gesprächen handelt Claude nur über die Werkzeuge aus `agentkit.werkzeugkasten` (eigener MCP-Server, kein
   anderer). Jedes Werkzeug ist Python: prüft die Eingabe, protokolliert, lässt sich rückgängig machen und handelt nie
   nach außen. Lesen über `lese_ordner` (Read, Grep, Glob mit Pfadgrenze, .env gesperrt).“
2. Warteschlangen: `shared/ausbau/` (Agent -> Jan: Ausbau-Vorschlag) ergänzen. agentkit-Liste: werkzeugkasten,
   faehigkeiten, ausbau, ablage.
3. „Agenten ändern keinen Code“ bleibt und wird ergänzt: „Fehlt eine Fähigkeit, schlägt ein Agent einen
   Ausbau-Auftrag vor. Code ändert nur eine Claude-Code-Sitzung im zuständigen Ordner nach Jans Okay.“ Unter „Nie
   automatisch“ kommt dazu: Ausbau-Aufträge.
4. Vorlage für neue Agenten: `faehigkeiten.toml` gehört dazu, für Agenten, die Aufträge annehmen, Pflicht.
5. Lernen aus Feedback: Feedback kann sich auch auf ein Gespräch beziehen; Lia darf Regeln aus ihrem eigenen Feedback
   selbst zurücknehmen (falls 8.8 ja).
6. Grundsatz von lia/chat („startet nie einen Auftrag“) ändert sich in lia/chat/STATUS.md (falls 8.5 ja).

---

## 6. Schritte, Zuständigkeit, Kosten

Je Schritt ein Commit über commit.sh, `./pruefen.sh` grün (nur mit Sperre), Tests ohne Netz plus ein echter Lauf.
Jeder Ordner im eigenen Chat; Bedarf an andere Ordner als Punkt in die Haupt-STATUS.

| # | Ordner | Schritt | Größe |
|---|---|---|---|
| 1 | Hauptordner/agentkit | claude_lauf: Grep/Glob unter lese_ordner, `lese_sperren`, Prompt über stdin (Punkt 35), `probe_rechte.py` | klein |
| 2 | lia/chat | Lesesicht (orte.md, ergebnisse/, ablage/), drei Lese-Ordner, neuer kurzer Prompt, Kosten messen. lia/chat liest die Instanz aus dem Gespräch statt fest `lia/instanz` (sonst ändert eine Probe echte Daten) | mittel |
| 3 | Hauptordner/agentkit | werkzeugkasten (MCP-Server, Bordmittel) mit struktur_aendern, rueckgaengig, datei_ablegen, gespraech_umhaengen; `agentkit.ablage`; Protokoll; claude_lauf `werkzeuge=` | mittel |
| 4 | lia/chat | Werkzeuge im Gespräch, Handlungen am Eintrag, Commit nach dem Lauf, Nachfrage-Regeln im Prompt | mittel |
| 5 | shared/webapp | Oberfläche ruhiger: Gespräch und Baum, rechte Spalte schlank, Knöpfe „Als Reihenfrage übernehmen“, Bausteine, „Auftrag ordnen“, Schalter weg; stille Handlungszeile; Ablage über agentkit.ablage. Dann Probe in der Test-Instanz mit Jan | mittel |
| 6 | Hauptordner + lia/unterricht, theater, recherche, examen, verwaltung | faehigkeiten.toml: Schema, agentkit.faehigkeiten, Vorlage; je Agent die Datei im eigenen Chat | klein je Ordner |
| 7 | Hauptordner + lia/chat | Werkzeug auftrag_geben, Notiz im Gespräch, wenn der Auftrag fertig ist | mittel |
| 8 | Hauptordner (agentkit, shared/telegram) | agentkit.ausbau, Werkzeug ausbau_vorschlagen, Meldung mit Knöpfen an Jan, Eintrag in die STATUS des Ordners | mittel |
| 9 | Hauptordner + lia/chat | feedback mit Bezug Gespräch, Werkzeug merken, Rücknahme durch Lia | mittel |
| 10 | shared/webapp | Drag and Drop: Stunden in der Reihe, Reihen zwischen Klassen, Dateien in Ablage und Gespräch (alle über strukturpflege bzw. agentkit.ablage, mit Rückgängig). Kann nach Schritt 5 parallel laufen | mittel |
| 11 | shared/webapp | Umschalten `webapp.service` nach Probe, nur mit Jans Okay | klein |

Nach Schritt 2 und nach Schritt 5 je eine Probe mit Jan; nach Schritt 11 zwei Wochen echter Betrieb, dann Kosten und
Protokoll ansehen.

### Kosten je Gesprächsnachricht
- Heute gemessen (10.11., Sonnet): 0,05–0,09 USD, steigt mit dem Verlauf; mit Websuche 0,14 USD, die
  Folgenachricht 0,21 USD.
- Mit Lesen und Werkzeugen: Jeder Werkzeugaufruf ist eine weitere Runde mit dem ganzen Gesprächsverlauf (größtenteils
  aus dem Zwischenspeicher, also billiger). Die Probe brauchte für 7 Runden mit winzigen Dateien ohne Verlauf
  0,04–0,05 USD. Schätzung, nicht gemessen: 0,10–0,30 USD je Nachricht mit Sonnet, mehr bei langen Dateien und
  mit Opus. Gemessen wird in Schritt 2 und 4, nicht geschätzt.
- Dafür entfällt Prompt-Text, der heute bei jedem Lauf mitgeht (Ablage bis 40.000 Zeichen).
- Aufträge, die Claude gibt, kosten wie heute Aufträge aus der Web-App. Alles auf Lias Kontingent (Jans Entscheidung
  09.11.), Jan sieht es im Leitstand.

### Risiken
- **Speicher (7,8 GB, kein Swap):** Ein claude-Prozess braucht rund 230–290 MB (gemessen 10.11. an laufenden
  Sitzungen). Dazu kommen der MCP-Server (Python mit agentkit, geschätzt 40–60 MB) und beim Aufbau der Lesesicht
  pypdf/python-docx. `lia-chat.service` hat `MemoryMax=500M`. Darum: Lesesicht vor dem claude-Lauf in einem eigenen,
  kurzen Prozess aufbauen, Grenze nach der Messung in Schritt 2/4 anpassen (Vorschlag 700M), höchstens zwei
  Läufe gleichzeitig wie heute (`[parallel]`). pruefen.sh nur mit Sperre.
- **Falsche Handlung** (Stunde an die falsche Reihe): Rückgängig, Protokoll, Nachfragen bei mehreren Änderungen.
- **Anweisungen in Dateien oder Webseiten** könnten Claude zu Handlungen verleiten. Begrenzt dadurch, dass kein
  Werkzeug nach außen handelt, alles rückgängig geht und die Mengengrenze je Nachricht gilt. Wer Netz und Handeln
  trennen will, sperrt die schreibenden Werkzeuge in Läufen mit WebFetch (Entscheidung 8.4).
- **Gleichzeitige Änderung** durch Web-App und Claude: strukturpflege sperrt und meldet Konflikte (vorhanden).
- **Lange Gespräche** werden mit Werkzeugausgaben schneller lang (Kontextgrenze). Ausweg wie im gespraech-plan:
  zusammenfassen und neu anfangen; ob claude bei `--resume` selbst verdichtet, prüft Schritt 4.
- **claude-Updates** können Rechte-Verhalten ändern: `probe_rechte.py` nach jedem Update.
- **Datenschutz:** Lesesicht enthält Texte von Ergebnissen und Ablage, nicht im Repo, Ordner 0700, wird mit den
  Quellen gelöscht. Lerngruppe nie im Protokoll.
- **Test-Instanz:** lia/chat liest heute immer `lia/instanz`. Ohne Schritt 2 würde eine Probe mit Werkzeugen Lias
  echte Struktur ändern.

---

## 7. Was nicht in diesem Plan steht
Noten berechnen, Stelle im Dokument markieren, Seitenbilder für die Ablage (siehe gespraech-plan 5), Jans eigene
Agenten (gleicher Werkzeugkasten später möglich), automatische Ausbau-Läufe (Stufe 2, eigener Plan).

---

## 8. Entscheidungen für Jan

1. **Reihenfolge:** erst Lesen und kurzer Prompt (Schritte 1–2, Probe), dann Handeln (3–5), dann Agenten und Lernen
   (6–9), Drag and Drop parallel ab Schritt 5? **Empfehlung: ja.**
2. **Wann handelt Claude ohne Nachfrage?** Einzelne, rückgängig machbare Änderung direkt; mehrere Änderungen,
   Löschen, Archivieren und Aufträge erst nach Lias Ja im Gespräch. **Empfehlung: so.**
3. **Rückgängig in der Oberfläche:** eine stille Zeile „Geändert: … · rückgängig“ unter der Antwort, oder nur
   über das Gespräch („mach das rückgängig“)? **Empfehlung: stille Zeile, weil Lia sonst nicht sieht, was sich
   geändert hat.**
4. **Websuche:** Häkchen „Im Netz nachsehen“ weg, Claude sucht selbst, wenn nötig (der Suchtext geht hinaus, Prompt
   verbietet Namen), oder Häkchen bleibt? Und: schreibende Werkzeuge in Läufen mit Websuche sperren?
   **Empfehlung: Häkchen weg, schreibende Werkzeuge in Läufen mit WebFetch nur nach Lias Ja.**
5. **lia/chat darf Aufträge an Lias Agenten geben** (ändert seinen Grundsatz „startet nie einen Auftrag“)?
   **Empfehlung: ja, ab Schritt 7, immer nach Lias Ja.**
6. **Ausbau:** jetzt Stufe 1 (Vorschlag an dich, Eintrag in die STATUS des Ordners, du startest die Sitzung),
   Stufe 2 (automatischer Lauf auf eigenem Zweig) später mit eigenem Plan? **Empfehlung: ja.**
7. **CLAUDE.md** wie in Abschnitt 5 ändern (jeweils im Schritt, der es braucht)? **Empfehlung: ja.**
8. **Lia darf eigenes Gelerntes selbst zurücknehmen**, du erfährst es? **Empfehlung: ja.**
9. **Modell und Schalter „gründlich“:** Schalter weg. In der Probe nach Schritt 2 dieselben Aufgaben mit Sonnet und
   Opus laufen lassen, dann entscheidest du nach Antwortzeit und Qualität (Qualität vor Kosten, 29.10.).
   **Empfehlung: so.**
10. **Drag and Drop zuerst wo?** **Empfehlung: Stunden in der Reihe und Dateien ins Gespräch bzw. an den Ort**, dann
    Reihen zwischen Klassen. Die Masken bleiben als Notweg, bis Gespräch und Ziehen tragen.
