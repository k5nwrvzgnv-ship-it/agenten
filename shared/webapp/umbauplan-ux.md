# Umbauplan zum UX-Befund (zweite Fassung, schrittweise freigegeben)

Stand 10.11.2026. Die erste Fassung hat die Knöpfe nur sortiert und ins ···-Menü geschoben. Jan: Das trifft es nicht.
Diese Fassung geht von drei Grundsätzen aus (Jan 10.11., dazu Punkt 37 der Haupt-STATUS: „willst du 1000 Knöpfe
entwickeln“, Bearbeiten-Flächen unintuitiv, Wunsch Ziehen statt Formulare):

1. **Ein Plus pro Seite, dann wählen.** Ein „+“ oben rechts öffnet eine kurze Liste, was hier neu entstehen kann.
   Es ersetzt „+ Neu hier“, „+ Gespräch“, „+ Stunde“, „+ Reihe“, „+ Datei ablegen“/„Hochladen“ und „Neuer Auftrag +“.
2. **Die Seite zeigt nur, was da ist.** Keine Formulare, keine Erklärtexte, keine leeren Abschnitte auf der Seite.
3. **Ändern direkt am Ding.** Stunden ziehen, Titel anklicken und umbenennen, Datei auf die Seite ziehen. Was dann
   noch übrig ist (Archivieren, In andere Klasse übernehmen, Termine, Ausblenden, Löschen), steht im „···“. Später,
   wenn Claude im Gespräch handeln kann (Punkt 37), sagt Lia es dort, und das „···“ wird noch kürzer.

So sieht die Reihe danach aus (Beispiel):

```
Ethik › Klasse 8 › Straftheorien                         [+]  [···]
Straftheorien
Wozu strafen wir?
                                                 | Deine Dateien
Gespräche   Such mir eine Reihenfrage   gestern  |   Planung.pdf
Stunden     1  Einstieg     Arbeitsblatt · läuft | Termine
            2  Kant: Vergeltung                  |   Di 11.11., Do 13.11.
            3  von Liszt                         | Schon behandelt
Material    Reihenentwurf               Final    |   Strafzwecke

[+]  → Gespräch · Material … · Stunde · Datei
[···] → Reihe bearbeiten · Termine · In andere Klasse übernehmen · Archivieren
```

Was das „+“ je Seite anbietet:

| Seite | Im „+“ |
|---|---|
| Heute | Gespräch (ohne Ort), Material … |
| Klasse | Gespräch, Reihe, Datei |
| Reihe | Gespräch, Material …, Stunde, Datei |
| Stunde | Gespräch, Material …, Datei |

„Material …“ führt wie heute zur Auswahl in Neu (Arbeitsblatt, Präsentation, … , Anderes Dokument), schon mit dem Ort.
„Stunde“ legt sofort eine Stunde mit offenem Thema an; das Thema schreibt Lia danach direkt in den Titel.

## Spielregeln

- Ein Schritt = ein Commit über `~/agenten/commit.sh`, vorher `./pruefen.sh` mit `flock` auf `commit.sperre`.
- Vorlagen und CSS wirken sofort auf Lias Dienst; Zwischenstände darf Lia sehen (Jan 10.11.). Nach jedem Schritt
  der Rundgang über alle Seiten gegen 127.0.0.1:8791 (nur lesend, alle 200). Python erst nach Neustart, mit Jans Okay.
- Menüs sind `<details>` wie heute in `gespraech.html:18`, gehen also ohne JavaScript. Wo JavaScript dazukommt
  (Schritt 4), bleibt ein Weg ohne: das „···“ führt dann zu den heutigen Masken.
- Kein neues Paket, keine fremden Skripte, CSP bleibt `'self'`.

## Schritt 1: Das Plus (gebaut 10.11.2026)

Gebaut wie unten, mit einer Abweichung: Die Ergebnis-Seite behält „+ Neu hier“ bis Schritt 6, und „Gespräche ohne Ort“
behält ihren Knopf „+ Gespräch“ (dort gibt es nur das eine). Eine abgeschlossene Reihe bietet kein „Material …“ (wie
vorher „+ Neu hier“ nur an laufenden Reihen). Tests: `test_plus_je_seite`, angepasst `test_reihe`,
`test_neu_hier_mit_art_und_stunde`, `test_formular_und_einstieg_in_heute`, `test_neu_stunde_waehlen`,
`test_baum_mit_neu_und_altes_format_ohne_masken`.


- Dateien: neu `oberflaeche/_plus.html` (Makro, Einträge je Seite), `basis.html:25` („+ Neu hier“ wird das „+“),
  `_ort.html:53–58` („+ Gespräch“ unten im Abschnitt weg, wandert ins „+“), `reihe.html:60–68` (Formular „+ Stunde“
  weg, Eintrag „Stunde“ im „+“ schickt dasselbe Formular mit leerem Thema), `klasse.html:34` („+ Reihe“ ins „+“),
  `_heute.html:10–12` („Neuer Auftrag +“ wird das „+“), `ruhig.css` (Plus-Knopf, Menü wie `.menue`). Eintrag „Datei“
  springt in diesem Schritt noch zum Abschnitt „Deine Dateien“ (richtig gelöst in Schritt 4).
- Lia sieht danach: Oben rechts ein „+“ statt bis zu drei verteilter blauer Knöpfe. Der nachgeklickte Weg „Material
  für eine Stunde“ beginnt dort, wo man ihn sucht.
- Tests: `test_app.py:863` (prüft „+ Neu hier“), `test_gespraech` und `test_gespraech_geloescht_meldung` (Gespräch
  anlegen: Route bleibt, Formular steht jetzt im „+“), `test_pflege_app.py` (+ Stunde, + Reihe: Routen bleiben,
  HTML-Prüfungen anpassen), Heute-Tests (`knopf-gross`). Neu: je Seite genau ein „+“ mit den Einträgen der Tabelle,
  im Archiv kein „+“.

## Schritt 2: Nur zeigen, was da ist (gebaut 10.11.2026)

Gebaut wie unten, nur Vorlagen und CSS. Abweichungen und Einzelheiten: „Deine Dateien“ bleibt ohne Dateien im HTML
(Sprungziel `#ablage` für „Datei“ im „+“ und die Weiterleitungen der Ablage), `ruhig.css` zeigt den Abschnitt dann nur
angesprungen (`:target`), mit Fehler oder Erledigt-Meldung immer. Ohne Stunden bleiben an der Reihe „Termine“, deren
Hinweis und Fehler ohne Überschrift stehen (bis Schritt 3). Die Klasse ohne Stundenplan zeigt nur den Link
„Stundenplan eintragen“; „Keine kommenden Termine.“ ist weg. Abschnittsnummern zählen nur Gezeigtes. Die leise Zeile
(`noch_leer` in `_ort.html`) steht, wenn an der Ebene kein Gespräch, kein Material, keine Datei, keine (ausgeblendete)
Stunde und an der Klasse kein Termin ist; im Archiv ohne „Mit + fängst du an.“ Heute: „Weiter im Gespräch“ nur mit
Gesprächen, auch wenn sonst kein Abschnitt da ist. Die Fach-Seite (`fach.html`) ist nicht Teil des Schritts und hat ihre
Leertexte noch. Tests: neu `test_nur_zeigen_was_da_ist`, `test_heute_ohne_leere_abschnitte`; angepasst `test_reihe`,
`test_gespraech`, `test_stunden`, `test_aendern_kopieren_ausblenden_loeschen`.

- Dateien: `_ort.html:23` und `:46` (Leertexte Dateien und Gespräche), `reihe.html:35–42`, `:57`, `stunde.html:10–18`,
  `klasse.html:39–46`, `:62–68`, `_heute.html:19–23`, `:46–56`. Leere Abschnitte fallen ganz weg. Ist eine Seite
  ganz leer, steht dort eine leise Zeile „Noch leer. Mit + fängst du an.“
- Lia sieht danach: Die abgeschlossene Reihe „Helfen“ ist Titel und Reihenfrage. Auf Heute fehlen „Läuft gerade“ und
  „Weiter im Gespräch“, wenn dort nichts ist. Der Satz über den Umweg zum Material an der Stunde ist weg.
- Tests: `test_app.py` („Noch kein Gespräch hier.“, „Noch nichts zur ganzen Reihe.“, „Noch keine Stunden.“,
  „Weiter im Gespräch“), `test_pflege_app.py` („Noch keine“). Neu: leere Reihe ohne Abschnitte, mit der leisen Zeile.

## Schritt 3: Seltenes ins „···“ (gebaut 10.11.2026)

Gebaut, nur Vorlagen und CSS: Makro `punkte` in `_plus.html`, Block `punkte` in `basis.html` rechts neben dem „+“.
Abweichungen: „Stunde verschieben“ steht sichtbar im „···“ der Reihe statt unsichtbar (ohne JavaScript und auf dem iPad
sonst nur über die Stunde); `ziehen.js` füllt weiter dasselbe Formular `#verschieben`. Im Archiv bleibt
„Wiederherstellen“ am Hinweis „Im Archiv …“ (dort das Naheliegende), im „···“ dann nur Bearbeiten und Übernehmen; die
Stunde im Archiv hat kein „···“. Die Klasse hat im „···“ Bearbeiten (Archivieren steht dort in der Maske, wie bisher),
„Stundenplan eintragen“ bzw. „ändern“ und Zusatztermin; der Abschnitt „Termine“ erscheint nur mit Stundenplan, Terminen
oder Hinweis. Fehler (z. B. Thema zu lang) stehen oben auf der Seite, an der Stunde ist das „···“ dann offen. „fällt
aus“ je Termin bleibt an der Terminzeile (direkt am Ding). Tests: neu `test_seltenes_im_punkte_menue`, angepasst
`test_stunden`, `test_nur_zeigen_was_da_ist`; `test_pflege_app.py` lief unverändert grün.

- Dateien: `reihe.html:20–28` (Bearbeiten, Archivieren, In andere Klasse übernehmen), `:81–94` (Termine, Reihe
  beginnt am), `stunde.html:20–61` (ganzer Bearbeiten-Block: Marke, Verschieben, Kopieren, fällt aus, Ausblenden,
  Löschen), `klasse.html:29–37` (Bearbeiten, Archiv), `:69–81` (Zusatztermin), `ruhig.css`. Das Formular
  „Verschieben“ (`reihe.html:70–79`) bleibt unsichtbar auf der Seite, weil `statisch/ziehen.js` es füllt.
- Lia sieht danach: Kopfzeile mit Titel, „+“ und „···“, darunter nur Inhalt. Keine Knopfreihen und offenen Formulare
  mehr mitten auf der Seite.
- Tests: `test_pflege_app.py` (Verschieben, Bearbeiten, Ausblenden, Ausfall, „In eine andere Klasse“, „Die Reihe
  beginnt“: Routen bleiben, HTML anpassen). Neu: keine `zeile-form` mehr außerhalb von Menüs auf Klasse, Reihe, Stunde.

## Schritt 4: Direkt am Ding (JavaScript, mit Weg ohne) (gebaut 10./11.11.2026, live; Probe teilweise)

Gebaut: `oberflaeche/_direkt.html` (Makro `titel`: Überschrift plus verstecktes Formular mit den Feldern der
bestehenden Route), `statisch/direkt.js` (Titel anklicken: Feld, Enter speichert per normalem POST, Esc oder
„Abbrechen“ zurück; Ablage: „Datei“ im „+“ öffnet die Auswahl, Datei auf die Seite ziehen, danach Zeile mit Namen,
Regel, „Ablegen“, „Abbrechen“), neue Routen `/reihe/<id>/titel` und `/klasse/<id>/titel` (`app._titel_aendern`, nur
das eine Feld, Fehler als Meldung, Konflikt wie in den Masken), `ziehen.js` mit Finger (450 ms halten, dann ziehen;
Linie zeigt die Stelle). Abweichungen: Klasse benennt den Namen um („8“, angezeigt „Klasse 8“). Der Knopf heißt jetzt
überall „Ablegen“ (vorher „Hochladen“). Die Vorlagen wirken vor dem Neustart: Reihe und Klasse zeigen das Umbenennen erst,
wenn die App `titel_aktion` liefert (neues Python); Stunde und Gespräch nutzen alte Routen und gehen sofort. Tests:
`test_titel_direkt`, `test_direkt_am_ding` (mit nachgestellter alter App), Schutzliste in `test_regel_25…`. Neustart
11.11. mit Jans Okay. Browser-Probe 11.11. (Chrome bei Jan, ohne zu speichern): Titel, Menüs, schmales Fenster,
Zieh-Rahmen für Dateien ok; noch von Hand offen: Datei loslassen, „Datei“ im „+“, Stunden ziehen (Maus, iPad-Finger),
Enter speichert. Einzelheiten in STATUS.md.

- Dateien: neu `statisch/direkt.js`, Anpassungen in `reihe.html`, `stunde.html`, `klasse.html`, `gespraech.html`,
  `_ort.html:25–31`, `ruhig.css`.
  - **Titel anklicken, umbenennen** (Enter speichert, Esc bricht ab): Stunde über `/stunde/<id>/aendern`
    (`app.py:1475`), Gespräch über `/gespraech/<id>/umbenennen`. Für Reihe und Klasse verlangt
    `/reihe/<id>/bearbeiten` (`app.py:1288`) alle Felder; dafür je eine kleine Route nur für den Titel (Python,
    Neustart, Tests in `test_pflege_app.py`).
  - **Datei auf die Seite ziehen** oder „Datei“ im „+“ wählen: Danach eine Zeile mit Dateiname, „PDF, Word … bis
    20 MB. Keine Schülerdaten.“ und „Ablegen“. Der Regeltext steht nur noch in diesem Moment da.
  - **Stunden ziehen** gibt es schon (`statisch/ziehen.js`), aber nur mit der Maus. Für das iPad: Ziehen per Finger
    dazu (Touch-Ereignisse).
- Lia sieht danach: Sie ändert, wo sie hinschaut. Ohne JavaScript führt „···“ zu den heutigen Masken.
- Tests: POST-Wege bleiben, neue Titel-Routen mit Tests; HTML: Titel tragen die nötigen Daten. Pflicht: Probe im
  Browser (Mac und iPad, falls Lia es nutzt), weil die Unittests kein JavaScript ausführen.

## Schritt 5: Raster mit rechter Spalte (gebaut 11.11.2026, live; Browser-Probe 11.11.)

Gebaut, nur Vorlagen und CSS: Makro `rechts_spalte` in `_ort.html` (aside `rechts` mit „Deine Dateien“ oben, darunter
der Kontext der Seite). Reihe: Termine (die Daten der Stunden, je ein Link auf die Stunde), Schon behandelt (aus der
Mitte nach rechts). Stunde: Termin mit Stunde („Di 11.11., 3. Std.“), Reihenfrage aus der Reihe (Link zur Reihe).
Klasse: der ganze Abschnitt Termine (Stundenplan, vergangene, kommende, „fällt aus“, Sprungziel `#termine`). Raster
in `ruhig.css`: Seitenleiste 240 px, dann Mitte (bis 736 px, also 640 px Text) und rechts 280 px zusammen mittig im
übrigen Platz; Seiten ohne rechte Spalte (Masken, Heute, Material, Fach) einspaltig bis 820 px und mittig. Das Gespräch
hat dasselbe Raster (vorher Mitte bis 820, rechts 300). Umbruch unter 1100 px und unter 760 px wie bisher. Abweichung:
Die Spalte steht an Klasse, Reihe und Stunde immer im HTML, weil `#ablage` dort Sprungziel bleibt. Ist außer der
zugeklappten Ablage nichts da, heißt sie `rechts-still` und ist per CSS (`:has`) unsichtbar, bis „Datei“ im „+“ dorthin
springt oder `direkt.js` `.ablage-offen` setzt. Ab 1101 px fällt dann auch ihre Spur weg (Rahmen `still-rechts`, Mitte
736 px mittig; Befund der Browser-Probe 11.11.: sonst 280 px leer rechts, linkslastig). „Leer“
(`noch_leer`) zählt weiter die ganze Seite (Termine und Dateien rechts eingeschlossen). Tests: neu
`test_rechte_spalte` (`test_app.py`), `test_termine_in_der_rechten_spalte` (`test_pflege_app.py`); angepasst
`test_nur_zeigen_was_da_ist`. `test_schnell.py` lief unverändert grün. Rundgang 11.11. gegen 8791: 615 Seiten, alle 200,
`lia/instanz` unverändert.

- Dateien: `basis.html:14`, `reihe.html`, `stunde.html`, `klasse.html` (Block `rechts`: Deine Dateien, Termine, Schon
  behandelt; wie `gespraech.html:76–106`), `ruhig.css:30–35` (Mitte ~640 px, rechts ~280 px; Masken einspaltig und
  mittig), Umbruch unter 1100 px bleibt (`ruhig.css:322`).
- Lia sieht danach: Links was sie tut (Gespräche, Stunden, Material), rechts der Kontext. Ebenen und Gespräch sehen
  gleich aus; rechts ist nicht mehr leer.
- Tests: `test_app.py` (Rahmen-Klassen), `test_pflege_app.py` (Termine auf Klasse und Reihe), `test_schnell.py`
  (TestSchnellNeu). Neu: Ebenen haben `aside.rechts`.

## Schritt 6: Ergebnis-Seite (gebaut 11.11.2026, live; Browser-Probe 11.11.)

Gebaut, nur Vorlagen und CSS (kein Neustart): `ergebnis.html` neu geordnet. Rückmeldung als Feld wie im Gespräch
(`form.eingabe`, Platzhalter „Was soll anders werden? Ich ändere es für dich. …“, „+ Datei anhängen“, „Senden“), immer
unter „Das Wichtigste“; `?offen=rueckmeldung&fassung=…&datei=…` setzt weiter das Ziel (Zeile „Zu … Stattdessen zum
Ganzen“), Route und schneller Weg unverändert. Je Datei ein Download-Symbol (`details.laden`, SVG-Pfeil) mit „PDF zum
Drucken“, „In Word öffnen“ und „Rückmeldung zu dieser Datei“, auch an der schnellen Fassung oben (ohne
Rückmeldungs-Eintrag) und an Dateien früherer Fassungen. Im „···“: Als final markieren (Fassung oben), Eigene Fassung
hochladen (`?offen=eigene` öffnet es, Fehler stehen darin), Gehört zu Reihe, Gehört zu Stunde. Verlauf: geschlossene
Klappe (`details.mehr`) „Verlauf: N Fassungen, M Rückmeldungen“ (Fassungen = die man final markieren kann), erst ab zwei
Stationen. „+ Neu hier“ ist das „+“ (`_plus.html` `plus(…, voll=false)`: hier nicht blau, „Senden“ ist der eine blaue
Knopf, bei finaler Fassung keiner) mit „Material …“ und „Variante“; der Block `plus` in `basis.html` ist jetzt leer.
Abweichungen: Die Final-Knöpfe älterer Fassungen bleiben in der Verlauf-Klappe. Die Varianten-Leiste erscheint erst mit
einer Variante (vorher auch nur „normal“ und „+ Variante“). Die Seite lädt `einmal.js` immer und `gespraech.js` für den
Namen der angehängten Datei. Seiten oben 2 × 260 px statt 2/3 der Breite. Tests: neu `test_ergebnis_seite_ruhig`,
`test_verlauf_zeile`; angepasst `test_ergebnis`, `test_varianten`, `test_reihe_zuordnen`, TestMaterial
(`test_ein_hauptknopf`, `test_eigene_fassung`, `test_rueckmeldung_je_datei`, `test_datei_wege_erklaert`,
`test_rueckmeldung_im_testbetrieb`). `test_schnell.py` lief unverändert grün. Rundgang 11.11. gegen 8791: 600 Seiten
(15 weniger, die Links `?offen=rueckmeldung`/`?offen=eigene` ohne Ziel fehlen), alle 200, `lia/instanz` unverändert. Browser-Probe 11.11.: 940 px hoch bei 1440 px (vorher 4059), Menüs im Fenster, Sprung
zum Feld ok. Daraus behoben: Name der Fassung über dem Feld aus dem Verlauf (vorher ohne Lias eigene gezählt, „Fassung 7“
statt „10“), Fokus im Feld nach dem Sprung (Test `test_ziel_der_rueckmeldung`), „Eigene Fassung hochladen …“ als
Eintrag im „···“ statt eines Dateifelds, Name und „Hochladen“ erst nach der Wahl (`direkt.js`, `form[data-datei-zeile]`,
Test `test_eigene_fassung_im_menue`). Befunde für später in STATUS.md.

- Dateien: `ergebnis.html`, `ruhig.css`.
  - Rückmeldung als immer sichtbares Eingabefeld unter „Das Wichtigste“ („Was soll anders werden?“, Datei anhängen,
    Senden), wie im Gespräch: kein Knopf, der erst eine Tafel öffnet (`:173`, `:186–210`). Route und schneller Weg
    bleiben gleich.
  - Je Datei ein Download-Symbol mit Auswahl PDF/Word und „Rückmeldung zu dieser Datei“ (`:50–57`).
  - „Eigene Fassung hochladen“ und „Als final markieren“ ins „···“ (`:175–178`, `:290`).
  - „Fassungen“ als eine geschlossene Klappe „Verlauf: 10 Fassungen, 6 Rückmeldungen“ (`:258–295`).
- Lia sieht danach: Kopf, Dateien, das Wichtigste, das Feld für ihre Rückmeldung, eine Zeile Verlauf. Etwa eine
  Bildschirmhöhe statt 4059 px.
- Tests: `test_app.py` (TestMaterial: „Als final markieren“, „Rückmeldung geben“, „Fassungen“, `test_rote_marken`
  erwartet genau einen blauen Knopf), `test_schnell.py` (TestSchnellNeu: Rückmeldung ohne Datei an lia/schnell,
  schnelle Fassung oben).

## Schritt 7: Gespräch-Seite und restliche Texte (gebaut 11.11.2026, live; Browser-Probe 11.11.)

Gebaut, nur Vorlagen (kein Neustart): Kopf des Gesprächs Name und „···“, darin zuerst „Daraus Auftrag machen“
(gleiche Route `sonder`, art `auftrag`). „Frag einfach los, so lang du willst. Keine Namen von Schüler*innen.“ ist der
Platzhalter; der leere Verlauf hat keinen Text. Die Klappe „Kennt …“ ist die einzige Angabe, was das Gespräch kennt;
der Satz rechts „Dieses Gespräch kennt keine Klasse …“ ist auch weg. Gekürzt: `gespraeche.html` („30 Tage“ nur in der
Klappe), `neu.html` (Tipp und „Weitere Arten“, Mikrofon, Satz unter „Auch als“, Überarbeiten-Hinweis, „Beachtet: …“;
Ort steht oben), `vorlagen.html` (ein Satz), `ich.html` (Satz nur in der Leerzeile), `pflege_reihe_neu.html` (ohne
„Je Termin entsteht …“; ohne freie Termine nur „Stunden“ mit Zahlenfeld). Abweichung: Die Zeilennummern galten
weiter (neu.html `:95–99` war Datei-Text und „Beachtet“). Tests: `test_gespraech` (Kopf, Menü, Platzhalter, eine
„Kennt“-Angabe, ohne Ort), `test_formular_und_einstieg_in_heute`, `test_neu_hier_mit_art_und_stunde`,
`test_vorlagen_und_ich`, `test_anlegen_mit_terminen_regel_32`. Rundgang 600 Seiten, alle 200. Browser-Probe 11.11.:
alles ok in 1440/1100/407 px; daraus „z. B. 6“ als Platzhalter im Feld „Stunden“. Befunde (Formulare im „···“,
„Senden“ bei 407 px links, Dateifeld in Neu, Brotkrumen, zwei Raster) in STATUS.md.


- Dateien: `gespraech.html:14–17` („Daraus Auftrag machen“ ins „···“), `_verlauf.html:27` („Frag einfach los …“ in den
  Platzhalter, `gespraech.html:58`), `gespraech.html:70–73` (bleibt einzige Angabe, was das Gespräch kennt),
  `gespraeche.html:21`, `neu.html:25`, `:42`, `:89`, `:95–99`, `vorlagen.html:48–49`, `ich.html:14–15`,
  `pflege_reihe_neu.html:18–21`.
- Lia sieht danach: Kopf des Gesprächs nur Name und „···“; weniger Text in Neu, Vorlagen und Ich.
- Tests: `test_app.py` („Frag einfach los“, „Daraus Auftrag machen“, Neu-Tests in TestNeuerAuftrag).

## Später

- Ändern im Gespräch statt im „···“ (Punkt 37, `docs/gespraech-flexibel-plan.md`, ruht gerade).
- Gebaut 11.11.2026 (Jans Wahl), Python, wirkt erst nach Neustart von `webapp.service`; die Vorlagen laufen mit der
  alten App wie bisher:
  - Stand der Reihe als Kennzeichen im Baum statt „(in Planung)“ im Namen: in Planung ein leiser hohler Punkt hinter
    dem Namen, abgeschlossen graue Schrift, der Stand als `title` und für Vorleser (`logik.baum` „stand“,
    „stand_text“; `basis.html`, `.baum-stand`, `.baum-fertig`). Stunde im Baum „1 · Thema“. „Ich“ heißt „Deine
    Regeln“ (`logik.SEITE_REGELN`; Route `/ich` bleibt). Tests vergleichen weiter mit dem früheren Baum
    (`test_ordnung.wie_frueher`).
  - „Fertig“ auf Heute je Reihe als Klappe (`logik.fertig_je_reihe`, `heute` liefert `fertig_gruppen`): Zeile mit Name,
    „5 Ergebnisse · zuletzt So 08.11.“ und Fach › Klasse, darin die Ergebnisse ohne Brotkrume; ohne Reihe einzeln;
    auch eine Reihe mit einem Ergebnis ist eine Klappe (Jans Vorschau). Die Grenze 10 zählt Einträge.

## Reihenfolge

1 → 2 → 3 sind reine Vorlagen und je eine kurze Sitzung; danach sieht jede Ebene schon ruhig aus. 4 ist die größte
und braucht eine Browserprobe. 5 bis 7 je eine Sitzung. Nach Schritt 3 lohnt ein Blick mit Lia.
