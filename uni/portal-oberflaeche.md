# Portal-Oberfläche: Aufgaben und Befund (Schritt 1)

Stand 04.11.2026. Nichts umgebaut. Jan hat die Kernaufgaben bestätigt und Ergänzungen genannt (Abschnitt "Schritt 3, Zwischenstand").
Schritt 2 (Messlatte) entfällt: Jan will keine Messung (04.11.). Es gibt keine Zielwerte, abgenommen wird nach Jans Eindruck.
Schritt 3 (Vorbilder) läuft, offene Punkte stehen am Ende.

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
- `portal/messung.py` und `portal/tests/test_messung.py` löschen: ja. Geprüft 04.11.: Sonst nutzt sie nichts im Repo (Treffer nur in
  STATUS.md und dieser Datei); `messung` in `auswertung_agent.py` und `agentkit/sprache.py` ist etwas anderes. Noch nicht gelöscht.
- Baumtest, fremde Person, Log-Auswertung nach zwei Wochen: gestrichen (ja).
- `webapp-plan.md` Abschnitt 9, Zeile "Oberfläche: kein Prüfstein, Abnahme nach Jans Eindruck": ergänzen (ja). Noch nicht eingetragen.

**Screenshot Projektseite (Exposé):**
- Befund 8 bestätigt: Das Formular samt Erklärung und Kostenangabe füllt den ersten Bildschirm, der Exposé-Text beginnt ganz unten.
- Befund 10 auch hier: Rechts ist etwa die halbe Breite leer.
- Rückmeldungen heißen nur nach ihrer Zeit ("2026-11-04 20:34"), der Inhalt ist nicht erkennbar.
- Inhalt: Die Kopfzeile zeigt "Felix Frankowiak (Matr.-Nr. XXXXXXXX)", darüber steht "Noch offen (0)". Der Platzhalter wird also nicht als offen erkannt.

## Offene Fragen an Jan

1. Bleibt die Zeile "mindestens 10 von 14 Tagen geübt, sonst Portalbau stoppen" (23.11.) in `webapp-plan.md` Abschnitt 9? Jans "ja" zu der
   Doppelfrage ist hier nicht eindeutig (bleibt oder Empfehlung streichen). Nachfragen, nichts ändern.
2. Sollen Aufgabe 9 (neue Recherche beginnen, Überblick vorab) und 10 (gemeinsam kapitelweise) feste Kernaufgaben werden? Bei 10 und dem
   Überblick spricht Jans Antwort dafür, zu 9 hat er nichts gesagt.
3. Sind mit "beide" Felix und Henri gemeint, und bleiben Lernen und Holzschutz für sie gesperrt?
4. Bestätigung der Vorbilder nach der Recherche. Erst danach Schritt 4.
