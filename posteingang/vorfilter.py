"""Vorfilter ohne Claude: Newsletter, Massenmails, Spam und gesperrte Absender fallen weg.

Rein, ohne Netz. Eingabe sind Mails aus agentkit.imap (dict). Die Kopfzeilen stehen in mail["kopf"]
(Namen klein geschrieben). Fehlt "kopf", wird nur der Absender geprüft.

Befund 27.10.2026 (letzte 200 Mails INBOX, 40 Junk): All-Inkl verschiebt Spam selbst nach Junk und
setzt X-Spam-Flag: YES, ohne Betreff-Präfix. In INBOX trugen 22 von 200 List-Unsubscribe, 1 Precedence: bulk.

Gesperrte Absender kommen aus den Regeln (regeln.md bzw. "Gelernte Regeln"), eine Zeile der Form
    - 27.10.2026: Absender weglassen: info@shop.de, @newsletter.example.com
"@domain" trifft die Domain und ihre Subdomains, sonst muss die Adresse genau stimmen.
"""

import email.utils
import re

MASSEN_PRECEDENCE = {"bulk", "list", "junk"}
REGEL_ABSENDER = re.compile(r"Absender weglassen:\s*(.+?)(\s*\((Anlass|Feedback)\b.*)?$", re.I)


def gesperrte_absender(regelzeilen: list[str]) -> list[str]:
    """Adressen und @Domains aus Regelzeilen "Absender weglassen: ...", klein geschrieben."""
    muster = []
    for zeile in regelzeilen:
        if m := REGEL_ABSENDER.search(zeile):
            muster += [t.strip().lower() for t in m.group(1).split(",") if "@" in t]
    return muster


def absender_gesperrt(von: str, muster: list[str]) -> bool:
    adresse = email.utils.parseaddr(von)[1].lower()
    if "@" not in adresse:
        return False
    domain = adresse.rsplit("@", 1)[1]
    for m in muster:
        if m.startswith("@"):
            if domain == m[1:] or domain.endswith("." + m[1:]):
                return True
        elif adresse == m:
            return True
    return False


def grund_weglassen(mail: dict, muster: list[str]) -> str | None:
    """Warum die Mail ohne Claude wegfällt, oder None, wenn Claude sie einordnen soll."""
    kopf = mail.get("kopf", {})
    if kopf.get("x-spam-flag", "").strip().upper() == "YES":
        return "spam"
    if absender_gesperrt(mail.get("von", ""), muster):
        return "absender"
    if kopf.get("list-unsubscribe", "").strip():
        return "newsletter"
    if kopf.get("precedence", "").strip().lower() in MASSEN_PRECEDENCE:
        return "massenmail"
    return None


def vorfiltern(mails: list[dict], muster: list[str]) -> tuple[list[dict], list[tuple[dict, str]]]:
    """Teilt in (für Claude, [(weggelassen, grund)]). Reihenfolge bleibt erhalten."""
    behalten, weg = [], []
    for mail in mails:
        if grund := grund_weglassen(mail, muster):
            weg.append((mail, grund))
        else:
            behalten.append(mail)
    return behalten, weg
