"""Verbrauch der claude-Läufe: Protokoll und Stufe.

Jeder Lauf schreibt eine Zeile nach shared/verbrauch/laeufe.jsonl (nicht im Repo).
Die Auslastung (0 bis 1) kommt aus dem rate_limit_event, das claude -p mitliefert:
five_hour = 5-Stunden-Fenster, seven_day = 7-Tage-Fenster des Pro-Kontingents.

Stufen: normal, sparen, nur_auftraege, limit (Grenzen in einstellungen.toml).
"""

import fcntl
import json
import time
from datetime import datetime
from pathlib import Path

from .config import KONTINGENT_DIR

DATEI = KONTINGENT_DIR / "verbrauch" / "laeufe.jsonl"  # gemeinsam für alle Instanzen (ein Konto)
STUFEN = ("normal", "sparen", "nur_auftraege", "limit")


def protokollieren(eintrag: dict, datei: Path | None = None) -> None:
    datei = datei or DATEI
    datei.parent.mkdir(parents=True, exist_ok=True)
    eintrag = {"zeit": time.time(), **eintrag}
    with open(datei, "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")


def _eintraege(datei: Path | None = None) -> list[dict]:
    datei = datei or DATEI
    if not datei.exists():
        return []
    ergebnis = []
    for zeile in datei.read_text(encoding="utf-8").splitlines():
        try:
            ergebnis.append(json.loads(zeile))
        except json.JSONDecodeError:
            continue  # kaputte Zeile (z. B. Absturz beim Schreiben) überspringen
    return ergebnis


def letzter_stand(datei: Path | None = None, jetzt: float | None = None) -> dict | None:
    """Letzte gemeldete Auslastung. Abgelaufene Fenster zählen als 0."""
    jetzt = jetzt or time.time()
    for e in reversed(_eintraege(datei)):
        a = e.get("auslastung")
        if not a:
            continue
        stand = dict(a)
        stand["zeit"] = e.get("zeit")
        for fenster in ("5h", "7d"):
            reset = stand.get(f"reset_{fenster}")
            if reset and reset <= jetzt:
                stand[fenster] = 0.0
        if stand.get("status") != "allowed" and (stand.get("reset_status") or 0) <= jetzt:
            stand["status"] = "allowed"
        return stand
    return None


def gesperrt(status: str | None) -> bool:
    """True, wenn der gemeldete Status ein Limit ist. "allowed_warning" ist nur eine Warnung (wie "allowed"):
    Die Stufen sparen/nur_auftraege greifen dann über die Auslastung 5h/7d."""
    return status not in (None, "allowed", "allowed_warning")


def stufe(stand: dict | None, cfg: dict) -> str:
    if stand is None:
        return "normal"
    if gesperrt(stand.get("status")):
        return "limit"
    s = cfg["stufen"]
    h5, d7 = stand.get("5h", 0) * 100, stand.get("7d", 0) * 100
    if h5 >= s["nur_auftraege_5h"] or d7 >= s["nur_auftraege_7d"]:
        return "nur_auftraege"
    if h5 >= s["sparen_5h"] or d7 >= s["sparen_7d"]:
        return "sparen"
    return "normal"


def auslastung_aus_event(info: dict) -> dict:
    """rate_limit_info aus claude -p in unser Format bringen."""
    fenster = info.get("unifiedWindows", {})
    return {
        "status": info.get("status"),
        "reset_status": info.get("resetsAt"),
        "5h": fenster.get("five_hour", {}).get("utilization", 0) or 0,
        "reset_5h": fenster.get("five_hour", {}).get("resetsAt"),
        "7d": fenster.get("seven_day", {}).get("utilization", 0) or 0,
        "reset_7d": fenster.get("seven_day", {}).get("resetsAt"),
    }


def heute(datei: Path | None = None) -> dict[str, dict]:
    """Läufe von heute pro Agent: Anzahl, Tokens, Minuten, Kosten-Vergleichswert.

    Läufe anderer Instanzen stehen als <instanz>/<agent> (z. B. lia/unterricht).
    """
    beginn = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    summe: dict[str, dict] = {}
    for e in _eintraege(datei):
        if e.get("zeit", 0) < beginn:
            continue
        name = f"{e['instanz']}/{e.get('agent', '?')}" if e.get("instanz") else e.get("agent", "?")
        s = summe.setdefault(name, {"laeufe": 0, "tokens": 0, "minuten": 0.0, "usd": 0.0, "fehler": 0})
        s["laeufe"] += 1
        s["tokens"] += e.get("tokens", 0)
        s["minuten"] += e.get("dauer_s", 0) / 60
        s["usd"] += e.get("usd", 0)
        s["fehler"] += 0 if e.get("ok") else 1
    return summe


def kosten(auftrag_id: str, datei: Path | None = None) -> float | None:
    """Summe der Kosten (USD) aller Läufe zu einem Auftrag, None, wenn kein Lauf protokolliert ist."""
    werte = [e.get("usd") or 0 for e in _eintraege(datei) if e.get("auftrag") == auftrag_id]
    return round(sum(werte), 4) if werte else None


def zeit_text(ts: float | None) -> str:
    return datetime.fromtimestamp(ts).strftime("%d.%m. %H:%M") if ts else "?"
