"""Normen-Ablage: Jan legt Normen aus Nautos als PDF nach data/normen/ (Unterordner erlaubt).

aufbereiten() schreibt zu jeder Datei die Textfassung <datei>.txt (mit "--- Seite N", wie beim
Kursmaterial) und das Verzeichnis data/normen/uebersicht.md: Kennung und Ausgabe (von der ersten
Seite), Seitenzahl, Datei. Lässt sich ein PDF nicht lesen (Scan, Schutz), steht das im Verzeichnis.
Normen bleiben in data/ (nicht im Repo) und gehen nie an andere weiter (Lizenz der HNEE).

Ohne Netz testbar: kennung(), ausgabe(), eintrag(), verzeichnis().
"""

import re
from pathlib import Path

import kurse

ORDNER = Path(__file__).resolve().parent / "data" / "normen"
VERZEICHNIS = "uebersicht.md"
FORMATE = (".pdf", ".docx", ".xlsx")
KENNUNG = re.compile(
    r"\b(DIN(?:\s+(?:EN\s+ISO|EN|ISO|SPEC|CEN/TS|CEN/TR|V))*|ÖNORM(?:\s+(?:EN|B))?|VDI|SIA)\s+"
    r"(\d{1,5}(?:\s\d{3})?(?:-\d{1,3}){0,2})")
MONATE = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
          "November", "Dezember")
AUSGABE_WORT = re.compile(r"\b(" + "|".join(MONATE) + r")\s+((?:19|20)\d{2})(?!\d)")  # Nautos: "Juni\t2019DEUTSCHE"
AUSGABE = re.compile(r"\b((?:19|20)\d{2}-(?:0[1-9]|1[0-2]))\b(?!-\d)")  # nicht JJJJ-MM-TT (Lizenzvermerk)
SEITE = re.compile(r"^--- Seite (\d+)$", re.M)
NAUTOS_NAME = re.compile(r"^(.+?)_((?:19|20)\d{2}-\d{2})-\d{2}_[A-Z]{2}_\d+$")  # DIN EN 350_2016-12-00_DE_2414889
UNLESBAR = ("(Kein Text gefunden", "(Textfassung fehlgeschlagen")


def _erste_seite(text: str) -> str:
    teile = SEITE.split(text)  # ["", "1", text1, "2", text2, ...]
    return teile[2] if len(teile) > 2 else text


def kennung(text: str) -> str | None:
    """Erste Normkennung auf der ersten Seite, z. B. "DIN EN 350" oder "DIN 68800-1"."""
    m = KENNUNG.search(_erste_seite(text))
    return f"{' '.join(m.group(1).split())} {m.group(2).replace(' ', '')}" if m else None


def ausgabe(text: str) -> str | None:
    """Ausgabe (JJJJ-MM) von der ersten Seite. DIN-Deckblätter schreiben "Dezember 2016", das zählt zuerst
    (ein "JJJJ-MM" davor steht oft bei "Ersatz für ..." und meint die alte Ausgabe)."""
    seite = _erste_seite(text)
    m = AUSGABE_WORT.search(seite)
    if m:
        return f"{m.group(2)}-{MONATE.index(m.group(1)) + 1:02d}"
    m = AUSGABE.search(seite)
    return m.group(1) if m else None


def aus_dateiname(datei: str) -> tuple[str, str] | None:
    """Kennung und Ausgabe aus dem Nautos-Dateinamen, z. B. "DIN EN 1995-1-1-NA_2013-08-00_DE_2025142.pdf"
    -> ("DIN EN 1995-1-1/NA", "2013-08"). Verlässlicher als das Deckblatt (NA, Änderungen, Berichtigungen)."""
    m = NAUTOS_NAME.match(Path(datei).stem)
    if not m:
        return None
    name = " ".join(m.group(1).replace("_", " ").split())
    while (z := re.sub(r"-(NA|A\d+)((?:/(?:NA|A\d+))*)$", r"/\1\2", name)) != name:  # -NA-A1 -> /NA/A1
        name = z
    return name, m.group(2)


def eintrag(datei: str, text: str | None) -> dict:
    lesbar = text is not None and not text.startswith(UNLESBAR)
    name = aus_dateiname(datei)
    if name:
        kenn, ausg = name
    elif lesbar:
        kenn, ausg = kennung(text), ausgabe(text)
    else:
        kenn, ausg = None, None
    return {"datei": datei, "kennung": kenn, "ausgabe": ausg,
            "seiten": len(SEITE.findall(text)) if lesbar else 0, "lesbar": lesbar}


def verzeichnis(eintraege: list[dict]) -> str:
    zeilen = ["# Normen (aus Nautos, nur für Jan)", "",
              "Suche mit Grep in den .txt-Dateien, dann gezielt Seiten im PDF lesen.",
              "Kennung und Ausgabe sind von der ersten Seite gelesen, im Zweifel dort prüfen.", ""]
    for e in sorted(eintraege, key=lambda e: (e["kennung"] or "~", e["datei"])):
        if not e["lesbar"]:
            zeilen.append(f"- {e['kennung'] or e['datei']}: KEIN TEXT (Scan oder geschützt), PDF mit Read ansehen: "
                          f"{e['datei']}")
            continue
        teile = [e["kennung"] or "Kennung unbekannt", f"Ausgabe {e['ausgabe']}" if e["ausgabe"] else None,
                 f"{e['seiten']} Seiten" if e["seiten"] else None]
        zeilen.append(f"- {', '.join(t for t in teile if t)}: {e['datei']} (Textfassung {e['datei']}.txt)")
    if not eintraege:
        zeilen.append("(noch keine Normen abgelegt)")
    return "\n".join(zeilen) + "\n"


def aufbereiten(ordner: Path = ORDNER, textfassung=kurse.textfassung) -> list[dict]:
    """Textfassungen für neue Dateien, Verzeichnis neu. Gibt die Einträge der neu aufbereiteten Dateien zurück."""
    return ablage_aufbereiten(ordner, eintrag, verzeichnis, textfassung)


def ablage_aufbereiten(ordner: Path, eintrag, verzeichnis, textfassung=kurse.textfassung) -> list[dict]:
    """Gemeinsam für Normen und Literatur: eintrag(datei, text) -> dict, verzeichnis(eintraege) -> str."""
    if not ordner.exists():
        return []
    eintraege, neu = [], []
    for pfad in sorted(ordner.rglob("*")):
        if not pfad.is_file() or pfad.suffix.lower() not in FORMATE or pfad.name.startswith("."):
            continue
        txt = pfad.with_name(pfad.name + ".txt")
        war_da = txt.exists()
        textfassung(pfad, erneuern=False)
        e = eintrag(pfad.relative_to(ordner).as_posix(), txt.read_text(errors="replace") if txt.exists() else None)
        eintraege.append(e)
        if not war_da:
            neu.append(e)
    (ordner / VERZEICHNIS).write_text(verzeichnis(eintraege), encoding="utf-8")
    return neu


def beschreiben(e: dict) -> str:
    if not e["lesbar"]:
        return f"- {e['kennung'] or e['datei']}: kein Text lesbar (Scan oder geschützt)"
    return f"- {e['kennung'] or 'Kennung unbekannt'}" + (f" ({e['ausgabe']})" if e["ausgabe"] else "") + \
        f", {e['seiten']} Seiten: {e['datei']}"
