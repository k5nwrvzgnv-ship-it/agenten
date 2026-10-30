# Status: Web-App für Lia (shared/webapp)

## Zweck
Überblick für Lia im Browser statt Telegram: was auf sie wartet, was läuft, was fertig ist. Später auch neue Aufträge,
Ergebnisse mit Vorschau, Feedback und Entwürfe. Plan: `../../docs/webapp-plan.md` (4.7 Technik, 7 Bauplan),
Auftrag und Entscheidungen: Punkt 24 in `../../STATUS.md`. Gestaltung „Modernist“ (Board ModHeute im Canvas
https://claude.ai/artifact/F8ysVSyr8TjGhFDcyNnejU).

## Stand (30.10.2026)
Bauschritt 1 und die Ergebnis-/Entwurf-Ansicht (nur lesend) fertig und committet, Aufträge mit Feedback-Schleife
als ein Auftrag mit Verlauf (Jans Anmerkung 30.10.), „Neuer Auftrag“ für Material im Testbetrieb (Jans Okay 30.10.),
Ordnung nach Fach, Klasse und Reihe (Jans Okay 30.10.), `./pruefen.sh` grün (Web-App: 73 Tests).
- Seite „Heute“, nur lesend, ohne Anmeldung, aus `lia/instanz` über agentkit (`auftraege.neue/erledigte`,
  `freigabe.offene`, je mit `basis=`). Die App selbst läuft ohne `AGENTKIT_INSTANZ`.
- Abschnitte: 01 Wartet auf dich (offene Entwürfe, Ergebnisse der letzten 48 h als „Neu“), 02 Läuft gerade,
  03 Fertig (höchstens 10), 04 Hat nicht geklappt (mit dem Grund des Agenten). Leere Abschnitte 03/04 fehlen.
- Ein Auftrag mit Feedback-Schleife ist EIN Auftrag (`logik.ketten`): Ursprung, Lias Rückmeldungen (Agent feedback)
  und Nachbesserungen hängen über `bezug` zusammen, auch Nachbesserungen von Nachbesserungen. „Heute“ zeigt je
  Kette eine Zeile mit Titel und Link des Ursprungs; Zeit, „Neu“ und Abschnitt nach der jüngsten Fassung, Hinweis
  „nach deiner Rückmeldung“. Läuft etwas in der Kette (Nachbesserung oder Rückmeldung), steht sie nur unter
  „Läuft gerade“ („Arbeitet an deiner Rückmeldung“, mit Link auf das bisherige Ergebnis).
- Echter Lauf 30.10. über einen Test-Socket: Theater-Fassung 0baec0 mit Lias Frage und Antwort 5d88d5 als eine
  Zeile; alle 7 Links aus „Heute“ 200, 5d88d5 und 1c1e7e leiten auf 0baec0 um.
- Begriffe aus Lias Sicht: Art aus quelle bzw. Agent (Material, Frage, Woche, Theater, Recherche, Examen), IDs und
  „Runde runde-…“ werden aus Titeln entfernt (Test prüft, dass keine ID und kein Agentenname im HTML steht).
- Zeiten in Europe/Berlin (Sommerzeit beachtet). htmx lädt den Inhalt jede Minute neu (`/teile/heute`).
- Kopfzeilen: CSP nur `'self'`, `no-store`, `nosniff`, kein Referrer; keine API-Doku (`/docs` 404).
- Zeilen in „Heute“ sind Links (außer „Läuft gerade“). IDs stehen nur in der URL, nie im sichtbaren Text.
- Ergebnis `/ergebnis/<id>` (nur abgeschlossene Aufträge der Instanz, ID per pruefe_id, zurückgezogene 404; IDs
  von Nachbesserungen und Rückmeldungen leiten mit 303 auf den Ursprung um): Titel, Art und Zeit der neuesten
  Fassung; „Das Wichtigste“ aus `daten.kern`/`punkte`/`pruefen` der neuesten erledigten Fassung, ohne
  `daten` der ganze Ergebnistext (Zeilen mit „- “ als Liste); Seiten aus `<stem>-vorschau/<stem>-seite-NN.png`
  (Klick öffnet das Bild groß); Dateien mit Knöpfen PDF (aus der Vorschau) und Original (Word/Excel/PowerPoint/PDF).
  Seiten und Dateien aus der jüngsten Fassung mit Dateien („Aus Fassung 1“, wenn die Antwort keine hat).
  Darunter „Verlauf“: Fassung 1, Deine Rückmeldung (Lias Text), Antwort bzw. Fassung n (n zählt nur Fassungen mit
  Dateien), je mit Zeit; frühere Fassungen aufklappbar (`<details>`, Kern, Punkte, Dateien), die oberste „steht
  oben“. Rückmeldung ohne Nachbesserung zeigt die Antwort des Feedback-Agenten. Läuft eine Nachbesserung: Hinweis
  oben; ist die letzte fehlgeschlagen: Hinweis und oben die Fassung davor. Alles fehlgeschlagen: „Hat nicht
  geklappt“ mit Grund. Downloads tragen die ID der Fassung, aus der die Datei stammt.
- Entwurf `/entwurf/<id>` (nur `freigabe.offene` der Instanz): ganzer Text ohne Kürzung, Details nur aus
  `logik.ENTWURF_DETAILS` (bisher „Einsatz“; `daten.datei` ist ein interner Pfad und bleibt verborgen),
  Hinweis „Setzt du selbst ein“. Keine Knöpfe.
- Echter Lauf 30.10.: alle 7 Links aus „Heute“ liefern 200 (5 Ergebnisse, 1 Fehlschlag, examen-0c44bf),
  Downloads und Seitenbilder kommen, falsche Nummern und Pfade 404. Das Dossier der Recherche (PDF) hat keine
  Vorschau (der Renderer hat dafür keine `-vorschau/` angelegt), dort nur der Download.

- Neuer Auftrag `/neu` (Board ModNeu, nur Material: `unterricht`, quelle `portal-material`), standardmäßig AUS.
  `WEBAPP_NEUER_AUFTRAG=test` gilt nur, wenn `WEBAPP_INSTANZ` nicht `lia/instanz` ist; kein Agent startet.
  `=echt`: jede Instanz, danach `systemctl --user start --no-block lia-unterricht.service`; das Ergebnis stellt
  Lias Zentrale auch per Telegram zu, Kosten auf Lias Kontingent. Ist es an, steht oben in „Heute“ der Knopf
  „Neuer Auftrag“, nach dem Abschicken (303 auf `/?abgeschickt=1`) der Hinweis „Dein Auftrag ist unterwegs“.
  Formular ohne JavaScript: Text (Pflicht, bis 5000 Zeichen), Dateien (bis 10, je bis 20 MB, PDF/Word/PowerPoint/
  Excel/JPG/PNG, Namen bereinigt), Hinweis „Bitte keine Namen“; Fehler zeigt das Formular mit Text wieder (400).
  Anlegen über `agentkit.auftraege.neuer_auftrag(..., basis=, agenten_dir=<instanz>/.., absender=PERSON)`;
  Uploads liegen kurz in `data/eingang/` und werden von agentkit nach `<agent>/data/eingang/<id>/` verschoben.
  Schutz ohne Konten: Origin muss zum Host passen (Sec-Fetch-Site same-origin), sonst 403; Token im Formular
  (HMAC, geheim je Start der App), nach einem Neustart „Die Seite war veraltet“. Ohne Zurücknehmen,
  ohne „Das beachte ich“, keine Auswahl der Art (gibt es noch nicht).
- Ordnung nach Fach, Klasse und Reihe (Jans Wunsch und Okay 30.10.):
  - Reihen aus `<instanz>/reihen.toml` (Format in `ordnung.py`: wie lia/unterricht/reihen.toml plus `id`,
    `stand`, `agenten`). Gibt es sie nicht (heute), setzt `ordnung.py` sie zusammen: Reihen aus
    `lia/unterricht/reihen.toml` (Fach aus profil.toml), Examensaufträge zur Reihe aus `examen.toml`
    (`titel_in_reihen_toml`), Theater aus `theater.toml` als Fach „Theater“, „Kurs 11“ (Jan 30.10., steht in
    keiner Datei, `THEATER_KURS`). Kaputte Dateien: Fehler im Log (nur bei Änderung), App zeigt ohne Reihen.
  - Zuordnung (`logik.reihe_von`): Feld `reihe` des Auftrags, sonst der Agent, wenn er in genau einer Reihe unter
    `agenten` steht. Nichts aus dem Text geraten, sonst „ohne Reihe“. Bei Ketten zählt der Ursprung.
    Echte Daten 30.10.: Theater-Fassung 0baec0 -> Theater; Entwurf examen-0c44bf -> Ethik 8 Straftheorien;
    alle Material-Aufträge, Recherche und der Fehlschlag ohne Reihe.
  - „Heute“: Chips Alle, je Fach, je Klasse (nur bei mehreren Klassen eines Fachs), Ohne Reihe, als Links
    `/?ordnung=fach:ethik|gruppe:…|reihe:…|ohne` (unbekannte Werte: alle); htmx lädt mit demselben Filter nach.
    Jede Zeile nennt ihre Reihe. Die Begrüßung zählt alles, was wartet, auch bei Filter. Ohne Reihen keine Chips.
  - `/unterricht` (nur lesend): je Fach, Klasse/Kurs und Reihe Reihenfrage, „Schon behandelt“, offene Entwürfe
    und Aufträge (Marke Offen, Läuft, Hat nicht geklappt), darunter „Ohne Reihe“. Kein Anlegen/Ändern.
  - Neuer Auftrag: Auswahl „Für welche Reihe?“ (laufende Reihen, Standard keine). Der Auftrag trägt `reihe`
    (agentkit, neues optionales Feld) und am Textende „Reihe: Titel (Fach, Klasse)“ für den Agenten.
- Test-Instanz für Jan: `data/test/instanz` (`.env` mit PERSON=Lia, 0600) und Agent-Ordner `data/test/unterricht`,
  nicht im Repo. Probelauf 30.10.: Auftrag mit PDF angelegt, Datei verschoben, ohne Origin 403; danach gelöscht.

## Neuplanung Desktop zuerst (30.10.2026, nur Plan, nichts gebaut)
Auftrag Jan 30.10.: Lia nutzt die App meist am PC; Chips und „Unterricht →“ sind unlogisch. Plan:
`../../docs/webapp-aufbau.md` (Befund, Abdeckung mit Regeln R1–R11, Objektmodell, Zustände Auftrag → Fassungen →
final, Mustertabelle, Heuristik-Review, Test mit 7 Aufgaben, Empfehlung). Klickbares Board „Desktop“ und Board
„Handy-Prüfung“ im Canvas (unten, „Neu 30.10.: Desktop zuerst“). Abdeckung und Testbogen in `data/ia/`
(nicht im Repo).
- Kern: drei Spalten Baum (Fach → Klasse/Kurs → Reihe → Stunde) | Inhalt mit Brotkrumen | Chat „Fragen“ mit dem
  Ort als Kontext. „Heute“ ist oberster Eintrag im Baum. „+ Neu hier“ öffnet eine Vorlagengalerie mit
  vorbelegtem Ort. Material zeigt Fassungen, „Als final markieren“ (nur Lia), „Rückmeldung geben“ (auch mit Datei),
  „Eigene Fassung hochladen“ (Lias echter Weg, löst offenen Punkt 8). Stunde ist leichte, nie verpflichtende Ebene.
- Geklärt (Jan 30.10.): Fach heißt „Darstellendes Spiel“ (App sagt noch „Theater“, `THEATER_KURS` in
  `ordnung.py`; umstellen mit dem ersten Bauschritt), DS-Kurs 12 gibt es (in keiner Datei, Reihen offen),
  Notentabelle gehört zu Ethik 8, Lia nutzt Word, Pages/Keynote und eine Schulplattform: Ausgabe bleibt
  docx/pptx und PDF.
- Jan hat das Desktop-Board am 30.10. durchgeklickt: sieht gut aus, alles klappt. Nächster Schritt: Test mit Lia
  am PC (Plan Abschnitt 6, Bogen `data/ia/testbogen.csv`), Canvas dafür über „Teilen“ freigeben oder an Jans
  Rechner testen. Danach Auswertung hier eintragen, dann Jans Okay für Bauschritt 1 des neuen Aufbaus. Gebaut wird erst nach Test und Jans Okay, in den
  Bauschritten aus Abschnitt 5 des Plans.

## Technik
- `logik.py`: reine Logik (`ketten()`, `heute()`, `ergebnis()`, `verlauf()`, `entwurf()`, Reihen: `reihen_aus()`,
  `reihe_von()`, `filter_chips()`, `unterricht()`), getestet. `ordnung.py`: Reihen-Dateien lesen. `dateien.py`: Pfade der
  Ergebnisdateien und der Vorschau, geprüft gegen den Agent-Ordner `lia/<agent>/` (aufgelöst inkl. Symlinks,
  kein `..`, nichts Verstecktes, nur pdf/docx/pptx/xlsx bzw. png). URLs tragen nur die Nummer in
  `ergebnis_dateien`, nie einen Pfad. `app.py`: FastAPI, dünn, Uvicorn auf Unix-Socket
  `data/webapp.sock` (Ordner 0700; Uvicorn setzt den Socket selbst auf 0666, der Ordner schützt).
- `vorlagen/heute.html` (Seite), `vorlagen/_heute.html` (Inhalt, auch für htmx), `_zeile.html` (Zeile für Heute
  und Unterricht), `unterricht.html`, `vorlagen/basis.html` (Kopf mit
  Zurück für Einzelansichten), `ergebnis.html`, `entwurf.html`, `statisch/stil.css`. 404 als lesbare Seite.
- `statisch/htmx-2.0.4.min.js` mit `.sha256` (von unpkg und jsdelivr geladen, beide gleich; Test prüft die Summe).
- `requirements.txt`: feste Versionen (pip freeze) von fastapi, uvicorn (ohne [standard]), jinja2,
  python-multipart, webauthn samt Abhängigkeiten. agentkit per `.venv/.../agentkit.pth`.
- Tests ohne httpx (nicht freigegeben): echter Uvicorn auf einem Socket im Temp-Ordner, Anfragen mit http.client.

## Starten und ansehen (zum Test, kein Dienst)
Auf dem Server (vom Mac aus `ssh agents-user`): `cd ~/agenten/shared/webapp && .venv/bin/python app.py` (Strg+C beendet).
Mit „Neuer Auftrag“ im Testbetrieb: `cd ~/agenten/shared/webapp && WEBAPP_INSTANZ=$PWD/data/test/instanz
WEBAPP_NEUER_AUFTRAG=test .venv/bin/python app.py` (zeigt dann die Test-Instanz, nicht Lias Aufträge).
Auf Jans Mac (Kurzname aus seiner ~/.ssh/config): `ssh -N -L 8792:/home/agent/agenten/shared/webapp/data/webapp.sock agents-user`, dann
http://localhost:8792. Nach einer Code-Änderung die laufende App mit Strg+C beenden und neu starten. Andere Instanz: `WEBAPP_INSTANZ=/pfad`, anderer Socket: `WEBAPP_SOCKET=/pfad`.
Nach Strg+C bzw. kill bleibt die leere Socket-Datei liegen; der nächste Start löscht sie.

## Entscheidungen
- Jan 30.10.: Design von „Heute“ passt (im Tunnel angesehen). Nächster Schritt vorgezogen vor die Konten:
  Ergebnis- und Entwurf-Ansicht nur lesend (Klick aus „Heute“), Knöpfe mit Wirkung erst danach. Lia bekommt
  ohnehin erst nach K1, K3 und Jans Okay zum Dienst Zugang; bis dahin nur Jans Tunnel.

## Offene Punkte
0. Neuer Auftrag echt (`WEBAPP_NEUER_AUFTRAG=echt` auf lia/instanz): erst mit Bauschritt 2 (Konten) und Jans
   Okay. Theater als Art erst, wenn der Theater-Agent neue Aufträge annimmt (bisher nur Nachbesserungen, neue
   Runden mit `runde.py` von Hand; Bedarf an den lia/theater-Chat). Zurücknehmen (10 s) fehlt noch.
9. Reihen: lia/instanz/reihen.toml legt der lia/unterricht-Chat an (Bedarf in Punkt 24 der Haupt-STATUS); bis
   dahin der Ersatz aus den Agent-Ordnern. Pflege durch Lia in der App (Neue Reihe, Behandeltes ergänzen) und
   „Reihe zuordnen“ für alte Aufträge (schreibt in Lias Instanz) erst mit Konten. Weitere Klassen von Lia sind
   nicht bekannt; Jan trägt sie ein, sobald Lia sie nennt.
8. Aufträge, die inhaltlich eine neue Fassung sind, aber als neuer Material-Auftrag mit Datei kamen (93e29e,
   03b145 zur Theater-Fassung), haben kein `bezug` und stehen einzeln. Nicht geraten; Jan gefragt, ob so etwas
   zusammengehören soll (sauber wäre ein Änderungswunsch mit Datei aus der Ergebnis-Ansicht, Bauschritt 4).
1. Dienst `webapp.service` (User-Unit mit OnFailure=ausfall@%n.service, MemoryMax=300M, Startgrenze): braucht
   Jans Okay (Bauplan Schritt 7). Bis dahin nur von Hand starten.
2. Bauschritt 2: Konten (SQLite), Einladungslink, Passkey auf localhost, Sitzung, Mandant aus der Sitzung.
3. „Neu“ ist bisher nur „in den letzten 48 h fertig“. Mit Konten: gesehen/ungelesen je Ergebnis.
4. Ergebnis und Entwurf nur lesend: keine Feedback-Knöpfe (Bauschritt 3), kein Abschließen/Ändern/Ablehnen
   (Bauschritt 5), keine Anmerkungen an einer Stelle. Fassungen stehen im Verlauf (keine Chips). Keine
   Leiste mit Bereichen, kein Fortschrittsbalken: gibt es noch nicht.
7. Kern-Texte aus Telegram sagen „antworte direkt auf diese Nachricht“. In der Web-App passt das erst mit den
   Feedback-Knöpfen; bis dahin bleibt der Text, wie der Agent ihn geschrieben hat.
5. Schrift: Inter/Inter Tight werden nur genutzt, wenn sie auf dem Gerät sind (sonst Helvetica/Arial). Google Fonts
   bewusst nicht (Lias Gerät soll nur mit dem Server sprechen). Schriftdateien lokal ausliefern: Jan fragen
   (Lizenz OFL, Dateien ins Repo wie htmx).
6. „Hat nicht geklappt“ zeigt auch alte Fehlschläge (22.10.) ohne Ablaufdatum. Ob sie nach einer Zeit verschwinden
   sollen, mit Lia klären.

## Gelernte Regeln
(noch keine)
