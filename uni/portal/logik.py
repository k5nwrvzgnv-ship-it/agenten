"""Reine Logik des Portals, ohne Netz: Formularschutz, Übungssitzung, Ansicht der Prüfungsseite.

Die Sitzung liegt in portal/data/, nicht in data/lernen/sitzung.json: Die gehört lernen.py (Telegram). Gemeinsam
sind nur zustand.json und verlauf.jsonl, geschrieben von lernmodell.Modul.bewerten. Der Ablauf folgt lernen.weiter:
"Nochmal" stellt die Karte am Ende einmal neu.
"""

import hmac
from datetime import datetime
from urllib.parse import urlsplit

import lernmodell


def herkunft_passt(origin: str | None, host: str | None, sec_fetch_site: str | None) -> bool:
    """Kommt ein Formular von dieser Seite? Kopie aus shared/webapp/logik.py (CSRF)."""
    if sec_fetch_site and sec_fetch_site != "same-origin":
        return False
    if not origin or not host or origin == "null":
        return False
    return urlsplit(origin).netloc == host


def formular_token(geheim: bytes) -> str:
    return hmac.new(geheim, b"portal-formular", "sha256").hexdigest()


def token_passt(geheim: bytes, token: str | None) -> bool:
    return bool(token) and hmac.compare_digest(formular_token(geheim), token)


def port_pruefen(wert: str) -> int:
    port = int(wert)
    if not 1024 <= port <= 65535:
        raise ValueError(f"Port außerhalb des Bereichs: {port}")
    return port


def sitzung_holen(s: dict | None, m: lernmodell.Modul, modul: str, jetzt: datetime, vorgemerkt=()) -> dict:
    """Heutige Sitzung fortsetzen oder neu beginnen. Ist die Runde leer, kommt die nächste Auswahl dazu: Wer weiter
    üben will, bekommt alles Fällige, die Grenze für neue Karten pro Tag bleibt (lernmodell.auswahl).
    vorgemerkt: Karten, die Jan aus einer Übungsauswertung bestätigt hat, kommen zuerst."""
    heute = jetzt.date().isoformat()
    if not s or s.get("datum") != heute or s.get("modul") != modul:
        s = {"datum": heute, "modul": modul, "warteschlange": [], "wiederholt": [], "erledigt": 0, "richtig": 0}
    s["warteschlange"] = [i for i in s["warteschlange"] if i in m.karten]  # Karten können neu erzeugt worden sein
    if not s["warteschlange"]:
        s["warteschlange"] = m.auswahl(jetzt)
    vorn = [i for i in vorgemerkt if i in m.karten]
    s["warteschlange"] = vorn + [i for i in s["warteschlange"] if i not in vorn]
    return s


def bewertung_lesen(wert: str | None) -> int | None:
    """Wert eines Knopfes (1 bis 4) oder None."""
    if wert not in {str(b) for b in lernmodell.BEWERTUNGEN.values()}:
        return None
    return int(wert)


def bewertung_anwenden(s: dict, m: lernmodell.Modul, karte_id: str, nr: str | None, bewertung: int,
                       jetzt: datetime) -> bool:
    """Bewertung speichern, wenn sie zur gezeigten Karte gehört. nr ist der Zähler beim Anzeigen: Ein Doppelklick
    oder ein altes Fenster zählt so nicht zweimal, auch nicht bei einer Karte, die nach "Nochmal" wiederkommt."""
    if not s["warteschlange"] or s["warteschlange"][0] != karte_id or nr != str(s["erledigt"]):
        return False
    m.bewerten(karte_id, bewertung, jetzt)
    s["warteschlange"].pop(0)
    s["erledigt"] += 1
    s["richtig"] += bewertung >= lernmodell.RICHTIG_AB
    if bewertung == lernmodell.BEWERTUNGEN["Nochmal"] and karte_id not in s["wiederholt"]:
        s["warteschlange"].append(karte_id)
        s["wiederholt"].append(karte_id)
    return True


def ganzes_bild(bild: str | None) -> str | None:
    """Bildkarten: Zur Frage ohne Beschriftung gehört die ganze Infokarte (karten.py, <name>-frage / <name>-ganz)."""
    if not bild or "-frage." not in bild:
        return None
    return bild.replace("-frage.", "-ganz.")


def themen_ansicht(plan: dict, m: lernmodell.Modul) -> list[dict]:
    """Themen des Prüfungsplans mit Lernstand, wichtigste zuerst."""
    zeilen = []
    for t in plan.get("themen", []):
        karten = [i for i, k in m.karten.items() if k["thema"] == t["id"]]
        zeilen.append({
            "titel": t.get("titel", t["id"]), "teil": t.get("teil", ""), "score": t.get("score", 0),
            "stand": m.status(t["id"]) if karten else "keine Karten",
            "karten": len(karten), "gesehen": sum(1 for i in karten if i in m.zustand),
            "begruendung": t.get("begruendung", ""), "lernziele": t.get("lernziele", []),
            "quellen": t.get("quellen", [])})
    return sorted(zeilen, key=lambda z: -z["score"])


def ueberblick(m: lernmodell.Modul, jetzt: datetime) -> dict:
    return {"karten": len(m.karten), "gesehen": sum(1 for i in m.karten if i in m.zustand),
            "dran": len(m.auswahl(jetzt))}
