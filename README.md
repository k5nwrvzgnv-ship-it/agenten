# Agenten

Persönliches Agenten-System von Jan. Regeln: siehe CLAUDE.md. Aktueller Stand: siehe STATUS.md.

| Ordner | Agent | Aufgabe |
|---|---|---|
| uni/ | uni | Moodle und Unipostfach überwachen, Fristen, Zusammenfassungen, Lernsessions |
| dokumente/ | dokumente | Anträge, Berichte, PowerPoints, Tabellen erstellen |
| posteingang/ | posteingang | E-Mails lesen, sortieren, Antwortentwürfe |
| einkauf/ | einkauf | Geschenke und Bedarf recherchieren, Vorschläge mit Preisen |
| shared/ | – | Logging, Config, Freigabe-Warteschlange, gelernte Regeln |

## Arbeiten mit Claude Code
- Pro Agent ein VS-Code-Fenster im Agent-Ordner öffnen und dort den Chat führen (`/rename <agent>`).
- Struktur und shared/ im Hauptordner bearbeiten.
- Am Ende jeder Sitzung STATUS.md aktualisieren und committen lassen.
- Alte Chats: `/resume`. Neu anfangen: `/clear`. Das Wissen steht in den Dateien, nicht im Chat.
