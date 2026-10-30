"""Reine Logik der Web-App für Lia, ohne Netz und ohne Dateizugriff, damit sie testbar ist.

heute() baut aus den Warteschlangen einer Instanz (agentkit.auftraege, agentkit.freigabe) die Ansicht
"Heute": wartet auf Lia (offene Entwürfe, neue Ergebnisse), läuft gerade, fertig, hat nicht geklappt.
ergebnis() und entwurf() bauen die Einzelansichten, auf die die Zeilen von "Heute" verlinken.
Ein Auftrag mit Feedback-Schleife ist EIN Auftrag: Ursprung, Lias Rückmeldungen (Agent feedback) und die
Nachbesserungen hängen über "bezug" zusammen (ketten()). "Heute" zeigt je Kette eine Zeile, die Ergebnis-Ansicht
die neueste Fassung oben und darunter den Verlauf.
Begriffe aus Lias Sicht: keine Agentennamen, keine IDs (wie shared/telegram/portal_logik.py). IDs stehen nur
in Links, nie im sichtbaren Text.

"Neu" heißt vorerst: in den letzten NEU_STUNDEN fertig geworden. Ob Lia ein Ergebnis gesehen hat, weiß die
App erst mit Konten (Bauschritt 2/3).
"""

import hmac
import re
import unicodedata
from datetime import datetime, timedelta
from urllib.parse import urlsplit

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


def ist_neu(auftrag: dict, jetzt: datetime) -> bool:
    fertig = auftrag.get("abgeschlossen")
    return bool(fertig) and jetzt - datetime.fromisoformat(fertig) <= timedelta(hours=NEU_STUNDEN)


def _zeitpunkt(auftrag: dict) -> float:
    """Wann ein Schritt der Kette geschah: Rückmeldung beim Schreiben, Fassung beim Fertigwerden (sonst Start)."""
    t = (auftrag.get("erstellt") if auftrag.get("agent") == "feedback" else None) \
        or auftrag.get("abgeschlossen") or auftrag.get("erstellt")
    return datetime.fromisoformat(t).timestamp() if t else 0.0


def ursprung_id(auftrag: dict, nach_id: dict[str, dict]) -> str:
    """ID des Ursprungsauftrags: bezug bis zum Anfang folgen (Nachbesserungen von Nachbesserungen)."""
    gesehen = {auftrag.get("id")}
    while auftrag.get("bezug") in nach_id and auftrag["bezug"] not in gesehen:
        auftrag = nach_id[auftrag["bezug"]]
        gesehen.add(auftrag.get("id"))
    return auftrag.get("id") or ""


def ketten(auftraege_: list[dict]) -> list[list[dict]]:
    """Aufträge (neue und erledigte) als Ketten je Ursprung, jede zeitlich sortiert; zurückgezogene fehlen."""
    gueltig = [a for a in auftraege_ if a.get("id") and a.get("status") != "zurueckgezogen"]
    nach_id = {a["id"]: a for a in gueltig}
    gruppen: dict[str, list[dict]] = {}
    for a in gueltig:
        gruppen.setdefault(ursprung_id(a, nach_id), []).append(a)
    return [sorted(k, key=_zeitpunkt) for k in gruppen.values()]


def kette_von(auftrag_id: str, auftraege_: list[dict]) -> list[dict]:
    return next((k for k in ketten(auftraege_) if any(a["id"] == auftrag_id for a in k)), [])


def fassungen(kette: list[dict]) -> list[dict]:
    """Die Ergebnisse einer Kette (Ursprung und Nachbesserungen), ohne Lias Rückmeldungen."""
    return [a for a in kette if a.get("agent") != "feedback"]


def kopf(kette: list[dict]) -> dict:
    """Der Auftrag, für den die Kette steht (Titel, Art, Link): die erste Fassung."""
    return (fassungen(kette) or kette)[0]


def _aktuelle_dateien(fassungen_: list[dict]) -> dict | None:
    """Die jüngste erledigte Fassung mit Dateien (eine Antwort ohne Dateien ersetzt sie nicht)."""
    return next((a for a in reversed(fassungen_) if a.get("status") == "erledigt" and a.get("ergebnis_dateien")),
                None)


def ketten_zeile(kette: list[dict], jetzt: datetime, marke: str = "") -> dict:
    nach_id = {a["id"]: a for a in kette}
    k, f = kopf(kette), fassungen(kette)
    dateien_von = _aktuelle_dateien(f)
    hinweis = " · ".join(x for x in (dateien_text(dateien_von["ergebnis_dateien"]) if dateien_von else "",
                                     "nach deiner Rückmeldung" if len(f) > 1 else "") if x)
    return _zeile(titel(k, nach_id), art(k), zeit_text(f[-1].get("abgeschlossen"), jetzt), marke, hinweis,
                  ergebnis_link(k))


def heute(neue: list[dict], erledigte: list[dict], entwuerfe: list[dict], jetzt: datetime,
          person: str = "Lia", reihen: list[dict] | None = None, filter_: str = "") -> dict:
    """Ansichtsdaten für "Heute". neue/erledigte: agentkit.auftraege, entwuerfe: agentkit.freigabe.offene().

    Je Kette eine Zeile. Abschnitt, Zeit und "Neu" richten sich nach der jüngsten Fassung; läuft etwas in der
    Kette (Nachbesserung oder Rückmeldung), steht sie unter "Läuft gerade".
    reihen (reihen_aus): jede Zeile nennt ihre Reihe; filter_ (filter_gueltig) zeigt nur passende Zeilen. Die
    Zahl in der Begrüßung zählt immer alles, was wartet."""
    reihen = reihen or []

    def mit_reihe(zeile: dict, eintrag: dict) -> dict:
        r = reihe_von(eintrag, reihen)
        return {**zeile, "reihe": reihe_text(r), "_passt": reihe_passt(r, filter_)}

    laufend, fertige = [], []
    for kette in ketten([*neue, *erledigte]):
        if any(a.get("status") == "neu" for a in kette):
            laufend.append(kette)
        elif fassungen(kette):  # nur Rückmeldungen ohne bekanntes Ergebnis: nichts zu zeigen
            fertige.append(kette)
    fertige.sort(key=lambda k: _zeitpunkt(fassungen(k)[-1]), reverse=True)
    ergebnisse = [k for k in fertige if fassungen(k)[-1].get("status") == "erledigt"]
    neu = [k for k in ergebnisse if ist_neu(fassungen(k)[-1], jetzt)]
    wartet = ([mit_reihe(entwurf_zeile(e, jetzt), e)
               for e in sorted(entwuerfe, key=lambda e: e.get("erstellt") or "", reverse=True)]
              + [mit_reihe(ketten_zeile(k, jetzt, "Neu"), kopf(k)) for k in neu])
    laeuft = []
    for kette in sorted(laufend, key=lambda k: _zeitpunkt(next(a for a in k if a.get("status") == "neu"))):
        k = kopf(kette)
        start = next(a for a in kette if a.get("status") == "neu").get("erstellt")
        laeuft.append(mit_reihe(_zeile(titel(k, {a["id"]: a for a in kette}),
                                       art(k) if k.get("agent") != "feedback" else "Rückmeldung",
                                       "seit " + zeit_text(start, jetzt) if start else "",
                                       hinweis="Arbeitet an deiner Rückmeldung" if len(kette) > 1 else "",
                                       link=ergebnis_link(k) if zeigbar(k) else ""), k))
    rest = [mit_reihe(ketten_zeile(k, jetzt), kopf(k)) for k in ergebnisse if k not in neu]
    fehlgeschlagen = [mit_reihe({**ketten_zeile(k, jetzt), "hinweis": "", "grund": kurz(grund(fassungen(k)[-1]), 300)},
                                kopf(k))
                      for k in fertige if fassungen(k)[-1].get("status") == "fehlgeschlagen"]
    n = len(wartet)

    def gefiltert(zeilen: list[dict]) -> list[dict]:
        return [{k: v for k, v in z.items() if k != "_passt"} for z in zeilen if z["_passt"]]

    rest = gefiltert(rest)
    return {
        "datum": datum_text(jetzt),
        "begruessung": f"Hallo {person}.",
        "anzahl_wartet": n,
        "wartet_text": ("Gerade wartet nichts auf dich." if n == 0
                        else "Sache wartet auf dich." if n == 1 else "Sachen warten auf dich."),
        "wartet": gefiltert(wartet),
        "laeuft": gefiltert(laeuft),
        "fertig": rest[:FERTIG_ANZAHL],
        "fertig_weitere": max(0, len(rest) - FERTIG_ANZAHL),
        "fehlgeschlagen": gefiltert(fehlgeschlagen),
        "chips": filter_chips(reihen, filter_),
        "filter": filter_,
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


def inhalt(auftrag: dict) -> dict:
    """Kern, Punkte, Blöcke und "Bitte prüfen" einer Fassung. Ohne daten.kern der ganze Ergebnistext."""
    daten = auftrag.get("daten") or {}
    if auftrag.get("status") != "erledigt":
        return {"kern": "", "punkte": [], "bloecke": [], "pruefen": ""}
    if daten.get("kern"):
        kern, punkte, bloecke = ohne_ids(daten["kern"]), [ohne_ids(p) for p in daten.get("punkte") or []], []
    else:
        kern, punkte, bloecke = "", [], absaetze(auftrag.get("ergebnis") or "")
    return {"kern": kern, "punkte": punkte, "bloecke": bloecke, "pruefen": ohne_ids(daten.get("pruefen") or "")}


def _dateien(auftrag: dict | None, vorschauen: dict[str, list[tuple[bool, bool, int]]]) -> list[dict]:
    if not auftrag:
        return []
    pfade = list(auftrag.get("ergebnis_dateien") or [])
    return [{**d, "auftrag": auftrag["id"]}
            for d in dateien_ansicht(pfade, vorschauen.get(auftrag["id"]) or [(False, False, 0)] * len(pfade))]


def verlauf(kette: list[dict], aktuell: dict | None, vorschauen: dict[str, list[tuple[bool, bool, int]]],
            jetzt: datetime) -> list[dict]:
    """Schritte der Kette in zeitlicher Folge: Fassungen (bzw. Antworten ohne Dateien) und Lias Rückmeldungen.

    art: "fassung" oder "rueckmeldung". aktuell: diese Fassung steht oben in der Ansicht."""
    beantwortet = {a["id"] for a in kette if a.get("agent") != "feedback"}
    schritte, nummer = [], 0
    for a in kette:
        if a.get("agent") == "feedback":
            nb = (a.get("daten") or {}).get("nachbesserung")
            notiz = ("Wird gerade bearbeitet." if a.get("status") == "neu"
                     else "" if nb in beantwortet else ohne_ids(a.get("ergebnis") or ""))
            schritte.append({"art": "rueckmeldung", "name": "Deine Rückmeldung",
                             "zeit": zeit_text(a.get("erstellt"), jetzt), "zitat": ohne_ids(a.get("text") or ""),
                             "notiz": notiz})
            continue
        if nummer == 0 or a.get("ergebnis_dateien"):
            nummer += 1
            name = f"Fassung {nummer}"
        else:
            name = "Antwort"
        status = a.get("status")
        schritte.append({
            "art": "fassung", "name": name, "id": a["id"], "aktuell": a is aktuell,
            "zeit": ("seit " + zeit_text(a.get("erstellt"), jetzt) if status == "neu"
                     else zeit_text(a.get("abgeschlossen"), jetzt)),
            "notiz": ("Läuft gerade." if status == "neu"
                      else "Hat nicht geklappt: " + grund(a) if status == "fehlgeschlagen" else ""),
            **inhalt(a),
            "dateien": _dateien(a, vorschauen) if status == "erledigt" else [],
        })
    return schritte


def ergebnis(kette: list[dict], vorschauen: dict[str, list[tuple[bool, bool, int]]], jetzt: datetime) -> dict:
    """Ansicht eines Auftrags samt Feedback-Schleife (kette aus ketten()): neueste Fassung oben, darunter der
    Verlauf. vorschauen: je Auftrags-ID die Vorschau-Infos seiner Ergebnisdateien (siehe dateien_ansicht)."""
    nach_id = {a["id"]: a for a in kette}
    k, f = kopf(kette), fassungen(kette)
    fertig = [a for a in f if a.get("status") in ("erledigt", "fehlgeschlagen")]
    erledigt = [a for a in f if a.get("status") == "erledigt"]
    aktuell = erledigt[-1] if erledigt else None
    juengste = fertig[-1] if fertig else k
    dateien_von = _aktuelle_dateien(f)
    laufend = next((a for a in kette if a.get("status") == "neu"), None)
    fehlgeschlagen = aktuell is None
    schritte = verlauf(kette, aktuell, vorschauen, jetzt)
    dateien_ = _dateien(dateien_von, vorschauen)
    return {
        "titel": titel(k, nach_id, TITEL_LANG),
        "unter": " · ".join(x for x in (art(k), zeit_text(juengste.get("abgeschlossen"), jetzt)) if x),
        "fehlgeschlagen": fehlgeschlagen,
        "grund": grund(juengste) if fehlgeschlagen else "",
        # Die letzte Nachbesserung ist fehlgeschlagen, oben steht die Fassung davor
        "zuletzt_fehlgeschlagen": (grund(juengste) if not fehlgeschlagen and juengste is not aktuell
                                   and juengste.get("status") == "fehlgeschlagen" else ""),
        "laeuft": ("Arbeitet gerade an deiner Rückmeldung (seit " + zeit_text(laufend.get("erstellt"), jetzt) + ")."
                   if laufend else ""),
        **inhalt(aktuell or {}),
        "dateien": dateien_,
        # Die neueste Antwort hat keine Dateien: Sie stammen aus einer früheren Fassung
        "dateien_aus": (next(x["name"] for x in schritte if x.get("id") == dateien_von["id"])
                        if dateien_ and dateien_von is not aktuell else ""),
        "verlauf": schritte if len(kette) > 1 else [],
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


# Neuer Auftrag: nur Arten, deren Agent neue Aufträge annimmt. Theater nimmt nur Nachbesserungen an (neue Runden
# startet runde.py von Hand), Frage und Woche sind in unterricht Platzhalter. Material wie im Telegram-Portal.
NEU_AGENT, NEU_QUELLE = "unterricht", "portal-material"
NEU_TEXT_MAX = 5000
NEU_DATEIEN_MAX = 10
NEU_DATEI_MAX_MB = 20  # wie Telegram
# Was der Agent lesen kann: Office und PDF über agentkit.textfassung, Bilder direkt
NEU_ENDUNGEN = (".pdf", ".docx", ".pptx", ".xlsx", ".jpg", ".jpeg", ".png")
_UNERLAUBT = re.compile(r'[\\/:*?"<>|\x00-\x1f\x7f]')


def dateiname_bereinigen(name: str) -> str:
    """Sicherer Dateiname aus dem Upload: ohne Ordner, Steuerzeichen und Punkt am Anfang, höchstens 100 Zeichen."""
    name = unicodedata.normalize("NFC", name.replace("\\", "/").rsplit("/", 1)[-1])
    name = " ".join(_UNERLAUBT.sub("_", name).split()).lstrip(".")
    stamm, punkt, endung = name.rpartition(".")
    if not punkt:
        stamm, endung = name, ""
    stamm = stamm[: 100 - len(endung) - 1].rstrip() or "datei"
    return f"{stamm}.{endung.lower()}" if endung else stamm


def neuer_auftrag_pruefen(text: str, dateien: list[tuple[str, int]]) -> tuple[str, list[str]]:
    """Prüft Lias Eingaben. dateien: (Name, Größe in Bytes). Gibt den bereinigten Text und Fehlertexte zurück."""
    text = (text or "").replace("\r\n", "\n").strip()
    fehler = []
    if not text:
        fehler.append("Schreib bitte kurz, was du brauchst.")
    elif len(text) > NEU_TEXT_MAX:
        fehler.append(f"Der Text ist zu lang (höchstens {NEU_TEXT_MAX} Zeichen).")
    if len(dateien) > NEU_DATEIEN_MAX:
        fehler.append(f"Höchstens {NEU_DATEIEN_MAX} Dateien auf einmal.")
    for name, groesse in dateien:
        if not name.lower().endswith(NEU_ENDUNGEN):
            fehler.append(f"„{dateiname_bereinigen(name)}“: Diese Art Datei kann ich nicht lesen "
                          "(PDF, Word, PowerPoint, Excel, Foto).")
        elif groesse > NEU_DATEI_MAX_MB * 1024 * 1024:
            fehler.append(f"„{dateiname_bereinigen(name)}“ ist größer als {NEU_DATEI_MAX_MB} MB.")
        elif groesse == 0:
            fehler.append(f"„{dateiname_bereinigen(name)}“ ist leer.")
    return text, fehler


def herkunft_passt(origin: str | None, host: str | None, sec_fetch_site: str | None) -> bool:
    """Kommt ein Formular von dieser Seite? Schutz gegen fremde Seiten im selben Browser (CSRF), solange es
    keine Konten gibt: Origin muss zum Host passen, Sec-Fetch-Site (wenn gesendet) same-origin sein."""
    if sec_fetch_site and sec_fetch_site != "same-origin":
        return False
    if not origin or not host or origin == "null":
        return False
    return urlsplit(origin).netloc == host


def formular_token(geheim: bytes) -> str:
    return hmac.new(geheim, b"neuer-auftrag", "sha256").hexdigest()


def token_passt(geheim: bytes, token: str | None) -> bool:
    return bool(token) and hmac.compare_digest(formular_token(geheim), token)


# Ordnung nach Fach, Klasse oder Kurs und Reihe (Jan 30.10.2026). Eine Reihe kommt aus reihen.toml (ordnung.py);
# ein Auftrag gehört zu ihr, wenn er ihre Kennung im Feld "reihe" trägt (Neuer Auftrag) oder sein Agent in ihrer
# Liste "agenten" steht und in keiner anderen (theater, examen). Was nicht sicher passt, ist "ohne Reihe": Am
# Auftragstext wird nichts geraten.
REIHE_TEXTE = ("id", "fach", "klasse", "titel", "reihenfrage", "lerngruppe", "notizen", "stand")
REIHE_LISTEN = ("behandelt", "merksaetze", "bisherige_reihen", "agenten")
REIHE_STAENDE = ("laufend", "abgeschlossen")
OHNE_REIHE = "ohne"
_UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
_KLAMMER = re.compile(r"\s*\([^)]*\)")


def kennung(*teile: str) -> str:
    """Kennung aus Fach, Klasse und Titel: Kleinbuchstaben, Ziffern, Bindestriche (agentkit REIHE_MUSTER).
    Klammern im Titel zählen nicht mit („Straftheorien (in Planung)“ bleibt ethik-8-straftheorien)."""
    text = " ".join(_KLAMMER.sub("", t) for t in teile).lower().translate(_UMLAUTE)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:80].rstrip("-")


def gruppe_name(klasse: str) -> str:
    """'8' -> 'Klasse 8', 'Kurs 11' bleibt."""
    return f"Klasse {klasse}" if klasse.isdigit() else klasse


def reihen_aus(eintraege: list, standard_fach: str = "") -> tuple[list[dict], list[str]]:
    """Reihen aus den [[reihe]]-Blöcken einer reihen.toml, geprüft. Gibt (Reihen, Fehlertexte für Jan) zurück;
    fehlerhafte Reihen fehlen. Pflicht: klasse und fach (ohne Angabe standard_fach)."""
    reihen, fehler, ids = [], [], set()
    for nr, e in enumerate(eintraege, 1):
        if not isinstance(e, dict):
            fehler.append(f"Reihe {nr}: kein Block [[reihe]]")
            continue
        falsch = sorted(k for k in e if k not in REIHE_TEXTE + REIHE_LISTEN
                        or (k in REIHE_TEXTE and not isinstance(e[k], str))
                        or (k in REIHE_LISTEN and not (isinstance(e[k], list)
                                                       and all(isinstance(x, str) for x in e[k]))))
        fach = (e.get("fach") if isinstance(e.get("fach"), str) else "").strip() or standard_fach
        klasse = (e.get("klasse") if isinstance(e.get("klasse"), str) else "").strip()
        titel_ = (e.get("titel") if isinstance(e.get("titel"), str) else "").strip()
        rid = (e.get("id") if isinstance(e.get("id"), str) else "").strip() or kennung(fach, klasse, titel_)
        stand = e.get("stand") or "laufend"
        if falsch:
            fehler.append(f"Reihe {nr}: unbekannte oder falsche Felder {falsch}")
        elif not fach or not klasse:
            fehler.append(f"Reihe {nr}: {'fach' if not fach else 'klasse'} fehlt")
        elif rid != kennung(rid) or not rid:
            fehler.append(f"Reihe {nr}: id {rid!r} nur aus Kleinbuchstaben, Ziffern und Bindestrichen")
        elif rid in ids:
            fehler.append(f"Reihe {nr}: id {rid!r} gibt es doppelt")
        elif stand not in REIHE_STAENDE:
            fehler.append(f"Reihe {nr}: stand {stand!r}, erlaubt {list(REIHE_STAENDE)}")
        else:
            ids.add(rid)
            reihen.append({
                "id": rid, "fach": fach, "fach_id": kennung(fach), "klasse": klasse, "gruppe": gruppe_name(klasse),
                "gruppe_id": kennung(fach, klasse), "titel": titel_ or gruppe_name(klasse),
                "reihenfrage": (e.get("reihenfrage") or "").strip(), "behandelt": list(e.get("behandelt") or []),
                "laufend": stand == "laufend", "agenten": list(e.get("agenten") or []),
            })
    return reihen, fehler


def reihe_von(eintrag: dict, reihen: list[dict]) -> dict | None:
    """Reihe eines Auftrags oder Entwurfs: Feld "reihe", sonst der Agent, wenn er zu genau einer Reihe gehört."""
    gesetzt = eintrag.get("reihe")
    if gesetzt:
        return next((r for r in reihen if r["id"] == gesetzt), None)
    treffer = [r for r in reihen if eintrag.get("agent") and eintrag["agent"] in r["agenten"]]
    return treffer[0] if len(treffer) == 1 else None


def reihe_text(reihe: dict | None) -> str:
    return f"{reihe['fach']} · {reihe['gruppe']} · {reihe['titel']}" if reihe else ""


def reihe_passt(reihe: dict | None, filter_: str) -> bool:
    """filter_: "" (alle), "ohne", "fach:<id>", "gruppe:<id>" oder "reihe:<id>"."""
    if not filter_:
        return True
    if filter_ == OHNE_REIHE:
        return reihe is None
    art_, _, wert = filter_.partition(":")
    return reihe is not None and reihe.get({"fach": "fach_id", "gruppe": "gruppe_id", "reihe": "id"}.get(art_, "")) == wert


def filter_chips(reihen: list[dict], aktiv: str) -> list[dict]:
    """Auswahl über "Heute": Alle, je Fach, je Klasse (nur wenn ein Fach mehrere hat), Ohne Reihe. Ohne Reihen leer."""
    if not reihen:
        return []
    chips = [("Alle", "")]
    for fach_id in dict.fromkeys(r["fach_id"] for r in reihen):
        im_fach = [r for r in reihen if r["fach_id"] == fach_id]
        chips.append((im_fach[0]["fach"], f"fach:{fach_id}"))
        gruppen = {r["gruppe_id"]: r for r in im_fach}
        if len(gruppen) > 1:
            chips += [(f"{r['fach']} {r['klasse']}", f"gruppe:{gid}") for gid, r in gruppen.items()]
    chips.append(("Ohne Reihe", OHNE_REIHE))
    return [{"text": t, "wert": w, "aktiv": w == aktiv} for t, w in chips]


def filter_gueltig(wert: str | None, reihen: list[dict]) -> str:
    """Der Filter aus der URL, wenn es ihn als Chip oder Reihe gibt; sonst "" (alle)."""
    erlaubt = {c["wert"] for c in filter_chips(reihen, "")} | {f"reihe:{r['id']}" for r in reihen}
    return wert if wert in erlaubt else ""


def reihen_auswahl(reihen: list[dict]) -> list[dict]:
    """Laufende Reihen für "Neuer Auftrag": Kennung und Text wie „Straftheorien (Ethik, Klasse 8)“."""
    return [{"id": r["id"], "text": f"{r['titel']} ({r['fach']}, {r['gruppe']})"} for r in reihen if r["laufend"]]


def reihe_pruefen(wert: str | None, reihen: list[dict]) -> tuple[str | None, list[str]]:
    """Gewählte Reihe aus dem Formular: Kennung oder None (keine Reihe), sonst ein Fehlertext."""
    if not wert:
        return None, []
    if wert in {r["id"] for r in reihen_auswahl(reihen)}:
        return wert, []
    return None, ["Diese Reihe gibt es nicht (mehr). Bitte wähl sie neu."]


def unterricht(reihen: list[dict], auftraege_: list[dict], jetzt: datetime) -> dict:
    """Ansicht "Unterricht": Fach, Klasse oder Kurs, Reihe, je mit ihren Aufträgen (neueste zuerst), darunter die
    Aufträge ohne Reihe. Je Kette eine Zeile wie in "Heute"."""
    zeilen_je: dict[str, list] = {}
    for kette in sorted((k for k in ketten(auftraege_) if fassungen(k)),
                        key=lambda k: _zeitpunkt(fassungen(k)[-1]), reverse=True):
        r = reihe_von(kopf(kette), reihen)
        letzte = fassungen(kette)[-1]
        marke = ("Läuft" if any(a.get("status") == "neu" for a in kette)
                 else "Hat nicht geklappt" if letzte.get("status") == "fehlgeschlagen" else "")
        zeile = ketten_zeile(kette, jetzt, marke)
        if not zeigbar(kopf(kette)):
            zeile["link"] = ""
        zeilen_je.setdefault(r["id"] if r else OHNE_REIHE, []).append(zeile)
    faecher: dict[str, dict] = {}
    for r in reihen:
        fach = faecher.setdefault(r["fach_id"], {"name": r["fach"], "gruppen": {}})
        gruppe = fach["gruppen"].setdefault(r["gruppe_id"], {"name": r["gruppe"], "reihen": []})
        gruppe["reihen"].append({"id": r["id"], "titel": r["titel"], "reihenfrage": r["reihenfrage"],
                                 "behandelt": "; ".join(r["behandelt"]), "laufend": r["laufend"],
                                 "zeilen": zeilen_je.get(r["id"], [])})
    return {"faecher": [{"name": f["name"], "gruppen": list(f["gruppen"].values())} for f in faecher.values()],
            "ohne": zeilen_je.get(OHNE_REIHE, [])}
