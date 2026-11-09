"""Eigene Ansichten einzelner Arten (arten.toml: ansicht = "recherche" | "pruefung" | "karten"), übernommen aus
uni/portal (projekt.py: Recherche, uebungen.py: Ergebnis einer mündlichen Übung). Rein, ohne Netz und ohne
Dateizugriff: app.py liest die Dateien (Pfade aus daten.ansicht des Ergebnisses, geprüft gegen den Agent-Ordner) und
gibt die Inhalte hierher. uni/portal bleibt bis zur Abnahme unverändert; Änderungen dort hier nachziehen.

Lesend: Karten übernehmen und üben bleiben im Portal (braucht fsrs aus uni/.venv), die Seite verlinkt dorthin.
"""

import re
from urllib.parse import quote, urlsplit

PORTAL = "https://uni.meldro.de"  # uni/portal hinter Caddy (uni/STATUS.md)
DOI = re.compile(r"^10\.\d+/\S+$")
FRAGE_ID = re.compile(r"^F\d+$")
MODUL = re.compile(r"^[a-z]+$")
UEBUNG_ID = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{6}$")
FETT = re.compile(r"\*\*(.+?)\*\*")

STATUS = {"gesichert": "gesichert", "teilweise": "teilweise belegt", "einschaetzung": "Einschätzung",
          "unbelegt": "unbelegt", "verworfen": "verworfen"}
RECHERCHE_ANSICHTEN = {"aussagen": "Aussagen", "quellen": "Quellen", "luecken": "Lücken und Widersprüche",
                       "suche": "Literatursuche"}


# --- daten.ansicht prüfen ----------------------------------------------------------------------------------------

def recherche_ordner(ansicht) -> str | None:
    """Ordner der Recherche relativ zum Agent-Ordner aus daten.ansicht ({"recherche": "data/recherchen/..."}).
    Nur unter data/recherchen/, ohne .. und Verstecktes; die App prüft danach noch gegen den Agent-Ordner."""
    pfad = ansicht.get("recherche") if isinstance(ansicht, dict) else None
    if not isinstance(pfad, str):
        return None
    teile = pfad.split("/")
    if teile[:2] != ["data", "recherchen"] or any(not t or t.startswith(".") or t == ".." for t in teile):
        return None
    return pfad


def modul_und_uebung(ansicht) -> tuple[str, str | None] | None:
    """(modul, uebung oder None) aus daten.ansicht, nur bekannte Muster."""
    if not isinstance(ansicht, dict) or not isinstance(ansicht.get("modul"), str) \
            or not MODUL.match(ansicht["modul"]):
        return None
    uebung = ansicht.get("uebung")
    if uebung is not None and (not isinstance(uebung, str) or not UEBUNG_ID.match(uebung)):
        return None
    return ansicht["modul"], uebung


def portal_link(modul: str, uebung: str | None = None) -> str:
    return f"{PORTAL}/modul/{quote(modul)}" + (f"/uebung/{quote(uebung)}" if uebung else "")


# --- Recherche (aus uni/portal/projekt.py) -----------------------------------------------------------------------

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
    datei = str(b.get("datei") or "").rsplit("/", 1)[-1].removesuffix(".txt")  # nur der Name, nie ein Link
    return {"zitat": str(b.get("zitat") or ""), "link": link_oder_none(b.get("url")), "url": str(b.get("url") or ""),
            "datei": datei, "seite": b.get("seite"), "vermerk": str(pruefung.get("vermerk") or ""),
            "bestanden": pruefung.get("status") == "bestanden"}


def _aussage(a: dict) -> dict:
    status = a.get("status")
    return {"id": str(a.get("id") or ""), "text": str(a.get("text") or ""),
            "status": status if status in STATUS else "unbekannt",
            "status_text": STATUS.get(status, str(status or "unbekannt")), "fehlt": str(a.get("fehlt") or ""),
            "belege": [_beleg(b) for b in a.get("belege") or [] if isinstance(b, dict)]}


def recherche_zahlen(geprueft: dict) -> dict:
    zaehler = {s: 0 for s in STATUS}
    for a in geprueft.get("aussagen") or []:
        if isinstance(a, dict) and a.get("status") in zaehler:
            zaehler[a["status"]] += 1
    return zaehler


def aussagen_ansicht(geprueft: dict, status: str | None, frage: str | None) -> dict:
    """Aussagen nach Fragen gruppiert. Filter nur mit bekannten Werten, sonst gilt er als nicht gesetzt."""
    status = status if status in STATUS else None
    fragen = [f for f in geprueft.get("fragen") or [] if isinstance(f, dict)]
    frage = frage if frage and FRAGE_ID.match(frage) and any(f.get("id") == frage for f in fragen) else None
    offen: dict = {}
    for o in geprueft.get("offen") or []:
        if isinstance(o, dict):
            offen.setdefault(o.get("frage"), []).append(str(o.get("warum") or ""))
    gruppen = []
    alle = [a for a in geprueft.get("aussagen") or [] if isinstance(a, dict)]
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
        gruppen.append({"id": "", "frage": "Ohne zugeordnete Frage", "aussagen": ohne, "gesamt": len(ohne),
                        "offen": []})
    return {"gruppen": gruppen, "status": status, "frage": frage,
            "anzahl": sum(len(g["aussagen"]) for g in gruppen)}


def quellen_ansicht(geprueft: dict) -> list[dict]:
    """Zitierfähige Quellen zuerst, dann neueste zuerst."""
    zeilen = []
    for q in geprueft.get("quellen") or []:
        if not isinstance(q, dict):
            continue
        pruefung = q.get("pruefung") if isinstance(q.get("pruefung"), dict) else {}
        jahr = q.get("jahr") if isinstance(q.get("jahr"), int) else None
        zeilen.append({"titel": str(q.get("titel") or q.get("url") or "Ohne Titel"),
                       "autoren": ", ".join(str(a) for a in q.get("autoren") or []), "jahr": jahr,
                       "doi": q.get("doi") if isinstance(q.get("doi"), str) else "", "doi_link": doi_link(q.get("doi")),
                       "link": link_oder_none(q.get("url")), "zitierfaehig": bool(q.get("zitierfaehig")),
                       "vermerk": str(pruefung.get("vermerk") or "")})
    return sorted(zeilen, key=lambda z: (not z["zitierfaehig"], -(z["jahr"] or 0), z["titel"].lower()))


def luecken_ansicht(geprueft: dict) -> dict:
    return {"luecken": [str(e.get("text") or "") for e in geprueft.get("luecken") or [] if isinstance(e, dict)],
            "widersprueche": [{"worum": str(w.get("worum") or ""), "ids": [str(i) for i in w.get("ids") or []]}
                              for w in geprueft.get("widersprueche") or [] if isinstance(w, dict)]}


def suche_ansicht(geprueft: dict) -> dict:
    suche = geprueft.get("literatursuche") if isinstance(geprueft.get("literatursuche"), dict) else {}
    return {"datenbank": str(suche.get("datenbank") or ""), "datum": str(suche.get("datum") or ""),
            "arbeiten": suche.get("arbeiten_ohne_doppelte"),
            "suchen": [s for s in suche.get("suchen") or [] if isinstance(s, dict)]}


def recherche(geprueft: dict, ansicht: str | None, status: str | None, frage: str | None) -> dict:
    """Alles für den Abschnitt Recherche: Reiter, Zahlen und der Inhalt des gewählten Reiters."""
    ansicht = ansicht if ansicht in RECHERCHE_ANSICHTEN else "aussagen"
    inhalt = {"aussagen": lambda: aussagen_ansicht(geprueft, status, frage), "quellen": lambda: quellen_ansicht(geprueft),
              "luecken": lambda: luecken_ansicht(geprueft), "suche": lambda: suche_ansicht(geprueft)}[ansicht]()
    return {"ansicht": ansicht, "ansichten": RECHERCHE_ANSICHTEN, "zahlen": recherche_zahlen(geprueft),
            "status_namen": STATUS, "inhalt": inhalt}


def _inline(zeile: str) -> list[dict]:
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
    """Markdown (Recherchebericht.md) für die Vorlage: Überschriften, Punkte, Absätze; Jinja maskiert den Text."""
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


# --- Mündliche Übung (aus uni/portal/uebungen.py) ----------------------------------------------------------------

def pruefung(auswertung: dict, kartenstand: dict, plan: dict, karten: list) -> dict:
    """Ergebnis einer Übung: Einschätzung, Bewertung je Rubrikpunkt, Lücken nach Thema (wichtigste zuerst),
    vorgeschlagene Karten mit Stand (übernommen oder nicht). Übernehmen geht im Portal."""
    themen = {t.get("id"): t for t in plan.get("themen") or [] if isinstance(t, dict)}
    karten_nach_id = {k.get("id"): k for k in karten if isinstance(k, dict)}
    stand = {"neu": {}, "faellig": {}, **(kartenstand or {})}
    gruppen: dict[str, list] = {}
    for luecke in auswertung.get("luecken") or []:
        if isinstance(luecke, dict):
            gruppen.setdefault(luecke.get("thema"), []).append(luecke)
    luecken = [{"titel": themen.get(i, {}).get("titel", i), "score": themen.get(i, {}).get("score", 0), "eintraege": e}
               for i, e in gruppen.items()]
    neu = [{**v, "titel": themen.get(v.get("thema"), {}).get("titel", v.get("thema")),
            "uebernommen": str(n) in stand["neu"]}
           for n, v in enumerate(auswertung.get("karten_neu") or []) if isinstance(v, dict)]
    faellig = [{**v, "frage": karten_nach_id.get(v.get("karte"), {}).get("frage", v.get("karte")),
                "uebernommen": str(n) in stand["faellig"]}
               for n, v in enumerate(auswertung.get("karten_faellig") or []) if isinstance(v, dict)]
    return {"gesamt": str(auswertung.get("gesamt") or ""),
            "punkte": [p for p in auswertung.get("punkte") or [] if isinstance(p, dict)],
            "luecken": sorted(luecken, key=lambda z: -(z["score"] or 0)), "neu": neu, "faellig": faellig,
            "offen": sum(1 for v in neu + faellig if not v["uebernommen"])}
