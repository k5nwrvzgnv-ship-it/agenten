"""Exposés für Forschungsprojekte: aus einem Besprechungstranskript (z. B. Teams) entsteht ein Exposé.

Auslöser: Auftrag beginnt mit "Exposé:" oder "Expose:" (nur der erste Auftrag einer Kette, Antworten darauf
überarbeiten dasselbe Exposé). Claude schreibt die Beschreibung nach data/expose/<kette>/expose.json und ein
Protokoll für Jan (Beschlossenes, Offenes, Belege). <kette> ist der erste Auftrag der Antwortkette.

Der Renderer kennt noch keine Art "expose" (Bedarf in ../STATUS.md). Bis dahin prüft dieses Modul die
Beschreibung selbst und macht daraus eine Markdown-Datei (<Titel>.md), die Jan in Word oder Teams übernehmen
kann. Das Format ist so gewählt, dass der Renderer es später übernehmen kann (Blöcke wie bei "zusammenfassung",
ohne Quellen: die Belege stehen nur im Protokoll).
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import kurse

ORDNER = Path("data") / "expose"
DATEI = "expose.json"
STAND = ".gebaut.json"
AUSLOESER = re.compile(r"^\s*expos[eé]\s*:", re.IGNORECASE)
DATUM = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
# Umfang (Jan 02.11.2026: 2 bis 4 Seiten, kurz und knapp; Henri: wenige Unterpunkte). Gezählt werden die Wörter
# der Blöcke ohne Kopf und Literatur, A4 mit 11 pt fasst etwa 450 Wörter.
WOERTER = (650, 1500)
LITERATUR_MAX = 12
UNTERPUNKTE_MAX = 6
# Angaben fürs Deckblatt (Matrikelnummern, Modul), persönlich, nicht im Repo
VORLAGE = Path("data") / "vorlagen" / "expose_vorlage.md"

VORLAGE_REGELN = """Formatvorlage (Jan 02.11.2026, Studienbeleg "Quercus" der HNEE): Deckblatt mit HNEE-Logo, einrichtung als
Fachbereich, autoren mit Matrikelnummer, rahmen als bis zu vier Zeilen (Art | Semester, Studiengang, Modul).
Zitierweise APA 7: im Text (Nachname, Jahr), (Nachname & Nachname, Jahr) bzw. (Nachname et al., Jahr), jede im
Text zitierte Quelle steht in literatur und umgekehrt. literatur alphabetisch nach APA 7 mit DOI als
https://doi.org/..., Normen wie „DIN 4074-1:2026-05, Titel. DIN Media GmbH.“"""

FORMAT = """Format der Beschreibung (JSON, reiner Text ohne Markdown, Zeilenumbruch \\n erlaubt):
{
  "art": "expose",
  "titel": "Arbeitstitel (höchstens 200 Zeichen)",
  "untertitel": "optional, höchstens 200 Zeichen",
  "autoren": ["Vorname Nachname (Matr.-Nr. 12345678)", "..."],
  "betreuung": ["Prof. Dr. ..."],
  "einrichtung": "Fachbereich Holzingenieurwesen",
  "rahmen": "Exposé | Wintersemester 2026/27\nStudiengang Holzingenieurwesen (M. Sc.)\nModul <Nummer> – <Name>",
  "datum": "TT.MM.JJJJ (Stand)",
  "bloecke": [
    {"typ": "ueberschrift", "text": "Ausgangslage und Problemstellung"},
    {"typ": "ueberschrift", "text": "Unterpunkt", "ebene": 2},
    {"typ": "absatz", "text": "..."},
    {"typ": "liste", "punkte": ["...", "..."], "nummeriert": false},
    {"typ": "tabelle", "titel": "optional", "kopf": ["Zeitraum", "Arbeitsschritt"], "zeilen": [["...", "..."]]}
  ],
  "literatur": ["Nachname, V., & Nachname, V. (Jahr). Titel. Zeitschrift, Band(Heft), Seiten. https://doi.org/..."]
}
Regeln: Pflicht sind art, titel, autoren, einrichtung, datum, bloecke. Überschriften ohne Nummer (Python
nummeriert). Vor der ersten Ebene 2 steht eine Ebene 1. Tabellen: höchstens 8 Spalten, jede Zeile gleich viele
Zellen wie der Kopf. Umfang 2 bis 4 Seiten: {wmin} bis {wmax} Wörter in den Blöcken, höchstens {lit}
Literaturangaben, höchstens {unter} Überschriften der Ebene 2. Keine Quellenangaben wie "Transkript" oder Zeitmarken im Exposé, die gehören ins Protokoll.
{vorlage_regeln}
Andere Felder sind Fehler.""".replace("{wmin}", str(WOERTER[0])).replace("{wmax}", str(WOERTER[1])) \
    .replace("{lit}", str(LITERATUR_MAX)).replace("{unter}", str(UNTERPUNKTE_MAX)) \
    .replace("{vorlage_regeln}", VORLAGE_REGELN)

_FELDER = {"art", "titel", "untertitel", "autoren", "betreuung", "einrichtung", "rahmen", "datum", "bloecke",
           "literatur"}
_BLOCKFELDER = {"ueberschrift": {"typ", "text", "ebene"}, "absatz": {"typ", "text"},
                "liste": {"typ", "punkte", "nummeriert"}, "tabelle": {"typ", "titel", "kopf", "zeilen"}}


@dataclass
class Bericht:
    dateien: list[Path] = field(default_factory=list)  # neu gebaut, gehen an Jan
    ungueltig: str = ""  # Fehler für Claude, leer = gültig oder nichts zu tun


def ist_exposeauftrag(text: str) -> bool:
    return bool(AUSLOESER.match(text))


def ordner(hier: Path, schluessel: str) -> Path:
    return hier / ORDNER / schluessel


def _text(wert, stelle: str, fehler: list[str], pflicht: bool = True, laenge: int = 5000) -> None:
    if not isinstance(wert, str) or (pflicht and not wert.strip()):
        fehler.append(f"{stelle}: muss ein Text sein{' (nicht leer)' if pflicht else ''}, ist {wert!r:.60}")
    elif len(wert) > laenge:
        fehler.append(f"{stelle}: höchstens {laenge} Zeichen, sind {len(wert)}")


def _textliste(wert, stelle: str, fehler: list[str], pflicht: bool, laenge: int = 1000) -> None:
    if not isinstance(wert, list) or (pflicht and not wert):
        fehler.append(f"{stelle}: muss eine Liste aus Texten sein{' (nicht leer)' if pflicht else ''}")
        return
    for i, w in enumerate(wert):
        _text(w, f"{stelle}[{i}]", fehler, laenge=laenge)


def _block(b, stelle: str, fehler: list[str], ebene1: bool) -> bool:
    """Prüft einen Block, gibt zurück, ob bis hier eine Überschrift der Ebene 1 stand."""
    if not isinstance(b, dict) or b.get("typ") not in _BLOCKFELDER:
        fehler.append(f"{stelle}.typ: muss einer von {', '.join(_BLOCKFELDER)} sein")
        return ebene1
    for f in sorted(set(b) - _BLOCKFELDER[b["typ"]]):
        fehler.append(f"{stelle}.{f}: unbekanntes Feld bei {b['typ']}")
    if b["typ"] == "ueberschrift":
        _text(b.get("text"), f"{stelle}.text", fehler, laenge=200)
        ebene = b.get("ebene", 1)
        if ebene not in (1, 2):
            fehler.append(f"{stelle}.ebene: muss 1 oder 2 sein, ist {ebene!r}")
        elif ebene == 2 and not ebene1:
            fehler.append(f"{stelle}.ebene: vor der ersten Ebene 2 muss eine Ebene 1 stehen")
        if isinstance(b.get("text"), str) and re.match(r"^\s*\d+(\.\d+)*\.?\s", b["text"]):
            fehler.append(f"{stelle}.text: ohne Nummer schreiben, Python nummeriert")
        return ebene1 or ebene == 1
    if b["typ"] == "absatz":
        _text(b.get("text"), f"{stelle}.text", fehler)
    elif b["typ"] == "liste":
        _textliste(b.get("punkte"), f"{stelle}.punkte", fehler, pflicht=True)
        if not isinstance(b.get("nummeriert", False), bool):
            fehler.append(f"{stelle}.nummeriert: muss true oder false sein")
    else:
        if "titel" in b:
            _text(b["titel"], f"{stelle}.titel", fehler, laenge=200)
        kopf, zeilen = b.get("kopf"), b.get("zeilen")
        if kopf is not None:
            _textliste(kopf, f"{stelle}.kopf", fehler, pflicht=True, laenge=500)
        if not isinstance(zeilen, list) or not zeilen or not all(isinstance(z, list) for z in zeilen):
            fehler.append(f"{stelle}.zeilen: muss eine nicht leere Liste aus Zeilen (Listen) sein")
            return ebene1
        breite = len(kopf) if isinstance(kopf, list) and kopf else len(zeilen[0])
        if not 1 <= breite <= 8:
            fehler.append(f"{stelle}: höchstens 8 Spalten, sind {breite}")
        for i, z in enumerate(zeilen):
            if len(z) != breite:
                fehler.append(f"{stelle}.zeilen[{i}]: {len(z)} Zellen, erwartet {breite}")
            for j, zelle in enumerate(z):
                _text(zelle, f"{stelle}.zeilen[{i}][{j}]", fehler, pflicht=False, laenge=500)
    return ebene1


def pruefen(text: str) -> list[str]:
    """Alle Fehler der Beschreibung auf einmal (leer = gültig)."""
    try:
        d = json.loads(text)
    except json.JSONDecodeError as f:
        return [f"kein gültiges JSON: {f}"]
    if not isinstance(d, dict):
        return ["die Beschreibung muss ein JSON-Objekt sein"]
    fehler = [f"{f}: unbekanntes Feld" for f in sorted(set(d) - _FELDER)]
    if d.get("art") != "expose":
        fehler.append(f'art: muss "expose" sein, ist {d.get("art")!r}')
    _text(d.get("titel"), "titel", fehler, laenge=200)
    if "untertitel" in d:
        _text(d["untertitel"], "untertitel", fehler, laenge=200)
    if "rahmen" in d:
        _text(d["rahmen"], "rahmen", fehler, laenge=400)
    _text(d.get("einrichtung"), "einrichtung", fehler, laenge=200)
    _textliste(d.get("autoren"), "autoren", fehler, pflicht=True, laenge=100)
    if "betreuung" in d:
        _textliste(d["betreuung"], "betreuung", fehler, pflicht=False, laenge=100)
    if not isinstance(d.get("datum"), str) or not DATUM.match(d["datum"]):
        fehler.append(f'datum: muss "TT.MM.JJJJ" sein, ist {d.get("datum")!r}')
    bloecke = d.get("bloecke")
    if not isinstance(bloecke, list) or not 1 <= len(bloecke) <= 200:
        fehler.append("bloecke: muss eine Liste aus 1 bis 200 Blöcken sein")
    else:
        ebene1 = False
        for i, b in enumerate(bloecke):
            ebene1 = _block(b, f"bloecke[{i}]", fehler, ebene1)
    if "literatur" in d:
        _textliste(d["literatur"], "literatur", fehler, pflicht=False)
    if not fehler:
        fehler += umfang(d)
    return fehler


def woerter(d: dict) -> int:
    """Wörter aller Blöcke (Überschriften, Absätze, Listen, Tabellen), ohne Kopf und Literatur."""
    texte = []
    for b in d["bloecke"]:
        texte += [b.get("text", ""), b.get("titel", "")] + b.get("punkte", []) + b.get("kopf", [])
        texte += [z for zeile in b.get("zeilen", []) for z in zeile]
    return sum(len(t.split()) for t in texte)


def umfang(d: dict) -> list[str]:
    """Fehler, wenn das Exposé nicht in 2 bis 4 Seiten passt (Beschreibung ist sonst gültig)."""
    fehler = []
    n = woerter(d)
    if not WOERTER[0] <= n <= WOERTER[1]:
        richtung = "kürzen" if n > WOERTER[1] else "ausführen"
        fehler.append(f"Umfang: {WOERTER[0]} bis {WOERTER[1]} Wörter in den Blöcken (2 bis 4 Seiten), sind {n}: "
                      f"{richtung}")
    if len(d.get("literatur", [])) > LITERATUR_MAX:
        fehler.append(f"literatur: höchstens {LITERATUR_MAX} Angaben, sind {len(d['literatur'])}")
    unter = sum(1 for b in d["bloecke"] if b["typ"] == "ueberschrift" and b.get("ebene", 1) == 2)
    if unter > UNTERPUNKTE_MAX:
        fehler.append(f"bloecke: höchstens {UNTERPUNKTE_MAX} Überschriften der Ebene 2, sind {unter} "
                      "(vorläufige Gliederung, wenige Unterpunkte)")
    return fehler


def _zelle(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", "<br>")


def als_markdown(d: dict) -> str:
    """Lesbare Fassung einer gültigen Beschreibung, Überschriften nummeriert (1, 1.1)."""
    zeilen = [f"# {d['titel']}"]
    if d.get("untertitel"):
        zeilen.append(f"\n*{d['untertitel']}*")
    kopf = [", ".join(d["autoren"])]
    if d.get("betreuung"):
        kopf.append(f"Betreuung: {', '.join(d['betreuung'])}")
    kopf += [x for x in (d.get("rahmen"), d["einrichtung"]) if x]
    kopf.append(f"Stand: {d['datum']}")
    zeilen.append("\n" + "  \n".join(kopf))
    nr = [0, 0]
    for b in d["bloecke"]:
        if b["typ"] == "ueberschrift":
            if b.get("ebene", 1) == 1:
                nr = [nr[0] + 1, 0]
                zeilen.append(f"\n## {nr[0]} {b['text']}")
            else:
                nr[1] += 1
                zeilen.append(f"\n### {nr[0]}.{nr[1]} {b['text']}")
        elif b["typ"] == "absatz":
            zeilen.append("\n" + b["text"])
        elif b["typ"] == "liste":
            zeichen = (lambda i: f"{i}.") if b.get("nummeriert") else (lambda i: "-")
            zeilen.append("\n" + "\n".join(f"{zeichen(i)} {p}" for i, p in enumerate(b["punkte"], 1)))
        else:
            if b.get("titel"):
                zeilen.append(f"\n**{b['titel']}**")
            kopf_t = b.get("kopf") or [""] * len(b["zeilen"][0])
            tab = [f"| {' | '.join(_zelle(z) for z in kopf_t)} |", "|" + "---|" * len(kopf_t)]
            tab += [f"| {' | '.join(_zelle(z) for z in zeile)} |" for zeile in b["zeilen"]]
            zeilen.append("\n" + "\n".join(tab))
    if d.get("literatur"):
        zeilen.append("\n## Literatur\n")
        zeilen.append("\n".join(f"- {q}" for q in d["literatur"]))
    return "\n".join(zeilen) + "\n"


def dateiname(titel: str) -> str:
    return kurse.sicherer_name(re.sub(r"\s*:\s*", " - ", titel))


def bauen(exposeordner: Path, weitere=None) -> Bericht:
    """Baut expose.json als <Titel>.md, wenn es neu oder geändert ist. Ungültig: Fehler für Claude.

    weitere(d) -> list[str]: zusätzliche Prüfung einer sonst gültigen Beschreibung (z. B. Literatur gegen die
    geprüfte Recherche)."""
    bericht = Bericht()
    datei = exposeordner / DATEI
    if not datei.is_file():
        return bericht
    roh = datei.read_bytes()
    summe = hashlib.sha256(roh).hexdigest()
    stand_datei = exposeordner / STAND
    stand = json.loads(stand_datei.read_text()) if stand_datei.exists() else {}
    if stand.get(DATEI) == summe:
        return bericht
    text = roh.decode("utf-8", errors="replace")
    fehler = pruefen(text)
    if not fehler and weitere:
        fehler = weitere(json.loads(text))
    if fehler:
        bericht.ungueltig = "\n".join(f"- {f}" for f in fehler)
        return bericht
    d = json.loads(text)
    ausgang = exposeordner / "fassung"
    ausgang.mkdir(exist_ok=True)
    for alt in ausgang.glob("*.md"):  # Titel kann sich geändert haben
        alt.unlink()
    ziel = ausgang / f"{dateiname(d['titel'])}.md"
    ziel.write_text(als_markdown(d), encoding="utf-8")
    bericht.dateien.append(ziel)
    stand[DATEI] = summe
    stand_datei.write_text(json.dumps(stand, indent=1))
    return bericht
