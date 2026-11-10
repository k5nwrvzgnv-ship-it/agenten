"""Agent schnell in Lias Instanz (AGENTKIT_INSTANZ=lia/instanz), Einstieg des Dienstes lia-schnell.

Der schnelle Weg neben dem gründlichen (docs/schnell-dokument-plan.md): ein claude-Lauf (Sonnet, ohne Werkzeuge),
dann der Renderer. Liest data/wuensche/<id>.json (schnittstelle.py) und schreibt data/antworten/<id>.json.
- aenderung: Beschreibung des Dokuments finden, Claude ändert sie (oder sagt „zu groß“), Python prüft und baut,
  die neue Datei kommt als eigene Fassung in dieselbe Kette (agentkit.fassungen). Zu groß: gründliche
  Nachbesserung an unterricht bzw. theater (auftraege.weitergeben).
- dokument: Claude wählt Arbeitsblatt, Folien oder Arbeitsmappe; das Ergebnis ist ein erledigter Auftrag des
  Agenten schnell mit dem Hinweis „schnell erstellt, ohne Quellenprüfung“.
Danach geht der Wunsch zum Lernen an den Feedback-Dienst (nur lernen), sobald [weitergabe] schnell das erlaubt.
Aufruf: AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python agent.py
"""

import copy
import json
import re
import shutil
import subprocess
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import logik
import renderer
import schnittstelle
from agentkit import auftraege, claude_lauf, config, einstellungen, fassungen, log, meldungen, regeln, struktur
from agentkit import textfassung, verbrauch

AGENT = "schnell"
HIER = Path(__file__).resolve().parent
DATEN = HIER / "data"
INSTANZ = config.SHARED_DIR
GRUENDLICH = ("unterricht", "theater")  # Agenten, deren Dokumente schnell geändert werden und die Großes bekommen
FORMAT = Path(renderer.__file__).resolve().parent / "FORMAT.md"
UNIT_DIR = Path.home() / ".config" / "systemd" / "user"
SITZUNGEN = [Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(p))
             for p in (HIER, HIER / claude_lauf.NUR_LESEN_CWD)]
AUFBEWAHREN_TAGE = 30  # Antworten
DATEI_ZEICHEN = 60_000  # Text aus Lias Dateien je Wunsch
logger = log.hole_logger(HIER, AGENT)

TEXTE = {
    "limit": "Gerade ist die Rechenzeit aufgebraucht. Versuch es bitte ab {zeit} noch einmal.",
    "belegt": "Gerade arbeiten mehrere Aufträge gleichzeitig. Versuch es bitte in ein paar Minuten noch einmal.",
    "zeit": "Das hat zu lange gedauert. Versuch es bitte noch einmal.",
    "technik": "Das hat leider nicht geklappt. Jan ist informiert und kümmert sich.",
    "ungueltig": "Dieses Dokument finde ich nicht mehr.",
    "gruendlich": "Das ist eine größere Änderung. Sie läuft jetzt gründlich und dauert länger.",
    "zu_gross": "Das ist für eine schnelle Änderung zu groß. Leg dafür bitte unter „Neu“ einen Auftrag an.",
    "geaendert": "Geändert.",
}


class Abbruch(Exception):
    """Wunsch endet mit einer Antwort für Lia (fehler, text)."""

    def __init__(self, fehler: str, text: str, wieder_frei: str | None = None):
        super().__init__(fehler)
        self.fehler, self.text, self.wieder_frei = fehler, text, wieder_frei


def jan_melden(text: str) -> None:
    """Meldung in Jans Instanz (seine Zentrale), nicht in Lias."""
    meldungen.melden(AGENT, f"Lia, Agent schnell: {text}", basis=config.KONTINGENT_DIR / "meldungen")


def lauf_einstellungen(cfg: dict | None = None, fotos: bool = False) -> dict:
    """Ohne Werkzeuge (--tools ""), mit Fotos nur Read im Fotoordner (lese_ordner); kurze Grenzen."""
    cfg = copy.deepcopy(cfg or einstellungen.lade())
    cfg["werkzeuge"][AGENT] = [""]
    cfg["lauf"].update(max_schritte=8 if fotos else 3, max_minuten=4, warten_minuten=1)
    return cfg


def claude_laufen(prompt: str, lauf_id: str, sitzung: str | None = None,
                  lese_ordner: list[Path] | None = None) -> claude_lauf.Ergebnis:
    return claude_lauf.laufen(AGENT, HIER, prompt, art="routine", lernsitzung=sitzung is None,
                              sitzung_fortsetzen=sitzung, auftrag_id=lauf_id,
                              cfg=lauf_einstellungen(fotos=bool(lese_ordner)), lese_ordner=lese_ordner)


def dienst_starten(agent: str) -> None:
    """lia-<agent>.service starten (--no-block), wie die Web-App. Fehlt der Dienst: Fehler im Log."""
    dienst = f"lia-{agent}.service"
    if not (UNIT_DIR / dienst).exists():
        logger.error("Kein Dienst %s, Auftrag wartet", dienst)
        return
    lauf = subprocess.run(["systemctl", "--user", "start", "--no-block", dienst], capture_output=True, text=True,
                          check=False)
    if lauf.returncode != 0:
        logger.error("Start von %s fehlgeschlagen: %s", dienst, lauf.stderr.strip())


def sitzung_loeschen(sitzung: str | None, ordner: list[Path] = SITZUNGEN) -> None:
    if sitzung:
        for o in ordner:
            (o / f"{Path(sitzung).name}.jsonl").unlink(missing_ok=True)
            shutil.rmtree(o / Path(sitzung).name, ignore_errors=True)


@dataclass
class Umgebung:
    """Was ein Wunsch braucht; Tests ersetzen laufen, bauen, weitergeben, starten, melden und die Pfade."""
    laufen: Callable = claude_laufen
    bauen: Callable = renderer.bauen
    weitergeben: Callable = auftraege.weitergeben
    starten: Callable = dienst_starten
    melden: Callable = jan_melden
    loeschen: Callable = sitzung_loeschen
    basis: Path = INSTANZ / "auftraege"
    agenten_dir: Path = INSTANZ.parent
    daten: Path = DATEN
    cfg: dict | None = None
    laeufe: list = field(default_factory=list)

    def einstellungen(self) -> dict:
        return self.cfg if self.cfg is not None else einstellungen.lade()


def profil_laden(u: Umgebung, agent: str) -> dict:
    with open(u.agenten_dir / logik.profil_agent(agent) / "profil.toml", "rb") as f:
        return tomllib.load(f)


def format_text(arten) -> str:
    return logik.format_abschnitte(FORMAT.read_text(encoding="utf-8"), arten)


def _claude(u: Umgebung, prompt: str, lauf_id: str, sitzung: str | None = None, lese: list[Path] | None = None):
    """Ein Lauf; Fehler von claude_lauf werden zu Abbruch mit Satz für Lia."""
    try:
        e = u.laufen(prompt, lauf_id, sitzung, lese)
    except claude_lauf.LimitErreicht as f:
        zeit = verbrauch.zeit_text(f.reset)
        raise Abbruch("limit", TEXTE["limit"].format(zeit=zeit), zeit) from None
    except (claude_lauf.KeinPlatz, claude_lauf.LaeuftSchon):
        raise Abbruch("belegt", TEXTE["belegt"]) from None
    except claude_lauf.Zeitueberschreitung:
        raise Abbruch("zeit", TEXTE["zeit"]) from None
    u.laeufe.append(e)
    if not e.ok or not e.text.strip():
        raise Abbruch("technik", TEXTE["technik"])
    return e


def entwerfen(u: Umgebung, prompt: str, lauf_id: str, alt: dict | None, bauen: Callable,
              lese: list[Path] | None = None) -> tuple[dict, dict]:
    """claude-Lauf, Antwort lesen, Beschreibung bilden, bauen. Ein Fehler (Antwort, Änderung, Renderer) geht
    einmal an Claude zurück. Gibt (Antwort, neue Beschreibung) zurück; zu groß: (Antwort, {}).
    Scheitert auch die Korrektur: logik.AenderungFehler."""
    e = _claude(u, prompt, lauf_id, lese=lese)
    basis = alt
    for runde in range(2):
        geaendert = False
        try:
            a = logik.antwort_lesen(e.text)
            if a["art"] == "zu_gross":
                return a, {}
            if basis is None and a["art"] != "beschreibung":
                raise logik.AntwortFehler("Für ein neues Dokument gib die ganze beschreibung aus.")
            neu = logik.neue_beschreibung(basis, a) if basis is not None else a["beschreibung"]
            if alt is not None and neu.get("art") != alt.get("art"):
                raise logik.AenderungFehler(f"art bleibt {alt.get('art')!r}")
            geaendert = True
            bauen(neu)
            return a, neu
        except (logik.AntwortFehler, logik.AenderungFehler, renderer.BeschreibungUngueltig) as f:
            if runde == 1:
                raise logik.AenderungFehler(str(f)) from None
            logger.info("Wunsch %s: Korrektur (%s)", lauf_id, type(f).__name__)
            zeige = neu if geaendert else basis
            if zeige is None:
                prompt_k = f"Das ging so nicht:\n{f}\n\nAntworte noch einmal mit genau einem JSON-Objekt wie verlangt."
            else:
                prompt_k = logik.prompt_korrektur(str(f), zeige, geaendert)
                basis = zeige
            e = _claude(u, prompt_k, lauf_id, sitzung=e.sitzung, lese=lese)
    raise AssertionError("nicht erreichbar")


def antwort(w: dict, ok: bool, text: str, stand: str, fehler: str | None = None, wieder_frei: str | None = None,
            fassung: dict | None = None, auftrag: str | None = None, sekunden: float = 0, usd: float = 0) -> dict:
    return {"id": w["id"], "art": w.get("art"), "zeit": schnittstelle.jetzt(), "ok": ok, "stand": stand,
            "text": text, "fehler": fehler, "wieder_frei": wieder_frei, "fassung": fassung, "auftrag": auftrag,
            "sekunden": round(sekunden, 1), "usd": round(usd, 4)}


# --- a) Änderung -------------------------------------------------------------------------------------------------

@dataclass
class Dokument:
    agent: str  # Agent der Kette
    ergebnis: dict  # erledigter Auftrag, an dem eine gründliche Nachbesserung ansetzt
    ursprung: str
    name: str  # Dateiname
    beschreibung: Path | None
    datei: Path | None  # die Datei selbst (bei schnell geänderten Fassungen die eigene Kopie)
    schnell_fassung: bool = False


def dokument_finden(w: dict, u: Umgebung) -> Dokument:
    """Fassung zum Wunsch: Datei nr des Auftrags bezug oder eigene Fassung n seiner Kette. Abbruch, wenn es sie nicht
    (mehr) gibt."""
    try:
        auftrag = auftraege.erledigter(w["bezug"], u.basis)
        ursprung = fassungen.ursprung(w["bezug"], u.basis)
    except (auftraege.AuftragFehler, fassungen.FassungFehler) as f:
        logger.warning("Wunsch %s: %s", w["id"], f)
        raise Abbruch("ungueltig", TEXTE["ungueltig"]) from None
    agent = auftrag["agent"]
    if auftrag.get("status") != "erledigt" or agent not in GRUENDLICH + (AGENT,):
        raise Abbruch("ungueltig", TEXTE["ungueltig"])
    if w.get("eigene"):
        stand = fassungen.lesen(w["bezug"], u.basis)
        e = next((e for e in stand["eigene"] if e["n"] == w["eigene"] and fassungen.art(e) == fassungen.ART_FASSUNG),
                 None)
        if e is None:
            raise Abbruch("ungueltig", TEXTE["ungueltig"])
        kopie = u.daten / "fassungen" / ursprung / f"eigene-{e['n']}"
        b = kopie / "beschreibung.json"
        erledigte = [a for a in fassungen.kette(w["bezug"], u.basis) if a.get("status") == "erledigt"]
        ergebnis = max(erledigte, key=lambda a: a.get("abgeschlossen") or "") if erledigte else auftrag
        return Dokument(agent, ergebnis, ursprung, e["name"], b if b.is_file() else None,
                        kopie / e["name"] if (kopie / e["name"]).is_file() else None, b.is_file())
    pfade = auftrag.get("ergebnis_dateien") or []
    if not 0 <= w.get("nr", 0) < len(pfade):
        raise Abbruch("ungueltig", TEXTE["ungueltig"])
    datei = u.agenten_dir / agent / pfade[w["nr"]]
    return Dokument(agent, auftrag, ursprung, datei.name, logik.beschreibung_finden(datei), datei)


def lernen(w: dict, u: Umgebung, d: Dokument) -> None:
    """Wunsch zum Lernen an den Feedback-Dienst (nur lernen, keine Nachbesserung). Nur wenn [weitergabe] schnell
    feedback erlaubt (Hauptordner-Chat), sonst würde der Dienst eine zweite Nachbesserung anlegen."""
    if not einstellungen.weitergabe_erlaubt(u.einstellungen(), AGENT, "feedback"):
        logger.info("Wunsch %s: Lernen aus ([weitergabe] schnell ohne feedback)", w["id"])
        return
    try:
        u.weitergeben(AGENT, "feedback", f"Zur Datei „{d.name}“: {w['text']}", None, cfg=u.cfg, basis=u.basis,
                      agenten_dir=u.agenten_dir, bezug=d.ergebnis["id"], quelle="feedback",
                      felder={"feedback_modus": "nur_lernen"}, still=True)
        u.starten("feedback")
    except (auftraege.AuftragFehler, OSError) as f:
        logger.error("Wunsch %s: Lernen nicht weitergegeben: %s", w["id"], f)
        u.melden(f"Wunsch {w['id']}: Feedback zum Lernen nicht weitergegeben: {f}")


def gruendlich(w: dict, u: Umgebung, d: Dokument, grund: str) -> dict:
    """Zu groß oder ohne Beschreibung: Nachbesserung an den gründlichen Agenten. Schnelle Dokumente haben keinen."""
    logger.info("Wunsch %s: gründlich (%s)", w["id"], kurz_grund(grund))
    if d.agent == AGENT:
        return antwort(w, True, f"{TEXTE['zu_gross']} {grund}".strip(), "zu_gross")
    grundlage, anhang = "", None
    if d.schnell_fassung and d.datei:
        grundlage = (f"Grundlage ist die schnell geänderte Fassung „{d.name}“ (angehängt), nicht dein letztes "
                     "Ergebnis. Baue darauf auf und setze den Wunsch darauf um.")
        anhang = [d.datei]
    try:
        nid = u.weitergeben(AGENT, d.agent, logik.nachbesserung_text(d.ergebnis, d.name, w["text"], grundlage), None,
                            dateien=anhang, cfg=u.cfg, basis=u.basis, agenten_dir=u.agenten_dir,
                            bezug=d.ergebnis["id"], nachbesserung=True, still=True)
    except (auftraege.AuftragFehler, OSError) as f:
        logger.error("Wunsch %s: Nachbesserung nicht weitergegeben: %s", w["id"], f)
        u.melden(f"Wunsch {w['id']}: Nachbesserung an {d.agent} nicht weitergegeben: {f}")
        raise Abbruch("technik", TEXTE["technik"]) from None
    u.starten(d.agent)
    return antwort(w, True, TEXTE["gruendlich"], "gruendlich", auftrag=nid)


def kurz_grund(grund: str) -> str:
    return logik.kurz(grund, 80)


def aenderung(w: dict, u: Umgebung) -> dict:
    d = dokument_finden(w, u)
    if d.beschreibung is None:
        a = gruendlich(w, u, d, "")
        lernen(w, u, d)
        return a
    alt = json.loads(d.beschreibung.read_text(encoding="utf-8"))
    profil = profil_laden(u, d.agent)
    arbeit = u.daten / "arbeit" / w["id"]
    shutil.rmtree(arbeit, ignore_errors=True)
    arbeit.mkdir(parents=True)
    ziel = arbeit / d.name
    regeln_ = regeln.agent_regeln(u.agenten_dir / logik.profil_agent(d.agent))
    prompt = logik.prompt_aenderung(w["text"], alt, format_text([alt["art"]]), regeln_, d.name, w.get("seite"))
    try:
        try:
            a, neu = entwerfen(u, prompt, f"schnell-{w['id']}", alt,
                               lambda b: u.bauen(b, ziel, profil=profil))
        except logik.AenderungFehler as f:
            logger.warning("Wunsch %s: auch nach Korrektur ungültig: %s", w["id"], logik.kurz(str(f), 300))
            a, neu = {"art": "zu_gross", "grund": ""}, {}
        if a["art"] == "zu_gross":
            ergebnis = gruendlich(w, u, d, a.get("grund", ""))
            lernen(w, u, d)
            return ergebnis
        (arbeit / "beschreibung.json").write_text(json.dumps(neu, ensure_ascii=False, indent=1), encoding="utf-8")
        abgabe = u.daten / "tmp" / f"abgabe-{w['id']}"
        shutil.rmtree(abgabe, ignore_errors=True)
        abgabe.mkdir(parents=True)
        shutil.copy2(ziel, abgabe / d.name)
        try:
            eintrag = fassungen.eigene_dazu(d.ergebnis["id"], abgabe / d.name, logik.notiz(w["text"]), u.basis,
                                            u.agenten_dir)
        finally:
            shutil.rmtree(abgabe, ignore_errors=True)
        ablage = u.daten / "fassungen" / d.ursprung / f"eigene-{eintrag['n']}"
        ablage.parent.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(ablage, ignore_errors=True)
        arbeit.rename(ablage)
    finally:
        shutil.rmtree(arbeit, ignore_errors=True)
    vorschau = ablage / f"{Path(d.name).stem}-vorschau"
    fassung = {"agent": d.agent, "bezug": d.ergebnis["id"], "ursprung": d.ursprung, "eigene": eintrag["n"],
               "name": eintrag["name"], "datei": eintrag["datei"],
               "vorschau": str(vorschau.relative_to(HIER)) if vorschau.is_dir() and vorschau.is_relative_to(HIER)
               else None}
    lernen(w, u, d)
    return antwort(w, True, a.get("antwort") or TEXTE["geaendert"], "fertig", fassung=fassung)


# --- b) Schnelles Dokument ---------------------------------------------------------------------------------------

def ort_text(ort: str | None, u: Umgebung) -> str:
    if not ort:
        return ""
    try:
        return logik.ort_text(struktur.laden(INSTANZ).ort(ort))
    except (OSError, struktur.StrukturFehler) as f:
        logger.warning("Struktur nicht lesbar: %s", f)
        u.melden(f"reihen.toml nicht lesbar, schnelles Dokument ohne Ort: {f}")
        return ""


def dateien_text(pfade: list[Path]) -> str:
    """Text aus Lias Dateien (ohne Fotos), je Datei mit Name, zusammen höchstens DATEI_ZEICHEN."""
    teile, je = [], DATEI_ZEICHEN // max(len(pfade), 1)
    for p in pfade:
        try:
            text = (textfassung.als_text(p) or "").strip()
        except Exception as f:  # noqa: BLE001 - kaputte Datei: Claude bekommt den Hinweis
            logger.warning("Datei nicht lesbar: %s", type(f).__name__)
            text = "(Die Datei ließ sich nicht lesen.)"
        if len(text) > je:
            text = text[:je] + "\n[… gekürzt]"
        teile.append(f"--- Datei: {p.name}\n{text or '(leer)'}")
    return "\n\n".join(teile)


def dokument(w: dict, u: Umgebung) -> dict:
    quellen = [schnittstelle.dateien_ordner(w["id"], u.daten) / n for n in w.get("dateien") or []]
    aid = auftraege.neuer_auftrag(AGENT, w["text"], quelle="schnell-dokument", ort=w.get("ort"),
                                  dateien=[p for p in quellen if p.is_file()] or None, basis=u.basis,
                                  agenten_dir=u.agenten_dir)
    try:
        a_eintrag = next(a for a in auftraege.neue(AGENT, u.basis) if a["id"] == aid)
        dateien = [u.agenten_dir / AGENT / p for p in a_eintrag.get("dateien") or []]
        fotos = [p for p in dateien if p.suffix.lower() in schnittstelle.FOTO_ENDUNGEN]
        texte = [p for p in dateien if p not in fotos]
        profil = profil_laden(u, AGENT)
        ordner = u.daten / "dokumente" / aid
        ordner.mkdir(parents=True, exist_ok=True)
        gebaut = {}

        def bauen(b):
            if b.get("art") not in logik.DOKUMENT_ARTEN:
                raise logik.AenderungFehler(f"art muss eins von {', '.join(logik.DOKUMENT_ARTEN)} sein")
            ziel = ordner / logik.dateiname(b)
            gebaut["ziel"] = ziel
            u.bauen(b, ziel, profil=profil)

        prompt = logik.prompt_dokument(w["text"], ort_text(w.get("ort"), u), dateien_text(texte),
                                       [str(p) for p in fotos], format_text(logik.DOKUMENT_ARTEN),
                                       regeln.agent_regeln(u.agenten_dir / "unterricht"))
        try:
            a, b = entwerfen(u, prompt, aid, None, bauen, lese=[fotos[0].parent] if fotos else None)
        except logik.AenderungFehler as f:
            logger.warning("Wunsch %s: Dokument auch nach Korrektur ungültig: %s", w["id"], logik.kurz(str(f), 300))
            u.melden(f"Schnelles Dokument {aid}: Beschreibung auch nach Korrektur ungültig")
            raise Abbruch("technik", TEXTE["technik"]) from None
        if a["art"] == "zu_gross":  # sollte bei neuen Dokumenten nicht kommen
            raise Abbruch("technik", TEXTE["technik"])
        ziel = gebaut["ziel"]
        ziel.with_suffix(".json").write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
        text = (a.get("antwort") or "Hier ist dein Dokument.").strip()
        auftraege.abschliessen(aid, f"{text}\n\n{logik.HINWEIS}", dateien=[ziel], basis=u.basis,
                               agenten_dir=u.agenten_dir, daten={"kern": text, "pruefen": logik.HINWEIS})
    except Abbruch as f:
        auftraege.abschliessen(aid, f.text, status="fehlgeschlagen", basis=u.basis, agenten_dir=u.agenten_dir)
        raise
    except Exception as f:
        auftraege.abschliessen(aid, f"Fehler: {type(f).__name__}", status="fehlgeschlagen", basis=u.basis,
                               agenten_dir=u.agenten_dir)
        raise
    vorschau = ziel.parent / f"{ziel.stem}-vorschau"
    fassung = {"agent": AGENT, "bezug": aid, "ursprung": aid, "eigene": None, "name": ziel.name,
               "datei": str(ziel.relative_to(u.agenten_dir / AGENT)),
               "vorschau": str(vorschau.relative_to(u.agenten_dir / AGENT)) if vorschau.is_dir() else None}
    return antwort(w, True, f"{text} {logik.HINWEIS}", "fertig", fassung=fassung, auftrag=aid)


# --- Warteschlange -----------------------------------------------------------------------------------------------

def bearbeiten(w: dict, u: Umgebung) -> dict:
    """Ein geprüfter Wunsch. Gibt immer eine Antwort zurück (bei Fehlern mit Satz für Lia)."""
    start, u.laeufe = time.monotonic(), []
    try:
        a = aenderung(w, u) if w["art"] == "aenderung" else dokument(w, u)
    except Abbruch as f:
        logger.warning("Wunsch %s: %s", w["id"], f.fehler)
        if f.fehler == "technik":
            u.melden(f"Wunsch {w['id']} ({w['art']}) fehlgeschlagen, siehe logs/schnell.log")
        a = antwort(w, False, f.text, "fehler", f.fehler, f.wieder_frei)
    except Exception as f:  # Fehler im eigenen Code: Lia bekommt einen Satz, Jan die Ursache
        logger.exception("Wunsch %s fehlgeschlagen", w["id"])
        u.melden(f"Wunsch {w['id']} ({w['art']}) fehlgeschlagen: {type(f).__name__}: {f}")
        a = antwort(w, False, TEXTE["technik"], "fehler", "technik")
    finally:
        for e in u.laeufe:
            u.loeschen(e.sitzung)
    a["sekunden"] = round(time.monotonic() - start, 1)
    a["usd"] = round(sum(e.usd for e in u.laeufe), 4)
    logger.info("Wunsch %s: %s, %s, %d Läufe, %.1f s, %.3f USD", w["id"], w["art"], a["stand"], len(u.laeufe),
                a["sekunden"], a["usd"])
    return a


def wunsch_lesen(pfad: Path) -> dict:
    try:
        roh = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as f:
        raise schnittstelle.WunschFehler(f"Wunsch-Datei nicht lesbar: {f}") from None
    return schnittstelle.wunsch_pruefen(roh)


def abarbeiten(u: Umgebung | None = None) -> int:
    """Alle wartenden Wünsche, älteste zuerst, auch solche, die währenddessen dazukommen."""
    u = u or Umgebung()
    aufraeumen(u.daten)
    gesehen, anzahl = set(), 0
    while neue := sorted((p for p in (u.daten / "wuensche").glob("*.json") if p.name not in gesehen),
                         key=lambda p: p.stat().st_mtime):
        for pfad in neue:
            gesehen.add(pfad.name)
            try:
                w = wunsch_lesen(pfad)
            except schnittstelle.WunschFehler as f:
                logger.warning("%s: %s", pfad.name, f)
                if schnittstelle.ID_MUSTER.match(pfad.stem):
                    schnittstelle.antwort_schreiben(antwort({"id": pfad.stem}, False, str(f), "fehler", "ungueltig"),
                                                    u.daten)
                pfad.unlink(missing_ok=True)
                continue
            try:
                schnittstelle.antwort_schreiben(bearbeiten(w, u), u.daten)
            finally:
                shutil.rmtree(schnittstelle.dateien_ordner(w["id"], u.daten), ignore_errors=True)
            pfad.unlink(missing_ok=True)
            anzahl += 1
    return anzahl


def aufraeumen(daten: Path = DATEN, tage: int = AUFBEWAHREN_TAGE, jetzt: float | None = None) -> int:
    """Antworten älter als tage, liegengebliebene Arbeitsordner und Uploads älter als 1 Tag."""
    jetzt = jetzt or time.time()
    weg = 0
    for p in (daten / "antworten").glob("*.json"):
        if jetzt - p.stat().st_mtime > tage * 86400:
            p.unlink(missing_ok=True)
            weg += 1
    for name in ("arbeit", "dateien", "tmp"):
        for p in (daten / name).glob("*"):
            if jetzt - p.stat().st_mtime > 86400:
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    p.unlink(missing_ok=True)
                weg += 1
    return weg


if __name__ == "__main__":
    abarbeiten()
