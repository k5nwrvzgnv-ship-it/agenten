"""Schnittstelle der Web-App zum Chat-Agenten (nur Python-Bordmittel, zum Importieren aus shared/webapp).

Gespräche (neu 10.11.2026, Bauplan shared/webapp/bauplan-gespraech.md): gespraech_anlegen(), gespraeche(),
gespraech(), umbenennen(), umhaengen(), loeschen(), gesehen(), nachricht(), bisher(), auftrag_ordnen(); die Antwort
holt antwort_holen(nachricht_id). Format: STATUS.md, Abschnitt „Gespräche“.

Alte Spalte „Fragen“ (bis die Web-App umgeschaltet hat): frage_stellen() legt Lias Dateien nach data/dateien/<id>/ und dann data/fragen/<id>.json an. systemd
(lia-chat.path) startet daraufhin lia-chat.service, der Agent schreibt data/antworten/<id>.json und löscht die Frage. Die Web-App fragt mit antwort_holen(id) nach,
bis die Antwort da ist (Vorschlag: alle 2 s). Format beider Dateien: STATUS.md, Abschnitt „Schnittstelle“.
"""

import json
import os
import re
import shutil
import uuid
from pathlib import Path

import chatverlauf as _verlauf
import gespraechablage as _g
from gespraechablage import OHNE_ORT, GespraechFehler  # noqa: F401 - für die Web-App

ORDNER = Path(__file__).resolve().parent / "data"
MAX_ZEICHEN = 4000
ID_MUSTER = re.compile(r"^[0-9a-f]{12}$")
ORT_FELDER = {"reihe": str, "stunde_id": str, "stunde": int, "chip": str, "stunde_thema": str,
              "materialien": list}
# Dateien in der Frage (Jan 02.11.2026): PDF, Word, PowerPoint, kein Excel und keine Bilder
ENDUNGEN = (".pdf", ".docx", ".pptx")
MAX_DATEIEN = 3
MAX_BYTES = 20 * 1024 * 1024
_UNERLAUBT = re.compile(r"[^\w .()-]")


class FrageFehler(ValueError):
    pass


def ort_pruefen(ort) -> dict | None:
    """Ort aus der Frage: None (ohne Ort) oder dict nur mit bekannten Feldern richtigen Typs."""
    if ort is None:
        return None
    if not isinstance(ort, dict) or not isinstance(ort.get("reihe"), str) or not ort["reihe"]:
        raise FrageFehler("Ort braucht eine Reihe (Kennung) oder ist None")
    for k, v in ort.items():
        if k not in ORT_FELDER or (v is not None and (not isinstance(v, ORT_FELDER[k]) or isinstance(v, bool))):
            raise FrageFehler(f"Ort: Feld {k} unbekannt oder falscher Typ")
    if not all(isinstance(m, str) for m in ort.get("materialien") or []):
        raise FrageFehler("Ort: materialien ist eine Liste von Titeln")
    return {k: v for k, v in ort.items() if v is not None}


def dateiname(name: str) -> str:
    """Dateiname ohne Pfadteile und Sonderzeichen, nicht versteckt, höchstens 120 Zeichen (Endung bleibt)."""
    stamm, endung = os.path.splitext(_UNERLAUBT.sub("_", Path(str(name)).name).strip().lstrip("."))
    return (stamm[:120 - len(endung)].strip() or "datei") + endung.lower()


def dateien_pruefen(namen) -> list[str]:
    """Namen der Dateien aus der Frage-Datei: Liste, höchstens 3, bereinigt, erlaubte Endung, ohne Doppelte."""
    if namen is None:
        return []
    if not isinstance(namen, list) or not all(isinstance(n, str) for n in namen):
        raise FrageFehler("dateien ist eine Liste von Namen")
    if len(namen) > MAX_DATEIEN:
        raise FrageFehler(f"Höchstens {MAX_DATEIEN} Dateien je Frage.")
    for n in namen:
        if n != dateiname(n):
            raise FrageFehler("Dateiname ungültig")
        if not n.lower().endswith(ENDUNGEN):
            raise FrageFehler("Im Chat gehen nur PDF, Word und PowerPoint.")
    if len(set(namen)) != len(namen):
        raise FrageFehler("Zwei Dateien mit demselben Namen")
    return namen


def frage_pruefen(frage) -> dict:
    """Prüft eine Frage-Datei (auch im Agenten). Gibt die bereinigte Frage zurück oder wirft FrageFehler."""
    if not isinstance(frage, dict):
        raise FrageFehler("Frage ist kein JSON-Objekt")
    if not isinstance(frage.get("id"), str) or not ID_MUSTER.match(frage["id"]):
        raise FrageFehler("Frage ohne gültige id")
    text = frage.get("text")
    if not isinstance(text, str) or not text.strip():
        raise FrageFehler("Die Frage ist leer.")
    if len(text) > MAX_ZEICHEN:
        raise FrageFehler(f"Die Frage ist zu lang (höchstens {MAX_ZEICHEN} Zeichen).")
    return {"id": frage["id"], "zeit": str(frage.get("zeit") or ""), "text": text.strip(),
            "gruendlich": frage.get("gruendlich") is True, "netz": frage.get("netz") is True,
            "ort": ort_pruefen(frage.get("ort")), "dateien": dateien_pruefen(frage.get("dateien"))}


def _schreiben(ziel: Path, daten: dict) -> None:
    """Atomar: erst in data/tmp, dann umbenennen (die Pfad-Unit sieht nie eine halbe Datei)."""
    tmp = ziel.parent.parent / "tmp" / ziel.name
    tmp.parent.mkdir(parents=True, exist_ok=True)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, ziel)


def frage_stellen(text: str, ort: dict | None = None, gruendlich: bool = False, ordner: Path = ORDNER,
                  netz: bool = False, dateien: list[tuple[str, Path]] | None = None) -> str:
    """Legt die Frage in die Warteschlange und gibt ihre id zurück. Ungültig: FrageFehler (Text für Lia).

    netz=True: Claude darf im Netz suchen (Lias Häkchen „Im Netz nachsehen“).
    dateien: [(Name, wie Lia ihn hochgeladen hat; Pfad der hochgeladenen Datei)], höchstens 3, PDF/Word/
    PowerPoint bis 20 MB. Die Dateien werden nach data/dateien/<id>/ verschoben; der Agent löscht sie nach der
    Antwort. Bei FrageFehler bleibt nichts liegen (die hochgeladenen Dateien räumt die Web-App selbst weg).
    """
    dateien = list(dateien or [])
    namen = [dateiname(n) for n, _ in dateien]
    frage = frage_pruefen({"id": uuid.uuid4().hex[:12], "zeit": _verlauf.jetzt().isoformat(timespec="seconds"),
                           "text": text, "gruendlich": gruendlich, "netz": netz, "ort": ort, "dateien": namen})
    for _, quelle in dateien:
        if not Path(quelle).is_file():
            raise FrageFehler("Eine Datei ist nicht angekommen.")
        if Path(quelle).stat().st_size > MAX_BYTES:
            raise FrageFehler("Eine Datei ist zu groß (höchstens 20 MB).")
    ziel = Path(ordner) / "dateien" / frage["id"]
    for name, (_, quelle) in zip(namen, dateien, strict=True):
        ziel.mkdir(parents=True, exist_ok=True)
        shutil.move(str(quelle), ziel / name)
    _schreiben(Path(ordner) / "fragen" / f"{frage['id']}.json", frage)
    return frage["id"]


def dateien_ordner(frage_id: str, ordner: Path = ORDNER) -> Path:
    return Path(ordner) / "dateien" / frage_id


def antwort_schreiben(antwort: dict, ordner: Path = ORDNER) -> None:
    _schreiben(Path(ordner) / "antworten" / f"{antwort['id']}.json", antwort)


def antwort_holen(frage_id: str, ordner: Path = ORDNER) -> dict | None:
    """Die Antwort oder None, solange sie noch nicht da ist."""
    if not ID_MUSTER.match(frage_id or ""):
        return None
    pfad = Path(ordner) / "antworten" / f"{frage_id}.json"
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def wartet(frage_id: str, ordner: Path = ORDNER) -> bool:
    """True, solange die Frage noch in der Warteschlange liegt."""
    return bool(ID_MUSTER.match(frage_id or "")) and (Path(ordner) / "fragen" / f"{frage_id}.json").exists()


def verlauf(ordner: Path = ORDNER) -> list[dict]:
    """Beantwortete Fragen der letzten 30 Tage, älteste zuerst."""
    return _verlauf.lesen(ordner)


# --- Gespräche ---------------------------------------------------------------------------------------------------

MAX_TEXT = 60_000  # Zeichen je Nachricht (claude -p lehnt Prompts über 128 KB ab)
FOTO_ENDUNGEN = (".jpg", ".jpeg", ".png")
HEIC_ENDUNGEN = (".heic", ".heif")
MAX_FOTOS = 5
HEIC_SATZ = ("HEIC-Fotos kann ich noch nicht lesen. Stell am iPhone bitte unter Einstellungen › Kamera › Formate "
             "„Maximale Kompatibilität“ ein oder schick das Foto als Bildschirmfoto (PNG).")


def _neue_id() -> str:
    return uuid.uuid4().hex[:12]


def gespraech_anlegen(name: str = "", ort: dict | None = None, ordner: Path = ORDNER) -> str:
    """Neues, leeres Gespräch. name leer: Name kommt aus der ersten Nachricht (name_vorschlag True). Gibt die id."""
    g = _g.neu(_neue_id(), _g.name_pruefen(name), _g.ort_pruefen(ort))
    with _g.sperre(ordner):
        _g.schreiben(g, ordner)
    return g["id"]


def gespraeche(ort: dict | str | None = None, ordner: Path = ORDNER) -> list[dict]:
    """Übersichten, jüngste zuerst. ort None: alle; OHNE_ORT: nur ohne Ort; {"ebene", "id"}: genau dort."""
    gs = _g.alle(ordner)
    if ort == OHNE_ORT:
        gs = [g for g in gs if g.get("ort") is None]
    elif ort is not None:
        ziel = _g.ort_pruefen(ort)
        gs = [g for g in gs if g.get("ort") == ziel]
    return sorted((_g.kurz(g) for g in gs), key=lambda k: k["zuletzt"] or "", reverse=True)


def gespraech(gid: str, ordner: Path = ORDNER) -> dict | None:
    """Das ganze Gespräch (mit eintraege, laeuft) oder None."""
    g = _g.lesen(gid, ordner)
    if g is None:
        return None
    return {**{k: v for k, v in g.items() if k not in ("sitzung", "kontext")}, "laeuft": _g.laeuft(g)}


def _aendern(gid: str, ordner: Path, aenderung) -> dict:
    """aenderung(g) unter der Sperre auf das Gespräch anwenden und speichern. Unbekannt: GespraechFehler."""
    with _g.sperre(ordner):
        g = _g.lesen(gid, ordner)
        if g is None:
            raise GespraechFehler("Dieses Gespräch gibt es nicht mehr.")
        aenderung(g)
        _g.schreiben(g, ordner)
    return g


def umbenennen(gid: str, name: str, ordner: Path = ORDNER) -> None:
    name = _g.name_pruefen(name)
    if not name:
        raise GespraechFehler("Der Name ist leer.")
    _aendern(gid, ordner, lambda g: g.update(name=name, name_vorschlag=False))


def umhaengen(gid: str, ort: dict | None, ordner: Path = ORDNER) -> None:
    """Gespräch an einen anderen Ort (oder ohne Ort). Claude bekommt den neuen Ort mit der nächsten Nachricht."""
    ort = _g.ort_pruefen(ort)
    _aendern(gid, ordner, lambda g: g.update(ort=ort))


def gesehen(gid: str, ordner: Path = ORDNER) -> None:
    """Lia hat das Gespräch angesehen: „neu“ in der Übersicht fällt weg."""
    _aendern(gid, ordner, lambda g: g.update(gesehen=sum(e.get("rolle") == "claude" for e in g["eintraege"])))


def loeschen(gid: str, ordner: Path = ORDNER) -> bool:
    """Gespräch samt Dateien weg; die claude-Sitzung löscht der Agent beim nächsten Aufräumen (sie gehört dann
    zu keinem Gespräch mehr). Gibt False, wenn es das Gespräch nicht gab."""
    with _g.sperre(ordner):
        return _g.loeschen(gid, ordner) is not None


def _art(name: str) -> str:
    endung = os.path.splitext(name)[1].lower()
    if endung in HEIC_ENDUNGEN:
        raise GespraechFehler(HEIC_SATZ)
    if endung in FOTO_ENDUNGEN:
        return "foto"
    if endung in ENDUNGEN:
        return "datei"
    raise GespraechFehler("Im Gespräch gehen Fotos (JPG, PNG), PDF, Word und PowerPoint.")


def anhaenge_pruefen(dateien) -> tuple[list[str], list[str], list[tuple[str, Path]]]:
    """[(Name, Pfad)] prüfen: Fotos bis 5, Dateien bis 3, je bis 20 MB. Gibt (Fotos, Dateien, [(Name, Pfad)]) mit
    bereinigten Namen."""
    fotos, andere, paare = [], [], []
    for name, quelle in dateien:
        n = dateiname(name)
        (fotos if _art(n) == "foto" else andere).append(n)
        paare.append((n, Path(quelle)))
        if not Path(quelle).is_file():
            raise GespraechFehler("Eine Datei ist nicht angekommen.")
        if Path(quelle).stat().st_size > MAX_BYTES:
            raise GespraechFehler("Eine Datei ist zu groß (höchstens 20 MB).")
    if len(fotos) > MAX_FOTOS:
        raise GespraechFehler(f"Höchstens {MAX_FOTOS} Fotos je Nachricht.")
    if len(andere) > MAX_DATEIEN:
        raise GespraechFehler(f"Höchstens {MAX_DATEIEN} Dateien je Nachricht.")
    if len(set(fotos + andere)) != len(fotos) + len(andere):
        raise GespraechFehler("Zwei Dateien mit demselben Namen.")
    return fotos, andere, paare


def nachricht(gid: str, text: str, dateien: list[tuple[str, Path]] | None = None, gruendlich: bool = False,
              netz: bool = False, ordner: Path = ORDNER) -> str:
    """Lias Nachricht ins Gespräch und in die Warteschlange. Gibt die nachricht_id (für antwort_holen).

    dateien: [(Name wie hochgeladen, Pfad)]; Fotos JPG/PNG bis 5, PDF/Word/PowerPoint bis 3, je bis 20 MB. Sie
    werden nach data/gespraeche/<id>/<nachricht_id>/ verschoben und bleiben bis zum Löschen des Gesprächs.
    Ungültig: GespraechFehler mit Satz für Lia; dann bleibt alles, wo es war.
    """
    text = text.strip() if isinstance(text, str) else ""
    dateien = list(dateien or [])
    if not text and not dateien:
        raise GespraechFehler("Die Nachricht ist leer.")
    if len(text) > MAX_TEXT:
        raise GespraechFehler(f"Die Nachricht ist zu lang (höchstens {MAX_TEXT:,} Zeichen).".replace(",", "."))
    fotos, andere, paare = anhaenge_pruefen(dateien)
    nid = _neue_id()
    eintrag = {"id": nid, "rolle": "lia", "zeit": _g.zeit_text(), "text": text, "fotos": fotos, "dateien": andere,
               "gruendlich": gruendlich is True, "netz": netz is True, "stand": "wartet", "fehler": None}
    with _g.sperre(ordner):
        g = _g.lesen(gid, ordner)
        if g is None:
            raise GespraechFehler("Dieses Gespräch gibt es nicht mehr.")
        if _g.laeuft(g):
            raise GespraechFehler("Claude antwortet noch auf deine letzte Nachricht. Warte bitte kurz.")
        ziel = _g.dateien_ordner(gid, ordner) / nid
        for name, quelle in paare:
            ziel.mkdir(parents=True, exist_ok=True)
            shutil.move(str(quelle), ziel / name)
        if g.get("name_vorschlag") and not g["eintraege"]:
            g["name"] = _g.name_aus_text(text or (fotos + andere)[0])
        g["eintraege"].append(eintrag)
        g["zuletzt"] = eintrag["zeit"]
        _g.schreiben(g, ordner)
        _schreiben(Path(ordner) / "fragen" / f"{nid}.json", {"art": "nachricht", "id": nid, "gespraech": gid})
    return nid


def _sonderlauf(gid: str, art: str, ordner: Path) -> str:
    g = _g.lesen(gid, ordner)
    if g is None:
        raise GespraechFehler("Dieses Gespräch gibt es nicht mehr.")
    if not any(e.get("rolle") == "claude" for e in g["eintraege"]):
        raise GespraechFehler("Im Gespräch steht noch nichts, das ich ordnen könnte.")
    nid = _neue_id()
    _schreiben(Path(ordner) / "fragen" / f"{nid}.json", {"art": art, "id": nid, "gespraech": gid})
    return nid


def bisher(gid: str, ordner: Path = ORDNER) -> str:
    """„Was haben wir bisher?“: Zusammenfassung des Gesprächs, steht nicht im Verlauf. Gibt die nachricht_id."""
    return _sonderlauf(gid, "bisher", ordner)


def auftrag_ordnen(gid: str, ordner: Path = ORDNER) -> str:
    """„Auftrag ordnen“: Auftragstext aus dem Gespräch (für „Neu“), steht nicht im Verlauf. Gibt die nachricht_id."""
    return _sonderlauf(gid, "auftrag", ordner)
