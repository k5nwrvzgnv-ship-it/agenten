# Format der Beschreibung (für Claude)

Du beschreibst ein Dokument als JSON (Arbeitsblatt, Zusammenfassung oder Folien). Python prüft es und baut daraus
die Datei. Du schreibst nur Inhalt: keine Dateinamen, keine Pfade, keine Schriftarten oder Farben. Die Gestaltung
kommt aus dem Profil des Agenten.

Ist die Beschreibung ungültig, bekommst du alle Fehler auf einmal, jeweils mit der Stelle, zum Beispiel
`bloecke[4].antwort.anzahl: muss eine ganze Zahl von 1 bis 30 sein, ist "fünf"`. Die Zählung beginnt bei 0.
Korrigiere alle genannten Stellen und gib die vollständige Beschreibung neu aus.

## Allgemein
- Unbekannte Felder sind Fehler. Schreibe nur die Felder, die hier stehen.
- Texte sind reiner Text. Markdown wie `**fett**` oder `# Titel` erscheint wörtlich, also weglassen.
  Ein Zeilenumbruch `\n` ist erlaubt.
- Pflichttexte dürfen nicht leer sein. Tabellenzellen dürfen leer sein.

## Arbeitsblatt (wird eine docx-Datei)

Oben steht immer eine Kopf-Tabelle: Fach, Thema, Nummer, Lehrkraft und Felder für Datum und Name. Fach, Lehrkraft,
Schrift und Farben kommen aus dem Profil des Agenten. Du gibst nur `titel` (das Thema, gern als Leitfrage) und
optional `nummer` an.

```json
{
  "art": "arbeitsblatt",
  "titel": "Muss ich fremden Menschen in Not genauso helfen wie Nahestehenden?",
  "nummer": "5",
  "bloecke": [
    {"typ": "merksatz", "titel": "Merksatz zu Peter Singer:", "text": "Ist die Not groß und sind meine Kosten klein, dann muss ich helfen."},
    {"typ": "anweisung", "text": "Lies das Beispiel und bearbeite die Aufgaben!"},
    {"typ": "material", "titel": "Beispiel", "text": "Yasmins großer Bruder zieht heute um ...\nGleichzeitig sucht ein Verein Helfer*innen ..."},
    {"typ": "aufgaben", "aufgaben": [
      {"text": "Warum ist der Bruder in Not? Unterstreiche die passenden Sätze im Text!", "hilfe": "Du findest Hinweise in den Zeilen 1-2."},
      {"text": "Welche Not ist größer? Kreuze an!", "antwort": {"art": "ankreuzen", "optionen": ["Die Not des Bruders", "Die Not der obdachlosen Menschen"]}},
      {"text": "Wem sollte Yasmin helfen? Begründe!", "antwort": {"art": "satzanfaenge", "saetze": [
        {"anfang": "Nach Peter Singer sollte Yasmin", "linien": 2},
        {"anfang": "Der Grund dafür ist, dass", "linien": 2}]}},
      {"text": "Erkläre den Begriff Not mit eigenen Worten.", "antwort": {"art": "linien", "anzahl": 4}},
      {"text": "Stelle die beiden Positionen als Schaubild dar.", "antwort": {"art": "kasten", "hoehe_cm": 8}}
    ]},
    {"typ": "neue_seite", "querformat": true},
    {"typ": "ueberschrift", "text": "Wem sollte Yasmin helfen?"},
    {"typ": "tabelle", "kopf": ["", "Peter Singer", "Aristoteles"], "zeilen": [["Behauptung", "", ""], ["Begründung", "", ""]], "zeilenhoehe_cm": 4, "erste_spalte_fett": true}
  ]
}
```

| Feld | Pflicht | Bedeutung |
|---|---|---|
| `art` | ja | `"arbeitsblatt"` |
| `titel` | ja | Thema in der Kopf-Tabelle, höchstens 200 Zeichen |
| `nummer` | nein | Nummer des Arbeitsblatts, z. B. `"5"` oder `"5.2"`, höchstens 20 Zeichen |
| `bloecke` | ja | 1 bis 200 Blöcke in Lesereihenfolge |

Blöcke, unterschieden durch `typ`:

| typ | Felder | Aussehen |
|---|---|---|
| `merksatz` | `titel` (optional), `text` (höchstens 5000 Zeichen) | Kasten mit Doppelrahmen, farbig |
| `anweisung` | `text` (höchstens 500 Zeichen) | fetter Satz, z. B. „Lies und bearbeite!“ |
| `material` | `titel` (optional, z. B. „Beispiel“, „Text“), `text` (höchstens 5000 Zeichen) | farbig hinterlegt, Blocksatz |
| `aufgaben` | `aufgaben`: 1 bis 20 Aufgaben, `titel` (optional, Standard „Aufgaben:“, `""` für keinen) | nummeriert, fett |
| `ueberschrift` | `text` (höchstens 200 Zeichen), `ebene` 1 bis 3 (optional, Standard 1) | fett |
| `absatz` | `text` (höchstens 5000 Zeichen) | normaler Text |
| `liste` | `punkte`: 1 bis 50 Texte, `nummeriert` true/false (optional, Standard false) | Aufzählung |
| `tabelle` | `kopf` (optional), `zeilen`: 1 bis 100, `zeilenhoehe_cm` (optional, 0.5 bis 15), `erste_spalte_fett` (optional) | mit Linien, höchstens 8 Spalten, Zellen höchstens 500 Zeichen, leer erlaubt. Jede Zeile hat gleich viele Zellen wie `kopf` bzw. wie die erste Zeile. Für Ausfülltabellen leere Zellen und `zeilenhoehe_cm`. |
| `neue_seite` | `querformat` true/false (optional, Standard false) | neue Seite, ab hier hoch oder quer |

Eine Aufgabe hat `text` (Pflicht, höchstens 2000 Zeichen), `antwort` (optional) und `hilfe` (optional, höchstens
500 Zeichen). Die Aufgaben werden über das ganze Blatt durchnummeriert, schreibe keine Nummer in den `text`. Hilfen
erscheinen klein nach den Aufgaben ihrer Gruppe als „Aufgabe 3: ...“.

`antwort` ist eines davon. Ohne `antwort` gibt es keinen Platz, etwa für „Unterstreiche im Text“:
- `{"art": "linien", "anzahl": 4}`: 1 bis 30 Schreiblinien
- `{"art": "kasten", "hoehe_cm": 8}`: leerer Kasten, 1 bis 25 cm hoch (Kommazahl erlaubt)
- `{"art": "ankreuzen", "optionen": ["...", "..."]}`: 2 bis 6 Optionen mit Kästchen nebeneinander, je höchstens 100 Zeichen
- `{"art": "satzanfaenge", "saetze": [{"anfang": "Ich finde, dass", "linien": 2}]}`: 1 bis 5 Satzanfänge (je höchstens
  200 Zeichen) mit je 1 bis 10 Linien

## Zusammenfassung (wird eine docx-Datei, A4)

Für Zusammenfassungen von Vorlesungen. Oben steht ein Kopf mit Kurs, Titel, „Vorlesung vom …“, Stand (heutiges
Datum, setzt der Renderer) und „erstellt von“ (aus dem Profil). Unten auf jeder Seite stehen Kurs, Titel und die
Seitenzahl. Überschriften werden automatisch nummeriert (1, 1.1), schreibe keine Nummer in den Text.

**Belege:** Absätze, Listenpunkte, Tabellen, Hinweise, Rechenbeispiele, Lösungen und offene Fragen dürfen `quellen`
haben, eine Liste aus 1 bis 10 Angaben `{"art": ..., "stelle": ...}`:
- `"transkript"`: Seite im Transkript, nur Zahlen wie `"4"`, `"4-5"` oder `"4, 7"`. Erscheint als „Transkript S. 4“.
- `"folie"`: Foliennummer, ebenso nur Zahlen. Erscheint als „Folie 12“.
- `"norm"`: Bezeichnung der Norm, z. B. `"DIN 68800-1"` (höchstens 100 Zeichen).

Die Quellen stehen klein in eckigen Klammern am Ende. Schreibe sie nicht in den Text, sonst kommt ein Fehler.
Dieselben Stellen (außer Lösungen) dürfen `kennzeichnung` haben: `"unsicher"` (Aussage im Transkript nicht
eindeutig) oder `"muendlich"` (nur in der Vorlesung gesagt, nicht auf den Folien). Die Legende dazu steht im Kopf.

```json
{
  "art": "zusammenfassung",
  "titel": "Integrierter Holzschutz: Grundlagen",
  "kurs": "Integrierter Holzschutz",
  "datum": "20.10.2026",
  "bloecke": [
    {"typ": "hinweis", "art": "organisatorisch", "text": "Die Übung beginnt erst in der nächsten Woche.", "kennzeichnung": "muendlich", "quellen": [{"art": "transkript", "stelle": "1"}]},
    {"typ": "ueberschrift", "text": "Warum Holzschutz?"},
    {"typ": "absatz", "text": "Holz kann von Pilzen und Insekten abgebaut werden.", "quellen": [{"art": "transkript", "stelle": "2-3"}, {"art": "folie", "stelle": "4"}]},
    {"typ": "ueberschrift", "text": "Maßnahmen", "ebene": 2},
    {"typ": "liste", "punkte": [
      {"text": "Baulicher Holzschutz hält Holz trocken.", "quellen": [{"art": "folie", "stelle": "6"}]},
      {"text": "Chemischer Holzschutz erst, wenn baulicher nicht reicht.", "kennzeichnung": "unsicher"},
      "Die Wahl der Holzart gehört ebenfalls dazu."]},
    {"typ": "hinweis", "art": "pruefungsrelevant", "text": "Die Rangfolge der Maßnahmen kommt in der Klausur.", "kennzeichnung": "muendlich"},
    {"typ": "tabelle", "titel": "Gebrauchsklassen (Auszug)", "kopf": ["Gebrauchsklasse", "Situation"], "zeilen": [["GK 1", "innen, trocken"], ["GK 4", "Erdkontakt"]], "erste_spalte_fett": true, "quellen": [{"art": "norm", "stelle": "DIN 68800-1"}]},
    {"typ": "rechenbeispiel", "titel": "Holzfeuchte", "aufgabe": "Eine Probe wiegt feucht 560 g, darrtrocken 480 g. Wie hoch ist die Holzfeuchte?", "gegeben": ["m_u = 560 g", "m_0 = 480 g"], "schritte": [
      {"text": "Formel", "rechnung": "u = (m_u − m_0) / m_0 · 100 %"},
      {"text": "Einsetzen und ausrechnen", "rechnung": "u = 80 g / 480 g · 100 % ≈ 16,7 %"}], "ergebnis": "u ≈ 16,7 %", "quellen": [{"art": "folie", "stelle": "12"}]}
  ],
  "selbsttest": [{"frage": "Welche Art des Holzschutzes hat Vorrang?", "loesung": "Der bauliche Holzschutz.", "quellen": [{"art": "transkript", "stelle": "5"}]}],
  "offene_fragen": ["Gibt es eine Altklausur zum Üben?"]
}
```

| Feld | Pflicht | Bedeutung |
|---|---|---|
| `art` | ja | `"zusammenfassung"` |
| `titel` | ja | Titel, höchstens 200 Zeichen |
| `untertitel` | nein | steht klein unter dem Titel, höchstens 200 Zeichen |
| `kurs` | ja | Name der Lehrveranstaltung, höchstens 100 Zeichen, steht im Kopf und in der Fußzeile |
| `datum` | ja | Datum der Vorlesung als `"TT.MM.JJJJ"`, z. B. `"20.10.2026"` |
| `bloecke` | ja | 1 bis 200 Blöcke in Lesereihenfolge |
| `selbsttest` | nein | 1 bis 30 Fragen `{"frage", "loesung", "quellen" (optional)}`, Frage höchstens 1000, Lösung höchstens 3000 Zeichen. Die Fragen stehen nach den Blöcken, die Lösungen auf einer eigenen letzten Seite. |
| `offene_fragen` | nein | 1 bis 30 Fragen, die die Vorlesung nicht geklärt hat, je Text (höchstens 1000 Zeichen) oder `{"text", "quellen", "kennzeichnung"}` |

Blöcke, unterschieden durch `typ` (`quellen` und `kennzeichnung` sind bei allen außer `ueberschrift` und `liste`
optional; bei `liste` stehen sie an den einzelnen Punkten):

| typ | Felder | Aussehen |
|---|---|---|
| `ueberschrift` | `text` (höchstens 200 Zeichen, ohne Nummer), `ebene` 1 oder 2 (optional, Standard 1). Vor der ersten Ebene 2 muss eine Ebene 1 stehen. | nummeriert, farbig |
| `absatz` | `text` (höchstens 5000 Zeichen) | normaler Text |
| `liste` | `punkte`: 1 bis 50, je Text (höchstens 1000 Zeichen) oder `{"text", "quellen", "kennzeichnung"}`; `nummeriert` true/false (optional) | Aufzählung |
| `tabelle` | `zeilen`: 1 bis 100, `kopf` (optional), `titel` (optional, steht fett darüber), `erste_spalte_fett` (optional) | höchstens 8 Spalten, Zellen höchstens 500 Zeichen, jede Zeile gleich viele Zellen. Quellen stehen unter der Tabelle. |
| `hinweis` | `art`: `"pruefungsrelevant"` oder `"organisatorisch"`, `text` (höchstens 5000 Zeichen), `titel` (optional, Standard „Prüfungsrelevant“ bzw. „Organisatorisches“) | farbiger Kasten mit Balken links |
| `rechenbeispiel` | `aufgabe` (höchstens 2000 Zeichen), `schritte`: 1 bis 15, je `text` (höchstens 1000) und `rechnung` (optional, höchstens 300); `ergebnis` (höchstens 300); `titel` (optional), `gegeben` (optional, 1 bis 15 Texte, je höchstens 300) | Kasten: Aufgabe, Gegeben, Schritt 1, 2, …, Ergebnis fett |

Formeln schreibst du als reinen Text, z. B. `u = (m_u − m_0) / m_0 · 100 %`.

## Folien (wird eine pptx-Datei, 16:9)

Die erste Folie ist immer die Titelfolie (farbiger Balken mit Icon, Titel, Untertitel). Danach folgen die Folien aus
`folien`. Jede hat einen Titel, darunter einen Strich, optional Icons rechts oben, und unten eine Fußzeile aus
Untertitel, Titel und Foliennummer. Der Inhalt einer Folie besteht aus 1 bis 4 Elementen, die untereinander stehen.
Die Schriftgröße wählt der Renderer: wenig Text wird größer, viel Text kleiner. Passt eine Folie auch verkleinert
nicht, bekommst du einen Fehler. Dann kürzen oder auf zwei Folien verteilen.

```json
{
  "art": "folien",
  "titel": "Muss ich Fremden in Not genauso helfen wie Nahestehenden?",
  "untertitel": "Ethik · Klasse 8",
  "icon": "handschlag",
  "folien": [
    {"titel": "Ziel für heute", "icons": ["ziel"], "inhalt": [
      {"typ": "zentriert", "absaetze": ["Wir wenden Singers und Aristoteles’ Positionen auf ein Beispiel an."]}]},
    {"titel": "Was ist Behauptung, Begründung, Beispiel?", "inhalt": [
      {"typ": "kasten", "titel": "Ein Argument:", "absaetze": [[
        {"text": "Ich finde, dass man nicht lügen sollte.", "farbe": "blau", "unterstrichen": true},
        {"text": " "},
        {"text": "Der Grund dafür ist, dass andere einem dann nicht mehr vertrauen.", "farbe": "orange", "unterstrichen": true}]]},
      {"typ": "legende", "eintraege": [{"text": "Behauptung", "farbe": "blau"}, {"text": "Begründung", "farbe": "orange"}]}]},
    {"titel": "Yasmins Entscheidung", "icons": ["paket", "schale"], "inhalt": [
      {"typ": "kasten", "absaetze": ["Yasmins großer Bruder zieht heute um ...", [{"text": "Yasmin muss sich entscheiden.", "fett": true}]]},
      {"typ": "satzanfang", "text": "Yasmin steht vor dem Problem, dass …"}]},
    {"titel": "Unsere Leitfrage", "inhalt": [{"typ": "leitfrage", "text": "Muss ich Fremden in Not genauso helfen wie Nahestehenden?"}]},
    {"titel": "Zwei Positionen", "inhalt": [{"typ": "spalten", "spalten": [
      {"titel": "Merksatz Singer", "text": "Ist die Not groß und sind meine Kosten klein, muss ich helfen."},
      {"titel": "Merksatz Aristoteles", "text": "Nahestehenden schulde ich mehr als Fremden."}]}]},
    {"titel": "Arbeitsauftrag", "inhalt": [
      {"typ": "zentriert", "absaetze": ["Bearbeitet die Aufgaben 1–4 auf euren Arbeitsblättern!"]},
      {"typ": "zeit", "minuten": 10}]},
    {"titel": "Wer überzeugt dich?", "inhalt": [
      {"typ": "auswahl", "optionen": ["Aristoteles", "Peter Singer"]},
      {"typ": "satzanfang", "text": "Mich überzeugt … am meisten, weil …"}]},
    {"titel": "Feedback", "inhalt": [{"typ": "feedback",
      "gut": ["Etwas, das ich heute gelernt habe, ist …"], "schlecht": ["Was ich heute nicht verstanden habe, ist …"]}]},
    {"titel": "Zusammenfassung", "inhalt": [
      {"typ": "text", "text": "Drei Dinge zum Merken:"},
      {"typ": "punkte", "punkte": ["Not und Kosten abwägen", "Nähe kann Pflichten begründen"]}]}
  ]
}
```

| Feld | Pflicht | Bedeutung |
|---|---|---|
| `art` | ja | `"folien"` |
| `titel` | ja | Titel der Titelfolie und der Fußzeile, höchstens 200 Zeichen |
| `untertitel` | nein | z. B. `"Ethik · Klasse 8"`, höchstens 100 Zeichen, steht auch in der Fußzeile |
| `icon` | nein | Icon auf der Titelfolie (Namen siehe unten) |
| `folien` | ja | 1 bis 50 Folien nach der Titelfolie |

Jede Folie hat `titel` (Pflicht, höchstens zwei Zeilen, also etwa 90 Zeichen), `inhalt` (Pflicht, 1 bis 4 Elemente)
und `icons` (optional, 1 bis 2 Namen, stehen rechts neben dem Titel).

Elemente, unterschieden durch `typ`:

| typ | Felder | Aussehen |
|---|---|---|
| `kasten` | `absaetze`: 1 bis 6, `titel` (optional, fett) | grauer Kasten mit Balken links, z. B. für Material, Beispiele, Argumente |
| `text` | `text` | normaler Text |
| `punkte` | `punkte`: 1 bis 8 | Aufzählung mit • |
| `zentriert` | `absaetze`: 1 bis 4 | großer fetter Text in der Mitte, z. B. Ziel, Arbeitsauftrag, Frage |
| `leitfrage` | `text` (höchstens 200 Zeichen, reiner Text) | weiß auf farbiger Fläche |
| `zeit` | `minuten`: 1 bis 180 | Wecker und „Zeit: 10 Minuten“ |
| `spalten` | `spalten`: 2 bis 3, je `titel` (höchstens 100 Zeichen) und `text` (höchstens 600) | graue Kästen nebeneinander, z. B. Merksätze |
| `auswahl` | `optionen`: 2 bis 4 (je höchstens 100 Zeichen, reiner Text) | umrandete Kästen nebeneinander, z. B. Positionen zur Wahl |
| `satzanfang` | `text` (höchstens 200 Zeichen, reiner Text) | grün mit Zeigefinger, Anführungszeichen „…“ kommen automatisch |
| `feedback` | `gut` und `schlecht`: je 1 bis 4 Satzanfänge (reiner Text) | zwei Spalten mit Smiley und traurigem Gesicht |
| `legende` | `eintraege`: 2 bis 4, je `text` und `farbe` | farbige, unterstrichene Begriffe nebeneinander (zu Markierungen im Text) |

**Textteile:** Wo oben `text` oder ein Eintrag in `absaetze`/`punkte` steht (außer „reiner Text“), darf statt eines
Texts eine Liste von Teilen stehen, um einzelne Stellen hervorzuheben:
`[{"text": "Ich finde, ...", "farbe": "blau", "unterstrichen": true}, {"text": " "}, {"text": "wichtig", "fett": true}]`.
Jeder Teil hat `text` und optional `fett`, `farbe` (`"blau"`, `"orange"`, `"gruen"`, `"rot"`, `"grau"`) und
`unterstrichen`. Leerzeichen zwischen den Teilen als eigener Teil `{"text": " "}`. Texte in Kästen höchstens 1500,
Punkte und zentrierte Absätze höchstens 300 Zeichen.

**Icons:** `achtung`, `aufgabe`, `auge`, `bild`, `buch`, `buecher`, `checkliste`, `daumen_hoch`, `daumen_runter`, `flagge`, `frage`, `gehirn`, `gesetz`, `gespraech`, `gluehbirne`, `gruppe`, `haken`, `handschlag`, `haus`, `herz`, `kalender`, `karte`, `kreuz`, `lupe`, `megafon`, `mikrofon`, `musik`, `neutral`, `notizen`, `ohr`, `paket`, `partner`, `person`, `pfeil`, `puzzle`, `rakete`, `sanduhr`, `schale`, `schreiben`, `schule`, `smiley`, `sprechblase`, `stern`, `stift`, `tafel`, `text`, `traurig`, `uhr`, `video`, `waage`, `wecker`, `welt`, `zeigefinger`, `ziel`, `zitat`.
