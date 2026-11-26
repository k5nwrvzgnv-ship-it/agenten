# Neurolign für Henri und Felix einrichten (Jans Schritte)

Stand 26.11.2026, nachts vorbereitet. Plan: docs/plan-neurolign-server.md.

**Schon erledigt (Claude):** Der Dienst `fehlstellenscan-neurolign` läuft auf dem Server und nimmt nur Verbindungen
vom Server selbst an (127.0.0.1:8796). Er ist erst erreichbar, wenn du die Schritte 1 und 2 gemacht hast. Passwörter
für jan, henri und felix stehen in `fehlstellenscan/.env`, der fertige Caddy-Block in
`fehlstellenscan/data/caddy-neurolign.txt` (Passwörter darin nur als Hash). Der Block ist mit `caddy validate` geprüft,
und mit einem Probe-Caddy ohne root auch die Anmeldung: ohne oder mit falschem Passwort 401, Henri kann sich nicht als
Jan ausgeben.

## 1. DNS bei INWX (Browser)

INWX, Domainliste, meldro.de, DNS. Zwei neue Einträge, wie bei kcal und lia:

| Typ  | Name      | Inhalt                    |
|------|-----------|---------------------------|
| A    | neurolign | 84.247.188.205            |
| AAAA | neurolign | 2a02:c207:3020:9076::1    |

Heute zeigt neurolign.meldro.de noch auf den INWX-Platzhalter 185.181.104.242 (Wildcard). Geht auch über Claude in
Chrome wie am 27.10. bei kcal.

Prüfen (Mac-Terminal, nach ein paar Minuten): `dig +short neurolign.meldro.de` zeigt 84.247.188.205.

## 2. Caddy (Server, als root)

Auf dem Mac `ssh agents` (das ist root auf dem Server). Dann:

    cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.vor-neurolign

Sicherungskopie der jetzigen Datei, falls etwas schiefgeht.

    { echo; cat /home/agent/agenten/fehlstellenscan/data/caddy-neurolign.txt; } >> /etc/caddy/Caddyfile

Hängt eine Leerzeile und den fertigen Block ans Ende der Caddyfile.

    caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

Prüft die ganze Datei. Am Ende muss `Valid configuration` stehen. Sonst nicht weiter, sondern mit
`cp /etc/caddy/Caddyfile.vor-neurolign /etc/caddy/Caddyfile` zurück.

    systemctl reload caddy

Lädt die neue Fassung, ohne kcal, lia und uni zu unterbrechen. Caddy holt beim ersten Aufruf das Zertifikat; das klappt
erst, wenn der DNS-Eintrag aus Schritt 1 wirkt.

Prüfen (Mac-Terminal):

    curl -s -o /dev/null -w '%{http_code}\n' https://neurolign.meldro.de/

muss `401` zeigen (Passwort fehlt). Dann im Browser https://neurolign.meldro.de öffnen, Benutzer `jan`, Passwort aus
`fehlstellenscan/.env` (Zeile NEUROLIGN_PASSWORT_JAN). Anzeigen auf dem Server als agent:

    grep NEUROLIGN ~/agenten/fehlstellenscan/.env

## 3. Zugänge verteilen

Henri: Benutzer `henri`, Passwort NEUROLIGN_PASSWORT_HENRI. Felix: Benutzer `felix`, Passwort NEUROLIGN_PASSWORT_FELIX.
Am besten einzeln per Signal oder persönlich, nicht in die Projektgruppe (dort liest Rüdiger mit, und der Verlauf bleibt).

## Was Henri und Felix können

- **Hochladen:** Balken anlegen (Länge, Breite, Höhe, Holzart), Seite auf dem Balkenbild antippen, Fotos wählen. Jedes
  Foto geht einzeln hoch, mit Fortschritt. JPEG und PNG; HEIC lehnt der Server ab (am iPhone gibt Safari beim Hochladen
  meist JPEG; sonst Einstellungen > Kamera > Formate > Maximale Kompatibilität). Höchstens 40 MB je Foto.
- **Labeln:** wie auf dem Mac. Jedes Label trägt den Namen. Speichert jemand ein Foto, das ein anderer inzwischen
  gespeichert hat, kommt ein Hinweis statt stillem Überschreiben.
- Alles wie du (vollwertige Kollegen, 26.11.): auch Fotos verwerfen, Maße ändern, Aufteilung und Training starten
  (gerechnet auf deinem Mac, siehe unten). Die Fotobox gibt es nur auf dem Mac.

## Mac: Abgleich

- Nach einer Fotobox-Sitzung: `bash ~/fehlstellenscan/mac/neurolign_abgleich.sh hoch` schickt neue Balken auf den
  Server. Balken, an denen auf dem Server schon gelabelt wird, und fremde Balken mit gleicher ID lässt es aus.
- `bash ~/fehlstellenscan/mac/neurolign_abgleich.sh runter` holt alle Balken mit Labels auf den Mac. Labels vom
  Server ersetzen die auf dem Mac. Mit dem Dienst unten passiert das vor jedem Training von selbst. Ab jetzt nur noch auf neurolign.meldro.de labeln.
- Skript holen (einmal): `scp agents-user:agenten/fehlstellenscan/mac/neurolign_abgleich.sh ~/fehlstellenscan/mac/`
- Balken vom Server heißen ab B501, die Fotobox auf dem Mac zählt ab B001. So gibt es keine zwei Balken mit
  derselben ID.

## Training vom Server aus (Mac als Dienst)

Training rechnet immer der Mac. Damit es auch auf neurolign.meldro.de startet, läuft Neurolign auf dem Mac als Dienst
und hält einen Tunnel zum Server offen. Einmal einrichten (Mac-Terminal):

    scp agents-user:agenten/fehlstellenscan/mac/neurolign_einrichten.sh ~/fehlstellenscan/mac/
    bash ~/fehlstellenscan/mac/neurolign_einrichten.sh

Das Skript holt das Programm vom Server, legt den Tunnel-Schlüssel in `~/fehlstellenscan/.env`, richtet den Dienst
ein (startet bei der Anmeldung, nach einem Absturz neu) und prüft am Ende, ob der Server den Mac erreicht. Läuft
Neurolign noch in einem Terminal, vorher dort mit ctrl-c beenden.

- Neurolign auf dem Mac danach nicht mehr von Hand starten, sondern einfach http://localhost:8765 öffnen.
- Erreichbar nur, wenn der Mac an ist und am Netzteil hängt (dann bleibt er wach). Sonst zeigt die Seite Training
  ein durchgestrichenes Notebook.
- Vor jedem Training holt der Mac alle Labels vom Server. Ergebnisse und Modelle bleiben auf dem Mac.
- Neue Fassung vom Server holen: dasselbe Skript noch einmal. Ausschalten: `bash ~/fehlstellenscan/mac/neurolign_einrichten.sh aus`.
- Protokoll: `~/Library/Logs/neurolign.log`.
