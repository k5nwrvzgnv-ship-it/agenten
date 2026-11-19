"""Besprechungsprotokolle aus einem Transkript (Art "protokoll" im Arbeitsplatz).

Claude liest das Transkript (Teams-.docx mit Textfassung, .vtt, .txt) und schreibt data/besprechungen/<kette>/
protokoll.json im Format FORMAT unten: Inhalt, keine Gestaltung. Jeder Beschluss, jede Aufgabe und jeder offene Punkt
trägt einen Beleg, ein kurzes wörtliches Zitat aus dem Transkript. Python prüft (pruefen): Format, Belege wörtlich im
Transkript, Namen aus den Teilnehmenden, Tagesordnung für die nächste Besprechung nur aus offenen Punkten, Aufgaben
oder als "neu" gekennzeichnet. Dann baut es daraus eine Renderer-Beschreibung der Art "bericht" (als_bericht) und mit
shared/renderer eine docx und PDF nach fassung/. Die Belege stehen nicht im Dokument (Jan 19.11.: Zeitmarken egal,
das Protokoll soll weitergebbar bleiben), nur in protokoll.json.

Hier steht nur Logik ohne Netz und ohne Claude. Den Ablauf macht agent.protokoll_auftrag.
"""

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import renderer
from renderer import vorschau

import kurse

ORDNER = Path("data") / "besprechungen"
DATEI = "protokoll.json"
STAND = ".gebaut.json"
DATUM = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
ZIELE = ("entscheiden", "klaeren", "informieren")
ZIEL_TEXT = {"entscheiden": "entscheiden", "klaeren": "klären", "informieren": "informieren"}
WER_FREI = ("alle", "offen")  # bei Aufgaben und Vorbereitung erlaubt, auch wenn kein Teilnehmender so heißt
TRANSKRIPT_ENDUNGEN = (".txt", ".md", ".vtt", ".srt")
MAX = {"teilnehmende": 12, "themen": 12, "beschluesse": 30, "aufgaben": 30, "offen": 30, "tagesordnung": 12,
       "vorab_klaeren": 5, "hinweise": 3}
MINUTEN_GESAMT = 240
ZITAT_WOERTER = (3, 40)

FORMAT = """Format (JSON, reiner Text ohne Markdown, Zeilenumbruch \\n erlaubt):
{
  "titel": "Worum es ging, kurz (höchstens 120 Zeichen)",
  "datum": "TT.MM.JJJJ (Tag der Besprechung; unbekannt: Tag des Auftrags und in hinweise_an_jan sagen)",
  "teilnehmende": ["Name, wie im Transkript", "..."],
  "kurzfassung": "3 bis 5 Sätze: Anlass, wichtigstes Ergebnis, was als Nächstes passiert",
  "themen": [{"titel": "Thema", "text": "was besprochen wurde, 1 bis 4 Sätze"}],
  "beschluesse": [{"text": "was beschlossen wurde", "von": "Name oder alle", "beleg": "wörtliches Zitat"}],
  "aufgaben": [{"was": "konkrete Aufgabe", "wer": "Name, alle oder offen", "bis": "Datum oder Ereignis, leer wenn
               nicht gesagt", "beleg": "wörtliches Zitat"}],
  "offen": [{"text": "offene oder strittige Frage, bei Uneinigkeit wer was meint", "beleg": "wörtliches Zitat"}],
  "naechster_termin": "Datum, Uhrzeit, Ort oder Link, wie gesagt; leer, wenn keiner genannt wurde",
  "naechste_besprechung": {
    "ziel": "ein Satz: was nach der nächsten Besprechung feststehen soll",
    "vorab_klaeren": ["Frage, die vor oder zu Beginn geklärt sein muss"],
    "tagesordnung": [{"punkt": "Thema", "ziel": "entscheiden | klaeren | informieren",
                      "vorbereitung": "wer bereitet was vor, oder leer", "minuten": 10, "bezug": ["O1", "A2"]}],
    "hinweise": ["sachliche Beobachtung zum Ablauf mit Vorschlag"]
  },
  "hinweise_an_jan": "optional: was du nicht sicher zuordnen konntest (geht nur an Jan, nicht ins Dokument)"
}
Regeln:
- Pflicht: titel, datum, teilnehmende, kurzfassung, naechste_besprechung mit ziel und mindestens einem Punkt in
  tagesordnung. Die Listen themen, beschluesse, aufgaben, offen dürfen leer sein, wenn es nichts davon gab.
- Python nummeriert: Beschlüsse B1, B2 ..., Aufgaben A1 ..., offene Punkte O1 ... in der Reihenfolge der Listen.
- beleg: 3 bis 40 aufeinanderfolgende Wörter genau so, wie sie im Transkript stehen (ohne Zeitmarke und
  Sprechername). Python sucht sie im Transkript, Groß- und Kleinschreibung und Satzzeichen zählen nicht. Steht
  etwas nicht wörtlich im Transkript, gehört es nicht ins Protokoll.
- von, wer und Namen in vorbereitung: nur Namen aus teilnehmende (oder alle, offen). Wer etwas übernimmt, muss
  das im Transkript gesagt oder zugesagt haben, sonst wer = "offen".
- bezug je Punkt der Tagesordnung: die Nummern der offenen Punkte (O...) und Aufgaben (A...), aus denen er
  folgt, oder ["neu"] für einen Punkt, der in der Besprechung zu kurz kam oder fehlte (dann in punkt sagen, warum).
- minuten: ganze Zahl von 1 bis 120, zusammen höchstens 240.
- hinweise (höchstens 3): Beobachtungen zum Ablauf, nicht zu Personen, z. B. "Das Thema Kamera kam dreimal
  auf, ohne Entscheidung: nächstes Mal mit einer Vorlage von zwei Optionen beginnen." Nichts Abwertendes, das
  Protokoll geht an alle Teilnehmenden.
- Höchstens 12 Teilnehmende, 12 Themen, je 30 Beschlüsse, Aufgaben, offene Punkte, 12 Punkte in der
  Tagesordnung, 5 Fragen in vorab_klaeren. Andere Felder sind Fehler. Lücken als [OFFEN: was fehlt]."""

_FELDER = {"titel", "datum", "teilnehmende", "kurzfassung", "themen", "beschluesse", "aufgaben", "offen",
           "naechster_termin", "naechste_besprechung", "hinweise_an_jan"}
_LISTEN = {"themen": {"titel", "text"}, "beschluesse": {"text", "von", "beleg"},
           "aufgaben": {"was", "wer", "bis", "beleg"}, "offen": {"text", "beleg"}}
_NAECHSTE = {"ziel", "vorab_klaeren", "tagesordnung", "hinweise"}
_PUNKT = {"punkt", "ziel", "vorbereitung", "minuten", "bezug"}
_KUERZEL = {"beschluesse": "B", "aufgaben": "A", "offen": "O"}


@dataclass
class Bericht:
    dateien: list[Path] = field(default_factory=list)  # neu gebaut (docx, pdf), gehen an Jan
    ungueltig: str = ""  # Fehler für Claude, leer = gültig oder nichts zu tun
    fehler: list[str] = field(default_factory=list)  # Fehler des Agenten (Profil, LibreOffice), nicht Claudes


def ordner(hier: Path, schluessel: str) -> Path:
    return hier / ORDNER / schluessel


def transkript_dateien(pfade: list[Path]) -> list[Path]:
    """Lesbare Fassung je angehängter Datei: .txt/.md/.vtt/.srt selbst, sonst die Textfassung <datei>.txt."""
    lesbar = []
    for p in pfade:
        if p.suffix.lower() in TRANSKRIPT_ENDUNGEN:
            lesbar.append(p)
        elif (txt := p.with_name(p.name + ".txt")).is_file():
            lesbar.append(txt)
    return [p for p in lesbar if p.is_file()]


def transkript_lesen(pfade: list[Path]) -> str:
    return "\n\n".join(p.read_text(encoding="utf-8", errors="replace") for p in transkript_dateien(pfade))


def _woerter(text: str) -> list[str]:
    """Wörter für den Vergleich: NFKC, klein, ohne Satzzeichen (Bindestrich trennt)."""
    text = unicodedata.normalize("NFKC", text).lower()
    return re.findall(r"\w+", text)


def zitat_im_text(zitat: str, transkript_woerter: str) -> bool:
    """transkript_woerter: " ".join(_woerter(transkript)) mit Leerzeichen an beiden Enden."""
    w = _woerter(zitat)
    return bool(w) and f" {' '.join(w)} " in transkript_woerter


def _vorbereitet(transkript: str) -> str:
    return f" {' '.join(_woerter(transkript))} "


def _text(wert, stelle: str, fehler: list[str], pflicht: bool = True, laenge: int = 2000) -> None:
    if not isinstance(wert, str) or (pflicht and not wert.strip()):
        fehler.append(f"{stelle}: muss ein Text sein{' (nicht leer)' if pflicht else ''}, ist {wert!r:.60}")
    elif len(wert) > laenge:
        fehler.append(f"{stelle}: höchstens {laenge} Zeichen, sind {len(wert)}")


def _liste(wert, stelle: str, fehler: list[str], hoechstens: int, pflicht: bool = False) -> list:
    if wert is None and not pflicht:
        return []
    if not isinstance(wert, list) or (pflicht and not wert):
        fehler.append(f"{stelle}: muss eine Liste sein{' (nicht leer)' if pflicht else ''}")
        return []
    if len(wert) > hoechstens:
        fehler.append(f"{stelle}: höchstens {hoechstens} Einträge, sind {len(wert)}")
    return wert


def _name_bekannt(name: str, teilnehmende: list[str], frei: tuple[str, ...]) -> bool:
    n = " ".join(_woerter(name))
    if n in frei:
        return True
    for t in teilnehmende:
        tw = _woerter(t)
        if n == " ".join(tw) or (n and n in tw):  # "Henri" passt zu "Henri Müller"
            return True
    return False


def pruefen(text: str, transkript: str) -> list[str]:
    """Alle Fehler von protokoll.json auf einmal (leer = gültig). transkript: Text aller Transkriptdateien."""
    try:
        d = json.loads(text)
    except json.JSONDecodeError as f:
        return [f"kein gültiges JSON: {f}"]
    if not isinstance(d, dict):
        return ["das Protokoll muss ein JSON-Objekt sein"]
    fehler = [f"{f}: unbekanntes Feld" for f in sorted(set(d) - _FELDER)]
    _text(d.get("titel"), "titel", fehler, laenge=120)
    if not isinstance(d.get("datum"), str) or not DATUM.match(d["datum"]):
        fehler.append(f'datum: muss "TT.MM.JJJJ" sein, ist {d.get("datum")!r}')
    _text(d.get("kurzfassung"), "kurzfassung", fehler, laenge=1200)
    for f in ("naechster_termin", "hinweise_an_jan"):
        if f in d:
            _text(d[f], f, fehler, pflicht=False, laenge=500 if f == "naechster_termin" else 2000)

    tw = _vorbereitet(transkript)
    teilnehmende = _liste(d.get("teilnehmende"), "teilnehmende", fehler, MAX["teilnehmende"], pflicht=True)
    namen = []
    for i, t in enumerate(teilnehmende):
        _text(t, f"teilnehmende[{i}]", fehler, laenge=100)
        if isinstance(t, str) and t.strip():
            if not any(f" {w} " in tw for w in _woerter(t)):
                fehler.append(f"teilnehmende[{i}]: {t!r} kommt im Transkript nicht vor")
            namen.append(t)

    nummern: dict[str, set[str]] = {}
    for liste, felder in _LISTEN.items():
        eintraege = _liste(d.get(liste), liste, fehler, MAX[liste])
        if liste in _KUERZEL:
            nummern[liste] = {f"{_KUERZEL[liste]}{i + 1}" for i in range(len(eintraege))}
        for i, e in enumerate(eintraege):
            stelle = f"{liste}[{i}]"
            if not isinstance(e, dict):
                fehler.append(f"{stelle}: muss ein Objekt sein")
                continue
            fehler += [f"{stelle}.{f}: unbekanntes Feld" for f in sorted(set(e) - felder)]
            for f in sorted(felder - {"beleg", "von", "wer", "bis"}):
                _text(e.get(f), f"{stelle}.{f}", fehler, laenge=120 if f == "titel" else 1000)
            if "bis" in felder:
                _text(e.get("bis", ""), f"{stelle}.bis", fehler, pflicht=False, laenge=100)
            for f in ("von", "wer"):
                if f in felder:
                    _text(e.get(f), f"{stelle}.{f}", fehler, laenge=100)
                    if isinstance(e.get(f), str) and e[f].strip() and not _name_bekannt(e[f], namen, WER_FREI):
                        fehler.append(f"{stelle}.{f}: {e[f]!r} steht nicht in teilnehmende (oder alle, offen)")
            if "beleg" in felder:
                _text(e.get("beleg"), f"{stelle}.beleg", fehler, laenge=400)
                b = e.get("beleg")
                if isinstance(b, str) and b.strip():
                    n = len(_woerter(b))
                    if not ZITAT_WOERTER[0] <= n <= ZITAT_WOERTER[1]:
                        fehler.append(f"{stelle}.beleg: {ZITAT_WOERTER[0]} bis {ZITAT_WOERTER[1]} Wörter, sind {n}")
                    elif not zitat_im_text(b, tw):
                        fehler.append(f"{stelle}.beleg: steht so nicht im Transkript: {b[:80]!r}")

    nb = d.get("naechste_besprechung")
    if not isinstance(nb, dict):
        fehler.append("naechste_besprechung: muss ein Objekt sein")
        return fehler
    fehler += [f"naechste_besprechung.{f}: unbekanntes Feld" for f in sorted(set(nb) - _NAECHSTE)]
    _text(nb.get("ziel"), "naechste_besprechung.ziel", fehler, laenge=500)
    for f in ("vorab_klaeren", "hinweise"):
        for i, t in enumerate(_liste(nb.get(f), f"naechste_besprechung.{f}", fehler, MAX[f])):
            _text(t, f"naechste_besprechung.{f}[{i}]", fehler, laenge=500)
    alle = set().union(*nummern.values()) if nummern else set()
    summe = 0
    for i, p in enumerate(_liste(nb.get("tagesordnung"), "naechste_besprechung.tagesordnung", fehler,
                                 MAX["tagesordnung"], pflicht=True)):
        stelle = f"naechste_besprechung.tagesordnung[{i}]"
        if not isinstance(p, dict):
            fehler.append(f"{stelle}: muss ein Objekt sein")
            continue
        fehler += [f"{stelle}.{f}: unbekanntes Feld" for f in sorted(set(p) - _PUNKT)]
        _text(p.get("punkt"), f"{stelle}.punkt", fehler, laenge=300)
        _text(p.get("vorbereitung", ""), f"{stelle}.vorbereitung", fehler, pflicht=False, laenge=300)
        if p.get("ziel") not in ZIELE:
            fehler.append(f"{stelle}.ziel: muss einer von {', '.join(ZIELE)} sein, ist {p.get('ziel')!r}")
        m = p.get("minuten")
        if not isinstance(m, int) or isinstance(m, bool) or not 1 <= m <= 120:
            fehler.append(f"{stelle}.minuten: ganze Zahl von 1 bis 120, ist {m!r}")
        else:
            summe += m
        bezug = p.get("bezug")
        if not isinstance(bezug, list) or not bezug or not all(isinstance(x, str) for x in bezug):
            fehler.append(f'{stelle}.bezug: Liste aus Nummern wie "O1", "A2" oder ["neu"]')
        elif bezug != ["neu"]:
            for x in bezug:
                if x.strip().upper() not in alle:
                    fehler.append(f"{stelle}.bezug: {x!r} gibt es nicht (vorhanden: {', '.join(sorted(alle)) or 'keine'})")
    if summe > MINUTEN_GESAMT:
        fehler.append(f"naechste_besprechung.tagesordnung: zusammen höchstens {MINUTEN_GESAMT} Minuten, sind {summe}")
    return fehler


def _absatz(text: str) -> dict:
    return {"typ": "absatz", "text": text}


def als_bericht(d: dict) -> dict:
    """Renderer-Beschreibung (Art "bericht") zu einem gültigen Protokoll. Belege bleiben draußen."""
    b = [_absatz("Teilnehmende: " + ", ".join(d["teilnehmende"])),
         {"typ": "ueberschrift", "text": "Kurzfassung"}, _absatz(d["kurzfassung"])]
    if d.get("themen"):
        b.append({"typ": "ueberschrift", "text": "Besprochen"})
        for t in d["themen"]:
            b += [{"typ": "ueberschrift", "text": t["titel"], "ebene": 2}, _absatz(t["text"])]
    if d.get("beschluesse"):
        b += [{"typ": "ueberschrift", "text": "Beschlüsse"},
              {"typ": "tabelle", "kopf": ["Nr.", "Beschluss", "von"], "erste_spalte_fett": True,
               "zeilen": [[f"B{i}", e["text"], e["von"]] for i, e in enumerate(d["beschluesse"], 1)]}]
    if d.get("aufgaben"):
        b += [{"typ": "ueberschrift", "text": "Aufgaben"},
              {"typ": "tabelle", "kopf": ["Nr.", "Aufgabe", "wer", "bis"], "erste_spalte_fett": True,
               "zeilen": [[f"A{i}", e["was"], e["wer"], e.get("bis") or "offen"]
                          for i, e in enumerate(d["aufgaben"], 1)]}]
    if d.get("offen"):
        b += [{"typ": "ueberschrift", "text": "Offene Punkte"},
              {"typ": "tabelle", "kopf": ["Nr.", "Punkt"], "erste_spalte_fett": True,
               "zeilen": [[f"O{i}", e["text"]] for i, e in enumerate(d["offen"], 1)]}]
    if (d.get("naechster_termin") or "").strip():
        b += [{"typ": "ueberschrift", "text": "Nächster Termin"}, _absatz(d["naechster_termin"])]
    nb = d["naechste_besprechung"]
    b += [{"typ": "ueberschrift", "text": "Vorschlag für die nächste Besprechung"}, _absatz("Ziel: " + nb["ziel"])]
    if nb.get("vorab_klaeren"):
        b += [_absatz("Vorab oder zu Beginn klären:"), {"typ": "liste", "punkte": list(nb["vorab_klaeren"])}]
    punkte = nb["tagesordnung"]
    zeilen = [[str(i), p["punkt"], ZIEL_TEXT[p["ziel"]], p.get("vorbereitung") or "", f"{p['minuten']} min",
               ", ".join(x.strip().upper() if x != "neu" else "neu" for x in p["bezug"])]
              for i, p in enumerate(punkte, 1)]
    zeilen.append(["", "zusammen", "", "", f"{sum(p['minuten'] for p in punkte)} min", ""])
    b.append({"typ": "tabelle", "titel": "Tagesordnung", "kopf": ["Nr.", "Punkt", "Ziel", "Vorbereitung", "Zeit",
                                                                   "aus"], "erste_spalte_fett": True,
              "zeilen": zeilen})
    if nb.get("hinweise"):
        b.append({"typ": "hinweis", "art": "wichtig", "titel": "Zum Ablauf", "text": "\n".join(nb["hinweise"])})
    return {"art": "bericht", "rubrik": "Besprechungsprotokoll", "titel": d["titel"], "datum": d["datum"],
            "bloecke": b}


def daten(d: dict | None) -> dict:
    """daten fürs Ergebnis im Arbeitsplatz ({"titel", "kern", "punkte", "pruefen"})."""
    if not d:
        return {"titel": "Besprechungsprotokoll", "kern": "Es liegt noch kein gültiges Protokoll vor.", "punkte": [],
                "pruefen": "Ergebnistext lesen: dort steht, was fehlt."}
    offen_wer = sum(1 for a in d.get("aufgaben", []) if " ".join(_woerter(a["wer"])) == "offen")
    ohne_frist = sum(1 for a in d.get("aufgaben", []) if not (a.get("bis") or "").strip())
    pruefen = [f"{len(d.get('beschluesse', []))} Beschlüsse und {len(d.get('aufgaben', []))} Aufgaben gegen die "
               "Erinnerung lesen"]
    if offen_wer or ohne_frist:
        pruefen.append(f"{offen_wer} Aufgaben ohne Zuständige, {ohne_frist} ohne Frist")
    if (d.get("hinweise_an_jan") or "").strip():
        pruefen.append("Hinweis des Agenten: " + d["hinweise_an_jan"].strip()[:300])
    return {"titel": f"Protokoll {d['datum']}: {d['titel']}"[:200],
            "kern": d["kurzfassung"][:500],
            "punkte": [f"B{i}: {e['text']}"[:200] for i, e in enumerate(d.get("beschluesse", [])[:8], 1)],
            "pruefen": ". ".join(pruefen) + "."}


def dateiname(d: dict) -> str:
    tag, monat, jahr = d["datum"].split(".")
    titel = re.sub(r"\s*:\s*", " - ", d["titel"])
    return kurse.sicherer_name(f"{jahr}-{monat}-{tag} Protokoll {titel}")


def bauen(protokollordner: Path, transkript: str, profil: dict, bauen=renderer.bauen,
          als_pdf=vorschau.als_pdf) -> Bericht:
    """Baut protokoll.json als docx und PDF, wenn es neu oder geändert ist. Ungültig: Fehler für Claude.

    Fehler des Agenten (Profil, LibreOffice) stehen in `fehler`, der Stand bleibt dann offen, damit der nächste Lauf
    es noch einmal versucht."""
    bericht = Bericht()
    datei = protokollordner / DATEI
    if not datei.is_file():
        return bericht
    roh = datei.read_bytes()
    summe = hashlib.sha256(roh).hexdigest()
    stand_datei = protokollordner / STAND
    stand = json.loads(stand_datei.read_text()) if stand_datei.exists() else {}
    if stand.get(DATEI) == summe:
        return bericht
    text = roh.decode("utf-8", errors="replace")
    if fehler := pruefen(text, transkript):
        bericht.ungueltig = "\n".join(f"- {f}" for f in fehler)
        return bericht
    d = json.loads(text)
    ausgang = protokollordner / "fassung"
    ausgang.mkdir(exist_ok=True)
    for alt in ausgang.iterdir():  # Titel oder Datum können sich geändert haben
        if alt.suffix in (".docx", ".pdf"):
            alt.unlink()
    docx = ausgang / f"{dateiname(d)}.docx"
    try:
        bauen(als_bericht(d), docx, profil=profil, vorschau=False)
    except renderer.BeschreibungUngueltig as f:  # Grenzen des Renderers, die pruefen() nicht kennt: an Claude
        bericht.ungueltig = "\n".join(f"- (im Dokument) {x}" for x in f.fehler)
        return bericht
    except (ValueError, OSError) as f:  # Profil (ProfilUngueltig ist ein ValueError)
        bericht.fehler.append(f"{docx.name} nicht gebaut: {f}")
        return bericht
    bericht.dateien.append(docx)
    try:
        bericht.dateien.append(als_pdf(docx, ausgang))
    except (OSError, vorschau.VorschauFehler) as f:  # die docx geht trotzdem an Jan
        bericht.fehler.append(f"PDF nicht gebaut, die docx hängt an: {f}")
        return bericht
    stand[DATEI] = summe
    stand_datei.write_text(json.dumps(stand, indent=1))
    return bericht
