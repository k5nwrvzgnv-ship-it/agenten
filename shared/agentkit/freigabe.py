"""Freigabe-Warteschlange: shared/freigabe/offen/ und erledigt/.

Agenten legen hier Entwürfe ab (Mails, Nachrichten, Käufe ...). Sie senden
oder bezahlen nie selbst. Die Telegram-Zentrale zeigt offene Entwürfe an
und trägt Jans Entscheidung ein:
- freigegeben
- abgelehnt (optional mit Begründung)
- aendern (mit Kommentar; der Agent erstellt daraus einen neuen Entwurf
  mit `vorgaenger` = alte ID)

Verfall (Untersuchung 11/2026, B5): Ein Entwurf, über den VERFALL_TAGE lang nicht entschieden wurde, bekommt
den Status "abgelaufen" (verfallen_lassen, die Zentrale ruft es in jeder Prüfrunde auf). Abgelaufen ist endgültig
und wird nie ausgeführt: Ein später Klick auf einen alten Knopf sendet so keine wochenalte Mail mehr.

Nach "freigegeben" führt der Agent den Entwurf selbst aus (CLAUDE.md):
1. zur_ausfuehrung(agent) liefert freigegebene, noch nicht ausgeführte Entwürfe.
2. ausfuehrung_beginnen(id) prüft den Fingerabdruck (ausgeführt wird genau
   das, was Jan gesehen hat), bei Käufen die Obergrenze, und reserviert den
   Entwurf. Das klappt nur einmal.
3. Der Agent handelt.
4. ausfuehrung_abschliessen(id, ergebnis, erfolgreich) vermerkt das Ergebnis.
Stürzt der Agent zwischen 2 und 4 ab, wird NICHT automatisch wiederholt
(sonst könnte eine Mail doppelt rausgehen). unklare() listet solche Fälle
für Jan auf.
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from . import _ablage, ereignis
from ._ablage import AblageFehler as FreigabeFehler  # noqa: F401
from .config import SHARED_DIR

BASIS = SHARED_DIR / "freigabe"
ENTSCHEIDUNGEN = ("freigegeben", "abgelehnt", "aendern")
ABGELAUFEN = "abgelaufen"  # kein Wert für entscheide(): entsteht nur durch verfallen_lassen()
VERFALL_TAGE = 7
logger = logging.getLogger("agentkit.freigabe")


def fingerabdruck(entwurf: dict) -> str:
    """Prüfsumme über alles, was Jan beim Freigeben sieht und was ausgeführt wird."""
    teile = {k: entwurf.get(k) for k in ("agent", "typ", "titel", "inhalt", "daten")}
    roh = json.dumps(teile, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(roh).hexdigest()


ZENTRALE, GRUPPE = "zentrale", "gruppe"
ANZEIGEN = (ZENTRALE, GRUPPE)


def in_der_zentrale(entwurf: dict) -> bool:
    """Zeigt die Zentrale diesen Entwurf? Ältere Einträge ohne Feld anzeige: ja."""
    return entwurf.get("anzeige", ZENTRALE) == ZENTRALE


def neuer_entwurf(
    agent: str,
    titel: str,
    inhalt: str,
    typ: str = "entwurf",
    daten: dict | None = None,
    vorgaenger: str | None = None,
    basis: Path | None = None,
    anzeige: str = ZENTRALE,
) -> str:
    """Legt einen Entwurf an und gibt seine ID zurück.

    typ: z. B. "mail", "nachricht", "kauf". daten: alles, was der Agent nach
    der Freigabe braucht (Empfänger, Betreff, Link ...). anzeige: wo Jan den Entwurf sieht und entscheidet,
    "zentrale" (Standard) oder "gruppe" (Rüdigers Projektgruppe, die Zentrale zeigt ihn dann nicht).
    """
    if anzeige not in ANZEIGEN:
        raise FreigabeFehler(f"unbekannte Anzeige: {anzeige}")
    eigene_basis, basis = basis, basis or BASIS
    if vorgaenger is not None:
        _ablage.pruefe_id(vorgaenger)
    eintrag_id = _ablage.neue_id(agent)
    eintrag = {
        "id": eintrag_id,
        "agent": agent,
        "typ": typ,
        "titel": titel,
        "inhalt": inhalt,
        "daten": daten or {},
        "vorgaenger": vorgaenger,
        "anzeige": anzeige,
        "erstellt": _ablage.jetzt(),
        "status": "offen",
        "entschieden": None,
        "kommentar": "",
        "ausfuehrung_start": None,
        "ausgefuehrt": None,
        "ausfuehrung": "",
        "erfolgreich": None,
    }
    eintrag["fingerabdruck"] = fingerabdruck(eintrag)
    _ablage.schreibe(_ablage.ordner(basis, "offen") / f"{eintrag_id}.json", eintrag)
    _ereignis("freigabe.wartet", eintrag_id, eigene_basis, typ=typ, vorgaenger=vorgaenger)
    return eintrag_id


def _ereignis(art: str, eintrag_id: str, basis: Path | None, **daten) -> None:
    ereignis.schreiben(art, eintrag_id.split("-")[2], ordner=ereignis.ordner_zu(basis),
                       daten={"freigabe": eintrag_id, **daten})


def offene(agent: str | None = None, basis: Path | None = None) -> list[dict]:
    return _ablage.liste(_ablage.ordner(basis or BASIS, "offen"), agent)


def erledigte(agent: str | None = None, basis: Path | None = None) -> list[dict]:
    return _ablage.liste(_ablage.ordner(basis or BASIS, "erledigt"), agent)


def entscheide(
    eintrag_id: str,
    status: str,
    kommentar: str = "",
    gesehen: str | None = None,
    basis: Path | None = None,
) -> dict:
    """Trägt Jans Entscheidung ein und verschiebt den Entwurf nach erledigt/.

    gesehen: Fingerabdruck des Entwurfs, den Telegram Jan angezeigt hat. Bei
    "freigegeben" Pflicht; passt er nicht zum gespeicherten Entwurf, wird
    nicht freigegeben.
    """
    if status not in ENTSCHEIDUNGEN:
        raise FreigabeFehler(f"Unbekannte Entscheidung: {status!r}")
    if status == "aendern" and not kommentar.strip():
        raise FreigabeFehler("Bei 'aendern' ist ein Kommentar nötig")
    eigene_basis, basis = basis, basis or BASIS
    if status == "freigegeben":
        _ablage.pruefe_id(eintrag_id)
        pfad = _ablage.ordner(basis, "offen") / f"{eintrag_id}.json"
        if not pfad.exists():
            raise FreigabeFehler(f"{eintrag_id} ist nicht (mehr) offen")
        if gesehen is None or gesehen != fingerabdruck(_ablage.lies(pfad)):
            raise FreigabeFehler(f"{eintrag_id}: Entwurf weicht von der Anzeige ab, nicht freigegeben")
    eintrag = _ablage.abschliessen(
        _ablage.ordner(basis, "offen"),
        _ablage.ordner(basis, "erledigt"),
        eintrag_id,
        {"status": status, "entschieden": _ablage.jetzt(), "kommentar": kommentar},
    )
    _ereignis("freigabe.entschieden", eintrag_id, eigene_basis, status=status)
    return eintrag


def alter_stunden(entwurf: dict, jetzt: datetime | None = None) -> float:
    """Stunden seit dem Anlegen. Ohne lesbares Datum 0 (dann verfällt nichts wegen eines kaputten Feldes)."""
    try:
        erstellt = datetime.fromisoformat(entwurf["erstellt"])
        if erstellt.tzinfo is None:
            erstellt = erstellt.astimezone()
    except (KeyError, TypeError, ValueError):
        logger.warning("Entwurf %s ohne lesbares Datum, Alter unbekannt", entwurf.get("id"))
        return 0.0
    return ((jetzt or datetime.now().astimezone()) - erstellt).total_seconds() / 3600


def verfallen_lassen(basis: Path | None = None, jetzt: datetime | None = None, tage: int = VERFALL_TAGE) -> list[dict]:
    """Schließt offene Entwürfe ab, die älter als `tage` sind: Status "abgelaufen". Gibt sie zurück.

    Das Verschieben klappt nur einmal: Entscheidet Jan im selben Augenblick, gewinnt genau einer von beiden.
    """
    eigene_basis, basis = basis, basis or BASIS
    abgelaufen = []
    for e in offene(basis=basis):
        if alter_stunden(e, jetzt) < tage * 24:
            continue
        try:
            eintrag = _ablage.abschliessen(
                _ablage.ordner(basis, "offen"), _ablage.ordner(basis, "erledigt"), e["id"],
                {"status": ABGELAUFEN, "entschieden": _ablage.jetzt(),
                 "kommentar": f"nach {tage} Tagen ohne Entscheidung abgelaufen"})
        except FreigabeFehler:
            continue  # gerade entschieden
        logger.info("Entwurf %s (%s) abgelaufen", e["id"], e.get("agent"))
        _ereignis("freigabe.entschieden", e["id"], eigene_basis, status=ABGELAUFEN)
        abgelaufen.append(eintrag)
    return abgelaufen


def abgelaufene(agent: str | None = None, basis: Path | None = None) -> list[dict]:
    return [e for e in erledigte(agent, basis) if e["status"] == ABGELAUFEN]


def _erledigt_pfad(eintrag_id: str, basis: Path) -> Path:
    _ablage.pruefe_id(eintrag_id)
    return _ablage.ordner(basis, "erledigt") / f"{eintrag_id}.json"


def zur_ausfuehrung(agent: str | None = None, basis: Path | None = None) -> list[dict]:
    """Freigegebene Entwürfe, deren Ausführung noch nicht begonnen hat."""
    return [
        e for e in erledigte(agent, basis)
        if e["status"] == "freigegeben" and e.get("ausfuehrung_start") is None
    ]


def unklare(agent: str | None = None, basis: Path | None = None) -> list[dict]:
    """Ausführung begonnen, aber nie abgeschlossen (z. B. Absturz). Jan muss prüfen."""
    return [
        e for e in erledigte(agent, basis)
        if e.get("ausfuehrung_start") is not None and e.get("ausgefuehrt") is None
    ]


def ausfuehrung_beginnen(
    eintrag_id: str, kauf_limit_euro: str | float | None = None, basis: Path | None = None
) -> dict:
    """Prüft und reserviert einen freigegebenen Entwurf für die Ausführung.

    kauf_limit_euro: Wert von KAUF_LIMIT_EURO aus der Config. Bei typ "kauf"
    muss daten["betrag_euro"] gesetzt sein und darf das Limit nicht übersteigen.
    """
    basis = basis or BASIS
    pfad = _erledigt_pfad(eintrag_id, basis)
    if not pfad.exists():
        raise FreigabeFehler(f"{eintrag_id} ist nicht entschieden")
    entwurf = _ablage.lies(pfad)
    if entwurf["status"] != "freigegeben":
        raise FreigabeFehler(f"{eintrag_id} ist nicht freigegeben")
    if entwurf.get("fingerabdruck") != fingerabdruck(entwurf):
        raise FreigabeFehler(f"{eintrag_id} wurde nach der Freigabe verändert, keine Ausführung")
    if entwurf["typ"] == "kauf":
        _pruefe_kauf(entwurf, kauf_limit_euro)

    # Sperrdatei: os.open mit O_EXCL klappt nur für den ersten Aufrufer.
    sperre = pfad.with_name(f"{eintrag_id}.ausfuehrung")
    try:
        os.close(os.open(sperre, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
    except FileExistsError:
        raise FreigabeFehler(f"{eintrag_id} wird schon oder wurde schon ausgeführt") from None
    entwurf["ausfuehrung_start"] = _ablage.jetzt()
    _ablage.schreibe(pfad, entwurf)
    _ereignis("freigabe.ausfuehrung_begonnen", eintrag_id, None if basis is BASIS else basis, typ=entwurf["typ"])
    return entwurf


def _pruefe_kauf(entwurf: dict, kauf_limit_euro) -> None:
    if kauf_limit_euro in (None, ""):
        raise FreigabeFehler("KAUF_LIMIT_EURO ist nicht gesetzt, es wird nicht gekauft")
    try:
        limit = float(str(kauf_limit_euro).replace(",", "."))
        betrag = float(entwurf["daten"]["betrag_euro"])
    except (KeyError, TypeError, ValueError):
        raise FreigabeFehler("Kauf ohne gültigen Betrag oder Limit, es wird nicht gekauft") from None
    if betrag <= 0 or betrag > limit:
        raise FreigabeFehler(f"Kauf über {betrag:.2f} EUR liegt über dem Limit von {limit:.2f} EUR")


def ausfuehrung_abschliessen(
    eintrag_id: str, ergebnis: str, erfolgreich: bool = True, basis: Path | None = None
) -> dict:
    """Vermerkt das Ergebnis der Ausführung (für die Meldung an Jan)."""
    basis = basis or BASIS
    pfad = _erledigt_pfad(eintrag_id, basis)
    entwurf = _ablage.lies(pfad)
    if entwurf.get("ausfuehrung_start") is None:
        raise FreigabeFehler(f"{eintrag_id}: Ausführung wurde nicht begonnen")
    if entwurf.get("ausgefuehrt") is not None:
        raise FreigabeFehler(f"{eintrag_id} ist schon abgeschlossen")
    entwurf.update(ausgefuehrt=_ablage.jetzt(), ausfuehrung=ergebnis, erfolgreich=erfolgreich)
    _ablage.schreibe(pfad, entwurf)
    _ereignis("freigabe.ausgefuehrt", eintrag_id, None if basis is BASIS else basis, erfolgreich=erfolgreich)
    return entwurf
