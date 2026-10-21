# Format der Beschreibung (für Claude)

Du beschreibst ein Dokument als JSON. Python prüft es und baut daraus die Datei. Du schreibst nur Inhalt:
keine Dateinamen, keine Pfade, keine Schriftarten oder Farben. Die Gestaltung kommt aus dem Profil des Agenten.

Ist die Beschreibung ungültig, bekommst du alle Fehler auf einmal, jeweils mit der Stelle, zum Beispiel
`bloecke[4].antwort.anzahl: muss eine ganze Zahl von 1 bis 30 sein, ist "fünf"`. Die Zählung beginnt bei 0.
Korrigiere alle genannten Stellen und gib die vollständige Beschreibung neu aus.

## Allgemein
- Unbekannte Felder sind Fehler. Schreibe nur die Felder, die hier stehen.
- Texte sind reiner Text. Markdown wie `**fett**` oder `# Titel` erscheint wörtlich, also weglassen.
  Ein Zeilenumbruch `\n` ist erlaubt.
- Pflichttexte dürfen nicht leer sein. Tabellenzellen und `untertitel` dürfen leer sein.

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

## Folien (wird eine pptx-Datei)

```json
{
  "art": "folien",
  "titel": "Der kategorische Imperativ",
  "untertitel": "Ethik, Klasse 10",
  "folien": [
    {"titel": "Was ist eine Maxime?", "punkte": ["subjektive Regel des Handelns", "Beispiel: Ich lüge, wenn es mir nützt."]},
    {"titel": "Fragen?"}
  ]
}
```

| Feld | Pflicht | Bedeutung |
|---|---|---|
| `art` | ja | `"folien"` |
| `titel` | ja | Titel der Titelfolie, höchstens 200 Zeichen |
| `untertitel` | nein | Untertitel der Titelfolie, höchstens 200 Zeichen, darf leer sein |
| `folien` | ja | 1 bis 50 Folien nach der Titelfolie |

Jede Folie hat `titel` (Pflicht, höchstens 200 Zeichen) und `punkte` (optional, 0 bis 10 Stichpunkte, je höchstens
300 Zeichen). Stichpunkte kurz halten: eine Zeile, kein ganzer Absatz.
