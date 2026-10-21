"""Prüfung der Beschreibung, bevor gebaut wird. Reine Logik ohne Office-Bibliotheken.

lesen() nimmt einen JSON-Text oder ein dict und gibt eine vollständige Beschreibung zurück
(fehlende optionale Felder mit Standardwert). Ist etwas falsch, wirft es BeschreibungUngueltig
mit allen Fehlern auf einmal, jeweils mit Pfad (`bloecke[4].antwort.anzahl: ...`), damit Claude
sie in einem Durchgang beheben kann. Das Format steht in FORMAT.md, die Grenzen hier oben.
"""

import difflib
import json
import math
import re

# Grenzen (in FORMAT.md genannt; bei Änderung dort nachziehen)
MAX_JSON_ZEICHEN = 1_000_000
MAX_TITEL = 200
MAX_NUMMER = 20
MAX_BLOECKE = 200
MAX_UEBERSCHRIFT_EBENE = 3
MAX_ABSATZ = 5000
MAX_ANWEISUNG = 500
MAX_LISTE_PUNKTE = 50
MAX_LISTE_PUNKT = 1000
MAX_TABELLE_SPALTEN = 8
MAX_TABELLE_ZEILEN = 100
MAX_ZELLE = 500
ZEILENHOEHE_CM = (0.5, 15)
MAX_AUFGABEN = 20
MAX_AUFGABE = 2000
MAX_HILFE = 500
MAX_ANTWORT_LINIEN = 30
KASTEN_CM = (1, 25)
ANKREUZEN_OPTIONEN = (2, 6)
MAX_OPTION = 100
MAX_SATZANFAENGE = 5
MAX_SATZANFANG = 200
MAX_SATZANFANG_LINIEN = 10
MAX_FOLIEN = 50
MAX_FOLIE_PUNKTE = 10
MAX_FOLIE_PUNKT = 300

ARTEN = ("arbeitsblatt", "folien")
BLOCKTYPEN = ("ueberschrift", "absatz", "liste", "tabelle", "merksatz", "anweisung", "material", "aufgaben",
              "neue_seite")
ANTWORTARTEN = ("linien", "kasten", "ankreuzen", "satzanfaenge")

# Zeichen, die in docx/pptx (XML) nicht vorkommen dürfen. Zeilenumbruch und Tab sind erlaubt.
_STEUERZEICHEN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_FEHLT = object()


class BeschreibungUngueltig(ValueError):
    """Die Beschreibung ist ungültig. `fehler` enthält alle Fehler, str() eine Liste für Claude."""

    def __init__(self, fehler: list[str]):
        self.fehler = fehler
        super().__init__("Beschreibung ungültig, bitte korrigieren:\n" + "\n".join(f"- {f}" for f in fehler))


def pruefen(beschreibung: dict | str) -> list[str]:
    """Alle Fehler der Beschreibung (JSON-Text oder dict). Leer heißt: ok."""
    try:
        lesen(beschreibung)
    except BeschreibungUngueltig as e:
        return e.fehler
    return []


def lesen(beschreibung: dict | str) -> dict:
    """Geprüfte Beschreibung mit Standardwerten. Wirft BeschreibungUngueltig mit allen Fehlern."""
    p = _Pruefer()
    daten = _json_lesen(beschreibung, p) if isinstance(beschreibung, str) else beschreibung
    ergebnis = None
    if not p.fehler:
        ergebnis = _beschreibung(p, daten)
    if p.fehler:
        raise BeschreibungUngueltig(p.fehler)
    return ergebnis


def _json_lesen(text: str, p: "_Pruefer"):
    if len(text) > MAX_JSON_ZEICHEN:
        p.melden("", f"zu lang ({len(text)} Zeichen, höchstens {MAX_JSON_ZEICHEN})")
        return None
    doppelt = []

    def ohne_doppelte(paare):
        namen = [n for n, _ in paare]
        doppelt.extend(n for n in dict.fromkeys(namen) if namen.count(n) > 1)
        return dict(paare)

    try:
        daten = json.loads(text, object_pairs_hook=ohne_doppelte)
    except json.JSONDecodeError as e:
        p.melden("", f"kein gültiges JSON (Zeile {e.lineno}, Spalte {e.colno}: {e.msg})")
        return None
    for name in doppelt:
        p.melden("", f"Feld {_zeigen(name)} kommt in einem Objekt doppelt vor")
    return daten


def _beschreibung(p: "_Pruefer", daten) -> dict | None:
    if not isinstance(daten, dict):
        p.melden("", f"muss ein Objekt {{...}} sein, ist {_zeigen(daten)}")
        return None
    art = daten.get("art", _FEHLT)
    if art == "arbeitsblatt":
        return _arbeitsblatt(p, daten)
    if art == "folien":
        return _folien(p, daten)
    erlaubt = " oder ".join(_zeigen(a) for a in ARTEN)
    if art is _FEHLT:
        p.melden("art", f"fehlt, erlaubt sind {erlaubt}")
    else:
        p.melden("art", f"muss {erlaubt} sein, ist {_zeigen(art)}")
    return None


def _arbeitsblatt(p: "_Pruefer", d: dict) -> dict:
    p.felder(d, "", pflicht=("art", "titel", "bloecke"), optional=("nummer",))
    titel = p.text(d.get("titel", _FEHLT), "titel", MAX_TITEL)
    nummer = ""
    if "nummer" in d:
        nummer = p.text(d["nummer"], "nummer", MAX_NUMMER)
    bloecke = p.liste(d.get("bloecke", _FEHLT), "bloecke", 1, MAX_BLOECKE) or []
    return {
        "art": "arbeitsblatt",
        "titel": titel,
        "nummer": nummer,
        "bloecke": [_block(p, b, f"bloecke[{i}]") for i, b in enumerate(bloecke)],
    }


def _block(p: "_Pruefer", b, pfad: str) -> dict | None:
    if not isinstance(b, dict):
        p.melden(pfad, f"muss ein Objekt {{...}} sein, ist {_zeigen(b)}")
        return None
    typ = b.get("typ", _FEHLT)
    if typ not in BLOCKTYPEN:
        erlaubt = ", ".join(_zeigen(t) for t in BLOCKTYPEN)
        if typ is _FEHLT:
            p.melden(f"{pfad}.typ", f"fehlt, erlaubt sind {erlaubt}")
        else:
            p.melden(f"{pfad}.typ", f"muss einer von {erlaubt} sein, ist {_zeigen(typ)}{_aehnlich(typ, BLOCKTYPEN)}")
        return None

    if typ == "ueberschrift":
        p.felder(b, pfad, pflicht=("typ", "text"), optional=("ebene",))
        ebene = 1
        if "ebene" in b:
            ebene = p.ganzzahl(b["ebene"], f"{pfad}.ebene", 1, MAX_UEBERSCHRIFT_EBENE)
        return {"typ": typ, "text": p.text(b.get("text", _FEHLT), f"{pfad}.text", MAX_TITEL), "ebene": ebene}

    if typ in ("absatz", "anweisung"):
        p.felder(b, pfad, pflicht=("typ", "text"))
        laenge = MAX_ABSATZ if typ == "absatz" else MAX_ANWEISUNG
        return {"typ": typ, "text": p.text(b.get("text", _FEHLT), f"{pfad}.text", laenge)}

    if typ in ("merksatz", "material"):
        p.felder(b, pfad, pflicht=("typ", "text"), optional=("titel",))
        titel = ""
        if "titel" in b:
            titel = p.text(b["titel"], f"{pfad}.titel", MAX_TITEL)
        return {"typ": typ, "titel": titel, "text": p.text(b.get("text", _FEHLT), f"{pfad}.text", MAX_ABSATZ)}

    if typ == "liste":
        p.felder(b, pfad, pflicht=("typ", "punkte"), optional=("nummeriert",))
        punkte = p.liste(b.get("punkte", _FEHLT), f"{pfad}.punkte", 1, MAX_LISTE_PUNKTE) or []
        nummeriert = False
        if "nummeriert" in b:
            nummeriert = p.wahrheitswert(b["nummeriert"], f"{pfad}.nummeriert")
        return {
            "typ": typ,
            "punkte": [p.text(x, f"{pfad}.punkte[{i}]", MAX_LISTE_PUNKT) for i, x in enumerate(punkte)],
            "nummeriert": nummeriert,
        }

    if typ == "tabelle":
        return _tabelle(p, b, pfad)

    if typ == "neue_seite":
        p.felder(b, pfad, pflicht=("typ",), optional=("querformat",))
        querformat = False
        if "querformat" in b:
            querformat = p.wahrheitswert(b["querformat"], f"{pfad}.querformat")
        return {"typ": typ, "querformat": querformat}

    # aufgaben
    p.felder(b, pfad, pflicht=("typ", "aufgaben"), optional=("titel",))
    titel = "Aufgaben:"
    if "titel" in b:
        titel = p.text(b["titel"], f"{pfad}.titel", MAX_TITEL, leer_erlaubt=True)
    aufgaben = []
    for i, a in enumerate(p.liste(b.get("aufgaben", _FEHLT), f"{pfad}.aufgaben", 1, MAX_AUFGABEN) or []):
        apfad = f"{pfad}.aufgaben[{i}]"
        if not isinstance(a, dict):
            p.melden(apfad, f"muss ein Objekt {{...}} sein, ist {_zeigen(a)}")
            continue
        p.felder(a, apfad, pflicht=("text",), optional=("antwort", "hilfe"))
        antwort = _antwort(p, a["antwort"], f"{apfad}.antwort") if "antwort" in a else None
        hilfe = p.text(a["hilfe"], f"{apfad}.hilfe", MAX_HILFE) if "hilfe" in a else ""
        aufgaben.append({"text": p.text(a.get("text", _FEHLT), f"{apfad}.text", MAX_AUFGABE),
                         "antwort": antwort, "hilfe": hilfe})
    return {"typ": typ, "titel": titel, "aufgaben": aufgaben}


def _tabelle(p: "_Pruefer", b: dict, pfad: str) -> dict:
    p.felder(b, pfad, pflicht=("typ", "zeilen"), optional=("kopf", "zeilenhoehe_cm", "erste_spalte_fett"))
    kopf = None
    if "kopf" in b:
        zellen = p.liste(b["kopf"], f"{pfad}.kopf", 1, MAX_TABELLE_SPALTEN) or []
        kopf = [p.text(z, f"{pfad}.kopf[{i}]", MAX_ZELLE, leer_erlaubt=True) for i, z in enumerate(zellen)]
    zeilenhoehe = None
    if "zeilenhoehe_cm" in b:
        zeilenhoehe = p.zahl(b["zeilenhoehe_cm"], f"{pfad}.zeilenhoehe_cm", *ZEILENHOEHE_CM)
    erste_fett = False
    if "erste_spalte_fett" in b:
        erste_fett = p.wahrheitswert(b["erste_spalte_fett"], f"{pfad}.erste_spalte_fett")
    zeilen = []
    spalten = len(kopf) if kopf else None
    for i, zeile in enumerate(p.liste(b.get("zeilen", _FEHLT), f"{pfad}.zeilen", 1, MAX_TABELLE_ZEILEN) or []):
        zpfad = f"{pfad}.zeilen[{i}]"
        zellen = p.liste(zeile, zpfad, 1, MAX_TABELLE_SPALTEN)
        if zellen is None:
            continue
        if spalten is None:
            spalten = len(zellen)
        elif len(zellen) != spalten:
            woher = "wie kopf" if kopf else "wie zeilen[0]"
            p.melden(zpfad, f"hat {len(zellen)} Zellen, erwartet {spalten} ({woher})")
        zeilen.append([p.text(z, f"{zpfad}[{j}]", MAX_ZELLE, leer_erlaubt=True) for j, z in enumerate(zellen)])
    return {"typ": "tabelle", "kopf": kopf, "zeilen": zeilen, "zeilenhoehe_cm": zeilenhoehe,
            "erste_spalte_fett": erste_fett}


def _antwort(p: "_Pruefer", a, pfad: str) -> dict | None:
    if not isinstance(a, dict):
        p.melden(pfad, f"muss ein Objekt {{...}} sein, ist {_zeigen(a)}")
        return None
    art = a.get("art", _FEHLT)
    if art == "linien":
        p.felder(a, pfad, pflicht=("art", "anzahl"))
        return {"art": art, "anzahl": p.ganzzahl(a.get("anzahl", _FEHLT), f"{pfad}.anzahl", 1, MAX_ANTWORT_LINIEN)}
    if art == "kasten":
        p.felder(a, pfad, pflicht=("art", "hoehe_cm"))
        return {"art": art, "hoehe_cm": p.zahl(a.get("hoehe_cm", _FEHLT), f"{pfad}.hoehe_cm", *KASTEN_CM)}
    if art == "ankreuzen":
        p.felder(a, pfad, pflicht=("art", "optionen"))
        optionen = p.liste(a.get("optionen", _FEHLT), f"{pfad}.optionen", *ANKREUZEN_OPTIONEN) or []
        return {"art": art,
                "optionen": [p.text(o, f"{pfad}.optionen[{i}]", MAX_OPTION) for i, o in enumerate(optionen)]}
    if art == "satzanfaenge":
        p.felder(a, pfad, pflicht=("art", "saetze"))
        saetze = []
        for i, s in enumerate(p.liste(a.get("saetze", _FEHLT), f"{pfad}.saetze", 1, MAX_SATZANFAENGE) or []):
            spfad = f"{pfad}.saetze[{i}]"
            if not isinstance(s, dict):
                p.melden(spfad, f"muss ein Objekt {{...}} sein, ist {_zeigen(s)}")
                continue
            p.felder(s, spfad, pflicht=("anfang", "linien"))
            saetze.append({"anfang": p.text(s.get("anfang", _FEHLT), f"{spfad}.anfang", MAX_SATZANFANG),
                           "linien": p.ganzzahl(s.get("linien", _FEHLT), f"{spfad}.linien", 1,
                                                MAX_SATZANFANG_LINIEN)})
        return {"art": art, "saetze": saetze}
    erlaubt = ", ".join(_zeigen(x) for x in ANTWORTARTEN)
    if art is _FEHLT:
        p.melden(f"{pfad}.art", f"fehlt, erlaubt sind {erlaubt}")
    else:
        p.melden(f"{pfad}.art", f"muss einer von {erlaubt} sein, ist {_zeigen(art)}{_aehnlich(art, ANTWORTARTEN)}")
    return None


def _folien(p: "_Pruefer", d: dict) -> dict:
    p.felder(d, "", pflicht=("art", "titel", "folien"), optional=("untertitel",))
    titel = p.text(d.get("titel", _FEHLT), "titel", MAX_TITEL)
    untertitel = ""
    if "untertitel" in d:
        untertitel = p.text(d["untertitel"], "untertitel", MAX_TITEL, leer_erlaubt=True)
    folien = []
    for i, f in enumerate(p.liste(d.get("folien", _FEHLT), "folien", 1, MAX_FOLIEN) or []):
        pfad = f"folien[{i}]"
        if not isinstance(f, dict):
            p.melden(pfad, f"muss ein Objekt {{...}} sein, ist {_zeigen(f)}")
            continue
        p.felder(f, pfad, pflicht=("titel",), optional=("punkte",))
        punkte = []
        if "punkte" in f:
            punkte = p.liste(f["punkte"], f"{pfad}.punkte", 0, MAX_FOLIE_PUNKTE) or []
        folien.append({
            "titel": p.text(f.get("titel", _FEHLT), f"{pfad}.titel", MAX_TITEL),
            "punkte": [p.text(x, f"{pfad}.punkte[{j}]", MAX_FOLIE_PUNKT) for j, x in enumerate(punkte)],
        })
    return {
        "art": "folien",
        "titel": titel,
        "untertitel": untertitel,
        "folien": folien,
    }


class _Pruefer:
    """Sammelt Fehler. Die Prüfungen geben den Wert zurück, bei Fehler None (und melden ihn).
    Fehlende Pflichtfelder meldet felder(), die Einzelprüfungen übergehen dann _FEHLT still."""

    def __init__(self):
        self.fehler: list[str] = []

    def melden(self, pfad: str, text: str):
        self.fehler.append(f"{pfad or 'Beschreibung'}: {text}")

    def felder(self, d: dict, pfad: str, pflicht: tuple, optional: tuple = ()):
        erlaubt = pflicht + optional
        for name in d:
            if name not in erlaubt:
                namen = ", ".join(erlaubt)
                self.melden(_unter(pfad, name), f"unbekanntes Feld{_aehnlich(name, erlaubt)}, erlaubt sind: {namen}")
        for name in pflicht:
            if name not in d:
                self.melden(_unter(pfad, name), "fehlt")

    def text(self, wert, pfad: str, max_laenge: int, leer_erlaubt: bool = False) -> str | None:
        if wert is _FEHLT:
            return None
        if not isinstance(wert, str):
            self.melden(pfad, f"muss ein Text sein, ist {_zeigen(wert)}")
            return None
        if not leer_erlaubt and not wert.strip():
            self.melden(pfad, "darf nicht leer sein")
            return None
        if len(wert) > max_laenge:
            self.melden(pfad, f"zu lang ({len(wert)} Zeichen, höchstens {max_laenge})")
            return None
        if _STEUERZEICHEN.search(wert):
            self.melden(pfad, "enthält Steuerzeichen (erlaubt sind nur Zeilenumbruch und Tab)")
            return None
        return wert

    def ganzzahl(self, wert, pfad: str, minimum: int, maximum: int) -> int | None:
        if wert is _FEHLT:
            return None
        if isinstance(wert, bool) or not isinstance(wert, int) or not minimum <= wert <= maximum:
            self.melden(pfad, f"muss eine ganze Zahl von {minimum} bis {maximum} sein, ist {_zeigen(wert)}")
            return None
        return wert

    def zahl(self, wert, pfad: str, minimum: float, maximum: float) -> float | None:
        if wert is _FEHLT:
            return None
        if (isinstance(wert, bool) or not isinstance(wert, int | float) or not math.isfinite(wert)
                or not minimum <= wert <= maximum):
            self.melden(pfad, f"muss eine Zahl von {minimum} bis {maximum} sein, ist {_zeigen(wert)}")
            return None
        return wert

    def wahrheitswert(self, wert, pfad: str) -> bool | None:
        if not isinstance(wert, bool):
            self.melden(pfad, f"muss true oder false sein, ist {_zeigen(wert)}")
            return None
        return wert

    def liste(self, wert, pfad: str, minimum: int, maximum: int) -> list | None:
        if wert is _FEHLT:
            return None
        if not isinstance(wert, list):
            self.melden(pfad, f"muss eine Liste [...] sein, ist {_zeigen(wert)}")
            return None
        if not minimum <= len(wert) <= maximum:
            self.melden(pfad, f"muss {minimum} bis {maximum} Einträge haben, hat {len(wert)}")
            return None
        return wert


def _unter(pfad: str, name: str) -> str:
    return f"{pfad}.{name}" if pfad else name


def _aehnlich(name, erlaubt) -> str:
    """Hinweis auf einen Tippfehler, z. B. ' (gemeint: "punkte"?)'."""
    if not isinstance(name, str):
        return ""
    treffer = difflib.get_close_matches(name, erlaubt, n=1)
    return f" (gemeint: {_zeigen(treffer[0])}?)" if treffer else ""


def _zeigen(wert) -> str:
    """Wert kurz und als JSON, damit Claude ihn in seiner Beschreibung wiederfindet."""
    text = json.dumps(wert, ensure_ascii=False, default=lambda w: type(w).__name__)
    return text if len(text) <= 40 else text[:37] + "..."
