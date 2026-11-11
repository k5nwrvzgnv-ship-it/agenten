"""Seitenbilder für Ergebnisdateien ohne Renderer-Vorschau (umbauplan-ux.md Schritt 6, Jans Okay 11.11.2026).

Der Renderer legt neben seinen Dateien <stem>-vorschau/ an (dateien.py). Viele Ergebnisse von uni und finance sind
aber PDFs oder Word-Dateien ohne diesen Ordner. Für sie macht der Arbeitsplatz die Bilder selbst, mit derselben
Funktion wie der Renderer (renderer.vorschau: LibreOffice -> PDF -> pypdfium2 -> ein PNG je Seite), und legt sie in
seinen eigenen Ordner data/vorschau/<auftrag>/<nr>/. Die Ordner der Agenten bleiben unberührt.

Die Umwandlung läuft in einem eigenen Prozess (vorschau_lauf.py) mit eigener Speichergrenze (systemd-run --scope),
weil der Dienst nur 200 MB darf und LibreOffice mehr braucht. Immer nur eine zur Zeit (ein Faden, eine Schlange).
Je Ordner steht in quelle.txt, aus welcher Fassung der Datei die Bilder sind (Größe und Zeitstempel); ändert sich
die Datei, gilt die Vorschau als fehlend. Ging es schief, steht der Grund in fehler.txt; nach einem Tag gibt es einen
neuen Versuch.
"""

import logging
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger("arbeitsplatz")

HIER = Path(__file__).resolve().parent
ENDUNGEN = {".pdf", ".docx", ".pptx", ".xlsx"}
SPEICHER = "1G"  # Grenze des Prozesses, der umwandelt
ZEITLIMIT_S = 300
NEUER_VERSUCH_S = 24 * 3600
FERTIG, LAEUFT, FEHLER, FEHLT = "fertig", "laeuft", "fehler", "fehlt"


def _lauf(quelle: Path, ziel: Path) -> None:
    """Bilder (und bei Office-Dateien die PDF) von quelle nach ziel, in einem eigenen Prozess mit Speichergrenze."""
    befehl = ["systemd-run", "--user", "--scope", "--quiet", "-p", f"MemoryMax={SPEICHER}",
              sys.executable, str(HIER / "vorschau_lauf.py"), str(quelle), str(ziel)]
    try:
        lauf = subprocess.run(befehl, capture_output=True, text=True, timeout=ZEITLIMIT_S)
    except (OSError, subprocess.SubprocessError) as f:
        raise RuntimeError(f"Vorschau nicht gestartet: {f}") from f
    if lauf.returncode != 0:
        raise RuntimeError(f"Vorschau fehlgeschlagen ({lauf.returncode}): {(lauf.stderr or lauf.stdout).strip()[-400:]}")


def kennung(quelle: Path) -> str:
    st = quelle.stat()
    return f"{st.st_size}:{st.st_mtime_ns}"


class Vorschauen:
    """Vorschauen in ordner/<auftrag>/<nr>/. ausfuehren(quelle, ziel) macht die Bilder (Standard: _lauf)."""

    def __init__(self, ordner: Path, ausfuehren: Callable[[Path, Path], None] | None = None):
        self.ordner = ordner
        self.ausfuehren = ausfuehren
        self._sperre = threading.Lock()
        self._schlange: queue.Queue = queue.Queue()
        self._offen: set[tuple[str, int]] = set()
        self._faden: threading.Thread | None = None

    def ziel(self, auftrag: str, nr: int) -> Path:
        return self.ordner / auftrag / str(nr)

    def stand(self, auftrag: str, nr: int, quelle: Path) -> str:
        with self._sperre:
            if (auftrag, nr) in self._offen:
                return LAEUFT
        z = self.ziel(auftrag, nr)
        try:
            if (z / "quelle.txt").read_text(encoding="utf-8") != kennung(quelle):
                return FEHLT
            fehler = z / "fehler.txt"
            if fehler.exists():
                return FEHLT if time.time() - fehler.stat().st_mtime > NEUER_VERSUCH_S else FEHLER
        except OSError:
            return FEHLT
        return FERTIG

    def seiten(self, auftrag: str, nr: int, quelle: Path) -> list[Path]:
        """Seitenbilder nach Seitenzahl; ohne fertige Vorschau leer."""
        if self.stand(auftrag, nr, quelle) != FERTIG:
            return []
        muster = re.compile(re.escape(quelle.stem) + r"-seite-(\d+)\.png")
        z = self.ziel(auftrag, nr)
        treffer = []
        for p in z.iterdir():
            if m := muster.fullmatch(p.name):
                treffer.append((int(m.group(1)), p))
        return [p for _, p in sorted(treffer)]

    def pdf(self, auftrag: str, nr: int, quelle: Path) -> Path | None:
        """PDF einer Office-Datei (LibreOffice), wenn die Vorschau fertig ist."""
        if quelle.suffix.lower() == ".pdf" or self.stand(auftrag, nr, quelle) != FERTIG:
            return None
        pdf = self.ziel(auftrag, nr) / f"{quelle.stem}.pdf"
        return pdf if pdf.is_file() else None

    def anstossen(self, auftrag: str, nr: int, quelle: Path) -> bool:
        """Vorschau in die Schlange, wenn sie fehlt. True: läuft jetzt oder schon."""
        if quelle.suffix.lower() not in ENDUNGEN:
            return False
        st = self.stand(auftrag, nr, quelle)
        if st == LAEUFT:
            return True
        if st != FEHLT:
            return False
        with self._sperre:
            if (auftrag, nr) in self._offen:
                return True
            self._offen.add((auftrag, nr))
            self._schlange.put((auftrag, nr, quelle))
            if self._faden is None or not self._faden.is_alive():
                self._faden = threading.Thread(target=self._arbeiten, name="vorschau", daemon=True)
                self._faden.start()
        return True

    def warten(self, sekunden: float = 30) -> None:
        """Bis die Schlange leer ist (für Tests)."""
        faden = self._faden
        if faden is not None:
            faden.join(sekunden)

    def _arbeiten(self) -> None:
        while True:
            with self._sperre:
                try:
                    auftrag, nr, quelle = self._schlange.get_nowait()
                except queue.Empty:
                    self._faden = None
                    return
            try:
                self._machen(auftrag, nr, quelle)
            finally:
                with self._sperre:
                    self._offen.discard((auftrag, nr))

    def _machen(self, auftrag: str, nr: int, quelle: Path) -> None:
        z = self.ziel(auftrag, nr)
        try:
            z.parent.mkdir(parents=True, exist_ok=True)
            neu = Path(tempfile.mkdtemp(dir=z.parent, prefix=f".{nr}-neu-"))
        except OSError as f:
            logger.error("Vorschau %s/%d: Ordner nicht angelegt: %s", auftrag, nr, f)
            return
        try:
            stempel = kennung(quelle)
            (self.ausfuehren or _lauf)(quelle, neu)
            logger.info("Vorschau %s/%d (%s) erstellt", auftrag, nr, quelle.name)
        except Exception as f:  # noqa: BLE001 - jeder Fehler landet in fehler.txt und im Log, der Faden lebt weiter
            logger.error("Vorschau %s/%d (%s) ging nicht: %s", auftrag, nr, quelle.name, f)
            (neu / "fehler.txt").write_text(str(f)[:500], encoding="utf-8")
            try:
                stempel = kennung(quelle)
            except OSError:
                stempel = ""
        try:
            (neu / "quelle.txt").write_text(stempel, encoding="utf-8")
            if z.exists():
                shutil.rmtree(z)
            neu.rename(z)
        except OSError as f:
            logger.error("Vorschau %s/%d nicht gespeichert: %s", auftrag, nr, f)
            shutil.rmtree(neu, ignore_errors=True)
