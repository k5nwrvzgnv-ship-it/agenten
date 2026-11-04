"""Agent "uniportal": wertet mündliche Übungen aus, Einstieg des Dienstes uni-portal-frage.

Gestartet von uni-portal-frage.path, sobald in data/warteschlange/ ein Auftrag liegt. Eigener Agent-Ordner uni/portal/
und damit eigene Sperre data/lauf.lock: Er läuft auch, während uni.service eine Recherche macht. Er lädt uni/.env nicht.

Claude bekommt alles im Prompt und keine Werkzeuge (kein Bash, kein Lesen, kein Schreiben). Der Name steht deshalb nicht
in shared/einstellungen.toml: Die Einstellungen für den Lauf setzt lauf_einstellungen, wie lia/chat/agent.py.

Dateiname nicht agent.py: Im Portal liegt uni/ mit dessen agent.py ebenfalls auf dem Suchpfad.

Stände (uebungen.py): läuft; wartet, solange alle Plätze belegt sind; nach WARTEN_S oder bei knappem Kontingent wird der
Auftrag geparkt und nur Jans Knopf startet ihn neu. Fehler landen mit Grund auf der Seite; technische auch als Meldung.
"""

import copy
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HIER = Path(__file__).resolve().parent
sys.path.append(str(HIER.parent))  # lernmodell.py liegt in uni/; hinten, damit eigene Namen vorgehen

import lernmodell  # noqa: E402
from agentkit import claude_lauf, einstellungen, log, meldungen, regeln, verbrauch  # noqa: E402

import ablage  # noqa: E402
import bewertung  # noqa: E402
import uebungen  # noqa: E402

AGENT = "uniportal"  # nur a-z: Meldungen lassen keine anderen Namen zu (agentkit._ablage.AGENT_MUSTER)
UNI = HIER.parent
DATEN = HIER / "data"
ZONE = ZoneInfo("Europe/Berlin")
logger = log.hole_logger(HIER, "uni-portal-frage")
# Sitzungen, die claude -p selbst ablegt (enthalten das Transkript): nach dem Lauf löschen, wie lia/chat
SITZUNGEN = Path.home() / ".claude" / "projects" / str(HIER).replace("/", "-")
MAX_MINUTEN = 10  # ein Lauf; Opus schreibt die Auswertung am Stück, ohne Werkzeuge
MAX_VERSUCHE = 3  # so oft darf eine Übung ohne Endstand starten (z. B. Speicher voll), dann fehlgeschlagen
WARTEN_S = 30 * 60  # so lange wartet ein Auftrag auf einen Platz, danach geparkt
PAUSE_S = 60  # alle so viele Sekunden neu versuchen


def _zeit() -> str:
    return datetime.now(ZONE).isoformat(timespec="seconds")


def lauf_einstellungen(cfg: dict | None = None) -> dict:
    """Ohne Werkzeuge (--tools ""). warten_minuten=0: Der Agent wartet selbst, damit die Seite "wartet" zeigen kann."""
    cfg = copy.deepcopy(cfg or einstellungen.lade())
    cfg["werkzeuge"][AGENT] = [""]
    cfg["lauf"].update(max_schritte=3, max_minuten=MAX_MINUTEN, warten_minuten=0)
    return cfg


def claude_fragen(prompt: str, uebung_id: str, sitzung: str | None = None) -> claude_lauf.Ergebnis:
    return claude_lauf.laufen(AGENT, HIER, prompt, art="anspruchsvoll", auftrag_id=f"uebung-{uebung_id}",
                              sitzung_fortsetzen=sitzung, cfg=lauf_einstellungen())


def jan_melden(text: str) -> None:
    meldungen.melden(AGENT, f"Uni-Portal: {text}")


def sitzung_loeschen(sitzung: str | None, ordner: Path = SITZUNGEN) -> None:
    if sitzung:
        (ordner / f"{Path(sitzung).name}.jsonl").unlink(missing_ok=True)


def kontingent_stufe() -> tuple[str, float | None]:
    stand = verbrauch.letzter_stand()
    return verbrauch.stufe(stand, einstellungen.lade()), (stand or {}).get("reset_status")


def _regeln_von_uni() -> str:
    """Die gelernten Regeln gelten auch hier; der Agent hat bewusst keine eigene STATUS.md mit Regeln."""
    return "\n".join(f"- {r}" for r in regeln.agent_regeln(UNI))


class Geparkt(Exception):
    """Der Auftrag wartet, bis Jan ihn anstößt. Der Text steht auf der Seite."""


class Gescheitert(Exception):
    """Endstand fehlgeschlagen. Der Text steht auf der Seite."""


def _mit_warten(ordner: Path, ausfuehren, warten_s: float, pause_s: float, schlafen) -> claude_lauf.Ergebnis:
    """Lauf starten; sind alle Plätze belegt, steht "wartet" auf der Seite und es wird neu versucht."""
    ende = time.monotonic() + warten_s
    while True:
        uebungen.stand_aendern(ordner, stand="laeuft", grund=None, aktualisiert=_zeit())
        try:
            return ausfuehren()
        except (claude_lauf.KeinPlatz, claude_lauf.LaeuftSchon) as f:
            logger.info("%s: wartet (%s)", ordner.name, type(f).__name__)
            if time.monotonic() >= ende:
                raise Geparkt("Alle Plätze sind seit langem belegt, vermutlich läuft eine Recherche. "
                              "Starte die Auswertung später mit dem Knopf.") from None
            uebungen.stand_aendern(ordner, stand="wartet", grund="Alle Plätze sind gerade belegt. Startet von selbst, "
                                   "sobald einer frei wird.", aktualisiert=_zeit())
            schlafen(pause_s)


def _ein_lauf(ordner: Path, fragen, prompt: str, sitzung: str | None, melden, warten_s, pause_s, schlafen) -> claude_lauf.Ergebnis:
    uebung_id = ordner.name
    try:
        return _mit_warten(ordner, lambda: fragen(prompt, uebung_id, sitzung), warten_s, pause_s, schlafen)
    except claude_lauf.LimitErreicht as f:
        raise Geparkt(f"Kontingent aufgebraucht, wieder frei ab {verbrauch.zeit_text(f.reset)}. Startet nicht von "
                      "selbst, dann bitte den Knopf nehmen.") from None
    except claude_lauf.Zeitueberschreitung:
        raise Gescheitert(f"Die Auswertung dauerte länger als {MAX_MINUTEN} Minuten.") from None
    except (Geparkt, Gescheitert):
        raise
    except Exception as f:  # jeder andere Abbruch: Grund auf der Seite, Ursache im Log und als Meldung
        logger.exception("%s: Lauf fehlgeschlagen", uebung_id)
        melden(f"Auswertung {uebung_id} fehlgeschlagen: {type(f).__name__}")
        raise Gescheitert(f"Technischer Fehler ({type(f).__name__}). Jan ist informiert.") from None


def auswerten(modul_ordner: Path, ordner: Path, fragen=claude_fragen, melden=jan_melden, loeschen=sitzung_loeschen,
              regeltext=_regeln_von_uni, warten_s: float = WARTEN_S, pause_s: float = PAUSE_S,
              schlafen=time.sleep) -> tuple[dict, dict]:
    """Eine Übung auswerten. Rückgabe: (Auswertung, Messwerte). Wirft Geparkt oder Gescheitert."""
    rubrik = uebungen.rubrik_lesen(modul_ordner)
    if not rubrik:
        raise Gescheitert("Für dieses Modul liegt keine Rubrik vor.")
    plan = lernmodell.lies_json(modul_ordner / "pruefungsplan.json", {})
    karten = lernmodell.lies_json(modul_ordner / "karten.json", [])
    transkript = (ordner / ablage.TRANSKRIPT).read_text(encoding="utf-8")
    try:
        prompt = bewertung.prompt_bauen(rubrik, plan, karten, transkript, regeltext())
    except bewertung.PromptZuGross as f:
        raise Gescheitert(str(f)) from None

    messung = {"usd": 0.0, "dauer_s": 0.0, "schritte": 0, "tokens": 0, "laeufe": 0, "prompt_bytes": len(prompt.encode())}
    sitzungen: list[str | None] = []

    def fragen_und_messen(text: str, sitzung: str | None) -> claude_lauf.Ergebnis:
        e = _ein_lauf(ordner, fragen, text, sitzung, melden, warten_s, pause_s, schlafen)
        sitzungen.append(e.sitzung)
        messung["usd"] += e.usd
        messung["dauer_s"] += e.dauer_s
        messung["schritte"] += e.schritte
        messung["tokens"] += e.tokens
        messung["laeufe"] += 1
        return e

    try:
        e = fragen_und_messen(prompt, None)
        if not e.ok:
            melden(f"Auswertung {ordner.name}: claude ohne brauchbare Antwort ({e.schritte} Schritte)")
            raise Gescheitert("Claude hat keine brauchbare Antwort geliefert. Jan ist informiert.")
        ergebnis, harte, weiche = bewertung.pruefen(bewertung.antwort_lesen(e.text), rubrik, plan, karten, transkript)
        messung["nachbesserung"] = bool(harte or weiche)
        erste_fehler = harte + weiche
        if harte or weiche:  # genau eine Nachbesserung in derselben Sitzung
            logger.info("%s: Nachbesserung, %d harte, %d weiche Fehler", ordner.name, len(harte), len(weiche))
            try:
                zweite = fragen_und_messen(bewertung.nachbesserung_prompt(harte + weiche), e.sitzung)
            except (Geparkt, Gescheitert):
                if ergebnis is None:
                    raise
                logger.info("%s: Nachbesserung ausgefallen, die erste Antwort bleibt", ordner.name)
                zweite = None
            if zweite is not None and zweite.ok:
                neu, harte2, weiche2 = bewertung.pruefen(bewertung.antwort_lesen(zweite.text), rubrik, plan, karten, transkript)
                if neu is not None:  # sonst bleibt die erste Antwort, wenn sie brauchbar war
                    ergebnis, harte, weiche = neu, harte2, weiche2
        if ergebnis is None:
            raise Gescheitert("Claudes Antwort war auch nach einer Nachbesserung unbrauchbar: " + "; ".join(harte)[:300])
    finally:
        for s in sitzungen:
            loeschen(s)
    ergebnis.update(id=ordner.name, zeit=_zeit(), rubrik_summe=uebungen.rubrik_summe(rubrik),
                    rubrik_bestaetigt_beim_lauf=uebungen.rubrik_bestaetigt(rubrik), verworfen=weiche,
                    erste_fehler=erste_fehler)
    return ergebnis, messung


def bearbeiten(auftrag: dict, uni: Path = UNI, daten: Path = DATEN, stufe=kontingent_stufe, **kw) -> None:
    """Einen Auftrag bis zum Endstand bringen: fertig, fehlgeschlagen oder geparkt."""
    uebung_id, modul = auftrag["id"], auftrag["modul"]
    ordner = ablage.uebung_ordner(uni, modul, uebung_id)
    if ordner is None:
        logger.warning("Auftrag %s: keine Übung zu dieser ID", uebung_id)
        return
    stand = uebungen.stand_lesen(ordner)
    versuche = stand.get("versuche", 0) + 1
    if versuche > MAX_VERSUCHE:
        uebungen.stand_aendern(ordner, stand="fehlgeschlagen", grund=f"Der Lauf brach {MAX_VERSUCHE}-mal ab, ohne ein "
                               "Ergebnis zu schreiben (Speicher oder Dienst).")
        return
    uebungen.stand_aendern(ordner, versuche=versuche)
    wert, reset = stufe()
    if wert == "limit" or (wert == "nur_auftraege" and not auftrag.get("erzwingen")):
        grund = (f"Kontingent aufgebraucht, wieder frei ab {verbrauch.zeit_text(reset)}. Startet nicht von selbst, dann "
                 "bitte den Knopf nehmen." if wert == "limit" else
                 "Kontingent ist knapp. Startet nicht von selbst; der Knopf startet die Auswertung trotzdem.")
        uebungen.stand_aendern(ordner, stand="wartet", grund=grund, versuche=0)
        uebungen.parken(daten, auftrag)
        logger.info("%s: geparkt, Stufe %s", uebung_id, wert)
        return
    try:
        ergebnis, messung = auswerten(ablage.modul_ordner(uni, modul), ordner, **kw)
    except Geparkt as f:
        uebungen.stand_aendern(ordner, stand="wartet", grund=str(f), versuche=0, aktualisiert=_zeit())
        uebungen.parken(daten, auftrag)
        logger.info("%s: geparkt", uebung_id)
        return
    except Gescheitert as f:
        uebungen.stand_aendern(ordner, stand="fehlgeschlagen", grund=str(f), aktualisiert=_zeit())
        logger.warning("%s: fehlgeschlagen: %s", uebung_id, f)
        return
    lernmodell.schreibe_json(ordner / ablage.AUSWERTUNG, ergebnis)
    uebungen.stand_aendern(ordner, stand="fertig", grund=None, aktualisiert=_zeit(), **messung)
    logger.info("%s: fertig, %d Läufe, %d Schritte, %d Tokens, %.1f s, %.3f USD, %d verworfen", uebung_id, messung["laeufe"],
                messung["schritte"], messung["tokens"], messung["dauer_s"], messung["usd"], len(ergebnis["verworfen"]))


def auftrag_lesen(pfad: Path) -> dict | None:
    """Auftrag prüfen: ID wie der Dateiname, Modul aus der Liste. Ungültig: None."""
    try:
        roh = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(roh, dict) or roh.get("id") != pfad.stem or not ablage.UEBUNG_ID.match(pfad.stem):
        return None
    if roh.get("modul") not in ablage.MODULE:
        return None
    return {"id": roh["id"], "modul": roh["modul"], "erzwingen": roh.get("erzwingen") is True}


def abarbeiten(uni: Path = UNI, daten: Path = DATEN, **kw) -> int:
    """Alle wartenden Aufträge, älteste zuerst, auch solche, die währenddessen dazukommen. Der Auftrag verschwindet
    immer aus der Warteschlange, sonst startet die Pfad-Unit den Dienst im Kreis. Stirbt der Prozess hart, bleibt er
    liegen und wird neu gestartet (MAX_VERSUCHE zählt das)."""
    gesehen, anzahl = set(), 0
    schlange = daten / uebungen.WARTESCHLANGE
    while neue := sorted((p for p in schlange.glob("*.json") if p.name not in gesehen), key=lambda p: p.name):
        for pfad in neue:
            gesehen.add(pfad.name)
            auftrag = auftrag_lesen(pfad)
            try:
                if auftrag is None:
                    logger.warning("%s: ungültiger Auftrag, entfernt", pfad.name)
                else:
                    bearbeiten(auftrag, uni, daten, **kw)
                    anzahl += 1
            except Exception as f:  # darf die übrigen Aufträge nicht aufhalten
                logger.exception("%s: unerwarteter Fehler", pfad.name)
                ordner = ablage.uebung_ordner(uni, auftrag["modul"], auftrag["id"]) if auftrag else None
                if ordner:
                    uebungen.stand_aendern(ordner, stand="fehlgeschlagen", grund=f"Technischer Fehler ({type(f).__name__}).")
            finally:
                pfad.unlink(missing_ok=True)
    return anzahl


if __name__ == "__main__":
    abarbeiten()
