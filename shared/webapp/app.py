"""Web-App für Lia: Seite "Heute" mit Ergebnis- und Entwurf-Ansicht und "Neuer Auftrag", ohne Anmeldung.

Rahmen in drei Spalten (docs/webapp-aufbau.md, Bauschritt 1): links der Baum (Heute, je Fach Klassen/Kurse und
Reihen), in der Mitte der Inhalt mit Brotkrumen, rechts "Fragen" (bisher nur Platzhalter, kein Chat).

Kein Port: Uvicorn hört auf einem Unix-Socket in data/ (Ordner nur für User agent), wie der Leitstand.
Zugriff zum Test per SSH-Tunnel:
  ssh -N -L 8792:/home/agent/agenten/shared/webapp/data/webapp.sock agents-user
und dann http://localhost:8792 im Browser.

Daten: Warteschlangen der Instanz WEBAPP_INSTANZ (Standard lia/instanz) über agentkit mit basis=.
Die App selbst läuft ohne AGENTKIT_INSTANZ. Logik in logik.py (getestet), hier nur Dateien und HTTP.

GET:
  /                                     Seite Heute
  /teile/heute                          Inhalt von Heute (htmx lädt ihn jede Minute neu)
  /ergebnis/<id>                        Auftrag mit Feedback-Schleife: neueste Fassung und Verlauf (auch
                                        fehlgeschlagene mit Grund). IDs von Nachbesserungen und Rückmeldungen
                                        leiten auf den Ursprung um.
  /ergebnis/<id>/datei/<n>              Download der n-ten Ergebnisdatei
  /ergebnis/<id>/datei/<n>/pdf          PDF aus der Vorschau des Renderers
  /ergebnis/<id>/datei/<n>/seite/<m>    Seitenbild m (ab 1) der Vorschau
  /ergebnis/<id>/datei/<n>/ansehen      Seiten-Betrachter (?seite=m, Standard 1): eine Seite groß, Vor/Zurück,
                                        ohne JavaScript; <id> ist die Fassung, aus der die Datei stammt
  /entwurf/<id>                         offener Entwurf, ganzer Text, keine Knöpfe
  /reihe/<kennung>                      Reihe mit Reihenfrage und ihren Aufträgen (ordnung.py, nur lesend)
  /unterricht                           alte Seite, leitet auf / um
  /statisch/...                         CSS, htmx
  /neu                                  Formular Neuer Auftrag (nur Material), nur wenn eingeschaltet
POST, die einzige Route mit Wirkung:
  /neu                                  legt einen Auftrag an (agentkit.auftraege.neuer_auftrag mit basis=)

Neuer Auftrag ist ausgeschaltet, bis WEBAPP_NEUER_AUFTRAG gesetzt ist:
  test  nur mit einer anderen Instanz als lia/instanz (WEBAPP_INSTANZ), kein Agent startet
  echt  jede Instanz, danach startet lia-unterricht.service (Ergebnis kommt auch per Telegram, Lias Kontingent)
Ohne Konten schützt sich das Formular vor fremden Seiten im selben Browser (CSRF): Origin muss zum Host passen
und ein Token aus dem Formular (geheim je Start der App) muss stimmen.
IDs werden mit agentkit geprüft und nur in der Instanz gesucht. Dateien kommen nur über ihre Nummer in
ergebnis_dateien, nie über einen Pfad aus der URL; jeder Pfad wird gegen den Agent-Ordner geprüft (dateien.py).

Start: .venv/bin/python app.py   (Socket-Pfad änderbar mit WEBAPP_SOCKET)
"""

import logging
import os
import secrets
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException

from agentkit import auftraege, config, freigabe
from agentkit._ablage import AblageFehler, pruefe_id

import dateien
import logik
import ordnung

HIER = Path(__file__).resolve().parent
SOCKET = Path(os.environ.get("WEBAPP_SOCKET") or HIER / "data" / "webapp.sock")
ECHTE_INSTANZ = HIER.parent.parent / "lia" / "instanz"
INSTANZ = Path(os.environ.get("WEBAPP_INSTANZ") or ECHTE_INSTANZ)
NEUER_AUFTRAG = os.environ.get("WEBAPP_NEUER_AUFTRAG", "")  # "", "test" oder "echt" (siehe oben)
EINGANG = HIER / "data" / "eingang"  # Uploads, bis agentkit sie in den Agent-Ordner verschiebt
UNIT_DIR = Path.home() / ".config" / "systemd" / "user"
GEHEIM = secrets.token_bytes(32)  # für das Formular-Token, neu bei jedem Start
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


@app.exception_handler(StarletteHTTPException)
async def fehlerseite(request: Request, fehler: StarletteHTTPException):
    if fehler.status_code == 404:
        return vorlagen.TemplateResponse(request, "nicht_gefunden.html", {
            "e": {"titel": "Nicht gefunden"}, **rahmen(reihen_laden(), logik.krumen("Nicht gefunden"))},
            status_code=404)
    return await http_exception_handler(request, fehler)


@app.middleware("http")
async def kopfzeilen(request: Request, call_next):
    antwort = await call_next(request)
    for name, wert in KOPFZEILEN.items():
        antwort.headers.setdefault(name, wert)
    return antwort


_reihen_fehler: list[str] = []  # zuletzt geloggte Fehler: nicht bei jedem Neuladen (jede Minute) wieder


def reihen_laden() -> list[dict]:
    """Lias Reihen; Fehler in reihen.toml stehen im Log, die App zeigt dann ohne die fehlerhaften Reihen."""
    reihen, fehler = ordnung.laden(INSTANZ)
    if fehler != _reihen_fehler:
        for f in fehler:
            logger.error("Reihen: %s", f)
        _reihen_fehler[:] = fehler
    return reihen


def heute_daten(reihen: list[dict] | None = None) -> dict:
    return logik.heute(auftraege.neue(basis=INSTANZ / "auftraege"),
                       auftraege.erledigte(basis=INSTANZ / "auftraege"),
                       freigabe.offene(basis=INSTANZ / "freigabe"),
                       datetime.now(ZONE), config.person(INSTANZ),
                       reihen if reihen is not None else reihen_laden())


def rahmen(reihen: list[dict], krumen: dict, aktiv: str = "", anzahl_wartet: int | None = None) -> dict:
    """Werte für basis.html: Baum (links) und Brotkrumen. Ohne anzahl_wartet wird "Heute" dafür berechnet."""
    if anzahl_wartet is None:
        anzahl_wartet = heute_daten(reihen)["anzahl_wartet"]
    return {"baum": logik.baum(reihen, anzahl_wartet, aktiv), "krumen": krumen}


def neu_modus() -> str:
    """"test", "echt" oder "" (aus). test gilt nie für Lias echte Instanz."""
    if NEUER_AUFTRAG == "echt":
        return "echt"
    if NEUER_AUFTRAG == "test" and INSTANZ.resolve() != ECHTE_INSTANZ.resolve():
        return "test"
    return ""


@app.get("/", response_class=HTMLResponse)
def seite_heute(request: Request):
    reihen = reihen_laden()
    h = heute_daten(reihen)
    return vorlagen.TemplateResponse(request, "heute.html", {
        "h": h, "neu": neu_modus(), "abgeschickt": request.query_params.get("abgeschickt") == "1",
        **rahmen(reihen, logik.krumen(), "heute", h["anzahl_wartet"])})


@app.get("/teile/heute", response_class=HTMLResponse)
def teil_heute(request: Request):
    return vorlagen.TemplateResponse(request, "_heute.html", {"h": heute_daten(), "neu": neu_modus()})


@app.get("/unterricht")
def alte_seite_unterricht():
    """Die Seite gibt es nicht mehr (Bauschritt 1 des neuen Aufbaus): Reihen stehen jetzt im Baum."""
    return RedirectResponse("/", status_code=301)


@app.get("/reihe/{reihe_id}", response_class=HTMLResponse)
def seite_reihe(request: Request, reihe_id: str):
    reihen = reihen_laden()
    reihe = next((r for r in reihen if r["id"] == reihe_id), None)
    if reihe is None:
        raise HTTPException(404)
    basis = INSTANZ / "auftraege"
    e = logik.reihe_ansicht(reihe, reihen, [*auftraege.neue(basis=basis), *auftraege.erledigte(basis=basis)],
                            datetime.now(ZONE), freigabe.offene(basis=INSTANZ / "freigabe"))
    return vorlagen.TemplateResponse(request, "reihe.html", {
        "e": e, **rahmen(reihen, logik.krumen(reihe=reihe), reihe["id"])})


def _formular(request: Request, text: str = "", fehler: list[str] | None = None, status: int = 200,
              reihe: str = ""):
    reihen = reihen_laden()
    return vorlagen.TemplateResponse(request, "neu.html", {
        "e": {"titel": "Neuer Auftrag", "unter": "Auftrag an deine Assistenz"},
        "modus": neu_modus(), "token": logik.formular_token(GEHEIM), "text": text, "fehler": fehler or [],
        "reihen": logik.reihen_auswahl(reihen), "reihe": reihe,
        "text_max": logik.NEU_TEXT_MAX, "max_mb": logik.NEU_DATEI_MAX_MB, "endungen": ",".join(logik.NEU_ENDUNGEN),
        **rahmen(reihen, logik.krumen("Neuer Auftrag")),
    }, status_code=status)


@app.get("/neu", response_class=HTMLResponse)
def seite_neu(request: Request):
    if not neu_modus():
        raise HTTPException(404)
    return _formular(request)


def agent_starten(agent: str) -> None:
    """Startet lia-<agent>.service wie portal.agent_starten (--no-block: nicht auf das Ende warten)."""
    dienst = f"lia-{agent}"
    if not (UNIT_DIR / f"{dienst}.service").exists():
        logger.error("Kein Dienst %s.service, Auftrag wartet", dienst)
        return
    lauf = subprocess.run(["systemctl", "--user", "start", "--no-block", f"{dienst}.service"],
                          capture_output=True, text=True, check=False)
    if lauf.returncode != 0:
        logger.error("Start von %s.service fehlgeschlagen: %s", dienst, lauf.stderr.strip())


@app.post("/neu", response_class=HTMLResponse)
async def neu_abschicken(request: Request):
    modus = neu_modus()
    if not modus:
        raise HTTPException(404)
    if not logik.herkunft_passt(request.headers.get("origin"), request.headers.get("host"),
                                request.headers.get("sec-fetch-site")):
        logger.warning("Neuer Auftrag abgewiesen: fremde Herkunft")
        raise HTTPException(403)
    grenze = (logik.NEU_DATEIEN_MAX * logik.NEU_DATEI_MAX_MB + 1) * 1024 * 1024
    if int(request.headers.get("content-length") or 0) > grenze:
        raise HTTPException(413)
    try:
        form = await request.form(max_files=logik.NEU_DATEIEN_MAX + 1, max_fields=5, max_part_size=64 * 1024)
    except Exception:  # kaputtes oder zu großes Formular (MultiPartException u. a.)
        logger.warning("Neuer Auftrag: Formular nicht lesbar")
        raise HTTPException(400) from None
    text, gewaehlt = str(form.get("text") or ""), str(form.get("reihe") or "")
    if not logik.token_passt(GEHEIM, str(form.get("token") or "")):
        return _formular(request, text, ["Die Seite war veraltet. Bitte wähle die Dateien neu und schick es noch "
                                         "einmal ab."], 400, gewaehlt)
    dateien_ = [d for d in form.getlist("dateien") if isinstance(d, UploadFile) and d.filename]
    text, fehler = logik.neuer_auftrag_pruefen(text, [(d.filename, d.size or 0) for d in dateien_])
    reihen = reihen_laden()
    reihe, fehler_reihe = logik.reihe_pruefen(gewaehlt, reihen)
    if fehler or fehler_reihe:
        return _formular(request, text, fehler + fehler_reihe, 400, reihe or "")
    EINGANG.mkdir(parents=True, exist_ok=True)
    ablage = Path(tempfile.mkdtemp(dir=EINGANG))
    try:
        pfade = []
        for nr, d in enumerate(dateien_):  # je Datei ein Unterordner: gleiche Namen überschreiben sich nicht
            pfad = ablage / str(nr) / logik.dateiname_bereinigen(d.filename)
            pfad.parent.mkdir()
            with pfad.open("wb") as ziel:
                shutil.copyfileobj(d.file, ziel)
            pfade.append(pfad)
        aid = auftraege.neuer_auftrag(logik.NEU_AGENT, logik.text_mit_reihe(text, reihe, reihen),
                                      quelle=logik.NEU_QUELLE, dateien=pfade, basis=INSTANZ / "auftraege",
                                      agenten_dir=INSTANZ.parent, absender=config.person(INSTANZ), reihe=reihe)
    except (auftraege.AuftragFehler, OSError) as fehler_:
        logger.error("Neuer Auftrag nicht angelegt: %s", fehler_)
        return _formular(request, text, [logik.FEHLGESCHLAGEN], 500)
    finally:
        shutil.rmtree(ablage, ignore_errors=True)
        for d in dateien_:
            await d.close()
    logger.info("Auftrag %s angelegt (%s, %d Dateien, Reihe %s, %s)", aid, logik.NEU_AGENT, len(pfade),
                reihe or "keine", modus)
    if modus == "echt":
        agent_starten(logik.NEU_AGENT)
    return RedirectResponse("/?abgeschickt=1", status_code=303)


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
    reihen = reihen_laden()
    reihe = logik.reihe_von(kopf, reihen)
    return vorlagen.TemplateResponse(request, "ergebnis.html", {
        "e": e, **rahmen(reihen, logik.krumen(e["titel"], reihe), reihe["id"] if reihe else "")})


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


@app.get("/ergebnis/{eintrag_id}/datei/{nr:int}/ansehen", response_class=HTMLResponse)
def seite_ansehen(request: Request, eintrag_id: str, nr: int, seite: str | None = None):
    wurzel, _ = _ergebnisdatei(eintrag_id, nr)
    pfade = _auftrag(eintrag_id).get("ergebnis_dateien") or []
    datei = next((d for d in logik.dateien_ansicht(pfade, dateien.vorschau_info(wurzel, pfade)) if d["nr"] == nr),
                 None)
    basis = INSTANZ / "auftraege"
    kette = logik.kette_von(eintrag_id, [*auftraege.neue(basis=basis), *auftraege.erledigte(basis=basis)])
    e = logik.betrachter(kette, eintrag_id, datei, seite) if datei else None
    if e is None:
        raise HTTPException(404)
    reihen = reihen_laden()
    reihe = logik.reihe_von(logik.kopf(kette), reihen)
    ueber = {"text": e["ergebnis_titel"], "link": e["ergebnis_link"]}
    return vorlagen.TemplateResponse(request, "ansehen.html", {
        "e": e, **rahmen(reihen, logik.krumen(e["titel"], reihe, ueber), reihe["id"] if reihe else "")})


@app.get("/entwurf/{eintrag_id}", response_class=HTMLResponse)
def seite_entwurf(request: Request, eintrag_id: str):
    try:
        pruefe_id(eintrag_id)
    except AblageFehler:
        raise HTTPException(404) from None
    eintrag = next((e for e in freigabe.offene(basis=INSTANZ / "freigabe") if e.get("id") == eintrag_id), None)
    if eintrag is None:
        raise HTTPException(404)
    e = logik.entwurf(eintrag, datetime.now(ZONE))
    reihen = reihen_laden()
    reihe = logik.reihe_von(eintrag, reihen)
    return vorlagen.TemplateResponse(request, "entwurf.html", {
        "e": e, **rahmen(reihen, logik.krumen(e["titel"], reihe), reihe["id"] if reihe else "")})


def socket_vorbereiten(socket_pfad: Path = SOCKET) -> None:
    socket_pfad.parent.mkdir(parents=True, exist_ok=True)
    socket_pfad.parent.chmod(0o700)  # Uvicorn gibt dem Socket 0666, der Ordner hält andere Benutzer fern
    socket_pfad.unlink(missing_ok=True)  # Rest eines früheren Laufs


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    socket_vorbereiten()
    logger.info("Web-App hört auf %s, Instanz %s, Neuer Auftrag: %s", SOCKET, INSTANZ, neu_modus() or "aus")
    if NEUER_AUFTRAG and not neu_modus():
        logger.warning("WEBAPP_NEUER_AUFTRAG=%s gilt nicht für %s, Neuer Auftrag bleibt aus", NEUER_AUFTRAG, INSTANZ)
    try:
        uvicorn.run(app, uds=str(SOCKET), log_level="info", proxy_headers=False, server_header=False)
    finally:
        SOCKET.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
