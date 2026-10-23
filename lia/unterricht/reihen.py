"""Reihenkontext: Lias laufende Unterrichtsreihen (reihen.toml) für jeden Lauf.

Grund (lia/auswertung, 23.10.2026): Viele Korrekturen in Lias Chats entstanden, weil Claude Reihenfrage, Klasse
oder schon behandelte Positionen nicht kannte. reihen.toml pflegt Jan von Hand; laden prüft sie, prompt_reihen
macht daraus einen Prompt-Abschnitt.
"""

import tomllib
from pathlib import Path

PFLICHT = ("klasse", "reihenfrage")
TEXTE = ("fach", "klasse", "titel", "reihenfrage", "lerngruppe", "notizen")
LISTEN = ("behandelt", "merksaetze")


class ReihenFehler(Exception):
    """reihen.toml ist kaputt oder unvollständig. Der Text ist für Jan."""


def laden(pfad: Path) -> list[dict]:
    """Alle Reihen aus der Datei, geprüft. Fehlt die Datei, gibt es keine Reihen."""
    if not pfad.exists():
        return []
    try:
        daten = tomllib.loads(pfad.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ReihenFehler(f"{pfad.name} ist kein gültiges TOML: {e}") from None
    if set(daten) - {"reihe"}:
        raise ReihenFehler(f"{pfad.name}: unbekannte Einträge {sorted(set(daten) - {'reihe'})}, erwartet [[reihe]]")
    reihen = daten.get("reihe", [])
    if not isinstance(reihen, list):
        raise ReihenFehler(f"{pfad.name}: Reihen als [[reihe]] schreiben, nicht [reihe]")
    for nr, reihe in enumerate(reihen, 1):
        unbekannt = set(reihe) - set(TEXTE) - set(LISTEN)
        if unbekannt:
            raise ReihenFehler(f"{pfad.name}, Reihe {nr}: unbekannte Felder {sorted(unbekannt)}")
        for feld in PFLICHT:
            if not str(reihe.get(feld, "")).strip():
                raise ReihenFehler(f"{pfad.name}, Reihe {nr}: {feld} fehlt")
        for feld in LISTEN:
            if feld in reihe and not (isinstance(reihe[feld], list) and all(isinstance(x, str) for x in reihe[feld])):
                raise ReihenFehler(f"{pfad.name}, Reihe {nr}: {feld} muss eine Liste von Texten sein")
    return reihen


def prompt_reihen(reihen: list[dict], fach: str) -> str:
    """Abschnitt für den Prompt, leer ohne Reihen."""
    if not reihen:
        return ""
    bloecke = []
    for r in reihen:
        kopf = f"### {r.get('fach') or fach}, Klasse {r['klasse']}" + (f": {r['titel']}" if r.get("titel") else "")
        zeilen = [kopf, f"- Reihenfrage: {r['reihenfrage']}"]
        if r.get("lerngruppe"):
            zeilen.append(f"- Lerngruppe: {r['lerngruppe']}")
        if r.get("behandelt"):
            zeilen.append("- Schon behandelt: " + "; ".join(r["behandelt"]))
        if r.get("merksaetze"):
            zeilen.append("- Merksätze der Reihe:\n" + "\n".join(f"  - {m}" for m in r["merksaetze"]))
        if r.get("notizen"):
            zeilen.append(f"- Notizen: {r['notizen']}")
        bloecke.append("\n".join(zeilen))
    return ("## Lias laufende Reihen\n"
            "Nimm die Reihe, die zu Klasse und Thema des Wunsches passt. Halte dich an ihre Reihenfrage und ihre "
            "Lerngruppe und baue auf dem auf, was schon behandelt ist; Merksätze der Reihe übernimmst du im "
            "Wortlaut. Passt keine Reihe oder mehrere, nenne deine Annahme im Begleittext.\n\n"
            + "\n\n".join(bloecke) + "\n\n")
