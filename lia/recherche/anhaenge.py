"""Anhänge zu einem Webauftrag: prüfen und in den Auftragsordner kopieren (Jan, 25.10.2026).

Zwei Wege: Zeilen "ANHANG: <absoluter Pfad>" in der Auftragsdatei und --anhang <pfad> beim Aufruf.
Erlaubt: Dateien unter ERLAUBT_UNTER (/home/agent/agenten/lia), nicht unter lia/instanz, keinem .venv- oder
.git-Ordner, kein .env*, nur ENDUNGEN, höchstens MAX_BYTES. Symlinks werden aufgelöst und dann geprüft.
Bei pdf und docx legt kopieren() mit agentkit.textfassung eine Textfassung <name>.txt daneben.
Abgelehntes kommt mit Grund zurück; der Aufrufer loggt es und meldet es Jan.
"""

import re
import shutil
from pathlib import Path

ERLAUBT_UNTER = Path("/home/agent/agenten/lia")
GESPERRT = ("instanz",)  # Unterordner von ERLAUBT_UNTER
ENDUNGEN = (".md", ".txt", ".pdf", ".docx")
MAX_BYTES = 5 * 1024 * 1024
_ZEILE = re.compile(r"^\s*ANHANG:\s*(\S.*?)\s*$", re.MULTILINE)


def aus_auftrag(text: str) -> list[str]:
    """Pfade aus Zeilen "ANHANG: <pfad>"."""
    return _ZEILE.findall(text)


def grund(pfad: str | Path, wurzel: Path = ERLAUBT_UNTER) -> str | None:
    """None, wenn der Anhang erlaubt ist, sonst der Grund."""
    roh = Path(pfad)
    if not roh.is_absolute():
        return "kein absoluter Pfad"
    try:
        echt = roh.resolve(strict=True)
    except (OSError, RuntimeError):
        return "Datei nicht gefunden"
    wurzel = wurzel.resolve()
    if not echt.is_relative_to(wurzel):
        return f"nicht unter {wurzel}"
    teile = echt.relative_to(wurzel).parts
    if teile and teile[0] in GESPERRT:
        return f"{wurzel.name}/{teile[0]} ist gesperrt"
    if any(t in (".venv", ".git") for t in teile):
        return ".venv und .git sind gesperrt"
    if echt.name.lower().startswith(".env"):
        return ".env-Dateien sind gesperrt"
    if echt.suffix.lower() not in ENDUNGEN:
        return f"Endung {echt.suffix or '(keine)'} nicht erlaubt, nur {', '.join(ENDUNGEN)}"
    if not echt.is_file():
        return "keine Datei"
    if echt.stat().st_size > MAX_BYTES:
        return f"größer als {MAX_BYTES // (1024 * 1024)} MB"
    return None


def kopieren(pfade: list[str], ziel: Path, als_text, wurzel: Path = ERLAUBT_UNTER) -> tuple[list[Path], list[str]]:
    """Kopiert erlaubte Anhänge nach ziel/ (gleiche Namen bekommen eine Nummer). Gibt (kopierte Dateien samt
    Textfassungen, abgelehnt als "pfad: grund") zurück. als_text(pfad) -> str | None (agentkit.textfassung)."""
    kopiert, abgelehnt, namen = [], [], set()
    for p in dict.fromkeys(pfade):  # doppelte nur einmal
        g = grund(p, wurzel)
        if g:
            abgelehnt.append(f"{p}: {g}")
            continue
        quelle = Path(p).resolve()
        name, n = quelle.name, 1
        while name.lower() in namen:
            n += 1
            name = f"{quelle.stem}-{n}{quelle.suffix}"
        namen.add(name.lower())
        ziel.mkdir(parents=True, exist_ok=True)
        datei = ziel / name
        shutil.copyfile(quelle, datei)
        kopiert.append(datei)
        if datei.suffix.lower() in (".pdf", ".docx"):
            try:
                text = als_text(datei)
            except Exception as e:  # noqa: BLE001 – fehlendes Paket oder kaputte Datei: melden, Datei bleibt
                abgelehnt.append(f"{p}: Textfassung nicht möglich ({type(e).__name__}: {e}), nur die Datei liegt bei")
                continue
            if text:
                textdatei = datei.with_name(datei.name + ".txt")
                textdatei.write_text(text, encoding="utf-8")
                kopiert.append(textdatei)
    return kopiert, abgelehnt
