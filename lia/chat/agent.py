"""Agent chat in Lias Instanz (AGENTKIT_INSTANZ=lia/instanz), Einstieg des Dienstes lia-chat.

Beantwortet Lias Fragen aus der Spalte „Fragen“ der Web-App: liest data/fragen/<id>.json (schnittstelle.py),
baut den Kontext des Orts aus Dateien (kontext.py), fragt Claude ohne Werkzeuge und schreibt
data/antworten/<id>.json. Startet nie einen Auftrag und handelt nie nach außen. Plan: plan.md.
Aufruf: AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python agent.py [--aufraeumen]
"""

import copy
import json
import sys
from pathlib import Path

import chatverlauf
import kontext
import schnittstelle
from agentkit import claude_lauf, config, einstellungen, log, meldungen, verbrauch

AGENT = "chat"
HIER = Path(__file__).resolve().parent
DATEN = HIER / "data"
logger = log.hole_logger(HIER, AGENT)
# Sitzungen, die claude -p selbst ablegt (Ordnername = Arbeitsordner mit - statt /). Werden gleich gelöscht,
# der Verlauf steht nur in data/verlauf.jsonl (30 Tage).
SITZUNGEN = Path.home() / ".claude" / "projects" / str(HIER).replace("/", "-")

TEXTE = {
    "limit": "Gerade ist die Rechenzeit aufgebraucht. Frag bitte ab {zeit} noch einmal.",
    "belegt": "Gerade arbeiten mehrere Aufträge gleichzeitig. Frag bitte in ein paar Minuten noch einmal.",
    "zeit": "Die Antwort hat zu lange gedauert. Versuch es bitte noch einmal, gern etwas kürzer gefragt.",
    "technik": "Das hat leider nicht geklappt. Jan ist informiert und kümmert sich.",
}


def jan_melden(text: str) -> None:
    """Meldung in Jans Instanz (seine Zentrale), nicht in Lias."""
    meldungen.melden(AGENT, f"Lia, Agent chat: {text}", basis=config.KONTINGENT_DIR / "meldungen")


def lauf_einstellungen(gruendlich: bool, cfg: dict | None = None) -> dict:
    """Einstellungen für einen Chat-Lauf: ohne Werkzeuge (--tools ""), wenige Schritte, kurze Zeit- und Wartegrenzen."""
    cfg = copy.deepcopy(cfg or einstellungen.lade())
    cfg["werkzeuge"][AGENT] = [""]
    cfg["lauf"].update(max_schritte=3, max_minuten=5 if gruendlich else 2, warten_minuten=1)
    return cfg


def claude_fragen(prompt: str, gruendlich: bool, frage_id: str) -> claude_lauf.Ergebnis:
    return claude_lauf.laufen(AGENT, HIER, prompt, art="anspruchsvoll" if gruendlich else "routine",
                              auftrag_id=f"chat-{frage_id}", cfg=lauf_einstellungen(gruendlich))


def sitzung_loeschen(sitzung: str | None, ordner: Path = SITZUNGEN) -> None:
    if sitzung:
        (ordner / f"{Path(sitzung).name}.jsonl").unlink(missing_ok=True)


def antwort(frage: dict, text: str, ok: bool, fehler: str | None = None, wieder_frei: str | None = None) -> dict:
    ort = frage.get("ort") or {}
    return {"id": frage["id"], "zeit": chatverlauf.jetzt().isoformat(timespec="seconds"), "ok": ok, "text": text,
            "gruendlich": frage.get("gruendlich", False), "reihe": ort.get("reihe"), "chip": ort.get("chip"),
            "fehler": fehler, "wieder_frei": wieder_frei}


def beantworten(frage: dict, instanz: Path, ordner: Path = DATEN, fragen=claude_fragen, melden=jan_melden,
                loeschen=sitzung_loeschen) -> dict:
    """Eine geprüfte Frage beantworten. Gibt die Antwort zurück (auch bei Fehlern, mit Satz für Lia)."""
    ort = frage["ort"]
    try:
        reihe = kontext.reihe_finden(kontext.reihen_laden(instanz), ort["reihe"]) if ort else None
    except (OSError, ValueError) as f:  # kaputte reihen.toml: ohne Reihe antworten, Jan Bescheid geben
        logger.warning("Reihen nicht lesbar: %s", f)
        melden(f"reihen.toml nicht lesbar, Chat antwortet ohne Reihe: {f}")
        reihe = None
    verlauf = chatverlauf.am_ort(chatverlauf.lesen(ordner), ort["reihe"] if ort else None)
    prompt = kontext.prompt(frage["text"], kontext.kontext_text(ort, reihe), verlauf, frage["gruendlich"])
    try:
        e = fragen(prompt, frage["gruendlich"], frage["id"])
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
    logger.info("Frage %s: %d Zeichen, Ort %s, %s, ok %s, %.1f s, %.3f USD", frage["id"], len(frage["text"]),
                "ja" if ort else "nein", "gründlich" if frage["gruendlich"] else "schnell", e.ok, e.dauer_s, e.usd)
    if not e.ok or not e.text.strip():
        melden(f"Frage {frage['id']}: claude ohne brauchbare Antwort ({e.schritte} Schritte)")
        return antwort(frage, TEXTE["technik"], False, "technik")
    a = antwort(frage, e.text.strip(), True)
    chatverlauf.anhaengen(ordner, {"id": frage["id"], "zeit": a["zeit"], "reihe": a["reihe"], "chip": a["chip"],
                                   "gruendlich": a["gruendlich"], "frage": frage["text"], "antwort": a["text"]})
    return a


def frage_lesen(pfad: Path) -> dict:
    """Frage-Datei lesen und prüfen. Ungültig: FrageFehler mit einer id, soweit erkennbar."""
    try:
        roh = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as f:
        raise schnittstelle.FrageFehler(f"Frage-Datei nicht lesbar: {f}") from None
    return schnittstelle.frage_pruefen(roh)


def fragen_abarbeiten(instanz: Path = config.SHARED_DIR, ordner: Path = DATEN, **kw) -> int:
    """Alle wartenden Fragen der Reihe nach (älteste zuerst), auch solche, die währenddessen dazukommen."""
    chatverlauf.aufraeumen(ordner)
    gesehen, anzahl = set(), 0
    while neue := sorted((p for p in (ordner / "fragen").glob("*.json") if p.name not in gesehen),
                         key=lambda p: p.stat().st_mtime):
        for pfad in neue:
            gesehen.add(pfad.name)
            try:
                frage = frage_lesen(pfad)
            except schnittstelle.FrageFehler as f:
                logger.warning("%s: %s", pfad.name, f)
                if schnittstelle.ID_MUSTER.match(pfad.stem):
                    schnittstelle.antwort_schreiben(antwort({"id": pfad.stem}, str(f), False, "ungueltig"), ordner)
                pfad.unlink(missing_ok=True)
                continue
            schnittstelle.antwort_schreiben(beantworten(frage, instanz, ordner, **kw), ordner)
            pfad.unlink(missing_ok=True)
            anzahl += 1
    return anzahl


def aufraeumen(ordner: Path = DATEN, sitzungen: Path = SITZUNGEN) -> None:
    """Täglich (lia-chat-aufraeumen.timer): alter Verlauf, alte Antworten, liegengebliebene claude-Sitzungen."""
    weg = chatverlauf.aufraeumen(ordner)
    for p in sitzungen.glob("*.jsonl") if sitzungen.exists() else []:
        p.unlink()
        weg += 1
    logger.info("Aufräumen: %d gelöscht", weg)


if __name__ == "__main__":
    if "--aufraeumen" in sys.argv[1:]:
        aufraeumen()
    else:
        fragen_abarbeiten()
