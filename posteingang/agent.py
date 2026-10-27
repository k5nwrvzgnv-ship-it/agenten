"""Agent posteingang: Jans privates Postfach jan@kleinke.org lesen und Wichtiges melden (Stufe 1).

Ein Lauf (gestartet vom Timer):
1. neue Mails holen (agentkit.imap, nur lesend) und sofort in data/mails_offen.json speichern,
   damit sie bei einem Ausfall nicht verloren gehen,
2. vorfiltern ohne Claude (vorfilter.py: Spam, Newsletter, Massenmail, gesperrte Absender aus den Regeln),
3. den Rest von Claude einordnen lassen (einordnung.py, art routine). Antwort KEINE = nichts melden,
4. Meldung an Jan mit [post], danach data/mails_offen.json löschen.

Kann Claude gerade nicht (Limit, Pause, Platz), bleiben die Mails offen und kommen im nächsten Lauf dran.
Senden gibt es in Stufe 1 nicht.
"""

import json
from datetime import date
from pathlib import Path

from agentkit import claude_lauf, config, imap, log, meldungen, regeln

import einordnung
import vorfilter

AGENT = "posteingang"
HIER = Path(__file__).resolve().parent
DATA = HIER / "data"
STAND_DATEI = DATA / "postfach.json"
MAILS_OFFEN = DATA / "mails_offen.json"
FEHLER_DATEI = DATA / "schritt_fehler.json"
PFLICHT = ("IMAP_HOST", "IMAP_NUTZER", "IMAP_KENNWORT")

logger = log.hole_logger(HIER, AGENT)

WARTEN = (claude_lauf.LimitErreicht, claude_lauf.KeinPlatz, claude_lauf.LaeuftSchon, claude_lauf.Pausiert)


def _lies_json(pfad: Path, standard):
    return json.loads(pfad.read_text()) if pfad.exists() else standard


def _schreibe_json(pfad: Path, daten) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix(".tmp")
    tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=1))
    tmp.replace(pfad)


def melden(text: str) -> str:
    """Hinweis an Jan per Telegram (über die Zentrale), gibt die ID der Meldung zurück."""
    mid = meldungen.melden(AGENT, text)
    logger.info("Meldung: %s", text.splitlines()[0])
    return mid


def neue_mails() -> list[dict]:
    cfg = config.lade_config(HIER, pflicht=PFLICHT)
    return imap.neue_mails(cfg["IMAP_HOST"], int(cfg.get("IMAP_PORT", 993)),
                           cfg["IMAP_NUTZER"], cfg["IMAP_KENNWORT"], STAND_DATEI)


def gesperrte_absender() -> list[str]:
    return vorfilter.gesperrte_absender(regeln.allgemeine_regeln() + regeln.agent_regeln(HIER))


def post_pruefen(holen=neue_mails, laufen=claude_lauf.laufen, melden=melden,
                 gesperrt=gesperrte_absender, offen_datei: Path | None = None) -> None:
    offen_datei = offen_datei or MAILS_OFFEN
    # Geholte Mails erst als offen speichern: Fällt der Claude-Lauf aus, gehen sie nicht verloren.
    offen = _lies_json(offen_datei, []) + holen()
    if not offen:
        return
    _schreibe_json(offen_datei, offen)

    behalten, weg = vorfilter.vorfiltern(offen, gesperrt())
    for m, grund in weg:
        logger.info("Vorgefiltert (%s): uid %s", grund, m["uid"])
    if behalten:
        try:
            e = laufen(AGENT, HIER, einordnung.prompt(behalten), art="routine", zeitgesteuert=True)
        except WARTEN as f:
            logger.info("Post wartet (%d Mails offen): %s", len(offen), f)
            return
        if not e.ok:
            raise claude_lauf.LaufFehler(f"Einordnung fehlgeschlagen, {len(offen)} Mails bleiben offen: {e.text[:300]}")
        if text := einordnung.meldung(e.text, len(behalten), len(weg)):
            melden(text)
        else:
            logger.info("%d Mails geprüft, %d vorgefiltert, nichts Wichtiges", len(behalten), len(weg))
    else:
        logger.info("%d Mails, alle vorgefiltert", len(weg))
    offen_datei.unlink()


def schritt_fehler_melden(schritt: str, f: Exception, heute: str | None = None, datei: Path | None = None,
                          melden=melden) -> bool:
    """Meldet einen fehlgeschlagenen Schritt, höchstens einmal am Tag je Schritt."""
    datei = datei or FEHLER_DATEI
    heute = heute or date.today().isoformat()
    stand = _lies_json(datei, {})
    if stand.get(schritt) == heute:
        return False
    melden(f"[post] Schritt {schritt} fehlgeschlagen: {type(f).__name__}: {f}\n"
           f"Weitere Fehler dieses Schritts heute nur im Log: posteingang/logs/posteingang.log")
    stand[schritt] = heute
    _schreibe_json(datei, stand)
    return True


if __name__ == "__main__":
    for schritt in (post_pruefen,):
        try:
            schritt()
        except Exception as f:  # noqa: BLE001 – ein Fehler soll die anderen Schritte nicht blockieren
            logger.exception("Schritt %s fehlgeschlagen", schritt.__name__)
            try:
                schritt_fehler_melden(schritt.__name__, f)
            except Exception:  # noqa: BLE001 – Melden darf den Lauf nicht abbrechen
                logger.exception("Fehler von %s nicht gemeldet", schritt.__name__)
