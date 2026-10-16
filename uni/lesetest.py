"""Lesetest für Moodle und Unipostfach. Liest nur, verändert und verschickt nichts.

Aufruf: .venv/bin/python lesetest.py
- Moodle: Anmeldung wie die Moodle-App (login/token.php), dann Kurse und anstehende Termine.
  Der Schlüssel wird in data/moodle_token.json (chmod 600) gespeichert und wiederverwendet.
- Mail: IMAP-Anmeldung, Posteingang nur lesend öffnen, ungelesene Mails zählen.
"""

import imaplib
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from agentkit import config

HIER = Path(__file__).resolve().parent
TOKEN_DATEI = HIER / "data" / "moodle_token.json"
cfg = config.lade_config(HIER, pflicht=("HNEE_NUTZER", "HNEE_KENNWORT", "MOODLE_URL", "IMAP_HOST"))


def _post(url: str, daten: dict) -> object:
    anfrage = urllib.request.Request(url, data=urllib.parse.urlencode(daten).encode())
    with urllib.request.urlopen(anfrage, timeout=30) as antwort:
        return json.load(antwort)


def moodle_token() -> str:
    if TOKEN_DATEI.exists():
        return json.loads(TOKEN_DATEI.read_text())["token"]
    antwort = _post(f"{cfg['MOODLE_URL']}/login/token.php", {
        "username": cfg["HNEE_NUTZER"], "password": cfg["HNEE_KENNWORT"], "service": "moodle_mobile_app"})
    if "token" not in antwort:
        raise RuntimeError(f"Moodle-Anmeldung fehlgeschlagen: {antwort.get('error', antwort)}")
    TOKEN_DATEI.parent.mkdir(exist_ok=True)
    fd = os.open(TOKEN_DATEI, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"token": antwort["token"]}, f)
    return antwort["token"]


def moodle(token: str, funktion: str, **parameter) -> object:
    antwort = _post(f"{cfg['MOODLE_URL']}/webservice/rest/server.php",
                    {"wstoken": token, "wsfunction": funktion, "moodlewsrestformat": "json", **parameter})
    if isinstance(antwort, dict) and "exception" in antwort:
        raise RuntimeError(f"{funktion}: {antwort.get('message')}")
    return antwort


def moodle_test() -> None:
    token = moodle_token()
    info = moodle(token, "core_webservice_get_site_info")
    print(f"Moodle: angemeldet als {info['fullname']} (Moodle {info.get('release', '?')})")

    kurse = moodle(token, "core_enrol_get_users_courses", userid=info["userid"])
    print(f"\n{len(kurse)} Kurse:")
    for k in kurse:
        print(f"  - {k['fullname']}")

    jetzt = int(time.time())
    termine = moodle(token, "core_calendar_get_action_events_by_timesort",
                     timesortfrom=jetzt, timesortto=jetzt + 60 * 86400, limitnum=50)["events"]
    print(f"\n{len(termine)} anstehende Termine/Abgaben (60 Tage):")
    for t in termine:
        wann = datetime.fromtimestamp(t["timesort"]).strftime("%a %d.%m. %H:%M")
        print(f"  - {wann}  {t.get('course', {}).get('shortname', '')}: {t['name']}")


def mail_test() -> None:
    with imaplib.IMAP4_SSL(cfg["IMAP_HOST"], int(cfg.get("IMAP_PORT", 993))) as imap:
        imap.login(cfg["HNEE_NUTZER"], cfg["HNEE_KENNWORT"])
        imap.select("INBOX", readonly=True)
        _, gesamt = imap.search(None, "ALL")
        _, ungelesen = imap.search(None, "UNSEEN")
        print(f"\nMail: angemeldet, Posteingang {len(gesamt[0].split())} Mails, "
              f"davon {len(ungelesen[0].split())} ungelesen")


if __name__ == "__main__":
    for name, test in (("Moodle", moodle_test), ("Mail", mail_test)):
        try:
            test()
        except Exception as f:  # noqa: BLE001 – Test soll beide Teile versuchen
            print(f"\n{name}: FEHLER: {f}")
