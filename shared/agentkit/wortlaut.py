"""Wörtliche Prüfung von Zitaten gegen einen Quelltext.

Grundsatz (Plan Examensreihe, Jan 25.10.2026): Was als Zitat oder Wortlaut gilt, prüft Python, nicht Claude.
Verglichen wird ohne Leerraum und ohne Silbentrennung am Zeilenende, weil Textfassungen aus PDFs Zeilen
umbrechen und Wörter trennen („verschie-\\ndenen“). Typografische Anführungszeichen und Striche zählen gleich.
Sonst muss jedes Zeichen stimmen.
"""

import re

_ZEICHEN = str.maketrans({
    "­": "",  # weiches Trennzeichen (im RLP als Aufzählungszeichen)
    "„": '"', "“": '"', "”": '"', "»": '"', "«": '"',
    "‚": "'", "‘": "'", "’": "'",
    "–": "-", "—": "-",
})
_TRENNUNG = re.compile(r"-[ \t]*\n\s*")
_LEERRAUM = re.compile(r"\s+")
_SEITE = re.compile(r"^--- Seite (\d+)\s*$", re.MULTILINE)


def normalisieren(text: str) -> str:
    """Vergleichsform: Silbentrennung am Zeilenende weg, Zeichen vereinheitlicht, kein Leerraum."""
    text = _TRENNUNG.sub("", text.translate(_ZEICHEN))
    return _LEERRAUM.sub("", text)


def steht_in(zitat: str, quelltext: str) -> bool:
    """True, wenn das Zitat wörtlich (in Vergleichsform) im Quelltext steht. Leere Zitate nie."""
    kurz = normalisieren(zitat)
    return bool(kurz) and kurz in normalisieren(quelltext)


def seiten(textfassung: str) -> dict[int, str]:
    """Teilt eine Textfassung mit „--- Seite N“ (agentkit.textfassung) in Seiten auf."""
    teile = _SEITE.split(textfassung)
    return {int(teile[i]): teile[i + 1] for i in range(1, len(teile) - 1, 2)}
