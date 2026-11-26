"""Wer darf was im Servermodus (neurolign.meldro.de). Reine Logik ohne Netz, getestet in tests/test_zugang.py.

Caddy prüft das Passwort (basicauth je Person) und setzt die Kopfzeile X-Nutzer. Dieser Kopfzeile wird nur
geglaubt, wenn die Anfrage von 127.0.0.1 kommt (Caddy auf demselben Server) und der Host stimmt. Jan, Henri und
Felix dürfen alles, was es im Servermodus gibt, als vollwertige Kollegen (Jan 26.11.2026)."""

from urllib.parse import urlsplit

HOST = "neurolign.meldro.de"
HERKUNFT = f"https://{HOST}"
NUTZER = ("jan", "henri", "felix")

ANSEHEN, HOCHLADEN, LABELN, VERWALTEN = "ansehen", "hochladen", "labeln", "verwalten"
ALLES = frozenset({ANSEHEN, HOCHLADEN, LABELN, VERWALTEN})
RECHTE = {name: ALLES for name in NUTZER}

# POST-Wege im Servermodus und das Recht, das sie brauchen. Alles andere gibt es dort nicht (Fotobox, Training).
POST_WEGE = {
    "/api/balken": HOCHLADEN,
    "/api/hochladen": HOCHLADEN,
    "/api/label": LABELN,
    "/api/foto-weg": VERWALTEN,
}


def host_von(kopf: str | None) -> str:
    kopf = (kopf or "").strip().lower()
    return "" if kopf.startswith("[") else kopf.rsplit(":", 1)[0]


def nutzer_aus(client: str, host: str | None, x_nutzer: str | None, erwarteter_host: str = HOST) -> str | None:
    """Name aus X-Nutzer, nur von 127.0.0.1 mit passendem Host und nur bekannte Namen. Sonst None."""
    if client != "127.0.0.1" or host_von(host) != erwarteter_host:
        return None
    name = (x_nutzer or "").strip().lower()
    return name if name in RECHTE else None


def darf(nutzer: str | None, recht: str) -> bool:
    return nutzer is not None and recht in RECHTE.get(nutzer, set())


def herkunft_ok(origin: str | None, referer: str | None, erwartet: str = HERKUNFT) -> bool:
    """Schutz gegen fremde Seiten, die im Browser der Person POST schicken: Origin muss stimmen; fehlt Origin, dann
    der Referer. Fehlt beides, wird abgelehnt."""
    if origin:
        return origin.rstrip("/") == erwartet
    if referer:
        t = urlsplit(referer)
        return f"{t.scheme}://{t.netloc}" == erwartet
    return False


def post_erlaubt(nutzer: str | None, weg: str) -> tuple[int, str] | None:
    """None, wenn erlaubt, sonst (Status, Text)."""
    recht = POST_WEGE.get(weg)
    if recht is None:
        return 404, "Gibt es hier nicht."
    if not darf(nutzer, recht):
        return 403, "Nicht erlaubt."
    return None
