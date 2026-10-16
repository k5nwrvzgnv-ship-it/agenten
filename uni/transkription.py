"""Vorlesungsaufzeichnungen in data/kurse/ nachts transkribieren (faster-whisper, nur CPU).

Läuft als eigener Dienst uni-transkript (Timer 1 Uhr), getrennt von agent.py.
Zu jeder Ton- oder Videodatei ohne Transkript entsteht <datei>.txt mit Zeitmarken
("[12:34] ..."). Fertige Transkripte werden nicht neu gerechnet. Schlägt eines fehl, steht der
Fehler in der .txt (und Jan bekommt eine Meldung). Für einen neuen Versuch die .txt löschen.

Tempo (Test 16.10.2026, Modell small, int8, 4 Kerne): 10 min Vorlesung in knapp 17 min,
also Faktor ~1,7. Eine Datei wird nur angefangen, wenn sie voraussichtlich vor ENDE_UHR
fertig ist, damit der Lauf um 8 Uhr frei bleibt.

Den Ton liest av direkt, weil faster-whisper 1.2.1 mit av 19 nicht zusammenpasst
(open() kennt metadata_errors nicht mehr). ffmpeg ist nicht nötig.
"""

import time
from datetime import datetime
from pathlib import Path

from agentkit import log, meldungen

from kurse import MEDIEN_ENDUNGEN as ENDUNGEN

AGENT = "uni"
HIER = Path(__file__).resolve().parent
ZIEL = HIER / "data" / "kurse"
MODELLE = HIER / "data" / "modelle"
MODELL = "small"
FAKTOR = 2.0  # Rechenzeit pro Sekunde Aufnahme, gemessen 1,7, mit Reserve
ENDE_UHR = 7
KOPF = (f"Automatisches Transkript (Whisper {MODELL}). Hörfehler möglich, vor allem bei Fachbegriffen "
        "und Namen. Zeitmarken [Minute:Sekunde] zum Nachhören im Video.\n\n")
logger = log.hole_logger(HIER, "uni-transkript")


def offene(ziel: Path) -> list[Path]:
    """Ton- und Videodateien ohne Transkript, älteste zuerst. Halbe Downloads (.tmp) zählen nicht."""
    dateien = [p for p in ziel.rglob("*") if p.is_file() and p.suffix.lower() in ENDUNGEN
               and not p.name.startswith(".") and not p.with_name(p.name + ".txt").exists()]
    return sorted(dateien, key=lambda p: p.stat().st_mtime)


def passt_noch(dauer_s: float, jetzt: datetime, ende_uhr: int = ENDE_UHR) -> bool:
    """Wird eine Aufnahme dieser Länge voraussichtlich vor ende_uhr (am selben Morgen) fertig?"""
    ende = jetzt.replace(hour=ende_uhr, minute=0, second=0, microsecond=0)
    if jetzt >= ende:
        return False
    return dauer_s * FAKTOR <= (ende - jetzt).total_seconds()


def zeitmarke(sekunden: float) -> str:
    s = int(sekunden)
    return f"[{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}]" if s >= 3600 else f"[{s // 60:02d}:{s % 60:02d}]"


def dauer(pfad: Path) -> float:
    import av
    with av.open(str(pfad)) as c:
        return (c.duration or 0) / 1e6


def ton_lesen(pfad: Path):
    """Ton als float32-Array, 16 kHz mono (das Format, das Whisper erwartet)."""
    import av
    import numpy as np
    teile = []
    with av.open(str(pfad)) as c:
        umwandler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        for frame in c.decode(audio=0):
            teile += [f.to_ndarray().reshape(-1) for f in umwandler.resample(frame)]
        teile += [f.to_ndarray().reshape(-1) for f in umwandler.resample(None)]
    return np.concatenate(teile).astype(np.float32) / 32768.0


def transkribieren(pfad: Path, modell) -> None:
    segmente, _ = modell.transcribe(ton_lesen(pfad), language="de", vad_filter=True)
    txt = pfad.with_name(pfad.name + ".txt")
    tmp = pfad.with_name(f".{pfad.name}.txt.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(KOPF)
        for s in segmente:
            f.write(f"{zeitmarke(s.start)} {s.text.strip()}\n")
    tmp.replace(txt)


def lauf() -> None:
    liste = offene(ZIEL)
    if not liste:
        return
    from faster_whisper import WhisperModel
    modell = WhisperModel(MODELL, device="cpu", compute_type="int8", cpu_threads=4, download_root=str(MODELLE))
    for pfad in liste:
        rel = pfad.relative_to(ZIEL)
        sekunden = dauer(pfad)
        if not passt_noch(sekunden, datetime.now()):
            logger.info("Pause bis zur nächsten Nacht, offen: %d Datei(en)", len(offene(ZIEL)))
            return
        logger.info("Transkribiere %s (%.0f min)", rel, sekunden / 60)
        start = time.time()
        try:
            transkribieren(pfad, modell)
        except Exception as f:  # noqa: BLE001 – Jan erfährt es, die übrigen Dateien laufen weiter
            logger.exception("Transkript fehlgeschlagen: %s", rel)
            meldungen.melden(AGENT, f"Transkript fehlgeschlagen: {rel}\n{f}")
            pfad.with_name(pfad.name + ".txt").write_text(f"(Transkript fehlgeschlagen: {f})", encoding="utf-8")
            continue
        logger.info("Fertig in %.0f min", (time.time() - start) / 60)
        meldungen.melden(AGENT, f"Aufzeichnung transkribiert: {rel}\nText: {rel}.txt")


if __name__ == "__main__":
    lauf()
