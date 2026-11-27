"""Fotobox-Aufnahme: kleiner Webserver auf dem Mac. Oberfläche im Browser (nur von diesem Rechner), das iPhone holt
sich den Auslöser per Kurzbefehl über das Netz und schickt das Foto zurück. Nur Bordmittel.

Kurzbefehl: Wiederholen { GET /h/<code>/warten ; Foto aufnehmen ; POST /h/<code>/foto }. „warten“ hält die
Verbindung mit Leerzeichen offen (gegen die Zeitgrenze von iOS) und endet erst beim Auslösen sauber. Bricht sie ab,
endet die Antwort unvollständig, der Kurzbefehl bricht ab und macht kein Foto.

iPhone-App (aufnahme/app): gleiche Wege mit Kopfzeile X-App. „warten“ antwortet dann mit einem Befehl als JSON
(foto, einmessen, ev, modus), dazu schickt die App laufend POST live (kleines JPEG, X-Zustand) und POST fehler.

Servermodus (--server, Jan 26.11.2026): läuft auf dem Server hinter Caddy (neurolign.meldro.de), nur 127.0.0.1.
Dieselben Seiten wie auf dem Mac (Jan 26.11.2026: „einfach ein Klon“), nur ohne iPhone: Auslösen meldet „nicht
verbunden“, ein Foto kommt über „Foto vom Mac“ (···) in den Abschnitt. Wer was darf, steht in zugang.py. Training rechnet
Jans Mac: der Server reicht die Trainingswege durch einen SSH-Tunnel an den Mac weiter (tunnel.py), der Mac öffnet
dafür einen zweiten, schmalen Eingang (--tunnel-port) und holt vor jedem Start die Labels vom Server (--abgleich)."""

import argparse
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
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

if __package__:
    from . import kette as k
    from . import logik as l
    from . import tunnel as t
    from . import zugang as z
else:
    import kette as k
    import logik as l
    import tunnel as t
    import zugang as z

SEITE = Path(__file__).resolve().parent / "seite"
TYPEN = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".woff2": "font/woff2", ".jpg": "image/jpeg", ".png": "image/png",
         ".heic": "image/heic"}
FOTO_WARTEN_S = 25
MAX_FOTO = 150_000_000
ERSTE_SERVER_NR = 500                            # Servermodus vergibt B501, B502, ...
MAX_HOCHLADEN = 40_000_000                       # je Foto im Servermodus, Caddy lässt 50 MB durch
ABGLEICH_S = 300                                 # Labels vom Server holen vor dem Training, höchstens
ABHOLEN_S = 3                                    # Server fragt so oft nach fertigen Vorlabeln


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


def freier_plan() -> dict:
    """Plan einer Seite mit hochgeladenen Fotos: keine Abschnitte, kein Zuschnitt, Maße nur in Pixeln."""
    return {"frei": True, "zuschnitt": None, "faktor": l.FAKTOR_START, "laengs_mm": None, "mitten_mm": []}


class Werk:
    def __init__(self, ordner: Path, python: Path | None = None):
        self.ordner = ordner
        ordner.mkdir(parents=True, exist_ok=True)
        self.port = 8765
        self.schloss = threading.Condition(threading.RLock())
        self.kette = k.Kette(ordner, self.lesen, self.ids)
        if python:
            self.kette.python = python            # Servermodus: Pillow und opencv aus der .venv von fehlstellenscan
        self.abgleich: Path | None = None         # Mac: Skript, das vor dem Training die Labels vom Server holt
        self.warter: object | None = None         # der eine wartende Kurzbefehl
        self.auftrag: dict | None = None
        self.hinweis = ""
        self.befehle: list[dict] = []             # an die App: einmessen, ev, modus
        self.live = b""
        self.live_zeit = -1e9
        self.raster: dict | None = None           # Raster der Mac-Seite, geht mit jeder Live-Antwort an die App
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
            if s["fotos"] and (s.get("plan") or {}).get("frei"):
                s["plan"], s["fehler"] = None, "Hochgeladen, ohne Abschnitte."   # Fotobox lässt diese Seite in Ruhe
                continue
            try:
                s["plan"], s["fehler"] = self.plan(b, seite), ""
            except ValueError as e:
                s["plan"], s["fehler"] = None, str(e)
        b["pruefung"] = l.kontrollen_mittel(b.get("kontrollen", []))
        return b

    def stand(self, server: bool = False) -> dict:
        """Stand für die Seiten. Im Servermodus ohne iPhone-Adressen (das iPhone spricht nur mit dem Mac)."""
        with self.schloss:
            namen = [] if server else ([f"http://{self.name}.local:{self.port}"] if self.name else []) + [
                f"http://{netzadresse()}:{self.port}"]
            return {"einstellungen": {k: v for k, v in self.einst.items() if k != "code"}, "handy": self.handy_da(), "app": self.zustand if self.app_da() else None,
                    "hinweis": self.hinweis, "ordner": str(self.ordner),
                    "adressen": [f"{n}/h/{self.einst['code']}" for n in namen],
                    "balken": [self.mit_plan(self.lesen(i)) for i in self.ids()]}

    def balken_speichern(self, daten: dict, von: str | None = None) -> dict:
        masse = l.masse_pruefen(daten) | {"name": l.name_pruefen(daten.get("name"))}
        with self.schloss:
            if daten.get("id"):
                b = self.lesen(daten["id"])
                if self.auftrag and self.auftrag["balken"] == b["id"]:
                    raise Konflikt("Es wird gerade ausgelöst.")
                self.masse_aendern(b, masse)
            else:
                kennung, nr = l.neue_id(self.einst["letzte_nr"], self.ids())
                self.einst["letzte_nr"] = nr
                self.sichern()
                b = {"id": kennung, "angelegt": datetime.now().isoformat(timespec="seconds"), **masse, "seiten": {}}
                if von:
                    b["von"] = von
            self.ablegen(b)
            return self.mit_plan(b)

    def masse_aendern(self, b: dict, masse: dict) -> None:
        """Neue Maße übernehmen, ohne ein Foto zu verwerfen. Seiten mit Fotobox-Fotos behalten ihre Abschnitte, nur
        Abstand und Maßstab folgen den neuen Maßen (logik.plan_anpassen), dazu px/mm je Foto und die Prüfmessungen
        dieser Seite. Labels stehen in Anteilen des Zuschnitts und bleiben gültig, der Körper rechnet neu.
        Geht eine Seite mit den neuen Maßen nicht in die Box, bleibt alles, wie es war."""
        neu = {**b, **masse}
        plaene = {}
        for n, s in b["seiten"].items():
            p = s.get("plan")
            if s["fotos"] and p and not p.get("frei"):
                plaene[n] = l.plan_anpassen(p, neu, n, [int(i) for i in s["fotos"]])
        b |= masse
        for n, p in plaene.items():
            s, alt = b["seiten"][n], b["seiten"][n]["plan"]
            voll_alt = alt.get("voll_mm") or alt["laengs_mm"]
            s["plan"] = p
            for f in s["fotos"].values():
                if f.get("breite_px"):
                    f["px_je_mm"] = round(l.px_je_mm(max(f["breite_px"], f["hoehe_px"]), p["voll_mm"]), 2)
            for g in s.get("geloescht", {}).values():
                if g.get("plan") == alt:
                    g["plan"] = p                # Rückgängig beim Foto-Papierkorb geht weiter
            for km in b.get("kontrollen", []):
                if km["seite"] == n:
                    km["foto_mm"] = round(km["foto_mm"] * p["voll_mm"] / voll_alt, 1)
                    km["abweichung"] = round((km["foto_mm"] / km["zollstock_mm"] - 1) * 100, 2)

    def papierkorb(self) -> Path:
        return self.ordner / "papierkorb"

    def balken_weg(self, daten: dict) -> dict:
        """Balken mit allem (Fotos, Zuschnitte, Labels, Körper) nach papierkorb/<ID>/ legen, nicht löschen. Der Teil
        in teile.json bleibt stehen, so kommt er beim Zurückholen in dieselbe Gruppe. IDs werden nie neu vergeben."""
        with self.schloss:
            b = self.lesen(daten.get("balken"))
            if self.auftrag and self.auftrag["balken"] == b["id"]:
                raise Konflikt("Es wird gerade ausgelöst.")
            if self.kette.lauf and self.kette.lauf["status"] in k.LAUFEND:
                raise Konflikt("Es läuft ein Training. Danach löschen.")
            ziel = self.papierkorb() / b["id"]
            if ziel.exists():                     # alter Rest gleicher ID: beiseite, nichts überschreiben
                ziel.rename(ziel.with_name(f"{b['id']}-{datetime.now():%Y%m%d-%H%M%S}"))
            ziel.parent.mkdir(exist_ok=True)
            (self.ordner / b["id"]).rename(ziel)
            return {"weg": b["id"]}

    def balken_zurueck(self, daten: dict) -> dict:
        kennung = daten.get("balken")
        if not isinstance(kennung, str) or not re.fullmatch(r"B\d{3,6}", kennung):
            raise ValueError("Unbekannter Balken.")
        with self.schloss:
            quelle, ziel = self.papierkorb() / kennung, self.ordner / kennung
            if not (quelle / "balken.json").exists():
                raise ValueError("Diesen Balken gibt es im Papierkorb nicht.")
            if ziel.exists():
                raise ValueError(f"{kennung} gibt es schon.")
            quelle.rename(ziel)
            return self.mit_plan(self.lesen(kennung))

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
        """Gilt für alle Seiten ohne Fotos. Die Originale bleiben ganz, der Ausschnitt steht im Plan der Seite.
        Mit bildfeld_mm [längs, quer] statt eines Rechtecks: Größe von Hand, gerechnet auf der Seite balken/seite."""
        with self.schloss:
            if "bildfeld_mm" in daten:
                b = self.mit_plan(self.lesen(daten.get("balken")))
                s = self.seite(b, daten.get("seite"))
                if s["fotos"] or not s["plan"] or not s["plan"].get("voll_mm"):
                    raise ValueError("Das Bildfeld lässt sich nur auf einer Seite ohne Fotos ändern.")
                werte = daten["bildfeld_mm"]
                if not isinstance(werte, list) or len(werte) != 2:
                    raise ValueError("Bildfeld nicht lesbar.")
                self.einst["zuschnitt"] = l.zuschnitt_aus_mass(self.einst["zuschnitt"], s["plan"]["voll_mm"], *werte)
            else:
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
            faktor = l.faktor_aus_messung(anteil, strecke, s["plan"]["abstand_mm"])
            self.einst["faktor"], self.einst["faktor_gemessen"] = faktor, True
            self.sichern()
            # Fotos dieses Balkens gelten ab jetzt mit dem gemessenen Maßstab (Labeln rechnet mit dem Plan der Seite)
            for andere in b["seiten"].values():
                if andere["fotos"] and andere["plan"] and andere["plan"]["faktor"] != faktor:
                    andere["plan"] = l.neu_skalieren(andere["plan"], faktor)
                    for f in andere["fotos"].values():
                        if f.get("breite_px"):
                            f["px_je_mm"] = round(l.px_je_mm(max(f["breite_px"], f["hoehe_px"]),
                                                             andere["plan"].get("voll_mm") or andere["plan"]["laengs_mm"]), 2)
            self.ablegen(b)
        return self.stand()

    def kontrolle(self, daten: dict) -> dict:
        """Prüfmessung an einem Foto speichern (Strecke im Foto gegen Zollstock), mit weg=True die letzte zurücknehmen.
        Der Maßstab bleibt dabei, wie er ist."""
        with self.schloss:
            b = self.lesen(daten.get("balken"))
            liste = b.setdefault("kontrollen", [])
            if daten.get("weg"):
                if not liste:
                    raise ValueError("Es gibt keine Prüfmessung zum Zurücknehmen.")
                liste.pop()
            else:
                seite = daten.get("seite")
                s = self.seite(b, seite)
                nr = str(daten.get("nr"))
                if nr not in s["fotos"]:
                    raise ValueError("Zu diesem Abschnitt gibt es kein Foto.")
                p = s["plan"]
                k = l.kontrolle(daten.get("anteil"), p.get("voll_mm") or p["laengs_mm"],
                                l.zahl(daten, "zollstock_mm", 1, 2000, "Zollstock"))
                liste.append({"seite": seite, "foto": s["fotos"][nr]["datei"], **k,
                              "zeit": datetime.now().isoformat(timespec="seconds")})
            self.ablegen(b)
            return self.mit_plan(b)

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
            if self.ist_frei(daten):
                b = self.frei_weg(daten, "mac")
                return {"balken": self.mit_plan(b)}
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
            if self.ist_frei(daten):
                return {"balken": self.mit_plan(self.frei_zurueck(daten))}
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

    # ---------------------------------------------------------- Servermodus
    def stand_server(self, nutzer: str) -> dict:
        """Für die Seite Hochladen: Balken mit Maßen und Fotos je Seite, dazu wer man ist und was man darf."""
        with self.schloss:
            balken = []
            for i in self.ids():
                b = self.lesen(i)
                seiten = {}
                for n in l.SEITEN:
                    s = b["seiten"].get(n) or {"fotos": {}, "plan": None}
                    seiten[n] = {"frei": not s["fotos"] or bool((s.get("plan") or {}).get("frei")),
                                 "fotos": [{"nr": int(nr), "datei": f["datei"], "von": f.get("von"), "zeit": f.get("zeit")}
                                           for nr, f in sorted(s["fotos"].items(), key=lambda x: int(x[0]))]}
                balken.append({"id": i, "laenge_mm": b["laenge_mm"], "breite_mm": b["breite_mm"],
                               "hoehe_mm": b["hoehe_mm"], "holzart": b.get("holzart", ""), "von": b.get("von"),
                               "seiten": seiten})
            return {"ich": nutzer, "verwalten": z.darf(nutzer, z.VERWALTEN), "balken": balken}

    def hochladen(self, kennung, seite, daten: bytes, von: str) -> dict:
        """Foto als nächstes Bild einer Seite ablegen. Seiten mit Fotobox-Fotos bleiben, wie sie sind."""
        endung = l.endung_von(daten)
        if endung == ".heic":
            raise ValueError("HEIC geht hier nicht. Am iPhone: Einstellungen > Kamera > Formate > Maximale Kompatibilität.")
        with self.schloss:
            b = self.lesen(kennung)
            s = self.seite(b, seite)
            if s["fotos"] and not (s.get("plan") or {}).get("frei"):
                raise ValueError("Diese Seite ist mit der Fotobox aufgenommen. Eine andere Seite wählen.")
            s["plan"] = freier_plan()
            nr = max((int(n) for n in s["fotos"]), default=-1) + 1
            jetzt = datetime.now()
            name = f"{kennung}_S{seite}_{nr + 1:02d}_hoch_{jetzt.strftime('%Y%m%d-%H%M%S-%f')[:-3]}{endung}"
            (self.ordner / kennung).mkdir(exist_ok=True)
            (self.ordner / kennung / name).write_bytes(daten)
            s["fotos"][str(nr)] = {"datei": name, "vorschau": name, "zeit": jetzt.isoformat(timespec="seconds"),
                                   "mitte_mm": None, "mb": round(len(daten) / 1e6, 1), "breite_px": None,
                                   "hoehe_px": None, "px_je_mm": None, "kamera": {}, "von": von, "quelle": "hochgeladen"}
            self.ablegen(b)
            return self.stand_server(von)

    def ist_frei(self, daten: dict) -> bool:
        s = self.seite(self.lesen(daten.get("balken")), daten.get("seite"))
        return bool((s.get("plan") or {}).get("frei"))

    def frei_weg(self, daten: dict, von: str) -> dict:
        """Hochgeladenes Foto nach verworfen/ legen. Labels bleiben liegen und zählen wieder nach dem Zurückholen."""
        b = self.lesen(daten.get("balken"))
        s = self.seite(b, daten.get("seite"))
        nr = str(daten.get("nr"))
        if not (s.get("plan") or {}).get("frei"):
            raise ValueError("Fotobox-Fotos werden auf dem Mac verwaltet.")
        foto = s["fotos"].pop(nr, None)
        if foto is None:
            raise ValueError("Hier gibt es kein Foto.")
        s.setdefault("geloescht", {})[nr] = {"foto": foto, "von": von,
                                             "zeit": datetime.now().isoformat(timespec="seconds")}
        ordner = self.ordner / b["id"]
        self.verschieben(foto, ordner, ordner / "verworfen")
        self.ablegen(b)
        return b

    def frei_zurueck(self, daten: dict) -> dict:
        """Verworfenes hochgeladenes Foto an seinen Platz zurück (gleiche Nummer, gleiche Labels)."""
        b = self.lesen(daten.get("balken"))
        s = self.seite(b, daten.get("seite"))
        nr = str(daten.get("nr"))
        alt = s.get("geloescht", {}).get(nr)
        if alt is None:
            raise ValueError("Nichts zum Zurückholen.")
        if nr in s["fotos"]:
            raise ValueError("Hier gibt es schon ein neues Foto.")
        if s["fotos"] and not (s.get("plan") or {}).get("frei"):
            raise ValueError("Die Seite ist inzwischen mit der Fotobox aufgenommen.")
        ordner = self.ordner / b["id"]
        if not (ordner / "verworfen" / alt["foto"]["datei"]).exists():
            raise ValueError("Das Foto liegt nicht mehr im Papierkorb.")
        del s["geloescht"][nr]
        s["plan"] = s.get("plan") or freier_plan()
        s["fotos"][nr] = alt["foto"]
        self.verschieben(alt["foto"], ordner / "verworfen", ordner)
        self.ablegen(b)
        return b

    def foto_weg(self, daten: dict, von: str) -> dict:
        """Servermodus: hochgeladenes Foto verwerfen (alle mit Recht verwalten)."""
        with self.schloss:
            self.frei_weg(daten, von)
            return self.stand_server(von)

    def foto_zurueck(self, daten: dict, von: str) -> dict:
        with self.schloss:
            self.frei_zurueck(daten)
            return self.stand_server(von)

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


def abgleich_runter(werk: Werk) -> None:
    """Mac: Balken und Labels vom Server holen (neurolign_abgleich.sh runter), wenn eingerichtet."""
    if werk.abgleich:
        try:
            r = subprocess.run(["bash", str(werk.abgleich), "runter"], capture_output=True, text=True,
                               timeout=ABGLEICH_S)
        except (OSError, subprocess.SubprocessError) as e:
            raise ValueError(f"Labels vom Server holen ging nicht: {e}") from e
        if r.returncode:
            letzte = (r.stderr or r.stdout).strip().splitlines()[-1:] or ["ohne Meldung"]
            raise ValueError(f"Labels vom Server holen ging nicht: {letzte[0]}")


def training_starten(werk: Werk, daten: dict) -> dict:
    """Mac: erst die Labels vom Server holen (wenn eingerichtet), dann das Training starten. Scheitert der Abgleich,
    startet nichts: sonst trainiert der Mac auf altem Stand."""
    abgleich_runter(werk)
    return werk.kette.starten(daten)


def vorlabeln_fern(werk: Werk, daten: dict) -> dict:
    """Mac, Auftrag vom Server: Fotos holt der Lauf selbst im Hintergrund (Abgleich), dann rechnet er."""
    return werk.kette.vorlabeln_starten(daten, True, (lambda: abgleich_runter(werk)) if werk.abgleich else None)


def vorlabel_abholen(server, inhalt: bytes) -> bytes:
    """Server: fertige Balken aus dem Stand des Macs in die eigenen Labels einfügen und dem Mac melden. Unter einem
    Schloss, damit Seite und Abholer nichts doppelt einfügen."""
    try:
        stand = json.loads(inhalt)
    except json.JSONDecodeError:
        return inhalt
    lauf = (stand or {}).get("lauf") if isinstance(stand, dict) else None
    if not lauf:
        return inhalt
    with server.abhol_schloss:
        for b, e in lauf.get("balken", {}).items():
            if "ergebnis" not in e:
                continue
            schon = server.abgeholt.get((lauf["id"], b))
            if schon is None:
                try:
                    schon = server.werk.kette.vorlabel_einfuegen(e["ergebnis"], "vorlabel")["neu"]
                except (ValueError, OSError) as x:
                    print(f"Vorlabel {b} nicht eingefügt: {x}", file=sys.stderr)
                    e["status"], e["fehler"] = "fehler", f"Einfügen ging nicht: {x}"
                    del e["ergebnis"]
                    continue
                server.abgeholt[(lauf["id"], b)] = schon
            del e["ergebnis"]
            e["neu"] = schon
            t.weiterreichen("POST", "/api/vorlabeln-ab", json.dumps({"lauf": lauf["id"], "balken": b, "neu": schon}).encode(),
                            server.schluessel, "server", server.mac_port)
    return json.dumps(stand, ensure_ascii=False).encode()


def abholer(server) -> None:
    """Server: solange auf dem Mac ein Vorlabeln läuft, alle 3 s abholen, auch ohne offene Seite. Höchstens einer."""
    with server.abhol_schloss:
        if server.abholt:
            return
        server.abholt = True

    def schleife():
        weg = 0
        try:
            while weg < 100:
                time.sleep(ABHOLEN_S)
                status, inhalt = t.weiterreichen("GET", "/api/vorlabeln", None, server.schluessel, "server",
                                                 server.mac_port)
                if status != 200:
                    weg += 1
                    continue
                weg = 0
                lauf = json.loads(vorlabel_abholen(server, inhalt)).get("lauf")
                if not lauf or lauf["status"] not in k.VLAUFEND:
                    break
        finally:
            server.abholt = False
    threading.Thread(target=schleife, daemon=True).start()


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
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
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

    def nutzer(self) -> str | None:
        return z.nutzer_aus(self.client_address[0], self.headers.get("Host"), self.headers.get("X-Nutzer"),
                            self.server.host)

    def koerper(self, grenze: int = MAX_FOTO) -> bytes:
        if "chunked" in (self.headers.get("Transfer-Encoding") or "").lower():
            teile, gesamt = [], 0
            while True:
                n = int(self.rfile.readline(100).split(b";")[0], 16)
                if n < 0 or (gesamt := gesamt + n) > grenze:
                    raise ValueError("Datei zu groß.")
                teil = self.rfile.read(n)
                self.rfile.readline(100)
                if n == 0:
                    return b"".join(teile)
                if len(teil) != n:
                    raise ValueError("Übertragung abgebrochen.")
                teile.append(teil)
        n = int(self.headers.get("Content-Length") or 0)
        if not 0 <= n <= grenze:
            raise ValueError("Datei zu groß.")
        daten = self.rfile.read(n)
        if len(daten) != n:
            raise ValueError("Übertragung abgebrochen.")
        return daten

    def datei_senden(self, weg: str, werk: Werk) -> None:
        """Seiten, Schrift, Skripte, Fotos und Zuschnitte, gleich in beiden Modi."""
        if z_ := re.fullmatch(r"/zuschnitt/([A-Za-z0-9_-]+?)(_k)?\.jpg", weg):
            try:
                return self.antwort(200, werk.kette.zuschnitt(z_[1], bool(z_[2])).read_bytes(), "image/jpeg")
            except ValueError as e:
                return self.antwort(404, {"fehler": str(e)})
        datei = None
        if weg == "/":
            datei = SEITE / "index.html"
        elif weg in ("/labeln", "/training", "/koerper", "/galerie"):
            datei = SEITE / f"{weg[1:]}.html"
        elif re.fullmatch(r"/[a-z-]+\.(css|js|woff2)", weg):
            datei = SEITE / weg[1:]
        elif re.fullmatch(r"/foto/B\d{3,6}/[A-Za-z0-9_-]+\.(jpg|png|heic)", weg):
            datei = werk.ordner / weg[6:]
        elif kz := re.fullmatch(r"/koerper/(B\d{3,6})/(S[1-4](?:_k)?\.jpg)", weg):
            datei = werk.ordner / kz[1] / "koerper" / kz[2]
        if datei is None or not datei.is_file():
            return self.antwort(404, {"fehler": "Gibt es nicht."})
        return self.antwort(200, datei.read_bytes(), TYPEN[datei.suffix])

    def koerper_senden(self, werk: Werk) -> None:
        try:
            return self.antwort(200, werk.kette.koerper(parse_qs(urlsplit(self.path).query).get("id", [""])[0]))
        except ValueError as e:
            return self.antwort(400, {"fehler": str(e)})
        except Exception as e:                      # Meldung in den Browser statt abgebrochener Verbindung
            traceback.print_exc()
            return self.antwort(500, {"fehler": f"Körper ging nicht: {type(e).__name__}: {e}"})

    def get_server(self, weg: str, werk: Werk) -> None:
        if (ich := self.nutzer()) is None:
            return self.antwort(403, {"fehler": "Nicht angemeldet."})
        if weg == "/api/stand":
            return self.antwort(200, werk.stand(server=True) | {"ich": ich})
        if weg == "/api/galerie":
            return self.antwort(200, werk.kette.galerie())
        if weg == "/api/koerper":
            return self.koerper_senden(werk)
        if weg == "/api/bilder":
            kodytek = parse_qs(urlsplit(self.path).query).get("satz") == ["kodytek"]
            return self.antwort(200, werk.kette.kodytek_bilder() if kodytek else werk.kette.bilder())
        if weg == "/api/klassen":
            return self.antwort(200, werk.kette.klassen_stand(ich))
        if weg == "/api/saetze":                         # Kodytek-Auswahl kommt per neurolign_abgleich.sh hoch
            return self.antwort(200, {"kodytek": len(werk.kette.kodytek())})
        if weg == "/api/training":
            return self.zum_mac("GET", weg, None, ich)
        if weg == "/api/vorlabeln":
            status, inhalt = t.weiterreichen("GET", weg, None, self.server.schluessel, ich, self.server.mac_port)
            if status == 200:
                inhalt = vorlabel_abholen(self.server, inhalt)
                if (json.loads(inhalt).get("lauf") or {}).get("status") in k.VLAUFEND:
                    abholer(self.server)
            return self.antwort(status, inhalt)
        if weg.startswith(("/api/", "/h/")) or weg == "/live.jpg":
            return self.antwort(404, {"fehler": "Gibt es hier nicht."})
        return self.datei_senden(weg, werk)

    def post_server(self, weg: str, query: str, werk: Werk) -> None:
        ich = self.nutzer()
        if ich is None:
            return self.antwort(403, {"fehler": "Nicht angemeldet."})
        if not z.herkunft_ok(self.headers.get("Origin"), self.headers.get("Referer"), f"https://{self.server.host}") \
                or self.headers.get("X-Aufnahme") != "1":
            return self.antwort(403, {"fehler": "Fremde Herkunft."})
        if nein := z.post_erlaubt(ich, weg):
            return self.antwort(nein[0], {"fehler": nein[1]})
        if weg == "/api/teil":                       # gilt auf dem Mac (Training), die Galerie hier zeigt es auch
            koerper = self.koerper(1_000_000)
            status, inhalt = t.weiterreichen("POST", weg, koerper, self.server.schluessel, ich, self.server.mac_port)
            if status == 200:
                try:
                    werk.kette.teil_setzen(json.loads(koerper))
                except ValueError as e:              # Balken nur auf dem Mac: dort gilt es trotzdem
                    print(f"Teil nur auf dem Mac gesetzt: {e}", file=sys.stderr)
            return self.antwort(status, inhalt)
        if weg in ("/api/training", "/api/abbrechen", "/api/vorlabeln-abbrechen"):
            return self.zum_mac("POST", weg, self.koerper(1_000_000), ich)
        if weg == "/api/vorlabeln":
            koerper = self.koerper(1_000_000)
            status, inhalt = t.weiterreichen("GET", weg, None, self.server.schluessel, ich, self.server.mac_port)
            if status == 200:
                vorlabel_abholen(self.server, inhalt)      # Rest des letzten Laufs zuerst
            status, inhalt = t.weiterreichen("POST", weg, koerper, self.server.schluessel, ich, self.server.mac_port)
            if status == 200:
                abholer(self.server)
            return self.antwort(status, inhalt)
        if weg == "/api/hochladen":
            q = {k: v[0] for k, v in parse_qs(query).items()}
            return self.antwort(200, werk.hochladen(q.get("balken"), q.get("seite"), self.koerper(MAX_HOCHLADEN), ich))
        if weg == "/api/datei":
            q = {k: v[0] for k, v in parse_qs(query).items()}
            return self.antwort(200, {"balken": werk.foto_ablegen(q.get("balken"), q.get("seite"),
                                                                   int(q.get("nr", "-1")), self.koerper())})
        daten = json.loads(self.koerper(1_000_000))
        if not isinstance(daten, dict):
            raise ValueError("Eingabe nicht lesbar.")
        if weg == "/api/balken":
            if daten.get("id") and not z.darf(ich, z.VERWALTEN):
                raise ValueError("Maße ändern nicht erlaubt.")
            return self.antwort(200, werk.balken_speichern(daten, ich))
        if weg == "/api/label":
            return self.antwort(200, werk.kette.speichern(daten, ich))
        if weg == "/api/klassen":
            return self.antwort(200, werk.kette.klassen_aendern(daten, ich))
        if weg == "/api/foto-massstab":
            return self.antwort(200, werk.kette.foto_massstab(daten, ich))
        if weg == "/api/foto-zurueck":
            return self.antwort(200, werk.foto_zurueck(daten, ich))
        if weg == "/api/foto-weg":
            return self.antwort(200, werk.foto_weg(daten, ich))
        return self.antwort(200, mac_wege(werk)[weg](daten))       # übrige Wege wie am Mac (zugang.POST_WEGE)

    def zum_mac(self, methode: str, weg: str, koerper: bytes | None, ich: str) -> None:
        """Servermodus: Trainingsweg durch den Tunnel an den Mac. Start dauert länger (Abgleich der Labels)."""
        zeit = ABGLEICH_S + 60 if (methode, weg) == ("POST", "/api/training") else 15
        status, inhalt = t.weiterreichen(methode, weg, koerper, self.server.schluessel, ich, self.server.mac_port, zeit)
        return self.antwort(status, inhalt)

    def tunnel_anfrage(self, methode: str) -> None:
        """Mac: schmaler Eingang für den Tunnel. Nur Trainingswege, nur mit Schlüssel."""
        weg, werk = urlsplit(self.path).path, self.server.werk
        if not t.erlaubt(methode, weg, self.headers.get(t.KOPF), self.server.schluessel):
            return self.antwort(403, {"fehler": "Nicht erlaubt."})
        try:
            if methode == "GET":
                return self.antwort(200, werk.kette.vorlabeln_stand(True) if weg == "/api/vorlabeln"
                                    else werk.kette.stand())
            daten = json.loads(self.koerper(1_000_000))
            if not isinstance(daten, dict):
                raise ValueError("Eingabe nicht lesbar.")
            tun = {"/api/training": lambda d: training_starten(werk, d), "/api/abbrechen": werk.kette.abbrechen,
                   "/api/teil": werk.kette.teil_setzen, "/api/vorlabeln": lambda d: vorlabeln_fern(werk, d),
                   "/api/vorlabeln-ab": werk.kette.vorlabeln_ab,
                   "/api/vorlabeln-abbrechen": werk.kette.vorlabeln_abbrechen}[weg]
            return self.antwort(200, tun(daten))
        except (ValueError, json.JSONDecodeError) as e:
            return self.antwort(400, {"fehler": str(e)})
        except OSError as e:
            print(f"Fehler: {e}", file=sys.stderr)
            return self.antwort(500, {"fehler": f"Speichern ging nicht: {e}"})

    def do_GET(self):
        weg = urlsplit(self.path).path
        werk = self.server.werk
        if self.server.nur_tunnel:
            return self.tunnel_anfrage("GET")
        if self.server.modus_server:
            return self.get_server(weg, werk)
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
        if weg == "/api/klassen":
            return self.antwort(200, werk.kette.klassen_stand())
        if weg == "/api/training":
            return self.antwort(200, werk.kette.stand())
        if weg == "/api/vorlabeln":
            return self.antwort(200, werk.kette.vorlabeln_stand())
        if weg == "/api/galerie":
            return self.antwort(200, werk.kette.galerie())
        if weg == "/api/koerper":
            return self.koerper_senden(werk)
        if weg == "/live.jpg":
            werk.raster = l.raster_fuers_handy({k: v[0] for k, v in parse_qs(urlsplit(self.path).query).items()})
        if weg == "/live.jpg" and werk.app_da():
            return self.antwort(200, werk.live, "image/jpeg")
        return self.datei_senden(weg, werk)

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
        if self.server.nur_tunnel:
            return self.tunnel_anfrage("POST")
        try:
            if self.server.modus_server:
                return self.post_server(weg, teile.query, werk)
            if weg.startswith("/h/"):
                was, kennung = self.handy_weg(weg), self.headers.get("X-Auftrag")
                if was == "foto":
                    werk.foto_vom_handy(self.koerper(), kennung, self.headers.get("X-Foto", ""))
                elif was == "live":
                    werk.live_vom_handy(self.koerper(), self.headers.get("X-Zustand", ""))
                    return self.antwort(200, {"ok": True, "raster": werk.raster})
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
            wege = mac_wege(werk) | {"/api/label": werk.kette.speichern, "/api/klassen": werk.kette.klassen_aendern,
                                    "/api/foto-massstab": werk.kette.foto_massstab, "/api/teil": werk.kette.teil_setzen,
                                    "/api/training": lambda d: training_starten(werk, d), "/api/abbrechen": werk.kette.abbrechen,
                                    "/api/vorlabeln": werk.kette.vorlabeln_starten,
                                    "/api/vorlabeln-abbrechen": werk.kette.vorlabeln_abbrechen}
            if weg not in wege:
                return self.antwort(404, {"fehler": "Gibt es nicht."})
            daten = json.loads(roh)
            if not isinstance(daten, dict):
                raise ValueError("Eingabe nicht lesbar.")
            return self.antwort(200, wege[weg](daten))
        except Konflikt as e:
            return self.antwort(409, {"fehler": str(e)})
        except (ValueError, json.JSONDecodeError) as e:
            return self.antwort(400, {"fehler": str(e)})
        except OSError as e:
            print(f"Fehler: {e}", file=sys.stderr)
            return self.antwort(500, {"fehler": f"Speichern ging nicht: {e}"})


def mac_wege(werk: Werk) -> dict:
    """POST-Wege der Aufnahme und Galerie, gleich auf dem Mac und auf dem Server (Jan 26.11.2026: die Domain ist ein
    Klon der Mac-Oberfläche). Auslösen und Kamera antworten auf dem Server mit „iPhone nicht verbunden“."""
    return {"/api/balken": werk.balken_speichern, "/api/vorschub": werk.vorschub, "/api/ausloesen": werk.ausloesen,
            "/api/einstellungen": werk.einstellen, "/api/massstab": werk.massstab, "/api/kontrolle": werk.kontrolle,
            "/api/kamera": werk.kamera, "/api/zuschnitt": werk.zuschneiden, "/api/loeschen": werk.loeschen,
            "/api/zurueck": werk.zurueckholen, "/api/balken-weg": werk.balken_weg,
            "/api/balken-zurueck": werk.balken_zurueck}


class Server(ThreadingHTTPServer):
    daemon_threads = True
    modus_server = nur_tunnel = False
    schluessel: str | None = None
    mac_port = t.SERVER_PORT
    abholt = False

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.abhol_schloss = threading.Lock()
        self.abgeholt: dict = {}                 # (Lauf, Balken) -> neue Objekte, schon eingefügt


def server_bauen(ordner: Path, adresse: str, port: int, modus_server: bool = False, python: Path | None = None,
                 host: str = z.HOST, schluessel: str | None = None, mac_port: int = t.SERVER_PORT) -> Server:
    server = Server((adresse, port), Anfrage)
    server.modus_server, server.host, server.schluessel, server.mac_port = modus_server, host, schluessel, mac_port
    server.werk = Werk(ordner, python)
    server.werk.port = server.server_address[1]
    if modus_server and server.werk.einst["letzte_nr"] < ERSTE_SERVER_NR:
        # Balken vom Server ab B501, die Fotobox auf dem Mac zählt ab B001: gleiche ID heißt nie zwei Balken
        server.werk.einst["letzte_nr"] = ERSTE_SERVER_NR
        server.werk.sichern()
    return server


def tunnel_eingang_bauen(werk: Werk, port: int, schluessel: str) -> Server:
    """Mac: zweiter Eingang nur auf 127.0.0.1 für den Tunnel vom Server, gleiche Ablage und gleiches Training."""
    eingang = Server(("127.0.0.1", port), Anfrage)
    eingang.nur_tunnel, eingang.schluessel, eingang.werk = True, schluessel, werk
    return eingang


def main() -> None:
    a = argparse.ArgumentParser(description="Neurolign: Aufnahme, Labeln, Training")
    a.add_argument("ordner", nargs="?", help="Ablage (Mac-Modus), Vorgabe ~/fehlstellenscan/aufnahmen")
    a.add_argument("--server", action="store_true", help="Servermodus hinter Caddy, nur 127.0.0.1")
    a.add_argument("--port", type=int)
    a.add_argument("--python", help="Python mit Pillow und opencv für den Zuschnitt")
    a.add_argument("--env", help=f".env mit {t.SCHLUESSEL_NAME} (Server und Mac)")
    a.add_argument("--mac-port", type=int, default=t.SERVER_PORT, help="Server: Ende des Tunnels zum Mac")
    a.add_argument("--tunnel-port", type=int, help="Mac: Eingang für den Tunnel öffnen (Vorgabe aus, sonst 8766)")
    a.add_argument("--abgleich", help="Mac: Abgleichskript, holt vor jedem Training die Labels vom Server")
    a.add_argument("--still", action="store_true", help="Mac: keinen Browser öffnen (Start als Dienst)")
    w = a.parse_args()
    ordner = Path(w.ordner).expanduser() if w.ordner else Path.home() / "fehlstellenscan" / "aufnahmen"
    schluessel = t.schluessel_aus(Path(w.env).expanduser()) if w.env else None
    python = Path(w.python) if w.python else None
    if w.server:
        server = server_bauen(ordner, "127.0.0.1", w.port or 8796, True, python, schluessel=schluessel,
                              mac_port=w.mac_port)
        print(f"Neurolign (Server) auf 127.0.0.1:{server.werk.port}, Ablage {ordner}, Mac über "
              f"127.0.0.1:{w.mac_port}{'' if schluessel else ' (ohne Schlüssel: Training aus)'}", flush=True)
    else:
        server = server_bauen(ordner, "0.0.0.0", w.port or 8765, python=python)
        if w.abgleich:
            server.werk.abgleich = Path(w.abgleich).expanduser()
        print(f"Aufnahme läuft: http://localhost:{server.werk.port}\nFotos: {ordner}\nBeenden mit Strg+C", flush=True)
        if w.tunnel_port:
            if not schluessel:
                sys.exit(f"--tunnel-port braucht {t.SCHLUESSEL_NAME} in --env")
            eingang = tunnel_eingang_bauen(server.werk, w.tunnel_port, schluessel)
            threading.Thread(target=eingang.serve_forever, daemon=True).start()
            print(f"Eingang für den Server: 127.0.0.1:{w.tunnel_port}", flush=True)
        if sys.platform == "darwin" and not w.still:
            subprocess.Popen(["open", f"http://localhost:{server.werk.port}"])
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")


if __name__ == "__main__":
    main()
