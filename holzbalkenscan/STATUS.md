# Status: Agent holzbalkenscan

## Zweck
Prüfstand für ein fremdes Forschungsverfahren, das Handyfotos einer Holzbauteilseite zu einem
maßhaltigen Streifenbild zusammensetzt. Der Prüfstand rechnet die Fotoreihen nach, liest die
Kennzahlen aus und vergleicht sie mit dem Vorlauf. Plan von Jan am 06.11.2026 freigegeben.

## Stand (07.11.2026)
- Prüfstand fertig und getestet (64 Tests, auch eine echte Speichergrenze per systemd-run), pruefen.sh grün.
- Reihe ISO 800 echt gerechnet: Lauf 20261107-010055 (Grenze 2800M) gelungen, Meldung an Jan gesendet.
  Nahtversatz Median 0,11 / max 0,31 mm, Länge roh -4,02 %, gegen den Referenzbericht nur kleine Abweichungen
  (Länge +12 mm, Kantenstreuung +0,07 mm, Nahtkanten 59 -> 53). Speicherspitzen: Vorprüfung 508 MB (114 s),
  Zusammenbau 1250 MB (496 s).
- Dienst nicht installiert, die Zentrale kennt den Agenten noch nicht (Bedarf 31 in ../STATUS.md).
- Auftrag Jan (07.11.): Felix' Verfahren nachweisbar verbessern, zuerst die Zuordnung (F5). Felix' übrige
  Reihen (261019 B, C, 261022 V1, V2) gibt es nicht, auf dem SharePoint liegt nur ISO 800 (Jan bestätigt).
  Mit Jans Okay stattdessen drei aus A abgeleitete Prüffälle (prueffaelle.py). Plan für die neue Zuordnung von
  Jan freigegeben, gebaut in verfahren_neu/ (Rohbild-Zuordnung, dazu zweiter Achsentest aus der Bewegung) und
  gemessen (Tabelle unten): pf-flau gelingt jetzt, A im Median gleich. Auf Jans Wunsch beide Änderungen getrennt
  gemessen (Fassung achse): Der Achsentest allein reicht für pf-flau nicht, die Rohbild-Zuordnung trägt.
  Behalten oder nicht: Jan (Offener Punkt 1).

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
- pf-flau scheitert schon am Achsentest (Schritt 1), nicht erst an der Zuordnung: Die 13 flauen Bilder lassen
  "laengs der Spalten" gewinnen (Streuung der Bandbreite 29,4 gegen 53,1 %), das Arbeitsbild ist um 90 Grad
  falsch gedreht (6048 x 8064 statt 8064 x 6048). Daraus folgen Band 12,87 statt 8,9 Px/mm, Kantenrest 191 statt
  14 Px, Versätze um 0 bis 20 mm statt rund 250 mm und 10 abgehängte Aufnahmen. Fehlerklasse wie P8. Ob Felix'
  Reihe C an derselben Stelle scheitert, ist offen (sein Bericht nennt die Kanten).
- pf-schmal bildet Reihe B NICHT nach: halbe Fläche allein senkt die Ausbeute nicht (54,8 statt 51,8 je Naht).
  Felix' Erklärung für B (zu wenig Bildfläche) ist damit an A nicht bestätigt; B hatte vermutlich weitere Ursachen.
- pf-luecke: eine fehlende Aufnahme überbrückt das Verfahren ohne Verlust.
- Nahtversatz misst nur die innere Stimmigkeit, nicht die Maßtreue. Künstliche Fälle ersetzen keine echten Reihen.

## Neue Fassung verfahren_neu/: gemessen 07.11.2026
Zwei Änderungen gegen Felix' Code, beide mit Jans Okay:
1. Zuordnung im Rohbild (F5): Punktpaare zuerst direkt im unveränderten Foto statt auf den aus den Kanten
   entzerrten Streifen.
2. Zweiter Achsentest aus der Bewegung: an 6 Bildpaaren die Richtung, in die sich die Ebene mit der größten
   Bewegung (das Bauteil) verschiebt, Suche im ganzen Bild ohne Annahme über die Achse. Ist das Urteil eindeutig
   und weicht vom Bandtest ab, gilt die Bewegung (Meldung im Prüfbericht). Kostet etwa 95 s je Reihe.
Je Reihe alt (Grundlinie oben) gegen neu (Läufe 20261107-052530 pf-flau, -054543 A, -060604 pf-luecke,
-062623 pf-schmal; Grenze je 2G).
| Reihe | gelingt | Punktpaare 1. Durchgang | 2. Durchgang | je Naht | abgehängt | Nahtversatz Median | max | Rest Punktpaare | Länge roh | Px/mm Band | sichtbare Nahtkanten | Rechenzeit | Spitze |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ISO 800 (A) | ja / ja | 330 / 1503 | 1296 / 1365 | 51,8 / 54,6 | 0 / 0 | 0,11 / 0,12 mm | 0,31 / 0,43 mm | 0,293 / 0,225 mm | -4,02 / -3,35 % | 8,90 / 8,90 | 53 / 71 | 496 / 1105 s | 1250 / 1211 MB |
| pf-luecke | ja / ja | 299 / 1305 | 1194 / 1227 | 49,8 / 51,1 | 0 / 0 | 0,09 / 0,08 mm | 0,32 / 0,32 mm | 0,335 / 0,259 mm | -4,21 / -3,28 % | 9,11 / 9,11 | 55 / 66 | 473 / 1110 s | 1249 / 1213 MB |
| pf-schmal | ja / ja | 364 / 674 | 1315 / 1216 | 54,8 / 50,7 | 1 / 1 | 0,14 / 0,10 mm | 0,49 / 0,56 mm | 0,231 / 0,319 mm | -2,24 / -3,10 % | 8,83 / 8,83 | 80 / 84 | 463 / 1289 s | 1116 / 1013 MB |
| pf-flau | **nein / ja** | 273 / 1348 | – / 1301 | – / 52,0 | 10 / 0 | – / 0,15 mm | – / 0,72 mm | 3,78 / 0,30 mm | – / -3,16 % | 12,87 / 9,39 | – / 46 | – / 1096 s | über 2700 / 1207 MB |
- pf-flau gelingt jetzt: Der Bandtest wählt weiter die falsche Achse (Streuung 53,1 gegen 29,4 %), die Bewegung
  (alle 6 Paare: dy 194 bis 406 Px, dx unter 27 Px) überstimmt ihn. Danach trägt die Rohbild-Zuordnung (25 von 25
  direkten Paaren). Bandbreite 9,39 statt 8,90 Px/mm wie bei A: in den flauen Bildern bleibt das Band 5 % zu
  breit (P1/P2a nicht gelöst). Größter Nahtversatz 0,72 mm, deutlich über A.
- Messregel (mit Jan): mehr Reihen gelingen (pf-flau) und A wird nicht schlechter im Median (+0,01 mm) und je
  Naht (+2,8). Schlechter in A: größter Nahtversatz 0,31 -> 0,43 mm, sichtbare Nahtkanten 53 -> 71. pf-schmal:
  weniger Punktpaare je Naht (54,8 -> 50,7). Rechenzeit gut doppelt (etwa 18 statt 8 min je Reihe).
- In A ist die Reihenfolge der Aufnahmen jetzt durchgehend aufsteigend; Felix' Lauf hatte bei 2250..2253 ein
  Zickzack (2251 -> 2252: 5 Paare und -281 mm, neu 41 Paare und +256 mm).
- Endbild 2230 -> 2231: richtige Ebene gefunden (3255 Px), aber über der Toleranz 45 % zum Median verworfen, dann
  Felix' Streifenweg. Toleranz nicht geändert (ohne Messung).
- Nahtversatz und Rest der Punktpaare messen nur die innere Stimmigkeit, nicht die Maßtreue. Die rohe Länge ist
  keine Probe (die Aufmaßlänge ist Eingangsgröße, P6). pf-flau ist künstlich, keine echte Reihe C.

## Getrennt gemessen: nur der Achsentest (Fassung achse, 07.11.2026)
Fassung achse = verfahren_neu/ mit --ohne-rohbild: Felix' Zuordnung auf den Streifen, dazu nur der zweite
Achsentest. Läufe 20261107-113330 A, -114514 pf-luecke, -115612 pf-schmal, -120710 pf-flau (Grenze je 3000M).
| Reihe | gelingt alt / achse / neu | abgehängt | je Naht | Nahtversatz Median | max | Länge roh | Rechenzeit |
|---|---|---|---|---|---|---|---|
| ISO 800 (A) | ja / ja / ja | 0 / 0 / 0 | 51,8 / 51,8 / 54,6 | 0,11 / 0,11 / 0,12 mm | 0,31 / 0,31 / 0,43 mm | -4,02 / -4,02 / -3,35 % | 496 / 591 / 1105 s |
| pf-luecke | ja / ja / ja | 0 / 0 / 0 | 49,8 / 49,8 / 51,1 | 0,09 / 0,09 / 0,08 mm | 0,32 / 0,32 / 0,32 mm | -4,21 / -4,21 / -3,28 % | 473 / 550 / 1110 s |
| pf-schmal | ja / ja / ja | 1 / 1 / 1 | 54,8 / 54,8 / 50,7 | 0,14 / 0,14 / 0,10 mm | 0,49 / 0,49 / 0,56 mm | -2,24 / -2,24 / -3,10 % | 463 / 550 / 1289 s |
| pf-flau | nein / **halb** / ja | 10 / **13** / 0 | – / 42,1 / 52,0 | – / 0,40 / 0,15 mm | – / 1,25 / 0,72 mm | – / -6,37 / -3,16 % | – / 438 / 1096 s |
- A, pf-luecke, pf-schmal: achse rechnet genau wie Felix (alle Kennzahlen gleich), nur etwa 80–95 s länger für den
  Achsentest. Der Test schadet also nicht.
- pf-flau mit achse: Achse jetzt richtig, der Lauf bricht nicht mehr ab, aber Felix' Zuordnung verbindet nur 13 von
  26 Aufnahmen (IMG_2230–2235 und 2249–2255 ohne Verbindung, 23 von 25 direkten Paaren, Rest der Punktpaare
  2,28 mm). Der Streifen zeigt also nur die halbe Reihe, Status "ok" täuscht. Für pf-flau braucht es die
  Rohbild-Zuordnung.
- Folgerung: Achsentest = reiner Gewinn ohne Nachteil. Rohbild-Zuordnung = nötig für pf-flau, kostet in A aber
  größten Nahtversatz (0,31 -> 0,43 mm), Nahtkanten (53 -> 71) und Rechenzeit (gut doppelt).

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
- verfahren_neu/: Kopie von zusammensetzen2.py, pruefen.py, kantenbild.py, bauteil_vorlage.json. Geändert nur
  zusammensetzen2.py, Schritt 3 (direkte und weitere Nachbarn): zuerst zuordnung_roh im Rohbild, Paare per
  inv(H0) in Streifenkoordinaten, Nachlauf mit der Median-Bewegung der Reihe, Rückfall auf Felix' Streifenweg.
  zuordnung_roh.py (neu, getestet): grob Teiler 8 über das ganze Bild (NCC mit Eindeutigkeit, RANSAC-Homographien
  bis 5 Ebenen, Wahl = größte Bewegung bzw. nächste an der Vorgabe), fein Teiler 2 nach Vorwarp, RANSAC.
  Annahme: längs = Bildzeilen im Arbeitsbild (Suchfenster längs weit, quer eng). Dazu achse_urteil /
  bewegung_beidseitig (NccFeld, Suche im ganzen Bild) als zweiter Achsentest, eingehängt nach achse_bestimmen.
  ruff.toml im Ordner nimmt nur die Kopien aus.
- kennzahlen.py: aus_zusammenbau(text), aus_vorpruefung(text). Rein, die letzte Fundstelle gilt, fehlende Werte None.
  Zuordnung: direkte_paare, bildpaare_1, punktpaare_1, punktpaare_2, punktpaare_je_naht, verwendet, abgehaengt
  (liest auch die Konsolenausgabe, wenn der Bericht fehlt).
- pruefstand.py: Codefassung (sha256 über *.py, *.json der gewählten Fassung), Fassung aus dem Auftrag ("fassung
  neu", "fassung achse"; lauf.json "fassung", ohne Angabe alt), Vergleich neu und achse immer gegen den letzten Lauf der alten Fassung (auch
  einen gescheiterten), Reihen finden und wählen, Speicherprüfung
  (MemAvailable gegen Grenze + 500 MB), systemd-run-Scope mit MemoryMax, Status je Schritt, Ablage,
  Vorlauf/Referenz, Vergleich mit Schwellen, Meldetext.
- agent.py: je Auftrag Speicher prüfen, je Reihe pruefen.py (--bericht) und zusammensetzen2.py (--ziel), jeder
  Schritt im eigenen Scope, Zeitgrenze 60 min, Speicherspitze per os.wait4. Ergebnis als Meldung
  (agentkit.meldungen), Auftrag mit einem Satz abgeschlossen. Ohne Claude, ohne Timer, Sperre data/lauf.sperre.
  Fehlt ein Bericht (Abbruch), liest er die Kennzahlen aus der Konsolenausgabe.
- Auftragstext: Reihennamen (sonst alle), "speicher 4G" (Standard 3G, geschätzt), "fassung neu" oder "fassung achse"
  (verfahren_neu/ mit --ohne-rohbild: Felix' Zuordnung, nur der zweite Achsentest).
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
Neue Fassung: Auftragstext z. B. 'pf-flau fassung neu speicher 2500M'. Je Auftrag eine Reihe; der Agent nimmt
einen Auftrag nur an, wenn Grenze + 500 MB frei sind (sonst "nicht gerechnet", neu einstellen).

## Entscheidungen
- 07.11.2026: Exit 1 von zusammensetzen2.py gilt als gelungen (heißt nur "mit Prüfpunkten"), Exit 0/1/2 von
  pruefen.py ebenso (grün/gelb/rot steht im Bericht).
- 07.11.2026: Reicht der Speicher nicht, wird der Auftrag als fehlgeschlagen abgeschlossen statt zu warten
  (es gibt keinen Timer, der ihn später holen würde).

## Offene Punkte
1. Entscheidung Jan: neue Fassung behalten oder nicht (siehe Messung, auch "Getrennt gemessen"). Mögliche nächste Schritte, je einzeln
   gegen die Grundlinie messen: Band/Startposen aus der Rohbild-Bewegung (Plan-Schritt 3, zielt auf das 5 % zu
   breite Band in pf-flau); größten Nahtversatz und sichtbare Nahtkanten in A untersuchen.
2. Rechenzeit der neuen Fassung etwa doppelt (grobe Suche über das ganze Bild je Paar, etwa 13 s); bei Bedarf
   Kachelraster ausdünnen, erst messen.
3. Echte zweite Reihe fehlt (Felix fragen oder neu aufnehmen). Download-Weg vom SharePoint (Ordner Panorama,
   Freigabelink von Jan vom 06.11.): Freigabelink mit curl -c holt ein Gast-Cookie (FedAuth); Liste per
   _api/web/GetFolderByServerRelativeUrl('/personal/jkl298_hnee_de/Documents/Forschungsprojekt_Lamellen-Scan/
   Panorama/Input/<reihe>')?$expand=Files. Dateien über _layouts/15/download.aspx?SourceUrl=<pfad> laden,
   nicht über /$value (brach ab). Nach jedem Download Größe gegen Length aus der Liste prüfen
   (der agent meldet unvollständige Fotos inzwischen selbst).
4. SPEICHER_STANDARD (3G) liegt über dem, was meist frei ist (~3,2 GB, nötig Grenze + 500 MB). Gelungene Läufe
   brauchen 1116–1250 MB, der gescheiterte pf-flau über 2700 MB. Vorschlag: Standard 2G, Jan entscheidet.
5. Danach Zweiteinschätzung F0–F8 (verfahren/PROBLEMSTELLUNG.md) per agentkit.claude_lauf.
6. Dienst installieren und Eintrag in der Zentrale (Bedarf 31 im Hauptstatus), beides mit Jans Okay.
7. Wenn Jan das doppelt findet: Meldung und Auftragsergebnis zu einer Nachricht zusammenlegen.
8. Liegengebliebene fehlgeschlagene Test-Scopes (holzbalkenscan-test-*) in systemd: mit
   systemctl --user reset-failed wegräumen, wenn Jan will; ob die Tests sie selbst aufräumen sollten, offen.

## Gelernte Regeln
- (noch keine)
