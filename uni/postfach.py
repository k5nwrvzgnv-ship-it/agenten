"""Unipostfach (Exchange der HNEE) per IMAP lesen. Nur lesend (Senden: mail.py, nur nach Freigabe).

Das Lesen selbst steckt in agentkit.imap (readonly, BODY.PEEK, Marke für neue Mails).
Hier stehen nur HNEE-Zugang und Stand-Datei data/postfach.json.
Beim ersten Lauf wurden alte Mails nicht nachgeholt (am 16.10.2026 rund 6000 Mails, über 5000 ungelesen).
"""

from pathlib import Path

from agentkit import imap

HIER = Path(__file__).resolve().parent
STAND_DATEI = HIER / "data" / "postfach.json"


def neue_mails(cfg: dict) -> list[dict]:
    """Mails seit dem letzten Aufruf, älteste zuerst (höchstens imap.MAX_MAILS pro Aufruf)."""
    return imap.neue_mails(cfg["IMAP_HOST"], int(cfg.get("IMAP_PORT", 993)),
                           cfg["HNEE_NUTZER"], cfg["HNEE_KENNWORT"], STAND_DATEI)
