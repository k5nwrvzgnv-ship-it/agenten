# Benutzerfreundlichkeit der Telegram-Zentralen (Jan und Lia)

Stand 21.10.2026. Untersucht: `shared/telegram/zentrale.py` (Jan, @Agentenzentralebot) und
`shared/telegram/portal.py` (Lia, @zentraleliabot, seit 21.10. 13:41 in Betrieb).

## Belegarten

| Kürzel | Bedeutung |
|---|---|
| **[Log]** | Gezählt aus `shared/telegram/logs/zentrale.log` (16.–21.10.), Warteschlangen und `gemeldet.json`. Nur Zahlen und Felder wie Agent oder Status, keine Texte. |
| **[Code]** | Abgeleitet aus dem Quelltext: Inspektion durch mich, keine Beobachtung echter Nutzer. |
| **[Beob.]** | Selbst beobachtet: Lias erste Nachricht „hallo“ über getUpdates (nur der Text, vor dem Start des Dienstes). |
| **[Verm.]** | Vermutung, nicht belegt. Mit dem Testplan prüfen. |

**Kein Telegram-Export.** Darum fehlt Schritt 2 im eigentlichen Sinn. Wiederkehrende Fragen, unbeantwortete
Nachrichten und Abbrüche lassen sich nur grob aus den Logs ablesen. Die Logs enthalten keine Texte, und unbekannte
Befehle werden nicht protokolliert.

## 1. Nutzergruppen und Aufgaben

| Gruppe | Belegt | Fehlt (bitte ergänzen) |
|---|---|---|
| **Jan**: Entwickler und einziger Nutzer seiner Zentrale | Einsteiger bei Git und Linux, diktiert per Handy-Tastatur, nur Text (CLAUDE.md, STATUS.md). Kennt die Befehle, weil er sie gebaut hat. | – |
| **Lia**: einzige Nutzerin ihrer Zentrale | Lehrerin für Theater/Darstellendes Spiel und Philosophie/Ethik. Nutzt nur Telegram, keine Befehle (dein Auftrag). | Wie vertraut ist sie mit Technik? Handy oder Desktop? Wann nutzt sie die Zentrale (Pause, abends)? Welche Antwortzeit erwartet sie? Weiß sie, dass alles erst Platzhalter ist? |

Weitere Gruppen gibt es nicht. Beide Bots reagieren nur auf je eine Chat-ID.

Typische Aufgaben:

| Nr. | Wer | Aufgabe |
|---|---|---|
| A1 | Lia | Erstkontakt: Bot öffnen und verstehen, was er kann |
| A2 | Lia | Material anfordern (Fach, Klasse, Thema, Dauer) |
| A3 | Lia | Eine Frage stellen oder einfach etwas schreiben (Freitext) |
| A4 | Lia | Eine Datei mitschicken, zum Beispiel eine Vorlage [Verm.: kommt bei Lehrkräften oft vor] |
| A5 | Jan | Auftrag geben (`/uni …` oder Freitext mit Agent-Auswahl) |
| A6 | Jan | Entwurf freigeben, ablehnen oder ändern |
| A7 | Jan | Auf ein Ergebnis antworten und in derselben Sitzung weitermachen |
| A8 | Jan | Datei an einen Auftrag hängen |

## 2. Nutzungsdaten (statt Export)

- **Jan [Log]:** 6 erledigte Aufträge in 6 Tagen. Alle gingen an uni, alle im Modus erledigen, alle per Befehl
  oder Freitext. Ergebnis nach 1,8 Minuten (Median), höchstens 2,6 Minuten. Die Aufträge waren 11 bis 610 Zeichen lang.
- **Ungenutzte Bereiche bei Jan [Log]:**
  - 0 Antworten auf Ergebnisse (Feld `bezug` leer), also kein Fortsetzen in derselben Sitzung
  - 0 Aufträge im Modus lernen
  - 0 Dateien
  - 0 Meldungen mit Knöpfen (13 Meldungen, alle von uni)
  - 0 Sitzungen am PC
  - 0 offene oder erledigte Entwürfe (im Log steht eine Freigabe, die Datei fehlt, vermutlich Testdaten)
- **Stabilität [Log]:** 10 Starts der Zentrale und 14 Netzwerkfehler beim Abholen neuer Nachrichten in 6 Tagen.
  Telegram liefert danach nach, ob dabei Nachrichten verloren gingen, ist offen [Verm.: eher nicht].
- **Lia [Log/Beob.]:**
  - Ihr erstes /start und „hallo“ kamen, bevor der Bot lief. Beim ersten Abruf lag nichts vor, beim zweiten nur „hallo“.
  - Seit dem Start: 0 Aufträge, 0 Knopfdrücke im Log.
  - Ob sie die Rückfrage zu „hallo“ gesehen hat, ist nicht protokolliert (siehe B10).

## 3. Cognitive Walkthrough (Sicht eines Neulings) und Nielsen-Heuristiken

Schweregrade nach Nielsen: 0 kein Problem, 1 kosmetisch, 2 klein, 3 groß, 4 Katastrophe.
H1–H10 sind die zehn Heuristiken (H1 Sichtbarkeit des Status, H2 Übereinstimmung mit der realen Welt,
H3 Kontrolle und Freiheit, H4 Konsistenz, H5 Fehler vermeiden, H6 Erkennen statt Erinnern,
H7 Flexibilität, H8 schlichtes Design, H9 aus Fehlern herausfinden, H10 Hilfe).

**Walkthrough-Fragen je Schritt:**
- (1) Will der Neuling das Richtige tun?
- (2) Sieht er die richtige Aktion?
- (3) Verbindet er sie mit seinem Ziel?
- (4) Sieht er danach, dass es vorangeht?

### Lias Zentrale

| Nr. | Befund | Aufgabe, Walkthrough | Heuristik | Grad | Beleg |
|---|---|---|---|---|---|
| B1 | Ein Gruß wird zum Auftrag. Auf „hallo“ antwortet der Bot „Nachricht: hallo – So abschicken?“ und zeigt kein Menü. Unklar bleibt, wohin es geht und was dann passiert. | A1 (1, 3) | H2, H5 | **3** | [Beob.] Lia schrieb „hallo“; [Code] `text_empfangen` → `text_eingang` |
| B2 | Alles ist Platzhalter, aber das steht nirgends vor dem Absenden. Lia beschreibt ihr Material ausführlich und bekommt dann „kommt bald“. | A2, A3 (4) | H2, H1 | **3** | [Code] `lia/unterricht/agent.py`, `BEGRUESSUNG`; Wirkung [Verm.] |
| B3 | Unter der Nachfrage („Was brauchst du? …“) gibt es weder Menü noch „Abbrechen“. Wer es sich anders überlegt, muss weit nach oben scrollen. | A2 (2) | H3 | 2 | [Code] `senden(..., None)` bei der Nachfrage |
| B4 | Das Ergebnis nennt nicht, zu welchem Auftrag es gehört. Bei zwei Aufträgen kurz nacheinander ist die Zuordnung unklar. | A2, A3 (4) | H1, H6 | 2 | [Code] `ergebnis_text` (Jans Zentrale zitiert den Auftrag, Lias nicht) |
| B5 | Fehlschlag: „Sag Jan bitte Bescheid.“ Jan erfährt davon nicht von selbst (ausfall@ meldet nur abgestürzte Dienste, keine fehlgeschlagenen Aufträge). | alle (4) | H9 | 2 | [Code] `FEHLGESCHLAGEN`, `agentkit/ausfall.py` |
| B6 | Dateien werden abgelehnt. Auch Sprachnachrichten und Sticker bekommen „Dateien kann ich noch nicht annehmen“. | A4 (3) | H2, H9 | 2 | [Code] `datei_empfangen` fängt alles ab, was kein Text ist |
| B7 | Nach „Ist unterwegs“ kommt bis zum Ergebnis nichts, kein Tippen-Hinweis. Bei Jans Agent dauerte das 1,8 bis 2,6 Minuten. | A2 (4) | H1 | 2 | [Log] Dauer bei Jan; [Code] kein `ChatAction` |
| B8 | „Meine Woche“ fragt „So abschicken?“, obwohl es nichts zu prüfen gibt. Ein Tipp mehr. | A1 (3) | H8, H7 | 1 | [Code] `menue_gewaehlt` |
| B9 | Jede Nachricht trägt drei Menüknöpfe, der Verlauf wird voll davon. Ältere Menüs bleiben anklickbar (unschädlich). | alle | H8 | 1 | [Code] `senden(markup=MENUE)` |
| B10 | Nicht messbar: Das Log zählt weder empfangene Texte noch Knopfdrücke noch Abbrüche. Abbrüche lassen sich darum nicht nachweisen. | – | (Betrieb) | 2 | [Code] `text_empfangen` und `knopf` loggen nichts |

### Jans Zentrale

| Nr. | Befund | Aufgabe, Walkthrough | Heuristik | Grad | Beleg |
|---|---|---|---|---|---|
| B11 | Die Agent-Auswahl bietet dokumente, posteingang und einkauf an, die es noch nicht gibt. Der Bot meldet „weitergegeben“, aber kein Dienst holt den Auftrag ab. Er bleibt still liegen. | A5 (4) | H1, H5 | **3** | [Code] `AGENTEN`, `agent_starten`; auf dem Server nur `uni.service`, kein `agent.py` in den drei Ordnern |
| B12 | Antworten auf ein Ergebnis setzt die Sitzung fort: eine versteckte Mechanik, bisher 0 Mal genutzt. | A7 (2) | H6, H10 | 2 | [Log] `bezug` = 0; docs/lia-architektur.md Abschnitt 6 |
| B13 | Es gibt kein Befehlsmenü in Telegram (`set_my_commands` fehlt). Jan muss sich `/unilern`, `/pc` und `/weiter` merken oder die lange Hilfe lesen. | A5, A7 (2) | H6 | 2 | [Code] |
| B14 | Nach „Ändern“ wird die nächste Nachricht immer zum Änderungswunsch, auch wenn Jan etwas anderes meinte (Moduswechsel ohne Anzeige und ohne Abbrechen). | A6 (4) | H3, H5 | 2 | [Code] `chat_data["aendern"]` in `text_ohne_befehl` |
| B15 | Dateien ohne Befehl warten und hängen sich an den nächsten Auftrag, auch an einen späteren an einen anderen Agenten. | A8 (4) | H5 | 2 | [Code] `auftrag_anlegen` → `eingang.wartende()`; genutzt [Log]: 0 |
| B16 | Text ohne Befehl geht immer im Modus erledigen, lernen gibt es nur per Befehl. | A5 | H7 | 1 | [Code] `agent_fragen` |
| B17 | 10 Neustarts und 14 Netzwerkfehler in 6 Tagen. Für Jan nicht sichtbar, solange Telegram nachliefert. | alle | H1 | 1 | [Log]; Folge [Verm.] |

## 4. Testplan für 5 Personen (Durchführung: Jan)

**Ziel:** Lias Zentrale mit Neulingen prüfen. Jans Zentrale hat einen einzigen Nutzer, der sie gebaut hat. Ein Test mit
Fremden sagt darüber wenig aus. Dafür reicht ein Selbsttest von A6 bis A8 mit Strichliste.

**Vorbereitung**
- **Test-Bot:** Die echten Bots reagieren nur auf eine Chat-ID. Für den Test einen eigenen Test-Bot mit eigener
  Instanz (`lia-test/shared`) anlegen. Entweder bekommt jede Testperson eine eigene Instanz, oder die Chat-ID wird vor
  jeder Sitzung getauscht. Das baue ich nach deinem Okay.
- **Testpersonen:** Noch offen. Kriterien: nutzen Telegram oder WhatsApp, kennen das System nicht, möglichst 3 von 5
  Lehrkräfte oder Menschen aus Lias Umfeld, gemischt in der Technikvertrautheit.
- **Ablauf:** Am eigenen Handy der Testperson, 20 Minuten. Lautes Denken. Du liest die Aufgaben vor, hilfst nicht und
  notierst. Vorher den Test-Bot zurücksetzen (Chat löschen, Warteschlangen leeren).

**Aufgaben** (ohne Knopfnamen formuliert, damit nichts verraten wird)

| Nr. | Aufgabe für die Testperson | Erfolg, wenn | Zeitlimit |
|---|---|---|---|
| T1 | „Du hast diesen Bot bekommen. Finde heraus, wofür er gut ist.“ | Sie nennt mindestens 2 der 3 Funktionen | 2 min |
| T2 | „Bestelle ein Arbeitsblatt zum kategorischen Imperativ für Klasse 10, 45 Minuten.“ | „Ist unterwegs“ erscheint, und der Text enthält Thema und Klasse | 3 min |
| T3 | „Du hast dich vertan und willst statt Material lieber eine Frage stellen.“ (während T2, vor dem Abschicken) | Frage-Modus erreicht, nichts Falsches abgeschickt | 2 min |
| T4 | „Frag den Bot, was du diese Woche vorhast.“ | Auftrag Woche abgeschickt | 1 min |
| T5 | „Schick dem Bot dieses Bild und sag, was er damit machen soll.“ | Sie versteht die Absage und weiß, was sie stattdessen tun kann | 2 min |
| T6 | „Welche Antwort gehört zu welcher Anfrage?“ (nach T2 und T4) | Richtige Zuordnung beider Antworten | 1 min |

**Messgrößen je Aufgabe** (Protokollbogen: eine Zeile je Person und Aufgabe)
- **Erfolg:** ja, mit Hilfe oder nein. Ein Abbruch oder das Zeitlimit zählt als nein.
- **Zeit:** Stoppuhr vom Ende des Vorlesens bis zum Erfolg oder Abbruch, in Sekunden.
- **Fehler:** Anzahl falscher Tipps (falscher Knopf, Verwerfen statt Abschicken, Text an falscher Stelle), Anzahl der
  Rückfragen an dich, Stellen, an denen sie zögert (über 5 s ohne Aktion).
- **Zitate:** wörtlich mitschreiben, vor allem Verwirrung und Erwartungen. Nur eigene Notizen, keine Aufnahme ohne Einwilligung.

**Auswertung**
- Erfolgsquote je Aufgabe (x/5), Median der Zeit, Summe der Fehler.
- Jeden beobachteten Fehler einem Befund aus Abschnitt 3 zuordnen oder als neuen Befund aufnehmen.
- Damit ist er belegt (Beobachtung) statt nur aus dem Code abgeleitet.
- Zielwerte (Vorschlag):
  - T1, T2, T4 bei mindestens 4 von 5 ohne Hilfe
  - T2 unter 90 Sekunden (Median)
  - SUS mindestens 68 (Durchschnitt üblicher Systeme)

**SUS-Fragebogen** (direkt nach den Aufgaben, 1 = stimme gar nicht zu … 5 = stimme voll zu)

1. Ich denke, dass ich dieses System gerne häufig benutzen würde.
2. Ich fand das System unnötig komplex.
3. Ich fand das System einfach zu benutzen.
4. Ich glaube, ich würde die Hilfe einer technisch versierten Person benötigen, um das System benutzen zu können.
5. Ich fand, die verschiedenen Funktionen in diesem System waren gut integriert.
6. Ich denke, das System enthielt zu viele Inkonsistenzen.
7. Ich kann mir vorstellen, dass die meisten Menschen den Umgang mit diesem System sehr schnell lernen.
8. Ich fand das System sehr umständlich zu nutzen.
9. Ich fühlte mich bei der Benutzung des Systems sehr sicher.
10. Ich musste eine Menge lernen, bevor ich anfangen konnte, mit diesem System zu arbeiten.

**Punkte:**
- Ungerade Fragen: Antwort − 1.
- Gerade Fragen: 5 − Antwort.
- Summe × 2,5 ergibt 0–100.
- Ab 5 Personen den Mittelwert bilden und die Spannweite angeben. Bei 5 Personen ist das nur ein Richtwert.

**Zum Schluss:** Zwei offene Fragen, „Was hat dich am meisten gestört?“ und „Wofür würdest du den Bot wirklich nutzen?“.

## 5. Maßnahmen (priorisiert)

| Prio | Maßnahme | Befund | Aufwand |
|---|---|---|---|
| 1 | Freitext ohne Menü nicht direkt als Auftrag behandeln. Erst „Was soll ich damit tun?“ mit den drei Menüknöpfen und „Nur so“ zeigen. Kurze Grüße mit Begrüßung und Menü beantworten. | B1 (3) | klein |
| 2 | In der Begrüßung und unter den Knöpfen ehrlich sagen: „Im Aufbau – ich sammle deine Wünsche, Antworten kommen später.“ | B2 (3) | sehr klein |
| 3 | Jans Agent-Auswahl auf Agenten mit Dienst beschränken. Wenn kein Dienst da ist, sagen: „Agent X gibt es noch nicht.“ | B11 (3) | klein |
| 4 | Knopf „Abbrechen“ unter jeder Nachfrage, ebenso unter Jans „Was soll geändert werden?“ | B3, B14 (2) | klein |
| 5 | Ergebnis mit Bezug („Zu deiner Anfrage ‚Arbeitsblatt Kant …‘:“) | B4 (2) | sehr klein |
| 6 | Fehlgeschlagene Aufträge an Jan melden, Lia bekommt „Jan ist informiert“. | B5 (2) | klein |
| 7 | Zählendes Log ohne Inhalte (Text empfangen, Knopf, Abbruch, Verwerfen), damit Abbrüche messbar werden | B10 (2) | sehr klein |
| 8 | Testplan durchführen (Test-Bot zuerst), danach die Reihenfolge der Punkte 9 bis 12 neu festlegen | alle | mittel |
| 9 | „Tippt …“-Anzeige während ein Auftrag läuft, sobald echte Agenten länger brauchen | B7 (2) | klein |
| 10 | Telegram-Befehlsmenü für Jan (`set_my_commands`), Hinweis „Antworte auf diese Nachricht, um weiterzumachen“ unter Ergebnissen | B12, B13 (2) | sehr klein |
| 11 | Dateien: Lias Absage nach Art unterscheiden (Sprachnachricht, Sticker). Bei Jan wartende Dateien beim nächsten Auftrag zur Bestätigung anzeigen. | B6, B15 (2) | klein |
| 12 | „Meine Woche“ ohne Rückfrage abschicken, Menü nur an der letzten Nachricht | B8, B9 (1) | sehr klein |
