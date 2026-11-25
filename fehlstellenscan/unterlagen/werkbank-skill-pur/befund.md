# Werkbank nur nach UI/UX Pro Max (Test, 25.11.2026)

Ohne Jans Optik und Einstellungen gestaltet. Ganz blind war ich nicht: Die erlaubte bedienung.js der alten Fassung enthielt auch deren Markup
und Klassenfarben. Bilder und CSS der alten Fassung habe ich erst fürs Vergleichsbild (fertig gerendert) gesehen.

## Anfragen und Treffer
- `image annotation review tool` (--design-system): Lernkarten-App, Claymorphism, Lila, Varela Round. **Verworfen**, passt nicht zum Produkt.
- Einmal enger: `imagery viewer inspection tool` (--design-system, --density 8, dazu --tokens css): „Earth Observation / Satellite
  Imagery Viewer“. **Übernommen**, weil Rasterbild plus Umrisse plus Prüfen die gleiche Aufgabe ist. Die engere Formulierung
  entstand, nachdem eine Textsuche in products.csv gezeigt hatte, dass es dieses Profil gibt. Sie ist also nicht blind gefunden.
  Holz, Labeln oder Qualitätsprüfung kennt der Skill nicht.
- style: `oled dark mode`, `data-dense dashboard`, `minimalism swiss style` (alle im Produkttreffer genannt), `flat design minimal`
  (nicht benutzt), `image annotation review` (0 Treffer).
- color: `satellite imagery` (bestätigt die Palette), `categorical colorblind palette` (GIS, hell: Palette verworfen, Regel
  „UI-Farben nicht für Daten“ genommen).
- typography: `developer technical mono` (bestätigt), `dashboard data readable` (Fira, nicht benutzt).
- icons: Phosphor, u. a. `trash delete`, `save disk`, `undo arrow`, `pencil edit`, `eye hide`, `upload add image`, `warning duplicate`,
  `arrow left right`, `icon button accessible label`. Ohne Treffer: `zoom magnifying`, `check confirm`, `keyboard help`, `caret chevron`;
  passende Phosphor-Zeichen ergänzt (das erlaubt der Skill).
- ux, benutzt: `dragging movements`, `target size touch`, `keyboard shortcut`, `undo destructive action`, `unsaved changes warning`,
  `focus not obscured`, `status message toast`, `color map legend status`, `empty state`, `modal dialog focus`, `reduced motion`,
  `disabled state contrast`, `hover state transition`, `range slider input`, `progress steps`.
  Ohne brauchbaren Treffer: `bottom sheet mobile`, `tabular numbers`, `loading save feedback`.
- ux, gesucht, aber ohne eigenen Beitrag: `map legend popup`, `map categories color alone` (Ausgabe ging bei einem abgebrochenen Befehl verloren).
- chart: `categorical colors colorblind`, `comparison categories`: keine Farbreihe für Klassen.
- --stack html-tailwind (nur Regeln): `focus ring`, `touch target size`, `icon size stroke`, `range input`,
  `responsive sidebar layout`, `dark mode colors`, `safe area dvh` (leer), `transition duration`.

## Woher die Optik kommt
| Entscheidung | Quelle |
|---|---|
| Dunkles neutrales Grau, Himmelblau für Hauptknopf, Bernstein für Auswahl | Farbtreffer, wörtlich |
| JetBrains Mono (Titel, Zahlen), IBM Plex Sans (Text), beide OFL | Typografie des Design-Systems, Regel number-tabular |
| Abstände 2 bis 32 px | --density 8 |
| Kopf 56, Zeile 36, Innenabstand 12, Schrift 12 bis 14, Kennzahlkacheln | Data-Dense Dashboard |
| Ecken 0, Linien statt Schatten | Minimalism & Swiss |
| Schwacher Schein am Hauptmaß | Dark Mode (OLED), „minimal glow“ |
| Bild in der Mitte, Bilderleiste unten | „Imagery-First + Timeline“ |
| Handy: Bild oben, Bereich darunter mit Reitern | „map-bottom-sheet“, frei umgesetzt (feststehend) |
| Maßstab im Bild, Beschriftung am Umriss | „every scale must be labeled“, direct-labeling |
| Strichmuster je Klasse | Map Symbology Not Color Alone |
| Punkt auch per Knopf verschieben, +/- zoomt, Pfeile schwenken | Dragging Movements, Map Keyboard |

## Verworfen oder nicht gedeckt
- Seitenmuster „Immersive“ (Tour, CTA) ist für Werbeseiten; Zeitregler und Vorher-Nachher braucht die Werkbank nicht.
- Klassenfarben: keine Farbreihe gefunden. Sechs Farbwerte aus den Daten des Skills, Auswahl von mir. Rückfall.
  Unter Farbfehlsichtigkeit nicht simuliert.
- Spaltenbreiten 288 und 320 (Skill: 240, zu schmal für Klasse, Maß und KI), Anordnung und Texte: von mir.
- Widerspruch im Skill: Stil verlangt Kontrast 7:1, seine Palette liefert bei Nebentext etwa 6:1. Es gilt 4,5:1.
- Keine helle Fassung, weil der Stil hell nicht empfiehlt.

## Geprüft
129 Prüfungen mit Playwright je für index.html und Einzeldatei (1440, 390, dazu 375, 768, quer 844), axe in mehreren Zuständen ohne Befund,
kein Überlauf, keine JS-Fehler. Nicht geprüft: echtes Handy, Safari, Firefox, Screenreader, große Systemschrift.

## Grenzen
Handy: Werkzeuge stehen ohne die geforderten 8 px Abstand, die Tastenübersicht ist ausgeblendet. Modell läuft nicht,
eigene Bilder messen in px. Gespeichert wird nur im Browser. Einzeldatei: `python3 bauen.py <ziel>`. Icons: Phosphor (MIT).
