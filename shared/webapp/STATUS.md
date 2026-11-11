# Status: Web-App für Lia (shared/webapp)

## Zweck
Überblick für Lia im Browser statt Telegram: was auf sie wartet, was läuft, was fertig ist. Später auch neue Aufträge,
Ergebnisse mit Vorschau, Feedback und Entwürfe. Plan: `../../docs/webapp-plan.md` (4.7 Technik, 7 Bauplan),
Auftrag und Entscheidungen: Punkt 24 in `../../STATUS.md`. Gestaltung „Modernist“ (Board ModHeute im Canvas
https://claude.ai/artifact/F8ysVSyr8TjGhFDcyNnejU).

## Oberfläche und schneller Weg (Stand 10.11.2026, Plan `../../docs/schnell-dokument-plan.md` Schritt 3)
`webapp.service` läuft seit 10.11. 12:30 auf ad9539a mit `WEBAPP_OBERFLAECHE=neu` (Jans Okay 10.11.): Lia sieht
`oberflaeche/` + `ruhig.css` mit Gesprächen und Ablage. Die Unit im Repo ist gleich der installierten. Nach dem Neustart
geprüft (nur lesend): Rundgang über 113 Seiten ab `/` gegen 127.0.0.1:8791, alle 200, „Anderes Dokument“ unter Neu
sichtbar, Rückmeldung-Formular da, kein Fehler im Log. Die alte Oberfläche ist für Lia nicht tragbar (Jan 10.11.);
die neue soll später noch besser werden (Punkt 37 der Haupt-STATUS).
- Schalter `WEBAPP_OBERFLAECHE`: `neu` nimmt `oberflaeche/` + `ruhig.css`, ohne Angabe oder `alt` gelten `vorlagen/` +
  `stil.css` mit der Spalte „Fragen“ (`/fragen`, `/teile/frage/<id>`). Die Routen der jeweils anderen Oberfläche geben
  404. Tests: `test_app.py`, `test_pflege_app.py` und `test_schnell.py` (TestSchnellNeu) prüfen `oberflaeche/`,
  `test_alt.py` und `test_schnell.py` (TestSchnell) die alte.
- `oberflaeche/` und `ruhig.css` wirken sofort auf den laufenden Dienst, Python erst nach dem Neustart. Nach Änderungen
  dort den Rundgang gegen 127.0.0.1:8791 wiederholen.
- Schneller Weg über lia/schnell (Schnittstelle: Abschnitt „Schnittstelle“ in `../../lia/schnell/STATUS.md`): ohne
  eigenen Schalter (Jan 10.11.: eine knappe Änderung soll von selbst schnell gehen, keine Wahl für Lia), in beiden
  Oberflächen, immer wenn Neu eingeschaltet ist (`WEBAPP_NEUER_AUFTRAG`, `app.schnell`):
  - Rückmeldung am Dokument ohne Datei an Dokumenten von unterricht, theater, schnell geht an `schnittstelle.aendern`
    statt an den Feedback-Dienst (`logik.schnell_ziel`): an einer Datei genau diese (mit Seite), zum Ganzen die
    neueste Fassung, wenn sie schnell geändert ist (`eigene=n`) oder vom Assistenten mit genau einer Datei. Mit
    Datei, bei Lias eigener Datei als neuester Fassung, mehreren Dateien oder anderen Agenten: gründlich an
    feedback. „Zu groß“ gibt lia/schnell selbst gründlich weiter.
  - „Neu“ hat die Karte „Anderes Dokument“ (`logik.VORLAGE_DOKUMENT`): Text, Ort, bis 5 Dateien an
    `schnittstelle.dokument`, danach Warteseite `/neu/schnell/<id>`, fertig weiter zur Ansicht des Auftrags.
  - Anzeige: Seite mit `?schnell=<id>` zeigt „Wird geändert …“ (bzw. „Wird erstellt …“) und fragt per htmx alle
    2 s `/teile/schnell/<id>` ab, nach 3 Minuten „dauert länger“ und alle 10 s. Mit Antwort HX-Redirect auf die
    Seite, Claudes Satz steht oben (Fehler rot). Ohne JavaScript: „Neu laden“. Doppelklick: gleicher Wunsch in
    2 Minuten wird nicht neu gestellt (im Speicher).
  - Schnell geänderte Fassungen (Notiz beginnt mit „Schnell geändert: “) heißen „von mir“; ist die neueste eine
    solche mit Seitenbildern, steht sie oben (Bilder, PDF, Word). Bilder neben der Datei im Agent-Ordner (dort legt
    lia/schnell sie seit be38551 ab), sonst aus `lia/schnell/data/fassungen/<ursprung>/eigene-<n>/` (Routen
    `/ergebnis/<id>/eigene/<n>/seite/<m>`, `…/pdf`). Kennzeichen `schnittstelle.NOTIZ_PRAEFIX` (zugesichert, Test
    gleicht ab). Schnelle Dokumente tragen nur `ort`; `logik.reihe_von` liest daraus die Reihe (nur agent schnell).
  - Echt startet die App nach jedem Wunsch `lia-schnell.service` (zusätzlich zur Pfad-Unit); Testbetrieb schreibt
    nach `data/schnell-test/`, kein Agent liest das.
  - Im Gespräch (lia/chat) gibt es keinen schnellen Weg: Schreibt Lia eine Änderung dort statt in „Rückmeldung
    geben“, geht sie an lia/chat.
- Probe 10.11. auf der Test-Instanz (8795, neue Oberfläche, Testbetrieb, Antwort von lia/schnell von Hand über die
  Schnittstelle geschrieben): Rückmeldung ohne Datei an lia/schnell, „Wird geändert …“ mit htmx, HX-Redirect, Satz
  oben, schnelle Fassung oben mit Seitenbild, PDF und Word; „Anderes Dokument“ bis zur Warteseite; 81 Seiten 200.
- Nicht geprüft: im Browser (htmx-Abfrage, HX-Redirect, Aussehen der neuen Oberfläche mit „Wird geändert …“), und der
  schnelle Weg auf dem echten Dienst mit einer echten Antwort von lia/schnell. Bei der Probe mit Lia ansehen.

## UX-Befund und Umbauplan (Stand 11.11.2026, Schritte 1 bis 4 gebaut und live)
`befund-ux.md` (fünf Ursachen, Fundstellen mit Datei:Zeile, Screenshots und Skizzen in `skizzen/befund/`) und
`umbauplan-ux.md` (zweite Fassung nach Jans Rückmeldung 10.11.: ein „+“ pro Seite mit Auswahl, nur zeigen was da
ist, Ändern direkt am Ding, Rest im „···“; Schritte 1–7, je Dateien, was Lia sieht, Tests). Wird
schrittweise freigegeben (Jan 10.11.). Zwischenstände darf Lia sehen (Jan 10.11.), also keine Probe-Kopie. Die
Zeilennummern im Befund und Plan gelten für Commit bf2e0d9.
- Schritt 1 gebaut (Jans Okay 10.11., live): Klasse, Reihe, Stunde und Heute haben oben rechts ein „+“
  (`oberflaeche/_plus.html`, Block `plus` in `basis.html`) mit Gespräch, Material …, Stunde bzw. Probe, Reihe, Datei,
  je nach Seite; „Datei“ springt vorerst zum Abschnitt „Deine Dateien“ (richtig in Schritt 4). Weg sind „+ Neu hier“
  (außer Ergebnis), „+ Gespräch“ im Abschnitt, Formular „+ Stunde“, Knopf „+ Reihe“ und „Neuer Auftrag +“. Nur
  Vorlagen und CSS, kein Neustart nötig. Rundgang 10.11. gegen 8791: 162 Seiten ohne Fehler. Nicht im Browser
  angesehen (Menü auf und zu, schmales Fenster).
- Schritt 2 gebaut (Jans Okay 10.11., live, nur Vorlagen und CSS): Leere Abschnitte fallen weg (Gespräche, Zur ganzen
  Reihe, Stunden-Überschrift, Material der Stunde, Reihen der Klasse, auf Heute „Wartet auf dich“, „Läuft gerade“,
  „Weiter im Gespräch“). Ganz leere Ebene: leise Zeile „Noch leer. Mit + fängst du an.“ (`_ort.html` `noch_leer`, im
  Archiv nur „Noch leer.“). „Deine Dateien“ ohne Dateien nur sichtbar, wenn „Datei“ im „+“ dorthin springt
  (`.ablage-zu:not(:target)` in `ruhig.css`) oder Fehler/Meldung da ist. Klasse ohne Stundenplan: nur Link
  „Stundenplan eintragen“. Einzelheiten im Plan. Rundgang 10.11. gegen 8791: 615 Seiten (mit Abfrage-Links, darum
  mehr als bei Schritt 1), alle 200, 14 Seiten mit der leisen Zeile, `lia/instanz` unverändert. Nicht im Browser
  angesehen (Sprung auf `#ablage` per „+“, schmales Fenster).
- Schritt 3 gebaut (Jans Okay 10.11., live, nur Vorlagen und CSS): Klasse, Reihe und Stunde haben neben dem „+“ ein
  „···“ (`_plus.html` `punkte`, Block `punkte` in `basis.html`) mit Bearbeiten, Archivieren, In eine andere Klasse,
  Termine, Reihe beginnt am, Stunde verschieben (Reihe); Thema und Marke, Verschieben, Kopieren, fällt aus, Ausblenden,
  Löschen (Stunde); Bearbeiten, Stundenplan, Zusatztermin (Klasse). Auf den Seiten keine Knopfreihen und Formularzeilen
  mehr. Im Archiv „Wiederherstellen“ am Hinweis. Einzelheiten und Abweichungen im Plan. Rundgang 10.11. gegen 8791:
  615 Seiten, alle 200, `lia/instanz` unverändert. Nicht im Browser angesehen (Menü auf und zu, Formulare im Menü bei
  schmalem Fenster, Ziehen der Stunden mit dem Formular im zugeklappten „···“).
- Schritt 4 gebaut und committet (Jans Okay 10.11.): Titel anklicken und umbenennen (Reihe, Klasse, Stunde, Gespräch;
  `_direkt.html`, `statisch/direkt.js`), Datei auf die Seite ziehen oder „Datei“ im „+“ öffnet die Auswahl, Regeltext
  erst mit gewählter Datei, Stunden per Finger ziehen (`ziehen.js`). Neue Routen `/reihe/<id>/titel`,
  `/klasse/<id>/titel`. Die Vorlagen fragen `titel_aktion` ab, das nur die App ab Schritt 4 liefert (so liefen sie
  schon vor dem Neustart). `webapp.service` am 11.11. 07:43 mit Jans Okay neu gestartet; danach Rundgang 615 Seiten,
  alle 200, Reihe und Klasse tragen das Umbenennen, neue Routen antworten (fremde Herkunft: 403), Log ohne Fehler,
  `lia/instanz` unverändert.
  Browser-Probe 11.11. (Claude im Chrome-Seitenfenster bei Jan, lia.meldro.de, nichts gespeichert, Absenden und
  Schreib-Aufrufe im Browser abgefangen): ok sind Titel der Reihe und der Stunde (Klick, Feld markiert, Esc und
  „Abbrechen“), „+“ und „···“ auf und zu, beide Menüs im Fenster auch bei 401 px, kein waagrechtes Scrollen, Rahmen
  und Hinweis beim Ziehen einer Datei über die Seite, Konsole ohne Fehler. Daraus behoben: „Stunde verschieben“ im
  „···“ der Reihe erst ab zwei Stunden (bei einer bot es nur „vor Stunde 1“).
  OFFEN, nur von Hand: Datei loslassen (Zeile mit Name, Regel, „Ablegen“; der nachgestellte Drop war im Seitenfenster
  gesperrt), „Datei“ im „+“ (öffnet ein Dateifenster), Stunde ziehen mit Maus und am iPad mit Finger (Reihe hatte nur
  eine Stunde), Enter speichert (bewusst nicht auf Lias Daten).
  Befund für später (Schritt 5): Bei ≤ 760 px steht die Seitenleiste unter dem Inhalt. „Stunde verschieben“ ist im
  „···“ ein offenes Formular, kein einzelner Menüpunkt.
  Nächster Schritt danach: 5 (Raster mit rechter Spalte).
Behoben aus „Nebenbei gefunden“:
- „Gespräch gelöscht.“ steht jetzt in `basis.html` und erscheint an Klasse, Reihe, Stunde und ohne Ort
  (`test_gespraech_geloescht_meldung`).
- `logik._regel_zeilen` hängt eingerückte Folgezeilen an die Regel davor (`test_regeln_mit_folgezeilen`). Die
  Theater-STATUS selbst ist noch falsch (Folgezeile hinter der Regel vom 08.11., doppeltes Datum); Ursache in
  `agentkit/regeln.py`, Bedarf Punkt 39 der Haupt-STATUS. Bis dahin hängt „Charaktereigenschaften.“ auf „Ich“ an
  der Regel vom 08.11.
- Test-Instanz 8795 am 10.11. neu aufgebaut (`data/test/aufbauen.py`), darin ein Test-Auftrag „Arbeitsblatt: Probe
  Befund …“ an Stunde 1 von Straftheorien (nachgeklickter Alltagsweg). Instanz danach beendet.

## Umbau „Gespräch in der Mitte“ (Stand 10.11.2026, Plan `bauplan-gespraech.md`, Jans Okay 10.11.)
Gebaut und committet (Bauplan-Schritte 1–6): `gespraech.py` (Markdown mit Überschriften, Tabellen, Bausteinen;
Orte, Kette, darunter; Verlauf), `ablage.py` (eigene Dateien an `lia/instanz/ablage/<ort-id>/`), Routen in `app.py`
(Block „Gespräche und Ablage am Ort“), neue Oberfläche `oberflaeche/` + `statisch/ruhig.css` + `gespraech.js`.
Nur mit `WEBAPP_OBERFLAECHE=neu` (siehe oben); dort ist die Spalte „Fragen“ weg.
- Schnittstelle zu lia/chat geprüft: Claude-Einträge `rolle: "claude"`, nur erfolgreiche; Fehlschläge stehen an
  Lias Eintrag (`stand: "fehler"`), den Satz für Lia holt die App über `antwort_holen` und zeigt ihn unter der
  Nachricht. lia/chat liest die Ablage aus `lia/instanz/ablage/<id>/` (gleicher Pfad wie die App schreibt).
- Nicht gebaut (für Testaufgaben 1–6 nicht nötig, Jan entscheidet): Vorschau-Panel für Material und Ablage (heute
  Link auf Ergebnis/Betrachter bzw. Datei), „Darüber sprechen“ an Material/Ablage, Ebenen-Kopf ruhiger (Pflege-
  Knöpfe ins „···“), roter Punkt im Baum (der Baum hat noch kein Zuklappen). Aufräumen alter Chat-Logik in
  `logik.py` (fragen_spalte, frage_ort …) nur nach Vorschlag an Jan.
Probe 10.11.2026 (Bauplan Schritt 7) mit Jan abgebrochen: Reihenfrage übernehmen, Foto senden und Auftrag ordnen
liefen technisch, aber Jan findet das Gespräch zu starr und überfordernd (Zielbild „wie eine Claude-Code-Sitzung“,
keine weiteren Knöpfe, auch „Als Reihenfrage übernehmen“ zu starr). Zielbild und Befund: Punkt 37 der Haupt-STATUS.
Testgespräche gelöscht. Jan hat am 10.11. trotzdem umgeschaltet (siehe oben): Die alte Oberfläche ist nicht tragbar,
die neue „ansich nicht schlecht“. Weiterbau nach dem Plan aus Punkt 37. Test-Instanz starten: `WEBAPP_INSTANZ=$PWD/data/test/instanz
WEBAPP_NEUER_AUFTRAG=test WEBAPP_CHAT=an WEBAPP_OBERFLAECHE=neu WEBAPP_PORT=8795` (8793/8794 sind uni-Portal und Arbeitsplatz), vorher
`data/test/aufbauen.py`. Achtung: lia/chat liest immer `lia/instanz`; Orte, die nur die Test-Instanz hat (neue
Stunden, „Kant: Vergeltung“, „von Liszt“), kennt Claude nicht.

## Stand (03.11.2026, Struktur pflegen siehe eigener Abschnitt)
Bauschritt 1 und die Ergebnis-/Entwurf-Ansicht (nur lesend) fertig und committet, Aufträge mit Feedback-Schleife
als ein Auftrag mit Verlauf (Jans Anmerkung 30.10.), „Neuer Auftrag“ für Material im Testbetrieb (Jans Okay 30.10.),
Ordnung nach Fach, Klasse und Reihe (Jans Okay 30.10.), Bauschritt 1 des neuen Aufbaus „Desktop zuerst“
(Jans Okay 30.10.), Seitengalerie statt aller Seitenbilder und Material-Ansicht wie Board „Desktop“ (Jans Wunsch 30.10.),
Block A und B aus dem Abgleich mit dem Board (Jans Wahl 30.10.: „Block A, dann B“) und danach „alle Funktionen des
Boards echt“ (Jan 30.10. abends, Plan `board-plan.md`, Abschnitt „Board komplett“ unten), `./pruefen.sh` grün
(Web-App: 129 Tests).
- Rahmen (Plan `../../docs/webapp-aufbau.md` 4.1, Board „Desktop“): drei Spalten Baum (260 px) | Inhalt mit
  Brotkrumen (bis 840 px) | „Fragen“ (320 px, nur Platzhalter „Kommt bald“, kein Chat, kein Claude-Aufruf). Alle
  Seiten (auch 404) über `vorlagen/basis.html`. Im HTML steht der Inhalt vorn. Unter 1100 px rutscht „Fragen“
  unter den Inhalt, unter 640 px alles untereinander: Inhalt, Baum, Fragen (einfacher als der Drilldown aus 4.2,
  die Brotkrumen führen zu „Heute“ zurück).
- Baum (`logik.baum`): oben „Heute“ mit der Zahl, was wartet, dann je Fach (Überschrift) die Klassen/Kurse (Link
  `/klasse/<kennung>`) und deren Reihen (Link `/reihe/<kennung>`, abgeschlossene mit Zusatz), unten „Mehr“ mit
  Vorlagen und Ich. Die gezeigte Seite ist markiert. Stunden stehen nicht im Baum, nur in der Reihe.
- Brotkrumen (`logik.krumen`): Heute; Reihe: Fach › Klasse (Link); Seite in einer Reihe (Ergebnis, Entwurf mit
  Reihe): Fach › Klasse › Reihe (Link) › [Stunde n bzw. Original] › Titel (gekürzt auf 60 Zeichen); sonst Heute ›
  Titel. Rechts daneben „+ Neu hier“ an Reihe, Stunde und Material (nur laufende Reihen, nur wenn Neu eingeschaltet).
- Reihe `/reihe/<kennung>` (`logik.reihe_ansicht`): Fach · Klasse, Reihenfrage, „Schon behandelt“, 01 „Zur ganzen
  Reihe“ (Entwürfe Offen; Material mit Stand `logik.material_marke`: Läuft, Final, Hat nicht geklappt, sonst
  „Fassung n“, in den ersten 48 h „· neu“), 02 Stunden (beim Theater-Agenten „Proben“) mit Nummer, Thema und
  Material, leer mit Hinweis, Formular „+ Stunde“. Varianten stehen nicht einzeln da. Unbekannt: 404.
- Klasse/Kurs `/klasse/<kennung>` (`logik.klasse_ansicht`, nur lesend): Reihen (laufende zuerst) mit Reihenfrage
  bzw. „Reihenfrage noch offen“, Zahl der Sachen, Marke Abgeschlossen; „Zur ganzen Klasse“ leer mit Hinweis
  (Material der Klasse steht in keiner Datei).
- Stunden (`/reihe/<kennung>/stunde/<n>`, Nummer = Platz unter den sichtbaren): nur aus reihen.toml (Strukturplan
  Bauschritt 5; die eigenen Stunden der App in `zustand.py` sind weg, auf dem Server gab es keine, geprüft 03.11.).
  Jede Stunde hat eine feste id aus agentkit. Material hängt an der id (`stunde_von`: `{"stunde": id}`) und folgt
  der Stunde beim Verschieben. „Gehört zu“ schickt noch die Nummer (die App speichert die id). Ein Auftrag aus
  einer Stunde nennt sie im Text („Stunde 3: Thema“) und trägt ihre id im Feld `ort`.
- Neu (`/neu`, Block A4): ohne `?art=` die Galerie (Arbeitsblatt, Präsentation, Tabelle: was unterricht baut),
  mit Art ein kurzes Formular (eigene Frage und Platzhalter je Art), Ort aus `?reihe=…&stunde=n` vorbelegt und
  oben genannt („für Ethik › Klasse 8 › Straftheorien › Stunde 1“), sonst Auswahl der Reihe. Text an den Agenten:
  „Arbeitsblatt: …“ + Reihe + Stunde. Danach zurück an den Ort mit Hinweis. Bei Fehlern ohne Art das Freitext-
  Formular wie bisher. Weiter nur `WEBAPP_NEUER_AUFTRAG=test|echt`.
- Vorlagen (`/vorlagen`) und Ich (`/ich`), Block A5, nur lesend: Gestaltung aus `<agenten>/unterricht/profil.toml`
  (Schrift, Größe, farbige Kästen, Folienschrift), Arten der Galerie, Muster und eigene Formatvorlage als leere
  Zustände. Ich: Regeln aus `<instanz>/regeln.md` („Für alles“) und den „Gelernten Regeln“ der STATUS.md von
  unterricht, theater, examen, recherche („Für Material“ usw.), ohne Feedback-IDs, Datum und Anlass darunter.
- Varianten (Regel R2; Türkisch entfällt, Jan 30.10.): „Auch als“ (einfach, mit Hilfekarten, Level 1–3) im Formular
  Arbeitsblatt und Lernerfolgskontrolle wird die Zeile „Auch als: …“ im Auftragstext; lia/unterricht baut die
  Varianten im selben Lauf als weitere Dateien. Nachträglich: Leiste „Varianten: normal · einfach“ mit
  „+ Variante“ legt einen eigenen Auftrag an unterricht an (Text „Variante „einfach“ von „Titel“: …“, Anhang =
  Kopie der finalen bzw. oberen Datei, nur docx/pptx); die Web-App merkt sich die Zuordnung (`zustand.py`:
  `varianten`), die Variante hat eine eigene Ansicht mit Brotkrume „Original“. Nur test/echt. Noch nie echt.
- „Heute“ in der Mitte, Inhalt wie bisher, jede Zeile mit Reihe nennt ihren Ort („Ethik › Klasse 8 ›
  Straftheorien“). Chips, `?ordnung=`, Seite `/unterricht` und „Unterricht →“ sind weg; `/unterricht` leitet mit
  301 auf `/` um. Aufträge ohne Reihe stehen nur in „Heute“.
- Ergebnis, Entwurf und Neuer Auftrag wie unten, nur im Rahmen; „Zurück“ ersetzt durch die Brotkrumen.
- Echter Lauf 30.10. (Test-Socket, lia/instanz): Baum Heute 5, Ethik › Klasse 8 › Straftheorien (in Planung),
  Darstellendes Spiel › Kurs 12 › Der nackte Wahnsinn; alle Links aus „Heute“ und beide Reihen 200.
- Seite „Heute“, nur lesend, ohne Anmeldung, aus `lia/instanz` über agentkit (`auftraege.neue/erledigte`,
  `freigabe.offene`, je mit `basis=`). Die App selbst läuft ohne `AGENTKIT_INSTANZ`.
- Abschnitte: 01 Wartet auf dich (offene Entwürfe, Ergebnisse der letzten 48 h als „Neu“), 02 Läuft gerade,
  03 Fertig (höchstens 10), 04 Hat nicht geklappt (mit dem Grund des Agenten). Leere Abschnitte 03/04 fehlen.
- Ein Auftrag mit Feedback-Schleife ist EIN Auftrag (`logik.ketten`): Ursprung, Lias Rückmeldungen (Agent feedback)
  und Nachbesserungen hängen über `bezug` zusammen, auch Nachbesserungen von Nachbesserungen. „Heute“ zeigt je
  Kette eine Zeile mit Titel und Link des Ursprungs; Zeit, „Neu“ und Abschnitt nach der jüngsten Fassung, Hinweis
  „nach deiner Rückmeldung“. Läuft etwas in der Kette (Nachbesserung oder Rückmeldung), steht sie nur unter
  „Läuft gerade“ („Arbeitet an deiner Rückmeldung“, mit Link auf das bisherige Ergebnis).
- Echter Lauf 30.10. über einen Test-Socket: Theater-Fassung 0baec0 mit Lias Frage und Antwort 5d88d5 als eine
  Zeile; alle 7 Links aus „Heute“ 200, 5d88d5 und 1c1e7e leiten auf 0baec0 um.
- Begriffe aus Lias Sicht: Art aus quelle bzw. Agent (Material, Frage, Woche, Theater, Recherche, Examen), IDs und
  „Runde runde-…“ werden aus Titeln entfernt (Test prüft, dass keine ID und kein Agentenname im HTML steht).
- Zeiten in Europe/Berlin (Sommerzeit beachtet). htmx lädt den Inhalt jede Minute neu (`/teile/heute`).
- Kopfzeilen: CSP nur `'self'`, `no-store`, `nosniff`, kein Referrer; keine API-Doku (`/docs` 404).
- Zeilen in „Heute“ sind Links (außer „Läuft gerade“). IDs stehen nur in der URL, nie im sichtbaren Text.
- Material-Ansicht (Jan 30.10.: „genau so wie das Board ausprobieren“, Board „Desktop“, Ansicht Material) auf
  `/ergebnis/<id>`: Kopf mit Art und Dateiart („Material · Word“, „Theater · 4 Word-Dateien“), Titel, Marke
  (Final, Läuft, Neu · wartet). Links bei genau einer Datei mit Seitenbildern die ersten zwei Seiten (Klick öffnet
  den Betrachter), sonst die Karten bzw. der Text; rechts die Knopf-Spalte: In Word/PowerPoint/Excel öffnen und
  PDF zum Drucken (nur bei einer Datei), Als final markieren, Rückmeldung geben, Eigene Fassung hochladen. Darunter
  „Das Wichtigste“ und „Fassungen“ (neueste oben: Name, „vom Assistenten/von dir, Zeit“, Kurztext, Marke Final,
  ältere zum Aufklappen, kleiner Knopf „Als final markieren“ an jeder Fassung mit Dateien und an eigenen).
  Ohne JavaScript: Rückmeldung und eigene Fassung öffnen sich über `?offen=rueckmeldung|eigene`, nach einer
  Aktion 303 auf `?erledigt=…` mit Hinweis oben. Varianten siehe oben.
  - Als final markieren (`POST …/final`, nur Fassungen aus `logik.final_erlaubt`, je Auftrag höchstens eine) und
    Eigene Fassung hochladen (`POST …/eigene`, Word/PowerPoint/Excel/PDF bis 20 MB, Download `…/eigene/<n>`)
    speichert seit 30.10. abends `agentkit.fassungen` (`<instanz>/fassungen/<ursprung>.json`, Datei im
    Agent-Ordner unter `data/eingang/<ursprung>/eigene-<n>/`; Jans Entscheidung: die Agenten sehen es). Das
    schreibt also auch in lia/instanz und startet keinen Lauf; darum geht es immer. `zustand.py` liest es zum
    Anzeigen mit. Final nimmt den Auftrag aus „Wartet auf dich“, unter Fertig steht „Final“.
    Der große Knopf gilt der neuesten Fassung, auch Lias eigener (`aktuell_ref`), und nennt sie, sobald es mehr als
    eine zur Wahl gibt („Fassung 2 als final markieren“); die Bestätigung nennt die Fassung. Oben steht dann weiter die
    Fassung des Assistenten („steht oben“ stimmt also), der Hinweis `oben_hinweis` sagt das und wo Lias Datei ist.
  - Rückmeldung geben (`POST …/rueckmeldung`): Text oder Datei, eine Datei allein reicht (dann Auftragstext
    `logik.RUECK_NUR_DATEI`, derselbe Wunsch wie Lias Satz vom 01.11.). Unter den zwei Knöpfen je ein Satz, was danach passiert. Über
    `agentkit.fassungen.rueckmeldung`: die Datei kommt mit ihrer Art in die Kette (fassung, anmerkungen, unklar),
    dann ein Auftrag an `feedback` (bezug = neueste fertige Fassung bzw. die Fassung der Datei, siehe „Rückmeldung
    je Datei“); der Feedback-Dienst richtet Zuordnung und Auftrag nach der Art aus und hängt die Datei an die
    Nachbesserung. Im Verlauf: Fassung n, „Deine Anmerkungen“ bzw. „Deine Datei“ (ohne Nummer, nicht final
    markierbar). Eine Fassung lädt Lia sonst über „Eigene Fassung“ hoch. Nur mit `WEBAPP_NEUER_AUFTRAG` test bzw. echt
    (startet lia-feedback.service). Sonst „Rückmeldungen gehen im Moment noch über Telegram“.
  - Doppelklick bei Rückmeldung, Neu, Variante, Eigene Fassung und Ausfall: Der Knopf sperrt sich nach dem Absenden
    (`statisch/einmal.js`, Formular mit `data-einmal`), dazu der Server (zweite Anfrage: gleiche Bestätigung, kein
    zweiter Lauf). Rückmeldung, Neu, Variante: `logik.auftrag_doppelt`, 30 s, gleicher Text, Bezug, Ort, Dateinamen;
    fehlgeschlagene und zurückgezogene zählen nicht. Gleicher Text mit anderer Datei gleichen Namens gilt in den 30 s
    auch als doppelt, zwei gleichnamige Dateien in einem Auftrag erkennt der Server nicht. Eigene Fassung:
    `logik.eigene_doppelt` und Vergleich des Inhalts, geänderte Datei bleibt eine neue Fassung. Ausfall: Termin fällt
    schon aus, dann dieselbe Seite wie nach der ersten Anfrage (`_ausfall_schon_da`).
    „+ Stunde“, „+ Reihe“, „+ Fach“, „Nochmal“: Knopfsperre und Formular-Kennung (Feld `einmal`, je geladene Seite neu,
    `app.einmal`): gleiche Kennung bekommt dieselbe Weiterleitung, auch während die erste Anfrage noch läuft; mehrere
    leere Stunden nacheinander bleiben möglich. Die App merkt sich die letzten 200 Kennungen im Speicher, ein Neustart
    leert sie; scheitert die erste Anfrage, zählt die Kennung nicht.
  - Alle POSTs mit Herkunftsprüfung und Token (`app.formular_lesen`), Aktionen nur an der ID des Ursprungs.
  - Echter Lauf 30.10. (nur lesend): alle 5 Ergebnisse 200, nichts gespeichert.
- Ergebnis `/ergebnis/<id>` (nur abgeschlossene Aufträge der Instanz, ID per pruefe_id, zurückgezogene 404; IDs
  von Nachbesserungen und Rückmeldungen leiten mit 303 auf den Ursprung um): Titel, Art und Zeit der neuesten
  Fassung; „Das Wichtigste“ aus `daten.kern`/`punkte`/`pruefen` der neuesten erledigten Fassung, ohne
  `daten` der ganze Ergebnistext (Zeilen mit „- “ als Liste); „Dateien“: je Datei eine Zeile mit Knöpfen PDF (aus
  der Vorschau) und Original (Word/Excel/PowerPoint/PDF); hat sie Seitenbilder (`<stem>-vorschau/<stem>-seite-NN.png`),
  ist sie eine Karte mit der ersten Seite klein, Name und „n Seiten · ansehen“ (auch an früheren Fassungen im Verlauf).
  Dateien aus der jüngsten Fassung mit Dateien („Aus Fassung 1“, wenn die Antwort keine hat).
- Seiten-Betrachter `/ergebnis/<id>/datei/<n>/ansehen?seite=m` (`logik.betrachter`, ohne JavaScript; `<id>` ist die
  Fassung, aus der die Datei stammt): eine Seite groß (passt ins Fenster), „‹ Vorige“/„Nächste ›“, Seitenzahlen als
  Links ab 3 Seiten, Tipp aufs Bild = nächste Seite (letzte: Bild in voller Größe), PDF, Original, „Zurück zum
  Ergebnis“; Brotkrumen bis zum Ergebnis; Untertitel „Fassung n · Seite m von k“ (Fassung nur, wenn es mehrere
  gibt). Falsche Seite, Datei ohne Seitenbilder, unerlaubte Pfade: 404. Echter Lauf 30.10.: Theater 4 Karten oben
  und 4 im Verlauf, alle Betrachter 200, Seite 99 404.
  Darunter „Verlauf“: Fassung 1, Deine Rückmeldung (Lias Text), Antwort bzw. Fassung n (n zählt nur Fassungen mit
  Dateien), je mit Zeit; frühere Fassungen aufklappbar (`<details>`, Kern, Punkte, Dateien), die oberste „steht
  oben“. Rückmeldung ohne Nachbesserung zeigt die Antwort des Feedback-Agenten. Läuft eine Nachbesserung: Hinweis
  oben; ist die letzte fehlgeschlagen: Hinweis und oben die Fassung davor. Alles fehlgeschlagen: „Hat nicht
  geklappt“ mit Grund. Downloads tragen die ID der Fassung, aus der die Datei stammt.
- Entwurf `/entwurf/<id>` (nur `freigabe.offene` der Instanz): ganzer Text ohne Kürzung, Details nur aus
  `logik.ENTWURF_DETAILS` (bisher „Einsatz“; `daten.datei` ist ein interner Pfad und bleibt verborgen),
  Hinweis „Setzt du selbst ein“. Keine Knöpfe.
- Echter Lauf 30.10.: alle 7 Links aus „Heute“ liefern 200 (5 Ergebnisse, 1 Fehlschlag, examen-0c44bf),
  Downloads und Seitenbilder kommen, falsche Nummern und Pfade 404. Das Dossier der Recherche (PDF) hat keine
  Vorschau (der Renderer hat dafür keine `-vorschau/` angelegt), dort nur der Download.

- Neuer Auftrag `/neu` (Board ModNeu, nur Material: `unterricht`, quelle `portal-material`), standardmäßig AUS.
  `WEBAPP_NEUER_AUFTRAG=test` gilt nur, wenn `WEBAPP_INSTANZ` nicht `lia/instanz` ist; kein Agent startet.
  `=echt`: jede Instanz, danach `systemctl --user start --no-block lia-unterricht.service`; das Ergebnis stellt
  Lias Zentrale auch per Telegram zu, Kosten auf Lias Kontingent. Ist es an, steht oben in „Heute“ der Knopf
  „Neuer Auftrag“, nach dem Abschicken (303 auf `/?abgeschickt=1`) der Hinweis „Dein Auftrag ist unterwegs“.
  Formular ohne JavaScript: Text (Pflicht, bis 5000 Zeichen), Dateien (bis 10, je bis 20 MB, PDF/Word/PowerPoint/
  Excel/JPG/PNG, Namen bereinigt), Hinweis „Bitte keine Namen“; Fehler zeigt das Formular mit Text wieder (400).
  Anlegen über `agentkit.auftraege.neuer_auftrag(..., basis=, agenten_dir=<instanz>/.., absender=PERSON)`;
  Uploads liegen kurz in `data/eingang/` und werden von agentkit nach `<agent>/data/eingang/<id>/` verschoben.
  Schutz ohne Konten: Origin muss zum Host passen (Sec-Fetch-Site same-origin), sonst 403 (dafür
  `Referrer-Policy: same-origin`, mit `no-referrer` schicken Browser `Origin: null`; Abschicken aus einem echten
  Browser nach dem Fix vom 01.11. noch nicht bestätigt); Token im Formular
  (HMAC, geheim je Start der App), nach einem Neustart „Die Seite war veraltet“. Ohne Zurücknehmen,
  ohne „Das beachte ich“, keine Auswahl der Art (gibt es noch nicht).
- Ordnung nach Fach, Klasse und Reihe (Jans Wunsch und Okay 30.10.; Strukturplan Bauschritt 2 erledigt 03.11.):
  - `ordnung.laden` liest `<instanz>/reihen.toml` nur über `agentkit.struktur.laden()` (altes und neues Format)
    und gibt (Reihen, Gruppen, Fehler) zurück; `logik.reihen_aus(s)` macht daraus Reihen und Klassen/Kurse der
    App. Gruppen sind die Klassen, im neuen Format auch ohne Reihe (Baum, Fach- und Klassen-Ansicht zeigen sie;
    nach der Migration steht Kurs 11 ohne Platzhalter-Reihe da). Archiv: im alten Format bleibt die Regel der App
    (schuljahr + abgeschlossen, Klassen-Kennung mit Jahr wie bisher, z. B. `/klasse/darstellendes-spiel-kurs-11`
    statt der struktur-id `…-klasse`), im neuen gilt `im_archiv`. Eine einzeln archivierte Reihe einer laufenden
    Klasse steht nur in der Klassen-Ansicht (Marke „Archiv“). Stand `geplant` gilt als laufend und steht im Baum
    als „(in Planung)“, in der Reihe als „· in Planung“. Kaputte Datei: ganze Datei verworfen (wie unterricht),
    Fehler im Log (nur bei Änderung), App zeigt ohne Reihen. Den Ersatzweg aus den Agent-Ordnern gibt es nicht mehr.
  - Test: `tests/test_ordnung.py` vergleicht Baum, Brotkrumen, Klassen-, Fach- und Reihen-Ansicht für die
    eingefrorene Kopie der echten Datei (`tests/daten/reihen_alt.toml`) mit dem Bild vor der Umstellung
    (`tests/daten/ansicht_vorher.json`), dazu `reihen_neu.toml` (dieselbe Datei im neuen Format) und die
    Testregeln 7, 22 (lesend) und 23 (`test_app.py`).
  - Zuordnung (`logik.reihe_von`): Feld `reihe` des Auftrags, sonst der Agent, wenn er in genau einer Reihe unter
    `agenten` steht. Nichts aus dem Text geraten, sonst „ohne Reihe“. Bei Ketten zählt der Ursprung.
    Echte Daten 30.10.: Theater-Fassung 0baec0 -> Der nackte Wahnsinn; Entwurf examen-0c44bf -> Ethik 8 Straftheorien;
    alle Material-Aufträge, Recherche und der Fehlschlag ohne Reihe.
  - Neuer Auftrag: Auswahl „Für welche Reihe?“ (laufende Reihen, Standard keine). Der Auftrag trägt `reihe`
    (für ältere Leser), `ort` (Stunden-id, sonst Reihen-id; agentkit.struktur) und am Textende „Reihe: Titel
    (Fach, Klasse)“ für den Agenten. Variante trägt `ort` = Reihe, Nochmal übernimmt `ort` des Ursprungs. Die
    Frage an den Chat behält ihren Ort (`{"reihe", "stunde": n, "stunde_thema", …}`), aus einer Stunde
    zusätzlich `stunde_id` (lia/chat liest dann Nummer und Thema aus reihen.toml).
- Test-Instanz für Jan: `data/test/instanz` (`.env` mit PERSON=Lia, 0600) und Agent-Ordner `data/test/unterricht`,
  nicht im Repo. Probelauf 30.10.: Auftrag mit PDF angelegt, Datei verschoben, ohne Origin 403; danach gelöscht.

## Struktur pflegen (Strukturplan Bauschritt 5, gebaut 03.11.2026, Commit 764fdcd, noch nicht abgenommen)
Plan `../../docs/struktur-pflege-plan.md` (2a, 4, 5, 6, 10). Lia pflegt Fach → Klasse/Kurs → Reihe → Stunde mit
Terminen in der App. Geschrieben wird nur über `agentkit.strukturpflege` (`app.pflegen`, im Faden über
`run_in_threadpool`, weil der Commit auf commit.sperre wartet); die App schreibt nie selbst in reihen.toml.
Masken nur im neuen Format (sonst 404, Baum ohne „+ …“).
- Code: `pflege.py` (reine Logik: Formularwerte, Stundenplan-Zeilen, Termine-Liste, Texte für Lia, getestet in
  `tests/test_pflege.py`), Routen im Block „Struktur pflegen“ in `app.py` (Liste im Kopf von app.py), Vorlagen
  `pflege_*.html`, `_pflege.html` (Bausteine), `rueckfrage.html`, `meldung.html`, `statisch/ziehen.js`.
- Baum: „+ Fach“, „+ Klasse oder Kurs“ je Fach, „+ Reihe“ in der Klasse, in der man ist (nicht im Archiv). Fach
  ohne Klasse steht jetzt im Baum (`logik.faecher_aus`).
- Schule: Bundesland fragt „Neue Klasse“ einmal (nur nötig mit Stundenplan), ändern unter „Ich“.
- Klasse: anlegen mit Stundenplan in derselben Maske (Zeilen Wochentag, Stunde, Einzel/Doppel, „+ weiterer
  Termin“ ohne JavaScript; ab/bis leer = ganzes Schuljahr aus den Ferien; meine Entscheidung zur Vorbelegung, Plan
  ließ sie offen: Schuljahresende statt Halbjahresende, damit „ab Februar“ ohne Fehler geht). Bearbeiten (Name,
  Schuljahr), Lerngruppe mit festem Hinweis aus Abschnitt 6 (eigenes Formular, nie im Log), Stundenplan (ganz oder ab
  Stichtag, vorbelegt Beginn der Winterferien), Ins nächste Schuljahr übernehmen (Lerngruppe nur mit Häkchen),
  in anderes Fach. Ansicht: Termine (kommende, vergangene eingeklappt) mit „fällt aus“ (Maske: Alles rückt nach /
  Diese Stunde fällt weg; freier Termin: nur streichen), „findet doch statt“, Zusatztermin.
- Reihe: anlegen mit Titel; freiwillig „ab …, n Termine“, einzelne Häkchen oder Stunden ohne Termin. Bearbeiten
  (Titel, Reihenfrage, Stand, Notizen, Behandelt, Merksätze; nur geänderte Felder gehen mit `gesehen` an agentkit,
  Jans Änderungen an anderen Feldern bleiben). In der Ansicht: Archivieren (ohne Rückfrage), Wiederherstellen,
  „In eine andere Klasse übernehmen“ (kopieren, zwei Schritte: Klasse, dann Termine), „Die Reihe beginnt am …“,
  „Termine“ (zuteilen, abgeben), in andere Klasse verschieben (Bearbeiten).
- Stunde: „+ Stunde“ (Thema darf offen bleiben, „Thema offen“), Thema und Marke, „Verschieben nach …“ (ein Formular:
  vor Stunde n / ans Ende / auf einen Termin / in eine andere Reihe; in der Reihe auch per Ziehen, das Skript füllt
  dasselbe Formular), Kopieren, Ausblenden („Ausgeblendete Stunden“ mit Material und Wiederherstellen), Löschen nur
  ohne Haken (sonst „Löschen geht nicht, daran hängt: …“).
- Rückfragen nur bei belegtem Ziel („Dahinter alles nachrücken“ / „Tauschen“) und beim Archivieren bzw. Löschen von
  Klasse oder Fach (nennt Klassen und Reihen). Nach jeder Aktion „<Text> · Rückgängig“ (`?aktion=<id>`, Hinweise von
  agentkit nur im Speicher), „Letzte Änderungen“ (20) unter „Ich“ mit Rückgängig.
- Schutz: alle POSTs mit Origin-Prüfung und Token (`pflege_formular`, bis 300 Felder). Tests: `tests/test_pflege_app.py`
  über den Socket für jede Maske, Testregeln 24, 25, 32–35, 21 (Lerngruppe nicht im Log), Wiederherstellungsprobe,
  Lia-Test-Aufgaben 1–6; Grundlage `tests/daten/reihen_echt.toml` (Kopie der echten Datei), Ferien aus
  `agentkit/ferien.json`. ALLES GRÜN steht im Commit.
- Testinstanz für Abnahme und Lia-Test (Plan 12/13): `data/test/instanz` (nicht im Repo), Kopie der echten
  reihen.toml ohne Bundesland, die ersten Stunden von Straftheorien heißen Einstieg, Kant: Vergeltung, von Liszt (über
  strukturpflege; vorhandene Stunden der Kopie werden umbenannt, Stunde 2 ist immer Kant). Testdaten ohne Dateien und
  ohne echte Inhalte: Reihenentwurf an der Reihe (Testbogen 1), Präsentation und Arbeitsblatt an Stunde 2 (Testbogen
  3 und 6), Theater-Ergebnis an Der nackte Wahnsinn. Neu aufbauen vor jedem Durchgang:
  `.venv/bin/python data/test/aufbauen.py` (löscht auch Zustand, Aktionsablage und Uploads, legt
  `data/test/unterricht` und `data/test/theater` frisch an, „Letzte Änderungen“ beginnt leer). Testbogen
  `data/ia/testbogen.csv` und `data/ia/testbogen-struktur.csv`. Startbefehl für Jan (Port 8792, Tunnel) in der
  Haupt-STATUS Punkt 24. `aufbauen.py` liegt unter `data/` und ist damit nicht versioniert: keine Sicherung, kein Test
  in `pruefen.sh`.
- Aufgabe 4 (Chat) ist aus `data/ia/testbogen.csv` gestrichen (Jan 04.11.), die übrigen behalten ihre Nummern (1-3,
  5-7). In der Testinstanz ginge sie nicht: Sie läuft ohne `WEBAPP_CHAT=an`, darum „Kommt bald“. Der Schalter allein
  reicht nicht, `CHAT_ORDNER` ist fest `lia/chat/data`: Die Testinstanz zeigte Lias echten Chat-Verlauf, und jede Frage
  startete den echten Agenten auf Lias Kontingent.
- Durchgespielt 03.11. über einen Test-Socket mit curl: Lia-Test-Aufgaben 1–6 gehen (Bundesland wird gefragt, erster
  Termin der 9 nach den Winterferien, Kopie mit sechs Terminen, Material wandert mit Kant auf Stunde 3, Ausfall rückt
  nach, Archiv und Zurückholen byte-gleich), alle sieben Aktionen per Rückgängig zurück, Log ohne Fehler.
- Offen: einmal im Browser durchklicken (Chrome, auch Ziehen); webapp.service neu starten nur mit Jans Okay
  (`systemctl --user restart webapp.service`).
- Commits von reihen.toml macht agentkit im Hintergrund (Speichern wartet nicht); die App stößt beim Start
  liegengebliebene an (`app.beim_start` über lifespan).

## Neuer Aufbau „Desktop zuerst“ (Plan 30.10.2026)
Plan `../../docs/webapp-aufbau.md` (Abschnitt 5: Bauschritte), Boards „Desktop“ und „Handy-Prüfung“ im Canvas.
Lias Test 30.10. (Jan): gefällt, Ebene Stunde gewünscht. Geklärt (Jan 30.10.): Fach „Darstellendes Spiel“, das
Stück gehört zu Kurs 12, Kurs 11 mit Kompositionsmethoden (laut Plan 4 ein echter Ort)
steht in keiner Datei und fehlt daher im Baum, Notentabelle gehört zu Ethik 8,
Lia nutzt Word, Pages/Keynote und eine Schulplattform: Ausgabe bleibt docx/pptx und PDF.
- Bauschritte 1 bis 4 gebaut (Stunden ohne Datei der Agenten, in data/), dazu final, eigene Fassung,
  Rückmeldung (Testbetrieb) ohne Konten. Fehlt: Fach-Ansicht, Konten (5), Chat-Spalte (6, braucht Chat-Agent).
- Die Reihen-Auswahl im Formular bleibt nur für „Neu“ ohne Ort (aus „Heute“). Die Art „Theater“ (Agent theater)
  heißt in den Zeilen noch so; im Board „Spielfassung“.

## Board komplett (Jan 30.10.2026 abends, Plan `board-plan.md`)
Jans Auftrag: „alle Funktionen aus dem Board zum Laufen bekommen“, je Ordner ein Chat (lia/unterricht, lia/theater,
lia/chat neu, Hauptordner/agentkit). In der Web-App gebaut, je mit Tests:
- Reihen aus `lia/instanz/reihen.toml` (eine Datei für App und Agenten) mit `schuljahr`: abgeschlossene Reihen
  eines Schuljahrs sind Archiv („Archiv: Klasse 7 · 2025/26“, im Baum eingeklappt, eigene Klassen-Kennung mit
  Jahr). Stunden aus reihen.toml gewinnen gegen die Stunden der Web-App; dann kein „+ Stunde“ und kein „Thema
  ändern“ (die Datei pflegt Jan; Masken in Bauschritt 5).
- Fach-Ansicht `/fach/<kennung>` (Klassen mit laufenden Reihen, „Zum ganzen Fach“ leer), Fach in Baum und
  Brotkrumen verlinkt; die gezeigte Reihe klappt im Baum ihre Stunden aus.
- Rückmeldung je Datei: Knopf „Rückmeldung“ an jeder Datei-Karte, „Rückmeldung zu dieser Seite“ im Betrachter;
  Text beginnt „Zur Datei „Name.docx“, Seite n:“, bezug = die Fassung, aus der die Datei stammt.
- Entwurf (Typ entwurf): „Setze ich selbst ein“ / „Brauche ich nicht“ / Rückgängig, gespeichert in `zustand.py`
  (`entwuerfe`), nicht in der Freigabe (Jans Freigabe bleibt unberührt, examen liest Entscheidungen nicht).
  Entschiedene warten nicht mehr in „Heute“. Ändern eines Entwurfs geht weiter über Jan.
- „Nochmal“ bei Fehlschlag (nur Material ohne Anhänge, nur test/echt): neuer Auftrag mit Text, quelle, bezug,
  sitzung des letzten Versuchs; ein ersetzter Ursprung verschwindet aus „Hat nicht geklappt“ (`ersetzt`).
- „Zurückziehen“ unter „Läuft gerade“ (`agentkit.auftraege.zurueckziehen`, ein laufender claude-Lauf endet). Zwei
  Schritte ohne JavaScript (`<details>`): Erst „Ja, zurückziehen“ schickt ab, „Nein“ lädt neu; das Neuladen von „Heute“ schließt die Rückfrage.
- Galerie: dazu Reihenentwurf und Lernerfolgskontrolle (nur Ethik, unterricht), Spielfassung (Kürzung) und
  Szenenaufgabe (nur Darstellendes Spiel, Agent theater, quelle portal-theater, weitere Felder Länge,
  Spieler*innen, Was bleiben muss bzw. Methode, Szene, Material). Spielfassung = ganze Runde, bis 3 Stunden,
  etwa 7 USD, nur „Der nackte Wahnsinn“.
- Spalte „Fragen“ an den Chat-Agenten `lia/chat` (Schnittstelle `schnittstelle.py`, Warteschlange in
  lia/chat/data): nur mit `WEBAPP_CHAT=an` (jede Frage läuft über Lias Kontingent, ca. 0,03 USD). „Ich weiß:
  Ort“ (Reihe, auf Stundenseiten mit Stunde), „ohne Ort fragen“, „gründlich“, Antwort per htmx alle 2 s
  (`/teile/frage/<id>`), die letzten 6 Fragen mit Trennlinie bei Ortswechsel, Markdown fett, Listen und Links,
  „Daraus Auftrag machen“ öffnet Neu mit Frage und Antwort am Ort.
  Ausbau lia/chat (Punkt 24 der Haupt-STATUS, 03.11.): Häkchen „Im Netz nachsehen“ (`netz=True`, Hinweis: Text
  der Frage geht als Suchanfrage hinaus, keine Namen); Datei-Feld bis 3 Dateien .pdf/.docx/.pptx je 20 MB, vorab
  geprüft (`logik.frage_dateien_pruefen`, Sätze in `FRAGE_FEHLER`), Upload in data/eingang, die Schnittstelle
  verschiebt sie, Rest (auch bei FrageFehler) löscht die App; FrageFehler-Sätze werden auf Schlüssel abgebildet
  (`logik.frage_fehler_schluessel`), die URL trägt nie Text des Agenten. Mehr als 10 Dateien: Formular nicht
  gelesen (400). Im Verlauf „mit Datei: Name“ aus `dateien`, `dateitext` nie. Links `[Titel](URL)` nur
  http/https mit Host (`logik.link_ziel`), `rel="noopener noreferrer"`, `target="_blank"`, sonst bleibt der
  Markdown-Text stehen. Echter Lauf 03.11. über einen Test-Socket (neuer Code, echte Warteschlange): Frage mit
  Häkchen und Word-Datei, Antwort mit Inhalt der Datei und zwei klickbaren Quellen, Datei danach gelöscht;
  Testeintrag aus lia/chat/data/verlauf.jsonl wieder entfernt.
- Formatvorlagen (Jan 30.10.): Seite Vorlagen › „Deine Formatvorlagen“: Upload .dotx/.docx/.potx/.pptx (bis
  20 MB) nach `lia/unterricht/data/vorlagen/` bzw. `…/reihenentwurf/`, `…/lernerfolgskontrolle/` („Gilt für“),
  Name bereinigt, gleicher Name ersetzt; Liste mit „gilt“ (neueste je Geltung und Sorte, wie
  formatvorlage.waehlen) bzw. „nicht genutzt“; Entfernen nur für gelistete Dateien (samt umgewandelter Kopie).
  Startet keinen Lauf, geht darum immer. Den Kopf mit Name/Datum setzt der Renderer weiter selbst (Bedarf
  shared/renderer in Punkt 24).
- Chrome-Test 31.10. (Befunde aus dem lesenden Durchlauf von lia.meldro.de, Jans Okay zur Reihenfolge):
  Fehlschlag in Lias Worten (`logik.grund`: „Rechenzeit“ statt Kontingent, abgelaufene Wartezeit entfällt) und
  bei Fehlschlag mit Datei, wo „Nochmal“ nicht geht, ein Weg über „Neu“ (`logik.nochmal_weg`); „Gehört zu Reihe“
  an Material ohne eigene Reihe (`zustand.py` reihe_von, `logik.mit_zuordnung` beim Laden aller Aufträge,
  POST `/ergebnis/<id>/reihe`); interne Dateinamen (`*.toml`, `*.md` …) fallen aus Lias Texten
  (`logik.ohne_dateinamen` in ohne_ids); „Reihenfrage noch offen“ in der Reihe, Reihe ohne Titel heißt „Noch
  ohne Titel“; Titel von Lias Material aus dem Dateinamen des Ergebnisses (ab zwei Wörtern), ihr Wunsch darunter;
  Neu mit Stunden-Auswahl bzw. Hinweis „gilt für die ganze Reihe“, unbekannte Stunde aus der URL wird gesagt;
  Galerie ohne den veralteten Satz zu Reihenentwurf/LEK; Baum markiert „Heute“ als Ort (aria-current=location)
  bei Seiten ohne Reihe; „Als final markieren“ abgesetzt am Ende der Knöpfe (rückgängig machbar, keine Rückfrage);
  Entwurf-Hinweis „Du entscheidest, ob du ihn einsetzt“; sichtbarer Fokus (`:focus-visible`). Bewusst gelassen:
  Inhalt steht im HTML vor dem Baum (schmales Fenster), die Tab-Reihenfolge bleibt darum Inhalt, Baum, Fragen.
  Tests der App laufen mit fester Zeit (30.10. abends), sonst hingen „heute 14:16“ vom Testtag ab.
  Offen: Begriffe (Level, Hilfekarten, „Varianten: normal“, „wartet“, Entwurf in drei Bedeutungen) warten auf Jan;
  Dienst nach diesen Commits noch nicht neu gestartet (Jan fragen).
Nicht gebaut: „+ Reihe“ in der App (schreibt reihen.toml; Jan bzw. unterricht-Chat), Fach-Material und Lias
Ablage (Jan fragen), Datei in eine Stunde ziehen (JavaScript), Muster, Konten.

## Gestaltung (Jans Wahl 04.11.2026: Feinschliff, Modernist und drei Spalten bleiben)
Gebaut 04.11. aus dem Befund: Punkte 2, 5, 7, dazu:
- Rot (`--akzent`) heißt nur „wartet auf dich“ oder „hat nicht geklappt“; ein Test hält die Liste der roten Stellen fest.
- Knöpfe: eine Grundform `.knopf`, dazu `-voll` (Hauptknopf), `-klein`, `-spalte`, `-leise` („fällt aus“). Auf der
  Material-Ansicht ist „Rückmeldung geben“ der schwarze Knopf, ist etwas offen der offene Weg, bei final keiner.
- Schriftgrößen: nur 12, 14, 16, 18, 22, 40, 64 (Test). Schrift Inter und Inter Tight in `statisch/schrift/` (von
  jsdelivr und unpkg, byte-gleich, Prüfsummen, Lizenz OFL), nur Lateinisch, darf 30 Tage im Browser bleiben.
- Hinweis mit Rückgängig (`.aktion-hinweis`) bleibt beim Scrollen oben kleben, der Sprung auf `#stunden`/`#termine` endet darunter.
- Wörter: Sätze sagen „ich“, „Deine Assistenz“ bleibt nur als Name oben links (Test); keine Agenten- und Ordnernamen
  mehr bei „daran hängt“; nach dem Rückgängigmachen „Zurückgenommen: …“.
- Bewusst nicht geändert: „Auftrag“ (Glossar sagt „Anfrage/Wunsch“, Jan entscheidet) und „Sag Jan bitte Bescheid“ bei
  Störungen (Sprachregel, Entscheidung 4 vom 27.10.: bleibt, wo Jan keine Meldung bekommt), obwohl Jan am 04.11.
  „kein sag Jan Bescheid“ mitgewählt hat; das hat er noch nicht entschieden. Punkte 4, 6, 9, 10 warten auf den Lia-Test.
- Achtung beim Bauen: Vorlagen und CSS wirken sofort auf den laufenden Dienst, Python erst nach dem Neustart. Vorlagen
  dürfen darum keinen neuen Filter und keine Pflichtwerte aus Python brauchen. Am 04.11. antwortete `webapp.service` so
  rund 14 Minuten mit 500 (etwa 09:01 bis 09:15, im Log nur meine eigene Abfrage). `./pruefen.sh` merkt das nicht.

## Skizze „Gespräch in der Mitte“ (Plan `../../docs/gespraech-plan.md` 4.1, Stand 11.11.2026 nachts, nicht mit Lia gesehen)
Klick-Attrappe ohne Claude-Lauf, Code der Web-App und webapp.service unberührt:
https://claude.ai/artifact/FcDwRi58HWDJX2TkVu2BEC (privat; Jan muss sie über „Teilen“ für Lia freigeben oder
auf seinem Rechner zeigen). Quelle `skizzen/gespraech.html`, neu veröffentlichen aus diesem Ordner. Prüfen:
`node skizzen/probelauf.js` (ohne Browser und ohne Pakete: jede Ansicht, Testaufgaben 1–6, Seitenleiste,
Vorschau jedes Materials, Rot nur bei „wartet“, Dichte je Ansicht).
- Eigenes Artifact statt Board im Canvas F8ysVSyr8TjGhFDcyNnejU (Gespräch mit Senden, Fotos, Kopieren und
  Überlagerungen geht als normale Seite einfacher). Das Board „Desktop“ bleibt als Stand vom 30.10.
- Struktur (Jan 09.11.): nur Variante A. Jedes Gespräch und jedes Material hängt an genau einer Ebene: Klasse/Kurs,
  Reihe, Stunde (oder „ohne Ort“), mit „hier“ und „darunter“.
- Oberfläche (Jan 10.11.: zu dicht, Modernist zu laut, Dokumente immer als Vorschau; Plan `ui-plan-notion.md`,
  über Nacht umgesetzt in 8 Schritten, Commits „Skizze UI Schritt 0–7“). Ruhig nach dem Vorbild Notion bei Dichte
  und Schrift, ohne dessen Marke: nur Inter 400–600, Größen 12/14/16/20/32 (schmal 26), 1-px-Linien, graue Flächen,
  gedecktes Blau nur für Hauptknopf und Fokus, Rot nur „wartet“ (Punkt plus Wort). Gilt nur für die Skizze; die
  echte Web-App bleibt Modernist, Entscheidung nach Lias Test (Jan 10.11.).
  - Seitenleiste: Auswahl grau, Zahlen nur beim Hover, roter Punkt bei „wartet“ (auch an zugeklappten Eltern),
    Pfeile zum Auf- und Zuklappen, Archiv zugeklappt, Vorlagen und Ich unten; unter 760 px hinter „Ordnung ▸“.
  - Ebene: eine Spalte; Titel, Reihenfrage als graue Notiz, „+ Gespräch“, „+ Datei ablegen“, „···“ (Neu aus
    Vorlage); Gespräche, Material, Stunden bzw. Reihen; „darunter“ zugeklappt mit Zahl und Namen (offen, wenn
    hier nichts hängt); Stand nur bei wartet, läuft, deine Datei.
  - Gespräch: Nachrichten ohne Etiketten, Bausteine als graue Fläche mit „Kopieren“ und „Als Reihenfrage
    übernehmen“; Kopf mit Name, „Daraus Auftrag machen“, „···“ (Umbenennen, Was haben wir bisher?, An andere
    Ebene hängen) und Schalter für die rechte Spalte (standardmäßig offen, ein- und ausklappbar, Jan 10.11.);
    unter der Eingabe nur „+ Foto oder Datei“ (Menü: vom Rechner, Beispielfoto), „Optionen“ (gründlich, im
    Netz), „Senden“; „Kennt …“ zugeklappt. Rechte Spalte: Reihenfrage, Material (Vorschau), Gespräche, darunter
    zugeklappt; die Kette „Hängt an“ ist weg (die Brotkrumen zeigen sie).
  - Dokumentvorschau: jedes Material und jede abgelegte Datei öffnet rechts ein Seitenpanel mit gezeichneten
    Beispielseiten je Art (Word, Folien, Buchseite, Tabelle, Planung, Kriterien; nur der Titel ist echt),
    Blättern, Seitenbildchen, „Groß ansehen“ (dunkel, Pfeiltasten, Esc), „Darüber sprechen“ (neues Gespräch
    an derselben Ebene mit der Datei als Anhang), bei „wartet“ „Rückmeldung geben“. Laufendes Material zeigt
    „Entsteht gerade“. Fotos im Gespräch öffnen groß. Lehnt sich an Ergebnisansicht und Seiten-Betrachter der App an.
  - Heute: „Wartet auf dich“ zuerst (öffnet die Vorschau), dann „Weiter im Gespräch“, „Alle Gespräche“ zugeklappt.
    Lückenliste: 7 Lücken sichtbar, Erklärung auf Klick, Rest unter „Weitere 6 anzeigen“, Frage als Notiz.
  - Dichte (Probelauf, ohne Seitenleiste, sofort sichtbare Wörter vorher → nachher): Lückenliste 331 → 220,
    Heute 103 → 84, Klasse 8 190 → 84, Reihe Straftheorien 191 → 104, Gespräch g1 384 → 286. Bedienelemente
    etwa gleich viele, weil Material jetzt klickbar ist. Schriftgrößen im CSS 14 → 6.
- Gesehen: am 11.11. nachts in Jans Chrome (Windows, breites Fenster): Lückenliste, Reihe, Gespräch, Vorschau,
  Groß ansehen. Dabei behoben: „Heute“ wuchs in der Seitenleiste in die Höhe; Seitenbild im Panel zu hoch;
  Titel auf gezeichneten Seiten liefen über den Rand. Schmal (≤ 1100, ≤ 760), Handy und dunkel am 10.11. nur im
  Code durchgesehen, nicht im Browser (Jans Chrome war minimiert; headless Chromium auf dem Server fehlen
  Systembibliotheken libatk, libasound u. a.). Dabei behoben: Seitenbilder in „Groß ansehen“ und Vorschau mit
  weißen Rändern (feste Höhe), Vorschau unter 760 px jetzt ganzseitig, Ebenen-Menü „···“ lief am Handy rechts
  hinaus, Zeilenaktion „Vorschau“ war auf Touch ganz versteckt (Plan: sichtbar), Stand verschwand nach Antippen,
  Fokus nach Schließen der Vorschau landete beim ersten gleichen Knopf statt beim Auslöser. Offen: „sehr leise“
  `#8c8b87` hat hell nur etwa 3,4 : 1 (12-px-Texte: Zahlen, Köpfe, Bausteinart), unter AA; Jan entscheidet.
  Jan 10.11. nach dem Durchsehen: „passt erstmal so“. Nächster Schritt: Jan teilt die Skizze mit Lia, dann Test.
- Beispiele: Klasse 8 (Plan bis zum Halbjahr, Notentabelle), Reihe Straftheorien (Reihenfrage finden über zwei Tage
  mit Tabelle, Foto, Bausteinen; Reihenentwurf, Fallsammlung, Planung.pdf), Stunde 2 (Kant einfach erklären,
  Präsentation, Buchseite), Stunde 3 (Einstieg mit einem Fall), Stunde 4 (Arbeitsblatt läuft), Kurs 11 (ohne Reihe,
  Gespräch am Kurs), Kurs 12 (Bewertung am Kurs, Probenplan an der Inszenierung), zwei Gespräche ohne Ort.
  Alle Gesprächstexte ausgedacht, ohne Namen und ohne Zitate aus Lias Chats. Wort für Claude: „Claude“ (offen,
  ob Lia das so will). „Skizze zurücksetzen“ stellt alles wieder her.

Test mit Lia (Plan 4.2, Jan leitet, ca. 20 Min., Rahmen wie `docs/webapp-aufbau.md` 6): erst Teil 1 („Stimmt
das? Was fehlt?“, Antworten notieren), dann die Aufgaben. Vorlesen in Lias Worten, nichts erklären, Hilfe erst
nach 2 Minuten.

| # | Aufgabe (vorlesen) | Erfolg, wenn | richtiger erster Klick |
|---|---|---|---|
| 1 | „Du suchst noch eine Reihenfrage für die Strafe-Reihe. Gestern hast du schon mit Claude darüber gesprochen. Mach da weiter und nimm die Frage, die dir gefällt, als Reihenfrage.“ | „Als Reihenfrage übernehmen“ an einem Baustein, rechts steht die neue Frage | Heute „Weiter im Gespräch“ oder Baum: Straftheorien |
| 2 | „Zeig Claude ein Foto deiner Planung und frag, was er davon hält.“ | Foto (eigenes oder Beispiel) angehängt und gesendet | „+ Foto oder Datei“ unter dem Eingabefeld, dann „Beispielfoto nehmen“ oder „Vom Rechner wählen“ |
| 3 | „Du willst einen Merksatz aus dem Gespräch in dein Arbeitsblatt in Word übernehmen.“ | „Kopieren“ am Baustein Merksatz | Baustein im Gespräch |
| 4 | „Für die dritte Stunde der Strafe-Reihe hattest du schon mal mit Claude einen Einstieg gesucht. Finde das Gespräch. Dann fang für die vierte Stunde ein neues an.“ | Gespräch „Einstieg mit einem Fall“ geöffnet; neues Gespräch hängt an Stunde 4 | Baum: Straftheorien bzw. Stunde 3 |
| 5 | „Aus dem Reihenfrage-Gespräch soll jetzt der Reihenentwurf werden. Gib ihn in Auftrag.“ | „Daraus Auftrag machen“, Text geprüft, Abschicken | „Daraus Auftrag machen“ |
| 6 | „Leg deine Bewertungskriterien für den Theaterkurs ab, damit Claude sie immer kennt. Danach: Du hast eine Frage zum Unterrichtsbesuch, die zu keiner Klasse gehört. Wo fragst du?“ | Datei an Kurs 12 abgelegt; „Gespräche ohne Ort“ geöffnet oder „+ Gespräch“ dort | Baum: Kurs 12, „+ Datei ablegen“; Baum „Gespräche ohne Ort“ |

Notieren je Aufgabe: Erfolg (ohne Hilfe / mit Hilfe / nicht), erster Klick, wörtliche Äußerungen, was sie
experimentell findet, was sie nicht braucht. Danach: „Wo würdest du ein Gespräch hinhängen, Reihe oder Stunde?“,
„Würdest du damit statt in claude.ai chatten? Was fehlt dafür?“. Kein Bau ohne ihr Okay (Plan 4.3).

## Technik
- `logik.py`: reine Logik (`ketten()`, `heute()`, `ergebnis()`, `verlauf()`, `entwurf()`, Reihen: `reihen_aus()`,
  `reihe_von()`, `zeilen_je_reihe()`, `reihe_ansicht()`, Rahmen: `baum()`, `krumen()`, Stunden, Varianten,
  Fragen), getestet. `ordnung.py`: Struktur (über agentkit.struktur), Profil und Regeln lesen. `zustand.py`: was die Web-App selbst
  in data/ speichert (Stunden, Zuordnungen zu Stunde und Reihe, Entwurf-Entscheidungen, Nochmal), liest final/eigene aus agentkit. `dateien.py`: Pfade der
  Ergebnisdateien und der Vorschau, geprüft gegen den Agent-Ordner `lia/<agent>/` (aufgelöst inkl. Symlinks,
  kein `..`, nichts Verstecktes, nur pdf/docx/pptx/xlsx bzw. png). URLs tragen nur die Nummer in
  `ergebnis_dateien`, nie einen Pfad. `app.py`: FastAPI, dünn, Uvicorn auf Unix-Socket
  `data/webapp.sock` (Ordner 0700; Uvicorn setzt den Socket selbst auf 0666, der Ordner schützt).
- `vorlagen/basis.html` (Rahmen: Brotkrumen, Inhalt, Baum, Fragen; Kopf für Einzelansichten),
  `heute.html` (Seite), `_heute.html` (Inhalt, auch für htmx), `_zeile.html` (Zeile für Heute und Reihe),
  `reihe.html`, `ergebnis.html` (Material-Ansicht), `ansehen.html` (Seiten-Betrachter), `entwurf.html`, `neu.html`, `nicht_gefunden.html` (404 im Rahmen),
  `statisch/stil.css`. `app.rahmen()` liefert Baum und Brotkrumen für jede Seite.
- `statisch/htmx-2.0.4.min.js` mit `.sha256` (von unpkg und jsdelivr geladen, beide gleich; Test prüft die Summe).
- `requirements.txt`: feste Versionen (pip freeze) von fastapi, uvicorn (ohne [standard]), jinja2,
  python-multipart, webauthn samt Abhängigkeiten. agentkit per `.venv/.../agentkit.pth`.
- Tests ohne httpx (nicht freigegeben): echter Uvicorn auf einem Socket im Temp-Ordner, Anfragen mit http.client.

## Starten und ansehen
Dienst (Jan 30.10. „Weg 2“): `webapp.service` (Vorlage `systemd/webapp.service`, installiert in
~/.config/systemd/user/, aktiviert), hört nur auf `127.0.0.1:8791`, echt auf lia/instanz mit
`WEBAPP_NEUER_AUFTRAG=echt` und `WEBAPP_CHAT=an`. Neu starten nach einer Code-Änderung:
`systemctl --user restart webapp.service`; Log: `journalctl --user -u webapp.service -n 50`.
Von außen: `https://lia.meldro.de` über Caddy (HTTPS, Passwortschutz basicauth, Benutzer `lia`). Passwort im
Klartext und als Hash nur in `.env` (0600, nicht im Repo); den fertigen Caddy-Block erzeugt `data/caddy-lia.txt`
(0600). Eintragen macht Jan als root (siehe Offene Punkte 1).
Jan über den Tunnel (Mac): `ssh -N -L 8792:127.0.0.1:8791 agents-user`, dann http://localhost:8792.
Zum Testen von Hand ohne Dienst wie bisher: `.venv/bin/python app.py` (Unix-Socket `data/webapp.sock`, Tunnel
`-L 8792:/home/agent/agenten/shared/webapp/data/webapp.sock`), Test-Instanz mit `WEBAPP_INSTANZ=$PWD/data/test/instanz
WEBAPP_NEUER_AUFTRAG=test`, anderer Socket `WEBAPP_SOCKET=/pfad`, Port `WEBAPP_PORT=<n>`.

## Entscheidungen
- Jan 30.10. abends: „Weg 2“: Lia nutzt die App über https://lia.meldro.de mit Passwort (Caddy basicauth), Dienst
  webapp.service auf 127.0.0.1:8791; Passkeys (Bauschritt 2) später, Adresse bleibt.
- Jan 30.10. abends: „Ja, echt“: Die Web-App läuft schon vor den Konten echt auf lia/instanz
  (`WEBAPP_NEUER_AUFTRAG=echt WEBAPP_CHAT=an`), nur über Jans SSH-Tunnel. Neu, Variante, Rückmeldung, Nochmal,
  Zurückziehen und Fragen starten damit Läufe auf Lias Kontingent; Ergebnisse gehen auch per Telegram an Lia.
  Lia selbst hat weiter keinen Zugang (Konten fehlen). Die App läuft von Hand, kein Dienst.
- Jan 30.10.: Design von „Heute“ passt (im Tunnel angesehen). Nächster Schritt vorgezogen vor die Konten:
  Ergebnis- und Entwurf-Ansicht nur lesend (Klick aus „Heute“), Knöpfe mit Wirkung erst danach. Lia bekommt
  ohnehin erst nach K1, K3 und Jans Okay zum Dienst Zugang; bis dahin nur Jans Tunnel.

## Offene Punkte
11. Befund 03.11. (Prüflauf ohne Lia, Vorhersagen, Liste der Verbesserungen, nichts davon bestätigt): `data/ia/befund-2026-11-03.md` (nicht im Repo). Gebaut: Punkte 1, 3 und 8 (Jans Wahl); der Rest ist nicht beauftragt, Jan entscheidet. Wie der Dienst heute läuft: Abschnitt „Oberfläche und schneller Weg“. Im Browser noch nicht geprüft: Sperre der Knöpfe und Darstellung des großen Knopfs. Die übrigen Formulare der Struktur-Pflege (etwa „+ Klasse“, Termine, Übernehmen, Kopieren) sind auf Doppelklick nicht gemessen. Offen für Jan: `data/test/aufbauen.py` ins Repo holen? Benutzeroberfläche und Design: siehe Abschnitt „Gestaltung“. Nach dem Neustart geprüft (04.11., laut Hauptordner-Chat, nur Abruf): `/`, `/neu`, `/ich`, `/vorlagen`, eine Reihe, `/fach/neu` und ein Ergebnis antworten 200, kein Fehler im Log, `lia/instanz/reihen.toml` unverändert. Im Browser belegt ist nur: Jan hat auf der Testinstanz eine neue Klasse und eine neue Reihe angelegt („erstmal ganz gut geklappt“). Offen, im Browser nicht geprüft: Punkte 2, 5 und 7, Rot, Knöpfe, Wörter und Schrift, auch die Messung, ob der Hinweis mit Rückgängig im Bild bleibt.
10. webapp.service mit dem lia/chat-Ausbau (Netz, Dateien, Links) neu gestartet (Jans Okay 03.11.), die Seite
    liefert Häkchen und Datei-Feld aus. Offen: einmal im Browser in lia.meldro.de prüfen (Datei hochladen, Link
    öffnet neuen Tab).
0. Echt auf lia/instanz: freigegeben (Jan 30.10., siehe Entscheidungen). Noch kein echter Lauf aus der Web-App;
   den ersten beobachten (Log der App, Ergebnis in „Heute“, Nachricht an Lia per Telegram).
9. Strukturplan (docs/struktur-pflege-plan.md): Bauschritt 2 für die Web-App erledigt (lesend). webapp.service
   läuft noch mit dem alten Code; Neustart braucht Jans Okay (`systemctl --user restart webapp.service`). Nächste
   Schritte für diesen Ordner: nach der Migration (3) und den Schreib-Operationen in agentkit (4) Bauschritt 5
   (Masken, „+ Neu“ je Ebene, Stunden aus der Datei statt aus data/, Tests 24–25). Dabei offen: Fach ohne Klasse
   zeigt der Baum noch nicht; zwei laufende Klassen mit gleichem Namen in verschiedenen Schuljahren sähen im Baum
   gleich aus; Material an einer ausgeblendeten Stunde fällt an die ganze Reihe (Zuordnung bleibt gespeichert,
   Liste „Ausgeblendete Stunden“ fehlt); „Gehört zu“ und „Neu“ schicken die Stunden-Nummer, mit Verschieben in
   der App besser die id. Die Test-Instanz `data/test/instanz` hat keine reihen.toml (zeigt keine Reihen).
8. Aufträge, die inhaltlich eine neue Fassung sind, aber als neuer Material-Auftrag mit Datei kamen (93e29e,
   03b145 zur Theater-Fassung), haben kein `bezug` und stehen einzeln. Nicht geraten; Jan gefragt, ob so etwas
   zusammengehören soll (sauber wäre ein Änderungswunsch mit Datei aus der Ergebnis-Ansicht, Bauschritt 4).
1. lia.meldro.de läuft (30.10. abends): DNS A/AAAA bei INWX, Caddy-Block aus `data/caddy-lia.txt` eingetragen.
   Geprüft von außen: ohne Passwort 401, mit Passwort 200 (IPv4 und IPv6), HSTS und CSP gesetzt, Formular mit
   Origin lia.meldro.de angenommen, fremde Herkunft 403, kcal unverändert. Passwortschutz ist Übergang bis
   Bauschritt 2 (Passkey); Klärung K1 (Schule/Datenschutz) offen, Jan hat „Weg 2“ trotzdem entschieden.
2. Bauschritt 2: Konten (SQLite), Einladungslink, Passkey auf localhost, Sitzung, Mandant aus der Sitzung.
3. „Neu“ ist bisher nur „in den letzten 48 h fertig“. Mit Konten: gesehen/ungelesen je Ergebnis.
4. Material-Ansicht: Stunden (ohne Datei), Varianten-Zuordnung und Entwurf-Entscheidungen liegen nur in der
   Web-App. Die Test-Instanz hat keine Ergebnisse: Zum Ausprobieren von Rückmeldung, Variante und Nochmal müsste
   dort eines liegen (z. B. Kopie eines echten Ergebnisses). Offen: Entwurf ändern (examen müsste Änderungen
   lesen), Anmerkungen an einer Stelle (Renderer).
   Telegram-Feedback-Knöpfe nicht übernehmen (Jan 30.10.: „die im tg sind quatsch“).
7. Kern-Texte aus Telegram sagen „antworte direkt auf diese Nachricht“. In der Web-App passt das erst mit den
   Feedback-Knöpfen; bis dahin bleibt der Text, wie der Agent ihn geschrieben hat.
6. „Hat nicht geklappt“ zeigt auch alte Fehlschläge (22.10.) ohne Ablaufdatum. Ob sie nach einer Zeit verschwinden
   sollen, mit Lia klären.

## Gelernte Regeln
(noch keine)
