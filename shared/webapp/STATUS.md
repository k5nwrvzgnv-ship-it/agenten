# Status: Web-App für Lia (shared/webapp)

## Zweck
Überblick für Lia im Browser statt Telegram: was auf sie wartet, was läuft, was fertig ist. Später auch neue Aufträge,
Ergebnisse mit Vorschau, Feedback und Entwürfe. Plan: `../../docs/webapp-plan.md` (4.7 Technik, 7 Bauplan),
Auftrag und Entscheidungen: Punkt 24 in `../../STATUS.md`. Gestaltung „Modernist“ (Board ModHeute im Canvas
https://claude.ai/artifact/F8ysVSyr8TjGhFDcyNnejU).

## Stand (30.10.2026)
Bauschritt 1 und die Ergebnis-/Entwurf-Ansicht (nur lesend) fertig und committet, Aufträge mit Feedback-Schleife
als ein Auftrag mit Verlauf (Jans Anmerkung 30.10.), „Neuer Auftrag“ für Material im Testbetrieb (Jans Okay 30.10.),
Ordnung nach Fach, Klasse und Reihe (Jans Okay 30.10.), Bauschritt 1 des neuen Aufbaus „Desktop zuerst“
(Jans Okay 30.10.), Seitengalerie statt aller Seitenbilder und Material-Ansicht wie Board „Desktop“ (Jans Wunsch 30.10.),
Block A und B aus dem Abgleich mit dem Board (Jans Wahl 30.10.: „Block A, dann B“) und danach „alle Funktionen des
Boards echt“ (Jan 30.10. abends, Plan `board-plan.md`, Abschnitt „Board komplett“ unten), `./pruefen.sh` grün
(Web-App: 113 Tests).
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
- Stunden (`/reihe/<kennung>/stunde/<n>`, Jan 30.10. Block A3): speichert die Web-App selbst (`zustand.py`:
  `stunden`, `stunde_von`), Nummer = Platz in der Liste, Thema bis 120 Zeichen, ändern ja, löschen und
  umsortieren nein. Ansicht mit Material der Stunde und „Thema ändern“. In der Material-Ansicht „Gehört zu“
  (ganze Reihe oder Stunde n). Ein Auftrag aus einer Stunde nennt sie im Text („Stunde 3: Thema“); die Agenten
  kennen keine Stunden (Bedarf a in Punkt 24).
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
  - Rückmeldung geben (`POST …/rueckmeldung`): Text (Pflicht), Datei mit Kommentaren. Über
    `agentkit.fassungen.rueckmeldung`: die Datei wird eigene Fassung, dann ein Auftrag an `feedback` (bezug =
    neueste fertige Fassung bzw. die Fassung der Datei, siehe „Rückmeldung je Datei“); der Feedback-Dienst liest
    die Word-Kommentare und hängt die Datei an die Nachbesserung. Nur mit `WEBAPP_NEUER_AUFTRAG` test bzw. echt
    (startet lia-feedback.service). Sonst „Rückmeldungen gehen im Moment noch über Telegram“.
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
  Schutz ohne Konten: Origin muss zum Host passen (Sec-Fetch-Site same-origin), sonst 403; Token im Formular
  (HMAC, geheim je Start der App), nach einem Neustart „Die Seite war veraltet“. Ohne Zurücknehmen,
  ohne „Das beachte ich“, keine Auswahl der Art (gibt es noch nicht).
- Ordnung nach Fach, Klasse und Reihe (Jans Wunsch und Okay 30.10.):
  - Reihen aus `<instanz>/reihen.toml` (Format in `ordnung.py`: wie lia/unterricht/reihen.toml plus `id`,
    `stand`, `agenten`). Gibt es sie nicht (heute), setzt `ordnung.py` sie zusammen: Reihen aus
    `lia/unterricht/reihen.toml` (Fach aus profil.toml), Examensaufträge zur Reihe aus `examen.toml`
    (`titel_in_reihen_toml`), das Stück aus `theater.toml` als Fach „Darstellendes Spiel“, „Kurs 12“ (Jan
    30.10., steht in keiner Datei, `THEATER_FACH`, `THEATER_KURS`). Kaputte Dateien: Fehler im Log (nur bei Änderung), App zeigt ohne Reihen.
  - Zuordnung (`logik.reihe_von`): Feld `reihe` des Auftrags, sonst der Agent, wenn er in genau einer Reihe unter
    `agenten` steht. Nichts aus dem Text geraten, sonst „ohne Reihe“. Bei Ketten zählt der Ursprung.
    Echte Daten 30.10.: Theater-Fassung 0baec0 -> Der nackte Wahnsinn; Entwurf examen-0c44bf -> Ethik 8 Straftheorien;
    alle Material-Aufträge, Recherche und der Fehlschlag ohne Reihe.
  - Neuer Auftrag: Auswahl „Für welche Reihe?“ (laufende Reihen, Standard keine). Der Auftrag trägt `reihe`
    (agentkit, neues optionales Feld) und am Textende „Reihe: Titel (Fach, Klasse)“ für den Agenten.
- Test-Instanz für Jan: `data/test/instanz` (`.env` mit PERSON=Lia, 0600) und Agent-Ordner `data/test/unterricht`,
  nicht im Repo. Probelauf 30.10.: Auftrag mit PDF angelegt, Datei verschoben, ohne Origin 403; danach gelöscht.

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
  Jahr). `[[reihe.stunde]]` (nr 1 bis n, thema, marke UB/Prüfung) gewinnt gegen die Stunden der Web-App; dann
  kein „+ Stunde“ und kein „Thema ändern“ (die Datei pflegt der unterricht-Chat bzw. Jan).
- Fach-Ansicht `/fach/<kennung>` (Klassen mit laufenden Reihen, „Zum ganzen Fach“ leer), Fach in Baum und
  Brotkrumen verlinkt; die gezeigte Reihe klappt im Baum ihre Stunden aus.
- Rückmeldung je Datei: Knopf „Rückmeldung“ an jeder Datei-Karte, „Rückmeldung zu dieser Seite“ im Betrachter;
  Text beginnt „Zur Datei „Name.docx“, Seite n:“, bezug = die Fassung, aus der die Datei stammt.
- Entwurf (Typ entwurf): „Setze ich selbst ein“ / „Brauche ich nicht“ / Rückgängig, gespeichert in `zustand.py`
  (`entwuerfe`), nicht in der Freigabe (Jans Freigabe bleibt unberührt, examen liest Entscheidungen nicht).
  Entschiedene warten nicht mehr in „Heute“. Ändern eines Entwurfs geht weiter über Jan.
- „Nochmal“ bei Fehlschlag (nur Material ohne Anhänge, nur test/echt): neuer Auftrag mit Text, quelle, bezug,
  sitzung des letzten Versuchs; ein ersetzter Ursprung verschwindet aus „Hat nicht geklappt“ (`ersetzt`).
- „Zurückziehen“ unter „Läuft gerade“ (`agentkit.auftraege.zurueckziehen`, ein laufender claude-Lauf endet).
- Galerie: dazu Reihenentwurf und Lernerfolgskontrolle (nur Ethik, unterricht), Spielfassung (Kürzung) und
  Szenenaufgabe (nur Darstellendes Spiel, Agent theater, quelle portal-theater, weitere Felder Länge,
  Spieler*innen, Was bleiben muss bzw. Methode, Szene, Material). Spielfassung = ganze Runde, bis 3 Stunden,
  etwa 7 USD, nur „Der nackte Wahnsinn“.
- Spalte „Fragen“ an den Chat-Agenten `lia/chat` (Schnittstelle `schnittstelle.py`, Warteschlange in
  lia/chat/data): nur mit `WEBAPP_CHAT=an` (jede Frage läuft über Lias Kontingent, ca. 0,03 USD). „Ich weiß:
  Ort“ (Reihe, auf Stundenseiten mit Stunde), „ohne Ort fragen“, „gründlich“, Antwort per htmx alle 2 s
  (`/teile/frage/<id>`), die letzten 6 Fragen mit Trennlinie bei Ortswechsel, Markdown nur fett und Listen,
  „Daraus Auftrag machen“ öffnet Neu mit Frage und Antwort am Ort. Noch nie aus der Web-App echt gefragt.
Nicht gebaut: „+ Reihe“ in der App (schreibt reihen.toml; Jan bzw. unterricht-Chat), Fach-Material und Lias
Ablage (Jan fragen), Datei in eine Stunde ziehen (JavaScript), Muster, eigene Formatvorlage hochladen (unterricht
nutzt jetzt Vorlagen aus seinem data/vorlagen/, ein Upload fehlt), Konten.

## Technik
- `logik.py`: reine Logik (`ketten()`, `heute()`, `ergebnis()`, `verlauf()`, `entwurf()`, Reihen: `reihen_aus()`,
  `reihe_von()`, `zeilen_je_reihe()`, `reihe_ansicht()`, Rahmen: `baum()`, `krumen()`, Stunden, Varianten,
  Fragen), getestet. `ordnung.py`: Reihen-Dateien, Profil und Regeln lesen. `zustand.py`: was die Web-App selbst
  in data/ speichert (Stunden, Zuordnungen, Entwurf-Entscheidungen, Nochmal), liest final/eigene aus agentkit. `dateien.py`: Pfade der
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
0. Echt auf lia/instanz: freigegeben (Jan 30.10., siehe Entscheidungen). Noch kein echter Lauf aus der Web-App;
   den ersten beobachten (Log der App, Ergebnis in „Heute“, Nachricht an Lia per Telegram).
9. Reihen: lia/instanz/reihen.toml gibt es (30.10.); der Ersatz aus den Agent-Ordnern greift nur noch ohne sie.
   Pflege durch Lia in der App (Neue Reihe, Behandeltes ergänzen) und
   „Reihe zuordnen“ für alte Aufträge (schreibt in Lias Instanz) erst mit Konten. Weitere Klassen von Lia sind
   nicht bekannt; Jan trägt sie ein, sobald Lia sie nennt.
8. Aufträge, die inhaltlich eine neue Fassung sind, aber als neuer Material-Auftrag mit Datei kamen (93e29e,
   03b145 zur Theater-Fassung), haben kein `bezug` und stehen einzeln. Nicht geraten; Jan gefragt, ob so etwas
   zusammengehören soll (sauber wäre ein Änderungswunsch mit Datei aus der Ergebnis-Ansicht, Bauschritt 4).
1. lia.meldro.de (Jan als root, 30.10. vorbereitet): DNS bei INWX A `84.247.188.205` und AAAA
   `2a02:c207:3020:9076::1` (wie kcal), dann `data/caddy-lia.txt` an /etc/caddy/Caddyfile anhängen (kcal-Block
   bleibt), `caddy validate --config /etc/caddy/Caddyfile`, `systemctl reload caddy`. Danach prüfen: ohne Passwort
   401, mit Passwort 200, Formulare (Origin = Host lia.meldro.de). Passwortschutz ist Übergang bis Bauschritt 2
   (Passkey); Klärung K1 (Schule/Datenschutz) offen, Jan hat „Weg 2“ trotzdem entschieden.
2. Bauschritt 2: Konten (SQLite), Einladungslink, Passkey auf localhost, Sitzung, Mandant aus der Sitzung.
3. „Neu“ ist bisher nur „in den letzten 48 h fertig“. Mit Konten: gesehen/ungelesen je Ergebnis.
4. Material-Ansicht: Stunden (ohne Datei), Varianten-Zuordnung und Entwurf-Entscheidungen liegen nur in der
   Web-App. Die Test-Instanz hat keine Ergebnisse: Zum Ausprobieren von Rückmeldung, Variante und Nochmal müsste
   dort eines liegen (z. B. Kopie eines echten Ergebnisses). Offen: Entwurf ändern (examen müsste Änderungen
   lesen), Anmerkungen an einer Stelle (Renderer).
   Telegram-Feedback-Knöpfe nicht übernehmen (Jan 30.10.: „die im tg sind quatsch“).
7. Kern-Texte aus Telegram sagen „antworte direkt auf diese Nachricht“. In der Web-App passt das erst mit den
   Feedback-Knöpfen; bis dahin bleibt der Text, wie der Agent ihn geschrieben hat.
5. Schrift: Inter/Inter Tight werden nur genutzt, wenn sie auf dem Gerät sind (sonst Helvetica/Arial). Google Fonts
   bewusst nicht (Lias Gerät soll nur mit dem Server sprechen). Schriftdateien lokal ausliefern: Jan fragen
   (Lizenz OFL, Dateien ins Repo wie htmx).
6. „Hat nicht geklappt“ zeigt auch alte Fehlschläge (22.10.) ohne Ablaufdatum. Ob sie nach einer Zeit verschwinden
   sollen, mit Lia klären.

## Gelernte Regeln
(noch keine)
