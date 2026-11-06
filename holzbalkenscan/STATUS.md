# Status: Agent holzbalkenscan

## Zweck
Prüfstand für ein fremdes Forschungsverfahren, das Handyfotos einer Holzbauteilseite zu einem
maßhaltigen Streifenbild zusammensetzt. Der Prüfstand rechnet die Fotoreihen nach, liest die
Kennzahlen aus und vergleicht sie mit dem Vorlauf. Plan von Jan am 06.11.2026 freigegeben.

## Stand (07.11.2026)
- Prüfstand fertig und getestet (36 Tests, auch eine echte Speichergrenze per systemd-run), pruefen.sh grün.
- Noch kein echter Lauf mit den 48-MP-Fotos (wartet auf Jans Okay).
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
1. Erster echter Lauf ISO 800 (07.11., Lauf 20261107-004413, Grenze 3000M, mit Jans Okay) scheiterte an zwei
   unvollständigen Fotos vom SharePoint-Download: IMG_2252.jpg (10223616 Byte) und IMG_2255.jpg (2818048 Byte)
   enden mitten im Bild. Jan lädt sie neu, dann Lauf wiederholen (vorher free -m, Jan fragen).
   Speicherspitzen bis zum Abbruch: Vorprüfung 417 MB (89 s), Zusammenbau 472 MB (28 s); die volle Spitze
   ist noch unbekannt, SPEICHER_STANDARD danach anpassen.
2. Zweite Reihe 261022_Test fehlt noch (von Jans SharePoint holen, nach data/reihen/).
3. Danach Zweiteinschätzung F0–F8 (verfahren/PROBLEMSTELLUNG.md) per agentkit.claude_lauf.
4. Dienst installieren und Eintrag in der Zentrale (Bedarf 31 im Hauptstatus), beides mit Jans Okay.
5. Wenn Jan das doppelt findet: Meldung und Auftragsergebnis zu einer Nachricht zusammenlegen.

## Gelernte Regeln
- (noch keine)
