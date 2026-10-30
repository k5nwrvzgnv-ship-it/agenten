# Web-App für Lia: Aufbau neu, Desktop zuerst

Stand 30.10.2026. Planung, nichts gebaut. Gebaut wird erst nach Lias Test (Abschnitt 6) und Jans Okay.
Ersetzt für die Oberfläche `docs/webapp-plan.md` 4.1 und 4.2 (Handy zuerst, fünf Bereiche unten). Alles andere dort
(Rahmen, Anmeldung, Mandanten, Bedrohungsmodell, Technik) gilt weiter.
Wireframes: Boards „Desktop“ und „Handy-Prüfung“ im Canvas https://claude.ai/artifact/F8ysVSyr8TjGhFDcyNnejU.
Abdeckung als Tabelle: `shared/webapp/data/ia/abdeckung.csv` (nicht im Repo, nur Dateinamen und Titel).

Jans Vorgaben (30.10.): Lia arbeitet meist am PC. Gerüst Fach → Klasse → Reihe → Stunde, auf jeder Ebene Aufträge,
die über Verbesserungen zu einem finalen Material werden. Ein fester Claude-Chat für schnelle Fragen.
Dokumentvorlagen verschiedener Art mit einfacher Oberfläche. Die Chips oben und „Unterricht →“ sind unlogisch.

---

## 1. Befund

Gelesen (nur Namen und Metadaten, keine Inhalte von Schülerarbeiten): Lias Ablage `lia/unterricht/data/wissen/eingang/`
(217 Dateien) und `lia/theater/data/entpackt/klasse/k11/` (100), die 27 anonymisierten Chats (Titel, Länge,
Zusammenfassung), `lia/instanz` (8 Aufträge, 1 Entwurf), `reihen.toml`, `theater.toml`, `examen.toml`, die
`profil.toml`, `beispiele.py`, Renderer-Arten, Lias Wünsche in den STATUS-Dateien.

**So ordnet Lia selbst.**
- Ethik: `Ethik / 7. Klasse / Reihe Tierethik / ABs | Powerpoints`. Fach, Klasse und Reihe sind Ordner.
- Darstellendes Spiel: `k11 / Kompositionsmethoden ABs`, `Grundlagen Körper ABs`, `Proben + Feedbackphase`,
  `Halbjahres- und Stoffplanung`. Kurs statt Klasse, Einheit statt Reihe, sonst gleich.
- **Die Stunde ist kein Ordner.** Sie steckt nur als Nummer im Dateinamen (`AB3.1`, `Freundschaft_Stunde2`,
  `Präsentation5`). 100 von 317 Dateien tragen so eine Nummer, und sie verrutscht
  (`Gerechtigkeit_Stunde_4_bzw_5`, `Stunde_3_7.12` und `Stunde_3_7.15`). Im Theaterkurs hat keine Datei eine
  Stundennummer.
- Unterhalb der Reihe sortiert Lia nach Art (ABs, Powerpoints, Bewertung LEK), nicht nach Stunde.
- 35 Dateien sind **Varianten** desselben Blatts: `_Türkisch`, `_einfach/_normal/_schwer`, `Level 1–3`,
  `_Textentlastung`, `_Hilfe`. Das sind keine neuen Materialien und keine Fassungen.
- Fassungen benennt sie im Dateinamen: `_final`, `_Final (1)`, `_neu`, `_Original`, `[Automatisch gespeichert]`.
  „Final“ ist also ihr eigenes Wort.
- Was keiner Klasse gehört, liegt auf Fach-Ebene: RLP, Operatoren, Kompetenzraster, Fachseminar-Notizen,
  UB-Entwürfe und Feedback (Ordner `UBs+Feedback`, `Seminar`). Ein Ethik-UB lag im DS-Ordner.

**So arbeitet sie mit Ergebnissen.** Ihre zwei jüngsten Aufträge (93e29e, 03b145) sind eine heruntergeladene
Fassung, in Word kommentiert und wieder hochgeladen („Bitte übernehme die Änderungswünsche“). Das ist ihr
Feedbackweg, nicht Knöpfe. Heute entsteht dabei ein neuer, unverbundener Auftrag (offener Punkt 8 der Web-App).

**Was der Chat leisten muss** (27 Chats, 1.143 Nachrichten von Lia):
- Schnelle Fragen mit 2–4 Nachrichten: „Definition Standbild, 2 Sätze“, Aristoteles-Regel für Drittklässler,
  Platz pro Zeile auf einem Arbeitsblatt, Gehalt, ein Formularfeld. Ort ist egal oder ergibt sich.
- Lange Planungsgespräche zu einer Reihe (Aristoteles/Helfen 617 Nachrichten, Partikularismus 510, Walzer 196,
  Strafe 160). Zwei davon beginnen mit „Kurzbeschreibung für den neuen Chat (zum Reinkopieren)“: **Lia trägt den
  Kontext der Reihe heute von Hand von Chat zu Chat.** Genau das soll der Ort in der App übernehmen.
- Verwaltung (Bewerbung, Teilzeitantrag, Examenstermin, Einladung zum UB): 6 Chats ohne Unterrichtsort.
- Ein Chat heißt „Attendance or roster check“ (Inhalt im Export leer): Namenslisten sind ein reales Risiko.

**Was fehlt bzw. offen ist.**
- Es gibt keine Stunden in irgendeiner Datei der Agenten (`reihen.toml` kennt Reihen, nicht Stunden).
- Fachname: Lias Ordner und `profil.toml` sagen „Darstellendes Spiel“/„DS“, die App sagt „Theater“ (Jan 30.10.).
  Vorschlag: „Darstellendes Spiel“ wie bei Lia, Kurzform DS. **Jan fragen.**
- Ein Chat erwähnt eine 12. DS-Klasse; in keiner Datei. Für die Notentabelle (ef0a90) ist die Klasse unbekannt.
- **Offene Frage an Jan:** Welche Programme nutzt Lia am PC (Word oder Pages, OneDrive/iCloud, Lernraum/Moodle,
  IServ)? Davon hängt ab, ob „In Word öffnen“ oder „Herunterladen“ der Hauptweg zum Bearbeiten ist. Die Ablage
  enthält `.pages`-Dateien: vermutlich Mac mit Pages und Word.

### 1.1 Abdeckung und Regeln für Grenzfälle

`abdeckung.csv`: 353 Zeilen, keine ohne Platz. Verteilung: Stunde 100, Reihe 194, Klasse 16, Fach 11,
Fach/Referendariat 23, Chat ohne Ort 9. Neun Regeln reichen, ein „Sonstiges“ braucht es nicht:

| Regel | Fall | Platz |
|---|---|---|
| R1 | jedes Material | auf der niedrigsten Ebene, für die es gemacht ist. Ohne Stunde bleibt es bei der Reihe (LEK, Erwartungshorizont, Reihenentwurf, Bewertungsraster, Quellen). Stunde ist nie Pflicht. |
| R2 | Varianten (einfach/schwer, Türkisch, Level, Hilfe) | ein Material mit mehreren Varianten, nicht mehrere Materialien |
| R3 | klassenübergreifend (RLP, Operatoren, Kompetenzraster mündlich) | Fach |
| R4 | Notentabelle, Halbjahresplanung, Sitzplan | Klasse. Nur leere Vorlagen und Noten ohne Namen; Namen bleiben bei Lia (Schulrechner). |
| R5 | Formatvorlage (Gestaltung, Kopfzeile) | übergreifend unter „Vorlagen“, gilt für alles, Fach oder Klasse kann sie überschreiben |
| R6 | Referendariat: Seminar, UB-Entwurf, UB-Feedback, Examen | Fach, Abschnitt „Referendariat“. UB und Prüfungsstunde zusätzlich als Marke an der Stunde, in der sie stattfinden; die Examensreihe ist eine normale Reihe mit Marke „Examen“. |
| R7 | Theater-Stück | Reihe der Art „Inszenierung“ im Kurs; Proben sind ihre Stunden, Spielfassung, Szenenkarte und Szenenaufgaben ihr Material |
| R8 | korrigierte Datei von Lia | neue Fassung desselben Materials („Eigene Fassung hochladen“), kein neuer Auftrag |
| R9 | Verwaltung, private Fragen | kein Ort, kein Material: nur im Chat (Ort „Allgemein“) |
| R10 | Material in mehreren Klassen | „In andere Klasse kopieren“: Kopie mit Herkunftsangabe, kein geteiltes Original (eine Änderung in Klasse 8 soll Klasse 7 nicht verändern) |
| R11 | Schuljahreswechsel | Klasse gehört zu einem Schuljahr („8 · 2026/27“). Nach dem Schuljahr ins Archiv: nur lesen, „Reihe wiederverwenden“ kopiert sie in eine neue Klasse. Lias Klasse 7 (2025/26) ist heute schon Archiv. |

---

## 2. Objektmodell (OOUX)

Objekte, die Lia sieht und nennt. Keine Agenten, keine IDs, keine Warteschlangen.

| Objekt | Kernattribute | Beziehungen (Menge) | Aktionen für Lia |
|---|---|---|---|
| **Fach** | Name, Kurzform | hat 1–n Klassen; hat Fach-Material; hat Abschnitt Referendariat | öffnen |
| **Klasse/Kurs** | Name („8“, „Kurs 11“), Schuljahr, Lerngruppe (Text), Stand (aktiv/Archiv) | gehört zu 1 Fach; hat 0–n Reihen; hat Klassen-Material | öffnen, Lerngruppe beschreiben, archivieren |
| **Reihe** | Titel, Reihenfrage, Art (Unterricht/Inszenierung), Stand (geplant/läuft/abgeschlossen), schon behandelt, Marke (Examen) | gehört zu 1 Klasse; hat 0–n Stunden; hat Reihen-Material, Aufträge, Chat-Ort | anlegen, Reihenfrage ändern, abschließen, wiederverwenden |
| **Stunde** | Nummer, Thema, Datum (optional), Marke (UB, Prüfung) | gehört zu 1 Reihe; hat 0–n Materialien, Aufträge | anlegen, umbenennen, verschieben, Material hineinziehen |
| **Auftrag** | Wunsch (Text), Art, Ort, Stand (Abschnitt 2.1), Kosten | an genau 1 Ort (Fach/Klasse/Reihe/Stunde); erzeugt 1 Material; hat 1–n Fassungen und Rückmeldungen | anlegen (aus Vorlage), Rückmeldung geben, eigene Fassung hochladen, Fassung als final markieren, zurückziehen |
| **Fassung** | Nummer, von (Assistent oder Lia), Zeit, Vorschau, Dateien | gehört zu 1 Auftrag | ansehen, herunterladen, als final markieren, vergleichen (später) |
| **Material** | Titel, Art (Arbeitsblatt, Präsentation, Reihenentwurf, LEK, Spielfassung, Tabelle …), Varianten, finale Fassung | an 1 Ort; entsteht aus 1 Auftrag oder aus Lias Ablage | öffnen, herunterladen, in andere Klasse kopieren, neue Runde starten |
| **Vorlage** | Name, Art, Felder des Wunschs, Geltung (alle/Fach/Klasse), Gestaltung, Muster | gilt an 1 Ort und darunter (vererbt); erzeugt Aufträge | wählen („Neu aus Vorlage“), Gestaltung hochladen, Muster ansehen |
| **Chat** | Verlauf, Ort (Kontext) | genau einer; Kontext = gerade geöffneter Ort | fragen, Ort umschalten („ohne Ort“), „daraus Auftrag machen“, leeren |

Bewusst **nicht** als eigenes Objekt: Variante (Teil des Materials, R2), Entwurf zum Freigeben (ist ein Auftrag mit
Stand „wartet auf dich“), Rückmeldung (Eintrag im Verlauf des Auftrags), Regel/Feedback (bleibt unter „Ich“).

Material und Auftrag: Für Lia ist ein Material „fertig“ oder „in Arbeit“. Darum zeigt die App **ein Material mit
seinem Auftrag dahinter**: Solange nichts final ist, steht das Material mit Stand „Fassung 2 · wartet auf dich“
an seinem Ort; nach „final“ steht es ohne Hinweis da, der Verlauf bleibt aufklappbar. Material aus Lias Ablage hat
keinen Auftrag, nur Dateien.

### 2.1 Zustände eines Auftrags

```
             Lia schickt ab (aus Vorlage, an einem Ort)
                        │
                        ▼
  ┌────────────── läuft ──────────────┐
  │ (Kontingent voll: „wartet bis …“) │──── Fehler ───► hat nicht geklappt ──► „Nochmal“ = läuft
  └───────────────┬───────────────────┘                     (Grund steht da)
                  ▼
        Fassung n liegt vor  ◄─────────────────────────────┐
        (wartet auf dich)                                   │
          │        │         │                              │
          │        │         └── Rückmeldung (Text, Datei) ─┤ läuft → Fassung n+1
          │        └──────────── eigene Fassung hochladen ──┘ (Fassung n+1 von Lia, sofort, kein Lauf)
          ▼
   „Als final markieren“ (Lia, an jeder Fassung, nicht nur der neuesten)
          │
          ▼
        final ── Material zeigt die finale Fassung am Ort, Auftrag verschwindet aus „Heute“
          │
          └── „Neue Runde“ → wieder läuft (Fassung n+1), final bleibt bis zur nächsten Markierung
```

- **Final setzt nur Lia.** Kein Automatismus nach Zeit, kein „Passt“-Knopf mit Nebenwirkung. Ein Klick, rückgängig
  machbar (Frame.io: „Approved“, Figma: „Ready“).
- **Final ist ein Zustand des Materials, kein Ende der Geschichte**: Fassungen bleiben, die finale ist markiert.
- **Nach final:** Der Auftrag fällt aus „Wartet auf dich“. Die finale Fassung ist das, was der Agent künftig als
  Beispiel für diese Art sehen darf (Kandidat für „Muster“, nur als Vorschlag an Lia, nie automatisch).
- Entwürfe der Freigabe (examen-0c44bf, Lia setzt selbst ein) passen in dasselbe Schema: „Setze ich selbst ein“
  entspricht „final“. Entwürfe, die nach außen gehen (Mails), behalten Freigeben/Ändern/Ablehnen (CLAUDE.md).
- Grenzen aus CLAUDE.md bleiben: Lias Nachbesserungen laufen ohne Jans Okay, Jan hat den Stopp-Knopf.

**Technischer Bedarf (später):** `final` und „eigene Fassung“ gibt es in agentkit noch nicht. Die Web-App kann
beides selbst speichern (nach Bauschritt 2, Konten/SQLite); eine eigene Fassung von Lia muss als Datei in den
Agent-Ordner, damit die nächste Runde darauf aufsetzt. Stunden brauchen ein Feld in `reihen.toml` oder eine
eigene Datei je Reihe. Beides in Punkt 24 der Haupt-STATUS notiert.

---

## 3. Muster aus verwandten Anwendungen

Je Problem ein Muster. Kriterium: Lia kennt es schon (Word, Drive, Schulplattform, claude.ai) oder es ist dort
seit Jahren bewährt.

| Problem | Muster | Vorbild | Warum dieses |
|---|---|---|---|
| Wo bin ich, wo liegt was (4 feste Ebenen) | **Baum links + Brotkrumen über dem Inhalt** | Google Drive, Notion, Moodle-Kursbereich, Planboard | entspricht 1:1 Lias Ordnern; Brotkrumen zeigen den Ort und sind zugleich der Kontext für Chat und Neuer Auftrag. Ersetzt die Filter-Chips und „Unterricht →“. |
| Was wartet auf mich | **Posteingang als erster Eintrag über dem Baum („Heute“)** | Gmail/Outlook Posteingang, Google Classroom „Zu erledigen“, Linear Inbox | eine Liste quer über alle Orte, jede Zeile nennt ihren Ort als Brotkrume. Kein Filter nötig, der Baum ist der Filter. |
| Stunden in der Reihe | **Reihe als Liste nummerierter Stunden, Material der Reihe darüber** | Planboard, Moodle-Themenformat („Abschnitte“) | Stunde ist leicht: Nummer + Thema, kann leer sein, Material lässt sich hineinziehen. Keine Pflichtebene (R1). |
| Neues anfangen | **„+ Neu“ am Ort, öffnet die Vorlagengalerie; der Ort ist vorbelegt** | Word/PowerPoint „Neu aus Vorlage“, Canva, Notion „+ in dieser Seite“ | Lia muss die Reihe nicht aus einer Liste wählen: sie steht schon da. Die Vorlage legt die Art fest. |
| Vorlagen verschiedener Art | **Galerie mit Vorschaukarte je Art, dann ein kurzes Formular nur mit den Feldern dieser Art** | Word-Vorlagen, Canva, Google Forms-Vorlagen | Drei Dinge getrennt: *Gestaltung* (Formatvorlage .dotx/.potx, Farben aus profil.toml), *Muster* (gelungene Beispiele, Anregung), *Arbeitsweise* (welche Felder, welcher Agent). Geltung: alle → Fach → Klasse, nach unten vererbt, unten überschreibt oben (wie Formatvorlagen in Word). |
| Fassungen und final | **Fassungsstapel mit einer Statusmarke, „Als final markieren“** | Frame.io Version Stack + Status, Figma „Ready for dev“, Google Docs benannte Versionen | Lia nennt Dateien schon „final“. Eine Marke, sichtbar am Ort; alte Fassungen aufklappbar statt gelöscht. |
| Rückmeldung | **Rückmeldung als Text oder als hochgeladene Datei mit Kommentaren; „Eigene Fassung hochladen“** | Frame.io „Upload new version“, Word Kommentare/Überarbeiten | Das ist Lias echter Weg (93e29e, 03b145). Anmerkungen an Stellen im Browser erst, wenn der Renderer Blocklagen liefert. |
| Schnelle Frage | **Chat dauerhaft rechts, Kontext = aktueller Ort, sichtbar als Chip** | Copilot-Seitenleiste in Word, Claude Projects, Notion AI | kein Wechsel ins andere Programm; ersetzt das Reinkopieren des Kontexts. Ein Klick „ohne Ort“ für Verwaltungsfragen. |
| Aus dem Gespräch wird Arbeit | **„Daraus Auftrag machen“ an einer Chat-Antwort** | Slack „Create task from message“, Linear „Create issue from Slack“ | übernimmt Text und Ort in die Vorlagengalerie; Lia prüft und schickt ab. Kein stilles Starten. |
| Handy | **Baum wird Drilldown-Liste, Chat und Neu als Vollbild-Blatt** | iOS Dateien, Google Drive App | gleiche Objekte, gleiche Wörter, nur gestapelt (Abschnitt 4.2). |

### 3.1 Chat: was zu klären ist

- **Kontext:** Python baut ihn aus Dateien, nicht das Modell: Fach, Klasse mit Lerngruppe, Reihe mit Reihenfrage
  und „schon behandelt“, Stundenliste, Titel der Materialien am Ort, Lias Regeln. Kein Inhalt aus Schülerdateien.
  Der Chip über dem Eingabefeld zeigt, was mitgeht („Ethik › 8 › Straftheorien“), Klick schaltet auf „ohne Ort“.
- **Kosten:** läuft auf Lias Kontingent über `agentkit.claude_lauf` (ohne Bash, Schreibschutz). Schnelle Fragen mit
  einem kleinen Modell (Haiku/Sonnet), lange Planungsfragen mit dem großen nur auf Lias Klick („gründlich
  antworten“). Kein Zähler je Nachricht; bei vollem Kontingent ein Hinweis mit Uhrzeit statt Fehler.
- **Keine Schülernamen:** fester Hinweis unter dem Eingabefeld; Uploads im Chat nur PDF/Word/Bild mit demselben
  Hinweis. Eine zuverlässige Namenserkennung gibt es nicht; nichts erfinden. Verläufe werden nach 30 Tagen
  gelöscht (Vorschlag, Jan entscheidet), keine Übernahme von Chat-Inhalten in Regeln ohne Lias Klick.
- **„Daraus Auftrag machen“:** öffnet die Vorlagengalerie mit Text und Ort vorbelegt. Ein Chat startet nie selbst
  einen Auftrag und handelt nie nach außen.
- **Ein Chat, nicht viele:** ein Verlauf, Trennlinie bei Ortswechsel („jetzt: Kurs 11 › Der nackte Wahnsinn“).
  Ältere Verläufe je Ort sind eine spätere Frage, erst nach dem Test.
- **Bedarf:** ein Chat-Agent (`lia/chat/` oder Teil von lia/unterricht) mit Ortskontext. In Punkt 24 notiert.

---

## 4. Wireframes

Im Canvas, Variante Modernist (Inter, schwarz auf weiß, ein rotes Akzent):
- **Desktop 1440** (klickbar): drei Spalten Baum | Inhalt | Chat. Ansichten: Heute, Reihe Straftheorien, Stunde 3,
  Material mit Fassungen, Neu aus Vorlage (Galerie und Formular), Theater-Reihe, Vorlagen. Der Chat bleibt rechts
  stehen und zeigt den Ort.
- **Handy-Prüfung 390**: dieselbe Stunde als Drilldown mit Brotkrumen, Chat als Knopf unten.

Inhalte sind Lias echte Orte (Ethik 8 Straftheorien, Kurs 11 Der nackte Wahnsinn, Archiv Klasse 7). Die Stunden
der Reihe Strafe sind **Beispiele** (es gibt in keiner Datei Stunden), angelehnt an `reihen.toml` und
`examen.toml` (Kant, von Liszt, Prüfungsstunde). Keine Schülernamen, kein Name der Lehrkraft.

### 4.1 Aufbau Desktop

```
┌──────────────┬──────────────────────────────────────────┬──────────────────┐
│ Heute     (2)│ Ethik › 8 › Straftheorien                │ Chat             │
│              │ STRAFTHEORIEN              [+ Neu]       │ Ort: Ethik › 8 › │
│ ETHIK        │ Reihenfrage …   läuft · Examen           │ Straftheorien  ×│
│  8 · 26/27   │                                          │                  │
│   Straftheo… │ Zur ganzen Reihe                          │  …Verlauf…       │
│   + Reihe    │  Reihenentwurf      Fassung 2 · wartet   │                  │
│  Archiv      │  Umfrage vor der Reihe   wartet          │                  │
│ DARST. SPIEL │  Fallsammlung       final                │ [Frage …      ]  │
│  Kurs 11     │ Stunden                                  │ Keine Namen von  │
│   Der nackte │  1 Einstieg …                            │ Schüler*innen.   │
│   Komposit…  │  2 Kant …            Präsentation · fin. │                  │
│ Vorlagen     │  3 Anwendung Kant    Arbeitsblatt läuft  │                  │
│ Ich          │  + Stunde                                │                  │
└──────────────┴──────────────────────────────────────────┴──────────────────┘
   260 px                    flexibel (max 760)                   360 px
```

### 4.2 Prüfung bei Handy-Breite

Bei unter 900 px: Chat-Spalte wird ein Knopf „Fragen“ unten rechts (Vollbild-Blatt). Unter 640 px: Baum wird zur
Startliste („Heute, Ethik, Darstellendes Spiel, Vorlagen“) mit Drilldown; die Brotkrumen bleiben oben und führen
zurück. Keine Tabellen, Ziele ab 44 px. Neuer Auftrag öffnet sich als Vollbild. Geprüft im Board: alle sieben
Testaufgaben gehen auch dort, mit einem Schritt mehr (Ort antippen statt im Baum sehen).

### 4.3 Heuristik-Review (Nielsen), alt gegen neu

| Heuristik | heute (Handy, Chips) | neuer Entwurf | Rest-Risiko |
|---|---|---|---|
| 1 Status sichtbar | Läuft/Fertig nur in „Heute“ | Marke am Material an seinem Ort und in Heute; „läuft“ mit Uhrzeit | Dauer eines Laufs ist unbekannt; nur „gestartet 14:02“ zeigen, nichts schätzen |
| 2 Sprache der Nutzerin | „Unterricht“, „Ohne Reihe“, „Material“ als Art | Lias Wörter: Reihe, Stunde, Arbeitsblatt, Präsentation, final, Kurs | „Auftrag“ ist Jans Wort; im Test beobachten, ob Lia es nutzt |
| 3 Kontrolle und Freiheit | kein Zurücknehmen | final rückgängig; Auftrag zurückziehen; „ohne Ort“ im Chat | Zurückziehen eines laufenden Auftrags braucht agentkit |
| 4 Konsistenz | Chips filtern, Unterricht-Seite zeigt dasselbe anders | ein Ort, eine Ansicht; Heute ist nur eine Liste mit Brotkrumen | – |
| 5 Fehler vermeiden | Reihe aus Liste wählen, leicht falsch | Ort ist vorbelegt und sichtbar im Formular | Lia startet aus „Heute“ ohne Ort: dann fragt das Formular nach dem Ort |
| 6 Erkennen statt erinnern | Chips ohne Erklärung | Baum zeigt immer alles; Vorlagen mit Vorschau | Baum wächst mit Archiv; Archiv eingeklappt |
| 7 Effizienz | jedes Mal Formular | „+ Neu“ am Ort, „Daraus Auftrag machen“, eigene Fassung hochladen | Tastenkürzel später |
| 8 Schlicht | Abschnitte 01–04, Chips, Link | drei Spalten, keine Filter | Chat-Spalte kostet Platz; ab 1280 px prüfen |
| 9 Fehler verstehen | Grund des Agenten | Grund + „Nochmal“ | – |
| 10 Hilfe | keine | Leere Zustände erklären („Noch keine Stunden. + Stunde“) | – |

---

## 5. Was sich gegenüber dem Gebauten ändert

- Fliegt raus: Chips oben, Seite `/unterricht`, Link „Unterricht →“, Reihen-Auswahl im Formular.
- Bleibt: „Heute“ (wird linke oberste Zeile, Inhalt fast gleich), Ergebnis-Ansicht (wird die Material-Ansicht),
  Entwurf, Ketten-Logik (`logik.ketten`), `reihe_von`, Testbetrieb von „Neuer Auftrag“, Gestaltung Modernist.
- Neu: Baum, Orts-Ansichten (Fach, Klasse, Reihe, Stunde), Vorlagengalerie, Chat-Spalte, final, eigene Fassung.

Bauschritte nach dem Test (je klein, `logik.py` mit Tests, App-Tests über Unix-Socket, `./pruefen.sh` grün):
1. Rahmen drei Spalten + Baum aus `reihen_aus()` + Brotkrumen; Heute in die Mitte; `/unterricht` und Chips weg.
2. Orts-Ansichten Fach/Klasse/Reihe (lesend), Material mit Marke statt Ergebnisliste.
3. Stunden (braucht Datei, Bedarf lia/unterricht), Material einer Stunde zuordnen.
4. Vorlagengalerie für die Arten, die laufen (Arbeitsblatt, Präsentation, Tabelle über unterricht), Ort vorbelegt.
5. Mit Konten (Bauschritt 2 des alten Plans): final, eigene Fassung hochladen, Rückmeldung.
6. Chat-Spalte, erst wenn der Chat-Agent steht (Bedarf lia/).

---

## 6. Test mit Lia am PC (Jan leitet)

**Rahmen.** 20 Minuten, Lias Rechner, Canvas-Board „Desktop“ im Vollbild (Play). Jan liest jede Aufgabe vor und
legt sie als Zettel hin, erklärt nichts, hilft erst nach 2 Minuten Stillstand (dann zählt die Aufgabe als „mit
Hilfe“). Lia denkt laut. Keine Aufnahme. Hinweis vorher: „Getestet wird die Seite, nicht du. Es ist ein Bild,
manches geht nicht wirklich.“

**Die sieben Aufgaben** (in Lias Worten, ohne Wörter der Oberfläche):

| # | Aufgabe (vorlesen) | Erfolg, wenn | richtiger erster Klick |
|---|---|---|---|
| 1 | „Du willst dir den Plan für deine Reihe zur Strafe in der 8 ansehen. Mach ihn auf.“ | Material „Reihenentwurf“ geöffnet | Baum: Straftheorien |
| 2 | „Für die dritte Stunde der Strafe-Reihe brauchst du noch ein Arbeitsblatt. Gib es in Auftrag.“ | Galerie aus Stunde 3, Vorlage Arbeitsblatt, abgeschickt | Baum/Reihe: Stunde 3 |
| 3 | „Die Präsentation für Stunde 2 passt jetzt so. Halte fest, dass das die Fassung ist, die du nimmst.“ | „Als final markieren“ an der Präsentation | Stunde 2 bzw. Präsentation |
| 4 | „Du weißt nicht genau, was ‚Vergeltung‘ einfach erklärt heißt. Finde es heraus.“ | Frage im Chat abgeschickt | Chat-Eingabefeld |
| 5 | „Für den Theaterkurs willst du eine gekürzte Spielfassung von einem Stück. Fang damit an.“ | Vorlage „Spielfassung (Kürzung)“ im Kurs 11 gewählt | Baum: Kurs 11 bzw. „+ Neu“ dort |
| 6 | „Du hast das Arbeitsblatt in Word korrigiert. Gib es zurück, damit eine bessere Fassung entsteht.“ | „Rückmeldung mit Datei“ oder „Eigene Fassung hochladen“ gewählt | Material öffnen (Heute oder Baum) |
| 7 | „Was wartet gerade auf dich? Mach das Neueste auf.“ | erste Zeile in Heute geöffnet | Heute |

**Gemessen je Aufgabe:** Erfolg (ohne Hilfe / mit Hilfe / nicht), erster Klick (richtig/falsch, wohin), Zeit bis
Erfolg in Sekunden (Handy-Stoppuhr), wörtliche Äußerungen. Bogen: `shared/webapp/data/ia/testbogen.csv`.

**Ziel:** mindestens 6 von 7 ohne Hilfe. Erster Klick bei mindestens 5 von 7 richtig (Studien zu First-Click-Tests:
ist der erste Klick richtig, gelingt die Aufgabe meist).

**Danach (5 Minuten):** „Was war unklar?“, „Was fehlt dir, das du jede Woche brauchst?“, „Stunde als eigene Ebene:
brauchst du das, oder reicht die Reihe?“, „Wo würdest du nach der Notentabelle suchen?“, „Welche Programme hast du
dabei offen (Word, Pages, OneDrive, Lernraum)?“

**Auswertung:** Was 2-mal falsch angeklickt wird, wird geändert, bevor gebaut wird. Bei unter 6 von 7: Board
ändern, zweiter Test.

---

## 7. Empfehlung an Jan

1. **Aufbau übernehmen:** drei Spalten, Baum Fach → Klasse/Kurs → Reihe → Stunde, „Heute“ als oberster
   Eintrag, Chat rechts, „+ Neu“ am Ort mit Vorlagengalerie. Chips und `/unterricht` entfallen.
2. **Stunde als leichte Ebene:** nummerierte Liste in der Reihe, nie Pflicht. Lia ordnet heute nach Reihe und Art,
   Stunden nur über Dateinamen, die verrutschen. Der Test fragt nach, ob sie die Ebene will.
3. **Final setzt Lia, eigene Fassung hochladen** ist der Hauptweg für Rückmeldungen (ihr echter Weg), Knöpfe sind
   Zusatz.
4. **Vorlagen in drei Teilen:** Gestaltung, Muster, Arbeitsweise; Geltung vererbt. Zuerst nur die Arten, die
   ein Agent wirklich kann (Arbeitsblatt, Präsentation, Tabelle; Spielfassung erst, wenn theater neue Aufträge
   annimmt).
5. **Chat erst nach dem Test bauen**, aber im Test zeigen: er ist die schnellste Hilfe für Lias häufigste kleine
   Fragen und ersetzt das Reinkopieren von Kontext.
6. **Vor dem Test zu klären (Jan):** Fachname „Darstellendes Spiel“ statt „Theater“? Welche Programme nutzt Lia?
   Gibt es Kurs 12 und für welche Klasse ist die Notentabelle?
