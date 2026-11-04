"""Forschungsprojekt im Portal: Exposé, Recherche, Protokoll und Schriftverkehr für die Anzeige aufbereiten.

Rein, ohne Netz und ohne Dateizugriff: app.py holt die Dateien über ablage.py und gibt die Inhalte hierher. Der Text wird
im Browser von Jinja maskiert, Links entstehen nur aus https-, http- und DOI-Angaben (link_oder_none, doi_link).
"""

import re
from urllib.parse import quote, urlsplit

OFFEN = re.compile(r"\[OFFEN(?::[^\]]*)?\]")
FETT = re.compile(r"\*\*(.+?)\*\*")
DOI = re.compile(r"^10\.\d+/\S+$")
FRAGE_ID = re.compile(r"^F\d+$")

STATUS = {"gesichert": "gesichert", "teilweise": "teilweise belegt", "einschaetzung": "Einschätzung",
          "unbelegt": "unbelegt", "verworfen": "verworfen"}
ANSICHTEN = {"aussagen": "Aussagen", "quellen": "Quellen", "luecken": "Lücken und Widersprüche", "suche": "Literatursuche"}


def teile(text: str) -> list[dict]:
    """Text in Stücke, [OFFEN: ...] ist markiert: [{"text": ..., "offen": bool}]."""
    text = str(text or "")
    stuecke, pos = [], 0
    for m in OFFEN.finditer(text):
        if m.start() > pos:
            stuecke.append({"text": text[pos:m.start()], "offen": False})
        stuecke.append({"text": m.group(0), "offen": True})
        pos = m.end()
    if pos < len(text):
        stuecke.append({"text": text[pos:], "offen": False})
    return stuecke


def offene_stellen(expose: dict) -> list[dict]:
    """Alle [OFFEN: ...] des Exposés mit dem Abschnitt, in dem sie stehen, in Textreihenfolge."""
    gefunden, abschnitt = [], "Deckblatt"

    def texte(wert):
        if isinstance(wert, str):
            yield wert
        elif isinstance(wert, list):
            for w in wert:
                yield from texte(w)
        elif isinstance(wert, dict):
            for w in wert.values():
                yield from texte(w)

    def sammeln(wert):
        for t in texte(wert):
            for m in OFFEN.findall(t):
                inhalt = m[1:-1].removeprefix("OFFEN").lstrip(": ").strip()
                gefunden.append({"was": inhalt or "ohne Angabe", "abschnitt": abschnitt})

    sammeln({k: v for k, v in expose.items() if k not in ("bloecke", "literatur")})
    for block in expose.get("bloecke") or []:
        if block.get("typ") == "ueberschrift":
            abschnitt = str(block.get("text") or abschnitt)
        sammeln(block)
    abschnitt = "Literatur"
    sammeln(expose.get("literatur") or [])
    return gefunden


def expose_ansicht(expose: dict) -> dict:
    """Blöcke für die Vorlage. Unbekannte Blockarten zählt "ausgelassen", damit die Seite sie nicht still verschluckt."""
    bloecke, ausgelassen = [], 0
    for b in expose.get("bloecke") or []:
        typ = b.get("typ")
        if typ == "ueberschrift":
            bloecke.append({"typ": typ, "ebene": 3 if b.get("ebene") == 2 else 2, "text": str(b.get("text") or "")})
        elif typ == "absatz":
            bloecke.append({"typ": typ, "teile": teile(b.get("text"))})
        elif typ == "liste":
            bloecke.append({"typ": typ, "nummeriert": bool(b.get("nummeriert")), "punkte": [teile(p) for p in b.get("punkte") or []]})
        elif typ == "tabelle":
            bloecke.append({"typ": typ, "titel": str(b.get("titel") or ""), "kopf": [str(k) for k in b.get("kopf") or []],
                            "zeilen": [[teile(z) for z in zeile] for zeile in b.get("zeilen") or []]})
        else:
            ausgelassen += 1
    return {"titel": str(expose.get("titel") or "Exposé"), "untertitel": str(expose.get("untertitel") or ""),
            "autoren": [str(a) for a in expose.get("autoren") or []], "betreuung": [str(a) for a in expose.get("betreuung") or []],
            "datum": str(expose.get("datum") or ""), "bloecke": bloecke, "ausgelassen": ausgelassen,
            "literatur": [teile(q) for q in expose.get("literatur") or []]}


def link_oder_none(url) -> str | None:
    """Nur http und https werden zum Link, alles andere bleibt Text."""
    if not isinstance(url, str) or re.search(r"[\s\"'<>]", url):
        return None
    try:
        teil = urlsplit(url)
    except ValueError:
        return None
    return url if teil.scheme in ("http", "https") and teil.hostname else None


def doi_link(doi) -> str | None:
    return "https://doi.org/" + quote(doi, safe="/:().-_;") if isinstance(doi, str) and DOI.match(doi) else None


def _beleg(b: dict) -> dict:
    pruefung = b.get("pruefung") if isinstance(b.get("pruefung"), dict) else {}
    datei = str(b.get("datei") or "").rsplit("/", 1)[-1].removesuffix(".txt")  # nur der Name, nie ein Link in die Ablage
    return {"zitat": str(b.get("zitat") or ""), "link": link_oder_none(b.get("url")), "url": str(b.get("url") or ""),
            "datei": datei, "seite": b.get("seite"), "vermerk": str(pruefung.get("vermerk") or ""),
            "bestanden": pruefung.get("status") == "bestanden"}


def _aussage(a: dict) -> dict:
    status = a.get("status")
    return {"id": str(a.get("id") or ""), "text": str(a.get("text") or ""), "status": status if status in STATUS else "unbekannt",
            "status_text": STATUS.get(status, str(status or "unbekannt")), "fehlt": str(a.get("fehlt") or ""),
            "belege": [_beleg(b) for b in a.get("belege") or []]}


def recherche_zahlen(geprueft: dict) -> dict:
    """Aussagen je Status, aus den Aussagen selbst gezählt (das Feld zahlen kann älter sein)."""
    zaehler = {s: 0 for s in STATUS}
    for a in geprueft.get("aussagen") or []:
        if a.get("status") in zaehler:
            zaehler[a["status"]] += 1
    return zaehler


def aussagen_ansicht(geprueft: dict, status: str | None, frage: str | None) -> dict:
    """Aussagen nach Fragen gruppiert. Filter nur mit bekannten Werten, sonst gilt er als nicht gesetzt."""
    status = status if status in STATUS else None
    fragen = [f for f in geprueft.get("fragen") or [] if isinstance(f, dict)]
    frage = frage if frage and FRAGE_ID.match(frage) and any(f.get("id") == frage for f in fragen) else None
    offen = {}
    for o in geprueft.get("offen") or []:
        offen.setdefault(o.get("frage"), []).append(str(o.get("warum") or ""))
    gruppen = []
    alle = geprueft.get("aussagen") or []
    for f in fragen:
        if frage and f.get("id") != frage:
            continue
        eigene = [a for a in alle if a.get("frage") == f.get("id")]
        passend = [_aussage(a) for a in eigene if not status or a.get("status") == status]
        if passend or not status:
            gruppen.append({"id": str(f.get("id") or ""), "frage": str(f.get("frage") or ""), "aussagen": passend,
                            "gesamt": len(eigene), "offen": offen.get(f.get("id"), [])})
    bekannt = {f.get("id") for f in fragen}
    ohne = [_aussage(a) for a in alle if a.get("frage") not in bekannt and (not status or a.get("status") == status)]
    if ohne and not frage:
        gruppen.append({"id": "", "frage": "Ohne zugeordnete Frage", "aussagen": ohne, "gesamt": len(ohne), "offen": []})
    return {"gruppen": gruppen, "status": status, "frage": frage,
            "fragen": [{"id": str(f.get("id") or ""), "frage": str(f.get("frage") or "")} for f in fragen],
            "anzahl": sum(len(g["aussagen"]) for g in gruppen)}


def quellen_ansicht(geprueft: dict) -> list[dict]:
    """Zitierfähige Quellen zuerst, dann neueste zuerst."""
    zeilen = []
    for q in geprueft.get("quellen") or []:
        pruefung = q.get("pruefung") if isinstance(q.get("pruefung"), dict) else {}
        jahr = q.get("jahr") if isinstance(q.get("jahr"), int) else None
        zeilen.append({"titel": str(q.get("titel") or q.get("url") or "Ohne Titel"), "autoren": ", ".join(str(a) for a in q.get("autoren") or []),
                       "jahr": jahr, "doi": q.get("doi") if isinstance(q.get("doi"), str) else "", "doi_link": doi_link(q.get("doi")),
                       "link": link_oder_none(q.get("url")), "zitierfaehig": bool(q.get("zitierfaehig")),
                       "bestanden": pruefung.get("status") == "bestanden", "vermerk": str(pruefung.get("vermerk") or "")})
    return sorted(zeilen, key=lambda z: (not z["zitierfaehig"], -(z["jahr"] or 0), z["titel"].lower()))


def luecken_ansicht(geprueft: dict) -> dict:
    return {"luecken": [str(eintrag.get("text") or "") for eintrag in geprueft.get("luecken") or []],
            "widersprueche": [{"worum": str(w.get("worum") or ""), "ids": [str(i) for i in w.get("ids") or []]}
                              for w in geprueft.get("widersprueche") or []]}


def suche_ansicht(geprueft: dict) -> dict:
    suche = geprueft.get("literatursuche") if isinstance(geprueft.get("literatursuche"), dict) else {}
    return {"datenbank": str(suche.get("datenbank") or ""), "datum": str(suche.get("datum") or ""),
            "arbeiten": suche.get("arbeiten_ohne_doppelte"), "suchen": [s for s in suche.get("suchen") or [] if isinstance(s, dict)]}


def _inline(zeile: str) -> list[dict]:
    """Text mit **fett** in Stücke."""
    stuecke, pos = [], 0
    for m in FETT.finditer(zeile):
        if m.start() > pos:
            stuecke.append({"text": zeile[pos:m.start()], "fett": False})
        stuecke.append({"text": m.group(1), "fett": True})
        pos = m.end()
    if pos < len(zeile):
        stuecke.append({"text": zeile[pos:], "fett": False})
    return stuecke


def markdown_bloecke(text: str) -> list[dict]:
    """Protokoll für die Vorlage (nach shared/webapp/logik.py): Überschriften, Punkte, Absätze; mehr braucht es nicht."""
    bloecke: list[dict] = []
    for zeile in (text or "").replace("\r\n", "\n").split("\n"):
        z = zeile.strip()
        kopf = re.match(r"^(#{1,6})\s+(.*)$", z)
        punkt = re.match(r"^(?:[-*]|\d+[.)])\s+(.*)$", z)
        if kopf:
            bloecke.append({"art": "kopf", "ebene": min(len(kopf.group(1)) + 1, 3), "text": kopf.group(2)})
        elif punkt:
            if not bloecke or bloecke[-1]["art"] != "punkte":
                bloecke.append({"art": "punkte", "punkte": []})
            bloecke[-1]["punkte"].append(_inline(punkt.group(1)))
        elif z:
            if bloecke and bloecke[-1]["art"] == "absatz" and bloecke[-1]["weiter"]:
                bloecke[-1]["teile"] += [{"text": " ", "fett": False}, *_inline(z)]
            else:
                bloecke.append({"art": "absatz", "teile": _inline(z), "weiter": True})
        elif bloecke and bloecke[-1]["art"] == "absatz":
            bloecke[-1]["weiter"] = False
    return bloecke


def schriftverkehr_ansicht(auszug: dict | None) -> dict:
    """Auszug (uni/schriftverkehr.py) je Kontakt, neueste Mail zuerst. None: Der Agent hat noch nicht abgeglichen."""
    if not auszug:
        return {"da": False, "kontakte": [], "stand": "", "gekappt": False, "anzahl": 0}
    kontakte = []
    mails = [m for m in auszug.get("mails") or [] if isinstance(m, dict)]
    for k in auszug.get("kontakte") or []:
        eigene = [m for m in mails if m.get("kontakt") == k.get("adresse")]
        kontakte.append({"name": str(k.get("name") or k.get("adresse") or ""), "adresse": str(k.get("adresse") or ""),
                         "mails": sorted(eigene, key=lambda m: str(m.get("datum") or ""), reverse=True)})
    return {"da": True, "kontakte": kontakte, "stand": str(auszug.get("stand") or ""), "gekappt": bool(auszug.get("gekappt")),
            "seit": str(auszug.get("seit") or ""), "anzahl": len(mails)}
