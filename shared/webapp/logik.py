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
from pathlib import Path
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
# Knöpfe der Material-Ansicht (Board "Desktop"): lange Fassung der Dateiknöpfe
OEFFNEN = {".pdf": "PDF zum Drucken", ".docx": "In Word öffnen", ".pptx": "In PowerPoint öffnen",
           ".xlsx": "In Excel öffnen"}
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
          person: str = "Lia", reihen: list[dict] | None = None, finale: set[str] | None = None) -> dict:
    """Ansichtsdaten für "Heute". neue/erledigte: agentkit.auftraege, entwuerfe: agentkit.freigabe.offene().

    Je Kette eine Zeile. Abschnitt, Zeit und "Neu" richten sich nach der jüngsten Fassung; läuft etwas in der
    Kette (Nachbesserung oder Rückmeldung), steht sie unter "Läuft gerade".
    reihen (reihen_aus): jede Zeile nennt ihren Ort als Brotkrume (Fach › Klasse › Reihe).
    finale: IDs der Ursprünge, die Lia als final markiert hat: Sie warten nicht mehr, stehen unter Fertig."""
    reihen, finale = reihen or [], finale or set()

    def mit_reihe(zeile: dict, eintrag: dict) -> dict:
        return {**zeile, "reihe": reihe_text(reihe_von(eintrag, reihen))}

    laufend, fertige = [], []
    for kette in ketten([*neue, *erledigte]):
        if any(a.get("status") == "neu" for a in kette):
            laufend.append(kette)
        elif fassungen(kette):  # nur Rückmeldungen ohne bekanntes Ergebnis: nichts zu zeigen
            fertige.append(kette)
    fertige.sort(key=lambda k: _zeitpunkt(fassungen(k)[-1]), reverse=True)
    ergebnisse = [k for k in fertige if fassungen(k)[-1].get("status") == "erledigt"]
    neu = [k for k in ergebnisse if ist_neu(fassungen(k)[-1], jetzt) and kopf(k)["id"] not in finale]
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
    rest = [mit_reihe(ketten_zeile(k, jetzt, "Final" if kopf(k)["id"] in finale else ""), kopf(k))
            for k in ergebnisse if k not in neu]
    fehlgeschlagen = [mit_reihe({**ketten_zeile(k, jetzt), "hinweis": "", "grund": kurz(grund(fassungen(k)[-1]), 300)},
                                kopf(k))
                      for k in fertige if fassungen(k)[-1].get("status") == "fehlgeschlagen"]
    n = len(wartet)
    return {
        "datum": datum_text(jetzt),
        "begruessung": f"Hallo {person}.",
        "anzahl_wartet": n,
        "wartet_text": ("Gerade wartet nichts auf dich." if n == 0
                        else "Sache wartet auf dich." if n == 1 else "Sachen warten auf dich."),
        "wartet": wartet,
        "laeuft": laeuft,
        "fertig": rest[:FERTIG_ANZAHL],
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
            knoepfe.append({"text": "PDF", "lang": OEFFNEN[".pdf"], "pfad": "/pdf"})
        knoepfe.append({"text": DATEIKNOEPFE.get(endung, "Datei"), "lang": OEFFNEN.get(endung, "Herunterladen"),
                        "pfad": ""})
        ansicht.append({"nr": nr, "name": datei_name(pfad), "knoepfe": knoepfe, "seiten": seiten,
                        "seiten_text": seiten_text(seiten) if seiten else ""})
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


def eigene_ref(n: int) -> str:
    """Kennung der n-ten eigenen Fassung von Lia (ab 1), wie eine Auftrags-ID für die Fassungen."""
    return f"eigene-{n}"


def zeitfolge(kette: list[dict], eigene: list[dict] = ()) -> list[tuple[str, dict]]:
    """Schritte der Kette und Lias eigene Fassungen (Einträge mit zeit, siehe zustand.py) zeitlich gemischt.
    Gibt (ref, eintrag) zurück: ref ist die Auftrags-ID bzw. eigene_ref(n); eigene Einträge tragen eigene=True."""
    folge = [(_zeitpunkt(a), a["id"], a) for a in kette]
    folge += [(_zeitpunkt({"erstellt": e.get("zeit")}), eigene_ref(n), {**e, "eigene": True})
              for n, e in enumerate(eigene, 1)]
    return [(ref, x) for _, ref, x in sorted(folge, key=lambda t: t[0])]


def fassung_namen(kette: list[dict], eigene: list[dict] = ()) -> dict[str, str]:
    """Name jeder Fassung: "Fassung n" (n zählt den Ursprung, Fassungen mit Dateien und Lias eigene Fassungen),
    sonst "Antwort". Schlüssel: Auftrags-ID bzw. eigene_ref(n)."""
    namen, nummer = {}, 0
    for ref, a in zeitfolge(kette, eigene):
        if a.get("agent") == "feedback":
            continue
        if nummer == 0 or a.get("ergebnis_dateien") or a.get("eigene"):
            nummer += 1
            namen[ref] = f"Fassung {nummer}"
        else:
            namen[ref] = "Antwort"
    return namen


def verlauf(kette: list[dict], aktuell: dict | None, vorschauen: dict[str, list[tuple[bool, bool, int]]],
            jetzt: datetime, eigene: list[dict] = (), final_ref: str = "") -> list[dict]:
    """Schritte der Kette in zeitlicher Folge: Fassungen (bzw. Antworten ohne Dateien), Lias Rückmeldungen und
    Lias eigene Fassungen.

    art: "fassung", "eigene" oder "rueckmeldung". aktuell: diese Fassung steht oben in der Ansicht.
    ref: Kennung für "final" (Auftrags-ID bzw. eigene_ref); finalbar: Lia kann sie als final markieren."""
    beantwortet = {a["id"] for a in kette if a.get("agent") != "feedback"}
    namen = fassung_namen(kette, eigene)
    schritte = []
    for ref, a in zeitfolge(kette, eigene):
        if a.get("eigene"):
            schritte.append({
                "art": "eigene", "name": namen[ref], "ref": ref, "von": "von dir", "aktuell": False,
                "zeit": zeit_text(a.get("zeit"), jetzt), "beschreibung": a.get("notiz") or "",
                "datei": {"name": datei_name(a.get("name") or ""), "nr": int(ref.rsplit("-", 1)[1]),
                          "knopf": DATEIKNOEPFE.get(Path(a.get("name") or "").suffix.lower(), "Datei")},
                "final": ref == final_ref, "finalbar": True})
            continue
        if a.get("agent") == "feedback":
            nb = (a.get("daten") or {}).get("nachbesserung")
            notiz = ("Wird gerade bearbeitet." if a.get("status") == "neu"
                     else "" if nb in beantwortet else ohne_ids(a.get("ergebnis") or ""))
            schritte.append({"art": "rueckmeldung", "name": "Deine Rückmeldung",
                             "zeit": zeit_text(a.get("erstellt"), jetzt), "zitat": ohne_ids(a.get("text") or ""),
                             "notiz": notiz})
            continue
        status = a.get("status")
        teile = inhalt(a)
        schritte.append({
            "art": "fassung", "name": namen[a["id"]], "id": a["id"], "ref": a["id"], "aktuell": a is aktuell,
            "von": "vom Assistenten", "beschreibung": kurz(teile["kern"] or next(iter(teile["punkte"]), ""), 120),
            "final": a["id"] == final_ref,
            "finalbar": status == "erledigt" and namen[a["id"]] != "Antwort",
            "zeit": ("seit " + zeit_text(a.get("erstellt"), jetzt) if status == "neu"
                     else zeit_text(a.get("abgeschlossen"), jetzt)),
            "notiz": ("Läuft gerade." if status == "neu"
                      else "Hat nicht geklappt: " + grund(a) if status == "fehlgeschlagen" else ""),
            **teile,
            "dateien": _dateien(a, vorschauen) if status == "erledigt" else [],
        })
    return schritte


def ergebnis(kette: list[dict], vorschauen: dict[str, list[tuple[bool, bool, int]]], jetzt: datetime,
             eigene: list[dict] = (), final_ref: str = "") -> dict:
    """Material-Ansicht eines Auftrags samt Feedback-Schleife (kette aus ketten(), Board "Desktop"): neueste
    Fassung des Assistenten oben, darunter die Fassungen. vorschauen: je Auftrags-ID die Vorschau-Infos seiner
    Ergebnisdateien (siehe dateien_ansicht). eigene, final_ref: was die Web-App selbst speichert (zustand.py)."""
    nach_id = {a["id"]: a for a in kette}
    k, f = kopf(kette), fassungen(kette)
    fertig = [a for a in f if a.get("status") in ("erledigt", "fehlgeschlagen")]
    erledigt = [a for a in f if a.get("status") == "erledigt"]
    aktuell = erledigt[-1] if erledigt else None
    juengste = fertig[-1] if fertig else k
    dateien_von = _aktuelle_dateien(f)
    laufend = next((a for a in kette if a.get("status") == "neu"), None)
    fehlgeschlagen = aktuell is None
    schritte = verlauf(kette, aktuell, vorschauen, jetzt, eigene, final_ref)
    final = next((x for x in schritte if x.get("final") and x.get("finalbar")), None)
    oben = (dateien_von or aktuell or {}).get("id") or ""
    dateien_ = _dateien(dateien_von, vorschauen)
    if final:
        marke = "Final"
    elif laufend:
        marke = "Läuft"
    elif aktuell is not None and ist_neu(juengste, jetzt):
        marke = "Neu · wartet"
    else:
        marke = ""
    if len(dateien_) == 1:
        dateiart = DATEIKNOEPFE.get(Path(dateien_von["ergebnis_dateien"][dateien_[0]["nr"]]).suffix.lower(), "")
    else:
        dateiart = dateien_text([dateien_von["ergebnis_dateien"][d["nr"]] for d in dateien_])
    return {
        "art_zeile": " · ".join(x for x in (art(k), dateiart) if x),
        "marke": marke,
        "final_name": final["name"] if final else "",
        # Knopf "Als final markieren" in der Spalte gilt für die Fassung, deren Dateien oben stehen
        "aktuell_ref": oben if final_erlaubt(oben, schritte) else "",
        "aktuell_final": bool(final) and final["ref"] == oben,
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
        "verlauf": schritte,
    }


VERALTET = "Die Seite war veraltet. Bitte wähle die Dateien neu und schick es noch einmal ab."
HINWEISE = {
    "final": "Final. Diese Fassung ist jetzt die, die du nimmst.",
    "nicht-final": "Nicht mehr final.",
    "eigene": "Deine Datei ist jetzt die neueste Fassung.",
    "rueckmeldung": "Rückmeldung ist unterwegs. Die neue Fassung erscheint hier und in „Heute“.",
    "rueckmeldung-test": "Rückmeldung angelegt (Testbetrieb, es startet kein Agent).",
    "stunde": "Angelegt. Mit „Gehört zu“ in einem Material ordnest du es hier ein.",
    "thema": "Thema geändert.",
    "zugeordnet": "Eingeordnet.",
    "auftrag": "Dein Auftrag ist unterwegs. Er steht hier und in „Heute“.",
    "auftrag-test": "Auftrag angelegt (Testbetrieb, es startet kein Agent). Er steht hier und in „Heute“.",
}


def hinweis_nach(aktion: str, ort: str = "") -> str:
    """Hinweis oben in der Material-Ansicht nach einer Aktion (?erledigt=…); unbekannt: nichts."""
    if aktion == "final" and ort:
        return f"Final. Diese Fassung steht jetzt bei {ort}."
    return HINWEISE.get(aktion, "")


def final_erlaubt(ref: str, schritte: list[dict]) -> bool:
    """Darf diese Fassung (ref aus verlauf) als final markiert werden?"""
    return any(x.get("ref") == ref and x.get("finalbar") for x in schritte)


def final_setzen(zustand_: dict, kopf_id: str, ref: str, an: bool, zeit: str) -> dict:
    """Neuer Zustand (zustand.py) mit final an bzw. aus. Je Auftrag ist höchstens eine Fassung final."""
    final = dict(zustand_.get("final") or {})
    if an:
        final[kopf_id] = {"fassung": ref, "zeit": zeit}
    elif (final.get(kopf_id) or {}).get("fassung") == ref:
        del final[kopf_id]
    return {**zustand_, "final": final}


def eigene_dazu(zustand_: dict, kopf_id: str, eintrag: dict) -> tuple[dict, int]:
    """Neuer Zustand mit einer eigenen Fassung mehr und ihre Nummer (ab 1)."""
    eigene = {k: list(v) for k, v in (zustand_.get("eigene") or {}).items()}
    eigene.setdefault(kopf_id, []).append(eintrag)
    return {**zustand_, "eigene": eigene}, len(eigene[kopf_id])


EIGENE_ENDUNGEN = (".pdf", ".docx", ".pptx", ".xlsx")
RUECK_ENDUNGEN = (".pdf", ".docx", ".pptx", ".xlsx", ".jpg", ".jpeg", ".png")


def datei_pruefen(name: str, groesse: int, endungen: tuple[str, ...]) -> list[str]:
    """Fehler für eine hochgeladene Datei (eigene Fassung oder Anhang einer Rückmeldung), sonst leer."""
    if Path(name).suffix.lower() not in endungen:
        arten = ", ".join(sorted({DATEIKNOEPFE.get(e, "Foto") for e in endungen}))
        return [f"Diese Datei geht nicht. Möglich sind: {arten}."]
    if groesse > NEU_DATEI_MAX_MB * 1024 * 1024:
        return [f"Die Datei ist zu groß (höchstens {NEU_DATEI_MAX_MB} MB)."]
    return []


def rueckmeldung_pruefen(text: str, datei: tuple[str, int] | None) -> tuple[str, list[str]]:
    """Rückmeldung aus der Material-Ansicht: Text ist Pflicht, eine Datei mit Kommentaren darf dazu."""
    text = (text or "").strip()
    fehler = []
    if not text:
        fehler.append("Schreib kurz, was anders werden soll.")
    elif len(text) > NEU_TEXT_MAX:
        fehler.append(f"Der Text ist zu lang (höchstens {NEU_TEXT_MAX} Zeichen).")
    if datei:
        fehler += datei_pruefen(*datei, RUECK_ENDUNGEN)
    return text, fehler


def rueckmeldung_text(text: str, datei_name_: str = "", fassung: str = "") -> str:
    """Text des Auftrags an den Feedback-Dienst. Eine angehängte Datei liegt als eigene Fassung in der Web-App
    (die Agenten können sie noch nicht lesen, Bedarf b in Punkt 24 der Haupt-STATUS)."""
    if not datei_name_:
        return text
    return (f"{text}\n\nDazu gibt es eine Datei mit Kommentaren ({datei_name_}, {fassung}). Sie liegt bisher nur in "
            "der Web-App.")


def seiten_text(anzahl: int) -> str:
    return "1 Seite" if anzahl == 1 else f"{anzahl} Seiten"


def betrachter(kette: list[dict], auftrag_id: str, datei: dict, seite: str | None,
               eigene: list[dict] = ()) -> dict | None:
    """Seiten-Betrachter für eine Datei einer Fassung: eine Seite groß, Vor/Zurück, Rückweg zum Ergebnis.

    datei aus dateien_ansicht (nr, name, knoepfe, seiten) der Fassung auftrag_id; seite aus ?seite= (Standard 1).
    None (404), wenn die Datei keine Seitenbilder hat oder die Seitenzahl keine Zahl von 1 bis zur Anzahl ist."""
    anzahl = datei.get("seiten") or 0
    wert = "1" if seite is None else seite.strip()
    if not anzahl or not (wert.isascii() and wert.isdigit()) or len(wert) > 4 or not 1 <= int(wert) <= anzahl:
        return None
    m = int(wert)
    k = kopf(kette)
    namen = fassung_namen(kette, eigene)
    basis = f"/ergebnis/{auftrag_id}/datei/{datei['nr']}"
    seiten = [{"nr": n, "link": f"{basis}/ansehen?seite={n}", "aktiv": n == m} for n in range(1, anzahl + 1)]
    return {
        "titel": datei["name"],
        # Fassung nur nennen, wenn es mehr als eine gibt
        "unter": " · ".join(x for x in (namen.get(auftrag_id) if len(namen) > 1 else "", f"Seite {m} von {anzahl}")
                            if x),
        "ergebnis_titel": titel(k, {a["id"]: a for a in kette}, TITEL_LANG),
        "ergebnis_link": ergebnis_link(k),
        "seite": m, "anzahl": anzahl, "seiten": seiten,
        "bild": f"{basis}/seite/{m}",
        "vorher": seiten[m - 2]["link"] if m > 1 else "",
        "nachher": seiten[m]["link"] if m < anzahl else "",
        "knoepfe": [{**kn, "link": basis + kn["pfad"]} for kn in datei["knoepfe"]],
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


# Vorlagen der Galerie „Neu“ (Board „Desktop“): nur Arten, die der Agent wirklich baut (Arbeitsblatt docx, Folien
# pptx, Arbeitsmappe xlsx). Reihenentwurf, LEK, Spielfassung und Szenenaufgabe fehlen, bis ein Agent sie kann.
VORLAGEN = {
    "arbeitsblatt": {"name": "Arbeitsblatt", "text": "Text, Merksatz, Aufgaben", "bild": "ab",
                     "frage": "Was soll drauf?", "hint": "Thema, Position, Fall, Dauer …"},
    "praesentation": {"name": "Präsentation", "text": "Folien für eine Stunde", "bild": "folie",
                      "frage": "Wofür?", "hint": "Ablauf der Stunde, Leitfrage …"},
    "tabelle": {"name": "Tabelle", "text": "Notentabelle, Liste (Excel), ohne Namen", "bild": "tabelle",
                "frage": "Welche Spalten?", "hint": "Nr., Note 1–5, Durchschnitt …"},
}


# Formular ohne Vorlage (Freitext wie bisher), wenn ein Auftrag ohne Art nicht angenommen wurde
VORLAGE_FREI = {"name": "Neuer Auftrag", "frage": "Was brauchst du?",
                "hint": "Zum Beispiel: Arbeitsblatt zum kategorischen Imperativ, Klasse 10, 45 Minuten, mit Fallbeispiel"}


def neu_link(reihe_id: str = "", stunde: int | None = None, art_: str = "") -> str:
    """Link auf „Neu“ mit vorbelegtem Ort (und Art)."""
    teile = [f"art={art_}"] if art_ else []
    teile += [f"reihe={reihe_id}"] if reihe_id else []
    teile += [f"stunde={stunde}"] if reihe_id and stunde else []
    return "/neu" + ("?" + "&".join(teile) if teile else "")


def galerie(reihe_id: str = "", stunde: int | None = None) -> list[dict]:
    return [{"art": k, **v, "link": neu_link(reihe_id, stunde, k)} for k, v in VORLAGEN.items()]


def ort_text(reihe: dict | None, stunde: tuple[int, str] | None = None) -> str:
    """Ort im Formular „Neu“: „Ethik › Klasse 8 › Straftheorien › Stunde 3“."""
    if not reihe:
        return ""
    return reihe_text(reihe) + (f"{ORT_TRENNER}{stunden_wort(reihe)[0]} {stunde[0]}" if stunde else "")


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
ORT_TRENNER = " › "
KRUME_LANG = 60  # letzte Brotkrume (z. B. ein langer Ergebnistitel)
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
    """Ort einer Zeile als Brotkrume: „Ethik › Klasse 8 › Straftheorien“."""
    return ORT_TRENNER.join((reihe["fach"], reihe["gruppe"], reihe["titel"])) if reihe else ""


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


def text_mit_reihe(text: str, reihe_id: str | None, reihen: list[dict], stunde: tuple[int, str] | None = None,
                   art_: str = "") -> str:
    """Auftragstext für den Agenten: Art vorn, gewählte Reihe und Stunde (Nummer, Thema) am Ende, damit er sie
    ohne eigenen Code im Prompt hat (Lias Reihen kennt er aus reihen.toml, Stunden kennt er nicht)."""
    vorlage = VORLAGEN.get(art_)
    if vorlage:
        text = f"{vorlage['name']}: {text}"
    r = next((x for x in reihen if x["id"] == reihe_id), None)
    if not r:
        return text
    text += f"\n\nReihe: {r['titel']} ({r['fach']}, {r['gruppe']})"
    if stunde:
        text += f"\n{stunden_wort(r)[0]} {stunde[0]}: {stunde[1]}"
    return text


def material_marke(kette: list[dict], jetzt: datetime, finale: set[str] = frozenset(),
                   eigene: list[dict] = ()) -> str:
    """Stand eines Materials an seinem Ort (Board "Desktop"): Läuft, Final, Hat nicht geklappt, sonst die Zahl
    der Fassungen („Fassung 2“, mit „· neu“ in den ersten NEU_STUNDEN). eigene: Lias eigene Fassungen."""
    letzte = fassungen(kette)[-1]
    if any(a.get("status") == "neu" for a in kette):
        return "Läuft"
    if kopf(kette)["id"] in finale:
        return "Final"
    if letzte.get("status") == "fehlgeschlagen":
        return "Hat nicht geklappt"
    nummer = sum(1 for n in fassung_namen(kette, eigene).values() if n.startswith("Fassung"))
    return f"Fassung {nummer}" + (" · neu" if ist_neu(letzte, jetzt) else "")


def zeilen_je_reihe(reihen: list[dict], auftraege_: list[dict], jetzt: datetime,
                    entwuerfe: list[dict] | None = None, finale: set[str] = frozenset(),
                    eigene: dict[str, list[dict]] | None = None) -> dict[str, list[dict]]:
    """Zeilen je Reihen-Kennung (OHNE_REIHE für den Rest): offene Entwürfe, dann je Kette eine Zeile wie in
    "Heute" (neueste zuerst), mit Marke Offen bzw. dem Stand des Materials (material_marke).
    finale, eigene: was die Web-App selbst speichert (zustand.py)."""
    zeilen_je: dict[str, list] = {}
    for e in sorted(entwuerfe or [], key=lambda e: e.get("erstellt") or "", reverse=True):
        r = reihe_von(e, reihen)
        zeilen_je.setdefault(r["id"] if r else OHNE_REIHE, []).append(entwurf_zeile(e, jetzt))
    for kette in sorted((k for k in ketten(auftraege_) if fassungen(k)),
                        key=lambda k: _zeitpunkt(fassungen(k)[-1]), reverse=True):
        r = reihe_von(kopf(kette), reihen)
        marke = material_marke(kette, jetzt, finale, (eigene or {}).get(kopf(kette)["id"], []))
        zeile = {**ketten_zeile(kette, jetzt, marke), "id": kopf(kette)["id"]}  # id nur zum Zuordnen, nie sichtbar
        if not zeigbar(kopf(kette)):
            zeile["link"] = ""
        zeilen_je.setdefault(r["id"] if r else OHNE_REIHE, []).append(zeile)
    return zeilen_je


def reihe_ansicht(reihe: dict, reihen: list[dict], auftraege_: list[dict], jetzt: datetime,
                  entwuerfe: list[dict] | None = None, finale: set[str] = frozenset(),
                  eigene: dict[str, list[dict]] | None = None, stunden_: list[dict] = (),
                  stunde_von: dict[str, dict] | None = None) -> dict:
    """Ansicht einer Reihe: Reihenfrage, schon Behandeltes, Material und Entwürfe zur ganzen Reihe, darunter die
    Stunden (bzw. Proben) mit ihrem Material. stunden_, stunde_von: aus zustand.py (die Web-App speichert sie)."""
    zeilen = zeilen_je_reihe(reihen, auftraege_, jetzt, entwuerfe, finale, eigene).get(reihe["id"], [])
    je_stunde = material_je_stunde(reihe["id"], zeilen, stunde_von or {}, len(stunden_))
    einzahl, mehrzahl = stunden_wort(reihe)
    return {"titel": reihe["titel"], "unter": f"{reihe['fach']} · {reihe['gruppe']}"
                                              + ("" if reihe["laufend"] else " · abgeschlossen"),
            "reihenfrage": reihe["reihenfrage"], "behandelt": "; ".join(reihe["behandelt"]),
            "zeilen": je_stunde.get(0, []), "wort": einzahl, "wort_mehrzahl": mehrzahl,
            "stunden_neu": reihe_link(reihe) + "/stunden",
            "stunden": [{"nr": nr, "titel": s["thema"], "link": stunde_link(reihe, nr),
                         "unter": ", ".join(z["titel"] for z in je_stunde.get(nr, [])) or "noch leer"}
                        for nr, s in enumerate(stunden_, 1)]}


def reihe_link(reihe: dict) -> str:
    return f"/reihe/{reihe['id']}"


def klasse_link(reihe: dict) -> str:
    """Link zur Klasse/zum Kurs einer Reihe (Kennung aus Fach und Klasse)."""
    return f"/klasse/{reihe['gruppe_id']}"


def klasse_aktiv(gruppe_id: str) -> str:
    """Wert für baum(aktiv=…) in der Klassen-Ansicht (getrennt von Reihen-Kennungen)."""
    return "klasse:" + gruppe_id


def klasse_ansicht(gruppe_id: str, reihen: list[dict], zeilen_je: dict[str, list[dict]]) -> dict | None:
    """Ansicht einer Klasse/eines Kurses (nur lesend): ihre Reihen mit Reihenfrage und Zahl der Materialien.
    zeilen_je aus zeilen_je_reihe. Material, das nur zur Klasse gehört, kennt noch keine Datei. Unbekannt: None."""
    eigene = [r for r in reihen if r["gruppe_id"] == gruppe_id]
    if not eigene:
        return None
    zeilen = []
    for r in sorted(eigene, key=lambda r: not r["laufend"]):  # laufende zuerst, sonst Reihenfolge der Datei
        n = len(zeilen_je.get(r["id"], []))
        zeilen.append({"titel": r["titel"], "unter": r["reihenfrage"] or "Reihenfrage noch offen",
                       "hinweis": "Noch nichts" if n == 0 else "1 Sache" if n == 1 else f"{n} Sachen",
                       "marke": "" if r["laufend"] else "Abgeschlossen", "link": reihe_link(r)})
    return {"titel": eigene[0]["gruppe"], "unter": eigene[0]["fach"], "zeilen": zeilen, "reihe": eigene[0]}


def baum(reihen: list[dict], anzahl_wartet: int, aktiv: str = "") -> list[dict]:
    """Linke Spalte: oben "Heute" mit der Zahl, was wartet, dann je Fach die Klassen/Kurse und ihre Reihen.
    aktiv: "heute", die Kennung der gezeigten Reihe oder klasse_aktiv(…). art: "eintrag" (Link), "fach"
    (Überschrift) oder "gruppe" (Klasse/Kurs, Link zur Klassen-Ansicht)."""
    eintraege = [{"art": "eintrag", "text": "Heute", "link": "/", "tiefe": 0, "zahl": anzahl_wartet or "",
                  "aktiv": aktiv == "heute"}]
    faecher: dict[str, dict[str, list[dict]]] = {}
    for r in reihen:
        faecher.setdefault(r["fach"], {}).setdefault(r["gruppe"], []).append(r)
    for fach, gruppen in faecher.items():
        eintraege.append({"art": "fach", "text": fach})
        for gruppe, reihen_ in gruppen.items():
            eintraege.append({"art": "gruppe", "text": gruppe, "tiefe": 0, "link": klasse_link(reihen_[0]),
                              "aktiv": aktiv == klasse_aktiv(reihen_[0]["gruppe_id"])})
            eintraege += [{"art": "eintrag", "text": r["titel"] + ("" if r["laufend"] else " (abgeschlossen)"),
                           "link": reihe_link(r), "tiefe": 1, "zahl": "", "aktiv": aktiv == r["id"]}
                          for r in reihen_]
    return eintraege


def krumen(hier: str = "", reihe: dict | None = None, ueber: dict | None = None) -> dict:
    """Brotkrumen über dem Inhalt: Teile mit Link (Fach ohne, es hat keine eigene Ansicht), dann die Seite selbst.
    Ohne Angaben "Heute"; nur reihe: die Reihen-Ansicht; reihe und hier: eine Seite in der Reihe; nur hier: eine
    Seite ohne Reihe unter "Heute". ueber ({"text", "link"}): eine Seite dazwischen, z. B. das Ergebnis über dem
    Seiten-Betrachter."""
    hier = kurz(hier, KRUME_LANG)
    extra = [{"text": kurz(ueber["text"], KRUME_LANG), "link": ueber["link"]}] if ueber and hier else []
    if reihe is None:
        return {"teile": [{"text": "Heute", "link": "/"}, *extra] if hier else [], "hier": hier or "Heute"}
    teile = [{"text": reihe["fach"], "link": ""}, {"text": reihe["gruppe"], "link": klasse_link(reihe)}]
    if not hier:
        return {"teile": teile, "hier": reihe["titel"]}
    return {"teile": [*teile, {"text": reihe["titel"], "link": reihe_link(reihe)}, *extra], "hier": hier}


def krumen_klasse(reihe: dict) -> dict:
    """Brotkrumen der Klassen-Ansicht: Fach › Klasse (reihe: irgendeine Reihe der Klasse)."""
    return {"teile": [{"text": reihe["fach"], "link": ""}], "hier": reihe["gruppe"]}


# Stunden (Board "Desktop", Jan 30.10.: Lia will die Ebene Stunde). Die Web-App speichert sie selbst (zustand.py),
# die Agenten kennen sie nicht. Nummer = Platz in der Liste (ab 1), keine Pflicht (Regel R1).
STUNDE_THEMA_MAX = 120


def stunden_wort(reihe: dict) -> tuple[str, str]:
    """„Stunde“ bzw. „Probe“ für eine Inszenierung (Reihe des Theater-Agenten, Regel R7)."""
    return ("Probe", "Proben") if "theater" in reihe["agenten"] else ("Stunde", "Stunden")


def stunde_link(reihe: dict, nr: int) -> str:
    return f"/reihe/{reihe['id']}/stunde/{nr}"


def stunde_pruefen(thema: str) -> tuple[str, list[str]]:
    thema = " ".join((thema or "").split())
    if not thema:
        return "", ["Schreib kurz das Thema dazu."]
    if len(thema) > STUNDE_THEMA_MAX:
        return thema, [f"Das Thema ist zu lang (höchstens {STUNDE_THEMA_MAX} Zeichen)."]
    return thema, []


def stunde_dazu(zustand_: dict, reihe_id: str, thema: str, zeit: str) -> tuple[dict, int]:
    """Neuer Zustand mit einer Stunde mehr am Ende der Reihe und ihre Nummer."""
    stunden = dict(zustand_.get("stunden") or {})
    stunden[reihe_id] = [*(stunden.get(reihe_id) or []), {"thema": thema, "zeit": zeit}]
    return {**zustand_, "stunden": stunden}, len(stunden[reihe_id])


def stunde_aendern(zustand_: dict, reihe_id: str, nr: int, thema: str) -> dict:
    """Neuer Zustand mit neuem Thema der Stunde nr (die Stunde muss es geben)."""
    liste = [dict(s) for s in (zustand_.get("stunden") or {}).get(reihe_id) or []]
    liste[nr - 1]["thema"] = thema
    return {**zustand_, "stunden": {**(zustand_.get("stunden") or {}), reihe_id: liste}}


def stunde_zuordnen(zustand_: dict, kopf_id: str, reihe_id: str, nr: int | None) -> dict:
    """Neuer Zustand: Material kopf_id gehört zu Stunde nr der Reihe, bei None zur ganzen Reihe."""
    von = dict(zustand_.get("stunde_von") or {})
    von.pop(kopf_id, None)
    if nr:
        von[kopf_id] = {"reihe": reihe_id, "nr": nr}
    return {**zustand_, "stunde_von": von}


def stunde_nummer(wert: str | None, anzahl: int) -> int | None:
    """Nummer aus Formular oder URL: 1 bis anzahl, sonst None."""
    return int(wert) if wert and wert.isdigit() and 1 <= int(wert) <= anzahl else None


def material_je_stunde(reihe_id: str, zeilen: list[dict], stunde_von: dict[str, dict],
                       anzahl: int) -> dict[int, list[dict]]:
    """Zeilen einer Reihe je Stunde; 0 = zur ganzen Reihe (auch Entwürfe und Zuordnungen zu Stunden, die es nicht
    mehr gibt)."""
    je: dict[int, list[dict]] = {}
    for z in zeilen:
        ort = stunde_von.get(z.get("id") or "") or {}
        nr = ort.get("nr") if ort.get("reihe") == reihe_id and isinstance(ort.get("nr"), int) else 0
        je.setdefault(nr if 1 <= nr <= anzahl else 0, []).append(z)
    return je


def stunde_ansicht(reihe: dict, nr: int, stunden_: list[dict], zeilen: list[dict],
                   stunde_von: dict[str, dict]) -> dict:
    """Ansicht einer Stunde: Thema und ihr Material (zeilen: Zeilen der Reihe aus zeilen_je_reihe)."""
    einzahl, _ = stunden_wort(reihe)
    return {"titel": stunden_[nr - 1]["thema"], "unter": f"{einzahl} {nr}", "nr": nr, "wort": einzahl,
            "zeilen": material_je_stunde(reihe["id"], zeilen, stunde_von, len(stunden_)).get(nr, [])}


def stunden_auswahl(reihe: dict, stunden_: list[dict]) -> list[dict]:
    """Auswahl „Gehört zu“ in der Material-Ansicht: ganze Reihe, dann die Stunden."""
    einzahl, _ = stunden_wort(reihe)
    return [{"nr": 0, "text": "zur ganzen Reihe"}] + [
        {"nr": nr, "text": f"{einzahl} {nr}: {s['thema']}"} for nr, s in enumerate(stunden_, 1)]
