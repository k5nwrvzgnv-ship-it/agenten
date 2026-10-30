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
  /ergebnis/<id>/eigene/<n>             Download von Lias n-ter eigener Fassung (zustand.py)
  /ergebnis/<id>/datei/<n>/ansehen      Seiten-Betrachter (?seite=m, Standard 1): eine Seite groß, Vor/Zurück,
                                        ohne JavaScript; <id> ist die Fassung, aus der die Datei stammt
  /entwurf/<id>                         offener Entwurf, ganzer Text; Lia entscheidet bei Typ entwurf selbst
  /reihe/<kennung>                      Reihe mit Reihenfrage und ihren Aufträgen (ordnung.py, nur lesend)
  /reihe/<kennung>/stunde/<n>           Stunde (bzw. Probe) n mit Thema und Material (Stunden speichert die Web-App)
  /fach/<kennung>                       Fach mit Klassen/Kursen (nur lesend)
  /klasse/<kennung>                     Klasse/Kurs mit ihren Reihen (nur lesend)
  /vorlagen                             Gestaltung (Profil des Material-Agenten) und Arten, nur lesend
  /ich                                  Lias Regeln (regeln.md, Gelernte Regeln der Agenten), nur lesend
  /unterricht                           alte Seite, leitet auf / um
  /statisch/...                         CSS, htmx
  /neu                                  Galerie der Vorlagen bzw. Formular (?art=…), Ort vorbelegt (?reihe=…&stunde=n),
                                        nur wenn eingeschaltet
POST:
  /neu                                  legt einen Auftrag an (agentkit.auftraege.neuer_auftrag mit basis=)
  /ergebnis/<id>/rueckmeldung           Rückmeldung an den Feedback-Dienst (Auftrag an feedback, bezug = Fassung),
                                        wie Neuer Auftrag nur im Testbetrieb oder echt; eine Datei wird eigene Fassung
  /ergebnis/<id>/final                  Fassung als final markieren oder zurücknehmen (nur in data/, zustand.py)
  /ergebnis/<id>/eigene                 eigene Fassung hochladen (nur in data/, die Agenten sehen sie nicht)
  /entwurf/<id>                         Lias Entscheidung „Setze ich selbst ein“/„Brauche ich nicht“/rückgängig (data/)
  /ergebnis/<id>/nochmal                fehlgeschlagenen letzten Versuch noch einmal anlegen (nur test/echt)
  /ergebnis/<id>/stunde                 Material einer Stunde der Reihe zuordnen (nur in data/)
  /ergebnis/<id>/variante               Variante anfordern: neuer Auftrag an den Material-Agenten mit der Datei als
                                        Anhang (wie Neuer Auftrag nur test/echt), Zuordnung in data/
  /reihe/<kennung>/stunden              neue Stunde am Ende der Reihe (nur in data/)
  /reihe/<kennung>/stunde/<n>           Thema der Stunde ändern (nur in data/)

Neuer Auftrag und Rückmeldung sind ausgeschaltet, bis WEBAPP_NEUER_AUFTRAG gesetzt ist:
  test  nur mit einer anderen Instanz als lia/instanz (WEBAPP_INSTANZ), kein Agent startet
  echt  jede Instanz, danach startet lia-unterricht.service bzw. lia-feedback.service (Ergebnis kommt auch per
        Telegram, Lias Kontingent)
Final, eigene Fassung und Stunden schreiben nur in data/ der Web-App (nicht in Lias Instanz) und gehen darum immer.
Ohne Konten schützen sich die Formulare vor fremden Seiten im selben Browser (CSRF): Origin muss zum Host passen
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
import zustand

HIER = Path(__file__).resolve().parent
SOCKET = Path(os.environ.get("WEBAPP_SOCKET") or HIER / "data" / "webapp.sock")
ECHTE_INSTANZ = HIER.parent.parent / "lia" / "instanz"
INSTANZ = Path(os.environ.get("WEBAPP_INSTANZ") or ECHTE_INSTANZ)
NEUER_AUFTRAG = os.environ.get("WEBAPP_NEUER_AUFTRAG", "")  # "", "test" oder "echt" (siehe oben)
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
    return logik.heute(auftraege.neue(basis=INSTANZ / "auftraege"),
                       auftraege.erledigte(basis=INSTANZ / "auftraege"),
                       _entwuerfe(),
                       datetime.now(ZONE), config.person(INSTANZ),
                       reihen if reihen is not None else reihen_laden(), set(z_["final"]),
                       set(z_["ersetzt"]))


def rahmen(reihen: list[dict], krumen: dict, aktiv: str = "", anzahl_wartet: int | None = None,
           neu_hier: str = "", stunde: int | None = None) -> dict:
    """Werte für basis.html: Baum (links) und Brotkrumen. Ohne anzahl_wartet wird "Heute" dafür berechnet.
    neu_hier: Link für „+ Neu hier“ neben den Brotkrumen (nur, wenn Neuer Auftrag eingeschaltet ist)."""
    if anzahl_wartet is None:
        anzahl_wartet = heute_daten(reihen)["anzahl_wartet"]
    reihe = next((r for r in reihen if r["id"] == aktiv), None)
    stunden = {aktiv: logik.reihe_stunden(reihe, zustand_().lesen())} if reihe else {}
    return {"baum": logik.baum(reihen, anzahl_wartet, aktiv, stunden, stunde), "krumen": krumen,
            "neu_hier": neu_hier if neu_modus() else ""}


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


def _reihe(reihe_id: str) -> tuple[list[dict], dict]:
    """Alle Reihen und die gesuchte; unbekannt: 404."""
    reihen = reihen_laden()
    reihe = next((r for r in reihen if r["id"] == reihe_id), None)
    if reihe is None:
        raise HTTPException(404)
    return reihen, reihe


def _alle_auftraege() -> list[dict]:
    basis = INSTANZ / "auftraege"
    return [*auftraege.neue(basis=basis), *auftraege.erledigte(basis=basis)]


def _reihe_seite(request: Request, reihe_id: str, fehler: list[str] | None = None, thema: str = "",
                 status: int = 200):
    reihen, reihe = _reihe(reihe_id)
    z = zustand_().lesen()
    e = logik.reihe_ansicht(reihe, reihen, _alle_auftraege(), datetime.now(ZONE),
                            _entwuerfe(), set(z["final"]), z["eigene"],
                            logik.reihe_stunden(reihe, z), z["stunde_von"], _ausblenden(z))
    return vorlagen.TemplateResponse(request, "reihe.html", {
        "e": e, "token": logik.formular_token(GEHEIM), "fehler": fehler or [], "thema": thema,
        "thema_max": logik.STUNDE_THEMA_MAX,
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
    stunden = logik.reihe_stunden(reihe, z)
    nr = logik.stunde_nummer(nr_text, len(stunden))
    if nr is None:
        raise HTTPException(404)
    zeilen = logik.zeilen_je_reihe(reihen, _alle_auftraege(), datetime.now(ZONE),
                                   _entwuerfe(), set(z["final"]),
                                   z["eigene"], _ausblenden(z)).get(reihe_id, [])
    e = logik.stunde_ansicht(reihe, nr, stunden, zeilen, z["stunde_von"])
    return vorlagen.TemplateResponse(request, "stunde.html", {
        "e": e, "reihe": reihe, "token": logik.formular_token(GEHEIM), "hinweis": hinweis, "fehler": fehler or [],
        "thema": thema or e["titel"], "thema_max": logik.STUNDE_THEMA_MAX,
        **rahmen(reihen, logik.krumen(e["unter"], reihe), reihe["id"], neu_hier=_neu_hier(reihe, nr), stunde=nr)},
        status_code=status)


@app.get("/reihe/{reihe_id}/stunde/{nr}", response_class=HTMLResponse)
def seite_stunde(request: Request, reihe_id: str, nr: str):
    hinweis = logik.HINWEISE.get(request.query_params.get("erledigt") or "", "")
    return _stunde_seite(request, reihe_id, nr, hinweis)


@app.post("/reihe/{reihe_id}/stunden", response_class=HTMLResponse)
async def stunde_anlegen(request: Request, reihe_id: str):
    _, reihe = _reihe(reihe_id)
    if reihe.get("stunden"):
        raise HTTPException(404)  # Stunden aus reihen.toml ändert die Datei, nicht die Web-App
    form = await formular_lesen(request, "Stunde", 0)
    thema, fehler = logik.stunde_pruefen(str(form.get("thema") or ""))
    if not logik.token_passt(GEHEIM, str(form.get("token") or "")):
        fehler = [logik.VERALTET]
    if fehler:
        return _reihe_seite(request, reihe_id, fehler, thema, 400)
    z_ = zustand_()
    try:
        neu, nr = logik.stunde_dazu(z_.lesen(), reihe_id, thema, datetime.now(ZONE).isoformat())
        z_.schreiben(neu)
    except OSError as fehler_:
        logger.error("Stunde nicht gespeichert: %s", fehler_)
        raise HTTPException(500) from None
    logger.info("Stunde %d in %s angelegt", nr, reihe_id)
    return RedirectResponse(f"{logik.stunde_link(reihe, nr)}?erledigt=stunde", status_code=303)


@app.post("/reihe/{reihe_id}/stunde/{nr}", response_class=HTMLResponse)
async def stunde_aendern(request: Request, reihe_id: str, nr: str):
    _, reihe = _reihe(reihe_id)
    z_ = zustand_()
    if reihe.get("stunden"):
        raise HTTPException(404)  # Stunden aus reihen.toml ändert die Datei, nicht die Web-App
    nummer = logik.stunde_nummer(nr, len(z_.lesen()["stunden"].get(reihe_id) or []))
    if nummer is None:
        raise HTTPException(404)
    form = await formular_lesen(request, "Stunde", 0)
    thema, fehler = logik.stunde_pruefen(str(form.get("thema") or ""))
    if not logik.token_passt(GEHEIM, str(form.get("token") or "")):
        fehler = [logik.VERALTET]
    if fehler:
        return _stunde_seite(request, reihe_id, nr, fehler=fehler, thema=thema, status=400)
    try:
        z_.schreiben(logik.stunde_aendern(z_.lesen(), reihe_id, nummer, thema))
    except OSError as fehler_:
        logger.error("Stunde nicht gespeichert: %s", fehler_)
        raise HTTPException(500) from None
    return RedirectResponse(f"{logik.stunde_link(reihe, nummer)}?erledigt=thema", status_code=303)


@app.get("/fach/{fach_id}", response_class=HTMLResponse)
def seite_fach(request: Request, fach_id: str):
    reihen = reihen_laden()
    zeilen_je = logik.zeilen_je_reihe(reihen, _alle_auftraege(), datetime.now(ZONE), _entwuerfe(),
                                      ausblenden=_ausblenden(zustand_().lesen()))
    e = logik.fach_ansicht(fach_id, reihen, zeilen_je)
    if e is None:
        raise HTTPException(404)
    return vorlagen.TemplateResponse(request, "fach.html", {
        "e": e, **rahmen(reihen, {"teile": [], "hier": e["titel"]}, logik.fach_aktiv(fach_id))})


@app.get("/klasse/{gruppe_id}", response_class=HTMLResponse)
def seite_klasse(request: Request, gruppe_id: str):
    reihen = reihen_laden()
    zeilen_je = logik.zeilen_je_reihe(reihen, _alle_auftraege(), datetime.now(ZONE),
                                      _entwuerfe(),
                                      ausblenden=_ausblenden(zustand_().lesen()))
    e = logik.klasse_ansicht(gruppe_id, reihen, zeilen_je)
    if e is None:
        raise HTTPException(404)
    return vorlagen.TemplateResponse(request, "klasse.html", {
        "e": e, **rahmen(reihen, logik.krumen_klasse(e["reihe"]), logik.klasse_aktiv(gruppe_id))})


_lese_fehler: list[str] = []  # wie _reihen_fehler: Fehler im Profil nur einmal loggen


@app.get("/vorlagen", response_class=HTMLResponse)
def seite_vorlagen(request: Request):
    profil, fehler = ordnung.profil(INSTANZ)
    if fehler != _lese_fehler:
        for f in fehler:
            logger.error("Profil: %s", f)
        _lese_fehler[:] = fehler
    return vorlagen.TemplateResponse(request, "vorlagen.html", {
        "e": {"titel": "Vorlagen", "unter": "Gilt für alles, was deine Assistenz für dich baut."},
        "gestaltung": logik.gestaltung(profil), "arten": list(logik.VORLAGEN.values()),
        **rahmen(reihen_laden(), logik.krumen("Vorlagen"), "vorlagen")})


@app.get("/ich", response_class=HTMLResponse)
def seite_ich(request: Request):
    return vorlagen.TemplateResponse(request, "ich.html", {
        "e": {"titel": "Ich", "unter": "Was deine Assistenz über deine Wünsche weiß."},
        "gruppen": logik.regeln_aus(ordnung.regeltexte(INSTANZ)),
        **rahmen(reihen_laden(), logik.krumen("Ich"), "ich")})


def _ort(reihen: list[dict], reihe_id: str, stunde_text: str) -> tuple[dict | None, tuple[int, str] | None]:
    """Vorbelegter Ort für „Neu“: laufende Reihe und Stunde (Nummer, Thema); Unbekanntes fällt weg."""
    reihe = next((r for r in reihen if r["id"] == reihe_id and r["laufend"]), None)
    if reihe is None:
        return None, None
    stunden = logik.reihe_stunden(reihe, zustand_().lesen())
    nr = logik.stunde_nummer(stunde_text, len(stunden))
    return reihe, ((nr, stunden[nr - 1]["thema"]) if nr else None)


def _formular(request: Request, text: str = "", fehler: list[str] | None = None, status: int = 200,
              reihe: str = "", art: str = "", stunde: str = "", extra: dict | None = None):
    """Galerie (ohne art) bzw. Formular einer Vorlage, Ort aus reihe und stunde vorbelegt."""
    reihen = reihen_laden()
    ort_reihe, ort_stunde = _ort(reihen, reihe, stunde)
    vorlage = logik.VORLAGEN.get(art) or (logik.VORLAGE_FREI if fehler else None)
    return vorlagen.TemplateResponse(request, "neu.html", {
        "e": {"titel": vorlage["name"] if vorlage else "Neu",
              "unter": "für " + logik.ort_text(ort_reihe, ort_stunde) if ort_reihe else "Auftrag an deine Assistenz"},
        "modus": neu_modus(), "token": logik.formular_token(GEHEIM), "text": text, "fehler": fehler or [],
        "art": art if vorlage else "", "vorlage": vorlage, "varianten": logik.VARIANTEN,
        "galerie": logik.galerie(ort_reihe["id"] if ort_reihe else "", ort_stunde[0] if ort_stunde else None,
                                 ort_reihe["fach"] if ort_reihe else ""), "extra": extra or {},
        "andere": logik.neu_link(ort_reihe["id"] if ort_reihe else "", ort_stunde[0] if ort_stunde else None),
        "reihen": [] if ort_reihe else logik.reihen_auswahl(reihen), "reihe": ort_reihe["id"] if ort_reihe else reihe,
        "ort_fest": bool(ort_reihe), "stunde": ort_stunde[0] if ort_stunde else "",
        "beachte": logik.ort_text(ort_reihe, ort_stunde),
        "text_max": logik.NEU_TEXT_MAX, "max_mb": logik.NEU_DATEI_MAX_MB, "endungen": ",".join(logik.NEU_ENDUNGEN),
        **rahmen(reihen, logik.krumen("Neu", ort_reihe) if ort_reihe else logik.krumen("Neu")),
    }, status_code=status)


@app.get("/neu", response_class=HTMLResponse)
def seite_neu(request: Request):
    if not neu_modus():
        raise HTTPException(404)
    q = request.query_params
    return _formular(request, reihe=q.get("reihe") or "", art=q.get("art") or "", stunde=q.get("stunde") or "")


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


async def formular_lesen(request: Request, wofuer: str, max_dateien: int):
    """Formular einer Route mit Wirkung: Herkunft prüfen (403), Größe begrenzen (413), lesen (400)."""
    if not logik.herkunft_passt(request.headers.get("origin"), request.headers.get("host"),
                                request.headers.get("sec-fetch-site")):
        logger.warning("%s abgewiesen: fremde Herkunft", wofuer)
        raise HTTPException(403)
    grenze = (max_dateien * logik.NEU_DATEI_MAX_MB + 1) * 1024 * 1024
    if int(request.headers.get("content-length") or 0) > grenze:
        raise HTTPException(413)
    try:
        return await request.form(max_files=max_dateien + 1, max_fields=10, max_part_size=64 * 1024)
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
    _, stunde = _ort(reihen, reihe or "", stunde_text)
    EINGANG.mkdir(parents=True, exist_ok=True)
    ablage = Path(tempfile.mkdtemp(dir=EINGANG))
    try:
        pfade = []
        for nr, d in enumerate(dateien_):  # je Datei ein Unterordner: gleiche Namen überschreiben sich nicht
            pfade.append(datei_ablegen(d, ablage / str(nr)))
        aid = auftraege.neuer_auftrag(agent, logik.text_mit_reihe(text, reihe, reihen, stunde, art, extra),
                                      quelle=quelle, dateien=pfade, basis=INSTANZ / "auftraege",
                                      agenten_dir=INSTANZ.parent, absender=config.person(INSTANZ), reihe=reihe)
    except (auftraege.AuftragFehler, OSError) as fehler_:
        logger.error("Neuer Auftrag nicht angelegt: %s", fehler_)
        return _formular(request, text, [logik.FEHLGESCHLAGEN], 500, reihe or "", art, stunde_text, extra)
    finally:
        shutil.rmtree(ablage, ignore_errors=True)
        for d in dateien_:
            await d.close()
    logger.info("Auftrag %s angelegt (%s, %d Dateien, Reihe %s, Stunde %s, %s)", aid, agent, len(pfade),
                reihe or "keine", stunde[0] if stunde else "keine", modus)
    wunsch = logik.varianten_waehlen([str(w) for w in form.getlist("varianten")]) if art == "arbeitsblatt" else []
    if stunde or wunsch:  # die Web-App merkt sich Stunde und „Auch als“ (zustand.py), die Agenten kennen beides nicht
        try:
            z_ = zustand_()
            z = z_.lesen()
            if stunde:
                z = logik.stunde_zuordnen(z, aid, reihe, stunde[0])
            z_.schreiben(logik.wunsch_setzen(z, aid, wunsch))
        except OSError as fehler_:
            logger.error("Stunde/Varianten von %s nicht gespeichert: %s", aid, fehler_)
    if modus == "echt":
        agent_starten(agent)
    erledigt = "auftrag" if modus == "echt" else "auftrag-test"
    if reihe:
        r = next(x for x in reihen if x["id"] == reihe)
        ziel = logik.stunde_link(r, stunde[0]) if stunde else logik.reihe_link(r)
        return RedirectResponse(f"{ziel}?erledigt={erledigt}", status_code=303)
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


def _kette(eintrag_id: str) -> tuple[list[dict], dict]:
    """Kette und Kopf zu einer ID aus der Instanz (auch Nachbesserung oder Rückmeldung); sonst 404."""
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
    stunden = logik.reihe_stunden(reihe, z) if reihe else []
    ort = z["stunde_von"].get(kopf["id"]) or {}
    nr = ort.get("nr") if reihe and ort.get("reihe") == reihe["id"] else None
    nr = nr if isinstance(nr, int) and 1 <= nr <= len(stunden) else None
    ueber = {"text": f"{logik.stunden_wort(reihe)[0]} {nr}", "link": logik.stunde_link(reihe, nr)} if nr else None
    original = logik.variante_von(z, kopf["id"])
    if original:  # Varianten stehen beim Original: Brotkrume und Leiste von dort
        ueber = {"text": "Original", "link": f"/ergebnis/{original[0]}"}
    leiste = logik.varianten_leiste(z, original[0] if original else kopf["id"], _alle_auftraege(),
                                    datetime.now(ZONE), set(z["final"]))
    return vorlagen.TemplateResponse(request, "ergebnis.html", {
        "stunden": logik.stunden_auswahl(reihe, stunden) if stunden and not original else [], "stunde_nr": nr or 0,
        "varianten": leiste, "variante_art": logik.VARIANTEN[original[1]]["name"] if original and
        original[1] in logik.VARIANTEN else "", "original_link": f"/ergebnis/{original[0]}" if original else "",
        "variante_moeglich": bool(neu_modus()) and not original and _variante_quelle(kette, kopf, e, z) is not None,
        "variante_arten": logik.VARIANTEN, "extra_max": logik.VARIANTE_EXTRA_MAX,
        "ziel": ziel, "nochmal": bool(neu_modus()) and logik.nochmal_moeglich(kette) and kopf["id"] not in z["ersetzt"],
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
    hinweis = logik.hinweis_nach(request.query_params.get("erledigt") or "", logik.reihe_text(reihe))
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
    try:
        zustand_().schreiben(logik.final_setzen(z, kopf["id"], ref, an, datetime.now(ZONE).isoformat()))
    except OSError as fehler_:
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
        if 1 <= n <= len(eigene):
            return dateien.sicher(zustand_().ablage / kopf["id"], str(eigene[n - 1].get("datei") or ""), endungen)
        return None
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
    EINGANG.mkdir(parents=True, exist_ok=True)
    ablage = Path(tempfile.mkdtemp(dir=EINGANG))
    try:
        kopie = ablage / quelle.name  # agentkit verschiebt den Anhang, das Original bleibt
        shutil.copyfile(quelle, kopie)
        text = logik.text_mit_reihe(logik.variante_text(art, e["titel"], extra), reihe["id"] if reihe else None,
                                    reihen)
        aid = auftraege.neuer_auftrag(logik.NEU_AGENT, text, quelle=logik.NEU_QUELLE, dateien=[kopie],
                                      basis=INSTANZ / "auftraege", agenten_dir=INSTANZ.parent,
                                      absender=config.person(INSTANZ), reihe=reihe["id"] if reihe else None)
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
                                      absender=config.person(INSTANZ), reihe=f["reihe"])
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
    wert = str(form.get("nr") or "")
    nr = logik.stunde_nummer(wert, len(logik.reihe_stunden(reihe, z)))
    if nr is None and wert != "0":
        raise HTTPException(404)
    try:
        z_.schreiben(logik.stunde_zuordnen(z, kopf["id"], reihe["id"], nr))
    except OSError as fehler_:
        logger.error("Zuordnung nicht gespeichert: %s", fehler_)
        return _ergebnis_seite(request, kette, kopf, hinweis=logik.FEHLGESCHLAGEN, status=500)
    return _fertig(kopf, "zugeordnet")


def _eigene_speichern(kette: list[dict], kopf: dict, upload: UploadFile, notiz: str) -> tuple[str, str]:
    """Lias Datei als nächste eigene Fassung ablegen und im Zustand eintragen: (Dateiname, Name der Fassung)."""
    z_ = zustand_()
    z = z_.lesen()
    n = len(z["eigene"].get(kopf["id"]) or []) + 1
    ordner = z_.ordner_eigene(kopf["id"], n)
    shutil.rmtree(ordner, ignore_errors=True)  # Rest eines abgebrochenen Versuchs
    pfad = datei_ablegen(upload, ordner)
    eintrag = {"name": pfad.name, "datei": f"{n}/{pfad.name}", "zeit": datetime.now(ZONE).isoformat(), "notiz": notiz}
    neu, n = logik.eigene_dazu(z, kopf["id"], eintrag)
    try:
        z_.schreiben(neu)
    except OSError:
        shutil.rmtree(ordner, ignore_errors=True)
        raise
    return pfad.name, logik.fassung_namen(kette, neu["eigene"][kopf["id"]])[logik.eigene_ref(n)]


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
            _eigene_speichern(kette, kopf, datei, "")
        except OSError as fehler_:
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
        try:
            name, fassung = _eigene_speichern(kette, kopf, datei, "mit deinen Kommentaren") if datei else ("", "")
            fid = auftraege.neuer_auftrag("feedback", logik.rueckmeldung_text(text, name, fassung, ziel),
                                          quelle="feedback", bezug=bezug, basis=INSTANZ / "auftraege")
        except (auftraege.AuftragFehler, OSError) as fehler_:
            logger.error("Rückmeldung nicht angelegt: %s", fehler_)
            return _ergebnis_seite(request, kette, kopf, "rueckmeldung", fehler=[logik.FEHLGESCHLAGEN], text=text,
                                   status=500, ziel=ziel)
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
    if not 1 <= nr <= len(eigene):
        raise HTTPException(404)
    return _ausliefern(dateien.sicher(z_.ablage / kopf["id"], str(eigene[nr - 1].get("datei") or ""),
                                      set(logik.RUECK_ENDUNGEN)))


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
