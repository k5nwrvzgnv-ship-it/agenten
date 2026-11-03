"""Lias Struktur Fach → Klasse/Kurs → Reihe → Stunde aus lia/instanz/reihen.toml, EINE Leseschicht für alle Leser.

Plan: docs/struktur-pflege-plan.md (Jan 03.11.2026, F1). Bauschritt 1: nur lesen. Schreiben (Block-Editor) kommt
in Bauschritt 4. unterricht, examen, recherche, chat und Web-App lesen ab Bauschritt 2 nur noch hierüber.

Neues Format (Abschnitt 2 des Plans), eine id gilt über alle Ebenen und ändert sich nie:
  [[fach]]   id, name; freiwillig kurzform, archiviert
  [[klasse]] id, fach (id des Fachs), name („8“, „Kurs 11“); freiwillig schuljahr, herkunft (id einer Klasse),
             archiviert. Die Lerngruppe steht NICHT hier, sondern in lerngruppen.toml (F6, siehe unten).
  [[reihe]]  id, klasse (id der Klasse); freiwillig titel, reihenfrage, notizen, stand (geplant, laufend,
             abgeschlossen; Standard laufend), herkunft (id einer Reihe), archiviert als Texte; behandelt,
             merksaetze, bisherige_reihen, agenten als Listen von Texten
  [[reihe.stunde]] id, thema; freiwillig marke ("UB" oder "Prüfung"), archiviert (= ausgeblendet).
             Keine gespeicherte Nummer (F3): Die Nummer zählt die Reihenfolge der Blöcke, nur über nicht
             ausgeblendete Stunden.
archiviert ist ein Datum "2026-11-03". Es vererbt sich beim Lesen (im_archiv): Ist das Fach oder die Klasse
archiviert, gilt alles darunter als archiviert, ohne dass dort etwas steht.

Altes Format (bis zur Migration, Bauschritt 3): nur [[reihe]] mit fach und klasse als Text (Regeln wie
lia/unterricht/reihen.py), Stunden mit nr. Fach und Klasse werden daraus abgeleitet (ids wie die Web-App:
kennung(fach), kennung(fach, klasse), mit Schuljahr dahinter, wenn eins gesetzt ist).

Lerngruppen: <instanz>/lerngruppen.toml (gitignored, chmod 600), je Klasse ein Eintrag `"<klassen-id>" = "Text"`
(lange Texte in dreifachen Anführungszeichen).
Der Text steht nie in Fehlertexten.

Aufgelöste Objekte sind Dicts mit denselben Feldnamen wie bisher in den Lesern (fach, klasse sind die NAMEN,
fach_id, klasse_id die Kennungen), damit Prompt-Texte gleich bleiben:
  Reihe:  id, ebene="reihe", fach, fach_id, klasse, klasse_id, schuljahr, lerngruppe, titel, reihenfrage, notizen,
          stand, behandelt, merksaetze, bisherige_reihen, agenten, herkunft, archiviert, im_archiv,
          stunden (sichtbare, je mit nr ab 1), ausgeblendete_stunden (nr None)
  Stunde: id, ebene="stunde", reihe_id, nr, thema, marke, archiviert, im_archiv
  Klasse: id, ebene="klasse", fach, fach_id, name, schuljahr, lerngruppe, herkunft, archiviert, im_archiv,
          reihen (ids)
  Fach:   id, ebene="fach", name, kurzform, archiviert, im_archiv, klassen (ids)

Aufruf: s = struktur.laden(); s.reihe("ethik-8-straftheorien"), s.ort(id), s.haengt_dran(id),
s.pruefungsreihen(), s.pruefungsstunde(reihe_id). struktur.pruefen() gibt Fehlertexte für Jan zurück (leer = gut).
Auf der Kommandozeile (commit-daten.sh): python3 -m agentkit.struktur [<instanz-ordner>]
"""

import hashlib
import json
import re
import stat
import sys
import tomllib
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .config import KONTINGENT_DIR

LIA_INSTANZ = KONTINGENT_DIR.parent / "lia" / "instanz"
DATEI = "reihen.toml"
LERNGRUPPEN = "lerngruppen.toml"
WEBAPP_DATEN = KONTINGENT_DIR / "webapp" / "data"  # shared/webapp/data (zustand/<schluessel>.json)

ID_MUSTER = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")  # passt auch zu agentkit.auftraege (Feld reihe, ort)
ID_MAX = 80
STAENDE = ("geplant", "laufend", "abgeschlossen")
MARKEN = ("UB", "Prüfung")
PRUEFUNG = "Prüfung"

FACH_TEXTE = ("id", "name", "kurzform", "archiviert")
KLASSE_TEXTE = ("id", "fach", "name", "schuljahr", "herkunft", "archiviert")
REIHE_TEXTE = ("id", "klasse", "titel", "reihenfrage", "notizen", "stand", "herkunft", "archiviert")
REIHE_LISTEN = ("behandelt", "merksaetze", "bisherige_reihen", "agenten")
STUNDE_TEXTE = ("id", "thema", "marke", "archiviert")
# Altes Format (wie lia/unterricht/reihen.py)
ALT_TEXTE = ("id", "fach", "klasse", "titel", "reihenfrage", "lerngruppe", "notizen", "stand", "schuljahr")
ALT_STUNDE = ("nr", "thema", "marke")

_UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
_KLAMMER = re.compile(r"\s*\([^)]*\)")


class StrukturFehler(Exception):
    """reihen.toml oder lerngruppen.toml ist kaputt, oder eine Abfrage hat kein eindeutiges Ergebnis. Der Text ist
    für Jan."""


def kennung(*teile: str) -> str:
    """Kennung wie shared/webapp/logik.kennung (nur fürs alte Format): Kleinbuchstaben, Ziffern, Bindestriche,
    Klammern im Titel zählen nicht mit."""
    text = " ".join(_KLAMMER.sub("", t) for t in teile).lower().translate(_UMLAUTE)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:ID_MAX].rstrip("-")


@dataclass
class Struktur:
    format: str  # "neu" oder "alt" (bis zur Migration)
    faecher: list[dict] = field(default_factory=list)
    klassen: list[dict] = field(default_factory=list)
    reihen: list[dict] = field(default_factory=list)
    instanz: Path | None = None  # Ordner mit auftraege/, freigabe/ (für haengt_dran)

    def objekt(self, kennung_: str) -> dict | None:
        """Objekt einer beliebigen Ebene per id, sonst None."""
        for o in self._alle():
            if o["id"] == kennung_:
                return o
        return None

    def reihe(self, kennung_: str) -> dict | None:
        o = self.objekt(kennung_)
        return o if o and o["ebene"] == "reihe" else None

    def stunden(self) -> list[dict]:
        """Alle Stunden, sichtbare und ausgeblendete."""
        return [s for r in self.reihen for s in r["stunden"] + r["ausgeblendete_stunden"]]

    def ort(self, kennung_: str) -> dict | None:
        """Lage eines Objekts: {"ebene", "fach", "klasse", "reihe", "stunde"} mit den aufgelösten Objekten (None für
        Ebenen darunter). Unbekannte id: None."""
        o = self.objekt(kennung_)
        if o is None:
            return None
        lage = {"ebene": o["ebene"], "fach": None, "klasse": None, "reihe": None, "stunde": None, o["ebene"]: o}
        if o["ebene"] == "stunde":
            lage["reihe"] = self.objekt(o["reihe_id"])
        if lage["reihe"]:
            lage["klasse"] = self.objekt(lage["reihe"]["klasse_id"])
        if lage["klasse"]:
            lage["fach"] = self.objekt(lage["klasse"]["fach_id"])
        return lage

    def pruefungsreihen(self) -> list[dict]:
        """Nicht archivierte Reihen mit mindestens einer sichtbaren Stunde mit Marke „Prüfung“ (Examen ist eine
        Stunde, F14)."""
        return [r for r in self.reihen if not r["im_archiv"] and any(s["marke"] == PRUEFUNG for s in r["stunden"])]

    def pruefungsstunde(self, reihe_id: str) -> dict:
        """Die eine sichtbare Stunde mit Marke „Prüfung“ der Reihe. Keine oder mehrere: StrukturFehler."""
        r = self.reihe(reihe_id)
        if r is None:
            raise StrukturFehler(f"Reihe {reihe_id!r} gibt es nicht in {DATEI}")
        treffer = [s for s in r["stunden"] if s["marke"] == PRUEFUNG]
        if len(treffer) != 1:
            raise StrukturFehler(f"Reihe {reihe_id!r} hat {len(treffer)} Stunden mit Marke „{PRUEFUNG}“, "
                                 "erwartet genau eine")
        return treffer[0]

    def haengt_dran(self, kennung_: str, webapp_daten: Path | None = None) -> list[dict]:
        """Was am Objekt hängt (Abschnitt 3.1 des Plans): je Quelle {"quelle", "anzahl", "text"}, leer = nichts.
        Quellen: darunter, auftraege, entwuerfe, agenten, webapp, chat, verweise. Löschen geht nur bei leerer Liste.
        Verweise per Titel (examen, recherche bis Bauschritt 2) erkennt das nicht, nur per id und die Marke
        „Prüfung“."""
        o = self.objekt(kennung_)
        if o is None:
            raise StrukturFehler(f"{kennung_!r} gibt es nicht in {DATEI}")
        haken = []

        def dazu(quelle: str, anzahl: int, einzahl: str, mehrzahl: str):
            if anzahl:
                haken.append({"quelle": quelle, "anzahl": anzahl,
                              "text": f"{anzahl} {einzahl if anzahl == 1 else mehrzahl}"})

        if o["ebene"] == "fach":
            dazu("darunter", len(o["klassen"]), "Klasse", "Klassen")
        elif o["ebene"] == "klasse":
            dazu("darunter", len(o["reihen"]), "Reihe", "Reihen")
        elif o["ebene"] == "reihe":
            dazu("darunter", len(o["stunden"]) + len(o["ausgeblendete_stunden"]), "Stunde", "Stunden")
            if o["agenten"]:
                haken.append({"quelle": "agenten", "anzahl": len(o["agenten"]),
                              "text": "Agenten: " + ", ".join(o["agenten"])})
        elif o["marke"] == PRUEFUNG:
            haken.append({"quelle": "verweise", "anzahl": 1, "text": "Prüfungsstunde (lia/examen)"})
        if self.instanz is None:
            return haken
        passt = _passt_zu(kennung_)
        dazu("auftraege", sum(map(passt, _jsons(self.instanz / "auftraege", ("neu", "erledigt")))),
             "Auftrag", "Aufträge")
        dazu("entwuerfe", sum(map(passt, _jsons(self.instanz / "freigabe", ("offen", "erledigt")))),
             "Entwurf", "Entwürfe")
        dazu("webapp", _im_zustand(kennung_, _zustand(self.instanz, webapp_daten or WEBAPP_DATEN)),
             "Zuordnung in der Web-App", "Zuordnungen in der Web-App")
        dazu("chat", sum(map(passt, _jsonl(self.instanz.parent / "chat" / "data" / "verlauf.jsonl"))),
             "Eintrag im Chat-Verlauf", "Einträge im Chat-Verlauf")
        for pfad in _verweise(kennung_, self.instanz):
            haken.append({"quelle": "verweise", "anzahl": 1, "text": f"Verweis in {pfad}"})
        return haken

    def _alle(self) -> list[dict]:
        return self.faecher + self.klassen + self.reihen + self.stunden()


# --- Laden und Prüfen ---------------------------------------------------------------------------------------------

def laden(instanz: Path | None = None) -> Struktur:
    """Struktur aus <instanz>/reihen.toml (Standard lia/instanz), geprüft und aufgelöst. Fehlt die Datei: leer.
    Fehler: StrukturFehler mit allen Fehlertexten. Liest nur, ändert nichts."""
    instanz = Path(instanz or LIA_INSTANZ)
    s, fehler = _lesen(instanz)
    if fehler:
        raise StrukturFehler("\n".join(fehler))
    return s


def pruefen(instanz: Path | None = None) -> list[str]:
    """Fehlertexte zu reihen.toml und lerngruppen.toml der Instanz, leer = in Ordnung."""
    return _lesen(Path(instanz or LIA_INSTANZ))[1]


def aus_text(text: str, lerngruppen: dict[str, str] | None = None, instanz: Path | None = None) -> Struktur:
    """Wie laden(), aber aus einem Text (Tests, später der Block-Editor vor dem Schreiben)."""
    s, fehler = aufloesen(text, lerngruppen or {}, instanz)
    if fehler:
        raise StrukturFehler("\n".join(fehler))
    return s


def aufloesen(text: str, lerngruppen: dict[str, str], instanz: Path | None = None) -> tuple[Struktur, list[str]]:
    """Reine Logik ohne Dateien: (Struktur, Fehlertexte). Bei Fehlern ist die Struktur unvollständig."""
    try:
        daten = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        return Struktur("neu", instanz=instanz), [f"{DATEI} ist kein gültiges TOML: {e}"]
    fremd = sorted(set(daten) - {"fach", "klasse", "reihe"})
    if fremd:
        return Struktur("neu", instanz=instanz), [f"{DATEI}: unbekannte Einträge {fremd}, erwartet [[fach]], "
                                                  "[[klasse]], [[reihe]]"]
    for name in ("fach", "klasse", "reihe"):
        if name in daten and not (isinstance(daten[name], list) and all(isinstance(x, dict) for x in daten[name])):
            return Struktur("neu", instanz=instanz), [f"{DATEI}: {name} als [[{name}]] schreiben, nicht [{name}]"]
    fehler: list[str] = []
    if "fach" in daten or "klasse" in daten:
        s = _neu(daten, fehler)
    else:
        s = _alt(daten.get("reihe", []), fehler)
    s.instanz = instanz
    _gemeinsam_pruefen(s, lerngruppen, fehler)
    if not fehler:
        _lerngruppen_einsetzen(s, lerngruppen)
    return s, fehler


def _lesen(instanz: Path) -> tuple[Struktur, list[str]]:
    lerngruppen, fehler = _lerngruppen_lesen(instanz / LERNGRUPPEN)
    pfad = instanz / DATEI
    text = pfad.read_text(encoding="utf-8") if pfad.exists() else ""
    s, weitere = aufloesen(text, lerngruppen, instanz)
    return s, fehler + weitere


def _lerngruppen_lesen(pfad: Path) -> tuple[dict[str, str], list[str]]:
    if not pfad.exists():
        return {}, []
    modus = stat.S_IMODE(pfad.stat().st_mode)
    if modus & 0o077:
        return {}, [f"{pfad.name} hat Rechte {oct(modus)}, erlaubt ist nur 600. Beheben mit: chmod 600 {pfad}"]
    try:
        daten = tomllib.loads(pfad.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        return {}, [f"{pfad.name} ist kein gültiges TOML: {e}"]
    falsch = sorted(k for k, v in daten.items() if not isinstance(v, str))
    if falsch:
        return {}, [f"{pfad.name}: Lerngruppe als Text schreiben ({falsch})"]
    return daten, []


def _texte_pruefen(e: dict, texte: tuple, listen: tuple, wo: str, fehler: list[str], kinder: tuple = ()) -> bool:
    unbekannt = sorted(set(e) - set(texte) - set(listen) - set(kinder))
    if unbekannt:
        hinweis = f" (Lerngruppe gehört nach {LERNGRUPPEN})" if "lerngruppe" in unbekannt else ""
        fehler.append(f"{wo}: unbekannte Felder {unbekannt}{hinweis}")
        return False
    ok = True
    for k in texte:
        if k in e and not isinstance(e[k], str):
            fehler.append(f"{wo}: {k} muss ein Text in Anführungszeichen sein")
            ok = False
    for k in listen:
        if k in e and not (isinstance(e[k], list) and all(isinstance(x, str) for x in e[k])):
            fehler.append(f"{wo}: {k} muss eine Liste von Texten sein")
            ok = False
    if isinstance(e.get("archiviert"), str):
        try:
            date.fromisoformat(e["archiviert"])
        except ValueError:
            fehler.append(f"{wo}: archiviert als Datum schreiben, z. B. \"2026-11-03\"")
            ok = False
    return ok


def _id_pruefen(e: dict, wo: str, fehler: list[str]) -> bool:
    wert = e.get("id")
    if not isinstance(wert, str) or not wert:
        fehler.append(f"{wo}: id fehlt")
        return False
    if not ID_MUSTER.fullmatch(wert) or len(wert) > ID_MAX:
        fehler.append(f"{wo}: id {wert!r} nur aus Kleinbuchstaben, Ziffern und Bindestrichen, höchstens {ID_MAX}")
        return False
    return True


def _pflicht(e: dict, felder: tuple, wo: str, fehler: list[str]) -> bool:
    fehlt = [k for k in felder if not (isinstance(e.get(k), str) and e[k].strip())]
    for k in fehlt:
        fehler.append(f"{wo}: {k} fehlt")
    return not fehlt


def _neu(daten: dict, fehler: list[str]) -> Struktur:
    s = Struktur("neu")
    faecher, klassen = {}, {}
    for nr, e in enumerate(daten.get("fach", []), 1):
        wo = f"{DATEI}, Fach {nr}"
        if not (_texte_pruefen(e, FACH_TEXTE, (), wo, fehler) and _id_pruefen(e, wo, fehler)
                and _pflicht(e, ("name",), wo, fehler)):
            continue
        f = {"id": e["id"], "ebene": "fach", "name": e["name"].strip(), "kurzform": e.get("kurzform", ""),
             "archiviert": e.get("archiviert", ""), "klassen": []}
        f["im_archiv"] = bool(f["archiviert"])
        faecher[f["id"]] = f
        s.faecher.append(f)
    for nr, e in enumerate(daten.get("klasse", []), 1):
        wo = f"{DATEI}, Klasse {nr}"
        if not (_texte_pruefen(e, KLASSE_TEXTE, (), wo, fehler) and _id_pruefen(e, wo, fehler)
                and _pflicht(e, ("fach", "name"), wo, fehler)):
            continue
        fach = faecher.get(e["fach"])
        if fach is None:
            fehler.append(f"{wo} ({e['id']}): Fach {e['fach']!r} gibt es nicht")
            continue
        k = {"id": e["id"], "ebene": "klasse", "fach": fach["name"], "fach_id": fach["id"], "name": e["name"].strip(),
             "schuljahr": e.get("schuljahr", ""), "lerngruppe": "", "herkunft": e.get("herkunft", ""),
             "archiviert": e.get("archiviert", ""), "im_archiv": bool(e.get("archiviert")) or fach["im_archiv"],
             "reihen": []}
        fach["klassen"].append(k["id"])
        klassen[k["id"]] = k
        s.klassen.append(k)
    for nr, e in enumerate(daten.get("reihe", []), 1):
        wo = f"{DATEI}, Reihe {nr}"
        if not (_texte_pruefen(e, REIHE_TEXTE, REIHE_LISTEN, wo, fehler, ("stunde",)) and _id_pruefen(e, wo, fehler)
                and _pflicht(e, ("klasse",), wo, fehler)):
            continue
        klasse = klassen.get(e["klasse"])
        if klasse is None:
            fehler.append(f"{wo} ({e['id']}): Klasse {e['klasse']!r} gibt es nicht")
            continue
        r = _reihe(e, klasse, wo, fehler)
        if r is None:
            continue
        stunden = e.get("stunde", [])
        if not isinstance(stunden, list) or not all(isinstance(x, dict) for x in stunden):
            fehler.append(f"{wo} ({e['id']}): Stunden als [[reihe.stunde]] schreiben")
            continue
        for snr, st in enumerate(stunden, 1):
            swo = f"{wo} ({e['id']}), Stunde {snr}"
            if not (_texte_pruefen(st, STUNDE_TEXTE, (), swo, fehler) and _id_pruefen(st, swo, fehler)
                    and _pflicht(st, ("thema",), swo, fehler)):
                continue
            _stunde_dazu(r, st["id"], st, swo, fehler)
        s.reihen.append(r)
    return s


def _alt(eintraege: list, fehler: list[str]) -> Struktur:
    """Altes Format: Fach und Klasse aus den Texten jeder Reihe ableiten."""
    s = Struktur("alt")
    faecher, klassen = {}, {}
    for nr, e in enumerate(eintraege, 1):
        wo = f"{DATEI}, Reihe {nr}"
        if not (_texte_pruefen(e, ALT_TEXTE, REIHE_LISTEN, wo, fehler, ("stunde",))
                and _pflicht(e, ("fach", "klasse"), wo, fehler)):
            continue
        if "id" in e and not _id_pruefen(e, wo, fehler):
            continue
        fach_name, klasse_name, schuljahr = e["fach"].strip(), e["klasse"].strip(), e.get("schuljahr", "").strip()
        fach = faecher.get(fach_name)
        if fach is None:
            fach = {"id": kennung(fach_name), "ebene": "fach", "name": fach_name, "kurzform": "", "archiviert": "",
                    "im_archiv": False, "klassen": []}
            faecher[fach_name] = fach
            s.faecher.append(fach)
        schluessel = (fach_name, klasse_name, schuljahr)
        klasse = klassen.get(schluessel)
        if klasse is None:
            klasse = {"id": kennung(fach_name, klasse_name, schuljahr), "ebene": "klasse", "fach": fach_name,
                      "fach_id": fach["id"], "name": klasse_name, "schuljahr": schuljahr, "lerngruppe": "",
                      "herkunft": "", "archiviert": "", "im_archiv": False, "reihen": []}
            klassen[schluessel] = klasse
            fach["klassen"].append(klasse["id"])
            s.klassen.append(klasse)
        e = {**e, "id": e.get("id") or kennung(fach_name, klasse_name, e.get("titel", ""))}
        r = _reihe(e, klasse, wo, fehler)
        if r is None:
            continue
        r["lerngruppe"] = e.get("lerngruppe", "")  # im alten Format steht sie an der Reihe
        stunden = e.get("stunde", [])
        if not isinstance(stunden, list) or not all(isinstance(x, dict) for x in stunden):
            fehler.append(f"{wo}: Stunden als [[reihe.stunde]] schreiben")
            continue
        nummern = set()
        for st in stunden:
            swo = f"{wo}, Stunde {st.get('nr')}"
            if set(st) - set(ALT_STUNDE):
                fehler.append(f"{swo}: unbekannte Felder {sorted(set(st) - set(ALT_STUNDE))}")
                continue
            if not isinstance(st.get("nr"), int) or isinstance(st["nr"], bool) or st["nr"] < 1:
                fehler.append(f"{wo}: Stunde braucht nr als ganze Zahl ab 1")
                continue
            if st["nr"] in nummern:
                fehler.append(f"{swo}: gibt es doppelt")
                continue
            nummern.add(st["nr"])
            _pflicht(st, ("thema",), swo, fehler)
        if len(nummern) == len(stunden) and all(isinstance(st.get("thema"), str) for st in stunden):
            for st in sorted(stunden, key=lambda x: x["nr"]):
                _stunde_dazu(r, f"{r['id']}-stunde-{st['nr']}", st, f"{wo}, Stunde {st['nr']}", fehler)
        s.reihen.append(r)
    # Abgeleitete ids von Fach und Klasse dürfen keine gespeicherte id treffen (z. B. die Platzhalter-Reihe
    # darstellendes-spiel-kurs-11 und Kurs 11 selbst); dann bekommt die abgeleitete einen Zusatz.
    vergeben = {r["id"] for r in s.reihen} | {st["id"] for st in s.stunden()}
    for f in s.faecher:
        if f["id"] in vergeben:
            f["id"] += "-fach"
    for k in s.klassen:
        if k["id"] in vergeben:
            k["id"] += "-klasse"
        k["fach_id"] = faecher[k["fach"]]["id"]
    for f in s.faecher:
        f["klassen"] = [k["id"] for k in s.klassen if k["fach"] == f["name"]]
    for k in s.klassen:
        for r in s.reihen:
            if r["id"] in k["reihen"]:
                r["klasse_id"], r["fach_id"] = k["id"], k["fach_id"]
    return s


def _reihe(e: dict, klasse: dict, wo: str, fehler: list[str]) -> dict | None:
    stand = e.get("stand", "laufend")
    if stand not in STAENDE:
        fehler.append(f"{wo} ({e['id']}): stand {stand!r}, erlaubt {list(STAENDE)}")
        return None
    r = {"id": e["id"], "ebene": "reihe", "fach": klasse["fach"], "fach_id": klasse["fach_id"],
         "klasse": klasse["name"], "klasse_id": klasse["id"], "schuljahr": klasse["schuljahr"], "lerngruppe": "",
         "titel": e.get("titel", "").strip(), "reihenfrage": e.get("reihenfrage", "").strip(),
         "notizen": e.get("notizen", ""), "stand": stand, "herkunft": e.get("herkunft", ""),
         "archiviert": e.get("archiviert", ""), "im_archiv": bool(e.get("archiviert")) or klasse["im_archiv"],
         **{k: list(e.get(k, [])) for k in REIHE_LISTEN}, "stunden": [], "ausgeblendete_stunden": []}
    klasse["reihen"].append(r["id"])
    return r


def _stunde_dazu(r: dict, kennung_: str, st: dict, wo: str, fehler: list[str]) -> None:
    marke = st.get("marke", "")
    if marke and marke not in MARKEN:
        fehler.append(f"{wo}: marke {marke!r}, erlaubt {list(MARKEN)}")
        return
    archiviert = st.get("archiviert", "")
    s = {"id": kennung_, "ebene": "stunde", "reihe_id": r["id"], "nr": None, "thema": st["thema"].strip(),
         "marke": marke, "archiviert": archiviert, "im_archiv": bool(archiviert) or r["im_archiv"]}
    if archiviert:
        r["ausgeblendete_stunden"].append(s)
    else:
        s["nr"] = len(r["stunden"]) + 1  # Nummer nur über sichtbare Stunden (F3)
        r["stunden"].append(s)


def _gemeinsam_pruefen(s: Struktur, lerngruppen: dict, fehler: list[str]) -> None:
    """Regeln über alle Ebenen: id einmalig, Herkunft zeigt auf dieselbe Ebene, ein Agent in höchstens einer Reihe,
    Lerngruppen nur für vorhandene Klassen."""
    gesehen: dict[str, str] = {}
    for o in s.faecher + s.klassen + s.reihen + s.stunden():
        if o["id"] in gesehen:
            fehler.append(f"{DATEI}: id {o['id']!r} gibt es doppelt ({gesehen[o['id']]} und {o['ebene']})")
        else:
            gesehen[o["id"]] = o["ebene"]
    for o in s.klassen + s.reihen:
        if o["herkunft"] and gesehen.get(o["herkunft"]) != o["ebene"]:
            fehler.append(f"{DATEI} ({o['id']}): herkunft {o['herkunft']!r} ist keine {o['ebene'].capitalize()}")
    agenten: dict[str, str] = {}
    for r in s.reihen:
        for a in r["agenten"]:
            if a in agenten:
                fehler.append(f"{DATEI}: Agent {a!r} steht in zwei Reihen ({agenten[a]} und {r['id']}), "
                              "erlaubt ist höchstens eine")
            agenten.setdefault(a, r["id"])
    klassen = {k["id"] for k in s.klassen}
    for k in sorted(set(lerngruppen) - klassen):
        fehler.append(f"{LERNGRUPPEN}: Klasse {k!r} gibt es nicht in {DATEI}")


def _lerngruppen_einsetzen(s: Struktur, lerngruppen: dict) -> None:
    for k in s.klassen:
        k["lerngruppe"] = lerngruppen.get(k["id"], "")
    klassen = {k["id"]: k for k in s.klassen}
    for r in s.reihen:
        r["lerngruppe"] = r["lerngruppe"] or klassen[r["klasse_id"]]["lerngruppe"]


# --- Quellen für haengt_dran ---------------------------------------------------------------------------------------

def _passt_zu(kennung_: str):
    return lambda e: isinstance(e, dict) and kennung_ in (e.get("reihe"), e.get("ort"))


def _jsons(basis: Path, ordner: tuple[str, ...]) -> list:
    """JSON-Einträge der Warteschlange (nur lesen, legt keine Ordner an). Unlesbare zählen nicht."""
    eintraege = []
    for name in ordner:
        for pfad in sorted((basis / name).glob("*.json")):
            try:
                eintraege.append(json.loads(pfad.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
    return eintraege


def _jsonl(pfad: Path) -> list:
    try:
        zeilen = pfad.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    eintraege = []
    for z in zeilen:
        try:
            eintraege.append(json.loads(z))
        except ValueError:
            continue
    return eintraege


def _zustand(instanz: Path, webapp_daten: Path) -> dict:
    """Zustand der Web-App zu dieser Instanz (Dateiname wie shared/webapp/zustand.py)."""
    schluessel = hashlib.sha256(str(instanz.resolve()).encode()).hexdigest()[:12]
    try:
        daten = json.loads((webapp_daten / "zustand" / f"{schluessel}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return daten if isinstance(daten, dict) else {}


def _im_zustand(kennung_: str, zustand: dict) -> int:
    """Stunden der Web-App an der Reihe, Material an Reihe oder Stunde, Lias Zuordnungen."""
    anzahl = len((zustand.get("stunden") or {}).get(kennung_) or [])
    anzahl += sum(1 for v in (zustand.get("stunde_von") or {}).values()
                  if isinstance(v, dict) and kennung_ in (v.get("reihe"), v.get("stunde")))
    anzahl += sum(1 for v in (zustand.get("reihe_von") or {}).values() if v == kennung_)
    return anzahl


def _verweise(kennung_: str, instanz: Path) -> list[str]:
    """Dateien der Agenten (lia/<agent>/*.toml, *.py), die die id in Anführungszeichen nennen."""
    muster = re.compile(rf"[\"']{re.escape(kennung_)}[\"']")
    treffer = []
    for pfad in sorted(instanz.parent.glob("*/*")):
        if pfad.suffix not in (".toml", ".py") or not pfad.is_file() or pfad.resolve().parent == instanz.resolve():
            continue  # die Instanz selbst (auch lia/unterricht/reihen.toml, ein Symlink dorthin) zählt nicht
        try:
            if muster.search(pfad.read_text(encoding="utf-8")):
                treffer.append(str(pfad.relative_to(instanz.parent.parent)))
        except (OSError, UnicodeDecodeError):
            continue
    return treffer


def main(argumente: list[str]) -> int:
    instanz = Path(argumente[0]) if argumente else LIA_INSTANZ
    fehler = pruefen(instanz)
    if fehler:
        print("\n".join(fehler), file=sys.stderr)
        return 1
    s = laden(instanz)
    print(f"Struktur in Ordnung ({instanz / DATEI}, Format {s.format}): {len(s.faecher)} Fächer, "
          f"{len(s.klassen)} Klassen, {len(s.reihen)} Reihen, {len(s.stunden())} Stunden")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
