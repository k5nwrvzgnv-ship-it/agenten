"""Masken von Kodytek et al. (Semantic Maps) in YOLO-seg-Polygone umwandeln und prüfen.

Läuft auf dem Server (3 Probemasken) und von Hand auf Jans Mac (alle Masken). Braucht numpy, Pillow,
opencv und datensatz.py im selben Ordner; kein agentkit, kein PyTorch.

Befehle (Einzelheiten mit --help, Anleitung in STATUS.md):
  ansehen     Farben einiger Masken zählen: Hintergrund, bekannte und unbekannte Farben
  bauen       Seg-Datensatz aus einem Box-Datensatz (gleiche Bilder und Aufteilung, Hardlinks) und den Masken
  gegenprobe  Objekte je Teil und Klasse gegen den Box-Datensatz zählen, Abweichungen je Bild
  zeichnen    Polygone (farbig) und Boxen (weiß) ins Bild zeichnen, als PNG

Masken: <nummer>_segm.bmp, RGB, Hintergrund schwarz, je Klasse eine feste Farbe (Semantic Map Specification).
Quelle der Masken ist das ZIP (jede Maske einzeln im Speicher gelesen, nie ganz entpacken, 174 GB) oder ein
Ordner mit einzelnen Masken. Jeder zusammenhängende Fleck einer Farbe wird ein Objekt.
"""

import argparse
import io
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np

import datensatz as d

# Farben der Semantic Map Specification in der Reihenfolge der festen Klassennummern (datensatz.KLASSEN).
FARBEN = ["00FF00", "FF0000", "FF6400", "FFAF00", "FF0064", "640064", "FF00FF", "0000FF", "10FFFF", "004000"]
HINTERGRUND = 0                          # schwarz
KLASSE_VON = {int(f, 16): k for k, f in enumerate(FARBEN)}
assert len(FARBEN) == len(d.KLASSEN)


# ---------------------------------------------------------------- Umwandeln (reine Logik)

def farbschluessel(rgb: np.ndarray) -> np.ndarray:
    """H x W x 3 (uint8) -> H x W (int32) mit 0xRRGGBB, damit jede Farbe ein einziger Wert ist."""
    rgb = rgb.astype(np.int32)
    return (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]


def farben_zaehlen(schluessel: np.ndarray) -> Counter:
    """Pixel je Farbe (0xRRGGBB), Hintergrund mitgezählt."""
    werte, anzahl = np.unique(schluessel, return_counts=True)
    return Counter({int(w): int(a) for w, a in zip(werte, anzahl, strict=True)})


def farbname(wert: int) -> str:
    return f"{wert:06X}"


def flecken(schluessel: np.ndarray, min_px: float) -> dict:
    """Alle Flecken einer Maske als Polygone in Pixelmitten (x + 0,5, y + 0,5).

    Ergebnis: objekte [(klasse, punkte N x 2)], klein [(klasse, breite, hoehe)] unter min_px in einer Richtung,
    linie [(klasse, breite, hoehe)] ohne Fläche (Polygon aus weniger als 3 Punkten oder Fläche 0, z. B. ein
    1 px breiter schräger Riss), unbekannt {farbe: pixel}, loecher {klasse: anzahl} (YOLO-Polygone haben keine
    Löcher, der Fleck wird voll ausgemalt)."""
    import cv2
    vordergrund = schluessel[schluessel != HINTERGRUND]
    werte = np.unique(vordergrund) if vordergrund.size else np.array([], np.int32)
    ergebnis = {"objekte": [], "klein": [], "linie": [], "unbekannt": {}, "loecher": Counter()}
    for wert in (int(w) for w in werte):
        if wert not in KLASSE_VON:
            ergebnis["unbekannt"][farbname(wert)] = int(np.count_nonzero(vordergrund == wert))
            continue
        klasse = KLASSE_VON[wert]
        binaer = (schluessel == wert).astype(np.uint8)
        konturen, hierarchie = cv2.findContours(binaer, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        for kontur, (_, _, _, eltern) in zip(konturen, hierarchie[0], strict=True):
            if eltern != -1:                 # innere Kontur = Loch in einem Fleck
                ergebnis["loecher"][klasse] += 1
                continue
            _, _, breite, hoehe = cv2.boundingRect(kontur)
            if breite < min_px or hoehe < min_px:
                ergebnis["klein"].append((klasse, breite, hoehe))
            elif len(kontur) < 3 or cv2.contourArea(kontur) == 0:
                ergebnis["linie"].append((klasse, breite, hoehe))
            else:
                ergebnis["objekte"].append((klasse, kontur.reshape(-1, 2).astype(np.float64) + 0.5))
    return ergebnis


def zu_yolo_seg(klasse: int, punkte: np.ndarray, breite: int, hoehe: int) -> str:
    """YOLO-seg-Zeile "klasse x1 y1 x2 y2 ...", normiert auf die echte Bildgröße."""
    return f"{klasse} " + " ".join(f"{x / breite:.6f} {y / hoehe:.6f}" for x, y in punkte)


def von_yolo_seg(zeile: str, breite: int, hoehe: int) -> tuple[int, np.ndarray]:
    """Umkehrung von zu_yolo_seg: (klasse, Punkte in Pixeln)."""
    teile = zeile.split()
    if len(teile) < 7 or len(teile) % 2 == 0:
        raise ValueError(f"keine YOLO-seg-Zeile (Klasse und mindestens 3 Punkte): {zeile[:60]!r}")
    werte = np.array([float(t) for t in teile[1:]]).reshape(-1, 2)
    if werte.min() < 0 or werte.max() > 1:
        raise ValueError(f"Punkte außerhalb 0..1: {zeile[:60]!r}")
    return int(teile[0]), werte * (breite, hoehe)


def label_klassen(text: str) -> Counter:
    """Objekte je Klasse in einer Label-Datei (Box oder seg, die erste Spalte ist die Klasse)."""
    return Counter(int(z.split()[0]) for z in text.splitlines() if z.strip())


# ---------------------------------------------------------------- Masken lesen

class Masken:
    """Masken aus dem ZIP (einzeln im Speicher) oder aus einem Ordner, Zugriff über die Bildnummer."""

    def __init__(self, quelle: Path):
        self.zip = None
        if quelle.is_dir():
            self.pfade = {p.name[:-len("_segm.bmp")]: p for p in quelle.rglob("*_segm.bmp")}
        else:
            self.zip = zipfile.ZipFile(quelle)
            self.pfade = {Path(i.filename).name[:-len("_segm.bmp")]: i
                          for i in self.zip.infolist() if i.filename.endswith("_segm.bmp")}

    def __contains__(self, nummer: str) -> bool:
        return nummer in self.pfade

    def __len__(self) -> int:
        return len(self.pfade)

    def nummern(self) -> list[str]:
        return sorted(self.pfade)

    def lesen(self, nummer: str) -> np.ndarray:
        """Maske als H x W x 3 (uint8, RGB)."""
        from PIL import Image
        if self.zip:
            daten = io.BytesIO(self.zip.read(self.pfade[nummer]))
        else:
            daten = self.pfade[nummer]
        with Image.open(daten) as bild:
            return np.asarray(bild.convert("RGB"))


# ---------------------------------------------------------------- Bauen

def bilder_im_datensatz(ordner: Path) -> dict[str, tuple[str, Path]]:
    """Bildnummer -> (Teil, Pfad) aus <ordner>/images/<teil>/<nummer>.bmp."""
    ergebnis = {}
    for teil in d.TEILE:
        for pfad in sorted((ordner / "images" / teil).glob("*.bmp")):
            ergebnis[pfad.stem] = (teil, pfad)
    return ergebnis


DATENKARTE = """# Datenkarte {name}

Quelle: {quelle}

- Gleiche Bilder und gleiche Aufteilung wie {vorlage} (Hardlinks), Labels aus den Masken (Semantic Maps).
- Je Klasse eine Farbe, Hintergrund schwarz. Jeder zusammenhängende Fleck einer Farbe ist ein Objekt
  (Polygon durch die Mitten der Randpixel). Löcher in Flecken werden mit ausgemalt (YOLO-seg kennt keine).
- Weggelassen: Flecken unter {min_px} px Breite oder Höhe (Klickfehler) und Flecken ohne Fläche (1 px breite
  Linien). Unbekannte Farben werden nicht umgewandelt. Alles einzeln in bericht.json.
- Klassen (feste Nummern): {klassen}
"""


def bauen(vorlage: Path, masken_quelle: Path, ziel: Path, min_px: float, nur_vorhandene: bool = False,
          probe: int = 0, kopieren: bool = False) -> dict:
    """Baut den Seg-Datensatz mit den Bildern und der Aufteilung der Vorlage (Box-Datensatz). Bricht ab, wenn
    das Ziel schon existiert oder (ohne nur_vorhandene) eine Maske fehlt. probe > 0: Überanpassungstest mit den
    ersten n train-Bildern, die Objekte haben, train = val."""
    if ziel.exists():
        raise FileExistsError(f"{ziel} gibt es schon, nichts überschrieben")
    bilder = bilder_im_datensatz(vorlage)
    if not bilder:
        raise FileNotFoundError(f"keine Bilder in {vorlage}/images/")
    masken = Masken(masken_quelle)
    fehlend = sorted(n for n in bilder if n not in masken)
    if fehlend and not nur_vorhandene:
        raise FileNotFoundError(f"{len(fehlend)} Masken fehlen, z. B. {fehlend[:5]}")

    for t in d.TEILE:
        (ziel / "images" / t).mkdir(parents=True)
        (ziel / "labels" / t).mkdir(parents=True)
    zaehlung = {t: {"bilder": 0, "ohne_fehler": 0, "objekte": Counter(), "bilder_je_klasse": Counter()}
                for t in d.TEILE}
    klein, linie, groesse_falsch = [], [], []
    unbekannt: dict[str, dict] = {}
    loecher: Counter = Counter()
    fertig = 0
    for nummer in sorted(bilder):
        if probe and fertig >= probe:
            break
        teil, bild = bilder[nummer]
        if nummer not in masken or (probe and teil != "train"):
            continue
        breite, hoehe = d.bildgroesse(bild)
        rgb = masken.lesen(nummer)
        if rgb.shape[:2] != (hoehe, breite):
            groesse_falsch.append({"nummer": nummer, "bild": [breite, hoehe], "maske": list(rgb.shape[1::-1])})
            continue
        f = flecken(farbschluessel(rgb), min_px)
        for farbe, pixel in f["unbekannt"].items():
            u = unbekannt.setdefault(farbe, {"pixel": 0, "bilder": []})
            u["pixel"] += pixel
            u["bilder"].append(nummer)
        for liste, ablage in ((f["klein"], klein), (f["linie"], linie)):
            ablage += [{"nummer": nummer, "klasse": d.KLASSEN[k], "breite_px": b, "hoehe_px": h}
                       for k, b, h in liste]
        loecher.update(d.KLASSEN[k] for k in f["loecher"].elements())
        if probe and not f["objekte"]:
            continue
        teil_ziel = "train" if probe else teil
        d.ablegen(bild, ziel / "images" / teil_ziel / f"{nummer}.bmp", kopieren)
        (ziel / "labels" / teil_ziel / f"{nummer}.txt").write_text(
            "".join(zu_yolo_seg(k, p, breite, hoehe) + "\n" for k, p in f["objekte"]), encoding="utf-8")
        z = zaehlung[teil_ziel]
        z["bilder"] += 1
        z["ohne_fehler"] += not f["objekte"]
        z["objekte"].update(d.KLASSEN[k] for k, _ in f["objekte"])
        z["bilder_je_klasse"].update({d.KLASSEN[k] for k, _ in f["objekte"]})
        fertig += 1

    pfad = str(ziel.resolve())
    (ziel / "data.yaml").write_text(
        d.data_yaml(pfad, val="images/train", test=None) if probe else d.data_yaml(pfad), encoding="utf-8")
    bericht = {
        "quelle": d.QUELLE,
        "vorlage": str(vorlage),
        "masken": masken_quelle.name,
        "min_px": min_px,
        "probe": probe,
        "klassen": d.KLASSEN,
        "teile": {t: {**z, "objekte": dict(z["objekte"]), "bilder_je_klasse": dict(z["bilder_je_klasse"])}
                  for t, z in zaehlung.items()},
        "unbekannte_farben": unbekannt,
        "klein": klein,
        "linie": linie,
        "loecher_ausgemalt": dict(loecher),
        "groesse_abweichend": groesse_falsch,
        "fehlende_masken": len(fehlend),
    }
    (ziel / "bericht.json").write_text(json.dumps(bericht, ensure_ascii=False, indent=1), encoding="utf-8")
    (ziel / "manifest.json").write_text(json.dumps({
        "git": d.git_stand(), "vorlage": str(vorlage.resolve()), "masken": str(masken_quelle.resolve()),
        "min_px": min_px, "kopieren": kopieren}, indent=1), encoding="utf-8")
    (ziel / "DATENKARTE.md").write_text(DATENKARTE.format(
        name=ziel.name, quelle=d.QUELLE, vorlage=vorlage.name, min_px=min_px,
        klassen=", ".join(f"{i} {k}" for i, k in enumerate(d.KLASSEN))), encoding="utf-8")
    return bericht


# ---------------------------------------------------------------- Gegenprobe und Zeichnen

def gegenprobe(seg: Path, boxen: Path) -> dict:
    """Objekte je Teil und Klasse in seg/labels gegen boxen/labels, dazu die Bilder mit Abweichung."""
    summen = {t: {"boxen": Counter(), "flecken": Counter()} for t in d.TEILE}
    je_bild = []
    for t in d.TEILE:
        for label in sorted((seg / "labels" / t).glob("*.txt")):
            box_datei = boxen / "labels" / t / label.name
            if not box_datei.exists():
                raise FileNotFoundError(f"{box_datei} fehlt (andere Aufteilung?)")
            f = label_klassen(label.read_text(encoding="utf-8"))
            b = label_klassen(box_datei.read_text(encoding="utf-8"))
            summen[t]["flecken"].update(f)
            summen[t]["boxen"].update(b)
            if f != b:
                je_bild.append({"teil": t, "nummer": label.stem, "abweichung": {
                    d.KLASSEN[k]: [b[k], f[k]] for k in sorted(set(f) | set(b)) if f[k] != b[k]}})
    tabelle = []
    for t in d.TEILE:
        for k, name in enumerate(d.KLASSEN):
            b, f = summen[t]["boxen"][k], summen[t]["flecken"][k]
            if b or f:
                tabelle.append({"teil": t, "klasse": name, "boxen": b, "flecken": f, "differenz": f - b})
    return {"tabelle": tabelle, "bilder_mit_abweichung": je_bild}


def zeichnen(seg: Path, boxen: Path | None, nummer: str, ausgabe: Path) -> Path:
    """Polygone in der Maskenfarbe (2 px), Boxen der Vorlage weiß (1 px), Klassennummer am Polygon."""
    import cv2
    funde = list(seg.glob(f"images/*/{nummer}.bmp"))
    if not funde:
        raise FileNotFoundError(f"Bild {nummer} nicht in {seg}/images/")
    bild_pfad = funde[0]
    teil = bild_pfad.parent.name
    bild = cv2.imread(str(bild_pfad), cv2.IMREAD_COLOR)
    hoehe, breite = bild.shape[:2]
    if boxen is not None:
        box_datei = boxen / "labels" / teil / f"{nummer}.txt"
        for zeile in box_datei.read_text(encoding="utf-8").splitlines() if box_datei.exists() else []:
            b = d.von_yolo(zeile)
            cv2.rectangle(bild, (round(b.x1 * breite), round(b.y1 * hoehe)),
                          (round(b.x2 * breite) - 1, round(b.y2 * hoehe) - 1), (255, 255, 255), 1)
    for zeile in (seg / "labels" / teil / f"{nummer}.txt").read_text(encoding="utf-8").splitlines():
        if not zeile.strip():
            continue
        klasse, punkte = von_yolo_seg(zeile, breite, hoehe)
        r, g, b = bytes.fromhex(FARBEN[klasse])
        ecken = np.round(punkte - 0.5).astype(np.int32)
        cv2.polylines(bild, [ecken], True, (b, g, r), 2)
        x, y = ecken.min(axis=0)
        cv2.putText(bild, str(klasse), (int(x), max(int(y) - 4, 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (b, g, r), 2)
    ausgabe.mkdir(parents=True, exist_ok=True)
    ziel = ausgabe / f"{nummer}_seg.png"
    if not cv2.imwrite(str(ziel), bild):
        raise OSError(f"{ziel} nicht geschrieben")
    return ziel


# ---------------------------------------------------------------- Befehle

def _ansehen(args) -> None:
    masken = Masken(args.masken)
    nummern = args.nummern or masken.nummern()[:args.anzahl]
    for nummer in nummern:
        if nummer not in masken:
            raise FileNotFoundError(f"Maske {nummer} nicht in {args.masken}")
        rgb = masken.lesen(nummer)
        farben = farben_zaehlen(farbschluessel(rgb))
        teile = []
        for wert, pixel in farben.most_common():
            name = ("Hintergrund" if wert == HINTERGRUND else
                    d.KLASSEN[KLASSE_VON[wert]] if wert in KLASSE_VON else "UNBEKANNT")
            teile.append(f"{farbname(wert)} {name} {pixel}")
        print(f"{nummer} {rgb.shape[1]}x{rgb.shape[0]}: " + ", ".join(teile))


def _bauen(args) -> None:
    bericht = bauen(args.vorlage, args.masken, args.ziel, args.min_px, nur_vorhandene=args.nur_vorhandene,
                    probe=args.probe, kopieren=args.kopieren)
    for t, z in bericht["teile"].items():
        print(f"{t}: {z['bilder']} Bilder, {z['ohne_fehler']} ohne Fehler, Objekte {z['objekte']}")
    print(f"klein {len(bericht['klein'])}, Linie {len(bericht['linie'])}, Löcher ausgemalt "
          f"{bericht['loecher_ausgemalt']}, Größe abweichend {len(bericht['groesse_abweichend'])}, "
          f"fehlende Masken {bericht['fehlende_masken']}")
    if bericht["unbekannte_farben"]:
        print("UNBEKANNTE FARBEN (nicht umgewandelt): " + ", ".join(
            f"{f} {u['pixel']} px in {len(u['bilder'])} Bildern" for f, u in bericht["unbekannte_farben"].items()))


def _gegenprobe(args) -> None:
    ergebnis = gegenprobe(args.seg, args.boxen)
    print(f"{'Teil':6} {'Klasse':16} {'Boxen':>7} {'Flecken':>8} {'Diff':>6}")
    for z in ergebnis["tabelle"]:
        print(f"{z['teil']:6} {z['klasse']:16} {z['boxen']:7} {z['flecken']:8} {z['differenz']:+6}")
    print(f"Bilder mit Abweichung: {len(ergebnis['bilder_mit_abweichung'])}")
    if args.ausgabe:
        args.ausgabe.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")


def _zeichnen(args) -> None:
    for nummer in args.nummern:
        print(zeichnen(args.seg, args.boxen, nummer, args.ausgabe))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="befehl", required=True)
    s = sub.add_parser("ansehen")
    s.add_argument("--masken", type=Path, required=True, help="Semantic Maps.zip oder Ordner mit _segm.bmp")
    s.add_argument("--anzahl", type=int, default=5)
    s.add_argument("nummern", nargs="*", help="bestimmte Bildnummern statt der ersten --anzahl")
    s.set_defaults(los=_ansehen)
    s = sub.add_parser("bauen")
    s.add_argument("--vorlage", type=Path, required=True, help="Box-Datensatz (Bilder und Aufteilung)")
    s.add_argument("--masken", type=Path, required=True, help="Semantic Maps.zip oder Ordner mit _segm.bmp")
    s.add_argument("--ziel", type=Path, required=True)
    s.add_argument("--min-px", type=float, default=d.MIN_PX)
    s.add_argument("--nur-vorhandene", action="store_true", help="Bilder ohne Maske überspringen")
    s.add_argument("--probe", type=int, default=0, help="Überanpassungstest: n train-Bilder, train = val")
    s.add_argument("--kopieren", action="store_true", help="Bilder kopieren statt Hardlink")
    s.set_defaults(los=_bauen)
    s = sub.add_parser("gegenprobe")
    s.add_argument("--seg", type=Path, required=True)
    s.add_argument("--boxen", type=Path, required=True, help="Box-Datensatz (Vorlage)")
    s.add_argument("--ausgabe", type=Path, help="Ergebnis als JSON (mit Abweichungen je Bild)")
    s.set_defaults(los=_gegenprobe)
    s = sub.add_parser("zeichnen")
    s.add_argument("--seg", type=Path, required=True)
    s.add_argument("--boxen", type=Path, help="Box-Datensatz: Boxen weiß dazuzeichnen")
    s.add_argument("--ausgabe", type=Path, required=True, help="Ordner für die PNGs")
    s.add_argument("nummern", nargs="+")
    s.set_defaults(los=_zeichnen)
    args = p.parse_args(argv)
    try:
        args.los(args)
    except (ValueError, FileExistsError, FileNotFoundError, OSError, zipfile.BadZipFile) as fehler:
        print(f"FEHLER: {fehler}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
