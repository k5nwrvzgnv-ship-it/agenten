# Status: Agent holzbalkenscan

## Zweck
Prüfstand für ein fremdes Forschungsverfahren, das Handyfotos einer Holzbauteilseite zu einem
maßhaltigen Streifenbild zusammensetzt. Der Prüfstand rechnet die Fotoreihen nach, liest die
Kennzahlen aus und vergleicht sie mit dem Vorlauf. Plan von Jan am 06.11.2026 freigegeben.

## Stand (07.11.2026)
- Prüfstand fertig und getestet (36 Tests, auch eine echte Speichergrenze per systemd-run), pruefen.sh grün.
- Reihe ISO 800 echt gerechnet: Lauf 20261107-010055 (Grenze 2800M) gelungen, Meldung an Jan gesendet.
  Nahtversatz Median 0,11 / max 0,31 mm, Länge roh -4,02 %, gegen den Referenzbericht nur kleine Abweichungen
  (Länge +12 mm, Kantenstreuung +0,07 mm, Nahtkanten 59 -> 53). Speicherspitzen: Vorprüfung 508 MB (114 s),
  Zusammenbau 1250 MB (496 s).
- Dienst nicht installiert, die Zentrale kennt den Agenten noch nicht (Bedarf 31 in ../STATUS.md).

## Aufbau
- verfahren/: fremder Code, byte-gleich aus /home/agent/holzbalken-skript/Code (zusammensetzen2.py,
  pruefen.py, kantenbild.py, bauteil_vorlage.json, KONZEPT.md, LIESMICH_FUER_REVIEW.md, PROBLEMSTELLUNG.md).
  Nicht ändern. ruff.toml nimmt ihn aus, Tests laufen nur in tests/.
- kennzahlen.py: aus_zusammenbau(text), aus_vorpruefung(text). Rein, die letzte Fundstelle gilt, fehlende Werte None.
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
1. Zweite Reihe 261022_Test fehlt noch (von Jans SharePoint holen, nach data/reihen/).
   SharePoint: Freigabelink mit curl -c holt ein Gast-Cookie (FedAuth); Liste per
   _api/web/GetFolderByServerRelativeUrl('/personal/jkl298_hnee_de/Documents/Forschungsprojekt_Lamellen-Scan/
   Panorama/Input/<reihe>')?$expand=Files. Dateien über _layouts/15/download.aspx?SourceUrl=<pfad> laden,
   nicht über /$value (brach ab). Nach jedem Download Größe gegen Length aus der Liste prüfen
   (der agent meldet unvollständige Fotos inzwischen selbst).
2. SPEICHER_STANDARD (3G) senken: gemessene Spitze 1250 MB bei 26 Fotos; Vorschlag erst nach der zweiten Reihe.
3. Danach Zweiteinschätzung F0–F8 (verfahren/PROBLEMSTELLUNG.md) per agentkit.claude_lauf.
4. Dienst installieren und Eintrag in der Zentrale (Bedarf 31 im Hauptstatus), beides mit Jans Okay.
5. Wenn Jan das doppelt findet: Meldung und Auftragsergebnis zu einer Nachricht zusammenlegen.
6. Liegengebliebene fehlgeschlagene Test-Scopes (holzbalkenscan-test-*) in systemd: mit
   systemctl --user reset-failed wegräumen, wenn Jan will; ob die Tests sie selbst aufräumen sollten, offen.

## Gelernte Regeln
- (noch keine)
