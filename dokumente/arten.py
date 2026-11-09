"""Arten des Arbeitsplatzes, die dokumente neben der Zusammenfassung baut: Präsentation und Bericht.

Der Ablauf ist derselbe wie bei der Zusammenfassung (zusammenfassen.erstellen): Claude beschreibt, der Renderer
baut (folien -> pptx, bericht -> docx, jeweils mit PDF und Seitenbildern), Claude kontrolliert Kontrolltext und
Vorschaubilder, Python prüft den Bericht. Statt einer Behauptungsliste gilt: nichts dazuerfinden, Wünsche aus dem
Auftrag umsetzen, was im Material fehlt, als [OFFEN: …] markieren.

Der Auftrag kommt vom Arbeitsplatz mit art und felder; die Felder stehen auch im Auftragstext ("Feld: Wert").
"""

import json

import zusammenfassen as z

ABBRUCH = "ZU_WENIG_MATERIAL"
FELDER_BERICHT = ("erfunden", "auftrag", "darstellung")
BERICHT_FORMAT = """{"erfunden": ["Aussage, die weder im Material noch im Auftrag steht"],
 "auftrag": ["Gliederungswunsch Kapitel Fazit fehlt"], "darstellung": ["Folie 4: Text zu voll"]}"""

GRUNDSATZ = """Nichts erfinden: Inhalt nur aus dem Material (Dateien des Auftrags) und den Angaben im Auftrag. Keine
Zahlen, Daten, Namen, Orte, Normen, Quellen, Beispiele, Tätigkeiten oder Bewertungen, die dort nicht stehen, auch
nicht als Platzhalter oder "typischerweise". Formulieren, kürzen, ordnen und gliedern darfst du frei. Fehlt etwas,
das an eine Stelle gehört, schreib dort [OFFEN: was fehlt, kurz] statt es auszudenken. Lieber kürzer und mit
offenen Stellen als lang und aufgefüllt."""

DATEIEN_HINWEIS = """Material: {material}. Zu Word, PowerPoint und Excel liegt <datei>.txt daneben, zu PDFs <datei>.txt
und Seitenbilder in <datei>-seiten/. Lies alles, bevor du schreibst."""

ABBRUCH_HINWEIS = """Reichen Material und Angaben nicht einmal für §KURZ§ (z. B. nur ein Thema, kein Material, keine
Stichpunkte), schreib keine Datei und antworte nur:
""" + ABBRUCH + """: <ein Satz, was fehlt>
Sonst antworte nur: fertig"""

PRAESENTATION_KONTEXT = """Du bist der Dokumente-Agent von Jan. Er studiert Holzingenieurwesen (M.Sc.) an der HNE
Eberswalde. Du baust eine Präsentation (Folien für einen Vortrag) nach seinem Auftrag aus dem Arbeitsplatz.

""" + GRUNDSATZ + """

Folien für einen Vortrag, passend zu Zielgruppe und Umfang im Auftrag: je Folie ein Gedanke, kurze Punkte statt
langer Sätze, höchstens etwa 6 Punkte je Folie. Umfang im Auftrag (z. B. "10 Folien") zählt die Titelfolie mit;
reicht das Material nicht, lieber weniger Folien. Am Ende eine Folie mit dem Fazit oder den Kernaussagen, wenn das
Material sie hergibt. Die Unterrichts-Elemente (satzanfang, feedback, auswahl, zeit, legende) nur, wenn der Auftrag
sie verlangt. untertitel: Anlass oder Zielgruppe, wenn im Auftrag genannt, sonst weglassen.

Du schreibst keine Datei selbst, sondern eine JSON-Beschreibung, aus der Python die pptx baut. Format:

{format}"""

BERICHT_KONTEXT = """Du bist der Dokumente-Agent von Jan. Er studiert Holzingenieurwesen (M.Sc.) an der HNE
Eberswalde. Du schreibst einen Bericht (z. B. Praktikumsbericht) nach seinem Auftrag aus dem Arbeitsplatz. Jan
überarbeitet ihn in Word und gibt ihn unter seinem Namen ab.

""" + GRUNDSATZ + """

Gerade bei Erfahrungsberichten: keine Eindrücke, Lernerfolge oder Bewertungen ausdenken. Steht dazu nichts im
Material, gehört dorthin ein [OFFEN: …] (z. B. "[OFFEN: Was hast du in dieser Woche gelernt?]").
Gliederung: der Gliederungswunsch aus dem Auftrag; ohne Wunsch die übliche Gliederung dieser Art von Bericht (für
einen Praktikumsbericht etwa Einleitung, Betrieb, Tätigkeiten, Reflexion, Fazit). Schreib in der Form, die zur Art
passt (Praktikumsbericht in der Ich-Form, sachlich). rubrik = Art des Berichts (z. B. "Praktikumsbericht").
datum weglassen, wenn der Auftrag keins nennt. Kennzeichnung "annahme" nicht verwenden: keine Annahmen, sondern
[OFFEN: …]. quellen und quellenverzeichnis nur, wenn der Bericht Fakten aus Fremdquellen im Material wiedergibt
(je Materialdatei eine ID M1, M2, … mit Dateinamen als Text); in Erfahrungsberichten weglassen. offene_fragen:
Fragen an Jan, die der Bericht nicht klären konnte (optional).

Du schreibst keine Datei selbst, sondern eine JSON-Beschreibung, aus der Python die docx baut. Format:

{format}"""

START = """

Auftrag{herkunft} (Felder als Zeilen "Feld: Wert"):
{text}

""" + DATEIEN_HINWEIS + """
Schreib dann die Beschreibung nach {ordner}/beschreibung.json. Ändere keine anderen Dateien.

""" + ABBRUCH_HINWEIS

ANTWORT = """Jan antwortet auf §FERTIG§:
{text}
{dateien}
Pass die Beschreibung entsprechend an und schreib sie vollständig nach {ordner}/beschreibung.json. Auch hier gilt:
nichts erfinden. Ergänzt Jan, was fehlte, ersetze das [OFFEN: …] dazu; sonst bleibt es stehen.
Antworte nur: fertig"""

KONTROLLE = """§DER§ ist gebaut ({seiten} {einheit}). Prüfe das Ergebnis jetzt, bevor es an Jan geht.
- Kontrolltext (Inhalt in Lesereihenfolge): {kontrolltext}
- Vorschaubilder, jedes mit Read ansehen: {bilder}
- Vergleiche mit dem Auftrag (Felder) und dem Material.
Schreib deinen Bericht nach {ordner}/kontrolle.json, genau in diesem Format:
{bericht}
- erfunden: Aussagen, Zahlen, Namen, Beispiele oder Bewertungen, die weder im Material noch im Auftrag stehen
- auftrag: Wünsche aus dem Auftrag (Thema, Zielgruppe, Gliederung, Umfang), die nicht umgesetzt sind, obwohl das
  Material dafür reicht
- darstellung: Fehler im Aussehen (abgeschnitten, überlappend, zu voll, leere Seite oder Folie, falsche Reihenfolge)
Leere Listen, wenn nichts zu beanstanden ist. Stellen [OFFEN: …] sind richtig, wo Material fehlt, und kein Fehler.
{vorher}
Findest du Fehler, korrigiere zusätzlich {ordner}/beschreibung.json. Dann wird neu gebaut und du prüfst noch einmal.
Ist alles in Ordnung, ändere beschreibung.json nicht.
{kurz}
Deine Antwort ist die Kurzfassung für Jan (höchstens 6 Zeilen, ohne Markdown): was drin ist, was offen ist und was
er vor dem Vortrag bzw. der Abgabe ergänzen oder prüfen sollte."""


def bericht_pruefen(text: str | None, nummern: list[int] | None = None) -> list[str]:
    """Probleme im Kontrollbericht für Präsentation und Bericht. Leer heißt fertig. nummern bleibt ungenutzt
    (Signatur wie zusammenfassen.bericht_pruefen)."""
    if text is None:
        return ["kontrolle.json fehlt"]
    try:
        b = json.loads(text)
    except json.JSONDecodeError as e:
        return [f"kontrolle.json ist kein gültiges JSON: {e}"]
    if not isinstance(b, dict):
        return ["kontrolle.json muss ein Objekt sein"]
    probleme = []
    unbekannt = set(b) - set(FELDER_BERICHT)
    if unbekannt:
        probleme.append(f"Unbekannte Felder: {', '.join(sorted(unbekannt))}")
    fehlend = [n for n in FELDER_BERICHT if n not in b]
    if fehlend:
        probleme.append(f"Felder fehlen: {', '.join(fehlend)}")
    titel = {"erfunden": "Dazuerfunden", "auftrag": "Auftrag nicht umgesetzt", "darstellung": "Darstellung"}
    for name in FELDER_BERICHT:
        wert = b.get(name, [])
        if not isinstance(wert, list):
            probleme.append(f"{name} muss eine Liste sein")
            continue
        probleme += [f"{titel[name]}: {t}" for t in wert]
    return probleme


def _art(kennung: str, name: str, renderer_art: str, endung: str, abschnitte, kontext: str, einheit: str,
         woerter: dict[str, str]) -> z.Art:
    def setzen(t: str) -> str:
        for marke, wort in woerter.items():
            t = t.replace(marke, wort)
        return t
    return z.Art(kennung, name, renderer_art, endung, abschnitte, setzen(kontext + START), setzen(ANTWORT),
                 setzen(KONTROLLE), BERICHT_FORMAT, bericht_pruefen, einheit=einheit, abbruch=ABBRUCH,
                 abbruch_text=f"Zu wenig Material für {woerter['§EIN§']}: ")


PRAESENTATION = _art("praesentation", "Präsentation", "folien", ".pptx", ("Allgemein", "Folien"),
                     PRAESENTATION_KONTEXT, "Folien",
                     {"§KURZ§": "eine kurze Präsentation", "§FERTIG§": "die fertige Präsentation",
                      "§DER§": "Die Präsentation", "§EIN§": "eine Präsentation"})
BERICHT = _art("bericht", "Bericht", "bericht", ".docx", ("Allgemein", "Zusammenfassung", "Bericht"),
               BERICHT_KONTEXT, "Seiten",
               {"§KURZ§": "einen kurzen Bericht", "§FERTIG§": "den fertigen Bericht", "§DER§": "Der Bericht",
                "§EIN§": "einen Bericht"})
ARTEN = {a.kennung: a for a in (z.ZUSAMMENFASSUNG, PRAESENTATION, BERICHT)}
