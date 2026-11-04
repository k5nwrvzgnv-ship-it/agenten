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
  /teile/frage/<id>                     Antwort des Chat-Agenten für die Spalte „Fragen“ (htmx, alle 2 s)
  /ergebnis/<id>                        Auftrag mit Feedback-Schleife: neueste Fassung und Verlauf (auch
                                        fehlgeschlagene mit Grund). IDs von Nachbesserungen und Rückmeldungen
                                        leiten auf den Ursprung um.
  /ergebnis/<id>/datei/<n>              Download der n-ten Ergebnisdatei
  /ergebnis/<id>/datei/<n>/pdf          PDF aus der Vorschau des Renderers
  /ergebnis/<id>/datei/<n>/seite/<m>    Seitenbild m (ab 1) der Vorschau
  /ergebnis/<id>/eigene/<n>             Download von Lias n-ter eigener Fassung (zustand.py)
  /ergebnis/<id>/datei/<n>/ansehen      Seiten-Betrachter (?seite=m, Standard 1): eine Seite groß, Vor/Zurück,
                                        ohne JavaScript; <id> ist die Fassung, aus der die Datei stammt
  /entwurf/<id>                         offener Entwurf, ganzer Text; Lia entscheidet bei Typ entwurf selbst
  /reihe/<kennung>                      Reihe mit Reihenfrage und ihren Aufträgen (ordnung.py, nur lesend)
  /reihe/<kennung>/stunde/<n>           Stunde (bzw. Probe) n mit Thema und Material (aus reihen.toml)
  /fach/<kennung>                       Fach mit Klassen/Kursen (nur lesend)
  /klasse/<kennung>                     Klasse/Kurs mit ihren Reihen (nur lesend)
  /vorlagen                             Gestaltung (Profil des Material-Agenten) und Arten, nur lesend
  /vorlagen/formatvorlage(/entfernen)   POST: Lias Word-/PowerPoint-Vorlage für lia/unterricht ablegen bzw. entfernen
  /ich                                  Lias Regeln (regeln.md, Gelernte Regeln der Agenten), nur lesend
  /unterricht                           alte Seite, leitet auf / um
  /statisch/...                         CSS, htmx
  /neu                                  Galerie der Vorlagen bzw. Formular (?art=…), Ort vorbelegt (?reihe=…&stunde=n),
                                        nur wenn eingeschaltet
POST:
  /fragen                               Frage an den Chat-Agenten (lia/chat), nur mit WEBAPP_CHAT=an
  /neu                                  legt einen Auftrag an (agentkit.auftraege.neuer_auftrag mit basis=)
  /ergebnis/<id>/rueckmeldung           Rückmeldung an den Feedback-Dienst (Auftrag an feedback, bezug = Fassung),
                                        wie Neuer Auftrag nur im Testbetrieb oder echt; eine Datei wird je nach Art Fassung oder Anmerkung
  /ergebnis/<id>/final                  Fassung als final markieren oder zurücknehmen (agentkit.fassungen)
  /ergebnis/<id>/eigene                 eigene Fassung hochladen (agentkit.fassungen, Datei in den Agent-Ordner)
  /entwurf/<id>                         Lias Entscheidung „Setze ich selbst ein“/„Brauche ich nicht“/rückgängig (data/)
  /auftrag/<id>/zurueckziehen           laufenden Auftrag zurückziehen (agentkit, nur test/echt)
  /ergebnis/<id>/nochmal                fehlgeschlagenen letzten Versuch noch einmal anlegen (nur test/echt)
  /ergebnis/<id>/stunde                 Material einer Stunde der Reihe zuordnen (nur in data/, über die Stunden-id)
  /ergebnis/<id>/variante               Variante anfordern: neuer Auftrag an den Material-Agenten mit der Datei als
                                        Anhang (wie Neuer Auftrag nur test/echt), Zuordnung in data/
Struktur pflegen (Strukturplan docs/struktur-pflege-plan.md, Bauschritt 5; geschrieben nur über
agentkit.strukturpflege, nie selbst in reihen.toml; nach jeder Aktion „… · Rückgängig“):
  GET+POST /fach/neu, /fach/<id>/bearbeiten, /fach/<id>/klasse/neu (mit Stundenplan und, einmal, Bundesland)
  GET+POST /klasse/<id>/bearbeiten, /klasse/<id>/stundenplan (auch ab Stichtag), /klasse/<id>/uebernehmen (ins
           nächste Schuljahr), /klasse/<id>/ausfall?termin=…, /klasse/<id>/reihe/neu (mit Terminen)
  POST     /klasse/<id>/lerngruppe, /klasse/<id>/verschieben, /klasse/<id>/ausfall-aufheben,
           /klasse/<id>/zusatztermin(-entfernen)
  GET+POST /reihe/<id>/bearbeiten, /reihe/<id>/termine (zuteilen, freigeben), /reihe/<id>/kopieren
  POST     /reihe/<id>/verschieben (andere Klasse), /reihe/<id>/zeitlich (beginnt an einem Termin),
           /reihe/<id>/stunden (neue Stunde), /stunde/<id>/aendern, /stunden/verschieben, /stunde/<id>/kopieren,
           /objekt/<id>/archivieren|wiederherstellen|loeschen, /schule (Bundesland), /rueckgaengig

Neuer Auftrag und Rückmeldung sind ausgeschaltet, bis WEBAPP_NEUER_AUFTRAG gesetzt ist:
  test  nur mit einer anderen Instanz als lia/instanz (WEBAPP_INSTANZ), kein Agent startet
  echt  jede Instanz, danach startet lia-unterricht.service bzw. lia-feedback.service (Ergebnis kommt auch per
        Telegram, Lias Kontingent)
Final und eigene Fassung speichert agentkit.fassungen in der Instanz (Jans Entscheidung 30.10.: die Agenten sollen sie
sehen); Stunden, Varianten-Zuordnung, Entwurf-Entscheidungen und „Nochmal“ nur data/ der Web-App. Alles davon geht
immer, auch ohne WEBAPP_NEUER_AUFTRAG, weil es keinen Lauf startet.
Ohne Konten schützen sich die Formulare vor fremden Seiten im selben Browser (CSRF): Origin muss zum Host passen
und ein Token aus dem Formular (geheim je Start der App) muss stimmen.
IDs werden mit agentkit geprüft und nur in der Instanz gesucht. Dateien kommen nur über ihre Nummer in
ergebnis_dateien, nie über einen Pfad aus der URL; jeder Pfad wird gegen den Agent-Ordner geprüft (dateien.py).

Start: .venv/bin/python app.py   (Socket-Pfad änderbar mit WEBAPP_SOCKET; mit WEBAPP_PORT=8791 auf 127.0.0.1:8791
       statt Socket, so läuft der Dienst systemd/webapp.service hinter Caddy)
"""

import logging
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
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

from agentkit import auftraege, config, fassungen, freigabe, struktur, termine
from agentkit import strukturpflege as sp
from agentkit._ablage import AblageFehler, pruefe_id

import dateien
import logik
import ordnung
import pflege
import zustand

HIER = Path(__file__).resolve().parent
SOCKET = Path(os.environ.get("WEBAPP_SOCKET") or HIER / "data" / "webapp.sock")
# Port auf 127.0.0.1 statt Socket (Dienst webapp.service hinter Caddy, lia.meldro.de; Jan 30.10. „Weg 2“)
PORT = os.environ.get("WEBAPP_PORT", "")
ECHTE_INSTANZ = HIER.parent.parent / "lia" / "instanz"
INSTANZ = Path(os.environ.get("WEBAPP_INSTANZ") or ECHTE_INSTANZ)
NEUER_AUFTRAG = os.environ.get("WEBAPP_NEUER_AUFTRAG", "")  # "", "test" oder "echt" (siehe oben)
CHAT = os.environ.get("WEBAPP_CHAT", "") == "an"  # Spalte „Fragen“ an den Chat-Agenten (Lias Kontingent)
CHAT_DIR = HIER.parent.parent / "lia" / "chat"
CHAT_ORDNER = CHAT_DIR / "data"  # Warteschlange des Chat-Agenten (lia/chat/schnittstelle.py)
DATEN = HIER / "data"
EINGANG = DATEN / "eingang"  # Uploads, bis agentkit sie in den Agent-Ordner verschiebt
UNIT_DIR = Path.home() / ".config" / "systemd" / "user"
GEHEIM = secrets.token_bytes(32)  # für das Formular-Token, neu bei jedem Start
ZONE = ZoneInfo("Europe/Berlin")
logger = logging.getLogger("webapp")

# Keine fremden Quellen (auch keine Google Fonts): Lias Gerät spricht nur mit diesem Server
KOPFZEILEN = {
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",  # nicht no-referrer: Browser schicken damit bei Formularen Origin: null (403)
    "Cache-Control": "no-store",
}

def beim_start() -> None:
    """Liegengebliebene Commits von reihen.toml nachholen (agentkit.strukturpflege, eigener Faden, kehrt sofort
    zurück). Ein Fehler hier hält die App nicht auf."""
    try:
        sp.anstossen(umgebung())
    except Exception:  # Start der App geht vor; agentkit meldet gescheiterte Commits selbst an Jan
        logger.exception("Commits der Struktur nicht angestoßen")


@asynccontextmanager
async def lebenslauf(_app):
    beim_start()
    yield


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lebenslauf)
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


def ordnung_laden() -> tuple[list[dict], list[dict]]:
    """Lias Reihen und Klassen/Kurse (agentkit.struktur); Fehler in reihen.toml stehen im Log, die App zeigt dann
    keine Reihen."""
    reihen, gruppen, fehler = ordnung.laden(INSTANZ)
    if fehler != _reihen_fehler:
        for f in fehler:
            logger.error("Reihen: %s", f)
        _reihen_fehler[:] = fehler
    return reihen, gruppen


def reihen_laden() -> list[dict]:
    return ordnung_laden()[0]


def zustand_() -> zustand.Zustand:
    """Was die Web-App selbst speichert (final, eigene Fassungen), je Instanz."""
    return zustand.Zustand(DATEN, INSTANZ)


def _entwuerfe() -> list[dict]:
    """Offene Entwürfe der Instanz mit Lias Entscheidung aus der Web-App (zustand.py)."""
    return logik.entwuerfe_mit_entscheidung(freigabe.offene(basis=INSTANZ / "freigabe"),
                                            zustand_().lesen()["entwuerfe"])


def _ausblenden(z: dict) -> set[str]:
    """Aufträge, die an ihrem Ort nicht als eigenes Material stehen: Varianten (beim Original) und
    fehlgeschlagene Ursprünge, die „Nochmal“ ersetzt hat."""
    return logik.varianten_ids(z) | set(z["ersetzt"])


def heute_daten(reihen: list[dict] | None = None) -> dict:
    z_ = zustand_().lesen()
    return logik.heute(logik.mit_zuordnung(auftraege.neue(basis=INSTANZ / "auftraege"), z_["reihe_von"]),
                       logik.mit_zuordnung(auftraege.erledigte(basis=INSTANZ / "auftraege"), z_["reihe_von"]),
                       _entwuerfe(),
                       datetime.now(ZONE), config.person(INSTANZ),
                       reihen if reihen is not None else reihen_laden(), set(z_["final"]),
                       set(z_["ersetzt"]))


def chat():
    """Schnittstelle des Chat-Agenten (lia/chat/schnittstelle.py, nur Bordmittel) oder None, wenn aus."""
    if not CHAT:
        return None
    if str(CHAT_DIR) not in sys.path:
        sys.path.append(str(CHAT_DIR))
    import schnittstelle
    return schnittstelle


def _fragen(reihen: list[dict], aktiv: str, stunde: int | None) -> dict | None:
    """Werte der Spalte „Fragen“ für den Ort der Seite; None, wenn der Chat aus ist (dann Platzhalter)."""
    modul = chat()
    if modul is None:
        return None
    reihe = next((r for r in reihen if r["id"] == aktiv), None)
    st = _stunde_tupel(reihe, stunde)
    try:
        verlauf = modul.verlauf(CHAT_ORDNER)
    except (OSError, ValueError) as fehler_:
        logger.error("Chat-Verlauf nicht lesbar: %s", fehler_)
        verlauf = []
    return logik.fragen_spalte(verlauf, reihe, st)


def _stunde_tupel(reihe: dict | None, nr: int | None) -> tuple[int, str] | None:
    if not reihe or not nr:
        return None
    stunden = logik.reihe_stunden(reihe)
    return (nr, stunden[nr - 1]["thema"]) if 1 <= nr <= len(stunden) else None


def rahmen(reihen: list[dict], krumen: dict, aktiv: str = "", anzahl_wartet: int | None = None,
           neu_hier: str = "", stunde: int | None = None) -> dict:
    """Werte für basis.html: Baum (links) und Brotkrumen. Ohne anzahl_wartet wird "Heute" dafür berechnet.
    neu_hier: Link für „+ Neu hier“ neben den Brotkrumen (nur, wenn Neuer Auftrag eingeschaltet ist)."""
    if anzahl_wartet is None:
        anzahl_wartet = heute_daten(reihen)["anzahl_wartet"]
    reihe = next((r for r in reihen if r["id"] == aktiv), None)
    stunden = {aktiv: logik.reihe_stunden(reihe)} if reihe else {}
    s = struktur_()
    pflegen_ = s is not None and s.format == "neu"  # die App schreibt nur das neue Format (agentkit.strukturpflege)
    return {"baum": logik.baum(reihen, anzahl_wartet, aktiv, stunden, stunde, ordnung_laden()[1],
                               logik.faecher_aus(s), pflegen_), "krumen": krumen,
            "neu_hier": neu_hier if neu_modus() else "", "fragen": _fragen(reihen, aktiv, stunde),
            "fragen_token": logik.formular_token(GEHEIM), "frage_fehler": logik.FRAGE_FEHLER}


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
        "token": logik.formular_token(GEHEIM),
        "hinweis": logik.HINWEISE.get(request.query_params.get("erledigt") or "", ""),
        **rahmen(reihen, logik.krumen(), "heute", h["anzahl_wartet"])})


@app.get("/teile/heute", response_class=HTMLResponse)
def teil_heute(request: Request):
    return vorlagen.TemplateResponse(request, "_heute.html", {"h": heute_daten(), "neu": neu_modus(),
                                                               "token": logik.formular_token(GEHEIM)})


@app.post("/fragen")
async def frage_stellen(request: Request):
    """Frage an den Chat-Agenten; danach zurück auf die Seite, die Antwort lädt htmx nach (/teile/frage/<id>).
    Dateien legt die Web-App in EINGANG ab, die Schnittstelle verschiebt sie; was übrig bleibt (auch bei
    FrageFehler), räumt die Web-App weg."""
    modul = chat()
    if modul is None:
        raise HTTPException(404)
    form = await formular_lesen(request, "Frage", logik.FRAGE_DATEIEN_MAX, logik.NEU_DATEIEN_MAX)  # zu viele: Satz
    dateien_ = [d for d in form.getlist("dateien") if isinstance(d, UploadFile) and d.filename]
    try:
        return await _frage_weitergeben(modul, form, dateien_)
    finally:
        for d in dateien_:
            await d.close()


async def _frage_weitergeben(modul, form, dateien_: list[UploadFile]) -> RedirectResponse:
    zurueck = logik.zurueck_pfad(str(form.get("zurueck") or ""))
    if not logik.token_passt(GEHEIM, str(form.get("token") or "")):
        return RedirectResponse(f"{zurueck}?fragefehler=veraltet#fragen", status_code=303)
    text, netz, gruendlich = str(form.get("text") or ""), form.get("netz") == "1", form.get("gruendlich") == "1"
    code = "leer" if not text.strip() else logik.frage_dateien_pruefen([(d.filename, d.size or 0) for d in dateien_])
    if code:
        return RedirectResponse(f"{zurueck}?fragefehler={code}#fragen", status_code=303)
    reihen = reihen_laden()
    reihe = None if form.get("ohne") else next((r for r in reihen if r["id"] == str(form.get("reihe") or "")), None)
    stunde = _stunde_tupel(reihe, logik.stunde_nummer(str(form.get("stunde") or ""), 999))
    EINGANG.mkdir(parents=True, exist_ok=True)
    ablage = Path(tempfile.mkdtemp(dir=EINGANG))
    try:  # je Datei ein Unterordner wie bei Neuer Auftrag
        uploads = [(d.filename, datei_ablegen(d, ablage / str(nr))) for nr, d in enumerate(dateien_)]
        stunde_id = logik.reihe_stunden(reihe)[stunde[0] - 1]["id"] if stunde else ""
        fid = modul.frage_stellen(text, logik.frage_ort(reihe, stunde, [], stunde_id), gruendlich, CHAT_ORDNER,
                                  netz=netz, dateien=uploads)
    except modul.FrageFehler as fehler_:
        logger.warning("Frage abgewiesen: %s", fehler_)
        code = logik.frage_fehler_schluessel(text, str(fehler_))
        return RedirectResponse(f"{zurueck}?fragefehler={code}#fragen", status_code=303)
    except OSError as fehler_:
        logger.error("Frage nicht gestellt: %s", fehler_)
        return RedirectResponse(f"{zurueck}?fragefehler=technik#fragen", status_code=303)
    finally:
        shutil.rmtree(ablage, ignore_errors=True)
    logger.info("Frage %s gestellt (%s, %s, %s, %d Dateien)", fid, reihe["id"] if reihe else "ohne Ort",
                "gründlich" if gruendlich else "schnell", "mit Netz" if netz else "ohne Netz", len(uploads))
    return RedirectResponse(f"{zurueck}?frage={fid}#fragen", status_code=303)


@app.get("/teile/frage/{frage_id}", response_class=HTMLResponse)
def teil_frage(request: Request, frage_id: str):
    """Antwort auf eine Frage für htmx: solange sie fehlt, „Denkt nach“ mit erneutem Nachfragen in 2 s."""
    modul = chat()
    if modul is None or not logik.chat_id_gueltig(frage_id):
        raise HTTPException(404)
    antwort = modul.antwort_holen(frage_id, CHAT_ORDNER)
    return vorlagen.TemplateResponse(request, "_frage.html", {
        "id": frage_id, "a": logik.fragen_eintrag(antwort) if antwort else None,
        "fehler": (antwort or {}).get("fehler"), "wartet": antwort is None})


@app.get("/unterricht")
def alte_seite_unterricht():
    """Die Seite gibt es nicht mehr (Bauschritt 1 des neuen Aufbaus): Reihen stehen jetzt im Baum."""
    return RedirectResponse("/", status_code=301)


def _reihe(reihe_id: str) -> tuple[list[dict], dict]:
    """Alle Reihen und die gesuchte; unbekannt: 404."""
    reihen = reihen_laden()
    reihe = next((r for r in reihen if r["id"] == reihe_id), None)
    if reihe is None:
        raise HTTPException(404)
    return reihen, reihe


def _auftraege_von(agent: str) -> list[dict]:
    """Offene und abgeschlossene Aufträge eines Agenten (für logik.auftrag_doppelt)."""
    basis = INSTANZ / "auftraege"
    return auftraege.neue(agent, basis) + auftraege.erledigte(agent, basis)


def _alle_auftraege() -> list[dict]:
    """Alle Aufträge der Instanz, mit Lias Zuordnung zu Reihen (zustand.py: reihe_von)."""
    basis = INSTANZ / "auftraege"
    return logik.mit_zuordnung([*auftraege.neue(basis=basis), *auftraege.erledigte(basis=basis)],
                               zustand_().lesen()["reihe_von"])


def _reihe_seite(request: Request, reihe_id: str, fehler: list[str] | None = None, thema: str = "",
                 status: int = 200):
    reihen, reihe = _reihe(reihe_id)
    z = zustand_().lesen()
    e = logik.reihe_ansicht(reihe, reihen, _alle_auftraege(), datetime.now(ZONE),
                            _entwuerfe(), set(z["final"]), z["eigene"],
                            logik.reihe_stunden(reihe), z["stunde_von"], _ausblenden(z))
    return vorlagen.TemplateResponse(request, "reihe.html", {
        "e": e, "token": logik.formular_token(GEHEIM), "fehler": fehler or [], "thema": thema,
        "thema_max": pflege.LAENGE["thema"], "p": reihe_pflege(struktur_(), reihe_id),
        "hinweis": "" if fehler else logik.HINWEISE.get(request.query_params.get("erledigt") or "", ""),
        **rahmen(reihen, logik.krumen(reihe=reihe), reihe["id"], neu_hier=_neu_hier(reihe))}, status_code=status)


@app.get("/reihe/{reihe_id}", response_class=HTMLResponse)
def seite_reihe(request: Request, reihe_id: str):
    return _reihe_seite(request, reihe_id)


def _neu_hier(reihe: dict, nr: int | None = None) -> str:
    """„+ Neu hier“ nur an laufenden Reihen (abgeschlossene nehmen keine Aufträge mehr an, reihe_pruefen)."""
    return logik.neu_link(reihe["id"], nr) if reihe["laufend"] else ""


def _stunde_seite(request: Request, reihe_id: str, nr_text: str, hinweis: str = "", fehler: list[str] | None = None,
                  thema: str = "", status: int = 200):
    reihen, reihe = _reihe(reihe_id)
    z = zustand_().lesen()
    stunden = logik.reihe_stunden(reihe)
    nr = logik.stunde_nummer(nr_text, len(stunden))
    if nr is None:
        raise HTTPException(404)
    zeilen = logik.zeilen_je_reihe(reihen, _alle_auftraege(), datetime.now(ZONE),
                                   _entwuerfe(), set(z["final"]),
                                   z["eigene"], _ausblenden(z)).get(reihe_id, [])
    e = logik.stunde_ansicht(reihe, nr, stunden, zeilen, z["stunde_von"])
    return vorlagen.TemplateResponse(request, "stunde.html", {
        "e": e, "reihe": reihe, "token": logik.formular_token(GEHEIM), "hinweis": hinweis, "fehler": fehler or [],
        "thema": thema if fehler else stunden[nr - 1]["thema"], "thema_max": pflege.LAENGE["thema"],
        "p": stunde_pflege(struktur_(), reihe_id, nr),
        **rahmen(reihen, logik.krumen(e["unter"], reihe), reihe["id"], neu_hier=_neu_hier(reihe, nr), stunde=nr)},
        status_code=status)


@app.get("/reihe/{reihe_id}/stunde/{nr}", response_class=HTMLResponse)
def seite_stunde(request: Request, reihe_id: str, nr: str):
    hinweis = logik.HINWEISE.get(request.query_params.get("erledigt") or "", "")
    return _stunde_seite(request, reihe_id, nr, hinweis)


# --- Struktur pflegen (docs/struktur-pflege-plan.md, Abschnitte 4 und 5; Bauschritt 5) ---------------------------------
# Jede Maske schreibt nur über agentkit.strukturpflege (Block-Editor, Rückgängig, Commit über commit-daten.sh); die App
# schreibt nie selbst in reihen.toml. Nach jeder Aktion steht oben „… · Rückgängig“ (?aktion=<id>), dazu „Letzte
# Änderungen“ unter „Ich“. Rückfragen nur bei belegtem Ziel und beim Löschen oder Archivieren einer Klasse oder eines
# Fachs (Grundsatz Flexibilität, Jan 03.11.). Die Lerngruppe steht nie in einem Log (Plan Abschnitt 6).

MELDEN = None  # Meldung an Jan; None = agentkit-Standard (meldungen.melden("webapp", …)), Tests setzen eine Funktion
PFLEGE_FELDER = 300  # Masken mit Terminlisten (je Termin ein Häkchen)
_NACH_AKTION: dict[str, list[str]] = {}  # Aktion -> Hinweise von agentkit für den Hinweis direkt danach (im Speicher)


def heute() -> date:
    return datetime.now(ZONE).date()


def umgebung() -> sp.Umgebung:
    """Wo agentkit.strukturpflege schreibt: die Instanz der App; Aktionsablage und Zustand in data/ der App."""
    return sp.Umgebung(instanz=INSTANZ, webapp_daten=DATEN, heute=heute(), melden=MELDEN, log=logger)


def struktur_() -> struktur.Struktur | None:
    """Struktur zum Pflegen (aufgelöst, mit Stundenplan und Terminen); kaputt: None (steht schon im Log)."""
    try:
        return struktur.laden(INSTANZ)
    except (struktur.StrukturFehler, OSError, UnicodeDecodeError):
        return None


def kalender_(s) -> termine.Kalender | None:
    if s is None or not s.schule.get("bundesland"):
        return None
    try:
        return s.kalender()
    except termine.TermineFehler as fehler_:
        logger.error("Kalender: %s", fehler_)
        return None


def _objekt(s, kennung_: str, ebene: str) -> dict:
    """Objekt einer Ebene zum Pflegen; unbekannt oder Datei im alten Format: 404."""
    o = s.objekt(kennung_) if s is not None and s.format == "neu" else None
    if o is None or o["ebene"] != ebene:
        raise HTTPException(404)
    return o


async def pflegen(operation: str, argumente: dict, gesehen: dict | None = None) -> tuple[sp.Ausgang | None, str]:
    """agentkit.strukturpflege.ausfuehren in einem Faden (Sperre und Schreiben der Datei; den Commit macht agentkit
    im Hintergrund, Speichern wartet nicht darauf). (Ausgang, "") oder (None, Fehlertext für Lia). termine.Belegt
    geht an den Aufrufer (Rückfrage)."""
    try:
        aus = await run_in_threadpool(sp.ausfuehren, operation, argumente, gesehen or None, sp.VON_LIA, umgebung())
    except termine.Belegt:
        raise
    except sp.HaengtDran as fehler_:
        return None, pflege.loeschen_text(fehler_.haken)
    except sp.PflegeFehler as fehler_:  # Texte von agentkit nennen nie die Lerngruppe
        logger.warning("Struktur: %s abgewiesen: %s", operation, fehler_)
        return None, pflege.fehler_text(fehler_)
    except OSError as fehler_:
        logger.error("Struktur: %s nicht gespeichert: %s", operation, fehler_)
        return None, logik.FEHLGESCHLAGEN
    if aus.aktion:
        _NACH_AKTION[aus.aktion] = list(aus.hinweise)
        for alt in list(_NACH_AKTION)[:-50]:
            del _NACH_AKTION[alt]
    return aus, ""


def nach(ziel: str, aus: sp.Ausgang) -> RedirectResponse:
    """Nach einer Aktion: zur Seite mit dem Hinweis „… · Rückgängig“ (oder „Nichts geändert“)."""
    pfad, _, anker = ziel.partition("#")
    frage = f"aktion={aus.aktion}" if aus.geaendert and aus.aktion else "erledigt=nichts"
    return RedirectResponse(f"{pfad}?{frage}" + (f"#{anker}" if anker else ""), status_code=303)


def aktion_hinweis(aktion_id: str | None) -> dict | None:
    """Für basis.html: Text der Aktion aus der Aktionsablage, ob Rückgängig noch geht, Hinweise von agentkit."""
    if not aktion_id:
        return None
    eintrag = next((a for a in sp.letzte(30, umgebung()) if a["id"] == aktion_id), None)
    if eintrag is None:
        return None
    return {"id": aktion_id, "text": eintrag["text"], "zurueck": not eintrag["zurueckgenommen"],
            "hinweise": _NACH_AKTION.get(aktion_id, [])}


vorlagen.env.globals["aktion_hinweis"] = aktion_hinweis
vorlagen.env.globals["formular_token"] = lambda: logik.formular_token(GEHEIM)


async def pflege_formular(request: Request, wofuer: str):
    """Formular einer Maske (Herkunft, Größe, viele Felder) und ob das Token passt."""
    form = await formular_lesen(request, wofuer, 0, max_felder=PFLEGE_FELDER)
    return form, logik.token_passt(GEHEIM, str(form.get("token") or ""))


def _wert(form) -> Callable[[str], str]:
    return lambda name: str(form.get(name) or "")


def _app_reihe(reihe_id: str) -> dict | None:
    return next((r for r in reihen_laden() if r["id"] == reihe_id), None)


def _pflege_ort(s, kennung_: str, hier: str) -> dict:
    """Brotkrumen und Baum für eine Maske am Objekt kennung_ (Fach, Klasse, Reihe oder Stunde)."""
    o = s.objekt(kennung_) if s is not None else None
    reihen = reihen_laden()
    if o is None:
        return rahmen(reihen, logik.krumen(hier))
    if o["ebene"] == "stunde":
        o = s.objekt(o["reihe_id"])
    if o["ebene"] == "reihe":
        r = _app_reihe(o["id"])
        return rahmen(reihen, logik.krumen(hier, r) if r else logik.krumen(hier), o["id"])
    fach = s.objekt(o["fach_id"]) if o["ebene"] == "klasse" else o
    teile = [{"text": fach["name"], "link": f"/fach/{fach['id']}"}]
    if o["ebene"] == "klasse":
        teile.append({"text": _klasse_name(o), "link": f"/klasse/{o['id']}"})
        return rahmen(reihen, {"teile": teile, "hier": hier}, logik.klasse_aktiv(o["id"]))
    return rahmen(reihen, {"teile": teile, "hier": hier}, logik.fach_aktiv(o["id"]))


def _klasse_name(k: dict) -> str:
    return logik.gruppe_name(k["name"]) + (f" · {k['schuljahr']}" if k["im_archiv"] and k["schuljahr"] else "")


def _klassen_wahl(s, ohne: str = "", mit_archiv: bool = True) -> list[dict]:
    """Klassen für „Verschieben“ und „Kopieren“: „Ethik · Klasse 8 (2026/27)“."""
    return [{"id": k["id"], "text": f"{k['fach']} · {logik.gruppe_name(k['name'])}"
             + (f" ({k['schuljahr']})" if k["schuljahr"] else "") + (" · Archiv" if k["im_archiv"] else "")}
            for k in s.klassen if k["id"] != ohne and (mit_archiv or not k["im_archiv"])]


def _haken(s, kennung_: str) -> list[dict]:
    try:
        return s.haengt_dran(kennung_, DATEN)
    except struktur.StrukturFehler:
        return []


def _seite(request: Request, vorlage: str, werte: dict, ort: dict, status: int = 200):
    return vorlagen.TemplateResponse(request, vorlage, {"token": logik.formular_token(GEHEIM), "fehler": [],
                                                        **werte, **ort}, status_code=status)


def _rueckfrage(request: Request, s, kennung_: str, titel: str, text: str, frage: str, action: str, form,
                knoepfe: list[tuple[str, str, str]], zurueck: str):
    """Einmal fragen (belegtes Ziel; Löschen bzw. Archivieren einer Klasse oder eines Fachs). Die Felder des
    Formulars gehen unverändert mit, dazu der gewählte Knopf."""
    felder = [(k, str(v)) for k, v in form.multi_items() if k not in ("token", "bei_belegt", "bestaetigt")]
    return _seite(request, "rueckfrage.html", {
        "e": {"titel": titel}, "text": text, "frage": frage, "action": action, "felder": felder,
        "knoepfe": knoepfe, "zurueck": zurueck}, _pflege_ort(s, kennung_, titel))


def _belegt(request: Request, s, kennung_: str, fehler_: termine.Belegt, action: str, form, zurueck: str):
    return _rueckfrage(request, s, kennung_, "Der Termin ist belegt", pflege.belegt_text(s, fehler_),
                       "Was soll mit dem passieren, was dort liegt?", action, form,
                       [("bei_belegt", termine.NACHRUECKEN, "Dahinter alles nachrücken"),
                        ("bei_belegt", termine.TAUSCHEN, "Tauschen")], zurueck)


def _stunde_link(s, stunde_id: str) -> str:
    """Seite einer Stunde nach einer Aktion (Nummer nach dem Verschieben); ausgeblendet: die Reihe."""
    o = s.objekt(stunde_id) if s is not None else None
    if o is None or o["ebene"] != "stunde":
        return "/"
    return f"/reihe/{o['reihe_id']}/stunde/{o['nr']}" if o["nr"] else f"/reihe/{o['reihe_id']}#ausgeblendet"


def _link(s, kennung_: str) -> str:
    o = s.objekt(kennung_) if s is not None else None
    if o is None:
        return "/"
    return _stunde_link(s, kennung_) if o["ebene"] == "stunde" else f"/{o['ebene']}/{kennung_}"


def _oben(s, kennung_: str) -> str:
    """Seite über dem Objekt (nach dem Löschen)."""
    o = s.objekt(kennung_)
    return {"fach": "/", "klasse": f"/fach/{o.get('fach_id')}", "reihe": f"/klasse/{o.get('klasse_id')}",
            "stunde": f"/reihe/{o.get('reihe_id')}"}[o["ebene"]]


def _ziel_danach(pfad: str) -> str:
    """Nach Rückgängig zurück auf die Seite, wenn es ihr Objekt noch gibt; sonst „Ich“ (Letzte Änderungen)."""
    m = re.fullmatch(r"/(fach|klasse|reihe)/([a-z0-9-]+)(/stunde/(\d+))?(/.*)?", pfad)
    if not m:
        return pfad
    s = struktur_()
    o = s.objekt(m[2]) if s is not None else None
    if o is None or o["ebene"] != m[1]:
        return "/ich#aenderungen"
    if m[4] and int(m[4]) > len(o.get("stunden") or []):
        return f"/reihe/{m[2]}"
    return pfad if not m[5] else f"/{m[1]}/{m[2]}"


@app.post("/rueckgaengig", response_class=HTMLResponse)
async def rueckgaengig(request: Request):
    """Gegen-Aktion als neue Änderung (agentkit, eigener Commit „Rückgängig: …“)."""
    form, token_ok = await pflege_formular(request, "Rückgängig")
    zurueck = logik.zurueck_pfad(str(form.get("zurueck") or ""))
    if not token_ok:
        return _meldung(request, "Rückgängig", pflege.VERALTET, zurueck, 400)
    try:
        aus = await run_in_threadpool(sp.rueckgaengig, str(form.get("aktion") or ""), sp.VON_LIA, umgebung())
    except sp.PflegeFehler as fehler_:
        logger.warning("Rückgängig abgewiesen: %s", fehler_)
        return _meldung(request, "Rückgängig geht nicht", pflege.fehler_text_rueckgaengig(fehler_), zurueck, 409)
    except OSError as fehler_:
        logger.error("Rückgängig nicht gespeichert: %s", fehler_)
        return _meldung(request, "Rückgängig geht nicht", logik.FEHLGESCHLAGEN, zurueck, 500)
    _NACH_AKTION[aus.aktion or ""] = list(aus.hinweise)
    return nach(_ziel_danach(zurueck), aus)


def _meldung(request: Request, titel: str, text: str, zurueck: str, status: int):
    return _seite(request, "meldung.html", {"e": {"titel": titel}, "text": text, "zurueck": zurueck},
                  rahmen(reihen_laden(), logik.krumen(titel)), status)


# Fach

def _fach_seite(request: Request, s, fach: dict | None, werte: dict, fehler: list[str] | None = None,
                status: int = 200):
    titel = "Neues Fach" if fach is None else "Fach bearbeiten"
    extra = {}
    if fach is not None:
        haken = _haken(s, fach["id"])
        extra = {"objekt": fach, "loeschen": not haken, "haken": pflege.haken_text(haken)}
    return _seite(request, "pflege_fach.html", {
        "e": {"titel": titel, "unter": fach["name"] if fach else "Fach anlegen"}, "werte": werte, "fach": fach,
        "laenge": pflege.LAENGE, "fehler": fehler or [], **extra},
        _pflege_ort(s, fach["id"], titel) if fach else rahmen(reihen_laden(), logik.krumen(titel)), status)


@app.get("/fach/neu", response_class=HTMLResponse)
def seite_fach_neu(request: Request):
    s = struktur_()
    if s is None or s.format != "neu":
        raise HTTPException(404)
    return _fach_seite(request, s, None, {"name": "", "kurzform": ""})


@app.post("/fach/neu", response_class=HTMLResponse)
async def fach_neu(request: Request):
    s = struktur_()
    if s is None or s.format != "neu":
        raise HTTPException(404)
    form, token_ok = await pflege_formular(request, "Fach anlegen")
    name, fehler = pflege.text(_wert(form)("name"), "name", pflege.PFLICHT["fach"])
    werte = {"name": name, "kurzform": ""}
    if not token_ok:
        fehler = [pflege.VERALTET]
    if not fehler:
        aus, f = await pflegen("fach_anlegen", {"name": name})
        if aus:
            return nach(f"/fach/{aus.neue_id}", aus)
        fehler = [f]
    return _fach_seite(request, s, None, werte, fehler, 400)


@app.get("/fach/{fach_id}/bearbeiten", response_class=HTMLResponse)
def seite_fach_bearbeiten(request: Request, fach_id: str):
    s = struktur_()
    f = _objekt(s, fach_id, "fach")
    return _fach_seite(request, s, f, {"name": f["name"], "kurzform": f["kurzform"]})


@app.post("/fach/{fach_id}/bearbeiten", response_class=HTMLResponse)
async def fach_bearbeiten(request: Request, fach_id: str):
    s = struktur_()
    f = _objekt(s, fach_id, "fach")
    form, token_ok = await pflege_formular(request, "Fach ändern")
    w = _wert(form)
    name, fehler = pflege.text(w("name"), "name", pflege.PFLICHT["fach"])
    kurzform, fehler2 = pflege.text(w("kurzform"), "kurzform")
    fehler = [pflege.VERALTET] if not token_ok else fehler + fehler2
    if not fehler:
        neu, gesehen = pflege.geaendert({"name": (name, w("alt_name")), "kurzform": (kurzform, w("alt_kurzform"))})
        if not neu:
            return RedirectResponse(f"/fach/{fach_id}?erledigt=nichts", status_code=303)
        aus, text_ = await pflegen("fach_aendern", {"fach": fach_id, **neu}, {fach_id: gesehen})
        if aus:
            return nach(f"/fach/{fach_id}", aus)
        fehler = [text_]
    return _fach_seite(request, s, f, {"name": name, "kurzform": kurzform}, fehler, 400)


# Klasse/Kurs

def _klasse_seite(request: Request, s, vorlage: str, titel: str, werte: dict, ort_id: str,
                  fehler: list[str] | None = None, status: int = 200, **extra):
    return _seite(request, vorlage, {
        "e": {"titel": titel, "unter": extra.pop("unter", "")}, "werte": werte, "fehler": fehler or [],
        "laenge": pflege.LAENGE, "tage": pflege.TAG_NAMEN, "stunden_wahl": pflege.STUNDEN,
        "bundeslaender": pflege.BUNDESLAENDER, **extra}, _pflege_ort(s, ort_id, titel), status)


def _grenzen(kal: termine.Kalender | None, schuljahr: str) -> tuple[date, date] | None:
    if kal is None:
        return None
    try:
        return kal.schuljahr(schuljahr)
    except termine.TermineFehler as fehler_:
        logger.warning("Schuljahr %s: %s", schuljahr, fehler_)
        return None


def _stundenplan_lesen(w, kal, schuljahr: str, mit_zeitraum: bool = True):
    """(Einträge, Zeilen der Maske, Zahl der Zeilen, Fehler) aus dem Formular; Einträge mit ab und bis."""
    anzahl = pflege.zeilen_zahl(w("zeilen"), bool(w("mehr")))
    eintraege, gezeigt, fehler = pflege.stundenplan(w, anzahl)
    if eintraege and mit_zeitraum and not fehler:
        ab, bis, fehler = pflege.zeitraum(w("ab"), w("bis"), _grenzen(kal, schuljahr))
        if fehler == [pflege.BUNDESLAND_FEHLT] and kal is not None:
            fehler = [pflege.FERIEN_FEHLEN.format(schuljahr=schuljahr)]
        eintraege = pflege.mit_zeitraum(eintraege, ab, bis)
    return eintraege, pflege.aufgefuellt(gezeigt, anzahl), anzahl, fehler


@app.get("/fach/{fach_id}/klasse/neu", response_class=HTMLResponse)
def seite_klasse_neu(request: Request, fach_id: str):
    s = struktur_()
    f = _objekt(s, fach_id, "fach")
    werte = {"name": "", "schuljahr": pflege.schuljahr_vorschlag(heute(), kalender_(s)), "ab": "", "bis": "",
             "bundesland": s.schule.get("bundesland", "")}
    return _klasse_seite(request, s, "pflege_klasse_neu.html", "Neue Klasse oder neuer Kurs", werte, fach_id,
                         unter=f["name"], fach=f, zeilen=pflege.aufgefuellt([], pflege.ZEILEN_MIN),
                         anzahl=pflege.ZEILEN_MIN, bundesland_fehlt=not s.schule.get("bundesland"))


@app.post("/fach/{fach_id}/klasse/neu", response_class=HTMLResponse)
async def klasse_neu(request: Request, fach_id: str):
    s = struktur_()
    f = _objekt(s, fach_id, "fach")
    form, token_ok = await pflege_formular(request, "Klasse anlegen")
    w = _wert(form)
    name, fehler = pflege.text(w("name"), "name", pflege.PFLICHT["klasse"])
    schuljahr, f_sj = pflege.schuljahr(w("schuljahr"))
    bundesland = s.schule.get("bundesland") or (w("bundesland") if w("bundesland") in pflege.BUNDESLAENDER else "")
    kal = kalender_(s) or (termine.kalender(bundesland) if bundesland else None)
    zeitplan, zeilen_, anzahl, f_plan = _stundenplan_lesen(w, kal, schuljahr)
    werte = {"name": name, "schuljahr": schuljahr, "ab": w("ab"), "bis": w("bis"), "bundesland": bundesland}

    def zeigen(fehler_: list[str], status: int):
        return _klasse_seite(request, s, "pflege_klasse_neu.html", "Neue Klasse oder neuer Kurs", werte, fach_id,
                             fehler_, status, unter=f["name"], fach=f, zeilen=zeilen_, anzahl=anzahl,
                             bundesland_fehlt=not s.schule.get("bundesland"))
    if w("mehr"):  # „+ weiterer Termin“: eine Zeile mehr, nichts gespeichert
        return zeigen([], 200)
    fehler = [pflege.VERALTET] if not token_ok else fehler + f_sj + f_plan
    if fehler:
        return zeigen(fehler, 400)
    if bundesland and not s.schule.get("bundesland"):  # Schule (einmal): Ferien und Feiertage
        aus, text_ = await pflegen("schule_setzen", {"bundesland": bundesland})
        if not aus:
            return zeigen([text_], 400)
    aus, text_ = await pflegen("klasse_anlegen", {"fach": fach_id, "name": name, "schuljahr": schuljahr,
                                                  "zeitplan": zeitplan or None})
    if not aus:
        return zeigen([text_], 400)
    return nach(f"/klasse/{aus.neue_id}", aus)


def _klasse_bearbeiten_seite(request: Request, s, k: dict, werte: dict, fehler: list[str] | None = None,
                             status: int = 200, lerngruppe: str | None = None):
    haken = _haken(s, k["id"])
    return _klasse_seite(
        request, s, "pflege_klasse.html", "Bearbeiten", werte, k["id"], fehler, status, unter=_klasse_name(k),
        klasse=k, lerngruppe=k["lerngruppe"] if lerngruppe is None else lerngruppe,
        lerngruppe_alt=k["lerngruppe"], hinweis_lerngruppe=pflege.LERNGRUPPE_HINWEIS,
        faecher=[f for f in s.faecher if f["id"] != k["fach_id"]], loeschen=not haken,
        haken=pflege.haken_text(haken))


@app.get("/klasse/{klasse_id}/bearbeiten", response_class=HTMLResponse)
def seite_klasse_bearbeiten(request: Request, klasse_id: str):
    s = struktur_()
    k = _objekt(s, klasse_id, "klasse")
    return _klasse_bearbeiten_seite(request, s, k, {"name": k["name"], "schuljahr": k["schuljahr"]})


@app.post("/klasse/{klasse_id}/bearbeiten", response_class=HTMLResponse)
async def klasse_bearbeiten(request: Request, klasse_id: str):
    s = struktur_()
    k = _objekt(s, klasse_id, "klasse")
    form, token_ok = await pflege_formular(request, "Klasse ändern")
    w = _wert(form)
    name, fehler = pflege.text(w("name"), "name", pflege.PFLICHT["klasse"])
    schuljahr, f_sj = pflege.schuljahr(w("schuljahr"))
    fehler = [pflege.VERALTET] if not token_ok else fehler + f_sj
    if not fehler:
        neu, gesehen = pflege.geaendert({"name": (name, w("alt_name")), "schuljahr": (schuljahr, w("alt_schuljahr"))})
        if not neu:
            return RedirectResponse(f"/klasse/{klasse_id}?erledigt=nichts", status_code=303)
        aus, text_ = await pflegen("klasse_aendern", {"klasse": klasse_id, **neu}, {klasse_id: gesehen})
        if aus:
            return nach(f"/klasse/{klasse_id}", aus)
        fehler = [text_]
    return _klasse_bearbeiten_seite(request, s, k, {"name": name, "schuljahr": schuljahr}, fehler, 400)


@app.post("/klasse/{klasse_id}/lerngruppe", response_class=HTMLResponse)
async def klasse_lerngruppe(request: Request, klasse_id: str):
    """Lerngruppe (lerngruppen.toml, nicht im Repo). Ihr Text geht in kein Log und keinen Hinweis."""
    s = struktur_()
    k = _objekt(s, klasse_id, "klasse")
    form, token_ok = await pflege_formular(request, "Lerngruppe")
    w = _wert(form)
    text_, fehler = pflege.text(w("lerngruppe"), "lerngruppe")
    fehler = [pflege.VERALTET] if not token_ok else fehler
    if not fehler:
        neu, gesehen = pflege.geaendert({"lerngruppe": (text_, w("alt_lerngruppe"))})
        if not neu:
            return RedirectResponse(f"/klasse/{klasse_id}?erledigt=nichts", status_code=303)
        aus, f = await pflegen("lerngruppe_setzen", {"klasse": klasse_id, "text": text_}, {klasse_id: gesehen})
        if aus:
            return nach(f"/klasse/{klasse_id}", aus)
        fehler = [f]
    return _klasse_bearbeiten_seite(request, s, k, {"name": k["name"], "schuljahr": k["schuljahr"]}, fehler, 400,
                                    lerngruppe=text_)


@app.post("/klasse/{klasse_id}/verschieben", response_class=HTMLResponse)
async def klasse_verschieben(request: Request, klasse_id: str):
    s = struktur_()
    k = _objekt(s, klasse_id, "klasse")
    form, token_ok = await pflege_formular(request, "Klasse verschieben")
    werte = {"name": k["name"], "schuljahr": k["schuljahr"]}
    if not token_ok:
        return _klasse_bearbeiten_seite(request, s, k, werte, [pflege.VERALTET], 400)
    aus, text_ = await pflegen("klasse_verschieben", {"klasse": klasse_id, "fach": _wert(form)("fach")})
    if aus:
        return nach(f"/klasse/{klasse_id}", aus)
    return _klasse_bearbeiten_seite(request, s, k, werte, [text_], 400)


def _stundenplan_seite(request: Request, s, k: dict, werte: dict, zeilen_: list[dict], anzahl: int,
                       fehler: list[str] | None = None, status: int = 200):
    return _klasse_seite(request, s, "pflege_stundenplan.html", "Stundenplan", werte, k["id"], fehler, status,
                         unter=_klasse_name(k), klasse=k, zeilen=zeilen_, anzahl=anzahl,
                         hat_plan=bool(k["zeitplan"]))


@app.get("/klasse/{klasse_id}/stundenplan", response_class=HTMLResponse)
def seite_stundenplan(request: Request, klasse_id: str):
    s = struktur_()
    k = _objekt(s, klasse_id, "klasse")
    kal = kalender_(s)
    stichtag = None
    if kal is not None and k["schuljahr"]:
        try:
            stichtag = kal.halbjahr_stichtag(k["schuljahr"])
        except termine.TermineFehler:
            stichtag = None
    vorbelegt = stichtag if stichtag and stichtag > heute() else None
    zeilen_ = pflege.stundenplan_zeilen(k["zeitplan"], vorbelegt or heute())
    anzahl = max(pflege.ZEILEN_MIN, len(zeilen_) + 1)
    werte = {"ab": min((e["ab"] for e in k["zeitplan"]), default=""),
             "bis": max((e["bis"] for e in k["zeitplan"]), default=""),
             "stichtag": vorbelegt.isoformat() if vorbelegt else "", "wie": "ab" if k["zeitplan"] else "ganz"}
    return _stundenplan_seite(request, s, k, werte, pflege.aufgefuellt(zeilen_, anzahl), anzahl)


@app.post("/klasse/{klasse_id}/stundenplan", response_class=HTMLResponse)
async def stundenplan(request: Request, klasse_id: str):
    """Stundenplan eintragen bzw. ändern, oder ab einem Stichtag neu (Halbjahr: Stunden danach bekommen neue Daten)."""
    s = struktur_()
    k = _objekt(s, klasse_id, "klasse")
    form, token_ok = await pflege_formular(request, "Stundenplan")
    w = _wert(form)
    wie = "ab" if w("wie") == "ab" and k["zeitplan"] else "ganz"
    kal = kalender_(s)
    zeitplan, zeilen_, anzahl, fehler = _stundenplan_lesen(w, kal, k["schuljahr"], wie == "ganz")
    werte = {"ab": w("ab"), "bis": w("bis"), "stichtag": w("stichtag"), "wie": wie}
    if w("mehr"):
        return _stundenplan_seite(request, s, k, werte, zeilen_, anzahl)
    if not token_ok:
        fehler = [pflege.VERALTET]
    if not fehler and kal is None and (zeitplan or wie == "ab"):
        fehler = [pflege.BUNDESLAND_FEHLT + " Du kannst es unter „Ich“ eintragen."]
    if not fehler and wie == "ab":
        stichtag = pflege.datum(w("stichtag"))
        ende = max((e["bis"] for e in k["zeitplan"]), default="")
        if stichtag is None:
            fehler = ["Ab wann gilt der neue Stundenplan? Bitte ein Datum wählen."]
        elif not zeitplan:
            fehler = ["Bitte mindestens einen Termin angeben."]
        else:
            aus, text_ = await pflegen("stundenplan_ab", {
                "klasse": klasse_id, "stichtag": stichtag.isoformat(),
                "zeitplan": [{**e, "bis": max(ende, stichtag.isoformat())} for e in zeitplan]})
            if aus:
                return nach(f"/klasse/{klasse_id}#termine", aus)
            fehler = [text_]
    elif not fehler:
        aus, text_ = await pflegen("stundenplan_setzen", {"klasse": klasse_id, "zeitplan": zeitplan})
        if aus:
            return nach(f"/klasse/{klasse_id}#termine", aus)
        fehler = [text_]
    return _stundenplan_seite(request, s, k, werte, zeilen_, anzahl, fehler, 400)


def _uebernehmen_seite(request: Request, s, k: dict, werte: dict, zeilen_: list[dict], anzahl: int,
                       fehler: list[str] | None = None, status: int = 200):
    return _klasse_seite(request, s, "pflege_uebernehmen.html", "Ins nächste Schuljahr übernehmen", werte, k["id"],
                         fehler, status, unter=_klasse_name(k), klasse=k, zeilen=zeilen_, anzahl=anzahl,
                         hat_lerngruppe=bool(k["lerngruppe"]))


@app.get("/klasse/{klasse_id}/uebernehmen", response_class=HTMLResponse)
def seite_uebernehmen(request: Request, klasse_id: str):
    s = struktur_()
    k = _objekt(s, klasse_id, "klasse")
    werte = {"name": k["name"], "schuljahr": pflege.naechstes_schuljahr(k["schuljahr"])
             or pflege.schuljahr_vorschlag(heute(), kalender_(s)), "ab": "", "bis": "", "lerngruppe": ""}
    return _uebernehmen_seite(request, s, k, werte, pflege.aufgefuellt([], pflege.ZEILEN_MIN), pflege.ZEILEN_MIN)


@app.post("/klasse/{klasse_id}/uebernehmen", response_class=HTMLResponse)
async def uebernehmen(request: Request, klasse_id: str):
    s = struktur_()
    k = _objekt(s, klasse_id, "klasse")
    form, token_ok = await pflege_formular(request, "Übernehmen")
    w = _wert(form)
    name, fehler = pflege.text(w("name"), "name", pflege.PFLICHT["klasse"])
    schuljahr, f_sj = pflege.schuljahr(w("schuljahr"))
    zeitplan, zeilen_, anzahl, f_plan = _stundenplan_lesen(w, kalender_(s), schuljahr)
    werte = {"name": name, "schuljahr": schuljahr, "ab": w("ab"), "bis": w("bis"), "lerngruppe": w("lerngruppe")}
    if w("mehr"):
        return _uebernehmen_seite(request, s, k, werte, zeilen_, anzahl)
    fehler = [pflege.VERALTET] if not token_ok else fehler + f_sj + f_plan
    if not fehler and zeitplan and kalender_(s) is None:
        fehler = [pflege.BUNDESLAND_FEHLT + " Du kannst es unter „Ich“ eintragen."]
    if not fehler:
        aus, text_ = await pflegen("klasse_kopieren", {
            "klasse": klasse_id, "name": name, "schuljahr": schuljahr, "zeitplan": zeitplan or None,
            "lerngruppe_mitnehmen": w("lerngruppe") == "1"})
        if aus:
            return nach(f"/klasse/{aus.neue_id}", aus)
        fehler = [text_]
    return _uebernehmen_seite(request, s, k, werte, zeilen_, anzahl, fehler, 400)


def _termine_von(s, klassen_id: str) -> tuple[list[dict], str]:
    """Termine der Klasse für Ansicht und Auswahl; geht es nicht (Bundesland, Ferien fehlen): Text für Lia."""
    k = s.objekt(klassen_id)
    if not (k["zeitplan"] or k["zusatz"]):
        return [], ""
    if k["zeitplan"] and not s.schule.get("bundesland"):
        return [], pflege.BUNDESLAND_FEHLT + " Du kannst es unter „Ich“ eintragen."
    try:
        return pflege.termine_liste(s, klassen_id, s.kalender() if k["zeitplan"] else None, heute()), ""
    except termine.TermineFehler as fehler_:
        logger.error("Termine von %s: %s", klassen_id, fehler_)
        return [], "Die Termine kann ich gerade nicht ausrechnen (Ferien fehlen). Sag Jan bitte Bescheid."


@app.get("/klasse/{klasse_id}/ausfall", response_class=HTMLResponse)
def seite_ausfall(request: Request, klasse_id: str, termin: str = ""):
    s = struktur_()
    k = _objekt(s, klasse_id, "klasse")
    t = next((x for x in _termine_von(s, klasse_id)[0] if x["kennung"] == termin and not x["ausgefallen"]), None)
    if t is None:
        raise HTTPException(404)
    return _klasse_seite(request, s, "pflege_ausfall.html", "Termin fällt aus", {}, klasse_id,
                         unter=_klasse_name(k), klasse=k, termin=t)


@app.post("/klasse/{klasse_id}/ausfall", response_class=HTMLResponse)
async def ausfall(request: Request, klasse_id: str):
    s = struktur_()
    k = _objekt(s, klasse_id, "klasse")
    form, token_ok = await pflege_formular(request, "Ausfall")
    w = _wert(form)
    t = next((x for x in _termine_von(s, klasse_id)[0] if x["kennung"] == w("termin") and not x["ausgefallen"]), None)
    if t is None:
        raise HTTPException(404)
    folge = w("folge") if t["stunde"] else termine.NACHRUECKEN  # freier Termin: nur streichen
    fehler = [pflege.VERALTET] if not token_ok else [] if folge in (termine.NACHRUECKEN, "faellt_weg") else [
        "Bitte wählen: Alles rückt nach, oder diese Stunde fällt weg."]
    if not fehler:
        aus, text_ = await pflegen("ausfall", {"klasse": klasse_id, "termin": t["kennung"], "folge": folge})
        if aus:
            return nach(f"/klasse/{klasse_id}#termine", aus)
        fehler = [text_]
    return _klasse_seite(request, s, "pflege_ausfall.html", "Termin fällt aus", {}, klasse_id, fehler, 400,
                         unter=_klasse_name(k), klasse=k, termin=t)


async def _klasse_aktion(request: Request, klasse_id: str, wofuer: str, operation: str, argumente) -> RedirectResponse:
    """Kleine Aktionen an der Klasse aus der Klassen-Ansicht (Knopf ohne Maske); Fehler als Meldung."""
    s = struktur_()
    _objekt(s, klasse_id, "klasse")
    form, token_ok = await pflege_formular(request, wofuer)
    zurueck = f"/klasse/{klasse_id}"
    if not token_ok:
        return _meldung(request, wofuer, pflege.VERALTET, zurueck, 400)
    args, fehler = argumente(_wert(form))
    if not fehler:
        aus, text_ = await pflegen(operation, {"klasse": klasse_id, **args})
        if aus:
            return nach(f"{zurueck}#termine", aus)
        fehler = [text_]
    return _meldung(request, wofuer, " ".join(fehler), zurueck, 400)


@app.post("/klasse/{klasse_id}/ausfall-aufheben", response_class=HTMLResponse)
async def ausfall_aufheben(request: Request, klasse_id: str):
    return await _klasse_aktion(request, klasse_id, "Termin findet statt", "ausfall_aufheben",
                                lambda w: ({"termin": w("termin")}, []))


@app.post("/klasse/{klasse_id}/zusatztermin", response_class=HTMLResponse)
async def zusatztermin(request: Request, klasse_id: str):
    def argumente(w):
        d, st = pflege.datum(w("datum")), w("stunde")
        if d is None or not st.isdigit() or int(st) not in pflege.STUNDEN:
            return {}, ["Für den Zusatztermin bitte Datum und Stunde wählen."]
        return {"termin": termine.kennung(d, int(st))}, []
    return await _klasse_aktion(request, klasse_id, "Zusatztermin", "zusatztermin", argumente)


@app.post("/klasse/{klasse_id}/zusatztermin-entfernen", response_class=HTMLResponse)
async def zusatztermin_entfernen(request: Request, klasse_id: str):
    return await _klasse_aktion(request, klasse_id, "Zusatztermin entfernen", "zusatztermin_entfernen",
                                lambda w: ({"termin": w("termin")}, []))


# Reihe

def _wahl_werte(w, liste) -> dict:
    """Werte des Termin-Bausteins zum erneuten Zeigen (Häkchen, ab, Anzahl)."""
    return {"gewaehlt": set(liste("termin")), "ab": w("ab"), "anzahl": w("anzahl")}


def _liste(form) -> Callable[[str], list[str]]:
    return lambda name: [str(v) for v in form.getlist(name)]


def _reihe_neu_seite(request: Request, s, k: dict, werte: dict, fehler: list[str] | None = None,
                     status: int = 200):
    liste, termine_fehler = _termine_von(s, k["id"])
    frei = [t for t in pflege.termin_optionen(liste, nur_frei=True) if not t["vergangen"]]
    werte = {"ab": pflege.erster_freier(liste, heute()), "anzahl": "", "gewaehlt": set(), **werte}
    return _klasse_seite(request, s, "pflege_reihe_neu.html", "Neue Reihe", werte, k["id"], fehler, status,
                         unter=_klasse_name(k), klasse=k, frei=frei, termine_fehler=termine_fehler,
                         ab_wahl=_ab_wahl(frei))


def _ab_wahl(frei: list[dict]) -> list[dict]:
    """„ab …“: je Datum mit freiem Termin ein Eintrag."""
    tage = {}
    for t in frei:
        tage.setdefault(t["datum"].isoformat(), t["text"].split(",")[0])
    return [{"wert": d, "text": text_} for d, text_ in tage.items()]


@app.get("/klasse/{klasse_id}/reihe/neu", response_class=HTMLResponse)
def seite_reihe_neu(request: Request, klasse_id: str):
    s = struktur_()
    k = _objekt(s, klasse_id, "klasse")
    return _reihe_neu_seite(request, s, k, {"titel": "", "ohne": ""})


@app.post("/klasse/{klasse_id}/reihe/neu", response_class=HTMLResponse)
async def reihe_neu(request: Request, klasse_id: str):
    s = struktur_()
    k = _objekt(s, klasse_id, "klasse")
    form, token_ok = await pflege_formular(request, "Reihe anlegen")
    w, liste = _wert(form), _liste(form)
    titel, fehler = pflege.text(w("titel"), "titel", pflege.PFLICHT["reihe"])
    wahl, f_wahl = pflege.termine_wahl(w, liste)
    ohne, f_ohne = pflege.ohne_termin_zahl(w("ohne"))
    werte = {"titel": titel, "ohne": w("ohne"), **_wahl_werte(w, liste)}
    fehler = [pflege.VERALTET] if not token_ok else fehler + f_wahl + f_ohne
    if not fehler:
        try:
            aus, text_ = await pflegen("reihe_anlegen", {"klasse": klasse_id, "titel": titel,
                                                         "stunden": [""] * ohne, **wahl})
        except termine.Belegt:
            aus, text_ = None, pflege.TERMIN_BELEGT
        if aus:
            return nach(f"/reihe/{aus.neue_id}", aus)
        fehler = [text_]
    return _reihe_neu_seite(request, s, k, werte, fehler, 400)


def _reihe_bearbeiten_seite(request: Request, s, r: dict, werte: dict, fehler: list[str] | None = None,
                            status: int = 200):
    haken = _haken(s, r["id"])
    return _seite(request, "pflege_reihe.html", {
        "e": {"titel": "Bearbeiten", "unter": r["titel"] or logik.OHNE_TITEL}, "reihe": r, "werte": werte,
        "fehler": fehler or [], "laenge": pflege.LAENGE, "staende": pflege.STAENDE,
        "klassen": _klassen_wahl(s, ohne=r["klasse_id"]), "loeschen": not haken, "haken": pflege.haken_text(haken)},
        _pflege_ort(s, r["id"], "Bearbeiten"), status)


def _reihe_werte(r: dict) -> dict:
    return {"titel": r["titel"], "reihenfrage": r["reihenfrage"], "stand": r["stand"], "notizen": r["notizen"],
            "behandelt": "\n".join(r["behandelt"]), "merksaetze": "\n".join(r["merksaetze"])}


@app.get("/reihe/{reihe_id}/bearbeiten", response_class=HTMLResponse)
def seite_reihe_bearbeiten(request: Request, reihe_id: str):
    s = struktur_()
    r = _objekt(s, reihe_id, "reihe")
    return _reihe_bearbeiten_seite(request, s, r, _reihe_werte(r))


@app.post("/reihe/{reihe_id}/bearbeiten", response_class=HTMLResponse)
async def reihe_bearbeiten(request: Request, reihe_id: str):
    s = struktur_()
    r = _objekt(s, reihe_id, "reihe")
    form, token_ok = await pflege_formular(request, "Reihe ändern")
    w = _wert(form)
    titel, fehler = pflege.text(w("titel"), "titel", pflege.PFLICHT["reihe"])
    felder, werte = {"titel": (titel, w("alt_titel"))}, {"titel": titel}
    for feld in ("reihenfrage", "notizen"):
        wert, f = pflege.text(w(feld), feld)
        felder[feld], werte[feld], fehler = (wert, w(f"alt_{feld}")), wert, fehler + f
    for feld in ("behandelt", "merksaetze"):
        wert, f = pflege.zeilen(w(feld), feld)
        felder[feld], werte[feld], fehler = (wert, w(f"alt_{feld}").splitlines()), w(feld), fehler + f
    stand = w("stand") if w("stand") in pflege.STAENDE else r["stand"]
    felder["stand"], werte["stand"] = (stand, w("alt_stand")), stand
    if not token_ok:
        fehler = [pflege.VERALTET]
    if not fehler:
        neu, gesehen = pflege.geaendert(felder)
        if not neu:
            return RedirectResponse(f"/reihe/{reihe_id}?erledigt=nichts", status_code=303)
        aus, text_ = await pflegen("reihe_aendern", {"reihe": reihe_id, **neu}, {reihe_id: gesehen})
        if aus:
            return nach(f"/reihe/{reihe_id}", aus)
        fehler = [text_]
    return _reihe_bearbeiten_seite(request, s, r, werte, fehler, 400)


async def _reihe_aktion(request: Request, reihe_id: str, wofuer: str, operation: str, argumente: Callable,
                        ziel: str = ""):
    """Aktion an der Reihe aus ihrer Ansicht (ein Knopf, eine Auswahl); belegtes Ziel: einmal fragen."""
    s = struktur_()
    _objekt(s, reihe_id, "reihe")
    form, token_ok = await pflege_formular(request, wofuer)
    zurueck = f"/reihe/{reihe_id}"
    if not token_ok:
        return _meldung(request, wofuer, pflege.VERALTET, zurueck, 400)
    args, fehler = argumente(_wert(form))
    if not fehler:
        try:
            aus, text_ = await pflegen(operation, {"reihe": reihe_id, **args})
        except termine.Belegt as belegt:
            return _belegt(request, s, reihe_id, belegt, request.url.path, form, zurueck)
        if aus:
            return nach(ziel or zurueck, aus)
        fehler = [text_]
    return _meldung(request, wofuer, " ".join(fehler), zurueck, 400)


def _bei_belegt(w) -> dict:
    return {"bei_belegt": w("bei_belegt")} if w("bei_belegt") in (termine.NACHRUECKEN, termine.TAUSCHEN) else {}


@app.post("/reihe/{reihe_id}/verschieben", response_class=HTMLResponse)
async def reihe_verschieben(request: Request, reihe_id: str):
    return await _reihe_aktion(request, reihe_id, "Reihe verschieben", "reihe_verschieben",
                               lambda w: ({"klasse": w("klasse")}, [] if w("klasse") else ["Bitte eine Klasse wählen."]))


@app.post("/reihe/{reihe_id}/zeitlich", response_class=HTMLResponse)
async def reihe_zeitlich(request: Request, reihe_id: str):
    return await _reihe_aktion(request, reihe_id, "Reihe verschieben", "reihe_zeitlich",
                               lambda w: ({"start": w("start"), **_bei_belegt(w)},
                                          [] if w("start") else ["Bitte einen Termin wählen."]))


def _termine_seite(request: Request, s, r: dict, werte: dict, fehler: list[str] | None = None, status: int = 200):
    liste, termine_fehler = _termine_von(s, r["klasse_id"])
    frei = [t for t in pflege.termin_optionen(liste, nur_frei=True) if not t["vergangen"]]
    eigene = [t for t in liste if t["stunde"] and t["stunde"]["reihe_id"] == r["id"]]
    werte = {"ab": pflege.erster_freier(liste, heute()), "anzahl": "", "gewaehlt": set(), **werte}
    return _seite(request, "pflege_termine.html", {
        "e": {"titel": "Termine", "unter": r["titel"] or logik.OHNE_TITEL}, "reihe": r, "werte": werte,
        "fehler": fehler or [], "frei": frei, "eigene": eigene, "termine_fehler": termine_fehler,
        "ab_wahl": _ab_wahl(frei)}, _pflege_ort(s, r["id"], "Termine"), status)


@app.get("/reihe/{reihe_id}/termine", response_class=HTMLResponse)
def seite_termine(request: Request, reihe_id: str):
    s = struktur_()
    return _termine_seite(request, s, _objekt(s, reihe_id, "reihe"), {})


@app.post("/reihe/{reihe_id}/termine", response_class=HTMLResponse)
async def termine_aendern(request: Request, reihe_id: str):
    """Freie Termine zuteilen (Häkchen oder „ab …, n Termine“) oder Termine der Reihe freigeben."""
    s = struktur_()
    r = _objekt(s, reihe_id, "reihe")
    form, token_ok = await pflege_formular(request, "Termine")
    w, liste = _wert(form), _liste(form)
    werte = _wahl_werte(w, liste)
    if not token_ok:
        return _termine_seite(request, s, r, werte, [pflege.VERALTET], 400)
    if w("was") == "freigeben":
        weg = [k for k in liste("frei") if k]
        if not weg:
            return _termine_seite(request, s, r, werte, ["Bitte die Termine anhaken, die die Reihe abgibt."], 400)
        aus, text_ = await pflegen("termine_freigeben", {"reihe": reihe_id, "termine": weg})
    else:
        wahl, fehler = pflege.termine_wahl(w, liste)
        if fehler or not wahl:
            return _termine_seite(request, s, r, werte, fehler or ["Bitte Termine anhaken oder eine Zahl angeben."],
                                  400)
        try:
            aus, text_ = await pflegen("termine_zuteilen", {"reihe": reihe_id, **wahl})
        except termine.Belegt:
            aus, text_ = None, pflege.TERMIN_BELEGT
    if aus:
        return nach(f"/reihe/{reihe_id}#stunden", aus)
    return _termine_seite(request, s, r, werte, [text_], 400)


def _kopieren_seite(request: Request, s, r: dict, ziel: dict | None, werte: dict, fehler: list[str] | None = None,
                    status: int = 200):
    liste, termine_fehler = _termine_von(s, ziel["id"]) if ziel else ([], "")
    frei = [t for t in pflege.termin_optionen(liste, nur_frei=True) if not t["vergangen"]]
    werte = {"ab": pflege.erster_freier(liste, heute()), "gewaehlt": set(),
             "anzahl": str(len(r["stunden"])) if r["stunden"] and frei else "", **werte}
    return _seite(request, "pflege_kopieren.html", {
        "e": {"titel": "In eine andere Klasse übernehmen", "unter": r["titel"] or logik.OHNE_TITEL}, "reihe": r,
        "ziel": ziel, "ziel_text": next((k["text"] for k in _klassen_wahl(s) if ziel and k["id"] == ziel["id"]), ""),
        "klassen": _klassen_wahl(s, ohne=r["klasse_id"], mit_archiv=False), "werte": werte,
        "fehler": fehler or [], "frei": frei, "termine_fehler": termine_fehler, "ab_wahl": _ab_wahl(frei)},
        _pflege_ort(s, r["id"], "Übernehmen"), status)


@app.get("/reihe/{reihe_id}/kopieren", response_class=HTMLResponse)
def seite_kopieren(request: Request, reihe_id: str, klasse: str = ""):
    s = struktur_()
    r = _objekt(s, reihe_id, "reihe")
    ziel = s.objekt(klasse) if klasse else None
    if ziel is not None and (ziel["ebene"] != "klasse" or ziel["im_archiv"]):
        ziel = None
    return _kopieren_seite(request, s, r, ziel, {})


@app.post("/reihe/{reihe_id}/kopieren", response_class=HTMLResponse)
async def kopieren(request: Request, reihe_id: str):
    """Reihe in eine andere Klasse kopieren (neue ids, Stunden nur mit Thema), freiwillig gleich mit Terminen."""
    s = struktur_()
    r = _objekt(s, reihe_id, "reihe")
    form, token_ok = await pflege_formular(request, "Reihe kopieren")
    w, liste = _wert(form), _liste(form)
    ziel = s.objekt(w("klasse"))
    if ziel is None or ziel["ebene"] != "klasse":
        return _kopieren_seite(request, s, r, None, {}, ["Bitte eine Klasse wählen."], 400)
    wahl, fehler = pflege.termine_wahl(w, liste)
    if not token_ok:
        fehler = [pflege.VERALTET]
    if not fehler:
        try:
            aus, text_ = await pflegen("reihe_kopieren", {"reihe": reihe_id, "klasse": ziel["id"], **wahl})
        except termine.Belegt:
            aus, text_ = None, pflege.TERMIN_BELEGT
        if aus:
            return nach(f"/reihe/{aus.neue_id}", aus)
        fehler = [text_]
    return _kopieren_seite(request, s, r, ziel, _wahl_werte(w, liste), fehler, 400)


# Stunde

@app.post("/reihe/{reihe_id}/stunden", response_class=HTMLResponse)
async def stunde_anlegen(request: Request, reihe_id: str):
    """Neue Stunde am Ende der Reihe; das Thema darf offen bleiben (Aktionsmatrix 4.4)."""
    s = struktur_()
    _objekt(s, reihe_id, "reihe")
    form, token_ok = await pflege_formular(request, "Stunde")
    thema, fehler = pflege.text(_wert(form)("thema"), "thema")
    if not token_ok:
        fehler = [pflege.VERALTET]
    if not fehler:
        aus, text_ = await pflegen("stunde_anlegen", {"reihe": reihe_id, "thema": thema})
        if aus:
            return nach(f"/reihe/{reihe_id}#stunden", aus)
        fehler = [text_]
    return _reihe_seite(request, reihe_id, fehler, thema, 400)


def _stunde_obj(s, stunde_id: str) -> dict:
    return _objekt(s, stunde_id, "stunde")


@app.post("/stunde/{stunde_id}/aendern", response_class=HTMLResponse)
async def stunde_aendern(request: Request, stunde_id: str):
    s = struktur_()
    st = _stunde_obj(s, stunde_id)
    form, token_ok = await pflege_formular(request, "Stunde ändern")
    w = _wert(form)
    thema, fehler = pflege.text(w("thema"), "thema")
    marke = w("marke") if w("marke") in pflege.MARKEN else ""
    zurueck = _stunde_link(s, stunde_id)
    if not token_ok:
        fehler = [pflege.VERALTET]
    if not fehler:
        neu, gesehen = pflege.geaendert({"thema": (thema, w("alt_thema")), "marke": (marke, w("alt_marke"))})
        if not neu:
            return RedirectResponse(f"{zurueck}?erledigt=nichts", status_code=303)
        aus, text_ = await pflegen("stunde_aendern", {"stunde": stunde_id, **neu}, {stunde_id: gesehen})
        if aus:
            return nach(zurueck, aus)
        fehler = [text_]
    if not st["nr"]:
        return _meldung(request, "Stunde ändern", " ".join(fehler), zurueck, 400)
    return _stunde_seite(request, st["reihe_id"], str(st["nr"]), fehler=fehler, thema=thema, status=400)


@app.post("/stunden/verschieben", response_class=HTMLResponse)
async def stunde_verschieben(request: Request):
    """„Verschieben nach …“ (ein Griff): an eine Stelle der Reihe (vor:<id> bzw. ende), auf einen Termin
    (termin:<kennung>) oder in eine andere Reihe (reihe:<id>). Aus der Reihe auch per Ziehen (statisch/ziehen.js
    füllt dieses Formular)."""
    s = struktur_()
    form, token_ok = await pflege_formular(request, "Stunde verschieben")
    w = _wert(form)
    st = _stunde_obj(s, w("stunde"))
    r = s.objekt(st["reihe_id"])
    zurueck = f"/reihe/{r['id']}#stunden"
    if not token_ok:
        return _meldung(request, "Verschieben", pflege.VERALTET, zurueck, 400)
    art, _, ziel = w("ziel").partition(":")
    if art == "termin":
        operation, args = "stunde_auf_termin", {"stunde": st["id"], "termin": ziel, **_bei_belegt(w)}
    elif art == "reihe":
        andere = s.objekt(ziel)
        if andere is None or andere["ebene"] != "reihe":
            raise HTTPException(404)
        operation, args = "stunde_verschieben", {"stunde": st["id"], "stelle": len(andere["stunden"]),
                                                 "reihe": ziel}
    elif art in ("vor", "ende"):
        stelle = pflege.stelle([x["id"] for x in r["stunden"]], st["id"], ziel if art == "vor" else "")
        if stelle is None:
            return _meldung(request, "Verschieben", "Diese Stelle gibt es nicht (mehr). Bitte lade die Seite neu.",
                            zurueck, 400)
        operation, args = "stunde_verschieben", {"stunde": st["id"], "stelle": stelle}
    else:
        return _meldung(request, "Verschieben", "Bitte wählen, wohin die Stunde soll.", zurueck, 400)
    try:
        aus, text_ = await pflegen(operation, args)
    except termine.Belegt as belegt:
        return _belegt(request, s, st["id"], belegt, "/stunden/verschieben", form, zurueck)
    if not aus:
        return _meldung(request, "Verschieben", text_, zurueck, 400)
    return nach(_stunde_link(struktur_(), st["id"]) if w("von") == "stunde" else zurueck, aus)


@app.post("/stunde/{stunde_id}/kopieren", response_class=HTMLResponse)
async def stunde_kopieren(request: Request, stunde_id: str):
    s = struktur_()
    st = _stunde_obj(s, stunde_id)
    form, token_ok = await pflege_formular(request, "Stunde kopieren")
    zurueck = _stunde_link(s, stunde_id)
    if not token_ok:
        return _meldung(request, "Kopieren", pflege.VERALTET, zurueck, 400)
    aus, text_ = await pflegen("stunde_kopieren", {"stunde": st["id"], "reihe": _wert(form)("reihe")})
    if not aus:
        return _meldung(request, "Kopieren", text_, zurueck, 400)
    return nach(_stunde_link(struktur_(), aus.neue_id) if aus.neue_id else zurueck, aus)


# Für alle Ebenen: archivieren (Stunde: ausblenden), wiederherstellen, löschen (nur, wenn nichts dranhängt)

@app.post("/objekt/{kennung_}/{was}", response_class=HTMLResponse)
async def objekt_aktion(request: Request, kennung_: str, was: str):
    if was not in ("archivieren", "wiederherstellen", "loeschen"):
        raise HTTPException(404)
    s = struktur_()
    o = s.objekt(kennung_) if s is not None and s.format == "neu" else None
    if o is None:
        raise HTTPException(404)
    form, token_ok = await pflege_formular(request, was)
    zurueck = _link(s, kennung_)
    if not token_ok:
        return _meldung(request, "Speichern", pflege.VERALTET, zurueck, 400)
    if o["ebene"] in ("fach", "klasse") and was != "wiederherstellen" and form.get("bestaetigt") != "1":
        return _bestaetigen(request, s, o, was, form, zurueck)
    ziel = _oben(s, kennung_) if was == "loeschen" else (
        f"/reihe/{o['reihe_id']}#ausgeblendet" if o["ebene"] == "stunde" and was == "archivieren" else zurueck)
    aus, text_ = await pflegen(was, {"id": kennung_})
    if not aus:
        return _meldung(request, "Geht nicht", text_, zurueck, 400)
    return nach(ziel, aus)


def _bestaetigen(request: Request, s, o: dict, was: str, form, zurueck: str):
    """Rückfrage beim Archivieren und Löschen einer Klasse oder eines Fachs: nennt die Zahl der Reihen."""
    if o["ebene"] == "fach":
        reihen = sum(len(s.objekt(k)["reihen"]) for k in o["klassen"])
        name, was_dran = f"Fach {o['name']}", f"{pflege.zahl_text(len(o['klassen']), 'Klasse', 'Klassen')} mit " \
                                              f"{pflege.zahl_text(reihen, 'Reihe', 'Reihen')}"
    else:
        name, was_dran = _klasse_name(o), pflege.zahl_text(len(o["reihen"]), "Reihe", "Reihen")
    if was == "archivieren":
        titel, text_ = f"{name} archivieren?", f"Dazu gehören {was_dran}. Alles bleibt erhalten und steht im Archiv."
        knopf = "Ja, archivieren"
    else:
        titel, text_ = f"{name} löschen?", "Gelöscht ist gelöscht; mit „Rückgängig“ holst du es direkt danach zurück."
        knopf = "Ja, löschen"
    return _rueckfrage(request, s, o["id"], titel, text_, "", request.url.path, form,
                       [("bestaetigt", "1", knopf)], zurueck)


@app.post("/schule", response_class=HTMLResponse)
async def schule(request: Request):
    """Bundesland der Schule (Ferien und Feiertage), einmal; ändern unter „Ich“."""
    form, token_ok = await pflege_formular(request, "Schule")
    bundesland = _wert(form)("bundesland")
    if not token_ok:
        return _meldung(request, "Schule", pflege.VERALTET, "/ich", 400)
    if bundesland not in pflege.BUNDESLAENDER:
        return _meldung(request, "Schule", "Bitte ein Bundesland wählen.", "/ich", 400)
    aus, text_ = await pflegen("schule_setzen", {"bundesland": bundesland})
    if not aus:
        return _meldung(request, "Schule", text_, "/ich", 400)
    return nach("/ich#schule", aus)


# Ansichten mit Pflege (Klasse, Reihe, Stunde): was die Masken dort brauchen

def klasse_pflege(s, klasse_id: str) -> dict | None:
    """Für klasse.html: Stand, Stundenplan, Termine (kommende und vergangene), Knöpfe. None: altes Format."""
    k = s.objekt(klasse_id) if s is not None and s.format == "neu" else None
    if k is None or k["ebene"] != "klasse":
        return None
    liste, termine_fehler = _termine_von(s, klasse_id)
    return {"klasse": k, "stundenplan": pflege.stundenplan_text(k["zeitplan"]), "termine_fehler": termine_fehler,
            "kommend": [t for t in liste if not t["vergangen"]], "vergangen": [t for t in liste if t["vergangen"]],
            "archiv": k["im_archiv"], "selbst_archiviert": bool(k["archiviert"]), "stunden_wahl": pflege.STUNDEN}


def reihe_pflege(s, reihe_id: str) -> dict | None:
    """Für reihe.html: Ziele für „Verschieben nach …“, „Reihe beginnt am …“, Stand des Archivs."""
    r = s.objekt(reihe_id) if s is not None and s.format == "neu" else None
    if r is None or r["ebene"] != "reihe":
        return None
    liste, termine_fehler = _termine_von(s, r["klasse_id"])
    return {"reihe": r, "archiv": r["im_archiv"], "selbst_archiviert": bool(r["archiviert"]),
            "klasse_archiviert": r["im_archiv"] and not r["archiviert"],
            "ziele": _ziele(s, r, None, liste), "termine": pflege.termin_optionen(liste),
            "start": r["stunden"][0]["termin"] if r["stunden"] else "", "termine_fehler": termine_fehler,
            "hat_termine": bool(liste)}


def stunde_pflege(s, reihe_id: str, nr: int) -> dict | None:
    r = s.objekt(reihe_id) if s is not None and s.format == "neu" else None
    if r is None or r["ebene"] != "reihe" or not 1 <= nr <= len(r["stunden"]):
        return None
    st = r["stunden"][nr - 1]
    liste, _ = _termine_von(s, r["klasse_id"])
    haken = _haken(s, st["id"])
    return {"stunde": st, "reihe": r, "ziele": _ziele(s, r, st, liste), "marken": pflege.MARKEN,
            "termin": pflege.termin_text(st["termin"]) if st["termin"] else "",
            "termin_offen": bool(st["termin"]) and any(t["kennung"] == st["termin"] and not t["ausgefallen"]
                                                         for t in liste),
            "reihen": [x for x in _reihen_wahl(s) if x["id"] != r["id"]], "loeschen": not haken,
            "haken": pflege.haken_text(haken), "archiv": r["im_archiv"], "laenge": pflege.LAENGE}


def _reihen_wahl(s) -> list[dict]:
    return [{"id": x["id"], "text": f"„{x['titel'] or logik.OHNE_TITEL}“ ({x['fach']}, {logik.gruppe_name(x['klasse'])})"}
            for x in s.reihen if not x["im_archiv"]]


def _ziele(s, r: dict, st: dict | None, liste: list[dict]) -> list[dict]:
    """Auswahl „Verschieben nach …“: Stellen der Reihe, Termine der Klasse, andere Reihen (Gruppen für <optgroup>)."""
    stellen = [{"wert": f"vor:{x['id']}", "text": f"vor Stunde {x['nr']}: {pflege.thema(x)}"}
               for x in r["stunden"] if st is None or x["id"] != st["id"]]
    stellen.append({"wert": "ende", "text": "ans Ende der Reihe"})
    gruppen = [{"titel": "In dieser Reihe", "ziele": stellen}]
    termine_ = [{"wert": f"termin:{t['wert']}", "text": t["text"]}
                for t in pflege.termin_optionen(liste, ohne=st["id"] if st else "")]
    if termine_:
        gruppen.append({"titel": "Auf einen Termin", "ziele": termine_})
    andere = [{"wert": f"reihe:{x['id']}", "text": f"ans Ende von {x['text']}"}
              for x in _reihen_wahl(s) if x["id"] != r["id"]]
    if andere:
        gruppen.append({"titel": "In eine andere Reihe", "ziele": andere})
    return gruppen


def ich_pflege() -> dict:
    """Für ich.html: Schule (Bundesland) und „Letzte Änderungen“ (die letzten 20, mit Rückgängig)."""
    s = struktur_()
    try:
        letzte = sp.letzte(20, umgebung())
    except OSError as fehler_:
        logger.error("Letzte Änderungen nicht lesbar: %s", fehler_)
        letzte = []
    return {"pflegen": s is not None and s.format == "neu", "bundesland": (s.schule if s else {}).get("bundesland", ""),
            "bundeslaender": pflege.BUNDESLAENDER, "aenderungen": pflege.aenderungen(letzte, datetime.now(ZONE))}


@app.get("/fach/{fach_id}", response_class=HTMLResponse)
def seite_fach(request: Request, fach_id: str):
    reihen, gruppen = ordnung_laden()
    zeilen_je = logik.zeilen_je_reihe(reihen, _alle_auftraege(), datetime.now(ZONE), _entwuerfe(),
                                      ausblenden=_ausblenden(zustand_().lesen()))
    s = struktur_()
    e = logik.fach_ansicht(fach_id, reihen, zeilen_je, gruppen, logik.faecher_aus(s))
    if e is None:
        raise HTTPException(404)
    f = s.objekt(fach_id) if s is not None and s.format == "neu" else None
    return vorlagen.TemplateResponse(request, "fach.html", {
        "e": e, "token": logik.formular_token(GEHEIM), "fach": f if f and f["ebene"] == "fach" else None,
        **rahmen(reihen, {"teile": [], "hier": e["titel"]}, logik.fach_aktiv(fach_id))})


@app.get("/klasse/{gruppe_id}", response_class=HTMLResponse)
def seite_klasse(request: Request, gruppe_id: str):
    reihen, gruppen = ordnung_laden()
    zeilen_je = logik.zeilen_je_reihe(reihen, _alle_auftraege(), datetime.now(ZONE),
                                      _entwuerfe(),
                                      ausblenden=_ausblenden(zustand_().lesen()))
    e = logik.klasse_ansicht(gruppe_id, reihen, zeilen_je, gruppen)
    if e is None:
        raise HTTPException(404)
    return vorlagen.TemplateResponse(request, "klasse.html", {
        "e": e, "token": logik.formular_token(GEHEIM), "p": klasse_pflege(struktur_(), gruppe_id),
        **rahmen(reihen, logik.krumen_klasse(e["gruppe"]), logik.klasse_aktiv(gruppe_id))})


_lese_fehler: list[str] = []  # wie _reihen_fehler: Fehler im Profil nur einmal loggen


@app.get("/vorlagen", response_class=HTMLResponse)
def seite_vorlagen(request: Request):
    return _vorlagen_seite(request, logik.HINWEISE.get(request.query_params.get("erledigt") or "", ""))


def _vorlagen_ordner(geltung: str) -> Path:
    """Ordner der Formatvorlagen von lia/unterricht (data/vorlagen bzw. data/vorlagen/<art>) der Instanz."""
    basis = INSTANZ.parent / logik.NEU_AGENT / "data" / "vorlagen"
    return basis / geltung if geltung else basis


def _formatvorlagen() -> list[dict]:
    dateien_ = []
    for geltung in logik.FORMAT_GELTUNG:
        ordner = _vorlagen_ordner(geltung)
        for p in sorted(ordner.iterdir()) if ordner.is_dir() else []:
            if p.is_file() and not p.is_symlink() and p.suffix.lower() in logik.FORMAT_ENDUNGEN \
                    and not p.name.startswith((".", "~$")):
                dateien_.append((geltung, p.name, p.stat().st_mtime))
    return logik.formatvorlagen(dateien_)


def _vorlagen_seite(request: Request, hinweis: str = "", fehler: list[str] | None = None, status: int = 200):
    profil, lese_fehler = ordnung.profil(INSTANZ)
    if lese_fehler != _lese_fehler:
        for f in lese_fehler:
            logger.error("Profil: %s", f)
        _lese_fehler[:] = lese_fehler
    return vorlagen.TemplateResponse(request, "vorlagen.html", {
        "e": {"titel": "Vorlagen", "unter": "Gilt für alles, was deine Assistenz für dich baut."},
        "gestaltung": logik.gestaltung(profil), "arten": list(logik.VORLAGEN.values()),
        "formatvorlagen": _formatvorlagen(), "geltungen": logik.FORMAT_GELTUNG, "token": logik.formular_token(GEHEIM),
        "endungen": ",".join(logik.FORMAT_ENDUNGEN), "hinweis": hinweis, "fehler": fehler or [],
        **rahmen(reihen_laden(), logik.krumen("Vorlagen"), "vorlagen")}, status_code=status)


@app.post("/vorlagen/formatvorlage", response_class=HTMLResponse)
async def formatvorlage_hochladen(request: Request):
    """Lias Word-/PowerPoint-Vorlage nach lia/unterricht/data/vorlagen[/<art>]; die neueste ihrer Sorte gilt.
    Startet keinen Lauf und geht darum immer (wie final)."""
    form = await formular_lesen(request, "Formatvorlage", 1)
    datei = form.get("datei")
    try:
        if not logik.token_passt(GEHEIM, str(form.get("token") or "")):
            return _vorlagen_seite(request, fehler=[logik.VERALTET], status=400)
        if not isinstance(datei, UploadFile) or not datei.filename:
            return _vorlagen_seite(request, fehler=["Wähle eine Datei aus."], status=400)
        geltung = str(form.get("geltung") or "")
        fehler = logik.formatvorlage_pruefen(datei.filename, datei.size or 0, geltung)
        if fehler:
            return _vorlagen_seite(request, fehler=fehler, status=400)
        ordner, tmp = _vorlagen_ordner(geltung), None
        try:
            ordner.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=ordner, prefix=".hochladen-")
            with os.fdopen(fd, "wb") as ziel:
                shutil.copyfileobj(datei.file, ziel)
            name = logik.dateiname_bereinigen(datei.filename)
            os.replace(tmp, ordner / name)  # gleicher Name: ersetzt die alte Fassung
        except OSError as fehler_:
            if tmp:
                Path(tmp).unlink(missing_ok=True)
            logger.error("Formatvorlage nicht gespeichert: %s", fehler_)
            return _vorlagen_seite(request, fehler=[logik.FEHLGESCHLAGEN], status=500)
    finally:
        if isinstance(datei, UploadFile):
            await datei.close()
    logger.info("Formatvorlage %s für %s gespeichert", name, geltung or "alle")
    return RedirectResponse("/vorlagen?erledigt=formatvorlage#formatvorlagen", status_code=303)


@app.post("/vorlagen/formatvorlage/entfernen", response_class=HTMLResponse)
async def formatvorlage_entfernen(request: Request):
    form = await formular_lesen(request, "Formatvorlage entfernen", 0)
    if not logik.token_passt(GEHEIM, str(form.get("token") or "")):
        return _vorlagen_seite(request, fehler=[logik.VERALTET], status=400)
    geltung, name = str(form.get("geltung") or ""), str(form.get("name") or "")
    if not any(v["geltung"] == geltung and v["name"] == name for v in _formatvorlagen()):
        raise HTTPException(404)  # nur, was die Seite gezeigt hat (kein Pfad aus dem Formular)
    ordner = _vorlagen_ordner(geltung)
    try:
        (ordner / name).unlink()
        for endung in (".docx", ".pptx"):  # umgewandelte Kopie von .dotx/.potx (formatvorlage.py)
            (ordner / "umgewandelt" / (Path(name).stem + endung)).unlink(missing_ok=True)
    except OSError as fehler_:
        logger.error("Formatvorlage nicht entfernt: %s", fehler_)
        return _vorlagen_seite(request, fehler=[logik.FEHLGESCHLAGEN], status=500)
    logger.info("Formatvorlage %s (%s) entfernt", name, geltung or "alle")
    return RedirectResponse("/vorlagen?erledigt=formatvorlage-weg#formatvorlagen", status_code=303)


@app.get("/ich", response_class=HTMLResponse)
def seite_ich(request: Request):
    return vorlagen.TemplateResponse(request, "ich.html", {
        "e": {"titel": "Ich", "unter": "Was deine Assistenz über deine Wünsche weiß."},
        "gruppen": logik.regeln_aus(ordnung.regeltexte(INSTANZ)), "token": logik.formular_token(GEHEIM),
        "p": ich_pflege(), **rahmen(reihen_laden(), logik.krumen("Ich"), "ich")})


def _ort(reihen: list[dict], reihe_id: str, stunde_text: str) -> tuple[dict | None, tuple[int, str] | None]:
    """Vorbelegter Ort für „Neu“: laufende Reihe und Stunde (Nummer, Thema); Unbekanntes fällt weg."""
    reihe = next((r for r in reihen if r["id"] == reihe_id and r["laufend"]), None)
    if reihe is None:
        return None, None
    stunden = logik.reihe_stunden(reihe)
    nr = logik.stunde_nummer(stunde_text, len(stunden))
    return reihe, ((nr, stunden[nr - 1]["thema"]) if nr else None)


def _formular(request: Request, text: str = "", fehler: list[str] | None = None, status: int = 200,
              reihe: str = "", art: str = "", stunde: str = "", extra: dict | None = None, aus: str = ""):
    """Galerie (ohne art) bzw. Formular einer Vorlage, Ort aus reihe und stunde vorbelegt."""
    reihen = reihen_laden()
    ort_reihe, ort_stunde = _ort(reihen, reihe, stunde)
    vorlage = logik.VORLAGEN.get(art) or (logik.VORLAGE_FREI if fehler else None)
    stunden = logik.reihe_stunden(ort_reihe) if ort_reihe else []
    return vorlagen.TemplateResponse(request, "neu.html", {
        # Stunde wählbar, wenn die Reihe welche hat; eine unbekannte aus der URL fällt nicht still weg (Nr. 2)
        "stunden_wahl": logik.stunden_auswahl(ort_reihe, stunden) if stunden and not ort_stunde else [],
        "stunde_fehlt": f"{logik.stunden_wort(ort_reihe)[0]} {stunde}" if ort_reihe and stunde and not ort_stunde
        else "", "reihe_link": logik.reihe_link(ort_reihe) if ort_reihe else "",
        "e": {"titel": vorlage["name"] if vorlage else "Neu",
              "unter": "für " + logik.ort_text(ort_reihe, ort_stunde) if ort_reihe else "Auftrag an deine Assistenz"},
        "modus": neu_modus(), "token": logik.formular_token(GEHEIM), "text": text, "fehler": fehler or [],
        "art": art if vorlage else "", "vorlage": vorlage, "varianten": logik.VARIANTEN,
        "galerie": logik.galerie(ort_reihe["id"] if ort_reihe else "", ort_stunde[0] if ort_stunde else None,
                                 ort_reihe["fach"] if ort_reihe else "", aus), "extra": extra or {},
        "andere": logik.neu_link(ort_reihe["id"] if ort_reihe else "", ort_stunde[0] if ort_stunde else None),
        "reihen": [] if ort_reihe else logik.reihen_auswahl(reihen), "reihe": ort_reihe["id"] if ort_reihe else reihe,
        "ort_fest": bool(ort_reihe), "stunde": ort_stunde[0] if ort_stunde else "",
        "beachte": logik.ort_text(ort_reihe, ort_stunde),
        "text_max": logik.NEU_TEXT_MAX, "max_mb": logik.NEU_DATEI_MAX_MB, "endungen": ",".join(logik.NEU_ENDUNGEN),
        **rahmen(reihen, logik.krumen("Neu", ort_reihe) if ort_reihe else logik.krumen("Neu"),
                 ort_reihe["id"] if ort_reihe else ""),
    }, status_code=status)


@app.get("/neu", response_class=HTMLResponse)
def seite_neu(request: Request):
    if not neu_modus():
        raise HTTPException(404)
    q = request.query_params
    text, aus = "", q.get("aus") or ""
    if aus and chat() is not None:  # „Daraus Auftrag machen“: Frage und Antwort als Wunsch
        text = logik.text_aus_chat(next((e for e in chat().verlauf(CHAT_ORDNER) if e.get("id") == aus), None))
    return _formular(request, text=text, reihe=q.get("reihe") or "", art=q.get("art") or "",
                     stunde=q.get("stunde") or "", aus=aus if text else "")


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


async def formular_lesen(request: Request, wofuer: str, max_dateien: int, max_teile: int | None = None,
                         max_felder: int = 10):
    """Formular einer Route mit Wirkung: Herkunft prüfen (403), Größe begrenzen (413), lesen (400).
    max_teile: so viele Dateien darf das Formular haben, ohne dass es 400 gibt (sonst max_dateien + 1); die
    Größe richtet sich nach max_dateien. max_felder: Masken der Struktur-Pflege haben Terminlisten."""
    if not logik.herkunft_passt(request.headers.get("origin"), request.headers.get("host"),
                                request.headers.get("sec-fetch-site")):
        logger.warning("%s abgewiesen: fremde Herkunft", wofuer)
        raise HTTPException(403)
    grenze = (max_dateien * logik.NEU_DATEI_MAX_MB + 1) * 1024 * 1024
    if int(request.headers.get("content-length") or 0) > grenze:
        raise HTTPException(413)
    try:
        return await request.form(max_files=max_teile or max_dateien + 1, max_fields=max_felder,
                                  max_part_size=64 * 1024)
    except Exception:  # kaputtes oder zu großes Formular (MultiPartException u. a.)
        logger.warning("%s: Formular nicht lesbar", wofuer)
        raise HTTPException(400) from None


def datei_ablegen(upload: UploadFile, ordner: Path) -> Path:
    """Hochgeladene Datei mit bereinigtem Namen in einen neuen Ordner schreiben."""
    pfad = ordner / logik.dateiname_bereinigen(upload.filename)
    ordner.mkdir(parents=True)
    with pfad.open("wb") as ziel:
        shutil.copyfileobj(upload.file, ziel)
    return pfad


def _neu_fertig(modus: str, reihe: str | None, reihen: list[dict], stunde) -> RedirectResponse:
    """Nach Neuer Auftrag: zur Stunde bzw. Reihe mit Bestätigung, ohne Reihe nach „Heute“."""
    if reihe:
        r = next(x for x in reihen if x["id"] == reihe)
        ziel = logik.stunde_link(r, stunde[0]) if stunde else logik.reihe_link(r)
        return RedirectResponse(f"{ziel}?erledigt={'auftrag' if modus == 'echt' else 'auftrag-test'}", status_code=303)
    return RedirectResponse("/?abgeschickt=1", status_code=303)


@app.post("/neu", response_class=HTMLResponse)
async def neu_abschicken(request: Request):
    modus = neu_modus()
    if not modus:
        raise HTTPException(404)
    form = await formular_lesen(request, "Neuer Auftrag", logik.NEU_DATEIEN_MAX)
    text, gewaehlt = str(form.get("text") or ""), str(form.get("reihe") or "")
    art, stunde_text = str(form.get("art") or ""), str(form.get("stunde") or "")
    if art not in logik.VORLAGEN:
        art = ""
    extra, fehler_extra = logik.extra_werte(art, lambda name: str(form.get(name) or ""))
    if not logik.token_passt(GEHEIM, str(form.get("token") or "")):
        return _formular(request, text, [logik.VERALTET], 400, gewaehlt, art, stunde_text, extra)
    dateien_ = [d for d in form.getlist("dateien") if isinstance(d, UploadFile) and d.filename]
    text, fehler = logik.neuer_auftrag_pruefen(text, [(d.filename, d.size or 0) for d in dateien_])
    reihen = reihen_laden()
    reihe, fehler_reihe = logik.reihe_pruefen(gewaehlt, reihen)
    if fehler or fehler_reihe or fehler_extra:
        return _formular(request, text, fehler + fehler_reihe + fehler_extra, 400, reihe or "", art, stunde_text,
                         extra)
    agent, quelle = logik.vorlage_agent(art)
    ort_reihe, stunde = _ort(reihen, reihe or "", stunde_text)
    # Feld ort (agentkit.struktur, Strukturplan Abschnitt 8): die Stunde, sonst die Reihe; reihe bleibt gesetzt
    stunde_id = logik.reihe_stunden(ort_reihe)[stunde[0] - 1]["id"] if stunde else None
    # „Auch als“: der Material-Agent baut die Varianten im selben Lauf (Zeile im Auftragstext, lia/unterricht)
    auch_als = logik.varianten_waehlen([str(w) for w in form.getlist("varianten")]) \
        if (logik.VORLAGEN.get(art) or {}).get("varianten") else []
    auftragstext = logik.text_mit_reihe(text, reihe, reihen, stunde, art, extra, auch_als)
    # Doppelklick: Lia sieht die Antwort der zweiten Anfrage, also dieselbe Bestätigung. Zwischen Prüfen und Anlegen
    # liegt kein await, gleichzeitige Anfragen kommen sich nicht in die Quere.
    if logik.auftrag_doppelt(_auftraege_von(agent), datetime.now(ZONE), auftragstext, ort=stunde_id or reihe,
                             dateinamen=[logik.dateiname_bereinigen(d.filename) for d in dateien_]):
        logger.info("Gleicher Auftrag an %s gerade schon angelegt, verworfen", agent)
        for d in dateien_:
            await d.close()
        return _neu_fertig(modus, reihe, reihen, stunde)
    EINGANG.mkdir(parents=True, exist_ok=True)
    ablage = Path(tempfile.mkdtemp(dir=EINGANG))
    try:
        pfade = []
        for nr, d in enumerate(dateien_):  # je Datei ein Unterordner: gleiche Namen überschreiben sich nicht
            pfade.append(datei_ablegen(d, ablage / str(nr)))
        aid = auftraege.neuer_auftrag(agent, auftragstext,
                                      quelle=quelle, dateien=pfade, basis=INSTANZ / "auftraege",
                                      agenten_dir=INSTANZ.parent, absender=config.person(INSTANZ), reihe=reihe,
                                      ort=stunde_id or reihe)
    except (auftraege.AuftragFehler, OSError) as fehler_:
        logger.error("Neuer Auftrag nicht angelegt: %s", fehler_)
        return _formular(request, text, [logik.FEHLGESCHLAGEN], 500, reihe or "", art, stunde_text, extra)
    finally:
        shutil.rmtree(ablage, ignore_errors=True)
        for d in dateien_:
            await d.close()
    logger.info("Auftrag %s angelegt (%s, %d Dateien, Reihe %s, Stunde %s, %s)", aid, agent, len(pfade),
                reihe or "keine", stunde[0] if stunde else "keine", modus)
    if stunde:  # die Web-App merkt sich, zu welcher Stunde der Auftrag gehört (zustand.py)
        try:
            z_ = zustand_()
            z_.schreiben(logik.stunde_zuordnen(z_.lesen(), aid, stunde_id))
        except OSError as fehler_:
            logger.error("Stunde von %s nicht gespeichert: %s", aid, fehler_)
    if modus == "echt":
        agent_starten(agent)
    return _neu_fertig(modus, reihe, reihen, stunde)


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


def _kette(eintrag_id: str) -> tuple[list[dict], dict]:
    """Kette und Kopf zu einer ID aus der Instanz (auch Nachbesserung oder Rückmeldung); sonst 404."""
    try:
        auftrag = auftraege.erledigter(eintrag_id, basis=INSTANZ / "auftraege")  # prüft die ID (pruefe_id)
    except AblageFehler:
        raise HTTPException(404) from None
    if not (logik.zeigbar(auftrag) or auftrag.get("agent") == "feedback"):
        raise HTTPException(404)
    kette = logik.kette_von(eintrag_id, _alle_auftraege())
    kopf = logik.kopf(kette)
    if not logik.zeigbar(kopf):  # z. B. Rückmeldung zu einem unbekannten Ergebnis
        raise HTTPException(404)
    return kette, kopf


def _material(kette: list[dict], kopf: dict) -> tuple[dict, list[dict], dict]:
    """Ansicht des Materials samt dem, was die Web-App selbst gespeichert hat: (Ansicht, eigene Fassungen, Zustand)."""
    z = zustand_().lesen()
    eigene = list(z["eigene"].get(kopf["id"]) or [])
    vorschauen = {a["id"]: dateien.vorschau_info(dateien.agent_ordner(INSTANZ, a.get("agent")),
                                                 a.get("ergebnis_dateien") or [])
                  for a in logik.fassungen(kette) if a.get("status") == "erledigt"}
    final_ref = (z["final"].get(kopf["id"]) or {}).get("fassung") or ""
    return logik.ergebnis(kette, vorschauen, datetime.now(ZONE), eigene, final_ref), eigene, z


def _ergebnis_seite(request: Request, kette: list[dict], kopf: dict, offen: str = "", hinweis: str = "",
                    fehler: list[str] | None = None, text: str = "", status: int = 200, ziel: dict | None = None):
    """Material-Ansicht. ziel: Rückmeldung an einer Datei/Seite (logik.rueckmeldung_ziel), sonst aus der URL."""
    if ziel is None and offen == "rueckmeldung":
        q = request.query_params
        ziel = logik.rueckmeldung_ziel(kette, q.get("fassung"), q.get("datei"), q.get("seite"))
    e, _, z = _material(kette, kopf)
    reihen = reihen_laden()
    reihe = logik.reihe_von(kopf, reihen)
    stunden = logik.reihe_stunden(reihe) if reihe else []
    nr = logik.stunde_nr(z["stunde_von"].get(kopf["id"]), stunden)
    ueber = {"text": f"{logik.stunden_wort(reihe)[0]} {nr}", "link": logik.stunde_link(reihe, nr)} if nr else None
    original = logik.variante_von(z, kopf["id"])
    if original:  # Varianten stehen beim Original: Brotkrume und Leiste von dort
        ueber = {"text": "Original", "link": f"/ergebnis/{original[0]}"}
    leiste = logik.varianten_leiste(z, original[0] if original else kopf["id"], _alle_auftraege(),
                                    datetime.now(ZONE), set(z["final"]))
    nochmal = bool(neu_modus()) and logik.nochmal_moeglich(kette) and kopf["id"] not in z["ersetzt"]
    # Geht „Nochmal“ nicht (Dateien dabei), zeigt die Seite den Weg über „Neu“ statt einer Sackgasse
    nochmal_weg = logik.nochmal_weg(kette) if neu_modus() and not nochmal and kopf["id"] not in z["ersetzt"] else ""
    return vorlagen.TemplateResponse(request, "ergebnis.html", {
        "stunden": logik.stunden_auswahl(reihe, stunden) if stunden and not original else [], "stunde_nr": nr or 0,
        "reihe_wahl": [] if original else logik.reihe_wahl(kopf, reihen, z["reihe_von"]),
        "varianten": leiste, "variante_art": logik.VARIANTEN[original[1]]["name"] if original and
        original[1] in logik.VARIANTEN else "", "original_link": f"/ergebnis/{original[0]}" if original else "",
        "variante_moeglich": bool(neu_modus()) and not original and _variante_quelle(kette, kopf, e, z) is not None,
        "variante_arten": logik.VARIANTEN, "extra_max": logik.VARIANTE_EXTRA_MAX,
        "ziel": ziel, "nochmal": nochmal, "nochmal_weg": nochmal_weg,
        "neu_link": logik.neu_link(reihe["id"] if reihe and reihe["laufend"] else ""),
        "e": e, "kopf_id": kopf["id"], "basis_url": logik.ergebnis_link(kopf), "token": logik.formular_token(GEHEIM),
        "aktionen": neu_modus(), "offen": offen if offen in ("rueckmeldung", "eigene", "variante") else "",
        "hinweis": hinweis, "fehler": fehler or [], "text": text, "text_max": logik.NEU_TEXT_MAX,
        "rueck_endungen": ",".join(logik.RUECK_ENDUNGEN), "eigene_endungen": ",".join(logik.EIGENE_ENDUNGEN),
        **rahmen(reihen, logik.krumen(e["titel"], reihe, ueber), reihe["id"] if reihe else "",
                 neu_hier=_neu_hier(reihe, nr) if reihe else "")}, status_code=status)


@app.get("/ergebnis/{eintrag_id}", response_class=HTMLResponse)
def seite_ergebnis(request: Request, eintrag_id: str):
    kette, kopf = _kette(eintrag_id)
    if kopf["id"] != eintrag_id:
        return RedirectResponse(f"/ergebnis/{kopf['id']}", status_code=303)
    reihe = logik.reihe_von(kopf, reihen_laden())
    aktion = request.query_params.get("erledigt") or ""
    fassung = _material(kette, kopf)[0]["final_name"] if aktion == "final" else ""
    hinweis = logik.hinweis_nach(aktion, logik.reihe_text(reihe), fassung)
    return _ergebnis_seite(request, kette, kopf, request.query_params.get("offen") or "", hinweis)


def _kopf_fuer_post(eintrag_id: str) -> tuple[list[dict], dict]:
    """Aktionen gehen nur an die Ansicht selbst (ID des Ursprungs), sonst 404."""
    kette, kopf = _kette(eintrag_id)
    if kopf["id"] != eintrag_id:
        raise HTTPException(404)
    return kette, kopf


def _fertig(kopf: dict, was: str) -> RedirectResponse:
    return RedirectResponse(f"{logik.ergebnis_link(kopf)}?erledigt={was}", status_code=303)


@app.post("/ergebnis/{eintrag_id}/final", response_class=HTMLResponse)
async def ergebnis_final(request: Request, eintrag_id: str):
    kette, kopf = _kopf_fuer_post(eintrag_id)
    form = await formular_lesen(request, "Final", 0)
    if not logik.token_passt(GEHEIM, str(form.get("token") or "")):
        return _ergebnis_seite(request, kette, kopf, hinweis=logik.VERALTET, status=400)
    e, _, z = _material(kette, kopf)
    ref, an = str(form.get("ref") or ""), form.get("an") == "1"
    if not logik.final_erlaubt(ref, e["verlauf"]):
        raise HTTPException(404)
    if not an and (z["final"].get(kopf["id"]) or {}).get("fassung") != ref:
        return _fertig(kopf, "nicht-final")  # war nicht final: nichts zu tun
    try:
        fassungen.final_setzen(kopf["id"], ref if an else None, basis=INSTANZ / "auftraege")
    except (fassungen.FassungFehler, OSError) as fehler_:
        logger.error("Final nicht gespeichert: %s", fehler_)
        return _ergebnis_seite(request, kette, kopf, hinweis=logik.FEHLGESCHLAGEN, status=500)
    logger.info("Final %s: %s (%s)", "an" if an else "aus", kopf["id"], ref)
    return _fertig(kopf, "final" if an else "nicht-final")


def _variante_quelle(kette: list[dict], kopf: dict, e: dict, z: dict) -> Path | None:
    """Datei, aus der eine Variante entsteht: die finale Fassung (auch Lias eigene), sonst die Datei oben in der
    Ansicht. Nur Material des Material-Agenten und nur Word/PowerPoint (logik.VARIANTE_ENDUNGEN)."""
    if kopf.get("agent") != logik.NEU_AGENT:
        return None
    endungen = set(logik.VARIANTE_ENDUNGEN)
    final = (z["final"].get(kopf["id"]) or {}).get("fassung") or ""
    if final.startswith("eigene-"):
        eigene = z["eigene"].get(kopf["id"]) or []
        n = int(final.rsplit("-", 1)[1]) if final.rsplit("-", 1)[1].isdigit() else 0
        return _eigene_pfad(kopf, eigene, n, endungen)
    fassung = next((a for a in logik.fassungen(kette) if a["id"] == final), None)
    if fassung and fassung.get("status") == "erledigt" and fassung.get("ergebnis_dateien"):
        kandidaten = [(fassung, nr) for nr in range(len(fassung["ergebnis_dateien"]))]
    else:
        nach_id = {a["id"]: a for a in kette}
        kandidaten = [(nach_id[d["auftrag"]], d["nr"]) for d in e["dateien"] if d["auftrag"] in nach_id]
    for auftrag, nr in kandidaten:
        rel = auftrag["ergebnis_dateien"][nr]
        wurzel = dateien.agent_ordner(INSTANZ, auftrag.get("agent"))
        pfad = dateien.sicher(wurzel, rel, endungen) if wurzel else None
        if pfad:
            return pfad
    return None


@app.post("/ergebnis/{eintrag_id}/variante", response_class=HTMLResponse)
async def ergebnis_variante(request: Request, eintrag_id: str):
    modus = neu_modus()
    if not modus:
        raise HTTPException(404)
    kette, kopf = _kopf_fuer_post(eintrag_id)
    form = await formular_lesen(request, "Variante", 0)
    art, extra = str(form.get("art") or ""), str(form.get("extra") or "")
    if not logik.token_passt(GEHEIM, str(form.get("token") or "")):
        return _ergebnis_seite(request, kette, kopf, "variante", fehler=[logik.VERALTET], text=extra, status=400)
    extra, fehler = logik.variante_pruefen(art, extra)
    if fehler:
        return _ergebnis_seite(request, kette, kopf, "variante", fehler=fehler, text=extra, status=400)
    e, _, z = _material(kette, kopf)
    if logik.variante_von(z, kopf["id"]):
        raise HTTPException(404)  # keine Variante einer Variante
    quelle = _variante_quelle(kette, kopf, e, z)
    if quelle is None:
        raise HTTPException(404)
    reihen = reihen_laden()
    reihe = logik.reihe_von(kopf, reihen)
    text = logik.text_mit_reihe(logik.variante_text(art, e["titel"], extra), reihe["id"] if reihe else None, reihen)
    if logik.auftrag_doppelt(_auftraege_von(logik.NEU_AGENT), datetime.now(ZONE), text,
                             ort=reihe["id"] if reihe else None, dateinamen=[quelle.name]):  # Doppelklick
        logger.info("Gleiche Variante %s zu %s gerade schon angelegt, verworfen", art, kopf["id"])
        return _fertig(kopf, "variante" if modus == "echt" else "variante-test")
    EINGANG.mkdir(parents=True, exist_ok=True)
    ablage = Path(tempfile.mkdtemp(dir=EINGANG))
    try:
        kopie = ablage / quelle.name  # agentkit verschiebt den Anhang, das Original bleibt
        shutil.copyfile(quelle, kopie)
        aid = auftraege.neuer_auftrag(logik.NEU_AGENT, text, quelle=logik.NEU_QUELLE, dateien=[kopie],
                                      basis=INSTANZ / "auftraege", agenten_dir=INSTANZ.parent,
                                      absender=config.person(INSTANZ), reihe=reihe["id"] if reihe else None,
                                      ort=reihe["id"] if reihe else None)
        z_ = zustand_()
        z_.schreiben(logik.variante_dazu(z_.lesen(), kopf["id"], art, aid, datetime.now(ZONE).isoformat()))
    except (auftraege.AuftragFehler, OSError) as fehler_:
        logger.error("Variante nicht angelegt: %s", fehler_)
        return _ergebnis_seite(request, kette, kopf, "variante", fehler=[logik.FEHLGESCHLAGEN], text=extra,
                               status=500)
    finally:
        shutil.rmtree(ablage, ignore_errors=True)
    logger.info("Variante %s (%s) zu %s angelegt (%s)", aid, art, kopf["id"], modus)
    if modus == "echt":
        agent_starten(logik.NEU_AGENT)
    return _fertig(kopf, "variante" if modus == "echt" else "variante-test")


@app.post("/auftrag/{eintrag_id}/zurueckziehen")
async def auftrag_zurueckziehen(request: Request, eintrag_id: str):
    """Laufenden oder wartenden Auftrag zurückziehen (agentkit.auftraege.zurueckziehen; ein laufender claude-Lauf
    endet binnen Sekunden). Wie Neuer Auftrag nur im Testbetrieb oder echt."""
    if not neu_modus():
        raise HTTPException(404)
    try:
        pruefe_id(eintrag_id)
    except AblageFehler:
        raise HTTPException(404) from None
    if not any(a.get("id") == eintrag_id for a in auftraege.neue(basis=INSTANZ / "auftraege")):
        raise HTTPException(404)
    form = await formular_lesen(request, "Zurückziehen", 0)
    if not logik.token_passt(GEHEIM, str(form.get("token") or "")):
        return RedirectResponse("/", status_code=303)
    try:
        auftraege.zurueckziehen(eintrag_id, "Von Lia in der Web-App zurückgezogen.", basis=INSTANZ / "auftraege")
    except (auftraege.AuftragFehler, OSError) as fehler_:
        logger.error("Zurückziehen von %s fehlgeschlagen: %s", eintrag_id, fehler_)
        raise HTTPException(409) from None
    logger.info("Auftrag %s zurückgezogen", eintrag_id)
    return RedirectResponse("/?erledigt=zurueckgezogen", status_code=303)


@app.post("/ergebnis/{eintrag_id}/nochmal", response_class=HTMLResponse)
async def ergebnis_nochmal(request: Request, eintrag_id: str):
    modus = neu_modus()
    if not modus:
        raise HTTPException(404)
    kette, kopf = _kopf_fuer_post(eintrag_id)
    form = await formular_lesen(request, "Nochmal", 0)
    if not logik.token_passt(GEHEIM, str(form.get("token") or "")):
        return _ergebnis_seite(request, kette, kopf, hinweis=logik.VERALTET, status=400)
    if not logik.nochmal_moeglich(kette) or kopf["id"] in zustand_().lesen()["ersetzt"]:
        raise HTTPException(404)
    f = logik.nochmal_felder(kette)
    try:
        aid = auftraege.neuer_auftrag(logik.NEU_AGENT, f["text"], quelle=f["quelle"], bezug=f["bezug"],
                                      sitzung=f["sitzung"], basis=INSTANZ / "auftraege", agenten_dir=INSTANZ.parent,
                                      absender=config.person(INSTANZ), reihe=f["reihe"], ort=f["ort"])
        if not f["bezug"]:  # neuer Ursprung: Ort und Zuordnungen gehen mit, der alte verschwindet aus „Heute“
            z_ = zustand_()
            z = z_.lesen()
            ersetzt = {**z["ersetzt"], kopf["id"]: aid}
            stunde_von = dict(z["stunde_von"])
            if kopf["id"] in stunde_von:
                stunde_von[aid] = stunde_von[kopf["id"]]
            z_.schreiben({**z, "ersetzt": ersetzt, "stunde_von": stunde_von})
    except (auftraege.AuftragFehler, OSError) as fehler_:
        logger.error("Nochmal nicht angelegt: %s", fehler_)
        return _ergebnis_seite(request, kette, kopf, hinweis=logik.FEHLGESCHLAGEN, status=500)
    logger.info("Nochmal %s zu %s angelegt (%s)", aid, kopf["id"], modus)
    if modus == "echt":
        agent_starten(logik.NEU_AGENT)
    return _fertig(kopf, "nochmal" if modus == "echt" else "nochmal-test")


@app.post("/ergebnis/{eintrag_id}/stunde", response_class=HTMLResponse)
async def ergebnis_stunde(request: Request, eintrag_id: str):
    kette, kopf = _kopf_fuer_post(eintrag_id)
    reihe = logik.reihe_von(kopf, reihen_laden())
    if reihe is None:
        raise HTTPException(404)
    form = await formular_lesen(request, "Stunde zuordnen", 0)
    if not logik.token_passt(GEHEIM, str(form.get("token") or "")):
        return _ergebnis_seite(request, kette, kopf, hinweis=logik.VERALTET, status=400)
    z_ = zustand_()
    z = z_.lesen()
    wert, stunden = str(form.get("nr") or ""), logik.reihe_stunden(reihe)
    nr = logik.stunde_nummer(wert, len(stunden))
    if nr is None and wert != "0":
        raise HTTPException(404)
    try:
        z_.schreiben(logik.stunde_zuordnen(z, kopf["id"], stunden[nr - 1]["id"] if nr else None))
    except OSError as fehler_:
        logger.error("Zuordnung nicht gespeichert: %s", fehler_)
        return _ergebnis_seite(request, kette, kopf, hinweis=logik.FEHLGESCHLAGEN, status=500)
    return _fertig(kopf, "zugeordnet")


@app.post("/ergebnis/{eintrag_id}/reihe", response_class=HTMLResponse)
async def ergebnis_reihe(request: Request, eintrag_id: str):
    """Lias Zuordnung eines Auftrags ohne eigene Reihe (Chrome-Test Nr. 4); "" nimmt sie zurück."""
    kette, kopf = _kopf_fuer_post(eintrag_id)
    reihen = reihen_laden()
    z_ = zustand_()
    z = z_.lesen()
    wahl = logik.reihe_wahl(kopf, reihen, z["reihe_von"])
    form = await formular_lesen(request, "Reihe zuordnen", 0)
    if not logik.token_passt(GEHEIM, str(form.get("token") or "")):
        return _ergebnis_seite(request, kette, kopf, hinweis=logik.VERALTET, status=400)
    wert = str(form.get("reihe") or "")
    if not wahl or wert not in {w["id"] for w in wahl}:
        raise HTTPException(404)
    try:
        ziel = next((r for r in reihen if r["id"] == wert), None)
        z_.schreiben(logik.reihe_zuordnen(z, kopf["id"], wert or None, logik.reihe_stunden(ziel) if ziel else []))
    except OSError as fehler_:
        logger.error("Zuordnung zur Reihe nicht gespeichert: %s", fehler_)
        return _ergebnis_seite(request, kette, kopf, hinweis=logik.FEHLGESCHLAGEN, status=500)
    return _fertig(kopf, "zugeordnet")


def _eigene_pfad(kopf: dict, eigene: list[dict], n: int, endungen: set[str]) -> Path | None:
    """Datei der n-ten eigenen Fassung im Agent-Ordner (agentkit.fassungen), gegen den Ordner geprüft."""
    eintrag = next((e for e in eigene if e.get("n") == n), None)
    wurzel = dateien.agent_ordner(INSTANZ, kopf.get("agent"))
    if eintrag is None or wurzel is None:
        return None
    return dateien.sicher(wurzel, str(eintrag.get("datei") or ""), endungen)


def _upload_ablegen(upload: UploadFile) -> Path:
    """Upload in einen neuen Ordner unter EINGANG schreiben (agentkit verschiebt ihn dann zum Agenten)."""
    EINGANG.mkdir(parents=True, exist_ok=True)
    return datei_ablegen(upload, Path(tempfile.mkdtemp(dir=EINGANG)) / "datei")


def _eigene_speichern(kette: list[dict], kopf: dict, upload: UploadFile, notiz: str) -> tuple[str, str]:
    """Lias Datei als nächste eigene Fassung über agentkit.fassungen ablegen: (Dateiname, Name der Fassung)."""
    pfad = _upload_ablegen(upload)
    try:
        eintrag = fassungen.eigene_dazu(kopf["id"], pfad, notiz, basis=INSTANZ / "auftraege",
                                        agenten_dir=INSTANZ.parent)
    finally:
        shutil.rmtree(pfad.parent.parent, ignore_errors=True)
    eigene = zustand_().lesen()["eigene"].get(kopf["id"]) or [eintrag]
    return eintrag["name"], logik.fassung_namen(kette, eigene).get(logik.eigene_ref(eintrag["n"]), "")


def _eigene_gerade_da(kopf: dict, upload: UploadFile) -> bool:
    """Liegt genau diese Datei (Name und Inhalt) gerade erst als letzte eigene Fassung da?"""
    eigene = zustand_().lesen()["eigene"].get(kopf["id"]) or []
    letzte = logik.eigene_doppelt(eigene, logik.dateiname_bereinigen(upload.filename), datetime.now(ZONE))
    pfad = _eigene_pfad(kopf, eigene, letzte["n"], set(logik.EIGENE_ENDUNGEN)) if letzte else None
    if pfad is None:
        return False
    upload.file.seek(0)
    gleich = pfad.read_bytes() == upload.file.read()
    upload.file.seek(0)
    return gleich


@app.post("/ergebnis/{eintrag_id}/eigene", response_class=HTMLResponse)
async def ergebnis_eigene(request: Request, eintrag_id: str):
    kette, kopf = _kopf_fuer_post(eintrag_id)
    form = await formular_lesen(request, "Eigene Fassung", 1)
    datei = form.get("datei")
    try:
        if not logik.token_passt(GEHEIM, str(form.get("token") or "")):
            return _ergebnis_seite(request, kette, kopf, "eigene", fehler=[logik.VERALTET], status=400)
        if not isinstance(datei, UploadFile) or not datei.filename:
            return _ergebnis_seite(request, kette, kopf, "eigene", fehler=["Wähle eine Datei aus."], status=400)
        fehler = logik.datei_pruefen(datei.filename, datei.size or 0, logik.EIGENE_ENDUNGEN)
        if fehler:
            return _ergebnis_seite(request, kette, kopf, "eigene", fehler=fehler, status=400)
        try:
            if _eigene_gerade_da(kopf, datei):  # Doppelklick: dieselbe Bestätigung, keine zweite Fassung
                logger.info("Gleiche eigene Fassung zu %s gerade schon gespeichert, verworfen", kopf["id"])
                return _fertig(kopf, "eigene")
            _eigene_speichern(kette, kopf, datei, "")
        except (fassungen.FassungFehler, OSError) as fehler_:
            logger.error("Eigene Fassung nicht gespeichert: %s", fehler_)
            return _ergebnis_seite(request, kette, kopf, "eigene", fehler=[logik.FEHLGESCHLAGEN], status=500)
    finally:
        if isinstance(datei, UploadFile):
            await datei.close()
    logger.info("Eigene Fassung zu %s gespeichert", kopf["id"])
    return _fertig(kopf, "eigene")


@app.post("/ergebnis/{eintrag_id}/rueckmeldung", response_class=HTMLResponse)
async def ergebnis_rueckmeldung(request: Request, eintrag_id: str):
    modus = neu_modus()
    if not modus:
        raise HTTPException(404)
    kette, kopf = _kopf_fuer_post(eintrag_id)
    form = await formular_lesen(request, "Rückmeldung", 1)
    datei = form.get("datei")
    datei = datei if isinstance(datei, UploadFile) and datei.filename else None
    text = str(form.get("text") or "")
    ziel = logik.rueckmeldung_ziel(kette, str(form.get("fassung") or ""), str(form.get("dnr") or ""),
                                   str(form.get("seite") or ""))
    try:
        if not logik.token_passt(GEHEIM, str(form.get("token") or "")):
            return _ergebnis_seite(request, kette, kopf, "rueckmeldung", fehler=[logik.VERALTET], text=text,
                                   status=400, ziel=ziel)
        text, fehler = logik.rueckmeldung_pruefen(text, (datei.filename, datei.size or 0) if datei else None)
        # an einer Datei: die Fassung, aus der sie stammt (die Nachbesserung setzt dort auf); sonst wie in
        # Telegram die neueste fertige Fassung des Assistenten
        bezug = ziel["fassung"] if ziel else next(
            (a["id"] for a in reversed(logik.fassungen(kette)) if a.get("status") == "erledigt"), "")
        if not bezug:
            raise HTTPException(404)
        if fehler:
            return _ergebnis_seite(request, kette, kopf, "rueckmeldung", fehler=fehler, text=text, status=400,
                                   ziel=ziel)
        auftragstext = logik.rueckmeldung_text(text, datei.filename if datei else "", ziel)
        # Doppelklick: Lia sieht die Antwort der zweiten Anfrage, also dieselbe Bestätigung. Prüfen und Anlegen liegen
        # ohne await hintereinander, gleichzeitige Anfragen kommen sich dazwischen nicht in die Quere.
        basis = INSTANZ / "auftraege"
        if logik.auftrag_doppelt(_auftraege_von("feedback"), datetime.now(ZONE), auftragstext, bezug=bezug):
            logger.info("Gleiche Rückmeldung zu %s gerade schon angelegt, verworfen", bezug)
            return _fertig(kopf, "rueckmeldung" if modus == "echt" else "rueckmeldung-test")
        pfad = _upload_ablegen(datei) if datei else None
        try:  # agentkit: die Datei kommt mit ihrer Art in die Kette (Agent sieht sie), dann der Auftrag an den Feedback-Dienst
            fid, _ = fassungen.rueckmeldung(bezug, auftragstext, pfad, basis=basis, agenten_dir=INSTANZ.parent)
        except (fassungen.FassungFehler, auftraege.AuftragFehler, OSError) as fehler_:
            logger.error("Rückmeldung nicht angelegt: %s", fehler_)
            return _ergebnis_seite(request, kette, kopf, "rueckmeldung", fehler=[logik.FEHLGESCHLAGEN], text=text,
                                   status=500, ziel=ziel)
        finally:
            if pfad:
                shutil.rmtree(pfad.parent.parent, ignore_errors=True)
    finally:
        if datei:
            await datei.close()
    logger.info("Rückmeldung %s zu %s angelegt (%s, Datei: %s)", fid, bezug, modus, "ja" if datei else "nein")
    if modus == "echt":
        agent_starten("feedback")
    return _fertig(kopf, "rueckmeldung" if modus == "echt" else "rueckmeldung-test")


@app.get("/ergebnis/{eintrag_id}/eigene/{nr:int}")
def eigene_datei(eintrag_id: str, nr: int):
    _, kopf = _kopf_fuer_post(eintrag_id)
    z_ = zustand_()
    eigene = z_.lesen()["eigene"].get(kopf["id"]) or []
    return _ausliefern(_eigene_pfad(kopf, eigene, nr, set(logik.RUECK_ENDUNGEN)))


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
    kette = logik.kette_von(eintrag_id, _alle_auftraege())
    eigene = zustand_().lesen()["eigene"].get(logik.kopf(kette).get("id"), []) if kette else []
    e = logik.betrachter(kette, eintrag_id, datei, seite, eigene) if datei else None
    if e is None:
        raise HTTPException(404)
    reihen = reihen_laden()
    reihe = logik.reihe_von(logik.kopf(kette), reihen)
    ueber = {"text": e["ergebnis_titel"], "link": e["ergebnis_link"]}
    return vorlagen.TemplateResponse(request, "ansehen.html", {
        "e": e, "aktionen": neu_modus(), **rahmen(reihen, logik.krumen(e["titel"], reihe, ueber), reihe["id"] if reihe else "")})


@app.get("/entwurf/{eintrag_id}", response_class=HTMLResponse)
def seite_entwurf(request: Request, eintrag_id: str):
    return _entwurf_seite(request, _entwurf(eintrag_id),
                          logik.HINWEISE.get(request.query_params.get("erledigt") or "", ""))


def _entwurf(eintrag_id: str) -> dict:
    try:
        pruefe_id(eintrag_id)
    except AblageFehler:
        raise HTTPException(404) from None
    eintrag = next((e for e in _entwuerfe() if e.get("id") == eintrag_id), None)
    if eintrag is None:
        raise HTTPException(404)
    return eintrag


def _entwurf_seite(request: Request, eintrag: dict, hinweis: str = "", status: int = 200):
    e = logik.entwurf(eintrag, datetime.now(ZONE))
    reihen = reihen_laden()
    reihe = logik.reihe_von(eintrag, reihen)
    return vorlagen.TemplateResponse(request, "entwurf.html", {
        "e": e, "hinweis": hinweis, "token": logik.formular_token(GEHEIM), "link": logik.entwurf_link(eintrag),
        **rahmen(reihen, logik.krumen(e["titel"], reihe), reihe["id"] if reihe else "")}, status_code=status)


@app.post("/entwurf/{eintrag_id}", response_class=HTMLResponse)
async def entwurf_entscheiden(request: Request, eintrag_id: str):
    eintrag = _entwurf(eintrag_id)
    if not logik.entwurf_lia_darf(eintrag):
        raise HTTPException(404)  # Entwürfe nach außen entscheidet Jan
    form = await formular_lesen(request, "Entwurf", 0)
    if not logik.token_passt(GEHEIM, str(form.get("token") or "")):
        return _entwurf_seite(request, eintrag, logik.VERALTET, 400)
    stand = str(form.get("stand") or "")
    if stand and stand not in logik.ENTWURF_ENTSCHEIDUNGEN:
        raise HTTPException(400)
    z_ = zustand_()
    try:
        z_.schreiben(logik.entwurf_entscheiden(z_.lesen(), eintrag_id, stand, datetime.now(ZONE).isoformat()))
    except OSError as fehler_:
        logger.error("Entscheidung zu %s nicht gespeichert: %s", eintrag_id, fehler_)
        return _entwurf_seite(request, eintrag, logik.FEHLGESCHLAGEN, 500)
    logger.info("Entwurf %s: %s", eintrag_id, stand or "wieder offen")
    return RedirectResponse(f"{logik.entwurf_link(eintrag)}?erledigt=entwurf-{stand or 'offen'}", status_code=303)


def socket_vorbereiten(socket_pfad: Path = SOCKET) -> None:
    socket_pfad.parent.mkdir(parents=True, exist_ok=True)
    socket_pfad.parent.chmod(0o700)  # Uvicorn gibt dem Socket 0666, der Ordner hält andere Benutzer fern
    socket_pfad.unlink(missing_ok=True)  # Rest eines früheren Laufs


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    port = logik.port_pruefen(PORT)
    ort = f"127.0.0.1:{port}" if port else str(SOCKET)
    logger.info("Web-App hört auf %s, Instanz %s, Neuer Auftrag: %s, Fragen: %s", ort, INSTANZ,
                neu_modus() or "aus", "an" if CHAT else "aus")
    if NEUER_AUFTRAG and not neu_modus():
        logger.warning("WEBAPP_NEUER_AUFTRAG=%s gilt nicht für %s, Neuer Auftrag bleibt aus", NEUER_AUFTRAG, INSTANZ)
    if port:  # nur lokal; von außen nur über Caddy (HTTPS, Passwort)
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info", proxy_headers=False, server_header=False)
        return
    socket_vorbereiten()
    try:
        uvicorn.run(app, uds=str(SOCKET), log_level="info", proxy_headers=False, server_header=False)
    finally:
        SOCKET.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
