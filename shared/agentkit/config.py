"""Konfiguration laden.

Reihenfolge: zuerst shared/.env, dann <agent>/.env. Bei gleichen Schlüsseln
gewinnt der Wert des Agenten. Jede vorhandene .env muss chmod 600 haben
(keine Rechte für Gruppe oder andere), sonst wird abgebrochen.
"""

import stat
from pathlib import Path

SHARED_DIR = Path(__file__).resolve().parent.parent


class ConfigFehler(Exception):
    pass


def _pruefe_rechte(pfad: Path) -> None:
    modus = stat.S_IMODE(pfad.stat().st_mode)
    if modus & 0o077:
        raise ConfigFehler(
            f"{pfad} hat Rechte {oct(modus)}, erlaubt ist nur 600. "
            f"Beheben mit: chmod 600 {pfad}"
        )


def lies_env(pfad: Path) -> dict[str, str]:
    """Liest eine .env-Datei (KEY=WERT, Kommentare mit #). Fehlt sie, kommt {} zurück."""
    if not pfad.exists():
        return {}
    _pruefe_rechte(pfad)
    werte = {}
    for nr, zeile in enumerate(pfad.read_text(encoding="utf-8").splitlines(), start=1):
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#"):
            continue
        if zeile.startswith("export "):
            zeile = zeile[len("export "):].lstrip()
        if "=" not in zeile:
            raise ConfigFehler(f"{pfad}, Zeile {nr}: kein '=' gefunden")
        schluessel, wert = zeile.split("=", 1)
        schluessel, wert = schluessel.strip(), wert.strip()
        if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "\"'":
            wert = wert[1:-1]
        werte[schluessel] = wert
    return werte


def lade_config(agent_dir: Path, pflicht: tuple[str, ...] = ()) -> dict[str, str]:
    """Lädt shared/.env und <agent_dir>/.env. Fehlende oder leere Pflichtwerte führen zum Abbruch."""
    config = lies_env(SHARED_DIR / ".env")
    config.update(lies_env(Path(agent_dir) / ".env"))
    fehlend = [k for k in pflicht if not config.get(k)]
    if fehlend:
        raise ConfigFehler(f"Fehlende Werte in .env: {', '.join(fehlend)}")
    return config
