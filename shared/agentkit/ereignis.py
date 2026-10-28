"""Ereignisse der Agenten für den Leitstand (shared/leitstand).

Jedes Ereignis ist eine Zeile in KONTINGENT_DIR/ereignisse/<JJJJ-MM-TT>.jsonl (nicht im Repo,
gemeinsam für alle Instanzen wie das Verbrauchsprotokoll). Es wird nur angehängt, mit Dateisperre.

Felder: id, zeit (Unix-Sekunden), typ, agent, instanz, lauf, auftrag, daten.
id = "<JJJJ-MM-TT>:<Byte-Position der Zeile>": eindeutig, aufsteigend, und lesen(seit=id) setzt
genau dahinter fort (z. B. nach einem Neuladen der Seite).

Datenschutz: In daten nur IDs, Arten, Zahlen und Werkzeugnamen, nie Inhalte (kein Auftragstext,
keine Antwort von Claude, keine Dateinamen, keine Suchbegriffe). Zur Sicherheit werden Texte in daten
auf MAX_TEXT Zeichen gekürzt.

schreiben() wirft nie: Ein Fehler hier darf keinen Lauf beenden. Er landet als Warnung im Log.

Typen (Stand Stufe 1): auftrag.angelegt, auftrag.abgeschlossen, lauf.gestartet, werkzeug, lauf.beendet,
lauf.fehler, freigabe.wartet, freigabe.entschieden, freigabe.ausfuehrung_begonnen, freigabe.ausgefuehrt.
Unklare Ausführungen (begonnen, nie abgeschlossen) ergeben sich daraus bzw. aus freigabe.unklare().
"""

import fcntl
import json
import logging
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from . import config
from .config import KONTINGENT_DIR

# AGENTKIT_EREIGNIS_DIR: anderer Ordner, z. B. in pruefen.sh, damit Tests nie in die echte Datei schreiben
ORDNER = Path(os.environ.get("AGENTKIT_EREIGNIS_DIR") or KONTINGENT_DIR / "ereignisse")
MAX_TEXT = 100
logger = logging.getLogger("agentkit.ereignis")


def ordner_zu(basis: Path | None) -> Path | None:
    """Ereignis-Ordner für eine Warteschlange: Mit eigener basis (Tests) darin, sonst der gemeinsame."""
    return None if basis is None else Path(basis) / "ereignisse"


def _kuerzen(wert):
    if isinstance(wert, str):
        return wert[:MAX_TEXT]
    if isinstance(wert, dict):
        return {k: _kuerzen(v) for k, v in wert.items()}
    if isinstance(wert, (list, tuple)):
        return [_kuerzen(v) for v in wert]
    return wert


def schreiben(typ: str, agent: str | None = None, *, lauf: str | None = None, auftrag: str | None = None,
              daten: dict | None = None, ordner: Path | None = None, jetzt: float | None = None) -> str | None:
    """Hängt ein Ereignis an und gibt seine id zurück (None bei Fehler)."""
    try:
        zeit = time.time() if jetzt is None else jetzt
        tag = datetime.fromtimestamp(zeit).date().isoformat()
        ordner = ordner or ORDNER
        ordner.mkdir(parents=True, exist_ok=True)
        eintrag = {"zeit": round(zeit, 3), "typ": typ, "agent": agent, "instanz": config.INSTANZ_NAME,
                   "lauf": lauf, "auftrag": auftrag, "daten": _kuerzen(daten or {})}
        zeile = (json.dumps(eintrag, ensure_ascii=False) + "\n").encode("utf-8")
        with open(ordner / f"{tag}.jsonl", "ab") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            pos = f.seek(0, os.SEEK_END)
            f.write(zeile)
        return f"{tag}:{pos}"
    except Exception as e:  # noqa: BLE001 - siehe Moduldoku: nie den Lauf beenden
        logger.warning("Ereignis %s (%s) nicht geschrieben: %s", typ, agent, e)
        return None


def _zerlege_id(eid: str) -> tuple[str, int]:
    tag, _, pos = eid.partition(":")
    date.fromisoformat(tag)  # ValueError bei Unsinn
    return tag, int(pos)


def lesen(seit: str | None = None, tage: int = 2, ordner: Path | None = None, heute: date | None = None) -> list[dict]:
    """Ereignisse in Reihenfolge, jedes mit Feld id.

    seit=None: die letzten `tage` Tage (heute eingeschlossen). seit=id: alles danach, auch aus späteren Tagen.
    Kaputte Zeilen (Absturz beim Schreiben) werden übersprungen.
    """
    if seit:
        ab_tag, ab_pos = _zerlege_id(seit)
    else:
        ab_tag, ab_pos = ((heute or date.today()) - timedelta(days=tage - 1)).isoformat(), -1
    ordner = ordner or ORDNER
    if not ordner.is_dir():
        return []
    ergebnis = []
    for datei in sorted(ordner.glob("*.jsonl")):
        tag = datei.stem
        if tag < ab_tag:
            continue
        with open(datei, "rb") as f:
            pos = 0
            for roh in f:
                start, pos = pos, pos + len(roh)
                if tag == ab_tag and start <= ab_pos:
                    continue
                if not roh.endswith(b"\n"):
                    break  # wird gerade geschrieben
                try:
                    e = json.loads(roh)
                except json.JSONDecodeError:
                    continue
                ergebnis.append({"id": f"{tag}:{start}", **e})
    return ergebnis


def aufraeumen(tage: int = 30, ordner: Path | None = None, heute: date | None = None) -> list[str]:
    """Löscht Tagesdateien, die älter als `tage` sind. Gibt die gelöschten Namen zurück."""
    ordner = ordner or ORDNER
    if not ordner.is_dir():
        return []
    grenze = ((heute or date.today()) - timedelta(days=tage)).isoformat()
    weg = []
    for datei in sorted(ordner.glob("*.jsonl")):
        if datei.stem < grenze:
            datei.unlink()
            weg.append(datei.name)
    return weg
