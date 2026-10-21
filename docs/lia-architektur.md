# Agenten-Netzwerk für Lia – Architektur

Stand 21.10.2026. Grundlage: `~/agenten` auf dem Contabo-Server (User `agent`, 81 Commits, `./pruefen.sh` ALLES GRÜN, 136 Tests), Dienste, Journal, `shared/telegram/logs/zentrale.log`, `uni/logs/`, `shared/verbrauch/laeufe.jsonl` (22 Läufe, 16.–21.10.). Telegram-Inhalte habe ich nur gezählt, nicht gelesen.

---

## 0. Vorab: zwei Punkte, die alles andere bestimmen

**Datenschutz an der Schule.** Lias Postfach und IServ enthalten Daten von Schülerinnen, Schülern und Eltern (Noten, Krankmeldungen, Förderbedarf, Konflikte). In Berlin und Brandenburg (der Begriff „Rahmenlehrplan“ spricht für eins der beiden Länder) braucht die Verarbeitung solcher Daten auf privaten Geräten nach meinem Kenntnisstand eine Genehmigung der Schulleitung. Die Weitergabe an einen US-KI-Anbieter ist noch einmal heikler. Das ist keine Rechtsberatung, aber eine harte Vorbedingung: **Vor dem Mail-Teil mit der Schulleitung bzw. der oder dem Datenschutzbeauftragten klären.** Unterrichtsplanung und Materialerstellung betreffen fast keine personenbezogenen Daten. Deshalb fängt der Ausbauplan dort an (Abschnitt 7).

**Claude-Konto.** Alle Läufe gehen heute über Jans Pro-Abo, das sich die Agenten mit seinen eigenen Chats teilen (`STATUS.md`, „Verbrauch“). Ein einziger Lauf zum Erzeugen von Lernkarten hat die 7-Tage-Auslastung auf 71 % gebracht (`uni/STATUS.md`). Kommt Lia dazu, nehmen sich beide gegenseitig das Kontingent weg, und Schuldaten laufen über Jans privates Verbraucherkonto. Empfehlung: **Lia bekommt ein eigenes Konto, am besten einen API-Schlüssel mit Budgetgrenze** (Geschäftsbedingungen, Auftragsverarbeitungsvertrag möglich). Größenordnung aus deinem Protokoll: Die 7 Opus-Läufe hätten zu API-Preisen zusammen 5,41 USD gekostet, die 13 Sonnet-Läufe 0,46 USD. Für Lia sind also eher zweistellige Euro-Beträge pro Monat zu erwarten, keine dreistelligen.

---

## 1. Ist-Analyse

### Aufbau

| Schicht | Umsetzung | Stelle |
|---|---|---|
| Betrieb | Ein VPS, 4 Kerne, 7,8 GB RAM, kein Swap, kein Docker, User `agent` ohne sudo, systemd-User-Units mit Linger | `CLAUDE.md`, „Server und Tabus“ |
| Grundsatz | „Claude denkt, Python handelt“: `claude -p` ohne Bash, ohne MCP, mit Schreibschutz | `claude_lauf.py:30-36, 152-162` |
| Warteschlangen | Ordner mit einer JSON-Datei je Eintrag (`auftraege`, `freigabe`, `meldungen`), atomar über `os.replace`/`os.rename` | `_ablage.py:58-94` |
| Freigabe | Fingerabdruck über das, was Jan gesehen hat, Ausführung genau einmal (Sperre mit O_EXCL), unklare Ausführungen werden nie wiederholt | `freigabe.py:36-40, 145-173, 137-142` |
| Kontingent | Stufen normal/sparen/nur_auftraege/limit nach 5h- und 7d-Auslastung, Plätze für parallele Läufe | `verbrauch.py:63-74`, `claude_lauf.py:109-130, 220-236` |
| Kanal | Ein Telegram-Bot, Polling, Prüfschleife alle 30 s, Knöpfe, Dateien, Sitzung fortsetzen per Antwort | `zentrale.py:470-528, 534-551` |
| Agent | `uni/agent.py`: ein Lauf arbeitet nacheinander Freigaben, Moodle-Spiegel, Aufträge, Fristen und Post ab | `uni/agent.py:313-318` |
| Qualität | `pruefen.sh` (Tests + ruff), Pre-commit-Hook, STATUS.md als Übergabe, Regeln lernen nur nach Bestätigung | `pruefen.sh`, `regeln.py` |

`dokumente/` ist nur ein Gerüst, `posteingang/` und `einkauf/` sind leer. Es gibt nirgends Code, der eine Mail verschickt. Ausführen kann der Agent bisher nur Freigaben vom Typ „regel“ (`uni/agent.py:60-64`).

### Stärken (übernehmen)

1. **Die Trennung von Denken und Handeln ist genau richtig für Lia.** Claude hat keine Bash und keinen MCP-Server (`claude_lauf.py:158`). Alles, was nach außen wirkt, ist Python-Code hinter einer Freigabe. Das ist der wirksamste Schutz gegen Prompt-Injection, den es gibt. Andere Sicherungen sind nur Zusatz.
2. **Die Freigabe ist sauber gebaut**: Fingerabdruck, genau einmal, nie still wiederholt, `unklare()`. Das tragen viele fertige Frameworks nicht.
3. **Reine Logik ist getrennt und getestet** (`fristen.py`, `logik.py`, `lernmodell.py`). Netz und Telegram bleiben dünn.
4. **Spiegeln, dann lesen**: Moodle wird nach `data/kurse/` gespiegelt, mit Textfassungen samt Seitennummern und einer `uebersicht.md`. Claude sucht darin mit Grep. Das ist günstig, nachvollziehbar und passt für Lehrpläne und Materialien.
5. **Das Kontingent wird gemessen** (`laeufe.jsonl` mit Tokens, Dauer, USD).
6. **Übergabe über Dateien** (STATUS.md, CLAUDE.md) statt über Chatverläufe.

### Schwächen und Engpässe

| # | Problem | Beleg | Folge für Lia |
|---|---|---|---|
| S1 | **Nur für eine Person gebaut.** Chat-ID fest als `JAN`, Agentenliste fest im Code, Pfade relativ zum Code, „Jan“ in Grundregel und Prompts | `zentrale.py:60`, `logik.py:10`, `config.py:11`, `claude_lauf.py:46-51`, `auftraege.py:40-41` | Ohne Umbau kann Lia nichts freigeben, und ihre Aufträge landen in denselben Warteschlangen wie Jans |
| S2 | **agentkit wird per `.pth` direkt aus Jans Arbeitsordner geladen** | `STATUS.md`, Einbindung per `.pth` | Ein halbfertiger Commit in Jans Hauptordner-Chat legt sofort auch Lias Agenten lahm |
| S3 | **Claude-CLI aktualisiert sich selbst** und das Setup hängt an CLI-Flags (`--tools`, `stream-json`, `rate_limit_event`) | 2.1.301 am 16.10. (`uni/STATUS.md`), heute 2.1.304 | Ein Update kann beide Netzwerke gleichzeitig zerlegen. Version festschreiben, Update nur nach `pruefen.sh` und einem echten Testlauf |
| S4 | **Werkzeuge gelten pro Agent, nicht pro Aufgabe.** Die Post-Prüfung läuft mit Read/Write/Edit/WebSearch, obwohl sie fremde Mailtexte im Prompt hat | `einstellungen.py:16-21`, `einstellungen.toml [werkzeuge] uni`, `uni/agent.py:298` | Eine präparierte Mail kann Dateien im Agent-Ordner verändern (Gedächtnis vergiften) oder Daten in eine Suchanfrage schreiben. Bei Lia mit WebFetch wäre das ein Abflusskanal |
| S5 | **Ausfälle von Diensten erfährt niemand.** `uni-transkript` wird seit dem 17.10. jede Nacht vom OOM-Killer beendet, immer an derselben 69-Minuten-Datei. STATUS.md sagt dazu nur „noch nicht geprüft“ | `journalctl --user -u uni-transkript` (19.–21.10.), `MemoryMax=3G`, kein Swap | Lia merkt nicht, wenn ihr Fristen-Scan stillsteht. Es braucht `OnFailure=` mit Meldung an den Admin (Jan) und eine Sperrliste für Dateien, die immer wieder abbrechen |
| S6 | **Kein Backup.** Git hat keinen Remote, `data/` liegt nicht im Repo, es gibt keinen Cronjob | `git remote -v` leer, `.gitignore` | Für Lias Materialien und Fristen ist das nicht hinnehmbar |
| S7 | **Ein Lauf blockiert den ganzen Agenten.** Eine Sperre pro Agent, alles läuft nacheinander, höchstens 2 Plätze für alle Agenten zusammen | `claude_lauf.py:235-236`, `einstellungen.toml [parallel]` | Ein Opus-Lauf von 15 Minuten für eine Unterrichtsreihe hält die Mail-Triage auf. Jan und Lia würden um dieselben Plätze konkurrieren |
| S8 | **Kein PDF.** Ohne LibreOffice kein PDF-Export, keine Vorschau, Claude sieht das Ergebnis nicht | `dokumente/STATUS.md`, „Grenzen ohne LibreOffice“ | Arbeitsblätter müssen gedruckt werden, PDF ist für Lia der Kern. (Dein `~/.ssh/config` hat einen Root-Zugang mit demselben Schlüssel: Installieren geht also, die Regel „ohne sudo“ ist eine Entscheidung, keine Grenze. Ohne Root geht es mit Typst, siehe 2.3) |
| S9 | **Telegram-Bedienung setzt Technikwissen voraus**: Schrägstrich-Befehle, „Antwort auf Meldung setzt Sitzung fort“, `/pc`, `/weiter` | `zentrale.py:67-77` | Für Lia so nicht bedienbar |
| S10 | **Linkvorschau ist an**: Telegram ruft Links in Nachrichten selbst ab | `zentrale.py` setzt nirgends `disable_web_page_preview` | Eine präparierte Mail kann über einen Link in einer Meldung Daten abfließen lassen. Billig zu beheben |
| S11 | **Gelernte Regeln stehen in STATUS.md**, die gleichzeitig Übergabe-Dokument ist | `regeln.py:21, 54-57` | Für Lia getrennt halten: Regeln sind Gedächtnis, STATUS.md ist Entwicklerdoku |

### Für Lia wiederverwenden oder neu bauen

| Wiederverwenden (nach Umbau auf mehrere Instanzen) | Neu |
|---|---|
| `_ablage`, `auftraege`, `freigabe`, `meldungen`, `regeln`, `log`, `verbrauch` | Konfiguration je Instanz (Person, Chat-ID, Pfade, Konto) |
| `claude_lauf` (Werkzeuge pro Aufgabe statt pro Agent) | IServ-Anbindung: IMAP/SMTP, CalDAV, WebDAV |
| `textfassung`, `kalender` (ICS-Auswertung, auch für CalDAV) | Mail-Ausführer: Entwurf per IMAP APPEND, Senden per SMTP |
| `postfach.py` (nur lesen, UID-Marke) als Vorlage | Renderer für docx/pptx/PDF (zusammen mit Jans dokumente-Agent) |
| `fristen.py` (Erinnerung 7/2/0 Tage) | Wissensbasis: Lehrpläne, Materialkatalog, Profil |
| Spiegel-Muster aus `kurse.py` (für IServ-Dateien) | Workflow-Motor für mehrstufige Skills |
| `logik.py` (Aufteilen, Knöpfe, Gemeldet) | Bedienung für Nicht-Techniker, Admin-Kanal für Fehler, Backup |
| `pruefen.sh`, Git-Hook, Vorlagen, Konventionen | |

---

## 2. Zielarchitektur

### 2.1 Rollen: drei logisch, zwei Prozesse zum Start

Ich schneide nach **Vertrauensgrenze und Daten**, nicht nach Themen. Daraus ergeben sich drei Rollen:

| Rolle | Aufgabe | Sieht fremde Inhalte? | Darf nach außen? | Werkzeuge für Claude |
|---|---|---|---|---|
| **buero** | Postfächer, Kalender, Fristen, Mailentwürfe, Wochenvorschau, Formulare | Ja (Mails, Anhänge) | Nur über Freigabe, Python führt aus | Triage: **keine**. Entwürfe: Read auf eigene Daten |
| **unterricht** | Unterrichtsreihen, Recherche, Abgleich mit dem Lehrplan, Einzelmaterial | Ja (Web) | Nein | Read, Glob, Grep, WebSearch, WebFetch, Write in den Arbeitsordner |
| **material** | Aus einer Beschreibung docx, pptx und PDF bauen, Vorschau erzeugen, prüfen | Nein | Nein | keine (reines Python) |

Begründung der Grenzen:
- **buero** ist der einzige Teil, der Mails liest *und* handeln kann. Er bekommt die wenigsten Werkzeuge und keinen Webzugriff. So kann eine präparierte Mail nichts recherchieren und nichts hinausschicken.
- **unterricht** darf ins Web, sieht aber nie Lias Postfach. Ein Abflusskanal (Web) und vertrauliche Daten (Mail) kommen nie in denselben Lauf.
- **material** ist kein eigener Agent, sondern ein **Renderer-Dienst** (Python): Beschreibung (JSON) rein, Datei raus. Er ist identisch mit dem, was dein `dokumente`-Agent ohnehin braucht. Einmal bauen, beide nutzen ihn.

Zum Start laufen **zwei Prozesse** (buero, unterricht) und der Renderer als Bibliothek. Mehr Agenten (eigener Recherche-Agent, eigener Fristen-Agent, ein Orchestrator-LLM) wären **überdimensioniert**. Recherche ist ein Werkzeug, keine Rolle. Fristen hängen an denselben Daten wie die Mails. Und für ein Routing, das die Zentrale mit einer Regel erledigt, braucht es keinen eigenen LLM-Lauf.

### 2.2 Orchestrierung

- **Verteilung**: Lias Zentrale (eigener Bot, eigene Instanz) entscheidet regelbasiert. Knöpfe und Bereiche der Oberfläche führen direkt zum richtigen Agenten. Freitext ohne Zuordnung klassifiziert ein Haiku-Lauf ohne Werkzeuge in buero oder unterricht, Lia bestätigt mit einem Knopf. Das ist dein bisheriger Ablauf „An welchen Agenten geht das?“, nur mit Vorschlag.
- **Kommunikation**: wie bisher über die Datei-Warteschlangen, mit neuen Feldern `instanz` und `von` (Agent oder Mensch).
  - Agent an Agent nur in einer Richtung und deterministisch: unterricht und buero übergeben an den Renderer.
  - buero gibt **nie selbst** Aufträge an unterricht. Er schlägt Lia vor: „Fachkonferenz Freitag, Unterlagen vorbereiten? [An Unterricht] [Nein]“. Das hält Kosten und Kontrolle bei ihr.
- **Planung**: Mehrstufige Abläufe (Unterrichtsreihe) sind **Zustandsmaschinen in Python**. Eine Datei `reihen/<id>/zustand.json` hält Phase, Eingaben und Ergebnisse. Jede Phase ist ein kurzer claude-Lauf mit Ausgabe-Schema. Zwischen den Phasen liegen Prüfpunkte, an denen Lia entscheidet (Grobplanung erst freigeben, dann Stunden, dann Material). Das hält einzelne Läufe klein (dein Karten-Lauf mit 29 von 30 Schritten und 820.000 Tokens zeigt, was sonst passiert), und abgebrochene Abläufe lassen sich fortsetzen.
- **Eskalation**, zwei Kanäle:
  - *Fachlich* an Lia: Rückfrage, Frist droht, Entwurf wartet seit 24 h.
  - *Technisch* an Jan: Dienst fehlgeschlagen, IServ-Login kaputt, Kontingent, Fehler im Renderer. Das läuft über `OnFailure=` in jeder Unit und über eine Gesundheitsprüfung, die Jans Zentrale meldet, **ohne Inhalte**. Lia bekommt nie einen Stacktrace, höchstens „Mail-Abruf hakt, Jan ist informiert“.

### 2.3 Anbindungen

**Grundsatz: keine MCP-Server mit Schreibrechten.** Ein MCP-Server, über den Claude Mails senden oder Termine anlegen kann, hebelt „Claude denkt, Python handelt“ aus. Deshalb gilt: **Lesen heißt in Python spiegeln, Schreiben heißt in Python ausführen, nach Freigabe.** MCP lohnt sich höchstens später für eine reine Lesesuche über die Wissensbasis, und auch dann ist er nicht nötig (siehe 2.4).

| Quelle | Lesen (Python, Timer) | Schreiben (Python, nach Freigabestufe) | Anmerkung |
|---|---|---|---|
| IServ-Mail | IMAP 993, nur lesen, UID-Marke (wie `postfach.py`) | Entwurf: IMAP APPEND in „Entwürfe“. Senden: SMTP 587 | IMAP/SMTP muss die Schule freigeschaltet haben. **Vorab mit Lias Zugang testen**, inklusive Zwei-Faktor-Anmeldung und App-Passwort |
| Private Mail | IMAP des Anbieters | wie oben | eigenes Konto in Lias `.env` |
| IServ-Kalender | CalDAV-REPORT, dann ICS-Auswertung mit `agentkit.kalender` | CalDAV PUT/DELETE | Freischaltung prüfen. Notfalls Abo-ICS nur lesend |
| Privater Kalender | ICS-Abo (wie bei dir) | – | – |
| IServ-Dateien | WebDAV-Spiegel ausgewählter Ordner, mit Textfassung (Muster `kurse.py`) | WebDAV PUT in den eigenen Ordner `KI-Ausgang/` | Gruppenordner nur lesen |
| Rahmenlehrpläne | einmal laden, Textfassung mit Seiten, strukturierter Auszug | – | statisch, nur bei neuer Fassung neu |
| Eigene Materialien | Import aus einem festen Ordner (IServ oder Cloud-Sync) | – | Metadaten-Karte je Datei (2.4) |
| Websuche | eingebautes WebSearch/WebFetch, **nur** in unterricht | – | nie in Läufen mit Mailinhalt |
| Dokumente | – | python-docx, python-pptx (vorhanden). **PDF über Typst** | Typst ist eine einzelne Programmdatei ohne sudo und erzeugt PDF und PNG. Damit kann Claude das Ergebnis als Bild prüfen. Alternativ LibreOffice headless per Root, braucht aber viel RAM. Für Arbeitsblätter und Bewertungsraster ist Typst die bessere Wahl, docx nur dort, wo Lia selbst weiterbearbeiten will |

Der Renderer nimmt eine Beschreibung entgegen (Format wie für `dokumente` vorgesehen: Blöcke, Tabellen, Bilder, Folien), prüft sie gegen ein Schema und baut mit Lias Vorlagen (Kopfzeile Schule, Fach-Farben). Danach erzeugt er Textfassung und PNG-Vorschau zur Selbstkontrolle. Bricht der Bau ab, geht der Fehler an Claude zurück, wie in `dokumente/STATUS.md` festgelegt.

### 2.4 Gedächtnis und Wissensbasis

Fünf Schichten mit klarer Schreibregel:

| Schicht | Inhalt | Speicher | Wer schreibt | Abruf |
|---|---|---|---|---|
| Wissensbasis | Rahmenlehrpläne (Text mit Seiten plus `kompetenzen.json`: Themenfelder, Standards, Operatoren), Lias Materialien mit Karte (Fach, Jahrgang, Thema, Methode, Dauer, Quelle, Pfad) | Dateien, `katalog.sqlite` | Python beim Import, Karten von Claude vorgeschlagen und von Python geprüft | `uebersicht.md` je Fach, Grep, SQL-Filter |
| Profil | Schule, Fächer, Kurse und Jahrgänge, Stundenplan, Vorgaben der Fachkonferenz zur Bewertung, Stil-Vorlieben, Vorlagen | `profil.md`, `vorlagen/` | nur nach Lias Freigabe | jeder Lauf bekommt den passenden Ausschnitt |
| Operativ | Fristen (Quelle, Status bestätigt/unbestätigt), Termine-Cache, Mail-Metadaten, Kontakte mit Rollen (Sekretariat, Fachbereichsleitung) | `buero.sqlite` | Python | Wochenvorschau und Fristen-Scan rein per SQL, ohne Claude |
| Verlauf | Protokolle je Auftrag, `reihen/<id>/` mit Zustand und Versionen, Lias Änderungskommentare | Dateien | Python, Claude im Arbeitsordner | Grep, Verweise |
| Gelernte Regeln | allgemein, je Agent und **je Skill** | `regeln/*.md` (nicht in STATUS.md) | nur nach Freigabe (Mechanik `regeln.py`) | in jeden passenden Lauf |

**Keine Vektordatenbank.** Für ein paar hundert Dateien und zwei Lehrpläne reichen Grep über Textfassungen plus Übersichten. Das hat dein uni-Agent schon gezeigt: von 488.000 auf 177.000 Tokens nur durch bessere Übersichten. Wenn es zu viel wird, kommt zuerst **SQLite FTS5** (Volltextsuche mit Rangfolge, in der Python-Standardbibliothek enthalten, kein neues Paket), Embeddings erst danach.

**Datensparsamkeit**: Namen von Schülerinnen und Schülern kommen nicht in die Wissensbasis und nicht in Profil oder Regeln. Wo Kurse nötig sind, stehen dort Kursnamen und Anzahlen, keine Personen.

### 2.5 Workflows als Skills

Ein Skill ist ein **versionierter Ordner**, keine Prompt-Zeichenkette im Code:

```
skills/unterrichtsreihe/
  SKILL.md          Zweck, Phasen, Qualitätskriterien (Text für Claude)
  phasen.toml       Phasen, Modell je Phase, Werkzeuge je Phase, Prüfpunkte für Lia
  schema/           Eingabe und Ausgabe je Phase (JSON-Schema)
  vorlagen/         Beispielstruktur, Formulierungsmuster
  beispiele/        2–3 gute Ergebnisse (Few-Shot, von Lia abgenommen)
  pruefen.py        Python-Prüfungen (Lehrplanbezug vorhanden? Zeiten summieren sich auf 90 min?)
  evals/            feste Testfälle mit Erwartung, laufen in pruefen.sh (ohne Claude) und als echter Lauf von Hand
  regeln.md         gelernte Regeln nur für diesen Skill
```

- **Python lädt den Skill und hängt die nötigen Teile an den Prompt.** Die eingebauten Claude-Code-Skills (`.claude/skills/`) nutze ich bewusst nicht als Mechanismus: Du schränkst mit `--tools` ein, dann müsste das Skill-Werkzeug zusätzlich freigegeben werden, und das Laden geschieht dann nach Ermessen des Modells. Selbst geladen ist es deterministisch und die Kosten sind sichtbar.
- **Jede Ausgabe trägt Skill-Name und Version.** So lässt sich später sagen, ob Version 3 bessere Reihen liefert als Version 2.
- **Verbessern**: Lias „Ändern“-Kommentare landen im Verlauf. Häufen sie sich, schlägt der Agent eine Skill-Regel vor (Freigabe). Größere Umbauten am Skill macht ein Entwickler-Chat im Skill-Ordner, geprüft gegen `evals/`.
- **Geteilt und persönlich**: Generische Skills (Mail-Triage, Einzelmaterial, Bewertungsraster) liegen im gemeinsamen Code. Lias Vorlieben stehen in ihren `regeln/` und im `profil.md`, nicht im Skill.

Erste Skills: `einzelmaterial` (Arbeitsblatt, Folien, Raster zu einem Thema), `mail-triage`, `mail-antwort`, `wochenvorschau`. Danach `unterrichtsreihe`, sobald Lias Ablauf feststeht.

### 2.6 Hintergrundjobs

| Job | Takt | Claude? | Ablauf |
|---|---|---|---|
| Spiegel | nachts 2 Uhr | nein | IServ-WebDAV, Kalender, Textfassungen, Backup |
| Postfach-Triage | Schultage 6:30–19:30 alle 30 min, Ferien 2× täglich | Haiku/Sonnet, **ohne Werkzeuge** | Python holt neue Mails. Vorfilter ohne Claude: Newsletter (List-Id), IServ-Systemmails, bekannte Absender-Regeln. Der Rest geht an Claude, Ausgabe JSON `{kategorie, dringend, frist, handlung, antwort_noetig}`. Python prüft das Schema, trägt Fristen als *unbestätigt* ein und meldet nur Dringendes sofort |
| Mail-Entwürfe | nach Triage, wenn `antwort_noetig` und Absender intern | Sonnet, ohne Werkzeuge | Entwurf landet in IServ-Entwürfe, Meldung mit [Ansehen] [Senden] [Ändern] |
| Fristen-Scan | täglich 6:00 | nein | SQL über Fristen und Termine, Schuljahreskalender (Notenschluss, Konferenzen), Erinnerungen 7/2/0 Tage (`fristen.py`) |
| Wochenvorschau | Sonntag 17:00 | ein Sonnet-Lauf zum Formulieren | Python sammelt Stundenplan, Termine, Fristen, offene Entwürfe und den Stand der Reihen. Claude formuliert, Kurzfassung per Telegram |
| Gesundheit | stündlich | nein | Letzte erfolgreiche Läufe, IServ-Login, Plattenplatz. Probleme gehen an Jan |

Schulferien als ICS-Abo, damit die Jobs in den Ferien seltener laufen.

---

## 3. Gemeinsame Basis und Trennung

**Empfehlung: derselbe Server, aber ein eigener Linux-User `lia`** (Home 700, eigene systemd-User-Units, eigene `~/.claude`-Anmeldung). Ein zweiter VPS (wenige Euro im Monat) wäre die sauberste Trennung. Er lohnt sich, wenn die Schule es verlangt oder der RAM knapp wird. Heute sind von 7,8 GB rund 6,5 GB frei, das reicht, sobald die Transkription repariert ist und Swap da ist.

| Gemeinsam | Strikt getrennt |
|---|---|
| Server, Betriebssystem, Python | Linux-User und Home-Verzeichnis (Rechte 700) |
| agentkit als **versioniertes Paket** (Git-Tag, `pip install` in jede venv). Lia läuft auf einer festen Version, Jan testet neue zuerst bei sich | `.env`, Zugangsdaten, IServ-Passwort |
| Code der Zentrale (eine Codebasis, zwei Instanzen) | Telegram-Bot-Token und Chat-ID (eigener Bot „Lias Assistenz“) |
| Renderer (material) und generische Skills | Claude-Konto, Kontingent, Sitzungen (`~/.claude/projects`) |
| `pruefen.sh`, Git-Hook, Vorlagen, Konventionen | Warteschlangen, Wissensbasis, Profil, Regeln, Protokolle, Logs |
| festgeschriebene Claude-CLI-Version | Backups (verschlüsselt, eigener Schlüssel) |
| Admin-Kanal: Lias technische Fehler gehen ohne Inhalt an Jans Zentrale | Plätze für Läufe (`verbrauch/plaetze` je Instanz), damit sich beide nicht blockieren |

Offen gesagt: **Vor dir als Root schützt diese Trennung Lias Daten nicht.** Sie verhindert Versehen (ein Agent liest die falschen Daten, ein Commit bricht die falsche Instanz), aber keinen Admin. Das ist eine Frage von Absprache und Vertrauen. Für Schuldaten ist es ein weiterer Grund, so wenig wie möglich zu speichern.

Nötige Umbauten an agentkit, klein gehalten:
- `config`: Wurzel der Instanz aus der Umgebungsvariable `AGENTKIT_INSTANZ` statt `SHARED_DIR = Path(__file__)…`
- Name der Person und Chat-ID aus der Konfiguration statt `JAN` und „Jan“ im Text
- Agentenliste aus der Konfiguration statt `AGENTEN = (...)`
- Werkzeuge pro **Aufgabe** (`laufen(..., werkzeuge=[])`)
- `regeln` in eigene Dateien
- Linkvorschau aus
- `OnFailure=` in den Vorlagen

---

## 4. Kontrolle und Sicherheit

### Freigabe-Matrix

**E** = nur entwerfen, Lia handelt selbst. **T** = mit einem Tipp freigeben, Python führt genau den gezeigten Entwurf einmal aus. **A** = selbstständig, wird protokolliert und gegebenenfalls gemeldet.

| Aktion | Stufe | Begründung |
|---|---|---|
| Mails lesen, einordnen, Fristen als *unbestätigt* erfassen | A | keine Wirkung nach außen |
| Erinnerungen und Wochenvorschau an Lia | A | |
| Antwortentwurf in IServ-Entwürfe ablegen | A | liegt nur in ihrem Postfach, sie sieht ihn in ihrer gewohnten Umgebung |
| Mail senden an Kollegium, Sekretariat, Schulleitung (intern) | T | Empfänger setzt Python aus den Kopfzeilen, nicht Claude |
| Mail senden an Externe (Theater, Verlage, Fortbildung) | T | mit Warnhinweis „extern“ |
| Mail an Eltern oder Schülerinnen und Schüler | E | Ton, Rechtsfolgen, Datenschutz. Lia schickt selbst |
| Zusage oder Absage auf Umfragen, Einladungen | T | |
| Eintrag im eigenen Kalender (aus Mail erkannt) | T, später A | A erst nach einigen Wochen ohne Fehler, mit Rückgängig-Knopf |
| Kalendereinladung annehmen/ablehnen, Termin ändern oder löschen | T | erreicht andere |
| Frist aus Mail bestätigen | T | eine falsche Frist ist teuer, das Bestätigen kostet einen Tipp |
| IServ-Dateien spiegeln, Materialien erzeugen, recherchieren | A | intern |
| Upload in den eigenen IServ-Ordner `KI-Ausgang/` | A | nur Lia sieht ihn |
| Teilen in Gruppen- oder Fachschaftsordnern, Aufgabe im IServ-Modul anlegen | T | Kolleginnen, Kollegen oder Kinder sehen es |
| Formulare und Anträge (Fortbildung, Dienstreise, Exkursion) | E | Lia unterschreibt und reicht ein |
| Noten, Zeugnisse, Gutachten, Förderpläne | E, besser gar nicht | Datenschutz und Verantwortung |
| Käufe, Bestellungen, Tickets | gar nicht im ersten Ausbau | Lia hat nicht danach gefragt |
| Mails oder Dateien löschen | nie. Verschieben ins Archiv: T | nicht rückgängig zu machen |
| Neue gelernte Regel | T | wie bei dir |

Ergänzungen zur Freigabe:
- Eine Freigabe läuft nach 48 h ab.
- Es gibt **kein „alle freigeben“ für Sendungen**.
- Ein langer Entwurf geht nicht in mehreren Telegram-Stücken zur Freigabe, sondern als Link in den Arbeitsbereich oder in die IServ-Entwürfe. Sonst ist kaum zu sehen, was man gerade freigibt.

### Schutz gegen Prompt-Injection über Mails

Nach Wirksamkeit geordnet. Die ersten drei tragen, der Rest ergänzt:

1. **Keine Werkzeuge in Läufen mit fremdem Inhalt.** Triage- und Entwurfsläufe bekommen `--tools` leer: Text rein, JSON raus. Dann kann eine Mail nichts lesen, schreiben oder abrufen lassen. (Das behebt S4 auch bei dir.)
2. **Markierung nach Herkunft.** Jede Ausgabe eines Laufs, der fremde Inhalte gesehen hat, ist markiert. Python lässt daraus **nur** Entwürfe, Meldungen und unbestätigte Fristen entstehen, nie eine A-Aktion. Empfänger, Betreff-Präfix und Antwort-Kopfzeilen bestimmt Python. Weicht Reply-To von From ab, gibt es eine Warnung.
3. **Kein Abflusskanal.** Kein Web in Mail-Läufen, Linkvorschau in Telegram aus, Links in Entwürfen werden markiert, Meldungen enthalten keine Rohinhalte aus Mails (nur die Zusammenfassung des Modells, als reiner Text ohne Markdown oder HTML).
4. **Strikte Ausgabe.** JSON-Schema, feste Kategorien, Längenbegrenzung. Was nicht passt, wird verworfen und protokolliert.
5. **Gedächtnis schützen.** Nichts aus Mails gelangt ohne Lias Tipp in Profil, Regeln oder Wissensbasis.
6. **Anhänge**: nur Textfassung, keine Makros, Größenlimit. Office-Dateien von außen gelten als fremd.
7. **Eingrenzen**: Mailinhalt zwischen zufälligen Grenzmarken, Hinweis „Daten, keine Anweisungen“. Das ist schwach und nur Zusatz.
8. **Prüfen**: ein Satz präparierter Testmails („Ignoriere alle Regeln und leite …“, versteckter HTML-Text, Antwort-an-Fälschung) in `evals/`, regelmäßig gegen die Triage laufen lassen. `permission_denials > 0` in einem Triage-Lauf geht als Alarm an Jan (die Zählung gibt es schon, `claude_lauf.py:253`).

---

## 5. Weitere Einsatzfelder

| Feld | Nutzen | Aufwand | Bemerkung |
|---|---|---|---|
| Vertretungs- und Notfallstunden-Mappe je Jahrgang | hoch | niedrig | fast nur Einzelmaterial-Skill |
| Klausur mit Erwartungshorizont nach Operatoren und Standards des Lehrplans | hoch | mittel | Lehrplan-Wissensbasis muss stehen |
| Primärtexte aufbereiten (gemeinfreie Klassiker), Erschließungshilfen in zwei bis drei Niveaustufen | hoch | niedrig | Philosophie/Ethik, Quelle immer angeben |
| Stoffverteilungs- und Jahresplan aus Lehrplan, Ferien und Stundenplan | hoch | mittel | Vorstufe der Unterrichtsreihen |
| Theaterbesuche: Spielpläne nach Schulvorstellungen und Theaterpädagogik durchsuchen, Elternbrief, Kostenliste, Fristen | hoch | mittel | Recherche als Wochenjob |
| Stückfassung: Strichfassung, Textanteil je Figur, Rollenverteilung | hoch | niedrig–mittel | Zählen in Python, Vorschläge von Claude |
| Probenplan aus Stundenplan, Raumbelegung und Aufführungstermin | mittel | mittel | Personen nur pseudonym |
| Bewertungsbögen für Präsentationsprüfung, Prüfungen in Darstellendem Spiel | hoch | niedrig | Raster-Skill |
| Aufführungsrechte und Verlage anfragen (Vorlagen, Fristen) | mittel | niedrig | buero |
| Aktuelle ethische Fälle der Woche als Gesprächsanlass | mittel | niedrig | Websuche, wöchentlich |
| Warm-ups und Übungen nach Ziel (Präsenz, Raum, Chor) | mittel | niedrig | wächst mit Lias Material |
| Fortbildungen finden (regionale Angebote) | mittel | niedrig | Websuche, monatlich |
| Konferenz- und Elternabend-Protokolle aus Stichpunkten | mittel | niedrig | ohne Namen von Kindern |
| Rückmeldung zu Schüleressays | hoch | mittel | **nur anonymisiert, nur Hinweise, keine Note**. Datenschutz vorher klären |
| Proben-Aufnahmen transkribieren oder auswerten | – | – | **abraten**: Ton und Bild von Kindern |
| Lernbegleiter, den die Kinder selbst nutzen | – | – | **abraten**: Zugang für Schülerinnen und Schüler, Aufsicht, Datenschutz. Gehört in schulische Werkzeuge |

---

## 6. Kanal

| Kriterium | A: Telegram für alles | B: Telegram (Dringendes, Freigaben) + IServ als Arbeitsbereich | C: Telegram (Dringendes, Freigaben) + eigene Web-Plattform |
|---|---|---|---|
| Bedienung unterwegs | ++ | ++ | ++ |
| Dokumente prüfen und überarbeiten | −− Datei öffnen, Kommentar als freier Text, keine Stelle im Dokument | + Word und PowerPoint wie gewohnt, Entwürfe im IServ-Postfach | ++ Vorschau, Kommentar je Abschnitt, Versionen |
| Freigabe-Flows | + kurz; − lang (mehrere Nachrichten, schwer zu überblicken) | ++ Tipp in Telegram, Prüfen in den IServ-Entwürfen | ++ Tipp in Telegram, lange Entwürfe mit Unterschieden im Web |
| Dateihandling | − 20 MB, keine Ordner, keine Versionen | + IServ-Ordner `KI-Ausgang/` | ++ |
| Entwicklung und Wartung | ++ existiert, 1–2 Tage Anpassung | + WebDAV-Upload und IMAP APPEND, wenige Tage | −− Anmeldung, HTTPS, Oberfläche, Updates, Angriffsfläche mit Schuldaten im Netz. Mehrere Wochen Feierabendarbeit |
| Nutzbar ohne Technik-Affinität | o Chat ist vertraut, aber Befehle und „Antwort auf Meldung“ sind versteckte Mechanik | ++ sie bleibt in Werkzeugen, die sie kennt | + wenn schlicht gehalten, − neues Werkzeug |
| Datenschutz | − alles liegt in der Telegram-Cloud (Bots ohne Ende-zu-Ende-Verschlüsselung) | + Inhalte bleiben in IServ, Telegram bekommt nur Kurzhinweise | + bei Zugang nur über ein privates Netz |

**Empfehlung: B jetzt, C später nur, wenn es gebraucht wird.** Die Frage lautete Telegram gegen Web. Der günstigste Arbeitsbereich ist aber der, den Lia schon täglich nutzt: Entwürfe in den IServ-Entwürfen, Materialien im IServ-Ordner, Telegram nur für „Achtung“ und „Tipp zum Freigeben“. Ohne Schrägstrich-Befehle: ein fester Knopf-Bereich (Neues Material, Mail-Überblick, Woche, Frage), Freitext geht mit Vorschlag und Knopf an den passenden Agenten.

Eine eigene Web-Plattform lohnt erst, wenn der Workflow für Unterrichtsreihen läuft. Dann wird das mehrstufige Prüfen mit Kommentaren je Phase in Telegram und IServ wirklich mühsam. Skizze für dann:

- **Technik**: FastAPI mit server-gerenderten Seiten (HTMX, kein Build-Schritt, Python wie der Rest), nur an localhost gebunden. Zugang **über Tailscale** (einmal von Jan auf Lias Laptop und Handy eingerichtet), also keine öffentliche Adresse und keine eigene Passwortverwaltung. Die Seite liest und schreibt dieselben Warteschlangen und Dateien wie die Agenten, es gibt keine zweite Datenhaltung.
- **Ansichten**:
  1. *Heute/Woche*: Stunden, Termine, Fristen, wartende Freigaben
  2. *Eingang*: eingeordnete Mails mit Entwurf daneben
  3. *Freigaben*: vollständige Vorschau, Unterschied zur Vorfassung, Freigeben/Ändern/Ablehnen
  4. *Unterricht*: je Kurs die Reihen mit Phasenstand, Stunden und Material, Kommentar je Abschnitt, daraus wird ein Änderungsauftrag
  5. *Bibliothek*: Suche und Filter (Fach, Jahrgang, Thema, Typ), PDF-Vorschau, nach IServ schieben
  6. *Fristen*: bestätigen, verschieben, erledigt
  7. *Profil und Regeln*: lesen, Änderung vorschlagen
- **Nicht bauen**: Chat-Oberfläche (dafür ist Telegram da), eigene Dateiverwaltung (dafür ist IServ da), Bearbeiten im Browser (dafür sind Word und PowerPoint da).

---

## 7. Ausbaureihenfolge

Jeder Schritt mit Voraussetzung und Prüfkriterium. Die Reihenfolge folgt dem Risiko: zuerst das, was ohne Schuldaten Nutzen bringt.

**Schritt 0: Fundament (Jan, ohne Lia)**
- *Inhalt*: agentkit mandantenfähig machen (Abschnitt 3), als versioniertes Paket ausliefern, Claude-CLI festschreiben, `OnFailure=` und Gesundheitsprüfung, Backup (z. B. restic auf einen externen Speicher, verschlüsselt), Swap anlegen und Transkription reparieren (Sperrliste für abgebrochene Dateien oder kleineres Modell), Werkzeuge pro Aufgabe, Linkvorschau aus.
- *Voraussetzung*: dein Okay. Root für Swap.
- *Funktioniert, wenn*: dein System läuft unverändert (`pruefen.sh` grün, uni-Timer laufen), eine Test-Instanz `lia` mit Dummy-Agent schafft einen Auftrag hin und zurück über einen Test-Bot, der User `agent` kann `/home/lia` nicht lesen, ein absichtlich fehlschlagender Dienst erzeugt eine Meldung bei dir, und eine Wiederherstellung aus dem Backup ist einmal geprobt.

**Schritt 1: Kleinste nützliche Version, „Material auf Zuruf“**
- *Inhalt*: Lias Bot mit Knopf-Menü, Agent unterricht mit Skill `einzelmaterial`, Renderer (docx, pptx, PDF über Typst, PNG-Vorschau), eine Schulvorlage. Lia schreibt „Arbeitsblatt kategorischer Imperativ, Klasse 10, 45 min“ und bekommt PDF und docx zurück.
- *Voraussetzung*: Schritt 0, Lias eigenes Claude-Konto oder API-Schlüssel, eine Vorlage von ihr. Keine IServ-Zugangsdaten, keine Datenschutzfrage.
- *Funktioniert, wenn*: in zwei Wochen mindestens fünf echte Aufträge von Lia kommen, mindestens drei Ergebnisse ohne größere Nacharbeit im Unterricht eingesetzt werden, ein Ergebnis in unter 10 Minuten da ist und die Kosten pro Auftrag gemessen sind. **Nutzt sie es nicht, liegt das Problem woanders als in der Technik. Dann vor dem Weiterbauen mit ihr reden.**

**Schritt 2: Wissensbasis**
- *Inhalt*: Rahmenlehrpläne für ihre Fächer (Textfassung, `kompetenzen.json`), Import eines Ordners ihrer Materialien mit Karten, `profil.md` mit ihr zusammen.
- *Voraussetzung*: Schritt 1 wird genutzt, Lia gibt Materialien frei.
- *Funktioniert, wenn*: Ergebnisse den Lehrplan mit Seite oder Standard zitieren, eine Frage wie „Was habe ich schon zu Antigone?“ ihre Dateien findet und Lia das Profil abgenommen hat.

**Schritt 3: buero nur lesend, Kalender und Fristen**
- *Inhalt*: CalDAV oder ICS von IServ und privat, Fristen-Scan, Wochenvorschau am Sonntag.
- *Voraussetzung*: IServ-Zugang technisch getestet (CalDAV/IMAP freigeschaltet? Zwei-Faktor?), **Klärung mit der Schule zum Datenschutz**.
- *Funktioniert, wenn*: vier Wochenvorschauen hintereinander stimmen und Lia in der Zeit keine Frist entdeckt, die das System verpasst hat.

**Schritt 4: Mail-Triage nur lesend**
- *Inhalt*: IMAP-Spiegel, Vorfilter, Triage ohne Werkzeuge, JSON, Meldungen bei Dringendem, unbestätigte Fristen mit Tipp zum Bestätigen.
- *Voraussetzung*: Schritt 3, Testmails mit Injection-Versuchen in `evals/` bestehen.
- *Funktioniert, wenn*: Lia zwei Wochen lang die Einordnung markiert (richtig/falsch), mindestens 90 % von „wichtig“ stimmen, keine dringende Mail verpasst wird und die Injection-Tests grün sind.

**Schritt 5: Mail-Entwürfe und Senden mit Tipp**
- *Inhalt*: Skill `mail-antwort`, IMAP APPEND in Entwürfe (A), SMTP-Ausführer hinter der Freigabe (T) zunächst nur für interne Empfänger.
- *Voraussetzung*: Schritt 4 stabil, Ausführer mit Tests (Fingerabdruck, genau einmal, Empfänger aus Kopfzeilen).
- *Funktioniert, wenn*: die Entwürfe mit wenig Änderung genutzt werden, das Protokoll keine einzige Sendung ohne Freigabe zeigt und ein doppelter Tipp keine zweite Mail auslöst.

**Schritt 6: Unterrichtsreihen**
- *Inhalt*: Lias festen Workflow als Skill `unterrichtsreihe` mit Phasen, Prüfpunkten, Beispielen und Prüfungen.
- *Voraussetzung*: Workflow mit Lia ausgearbeitet, Schritte 1 und 2 stabil.
- *Funktioniert, wenn*: eine komplette Reihe gebaut und unterrichtet wurde und aus Lias Änderungen Skill-Regeln entstanden sind, die die nächste Reihe spürbar verbessern.

**Schritt 7: Ausbau nach Bedarf**
- *Inhalt*: Kalender schreiben (T), Teilen in IServ-Gruppen (T), Web-Plattform C, weitere Felder aus Abschnitt 5.
- *Voraussetzung*: belegter Bedarf aus dem echten Gebrauch, nicht vorab.
- *Funktioniert, wenn*: je Ausbau vorher ein Prüfkriterium wie oben feststeht.

---

## Kritische Zusammenfassung

- **Ungeeignet am Bestand**: ausschließlich für Jan gebaut (S1), live geteiltes agentkit (S2), sich selbst aktualisierende CLI (S3), Werkzeuge pro Agent (S4), keine Meldung bei Ausfällen (S5, belegt durch fünf Nächte OOM), kein Backup (S6), geteiltes Pro-Kontingent. Nichts davon ist schwer zu beheben, aber alles muss **vor** Lia erledigt sein.
- **Überdimensioniert wäre**: Orchestrator-LLM, mehr als drei Rollen, MCP-Server mit Schreibrechten, Vektordatenbank, Web-Plattform als erster Schritt, selbstständiges Senden.
- **Fragil bleibt**: der IServ-Zugang (die Schule kann IMAP oder WebDAV abschalten, Passwortwechsel, Zwei-Faktor. Deshalb Gesundheitsprüfung und Meldung an Jan), Telegram-Mechaniken für eine Nicht-Technikerin, ein einzelner VPS, und die Frage, ob die Schule das Ganze überhaupt erlaubt. Letzteres zuerst klären, sonst wird für die Schublade gebaut.
