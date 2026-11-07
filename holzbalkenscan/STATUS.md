# Status: Agent holzbalkenscan

## Zweck
Prüfstand für ein fremdes Forschungsverfahren, das Handyfotos einer Holzbauteilseite zu einem
maßhaltigen Streifenbild zusammensetzt. Der Prüfstand rechnet die Fotoreihen nach, liest die
Kennzahlen aus und vergleicht sie mit dem Vorlauf. Plan von Jan am 06.11.2026 freigegeben.

## Stand (07.11.2026)
- Prüfstand fertig und getestet (47 Tests, auch eine echte Speichergrenze per systemd-run), pruefen.sh grün.
- Reihe ISO 800 echt gerechnet: Lauf 20261107-010055 (Grenze 2800M) gelungen, Meldung an Jan gesendet.
  Nahtversatz Median 0,11 / max 0,31 mm, Länge roh -4,02 %, gegen den Referenzbericht nur kleine Abweichungen
  (Länge +12 mm, Kantenstreuung +0,07 mm, Nahtkanten 59 -> 53). Speicherspitzen: Vorprüfung 508 MB (114 s),
  Zusammenbau 1250 MB (496 s).
- Dienst nicht installiert, die Zentrale kennt den Agenten noch nicht (Bedarf 31 in ../STATUS.md).
- Auftrag Jan (07.11.): Felix' Verfahren nachweisbar verbessern, zuerst die Zuordnung (F5). Felix' übrige
  Reihen (261019 B, C, 261022 V1, V2) gibt es nicht, auf dem SharePoint liegt nur ISO 800 (Jan bestätigt).
  Mit Jans Okay stattdessen drei aus A abgeleitete Prüffälle (prueffaelle.py). Nächster Schritt: Plan für die
  neue Zuordnung liegt Jan vor, Umsetzung erst nach Okay (eigene Fassung verfahren_neu/, verfahren/ bleibt).

## Grundlinie: Felix' Code unverändert (Codefassung 9a26847fe5ed)
| Reihe | gelingt | direkte Nachbarpaare | Punktpaare 1. / 2. Durchgang | je Naht | abgehängt | Nahtversatz Median / max | Länge roh | Px/mm Band | Spitze |
|---|---|---|---|---|---|---|---|---|---|
| ISO 800 (A) | ja | 25 von 25 | 330 / 1296 | 51,8 | 0 | 0,11 / 0,31 mm | -4,02 % | 8,90 | 1250 MB |
| pf-luecke | ja | 24 von 24 | 299 / 1194 | 49,8 | 0 | 0,09 / 0,32 mm | -4,21 % | 9,11 | 1249 MB |
| pf-schmal | ja | 24 von 25 | 364 / 1315 | 54,8 | 1 (IMG_2230) | 0,14 / 0,49 mm | -2,24 % | 8,83 | 1116 MB |
| pf-flau | nein | 24 von 25, Versätze falsch | 273 / – | – | 10 (2230–2239) | – | – | 12,87 | über 2700 MB |
Läufe 20261107-010055, -014959, -015943, -020947 (pf-flau auch -014106 mit 2G). Kennzahlen bei pf-flau aus der
Konsolenausgabe, der Bericht fehlt, weil das Zeichnen an der Speichergrenze abbrach (mehr als 2700M ist neben den
übrigen Diensten nicht frei).
- pf-flau bildet Reihe C nach: 13 Bilder mit flauer Kante kippen die Bandbreite der GANZEN Reihe (12,87 statt 8,9
  Px/mm, Kantenrest Median 191 statt 14 Px), die Streifen sind falsch entzerrt, die direkten Paare zeigen Versätze
  um 0 bis 20 mm statt rund 250 mm (falsche Treffer), 10 Aufnahmen hängen ab. Das ist genau die Kette aus P2a/P4.
- pf-schmal bildet Reihe B NICHT nach: halbe Fläche allein senkt die Ausbeute nicht (54,8 statt 51,8 je Naht).
  Felix' Erklärung für B (zu wenig Bildfläche) ist damit an A nicht bestätigt; B hatte vermutlich weitere Ursachen.
- pf-luecke: eine fehlende Aufnahme überbrückt das Verfahren ohne Verlust.
- Nahtversatz misst nur die innere Stimmigkeit, nicht die Maßtreue. Künstliche Fälle ersetzen keine echten Reihen.

## Prüffälle (prueffaelle.py, Daten in data/reihen/pf-*, je Ordner herkunft.json)
- Abgeleitet aus ISO 800 mit der Lage der Bauteilebene je Bild aus Lauf 20261107-010055 (streifen.modell.pkl).
- pf-luecke: IMG_2242 fehlt (übrige Fotos als Hardlinks).
- pf-schmal: Fläche v < 115 mm durch den Hintergrund davor ersetzt, Höhe 115 mm, Bauteilanteil etwa 13 %.
  In den Endbildern (2230, 2255) liegt die Modellkante bis 20 mm daneben, dort ist der Balken etwas breiter.
- pf-flau: IMG_2236–2248, Hintergrund hinter der Kante v = 230 je Kanal auf das Holzmittel (+5 Graustufen),
  Pflastertextur bleibt. Kontrast vorher 46–61, nachher 5–8 Graustufen.
- Erzeugen (etwa 40 min): systemd-run --user --scope -q -p MemoryMax=1500M .venv/bin/python prueffaelle.py
  "data/laeufe/20261107-010055/ISO 800"

## Aufbau
- verfahren/: fremder Code, byte-gleich aus /home/agent/holzbalken-skript/Code (zusammensetzen2.py,
  pruefen.py, kantenbild.py, bauteil_vorlage.json, KONZEPT.md, LIESMICH_FUER_REVIEW.md, PROBLEMSTELLUNG.md).
  Nicht ändern. ruff.toml nimmt ihn aus, Tests laufen nur in tests/.
- kennzahlen.py: aus_zusammenbau(text), aus_vorpruefung(text). Rein, die letzte Fundstelle gilt, fehlende Werte None.
  Zuordnung: direkte_paare, bildpaare_1, punktpaare_1, punktpaare_2, punktpaare_je_naht, verwendet, abgehaengt
  (liest auch die Konsolenausgabe, wenn der Bericht fehlt).
- pruefstand.py: Codefassung (sha256 über verfahren/*.py, *.json), Reihen finden und wählen, Speicherprüfung
  (MemAvailable gegen Grenze + 500 MB), systemd-run-Scope mit MemoryMax, Status je Schritt, Ablage,
  Vorlauf/Referenz, Vergleich mit Schwellen, Meldetext.
- agent.py: je Auftrag Speicher prüfen, je Reihe pruefen.py (--bericht) und zusammensetzen2.py (--ziel), jeder
  Schritt im eigenen Scope, Zeitgrenze 60 min, Speicherspitze per os.wait4. Ergebnis als Meldung
  (agentkit.meldungen), Auftrag mit einem Satz abgeschlossen. Ohne Claude, ohne Timer, Sperre data/lauf.sperre.
- Auftragstext: Reihennamen (sonst alle), "speicher 4G" (Standard 3G, geschätzt).
- Daten (nicht im Repo): data/reihen/<reihe>/ (Fotos + bauteil.json), data/referenz/<reihe>.txt (Bericht des
  Auftraggebers, Vergleichsbasis ohne Vorlauf), data/laeufe/<lauf-id>/lauf.json und je Reihe Berichte,
  Konsolenausgabe, streifen.jpg.
- Reihen: "ISO 800" (26 Fotos, Testbalken 261019 Seite A; Referenz streifen_v40_ISO800.txt, Nahtversatz 0,09 mm).
  Die Rechenzeit im Referenzbericht (33 s) ist nur der Zeichenteil (--weiter), der Vergleich zeigt sie darum als Änderung.
- Dienst: systemd/holzbalkenscan.service (Vorlage, nicht installiert).

## Auftrag von Hand (bis die Zentrale den Agenten kennt)
    cd ~/agenten/holzbalkenscan
    .venv/bin/python -c "from agentkit import auftraege; print(auftraege.neuer_auftrag('holzbalkenscan', 'ISO 800', quelle='hand'))"
    .venv/bin/python agent.py

## Entscheidungen
- 07.11.2026: Exit 1 von zusammensetzen2.py gilt als gelungen (heißt nur "mit Prüfpunkten"), Exit 0/1/2 von
  pruefen.py ebenso (grün/gelb/rot steht im Bericht).
- 07.11.2026: Reicht der Speicher nicht, wird der Auftrag als fehlgeschlagen abgeschlossen statt zu warten
  (es gibt keinen Timer, der ihn später holen würde).

## Offene Punkte
1. Echte zweite Reihe fehlt (Felix fragen oder neu aufnehmen). Download-Weg vom SharePoint (Ordner Panorama,
   Freigabelink von Jan vom 06.11.): Freigabelink mit curl -c holt ein Gast-Cookie (FedAuth); Liste per
   _api/web/GetFolderByServerRelativeUrl('/personal/jkl298_hnee_de/Documents/Forschungsprojekt_Lamellen-Scan/
   Panorama/Input/<reihe>')?$expand=Files. Dateien über _layouts/15/download.aspx?SourceUrl=<pfad> laden,
   nicht über /$value (brach ab). Nach jedem Download Größe gegen Length aus der Liste prüfen
   (der agent meldet unvollständige Fotos inzwischen selbst).
2. SPEICHER_STANDARD (3G) liegt über dem, was meist frei ist (~3,2 GB, nötig Grenze + 500 MB). Gelungene Läufe
   brauchen 1116–1250 MB, der gescheiterte pf-flau über 2700 MB. Vorschlag: Standard 2G, Jan entscheidet.
3. Danach Zweiteinschätzung F0–F8 (verfahren/PROBLEMSTELLUNG.md) per agentkit.claude_lauf.
4. Dienst installieren und Eintrag in der Zentrale (Bedarf 31 im Hauptstatus), beides mit Jans Okay.
5. Wenn Jan das doppelt findet: Meldung und Auftragsergebnis zu einer Nachricht zusammenlegen.
6. Liegengebliebene fehlgeschlagene Test-Scopes (holzbalkenscan-test-*) in systemd: mit
   systemctl --user reset-failed wegräumen, wenn Jan will; ob die Tests sie selbst aufräumen sollten, offen.

## Gelernte Regeln
- (noch keine)
