"""Lesetest für Moodle und Unipostfach. Liest nur, verändert und verschickt nichts.

Aufruf: .venv/bin/python lesetest.py
- Moodle: Anmeldung wie die Moodle-App (siehe moodle.py), dann Kurse und offene Fristen.
- Mail: IMAP-Anmeldung, Posteingang nur lesend öffnen, ungelesene Mails zählen.
"""

import imaplib
import time
from datetime import datetime
from pathlib import Path

from agentkit import config

import moodle

HIER = Path(__file__).resolve().parent
cfg = config.lade_config(HIER, pflicht=("HNEE_NUTZER", "HNEE_KENNWORT", "MOODLE_URL", "IMAP_HOST"))


def moodle_test() -> None:
    m = moodle.Moodle(cfg)
    info = m.aufruf("core_webservice_get_site_info")
    print(f"Moodle: angemeldet als {info['fullname']} (Moodle {info.get('release', '?')})")
    kurse = m.kurse()
    print(f"\n{len(kurse)} Kurse:")
    for k in kurse:
        print(f"  - {k['fullname']}")
    fristen = m.fristen(int(time.time()))
    print(f"\n{len(fristen)} offene Fristen (Aufgaben und Tests):")
    for f in fristen:
        wann = datetime.fromtimestamp(f["faellig"]).strftime("%d.%m.%Y %H:%M")
        print(f"  - {wann}  {f['kurs']}: {f['name']} ({'abgegeben' if f['erledigt'] else 'offen'})")


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
