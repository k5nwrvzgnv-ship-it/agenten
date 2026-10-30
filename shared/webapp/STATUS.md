# Status: Web-App für Lia (shared/webapp)

## Zweck
Überblick für Lia im Browser statt Telegram: was auf sie wartet, was läuft, was fertig ist. Später auch neue Aufträge,
Ergebnisse mit Vorschau, Feedback und Entwürfe. Plan: `../../docs/webapp-plan.md` (4.7 Technik, 7 Bauplan),
Auftrag und Entscheidungen: Punkt 24 in `../../STATUS.md`. Gestaltung „Modernist“ (Board ModHeute im Canvas
https://claude.ai/artifact/F8ysVSyr8TjGhFDcyNnejU).

## Stand (30.10.2026)
Bauschritt 1 und die Ergebnis-/Entwurf-Ansicht (nur lesend) fertig und committet, `./pruefen.sh` grün
(Web-App: 38 Tests).
- Seite „Heute“, nur lesend, ohne Anmeldung, aus `lia/instanz` über agentkit (`auftraege.neue/erledigte`,
  `freigabe.offene`, je mit `basis=`). Die App selbst läuft ohne `AGENTKIT_INSTANZ`.
- Abschnitte: 01 Wartet auf dich (offene Entwürfe, Ergebnisse der letzten 48 h als „Neu“), 02 Läuft gerade,
  03 Fertig (höchstens 10), 04 Hat nicht geklappt (mit dem Grund des Agenten). Leere Abschnitte 03/04 fehlen.
- Echter Lauf 30.10. über den Socket: 7 Aufträge und examen-0c44bf richtig eingeteilt (5 warten, 1 fertig,
  1 fehlgeschlagen; der Feedback-Auftrag erscheint nicht selbst, sondern als „Antwort auf deine Rückmeldung zu …“).
- Begriffe aus Lias Sicht: Art aus quelle bzw. Agent (Material, Frage, Woche, Theater, Recherche, Examen), IDs und
  „Runde runde-…“ werden aus Titeln entfernt (Test prüft, dass keine ID und kein Agentenname im HTML steht).
- Zeiten in Europe/Berlin (Sommerzeit beachtet). htmx lädt den Inhalt jede Minute neu (`/teile/heute`).
- Kopfzeilen: CSP nur `'self'`, `no-store`, `nosniff`, kein Referrer; keine API-Doku (`/docs` 404).
- Zeilen in „Heute“ sind Links (außer „Läuft gerade“). IDs stehen nur in der URL, nie im sichtbaren Text.
- Ergebnis `/ergebnis/<id>` (nur abgeschlossene Aufträge der Instanz, ID per pruefe_id, Feedback-Bestätigungen
  und zurückgezogene 404): Titel, Art und Zeit; „Das Wichtigste“ aus `daten.kern`/`punkte`/`pruefen`, ohne
  `daten` der ganze Ergebnistext (Zeilen mit „- “ als Liste); Seiten aus `<stem>-vorschau/<stem>-seite-NN.png`
  (Klick öffnet das Bild groß); Dateien mit Knöpfen PDF (aus der Vorschau) und Original (Word/Excel/PowerPoint/PDF).
  Nachbesserung: Lias Rückmeldung (aus dem Feedback-Fall, `daten.nachbesserung`) und Link zum ursprünglichen
  Ergebnis; das ursprüngliche zeigt „Später dazu“. Fehlgeschlagen: „Hat nicht geklappt“ mit Grund.
- Entwurf `/entwurf/<id>` (nur `freigabe.offene` der Instanz): ganzer Text ohne Kürzung, Details nur aus
  `logik.ENTWURF_DETAILS` (bisher „Einsatz“; `daten.datei` ist ein interner Pfad und bleibt verborgen),
  Hinweis „Setzt du selbst ein“. Keine Knöpfe.
- Echter Lauf 30.10.: alle 7 Links aus „Heute“ liefern 200 (5 Ergebnisse, 1 Fehlschlag, examen-0c44bf),
  Downloads und Seitenbilder kommen, falsche Nummern und Pfade 404. Das Dossier der Recherche (PDF) hat keine
  Vorschau (der Renderer hat dafür keine `-vorschau/` angelegt), dort nur der Download.

## Technik
- `logik.py`: reine Logik (`heute()`, `ergebnis()`, `entwurf()`), getestet. `dateien.py`: Pfade der
  Ergebnisdateien und der Vorschau, geprüft gegen den Agent-Ordner `lia/<agent>/` (aufgelöst inkl. Symlinks,
  kein `..`, nichts Verstecktes, nur pdf/docx/pptx/xlsx bzw. png). URLs tragen nur die Nummer in
  `ergebnis_dateien`, nie einen Pfad. `app.py`: FastAPI, dünn, Uvicorn auf Unix-Socket
  `data/webapp.sock` (Ordner 0700; Uvicorn setzt den Socket selbst auf 0666, der Ordner schützt).
- `vorlagen/heute.html` (Seite), `vorlagen/_heute.html` (Inhalt, auch für htmx), `vorlagen/basis.html` (Kopf mit
  Zurück für Einzelansichten), `ergebnis.html`, `entwurf.html`, `statisch/stil.css`. 404 als lesbare Seite.
- `statisch/htmx-2.0.4.min.js` mit `.sha256` (von unpkg und jsdelivr geladen, beide gleich; Test prüft die Summe).
- `requirements.txt`: feste Versionen (pip freeze) von fastapi, uvicorn (ohne [standard]), jinja2,
  python-multipart, webauthn samt Abhängigkeiten. agentkit per `.venv/.../agentkit.pth`.
- Tests ohne httpx (nicht freigegeben): echter Uvicorn auf einem Socket im Temp-Ordner, Anfragen mit http.client.

## Starten und ansehen (zum Test, kein Dienst)
Auf dem Server (vom Mac aus `ssh agents-user`): `cd ~/agenten/shared/webapp && .venv/bin/python app.py` (Strg+C beendet).
Auf Jans Mac (Kurzname aus seiner ~/.ssh/config): `ssh -N -L 8792:/home/agent/agenten/shared/webapp/data/webapp.sock agents-user`, dann
http://localhost:8792. Nach einer Code-Änderung die laufende App mit Strg+C beenden und neu starten. Andere Instanz: `WEBAPP_INSTANZ=/pfad`, anderer Socket: `WEBAPP_SOCKET=/pfad`.
Nach Strg+C bzw. kill bleibt die leere Socket-Datei liegen; der nächste Start löscht sie.

## Entscheidungen
- Jan 30.10.: Design von „Heute“ passt (im Tunnel angesehen). Nächster Schritt vorgezogen vor die Konten:
  Ergebnis- und Entwurf-Ansicht nur lesend (Klick aus „Heute“), Knöpfe mit Wirkung erst danach. Lia bekommt
  ohnehin erst nach K1, K3 und Jans Okay zum Dienst Zugang; bis dahin nur Jans Tunnel.

## Offene Punkte
1. Dienst `webapp.service` (User-Unit mit OnFailure=ausfall@%n.service, MemoryMax=300M, Startgrenze): braucht
   Jans Okay (Bauplan Schritt 7). Bis dahin nur von Hand starten.
2. Bauschritt 2: Konten (SQLite), Einladungslink, Passkey auf localhost, Sitzung, Mandant aus der Sitzung.
3. „Neu“ ist bisher nur „in den letzten 48 h fertig“. Mit Konten: gesehen/ungelesen je Ergebnis.
4. Ergebnis und Entwurf nur lesend: keine Feedback-Knöpfe (Bauschritt 3), kein Abschließen/Ändern/Ablehnen
   (Bauschritt 5), keine Fassungs-Chips, keine Anmerkungen an einer Stelle. Kein Knopf „Neuer Auftrag“, keine
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
