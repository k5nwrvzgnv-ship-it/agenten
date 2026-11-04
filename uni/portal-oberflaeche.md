# Portal-Oberfläche: Aufgaben und Befund (Schritt 1)

Stand 04.11.2026. Nichts umgebaut. Jan hat die Kernaufgaben bestätigt und Ergänzungen genannt (Abschnitt "Schritt 3, Zwischenstand").
Schritt 2 (Messlatte) entfällt: Jan will keine Messung (04.11.). Es gibt keine Zielwerte, abgenommen wird nach Jans Eindruck.
Schritt 3 (Vorbilder): eingearbeitet, Jans Bestätigung steht aus. Offene Punkte stehen am Ende. Schritt 4 beginnt erst nach seinem Okay.

Kennzeichnung: **[B]** belegt in den genannten Daten, **[W]** von Jan gewünscht, aber noch nicht praktisch vorgekommen,
**[V]** meine Vermutung.

## Grundlage und ihre Grenzen

- Jans eigene Nachrichten aus den Chats im uni-Ordner seit 28.10., Aufträge der Exposé-Kette in
  `shared/auftraege/erledigt/`, PDF-Anmerkungen vom 03.11. (als Text im Auftrag 20261103-114706-uni-c85257),
  `data/projekte/fehlstellen/schriftverkehr.json`, `geprueft.json` der Kette, Vorlagen, CSS, Zugriffslog des Dienstes.
- **Keine Sichtprüfung.** Der Browser auf dem Server startet nicht (Systembibliotheken fehlen, zum Beispiel libatk),
  und es war kein Chrome mit Erweiterung verbunden. Alle Aussagen zum Aufbau kommen aus HTML und CSS.
- **Kleine Stichprobe, vor dem Portal entstanden.** Eine Kette, ein Projekt, drei Tage. Die Arbeitsmomente liefen in
  Chat und Telegram, das Portal gibt es erst seit dem 04.11. Lernen und Üben sind damit nicht abgedeckt.
- **Das Log taugt kaum.** Fast alle Einträge sehen nach Tests und Messungen aus (Dutzend Aufrufe in einer Minute,
  absichtlich abgelehnte Eingaben). Möglicherweise von Jan **[V]**: 15:30 bis 15:31 Modul, Projekt, Recherche, neun Minuten
  vor der Kritik. Kein Filter, keine weitere Ansicht. Die Quelle lässt sich nicht trennen, alles kommt über 127.0.0.1.

## Kernaufgaben

| Nr. | Aufgabe | Beleg | Einstufung |
|---|---|---|---|
| 1 | Aktuelle Fassung lesen und kommentieren, dann die neue Fassung prüfen | PDF-Anmerkungen 03.11. (6 Punkte plus Generelles), Nachtrag, 5 Aufträge der Kette; Jan 04.11.: "der agent schreibt und wir kommentieren" | [B], häufigste Aufgabe |
| 2 | Offene Stellen abarbeiten: was fehlt, was kann ich nachliefern | Anmerkungen 1, 2, 5, 6; Normen und Werk Schneider am 03.11. nachgeliefert; "welche normen brauchen wir noch" | [B] |
| 3 | Der Recherche eine Nachfrage stellen, kurz und sparsam | Kamera oder RealSense für Henri ("nicht so viele tokens"), Normen-Frage, beide 03.11., im Chat | [B], zwei Fälle |
| 4 | Von einer Aussage im Text zur Quelle: trägt das, kann es weg | Anmerkungen 3 bis 5 (Scopus-Absatz, Achatz, Lin, Pan "kann entfallen", Kodytek). Dass Jan dabei in Belegen nachsah, ist nicht belegt | [B] für den Bedarf am Text, [V] für den Weg über die Belege |
| 5 | Verstehen, wie die Recherche zustande kam, und es erklären | "wie die recherche ... abgelaufen ist", "ich verstehe nicht was die csv geliefert hat", Zusammenfassung für Freunde (alle 03.11.) | [B] |
| 6 | Ergebnis an die Gruppe oder Betreuung weitergeben | PDF-Blatt für Henri; Exposé für Böhme; Rückfragen Böhmes zu Zeitplan und Termin | [B] |
| 7 | Stand mit Kontaktpersonen sehen, Interviews vorbereiten | Jan 04.11.: "schriftverkehr ... ersichtlich", Interviews "kommt schon recht bald" | [W] |
| 8 | Für die Prüfung üben, Karten und mündlich | Jan 04.11.: will ab jetzt mehr lernen; Nutzung 0 laut Plan, Abschnitt 2 | [W], nicht aus dieser Auswertung abgeleitet |

Auffällig: Für keine dieser Aufgaben brauchte Jan belegt die Liste aller Aussagen. Das ist aber die Standardansicht.

## Befund zum heutigen Stand

Gemessen an der laufenden Instanz, Wörter ohne Auszeichnungen:

| Seite | Wörter | Links | Aufklapper |
|---|---:|---:|---:|
| Recherche (Standardansicht) | 16.635 | 258 | 163 |
| Protokoll | 2.643 | 7 | 0 |
| Projekt (Exposé) | 1.416 | 9 | 0 |
| Modul Holzschutz | 1.419 | 5 | 16 |

Rangfolge nach vermuteter Wirkung, die Reihenfolge ist meine Einschätzung:

1. **Die Recherche öffnet mit allem.** 163 Aussagen unter 24 Fragen auf einer Seite, die Fragen im Schnitt 342 Zeichen
   lang, die längste 464. Es gibt keinen Überblick vorab und keine Standardauswahl.
2. **Die Gliederung folgt der Datei, nicht der Arbeit.** Die Ansichten Aussagen, Quellen, Lücken, Literatursuche
   entsprechen den Feldern von `geprueft.json`. Keine davon beantwortet eine Kernaufgabe direkt.
3. **Exposé und Recherche sind nicht verknüpft.** Aus dem Exposé führt kein Link zu Aussage oder Beleg (Aufgabe 4).
   Auch von einer Quelle kommt man nicht zu ihren Aussagen. Von 89 Quellen stehen 12 Angaben im Literaturverzeichnis,
   aber im Portal ist nicht sichtbar, welche.
4. **Keine Suche.** Weder Volltext noch Suchfeld. Sortiert wird nur fest (Quellen). Filter gibt es nur nach Status und
   nach einer Frage.
5. **Der Statusfilter trennt schlecht.** 87 von 163 Aussagen sind "teilweise". Das Feld "Fehlt" ist bei 88 Aussagen
   gefüllt und steckt zugeklappt in den Details. Nach Herkunft (Scopus 54, Methoden 26, Regelwerk 25 ...) oder Art
   (129 Tatsachen, 34 Einschätzungen) lässt sich nicht filtern. 29 Aussagen haben gar keinen Beleg, auch das ist nicht wählbar.
6. **Nachfragen gehen nicht im Portal** (Aufgabe 3). Die Recherche-Seite hat kein Formular. Das ist vermutlich die Lücke hinter
   "machtvolles Instrument" **[V]**.
7. **Hierarchie fehlt.** Der Baum listet Projekt und Modul flach, ohne Trennung von Arbeiten und Lernen. Brotkrumen wie bei Lia
   wurden beim Übernehmen entfernt. Auf der Seite liegen Reiter, Ansicht und Status als bis zu drei Navigationsreihen
   übereinander.
8. **Kommentieren liegt vor dem Text.** Das Formular "Rückmeldung geben" steht vor dem Exposé. Wer erst liest, muss zurück.
9. **Fassungen lassen sich nicht vergleichen.** Das Portal zeigt nur die aktuelle Fassung und kein "was hat sich geändert"
   (Aufgabe 1). Die Sicherung alter Fassungen gibt es nur für den Agenten.
10. **Vermutlich leere rechte Spalte [V].** Das CSS hält auf breiten Fenstern 320 px für die Spalte "Fragen" frei, die im Uni-Portal
    fehlt. Der Text ist dazu auf 840 px begrenzt. Muss im Browser bestätigt werden.

Nicht geprüft: Lesbarkeit, Abstände, Schriftgrößen und Handy-Ansicht, alles, was nur ein Bild zeigt.

## Was daraus nicht folgt

- Keine Struktur und kein Entwurf, das ist Schritt 4.
- Ob ein Nachfrage-Formular gebaut wird. Es berührt Kosten und Agentenlogik und wäre ein eigener Vorschlag.

## Schritt 3, Zwischenstand (Jan 04.11.)

**Kernaufgaben:** Jan: "stimmen". Er möchte vielleicht ergänzen **[W]**:
- 9. Neue Recherche beginnen und vorab einen Überblick haben, wie sie ablaufen wird.
- 10. Gemeinsam kapitelweise am Forschungsprojekt arbeiten; jede Person der Gruppe bekommt einen Zugang zur Web-App. Dafür hat Jan
  schon eine Idee, die er noch ausführlicher erklärt. Sie ist noch nicht aufgenommen, also nicht erfinden, sondern nachfragen.

**Flexibilität heißt (Jan):** Der Aufbau hat eine sinnvolle Logik, und auf jeder Strukturebene kann der Nutzer einen neuen Reiter
hinzufügen oder entfernen. Die Ebenen laufen von Kursen über Vorlesungen und deren Aufbereitungen zu Prüfungsleistungen. Dokumente und
Aufträge bzw. Recherchen finden auf einer bestimmten Ebene statt und werden dort auch wiedergefunden. Das gilt auch für alles andere.
Mein alter Vorschlag (Filter, Suche, gespeicherte Ansichten) war also nicht gemeint.

**Erstes Vorbild, von Jan genannt:** Lias Web-App, "in der Hinsicht schon ganz gut inzwischen". Was sich übernehmen lässt, laut
`shared/webapp/STATUS.md` und Vorlagen, von mir nicht im Browser gesehen, von Jan noch nicht bestätigt **[V]**:
- Baum nach Ebenen (dort Fach, Klasse, Reihe), die gezeigte Seite markiert. Brotkrumen auf jeder Seite.
- "+ Neu hier" an Reihe, Stunde und Material: Der neue Auftrag kennt seinen Ort und bleibt dort auffindbar.
- "+ Stunde", "+ Reihe", "+ Fach" in der Pflege: Ebenen lassen sich anlegen, ohne die Struktur von Hand zu ändern.
- Jede Zeile nennt ihren Ort, wenn sie außerhalb der Ebene steht ("Ethik › Klasse 8 › Straftheorien").
- Unklar: Ob die Struktur dort auch das Entfernen trägt und was Jan an Lias App genau gut findet.
- Grenze: `shared/webapp` bleibt unverändert, übernommen wird nur das Muster, in `uni/`.

**Screenshots (Recherche und Modul Holzschutz, 04.11.):** erste Sichtprüfung, die Projektseite mit dem Exposé fehlt noch.
- Befund 10 bestätigt: Rechts neben dem Inhalt ist auf breitem Fenster etwa die halbe Breite leer.
- Befund 7 bestätigt: Reiter, Ansicht und Status liegen als drei Reihen übereinander, und erst darunter beginnt der Inhalt.
- Recherche: Die Fragen stehen als fette Großbuchstaben über bis zu sechs Zeilen und sind so schwerer lesbar als die Aussagen darunter.
- Modul: Das Formular "Transkript auswerten" füllt die Mitte der Seite, die Themen kommen erst danach. Der technische Hinweis auf
  `ELEVENLABS_AGENT_URL` in `uni/portal/.env` steht offen auf der Seite. Alle Themen zeigen "Score 5, nicht gesehen" ohne Erklärung.

**Spannung zum Plan:** `webapp-plan.md` Abschnitt 8 "Was nicht gebaut wird" nennt "Zugänge für die Gruppe" und "Oberfläche für die
Recherche-Pipeline". Die Aufgaben 9 und 10 gehen darüber hinaus. Das Portal hat heute ein gemeinsames Passwort und keine Personen,
wer Zugang hat, sähe auch Schriftverkehr und Lernstand. Vor Schritt 4 klären. Zugänge und Recherche-Start berühren Kosten und
Datenschutz und kommen, wie die Nachfrage, als eigener Vorschlag.

## Jans Antworten (04.11., abends)

**Seine Idee zur gemeinsamen Arbeit, nah an seinen Worten:** Ähnlich wie bei Lias Web-App gibt es Ebenen. Oberste Ebene ist der Kurs
(wissenschaftliches Projekt). Innerhalb des Projekts können neue Reiter aufgemacht werden, seine spontanen Beispiele: Themenfindung,
Exposé, Versuche, Interviews, Software, Hardware, Schriftlicher Teil. Alles lässt sich frei benennen, umbenennen und umorganisieren, auch
im Nachhinein. Innerhalb dieser Ebenen gibt es wieder neue Ebenen, im schriftlichen Teil zum Beispiel die einzelnen Kapitel, sodass jede
Person in einem Kapitel arbeiten kann. Auf den Ebenen kann man immer Dokumente oder Aufträge anlegen. So hat jeder Auftrag und jedes
Dokument einen Ort, und alle Fassungen gehören zu dem einen Dokument.

**Rechte (Jan):** "beide sollen alles bearbeiten können innerhalb des wissenschaftlichen projektes, wir arbeiten alle an allem und
brauchen auch überblick was die anderen gemacht haben". Daraus neu [W]: Überblick, was die anderen gemacht haben. "beide" meint vermutlich
Felix und Henri **[V]**, das Exposé nennt sie als Mitautoren. Dass Lernstand und Modul Holzschutz für sie gesperrt bleiben, folgt
aus "innerhalb des Projekts" nur vermutlich **[V]**.

**Lias App:** Die Liste oben stimmt "so in etwa", Jan verweist auf seine Idee. Damit gilt sie als bestätigt, ohne Einzelprüfung.

**Weitere Vorbilder:** Ihm fällt keines ein. "du kannst sehr gerne mal recherchieren, wir sollten nicht das rad neu erfinden". Die
Recherche ist also von Jan gewünscht und ersetzt die eigene Benutzung; Vorbilder daraus sind nur aus Dokumentation bekannt und so zu kennzeichnen.

**Entscheidungen:**
- `portal/messung.py` und `portal/tests/test_messung.py` löschen: ja. Direkt davor erneut geprüft: Sonst nutzt sie nichts im Repo;
  `messung` in `auswertung_agent.py` und `agentkit/sprache.py` ist etwas anderes. Gelöscht.
- Baumtest, fremde Person, Log-Auswertung nach zwei Wochen: gestrichen (ja).
- `webapp-plan.md` Abschnitt 9, Zeile "Oberfläche: kein Prüfstein, Abnahme nach Jans Eindruck": ergänzen (ja). Eingetragen.

**Screenshot Projektseite (Exposé):**
- Befund 8 bestätigt: Das Formular samt Erklärung und Kostenangabe füllt den ersten Bildschirm, der Exposé-Text beginnt ganz unten.
- Befund 10 auch hier: Rechts ist etwa die halbe Breite leer.
- Rückmeldungen heißen nur nach ihrer Zeit ("2026-11-04 20:34"), der Inhalt ist nicht erkennbar.
- Inhalt: Die Kopfzeile zeigt "Felix Frankowiak (Matr.-Nr. XXXXXXXX)", darüber steht "Noch offen (0)". Der Platzhalter wird also nicht als offen erkannt.

## Schritt 3, Vorbilder aus der Recherche (04.11.)

**Wie sicher das ist:** Alles in diesem Abschnitt ist nur aus der Dokumentation der Anbieter bekannt, abgerufen am 04.11.2026. Die Seiten
wurden über automatische Zusammenfassung gelesen, nicht im Wortlaut geprüft. Keines der Werkzeuge wurde benutzt, ob sich ein Muster
gut anfühlt, ist also offen. Von Jan noch nicht bestätigt. Übernommen werden nur Muster, kein Werkzeug wird eingeführt. Lias App steht
oben und gilt als bestätigt.

Aufgabennummern wie in "Kernaufgaben" und "Schritt 3, Zwischenstand". "Ebenen" meint Jans Idee aus "Jans Antworten". Die Aufgaben 9 und 10
sind noch nicht fest (Frage 2).

### Notion: Ebenen und Kommentare

Quellen: [Seitenleiste](https://www.notion.com/help/navigate-with-the-sidebar), [Kommentare](https://www.notion.com/help/comments-mentions-and-reminders),
[Löschen und Wiederherstellen](https://www.notion.com/help/duplicate-delete-and-restore-content), [Analytics](https://www.notion.com/help/page-analytics)

- **Ebenen, Aufgabe 10:** Seiten beliebig tief verschachtelt, "+" beim Darüberfahren legt eine Unterseite an Ort und Stelle an, Verschieben
  per Ziehen in der Seitenleiste. Gelöschte Seiten liegen 30 Tage im Papierkorb und lassen sich wiederherstellen, das sichert Jans "entfernen" ab.
- **Aufgabe 1, 2:** Kommentar an der markierten Stelle, standardmäßig rechts neben dem Text. Häkchen löst auf, ein Filter holt Erledigtes
  zurück. Bereich mit allen Kommentaren der Seite, filterbar nach Person und Status.
- **Aufgabe 10:** Pro Seite sichtbar, wer erstellt, bearbeitet und angesehen hat, mit Zeitpunkt.
- **Nicht übernehmen:** Fassungen. Sie entstehen automatisch alle 10 Minuten und passen schlecht auf benannte Fassungen eines Agenten.
- **Nicht belegt:** Umbenennen und Pfadanzeige standen nicht im Gelesenen. Die Brotkrumen kommen ohnehin aus Lias App.

### Basecamp: eine Datei mit Fassungen, Überblick über die anderen

Quellen: [Aktivität](https://5.basecamp-help.com/article/1160-activity), [Dokumente und Dateien](https://5.basecamp-help.com/article/1079-docs-and-files),
[Verschieben](https://5.basecamp-help.com/article/1134-moving-copying), [Projekt einrichten](https://5.basecamp-help.com/article/1176-creating-and-setting-up-a-project) (nur aus dem Suchergebnis)

- **Aufgabe 10:** Zeitleiste nach Datum gruppiert, ein Klick führt an den ursprünglichen Ort. Filter nach Projekt, Person und Stichwort.
- **Aufgabe 1, Jans "alle Fassungen gehören zu dem einen Dokument":** Vorn die aktuelle Fassung, "Replace with a new version" darunter,
  "See all versions" zeigt die früheren.
- **Ebenen:** Beim Verschieben bleiben Kommentare, Anhänge und Verlauf erhalten. Ordner klappen in der Liste auf, ohne die Seite zu verlassen.
- **Nur aus dem Suchergebnis:** Werkzeuge je Projekt zu- und abschalten und direkt umbenennen, wirkt nur in diesem Projekt.
- **Grenze:** Die Struktur ist eher flach (Projekt, Werkzeuge, Ordner) und nicht Jans freier Baum. Die Tiefe der Ordner ist nicht angegeben.

### Overleaf: benannte Fassungen, Kommentare

Quellen: [Verlauf und Fassungen](https://docs.overleaf.com/writing-and-editing/history-and-versioning), [Kommentare](https://docs.overleaf.com/collaborating/commenting),
[Reviewer](https://docs.overleaf.com/collaborating/reviewing-and-reviewers) (nur aus dem Suchergebnis)

- **Aufgabe 1:** Wichtige Stände bekommen einen Namen ("Label this version"). Zwei Ansichten: "All history" und "Labels". Der jetzige Stand heißt
  "Current state". Vergleich durch Wahl von Start und Ende in der Liste.
- **Aufgabe 1, 2:** Text markieren, Kommentar ins Panel daneben. Häkchen löst auf, aufgelöste Kommentare stehen in einer Liste und lassen sich wieder öffnen.
- **Nicht übernehmen:** Beim Wiederherstellen werden Kommentare und Änderungsverfolgung mit zurückgesetzt. Das passt nicht zu einer
  Kommentar-Fassung-Kette **[V]**.
- **Nicht belegt:** Übersicht offener Kommentare über alle Dateien, Überblick über die Tätigkeit anderer, Aufteilung in Kapitel.

### Confluence Cloud: Fassungen vergleichen

Quelle: [Seite erstellen und bearbeiten](https://support.atlassian.com/confluence-cloud/docs/create-edit-and-publish-a-page/)

- **Aufgabe 1 ("was hat sich geändert", Befund 9):** Zwei Versionen auswählen und vergleichen, lange unveränderte Abschnitte sind ausgeblendet.
- **Aufgabe 1:** Wiederherstellen löscht nichts, die alte Version wird als neueste kopiert, mit Änderungskommentar.
- **Nicht verwendet:** Das Verschieben im Baum fand sich nur in sehr alter Dokumentation (Version 2.9), für das aktuelle Produkt also nicht belegt.

### NotebookLM: von der Aussage zur Quelle

Quelle: [Hilfeseite](https://support.google.com/notebooklm/answer/16179559?hl=en) (die Hilfe heißt inzwischen "Gemini Notebook")

- **Aufgabe 4:** Verweis direkt im Text, Darüberfahren zeigt die zitierte Stelle, ein Klick öffnet die Quelle dort.
- **Aufgabe 3, nur als Muster:** Antworten stützen sich nur auf die eigenen Quellen und lassen sich als Notiz mit klickbaren Zitaten speichern. Die Nachfrage selbst ist ein eigener Vorschlag.
- **Grenze:** Dort geht es um Chat-Antworten, nicht um eine eigene Fassung wie das Exposé. Das Muster muss auf Exposé-Sätze und `geprueft.json`
  übertragen werden. Ob die Daten das hergeben, ist nicht geprüft.

### Lücken

- Aufgabe 5 (wie kam die Recherche zustande), 6 (Weitergabe), 7 (Kontaktpersonen), 9 (neue Recherche, Überblick vorab): kein Vorbild.
  Danach wurde teils gar nicht gesucht, teils fand sich nichts Belastbares.
- Aufgabe 8 (Üben): war nicht Teil dieser Suche.
- Aufgabe 2 nur teilweise: Kommentare sind pro Seite belegt, eine Gesamtliste "was fehlt noch" über alle Dokumente nicht.
- Aufträge an einen Agenten mit festem Ort: In den gelesenen Werkzeugen gibt es nichts Direktes, Vorbild bleibt Lias "+ Neu hier".

### Spannung zum Plan

Stand: `webapp-plan.md` Abschnitt "Was nicht gebaut wird" (unter Abschnitt 8) bleibt unverändert, solange Jan nichts anderes sagt.

| Im Plan ausgeschlossen | Was dagegen läuft | Folge |
|---|---|---|
| "Zugänge für die Gruppe" | Aufgabe 10, Jans "wir arbeiten alle an allem" | Eigener Vorschlag (Kosten, Datenschutz). Heute gibt es ein gemeinsames Passwort und keine Personen |
| "Oberfläche für die Recherche-Pipeline" | Aufgabe 9, Recherche-Start, Nachfrage (Aufgabe 3) | Eigener Vorschlag (Kosten, Agentenlogik) |
| "Web-Editor für Berichte: Word bleibt" | Kommentieren an der Textstelle im Browser | Entfällt, Jan will das vorerst nicht (siehe "Jans Antworten auf die Fragen") |

Davon hängen ab:
- Der Filter nach Person im Aktivitätsüberblick (Basecamp) hängt an den Zugängen. Ohne Personen zeigt eine Zeitleiste nur, was geschah, nicht wer es war **[V]**.
- Für den Fassungsvergleich (Confluence, Overleaf) ist in Schritt 4 zu prüfen, woher die alten Fassungen kommen: Die Sicherung `vorher/` gibt das Portal laut
  `STATUS.md` nie wieder aus.

## Jans Antworten auf die Fragen (04.11., spät)

- **Zeile "mindestens 10 von 14 Tagen":** "nein löschen". Aus `webapp-plan.md` Abschnitt 9 gelöscht.
- **"Beide":** Felix und Henri sind gemeint. "holzschutz oder ander müssen nicht gesperrt bleiben, soeinfahch wie möglich erstmal". Keine Sperren vorerst.
  Sie sähen dann auch Schriftverkehr und Lernstand, das benennt der Vorschlag zu den Zugängen.
- **Eigener Vorschlag zu Zugänge, Recherche-Start, Nachfrage:** "ja gerne", dafür Vorbilder recherchieren, "keine lust das rad neu zuerfinden".
- **Kommentieren an der Textstelle im Browser:** "erstmal zu kompliziert, lieber das mit dokumetnen und kommentaren optimieren und wirklich gut machen".
  Nicht vorsehen. Die Muster dazu (Notion, Overleaf) gelten damit nur noch für die Darstellung der Kommentare und das Erledigen, nicht fürs Markieren im Text **[V]**.

## Offene Fragen an Jan

1. Aufgabe 9 und 10: Jan hat die Frage nicht verstanden, einfacher neu gestellt.
2. Bestätigst du die Vorbilder? Erst danach Schritt 4.

**Hinweis zum Exposé:** Die Autorenzeile der aktuellen Fassung zeigt "Felix Frankowiak (Matr.-Nr. XXXXXXXX)". Die Seite meldet trotzdem "Noch offen (0)",
weil `portal/projekt.py` nur `[OFFEN: ...]` als offene Stelle erkennt. Nur gemeldet, nichts geändert.
