# Plan: alle Funktionen des Boards „Desktop“ echt (Jan 30.10.2026)

Jans Auftrag (30.10.): „nun will ich wirklich alle Funktionen aus dem Board zum Laufen bekommen. Erstelle einen
Plan und öffne die entsprechenden Chats und lege los.“ Board: Canvas https://claude.ai/artifact/F8ysVSyr8TjGhFDcyNnejU,
Datei `project/Desktop.dc.html`. Stand der App: `shared/webapp/STATUS.md` (Abschnitt „Abgleich Board“).
Regeln wie immer (CLAUDE.md): ein Chat pro Ordner, jeder ändert nur seinen Ordner, Bedarf woanders in Punkt 24 der
Haupt-STATUS; Pläne für neue Dienste, Pakete, Benutzer erst Jan vorlegen; Commit nur mit Pfaden.

## Was fehlt, wer baut es

| # | Funktion im Board | fehlt in | Chat (Ordner) |
|---|---|---|---|
| 1 | Eine Datei `lia/instanz/reihen.toml` für App und Agenten, mit id, stand, agenten, schuljahr | Daten | lia/unterricht |
| 2 | Kurs 11 (Einheiten aus Lias Ordner k11) und Archiv Klasse 7 (2025/26) als Reihen | Daten | lia/unterricht |
| 3 | Stunden in der Datei der Agenten (Nummer, Thema, Marke UB/Prüfung); Web-App zieht danach um | Daten + Agent | lia/unterricht, dann shared/webapp |
| 4 | Arten Reihenentwurf und Lernerfolgskontrolle (mit Erwartungshorizont) | Agent | lia/unterricht |
| 5 | Varianten in einem Lauf (einfach, Türkisch, Hilfekarten, Level) | Agent | lia/unterricht |
| 6 | Nachbesserung auf Grundlage von Lias eigener Fassung (Word mit Kommentaren) | Agent + agentkit | lia/unterricht, Hauptordner |
| 7 | Eigene Formatvorlage (.dotx/.potx, Renderer kann es) nutzen | Agent | lia/unterricht |
| 8 | Spielfassung (Kürzung) und Szenenaufgabe als neue Aufträge | Agent | lia/theater |
| 9 | Chat „Fragen“ mit Ort, „ohne Ort“, „Daraus Auftrag machen“ | neuer Agent | lia/chat (neu) |
| 10 | final und eigene Fassung in agentkit (statt nur in der Web-App), Auftrag zurückziehen, Dateien an Rückmeldungen | agentkit | Hauptordner |
| 11 | Rückmeldung je Datei, Entwurf „Setze ich selbst ein“, „Nochmal“, Stunden im Baum, Archiv und „+ Reihe“ (nach 1), Fach-Ansicht, Chat-Spalte (nach 9) | Oberfläche | shared/webapp |
| 12 | Echt statt Testbetrieb auf lia/instanz (Lias Kontingent, Ergebnisse auch per Telegram) | Jans Entscheidung | Jan |

## Reihenfolge
1. Sofort parallel: shared/webapp (11, ohne Teile, die auf 1/9 warten), lia/unterricht (1, 2, dann 3 bis 7),
   lia/theater (8), lia/chat (9: Plan an Jan, gebaut erst nach seinem Okay), Hauptordner (10).
2. Danach die Web-App auf die neuen Dateien umstellen (reihen.toml in der Instanz, Stunden, Chat).
3. Dann echt (12) nach Jans Okay, sonst bleibt alles mit Wirkung im Testbetrieb.

## Schnittstellen (damit die Chats zusammenpassen)
- reihen.toml-Format: siehe Kopf von `shared/webapp/ordnung.py`. Neu dazu: `schuljahr` („2026/27“), und je Reihe
  `[[reihe.stunde]]` mit `nr`, `thema`, optional `marke` („UB“, „Prüfung“). Die Web-App liest beides.
- Aufträge aus der Web-App: Agent unterricht, quelle `portal-material`, Feld `reihe`, Text beginnt mit der Art
  („Arbeitsblatt: …“), am Ende „Reihe: …“ und ggf. „Stunde n: Thema“. Varianten heute: eigener Auftrag „Variante
  „Türkisch“ von „Titel“: …“ mit Datei als Anhang. Neue Arten (Reihenentwurf, LEK) bitte als Präfix im Text.
- Theater aus der Web-App: Agent theater, quelle `portal-theater` (neu), Text „Spielfassung: Stück, Länge,
  Spieler*innen, was bleiben muss“ bzw. „Szenenaufgabe: …“, Feld `reihe`.
- Chat: Web-App ruft nichts selbst auf. Vorschlag: lia/chat bietet eine Python-Funktion bzw. einen Dienst, der eine
  Frage mit Ortskontext beantwortet (Warteschlange `shared/auftraege`-Muster oder Unix-Socket); Entscheidung im
  lia/chat-Chat mit Jan.
