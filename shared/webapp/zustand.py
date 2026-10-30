"""Was die Web-App selbst speichert, bis Konten oder agentkit es können: "final" je Auftrag und Lias eigene Fassungen.

Je Instanz eine JSON-Datei data/zustand/<schluessel>.json, die Dateien der eigenen Fassungen unter
data/eigene/<schluessel>/<ursprung-id>/<n>/<name>. Nichts davon liegt in Lias Instanz, die Agenten sehen es nicht
(Bedarf b und d in Punkt 24 der Haupt-STATUS).

Format:
  {"final":  {"<ursprung-id>": {"fassung": "<auftrags-id oder eigene-n>", "zeit": "<iso>"}},
   "eigene": {"<ursprung-id>": [{"name": "Blatt.docx", "datei": "1/Blatt.docx", "zeit": "<iso>", "notiz": ""}]}}
Die reine Logik dazu steht in logik.py (final_setzen, eigene_dazu).
"""

import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger("webapp")


def leer() -> dict:
    return {"final": {}, "eigene": {}}


class Zustand:
    def __init__(self, daten_dir: Path, instanz: Path):
        schluessel = hashlib.sha256(str(instanz.resolve()).encode()).hexdigest()[:12]
        self.datei = daten_dir / "zustand" / f"{schluessel}.json"
        self.ablage = daten_dir / "eigene" / schluessel

    def lesen(self) -> dict:
        """Gespeicherter Zustand; fehlt die Datei: leer. Kaputte Datei: Fehler im Log, leer (nichts überschreiben,
        schreiben() bricht dann ab)."""
        try:
            daten = json.loads(self.datei.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return leer()
        except (OSError, ValueError) as fehler:
            logger.error("Zustand %s nicht lesbar: %s", self.datei, fehler)
            return {**leer(), "kaputt": True}
        if not isinstance(daten, dict):
            logger.error("Zustand %s ist kein Objekt", self.datei)
            return {**leer(), "kaputt": True}
        return {"final": dict(daten.get("final") or {}), "eigene": dict(daten.get("eigene") or {})}

    def schreiben(self, daten: dict) -> None:
        """Ganz oder gar nicht (temporäre Datei, dann umbenennen). Eine kaputte Datei wird nie überschrieben."""
        if daten.get("kaputt"):
            raise OSError(f"Zustand {self.datei} ist kaputt, nichts geschrieben")
        self.datei.parent.mkdir(parents=True, exist_ok=True)
        self.datei.parent.chmod(0o700)
        fd, tmp = tempfile.mkstemp(dir=self.datei.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"final": daten["final"], "eigene": daten["eigene"]}, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.datei)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def finale(self) -> set[str]:
        """IDs der Ursprünge mit einer finalen Fassung (für "Heute")."""
        return set(self.lesen()["final"])

    def ordner_eigene(self, ursprung_id: str, n: int) -> Path:
        return self.ablage / ursprung_id / str(n)
