"""Masken von Kodytek et al. (Semantic Maps) in YOLO-seg-Polygone umwandeln und prüfen.

Läuft auf dem Server (3 Probemasken) und von Hand auf Jans Mac (alle Masken). Braucht numpy, Pillow,
opencv und datensatz.py im selben Ordner; kein agentkit, kein ultralytics (Vorhersagen kommen
als Textdateien von `yolo segment predict` auf dem Mac).

Befehle (Einzelheiten mit --help, Anleitung in STATUS.md):
  ansehen     Farben einiger Masken zählen: Hintergrund, bekannte und unbekannte Farben
  bauen       Seg-Datensatz aus einem Box-Datensatz (gleiche Bilder und Aufteilung, Hardlinks) und den Masken
  gegenprobe  Objekte je Teil und Klasse gegen den Box-Datensatz zählen, Abweichungen je Bild
  zeichnen    Masken der Markierung ins Bild zeichnen (ohne Boxen), als JPG
  gruppenbilder  Bilder für Menschen aus Markierung und Vorhersage des Modells: Vergleich, Umriss, Maße in mm

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


# Namen für Bilder, die Menschen ansehen (Gruppe, Vorträge); Reihenfolge wie datensatz.KLASSEN.
NAMEN_DE = ["Ast lebend", "Ast tot", "Astloch", "Ast mit Riss", "Riss", "Quartzity", "Harz", "Mark", "Bläue",
            "Überwallung"]
BREITE_BILD = 1600      # Breite der fertigen Bilder (Original 2800), reicht für Telegram und Folien


# Kodytek-Paper (Abschnitt Hardware): quer zum Brett (x, Kamerazeile) 16,66 px/mm, längs (y, Zeilen) 6,67 px/mm.
# Die Pixel sind also nicht quadratisch; Maße immer erst in mm umrechnen, dann messen.
PX_JE_MM = (16.66, 6.67)
ELLIPSE = (180, 255, 50)        # Farbe für Ellipse und Achsen im Maßbild (gut sichtbar auf Holz)
AESTE = {0, 1, 2, 3}            # live_knot, dead_knot, knot_missing, knot_with_crack: nur hier Maße (Ellipse)
# Schriften mit ß und ×: DejaVu auf dem Server, Arial auf dem Mac; sonst Pillows eingebaute (ohne diese Zeichen)
SCHRIFTEN = ("DejaVuSans.ttf", "Arial.ttf")


def objekte_aus_label(text: str, breite: int, hoehe: int) -> list[tuple[int, np.ndarray, float | None]]:
    """Label-Datei (YOLO-seg) als [(klasse, Punkte in Pixeln, None)], None = keine Konfidenz (Markierung)."""
    return [(*von_yolo_seg(z, breite, hoehe), None) for z in text.splitlines() if z.strip()]


def objekte_aus_vorhersage(text: str, breite: int, hoehe: int) -> list[tuple[int, np.ndarray, float | None]]:
    """Ausgabe von `yolo segment predict save_txt=True save_conf=True`: wie ein Label, die Konfidenz steht als
    letzte Zahl (dann ist die Anzahl der Werte gerade). Ohne save_conf ist die Konfidenz None."""
    objekte = []
    for zeile in text.splitlines():
        teile = zeile.split()
        if not teile:
            continue
        konfidenz = None
        if len(teile) % 2 == 0:
            konfidenz = float(teile[-1])
            teile = teile[:-1]
        objekte.append((*von_yolo_seg(" ".join(teile), breite, hoehe), konfidenz))
    return objekte


def masse_mm(punkte: np.ndarray, px_je_mm: tuple[float, float] = PX_JE_MM) -> dict | None:
    """Ellipse an den Umriss (Pixel) in mm angepasst: mitte, achsen (volle Durchmesser wie cv2), winkel (Grad),
    lang, kurz. None bei weniger als 5 Punkten (cv2.fitEllipse braucht 5)."""
    import cv2
    if len(punkte) < 5:
        return None
    mm = (np.asarray(punkte, dtype=np.float64) / px_je_mm).astype(np.float32)
    (cx, cy), (a, b), winkel = cv2.fitEllipse(mm)
    return {"mitte": (cx, cy), "achsen": (a, b), "winkel": winkel, "lang": max(a, b), "kurz": min(a, b)}


def ellipse_px(masse: dict, px_je_mm: tuple[float, float] = PX_JE_MM, schritte: int = 120) -> np.ndarray:
    """Umfang der Ellipse aus masse_mm zurück in Bildpixel (schritte x 2)."""
    (cx, cy), (a, b), w = masse["mitte"], masse["achsen"], np.radians(masse["winkel"])
    t = np.linspace(0, 2 * np.pi, schritte, endpoint=False)
    x = cx + a / 2 * np.cos(t) * np.cos(w) - b / 2 * np.sin(t) * np.sin(w)
    y = cy + a / 2 * np.cos(t) * np.sin(w) + b / 2 * np.sin(t) * np.cos(w)
    return np.stack([x, y], axis=1) * px_je_mm


def achsen_px(masse: dict, px_je_mm: tuple[float, float] = PX_JE_MM) -> list[np.ndarray]:
    """Die beiden Achsen der Ellipse als Strecken (2 x 2) in Bildpixeln."""
    (cx, cy), (a, b), w = masse["mitte"], masse["achsen"], np.radians(masse["winkel"])
    richtungen = [(a / 2 * np.cos(w), a / 2 * np.sin(w)), (-b / 2 * np.sin(w), b / 2 * np.cos(w))]
    return [np.array([[cx - dx, cy - dy], [cx + dx, cy + dy]]) * px_je_mm for dx, dy in richtungen]


def schrift(groesse: int):
    from PIL import ImageFont
    for name in SCHRIFTEN:
        try:
            return ImageFont.truetype(name, groesse)
        except OSError:
            continue
    return ImageFont.load_default(size=groesse)


def zahl(wert: float, stellen: int = 1) -> str:
    return f"{wert:.{stellen}f}".replace(".", ",")


def masken_bild(bild, objekte: list, titel: str, art: str = "flaeche"):
    """Masken ins Bild, ohne Boxen; oben ein Balken mit dem Titel. Ergebnis ist BREITE_BILD breit.
    art "flaeche": halbdurchsichtig mit Umriss, Name und ggf. Konfidenz. "umriss": nur dünner Umriss mit Name.
    "masse": dünner Umriss; bei Ästen dazu Ellipse mit Achsen und Länge × Breite der Ellipse in mm (bei langen
    Formen wie Rissen oder quartzity sagt eine Ellipse nichts, dort nur der Name).
    bild: PIL-Bild (RGB) in Originalgröße, objekte: [(klasse, Punkte in Pixeln, konfidenz oder None)]."""
    from PIL import Image, ImageDraw
    if art not in ("flaeche", "umriss", "masse"):
        raise ValueError(f"unbekannte Art {art!r}")
    massstab = BREITE_BILD / bild.width
    grund = bild.convert("RGBA").resize((BREITE_BILD, round(bild.height * massstab)), Image.LANCZOS)
    schicht = Image.new("RGBA", grund.size, (0, 0, 0, 0))
    zeichner = ImageDraw.Draw(schicht)
    font = schrift(28)
    texte = []
    for klasse, punkte, konfidenz in objekte:
        farbe = tuple(bytes.fromhex(FARBEN[klasse]))
        ecken = [tuple(p) for p in (punkte * massstab).tolist()]
        text = NAMEN_DE[klasse]
        if art == "flaeche":
            zeichner.polygon(ecken, fill=(*farbe, 90), outline=(*farbe, 255), width=3)
        else:
            zeichner.polygon(ecken, outline=(*farbe, 255), width=2 if art == "masse" else 3)
        if art == "masse" and klasse in AESTE:
            m = masse_mm(punkte)
            if m is not None:
                zeichner.polygon([tuple(p) for p in (ellipse_px(m) * massstab).tolist()],
                                 outline=(*ELLIPSE, 255), width=3)
                for strecke in achsen_px(m):
                    zeichner.line([tuple(p) for p in (strecke * massstab).tolist()], fill=(*ELLIPSE, 255), width=2)
                text += f": {zahl(m['lang'])} × {zahl(m['kurz'])} mm"
        elif konfidenz is not None:
            text += " " + zahl(konfidenz, 2)
        texte.append((text, farbe, punkte * massstab))
    for text, farbe, punkte in texte:           # Schrift zuletzt, damit keine Maske sie verdeckt
        links, oben, rechts, unten = zeichner.textbbox((0, 0), text, font=font)
        x, y = punkte.min(axis=0)
        x = min(max(x, 0), grund.width - rechts - 8)
        y = y - unten - 10 if y - unten - 10 >= 0 else punkte[:, 1].max() + 6
        # Feld in der Klassenfarbe, Schrift schwarz oder weiß: auch dunkle Farben (quartzity, overgrown) lesbar
        hell = 0.299 * farbe[0] + 0.587 * farbe[1] + 0.114 * farbe[2] > 140
        zeichner.rectangle((x, y, x + rechts + 8, y + unten + 6), fill=(*farbe, 230))
        zeichner.text((x + 4, y + 2), text, fill=(0, 0, 0, 255) if hell else (255, 255, 255, 255), font=font)
    fertig = Image.alpha_composite(grund, schicht).convert("RGB")
    kopf = Image.new("RGB", (fertig.width, 50), (30, 30, 30))
    ImageDraw.Draw(kopf).text((14, 8), titel, fill=(255, 255, 255), font=schrift(28))
    gesamt = Image.new("RGB", (fertig.width, kopf.height + fertig.height))
    gesamt.paste(kopf, (0, 0))
    gesamt.paste(fertig, (0, kopf.height))
    return gesamt


def uebereinander(bilder: list):
    """Bilder gleicher Breite untereinander, mit 6 px dunklem Abstand."""
    from PIL import Image
    gesamt = Image.new("RGB", (bilder[0].width, sum(b.height for b in bilder) + 6 * (len(bilder) - 1)), (30, 30, 30))
    y = 0
    for b in bilder:
        gesamt.paste(b, (0, y))
        y += b.height + 6
    return gesamt


def bild_laden(pfad: Path):
    from PIL import Image
    with Image.open(pfad) as b:
        return b.convert("RGB")


def zeichnen(seg: Path, nummer: str, ausgabe: Path) -> Path:
    """Markierung (Masken aus den Labels eines Seg-Datensatzes) als JPG, zum Prüfen der Umwandlung."""
    funde = sorted(seg.glob(f"images/*/{nummer}.bmp"))
    if not funde:
        raise FileNotFoundError(f"Bild {nummer} nicht in {seg}/images/")
    bild = bild_laden(funde[0])
    label = seg / "labels" / funde[0].parent.name / f"{nummer}.txt"
    ausgabe.mkdir(parents=True, exist_ok=True)
    ziel = ausgabe / f"{nummer}_masken.jpg"
    masken_bild(bild, objekte_aus_label(label.read_text(encoding="utf-8"), *bild.size), "Markierung").save(
        ziel, quality=90)
    return ziel


def gruppenbilder(bilder: Path, markierung: Path, vorhersage: Path, nummer: str, ausgabe: Path) -> list[Path]:
    """Drei Bilder je Nummer (nur Masken, keine Boxen): <nummer>_vergleich.jpg (Markierung über Modell),
    <nummer>_umriss.jpg (Modell als Umriss), <nummer>_masse.jpg (Modell mit Ellipse und mm). Fehlt die Datei der
    Vorhersage, hat das Modell nichts gefunden (ultralytics schreibt dann keine)."""
    bild = bild_laden(bilder / f"{nummer}.bmp")
    markiert = objekte_aus_label((markierung / f"{nummer}.txt").read_text(encoding="utf-8"), *bild.size)
    datei = vorhersage / f"{nummer}.txt"
    modell = objekte_aus_vorhersage(datei.read_text(encoding="utf-8"), *bild.size) if datei.exists() else []
    ausgabe.mkdir(parents=True, exist_ok=True)
    teile = {
        "vergleich": uebereinander([masken_bild(bild, markiert, "Markierung"), masken_bild(bild, modell, "Modell")]),
        "umriss": masken_bild(bild, modell, "Modell: Umriss", art="umriss"),
        "masse": masken_bild(bild, modell, "Modell: Maße aus dem Umriss (Ellipse)", art="masse"),
    }
    ziele = []
    for name, fertig in teile.items():
        ziele.append(ausgabe / f"{nummer}_{name}.jpg")
        fertig.save(ziele[-1], quality=90)
    return ziele


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
        print(zeichnen(args.seg, nummer, args.ausgabe))


def _gruppenbilder(args) -> None:
    for nummer in args.nummern:
        for ziel in gruppenbilder(args.bilder, args.markierung, args.vorhersage, nummer, args.ausgabe):
            print(ziel)


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
    s.add_argument("--ausgabe", type=Path, required=True, help="Ordner für die JPGs")
    s.add_argument("nummern", nargs="+")
    s.set_defaults(los=_zeichnen)
    s = sub.add_parser("gruppenbilder")
    s.add_argument("--bilder", type=Path, required=True, help="Ordner mit <nummer>.bmp")
    s.add_argument("--markierung", type=Path, required=True, help="Ordner mit den Labels <nummer>.txt")
    s.add_argument("--vorhersage", type=Path, required=True,
                   help="Ordner labels/ aus `yolo segment predict save_txt=True save_conf=True`")
    s.add_argument("--ausgabe", type=Path, required=True, help="Ordner für die JPGs")
    s.add_argument("nummern", nargs="+")
    s.set_defaults(los=_gruppenbilder)
    args = p.parse_args(argv)
    try:
        args.los(args)
    except (ValueError, FileExistsError, FileNotFoundError, OSError, zipfile.BadZipFile) as fehler:
        print(f"FEHLER: {fehler}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
