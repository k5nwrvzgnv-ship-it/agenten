"""Agent holzbalkenscan: Prüfstand für das fremde Verfahren in verfahren/.

Ein Lauf je Auftrag (agentkit.auftraege), ohne Timer und ohne Claude:
1. Speicher prüfen (MemAvailable gegen Grenze + Reserve). Reicht er nicht: Auftrag fehlgeschlagen, nichts gerechnet.
2. Je Reihe aus data/reihen/ (oder den im Auftrag genannten) pruefen.py und zusammensetzen2.py, jeder Schritt in
   einem eigenen systemd-Scope mit MemoryMax: wird er zu groß, bricht nur er ab.
3. Kennzahlen auslesen, data/laeufe/<lauf-id>/lauf.json schreiben, mit Vorlauf bzw. Referenz vergleichen.
4. Ergebnis als Meldung an Jan (agentkit.meldungen), Auftrag kurz abschließen.

Im Auftragstext: Reihennamen (sonst alle), "speicher 4G" (sonst SPEICHER_STANDARD), "fassung neu" (verfahren_neu/
statt verfahren/; verglichen wird dann mit dem letzten Lauf der alten Fassung).
"""

import fcntl
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import kennzahlen
import pruefstand

AGENT = "holzbalkenscan"
HIER = Path(__file__).resolve().parent
VERFAHREN = HIER / "verfahren"
VERFAHREN_NEU = HIER / "verfahren_neu"
DATEN = HIER / "data"
SPEICHER_STANDARD = "3G"  # geschätzt, bis ein echter Lauf die Spitze gemessen hat
ZEITGRENZE_S = 60 * 60    # je Schritt


def schritt_ausfuehren(cmd: list[str], cwd: Path, ausgabe: Path, zeitgrenze_s: float) -> dict:
    """Startet cmd, Ausgabe in die Datei. Gibt exit, dauer_s, spitze_mb (größter Speicher) und zeit_um zurück."""
    t0 = time.monotonic()
    with open(ausgabe, "wb") as aus:
        p = subprocess.Popen(cmd, cwd=cwd, stdout=aus, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        zeit_um = threading.Event()

        def abbrechen():
            zeit_um.set()
            p.kill()

        timer = threading.Timer(zeitgrenze_s, abbrechen)
        timer.start()
        try:
            _, status, nutzung = os.wait4(p.pid, 0)  # wait4 liefert die Speicherspitze genau dieses Prozesses
        finally:
            timer.cancel()
    p.returncode = os.waitstatus_to_exitcode(status)
    return {"exit": p.returncode, "dauer_s": round(time.monotonic() - t0, 1),
            "spitze_mb": nutzung.ru_maxrss // 1024, "zeit_um": zeit_um.is_set()}


def reihe_rechnen(lid: str, reihe: Path, ziel: Path, grenze: str, verfahren: Path = VERFAHREN,
                  befehl=pruefstand.befehl, python: str = sys.executable,
                  zeitgrenze_s: float = ZEITGRENZE_S) -> dict:
    """Beide Schritte für eine Reihe, Ergebnis wie in pruefstand beschrieben."""
    ziel.mkdir(parents=True, exist_ok=True)
    vor_txt, streifen = ziel / "vorpruefung.txt", ziel / "streifen.jpg"
    zus_txt = streifen.with_suffix(".txt")
    plan = [
        ("vorpruefung", "pruefen.py", [str(reihe), "--bericht", str(vor_txt)], vor_txt, kennzahlen.aus_vorpruefung),
        ("zusammenbau", "zusammensetzen2.py", [str(reihe), "--ziel", str(streifen)], zus_txt,
         kennzahlen.aus_zusammenbau),
    ]
    erg = {"schritte": {}, "unvollstaendig": pruefstand.unvollstaendige_fotos(reihe)}
    for schritt, skript, argumente, bericht, auslesen in plan:
        cmd = befehl(python, verfahren / skript, argumente, grenze, pruefstand.scope_name(lid, reihe.name, schritt))
        s = schritt_ausfuehren(cmd, ziel, ziel / f"{schritt}.ausgabe.txt", zeitgrenze_s)
        s["status"] = pruefstand.schritt_status(schritt, s["exit"], s.pop("zeit_um"), bericht.is_file())
        erg["schritte"][schritt] = s
        # Ohne Bericht (Abbruch, etwa an der Speichergrenze) die Konsolenausgabe lesen: Sie enthält dieselben
        # Zeilen bis zum Abbruch, und gerade gescheiterte Läufe sollen ihre Zuordnungszahlen zeigen.
        quelle = bericht if bericht.is_file() else ziel / f"{schritt}.ausgabe.txt"
        erg[schritt] = auslesen(quelle.read_text(encoding="utf-8", errors="replace")) if quelle.is_file() else {}
    erg["status"] = pruefstand.reihe_status(erg["schritte"])
    return erg


def lauf(text: str, auftrag_id: str | None, daten: Path = DATEN, jetzt: datetime | None = None,
         verfahren_neu: Path = VERFAHREN_NEU, **rechnen) -> tuple[dict, str]:
    """Rechnet die gewählten Reihen, speichert lauf.json und gibt (lauf, Meldetext) zurück."""
    jetzt = jetzt or datetime.now()
    lid = pruefstand.lauf_id(jetzt)
    reihen_dir, laeufe = daten / "reihen", daten / "laeufe"
    reihen = pruefstand.auswahl(text, pruefstand.reihen_finden(reihen_dir))
    grenze = pruefstand.speicher_aus_text(text, SPEICHER_STANDARD)
    lauf_dir = laeufe / lid
    fassung = pruefstand.fassung_aus_text(text)
    if fassung == "neu":
        rechnen["verfahren"] = verfahren_neu
    ergebnis = {"id": lid, "zeit": jetzt.isoformat(timespec="seconds"), "fassung": fassung,
                "code": pruefstand.codefassung(rechnen.get("verfahren", VERFAHREN)),
                "auftrag": auftrag_id, "speicher": grenze, "reihen": {}}
    for name in reihen:
        ergebnis["reihen"][name] = reihe_rechnen(lid, reihen_dir / name, lauf_dir / name, grenze, **rechnen)
        pruefstand.speichern(lauf_dir, ergebnis)  # nach jeder Reihe, damit ein Abbruch nichts verliert
    pruefstand.speichern(lauf_dir, ergebnis)
    vergleiche = {n: pruefstand.basis(laeufe, daten / "referenz", lid, n, fassung) for n in reihen}
    return ergebnis, pruefstand.meldetext(ergebnis, vergleiche)


def kurzfassung(ergebnis: dict) -> str:
    reihen = ergebnis["reihen"]
    if not reihen:
        return f"Lauf {ergebnis['id']}: keine Reihe in data/reihen gefunden."
    stand = ", ".join(f"{n}: {e['status']}" for n, e in reihen.items())
    return (f"Lauf {ergebnis['id']} (Fassung {ergebnis.get('fassung', 'alt')}, Code {ergebnis['code']}) fertig, "
            f"{stand}. Kennzahlen kommen als Meldung.")


def main() -> int:
    from agentkit import auftraege, log, meldungen

    logger = log.hole_logger(HIER, AGENT)
    DATEN.mkdir(exist_ok=True)
    with open(DATEN / "lauf.sperre", "w") as sperre:
        try:
            fcntl.flock(sperre, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.info("Ein anderer Lauf ist aktiv, Aufträge warten")
            return 0
        for a in auftraege.neue(AGENT):
            grenze = pruefstand.speicher_aus_text(a["text"], SPEICHER_STANDARD)
            ok, grund = pruefstand.genug_speicher(Path("/proc/meminfo").read_text(), grenze)
            if not ok:
                logger.warning("Auftrag %s nicht gerechnet: %s", a["id"], grund)
                auftraege.abschliessen(a["id"], f"Nicht gerechnet: {grund}. Später neu beauftragen.",
                                       status="fehlgeschlagen")
                continue
            logger.info("Auftrag %s: Lauf mit Grenze %s (%s)", a["id"], grenze, grund)
            try:
                ergebnis, text = lauf(a["text"], a["id"])
            except Exception as f:  # noqa: BLE001 – Jan soll jeden Abbruch erfahren
                logger.exception("Lauf zu %s abgebrochen", a["id"])
                auftraege.abschliessen(a["id"], f"Lauf abgebrochen: {f}", status="fehlgeschlagen")
                continue
            meldungen.melden(AGENT, text)
            auftraege.abschliessen(a["id"], kurzfassung(ergebnis))
    return 0


if __name__ == "__main__":
    sys.exit(main())
