"""Kernstellen vom Seitenbild (Quellen mit scan_id, Liszt): Prompts und Prüfungen (ohne Netz).

Ablauf (Jan, 25.10.2026), gesteuert von agent.py:
1. Auswahl: ein Claude-Lauf (Opus) mit der OCR-Textfassung nur zur Orientierung. Ergebnis je Stelle:
   seiten (Druckseiten, höchstens zwei aufeinanderfolgende), anfang, ende (Wörter), position, zweck.
   auswahl_pruefen() nimmt nur gültige Einträge, höchstens MAX_STELLEN.
2. Python lädt die Seitenbilder (agentkit.abruf), legt sie als data/bilder/<id>/s<seite>.jpg ab.
3. Zwei Abschriften in getrennten Sitzungen ohne OCR (abschrift_prompt), bei Abweichung eine dritte
   nur für die strittigen Stellen.
4. stelle_pruefen(): Abschriften vergleichen, Länge, unscharf gegen die OCR (abschrift.py).
"""

import json
from pathlib import Path

import abschrift

MIN_STELLEN, MAX_STELLEN = 3, 5
MAX_ZEICHEN = 900  # über eine Seitengrenze hinweg darf es etwas länger sein als bei Kant


class SeitenbildFehler(Exception):
    pass


def auswahl_prompt(quelle: dict, textpfad: str, ausgabe: str, reihe: str, von: int, bis: int) -> str:
    return f"""Aufgabe: Wähle Kernstellen aus einem Aufsatz für Lias Unterricht (Lehrerin, Examensstunde).

Text: {quelle['autor']}, {quelle['werk']}. Ausgabe: {quelle['ausgabe']}.
Die Datei {textpfad} enthält die automatische Texterkennung (OCR) der Druckseiten {von} bis {bis}, je Seite
mit einer Zeile "--- Seite N". Die OCR ist schlecht: Die Fraktur wurde als Antiqua gelesen ("unb" = und,
"ber" = der, "fein" = sein, "©träfe" = Strafe, "3wecf" = Zweck). Nutze sie NUR zur Orientierung.
Lies keine anderen Dateien.

Kontext der Reihe:
{reihe or '(kein Reihenkontext vorhanden)'}
Lia stellt von Liszt als Gegenposition zu Kant dar: Zweckstrafe (Besserung, Abschreckung,
Unschädlichmachung), Strafe als Schutz der Gesellschaft statt Vergeltung.

Wähle {MIN_STELLEN} bis {MAX_STELLEN} Stellen, die diese Position am klarsten zeigen und für Klasse 8 (vereinfacht)
als Quellenauszug taugen, je höchstens etwa drei Sätze. Noch KEIN Zitat. Je Stelle:
- seiten: Liste der Druckseiten (eine Seite oder zwei aufeinanderfolgende)
- anfang: die ersten drei bis fünf Wörter der Stelle, in richtiger Schreibung (aus der OCR erschlossen)
- ende: die letzten drei bis fünf Wörter der Stelle, ebenso
- position: kurz, z. B. Besserung, Abschreckung, Unschädlichmachung, Zweckstrafe, Kritik der Vergeltung
- zweck: ein Satz für Lia: wozu die Stelle in der Reihe dient

Schreibe das Ergebnis NUR in die Datei {ausgabe}, als JSON:
{{"stellen": [{{"seiten": [0], "anfang": "...", "ende": "...", "position": "...", "zweck": "..."}}]}}
Antworte danach mit einem Satz."""


def abschrift_prompt(stellen: list[dict], bilder: dict[int, str], ausgabe: str) -> str:
    """stellen: [{nr, seiten, anfang, ende}], bilder: {seite: Pfad relativ zum Agent-Ordner}."""
    liste = "\n".join(
        f"- Stelle {s['nr']}: Bild(er) {', '.join(bilder[x] for x in s['seiten'])} (Druckseite "
        f"{'/'.join(str(x) for x in s['seiten'])}). Beginnt etwa mit: \"{s['anfang']}\". Endet etwa mit: \"{s['ende']}\"."
        for s in stellen)
    return f"""Aufgabe: Schreibe Textstellen von Seitenbildern eines Drucks von 1883 (Fraktur) ab.

Lies NUR die genannten Bilddateien, keine anderen Dateien.
{liste}

Die Anfangs- und Endwörter sind aus einer schlechten Texterkennung erschlossen und können leicht abweichen.
Suche die Stelle auf dem Bild und schreibe sie vollständig ab, vom Satzanfang bis zum Satzende.

Regeln:
- Buchstabengetreu, wie gedruckt. Alte Schreibung belassen (z. B. Theil, seyn, Thatsache). Nichts verbessern,
  nichts modernisieren, nichts auslassen, keine Auslassungszeichen.
- Langes ſ als s schreiben. ß bleibt ß.
- Silbentrennung am Zeilenende auflösen (das Trennzeichen sieht aus wie "=" oder "-"); Zeilenumbrüche als
  Leerzeichen. Gesperrt Gedrucktes normal schreiben.
- Fußnotenzeichen (hochgestellte Ziffern) und Fußnoten weglassen.
- Ist ein Wort nicht sicher lesbar, schreibe an seiner Stelle [?].

Schreibe das Ergebnis NUR in die Datei {ausgabe}, als JSON:
{{"stellen": [{{"nr": 1, "zitat": "..."}}]}}
Antworte danach mit einem Satz."""


def _json_stellen(pfad: Path) -> list:
    try:
        daten = json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise SeitenbildFehler(f"Antwortdatei {Path(pfad).name} fehlt oder ist kein JSON: {e}") from None
    stellen = daten.get("stellen") if isinstance(daten, dict) else None
    if not isinstance(stellen, list):
        raise SeitenbildFehler(f"Antwortdatei {Path(pfad).name}: Feld stellen fehlt")
    return stellen


def auswahl_pruefen(pfad: Path, von: int, bis: int) -> tuple[list[dict], list[str]]:
    """(gültige Stellen mit nr, Gründe für verworfene). Gültig: Seiten im Bereich, eine oder zwei
    aufeinanderfolgende, anfang/ende/position/zweck nicht leer. Höchstens MAX_STELLEN."""
    gut, schlecht = [], []
    for s in _json_stellen(pfad):
        seiten = s.get("seiten") if isinstance(s, dict) else None
        if (not isinstance(seiten, list) or not 1 <= len(seiten) <= 2
                or not all(isinstance(x, int) and not isinstance(x, bool) and von <= x <= bis for x in seiten)
                or (len(seiten) == 2 and seiten[1] != seiten[0] + 1)):
            schlecht.append(f"Seiten ungültig: {seiten!r}")
            continue
        if not all(isinstance(s.get(f), str) and s[f].strip() for f in ("anfang", "ende", "position", "zweck")):
            schlecht.append(f"S. {seiten[0]}: anfang, ende, position oder zweck fehlt")
            continue
        gut.append({"nr": len(gut) + 1, "seiten": seiten, **{f: s[f].strip() for f in ("anfang", "ende", "position", "zweck")}})
    if len(gut) > MAX_STELLEN:
        schlecht.append(f"{len(gut) - MAX_STELLEN} Stellen über {MAX_STELLEN} nicht genommen")
        gut = gut[:MAX_STELLEN]
    return gut, schlecht


def abschriften_lesen(pfad: Path) -> dict[int, str]:
    """{nr: zitat} aus einer Abschrift-Datei. Fehlt die Datei: SeitenbildFehler."""
    aus = {}
    for s in _json_stellen(pfad):
        if isinstance(s, dict) and isinstance(s.get("nr"), int) and isinstance(s.get("zitat"), str):
            aus[s["nr"]] = s["zitat"].strip()
    return aus


def stelle_pruefen(auswahl: dict, fassungen: list[str], ocr: dict[int, str], scan_links: dict,
                   schwelle: float = abschrift.SCHWELLE) -> tuple[dict | None, str | None]:
    """(Registerstelle, None) oder (None, Grund). fassungen: zwei oder drei Abschriften derselben Stelle."""
    zitat, unterschiede = abschrift.vergleichen(fassungen)
    if zitat is None:
        return None, "Abschriften ungleich: " + "; ".join(unterschiede[:8])
    if not abschrift.MIN_ZEICHEN <= len(zitat) <= MAX_ZEICHEN:
        return None, f"Länge {len(zitat)} Zeichen, erlaubt {abschrift.MIN_ZEICHEN} bis {MAX_ZEICHEN}"
    wert = abschrift.aehnlichkeit(zitat, "\n".join(ocr[s] for s in auswahl["seiten"]))
    if wert < schwelle:
        return None, f"passt nicht zur OCR der Seite (Ähnlichkeit {wert:.3f} < {schwelle})"
    return {
        "seite": auswahl["seiten"][0], "seiten": auswahl["seiten"], "zitat": zitat,
        "position": auswahl["position"], "zweck": auswahl["zweck"],
        "geprueft": False,  # nicht wörtlich gegen einen sicheren Text geprüft: Lia prüft am Scan
        "am_scan_pruefen": True,
        "scan_link": {str(s): scan_links[str(s)] for s in auswahl["seiten"]},
        "pruefung": {"abschriften_gleich": "2 von 3" if unterschiede else "2 von 2",
                     "ocr_aehnlichkeit": wert, "schwelle": schwelle},
    }, None
