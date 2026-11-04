# Portal für den Uni-Agenten: Entscheidungsgrundlage

Stand 04.11.2026. Nichts gebaut, keine Pakete, Dienste oder Caddy-Änderungen. Bauen erst nach Jans Okay.

Kennzeichnung: **[B]** belegt (Fundstelle oder Messung), **[S]** Schätzung, **[O]** offen.
Pfade relativ zum Hauptordner. Inhalte aus Mails, Skripten und Aufträgen stehen hier bewusst nicht.

## Ergebnis in fünf Sätzen

1. Ein Portal löst das Lernproblem nur zum Teil: Das Lernsystem lief nie, und das liegt nicht an der fehlenden Oberfläche.
2. Lias App wird nicht kopiert und nicht zweimal betrieben. 41 ihrer 67 Routen sind Schulstruktur. Empfehlung: kleine neue App in `uni/portal/`, die agentkit nutzt und Gestaltung sowie wenige Schutzfunktionen übernimmt.
3. Erster Durchstich ist die Prüfungsseite Holzschutz: Stand je Thema, Karten üben, Lücken, Probeprüfung auswerten. Karten üben kostet kein Kontingent.
4. Ein Web-Editor, eine Recherche-Oberfläche und Live-Sprache im Portal werden vorerst nicht gebaut.
5. Abbruchkriterium: Wird in den ersten 14 Tagen an weniger als 10 Tagen geübt, stoppt der Portalbau.

## 1. Warum wurde das Lernsystem nicht genutzt?

Befund **[B]**:
- `uni-lernen.service` und `.timer` fehlen in `~/.config/systemd/user/`. `uni/logs/uni-lernen.log` hat 0 Byte.
- Im Modulordner liegt keine `zustand.json` und keine `verlauf.jsonl`, obwohl `uni/data/lernen/holzschutz/karten.json` 64 Karten enthält. Bewertet wurde also keine Karte. (Die STATUS nennt 61 Karten aus dem ersten Lauf.)
- Der Dienst wartet auf Punkt 6 der Haupt-STATUS (Zentrale soll Klick-Aufträge still abschließen, offen seit 20.10.).
- Von 27 Uni-Aufträgen seit 16.10. lief keiner im Modus `lernen`. `/unilern` wurde also nie genutzt.
- Das ElevenLabs-Paket liegt seit 29.10. fertig da. Kein Auftrag enthält ein Transkript daraus. Ob Jan es im Web ausprobiert hat, sehe ich nicht **[O]**.

Deutung:
- Die technische Ursache ist klein und vom Portal unabhängig: ein offener Punkt in der Zentrale und ein nicht eingerichteter Dienst.
- Ob auch Zeit oder Antrieb fehlen, geben die Daten nicht her **[O]**. Das kann nur Jan beantworten, und die Probe unten misst es.
- Ein Portal ist ein Ort, zu dem man selbst gehen muss. Die Telegram-Abfrage um 18 Uhr kommt von allein. Für den täglichen Anstoß ist das Portal also eher schlechter **[S]**.

Was das Portal für das Lernen wirklich bringt **[S]**: Überblick über Themen und Lücken, größere Bildkarten für die Pilzbestimmung, längere Antworten, Auswertung von Probeprüfungen.

Folge: **Der Anstoß bleibt in Telegram.** Das Portal teilt sich mit Telegram denselben Lernstand (`lernmodell.py`).

## 2. Was Jan wirklich macht

Grundlage **[B]**: `shared/auftraege/erledigt/*-uni-*.json` (27 Aufträge, 16.10. bis 04.11.), `shared/verbrauch/laeufe.jsonl` (487 Läufe, 92,71 USD Gegenwert, davon 84,69 Aufträgen zugeordnet), Jans Nachrichten aus den Chats in diesem Ordner. Die Zuordnung zu den Arten stammt von mir. Es sind nur 19 Tage, das ist eine kleine Stichprobe.

| Art | Aufträge | USD | Passt Telegram? |
|---|---|---:|---|
| Mail entwerfen | 6 | 1,60 | ja, bleibt dort |
| Frage zu Kurs oder Abgabe | 6 | 3,49 | ja |
| Lernblatt aus Vorlesung | 5 | 5,34 | geht, das PDF kommt als Anhang |
| Termin | 3 | 0,92 | ja, bleibt dort |
| Exposé (eine Kette) | 5 | 71,42 | nein, siehe unten |
| Kurzrecherche mit Blatt | 2 | 1,94 | geht |
| Lernen, Simulation | 0 | 0 | nie genutzt |

Was daran auffällt **[B]**:
- Das Exposé verursacht 77 % der Kosten und hat Telegram gesprengt: Etwa acht Chats drehen sich darum, 4 der 27 Aufträge entstanden im Chat statt in Telegram. PDF-Kommentare wurden am 03.11. im Chat abgeschrieben.
- Rückmeldung zum Lauf fehlt: Eine Nachricht lautete nur „hallo?“. Der Exposé-Lauf dauerte 382 Minuten und endete als „fehlgeschlagen“, obwohl danach Fassungen entstanden.
- Zwei kleine Aufträge warteten etwa 195 Minuten. Die Ursache habe ich nicht geprüft **[O]**.

Der Portalbedarf ist damit bei Arbeiten belegt und beim Lernen nur erklärt, nicht belegt.

### Objektmodell (OOUX)

| Objekt | Kernattribute | Beziehungen | Aktionen |
|---|---|---|---|
| Modul | Name, Kurzform, Teile | hat 1–n Kurse, 1–n Prüfungsleistungen | öffnen |
| Kurs | Moodle-Name, Hochschule (HNEE, BFH) | gehört zu 1 Modul; hat Material, Transkripte | Material öffnen, fragen |
| Prüfungsleistung | Form, Termin, Anmeldestand, Gewicht | gehört zu 1 Modul; hat Themen oder 1 Arbeit | Stand ansehen |
| Thema | Score, Signale, Quellen, Lernstand | hat Karten; taucht in Probeprüfungen auf | üben, Lücke melden |
| Karte | Frage, Antwort, Quelle, Bild, FSRS-Stand | gehört zu 1 Thema | bewerten |
| Probeprüfung | Datum, Prüfer (KI oder Mensch), Rubrik, Transkript | prüft 1 Prüfungsleistung; deckt Lücken auf | auswerten, Lücken übernehmen |
| Arbeit | Art (Exposé, Bericht), Gruppe, Betreuung, Frist | hat Fassungen, Quellen, KI-Nachweis | Fassung ansehen, Rückmeldung geben |
| Fassung | Nummer, von wem, Dateien | gehört zu 1 Arbeit | herunterladen, kommentiert hochladen, final setzen |
| Quelle | Beleg, Status, Norm oder Literatur | gestützt auf Recherche; zitiert in Arbeit | Fundstelle öffnen |

Bewusst kein Objekt: Mail, Termin (bleiben in Telegram), Fach, Klasse, Reihe, Stunde (Lias Welt).

Wichtiger Unterschied zu Lia: Modul und Prüfungsleistung müssen getrennt sein. Ein Modul kann aus zwei Kursen bestehen und eine einzige gemeinsame Prüfung haben (Holzschutz: IHS und SHB; Modulhandbuch S. 41–43 laut `pruefungsplan.json`).

## 3. Was lässt sich übernehmen?

### Inventar `shared/webapp/` **[B]**

Routen gezählt aus den `@app`-Zeilen in `app.py` (67 Routen, 2.451 Zeilen).

| Gruppe | Routen | Fundstelle | Urteil |
|---|---:|---|---|
| Fach, Klasse, Reihe, Stunde, Stundenplan, Ausfall, Pflege | 41 | `app.py:401`–`1615` | nicht übernehmen, Schulmodell |
| Auftrag, Ergebnis, Fassung, Datei, Seitenbetrachter, Entwurf | 18 | `app.py:1769`–`2405` | Ablauf als Muster; `variante`, `stunde`, `reihe` entfallen |
| Rahmen: Heute, Fragen, Vorlagen, Ich | 8 | `app.py:281`–`347`, `1632`–`1723` | Muster, neu schreiben |

| Baustein | Fundstelle | Urteil |
|---|---|---|
| CSS, Schrift, htmx mit Prüfsummen | `shared/webapp/statisch/` | kopieren |
| Seitengerüst | `vorlagen/basis.html` | kopieren und anpassen |
| Sicherheitskopfzeilen, Formularschutz | `app.py:169`, `logik.py:893`, `903`, `907` | kopieren, später nach agentkit |
| Sichere Dateipfade | `dateien.py` `sicher()` | kopieren; `agent_ordner()` passt nicht |
| Textbausteine, Ketten, Verlauf, Betrachter | `logik.py:73`, `218`, `478`, `711` | einzeln prüfen, teils Lias Wortwahl |
| Markdown-Anzeige | `logik.py:1569` | kopieren |
| Warteschlangen, Fassungen, Freigabe | `agentkit.auftraege`, `fassungen`, `freigabe` | unverändert nutzen |
| Chat-Muster: Datei, Pfad-Unit, Oneshot | `lia/chat/schnittstelle.py`, `lia/chat/systemd/` | Muster; Code ist an Reihen gebunden |
| Tests | `shared/webapp/tests/` (3.681 Zeilen) | nur als Vorbild |

Feste Bindungen an Lia, die einen Zweitbetrieb verhindern **[B]**:
- `app.py:119`, `123`: Instanz und Chat-Ordner liegen unter `lia/`.
- `app.py:1783`: Dienstname ist fest `lia-<agent>`.
- `dateien.py:20`: Agent-Ordner ist `instanz.parent/<agent>`. Bei Jan läge die Instanz in `shared/`, der Agent aber in `uni/`.
- `app.py:488`, `679`: `sp.VON_LIA`.

### Entscheidung

| Weg | Vorteil | Nachteil | Aufwand **[S]** |
|---|---|---|---|
| A. Dieselbe App zweimal, per Umgebungsvariablen | ein Code | Umbau im laufenden Betrieb, Schulmodell bleibt, Risiko für Lia hoch | hoch |
| B. App kopieren und ausdünnen | schneller Start | etwa 60 % löschen, Sicherheitskorrekturen laufen auseinander | mittel, dauerhaft teuer |
| C. Gemeinsamen Kern herauslösen | sauber | `shared/webapp` hatte seit 30.10. 82 Commits, der Kern wäre ein bewegliches Ziel; Lia ist Risikoträgerin | hoch |
| **D. Neue kleine App, Bausteine gezielt übernehmen** | Lia unberührt, eigenes Modell | wenig Doppelcode | 2–4 Chat-Sitzungen für den Durchstich |

**Empfehlung D.** Der Kern kann später in den Hauptordner-Chat wandern, wenn beide Apps stabil zeigen, was wirklich gemeinsam ist. Auch das Vorgehen schont Lia: Kein Commit in `shared/webapp/`.

Pakete: FastAPI, Uvicorn, Jinja2, python-multipart in `uni/.venv`, gleiche Versionen wie bei Lia. Dafür braucht es Jans Okay.

## 4. Laufmodell und Speicher

Problem **[B]**: `shared/agentkit/claude_lauf.py:404` sperrt je Agent-Ordner über `data/lauf.lock`, ohne Warten. Läuft eine Recherche in `uni/`, schlägt jeder weitere Claude-Lauf aus `uni/` sofort fehl. Dazu sind über alle Agenten und auch für Lia nur 2 Plätze frei, in der Sparstufe 1 (`shared/einstellungen.toml`, `[parallel]`).

Drei Wege durchs Portal:

| Tätigkeit | Weg | Claude? |
|---|---|---|
| Karten, Themenstand, Dateien ansehen | direkt im Web-Dienst | nein, kein Kontingent, keine Sperre |
| Große Aufträge (Arbeit, Recherche, Lernblatt) | `shared/auftraege/` an `uni`, wie heute | ja, wartet in der Schlange, Stand wird angezeigt |
| Schnelle Fragen, Probeprüfung auswerten | eigener Agent `uni/portal/` mit eigenem `data/lauf.lock`, Pfad-Unit wie `lia-chat` | ja, läuft auch während einer Recherche |

Risiko **[S]**: Eine Recherche belegt einen der 2 Plätze. Portal-Fragen können dann mit Lia konkurrieren. Das Portal sollte deshalb bei knappem Kontingent klar „wartet“ sagen und nichts automatisch starten.

Speicherbudget **[B]** gemessen am 04.11. vormittags: 7.941 MB gesamt, etwa 4.070 MB verfügbar, kein Swap, jeder `claude`-Prozess etwa 280 MB, sieben davon liefen (`ps`). Lias Web-App: 52 MB Spitze, Grenze 300 MB.

| Dienst | Grenze **[S]** | Anmerkung |
|---|---|---|
| `uni-portal` (Web) | `MemoryMax=200M` | Lia braucht 52 MB; Seitenbilder gesondert messen |
| `uni-portal-frage` (Oneshot) | `MemoryMax=500M` | wie `lia-chat` |
| `uni.service` | bleibt 1G | unverändert |
| `uni-transkript` | bleibt 3G, nachts | läuft nur nachts, tagsüber nicht einplanen |

Kein Ton auf dem Server: Die Transkription schafft Faktor 1,7 bis 2,5 und braucht bis 1,2 GB (`uni/STATUS.md`), `ffmpeg` fehlt.

## 5. Arbeiten: gültige Fassung, Kommentare, KI-Regeln

### Wo liegt die gültige Fassung?

Heute **[B]**: Claude schreibt `expose.json`, der Renderer baut docx und PDF, Jan kommentiert im PDF. `agentkit.fassungen` kennt eigene Fassungen und `grundlage()`, aber `uni/agent.py` und `uni/expose.py` nutzen es nicht.

Gefahr daraus **[B]**: Ändert Jan die Word-Datei selbst, kennt der nächste Lauf nur die alte `expose.json` und überschreibt seine Änderung.

Vorschlag:
- **Solange der Agent schreibt, gilt die JSON-Fassung.** Docx und PDF sind daraus gebaut.
- **Kommentierte PDF oder Word hochladen = Rückmeldung.** Das geht technisch schon (`kurse.kommentare_block`), nur ein Echttest mit Anhang fehlt.
- **Wird die Word-Datei selbst geändert, wechselt die Führung.** Sie wird „eigene Fassung“ über `agentkit.fassungen`, der Agent arbeitet ab dann auf ihrem Text und baut die JSON nicht blind neu. Das braucht Code in `uni/`.
- **Final gesetzte Fassung ist für den Agenten tabu**, bis Jan eine neue Runde startet.
- **Kein Web-Editor.** Word kann Kommentare, Änderungsverfolgung und Formatvorlage bereits, und die Gruppe arbeitet ohnehin außerhalb.
- **Gruppe:** Felix und Henri bekommen keinen Zugang. Ihre Beiträge kommen als Datei oder Transkript herein. Jan bestätigt das oder entscheidet anders **[O]**.

### Was die HNEE verlangt **[B]**

Quelle: Richtlinie vom 15.10.2025, in `uni/data/kurse/Forschungsprojekt 1 - Wissenschaftliches Arbeiten/03 28. April/`, verbindlich auch für Studierende.

- Abschnitt 2 und 5: KI-Inhalte sind zu kennzeichnen, der Einsatz ist zu dokumentieren. Lehrende informieren je Veranstaltung über die zulässige Nutzung.
- Abschnitt 3: „Die Verarbeitung vertraulicher, personenbezogener oder urheberrechtlich geschützter Daten in öffentlich zugängliche KI-Systeme ist unzulässig.“
- Erklärungsformular: `Erklaerung_zur_Verwendung_KI_Tools_HNEE_202410 de.docx` (Werkzeug, URL, Datum, Arbeitsschritt, Verwendung, betroffene Teile, Kommentar). Es liegt im Kurs „Spezielle Themen der Holzphysik“; ob es für jede Arbeit gilt, ist offen **[O]**.

Folgen:
- **KI-Nachweis je Arbeit:** Das Portal kann aus Aufträgen und `laeufe.jsonl` einen Entwurf des Formulars füllen. Das ist kleiner Aufwand und schützt Jan real. Die Bewertung und Unterschrift bleiben bei ihm.
- **Offen [O]:** Ob das bezahlte Claude-Konto oder ElevenLabs als „öffentlich zugängliches KI-System“ im Sinn von Abschnitt 3 gilt, steht nicht in der Richtlinie. Das berührt Normen, Skripte und die Wissensdateien des ElevenLabs-Pakets. Ich kann das nicht entscheiden; es muss Jan einordnen oder bei der HNEE klären.
- **Exposé:** Der Versand an den Betreuer war für den 04.11. geplant. Eine KI-Kennzeichnung ist in der STATUS nicht erwähnt. Vor dem Versand prüfen.

## 6. Mündliche Prüfung: Technikprobe (nichts davon ist ausgeführt)

Kernerkenntnis: **Stufe 1 braucht das Portal nicht.** Der ElevenLabs-Agent läuft in dessen eigener Oberfläche. Das Portal muss nur das Transkript annehmen und auswerten. So bleibt auch Lias strenge Sicherheitsrichtlinie (`default-src 'self'`) als Vorbild für das Portal unverändert gültig.

| Weg | Was bekannt ist | Was zu messen ist |
|---|---|---|
| ElevenLabs-Agent | Daten bleiben standardmäßig 2 Jahre, Frist einstellbar (Doku); Voice Clone ab Starter (Preisseite); etwa 0,08 USD/min laut Drittquellen, Sprachmodell extra **[S]** | Wartezeit, Kosten für 40 min, Fachbegriffe, Transkript-Export |
| Spracherkennung im Browser | laut MDN nicht in allen wichtigen Browsern verfügbar; in Chrome geht der Ton an einen Webdienst | Safari und Chrome am Mac, Fachbegriffe, Abbrüche bei langen Antworten |
| Aufnehmen, dann auswerten | Serverlast wie oben: 15 min Vortrag etwa 25–40 min Rechenzeit **[S]** | Nur für Vortragsprobe tauglich, nicht für Gespräch; Tonformat ohne `ffmpeg` prüfen |

Messvorschrift: je Weg dieselben 10 Prüfungsfragen, 5 Antworten mit Fachbegriffen (etwa Gebrauchsklasse, Hausschwamm).
- Zeit vom Ende meiner Antwort bis zum Beginn der Frage, gestoppt, Median und schlechtester Wert.
- Falsch erkannte Fachbegriffe in Prozent.
- Tatsächliche Kosten je 40 Minuten.

Annahmeschwelle **[S]**: Median unter 2 Sekunden, schlechtester Wert unter 5, höchstens 10 % falsche Fachbegriffe, höchstens 5 USD je Sitzung. Abweichungen entscheidet Jan.

Empfehlung: zuerst nur ElevenLabs testen. Das Paket ist fertig. Die anderen beiden Wege nur, wenn es durchfällt.

## 7. Absicherung

| Was | Gefahr | Maßnahme |
|---|---|---|
| Moodle-Token, HNEE-Kennwort in `uni/.env` | Fehler im Web-Dienst legt sie offen | Web-Dienst lädt `uni/.env` nicht; Abrufe bleiben bei `agent.py` |
| Mails (`data/mails`, `data/mailauftraege`) | im Portal unnötig, hochsensibel | nie anzeigen; das Portal liest nur eine feste Positivliste von Ordnern |
| Normen-PDFs, Skripte | Weitergabe geschützter Inhalte | nur nach Anmeldung, keine öffentlichen Links, kein Zwischenspeichern im Browser |
| Anmeldung | fremder Zugriff | Beginn nur per SSH-Tunnel auf Unix-Socket, wie der Leitstand, kein offener Port |
| Datei-Upload | Schadinhalt, Pfadtricks | Endungen und Größe begrenzen, `dateien.sicher`, Textfassung nur im Agenten |
| Formulare | fremde Seiten lösen Aktionen aus | Origin und Token wie bei Lia |
| Nach außen handeln | Portal wird Hintertür | keine Mails, Abgaben oder Käufe im Portal, Freigabe bleibt in Telegram |
| Gleicher Linux-Benutzer | Fehler in Lias App könnte Jans Daten lesen und umgekehrt | bleibt bestehen **[B]**; bekannt, Trennung wäre größerer Umbau |

Handy oder Zugriff ohne Tunnel erst danach: dann Caddy mit eigenem Block durch Jan, weil das Root braucht, und eine stärkere Anmeldung als Lias Übergangspasswort.

**Fund, unabhängig vom Portal [B]:** In einem Chat dieses Ordners (Datei beginnt mit `6d08c4`, unter `~/.claude/projects/`) steht Jans HNEE-Kennwort im Klartext. Der Ordner ist nur für `agent` lesbar. Die nächtliche Sicherung schiebt laut ihrer Unit das Agenten-Repo nach GitHub, dieser Ordner liegt außerhalb davon. Empfehlung: Kennwort ändern und danach in `uni/.env` nachtragen. Der Wert steht bewusst nirgends in diesem Plan.

## 8. Erster Durchstich, rückwärts vom Januar geplant

Prüfung: Vortrag mit mündlicher Prüfung, 100 %, „Januar 2027, ungefähr“ **[B]** `pruefungsplan.json`. Der genaue Termin und die Anmeldung sind offen **[O]**.

| Zeitraum **[S]** | Schritt | Ort |
|---|---|---|
| bis 08.11. | Termin klären; Punkt 6 der Zentrale; `uni-lernen` einrichten; Telegram-Abfrage startet | Hauptordner, Jan |
| bis 08.11. | ElevenLabs einmal 10 Minuten nach Messvorschrift testen | Jan |
| 09.–22.11. | Durchstich: Prüfungsseite Holzschutz | `uni/portal/` |
| 23.11. | Entscheidung über Weiterbau anhand der Nutzung | Jan |
| Anfang Dez. | Probeprüfung 1 mit Mitstudierendem, Lücken in Karten | Gruppe |
| Dez. | Zweiter Durchstich: Arbeit mit Fassungen und KI-Nachweis | `uni/portal/` |
| Mitte Jan. | Probeprüfung 2 | Gruppe |

Inhalt des Durchstichs:
1. Modulseite: Prüfungsform, Termin, Themen mit Score und Lernstand, Liste „fehlt“ aus `pruefungsplan.json`.
2. Karten üben im Browser, große Bilder, vier Knöpfe, über `lernmodell.py`, dieselbe `verlauf.jsonl` wie Telegram.
3. Probeprüfung auswerten: Transkript hochladen, Auswertung gegen eine Rubrik, Vorschläge für neue oder fällige Karten. Rubrik aus Modulhandbuch und Dozentenhinweisen, Jan bestätigt sie einmal.
4. Keine weiteren Module, aber die Daten liegen je Modul, damit andere folgen können.

Lücken, die das Portal nicht schließt **[B]** (`pruefungsplan.json`, „fehlt“): Ablauf der Prüfung, Gedächtnisprotokolle, IHS-Folien ab Vorlesung 2, Mitschriften verpasster Termine, Fotos von Holzproben. Sie sind wichtiger als jede Oberfläche und nur durch Nachfragen zu bekommen. Jan wollte am 24.10. vorerst keine Mails an Dozenten; Kommilitonen wären der erste Weg.

### Was nicht gebaut wird

- Web-Editor für Berichte: Word bleibt.
- Oberfläche für die Recherche-Pipeline: Sie läuft wenige Male und kostet viel. Sichtbar sind nur Stand und Bericht, ab dem zweiten Durchstich.
- Live-Sprache im Portal, solange ElevenLabs reicht.
- Mails, Termine, Freigaben: bleiben in Telegram.
- Gesamtsuche über alle Kurse: Machbar mit SQLite FTS5 (auf dem Server vorhanden), aber erst bei belegtem Bedarf.
- Zugänge für die Gruppe, Handy-Oberfläche, Änderungen an Lias App.

## 9. Was das Ergebnis unabhängig belegt

Die Schwellen sind meine Vorschläge **[S]**. Jans Ausgangsmaßstab vom 20.10.: Prüfungsbedingungen, nicht Informiertheit.

| Aussage | Prüfstein | Schwelle | Zeitpunkt |
|---|---|---|---|
| Das System wird genutzt | `verlauf.jsonl` | mindestens 10 von 14 Tagen geübt, sonst Portalbau stoppen | 23.11. |
| Das Gedächtnismodell passt | FSRS-Vorhersage gegen tatsächliche Trefferquote | Abweichung höchstens 10 Prozentpunkte | nach 300 Bewertungen |
| Jan kann es unter Prüfungsbedingungen | Mitstudierender prüft 30 Minuten mit Rubrik, ohne KI-Auswertung zu sehen | Note 1 bis 3 auf der Rubrik | Anfang Dez., Mitte Jan. |
| Die KI-Bewertung taugt | gleiche Probe von KI und Mensch getrennt bewertet | Abstand höchstens eine Notenstufe | Anfang Dez. |
| Der Plan traf die Prüfung | Gedächtnisprotokoll direkt nach der Prüfung gegen Themenliste | mindestens 80 % der Fragen im Plan | Prüfungstag |
| Das Ziel ist erreicht | Note der Prüfenden | bestanden; die Note selbst ist nur ein einzelner Datenpunkt | Januar |
| Arbeiten taugen | Rückmeldung des Betreuers | keine falsche Quelle oder Tatsache beanstandet | nach jeder Abgabe |
| Belege stimmen | Crossref und wörtlicher Zitatabgleich (`recherche.py`) | 100 % der Literatur der finalen Fassung | vor jeder Abgabe |
| Lia bleibt unberührt | `git diff` auf `shared/webapp` leer, ihre Tests grün, Dienst aktiv | exakt das | jeder Commit |
| Zugang ist dicht | Aufruf von außen, `ss -ltn` | kein offener Port im Tunnelbetrieb; mit Caddy 401 ohne Anmeldung | vor jedem Echtbetrieb |
| Tempo, Speicher, Kosten | Stoppuhr, `MemoryPeak`, `laeufe.jsonl` | Karte unter 0,5 s, Web unter 200 MB, Karten 0 USD | Abnahme Durchstich |

Schwäche: Die Prüfung ist ein einziger Durchlauf, und Üben wirkt nicht getrennt von Jans übrigem Lernen. Ursache und Wirkung lassen sich damit nicht beweisen. Die Probeprüfungen sind der beste verfügbare Ersatz.

## 10. Jans Entscheidungen (04.11.2026)

Diese Punkte gehen den Abschnitten oben vor, wo sie abweichen.

1. Bisher fehlte die Zeit. Ab jetzt will Jan mehr lernen und das Portal dafür nutzen. Das Portal kommt deshalb zuerst. Die Telegram-Abfrage (`uni-lernen`, Punkt 6 der Zentrale) ist keine Voraussetzung mehr und bleibt optional für später. Die Termine in Abschnitt 8 sind nur noch eine grobe Reihenfolge.
2. Jan ist angemeldet, der Termin liegt irgendwann im Januar. Keine Mahnungen dazu.
3. Kein menschlicher Probeprüfer vorerst. Die mündliche Übung läuft über ElevenLabs. Damit fehlt der Vergleich „Mensch gegen KI“ aus Abschnitt 9; als unabhängiger Prüfstein bleiben Gedächtnisprotokoll und Note.
4. KI-Richtlinie: Jan hat das eingeordnet, kein Thema mehr. KI-Nachweis und offene Fragen aus Abschnitt 5 entfallen.
5. Zugriff vom Mac, ohne Tunnel, über eine eigene Subdomain mit HTTPS und Passwort (Caddy basicauth wie `lia.meldro.de`). Damit gilt die Tunnel-Zeile aus Abschnitt 7 nicht. Mikrofon im Browser setzt HTTPS voraus und wäre damit möglich.
6. Schriftverkehr mit Kontaktpersonen des Forschungsprojekts soll im Portal sichtbar sein. Das geht über Abschnitt 7 und Abschnitt 8 („Mails bleiben in Telegram“) hinaus, aber nur für einen Auszug: Der Agent schreibt die Mails der eingetragenen Personen nach `data/projekte/<projekt>/schriftverkehr.json`. `data/mails`, `data/mailauftraege` und das Postfach bleiben für das Portal gesperrt, Mails geschrieben und freigegeben werden weiter über Telegram.

Stand Subdomain **[B]**: `uni.meldro.de` zeigt am 04.11. auf 185.181.104.242, nicht auf diesen Server (84.247.188.205). DNS muss Jan bei INWX setzen. Port 8793 auf 127.0.0.1 ist frei.

## Quellen außerhalb des Repos

- [MDN: SpeechRecognition](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition)
- [ElevenLabs: Aufbewahrung von Gesprächsdaten](https://elevenlabs.io/docs/agents-platform/customization/privacy/retention)
- [ElevenLabs: Preise](https://elevenlabs.io/pricing), Agentenpreise stehen separat unter elevenlabs.io/pricing/agents und wurden nicht geprüft
- Minutenpreis aus Drittquelle, zum Beispiel [HappyRobot](https://www.happyrobot.ai/hub/elevenlabs-pricing); vor einer Entscheidung beim Anbieter prüfen
