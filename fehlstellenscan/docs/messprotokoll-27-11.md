# Messprotokoll Äste (Termin bei Felix, 27.11.2026)

Stand 23.11.2026. Gehört zu docs/plan-trainingswerkzeug.md (Phase 0) und docs/entwurf-aufnahme-apparatur.md.
Zweck: echte Maße am Holz, gegen die wir später das Modell prüfen. Ohne diese Werte können wir nie sagen, wie
genau das Modell in mm misst. Eingabe danach in eine Tabelle (CSV, siehe unten), auswertung.py rechnet.

## Was wir brauchen
- 2 bis 3 Balken, je eine Seite, darauf zusammen 10 bis 20 Äste, gemischt: klein (unter 10 mm), mittel, groß,
  hell und dunkel, rund und lang gezogen. Lieber 15 sorgfältig als 40 schnell.
- Diese Balken werden nur Test, nie Training. Darum schreiben wir sie hier auf (Balkennummer).
- Messschieber, Zollstock oder Maßband (für die Lage), Kreide, Stift, diese Seite.

## Vorbereitung am Balken
1. Balkennummer und Seite wie beim Fotografieren (Klappenbild, Kurzbefehl). Ein Ende mit Kreide „A“ markieren:
   Dort beginnt die Messung längs und dort steht die Box beim ersten Foto.
2. Eine Kante mit Kreide als Bezugskante markieren (Strich „K“ auf der Fläche nahe der Kante): quer wird ab
   dieser Kante gemessen. Im Klappenbild festhalten, welche Kante K ist.
3. Jeden ausgewählten Ast mit einer kleinen Nummer neben (nicht auf) den Ast schreiben, 1 bis 20. Nichts auf den
   Ast malen und den Ast nicht einkreisen: Kreide auf dem Ast verändert genau das, was das Modell sehen soll.
4. Erst fotografieren (wie geplant), dann messen. So sind die Nummern auf den Fotos und wir finden jeden Ast
   wieder.

## Messen je Ast
- l: Abstand vom Ende A bis zur Mitte des Asts, längs, in mm (Zollstock reicht, auf 5 mm genau).
- q: Abstand von Kante K bis zur Mitte des Asts, quer, in mm (Messschieber oder Zollstock, auf 2 mm genau).
- d_min: kleinster sichtbarer Durchmesser des Asts, mit Messschieber, auf 0,5 mm.
- d_max: größter sichtbarer Durchmesser, mit Messschieber, auf 0,5 mm.
- Wo der Ast aufhört, entscheidet ihr am Holz (Übergang vom Ast zum Holz). Bei dunklem Ring oder Rinde um den
  Ast unter Bemerkung „Ring“ notieren und den Durchmesser ohne Ring messen; den mit Ring, wenn Zeit ist, als
  zweite Zeile mit Bemerkung „mit Ring“. Was die Norm hier will, klären wir mit Henri.

## Zweite Messung (wie genau messen Menschen?)
Bei 5 Ästen misst eine zweite Person d_min und d_max noch einmal, ohne die ersten Werte zu sehen (Zettel umklappen).
Die Abweichung zwischen euch beiden ist die Grenze, unter der wir vom Modell nichts verlangen können.

## Tabelle (auf Papier, danach als CSV)

| Balken | Seite | Ast | l mm | q mm | d_min mm | d_max mm | Messer | Bemerkung |
|---|---|---|---|---|---|---|---|---|
| | | 1 | | | | | | |
| | | 2 | | | | | | |
| | | 3 | | | | | | |
| | | 4 | | | | | | |
| | | 5 | | | | | | |
| | | 6 | | | | | | |
| | | 7 | | | | | | |
| | | 8 | | | | | | |
| | | 9 | | | | | | |
| | | 10 | | | | | | |
| | | 11 | | | | | | |
| | | 12 | | | | | | |
| | | 13 | | | | | | |
| | | 14 | | | | | | |
| | | 15 | | | | | | |

Messer: Kürzel (F für Felix, J für Jan, H für Henri). Zweite Messung als eigene Zeile mit gleicher Astnummer und
anderem Messer.

## CSV für auswertung.py
Eine Datei messung.csv, Semikolon, Komma oder Punkt als Dezimalzeichen, erste Zeile genau so:

    balken;seite;ast;l_mm;q_mm;d_min_mm;d_max_mm;messer;bemerkung
    B07;A;1;412;63;14,5;22;F;
    B07;A;1;;;15;21,5;J;zweite Messung

Leere l und q in der zweiten Messung sind erlaubt (Lage steht schon in der ersten Zeile).

Auswertung auf dem Server, sobald Fotos, Streifenbild und Vorhersage da sind (balken.py kacheln/karte):

    .venv/bin/python auswertung.py messung --messungen messung.csv --funde <karte>/funde.json --balken B07 --seite A --ausgabe <ordner>

Ergebnis: je Ast Modell gegen Messschieber, mittlere Abweichung und Streuung des kleinsten Durchmessers, Äste ohne
Fund, Abweichung zwischen zwei Messenden.
