# Telegram-Zentrale – Stand

Ausführlicher Stand der Zentrale (Bedienung, Freigabe, Meldungen, Feedback): Haupt-`STATUS.md`, Abschnitt
„Stand (27.10.2026)“. Diese Datei hält nur den Stand nach dem Nachtauftrag 22./23.11.2026 fest.

## Stand (23.11.2026)
- Auf reines Signal gekürzt (Befund und Belege: `docs/befund-ux.md` Abschnitte 1 bis 4, Commit c44da8d).
- Jans Zentrale zeigt keine Feedback-Knöpfe mehr unter Ergebnissen (Schalter `logik.FEEDBACK_KNOEPFE`, aus).
  Korrigiert wird per Antwort auf das Ergebnis. Lias Zentrale ist unverändert.
- Menü: nur Agent-Knöpfe und „Entwürfe (n)“, wenn welche offen sind. `/hilfe` hat vier Zeilen. `/<agent>lern`,
  `/pc`, `/weiter` und `/verwerfen` gehen still weiter, stehen aber nirgends mehr.
- Meldungen und Ergebnisse ohne Vorlage laufen durch `logik.signal_html`: sichtbar sind die Kopfzeile und höchstens
  3 Punkte, der Rest steht zugeklappt darunter. Technikpräfixe, Zählerklammern, Markdown und Pfade fallen weg.
- Regeln als Tests: `tests/test_regeln.py` (`logik.regelverstoesse` über alle jan_*-Snapshots). Geprüft werden die
  Längengrenze, höchstens ein Handlungsaufruf und keine Füllwörter.
- Entwürfe zur Freigabe bleiben ungekürzt (Fingerabdruck). Rüdiger und die Freigabe-Logik sind unverändert.
- Live seit dem Neustart am 22.11. um 21:46. Rauchtest: Dienst aktiv, kein neuer Traceback, getMe antwortet.

## Nicht geprüft
- Klicks und das Aussehen in Telegram selbst: In der Nacht ging keine Testnachricht an Jan, geprüft sind nur
  Snapshots und Unit-Tests.

## Gelernte Regeln
(noch keine)
