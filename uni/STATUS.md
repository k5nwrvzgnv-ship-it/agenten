# Status: Agent uni

## Zweck
Moodle und Unipostfach überwachen, Fristen, Zusammenfassungen, Lernsessions.

## Stand (16.10.2026)
- Noch nicht begonnen. Umsetzung im eigenen Chat im Ordner uni/.

## Anforderungen (von Jan, 16.10.2026)
Zwei Arbeitsmodi. Jan wählt je nach Zeitdruck; ohne Angabe gilt "erledigen".
- Modus erledigen: Der Agent arbeitet allein und liefert danach ein verständliches Protokoll:
  - was er Schritt für Schritt gemacht hat,
  - welche Quellen er genutzt hat, mit genauer Stelle (Kurs, Datei, Seite/Folie),
  - wo er unsicher ist,
  - wie Jan das Ergebnis selbst nachprüfen kann (konkrete Prüfschritte).
  Kurzfassung per Telegram, volles Protokoll als Datei in uni/protokolle/.
- Modus lernen: Der Agent nimmt Jan an die Hand und arbeitet den Auftrag gemeinsam mit ihm durch
  (erklären, Fragen stellen, auf Antwort warten, Rückmeldung geben). Nicht alles vorlösen.
  Läuft sowohl über Telegram (unterwegs, kurze Nachrichten) als auch im Claude-Code-Chat am PC.
  Technisch: mehrere Runden, Sitzung fortsetzen mit `claude -p --resume`; der Agent merkt sich die Sitzung pro Auftrag.
- Entscheidung 16.10.: Kein automatischer Vorschlag von Modus lernen bei benoteten Abgaben. Jan wählt selbst.
- Der Modus steht im Auftrag (Feld `modus` in agentkit/auftraege.py, Werte `erledigen`/`lernen`).

## Offene Punkte
1. Wie wird eine Lern-Sitzung von Telegram an den PC-Chat übergeben und umgekehrt?

## Gelernte Regeln
- (noch keine)
