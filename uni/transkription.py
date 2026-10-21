"""Vorlesungsaufzeichnungen in data/kurse/ nachts transkribieren (faster-whisper, nur CPU).

Läuft als eigener Dienst uni-transkript (Timer 1 Uhr), getrennt von agent.py.
Zu jeder Ton- oder Videodatei ohne Transkript entsteht <datei>.txt mit Zeitmarken
("[12:34] ..."). Fertige Transkripte werden nicht neu gerechnet. Schlägt eines fehl, steht der
Fehler in der .txt (und Jan bekommt eine Meldung). Für einen neuen Versuch die .txt löschen.

Tempo (Test 16.10.2026, Modell small, int8, 4 Kerne): 10 min Vorlesung in knapp 17 min,
also Faktor ~1,7. Eine Datei wird nur angefangen, wenn sie voraussichtlich vor ENDE_UHR
fertig ist, damit der Lauf um 8 Uhr frei bleibt.

Speicher (gemessen 21.10.2026): faster-whisper berechnet die Merkmale für den ganzen übergebenen
Ton auf einmal, ca. 50 MB pro Minute. 69 min sprengten MemoryMax=3G (OOM-Killer). Deshalb wird in
Stücken von STUECK_S gerechnet, geschnitten an der leisesten Stelle nahe der Grenze.
Ein harter Abbruch (OOM-Killer) hinterlässt keine .txt. Damit eine solche Datei nicht jede Nacht
die Warteschlange blockiert, zählt data/transkript_versuche.json die Starts. Nach MAX_VERSUCHE
Starts ohne Ergebnis wird sie aufgegeben (Fehler-.txt und Meldung).

Den Ton liest av direkt, weil faster-whisper 1.2.1 mit av 19 nicht zusammenpasst
(open() kennt metadata_errors nicht mehr). ffmpeg ist nicht nötig.
"""

import json
import time
from datetime import datetime
from pathlib import Path

from agentkit import log, meldungen

from kurse import MEDIEN_ENDUNGEN as ENDUNGEN

AGENT = "uni"
HIER = Path(__file__).resolve().parent
ZIEL = HIER / "data" / "kurse"
MODELLE = HIER / "data" / "modelle"
VERSUCHE_DATEI = HIER / "data" / "transkript_versuche.json"
MODELL = "small"
FAKTOR = 2.0  # Rechenzeit pro Sekunde Aufnahme, gemessen 1,7, mit Reserve
ENDE_UHR = 7
RATE = 16000  # Abtastrate, die Whisper erwartet
STUECK_S = 600  # 10 min: ca. 1 GB für die Merkmale
SUCHE_S = 15  # Schnitt an der leisesten Stelle im Bereich ±SUCHE_S um die Grenze
FENSTER_S = 0.5
MAX_VERSUCHE = 2
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


def schnitte(ton, rate: int = RATE, stueck_s: float = STUECK_S, suche_s: float = SUCHE_S,
             fenster_s: float = FENSTER_S) -> list[int]:
    """Grenzen der Stücke als Sample-Index, von 0 bis len(ton).

    Etwa alle stueck_s Sekunden, jeweils in der Mitte des leisesten Fensters (fenster_s) im
    Bereich ±suche_s um die Grenze, damit möglichst kein Wort zerschnitten wird.
    """
    import numpy as np
    n, stueck, suche, fenster = len(ton), int(stueck_s * rate), int(suche_s * rate), int(fenster_s * rate)
    grenzen = [0]
    while n - grenzen[-1] > stueck + suche:
        mitte = grenzen[-1] + stueck
        von = mitte - suche
        energie = np.square(ton[von:mitte + suche].astype(np.float64))
        summe = np.concatenate(([0.0], np.cumsum(energie)))
        grenzen.append(von + int(np.argmin(summe[fenster:] - summe[:-fenster])) + fenster // 2)
    grenzen.append(n)
    return grenzen


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
        umwandler = av.AudioResampler(format="s16", layout="mono", rate=RATE)
        for frame in c.decode(audio=0):
            teile += [f.to_ndarray().reshape(-1) for f in umwandler.resample(frame)]
        teile += [f.to_ndarray().reshape(-1) for f in umwandler.resample(None)]
    return np.concatenate(teile).astype(np.float32) / 32768.0


def transkribieren(pfad: Path, modell, lesen=ton_lesen) -> None:
    ton = lesen(pfad)
    grenzen = schnitte(ton)
    txt = pfad.with_name(pfad.name + ".txt")
    tmp = pfad.with_name(f".{pfad.name}.txt.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(KOPF)
        for von, bis in zip(grenzen, grenzen[1:], strict=False):
            if bis <= von:
                continue
            segmente, _ = modell.transcribe(ton[von:bis], language="de", vad_filter=True)
            for s in segmente:
                f.write(f"{zeitmarke(von / RATE + s.start)} {s.text.strip()}\n")
    tmp.replace(txt)


def _lies_versuche(datei: Path) -> dict[str, int]:
    return json.loads(datei.read_text(encoding="utf-8")) if datei.exists() else {}


def _schreibe_versuche(datei: Path, versuche: dict[str, int]) -> None:
    datei.parent.mkdir(parents=True, exist_ok=True)
    tmp = datei.with_suffix(".tmp")
    tmp.write_text(json.dumps(versuche, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(datei)


def versuche(datei: Path, rel: str) -> int:
    """Wie oft rel schon angefangen und nicht beendet wurde."""
    return _lies_versuche(datei).get(rel, 0)


def versuch_merken(datei: Path, rel: str) -> None:
    """Vor dem Rechnen speichern: So zählt auch ein harter Abbruch (OOM-Killer)."""
    v = _lies_versuche(datei)
    v[rel] = v.get(rel, 0) + 1
    _schreibe_versuche(datei, v)


def versuch_vergessen(datei: Path, rel: str) -> None:
    v = _lies_versuche(datei)
    if v.pop(rel, None) is not None:
        _schreibe_versuche(datei, v)


def aufgeben(pfad: Path, rel: Path, grund: str) -> None:
    meldungen.melden(AGENT, f"Transkript fehlgeschlagen: {rel}\n{grund}")
    pfad.with_name(pfad.name + ".txt").write_text(f"(Transkript fehlgeschlagen: {grund})", encoding="utf-8")


def lauf() -> None:
    liste = offene(ZIEL)
    if not liste:
        return
    from faster_whisper import WhisperModel
    modell = WhisperModel(MODELL, device="cpu", compute_type="int8", cpu_threads=4, download_root=str(MODELLE))
    for pfad in liste:
        rel = pfad.relative_to(ZIEL)
        if versuche(VERSUCHE_DATEI, str(rel)) >= MAX_VERSUCHE:
            logger.error("Aufgegeben nach %d abgebrochenen Versuchen: %s", MAX_VERSUCHE, rel)
            aufgeben(pfad, rel, f"{MAX_VERSUCHE} Versuche ohne Ergebnis abgebrochen (z. B. Speicher). "
                                "Für einen neuen Versuch die .txt löschen.")
            versuch_vergessen(VERSUCHE_DATEI, str(rel))
            continue
        sekunden = dauer(pfad)
        if not passt_noch(sekunden, datetime.now()):
            logger.info("Pause bis zur nächsten Nacht, offen: %d Datei(en)", len(offene(ZIEL)))
            return
        logger.info("Transkribiere %s (%.0f min)", rel, sekunden / 60)
        versuch_merken(VERSUCHE_DATEI, str(rel))
        start = time.time()
        try:
            transkribieren(pfad, modell)
        except Exception as f:  # noqa: BLE001 – Jan erfährt es, die übrigen Dateien laufen weiter
            logger.exception("Transkript fehlgeschlagen: %s", rel)
            aufgeben(pfad, rel, str(f))
            versuch_vergessen(VERSUCHE_DATEI, str(rel))
            continue
        versuch_vergessen(VERSUCHE_DATEI, str(rel))
        logger.info("Fertig in %.0f min", (time.time() - start) / 60)
        meldungen.melden(AGENT, f"Aufzeichnung transkribiert: {rel}\nText: {rel}.txt")


if __name__ == "__main__":
    lauf()
