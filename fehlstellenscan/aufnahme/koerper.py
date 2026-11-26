"""Körper eines Balkens aus seinen vier Seiten (Plan: docs/ideen-galerie-3d-und-aufteilung.md).

Je Foto: Holz vom dunklen Grund trennen, Fläche gerade drehen, quer auf ihre Kanten schneiden. Je Seite: Fotos
nach ihrer Lage längs (mitte_mm) überblendet aneinanderlegen und auf die eingetragenen Maße bringen. Gemessene
Maße stehen daneben in koerper.json, damit Abweichungen sichtbar bleiben.

Lage der Seiten: Der Balken wird um seine Längsachse gerollt, das Handy bleibt. Dann stößt die nächste Seite an
die obere Bildkante (an B002 an den Zapfen des Bodens geprüft). Die vier Bilder übereinander ergeben so den
abgewickelten Mantel, ohne Spiegeln.

Nur numpy und Pillow, läuft in der Trainings-.venv am Mac und in der .venv auf dem Server:
  python koerper.py <Balkenordner>      schreibt <Balkenordner>/koerper/ (S1.jpg bis S4.jpg, klein S1_k.jpg, koerper.json)
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SUCHE_PX = 1200          # lange Bildseite für die Kantensuche
ZIEL_PX_JE_MM = 4.0      # Auflösung der fertigen Seitenbilder
MAX_BREITE_PX = 8000     # längs höchstens so viele Pixel (lange Balken bekommen weniger px/mm)
KLEIN_PX = 480           # Breite der kleinen Seitenbilder für die Galerie
RAND = 0.01              # Fläche gilt als am Bildrand abgeschnitten, wenn sie näher als 1 % am Rand liegt


def schwelle_otsu(werte: np.ndarray) -> float:
    """Schwelle, die zwei Gruppen von Werten am besten trennt (Otsu)."""
    werte = werte.ravel().astype(np.float64)
    haeufig, raender = np.histogram(werte, bins=256)
    mitten = (raender[:-1] + raender[1:]) / 2
    w0 = np.cumsum(haeufig)
    w1 = w0[-1] - w0
    s0 = np.cumsum(haeufig * mitten)
    m0 = s0 / np.maximum(w0, 1)
    m1 = (s0[-1] - s0) / np.maximum(w1, 1)
    zwischen = w0 * w1 * (m0 - m1) ** 2
    return float(mitten[int(np.argmax(zwischen))])


def holzmaske(rgb: np.ndarray) -> np.ndarray:
    """True, wo Holz ist. Holz ist rot-gelblich, der Grund schwarz bis bläulich grau: Rot minus Blau trennt beides."""
    wert = rgb[..., 0].astype(np.int16) - rgb[..., 2].astype(np.int16)
    return wert > schwelle_otsu(wert)


def laengster_lauf(an: np.ndarray) -> tuple[int, int]:
    """Anfang und Ende (einschließlich) des längsten zusammenhängenden True-Stücks."""
    bester, start, beste = (0, -1), None, -1
    for i, x in enumerate(list(an) + [False]):
        if x and start is None:
            start = i
        elif not x and start is not None:
            if i - start > beste:
                bester, beste = (start, i - 1), i - start
            start = None
    if beste < 0:
        raise ValueError("kein Holz im Bild gefunden")
    return bester


def ausgleichsgerade(x: np.ndarray, y: np.ndarray) -> float:
    """Steigung einer Geraden durch die Punkte, Ausreißer (Zapfen, Ecken) werden einmal verworfen."""
    a, b = np.polyfit(x, y, 1)
    rest = y - (a * x + b)
    mad = np.median(np.abs(rest - np.median(rest))) or 1.0
    gut = np.abs(rest) <= 3 * 1.4826 * mad
    if gut.sum() >= 2:
        a, b = np.polyfit(x[gut], y[gut], 1)
    return float(a)


def kanten(maske: np.ndarray) -> dict:
    """Kanten der Fläche in einer Maske (Pixel der Maske) und ihre Neigung in Grad (positiv = im Uhrzeigersinn)."""
    anteil = maske.mean(axis=0)
    links, rechts = laengster_lauf(anteil > 0.5 * anteil.max())
    breite = rechts - links + 1
    innen = np.arange(links + breite // 10, rechts - breite // 10 + 1)
    hat = maske[:, innen].any(axis=0)
    innen = innen[hat]
    if len(innen) < 2:
        raise ValueError("Fläche zu schmal für die Kantensuche")
    spalten = maske[:, innen]
    oben = spalten.argmax(axis=0).astype(np.float64)
    unten = (maske.shape[0] - 1 - spalten[::-1].argmax(axis=0)).astype(np.float64)
    neigung = (ausgleichsgerade(innen, oben) + ausgleichsgerade(innen, unten)) / 2
    return {"links": float(links), "rechts": float(rechts + 1), "oben": float(np.median(oben)),
            "unten": float(np.median(unten) + 1), "winkel": math.degrees(math.atan(neigung)),
            "rand_links": links <= RAND * maske.shape[1], "rand_rechts": rechts + 1 >= (1 - RAND) * maske.shape[1]}


def flaeche_finden(bild: Image.Image) -> tuple[Image.Image, dict]:
    """Dreht das Bild so, dass die Fläche waagerecht liegt, und gibt ihre Kanten in Pixeln des gedrehten Bildes."""
    faktor = max(bild.size) / SUCHE_PX
    klein_groesse = (round(bild.width / faktor), round(bild.height / faktor))
    erste = kanten(holzmaske(np.asarray(bild.resize(klein_groesse, Image.Resampling.BILINEAR))))
    gerade = bild.rotate(erste["winkel"], resample=Image.Resampling.BICUBIC, fillcolor=(0, 0, 0))
    k = kanten(holzmaske(np.asarray(gerade.resize(klein_groesse, Image.Resampling.BILINEAR))))
    sx, sy = bild.width / klein_groesse[0], bild.height / klein_groesse[1]
    k.update(links=k["links"] * sx, rechts=k["rechts"] * sx, oben=k["oben"] * sy, unten=k["unten"] * sy,
             winkel=erste["winkel"] + k["winkel"])
    return gerade, k


def richtung(stuecke: list[dict]) -> int:
    """+1, wenn mm längs nach rechts wachsen. Das Foto mit der kleinsten Lage zeigt den Anfang des Balkens."""
    erstes = min(stuecke, key=lambda s: s["mitte_mm"])
    if not erstes["kanten"]["rand_links"]:
        return 1
    if not erstes["kanten"]["rand_rechts"]:
        return -1
    raise ValueError("erstes Foto zeigt kein Balkenende, Lage längs nicht bestimmbar")


def seite_bauen(fotos: list[dict], laenge_mm: float, flaeche_mm: float) -> tuple[Image.Image, dict]:
    """fotos: je {"bild": PIL-Bild (Zuschnitt), "mitte_mm": Lage der Bildmitte längs, "px_je_mm"}.
    Ergebnis: Seitenbild genau laenge_mm x flaeche_mm (längs waagerecht) und ein Bericht mit den gemessenen Maßen."""
    stuecke = []
    for f in fotos:
        gerade, k = flaeche_finden(f["bild"])
        stuecke.append({"bild": gerade, "kanten": k, "mitte_mm": float(f["mitte_mm"]), "px_je_mm": float(f["px_je_mm"])})
    r = richtung(stuecke)
    # Lage jeder Bildspalte längs in mm, Nullpunkt am Anfang des Balkens im ersten Foto
    for s in stuecke:
        s["mm"] = lambda x, s=s: s["mitte_mm"] + r * (x - s["bild"].width / 2) / s["px_je_mm"]
    erstes, letztes = min(stuecke, key=lambda s: s["mitte_mm"]), max(stuecke, key=lambda s: s["mitte_mm"])
    anfang = erstes["mm"](erstes["kanten"]["links" if r > 0 else "rechts"])
    ende_px = letztes["kanten"]["rechts" if r > 0 else "links"]
    ende = letztes["mm"](ende_px) if not letztes["kanten"]["rand_rechts" if r > 0 else "rand_links"] else None

    gemessen_laenge = (ende - anfang) if ende is not None else None
    streck = (gemessen_laenge / laenge_mm) if gemessen_laenge else 1.0      # gemessene auf eingetragene Länge
    aus = min(ZIEL_PX_JE_MM, MAX_BREITE_PX / laenge_mm)
    breite, hoehe = round(laenge_mm * aus), round(flaeche_mm * aus)
    summe = np.zeros((hoehe, breite, 3), np.float64)
    gewicht = np.zeros((hoehe, breite), np.float64)
    quer = []
    for s in stuecke:
        k = s["kanten"]
        quer.append((k["unten"] - k["oben"]) / s["px_je_mm"])
        x0, x1 = (k["links"], k["rechts"])
        if k["rand_links"]:
            x0 = 0.0
        if k["rand_rechts"]:
            x1 = float(s["bild"].width)
        a, b = sorted(((s["mm"](x0) - anfang) / streck, (s["mm"](x1) - anfang) / streck))
        z0, z1 = max(0, math.floor(a * aus)), min(breite, math.ceil(b * aus))
        if z1 <= z0:
            continue
        # Zielspalten z0..z1 zeigen die Bildspalten zwischen x0 und x1 (Richtung beachten), quer oben..unten
        links_mm, rechts_mm = z0 / aus * streck + anfang, z1 / aus * streck + anfang
        bx = [s["bild"].width / 2 + r * (m - s["mitte_mm"]) * s["px_je_mm"] for m in (links_mm, rechts_mm)]
        stueck = s["bild"].transform((z1 - z0, hoehe), Image.Transform.EXTENT,
                                     (bx[0], k["oben"], bx[1], k["unten"]), Image.Resampling.BICUBIC)
        # Überblenden: Gewicht steigt zu den Rändern des Stücks hin linear ab (höchstens 30 mm breit)
        spalten = np.arange(z0, z1) + 0.5
        rampe = max(1.0, 30 * aus)
        w = np.clip(np.minimum(spalten - a * aus, b * aus - spalten) / rampe, 0.01, 1.0)
        summe[:, z0:z1] += np.asarray(stueck, np.float64) * w[None, :, None]
        gewicht[:, z0:z1] += w[None, :]
    luecke = float((gewicht[0] == 0).mean())
    bild = (summe / np.maximum(gewicht, 1e-9)[..., None]).clip(0, 255).astype(np.uint8)
    if r < 0:
        bild = bild[:, ::-1]      # zurück in die Bildrichtung des Fotos: nie spiegeln, Anfang dann rechts
    bericht = {"fotos": len(fotos), "richtung": r, "winkel_grad": [round(s["kanten"]["winkel"], 2) for s in stuecke],
               "laenge_mm": round(gemessen_laenge, 1) if gemessen_laenge else None,
               "flaeche_mm": round(float(np.median(quer)), 1), "luecke_anteil": round(luecke, 4),
               "px_je_mm": round(aus, 3)}
    return Image.fromarray(bild), bericht


def px_aus_plan(zuschnitt: Image.Image, plan: dict) -> float:
    """px je mm, wenn das Foto keinen Wert hat (auf dem Mac misst sips ihn): ganze Bildbreite durch voll_mm."""
    anteil = (plan.get("zuschnitt") or [0, 0, 1, 1])[2]
    return zuschnitt.width / anteil / plan["voll_mm"]


def abweichung(gemessen: float | None, soll: float) -> float | None:
    return None if gemessen is None else round(100 * (gemessen - soll) / soll, 1)


def koerper_bauen(ordner: Path) -> dict:
    """Liest <ordner>/balken.json und die Zuschnitte, schreibt <ordner>/koerper/. Seiten ohne Fotos fehlen."""
    balken = json.loads((ordner / "balken.json").read_text(encoding="utf-8"))
    ziel = ordner / "koerper"
    ziel.mkdir(exist_ok=True)
    ergebnis = {"id": balken["id"], "laenge_mm": balken["laenge_mm"], "breite_mm": balken["breite_mm"],
                "hoehe_mm": balken["hoehe_mm"], "seiten": {}}
    for nr, seite in sorted(balken.get("seiten", {}).items()):
        eintraege = [f for _, f in sorted(seite.get("fotos", {}).items(), key=lambda x: int(x[0]))]
        if not eintraege:
            continue
        flaeche = seite["plan"]["flaeche_mm"]
        fotos = []
        for f in eintraege:
            pfad = ordner / "zuschnitt" / (Path(f["datei"]).stem + ".jpg")
            if not pfad.exists():
                raise FileNotFoundError(f"Zuschnitt fehlt: {pfad}")
            with Image.open(pfad) as roh:
                bild = roh.convert("RGB")
            fotos.append({"bild": bild, "mitte_mm": f["mitte_mm"], "px_je_mm": f.get("px_je_mm") or px_aus_plan(bild, seite["plan"])})
        bild, bericht = seite_bauen(fotos, balken["laenge_mm"], flaeche)
        vorlaeufig = ziel / f"S{nr}.tmp"
        bild.save(vorlaeufig, "JPEG", quality=90)
        vorlaeufig.replace(ziel / f"S{nr}.jpg")
        klein = bild.resize((KLEIN_PX, max(24, round(bild.height * KLEIN_PX / bild.width))), Image.Resampling.LANCZOS)
        klein.save(vorlaeufig, "JPEG", quality=85)
        vorlaeufig.replace(ziel / f"S{nr}_k.jpg")
        bericht["soll_mm"] = {"laenge": balken["laenge_mm"], "flaeche": flaeche}
        bericht["abweichung_prozent"] = {"laenge": abweichung(bericht["laenge_mm"], balken["laenge_mm"]),
                                         "flaeche": abweichung(bericht["flaeche_mm"], flaeche)}
        ergebnis["seiten"][nr] = bericht
    (ziel / "koerper.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")
    return ergebnis


if __name__ == "__main__":
    print(json.dumps(koerper_bauen(Path(sys.argv[1])), ensure_ascii=False, indent=1))
