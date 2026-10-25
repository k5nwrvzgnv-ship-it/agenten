"""Kernstellen eines Primärtexts: Prompt für Claude, Antwort lesen, wörtlich prüfen (ohne Netz).

Grundsatz: Claude wählt aus, Python prüft. Claude liest nur die Textfassung data/text/<id>.txt und
schreibt eine JSON-Datei data/kernstellen/<id>.json:
  {"stellen": [{"seite": 331, "zitat": "...", "position": "Vergeltung", "zweck": "..."}]}
pruefen() nimmt jede Stelle nur, wenn das Zitat mit agentkit.wortlaut.steht_in auf genau ihrer Seite
steht, nicht zu lang ist und nicht doppelt vorkommt. Was durchfällt, bekommt Claude höchstens einmal
zurück (nachbesserung_prompt), danach wird es gestrichen und Jan gemeldet (agent.py).
"""

import json
from pathlib import Path

from agentkit import wortlaut

MIN_STELLEN, MAX_STELLEN = 3, 6
MAX_ZEICHEN = 700        # etwa drei lange Sätze. Sätze zählen geht nicht sicher ("d. i.", "u. dergl.").
MAX_SAETZE = 3           # nur im Prompt
FELDER = ("seite", "zitat", "position", "zweck")


class KernstellenFehler(Exception):
    pass


def reihe_text(reihen: list[dict]) -> str:
    """Prompt-Abschnitt zur Reihe Straftheorien aus lia/unterricht/reihen.toml (nur gelesen)."""
    for r in reihen:
        if "Straftheorien" in r.get("titel", ""):
            teile = [f"Ethik Klasse {r.get('klasse', '?')}, Reihe {r['titel']}."]
            for feld, name in (("lerngruppe", "Lerngruppe"), ("notizen", "Planung")):
                if r.get(feld):
                    teile.append(f"{name}: {r[feld]}")
            return "\n".join(teile)
    return ""


def prompt(quelle: dict, textpfad: str, ausgabe: str, reihe: str) -> str:
    personen = quelle.get("autor", "")
    return f"""Aufgabe: Wähle Kernstellen aus einem Primärtext für Lias Unterricht (Lehrerin, Examensstunde).

Text: {personen}, {quelle['werk']}. Ausgabe: {quelle['ausgabe']}.
Lies NUR die Datei {textpfad}. Sie ist in Seiten geteilt, jede beginnt mit einer Zeile "--- Seite N"
(N = Seite der Vorlage). Lies keine anderen Dateien.

Kontext der Reihe:
{reihe or '(kein Reihenkontext vorhanden)'}

Wähle {MIN_STELLEN} bis {MAX_STELLEN} Stellen, die die Position des Autors zum Zweck der Strafe am klarsten zeigen und
für Klasse 8 (vereinfacht) als Quellenauszug taugen. Je Stelle:
- seite: die Zahl N der Seite, auf der das ganze Zitat steht. Ein Zitat darf nicht über eine Seitengrenze gehen.
- zitat: WÖRTLICH aus der Datei kopiert, Zeichen für Zeichen, mit der Schreibweise der Vorlage (alte
  Rechtschreibung, "=" als Bindestrich, Zeilenumbrüche darfst du durch Leerzeichen ersetzen). Nichts
  auslassen, nichts ergänzen, keine Auslassungszeichen. Höchstens {MAX_SAETZE} Sätze.
- position: kurz, z. B. Vergeltung, Besserung, Abschreckung, Sicherung, Menschenwürde.
- zweck: ein Satz für Lia: wozu die Stelle in der Reihe dient.

Schreibe das Ergebnis NUR in die Datei {ausgabe}, als JSON:
{{"stellen": [{{"seite": 0, "zitat": "...", "position": "...", "zweck": "..."}}]}}
Antworte danach mit einem Satz. Python prüft jedes Zitat wörtlich gegen die Seite."""


def nachbesserung_prompt(durchgefallen: list[dict], textpfad: str, ausgabe: str) -> str:
    liste = "\n".join(f"- Seite {d['stelle'].get('seite')}: {d['grund']}. Zitat: {d['stelle'].get('zitat', '')!r}"
                      for d in durchgefallen)
    return f"""Diese Stellen haben die wörtliche Prüfung nicht bestanden:
{liste}

Korrigiere nur diese Stellen: Zitat wörtlich aus {textpfad} kopieren und die richtige Seite angeben,
oder die Stelle durch eine andere ersetzen. Schreibe in {ausgabe} NUR die korrigierten bzw. ersetzten
Stellen, im selben JSON-Format. Die bestandenen Stellen bleiben ohnehin erhalten."""


def antwort_lesen(pfad: Path) -> list[dict]:
    """Stellen aus Claudes JSON-Datei. Kaputte Datei: KernstellenFehler. Einzelne Stellen prüft pruefen()."""
    try:
        daten = json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise KernstellenFehler(f"Antwortdatei {Path(pfad).name} fehlt oder ist kein JSON: {e}") from None
    stellen = daten.get("stellen") if isinstance(daten, dict) else None
    if not isinstance(stellen, list):
        raise KernstellenFehler(f"Antwortdatei {Path(pfad).name}: Feld stellen fehlt")
    return stellen


def _grund(stelle, seiten: dict[int, str], schon: list[dict]) -> str | None:
    if not isinstance(stelle, dict) or any(f not in stelle for f in FELDER):
        return f"Felder fehlen (nötig: {', '.join(FELDER)})"
    seite, zitat = stelle["seite"], stelle["zitat"]
    if not isinstance(seite, int) or isinstance(seite, bool) or seite not in seiten:
        return f"Seite {seite!r} gibt es in der Textfassung nicht"
    if not isinstance(zitat, str) or not zitat.strip():
        return "Zitat leer"
    if len(zitat) > MAX_ZEICHEN:
        return f"Zitat zu lang (höchstens {MAX_ZEICHEN} Zeichen, etwa {MAX_SAETZE} Sätze)"
    if not all(isinstance(stelle[f], str) and stelle[f].strip() for f in ("position", "zweck")):
        return "position oder zweck leer"
    if not wortlaut.steht_in(zitat, seiten[seite]):
        return f"Zitat steht nicht wörtlich auf Seite {seite}"
    kurz = wortlaut.normalisieren(zitat)
    if any(kurz in wortlaut.normalisieren(s["zitat"]) or wortlaut.normalisieren(s["zitat"]) in kurz for s in schon):
        return "Zitat doppelt oder überschneidet sich mit einer anderen Stelle"
    return None


def pruefen(stellen: list, textfassung: str, schon: list[dict] | None = None) -> tuple[list[dict], list[dict]]:
    """(bestanden, durchgefallen). bestanden: Registerform {seite, zitat, position, zweck, geprueft}.
    schon: bereits bestandene Stellen (gegen Doppelte). durchgefallen: [{stelle, grund}]."""
    seiten = wortlaut.seiten(textfassung)
    gut, schlecht = [], []
    for s in stellen:
        grund = _grund(s, seiten, (schon or []) + gut)
        if grund:
            schlecht.append({"stelle": s, "grund": grund})
            continue
        e = {"seite": s["seite"], "zitat": s["zitat"].strip(), "position": s["position"].strip(),
             "zweck": s["zweck"].strip(), "geprueft": True}
        gut.append(e)
    return gut, schlecht
