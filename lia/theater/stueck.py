"""Stücktext in nummerierte Einheiten zerlegen (ohne Claude, ohne Netz).

Grundlage ist die Textfassung der PDF (agentkit.textfassung, mit „--- Seite N“-Marken). Python entfernt Kopf- und
Fußzeilen der Ansichtssendung, erkennt Akte, Sprecher („NAME:“) und Regie („(...)“) und vergibt jeder Einheit eine
feste Nummer. Claude wählt später nur Nummern aus; Python übernimmt den Text wörtlich (Plan Jan 29.10.2026).

Seiten: `seite` ist die gedruckte Seitenzahl (die Lia im Textbuch sieht), `pdf_seite` die Seite der PDF.
Typen: "rede" (beginnt mit Sprecher), "regie" (beginnt mit Klammer), "text" (alles andere: Fortsetzung einer Rede
nach einer Regieanweisung oder erzählende Regie; Python kann beides nicht sicher trennen).
"""

import re
from dataclasses import asdict, dataclass

WOERTER_JE_MINUTE = 130  # Sprechtempo für die Schätzung der Sprechzeit (nur Text, ohne Spiel und Pausen)

# Zeilen der Ansichtssendung, die auf jeder Seite stehen
_FUSS = ("Probeexemplar für ",)
# Die Anmerkung steht in der Textfassung teils mitten in einer Zeile, mit wechselnden Umbrüchen
_ANMERKUNG = re.compile(r"Anmerkung: Was Sie gerade lesen ist eine Ansichtssendung.*?69469\s+Weinheim[ \t]*\n?",
                        re.DOTALL)
_SEITE = re.compile(r"^--- Seite (\d+)$")
_AKT = {"ERSTER AKT": 1, "ZWEITER AKT": 2, "DRITTER": 3}

# Sprecher im Stück: Schreibweisen im Text -> einheitlicher Name. Rollen im Stück im Stück bleiben eigene Namen,
# weil sie eine andere Ebene sind (Dotty spielt Mrs Clackett).
SPRECHER = {
    "DOTTY": "DOTTY", "GARRY": "GARRY", "BROOKE": "BROOKE", "FREDERICK": "FREDERICK", "FREDDIE": "FREDERICK",
    "BELINDA": "BELINDA", "SELSDON": "SELSDON", "LLOYD": "LLOYD", "POPPY": "POPPY", "TIM": "TIM",
    "ROGER": "ROGER", "VICKI": "VICKI", "PHILIP": "PHILIP", "FLAVIA": "FLAVIA", "EINBRECHER": "EINBRECHER",
    "SCHEICH": "SCHEICH", "MRS.CLACKETT": "MRS CLACKETT", "MRS.CLACKET": "MRS CLACKETT",
    "MRS CLACKETT": "MRS CLACKETT", "MRS.C.": "MRS CLACKETT", "MRS C.": "MRS CLACKETT", "MRS C": "MRS CLACKETT",
    "MRS.C": "MRS CLACKETT", "ALLE": "ALLE", "DIE ANDEREN": "DIE ANDEREN", "ANDERE": "DIE ANDEREN",
}
# Wer spielt welche Rolle im Stück im Stück (Personenverzeichnis S. 2)
ROLLE_VON = {"MRS CLACKETT": "DOTTY", "ROGER": "GARRY", "VICKI": "BROOKE", "PHILIP": "FREDERICK",
             "SCHEICH": "FREDERICK", "FLAVIA": "BELINDA", "EINBRECHER": "SELSDON"}
_SPRECHER = re.compile(r"^([A-Za-zÄÖÜäöü][A-Za-zÄÖÜäöü. ]{0,15}?)\s*:\s*(.*)$")
_SPRECHER_OHNE_DOPPELPUNKT = re.compile(r"^(Mrs Clackett)\s+(.+)$")  # einmal auf S. 4
# Regie ohne Klammern: nennt Figuren in Großbuchstaben (in Reden stehen Namen normal) oder beginnt typisch
_REGIE_OHNE_KLAMMER = re.compile(
    r"\b(DOTTY|GARRY|BROOKE|FREDERICK|BELINDA|SELSDON|LLOYD|POPPY|TIM|ROGER|VICKI|PHILIP|FLAVIA|EINBRECHER|"
    r"SCHEICH|MRS\.? ?CLACKETT)\b|^(Auftritt|Ab |Ab$|V[O0]RHANG)")


class StueckFehler(Exception):
    pass


@dataclass
class Einheit:
    nr: int
    akt: int
    seite: int  # gedruckte Seite
    pdf_seite: int
    typ: str  # rede, regie, text
    sprecher: str  # bei text: letzter Sprecher davor ("" wenn keiner)
    text: str

    @property
    def woerter(self) -> int:
        return len(self.text.split())


def _sprecher(zeile: str) -> tuple[str, str] | None:
    m = _SPRECHER.match(zeile) or _SPRECHER_OHNE_DOPPELPUNKT.match(zeile)
    if not m:
        return None
    name = " ".join(m.group(1).upper().split())
    name = SPRECHER.get(name) or SPRECHER.get(name.replace(" ", ""))
    return (name, m.group(2).strip()) if name else None


def _zeilen(text: str):
    """(pdf_seite, gedruckte Seite, Zeile) ohne Kopf-, Fuß- und Anmerkungszeilen."""
    pdf_seite, seite, erwarte_nummer = 0, 0, False
    for roh in _ANMERKUNG.sub("\n", text).splitlines():
        zeile = roh.strip()
        m = _SEITE.match(zeile)
        if m:
            pdf_seite, erwarte_nummer = int(m.group(1)), True
            continue
        if erwarte_nummer:
            erwarte_nummer = False
            if zeile.isdigit():
                seite = int(zeile)
                continue
        # einzelne Zahlen sind Reste von Seitenzahlen, die die Textfassung verschoben hat
        if not zeile or zeile.startswith(_FUSS) or zeile.isdigit():
            continue
        yield pdf_seite, seite, zeile


def _anhaengen(text: str, zeile: str) -> str:
    """Zeile anfügen; Trennstrich am Zeilenende vor Kleinbuchstaben wird entfernt (Auf-/treten)."""
    if text.endswith("-") and len(text) > 1 and text[-2].isalpha() and zeile[:1].islower():
        return text[:-1] + zeile
    return f"{text} {zeile}" if text else zeile


def zerlegen(text: str) -> list[Einheit]:
    """Einheiten ab dem ersten Akt. Fehlt ein Akt, ist das ein StueckFehler (falsche Datei?)."""
    einheiten: list[Einheit] = []
    akt, letzter = 0, ""
    for pdf_seite, seite, zeile in _zeilen(text):
        if zeile in _AKT and _AKT[zeile] == akt + 1:
            akt, letzter = _AKT[zeile], ""
            einheiten.append(Einheit(0, akt, seite, pdf_seite, "regie", "", zeile))
            continue
        if akt == 0:
            continue
        sp = _sprecher(zeile)
        aktuell = einheiten[-1]
        offen = aktuell.text.count("(") > aktuell.text.count(")")
        if sp:
            letzter = sp[0]
            einheiten.append(Einheit(0, akt, seite, pdf_seite, "rede", sp[0], sp[1]))
        elif not offen and (zeile.startswith("(") or (aktuell.typ != "regie" and _REGIE_OHNE_KLAMMER.search(zeile))):
            einheiten.append(Einheit(0, akt, seite, pdf_seite, "regie", letzter, zeile))
        elif aktuell.typ == "regie" and not offen and aktuell.text.endswith(")"):
            # nach einer geschlossenen Regieanweisung: Fortsetzung der Rede oder erzählende Regie
            einheiten.append(Einheit(0, akt, seite, pdf_seite, "text", letzter, zeile))
        else:
            aktuell.text = _anhaengen(aktuell.text, zeile)
    if akt != 3:
        raise StueckFehler(f"Nur {akt} von 3 Akten gefunden")
    for i, e in enumerate(einheiten, 1):
        e.nr = i
    return einheiten


def sprechminuten(einheiten: list[Einheit]) -> float:
    """Geschätzte Sprechzeit der Reden (ohne Regie), in Minuten."""
    return sum(e.woerter for e in einheiten if e.typ != "regie") / WOERTER_JE_MINUTE


def bereich(einheiten: list[Einheit], von: int, bis: int) -> list[Einheit]:
    """Einheiten von..bis (Nummern, beide eingeschlossen)."""
    return [e for e in einheiten if von <= e.nr <= bis]


def akt_grenzen(einheiten: list[Einheit]) -> dict[int, tuple[int, int]]:
    """Akt -> (erste Nummer, letzte Nummer)."""
    grenzen: dict[int, tuple[int, int]] = {}
    for e in einheiten:
        von, _ = grenzen.get(e.akt, (e.nr, e.nr))
        grenzen[e.akt] = (von, e.nr)
    return grenzen


def zeile(e: Einheit) -> str:
    """Eine Einheit als Zeile für Claude und für die Spielfassung."""
    if e.typ == "rede":
        return f"{e.sprecher}: {e.text}"
    return e.text


def nummeriert(einheiten: list[Einheit], max_zeichen: int = 40000) -> list[str]:
    """Text mit Nummern für Claude, in Teile von höchstens max_zeichen (für Read). Kopf je Seite und Akt."""
    teile, aktuell, seite, akt = [], [], None, None
    for e in einheiten:
        kopf = []
        if e.akt != akt:
            akt = e.akt
            kopf.append(f"=== AKT {akt} ===")
        if e.seite != seite:
            seite = e.seite
            kopf.append(f"--- S. {seite}")
        z = "\n".join(kopf + [f"[{e.nr}] {zeile(e)}"])
        if aktuell and sum(len(t) + 1 for t in aktuell) + len(z) > max_zeichen:
            teile.append("\n".join(aktuell))
            aktuell = [f"--- S. {seite} (Fortsetzung)"] if not kopf else []
        aktuell.append(z)
    if aktuell:
        teile.append("\n".join(aktuell))
    return teile


def als_dicts(einheiten: list[Einheit]) -> list[dict]:
    return [asdict(e) for e in einheiten]


def aus_dicts(daten: list[dict]) -> list[Einheit]:
    return [Einheit(**d) for d in daten]
