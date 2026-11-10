"""Agent chat in Lias Instanz (AGENTKIT_INSTANZ=lia/instanz), Einstieg des Dienstes lia-chat.

Beantwortet Lias Fragen aus der Spalte „Fragen“ der Web-App: liest data/fragen/<id>.json (schnittstelle.py),
baut den Kontext des Orts aus Dateien (kontext.py), fragt Claude ohne Werkzeuge (auf Lias Wunsch mit Websuche) und schreibt
data/antworten/<id>.json. Startet nie einen Auftrag und handelt nie nach außen. Plan: plan.md.
Aufruf: AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python agent.py [--aufraeumen]
"""

import copy
import json
import shutil
import sys
from pathlib import Path

import chatverlauf
import gespraechlauf
import kontext
import schnittstelle
import wissen
from agentkit import claude_lauf, config, einstellungen, log, meldungen, struktur, textfassung, verbrauch

AGENT = "chat"
HIER = Path(__file__).resolve().parent
DATEN = HIER / "data"
logger = log.hole_logger(HIER, AGENT)
# Sitzungen, die claude -p selbst ablegt (Ordnername = Arbeitsordner mit - statt /). Die der alten Spalte
# „Fragen“ werden gleich gelöscht (Verlauf in data/verlauf.jsonl), die der Gespräche erst mit dem Gespräch.
SITZUNGEN = Path.home() / ".claude" / "projects" / str(HIER).replace("/", "-")
NETZ_DOMAINS_VON = "recherche"  # WebFetch nur auf die Liste von Lias Recherche (einstellungen.toml)
NETZ_SCHRITTE = 8  # Suchen und Seiten öffnen sind je ein Schritt
DATEI_ZEICHEN = 60_000  # Text aus Lias Dateien je Frage höchstens so viel (alle Dateien zusammen)

TEXTE = {
    "limit": "Gerade ist die Rechenzeit aufgebraucht. Frag bitte ab {zeit} noch einmal.",
    "belegt": "Gerade arbeiten mehrere Aufträge gleichzeitig. Frag bitte in ein paar Minuten noch einmal.",
    "zeit": "Die Antwort hat zu lange gedauert. Versuch es bitte noch einmal, gern etwas kürzer gefragt.",
    "technik": "Das hat leider nicht geklappt. Jan ist informiert und kümmert sich.",
}


def jan_melden(text: str) -> None:
    """Meldung in Jans Instanz (seine Zentrale), nicht in Lias."""
    meldungen.melden(AGENT, f"Lia, Agent chat: {text}", basis=config.KONTINGENT_DIR / "meldungen")


def lauf_einstellungen(gruendlich: bool, cfg: dict | None = None, netz: bool = False) -> dict:
    """Einstellungen für einen Chat-Lauf: ohne Werkzeuge (--tools ""), wenige Schritte, kurze Zeit- und Wartegrenzen.

    netz (Jan 02.11.2026, nur auf Lias Häkchen): WebSearch und WebFetch, WebFetch nur auf die Domains von Lias
    Recherche ([webfetch] recherche). Fehlt die Liste, nur WebSearch: WebFetch ohne Liste dürfte überall hin.
    """
    cfg = copy.deepcopy(cfg or einstellungen.lade())
    if netz:
        domains = cfg.get("webfetch", {}).get(NETZ_DOMAINS_VON)
        cfg["werkzeuge"][AGENT] = ["WebSearch", "WebFetch"] if domains else ["WebSearch"]
        if domains:
            cfg["webfetch"][AGENT] = list(domains)
        cfg["lauf"].update(max_schritte=NETZ_SCHRITTE, max_minuten=6 if gruendlich else 4, warten_minuten=1)
    else:
        cfg["werkzeuge"][AGENT] = [""]
        cfg["lauf"].update(max_schritte=3, max_minuten=5 if gruendlich else 2, warten_minuten=1)
    return cfg


def claude_fragen(prompt: str, gruendlich: bool, frage_id: str, netz: bool = False) -> claude_lauf.Ergebnis:
    return claude_lauf.laufen(AGENT, HIER, prompt, art="anspruchsvoll" if gruendlich else "routine",
                              auftrag_id=f"chat-{frage_id}", cfg=lauf_einstellungen(gruendlich, netz=netz))


def sitzung_loeschen(sitzung: str | None, ordner: Path = SITZUNGEN) -> None:
    """Sitzungsdatei und den Ordner gleichen Namens (claude legt dort z. B. Webabrufe ab)."""
    if sitzung:
        (ordner / f"{Path(sitzung).name}.jsonl").unlink(missing_ok=True)
        shutil.rmtree(ordner / Path(sitzung).name, ignore_errors=True)


def dateien_text(frage: dict, ordner: Path = DATEN) -> str:
    """Text aus Lias Dateien der Frage, je Datei mit Name, zusammen höchstens DATEI_ZEICHEN. Ohne Dateien: leer."""
    namen = frage.get("dateien") or []
    teile, je_datei = [], DATEI_ZEICHEN // max(len(namen), 1)
    for name in namen:
        try:
            text = (textfassung.als_text(schnittstelle.dateien_ordner(frage["id"], ordner) / name) or "").strip()
        except Exception as f:  # kaputte oder verschlüsselte Datei: Claude bekommt den Hinweis, Lia die Antwort
            logger.warning("Frage %s: Datei nicht lesbar: %s", frage["id"], type(f).__name__)
            text = "(Die Datei ließ sich nicht lesen.)"
        if text.startswith("(Kein Text gefunden"):  # Scan: im Chat ohne Werkzeuge nicht lesbar
            text = "(Kein Text gefunden, vermutlich ein Scan. Lesen kann ich ihn nicht.)"
        if len(text) > je_datei:
            text = text[:je_datei] + "\n[… gekürzt]"
        teile.append(f"--- Datei: {name}\n{text or '(leer)'}")
    return "\n\n".join(teile)


def dateien_loeschen(frage_id: str, ordner: Path = DATEN) -> None:
    shutil.rmtree(schnittstelle.dateien_ordner(frage_id, ordner), ignore_errors=True)


def antwort(frage: dict, text: str, ok: bool, fehler: str | None = None, wieder_frei: str | None = None) -> dict:
    ort = frage.get("ort") or {}
    return {"id": frage["id"], "zeit": chatverlauf.jetzt().isoformat(timespec="seconds"), "ok": ok, "text": text,
            "gruendlich": frage.get("gruendlich", False), "netz": frage.get("netz", False), "reihe": ort.get("reihe"),
            "chip": ort.get("chip"), "fehler": fehler, "wieder_frei": wieder_frei}


def beantworten(frage: dict, instanz: Path, ordner: Path = DATEN, fragen=claude_fragen, melden=jan_melden,
                loeschen=sitzung_loeschen) -> dict:
    """Eine geprüfte Frage beantworten. Gibt die Antwort zurück (auch bei Fehlern, mit Satz für Lia)."""
    ort = frage["ort"]
    try:
        reihe = kontext.reihe_finden(kontext.reihen_laden(instanz), ort["reihe"]) if ort else None
    except (OSError, struktur.StrukturFehler) as f:  # kaputte reihen.toml: ohne Reihe antworten, Jan melden
        logger.warning("Reihen nicht lesbar: %s", f)
        melden(f"reihen.toml nicht lesbar, Chat antwortet ohne Reihe: {f}")
        reihe = None
    verlauf = chatverlauf.am_ort(chatverlauf.lesen(ordner), ort["reihe"] if ort else None)
    netz = frage.get("netz", False)
    # Neue Dateien gehen mit; sonst der Text aus der letzten Frage mit Datei an diesem Ort (für Folgefragen)
    datei = dateien_text(frage, ordner) or next((e["dateitext"] for e in reversed(verlauf) if e.get("dateitext")), "")
    prompt = kontext.prompt(frage["text"], kontext.kontext_text(ort, reihe), verlauf, frage["gruendlich"], netz,
                            datei, neu=bool(frage.get("dateien")))
    try:
        e = fragen(prompt, frage["gruendlich"], frage["id"], netz=netz)
    except claude_lauf.LimitErreicht as f:
        zeit = verbrauch.zeit_text(f.reset)
        logger.warning("Frage %s: %s", frage["id"], f)
        return antwort(frage, TEXTE["limit"].format(zeit=zeit), False, "limit", zeit)
    except (claude_lauf.KeinPlatz, claude_lauf.LaeuftSchon) as f:
        logger.warning("Frage %s: %s", frage["id"], f)
        return antwort(frage, TEXTE["belegt"], False, "belegt")
    except claude_lauf.Zeitueberschreitung as f:
        logger.warning("Frage %s: %s", frage["id"], f)
        return antwort(frage, TEXTE["zeit"], False, "zeit")
    except Exception as f:  # jeder andere Abbruch: Lia bekommt einen Satz, Jan die Ursache
        logger.exception("Frage %s fehlgeschlagen", frage["id"])
        melden(f"Frage {frage['id']} fehlgeschlagen: {type(f).__name__}: {f}")
        return antwort(frage, TEXTE["technik"], False, "technik")
    loeschen(e.sitzung)
    logger.info("Frage %s: %d Zeichen, Ort %s, %s, Netz %s, %d Dateien, ok %s, %d Schritte, %.1f s, %.3f USD",
                frage["id"], len(frage["text"]), "ja" if ort else "nein",
                "gründlich" if frage["gruendlich"] else "schnell", "ja" if netz else "nein",
                len(frage.get("dateien") or []), e.ok, e.schritte, e.dauer_s, e.usd)
    if e.verweigert:  # z. B. WebFetch auf eine Seite außerhalb der Liste: nur zählen, keine Adressen ins Log
        logger.info("Frage %s: %d Werkzeug-Aufrufe abgelehnt", frage["id"], len(e.verweigert))
    if not e.ok or not e.text.strip():
        melden(f"Frage {frage['id']}: claude ohne brauchbare Antwort ({e.schritte} Schritte)")
        return antwort(frage, TEXTE["technik"], False, "technik")
    a = antwort(frage, e.text.strip(), True)
    chatverlauf.anhaengen(ordner, {"id": frage["id"], "zeit": a["zeit"], "reihe": a["reihe"], "chip": a["chip"],
                                   "gruendlich": a["gruendlich"], "netz": a["netz"], "frage": frage["text"],
                                   "antwort": a["text"], "dateien": frage.get("dateien") or [],
                                   "dateitext": datei if frage.get("dateien") else ""})
    return a


def frage_lesen(pfad: Path) -> dict:
    """Frage-Datei lesen und prüfen. Ungültig: FrageFehler mit einer id, soweit erkennbar."""
    try:
        roh = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as f:
        raise schnittstelle.FrageFehler(f"Frage-Datei nicht lesbar: {f}") from None
    return schnittstelle.frage_pruefen(roh)


GESPRAECH_ARTEN = ("nachricht", "bisher", "auftrag")


def gespraech_abarbeiten(pfad: Path, instanz: Path, ordner: Path, sitzungen: Path = gespraechlauf.GESPRAECH_SITZUNGEN,
                         sonder_sitzungen: Path = SITZUNGEN, claude=gespraechlauf.claude_gespraech,
                         melden=jan_melden, netz_an=gespraechlauf.netz_moeglich, lia: Path | None = wissen.LIA) -> bool:
    """Eintrag für ein Gespräch ({"art", "id", "gespraech"}) beantworten. False, wenn es keiner ist."""
    try:
        job = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(job, dict) or job.get("art") not in GESPRAECH_ARTEN:
        return False
    if not (schnittstelle.ID_MUSTER.match(str(job.get("id"))) and schnittstelle.ID_MUSTER.match(
            str(job.get("gespraech")))) or job["id"] != pfad.stem:
        logger.warning("%s: Gesprächs-Eintrag ungültig", pfad.name)
    elif job["art"] == "nachricht":
        schnittstelle.antwort_schreiben(gespraechlauf.nachricht_beantworten(
            job, instanz, ordner, sitzungen, claude=claude, melden=melden, netz_an=netz_an,
            sitzung_loeschen=lambda s: sitzung_loeschen(s, sitzungen), lia=lia), ordner)
    else:
        schnittstelle.antwort_schreiben(gespraechlauf.sonder_beantworten(
            job, instanz, ordner, claude=claude, melden=melden,
            sitzung_loeschen=lambda s: sitzung_loeschen(s, sonder_sitzungen)), ordner)
    pfad.unlink(missing_ok=True)
    return True


def gespraech_fehler(pfad: Path, ordner: Path) -> None:
    """Nach einem Fehler im Code: Antwort „technik“, Nachricht als fehlgeschlagen markieren, Eintrag weg (sonst
    startet lia-chat.path den Dienst immer wieder)."""
    try:
        job = json.loads(pfad.read_text(encoding="utf-8"))
        if schnittstelle.ID_MUSTER.match(str(job.get("id"))):
            schnittstelle.antwort_schreiben(gespraechlauf._antwort(job, False, gespraechlauf.TEXTE["technik"],
                                                                   "technik"), ordner)
            if schnittstelle.ID_MUSTER.match(str(job.get("gespraech"))):
                gespraechlauf._fehler_eintragen(job["gespraech"], job["id"], "technik", ordner)
    except Exception:  # noqa: BLE001 - Aufräumen nach dem Fehler darf nicht selbst hängen bleiben
        logger.exception("%s: Fehler nicht eintragbar", pfad.name)
    pfad.unlink(missing_ok=True)


def fragen_abarbeiten(instanz: Path = config.SHARED_DIR, ordner: Path = DATEN, gespraech_kw: dict | None = None,
                      **kw) -> int:
    """Alle wartenden Fragen und Gesprächs-Nachrichten der Reihe nach (älteste zuerst), auch solche, die
    währenddessen dazukommen. gespraech_kw: für Tests (claude, melden, sitzungen)."""
    chatverlauf.aufraeumen(ordner)
    gesehen, anzahl = set(), 0
    while neue := sorted((p for p in (ordner / "fragen").glob("*.json") if p.name not in gesehen),
                         key=lambda p: p.stat().st_mtime):
        for pfad in neue:
            gesehen.add(pfad.name)
            try:
                if gespraech_abarbeiten(pfad, instanz, ordner, **(gespraech_kw or {})):
                    anzahl += 1
                    continue
            except Exception as f:  # Fehler im eigenen Code: Lia bekommt einen Satz, Jan die Ursache
                logger.exception("%s: Gesprächs-Eintrag fehlgeschlagen", pfad.name)
                (gespraech_kw or {}).get("melden", jan_melden)(
                    f"Gesprächs-Eintrag {pfad.name} fehlgeschlagen: {type(f).__name__}: {f}")
                gespraech_fehler(pfad, ordner)
                continue
            try:
                frage = frage_lesen(pfad)
            except schnittstelle.FrageFehler as f:
                logger.warning("%s: %s", pfad.name, f)
                if schnittstelle.ID_MUSTER.match(pfad.stem):
                    schnittstelle.antwort_schreiben(antwort({"id": pfad.stem}, str(f), False, "ungueltig"), ordner)
                    dateien_loeschen(pfad.stem, ordner)
                pfad.unlink(missing_ok=True)
                continue
            try:
                schnittstelle.antwort_schreiben(beantworten(frage, instanz, ordner, **kw), ordner)
            finally:  # Lias Dateien bleiben nie liegen, auch nicht nach einem Fehler (ihr Text steht im Verlauf)
                dateien_loeschen(frage["id"], ordner)
            pfad.unlink(missing_ok=True)
            anzahl += 1
    return anzahl


def aufraeumen(ordner: Path = DATEN, sitzungen: Path = SITZUNGEN,
               gespraech_sitzungen: Path = gespraechlauf.GESPRAECH_SITZUNGEN) -> None:
    """Täglich (lia-chat-aufraeumen.timer): alter Verlauf, alte Antworten, Gespräche 30 Tage nach der letzten
    Nachricht (samt Dateien und Sitzung), claude-Sitzungen, die zu keinem Gespräch gehören."""
    weg = chatverlauf.aufraeumen(ordner) + gespraechlauf.aufraeumen(ordner, [sitzungen, gespraech_sitzungen])
    logger.info("Aufräumen: %d gelöscht", weg)


if __name__ == "__main__":
    if "--aufraeumen" in sys.argv[1:]:
        aufraeumen()
    else:
        fragen_abarbeiten()
