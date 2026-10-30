"""Reihenkontext: Lias laufende Unterrichtsreihen (reihen.toml) für jeden Lauf.

Grund (lia/auswertung, 23.10.2026): Viele Korrekturen in Lias Chats entstanden, weil Claude Reihenfrage, Klasse
oder schon behandelte Positionen nicht kannte. reihen.toml pflegt Jan von Hand; laden prüft sie, prompt_reihen
macht daraus einen Prompt-Abschnitt.

Seit 30.10.2026 liegt die Datei in der Instanz (lia/instanz/reihen.toml), EINE Datei für Web-App und Agenten
(Format auch im Kopf von shared/webapp/ordnung.py). Dazu freiwillig: id (feste Kennung, steht in Aufträgen im Feld
reihe), stand (laufend oder abgeschlossen), schuljahr (z. B. "2025/26"), agenten (Liste, z. B. ["theater"]).
Abgeschlossene Reihen stehen im Prompt nur als kurze Liste.
"""

import re
import tomllib
from pathlib import Path

PFLICHT = ("fach", "klasse")  # Reihenfrage fehlt, solange eine Reihe noch geplant wird; fach wie die Web-App
TEXTE = ("id", "fach", "klasse", "titel", "reihenfrage", "lerngruppe", "notizen", "stand", "schuljahr")
LISTEN = ("behandelt", "merksaetze", "bisherige_reihen", "agenten")
STAENDE = ("laufend", "abgeschlossen")
ID_MUSTER = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")  # wie agentkit.auftraege (Feld reihe)


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
    ids = set()
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
        if reihe.get("stand", "laufend") not in STAENDE:
            raise ReihenFehler(f"{pfad.name}, Reihe {nr}: stand {reihe['stand']!r}, erlaubt {list(STAENDE)}")
        if "id" in reihe:
            if not ID_MUSTER.fullmatch(str(reihe["id"])):
                raise ReihenFehler(f"{pfad.name}, Reihe {nr}: id nur aus Kleinbuchstaben, Ziffern und Bindestrichen")
            if reihe["id"] in ids:
                raise ReihenFehler(f"{pfad.name}, Reihe {nr}: id {reihe['id']!r} gibt es doppelt")
            ids.add(reihe["id"])
    return reihen


def laufend(reihe: dict) -> bool:
    return reihe.get("stand", "laufend") == "laufend"


def ort(reihe: dict, fach: str) -> str:
    """z. B. „Ethik, Klasse 8“ oder „Darstellendes Spiel, Kurs 12“."""
    klasse = str(reihe["klasse"])
    return f"{reihe.get('fach') or fach}, " + (f"Klasse {klasse}" if klasse[:1].isdigit() else klasse)


def prompt_reihen(reihen: list[dict], fach: str) -> str:
    """Abschnitt für den Prompt, leer ohne Reihen."""
    if not reihen:
        return ""
    bloecke = []
    for r in filter(laufend, reihen):
        kopf = f"### {ort(r, fach)}" + (f": {r['titel']}" if r.get("titel") else "")
        zeilen = [kopf]
        if r.get("reihenfrage"):
            zeilen.append(f"- Reihenfrage: {r['reihenfrage']}")
        if r.get("lerngruppe"):
            zeilen.append(f"- Lerngruppe: {r['lerngruppe']}")
        if r.get("bisherige_reihen"):
            zeilen.append("- Frühere Reihen der Klasse:\n" + "\n".join(f"  - {x}" for x in r["bisherige_reihen"]))
        if r.get("behandelt"):
            zeilen.append("- Schon behandelt: " + "; ".join(r["behandelt"]))
        if r.get("merksaetze"):
            zeilen.append("- Merksätze der Reihe:\n" + "\n".join(f"  - {m}" for m in r["merksaetze"]))
        if r.get("notizen"):
            zeilen.append(f"- Notizen: {r['notizen']}")
        bloecke.append("\n".join(zeilen))
    fertig = [r for r in reihen if not laufend(r)]
    if fertig:
        bloecke.append("### Abgeschlossene Reihen (nur zur Orientierung, was die Klassen schon kennen)\n" + "\n".join(
            f"- {ort(r, fach)}" + (f" ({r['schuljahr']})" if r.get("schuljahr") else "")
            + (f": {r['titel']}" if r.get("titel") else "") + (f" – {r['reihenfrage']}" if r.get("reihenfrage") else "")
            for r in fertig))
    return ("## Lias laufende Reihen\n"
            "Nimm die Reihe, die zu Klasse und Thema des Wunsches passt. Halte dich an ihre Reihenfrage und ihre "
            "Lerngruppe und baue auf dem auf, was schon behandelt ist; Merksätze der Reihe übernimmst du im "
            "Wortlaut. Frühere Reihen zeigen, was die Klasse schon kennt. Passt keine Reihe oder mehrere, nenne "
            "deine Annahme im Begleittext.\n\n"
            + "\n\n".join(bloecke) + "\n\n")
