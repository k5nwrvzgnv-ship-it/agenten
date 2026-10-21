"""Vorschau: docx/pptx -> PDF (LibreOffice) -> ein PNG je Seite (pypdfium2).

Damit sehen Claude und der Renderer-Chat, wie eine gebaute Datei aussieht. Schriften, die auf dem Server
fehlen, ersetzt LibreOffice (Calibri durch Carlito mit gleichen Maßen, Aptos nur ungefähr).
pypdfium2 wird erst bei Bedarf importiert: Wer keine Vorschau braucht, braucht es nicht in seiner .venv.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

SOFFICE = "soffice"  # aus apt (libreoffice-*-nogui), siehe STATUS.md
ZEITLIMIT_S = 120
AUFLOESUNG_DPI = 100  # reicht zum Ansehen, ein A4-Bild ist dann etwa 830 x 1170 Pixel
MAX_SEITEN = 30
OFFICE_ENDUNGEN = (".docx", ".pptx", ".xlsx", ".odt", ".odp")


class VorschauFehler(RuntimeError):
    """Die Vorschau ging nicht (LibreOffice fehlt, Zeitlimit, kaputte Datei)."""


def vorschau(quelle: Path, zielordner: Path, dpi: int = AUFLOESUNG_DPI) -> list[Path]:
    """Bilder aller Seiten (höchstens MAX_SEITEN) von docx, pptx oder pdf nach `zielordner`."""
    quelle, zielordner = Path(quelle), Path(zielordner)
    zielordner.mkdir(parents=True, exist_ok=True)
    pdf = quelle if quelle.suffix.lower() == ".pdf" else als_pdf(quelle, zielordner)
    return als_bilder(pdf, zielordner, dpi)


def als_pdf(quelle: Path, zielordner: Path) -> Path:
    """Office-Datei mit LibreOffice in PDF umwandeln. Gibt den Pfad der PDF zurück."""
    if quelle.suffix.lower() not in OFFICE_ENDUNGEN:
        raise VorschauFehler(f"{quelle.name}: nur {', '.join(OFFICE_ENDUNGEN)} oder .pdf")
    if not quelle.is_file():
        raise VorschauFehler(f"{quelle}: Datei fehlt")
    soffice = shutil.which(SOFFICE)
    if soffice is None:
        raise VorschauFehler("LibreOffice (soffice) ist nicht installiert")
    # Eigenes Profil je Aufruf: Zwei gleichzeitige Läufe sperren sich sonst gegenseitig.
    with tempfile.TemporaryDirectory(prefix="renderer-lo-") as profil:
        befehl = [soffice, "--headless", "--norestore", "--nolockcheck",
                  f"-env:UserInstallation={Path(profil).as_uri()}",
                  "--convert-to", "pdf", "--outdir", str(zielordner), str(quelle)]
        try:
            lauf = subprocess.run(befehl, capture_output=True, text=True, timeout=ZEITLIMIT_S)
        except subprocess.TimeoutExpired as e:
            raise VorschauFehler(f"{quelle.name}: LibreOffice brauchte länger als {ZEITLIMIT_S} s") from e
    pdf = zielordner / f"{quelle.stem}.pdf"
    if lauf.returncode != 0 or not pdf.is_file():
        meldung = (lauf.stderr or lauf.stdout).strip()[-500:]
        raise VorschauFehler(f"{quelle.name}: Umwandlung in PDF fehlgeschlagen ({lauf.returncode}): {meldung}")
    return pdf


def als_bilder(pdf: Path, zielordner: Path, dpi: int = AUFLOESUNG_DPI) -> list[Path]:
    """Ein PNG je Seite (`<name>-seite-01.png`, ...), höchstens MAX_SEITEN."""
    import pypdfium2

    try:
        dokument = pypdfium2.PdfDocument(pdf)
    except pypdfium2.PdfiumError as e:
        raise VorschauFehler(f"{Path(pdf).name}: PDF lässt sich nicht öffnen ({e})") from e
    bilder = []
    try:
        for nr in range(min(len(dokument), MAX_SEITEN)):
            ziel = Path(zielordner) / f"{Path(pdf).stem}-seite-{nr + 1:02d}.png"
            dokument[nr].render(scale=dpi / 72).to_pil().save(ziel)
            bilder.append(ziel)
    finally:
        dokument.close()
    return bilder
