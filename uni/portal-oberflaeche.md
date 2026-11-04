# Portal-Oberfläche: Aufgaben und Befund (Schritt 1)

Stand 04.11.2026. Nichts umgebaut. Noch offen ist Jans Okay zu den Kernaufgaben und seine Antwort auf die Frage am Ende.
Schritt 2 (Messlatte) entfällt: Jan will keine Messung (04.11.). Es gibt keine Zielwerte, abgenommen wird nach Jans Eindruck.
Als nächster Schritt folgt 3 (Vorbilder).

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

## Offene Fragen an Jan

1. "Recherche-Maske": entschieden (Jan 04.11.): navigieren und nachfragen. Die Nachfrage kommt als eigener Vorschlag, weil
   sie Kosten und Agentenlogik berührt.
2. "Flexibilität": Was wolltest du zuletzt tun und konntest es nicht? Vorschlag: kombinierbare Filter, Suche, gespeicherte
   Ansichten, keine Einstellungsseite.
