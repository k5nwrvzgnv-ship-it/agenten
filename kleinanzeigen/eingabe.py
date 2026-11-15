"""Eingaben der Nutzer lesen (ohne Netz): Preisgrenze, Umkreis, PLZ und Freischaltung."""

import re
from dataclasses import dataclass


@dataclass
class Details:
    max_preis: float | None = None
    umkreis_km: int | None = None
    plz: str | None = None


def details_lesen(text: str) -> Details:
    """'max 80 €, 30 km um 34128' -> Details(80, 30, '34128'). Fehlende Teile bleiben None.

    PLZ: genau fünf Ziffern. Umkreis: Zahl vor km. Preis: Zahl mit €/Euro, sonst die übrige Zahl.
    """
    t = text.replace(" ", " ")
    d = Details()
    plz = re.search(r"(?<!\d)(\d{5})(?!\d)", t)
    if plz:
        d.plz = plz.group(1)
        t = t[:plz.start()] + " " + t[plz.end():]
    km = re.search(r"(\d{1,3})\s*km\b", t, re.I)
    if km:
        d.umkreis_km = int(km.group(1))
        t = t[:km.start()] + " " + t[km.end():]
    preis = re.search(r"(\d+(?:[.,]\d{1,2})?)\s*(?:€|euro\b|eur\b)", t, re.I) \
        or re.search(r"(\d+(?:[.,]\d{1,2})?)", t)
    if preis:
        d.max_preis = float(preis.group(1).replace(",", "."))
    return d


def umkreis_runden(km: int) -> int:
    """Kleinanzeigen kennt nur feste Umkreise, auf den nächsthöheren runden (max 200)."""
    for stufe in (5, 10, 20, 30, 50, 100, 150, 200):
        if km <= stufe:
            return stufe
    return 200


def chat_ids_lesen(wert: str) -> set[int]:
    """ERLAUBTE_CHAT_IDS aus .env: '123, -456 789' -> {123, -456, 789}. Ungültiges wird ignoriert."""
    ids = set()
    for teil in re.split(r"[,\s;]+", wert or ""):
        try:
            ids.add(int(teil))
        except ValueError:
            continue
    return ids


def preis_text(preis: float | None) -> str:
    if preis is None:
        return "egal"
    return f"{preis:g} €"


def details_text(max_preis: float | None, umkreis_km: int | None, plz: str | None) -> str:
    ort = f"{umkreis_km} km um {plz}" if plz and umkreis_km else (f"um {plz}" if plz else "ganz Deutschland")
    return f"max. {preis_text(max_preis)}, {ort}"
