"""Fotobox-Aufnahme: kleiner Webserver auf dem Mac. Oberfläche im Browser (nur von diesem Rechner), das iPhone holt
sich den Auslöser per Kurzbefehl über das Netz und schickt das Foto zurück. Nur Bordmittel.

Kurzbefehl: Wiederholen { GET /h/<code>/warten ; Foto aufnehmen ; POST /h/<code>/foto }. „warten“ hält die
Verbindung mit Leerzeichen offen (gegen die Zeitgrenze von iOS) und endet erst beim Auslösen sauber. Bricht sie ab,
endet die Antwort unvollständig, der Kurzbefehl bricht ab und macht kein Foto.

iPhone-App (aufnahme/app): gleiche Wege mit Kopfzeile X-App. „warten“ antwortet dann mit einem Befehl als JSON
(foto, einmessen, ev, modus), dazu schickt die App laufend POST live (kleines JPEG, X-Zustand) und POST fehler."""

import hmac
import json
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

if __package__:
    from . import kette as k
    from . import logik as l
else:
    import kette as k
    import logik as l

SEITE = Path(__file__).resolve().parent / "seite"
TYPEN = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".woff2": "font/woff2", ".jpg": "image/jpeg", ".png": "image/png",
         ".heic": "image/heic"}
FOTO_WARTEN_S = 25
MAX_FOTO = 150_000_000


class Konflikt(Exception):
    """Geht gerade nicht (z. B. iPhone nicht verbunden)."""


def schreiben(pfad: Path, daten: dict) -> None:
    neu = pfad.with_suffix(".neu")
    neu.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    neu.replace(pfad)


def befehl(*teile: str) -> str:
    try:
        return subprocess.run(teile, capture_output=True, text=True, timeout=30, check=True).stdout
    except (OSError, subprocess.SubprocessError) as e:
        print(f"Befehl {teile[0]} ging nicht: {e}", file=sys.stderr)
        return ""


def netzadresse() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as so:
        try:
            so.connect(("192.0.2.1", 9))          # schickt nichts, bestimmt nur die eigene Adresse
            return so.getsockname()[0]
        except OSError:
            return "127.0.0.1"


class Werk:
    def __init__(self, ordner: Path):
        self.ordner = ordner
        ordner.mkdir(parents=True, exist_ok=True)
        self.port = 8765
        self.schloss = threading.Condition(threading.RLock())
        self.kette = k.Kette(ordner, self.lesen, self.ids)
        self.warter: object | None = None         # der eine wartende Kurzbefehl
        self.auftrag: dict | None = None
        self.hinweis = ""
        self.befehle: list[dict] = []             # an die App: einmessen, ev, modus
        self.live = b""
        self.live_zeit = -1e9
        self.zustand: dict = {}                   # was die App zuletzt über die Kamera gemeldet hat
        self.name = befehl("scutil", "--get", "LocalHostName").strip() if sys.platform == "darwin" else ""
        datei = ordner / "einstellungen.json"
        self.einst = {"kamera_rolle_mm": 600.0, "abstand_gemessen": False, "faktor": l.FAKTOR_START,
                      "faktor_gemessen": False, "zuschnitt": None, "letzte_nr": 0, "code": secrets.token_hex(4)}
        if datei.exists():
            self.einst |= json.loads(datei.read_text(encoding="utf-8"))
        schreiben(datei, self.einst)
        datei.chmod(0o600)

    def sichern(self) -> None:
        datei = self.ordner / "einstellungen.json"
        schreiben(datei, self.einst)
        datei.chmod(0o600)

    # ---------------------------------------------------------- Balken
    def ids(self) -> list[str]:
        return sorted(p.parent.name for p in self.ordner.glob("B*/balken.json"))

    def lesen(self, kennung) -> dict:
        if not isinstance(kennung, str) or not re.fullmatch(r"B\d{3,6}", kennung):
            raise ValueError("Unbekannter Balken.")
        pfad = self.ordner / kennung / "balken.json"
        if not pfad.exists():
            raise ValueError("Unbekannter Balken.")
        return json.loads(pfad.read_text(encoding="utf-8"))

    def ablegen(self, b: dict) -> None:
        (self.ordner / b["id"]).mkdir(exist_ok=True)
        schreiben(self.ordner / b["id"] / "balken.json", b)

    def seite(self, b: dict, seite) -> dict:
        if seite not in l.SEITEN:
            raise ValueError("Unbekannte Seite.")
        return b["seiten"].setdefault(seite, {"schritt_mm": None, "plan": None, "fotos": {}})

    def plan(self, b: dict, seite: str) -> dict:
        """Steht ein Foto, gilt der eingefrorene Plan, sonst der aus den aktuellen Einstellungen."""
        s = self.seite(b, seite)
        if s["fotos"]:
            return s["plan"]
        return l.plan(b, seite, self.einst["kamera_rolle_mm"], self.einst["faktor"], s["schritt_mm"],
                      self.einst["zuschnitt"])

    def mit_plan(self, b: dict) -> dict:
        for seite in l.SEITEN:
            s = self.seite(b, seite)
            try:
                s["plan"], s["fehler"] = self.plan(b, seite), ""
            except ValueError as e:
                s["plan"], s["fehler"] = None, str(e)
        return b

    def stand(self) -> dict:
        with self.schloss:
            namen = ([f"http://{self.name}.local:{self.port}"] if self.name else []) + [
                f"http://{netzadresse()}:{self.port}"]
            return {"einstellungen": {k: v for k, v in self.einst.items() if k != "code"}, "handy": self.handy_da(), "app": self.zustand if self.app_da() else None,
                    "hinweis": self.hinweis, "ordner": str(self.ordner),
                    "adressen": [f"{n}/h/{self.einst['code']}" for n in namen],
                    "balken": [self.mit_plan(self.lesen(i)) for i in self.ids()]}

    def balken_speichern(self, daten: dict) -> dict:
        masse = l.masse_pruefen(daten)
        with self.schloss:
            if daten.get("id"):
                b = self.lesen(daten["id"])
                if any(s["fotos"] for s in b["seiten"].values()):
                    raise ValueError("Der Balken hat schon Fotos, die Maße bleiben.")
                b |= masse
            else:
                kennung, nr = l.neue_id(self.einst["letzte_nr"], self.ids())
                self.einst["letzte_nr"] = nr
                self.sichern()
                b = {"id": kennung, "angelegt": datetime.now().isoformat(timespec="seconds"), **masse, "seiten": {}}
            self.ablegen(b)
            return self.mit_plan(b)

    def vorschub(self, daten: dict) -> dict:
        with self.schloss:
            b = self.lesen(daten.get("balken"))
            s = self.seite(b, daten.get("seite"))
            if s["fotos"]:
                raise ValueError("Diese Seite hat schon Fotos, der Vorschub bleibt.")
            s["schritt_mm"] = l.zahl(daten, "mm", 10, 2000, "Vorschub") if daten.get("mm") else None
            self.ablegen(b)
            return self.mit_plan(b)

    def einstellen(self, daten: dict) -> dict:
        with self.schloss:
            self.einst["kamera_rolle_mm"] = l.zahl(daten, "kamera_rolle_mm", 150, 2000, "Abstand")
            self.einst["abstand_gemessen"] = True
            self.sichern()
        return self.stand()

    def zuschneiden(self, daten: dict) -> dict:
        """Gilt für alle Seiten ohne Fotos. Die Originale bleiben ganz, der Ausschnitt steht im Plan der Seite."""
        with self.schloss:
            self.einst["zuschnitt"] = l.zuschnitt_pruefen(daten.get("zuschnitt"))
            self.sichern()
        return self.stand()

    def massstab(self, daten: dict) -> dict:
        with self.schloss:
            b = self.lesen(daten.get("balken"))
            s = self.seite(b, daten.get("seite"))
            if not s["fotos"]:
                raise ValueError("Auf dieser Seite gibt es noch kein Foto.")
            anteil = daten.get("anteil")
            if isinstance(anteil, bool) or not isinstance(anteil, (int, float)):
                raise ValueError("Zwei Punkte im Foto anklicken.")
            strecke = l.zahl(daten, "strecke_mm", 10, 2000, "Strecke")
            self.einst["faktor"] = l.faktor_aus_messung(anteil, strecke, s["plan"]["abstand_mm"])
            self.einst["faktor_gemessen"] = True
            self.sichern()
        return self.stand()

    def abschnitt(self, kennung, seite, nr) -> tuple[dict, dict, dict]:
        b = self.lesen(kennung)
        s = self.seite(b, seite)
        p = self.plan(b, seite)
        if isinstance(nr, bool) or not isinstance(nr, int) or not 0 <= nr < len(p["mitten_mm"]):
            raise ValueError("Unbekannter Abschnitt.")
        return b, s, p

    # ---------------------------------------------------------- Fotos
    def foto_ablegen(self, kennung, seite, nr, daten: bytes, kamera: dict | None = None) -> dict:
        with self.schloss:
            b, s, p = self.abschnitt(kennung, seite, nr)
            endung = l.endung_von(daten)
            jetzt = datetime.now()
            ordner = self.ordner / kennung
            ordner.mkdir(exist_ok=True)
            mitte = p["mitten_mm"][nr]
            name = l.foto_name(kennung, seite, nr, mitte, jetzt.strftime("%Y%m%d-%H%M%S-%f")[:-3], endung)
            ziel = ordner / name
            ziel.write_bytes(daten)
            foto = {"datei": name, "vorschau": name, "zeit": jetzt.isoformat(timespec="seconds"), "mitte_mm": mitte,
                    "mb": round(len(daten) / 1e6, 1), "breite_px": None, "hoehe_px": None, "px_je_mm": None, "kamera": kamera or {}}
            self.vermessen(ziel, foto, p)
            alt = s["fotos"].get(str(nr))
            s["plan"] = p
            s["fotos"][str(nr)] = foto
            self.ablegen(b)
            if alt:
                self.verschieben(alt, ordner, ordner / "verworfen")
            return self.mit_plan(b)

    def verschieben(self, foto: dict, von: Path, nach: Path) -> None:
        nach.mkdir(exist_ok=True)
        for n in {foto["datei"], foto["vorschau"]}:
            if (von / n).exists():
                shutil.move(von / n, nach / n)

    def loeschen(self, daten: dict) -> dict:
        """Foto nach verworfen/ legen. Der Eintrag bleibt für Rückgängig in geloescht."""
        with self.schloss:
            if self.auftrag:
                raise Konflikt("Es wird gerade ausgelöst.")
            b, s, p = self.abschnitt(daten.get("balken"), daten.get("seite"), daten.get("nr"))
            foto = s["fotos"].pop(str(daten["nr"]), None)
            if foto is None:
                raise ValueError("Hier gibt es kein Foto.")
            s.setdefault("geloescht", {})[str(daten["nr"])] = {"foto": foto, "plan": p}
            ordner = self.ordner / b["id"]
            self.verschieben(foto, ordner, ordner / "verworfen")
            self.ablegen(b)
            return {"balken": self.mit_plan(b)}

    def zurueckholen(self, daten: dict) -> dict:
        with self.schloss:
            if self.auftrag:
                raise Konflikt("Es wird gerade ausgelöst.")
            b = self.lesen(daten.get("balken"))
            s = self.seite(b, daten.get("seite"))
            nr = str(daten.get("nr"))
            alt = s.get("geloescht", {}).get(nr)
            if alt is None:
                raise ValueError("Nichts zum Zurückholen.")
            if nr in s["fotos"]:
                raise ValueError("Hier gibt es schon ein neues Foto.")
            if s["fotos"] and s["plan"] != alt["plan"]:
                raise ValueError("Die Seite wurde inzwischen mit anderen Werten fotografiert.")
            del s["geloescht"][nr]
            s["plan"], s["fotos"][nr] = alt["plan"], alt["foto"]
            ordner = self.ordner / b["id"]
            self.verschieben(alt["foto"], ordner / "verworfen", ordner)
            self.ablegen(b)
            return {"balken": self.mit_plan(b)}

    def vermessen(self, ziel: Path, foto: dict, p: dict) -> None:
        """Größe und JPEG-Vorschau per sips (macOS). HEIC zeigen nicht alle Browser."""
        if sys.platform != "darwin":
            return
        g = re.findall(r"pixel(?:Width|Height): (\d+)", befehl("sips", "-g", "pixelWidth", "-g", "pixelHeight", str(ziel)))
        if len(g) == 2:
            foto["breite_px"], foto["hoehe_px"] = int(g[0]), int(g[1])
            foto["px_je_mm"] = round(l.px_je_mm(max(int(g[0]), int(g[1])), p.get("voll_mm", p["laengs_mm"])), 2)
        vorschau = ziel.with_name(ziel.stem + "_vorschau.jpg")
        befehl("sips", "-s", "format", "jpeg", "-s", "formatOptions", "85", "-Z", "2400", str(ziel), "--out", str(vorschau))
        if vorschau.exists():
            foto["vorschau"] = vorschau.name

    def handy_da(self) -> bool:
        return self.warter is not None or self.app_da()

    def app_da(self) -> bool:
        return time.monotonic() - self.live_zeit < 3

    def kamera(self, daten: dict) -> dict:
        art, wert = daten.get("art"), daten.get("wert")
        if art not in ("einmessen", "ev", "modus") or (art == "modus" and wert not in ("fest", "fein")) or (
                art == "ev" and (isinstance(wert, bool) or not isinstance(wert, (int, float)) or not -2 <= wert <= 2)):
            raise ValueError("Unbekannter Befehl.")
        with self.schloss:
            if not self.app_da():
                raise Konflikt("iPhone-App nicht verbunden.")
            self.befehle.append({"art": art, "wert": wert})
            self.schloss.notify_all()
        return {"ok": True}

    def live_vom_handy(self, daten: bytes, zustand: str) -> None:
        if l.endung_von(daten) != ".jpg":
            raise ValueError("Live-Bild ist kein JPEG.")
        neu = json.loads(zustand or "{}")
        with self.schloss:
            self.live, self.live_zeit = daten, time.monotonic()
            self.zustand = neu if isinstance(neu, dict) else {}

    def fehler_vom_handy(self, text: str, kennung: str | None) -> None:
        with self.schloss:
            self.hinweis = f"iPhone: {text[:200]}"
            auftrag = self.auftrag
            if auftrag and kennung == auftrag["id"]:
                self.auftrag = None
                auftrag["fehler"], auftrag["fertig"] = self.hinweis, True
                self.schloss.notify_all()

    def naechster_befehl(self, app: bool) -> bytes | None:
        """Was der wartende Kurzbefehl oder die App jetzt tun soll."""
        if app and self.befehle:
            return json.dumps(self.befehle.pop(0)).encode()
        a = self.auftrag
        if a and not a["abgeholt"]:
            a["abgeholt"] = True
            return json.dumps({"art": "foto", "id": a["id"], "fokus": f"{a['balken']}-{a['seite']}"}).encode() if app else b"foto"
        return None

    def ausloesen(self, daten: dict) -> dict:
        with self.schloss:
            self.abschnitt(daten.get("balken"), daten.get("seite"), daten.get("nr"))
            if self.auftrag:
                raise Konflikt("Es wird gerade schon ausgelöst.")
            if not self.handy_da():
                raise Konflikt("iPhone nicht verbunden. Kurzbefehl auf dem iPhone starten.")
            auftrag = {"balken": daten["balken"], "seite": daten["seite"], "nr": daten["nr"], "balken_neu": None,
                       "fehler": None, "fertig": False,
                       "abgeholt": False, "id": secrets.token_hex(4)}
            self.auftrag, self.hinweis = auftrag, ""
            self.schloss.notify_all()
            ende = time.monotonic() + FOTO_WARTEN_S
            while not auftrag["fertig"] and time.monotonic() < ende:
                self.schloss.wait(max(0.01, ende - time.monotonic()))
            if self.auftrag is auftrag:
                self.auftrag = None
        if auftrag["fehler"]:
            raise ValueError(auftrag["fehler"])
        if not auftrag["fertig"]:
            raise Konflikt("Kein Foto angekommen. Auf dem iPhone nachsehen und den Kurzbefehl neu starten.")
        return {"balken": auftrag["balken_neu"]}

    def foto_vom_handy(self, daten: bytes, kennung: str | None = None, kamera: str = "") -> None:
        werte = json.loads(kamera or "{}")
        with self.schloss:
            auftrag = self.auftrag
            if auftrag and kennung and kennung != auftrag["id"]:
                auftrag = None                   # verspätetes Foto eines früheren Auslösens
            if auftrag:
                self.auftrag = None
            if auftrag is None:
                endung = l.endung_von(daten)
                weg = self.ordner / "unzugeordnet"
                weg.mkdir(exist_ok=True)
                name = datetime.now().strftime("%Y%m%d-%H%M%S-%f") + endung
                (weg / name).write_bytes(daten)
                self.hinweis = f"Ein Foto kam ohne Auslöser an: unzugeordnet/{name}"
                return
            try:
                auftrag["balken_neu"] = self.foto_ablegen(auftrag["balken"], auftrag["seite"], auftrag["nr"], daten, werte)
            except (ValueError, OSError) as e:
                auftrag["fehler"] = str(e)
            finally:
                auftrag["fertig"] = True
                self.schloss.notify_all()


class Anfrage(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    timeout = 60

    def log_message(self, muster, *teile):
        pass                                     # Adressen enthalten den Code, Fehler melden wir selbst

    def antwort(self, status: int, inhalt, typ: str = "application/json; charset=utf-8") -> None:
        daten = inhalt if isinstance(inhalt, bytes) else json.dumps(inhalt, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(daten)))
        self.send_header("Cache-Control", "no-store")
        if status >= 400:
            self.send_header("Connection", "close")  # ein ungelesener Körper darf nicht als Anfrage gelten
            self.close_connection = True
        self.end_headers()
        self.wfile.write(daten)

    def vom_mac(self) -> bool:
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        return self.client_address[0] == "127.0.0.1" and host in ("localhost", "127.0.0.1")

    def handy_weg(self, weg: str) -> str | None:
        """Pfad hinter /h/<code>/, wenn der Code stimmt."""
        teile = weg.split("/")
        if len(teile) == 4 and teile[1] == "h" and hmac.compare_digest(teile[2].encode(), self.server.werk.einst["code"].encode()):
            return teile[3]
        return None

    def koerper(self) -> bytes:
        if "chunked" in (self.headers.get("Transfer-Encoding") or "").lower():
            teile, gesamt = [], 0
            while True:
                n = int(self.rfile.readline(100).split(b";")[0], 16)
                if n < 0 or (gesamt := gesamt + n) > MAX_FOTO:
                    raise ValueError("Datei zu groß.")
                teil = self.rfile.read(n)
                self.rfile.readline(100)
                if n == 0:
                    return b"".join(teile)
                if len(teil) != n:
                    raise ValueError("Übertragung abgebrochen.")
                teile.append(teil)
        n = int(self.headers.get("Content-Length") or 0)
        if not 0 <= n <= MAX_FOTO:
            raise ValueError("Datei zu groß.")
        daten = self.rfile.read(n)
        if len(daten) != n:
            raise ValueError("Übertragung abgebrochen.")
        return daten

    def do_GET(self):
        weg = urlsplit(self.path).path
        werk = self.server.werk
        if weg.startswith("/h/"):
            if self.handy_weg(weg) == "warten":
                return self.warten(werk)
            return self.antwort(403, {"fehler": "Adresse im Kurzbefehl prüfen."})
        if not self.vom_mac():
            return self.antwort(403, {"fehler": "Nur auf diesem Rechner."})
        if weg == "/api/stand":
            return self.antwort(200, werk.stand())
        if weg == "/api/bilder":
            kodytek = parse_qs(urlsplit(self.path).query).get("satz") == ["kodytek"]
            return self.antwort(200, werk.kette.kodytek_bilder() if kodytek else werk.kette.bilder())
        if weg == "/api/saetze":
            return self.antwort(200, {"kodytek": len(werk.kette.kodytek())})
        if weg == "/api/training":
            return self.antwort(200, werk.kette.stand())
        if z := re.fullmatch(r"/zuschnitt/([A-Za-z0-9_-]+?)(_k)?\.jpg", weg):
            try:
                return self.antwort(200, werk.kette.zuschnitt(z[1], bool(z[2])).read_bytes(), "image/jpeg")
            except ValueError as e:
                return self.antwort(404, {"fehler": str(e)})
        if weg == "/live.jpg" and werk.app_da():
            return self.antwort(200, werk.live, "image/jpeg")
        datei = None
        if weg == "/":
            datei = SEITE / "index.html"
        elif weg in ("/labeln", "/training"):
            datei = SEITE / f"{weg[1:]}.html"
        elif re.fullmatch(r"/[a-z-]+\.(css|js|woff2)", weg):
            datei = SEITE / weg[1:]
        elif re.fullmatch(r"/foto/B\d{3,6}/[A-Za-z0-9_-]+\.(jpg|png|heic)", weg):
            datei = werk.ordner / weg[6:]
        if datei is None or not datei.is_file():
            return self.antwort(404, {"fehler": "Gibt es nicht."})
        return self.antwort(200, datei.read_bytes(), TYPEN[datei.suffix])

    def warten(self, werk: Werk) -> None:
        ich, app = object(), self.headers.get("X-App") == "1"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        self.close_connection = True
        with werk.schloss:
            werk.warter = ich
            werk.schloss.notify_all()
        try:
            while True:
                with werk.schloss:
                    if werk.warter is not ich:
                        return                   # neuer Kurzbefehl hat übernommen: unvollständig enden
                    befehl = werk.naechster_befehl(app)
                    if befehl is not None:
                        self.wfile.write(b"%x\r\n%s\r\n0\r\n\r\n" % (len(befehl), befehl))
                        return
                    self.wfile.write(b"1\r\n \r\n")
                    werk.schloss.wait(2)
        except OSError:
            pass                                 # iPhone weg, zeigt die Oberfläche als „nicht verbunden“
        finally:
            with werk.schloss:
                if werk.warter is ich:
                    werk.warter = None

    def do_POST(self):
        teile = urlsplit(self.path)
        weg, werk = teile.path, self.server.werk
        try:
            if weg.startswith("/h/"):
                was, kennung = self.handy_weg(weg), self.headers.get("X-Auftrag")
                if was == "foto":
                    werk.foto_vom_handy(self.koerper(), kennung, self.headers.get("X-Foto", ""))
                elif was == "live":
                    werk.live_vom_handy(self.koerper(), self.headers.get("X-Zustand", ""))
                elif was == "fehler":
                    werk.fehler_vom_handy(self.koerper().decode("utf-8", "replace"), kennung)
                else:
                    return self.antwort(403, {"fehler": "Adresse im Kurzbefehl prüfen."})
                return self.antwort(200, {"ok": True})
            if not self.vom_mac() or self.headers.get("X-Aufnahme") != "1":
                return self.antwort(403, {"fehler": "Nur auf diesem Rechner."})
            roh = self.koerper()
            if weg == "/api/datei":
                q = {k: v[0] for k, v in parse_qs(teile.query).items()}
                return self.antwort(200, {"balken": werk.foto_ablegen(q.get("balken"), q.get("seite"), int(q.get("nr", "-1")), roh)})
            wege = {"/api/balken": werk.balken_speichern, "/api/vorschub": werk.vorschub, "/api/ausloesen": werk.ausloesen,
                    "/api/einstellungen": werk.einstellen, "/api/massstab": werk.massstab, "/api/kamera": werk.kamera, "/api/zuschnitt": werk.zuschneiden, "/api/loeschen": werk.loeschen,
                    "/api/zurueck": werk.zurueckholen, "/api/label": werk.kette.speichern, "/api/teil": werk.kette.teil_setzen,
                    "/api/training": werk.kette.starten, "/api/abbrechen": werk.kette.abbrechen}
            if weg not in wege:
                return self.antwort(404, {"fehler": "Gibt es nicht."})
            daten = json.loads(roh)
            if not isinstance(daten, dict):
                raise ValueError("Eingabe nicht lesbar.")
            return self.antwort(200, wege[weg](daten))
        except Konflikt as e:
            return self.antwort(409, {"fehler": str(e)})
        except ValueError as e:
            return self.antwort(400, {"fehler": str(e)})
        except OSError as e:
            print(f"Fehler: {e}", file=sys.stderr)
            return self.antwort(500, {"fehler": f"Speichern ging nicht: {e}"})


class Server(ThreadingHTTPServer):
    daemon_threads = True


def server_bauen(ordner: Path, adresse: str, port: int) -> Server:
    server = Server((adresse, port), Anfrage)
    server.werk = Werk(ordner)
    server.werk.port = server.server_address[1]
    return server


def main() -> None:
    ordner = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / "fehlstellenscan" / "aufnahmen"
    server = server_bauen(ordner, "0.0.0.0", 8765)
    print(f"Aufnahme läuft: http://localhost:8765\nFotos: {ordner}\nBeenden mit Strg+C")
    if sys.platform == "darwin":
        subprocess.Popen(["open", "http://localhost:8765"])
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")


if __name__ == "__main__":
    main()
