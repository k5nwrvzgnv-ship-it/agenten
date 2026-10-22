# Status: Agent unterricht (Lias Instanz)

## Zweck
Material auf Zuruf für Lia (docs/lia-architektur.md, Schritt 1): Lia tippt in ihrer Zentrale „Neues Material“,
beschreibt ihren Wunsch und bekommt ein Arbeitsblatt (docx) oder Folien (pptx) in ihrem Stil mit Begleittext.
Woche und Frage sind noch Platzhalter („kommt bald“, ohne Claude).

## Stand (22.10.2026)
- Material läuft (Code fertig, Tests grün, Dienst eingerichtet). Noch kein Auftrag von Lia über Telegram.
- Echter Lauf 22.10. (direkt mit material.bearbeiten, ohne Warteschlange, damit Lia nichts bekam):
  „Arbeitsblatt kategorischer Imperativ, Klasse 10, 45 min“ mit Opus: 2 Claude-Läufe, 90 s, 129.430 Tokens,
  umgerechnet 0,61 USD (Pro-Abo, also nur Kontingent). Beschreibung gleich gültig; in der Kontrolle sah Claude
  den Überlauf auf eine 4. Seite und kürzte, Python baute neu (3 Seiten: Merksatz, Text, Fälle, 5 Aufgaben mit
  Satzanfängen und Hilfen, Tabelle quer). Inhalt fachlich ordentlich, Jan hat die Datei noch nicht angesehen:
  data/arbeit/20261022-231000-unterricht-a1b2c3/.
- Folien sind nur mit Tests geprüft, noch nicht im echten Lauf.

## Ablauf (material.py)
1. Prompt = Lias Wunsch + skills/einzelmaterial/SKILL.md + Abschnitte Allgemein/Arbeitsblatt/Folien aus
   shared/renderer/FORMAT.md (zur Laufzeit gelesen, bleibt aktuell). Claude schreibt mit Write
   data/arbeit/<auftrag>/beschreibung.json.
2. Python baut mit renderer.bauen (Profil profil.toml). Fehler (Datei fehlt, kein JSON, falsche art,
   BeschreibungUngueltig) gehen in derselben Sitzung an Claude zurück, höchstens 3 Korrekturen.
3. Kontrolle: Claude sieht Kontrolltext und Vorschau-PNGs. Ändert Claude die Beschreibung, baut Python neu
   (eine Kontrollrunde, die neue Vorschau sieht Claude nicht mehr).
4. Claudes letzte Antwort ist der Begleittext, die Datei geht über auftraege.abschliessen(..., dateien=).
- Opus (art="anspruchsvoll"), Zeitbudget 18 min für neue Läufe, Dienst-Timeout 25 min.
- Fehler: Lia bekommt „nicht erstellen, Jan ist informiert“ (ihre Zentrale zeigt bei fehlgeschlagen
  ohnehin ihren eigenen Text), Jan eine Meldung in seiner Zentrale (jan_melden, Jans shared/meldungen).
  Kontingent erschöpft: ebenso, mit Uhrzeit im Ergebnis. Unerwartete Fehler: dasselbe, der Dienst läuft weiter.
- Dateiname aus art und titel (Arbeitsblatt <Titel>.docx), am Wortende auf 60 Zeichen gekürzt.

## Aufbau
- Instanz: AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz (Warteschlangen, Regeln, .env dort)
- Code: agent.py (Verteilung nach quelle, Fehler, Meldung an Jan), material.py (Ablauf, ohne Netz testbar)
- Skill: skills/einzelmaterial/SKILL.md (Version 1, Art wählen, Qualitätskriterien). Version steht in material.py.
- Profil: profil.toml (Kopie von shared/renderer/beispiele/profil-lia-stil.toml, Ethik, Frau Pohlmann)
- .venv: Pakete aus requirements.txt (Versionen wie shared/renderer), agentkit und renderer per agentkit.pth
- Dienst: lia-unterricht.service (oneshot, Vorlage systemd/, MemoryMax 1500M), gestartet von Lias Zentrale.
  Nach Änderung: Vorlage nach ~/.config/systemd/user/ kopieren, systemctl --user daemon-reload.
- Laufzeitdaten: data/arbeit/<auftrag>/ (Beschreibung, Datei, Vorschau), Logs: logs/ (beide nicht im Repo)
- Kosten je Auftrag: logs/ (Zeile „fertig: ... USD, Tokens“) und shared/verbrauch/ (instanz lia).

## Entscheidungen (Jan, 22.10.2026)
- Der Agent löst den Platzhalter unterricht ab (Weg material), kein eigener Agent; portal_logik bleibt unverändert.
- Fach Ethik, Lehrkraft Frau Pohlmann. Modell Opus.
- Formate docx und pptx, keine PDF-Ausgabe an Lia (Renderer-Entscheidung).

## Offene Punkte
1. Handtest: Lia tippt „Neues Material“ und schickt einen Wunsch, einmal Arbeitsblatt, einmal Folien.
2. Wünsche nach Änderung („mach Aufgabe 3 leichter“): Lias Zentrale kennt noch keine Antwort auf ein Ergebnis.
   Dann Sitzung fortsetzen (Feld sitzung ist gespeichert) und Beschreibung überarbeiten lassen.
3. Lias Vorlage nutzen (data/vorlagen/, renderer vorlage=), sobald die Zentrale Dateien annimmt.
4. Ausbau des Skills nach Architektur 2.5 (beispiele/, evals/), sobald Lia Ergebnisse abgenommen hat.
5. Woche und Frage: noch Platzhalter.

## Gelernte Regeln
- (noch keine)
