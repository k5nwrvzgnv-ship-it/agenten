# Recherche: Inneres aus der Oberfläche, digitaler Zwilling BSH, Flicken statt Kappen

Stand 12.11.2026, Websuche durch Claude. Überwiegend aus Kurzfassungen und Herstellerseiten, Volltexte nur
wo vermerkt. Normtext EN 14080 nicht eingesehen (kostenpflichtig).

## 1. Äste im Inneren aus der Oberfläche

Schnittholz (Bretter, Lamellen):
- TU Wien (Kandler, Lukacevic, Füssl): Algorithmus rekonstruiert die 3D-Astgeometrie im Brett aus
  Faserwinkeln an der Oberfläche (Laserscan, Tracheideneffekt) und der geschätzten Marklage
  (Construction and Building Materials 2016). Weiterentwickelt zu einem 3D-Ast- und Faserverlaufsmodell
  zur Vorhersage der Brettfestigkeit (Lukacevic, Kandler, Hu, Olsson, Füssl, Materials & Design 166, 2019,
  doi 10.1016/j.matdes.2019.107617). Dissertation Lukacevic 2014 (TU Wien, repositum).
- Das ist genau der Einstieg „Äste auf allen vier Seiten, Kegel vom Mark“, aber mit Faserwinkeln statt nur
  Farbbild. Kamera plus YOLO liefert keine Faserwinkel; die braucht Laser mit Tracheideneffekt.

Rundholz, Deep Learning:
- Arbeiten zur Vorhersage innerer Äste aus der Rindenform (arXiv 2010.03173, Übersicht ResearchGate
  339199815, Folgearbeit arXiv 2308.11291 „Longitudinal Feature Propagation“). Grundlage: Äste hinterlassen
  Spuren auf der Rinde. Engpass laut Autoren: zu wenige echte Paare aus CT und Oberfläche, daher künstliche
  Daten (1.800 simulierte Stämme). Zum Erzeugen solcher Daten: arXiv 2503.14277.
- Astsegmentierung in CT-Daten (z. B. KnotSegNet3D, Wood Science and Technology 2026) liefert Labels für
  solche Paare.

Bewertung: Für Äste ist das Feld etabliert, für Schnittholz mit physikalischem Modell, für Rundholz mit
Deep Learning. Zu Fäulnis, Hohlräumen oder Metall aus der Oberfläche nichts gefunden (erwartbar).

## 2. Digitaler Zwilling BSH aus Lamellenscans

- Kandler, Lukacevic, Füssl u. a. (Eur. J. Wood Prod. 2018, doi 10.1007/s00107-018-1328-6, „Experimental study
  on glued laminated timber beams with well-known knot morphology“): Lamellen gescannt, Äste virtuell
  rekonstruiert, Lage jeder Lamelle im Träger festgehalten, 50 BSH-Träger in 5 Aufbauten im
  4-Punkt-Biegeversuch geprüft. Das ist im Kern der Zwilling, als Forschungsaufbau.
- TU Delft: FE-Verfahren zur virtuellen Sortierung; Bretter aus Astdaten der Oberfläche rekonstruiert, daraus
  ein BSH-Modell aus den einzelnen Lamellen.
- SEWC 2023: Ablauf, der jede Lamelle ihrer Lage im Stamm zuordnet und daraus ein FE-Modell baut.
- Offene Lücke laut Quellen: Festigkeit aus Astgeometrie realistisch vorhersagen, vor allem bei Astgruppen
  in schlechteren Brettern. Eine fertige Industrielösung „Zwilling je Träger“ nicht gefunden.

## 3. Ausfräsen und Flicken

Industrie (optisch, Platten):
- Wintersteiger TRC Woodpatch: bohrt Fehlstellen rund aus, schneidet den Flicken aus einer Leiste, presst ihn
  ein, wendet die Platte, flickt die Rückseite. Erkennung mit eigenem Scanner (Faulty Spot Eye). Für
  Mehrschichtplatten, Schalungsplatten, „glulam panels“; Standardmaße Länge 1,5-3 m, Breite etwa 500 mm,
  Dicke 10-20 mm. Pfeifer nutzt vier Module, Takt rund 3,5 s je Flicken.
- TU Wien, EU-Projekt HOL-I-Wood PR (FP7, 2015, Partner u. a. MiCROTEC, Luleå): Roboter flickt Schalungsplatten,
  berechnet minimale Flickenzahl und Reihenfolge, Prototyp lief im Sägewerk in Slowenien.
- Ergebnis: Flickautomaten gibt es, aber für dünne Decklagen (10-20 mm), runde Flicken, Optik bzw. Ausbeute.
  Für 40-mm-Lamellen vor dem Verkleben nichts Industrielles gefunden.

Tragend (Forschung):
- Derkowski, Kuliński, Trociński, Mirski (Poznań), Krzosek (SGGW), Materials 15(22):8112, 2022, Volltext
  gelesen: Kiefer, Lamellen 40 x 138 mm. Nur Randäste ausgefräst (halbrund, Radius 30/40 mm, CNC),
  mit astfreiem Holz gefüllt (PUR bzw. MUF). BSH-Träger im 4-Punkt-Biegeversuch: Mittel über 40 N/mm²,
  Minimum über 34; PUR mehr als 22 % besser als MUF; am besten, wenn die geflickten Lamellen unter einer
  fehlerfreien Zuglamelle liegen. Fehlerfreie Festigkeit nicht erreicht, Kerbwirkung und Faserlage an der
  Fräskante bleiben das Problem. Kleine Probenzahl (6 je Variante), Ergebnis als Hinweis, keine Kennwerte.
  Laut Autoren bis 20 % Holz gespart. Vergleich mit herkömmlich gekappten und keilgezinkten Trägern ähnlich.
- Korrektur meiner Einschätzung: „Schiffchen stellt die Festigkeit nicht her“ stimmt für fehlerfreies Niveau,
  aber Träger mit geflickten inneren Lamellen erreichten in dieser Studie tragfähige Werte. Bauaufsichtlich
  zugelassen ist das damit nicht.

Regelwerk (Oberfläche):
- Oberflächenqualitäten (Industrie-, Sicht-, Auslesequalität) stehen im BS-Holz-Merkblatt der
  Studiengemeinschaft Holzleimbau, nicht als Festigkeitsregel. Laut Verbandsunterlagen (Merkblatt 2012,
  Herstellerverzeichnis 2018) sind Astlochstopfen und Schiffchen in Sichtqualität zulässig, in
  Industriequalität nicht gefordert. Ein Hersteller (fortelignum) schreibt „nicht zulässig“ in Sichtqualität.
  Widerspruch nicht aufgelöst; aktuelle Fassung des Merkblatts und EN 14080 selbst prüfen.
- Ob EN 14080 Ausfräsen mit Einsatz in tragenden Lamellen regelt oder ausschließt: nicht gefunden.

## Folgerungen für die Projekte (Vorschlag)
- Zwilling und Flicken sind Forschungsstand, nicht Marktstand: Lücke zwischen Studie (Poznań, TU Wien) und
  Industrie (Wintersteiger nur Decklagen). Das passt eher zu Ziel 1 (Forschung) als zu Ziel 3 (Werken verkaufen).
- Für das eigene Modell: Masken und Lage je Seite sind Voraussetzung, Faserwinkel bräuchten anderen Sensor.
- Fragen an die Werke: Wird heute in Sichtqualität geflickt (von Hand, automatisch)? Was kostet eine
  Kappung mit Keilzinkung an Ausbeute? Wäre Flicken in inneren Lamellen interessant, wenn es zugelassen wäre?
- Fragen an Prof. Böhme: Kontakt TU Wien (Füssl) oder Poznań (Derkowski)? Zulassungsweg (abZ/ETA) für
  geflickte Lamellen realistisch?

## Quellen
- https://link.springer.com/article/10.1007/s00107-018-1348-2
- https://www.doaj.org/article/c2dc5ec189c74255a6e419ae9f922d47 (Materials & Design 2019)
- https://repositum.tuwien.at/handle/20.500.12708/256 (BSH-Träger mit bekannter Astmorphologie)
- https://link.springer.com/article/10.1007/s00107-018-1328-6
- https://arxiv.org/pdf/2010.03173
- https://arxiv.org/pdf/2308.11291
- https://arxiv.org/html/2503.14277
- https://link.springer.com/article/10.1007/s00226-026-01771-w
- https://repository.tudelft.nl/record/uuid:10ff46cf-e768-4e71-80c7-82413ed58823
- https://pmc.ncbi.nlm.nih.gov/articles/PMC9695602/ (Derkowski et al. 2022)
- https://www.tuwien.at/en/tu-wien/news/news-articles/news/wood-patching-robot-1
- https://www.wintersteiger.com/en/Woodtech/Flooring-furniture-and-boards/Product-range/Timber-Repair-and-Cosmetics/554-TRC-Woodpatch
- https://www.brettschichtholz.de/publish/binarydata/pdfs/2018/stghb_bs-holz-herstellerverzeichnis_2018-03_ihb_print_180430.pdf
- https://www.it.brettschichtholz.de/publish/binarydata/aktuelles/bs-holz-merkblatt-2012.pdf
- https://fortelignum.de/brettschichtholz-bsh/
