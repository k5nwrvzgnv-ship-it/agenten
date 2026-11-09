# Status: Agent vabali (Lias Instanz)

## Zweck
Lia hat einen Gutschein für eine Massage im vabali spa Berlin (nach dem Examen). Der Agent prüft, ob ein passender
Termin frei wird, und schickt Lia dann eine Nachricht über ihre Zentrale (@zentraleliabot). Buchen tut Lia selbst.
Auftrag Jan 09.11.2026: 80 Min. Einzelmassage, Beginn spätestens 14:00, am liebsten Di 01.12., sonst bis So 06.12.

## Stand (09.11.2026)
- Läuft: Timer lia-vabali.timer alle 15 Minuten von 7:00 bis 22:45, Dienst lia-vabali.service (oneshot, ohne
  Claude, MemoryMax 200M, OnFailure ausfall@). Vorlagen in systemd/. Ein Lauf dauert etwa eine Minute.
- Suche in suche.toml (Tage, beginn_bis, dauer_minuten, partner, Link). Gemeldet werden alle buchbaren 80-Min.-
  Einzelmassagen (heute Ganzkörper, Aromaöl, vabali-Moment, Lomi Lomi Nui, Hot Stone). Für welche Massage der
  Gutschein gilt, ist nicht bekannt; Lia sieht das beim Buchen.
- Schnittstelle (abfrage.py): Buchungssoftware Sparkle hinter vabali.de/berlin/buchung-shop/, ohne Login, nur
  lesend. getAvailableArtikel (Massagen eines Tages; ausgebuchte Tage liefern eine leere Liste) und
  getPossibleAnwendungen (Startzeiten mit freiem Personal). 1 s Pause zwischen Abfragen.
- Meldungen: neu frei gewordene Termine an Lia (Lias Instanz), je Tag und Uhrzeit eine Zeile. Was beim letzten Lauf
  schon frei war, kommt nicht noch einmal; wird ein Termin frei, wieder belegt und wieder frei, kommt er erneut.
  Stand in data/stand.json. Scheitert die Abfrage, bekommt Jan einmal eine Meldung, und eine, wenn es wieder klappt.
- Erster echter Lauf 09.11. 23:21: 0 passende Termine (01.12. und 03.12. nur abends frei, 02., 04.–06.12. ausgebucht),
  keine Nachricht an Lia. Der Weg bis zu Lias Telegram ist der übliche von meldungen.melden (wie bei Lias anderen
  Agenten), mit diesem Agenten aber noch nicht echt durchlaufen.

## Offen
- Nach dem 06.12. (oder sobald Lia gebucht hat) Timer abschalten:
  `systemctl --user disable --now lia-vabali.timer`
- Leere Liste an allen Tagen sieht aus wie "alles ausgebucht". Ändert vabali die Schnittstelle so, dass sie leer
  antwortet statt mit Fehler, merkt der Agent das nicht.
- README (Diensttabelle) im Hauptordner nennt lia-vabali noch nicht.
