"""Aufträge mit Art aus dem Arbeitsplatz (docs/arbeitsplatz-plan.md, Schnittstellen).

uni nimmt diese Arten gezielt an, ohne den Auftragstext zu deuten:
- recherche: Research-Bericht, die geprüfte Recherche aus recherche.py ohne Exposé (zweck "bericht"),
- expose: wie "Exposé: ..." aus Telegram (Recherche, Exposé, docx und PDF),
- lernkarten: karten.py für ein Modul mit Prüfungsplan,
- pruefung: Auswertung eines Transkripts der mündlichen Übung über den vorhandenen Weg des Portals
  (portal/auswertung_agent.auswerten, Agent uniportal, ohne Werkzeuge).

Hier steht nur Logik ohne Netz und ohne Claude: Felder lesen, Werte prüfen, daten fürs Ergebnis bauen
({"titel", "kern", "punkte", "pruefen"}). Den Ablauf macht agent.art_auftrag. Ohne art bleibt alles wie bisher.
"""

import re

ARTEN = ("recherche", "expose", "lernkarten", "pruefung")
# Nachbesserung (Rückmeldung in derselben Kette) gibt es bisher nur fürs Exposé, die anderen brauchen einen neuen Auftrag
MIT_NACHBESSERUNG = frozenset({"expose"})

# Research-Bericht: Umfang -> (Kostengrenze USD, höchstens Fragen, höchstens Suchfenster). Geschätzt nach dem ersten
# Exposé (02.11.: 6 Fenster, 24 Fragen, 35 USD), nicht gemessen.
UMFANG = {"kurz": (15.0, 8, 2), "gruendlich": (50.0, 24, 6)}
PUNKTE_MAX = 8
OFFEN = re.compile(r"\[OFFEN:\s*([^\]]*)\]")
UEBUNG_ID = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{6}$")


class ArtFehler(ValueError):
    """Auftrag mit Art nicht ausführbar (Feld fehlt, Wert unbekannt). Der Text geht so an Jan."""


def _norm(text: str) -> str:
    return " ".join(str(text).lower().replace("ü", "ue").replace("ö", "oe").replace("ä", "ae").replace("ß", "ss").split())


def feld(a: dict, *namen: str) -> str:
    """Wert eines Formularfelds (Name ohne Rücksicht auf Groß- und Kleinschreibung, Umlaute), sonst ""."""
    felder = a.get("felder") or {}
    gesucht = {_norm(n) for n in namen}
    for name, wert in felder.items():
        if _norm(name) in gesucht and isinstance(wert, str):
            return wert.strip()
    return ""


def text_mit_feldern(a: dict) -> str:
    """Auftragstext für den Prompt. Die App schreibt die Felder als "Name: Wert" in den Text; fehlt dort eines, kommt
    es hier dazu, damit Claude jedes Feld sieht."""
    text = a.get("text") or ""
    fehlen = [f"{n}: {w}" for n, w in (a.get("felder") or {}).items()
              if isinstance(w, str) and w.strip() and f"{n}: {w}" not in text]
    return "\n".join([text, *fehlen]).strip()


def umfang(wert: str) -> tuple[float, int, int]:
    """Umfang des Research-Berichts. Ohne Angabe kurz (Kosten)."""
    return UMFANG["gruendlich"] if _norm(wert).startswith("gruendlich") else UMFANG["kurz"]


def modul_waehlen(wert: str, module: dict[str, str]) -> str:
    """Modul-Ordner zu einem Feldwert (Ordnername oder Anzeigename). Gibt es nur ein Modul, darf das Feld leer sein."""
    if not wert and len(module) == 1:
        return next(iter(module))
    for ordner, name in module.items():
        if _norm(wert) in (_norm(ordner), _norm(name)):
            return ordner
    bekannt = ", ".join(module.values()) or "keins"
    raise ArtFehler(f"Modul {wert!r} unbekannt. Möglich: {bekannt}." if wert else f"Modul fehlt. Möglich: {bekannt}.")


def themen_waehlen(wert: str, themen: list[dict]) -> set[str] | None:
    """Themen-IDs zu einer Liste (Komma oder Zeile) aus IDs oder Teilen des Titels. Leer: None (alle)."""
    teile = [t.strip() for t in re.split(r"[,;\n]", wert or "") if t.strip()]
    if not teile:
        return None
    gewaehlt = set()
    for teil in teile:
        treffer = [t["id"] for t in themen if _norm(teil) in (_norm(t["id"]), _norm(t.get("titel", "")))
                   or _norm(teil) in _norm(t.get("titel", ""))]
        if not treffer:
            raise ArtFehler(f"Thema {teil!r} steht nicht im Prüfungsplan.")
        gewaehlt.update(treffer)
    return gewaehlt


def score_waehlen(wert: str) -> int:
    """Mindest-Score 1 bis 5 aus dem Feld (erste Ziffer), ohne Angabe 4 wie karten.py."""
    ziffer = re.search(r"[1-5]", wert or "")
    return int(ziffer.group()) if ziffer else 4


def uebung_id(auftrag_id: str) -> str:
    """Feste ID der Übung aus der Auftrags-ID (Format des Portals): Ein neuer Anlauf trifft dieselbe Übung."""
    teile = auftrag_id.split("-")
    kandidat = f"{teile[0]}-{teile[1]}-{teile[-1]}" if len(teile) >= 4 else ""
    if not UEBUNG_ID.match(kandidat):
        raise ArtFehler(f"Auftrags-ID {auftrag_id!r} passt nicht zum Format der Übungen")
    return kandidat


def _kurz(text: str, n: int = 300) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def daten_recherche(g: dict) -> dict:
    """daten zu geprueft.json eines Research-Berichts."""
    z = g["zahlen"]
    gesichert = [a for a in g["aussagen"] if a["status"] == "gesichert"]
    pruefen = (f"{z['teilweise']} Aussagen nur teilweise belegt, {z['unbelegt']} unbelegt, {len(g['luecken'])} Lücken, "
               f"{len(g['widersprueche'])} Widersprüche: im Bericht nachsehen.")
    return {"titel": _kurz(f"Recherche: {g['thema']}", 200),
            "kern": (f"{len(g['fragen'])} Fragen, {len(g['aussagen'])} Aussagen, davon {z['gesichert']} gesichert; "
                     f"{z['quellen_zitierfaehig']} zitierfähige Quellen."),
            "punkte": [_kurz(a["text"]) for a in gesichert[:PUNKTE_MAX]],
            "pruefen": pruefen}


def _texte(d: dict) -> list[str]:
    texte = []
    for b in d.get("bloecke", []):
        texte += [b.get("text", ""), b.get("titel", "")] + list(b.get("punkte", [])) + list(b.get("kopf", []))
        texte += [z for zeile in b.get("zeilen", []) for z in zeile]
    return [t for t in texte if isinstance(t, str)]


def daten_expose(d: dict | None) -> dict:
    """daten zu expose.json. Ohne gültiges Exposé nur ein Hinweis."""
    if not d:
        return {"titel": "Exposé", "kern": "Es liegt noch kein gültiges Exposé vor.", "punkte": [],
                "pruefen": "Ergebnistext lesen: dort steht, was fehlt."}
    offen = [m.strip() for t in _texte(d) for m in OFFEN.findall(t)]
    gliederung = [b["text"] for b in d.get("bloecke", []) if b.get("typ") == "ueberschrift" and b.get("ebene", 1) == 1]
    pruefen = ("Offene Stellen: " + "; ".join(_kurz(o, 120) for o in offen[:5])
               + (f" (und {len(offen) - 5} weitere)" if len(offen) > 5 else "")) if offen else \
        "Keine [OFFEN]-Stellen. Literatur und Deckblatt prüfen."
    return {"titel": _kurz(d.get("titel") or "Exposé", 200),
            "kern": f"Exposé mit {len(gliederung)} Abschnitten, {len(d.get('literatur', []))} Literaturangaben, "
                    f"{len(offen)} offenen Stellen.",
            "punkte": [_kurz(g, 200) for g in gliederung[:PUNKTE_MAX]],
            "pruefen": pruefen}


def daten_karten(modul_name: str, r: dict, themen: set[str] | None) -> dict:
    """daten zu karten.erzeugen_ergebnis."""
    neu = r["neu"]
    auswahl = f" ({', '.join(sorted(themen))})" if themen else ""
    pruefen = "Antworten und Quellen der neuen Karten beim ersten Üben gegenlesen."
    if r["fehler"]:
        pruefen += f" {len(r['fehler'])} Entwürfe verworfen: " + "; ".join(_kurz(f, 120) for f in r["fehler"][:3])
    return {"titel": f"Lernkarten {modul_name}{auswahl}",
            "kern": f"{len(neu)} neue Karten für {modul_name}" + ("." if neu else ", keine neue Karte übernommen."),
            "punkte": [_kurz(k["frage"], 200) for k in neu[:PUNKTE_MAX]],
            "pruefen": pruefen}


def daten_pruefung(modul_name: str, auswertung: dict, stufen: dict[str, str], titel: str,
                   rubrik_bestaetigt: bool) -> dict:
    """daten zur Auswertung einer mündlichen Übung (Format portal/bewertung.pruefen)."""
    punkte = [_kurz(f"{p['id']}: {stufen.get(p['stufe'], p['stufe'])}. {p.get('begruendung', '')}", 250)
              for p in auswertung.get("punkte", [])]
    pruefen = (f"{len(auswertung.get('luecken', []))} Lücken, {len(auswertung.get('karten_neu', []))} vorgeschlagene "
               f"neue Karten, {len(auswertung.get('karten_faellig', []))} zum Wiederholen: in der Prüfungsansicht "
               "übernehmen.")
    if not rubrik_bestaetigt:
        pruefen += " Die Rubrik ist noch nicht bestätigt, die Stufen sind vorläufig."
    return {"titel": _kurz(titel or f"Mündliche Übung {modul_name}", 200),
            "kern": _kurz(auswertung.get("gesamt", ""), 500),
            "punkte": punkte[:PUNKTE_MAX + 4],  # die Rubrik hat bis zu 10 Punkte, alle sollen sichtbar sein
            "pruefen": pruefen}
