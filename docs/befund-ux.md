# Befund UX: Zentrale und Arbeitsplatz

Stand 22./23.11.2026, Nachtauftrag. Grundlage sind nur Rohspuren, keine Zusammenfassungen:
Jans eigene Nachrichten in den Claude-Chats (`~/.claude/projects/*/…jsonl`, 929 eigene Nachrichten, nur Jans Text),
die Aufträge (`shared/auftraege/erledigt`, 100 Stück), die gesendeten Meldungen (`shared/meldungen/gesendet`, 183),
die Freigaben (`shared/freigabe`, 29), das Log der Zentrale (`shared/telegram/logs/zentrale.log`, 16.10. bis 22.11.),
die Feedback-Fälle (`shared/feedback/data/meldungen.json`, 14) und das Journal von `arbeitsplatz.service`.
Grenzen: Das Log der Zentrale speichert keine Nachrichteninhalte und nicht jeden Knopf (Menü-Knöpfe fehlen ganz).
Im Journal des Arbeitsplatzes lassen sich Jans Abrufe nicht von den eigenen Rundgängen der Bau-Sitzungen trennen
(jede `/neu/<art>` genau 84-mal: das sind Rundgänge).

## 1. Was Jan gestört hat (wörtliche Belege)

| # | Störpunkt | Beleg (Datum, Jans Worte) |
|---|---|---|
| S1 | Zu viele Nachrichten, zu viel Information, Technik im Chat | 22.10.2026: „ziemlich viele informationen. ziemlich viele nachrichten (was will ich immer die stufen sehen, verstehe ich eh nicht. die erklärung zu den dokumenten ist ewig lang. … der verweis wo etwas abgelet urde und so komlett ega … backend bleibt backend you got me?“ |
| S2 | Hässliche Formatierung (Absender in Klammern) | 22.10.2026: „die formatierung (von welchem agent was kommt, sieht hässlich uas mit den klammern“ |
| S3 | Nachrichten zu technisch, nicht schlicht | 27.10.2026: „generell sollten alle Nachrichten weniger technisch sein. Es ist frontend, was für den einfach Nutzer verständlich und attraktiv aussehen sollte.“ |
| S4 | Veraltete Funktionen in der Zentrale: „Zu lang“, „Falscher Fokus“, „Rückmeldung geben“ | 22.11.2026: „Der tg zentrale soll entslpoppt werden. da sind tils noch veraltete funktinenne. drinnen (zu lang, falscher fpokus, rückmeldung geben)“ |
| S5 | Kein Noise, nur Signal, ruhig und aufgeräumt | 22.11.2026: „ausserdme soll die formatierung und inahlt aufgeräumt ruhig und auf reines signal reduziert werden. ichwill kein noise.“ und 22.11.2026: „wenig rauschen. Viel signal! … Lieber weniger und dafür sicher!“ |
| S6 | Knöpfe nur, wenn sinnvoll, sonst im Menü | 15.11.2026: „ich finde auch besser wenn es ohne viele knöpfe geht. ein knopf sollte wirklich nur da sein, wenn er sinnvoll ist oder ben versteckt in einem menü.“ Ähnlich 10.11.2026 (Lias App): „mit den knöpfen ist auch wieder zu starr … Willst du 1000 knöpfe entwicklen.“ |
| S7 | Oberfläche überladen, keine Hierarchie | 04.11.2026: „die nutzeroberfläche ist furchtbar leider. viel zu viele informationen und keine gute infromation der struktur. es braucht eine logische Hierarchie“; 27.10.2026: „Das sieht immernoch total überladen und unelegant aus.“ |
| S8 | Arbeitsplatz unübersichtlich, schlicht und ruhig gewünscht | 19.11.2026: „das sieht unüberischtlich aus. Lieber einfach das dokument einmal als gallerie und dann download button wür word und pdf (alles schlicht un ruhig)“ |
| S9 | Ebenen kaum unterscheidbar, Titel unruhig, das Wichtigste geht unter | 19.11.2026: „texte sollten angenehme größe haben und sinnvoll umbrechen siehe titel vom dokument, das ist unruhig. auch oben die ordnersturkure kaum zu unterscheiden vom rest und unten (das wichtigste auch kaum zu unterchdeine) vielleicht zarte rahmen oder shadows“ |
| S10 | Bedienelemente an der richtigen Stelle | 19.11.2026: „das Pluss und die drei punkte immer unten auf höher der Galerien … das plus dann eben in der kartei in der man sich befindet“ |
| S11 | Vorbild Apple, nicht das Rad neu erfinden | 22.11.2026: „eine solche plattform gibt es zu hauf und er kann sich tolle sachen davon übenehmen. UIUX apple ist zum beispiel ein gutes beispiel für was ich nice finde.“ |
| S12 | Prüfungsphase: Lernstoff muss als Lernformat greifbar sein | 22.11.2026: „langsam meine Prüfungsphase näher kommt und hier auch nochmal geguckt werden muss das alles an stoff und signal, was es gibt auch in lernformate für mcih gefbracht wird“ |
| S13 | Fehlermeldungen, die nur stören | 03.11.2026 (Vinted): „ich nicht die ganze zeit fhelrmeldungen bekomme“; 13.11.2026: „mein postfach meldet in der zentraler error.“ |
| S14 | Morgens keine Listen | 22.11.2026: „ich will keien liste bekommen man morgen fürh das nervt ohne ende“ |

Was die Zahlen dazu sagen:
- Ergebnisse der Agenten an Jan: Median 643 Zeichen, 27 von 65 über 800 Zeichen (Sprachregel: höchstens 800).
- Meldungen: uni 85 Stück, Median 331, längste 3552 Zeichen; posteingang 33, Median 278; holzbalkenscan 18,
  Median 1712. Die Sprachprüfung der Zentrale schreibt seit Wochen Warnungen ins Log (z. B. 22.11. 13:01
  „laenge: 1828 Zeichen, höchstens 800“), ändert aber nichts an der Nachricht.
- Rauschen in echten Meldungen: Statuszähler im Kopf („Wichtige Uni-Mails (8 neue geprüft):“, „[post] Wichtige
  Mails (3 geprüft, 1 vorgefiltert):“), Technikpräfixe („Lia, Agent vabali:“), Markdown-Sterne (`**Was es ist:**`),
  Dateipfade („Datei: /home/agent/agenten/lia/recherche/…docx“), Kosten und Prüfzahlen („Belege: 27 bestanden,
  0 durchgefallen, 0 ungeprüft (erste Prüfung: 27/2/0)“), viermal derselbe Satzbau („Termin zum Antippen: …
  Erinnerung 7 Tage, 1 Tag und 2 Std. vorher.“).
- Wie Jan wirklich korrigiert: 6-mal per Antwort auf ein Ergebnis, 11-mal „Ändern“ am Entwurf. Feedback-Knöpfe:
  6 Klicks in 4 Wochen (5× „Feedback schreiben“, 1× „Passt“, „Zu lang“ und „Falscher Fokus“ nie), zuletzt 09.11.

## 2. Inventar der Zentrale (`shared/telegram`, Stand vor dem Umbau)

Spalten: zuletzt benutzt (aus Log und Warteschlangen), Häufigkeit seit 16.10., typische Länge der Antwort,
verlangt eine Entscheidung von Jan.

### Befehle und Eingaben
| Eingabe | Zuletzt | Häufigkeit | Länge | Entscheidung |
|---|---|---|---|---|
| Text ohne Befehl → „An wen geht das?“ + Agent-Knöpfe | 18.11. | Hauptweg (42 Telegram-Aufträge gesamt) | 17 Zeichen | ja (Agent wählen) |
| `/uni Text`, `/<agent> Text` | 18.11. | in den 42 enthalten | Bestätigung 45 Zeichen | nein |
| `/unilern`, Modus „lernen“, Knopf „Modus wechseln“ | nie | 0 | – | – |
| Antwort auf ein Ergebnis (gleiche Sitzung) | 09.11. | 6 | – | nein |
| Antwort auf eine Meldung mit Knöpfen | – | 0 im Log | – | – |
| Dateien und Fotos | 19.11. | 7 Aufträge mit Dateien | Hinweis ~150 Zeichen | ja, wenn ohne Auftrag |
| `/verwerfen` | nie | 0 | – | – |
| `/pc`, `/weiter` | nie | 0 | Befehl zum Kopieren | – |
| `/start`, `/menue` (Panel) | nicht protokolliert | – | 4–6 Zeilen Kurzstand | – |
| `/hilfe` | nicht protokolliert | – | 13 Zeilen | – |
| `/status` | nicht protokolliert | – | 6 Zeilen, meist Nullen | – |
| `/verbrauch` | nicht protokolliert | – | 10–15 Zeilen | – |

### Knöpfe
| Knopf | Zuletzt | Häufigkeit | Entscheidung |
|---|---|---|---|
| Entwurf: Freigeben / Ändern / Ablehnen | 19.11. | 12 / 11 / 2 | ja, Kern der Zentrale |
| Ergebnis: Passt / Zu lang / Falscher Fokus / Feedback schreiben | 09.11. | 1 / 0 / 0 / 5 | verlangt Bewertung, die Jan nicht abgibt (S4) |
| Zu lang → Nur hier kürzer / Ab jetzt immer kürzer | nie | 0 | – |
| Feedback-Meldung: Übernehmen / Verwerfen / Stopp | 09.11. | 5 | ja |
| Rüdiger: Freischalten / Nicht freischalten | 20.11. | 2 | ja |
| Panel: Agent, Entwürfe (n), Verbrauch, Status, Hilfe, ↻ Aktualisieren, « Zurück | nicht protokolliert | – | nein |
| Erinnerung: „Entwürfe ansehen“ | – | – | ja |

### Nachrichtentypen an Jan
| Typ | Zuletzt | Häufigkeit | Typische Länge | Entscheidung |
|---|---|---|---|---|
| Ergebnis eines Auftrags (+ 4 Feedback-Knöpfe) | 19.11. | 65 | 643 (bis 1946) | nein |
| Bestätigung „Uni ist dran. Das Ergebnis kommt hierher.“ | 18.11. | ~45 | 45 | nein |
| Entwurf mit Freigeben/Ändern/Ablehnen | 19.11. | 29 | lang, wird bewusst nicht gekürzt | ja |
| Freigabe-Antwort „Freigegeben. Uni führt es jetzt aus und meldet sich.“ | 19.11. | 14 | 55 | nein |
| Ausgeführt / Hat nicht geklappt | 19.11. | 12 | 60–200 | nein |
| Unklar, ob ausgeführt | 05.11. | 2 | 190 | ja (selbst prüfen) |
| Entwürfe abgelaufen | 16.11. | 1 | 150–300 | nein |
| Erinnerung an offene Entwürfe | – | selten | 80 | ja |
| Meldung uni (Mails, neues Material, Fristen) | 22.11. | 85 | 331 (bis 3552) | selten |
| Meldung posteingang (wichtige Mails) | 22.11. | 33 | 278 (bis 1356) | selten |
| Meldung holzbalkenscan (Prüfstand-Läufe) | 07.11. | 18 | 1712 (bis 4214) | nein |
| Meldungen von Lias Agenten (recherche, vabali, theater, examen, unterricht) | 20.11. | 31 | 50–670 | nein |
| Feedback-Zusammenfassung mit Stopp | 09.11. | 14 | 660 (bis 887) | ja |
| Rüdiger-Freischaltung | 20.11. | 2 | 190 | ja |
| Stufe: Rechenzeit aufgebraucht / wieder frei | laufend | je Wechsel (8× limit seit 16.10.) | 90 | nein |
| Weitergabe wartet (Empfänger ohne Dienst) | 22.10. | 1 | 120 | nein |
| Datei-Hinweise (liegt bereit, zu groß, nicht geladen) | 05.11. | wenige | 80–160 | teils |
| Störung (ausfall@) | – | selten | 80 | nein |

## 3. Entscheidungen für den Umbau der Zentrale (Teil A)

Abgeleitet aus S1 bis S6 und dem Inventar. Code darf hinter einem Schalter bleiben, sichtbar ist es weg.
1. Feedback-Knöpfe unter Ergebnissen (Passt, Zu lang, Falscher Fokus, Feedback schreiben, Nur hier/Ab jetzt
   kürzer) weg (S4, 6 Klicks in 4 Wochen). Korrigiert wird so, wie Jan es tut: Antwort auf das Ergebnis.
2. Lernmodus (`/<agent>lern`, „Modus wechseln“), `/pc`, `/weiter`, `/verwerfen` aus Hilfe und Menü (nie benutzt).
3. Menü: nur Agenten und „Entwürfe“, wenn welche offen sind; Status, Verbrauch, Hilfe, Aktualisieren raus aus der
   ersten Ebene (S6). Kurzstand nur, wenn etwas zu tun ist.
4. Jede Nachricht der Zentrale: eine Zeile Kern, höchstens drei Punkte, höchstens eine Handlung, keine
   Höflichkeitsformeln („bitte“, „Danke“, „leider“), keine Wiederholung, keine Statusprosa
   („Das Ergebnis kommt hierher“, „und meldet sich“).
5. Meldungen der Agenten laufen durch einen Signal-Filter der Zentrale: Technikpräfixe, Zählerklammern,
   Markdown-Sterne und Pfade raus; sichtbar bleiben Kern und höchstens drei Punkte, der Rest steht zugeklappt
   darunter (Telegram „expandable blockquote“), damit nichts verloren geht (S5: „Lieber weniger und dafür sicher“).
6. Entwürfe zur Freigabe bleiben ungekürzt: freigegeben wird genau der gezeigte Text (harte Regel).

## 4. Vorher/nachher echter Nachrichten (Teil A)

(wird von der Sitzung für Teil A ergänzt)

## 5. Heuristik-Prüfung Arbeitsplatz nach Nielsen (Teil B)

(wird von der Sitzung für Teil B ergänzt)
