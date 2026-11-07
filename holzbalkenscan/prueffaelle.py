"""Erschwerte Prüffälle aus einer gelungenen Reihe ableiten (Ersatz für fehlende echte Reihen).

Felix' Reihen 261019 B, 261019 C und 261022 V1 liegen nicht vor. Die Fälle hier ahmen die
Ursachen nach, an denen B und C laut verfahren/PROBLEMSTELLUNG.md gescheitert sind, und zwar
an den Fotos von Reihe A (ISO 800). Grundlage ist die Lage der Bauteilebene in jedem Bild aus
einem gelungenen Lauf des Verfahrens (streifen.modell.pkl: Hs = Ebene in mm -> Bildpixel,
His umgekehrt; v quer 0..Flächenhöhe, u längs).

    pf-luecke  P4: eine Aufnahme in der Mitte fehlt, die Nachbarn überlappen nur noch knapp.
    pf-schmal  B: halbe Fläche. Der Streifen v < SCHMAL_MM wird durch den Hintergrund davor
               ersetzt (Quelle v - SCHMAL_MM), die Fläche ist danach 230 - 115 = 115 mm hoch,
               der Bauteilanteil am Bild sinkt von 27 auf etwa 13 %.
    pf-flau    C: kaum Kantenkontrast. In 13 aufeinanderfolgenden Bildern wird der Hintergrund
               hinter der Kante v = Flächenhöhe je Farbkanal auf das Mittel des Holzes am Rand
               gezogen (plus FLAU_VERSATZ Graustufen); die Textur des Pflasters bleibt.

Grenzen: Die neue Kante bei pf-schmal ist eine gerade Naht im Bild, keine echte Bauteilkante;
in Endbildern, deren Kante das Modell um bis zu 20 mm verfehlt (IMG_2230, IMG_2255), ist sie
unsauber. Das Neuschreiben als JPEG (Qualität 95) ändert die Fotos minimal, auch in pf-luecke
nicht (dort werden die Originale verlinkt).

Aufruf (aus diesem Ordner, mit Speichergrenze):
    systemd-run --user --scope -q -p MemoryMax=1500M .venv/bin/python prueffaelle.py <lauf-ordner der Reihe>
"""

import json
import os
import pickle
import sys
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

HIER = Path(__file__).resolve().parent
QUELLE = HIER / "data" / "reihen" / "ISO 800"
ZIEL = HIER / "data" / "reihen"

LUECKE_BILD = "IMG_2242.jpg"
SCHMAL_MM = 115.0
FLAU_BILDER = [f"IMG_{n}.jpg" for n in range(2236, 2249)]
FLAU_VERSATZ = 5.0          # Graustufen; Reihe C: Unterkante 4,7
RAMPE_MM = 2.0              # Übergang an der Kante, damit kein Saum aus Mischpixeln bleibt
PROBE_MM = (3.0, 25.0)      # Abstand von der Kante, in dem die Mittel gemessen werden
BLOCK = 512                 # Zeilen je Rechenblock (Speicher)


# --- reine Rechnung ---------------------------------------------------------------------------

def abbilden(H: np.ndarray, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Homographie auf Koordinatenfelder anwenden."""
    w = H[2, 0] * x + H[2, 1] * y + H[2, 2]
    return (H[0, 0] * x + H[0, 1] * y + H[0, 2]) / w, (H[1, 0] * x + H[1, 1] * y + H[1, 2]) / w


def spiegeln(k: np.ndarray, n: int) -> np.ndarray:
    """Koordinaten außerhalb 0..n-1 an den Rand spiegeln (ohne Randpixel zu doppeln)."""
    p = 2 * (n - 1)
    k = np.mod(k, p)
    return np.where(k > n - 1, p - k, k)


def abtasten(bild: np.ndarray, xq: np.ndarray, yq: np.ndarray) -> np.ndarray:
    """Bilinear abtasten (bild H x W x C, uint8), Ränder gespiegelt. Ergebnis float32."""
    h, w = bild.shape[:2]
    xq = spiegeln(xq, w)
    yq = spiegeln(yq, h)
    x0 = np.clip(np.floor(xq).astype(np.int64), 0, w - 2)
    y0 = np.clip(np.floor(yq).astype(np.int64), 0, h - 2)
    fx = (xq - x0)[..., None].astype(np.float32)
    fy = (yq - y0)[..., None].astype(np.float32)
    a = bild[y0, x0].astype(np.float32)
    b = bild[y0, x0 + 1].astype(np.float32)
    c = bild[y0 + 1, x0].astype(np.float32)
    d = bild[y0 + 1, x0 + 1].astype(np.float32)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def schmal(bild: np.ndarray, H: np.ndarray, Hi: np.ndarray, schnitt_mm: float) -> np.ndarray:
    """Alles mit v < schnitt_mm durch den Hintergrund davor ersetzen (Quelle v - schnitt_mm)."""
    h, w = bild.shape[:2]
    aus = bild.copy()
    xs = np.arange(w, dtype=np.float64)
    for y0 in range(0, h, BLOCK):
        y, x = np.meshgrid(np.arange(y0, min(h, y0 + BLOCK), dtype=np.float64), xs, indexing="ij")
        u, v = abbilden(Hi, x, y)
        m = v < schnitt_mm
        if not m.any():
            continue
        xq, yq = abbilden(H, u[m], v[m] - schnitt_mm)
        blk = aus[y0:y0 + BLOCK]
        blk[m] = np.clip(np.rint(abtasten(bild, xq, yq)), 0, 255).astype(np.uint8)
    return aus


def kantenmittel(bild: np.ndarray, Hi: np.ndarray, kante_mm: float) -> tuple[np.ndarray, np.ndarray]:
    """Mittel je Farbkanal innen (Holz) und außen (Hintergrund) in PROBE_MM Abstand von v = kante_mm."""
    h, w = bild.shape[:2]
    y, x = np.mgrid[0:h:8, 0:w:8].astype(np.float64)
    _, v = abbilden(Hi, x, y)
    probe = bild[::8, ::8].astype(np.float64)
    innen = (v > kante_mm - PROBE_MM[1]) & (v < kante_mm - PROBE_MM[0])
    aussen = (v > kante_mm + PROBE_MM[0]) & (v < kante_mm + PROBE_MM[1])
    if innen.sum() < 50 or aussen.sum() < 50:
        raise ValueError("Kante liegt nicht im Bild")
    return probe[innen].mean(axis=0), probe[aussen].mean(axis=0)


def flau(bild: np.ndarray, Hi: np.ndarray, kante_mm: float, versatz: float) -> tuple[np.ndarray, float, float]:
    """Hintergrund hinter v = kante_mm auf das Holzmittel ziehen. Gibt (Bild, Kontrast vorher, nachher)."""
    innen, aussen = kantenmittel(bild, Hi, kante_mm)
    ziel = innen + versatz * np.sign((aussen - innen).mean() or 1.0)
    schub = ziel - aussen
    h, w = bild.shape[:2]
    aus = bild.copy()
    xs = np.arange(w, dtype=np.float64)
    for y0 in range(0, h, BLOCK):
        y, x = np.meshgrid(np.arange(y0, min(h, y0 + BLOCK), dtype=np.float64), xs, indexing="ij")
        _, v = abbilden(Hi, x, y)
        g = np.clip((v - kante_mm) / RAMPE_MM, 0.0, 1.0)[..., None]
        if not g.any():
            continue
        blk = aus[y0:y0 + BLOCK].astype(np.float32) + g * schub.astype(np.float32)
        aus[y0:y0 + BLOCK] = np.clip(np.rint(blk), 0, 255).astype(np.uint8)
    nach_i, nach_a = kantenmittel(aus, Hi, kante_mm)
    grau = np.array([0.299, 0.587, 0.114])
    return aus, float(abs((aussen - innen) @ grau)), float(abs((nach_a - nach_i) @ grau))


def bauteil_fuer(daten: dict, fall: str) -> dict:
    """bauteil.json des Prüffalls aus der der Quelle."""
    d = dict(daten)
    d["bauteil"] = f"{daten.get('bauteil', '')} (Prüffall {fall}, abgeleitet)".strip()
    if fall == "pf-schmal":
        h = float(daten["flaeche_hoehe_mm"]) - SCHMAL_MM
        d["flaeche_hoehe_mm"] = h
        d["flaeche_hoehe_mm_gemessen"] = [h, h, h]
        d["lamellen"] = None
    return d


# --- Dateien ----------------------------------------------------------------------------------

def _schreiben(pfad: Path, arr: np.ndarray, exif: bytes | None) -> None:
    Image.fromarray(arr).save(pfad, quality=95, subsampling=0, **({"exif": exif} if exif else {}))


def erzeugen(lauf_reihe: Path, quelle: Path = QUELLE, ziel: Path = ZIEL) -> dict:
    with open(lauf_reihe / "streifen.modell.pkl", "rb") as fh:
        Z = pickle.load(fh)
    if Z["dreh"]:
        raise ValueError("Modell mit gedrehter Achse wird nicht unterstützt")
    modell = {b["name"]: (Z["Hs"][k], Z["His"][k]) for k, b in enumerate(Z["bilder"])}
    daten = json.loads((quelle / "bauteil.json").read_text(encoding="utf-8"))
    hoehe = float(daten["flaeche_hoehe_mm"])
    fotos = sorted(p for p in quelle.iterdir() if p.suffix.lower() == ".jpg")
    protokoll = {}
    for fall in ("pf-luecke", "pf-schmal", "pf-flau"):
        d = ziel / fall
        d.mkdir(parents=True, exist_ok=True)
        notiz = {"quelle": str(quelle), "modell": str(lauf_reihe / "streifen.modell.pkl"), "bilder": {}}
        for p in fotos:
            z = d / p.name
            if fall == "pf-luecke":
                if p.name != LUECKE_BILD and not z.exists():
                    os.link(p, z)
                continue
            if fall == "pf-flau" and p.name not in FLAU_BILDER:
                if not z.exists():
                    os.link(p, z)
                continue
            if p.name not in modell:
                raise ValueError(f"{p.name} fehlt im Modell")
            H, Hi = modell[p.name]
            with Image.open(p) as im:
                exif = im.info.get("exif")
                arr = np.asarray(im.convert("RGB"))
            if fall == "pf-schmal":
                _schreiben(z, schmal(arr, H, Hi, SCHMAL_MM), exif)
            else:
                neu, vor, nach = flau(arr, Hi, hoehe, FLAU_VERSATZ)
                _schreiben(z, neu, exif)
                notiz["bilder"][p.name] = {"kontrast_vorher": round(vor, 1), "kontrast_nachher": round(nach, 1)}
            print(f"{fall}: {p.name}", flush=True)
        (d / "bauteil.json").write_text(json.dumps(bauteil_fuer(daten, fall), ensure_ascii=False, indent=1),
                                        encoding="utf-8")
        (d / "herkunft.json").write_text(json.dumps(notiz, ensure_ascii=False, indent=1), encoding="utf-8")
        protokoll[fall] = notiz
    return protokoll


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    erzeugen(Path(sys.argv[1]))
