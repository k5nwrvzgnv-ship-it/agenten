# Status: Agent kleinanzeigen

## Zweck
Wie der alte Vinted-Bot (~/agents/vinted), nur für Kleinanzeigen (ehemals eBay Kleinanzeigen):
Jan (und ein Kumpel) beschreibt oder fotografiert, was er sucht, der Agent sucht laufend passende Anzeigen,
meldet bewertete Treffer und schreibt Verkäufer nach Freigabe an.

## Stand (15.11.2026)
- Ordnergerüst angelegt: STATUS.md, tests/, systemd/kleinanzeigen.service (Vorlage, nicht installiert;
  für einen eigenen Telegram-Bot wird es ein Dauerdienst wie vinted-bot, Vorlage dann anpassen).
- Zugriff vom Server getestet, Suche geht ohne Browser (siehe Zugriffstest).
- Noch kein Code, keine .venv, keine .env, kein Dienst, nicht in pruefen.sh.

## Aufbau (geplant, nach Systemkonvention)
- Code: kleinanzeigen/agent.py (Einstieg), Logik ohne Netz in eigenen, getesteten Modulen
- .venv: kleinanzeigen/.venv, agentkit per .pth eingebunden
- Dienst: kleinanzeigen.service (oneshot), ggf. Timer für laufende Suchen
- Zugangsdaten: kleinanzeigen/.env (chmod 600), Vorlage .env.example
- Laufzeitdaten: kleinanzeigen/data/, Logs: kleinanzeigen/logs/ (nicht im Repo)

## Entscheidungen
- 15.11.2026: Ordner unter ~/agenten (agentkit, Freigabe), nicht als eigenständiger Bot wie Vinted.
- 15.11.2026 (Jan): Umfang wie Vinted-Bot, also suchen, bewerten und Verkäufer anschreiben. Anschreiben ist
  Handeln nach außen, also nur nach Freigabe des konkreten Entwurfs.
- 15.11.2026 (Jan): Teilagent des geplanten Agenten einkauf.
- 15.11.2026 (Jan): Eigener Telegram-Bot (eigener Token), weil ein Kumpel von Jan ihn mitbenutzen soll.

## Zugriffstest (15.11.2026)
- Zwei Abrufe vom Server mit normalem Browser-User-Agent (curl): Startseite und /s-fahrrad/k0 beide 200,
  keine Captcha- oder Sperrseite. Suchseite enthält 27 Anzeigen (data-adid, data-href, Titel und Beschreibung
  als JSON im HTML). Suchen geht also vermutlich ohne Browser direkt vom Server.
- Nicht getestet: viele Abrufe hintereinander (Drosselung), Login und Nachrichten schreiben (braucht ein Konto,
  dort ist eher mit Bot-Schutz zu rechnen).

## Offene Punkte
1. Kumpel als Nutzer: Nach der harten Regel gibt Jan jede Handlung nach außen frei. Soll der Kumpel seine
   eigenen Nachrichten-Entwürfe selbst freigeben (eigene Instanz wie lia/instanz) oder Jan alles? Wessen
   Kleinanzeigen-Konto schreibt (je Nutzer eigenes)? Wer zahlt die Claude-Läufe des Kumpels (Verbrauch)?
2. Anschreiben technisch: Login und Nachrichten direkt per HTTP oder zeitgesteuert kurz per Browser
   (keine dauerhaft laufende Browser-Automation). Erst einen Testlauf machen, wenn ein Konto feststeht.
3. Ordner: als Teilagent von einkauf später ggf. nach einkauf/kleinanzeigen verschieben.
4. Telegram-Token: Jan legt den Bot bei @BotFather an und trägt den Token selbst in kleinanzeigen/.env ein.
5. Pakete (z. B. httpx, python-telegram-bot, Pillow) nur nach Jans Okay, dann requirements.txt.
6. Nach dem ersten Code: .venv anlegen, Testordner in pruefen.sh eintragen, Eintrag in README/CLAUDE.md
   (Hauptordner-Chat).

## Gelernte Regeln
- (noch keine)
