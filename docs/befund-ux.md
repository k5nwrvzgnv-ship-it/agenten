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

Umgesetzt am 22./23.11.2026 in `shared/telegram` (Signal-Filter `logik.signal_html`, Regeln `logik.regelverstoesse`,
Tests `tests/test_regeln.py`). „Nachher“ ist das, was Jan ohne Aufklappen sieht; der Rest steht zugeklappt darunter
(`<blockquote expandable>`), nichts fällt weg. Die Nachher-Fassungen sind mit dem neuen Code aus den echten Dateien
erzeugt, nicht von Hand geschrieben. Zeichen: Länge des Agententexts vorher, sichtbarer Teil nachher.

| # | Quelle | Vorher | Nachher (sichtbar) |
|---|---|---|---|
| 1 | Meldung uni, 22.11. 13:01 (`meldungen/gesendet/20261122-130128-uni-3bcb7b`) | „Wichtige Uni-Mails (8 neue geprüft):“, dann 6 Unterpunkte, ein Absatz und viermal „Termin zum Antippen: … Erinnerung 7 Tage, 1 Tag und 2 Std. vorher.“ (1824 Zeichen, Log-Warnung „laenge“) | **Uni** / Wichtige Uni-Mails: / • noreply@hnee.de: Prüfungsanmeldungen bestätigt (22.11.). Es ist nichts zu tun, die Termine stehen im Stundenplan. (139 Zeichen) |
| 2 | Meldung recherche (Lia), 14.11. (`…20261114-133829-recherche-75af63`) | „Lia, Agent recherche: Webauftrag fertig: 20 von 39 Aussagen belegt, 19 unbelegt. Belege: 27 bestanden, 0 durchgefallen, 0 ungeprüft (erste Prüfung: 27/2/0). … Kosten 2.02 USD in 3 Läufen. Datei: /home/agent/agenten/lia/recherche/data/web/…docx“ (432) | **Recherche (Lia)** / Webauftrag fertig: 20 von 39 Aussagen belegt, 19 unbelegt. (68; Prüfzahlen und Kosten zugeklappt, Pfad weg) |
| 3 | Meldung posteingang, 22.11. 19:00 (`…20261122-190022-posteingang-1ab6ce`) | „[post] Wichtige Mails (3 geprüft, 1 vorgefiltert):“ + Mail-Zeile (274) | **Posteingang** / Wichtige Mails: / Bestellung/Versand \| PayPal: … Nur prüfen, ob die Zahlung von Jan stammt. (251; Präfix und Zähler weg) |
| 4 | Meldung holzbalkenscan, 07.11. (`…20261107-121623-holzbalkenscan-de22af`) | Kopfzeile, dann 40 Zeilen Messwerte und Vergleich mit der alten Fassung (3259) | **Holzbalkenscan** / Prüfstand holzbalkenscan, Lauf …, Fassung achse, … / pf-flau: ok (129; Messwerte zugeklappt) |
| 5 | Meldung uni, 03.11. (`…20261103-120341-uni-8af728`) | „Normen aufbereitet (9 neu):“ + 9 Zeilen mit Dateipfaden (928) | **Uni** / Normen aufbereitet: / 3 Normen als Punkte (314; die übrigen 6 zugeklappt) |
| 6 | Ergebnis uni, 11.11. (`auftraege/erledigt/20261111-225743-uni-e86e20`) | 1456 Zeichen Fließtext mit Liste, darunter 4 Knöpfe „Passt / Zu lang / Falscher Fokus / Feedback schreiben“ | **Uni** / Ich habe keinen frei herunterladbaren Datensatz gefunden, der Oberflächenbilder und CT-Scans derselben Stämme oder Bretter enthält … (190; Liste zugeklappt, keine Knöpfe; Antwort auf das Ergebnis setzt das Gespräch fort) |
| 7 | Texte der Zentrale (`logik.py`) | „Uni ist dran. Das Ergebnis kommt hierher.“ · „Freigegeben. Uni führt es jetzt aus und meldet sich.“ · „Einen Grund kann ich dir leider nicht nennen. Schick den Auftrag noch einmal, oder sieh am PC nach.“ · „Ich weiß nicht, ob das geklappt hat … Bitte prüf selbst, ob es angekommen ist. Ich wiederhole es nicht von allein.“ | „Uni ist dran.“ · „Freigegeben.“ · „Den Grund kenne ich nicht. Schick den Auftrag noch einmal.“ · „Unklar, ob das geklappt hat: … Angefangen, aber kein Ende gemeldet. Ich wiederhole es nicht. Prüf, ob es angekommen ist.“ |
| 8 | Menü `/start` und `/hilfe` | Menü: „Verbraucht: 6 % (5 Stunden), 1 % (7 Tage) / Entwürfe: 1 \| Aufträge in Arbeit: 0“ + Knöpfe Agenten, Entwürfe (0), Verbrauch, Status, Hilfe, ↻ Aktualisieren; nach Agent-Wahl „Modus wechseln: lernen“. Hilfe 13 Zeilen mit /unilern, /verwerfen, /pc, /weiter | Menü: „Zentrale“ + nur Agent-Knöpfe, „Entwürfe (n)“ nur wenn welche offen sind; Kurzstand nur bei aufgebrauchter Rechenzeit oder wartenden Dateien; nach Agent-Wahl „Was soll Uni tun?“. Hilfe 4 Zeilen (Aufträge, Text ohne Befehl, Antwort auf Ergebnis, Dateien) |

Unverändert und bewusst ungekürzt: Entwürfe zur Freigabe mit Freigeben/Ändern/Ablehnen (Fingerabdruck), Rüdiger, Lias
Zentrale. Still weiter angenommen, aber nirgends mehr genannt: `/unilern`, `/pc`, `/weiter`, `/verwerfen`, alte
Feedback-Knöpfe in früheren Nachrichten. Feedback-Knöpfe wieder einschalten: `logik.FEEDBACK_KNOEPFE = True`.

## 5. Heuristik-Prüfung Arbeitsplatz nach Nielsen (Teil B)

Geprüft am 22.11.2026 abends gegen den laufenden Dienst (127.0.0.1:8794, nur lesend), Desktop 1440 px und Handy
390 px, Bilder in `docs/arbeitsplatz-vorher-nachher/vorher-*.png`, axe-core 4.10.2 je Seite. Schwere nach Nielsen:
0 kein Problem, 1 kosmetisch, 2 klein, 3 groß, 4 Katastrophe. Maßstab zusätzlich Apples Human Interface Guidelines
(Klarheit, Zurückhaltung, Hierarchie).

| # | Heuristik | Seite | Befund | Schwere | Beleg |
|---|---|---|---|---|---|
| H1 | Sichtbarkeit des Systemstatus | Lernansichten | „Karten üben“ und „Übung ansehen“ zeigen auf `https://uni.meldro.de/modul/…`, seit 19.11. landet das im Arbeitsplatz: 404. Der Lernstand (64 Karten, 8 dran) ist vom Arbeitsplatz aus gar nicht sichtbar. | 4 | S12 |
| H1 | Sichtbarkeit des Systemstatus | Heute | „Läuft gerade“ steht dauernd in einer eigenen Spalte, auch als „Gerade läuft nichts.“; der Baum zeigt dasselbe schon („2 läuft“). | 2 | S5 |
| H2 | Übereinstimmung mit der echten Welt | alle | Oberfläche sagt „Ordner“, Heute aber „Orte“ und „Recherchen ohne Ort“. Zeilen nennen den Agenten („uni“, „dokumente“, „finance“) statt der Sache. | 2 | S1 („backend bleibt backend“), S3 |
| H2 | Übereinstimmung mit der echten Welt | Dokument | Kopf zeigt „Kosten bisher 81.79 USD“ und „Fassung 5“ vor dem Titel; das ist Technik, nicht Inhalt. | 2 | S1, S3 |
| H3 | Nutzerkontrolle und Freiheit | Handy, Baum | Auf Touch steht neben jedem Ordner dauerhaft ein Papierkorb (Löschen ohne Nachfrage, Rückgängig nur am Hinweis). Leicht danebengetippt. | 3 | S6 |
| H4 | Konsistenz und Standards | Ordner, Heute | Das „+“ ist blau gefüllt, auf dem Dokument ist „Senden“ blau: zwei Hauptfarben für zwei verschiedene Arten von Knopf. Apple: ein Akzent für die eine Haupthandlung. | 2 | S6, S11 |
| H4 | Konsistenz und Standards | Lernansichten | Das Portal sieht völlig anders aus (Schwarz, Großbuchstaben, harte Linien, eigener Baum „Uni“). | 3 | S7, S11 |
| H5 | Fehler vermeiden | Dokument | Titel trennt mitten im Wort („Fehls-tellenerkennung“, `hyphens: auto` bei Komposita). | 1 | S9 |
| H6 | Erkennen statt Erinnern | Heute | Prüfungsmodule, Karten und mündliche Übung sind nirgends verlinkt; man muss die Portal-Adresse kennen. | 3 | S12 |
| H7 | Flexibilität und Effizienz | Heute | Jede Zeile hat drei Zeilen Text (Titel, Agent · Zeit, Ordnerpfad) und rechts „Fassung n“: viel Lesestoff für eine Liste. | 2 | S5, S7 |
| H8 | Ästhetik und Minimalismus | Heute | „Zuletzt“ wiederholt die acht Einträge aus „Wartet auf dich“ eins zu eins; Heute ist 2770 px hoch, davon ein Drittel doppelt. | 3 | S5 („ichwill kein noise“), S7 („viel zu viele informationen“) |
| H8 | Ästhetik und Minimalismus | Heute | Kosten heute und die letzten sechs Läufe mit Dollarbeträgen stehen dauerhaft rechts. | 2 | S1, S5 |
| H8 | Ästhetik und Minimalismus | alle | Abschnittstitel (20 px fett) sind kaum kleiner als der Seitentitel (32 px) und so laut wie die Zeilen: Ebenen kaum unterscheidbar. | 3 | S9 („Ebenen kaum zu unterscheiden“), S7 („logische Hierarchie“) |
| H8 | Ästhetik und Minimalismus | Ordner, Dokument | Brotkrumen wiederholen den Seitentitel; auf dem Dokument bricht der lange Titel im Streifen zweizeilig um und steht direkt darunter noch einmal groß. | 2 | S9 („Titel unruhig“) |
| H8 | Ästhetik und Minimalismus | Heute | Der Brotkrumen-Streifen zeigt auf Heute nur „Heute“, darunter steht „Heute“ groß. | 1 | S5 |
| H8 | Ästhetik und Minimalismus | Dokument | „Klick auf die Seite zeigt alle zum Durchblättern.“ erklärt, was das Bild schon zeigt. | 1 | S1 („die erklärung … ist ewig lang“) |
| H8 | Ästhetik und Minimalismus | Dokument | Das Rückmeldungsfeld steht als eigene Karte mit Rahmen und Schatten gleichrangig neben dem Dokument; „Rückmeldung zu dieser Datei“ im Menü klingt nach dem alten Feedback-Knopf. | 2 | S4 („Rückmeldung geben“ veraltet), S6 |
| H8 | Ästhetik und Minimalismus | Ordner | Unterordner als Aufzählung mit hohlen Kreisen, gleich groß wie Dokumente: keine Unterscheidung zwischen Ordner und Inhalt. | 2 | S9, S7 |
| H9 | Fehler erkennen und beheben | Heute | „Hat nicht geklappt“ in Rot auf Weiß erreicht nur 4,0:1 (axe: color-contrast, serious). | 2 | S13 |
| H9 | Fehler erkennen und beheben | Lernansichten | Portal zeigt Technik als Hinweis („ELEVENLABS_AGENT_URL in uni/portal/.env“). Liegt in `uni/`, hier nicht geändert. | 2 | S3, S13 |
| H10 | Hilfe und Dokumentation | Heute | Klappe „Ohne Ordner“ erklärt Ziehen und Menü in einem Satz; passt, bleibt. | 0 | – |
| – | Zugänglichkeit (axe) | Ordner, Betrachter, Karten | Seitentitel bekommt per `direkt.js` `role="button"`, damit hat die Seite keine Überschrift erster Ebene (axe: aria-allowed-role, page-has-heading-one); Betrachter und Karten üben ohne h1. | 2 | – |

Umgesetzt (Teil B, 22./23.11.2026), je Befund:
- H1, H6, H4 Lernen: Der Arbeitsplatz reicht `/modul/…` an das Uni-Portal (127.0.0.1:8793) durch und zeigt es in
  seinem eigenen ruhigen Aussehen (Lernkarten, Bewerten, mündliche Übung gehen weiter über das Portal, fsrs bleibt in
  `uni/.venv`). Heute hat oben den Abschnitt „Lernen“ mit jedem Prüfungsmodul („Karten üben“, „Mündlich“), der
  Modul-Ordner und seine Elternordner zeigen dasselbe. `ansichten.PORTAL` zeigt auf den Arbeitsplatz selbst.
- H8 Heute: „Zuletzt“ ohne die Einträge aus „Wartet auf dich“, höchstens acht; „Läuft gerade“ nur, wenn etwas läuft;
  Kosten in einer zugeklappten Klappe „Verbrauch“ ganz unten; Heute ist einspaltig; „Orte“ heißt „Ordner“ und steht
  nur auf schmalen Bildschirmen (breit steht der Baum daneben).
- H7, H2 Zeilen: eine leise Zeile unter dem Titel (Art · Ordner · Zeit), kein Agent, „Fassung n“ nur noch im Verlauf;
  rechts nur, was zu tun ist (Läuft, Final, Hat nicht geklappt).
- H8 Hierarchie: Seitentitel 30 px, Abschnittstitel klein und leise (13 px), Zeilen 15 px, Metadaten 12 px; mehr
  Abstand zwischen Abschnitten; Brotkrumen ohne die aktuelle Seite (steht als Titel darunter), auf Heute kein Streifen.
- H4, H3: „+“ nicht mehr blau, blau bleibt allein die Haupthandlung einer Seite (Senden, Weiter); auf Touch stehen
  „+“ und Löschen im Baum nur am offenen Ordner.
- H2, H8, H5 Dokument: Kosten aus dem Kopf (stehen im Verlauf je Fassung), keine Erklärsätze, Titel ohne
  automatische Silbentrennung. Das Rückmeldungsfeld ist ein schlichtes Eingabefeld ohne Karte und ohne Überschrift
  („Was soll anders werden?“), Route und Funktion gleich; im Menü heißt es „Zu dieser Datei etwas ändern“.
- H8 Ordner: Unterordner als Zeilen mit „›“, ohne Kreise.
- H9, axe: Rot für Text dunkler (Kontrast ab 4,5:1), Titel bleibt `h1` (das Umbenennen sitzt auf einem Knopf im Titel),
  Betrachter mit Überschrift.
