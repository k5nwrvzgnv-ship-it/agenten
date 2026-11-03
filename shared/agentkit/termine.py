"""Termine einer Klasse aus ihrem Stundenplan, Ferien und Feiertage je Bundesland, und die Rechenregeln zum
Verschieben von Stunden und Reihen (Strukturplan docs/struktur-pflege-plan.md, Abschnitt 2a, Bauschritt 1b).

Rein und ohne Netz. Gelesen wird höchstens die Ferien-Datei ferien.json neben dieser Datei (geholt einmal je
Schuljahr mit python3 -m agentkit.ferien_holen, von Hand pflegbar). Geschrieben wird nie: Jede Rechenregel gibt ein
Ergebnis mit den neuen Terminen zurück, schreiben tut agentkit.struktur (Bauschritt 4). Jans Grundsatz Flexibilität
(03.11.): Nichts ist gesperrt außer dem, was Daten kaputt macht (ein Termin trägt höchstens eine Stunde, ein
gestrichener keine). Lücken zwischen Reihen und Stunden ohne Termin sind erlaubt.

Begriffe
  Termin      Platz im Stundenplan der Klasse: Datum und Unterrichtsstunde, Kennung "2026-11-11/3". Eine
              Doppelstunde ist EIN Termin (F21), die Kennung nennt ihre erste Unterrichtsstunde.
  Stundenplan klasse.zeitplan, je wiederkehrendem Termin {tag "Mo".."Sa", stunde (Unterrichtsstunde 0..15),
              laenge 1 oder 2 (Standard 1), ab, bis (Datum "2026-08-24")}. Keine A/B-Wochen (F22).
  ausfall     gestrichene Termine der Klasse (Kennungen), zusatz einzelne Zusatztermine (Kennungen, auch in Ferien).
  Belegung    Stunde -> Termin (Kennung oder None) für alle Stunden der Klasse, auch ausgeblendete.

Termine: termine(zeitplan, kalender, ausfall, zusatz) -> [Termin] in Datumsfolge, ohne Ferien, Feiertage, Ausfall.
Kalender: kalender("BE") aus ferien.json; schuljahr("2026/27") -> (beginn, ende) (nach den Sommerferien bis vor die
nächsten), schuljahr_von(datum), halbjahr_stichtag(name) (Beginn der Winter-/Halbjahresferien, F24; None, wenn das
Land keine hat: dann fragt die App), halbjahre(name, stichtag=None).

Rechenregeln (2a.3) an einem Plan (Stand einer Klasse, wird nie verändert), je -> Ergebnis:
  alles_rueckt_nach(termin)       Termin gestrichen, jede spätere Stunde der Klasse einen Termin weiter (F23)
  stunde_faellt_weg(termin)       Termin gestrichen, seine Stunde ausgeblendet, sonst bleibt alles
  ausfall_aufheben(termin)        Termin wieder frei, nichts rückt
  stunde_verschieben(folge, id, stelle)   Inhalt wandert, Termine bleiben an ihren Plätzen
  stunde_auf_termin(id, termin, bei_belegt)   frei: nur diese Stunde; belegt: "nachruecken" oder "tauschen"
  reihe_verschieben(reihe, start, bei_belegt) Reihe ab start; belegt: "nachruecken" oder "tauschen"
  stundenplan_ab(stichtag, neuer_zeitplan)    Halbjahr: Stunden ab Stichtag der Reihe nach auf die neuen Termine
  zuteilen(ids, ab=None, auswahl=None)        Stunden ohne Termin bekommen freie Termine der Reihe nach
Trifft ein Ziel belegte Termine und fehlt bei_belegt, kommt Belegt (die App fragt einmal und ruft erneut auf).
Ergebnis.rueckgaengig() ist die Gegen-Aktion, Ergebnis.anwenden() der neue Plan.
"""

import json
import re
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from functools import cached_property
from itertools import zip_longest
from pathlib import Path

FERIEN_DATEI = Path(__file__).with_name("ferien.json")
BUNDESLAENDER = {
    "BB": "Brandenburg", "BE": "Berlin", "BW": "Baden-Württemberg", "BY": "Bayern", "HB": "Bremen",
    "HE": "Hessen", "HH": "Hamburg", "MV": "Mecklenburg-Vorpommern", "NI": "Niedersachsen",
    "NW": "Nordrhein-Westfalen", "RP": "Rheinland-Pfalz", "SH": "Schleswig-Holstein", "SL": "Saarland",
    "SN": "Sachsen", "ST": "Sachsen-Anhalt", "TH": "Thüringen",
}
TAGE = ("Mo", "Di", "Mi", "Do", "Fr", "Sa")
_WOCHENTAGE = TAGE + ("So",)
STUNDE_MAX = 15
ZEITPLAN_FELDER = ("tag", "stunde", "laenge", "ab", "bis")
SOMMERFERIEN = "Sommerferien"
# Ferien, mit deren Beginn das 1. Halbjahr endet (F24). Bayern (Frühjahrsferien), Saarland (Fastnachtsferien) und
# Länder ohne solche Ferien (BW, HE, NW, RP, SH) haben keinen ableitbaren Stichtag: die App fragt Lia.
HALBJAHRESFERIEN = ("Winterferien", "Halbjahresferien", "Halbjahrespause")
# Einträge mit "schulart" gelten nur für diese Schulart (heute nur MV); Lia unterrichtet an einer allgemeinbildenden.
STANDARD_SCHULART = "Allgemeinbildende Schulen"
NACHRUECKEN, TAUSCHEN = "nachruecken", "tauschen"
_KENNUNG = re.compile(r"(\d{4}-\d{2}-\d{2})/(\d{1,2})")
_DATUM = re.compile(r"\d{4}-\d{2}-\d{2}")
_SCHULJAHR = re.compile(r"(\d{4})/(\d{2})")


class TermineFehler(Exception):
    """Eingabe oder Ferien-Datei passt nicht. Der Text ist für Lia bzw. Jan."""


class Belegt(TermineFehler):
    """Das Ziel ist belegt. Die App fragt einmal „Dahinter alles nachrücken“ oder „Tauschen“ und ruft mit bei_belegt
    erneut auf. stunden: ids der getroffenen Stunden, reihen: ids ihrer Reihen (ohne None)."""

    def __init__(self, text: str, stunden: list[str], reihen: list[str]):
        super().__init__(text)
        self.stunden = stunden
        self.reihen = reihen


# --- Daten und Kennungen ------------------------------------------------------------------------------------------

def datum_lesen(wert) -> date:
    """Datum aus "2026-11-03" (oder einem TOML-Datum)."""
    if isinstance(wert, date) and not isinstance(wert, datetime):
        return wert
    if isinstance(wert, str) and _DATUM.fullmatch(wert):
        try:
            return date.fromisoformat(wert)
        except ValueError:
            pass
    raise TermineFehler(f"{wert!r} ist kein Datum wie \"2026-11-03\"")


def kennung(datum: date, stunde: int) -> str:
    return f"{datum.isoformat()}/{stunde}"


def kennung_lesen(text) -> tuple[date, int]:
    """(Datum, Unterrichtsstunde) aus "2026-11-11/3"."""
    m = _KENNUNG.fullmatch(text) if isinstance(text, str) else None
    if m and 0 <= int(m[2]) <= STUNDE_MAX:
        try:
            return date.fromisoformat(m[1]), int(m[2])
        except ValueError:
            pass
    raise TermineFehler(f"Termin {text!r} wie \"2026-11-11/3\" schreiben (Datum/Unterrichtsstunde)")


def anzeige(kennung_: str, laenge: int = 1) -> str:
    """„Di 11.11., 3. Std.“ bzw. „Di 11.11., 3./4. Std.“ für die Anzeige und den Kontext der Agenten."""
    d, st = kennung_lesen(kennung_)
    std = f"{st}." if laenge == 1 else f"{st}./{st + 1}."
    return f"{_WOCHENTAGE[d.weekday()]} {d.day:02d}.{d.month:02d}., {std} Std."


@dataclass(frozen=True, order=True)
class Termin:
    datum: date
    stunde: int
    laenge: int = field(default=1, compare=False)
    zusatz: bool = field(default=False, compare=False)
    ausgefallen: bool = field(default=False, compare=False)

    @property
    def kennung(self) -> str:
        return kennung(self.datum, self.stunde)

    @property
    def text(self) -> str:
        return anzeige(self.kennung, self.laenge)


# --- Ferien und Feiertage -----------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Kalender:
    """Ferien und Feiertage eines Bundeslands, nur die, die für alle Schulen des Lands gelten."""
    bundesland: str
    ferien: tuple = ()      # (von, bis, name), nach von sortiert
    feiertage: tuple = ()   # (datum, name)
    abgedeckt: tuple = ()   # (von, bis): Zeiträume, für die die Datei vollständig ist

    def frei(self, tag: date) -> str | None:
        """Name des Feiertags oder der Ferien an diesem Tag, sonst None."""
        for d, name in self.feiertage:
            if d == tag:
                return name
        for von, bis, name in self.ferien:
            if von <= tag <= bis:
                return name
        return None

    def abgedeckt_pruefen(self, von: date, bis: date) -> None:
        """TermineFehler, wenn ferien.json den Zeitraum nicht ganz abdeckt (dann fehlen vielleicht Ferien)."""
        tag = von
        for a, b in sorted(self.abgedeckt):
            if a <= tag <= b:
                tag = b + timedelta(days=1)
            if tag > bis:
                return
        raise TermineFehler(f"Ferien für {BUNDESLAENDER[self.bundesland]} ab {tag.isoformat()} fehlen in "
                            f"{FERIEN_DATEI.name}. Holen mit: python3 -m agentkit.ferien_holen")

    def _ferien_namens(self, namen: tuple, von: date, bis: date) -> list[tuple]:
        return [f for f in self.ferien if f[2] in namen and von <= f[0] <= bis]

    def schuljahr(self, name: str) -> tuple[date, date]:
        """(erster Tag nach den Sommerferien, letzter Tag vor den nächsten) für "2026/27"."""
        m = _SCHULJAHR.fullmatch(name) if isinstance(name, str) else None
        if not m or (int(m[1]) + 1) % 100 != int(m[2]):
            raise TermineFehler(f"Schuljahr {name!r} wie \"2026/27\" schreiben")
        jahr = int(m[1])
        vorher = self._ferien_namens((SOMMERFERIEN,), date(jahr, 1, 1), date(jahr, 12, 31))
        danach = self._ferien_namens((SOMMERFERIEN,), date(jahr + 1, 1, 1), date(jahr + 1, 12, 31))
        if not vorher or not danach:
            raise TermineFehler(f"Sommerferien {jahr if not vorher else jahr + 1} für "
                                f"{BUNDESLAENDER[self.bundesland]} fehlen in {FERIEN_DATEI.name}. "
                                "Holen mit: python3 -m agentkit.ferien_holen")
        return vorher[0][1] + timedelta(days=1), danach[0][0] - timedelta(days=1)

    def schuljahr_von(self, tag: date) -> str:
        """Schuljahr, zu dem der Tag gehört; die Sommerferien zählen schon zum nächsten (Vorbelegung der Maske)."""
        sommer = self._ferien_namens((SOMMERFERIEN,), date(tag.year, 1, 1), date(tag.year, 12, 31))
        if not sommer:
            raise TermineFehler(f"Sommerferien {tag.year} für {BUNDESLAENDER[self.bundesland]} fehlen in "
                                f"{FERIEN_DATEI.name}. Holen mit: python3 -m agentkit.ferien_holen")
        jahr = tag.year if tag >= sommer[0][0] else tag.year - 1
        return f"{jahr}/{(jahr + 1) % 100:02d}"

    def halbjahr_stichtag(self, name: str) -> date | None:
        """Beginn der Winter- bzw. Halbjahresferien im Schuljahr (F24), None, wenn das Land keine hat."""
        beginn, ende = self.schuljahr(name)
        treffer = self._ferien_namens(HALBJAHRESFERIEN, beginn, ende)
        return treffer[0][0] if treffer else None

    def halbjahre(self, name: str, stichtag: date | None = None) -> list[tuple[date, date]]:
        """[(Beginn, Tag vor dem Stichtag), (Stichtag, Ende)]. Der Stichtag ist änderbar (F24)."""
        beginn, ende = self.schuljahr(name)
        stichtag = stichtag or self.halbjahr_stichtag(name)
        if stichtag is None:
            raise TermineFehler(f"{BUNDESLAENDER[self.bundesland]} hat keine Winterferien: Stichtag fürs "
                                "2. Halbjahr bitte angeben")
        if not beginn < stichtag <= ende:
            raise TermineFehler(f"Stichtag {stichtag.isoformat()} liegt nicht im Schuljahr {name}")
        return [(beginn, stichtag - timedelta(days=1)), (stichtag, ende)]


def ferien_pruefen(daten) -> list[str]:
    """Fehlertexte zum Inhalt von ferien.json, leer = in Ordnung."""
    wo = FERIEN_DATEI.name
    if not isinstance(daten, dict) or not isinstance(daten.get("laender"), dict):
        return [f"{wo}: erwartet ein Objekt mit \"laender\""]
    fehler = []
    for land, eintrag in daten["laender"].items():
        lwo = f"{wo}, {land}"
        if land not in BUNDESLAENDER:
            fehler.append(f"{lwo}: unbekanntes Bundesland, erlaubt {sorted(BUNDESLAENDER)}")
            continue
        if not isinstance(eintrag, dict) or set(eintrag) - {"abgedeckt", "ferien", "feiertage"}:
            fehler.append(f"{lwo}: erwartet \"abgedeckt\", \"ferien\", \"feiertage\"")
            continue
        for art, felder, daten_felder in (("abgedeckt", ("von", "bis", "quelle", "abgerufen"), ("von", "bis")),
                                          ("ferien", ("name", "von", "bis", "nur", "schulart"), ("von", "bis")),
                                          ("feiertage", ("name", "datum", "nur", "schulart"), ("datum",))):
            liste = eintrag.get(art, [])
            if not isinstance(liste, list):
                fehler.append(f"{lwo}: {art} muss eine Liste sein")
                continue
            for nr, e in enumerate(liste, 1):
                ewo = f"{lwo}, {art} {nr}"
                if not isinstance(e, dict) or set(e) - set(felder) or not all(isinstance(v, str) for v in e.values()):
                    fehler.append(f"{ewo}: erlaubt sind Texte in {list(felder)}")
                    continue
                try:
                    werte = [datum_lesen(e.get(k)) for k in daten_felder]
                except TermineFehler as f:
                    fehler.append(f"{ewo}: {f}")
                    continue
                if len(werte) == 2 and werte[0] > werte[1]:
                    fehler.append(f"{ewo}: von liegt nach bis")
    return fehler


def kalender_aus_daten(daten: dict, bundesland: str, schulart: str = STANDARD_SCHULART) -> Kalender:
    """Kalender aus dem Inhalt von ferien.json. Einträge mit "nur" (z. B. Inseln, eine Stadt) gelten nicht für das
    ganze Land und zählen nicht; Einträge mit "schulart" nur für diese Schulart."""
    if bundesland not in BUNDESLAENDER:
        raise TermineFehler(f"Bundesland {bundesland!r} gibt es nicht, erlaubt {sorted(BUNDESLAENDER)}")
    fehler = ferien_pruefen(daten)
    if fehler:
        raise TermineFehler("\n".join(fehler))
    land = daten["laender"].get(bundesland)
    if land is None:
        raise TermineFehler(f"Für {BUNDESLAENDER[bundesland]} stehen keine Ferien in {FERIEN_DATEI.name}. "
                            "Holen mit: python3 -m agentkit.ferien_holen")

    def gilt(e):
        return not e.get("nur") and e.get("schulart", schulart) == schulart

    return Kalender(
        bundesland,
        tuple(sorted((datum_lesen(e["von"]), datum_lesen(e["bis"]), e["name"]) for e in land.get("ferien", [])
                     if gilt(e))),
        tuple(sorted((datum_lesen(e["datum"]), e["name"]) for e in land.get("feiertage", []) if gilt(e))),
        tuple(sorted((datum_lesen(e["von"]), datum_lesen(e["bis"])) for e in land.get("abgedeckt", []))))


def kalender(bundesland: str, datei: Path | None = None, schulart: str = STANDARD_SCHULART) -> Kalender:
    """Kalender des Bundeslands aus ferien.json (nur lesen)."""
    pfad = Path(datei or FERIEN_DATEI)
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise TermineFehler(f"{pfad} fehlt. Holen mit: python3 -m agentkit.ferien_holen") from None
    except ValueError as e:
        raise TermineFehler(f"{pfad.name} ist kein gültiges JSON: {e}") from None
    return kalender_aus_daten(daten, bundesland, schulart)


# --- Termine aus dem Stundenplan ----------------------------------------------------------------------------------

def _ganzzahl(wert) -> bool:
    return isinstance(wert, int) and not isinstance(wert, bool)


def zeitplan_pruefen(eintraege, wo: str = "Stundenplan") -> list[str]:
    """Fehlertexte zum Stundenplan einer Klasse, leer = in Ordnung. Zwei Einträge dürfen sich nicht überschneiden
    (gleicher Tag, gleiche Unterrichtsstunde, Zeiträume überlappen)."""
    if not isinstance(eintraege, list) or not all(isinstance(e, dict) for e in eintraege):
        return [f"{wo}: als [[klasse.zeitplan]] schreiben"]
    fehler, gueltig = [], []
    for nr, e in enumerate(eintraege, 1):
        ewo = f"{wo}, Eintrag {nr}"
        unbekannt = sorted(set(e) - set(ZEITPLAN_FELDER))
        if unbekannt:
            fehler.append(f"{ewo}: unbekannte Felder {unbekannt}")
            continue
        ok = True
        if e.get("tag") not in TAGE:
            fehler.append(f"{ewo}: tag {e.get('tag')!r}, erlaubt {list(TAGE)}")
            ok = False
        if not (_ganzzahl(e.get("stunde")) and 0 <= e["stunde"] <= STUNDE_MAX):
            fehler.append(f"{ewo}: stunde als Zahl von 0 bis {STUNDE_MAX} schreiben (Unterrichtsstunde)")
            ok = False
        laenge = e.get("laenge", 1)
        if not (_ganzzahl(laenge) and laenge in (1, 2)):
            fehler.append(f"{ewo}: laenge 1 (Einzelstunde) oder 2 (Doppelstunde)")
            ok = False
        try:
            ab, bis = datum_lesen(e.get("ab")), datum_lesen(e.get("bis"))
        except TermineFehler:
            fehler.append(f"{ewo}: ab und bis als Datum schreiben, z. B. \"2026-08-24\"")
            continue
        if ab > bis:
            fehler.append(f"{ewo}: ab liegt nach bis")
            ok = False
        if ok:
            gueltig.append((nr, e["tag"], e["stunde"], e["stunde"] + laenge - 1, ab, bis))
    for i, a in enumerate(gueltig):
        for b in gueltig[i + 1:]:
            if a[1] == b[1] and a[2] <= b[3] and b[2] <= a[3] and a[4] <= b[5] and b[4] <= a[5]:
                fehler.append(f"{wo}: Eintrag {a[0]} und {b[0]} überschneiden sich ({a[1]}, {b[2]}. Stunde)")
    return fehler


def zeitplan_normal(eintraege: list) -> list[dict]:
    """Stundenplan mit laenge und Daten als Text, so wie die Datei ihn schreibt."""
    return [{"tag": e["tag"], "stunde": e["stunde"], "laenge": e.get("laenge", 1),
             "ab": datum_lesen(e["ab"]).isoformat(), "bis": datum_lesen(e["bis"]).isoformat()} for e in eintraege]


def termine(zeitplan, kalender_: Kalender | None, ausfall=(), zusatz=(), mit_ausfall: bool = False) -> list[Termin]:
    """Alle Termine des Stundenplans ohne Ferien und Feiertage, dazu die Zusatztermine, in Datumsfolge. Gestrichene
    (ausfall) fehlen, mit mit_ausfall=True stehen sie mit ausgefallen=True darin."""
    fehler = zeitplan_pruefen(list(zeitplan))
    if fehler:
        raise TermineFehler("\n".join(fehler))
    if zeitplan and kalender_ is None:
        raise TermineFehler("Für den Stundenplan fehlt das Bundesland ([schule] bundesland)")
    gestrichen = {kennung_lesen(k) for k in ausfall}
    plaetze: dict[tuple, Termin] = {}
    for e in zeitplan:
        ab, bis = datum_lesen(e["ab"]), datum_lesen(e["bis"])
        kalender_.abgedeckt_pruefen(ab, bis)
        tag = ab + timedelta(days=(TAGE.index(e["tag"]) - ab.weekday()) % 7)
        while tag <= bis:
            if kalender_.frei(tag) is None:
                plaetze[(tag, e["stunde"])] = Termin(tag, e["stunde"], e.get("laenge", 1))
            tag += timedelta(days=7)
    for k in zusatz:
        d, st = kennung_lesen(k)
        plaetze.setdefault((d, st), Termin(d, st, zusatz=True))
    liste = []
    for schluessel in sorted(plaetze):
        if schluessel not in gestrichen:
            liste.append(plaetze[schluessel])
        elif mit_ausfall:
            liste.append(replace(plaetze[schluessel], ausgefallen=True))
    return liste


def belegung_pruefen(belegung: dict, ausfall=()) -> list[str]:
    """Testregel 31: Ein Termin trägt höchstens eine Stunde, ein gestrichener keine."""
    fehler, gesehen, gestrichen = [], {}, set(ausfall)
    for sid, k in belegung.items():
        if not k:
            continue
        if k in gestrichen:
            fehler.append(f"Stunde {sid}: Termin {k} ist gestrichen (ausfall) und trägt keine Stunde")
        if k in gesehen:
            fehler.append(f"Termin {k} trägt zwei Stunden ({gesehen[k]} und {sid}), erlaubt ist eine")
        else:
            gesehen[k] = sid
    return fehler


def nach_datum(stunden: list[str], belegung: dict) -> list[str]:
    """Reihenfolge einer Reihe nach einer Regel: Stunden mit Termin auf ihren Plätzen nach Datum geordnet, Stunden
    ohne Termin bleiben an ihrer Stelle (Reihenfolge der Blöcke = Reihenfolge der Daten, Abschnitt 2a.2)."""
    mit = sorted((s for s in stunden if belegung.get(s)), key=lambda s: kennung_lesen(belegung[s]))
    rest = iter(mit)
    return [next(rest) if belegung.get(s) else s for s in stunden]


# --- Rechenregeln -------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Plan:
    """Stand einer Klasse für die Rechenregeln. Wird nie verändert; jede Regel gibt ein Ergebnis zurück.
    belegung: alle Stunden der Klasse -> Kennung oder None. reihen: Reihe -> Stunden-ids in Reihenfolge (auch
    ausgeblendete, die stehen zusätzlich in ausgeblendet)."""
    zeitplan: tuple = ()
    belegung: dict = field(default_factory=dict)
    reihen: dict = field(default_factory=dict)
    ausfall: tuple = ()
    zusatz: tuple = ()
    ausgeblendet: frozenset = frozenset()
    kalender: Kalender | None = None

    @cached_property
    def termine(self) -> list[Termin]:
        """Verfügbare Termine (ohne Ausfall) in Datumsfolge."""
        return termine(self.zeitplan, self.kalender, self.ausfall, self.zusatz)

    @cached_property
    def _pos(self) -> dict[str, int]:
        return {t.kennung: i for i, t in enumerate(self.termine)}

    def stunde_auf(self, kennung_: str) -> str | None:
        """id der Stunde auf dem Termin, sonst None."""
        for sid, k in self.belegung.items():
            if k == kennung_:
                return sid
        return None

    def reihe_von(self, stunde_id: str) -> str | None:
        for rid, ids in self.reihen.items():
            if stunde_id in ids:
                return rid
        return None

    def freie(self, ab: date | None = None, anzahl: int | None = None) -> list[Termin]:
        """Freie Termine (ohne Stunde) ab einem Datum, für „Termine zuteilen“ („ab Di 11.11., 8 Termine“)."""
        belegt = set(self.belegung.values())
        frei = [t for t in self.termine if t.kennung not in belegt and (ab is None or t.datum >= ab)]
        return frei[:anzahl] if anzahl is not None else frei

    def hinweise(self) -> list[str]:
        """Was Lia oder Jan wissen sollten, ohne dass es kaputt ist: Stunden auf einem Datum, das kein Termin des
        Stundenplans ist (z. B. nach einer Änderung von Hand). TermineFehler, wenn Ferien fehlen."""
        gestrichen = set(self.ausfall)
        return [f"Stunde {sid} liegt auf {k}, das ist kein Termin der Klasse (Stundenplan, Ferien, Feiertage)"
                for sid, k in self.belegung.items() if k and k not in self._pos and k not in gestrichen]

    def _index(self, kennung_: str) -> int:
        if kennung_ in self._pos:
            return self._pos[kennung_]
        kennung_lesen(kennung_)
        if kennung_ in self.ausfall:
            raise TermineFehler(f"Der Termin {anzeige(kennung_)} ist schon gestrichen")
        raise TermineFehler(f"{anzeige(kennung_)} ist kein Termin dieser Klasse (Stundenplan, Ferien, Feiertage)")

    def _sichtbar(self, reihe_id: str) -> list[str]:
        if reihe_id not in self.reihen:
            raise TermineFehler(f"Reihe {reihe_id!r} gehört nicht zu dieser Klasse")
        return [s for s in self.reihen[reihe_id] if s not in self.ausgeblendet]

    def _belegt(self, getroffen: list[str], was: str) -> Belegt:
        reihen = list(dict.fromkeys(r for r in map(self.reihe_von, getroffen) if r))
        return Belegt(f"{was} ist belegt: dahinter alles nachrücken oder tauschen?", getroffen, reihen)

    def _schieben(self, neu: dict, block: set[int], bewegte: set[str], start: int) -> None:
        """Nachrücken: Stunden ab start, die nicht bewegt werden, rücken der Reihe nach so weit, dass sie nicht auf
        dem Block liegen; keine rückt nach vorn, keine weiter als nötig, die Reihenfolge bleibt."""
        andere = sorted((self._pos[k], sid) for sid, k in self.belegung.items()
                        if sid not in bewegte and k in self._pos and self._pos[k] >= start)
        letzte = -1
        for p, sid in andere:
            q = max(p, letzte + 1)
            while q in block:
                q += 1
            neu[sid] = self.termine[q].kennung if q < len(self.termine) else None
            letzte = q

    def _ergebnis(self, neu: dict, ausfall=None, zeitplan=None, ausblenden=(), hinweise=(),
                  reihenfolge=None, folge_vorher=None) -> "Ergebnis":
        ausfall = tuple(sorted(self.ausfall if ausfall is None else ausfall, key=kennung_lesen))
        fehler = belegung_pruefen(neu, ausfall)
        if fehler:  # darf nicht vorkommen; lieber nichts als kaputte Daten
            raise TermineFehler("Die Rechnung ergäbe kaputte Termine: " + "; ".join(fehler))
        weg = [s for s, k in neu.items() if self.belegung.get(s) and not k and s not in ausblenden]
        hinweise = list(hinweise)
        if weg:
            hinweise.append(f"{len(weg)} {'Stunde hat' if len(weg) == 1 else 'Stunden haben'} keinen Termin mehr im "
                            "Stundenplan und stehen ohne Datum in der Reihe")
        return Ergebnis(termine=neu, ausfall=list(ausfall),
                        zeitplan=list(self.zeitplan if zeitplan is None else zeitplan),
                        ausblenden=list(ausblenden), hinweise=hinweise, ohne_termin=weg,
                        reihenfolge=reihenfolge, folge_vorher=folge_vorher, vorher=self)

    # Regeln

    def alles_rueckt_nach(self, kennung_: str) -> "Ergebnis":
        """Termin fällt aus, „Alles rückt nach“: jede spätere Stunde der Klasse (über Reihengrenzen, F23) wandert um
        genau einen Termin; die letzte nimmt den nächsten Termin oder steht ohne da. Trägt der Termin keine Stunde,
        wird er nur gestrichen."""
        i = self._index(kennung_)
        neu = dict(self.belegung)
        if self.stunde_auf(kennung_) is not None:
            for sid, k in self.belegung.items():
                p = self._pos.get(k)
                if p is not None and p >= i:
                    neu[sid] = self.termine[p + 1].kennung if p + 1 < len(self.termine) else None
        return self._ergebnis(neu, ausfall=self.ausfall + (kennung_,))

    def stunde_faellt_weg(self, kennung_: str) -> "Ergebnis":
        """Termin fällt aus, „Diese Stunde fällt weg“: die Stunde wird ausgeblendet (ohne Termin), sonst bleibt alles."""
        self._index(kennung_)
        neu = dict(self.belegung)
        sid = self.stunde_auf(kennung_)
        if sid is not None:
            neu[sid] = None
        return self._ergebnis(neu, ausfall=self.ausfall + (kennung_,), ausblenden=[sid] if sid else [])

    def ausfall_aufheben(self, kennung_: str) -> "Ergebnis":
        """Gestrichener Termin wird wieder frei; nichts rückt (Stunden legt Lia selbst darauf)."""
        if kennung_ not in self.ausfall:
            raise TermineFehler(f"Der Termin {anzeige(kennung_)} ist nicht gestrichen")
        return self._ergebnis(dict(self.belegung), ausfall=[k for k in self.ausfall if k != kennung_])

    def stunde_verschieben(self, folge: list[str], stunde_id: str, stelle: int) -> "Ergebnis":
        """Stunde in der Folge (Stunden einer Reihe oder der Klasse in Reihenfolge) an die Stelle (0 = vorn, gezählt
        in der neuen Folge). Der Inhalt wandert, die Termine bleiben an ihren Plätzen: die Stunden dazwischen rücken
        je einen Termin weiter (2a.3). Ergebnis.reihenfolge ist die neue Folge."""
        folge = list(folge)
        if len(set(folge)) != len(folge) or stunde_id not in folge:
            raise TermineFehler(f"Stunde {stunde_id!r} steht nicht (genau einmal) in der Folge")
        if not 0 <= stelle < len(folge):
            raise TermineFehler(f"Stelle {stelle} gibt es nicht, erlaubt 0 bis {len(folge) - 1}")
        neue = [s for s in folge if s != stunde_id]
        neue.insert(stelle, stunde_id)
        neu = dict(self.belegung)
        for s, k in zip(neue, [self.belegung.get(s) for s in folge], strict=True):
            neu[s] = k
        return self._ergebnis(neu, reihenfolge=neue, folge_vorher=folge)

    def stunde_auf_termin(self, stunde_id: str, kennung_: str, bei_belegt: str | None = None) -> "Ergebnis":
        """Stunde direkt auf einen Termin, auch in eine Lücke oder eine andere Reihe. Frei: nur diese Stunde ändert
        ihr Datum. Belegt: bei_belegt "nachruecken" (die Stunde dort und nötige weitere rücken nach) oder
        "tauschen" (beide tauschen ihre Termine), sonst Belegt."""
        p = self._index(kennung_)
        besetzer = self.stunde_auf(kennung_)
        neu = dict(self.belegung)
        neu[stunde_id] = kennung_
        if besetzer in (None, stunde_id):
            pass
        elif bei_belegt is None:
            raise self._belegt([besetzer], f"Der Termin {anzeige(kennung_)}")
        elif bei_belegt == TAUSCHEN:
            neu[besetzer] = self.belegung.get(stunde_id)
        elif bei_belegt == NACHRUECKEN:
            self._schieben(neu, {p}, {stunde_id}, p)
        else:
            raise TermineFehler(f"bei_belegt {bei_belegt!r}, erlaubt {NACHRUECKEN!r} oder {TAUSCHEN!r}")
        return self._ergebnis(neu)

    def reihe_verschieben(self, reihe_id: str, start: str, bei_belegt: str | None = None) -> "Ergebnis":
        """Ganze Reihe beginnt am Termin start; ihre sichtbaren Stunden liegen der Reihe nach auf den Terminen ab dort
        (zu wenige: die letzten ohne Termin). Belegte Termine anderer Reihen:
          "nachruecken": die getroffenen Stunden rücken hinter die Reihe, nur so weit wie nötig, Lücken danach bleiben;
          "tauschen":    die Reihe und die Reihe auf dem ersten getroffenen Termin tauschen ihre Plätze; zusammen
                         belegen sie genau dieselben Termine wie vorher, alle anderen Stunden bleiben."""
        eigene = self._sichtbar(reihe_id)
        if not eigene:
            raise TermineFehler("Die Reihe hat keine Stunden")
        p = self._index(start)
        block = list(range(p, min(p + len(eigene), len(self.termine))))
        eigen = set(eigene)
        getroffen = [s for s in (self.stunde_auf(self.termine[q].kennung) for q in block) if s and s not in eigen]
        neu = dict(self.belegung)
        if getroffen and bei_belegt is None:
            raise self._belegt(getroffen, f"Ab {anzeige(start)}")
        if not getroffen or bei_belegt == NACHRUECKEN:
            for s, q in zip_longest(eigene, block):
                neu[s] = self.termine[q].kennung if q is not None else None
            if getroffen:
                self._schieben(neu, set(block), eigen, p)
            return self._ergebnis(neu)
        if bei_belegt != TAUSCHEN:
            raise TermineFehler(f"bei_belegt {bei_belegt!r}, erlaubt {NACHRUECKEN!r} oder {TAUSCHEN!r}")
        mit_r = [s for s in eigene if self.belegung.get(s) in self._pos]
        if not mit_r:
            raise TermineFehler("Tauschen geht nur, wenn die Reihe schon Termine hat; hier passt „Dahinter alles "
                                "nachrücken“")
        andere = self.reihe_von(getroffen[0])
        mit_b = [s for s in self._sichtbar(andere) if self.belegung.get(s) in self._pos] if andere else getroffen[:1]
        plaetze = sorted(self._pos[self.belegung[s]] for s in mit_r + mit_b)
        r_zuerst = min(self._pos[self.belegung[s]] for s in mit_r) > min(self._pos[self.belegung[s]] for s in mit_b)
        for s, q in zip(mit_r + mit_b if r_zuerst else mit_b + mit_r, plaetze, strict=True):
            neu[s] = self.termine[q].kennung
        return self._ergebnis(neu)

    def stundenplan_ab(self, stichtag, neuer_zeitplan: list[dict]) -> "Ergebnis":
        """Stundenplan ab Stichtag (Halbjahr, F24): der alte endet am Tag davor, der neue gilt ab Stichtag (ab fehlt =
        Stichtag). Die Stunden auf Terminen ab dem Stichtag liegen dann der Reihe nach auf den neuen Terminen, Plätze
        ohne Stunde bleiben frei; Zusatztermine und Stunden davor bleiben. Ergebnis.zeitplan ist der neue Plan."""
        stichtag = datum_lesen(stichtag)
        zeitplan = []
        for e in zeitplan_normal(list(self.zeitplan)):
            if datum_lesen(e["ab"]) < stichtag:
                zeitplan.append({**e, "bis": min(datum_lesen(e["bis"]), stichtag - timedelta(days=1)).isoformat()})
        neue = [{"ab": stichtag.isoformat(), **e} for e in neuer_zeitplan]
        fehler = zeitplan_pruefen(neue, "Neuer Stundenplan")
        if fehler:
            raise TermineFehler("\n".join(fehler))
        if any(datum_lesen(e["ab"]) < stichtag for e in neue):
            raise TermineFehler("Der neue Stundenplan beginnt frühestens am Stichtag")
        zeitplan += zeitplan_normal(neue)
        danach = replace(self, zeitplan=tuple(zeitplan))
        alt = [t.kennung for t in self.termine if t.datum >= stichtag and not t.zusatz]
        jetzt = [t.kennung for t in danach.termine if t.datum >= stichtag and not t.zusatz]
        umzug = {k: jetzt[i] if i < len(jetzt) else None for i, k in enumerate(alt)}
        neu = {sid: umzug.get(k, k) if k else k for sid, k in self.belegung.items()}
        hinweise = []
        if len(alt) != len(jetzt):
            hinweise.append(f"Ab {stichtag.strftime('%d.%m.%Y')} hat der neue Stundenplan {len(jetzt)} Termine, der "
                            f"alte hatte {len(alt)}")
        try:
            return self._ergebnis(neu, zeitplan=zeitplan, hinweise=hinweise)
        except TermineFehler:
            raise TermineFehler("Mit dem neuen Stundenplan lägen zwei Stunden auf einem Termin (Zusatztermin?). "
                                "Bitte die Stunde auf dem Zusatztermin vorher verschieben") from None

    def zuteilen(self, stunden: list[str], ab: date | None = None, auswahl: list[str] | None = None) -> "Ergebnis":
        """Stunden ohne Termin (in dieser Reihenfolge) bekommen freie Termine: die gewählten (auswahl, Häkchen in der
        Terminliste) oder die nächsten freien ab einem Datum. Stunden mit Termin bleiben."""
        ohne = [s for s in stunden if not self.belegung.get(s)]
        if auswahl is not None:
            for k in auswahl:
                self._index(k)
            getroffen = [s for s in map(self.stunde_auf, auswahl) if s]
            if getroffen:
                raise self._belegt(getroffen, "Ein gewählter Termin")
            plaetze = sorted(auswahl, key=kennung_lesen)
        else:
            plaetze = [t.kennung for t in self.freie(ab=ab)]
        neu = dict(self.belegung)
        for s, k in zip(ohne, plaetze, strict=False):  # zu wenige Plätze: der Rest bleibt ohne
            neu[s] = k
        rest = len(ohne) - len(plaetze)
        hinweise = [f"{rest} {'Stunde bekommt' if rest == 1 else 'Stunden bekommen'} keinen Termin, es gibt nicht "
                    "genug freie"] if rest > 0 else []
        return self._ergebnis(neu, hinweise=hinweise)


@dataclass
class Ergebnis:
    """Neue Termine nach einer Regel. Nichts ist geschrieben. termine: alle Stunden der Klasse -> Kennung oder None;
    ausfall, zeitplan: neue Werte der Klasse; ausblenden/einblenden: Stunden-ids; ohne_termin: Stunden, die ihren
    Termin verloren haben (die App nennt sie Lia); reihenfolge: neue Folge (nur stunde_verschieben)."""
    termine: dict
    ausfall: list
    zeitplan: list
    ausblenden: list = field(default_factory=list)
    einblenden: list = field(default_factory=list)
    hinweise: list = field(default_factory=list)
    ohne_termin: list = field(default_factory=list)
    reihenfolge: list | None = None
    folge_vorher: list | None = None
    vorher: Plan | None = None

    @property
    def geaendert(self) -> dict:
        """Nur die Stunden, deren Termin sich ändert: id -> neue Kennung oder None."""
        return {s: k for s, k in self.termine.items() if (self.vorher.belegung.get(s) if self.vorher else None) != k}

    def anwenden(self) -> Plan:
        """Der Plan nach dieser Regel (zum Weiterrechnen und für Tests; schreiben tut struktur)."""
        p = self.vorher
        reihen = {r: list(ids) for r, ids in p.reihen.items()}
        if self.reihenfolge:
            stelle = {s: i for i, s in enumerate(self.reihenfolge)}
            for r, ids in reihen.items():
                drin = iter(sorted((s for s in ids if s in stelle), key=stelle.get))
                reihen[r] = [next(drin) if s in stelle else s for s in ids]
        ausgeblendet = (p.ausgeblendet | set(self.ausblenden)) - set(self.einblenden)
        return replace(p, zeitplan=tuple(self.zeitplan), belegung=dict(self.termine), reihen=reihen,
                       ausfall=tuple(self.ausfall), ausgeblendet=frozenset(ausgeblendet))

    def rueckgaengig(self) -> "Ergebnis":
        """Gegen-Aktion: stellt alle Termine, Ausfälle, den Stundenplan, Ausblendungen und die Reihenfolge wieder her."""
        p = self.vorher
        return Ergebnis(termine=dict(p.belegung), ausfall=list(p.ausfall), zeitplan=list(p.zeitplan),
                        ausblenden=list(self.einblenden), einblenden=list(self.ausblenden),
                        reihenfolge=self.folge_vorher, folge_vorher=self.reihenfolge, vorher=self.anwenden())
