"""Uni-Portal: Prüfungsseite und Karten üben. Hört nur auf 127.0.0.1, von außen über Caddy (HTTPS, Passwort).

Schutz (webapp-plan.md, Abschnitt 7): lädt uni/.env nicht, liest nur die Positivliste aus ablage.py, handelt nie
nach außen, ruft Claude nicht auf. Karten üben kostet also kein Kontingent. Logik ohne Netz steht in logik.py.

Seiten:
  /                                  weiter zum Modul
  /modul/<modul>                     Prüfungsform, Themen mit Score und Lernstand, Liste "fehlt"
  /modul/<modul>/ueben               nächste Karte
  /modul/<modul>/bewerten            POST: Bewertung speichern
  /modul/<modul>/bild/<karte>/<art>  Bild der Karte (frage oder ganz)
"""

import logging
import os
import secrets
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

import uvicorn
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

HIER = Path(__file__).resolve().parent
sys.path.append(str(HIER.parent))  # lernmodell.py liegt in uni/; hinten, damit eigene Namen vorgehen

import lernmodell  # noqa: E402

import ablage  # noqa: E402
import logik  # noqa: E402

UNI = HIER.parent
DATEN = HIER / "data"  # nur die Sitzung des Portals
PORT = os.environ.get("PORTAL_PORT", "8793")
GEHEIM = secrets.token_bytes(32)  # für das Formular-Token, neu bei jedem Start
ZONE = ZoneInfo("Europe/Berlin")
SPERRE = threading.Lock()  # Lesen, Bewerten und Sitzung schreiben gehören zusammen
logger = logging.getLogger("uni-portal")

# Wie Lias App (shared/webapp/app.py): keine fremden Quellen, kein Zwischenspeichern
KOPFZEILEN = {
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",  # nicht no-referrer: Browser schicken damit bei Formularen Origin: null (403)
    "Cache-Control": "no-store",
}

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/statisch", StaticFiles(directory=HIER / "statisch"), name="statisch")
vorlagen = Jinja2Templates(directory=HIER / "vorlagen")


@app.middleware("http")
async def kopfzeilen(request: Request, call_next):
    antwort = await call_next(request)
    if request.url.path.startswith("/statisch/schrift/"):  # no-store ließe die Schrift bei jedem Seitenwechsel neu laden
        antwort.headers["Cache-Control"] = "public, max-age=2592000"
    for name, wert in KOPFZEILEN.items():
        antwort.headers.setdefault(name, wert)
    return antwort


def _jetzt() -> datetime:
    return datetime.now(ZONE)


def _modul(modul: str) -> lernmodell.Modul:
    m = ablage.modul_laden(UNI, modul)
    if m is None:
        raise HTTPException(404)
    return m


def _sitzung_datei(modul: str) -> Path:
    return DATEN / f"sitzung_{modul}.json"


def _sitzung(m: lernmodell.Modul, modul: str, jetzt: datetime) -> dict:
    return logik.sitzung_holen(lernmodell.lies_json(_sitzung_datei(modul), None), m, modul, jetzt)


def _sitzung_schreiben(modul: str, s: dict) -> None:
    DATEN.mkdir(mode=0o700, exist_ok=True)
    lernmodell.schreibe_json(_sitzung_datei(modul), s)


def _rahmen(modul: str) -> dict:
    return {"module": [{"id": i, "name": n} for i, n in ablage.MODULE.items()], "aktiv": modul, "modul": modul,
            "name": ablage.MODULE[modul]}


@app.get("/")
def start():
    return RedirectResponse(f"/modul/{next(iter(ablage.MODULE))}", status_code=303)


@app.get("/modul/{modul}")
def pruefungsseite(request: Request, modul: str):
    m = _modul(modul)
    plan = ablage.plan_lesen(UNI, modul)
    return vorlagen.TemplateResponse(request, "modul.html", {
        **_rahmen(modul), "plan": plan, "themen": logik.themen_ansicht(plan, m),
        "ueberblick": logik.ueberblick(m, _jetzt())})


@app.get("/modul/{modul}/ueben")
def ueben(request: Request, modul: str):
    with SPERRE:
        m = _modul(modul)
        jetzt = _jetzt()
        s = _sitzung(m, modul, jetzt)
        _sitzung_schreiben(modul, s)
    karte = m.karten[s["warteschlange"][0]] if s["warteschlange"] else None
    daten = {**_rahmen(modul), "sitzung": s, "karte": karte, "offen": len(s["warteschlange"]),
             "veraltet": request.query_params.get("veraltet") == "1", "token": logik.formular_token(GEHEIM),
             "bewertungen": lernmodell.BEWERTUNGEN}
    if karte:
        daten["thema"] = m.themen.get(karte["thema"], {}).get("titel", karte["thema"])
        daten["score"] = m.score(karte["thema"])
        daten["hat_bild"] = ablage.bild_pfad(UNI, modul, karte.get("bild")) is not None
        daten["hat_ganzes"] = ablage.bild_pfad(UNI, modul, logik.ganzes_bild(karte.get("bild"))) is not None
    return vorlagen.TemplateResponse(request, "ueben.html", daten)


@app.post("/modul/{modul}/bewerten")
def bewerten(request: Request, modul: str, token: Annotated[str, Form()] = "", karte: Annotated[str, Form()] = "",
             nr: Annotated[str, Form()] = "", bewertung: Annotated[str, Form()] = ""):
    if not logik.herkunft_passt(request.headers.get("origin"), request.headers.get("host"),
                                request.headers.get("sec-fetch-site")):
        raise HTTPException(403, "Formular kommt nicht von dieser Seite")
    if not logik.token_passt(GEHEIM, token):  # Dienst wurde neu gestartet, die Seite ist alt: nichts verloren
        return RedirectResponse(f"/modul/{modul}/ueben?veraltet=1", status_code=303)
    wert = logik.bewertung_lesen(bewertung)
    if wert is None:
        raise HTTPException(400, "Unbekannte Bewertung")
    with SPERRE:
        m = _modul(modul)
        jetzt = _jetzt()
        s = _sitzung(m, modul, jetzt)
        logik.bewertung_anwenden(s, m, karte, nr, wert, jetzt)
        _sitzung_schreiben(modul, s)
    return RedirectResponse(f"/modul/{modul}/ueben", status_code=303)


@app.get("/modul/{modul}/bild/{karte_id}/{art}")
def bild(modul: str, karte_id: str, art: str):
    karte = _modul(modul).karten.get(karte_id)
    if karte is None or art not in ("frage", "ganz"):
        raise HTTPException(404)
    eintrag = karte.get("bild") if art == "frage" else logik.ganzes_bild(karte.get("bild"))
    pfad = ablage.bild_pfad(UNI, modul, eintrag)
    if pfad is None:
        raise HTTPException(404)
    return FileResponse(pfad)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    port = logik.port_pruefen(PORT)
    logger.info("Uni-Portal hört auf 127.0.0.1:%s", port)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info", proxy_headers=False, server_header=False)


if __name__ == "__main__":
    main()
