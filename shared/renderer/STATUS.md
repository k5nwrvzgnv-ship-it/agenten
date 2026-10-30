# Status: Renderer (shared/renderer)

## Zweck
Gemeinsame Bibliothek für Jan und Lia: Claude schreibt eine JSON-Beschreibung, Python baut daraus ein Arbeitsblatt
(docx) oder Folien (pptx) im Stil von Lias Material, eine Zusammenfassung (docx) in Jans Stil oder eine Arbeitsmappe
(xlsx, Tabellen zum Ausfüllen mit Rechnungen), mit Kontrolltext und Vorschaubildern für Claude. Claude führt nie Code aus. Nutzer: Lias Material-Agent (Übergabe
`../../docs/uebergabe-lia-dokumente.md`) und Jans dokumente-Agent (Zusammenfassungen, Hauptordner-STATUS Punkt 3a). Grundlage: `../../docs/lia-architektur.md`, Abschnitt 2.1 (Rolle material).

## Stand (30.10.2026)
Kern fertig, alle Schritte committet, `./pruefen.sh` grün (Renderer: 155 Tests). lia/unterricht nutzt Arbeitsblatt
und Folien.
Art `arbeitsmappe` (Excel) fertig (29.10.): Lias Notentabelle gebaut (`data/nachbau/notentabelle/`, Vorschau
angesehen, Calc rechnet wie Python). Offen: Jan öffnet sie in Excel, Vergleich mit der Handvorlage, lia/unterricht
schaltet die Art frei (Bedarf in `../../STATUS.md`).
Art `zusammenfassung` fertig, mit HNEE-Farben im Profil (Vorschau angesehen, Jan hat die Farben am 22.10. freigegeben,
Beispiel `beispiele/zusammenfassung-beispiel.json`). Es fehlt nur das Logo (Offene Punkte 1).
Lias Arbeitsblatt 5.2 und Präsentation 5 sind nachgebaut und nah am Original (Jan hat beide in Word und
PowerPoint angesehen). Vorlagen sind nur mit selbst gebauten Testvorlagen geprüft, eine echte gibt es noch nicht.

## Nutzung (für den Agenten)
```python
from renderer import bauen, BeschreibungUngueltig
ergebnis = bauen(beschreibung, ausgang / "blatt.docx", profil=profil, vorlage=None, vorschau=True)
# BeschreibungUngueltig: str(e) an Claude zurück (alle Fehler mit Pfad), Claude korrigiert und schickt neu.
# ValueError / design.ProfilUngueltig: Fehler des Agenten (Endung, Profil, Vorlage), an Jan melden.
ergebnis.pfad, ergebnis.kontrolltext, ergebnis.bilder, ergebnis.pdf, ergebnis.hinweise
```
- Format für Claude: `FORMAT.md` (gehört in den Skill des Agenten). Art `arbeitsblatt` -> .docx, `folien` -> .pptx,
  `zusammenfassung` -> .docx (Jan bekommt das PDF aus der Vorschau, `ergebnis.pdf`), `arbeitsmappe` -> .xlsx
  (ohne Vorlage; der Kontrolltext endet mit Proben, die Python nachgerechnet hat).
- Profil: dict, z. B. aus TOML. Vorlage mit Lias Stil: `beispiele/profil-lia-stil.toml` (ohne Namen, Fach und
  Lehrkraft trägt ihr Agent ein), mit Jans Stil: `beispiele/profil-jan-zusammenfassung.toml` (`erstellt_von` trägt
  der dokumente-Agent ein). Felder und Standardwerte: `design.py`.
- Vorlage: .docx/.pptx des Agenten (`<agent>/data/vorlagen/`); .dotx/.potx vorher mit `vorlage_umwandeln()`.
- Vorschau: `<ziel ohne Endung>-vorschau/` mit PNG je Seite und PDF. Scheitert sie, steht der Grund in `hinweise`
  (und im Log `renderer`), die Datei gibt es trotzdem. Die PDF nutzt die Ersatzschriften des Servers.
- Die .venv des Agenten braucht python-docx, python-pptx, xlsxwriter, Pillow und pypdfium2 (Versionen:
  `requirements.txt`), LibreOffice kommt aus dem System (`/usr/bin/soffice`, mit Calc für xlsx).

## Aufbau
- `__init__.py`: `bauen`, `Ergebnis`, `pruefen`, `vorlage_umwandeln`, `BeschreibungUngueltig`.
- `pruefung.py`: strenge Prüfung (reine Logik), `lesen()` liefert die Beschreibung mit allen Standardwerten. Grenzen
  stehen oben im Modul und in `FORMAT.md`, bei Änderung beide anpassen (`tests/test_format.py` prüft die Beispiele).
- `arbeitsblatt.py`, `folien.py`, `zusammenfassung.py`, `arbeitsmappe.py`: bauen aus der gelesenen Beschreibung.
  `rechnung.py`: Rechensprache der Arbeitsmappe (reine Logik: zerlegen, gegen Spalten prüfen, Kreise, nach Excel
  übersetzen, in Python nachrechnen). Die Zusammenfassung
  erbt Seite, Schrift und XML-Hilfen vom Arbeitsblatt (`arbeitsblatt._Bau`), Änderungen dort wirken auf beide. `design.py`: Profil. `icons.py`: 55 Icons
  (Tabler Icons 3.49.0, MIT, Schriften in `icons/`). `vorlagen.py`. `kontrolle.py`: Kontrolltext aus der gebauten
  Datei in Lesereihenfolge (xlsx mit zipfile/xml.etree). `vorschau.py`: LibreOffice -> PDF, pypdfium2 -> PNG.
  `tests/test_calc.py`: Calc rechnet dasselbe wie `rechnung.py` (übersprungen ohne LibreOffice).
- `data/` (nicht im Repo): `lia-vorbilder/` (Lias PDFs), `nachbau/` (Nachbauten mit Vergleichsbildern),
  `icons/uebersicht.png`, Testausgaben.
- .venv neu aufsetzen: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, dann
  `echo /home/agent/agenten/shared > .venv/lib/python3.12/site-packages/agentkit.pth`.

## Lias Stil (vermessen an den Vorbildern)
- **Arbeitsblatt:** A4, Ränder 2 cm, Calibri 11, Zeilenabstand 1,15. Kopf-Tabelle 3,75 / 8 / 4,25 cm (Fach und
  Lehrkraft | Thema gelb FFD873 und „Arbeitsblatt n“ | Datum, Name). Merksatz im Doppelrahmen (außen dick) rosa
  F2CEED, Material grün D9F2D0 im Blocksatz, Anweisung fett, Aufgaben „1.“ fett mit hängendem Einzug, Ankreuz-Kästchen
  Wingdings F070, Hilfen 9 pt, Schreiblinien 0,6 cm.
- **Folien:** 16:9 (12192000 x 6858000 EMU), Aptos / Aptos Display, Akzent C00000, Kästen F5F5F5, Satzanfänge
  196B24, Markierungen blau 156082, orange A8480C, grün 196B24. Titel 1,2 bis 4,6 cm (44 pt einzeilig, 38/32 pt
  zweizeilig), Strich bei 4,72 cm von 2,37 bis 31,5 cm, Inhalt 5,5 bis 17,6 cm, Fußzeile bei 18 cm,
  Titelfolie mit 10,16 cm breitem Balken.
- Bewusst anders als bei Lia: Hilfen nach den Aufgaben statt fest am Seitenende, Ankreuz-Optionen eingerückt,
  erste Spalte der Ausfülltabelle gleich breit, Handschlag-Icon in Herzform, Zeigefinger und Paket nur als Umriss,
  Icons im Folieninhalt etwas kleiner.

## Jans Stil (Zusammenfassung, mit Jan abgestimmt 22.10.)
- A4, Ränder 2 cm, Calibri 11, Zeilenabstand 1,15, 6 pt nach Absätzen. Kopf: Kurs (klein, farbig), Titel 20 pt,
  Untertitel, „Vorlesung vom · Stand · erstellt von“, Legende der Kennzeichen (nur wenn benutzt), Linie.
- Überschriften nummeriert (1, 1.1), Farbe `ueberschrift`. Hinweise und Rechenbeispiel: Fläche mit Balken links.
  Quellen und Kennzeichen klein und grau in eckigen Klammern am Absatzende. Tabellenkopf hinterlegt.
- Am Ende Selbsttest, offene Fragen, Lösungen auf eigener Seite. Fußzeile: Kurs · Titel, rechts „Seite x von y“
  (nur ohne Fußzeile der Vorlage).
- Farben der HNEE (Hochschule für nachhaltige Entwicklung Eberswalde): Burnham 00261E für Überschriften, Kurs,
  Linie und Balken; Sycamore 949547 aufgehellt für Prüfungsrelevant (30 %, DFDFC8) und Tabellenkopf (20 %, EAEADA);
  Organisatorisches, Rechenbeispiel, Quellen grau. Quelle der Farbcodes: Markenfarben-Übersicht von Jan, nicht das
  Design-Handbuch der HNEE (bei Gelegenheit abgleichen). Logo über eine Word-Vorlage.

## Technik, die man kennen muss
- Word: Neue XML-Elemente an der Stelle einfügen, die das Schema verlangt (sonst „unlesbarer Inhalt“). Theme-
  Schriften entfernen (sie hätten Vorrang). Spaltenbreiten in Raster und Zellen setzen (LibreOffice liest das Raster,
  Word die Zellen). Schreiblinien: unterer Rahmen plus `between`. Nach jeder Tabelle ein leerer Absatz (zwei Tabellen
  hintereinander verschmelzen). Je Zeile ein Absatz statt Zeilenumbruch (Blocksatz). Nummerierte Listen neu starten.
- Absatzrahmen: Word und LibreOffice zeichnen den linken Rahmen am Einzug. Eingerückte Zeilen in Kästen daher
  hängend (Einzug links, erste Zeile negativ, Tabulator), sonst springt der Balken. Rechter Tabulator genau am
  rechten Rand wird von LibreOffice übergangen (0,01 cm davor setzen), Tabstopps des Footer-Stils vorher löschen.
  `page_break_before = False` schreibt ein Element mit val="0", also nur bei True setzen.
- PowerPoint: Formen ohne `p:style` (der Effektstil zeichnet sonst Schatten). Textgröße je Folie aus geschätzter
  Zeilenzahl (`folien.zeilen()`), Maßstab 1,35 bis 0,6, sonst Fehler an Claude. Titel im Titel-Platzhalter
  (Gliederung). Layouts nach Platzhalterart suchen (`vorlagen.layout`), nicht nach Namen.
- Icons: Pillow mit `Layout.BASIC` (raqm scheitert an Zeichen aus dem Unicode-Privatbereich).
- Kontrolltext: lxml-Elemente festhalten statt `id()` merken (Adressen werden wiederverwendet).
- Vorschau-Schriften: Carlito ersetzt Calibri maßgleich. Aptos ersetzt `~/.config/fontconfig/fonts.conf` durch
  Liberation Sans (eher breiter, Überläufe fallen also früher auf). LibreOffice aus apt (`libreoffice-writer-nogui`,
  `libreoffice-impress-nogui`, `libreoffice-calc-nogui` seit 29.10., `fonts-crosextra-carlito`), etwa 5 s je Datei.

## Entscheidungen (Jan, 21./22.10.)
- Lias Stil ist der Maßstab. Das Profil gibt der Agent mit, der Renderer enthält keine Daten einer Person.
- Formate docx und pptx. PDF entsteht nur als Teil der Vorschau, als Ausgabe für Lia ist es nicht vereinbart.
- Kontrolle durch Claude: Vorschaubilder und Kontrolltext.
- Vorlagen schlank: Kopf-/Fußzeilen, Logo, Ränder bzw. Master und Hintergrund aus der Vorlage, Inhalte im Stil des
  Profils. Fehlen der Word-Vorlage Listen- oder Überschriftenstile, setzt der Renderer Zeichen von Hand bzw. legt
  die Stile an. PowerPoint-Vorlagen nur in 16:9.
- PDFs lesen (Lia schickt PDFs) gehört in agentkit, Bedarf steht in `../../STATUS.md`.
- Ab der ersten Nutzung durch einen Agenten: Format nur erweitern, nicht umbauen, jede Erweiterung mit Tests.
- Zusammenfassung (22.10.): Quellen als Klammer im Text statt Fußnoten, Selbsttest und offene Fragen am Ende,
  Lösungen auf eigener Seite, Überschriften nummeriert, Calibri 11, HNEE-Farben, Logo über Vorlage.
  Kennzeichen: `unsicher` (Transkript nicht eindeutig), `muendlich` (nur gesagt, nicht auf den Folien).

## Vorgaben
- Eingabe streng prüfen, Fehlermeldungen so, dass Claude sie in derselben Sitzung beheben kann.
- Keine Inhalte, Zugangsdaten oder Netzzugriffe im Renderer.
- Erst die Vorschau ansehen, dann „fertig“ sagen.

## Arbeitsmappe (Excel, gebaut 29.10. nach Jans Plan-Freigabe)
- Format: `FORMAT.md`, Abschnitt Arbeitsmappe. Leere Vorlagen: Blätter mit Titel, Hinweisen, Spalten (`nummer`,
  `text`, `zahl`, `rechnung`) und Zeilenzahl. Keine vorbelegten Werte und keine Auswahllisten (später nur erweitern;
  keine Schülerdaten über Claude).
- Formeln: Claude schreibt die Rechensprache (`mittelwert(n1:n5)`, `wenn_leer(2/3 * schnitt + 1/3 * lek, schnitt)`),
  nie Excel. `rechnung.py` erzeugt die Excel-Formel aus dem Baum. Leer-Regel: leer, solange ein benutzter Wert fehlt
  (summe/mittelwert/min/max: erst wenn alle fehlen), Excel `IF(COUNT(..)=0,"",..)`. COUNT statt ISBLANK, weil eine
  leere Rechnung "" enthält; COUNT übergeht auch Fehler (#DIV/0!), `ausrechnen()` genauso.
- Bau (`arbeitsmappe.py`, xlsxwriter): `strings_to_formulas`/`_urls` aus (Text mit `=` bleibt Text), Datenüberprüfung
  mit deutscher Meldung, Zahlformate nur `0`/`0.00`, Rechenfelder `farben.rechenfeld`, Kopf `farben.tabellenkopf`,
  kein Blattschutz, Kopf fixiert, A4 quer auf eine Seite, wenn dafür höchstens auf 70 % verkleinert wird
  (`MIN_MASSSTAB`, Schätzung `massstab_eine_seite`), sonst auf Seitenbreite; Titel bis Kopf auf jeder Seite,
  „Seite x von y“.
  Gespeicherte Werte = Werte einer leeren Zeile (sonst zeigen Programme ohne Neuberechnung 0).
- Calc rechnet xlsx beim Laden nur neu mit `OOXMLRecalcMode` = 0 im Profil; `vorschau.umwandeln` schreibt das in jedes
  frische Profil. CSV-Ausgabe (`umwandeln(.., "csv")`) zeigt volle Genauigkeit, nur das erste Blatt.
- Entscheidungen Jan 29.10.: Calc installiert, kein Blattschutz, Nachkommastellen nur Anzeige, ohne LEK zählt der
  Durchschnitt (per `wenn_leer`).
- Offen: Jan öffnet `data/nachbau/notentabelle/Notentabelle.xlsx` in Excel (Eingabeprüfung, Rechnung, Druck).
  Handvorlage des lia-Chats zum Vergleich fehlt auf dem Server. 35 Zeilen passen auf eine Druckseite (Maßstab
  etwa 80 %, Vorschau 30.10. neu gebaut und angesehen).

## Offene Punkte
1. Logo der HNEE: liegt bisher nur weiß als SVG vor (für dunklen Grund). Besser eine offizielle grüne Logo-Datei
   als das weiße SVG umzufärben (das Grün im Logo wirkt heller als Burnham). LibreOffice wandelt SVG in PNG um
   (`soffice --headless --convert-to png`), getestet.
   Die Word-Vorlage mit Logo in der Kopfzeile baut der dokumente-Chat (C) in `dokumente/data/vorlagen/`.
2. Lias Material-Agent baut auf dem Renderer auf (eigener Chat in `lia/<agent>`). Sein Skill nimmt `FORMAT.md`
   auf, sein Profil `beispiele/profil-lia-stil.toml` mit Fach und Lehrkraft.
3. Echte Vorlage von Lia oder Jan testen, sobald es eine gibt (Zentrale muss Dateien annehmen, Hauptordner-Chat).
4. Kleinigkeiten nach Bedarf: Aufzählungspunkte stehen in LibreOffice etwas hoch (in PowerPoint unauffällig),
   Icons im Folieninhalt etwas größer, Zeilennummern im Material (Lias Hilfen verweisen auf Zeilen).
5. Später für Jans dokumente-Agent: weitere Arten (Brief, Bericht), Bearbeiten bestehender
   Dateien (Anforderungen in `../../dokumente/STATUS.md`).

## Gelernte Regeln
- Erst die Vorschau ansehen, dann „fertig“ sagen: Tests prüfen das XML, nicht das Aussehen. (Jan, 21.10.)
