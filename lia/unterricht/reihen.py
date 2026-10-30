"""Reihenkontext: Lias laufende Unterrichtsreihen (reihen.toml) für jeden Lauf.

Grund (lia/auswertung, 23.10.2026): Viele Korrekturen in Lias Chats entstanden, weil Claude Reihenfrage, Klasse
oder schon behandelte Positionen nicht kannte. reihen.toml pflegt Jan von Hand; laden prüft sie, prompt_reihen
macht daraus einen Prompt-Abschnitt.

Seit 30.10.2026 liegt die Datei in der Instanz (lia/instanz/reihen.toml), EINE Datei für Web-App und Agenten
(Format auch im Kopf von shared/webapp/ordnung.py). Dazu freiwillig: id (feste Kennung, steht in Aufträgen im Feld
reihe), stand (laufend oder abgeschlossen), schuljahr (z. B. "2025/26"), agenten (Liste, z. B. ["theater"]).
Abgeschlossene Reihen stehen im Prompt nur als kurze Liste.

Stunden (board-plan.md 3): je Reihe [[reihe.stunde]] mit nr (ganze Zahl ab 1), thema und optional marke ("UB" oder
"Prüfung"). Sie gehen mit ins Prompt. Hat der Auftrag das Feld reihe (Web-App), steht diese Reihe zuerst und als
gewählt; die Stunde selbst steht als Zeile „Stunde n: Thema“ (bzw. „Probe n“) im Auftragstext.
"""

import re
import tomllib
from pathlib import Path

PFLICHT = ("fach", "klasse")  # Reihenfrage fehlt, solange eine Reihe noch geplant wird; fach wie die Web-App
TEXTE = ("id", "fach", "klasse", "titel", "reihenfrage", "lerngruppe", "notizen", "stand", "schuljahr")
LISTEN = ("behandelt", "merksaetze", "bisherige_reihen", "agenten")
STAENDE = ("laufend", "abgeschlossen")
MARKEN = ("UB", "Prüfung")
STUNDE_FELDER = ("nr", "thema", "marke")
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
        unbekannt = set(reihe) - set(TEXTE) - set(LISTEN) - {"stunde"}
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
        _stunden_pruefen(reihe.pop("stunde", []), reihe, f"{pfad.name}, Reihe {nr}")
    return reihen


def _stunden_pruefen(stunden, reihe: dict, wo: str) -> None:
    """Prüft [[reihe.stunde]] und legt sie unter "stunden" (nach nr sortiert) ab."""
    if not isinstance(stunden, list) or not all(isinstance(s, dict) for s in stunden):
        raise ReihenFehler(f"{wo}: Stunden als [[reihe.stunde]] schreiben")
    nummern = set()
    for s in stunden:
        if set(s) - set(STUNDE_FELDER):
            raise ReihenFehler(f"{wo}: Stunde mit unbekannten Feldern {sorted(set(s) - set(STUNDE_FELDER))}")
        if not isinstance(s.get("nr"), int) or isinstance(s["nr"], bool) or s["nr"] < 1:
            raise ReihenFehler(f"{wo}: Stunde braucht nr als ganze Zahl ab 1")
        if s["nr"] in nummern:
            raise ReihenFehler(f"{wo}: Stunde {s['nr']} gibt es doppelt")
        nummern.add(s["nr"])
        if not isinstance(s.get("thema"), str) or not s["thema"].strip():
            raise ReihenFehler(f"{wo}, Stunde {s['nr']}: thema fehlt")
        if "marke" in s and s["marke"] not in MARKEN:
            raise ReihenFehler(f"{wo}, Stunde {s['nr']}: marke {s['marke']!r}, erlaubt {list(MARKEN)}")
    if stunden:
        reihe["stunden"] = sorted(stunden, key=lambda s: s["nr"])


def laufend(reihe: dict) -> bool:
    return reihe.get("stand", "laufend") == "laufend"


def ort(reihe: dict, fach: str) -> str:
    """z. B. „Ethik, Klasse 8“ oder „Darstellendes Spiel, Kurs 12“."""
    klasse = str(reihe["klasse"])
    return f"{reihe.get('fach') or fach}, " + (f"Klasse {klasse}" if klasse[:1].isdigit() else klasse)


def stunden_wort(reihe: dict) -> str:
    """„Probe“ für eine Inszenierung (Reihe des Theater-Agenten), sonst „Stunde“ (wie die Web-App)."""
    return "Probe" if "theater" in reihe.get("agenten", []) else "Stunde"


def prompt_reihen(reihen: list[dict], fach: str, gewaehlt: str | None = None) -> str:
    """Abschnitt für den Prompt, leer ohne Reihen. gewaehlt: id der Reihe aus dem Auftrag (Feld reihe)."""
    if not reihen:
        return ""
    bloecke = []
    wahl = next((r for r in reihen if gewaehlt and r.get("id") == gewaehlt), None)
    for r in ([wahl] if wahl else []) + [r for r in reihen if laufend(r) and r is not wahl]:
        kopf = f"### {ort(r, fach)}" + (f": {r['titel']}" if r.get("titel") else "")
        if r is wahl:
            kopf += " (Lia hat den Auftrag dieser Reihe zugeordnet)"
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
        if r.get("stunden"):
            wort = stunden_wort(r)
            zeilen.append(f"- {wort}n der Reihe:\n" + "\n".join(
                f"  - {wort} {s['nr']}: {s['thema']}" + (f" ({s['marke']})" if s.get("marke") else "")
                for s in r["stunden"]))
        bloecke.append("\n".join(zeilen))
    fertig = [r for r in reihen if not laufend(r) and r is not wahl]
    if fertig:
        bloecke.append("### Abgeschlossene Reihen (nur zur Orientierung, was die Klassen schon kennen)\n" + "\n".join(
            f"- {ort(r, fach)}" + (f" ({r['schuljahr']})" if r.get("schuljahr") else "")
            + (f": {r['titel']}" if r.get("titel") else "") + (f" – {r['reihenfrage']}" if r.get("reihenfrage") else "")
            for r in fertig))
    return ("## Lias laufende Reihen\n"
            "Nimm die Reihe, die zu Klasse und Thema des Wunsches passt. Halte dich an ihre Reihenfrage und ihre "
            "Lerngruppe und baue auf dem auf, was schon behandelt ist; Merksätze der Reihe übernimmst du im "
            "Wortlaut. Frühere Reihen zeigen, was die Klasse schon kennt. Hat Lia den Auftrag einer Reihe zugeordnet, "
            "nimm diese. Nennt ihr Wunsch eine Stunde (z. B. „Stunde 3: …“), passt das Material genau zu dieser "
            "Stunde: Es baut auf den Stunden davor auf und bereitet die danach vor; bei UB oder Prüfung besonders "
            "sorgfältig. Passt keine Reihe oder mehrere, nenne deine Annahme im Begleittext.\n\n"
            + "\n\n".join(bloecke) + "\n\n")
