"""Gelernte Regeln lesen, vorschlagen und (nach Freigabe) eintragen.

Allgemeine Regeln: shared/regeln.md, Abschnitt "## Regeln".
Agentenspezifische Regeln: <agent>/STATUS.md, Abschnitt "## Gelernte Regeln".
Format: eine Regel pro Zeile, "- TT.MM.JJJJ: Regel (Anlass: ...)".

Ablauf (CLAUDE.md, "Lernen nur nach Bestätigung"):
1. Agent ruft regel_vorschlagen() auf -> Entwurf vom Typ "regel" in der Freigabe.
2. Jan gibt frei (oder lehnt ab).
3. Erst dann schreibt regel_eintragen() die Regel in die Datei.

Aus Feedback (CLAUDE.md, "Lernen aus Feedback"): agentkit.feedback schreibt Regeln und Notizen ohne
Freigabe mit zeile_eintragen(); jede Zeile endet mit "(Feedback <id>)". Jans Stopp entfernt sie mit
zeilen_entfernen(). Bestehende Zeilen werden dabei nie geändert.
"""

from datetime import date
from pathlib import Path

from . import freigabe
from .config import SHARED_DIR

ALLGEMEIN_DATEI = SHARED_DIR / "regeln.md"
ALLGEMEIN_ABSCHNITT = "## Regeln"
AGENT_ABSCHNITT = "## Gelernte Regeln"
PLATZHALTER = "- (noch keine)"


class RegelFehler(Exception):
    pass


def _abschnitt_grenzen(zeilen: list[str], ueberschrift: str) -> tuple[int, int]:
    """Index der Überschrift und Index der ersten Zeile nach dem Abschnitt."""
    try:
        start = next(i for i, z in enumerate(zeilen) if z.strip() == ueberschrift)
    except StopIteration:
        raise RegelFehler(f"Abschnitt '{ueberschrift}' nicht gefunden") from None
    ende = next(
        (i for i in range(start + 1, len(zeilen)) if zeilen[i].startswith("## ")),
        len(zeilen),
    )
    return start, ende


def _lies_regeln(pfad: Path, ueberschrift: str) -> list[str]:
    if not pfad.exists():
        return []
    zeilen = pfad.read_text(encoding="utf-8").splitlines()
    start, ende = _abschnitt_grenzen(zeilen, ueberschrift)
    return [
        z.strip()[2:]
        for z in zeilen[start + 1 : ende]
        if z.strip().startswith("- ") and z.strip() != PLATZHALTER
    ]


def _ziel(agent_dir: Path | None) -> tuple[Path, str]:
    if agent_dir is None:
        return ALLGEMEIN_DATEI, ALLGEMEIN_ABSCHNITT
    return Path(agent_dir) / "STATUS.md", AGENT_ABSCHNITT


def allgemeine_regeln() -> list[str]:
    return _lies_regeln(ALLGEMEIN_DATEI, ALLGEMEIN_ABSCHNITT)


def agent_regeln(agent_dir: Path) -> list[str]:
    return _lies_regeln(Path(agent_dir) / "STATUS.md", AGENT_ABSCHNITT)


def regeln_als_text(agent_dir: Path) -> str:
    """Alle Regeln als Textblock, z. B. zum Einfügen in den Prompt für claude -p."""
    teile = []
    for titel, regeln in (
        ("Allgemeine Regeln", allgemeine_regeln()),
        ("Regeln für diesen Agenten", agent_regeln(agent_dir)),
    ):
        teile.append(f"{titel}:\n" + ("\n".join(f"- {r}" for r in regeln) or "- (keine)"))
    return "\n\n".join(teile)


def regel_vorschlagen(
    agent: str,
    regel: str,
    anlass: str,
    allgemein: bool = False,
    basis: Path | None = None,
) -> str:
    """Legt einen Regel-Vorschlag in die Freigabe. Gibt die Entwurfs-ID zurück."""
    if not regel.strip() or "\n" in regel:
        raise RegelFehler("Eine Regel muss genau eine nicht leere Zeile sein")
    ziel = "shared/regeln.md" if allgemein else f"{agent}/STATUS.md"
    return freigabe.neuer_entwurf(
        agent,
        titel=f"Neue Regel für {ziel}",
        inhalt=f"{regel}\n\nAnlass: {anlass}",
        typ="regel",
        daten={"regel": regel.strip(), "anlass": anlass.strip(), "allgemein": allgemein},
        basis=basis,
    )


def regel_eintragen(entwurf: dict, agent_dir: Path | None = None) -> bool:
    """Schreibt eine freigegebene Regel in ihre Datei.

    agent_dir ist nur für agentenspezifische Regeln nötig. Gibt False zurück,
    wenn die Regel schon drinsteht (doppeltes Eintragen passiert also nicht).
    """
    if entwurf.get("typ") != "regel":
        raise RegelFehler("Entwurf ist kein Regel-Vorschlag")
    if entwurf.get("status") != "freigegeben":
        raise RegelFehler("Regel ist nicht freigegeben")
    daten = entwurf["daten"]
    if not daten["allgemein"] and agent_dir is None:
        raise RegelFehler("Für eine Agenten-Regel wird agent_dir gebraucht")
    pfad, ueberschrift = _ziel(None if daten["allgemein"] else agent_dir)

    regel = daten["regel"]
    if any(r.split(": ", 1)[-1].startswith(regel) for r in _lies_regeln(pfad, ueberschrift)):
        return False
    _einfuegen(pfad, ueberschrift, f"- {date.today():%d.%m.%Y}: {regel} (Anlass: {daten['anlass']})")
    return True


def _einfuegen(pfad: Path, ueberschrift: str, neue_zeile: str, anlegen: bool = False) -> None:
    """Zeile ans Ende der Liste im Abschnitt; anlegen=True legt einen fehlenden Abschnitt am Dateiende an."""
    zeilen = pfad.read_text(encoding="utf-8").splitlines()
    if anlegen and not any(z.strip() == ueberschrift for z in zeilen):
        zeilen += ["", ueberschrift]
    start, ende = _abschnitt_grenzen(zeilen, ueberschrift)
    abschnitt = [z for z in zeilen[start + 1 : ende] if z.strip() != PLATZHALTER]
    # nach dem letzten Listenpunkt einfügen, Leerzeilen am Abschnittsende behalten
    letzte = max((i for i, z in enumerate(abschnitt) if z.strip().startswith("- ")), default=-1)
    if letzte == -1:
        while abschnitt and not abschnitt[0].strip() and any(z.strip() for z in abschnitt):
            abschnitt.pop(0)
    abschnitt.insert(letzte + 1, neue_zeile)
    zeilen[start + 1 : ende] = abschnitt
    pfad.write_text("\n".join(zeilen) + "\n", encoding="utf-8")


def herkunft(feedback_id: str) -> str:
    return f"(Feedback {feedback_id})"


def zeile_eintragen(pfad: Path, ueberschrift: str, text: str, feedback_id: str, heute: date | None = None) -> str:
    """Regel oder Notiz aus Feedback eintragen, ohne Freigabe. Gibt die geschriebene Zeile zurück.

    text muss genau eine nicht leere Zeile sein. Fehlt der Abschnitt, wird er am Ende angelegt.
    """
    text = text.strip()
    if not text or "\n" in text:
        raise RegelFehler("Eine Regel muss genau eine nicht leere Zeile sein")
    if not Path(pfad).exists():
        raise RegelFehler(f"Datei fehlt: {pfad}")
    zeile = f"- {heute or date.today():%d.%m.%Y}: {text} {herkunft(feedback_id)}"
    _einfuegen(Path(pfad), ueberschrift, zeile, anlegen=True)
    return zeile


def zeilen_entfernen(pfad: Path, feedback_id: str) -> int:
    """Entfernt alle Zeilen, die aus diesem Feedback stammen (Jans Stopp). Gibt ihre Anzahl zurück."""
    pfad = Path(pfad)
    if not pfad.exists():
        return 0
    zeilen = pfad.read_text(encoding="utf-8").splitlines()
    marke = herkunft(feedback_id)
    bleiben = [z for z in zeilen if not (z.lstrip().startswith("- ") and z.rstrip().endswith(marke))]
    if len(bleiben) != len(zeilen):
        pfad.write_text("\n".join(bleiben) + "\n", encoding="utf-8")
    return len(zeilen) - len(bleiben)
