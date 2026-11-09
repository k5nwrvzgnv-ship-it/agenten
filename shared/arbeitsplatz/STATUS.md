# Arbeitsplatz – Stand

## Zweck
Neutrale Web-Oberfläche über Jans Agenten (uni, dokumente, finance): freier Baum aus Orten, Dokumentarten aus
`arten.toml`, Dokumente mit Fassungen und Rückmeldung. Plan und verbindliche Schnittstellen:
`../../docs/arbeitsplatz-plan.md` (Jans Okay 09.11.2026). Gebaut im Hauptordner-Chat (Sitzung A).
Lias App `shared/webapp` ist Muster und Quelle (CSS, Schrift, htmx kopiert), wird nicht verändert.
`uni/portal` bleibt bis zur Abnahme unverändert.

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
- finance: Aufträge nach `art` und Feld Thema, Ergebnis mit `daten.titel` (siehe finance/STATUS.md).
- Tests: `tests/` (Logik, Ansichten, App über Unix-Socket mit http.client), in pruefen.sh eingetragen.

„Wartet auf dich“ kennt kein „gesehen“; ein Dokument steht dort, bis es final ist oder 14 Tage alt.

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
2. ARBEITSPLATZ_AUFTRAEGE bleibt bis zu den echten Läufen aus.
3. `shared/orte.json` und `orte-zuordnung.json` sind nicht im Repo und damit nicht in der nächtlichen Sicherung
   (nur git push). Ins Repo käme die Datei nur über einen Weg wie commit-daten.sh; die Frage legt die koordinierende
   Sitzung Jan am 10.11. vor. Bis dahin kein eigener Sicherungsweg.
4. Echte Läufe 10.11. ab 15 Uhr: alle Arten außer Exposé, Recherche nur „kurz“ (Jans Entscheidung, siehe Plan).

## Gelernte Regeln
(noch keine)
