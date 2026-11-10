"""Gespräche beantworten (Teil des Agenten chat, gestartet aus agent.py für Einträge mit "art" in data/fragen/).

Eine Nachricht setzt die claude-Sitzung des Gesprächs fort (claude_lauf lernsitzung/sitzung_fortsetzen, Jan
09.11.2026). Jeder Gesprächslauf läuft mit claude_lauf lese_ordner = Ordner dieses Gesprächs (data/gespraeche/<id>/):
Claude darf nur dort lesen (Fotos über Read), und weil claude Sitzungen je Arbeitsordner führt (lese_ordner läuft
in data/nur_lesen/), muss jeder Lauf eines Gesprächs dieselbe Art haben, sonst ginge Fortsetzen nicht. Fotos aus
Lias Ablage am Ort werden dafür in den Gesprächsordner kopiert (ablage/<ort-id>/). Sonderläufe „bisher“ und „auftrag“ laufen ohne
Sitzung über den Verlauf als Text, ihre Antwort kommt nicht ins Gespräch.
"""

import copy
import logging
import re
import shutil
import time
from pathlib import Path

import gespraechablage as ga
import kontext
import schnittstelle
from agentkit import claude_lauf, einstellungen, struktur, textfassung, verbrauch

AGENT = "chat"
HIER = Path(__file__).resolve().parent
logger = logging.getLogger(AGENT)

# Sitzungen der Gespräche: claude legt sie je Arbeitsordner ab (Name = Pfad, Sonderzeichen als -)
GESPRAECH_SITZUNGEN = (Path.home() / ".claude" / "projects" /
                       re.sub(r"[^A-Za-z0-9]", "-", str(HIER / claude_lauf.NUR_LESEN_CWD)))
TEXT_ENDUNGEN = (".pdf", ".docx", ".pptx")
FOTO_ENDUNGEN = schnittstelle.FOTO_ENDUNGEN
ABLAGE_FOTOS = 5  # je Lauf höchstens so viele Fotos aus der Ablage (die jüngsten)
PROMPT_BYTES = 120_000  # claude -p nimmt höchstens 128 KB je Argument
DATEI_ZEICHEN = 60_000  # Text aus Dateien einer Nachricht zusammen
ABLAGE_ZEICHEN = 40_000  # Text aus der Ablage je Lauf zusammen

TEXTE = {
    "limit": "Gerade ist die Rechenzeit aufgebraucht. Schreib bitte ab {zeit} noch einmal.",
    "belegt": "Gerade arbeiten mehrere Aufträge gleichzeitig. Schick die Nachricht bitte in ein paar Minuten noch "
              "einmal.",
    "zeit": "Die Antwort hat zu lange gedauert. Versuch es bitte noch einmal, gern in kleineren Schritten.",
    "technik": "Das hat leider nicht geklappt. Jan ist informiert und kümmert sich.",
    "weg": "Dieses Gespräch gibt es nicht mehr.",
}


def netz_moeglich() -> bool:
    """Erlaubt agentkit WebSearch zusammen mit lese_ordner? (Bedarf an agentkit vom 10.11.2026; bis dahin bleibt
    Lias Häkchen „Im Netz nachsehen“ in Gesprächen ohne Wirkung.)"""
    try:
        regeln = claude_lauf.rechte(["WebSearch", "Read"], None, [Path("/x")])["permissions"]["allow"]
    except TypeError:
        return False
    return "WebSearch" in regeln


def lauf_einstellungen(gruendlich: bool, netz: bool, fotos: int, cfg: dict | None = None,
                       sonder: bool = False) -> dict:
    """Werkzeuge und Grenzen für einen Gesprächslauf. Read nur mit Fotos, WebSearch/WebFetch nur mit netz."""
    cfg = copy.deepcopy(cfg or einstellungen.lade())
    werkzeuge = []
    if netz and not sonder:
        domains = cfg.get("webfetch", {}).get("recherche")
        werkzeuge += ["WebSearch", "WebFetch"] if domains else ["WebSearch"]
        if domains:
            cfg.setdefault("webfetch", {})[AGENT] = list(domains)
    if fotos and not sonder:
        werkzeuge.append("Read")
    cfg["werkzeuge"][AGENT] = werkzeuge or [""]
    schritte = 3 + (fotos if not sonder else 0) + (8 if netz and not sonder else 0)
    minuten = (8 if gruendlich else 4) + (2 if netz and not sonder else 0)
    cfg["lauf"].update(max_schritte=schritte, max_minuten=minuten, warten_minuten=1)
    return cfg


def claude_gespraech(prompt: str, *, gruendlich: bool, kennung: str, netz: bool = False,
                     lese_ordner: Path | None = None, fotos: int = 0, sitzung: str | None = None,
                     neu: bool = True, sonder: bool = False) -> claude_lauf.Ergebnis:
    cfg = lauf_einstellungen(gruendlich, netz, fotos, sonder=sonder)
    zusatz = {} if sonder else {"lese_ordner": [lese_ordner]}
    if not sonder:
        lese_ordner.mkdir(parents=True, exist_ok=True)
    return claude_lauf.laufen(AGENT, HIER, prompt, art="anspruchsvoll" if gruendlich else "routine",
                              lernsitzung=neu and not sonder, sitzung_fortsetzen=None if neu else sitzung,
                              auftrag_id=f"chat-{kennung}", cfg=cfg, **zusatz)


# --- Text und Fotos ------------------------------------------------------------------------------------------------

def text_aus(pfad: Path, je_datei: int) -> str:
    """Text einer Datei für den Prompt, mit Satz statt Text bei Scan, Excel oder kaputter Datei."""
    if pfad.suffix.lower() == ".xlsx":
        return "(Excel-Dateien kann ich im Gespräch noch nicht lesen.)"
    try:
        text = (textfassung.als_text(pfad) or "").strip()
    except Exception as f:  # kaputte oder verschlüsselte Datei: Claude bekommt den Hinweis
        logger.warning("Datei nicht lesbar: %s", type(f).__name__)
        return "(Die Datei ließ sich nicht lesen.)"
    if text.startswith("(Kein Text gefunden"):
        return "(Kein Text gefunden, vermutlich ein Scan. Als Foto (JPG/PNG) kann ich ihn ansehen.)"
    return (text[:je_datei] + "\n[… gekürzt]") if len(text) > je_datei else (text or "(leer)")


def dateien_text(pfade: list[Path], gesamt: int = DATEI_ZEICHEN, titel: str = "Datei") -> str:
    je = gesamt // max(len(pfade), 1)
    return "\n\n".join(f"--- {titel}: {p.name}\n{text_aus(p, je)}" for p in pfade)


def signatur(ort_id: str, p: Path) -> str:
    st = p.stat()
    return f"{ort_id}/{p.name}:{st.st_size}:{int(st.st_mtime)}"


def ablage_sammeln(ids: list[str], ablage: Path, gordner: Path, gesendet: list[str]) -> tuple[str, list[Path], list[str]]:
    """Dateien aus <ablage>/<id>/ (Ebene und darüber), die Claude in diesem Gespräch noch nicht bekommen hat.

    Text über textfassung (zusammen höchstens ABLAGE_ZEICHEN), Fotos werden nach <gordner>/ablage/<id>/ kopiert
    (Read darf nur dort lesen), höchstens ABLAGE_FOTOS, die jüngsten. Gibt (Text, Fotopfade, neue Signaturen).
    """
    texte, fotos, neu = [], [], []
    for oid in ids:
        ordner = ablage / oid
        if not ordner.is_dir():
            continue
        for p in sorted(ordner.iterdir()):
            if not p.is_file() or p.name.startswith(".") or p.is_symlink():
                continue
            endung = p.suffix.lower()
            if endung not in TEXT_ENDUNGEN + FOTO_ENDUNGEN + (".xlsx",):
                continue
            sig = signatur(oid, p)
            if sig in gesendet:
                continue
            (fotos if endung in FOTO_ENDUNGEN else texte).append((oid, p, sig))
    fotos = sorted(fotos, key=lambda t: t[1].stat().st_mtime, reverse=True)[:ABLAGE_FOTOS]
    kopien = []
    for oid, p, sig in fotos:
        ziel = gordner / "ablage" / oid / p.name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, ziel)
        kopien.append(ziel)
        neu.append(sig)
    text = dateien_text([p for _, p, _ in texte], ABLAGE_ZEICHEN, "Abgelegt") if texte else ""
    neu += [sig for _, _, sig in texte]
    if kopien:
        text += ("\n\n" if text else "") + "Abgelegte Fotos (mit Read öffnen, wenn sie für die Nachricht wichtig " \
                                           "sind):\n" + "\n".join(str(k) for k in kopien)
    return text, kopien, neu


def kuerzen(text: str, max_bytes: int) -> str:
    """Text auf höchstens max_bytes (UTF-8), mit Hinweis."""
    if len(text.encode()) <= max_bytes:
        return text
    roh = text.encode()[:max(max_bytes - 40, 0)].decode(errors="ignore")
    return roh + "\n[… gekürzt]"


# --- Abläufe -------------------------------------------------------------------------------------------------------

def _antwort(job: dict, ok: bool, text: str, fehler: str | None = None, wieder_frei: str | None = None,
             chip: str = "", gruendlich: bool = False, netz: bool = False) -> dict:
    return {"id": job["id"], "gespraech": job.get("gespraech"), "art": job.get("art"),
            "zeit": ga.zeit_text(), "ok": ok, "text": text, "fehler": fehler, "wieder_frei": wieder_frei,
            "chip": chip, "gruendlich": gruendlich, "netz": netz}


def _rufen(lauf, kennung: str, melden) -> tuple[claude_lauf.Ergebnis | None, str | None, str | None]:
    """lauf() ausführen. Gibt (Ergebnis, None, None) oder (None, Fehlerart, wieder_frei)."""
    try:
        e = lauf()
    except claude_lauf.LimitErreicht as f:
        logger.warning("%s: %s", kennung, f)
        return None, "limit", verbrauch.zeit_text(f.reset)
    except (claude_lauf.KeinPlatz, claude_lauf.LaeuftSchon) as f:
        logger.warning("%s: %s", kennung, f)
        return None, "belegt", None
    except claude_lauf.Zeitueberschreitung as f:
        logger.warning("%s: %s", kennung, f)
        return None, "zeit", None
    except Exception as f:  # jeder andere Abbruch: Lia bekommt einen Satz, Jan die Ursache
        logger.exception("%s fehlgeschlagen", kennung)
        melden(f"Gespräch, Nachricht {kennung} fehlgeschlagen: {type(f).__name__}: {f}")
        return None, "technik", None
    if not e.ok or not e.text.strip():
        return e, "leer", None
    return e, None, None


def _struktur(instanz: Path, melden):
    try:
        return struktur.laden(instanz)
    except (OSError, struktur.StrukturFehler) as f:
        logger.warning("Reihen nicht lesbar: %s", f)
        melden(f"reihen.toml nicht lesbar, Gespräch ohne Ort-Angaben: {f}")
        return None


def sitzung_da(sitzung: str | None, sitzungen: Path) -> bool:
    return bool(sitzung) and (sitzungen / f"{Path(sitzung).name}.jsonl").exists()


def _fehler_eintragen(gid: str, nid: str, art: str, daten: Path) -> None:
    with ga.sperre(daten):
        g = ga.lesen(gid, daten)
        if g is None:
            return
        for e in g["eintraege"]:
            if e["id"] == nid and e["rolle"] == "lia":
                e.update(stand="fehler", fehler=art)
        ga.schreiben(g, daten)


def nachricht_beantworten(job: dict, instanz: Path, daten: Path, sitzungen: Path, claude=claude_gespraech,
                          melden=print, sitzung_loeschen=None, netz_an=netz_moeglich) -> dict:
    """Lias Nachricht job["id"] im Gespräch job["gespraech"] beantworten. Gibt die Antwort (auch bei Fehlern)."""
    gid, nid = job["gespraech"], job["id"]
    g = ga.lesen(gid, daten)
    eintrag = next((e for e in (g or {}).get("eintraege", []) if e["id"] == nid and e["rolle"] == "lia"), None)
    if g is None or eintrag is None or eintrag.get("stand") != "wartet":
        return _antwort(job, False, TEXTE["weg"], "ungueltig")
    gruendlich, netz = eintrag["gruendlich"], eintrag["netz"] and netz_an()
    s = _struktur(instanz, melden)
    chip, ort_text = kontext.ort_kontext(g.get("ort"), s)
    gordner = ga.dateien_ordner(gid, daten)
    davor = [e for e in g["eintraege"] if e is not eintrag]
    erste = not sitzung_da(g.get("sitzung"), sitzungen)
    gesendet = [] if erste else list(g.get("kontext", {}).get("ablage", []))
    ablage, ablage_fotos, ablage_neu = ablage_sammeln(kontext.ablage_ids(g.get("ort"), s), instanz / "ablage",
                                                      gordner, gesendet)
    fotos = [gordner / nid / n for n in eintrag["fotos"]]
    dtext = dateien_text([gordner / nid / n for n in eintrag["dateien"]]) if eintrag["dateien"] else ""
    vorher_netz = any(e.get("netz") for e in davor if e.get("rolle") == "lia")

    def prompt_bauen(erste_: bool) -> str:
        verlauf = kontext.verlauf_text(davor) if erste_ and davor else ""
        teile = dict(ablage=ablage, dateien=dtext, verlauf=verlauf)
        ort_neu = not erste_ and ort_text != g.get("kontext", {}).get("ort")
        ohne = len(kontext.gespraech_prompt(eintrag["text"], erste=erste_, gruendlich=gruendlich, netz=netz,
                                            vorher_netz=vorher_netz, ort_text=ort_text, ort_neu=ort_neu,
                                            fotos=[str(p) for p in fotos]).encode()) + 200
        rest = PROMPT_BYTES - ohne
        for k in ("verlauf", "ablage", "dateien"):  # zuerst Verlauf, dann Ablage, dann Dateien kürzen
            andere = sum(len(v.encode()) for kk, v in teile.items() if kk != k)
            if andere + len(teile[k].encode()) > rest:
                teile[k] = kuerzen(teile[k], max(rest - andere, 0))
        return kontext.gespraech_prompt(eintrag["text"], erste=erste_, gruendlich=gruendlich, netz=netz,
                                        vorher_netz=vorher_netz, ort_text=ort_text,
                                        ort_neu=ort_neu,
                                        ablage=teile["ablage"], dateien=teile["dateien"],
                                        fotos=[str(p) for p in fotos], verlauf=teile["verlauf"])

    alle_fotos = len(fotos) + len(ablage_fotos)

    def lauf(erste_: bool):
        return claude(prompt_bauen(erste_), gruendlich=gruendlich, kennung=nid, netz=netz, lese_ordner=gordner,
                      fotos=alle_fotos, sitzung=g.get("sitzung"), neu=erste_)

    e, fehler, frei = _rufen(lambda: lauf(erste), nid, melden)
    if fehler == "leer" and not erste:  # Fortsetzen ging schief: einmal neu mit dem Verlauf als Text
        logger.warning("Nachricht %s: Fortsetzen ohne Antwort, neue Sitzung", nid)
        erste = True
        e, fehler, frei = _rufen(lambda: lauf(True), nid, melden)
    if fehler == "leer":
        melden(f"Gespräch, Nachricht {nid}: claude ohne brauchbare Antwort ({e.schritte} Schritte)")
        fehler = "technik"
    if fehler:
        _fehler_eintragen(gid, nid, fehler, daten)
        text = TEXTE[fehler].format(zeit=frei) if fehler == "limit" else TEXTE[fehler]
        return _antwort(job, False, text, fehler, frei, chip, gruendlich, netz)
    logger.info("Nachricht %s: %d Zeichen, Ort %s, %s, Netz %s, %d Fotos, %d Dateien, Ablage %d neu, %s, "
                "%d Schritte, %.1f s, %.3f USD", nid, len(eintrag["text"]), g["ort"]["ebene"] if g.get("ort") else
                "ohne", "gründlich" if gruendlich else "schnell", "ja" if netz else "nein", len(fotos),
                len(eintrag["dateien"]), len(ablage_neu), "neu" if erste else "fortgesetzt", e.schritte,
                e.dauer_s, e.usd)
    if e.verweigert:
        logger.info("Nachricht %s: %d Werkzeug-Aufrufe abgelehnt", nid, len(e.verweigert))
    a = _antwort(job, True, e.text.strip(), chip=chip, gruendlich=gruendlich, netz=netz)
    with ga.sperre(daten):
        g = ga.lesen(gid, daten)
        if g is None:  # während des Laufs gelöscht: neue Sitzung gleich mit weg
            if sitzung_loeschen:
                sitzung_loeschen(e.sitzung)
            return _antwort(job, False, TEXTE["weg"], "ungueltig")
        for x in g["eintraege"]:
            if x["id"] == nid and x["rolle"] == "lia":
                x.update(stand="fertig", fehler=None)
        g["eintraege"].append({"id": nid, "rolle": "claude", "zeit": a["zeit"], "text": a["text"],
                               "gruendlich": gruendlich, "netz": netz})
        g["sitzung"] = e.sitzung
        g["kontext"] = {"ort": ort_text, "ablage": gesendet + ablage_neu}
        g["zuletzt"] = a["zeit"]
        ga.schreiben(g, daten)
    return a


def sonder_beantworten(job: dict, instanz: Path, daten: Path, claude=claude_gespraech, melden=print,
                       sitzung_loeschen=None) -> dict:
    """„bisher“ oder „auftrag“: ein Lauf ohne Werkzeuge und ohne Sitzung über den Verlauf als Text."""
    g = ga.lesen(job["gespraech"], daten)
    if g is None:
        return _antwort(job, False, TEXTE["weg"], "ungueltig")
    chip, ort_text = kontext.ort_kontext(g.get("ort"), _struktur(instanz, melden))
    prompt = kontext.sonder_prompt(job["art"], kontext.verlauf_text(g["eintraege"]), ort_text)
    prompt = kuerzen(prompt, PROMPT_BYTES)
    e, fehler, frei = _rufen(lambda: claude(prompt, gruendlich=False, kennung=job["id"], sonder=True),
                             job["id"], melden)
    if e is not None and sitzung_loeschen:
        sitzung_loeschen(e.sitzung)  # eigene Sitzung des Sonderlaufs gehört zu keinem Gespräch
    if fehler == "leer":
        melden(f"Gespräch, Sonderlauf {job['id']}: claude ohne brauchbare Antwort")
        fehler = "technik"
    if fehler:
        text = TEXTE[fehler].format(zeit=frei) if fehler == "limit" else TEXTE[fehler]
        return _antwort(job, False, text, fehler, frei, chip)
    logger.info("Sonderlauf %s (%s): %d Einträge, %d Schritte, %.1f s, %.3f USD", job["id"], job["art"],
                len(g["eintraege"]), e.schritte, e.dauer_s, e.usd)
    return _antwort(job, True, e.text.strip(), chip=chip)


def aufraeumen(daten: Path, sitzungen: list[Path], heute=None) -> int:
    """Gespräche 30 Tage nach der letzten Nachricht samt Dateien und Sitzung löschen; claude-Sitzungen, die zu
    keinem Gespräch gehören und älter als eine Stunde sind, auch. Gibt die Zahl gelöschter Dinge zurück."""
    weg = 0
    with ga.sperre(daten):
        for g in ga.alle(daten):
            if ga.alt(g, heute=heute):
                ga.loeschen(g["id"], daten)
                weg += 1
        behalten = {Path(g["sitzung"]).name for g in ga.alle(daten) if g.get("sitzung")}
    for p in {p for o in sitzungen if o.exists() for p in o.glob("*.jsonl")}:
        try:
            if p.stem not in behalten and time.time() - p.stat().st_mtime > 3600:
                p.unlink()
                shutil.rmtree(p.with_suffix(""), ignore_errors=True)  # Ordner gleichen Namens (Webabrufe)
                weg += 1
        except FileNotFoundError:
            continue
    return weg
