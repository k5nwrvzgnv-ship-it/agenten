"""Was die Web-App selbst speichert: Stunden einer Reihe (solange reihen.toml keine hat), welches Material zu welcher
Stunde gehört, welche Aufträge Varianten eines Materials sind, Lias Entscheidungen zu Entwürfen, „Nochmal“.
"final" und Lias eigene Fassungen speichert seit 30.10.2026 agentkit.fassungen (<instanz>/fassungen/, Dateien im
Agent-Ordner, damit die Agenten sie sehen; Jans Entscheidung). lesen() liefert sie zum Anzeigen mit.

Je Instanz eine JSON-Datei data/zustand/<schluessel>.json, die Dateien der eigenen Fassungen unter
data/eigene/<schluessel>/<ursprung-id>/<n>/<name>. Nichts davon liegt in Lias Instanz, die Agenten sehen es nicht
(Bedarf b und d in Punkt 24 der Haupt-STATUS).

Format:
  {"stunden": {"<reihe-id>": [{"thema": "Kant: Vergeltung", "zeit": "<iso>"}]},   Nummer = Platz in der Liste (ab 1)
   "stunde_von": {"<ursprung-id>": {"reihe": "<reihe-id>", "nr": 2}},
   "varianten": {"<ursprung-id>": [{"art": "einfach", "auftrag": "<auftrags-id der variante>", "zeit": "<iso>"}]},
   "varianten_wunsch": {"<ursprung-id>": ["tuerkisch"]},   Lias „Auch als“, bis die Variante angefordert ist
   "entwuerfe": {"<entwurf-id>": {"stand": "selbst" | "nein", "zeit": "<iso>"}},   Lias Entscheidung (logik)
   "ersetzt": {"<fehlgeschlagener ursprung>": "<auftrags-id von Nochmal>"}}
Die reine Logik dazu steht in logik.py (stunde_dazu, stunde_zuordnen, variante_dazu, entwurf_entscheiden).
Dazu beim Lesen (nur lesend aus agentkit.fassungen): "final": {"<ursprung>": {"fassung", "zeit"}},
"eigene": {"<ursprung>": [{"n", "name", "datei" (relativ zum Agent-Ordner), "notiz", "zeit"}]}.
Stunden kennen die Agenten nicht; ein Auftrag aus einer Stunde nennt sie im Text (logik.text_mit_reihe).
"""

import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger("webapp")


FELDER = ("stunden", "stunde_von", "varianten", "varianten_wunsch", "entwuerfe", "ersetzt")


def leer() -> dict:
    return {f: {} for f in FELDER}


class Zustand:
    def __init__(self, daten_dir: Path, instanz: Path):
        schluessel = hashlib.sha256(str(instanz.resolve()).encode()).hexdigest()[:12]
        self.datei = daten_dir / "zustand" / f"{schluessel}.json"
        self.fassungen = instanz / "fassungen"  # agentkit.fassungen (basis = instanz/auftraege)

    def lesen(self) -> dict:
        """Gespeicherter Zustand samt final und eigene aus agentkit.fassungen; fehlt die Datei: leer. Kaputte Datei:
        Fehler im Log, leer (nichts überschreiben, schreiben() bricht dann ab)."""
        zustand = {**leer(), **self._fassungen()}
        try:
            daten = json.loads(self.datei.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return zustand
        except (OSError, ValueError) as fehler:
            logger.error("Zustand %s nicht lesbar: %s", self.datei, fehler)
            return {**zustand, "kaputt": True}
        if not isinstance(daten, dict):
            logger.error("Zustand %s ist kein Objekt", self.datei)
            return {**zustand, "kaputt": True}
        return {**zustand, **{f: dict(daten.get(f) or {}) for f in FELDER}}

    def _fassungen(self) -> dict:
        """final und eigene je Ursprung aus <instanz>/fassungen/*.json (nur lesen; schreiben tut agentkit)."""
        final, eigene = {}, {}
        for pfad in sorted(self.fassungen.glob("*.json")) if self.fassungen.is_dir() else []:
            try:
                stand = json.loads(pfad.read_text(encoding="utf-8"))
            except (OSError, ValueError) as fehler:
                logger.error("Fassungen %s nicht lesbar: %s", pfad, fehler)
                continue
            u = stand.get("ursprung") or pfad.stem
            if stand.get("final"):
                final[u] = stand["final"]
            if stand.get("eigene"):
                eigene[u] = sorted(stand["eigene"], key=lambda e: e.get("n", 0))
        return {"final": final, "eigene": eigene}

    def schreiben(self, daten: dict) -> None:
        """Ganz oder gar nicht (temporäre Datei, dann umbenennen). Eine kaputte Datei wird nie überschrieben.
        final und eigene schreibt diese Funktion nicht (agentkit.fassungen)."""
        if daten.get("kaputt"):
            raise OSError(f"Zustand {self.datei} ist kaputt, nichts geschrieben")
        self.datei.parent.mkdir(parents=True, exist_ok=True)
        self.datei.parent.chmod(0o700)
        fd, tmp = tempfile.mkstemp(dir=self.datei.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({feld: daten.get(feld) or {} for feld in FELDER}, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.datei)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
