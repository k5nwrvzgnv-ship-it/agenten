"""Prüfschritt: ein unabhängiger Prüfer bewertet den Ablauf, der Autor überarbeitet ihn (Jan 29.10.2026).

Der Prüfer läuft in einer neuen Sitzung (sieht nicht, wie der Ablauf entstanden ist) und bewertet die
Spielfassung gegen die Rubrik in theater.toml. Liegt ein Kriterium unter „gut“, überarbeitet der Autor in seiner
Sitzung (kennt das Stück) den Ablauf; danach prüft wieder ein neuer Prüfer. Höchstens MAX_UEBERARBEITUNGEN Runden.
Python prüft die Antwort des Prüfers (jedes Kriterium genau einmal, Stufe, Beleg, Verbesserung unter der
Schwelle); die Überarbeitung prüft fassung.pruefen wie den ersten Ablauf.
"""

MAX_UEBERARBEITUNGEN = 2
MAX = {"beleg": 500, "verbesserung": 500, "aenderung": 400, "staerke": 300}


def unter_schwelle(kritik: dict, rubrik: dict) -> list[dict]:
    """Bewertungen unter der Mindeststufe, in Reihenfolge der Rubrik."""
    stufen = rubrik["stufen"]["liste"]
    grenze = stufen.index(rubrik["stufen"]["mindestens"])
    return [b for b in kritik["kriterien"] if stufen.index(b["stufe"]) < grenze]


def pruefen(daten: dict, rubrik: dict) -> list[str]:
    """Alle Fehler auf einmal (leer = in Ordnung)."""
    fehler: list[str] = []
    stufen = rubrik["stufen"]["liste"]
    ids = [k["id"] for k in rubrik["kriterium"]]
    grenze = stufen.index(rubrik["stufen"]["mindestens"])
    bewertungen = daten.get("kriterien")
    if not isinstance(bewertungen, list):
        return ["kriterien: Liste erwartet"]
    gesehen: dict[str, int] = {}
    for i, b in enumerate(bewertungen):
        wo = f"kriterien[{i}]"
        if not isinstance(b, dict) or b.get("id") not in ids:
            fehler.append(f"{wo}.id: eins von {', '.join(ids)}")
            continue
        gesehen[b["id"]] = gesehen.get(b["id"], 0) + 1
        if b.get("stufe") not in stufen:
            fehler.append(f"{wo}.stufe: eine von {', '.join(stufen)}")
            continue
        for feld, pflicht in (("beleg", True), ("verbesserung", stufen.index(b["stufe"]) < grenze)):
            wert = b.get(feld)
            if wert is None and not pflicht:
                continue
            if not isinstance(wert, str) or not wert.strip():
                fehler.append(f"{wo}.{feld}: Text fehlt" + (" (Pflicht unter „gut“)" if feld == "verbesserung" else ""))
            elif len(wert) > MAX[feld]:
                fehler.append(f"{wo}.{feld}: höchstens {MAX[feld]} Zeichen, sind {len(wert)}")
    for kid in ids:
        if gesehen.get(kid, 0) != 1:
            fehler.append(f"Kriterium {kid} kommt {gesehen.get(kid, 0)}-mal vor, genau einmal nötig")
    for feld, n_max, laenge in (("staerken", 5, MAX["staerke"]), ("wichtigste_aenderungen", 6, MAX["aenderung"])):
        liste = daten.get(feld, [])
        if not isinstance(liste, list) or len(liste) > n_max or \
                any(not isinstance(x, str) or not x.strip() or len(x) > laenge for x in liste):
            fehler.append(f"{feld}: höchstens {n_max} Texte, je höchstens {laenge} Zeichen")
    if not fehler and unter_schwelle(daten, rubrik) and not daten.get("wichtigste_aenderungen"):
        fehler.append("wichtigste_aenderungen: unter „gut“ mindestens eine Änderung nennen")
    return fehler


def _rubrik_text(rubrik: dict) -> str:
    return "\n".join(f"- {k['id']} – {k['name']}\n  Prüffrage: {k['frage']}\n  „gut“ heißt: {k['gut']}"
                     for k in rubrik["kriterium"])


def prompt(ausgabe: str, spielfassung: str, ablauf: str, vorgaben: str, grundlagen: str, buch: list[str],
           szenenkarte: str, rubrik: dict, runde: int) -> str:
    stufen = ", ".join(f"„{s}“" for s in rubrik["stufen"]["liste"])
    buchteile = "\n".join(f"- {t}" for t in buch)
    return f"""Du bist ein erfahrener Theaterpädagoge und prüfst einen Entwurf für Lia, Lehrerin für Darstellendes
Spiel. Ihr Kurs (18 SuS, Oberstufe) spielt eine eigene Fassung von „Der nackte Wahnsinn“ (Michael Frayn), 35–40
Minuten. Du hast den Entwurf nicht geschrieben. Bewerte streng und ehrlich, so wie eine erfahrene Kollegin, die
will, dass die Aufführung gelingt. „gut“ nur, wenn die „gut“-Beschreibung erfüllt ist. Nicht schönfärben.
Prüfrunde {runde}.

Lies zuerst mit Read:
1. Lias Vorgaben, ihre Ideen und ihre Unsicherheit: {vorgaben}
2. Die Spielfassung (Ablauf mit Spielideen, Originaltext wörtlich, neuer Text): {spielfassung}
3. Den Ablauf als JSON (Minuten, Muss-Punkte, Varianten, Vorschläge): {ablauf}
4. Die Szenenkarte des Originals (was das Stück hergibt): {szenenkarte}
5. Was die SuS können: {grundlagen}
6. Lias Fachbuch (Kündiger, Praxis Schultheater), als Maßstab für Spielweisen und Probenarbeit:
{buchteile}

Rubrik (Stufen: {stufen}):
{_rubrik_text(rubrik)}

Schreibe die Datei {ausgabe} (JSON, sonst nichts):
{{
  "kriterien": [
    {{"id": "steigerung", "stufe": "ansatzweise",
      "beleg": "Was erfüllt ist oder fehlt, mit Baustein-ids (z. B. B07, B16), höchstens 500 Zeichen",
      "verbesserung": "Pflicht unter „gut“: was genau zu ändern ist, spielbar und konkret, höchstens 500 Zeichen"}}
  ],
  "staerken": ["höchstens 5, was unbedingt bleiben soll"],
  "wichtigste_aenderungen": ["höchstens 6, nach Wirkung geordnet, je höchstens 400 Zeichen"]
}}
Jedes Kriterium genau einmal. Ändere selbst nichts am Ablauf. Antworte am Ende nur mit „fertig“."""


def kritik_text(kritik: dict, rubrik: dict) -> str:
    """Bewertung als Text für die Überarbeitung."""
    namen = {k["id"]: k["name"] for k in rubrik["kriterium"]}
    zeilen = []
    for b in kritik["kriterien"]:
        zeilen.append(f"- {b['id']} ({namen[b['id']]}): {b['stufe']}. {b['beleg']}")
        if b.get("verbesserung"):
            zeilen.append(f"  Verbesserung: {b['verbesserung']}")
    if kritik.get("staerken"):
        zeilen += ["Stärken, die bleiben sollen:"] + [f"- {s}" for s in kritik["staerken"]]
    if kritik.get("wichtigste_aenderungen"):
        zeilen += ["Wichtigste Änderungen:"] + [f"- {a}" for a in kritik["wichtigste_aenderungen"]]
    return "\n".join(zeilen)


def ueberarbeitung_prompt(ausgabe: str, alt: str, kritik: dict, rubrik: dict, lesen: list[str]) -> str:
    """Für den Autor (seine Sitzung, sonst eine neue: dann liest er die Dateien in `lesen`)."""
    dateien = "\n".join(f"- {d}" for d in lesen)
    unter = ", ".join(b["id"] for b in unter_schwelle(kritik, rubrik))
    return f"""Ein unabhängiger Prüfer hat deinen Ablauf ({alt}) bewertet. Kennst du Stück, Szenenkarte und Lias
Vorgaben noch nicht (neue Sitzung), lies zuerst:
{dateien}

Bewertung:
{kritik_text(kritik, rubrik)}

Überarbeite den Ablauf so, dass die Kriterien unter „gut“ ({unter}) mindestens „gut“ erreichen, ohne die
Stärken zu verlieren. Du darfst Bausteine umbauen, streichen, neu anlegen und andere Originalstellen wählen.
Übernimmst du einen Punkt des Prüfers nicht, sag warum. Schreibe die ganze Datei {ausgabe} neu, im selben Format
wie {alt} und mit denselben Regeln (Minuten, jede Nummer nur einmal, jeder Muss-Punkt genau einmal, Varianten,
zuspitzung), dazu ein Feld "aenderungen": Liste mit höchstens 8 Texten (je höchstens 400 Zeichen), was du
geändert hast und warum, oder warum du einen Punkt nicht übernimmst.
Antworte am Ende nur mit „fertig“."""


def aenderungen_pruefen(daten: dict) -> list[str]:
    a = daten.get("aenderungen")
    if not isinstance(a, list) or not 1 <= len(a) <= 8 or \
            any(not isinstance(x, str) or not x.strip() or len(x) > MAX["aenderung"] for x in a):
        return [f"aenderungen: 1 bis 8 Texte, je höchstens {MAX['aenderung']} Zeichen"]
    return []


def bloecke(kritik: dict, rubrik: dict, ueberarbeitungen: int, aenderungen: list[str]) -> list[dict]:
    """Abschnitt für das Ablauf-Dokument: letzte Bewertung und was nach den Prüfungen geändert wurde."""
    namen = {k["id"]: k["name"] for k in rubrik["kriterium"]}
    wie_oft = {0: "nicht überarbeitet", 1: "einmal überarbeitet"}.get(ueberarbeitungen, f"{ueberarbeitungen}-mal überarbeitet")
    unter = unter_schwelle(kritik, rubrik)
    stand = ("Alle Kriterien mindestens „gut“." if not unter else
             f"Noch unter „gut“: {', '.join(namen[b['id']] for b in unter)}.")
    b = [{"typ": "ueberschrift", "text": "Prüfung"},
         {"typ": "absatz", "text": f"Ein zweiter, unabhängiger Durchgang hat den Ablauf gegen {len(rubrik['kriterium'])} "
                                   f"Kriterien geprüft (aus deinen Vorgaben abgeleitet). Der Ablauf wurde danach "
                                   f"{wie_oft}. {stand}"},
         {"typ": "tabelle", "kopf": ["Kriterium", "Stufe", "Begründung"],
          "zeilen": [[namen[x["id"]], x["stufe"], x["beleg"]] for x in kritik["kriterien"]]}]
    if aenderungen:
        b += [{"typ": "ueberschrift", "text": "Nach der Prüfung geändert", "ebene": 2},
              {"typ": "liste", "punkte": aenderungen}]
    if unter:
        b += [{"typ": "ueberschrift", "text": "Was der Prüfer noch vorschlägt", "ebene": 2},
              {"typ": "liste", "punkte": [f"{namen[x['id']]}: {x['verbesserung']}" for x in unter]}]
    return b
