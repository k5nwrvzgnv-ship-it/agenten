"""Lernblätter für Jan: Claude beschreibt, Python baut docx und PDF (shared/renderer, Art "zusammenfassung").

Claude schreibt ein Lernblatt als data/lernblaetter/<auftrag>/blatt_<n>.json im Renderer-Format. <auftrag> ist
der erste Auftrag einer Antwortkette: Will Jan per Antwort etwas geändert haben, ändert Claude dieselbe Datei.
Nach jedem Lauf baut agent.py mit bauen_neue() jedes neue oder geänderte Blatt nach
data/lernblaetter/<auftrag>/blatt_<n>/<Titel>.docx und .pdf (LibreOffice, ohne Bildvorschau, also ohne pypdfium2).
<auftrag>/.gebaut.json merkt die Prüfsumme je gebauter Beschreibung, ein unverändertes Blatt kommt nicht noch
einmal. Ungültige Beschreibungen gehen mit den Fehlern des Renderers an Claude zurück (agent.py).
Das Format für Claude legt format_ablegen() als data/lernblaetter/FORMAT.md ab (Abschnitte Allgemein und
Zusammenfassung aus shared/renderer/FORMAT.md), damit es nicht in jedem Prompt steht.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import renderer
from renderer import pruefung, vorschau

import kurse
import weitergabe

ORDNER = Path("data") / "lernblaetter"
STAND = ".gebaut.json"
MUSTER = re.compile(r"^blatt_\d{1,2}\.json$")
ART = "zusammenfassung"


@dataclass
class Bericht:
    pdfs: list[Path] = field(default_factory=list)  # neu gebaut, gehen an Jan
    ungueltig: dict[str, str] = field(default_factory=dict)  # Dateiname -> Fehler für Claude
    fehler: list[str] = field(default_factory=list)  # Fehler des Agenten (LibreOffice, Profil), nicht Claudes


def ordner(hier: Path, schluessel: str) -> Path:
    return hier / ORDNER / schluessel


def format_ablegen(format_md: str, ziel: Path) -> None:
    """Formatteil für Claude nach `ziel` schreiben (nur wenn er sich geändert hat)."""
    text = "\n\n".join(weitergabe.format_abschnitt(format_md, t) for t in ("## Allgemein", "## Zusammenfassung"))
    text = "# Format für Lernblätter (Auszug aus shared/renderer/FORMAT.md)\n\n" + text + "\n"
    if not ziel.exists() or ziel.read_text() != text:
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(text)


def dateiname(titel: str) -> str:
    """Name der Datei, die Jan in Telegram sieht: "Holzschutz: Grundlagen" -> "Holzschutz - Grundlagen"."""
    return kurse.sicherer_name(re.sub(r"\s*:\s*", " - ", titel))


def _fehler_beschreibung(text: str) -> list[str]:
    fehler = pruefung.pruefen(text)
    if not fehler:
        art = json.loads(text).get("art")
        if art != ART:
            fehler = [f'art: Lernblätter sind "{ART}", ist {art!r}']
    return fehler


def bauen_neue(blattordner: Path, profil: dict, bauen=renderer.bauen, als_pdf=vorschau.als_pdf) -> Bericht:
    """Baut jedes neue oder geänderte blatt_<n>.json in `blattordner`, gibt die PDFs und alle Fehler zurück."""
    bericht = Bericht()
    if not blattordner.is_dir():
        return bericht
    stand_datei = blattordner / STAND
    stand = json.loads(stand_datei.read_text()) if stand_datei.exists() else {}
    for datei in sorted(p for p in blattordner.iterdir() if MUSTER.match(p.name) and p.is_file()):
        roh = datei.read_bytes()
        summe = hashlib.sha256(roh).hexdigest()
        if stand.get(datei.name) == summe:
            continue
        text = roh.decode("utf-8", errors="replace")
        fehler = _fehler_beschreibung(text)
        if fehler:
            bericht.ungueltig[datei.name] = "\n".join(f"- {f}" for f in fehler)
            continue
        ausgang = blattordner / datei.stem
        ausgang.mkdir(exist_ok=True)
        for alt in ausgang.iterdir():  # Titel kann sich geändert haben, alte Fassung soll nicht liegen bleiben
            if alt.suffix in (".docx", ".pdf"):
                alt.unlink()
        docx = ausgang / f"{dateiname(json.loads(text)['titel'])}.docx"
        try:
            bauen(text, docx, profil=profil, vorschau=False)
            pdf = als_pdf(docx, ausgang)
        except renderer.BeschreibungUngueltig as f:  # nach pruefen() nicht zu erwarten, dann eben an Claude
            bericht.ungueltig[datei.name] = "\n".join(f"- {x}" for x in f.fehler)
            continue
        except (ValueError, OSError, vorschau.VorschauFehler) as f:
            bericht.fehler.append(f"{datei.name}: {f}")
            continue
        bericht.pdfs.append(pdf)
        stand[datei.name] = summe
    stand_datei.write_text(json.dumps(stand, indent=1))
    return bericht
