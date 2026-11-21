"""Das Kodytek-Seg-Modell auf einem ganzen Balken: Streifenbild (holzbalkenscan, Felix' Verfahren) in Kacheln im
Maßstab und in der Lage der Kodytek-Bilder schneiden, die Vorhersagen vom Mac zurück auf den Balken legen und als
Karte in mm zeichnen.

Läuft auf dem Server (Pillow, numpy, opencv, masken.py und datensatz.py aus demselben Ordner; kein ultralytics).
Das Modell läuft auf dem Mac per `yolo segment predict`, Anleitung in STATUS.md.

Befehle (Einzelheiten mit --help):
  kacheln  Streifenbild -> Kacheln <name>.jpg und kacheln.json (Lage jeder Kachel in mm auf dem Balken)
  karte    kacheln.json und Vorhersagen (.txt) -> funde.json, funde.csv und je Meter ein Kartenbild

Lage und Maßstab: In den Kodytek-Bildern läuft das Brett senkrecht. x ist quer zum Brett (16,66 Px/mm), y längs
(6,67 Px/mm), ein Bild (2800 x 1024) deckt also 168,1 mm quer und 153,5 mm längs. Im Streifenbild läuft der Balken
waagerecht (x längs, y quer, gleiche Px/mm in beiden Richtungen). Jede Kachel wird darum gespiegelt an der
Diagonale (transponiert: x und y getauscht) und je Richtung auf den Kodytek-Maßstab gestreckt. So sehen Äste für
das Modell so groß und so geformt aus wie im Training.

Koordinaten auf dem Balken in mm: l längs ab dem Balkenanfang (links im Streifen), q quer ab der oberen Kante.
Doppelte Funde in Überlappungen: Ein Fund zählt nur in der Kachel, in deren Kern sein Schwerpunkt liegt (Kern =
Kachel bis zur Mitte der Überlappung mit den Nachbarn). Ein Fund, den das Modell an einem Kachelrand abschneidet,
kann so in keiner Kachel ganz stehen; die Überlappung (Vorgabe 40 mm längs) macht das selten.
"""

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

import datensatz as d
import masken as m

KACHEL_PX = (2800, 1024)                                  # Kodytek-Bild: Breite (quer), Höhe (längs)
KACHEL_MM = (KACHEL_PX[0] / m.PX_JE_MM[0], KACHEL_PX[1] / m.PX_JE_MM[1])   # (quer 168,1, längs 153,5)
UEBERLAPPUNG_MM = 40.0                                    # Mindestüberlappung längs; quer ergibt sie sich
KARTE_PX_JE_MM = 3.0                                      # Kartenbilder: 1 m Balken = 3000 Px breit
KARTE_ABSCHNITT_MM = 1000.0


# ---------------------------------------------------------------- reine Logik

def anfaenge(laenge: float, kachel: float, ueberlappung: float) -> list[float]:
    """Anfänge der Kacheln entlang einer Strecke, gleichmäßig verteilt, erste bei 0, letzte bündig am Ende,
    Überlappung mindestens `ueberlappung`. Ist die Strecke kürzer als eine Kachel, eine Kachel bei 0 (der Rest
    der Kachel liegt dann außerhalb und wird beim Schneiden mit Rand gefüllt)."""
    if laenge <= kachel:
        return [0.0]
    schritt = kachel - ueberlappung
    if schritt <= 0:
        raise ValueError("Überlappung muss kleiner als die Kachel sein")
    anzahl = math.ceil((laenge - kachel) / schritt) + 1
    abstand = (laenge - kachel) / (anzahl - 1)
    return [i * abstand for i in range(anzahl)]


def kerne(starts: list[float], kachel: float) -> list[tuple[float, float]]:
    """Kern jeder Kachel: von der Mitte der Überlappung mit der vorigen bis zur Mitte mit der nächsten.
    Erste und letzte Kachel reichen nach außen unbegrenzt."""
    grenzen = [(starts[i] + kachel + starts[i + 1]) / 2 for i in range(len(starts) - 1)]
    unten = [-math.inf, *grenzen]
    oben = [*grenzen, math.inf]
    return list(zip(unten, oben, strict=True))


def raster(laenge_mm: float, hoehe_mm: float, ueberlappung_mm: float = UEBERLAPPUNG_MM) -> list[dict]:
    """Alle Kacheln eines Balkens: name, l0/q0 (Anfang in mm), kern_l/kern_q (Kern in mm)."""
    quer, laengs = KACHEL_MM
    ls, qs = anfaenge(laenge_mm, laengs, ueberlappung_mm), anfaenge(hoehe_mm, quer, ueberlappung_mm)
    kl, kq = kerne(ls, laengs), kerne(qs, quer)
    return [{"name": f"l{i:03d}_q{j}", "l0": round(l0, 3), "q0": round(q0, 3),
             "kern_l": [kl[i][0], kl[i][1]], "kern_q": [kq[j][0], kq[j][1]]}
            for i, l0 in enumerate(ls) for j, q0 in enumerate(qs)]


def kachel_zu_balken(punkte_px: np.ndarray, kachel: dict) -> np.ndarray:
    """Punkte (x, y) in Kachelpixeln -> (l, q) in mm auf dem Balken. x quer, y längs (Kodytek-Lage)."""
    p = np.asarray(punkte_px, dtype=np.float64)
    q = kachel["q0"] + p[:, 0] / m.PX_JE_MM[0]
    l_ = kachel["l0"] + p[:, 1] / m.PX_JE_MM[1]
    return np.stack([l_, q], axis=1)


def im_kern(punkte_mm: np.ndarray, kachel: dict) -> bool:
    """Liegt der Schwerpunkt (Mittel der Umrisspunkte) im Kern der Kachel? Halboffen [unten, oben)."""
    l_, q = punkte_mm.mean(axis=0)
    (lu, lo), (qu, qo) = kachel["kern_l"], kachel["kern_q"]
    return lu <= l_ < lo and qu <= q < qo


def fund(klasse: int, punkte_mm: np.ndarray, konfidenz: float | None, kachel: str) -> dict:
    """Ein Fund mit Lage und Größe in mm. Bei Ästen dazu die Ellipse (lang, kurz) aus dem Umriss."""
    lmin, qmin = punkte_mm.min(axis=0)
    lmax, qmax = punkte_mm.max(axis=0)
    eintrag = {"klasse": d.KLASSEN[klasse], "name": m.NAMEN_DE[klasse], "konfidenz": konfidenz, "kachel": kachel,
               "l_von": round(float(lmin), 1), "l_bis": round(float(lmax), 1),
               "q_von": round(float(qmin), 1), "q_bis": round(float(qmax), 1),
               "ellipse_lang": None, "ellipse_kurz": None, "umriss": np.round(punkte_mm, 1).tolist()}
    if klasse in m.AESTE:
        masse = m.masse_mm(punkte_mm, (1.0, 1.0))
        if masse is not None:
            eintrag["ellipse_lang"], eintrag["ellipse_kurz"] = round(masse["lang"], 1), round(masse["kurz"], 1)
    return eintrag


def funde_sammeln(kacheln: list[dict], vorhersagen: dict[str, str]) -> tuple[list[dict], int]:
    """Vorhersagen je Kachel (Name -> Text von yolo predict) zu Funden auf dem Balken, nach l sortiert.
    Zweiter Wert: Zahl der verworfenen Doppelten (Schwerpunkt im Kern einer anderen Kachel)."""
    funde, doppelt = [], 0
    for kachel in kacheln:
        text = vorhersagen.get(kachel["name"])
        if not text:
            continue
        for klasse, punkte, konfidenz in m.objekte_aus_vorhersage(text, *KACHEL_PX):
            mm = kachel_zu_balken(punkte, kachel)
            if im_kern(mm, kachel):
                funde.append(fund(klasse, mm, konfidenz, kachel["name"]))
            else:
                doppelt += 1
    funde.sort(key=lambda f: (f["l_von"], f["q_von"]))
    return funde, doppelt


# ---------------------------------------------------------------- Bilder

def kachel_schneiden(streifen, feld: tuple[float, float], px_je_mm: float, kachel: dict):
    """Eine Kachel aus dem Streifenbild (PIL, Balken waagerecht): Ausschnitt in Streifenpixeln, transponiert und auf
    KACHEL_PX gestreckt. feld = Pixel (x, y) der oberen linken Ecke des Balkens im Streifen. Außerhalb des Streifens
    füllt Pillow schwarz, wie der Hintergrund bei Kodytek."""
    from PIL import Image
    x0 = feld[0] + kachel["l0"] * px_je_mm
    y0 = feld[1] + kachel["q0"] * px_je_mm
    rechteck = (x0, y0, x0 + KACHEL_MM[1] * px_je_mm, y0 + KACHEL_MM[0] * px_je_mm)
    ausschnitt = streifen.crop(tuple(round(v) for v in rechteck))
    return ausschnitt.transpose(Image.Transpose.TRANSPOSE).resize(KACHEL_PX, Image.LANCZOS)


def kacheln_schreiben(streifen_pfad: Path, ausgabe: Path, laenge_mm: float, hoehe_mm: float,
                      feld: tuple[float, float], px_je_mm: float, ueberlappung_mm: float) -> dict:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None                        # Streifen sind 40.000 Px lang
    kacheln = raster(laenge_mm, hoehe_mm, ueberlappung_mm)
    ausgabe.mkdir(parents=True, exist_ok=True)
    with Image.open(streifen_pfad) as roh:
        streifen = roh.convert("RGB")
    for kachel in kacheln:
        kachel_schneiden(streifen, feld, px_je_mm, kachel).save(ausgabe / f"{kachel['name']}.jpg", quality=95)
    beschreibung = {"streifen": str(streifen_pfad), "laenge_mm": laenge_mm, "hoehe_mm": hoehe_mm,
                    "feld_px": list(feld), "px_je_mm": px_je_mm, "ueberlappung_mm": ueberlappung_mm,
                    "kachel_px": list(KACHEL_PX), "kachel_mm_quer_laengs": [round(v, 2) for v in KACHEL_MM],
                    "lage": "Kachel transponiert: x quer (q), y laengs (l), wie Kodytek", "kacheln": kacheln}
    (ausgabe / "kacheln.json").write_text(json.dumps(beschreibung, ensure_ascii=False, indent=1), encoding="utf-8")
    return beschreibung


def karte_zeichnen(streifen, beschreibung: dict, funde: list[dict], von_mm: float, bis_mm: float):
    """Kartenbild eines Abschnitts: Balken waagerecht, Umrisse in Neonfarben, Namen mit Konfidenz, bei Ästen
    lang x kurz in mm. Kopfzeile mit Abschnitt, Fußleiste mit mm-Teilung längs."""
    from PIL import Image, ImageDraw
    s, (fx, fy) = beschreibung["px_je_mm"], beschreibung["feld_px"]
    hoehe = beschreibung["hoehe_mm"]
    bis_mm = min(bis_mm, beschreibung["laenge_mm"])
    ausschnitt = streifen.crop((round(fx + von_mm * s), round(fy), round(fx + bis_mm * s), round(fy + hoehe * s)))
    k = KARTE_PX_JE_MM
    grund = ausschnitt.resize((round((bis_mm - von_mm) * k), round(hoehe * k)), Image.LANCZOS).convert("RGBA")
    schicht = Image.new("RGBA", grund.size, (0, 0, 0, 0))
    zeichner = ImageDraw.Draw(schicht)
    font = m.schrift(22)
    texte = []
    for f in funde:
        if f["l_bis"] < von_mm or f["l_von"] > bis_mm:
            continue
        nummer = d.KLASSEN.index(f["klasse"])
        farbe = tuple(bytes.fromhex(m.ANZEIGE[nummer]))
        punkte = (np.array(f["umriss"]) - (von_mm, 0)) * k
        zeichner.polygon([tuple(p) for p in punkte.tolist()], outline=(*farbe, 255), width=3)
        text = f["name"]
        if f["ellipse_lang"] is not None:
            text += f" {m.zahl(f['ellipse_lang'], 0)}×{m.zahl(f['ellipse_kurz'], 0)} mm"
        if f["konfidenz"] is not None:
            text += f" ({m.zahl(f['konfidenz'], 2)})"
        texte.append((text, farbe, punkte))
    belegt: list[tuple[float, float, float, float]] = []
    for text, farbe, punkte in texte:
        _, _, rechts, unten = zeichner.textbbox((0, 0), text, font=font)
        x, y, x2, y2 = m.textplatz(punkte, rechts + 8, unten + 6, grund.size, belegt)
        belegt.append((x, y, x2, y2))
        hell = 0.299 * farbe[0] + 0.587 * farbe[1] + 0.114 * farbe[2] > 140
        zeichner.rectangle((x, y, x2, y2), fill=(*farbe, 220))
        zeichner.text((x + 4, y + 2), text, fill=(0, 0, 0, 255) if hell else (255, 255, 255, 255), font=font)
    karte = Image.alpha_composite(grund, schicht).convert("RGB")
    kopf_h, fuss_h = 44, 40
    gesamt = Image.new("RGB", (karte.width, kopf_h + karte.height + fuss_h), (30, 30, 30))
    gesamt.paste(karte, (0, kopf_h))
    z = ImageDraw.Draw(gesamt)
    anzahl = sum(1 for f in funde if von_mm <= (f["l_von"] + f["l_bis"]) / 2 < bis_mm)
    z.text((12, 8), f"Balken {m.zahl(von_mm / 1000, 1)} bis {m.zahl(bis_mm / 1000, 1)} m: {anzahl} Funde "
                    f"(Kodytek-Seg-Modell, Umriss, Ellipse bei Ästen)", fill=(255, 255, 255), font=m.schrift(24))
    klein = m.schrift(18)
    for mm in range(math.ceil(von_mm / 10) * 10, math.floor(bis_mm) + 1, 10):
        x = (mm - von_mm) * k
        lang = 14 if mm % 100 == 0 else 6
        z.line((x, kopf_h + karte.height, x, kopf_h + karte.height + lang), fill=(255, 255, 255), width=2)
        if mm % 100 == 0:
            z.text((x + 3, kopf_h + karte.height + 14), f"{mm}", fill=(255, 255, 255), font=klein)
    return gesamt


CSV_SPALTEN = ["klasse", "name", "konfidenz", "l_von", "l_bis", "q_von", "q_bis", "ellipse_lang", "ellipse_kurz",
               "kachel"]


def karte_schreiben(kacheln_ordner: Path, vorhersage: Path, ausgabe: Path) -> dict:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    beschreibung = json.loads((kacheln_ordner / "kacheln.json").read_text(encoding="utf-8"))
    texte = {p.stem: p.read_text(encoding="utf-8") for p in vorhersage.glob("*.txt")}
    unbekannt = sorted(set(texte) - {k["name"] for k in beschreibung["kacheln"]})
    if unbekannt:
        raise ValueError(f"Vorhersagen ohne Kachel in kacheln.json: {', '.join(unbekannt[:5])}")
    funde, doppelt = funde_sammeln(beschreibung["kacheln"], texte)
    ausgabe.mkdir(parents=True, exist_ok=True)
    (ausgabe / "funde.json").write_text(json.dumps(funde, ensure_ascii=False, indent=1), encoding="utf-8")
    with (ausgabe / "funde.csv").open("w", encoding="utf-8", newline="") as datei:
        schreiber = csv.DictWriter(datei, CSV_SPALTEN, extrasaction="ignore", delimiter=";")
        schreiber.writeheader()
        schreiber.writerows(funde)
    with Image.open(beschreibung["streifen"]) as roh:
        streifen = roh.convert("RGB")
    bilder = []
    von = 0.0
    while von < beschreibung["laenge_mm"]:
        ziel = ausgabe / f"karte_{int(von / 1000):02d}m.jpg"
        karte_zeichnen(streifen, beschreibung, funde, von, von + KARTE_ABSCHNITT_MM).save(ziel, quality=90)
        bilder.append(ziel)
        von += KARTE_ABSCHNITT_MM
    je_klasse: dict[str, int] = {}
    for f in funde:
        je_klasse[f["name"]] = je_klasse.get(f["name"], 0) + 1
    return {"funde": len(funde), "doppelt_verworfen": doppelt, "je_klasse": je_klasse,
            "kacheln_mit_fund": len(texte), "bilder": [str(b) for b in bilder]}


# ---------------------------------------------------------------- Befehle

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawTextHelpFormatter)
    b = p.add_subparsers(dest="befehl", required=True)
    s = b.add_parser("kacheln", help="Streifenbild in Kacheln im Kodytek-Maßstab schneiden")
    s.add_argument("--streifen", type=Path, required=True, help="streifen.jpg aus einem holzbalkenscan-Lauf")
    s.add_argument("--laenge", type=float, required=True, help="Balkenlänge in mm (streifen.txt, Balkenfeld)")
    s.add_argument("--hoehe", type=float, required=True, help="Balkenhöhe in mm")
    s.add_argument("--feld", type=float, nargs=2, required=True, metavar=("X", "Y"),
                   help="Pixel der oberen linken Balkenecke im Streifen")
    s.add_argument("--px-je-mm", type=float, required=True, help="Maßstab des Streifens (streifen.txt: Ziel)")
    s.add_argument("--ueberlappung", type=float, default=UEBERLAPPUNG_MM, help="mm, Vorgabe %(default)s")
    s.add_argument("--ausgabe", type=Path, required=True)
    s = b.add_parser("karte", help="Vorhersagen vom Mac auf den Balken legen: funde.json/.csv, Kartenbilder")
    s.add_argument("--kacheln", type=Path, required=True, help="Ordner mit kacheln.json")
    s.add_argument("--vorhersage", type=Path, required=True, help="labels/ von yolo segment predict")
    s.add_argument("--ausgabe", type=Path, required=True)
    args = p.parse_args(argv)
    if args.befehl == "kacheln":
        ergebnis = kacheln_schreiben(args.streifen, args.ausgabe, args.laenge, args.hoehe, tuple(args.feld),
                                     args.px_je_mm, args.ueberlappung)
        anzahl_l = len({k["l0"] for k in ergebnis["kacheln"]})
        print(f"{len(ergebnis['kacheln'])} Kacheln ({anzahl_l} längs x "
              f"{len(ergebnis['kacheln']) // anzahl_l} quer) in {args.ausgabe}")
    else:
        ergebnis = karte_schreiben(args.kacheln, args.vorhersage, args.ausgabe)
        print(json.dumps({k: v for k, v in ergebnis.items() if k != "bilder"}, ensure_ascii=False))
        for bild in ergebnis["bilder"]:
            print(bild)
    return 0


if __name__ == "__main__":
    sys.exit(main())
