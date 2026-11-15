# Status: Agent kleinanzeigen

## Zweck
Wie der alte Vinted-Bot (~/agents/vinted), nur für Kleinanzeigen (ehemals eBay Kleinanzeigen):
Jan beschreibt oder fotografiert, was er sucht, der Agent sucht passende Anzeigen und meldet bewertete Treffer.
Genauer Umfang noch offen (siehe Offene Punkte).

## Stand (15.11.2026)
- Nur Ordnergerüst angelegt: STATUS.md, tests/, systemd/kleinanzeigen.service (Vorlage, nicht installiert).
- Noch kein Code, keine .venv, keine .env, kein Dienst, nicht in pruefen.sh.

## Aufbau (geplant, nach Systemkonvention)
- Code: kleinanzeigen/agent.py (Einstieg), Logik ohne Netz in eigenen, getesteten Modulen
- .venv: kleinanzeigen/.venv, agentkit per .pth eingebunden
- Dienst: kleinanzeigen.service (oneshot), ggf. Timer für laufende Suchen
- Zugangsdaten: kleinanzeigen/.env (chmod 600), Vorlage .env.example
- Laufzeitdaten: kleinanzeigen/data/, Logs: kleinanzeigen/logs/ (nicht im Repo)

## Entscheidungen
- 15.11.2026: Ordner unter ~/agenten (agentkit, Zentrale, Freigabe), nicht als eigenständiger Bot wie Vinted.

## Offene Punkte
1. Umfang klären: nur suchen und melden, oder auch Verkäufer anschreiben (nach außen, nur über Freigabe)?
   Verhältnis zum geplanten Agenten einkauf (README: "Recherche mit Preisen")?
2. Zugriff auf Kleinanzeigen: direkt vom Server oder (wie Vinted) über Chrome auf Jan-work? Vorher testen,
   ob die Server-IP geblockt wird. Regel: keine dauerhaft laufende Browser-Automation.
3. Kontakt zu Jan: über die Agentenzentrale (/kleinanzeigen) oder eigener Telegram-Bot (eigener Token)?
4. Pakete (z. B. httpx, Pillow) nur nach Jans Okay, dann requirements.txt.
5. Nach dem ersten Code: .venv anlegen, Testordner in pruefen.sh eintragen, Eintrag in README/CLAUDE.md
   (Hauptordner-Chat).

## Gelernte Regeln
- (noch keine)
