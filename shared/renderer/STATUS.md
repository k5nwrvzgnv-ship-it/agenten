# Status: Renderer (shared/renderer)

## Zweck
Gemeinsame Bibliothek für Jan und Lia: Eine JSON-Beschreibung geht rein (von Claude geschrieben), eine
Datei kommt raus (docx, pptx, später PDF). Claude führt nie Code aus, Python baut. Nutzer sind Lias
Material-Agent (zuerst) und Jans dokumente-Agent (später). Grundlage: docs/lia-architektur.md,
Abschnitt 2.1 (Rolle material) und 7 (Schritt 1).

## Stand (21.10.2026)
- Entscheidungen geklärt (siehe unten), Plan von Jan freigegeben (6 Schritte, siehe Offene Punkte).
- Schritt 1 fertig: `.venv` (Versionen wie in `dokumente/`, Pillow bewusst auf 12.3.0), `agentkit.pth`,
  `requirements.txt`, leeres Paket, `tests/test_umgebung.py`, Eintrag in `pruefen.sh`.
- Schritt 2 fertig: `pruefung.py` (`pruefen`, `lesen`, `BeschreibungUngueltig`), `FORMAT.md` (Format für
  Claude, die Agenten nehmen es in ihren Skill auf). `lesen()` gibt die Beschreibung mit Standardwerten zurück,
  die Bau-Module verlassen sich darauf. Grenzen stehen oben in `pruefung.py` und in `FORMAT.md`: bei Änderung
  beide anpassen. `tests/test_format.py` prüft, dass die JSON-Beispiele in FORMAT.md gültig bleiben.
  Doppelte Felder, NaN und Steuerzeichen (die in docx/pptx nicht erlaubt sind) sind Fehler.
- Schritt 3 fertig: `arbeitsblatt.py` (`bauen(beschreibung, ziel)`, Beschreibung aus `pruefung.lesen`).
  A4, Ränder 2 cm, Stile der python-docx-Standardvorlage, Sprache de-DE, kein Autor. Was python-docx nicht kann,
  steht als kleines XML (`_xml_*`): Rahmen, Schreiblinien (unterer Rahmen plus `between`, sonst zeichnet Word nur
  eine Linie unter der Gruppe), Neustart nummerierter Listen, Wiederholung der Tabellenkopfzeile. Neue
  XML-Elemente werden an der Stelle eingefügt, die das Schema verlangt (sonst meldet Word „unlesbarer Inhalt“).
  Nach jeder Tabelle steht ein leerer Absatz (zwei Tabellen hintereinander verschmelzen in Word).
  Aufgaben heißen „Aufgabe 1: ...“ (fett) und bleiben mit ihrem Antwortplatz zusammen.
- Schritt A (Vorschau) fertig: `vorschau.py` (`vorschau(datei, ordner)` -> PNG je Seite, `als_pdf`, `als_bilder`,
  `VorschauFehler`). LibreOffice 24.2 aus apt (`libreoffice-writer-nogui`, `libreoffice-impress-nogui`,
  `fonts-crosextra-carlito`, von Jan als root installiert, 21.10.), `/usr/bin/soffice`, etwa 5 s je Umwandlung.
  pypdfium2 5.14.0 in der .venv. Agenten, die die Vorschau nutzen, brauchen pypdfium2 in ihrer .venv. Der Test mit
  LibreOffice wird übersprungen, wenn soffice fehlt. Das AppImage (fehlende Systembibliotheken) ist wieder gelöscht.
- Befund aus der ersten Vorschau des Arbeitsblatts (`data/vorschau/`, nicht im Repo):
  - Fließtext erscheint in einer Serifenschrift: Die python-docx-Vorlage legt keine Schrift für Normal fest.
    In Schritt B Calibri 11 fest setzen.
  - Unterstrichene Tabs (Linien in der Kopfzeile) zeigt LibreOffice nicht. Für Ausfüll-Linien Rahmen nehmen.
  - Schreiblinien, Kasten und Tabelle sehen aus wie gedacht.
- Neu aufsetzen: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, dann
  `echo /home/agent/agenten/shared > .venv/lib/python3.12/site-packages/agentkit.pth`.

## Zuerst lesen
1. `../../CLAUDE.md`: Regeln. Dieser Chat ändert nur shared/renderer/, Bedarf anderswo steht in
   `../../STATUS.md`.
2. `../../STATUS.md` (Punkt 8) und `../../docs/uebergabe-lia-dokumente.md` (Lias Agent, der den Renderer nutzt)
3. `../../dokumente/STATUS.md`, Abschnitt Anforderungen: Jans Wünsche (Vorlagen, Bearbeiten, Excel,
   Textfassung zur Selbstkontrolle, Fehler zurück an Claude). Gilt später, nicht für den ersten Schritt.

## Entscheidungen (Jan, 21.10.)
- **Umfang des Kerns:** alle vier Bausteine:
  - Titel, Überschriften, Absätze, Listen, Tabellen
  - Aufgaben mit Platz für Antworten (Linien oder Kästen)
  - Kopfzeile (Name, Klasse, Datum)
  - Folien mit Titel und Stichpunkten
- **Formate:** zuerst nur docx und pptx (python-docx, python-pptx). PDF später, wenn Bedarf da ist. Typst oder
  LibreOffice nur nach erneutem Okay von Jan.
- **Vorlagen:** sollen über die Bedienoberfläche (Telegram) vorgegeben werden können. Aufteilung:
  - Renderer: optionales Feld für eine Vorlage (docx/pptx). Mit Vorlage baut er auf deren Stilen bzw.
    Folienmastern auf, ohne Vorlage auf schlichten Standardstilen. Dazu eine Hilfsfunktion, die .dotx/.potx in
    .docx/.pptx umwandelt.
  - Agent: legt die Vorlagen unter `<agent>/data/vorlagen/` ab, nicht im Renderer.
  - Zentrale: Lias `portal.py` muss Dateien annehmen. Das macht der Hauptordner-Chat (steht in `../../STATUS.md`,
    Punkt 8).
  - Ob Lia eine Schulvorlage hat, ist noch offen. Für den Kern ist das egal.
- **Tests:** eigene `shared/renderer/.venv` mit python-docx 1.2.0 und python-pptx 1.0.2 (gleiche Versionen wie
  in `dokumente/`). Dazu kommt ein Eintrag in `pruefen.sh`.
- **Laufzeit:** Die Agenten importieren den Renderer über agentkit.pth in ihrer eigenen .venv. Darum brauchen
  sie dort python-docx bzw. python-pptx. Die .venv des Renderers ist nur für die Tests da.

## Lias Design (Vorbilder von Jan, 21.10.)
Vorbilder liegen in `data/lia-vorbilder/` (nicht im Repo): `arbeitsblatt-5.2.pdf` (Word), `praesentation-5.pdf`
(Lias Unterrichtspräsentation). Der Kern aus Schritt 2/3 ist dafür zu schlicht. Was die Vorbilder zeigen:
- **Arbeitsblatt** (A4, Calibri 11):
  - Kopf als Tabelle im Text, nicht als Kopfzeile: links Fach („Ethik“) und Lehrkraft („Frau Pohlmann“), Mitte
    das Thema als Leitfrage (gelb-orange hinterlegt) und „Arbeitsblatt 5“, rechts Datum und Name zum Ausfüllen.
  - Merksatz-Kasten: doppelter Rahmen, rosa-lila hinterlegt, Titel fett („Merksatz zu Peter Singer:“).
  - Arbeitsanweisung fett, darunter Material („Beispiel“) grün hinterlegt.
  - „Aufgaben:“ fett, nummeriert 1., 2., ..., der Aufgabentext fett. Antwortarten: im Text unterstreichen
    (kein Platz), Ankreuzen mit Kästchen nebeneinander, Satzanfänge mit Schreiblinien („Nach Peter Singer sollte
    Yasmin ____“).
  - Hilfen zu einzelnen Aufgaben klein am Seitenende („**Aufgabe 1:** Du findest Hinweise in den Zeilen 1-2“).
  - Seite 2 im Querformat: leere Tabelle zum Ausfüllen mit gedrehter Schrift.
- **Folien** (16:9, Aptos, Akzentfarbe Rot um #C00000):
  - Titelfolie: roter Balken links mit weißem Icon, rechts Titel rot fett, darunter „Ethik · Klasse 8“ grau.
  - Jede Folie: Titel rot fett, roter Strich darunter, optional Icons rechts oben, Fußzeile klein grau
    „Fach · Klasse · Thema“ und Foliennummer.
  - Bausteine: grauer Textkasten mit rotem Balken links (Material, letzter Satz fett), Leitfrage weiß auf roter
    Fläche, zentrierter großer fetter Text (Ziel, Arbeitsauftrag), Zeitangabe mit Wecker-Icon, zwei Spalten
    (Merksätze mit roter Überschrift auf Grau), Auswahl (zwei Kästen mit rotem Rand), Satzanfang grün mit
    Zeigefinger-Icon, Feedback (Smileys mit Satzanfängen), farbige Unterstreichung von Textteilen mit Legende
    (Behauptung blau, Begründung orange, Beispiel grün).
- Calibri und Aptos sind Microsoft-Schriften. Auf dem Server gibt es keine Schriften. Für die Vorschau ersetzt
  Carlito Calibri mit gleichen Maßen, für Aptos gibt es keinen genauen Ersatz (Vorschau nur ungefähr).

## Entscheidungen (Jan, 21.10., nach den Vorbildern)
- Der Renderer baut Arbeitsblätter und Folien in Lias Stil (siehe oben).
- **Vorschau:** LibreOffice (ohne sudo, in ~/.local) wandelt docx/pptx in PDF um, pypdfium2 macht daraus Bilder.
  So prüfen Claude und dieser Chat das Aussehen. Installation erst nach Jans Okay zum konkreten Plan.
- **PDF lesen** (Lia schickt PDFs als Vorlage): kommt in agentkit (Seiten als Bilder mit pypdfium2), Bedarf steht in
  `../../STATUS.md`. Der Renderer liest nichts.
- **Icons:** freies Icon-Set (z. B. Tabler Icons, MIT-Lizenz). Python zeichnet sie als PNG in der gewünschten Farbe.
- Das Format darf jetzt noch umgebaut werden, denn noch nutzt es kein Agent. Ab der ersten Nutzung gilt: nur
  erweitern.

## Vorgaben
- Schnittstelle stabil halten: Beide Instanzen nutzen den Renderer sofort, es gibt kein versioniertes Paket.
  Das Format nur erweitern, nicht umbauen, und jede Erweiterung mit Tests.
- Eingabe streng prüfen, bevor gebaut wird (Schema). Fehlermeldungen so schreiben, dass Claude sie in derselben
  Sitzung beheben kann.
- Ausgabe zur Selbstkontrolle: eine Textfassung des fertigen Dokuments, die Claude lesen kann.
- Keine Inhalte, Zugangsdaten oder Netzzugriffe im Renderer.

## Fertig heißt (erster Schritt)
- `from renderer import ...` baut aus einer Beispielbeschreibung ein Arbeitsblatt als docx und eine kleine
  Folienreihe als pptx.
- Ungültige Beschreibungen ergeben klare Fehler.
- Es gibt Tests, `./pruefen.sh` ist grün, die Schritte sind committet, und diese STATUS.md beschreibt das Format.

## Offene Punkte
0. Neuer Plan für Lias Stil, von Jan freigegeben (21.10.). Er ersetzt die Schritte 4 bis 6 unten:
   - A. (erledigt) Vorschau: LibreOffice, Carlito, pypdfium2, vorschau.py
   - B. Arbeitsblatt in Lias Stil: Kopf-Tabelle, Merksatz, Material, Arbeitsanweisung, Aufgaben mit Antwortarten
     linien/kasten/ankreuzen/satzanfaenge/keine und Hilfen am Seitenende, Querformat-Seite mit Ausfülltabelle.
     Format darf umgebaut werden. Prüfen: Lias AB 5.2 nachbauen, Vorschau mit dem Original vergleichen.
   - C. Icons: Tabler Icons (MIT) als Schrift, Pillow zeichnet PNG in jeder Farbe, feste deutsche Namensliste.
   - D. Folien in Lias Stil (siehe „Lias Design“), Lias Präsentation 5 nachbauen und vergleichen.
   - E. Vorlagen, Textfassung, Beispiele, Doku (alte Schritte 5 und 6).
   - Design-Profil (Farben, Schriften, Fach, Lehrkraft) gibt der Agent mit, der Renderer enthält keine Daten von Lia.

Erster Plan (21.10.), je Schritt ein Commit. Schnittstelle: `pruefen(beschreibung)` -> Fehlerliste,
`bauen(beschreibung, ziel, vorlage=None)` -> Ergebnis(pfad, textfassung), `vorlage_umwandeln(quelle, ziel)`,
`BeschreibungUngueltig`. Vorlage ist ein Parameter des Agenten, nicht Teil von Claudes JSON.
Module: pruefung.py, arbeitsblatt.py, folien.py, vorlagen.py, FORMAT.md, beispiele/.
1. (erledigt) .venv, requirements.txt, pruefen.sh, leeres Paket mit Test
2. (erledigt) pruefung.py mit Tests, FORMAT.md (art arbeitsblatt: titel, kopfzeile, bloecke ueberschrift/absatz/liste/
   tabelle/aufgabe mit antwort linien|kasten; art folien: titel, untertitel, folien mit titel/punkte).
   Streng: unbekannte Felder sind Fehler, alle Fehler auf einmal mit Pfad (`bloecke[4].antwort.anzahl: ...`).
3. (erledigt) Arbeitsblatt als docx mit Tests (Linien/Kästen per XML, Kopfzeile auf jeder Seite, A4)
4. Folien als pptx mit Tests (Layouts nach Platzhaltertyp suchen, nicht nach Namen)
5. Vorlagen: Umwandlung .dotx/.potx und Parameter `vorlage`, mit Tests
6. Beispiele, Textfassung über agentkit.textfassung im Ergebnis, Format hier in STATUS.md.
   Vorher mit Jan klären: agentkit.textfassung setzt Tabellen ans Ende, zeigt keine Listenzeichen, keine
   Kopfzeile und keine Antwortlinien. Für die Selbstkontrolle reicht das evtl. nicht (Änderung wäre im
   Hauptordner-Chat).

## Gelernte Regeln
- (noch keine)
