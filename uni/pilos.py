"""Online-Raum für Treffen über HNEE Meeting (pilos.hnee.de, BigBlueButton).

Die HNEE nimmt neue Webkonferenzen nur noch über PILOS an (Hinweis auf bbb.hnee.de, 18.11.2026). Anmeldung
per LDAP mit HNEE_NUTZER und HNEE_KENNWORT, wie im Browser (Sanctum: Cookie XSRF-TOKEN, dann JSON-API).
Der Agent hat einen festen Raum (RAUMNAME, Typ Meeting). Gibt es ihn nicht, legt er ihn einmal an. Link und
Zugangscode stehen danach in data/sitzungsraum.json (600), weitere Mails brauchen keine Anmeldung.
Wird der Raum in PILOS gelöscht, die Datei löschen; der nächste Bedarf legt ihn neu an.

Rein und getestet: braucht_link, hinweis, links_pruefen, link_warnung, raum_auffrischen, raum_waehlen, typ_id, raum_aus.
"""

import http.cookiejar
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
RAUM_DATEI = HIER / "data" / "sitzungsraum.json"
BASIS = "https://pilos.hnee.de"
RAUMNAME = "Forschungsprojekt Fehlstellen"
RAUMTYP = "Meeting"

# Jans Auftrag fragt nach einem Online-Treffen mit Link
_STARK = re.compile(r"\b(bbb|bigbluebutton|pilos|videokonferenz|webkonferenz|einwahl\w*|online-?(treffen|termin|"
                    r"sitzung|meeting|besprechung))\b", re.I)
_LINK = re.compile(r"\blink\w*\b", re.I)
_WORUM = re.compile(r"(sitzung|treffen|meeting|konferenz|raum|online|besprechung|einladung|einladen)", re.I)
# Konferenzlinks, die nur von Python kommen dürfen
_KONFERENZ = re.compile(r"https?://[^\s<>()\"']*(pilos\.hnee\.de|bbb\.hnee\.de|bigbluebutton|zoom\.us|"
                        r"teams\.microsoft\.com|meet\.google\.com|webex\.com)[^\s<>()\"']*", re.I)


class PilosFehler(Exception):
    pass


def braucht_link(text: str) -> bool:
    """Will Jan zu einem Online-Treffen einladen (Link zur Sitzung, BBB, Online-Treffen ...)?"""
    return bool(_STARK.search(text) or (_LINK.search(text) and _WORUM.search(text)))


def link(raum_id: str, basis: str = BASIS) -> str:
    return f"{basis.rstrip('/')}/rooms/{raum_id}"


def raum_aus(daten: dict, basis: str = BASIS) -> dict:
    """{"id", "name", "url", "zugangscode"} aus der Antwort von /api/v1/rooms/<id> (Feld data)."""
    return {"id": daten["id"], "name": daten["name"], "url": link(daten["id"], basis),
            "zugangscode": str(daten.get("access_code") or "")}


def raum_waehlen(raeume: list[dict], name: str = RAUMNAME, besitzer_id: int | None = None) -> dict | None:
    """Der eigene Raum mit genau diesem Namen (ohne Groß/klein), sonst None."""
    for r in raeume:
        if str(r.get("name", "")).strip().lower() != name.strip().lower():
            continue
        if besitzer_id is not None and (r.get("owner") or {}).get("id") != besitzer_id:
            continue
        return r
    return None


def typ_id(typen: list[dict], name: str = RAUMTYP) -> int:
    for t in typen:
        if str(t.get("name", "")).lower() == name.lower():
            return int(t["id"])
    raise PilosFehler(f"Raumtyp {name!r} gibt es nicht (vorhanden: {', '.join(str(t.get('name')) for t in typen)})")


def hinweis(raum: dict) -> str:
    """Satz für den Auftragstext: Claude nimmt genau diesen Link, Python hat ihn aus PILOS."""
    code = (f" Zugangscode: {raum['zugangscode']} (gehört mit in die Mail, sonst kommt niemand hinein)."
            if raum.get("zugangscode") else " Ein Zugangscode ist nicht nötig, nenn keinen.")
    return (f"\n\nOnline-Raum für das Treffen (BigBlueButton über HNEE Meeting, von Python angelegt): {raum['url']}."
            f"{code} Nimm genau diesen Link in die Mail, erfinde keinen anderen und nenn keinen anderen Dienst.")


def links_pruefen(text: str, raum: dict | None, quellen: str = "") -> list[str]:
    """Fehler je Konferenzlink im Entwurf, der weder der Raum von Python ist noch in quellen steht
    (Jans Auftrag, gefundene Mails): Solche Links hat Claude erfunden."""
    erlaubt = raum["url"].rstrip("/") if raum else None
    fremd = [m.group(0).rstrip(".,;:!?") for m in _KONFERENZ.finditer(text)]
    return [f"Konferenzlink nicht von Python: {u}" for u in fremd if u.rstrip("/") != erlaubt and u not in quellen]


LINK_FEHLT = "Jan wollte einen Link zum Online-Treffen, im Text steht er nicht."


def link_warnung(daten: dict, raum: dict | None) -> dict:
    """Gab Python einen Raum vor und fehlt sein Link im Text, steht das unter "Bitte prüfen" in der Freigabe."""
    if not raum or raum["url"] in daten["text"]:
        return daten
    return {**daten, "pruefen": " ".join(filter(None, (LINK_FEHLT, daten.get("pruefen"))))}


def raum_auffrischen(gespeichert: dict, aktuell: dict | None) -> dict:
    """Kontext eines Mail-Auftrags (kontext.json) mit dem aktuellen Raum: Hat sich der Raum seitdem geändert
    (z. B. Zugangscode abgeschaltet), ersetzt der neue Hinweis den alten, damit Ändern nichts Veraltetes nennt."""
    alt = gespeichert.get("raum")
    if not alt or not aktuell or aktuell == alt:
        return gespeichert
    return {**gespeichert, "raum": aktuell, "text": gespeichert["text"].replace(hinweis(alt), hinweis(aktuell))}


class Pilos:
    """Dünne Verbindung zur JSON-API von PILOS (nur das, was der Agent braucht)."""

    def __init__(self, nutzer: str, kennwort: str, basis: str = BASIS):
        self.basis = basis.rstrip("/")
        self.nutzer, self.kennwort = nutzer, kennwort
        self._kekse = http.cookiejar.CookieJar()
        self._oeffner = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self._kekse))
        self._benutzer = None

    def _xsrf(self) -> str:
        return urllib.parse.unquote(next((k.value for k in self._kekse if k.name == "XSRF-TOKEN"), ""))

    def _anfrage(self, methode: str, pfad: str, inhalt: dict | None = None) -> dict:
        anfrage = urllib.request.Request(
            self.basis + pfad, method=methode, data=None if inhalt is None else json.dumps(inhalt).encode(),
            headers={"Accept": "application/json", "Content-Type": "application/json",
                     "X-XSRF-TOKEN": self._xsrf(), "Referer": self.basis + "/login"})
        try:
            with self._oeffner.open(anfrage, timeout=30) as antwort:
                roh = antwort.read().decode()
        except urllib.error.HTTPError as f:
            raise PilosFehler(f"{methode} {pfad}: HTTP {f.code} {f.read().decode(errors='replace')[:200]}") from None
        except urllib.error.URLError as f:
            raise PilosFehler(f"{methode} {pfad}: {f.reason}") from None
        return json.loads(roh) if roh else {}

    def anmelden(self) -> dict:
        try:
            self._oeffner.open(self.basis + "/sanctum/csrf-cookie", timeout=30).read()
        except urllib.error.URLError as f:
            raise PilosFehler(f"PILOS nicht erreichbar: {f}") from None
        self._anfrage("POST", "/api/v1/login/ldap", {"username": self.nutzer, "password": self.kennwort})
        self._benutzer = self._anfrage("GET", "/api/v1/currentUser")["data"]
        if not self._benutzer or "id" not in self._benutzer:
            raise PilosFehler("Anmeldung bei PILOS fehlgeschlagen")
        return self._benutzer

    def eigene_raeume(self) -> list[dict]:
        raeume, seite = [], 1
        while True:
            r = self._anfrage("GET", "/api/v1/rooms?" + urllib.parse.urlencode({
                "filter_own": 1, "filter_shared": 0, "filter_public": 0, "filter_all": 0, "only_favorites": 0,
                "sort_by": "alpha", "per_page": 20, "page": seite}))
            raeume += r.get("data", [])
            if seite >= int((r.get("meta") or {}).get("last_page") or 1):
                return raeume
            seite += 1

    def raum(self, raum_id: str) -> dict:
        return self._anfrage("GET", f"/api/v1/rooms/{urllib.parse.quote(raum_id)}")["data"]

    def raum_anlegen(self, name: str, typ: str = RAUMTYP) -> dict:
        typen = self._anfrage("GET", "/api/v1/roomTypes?filter=own")["data"]
        return self._anfrage("POST", "/api/v1/rooms", {"name": name, "room_type": typ_id(typen, typ)})["data"]


def gespeicherter_raum(datei: Path | None = None) -> dict | None:
    """Der schon bekannte Raum (ohne Netz), sonst None."""
    datei = datei or RAUM_DATEI
    try:
        return json.loads(datei.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def sitzungsraum(cfg: dict, datei: Path | None = None, verbindung=None) -> dict:
    """Der feste Raum des Agenten: aus data/sitzungsraum.json, sonst aus PILOS (anlegen, falls es ihn nicht gibt).

    Wirft PilosFehler, wenn PILOS nicht antwortet oder die Anmeldung scheitert.
    """
    datei = datei or RAUM_DATEI
    if raum := gespeicherter_raum(datei):
        return raum
    p = verbindung or Pilos(cfg["HNEE_NUTZER"], cfg["HNEE_KENNWORT"])
    ich = p.anmelden()
    vorhanden = raum_waehlen(p.eigene_raeume(), RAUMNAME, ich.get("id"))
    rid = vorhanden["id"] if vorhanden else p.raum_anlegen(RAUMNAME)["id"]
    raum = raum_aus(p.raum(rid), p.basis)
    datei.parent.mkdir(exist_ok=True)
    fd = os.open(datei, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(raum, f, ensure_ascii=False, indent=1)
    return raum
