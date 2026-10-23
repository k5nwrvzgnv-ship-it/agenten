# Status: Werkzeug auswertung (Lias Instanz)

## Zweck
Aus Lias Chats in claude.ai (über Jans Konto) ableiten, welche wiederkehrenden Aufgaben sich für ihre
Agenten lohnen und wie gut die Agenten sie lösen müssen. Ergebnis: Rangliste, Beispiele, Prüfsatz und
Regelvorschläge für lia/unterricht bzw. neue Agenten. Kein Agent: Jan startet es von Hand.

## Stand (23.10.2026)
- Schritt 1 erledigt: Gerüst (.venv ohne Pakete, agentkit per .pth, ablage.py mit Tests, Eintrag in pruefen.sh).
- Schritt 2 erledigt: Lia hat am 23.10.2026 der Erklärung in einwilligung.md ohne Einschränkungen
  zugestimmt (mündlich an Jan, Jan hat es im Chat weitergegeben).
- Schritt 3 vorbereitet: anleitung-export.md (für Jan), Befehle entpacken und struktur. Export fehlt noch.
- Schritt 4 vorbereitet: Befehl chatliste (Vorschlag Lia/Jan/unklar nach Stichwörtern, nur Titel).
  Mit einem Kunst-Export durchgespielt.
- Schritt 3 erledigt (23.10.): Export in data/export/ (conversations, projects, light_metadata; memories-ZIP
  liegt ungeöffnet im Upload-Ordner der App). Befund conversations.json:
  - 247 Chats, 5.687 Nachrichten, nur 26.07.–23.10.2026 (Projekte reichen bis April zurück: ältere Chats
    fehlen im Export oder wurden gelöscht, ungeklärt).
  - Felder je Chat: uuid, name, summary, created_at, updated_at, account, chat_messages. Je Nachricht: uuid,
    sender (human/assistant), text, content[] (Typen text, thinking, tool_use, tool_result, document, image,
    injected_prompt_block), files[] (nur Name und uuid, kein Inhalt), attachments[] (mit extracted_content),
    parent_message_uuid (Wurzel 00000000-0000-4000-8000-000000000000).
  - Text steht in .text, bei 912 Nachrichten nur in content[] (auswahl.nachricht_text).
  - Bearbeitete Prompts: enthalten, 7 Stellen in 6 Chats, alle Äste mit Antwort.
    Verworfene (neu erzeugte) Antworten: keine Geschwister unter Assistent-Antworten, also nicht enthalten.
  - 25 Chats ohne Titel sind komplett leer (760 Nachrichten ohne Text): wer = leer.
  - Kein Feld, das einen Chat einem Projekt zuordnet. projects: 25 Projekte (name, description,
    prompt_template, docs[].content), eindeutig Lias nur „Lia Schule“.
  - light_metadata: users.json, login_history.json (IP-Adressen, nicht nötig, Löschung vorgeschlagen).
- Schritt 4 erledigt (23.10.): 27 Chats von Lia nach data/lia/chats.json, dazu Projekt „Lia Schule“
  (Unterrichtsbesuch DS, 2 Dokumente) nach data/lia/projekte/. Alle übrigen Chats und Projekte gelöscht,
  data/chatliste.tsv enthält nur noch Lias 27 Zeilen.
  Entscheidungen: privat = Haushalt, Familie, Gesundheit (auch Lias Verbeamtung/Amtsarzt), Psychotherapie,
  Beihilfe (Jan) – egal von wem, nicht ausgewertet. Lucy ist die Mitbewohnerin (dritte Person, keine
  Einwilligung): ihre Projekte und alle Chats, die zu ihr passen könnten, sind draußen. Die letzten
  10 unklaren hat Claude entschieden (Jan 23.10.), im Zweifel gegen Lia: aufgenommen nur der
  Teilzeitantrag (Formular im Referendariat).
- Noch vorhanden und nicht gebraucht: data/export/light_metadata-000/ (Konto, Anmeldungen mit IP) und
  memories-000.zip im Upload-Ordner der App. Löschung vorgeschlagen, Jans Antwort fehlt.

## Aufbau
- Einstieg: auswertung.py (`.venv/bin/python auswertung.py <befehl>`, Befehle im Kopf der Datei).
- ablage.py: data/ mit chmod 700, Dateien mit chmod 600 (atomar), lehnt ungeschützte Ordner ab.
- export.py: ZIP sicher entpacken (keine Pfade nach oben, keine Symlinks, höchstens 2 GB), Strukturbericht
  ohne Inhalte, Verzweigungen über parent_message_uuid.
- auswahl.py: Chatliste data/chatliste.tsv mit Spalte wer (Lia/Jan/privat/leer/unklar), bestaetigte_lia()
  liest sie zurück und bricht ab, solange etwas unklar ist; filtern() behält nur Lias Chats. Stichwortlisten LIA/JAN oben in der Datei.
- Arbeitsdaten: data/lia/chats.json (Lias 27 Chats im Exportformat), data/lia/projekte/, data/chatliste.tsv,
  data/struktur.txt (nur Feldnamen). Der Export kam als 6 ZIPs, geladen nur conversations, projects, light_metadata.
- .venv: auswertung/.venv, keine Pakete (requirements.txt leer), agentkit per agentkit.pth.
- Kein Dienst, kein Timer, keine .env.
- Rohdaten und Ergebnisse nur in data/ (nicht im Repo, .gitignore `data/`), Logs in logs/.

## Datenschutz
- Weiter geht es erst mit Lias Einwilligung (einwilligung.md). Lias Chats können Schülerdaten enthalten.
  Ihr Okay wird hier mit Datum und Einschränkungen vermerkt. Widerruft sie, wird alles gelöscht, auch Ergebnisse.
- Jans eigene Chats im Export werden nach der Auswahl (Schritt 4) nicht weiter verarbeitet.
- Löschtermine (mit Lias Okay vom 23.10.2026 verbindlich): Jans Chats nach Schritt 4; Lias Originalchats nach
  Schritt 8, spätestens 31.12.2026; die ZIP-Datei auf Jans Rechner nach dem Hochladen. Es bleiben nur
  anonymisierte Ergebnisse, die Beispiele erst nach Lias Durchsicht.

## Plan (je Schritt erst nach Jans Okay, danach ein Commit)
1. Gerüst – erledigt.
2. Einwilligung: kurze Erklärung für Lia (was ausgewertet wird, was nicht, wo die Daten liegen, Löschung).
3. Export: Anleitung für Jan (claude.ai-Export anfordern, auf den Server laden), dann Struktur prüfen:
   Felder, verworfene Antworten, bearbeitete Prompts.
4. Lias Chats herausfiltern: Vorschlagsliste, Lia oder Jan bestätigen.
5. Anonymisieren: getestetes Skript (Namen, Schulen, Schüler, Kontaktdaten), Stichprobe für Jan.
6. Analyse: Chats in Aufgaben zerlegen, Kategorienschema an einer Stichprobe, Einordnung über
   agentkit.claude_lauf (mehrere Aufgaben je Lauf, günstiges Modell, vorher Kostenschätzung),
   je Kategorie Häufigkeit, Runden, Korrekturen, typische Eingaben; Lias Korrekturen gesondert.
7. Ergebnisse in data/ und Zusammenfassung hier: Rangliste (Häufigkeit × Aufwand × Automatisierbarkeit)
   mit Empfehlung unterricht oder neuer Agent, anonymisierte Beispiele, Prüfsatz, Regelvorschläge.
   Bedarf anderswo nur als Vorschlag in die Haupt-STATUS.md.
8. Prüfung durch Lia: 20–30 Aufgaben selbst kodieren, Übereinstimmung vergleichen; danach blinde
   Bewertung von lia/unterricht gegen ihre alten Ergebnisse (Läufe macht der unterricht-Chat).

## Offene Punkte
1. Schritt 5: Anonymisieren (nach Jans Okay).
2. Löschen von light_metadata und memories-ZIP (Jans Okay fehlt).
3. Instanz für die claude-Läufe in Schritt 6: Vorschlag AGENTKIT_INSTANZ=lia/instanz (es sind Lias Daten).
