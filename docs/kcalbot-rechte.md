# kcalbot: Rechte der Datenbank und Port 8787

Für Jan, als root auszuführen (der User agent hat kein sudo). Stand 27.10.2026.
Jeden Block einzeln ausführen und die Ausgabe ansehen, nicht alles auf einmal.

## Befund
- `/opt/kcalbot/tracker.db` und die Sicherungen `tracker.db.bak-20261017-1537`, `tracker.db.bak-ui` haben
  `-rw-r--r--`: Jeder User auf dem Server kann sie lesen. Darin: Mahlzeiten, Gewicht, Profile aller Nutzer und
  die geheimen Schlüssel des Schritte-Links (Tabelle `steps_keys`).
- Die Schritte-API lauscht auf `0.0.0.0:8787`, ohne HTTPS. `PUBLIC_URL` ist laut Code für eine Adresse wie
  `http://84.247.188.205:8787` gedacht, der Schlüssel steht dann in der URL.
- ufw ist aktiv, eingehend standardmäßig DROP. Ob 8787 freigegeben ist, kann agent nicht sehen.
  Ebenso wenig, ob der iPhone-Kurzbefehl benutzt wird (Journal braucht Gruppe adm).

## Teil A: Datenbank nur noch für bot

```bash
ls -la /opt/kcalbot
```
Zeigt die Dateien mit Rechten, zum Vergleich hinterher.

```bash
chmod 600 /opt/kcalbot/tracker.db /opt/kcalbot/tracker.db.bak-*
```
Nur noch der Eigentümer bot darf lesen und schreiben. Der laufende Bot ist bot, er merkt davon nichts.
SQLite legt seine Journal-Dateien mit denselben Rechten wie die Datenbank an.

```bash
mkdir -p /etc/systemd/system/kcalbot.service.d
printf '[Service]\nUMask=0077\n' > /etc/systemd/system/kcalbot.service.d/umask.conf
systemctl daemon-reload
systemctl restart kcalbot
systemctl status kcalbot --no-pager
```
Neue Dateien, die der Bot anlegt, sind ab jetzt nur für bot lesbar. Der Neustart dauert wenige Sekunden,
`status` muss `active (running)` zeigen.

Optional, schließt auch Code und README für andere User:
```bash
chmod 750 /opt/kcalbot
```
Dann kann auch agent (und damit ein Chat wie dieser) den Code nicht mehr lesen. Nur machen, wenn das gewollt ist.

Danach im agent-Chat prüfen lassen: `cat /opt/kcalbot/tracker.db` muss „Permission denied“ melden.

### Schlüssel des Schritte-Links erneuern (optional)
Es gibt keinen Hinweis, dass jemand die Schlüssel gelesen hat. Lesen konnte sie jeder User des Servers, praktisch
nur agent. Wer auf Nummer sicher gehen will:
```bash
sudo -u bot /opt/kcalbot/.venv/bin/python -c "import sqlite3; c = sqlite3.connect('/opt/kcalbot/tracker.db'); c.execute('DELETE FROM steps_keys'); c.commit()"
```
Löscht alle Schlüssel. Jeder Nutzer muss danach `/schritte_link` beim Bot aufrufen und die neue URL im
Kurzbefehl eintragen, sonst bekommt sein iPhone „forbidden“. Vorher die Nutzer fragen.

## Teil B: Port 8787

Erst nachsehen, dann entscheiden:
```bash
ufw status numbered
```
Zeigt die Firewall-Regeln. Gesucht: eine Zeile mit `8787`.

```bash
grep -E '^(PUBLIC_URL|STEPS_API_PORT)=' /opt/kcalbot/.env
```
Zeigt, ob und mit welcher Adresse der Schritte-Link eingerichtet ist (kein Geheimnis in diesen Zeilen).

```bash
journalctl -u kcalbot --since "-30 days" --no-pager | grep -c "Schritte vom iPhone"
```
Wie oft in 30 Tagen ein iPhone Schritte geschickt hat.

### Fall 1: keine Regel für 8787
Der Port ist von außen schon zu, nur der Server selbst erreicht ihn. Nichts zu tun. Der Kurzbefehl kann dann
heute gar nicht funktionieren; ist `PUBLIC_URL` gesetzt, bekommen Nutzer einen Link, der nicht geht.

### Fall 2: Regel für 8787, Kurzbefehl wird nicht benutzt (Zähler 0)
```bash
ufw delete allow 8787/tcp
```
Schließt den Port von außen. Stand die Regel anders da (z. B. mit IP), stattdessen die Nummer aus
`ufw status numbered` nehmen: `ufw delete <nummer>`.

### Fall 3: Regel für 8787, Kurzbefehl wird benutzt
Nicht einfach schließen, sonst kommen keine Schritte mehr an. Der richtige Weg ist HTTPS davor
(Domain auf 84.247.188.205, ein Reverse-Proxy wie Caddy, 8787 nur noch lokal). Das heißt Software installieren
und den Code von kcalbot ändern (Bindung an 127.0.0.1 statt 0.0.0.0, Zeile 531): eigener Plan, eigenes Okay.
Bis dahin bleibt das Risiko: Wer im selben WLAN mitliest, sieht den Schlüssel und kann Schritte eintragen,
mehr nicht.
