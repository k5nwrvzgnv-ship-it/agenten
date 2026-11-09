# Status: Agent verwaltung (Lia)

## Zweck
Behördenformulare für Lia vorausfüllen, damit sie nur noch prüft, unterschreibt und mitbringt. Erster Fall:
Verbeamtung im Land Berlin (Mail der Einstellungsstelle SenBJF vom 06.11.2026, Termin 10.11.2026 14:00,
Flottenstraße 28-42). Python füllt die Felder; Claude sieht Lias Daten nicht.

## Stand (09.11.2026)
- Läuft von Hand, kein Dienst, kein Timer (Jan 09.11.2026). Lia gibt Angaben nicht über Telegram (Jan 09.11.):
  Jan beantwortet die Fragen im Chat, der Chat trägt sie in data/angaben.toml ein (Vorlage
  angaben.beispiel.toml, chmod 600, Pflicht).
- `.venv/bin/python agent.py laden`: Gesamtpaket von berlin.de (agentkit.abruf, Allowlist berlin.de) nach
  data/quellen/, Prüfsumme muss zu formulare.PAKET_SHA256 passen (Stand 09.11.2026, 88 Seiten).
- `.venv/bin/python agent.py fuellen`: data/ausgang/verbeamtung-formulare.pdf (nur die zutreffenden
  Formulare, Reihenfolge der Checkliste, Felder ausfüllbar) und verbeamtung-checkliste.txt (was beiliegt, was
  entfällt, was Lia von Hand macht, fehlende Angaben, persönliche Unterlagen). Beide chmod 600.
- Probelauf mit Beispieldaten: 9 Formulare, 18 Seiten; Seitenbilder geprüft (Felder sitzen richtig).
- Noch nicht geliefert: echte Angaben fehlen (Fragenliste an Jan 09.11.). Weg zu Lia offen (Jan gibt die PDF
  weiter oder Ergebnis über Lias Zentrale).

## Aufbau
- angaben.py: Angaben laden (TOML, Rechte 600), Werte mit Buchführung, was fehlt; abgeleitete Werte (rein).
- formulare.py: Katalog der Formulare (Checklisten-Nr., Seiten im Paket, Bedingung, Feldzuordnung) (rein).
  Zuordnung an Seitenbildern geprüft; viele Felder heißen "KontrollkästchenN"/"undefined_N", Kommentare
  sagen, was dort steht.
- druck.py: Formular je eigene PDF aus dem Paket schneiden, füllen, Felder mit Vorsatz <schluessel>.
  umbenennen, zusammenfügen (pypdf). Unbekannte Feldnamen in der Zuordnung -> DruckFehler.
- checkliste.py: Text der Checkliste (rein). agent.py: Einstieg (laden, fuellen), Log ohne Angaben.
- .venv: lia/verwaltung/.venv, pypdf 6.21.0 (wie lia/chat), agentkit per .pth.
- Tests: `.venv/bin/python -m unittest discover -s tests -t .` (Tests mit dem echten Paket laufen nur,
  wenn data/quellen/ geladen ist, sonst übersprungen).

## Entscheidungen
- 09.11.2026 (Jan): eigener Agent lia/verwaltung; Mailzugang nicht nötig, Terminbestätigung macht Lia selbst.
- 09.11.2026: Gesamtpaket statt Einzel-PDFs: Einzel-PDFs teils AES-verschlüsselt (pypdf bräuchte
  cryptography, neues Paket). Im Paket wiederholen sich Feldnamen über Formulare, darum je Formular eine
  eigene PDF und Vorsatz vor jedem Feldnamen.
- 09.11.2026: "Erklärung zu Erkrankungen" nur Name, Geburtsdatum, Dienststelle; Inhalt liest und
  unterschreibt Lia selbst. Kästchen zum Führungszeugnis im Personalfragebogen bleiben für Lia.
- 09.11.2026: Häftlingshilfegesetz "nein" nur bei Geburt ab 1990 automatisch; Erklärungen (Verurteilungen,
  Verfahren, Zwangsvollstreckung) nur, wenn ausdrücklich angegeben.
- 09.11.2026: Tabellen im Personalfragebogen bis 5 Zeilen; mehr steht als Hinweis in der Checkliste.

## Offene Punkte
1. Echte Angaben eintragen, füllen, Seitenbilder prüfen, an Lia liefern.
2. Lebenslauf (eigenhändig unterschrieben) könnte der Agent aus denselben Angaben vorbereiten (Renderer).
3. Nach der Staatsprüfung: vorläufige Bescheinigung per Mail an die Einstellungsstelle (Lia selbst).
4. Kein Dienst; wenn weitere Formularfälle kommen, Auftrag über Lias Zentrale und Dienst lia-verwaltung.

## Gelernte Regeln
- (noch keine)
