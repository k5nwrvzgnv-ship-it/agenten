"""Auszug aus Lias Fachbuch als Kontext für Claude (ohne Claude, ohne Netz).

Lias Buch „Praxis Schultheater“ (Kündiger) liegt als Scan mit Texterkennung vor, 384 Seiten. Ganz wäre es etwa
dreimal so lang wie das Stück, deshalb nimmt der Agent nur die Kapitel aus theater.toml [buch] (Jan 29.10.2026).
Seitenangaben im Auszug sind die gedruckten Seiten (PDF-Seite = gedruckte Seite + versatz). Zeilen, die die
Texterkennung aus Abbildungen gemacht hat (Zeichensalat), fallen weg.
"""

import re

_SEITE = re.compile(r"^--- Seite (\d+)$")
MIN_BUCHSTABEN_ANTEIL = 0.6  # darunter ist eine Zeile Zeichensalat (z. B. „l>ii§i!§li!.I.j“)


class BuchFehler(Exception):
    pass


def lesbar(zeile: str) -> bool:
    """Zeile mit genug Buchstaben, Ziffern und Leerzeichen; einzelne Zeichen und Symbole fallen weg."""
    zeile = zeile.strip()
    if len(zeile) < 3:
        return False
    gut = sum(z.isalnum() or z.isspace() for z in zeile)
    return gut / len(zeile) >= MIN_BUCHSTABEN_ANTEIL and sum(z.isalpha() for z in zeile) >= 2


def seiten(text: str) -> dict[int, list[str]]:
    """PDF-Seite -> Zeilen."""
    ergebnis, seite = {}, None
    for zeile in text.splitlines():
        m = _SEITE.match(zeile.strip())
        if m:
            seite = int(m.group(1))
            ergebnis[seite] = []
        elif seite is not None:
            ergebnis[seite].append(zeile)
    return ergebnis


def auszug(text: str, bereiche: list[list[int]], versatz: int, titel: str, max_zeichen: int = 40000) -> list[str]:
    """Kapitel als Teile (für Read, je höchstens max_zeichen, getrennt an Seitengrenzen) mit „--- Buch S. n“
    (gedruckte Seite). bereiche: [[von, bis], ...] in gedruckten Seiten."""
    nach_seite = seiten(text)
    kopf = (f"# Auszug: {titel}\nGedruckte Seitenzahlen. Texterkennung eines Scans: Leerzeichen innerhalb von "
            "Wörtern sind Fehler der Erkennung, Abbildungen fehlen.")
    teile, aktuell = [], kopf
    for von, bis in bereiche:
        if von > bis:
            raise BuchFehler(f"Bereich {von}–{bis}: von größer als bis")
        for gedruckt in range(von, bis + 1):
            zeilen = nach_seite.get(gedruckt + versatz)
            if zeilen is None:
                raise BuchFehler(f"Seite {gedruckt} (PDF {gedruckt + versatz}) fehlt in der Textfassung")
            seite = "\n".join([f"--- Buch S. {gedruckt}"] + [" ".join(z.split()) for z in zeilen if lesbar(z)])
            if len(aktuell) + len(seite) + 1 > max_zeichen and aktuell != kopf:
                teile.append(aktuell + "\n")
                aktuell = f"# Auszug (Fortsetzung): {titel}"
            aktuell += "\n" + seite
    teile.append(aktuell + "\n")
    return teile
