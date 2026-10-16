# Status: Agent dokumente

## Zweck
Word-, PowerPoint- und Excel-Dateien für Jan erstellen und bearbeiten: Anträge, Berichte,
Präsentationen, Tabellen. Sauber formatiert, auf Wunsch auf Jans Vorlagen.

## Stand (17.10.2026)
- Gerüst aus dem Hauptordner-Chat: .venv mit agentkit und python-docx 1.2.0, python-pptx 1.0.2,
  openpyxl 3.1.5 (dieselben Versionen wie uni, Stand in requirements.txt), Umgebungstest in tests/,
  Eintrag in ../pruefen.sh, Dienstdatei systemd/dokumente.service (noch nicht eingerichtet).
- Noch kein agent.py. Aufträge an /dokumente bleiben bis dahin in shared/auftraege/neu/ liegen.
- Keine Zugangsdaten nötig, daher keine .env.

## Anforderungen (Jan, 17.10.)
- Bauweise: Claude schreibt eine Beschreibung des Dokuments (z. B. JSON: Überschriften, Absätze,
  Listen, Tabellen, Bilder, Folien, Blätter mit Formeln). Python prüft sie und baut daraus die Datei.
  Claude führt nie Code aus (claude_lauf ohne Bash). Das Format der Beschreibung legt dieser Chat fest.
  Fehler beim Bauen gehen an Claude zurück (Sitzung fortsetzen), nicht still verschlucken.
- Vorlagen: Jan schickt seine Vorlagen per Telegram (z. B. Datei mit "/dokumente Vorlage Briefkopf").
  Ablage unter data/vorlagen/. Neue Dokumente bauen auf deren Stilen bzw. Folienmastern auf.
  Hinweis: python-docx öffnet .dotx und python-pptx .potx nicht direkt (anderer Inhaltstyp), sie
  müssen beim Ablegen in .docx/.pptx umgewandelt werden.
- Bearbeiten: Jan schickt eine bestehende Datei mit Auftrag. Das Original bleibt unverändert, das
  Ergebnis ist eine neue Datei (z. B. <name>-bearbeitet.docx).
- Rückweg: Ergebnisdateien nach data/ausgang/<auftrag-id>/ legen und
  `auftraege.abschliessen(..., dateien=[...])` übergeben. Die Zentrale schickt sie Jan nach dem
  Ergebnistext (bis 50 MB, nur Dateien im Agent-Ordner, nichts Verstecktes).
- Ein Dokument an Jan zu schicken ist kein Handeln nach außen, braucht also keine Freigabe.
  Weitergabe an andere macht Jan selbst.
- Grenzen ohne LibreOffice (kein sudo): kein PDF-Export, keine alten Formate doc/ppt/xls, keine
  Vorschau. Claude sieht das Ergebnis nicht: Python sollte eine Textfassung des fertigen Dokuments
  zur Selbstkontrolle erzeugen.

## Aufbau
- Code: dokumente/agent.py (Einstieg, Vorlage ../shared/vorlagen/agent_beispiel.py), weitere Module
- .venv: dokumente/.venv, agentkit per .pth eingebunden
- Dienst: dokumente.service (oneshot, arbeitet Aufträge ab), kein Timer
- Laufzeitdaten: dokumente/data/ (eingang/, ausgang/, vorlagen/), Logs: dokumente/logs/ (beide nicht
  im Repo), protokolle/ ebenfalls nicht im Repo
- Tests: `.venv/bin/python -m unittest discover -s tests -t .`

## Entscheidungen
- 17.10.: Beschreibung + Python statt von Claude geschriebener Skripte (Jan; "Claude denkt, Python handelt").

## Offene Punkte
1. agent.py: Aufträge abarbeiten, Beschreibungsformat, Bauen für docx, pptx, xlsx, Tests.
2. Vorlagen annehmen und verwenden, bestehende Dateien bearbeiten.
3. Wenn agent.py läuft: Dienst einrichten (Befehl oben in systemd/dokumente.service).
4. Dateien von Jan lesen: Claude liest PDF, Bilder und Text direkt, aber nicht docx/pptx/xlsx.
   uni hat dafür kurse.als_text(). Nicht kopieren: im Hauptordner-Chat nach agentkit verschieben lassen
   (Bedarf in ../STATUS.md eingetragen).

## Gelernte Regeln
- (noch keine)
