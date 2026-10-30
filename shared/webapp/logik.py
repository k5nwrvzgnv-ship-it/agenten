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


# Lias Entscheidung zu einem Entwurf, den sie selbst einsetzt (typ "entwurf"). Speichert die Web-App (zustand.py,
# "entwuerfe"), nicht die Freigabe: Entscheidungen der Freigabe trifft nach CLAUDE.md Jan, und kein Agent liest sie
# für diesen Typ. Entwürfe, die nach außen gehen (Mail usw.), bleiben bei Jan.
ENTWURF_ENTSCHEIDUNGEN = {"selbst": "Setzt du selbst ein", "nein": "Brauchst du nicht"}


def entwurf_lia_darf(entwurf: dict) -> bool:
    return entwurf.get("typ") == "entwurf"


def entwurf_zeile(entwurf: dict, jetzt: datetime) -> dict:
    entschieden = ENTWURF_ENTSCHEIDUNGEN.get(entwurf.get("lia_entscheidung") or "")
    return _zeile(entwurf_titel(entwurf), "Entwurf", zeit_text(entwurf.get("erstellt"), jetzt),
                  "Erledigt" if entschieden else "Offen", entschieden or entwurf_hinweis(entwurf),
                  entwurf_link(entwurf))


def entwuerfe_mit_entscheidung(entwuerfe: list[dict], entscheidungen: dict[str, dict]) -> list[dict]:
    """Offene Entwürfe der Freigabe mit Lias Entscheidung aus der Web-App (Feld lia_entscheidung)."""
    return [{**e, "lia_entscheidung": (entscheidungen.get(e.get("id") or "") or {}).get("stand", "")}
            if entwurf_lia_darf(e) else e for e in entwuerfe]


def entwurf_entscheiden(zustand_: dict, entwurf_id: str, stand: str, zeit: str) -> dict:
    """Neuer Zustand mit Lias Entscheidung (stand aus ENTWURF_ENTSCHEIDUNGEN) bzw. ohne (stand "")."""
    ent = dict(zustand_.get("entwuerfe") or {})
    ent.pop(entwurf_id, None)
    if stand:
        ent[entwurf_id] = {"stand": stand, "zeit": zeit}
    return {**zustand_, "entwuerfe": ent}


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
          person: str = "Lia", reihen: list[dict] | None = None, finale: set[str] | None = None,
          ersetzt: set[str] = frozenset()) -> dict:
    """Ansichtsdaten für "Heute". neue/erledigte: agentkit.auftraege, entwuerfe: agentkit.freigabe.offene().

    Je Kette eine Zeile. Abschnitt, Zeit und "Neu" richten sich nach der jüngsten Fassung; läuft etwas in der
    Kette (Nachbesserung oder Rückmeldung), steht sie unter "Läuft gerade".
    reihen (reihen_aus): jede Zeile nennt ihren Ort als Brotkrume (Fach › Klasse › Reihe).
    finale: IDs der Ursprünge, die Lia als final markiert hat: Sie warten nicht mehr, stehen unter Fertig.
    ersetzt: fehlgeschlagene Ursprünge, die Lia mit „Nochmal“ neu gestartet hat (stehen nicht mehr unter 04)."""
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
               for e in sorted(entwuerfe, key=lambda e: e.get("erstellt") or "", reverse=True)
               if not e.get("lia_entscheidung")]
              + [mit_reihe(ketten_zeile(k, jetzt, "Neu"), kopf(k)) for k in neu])
    laeuft = []
    for kette in sorted(laufend, key=lambda k: _zeitpunkt(next(a for a in k if a.get("status") == "neu"))):
        k = kopf(kette)
        start = next(a for a in kette if a.get("status") == "neu").get("erstellt")
        laufend_ = next(a for a in kette if a.get("status") == "neu")
        laeuft.append({**mit_reihe(_zeile(titel(k, {a["id"]: a for a in kette}),
                                          art(k) if k.get("agent") != "feedback" else "Rückmeldung",
                                          "seit " + zeit_text(start, jetzt) if start else "",
                                          hinweis="Arbeitet an deiner Rückmeldung" if len(kette) > 1 else "",
                                          link=ergebnis_link(k) if zeigbar(k) else ""), k),
                       "zurueck_id": laufend_["id"]})  # nur im Formular „Zurückziehen“, nie sichtbar
    rest = [mit_reihe(ketten_zeile(k, jetzt, "Final" if kopf(k)["id"] in finale else ""), kopf(k))
            for k in ergebnisse if k not in neu]
    fehlgeschlagen = [mit_reihe({**ketten_zeile(k, jetzt), "hinweis": "", "grund": kurz(grund(fassungen(k)[-1]), 300)},
                                kopf(k))
                      for k in fertige if fassungen(k)[-1].get("status") == "fehlgeschlagen"
                      and kopf(k)["id"] not in ersetzt]
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
    "zurueckgezogen": "Zurückgezogen. Deine Assistenz hört damit auf.",
    "nochmal": "Läuft noch einmal. Das Ergebnis erscheint in „Heute“.",
    "nochmal-test": "Noch einmal angelegt (Testbetrieb, es startet kein Agent).",
    "entwurf-selbst": "Erledigt: Du setzt den Entwurf selbst ein. Er wartet nicht mehr in „Heute“.",
    "entwurf-nein": "Erledigt: Du brauchst den Entwurf nicht.",
    "entwurf-offen": "Wieder offen.",
    "variante": "Die Variante ist unterwegs. Sie erscheint hier unter „Varianten“ und in „Heute“.",
    "variante-test": "Variante angelegt (Testbetrieb, es startet kein Agent).",
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


def rueckmeldung_ziel(kette: list[dict], fassung_id: str | None, nr_text: str | None,
                      seite_text: str | None) -> dict | None:
    """Worauf sich eine Rückmeldung bezieht, wenn Lia sie an einer Datei (und Seite) gibt (Jan 30.10.: Rückmeldung
    je Dokument statt je Ergebnis). fassung_id: Fassung, aus der die Datei stammt; nr_text: Index in deren
    ergebnis_dateien; seite_text: Seite im Betrachter (optional). Unbekanntes: None (dann gilt das Ganze)."""
    fassung = next((a for a in fassungen(kette) if a.get("id") == fassung_id and a.get("status") == "erledigt"), None)
    pfade = (fassung or {}).get("ergebnis_dateien") or []
    if not fassung or not (nr_text or "").isdigit() or not 0 <= int(nr_text) < len(pfade):
        return None
    nr = int(nr_text)
    seite = int(seite_text) if (seite_text or "").isdigit() and 1 <= int(seite_text) <= 999 else None
    name = Path(pfade[nr]).name  # mit Endung: der Agent findet die Datei daran
    return {"fassung": fassung["id"], "nr": nr, "seite": seite or "", "name": name,
            "text": f"„{name}“" + (f", Seite {seite}" if seite else ""),
            "fassung_name": fassung_namen(kette).get(fassung["id"], "")}


def rueckmeldung_text(text: str, datei_name_: str = "", ziel: dict | None = None) -> str:
    """Text des Auftrags an den Feedback-Dienst. ziel (rueckmeldung_ziel): Der Text beginnt mit Datei und Seite.
    Eine angehängte Datei wird eigene Fassung (agentkit.fassungen.rueckmeldung); der Feedback-Dienst liest ihre
    Word-Kommentare und hängt sie an die Nachbesserung."""
    if ziel:
        text = f"Zur Datei {ziel['text']}: {text}"
    if not datei_name_:
        return text
    return f"{text}\n\nDazu eine Datei mit Kommentaren: {dateiname_bereinigen(datei_name_)}."


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
        "rueckmeldung": (f"{ergebnis_link(k)}?offen=rueckmeldung&fassung={auftrag_id}&datei={datei['nr']}"
                         f"&seite={m}#rueckmeldung"),
    }


def entwurf(eintrag: dict, jetzt: datetime) -> dict:
    """Ansicht eines offenen Entwurfs: ganzer Text, Details aus ENTWURF_DETAILS. lia_darf: Lia kann selbst
    entscheiden (typ entwurf), entschieden: ihre Entscheidung als Text."""
    daten = eintrag.get("daten") or {}
    details = [(name, ohne_ids(str(daten[schluessel]))) for schluessel, name in ENTWURF_DETAILS.items()
               if daten.get(schluessel)]
    return {
        "titel": entwurf_titel(eintrag),
        "unter": " · ".join(x for x in ("Entwurf", zeit_text(eintrag.get("erstellt"), jetzt)) if x),
        "inhalt": ohne_ids_lang(eintrag.get("inhalt") or "").strip("\n"),
        "details": details,
        "hinweis": entwurf_hinweis(eintrag),
        "lia_darf": entwurf_lia_darf(eintrag),
        "entschieden": ENTWURF_ENTSCHEIDUNGEN.get(eintrag.get("lia_entscheidung") or "", ""),
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


# Vorlagen der Galerie „Neu“ (Board „Desktop“): nur Arten, die ein Agent wirklich baut. unterricht: Arbeitsblatt
# (docx), Folien (pptx), Arbeitsmappe (xlsx), Reihenentwurf und Lernerfolgskontrolle mit Erwartungshorizont (30.10.,
# nur Ethik); theater (30.10., nur Darstellendes Spiel): Spielfassung (ganze Runde, nur „Der nackte Wahnsinn“)
# und Szenenaufgabe. varianten: Formular zeigt „Auch als“ (der Agent baut sie im selben Lauf).
# fach: nur in Reihen dieses Fachs ("" = alle). extra: weitere Felder (Name, Frage, Platzhalter, lang, Zeilenanfang
# im Auftragstext, wie der Agent ihn liest).
VORLAGEN = {
    "arbeitsblatt": {"name": "Arbeitsblatt", "text": "Text, Merksatz, Aufgaben", "bild": "ab",
                     "frage": "Was soll drauf?", "hint": "Thema, Position, Fall, Dauer …", "varianten": True},
    "praesentation": {"name": "Präsentation", "text": "Folien für eine Stunde", "bild": "folie",
                      "frage": "Wofür?", "hint": "Ablauf der Stunde, Leitfrage …"},
    "tabelle": {"name": "Tabelle", "text": "Notentabelle, Liste (Excel), ohne Namen", "bild": "tabelle",
                "frage": "Welche Spalten?", "hint": "Nr., Note 1–5, Durchschnitt …"},
    "reihenentwurf": {"name": "Reihenentwurf", "text": "Reihenfrage, Stunden, Ziele", "bild": "tabelle",
                      "fach": "Ethik", "frage": "Thema und Reihenfrage", "hint": "oder: Reihenfrage noch offen"},
    "lek": {"name": "Lernerfolgskontrolle", "kopf": "Lernerfolgskontrolle", "text": "mit Erwartungshorizont",
            "bild": "ab", "fach": "Ethik", "frage": "Was wird geprüft?", "hint": "Positionen, Operatoren …",
            "varianten": True},
    "spielfassung": {"name": "Spielfassung (Kürzung)", "kopf": "Spielfassung", "text": "Stück auf eure Länge kürzen",
                     "bild": "skript", "agent": "theater", "quelle": "portal-theater", "fach": "Darstellendes Spiel",
                     "frage": "Welches Stück?", "hint": "Der nackte Wahnsinn", "kurz": True,
                     "hinweis": "Dauert bis zu drei Stunden. Bisher kennt deine Assistenz nur den Text von "
                                "„Der nackte Wahnsinn“.",
                     "extra": [("laenge", "Länge", "z. B. 35–40 Minuten", False, "Länge"),
                               ("spieler", "Spieler*innen", "z. B. 18", False, "Spieler*innen"),
                               ("bleiben", "Was muss bleiben?", "Szenen, Figuren, Ideen", True, "Was bleiben muss")]},
    "szene": {"name": "Szenenaufgabe", "kopf": "Szenenaufgabe", "text": "Aufgabe für eine Gruppe", "bild": "ab",
              "agent": "theater", "quelle": "portal-theater", "fach": "Darstellendes Spiel",
              "frage": "Worum geht es?", "hint": "Thema der Szene", "kurz": True,
              "extra": [("methode", "Methode", "z. B. Standbild, Chor", False, "Methode"),
                        ("szene", "Szene", "Baustein oder Stelle im Stück", False, "Szene"),
                        ("material", "Material", "Requisiten, Texte, Musik", True, "Material")]},
}
EXTRA_MAX = 1500


def vorlage_agent(art_: str) -> tuple[str, str]:
    """(Agent, quelle) einer Vorlage; ohne Vorlage der Material-Agent."""
    v = VORLAGEN.get(art_) or {}
    return v.get("agent") or NEU_AGENT, v.get("quelle") or NEU_QUELLE


def extra_werte(art_: str, form_wert) -> tuple[dict[str, str], list[str]]:
    """Weitere Felder einer Vorlage aus dem Formular (form_wert(name) -> str), bereinigt, mit Fehlern."""
    werte, fehler = {}, []
    for name, frage, _, lang, _ in (VORLAGEN.get(art_) or {}).get("extra", []):
        wert = (form_wert(name) or "").replace("\r\n", "\n").strip()
        if not lang:
            wert = " ".join(wert.split())
        if len(wert) > EXTRA_MAX:
            fehler.append(f"„{frage}“ ist zu lang (höchstens {EXTRA_MAX} Zeichen).")
        werte[name] = wert
    return werte, fehler


# Formular ohne Vorlage (Freitext wie bisher), wenn ein Auftrag ohne Art nicht angenommen wurde
VORLAGE_FREI = {"name": "Neuer Auftrag", "frage": "Was brauchst du?",
                "hint": "Zum Beispiel: Arbeitsblatt zum kategorischen Imperativ, Klasse 10, 45 Minuten, mit Fallbeispiel"}


def neu_link(reihe_id: str = "", stunde: int | None = None, art_: str = "", aus: str = "") -> str:
    """Link auf „Neu“ mit vorbelegtem Ort (und Art). aus: id einer Chat-Antwort („Daraus Auftrag machen“)."""
    teile = [f"art={art_}"] if art_ else []
    teile += [f"reihe={reihe_id}"] if reihe_id else []
    teile += [f"stunde={stunde}"] if reihe_id and stunde else []
    teile += [f"aus={aus}"] if chat_id_gueltig(aus) else []
    return "/neu" + ("?" + "&".join(teile) if teile else "")


def text_aus_chat(eintrag: dict | None) -> str:
    """Vorbelegter Wunsch aus einer Chat-Antwort: Lias Frage und die Antwort, ohne Markdown-Sternchen."""
    if not eintrag:
        return ""
    antwort = _FETT.sub(r"\1", eintrag.get("antwort") or "").strip()
    return f"{eintrag.get('frage') or ''}\n\n{antwort}".strip()[:NEU_TEXT_MAX]


def galerie(reihe_id: str = "", stunde: int | None = None, fach: str = "", aus: str = "") -> list[dict]:
    """Vorlagen für einen Ort: alle für alle Fächer, dazu die des Fachs der Reihe (ohne Ort: alle)."""
    return [{"art": k, **v, "link": neu_link(reihe_id, stunde, k, aus)} for k, v in VORLAGEN.items()
            if not v.get("fach") or not fach or v["fach"] == fach]


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
REIHE_TEXTE = ("id", "fach", "klasse", "titel", "reihenfrage", "lerngruppe", "notizen", "stand", "schuljahr")
REIHE_LISTEN = ("behandelt", "merksaetze", "bisherige_reihen", "agenten")
REIHE_STAENDE = ("laufend", "abgeschlossen")
# [[reihe.stunde]] wie lia/unterricht/reihen.py (_stunden_pruefen): nr ab 1, thema, optional marke
STUNDE_FELDER = ("nr", "thema", "marke")
STUNDE_MARKEN = ("UB", "Prüfung")
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
        falsch = sorted(k for k in e if (_stunden_falsch(e[k]) if k == "stunde" else (
                        k not in REIHE_TEXTE + REIHE_LISTEN
                        or (k in REIHE_TEXTE and not isinstance(e[k], str))
                        or (k in REIHE_LISTEN and not (isinstance(e[k], list)
                                                       and all(isinstance(x, str) for x in e[k]))))))
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
            schuljahr = (e.get("schuljahr") or "").strip()
            # Archiv (Regel R11): abgeschlossene Reihe eines genannten Schuljahrs; die Klasse trägt dann das Jahr,
            # damit „Kurs 11 · 2025/26“ nicht mit dem laufenden Kurs 11 zusammenfällt
            archiv = bool(schuljahr) and stand == "abgeschlossen"
            gruppe = gruppe_name(klasse) + (f" · {schuljahr}" if archiv else "")
            reihen.append({
                "id": rid, "fach": fach, "fach_id": kennung(fach), "klasse": klasse, "gruppe": gruppe,
                "gruppe_id": kennung(fach, klasse, schuljahr) if archiv else kennung(fach, klasse),
                "titel": titel_ or gruppe_name(klasse), "schuljahr": schuljahr, "archiv": archiv,
                "reihenfrage": (e.get("reihenfrage") or "").strip(), "behandelt": list(e.get("behandelt") or []),
                "laufend": stand == "laufend", "agenten": list(e.get("agenten") or []),
                "stunden": [{"thema": s["thema"].strip(), "marke": s.get("marke", ""), "aus_datei": True}
                            for s in sorted(e.get("stunde") or [], key=lambda s: s["nr"])],
            })
    return reihen, fehler


def _stunden_falsch(stunden) -> bool:
    """Stimmt [[reihe.stunde]] nicht (Regeln wie lia/unterricht/reihen.py)? Die Nummern müssen 1 bis n sein, weil
    die App Stunden nach ihrem Platz zählt."""
    if not isinstance(stunden, list) or not all(isinstance(s, dict) for s in stunden):
        return True
    for s in stunden:
        if set(s) - set(STUNDE_FELDER) or not isinstance(s.get("nr"), int) or isinstance(s["nr"], bool) \
                or not isinstance(s.get("thema"), str) or not s["thema"].strip() \
                or ("marke" in s and s["marke"] not in STUNDE_MARKEN):
            return True
    return sorted(s["nr"] for s in stunden) != list(range(1, len(stunden) + 1))


def reihe_stunden(reihe: dict, zustand_: dict) -> list[dict]:
    """Stunden einer Reihe: aus reihen.toml, wenn dort welche stehen (dann pflegt sie die Datei), sonst die, die
    die Web-App selbst speichert (zustand.py)."""
    return reihe.get("stunden") or (zustand_.get("stunden") or {}).get(reihe["id"]) or []


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
                   art_: str = "", extra: dict[str, str] | None = None, auch_als: list[str] = ()) -> str:
    """Auftragstext für den Agenten: Art vorn („Arbeitsblatt: …“, „Spielfassung: …“), weitere Felder als Zeilen
    („Länge: …“), gewählte Reihe und Stunde (Nummer, Thema) am Ende, damit er sie ohne eigenen Code im Prompt hat."""
    vorlage = VORLAGEN.get(art_)
    if vorlage:
        text = f"{vorlage.get('kopf') or vorlage['name']}: {text}"
        for name, _, _, _, anfang in vorlage.get("extra", []):
            if (extra or {}).get(name):
                text += f"\n{anfang}: {extra[name]}"
        if auch_als and vorlage.get("varianten"):  # Zeile, die lia/unterricht liest (material.VARIANTEN_ZEILE)
            text += "\nAuch als: " + ", ".join(VARIANTEN[v]["wort"] for v in auch_als if v in VARIANTEN)
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
                    eigene: dict[str, list[dict]] | None = None,
                    ausblenden: set[str] = frozenset()) -> dict[str, list[dict]]:
    """Zeilen je Reihen-Kennung (OHNE_REIHE für den Rest): offene Entwürfe, dann je Kette eine Zeile wie in
    "Heute" (neueste zuerst), mit Marke Offen bzw. dem Stand des Materials (material_marke).
    finale, eigene: was die Web-App selbst speichert (zustand.py). ausblenden: IDs von Varianten, sie stehen beim
    Original (varianten_leiste)."""
    zeilen_je: dict[str, list] = {}
    for e in sorted(entwuerfe or [], key=lambda e: e.get("erstellt") or "", reverse=True):
        r = reihe_von(e, reihen)
        zeilen_je.setdefault(r["id"] if r else OHNE_REIHE, []).append(entwurf_zeile(e, jetzt))
    for kette in sorted((k for k in ketten(auftraege_) if fassungen(k)),
                        key=lambda k: _zeitpunkt(fassungen(k)[-1]), reverse=True):
        if kopf(kette)["id"] in ausblenden:
            continue
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
                  stunde_von: dict[str, dict] | None = None, ausblenden: set[str] = frozenset()) -> dict:
    """Ansicht einer Reihe: Reihenfrage, schon Behandeltes, Material und Entwürfe zur ganzen Reihe, darunter die
    Stunden (bzw. Proben) mit ihrem Material. stunden_, stunde_von: aus zustand.py (die Web-App speichert sie)."""
    zeilen = zeilen_je_reihe(reihen, auftraege_, jetzt, entwuerfe, finale, eigene, ausblenden).get(reihe["id"], [])
    je_stunde = material_je_stunde(reihe["id"], zeilen, stunde_von or {}, len(stunden_))
    einzahl, mehrzahl = stunden_wort(reihe)
    return {"titel": reihe["titel"], "unter": f"{reihe['fach']} · {reihe['gruppe']}"
                                              + ("" if reihe["laufend"] else " · abgeschlossen"),
            "reihenfrage": reihe["reihenfrage"], "behandelt": "; ".join(reihe["behandelt"]),
            "zeilen": je_stunde.get(0, []), "wort": einzahl, "wort_mehrzahl": mehrzahl,
            "stunden_neu": "" if reihe.get("stunden") else reihe_link(reihe) + "/stunden",
            "stunden": [{"nr": nr, "titel": s["thema"], "link": stunde_link(reihe, nr), "marke": s.get("marke", ""),
                         "unter": ", ".join(z["titel"] for z in je_stunde.get(nr, [])) or "noch leer"}
                        for nr, s in enumerate(stunden_, 1)]}


def reihe_link(reihe: dict) -> str:
    return f"/reihe/{reihe['id']}"


def klasse_link(reihe: dict) -> str:
    """Link zur Klasse/zum Kurs einer Reihe (Kennung aus Fach und Klasse)."""
    return f"/klasse/{reihe['gruppe_id']}"


def fach_aktiv(fach_id: str) -> str:
    return "fach:" + fach_id


def fach_ansicht(fach_id: str, reihen: list[dict], zeilen_je: dict[str, list[dict]]) -> dict | None:
    """Ansicht eines Fachs (nur lesend): Klassen/Kurse mit Zahl der Reihen. Fach-Material (RLP, Operatoren,
    Referendariat, Regel R3/R6) steht in keiner Datei. Unbekannt: None."""
    eigene = [r for r in reihen if r["fach_id"] == fach_id]
    if not eigene:
        return None
    gruppen: dict[str, list[dict]] = {}
    for r in eigene:
        gruppen.setdefault(r["gruppe_id"], []).append(r)
    zeilen = []
    for rs in gruppen.values():
        laufend = [r["titel"] for r in rs if r["laufend"]]
        n = sum(len(zeilen_je.get(r["id"], [])) for r in rs)
        zeilen.append({"titel": rs[0]["gruppe"], "link": klasse_link(rs[0]),
                       "unter": ("Läuft: " + ", ".join(laufend)) if laufend else "keine laufende Reihe",
                       "hinweis": f"{len(rs)} {'Reihe' if len(rs) == 1 else 'Reihen'} · "
                                  + ("noch nichts" if n == 0 else "1 Sache" if n == 1 else f"{n} Sachen"),
                       "marke": ""})
    return {"titel": eigene[0]["fach"], "unter": "Fach", "zeilen": zeilen}


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


def baum(reihen: list[dict], anzahl_wartet: int, aktiv: str = "", stunden: dict[str, list[dict]] | None = None,
         aktiv_stunde: int | None = None) -> list[dict]:
    """Linke Spalte: oben "Heute" mit der Zahl, was wartet, dann je Fach die Klassen/Kurse und ihre Reihen, unten
    „Mehr“ mit Vorlagen und Ich. Die gezeigte Reihe klappt ihre Stunden aus (stunden: je Reihen-Kennung, aus
    zustand.py; aktiv_stunde: die gezeigte Stunde). Fach-Überschriften verlinken auf die Fach-Ansicht.
    aktiv: "heute", "vorlagen", "ich", fach_aktiv(…), die Kennung der gezeigten Reihe oder klasse_aktiv(…). art: "eintrag" (Link), "fach"
    (Überschrift) oder "gruppe" (Klasse/Kurs, Link zur Klassen-Ansicht)."""
    eintraege = [{"art": "eintrag", "text": "Heute", "link": "/", "tiefe": 0, "zahl": anzahl_wartet or "",
                  "aktiv": aktiv == "heute"}]
    faecher: dict[str, dict[str, list[dict]]] = {}
    for r in reihen:
        faecher.setdefault(r["fach"], {}).setdefault(r["gruppe"], []).append(r)
    for fach, gruppen in faecher.items():
        fid = next(iter(gruppen.values()))[0]["fach_id"]
        eintraege.append({"art": "fach", "text": fach, "link": f"/fach/{fid}", "aktiv": aktiv == fach_aktiv(fid)})
        # Archiv (Regel R11) nach den laufenden Klassen, eingeklappt: Reihen nur, wenn man in ihnen ist
        for gruppe, reihen_ in sorted(gruppen.items(), key=lambda g: g[1][0]["archiv"]):
            archiv = reihen_[0]["archiv"]
            drin = aktiv in {klasse_aktiv(reihen_[0]["gruppe_id"]), *(r["id"] for r in reihen_)}
            eintraege.append({"art": "gruppe", "text": ("Archiv: " if archiv else "") + gruppe, "tiefe": 0,
                              "link": klasse_link(reihen_[0]),
                              "aktiv": aktiv == klasse_aktiv(reihen_[0]["gruppe_id"])})
            if archiv and not drin:
                continue
            for r in reihen_:
                eintraege.append({"art": "eintrag", "text": r["titel"] + ("" if r["laufend"] else " (abgeschlossen)"),
                                  "link": reihe_link(r), "tiefe": 1, "zahl": "",
                                  "aktiv": aktiv == r["id"] and not aktiv_stunde})
                if aktiv == r["id"]:
                    eintraege += [{"art": "eintrag", "text": f"{nr}  {s['thema']}", "link": stunde_link(r, nr),
                                   "tiefe": 2, "zahl": "", "aktiv": aktiv_stunde == nr}
                                  for nr, s in enumerate((stunden or {}).get(r["id"]) or [], 1)]
    eintraege += [{"art": "fach", "text": "Mehr"},
                  {"art": "eintrag", "text": "Vorlagen", "link": "/vorlagen", "tiefe": 0, "zahl": "",
                   "aktiv": aktiv == "vorlagen"},
                  {"art": "eintrag", "text": "Ich", "link": "/ich", "tiefe": 0, "zahl": "", "aktiv": aktiv == "ich"}]
    return eintraege


def krumen(hier: str = "", reihe: dict | None = None, ueber: dict | None = None) -> dict:
    """Brotkrumen über dem Inhalt: Teile mit Link (Fach, Klasse, Reihe), dann die Seite selbst.
    Ohne Angaben "Heute"; nur reihe: die Reihen-Ansicht; reihe und hier: eine Seite in der Reihe; nur hier: eine
    Seite ohne Reihe unter "Heute". ueber ({"text", "link"}): eine Seite dazwischen, z. B. das Ergebnis über dem
    Seiten-Betrachter."""
    hier = kurz(hier, KRUME_LANG)
    extra = [{"text": kurz(ueber["text"], KRUME_LANG), "link": ueber["link"]}] if ueber and hier else []
    if reihe is None:
        return {"teile": [{"text": "Heute", "link": "/"}, *extra] if hier else [], "hier": hier or "Heute"}
    teile = [{"text": reihe["fach"], "link": f"/fach/{reihe['fach_id']}"},
             {"text": reihe["gruppe"], "link": klasse_link(reihe)}]
    if not hier:
        return {"teile": teile, "hier": reihe["titel"]}
    return {"teile": [*teile, {"text": reihe["titel"], "link": reihe_link(reihe)}, *extra], "hier": hier}


def krumen_klasse(reihe: dict) -> dict:
    """Brotkrumen der Klassen-Ansicht: Fach › Klasse (reihe: irgendeine Reihe der Klasse)."""
    return {"teile": [{"text": reihe["fach"], "link": f"/fach/{reihe['fach_id']}"}], "hier": reihe["gruppe"]}


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
    marke = stunden_[nr - 1].get("marke") or ""
    return {"titel": stunden_[nr - 1]["thema"], "unter": f"{einzahl} {nr}" + (f" · {marke}" if marke else ""),
            "nr": nr, "wort": einzahl, "aus_datei": bool(stunden_[nr - 1].get("aus_datei")),
            "zeilen": material_je_stunde(reihe["id"], zeilen, stunde_von, len(stunden_)).get(nr, [])}


def stunden_auswahl(reihe: dict, stunden_: list[dict]) -> list[dict]:
    """Auswahl „Gehört zu“ in der Material-Ansicht: ganze Reihe, dann die Stunden."""
    einzahl, _ = stunden_wort(reihe)
    return [{"nr": 0, "text": "zur ganzen Reihe"}] + [
        {"nr": nr, "text": f"{einzahl} {nr}: {s['thema']}"} for nr, s in enumerate(stunden_, 1)]


# Seiten „Vorlagen“ und „Ich“ (Board „Desktop“), nur lesend
_FEEDBACK_HERKUNFT = re.compile(r"\s*\(Feedback [^)]*\)")
_ANLASS = re.compile(r"\s*\(Anlass:\s*([^)]*)\)\s*$")
_REGEL_DATUM = re.compile(r"^(\d{1,2}\.\d{1,2}\.\d{4}):\s*")


def gestaltung(profil_: dict) -> list[dict]:
    """Zeilen „Gestaltung“ aus dem Profil des Material-Agenten (Schrift, Größe, farbige Kästen, Folien)."""
    if not profil_:
        return []
    farben = profil_.get("farben") or {}
    kaesten = [n for k, n in (("thema", "Thema"), ("merksatz", "Merksatz"), ("material", "Material")) if k in farben]
    blatt = [x for x in (profil_.get("schrift"),
                         f"{profil_['schriftgroesse_pt']} pt" if profil_.get("schriftgroesse_pt") else "") if x]
    zeilen = []
    if blatt or kaesten:
        zeilen.append({"titel": "Arbeitsblatt", "marke": "alle Fächer", "unter": " ".join(blatt) + (
            (", farbig hinterlegt: " if blatt else "Farbig hinterlegt: ") + ", ".join(kaesten) if kaesten else "")})
    if profil_.get("folien_schrift"):
        zeilen.append({"titel": "Präsentation", "marke": "alle Fächer", "unter": str(profil_["folien_schrift"])
                       + (", mit Akzentfarbe" if "akzent" in farben else "")})
    return zeilen


def _regel_zeilen(text: str, ueberschrift: str) -> list[str]:
    """Listenzeilen ("- …") unter einer Überschrift "## …" bis zur nächsten."""
    zeilen, drin = [], False
    for z in text.splitlines():
        if z.startswith("## "):
            drin = z[3:].strip() == ueberschrift
        elif drin and z.startswith("- "):
            zeilen.append(z[2:].strip())
    return zeilen


def regel(zeile: str) -> dict | None:
    """Eine Regelzeile für Lia: Text, darunter Datum und Anlass; ohne Feedback-ID. Platzhalter: None."""
    zeile = _FEEDBACK_HERKUNFT.sub("", zeile).strip()
    if not zeile or zeile.startswith("("):
        return None
    datum = _REGEL_DATUM.match(zeile)
    zeile = zeile[datum.end():] if datum else zeile
    anlass = _ANLASS.search(zeile)
    text = zeile[:anlass.start()] if anlass else zeile
    return {"titel": ohne_ids(text), "unter": " · ".join(x for x in (
        datum.group(1) if datum else "", ohne_ids(anlass.group(1)) if anlass else "") if x)}


def regeln_aus(texte: list[tuple[str, str]]) -> list[dict]:
    """Gruppen für „Ich“: allgemeine Regeln (regeln.md, Abschnitt Regeln), dann je Agent die gelernten Regeln
    (STATUS.md, Abschnitt Gelernte Regeln) unter Lias Wort für die Art („Für Material“)."""
    gruppen = []
    for agent, text in texte:
        zeilen = [r for r in map(regel, _regel_zeilen(text, "Gelernte Regeln" if agent else "Regeln")) if r]
        if zeilen:
            name = "Für alles" if not agent else "Für " + ARTEN_NACH_AGENT.get(agent, "Weiteres")
            gruppen.append({"titel": name, "regeln": zeilen})
    return gruppen


# Varianten (Board „Desktop“, Regel R2: ein Material mit Varianten, keine neuen Materialien). Kein Agent baut
# Varianten selbst (unterricht liefert genau eine Datei je Auftrag). Darum ist jede Variante ein eigener Auftrag an
# den Material-Agenten mit der Datei des Originals als Anhang; die Web-App merkt sich, was zusammengehört
# (zustand.py: varianten, varianten_wunsch). Türkisch braucht Jan nicht (30.10., Leitfaden: eingestellt).
VARIANTEN = {
    "einfach": {"name": "einfach", "wort": "einfach",
                "auftrag": "sprachlich einfacher: kürzere Sätze, schwierige Wörter erklärt, gleiche Inhalte und Aufgaben"},
    "hilfekarten": {"name": "mit Hilfekarten", "wort": "mit Hilfekarten",
                    "auftrag": "mit Hilfekarten: gleiche Aufgaben, dazu gestufte Hilfen je Aufgabe"},
    "level": {"name": "Level 1–3", "wort": "Level",
              "auftrag": "in drei Niveaus (Level 1 bis 3): gleiche Inhalte, unterschiedlich schwer"},
}
VARIANTE_ENDUNGEN = (".docx", ".pptx")  # Varianten von Blättern und Folien, nicht von Tabellen oder PDFs
VARIANTE_EXTRA_MAX = 500


def varianten_waehlen(werte: list[str]) -> list[str]:
    """Bekannte Varianten aus dem Formular „Auch als“, in fester Reihenfolge, ohne Doppelte."""
    return [k for k in VARIANTEN if k in werte]


def variante_pruefen(art_: str, extra: str) -> tuple[str, list[str]]:
    extra = " ".join((extra or "").split())
    fehler = [] if art_ in VARIANTEN else ["Wähl eine Variante aus."]
    if len(extra) > VARIANTE_EXTRA_MAX:
        fehler.append(f"Der Text ist zu lang (höchstens {VARIANTE_EXTRA_MAX} Zeichen).")
    return extra, fehler


def variante_text(art_: str, titel_: str, extra: str = "") -> str:
    """Auftragstext einer Variante (die Reihe hängt text_mit_reihe an)."""
    v = VARIANTEN[art_]
    return (f"Variante „{v['name']}“ von „{titel_}“: Bau das angehängte Blatt als Variante, {v['auftrag']}. "
            "Gestaltung und Dateiart bleiben." + (f" Dazu: {extra}" if extra else ""))


def variante_dazu(zustand_: dict, kopf_id: str, art_: str, auftrag_id: str, zeit: str) -> dict:
    """Neuer Zustand: auftrag_id ist die Variante art_ von kopf_id. Ein erfüllter Wunsch fällt weg."""
    varianten = dict(zustand_.get("varianten") or {})
    varianten[kopf_id] = [*(varianten.get(kopf_id) or []), {"art": art_, "auftrag": auftrag_id, "zeit": zeit}]
    wunsch = dict(zustand_.get("varianten_wunsch") or {})
    rest = [w for w in wunsch.get(kopf_id) or [] if w != art_]
    if rest:
        wunsch[kopf_id] = rest
    else:
        wunsch.pop(kopf_id, None)
    return {**zustand_, "varianten": varianten, "varianten_wunsch": wunsch}


def wunsch_setzen(zustand_: dict, kopf_id: str, arten: list[str]) -> dict:
    """Neuer Zustand mit Lias Wunsch „Auch als“ für ein Material, das noch läuft."""
    wunsch = dict(zustand_.get("varianten_wunsch") or {})
    if arten:
        wunsch[kopf_id] = list(arten)
    return {**zustand_, "varianten_wunsch": wunsch}


def variante_von(zustand_: dict, auftrag_id: str) -> tuple[str, str] | None:
    """(ID des Originals, Art), wenn auftrag_id eine Variante ist."""
    for kopf_id, liste in (zustand_.get("varianten") or {}).items():
        for v in liste:
            if v.get("auftrag") == auftrag_id:
                return kopf_id, v.get("art") or ""
    return None


def varianten_ids(zustand_: dict) -> set[str]:
    return {v.get("auftrag") for liste in (zustand_.get("varianten") or {}).values() for v in liste}


def varianten_leiste(zustand_: dict, kopf_id: str, auftraege_: list[dict], jetzt: datetime,
                     finale: set[str] = frozenset()) -> dict:
    """Leiste „Varianten“ in der Material-Ansicht: normal (dieses Material), je Variante Name, Link und Stand,
    dazu gewünschte, noch nicht angeforderte Varianten. Leer, wenn es nichts davon gibt."""
    gemacht = []
    for v in (zustand_.get("varianten") or {}).get(kopf_id) or []:
        kette = kette_von(v.get("auftrag") or "", auftraege_)
        if not kette or v.get("art") not in VARIANTEN:
            continue  # zurückgezogen oder unbekannt
        k = kopf(kette)  # läuft die Variante noch, hat sie keine Ansicht (wie in Heute)
        gemacht.append({"name": VARIANTEN[v["art"]]["name"], "link": ergebnis_link(k) if zeigbar(k) else "",
                        "marke": material_marke(kette, jetzt, finale) if fassungen(kette) else ""})
    gewuenscht = [{"art": w, "name": VARIANTEN[w]["name"]}
                  for w in (zustand_.get("varianten_wunsch") or {}).get(kopf_id) or [] if w in VARIANTEN]
    return {"gemacht": gemacht, "gewuenscht": gewuenscht}


# „Nochmal“ bei einem Fehlschlag (Board „Desktop“, Heute 03): derselbe Auftrag noch einmal, nur für den
# Material-Agenten und nur ohne Anhänge (die liegen nach dem ersten Versuch im Agent-Ordner, nicht mehr hier).
def nochmal_moeglich(kette: list[dict]) -> bool:
    f = fassungen(kette)
    letzte = f[-1] if f else {}
    return (letzte.get("status") == "fehlgeschlagen" and letzte.get("agent") == NEU_AGENT
            and not letzte.get("dateien") and not any(a.get("status") == "neu" for a in kette))


def nochmal_felder(kette: list[dict]) -> dict:
    """Felder für agentkit.auftraege.neuer_auftrag: Text, quelle, bezug und sitzung des letzten Versuchs, Reihe
    des Ursprungs. Ein fehlgeschlagener Ursprung bekommt keinen bezug (sonst hielte ihn der Agent für eine
    Nachbesserung); die Web-App merkt sich dann, dass der neue Auftrag ihn ersetzt (zustand.py: ersetzt)."""
    letzte, k = fassungen(kette)[-1], kopf(kette)
    return {"text": letzte.get("text") or "", "quelle": letzte.get("quelle") or NEU_QUELLE,
            "bezug": letzte.get("bezug"), "sitzung": letzte.get("sitzung"), "reihe": k.get("reihe")}


# Spalte „Fragen“ (Board „Desktop“): Chat-Agent lia/chat über seine Schnittstelle (Warteschlange in Dateien).
# Die Antworten sind Markdown (fett, Listen); hier nur so viel davon, wie die Spalte zeigt, ohne HTML von außen.
_FETT = re.compile(r"\*\*(.+?)\*\*")
VERLAUF_ANZAHL = 6  # so viele Fragen zeigt die Spalte (der Agent hält 30 Tage)


def _teile(zeile: str) -> list[dict]:
    teile, pos = [], 0
    for m in _FETT.finditer(zeile):
        if m.start() > pos:
            teile.append({"text": zeile[pos:m.start()], "fett": False})
        teile.append({"text": m.group(1), "fett": True})
        pos = m.end()
    if pos < len(zeile):
        teile.append({"text": zeile[pos:], "fett": False})
    return teile


def markdown_bloecke(text: str) -> list[dict]:
    """Antworttext in Blöcke: {"absatz": [Teile]} oder {"punkte": [[Teile]]} (Zeilen mit "- ", "* " oder "1. "),
    Teile {"text", "fett"} (**…**). Überschriften (#) werden fette Absätze."""
    bloecke: list[dict] = []
    for zeile in (text or "").replace("\r\n", "\n").split("\n"):
        z = zeile.strip()
        punkt = re.match(r"^(?:[-*]|\d+[.)])\s+(.*)$", z)
        if punkt:
            if not bloecke or "punkte" not in bloecke[-1]:
                bloecke.append({"punkte": []})
            bloecke[-1]["punkte"].append(_teile(punkt.group(1)))
        elif z.startswith("#"):
            bloecke.append({"absatz": [{"text": z.lstrip("#").strip(), "fett": True}]})
        elif z:
            if bloecke and "absatz" in bloecke[-1] and bloecke[-1].get("weiter"):
                bloecke[-1]["absatz"] += [{"text": " ", "fett": False}, *_teile(z)]
            else:
                bloecke.append({"absatz": _teile(z), "weiter": True})
        elif bloecke:
            bloecke[-1].pop("weiter", None)
    for b in bloecke:
        b.pop("weiter", None)
    return bloecke


def fragen_eintrag(e: dict) -> dict:
    """Eine Frage mit Antwort für die Spalte (aus verlauf() bzw. antwort_holen() des Chat-Agenten)."""
    return {"id": e.get("id") or "", "frage": e.get("frage") or "", "chip": e.get("chip") or "",
            "reihe": e.get("reihe") or "", "ok": e.get("ok", True), "gruendlich": bool(e.get("gruendlich")),
            "bloecke": markdown_bloecke(e.get("antwort") if "antwort" in e else e.get("text") or "")}


def fragen_spalte(verlauf: list[dict], reihe: dict | None, stunde: tuple[int, str] | None) -> dict:
    """Werte für die Spalte: Ort als Chip („Ich weiß: …“), die letzten Fragen (neueste unten) mit Trennlinie, wenn
    die Reihe wechselt."""
    eintraege = [fragen_eintrag(e) for e in verlauf[-VERLAUF_ANZAHL:]]
    vorher = None
    for e in eintraege:
        e["wechsel"] = vorher is not None and e["reihe"] != vorher
        vorher = e["reihe"]
    return {"chip": ort_text(reihe, stunde), "reihe": reihe["id"] if reihe else "",
            "stunde": stunde[0] if stunde else "", "verlauf": eintraege}


def frage_ort(reihe: dict | None, stunde: tuple[int, str] | None, materialien: list[str]) -> dict | None:
    """Ort für schnittstelle.frage_stellen: nur die Reihe ist Pflicht."""
    if not reihe:
        return None
    ort = {"reihe": reihe["id"], "chip": ort_text(reihe, stunde), "materialien": materialien[:20]}
    if stunde:
        ort |= {"stunde": stunde[0], "stunde_thema": stunde[1]}
    return ort


def zurueck_pfad(wert: str | None) -> str:
    """Seite, auf die es nach der Frage zurückgeht: nur ein Pfad dieser App, sonst „Heute“."""
    wert = (wert or "").split("?", 1)[0].split("#", 1)[0]
    return wert if re.fullmatch(r"/[A-Za-z0-9/_\-]*", wert) and not wert.startswith("//") else "/"


FRAGE_FEHLER = {"leer": "Schreib kurz deine Frage.", "lang": "Die Frage ist zu lang (höchstens 4.000 Zeichen).",
                "veraltet": "Die Seite war veraltet. Bitte schick die Frage noch einmal.",
                "technik": "Die Frage kam nicht an. Sag Jan bitte Bescheid."}


def chat_id_gueltig(wert: str | None) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{12}", wert or ""))


def port_pruefen(wert: str | None) -> int | None:
    """WEBAPP_PORT: Zahl von 1024 bis 65535, sonst None (dann Unix-Socket). Falsche Angabe: ValueError."""
    if not wert:
        return None
    if not wert.isdigit() or not 1024 <= int(wert) <= 65535:
        raise ValueError(f"WEBAPP_PORT {wert!r}: Zahl von 1024 bis 65535")
    return int(wert)
