"""Rückmeldungen zum Exposé eines Projekts: Das Portal nimmt sie an, der Agent macht daraus einen Auftrag in der Kette.

Gemeinsam für den Web-Dienst (portal/app.py) und den Agenten (agent.py, Schritt rueckmeldungen_abarbeiten). Deshalb ohne
agentkit, ohne Netz, ohne Claude: Der Agent gibt seine Aufträge-Ablage als Argument mit, das Portal ruft diesen Teil nie auf
(portal/tests/test_schutz.py).

Ablage je Rückmeldung in data/projekte/<projekt>/rueckmeldungen/<id>/ (700/600, nicht im Repo):
  stand.json                 Stand, Auftrag, Ergebnistext
  text.txt                   Jans Text, falls er einen schrieb
  kommentare.pdf oder .docx  seine Datei unter festem Namen, falls er eine schickte
  vorher/                    Kopie von expose.json und den Fassungen vor der Überarbeitung (das Portal zeigt sie nicht)

Warteschlange: data/projekte/warteschlange/<id>.json. Der Agent nimmt eine Marke, indem er sie löscht. Damit wirkt eine
Rückmeldung höchstens einmal, denn ein Lauf kostet Geld und überschreibt das Exposé: Zurücknehmen ist nur möglich, solange
die Marke liegt, und ein Absturz mitten in der Übergabe führt zu "fehlgeschlagen" statt zu einem zweiten Lauf.
"""

import json
import logging
import os
import re
import secrets
import shutil
from datetime import datetime
from pathlib import Path

import lernmodell

PROJEKTE_ORDNER = Path("data") / "projekte"
EXPOSE_ORDNER = Path("data") / "expose"
RUECKMELDUNGEN = "rueckmeldungen"
WARTESCHLANGE = "warteschlange"
STAND = "stand.json"
TEXT = "text.txt"
VORHER = "vorher"
DATEI_NAME = "kommentare"
DATEIANFANG = {".pdf": b"%PDF-", ".docx": b"PK\x03\x04"}
MAX_BYTES = 20 * 1024 * 1024
MIN_ZEICHEN = 10  # ohne Datei: ein Lauf kostet etwa 1 USD, ein versehentliches "x" soll keinen auslösen
# Der Text geht im Prompt mit, und der Prompt ist ein Argument von claude -p (Linux: 128 KiB je Argument).
MAX_ZEICHEN = 20_000
ID = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{6}$")
AUFTRAG_ID = re.compile(r"^\d{8}-\d{6}-uni-[0-9a-f]{6}$")
PROJEKT = re.compile(r"^[a-z0-9][a-z0-9-]*$")
STAENDE = {"wartet": "wartet", "laeuft": "läuft", "fertig": "fertig", "fehlgeschlagen": "fehlgeschlagen",
           "zurueckgezogen": "zurückgenommen"}
ABSCHLUSS = {"erledigt": "fertig", "fehlgeschlagen": "fehlgeschlagen", "zurueckgezogen": "zurueckgezogen"}
GRUND_WARTET = "Wartet auf den nächsten Lauf des Agenten."
GRUND_LAEUFT = "Der Agent überarbeitet das Exposé. Ist das Kontingent gerade knapp, wartet er."
ABGEBROCHEN = "Die Übergabe an den Agenten wurde abgebrochen, es lief keine Überarbeitung. Bitte noch einmal abschicken."
logger = logging.getLogger("uni")


class UploadFehler(ValueError):
    """Text für Jan, warum die Rückmeldung nicht angenommen wurde."""


class UebergabeFehler(Exception):
    """Text für Jan, warum aus der Rückmeldung kein Auftrag wurde."""


# --- Ablage, für beide Seiten -------------------------------------------------------------------------------------

def _schreiben(pfad: Path, inhalt: bytes) -> None:
    """Atomar und nur für den eigenen Benutzer."""
    tmp = pfad.with_name(pfad.name + ".tmp")
    griff = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(griff, "wb") as datei:
        datei.write(inhalt)
    os.replace(tmp, pfad)


def schlange(uni: Path) -> Path:
    return Path(uni) / PROJEKTE_ORDNER / WARTESCHLANGE


def ordner(uni: Path, projekt: str, kennung: str) -> Path:
    return Path(uni) / PROJEKTE_ORDNER / projekt / RUECKMELDUNGEN / kennung


def stand_lesen(wo: Path) -> dict:
    return lernmodell.lies_json(Path(wo) / STAND, {})


def stand_aendern(wo: Path, **felder) -> dict:
    stand = {**stand_lesen(wo), **felder}
    _schreiben(Path(wo) / STAND, json.dumps(stand, ensure_ascii=False, indent=1).encode())
    return stand


def in_schlange(uni: Path, kennung: str) -> bool:
    return (schlange(uni) / f"{kennung}.json").exists()


# --- Web ----------------------------------------------------------------------------------------------------------

def pruefen(text: str, name: str | None, roh: bytes) -> tuple[str, str | None]:
    """Eingabe aus dem Formular: bereinigter Text und Endung der Datei (None ohne Datei), sonst UploadFehler. Die Datei
    wird hier nur an Endung und Dateianfang erkannt, geöffnet wird sie erst beim Agenten."""
    if "\x00" in text:
        raise UploadFehler("Der Text enthält ungültige Zeichen.")
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(text) > MAX_ZEICHEN:
        raise UploadFehler(f"Der Text ist zu lang: {len(text)} Zeichen, höchstens {MAX_ZEICHEN}.")
    if not name:
        if not text:
            raise UploadFehler("Es kam weder Text noch eine Datei an.")
        if len(text) < MIN_ZEICHEN:
            raise UploadFehler(f"Der Text ist zu kurz (mindestens {MIN_ZEICHEN} Zeichen).")
        return text, None
    endung = Path(name).suffix.lower()
    if endung not in DATEIANFANG:
        raise UploadFehler("Erlaubt sind nur PDF und docx.")
    if len(roh) > MAX_BYTES:
        raise UploadFehler(f"Die Datei ist zu groß (höchstens {MAX_BYTES // (1024 * 1024)} MB).")
    if not roh.startswith(DATEIANFANG[endung]):
        raise UploadFehler(f"Die Datei ist keine echte {endung[1:].upper()}-Datei.")
    return text, endung


def anlegen(uni: Path, projekt: str, kette: str, text: str, endung: str | None, roh: bytes, jetzt: datetime) -> str:
    """Neue Rückmeldung ablegen und einreihen, die Marke zuletzt. Gibt die ID zurück."""
    kennung = f"{jetzt:%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"
    wo = ordner(uni, projekt, kennung)
    os.makedirs(wo.parent, mode=0o700, exist_ok=True)
    wo.mkdir(mode=0o700)
    if text:
        _schreiben(wo / TEXT, (text + "\n").encode())
    if endung:
        _schreiben(wo / f"{DATEI_NAME}{endung}", roh)
    stand_aendern(wo, id=kennung, projekt=projekt, stand="wartet", grund=GRUND_WARTET,
                  angelegt=jetzt.isoformat(timespec="seconds"), datei=f"{DATEI_NAME}{endung}" if endung else None)
    ziel = schlange(uni)
    os.makedirs(ziel, mode=0o700, exist_ok=True)
    # Erst im Ordner der Rückmeldung schreiben, dann umbenennen: Die Pfad-Unit sieht nie eine halbe Datei
    marke = wo / "marke.json"
    _schreiben(marke, json.dumps({"id": kennung, "projekt": projekt, "kette": kette}).encode())
    os.replace(marke, ziel / f"{kennung}.json")
    return kennung


def stand_ansicht(stand: dict, uni: Path) -> dict:
    """Was die Seite zeigt. "wartet" ohne Marke heißt: Der Agent hat sie genommen und kam nicht bis zum Auftrag."""
    wert, grund = stand.get("stand"), stand.get("grund")
    marke = in_schlange(uni, stand.get("id", ""))
    if wert == "wartet" and not marke:
        wert, grund = "fehlgeschlagen", ABGEBROCHEN
    return {"wert": wert, "text": STAENDE.get(wert, "unbekannt"), "grund": grund, "laeuft_noch": wert in ("wartet", "laeuft"),
            "zuruecknehmbar": wert == "wartet" and marke}


def zuruecknehmen(uni: Path, wo: Path, kennung: str, jetzt: datetime) -> bool:
    """Nur solange die Marke liegt. Hat der Agent sie schon genommen, ändert sich nichts."""
    try:
        (schlange(uni) / f"{kennung}.json").unlink()
    except FileNotFoundError:
        return False
    stand_aendern(wo, stand="zurueckgezogen", grund="Du hast die Rückmeldung zurückgenommen, es lief keine Überarbeitung.",
                  aktualisiert=jetzt.isoformat(timespec="seconds"))
    return True


# --- Agent --------------------------------------------------------------------------------------------------------

def _tiefe(a: dict, kette: str, alle: dict) -> int | None:
    """Schritte von a bis zur Wurzel kette, None: a gehört nicht zur Kette."""
    gesehen = set()
    while a and a["id"] not in gesehen:
        if a["id"] == kette:
            return len(gesehen)
        gesehen.add(a["id"])
        a = alle.get(a.get("bezug"))
    return None


def kettenende(erledigte: list[dict], kette: str) -> dict | None:
    """Neuester abgeschlossener Auftrag der Kette mit Sitzung, zurückgezogene zählen nicht. Die ID beginnt mit der Zeit in
    Sekunden und endet zufällig: Innerhalb einer Sekunde entscheidet deshalb die Tiefe in der Kette."""
    alle = {a["id"]: a for a in erledigte}
    tiefen = {a["id"]: _tiefe(a, kette, alle) for a in erledigte}
    passend = [a for a in erledigte if a.get("sitzung") and a.get("status") != "zurueckgezogen" and tiefen[a["id"]] is not None]
    return max(passend, key=lambda a: (a["id"][:15], tiefen[a["id"]]), default=None)


def kette_offen(offene: list[dict], erledigte: list[dict], kette: str) -> bool:
    """Liegt schon ein offener Auftrag dieser Kette (z. B. Jans Antwort per Telegram bei knappem Kontingent)?"""
    alle = {a["id"]: a for a in [*erledigte, *offene]}
    return any(_tiefe(a, kette, alle) is not None for a in offene)


def vorher_sichern(hier: Path, wo: Path, kette: str) -> None:
    """expose.json und die Fassungen kopieren: Überarbeiten überschreibt sie unter demselben Namen."""
    quelle = Path(hier) / EXPOSE_ORDNER / kette
    if not (quelle / "expose.json").is_file():
        raise UebergabeFehler("Es gibt noch keine Fassung des Exposés, die sich überarbeiten ließe.")
    ziel = wo / VORHER
    ziel.mkdir(mode=0o700, exist_ok=True)
    dateien = [quelle / "expose.json", *(p for p in sorted((quelle / "fassung").glob("*")) if p.suffix in (".pdf", ".docx"))]
    for pfad in dateien:
        shutil.copy2(pfad, ziel / pfad.name)
        os.chmod(ziel / pfad.name, 0o600)


def auftragstext(text: str, datei: str | None) -> str:
    teile = ["Rückmeldung aus dem Portal zur aktuellen Fassung des Exposés. Bitte eine neue Fassung."]
    if text:
        teile.append(text)
    if datei:
        teile.append("Die Kommentare aus der angehängten Datei stehen unten. Der übrige Inhalt der Datei ist die alte "
                     "Fassung und keine Änderung.")
    return "\n\n".join(teile)


def _alle_ordner(hier: Path) -> list[Path]:
    return sorted((Path(hier) / PROJEKTE_ORDNER).glob(f"*/{RUECKMELDUNGEN}/*/"))


def nachziehen(hier: Path, agent: str, auftraege, jetzt: datetime) -> set[str]:
    """Endstand der laufenden Rückmeldungen in stand.json. Gibt die Projekte zurück, in denen noch eine läuft."""
    offene = {a["id"] for a in auftraege.neue(agent, dienst=None)}
    laufend = set()
    for wo in _alle_ordner(hier):
        stand = stand_lesen(wo)
        if stand.get("stand") != "laeuft":
            continue
        auftrag = stand.get("auftrag")
        if auftrag in offene:
            laufend.add(stand.get("projekt"))
            continue
        zeit = jetzt.isoformat(timespec="seconds")
        try:
            fertig = auftraege.erledigter(auftrag)
        except Exception:  # noqa: BLE001 – Auftrag fehlt: nicht ewig "läuft" anzeigen
            logger.exception("Rückmeldung %s: Auftrag %s nicht gefunden", wo.name, auftrag)
            stand_aendern(wo, stand="fehlgeschlagen", grund=f"Der Auftrag {auftrag} ist nicht mehr auffindbar.", aktualisiert=zeit)
            continue
        wert = ABSCHLUSS.get(fertig.get("status"), "fehlgeschlagen")
        ergebnis = fertig.get("ergebnis") or ""
        grund = {"fertig": None, "fehlgeschlagen": "Der Agent meldet einen Fehler.",
                 "zurueckgezogen": "Der Auftrag wurde gestoppt."}[wert]
        stand_aendern(wo, stand=wert, grund=grund, ergebnis=ergebnis, aktualisiert=zeit)
        logger.info("Rückmeldung %s: %s", wo.name, wert)
    return laufend


def _marke_lesen(pfad: Path) -> dict:
    marke = json.loads(pfad.read_text(encoding="utf-8"))
    gueltig = (isinstance(marke, dict) and ID.match(str(marke.get("id"))) and marke["id"] == pfad.stem
               and PROJEKT.match(str(marke.get("projekt"))) and AUFTRAG_ID.match(str(marke.get("kette"))))
    if not gueltig:
        raise ValueError("Felder ungültig")
    return marke


def _uebergeben(hier: Path, agent: str, auftraege, marke: dict, kommentare, jetzt: datetime) -> str:
    """Aus einer genommenen Marke den Auftrag machen. Vorher sichern: Ohne Kopie wird nichts überschrieben."""
    wo = ordner(hier, marke["projekt"], marke["id"])
    stand = stand_lesen(wo)
    pfad_text = wo / TEXT
    text = pfad_text.read_text(encoding="utf-8").strip() if pfad_text.is_file() else ""
    datei = wo / stand["datei"] if stand.get("datei") else None
    hinweis = None
    if datei:
        try:
            ohne_kommentare = not kommentare(datei)
        except Exception as f:  # noqa: BLE001 – kaputte Datei: Jan soll es erfahren
            logger.warning("Rückmeldung %s: Kommentare nicht lesbar: %s", marke["id"], f)
            if not text:
                raise UebergabeFehler(f"Die Datei ist nicht lesbar: {f}") from f
            ohne_kommentare = True
        if ohne_kommentare and not text:
            raise UebergabeFehler("In der Datei stehen keine Kommentare, und es kam kein Text mit. Es lief keine "
                                  "Überarbeitung. Eigene Word-Textänderungen gehören ins Textfeld.")
        if ohne_kommentare:
            hinweis = "In der Datei stehen keine lesbaren Kommentare, die Überarbeitung beruht auf deinem Text."
    erledigte = auftraege.erledigte(agent)
    ende = kettenende(erledigte, marke["kette"])
    if ende is None:
        raise UebergabeFehler(f"Zur Kette {marke['kette']} gibt es keinen Auftrag mit Sitzung.")
    vorher_sichern(hier, wo, marke["kette"])
    auftrag = auftraege.neuer_auftrag(agent, auftragstext(text, stand.get("datei")), quelle="portal", bezug=ende["id"],
                                      sitzung=ende["sitzung"], dateien=[datei] if datei else [], kopieren=True)
    stand_aendern(wo, stand="laeuft", grund=GRUND_LAEUFT, auftrag=auftrag, hinweis=hinweis,
                  aktualisiert=jetzt.isoformat(timespec="seconds"))
    logger.info("Rückmeldung %s: Auftrag %s in der Kette %s", marke["id"], auftrag, marke["kette"])
    return auftrag


def naechste_uebergeben(hier: Path, agent: str, auftraege, laufend: set[str], kommentare, melden, jetzt: datetime) -> int:
    """Je Projekt höchstens eine Marke zum Auftrag machen, wenn dort nichts läuft. Gibt die Zahl der neuen Aufträge zurück."""
    belegt, neu = set(laufend), 0
    for pfad in sorted(schlange(hier).glob("*.json")):
        try:
            marke = _marke_lesen(pfad)
        except FileNotFoundError:  # gerade zurückgenommen
            continue
        except ValueError as f:  # bliebe sonst für immer liegen
            logger.error("Marke %s ungültig, entfernt: %s", pfad.name, f)
            pfad.unlink(missing_ok=True)
            melden(f"Rückmeldung {pfad.stem}: Die Marke im Portal war ungültig und wurde entfernt ({f}).")
            continue
        if marke["projekt"] in belegt:
            continue
        if kette_offen(auftraege.neue(agent, dienst=None), auftraege.erledigte(agent), marke["kette"]):
            logger.info("Rückmeldung %s wartet: In der Kette %s ist noch ein Auftrag offen", marke["id"], marke["kette"])
            continue
        try:
            pfad.unlink()  # ab hier höchstens einmal, siehe oben
        except FileNotFoundError:  # zwischen Lesen und Nehmen zurückgenommen
            continue
        belegt.add(marke["projekt"])
        try:
            _uebergeben(hier, agent, auftraege, marke, kommentare, jetzt)
            neu += 1
        except Exception as f:  # noqa: BLE001 – eine Rückmeldung darf die anderen nicht blockieren
            logger.exception("Rückmeldung %s nicht übergeben", marke["id"])
            grund = str(f) if isinstance(f, UebergabeFehler) else f"Übergabe fehlgeschlagen: {type(f).__name__}: {f}"
            stand_aendern(ordner(hier, marke["projekt"], marke["id"]), stand="fehlgeschlagen", grund=grund,
                          aktualisiert=jetzt.isoformat(timespec="seconds"))
            melden(f"Rückmeldung {marke['id']} zum Exposé nicht übergeben: {grund}")
    return neu


def abarbeiten(hier: Path, agent: str, auftraege, auftraege_abarbeiten, kommentare, melden, zeit) -> None:
    """Endstände nachziehen, Marken übergeben, Aufträge abarbeiten, bis keine Marke mehr dran ist. Jede Runde mit neuem
    Auftrag verbraucht eine Marke, die Schleife endet also. Bleibt ein Auftrag bei knappem Kontingent liegen, gilt sein
    Projekt als belegt, und der nächste Lauf macht weiter."""
    while True:
        laufend = nachziehen(hier, agent, auftraege, zeit())
        if not naechste_uebergeben(hier, agent, auftraege, laufend, kommentare, melden, zeit()):
            return
        auftraege_abarbeiten()
