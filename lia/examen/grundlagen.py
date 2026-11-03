"""Grundlagen der Examensreihe: Rubrik, RLP-Wortlaut und Prüfungsangaben laden und prüfen.

Schritt 1 des Plans (Jan 25.10.2026). Die Dateien liegen im Repo (keine Schülerdaten) und sind die feste
Grundlage für alle späteren Läufe (Skizzen, Prüfer). Aufruf `.venv/bin/python grundlagen.py` prüft alles:
Rubrik vollständig, jede RLP-Stelle wörtlich auf ihrer Seite im PDF, offene Angaben in examen.toml, die Reihe.
Die Reihe kommt aus lia/instanz/reihen.toml über agentkit.struktur (Strukturplan, Jan 03.11.2026, F14): die eine
Reihe mit einer Stunde mit Marke „Prüfung“. Deren Nummer ist die Stelle der Prüfungsstunde in der Reihe.
"""

import sys
import tomllib
from pathlib import Path

from agentkit import struktur, wortlaut

HIER = Path(__file__).resolve().parent
RUBRIK = HIER / "rubrik.toml"
RLP_AUSZUG = HIER / "rlp_auszug.toml"
EXAMEN = HIER / "examen.toml"
RLP_PDF = HIER / "data" / "vorgaben" / "RLP_Ethik_Sek_I.pdf"

KRITERIUM_FELDER = ("id", "name", "frage", "gut", "quelle")
STELLE_PFLICHT = ("id", "seite", "abschnitt", "text")
STELLE_FREI = ("stufe", "hinweis")


class GrundlagenFehler(Exception):
    """Eine Grundlagen-Datei ist kaputt oder unvollständig. Der Text ist für Jan."""


class ReiheOffen(GrundlagenFehler):
    """Keine oder mehr als eine Reihe bzw. Prüfungsstunde. Der Text sagt Jan, was Lia eintragen muss."""


def _toml(pfad: Path) -> dict:
    try:
        return tomllib.loads(pfad.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise GrundlagenFehler(f"{pfad.name} fehlt") from None
    except tomllib.TOMLDecodeError as e:
        raise GrundlagenFehler(f"{pfad.name} ist kein gültiges TOML: {e}") from None


def _eindeutige_ids(eintraege: list[dict], name: str) -> None:
    ids = [e["id"] for e in eintraege]
    doppelt = sorted({i for i in ids if ids.count(i) > 1})
    if doppelt:
        raise GrundlagenFehler(f"{name}: doppelte id {doppelt}")


def rubrik_laden(pfad: Path = RUBRIK) -> dict:
    """Rubrik mit [stufen] (liste, mindestens) und [[kriterium]], geprüft."""
    daten = _toml(pfad)
    stufen = daten.get("stufen", {})
    liste = stufen.get("liste")
    if not (isinstance(liste, list) and len(liste) >= 2 and all(isinstance(s, str) and s for s in liste)):
        raise GrundlagenFehler(f"{pfad.name}: [stufen] liste braucht mindestens zwei Stufen")
    if stufen.get("mindestens") not in liste:
        raise GrundlagenFehler(f"{pfad.name}: [stufen] mindestens muss eine der Stufen sein")
    kriterien = daten.get("kriterium")
    if not isinstance(kriterien, list) or not kriterien:
        raise GrundlagenFehler(f"{pfad.name}: keine Kriterien ([[kriterium]])")
    for nr, k in enumerate(kriterien, 1):
        fehlend = [f for f in KRITERIUM_FELDER if not str(k.get(f, "")).strip()]
        if fehlend:
            raise GrundlagenFehler(f"{pfad.name}, Kriterium {nr}: {', '.join(fehlend)} fehlt")
        unbekannt = set(k) - set(KRITERIUM_FELDER)
        if unbekannt:
            raise GrundlagenFehler(f"{pfad.name}, Kriterium {nr}: unbekannte Felder {sorted(unbekannt)}")
    _eindeutige_ids(kriterien, pfad.name)
    return daten


def auszug_laden(pfad: Path = RLP_AUSZUG) -> list[dict]:
    """RLP-Stellen ([[stelle]]), geprüft auf Felder, nicht auf Wortlaut (das macht auszug_pruefen)."""
    stellen = _toml(pfad).get("stelle")
    if not isinstance(stellen, list) or not stellen:
        raise GrundlagenFehler(f"{pfad.name}: keine Stellen ([[stelle]])")
    for nr, s in enumerate(stellen, 1):
        fehlend = [f for f in STELLE_PFLICHT if not str(s.get(f, "")).strip()]
        if fehlend:
            raise GrundlagenFehler(f"{pfad.name}, Stelle {nr}: {', '.join(fehlend)} fehlt")
        if not isinstance(s["seite"], int):
            raise GrundlagenFehler(f"{pfad.name}, Stelle {nr}: seite muss eine Zahl sein")
        unbekannt = set(s) - set(STELLE_PFLICHT) - set(STELLE_FREI)
        if unbekannt:
            raise GrundlagenFehler(f"{pfad.name}, Stelle {nr}: unbekannte Felder {sorted(unbekannt)}")
    _eindeutige_ids(stellen, pfad.name)
    return stellen


def auszug_pruefen(stellen: list[dict], textfassung: str) -> list[str]:
    """Fehlerliste: Stellen, die nicht wörtlich auf ihrer Seite stehen. Leer = alles belegt."""
    seiten = wortlaut.seiten(textfassung)
    fehler = []
    for s in stellen:
        if wortlaut.steht_in(s["text"], seiten.get(s["seite"], "")):
            continue
        anderswo = [nr for nr, t in seiten.items() if wortlaut.steht_in(s["text"], t)]
        if anderswo:
            fehler.append(f"{s['id']}: steht nicht auf Seite {s['seite']}, sondern auf {anderswo}")
        else:
            fehler.append(f"{s['id']}: nicht wörtlich im RLP gefunden")
    return fehler


def pruefungsreihe(s: struktur.Struktur) -> tuple[dict, dict]:
    """(Reihe, Prüfungsstunde) aus der aufgelösten Struktur. Nicht genau eine: ReiheOffen."""
    reihen = s.pruefungsreihen()
    if not reihen:
        raise ReiheOffen(f"Keine Reihe hat eine Stunde mit Marke „{struktur.PRUEFUNG}“. Lia muss die Stunden der "
                         "Reihe mit Prüfungsstunde eintragen und die Prüfungsstunde markieren.")
    if len(reihen) > 1:
        raise ReiheOffen(f"{len(reihen)} Reihen haben eine Stunde mit Marke „{struktur.PRUEFUNG}“ "
                         f"({', '.join(r['id'] for r in reihen)}), erwartet genau eine. Lia muss die Marke in den "
                         "anderen Reihen entfernen.")
    try:
        return reihen[0], s.pruefungsstunde(reihen[0]["id"])
    except struktur.StrukturFehler as e:
        raise ReiheOffen(f"{e}. Lia muss die Marke so setzen, dass genau eine Stunde die Prüfungsstunde ist.") from None


def offene_angaben(daten: dict, vorne: str = "") -> list[str]:
    """Schlüssel (mit Punkt verbunden), deren Wert noch leer ist: Angaben, die Lia nachliefern muss."""
    offen = []
    for schluessel, wert in daten.items():
        name = f"{vorne}{schluessel}"
        if isinstance(wert, dict):
            offen += offene_angaben(wert, f"{name}.")
        elif wert == "" or wert == []:
            offen.append(name)
    return offen


def main() -> int:
    from agentkit import textfassung

    fehler = []
    try:
        rubrik = rubrik_laden()
        print(f"ok      Rubrik: {len(rubrik['kriterium'])} Kriterien, mindestens „{rubrik['stufen']['mindestens']}“")
    except GrundlagenFehler as e:
        fehler.append(str(e))
    try:
        stellen = auszug_laden()
        if not RLP_PDF.exists():
            fehler.append(f"RLP-PDF fehlt: {RLP_PDF}")
        else:
            falsch = auszug_pruefen(stellen, textfassung.als_text(RLP_PDF) or "")
            fehler += falsch
            print(f"{'ok     ' if not falsch else 'FEHLER '} RLP: {len(stellen) - len(falsch)} von {len(stellen)} "
                  "Stellen wörtlich belegt")
    except GrundlagenFehler as e:
        fehler.append(str(e))
    try:
        offen = offene_angaben(_toml(EXAMEN))
        print("ok      examen.toml" + (f", noch offen: {', '.join(offen)}" if offen else ", vollständig"))
    except GrundlagenFehler as e:
        fehler.append(str(e))
    try:
        reihe, stunde = pruefungsreihe(struktur.laden())
        print(f"ok      Reihe {reihe['id']}: Prüfungsstunde ist Stunde {stunde['nr']} von {len(reihe['stunden'])}")
    except ReiheOffen as e:
        print(f"offen   Reihe: {e}")
    except struktur.StrukturFehler as e:
        fehler.append(str(e))
    for f in fehler:
        print(f"FEHLER  {f}")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
