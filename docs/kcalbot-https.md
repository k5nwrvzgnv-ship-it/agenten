# kcalbot: HTTPS vor dem Schritte-Link (Plan, noch nichts umgesetzt)

Stand 27.10.2026. Vorgeschichte und Rechte: kcalbot-rechte.md. Alles hier läuft als root (`ssh agents`).

## Ziel
Der iPhone-Kurzbefehl schickt die Schritte über `https://kcal.meldro.de/steps?...` statt `http://84.247.188.205:8787/...`.
Der Schlüssel geht dann verschlüsselt über das Netz. Port 8787 ist danach von außen zu, kcalbot lauscht nur noch lokal.

## Ausgangslage (geprüft)
- Ports 80 und 443 sind frei, kein Webserver installiert.
- Ubuntu-Paket `caddy` 2.6.2 verfügbar (offizielle Paketquelle, keine Fremdquelle nötig).
- kcalbot bindet fest an `0.0.0.0` (bot.py Zeile 531), Port aus `STEPS_API_PORT`, Link aus `PUBLIC_URL`.
- Der Kurzbefehl wird benutzt: 25 Übertragungen in 30 Tagen.

## Entscheidung 1: Name für das Zertifikat

Entschieden 27.10.2026: Variante A, Domain meldro.de bei INWX (Nameserver INWX), Subdomain kcal.meldro.de.
Ein Zertifikat braucht einen Namen, auf den es ausgestellt wird.

- **A: eigene Domain oder Subdomain (empfohlen).** Zum Beispiel `kcal.<deine-domain>.de`, ein A-Eintrag auf
  84.247.188.205 (und AAAA auf 2a02:c207:3020:9076::1). Hast du keine: Domain beim Anbieter deiner Wahl, rund
  1 Euro im Monat, oder kostenlos eine Subdomain bei DuckDNS (dann hängt der Link an diesem Dienst).
  Funktioniert mit dem Ubuntu-Paket Caddy 2.6.2, Zertifikat 90 Tage, Caddy erneuert selbst.
- **B: Zertifikat direkt auf die IP.** Let's Encrypt stellt das seit 15.01.2026 aus, nur 6 Tage gültig, nur mit
  ACME-Profil `shortlived`. Caddy 2.6.2 kann das nicht, man bräuchte eine neuere Caddy-Version aus der
  Fremdquelle von Caddy, und für Caddy ist ein Fehler dazu gemeldet (Issue 7399). Nicht empfohlen.

## Entscheidung 2: Schlüssel bei der Umstellung erneuern
Die bisherigen Schlüssel liefen unverschlüsselt durchs Netz und lagen bis heute lesbar auf dem Server. Da jeder
Nutzer beim Umstieg ohnehin die URL im Kurzbefehl tauscht, kostet ein neuer Schlüssel nichts extra.
Empfehlung: ja, im selben Schritt.

## Schritte (Variante A)

**1. DNS-Eintrag** bei INWX (Domainliste, meldro.de, DNS bzw. Nameserver-Einträge), zwei neue Einträge:

| Name | Typ | Wert | TTL |
|---|---|---|---|
| kcal | A | 84.247.188.205 | 3600 |
| kcal | AAAA | 2a02:c207:3020:9076::1 | 3600 |

Erledigt 27.10.2026 (über Claude in Chrome), vom Server aus geprüft: kcal.meldro.de löst auf beide Adressen auf.
Die übrigen Einträge (Parkseite von INWX, auch * als Platzhalter) sind unverändert.
Prüfen vom Mac: `dig +short kcal.meldro.de` zeigt die IP.

**2. Caddy installieren** (Ubuntu-Paket, legt den Dienst `caddy` unter eigenem User an, etwa 30-50 MB RAM):
```bash
apt install caddy
```

**3. Firewall für Web öffnen** (80 braucht Let's Encrypt zur Prüfung und für die Weiterleitung auf https):
```bash
ufw allow 80/tcp comment 'caddy'
ufw allow 443/tcp comment 'caddy'
```

**4. Caddy einrichten**, die Datei `/etc/caddy/Caddyfile` komplett ersetzen durch:
```
kcal.meldro.de {
	handle /steps {
		reverse_proxy 127.0.0.1:8787
	}
	handle {
		respond 404
	}
}
```
Nur `/steps` wird durchgereicht, alles andere ergibt 404. Ohne `log`-Eintrag schreibt Caddy kein Zugriffslog,
der Schlüssel aus der URL landet also nirgends. Dann:
```bash
systemctl reload caddy
```
Prüfen: `curl -s -o /dev/null -w '%{http_code}\n' 'https://kcal.meldro.de/steps?key=x'` muss `403` zeigen
(kcalbot antwortet, der Schlüssel ist falsch). Ab hier gehen alter und neuer Weg parallel.

Stand 27.10.2026: Schritte 2-4 erledigt. Updates eingespielt (kein Neustart nötig), Caddy 2.6.2 läuft, ufw 80/443
offen, Zertifikat von Let's Encrypt bis 25.01.2027 (Caddy erneuert selbst). Geprüft vom Server: /steps mit falschem
Schlüssel 403 (IPv4 und IPv6), / ergibt 404, http leitet auf https um (308).

**5. kcalbot auf den neuen Link umstellen**, in `/opt/kcalbot/.env` die Zeile ändern:
```
PUBLIC_URL=https://kcal.meldro.de
```
Optional jetzt die Schlüssel erneuern (Entscheidung 2, Befehl in kcalbot-rechte.md), dann:
```bash
systemctl restart kcalbot
```

**6. Nutzer umstellen.** Jeder Nutzer ruft `/schritte_link` auf und trägt die neue URL im Kurzbefehl ein. Wer das
ist, zeigt `/nutzer` beim Bot. Frist zum Beispiel eine Woche. Wurden die Schlüssel erneuert, funktioniert der alte
Link sofort nicht mehr (Antwort „forbidden“), also vorher Bescheid geben.

**7. Alten Weg schließen**, nach der Frist:
- In bot.py Zeile 531 `"0.0.0.0"` durch `"127.0.0.1"` ersetzen (Datei gehört bot: `sudo -u bot nano /opt/kcalbot/bot.py`),
  dann `systemctl restart kcalbot`. Prüfen: `ss -ltn | grep 8787` zeigt `127.0.0.1:8787`.
- Firewall-Regeln für 8787 löschen. Die Nummern verschieben sich nach jedem Löschen, darum jeweils neu nachsehen:
  `ufw status numbered`, dann `ufw delete <nummer>` für `8787/tcp`, danach dasselbe für `8787/tcp (v6)`.

## Zurück, falls etwas nicht geht
- Bis Schritt 6 läuft der alte Link weiter. Zurück: `PUBLIC_URL` auf den alten Wert, `systemctl restart kcalbot`.
- Caddy wieder entfernen: `systemctl disable --now caddy`, `ufw delete allow 80/tcp`, `ufw delete allow 443/tcp`.

## Was bleibt
- Wer einen Schlüssel kennt, kann weiterhin Schritte eintragen, nur mitlesen kann ihn niemand mehr.
- Caddy ist ein neuer Dienst, der aus dem Internet erreichbar ist. Ubuntu-Sicherheitsupdates gelten auch für ihn
  (die offenen Updates vom Login sind noch nicht eingespielt).
