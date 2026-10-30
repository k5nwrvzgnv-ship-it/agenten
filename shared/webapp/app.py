"""Web-App für Lia: Seite "Heute" mit Ergebnis- und Entwurf-Ansicht, nur lesend, ohne Anmeldung.

Kein Port: Uvicorn hört auf einem Unix-Socket in data/ (Ordner nur für User agent), wie der Leitstand.
Zugriff zum Test per SSH-Tunnel:
  ssh -N -L 8792:/home/agent/agenten/shared/webapp/data/webapp.sock agents-user
und dann http://localhost:8792 im Browser.

Daten: Warteschlangen der Instanz WEBAPP_INSTANZ (Standard lia/instanz) über agentkit mit basis=.
Die App selbst läuft ohne AGENTKIT_INSTANZ. Logik in logik.py (getestet), hier nur Dateien und HTTP.

Nur GET:
  /                                     Seite Heute
  /teile/heute                          Inhalt von Heute (htmx lädt ihn jede Minute neu)
  /ergebnis/<id>                        Auftrag mit Feedback-Schleife: neueste Fassung und Verlauf (auch
                                        fehlgeschlagene mit Grund). IDs von Nachbesserungen und Rückmeldungen
                                        leiten auf den Ursprung um.
  /ergebnis/<id>/datei/<n>              Download der n-ten Ergebnisdatei
  /ergebnis/<id>/datei/<n>/pdf          PDF aus der Vorschau des Renderers
  /ergebnis/<id>/datei/<n>/seite/<m>    Seitenbild m (ab 1) der Vorschau
  /entwurf/<id>                         offener Entwurf, ganzer Text, keine Knöpfe
  /statisch/...                         CSS, htmx
IDs werden mit agentkit geprüft und nur in der Instanz gesucht. Dateien kommen nur über ihre Nummer in
ergebnis_dateien, nie über einen Pfad aus der URL; jeder Pfad wird gegen den Agent-Ordner geprüft (dateien.py).

Start: .venv/bin/python app.py   (Socket-Pfad änderbar mit WEBAPP_SOCKET)
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from agentkit import auftraege, config, freigabe
from agentkit._ablage import AblageFehler, pruefe_id

import dateien
import logik

HIER = Path(__file__).resolve().parent
SOCKET = Path(os.environ.get("WEBAPP_SOCKET") or HIER / "data" / "webapp.sock")
INSTANZ = Path(os.environ.get("WEBAPP_INSTANZ") or HIER.parent.parent / "lia" / "instanz")
ZONE = ZoneInfo("Europe/Berlin")
logger = logging.getLogger("webapp")

# Keine fremden Quellen (auch keine Google Fonts): Lias Gerät spricht nur mit diesem Server
KOPFZEILEN = {
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/statisch", StaticFiles(directory=HIER / "statisch"), name="statisch")
vorlagen = Jinja2Templates(directory=HIER / "vorlagen")


NICHT_GEFUNDEN = ('<!doctype html><html lang="de"><head><meta charset="utf-8">'
                  '<meta name="viewport" content="width=device-width, initial-scale=1"><title>Nicht gefunden</title>'
                  '<link rel="stylesheet" href="/statisch/stil.css"></head><body><main class="einzeln">'
                  '<header class="kopf"><a class="zurueck" href="/"><span aria-hidden="true">←</span>Zurück</a>'
                  '<h1 class="titel-gross">Nicht gefunden</h1></header>'
                  '<p class="absatz">Das gibt es hier nicht (mehr).</p></main></body></html>')


@app.exception_handler(StarletteHTTPException)
async def fehlerseite(request: Request, fehler: StarletteHTTPException):
    if fehler.status_code == 404:
        return HTMLResponse(NICHT_GEFUNDEN, status_code=404)
    return await http_exception_handler(request, fehler)


@app.middleware("http")
async def kopfzeilen(request: Request, call_next):
    antwort = await call_next(request)
    for name, wert in KOPFZEILEN.items():
        antwort.headers.setdefault(name, wert)
    return antwort


def heute_daten(instanz: Path | None = None) -> dict:
    instanz = instanz or INSTANZ
    return logik.heute(auftraege.neue(basis=instanz / "auftraege"),
                       auftraege.erledigte(basis=instanz / "auftraege"),
                       freigabe.offene(basis=instanz / "freigabe"),
                       datetime.now(ZONE), config.person(instanz))


@app.get("/", response_class=HTMLResponse)
def seite_heute(request: Request):
    return vorlagen.TemplateResponse(request, "heute.html", {"h": heute_daten()})


@app.get("/teile/heute", response_class=HTMLResponse)
def teil_heute(request: Request):
    return vorlagen.TemplateResponse(request, "_heute.html", {"h": heute_daten()})


def _auftrag(eintrag_id: str) -> dict:
    """Abgeschlossener Auftrag aus der Instanz, der eine Ergebnis-Ansicht hat; sonst 404."""
    try:
        auftrag = auftraege.erledigter(eintrag_id, basis=INSTANZ / "auftraege")  # prüft die ID (pruefe_id)
    except AblageFehler:
        raise HTTPException(404) from None
    if not logik.zeigbar(auftrag):
        raise HTTPException(404)
    return auftrag


def _ergebnisdatei(eintrag_id: str, nr: int) -> tuple[Path, str]:
    """Agent-Ordner und relativer Pfad der nr-ten Ergebnisdatei; sonst 404."""
    auftrag = _auftrag(eintrag_id)
    pfade = auftrag.get("ergebnis_dateien") or []
    wurzel = dateien.agent_ordner(INSTANZ, auftrag.get("agent"))
    if auftrag.get("status") != "erledigt" or wurzel is None or not 0 <= nr < len(pfade):
        raise HTTPException(404)
    return wurzel, pfade[nr]


def _ausliefern(pfad: Path | None, herunterladen: bool = True) -> FileResponse:
    if pfad is None:
        raise HTTPException(404)
    return FileResponse(pfad, filename=pfad.name if herunterladen else None)


@app.get("/ergebnis/{eintrag_id}", response_class=HTMLResponse)
def seite_ergebnis(request: Request, eintrag_id: str):
    try:
        auftrag = auftraege.erledigter(eintrag_id, basis=INSTANZ / "auftraege")  # prüft die ID (pruefe_id)
    except AblageFehler:
        raise HTTPException(404) from None
    if not (logik.zeigbar(auftrag) or auftrag.get("agent") == "feedback"):
        raise HTTPException(404)
    basis = INSTANZ / "auftraege"
    kette = logik.kette_von(eintrag_id, [*auftraege.neue(basis=basis), *auftraege.erledigte(basis=basis)])
    kopf = logik.kopf(kette)
    if not logik.zeigbar(kopf):  # z. B. Rückmeldung zu einem unbekannten Ergebnis
        raise HTTPException(404)
    if kopf["id"] != eintrag_id:
        return RedirectResponse(f"/ergebnis/{kopf['id']}", status_code=303)
    vorschauen = {a["id"]: dateien.vorschau_info(dateien.agent_ordner(INSTANZ, a.get("agent")),
                                                 a.get("ergebnis_dateien") or [])
                  for a in logik.fassungen(kette) if a.get("status") == "erledigt"}
    e = logik.ergebnis(kette, vorschauen, datetime.now(ZONE))
    return vorlagen.TemplateResponse(request, "ergebnis.html", {"e": e})


@app.get("/ergebnis/{eintrag_id}/datei/{nr:int}")
def datei_original(eintrag_id: str, nr: int):
    wurzel, relativ = _ergebnisdatei(eintrag_id, nr)
    return _ausliefern(dateien.sicher(wurzel, relativ, dateien.DOWNLOAD_ENDUNGEN))


@app.get("/ergebnis/{eintrag_id}/datei/{nr:int}/pdf")
def datei_pdf(eintrag_id: str, nr: int):
    wurzel, relativ = _ergebnisdatei(eintrag_id, nr)
    return _ausliefern(dateien.vorschau_pdf(wurzel, relativ))


@app.get("/ergebnis/{eintrag_id}/datei/{nr:int}/seite/{seite:int}")
def datei_seite(eintrag_id: str, nr: int, seite: int):
    wurzel, relativ = _ergebnisdatei(eintrag_id, nr)
    seiten = dateien.vorschau_seiten(wurzel, relativ)
    return _ausliefern(seiten[seite - 1] if 1 <= seite <= len(seiten) else None, herunterladen=False)


@app.get("/entwurf/{eintrag_id}", response_class=HTMLResponse)
def seite_entwurf(request: Request, eintrag_id: str):
    try:
        pruefe_id(eintrag_id)
    except AblageFehler:
        raise HTTPException(404) from None
    eintrag = next((e for e in freigabe.offene(basis=INSTANZ / "freigabe") if e.get("id") == eintrag_id), None)
    if eintrag is None:
        raise HTTPException(404)
    return vorlagen.TemplateResponse(request, "entwurf.html", {"e": logik.entwurf(eintrag, datetime.now(ZONE))})


def socket_vorbereiten(socket_pfad: Path = SOCKET) -> None:
    socket_pfad.parent.mkdir(parents=True, exist_ok=True)
    socket_pfad.parent.chmod(0o700)  # Uvicorn gibt dem Socket 0666, der Ordner hält andere Benutzer fern
    socket_pfad.unlink(missing_ok=True)  # Rest eines früheren Laufs


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    socket_vorbereiten()
    logger.info("Web-App hört auf %s, Instanz %s", SOCKET, INSTANZ)
    try:
        uvicorn.run(app, uds=str(SOCKET), log_level="info", proxy_headers=False, server_header=False)
    finally:
        SOCKET.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
