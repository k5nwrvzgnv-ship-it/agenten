"""Rechensprache für Rechenfelder der Arbeitsmappe (Excel). Reine Logik ohne Office-Bibliotheken.

Claude schreibt nie Excel-Formeln, sondern kurze Ausdrücke wie `2/3 * schnitt + 1/3 * lek` oder
`mittelwert(n1:n5)`. zerlegen() prüft den Text Zeichen für Zeichen und baut einen Baum, excel() erzeugt daraus die
Formel, ausrechnen() rechnet denselben Baum in Python nach (Probe im Kontrolltext, Vergleich mit Calc). Kein Zeichen
von Claude gelangt ungeprüft in eine Formel: Es gibt nur Zahlen, Spalten derselben Zeile, Bereiche, + - * /,
Klammern und die Funktionen in FUNKTIONEN.

Leer-Regel: Eine Rechnung ist leer, solange ein benutzter Wert leer ist; bei summe, mittelwert, min und max erst,
wenn alle Werte leer sind. anzahl ist nie leer. wenn_leer(a, b) ist a, solange a nicht leer ist, sonst b.
In Excel wird daraus IF(Bedingung,"",Formel). Die Bedingung zählt mit COUNT, denn eine leere Rechnung enthält ""
und wäre für ISBLANK nicht leer. COUNT übergeht auch Fehlerwerte, ausrechnen() macht es genauso.
"""

import difflib
import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

MAX_FORMEL = 300  # Zeichen
MAX_TIEFE = 10  # Klammern und Funktionen ineinander
MAX_ARGUMENTE = 30
MAX_ZIFFERN = 9  # vor und nach dem Punkt
MAX_STELLEN = 4  # runden(x, n): n von 0 bis 4
MAX_EXCEL = 8000  # Excel erlaubt 8192 Zeichen je Formel

SAMMEL = {"summe": "SUM", "mittelwert": "AVERAGE", "min": "MIN", "max": "MAX", "anzahl": "COUNT"}
FUNKTIONEN = (*SAMMEL, "runden", "wenn_leer")
RECHENARTEN = ("zahl", "rechnung")  # Spaltenarten, mit denen gerechnet werden darf
LEER = None
FEHLER = "#DIV/0!"  # Teilen durch 0 zur Laufzeit, wie in Excel

_TOKEN = re.compile(r"(?P<zahl>\d+(?:\.\d+)?)|(?P<name>[a-z][a-z0-9_]*)|(?P<zeichen>[-+*/(),:])")
_RANG = {"+": 1, "-": 1, "*": 2, "/": 2}
_DEUTSCH = {"SUM": "SUMME", "AVERAGE": "MITTELWERT", "COUNT": "ANZAHL", "ROUND": "RUNDEN", "IF": "WENN",
            "OR": "ODER", "AND": "UND"}


class FormelFehler(ValueError):
    """Fehler in einer Formel, `stelle` zählt ab 0, str() ab 1 für Claude."""

    def __init__(self, stelle: int, text: str):
        self.stelle, self.text = stelle, text
        super().__init__(f"Zeichen {stelle + 1}: {text}")


@dataclass(frozen=True)
class Knoten:
    art: str  # zahl, spalte, bereich, op, minus, funktion
    wert: str = ""  # Zahl als Text, Spalten-id, Operator oder Funktionsname
    kinder: tuple = ()
    stelle: int = 0


def zerlegen(text: str) -> Knoten:
    """Baum des Ausdrucks. Wirft FormelFehler mit Stelle."""
    if len(text) > MAX_FORMEL:
        raise FormelFehler(MAX_FORMEL, f"zu lang ({len(text)} Zeichen, höchstens {MAX_FORMEL})")
    if not text.strip():
        raise FormelFehler(0, "leer, z. B. \"mittelwert(n1:n5)\" schreiben")
    z = _Zerleger(_tokens(text))
    baum = z.ausdruck(0)
    art, wert, stelle = z.jetzt()
    if art != "ende":
        raise FormelFehler(stelle, f"unerwartet: {wert!r}{_KOMMA_HINWEIS if wert == ',' else ''}")
    _bereiche_pruefen(baum, None)
    return baum


def pruefen_gegen(baum: Knoten, spalten: list[tuple[str, str]]) -> list[FormelFehler]:
    """Fehler der Bezüge gegen die Spalten des Blatts [(id, art), ...] in Reihenfolge."""
    arten = dict(spalten)
    ids = [i for i, _ in spalten]
    fehler = []

    def rechenspalte(sid: str, stelle: int) -> bool:
        if sid not in arten:
            treffer = difflib.get_close_matches(sid, ids, n=1)
            tipp = f" (gemeint: {treffer[0]!r}?)" if treffer else ""
            fehler.append(FormelFehler(stelle, f"unbekannte Spalte {sid!r}{tipp}, vorhanden: {', '.join(ids)}"))
            return False
        if arten[sid] not in RECHENARTEN:
            fehler.append(FormelFehler(stelle, f"Spalte {sid!r} hat die Art {arten[sid]!r}, gerechnet wird nur "
                                               "mit zahl- und rechnung-Spalten"))
            return False
        return True

    for k in _alle(baum):
        if k.art == "spalte":
            rechenspalte(k.wert, k.stelle)
        elif k.art == "bereich":
            a, b = (kind.wert for kind in k.kinder)
            if not (rechenspalte(a, k.kinder[0].stelle) & rechenspalte(b, k.kinder[1].stelle)):
                continue
            if ids.index(a) >= ids.index(b):
                fehler.append(FormelFehler(k.stelle, f"Bereich {a}:{b} muss von links nach rechts gehen "
                                                     f"({a!r} steht nicht vor {b!r})"))
                continue
            for sid in ids[ids.index(a) + 1:ids.index(b)]:
                if arten[sid] not in RECHENARTEN:
                    fehler.append(FormelFehler(k.stelle, f"Bereich {a}:{b} enthält {sid!r} mit Art {arten[sid]!r}, "
                                                         "nur zahl- und rechnung-Spalten"))
    return fehler


def abhaengig(baum: Knoten, reihe: list[str]) -> set[str]:
    """Alle Spalten, die der Ausdruck benutzt (Bereiche aufgelöst). `reihe`: Spalten-ids in Reihenfolge."""
    ids = set()
    for k in _alle(baum):
        if k.art == "spalte":
            ids.add(k.wert)
        elif k.art == "bereich":
            ids.update(_im_bereich(k, reihe))
    return ids


def zyklus(formeln: dict[str, Knoten], reihe: list[str]) -> list[str] | None:
    """Ein Kreis aus Rechnungen, die sich gegenseitig brauchen, z. B. ["a", "b", "a"], sonst None."""
    fertig = set()

    def besuchen(sid: str, weg: list[str]) -> list[str] | None:
        if sid in weg:
            return weg[weg.index(sid):] + [sid]
        if sid in fertig:
            return None
        for nach in sorted(abhaengig(formeln[sid], reihe) & formeln.keys()):
            kreis = besuchen(nach, weg + [sid])
            if kreis:
                return kreis
        fertig.add(sid)
        return None

    for sid in formeln:
        kreis = besuchen(sid, [])
        if kreis:
            return kreis
    return None


def reihenfolge(formeln: dict[str, Knoten], reihe: list[str]) -> list[str]:
    """Rechnungen so geordnet, dass jede nach allen kommt, die sie braucht (ohne Kreis, siehe zyklus)."""
    fertig: list[str] = []

    def besuchen(sid: str):
        for nach in sorted(abhaengig(formeln[sid], reihe) & formeln.keys()):
            if nach not in fertig:
                besuchen(nach)
        if sid not in fertig:
            fertig.append(sid)

    for sid in reihe:
        if sid in formeln:
            besuchen(sid)
    return fertig


def excel(baum: Knoten, zelle) -> str:
    """Excel-Formel (englische Namen, mit "="). `zelle(id)` liefert die Zelladresse in dieser Zeile, z. B. "C5"."""
    text, _, bedingung = _excel(baum, zelle)
    return f'=IF({_oder(bedingung)},"",{text})' if bedingung else f"={text}"


def deutsch(formel: str) -> str:
    """Excel-Formel so, wie sie ein deutsches Excel zeigt: MITTELWERT statt AVERAGE, ; und Komma."""
    formel = re.sub(r"\b([A-Z]+)\(", lambda m: _DEUTSCH.get(m.group(1), m.group(1)) + "(", formel)
    return formel.replace(",", ";").replace(".", ",")


def ausrechnen(baum: Knoten, werte: dict, reihe: list[str]):
    """Wert des Ausdrucks: Zahl, LEER oder FEHLER. `werte`: Spalten-id -> Zahl, LEER oder FEHLER."""
    if baum.art == "zahl":
        return float(baum.wert)
    if baum.art == "spalte":
        wert = werte.get(baum.wert)
        return wert if _ist_zahl(wert) else LEER  # wie COUNT: leer und Fehler zählen als leer
    if baum.art == "minus":
        wert = ausrechnen(baum.kinder[0], werte, reihe)
        return -wert if _ist_zahl(wert) else wert
    if baum.art == "op":
        a, b = (ausrechnen(k, werte, reihe) for k in baum.kinder)
        if a is LEER or b is LEER:
            return LEER
        if a == FEHLER or b == FEHLER:
            return FEHLER
        if baum.wert == "/":
            return FEHLER if b == 0 else a / b
        return {"+": a + b, "-": a - b, "*": a * b}[baum.wert]
    name = baum.wert
    if name in SAMMEL:
        alle = []
        for k in baum.kinder:
            alle += [werte.get(s) for s in (_im_bereich(k, reihe) if k.art == "bereich" else [k.wert])]
        zahlen = [w for w in alle if _ist_zahl(w)]
        if name == "anzahl":
            return float(len(zahlen))
        if not zahlen:
            return LEER
        if FEHLER in alle:
            return FEHLER
        return {"summe": sum, "min": min, "max": max,
                "mittelwert": lambda z: sum(z) / len(z)}[name](zahlen)
    if name == "runden":
        wert = ausrechnen(baum.kinder[0], werte, reihe)
        if not _ist_zahl(wert):
            return wert
        stellen = Decimal(1).scaleb(-int(baum.kinder[1].wert))
        return float(Decimal(repr(wert)).quantize(stellen, rounding=ROUND_HALF_UP))  # wie Excel: 0,5 nach oben
    # wenn_leer
    wert = ausrechnen(baum.kinder[0], werte, reihe)
    return ausrechnen(baum.kinder[1], werte, reihe) if wert is LEER else wert


def spaltenbuchstabe(nr: int) -> str:
    """Excel-Spalte: 0 -> A, 25 -> Z, 26 -> AA."""
    text = ""
    nr += 1
    while nr:
        nr, rest = divmod(nr - 1, 26)
        text = chr(65 + rest) + text
    return text


def zeile_ausrechnen(formeln: dict[str, Knoten], reihe: list[str], eingaben: dict) -> dict:
    """Alle Werte einer Zeile: Eingaben (Zahl oder LEER) plus jede Rechnung in der nötigen Reihenfolge."""
    werte = dict(eingaben)
    for sid in reihenfolge(formeln, reihe):
        werte[sid] = ausrechnen(formeln[sid], werte, reihe)
    return werte


# --- Zerlegen ---

_KOMMA_HINWEIS = " (Kommazahlen mit Punkt schreiben, z. B. 2.5; Komma trennt nur Argumente einer Funktion)"


def _tokens(text: str) -> list[tuple[str, str, int]]:
    tokens, pos = [], 0
    while True:
        while pos < len(text) and text[pos] in " \t\n":
            pos += 1
        if pos >= len(text):
            break
        m = _TOKEN.match(text, pos)
        if not m:
            raise FormelFehler(pos, _zeichen_fehler(text[pos]))
        if m.lastgroup == "zahl" and any(len(t) > MAX_ZIFFERN for t in m.group().split(".")):
            raise FormelFehler(pos, f"Zahl zu lang (höchstens {MAX_ZIFFERN} Ziffern vor und nach dem Punkt)")
        tokens.append((m.lastgroup, m.group(), pos))
        pos = m.end()
    tokens.append(("ende", "", len(text)))
    return tokens


def _zeichen_fehler(zeichen: str) -> str:
    if zeichen.isupper():
        return "Großbuchstaben sind nicht erlaubt, Spalten-ids und Funktionen klein schreiben"
    if zeichen == "=":
        return "kein = schreiben, nur den Ausdruck, z. B. \"2/3 * schnitt + 1/3 * lek\""
    if zeichen == ";":
        return "Argumente mit Komma trennen, z. B. runden(endnote, 2)"
    return (f"Zeichen {zeichen!r} ist nicht erlaubt (erlaubt: Zahlen mit Punkt, Spalten-ids, + - * /, Klammern, "
            f"Funktionen {', '.join(FUNKTIONEN)})")


class _Zerleger:
    """Rekursiver Abstieg: ausdruck = term (+|- term)*, term = faktor (*|/ faktor)*, faktor = -faktor | atom."""

    def __init__(self, tokens: list):
        self.tokens, self.i = tokens, 0

    def jetzt(self) -> tuple[str, str, int]:
        return self.tokens[self.i]

    def weiter(self) -> tuple[str, str, int]:
        token = self.tokens[self.i]
        self.i += 1
        return token

    def erwarten(self, zeichen: str):
        art, wert, stelle = self.jetzt()
        if wert != zeichen or art != "zeichen":
            raise FormelFehler(stelle, f"{zeichen!r} erwartet, steht {wert!r}" if art != "ende"
                               else f"{zeichen!r} fehlt am Ende")
        self.weiter()

    def ausdruck(self, tiefe: int) -> Knoten:
        if tiefe > MAX_TIEFE:
            raise FormelFehler(self.jetzt()[2], f"zu tief verschachtelt (höchstens {MAX_TIEFE} Ebenen)")
        links = self.term(tiefe)
        while self.jetzt()[1] in ("+", "-") and self.jetzt()[0] == "zeichen":
            _, op, stelle = self.weiter()
            links = Knoten("op", op, (links, self.term(tiefe)), stelle)
        return links

    def term(self, tiefe: int) -> Knoten:
        links = self.faktor(tiefe)
        while self.jetzt()[1] in ("*", "/") and self.jetzt()[0] == "zeichen":
            _, op, stelle = self.weiter()
            rechts = self.faktor(tiefe)
            if op == "/" and rechts.art == "zahl" and float(rechts.wert) == 0:
                raise FormelFehler(rechts.stelle, "Teilen durch 0")
            links = Knoten("op", op, (links, rechts), stelle)
        return links

    def faktor(self, tiefe: int) -> Knoten:
        art, wert, stelle = self.jetzt()
        if art == "zeichen" and wert == "-":
            self.weiter()
            return Knoten("minus", "-", (self.faktor(tiefe + 1),), stelle)
        return self.atom(tiefe)

    def atom(self, tiefe: int) -> Knoten:
        art, wert, stelle = self.weiter()
        if art == "zahl":
            return Knoten("zahl", wert, (), stelle)
        if art == "name":
            if self.jetzt()[1] == "(":
                return self.funktion(wert, stelle, tiefe)
            if self.jetzt()[1] == ":":
                self.weiter()
                art2, wert2, stelle2 = self.weiter()
                if art2 != "name":
                    raise FormelFehler(stelle2, f"nach ':' fehlt die letzte Spalte des Bereichs, z. B. {wert}:n5")
                return Knoten("bereich", f"{wert}:{wert2}",
                              (Knoten("spalte", wert, (), stelle), Knoten("spalte", wert2, (), stelle2)), stelle)
            return Knoten("spalte", wert, (), stelle)
        if art == "zeichen" and wert == "(":
            innen = self.ausdruck(tiefe + 1)
            self.erwarten(")")
            return innen
        if art == "ende":
            raise FormelFehler(stelle, "endet zu früh, hier fehlt noch eine Zahl, Spalte oder Klammer")
        raise FormelFehler(stelle, f"unerwartet: {wert!r}{_KOMMA_HINWEIS if wert == ',' else ''}")

    def funktion(self, name: str, stelle: int, tiefe: int) -> Knoten:
        if name not in FUNKTIONEN:
            treffer = difflib.get_close_matches(name, FUNKTIONEN, n=1)
            tipp = f" (gemeint: {treffer[0]!r}?)" if treffer else ""
            raise FormelFehler(stelle, f"unbekannte Funktion {name!r}{tipp}, erlaubt sind nur: {', '.join(FUNKTIONEN)}")
        self.erwarten("(")
        argumente = [self.ausdruck(tiefe + 1)]
        while self.jetzt()[1] == "," and self.jetzt()[0] == "zeichen":
            self.weiter()
            argumente.append(self.ausdruck(tiefe + 1))
        self.erwarten(")")
        if name in SAMMEL:
            if len(argumente) > MAX_ARGUMENTE:
                raise FormelFehler(stelle, f"{name}: höchstens {MAX_ARGUMENTE} Argumente")
            for a in argumente:
                if a.art not in ("spalte", "bereich"):
                    raise FormelFehler(a.stelle, f"{name}: nur Spalten oder Bereiche wie n1:n5, keine Rechnung "
                                                 "(dafür eine eigene rechnung-Spalte anlegen)")
        else:
            beispiel = "runden(endnote, 2)" if name == "runden" else "wenn_leer(2/3 * schnitt + 1/3 * lek, schnitt)"
            if len(argumente) != 2:
                raise FormelFehler(stelle, f"{name} braucht genau 2 Argumente, z. B. {beispiel}")
            if name == "runden":
                n = argumente[1]
                if n.art != "zahl" or "." in n.wert or int(n.wert) > MAX_STELLEN:
                    raise FormelFehler(n.stelle, f"runden: Stellen als ganze Zahl von 0 bis {MAX_STELLEN}")
        return Knoten("funktion", name, tuple(argumente), stelle)


def _bereiche_pruefen(k: Knoten, eltern: Knoten | None):
    if k.art == "bereich" and not (eltern is not None and eltern.art == "funktion" and eltern.wert in SAMMEL):
        raise FormelFehler(k.stelle, f"Bereich {k.wert} nur in {', '.join(SAMMEL)}, z. B. mittelwert({k.wert})")
    if k.art != "bereich":
        for kind in k.kinder:
            _bereiche_pruefen(kind, k)


def _alle(k: Knoten):
    yield k
    if k.art != "bereich":
        for kind in k.kinder:
            yield from _alle(kind)


def _im_bereich(k: Knoten, reihe: list[str]) -> list[str]:
    a, b = (kind.wert for kind in k.kinder)
    return reihe[reihe.index(a):reihe.index(b) + 1]


def _ist_zahl(wert) -> bool:
    return isinstance(wert, int | float) and not isinstance(wert, bool)


# --- Nach Excel ---

def _excel(k: Knoten, zelle) -> tuple[str, int, tuple]:
    """(Text, Rang, Leer-Bedingung). Rang 3: Zahl, Zelle, Funktion. Bedingung: Teile, die mit ODER gelten."""
    if k.art == "zahl":
        ganz, _, rest = k.wert.partition(".")
        return (ganz.lstrip("0") or "0") + (f".{rest}" if rest else ""), 3, ()
    if k.art == "spalte":
        ref = zelle(k.wert)
        return ref, 3, (f"COUNT({ref})=0",)
    if k.art == "minus":
        text, rang, bedingung = _excel(k.kinder[0], zelle)
        return f"-({text})" if rang < 3 else f"-{text}", 2.5, bedingung
    if k.art == "op":
        rang = _RANG[k.wert]
        (a, ra, ba), (b, rb, bb) = (_excel(kind, zelle) for kind in k.kinder)
        if ra < rang:
            a = f"({a})"
        if rb < rang or (rb == rang and k.wert in "-/"):
            b = f"({b})"
        return f"{a}{k.wert}{b}", rang, _und_dazu(ba, bb)
    name = k.wert
    if name in SAMMEL:
        argumente = ",".join(f"{zelle(a.kinder[0].wert)}:{zelle(a.kinder[1].wert)}" if a.art == "bereich"
                             else zelle(a.wert) for a in k.kinder)
        return f"{SAMMEL[name]}({argumente})", 3, () if name == "anzahl" else (f"COUNT({argumente})=0",)
    if name == "runden":
        text, _, bedingung = _excel(k.kinder[0], zelle)
        return f"ROUND({text},{k.kinder[1].wert})", 3, bedingung
    # wenn_leer
    (a, _, ba), (b, _, bb) = (_excel(kind, zelle) for kind in k.kinder)
    if not ba:
        return a, 3, ()
    return f"IF({_oder(ba)},{b},{a})", 3, (f"AND({_oder(ba)},{_oder(bb)})",) if bb else ()


def _und_dazu(a: tuple, b: tuple) -> tuple:
    return tuple(dict.fromkeys(a + b))  # ohne Doppelte, Reihenfolge bleibt


def _oder(teile: tuple) -> str:
    return teile[0] if len(teile) == 1 else f"OR({','.join(teile)})"
