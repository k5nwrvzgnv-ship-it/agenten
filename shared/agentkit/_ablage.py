"""Gemeinsame Hilfen für die datei-basierten Warteschlangen (ein JSON pro Eintrag).

Schreiben läuft immer über eine temporäre Datei und os.replace, damit nie eine
halb geschriebene Datei gelesen wird. Verschieben nach erledigt/ läuft über
os.rename: Das klappt nur einmal, ein Eintrag kann also nicht doppelt
abgeschlossen werden.
"""

import json
import os
import re
import secrets
from datetime import datetime
from pathlib import Path

ID_MUSTER = re.compile(r"^\d{8}-\d{6}-[a-z]+-[0-9a-f]{6}$")
AGENT_MUSTER = re.compile(r"^[a-z]+$")
MAX_ANHANG_BYTES = 50 * 1024 * 1024  # mehr nimmt die Bot-Schnittstelle von Telegram nicht an


class AblageFehler(Exception):
    pass


def jetzt() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def neue_id(agent: str) -> str:
    pruefe_agent(agent)
    return f"{datetime.now():%Y%m%d-%H%M%S}-{agent}-{secrets.token_hex(3)}"


def pruefe_agent(agent: str) -> None:
    if not AGENT_MUSTER.match(agent):
        raise AblageFehler(f"Ungültiger Agent-Name: {agent!r}")


def pruefe_id(eintrag_id: str) -> None:
    # IDs kommen später auch aus Telegram-Knöpfen: nur das bekannte Format zulassen,
    # damit niemand Pfade wie ../../ unterschieben kann.
    if not ID_MUSTER.match(eintrag_id):
        raise AblageFehler(f"Ungültige ID: {eintrag_id!r}")


def pruefe_dienst(agent: str, dienst: str | None) -> None:
    """Dienst eines Agenten: <agent> oder <agent>-<wort> (z. B. uni-lernen), die Zentrale startet ihn."""
    if dienst is not None and not re.fullmatch(rf"{re.escape(agent)}(-[a-z]+)?", dienst):
        raise AblageFehler(f"Ungültiger Dienst für {agent}: {dienst!r}")


def ordner(basis: Path, name: str) -> Path:
    pfad = basis / name
    pfad.mkdir(parents=True, exist_ok=True)
    return pfad


def schreibe(pfad: Path, daten: dict) -> None:
    tmp = pfad.with_name(f".{pfad.name}.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, pfad)


def lies(pfad: Path) -> dict:
    return json.loads(pfad.read_text(encoding="utf-8"))


def liste(verzeichnis: Path, agent: str | None = None) -> list[dict]:
    """Alle Einträge eines Ordners, älteste zuerst, optional nur für einen Agenten."""
    eintraege = []
    for pfad in sorted(verzeichnis.glob("*.json")):
        daten = lies(pfad)
        if agent is None or daten.get("agent") == agent:
            eintraege.append(daten)
    return eintraege


def abschliessen(von: Path, nach: Path, eintrag_id: str, aenderungen: dict) -> dict:
    """Verschiebt einen Eintrag von `von` nach `nach` und ergänzt `aenderungen`."""
    pruefe_id(eintrag_id)
    quelle = von / f"{eintrag_id}.json"
    zwischen = nach / f".{eintrag_id}.json.inarbeit"
    try:
        os.rename(quelle, zwischen)
    except FileNotFoundError:
        raise AblageFehler(f"{eintrag_id} ist nicht (mehr) offen") from None
    daten = lies(zwischen)
    daten.update(aenderungen)
    schreibe(nach / f"{eintrag_id}.json", daten)
    zwischen.unlink()
    return daten


def anhaenge_pruefen(agent_dir: Path, dateien) -> list[str]:
    """Dateien, die ein Agent Jan schicken will: Pfade relativ zum Agent-Ordner.

    Nur echte Dateien im eigenen Agent-Ordner, nichts Verstecktes (.env, .venv/),
    höchstens MAX_ANHANG_BYTES. Die Zentrale prüft vor dem Senden noch einmal.
    """
    wurzel = agent_dir.resolve()
    pfade = []
    for datei in map(Path, dateien):
        pfad = (agent_dir / datei).resolve()  # absolute Pfade bleiben absolut
        if not pfad.is_relative_to(wurzel):
            raise AblageFehler(f"Datei liegt nicht im Agent-Ordner: {datei}")
        relativ = pfad.relative_to(wurzel)
        if any(teil.startswith(".") for teil in relativ.parts):
            raise AblageFehler(f"Versteckte Datei: {datei}")
        if not pfad.is_file():
            raise AblageFehler(f"Datei fehlt: {datei}")
        if pfad.stat().st_size > MAX_ANHANG_BYTES:
            raise AblageFehler(f"Datei größer als {MAX_ANHANG_BYTES // 2**20} MB: {datei}")
        pfade.append(relativ.as_posix())
    return pfade
