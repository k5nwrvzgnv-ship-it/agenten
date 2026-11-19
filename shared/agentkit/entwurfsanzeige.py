"""Anzeige eines Entwurfs als Telegram-HTML (Kopf, Inhalt im blockquote, Prüffrage), ohne Telegram.

Genutzt von der Zentrale (shared/telegram) und vom Gruppen-Bot Rüdiger (fehlstellenscan/gruppe_logik.py),
damit Jan einen Entwurf überall gleich sieht.
"""

import email.utils
import re
from datetime import datetime
from html import escape

from agentkit.mail import anhang_zeile

MAX_LAENGE = 3800  # Telegram erlaubt 4096 Zeichen pro Nachricht, etwas Puffer


def anzeigename(agent: str) -> str:
    """'dokumente' -> 'Dokumente', 'lia/recherche' -> 'Recherche (Lia)' (so steht der Absender über der Nachricht)."""
    instanz, _, name = agent.rpartition("/")
    name = name[:1].upper() + name[1:]
    return f"{name} ({instanz[:1].upper()}{instanz[1:]})" if instanz else name


TYP_NAMEN = {"mail": "Mail-Entwurf", "nachricht": "Nachrichten-Entwurf", "kauf": "Kauf-Entwurf",
             "termin": "Termin-Entwurf"}


def _steht_im_inhalt(wert, inhalt: str) -> bool:
    """Steht der Wert (Text oder Liste von Texten) wörtlich, als ganzes Wort, schon im Inhalt?"""
    werte = wert if isinstance(wert, list) else [wert]
    if not all(isinstance(w, str) for w in werte):
        return False  # Zahlen, Objekte usw. immer zeigen
    return all(not w.strip() or re.search(r"(?<!\w)" + re.escape(w.strip()) + r"(?!\w)", inhalt) for w in werte)


DETAIL_NAMEN = {"an": "An", "cc": "Cc", "bcc": "Bcc", "betreff": "Betreff", "text": "Text", "begruendung": "Warum",
                "antwort_auf_uid": "Antwort auf Mail Nr.", "in_reply_to": "Antwort auf"}
TECHNIK = ("in_reply_to", "references", "antwort_auf_uid", "message_id")  # aus der Originalmail, nicht gezeigt
BEZUG = ("antwort_auf", "antwort_auf_von", "antwort_auf_datum")  # nur für die Bezugszeile
WARUM = ("begruendung", "pruefen")
MAIL_KOPF = ("an", "cc", "betreff", "text", "anhaenge")
PRAEFIXE = re.compile(r"^\s*(?:(?:re|aw|antw|wg|fw|fwd|sv)\s*(?:\[\d+\])?\s*:\s*)+", re.IGNORECASE)
WEITERLEITUNG = re.compile(r"^\s*(?:wg|fw|fwd)\b", re.IGNORECASE)
BITTE = re.compile(r"(?:(?<=[.!?])\s+|^)(Bitte prüf\w*\b[^.!?]*[.!?]?)")
BITTE_VORSATZ = re.compile(r"^bitte prüf\w*\b,?\s*", re.IGNORECASE)


def detail_name(schluessel: str) -> str:
    return DETAIL_NAMEN.get(schluessel, schluessel.replace("_", " ").capitalize())


def detail_wert(wert) -> str:
    """Wert eines Entwurfs lesbar: Listen mit Komma, ja/nein, Objekte als „Name: Wert“."""
    if isinstance(wert, bool):
        return "ja" if wert else "nein"
    if isinstance(wert, list):
        return ", ".join(detail_wert(w) for w in wert)
    if isinstance(wert, dict):
        return ", ".join(f"{detail_name(k)}: {detail_wert(w)}" for k, w in wert.items())
    return str(wert)


def _esc(text) -> str:
    return escape(str(text), False)


def betreff_kurz(betreff: str) -> str:
    """'AW: AW: Re: Anfrage' -> 'Re: Anfrage', 'WG: AW: x' -> 'Fwd: x' (nur für die Anzeige)."""
    m = PRAEFIXE.match(betreff or "")
    if not m:
        return (betreff or "").strip()
    return ("Fwd: " if WEITERLEITUNG.match(betreff) else "Re: ") + betreff[m.end():].strip()


def name_aus(von: str) -> tuple[str, str]:
    """'"Oppermann, J." <j@x.de>' -> ('J. Oppermann', 'j@x.de'). Ohne Namen ist der Name die Adresse."""
    name, adresse = email.utils.parseaddr(von or "")
    name = " ".join(name.split())
    if name.count(",") == 1:
        nach, vor = (t.strip() for t in name.split(","))
        name = f"{vor} {nach}".strip()
    return name or adresse or (von or "").strip(), adresse


def _datum(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y")
    except (TypeError, ValueError):
        return ""


def _original(daten: dict) -> tuple[str, str]:
    """(Absender, Betreff) der Mail, auf die geantwortet wird, sonst ('', '')."""
    von = daten.get("antwort_auf_von") or ""
    roh = daten.get("antwort_auf") or ""
    if von and roh.startswith(von + ": "):
        return von, roh[len(von) + 2:]
    if not von and roh:  # ältere Entwürfe: nur "Absender: Betreff"
        trenner = ">: " if ">: " in roh else ": "
        von, _, betreff = roh.partition(trenner)
        return von + (">" if trenner == ">: " else ""), betreff
    return von, ""


def bezug_text(daten: dict) -> str:
    """Kurze Bezugszeile einer Antwort: 'Antwort auf die Mail vom 11.08.2026'. Leer bei neuer Mail."""
    von, original = _original(daten)
    if not von:
        return "Antwort auf eine frühere Mail" if daten.get("in_reply_to") or daten.get("antwort_auf_uid") else ""
    name, adresse = name_aus(von)
    an = [a.lower() for a in daten.get("an") or []]
    text = "Antwort auf die Mail" + ("" if adresse and adresse.lower() in an else f" von {name}")
    if datum := _datum(daten.get("antwort_auf_datum") or ""):
        text += f" vom {datum}"
    kurz_original = betreff_kurz(original)
    if kurz_original and PRAEFIXE.sub("", kurz_original) not in (daten.get("betreff") or ""):
        text += f": „{kurz_original}“"
    return text


def warum_und_frage(daten: dict) -> tuple[str, str]:
    """(Begründung, Prüffrage). Fehlt das Feld pruefen, wird ein Satz „Bitte prüf…“ aus der Begründung gezogen."""
    warum = str(daten.get("begruendung") or "").strip()
    frage = str(daten.get("pruefen") or "").strip()
    if not frage and (m := BITTE.search(warum)):
        frage = m.group(1).strip()
        warum = (warum[:m.start()] + warum[m.end():]).strip()
    return warum, BITTE_VORSATZ.sub("", frage)


def _empfaenger(daten: dict) -> list[str]:
    """'<b>An J. Oppermann</b> (j@x.de)', jede Adresse genau einmal; Namen nur aus der Originalmail."""
    name, adresse = name_aus(_original(daten)[0])
    namen = {adresse.lower(): name} if adresse and name != adresse else {}

    def person(a: str, fett: bool) -> str:
        n = namen.get(a.lower())
        if not fett:
            return f"{_esc(n)} ({_esc(a)})" if n else _esc(a)
        return f"<b>{_esc(n)}</b> ({_esc(a)})" if n else f"<b>{_esc(a)}</b>"

    an = ", ".join(person(a, True) for a in daten["an"])
    zeilen = ["<b>An " + an[len("<b>"):]]
    if daten.get("cc"):
        zeilen.append("Cc: " + ", ".join(person(a, False) for a in daten["cc"]))
    return zeilen


def entwurf_als_text(entwurf: dict) -> list[str]:
    """Entwurf als HTML-Nachricht(en) für die Freigabe. Gerüst für alle Typen: Kopf, Inhalt im blockquote,
    Prüffrage. Pro Typ unterscheidet sich nur der Kopf. Begründung und technische Kopfzeilen (In-Reply-To,
    References) zeigt Telegram nicht (Jan, 28.10.2026), sie bleiben im Entwurf (inhalt, daten).

    Jan sieht alles, was ausgeführt wird: Mails aus den daten (genau das geht raus), andere Typen mit inhalt
    und allen Feldern, die dort nicht schon wörtlich stehen (Jan, 27.10.2026). Lange Inhalte werden auf
    mehrere Nachrichten verteilt (nichts abschneiden). Inhalte werden escaped, Tags nur von hier.
    """
    zusatz = TYP_NAMEN.get(entwurf["typ"], "Entwurf") + (", überarbeitet" if entwurf.get("vorgaenger") else "")
    daten = entwurf.get("daten") or {}
    ist_mail = entwurf["typ"] == "mail" and daten.get("an") and daten.get("text")
    zeilen = [f"<b>{_esc(anzeigename(entwurf['agent']))}</b> · {_esc(zusatz)}"]
    if ist_mail:
        inhalt, bekannt = daten["text"], (*MAIL_KOPF, *BEZUG, *WARUM, *TECHNIK)
        zeilen += _empfaenger(daten)[:1] + [_esc(daten["betreff"])]
        if bezug := bezug_text(daten):
            zeilen.append(f"<i>{_esc(bezug)}</i>")
        zeilen += _empfaenger(daten)[1:]
        zeilen += [f"Anhang: {_esc(anhang_zeile(a))}" for a in daten.get("anhaenge") or []]
    else:
        inhalt, bekannt = entwurf["inhalt"], (*WARUM, *TECHNIK)
        zeilen.append(f"<b>{_esc(entwurf['titel'])}</b>")
    zeilen += [f"{_esc(detail_name(k))}: {_esc(detail_wert(v))}" for k, v in daten.items()
               if k not in bekannt and v not in ("", [], {}, None) and not _steht_im_inhalt(v, inhalt)]
    teile = ["\n".join(zeilen), f"<blockquote>{_esc(inhalt.strip())}</blockquote>"]
    if frage := warum_und_frage(daten)[1]:
        teile.append(f"<b>Bitte prüfen:</b> {_esc(frage)}")
    return html_aufteilen("\n\n".join(teile))


TAG = re.compile(r"<(/?)([a-z]+)[^>]*>")


def _sicherer_schnitt(html: str, platz: int) -> int:
    """Schnittstelle ohne Zeilenende: lieber an einem Leerzeichen, nie in einem Tag oder einer Entität."""
    schnitt = html.rfind(" ", 0, platz)
    schnitt = schnitt if schnitt > platz // 2 else platz
    if html.rfind("<", 0, schnitt) > html.rfind(">", 0, schnitt):
        schnitt = html.rfind("<", 0, schnitt)
    if (amp := html.rfind("&", 0, schnitt)) > html.rfind(";", 0, schnitt) and schnitt - amp < 10:
        schnitt = amp
    return schnitt


def html_aufteilen(html: str, max_laenge: int = MAX_LAENGE) -> list[str]:
    """HTML auf Nachrichten verteilen, ohne ein Tag zu zerschneiden: offene Tags (z. B. blockquote) werden am
    Ende eines Stücks geschlossen und im nächsten wieder geöffnet. Es geht nichts verloren."""
    stuecke, offen, rest = [], [], html.strip()
    while True:
        vorsatz = "".join(t for _, t in offen)
        if len(vorsatz) + len(rest) <= max_laenge:
            stuecke.append(vorsatz + rest)
            return stuecke
        platz = max_laenge - 2 * len(vorsatz) - 100  # Platz für Schließen und Tags, die im Stück aufgehen
        schnitt = rest.rfind("\n", 0, platz)
        if schnitt < platz // 2:  # sonst stünde z. B. der Kopf allein in einer Nachricht
            schnitt = _sicherer_schnitt(rest, platz) or platz
        teil = rest[:schnitt].rstrip("\n")
        for m in TAG.finditer(teil):
            if m.group(1):
                for i in range(len(offen) - 1, -1, -1):
                    if offen[i][0] == m.group(2):
                        del offen[i]
                        break
            else:
                offen.append((m.group(2), m.group(0)))
        stuecke.append(vorsatz + teil + "".join(f"</{name}>" for name, _ in reversed(offen)))
        rest = rest[schnitt:].lstrip("\n ")
