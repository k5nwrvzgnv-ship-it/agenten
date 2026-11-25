"""Fertige Datensätze auf dem Mac (datensaetze/*, YOLO-seg) für die Kette: erkennen, zählen, Kodytek-Auswahl ziehen.
Nur Bordmittel. Die Originale werden nur gelesen, der Test-Teil wird nie angefasst."""

import os
import random
import re
from collections import Counter
from pathlib import Path

QUELLE = "kodytek-seg-1"              # daraus kommt die Auswahl zum Korrigieren
ANZAHL = {"train": 400, "val": 100}
JE_KLASSE = {"train": 40, "val": 10}  # so viele Bilder je Klasse zuerst, seltene Klassen vor häufigen
BILDER = {".bmp", ".jpg", ".jpeg", ".png"}


def klassen_gelesen(data_yaml: Path) -> list[str]:
    """Klassennamen aus einem data.yaml in der Form, die datensatz.py und bilder.py schreiben."""
    text = data_yaml.read_text(encoding="utf-8")
    block = text.split("names:", 1)[1] if "names:" in text else ""
    paare = re.findall(r"^ +(\d+): *([A-Za-z_]+)\s*$", block, re.M)
    return [n for i, (nr, n) in enumerate(paare) if int(nr) == i]


def ist_seg(ordner: Path) -> bool:
    """Umrisse (mehr als fünf Werte je Zeile) statt Boxen: erste nicht leere Labeldatei entscheidet."""
    for p in (ordner / "labels" / "train").glob("*.txt"):
        if zeile := p.read_text(encoding="utf-8").strip():
            return len(zeile.splitlines()[0].split()) > 5
    return False


def bilder_in(ordner: Path, teil: str) -> list[Path]:
    weg = ordner / "images" / teil
    if not weg.is_dir():
        return []
    return sorted(Path(e.path) for e in os.scandir(weg) if os.path.splitext(e.name)[1].lower() in BILDER)


def label_zu(bild: Path) -> Path:
    return bild.parents[2] / "labels" / bild.parent.name / f"{bild.stem}.txt"


def objekte_aus(text: str) -> list[dict]:
    """YOLO-seg-Zeilen als Objekte des Labelns, ungeprüft (ok = falsch)."""
    ergebnis = []
    for zeile in text.splitlines():
        w = zeile.split()
        if len(w) < 7:
            continue
        z = [min(1.0, max(0.0, float(x))) for x in w[1:]]
        ergebnis.append({"k": int(w[0]), "ok": False, "p": [[z[i], z[i + 1]] for i in range(0, len(z) - 1, 2)]})
    return ergebnis


def zeilen_aus(objekte: list[dict]) -> str:
    return "".join(f"{o['k']} " + " ".join(f"{x:.6f} {y:.6f}" for x, y in o["p"]) + "\n" for o in objekte)


def ziehen(klassen_je_bild: dict[str, set[int]], anzahl: int, je_klasse: int, seed: int = 20261125) -> list[str]:
    """Reproduzierbare Auswahl: je Klasse bis zu je_klasse Bilder, seltenste zuerst, Rest zufällig."""
    namen = sorted(klassen_je_bild)
    random.Random(seed).shuffle(namen)
    haeufig = Counter(k for ks in klassen_je_bild.values() for k in ks)
    wahl: dict[str, None] = {}
    for k, _ in sorted(haeufig.items(), key=lambda x: (x[1], x[0])):
        da = sum(k in klassen_je_bild[n] for n in wahl)
        for n in namen:
            if da >= je_klasse or len(wahl) >= anzahl:
                break
            if k in klassen_je_bild[n] and n not in wahl:
                wahl[n] = None
                da += 1
    for n in namen:
        if len(wahl) >= anzahl:
            break
        wahl.setdefault(n)
    return list(wahl)


def auswahl_ziehen(quelle: Path) -> list[dict]:
    ergebnis = []
    for teil, n in ANZAHL.items():
        je, orte = {}, {}
        for b in bilder_in(quelle, teil):
            t = label_zu(b)
            if t.exists():
                je[b.stem] = {int(z.split()[0]) for z in t.read_text(encoding="utf-8").splitlines() if z.strip()}
                orte[b.stem] = b
        ergebnis += [{"name": f"kodytek_{s}", "teil": teil, "bild": str(orte[s])}
                     for s in ziehen(je, n, JE_KLASSE[teil])]
    return ergebnis


def gefunden(wurzel: Path, klassen: list[str]) -> list[Path]:
    """Datensätze, die sich verbinden lassen: Umrisse und dieselbe Klassenzählung. Eigene Läufe (altholz-N) nicht."""
    ergebnis = []
    for y in sorted((wurzel / "datensaetze").glob("*/data.yaml")):
        namen = klassen_gelesen(y)
        if not y.parent.name.startswith("altholz-") and namen and namen == klassen[:len(namen)] and ist_seg(y.parent):
            ergebnis.append(y.parent)
    return ergebnis
