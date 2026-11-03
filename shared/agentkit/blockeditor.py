"""Block-Editor für lia/instanz/reihen.toml und lerngruppen.toml (Strukturplan docs/struktur-pflege-plan.md, 7.1
Option A, nur Bordmittel, Bauschritt 4).

Der Editor ändert den Text zeilenweise, damit ein Diff der App aussieht wie Jans Handänderungen: Kommentare und Jans
Umbrüche bleiben, nur betroffene Zeilen ändern sich. Er kennt eine Teilmenge von TOML:
  Kopfzeilen   [schule], [[fach]], [[klasse]], [[klasse.zeitplan]], [[reihe]], [[reihe.stunde]]; eine Unter-Tabelle
               steht direkt hinter ihrer Tabelle oder einer Schwester (wie von Hand)
  Einträge     schluessel = wert mit einfachem Schlüssel (Buchstaben, Ziffern, _ und -), Werte wie Texte, Zahlen,
               Daten, Listen; Kommentare und Leerzeilen dazwischen
  lerngruppen  nur Einträge "klassen-id" = Text (dreifache Anführungszeichen) ohne Kopfzeilen (kopf_eintraege=True)
Alles andere (Inline-Tabellen, gepunktete oder fremde Schlüssel in Anführungszeichen, andere Tabellen) führt zu
EditorFehler: Der Editor verweigert, statt umzuformatieren. Nach dem Lesen und vor dem Schreiben vergleicht er den
Inhalt laut tomllib mit dem, was er selbst erwartet; weicht er ab, bricht er ab.

Aufbau: Dokument = kopf (Zeilen vor dem ersten Block) + Blöcke. Ein Block hat vor (Leerzeilen und Kommentare direkt
über seiner Kopfzeile, gehen beim Löschen mit), kopf (die Kopfzeile) und teile (Einträge, Kommentar- und
Leerzeilen). Neue Werte schreibt er im Stil der Datei: Text in "…", lange Texte als \"\"\"…\"\"\" mit \\-Umbruch bei
höchstens BREITE Zeichen, lange Listen eine Zeile je Wert.

Rückgängig (Gegen): Einheiten sind Blöcke mit id (eine Klasse samt ihrem Stundenplan), [schule] und der Kopf, in
lerngruppen.toml je Eintrag. gegen(alt, neu) merkt sich die betroffenen Einheiten vorher und nachher;
zurueck(gegen, text) stellt sie wieder her, aber nur, wenn sie seitdem unverändert sind (sonst EditorKonflikt).
"""

import re
import tomllib
from dataclasses import dataclass, field

BREITE = 120
EINZUG = "    "
KOEPFE = {
    "[schule]": "schule",
    "[[fach]]": "fach",
    "[[klasse]]": "klasse",
    "[[klasse.zeitplan]]": "klasse.zeitplan",
    "[[reihe]]": "reihe",
    "[[reihe.stunde]]": "reihe.stunde",
}
KOPF_VON = {art: kopf for kopf, art in KOEPFE.items()}
UNTER = {"klasse.zeitplan": "klasse", "reihe.stunde": "reihe"}  # Unter-Tabelle -> Tabelle
KOPF_EINHEIT, ENDE_EINHEIT, SCHULE_EINHEIT = "#kopf", "#ende", "#schule"

_SCHLUESSEL = re.compile(r"\s*([A-Za-z0-9_-]+|\"[a-z0-9-]+\")\s*=\s*")
_ESCAPE = {"\\": "\\\\", '"': '\\"', "\b": "\\b", "\t": "\\t", "\n": "\\n", "\f": "\\f", "\r": "\\r"}


class EditorFehler(Exception):
    """Der Text enthält etwas, das der Editor nicht kennt, oder eine Änderung ergäbe nicht den erwarteten Inhalt.
    Der Text ist für Jan."""


class EditorKonflikt(EditorFehler):
    """Rückgängig geht nicht: eine betroffene Einheit wurde seitdem geändert. einheiten: ihre Schlüssel."""

    def __init__(self, text: str, einheiten: list[str]):
        super().__init__(text)
        self.einheiten = einheiten


@dataclass
class Eintrag:
    schluessel: str  # ohne Anführungszeichen
    zeilen: list[str]
    wert: object


@dataclass
class Block:
    art: str
    kopf: str
    vor: list[str] = field(default_factory=list)
    teile: list = field(default_factory=list)  # Eintrag oder str

    def text(self) -> str:
        return "".join(self.vor) + self.kopf + _teile_text(self.teile)

    def daten(self) -> dict:
        return {t.schluessel: t.wert for t in self.teile if isinstance(t, Eintrag)}

    def eintrag(self, schluessel: str) -> Eintrag | None:
        return next((t for t in self.teile if isinstance(t, Eintrag) and t.schluessel == schluessel), None)

    def wert(self, schluessel: str, standard=None):
        e = self.eintrag(schluessel)
        return standard if e is None else e.wert

    def setzen(self, schluessel: str, wert, ordnung: tuple = (), lang: bool = False) -> bool:
        """Wert setzen; neue Zeile an der Stelle laut ordnung (nach dem letzten Eintrag, der dort davor steht).
        Gleicher Wert: nichts ändert sich (auch nicht Jans Umbruch). Gibt zurück, ob sich etwas geändert hat."""
        alt = self.eintrag(schluessel)
        if alt is not None and alt.wert == wert:
            return False
        neu = Eintrag(schluessel, wert_zeilen(schluessel, wert, lang), wert)
        if alt is not None:
            self.teile[self.teile.index(alt)] = neu
            return True
        self.teile.insert(_stelle(self.teile, schluessel, ordnung), neu)
        return True

    def entfernen(self, schluessel: str) -> bool:
        alt = self.eintrag(schluessel)
        if alt is None:
            return False
        self.teile.remove(alt)
        return True


def neuer_block(art: str, werte: list[tuple[str, object]]) -> Block:
    """Block im Stil der Datei: Leerzeile davor, Kopfzeile, je Wert ein Eintrag (leere Werte fehlen)."""
    teile = [Eintrag(k, wert_zeilen(k, v), v) for k, v in werte if v not in (None, "", [])]
    return Block(art, KOPF_VON[art] + "\n", ["\n"], teile)


@dataclass
class Dokument:
    kopf: list = field(default_factory=list)  # str oder (nur lerngruppen.toml) Eintrag
    bloecke: list[Block] = field(default_factory=list)
    kopf_eintraege: bool = False

    def text(self) -> str:
        return _teile_text(self.kopf) + "".join(b.text() for b in self.bloecke)

    def daten(self) -> dict:
        """Inhalt so, wie tomllib ihn aus text() lesen muss."""
        d = {t.schluessel: t.wert for t in self.kopf if isinstance(t, Eintrag)}
        letzte: dict[str, dict] = {}
        for b in self.bloecke:
            werte = b.daten()
            if b.art == "schule":
                d["schule"] = werte
            elif b.art in UNTER:
                letzte[UNTER[b.art]].setdefault(b.art.split(".")[1], []).append(werte)
            else:
                d.setdefault(b.art, []).append(werte)
                letzte[b.art] = werte
        return d

    # Blöcke finden

    def index(self, kennung: str) -> int:
        """Index des Blocks (fach, klasse, reihe, stunde) mit dieser id; fehlt er: EditorFehler."""
        for i, b in enumerate(self.bloecke):
            if b.art not in ("schule", "klasse.zeitplan") and b.wert("id") == kennung:
                return i
        raise EditorFehler(f"Block mit id {kennung!r} gibt es nicht")

    def block(self, kennung: str) -> Block:
        return self.bloecke[self.index(kennung)]

    def gruppe(self, i: int) -> range:
        """Block i mit seinen Unter-Tabellen (Klasse mit Stundenplan, Reihe mit Stunden)."""
        art = self.bloecke[i].art
        j = i + 1
        while j < len(self.bloecke) and UNTER.get(self.bloecke[j].art) == art:
            j += 1
        return range(i, j)

    def unter(self, kennung: str) -> list[Block]:
        """Unter-Tabellen eines Blocks (Stundenplan einer Klasse, Stunden einer Reihe) in Dateireihenfolge."""
        g = self.gruppe(self.index(kennung))
        return self.bloecke[g.start + 1:g.stop]

    # Blöcke einfügen, herausnehmen

    def einfuegen(self, stelle: int, bloecke: list[Block]) -> None:
        """Blöcke vor dem Block an stelle einfügen (stelle = len: ans Ende)."""
        if stelle == len(self.bloecke) and bloecke:
            _zeilenende(self.bloecke[-1].teile if self.bloecke else self.kopf)
        self.bloecke[stelle:stelle] = bloecke

    def herausnehmen(self, bereich: range) -> list[Block]:
        weg = self.bloecke[bereich.start:bereich.stop]
        del self.bloecke[bereich.start:bereich.stop]
        return weg

    # lerngruppen.toml: Einträge ohne Kopfzeile

    def kopf_setzen(self, schluessel: str, wert: str) -> bool:
        alt = next((t for t in self.kopf if isinstance(t, Eintrag) and t.schluessel == schluessel), None)
        if alt is not None and alt.wert == wert:
            return False
        neu = Eintrag(schluessel, wert_zeilen(f'"{schluessel}"', wert, lang=True), wert)
        if alt is not None:
            self.kopf[self.kopf.index(alt)] = neu
            return True
        _zeilenende(self.kopf)
        if self.kopf and not (isinstance(self.kopf[-1], str) and not self.kopf[-1].strip()):
            self.kopf.append("\n")  # Leerzeile zwischen den Einträgen
        self.kopf.append(neu)
        return True

    def kopf_entfernen(self, schluessel: str) -> bool:
        """Eintrag mit Kommentar direkt darüber und den Leerzeilen davor entfernen."""
        for i, t in enumerate(self.kopf):
            if isinstance(t, Eintrag) and t.schluessel == schluessel:
                davor = self.kopf[:i]
                _vor_abtrennen(davor)
                del self.kopf[len(davor):i + 1]
                return True
        return False

    # Einheiten fürs Rückgängig

    def einheiten(self) -> list[tuple[str, str]]:
        """(Schlüssel, Text) in Dateireihenfolge; zusammen ergeben sie text()."""
        if self.kopf_eintraege:
            teile: list[tuple[str, list]] = [(KOPF_EINHEIT, [])]
            for t in self.kopf:
                if isinstance(t, Eintrag):
                    teile.append((t.schluessel, _vor_abtrennen(teile[-1][1]) + [t]))
                else:
                    teile[-1][1].append(t)
            return [(k, _teile_text(v)) for k, v in teile]
        liste = [(KOPF_EINHEIT, _teile_text(self.kopf))]
        for b in self.bloecke:
            if b.art in UNTER and UNTER[b.art] == "klasse":
                k, v = liste[-1]
                liste[-1] = (k, v + b.text())
            else:
                kennung = SCHULE_EINHEIT if b.art == "schule" else b.wert("id")
                if not isinstance(kennung, str):
                    raise EditorFehler(f"{b.kopf.strip()} ohne id")
                liste.append((kennung, b.text()))
        return liste


# --- Lesen --------------------------------------------------------------------------------------------------------

def lesen(text: str, kopf_eintraege: bool = False) -> Dokument:
    """Text in Blöcke zerlegen. Unbekanntes: EditorFehler. Danach muss tomllib denselben Inhalt lesen."""
    zeilen = text.splitlines(keepends=True)
    dok = Dokument(kopf_eintraege=kopf_eintraege)
    teile = dok.kopf
    i = 0
    while i < len(zeilen):
        z = zeilen[i]
        roh = z.strip()
        if not roh or roh.startswith("#"):
            teile.append(z)
            i += 1
            continue
        if roh.startswith("["):
            kopf = roh.split("#", 1)[0].strip()
            art = KOEPFE.get(kopf)
            if art is None or kopf_eintraege:
                raise EditorFehler(f"Zeile {i + 1}: Tabelle {kopf!r} kennt der Editor nicht")
            if art in UNTER and not (dok.bloecke and dok.bloecke[-1].art in (art, UNTER[art])):
                raise EditorFehler(f"Zeile {i + 1}: {kopf} steht nicht direkt hinter {KOPF_VON[UNTER[art]]}")
            vor = _vor_abtrennen(teile)
            block = Block(art, z, vor)
            dok.bloecke.append(block)
            teile = block.teile
            i += 1
            continue
        m = _SCHLUESSEL.match(z)
        if not m:
            raise EditorFehler(f"Zeile {i + 1}: Schlüssel kennt der Editor nicht (nur einfache Schlüssel)")
        if teile is dok.kopf and not kopf_eintraege:
            raise EditorFehler(f"Zeile {i + 1}: Eintrag vor der ersten Tabelle kennt der Editor nicht")
        schluessel = m[1].strip('"')
        if m[1].startswith('"') and not kopf_eintraege:
            raise EditorFehler(f"Zeile {i + 1}: Schlüssel in Anführungszeichen kennt der Editor nicht")
        j = _wert_ende(zeilen, i, m.end())
        stueck = zeilen[i:j + 1]
        teile.append(Eintrag(schluessel, stueck, _wert_lesen(stueck, schluessel, i)))
        i = j + 1
    _inhalt_pruefen(text, dok, "Datei")
    return dok


def pruefen(dok: Dokument) -> str:
    """Neuer Text des Dokuments, nachdem tomllib ihn gelesen hat und der Inhalt dem erwarteten entspricht."""
    text = dok.text()
    _inhalt_pruefen(text, dok, "Änderung")
    if lesen(text, dok.kopf_eintraege).text() != text:
        raise EditorFehler("Änderung: der neue Text lässt sich nicht wieder genauso zerlegen")
    return text


def _inhalt_pruefen(text: str, dok: Dokument, was: str) -> None:
    try:
        gelesen = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise EditorFehler(f"{was}: kein gültiges TOML ({e})") from None
    if gelesen != dok.daten():
        raise EditorFehler(f"{was}: tomllib liest etwas anderes, als der Editor erwartet (Konstrukt unbekannt)")


def _vor_abtrennen(teile: list) -> list[str]:
    """Kommentarzeilen direkt über der Kopfzeile und die Leerzeilen darüber gehören zum nächsten Block."""
    j = len(teile)
    while j and isinstance(teile[j - 1], str) and teile[j - 1].strip().startswith("#"):
        j -= 1
    while j and isinstance(teile[j - 1], str) and not teile[j - 1].strip():
        j -= 1
    vor = teile[j:]
    del teile[j:]
    return vor


def _wert_ende(zeilen: list[str], i: int, p: int) -> int:
    """Letzte Zeile des Werts, der in Zeile i an Stelle p beginnt (Texte und Listen über mehrere Zeilen)."""
    tiefe = 0
    while True:
        z = zeilen[i]
        while p < len(z):
            if z.startswith('"""', p) or z.startswith("'''", p):
                i, p = _mehrzeilig_ende(zeilen, i, p + 3, z[p])
                z = zeilen[i]
                continue
            c = z[p]
            if c in "\"'":
                p = _einzeilig_ende(z, p + 1, c, i)
                continue
            if c == "{":
                raise EditorFehler(f"Zeile {i + 1}: Inline-Tabelle kennt der Editor nicht")
            if c == "[":
                tiefe += 1
            elif c == "]":
                tiefe -= 1
            elif c in "#\r\n":
                break
            p += 1
        if tiefe <= 0:
            return i
        i, p = i + 1, 0
        if i >= len(zeilen):
            raise EditorFehler("Liste ohne schließende Klammer")


def _einzeilig_ende(z: str, p: int, quote: str, i: int) -> int:
    while p < len(z):
        if quote == '"' and z[p] == "\\":
            p += 2
            continue
        if z[p] == quote:
            return p + 1
        if z[p] == "\n":
            break
        p += 1
    raise EditorFehler(f"Zeile {i + 1}: Text ohne schließendes Anführungszeichen")


def _mehrzeilig_ende(zeilen: list[str], i: int, p: int, quote: str) -> tuple[int, int]:
    dreifach = quote * 3
    while i < len(zeilen):
        z = zeilen[i]
        while p < len(z):
            if quote == '"' and z[p] == "\\":
                p += 2
                continue
            if z.startswith(dreifach, p):
                p += 3
                for _ in range(2):  # bis zu zwei Anführungszeichen gehören noch zum Text
                    if z.startswith(quote, p) and not z.startswith(dreifach, p + 1):
                        p += 1
                return i, p
            p += 1
        i, p = i + 1, 0
    raise EditorFehler("Text in dreifachen Anführungszeichen ohne Ende")


def _wert_lesen(stueck: list[str], schluessel: str, i: int):
    try:
        d = tomllib.loads("".join(stueck))
    except tomllib.TOMLDecodeError as e:
        raise EditorFehler(f"Zeile {i + 1}: Wert kennt der Editor nicht ({e})") from None
    if list(d) != [schluessel] or _hat_tabelle(d[schluessel]):
        raise EditorFehler(f"Zeile {i + 1}: Wert kennt der Editor nicht (Tabelle im Wert)")
    return d[schluessel]


def _hat_tabelle(wert) -> bool:
    if isinstance(wert, dict):
        return True
    return isinstance(wert, list) and any(map(_hat_tabelle, wert))


def _teile_text(teile: list) -> str:
    return "".join(t if isinstance(t, str) else "".join(t.zeilen) for t in teile)


def _zeilenende(teile: list) -> None:
    """Letzte Zeile bekommt ein Zeilenende, damit dahinter etwas angefügt werden kann."""
    if not teile:
        return
    letzte = teile[-1]
    if isinstance(letzte, str):
        if not letzte.endswith("\n"):
            teile[-1] = letzte + "\n"
    elif not letzte.zeilen[-1].endswith("\n"):
        letzte.zeilen[-1] += "\n"


def _stelle(teile: list, schluessel: str, ordnung: tuple) -> int:
    """Einfügestelle für einen neuen Eintrag: hinter dem letzten Eintrag, der laut ordnung davor steht, sonst vor
    dem ersten Eintrag, der danach steht, sonst hinter dem letzten Eintrag."""
    eintraege = [(i, t) for i, t in enumerate(teile) if isinstance(t, Eintrag)]
    if schluessel in ordnung:
        rang = ordnung.index(schluessel)
        davor = [i for i, t in eintraege if t.schluessel in ordnung and ordnung.index(t.schluessel) < rang]
        if davor:
            return davor[-1] + 1
        danach = [i for i, t in eintraege if t.schluessel in ordnung]
        if danach:
            return danach[0]
    return eintraege[-1][0] + 1 if eintraege else 0


# --- Schreiben im Stil der Datei ----------------------------------------------------------------------------------

def wert_zeilen(schluessel: str, wert, lang: bool = False) -> list[str]:
    """Zeilen für schluessel = wert im Stil von Jans Handänderungen."""
    anfang = f"{schluessel} = "
    if isinstance(wert, bool) or not isinstance(wert, (str, int, list)):
        raise EditorFehler(f"{schluessel}: Wert {type(wert).__name__} schreibt der Editor nicht")
    if isinstance(wert, int):
        return [f"{anfang}{wert}\n"]
    if isinstance(wert, str):
        kurz = anfang + _einfach(wert)
        if not lang and "\n" not in wert and len(kurz) <= BREITE:
            return [kurz + "\n"]
        return _mehrzeilig(anfang, wert)
    if not all(isinstance(x, str) for x in wert):
        raise EditorFehler(f"{schluessel}: nur Listen von Texten")
    kurz = anfang + "[" + ", ".join(map(_einfach, wert)) + "]"
    if all("\n" not in x for x in wert) and len(kurz) <= BREITE:
        return [kurz + "\n"]
    zeilen = [anfang + "[\n"]
    for x in wert:
        stueck = _mehrzeilig(EINZUG, x) if "\n" in x else [EINZUG + _einfach(x) + "\n"]
        stueck[-1] = stueck[-1][:-1] + ",\n"
        zeilen += stueck
    return zeilen + ["]\n"]


def _einfach(text: str) -> str:
    return '"' + "".join(_ESCAPE.get(c) or (f"\\u{ord(c):04x}" if ord(c) < 32 or ord(c) == 127 else c)
                         for c in text) + '"'


def _mehrzeilig(anfang: str, text: str) -> list[str]:
    """Text in dreifachen Anführungszeichen; echte Zeilenumbrüche bleiben, lange Zeilen werden an Leerzeichen mit
    \\ umbrochen (das Leerzeichen bleibt vor dem \\, wie bei Jan)."""
    absaetze = ["".join(map(_mehrzeilig_zeichen, absatz)) for absatz in text.split("\n")]
    zeilen = []
    erste = anfang + '"""' + ("\n" if text.startswith("\n") else "")
    vorn = erste
    for nr, absatz in enumerate(absaetze):
        stuecke = _umbrechen(absatz, BREITE - len(vorn) - 1, BREITE - 1)
        for k, s in enumerate(stuecke):
            zeile = (vorn if k == 0 else "") + s
            zeilen.append(zeile + ("\\\n" if k < len(stuecke) - 1 else ""))
        if nr < len(absaetze) - 1:
            zeilen[-1] += "\n"
        vorn = ""
    zeilen[-1] += '"""\n'
    return "".join(zeilen).splitlines(keepends=True)


def _mehrzeilig_zeichen(c: str) -> str:
    if c in '\\"\b\f\r':
        return _ESCAPE[c]
    return f"\\u{ord(c):04x}" if (ord(c) < 32 and c != "\t") or ord(c) == 127 else c


def _umbrechen(text: str, erste_breite: int, breite: int) -> list[str]:
    """Text an Leerzeichen (vor einem Nicht-Leerzeichen) in Stücke höchstens der Breite; jedes Stück außer dem
    letzten endet auf das Leerzeichen."""
    stuecke, rest, b = [], text, erste_breite
    while len(rest) > b:
        stellen = [i for i in range(1, len(rest) - 1) if rest[i] == " " and rest[i + 1] != " "]
        passend = [i for i in stellen if i + 1 <= b]
        if not stellen:
            break
        schnitt = (passend[-1] if passend else stellen[0]) + 1
        stuecke.append(rest[:schnitt])
        rest, b = rest[schnitt:], breite
    return stuecke + [rest]


# --- Rückgängig ---------------------------------------------------------------------------------------------------

def gegen(alt: str, neu: str, kopf_eintraege: bool = False) -> dict:
    """Gegen-Operation von alt nach neu (JSON-fähig): die betroffenen Einheiten vorher und nachher und die
    Reihenfolge vorher. Betroffen ist, was sich geändert hat, neu ist, fehlt oder an eine andere Stelle kam."""
    a = lesen(alt, kopf_eintraege).einheiten()
    n = lesen(neu, kopf_eintraege).einheiten()
    va, vn = dict(a), dict(n)
    gemeinsam = [k for k, _ in a if k in vn]
    bleibt = set(_lcs(gemeinsam, [k for k, _ in n if k in va]))
    betroffen = [k for k, _ in a + n if va.get(k) != vn.get(k) or (k in va and k in vn and k not in bleibt)]
    betroffen = list(dict.fromkeys(betroffen))
    return {"reihenfolge": [k for k, _ in a], "betroffen": betroffen,
            "vorher": {k: va[k] for k in betroffen if k in va}, "nachher": {k: vn[k] for k in betroffen if k in vn}}


def zurueck(g: dict, text: str, kopf_eintraege: bool = False) -> str:
    """Gegen-Operation auf den aktuellen Text anwenden. Ist eine betroffene Einheit seitdem geändert (oder neu, oder
    weg): EditorKonflikt, nichts geändert. Andere Einheiten bleiben, wie sie jetzt sind."""
    jetzt = lesen(text, kopf_eintraege).einheiten()
    werte = dict(jetzt)
    geaendert = [k for k in g["betroffen"] if werte.get(k) != g["nachher"].get(k)]
    if geaendert:
        raise EditorKonflikt("Inzwischen geändert: " + ", ".join(geaendert), geaendert)
    betroffen = set(g["betroffen"])
    liste = [(k, v) for k, v in jetzt if k not in betroffen]
    letzte = None
    for k in g["reihenfolge"]:
        if k in betroffen:
            stelle = 0 if letzte is None else next(i for i, (x, _) in enumerate(liste) if x == letzte) + 1
            liste.insert(stelle, (k, g["vorher"][k]))
            letzte = k
        elif k in werte:
            letzte = k
    neu = "".join(v for _, v in liste)
    lesen(neu, kopf_eintraege)
    return neu


def _lcs(a: list, b: list) -> list:
    """Längste gemeinsame Teilfolge (Einheiten, die nicht bewegt wurden)."""
    tab = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) - 1, -1, -1):
        for j in range(len(b) - 1, -1, -1):
            tab[i][j] = tab[i + 1][j + 1] + 1 if a[i] == b[j] else max(tab[i + 1][j], tab[i][j + 1])
    folge, i, j = [], 0, 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            folge.append(a[i])
            i, j = i + 1, j + 1
        elif tab[i + 1][j] >= tab[i][j + 1]:
            i += 1
        else:
            j += 1
    return folge
