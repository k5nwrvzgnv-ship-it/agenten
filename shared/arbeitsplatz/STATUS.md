# Arbeitsplatz – Stand

## Zweck
Neutrale Web-Oberfläche über Jans Agenten (uni, dokumente, finance): freier Baum aus Orten, Dokumentarten aus
`arten.toml`, Dokumente mit Fassungen und Rückmeldung. Plan und verbindliche Schnittstellen:
`../../docs/arbeitsplatz-plan.md` (Jans Okay 09.11.2026). Gebaut im Hauptordner-Chat (Sitzung A).
Lias App `shared/webapp` ist Muster und Quelle (CSS, Schrift, htmx kopiert), wird nicht verändert.
`uni/portal` bleibt bis zur Abnahme unverändert.

## Aus der Untersuchung 11/2026 (16.11.2026, Hauptordner-Chat mit Jans Okay)
- statisch/ruhig.css: --leise und --sehrleise dunkler (hell #6b6a67 und #706f6c, dunkel --sehrleise #8f8f8a), Kontrast
  ab 4,5 auf --bg und --flaeche. Bei pointer: coarse sind Knöpfe, Baumeinträge, Zeilen und Felder 44 px hoch.
  shared/webapp/tests/test_kontrast.py rechnet nach und verlangt, dass beide ruhig.css gleich bleiben.
  Wirkt sofort, am Gerät noch nicht angesehen.

## Stand (09.11.2026, nachts)
Schritte 1 bis 4 und der lesende Teil von Schritt 5 aus dem Auftrag an Sitzung A:
- agentkit: `neuer_auftrag(..., art=, felder=)`; Nachbesserungen des Feedback-Dienstes erben `ort`, `art`, `felder`,
  wenn der Ursprung eine `art` hat (`auftraege.herkunft_erben`, Lia unverändert).
- agentkit: `orte` (Baum in `<instanz>/orte.json`, Sperre, Rückgängig über `<instanz>/orte-aktionen.json`) und
  `arten` (liest und prüft `arten.toml`, Formular prüfen, Auftragstext).
- App: Rahmen drei Spalten (Baum | Seite | Läuft gerade), Baum mit „+ Seite“ (unter dem aktiven Ort und oben),
  Ort-Seite mit Dokumenten, Unterseiten (↑/↓), „+ Seite“, Umbenennen, Verschieben, Archivieren; Archiv mit
  Wiederherstellen; Hinweis mit Rückgängig nach jeder Änderung; „+ Neu“ öffnet die Galerie der aktiven Arten, das
  Formular legt den Auftrag an (`quelle="arbeitsplatz"`, ort, art, felder, Dateien) und startet
  `<agent>.service` mit `systemctl --user start --no-block`. Doppelklick legt nichts doppelt an.
- Dokument-Ansicht `/dokument/<ursprung>` (Schritt 4, 09.11. nachts): oben die finale, sonst neueste fertige
  Fassung mit Kern, Punkten, „Bitte prüfen“, Original zum Herunterladen, PDF (eigene PDF oder Vorschau des Renderers)
  und allen Seitenbildern; „Rückmeldung geben“ (Text und/oder Datei, über agentkit.fassungen.rueckmeldung an
  feedback.service, nur bei Arten mit rueckmeldung und nur mit ARBEITSPLATZ_AUFTRAEGE=echt), „Eigene Fassung
  hochladen“ (geht immer), alle Fassungen aufklappbar (auch eigene) mit „Als final markieren“, Kosten je Fassung,
  Rückmeldungen mit Antwort des Feedback-Dienstes.
- Heute: „Wartet auf dich“ (fertig, nicht final, letzte 14 Tage; und was nicht geklappt hat), Orte, Zuletzt.
  Rechte Spalte: Läuft gerade, Kosten heute (Jans Instanz) und die letzten 6 Läufe mit Link zum Dokument
  (agentkit.verbrauch.letzte, kosten_je).
- Eigene Ansichten (Schritt 5, lesend, `ansichten.py`, übernommen aus uni/portal/projekt.py und uebungen.py):
  recherche zeigt Recherchebericht.md und die geprüfte Recherche (Reiter Aussagen mit Status- und Fragefilter,
  Quellen, Lücken und Widersprüche, Literatursuche); pruefung zeigt Einschätzung, Bewertung je Rubrikpunkt, Lücken
  je Thema und vorgeschlagene Karten, „Übernehmen“ geht über den Link ins Portal; karten verlinkt aufs Portal
  (Üben braucht fsrs aus uni/.venv, nicht in dieser .venv ohne Jans Okay). Pfade kommen aus `daten.ansicht` des
  Ergebnisses (uni) und werden gegen den Agent-Ordner geprüft.
- Recherchen (docs/recherche-plan.md Schritt 4 und „Recherche am Ort“, Skizze docs/recherche-entwurf.html, Jan
  15.11.2026, nur lesend): Eine Recherche steht im Baum unter ihrem Ort wie eine Unterseite (`logik.baum_zeilen`,
  art "recherche", Zeichen ⌕), die Ort-Seite zeigt „Recherchen“ und leise „Gilt hier mit, von weiter oben“.
  Ort: Feld `ort` in wissen.json, sonst `orte-zuordnung.json` Schlüssel `"recherchen": {"<uni|lia>/<projekt>": ort}`
  (`logik.recherche_ort`; Ort fehlt oder archiviert: ohne Ort). Ohne Ort (Lias Projekte): „Recherchen ohne Ort“ auf
  Heute. `/recherchen` leitet nach Heute weiter. Projekte: Ordner mit wissen.json unter `uni/data/projekte/` und
  `lia/recherche/data/projekte/` (`RECHERCHE_MOTOREN`), gelesen nur bei geänderter Datei (`_WISSEN_SPEICHER`).
  `/recherche/<uni|lia>/<projekt>` ohne `?ansicht`: Übersicht (`ansichten.projekt_uebersicht`): Auf einen Blick
  (Zusammenfassung des letzten Laufs), nur Gesichertes nach Fragegruppe (eine Gruppe: nach Frage), Quelle kurz
  dahinter, Zitat beim Anklicken; Offenes, Unsicheres, Quellen, Kosten in der Klappe. Die ausführlichen Reiter
  (Aussagen mit Filtern, Quellen, Lücken und Rückfragen, Läufe) über „···“ bzw. `?ansicht=`.
  Neue Recherche (17.11.2026, Jan „Ja, alles“): „+ → Recherche …“ auf jeder Ort-Seite und auf Heute öffnet
  `/recherche/neu?ort=<id>` (ein Textfeld „Was willst du wissen?“). „Senden“ zeigt einen Plan ohne Claude
  (`logik.recherche_plan`: Thema = erste Zeile, gekürzt; Fragestellung = ganzer Text; Umfang gründlich, wenn das Wort
  im Text steht, sonst kurz; Kosten aus `agentkit.recherche.kosten_schaetzen`). „Los“ (`/recherche/los`) legt einen
  Auftrag der Art recherche an uni mit dem Ort an und startet uni.service. Von Heute aus muss beim Plan ein Ort
  gewählt werden (Dokumente ohne Ort stünden nirgends). Das Ergebnis erscheint vorerst als Dokument am Ort; als
  Recherche im Baum erst, wenn uni daraus ein Projekt mit `ort` macht (Bedarf in der Haupt-STATUS, Punkt 42).
  Zuordnung 15.11.: Exposé-Recherche -> `expose`. Die alte Dokument-Ansicht recherche bleibt, bis neue Läufe in
  Projekte schreiben.
- finance: Aufträge nach `art` und Feld Thema, Ergebnis mit `daten.titel` (siehe finance/STATUS.md).
- Tests: `tests/` (Logik, Ansichten, App über Unix-Socket mit http.client), in pruefen.sh eingetragen.

„Wartet auf dich“ kennt kein „gesehen“; ein Dokument steht dort, bis es final ist oder 14 Tage alt.

## Ruhige Oberfläche (11.11.2026, `umbauplan-ux.md`, Jans Okay, Variante A)
Übernommen aus Lias App (`shared/webapp/umbauplan-ux.md`, dort nichts geändert), alle fünf Schritte gebaut:
- Aussehen: `ruhig.css` (Kopie) statt `stil.css`; rechte Spalte nur auf Heute (Läuft gerade, Kosten), alle anderen
  Seiten einspaltig und mittig. Was läuft, steht überall im Baum neben „Heute“ und als Marke am Dokument.
- „+“ oben rechts (`vorlagen/_plus.html`): Heute Seite, Dokument …; Ort Seite, Dokument …, Datei; Dokument „Dokument …“
  (nicht blau). „Seite“ legt sofort „Neue Seite“ an, die gleich zum Umbenennen offen steht. Im „···“ des Orts:
  Umbenennen, Verschieben, Unterseiten ordnen (ab zwei), Archivieren. Leere Abschnitte fallen weg, ganz leer steht
  „Noch leer. Mit + fängst du an.“ Im Baum kein „+ Seite“ mehr unter dem aktiven Ort (unten bleibt es).
- Direkt am Ding (`statisch/direkt.js`, `vorlagen/_direkt.html`): Titel eines Orts anklicken (Enter speichert, Esc
  bricht ab, Route `/ort/<id>/umbenennen`); Datei auf die Seite ziehen landet im Feld mit `data-ablegen` (Formular:
  Material, Ort: Datei am Ort, Dokument: Anhang der Rückmeldung).
- Datei am Ort (Python): `POST /neu/datei` legt die Dateien nach `data/eingang/gelegt-<kennung>/` (Grenzen wie beim
  Formular), dann Galerie „Was soll daraus werden?“ (nur Arten mit Material), Formular mit „Schon dabei“, der Auftrag
  übernimmt sie, der Ordner geht danach weg. Liegengebliebenes löscht das nächste Ablegen nach einem Tag.
- Dokument-Seite: Rückmeldung als immer sichtbares Feld (nur Arten mit `rueckmeldung`), „Senden“ der einzige blaue
  Knopf (bei finaler Fassung keiner); je Datei ein Download-Symbol (PDF ansehen, Word-/PowerPoint-/…-Datei); die ersten
  zwei Seiten groß, alle in einer Klappe; im „···“ final und „Eigene Fassung hochladen …“ (`?offen=eigene` öffnet es);
  Verlauf als geschlossene Klappe ab zwei Stationen. `statisch/anhang.js` zeigt den Namen der angehängten Datei.
- Vorschau (Schritt 6, `vorschau.py`): Dokumente ohne Renderer-Vorschau bekommen eigene Seitenbilder in
  `data/vorschau/<auftrag>/<nr>/`, beim ersten Öffnen im Hintergrund, in einem eigenen Prozess mit 1 GB Grenze
  (`vorschau_lauf.py`, `systemd-run --user --scope`). Betrachter `…/ansehen?seite=m` mit Blättern.
- Rückmeldung zu einer Datei oder Seite (Schritt 7), Heute lädt sich jede Minute neu (Schritt 8).
- Schritte 6 bis 8 live seit dem Neustart 11.11. 16:36 mit Jans Okay: 11 Vorschauen ohne Fehler erstellt, alle 7
  Dokumente mit Dateien haben Seitenbilder (vorher 1), Dienst 57 MB, Rundgang 466 Abrufe alle 200.
- Ohne JavaScript geht alles über `<details>` und Formulare. Browser-Probe bei Jan steht aus (siehe Offene Punkte).
- Live seit dem Neustart 11.11. 15:42 mit Jans Okay (Rundgang 145 Abrufe, alle 200; `/neu/datei` antwortet).

## Technik
- `logik.py`: reine Logik (Baum-Zeilen, Brotkrumen, Ziele zum Verschieben, Dokumente als Ketten über `bezug` mit
  Titel und Marke, Läuft gerade, Dokument-Ansicht, Wartet auf dich, Kosten-Zeilen, Schutz: Origin, Token, sichere
  Weiterleitung). Getestet.
- `dateien.py`: Kopie aus shared/webapp (Pfadprüfung gegen den Agent-Ordner, Vorschau des Renderers
  `<stem>-vorschau/<stem>-seite-NN.png` und `<stem>.pdf`), dazu .md als Download. URLs tragen Auftrag und Nummer in
  `ergebnis_dateien`, nie einen Pfad.
- `app.py`: FastAPI, dünn. Instanz `ARBEITSPLATZ_INSTANZ` (Standard Jans shared-Ordner): `orte.json`,
  `auftraege/`, `fassungen/`. Agent-Ordner = Instanz.parent.
- Ein Dokument ist eine Kette über `bezug`, deren Ursprung `ort` trägt. Titel: `daten.titel` der neuesten fertigen
  Fassung, sonst Dateiname der ersten Ergebnisdatei, sonst „<Art>: <erstes Feld>“.
- `arten.toml`: Format wie im Plan, zusätzlich je Art `material` ("nein" | "optional" Standard | "pflicht"),
  `material_oder = "<Feld>"` (dieses Feld oder eine Datei ist Pflicht, bei pruefung: Transkript) und
  `rueckmeldung = false` (Agent nimmt keine Rückmeldung an: recherche, lernkarten, pruefung laut uni; die
  Dokument-Ansicht in Schritt 4 zeigt dann keinen Knopf „Rückmeldung“), je Feld `hilfe`.
  Felder von Sitzung B (uni, 182498d) und C (dokumente, 6ef033f, e122de8) übernommen; alle neun Arten aktiv
  (praesentation und bericht nach Probeläufen, gemeldet von der koordinierenden Sitzung).
- Uploads: höchstens 10 Dateien, je 50 MB, Endungen pdf, docx, pptx, xlsx, txt, md, png, jpg, vtt, srt, json; liegen kurz in
  `data/eingang/`, agentkit verschiebt sie nach `<agent>/data/eingang/<auftrag>/`.
- Schutz: Origin muss zum Host passen, Formular-Token (geheim je Start), CSP ohne fremde Quellen, no-store.
- `statisch/`: ruhig.css, Schrift, htmx, einmal.js aus shared/webapp kopiert (nicht dort ändern), direkt.js und
  anhang.js nach Lias direkt.js und gespraech.js; `arbeitsplatz.css` mit den Ergänzungen (tiefere Baum-Ebenen,
  Ordnen im „···“, Seitenbilder, Recherche).
- `requirements.txt`: feste Versionen, dieselben Pakete wie shared/webapp ohne webauthn und dessen Abhängigkeiten;
  dazu pypdfium2 und pillow für die Vorschau (Jans Okay 11.11.).
  agentkit per `.venv/lib/python3.12/site-packages/agentkit.pth`.
- Vorlagen wirken sofort auf den laufenden Dienst, Python erst nach Neustart.

## Starten und ansehen
- Dienst `arbeitsplatz.service` (Vorlage `systemd/arbeitsplatz.service`), nur `127.0.0.1:8794`,
  `ARBEITSPLATZ_AUFTRAEGE=echt` seit 17.11.2026 (Jans Okay; gilt für alle Arten). Mit `aus` prüfen Formulare nur.
- Neustart nach Code-Änderung: `systemctl --user restart arbeitsplatz.service`;
  Log: `journalctl --user -u arbeitsplatz.service -n 50`.
- Jan über den Tunnel (Mac): `ssh -N -L 8794:127.0.0.1:8794 agents-user`, dann http://localhost:8794.
- Von Hand ohne Dienst: `.venv/bin/python app.py` (Unix-Socket `data/arbeitsplatz.sock`).
- Von außen: https://uni.meldro.de (Caddy, Passwort wie bisher, Benutzer jan), seit 19.11.2026 auf 8794 statt
  uni/portal (8793). Sicherung: /etc/caddy/Caddyfile.vor-arbeitsplatz. uni-portal läuft nur noch lokal.
- Offen: ansichten.PORTAL zeigt noch auf https://uni.meldro.de, die Portal-Links (Lernkarten übernehmen,
  Übung) landen damit im Arbeitsplatz (404). Jan entscheidet: eigene Adresse fürs Portal oder Umzug.

## Offene Punkte
0. Browser-Probe der ruhigen Oberfläche bei Jan (Tunnel, siehe oben): Titel anklicken (Enter, Esc), „Seite“ im „+“
   (neue Seite gleich offen), „Datei“ im „+“ und Datei auf einen Ort ziehen, Datei aufs Formular und auf ein Dokument
   ziehen, eigene Fassung im „···“, Menüs bei schmalem Fenster, Vorschau und Betrachter, Rückmeldung zu einer Seite,
   Heute nach einer Minute. Ein Bildschirmfoto vom Server geht nicht (dem
   Headless-Chromium fehlen Systembibliotheken).
1. Umzug (09.11. nachts): Orte auf Jans Instanz angelegt: „Forschungsprojekt Fehlstellen“ mit „Exposé“, „Recherche“,
   „Interviews“, „Schriftlicher Teil“; „Modul Holzschutz“; „Finanzen“. Alte Ergebnisse ohne Feld `ort` ordnet
   `shared/orte-zuordnung.json` zu (`{"zuordnung": {ursprung: ort}}`, nicht im Repo, Aufträge bleiben unverändert;
   das Feld `ort` eines Auftrags geht vor). Zugeordnet, weil eindeutig: Exposé-Kette 20261102-165741-uni-ac9dcc ->
   Exposé; finance 4fdc5f, b3c246, fa0f3f -> Finanzen; Zusammenfassung 20261022-225119-dokumente-8e2548
   („Vorlesung Integrierter Holzschutz“) -> Modul Holzschutz. Prüfungsübungen gibt es noch nicht als Aufträge.
   Ohne Ort, weil nicht eindeutig (Jan entscheidet): 20261104-163834-uni-2ee98f (Exposé überarbeiten, eigene Kette),
   20261103-104356-uni-49cf67 (Recherche für Henri zum Forschungsprojekt), 20261106-141103-uni-6e2f35 (Recherche
   Smartphone-Photogrammetrie), 20261027-171320-uni-a4ca81 (Lernblatt Exkursion Holzschutz),
   20261022-082205-uni-f0e6f1 (Transkript Holzschutz aufbereitet), 20261030-150241-uni-a54f6f (Vorlesung Sanierung
   im Holzbau), die Probeläufe von dokumente 20261109-211357-...-a51635 (Präsentation) und -211605-...-c7647f
   (Bericht) sowie alle übrigen Telegram-Aufträge (Mails, Termine, Fragen).
   Zuordnen geht bisher nur über die Datei, nicht in der Oberfläche.
3. `shared/orte.json` und `orte-zuordnung.json` sind nicht im Repo und damit nicht in der nächtlichen Sicherung
   (nur git push). Ins Repo käme die Datei nur über einen Weg wie commit-daten.sh; die Frage legt die koordinierende
   Sitzung Jan am 10.11. vor. Bis dahin kein eigener Sicherungsweg.
5. Recherche am Ort, nächste Schritte (docs/recherche-plan.md 6a, 6b, 7): Plan mit Claude statt Python (Planlauf,
   Absichtserkennung, Bestand am Ort); uni und lia/recherche setzen `ort` beim Schreiben der Projekte (Bedarf in der
   Haupt-STATUS); Verschieben einer Recherche im „···“. „+ → Recherche …“ live seit dem Neustart 17.11. (alle
   Seiten 200); ein echter Lauf darüber steht noch aus. Lias drei Projekte haben keinen Ort (Jans Instanz kennt ihre Reihen nicht), sie stehen auf Heute.
4. Echte Läufe 10.11. ab 15 Uhr: alle Arten außer Exposé, Recherche nur „kurz“ (Jans Entscheidung, siehe Plan).

## Gelernte Regeln
(noch keine)
