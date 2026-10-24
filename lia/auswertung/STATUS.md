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
- Gelöscht (Jan 23.10.): login_history.json, memories-ZIP. Noch da, nicht gebraucht: data/export/light_metadata-000/users.json.
- Schritt 5 (23.10.): anonymisiert nach data/lia/anonym.json (aufbereitet: nur Titel, Datum, Zusammenfassung,
  Nachrichten mit Text, Anhängen, Dateinamen; ohne Werkzeugaufrufe und Suchergebnisse). 1.031 Ersetzungen,
  77 Platzhalter: Lehrkraft, Partner, Person 1–3, Schule A–C, Schüler 1–67, dazu E-Mail, Telefon, Adresse,
  PLZ Ort, Nummer (5+ Ziffern außer ISBN), Schulnummer. Namensliste data/namen.json (97 Einträge, nicht im
  Repo), Zuordnung data/lia/zuordnung.json. Liste gebaut aus: Großwörtern ohne Artikel, Lias kleingeschriebener
  Anwesenheitsliste, Aufzählungen und Tabellenspalten mit bekannten Namen. Restsuche: keine Namen der Liste mehr,
  keine Mails/Telefon/Adressen. Absichtlich nicht ersetzt: Autoren, öffentliche Personen, Figuren aus Stücken und
  Romanen, von Claude erfundene Namen in Beispielaufgaben (Elif, Lukas, Mara ...). Bezirke bleiben.
  Stichprobe (12 Ausschnitte) in data/stichprobe.md, wartet auf Jans Kontrolle.
  Grenze: Namen, die nur einmal im Fließtext stehen und in keiner Liste, können fehlen. Original data/lia/chats.json
  bleibt bis zum Löschtermin (für Nachbesserungen).

- Schritt 6 vorbereitet (23.10.): verlauf.py zerlegt Chats in Runden (Hauptpfad, Bearbeitungen gezählt) und
  baut eine kompakte Fassung (Lias Prompts ganz, Claudes Antworten auf 300 Zeichen). 1.142 Runden, ca. 165.000
  Tokens (geschätzt: Zeichen/3,5). Zwei Chats machen die Hälfte aus (308 und 255 Runden).
  Kostenschätzung (Preise je 1 Mio. Tokens Ein/Aus: Haiku 5.5 0,10/0,50 USD, Sonnet 5.5 2/10, Opus 5.5 4/20):
  ca. 9 Läufe mit je ~20.000 Tokens Daten + ~8.000 Grundlast/Anleitung, Ausgabe ~30.000 Tokens gesamt.
  Haiku ca. 0,05–0,10 USD, Sonnet ca. 1–1,50 USD, Opus ca. 2–3 USD (Pro-Abo: nur Kontingent, kein Geld).
  Kontrolle: 30 Aufgaben zusätzlich mit Sonnet einordnen und vergleichen, ca. 0,20 USD.
  Jan 23.10.: Sonnet (art routine), kein Warten auf Haiku.
  Schema: schema.md (aus 9 Chats, ca. 230 Runden, in diesem Chat abgeleitet), von Jan bestätigt.
  9 Kategorien, Felder je Aufgabe, 9 Arten von Korrekturen. Geht wörtlich in den Prompt.
  Hindernis: claude_lauf wählt Haiku nur in der Stufe sparen (art routine = Sonnet). Bedarf in Haupt-STATUS.

- Schritt 6 erledigt (23.10.): 11 Pakete mit Sonnet eingeordnet (12 Läufe, eine Nachbesserung, 2,54 USD,
  ca. 557.000 Tokens, 5h-Auslastung 32 % -> 42 %). Schätzung war 1–1,50 USD: je Lauf fielen ~2x so viele Tokens an
  (Grundlast und Ausgabe). 245 Aufgaben nach Zusammenführen, alle Antworten gültig. Ergebnisse in data/ergebnis/:
  aufgaben.json, kategorien.json (Kennzahlen), korrekturen.json (284 Korrekturen von Lia mit Zitat).

  | Kategorie | Aufg. | Runden | Median | Korr. | automatisierbar hoch/mittel/gering |
  |---|---|---|---|---|---|
  | material | 80 | 395 | 3 | 148 | 33/36/11 |
  | planung | 47 | 239 | 4 | 46 | 2/15/30 |
  | fachklaerung | 37 | 150 | 3 | 11 | 19/15/3 |
  | eigener_text | 28 | 89 | 2 | 25 | 8/20/0 |
  | auswahl | 24 | 134 | 4,5 | 34 | 13/3/8 |
  | bewertung | 13 | 87 | 5 | 17 | 7/4/2 |
  | verwaltung | 9 | 25 | 2 | 0 | 5/3/1 |
  | sonstiges | 5 | 19 | 3 | 2 | 2/3/0 |
  | kommunikation | 2 | 4 | 2 | 1 | 2/0/0 |

  Häufigste Korrekturen bei material: form 38, fachlich 20, umfang 19, niveau 17, missverstanden 15,
  anwendbarkeit 14, stil 12. Bei planung: fachlich 14, missverstanden 13, anwendbarkeit 9.
  Fächer: Ethik deutlich vor DS. Belastung (Frust, Zeitdruck) in 31 Aufgaben, am häufigsten bei planung (9).
  Stichprobe der Korrekturen plausibel, Zuordnung der Art teils strittig (wird in Schritt 8 mit Lia geprüft).

- Schritt 7 (23.10.): Ergebnisse in data/ergebnis/: rangliste.json, beispiele.md (je Top-Typ 2 Aufgaben mit
  Auftrag und Korrekturen), pruefsatz.json (22 echte Aufträge mit Kontext, Kriterien aus Lias Korrekturen und
  ihrem alten Ergebnis). Alles anonymisiert. Zusammenfassung unten.

## Ergebnis: Rangliste und Empfehlung (Stand 23.10.2026, UNGEPRÜFT)
Jan 23.10.: Lias Prüfung (Schritt 8) vorerst ausgesetzt. Die Einordnung stammt allein von Claude (Sonnet) und
ist nicht mit Lias Sicht abgeglichen. Rangliste und Zahlen als Orientierung nutzen, nicht als Messung.
Wert = Runden x Automatisierbarkeit (hoch 1, mittel 0,6, gering 0,2), also etwa die Runden, die ein Agent
Lia abnehmen könnte. Typen per Stichwort aus Titel/Ausgabe (rangliste.py), Zuordnung teils grob.

| # | Typ | Kat. | Aufg. | Runden | Korr./Aufg. | Wert | Empfehlung |
|---|---|---|---|---|---|---|---|
| 1 | Philosophie und Quellen klären | fachklaerung | 34 | 137 | 0,26 | 89 | unterricht, Weg „Frage stellen“ |
| 2 | UB-Entwurf und eigene Texte prüfen | eigener_text | 28 | 89 | 0,89 | 59 | unterricht, später (Text prüfen) |
| 3 | AB-Bausteine (Aufgaben, Kärtchen, EH) | material | 14 | 74 | 1,43 | 54 | unterricht, Material |
| 4 | Argumentieren üben (BBB, Erörterung) | material | 14 | 80 | 2,14 | 50 | unterricht, Material |
| 5 | AB-Text zu einer Position, Merksatz | material | 21 | 87 | 1,90 | 41 | unterricht, Material |
| 6 | Stunde und UB planen | planung | 26 | 152 | 1,15 | 41 | nicht automatisieren, nur Kontext liefern |
| 7 | Bewertungsbögen und Noten | bewertung | 10 | 54 | 1,70 | 36 | eigener Agent später, erst Datenschutz |
| 8 | Reihe und RLP | planung | 21 | 87 | 0,76 | 35 | unterricht mit RLP-Wissensbasis |
| 9 | Mitarbeit auswerten | bewertung | 3 | 33 | 0 | 33 | Python-Werkzeug, erst Datenschutz |
| 10 | Stücke zusammenfassen | material | 12 | 39 | 1,67 | 32 | unterricht, Material (DS) |
| 11 | Positionen und Fälle auswählen | auswahl | 13 | 85 | 1,69 | 31 | unterricht, schwer |
| 12 | Fallbeispiel | material | 9 | 64 | 2,44 | 31 | unterricht, Material |
| 13 | Stücke, Filme, Themen auswählen | auswahl | 11 | 49 | 1,09 | 30 | unterricht, „Frage stellen“ |
| 14 | Theatermaterial (Szenen, Chortext) | material | 10 | 51 | 1,60 | 26 | unterricht, braucht DS-Profil |
| 15 | Verwaltung (Formulare, Bewerbung) | verwaltung | 9 | 25 | 0 | 19 | späterer Agent buero |

Rest (sonstiges, Stück/Film klären, Nachrichten) unter 15.
Fazit: Rund drei Viertel der Aufgaben gehören zu lia/unterricht (Material, Fragen, Auswahl, Texte prüfen).
Material ist dort schon gebaut, muss aber die hohe Korrekturrate (1,4–2,4 je Aufgabe) senken. Am meisten
fehlt: Wissen über die laufende Reihe (Reihenfrage, Klasse, behandelte Positionen): 43 Korrekturen „missverstanden“
und 14 „einseitig“ gehen darauf zurück. Neue Agenten lohnen sich nur für Bewertung (Bögen, Noten, Mitarbeit:
gut automatisierbar, aber Schülerdaten, siehe docs/lia-architektur.md Abschnitt 0) und später buero (selten).
Planung (Wert 41 + 35) bleibt Lias Gespräch; ein Agent hilft dort nur mit Kontext und Belegen.

Beispiele (Details in data/ergebnis/beispiele.md): Aristoteles-Merksatz für Klasse 8 (14 Runden, 11 Korrekturen),
Singers Argument als BBB-Schnipsel (25 Runden, 7 Korrekturen), Fallbeispiel Familie vs. Fremde (17 Runden),
Zentrale Themen zu Dramen als einfache Kommaliste (9 Runden, 6 Korrekturen), Mitarbeit Theaterkurs (2 x 16 Runden,
eine Frage je Schüler, keine Korrektur).

Prüfsatz (data/ergebnis/pruefsatz.json, für den unterricht-Chat in Schritt 8): 22 Aufträge, P01–P04 AB-Text,
P05–P07 Argumentieren, P08–P10 Fallbeispiel, P11–P13 AB-Bausteine, P14–P15 Stücke zusammenfassen, P16–P17
Theater, P18–P20 Fachfragen, P21–P22 Bewertung. Je Eintrag: auftrag, kontext (bis zu 3 Prompts davor),
anhaenge (nur Namen, Inhalte sind nicht im Export), kriterien (Lias Korrekturen), altes_ergebnis.
Grenze: Aufträge mitten im Chat brauchen den Kontext; vor dem Lauf zu einem vollständigen Auftrag umschreiben.

## Schritt 8: Prüfung durch Lia (vorbereitet 23.10.2026, ausgesetzt)
Jan 23.10.: vorerst ausgesetzt, der unterricht-Chat legt ohne sie los. Bogen und Befehle bleiben für später.
pruefung.py, Befehle in auswertung.py. Bögen sind einzelne HTML-Dateien ohne Netz: Lia öffnet sie im Browser
(Handy oder Rechner), tippt die Antworten an, „Antworten speichern“ lädt eine CSV herunter, die sie Jan schickt.
Geprüft: Skript mit node --check und Attrappe, Ablauf mit Platzhaltertexten durchgespielt (danach gelöscht).

A. Kodierung (fertig zum Versand): data/pruefung/kodierbogen.html, 25 Aufgaben (jede Kategorie mindestens
   einmal, höchstens 12 Runden, fester Seed), Stichprobe in data/pruefung/kodier_stichprobe.json. Lia sieht nur den
   Chatausschnitt (Claudes Antworten auf 700 Zeichen gekürzt), nicht Claudes Einordnung. Sie wählt Kategorie,
   Ergebnis, Automatisierbarkeit, Zahl und Art der Korrekturen. Dauer geschätzt 45–60 Minuten.
   Die Aufgabengrenzen sind vorgegeben, die Zerlegung selbst wird nicht geprüft.
   Auswertung: `auswertung.py kodierung <csv>` -> Anteil gleich und Cohens Kappa je Feld, Korrekturzahl
   (gleich, höchstens 1 daneben), Überlappung der Korrekturarten, Liste der abweichenden Kategorien.
   Faustregel: Kappa ab 0,6 brauchbar; darunter Schema schärfen, bevor die Rangliste gilt.
B. Blindvergleich (wartet auf den unterricht-Chat):
   1. Der unterricht-Chat lässt lia/unterricht die Prüfsatz-Aufträge P01–P17 (Material) bearbeiten, je als eigener
      Auftrag mit dem Kontext ausformuliert, ohne Lia etwas zu schicken. P18–P20 (Fachfragen) erst, wenn es „Frage
      stellen“ gibt; P21–P22 (Bewertung) entfallen, dafür gibt es keinen Agenten.
   2. Er legt die Textfassung jedes Ergebnisses ab als lia/unterricht/data/pruefung/P01.txt usw. (agentkit.textfassung).
   3. `auswertung.py vergleichsbogen /home/agent/agenten/lia/unterricht/data/pruefung` baut den Bogen: je Auftrag
      A und B in zufälliger Reihenfolge, beide als Text ohne Markdown und ohne claude.ai-Reste angeglichen. Schlüssel
      in data/pruefung/vergleich_schluessel.json (Lia bekommt ihn nicht).
   4. Lia bewertet je Paar: besser (A/B/gleich), so verwendbar (ja/mit Änderungen/nein) je Fassung, welche ihrer
      früheren Wünsche (Kriterien aus den Korrekturen) jede Fassung erfüllt.
   5. `auswertung.py vergleich <csv>` -> wie oft neu besser, Verwendbarkeit, Anteil erfüllter Kriterien alt/neu.
   Grenze: Das alte Ergebnis ist Lias Endstand nach ihren Korrekturen, das neue ein erster Versuch. Ziel ist,
   dass neu mindestens gleichauf liegt; ein Rückstand zeigt, wo Regeln und Reihenkontext fehlen.

## Regelvorschläge (aus 284 Korrekturen, noch nicht freigegeben)
Erst nach Okay von Jan/Lia in lia/instanz/regeln.md (allgemein) oder lia/unterricht/STATUS.md eintragen.
1. Was einem Philosophen zugeschrieben wird, braucht einen Beleg (Werk, Stelle). Eigene didaktische Vereinfachung
   als solche kennzeichnen. Nichts erfinden, Unsicherheit sagen. (fachlich: 52)
2. Vor jeder Antwort Reihenfrage, Klasse und gewählte Positionen der laufenden Reihe beachten, nicht stillschweigend
   wechseln. Schon behandelte Positionen nicht wieder vorschlagen. (missverstanden: 43, einseitig: 14)
3. Texte für Schülerinnen und Schüler: Fließtext in ganzen Sätzen, ohne Zwischenüberschriften und ohne Stellenangaben;
   Belege gehören in den Begleittext für Lia. BBB: je Teil genau ein vollständiger Satz. (form: 48)
4. Sprache für die 8. Klasse (lernschwach, mehrsprachig): kurze Sätze, keine Redewendungen, abstrakte Wörter
   (schulden, Pflicht, zustehen, Kosten tragen) vermeiden oder erklären, nichts voraussetzen, was nicht behandelt
   wurde. Nicht „eloquent“. (niveau: 26, stil)
5. Ein Merksatz oder eine Regel muss sich auf einen Fall anwenden lassen und ihn eindeutig entscheiden. Vor der
   Ausgabe an einem Beispiel prüfen. (anwendbarkeit: 30)
6. Fallbeispiele: alltagsnah, logisch stimmig, eindeutige Entscheidung (entweder/oder), keine Tötung, kein Femizid,
   keine Gewalt, die man rechtfertigen müsste; Strafen realistisch. (anwendbarkeit, andere)
7. Zwei Positionen für eine Reihe müssen sich klar widersprechen; nah beieinander liegende Positionen sagen. (fachlich)
8. Auswahllisten breit streuen, nicht nur eine Richtung. (einseitig)
9. Lieber kurz; auf Wunsch länger. Arbeitsblatt passt auf eine Seite, wenn nicht anders gesagt. (umfang: 31)
10. Geschlechtergerecht schreiben (nicht männlich tonnotiert). Texte, die Lia selbst abgibt, in ihrem Ton, ohne
    Umgangssprache und nicht geschwollen. (stil: 18)
11. Bewertung: Lias Gewichtungen übernehmen, jede Skala auf erreichbare Noten prüfen, Rechnungen nachvollziehbar. (bewertung)

## Aufbau
- Einstieg: auswertung.py (`.venv/bin/python auswertung.py <befehl>`, Befehle im Kopf der Datei).
- ablage.py: data/ mit chmod 700, Dateien mit chmod 600 (atomar), lehnt ungeschützte Ordner ab.
- export.py: ZIP sicher entpacken (keine Pfade nach oben, keine Symlinks, höchstens 2 GB), Strukturbericht
  ohne Inhalte, Verzweigungen über parent_message_uuid.
- schema.md: Kategorien und Felder für die Einordnung (keine personenbezogenen Daten).
- pruefung.py: Stichprobe, HTML-Bögen, Übereinstimmung (Kappa), Blindvergleich.
- rangliste.py: Aufgabentypen und Rangliste. pruefsatz.py: Prüfsatz.
- einordnen.py: Pakete, Prompt, Prüfung, Zusammenführen. statistik.py: Kennzahlen, Korrekturliste.
- verlauf.py: hauptpfad(), runden(), kompakt(), tokens_geschaetzt().
- anonym.py: aufbereiten() und Ersetzer (Namensliste + Muster), reste() für die Restsuche.
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
1. Jan/Lia entscheiden über die Regelvorschläge (einzeln). Eingetragen in lia/unterricht/STATUS.md: 1, 2 (gekürzt),
   3, 4 (Lia, 24.10.; 4 nur für Klasse 8, mit zwei bis drei schwierigeren Wörtern je Text;
   5 mit fachlicher Korrektheit zuerst und Testfall im Begleittext; 6 vorerst für alle Klassen; 7). Offen: 8–11.
2. Schritt 8 ausgesetzt (Jan 23.10.). Wieder aufnehmen: Lia bekommt data/pruefung/kodierbogen.html, ihre CSV mit
   `kodierung` auswerten; Blindvergleich, sobald der unterricht-Chat P01–P17 abgelegt hat.
4. Löschung der Rohdaten spätestens 31.12.2026 (auch wenn Schritt 8 ausfällt): data/lia/chats.json, data/namen.json,
   data/lia/zuordnung.json, data/export/ (users.json), data/chatliste.tsv. Danach nur Anonymisiertes.
3. Instanz für die claude-Läufe in Schritt 6: Vorschlag AGENTKIT_INSTANZ=lia/instanz (es sind Lias Daten).

## Gelernte Regeln
- (noch keine)
