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
- 15.11.2026 (Jan): Kein Kleinanzeigen-Konto, nur scannen. Der Bot schickt Treffer mit Link, Jan bzw. der
  Kumpel klickt und schreibt selbst. Damit handelt der Agent nicht nach außen, keine Freigabe nötig.
- 15.11.2026 (Jan): Sonnet bewertet die Treffer (und erkennt Fotos). Erwartet ca. 75 USD/Monat API-Gegenwert.
- 15.11.2026 (Jan): Teilagent des geplanten Agenten einkauf.
- 15.11.2026 (Jan): Eigener Telegram-Bot (eigener Token), weil ein Kumpel von Jan ihn mitbenutzen soll.

## Zugriffstest (15.11.2026)
- Zwei Abrufe vom Server mit normalem Browser-User-Agent (curl): Startseite und /s-fahrrad/k0 beide 200,
  keine Captcha- oder Sperrseite. Suchseite enthält 27 Anzeigen (data-adid, data-href, Titel und Beschreibung
  als JSON im HTML). Suchen geht also vermutlich ohne Browser direkt vom Server.
- Nicht getestet: viele Abrufe hintereinander (Drosselung), Login und Nachrichten schreiben (braucht ein Konto,
  dort ist eher mit Bot-Schutz zu rechnen).

## Kostenschätzung (15.11.2026, aus shared/verbrauch/laeufe.jsonl)
- Vinted-Bot real 27.10.-02.11.: 826 Ranking-Läufe mit Fotos auf Opus, 0,05 USD je Lauf, 44 USD in 6 Tagen
  (Spitze 17 USD/Tag). Grund: Prüfung alle 10 min, jede Prüfung ein Claude-Lauf mit Bildern.
- Echte Durchschnitte kurzer Läufe hier: Haiku 0,002 USD, Sonnet 0,025 USD, Opus (5.5) 0,03-0,05 USD.
- Plan für Kleinanzeigen: Python filtert vor (schon gesehene Anzeigen, Preis, Suchbegriffe, Umkreis), Claude nur
  für neue Kandidaten, gebündelt, nur Text. Annahme ca. 100 Läufe/Tag (3 Suchen, beide Nutzer):
  Haiku ca. 0,20 USD/Tag (6 USD/Monat), Sonnet ca. 2,50 USD/Tag (75 USD/Monat), Opus wie Vinted 150+ USD/Monat.
- USD sind API-Gegenwert. Über das Abo-Konto kostet es kein Geld extra, verbraucht aber das 5h-/7d-Kontingent
  aller Agenten. Server, Telegram und Kleinanzeigen-Abrufe kosten nichts.

## Offene Punkte
1. Takt und Konto festlegen (Vorschlag: Prüfung alle 10-15 min, Tagesgrenze an Läufen, Agenten-Konto).
2. Kumpel: zweiter Nutzer im eigenen Bot (Chat-ID in .env freischalten), seine Suchen getrennt von Jans.
3. Ordner: als Teilagent von einkauf später ggf. nach einkauf/kleinanzeigen verschieben.
4. Telegram-Token: Jan legt den Bot bei @BotFather an und trägt den Token selbst in kleinanzeigen/.env ein.
5. Pakete (z. B. httpx, python-telegram-bot, Pillow) nur nach Jans Okay, dann requirements.txt.
6. Nach dem ersten Code: .venv anlegen, Testordner in pruefen.sh eintragen, Eintrag in README/CLAUDE.md
   (Hauptordner-Chat).

## Gelernte Regeln
- (noch keine)
