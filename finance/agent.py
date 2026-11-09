"""Agent finance: Recherche zur Wirtschaftlichkeit eines Themas (Auftrag per /finance <Thema>).

Ein Lauf: 1. freigegebene Entwürfe ausführen, 2. Aufträge abarbeiten (je Auftrag eine Recherche in fünf
Schritten, siehe ablauf.py und schritte.py). Claude denkt (ein Lauf je Schritt), Python lädt Webquellen,
legt sie ab (quellen.py) und prüft jede Zahl (pruefung.py).
"""

import tempfile
import tomllib
from datetime import date
from pathlib import Path

from agentkit import abruf, auftraege, claude_lauf, config, freigabe, log, textfassung, wortlaut

import renderer

import ablauf
import abrufer
import bericht
import quellen

AGENT = "finance"
HIER = Path(__file__).resolve().parent
QUELLEN = HIER / "data" / "quellen"
RECHERCHEN = HIER / "data" / "recherchen"
CACHE = HIER / "data" / "cache"
PROFIL = HIER / "profil-bericht.toml"
logger = log.hole_logger(HIER, AGENT)
log.hole_logger(HIER, "renderer")  # Warnungen des Renderers (z. B. Vorschau) ins selbe Log-Verzeichnis
cfg = config.lade_config(HIER)


def ausfuehren(entwurf: dict) -> str:
    """Hier handelt der Python-Code nach Jans Freigabe. finance legt noch keine Entwürfe an."""
    raise NotImplementedError(entwurf["typ"])


def freigegebene_ausfuehren() -> None:
    for e in freigabe.zur_ausfuehrung(AGENT):
        try:
            freigabe.ausfuehrung_beginnen(e["id"], kauf_limit_euro=cfg.get("KAUF_LIMIT_EURO"))
        except freigabe.FreigabeFehler as f:
            logger.warning("Nicht ausgeführt: %s", f)
            continue
        try:
            ergebnis = ausfuehren(e)
            freigabe.ausfuehrung_abschliessen(e["id"], ergebnis, erfolgreich=True)
        except Exception as f:  # noqa: BLE001 – jeder Fehler wird Jan gemeldet
            logger.exception("Ausführung %s fehlgeschlagen", e["id"])
            freigabe.ausfuehrung_abschliessen(e["id"], f"Fehler: {f}", erfolgreich=False)


def web_laden(url: str, _laden=abruf.laden) -> ablauf.Web:
    """Webquelle holen (nur GET, Cache in data/cache). HTML als Text, PDF über agentkit.textfassung."""
    try:
        erg = _laden(url, allowlist=[ablauf.host(url)], cache_dir=CACHE)
    except abruf.AbrufFehler as f:
        raise ablauf.WebFehler(str(f)) from f
    art = (erg.meta.get("content_type") or "").lower()
    try:
        if "pdf" in art or url.lower().endswith(".pdf"):
            with tempfile.TemporaryDirectory() as tmp:
                pfad = Path(tmp) / "quelle.pdf"
                pfad.write_bytes(erg.inhalt)
                try:
                    text = textfassung.als_text(pfad)
                except ImportError as f:
                    raise ablauf.WebFehler("PDF kann finance noch nicht lesen (Paket pypdf fehlt)") from f
            if not text:
                raise ablauf.WebFehler("PDF ohne lesbaren Text")
            return ablauf.Web(erg.inhalt, text, "pdf")
        if "html" in art:
            return ablauf.Web(erg.inhalt, erg.text_ohne_html(), "html")
        return ablauf.Web(erg.inhalt, erg.text(), "txt")
    except abruf.AbrufFehler as f:
        raise ablauf.WebFehler(str(f)) from f


def abrufen(abfrage: dict, _laden=abruf.laden) -> str:
    """Eine Abfrage von Claude ausführen und ablegen: Quellen-ID oder AbfrageFehler/WebFehler (Text für Claude)."""
    anfrage = abrufer.anfrage_bauen(abfrage, cfg)
    try:
        erg = _laden(anfrage.url, allowlist=anfrage.allowlist, cache_dir=CACHE, methode=anfrage.methode,
                     daten=anfrage.daten, header=anfrage.header, neu=True)  # Primärdaten immer frisch
    except abruf.AbrufFehler as f:
        raise ablauf.WebFehler(str(f)) from f
    roh, endung = abrufer.antwort_pruefen(anfrage.art, erg.inhalt, erg.meta.get("content_type"))
    qid = quellen.speichern(QUELLEN, anfrage.art, anfrage.quelle_url, roh, anfrage.beschreibung, endung=endung)
    logger.info("Primärdaten %s: %s", qid, anfrage.beschreibung)
    return qid


def dokumente(thema: str, ergebnisse: list, ordner: Path, _bauen=renderer.bauen) -> tuple[list[Path], list[str]]:
    """Bericht (PDF, sonst docx) und Modell (xlsx) im Recherche-Ordner. (Dateien, Fehler für Jan)."""
    daten, abbruch = bericht.aus_ergebnissen(ergebnisse)
    metas = {m["id"]: m for m in quellen.alle(QUELLEN)}
    profil = tomllib.loads(PROFIL.read_text(encoding="utf-8"))
    dateien, fehler = [], []
    auftraege_ = [("Bericht", bericht.beschreibung(thema, daten, metas, date.today(), abbruch), "bericht.docx", True),
                  ("Modell", bericht.modell(thema, daten), "modell.xlsx", False)]
    for name, beschreibung, datei, vorschau in auftraege_:
        if beschreibung is None:
            continue
        try:
            erg = _bauen(beschreibung, ordner / datei, profil=profil, vorschau=vorschau)
        except (renderer.BeschreibungUngueltig, ValueError) as f:  # Fehler im finance-Code, nicht bei Claude
            logger.error("%s nicht gebaut: %s", name, f)
            fehler.append(f"{name} nicht gebaut: {str(f)[:300]}")
            continue
        dateien.append(Path(erg.pdf) if getattr(erg, "pdf", None) else Path(erg.pfad))
        fehler += [f"{name}: {h}" for h in getattr(erg, "hinweise", None) or []]
    return dateien, fehler


def recherche_abarbeiten(a: dict, laufen=claude_lauf.laufen, laden=web_laden, abfragen=abrufen) -> None:
    """Eine Recherche. LimitErreicht, KeinPlatz, LaeuftSchon gehen durch (Auftrag wartet)."""
    ordner = RECHERCHEN / a["id"]
    thema = a["text"].strip()

    def lauf(prompt: str):
        return laufen(AGENT, HIER, prompt, art="anspruchsvoll", auftrag_id=a["id"])

    ergebnisse = ablauf.recherche(thema, HIER, ordner, QUELLEN, lauf, laden, wortlaut.steht_in, date.today(),
                                  abrufen=abfragen)
    text = ablauf.bericht_text(thema, ergebnisse, str(ordner.relative_to(HIER)))
    dateien, fehler = dokumente(thema, ergebnisse, ordner)
    if fehler:
        text += "\n" + "\n".join(f"- {f}" for f in fehler)
    ok = ergebnisse[-1].ok
    logger.info("Recherche %s: %s", a["id"], "fertig" if ok else "abgebrochen")
    auftraege.abschliessen(a["id"], text, status="erledigt" if ok else "fehlgeschlagen", dateien=dateien)


def auftraege_abarbeiten(laufen=claude_lauf.laufen, laden=web_laden) -> None:
    for a in auftraege.neue(AGENT):
        try:
            recherche_abarbeiten(a, laufen, laden)
        except (claude_lauf.LimitErreicht, claude_lauf.KeinPlatz, claude_lauf.LaeuftSchon) as f:
            logger.info("Auftrag %s wartet: %s", a["id"], f)  # bleibt in neu/, fertige Schritte bleiben liegen
            return
        except claude_lauf.LaufFehler as f:
            logger.warning("Auftrag %s fehlgeschlagen: %s", a["id"], f)
            auftraege.abschliessen(a["id"], f"Fehler: {f}", status="fehlgeschlagen")


if __name__ == "__main__":
    freigegebene_ausfuehren()
    auftraege_abarbeiten()
