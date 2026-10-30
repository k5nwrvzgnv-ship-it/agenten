"""Web-App für Lia, Bauschritt 1: Seite "Heute", nur lesend, ohne Anmeldung.

Kein Port: Uvicorn hört auf einem Unix-Socket in data/ (Ordner nur für User agent), wie der Leitstand.
Zugriff zum Test per SSH-Tunnel:
  ssh -N -L 8792:/home/agent/agenten/shared/webapp/data/webapp.sock agent@<server>
und dann http://localhost:8792 im Browser.

Daten: Warteschlangen der Instanz WEBAPP_INSTANZ (Standard lia/instanz) über agentkit mit basis=.
Die App selbst läuft ohne AGENTKIT_INSTANZ. Logik in logik.py (getestet), hier nur Dateien und HTTP.

Nur GET:
  /              Seite Heute
  /teile/heute   Inhalt von Heute (htmx lädt ihn jede Minute neu)
  /statisch/...  CSS, htmx

Start: .venv/bin/python app.py   (Socket-Pfad änderbar mit WEBAPP_SOCKET)
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agentkit import auftraege, config, freigabe

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
