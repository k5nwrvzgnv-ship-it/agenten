"""Training vom Server aus, gerechnet auf Jans Mac (Jan 26.11.2026). Nur Bordmittel, läuft auf beiden Seiten.

Der Mac baut einen SSH-Tunnel zum Server auf (mac/neurolign_dienst.sh): Port 8797 auf dem Server führt zu Port 8766
auf dem Mac. Dort hört Neurolign (Mac-Modus) mit einem zweiten, schmalen Eingang, der nur die Trainingswege kennt und
nur Anfragen mit dem gemeinsamen Schlüssel annimmt (NEUROLIGN_TUNNEL_SCHLUESSEL in der .env auf beiden Seiten).
Der Server reicht /api/training, /api/abbrechen, /api/teil und /api/vorlabeln (Vorlabeln, docs/plan-vorlabeln.md)
dorthin weiter. Ist der Mac nicht da, antwortet er 503
mit {"mac": false}."""

import hmac
import http.client
from pathlib import Path

SERVER_PORT = 8797          # auf dem Server, nur 127.0.0.1, Ende des Tunnels
MAC_PORT = 8766             # auf dem Mac, nur 127.0.0.1, schmaler Eingang
SCHLUESSEL_NAME = "NEUROLIGN_TUNNEL_SCHLUESSEL"
KOPF = "X-Tunnel"

# Wege, die durch den Tunnel dürfen: (Methode, Weg)
WEGE = {("GET", "/api/training"), ("POST", "/api/training"), ("POST", "/api/abbrechen"), ("POST", "/api/teil"),
        ("GET", "/api/vorlabeln"), ("POST", "/api/vorlabeln"), ("POST", "/api/vorlabeln-ab"),
        ("POST", "/api/vorlabeln-abbrechen")}


def schluessel_aus(env: Path | None) -> str | None:
    """Schlüssel aus einer .env-Datei (Zeile NAME=wert). None, wenn Datei oder Zeile fehlt oder der Wert zu kurz ist."""
    if env is None or not env.is_file():
        return None
    for zeile in env.read_text(encoding="utf-8").splitlines():
        name, gleich, wert = zeile.strip().partition("=")
        if gleich and name.strip() == SCHLUESSEL_NAME:
            wert = wert.strip().strip("'\"")
            return wert if len(wert) >= 20 else None
    return None


def erlaubt(methode: str, weg: str, kopf: str | None, schluessel: str | None) -> bool:
    """Für den Eingang auf dem Mac: nur bekannte Wege und nur mit dem richtigen Schlüssel."""
    if not schluessel or not kopf or (methode, weg) not in WEGE:
        return False
    return hmac.compare_digest(kopf.encode(), schluessel.encode())


def weiterreichen(methode: str, weg: str, koerper: bytes | None, schluessel: str | None, nutzer: str,
                  port: int = SERVER_PORT, zeit: float = 15) -> tuple[int, bytes]:
    """Anfrage an den Mac weitergeben. (Status, JSON-Körper). Mac nicht erreichbar: 503."""
    if not schluessel:
        return 503, b'{"fehler": "Tunnel zum Mac nicht eingerichtet.", "mac": false}'
    v = http.client.HTTPConnection("127.0.0.1", port, timeout=zeit)
    try:
        v.request(methode, weg, body=koerper, headers={
            "Host": "localhost", KOPF: schluessel, "X-Aufnahme": "1", "X-Nutzer": nutzer,
            "Content-Type": "application/json"})
        a = v.getresponse()
        return a.status, a.read()
    except (OSError, http.client.HTTPException):
        return 503, b'{"fehler": "Mac nicht erreichbar.", "mac": false}'
    finally:
        v.close()
