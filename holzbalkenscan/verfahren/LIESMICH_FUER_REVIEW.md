# Für die Zweiteinschätzung: was hier liegt und in welcher Reihenfolge

Dieses Paket geht an einen Gutachter, der das Projekt nicht kennt. Diese Seite
sagt, was jede Datei ist, in welchem Stand sie ist und wie man sie am besten
liest.

---

## Worum gebeten wird

Ein Verfahren setzt Smartphone-Fotoreihen eines Holzbauteils zu **einem
maßhaltigen Bild** zusammen, an dem anschließend Merkmale (Äste, Risse,
Beschädigungen) vermessen werden, bei Bauteilen bis 12 m. Das Verfahren
funktioniert bei drei von fünf bekannten Fotoreihen; die Ursachen der
Fehlschläge sind gemessen, aber nicht alle behoben.

**Die Zielgenauigkeit ist bindend festgelegt** (Projektleitung, 05.11.2026):
**±1 mm lokal am einzelnen Merkmal**, **±5 bis ±10 mm global** für die
Position eines Befunds auf dem Bauteil. Abschnitt 1 der Problemstellung führt
das auf zwei getrennte technische Größen zurück — den Quermaßstab und die
Längsdrift — und rechnet vor, welche davon heute hält und welche nicht.

Gesucht ist eine **unabhängige Einschätzung der offenen Probleme** — besonders
dazu, ob die eingeschlagenen Wege tragen oder ob an einer Stelle grundsätzlich
anders anzusetzen wäre. Die konkreten Fragen stehen am Ende von
`PROBLEMSTELLUNG.md` (Abschnitt 7, F0–F8).

---

## Lesereihenfolge

**1. `PROBLEMSTELLUNG.md`** — zuerst und vollständig.

Enthält Aufgabe, Randbedingungen, Verfahrensablauf, die neun offenen Probleme
mit Messbelegen, eine Tabelle dessen, was bereits **geprüft und verworfen**
wurde, und die acht Fragen. Alles Weitere ist Beleg dazu.

Zwei Abschnitte verdienen besondere Aufmerksamkeit:

- **Abschnitt 6 (verworfen)** — zwölf Ansätze, die gemessen gescheitert sind.
  Wer sie ohne Kenntnis vorschlägt, kostet beide Seiten Zeit.
- **Abschnitt 5, P1** — der Maßstab ist mehrdeutig, und dahinter steckt eine
  echte geometrische Entartung. Das ist das schwerwiegendste Problem.

**2. `KONZEPT.md`** — Zweck, Fehlerbudget, Einordnung ins Gesamtvorhaben.

Auszug aus dem Konzeptpapier des Forschungsvorhabens, Stand **15.10.2026**.
Beantwortet, was die Problemstellung bewusst offenlässt: **wozu** die Bilder
dienen, welche Genauigkeit die Sortieraufgabe braucht, und welche Varianten auf
dem Weg dorthin verworfen wurden.

Besonders relevant:

| Abschnitt | warum |
|---|---|
| **4.6** | Fehlerbudget und erreichbare Genauigkeiten. Nennt den dominierenden Term: die Unsicherheit der Flächenhöhe selbst, ±0,5–1,5 %, weil Altholz nicht maßhaltig ist. Da die Flächenhöhe das Maßnormal ist, ist das eine **harte Obergrenze**. |
| **4.6, „Versagensfall"** | Der konisch zulaufende Querschnitt war **vorhergesehen** — samt Dreipunktmessung am Bauteil als Erkennungsmittel. Entspricht P3 der Problemstellung. |
| **4.12** | Mitgeführter Maßstab im Bild: einschließlich des Tiefenproblems (10 mm Versatz = 1,7 % Fehler bei 600 mm Abstand) und der Unterscheidung „starr an der Kamera" gegen „auf die Bauteilebene bezogen". Entspricht P6. |
| **4.13** | Was die Beschränkung auf Pillow/numpy messbar kostet — an einer früheren Versuchsreihe quantifiziert. Direkter Beitrag zu **F7**. |
| **6.2** | Eine Anforderung, die in der Problemstellung fehlt: **alle vier Bauteilseiten brauchen denselben Nullpunkt**, sonst liegt x = 2340 mm nicht auf beiden Seiten an derselben Station. |
| **6.5** | Die normative Vorfrage: ob eine Sortierbeurteilung *vom Bild* überhaupt zulässig ist. Nicht technisch, aber es rahmt alles. |

> ### Achtung: Das Konzept ist älter als der Code
>
> Das Papier ist vom 15.10. und trägt selbst den Vermerk „Entwurf, nichts davon
> ist umgesetzt". Inzwischen ist vieles umgesetzt — und **an sieben Stellen hat
> die Messung das Konzept überholt.** Im Zweifel gilt die Problemstellung.
>
> | Konzept sagt | gemessener Stand |
> |---|---|
> | **§4.6: Toleranz** — ±1–2 % gesamt, Befundposition ±5–10 mm auf 4 m | Inzwischen präzisiert und bindend: **±1 mm lokal am Merkmal, ±5–10 mm global für Befundpositionen.** Die Angabe „±1–2 % Gesamtabweichung" ist damit überholt — sie wäre für die lokale Messung zu grob (2 % von 30 mm = 0,6 mm liegt knapp, 2 % von 200 mm = 4 mm nicht mehr). Maßgeblich ist Abschnitt 1 der Problemstellung. |
> | §4.6: „Die Unsicherheit der Flächenhöhe ist der **dominierende** Fehler" | Für die **lokale** Anforderung trifft das nicht zu: 1,5 % von 30 mm sind 0,45 mm von 1 mm zulässig. Dominierend sind die Bandmehrdeutigkeit (P1, 14 %) und der Bauteilzulauf (P3, 5 %). Die Flächenhöhe wird erst dominierend, wenn beide gelöst sind. |
> | §4.4: „Schrägstellung bis etwa 20° ist unkritisch" | Gemessen: über 3° wird die Kantenmessung unsicher, über 6° verliert sie das Band. §4.13 desselben Papiers korrigiert sich bereits selbst auf „etwa 3 Grad". |
> | §4.5, Schritt 4: „Nach der Entzerrung ist nur noch eine reine Verschiebung übrig — Phasenkorrelation genügt" | Trägt nicht. Nötig sind volle Perspektive je Bild und eine Bündelausgleichung über die Reihe. §4.13 stellt das bereits fest. |
> | §4.5, Schritt 5 / §4.6: „Einpassung auf die Gesamtlänge — damit verschwindet jede aufgelaufene Drift", Driftbeitrag **0** | **Das ist der gefährlichste Punkt.** Die Einpassung *verbirgt* die Drift, sie beseitigt sie nicht: Gemessen lag dieselbe Stelle am Balken zwischen zwei Codefassungen 35 mm auseinander, obwohl beide Streifen außen exakt die Solllänge hatten. Ein Fehler, der sich nicht mehr zeigt, ist nicht weg. |
> | §4.3 / §4.4: 7 Aufnahmen je Seite, 25–30 % Überlappung | Alle gelungenen Reihen liegen bei 56–72 % Überlappung. P4 zeigt, warum: Die Punktpaarausbeute bricht weit schneller ein als linear. |
> | §4.13: „Nähte: Flachfeld plus Zweibandmischung" | Verworfen — die Zweibandmischung war die Ursache der Geisterfragmente. Heute Nahtwahl statt Mischung. |
> | §4.13: Entwicklungsstand, Dateitabelle | Vom 15.10. und überholt. `pruefen.py` wurde vollständig neu geschrieben, `zusammensetzen.py` durch `zusammensetzen2.py` ersetzt. |
>
> Umgekehrt enthält §4.13 zwei Einsichten, die sich **bestätigt** haben und im
> heutigen Code stehen: „erst auf die Messfläche beschneiden, dann suchen" und
> „Suchkacheln nach Eindeutigkeit wählen, nicht nach Kontrast".

**3. `zusammensetzen2.py`** (2405 Zeilen) — der Zusammenbau.

Der Kern. Lesenswerte Stellen in dieser Reihenfolge:

| Funktion | was dort passiert |
|---|---|
| `bandgueten` | wie das Bauteil im Bild gefunden wird (das Kernkriterium) |
| `band_aus_bewegung` | zweiter, unabhängiger Weg über die Parallaxe |
| `band_waehlen` | die Entscheidung zwischen beiden — und warum sie bewusst nur meldet |
| `stationen_messen` | Kantenmessung je Bild, zwei Durchgänge |
| `Modell` / `bauen_residuen` | das Geometriemodell und die Nebenbedingungen |
| `levenberg` | die Ausgleichung (Levenberg-Marquardt, numerische Jacobi-Matrix) |
| `photometrie` | Kanalfaktoren je Bild plus gemeinsames Lichtfeld |
| `balkenenden` | Bauteilenden über die Faserrichtung |

**4. `pruefen.py`** (1495 Zeilen) — die Vorab-Prüfung.

Beurteilt eine Fotoreihe, **bevor** zusammengesetzt wird, und sagt grün / gelb /
rot vorher, getrennt nach Maßtreue und Farbtreue. Interessant vor allem als
Beleg dafür, welche Kennwerte sich als aussagekräftig erwiesen haben und welche
nicht.

**5. `kantenbild.py`** (75 Zeilen) — Sichtkontrolle.

Zeichnet die gefundenen Kantenpunkte in die Aufnahme. Hat mehrfach Fehler
sichtbar gemacht, die aus den Zahlen allein nicht zu erkennen waren.

**6. `bauteil_vorlage.json`** — das Eingabeformat je Bildreihe
(Bauteilmaße, gewünschte Auflösung, Saum).

---

## Wie der Code zu lesen ist

Die Kommentare sind **deutschsprachig und ungewöhnlich ausführlich**. Das ist
Absicht: An fast jeder Schwelle und jeder Designentscheidung steht die Messung
daneben, die sie begründet, meist mit Nennung der Fotoreihe, an der sie
gescheitert oder bestätigt wurde. Beispiel aus `band_waehlen`:

> *„An der Reihe 261022/Versuch 1 lieferte der freie Weg 1.60 statt 16.0 Px/mm,
> an Versuch 2 der Parallaxenweg 13.7 statt 15.7."*

**Wer eine Schwelle in Frage stellt, findet den Grund dafür am Fundort.** Umgekehrt
gilt: Wo kein Grund dabeisteht, ist die Schwelle geraten — das ist dann auch so
vermerkt.

Beide Programme laufen mit **ausschließlich Pillow und numpy**. Das ist eine
harte Vorgabe des Auftraggebers, keine Verlegenheitslösung. Frage F7 in der
Problemstellung bittet ausdrücklich um eine Einschätzung, welche Probleme durch
diese Vorgabe verursacht sind.

---

## Aufruf

```
python3 pruefen.py "<Bildordner>"                 # Prüfbericht, ~20 s für 20 Fotos
python3 pruefen.py "<Bildordner>" --bericht b.txt

python3 zusammensetzen2.py "<Bildordner>"         # Zusammenbau, einige Minuten
python3 zusammensetzen2.py "<Bildordner>" --nur-geometrie   # rechnet, zeichnet nicht
python3 zusammensetzen2.py "<Bildordner>" --weiter          # zeichnet aus dem Zwischenspeicher neu

python3 kantenbild.py "<Bildordner>" IMG_x.jpg ziel.jpg
```

Im Bildordner muss eine `bauteil.json` liegen (Vorlage beiliegend).

---

## Was bewusst **nicht** beiliegt

**Die Fotos** (1,6 GB über sechs Reihen). Für eine Code- und Methodenkritik
nicht nötig. Soll etwas nachgerechnet werden, genügen zwei Reihen:
`ISO 800` (250 MB, gelingt) und `261022_Test` (180 MB, enthält einen
gescheiterten und einen gelungenen Versuch). Auf Anfrage verfügbar.

**`zusammensetzen.py`** — der Vorgänger, dessen Architektur verworfen wurde
(eine Fehlerkette statt einer Ausgleichung, Zweibandmischung mit
Geisterfragmenten, seitenverkehrte Ausgabe). Der Befund dazu steht in der
Problemstellung; den Code dazu zu lesen lohnt nicht.

**`LIESMICH.md`** — ein Entwicklungstagebuch vom 15.10., drei Wochen älter als
der heutige Stand. Es beschreibt eine frühere `pruefen.py`, die es so nicht mehr
gibt, und **widerspricht der Problemstellung an einer zentralen Stelle**: Der
dort beschriebene Maßstab aus Lamellen- und Dielenfugen wurde entfernt, weil
Vollholz keine Fugen hat. Auf Anfrage verfügbar, wenn die Entwicklungsgeschichte
interessiert.

---

## Zum Umgang mit den Zahlen

Alle Messwerte in der Problemstellung stammen aus den sechs vorliegenden
Fotoreihen und sind mit den beiliegenden Programmen reproduzierbar. Wo etwas
geschätzt statt gemessen ist, steht es dabei — etwa die rote Schwelle für den
Bauteilanteil (18 %), die ungemessen zwischen 11 % (Reihe fällt auseinander) und
27 % (Reihe gelingt) liegt.

**Die Datenbasis ist dünn:** fünf Reihen mit bekanntem Ausgang, davon vier an
ein und demselben Testbalken. Zwei Vorhersagen der Prüfung waren vorher falsch,
beide Male aus nachvollziehbarem Grund (dokumentiert in Problemstellung, P7).
Einschätzungen dazu, wie ein solches Verfahren mit so wenigen Belegfällen
abzusichern wäre, sind ausdrücklich willkommen — das ist Frage F8.

---

*Hinweis zur Benennung: Diese Datei heißt `LIESMICH_FUER_REVIEW.md`. Die Datei
`LIESMICH.md` ist etwas anderes — das alte Entwicklungstagebuch, siehe oben.*
