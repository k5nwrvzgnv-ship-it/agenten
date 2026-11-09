"""Prüft die JSON-Ergebnisse, die Claude je Schritt schreibt (nur Bordmittel, ohne Netz).

Grundregel: keine Zahl ohne Quelle oder Annahme. Jede Zahl steht deshalb in einem Zahl-Objekt:

    {"wert": 12.5, "einheit": "Mio EUR", "quelle": "Q-20261109-genesis-3fa2c1"}
    {"wert": 0.3, "einheit": "Anteil", "annahme": "Begründung, warum dieser Wert angenommen wird"}
    {"wert": 0.08, "einheit": "Anteil", "berechnet": {"art": "quotient", "aus": [<Zahl>, <Zahl>]}}

- quelle: ID aus data/quellen/. Bei Primärdaten (nicht "web") muss der Wert in den Rohdaten stehen,
  auch in anderer Größenordnung (Tsd/Mio/Mrd) und auf 0,5 % gerundet.
- annahme: nicht belegbar, Begründung Pflicht. Erscheint im Bericht als Annahme.
- berechnet: Python rechnet nach (produkt, quotient, summe, differenz), Abweichung höchstens 1 %.
  Damit wird auch die Marktgröße von unten geprüft: Produkt der Faktoren = Ergebnis.

Eine nackte Zahl außerhalb von "wert" ist ein Fehler. Ausnahmen nur in Feldern aus ZAEHLFELDER (Jahr, Nummer).
Fehler kommen wie beim Renderer gesammelt, jeweils mit der Stelle: `luecken[2].umsatz: Zahl ohne Quelle`.
"""

import math
import re
from datetime import date
from pathlib import Path

import quellen

ZAEHLFELDER = {"jahr", "von_jahr", "bis_jahr", "nr", "cik"}
RECHENARTEN = {"produkt": None, "quotient": 2, "summe": None, "differenz": 2}  # None = beliebig viele (ab 2)
SICHERHEIT = ("niedrig", "mittel", "hoch")
SZENARIEN = ("pessimistisch", "basis", "optimistisch")
MAX_HYPOTHESEN = 3
TOLERANZ_ROH = 0.005
TOLERANZ_RECHNUNG = 0.01
_DATUM = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _ist_zahl(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _nah(a: float, b: float, toleranz: float) -> bool:
    if a == b:
        return True
    return abs(a - b) <= toleranz * max(abs(a), abs(b))


def im_rohinhalt(wert: float, roh_werte: list[float]) -> bool:
    """True, wenn wert (auch als Tsd/Mio/Mrd bzw. deren Bruchteil) in den Rohdaten steht."""
    for exp in range(-4, 5):
        ziel = wert * 1000 ** exp
        if any(_nah(ziel, r, TOLERANZ_ROH) for r in roh_werte):
            return True
    return False


def nachrechnen(art: str, werte: list[float]) -> float:
    if art == "produkt":
        return math.prod(werte)
    if art == "summe":
        return sum(werte)
    if art == "differenz":
        return werte[0] - werte[1]
    if art == "quotient":
        if werte[1] == 0:
            raise ZeroDivisionError
        return werte[0] / werte[1]
    raise ValueError(art)


class Pruefer:
    """Sammelt Fehler und Hinweise über ein ganzes Schritt-Ergebnis. Rohdaten werden je Quelle einmal gelesen."""

    def __init__(self, quellen_ordner: Path):
        self.ordner = Path(quellen_ordner)
        self.fehler: list[str] = []
        self.hinweise: list[str] = []
        self._roh: dict[str, list[float] | None] = {}
        self.benutzte_quellen: set[str] = set()
        self.annahmen: list[tuple[str, str]] = []  # (Stelle, Begründung) für den Bericht

    def _rohwerte(self, qid: str) -> list[float] | None:
        """Zahlen der Rohdaten; None bei Art web (kein Abgleich möglich)."""
        if qid not in self._roh:
            m = quellen.meta(self.ordner, qid)
            self._roh[qid] = None if m["art"] == "web" else quellen.zahlen_im_rohinhalt(
                quellen.rohinhalt(self.ordner, qid))
        return self._roh[qid]

    def zahl(self, obj: dict, stelle: str) -> float | None:
        """Prüft ein Zahl-Objekt, gibt den Wert zurück (None bei Fehler)."""
        wert = obj.get("wert")
        if not _ist_zahl(wert):
            self.fehler.append(f"{stelle}.wert: muss eine Zahl sein, ist {wert!r}")
            return None
        einheit = obj.get("einheit")
        if not isinstance(einheit, str) or not einheit.strip():
            self.fehler.append(f"{stelle}.einheit: fehlt (z. B. \"Mio EUR\", \"Stück\", \"Anteil\")")
        belege = [k for k in ("quelle", "annahme", "berechnet") if k in obj]
        if len(belege) != 1:
            self.fehler.append(f"{stelle}: Zahl {wert} braucht genau eins von quelle, annahme, berechnet"
                               f" (hat {', '.join(belege) or 'keins'})")
            return None
        unbekannt = set(obj) - {"wert", "einheit", "quelle", "annahme", "berechnet", "stand"}
        if unbekannt:
            self.fehler.append(f"{stelle}: unbekannte Felder {', '.join(sorted(unbekannt))}")
        beleg = belege[0]
        if beleg == "quelle":
            self._quelle(obj["quelle"], wert, stelle)
        elif beleg == "annahme":
            text = obj["annahme"]
            if not isinstance(text, str) or len(text.strip()) < 10:
                self.fehler.append(f"{stelle}.annahme: Begründung fehlt oder ist zu kurz")
            else:
                self.annahmen.append((stelle, text.strip()))
        else:
            self._berechnet(obj["berechnet"], wert, stelle)
        return wert

    def _quelle(self, qid, wert: float, stelle: str) -> None:
        if not isinstance(qid, str) or not quellen.ist_id(qid):
            self.fehler.append(f"{stelle}.quelle: keine Quellen-ID: {qid!r}")
            return
        try:
            roh = self._rohwerte(qid)
        except quellen.QuellenFehler as f:
            self.fehler.append(f"{stelle}.quelle: {f}")
            return
        self.benutzte_quellen.add(qid)
        if roh is None:
            self.hinweise.append(f"{stelle}: {wert} aus Webquelle {qid}, nicht mit Rohdaten abgeglichen")
        elif not im_rohinhalt(wert, roh):
            self.fehler.append(f"{stelle}: {wert} steht nicht in den Rohdaten von {qid}")

    def _berechnet(self, b, wert: float, stelle: str) -> None:
        if not isinstance(b, dict) or set(b) != {"art", "aus"}:
            self.fehler.append(f"{stelle}.berechnet: braucht genau art und aus")
            return
        art, aus = b["art"], b["aus"]
        if art not in RECHENARTEN:
            self.fehler.append(f"{stelle}.berechnet.art: {art!r}, erlaubt: {', '.join(RECHENARTEN)}")
            return
        anzahl = RECHENARTEN[art]
        if not isinstance(aus, list) or len(aus) < 2 or (anzahl and len(aus) != anzahl):
            self.fehler.append(f"{stelle}.berechnet.aus: {art} braucht {anzahl or 'mindestens 2'} Zahlen")
            return
        werte = []
        for i, teil in enumerate(aus):
            if not isinstance(teil, dict):
                self.fehler.append(f"{stelle}.berechnet.aus[{i}]: muss ein Zahl-Objekt sein")
                return
            w = self.zahl(teil, f"{stelle}.berechnet.aus[{i}]")
            if w is None:
                return
            werte.append(w)
        try:
            soll = nachrechnen(art, werte)
        except ZeroDivisionError:
            self.fehler.append(f"{stelle}.berechnet: Division durch 0")
            return
        if not _nah(wert, soll, TOLERANZ_RECHNUNG):
            self.fehler.append(f"{stelle}: {wert} stimmt nicht, {art} ergibt {soll:.6g}")

    def durchlaufen(self, x, stelle: str = "") -> None:
        """Geht das ganze JSON durch: Zahl-Objekte prüfen, nackte Zahlen melden."""
        if isinstance(x, dict):
            if "wert" in x:
                self.zahl(x, stelle or "(oben)")
                return
            for k, v in x.items():
                pfad = f"{stelle}.{k}" if stelle else k
                if k in ZAEHLFELDER and isinstance(v, int) and not isinstance(v, bool):
                    continue
                self.durchlaufen(v, pfad)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                self.durchlaufen(v, f"{stelle}[{i}]")
        elif _ist_zahl(x) or isinstance(x, float):
            self.fehler.append(f"{stelle}: nackte Zahl {x}, gehört in ein Zahl-Objekt mit quelle oder annahme")


def _datum_ok(text) -> bool:
    if not isinstance(text, str) or not _DATUM.match(text):
        return False
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def hypothesen_pruefen(hypothesen, heute: date) -> list[str]:
    """Höchstens drei Hypothesen, jede mit Sicherheitsgrad, drei Szenarien und vorab festen Abbruchkriterien."""
    fehler = []
    if not isinstance(hypothesen, list) or not 1 <= len(hypothesen) <= MAX_HYPOTHESEN:
        return [f"hypothesen: 1 bis {MAX_HYPOTHESEN} Hypothesen, nicht "
                f"{len(hypothesen) if isinstance(hypothesen, list) else repr(hypothesen)}"]
    for i, h in enumerate(hypothesen):
        s = f"hypothesen[{i}]"
        if not isinstance(h, dict):
            fehler.append(f"{s}: muss ein Objekt sein")
            continue
        for feld in ("titel", "these", "begruendung"):
            if not isinstance(h.get(feld), str) or not h[feld].strip():
                fehler.append(f"{s}.{feld}: fehlt")
        if h.get("sicherheit") not in SICHERHEIT:
            fehler.append(f"{s}.sicherheit: {h.get('sicherheit')!r}, erlaubt: {', '.join(SICHERHEIT)}")
        sz = h.get("szenarien")
        if not isinstance(sz, dict) or set(sz) != set(SZENARIEN):
            fehler.append(f"{s}.szenarien: braucht genau {', '.join(SZENARIEN)}")
        kriterien = h.get("abbruchkriterien")
        if not isinstance(kriterien, list) or not kriterien:
            fehler.append(f"{s}.abbruchkriterien: mindestens ein Kriterium, vorab festgelegt")
            continue
        for j, k in enumerate(kriterien):
            sk = f"{s}.abbruchkriterien[{j}]"
            if not isinstance(k, dict) or not isinstance(k.get("text"), str) or not k["text"].strip():
                fehler.append(f"{sk}.text: fehlt")
                continue
            if not _datum_ok(k.get("pruefen_bis")):
                fehler.append(f"{sk}.pruefen_bis: Datum JJJJ-MM-TT fehlt")
            elif date.fromisoformat(k["pruefen_bis"]) <= heute:
                fehler.append(f"{sk}.pruefen_bis: muss in der Zukunft liegen")
    return fehler


def pruefen(daten: dict, quellen_ordner: Path, heute: date | None = None) -> Pruefer:
    """Prüft ein Schritt-Ergebnis vollständig. Fertig ist es nur ohne Fehler (p.fehler leer)."""
    p = Pruefer(quellen_ordner)
    if not isinstance(daten, dict):
        p.fehler.append("Ergebnis muss ein JSON-Objekt sein")
        return p
    p.durchlaufen(daten)
    if "hypothesen" in daten:
        p.fehler.extend(hypothesen_pruefen(daten["hypothesen"], heute or date.today()))
    return p
