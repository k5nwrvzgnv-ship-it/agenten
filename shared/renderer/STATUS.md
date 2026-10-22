# Status: Renderer (shared/renderer)

## Zweck
Gemeinsame Bibliothek für Jan und Lia: Claude schreibt eine JSON-Beschreibung, Python baut daraus ein Arbeitsblatt
(docx) oder Folien (pptx) im Stil von Lias Material oder eine Zusammenfassung (docx) in Jans Stil, mit Kontrolltext
und Vorschaubildern für Claude. Claude führt nie Code aus. Nutzer: Lias Material-Agent (Übergabe
`../../docs/uebergabe-lia-dokumente.md`) und Jans dokumente-Agent (Zusammenfassungen, Hauptordner-STATUS Punkt 3a). Grundlage: `../../docs/lia-architektur.md`, Abschnitt 2.1 (Rolle material).

## Stand (22.10.2026)
Kern fertig, alle Schritte committet, `./pruefen.sh` grün (Renderer: 110 Tests). Noch nutzt ihn kein Agent.
Art `zusammenfassung` fertig (Vorschau angesehen, Beispiel `beispiele/zusammenfassung-beispiel.json`); es fehlen
nur noch HNEE-Grün und Logo (Offene Punkte 1).
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
  `zusammenfassung` -> .docx (Jan bekommt das PDF aus der Vorschau, `ergebnis.pdf`).
- Profil: dict, z. B. aus TOML. Vorlage mit Lias Stil: `beispiele/profil-lia-stil.toml` (ohne Namen, Fach und
  Lehrkraft trägt ihr Agent ein), mit Jans Stil: `beispiele/profil-jan-zusammenfassung.toml` (`erstellt_von` trägt
  der dokumente-Agent ein). Felder und Standardwerte: `design.py`.
- Vorlage: .docx/.pptx des Agenten (`<agent>/data/vorlagen/`); .dotx/.potx vorher mit `vorlage_umwandeln()`.
- Vorschau: `<ziel ohne Endung>-vorschau/` mit PNG je Seite und PDF. Scheitert sie, steht der Grund in `hinweise`
  (und im Log `renderer`), die Datei gibt es trotzdem. Die PDF nutzt die Ersatzschriften des Servers.
- Die .venv des Agenten braucht python-docx, python-pptx, Pillow und pypdfium2 (Versionen: `requirements.txt`),
  LibreOffice kommt aus dem System (`/usr/bin/soffice`).

## Aufbau
- `__init__.py`: `bauen`, `Ergebnis`, `pruefen`, `vorlage_umwandeln`, `BeschreibungUngueltig`.
- `pruefung.py`: strenge Prüfung (reine Logik), `lesen()` liefert die Beschreibung mit allen Standardwerten. Grenzen
  stehen oben im Modul und in `FORMAT.md`, bei Änderung beide anpassen (`tests/test_format.py` prüft die Beispiele).
- `arbeitsblatt.py`, `folien.py`, `zusammenfassung.py`: bauen aus der gelesenen Beschreibung. Die Zusammenfassung
  erbt Seite, Schrift und XML-Hilfen vom Arbeitsblatt (`arbeitsblatt._Bau`), Änderungen dort wirken auf beide. `design.py`: Profil. `icons.py`: 55 Icons
  (Tabler Icons 3.49.0, MIT, Schriften in `icons/`). `vorlagen.py`. `kontrolle.py`: Kontrolltext aus der gebauten
  Datei in Lesereihenfolge. `vorschau.py`: LibreOffice -> PDF, pypdfium2 -> PNG.
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
- Farben der HNEE (Hochschule für nachhaltige Entwicklung Eberswalde), Logo über eine Word-Vorlage.

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
  `libreoffice-impress-nogui`, `fonts-crosextra-carlito`), etwa 5 s je Datei.

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

## Offene Punkte
1. HNEE-Stil fertigstellen: Jan nennt den Grünton (Farbcode) bzw. schickt das Logo in Grün. Dann Farben in
   `beispiele/profil-jan-zusammenfassung.toml` eintragen (Stellen mit „HNEE“). Das Logo liegt bisher nur weiß als SVG
   vor (für dunklen Grund); LibreOffice wandelt SVG in PNG um (`soffice --headless --convert-to png`), getestet.
   Die Word-Vorlage mit Logo in der Kopfzeile baut der dokumente-Chat (C) in `dokumente/data/vorlagen/`.
2. Lias Material-Agent baut auf dem Renderer auf (eigener Chat in `lia/<agent>`). Sein Skill nimmt `FORMAT.md`
   auf, sein Profil `beispiele/profil-lia-stil.toml` mit Fach und Lehrkraft.
3. Echte Vorlage von Lia oder Jan testen, sobald es eine gibt (Zentrale muss Dateien annehmen, Hauptordner-Chat).
4. Kleinigkeiten nach Bedarf: Aufzählungspunkte stehen in LibreOffice etwas hoch (in PowerPoint unauffällig),
   Icons im Folieninhalt etwas größer, Zeilennummern im Material (Lias Hilfen verweisen auf Zeilen).
5. Später für Jans dokumente-Agent: weitere Arten (Brief, Bericht, Tabelle/Excel), Bearbeiten bestehender
   Dateien (Anforderungen in `../../dokumente/STATUS.md`).

## Gelernte Regeln
- Erst die Vorschau ansehen, dann „fertig“ sagen: Tests prüfen das XML, nicht das Aussehen. (Jan, 21.10.)
