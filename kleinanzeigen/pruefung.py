"""Ein Prüfdurchgang für eine Suche, ohne Netz: Anzeigen rein, Telegram-Texte raus.

Abruf und Claude-Lauf kommen als Werte bzw. Funktion von außen (bot.py), damit das hier testbar bleibt.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

import bewertung
import vorfilter
from db import Speicher
from seite import Anzeige
from texte import treffer_text

log = logging.getLogger(__name__)

MAX_KANDIDATEN = 25  # mehr gehen nicht in einen Lauf, der Rest gilt als gesehen


@dataclass
class Ergebnis:
    meldungen: list[str] = field(default_factory=list)
    kandidaten: int = 0
    claude: bool = False  # ein Claude-Lauf wurde gestartet
    notfall: bool = False  # ohne Claude gemeldet (Tagesgrenze)


def zusammenfuehren(listen: list[list[Anzeige]]) -> list[Anzeige]:
    """Anzeigen mehrerer Suchbegriffe ohne Doppelte, Reihenfolge bleibt."""
    gesehen, raus = set(), []
    for liste in listen:
        for a in liste:
            if a.id not in gesehen:
                gesehen.add(a.id)
                raus.append(a)
    return raus


def suche_pruefen(sp: Speicher, suche: dict, anzeigen: list[Anzeige], claude: Callable[[str], str],
                  claude_frei: bool, schwelle: int = bewertung.MELDE_SCHWELLE) -> Ergebnis:
    """Neue Kandidaten bestimmen, bewerten (oder ohne Claude nur klare Schnäppchen) und Meldungen bauen.

    claude(prompt) -> Antworttext; wirft bei Fehlern. Dann bleiben die Kandidaten ungesehen und werden
    beim nächsten Takt erneut versucht. claude_frei=False: Tagesgrenze erreicht, kein Lauf.
    """
    erg = Ergebnis()
    gesehen = sp.gesehen_ids(suche["id"])
    kandidaten = vorfilter.vorfiltern(anzeigen, gesehen, suche["max_preis"], suche["ausschluss"])
    kandidaten_ids = {a.id for a in kandidaten}
    uebrig = [a for a in anzeigen if a.id not in gesehen and a.id not in kandidaten_ids]
    sp.gesehen_merken(suche["id"], [(a.id, a.preis) for a in uebrig])
    zu_viele, kandidaten = kandidaten[MAX_KANDIDATEN:], kandidaten[:MAX_KANDIDATEN]
    sp.gesehen_merken(suche["id"], [(a.id, a.preis) for a in zu_viele])
    erg.kandidaten = len(kandidaten)
    if not kandidaten:
        return erg

    markt = vorfilter.marktpreis(sp.preise(suche["id"]))
    if not claude_frei:
        referenz = suche.get("marktwert") or markt
        for a in vorfilter.notfall_schnaeppchen(kandidaten, referenz):
            erg.meldungen.append(treffer_text(a, None, suche["titel"], referenz))
        erg.notfall = bool(erg.meldungen)
        sp.gesehen_merken(suche["id"], [(a.id, a.preis) for a in kandidaten])
        return erg

    erg.claude = True
    antwort = claude(bewertung.bewertungs_prompt(suche, kandidaten, markt))
    bewertungen = bewertung.bewertung_pruefen(antwort, {a.id for a in kandidaten})
    sp.gesehen_merken(suche["id"], [(a.id, a.preis) for a in kandidaten])
    fehlend = len(kandidaten) - len(bewertungen)
    if fehlend:
        log.warning("Suche %s: %d von %d Anzeigen ohne Bewertung", suche["id"], fehlend, len(kandidaten))
    for a, b in bewertung.treffer_auswaehlen(kandidaten, bewertungen, schwelle):
        erg.meldungen.append(treffer_text(a, b, suche["titel"], markt))
    return erg
