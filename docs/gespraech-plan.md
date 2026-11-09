# Plan: Gespräch in die Mitte der Web-App (Lia)

Stand 09.11.2026. Nur Plan, nichts gebaut. Jans Entscheidungen 09.11.2026: alle fünf Empfehlungen aus Abschnitt 3
angenommen. Gebaut wird erst nach Lias Okay zur Skizze (Abschnitt 4).

Anlass: Lia nutzt die Web-App (shared/webapp, lia.meldro.de) kaum und chattet weiter in claude.ai („das Chatten
fehlt“). Auswertung ihrer 9 claude.ai-Chats seit 24.10. (lia/auswertung, Lauf luecken, 09.11.): 188 Runden, nur 15
gingen heute genauso in der Web-App, in 140 war das Hin und Her selbst wichtig. Lückenliste:
`lia/auswertung/STATUS.md`, Abschnitt „Zweiter Durchgang luecken“; Belege mit Zitaten nur auf dem Server
(`lia/auswertung/data/luecken/bericht.md`). Grenzen: Einschätzung von Claude, nicht mit Lia abgeglichen; die Hälfte
der Runden stammt aus einem Chat (Straftheorien, 93 Runden).

Grundgedanke (Jan und Claude, 09.11.): nicht den Chat in der rechten Spalte flicken, sondern den Aufbau drehen. Das
Gespräch kommt in die Mitte. Baum, Aufträge und Ergebnisansicht bleiben, denn der Ort mit Reihe, Reihenfrage,
Lerngruppe, Stunden und Material ist der Vorteil gegenüber claude.ai: Lia muss den Kontext nicht mehr von Chat zu
Chat kopieren (Befund in `docs/webapp-aufbau.md` 1).

Heute (Stand der Quellen):
- Spalte „Fragen“ rechts, 320 px. `lia/chat` antwortet ohne Werkzeuge, nimmt nur die letzten 6 Fragen am selben Ort
  mit (je gekürzt, `lia/chat/chatverlauf.py` `am_ort`), ein Ortswechsel setzt zurück. Jede claude-Sitzung wird nach
  dem Lauf gelöscht. Prompt verlangt kurze Antworten, nur fett, Listen, Links (schmale Spalte). Dateien nur
  PDF/Word/PowerPoint, Text bis 4.000 Zeichen.
- Schon gebaut und seit 04.11. live (Struktur pflegen, `shared/webapp/STATUS.md`): Lia kann Fach, Klasse, Reihe und
  Stunde selbst anlegen und die Reihenfrage ändern. Lias Chats stammen größtenteils aus der Zeit davor. Ob sie die
  Masken kennt, ist unbekannt.

---

## 1. Zielbild

### (a) Gespräch als Hauptansicht
- An jedem Ort (Reihe, Stunde, Projekt, Klasse, Fach) gibt es Gespräche. Das Gespräch steht in der Mitte, breit
  (Inhalt bis ca. 840 px), Antworten ungekürzt mit Überschriften und Tabellen.
- Mehrere benannte Gespräche je Ort („Reihenfrage finden“, „Stunde 3 Einstieg“), dazu Gespräche ohne Ort
  (Verwaltung, private Fragen, Regel R9 in `docs/webapp-aufbau.md`). Name schlägt Claude aus der ersten Frage vor,
  Lia kann ihn ändern.
- Voller Verlauf über Tage: Lia kommt am nächsten Tag zurück und macht weiter. Kein Zurücksetzen bei Ortswechsel,
  das Gespräch gehört zu seinem Ort.
- Eingabe: großes Feld für lange eingefügte Texte (eigene Planung, Textauszug), Fotos und Bildschirmfotos
  (JPG, PNG, HEIC als Foto vom iPhone), dazu wie heute PDF/Word/PowerPoint.
- Auf Wunsch „Was haben wir bisher?“: Zusammenfassung des Gesprächs (verworfene und gewählte Varianten).
- Kontext wie heute aus Python (Reihe, Reihenfrage, Lerngruppe, Stunden, Material-Titel, Lias Regeln), bei jeder
  Nachricht frisch, weil Lia die Reihenfrage unterwegs ändert.

### (b) Brücken zwischen Gespräch und Material
- **Textbaustein mit Kopier-Knopf:** Was Lia direkt verwenden will (Merksatz, Arbeitsauftrag, Reihenfrage,
  Fallbeispiel), steht in der Antwort als abgesetzter Block mit „Kopieren“. Verfeinern geht im Gespräch, ohne Auftrag
  und ohne neue Fassung.
- **„Als Reihenfrage übernehmen“** an einem Baustein, wenn das Gespräch an einer Reihe hängt (schreibt über die
  vorhandene Maske, mit Rückgängig).
- **„Daraus Auftrag machen“ mit dem Gespräch als Kontext:** Claude ordnet das Gespräch zu einem Auftragstext
  (was entschieden ist, was verworfen ist, Wunsch), Lia sieht ihn in der Vorlagengalerie, ändert ihn und schickt ab.
  Ort ist vorbelegt. Ein Gespräch startet nie selbst einen Auftrag (wie heute). Deckt auch „Auftrag vor dem Start
  ordnen“ ab.
- **Dateien fest an Reihe oder Stunde:** „Eigene Datei ablegen“ am Ort, ohne Auftrag (Lias Planung, Buchseite,
  Bewertungskriterien). Das Gespräch an diesem Ort kennt sie (Text über agentkit.textfassung, Fotos über Read),
  Lia muss sie nicht bei jeder Frage neu hochladen. Fester Hinweis: keine Schülerdaten.
- **Vom Material ins Gespräch:** „Darüber sprechen“ an einem Material öffnet ein Gespräch am selben Ort mit dieser
  Datei als Grundlage (deckt „Eigene Texte und Planungen prüfen“ mit ab).

### (c) Orte selbst anlegen
- Reihe anlegen und Reihenfrage ändern: gebaut (siehe oben). Offen: Lia davon wissen lassen, die Masken im Browser
  einmal prüfen (offener Punkt 11 der Web-App).
- Neu: **Projekt** als Ort für Vorhaben außerhalb einer Reihe (Projekttag, Theaterprojekt): eine Reihe der Art
  „Projekt“ in der Klasse oder auf Fach-Ebene, ohne Reihenfrage und ohne Pflicht-Stunden. Einzeltermine als Stunde
  mit Termin gibt es schon.
- „+ Gespräch“ ist auf jeder Ebene der schnellste Anfang; einen Ort braucht es dafür nicht.

### Was bleibt
Baum links (Fach › Klasse › Reihe › Stunde, „Heute“ oben), Aufträge mit Fassungen, Rückmeldung und final,
Ergebnisansicht mit Seitenbildern, Vorlagengalerie, Gestaltung Modernist, die drei Spalten (Jans Wahl 04.11.).

### Aufbau Desktop (Vorschlag, Skizze klärt es)
```
┌──────────────┬──────────────────────────────────────────┬──────────────────┐
│ Heute     (2)│ Ethik › 8 › Straftheorien                │ An diesem Ort    │
│              │ [Gespräche ▾ Reihenfrage finden] [+ Neu] │ Reihenfrage …  ✎ │
│ ETHIK        │                                          │ Gespräche (3)    │
│  8 · 26/27   │  Lia: …                                  │  Reihenfrage f.  │
│   Straftheo… │  Claude: … Tabelle …                     │  Stunde 3 Einst. │
│    Gespräche │   ┌ Baustein ──────────── [Kopieren] ┐   │ Material         │
│    Stunden   │   │ Ist Strafe Vergeltung …?          │   │  Reihenentwurf · │
│ DARST. SPIEL │   └───── [Als Reihenfrage übernehmen] ┘   │  Arbeitsblatt ·  │
│  Kurs 12     │                                          │ Eigene Dateien   │
│ Ohne Ort     │ [Text, Fotos, Dateien …        ] [Senden]│  Planung.pdf     │
│ Vorlagen     │ gründlich · Im Netz · Daraus Auftrag     │ + Datei ablegen  │
└──────────────┴──────────────────────────────────────────┴──────────────────┘
   260 px                  Gespräch (bis 840)                    320 px
```
Die Reihen-Ansicht (Stunden, Material) bleibt und ist einen Klick entfernt („Übersicht“ neben „Gespräche“). Rechts
steht, was das Gespräch kennt. Unter 1100 px wandert die rechte Spalte unter das Gespräch.

---

## 2. Die drei Teile im Einzelnen

Runden aus der Lückenliste (eine Runde kann mehrere Lücken haben, darum keine Summe).

| Teil | schließt Lücken (Runden) |
|---|---|
| (a) Gespräch | langes Gespräch mit vollem Verlauf (99), lange Antworten und Tabellen (59), Fotos und Screenshots (39), eigene Texte prüfen (22), mehrere Gespräche, ohne Ort (19), langen Text einfügen (7) |
| (b) Brücken | schnelle Textarbeit ohne neue Datei (39), Dateien dauerhaft ablegen (26), Auftrag vor dem Start ordnen (2); Fotos und eigene Texte zum Teil |
| (c) Orte | Reihen und Orte selbst anlegen (19), zum großen Teil schon gebaut |

### (a) Gespräch
`lia/chat`:
- Gespräch als eigenes Objekt: `data/gespraeche/<id>.json` (Name, Ort oder keiner, claude-Sitzung, Einträge,
  zuletzt). Schnittstelle neu: `gespraech_anlegen(name, ort)`, `gespraeche(ort=None)`, `umbenennen`,
  `frage_stellen(..., gespraech=id)`. Die alte Spalte läuft bis zum Umbau weiter.
- Gedächtnis über die claude-Sitzung (`agentkit.claude_lauf.laufen(..., lernsitzung=True)`, dann
  `sitzung_fortsetzen=<id>`) statt der letzten 6 Fragen (Entscheidung 3.1). Sitzungen der Gespräche werden nicht
  mehr nach jedem Lauf gelöscht, sondern mit dem Gespräch (Aufbewahrung, Entscheidung 3.5).
- Prompt: Länge nach Bedarf, Überschriften und Tabellen erlaubt, Bausteine als markierter Block (z. B. Codeblock
  `baustein`), Zusammenfassung auf Wunsch.
- Grenzen: Text bis ca. 60.000 Zeichen (claude -p lehnt Prompts über 128 KB ab, Befund lia/auswertung 09.11.),
  Fotos bis 5 je Nachricht. Fotos über Read (Entscheidung 3.2).
- Tests ohne Netz für Gesprächsablage, Fortsetzen, Aufräumen, Grenzen; ein echter Lauf mit drei Nachrichten über
  zwei Tage.

`shared/webapp`:
- Seiten `/gespraech/<id>` und `/gespraeche` (ohne Ort), Liste der Gespräche am Ort, „+ Gespräch“, umbenennen,
  löschen. Rahmen: Mitte = Gespräch, rechts „An diesem Ort“ (Entscheidung 3.3).
- Markdown-Anzeige um Überschriften, Tabellen und Baustein-Blöcke erweitern (eigene Funktion in logik.py, kein
  neues Paket), Kopier-Knopf als kleines Skript (Clipboard geht über HTTPS, lia.meldro.de hat es).
- Eingabe: großes Feld (wächst mit), Upload für Fotos (Prüfung in `logik.frage_dateien_pruefen` erweitern).
- Antwort weiter per htmx-Abfrage; „denkt nach …“ mit Startzeit.

Aufwand grob: groß. lia/chat 2 Sitzungen, Web-App 2 bis 3 Sitzungen.

### (b) Brücken
`shared/webapp`: Kopier-Knopf (mit (a)), „Als Reihenfrage übernehmen“ über `agentkit.strukturpflege`, „Daraus
Auftrag machen“ aus dem Gespräch, „Eigene Datei ablegen“ am Ort mit Liste und Entfernen, „Darüber sprechen“ an
Material. Wo die eigenen Dateien liegen, entscheidet der Bau (Vorschlag: `lia/instanz/ablage/<ort-id>/`, damit
auch lia/unterricht sie lesen kann; Zuordnung über die feste id aus agentkit.struktur).
`lia/chat`: eigene Dateien des Orts in den Kontext (Text gekürzt, Fotos über Read), neue Art „Auftrag ordnen“: ein
Lauf, der aus dem Gespräch einen Auftragstext schreibt (kein Werkzeug, nur Text zurück).
Hauptordner/agentkit: Ablage am Ort, falls lia/unterricht sie auch nutzen soll (Bedarf, nicht Teil dieses Plans).
Aufwand grob: mittel. Web-App 1 bis 2 Sitzungen, lia/chat 1.

### (c) Orte
`shared/webapp`: Hinweis an Lia auf die vorhandenen Masken, Browser-Prüfung (offener Punkt 11), Art „Projekt“.
`agentkit.struktur`/`strukturpflege` (Hauptordner): Art „Projekt“, falls die Datei sie noch nicht kennt.
`lia/chat`: Kontext für Projekte (ohne Reihenfrage).
Aufwand grob: klein.

---

## 3. Entscheidungen (Jan 09.11.2026: alle wie empfohlen)

1. **Gedächtnis: claude-Sitzung fortsetzen statt der letzten 6 Fragen.** `agentkit.claude_lauf` kann das schon
   (`lernsitzung`, `sitzung_fortsetzen`, `--resume`). Dafür darf lia/chat die Sitzungen der Gespräche nicht mehr
   nach jedem Lauf löschen. Vorteil: voller Verlauf ohne eigene Kürzung, frühere Nachrichten werden vom Zwischenspeicher
   billiger. Risiko: sehr lange Gespräche (93 Runden) stoßen an die Kontextgrenze; Ausweg „Zusammenfassen und in
   neuem Gespräch weiter“. Gegenmodell: Verlauf selbst in den Prompt legen (volle Kontrolle, aber jedes Mal neu
   bezahlt und an der 128-KB-Grenze). **Empfehlung: Sitzung fortsetzen. Jan 09.11.2026: ja.**
2. **Werkzeug Read für Fotos.** Heute läuft lia/chat ohne Werkzeuge. Fotos kann Claude nur über Read sehen. Read nur
   für den Ordner der Dateien dieses Gesprächs (Erlaubnis in `--settings`, Rest verboten), keine anderen Werkzeuge;
   ob die Grenze hält, vorher in agentkit testen (Hauptordner-Chat). Pages-Dateien nicht (kein lesbares Format ohne
   neues Paket), Lia exportiert als PDF. **Empfehlung: ja, mit Pfadgrenze und Test. Jan 09.11.2026: ja.**
3. **Aufbau „Desktop zuerst“, Modernist, drei Spalten bleiben, die Mitte wechselt.** Mitte = Gespräch, rechts „An
   diesem Ort“ (Reihenfrage, Gespräche, Material, eigene Dateien); die Reihen-Übersicht bleibt einen Klick entfernt.
   Alternative: Gespräch nur als eigener Reiter neben der Übersicht, rechte Spalte unverändert. **Empfehlung: erste
   Variante, in der Skizze beide zeigen und Lia wählen lassen. Jan 09.11.2026: okay.** Handy: wie bisher untereinander.
4. **Kosten je Gespräch auf Lias Kontingent.** Heute ca. 0,03 USD je kurzer Frage (Sonnet). Ein langes Gespräch kostet
   deutlich mehr, weil der Verlauf mitgeht; wie viel, wird im ersten echten Lauf gemessen, nicht geschätzt. Lias
   Läufe brauchen nach CLAUDE.md kein Okay von Jan; Qualität geht vor Kosten (Jan 29.10.). Vorschlag: Standard
   Sonnet, „gründlich“ (Opus) als Schalter je Gespräch statt je Frage; bei vollem Kontingent Hinweis mit Uhrzeit wie
   heute; keine Zähler für Lia. Jan sieht die Kosten im Leitstand. **Empfehlung: so, nach zwei Wochen Kosten ansehen. Jan 09.11.2026: okay.**
5. **Aufbewahrung.** Heute 30 Tage ab Frage. Für Gespräche über Tage: 30 Tage ab der letzten Nachricht, dann
   samt claude-Sitzung und Dateien gelöscht; Lia kann ein Gespräch vorher selbst löschen. Daten können Schülerbezug
   haben, darum kein „für immer“. **Empfehlung: 30 Tage ab letzter Nachricht. Jan 09.11.2026: okay.**

---

## 4. Vorgehen

1. **Skizze für Lia** (Klick-Attrappe, kein echter Claude-Lauf): Board im bestehenden Canvas
   (https://claude.ai/artifact/F8ysVSyr8TjGhFDcyNnejU) oder eigenes Artifact, Modernist, Lias echte Orte, Beispieltexte
   ohne Namen und ohne wörtliche Zitate aus ihren Chats. Ansichten: Gespräch an der Reihe mit Tabelle und Baustein,
   Liste der Gespräche, Gespräch ohne Ort, Foto anhängen, „Daraus Auftrag machen“, eigene Datei ablegen. Beide
   Varianten aus 3.3. Macht der shared/webapp-Chat.
2. **Mit Lia ansehen** (Jan leitet, ca. 20 Min., wie Test 30.10.): zuerst die Lückenliste in ihren Worten („Stimmt
   das? Was fehlt?“), dann 4 bis 5 Aufgaben aus ihren echten Mustern (z. B. „Such mit Claude eine Reihenfrage und
   übernimm sie“, „Zeig Claude ein Foto deiner Planung und frag, was er davon hält“, „Mach morgen im Gespräch von
   gestern weiter“). Notieren: was sie versteht, was sie experimentell findet, was sie nicht braucht. Kein Bau ohne
   ihr Okay.
3. **Bauen in kleinen Schritten, je Ordner im eigenen Chat**, je mit Tests, `./pruefen.sh` grün, Commit:
   1. lia/chat: Gespräch als Objekt, Sitzung fortsetzen, Aufräumen (Entscheidung 3.1, 3.5). Schnittstelle neu,
      alte Spalte läuft weiter.
   2. Hauptordner: Read mit Pfadgrenze in agentkit prüfen (3.2), Art „Projekt“ falls nötig.
   3. shared/webapp: Gesprächsansicht in der Mitte, Liste, ohne Ort, Markdown mit Tabellen, Kopier-Knopf, großes Feld.
      Neustart des Dienstes nur mit Jans Okay.
   4. lia/chat + shared/webapp: Fotos.
   5. shared/webapp + lia/chat: eigene Dateien am Ort, „Daraus Auftrag machen“ mit Gespräch, „Als Reihenfrage
      übernehmen“, „Darüber sprechen“.
   6. Nach zwei Wochen: Nutzung und Kosten ansehen, mit Lia kurz nachfragen.
4. Bedarf an andere Ordner geht als Punkt in die Haupt-STATUS. Punkt 36 dort sollte auf diesen Plan verweisen
   (nicht in diesem Commit, macht der Hauptordner-Chat).

---

## 5. Später (nicht in diesem Umbau)
- **Noten berechnen** (10 Runden): Python rechnet, Claude erklärt nur. Berührt Schülerdaten und Datenschutz, darum
  eigener Plan und Vorschlag an Jan (CLAUDE.md).
- **Verlaufsplan als Auftragsart** (2 Runden): neue Vorlage in der Galerie, Bedarf an lia/unterricht.
- **Stelle im Dokument markieren** (11 Runden): Anmerkung an einer Stelle der Vorschau und nur diese Stelle ändern;
  braucht Blocklagen vom Renderer (offener Punkt 4 der Web-App).
