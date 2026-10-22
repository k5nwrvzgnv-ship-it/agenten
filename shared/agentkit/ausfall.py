"""Meldung an Jan, wenn ein systemd-Dienst fehlschlägt.

Jede Unit trägt `OnFailure=ausfall@%n.service`. systemd startet dann
`python3 -m agentkit.ausfall <unit>` (Dienstvorlage shared/systemd/ausfall@.service).

- Schickt direkt über die Telegram-Schnittstelle (nur Bordmittel, Token aus shared/.env), damit
  die Meldung auch ankommt, wenn die Zentrale selbst ausgefallen ist. Linkvorschau aus.
- Klappt das nicht, landet die Meldung in shared/meldungen/, die Zentrale schickt sie später.
- Pro Unit höchstens eine Meldung in SPERRE_S (Stand in shared/ausfall/stand.json), damit ein
  Dienst mit Timer alle 15 Minuten nicht jedes Mal meldet.
- Kurz und ohne Technik (Jan 22.10.): "Störung" fett, welcher Dienst, Grund in Worten. Journal-Zeilen
  stehen nicht in der Meldung, die liest ein Chat am Server (journalctl --user -u <unit>).

Grenze: Dienste mit Restart=on-failure (agentenzentrale) gelten erst als fehlgeschlagen, wenn
systemd das Neustarten aufgibt. Einzelne Abstürze mit erfolgreichem Neustart meldet das nicht.
"""

import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from html import escape
from pathlib import Path

from . import _ablage, meldungen
from .config import SHARED_DIR, lies_env

STAND = SHARED_DIR / "ausfall" / "stand.json"
SPERRE_S = 6 * 3600
GRUENDE = {
    "oom-kill": "zu wenig Arbeitsspeicher",
    "timeout": "hat zu lange gebraucht",
    "exit-code": "mit einem Fehler beendet",
    "signal": "abgebrochen",
    "core-dump": "abgestürzt",
    "watchdog": "reagiert nicht mehr",
    "start-limit-hit": "startet immer wieder neu und wurde angehalten",
    "resources": "konnte nicht starten",
}


def agent_aus_unit(unit: str) -> str:
    """'uni-transkript.service' -> 'uni', 'agentenzentrale.service' -> 'agentenzentrale'."""
    name = unit.split(".", 1)[0].split("-", 1)[0].split("@", 1)[0]
    return name if _ablage.AGENT_MUSTER.match(name) else "ausfall"


def darf_melden(stand: dict, unit: str, jetzt: float, sperre_s: float = SPERRE_S) -> bool:
    return unit not in stand or jetzt - stand[unit] >= sperre_s


def text(unit: str, ergebnis: str) -> str:
    """'uni-transkript.service', 'oom-kill' -> 'Uni-transkript ist ausgefallen: zu wenig Arbeitsspeicher. ...'"""
    name = unit.split(".", 1)[0]
    grund = GRUENDE.get(ergebnis, f"Grund unbekannt ({ergebnis})" if ergebnis else "Grund unbekannt")
    return (f"{name[:1].upper()}{name[1:]} ist ausgefallen: {grund}.\n"
            f"Ich melde mich dazu frühestens in {SPERRE_S // 3600} Stunden wieder.")


def _befehl(*args: str) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError) as f:
        return f"({args[0]} nicht lesbar: {f})"


def _lies_stand(datei: Path) -> dict:
    try:
        return json.loads(datei.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def telegram_senden(token: str, chat_id: str, nachricht: str) -> None:
    daten = urllib.parse.urlencode({"chat_id": chat_id, "text": nachricht, "parse_mode": "HTML",
                                    "disable_web_page_preview": "true"}).encode()
    with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", daten, timeout=20) as r:
        if not json.loads(r.read()).get("ok"):
            raise OSError("Telegram hat die Nachricht nicht angenommen")


def melden(unit: str, jetzt: float | None = None, stand_datei: Path | None = None,
           senden=telegram_senden, env: dict | None = None) -> str:
    """Meldet den Ausfall einer Unit. Gibt zurück, was passiert ist (für Log und Tests)."""
    jetzt = jetzt or time.time()
    stand_datei = stand_datei or STAND
    stand = _lies_stand(stand_datei)
    if not darf_melden(stand, unit, jetzt):
        return "gesperrt"
    env = lies_env(SHARED_DIR / ".env") if env is None else env
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    ergebnis = _befehl("systemctl", "--user", "show", "-p", "Result", "--value", unit)
    nachricht = text(unit, ergebnis)
    try:
        senden(token, env.get("TELEGRAM_CHAT_ID", ""), "<b>Störung</b>\n" + escape(nachricht, False))
        weg = "telegram"
    except Exception as f:  # noqa: BLE001 – dann eben über die Zentrale
        grund = str(f).replace(token, "<token>") if token else str(f)
        print(f"Direktversand fehlgeschlagen: {type(f).__name__}: {grund}", file=sys.stderr)  # landet im Journal
        meldungen.melden(agent_aus_unit(unit), nachricht)
        weg = "warteschlange"
    stand[unit] = jetzt
    stand_datei.parent.mkdir(parents=True, exist_ok=True)
    tmp = stand_datei.with_suffix(".tmp")
    tmp.write_text(json.dumps(stand, indent=1), encoding="utf-8")
    tmp.replace(stand_datei)
    return weg


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Aufruf: python3 -m agentkit.ausfall <unit>")
    print(melden(sys.argv[1]))
