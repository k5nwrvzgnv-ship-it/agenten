"""Masken der Struktur-Pflege (docs/struktur-pflege-plan.md, Abschnitte 2a, 4, 5, 6; Bauschritt 5): reine Logik ohne
Dateien und Netz, getestet in tests/test_pflege.py. Formularwerte werden hier zu Argumenten für
agentkit.strukturpflege; geschrieben wird nur dort, die App schreibt nie selbst in reihen.toml.

Regeln aus dem Plan: Beim Anlegen nur Pflichtfelder, alles andere über „Bearbeiten“. Fehlertexte in Lias Worten,
nichts wird gespeichert, solange ein Pflichtfeld fehlt. Die Lerngruppe steht in keinem Text, den diese Datei baut
(Abschnitt 6, Testregel 21).
"""

import re
from collections.abc import Callable
from datetime import date, datetime

from agentkit import struktur, termine
from agentkit import strukturpflege as sp

LAENGE = sp.LAENGE  # gleiche Grenzen wie agentkit, im Formular als maxlength
TAG_NAMEN = {"Mo": "Montag", "Di": "Dienstag", "Mi": "Mittwoch", "Do": "Donnerstag", "Fr": "Freitag",
             "Sa": "Samstag"}
STAENDE = {"geplant": "In Planung", "laufend": "Läuft", "abgeschlossen": "Abgeschlossen"}
MARKEN = struktur.MARKEN
BUNDESLAENDER = dict(sorted(termine.BUNDESLAENDER.items(), key=lambda kv: kv[1]))
STUNDEN = tuple(range(termine.STUNDE_MAX + 1))  # Unterrichtsstunde, auch eine 0. Stunde
ZEILEN_MIN = 2  # so viele Zeilen hat der Stundenplan in der Maske mindestens; „+ weiterer Termin“ gibt eine mehr
ZEILEN_MAX = 12
LERNGRUPPE_HINWEIS = ("Nur die Gruppe beschreiben. Keine Namen, keine Angaben zu einzelnen Schüler*innen "
                      "(Diagnosen, Förderbedarf, Noten).")
THEMA_OFFEN = "Thema offen"
PFLICHT = {
    "fach": "Wie heißt das Fach? Bitte gib einen Namen ein.",
    "klasse": "Wie heißt die Klasse oder der Kurs? Zum Beispiel „8“ oder „Kurs 11“.",
    "reihe": "Wie heißt die Reihe? Bitte gib einen Titel ein.",
}
FELD = {"name": "Der Name", "kurzform": "Die Kurzform", "titel": "Der Titel", "thema": "Das Thema",
        "reihenfrage": "Die Reihenfrage", "notizen": "Die Notizen", "behandelt": "Eine Zeile bei „Schon behandelt“",
        "merksaetze": "Ein Merksatz", "lerngruppe": "Die Beschreibung der Lerngruppe"}
NEU_LADEN = "Inzwischen hat sich hier etwas geändert. Bitte lade die Seite neu und versuch es noch einmal."
GIBT_ES_NICHT = "Das gibt es inzwischen nicht mehr. Bitte lade die Seite neu."
BUNDESLAND_FEHLT = "Für den Stundenplan brauche ich dein Bundesland (wegen der Ferien und Feiertage)."
FERIEN_FEHLEN = ("Für das Schuljahr {schuljahr} kenne ich die Ferien noch nicht. Bitte „ab“ und „bis“ angeben oder "
                 "Jan Bescheid sagen.")
VERALTET = "Die Seite war veraltet. Bitte lade sie neu und versuch es noch einmal."
TERMIN_BELEGT = "Ein gewählter Termin ist inzwischen belegt. Bitte lade die Seite neu und wähl noch einmal."
_SCHULJAHR = re.compile(r"(\d{4})/(\d{2})")
_DATUM = re.compile(r"\d{4}-\d{2}-\d{2}")


# --- Eingaben ------------------------------------------------------------------------------------------------------

def text(wert: str | None, feld: str, pflicht: str = "") -> tuple[str, list[str]]:
    """Text aus dem Formular, ohne Rand. pflicht: Fehlertext, wenn er leer ist."""
    wert = (wert or "").strip()
    if pflicht and not wert:
        return wert, [pflicht]
    if len(wert) > LAENGE.get(feld, 5000):
        return wert, [f"{FELD[feld]} ist zu lang (höchstens {LAENGE.get(feld, 5000)} Zeichen)."]
    return wert, []


def zeilen(wert: str | None, feld: str) -> tuple[list[str], list[str]]:
    """Liste aus einem Textfeld, je Zeile ein Eintrag (Schon behandelt, Merksätze)."""
    liste = [z.strip() for z in (wert or "").splitlines() if z.strip()]
    zu_lang = [z for z in liste if len(z) > LAENGE.get(feld, 5000)]
    return liste, [f"{FELD[feld]} ist zu lang (höchstens {LAENGE.get(feld, 5000)} Zeichen)."] if zu_lang else []


def schuljahr(wert: str | None) -> tuple[str, list[str]]:
    wert = (wert or "").strip()
    m = _SCHULJAHR.fullmatch(wert)
    if not (m and (int(m[1]) + 1) % 100 == int(m[2])):
        return wert, ["Schreib das Schuljahr bitte so: 2026/27."]
    return wert, []


def schuljahr_vorschlag(heute: date, kalender: termine.Kalender | None = None) -> str:
    """Vorbelegung: aus den Ferien des Bundeslands (die Sommerferien zählen schon zum nächsten), sonst ab August."""
    if kalender is not None:
        try:
            return kalender.schuljahr_von(heute)
        except termine.TermineFehler:
            pass
    jahr = heute.year if heute.month >= 8 else heute.year - 1
    return f"{jahr}/{(jahr + 1) % 100:02d}"


def naechstes_schuljahr(wert: str) -> str:
    m = _SCHULJAHR.fullmatch(wert or "")
    return f"{int(m[1]) + 1}/{(int(m[2]) + 1) % 100:02d}" if m else ""


def datum(wert: str | None) -> date | None:
    """Datum aus einem Feld type=date ("2026-11-03"), sonst None."""
    wert = (wert or "").strip()
    if not _DATUM.fullmatch(wert):
        return None
    try:
        return date.fromisoformat(wert)
    except ValueError:
        return None


def zeilen_zahl(wert: str | None, mehr: bool = False) -> int:
    """Zahl der Stundenplan-Zeilen aus dem Formular; mehr: „+ weiterer Termin“ gedrückt."""
    n = int(wert) if (wert or "").isdigit() else ZEILEN_MIN
    return max(ZEILEN_MIN, min(ZEILEN_MAX, n + (1 if mehr else 0)))


def stundenplan(wert: Callable[[str], str], anzahl: int) -> tuple[list[dict], list[dict], list[str]]:
    """Zeilen des Stundenplans aus dem Formular (Felder tag-n, stunde-n, laenge-n): (Einträge ohne ab/bis, Zeilen
    zum erneuten Zeigen, Fehler). Leere Zeilen zählen nicht."""
    eintraege, gezeigt, fehler = [], [], []
    for n in range(anzahl):
        tag, stunde, laenge = wert(f"tag-{n}").strip(), wert(f"stunde-{n}").strip(), wert(f"laenge-{n}").strip()
        gezeigt.append({"tag": tag, "stunde": stunde, "laenge": laenge or "1"})
        if not tag and not stunde:
            continue
        if tag not in termine.TAGE:
            fehler.append(f"Termin {n + 1}: Welcher Wochentag?")
            continue
        if not stunde.isdigit() or int(stunde) not in STUNDEN:
            fehler.append(f"Termin {n + 1}: In welcher Stunde?")
            continue
        eintraege.append({"tag": tag, "stunde": int(stunde), "laenge": 2 if laenge == "2" else 1})
    for i, a in enumerate(eintraege):
        for b in eintraege[i + 1:]:
            if a["tag"] == b["tag"] and a["stunde"] < b["stunde"] + b["laenge"] \
                    and b["stunde"] < a["stunde"] + a["laenge"]:
                fehler.append(f"Zwei Termine liegen zur selben Zeit ({TAG_NAMEN[a['tag']]}, {b['stunde']}. Stunde).")
    return eintraege, gezeigt, fehler


def zeitraum(ab_text: str | None, bis_text: str | None,
             grenzen: tuple[date, date] | None) -> tuple[str, str, list[str]]:
    """ab und bis des Stundenplans; leer = Grenzen des Schuljahrs (aus den Ferien). Fehlt beides: Fehler."""
    ab, bis = datum(ab_text), datum(bis_text)
    if (ab_text or "").strip() and ab is None or (bis_text or "").strip() and bis is None:
        return "", "", ["Bitte bei „ab“ und „bis“ ein Datum wählen."]
    if grenzen is not None:
        ab, bis = ab or grenzen[0], bis or grenzen[1]
    if ab is None or bis is None:
        return "", "", [BUNDESLAND_FEHLT]
    if ab > bis:
        return "", "", ["„ab“ liegt nach „bis“."]
    return ab.isoformat(), bis.isoformat(), []


def mit_zeitraum(eintraege: list[dict], ab: str, bis: str) -> list[dict]:
    return [{**e, "ab": ab, "bis": bis} for e in eintraege]


def stundenplan_zeilen(zeitplan: list[dict], stichtag: date | None = None) -> list[dict]:
    """Zeilen zum Vorbelegen der Maske: die wiederkehrenden Termine, die am Stichtag (sonst zuletzt) gelten."""
    if stichtag is not None:
        gilt = [e for e in zeitplan if termine.datum_lesen(e["ab"]) <= stichtag <= termine.datum_lesen(e["bis"])]
        zeitplan = gilt or zeitplan
    gesehen, liste = set(), []
    for e in zeitplan:
        schluessel = (e["tag"], e["stunde"], e.get("laenge", 1))
        if schluessel not in gesehen:
            gesehen.add(schluessel)
            liste.append({"tag": e["tag"], "stunde": str(e["stunde"]), "laenge": str(e.get("laenge", 1))})
    return liste


def aufgefuellt(gezeigt: list[dict], anzahl: int) -> list[dict]:
    """Zeilen der Maske, mit leeren auf anzahl aufgefüllt."""
    return gezeigt + [{"tag": "", "stunde": "", "laenge": "1"}] * max(0, anzahl - len(gezeigt))


def stundenplan_text(zeitplan: list[dict]) -> str:
    """„Di 3. Std., Do 5./6. Std.“ für die Klassen-Ansicht (wiederkehrende Termine, ohne Daten)."""
    teile = []
    for e in stundenplan_zeilen(zeitplan, None):
        st = int(e["stunde"])
        teile.append(f"{e['tag']} {st}." + (f"/{st + 1}." if e["laenge"] == "2" else "") + " Std.")
    return ", ".join(teile)


def termine_wahl(wert: Callable[[str], str], liste: Callable[[str], list[str]]) -> tuple[dict, list[str]]:
    """„Termine zuteilen“ aus dem Formular: einzeln angehakte Termine (Feld termin) oder „ab …, n Termine“ (Felder
    ab, anzahl). {} = keine Termine. Argumente wie strukturpflege (termine bzw. ab + anzahl)."""
    gewaehlt = [k for k in liste("termin") if k]
    if gewaehlt:
        return {"termine": gewaehlt}, []
    anzahl = wert("anzahl").strip()
    if not anzahl or anzahl == "0":
        return {}, []
    if not anzahl.isdigit():
        return {}, ["Bitte die Zahl der Termine als Zahl angeben."]
    ab = wert("ab").strip()
    return {"anzahl": int(anzahl), **({"ab": ab} if datum(ab) else {})}, []


def ohne_termin_zahl(wert: str | None) -> tuple[int, list[str]]:
    """Zahl der „Stunden ohne Termin“ beim Anlegen einer Reihe (höchstens 60)."""
    wert = (wert or "").strip()
    if not wert:
        return 0, []
    if not wert.isdigit() or int(wert) > 60:
        return 0, ["Bitte bei „Stunden ohne Termin“ eine Zahl bis 60 angeben."]
    return int(wert), []


def geaendert(felder: dict[str, tuple]) -> tuple[dict, dict]:
    """Nur die Felder, die Lia geändert hat: (zu ändern, gesehen). felder: name -> (neu, beim Öffnen gezeigt).
    So bleiben Änderungen von Jan an anderen Feldern erhalten (Plan 7.2.4)."""
    neu, alt = {}, {}
    for name, (wert, gezeigt) in felder.items():
        if _norm(wert) != _norm(gezeigt):
            neu[name], alt[name] = wert, gezeigt
    return neu, alt


def _norm(wert):
    return [x.strip() for x in wert] if isinstance(wert, list) else (wert or "").strip()


# --- Ansichten -----------------------------------------------------------------------------------------------------

def termin_text(kennung: str, laenge: int = 1) -> str:
    try:
        return termine.anzeige(kennung, laenge)
    except termine.TermineFehler:
        return kennung


def thema(st: dict) -> str:
    return st.get("thema") or THEMA_OFFEN


def belegung(s, klassen_id: str) -> dict[str, dict]:
    """Termin -> Stunde der Klasse ({id, nr (None = ausgeblendet), thema, reihe_id, reihe})."""
    auf = {}
    for r in s.reihen:
        if r["klasse_id"] != klassen_id:
            continue
        for st in r["stunden"] + r["ausgeblendete_stunden"]:
            if st["termin"]:
                auf[st["termin"]] = {"id": st["id"], "nr": st["nr"], "thema": thema(st), "reihe_id": r["id"],
                                     "reihe": r["titel"] or "ohne Titel"}
    return auf


def termine_liste(s, klassen_id: str, kalender: termine.Kalender | None, heute: date) -> list[dict]:
    """Alle Termine der Klasse in Datumsfolge, auch gestrichene: {kennung, text, datum, vergangen, ausgefallen,
    zusatz, stunde (oder None)}. TermineFehler, wenn Ferien oder das Bundesland fehlen."""
    k = s.objekt(klassen_id)
    auf = belegung(s, klassen_id)
    liste = []
    for t in termine.termine(k["zeitplan"], kalender, k["ausfall"], k["zusatz"], mit_ausfall=True):
        liste.append({"kennung": t.kennung, "text": t.text, "datum": t.datum, "vergangen": t.datum < heute,
                      "ausgefallen": t.ausgefallen, "zusatz": t.zusatz,
                      "stunde": None if t.ausgefallen else auf.get(t.kennung)})
    return liste


def termin_optionen(liste: list[dict], nur_frei: bool = False, ohne: str = "") -> list[dict]:
    """Auswahl für „Verschieben nach …“ und „Termine zuteilen“: nicht gestrichene Termine (ohne: die Stunde selbst
    auslassen), Text mit dem, was dort liegt."""
    wahl = []
    for t in liste:
        st = t["stunde"]
        if t["ausgefallen"] or (nur_frei and st) or (st and st["id"] == ohne):
            continue
        dort = f"{_stunde_kurz(st)} ({st['reihe']})" if st else "frei"
        wahl.append({"wert": t["kennung"], "text": f"{t['text']} · {dort}", "frei": not st, "datum": t["datum"],
                     "vergangen": t["vergangen"]})
    return wahl


def _stunde_kurz(st: dict) -> str:
    return f"Stunde {st['nr']}: {st['thema']}" if st["nr"] else f"ausgeblendet: {st['thema']}"


def erster_freier(liste: list[dict], heute: date) -> str:
    """Vorbelegung für „ab“: Datum des ersten freien Termins ab heute."""
    return next((t["datum"].isoformat() for t in liste
                 if not t["ausgefallen"] and not t["stunde"] and t["datum"] >= heute), "")


def belegt_text(s, fehler: termine.Belegt) -> str:
    """Rückfrage bei belegtem Ziel (Grundsatz Flexibilität: einmal fragen)."""
    namen = []
    for sid in fehler.stunden[:3]:
        o = s.objekt(sid) if s else None
        r = s.objekt(o["reihe_id"]) if o else None
        if o and r:
            namen.append(f"„{thema(o)}“ ({r['titel'] or 'ohne Titel'})")
    if not namen:
        return "Dort liegt schon eine Stunde."
    weitere = " und weitere" if len(fehler.stunden) > 3 else ""
    return f"Dort liegt schon {', '.join(namen)}{weitere}."


def fehler_text(fehler: Exception) -> str:
    """Fehler aus agentkit.strukturpflege für Lia (die Texte dort nennen nie die Lerngruppe)."""
    if isinstance(fehler, sp.Konflikt):
        return NEU_LADEN
    t = str(fehler).strip()
    if re.search(r"'[^']*' gibt es nicht", t):
        return GIBT_ES_NICHT
    if t.endswith(" fehlt"):
        return f"{t.removesuffix(' fehlt')}: bitte ausfüllen."
    return t if t.endswith((".", "?", "!")) else t + "."


def fehler_text_rueckgaengig(fehler: Exception) -> str:
    """Rückgängig geht nicht (z. B. Jan hat den Block inzwischen geändert): der Satz von agentkit, als Satz."""
    t = str(fehler).strip()
    return t if t.endswith((".", "?", "!")) else t + "."


def stelle(folge: list[str], stunde_id: str, vor_id: str = "") -> int | None:
    """Stelle für strukturpflege.stunde_verschieben (ab 0, gezählt in der neuen Folge): vor die Stunde vor_id,
    ohne vor_id ans Ende. None, wenn es die Stunden nicht (mehr) gibt."""
    if stunde_id not in folge:
        return None
    rest = [s for s in folge if s != stunde_id]
    if not vor_id:
        return len(rest)
    return rest.index(vor_id) if vor_id in rest else None


def haken_text(haken: list[dict]) -> str:
    """„2 Stunden, 1 Auftrag“ aus struktur.haengt_dran."""
    return ", ".join(h["text"] for h in haken)


def loeschen_text(haken: list[dict]) -> str:
    return (f"Löschen geht nicht, weil noch etwas daran hängt: {haken_text(haken)}. Archivieren geht immer, dabei "
            "geht nichts verloren.")


def zahl_text(n: int, einzahl: str, mehrzahl: str) -> str:
    return f"{n} {einzahl if n == 1 else mehrzahl}"


def aenderungen(letzte: list[dict], jetzt: datetime) -> list[dict]:
    """„Letzte Änderungen“ unter „Ich“: Text, Zeit, ob Rückgängig noch geht."""
    liste = []
    for a in letzte:
        try:
            zeit = datetime.fromisoformat(a.get("zeit") or "").astimezone(jetzt.tzinfo)
        except ValueError:
            zeit = None
        tage = (jetzt.date() - zeit.date()).days if zeit else None
        wann = "" if zeit is None else f"heute {zeit:%H:%M}" if tage == 0 else \
            f"gestern {zeit:%H:%M}" if tage == 1 else f"{zeit:%d.%m.%Y %H:%M}"
        liste.append({"id": a.get("id") or "", "text": a.get("text") or "", "zeit": wann,
                      "zurueck": not a.get("zurueckgenommen"),
                      "hinweis": "zurückgenommen" if a.get("zurueckgenommen") else ""})
    return liste
