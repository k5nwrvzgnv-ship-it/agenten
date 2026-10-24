"""Literatur-Ablage: Bücher, Handbücher und Merkblätter als PDF in data/literatur/<herkunft>/.

aufbereiten() schreibt wie bei den Normen zu jeder Datei die Textfassung <datei>.txt (mit "--- Seite N")
und das Verzeichnis data/literatur/uebersicht.md: Herkunft (Unterordner), Titel aus dem Dateinamen,
Seitenzahl, Datei. Unlesbare PDFs (Scan, Schutz) stehen als KEIN TEXT im Verzeichnis.
Literatur bleibt in data/ (nicht im Repo), lizenzierte Werke gehen nicht an andere weiter.

Ohne Netz testbar: titel(), eintrag(), verzeichnis().
"""

import re
from pathlib import Path

import kurse
import normen

ORDNER = Path(__file__).resolve().parent / "data" / "literatur"
VERZEICHNIS = "uebersicht.md"


def titel(datei: str) -> str:
    """Lesbarer Titel aus dem Dateinamen: "R05_T02_F02_Holzschutz--Bauliche-Massnahmen_2023-01.pdf"
    -> "R05 T02 F02 Holzschutz – Bauliche Massnahmen 2023-01"."""
    stamm = Path(datei).stem.replace("--", " – ")
    stamm = re.sub(r"(?<=[A-Za-zÄÖÜäöüß])-(?=[A-Za-zÄÖÜäöüß])", " ", stamm)
    return " ".join(stamm.replace("_", " ").split())


def eintrag(datei: str, text: str | None) -> dict:
    lesbar = text is not None and not text.startswith(normen.UNLESBAR)
    teile = Path(datei).parts
    return {"datei": datei, "herkunft": teile[0] if len(teile) > 1 else "", "titel": titel(datei),
            "seiten": len(normen.SEITE.findall(text)) if lesbar else 0, "lesbar": lesbar}


def verzeichnis(eintraege: list[dict]) -> str:
    zeilen = ["# Literatur (Bücher, Handbücher, Merkblätter)", "",
              "Suche mit Grep in den .txt-Dateien, dann gezielt Seiten im PDF lesen. Fehlen in der Textfassung",
              "Leerzeichen, nach einzelnen Fachwörtern suchen statt nach Wortfolgen.", ""]
    for e in sorted(eintraege, key=lambda e: (e["herkunft"], e["datei"])):
        name = f"{e['herkunft']}: {e['titel']}" if e["herkunft"] else e["titel"]
        if not e["lesbar"]:
            zeilen.append(f"- {name}: KEIN TEXT (Scan oder geschützt), PDF mit Read ansehen: {e['datei']}")
        else:
            seiten = f", {e['seiten']} Seiten" if e["seiten"] else ""
            zeilen.append(f"- {name}{seiten}: {e['datei']} (Textfassung {e['datei']}.txt)")
    if not eintraege:
        zeilen.append("(noch keine Literatur abgelegt)")
    return "\n".join(zeilen) + "\n"


def aufbereiten(ordner: Path = ORDNER, textfassung=kurse.textfassung) -> list[dict]:
    """Textfassungen für neue Dateien, Verzeichnis neu. Gibt die Einträge der neu aufbereiteten Dateien zurück."""
    return normen.ablage_aufbereiten(ordner, eintrag, verzeichnis, textfassung)


def beschreiben(e: dict) -> str:
    if not e["lesbar"]:
        return f"- {e['titel']}: kein Text lesbar (Scan oder geschützt)"
    return f"- {e['titel']}, {e['seiten']} Seiten: {e['datei']}"
