"""Vorfilter ohne Claude: nur neue, passende Anzeigen gehen an die Bewertung.

Dazu der Marktpreis einer Suche (Median aller gesehenen Preise), damit Claude und die Notmeldung
ohne Claude ein Schnäppchen erkennen.
"""

import re
from statistics import median

from seite import Anzeige

# Gesuche und Tausch sind keine Angebote
_GESUCH = re.compile(r"^\W*(suche|gesucht|tausche|ankauf|kaufe)\b", re.I)
MARKT_MIN = 8  # weniger Vergleichspreise: kein Marktpreis


def _woerter(text: str) -> str:
    return " " + re.sub(r"\W+", " ", text.lower()) + " "


def ausgeschlossen(anzeige: Anzeige, ausschluss: list[str]) -> bool:
    """True, wenn ein Ausschlusswort als ganzes Wort im Titel oder in der Beschreibung steht."""
    text = _woerter(f"{anzeige.titel} {anzeige.beschreibung}")
    return any(_woerter(w).strip() and _woerter(w) in text for w in ausschluss)


def vorfiltern(anzeigen: list[Anzeige], gesehen: set[int], max_preis: float | None,
               ausschluss: list[str]) -> list[Anzeige]:
    """Neue Kandidaten: nicht gesehen, kein Gesuch, im Preis (ohne Preis bleibt drin), kein Ausschlusswort.
    Alte Top-Anzeigen (nicht von heute/gestern) fallen raus, die sind kein frisches Angebot."""
    raus = []
    for a in anzeigen:
        if a.id in gesehen:
            continue
        if a.top and not a.neu:
            continue
        if _GESUCH.search(a.titel):
            continue
        if max_preis is not None and a.preis is not None and a.preis > max_preis:
            continue
        if ausschluss and ausgeschlossen(a, ausschluss):
            continue
        raus.append(a)
    return raus


def marktpreis(preise: list[float]) -> float | None:
    """Median der gesehenen Preise (ohne 0 € und ohne fehlende), erst ab MARKT_MIN Werten."""
    werte = [p for p in preise if p and p > 0]
    if len(werte) < MARKT_MIN:
        return None
    return float(median(werte))


def notfall_schnaeppchen(kandidaten: list[Anzeige], markt: float | None, anteil: float = 0.6) -> list[Anzeige]:
    """Ohne Claude (Tagesgrenze erreicht): nur Anzeigen klar unter Marktpreis, sonst nichts."""
    if not markt:
        return []
    return [a for a in kandidaten if a.preis is not None and 0 < a.preis <= markt * anteil]
