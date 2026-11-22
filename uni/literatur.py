"""Literatur-Ablage: Bücher, Handbücher und Merkblätter als PDF in data/literatur/<herkunft>/.

aufbereiten() schreibt wie bei den Normen zu jeder Datei die Textfassung <datei>.txt (mit "--- Seite N")
und das Verzeichnis data/literatur/uebersicht.md: Herkunft (Unterordner), Titel aus dem Dateinamen,
Seitenzahl, Datei. Unlesbare PDFs (Scan, Schutz) stehen als KEIN TEXT im Verzeichnis.
Woher eine heruntergeladene Datei stammt, steht in data/literatur/quellen.json
({"<datei relativ>": {"quelle": "<Adresse>", "abgerufen": "TT.MM.JJJJ", "hinweis": "..."}}); das Verzeichnis
zeigt es unter dem Eintrag als Zeile "Quelle: ...". Ohne Datei oder bei kaputtem JSON: ohne Quellenzeilen.
Literatur bleibt in data/ (nicht im Repo), lizenzierte Werke gehen nicht an andere weiter.

Ohne Netz testbar: titel(), eintrag(), verzeichnis().
"""

import json
import re
from pathlib import Path

import kurse
import normen

ORDNER = Path(__file__).resolve().parent / "data" / "literatur"
VERZEICHNIS = "uebersicht.md"
QUELLEN = "quellen.json"


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


def quellen_lesen(ordner: Path) -> dict[str, dict]:
    """Herkunftsangaben aus quellen.json; fehlt die Datei oder ist sie kaputt: {}."""
    try:
        daten = json.loads((ordner / QUELLEN).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {k: v for k, v in daten.items() if isinstance(k, str) and isinstance(v, dict)} \
        if isinstance(daten, dict) else {}


def quellenzeile(q: dict) -> str:
    """'  Quelle: <adresse> (abgerufen <datum>; <hinweis>)' oder '' ohne Adresse."""
    adresse = str(q.get("quelle") or "").strip()
    if not adresse:
        return ""
    zusatz = "; ".join(x for x in (f"abgerufen {q['abgerufen']}" if q.get("abgerufen") else "",
                                    str(q.get("hinweis") or "").strip()) if x)
    return f"  Quelle: {adresse}" + (f" ({zusatz})" if zusatz else "")


def verzeichnis(eintraege: list[dict], quellen: dict[str, dict] | None = None) -> str:
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
        if zeile := quellenzeile((quellen or {}).get(e["datei"], {})):
            zeilen.append(zeile)
    if not eintraege:
        zeilen.append("(noch keine Literatur abgelegt)")
    return "\n".join(zeilen) + "\n"


def aufbereiten(ordner: Path = ORDNER, textfassung=kurse.textfassung) -> list[dict]:
    """Textfassungen für neue Dateien, Verzeichnis neu. Gibt die Einträge der neu aufbereiteten Dateien zurück."""
    quellen = quellen_lesen(ordner)
    return normen.ablage_aufbereiten(ordner, eintrag, lambda es: verzeichnis(es, quellen), textfassung)


def beschreiben(e: dict) -> str:
    if not e["lesbar"]:
        return f"- {e['titel']}: kein Text lesbar (Scan oder geschützt)"
    return f"- {e['titel']}, {e['seiten']} Seiten: {e['datei']}"
