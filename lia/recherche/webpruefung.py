"""Webauftrag: Claudes Ergebnis lesen, Belege prüfen, docx-Beschreibung bauen (ohne Netz).

Grundsatz (Plan „Webrecherche“, Jan 25.10.2026): Claude recherchiert, Python prüft jeden Beleg.
Format von Claudes Ergebnis (ergebnis.json):
  {"abschnitte": [{"titel": "...", "aussagen": [{"text": "...", "belege": [
      {"url": "https://...", "zitat": "wörtlich von der Seite"} | {"register": "<quelle>:<seite>"}]}]}],
   "luecken": ["..."], "rueckfragen": ["..."]}

Beleg prüfen (beleg_pruefen), Ergebnis "bestanden" | "durchgefallen" | "ungeprueft" mit Vermerk:
- URL auf Jans Liste (einstellungen [webfetch] recherche): Seite laden (der Aufrufer gibt seitentext(url)
  mit, agentkit.abruf + html_zu_text), Zitat mit agentkit.wortlaut.steht_in gegen den Seitentext.
- Video- und Mediatheksseiten: nur Existenz und Titel (das Zitat muss im Seitentext stehen, dort steht oben der
  Titel). Länge und Untertitel: nicht geprüft.
- URL nicht auf der Liste: nicht laden, "ungeprueft", Vermerk „Quelle nicht auf der Liste, ungeprüft“.
- Register-Verweis "<quelle>:<seite>": Quelle im Register, verwendbar, mit einer Stelle auf dieser Seite.
Eine Aussage gilt als belegt, wenn mindestens ein Beleg bestanden hat. Sonst kommt sie unter „Nicht belegt“.
"""

import json
from pathlib import Path
from urllib.parse import urlsplit

from agentkit import abruf, wortlaut

MEDIEN = ("youtube.com", "youtu.be", "ardmediathek.de", "zdf.de", "arte.tv", "vimeo.com")
NICHT_AUF_LISTE = "Quelle nicht auf der Liste, ungeprüft"
MEDIEN_VERMERK = "Videoseite: nur Existenz und Titel geprüft; Länge und Untertitel nicht geprüft"


class WebFehler(Exception):
    pass


def lesen(pfad: Path) -> dict:
    """Claudes ergebnis.json, Aufbau geprüft. Fehler: WebFehler mit allen Stellen."""
    try:
        daten = json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise WebFehler(f"{Path(pfad).name} fehlt oder ist kein JSON: {e}") from None
    fehler = []
    if not isinstance(daten, dict) or not isinstance(daten.get("abschnitte"), list):
        raise WebFehler("abschnitte fehlt")
    for i, a in enumerate(daten["abschnitte"]):
        if not isinstance(a, dict) or not _text(a.get("titel")) or not isinstance(a.get("aussagen"), list):
            fehler.append(f"abschnitte[{i}]: titel und aussagen nötig")
            continue
        for j, s in enumerate(a["aussagen"]):
            ort = f"abschnitte[{i}].aussagen[{j}]"
            if not isinstance(s, dict) or not _text(s.get("text")) or not isinstance(s.get("belege", []), list):
                fehler.append(f"{ort}: text nötig, belege als Liste")
                continue
            for k, b in enumerate(s.get("belege", [])):
                if not (isinstance(b, dict) and (_text(b.get("register")) or
                                                 (_text(b.get("url")) and _text(b.get("zitat"))))):
                    fehler.append(f"{ort}.belege[{k}]: {{url, zitat}} oder {{register}} nötig")
    for feld in ("luecken", "rueckfragen"):
        if not isinstance(daten.get(feld, []), list) or not all(_text(x) for x in daten.get(feld, [])):
            fehler.append(f"{feld}: Liste von Texten nötig")
    if fehler:
        raise WebFehler("; ".join(fehler))
    daten.setdefault("luecken", [])
    daten.setdefault("rueckfragen", [])
    return daten


def _text(x) -> bool:
    return isinstance(x, str) and bool(x.strip())


def ist_medienseite(url: str) -> bool:
    return abruf.host_erlaubt(urlsplit(url).hostname or "", MEDIEN)


def register_stellen(register: dict[str, dict]) -> dict[str, dict]:
    """{"<quelle>:<seite>": Stelle} aller verwendbaren Quellen (auch jede Seite einer Stelle über zwei Seiten)."""
    aus = {}
    for qid, e in register.items():
        if not e.get("gemeinfreiheit", {}).get("verwendbar"):
            continue
        for s in e.get("stellen", []):
            for seite in s.get("seiten") or [s.get("seite")]:
                aus.setdefault(f"{qid}:{seite}", s)
    return aus


def beleg_pruefen(beleg: dict, domains: list[str], seitentext, stellen: dict[str, dict]) -> dict:
    """{"status", "vermerk"} für einen Beleg. seitentext(url) -> Text oder AbrufFehler."""
    if "register" in beleg:
        if beleg["register"] in stellen:
            return {"status": "bestanden", "vermerk": "Quellenregister (geprüft)"}
        return {"status": "durchgefallen", "vermerk": f"Register-Verweis {beleg['register']} gibt es nicht"}
    url = beleg["url"]
    try:
        abruf.pruefen(url, domains)
    except abruf.AbrufFehler:
        return {"status": "ungeprueft", "vermerk": NICHT_AUF_LISTE}
    try:
        text = seitentext(url)
    except abruf.AbrufFehler as e:
        return {"status": "durchgefallen", "vermerk": f"Seite nicht ladbar: {e}"}
    medien = ist_medienseite(url)
    if wortlaut.steht_in(beleg["zitat"], text):
        return {"status": "bestanden", "vermerk": MEDIEN_VERMERK if medien else "Zitat auf der Seite gefunden"}
    if medien:
        return {"status": "durchgefallen", "vermerk": "Videoseite erreichbar, Titel/Zitat aber nicht auf der Seite"}
    return {"status": "durchgefallen", "vermerk": "Zitat steht nicht wörtlich auf der Seite"}


def pruefen(daten: dict, domains: list[str], seitentext, stellen: dict[str, dict]) -> dict:
    """Prüft alle Belege. Ergebnis: daten mit "pruefung" je Beleg und "belegt" je Aussage, dazu "zahlen"."""
    zahlen = {"aussagen": 0, "belegt": 0, "unbelegt": 0, "bestanden": 0, "durchgefallen": 0, "ungeprueft": 0}
    for a in daten["abschnitte"]:
        for s in a["aussagen"]:
            zahlen["aussagen"] += 1
            for b in s.get("belege", []):
                b["pruefung"] = beleg_pruefen(b, domains, seitentext, stellen)
                zahlen[b["pruefung"]["status"]] += 1
            s["belegt"] = any(b["pruefung"]["status"] == "bestanden" for b in s.get("belege", []))
            zahlen["belegt" if s["belegt"] else "unbelegt"] += 1
    daten["zahlen"] = zahlen
    return daten


def durchgefallene(daten: dict) -> list[str]:
    """Liste für die Nachbesserung: je durchgefallenem Beleg Ort, Beleg und Grund."""
    aus = []
    for i, a in enumerate(daten["abschnitte"]):
        for j, s in enumerate(a["aussagen"]):
            for k, b in enumerate(s.get("belege", [])):
                if b.get("pruefung", {}).get("status") == "durchgefallen":
                    was = b.get("register") or f"{b['url']} | Zitat: {b['zitat']!r}"
                    aus.append(f"abschnitte[{i}].aussagen[{j}].belege[{k}] ({s['text'][:80]}): {was} -> "
                               f"{b['pruefung']['vermerk']}")
    return aus


def _quelle_text(b: dict, register: dict[str, dict]) -> str:
    if "register" in b:
        qid, _, seite = b["register"].partition(":")
        e = register.get(qid, {})
        teile = [e.get("autor", ""), e.get("werk", qid), e.get("ausgabe", ""), f"S. {seite}"]
        text = ", ".join(t for t in teile if t)
        if any(s.get("am_scan_pruefen") for s in e.get("stellen", [])):
            text += " (Abschrift vom Scan, am Scan prüfen)"
        return text
    return f"{b['url']} ({b['pruefung']['vermerk']})"


def _bloecke_liste(punkte: list[str], nummeriert: bool = False) -> list[dict]:
    """Renderer erlaubt höchstens 50 Punkte je Liste und 5000 Zeichen je Punkt."""
    punkte = [p[:4900] for p in punkte]
    return [{"typ": "liste", "punkte": punkte[i:i + 50], "nummeriert": nummeriert} for i in range(0, len(punkte), 50)]


def _traegt_satz(daten: dict) -> str:
    z = daten.get("traegt_zahlen")
    if not z:
        return ""
    return (f" Zusätzlich geprüft, ob die Zitate die Tatsachenaussagen tragen (Einschätzungen nicht): {z['ja']} ja, "
            f"{z['teilweise']} teilweise, {z['nein']} nein, {z['nicht_geprueft']} nicht geprüft.")


def beschreibung(titel: str, daten: dict, register: dict[str, dict]) -> dict:
    """Renderer-Beschreibung (Art arbeitsblatt): Abschnitte mit Quellennummern, Quellen, Nicht belegt,
    Lücken, Rückfragen. Belegt sind nur Aussagen mit mindestens einem bestandenen Beleg."""
    quellen, nummer = [], {}

    def nr(b: dict) -> int:
        schluessel = b.get("register") or (b["url"], b["zitat"])
        if schluessel not in nummer:
            quellen.append(b)
            nummer[schluessel] = len(quellen)
        return nummer[schluessel]

    z = daten["zahlen"]
    bloecke = [{"typ": "absatz", "text": (
        f"Automatisch recherchiert, von Python geprüft. {z['belegt']} von {z['aussagen']} Aussagen belegt. "
        f"Belege: {z['bestanden']} bestanden, {z['durchgefallen']} durchgefallen, {z['ungeprueft']} ungeprüft "
        "(Quelle nicht auf der Liste). In eckigen Klammern: Nummern der bestandenen Belege, siehe Quellen."
        + _traegt_satz(daten))}]
    nicht_belegt = []
    for a in daten["abschnitte"]:
        belegte = [s for s in a["aussagen"] if s["belegt"]]
        nicht_belegt += [(a["titel"], s) for s in a["aussagen"] if not s["belegt"]]
        if not belegte:
            continue
        bloecke.append({"typ": "ueberschrift", "text": a["titel"][:200], "ebene": 2})
        for s in belegte:
            gut = sorted({nr(b) for b in s["belege"] if b["pruefung"]["status"] == "bestanden"})
            offen = sorted({nr(b) for b in s["belege"] if b["pruefung"]["status"] == "ungeprueft"})
            klammer = ", ".join(map(str, gut)) + (f"; ungeprüft: {', '.join(map(str, offen))}" if offen else "")
            urteil = s.get("traegt", {})
            if urteil.get("traegt") == "teilweise":
                klammer += f"; Detail nicht belegt: {urteil.get('fehlt') or 'nicht genannt'}"
            elif urteil.get("traegt") == "nicht geprüft":
                klammer += "; ob das Zitat die Aussage trägt: nicht geprüft"
            bloecke.append({"typ": "absatz", "text": f"{s['text']} [{klammer}]"[:5000]})
    if nicht_belegt:
        bloecke.append({"typ": "ueberschrift", "text": "Nicht belegt", "ebene": 1})
        bloecke.append({"typ": "absatz", "text": "Diese Aussagen hatten keinen bestandenen Beleg. Nicht verwenden, "
                                                  "ohne sie selbst zu prüfen."})
        punkte = []
        for t, s in nicht_belegt:
            gruende = "; ".join(f"{b.get('register') or b['url']}: {b['pruefung']['vermerk']}" for b in s.get("belege", []))
            if s.get("traegt", {}).get("traegt") == "nein":
                gruende = f"Zitat trägt die Aussage nicht: {s['traegt'].get('fehlt') or 'ohne Angabe'}; " + gruende
            punkte.append(f"{t}: {s['text']} (Belege: {gruende or 'keine'})")
        bloecke += _bloecke_liste(punkte)
    if quellen:
        bloecke.append({"typ": "ueberschrift", "text": "Quellen", "ebene": 1})
        bloecke += _bloecke_liste([_quelle_text(b, register) for b in quellen], nummeriert=True)
    for feld, kopf in (("luecken", "Lücken"), ("rueckfragen", "Rückfragen")):
        if daten.get(feld):
            bloecke.append({"typ": "ueberschrift", "text": kopf, "ebene": 1})
            bloecke += _bloecke_liste(daten[feld])
    return {"art": "arbeitsblatt", "titel": titel[:200], "nummer": "R", "bloecke": bloecke[:200]}
