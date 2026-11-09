"""Arbeitsplatz: neutrale Web-Oberfläche über Jans Agenten (docs/arbeitsplatz-plan.md).

Drei Spalten wie Lias App (shared/webapp, Gestaltung „Modernist“, CSS/Schrift/htmx von dort kopiert): links der Baum
der Orte (agentkit.orte) mit „+ Seite“, Mitte die Seite des Orts mit Unterseiten und Dokumenten, rechts „Läuft gerade“.
„+ Neu“ öffnet die Galerie der aktiven Arten (agentkit.arten, shared/arbeitsplatz/arten.toml), das Formular je Art
legt einen Auftrag an (quelle="arbeitsplatz", ort, art, felder) und startet <agent>.service.

Seiten (GET): /  /ort/<id>  /seite/neu?eltern=<id>  /archiv  /neu?ort=<id>  /neu/<art>?ort=<id>  /dokument/<id>
Formulare (POST): /seite/neu  /ort/<id>/umbenennen|verschieben|archivieren|wiederherstellen  /rueckgaengig  /neu/<art>

Aufträge sind ausgeschaltet, bis ARBEITSPLATZ_AUFTRAEGE=echt gesetzt ist (Standard aus: Formular prüft, legt nichts
an). Orte pflegen geht immer (startet keinen Lauf).
Schutz ohne Konten (wie shared/webapp): Origin muss zum Host passen und das Formular-Token (geheim je Start) stimmen.
Zugang von außen nur über Caddy mit Passwort (macht Jan).

Start: .venv/bin/python app.py   (Unix-Socket data/arbeitsplatz.sock, änderbar mit ARBEITSPLATZ_SOCKET; mit
       ARBEITSPLATZ_PORT=8794 auf 127.0.0.1:8794, so läuft systemd/arbeitsplatz.service)
Instanz: ARBEITSPLATZ_INSTANZ (Standard: Jans shared-Ordner); orte.json, auftraege/, fassungen/ liegen dort.
"""

import logging
import os
import re
import secrets
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException

from agentkit import _ablage, arten, auftraege, config, orte

import logik

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
logger = logging.getLogger("arbeitsplatz")

KOPFZEILEN = {
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",  # nicht no-referrer: Browser schicken sonst Origin: null (403)
    "Cache-Control": "no-store",
}
VERALTET = "Die Seite war zu alt. Bitte neu laden und noch einmal versuchen."

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


def heute_iso() -> str:
    return datetime.now(ZONE).date().isoformat()


def rahmen(baum: list[dict], aktiv: str | None, krumen: dict, neu_hier: str | None = "/neu") -> dict:
    """Baum, Brotkrumen, „+ Neu“ und „Läuft gerade“ für jede Seite."""
    namen = arten_namen()
    laeuft = logik.laufend(auftraege.neue(basis=basis()), namen)
    for z in laeuft:
        z["seit_text"] = logik.zeit_kurz(z["seit"], heute_iso())
    return {"baum": logik.baum_zeilen(baum, aktiv), "krumen": krumen, "neu_hier": neu_hier, "laeuft": laeuft,
            "auftraege_an": auftraege_an()}


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
    antwort = await call_next(request)
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
    docs = logik.dokumente(alle, None, namen, finals())
    for d in docs:
        d["ort_text"] = logik.ort_text(baum, d["ort"])
        d["zeit_text"] = logik.zeit_kurz(d["zeit"], heute_iso())
    return seite(request, "heute.html", {"e": {"titel": "Heute"}, "zuletzt": docs[:15],
                                         "oben": orte.kinder(baum, None),
                                         **rahmen(baum, None, logik.krumen(baum, None))})


@app.get("/ort/{ort_id}", response_class=HTMLResponse)
def seite_ort(request: Request, ort_id: str):
    baum = baum_laden()
    k = ort_oder_404(baum, ort_id)
    docs = logik.dokumente(alle_auftraege(), ort_id, arten_namen(), finals())
    for d in docs:
        d["zeit_text"] = logik.zeit_kurz(d["zeit"], heute_iso())
    return seite(request, "ort.html", {
        "e": {"titel": k["titel"]}, "ort": k, "archiviert": not orte.sichtbar(baum, ort_id),
        "unterseiten": orte.kinder(baum, ort_id), "dokumente": docs,
        "ziele": logik.ziele_zum_verschieben(baum, ort_id),
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


@app.get("/neu", response_class=HTMLResponse)
def seite_galerie(request: Request, ort: str = ""):
    baum = baum_laden()
    k = _ort_param(baum, ort)
    return seite(request, "galerie.html", {
        "e": {"titel": "Neu"}, "ort": k, "ort_text": logik.ort_text(baum, ort),
        "arten": arten.aktive(arten_laden()),
        **rahmen(baum, ort or None, logik.krumen(baum, ort or None, "Neu") if ort else
                 {"teile": [{"text": "Heute", "link": "/"}], "hier": "Neu"}, None)})


def _art_oder_404(kennung: str) -> dict:
    art = arten.finden(arten_laden(), kennung)
    if art is None or not art["aktiv"]:
        raise HTTPException(404)
    return art


def _formular_seite(request: Request, baum: list[dict], art: dict, ort: str, werte: dict, fehler: list[str],
                    status: int = 200):
    krumen = logik.krumen(baum, ort or None, art["name"]) if ort else {
        "teile": [{"text": "Heute", "link": "/"}, {"text": "Neu", "link": "/neu"}], "hier": art["name"]}
    return seite(request, "formular.html", {
        "e": {"titel": art["name"]}, "art": art, "ort": ort, "ort_text": logik.ort_text(baum, ort),
        "werte": werte, "fehler": fehler, "orte_wahl": logik.ziele_zum_verschieben(baum, "")[1:],
        **rahmen(baum, ort or None, krumen, None)}, status)


@app.get("/neu/{kennung}", response_class=HTMLResponse)
def seite_formular(request: Request, kennung: str, ort: str = ""):
    baum = baum_laden()
    _ort_param(baum, ort)
    return _formular_seite(request, baum, _art_oder_404(kennung), ort, {}, [])


async def _dateien_sichern(dateien: list[UploadFile]) -> tuple[Path | None, list[Path], str]:
    """Hochgeladene Dateien in einen eigenen Ordner unter data/eingang/ (agentkit verschiebt sie zum Agenten).
    Gibt (Ordner, Pfade, Fehler) zurück."""
    dateien = [d for d in dateien if isinstance(d, UploadFile) and d.filename]
    if not dateien:
        return None, [], ""
    if len(dateien) > MAX_DATEIEN:
        return None, [], f"Höchstens {MAX_DATEIEN} Dateien"
    (DATEN / "eingang").mkdir(parents=True, exist_ok=True)
    ordner = Path(tempfile.mkdtemp(dir=DATEN / "eingang"))
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
    if not token_ok:
        return _formular_seite(request, baum, art, ort, eingabe, [VERALTET], 400)
    if ziel := einmal_ziel(request, form):
        return RedirectResponse(ziel, status_code=303)
    fehler = []
    try:
        werte = arten.formular_pruefen(art, eingabe)
    except arten.ArtFehler as f:
        fehler, werte = str(f).split("; "), eingabe
    hochgeladen = [d for d in form.getlist("dateien") if isinstance(d, UploadFile) and d.filename]
    fehler += arten.material_fehler(art, werte, len(hochgeladen))
    if not ort:
        fehler.append("Ort: bitte wählen, wo das Dokument liegen soll")
    if not auftraege_an():
        fehler.append("Aufträge sind gerade ausgeschaltet (ARBEITSPLATZ_AUFTRAEGE). Nichts angelegt.")
    if fehler:
        return _formular_seite(request, baum, art, ort, werte, fehler, 400)
    ordner, pfade, fehler_datei = await _dateien_sichern(hochgeladen)
    if fehler_datei:
        return _formular_seite(request, baum, art, ort, werte, [fehler_datei], 400)
    try:
        aid = await run_in_threadpool(lambda: auftraege.neuer_auftrag(
            art["agent"], arten.auftragstext(art, werte), quelle=QUELLE, ort=ort, art=art["kennung"], felder=werte,
            dateien=pfade, basis=basis(), agenten_dir=agenten_dir()))
    except (auftraege.AuftragFehler, OSError) as f:
        logger.error("Auftrag %s nicht angelegt: %s", art["kennung"], f)
        return _formular_seite(request, baum, art, ort, werte, ["Anlegen ging gerade nicht. Bitte noch einmal."], 500)
    finally:
        if ordner is not None:
            shutil.rmtree(ordner, ignore_errors=True)
    gestartet = await run_in_threadpool(dienst_starten, art["agent"])
    logger.info("Auftrag %s (%s) an %s angelegt, Dienst %s", aid, art["kennung"], art["agent"],
                "gestartet" if gestartet else "nicht gestartet")
    ziel = f"{logik.ort_link(ort)}?erledigt={'auftrag' if gestartet else 'auftrag-wartet'}"
    einmal_merken(request, form, ziel)
    return RedirectResponse(ziel, status_code=303)


# --- Dokument (erste, lesende Fassung; die volle Ansicht kommt in Schritt 4) ------------------------------------

@app.get("/dokument/{ursprung}", response_class=HTMLResponse)
def seite_dokument(request: Request, ursprung: str):
    try:
        _ablage.pruefe_id(ursprung)
    except _ablage.AblageFehler:
        raise HTTPException(404) from None
    baum = baum_laden()
    namen = arten_namen()
    kette = logik.ketten(alle_auftraege()).get(ursprung)
    if not kette or kette[0]["id"] != ursprung:
        raise HTTPException(404)
    ort = kette[0].get("ort") if any(k["id"] == kette[0].get("ort") for k in baum) else None
    titel = logik.titel_von(kette, namen)
    marke, rot = logik.marke_von(kette, finals().get(ursprung))
    fassungen_ = [{"id": a["id"], "status": a.get("status"), "zeit": logik.zeit_kurz(
        a.get("abgeschlossen") or a.get("erstellt") or "", heute_iso()), "kern": (a.get("daten") or {}).get("kern", ""),
        "ergebnis": a.get("ergebnis", ""), "dateien": [logik.dateiname(p) for p in a.get("ergebnis_dateien") or []],
        "text": a.get("text", "")} for a in kette]
    return seite(request, "dokument.html", {
        "e": {"titel": titel}, "art": namen.get(kette[0].get("art") or "", ""), "marke": marke, "rot": rot,
        "fassungen": list(reversed(fassungen_)),
        **rahmen(baum, ort, logik.krumen(baum, ort, titel), f"/neu?ort={quote(ort)}" if ort else "/neu")})


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
