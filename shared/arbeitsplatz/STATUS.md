# Arbeitsplatz – Stand

## Zweck
Neutrale Web-Oberfläche über Jans Agenten (uni, dokumente, finance): freier Baum aus Orten, Dokumentarten aus
`arten.toml`, Dokumente mit Fassungen und Rückmeldung. Plan und verbindliche Schnittstellen:
`../../docs/arbeitsplatz-plan.md` (Jans Okay 09.11.2026). Gebaut im Hauptordner-Chat (Sitzung A).
Lias App `shared/webapp` ist Muster und Quelle (CSS, Schrift, htmx kopiert), wird nicht verändert.
`uni/portal` bleibt bis zur Abnahme unverändert.

## Stand (09.11.2026, abends)
Schritte 1 bis 3 aus dem Auftrag an Sitzung A:
- agentkit: `neuer_auftrag(..., art=, felder=)`; Nachbesserungen des Feedback-Dienstes erben `ort`, `art`, `felder`,
  wenn der Ursprung eine `art` hat (`auftraege.herkunft_erben`, Lia unverändert).
- agentkit: `orte` (Baum in `<instanz>/orte.json`, Sperre, Rückgängig über `<instanz>/orte-aktionen.json`) und
  `arten` (liest und prüft `arten.toml`, Formular prüfen, Auftragstext).
- App: Rahmen drei Spalten (Baum | Seite | Läuft gerade), Baum mit „+ Seite“ (unter dem aktiven Ort und oben),
  Ort-Seite mit Dokumenten, Unterseiten (↑/↓), „+ Seite“, Umbenennen, Verschieben, Archivieren; Archiv mit
  Wiederherstellen; Hinweis mit Rückgängig nach jeder Änderung; „+ Neu“ öffnet die Galerie der aktiven Arten, das
  Formular legt den Auftrag an (`quelle="arbeitsplatz"`, ort, art, felder, Dateien) und startet
  `<agent>.service` mit `systemctl --user start --no-block`. Doppelklick legt nichts doppelt an.
- Dokument-Seite `/dokument/<ursprung>`: erste, nur lesende Fassung (Fassungen mit Stand, Kern, Dateinamen).
- Tests: `tests/` (Logik, App über Unix-Socket mit http.client), in pruefen.sh eingetragen.

Noch nicht gebaut (Schritt 4, ab 10.11. morgens): Dokument-Ansicht mit Seitenbildern, PDF und Original, Rückmeldung
Text/Datei, eigene Fassung, final (agentkit.fassungen), „Heute“ mit „wartet auf mich“, Kosten aus agentkit.verbrauch;
finance `daten.titel` und `art`. Schritt 5 (Umzug aus uni/portal) erst nach Rücksprache mit der uni-Sitzung.

## Technik
- `logik.py`: reine Logik (Baum-Zeilen, Brotkrumen, Ziele zum Verschieben, Dokumente als Ketten über `bezug` mit
  Titel und Marke, Läuft gerade, Schutz: Origin, Token, sichere Weiterleitung). Getestet.
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
- `statisch/`: stil.css, Schrift, htmx, einmal.js aus shared/webapp kopiert (nicht dort ändern);
  `arbeitsplatz.css` mit den Ergänzungen (tiefere Baum-Ebenen usw.).
- `requirements.txt`: feste Versionen, dieselben Pakete wie shared/webapp ohne webauthn und dessen Abhängigkeiten.
  agentkit per `.venv/lib/python3.12/site-packages/agentkit.pth`.
- Vorlagen wirken sofort auf den laufenden Dienst, Python erst nach Neustart.

## Starten und ansehen
- Dienst `arbeitsplatz.service` (Vorlage `systemd/arbeitsplatz.service`), nur `127.0.0.1:8794`,
  `ARBEITSPLATZ_AUFTRAEGE=aus` (Formular prüft, legt nichts an). Echt mit `ARBEITSPLATZ_AUFTRAEGE=echt` in der Unit.
- Neustart nach Code-Änderung: `systemctl --user restart arbeitsplatz.service`;
  Log: `journalctl --user -u arbeitsplatz.service -n 50`.
- Jan über den Tunnel (Mac): `ssh -N -L 8794:127.0.0.1:8794 agents-user`, dann http://localhost:8794.
- Von Hand ohne Dienst: `.venv/bin/python app.py` (Unix-Socket `data/arbeitsplatz.sock`).
- Caddy (von außen mit Passwort) macht Jan als root nach der Abnahme.

## Offene Punkte
1. Schritt 4 und 5 (siehe oben).
2. Orte liegen in `shared/orte.json` (nicht im Repo, wie die Aufträge). Sicherung prüfen.

## Gelernte Regeln
(noch keine)
