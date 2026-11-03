"""Lia pflegt ihre Struktur Fach → Klasse/Kurs → Reihe → Stunde mit Terminen: Schreib-Operationen auf
lia/instanz/reihen.toml und lerngruppen.toml (Strukturplan docs/struktur-pflege-plan.md, Abschnitte 3, 4, 6, 7;
Bauschritt 4). Gelesen wird über agentkit.struktur, gerechnet mit agentkit.termine, geschrieben mit
agentkit.blockeditor, damit ein Diff der App aussieht wie Jans Handänderungen.

Jans Grundsatz Flexibilität (03.11.): Verschieben ist immer einfach, gesperrt wird nur, was Daten kaputt macht.
Keine Operation verschiebt etwas, das Lia nicht ausgelöst hat.

Aufruf (Web-App, später Skripte für Jan):
  from agentkit import strukturpflege as sp
  aus = sp.ausfuehren("reihe_anlegen", {"klasse": "ethik-8", "titel": "Würde"}, gesehen=None)
  aus.aktion (id fürs Rückgängig), aus.text („Reihe „Würde“ in Ethik 8 (2026/27) angelegt“), aus.hinweise,
  aus.neue_id, aus.geaendert, aus.gesichert (Commit gelungen)
  sp.rueckgaengig(aus.aktion); sp.letzte(20) für „Letzte Änderungen“; sp.OPERATIONEN (Name -> Beschreibung)
  sp.vorschau(operation, argumente, text, lerngruppen_text) rechnet nur (Tests, Vorschau), schreibt nichts.
Fehler (Text immer für Lia lesbar, nie mit Lerngruppen-Text):
  PflegeFehler        Eingabe falsch oder Datei gerade nicht beschreibbar (Jan ist dann schon informiert)
  Konflikt            „gesehen“ passt nicht mehr bzw. Rückgängig nach fremder Änderung: neu laden
  Handaenderung       reihen.toml hat ungespeicherte Handänderungen (Jan bekommt eine Meldung)
  HaengtDran          Löschen geht nicht, .haken wie struktur.haengt_dran: die App bietet Archivieren an
  termine.Belegt      Ziel belegt: einmal fragen, dann mit bei_belegt "nachruecken" oder "tauschen" erneut

Ablauf einer Änderung (7.2): Sperre <instanz>/.reihen.sperre; frisch lesen; die Datei muss gültig sein; Konflikt
nur, wenn sich einer der Werte aus `gesehen` ({id: {feld: wert, wie struktur ihn liefert}}) geändert hat; Operation
auf den aktuellen Text; neuen Text mit tomllib und struktur prüfen; hat reihen.toml ungespeicherte Änderungen, die
nicht vom letzten Schreiben der App stammen: nicht schreiben, Meldung an Jan; atomar auf den echten Pfad (nie auf
den Symlink lia/unterricht/reihen.toml); Aktion mit Gegen-Operation in die Aktionsablage; commit-daten.sh mit
„lia/instanz: <Text> (<von>)“, nur wenn die Datei lia/instanz/reihen.toml des Repos ist. Die Lerngruppe (F6) geht in
lerngruppen.toml (0600, nicht im Repo) und nie in Commit, Log, Meldung oder Aktionsliste; ihr alter Text liegt für
Rückgängig nur in der Aktionsablage (Ordner 0700, Dateien 0600, Standard shared/webapp/data/aktionen/<instanz>/).
"""

import fcntl
import hashlib
import json
import logging
import os
import random
import re
import secrets
import subprocess
import tomllib
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from . import blockeditor as be
from . import struktur, termine
from .struktur import DATEI, LERNGRUPPEN, LIA_INSTANZ, WEBAPP_DATEN

SPERRE = ".reihen.sperre"
REPO_PFAD = Path("lia") / "instanz" / DATEI  # nur diese Datei committet commit-daten.sh
VON_LIA = "Lia, Web-App"
MELDE_AGENT = "webapp"
AKTIONEN_BEHALTEN = 1000
LIA_JAN_WEISS = "Speichern geht gerade nicht. Jan ist informiert."

# Reihenfolge der Schlüssel je Block, wie in Jans Datei; neue Zeilen kommen an diese Stelle.
ORDNUNG = {
    "schule": ("bundesland",),
    "fach": ("id", "name", "kurzform", "archiviert"),
    "klasse": ("id", "fach", "name", "schuljahr", "herkunft", "ausfall", "zusatz", "archiviert"),
    "klasse.zeitplan": termine.ZEITPLAN_FELDER,
    "reihe": ("id", "klasse", "titel", "reihenfrage", "stand", "herkunft", "notizen", "behandelt", "merksaetze",
              "bisherige_reihen", "agenten", "archiviert"),
    "reihe.stunde": ("id", "termin", "thema", "marke", "archiviert"),
}
AENDERBAR = {
    "fach": ("name", "kurzform"),
    "klasse": ("name", "schuljahr"),
    "reihe": ("titel", "reihenfrage", "stand", "notizen", "behandelt", "merksaetze"),
    "stunde": ("thema", "marke"),
}
FELDNAMEN = {"name": "Name", "kurzform": "Kurzform", "schuljahr": "Schuljahr", "titel": "Titel",
             "reihenfrage": "Reihenfrage", "stand": "Stand", "notizen": "Notizen", "behandelt": "Behandelt",
             "merksaetze": "Merksätze", "thema": "Thema", "marke": "Marke"}
LAENGE = {"name": 40, "kurzform": 12, "titel": 120, "thema": 120, "reihenfrage": 300, "notizen": 5000,
          "behandelt": 120, "merksaetze": 600, "lerngruppe": 3000}
_SCHULJAHR = re.compile(r"(\d{4})/(\d{2})")
_AKTION_ID = re.compile(r"\d{8}-\d{6}-\d{6}")  # nach Zeit sortierbar


class PflegeFehler(Exception):
    """Text für Lia (nie mit Lerngruppen-Text)."""


class Konflikt(PflegeFehler):
    pass


class Handaenderung(PflegeFehler):
    pass


class HaengtDran(PflegeFehler):
    def __init__(self, text: str, haken: list[dict]):
        super().__init__(text)
        self.haken = haken


@dataclass
class Umgebung:
    """Wo und wie geschrieben wird. Standard: echte Instanz lia/instanz, Ablage der Web-App, Meldung an Jan."""
    instanz: Path = LIA_INSTANZ
    ablage: Path | None = None            # Aktionsablage; Standard WEBAPP_DATEN/aktionen/<schlüssel der instanz>
    webapp_daten: Path | None = None      # für haengt_dran (Standard shared/webapp/data)
    kalender: termine.Kalender | None = None  # Standard aus [schule] bundesland und ferien.json
    ferien_datei: Path | None = None
    melden: Callable[[str], object] | None = None  # Standard meldungen.melden("webapp", text)
    commit: bool = True                   # commit-daten.sh, wenn die Datei lia/instanz/reihen.toml des Repos ist
    commit_zeit: int = 300                # Sekunden; commit-daten.sh wartet auf commit.sperre
    heute: date | None = None
    zufall: random.Random | None = None   # für Stunden-ids (Tests: fester Startwert)
    log: logging.Logger | None = None


@dataclass
class Rechnung:
    """Ergebnis von vorschau(): neue Texte, nichts geschrieben."""
    text: str
    lerngruppen: str
    beschreibung: str
    hinweise: list[str] = field(default_factory=list)
    neue_id: str | None = None
    gegen: dict = field(default_factory=dict)  # {"reihen": blockeditor.gegen oder None, "lerngruppen": ...}


@dataclass
class Ausgang:
    geaendert: bool
    text: str
    aktion: str | None = None
    hinweise: list[str] = field(default_factory=list)
    neue_id: str | None = None
    gesichert: bool = False  # Commit gelungen (oder nicht nötig)
    commit: str | None = None


OPERATIONEN: dict[str, str] = {}
_FUNKTIONEN: dict[str, Callable] = {}


def _operation(name: str, beschreibung: str):
    def eintragen(f):
        OPERATIONEN[name] = beschreibung
        _FUNKTIONEN[name] = f
        return f
    return eintragen


# --- Rechnen (ohne Dateien) ---------------------------------------------------------------------------------------

def vorschau(operation: str, argumente: dict | None, text: str, lerngruppen: str = "",
             umgebung: Umgebung | None = None, gesehen: dict | None = None) -> Rechnung:
    """Operation auf die Texte anwenden, ohne zu schreiben. Fehler: PflegeFehler, termine.Belegt,
    blockeditor.EditorFehler (Datei mit Konstrukten, die der Editor nicht kennt)."""
    u = umgebung or Umgebung()
    if operation not in _FUNKTIONEN:
        raise PflegeFehler(f"Aktion {operation!r} gibt es nicht")
    a = _Arbeit(text, lerngruppen, u)
    a.gesehen_pruefen(gesehen or {})
    try:
        beschreibung = _FUNKTIONEN[operation](a, **(argumente or {}))
    except TypeError as e:
        raise PflegeFehler(f"Angaben zu {operation} passen nicht ({e})") from None
    except termine.Belegt:
        raise
    except termine.TermineFehler as e:
        raise PflegeFehler(str(e)) from None
    return a.ergebnis(beschreibung)


class _Arbeit:
    """Text als Dokument, dazu die aufgelöste Struktur. Operationen ändern das Dokument; s wird bei Bedarf neu
    gelesen (neu_lesen)."""

    def __init__(self, text: str, lerngruppen: str, u: Umgebung):
        self.u = u
        self.alt, self.lg_alt = text, lerngruppen
        self.dok = be.lesen(text)
        self.lg = be.lesen(lerngruppen, kopf_eintraege=True)
        self.instanz = Path(u.instanz) if u.instanz else None
        self.s = self._aufloesen(text, "Die Datei")
        if text.strip() and self.s.format != "neu":
            raise PflegeFehler("reihen.toml ist noch im alten Format; die App schreibt nur das neue")
        self.heute = (u.heute or date.today()).isoformat()
        self.zufall = u.zufall or random.Random(secrets.randbits(64))
        self.hinweise: list[str] = []
        self.neue_id: str | None = None
        self._kal: termine.Kalender | None = u.kalender

    # Lesen

    def lerngruppen(self) -> dict[str, str]:
        return {k: v for k, v in self.lg.daten().items()}

    def _aufloesen(self, text: str, was: str) -> struktur.Struktur:
        s, fehler = struktur.aufloesen(text, self.lerngruppen(), self.instanz)
        if fehler:
            raise PflegeFehler(f"{was} ist ungültig: " + "; ".join(fehler))
        return s

    def neu_lesen(self) -> None:
        self.s = self._aufloesen(self.dok.text(), "Das Ergebnis")

    def obj(self, kennung: str, ebene: str | None = None) -> dict:
        o = self.s.objekt(kennung) if isinstance(kennung, str) else None
        if o is None or (ebene and o["ebene"] != ebene):
            raise PflegeFehler(f"{_EBENE.get(ebene, 'Eintrag')} {kennung!r} gibt es nicht")
        return o

    def gesehen_pruefen(self, gesehen: dict) -> None:
        """7.2.4: Konflikt nur, wenn sich genau ein gesehener Wert geändert hat."""
        for kennung, felder in gesehen.items():
            o = self.s.objekt(kennung)
            if o is None:
                raise Konflikt("Inzwischen gelöscht, bitte neu laden")
            for feld, wert in felder.items():
                if not _gleich(o.get(feld), wert):
                    raise Konflikt(f"Inzwischen geändert ({FELDNAMEN.get(feld, feld)}), bitte neu laden")

    def kalender(self) -> termine.Kalender:
        if self._kal is None:
            self._kal = self.s.kalender(self.u.ferien_datei)
        return self._kal

    def plan(self, klassen_id: str) -> termine.Plan:
        k = self.obj(klassen_id, "klasse")
        return self.s.plan(klassen_id, self.kalender() if k["zeitplan"] else None)

    # Schreiben ins Dokument

    def setzen(self, kennung: str, schluessel: str, wert) -> bool:
        """Wert setzen; leer ("", [], None) entfernt die Zeile."""
        b = self.dok.block(kennung)
        if wert in (None, "", []):
            return b.entfernen(schluessel)
        return b.setzen(schluessel, wert, ORDNUNG[b.art])

    def neue_kennung(self, *teile: str) -> str:
        basis = struktur.kennung(*teile) or "neu"
        kandidat, n = basis, 1
        while not self._frei(kandidat):
            n += 1
            kandidat = f"{basis[:struktur.ID_MAX - len(str(n)) - 1]}-{n}"
        return kandidat

    def stunden_kennung(self) -> str:
        while True:
            kandidat = "s-" + "".join(self.zufall.choice("abcdefghijkmnpqrstuvwxyz23456789") for _ in range(6))
            if self._frei(kandidat):
                return kandidat

    def _frei(self, kandidat: str) -> bool:
        ids = {b.wert("id") for b in self.dok.bloecke}
        return kandidat not in ids and self.s.id_frei(kandidat, self.u.webapp_daten)

    def einfuegen(self, stelle: int, block: be.Block) -> None:
        self.dok.einfuegen(stelle, [block])

    def ergebnis(self, beschreibung: str) -> Rechnung:
        text, lg = be.pruefen(self.dok), be.pruefen(self.lg)
        self._aufloesen(text, "Das Ergebnis")
        _lg_pruefen(lg)
        g = {"reihen": be.gegen(self.alt, text) if text != self.alt else None,
             "lerngruppen": be.gegen(self.lg_alt, lg, kopf_eintraege=True) if lg != self.lg_alt else None}
        return Rechnung(text, lg, beschreibung, list(dict.fromkeys(self.hinweise)), self.neue_id, g)

    # Stellen für neue Blöcke (wie Jan: erst Fächer, dann Klassen, dann Reihen mit ihren Stunden)

    def _indizes(self, art: str) -> list[int]:
        return [i for i, b in enumerate(self.dok.bloecke) if b.art == art]

    def _vor_erstem(self, arten: tuple) -> int:
        return next((i for i, b in enumerate(self.dok.bloecke) if b.art in arten), len(self.dok.bloecke))

    def stelle_fach(self) -> int:
        f = self._indizes("fach")
        return self.dok.gruppe(f[-1]).stop if f else self._vor_erstem(("klasse", "reihe"))

    def stelle_klasse(self, fach_id: str) -> int:
        """Hinter der letzten nicht archivierten Klasse des Fachs, sonst hinter der letzten nicht archivierten."""
        bl = self.dok.bloecke
        klassen = self._indizes("klasse")
        aktiv = [i for i in klassen if not bl[i].wert("archiviert")]
        eigene = [i for i in aktiv if bl[i].wert("fach") == fach_id] or aktiv
        if eigene:
            return self.dok.gruppe(eigene[-1]).stop
        return klassen[0] if klassen else self._vor_erstem(("reihe",))

    def stelle_reihe(self, klassen_id: str) -> int:
        """Hinter der letzten Reihe der Klasse, sonst vor der ersten Reihe einer späteren Klasse."""
        bl = self.dok.bloecke
        eigene = [i for i in self._indizes("reihe") if bl[i].wert("klasse") == klassen_id]
        if eigene:
            return self.dok.gruppe(eigene[-1]).stop
        folge = [bl[i].wert("id") for i in self._indizes("klasse")]
        spaeter = set(folge[folge.index(klassen_id) + 1:]) if klassen_id in folge else set()
        return next((i for i in self._indizes("reihe") if bl[i].wert("klasse") in spaeter), len(bl))

    def stelle_stunde(self, reihe_id: str, sichtbar_stelle: int | None = None) -> int:
        """Vor der sichtbaren Stunde Nummer sichtbar_stelle+1 der Reihe, sonst am Ende der Reihe."""
        g = self.dok.gruppe(self.dok.index(reihe_id))
        sichtbare = [i for i in range(g.start + 1, g.stop) if not self.dok.bloecke[i].wert("archiviert")]
        if sichtbar_stelle is not None and sichtbar_stelle < len(sichtbare):
            return sichtbare[sichtbar_stelle]
        return g.stop

    def herausnehmen(self, kennung: str) -> list[be.Block]:
        return self.dok.herausnehmen(self.dok.gruppe(self.dok.index(kennung)))

    def reihe_ordnen(self, reihe_id: str, neue: list[str]) -> None:
        """Die Stunden aus neue nehmen ihre bisherigen Plätze in der Reihe in dieser Reihenfolge ein."""
        g = self.dok.gruppe(self.dok.index(reihe_id))
        bloecke = self.dok.bloecke[g.start + 1:g.stop]
        nach_id = {b.wert("id"): b for b in bloecke}
        drin, folge = set(neue), iter(neue)
        self.dok.bloecke[g.start + 1:g.stop] = [nach_id[next(folge)] if b.wert("id") in drin else b
                                                for b in bloecke]

    # Termine schreiben (Ergebnis einer Rechenregel aus agentkit.termine)

    def termine_schreiben(self, klassen_id: str, erg: termine.Ergebnis) -> None:
        for sid, k in erg.geaendert.items():
            self.setzen(sid, "termin", k or "")
        self.setzen(klassen_id, "ausfall", list(erg.ausfall))
        self.zeitplan_schreiben(klassen_id, erg.zeitplan)
        for sid in erg.ausblenden:
            self.setzen(sid, "archiviert", self.heute)
        for sid in erg.einblenden:
            self.setzen(sid, "archiviert", "")
        if erg.reihenfolge:
            self.reihe_ordnen(erg.vorher.reihe_von(erg.reihenfolge[0]), erg.reihenfolge)
        else:
            for rid in dict.fromkeys(filter(None, map(erg.vorher.reihe_von, erg.geaendert))):
                ids = [b.wert("id") for b in self.dok.unter(rid)]
                neu = termine.nach_datum(ids, erg.termine)
                if neu != ids:
                    self.reihe_ordnen(rid, neu)
        self.hinweise += erg.hinweise

    def zeitplan_schreiben(self, klassen_id: str, neu: list[dict]) -> None:
        bloecke = self.dok.unter(klassen_id)
        alt = termine.zeitplan_normal([b.daten() for b in bloecke])
        neu = termine.zeitplan_normal(list(neu))
        if alt == neu:
            return
        for b, a, n in zip(bloecke, alt, neu, strict=False):  # mehr oder weniger Einträge: siehe unten
            for k in termine.ZEITPLAN_FELDER:
                if a[k] != n[k]:
                    b.setzen(k, n[k], ORDNUNG["klasse.zeitplan"])
        stelle = self.dok.gruppe(self.dok.index(klassen_id)).stop
        self.dok.einfuegen(stelle, [be.neuer_block("klasse.zeitplan", list(e.items())) for e in neu[len(alt):]])
        for b in bloecke[len(neu):]:
            self.dok.bloecke.remove(b)

    # Texte

    def klasse_text(self, kennung: str) -> str:
        k = self.obj(kennung, "klasse")
        return f"{k['fach']} {k['name']}" + (f" ({k['schuljahr']})" if k["schuljahr"] else "")

    def name(self, kennung: str) -> str:
        """„Reihe „Würde“ in Ethik 9 (2026/27)“ usw. für Commit-Nachricht und Aktionsliste."""
        o = self.obj(kennung)
        if o["ebene"] == "fach":
            return f"Fach „{o['name']}“"
        if o["ebene"] == "klasse":
            return f"Klasse {self.klasse_text(kennung)}"
        if o["ebene"] == "reihe":
            return f"Reihe „{o['titel'] or 'ohne Titel'}“ in {self.klasse_text(o['klasse_id'])}"
        r = self.obj(o["reihe_id"])
        return f"Stunde „{o['thema'] or 'Thema offen'}“ in „{r['titel'] or 'ohne Titel'}“"


_EBENE = {"fach": "Fach", "klasse": "Klasse", "reihe": "Reihe", "stunde": "Stunde", None: "Eintrag"}


def _gleich(jetzt, gesehen) -> bool:
    if not jetzt and not gesehen:
        return True  # fehlt, "" und [] sind dasselbe
    if isinstance(jetzt, str) and isinstance(gesehen, str):
        return jetzt.strip() == gesehen.strip()
    return jetzt == gesehen


def _lg_pruefen(text: str) -> None:
    daten = tomllib.loads(text)
    if any(not isinstance(v, str) for v in daten.values()):
        raise PflegeFehler("lerngruppen.toml: Lerngruppe muss ein Text sein")


def _text(wert, feld: str, pflicht: bool = False) -> str:
    if wert is None:
        wert = ""
    if not isinstance(wert, str):
        raise PflegeFehler(f"{FELDNAMEN.get(feld, feld)}: bitte Text eingeben")
    wert = wert.strip()
    if pflicht and not wert:
        raise PflegeFehler(f"{FELDNAMEN.get(feld, feld)} fehlt")
    if len(wert) > LAENGE.get(feld, 5000):
        raise PflegeFehler(f"{FELDNAMEN.get(feld, feld)}: höchstens {LAENGE.get(feld, 5000)} Zeichen")
    return wert


def _liste(wert, feld: str) -> list[str]:
    if isinstance(wert, str):
        wert = wert.splitlines()
    if not isinstance(wert, list):
        raise PflegeFehler(f"{FELDNAMEN.get(feld, feld)}: bitte eine Liste")
    return [t for t in (_text(x, feld) for x in wert) if t]


def _schuljahr(wert, pflicht: bool = True) -> str:
    wert = _text(wert, "schuljahr", pflicht)
    m = _SCHULJAHR.fullmatch(wert)
    if wert and not (m and (int(m[1]) + 1) % 100 == int(m[2])):
        raise PflegeFehler("Schuljahr wie „2026/27“ schreiben")
    return wert


def _naechstes_schuljahr(wert: str) -> str:
    m = _SCHULJAHR.fullmatch(wert or "")
    if not m:
        raise PflegeFehler("Schuljahr fehlt")
    return f"{int(m[1]) + 1}/{(int(m[2]) + 1) % 100:02d}"


def _marke(wert) -> str:
    wert = _text(wert, "marke")
    if wert and wert not in struktur.MARKEN:
        raise PflegeFehler(f"Marke {wert!r}, erlaubt {', '.join(struktur.MARKEN)} oder keine")
    return wert


def _zeitplan(wert) -> list[dict]:
    if not isinstance(wert, list):
        raise PflegeFehler("Stundenplan: bitte eine Liste von Terminen")
    fehler = termine.zeitplan_pruefen(wert)
    if fehler:
        raise PflegeFehler("; ".join(fehler))
    return termine.zeitplan_normal(wert)


def _doppelte_klasse(a: _Arbeit, fach_id: str, name: str, schuljahr: str, ausser: str | None = None) -> None:
    for k in a.s.klassen:
        if (k["id"] != ausser and k["fach_id"] == fach_id and k["name"].casefold() == name.casefold()
                and k["schuljahr"] == schuljahr):
            raise PflegeFehler(f"Klasse {name} ({schuljahr}) in {k['fach']} gibt es schon")


def _laeuft_noch(a: _Arbeit, kennung: str) -> bool:
    if a.instanz is None:
        return False
    return any(map(struktur._passt_zu(kennung), struktur._jsons(a.instanz / "auftraege", ("neu",))))


# --- Operationen: Schule, Fach ------------------------------------------------------------------------------------

@_operation("schule_setzen", "Bundesland der Schule eintragen oder ändern (Ferien, Feiertage)")
def _schule_setzen(a: _Arbeit, bundesland: str) -> str:
    if bundesland not in termine.BUNDESLAENDER:
        raise PflegeFehler("Bitte ein Bundesland wählen")
    for b in a.dok.bloecke:
        if b.art == "schule":
            b.setzen("bundesland", bundesland, ORDNUNG["schule"])
            break
    else:
        a.einfuegen(0, be.neuer_block("schule", [("bundesland", bundesland)]))
    return f"Bundesland {termine.BUNDESLAENDER[bundesland]} eingetragen"


@_operation("fach_anlegen", "Fach anlegen")
def _fach_anlegen(a: _Arbeit, name: str, kurzform: str = "") -> str:
    name, kurzform = _text(name, "name", True), _text(kurzform, "kurzform")
    if any(f["name"].casefold() == name.casefold() for f in a.s.faecher):
        raise PflegeFehler(f"Fach {name} gibt es schon")
    a.neue_id = a.neue_kennung(name)
    a.einfuegen(a.stelle_fach(), be.neuer_block("fach", [("id", a.neue_id), ("name", name), ("kurzform", kurzform)]))
    return f"Fach „{name}“ angelegt"


@_operation("fach_aendern", "Name oder Kurzform eines Fachs ändern")
def _fach_aendern(a: _Arbeit, fach: str, **felder) -> str:
    return _aendern(a, fach, "fach", felder)


# --- Klasse/Kurs --------------------------------------------------------------------------------------------------

@_operation("klasse_anlegen", "Klasse oder Kurs anlegen, Stundenplan freiwillig")
def _klasse_anlegen(a: _Arbeit, fach: str, name: str, schuljahr: str, zeitplan: list | None = None,
                    herkunft: str = "") -> str:
    f = a.obj(fach, "fach")
    name, schuljahr = _text(name, "name", True), _schuljahr(schuljahr)
    _doppelte_klasse(a, f["id"], name, schuljahr)
    if herkunft:
        a.obj(herkunft, "klasse")
    a.neue_id = a.neue_kennung(f["id"], name)
    if a.neue_id != struktur.kennung(f["id"], name):
        a.neue_id = a.neue_kennung(f["id"], name, schuljahr)
    a.einfuegen(a.stelle_klasse(f["id"]), be.neuer_block("klasse", [
        ("id", a.neue_id), ("fach", f["id"]), ("name", name), ("schuljahr", schuljahr), ("herkunft", herkunft)]))
    if zeitplan:
        a.zeitplan_schreiben(a.neue_id, _zeitplan(zeitplan))
    a.neu_lesen()
    return f"Klasse {a.klasse_text(a.neue_id)} angelegt"


@_operation("klasse_aendern", "Name oder Schuljahr einer Klasse ändern")
def _klasse_aendern(a: _Arbeit, klasse: str, **felder) -> str:
    k = a.obj(klasse, "klasse")
    name = _text(felder.get("name", k["name"]), "name", True)
    schuljahr = _schuljahr(felder.get("schuljahr", k["schuljahr"]))
    _doppelte_klasse(a, k["fach_id"], name, schuljahr, ausser=k["id"])
    return _aendern(a, klasse, "klasse", felder)


@_operation("klasse_verschieben", "Klasse in ein anderes Fach (Korrektur); Reihen und Stunden gehen mit")
def _klasse_verschieben(a: _Arbeit, klasse: str, fach: str) -> str:
    k, f = a.obj(klasse, "klasse"), a.obj(fach, "fach")
    if k["fach_id"] == f["id"]:
        raise PflegeFehler("Die Klasse gehört schon zu diesem Fach")
    _doppelte_klasse(a, f["id"], k["name"], k["schuljahr"])
    text = f"Klasse {a.klasse_text(klasse)} nach {f['name']} verschoben"
    bloecke = a.herausnehmen(klasse)
    bloecke[0].setzen("fach", f["id"], ORDNUNG["klasse"])
    a.dok.einfuegen(a.stelle_klasse(f["id"]), bloecke)
    return text


@_operation("klasse_kopieren", "Ins nächste Schuljahr übernehmen: neue Klasse mit Herkunft, ohne Reihen")
def _klasse_kopieren(a: _Arbeit, klasse: str, name: str, schuljahr: str | None = None,
                     lerngruppe_mitnehmen: bool = False, zeitplan: list | None = None) -> str:
    k = a.obj(klasse, "klasse")
    alt = a.klasse_text(klasse)
    text = _klasse_anlegen(a, k["fach_id"], name, schuljahr or _naechstes_schuljahr(k["schuljahr"]),
                           zeitplan=zeitplan, herkunft=k["id"])
    if lerngruppe_mitnehmen and k["lerngruppe"]:
        a.lg.kopf_setzen(a.neue_id, k["lerngruppe"])
    return text.replace(" angelegt", f" aus {alt} übernommen")


@_operation("lerngruppe_setzen", "Lerngruppe einer Klasse (lerngruppen.toml, nicht im Repo)")
def _lerngruppe_setzen(a: _Arbeit, klasse: str, text: str) -> str:
    k = a.obj(klasse, "klasse")
    wert = _text(text, "lerngruppe")
    if wert:
        a.lg.kopf_setzen(k["id"], wert)
    else:
        a.lg.kopf_entfernen(k["id"])
    return f"Lerngruppe von {a.klasse_text(klasse)} geändert"


@_operation("stundenplan_setzen", "Stundenplan eintragen oder ändern, solange keine Stunde ihren Termin verliert")
def _stundenplan_setzen(a: _Arbeit, klasse: str, zeitplan: list) -> str:
    neu = _zeitplan(zeitplan)
    plan = a.plan(klasse)
    kal = a.kalender() if neu else plan.kalender
    danach = termine.Plan(zeitplan=tuple(neu), belegung=plan.belegung, reihen=plan.reihen, ausfall=plan.ausfall,
                          zusatz=plan.zusatz, ausgeblendet=plan.ausgeblendet, kalender=kal)
    verloren = [h for h in danach.hinweise() if h not in plan.hinweise()]
    if verloren:
        raise PflegeFehler(f"{len(verloren)} Stunden lägen dann nicht mehr auf einem Termin. Für einen neuen "
                           "Stundenplan ab einem Stichtag bitte „Stundenplan ab …“ nehmen")
    a.zeitplan_schreiben(klasse, neu)
    return f"Stundenplan von {a.klasse_text(klasse)} geändert"


@_operation("stundenplan_ab", "Neuer Stundenplan ab Stichtag (Halbjahr); Stunden danach bekommen neue Daten")
def _stundenplan_ab(a: _Arbeit, klasse: str, stichtag: str, zeitplan: list) -> str:
    erg = a.plan(klasse).stundenplan_ab(stichtag, zeitplan)
    a.termine_schreiben(klasse, erg)
    return f"Stundenplan von {a.klasse_text(klasse)} ab {termine.datum_lesen(stichtag):%d.%m.%Y} geändert"


@_operation("zusatztermin", "Einzelner Zusatztermin an der Klasse (Nachholen, Projekttag)")
def _zusatztermin(a: _Arbeit, klasse: str, termin: str) -> str:
    k = a.obj(klasse, "klasse")
    termine.kennung_lesen(termin)
    if termin in k["zusatz"] or termin in [t.kennung for t in a.plan(klasse).termine]:
        raise PflegeFehler(f"{termine.anzeige(termin)} ist schon ein Termin der Klasse")
    a.setzen(klasse, "zusatz", sorted(k["zusatz"] + [termin], key=termine.kennung_lesen))
    return f"Zusatztermin {termine.anzeige(termin)} in {a.klasse_text(klasse)}"


@_operation("zusatztermin_entfernen", "Zusatztermin entfernen (nur ohne Stunde darauf)")
def _zusatztermin_entfernen(a: _Arbeit, klasse: str, termin: str) -> str:
    k = a.obj(klasse, "klasse")
    if termin not in k["zusatz"]:
        raise PflegeFehler("Das ist kein Zusatztermin der Klasse")
    if a.plan(klasse).stunde_auf(termin):
        raise PflegeFehler("Auf dem Termin liegt eine Stunde; erst die Stunde verschieben")
    a.setzen(klasse, "zusatz", [t for t in k["zusatz"] if t != termin])
    return f"Zusatztermin {termine.anzeige(termin)} in {a.klasse_text(klasse)} entfernt"


# --- Reihe --------------------------------------------------------------------------------------------------------

def _stunden_bloecke(a: _Arbeit, reihe_id: str, themen: list[str], stelle: int) -> list[str]:
    ids = []
    for nr, thema in enumerate(themen):
        sid = a.stunden_kennung()
        a.dok.einfuegen(stelle + nr, [be.neuer_block("reihe.stunde", [("id", sid), ("thema", thema)])])
        ids.append(sid)
    return ids


def _zuteilen(a: _Arbeit, reihe_id: str, auswahl: list | None, ab: str | None, anzahl: int | None) -> int:
    """Termine zuteilen (4.5): Stunden ohne Termin bekommen sie der Reihe nach, für den Rest entstehen neue Stunden
    mit offenem Thema. Gibt die Zahl der zugeteilten Termine zurück."""
    a.neu_lesen()
    r = a.obj(reihe_id, "reihe")
    plan = a.plan(r["klasse_id"])
    if auswahl is not None:
        if not isinstance(auswahl, list) or not auswahl:
            raise PflegeFehler("Bitte Termine wählen")
        ziel = sorted(set(auswahl), key=termine.kennung_lesen)
        plan.zuteilen([], auswahl=ziel)  # prüft: Termine der Klasse und frei (sonst termine.Belegt)
    else:
        if not isinstance(anzahl, int) or isinstance(anzahl, bool) or anzahl < 1:
            raise PflegeFehler("Bitte die Zahl der Termine angeben")
        ziel = [t.kennung for t in plan.freie(termine.datum_lesen(ab) if ab else None, anzahl)]
        if len(ziel) < anzahl:
            a.hinweise.append(f"Es gibt nur {len(ziel)} freie Termine")
    ohne = [s["id"] for s in r["stunden"] if not s["termin"]]
    neue = _stunden_bloecke(a, reihe_id, [""] * max(0, len(ziel) - len(ohne)), a.stelle_stunde(reihe_id))
    a.neu_lesen()
    a.termine_schreiben(r["klasse_id"], a.plan(r["klasse_id"]).zuteilen(ohne + neue, auswahl=ziel))
    return len(ziel)


@_operation("reihe_anlegen", "Reihe anlegen; freiwillig Stunden ohne Termin oder gleich Termine zuteilen")
def _reihe_anlegen(a: _Arbeit, klasse: str, titel: str, stand: str = "geplant", reihenfrage: str = "",
                   stunden: list | None = None, termine: list | None = None, ab: str | None = None,
                   anzahl: int | None = None) -> str:
    k = a.obj(klasse, "klasse")
    titel, reihenfrage = _text(titel, "titel", True), _text(reihenfrage, "reihenfrage")
    if stand not in struktur.STAENDE:
        raise PflegeFehler(f"Stand {stand!r}, erlaubt {', '.join(struktur.STAENDE)}")
    a.neue_id = a.neue_kennung(k["id"], titel)
    a.einfuegen(a.stelle_reihe(k["id"]), be.neuer_block("reihe", [
        ("id", a.neue_id), ("klasse", k["id"]), ("titel", titel), ("reihenfrage", reihenfrage), ("stand", stand)]))
    themen = [_text(t, "thema") for t in (stunden or [])]
    _stunden_bloecke(a, a.neue_id, themen, a.stelle_stunde(a.neue_id))
    if termine is not None or anzahl is not None:
        _zuteilen(a, a.neue_id, termine, ab, anzahl)
    a.neu_lesen()
    return f"Reihe „{titel}“ in {a.klasse_text(k['id'])} angelegt"


@_operation("reihe_aendern", "Titel, Reihenfrage, Stand, Notizen, Behandelt, Merksätze einer Reihe ändern")
def _reihe_aendern(a: _Arbeit, reihe: str, **felder) -> str:
    return _aendern(a, reihe, "reihe", felder)


def _termin_behalten(a: _Arbeit, ziel_klasse: str, kennung: str) -> bool:
    """Behält eine Stunde beim Wechsel der Klasse ihren Termin? Nur, wenn er in der Ziel-Klasse frei ist."""
    if not kennung:
        return False
    plan = a.plan(ziel_klasse)
    return kennung in {t.kennung for t in plan.freie()}


@_operation("reihe_verschieben", "Reihe in eine andere Klasse (auch anderes Fach oder Archiv); Stunden gehen mit")
def _reihe_verschieben(a: _Arbeit, reihe: str, klasse: str) -> str:
    r, k = a.obj(reihe, "reihe"), a.obj(klasse, "klasse")
    if r["klasse_id"] == k["id"]:
        raise PflegeFehler("Die Reihe gehört schon zu dieser Klasse")
    text = f"{a.name(reihe)} nach {a.klasse_text(klasse)} verschoben"
    weg = 0
    for st in r["stunden"] + r["ausgeblendete_stunden"]:
        if st["termin"] and not _termin_behalten(a, k["id"], st["termin"]):
            a.setzen(st["id"], "termin", "")
            weg += 1
    if weg:
        a.hinweise.append(f"{weg} {'Stunde hat' if weg == 1 else 'Stunden haben'} in der neuen Klasse noch keinen "
                          "Termin")
    bloecke = a.herausnehmen(reihe)
    bloecke[0].setzen("klasse", k["id"], ORDNUNG["reihe"])
    a.dok.einfuegen(a.stelle_reihe(k["id"]), bloecke)
    return text


@_operation("reihe_zeitlich", "Reihe zeitlich verschieben: beginnt an einem anderen Termin")
def _reihe_zeitlich(a: _Arbeit, reihe: str, start: str, bei_belegt: str | None = None) -> str:
    r = a.obj(reihe, "reihe")
    a.termine_schreiben(r["klasse_id"], a.plan(r["klasse_id"]).reihe_verschieben(reihe, start, bei_belegt))
    return f"{a.name(reihe)} beginnt jetzt {termine.anzeige(start)}"


@_operation("reihe_kopieren", "Reihe in eine andere Klasse kopieren (neue ids, Stunden nur mit Thema)")
def _reihe_kopieren(a: _Arbeit, reihe: str, klasse: str, termine: list | None = None, ab: str | None = None,
                    anzahl: int | None = None) -> str:
    r, k = a.obj(reihe, "reihe"), a.obj(klasse, "klasse")
    roh = a.dok.block(reihe).daten()
    a.neue_id = a.neue_kennung(k["id"], r["titel"] or "reihe")
    werte = [("id", a.neue_id), ("klasse", k["id"])]
    for feld in ORDNUNG["reihe"][2:]:
        if feld == "stand":
            werte.append(("stand", "geplant"))
        elif feld == "herkunft":
            werte.append(("herkunft", r["id"]))
        elif feld not in ("agenten", "archiviert") and feld in roh:
            werte.append((feld, roh[feld]))
    a.einfuegen(a.stelle_reihe(k["id"]), be.neuer_block("reihe", werte))
    _stunden_bloecke(a, a.neue_id, [s["thema"] for s in r["stunden"]], a.stelle_stunde(a.neue_id))
    if termine is not None or anzahl is not None:
        _zuteilen(a, a.neue_id, termine, ab, anzahl)
    a.neu_lesen()
    return f"Reihe „{r['titel']}“ aus {a.klasse_text(r['klasse_id'])} nach {a.klasse_text(k['id'])} kopiert"


# --- Stunde -------------------------------------------------------------------------------------------------------

@_operation("stunde_anlegen", "Stunde anlegen, ans Ende oder vor eine Stunde; Thema darf offen bleiben")
def _stunde_anlegen(a: _Arbeit, reihe: str, thema: str = "", marke: str = "", vor: str | None = None,
                    termin: str | None = None, bei_belegt: str | None = None) -> str:
    r = a.obj(reihe, "reihe")
    thema, marke = _text(thema, "thema"), _marke(marke)
    if vor is not None:
        v = a.obj(vor, "stunde")
        if v["reihe_id"] != r["id"]:
            raise PflegeFehler("Die Stunde, vor die eingefügt wird, gehört zu einer anderen Reihe")
        stelle = a.dok.index(vor)
    else:
        stelle = a.stelle_stunde(reihe)
    a.neue_id = a.stunden_kennung()
    a.einfuegen(stelle, be.neuer_block("reihe.stunde", [("id", a.neue_id), ("thema", thema), ("marke", marke)]))
    a.neu_lesen()
    if termin:
        a.termine_schreiben(r["klasse_id"], a.plan(r["klasse_id"]).stunde_auf_termin(a.neue_id, termin, bei_belegt))
        a.neu_lesen()
    return f"{a.name(a.neue_id)} angelegt"


@_operation("stunde_aendern", "Thema oder Marke (UB, Prüfung) einer Stunde ändern")
def _stunde_aendern(a: _Arbeit, stunde: str, **felder) -> str:
    if "marke" in felder:
        felder["marke"] = _marke(felder["marke"])
    return _aendern(a, stunde, "stunde", felder)


@_operation("stunde_verschieben", "Stunde an eine andere Stelle der Reihe (Termine bleiben) oder in eine andere Reihe")
def _stunde_verschieben(a: _Arbeit, stunde: str, stelle: int, reihe: str | None = None) -> str:
    st = a.obj(stunde, "stunde")
    if st["archiviert"]:
        raise PflegeFehler("Ausgeblendete Stunde bitte erst wiederherstellen")
    if not isinstance(stelle, int) or isinstance(stelle, bool) or stelle < 0:
        raise PflegeFehler("Stelle fehlt")
    r = a.obj(st["reihe_id"])
    ziel = a.obj(reihe, "reihe") if reihe else r
    if ziel["id"] == r["id"]:
        folge = [s["id"] for s in r["stunden"]]
        if stelle >= len(folge):
            raise PflegeFehler(f"Stelle {stelle + 1} gibt es nicht, die Reihe hat {len(folge)} Stunden")
        if folge.index(stunde) == stelle:
            raise PflegeFehler("Die Stunde steht schon an dieser Stelle")
        a.termine_schreiben(r["klasse_id"], a.plan(r["klasse_id"]).stunde_verschieben(folge, stunde, stelle))
        return f"{a.name(stunde)} an Stelle {stelle + 1} verschoben"
    text = f"{a.name(stunde)} nach „{ziel['titel']}“ verschoben"
    if st["termin"]:
        a.setzen(stunde, "termin", "")
        a.hinweise.append("Die Stunde hat in der neuen Reihe noch keinen Termin")
    bloecke = a.herausnehmen(stunde)
    a.dok.einfuegen(a.stelle_stunde(ziel["id"], stelle), bloecke)
    return text


@_operation("stunde_kopieren", "Stunde in eine andere Reihe kopieren (nur das Thema)")
def _stunde_kopieren(a: _Arbeit, stunde: str, reihe: str) -> str:
    st, ziel = a.obj(stunde, "stunde"), a.obj(reihe, "reihe")
    a.neue_id = _stunden_bloecke(a, ziel["id"], [st["thema"]], a.stelle_stunde(ziel["id"]))[0]
    a.neu_lesen()
    return f"{a.name(stunde)} nach „{ziel['titel']}“ kopiert"


@_operation("stunde_auf_termin", "Stunde direkt auf einen Termin legen (auch in eine Lücke)")
def _stunde_auf_termin(a: _Arbeit, stunde: str, termin: str, bei_belegt: str | None = None) -> str:
    st = a.obj(stunde, "stunde")
    r = a.obj(st["reihe_id"])
    a.termine_schreiben(r["klasse_id"], a.plan(r["klasse_id"]).stunde_auf_termin(stunde, termin, bei_belegt))
    return f"{a.name(stunde)} auf {termine.anzeige(termin)} gelegt"


# --- Termin -------------------------------------------------------------------------------------------------------

@_operation("termine_zuteilen", "Freie Termine einer Reihe zuteilen (Häkchen oder „ab …, n Termine“)")
def _termine_zuteilen(a: _Arbeit, reihe: str, termine: list | None = None, ab: str | None = None,
                      anzahl: int | None = None) -> str:
    n = _zuteilen(a, reihe, termine, ab, anzahl)
    return f"{a.name(reihe)}: {n} {'Termin' if n == 1 else 'Termine'} zugeteilt"


@_operation("termine_freigeben", "Termine einer Reihe freigeben; leere Stunden verschwinden, andere bleiben ohne")
def _termine_freigeben(a: _Arbeit, reihe: str, termine: list) -> str:
    r = a.obj(reihe, "reihe")
    eigene = {s["termin"]: s for s in r["stunden"] + r["ausgeblendete_stunden"] if s["termin"]}
    if not termine or any(k not in eigene for k in termine):
        raise PflegeFehler("Bitte Termine dieser Reihe wählen")
    for k in termine:
        st = eigene[k]
        if not st["thema"] and not st["marke"] and not a.s.haengt_dran(st["id"], a.u.webapp_daten):
            a.herausnehmen(st["id"])
        else:
            a.setzen(st["id"], "termin", "")
    return f"{a.name(reihe)}: {len(termine)} {'Termin' if len(termine) == 1 else 'Termine'} freigegeben"


@_operation("ausfall", "Termin fällt aus: folge \"nachruecken\" (alles rückt nach) oder \"faellt_weg\" (Stunde fällt weg)")
def _ausfall(a: _Arbeit, klasse: str, termin: str, folge: str) -> str:
    plan = a.plan(klasse)
    if folge == termine.NACHRUECKEN:
        erg, wie = plan.alles_rueckt_nach(termin), "alles rückt nach"
    elif folge == "faellt_weg":
        erg, wie = plan.stunde_faellt_weg(termin), "die Stunde fällt weg"
    else:
        raise PflegeFehler("Bitte wählen: alles rückt nach oder die Stunde fällt weg")
    a.termine_schreiben(klasse, erg)
    return f"{a.klasse_text(klasse)}: {termine.anzeige(termin)} fällt aus, {wie}"


@_operation("ausfall_aufheben", "Gestrichenen Termin wieder frei machen")
def _ausfall_aufheben(a: _Arbeit, klasse: str, termin: str) -> str:
    a.termine_schreiben(klasse, a.plan(klasse).ausfall_aufheben(termin))
    return f"{a.klasse_text(klasse)}: {termine.anzeige(termin)} findet wieder statt"


# --- Für alle Ebenen ----------------------------------------------------------------------------------------------

def _aendern(a: _Arbeit, kennung: str, ebene: str, felder: dict) -> str:
    """Felder setzen, die die Maske ändern darf (Aktionsmatrix 4.x). id ändert sich nie (Testregel 1)."""
    o = a.obj(kennung, ebene)
    name = a.name(kennung)
    if not felder:
        raise PflegeFehler("Nichts zu ändern")
    for feld in felder:
        if feld == "id":
            raise PflegeFehler("Eine id ändert sich nie")
        if feld not in AENDERBAR[ebene]:
            raise PflegeFehler(f"{FELDNAMEN.get(feld, feld)} ändert diese Aktion nicht")
    geaendert = []
    for feld, wert in felder.items():
        if feld in ("behandelt", "merksaetze"):
            wert = _liste(wert, feld)
        elif feld == "stand":
            if wert not in struktur.STAENDE:
                raise PflegeFehler(f"Stand {wert!r}, erlaubt {', '.join(struktur.STAENDE)}")
        elif feld == "schuljahr":
            wert = _schuljahr(wert)
        else:
            wert = _text(wert, feld, pflicht=feld in ("name", "titel"))
        if not _gleich(o.get(feld), wert) and a.setzen(kennung, feld, wert):
            geaendert.append(FELDNAMEN[feld])
    if not geaendert:
        return f"{name}: nichts geändert"
    a.neu_lesen()
    jetzt = f" (jetzt „{felder['titel'].strip()}“)" if "Titel" in geaendert else ""
    return f"{name}: {', '.join(geaendert)} geändert{jetzt}"


@_operation("archivieren", "Fach, Klasse, Reihe archivieren oder Stunde ausblenden (eine Zeile, nichts geht verloren)")
def _archivieren(a: _Arbeit, id: str) -> str:
    o = a.obj(id)
    if o["archiviert"]:
        raise PflegeFehler("Ist schon archiviert")
    if o["ebene"] == "reihe" and _laeuft_noch(a, id):
        a.hinweise.append("Ein Auftrag läuft noch; sein Ergebnis landet im Archiv")
    text = f"{a.name(id)} {'ausgeblendet' if o['ebene'] == 'stunde' else 'archiviert'}"
    a.setzen(id, "archiviert", a.heute)
    return text


@_operation("wiederherstellen", "Archiviertes oder Ausgeblendetes zurückholen, genau wie vorher")
def _wiederherstellen(a: _Arbeit, id: str) -> str:
    o = a.obj(id)
    if not o["archiviert"]:
        if o["im_archiv"]:
            raise PflegeFehler("Archiviert ist die Klasse oder das Fach darüber; bitte das wiederherstellen")
        raise PflegeFehler("Ist nicht archiviert")
    a.setzen(id, "archiviert", "")
    return f"{a.name(id)} wiederhergestellt"


@_operation("loeschen", "Löschen, nur wenn nichts dranhängt (sonst HaengtDran: Archivieren anbieten)")
def _loeschen(a: _Arbeit, id: str) -> str:
    o = a.obj(id)
    haken = a.s.haengt_dran(id, a.u.webapp_daten)
    if haken:
        raise HaengtDran("Löschen geht nicht, daran hängt: " + ", ".join(h["text"] for h in haken)
                         + ". Archivieren geht immer.", haken)
    text = f"{a.name(id)} gelöscht"
    a.herausnehmen(id)
    if o["ebene"] == "klasse":
        a.lg.kopf_entfernen(id)
    return text


# --- Ablauf mit Dateien -------------------------------------------------------------------------------------------

def ausfuehren(operation: str, argumente: dict | None = None, gesehen: dict | None = None, von: str = VON_LIA,
               umgebung: Umgebung | None = None) -> Ausgang:
    """Eine Änderung mit allem, was dazugehört (siehe Kopf). Ohne Änderung: Ausgang.geaendert False, nichts
    geschrieben."""
    u = umgebung or Umgebung()
    return _ablauf(u, von, operation, lambda text, lg: vorschau(operation, argumente, text, lg, u, gesehen))


def rueckgaengig(aktion_id: str, von: str = VON_LIA, umgebung: Umgebung | None = None) -> Ausgang:
    """Gegen-Aktion als neue Änderung (eigener Commit „Rückgängig: …“). Geht, solange die betroffenen Blöcke seitdem
    unverändert sind; sonst Konflikt und nichts geschrieben."""
    u = umgebung or Umgebung()
    ablage = _ablage(u)
    if not isinstance(aktion_id, str) or not _AKTION_ID.fullmatch(aktion_id):
        raise PflegeFehler("Diese Änderung gibt es nicht")
    try:
        aktion = json.loads((ablage / f"{aktion_id}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise PflegeFehler("Diese Änderung gibt es nicht (mehr)") from None
    if aktion.get("zurueckgenommen"):
        raise PflegeFehler("Diese Änderung ist schon rückgängig gemacht")

    def rechnen(text: str, lg: str) -> Rechnung:
        g = aktion["gegen"]
        try:
            neu = be.zurueck(g["reihen"], text) if g.get("reihen") else text
            lg_neu = be.zurueck(g["lerngruppen"], lg, kopf_eintraege=True) if g.get("lerngruppen") else lg
        except be.EditorKonflikt:
            raise Konflikt("Rückgängig geht nicht mehr: daran wurde inzwischen etwas geändert") from None
        a = _Arbeit(text, lg, u)
        a.dok, a.lg = be.lesen(neu), be.lesen(lg_neu, kopf_eintraege=True)
        return a.ergebnis(f"Rückgängig: {aktion['text']}")

    return _ablauf(u, von, "rueckgaengig", rechnen, rueckgaengig_von=aktion_id)


def letzte(anzahl: int = 20, umgebung: Umgebung | None = None) -> list[dict]:
    """„Letzte Änderungen“, neueste zuerst: id, zeit, text, von, operation, zurueckgenommen (id der Gegen-Aktion
    oder None), rueckgaengig_von. Ohne Gegen-Operation und ohne Lerngruppen-Text."""
    ablage = _ablage(Umgebung() if umgebung is None else umgebung)
    liste = []
    aktionen = [p for p in ablage.glob("*.json") if _AKTION_ID.fullmatch(p.stem)] if ablage.exists() else []
    for pfad in sorted(aktionen, reverse=True)[:anzahl]:
        try:
            a = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        liste.append({k: a.get(k) for k in ("id", "zeit", "text", "von", "operation", "zurueckgenommen",
                                            "rueckgaengig_von")})
    return liste


def _ablauf(u: Umgebung, von: str, operation: str, rechnen: Callable[[str, str], Rechnung],
            rueckgaengig_von: str | None = None) -> Ausgang:
    log = u.log or logging.getLogger("agentkit.strukturpflege")
    instanz = Path(u.instanz)
    pfad = Path(os.path.realpath(instanz / DATEI))  # nie den Symlink ersetzen
    lg_pfad = Path(os.path.realpath(instanz / LERNGRUPPEN))
    ablage = _ablage(u)
    with _sperre(instanz):
        text, lg_text = _lies(pfad), _lies(lg_pfad)
        fehler = struktur.pruefen(instanz)
        if fehler:
            _jan(u, ablage, "ungueltig", text, "lia/instanz/reihen.toml oder lerngruppen.toml ist ungültig, die "
                 "Web-App schreibt nicht, bis es behoben ist:\n" + "\n".join(fehler))
            raise PflegeFehler(LIA_JAN_WEISS)
        try:
            r = rechnen(text, lg_text)
        except be.EditorFehler as e:
            _jan(u, ablage, "editor", text, f"Die Web-App kann lia/instanz/reihen.toml nicht ändern: {e}. Bitte die "
                 "Stelle so schreiben wie die übrigen Einträge.")
            raise PflegeFehler(LIA_JAN_WEISS) from None
        if r.text == text and r.lerngruppen == lg_text:
            return Ausgang(False, r.beschreibung, hinweise=r.hinweise, neue_id=r.neue_id, gesichert=True)
        repo = _repo(pfad) if r.text != text else None
        if repo and _ungespeichert(repo, pfad) and _hash(text) != _letzter_hash(ablage):
            _jan(u, ablage, "hand", text, "lia/instanz/reihen.toml hat ungespeicherte Handänderungen. Die Web-App "
                 "schreibt nicht, bis sie committet sind (~/agenten/commit-daten.sh \"Nachricht\").")
            raise Handaenderung("Speichern geht gerade nicht, weil Jan die Datei bearbeitet. Jan ist informiert.")
        _schreiben(pfad, text, r.text, lg_pfad, lg_text, r.lerngruppen)
        if r.text != text:
            _json_schreiben(ablage / "stand.json", {"hash": _hash(r.text)})
        aktion = _aktion_ablegen(ablage, r, von, operation, rueckgaengig_von)
        log.info("Struktur: %s (%s), Aktion %s", r.beschreibung, von, aktion)
        aus = Ausgang(True, r.beschreibung, aktion, r.hinweise, r.neue_id, gesichert=True)
        if repo and u.commit and pfad == Path(os.path.realpath(repo / REPO_PFAD)):
            aus.commit = _committen(u, ablage, repo, f"lia/instanz: {r.beschreibung} ({von})", log)
            aus.gesichert = aus.commit is not None
            if not aus.gesichert:
                aus.hinweise.append("Gespeichert, aber noch nicht in Git gesichert; Jan ist informiert")
    return aus


@contextmanager
def _sperre(instanz: Path):
    """flock auf <instanz>/.reihen.sperre für Lesen-Ändern-Schreiben (App, später Skripte)."""
    with open(instanz / SPERRE, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _lies(pfad: Path) -> str:
    return pfad.read_text(encoding="utf-8") if pfad.exists() else ""


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _schreiben(pfad: Path, alt: str, neu: str, lg_pfad: Path, lg_alt: str, lg_neu: str) -> None:
    """Beide Dateien atomar. Reihenfolge so, dass dazwischen nie eine Lerngruppe ohne Klasse steht; scheitert die
    zweite, wird die erste zurückgeschrieben."""
    schritte = []
    if neu != alt:
        schritte.append((pfad, alt, neu, None))
    if lg_neu != lg_alt:
        schritte.append((lg_pfad, lg_alt, lg_neu, 0o600))
    if len(schritte) == 2 and set(tomllib.loads(lg_neu)) <= set(tomllib.loads(lg_alt)):
        schritte.reverse()  # Lerngruppe fällt weg: erst sie, dann die Klasse
    erledigt = []
    try:
        for ziel, vorher, nachher, rechte in schritte:
            _atomar(ziel, nachher, rechte)
            erledigt.append((ziel, vorher, rechte))
    except BaseException:
        for ziel, vorher, rechte in erledigt:
            _atomar(ziel, vorher, rechte)
        raise


def _atomar(pfad: Path, text: str, rechte: int | None = None) -> None:
    """Temporäre Datei im selben Ordner, fsync, os.replace. Bricht es dazwischen ab, bleibt die alte Datei und keine
    .tmp-Datei."""
    if rechte is None:
        rechte = pfad.stat().st_mode & 0o777 if pfad.exists() else 0o664
    tmp = pfad.with_name(f".{pfad.name}.{secrets.token_hex(4)}.tmp")
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, rechte)
        os.replace(tmp, pfad)
    finally:
        tmp.unlink(missing_ok=True)
    ordner = os.open(pfad.parent, os.O_RDONLY)
    try:
        os.fsync(ordner)
    finally:
        os.close(ordner)


def _umgebung_ohne_git() -> dict:
    """Ohne GIT_DIR, GIT_INDEX_FILE usw.: läuft das hier aus einem Git-Hook heraus, träfe git sonst das Repo des
    Hooks statt der Datei."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _git(repo: Path, *argumente: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *argumente], capture_output=True, text=True, timeout=60,
                          env=_umgebung_ohne_git())


def _repo(pfad: Path) -> Path | None:
    """Wurzel des Git-Repos, wenn die Datei dort verfolgt wird; sonst None (Testinstanz, kein Git)."""
    try:
        r = _git(pfad.parent, "rev-parse", "--show-toplevel")
        if r.returncode != 0:
            return None
        repo = Path(r.stdout.strip())
        return repo if _git(repo, "ls-files", "--error-unmatch", "--", str(pfad)).returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _ungespeichert(repo: Path, pfad: Path) -> bool:
    return _git(repo, "diff", "--quiet", "HEAD", "--", str(pfad)).returncode != 0


def _committen(u: Umgebung, ablage: Path, repo: Path, nachricht: str, log: logging.Logger) -> str | None:
    try:
        r = subprocess.run([str(repo / "commit-daten.sh"), nachricht], cwd=repo, capture_output=True, text=True,
                           timeout=u.commit_zeit, env=_umgebung_ohne_git())
        if r.returncode == 0:
            return _git(repo, "rev-parse", "HEAD").stdout.strip() or None
        grund = (r.stderr or r.stdout).strip()[-500:]
    except (OSError, subprocess.SubprocessError) as e:
        grund = str(e)
    log.error("commit-daten.sh fehlgeschlagen: %s", grund)
    _jan(u, ablage, "commit", nachricht, f"Die Web-App hat lia/instanz/reihen.toml geschrieben, aber commit-daten.sh "
         f"ist fehlgeschlagen ({grund}). Die nächste Änderung committet mit, oder von Hand: "
         "~/agenten/commit-daten.sh \"Nachricht\".")
    return None


def _jan(u: Umgebung, ablage: Path, grund: str, zu: str, text: str) -> None:
    """Meldung an Jan, je Grund und Dateistand nur einmal (Lia klickt sonst mehrmals)."""
    log = u.log or logging.getLogger("agentkit.strukturpflege")
    log.warning("%s", text.splitlines()[0])
    gemeldet = _json_lesen(ablage / "gemeldet.json")
    if gemeldet.get(grund) == _hash(zu):
        return
    try:
        if u.melden is not None:
            u.melden(text)
        else:
            from . import meldungen
            meldungen.melden(MELDE_AGENT, text)
    except Exception:  # die Meldung darf den eigentlichen Fehler nicht verdecken
        log.exception("Meldung an Jan fehlgeschlagen")
        return
    _json_schreiben(ablage / "gemeldet.json", {**gemeldet, grund: _hash(zu)})


def _ablage(u: Umgebung) -> Path:
    if u.ablage is not None:
        return Path(u.ablage)
    schluessel = hashlib.sha256(str(Path(u.instanz).resolve()).encode()).hexdigest()[:12]
    return Path(u.webapp_daten or WEBAPP_DATEN) / "aktionen" / schluessel


def _letzter_hash(ablage: Path) -> str | None:
    return _json_lesen(ablage / "stand.json").get("hash")


def _json_lesen(pfad: Path) -> dict:
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return daten if isinstance(daten, dict) else {}


def _json_schreiben(pfad: Path, daten: dict) -> None:
    """Aktionsablage: Ordner 0700, Dateien 0600 (alter Lerngruppen-Text fürs Rückgängig)."""
    pfad.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(pfad.parent, 0o700)
    _atomar(pfad, json.dumps(daten, ensure_ascii=False, indent=1), 0o600)


def _aktion_ablegen(ablage: Path, r: Rechnung, von: str, operation: str, rueckgaengig_von: str | None) -> str:
    aktion_id = f"{datetime.now():%Y%m%d-%H%M%S-%f}"
    while (ablage / f"{aktion_id}.json").exists():  # zwei Aktionen in derselben Mikrosekunde
        aktion_id = aktion_id[:-6] + f"{int(aktion_id[-6:]) + 1:06d}"
    _json_schreiben(ablage / f"{aktion_id}.json", {
        "id": aktion_id, "zeit": datetime.now().astimezone().isoformat(timespec="seconds"), "text": r.beschreibung,
        "von": von, "operation": operation, "rueckgaengig_von": rueckgaengig_von, "zurueckgenommen": None,
        "gegen": r.gegen})
    if rueckgaengig_von:
        alt = ablage / f"{rueckgaengig_von}.json"
        _json_schreiben(alt, {**_json_lesen(alt), "zurueckgenommen": aktion_id})
    for pfad in sorted(p for p in ablage.glob("*.json") if _AKTION_ID.fullmatch(p.stem))[:-AKTIONEN_BEHALTEN]:
        pfad.unlink(missing_ok=True)
    return aktion_id
