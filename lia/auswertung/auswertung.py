"""Auswertung von Lias claude.ai-Chats: Welche wiederkehrenden Aufgaben lohnen sich für ihre Agenten?

Werkzeug, das Jan von Hand startet (kein Dienst, kein Timer). Rohdaten nur in data/ (ablage.py).
Aufruf: .venv/bin/python auswertung.py <befehl>
  entpacken <zip>  Export nach data/export/ entpacken, danach die ZIP-Datei löschen
  struktur         Feldnamen, Typen, Anzahlen des Exports (ohne Inhalte), auch nach data/struktur.txt
Ohne Befehl wird nur data/ angelegt. Plan und weitere Schritte in STATUS.md.
"""

import sys
from pathlib import Path

import ablage
import export

EXPORT = ablage.DATEN / "export"


def main(argumente: list[str]) -> int:
    ablage.datenordner()
    befehl = argumente[0] if argumente else ""
    if befehl == "entpacken" and len(argumente) == 2:
        zip_pfad = Path(argumente[1])
        if EXPORT.exists() and any(EXPORT.iterdir()):
            print(f"{EXPORT} ist nicht leer. Erst prüfen und von Hand leeren.")
            return 1
        dateien = export.entpacken(zip_pfad, EXPORT)
        zip_pfad.unlink()
        print(f"{len(dateien)} Dateien nach {EXPORT} entpackt, {zip_pfad.name} gelöscht.")
        return 0
    if befehl == "struktur":
        text = export.bericht(EXPORT)
        ablage.schreiben(ablage.DATEN / "struktur.txt", text)
        print(text)
        return 0
    if befehl:
        print(__doc__)
        return 1
    print(f"Datenordner bereit: {ablage.DATEN} (chmod 700)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
