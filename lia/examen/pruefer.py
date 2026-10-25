"""Prüfer-Lauf: bewertet jede Skizze gegen die Rubrik und schreibt Kolloquiumsfragen.

Plan Examensreihe, Schritt 4 (Jan 25.10.2026). Eigener Claude-Lauf in neuer Sitzung: Der Prüfer sieht die
Skizzen und den Kontext, nicht den Verlauf des Skizzen-Laufs. Python prüft, dass jedes Kriterium genau einmal mit
einer gültigen Stufe und einem Beleg bewertet ist und je Skizze genau fünf Fragen da sind.
"""

import json
from pathlib import Path

FRAGEN = 5


class PrueferFehler(Exception):
    """Antwort fehlt oder ist kein JSON. Der Text ist für Jan."""


def prompt(kontext_text: str, skizzen_md: str, rubrik: dict, ausgabe: str) -> str:
    stufen = ", ".join(f"„{s}“" for s in rubrik["stufen"]["liste"])
    kriterien = "\n".join(f"- {k['id']} – {k['name']}\n  Prüffrage: {k['frage']}\n  „gut“ heißt: {k['gut']}"
                          for k in rubrik["kriterium"])
    return f"""Du bist Prüfer für Lias Examensreihe (Referendariat Ethik, Berlin). Du bewertest drei
Grobskizzen streng und ehrlich gegen die Rubrik, so wie ein Prüfungsausschuss die schriftliche Planung lesen würde.
Nicht schönfärben: „gut“ nur, wenn die „gut“-Beschreibung erfüllt ist. Fehlt etwas, sag was.

{kontext_text}

# Rubrik (Stufen: {stufen})
{kriterien}

# Die drei Skizzen
{skizzen_md}

# Auftrag
1. Für jede Skizze jedes Kriterium genau einmal: kriterium (id), stufe (genau eine der Stufen oben), beleg
   (ein Satz mit Bezug auf die Skizze: was erfüllt ist oder was fehlt).
2. Je Skizze genau {FRAGEN} Kolloquiumsfragen, wie sie im Reflexionsgespräch kommen könnten: nach Begründungen,
   Alternativen, Lerngruppe, fachlicher Richtigkeit. Kurz und konkret auf diese Skizze bezogen.
3. Je Skizze staerkste_schwaeche: ein Satz, was zuerst verbessert werden müsste.

# Ausgabe
Schreibe mit Write genau diese Datei: {ausgabe}
Nur JSON: {{"skizzen": [{{"kennung": "A", "bewertung": [{{"kriterium": "id", "stufe": "...", "beleg": "..."}}],
"kolloquiumsfragen": ["..."], "staerkste_schwaeche": "..."}}]}}
Deine letzte Antwort ist ein Satz: welche Skizze du insgesamt am stärksten findest und warum."""


def nachbesserung_prompt(fehler: list[str], ausgabe: str) -> str:
    return ("Die Prüfung deiner Datei hat Fehler gefunden. Verbessere genau diese Punkte und schreibe die "
            f"ganze Datei {ausgabe} neu (gleiches Format):\n" + "\n".join(f"- {f}" for f in fehler))


def antwort_lesen(pfad: Path) -> dict:
    try:
        daten = json.loads(Path(pfad).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise PrueferFehler(f"Claude hat {Path(pfad).name} nicht geschrieben") from None
    except json.JSONDecodeError as e:
        raise PrueferFehler(f"{Path(pfad).name} ist kein JSON: {e}") from None
    if not isinstance(daten, dict):
        raise PrueferFehler(f"{Path(pfad).name}: erwartet ein Objekt mit skizzen")
    return daten


def pruefen(daten: dict, rubrik: dict, kennungen: list[str]) -> list[str]:
    """Fehlerliste (leer = vollständig)."""
    skizzen = daten.get("skizzen")
    if not isinstance(skizzen, list):
        return ["skizzen fehlt oder ist keine Liste"]
    fehler = []
    if sorted(s.get("kennung") or "" for s in skizzen) != sorted(kennungen):
        fehler.append(f"Bewertung für genau diese Skizzen erwartet: {kennungen}")
    ids = [k["id"] for k in rubrik["kriterium"]]
    stufen = rubrik["stufen"]["liste"]
    for sk in skizzen:
        k = sk.get("kennung", "?")
        bewertung = sk.get("bewertung") if isinstance(sk.get("bewertung"), list) else []
        gesehen = [b.get("kriterium") for b in bewertung]
        fehlend = [i for i in ids if i not in gesehen]
        if fehlend:
            fehler.append(f"Skizze {k}: Kriterien fehlen: {fehlend}")
        doppelt = sorted({i for i in gesehen if gesehen.count(i) > 1})
        if doppelt:
            fehler.append(f"Skizze {k}: Kriterien doppelt: {doppelt}")
        fremd = [i for i in gesehen if i not in ids]
        if fremd:
            fehler.append(f"Skizze {k}: unbekannte Kriterien: {fremd}")
        for b in bewertung:
            if b.get("stufe") not in stufen:
                fehler.append(f"Skizze {k}, {b.get('kriterium')}: Stufe {b.get('stufe')!r} gibt es nicht")
            if not str(b.get("beleg", "")).strip():
                fehler.append(f"Skizze {k}, {b.get('kriterium')}: beleg fehlt")
        fragen = sk.get("kolloquiumsfragen")
        if not isinstance(fragen, list) or len([f for f in fragen if str(f).strip()]) != FRAGEN:
            fehler.append(f"Skizze {k}: genau {FRAGEN} Kolloquiumsfragen erwartet")
        if not str(sk.get("staerkste_schwaeche", "")).strip():
            fehler.append(f"Skizze {k}: staerkste_schwaeche fehlt")
    return fehler


def unter_schwelle(sk: dict, rubrik: dict) -> list[str]:
    """Kriterien-ids dieser Skizze unter der Mindeststufe (Abbruchkriterium der Runden)."""
    stufen = rubrik["stufen"]["liste"]
    grenze = stufen.index(rubrik["stufen"]["mindestens"])
    return [b["kriterium"] for b in sk["bewertung"] if stufen.index(b["stufe"]) < grenze]


def darstellen(sk: dict, rubrik: dict) -> str:
    namen = {k["id"]: k["name"] for k in rubrik["kriterium"]}
    reihenfolge = {k["id"]: i for i, k in enumerate(rubrik["kriterium"])}
    unter = unter_schwelle(sk, rubrik)
    zeilen = [f"### Prüfung Skizze {sk['kennung']}", "",
              f"Unter „{rubrik['stufen']['mindestens']}“: {len(unter)} von {len(sk['bewertung'])} Kriterien. "
              f"Zuerst verbessern: {sk['staerkste_schwaeche']}", "",
              "| Kriterium | Stufe | Beleg |", "|---|---|---|"]
    for b in sorted(sk["bewertung"], key=lambda b: reihenfolge[b["kriterium"]]):
        stufe = f"**{b['stufe']}**" if b["kriterium"] in unter else b["stufe"]
        zeilen.append(f"| {namen[b['kriterium']]} | {stufe} | {b['beleg']} |")
    zeilen += ["", "**Kolloquiumsfragen:**", *(f"{i}. {f}" for i, f in enumerate(sk["kolloquiumsfragen"], 1))]
    return "\n".join(zeilen)
