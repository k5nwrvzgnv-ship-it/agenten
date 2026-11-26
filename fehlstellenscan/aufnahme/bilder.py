"""Bildrechnung der Kette, läuft in der Trainings-.venv (Pillow, numpy, opencv, kein ultralytics):
  python bilder.py schneiden <Foto> <Ziel.jpg> <klein.jpg> <Zuschnitt als JSON>
  python bilder.py bauen <Auftrag.json>       Auftrag schreibt kette.py"""

import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

KACHEL = 1280
UEBERLAPPUNG = 256
MIN_PX = 2


def schneiden(quelle: Path, ziel: Path, klein: Path, zuschnitt: list[float] | None) -> None:
    """Wie die Aufnahme-Oberfläche: EXIF-Lage anwenden, hochkant nach rechts legen, dann auf Anteile zuschneiden."""
    with Image.open(quelle) as roh:
        bild = ImageOps.exif_transpose(roh).convert("RGB")
    if bild.height > bild.width:
        bild = bild.transpose(Image.Transpose.ROTATE_270)
    x, y, b, h = zuschnitt or (0, 0, 1, 1)
    w, H = bild.size
    bild = bild.crop((round(x * w), round(y * H), min(w, round((x + b) * w)), min(H, round((y + h) * H))))
    vorlaeufig = ziel.with_suffix(".tmp")
    bild.save(vorlaeufig, "JPEG", quality=95)
    vorlaeufig.replace(ziel)
    bild.thumbnail((320, 320))
    bild.save(klein, "JPEG", quality=85)


def raster(laenge: int) -> list[int]:
    """Anfänge der Kacheln entlang einer Bildseite, lückenlos mit mindestens UEBERLAPPUNG."""
    if laenge <= KACHEL:
        return [0]
    n = -(-(laenge - UEBERLAPPUNG) // (KACHEL - UEBERLAPPUNG))
    return [round(i * (laenge - KACHEL) / (n - 1)) for i in range(n)]


def zeilen(objekte: list[dict], groesse: tuple[int, int], x0: int, y0: int, b: int, h: int) -> list[str]:
    """YOLO-seg-Zeilen der Objekte in einer Kachel. Objekte werden einzeln gemalt, damit sich berührende gleicher
    Klasse getrennt bleiben; am Kachelrand geteilte Stücke werden eigene Objekte."""
    ergebnis = []
    for o in objekte:
        p = np.array(o["p"]) * groesse - (x0, y0)
        if p[:, 0].max() < 0 or p[:, 1].max() < 0 or p[:, 0].min() > b or p[:, 1].min() > h:
            continue
        maske = np.zeros((h, b), np.uint8)
        cv2.fillPoly(maske, [np.round(p).astype(np.int32)], 1)
        for k in cv2.findContours(maske, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
            _, _, kb, kh = cv2.boundingRect(k)
            if len(k) < 3 or kb < MIN_PX or kh < MIN_PX:
                continue
            ergebnis.append(f"{o['k']} " + " ".join(f"{q[0][0] / b:.6f} {q[0][1] / h:.6f}" for q in k))
    return ergebnis


def bauen(auftrag: dict) -> dict:
    ziel = Path(auftrag["ziel"])
    if ziel.exists():
        raise FileExistsError(f"{ziel} gibt es schon, nichts überschrieben")
    zahl: dict = {"pruefung": auftrag["pruefung"], "kacheln": Counter(), "objekte": Counter(), "balken": {},
                  "saetze": auftrag.get("saetze", ["altholz"])}
    for t in ("train", "val"):
        (ziel / "images" / t).mkdir(parents=True)
        (ziel / "labels" / t).mkdir(parents=True)
    altholz_val = []
    for e in auftrag["bilder"]:
        zahl["balken"][e["balken"]] = e["teil"]
        with Image.open(e["bild"]) as roh:
            bild = roh.convert("RGB")
        for y0 in raster(bild.height):
            for x0 in raster(bild.width):
                b, h = min(KACHEL, bild.width), min(KACHEL, bild.height)
                z = zeilen(e["objekte"], bild.size, x0, y0, b, h)
                name = f"{e['name']}_x{x0:05d}_y{y0:05d}"
                bild.crop((x0, y0, x0 + b, y0 + h)).save(ziel / "images" / e["teil"] / f"{name}.jpg", quality=95)
                (ziel / "labels" / e["teil"] / f"{name}.txt").write_text("".join(s + "\n" for s in z))
                zahl["kacheln"][e["teil"]] += 1
                zahl["objekte"].update(auftrag["klassen"][int(s.split()[0])] for s in z)
                if e["teil"] == "val":
                    altholz_val.append(str(ziel / "images" / "val" / f"{name}.jpg"))
    for e in auftrag.get("ganze", []):      # ganze Bilder mit fertigem Label (Kodytek), nicht gekachelt
        quelle = Path(e["bild"])
        bild = ziel / "images" / e["teil"] / f"{e['name']}{quelle.suffix}"
        try:
            os.link(quelle, bild)           # kein zusätzlicher Platz
        except OSError:
            shutil.copyfile(quelle, bild)
        (ziel / "labels" / e["teil"] / f"{e['name']}.txt").write_text(e["label"])
        zahl["kacheln"][e["teil"]] += 1
        zahl["objekte"].update(auftrag["klassen"][int(z.split()[0])] for z in e["label"].splitlines() if z.strip())
    wege = {t: f"images/{t}" for t in ("train", "val")}
    for t, dazu in auftrag.get("dazu", {}).items():
        if dazu:                            # eigene Bilder zuerst: ultralytics legt seinen Labelspeicher daneben ab
            eigen = sorted(str(p) for p in (ziel / "images" / t).iterdir())
            (ziel / f"{t}.txt").write_text("".join(x + "\n" for x in eigen + dazu))
            wege[t] = f"{t}.txt"
            zahl["kacheln"][t] += len(dazu)
            zahl["dazu_" + t] = len(dazu)
    (ziel / "data.yaml").write_text(f"path: {json.dumps(str(ziel))}\ntrain: {wege['train']}\nval: {wege['val']}\nnames:\n" + "".join(
        f"  {i}: {n}\n" for i, n in enumerate(auftrag["klassen"])))
    if altholz_val and zahl["kacheln"]["val"] > len(altholz_val):
        # Prüfung mischt Altholz mit anderen Sätzen: eigene Prüfliste nur für Altholz, kette.py prüft best.pt damit
        (ziel / "val_altholz.txt").write_text("".join(x + "\n" for x in altholz_val))
        (ziel / "altholz.yaml").write_text(f"path: {json.dumps(str(ziel))}\ntrain: {wege['train']}\nval: val_altholz.txt\n"
                                           "names:\n" + "".join(f"  {i}: {n}\n" for i, n in enumerate(auftrag["klassen"])))
        zahl["altholz_val"] = len(altholz_val)
    (ziel / "bericht.json").write_text(json.dumps(zahl, ensure_ascii=False, indent=1))
    return zahl


if __name__ == "__main__":
    if sys.argv[1] == "schneiden":
        schneiden(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), json.loads(sys.argv[5]))
    else:
        print(bauen(json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))))
