"""Prüfung der Beschreibung, bevor gebaut wird. Reine Logik ohne Office-Bibliotheken.

lesen() nimmt einen JSON-Text oder ein dict und gibt eine vollständige Beschreibung zurück
(fehlende optionale Felder mit Standardwert). Ist etwas falsch, wirft es BeschreibungUngueltig
mit allen Fehlern auf einmal, jeweils mit Pfad (`bloecke[4].antwort.anzahl: ...`), damit Claude
sie in einem Durchgang beheben kann. Das Format steht in FORMAT.md, die Grenzen hier oben.
"""

import datetime
import difflib
import json
import math
import re

from renderer import rechnung
from renderer.icons import NAMEN

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
MAX_UNTERTITEL = 100
MAX_FOLIE_ICONS = 2
MAX_FOLIE_INHALT = 4
MAX_ELEMENT_TEXT = 1500
MAX_FOLIE_PUNKTE = 8
MAX_FOLIE_PUNKT = 300
MAX_KASTEN_ABSAETZE = 6
MAX_ZENTRIERT_ABSAETZE = 4
MAX_KURZTEXT = 100
MAX_MINUTEN = 180
SPALTEN = (2, 3)
MAX_SPALTE_TEXT = 600
AUSWAHL_OPTIONEN = (2, 4)
MAX_FEEDBACK = 4
LEGENDE = (2, 4)
MAX_TEXTTEILE = 30
# Zusammenfassung
MAX_KURS = 100
MAX_Z_EBENE = 2
MAX_QUELLEN = 10
MAX_QUELLE_STELLE = 100
MAX_GEGEBEN = 15
MAX_SCHRITTE = 15
MAX_RECHNUNG = 300
MAX_SELBSTTEST = 30
MAX_FRAGE = 1000
MAX_LOESUNG = 3000
MAX_OFFENE_FRAGEN = 30
# Arbeitsmappe (Excel)
MAX_BLAETTER = 10
MAX_BLATTNAME = 31  # Grenze von Excel
MAX_HINWEISE = 5
MAX_HINWEIS = 300
MAX_ZEILEN = 500
MAX_SPALTEN = 30
MAX_KOPF = 50
MAX_SPALTE_ID = 30
BREITE = (3, 60)  # Zeichen
MAX_FIXIERT = 3
MAX_NACHKOMMA = 4
MAX_ZAHL = 1e9
MAX_ZEICHEN_GRENZE = 1000

ARTEN = ("arbeitsblatt", "folien", "zusammenfassung", "arbeitsmappe")
BLOCKTYPEN = ("ueberschrift", "absatz", "liste", "tabelle", "merksatz", "anweisung", "material", "aufgaben",
              "neue_seite")
ANTWORTARTEN = ("linien", "kasten", "ankreuzen", "satzanfaenge")
ELEMENTTYPEN = ("text", "punkte", "kasten", "leitfrage", "zentriert", "zeit", "spalten", "auswahl", "satzanfang",
                "feedback", "legende")
TEXTFARBEN = ("blau", "orange", "gruen", "rot", "grau")
Z_BLOCKTYPEN = ("ueberschrift", "absatz", "liste", "tabelle", "hinweis", "rechenbeispiel")
HINWEISARTEN = ("pruefungsrelevant", "organisatorisch")
KENNZEICHNUNGEN = ("unsicher", "muendlich")
QUELLENARTEN = ("transkript", "folie", "norm")
SPALTENARTEN = ("nummer", "text", "zahl", "rechnung")
ICON_NAMEN = NAMEN

# Zeichen, die in docx/pptx (XML) nicht vorkommen dürfen. Zeilenumbruch und Tab sind erlaubt.
_STEUERZEICHEN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_DATUM = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")
_SEITEN = re.compile(r"^\d{1,4}( ?[-–] ?\d{1,4})?(, ?\d{1,4}( ?[-–] ?\d{1,4})?)*$")  # 4 | 4-5 | 4, 7
_NUMMER_VORN = re.compile(r"^\d+(\.\d+)+\.?\s|^\d+\.\s")  # "1. ", "1.2 ", nicht "3 Säulen"
_QUELLE_IM_TEXT = re.compile(r"[\[(](Transkript|Folie)\b")
_SPALTE_ID = re.compile(r"^[a-z][a-z0-9_]*$")
_BLATTNAME_VERBOTEN = re.compile(r"[\[\]:*?/\\]")
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
    if art == "zusammenfassung":
        return _zusammenfassung(p, daten)
    if art == "arbeitsmappe":
        return _arbeitsmappe(p, daten)
    erlaubt = ", ".join(_zeigen(a) for a in ARTEN[:-1]) + f" oder {_zeigen(ARTEN[-1])}"
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
    p.felder(d, "", pflicht=("art", "titel", "folien"), optional=("untertitel", "icon"))
    titel = p.text(d.get("titel", _FEHLT), "titel", MAX_TITEL)
    untertitel = p.text(d["untertitel"], "untertitel", MAX_UNTERTITEL) if "untertitel" in d else ""
    icon = _icon(p, d["icon"], "icon") if "icon" in d else None
    folien = []
    for i, f in enumerate(p.liste(d.get("folien", _FEHLT), "folien", 1, MAX_FOLIEN) or []):
        pfad = f"folien[{i}]"
        if not isinstance(f, dict):
            p.melden(pfad, f"muss ein Objekt {{...}} sein, ist {_zeigen(f)}")
            continue
        p.felder(f, pfad, pflicht=("titel", "inhalt"), optional=("icons",))
        bilder = []
        if "icons" in f:
            namen = p.liste(f["icons"], f"{pfad}.icons", 1, MAX_FOLIE_ICONS) or []
            bilder = [_icon(p, n, f"{pfad}.icons[{j}]") for j, n in enumerate(namen)]
        inhalt = p.liste(f.get("inhalt", _FEHLT), f"{pfad}.inhalt", 1, MAX_FOLIE_INHALT) or []
        folien.append({
            "titel": p.text(f.get("titel", _FEHLT), f"{pfad}.titel", MAX_TITEL),
            "icons": bilder,
            "inhalt": [_element(p, e, f"{pfad}.inhalt[{j}]") for j, e in enumerate(inhalt)],
        })
    return {"art": "folien", "titel": titel, "untertitel": untertitel, "icon": icon, "folien": folien}


def _element(p: "_Pruefer", e, pfad: str) -> dict | None:
    if not isinstance(e, dict):
        p.melden(pfad, f"muss ein Objekt {{...}} sein, ist {_zeigen(e)}")
        return None
    typ = e.get("typ", _FEHLT)
    if typ not in ELEMENTTYPEN:
        erlaubt = ", ".join(_zeigen(t) for t in ELEMENTTYPEN)
        if typ is _FEHLT:
            p.melden(f"{pfad}.typ", f"fehlt, erlaubt sind {erlaubt}")
        else:
            p.melden(f"{pfad}.typ", f"muss einer von {erlaubt} sein, ist {_zeigen(typ)}{_aehnlich(typ, ELEMENTTYPEN)}")
        return None

    def texte(feld: str, minimum: int, maximum: int, laenge: int, teile: bool = True) -> list:
        werte = p.liste(e.get(feld, _FEHLT), f"{pfad}.{feld}", minimum, maximum) or []
        pruef = _textteile if teile else (lambda p_, w, pf, n: p_.text(w, pf, n))
        return [pruef(p, w, f"{pfad}.{feld}[{i}]", laenge) for i, w in enumerate(werte)]

    if typ == "text":
        p.felder(e, pfad, pflicht=("typ", "text"))
        return {"typ": typ, "text": _textteile(p, e.get("text", _FEHLT), f"{pfad}.text", MAX_ELEMENT_TEXT)}
    if typ == "punkte":
        p.felder(e, pfad, pflicht=("typ", "punkte"))
        return {"typ": typ, "punkte": texte("punkte", 1, MAX_FOLIE_PUNKTE, MAX_FOLIE_PUNKT)}
    if typ == "kasten":
        p.felder(e, pfad, pflicht=("typ", "absaetze"), optional=("titel",))
        titel = p.text(e["titel"], f"{pfad}.titel", MAX_KURZTEXT) if "titel" in e else ""
        return {"typ": typ, "titel": titel, "absaetze": texte("absaetze", 1, MAX_KASTEN_ABSAETZE, MAX_ELEMENT_TEXT)}
    if typ in ("leitfrage", "satzanfang"):
        p.felder(e, pfad, pflicht=("typ", "text"))
        return {"typ": typ, "text": p.text(e.get("text", _FEHLT), f"{pfad}.text", MAX_TITEL)}
    if typ == "zentriert":
        p.felder(e, pfad, pflicht=("typ", "absaetze"))
        return {"typ": typ, "absaetze": texte("absaetze", 1, MAX_ZENTRIERT_ABSAETZE, MAX_FOLIE_PUNKT)}
    if typ == "zeit":
        p.felder(e, pfad, pflicht=("typ", "minuten"))
        return {"typ": typ, "minuten": p.ganzzahl(e.get("minuten", _FEHLT), f"{pfad}.minuten", 1, MAX_MINUTEN)}
    if typ == "spalten":
        p.felder(e, pfad, pflicht=("typ", "spalten"))
        spalten = []
        for i, s in enumerate(p.liste(e.get("spalten", _FEHLT), f"{pfad}.spalten", *SPALTEN) or []):
            spfad = f"{pfad}.spalten[{i}]"
            if not isinstance(s, dict):
                p.melden(spfad, f"muss ein Objekt {{...}} sein, ist {_zeigen(s)}")
                continue
            p.felder(s, spfad, pflicht=("titel", "text"))
            spalten.append({"titel": p.text(s.get("titel", _FEHLT), f"{spfad}.titel", MAX_KURZTEXT),
                            "text": _textteile(p, s.get("text", _FEHLT), f"{spfad}.text", MAX_SPALTE_TEXT)})
        return {"typ": typ, "spalten": spalten}
    if typ == "auswahl":
        p.felder(e, pfad, pflicht=("typ", "optionen"))
        return {"typ": typ, "optionen": texte("optionen", *AUSWAHL_OPTIONEN, MAX_KURZTEXT, teile=False)}
    if typ == "feedback":
        p.felder(e, pfad, pflicht=("typ", "gut", "schlecht"))
        return {"typ": typ, "gut": texte("gut", 1, MAX_FEEDBACK, MAX_FOLIE_PUNKT, teile=False),
                "schlecht": texte("schlecht", 1, MAX_FEEDBACK, MAX_FOLIE_PUNKT, teile=False)}
    # legende
    p.felder(e, pfad, pflicht=("typ", "eintraege"))
    eintraege = []
    for i, x in enumerate(p.liste(e.get("eintraege", _FEHLT), f"{pfad}.eintraege", *LEGENDE) or []):
        xpfad = f"{pfad}.eintraege[{i}]"
        if not isinstance(x, dict):
            p.melden(xpfad, f"muss ein Objekt {{...}} sein, ist {_zeigen(x)}")
            continue
        p.felder(x, xpfad, pflicht=("text", "farbe"))
        eintraege.append({"text": p.text(x.get("text", _FEHLT), f"{xpfad}.text", MAX_KURZTEXT),
                          "farbe": _farbe(p, x.get("farbe", _FEHLT), f"{xpfad}.farbe")})
    return {"typ": typ, "eintraege": eintraege}


def _zusammenfassung(p: "_Pruefer", d: dict) -> dict:
    p.felder(d, "", pflicht=("art", "titel", "kurs", "datum", "bloecke"),
             optional=("untertitel", "selbsttest", "offene_fragen"))
    titel = p.text(d.get("titel", _FEHLT), "titel", MAX_TITEL)
    untertitel = p.text(d["untertitel"], "untertitel", MAX_TITEL) if "untertitel" in d else ""
    kurs = p.text(d.get("kurs", _FEHLT), "kurs", MAX_KURS)
    datum = _datum(p, d.get("datum", _FEHLT), "datum")
    bloecke = p.liste(d.get("bloecke", _FEHLT), "bloecke", 1, MAX_BLOECKE) or []
    gelesen = [_z_block(p, b, f"bloecke[{i}]") for i, b in enumerate(bloecke)]
    ebene1 = False
    for i, b in enumerate(gelesen):
        if b is None or (b["typ"] == "ueberschrift" and b["ebene"] is None):
            break  # Block schon als Fehler gemeldet, keine Folgefehler
        if b["typ"] == "ueberschrift":
            if b["ebene"] == 2 and not ebene1:
                p.melden(f"bloecke[{i}].ebene", "Ebene 2 vor der ersten Überschrift der Ebene 1, "
                                                 "erst eine Überschrift mit ebene 1 setzen")
            ebene1 = ebene1 or b["ebene"] == 1
    selbsttest = []
    if "selbsttest" in d:
        for i, f in enumerate(p.liste(d["selbsttest"], "selbsttest", 1, MAX_SELBSTTEST) or []):
            fpfad = f"selbsttest[{i}]"
            if not isinstance(f, dict):
                p.melden(fpfad, f"muss ein Objekt {{...}} sein, ist {_zeigen(f)}")
                continue
            p.felder(f, fpfad, pflicht=("frage", "loesung"), optional=("quellen",))
            selbsttest.append({"frage": _z_text(p, f.get("frage", _FEHLT), f"{fpfad}.frage", MAX_FRAGE),
                               "loesung": _z_text(p, f.get("loesung", _FEHLT), f"{fpfad}.loesung", MAX_LOESUNG),
                               "quellen": _quellen(p, f, fpfad)})
    offene = []
    if "offene_fragen" in d:
        fragen = p.liste(d["offene_fragen"], "offene_fragen", 1, MAX_OFFENE_FRAGEN) or []
        offene = [_punkt(p, f, f"offene_fragen[{i}]", MAX_FRAGE) for i, f in enumerate(fragen)]
    return {"art": "zusammenfassung", "titel": titel, "untertitel": untertitel, "kurs": kurs, "datum": datum,
            "bloecke": gelesen, "selbsttest": selbsttest, "offene_fragen": offene}


def _z_block(p: "_Pruefer", b, pfad: str) -> dict | None:
    """Block einer Zusammenfassung. Fast alle Blöcke tragen `quellen` und `kennzeichnung`."""
    if not isinstance(b, dict):
        p.melden(pfad, f"muss ein Objekt {{...}} sein, ist {_zeigen(b)}")
        return None
    typ = b.get("typ", _FEHLT)
    if typ not in Z_BLOCKTYPEN:
        erlaubt = ", ".join(_zeigen(t) for t in Z_BLOCKTYPEN)
        if typ is _FEHLT:
            p.melden(f"{pfad}.typ", f"fehlt, erlaubt sind {erlaubt}")
        else:
            p.melden(f"{pfad}.typ", f"muss einer von {erlaubt} sein, ist {_zeigen(typ)}{_aehnlich(typ, Z_BLOCKTYPEN)}")
        return None
    beleg = ("quellen", "kennzeichnung")

    if typ == "ueberschrift":
        p.felder(b, pfad, pflicht=("typ", "text"), optional=("ebene",))
        ebene = p.ganzzahl(b["ebene"], f"{pfad}.ebene", 1, MAX_Z_EBENE) if "ebene" in b else 1
        text = p.text(b.get("text", _FEHLT), f"{pfad}.text", MAX_TITEL)
        if text and _NUMMER_VORN.match(text):
            p.melden(f"{pfad}.text", "ohne Nummer schreiben, die Nummer setzt der Renderer")
        return {"typ": typ, "text": text, "ebene": ebene}

    if typ == "absatz":
        p.felder(b, pfad, pflicht=("typ", "text"), optional=beleg)
        return {"typ": typ, "text": _z_text(p, b.get("text", _FEHLT), f"{pfad}.text", MAX_ABSATZ),
                **_beleg(p, b, pfad)}

    if typ == "liste":
        p.felder(b, pfad, pflicht=("typ", "punkte"), optional=("nummeriert",))
        punkte = p.liste(b.get("punkte", _FEHLT), f"{pfad}.punkte", 1, MAX_LISTE_PUNKTE) or []
        nummeriert = p.wahrheitswert(b["nummeriert"], f"{pfad}.nummeriert") if "nummeriert" in b else False
        return {"typ": typ, "nummeriert": nummeriert,
                "punkte": [_punkt(p, x, f"{pfad}.punkte[{i}]", MAX_LISTE_PUNKT) for i, x in enumerate(punkte)]}

    if typ == "tabelle":
        p.felder(b, pfad, pflicht=("typ", "zeilen"), optional=("titel", "kopf", "erste_spalte_fett") + beleg)
        titel = p.text(b["titel"], f"{pfad}.titel", MAX_TITEL) if "titel" in b else ""
        # Prüfung der Zellen wie beim Arbeitsblatt, ohne zeilenhoehe_cm (keine Ausfülltabellen)
        tabelle = _tabelle(p, {k: v for k, v in b.items() if k not in ("titel",) + beleg}, pfad)
        del tabelle["zeilenhoehe_cm"]
        return {**tabelle, "titel": titel, **_beleg(p, b, pfad)}

    if typ == "hinweis":
        p.felder(b, pfad, pflicht=("typ", "art", "text"), optional=("titel",) + beleg)
        art = b.get("art", _FEHLT)
        if art is not _FEHLT and art not in HINWEISARTEN:
            p.melden(f"{pfad}.art", f"muss {' oder '.join(_zeigen(a) for a in HINWEISARTEN)} sein, ist {_zeigen(art)}"
                                    f"{_aehnlich(art, HINWEISARTEN)}")
            art = None
        titel = p.text(b["titel"], f"{pfad}.titel", MAX_TITEL) if "titel" in b else ""
        return {"typ": typ, "art": None if art is _FEHLT else art, "titel": titel,
                "text": _z_text(p, b.get("text", _FEHLT), f"{pfad}.text", MAX_ABSATZ), **_beleg(p, b, pfad)}

    # rechenbeispiel
    p.felder(b, pfad, pflicht=("typ", "aufgabe", "schritte", "ergebnis"), optional=("titel", "gegeben") + beleg)
    titel = p.text(b["titel"], f"{pfad}.titel", MAX_TITEL) if "titel" in b else ""
    gegeben = []
    if "gegeben" in b:
        werte = p.liste(b["gegeben"], f"{pfad}.gegeben", 1, MAX_GEGEBEN) or []
        gegeben = [p.text(w, f"{pfad}.gegeben[{i}]", MAX_RECHNUNG) for i, w in enumerate(werte)]
    schritte = []
    for i, s in enumerate(p.liste(b.get("schritte", _FEHLT), f"{pfad}.schritte", 1, MAX_SCHRITTE) or []):
        spfad = f"{pfad}.schritte[{i}]"
        if not isinstance(s, dict):
            p.melden(spfad, f"muss ein Objekt {{...}} sein, ist {_zeigen(s)}")
            continue
        p.felder(s, spfad, pflicht=("text",), optional=("rechnung",))
        schritte.append({"text": p.text(s.get("text", _FEHLT), f"{spfad}.text", MAX_LISTE_PUNKT),
                         "rechnung": p.text(s["rechnung"], f"{spfad}.rechnung", MAX_RECHNUNG)
                         if "rechnung" in s else ""})
    return {"typ": typ, "titel": titel,
            "aufgabe": p.text(b.get("aufgabe", _FEHLT), f"{pfad}.aufgabe", MAX_AUFGABE), "gegeben": gegeben,
            "schritte": schritte, "ergebnis": p.text(b.get("ergebnis", _FEHLT), f"{pfad}.ergebnis", MAX_RECHNUNG),
            **_beleg(p, b, pfad)}


def _arbeitsmappe(p: "_Pruefer", d: dict) -> dict:
    p.felder(d, "", pflicht=("art", "titel", "blaetter"))
    titel = p.text(d.get("titel", _FEHLT), "titel", MAX_TITEL)
    blaetter = []
    namen = []
    for i, b in enumerate(p.liste(d.get("blaetter", _FEHLT), "blaetter", 1, MAX_BLAETTER) or []):
        blatt = _blatt(p, b, f"blaetter[{i}]")
        if blatt is None:
            continue
        if blatt["name"] and blatt["name"].lower() in namen:
            p.melden(f"blaetter[{i}].name", f"{_zeigen(blatt['name'])} gibt es schon (Groß-/Kleinschreibung zählt "
                                            "nicht), jedes Blatt braucht einen eigenen Namen")
        namen.append((blatt["name"] or "").lower())
        blaetter.append(blatt)
    return {"art": "arbeitsmappe", "titel": titel, "blaetter": blaetter}


def _blatt(p: "_Pruefer", b, pfad: str) -> dict | None:
    if not isinstance(b, dict):
        p.melden(pfad, f"muss ein Objekt {{...}} sein, ist {_zeigen(b)}")
        return None
    p.felder(b, pfad, pflicht=("name", "zeilen", "spalten"),
             optional=("titel", "hinweise", "fixierte_spalten", "hochformat"))
    name = p.text(b.get("name", _FEHLT), f"{pfad}.name", MAX_BLATTNAME)
    if name is not None:
        if _BLATTNAME_VERBOTEN.search(name) or name.startswith("'") or name.endswith("'"):
            p.melden(f"{pfad}.name", "ohne die Zeichen [ ] : * ? / \\ und ohne ' am Anfang oder Ende (Excel)")
            name = None
        elif name.strip().lower() == "history":
            p.melden(f"{pfad}.name", "\"History\" ist in Excel reserviert, bitte anders nennen")
            name = None
    titel = p.text(b["titel"], f"{pfad}.titel", MAX_TITEL) if "titel" in b else ""
    hinweise = []
    if "hinweise" in b:
        texte = p.liste(b["hinweise"], f"{pfad}.hinweise", 1, MAX_HINWEISE) or []
        hinweise = [p.text(h, f"{pfad}.hinweise[{j}]", MAX_HINWEIS) for j, h in enumerate(texte)]
    fixiert = p.ganzzahl(b["fixierte_spalten"], f"{pfad}.fixierte_spalten", 0, MAX_FIXIERT) \
        if "fixierte_spalten" in b else 0
    spalten = [_spalte(p, s, f"{pfad}.spalten[{j}]")
               for j, s in enumerate(p.liste(b.get("spalten", _FEHLT), f"{pfad}.spalten", 1, MAX_SPALTEN) or [])]
    if fixiert and len(spalten) <= fixiert:
        p.melden(f"{pfad}.fixierte_spalten", f"muss kleiner als die Zahl der Spalten ({len(spalten)}) sein")
    _formeln_pruefen(p, spalten, pfad)
    return {
        "name": name,
        "titel": titel,
        "hinweise": hinweise,
        "zeilen": p.ganzzahl(b.get("zeilen", _FEHLT), f"{pfad}.zeilen", 1, MAX_ZEILEN),
        "fixierte_spalten": fixiert,
        "hochformat": p.wahrheitswert(b["hochformat"], f"{pfad}.hochformat") if "hochformat" in b else False,
        "spalten": spalten,
    }


def _spalte(p: "_Pruefer", s, pfad: str) -> dict | None:
    if not isinstance(s, dict):
        p.melden(pfad, f"muss ein Objekt {{...}} sein, ist {_zeigen(s)}")
        return None
    art = s.get("art", _FEHLT)
    if art not in SPALTENARTEN:
        erlaubt = ", ".join(_zeigen(a) for a in SPALTENARTEN)
        if art is _FEHLT:
            p.melden(f"{pfad}.art", f"fehlt, erlaubt sind {erlaubt}")
        else:
            p.melden(f"{pfad}.art", f"muss einer von {erlaubt} sein, ist {_zeigen(art)}{_aehnlich(art, SPALTENARTEN)}")
        return None
    zusatz = {"nummer": (), "text": ("max_zeichen",), "zahl": ("ganz", "min", "max", "nachkommastellen"),
              "rechnung": ("nachkommastellen",)}[art]
    p.felder(s, pfad, pflicht=("id", "kopf", "art") + (("formel",) if art == "rechnung" else ()),
             optional=("breite",) + zusatz)
    sid = p.text(s.get("id", _FEHLT), f"{pfad}.id", MAX_SPALTE_ID)
    if sid is not None and (not _SPALTE_ID.match(sid) or sid in rechnung.FUNKTIONEN):
        grund = "ist ein Funktionsname" if sid in rechnung.FUNKTIONEN else \
            "nur Kleinbuchstaben a-z, Ziffern und _, am Anfang ein Buchstabe, z. B. \"note1\""
        p.melden(f"{pfad}.id", f"{_zeigen(sid)} geht nicht: {grund}")
        sid = None
    spalte = {"id": sid, "kopf": p.text(s.get("kopf", _FEHLT), f"{pfad}.kopf", MAX_KOPF), "art": art,
              "breite": p.zahl(s["breite"], f"{pfad}.breite", *BREITE) if "breite" in s else None,
              "max_zeichen": None, "ganz": False, "min": None, "max": None, "nachkommastellen": None, "formel": None,
              "baum": None}  # baum: zerlegte Formel (rechnung.Knoten)
    if art == "text" and "max_zeichen" in s:
        spalte["max_zeichen"] = p.ganzzahl(s["max_zeichen"], f"{pfad}.max_zeichen", 1, MAX_ZEICHEN_GRENZE)
    if art == "zahl":
        ganz = p.wahrheitswert(s["ganz"], f"{pfad}.ganz") if "ganz" in s else False
        spalte["ganz"] = ganz
        for grenze in ("min", "max"):
            if grenze in s:
                wert = p.zahl(s[grenze], f"{pfad}.{grenze}", -MAX_ZAHL, MAX_ZAHL)
                if wert is not None and ganz and wert != int(wert):
                    p.melden(f"{pfad}.{grenze}", f"muss bei ganz: true eine ganze Zahl sein, ist {_zeigen(wert)}")
                    wert = None
                spalte[grenze] = wert
        if spalte["min"] is not None and spalte["max"] is not None and spalte["min"] > spalte["max"]:
            p.melden(f"{pfad}.min", f"ist größer als max ({_zeigen(spalte['min'])} > {_zeigen(spalte['max'])})")
        if "nachkommastellen" in s and ganz:
            p.melden(f"{pfad}.nachkommastellen", "passt nicht zu ganz: true, eins von beiden weglassen")
        elif "nachkommastellen" in s:
            spalte["nachkommastellen"] = p.ganzzahl(s["nachkommastellen"], f"{pfad}.nachkommastellen", 0,
                                                    MAX_NACHKOMMA)
    if art == "rechnung":
        spalte["nachkommastellen"] = p.ganzzahl(s["nachkommastellen"], f"{pfad}.nachkommastellen", 0,
                                                MAX_NACHKOMMA) if "nachkommastellen" in s else 2
        formel = p.text(s.get("formel", _FEHLT), f"{pfad}.formel", rechnung.MAX_FORMEL)
        if formel is not None:
            try:
                spalte["baum"] = rechnung.zerlegen(formel)
                spalte["formel"] = formel
            except rechnung.FormelFehler as e:
                p.melden(f"{pfad}.formel", str(e))
    return spalte


def _formeln_pruefen(p: "_Pruefer", spalten: list, pfad: str):
    """Bezüge, Kreise und Länge der Formeln eines Blatts. Nur, wenn alle Spalten lesbar sind (keine Folgefehler)."""
    if any(s is None or s["id"] is None for s in spalten):
        return
    ids = [s["id"] for s in spalten]
    for j, sid in enumerate(ids):
        if sid in ids[:j]:
            p.melden(f"{pfad}.spalten[{j}].id", f"{_zeigen(sid)} gibt es schon in spalten[{ids.index(sid)}], "
                                                 "jede Spalte braucht eine eigene id")
            return
    reihe = [(s["id"], s["art"]) for s in spalten]
    formeln, alle_lesbar = {}, True
    for j, s in enumerate(spalten):
        if s["art"] != "rechnung":
            continue
        fehler = rechnung.pruefen_gegen(s["baum"], reihe) if s["baum"] is not None else [None]
        for f in fehler:
            if f is not None:  # None: Formel schon als Fehler gemeldet
                p.melden(f"{pfad}.spalten[{j}].formel", str(f))
        alle_lesbar = alle_lesbar and not fehler
        formeln[s["id"]] = s["baum"]
    if not alle_lesbar:
        return
    kreis = rechnung.zyklus(formeln, ids)
    if kreis:
        j = ids.index(kreis[0])
        p.melden(f"{pfad}.spalten[{j}].formel", "Rechnungen brauchen sich gegenseitig: " + " -> ".join(kreis)
                 + " (keine Rechnung darf sich selbst brauchen, auch nicht über einen Bereich)")
        return
    zelle = {sid: f"{rechnung.spaltenbuchstabe(k)}{MAX_ZEILEN + 20}" for k, sid in enumerate(ids)}.__getitem__
    for j, s in enumerate(spalten):
        if s["art"] == "rechnung":
            if len(rechnung.excel(s["baum"], zelle)) > rechnung.MAX_EXCEL:
                p.melden(f"{pfad}.spalten[{j}].formel", "wird in Excel zu lang, bitte vereinfachen "
                                                        "(z. B. einen Teil in eine eigene rechnung-Spalte)")


def _punkt(p: "_Pruefer", wert, pfad: str, max_laenge: int) -> dict | None:
    """Listenpunkt oder offene Frage: Text oder {text, quellen, kennzeichnung}. Ergebnis: immer das Objekt."""
    if isinstance(wert, dict):
        p.felder(wert, pfad, pflicht=("text",), optional=("quellen", "kennzeichnung"))
        return {"text": _z_text(p, wert.get("text", _FEHLT), f"{pfad}.text", max_laenge), **_beleg(p, wert, pfad)}
    if not isinstance(wert, str):
        p.melden(pfad, f"muss ein Text oder ein Objekt {{\"text\": ...}} sein, ist {_zeigen(wert)}")
        return None
    return {"text": _z_text(p, wert, pfad, max_laenge), "quellen": [], "kennzeichnung": None}


def _z_text(p: "_Pruefer", wert, pfad: str, max_laenge: int) -> str | None:
    """Text einer Zusammenfassung. Quellen gehören ins Feld quellen, nicht in den Text."""
    text = p.text(wert, pfad, max_laenge)
    if text and _QUELLE_IM_TEXT.search(text):
        p.melden(pfad, "Quellenangabe im Text, bitte ins Feld quellen verschieben "
                       "(z. B. [{\"art\": \"transkript\", \"stelle\": \"4\"}])")
    return text


def _beleg(p: "_Pruefer", d: dict, pfad: str) -> dict:
    kennzeichnung = d.get("kennzeichnung", _FEHLT)
    if kennzeichnung is _FEHLT:
        kennzeichnung = None
    elif kennzeichnung not in KENNZEICHNUNGEN:
        p.melden(f"{pfad}.kennzeichnung", f"muss {' oder '.join(_zeigen(k) for k in KENNZEICHNUNGEN)} sein, "
                                          f"ist {_zeigen(kennzeichnung)}{_aehnlich(kennzeichnung, KENNZEICHNUNGEN)}")
        kennzeichnung = None
    return {"quellen": _quellen(p, d, pfad), "kennzeichnung": kennzeichnung}


def _quellen(p: "_Pruefer", d: dict, pfad: str) -> list:
    if "quellen" not in d:
        return []
    quellen = []
    for i, q in enumerate(p.liste(d["quellen"], f"{pfad}.quellen", 1, MAX_QUELLEN) or []):
        qpfad = f"{pfad}.quellen[{i}]"
        if not isinstance(q, dict):
            p.melden(qpfad, f"muss ein Objekt {{\"art\": ..., \"stelle\": ...}} sein, ist {_zeigen(q)}")
            continue
        p.felder(q, qpfad, pflicht=("art", "stelle"))
        art = q.get("art", _FEHLT)
        if art is not _FEHLT and art not in QUELLENARTEN:
            p.melden(f"{qpfad}.art", f"muss einer von {', '.join(_zeigen(a) for a in QUELLENARTEN)} sein, "
                                     f"ist {_zeigen(art)}{_aehnlich(art, QUELLENARTEN)}")
            continue
        stelle = p.text(q.get("stelle", _FEHLT), f"{qpfad}.stelle", MAX_QUELLE_STELLE)
        if stelle and art in ("transkript", "folie") and not _SEITEN.match(stelle):
            wort = "Seiten" if art == "transkript" else "Foliennummern"
            p.melden(f"{qpfad}.stelle", f"nur {wort} wie \"4\", \"4-5\" oder \"4, 7\", ist {_zeigen(stelle)}")
            continue
        if art is not _FEHLT and stelle:
            quellen.append({"art": art, "stelle": stelle})
    return quellen


def _datum(p: "_Pruefer", wert, pfad: str) -> str | None:
    text = p.text(wert, pfad, 10)
    if text is None:
        return None
    treffer = _DATUM.match(text)
    if treffer:
        tag, monat, jahr = (int(x) for x in treffer.groups())
        try:
            datetime.date(jahr, monat, tag)
            return text
        except ValueError:
            pass
    p.melden(pfad, f"muss ein Datum wie \"20.10.2026\" sein (TT.MM.JJJJ), ist {_zeigen(text)}")
    return None


def _textteile(p: "_Pruefer", wert, pfad: str, max_laenge: int) -> list | None:
    """Ein Text oder eine Liste von Teilen {text, fett, farbe, unterstrichen}. Ergebnis: immer die Liste."""
    if isinstance(wert, str):
        text = p.text(wert, pfad, max_laenge)
        return [{"text": text, "fett": False, "farbe": None, "unterstrichen": False}] if text is not None else None
    if wert is _FEHLT:
        return None
    if not isinstance(wert, list):
        p.melden(pfad, f"muss ein Text oder eine Liste von Textteilen sein, ist {_zeigen(wert)}")
        return None
    teile = []
    for i, t in enumerate(p.liste(wert, pfad, 1, MAX_TEXTTEILE) or []):
        tpfad = f"{pfad}[{i}]"
        if not isinstance(t, dict):
            p.melden(tpfad, f"muss ein Objekt {{\"text\": ...}} sein, ist {_zeigen(t)}")
            continue
        p.felder(t, tpfad, pflicht=("text",), optional=("fett", "farbe", "unterstrichen"))
        teile.append({
            "text": p.text(t.get("text", _FEHLT), f"{tpfad}.text", max_laenge, leer_erlaubt=True),
            "fett": p.wahrheitswert(t["fett"], f"{tpfad}.fett") if "fett" in t else False,
            "farbe": _farbe(p, t["farbe"], f"{tpfad}.farbe") if "farbe" in t else None,
            "unterstrichen": p.wahrheitswert(t["unterstrichen"], f"{tpfad}.unterstrichen") if "unterstrichen" in t
            else False,
        })
    if sum(len(t["text"] or "") for t in teile) > max_laenge:
        p.melden(pfad, f"zu lang (zusammen höchstens {max_laenge} Zeichen)")
    elif teile and all(t["text"] is not None and not t["text"].strip() for t in teile):
        p.melden(pfad, "darf nicht leer sein (einzelne Teile wie \" \" sind als Trenner erlaubt)")
    return teile


def _farbe(p: "_Pruefer", wert, pfad: str) -> str | None:
    if wert is _FEHLT:
        return None
    if wert not in TEXTFARBEN:
        p.melden(pfad, f"muss einer von {', '.join(_zeigen(f) for f in TEXTFARBEN)} sein, ist {_zeigen(wert)}")
        return None
    return wert


def _icon(p: "_Pruefer", wert, pfad: str) -> str | None:
    if wert not in ICON_NAMEN:
        p.melden(pfad, f"kein Icon dieses Namens: {_zeigen(wert)}{_aehnlich(wert, ICON_NAMEN)}, "
                       f"erlaubt sind: {', '.join(ICON_NAMEN)}")
        return None
    return wert


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
