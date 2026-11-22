# Entwurf: Aufnahme-Aufbau für Altholzbalken (Termin bei Felix, Fr 27.11.2026)

Stand 22.11.2026, Entwurf von Claude für Jan, Henri und Felix, noch nicht entschieden. Skizze:
unterlagen/apparatur-skizze.svg. Gehört zu docs/plan-erster-test-altholz.md. Maße gerechnet, nicht gemessen,
Preise geschätzt.

## Anforderungen (Jan 22.11.2026)
- Licht und Abstand schwanken nicht, in keinem Bild, bei keinem Balken.
- Wenig Aufwand: möglichst etwas Fertiges, kaum Bau, wenig Geld.
- Smart: Maße und Angaben zum Balken einmal erfassen und automatisch mit den Fotos verknüpfen.
- Taugt für beides: YOLO-Trainingsbilder (feiner als Kodytek, 16,7 Px/mm quer) und Felix' Streifenbild (beide
  Kanten mit Kontrast im Bild, 25-30 % Überlappung, bauteil.json je Seite).

## Idee: LED-Fotobox als Reiter auf dem Balken
Eine faltbare Fotobox für Produktfotos (Würfel 60 x 60 x 60 cm, LED-Leisten innen, Loch oben fürs Handy) gibt es
fertig. In zwei gegenüberliegende Seitenwände schneiden wir von unten je einen Schlitz, 25 cm hoch, etwa 45 cm
breit. Dann setzt man die Box quer über den Balken: Die Schlitzoberkanten liegen auf der Balkenfläche, die Wände
hängen seitlich herunter, das Handy liegt oben auf dem Loch.

Was das löst:
- Licht: Die Box schließt Hallenlicht und Sonne aus, innen leuchten nur die eigenen LEDs, gestreut durch die weißen
  Wände. Jedes Bild hat dasselbe Licht, drinnen wie draußen, am ersten wie am letzten Balken.
- Abstand: Die Box liegt auf der Fläche, das Handy auf der Box. Kamerahöhe über der Fläche immer 60 - 25 = 35 cm,
  Blick senkrecht. Der Maßstab ist damit fest, einmal kalibriert gilt er für alle Balken.
- Hintergrund: Neben beiden Kanten sieht die Kamera in die Box hinein statt auf Pflaster. Die unteren 25 cm der
  beiden Seitenwände ohne Schlitz innen mit dem mitgelieferten schwarzen Hintergrundtuch auskleiden, dann liegt
  jede Kante vor Schwarz.
- Kein Fotografenschatten, kein Hilfsmittel auf der Kante, kein Stativ.

Bildfeld bei 35 cm (Hauptkamera 1x, 24 mm KB): etwa 50 x 38 cm, mit 48 MP (8064 x 6048) rund 16 Px/mm, also wie
Kodytek quer und weit feiner längs. Flächen bis etwa 34 cm Breite passen mit Rand ins Bild. Der Würfel ist innen
60 cm lang, das Bildfeld 50 cm, die Wände sind also nicht im Bild.

### Was zu kaufen und zu tun ist
| Teil | geschätzt |
|---|---|
| Faltbare LED-Fotobox 60 x 60 x 60 cm mit Loch oben, möglichst CRI 95 (z. B. Yorbay, OMBAR, Heorryn) | 40-80 € |
| Powerbank für die LEDs (meist USB), falls bei Felix keine Steckdose ist | vorhanden? |
| Kamera-App mit Sperre für Belichtung, Fokus und Weißabgleich bei 48 MP (siehe unten) | 0-5 € |
| Vier kurze Kantholz-Klötze, schmaler als der Balken (siehe Böcke) | Reststücke |

Umbau etwa 30 Minuten: Schlitze mit Cutter, Kanten mit Gewebeband einfassen, schwarzes Tuch innen ankleben, Handy
auf dem Loch mit Klettband oder Gummiband fixieren. Vor dem Kauf auf der Produktseite prüfen: Kameraloch oben,
Wände aus festen Platten (lassen sich schneiden), Stromversorgung, CRI-Angabe.

Böcke: Die Wände hängen 25 cm unter der Fläche. Damit sie über die Böcke wegkommen, liegt der Balken auf Klötzen,
die schmaler sind als der Balken, und Balkenhöhe plus Klotz ist mehr als 25 cm. Bei flachen Balken höhere Klötze.

Ausweichlösung ohne Kauf der Box: gleiches Prinzip mit einem Umzugskarton (Schlitze unten, innen weißes Papier,
unten schwarzes Papier, ein USB-LED-Streifen oben rundum, Loch im Deckel). Billiger, aber Höhe und Bildfeld müssen
zum Karton passen, also vorher nachrechnen.

## Apps und Metadaten
### Kamera
Ziel: in allen Bildern dieselbe Belichtung, derselbe Weißabgleich, derselbe Fokus, 48 MP, Hauptkamera. Weil das
Licht in der Box konstant ist, stellt man die Werte einmal ein und lässt sie den ganzen Tag stehen.
- Kandidaten laut App Store (nicht selbst getestet): Manual Camera 4 (Sperren für Belichtung, Fokus, Weißabgleich,
  48 MP ab iPhone 14 Pro), Modus ProCam (48 MP, Fokus und Weißabgleich manuell), Manual Cam (kostenlos, ISO,
  Verschluss, Weißabgleich, Fokus einzeln sperrbar, 48 MP unklar). Felix nutzt schon ProCamera, das kann das auch;
  der Prüfstand hat dort aber fehlerhafte EXIF-Felder gefunden (holzbalkenscan/verfahren/pruefen.py).
- Feste Werte: ISO niedrig (z. B. 50-100), Verschluss 1/60 s oder kürzer, Weißabgleich fest in Kelvin, Fokus fest
  auf die Fläche, HDR und Nachtmodus aus, Linse fest (kein automatischer Wechsel zur Makrokamera).
- Auslösen per Lautstärketaste am Kabelkopfhörer oder per Apple Watch, damit die Box beim Antippen nicht wackelt.

### Balkendaten einmal erfassen statt Zollstock im Bild
Zur Frage Zollstock: Für YOLO braucht es keinen. Felix' Verfahren braucht die Flächenhöhe (an drei Stellen
gemessen) und die Gesamtlänge als Zahlen in bauteil.json, nicht als Bild. Der Zollstock im Bild war bei ihm nur
eine Gegenprobe. Mit der Box ist der Maßstab ohnehin fest: Einmal am Morgen ein Kalibrierbild (gedrucktes
Schachbrett oder Maßband flach auf einem Brett unter der Box), danach kein Maßstab mehr im Bild.

Also je Balken einmal messen und eintippen:
- iPhone-Kurzbefehl „Balken erfassen“ (App Kurzbefehle, ohne Zusatz-App): fragt Balkennummer, Seite, Länge,
  Flächenhöhe an drei Stellen, Holzart und Notiz ab und hängt eine Zeile mit Uhrzeit an eine Textdatei in iCloud
  Drive an. Geht offline. Den Kurzbefehl kann ich als Schritt-für-Schritt-Anleitung schreiben.
- Messen mit Zollstock oder Laser-Entfernungsmesser. LiDAR-Apps (Messen, Polycam) sind für die Länge ok, für die
  Flächenhöhe aber nur zentimetergenau, das reicht als Maßnormal nicht.
- Dazu als erstes Bild jeder Seite eine Klappe wie beim Film: Karte mit Balkennummer und Seite in groß. Sicherung,
  falls Uhrzeit oder Kurzbefehl einmal nicht stimmen.

### Verknüpfung auf dem Rechner (Vorschlag, noch nicht gebaut)
Ein kleines Skript in fehlstellenscan/ (etwa `aufnahme.py ordnen`) liest die Textdatei des Kurzbefehls und die
Aufnahmezeit jedes Fotos aus den EXIF-Daten (Pillow, schon vorhanden, kein neues Paket). Es
- ordnet jedes Foto der Balkenseite zu, die zuletzt vor ihm erfasst wurde,
- legt je Balken und Seite einen Ordner an, Fotos in Aufnahmereihenfolge, Klappenbild getrennt,
- schreibt dort Felix' bauteil.json (Flächenhöhe, Länge, grenzen = kanten) und eine Liste mit Kalibrierung
  (Px/mm), App-Einstellungen und Notizen,
- meldet Lücken: Seite ohne Fotos, Fotos ohne Seite, auffällige Zeitsprünge.
Damit gehen die Reihen direkt in den Prüfstand (Streifenbild) und in balken.py (Kacheln fürs Seg-Modell). Bauen
nur mit Jans Okay, testbar ohne Netz mit kleinen Beispieldaten. Fotos kommen per AirDrop oder Kabel auf Jans Mac.

## Ablauf am Freitag
Vorher (bis Donnerstag): Box bestellen und umbauen, Probe an einem Brett: Bildfeld, Schärfe, Helligkeit, App-Werte
festlegen, Kalibrierbild. Probefotos an Jan, dann prüfen wir auf dem Server Streifenbild und Kacheln.

Am Balken:
1. Balken auf Böcke mit Klötzen. Messen, Kurzbefehl ausfüllen (Seite A).
2. Klappenbild, dann Box ans Balkenende. Erstes und letztes Bild ragen über das Ende: Dort liegt nur ein Schlitz
   auf, die Box von Hand waagerecht halten.
3. Je Bild: Box anheben, etwa 30 cm weitersetzen (Markierung an der Box, Kreidestrich am vorigen Platz),
   auslösen. Rund 40 % Überlappung, etwa 17 Bilder für einen 5-m-Balken.
4. Drehen (zu zweit), Kurzbefehl für die nächste Seite, weiter.
Zeit grob: 10-15 Minuten je Balken mit Drehen. Vielfalt vor Menge: viele verschiedene Balken, notfalls nur zwei
Seiten je Balken.

## Grenzen
- Gleichmäßiges Licht zeigt Risse und Relief schwächer als Streiflicht. Für den ersten Test egal (Kodytek ist auch
  gleichmäßig beleuchtet). Später: eine LED-Leiste der Box abschalten oder eine tief seitlich anbringen.
- Flächen breiter als etwa 34 cm passen nicht in ein Bild. Stark ausgebrochene Stellen unter einem Schlitz:
  Box kippelt, dann etwas versetzen.
- Sehr helle Balken vor weißer Boxwand: deshalb das schwarze Tuch unten.
- Ob die gewählte App wirklich alle Werte bei 48 MP festhält, zeigt erst die Probe.
- Den Aufsetzrahmen aus Latten mit eigenen Leuchten (frühere Fassung dieses Entwurfs, in Git) braucht es nicht
  mehr: Die Box liefert dasselbe fertig.

## Offen (bitte klären)
- Querschnitte und Längen der Balken bei Felix (passt 34 cm Breite, reichen 25 cm plus Klotz?).
- Welches Handy? 48 MP braucht ein iPhone 14 Pro, 15 oder neuer.
- Strom bei Felix, Böcke, Erlaubnis des Arbeitgebers, wer dreht mit.
- Soll ich den Kurzbefehl beschreiben und `aufnahme.py ordnen` bis Donnerstag bauen?
