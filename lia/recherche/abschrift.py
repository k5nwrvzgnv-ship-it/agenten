"""Abschriften vom Seitenbild prüfen (ohne Netz). Für Quellen ohne brauchbare OCR (Liszt, Fraktur).

Ablauf (Jan, 25.10.2026): Claude schreibt jede Stelle zweimal unabhängig vom Bild ab. Python prüft:
a) vergleichen(): Die Abschriften müssen nach agentkit.wortlaut.normalisieren gleich sein. Sind sie es
   nicht, entscheidet eine dritte (zwei von drei gleich), sonst wird die Stelle verworfen.
b) aehnlichkeit(): Die Abschrift muss unscharf zur OCR der Seite passen. Beide Seiten werden vorher
   angeglichen (angleichen): nur Buchstaben und Ziffern, klein, typische Fraktur-Verwechslungen der OCR auf
   eine Form gebracht. Dann sucht difflib das ähnlichste gleich lange Fenster in der OCR.
   Schwelle: SCHWELLE, bestimmt an bekannten Seiten (STATUS.md).
Unleserliches markiert Claude mit [?]; solche Stellen werden verworfen.
"""

import re
from difflib import SequenceMatcher

from agentkit import wortlaut

SCHWELLE = 0.75  # Bestimmung: STATUS.md, Abschnitt Entscheidungen
MIN_ZEICHEN = 50  # kürzere Stellen kommen zu nah an falsche Seiten heran (Kalibrierung)
UNLESERLICH = "[?]"

# Folgen zuerst (OCR liest Fraktur-ch als "dj", "d)", "(^" usw.), dann einzelne Zeichen.
_FOLGEN = [("d)", "ch"), ("dj", "ch"), ("(^", "ch"), ("cf)", "ch"), ("rn", "m"), ("ii", "u")]
_ZEICHEN = str.maketrans({
    "b": "d", "ſ": "s", "f": "s", "k": "s", "©": "s", "$": "s", "§": "z", "3": "z",
    "ä": "a", "ö": "o", "ü": "n", "u": "n", "c": "e", "ß": "s", "j": "i", "l": "i", "t": "i", "y": "i",
})
_NICHT_BUCHSTABE = re.compile(r"[^a-z0-9]")


def angleichen(text: str) -> str:
    """Vergleichsform für Fraktur-OCR. Grob mit Absicht: Sie ist nur für das unscharfe Suchen da."""
    text = text.replace("-\n", "").replace("=\n", "").replace("ſ", "s").lower()
    for alt, neu in _FOLGEN:
        text = text.replace(alt, neu)
    return _NICHT_BUCHSTABE.sub("", text.translate(_ZEICHEN))


def aehnlichkeit(abschrift: str, ocr: str) -> float:
    """Ähnlichkeit 0..1 des besten Fensters in der OCR (gleich lang wie die Abschrift)."""
    a, o = angleichen(abschrift), angleichen(ocr)
    if not a or not o:
        return 0.0
    if len(o) <= len(a):
        return round(SequenceMatcher(None, a, o, autojunk=False).ratio(), 3)
    schritt = max(1, len(a) // 10)
    beste, beste_pos = 0.0, 0
    for pos in range(0, len(o) - len(a) + schritt, schritt):
        r = SequenceMatcher(None, a, o[pos:pos + len(a)], autojunk=False).ratio()
        if r > beste:
            beste, beste_pos = r, pos
    for pos in range(max(0, beste_pos - schritt), min(len(o) - len(a), beste_pos + schritt) + 1):
        beste = max(beste, SequenceMatcher(None, a, o[pos:pos + len(a)], autojunk=False).ratio())
    return round(beste, 3)


def unterschiede(a: str, b: str) -> list[str]:
    """Abweichende Wörter zweier Abschriften, für die Meldung an Jan."""
    wa, wb = a.split(), b.split()
    aus = []
    for op, i1, i2, j1, j2 in SequenceMatcher(None, wa, wb, autojunk=False).get_opcodes():
        if op != "equal":
            aus.append(f"{' '.join(wa[i1:i2]) or '–'} / {' '.join(wb[j1:j2]) or '–'}")
    return aus


def vergleichen(fassungen: list[str]) -> tuple[str | None, list[str]]:
    """(gültige Fassung oder None, Unterschiede). Gültig: die ersten beiden gleich, sonst zwei von drei."""
    if any(UNLESERLICH in f for f in fassungen):
        return None, ["Abschrift enthält [?] (unleserlich)"]
    formen = [wortlaut.normalisieren(f) for f in fassungen]
    if len(formen) >= 2 and formen[0] == formen[1] and formen[0]:
        return fassungen[0], []
    if len(formen) >= 3:
        for i, j in ((0, 2), (1, 2)):
            if formen[i] == formen[j] and formen[i]:
                return fassungen[i], unterschiede(fassungen[0], fassungen[1])
    return None, unterschiede(fassungen[0], fassungen[1]) if len(fassungen) >= 2 else ["nur eine Abschrift"]
