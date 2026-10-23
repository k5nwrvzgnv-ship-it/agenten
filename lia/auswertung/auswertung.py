"""Auswertung von Lias claude.ai-Chats: Welche wiederkehrenden Aufgaben lohnen sich für ihre Agenten?

Werkzeug, das Jan von Hand startet (kein Dienst, kein Timer). Rohdaten nur in data/ (ablage.py).
Aufruf: .venv/bin/python auswertung.py <befehl>
  entpacken <zip>… je ZIP nach data/export/<name>/ entpacken, danach die ZIP-Datei löschen
  struktur         Feldnamen, Typen, Anzahlen des Exports (ohne Inhalte), auch nach data/struktur.txt
  chatliste        Vorschlag, welche Chats Lias sind, nach data/chatliste.tsv (nur Titel)
  filtern <projekt-uuid>…  bestätigte Chats und diese Projekte nach data/lia/, übrige Chats und Projekte löschen
Ohne Befehl wird nur data/ angelegt. Plan und weitere Schritte in STATUS.md.
"""

import json
import shutil
import sys
from collections import Counter
from pathlib import Path

import ablage
import auswahl
import export

EXPORT = ablage.DATEN / "export"
LIA = ablage.DATEN / "lia"


def main(argumente: list[str]) -> int:
    ablage.datenordner()
    befehl = argumente[0] if argumente else ""
    if befehl == "entpacken" and len(argumente) >= 2:
        # Der Export kommt als mehrere ZIPs (conversations-000.zip, projects-000.zip, ...), je eins in einen Unterordner
        for zip_pfad in map(Path, argumente[1:]):
            ziel = EXPORT / zip_pfad.stem
            if ziel.exists() and any(ziel.iterdir()):
                print(f"{ziel} ist nicht leer, {zip_pfad.name} übersprungen. Erst prüfen und von Hand leeren.")
                continue
            dateien = export.entpacken(zip_pfad, ziel)
            zip_pfad.unlink()
            print(f"{len(dateien)} Dateien nach {ziel} entpackt, {zip_pfad.name} gelöscht.")
        return 0
    if befehl == "struktur":
        text = export.bericht(EXPORT)
        ablage.schreiben(ablage.DATEN / "struktur.txt", text)
        print(text)
        return 0
    if befehl == "chatliste":
        ziel = ablage.DATEN / "chatliste.tsv"
        if ziel.exists():
            print(f"{ziel} gibt es schon (vielleicht mit Korrekturen). Erst von Hand umbenennen.")
            return 1
        quellen = sorted(EXPORT.rglob("conversations*.json"))  # Aufbau des neuen Exports noch ungeprüft
        if len(quellen) != 1:
            print(f"Erwartet genau eine conversations*.json unter {EXPORT}, gefunden: {len(quellen)}")
            return 1
        gespraeche = json.loads(quellen[0].read_text(encoding="utf-8"))
        tsv = auswahl.chatliste(gespraeche)
        ablage.schreiben(ziel, tsv)
        anzahl = Counter(z.rsplit("\t", 1)[1] for z in tsv.splitlines()[1:])
        print(f"{ziel}: {sum(anzahl.values())} Chats, Vorschlag {dict(anzahl)}. Spalte wer korrigieren.")
        return 0
    if befehl == "filtern":
        return filtern_befehl(argumente[1:])
    if befehl:
        print(__doc__)
        return 1
    print(f"Datenordner bereit: {ablage.DATEN} (chmod 700)")
    return 0


def filtern_befehl(projekt_uuids: list[str]) -> int:
    """Lias Chats und die genannten Projekte nach data/lia/, danach Export-Chats und -Projekte löschen."""
    lia = auswahl.bestaetigte_lia((ablage.DATEN / "chatliste.tsv").read_text(encoding="utf-8"))
    quelle = EXPORT / "conversations-000" / "conversations.json"
    chats = auswahl.filtern(json.loads(quelle.read_text(encoding="utf-8")), lia)
    projekte_dir = EXPORT / "projects-000" / "projects"
    projekte = [projekte_dir / f"{u}.json" for u in projekt_uuids]
    for p in projekte:
        if not p.is_file():
            print(f"Projekt fehlt: {p.name}")
            return 1
    ziel = ablage.datenordner(LIA)
    ablage.schreiben(ziel / "chats.json", json.dumps(chats, ensure_ascii=False))
    ablage.datenordner(ziel / "projekte")
    for p in projekte:
        ablage.schreiben_bytes(ziel / "projekte" / p.name, p.read_bytes())
    if len(json.loads((ziel / "chats.json").read_text(encoding="utf-8"))) != len(lia):
        print("Kontrolle fehlgeschlagen, nichts gelöscht.")
        return 1
    quelle.unlink()
    shutil.rmtree(projekte_dir)
    print(f"{len(chats)} Chats und {len(projekte)} Projekte nach {ziel}. Übrige Chats und Projekte gelöscht.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
