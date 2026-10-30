"""Reine Logik der Web-App für Lia, ohne Netz und ohne Dateizugriff, damit sie testbar ist.

heute() baut aus den Warteschlangen einer Instanz (agentkit.auftraege, agentkit.freigabe) die Ansicht
"Heute": wartet auf Lia (offene Entwürfe, neue Ergebnisse), läuft gerade, fertig, hat nicht geklappt.
ergebnis() und entwurf() bauen die Einzelansichten, auf die die Zeilen von "Heute" verlinken.
Begriffe aus Lias Sicht: keine Agentennamen, keine IDs (wie shared/telegram/portal_logik.py). IDs stehen nur
in Links, nie im sichtbaren Text.

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
DATEIKNOEPFE = {".pdf": "PDF", ".docx": "Word", ".pptx": "PowerPoint", ".xlsx": "Excel"}
TITEL_LANG = 300  # Überschrift in der Ergebnis-Ansicht (in "Heute" 80 Zeichen)
WOCHENTAGE = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
# Felder aus daten eines Entwurfs, die Lia sieht. Nur diese: andere (z. B. "datei") sind interne Pfade.
ENTWURF_DETAILS = {"einsatz": "Einsatz"}

# Technische Kennungen, die in Auftragstexten stehen können: "(Auftrag 2026...-theater-0baec0)", "Runde runde-2026..."
_AUFTRAG_KLAMMER = re.compile(r"\s*\(Auftrag [^)]*\)")
_RUNDE = re.compile(r":?\s*Runde\s+runde-\d{8}-\d{6}")
_ID = re.compile(r"\b(?:runde-)?\d{8}-\d{6}(?:-[a-z]+-[0-9a-f]{6})?\b")


def ohne_ids(text: str) -> str:
    text = _ID.sub("", _RUNDE.sub("", _AUFTRAG_KLAMMER.sub("", text)))
    return " ".join(text.split()).strip(" :,-")


def ohne_ids_lang(text: str) -> str:
    """Wie ohne_ids, aber Zeilen und Einrückung bleiben (für ganze Entwürfe)."""
    return _ID.sub("", _RUNDE.sub("", _AUFTRAG_KLAMMER.sub("", text)))


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


def titel(auftrag: dict, nach_id: dict[str, dict], laenge: int = 80) -> str:
    """Überschrift eines Auftrags: erste Zeile des Texts ohne IDs, bei Nachbesserung und Feedback der Bezug."""
    bezug = nach_id.get(auftrag.get("bezug") or "")
    bezug_titel = f" zu „{titel(bezug, {})}“" if bezug else ""
    if auftrag.get("agent") == "feedback":
        return "Deine Rückmeldung" + bezug_titel
    text = (auftrag.get("text") or "").strip()
    if auftrag.get("bezug") and text.startswith("Nachbesserung"):
        return "Antwort auf deine Rückmeldung" + bezug_titel
    erste = ohne_ids(text.split("\n", 1)[0])
    return kurz(erste[:1].upper() + erste[1:], laenge) if erste else art(auftrag)


def dateien_text(pfade: list[str]) -> str:
    """'1 PDF', '4 Word-Dateien', '1 Excel-Datei, 1 PDF'. Unbekannte Endungen zählen als Datei."""
    zaehler: dict[tuple[str, str], int] = {}
    for p in pfade:
        endung = "." + p.rsplit(".", 1)[-1].lower() if "." in p else ""
        name = DATEIARTEN.get(endung, ("Datei", "Dateien"))
        zaehler[name] = zaehler.get(name, 0) + 1
    return ", ".join(f"{n} {einzahl if n == 1 else mehrzahl}" for (einzahl, mehrzahl), n in zaehler.items())


def ergebnis_link(eintrag: dict) -> str:
    return f"/ergebnis/{eintrag['id']}" if eintrag.get("id") else ""


def entwurf_link(eintrag: dict) -> str:
    return f"/entwurf/{eintrag['id']}" if eintrag.get("id") else ""


def _zeile(titel_: str, art_: str, zeit: str, marke: str = "", hinweis: str = "", link: str = "") -> dict:
    """Eine Zeile der Ansicht. unter: Art und Zeit, durch Mittelpunkt getrennt."""
    return {"titel": titel_, "unter": " · ".join(x for x in (art_, zeit) if x), "marke": marke, "hinweis": hinweis,
            "link": link}


def entwurf_hinweis(entwurf: dict) -> str:
    return "Setzt du selbst ein" if entwurf.get("typ") == "entwurf" else "Wartet auf deine Entscheidung"


def entwurf_titel(entwurf: dict) -> str:
    return kurz(ohne_ids(entwurf.get("titel") or "Entwurf"), 80) or "Entwurf"


def entwurf_zeile(entwurf: dict, jetzt: datetime) -> dict:
    return _zeile(entwurf_titel(entwurf), "Entwurf", zeit_text(entwurf.get("erstellt"), jetzt), "Offen",
                  entwurf_hinweis(entwurf), entwurf_link(entwurf))


def ergebnis_zeile(auftrag: dict, nach_id: dict[str, dict], jetzt: datetime, marke: str = "") -> dict:
    return _zeile(titel(auftrag, nach_id), art(auftrag), zeit_text(auftrag.get("abgeschlossen"), jetzt), marke,
                  dateien_text(auftrag.get("ergebnis_dateien") or []), ergebnis_link(auftrag))


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
    fehlgeschlagen = [{**_zeile(titel(a, nach_id), art(a), zeit_text(a.get("abgeschlossen"), jetzt),
                              link=ergebnis_link(a)),
                       "grund": kurz(grund(a), 300)}
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


def grund(auftrag: dict) -> str:
    """Warum ein Auftrag nicht geklappt hat, aus Sicht des Agenten; ohne Angabe der Standardsatz."""
    return ohne_ids(auftrag.get("ergebnis") or "") or FEHLGESCHLAGEN


def zeigbar(auftrag: dict) -> bool:
    """Hat der Auftrag eine Ergebnis-Ansicht? Feedback-Bestätigungen und zurückgezogene nicht."""
    return auftrag.get("agent") != "feedback" and auftrag.get("status") in ("erledigt", "fehlgeschlagen")


def absaetze(text: str) -> list[dict]:
    """Ergebnistext in Blöcke: {"absatz": str} oder {"punkte": [str]} (Zeilen mit "- " am Anfang)."""
    bloecke: list[dict] = []
    for zeile in text.splitlines():
        zeile = zeile.strip()
        if zeile.startswith("- "):
            punkt = ohne_ids(zeile[2:])
            if bloecke and "punkte" in bloecke[-1]:
                bloecke[-1]["punkte"].append(punkt)
            else:
                bloecke.append({"punkte": [punkt]})
        elif zeile:
            bloecke.append({"absatz": ohne_ids(zeile)})
    return bloecke


def datei_name(pfad: str) -> str:
    """Anzeigename einer Ergebnisdatei: Dateiname ohne Ordner und Endung."""
    name = pfad.replace("\\", "/").rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[0] if "." in name else name


def dateien_ansicht(pfade: list[str], vorschauen: list[tuple[bool, bool, int]]) -> list[dict]:
    """Dateien eines Ergebnisses mit Knöpfen. vorschauen[i]: (Datei da, Vorschau-PDF da, Anzahl Vorschauseiten).

    nr ist der Index in ergebnis_dateien: Die URLs der Downloads tragen nur ihn, nie einen Pfad.
    Fehlende oder unerlaubte Dateien fehlen. Ein PDF-Knopf aus der Vorschau kommt nur dazu, wenn die Datei
    selbst kein PDF ist."""
    ansicht = []
    for nr, (pfad, (da, hat_pdf, seiten)) in enumerate(zip(pfade, vorschauen, strict=True)):
        if not da:
            continue
        endung = "." + pfad.rsplit(".", 1)[-1].lower() if "." in pfad else ""
        knoepfe = []
        if hat_pdf and endung != ".pdf":
            knoepfe.append({"text": "PDF", "pfad": "/pdf"})
        knoepfe.append({"text": DATEIKNOEPFE.get(endung, "Datei"), "pfad": ""})
        ansicht.append({"nr": nr, "name": datei_name(pfad), "knoepfe": knoepfe, "seiten": seiten})
    return ansicht


def ergebnis(auftrag: dict, erledigte: list[dict], vorschauen: list[tuple[bool, bool, int]],
             jetzt: datetime) -> dict:
    """Ansicht eines Ergebnisses. erledigte: alle abgeschlossenen Aufträge der Instanz (für Bezüge)."""
    nach_id = {a["id"]: a for a in erledigte if "id" in a}
    daten = auftrag.get("daten") or {}
    fehlgeschlagen = auftrag.get("status") == "fehlgeschlagen"
    text = auftrag.get("ergebnis") or ""
    if fehlgeschlagen:
        kern, punkte, bloecke = "", [], []
    elif daten.get("kern"):
        kern, punkte, bloecke = ohne_ids(daten["kern"]), [ohne_ids(p) for p in daten.get("punkte") or []], []
    else:
        kern, punkte, bloecke = "", [], absaetze(text)
    bezug = nach_id.get(auftrag.get("bezug") or "")
    # Lias Rückmeldung, aus der diese Nachbesserung entstand (Feedback-Fall nennt die Nachbesserung)
    rueckmeldung = next((ohne_ids(a.get("text") or "") for a in erledigte
                         if a.get("agent") == "feedback" and auftrag.get("id")
                         and (a.get("daten") or {}).get("nachbesserung") == auftrag["id"]), "")
    antworten = sorted((a for a in erledigte if a.get("bezug") == auftrag.get("id") and auftrag.get("id")
                        and zeigbar(a) and a.get("status") == "erledigt"),
                       key=lambda a: a.get("abgeschlossen") or "")
    pfade = [] if fehlgeschlagen else list(auftrag.get("ergebnis_dateien") or [])
    return {
        "titel": titel(auftrag, nach_id, TITEL_LANG),
        "unter": " · ".join(x for x in (art(auftrag), zeit_text(auftrag.get("abgeschlossen"), jetzt)) if x),
        "fehlgeschlagen": fehlgeschlagen,
        "grund": grund(auftrag) if fehlgeschlagen else "",
        "kern": kern,
        "punkte": punkte,
        "bloecke": bloecke,
        "pruefen": "" if fehlgeschlagen else ohne_ids(daten.get("pruefen") or ""),
        "dateien": dateien_ansicht(pfade, vorschauen) if pfade else [],
        "rueckmeldung": rueckmeldung,
        "bezug": ({"titel": titel(bezug, nach_id), "link": ergebnis_link(bezug)}
                  if bezug and zeigbar(bezug) else None),
        "antworten": [{"titel": titel(a, nach_id), "unter": zeit_text(a.get("abgeschlossen"), jetzt),
                       "link": ergebnis_link(a)} for a in antworten],
    }


def entwurf(eintrag: dict, jetzt: datetime) -> dict:
    """Ansicht eines offenen Entwurfs: ganzer Text, Details aus ENTWURF_DETAILS, keine Knöpfe."""
    daten = eintrag.get("daten") or {}
    details = [(name, ohne_ids(str(daten[schluessel]))) for schluessel, name in ENTWURF_DETAILS.items()
               if daten.get(schluessel)]
    return {
        "titel": entwurf_titel(eintrag),
        "unter": " · ".join(x for x in ("Entwurf", zeit_text(eintrag.get("erstellt"), jetzt)) if x),
        "inhalt": ohne_ids_lang(eintrag.get("inhalt") or "").strip("\n"),
        "details": details,
        "hinweis": entwurf_hinweis(eintrag),
    }
