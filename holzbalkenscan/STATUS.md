# Status: Agent holzbalkenscan

## Zweck
Prüfstand für ein fremdes Forschungsverfahren, das Handyfotos einer Holzbauteilseite zu einem
maßhaltigen Streifenbild zusammensetzt. Der Prüfstand rechnet die Fotoreihen nach, liest die
Kennzahlen aus und vergleicht sie mit dem Vorlauf. Plan von Jan am 06.11.2026 freigegeben.

## Stand (07.11.2026, Übergabe mitten in der Arbeit)
- Committet: Gerüst (.venv mit numpy 2.5.4, Pillow 13.0.0, agentkit.pth), Eintrag in pruefen.sh
  und CLAUDE.md; verfahren/ (Fremdcode, byte-gleich aus /home/agent/holzbalken-skript/Code,
  ruff.toml nimmt holzbalkenscan/verfahren aus); kennzahlen.py mit tests/test_kennzahlen.py.
- NICHT committet: pruefstand.py und tests/test_pruefstand.py (32 Tests im Ordner grün, ruff grün).
  Der Commit brach ab, weil pruefen.sh insgesamt nicht grün war. Ursache noch nicht angesehen,
  kann auch ein anderer Ordner sein.
- Fotos: data/reihen/ISO 800/ (26 Fotos + bauteil.json, aus Input/ verschoben, git ignoriert data/).
  Referenzbericht des Auftraggebers: data/referenz/ISO 800.txt (Kopie von Output-2/streifen_v40_ISO800.txt).
- Getestet am Server: systemd-run --user --scope -p MemoryMax=50M bricht einen zu großen Prozess mit
  Signal 9 ab (returncode -9), nur ihn. os.wait4 auf die Popen-PID liefert die Speicherspitze (ru_maxrss).

## Aufbau
- kennzahlen.py: aus_zusammenbau(text), aus_vorpruefung(text), rein, letzte Fundstelle gilt.
- pruefstand.py: codefassung (sha256 über verfahren/*.py,*.json), reihen_finden, auswahl (Reihen aus
  dem Auftragstext, sonst alle), speicher_aus_text ("speicher 4G"), genug_speicher (MemAvailable gegen
  Grenze + 500 MB), befehl (systemd-run-Scope), schritt_status, speichern (data/laeufe/<id>/lauf.json),
  vorlauf/basis (Vorlauf, sonst Referenzbericht), vergleichen, meldetext.
- Aufruf des Verfahrens: pruefen.py <reihe> --bericht <dir>/vorpruefung.txt (Exit 0/1/2 = grün/gelb/rot);
  zusammensetzen2.py <reihe> --ziel <dir>/streifen.jpg (schreibt streifen.txt; Exit 0/1 gelungen,
  2 Eingabe, 3 Absturz). Die Rechenzeit im Referenzbericht (33 s) ist nur der Zeichenteil (--weiter).

## Offene Punkte
1. Ursache für pruefen.sh nicht grün klären, pruefstand.py + Tests committen.
2. agent.py: Aufträge per agentkit.auftraege holen, Sperre data/lauf.sperre, Speicher prüfen, je Reihe
   beide Schritte per pruefstand.befehl (cwd = Laufordner, Ausgabe in Datei, Zeitgrenze per Timer +
   kill, os.wait4 für Spitze), Kennzahlen auslesen, lauf.json speichern, meldungen.melden mit
   meldetext, Auftrag abschliessen (kurz, Details in der Meldung). Ohne Timer, ohne Claude.
   Standard-Speichergrenze 3G ist geschätzt, bis ein echter Lauf die Spitze misst.
3. systemd/holzbalkenscan.service nach Vorlage (nicht installieren ohne Jan).
4. Die Zentrale kennt den Agenten noch nicht (shared/telegram/logik.py AGENTEN): Bedarf in die
   STATUS.md des Hauptordners schreiben. Bis dahin Auftrag von Hand anlegen.
5. Echter Lauf mit den 48-MP-Fotos nur nach Jans Okay und free -m (am 07.11. ca. 2,2 GB verfügbar).
6. Zweite Reihe 261022_Test fehlt noch (SharePoint).
7. Danach Zweiteinschätzung F0–F8 (verfahren/PROBLEMSTELLUNG.md) per agentkit.claude_lauf.

## Gelernte Regeln
- (noch keine)
