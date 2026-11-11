"""Arbeitsplatz: neutrale Web-Oberfläche über Jans Agenten (docs/arbeitsplatz-plan.md).

Drei Spalten wie Lias App (shared/webapp, Gestaltung „Modernist“, CSS/Schrift/htmx von dort kopiert): links der Baum
der Orte (agentkit.orte) mit „+ Seite“, Mitte die Seite des Orts mit Unterseiten und Dokumenten, rechts „Läuft gerade“.
„+ Neu“ öffnet die Galerie der aktiven Arten (agentkit.arten, shared/arbeitsplatz/arten.toml), das Formular je Art
legt einen Auftrag an (quelle="arbeitsplatz", ort, art, felder) und startet <agent>.service.

Seiten (GET): /  /ort/<id>  /seite/neu?eltern=<id>  /archiv  /neu?ort=<id>  /neu/<art>?ort=<id>  /dokument/<id>
  Dateien: /dokument/<id>/datei/<auftrag>/<nr>[/pdf|/seite/<n>]  /dokument/<id>/eigene/<n>
Formulare (POST): /seite/neu  /ort/<id>/umbenennen|verschieben|archivieren|wiederherstellen  /rueckgaengig  /neu/<art>
  /dokument/<id>/final|eigene|rueckmeldung (Rückmeldung geht an feedback.service, nur bei Arten mit rueckmeldung)
Ein Dokument ist eine Kette über bezug; Dateien kommen nur über Auftrag und Nummer in ergebnis_dateien, jeder Pfad
wird gegen den Agent-Ordner geprüft (dateien.py, Kopie aus shared/webapp).

Aufträge sind ausgeschaltet, bis ARBEITSPLATZ_AUFTRAEGE=echt gesetzt ist (Standard aus: Formular prüft, legt nichts
an). Orte pflegen geht immer (startet keinen Lauf).
Schutz ohne Konten (wie shared/webapp): Origin muss zum Host passen und das Formular-Token (geheim je Start) stimmen.
Zugang von außen nur über Caddy mit Passwort (macht Jan).

Start: .venv/bin/python app.py   (Unix-Socket data/arbeitsplatz.sock, änderbar mit ARBEITSPLATZ_SOCKET; mit
       ARBEITSPLATZ_PORT=8794 auf 127.0.0.1:8794, so läuft systemd/arbeitsplatz.service)
Instanz: ARBEITSPLATZ_INSTANZ (Standard: Jans shared-Ordner); orte.json, auftraege/, fassungen/ liegen dort.
"""

import json
import logging
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException

from agentkit import _ablage, arten, auftraege, config, fassungen, orte, verbrauch

import ansichten
import dateien
import logik
import vorschau

HIER = Path(__file__).resolve().parent
SOCKET = Path(os.environ.get("ARBEITSPLATZ_SOCKET") or HIER / "data" / "arbeitsplatz.sock")
PORT = os.environ.get("ARBEITSPLATZ_PORT", "")
INSTANZ = Path(os.environ.get("ARBEITSPLATZ_INSTANZ") or config.KONTINGENT_DIR)
AUFTRAEGE = os.environ.get("ARBEITSPLATZ_AUFTRAEGE", "aus")  # "aus" oder "echt"
ARTEN_DATEI = HIER / "arten.toml"
DATEN = HIER / "data"
UNIT_DIR = Path.home() / ".config" / "systemd" / "user"
GEHEIM = secrets.token_bytes(32)
ZONE = ZoneInfo("Europe/Berlin")
MAX_DATEIEN = 10
ENDUNGEN = (".pdf", ".docx", ".pptx", ".xlsx", ".txt", ".md", ".png", ".jpg", ".jpeg", ".vtt", ".srt", ".json")
QUELLE = "arbeitsplatz"
GELEGT = "gelegt-"  # Datei am Ort (umbauplan-ux.md Schritt 4): data/eingang/gelegt-<kennung>/ bis zum Auftrag
GELEGT_MUSTER = re.compile(r"[a-z0-9_]{6,16}")
GELEGT_ALTER = 24 * 3600  # Sekunden; Liegengebliebenes löscht das nächste Ablegen
logger = logging.getLogger("arbeitsplatz")

KOPFZEILEN = {
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",  # nicht no-referrer: Browser schicken sonst Origin: null (403)
    "Cache-Control": "no-store",
}
VERALTET = "Die Seite war zu alt. Bitte neu laden und noch einmal versuchen."
FEHLGESCHLAGEN = "Das ging gerade nicht. Bitte noch einmal versuchen; Einzelheiten stehen im Log."

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/statisch", StaticFiles(directory=HIER / "statisch"), name="statisch")
vorlagen = Jinja2Templates(directory=HIER / "vorlagen")
vorlagen.env.globals["formular_token"] = lambda: logik.formular_token(GEHEIM)
vorlagen.env.globals["einmal_kennung"] = lambda: secrets.token_hex(8)


def auftraege_an() -> bool:
    return AUFTRAEGE == "echt"


# --- Daten lesen -------------------------------------------------------------------------------------------------

def basis() -> Path:
    return INSTANZ / "auftraege"


def agenten_dir() -> Path:
    return INSTANZ.parent


def baum_laden() -> list[dict]:
    try:
        return orte.laden(INSTANZ)
    except orte.OrtFehler as f:
        logger.error("Orte nicht lesbar: %s", f)
        return []


def arten_laden() -> list[dict]:
    try:
        return arten.laden(ARTEN_DATEI, agenten_dir())
    except arten.ArtFehler as f:
        logger.error("Arten nicht lesbar: %s", f)
        return []


def arten_namen() -> dict[str, str]:
    return {a["kennung"]: a["name"] for a in arten_laden()}


def alle_auftraege() -> list[dict]:
    return auftraege.erledigte(basis=basis()) + auftraege.neue(basis=basis())


def finals() -> dict[str, dict | None]:
    """Ursprung -> final-Eintrag aus agentkit.fassungen (Dateien <instanz>/fassungen/<ursprung>.json)."""
    ergebnis = {}
    for pfad in (INSTANZ / "fassungen").glob("*.json"):
        try:
            ergebnis[pfad.stem] = _ablage.lies(pfad).get("final")
        except (OSError, ValueError) as f:
            logger.warning("Fassungen %s nicht lesbar: %s", pfad.name, f)
    return ergebnis


ZUORDNUNG = "orte-zuordnung.json"  # alte Ergebnisse ohne Feld ort -> Ort (die Aufträge bleiben unverändert)


def zuordnung() -> dict[str, str]:
    pfad = INSTANZ / ZUORDNUNG
    if not pfad.exists():
        return {}
    try:
        return logik.zuordnung_pruefen(json.loads(pfad.read_text(encoding="utf-8")))
    except (OSError, ValueError) as f:
        logger.error("%s nicht lesbar: %s", ZUORDNUNG, f)
        return {}


def heute_iso() -> str:
    return datetime.now(ZONE).date().isoformat()


def rahmen(baum: list[dict], aktiv: str | None, krumen: dict, neu_hier: str | None = "/neu") -> dict:
    """Baum, Brotkrumen, „+ Neu“ und „Läuft gerade“ für jede Seite."""
    namen = arten_namen()
    laeuft = logik.laufend(auftraege.neue(basis=basis()), namen)
    for z in laeuft:
        z["seit_text"] = logik.zeit_kurz(z["seit"], heute_iso())
    return {"baum": logik.baum_zeilen(baum, aktiv), "krumen": krumen, "neu_hier": neu_hier, "laeuft": laeuft,
            "auftraege_an": auftraege_an(), **kosten_spalte(namen)}


KOSTEN_ZEILEN = 6


def kosten_spalte(namen: dict[str, str]) -> dict:
    """Kosten heute (Jans Instanz) und die letzten Läufe für die rechte Spalte; Fehler: leer, im Log."""
    try:
        heute_ = verbrauch.heute()
        letzte = verbrauch.letzte(KOSTEN_ZEILEN)
    except OSError as f:
        logger.warning("Verbrauch nicht lesbar: %s", f)
        return {"kosten_heute": None, "kosten_letzte": []}
    ketten = logik.ketten(alle_auftraege())
    ursprung_von = {a["id"]: u for u, k in ketten.items() for a in k}
    titel = {u: logik.titel_von(k, namen) for u, k in ketten.items() if any(a["id"] in
             {e.get("auftrag") for e in letzte} for a in k)}
    summe = sum(w["usd"] for name, w in heute_.items() if "/" not in name)
    return {"kosten_heute": f"{summe:.2f}", "kosten_letzte": logik.kosten_zeilen(letzte, ursprung_von, titel)}


def seite(request: Request, vorlage: str, werte: dict, status: int = 200) -> HTMLResponse:
    return vorlagen.TemplateResponse(request, vorlage, {"token": logik.formular_token(GEHEIM), "fehler": [],
                                                        **werte}, status_code=status)


def ort_oder_404(baum: list[dict], ort_id: str) -> dict:
    k = next((k for k in baum if k["id"] == ort_id), None)
    if k is None:
        raise HTTPException(404)
    return k


# --- Rahmen, Fehler, Kopfzeilen ----------------------------------------------------------------------------------

@app.exception_handler(StarletteHTTPException)
async def fehlerseite(request: Request, fehler: StarletteHTTPException):
    if fehler.status_code == 404:
        baum = baum_laden()
        return seite(request, "meldung.html", {"e": {"titel": "Nicht gefunden"},
                                               "text": "Diese Seite gibt es nicht (mehr).",
                                               **rahmen(baum, None, {"teile": [{"text": "Heute", "link": "/"}],
                                                                     "hier": "Nicht gefunden"})}, 404)
    return await http_exception_handler(request, fehler)


@app.middleware("http")
async def kopfzeilen(request: Request, call_next):
    try:
        antwort = await call_next(request)
    finally:
        if (form := getattr(request.state, "formular", None)) is not None:
            await form.close()  # hochgeladene Dateien (temporär) schließen
    if request.url.path.startswith("/statisch/schrift/"):
        antwort.headers["Cache-Control"] = "public, max-age=2592000"
    for name, wert in KOPFZEILEN.items():
        antwort.headers.setdefault(name, wert)
    return antwort


async def formular(request: Request):
    """Formular lesen; fremde Herkunft: 403. Gibt (form, token_ok) zurück."""
    if not logik.herkunft_passt(request.headers.get("origin"), request.headers.get("host"),
                                request.headers.get("sec-fetch-site")):
        logger.warning("Formular %s von fremder Herkunft abgelehnt", request.url.path)
        raise HTTPException(403)
    form = await request.form(max_files=MAX_DATEIEN, max_fields=200)
    request.state.formular = form
    return form, logik.token_passt(GEHEIM, str(form.get("token") or ""))


_EINMAL: dict[str, str] = {}  # Formular-Kennung -> Ziel der Weiterleitung (Doppelklick schickt dieselbe Kennung)
EINMAL_MERKEN = 200


def einmal_ziel(request: Request, form) -> str | None:
    kennung = str(form.get("einmal") or "")
    return _EINMAL.get(f"{request.url.path}|{kennung}") if kennung else None


def einmal_merken(request: Request, form, ziel: str) -> None:
    if kennung := str(form.get("einmal") or ""):
        _EINMAL[f"{request.url.path}|{kennung}"] = ziel
        for alt in list(_EINMAL)[:-EINMAL_MERKEN]:
            del _EINMAL[alt]


def mit_aktion(ziel: str, aus: orte.Ausgang) -> RedirectResponse:
    trenner = "&" if "?" in ziel else "?"
    return RedirectResponse(f"{ziel}{trenner}aktion={quote(aus.aktion)}", status_code=303)


def aktion_hinweis(aktion_id: str | None) -> dict | None:
    """Text der Aktion für den Hinweis mit Rückgängig (nur bekannte Aktionen)."""
    if not aktion_id:
        return None
    try:
        letzte = orte.letzte(50, INSTANZ)
    except orte.OrtFehler:
        return None
    a = next((a for a in letzte if a["aktion"] == aktion_id), None)
    return {"id": a["aktion"], "text": a["text"]} if a else None


vorlagen.env.globals["aktion_hinweis"] = aktion_hinweis


# --- Heute, Ort, Archiv ------------------------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def seite_heute(request: Request):
    baum = baum_laden()
    namen = arten_namen()
    alle = alle_auftraege()
    docs = logik.dokumente(alle, None, namen, finals(), zuordnung())
    for d in docs:
        d["ort_text"] = logik.ort_text(baum, d["ort"])
        d["zeit_text"] = logik.zeit_kurz(d["zeit"], heute_iso())
    return seite(request, "heute.html", {"e": {"titel": "Heute"}, "zuletzt": docs[:15],
                                         "wartet": logik.wartet_auf_mich(docs, heute_iso()),
                                         "oben": orte.kinder(baum, None),
                                         **rahmen(baum, None, logik.krumen(baum, None))})


@app.get("/ort/{ort_id}", response_class=HTMLResponse)
def seite_ort(request: Request, ort_id: str):
    baum = baum_laden()
    k = ort_oder_404(baum, ort_id)
    docs = logik.dokumente(alle_auftraege(), ort_id, arten_namen(), finals(), zuordnung())
    for d in docs:
        d["zeit_text"] = logik.zeit_kurz(d["zeit"], heute_iso())
    return seite(request, "ort.html", {
        "e": {"titel": k["titel"]}, "ort": k, "archiviert": not orte.sichtbar(baum, ort_id),
        "unterseiten": orte.kinder(baum, ort_id), "dokumente": docs,
        "ziele": logik.ziele_zum_verschieben(baum, ort_id),
        "endungen": ",".join(ENDUNGEN), "max_dateien": MAX_DATEIEN,
        **rahmen(baum, ort_id, logik.krumen(baum, ort_id), f"/neu?ort={quote(ort_id)}")})


@app.get("/archiv", response_class=HTMLResponse)
def seite_archiv(request: Request):
    baum = baum_laden()
    eintraege = [{"ort": k, "pfad": logik.ort_text(baum, k["id"])} for k in orte.archiv(baum)]
    return seite(request, "archiv.html", {"e": {"titel": "Archiv"}, "eintraege": eintraege, **rahmen(
        baum, None, {"teile": [{"text": "Heute", "link": "/"}], "hier": "Archiv"})})


@app.get("/seite/neu", response_class=HTMLResponse)
def seite_seite_neu(request: Request, eltern: str = ""):
    baum = baum_laden()
    if eltern:
        ort_oder_404(baum, eltern)
    return _seite_neu(request, baum, eltern, "", [])


def _seite_neu(request: Request, baum: list[dict], eltern: str, titel: str, fehler: list[str], status: int = 200):
    krumen = logik.krumen(baum, eltern or None, "Neue Seite") if eltern else {
        "teile": [{"text": "Heute", "link": "/"}], "hier": "Neue Seite"}
    return seite(request, "seite_neu.html", {"e": {"titel": "Neue Seite"}, "eltern": eltern, "titel": titel,
                                             "fehler": fehler, **rahmen(baum, eltern or None, krumen)}, status)


async def _pflegen(aendern: Callable[[], orte.Ausgang]) -> tuple[orte.Ausgang | None, str]:
    try:
        return await run_in_threadpool(aendern), ""
    except orte.OrtFehler as f:
        return None, str(f)
    except OSError as f:
        logger.error("Orte nicht gespeichert: %s", f)
        return None, "Speichern ging gerade nicht. Bitte noch einmal versuchen."


@app.post("/seite/neu", response_class=HTMLResponse)
async def seite_neu(request: Request):
    form, token_ok = await formular(request)
    eltern, titel = str(form.get("eltern") or ""), str(form.get("titel") or "")
    baum = baum_laden()
    if eltern:
        ort_oder_404(baum, eltern)
    if not token_ok:
        return _seite_neu(request, baum, eltern, titel, [VERALTET], 400)
    if ziel := einmal_ziel(request, form):
        return RedirectResponse(ziel, status_code=303)
    aus, fehler = await _pflegen(lambda: orte.anlegen(titel, eltern or None, instanz=INSTANZ))
    if aus is None:
        return _seite_neu(request, baum, eltern, titel, [fehler], 400)
    logger.info("Ort %s angelegt", aus.id)
    antwort = mit_aktion(logik.ort_link(aus.id), aus)
    einmal_merken(request, form, antwort.headers["location"])
    return antwort


async def _ort_aendern(request: Request, ort_id: str, aendern: Callable[[object], orte.Ausgang],
                       ziel: str | None = None):
    form, token_ok = await formular(request)
    baum = baum_laden()
    ort_oder_404(baum, ort_id)
    zurueck = logik.ziel_sicher(str(form.get("zurueck") or ""), ziel or logik.ort_link(ort_id))
    if not token_ok:
        return _meldung(request, baum, "Nicht gespeichert", VERALTET, zurueck, 400)
    aus, fehler = await _pflegen(lambda: aendern(form))
    if aus is None:
        return _meldung(request, baum, "Nicht gespeichert", fehler, zurueck, 400)
    logger.info("Ort %s: %s", ort_id, aus.text)
    return mit_aktion(zurueck, aus)


def _meldung(request: Request, baum: list[dict], titel: str, text: str, zurueck: str, status: int):
    return seite(request, "meldung.html", {"e": {"titel": titel}, "text": text, "zurueck": zurueck, **rahmen(
        baum, None, {"teile": [{"text": "Heute", "link": "/"}], "hier": titel})}, status)


@app.post("/ort/{ort_id}/umbenennen", response_class=HTMLResponse)
async def ort_umbenennen(request: Request, ort_id: str):
    return await _ort_aendern(request, ort_id,
                              lambda f: orte.umbenennen(ort_id, str(f.get("titel") or ""), instanz=INSTANZ))


def _position(wert) -> int | None:
    text = str(wert or "")
    if not text:
        return None
    if not text.isdigit():
        raise orte.OrtFehler("Ungültige Position")
    return int(text)


@app.post("/ort/{ort_id}/verschieben", response_class=HTMLResponse)
async def ort_verschieben(request: Request, ort_id: str):
    return await _ort_aendern(request, ort_id, lambda f: orte.verschieben(
        ort_id, str(f.get("eltern") or "") or None, _position(f.get("position")), instanz=INSTANZ))


@app.post("/ort/{ort_id}/archivieren", response_class=HTMLResponse)
async def ort_archivieren(request: Request, ort_id: str):
    return await _ort_aendern(request, ort_id, lambda f: orte.archivieren(ort_id, instanz=INSTANZ), "/archiv")


@app.post("/ort/{ort_id}/wiederherstellen", response_class=HTMLResponse)
async def ort_wiederherstellen(request: Request, ort_id: str):
    return await _ort_aendern(request, ort_id, lambda f: orte.wiederherstellen(ort_id, instanz=INSTANZ))


@app.post("/rueckgaengig", response_class=HTMLResponse)
async def rueckgaengig(request: Request):
    form, token_ok = await formular(request)
    baum = baum_laden()
    zurueck = logik.ziel_sicher(str(form.get("zurueck") or ""))
    if not token_ok:
        return _meldung(request, baum, "Nicht rückgängig gemacht", VERALTET, zurueck, 400)
    aus, fehler = await _pflegen(lambda: orte.rueckgaengig(str(form.get("aktion") or ""), instanz=INSTANZ))
    if aus is None:
        return _meldung(request, baum, "Nicht rückgängig gemacht", fehler, zurueck, 400)
    # Die Seite des Orts gibt es nach Rückgängig von „Anlegen“ nicht mehr: dann nach Heute
    pfad = zurueck.split("?", 1)[0]
    if pfad.startswith("/ort/") and not any(logik.ort_link(k["id"]) == pfad for k in baum_laden()):
        zurueck = "/"
    return mit_aktion(zurueck, aus)


# --- Neu: Galerie und Formular -----------------------------------------------------------------------------------

def _ort_param(baum: list[dict], ort_id: str) -> dict | None:
    if not ort_id:
        return None
    return ort_oder_404(baum, ort_id)


def gelegt_ordner(kennung: str) -> Path | None:
    """Ordner der am Ort abgelegten Dateien (umbauplan-ux.md Schritt 4). Ungültig oder nicht (mehr) da: None."""
    if not GELEGT_MUSTER.fullmatch(kennung or ""):
        return None
    ordner = DATEN / "eingang" / f"{GELEGT}{kennung}"
    return ordner if ordner.is_dir() else None


def gelegt_dateien(kennung: str) -> list[Path]:
    ordner = gelegt_ordner(kennung)
    return sorted((p for p in ordner.iterdir() if p.is_file()), key=lambda p: p.name.casefold()) if ordner else []


def gelegt_aufraeumen(jetzt: float | None = None) -> None:
    """Abgelegte Dateien, aus denen nach GELEGT_ALTER kein Auftrag wurde, löschen (Fehler nur ins Log)."""
    jetzt = time.time() if jetzt is None else jetzt
    eingang = DATEN / "eingang"
    if not eingang.is_dir():
        return
    for ordner in eingang.glob(f"{GELEGT}*"):
        try:
            if ordner.is_dir() and jetzt - ordner.stat().st_mtime > GELEGT_ALTER:
                shutil.rmtree(ordner)
                logger.info("Abgelegte Dateien %s nach einem Tag gelöscht", ordner.name)
        except OSError as f:
            logger.warning("Abgelegte Dateien %s nicht gelöscht: %s", ordner.name, f)


@app.get("/neu", response_class=HTMLResponse)
def seite_galerie(request: Request, ort: str = "", datei: str = ""):
    baum = baum_laden()
    k = _ort_param(baum, ort)
    gelegt = gelegt_dateien(datei) if datei else []
    aktive = arten.aktive(arten_laden())
    return seite(request, "galerie.html", {
        "e": {"titel": "Was soll daraus werden?" if gelegt else "Neu"}, "ort": k, "ort_text": logik.ort_text(baum, ort),
        "arten": [a for a in aktive if a["material"] != "nein"] if gelegt else aktive,
        "datei": datei if gelegt else "", "gelegt": [p.name for p in gelegt], "gelegt_weg": bool(datei and not gelegt),
        **rahmen(baum, ort or None, logik.krumen(baum, ort or None, "Neu") if ort else
                 {"teile": [{"text": "Heute", "link": "/"}], "hier": "Neu"}, None)})


@app.post("/neu/datei", response_class=HTMLResponse)
async def datei_ablegen(request: Request):
    """Datei am Ort (umbauplan-ux.md Schritt 4): Dateien kurz ablegen, dann die Galerie „Was soll daraus werden?“.
    Steht vor /neu/{kennung}, damit „datei“ keine Art ist."""
    form, token_ok = await formular(request)
    baum = baum_laden()
    ort = str(form.get("ort") or "")
    _ort_param(baum, ort)
    zurueck = logik.ort_link(ort) if ort else "/"
    if not token_ok:
        return _meldung(request, baum, "Nicht abgelegt", VERALTET, zurueck, 400)
    if ziel := einmal_ziel(request, form):
        return RedirectResponse(ziel, status_code=303)
    await run_in_threadpool(gelegt_aufraeumen)
    hochgeladen = [d for d in form.getlist("dateien") if isinstance(d, UploadFile) and d.filename]
    if not hochgeladen:
        return _meldung(request, baum, "Nicht abgelegt", "Wähle eine Datei aus.", zurueck, 400)
    ordner, _, fehler = await _dateien_sichern(hochgeladen, GELEGT)
    if fehler:
        return _meldung(request, baum, "Nicht abgelegt", fehler, zurueck, 400)
    kennung = ordner.name.removeprefix(GELEGT)
    logger.info("%d Datei(en) als %s abgelegt", len(hochgeladen), ordner.name)
    ziel = f"/neu?{'ort=' + quote(ort) + '&' if ort else ''}datei={kennung}"
    einmal_merken(request, form, ziel)
    return RedirectResponse(ziel, status_code=303)


def _art_oder_404(kennung: str) -> dict:
    art = arten.finden(arten_laden(), kennung)
    if art is None or not art["aktiv"]:
        raise HTTPException(404)
    return art


def _formular_seite(request: Request, baum: list[dict], art: dict, ort: str, werte: dict, fehler: list[str],
                    status: int = 200, datei: str = ""):
    krumen = logik.krumen(baum, ort or None, art["name"]) if ort else {
        "teile": [{"text": "Heute", "link": "/"}, {"text": "Neu", "link": "/neu"}], "hier": art["name"]}
    gelegt = gelegt_dateien(datei) if datei and art["material"] != "nein" else []
    return seite(request, "formular.html", {
        "e": {"titel": art["name"]}, "art": art, "ort": ort, "ort_text": logik.ort_text(baum, ort),
        "werte": werte, "fehler": fehler, "orte_wahl": logik.ziele_zum_verschieben(baum, "")[1:],
        "datei": datei if gelegt else "", "gelegt": [p.name for p in gelegt],
        **rahmen(baum, ort or None, krumen, None)}, status)


@app.get("/neu/{kennung}", response_class=HTMLResponse)
def seite_formular(request: Request, kennung: str, ort: str = "", datei: str = ""):
    baum = baum_laden()
    _ort_param(baum, ort)
    return _formular_seite(request, baum, _art_oder_404(kennung), ort, {}, [], datei=datei)


async def _dateien_sichern(dateien: list[UploadFile], praefix: str = "",
                          schon: int = 0) -> tuple[Path | None, list[Path], str]:
    """Hochgeladene Dateien in einen eigenen Ordner unter data/eingang/ (agentkit verschiebt sie zum Agenten).
    praefix: Anfang des Ordnernamens (GELEGT für Datei am Ort); schon: Zahl schon gelegter Dateien, zählt zur Grenze.
    Gibt (Ordner, Pfade, Fehler) zurück."""
    dateien = [d for d in dateien if isinstance(d, UploadFile) and d.filename]
    if not dateien:
        return None, [], ""
    if len(dateien) + schon > MAX_DATEIEN:
        return None, [], f"Höchstens {MAX_DATEIEN} Dateien"
    (DATEN / "eingang").mkdir(parents=True, exist_ok=True)
    ordner = Path(tempfile.mkdtemp(dir=DATEN / "eingang", prefix=praefix or None))
    pfade = []
    for d in dateien:
        name = re.sub(r"[^\w.\- ]", "_", Path(d.filename).name).lstrip(".") or "datei"
        if Path(name).suffix.casefold() not in ENDUNGEN:
            shutil.rmtree(ordner)
            return None, [], f"{name}: nur {', '.join(e.lstrip('.') for e in ENDUNGEN)}"
        ziel, n = ordner / name, 2
        while ziel.exists():
            ziel, n = ordner / f"{Path(name).stem}-{n}{Path(name).suffix}", n + 1
        groesse = 0
        with open(ziel, "wb") as f:
            while block := await d.read(1 << 20):
                groesse += len(block)
                if groesse > _ablage.MAX_ANHANG_BYTES:
                    shutil.rmtree(ordner)
                    return None, [], f"{name} ist größer als {_ablage.MAX_ANHANG_BYTES // 2**20} MB"
                f.write(block)
        pfade.append(ziel)
    return ordner, pfade, ""


def dienst_starten(agent: str) -> bool:
    """<agent>.service ohne Warten starten. False, wenn es die Unit nicht gibt oder systemctl scheitert."""
    if not (UNIT_DIR / f"{agent}.service").exists():
        logger.error("Dienst %s.service gibt es nicht, Auftrag wartet", agent)
        return False
    try:
        subprocess.run(["systemctl", "--user", "start", "--no-block", f"{agent}.service"], check=True,
                       capture_output=True, text=True, timeout=30)
        return True
    except (OSError, subprocess.SubprocessError) as f:
        logger.error("Dienst %s.service nicht gestartet: %s", agent, f)
        return False


@app.post("/neu/{kennung}", response_class=HTMLResponse)
async def neuer_auftrag(request: Request, kennung: str):
    form, token_ok = await formular(request)
    art = _art_oder_404(kennung)
    baum = baum_laden()
    ort = str(form.get("ort") or "")
    _ort_param(baum, ort)
    eingabe = {f["name"]: str(form.get(f"feld-{i}") or "") for i, f in enumerate(art["feld"])}
    datei = str(form.get("datei") or "") if art["material"] != "nein" else ""
    if not token_ok:
        return _formular_seite(request, baum, art, ort, eingabe, [VERALTET], 400, datei)
    if ziel := einmal_ziel(request, form):
        return RedirectResponse(ziel, status_code=303)
    fehler = []
    try:
        werte = arten.formular_pruefen(art, eingabe)
    except arten.ArtFehler as f:
        fehler, werte = str(f).split("; "), eingabe
    hochgeladen = [d for d in form.getlist("dateien") if isinstance(d, UploadFile) and d.filename]
    gelegt = gelegt_dateien(datei) if datei else []
    if datei and not gelegt:
        fehler.append("Die abgelegte Datei ist nicht mehr da (nach einem Tag gelöscht). Bitte noch einmal wählen.")
        datei = ""
    fehler += arten.material_fehler(art, werte, len(hochgeladen) + len(gelegt))
    if not ort:
        fehler.append("Ort: bitte wählen, wo das Dokument liegen soll")
    if not auftraege_an():
        fehler.append("Aufträge sind gerade ausgeschaltet (ARBEITSPLATZ_AUFTRAEGE). Nichts angelegt.")
    if fehler:
        return _formular_seite(request, baum, art, ort, werte, fehler, 400, datei)
    ordner, pfade, fehler_datei = await _dateien_sichern(hochgeladen, schon=len(gelegt))
    if fehler_datei:
        return _formular_seite(request, baum, art, ort, werte, [fehler_datei], 400, datei)
    try:
        aid = await run_in_threadpool(lambda: auftraege.neuer_auftrag(
            art["agent"], arten.auftragstext(art, werte), quelle=QUELLE, ort=ort, art=art["kennung"], felder=werte,
            dateien=gelegt + pfade, basis=basis(), agenten_dir=agenten_dir()))
    except (auftraege.AuftragFehler, OSError) as f:
        logger.error("Auftrag %s nicht angelegt: %s", art["kennung"], f)
        return _formular_seite(request, baum, art, ort, werte, ["Anlegen ging gerade nicht. Bitte noch einmal."], 500,
                               datei)
    finally:
        if ordner is not None:
            shutil.rmtree(ordner, ignore_errors=True)
    if gelegt:  # agentkit hat sie verschoben; der leere Ordner geht mit
        shutil.rmtree(gelegt[0].parent, ignore_errors=True)
    gestartet = await run_in_threadpool(dienst_starten, art["agent"])
    logger.info("Auftrag %s (%s) an %s angelegt, Dienst %s", aid, art["kennung"], art["agent"],
                "gestartet" if gestartet else "nicht gestartet")
    ziel = f"{logik.ort_link(ort)}?erledigt={'auftrag' if gestartet else 'auftrag-wartet'}"
    einmal_merken(request, form, ziel)
    return RedirectResponse(ziel, status_code=303)


# --- Dokument ----------------------------------------------------------------------------------------------------

def _dokument(ursprung: str) -> tuple[list[dict], list[dict]]:
    """(Kette, Rückmeldungen an feedback) zum Ursprung; sonst 404. Nur Ketten, deren Ursprung ein Dokument ist."""
    try:
        _ablage.pruefe_id(ursprung)
    except _ablage.AblageFehler:
        raise HTTPException(404) from None
    alle = alle_auftraege()
    kette = logik.ketten(alle).get(ursprung)
    if not kette or kette[0]["id"] != ursprung:
        raise HTTPException(404)
    ids = {a["id"] for a in kette}
    rueck = [a for a in alle if a.get("agent") == "feedback" and a.get("bezug") in ids]
    return kette, rueck


def _stand(ursprung: str) -> dict:
    try:
        return fassungen.lesen(ursprung, basis=basis())
    except (fassungen.FassungFehler, OSError, ValueError) as f:
        logger.error("Fassungen zu %s nicht lesbar: %s", ursprung, f)
        return {"final": None, "eigene": []}


_VORSCHAUEN: dict[Path, vorschau.Vorschauen] = {}


def vorschauen() -> vorschau.Vorschauen:
    """Eigene Vorschauen in data/vorschau/ (umbauplan-ux.md Schritt 6); je DATEN eine (Tests ändern DATEN)."""
    return _VORSCHAUEN.setdefault(DATEN, vorschau.Vorschauen(DATEN / "vorschau"))


def datei_info(a: dict) -> list[tuple]:
    """Je Ergebnisdatei (darf ausgeliefert werden, PDF da, Seiten, Vorschau läuft). Ohne Renderer-Vorschau nimmt es
    die eigene und stößt sie an, wenn sie fehlt (läuft im Hintergrund, die Seite zeigt solange einen Hinweis)."""
    wurzel = dateien.agent_ordner(INSTANZ, a.get("agent"))
    pfade = a.get("ergebnis_dateien") or []
    info = []
    for nr, (relativ, (original, pdf, seiten)) in enumerate(zip(pfade, dateien.vorschau_info(wurzel, pfade),
                                                                  strict=False)):
        laeuft = False
        quelle = dateien.sicher(wurzel, relativ, vorschau.ENDUNGEN) if original and not seiten else None
        if quelle is not None:
            v = vorschauen()
            if eigene := v.seiten(a["id"], nr, quelle):
                seiten, pdf = len(eigene), pdf or v.pdf(a["id"], nr, quelle) is not None
            else:
                laeuft = v.anstossen(a["id"], nr, quelle)
        info.append((original, pdf, seiten, laeuft))
    return info


def _ansicht(kette: list[dict], rueck: list[dict]) -> dict:
    vorschauen_ = {a["id"]: datei_info(a) for a in kette if a.get("status") == "erledigt"}
    art = arten.finden(arten_laden(), kette[0].get("art") or "")
    try:
        kosten = verbrauch.kosten_je({a["id"] for a in kette} | {r["id"] for r in rueck})
    except OSError as f:
        logger.warning("Verbrauch nicht lesbar: %s", f)
        kosten = {}
    return logik.dokument_ansicht(kette, rueck, _stand(kette[0]["id"]), vorschauen_, kosten, art, heute_iso())


def _dokument_seite(request: Request, ursprung: str, offen: str = "", fehler: list[str] | None = None,
                    text: str = "", status: int = 200, ziel: dict | None = None):
    """ziel: Rückmeldung an einer Datei/Seite (logik.rueckmeldung_ziel); ohne aus der URL (?offen=rueckmeldung&…)."""
    kette, rueck = _dokument(ursprung)
    baum = baum_laden()
    namen = arten_namen()
    ort = logik.ort_von(kette[0], zuordnung())
    ort = ort if any(k["id"] == ort for k in baum) else None
    titel = logik.titel_von(kette, namen)
    marke, rot = logik.marke_von(kette, _stand(ursprung).get("final"))
    d = _ansicht(kette, rueck)
    art = arten.finden(arten_laden(), kette[0].get("art") or "")
    q = request.query_params
    if ziel is None and offen == "rueckmeldung":
        ziel = logik.rueckmeldung_ziel(kette, d, q.get("fassung"), q.get("datei"), q.get("seite"))
    return seite(request, "dokument.html", {"ziel": ziel if d["rueckmeldung_moeglich"] else None,
        "e": {"titel": titel}, "art": namen.get(kette[0].get("art") or "", ""), "marke": marke, "rot": rot,
        "d": d, "u": ursprung, "eigen": eigene_ansicht(request, kette, art, d["haupt"]),
        "md": markdown_von(kette, d["haupt"]), "offen": offen, "fehler": fehler or [], "text": text,
        "eigene_endungen": ",".join(sorted(dateien.EIGENE_ENDUNGEN)),
        "rueck_endungen": ",".join(sorted(dateien.RUECK_ENDUNGEN)),
        **rahmen(baum, ort, logik.krumen(baum, ort, titel), f"/neu?ort={quote(ort)}" if ort else "/neu")}, status)


@app.get("/dokument/{ursprung}", response_class=HTMLResponse)
def seite_dokument(request: Request, ursprung: str):
    return _dokument_seite(request, ursprung, request.query_params.get("offen") or "")


MAX_JSON = 20 * 2**20  # größere Dateien liest die Ansicht nicht


def _json(wurzel: Path, relativ: str, leer):
    """JSON-Datei im Agent-Ordner (geprüft wie Downloads), sonst leer."""
    pfad = dateien.sicher(wurzel, relativ, {".json"})
    if pfad is None or pfad.stat().st_size > MAX_JSON:
        return leer
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError) as f:
        logger.warning("%s nicht lesbar: %s", relativ, f)
        return leer
    return daten if isinstance(daten, type(leer)) else leer


def eigene_ansicht(request: Request, kette: list[dict], art: dict | None, haupt: dict | None) -> dict | None:
    """Abschnitt der eigenen Ansicht einer Art (recherche, pruefung, karten) aus daten.ansicht der neuesten fertigen
    Fassung, die eine hat. None: keine eigene Ansicht oder nichts zu zeigen."""
    name = (art or {}).get("ansicht") or ""
    if name not in ("recherche", "pruefung", "karten"):
        return None
    wurzel = dateien.agent_ordner(INSTANZ, kette[0].get("agent"))
    angabe = next(((a.get("daten") or {}).get("ansicht") for a in reversed(kette)
                   if a.get("status") == "erledigt" and (a.get("daten") or {}).get("ansicht")), None)
    if wurzel is None or angabe is None:
        return None
    q = request.query_params
    if name == "recherche":
        ordner = ansichten.recherche_ordner(angabe)
        geprueft = _json(wurzel, f"{ordner}/geprueft.json", {}) if ordner else {}
        if not geprueft:
            return {"name": name, "leer": True}
        return {"name": name, **ansichten.recherche(geprueft, q.get("ansicht"), q.get("status"), q.get("frage"))}
    mu = ansichten.modul_und_uebung(angabe)
    if mu is None:
        return None
    modul, uebung = mu
    if name == "karten" or uebung is None:
        return {"name": "karten", "modul": modul, "link": ansichten.portal_link(modul)}
    basis_ = f"data/lernen/{modul}"
    auswertung = _json(wurzel, f"{basis_}/uebungen/{uebung}/auswertung.json", {})
    if not auswertung:
        return {"name": name, "leer": True, "link": ansichten.portal_link(modul, uebung)}
    return {"name": name, "link": ansichten.portal_link(modul, uebung), **ansichten.pruefung(
        auswertung, _json(wurzel, f"{basis_}/uebungen/{uebung}/kartenstand.json", {}),
        _json(wurzel, f"{basis_}/pruefungsplan.json", {}), _json(wurzel, f"{basis_}/karten.json", []))}


MAX_MD = 2 * 2**20


def markdown_von(kette: list[dict], haupt: dict | None) -> list[dict]:
    """Inhalt der ersten .md-Datei der Hauptfassung als Blöcke (Recherchebericht von uni), sonst []."""
    if not haupt or haupt["art"] != "agent":
        return []
    a = next((a for a in kette if a["id"] == haupt["ref"]), None)
    wurzel = dateien.agent_ordner(INSTANZ, (a or {}).get("agent"))
    for rel in (a or {}).get("ergebnis_dateien") or []:
        if rel.lower().endswith(".md") and wurzel is not None:
            pfad = dateien.sicher(wurzel, rel, {".md"})
            if pfad is not None and pfad.stat().st_size <= MAX_MD:
                try:
                    return ansichten.markdown_bloecke(pfad.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError) as f:
                    logger.warning("%s nicht lesbar: %s", rel, f)
    return []


def _ergebnisdatei(ursprung: str, auftrag_id: str, nr: int) -> tuple[Path, str]:
    """Agent-Ordner und relativer Pfad der nr-ten Ergebnisdatei eines fertigen Auftrags der Kette; sonst 404."""
    kette, _ = _dokument(ursprung)
    a = next((a for a in kette if a["id"] == auftrag_id), None)
    pfade = (a or {}).get("ergebnis_dateien") or []
    wurzel = dateien.agent_ordner(INSTANZ, (a or {}).get("agent"))
    if a is None or a.get("status") != "erledigt" or wurzel is None or not 0 <= nr < len(pfade):
        raise HTTPException(404)
    return wurzel, pfade[nr]


def _ausliefern(pfad: Path | None, herunterladen: bool = True) -> FileResponse:
    if pfad is None:
        raise HTTPException(404)
    return FileResponse(pfad, filename=pfad.name if herunterladen else None)


@app.get("/dokument/{ursprung}/datei/{auftrag_id}/{nr:int}")
def datei_original(ursprung: str, auftrag_id: str, nr: int):
    wurzel, relativ = _ergebnisdatei(ursprung, auftrag_id, nr)
    return _ausliefern(dateien.sicher(wurzel, relativ, dateien.DOWNLOAD_ENDUNGEN))


def _seiten(wurzel: Path, relativ: str, auftrag_id: str, nr: int) -> list[Path]:
    """Seitenbilder: die des Renderers, sonst die eigenen (data/vorschau)."""
    if seiten := dateien.vorschau_seiten(wurzel, relativ):
        return seiten
    quelle = dateien.sicher(wurzel, relativ, vorschau.ENDUNGEN)
    return vorschauen().seiten(auftrag_id, nr, quelle) if quelle else []


@app.get("/dokument/{ursprung}/datei/{auftrag_id}/{nr:int}/pdf")
def datei_pdf(ursprung: str, auftrag_id: str, nr: int):
    wurzel, relativ = _ergebnisdatei(ursprung, auftrag_id, nr)
    pdf = dateien.sicher(wurzel, relativ, {".pdf"}) or dateien.vorschau_pdf(wurzel, relativ)
    if pdf is None and (quelle := dateien.sicher(wurzel, relativ, vorschau.ENDUNGEN)):
        pdf = vorschauen().pdf(auftrag_id, nr, quelle)
    return _ausliefern(pdf, herunterladen=False)


@app.get("/dokument/{ursprung}/datei/{auftrag_id}/{nr:int}/seite/{seite_nr:int}")
def datei_seite(ursprung: str, auftrag_id: str, nr: int, seite_nr: int):
    wurzel, relativ = _ergebnisdatei(ursprung, auftrag_id, nr)
    seiten = _seiten(wurzel, relativ, auftrag_id, nr)
    return _ausliefern(seiten[seite_nr - 1] if 1 <= seite_nr <= len(seiten) else None, herunterladen=False)


@app.get("/dokument/{ursprung}/datei/{auftrag_id}/{nr:int}/ansehen", response_class=HTMLResponse)
def datei_ansehen(request: Request, ursprung: str, auftrag_id: str, nr: int):
    """Seiten-Betrachter (umbauplan-ux.md Schritt 6): eine Seite groß, Vor/Zurück, Seitenzahlen, ohne JavaScript."""
    wurzel, relativ = _ergebnisdatei(ursprung, auftrag_id, nr)
    basis_link = f"/dokument/{ursprung}/datei/{auftrag_id}/{nr}"
    b = logik.betrachter(len(_seiten(wurzel, relativ, auftrag_id, nr)), request.query_params.get("seite"),
                         f"{basis_link}/ansehen")
    if b is None:
        raise HTTPException(404)
    kette, rueck = _dokument(ursprung)
    d = _ansicht(kette, rueck)
    x = next((x for f in d["fassungen"] if f["ref"] == auftrag_id for x in f["dateien"] if x["nr"] == nr), None)
    if x is None:
        raise HTTPException(404)
    baum = baum_laden()
    ort = logik.ort_von(kette[0], zuordnung())
    ort = ort if any(k["id"] == ort for k in baum) else None
    titel = logik.titel_von(kette, arten_namen())
    krumen = logik.krumen(baum, ort, x["name"])
    krumen["teile"].append({"text": titel, "link": f"/dokument/{ursprung}"})
    return seite(request, "ansehen.html", {
        "e": {"titel": x["name"]}, "b": b, "x": x, "u": ursprung, "ref": auftrag_id, "basis_link": basis_link,
        "rueck_link": (f"/dokument/{ursprung}?offen=rueckmeldung&fassung={auftrag_id}&datei={nr}&seite={b['seite']}"
                       "#rueckmeldung") if d["rueckmeldung_moeglich"] else "",
        **rahmen(baum, ort, krumen, None)})


@app.get("/dokument/{ursprung}/eigene/{n:int}")
def eigene_datei(ursprung: str, n: int):
    kette, _ = _dokument(ursprung)
    eintrag = next((e for e in _stand(ursprung).get("eigene") or [] if e.get("n") == n), None)
    wurzel = dateien.agent_ordner(INSTANZ, kette[0].get("agent"))
    if eintrag is None or wurzel is None:
        raise HTTPException(404)
    return _ausliefern(dateien.sicher(wurzel, str(eintrag.get("datei") or ""), dateien.RUECK_ENDUNGEN))


def _fertig(ursprung: str, was: str) -> RedirectResponse:
    return RedirectResponse(f"/dokument/{ursprung}?erledigt={was}", status_code=303)


@app.post("/dokument/{ursprung}/final", response_class=HTMLResponse)
async def dokument_final(request: Request, ursprung: str):
    form, token_ok = await formular(request)
    kette, rueck = _dokument(ursprung)
    if not token_ok:
        return _dokument_seite(request, ursprung, fehler=[VERALTET], status=400)
    ref, an = str(form.get("ref") or ""), form.get("an") == "1"
    if not logik.final_erlaubt(ref, _ansicht(kette, rueck)):
        raise HTTPException(404)
    try:
        await run_in_threadpool(fassungen.final_setzen, ursprung, ref if an else None, basis())
    except (fassungen.FassungFehler, OSError) as f:
        logger.error("Final nicht gespeichert: %s", f)
        return _dokument_seite(request, ursprung, fehler=[FEHLGESCHLAGEN], status=500)
    logger.info("Final %s: %s (%s)", "an" if an else "aus", ursprung, ref)
    return _fertig(ursprung, "final" if an else "nicht-final")


async def _upload_sichern(upload: UploadFile) -> Path:
    """Upload unter seinem bereinigten Namen in einen neuen Ordner unter data/eingang/ (agentkit verschiebt ihn)."""
    (DATEN / "eingang").mkdir(parents=True, exist_ok=True)
    ziel = Path(tempfile.mkdtemp(dir=DATEN / "eingang")) / logik.dateiname_bereinigen(upload.filename or "")
    groesse = 0
    with open(ziel, "wb") as f:
        while block := await upload.read(1 << 20):
            groesse += len(block)
            if groesse > _ablage.MAX_ANHANG_BYTES:
                f.close()
                shutil.rmtree(ziel.parent, ignore_errors=True)
                raise ValueError(f"Datei größer als {_ablage.MAX_ANHANG_BYTES // 2**20} MB")
            f.write(block)
    return ziel


@app.post("/dokument/{ursprung}/eigene", response_class=HTMLResponse)
async def dokument_eigene(request: Request, ursprung: str):
    form, token_ok = await formular(request)
    _dokument(ursprung)
    datei = form.get("datei")
    if not token_ok:
        return _dokument_seite(request, ursprung, "eigene", [VERALTET], status=400)
    if not isinstance(datei, UploadFile) or not datei.filename:
        return _dokument_seite(request, ursprung, "eigene", ["Wähle eine Datei aus."], status=400)
    if fehler := logik.datei_erlaubt(datei.filename, dateien.EIGENE_ENDUNGEN):
        return _dokument_seite(request, ursprung, "eigene", [fehler], status=400)
    if ziel := einmal_ziel(request, form):
        return RedirectResponse(ziel, status_code=303)
    try:
        pfad = await _upload_sichern(datei)
        try:
            await run_in_threadpool(lambda: fassungen.eigene_dazu(ursprung, pfad, str(form.get("notiz") or "")[:500],
                                                                  basis=basis(), agenten_dir=agenten_dir()))
        finally:
            shutil.rmtree(pfad.parent, ignore_errors=True)
    except ValueError as f:
        return _dokument_seite(request, ursprung, "eigene", [str(f)], status=400)
    except (fassungen.FassungFehler, OSError) as f:
        logger.error("Eigene Fassung zu %s nicht gespeichert: %s", ursprung, f)
        return _dokument_seite(request, ursprung, "eigene", [FEHLGESCHLAGEN], status=500)
    logger.info("Eigene Fassung zu %s gespeichert", ursprung)
    antwort = _fertig(ursprung, "eigene")
    einmal_merken(request, form, antwort.headers["location"])
    return antwort


@app.post("/dokument/{ursprung}/rueckmeldung", response_class=HTMLResponse)
async def dokument_rueckmeldung(request: Request, ursprung: str):
    form, token_ok = await formular(request)
    kette, rueck = _dokument(ursprung)
    datei = form.get("datei")
    datei = datei if isinstance(datei, UploadFile) and datei.filename else None
    text = str(form.get("text") or "")
    ansicht = _ansicht(kette, rueck)
    ziel = logik.rueckmeldung_ziel(kette, ansicht, str(form.get("fassung") or ""), str(form.get("dnr") or ""),
                                   str(form.get("seite") or ""))
    if not token_ok:
        return _dokument_seite(request, ursprung, "rueckmeldung", [VERALTET], text, 400, ziel)
    if not ansicht["rueckmeldung_moeglich"]:
        raise HTTPException(404)
    text, fehler = logik.rueckmeldung_pruefen(text, datei is not None)
    if datei and (f := logik.datei_erlaubt(datei.filename, dateien.RUECK_ENDUNGEN)):
        fehler.append(f)
    if not auftraege_an():
        fehler.append("Aufträge sind gerade ausgeschaltet (ARBEITSPLATZ_AUFTRAEGE). Nichts angelegt.")
    if fehler:
        return _dokument_seite(request, ursprung, "rueckmeldung", fehler, text, 400, ziel)
    if weiter := einmal_ziel(request, form):
        return RedirectResponse(weiter, status_code=303)
    # an einer Datei: die Fassung, aus der sie stammt (die Nachbesserung setzt dort auf); sonst die neueste fertige
    bezug = ziel["fassung"] if ziel else ansicht["bezug"]
    try:
        pfad = await _upload_sichern(datei) if datei else None
        try:
            fid, _ = await run_in_threadpool(lambda: fassungen.rueckmeldung(
                bezug, logik.rueckmeldung_text(text, ziel), pfad, basis=basis(), agenten_dir=agenten_dir()))
        finally:
            if pfad:
                shutil.rmtree(pfad.parent, ignore_errors=True)
    except ValueError as f:
        return _dokument_seite(request, ursprung, "rueckmeldung", [str(f)], text, 400, ziel)
    except (fassungen.FassungFehler, auftraege.AuftragFehler, OSError) as f:
        logger.error("Rückmeldung zu %s nicht angelegt: %s", ursprung, f)
        return _dokument_seite(request, ursprung, "rueckmeldung", [FEHLGESCHLAGEN], text, 500, ziel)
    gestartet = await run_in_threadpool(dienst_starten, "feedback")
    logger.info("Rückmeldung %s zu %s angelegt (Datei: %s, Ziel: %s)", fid, bezug, "ja" if datei else "nein",
                "ja" if ziel else "nein")
    antwort = _fertig(ursprung, "rueckmeldung" if gestartet else "rueckmeldung-wartet")
    einmal_merken(request, form, antwort.headers["location"])
    return antwort


# --- Start -------------------------------------------------------------------------------------------------------

def socket_vorbereiten(socket_pfad: Path = SOCKET) -> None:
    socket_pfad.parent.mkdir(parents=True, exist_ok=True)
    socket_pfad.parent.chmod(0o700)  # Uvicorn gibt dem Socket 0666, der Ordner hält andere Benutzer fern
    socket_pfad.unlink(missing_ok=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if AUFTRAEGE not in ("aus", "echt"):
        raise SystemExit(f"ARBEITSPLATZ_AUFTRAEGE={AUFTRAEGE!r}: nur aus oder echt")
    port = logik.port_pruefen(PORT)
    wo = f"127.0.0.1:{port}" if port else str(SOCKET)
    logger.info("Arbeitsplatz hört auf %s, Instanz %s, Aufträge: %s", wo, INSTANZ, AUFTRAEGE)
    arten_laden()  # Fehler in arten.toml gleich beim Start ins Log
    if port:
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info", proxy_headers=False, server_header=False)
        return
    socket_vorbereiten()
    try:
        uvicorn.run(app, uds=str(SOCKET), log_level="info", proxy_headers=False, server_header=False)
    finally:
        SOCKET.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
