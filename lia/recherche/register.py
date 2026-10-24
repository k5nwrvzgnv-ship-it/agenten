"""Quellenregister data/register.json (ohne Netz). lia/examen liest es später.

Aufbau: {"aktualisiert": ..., "quellen": [eintrag, ...]}, je Eintrag:
  id, art, werk, ausgabe, autor (falls vorhanden), urls, abgerufen (frühester Abruf),
  roh (je URL: url, abgerufen, sha256 des geladenen Inhalts), textfassung (Pfad relativ zum
  Agent-Ordner), sha256 (der Textfassung), gemeinfreiheit {status, verwendbar, begruendung},
  stellen [{seite, zitat, geprueft}].
Gesetze: der ganze Paragraf ist eine Stelle, Zitat = Normtext, geprüft mit agentkit.wortlaut.steht_in
gegen die Textfassung. Bei Primärtexten füllt Teil C die Stellen. Sie bleiben über Läufe erhalten,
solange sich die Textfassung nicht ändert.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from agentkit import wortlaut


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def gesetz_stelle(normtext: str, text: str) -> dict:
    return {"seite": 1, "zitat": normtext, "geprueft": wortlaut.steht_in(normtext, text)}


def eintrag(quelle: dict, metas: list[dict], textpfad: str, text: str, gemeinfreiheit: dict,
            stellen: list[dict]) -> dict:
    e = {"id": quelle["id"], "art": quelle["art"], "werk": quelle["werk"], "ausgabe": quelle["ausgabe"]}
    if quelle.get("autor"):
        e["autor"] = quelle["autor"]
    e.update({
        "urls": [m["url"] for m in metas],
        "abgerufen": min(m["abgerufen"] for m in metas),
        "roh": [{"url": m["url"], "abgerufen": m["abgerufen"], "sha256": m["sha256"]} for m in metas],
        "textfassung": textpfad,
        "sha256": sha256(text),
        "gemeinfreiheit": gemeinfreiheit,
        "stellen": stellen,
    })
    return e


def alte_stellen(alt: dict | None, text: str) -> tuple[list[dict], bool]:
    """Stellen aus dem alten Eintrag, wenn die Textfassung gleich ist. Zweiter Wert: verworfen?"""
    if not alt or not alt.get("stellen"):
        return [], False
    if alt.get("sha256") == sha256(text):
        return alt["stellen"], False
    return [], True


def laden(pfad: Path) -> dict[str, dict]:
    """Einträge nach id. Ohne Datei leer."""
    if not pfad.exists():
        return {}
    return {e["id"]: e for e in json.loads(pfad.read_text(encoding="utf-8"))["quellen"]}


def speichern(pfad: Path, eintraege: list[dict]) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    daten = {"aktualisiert": datetime.now().astimezone().isoformat(timespec="seconds"), "quellen": eintraege}
    tmp = pfad.with_name(f".{pfad.name}.tmp")
    tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(pfad)
