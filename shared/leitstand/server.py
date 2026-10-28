"""Leitstand, Stufe 1: lesende Web-Ansicht der Agenten (Netz, Läufe), Dienst leitstand.

Kein Port: Der Server hört auf einem Unix-Socket in data/ (Ordner nur für User agent), damit andere
Benutzer des Servers (z. B. bot) nicht herankommen. Jan öffnet ihn über einen SSH-Tunnel:
  ssh -N -L 8790:/home/agent/agenten/shared/leitstand/data/leitstand.sock agent@<server>
und dann http://localhost:8790 im Browser.

Nur GET:
  /                       Seite (index.html)
  /api/zustand            Dienste mit Zustand, letzter Lauf, offene/unklare Freigaben, Abo-Auslastung
  /api/laeufe             Läufe der letzten Tage (aus agentkit.ereignis)
  /api/laeufe/<lauf-id>   ein Lauf mit Ereignissen und (bei Jans Instanz) Auftrag
  /api/ereignisse?seit=<id>  neue Ereignisse seit id (die Seite fragt alle 2 s)
Logik in logik.py (getestet), hier nur Dateien, systemctl und HTTP.

Start: .venv/bin/python server.py   (Socket-Pfad änderbar mit LEITSTAND_SOCKET)
"""

import json
import logging
import os
import socketserver
import subprocess
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from agentkit import auftraege, einstellungen, ereignis, freigabe, verbrauch
from agentkit._ablage import AblageFehler

import logik

HIER = Path(__file__).resolve().parent
SOCKET = Path(os.environ.get("LEITSTAND_SOCKET") or HIER / "data" / "leitstand.sock")
UNIT_DIR = Path.home() / ".config" / "systemd" / "user"
TAGE = 3  # so weit zurück zeigen /api/laeufe und die Netz-Ansicht Läufe
logger = logging.getLogger("leitstand")


def lebt(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def unit_namen() -> list[str]:
    # Vorlagen (ausfall@.service) lassen `systemctl show` für alle Units scheitern
    return sorted(p.name for p in UNIT_DIR.glob("*") if p.suffix in (".service", ".timer") and "@" not in p.name)


def units(namen: list[str]) -> dict[str, dict]:
    if not namen:
        return {}
    p = subprocess.run(["systemctl", "--user", "show", "-p",
                        "Id,ActiveState,SubState,Result,StateChangeTimestamp,NextElapseUSecRealtime", *namen],
                       capture_output=True, text=True, timeout=10)
    if p.returncode != 0:
        logger.warning("systemctl show: %s", p.stderr.strip()[:200])
    return logik.systemctl_lesen(p.stdout)


def alle_laeufe() -> list[dict]:
    return logik.laeufe(ereignis.lesen(tage=TAGE), lebt)


def zustand() -> dict:
    cfg = einstellungen.lade()
    stand = verbrauch.letzter_stand()
    namen = unit_namen()
    return {
        "agenten": logik.agenten(namen, units(namen), alle_laeufe(), freigabe.offene(), freigabe.unklare()),
        "verbrauch": logik.verbrauch_anzeigen(stand, verbrauch.stufe(stand, cfg), cfg.get("konto", {}).get("quelle")),
    }


def lauf(lauf_id: str) -> dict | None:
    gefunden = next((lauf for lauf in alle_laeufe() if lauf["id"] == lauf_id), None)
    if gefunden is None:
        return None
    a = None
    if gefunden.get("auftrag") and gefunden.get("instanz") is None:
        try:
            a = auftraege.erledigter(gefunden["auftrag"])
        except (AblageFehler, FileNotFoundError, KeyError):
            a = next((x for x in auftraege.neue() if x["id"] == gefunden["auftrag"]), None)
    return {**gefunden, "auftrag_daten": logik.auftrag_anzeigen(a, gefunden.get("instanz"))}


class Anfrage(BaseHTTPRequestHandler):
    server_version = "Leitstand/1"

    def address_string(self) -> str:
        return "socket"  # Unix-Socket hat keine Adresse

    def log_message(self, format, *args):  # noqa: A002 - Name aus BaseHTTPRequestHandler
        logger.info(format, *args)

    def senden(self, code: int, inhalt: bytes, typ: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(inhalt)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(inhalt)

    def json(self, daten, code: int = 200) -> None:
        self.senden(code, json.dumps(daten, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):  # noqa: N802 - Name aus BaseHTTPRequestHandler
        url = urlparse(self.path)
        try:
            if url.path == "/":
                self.senden(200, (HIER / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/api/zustand":
                self.json(zustand())
            elif url.path == "/api/laeufe":
                self.json([{k: v for k, v in x.items() if k != "ereignisse"} for x in alle_laeufe()])
            elif url.path.startswith("/api/laeufe/"):
                gefunden = lauf(url.path.rsplit("/", 1)[1])
                self.json(gefunden if gefunden else {"fehler": "Lauf nicht gefunden"}, 200 if gefunden else 404)
            elif url.path == "/api/ereignisse":
                seit = parse_qs(url.query).get("seit", [None])[0]
                try:
                    neu = ereignis.lesen(seit=seit, tage=TAGE)
                except ValueError:
                    self.json({"fehler": "seit ungültig"}, 400)
                    return
                self.json(neu[-500:])
            else:
                self.json({"fehler": "unbekannt"}, 404)
        except Exception:
            logger.exception("Fehler bei %s", url.path)
            self.json({"fehler": "Fehler im Leitstand, siehe Log"}, 500)

    def do_POST(self):  # noqa: N802
        self.json({"fehler": "Stufe 1: nur lesen"}, 405)


class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


def starten(socket_pfad: Path = SOCKET) -> Server:
    socket_pfad.parent.mkdir(parents=True, exist_ok=True)
    socket_pfad.parent.chmod(0o700)
    if socket_pfad.exists():
        socket_pfad.unlink()  # Rest eines früheren Laufs
    alt = os.umask(0o077)
    try:
        server = Server(str(socket_pfad), Anfrage)
    finally:
        os.umask(alt)
    return server


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    weg = ereignis.aufraeumen()
    if weg:
        logger.info("Alte Ereignisdateien gelöscht: %s", ", ".join(weg))
    server = starten()
    logger.info("Leitstand hört auf %s", SOCKET)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        SOCKET.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
