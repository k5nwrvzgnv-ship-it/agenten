"""Uni-Portal: Prüfungsseite, Karten üben, mündliche Übungen. Hört nur auf 127.0.0.1, von außen über Caddy (HTTPS,
Passwort).

Schutz (webapp-plan.md, Abschnitt 7): lädt uni/.env nicht, liest nur die Positivliste aus ablage.py, handelt nie
nach außen, ruft Claude nicht auf: Das tut allein auswertung_agent.py in eigenem Dienst, ausgelöst über eine Datei in
der Warteschlange. Karten üben kostet also kein Kontingent. Logik ohne Netz steht in logik.py und uebungen.py.

Seiten:
  /                                  weiter zum Modul
  /modul/<modul>                     Prüfungsform, Themen mit Score und Lernstand, Liste "fehlt"
  /modul/<modul>/ueben               nächste Karte
  /modul/<modul>/bewerten            POST: Bewertung speichern
  /modul/<modul>/bild/<karte>/<art>  Bild der Karte (frage oder ganz)
  /modul/<modul>/uebung              POST: Transkript annehmen, Auswertung einreihen
  /modul/<modul>/uebung/<id>         Laufstand und Ergebnis
  /modul/<modul>/uebung/<id>/neu     POST: geparkte oder fehlgeschlagene Auswertung neu starten
  /modul/<modul>/uebung/<id>/karten  POST: Kartenvorschläge bestätigen, einzeln oder gesammelt
  /modul/<modul>/rubrik              Rubrik ansehen
  /modul/<modul>/rubrik/bestaetigen  POST: Rubrik bestätigen
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
import uebungen  # noqa: E402

UNI = HIER.parent
DATEN = HIER / "data"  # Sitzung des Portals, Warteschlange der Auswertung
ENV_DATEI = HIER / ".env"  # nur die Adresse des ElevenLabs-Agenten wird daraus gelesen (ablage.elevenlabs_adresse)
MAX_FORMULAR_BYTES = 1024 * 1024  # Körper des Upload-Formulars; Starlette begrenzt ein Textfeld genauso
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
    return logik.sitzung_holen(lernmodell.lies_json(_sitzung_datei(modul), None), m, modul, jetzt,
                               uebungen.vorgemerkt_lesen(m.ordner))


def _sitzung_schreiben(modul: str, s: dict) -> None:
    DATEN.mkdir(mode=0o700, exist_ok=True)
    lernmodell.schreibe_json(_sitzung_datei(modul), s)


def _rahmen(modul: str) -> dict:
    return {"module": [{"id": i, "name": n} for i, n in ablage.MODULE.items()], "aktiv": modul, "modul": modul,
            "name": ablage.MODULE[modul]}


@app.get("/")
def start():
    return RedirectResponse(f"/modul/{next(iter(ablage.MODULE))}", status_code=303)


def _uebungen_ansicht(modul: str) -> list[dict]:
    zeilen = []
    for uebung_id in ablage.uebungen_ids(UNI, modul):
        pfad = ablage.uebung_datei(UNI, modul, uebung_id, ablage.STAND)
        stand = lernmodell.lies_json(pfad, {}) if pfad else {}
        zeilen.append({"id": uebung_id, "titel": stand.get("titel") or "Ohne Titel", "angelegt": stand.get("angelegt", ""),
                       "stand": uebungen.stand_ansicht(stand, DATEN)})
    return zeilen


def _modul_seite(request: Request, modul: str, fehler: str | None = None, text: str = "", titel: str = "",
                 status_code: int = 200):
    m = _modul(modul)
    plan = ablage.plan_lesen(UNI, modul)
    rubrik = uebungen.rubrik_lesen(m.ordner)
    return vorlagen.TemplateResponse(request, "modul.html", {
        **_rahmen(modul), "plan": plan, "themen": logik.themen_ansicht(plan, m),
        "ueberblick": logik.ueberblick(m, _jetzt()), "vorgemerkt": len(uebungen.vorgemerkt_lesen(m.ordner)),
        "elevenlabs": ablage.elevenlabs_adresse(ENV_DATEI), "uebungen": _uebungen_ansicht(modul),
        "rubrik_da": rubrik is not None, "rubrik_bestaetigt": uebungen.rubrik_bestaetigt(rubrik),
        "token": logik.formular_token(GEHEIM), "fehler": fehler, "eingabe_text": text, "eingabe_titel": titel,
        "endungen": ", ".join(uebungen.ENDUNGEN), "max_kb": uebungen.MAX_BYTES // 1024,
        "max_zeichen": uebungen.MAX_ZEICHEN}, status_code=status_code)


@app.get("/modul/{modul}")
def pruefungsseite(request: Request, modul: str):
    return _modul_seite(request, modul)


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
        if logik.bewertung_anwenden(s, m, karte, nr, wert, jetzt):
            uebungen.vormerkung_entfernen(m.ordner, karte)
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


def _formular_pruefen(request: Request, token: str | None) -> bool:
    """Herkunft falsch: 403. Rückgabe False: Token alt (Dienst neu gestartet), die Seite soll neu geladen werden."""
    if not logik.herkunft_passt(request.headers.get("origin"), request.headers.get("host"),
                                request.headers.get("sec-fetch-site")):
        raise HTTPException(403, "Formular kommt nicht von dieser Seite")
    return logik.token_passt(GEHEIM, token)


def _uebung_ordner(modul: str, uebung_id: str) -> Path:
    ordner = ablage.uebung_ordner(UNI, modul, uebung_id)
    if ordner is None:
        raise HTTPException(404)
    return ordner


def _auswertung(modul: str, uebung_id: str) -> dict | None:
    pfad = ablage.uebung_datei(UNI, modul, uebung_id, ablage.AUSWERTUNG)
    return lernmodell.lies_json(pfad, None) if pfad else None


@app.post("/modul/{modul}/uebung")
async def uebung_hochladen(request: Request, modul: str):
    m = _modul(modul)
    try:
        laenge = int(request.headers.get("content-length", ""))
    except ValueError:
        raise HTTPException(411, "Größe des Formulars fehlt") from None
    if laenge > MAX_FORMULAR_BYTES:  # vor dem Lesen: ein zu großer Körper landet gar nicht erst auf der Platte
        return _modul_seite(request, modul, f"Zu groß: höchstens {uebungen.MAX_BYTES // 1024} KB.", status_code=413)
    async with request.form(max_files=1, max_fields=4) as formular:
        token, text, titel, datei = (formular.get(n) for n in ("token", "text", "titel", "datei"))
        name, roh = None, b""
        if datei is not None and not isinstance(datei, str) and datei.filename:
            name = datei.filename
            roh = await datei.read(uebungen.MAX_BYTES + 1)
    text = text if isinstance(text, str) else ""
    titel = uebungen.titel_pruefen(titel if isinstance(titel, str) else "")
    if not _formular_pruefen(request, token if isinstance(token, str) else None):
        return _modul_seite(request, modul, "Die Seite war nicht mehr aktuell. Bitte noch einmal absenden.", text, titel, 400)
    try:
        if name and text.strip():
            raise uebungen.UploadFehler("Bitte entweder eine Datei oder Text, nicht beides.")
        if not name and not text.strip():
            raise uebungen.UploadFehler("Es kam weder eine Datei noch Text an.")
        inhalt = uebungen.datei_lesen(name, roh) if name else uebungen.text_pruefen(text)
    except uebungen.UploadFehler as f:
        return _modul_seite(request, modul, str(f), text, titel, 400)
    uebung_id = uebungen.anlegen(m.ordner, DATEN, modul, inhalt, titel, _jetzt())
    logger.info("Übung %s angelegt, %d Zeichen", uebung_id, len(inhalt))
    return RedirectResponse(f"/modul/{modul}/uebung/{uebung_id}", status_code=303)


@app.get("/modul/{modul}/uebung/{uebung_id}")
def uebung_seite(request: Request, modul: str, uebung_id: str):
    m = _modul(modul)
    ordner = _uebung_ordner(modul, uebung_id)
    pfad_stand = ablage.uebung_datei(UNI, modul, uebung_id, ablage.STAND)
    pfad_text = ablage.uebung_datei(UNI, modul, uebung_id, ablage.TRANSKRIPT)
    stand = lernmodell.lies_json(pfad_stand, {}) if pfad_stand else {}
    auswertung = _auswertung(modul, uebung_id)
    rubrik = uebungen.rubrik_lesen(m.ordner)
    ansicht = None
    if auswertung:
        ansicht = uebungen.ergebnis_ansicht(auswertung, uebungen.kartenstand_lesen(ordner), ablage.plan_lesen(UNI, modul), m.karten)
    return vorlagen.TemplateResponse(request, "uebung.html", {
        **_rahmen(modul), "uebung_id": uebung_id, "stand": stand, "laufstand": uebungen.stand_ansicht(stand, DATEN),
        "auswertung": auswertung, "ansicht": ansicht, "rubrik_hinweis": uebungen.rubrik_hinweis(auswertung, rubrik),
        "transkript": pfad_text.read_text(encoding="utf-8") if pfad_text else "", "token": logik.formular_token(GEHEIM),
        "veraltet": request.query_params.get("veraltet") == "1"})


@app.post("/modul/{modul}/uebung/{uebung_id}/neu")
def uebung_neu_starten(request: Request, modul: str, uebung_id: str, token: Annotated[str, Form()] = ""):
    ordner = _uebung_ordner(modul, uebung_id)
    if not _formular_pruefen(request, token):
        return RedirectResponse(f"/modul/{modul}/uebung/{uebung_id}?veraltet=1", status_code=303)
    with SPERRE:
        uebungen.neu_einreihen(ordner, DATEN, modul, uebung_id, _jetzt())
    return RedirectResponse(f"/modul/{modul}/uebung/{uebung_id}", status_code=303)


@app.post("/modul/{modul}/uebung/{uebung_id}/karten")
def karten_bestaetigen(request: Request, modul: str, uebung_id: str, token: Annotated[str, Form()] = "",
                       art: Annotated[str, Form()] = "", nr: Annotated[str, Form()] = ""):
    """nr ist eine Vorschlagsnummer oder "alle". Erst dieser Klick schreibt an karten.json oder vorgemerkt.json."""
    m = _modul(modul)
    ordner = _uebung_ordner(modul, uebung_id)
    if not _formular_pruefen(request, token):
        return RedirectResponse(f"/modul/{modul}/uebung/{uebung_id}?veraltet=1", status_code=303)
    if nr != "alle" and not nr.isdecimal():
        raise HTTPException(400, "Unbekannter Vorschlag")
    auswertung = _auswertung(modul, uebung_id)
    if auswertung is None:
        raise HTTPException(404)
    with SPERRE:
        uebungen.uebernehmen(m.ordner, ordner, auswertung, art, None if nr == "alle" else [int(nr)], _jetzt())
    return RedirectResponse(f"/modul/{modul}/uebung/{uebung_id}", status_code=303)


@app.get("/modul/{modul}/rubrik")
def rubrik_seite(request: Request, modul: str):
    m = _modul(modul)
    rubrik = uebungen.rubrik_lesen(m.ordner)
    if rubrik is None:
        raise HTTPException(404)
    return vorlagen.TemplateResponse(request, "rubrik.html", {
        **_rahmen(modul), "rubrik": rubrik, "bestaetigt": uebungen.rubrik_bestaetigt(rubrik),
        "token": logik.formular_token(GEHEIM), "veraltet": request.query_params.get("veraltet") == "1"})


@app.post("/modul/{modul}/rubrik/bestaetigen")
def rubrik_bestaetigen(request: Request, modul: str, token: Annotated[str, Form()] = ""):
    m = _modul(modul)
    if not _formular_pruefen(request, token):
        return RedirectResponse(f"/modul/{modul}/rubrik?veraltet=1", status_code=303)
    with SPERRE:
        uebungen.rubrik_bestaetigen(m.ordner, _jetzt())
    return RedirectResponse(f"/modul/{modul}/rubrik", status_code=303)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    port = logik.port_pruefen(PORT)
    logger.info("Uni-Portal hört auf 127.0.0.1:%s", port)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info", proxy_headers=False, server_header=False)


if __name__ == "__main__":
    main()
