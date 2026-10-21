# Format der Beschreibung (für Claude)

Du beschreibst ein Dokument als JSON. Python prüft es und baut daraus die Datei. Du schreibst nur Inhalt:
keine Dateinamen, keine Pfade, keine Schriftarten oder Farben. Die Gestaltung kommt aus der Vorlage.

Ist die Beschreibung ungültig, bekommst du alle Fehler auf einmal, jeweils mit der Stelle, zum Beispiel
`bloecke[4].antwort.anzahl: muss eine ganze Zahl von 1 bis 30 sein, ist "fünf"`. Die Zählung beginnt bei 0.
Korrigiere alle genannten Stellen und gib die vollständige Beschreibung neu aus.

## Allgemein
- Unbekannte Felder sind Fehler. Schreibe nur die Felder, die hier stehen.
- Texte sind reiner Text. Markdown wie `**fett**` oder `# Titel` erscheint wörtlich, also weglassen.
  Ein Zeilenumbruch `\n` ist erlaubt.
- Pflichttexte dürfen nicht leer sein. Tabellenzellen und `untertitel` dürfen leer sein.

## Arbeitsblatt (wird eine docx-Datei)

```json
{
  "art": "arbeitsblatt",
  "titel": "Der kategorische Imperativ",
  "kopfzeile": ["Name", "Klasse", "Datum"],
  "bloecke": [
    {"typ": "ueberschrift", "text": "Einstieg", "ebene": 1},
    {"typ": "absatz", "text": "Kant fragt, wann eine Handlung moralisch ist."},
    {"typ": "liste", "punkte": ["Maxime", "allgemeines Gesetz"], "nummeriert": false},
    {"typ": "tabelle", "kopf": ["Begriff", "Erklärung"], "zeilen": [["Maxime", ""], ["Pflicht", ""]]},
    {"typ": "aufgabe", "text": "Erkläre den Begriff Maxime mit eigenen Worten.", "antwort": {"art": "linien", "anzahl": 5}},
    {"typ": "aufgabe", "text": "Stelle den Gedankengang als Schaubild dar.", "antwort": {"art": "kasten", "hoehe_cm": 8}},
    {"typ": "aufgabe", "text": "Lies den Text auf Seite 42."}
  ]
}
```

| Feld | Pflicht | Bedeutung |
|---|---|---|
| `art` | ja | `"arbeitsblatt"` |
| `titel` | ja | Titel oben auf dem Blatt, höchstens 200 Zeichen |
| `kopfzeile` | nein | 1 bis 4 Felder zum Ausfüllen (je höchstens 30 Zeichen), oben auf jeder Seite mit einer Linie dahinter |
| `bloecke` | ja | 1 bis 200 Blöcke in Lesereihenfolge |

Blöcke, unterschieden durch `typ`:

| typ | Felder |
|---|---|
| `ueberschrift` | `text` (höchstens 200 Zeichen), `ebene` 1 bis 3 (optional, Standard 1) |
| `absatz` | `text` (höchstens 5000 Zeichen) |
| `liste` | `punkte`: 1 bis 50 Texte (je höchstens 1000 Zeichen), `nummeriert` true/false (optional, Standard false) |
| `tabelle` | `kopf` (optional): Spaltennamen, `zeilen`: 1 bis 100 Zeilen. Höchstens 8 Spalten, jede Zeile hat gleich viele Zellen wie `kopf` bzw. wie die erste Zeile. Zellen höchstens 500 Zeichen, leer erlaubt. |
| `aufgabe` | `text` (höchstens 2000 Zeichen), `antwort` (optional, ohne sie gibt es keinen Platz zum Schreiben) |

Aufgaben werden automatisch nummeriert. Schreibe keine Nummer in den `text`.

`antwort` ist eines von beiden:
- `{"art": "linien", "anzahl": 5}`: 1 bis 30 Schreiblinien
- `{"art": "kasten", "hoehe_cm": 8}`: ein leerer Kasten, 1 bis 25 cm hoch (Kommazahl erlaubt)

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
