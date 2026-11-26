# Plan: Neurolign auf dem Server für Henri und Felix

Stand 26.11.2026, 01:20. Entschieden von Jan (26.11.2026 nachts, Auswahl im Chat):
- Neurolign (aufnahme/server.py) läuft zusätzlich als Dienst auf dem Server, immer an. Der Server ist ab dann die
  Hauptablage für Fotos und Labels. Training bleibt auf Jans Mac, der Mac holt sich die Daten per Skript.
- Henri und Felix dürfen Fotos hochladen und labeln. Training, Aufteilung, Löschen, Fotobox-Steuerung nur Jan.
- Adresse: https://neurolign.meldro.de
- Anmeldung: Passwort je Person über Caddy basicauth (jan, henri, felix), die App kennt so den Namen.

Umsetzung als Nachtauftrag ab 02:00 (neue Tokens). DNS und Caddy macht Jan morgens als root (Teil C).

## Teil A: Code (Claude, nachts)

1. Servermodus in aufnahme/server.py (Mac-Modus bleibt unverändert, vom_mac() bleibt wie es ist):
   - Start z. B. `server.py --server --port 8796 --ablage <fehlstellenscan>/data/neurolign/aufnahmen`, hört nur auf
     127.0.0.1. Port vorher mit `ss -tln` prüfen (8787, 8791, 8793, 8794, 9222 sind belegt).
   - Nutzer aus Kopfzeile `X-Nutzer`, die Caddy setzt (`header_up X-Nutzer {http.auth.user.id}`). Nur annehmen, wenn
     die Anfrage von 127.0.0.1 kommt und der Host neurolign.meldro.de ist. Ohne gültigen Nutzer: 403.
   - Rollen als reine, getestete Funktion (logik.py oder eigene Datei, z. B. aufnahme/zugang.py): jan = alles im
     Servermodus, henri und felix = lesen, hochladen, labeln. Jeder POST wird gegen die Rolle geprüft, nicht nur die
     Knöpfe versteckt.
   - Schutz wie bei der Web-App für Lia: POST nur mit passender Origin (https://neurolign.meldro.de), Balken-ID und
     Dateinamen streng prüfen (kein Pfadausbruch), Größenbegrenzung je Datei (z. B. 40 MB).
   - Im Servermodus keine Fotobox, kein iPhone-Weg /h/, kein Training (kein yolo auf dem Server), kein sips.
2. Hochladen: neue Ansicht statt Fotobox-Aufnahme. Balken-ID wählen oder neu anlegen, Seite (1-4, optional), ein
   oder mehrere Fotos. Erst nachsehen, wie „Foto vom Mac“ (···) Fotos einsortiert, und das wiederverwenden, statt
   einen zweiten Weg zu bauen. In balken.json je Foto: `von` (Nutzer) und Zeit. Einzeln hochladen (eine Anfrage je
   Foto, mit Fortschritt), damit große Dateien nicht an einem Stück hängen.
   HEIC: Pillow kann es ohne Zusatzpaket nicht. `accept="image/jpeg,image/png"` lässt iOS-Safari meist JPEG liefern;
   kommt trotzdem HEIC, klare Ablehnung mit Hinweis. Kein neues Paket ohne Jans Okay.
3. Labeln: unverändert nutzbar, je gespeichertem Label `von` und Zeit. Zwei Personen am selben Foto: der zweite
   Speichervorgang darf den ersten nicht still überschreiben (Stand mitschicken, bei Abweichung Hinweis).
   Kodytek-Auswahl nur anzeigen, wenn die Bilder auf dem Server liegen (Regel: nie alle Rohbilder auf den Server),
   sonst ausblenden.
4. Oberfläche nach Jans Regeln: Skill `ui-arbeit` laden. Knöpfe nur Symbol, keine Sätze, keine Schalter. Optik wie
   die bestehende Seite. Am gerenderten Bild prüfen (Handybreite und Rechner), als henri und als jan.
5. Abgleich mit dem Mac: mac/neurolign_abgleich.sh (rsync über `agents-user`).
   - `hoch`: neue Fotobox-Balken vom Mac auf den Server (nur Balken-Ordner, die es auf dem Server noch nicht gibt
     oder die dort noch keine Labels haben; nie --delete).
   - `runter`: ganzen Ablageordner vom Server auf den Mac vor dem Training (Labels vom Server gewinnen).
   - Regel ab dann: gelabelt wird nur noch auf neurolign.meldro.de. Das in STATUS.md und im Skript sagen.
6. Tests (tests/test_aufnahme.py, tests/test_kette.py oder neue Datei): Rollen, Nutzer aus Kopfzeile nur von
   127.0.0.1, Origin-Prüfung, Pfadprüfung, Hochladen landet richtig, `von` steht drin, henri darf nicht trainieren
   oder löschen. Server echt starten (127.0.0.1, Testordner) und mit curl beide Rollen durchspielen.

## Teil B: Dienst und Zugänge (Claude, nachts)

1. Unit-Vorlage systemd/fehlstellenscan-neurolign.service: .venv von fehlstellenscan, nur 127.0.0.1:8796,
   MemoryMax 512M, Restart=on-failure, OnFailure=ausfall@%n.service, Startgrenze. Nach ~/.config/systemd/user/
   kopieren, `systemctl --user enable --now`. Von außen ist er erst nach Teil C erreichbar.
2. Passwörter: je eines für jan, henri, felix (`python3 -c "import secrets; print(secrets.token_urlsafe(18))"`),
   im Klartext nur in fehlstellenscan/.env (chmod 600, vorher gegen .gitignore prüfen):
   NEUROLIGN_PASSWORT_JAN, _HENRI, _FELIX. Hashes mit `caddy hash-password --plaintext ...` (läuft ohne root).
3. Caddy-Block fertig zum Einfügen in data/caddy-neurolign.txt (nicht im Repo, enthält Hashes):

       neurolign.meldro.de {
           basicauth {
               jan <hash>
               henri <hash>
               felix <hash>
           }
           request_body {
               max_size 50MB
           }
           header Strict-Transport-Security "max-age=31536000"
           reverse_proxy 127.0.0.1:8796 {
               header_up X-Nutzer {http.auth.user.id}
           }
       }

   Vorher in Caddy-Doku prüfen, dass der Platzhalter `{http.auth.user.id}` stimmt (nicht raten), und den Block mit
   `caddy validate --config <kopie> --adapter caddyfile` an einer Kopie der Caddyfile im Scratchpad prüfen.
4. docs/neurolign-einrichten.md: Jans Schritte für morgen (Teil C), jeder Befehl mit kurzer Erklärung, mit Angabe,
   ob Mac oder Server und welcher Benutzer.

## Teil C: Jan morgens (als root bzw. bei INWX)

1. INWX, meldro.de, DNS: A `neurolign` -> 84.247.188.205, AAAA `neurolign` -> 2a02:c207:3020:9076::1. Heute zeigt
   neurolign.meldro.de auf den INWX-Platzhalter 185.181.104.242. (Geht auch über Claude in Chrome wie bei kcal.)
2. `ssh agents`, Block aus /home/agent/agenten/fehlstellenscan/data/caddy-neurolign.txt an /etc/caddy/Caddyfile
   anhängen, `caddy validate --config /etc/caddy/Caddyfile`, `systemctl reload caddy`.
3. Prüfen: ohne Passwort 401, mit Jans Passwort die Seite.
4. Passwörter an Henri und Felix selbst schicken (nicht über Rüdiger in die Gruppe, das wäre Handeln nach außen und
   ein Geheimnis im Gruppenverlauf).

## Grenzen für den Nachtauftrag
- Nur fehlstellenscan/ ändern. Andere Chats arbeiten parallel (am 26.11. 01:12 offene Änderungen an
  aufnahme/kette.py, bilder.py, seite/training.js, gruppe_logik.py): fremde Änderungen nicht committen und nicht
  überschreiben. Betrifft eine eigene Änderung eine Datei mit fremden offenen Änderungen, erst `git diff` lesen und
  nur die eigenen Teile anfassen; im Zweifel die Datei aussparen und in STATUS.md vermerken.
- pruefen.sh nur mit flock auf ~/agenten/commit.sperre, committen nur mit commit.sh und Pfaden.
- Kein root, keine Caddyfile, kein DNS, keine Nachricht an Henri, Felix oder die Gruppe, keine neuen Pakete.
- Kleine Schritte, je ein Commit. Am Ende STATUS.md (Abschnitt Neurolign-Server) und Meldung an Jan über die
  Zentrale (shared/meldungen/ per agentkit.meldungen), was fertig ist und was Jan morgens tun muss.
