"""Agent vabali in Lias Instanz (AGENTKIT_INSTANZ=lia/instanz), Einstieg des Dienstes lia-vabali.

Prüft zeitgesteuert (Timer lia-vabali, alle 15 Minuten von 7 bis 23 Uhr), ob im vabali spa Berlin eine Massage
nach suche.toml frei ist, und meldet neu frei gewordene Termine über Lias Zentrale an Lia. Buchen tut Lia selbst.
Ohne Claude. Fehler der Abfrage bekommt Jan einmal als Meldung, bis eine Abfrage wieder klappt.
Aufruf: AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python agent.py
"""

import json
import tomllib
from datetime import date
from pathlib import Path

import logik
from abfrage import Abfrage, AbfrageFehler
from agentkit import config, log, meldungen

AGENT = "vabali"
HIER = Path(__file__).resolve().parent
STAND = HIER / "data" / "stand.json"
logger = log.hole_logger(HIER, AGENT)


def lia_melden(text: str) -> None:
    meldungen.melden(AGENT, text)  # Lias Instanz, also Lias Zentrale


def jan_melden(text: str) -> None:
    """Meldung in Jans Instanz (seine Zentrale), nicht in Lias."""
    meldungen.melden(AGENT, f"Lia, Agent vabali: {text}", basis=config.KONTINGENT_DIR / "meldungen")


def stand_lesen(pfad: Path) -> dict:
    if not pfad.exists():
        return {"frei": [], "fehler_gemeldet": False}
    return json.loads(pfad.read_text(encoding="utf-8"))


def stand_schreiben(pfad: Path, stand: dict) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix(".tmp")
    tmp.write_text(json.dumps(stand, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(pfad)


def freie_termine(abfrage, tage: list[str], suche: dict) -> set[tuple]:
    frei = set()
    for datum in tage:
        for a in logik.passende_artikel(abfrage.artikel(datum), suche["dauer_minuten"], suche["partner"]):
            for zeit in logik.passende_zeiten(abfrage.zeiten(datum, a["Artikel_ID"]), suche["beginn_bis"]):
                frei.add((datum, zeit, a["Name"]))
    return frei


def lauf(suche: dict, heute: date, abfrage, stand_pfad: Path = STAND, lia=lia_melden, jan=jan_melden) -> None:
    tage = logik.offene_tage(suche["tage"], heute)
    if not tage:
        logger.info("Zeitraum vorbei, nichts zu tun (Timer lia-vabali kann aus)")
        return
    stand = stand_lesen(stand_pfad)
    try:
        aktuell = freie_termine(abfrage, tage, suche)
    except AbfrageFehler as f:
        logger.error("Abfrage gescheitert: %s", f)
        if not stand.get("fehler_gemeldet"):
            jan(f"Abfrage bei vabali gescheitert, Lia bekommt bis zur Behebung keine Termine: {f}")
            stand["fehler_gemeldet"] = True
            stand_schreiben(stand_pfad, stand)
        return
    neu = logik.neue_termine({tuple(t) for t in stand.get("frei", [])}, aktuell)
    logger.info("%d passende Termine frei, davon %d neu", len(aktuell), len(neu))
    if neu:
        lia(logik.meldungstext(neu, suche["link"]))
        logger.info("Lia gemeldet: %s", neu)
    if stand.get("fehler_gemeldet"):
        jan("Abfrage bei vabali klappt wieder.")
    stand_schreiben(stand_pfad, {"frei": sorted(aktuell), "fehler_gemeldet": False})


def main() -> None:
    suche = tomllib.loads((HIER / "suche.toml").read_text(encoding="utf-8"))
    lauf(suche, date.today(), Abfrage())


if __name__ == "__main__":
    main()
