# Status: Web-App für Lia (shared/webapp)

## Zweck
Überblick für Lia im Browser statt Telegram: was auf sie wartet, was läuft, was fertig ist. Später auch neue Aufträge,
Ergebnisse mit Vorschau, Feedback und Entwürfe. Plan: `../../docs/webapp-plan.md` (4.7 Technik, 7 Bauplan),
Auftrag und Entscheidungen: Punkt 24 in `../../STATUS.md`. Gestaltung „Modernist“ (Board ModHeute im Canvas
https://claude.ai/artifact/F8ysVSyr8TjGhFDcyNnejU).

## Stand (30.10.2026)
Bauschritt 1 fertig und committet, `./pruefen.sh` grün (Web-App: 18 Tests).
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

## Technik
- `logik.py`: reine Logik (`heute()`), getestet. `app.py`: FastAPI, dünn, Uvicorn auf Unix-Socket
  `data/webapp.sock` (Ordner 0700; Uvicorn setzt den Socket selbst auf 0666, der Ordner schützt).
- `vorlagen/heute.html` (Seite), `vorlagen/_heute.html` (Inhalt, auch für htmx), `statisch/stil.css`.
- `statisch/htmx-2.0.4.min.js` mit `.sha256` (von unpkg und jsdelivr geladen, beide gleich; Test prüft die Summe).
- `requirements.txt`: feste Versionen (pip freeze) von fastapi, uvicorn (ohne [standard]), jinja2,
  python-multipart, webauthn samt Abhängigkeiten. agentkit per `.venv/.../agentkit.pth`.
- Tests ohne httpx (nicht freigegeben): echter Uvicorn auf einem Socket im Temp-Ordner, Anfragen mit http.client.

## Starten und ansehen (zum Test, kein Dienst)
Auf dem Server: `cd ~/agenten/shared/webapp && .venv/bin/python app.py` (Strg+C beendet).
Auf Jans Rechner: `ssh -N -L 8792:/home/agent/agenten/shared/webapp/data/webapp.sock agent@<server>`, dann
http://localhost:8792. Andere Instanz: `WEBAPP_INSTANZ=/pfad`, anderer Socket: `WEBAPP_SOCKET=/pfad`.
Nach Strg+C bzw. kill bleibt die leere Socket-Datei liegen; der nächste Start löscht sie.

## Offene Punkte
1. Dienst `webapp.service` (User-Unit mit OnFailure=ausfall@%n.service, MemoryMax=300M, Startgrenze): braucht
   Jans Okay (Bauplan Schritt 7). Bis dahin nur von Hand starten.
2. Bauschritt 2: Konten (SQLite), Einladungslink, Passkey auf localhost, Sitzung, Mandant aus der Sitzung.
3. „Neu“ ist bisher nur „in den letzten 48 h fertig“. Mit Konten: gesehen/ungelesen je Ergebnis.
4. Zeilen sind noch keine Links (Ergebnis-Ansicht ist Bauschritt 3, Entwurf abschließen Bauschritt 5). Kein Knopf
   „Neuer Auftrag“, keine Leiste mit Bereichen, kein Fortschrittsbalken: gibt es noch nicht.
5. Schrift: Inter/Inter Tight werden nur genutzt, wenn sie auf dem Gerät sind (sonst Helvetica/Arial). Google Fonts
   bewusst nicht (Lias Gerät soll nur mit dem Server sprechen). Schriftdateien lokal ausliefern: Jan fragen
   (Lizenz OFL, Dateien ins Repo wie htmx).
6. „Hat nicht geklappt“ zeigt auch alte Fehlschläge (22.10.) ohne Ablaufdatum. Ob sie nach einer Zeit verschwinden
   sollen, mit Lia klären.

## Gelernte Regeln
(noch keine)
