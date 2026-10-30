"""Reine Logik der Web-App für Lia, ohne Netz und ohne Dateizugriff, damit sie testbar ist.

heute() baut aus den Warteschlangen einer Instanz (agentkit.auftraege, agentkit.freigabe) die Ansicht
"Heute": wartet auf Lia (offene Entwürfe, neue Ergebnisse), läuft gerade, fertig, hat nicht geklappt.
Begriffe aus Lias Sicht: keine Agentennamen, keine IDs (wie shared/telegram/portal_logik.py).

"Neu" heißt vorerst: in den letzten NEU_STUNDEN fertig geworden. Ob Lia ein Ergebnis gesehen hat, weiß die
App erst mit Konten (Bauschritt 2/3).
"""

import re
from datetime import datetime, timedelta

NEU_STUNDEN = 48
FERTIG_ANZAHL = 10  # so viele fertige Aufträge zeigt "Heute", der Rest kommt später unter "Anfragen"
FEHLGESCHLAGEN = "Das hat leider nicht geklappt. Sag Jan bitte Bescheid."  # wie portal_logik.FEHLGESCHLAGEN

# Art aus Lias Sicht: erst nach quelle (Art im Portal), sonst nach dem zuständigen Agenten
ARTEN_NACH_QUELLE = {"portal-frage": "Frage", "portal-woche": "Woche"}
ARTEN_NACH_AGENT = {"unterricht": "Material", "theater": "Theater", "recherche": "Recherche", "examen": "Examen"}
DATEIARTEN = {".pdf": ("PDF", "PDFs"), ".docx": ("Word-Datei", "Word-Dateien"),
              ".pptx": ("PowerPoint-Datei", "PowerPoint-Dateien"), ".xlsx": ("Excel-Datei", "Excel-Dateien")}
WOCHENTAGE = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")

# Technische Kennungen, die in Auftragstexten stehen können: "(Auftrag 2026...-theater-0baec0)", "Runde runde-2026..."
_AUFTRAG_KLAMMER = re.compile(r"\s*\(Auftrag [^)]*\)")
_RUNDE = re.compile(r":?\s*Runde\s+runde-\d{8}-\d{6}")
_ID = re.compile(r"\b(?:runde-)?\d{8}-\d{6}(?:-[a-z]+-[0-9a-f]{6})?\b")


def ohne_ids(text: str) -> str:
    text = _ID.sub("", _RUNDE.sub("", _AUFTRAG_KLAMMER.sub("", text)))
    return " ".join(text.split()).strip(" :,-")


def kurz(text: str, laenge: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= laenge else text[: laenge - 1].rstrip() + "…"


def zeit_text(zeitpunkt: str | None, jetzt: datetime) -> str:
    """'heute 14:16', 'gestern 12:19', sonst 'Do 29.10.'. Ohne Zeitpunkt leer."""
    if not zeitpunkt:
        return ""
    z = datetime.fromisoformat(zeitpunkt).astimezone(jetzt.tzinfo)
    tage = (jetzt.date() - z.date()).days
    if tage == 0:
        return f"heute {z:%H:%M}"
    if tage == 1:
        return f"gestern {z:%H:%M}"
    return datum_text(z)


def datum_text(z: datetime) -> str:
    return f"{WOCHENTAGE[z.weekday()]} {z:%d.%m.}"


def art(auftrag: dict) -> str:
    return (ARTEN_NACH_QUELLE.get(auftrag.get("quelle") or "")
            or ARTEN_NACH_AGENT.get(auftrag.get("agent") or "") or "Auftrag")


def titel(auftrag: dict, nach_id: dict[str, dict]) -> str:
    """Überschrift eines Auftrags: erste Zeile des Texts ohne IDs, bei Nachbesserung und Feedback der Bezug."""
    bezug = nach_id.get(auftrag.get("bezug") or "")
    bezug_titel = f" zu „{titel(bezug, {})}“" if bezug else ""
    if auftrag.get("agent") == "feedback":
        return "Deine Rückmeldung" + bezug_titel
    text = (auftrag.get("text") or "").strip()
    if auftrag.get("bezug") and text.startswith("Nachbesserung"):
        return "Antwort auf deine Rückmeldung" + bezug_titel
    erste = ohne_ids(text.split("\n", 1)[0])
    return kurz(erste[:1].upper() + erste[1:], 80) if erste else art(auftrag)


def dateien_text(pfade: list[str]) -> str:
    """'1 PDF', '4 Word-Dateien', '1 Excel-Datei, 1 PDF'. Unbekannte Endungen zählen als Datei."""
    zaehler: dict[tuple[str, str], int] = {}
    for p in pfade:
        endung = "." + p.rsplit(".", 1)[-1].lower() if "." in p else ""
        name = DATEIARTEN.get(endung, ("Datei", "Dateien"))
        zaehler[name] = zaehler.get(name, 0) + 1
    return ", ".join(f"{n} {einzahl if n == 1 else mehrzahl}" for (einzahl, mehrzahl), n in zaehler.items())


def _zeile(titel_: str, art_: str, zeit: str, marke: str = "", hinweis: str = "") -> dict:
    """Eine Zeile der Ansicht. unter: Art und Zeit, durch Mittelpunkt getrennt."""
    return {"titel": titel_, "unter": " · ".join(x for x in (art_, zeit) if x), "marke": marke, "hinweis": hinweis}


def entwurf_zeile(entwurf: dict, jetzt: datetime) -> dict:
    selbst = entwurf.get("typ") == "entwurf"
    return _zeile(kurz(ohne_ids(entwurf.get("titel") or "Entwurf"), 80), "Entwurf",
                  zeit_text(entwurf.get("erstellt"), jetzt), "Offen",
                  "Setzt du selbst ein" if selbst else "Wartet auf deine Entscheidung")


def ergebnis_zeile(auftrag: dict, nach_id: dict[str, dict], jetzt: datetime, marke: str = "") -> dict:
    return _zeile(titel(auftrag, nach_id), art(auftrag), zeit_text(auftrag.get("abgeschlossen"), jetzt), marke,
                  dateien_text(auftrag.get("ergebnis_dateien") or []))


def ist_neu(auftrag: dict, jetzt: datetime) -> bool:
    fertig = auftrag.get("abgeschlossen")
    return bool(fertig) and jetzt - datetime.fromisoformat(fertig) <= timedelta(hours=NEU_STUNDEN)


def heute(neue: list[dict], erledigte: list[dict], entwuerfe: list[dict], jetzt: datetime,
          person: str = "Lia") -> dict:
    """Ansichtsdaten für "Heute". neue/erledigte: agentkit.auftraege, entwuerfe: agentkit.freigabe.offene()."""
    nach_id = {a["id"]: a for a in [*neue, *erledigte] if "id" in a}
    erledigte = sorted(erledigte, key=lambda a: a.get("abgeschlossen") or "", reverse=True)
    # Feedback-Bestätigungen sind keine Ergebnisse: Was daraus wird, zeigt die Nachbesserung
    ergebnisse = [a for a in erledigte if a.get("status") == "erledigt" and a.get("agent") != "feedback"]
    neu = [a for a in ergebnisse if ist_neu(a, jetzt)]
    wartet = ([entwurf_zeile(e, jetzt) for e in sorted(entwuerfe, key=lambda e: e.get("erstellt") or "",
                                                       reverse=True)]
              + [ergebnis_zeile(a, nach_id, jetzt, "Neu") for a in neu])
    laeuft = [_zeile(titel(a, nach_id), art(a) if a.get("agent") != "feedback" else "Rückmeldung",
                     "seit " + zeit_text(a.get("erstellt"), jetzt) if a.get("erstellt") else "")
              for a in sorted(neue, key=lambda a: a.get("erstellt") or "")]
    rest = [a for a in ergebnisse if a not in neu]
    fehlgeschlagen = [{**_zeile(titel(a, nach_id), art(a), zeit_text(a.get("abgeschlossen"), jetzt)),
                       "grund": kurz(ohne_ids(a.get("ergebnis") or "") or FEHLGESCHLAGEN, 300)}
                      for a in erledigte if a.get("status") == "fehlgeschlagen" and a.get("agent") != "feedback"]
    n = len(wartet)
    return {
        "datum": datum_text(jetzt),
        "begruessung": f"Hallo {person}.",
        "anzahl_wartet": n,
        "wartet_text": ("Gerade wartet nichts auf dich." if n == 0
                        else "Sache wartet auf dich." if n == 1 else "Sachen warten auf dich."),
        "wartet": wartet,
        "laeuft": laeuft,
        "fertig": [ergebnis_zeile(a, nach_id, jetzt) for a in rest[:FERTIG_ANZAHL]],
        "fertig_weitere": max(0, len(rest) - FERTIG_ANZAHL),
        "fehlgeschlagen": fehlgeschlagen,
    }
