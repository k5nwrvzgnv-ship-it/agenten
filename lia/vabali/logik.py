"""Reine Logik des Agenten vabali (ohne Netz): passende Massagen und Zeiten, neue Termine, Meldungstext.

Ein Termin ist ein Tupel (datum "JJJJ-MM-TT", zeit "HH:MM", name der Massage).
"""

from datetime import date

WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def passende_artikel(artikel: list[dict], dauer: int, partner: bool) -> list[dict]:
    """Buchbare Massagen mit der gesuchten Dauer, ohne Partnermassagen (außer partner=True)."""
    return [a for a in artikel
            if a.get("buchbar") and a.get("Dauer") == dauer and bool(a.get("Doppelanwendung")) == partner]


def passende_zeiten(moegliche: dict, beginn_bis: str) -> list[str]:
    """Startzeiten "HH:MM" bis einschließlich beginn_bis, an denen jemand frei ist, aufsteigend.

    moegliche: Feld possibleAnwendungen der Schnittstelle, {"10:30:00": [Personal-IDs], ...}.
    """
    zeiten = {z[:5] for z, personal in moegliche.items() if personal}
    return sorted(z for z in zeiten if z <= beginn_bis)


def offene_tage(tage: list[str], heute: date) -> list[str]:
    """Gesuchte Tage ab heute (vergangene fallen weg)."""
    return [t for t in tage if date.fromisoformat(t) >= heute]


def neue_termine(alt: set[tuple], aktuell: set[tuple]) -> list[tuple]:
    """Termine, die beim letzten Lauf nicht frei waren, sortiert nach Tag und Zeit."""
    return sorted(aktuell - alt)


def tag_text(datum: str) -> str:
    d = date.fromisoformat(datum)
    return f"{WOCHENTAGE[d.weekday()]} {d.day:02d}.{d.month:02d}."


def meldungstext(termine: list[tuple], link: str) -> str:
    """Nachricht an Lia über neu frei gewordene Termine, je Tag und Uhrzeit eine Zeile.

    Ein freier Platz gilt meist für mehrere Massagen zugleich (dieselbe Masseurin), daher zusammengefasst.
    """
    massagen: dict[tuple, list[str]] = {}
    for d, z, n in sorted(termine):
        massagen.setdefault((d, z), []).append(n)
    zeilen = [f"- {tag_text(d)} {z} Uhr: {', '.join(namen)}" for (d, z), namen in massagen.items()]
    kopf = "Im vabali Berlin ist ein Massagetermin frei geworden:" if len(zeilen) == 1 else \
        "Im vabali Berlin sind Massagetermine frei geworden:"
    return "\n".join([kopf, *zeilen, "", f"Buchen: {link}", "Am besten schnell, freie Termine sind oft bald wieder weg."])
