"""Test (Jan 28.11.2026): Vorlabel ohne eigene Labels, nur mit Begriffen. Zwei Modelle, die Text verstehen, laufen auf
Fotos der Fotobox-Balken: YOLOE (ultralytics, Gewichte laden beim ersten Start selbst) und SAM 3 (Gewichte sam3.pt nur
nach Freigabe auf https://huggingface.co/facebook/sam3, von Hand nach ~/fehlstellenscan/modelle/). Kacheln und
Umrechnung wie beim Vorlabeln (vorlabeln.kacheln, vorlabeln.foto_objekte). Ergebnis nur als Datei und Bilder, nichts
geht in die Labels. Läuft auf dem Mac in der Trainings-.venv, nicht neben einem Training oder Vorlabeln (mps):

  python ~/fehlstellenscan/aufnahme/textprompt.py --balken B004 B005 --anzahl 10

Ausgabe ~/fehlstellenscan/textprompt-test/: ergebnis.json (Objekte je Modell und Foto, Dauer), bilder/<Foto>.jpg (oben
YOLOE, unten SAM 3, Umriss und Begriff). ultralytics wird erst beim Rechnen geladen; die reinen Teile sind getestet
(tests/test_textprompt.py, ohne torch)."""

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

if __package__:
    from . import kette as k
    from . import vorlabeln as vl
else:
    import kette as k
    import vorlabeln as vl

# Begriff fürs Modell (englisch, kurz) -> Name im Bild. Klassen der Gruppe vom 27.11.2026, dazu Fuge und Nagel, damit
# man sieht, ob das Modell Fugen für Risse und Nägel für Löcher hält.
BEGRIFFE = [
    ("wood knot", "Ast"),
    ("crack", "Riss"),
    ("resin pocket", "Harzgalle"),
    ("nail hole", "Nagelloch"),
    ("screw hole", "Schraubloch"),
    ("chipped wood", "Abplatzung"),
    ("insect exit hole", "Insektenloch"),
    ("glue line", "Fuge"),
    ("metal nail", "Nagel"),
]
FARBEN = ["#00e5ff", "#ff2bd6", "#ffd400", "#ff6a00", "#ff9e7a", "#7cff4d", "#b388ff", "#9e9e9e", "#ffffff"]
MODELLE = ("yoloe", "sam3")
YOLOE_GEWICHTE = "yoloe-26l-seg.pt"


def begriffe_lesen(zusatz: list[str] | None) -> list[tuple[str, str]]:
    """--begriff "englisch=Deutsch" ersetzt die ganze Liste, sonst gilt BEGRIFFE."""
    if not zusatz:
        return list(BEGRIFFE)
    ergebnis = []
    for z in zusatz:
        en, _, de = z.partition("=")
        if not en.strip():
            raise ValueError(f"Begriff leer: {z!r}")
        ergebnis.append((en.strip(), de.strip() or en.strip()))
    return ergebnis


def verteilt(namen: list[str], anzahl: int) -> list[str]:
    """anzahl Namen gleichmäßig über die Liste, immer dieselben."""
    if anzahl >= len(namen):
        return list(namen)
    if anzahl <= 0:
        return []
    if anzahl == 1:
        return [namen[len(namen) // 2]]
    return [namen[round(i * (len(namen) - 1) / (anzahl - 1))] for i in range(anzahl)]


def liste(wert) -> list:
    """Tensor, numpy oder Liste -> Liste (ohne torch zu importieren)."""
    if wert is None:
        return []
    for weg in ("cpu", "numpy"):
        if hasattr(wert, weg):
            wert = getattr(wert, weg)()
    return wert.tolist() if hasattr(wert, "tolist") else list(wert)


def zeilen_aus_ergebnis(r, begriffe: list[str]) -> str:
    """Ein Ergebnis von ultralytics (masks.xyn, boxes.cls, boxes.conf, names) als Zeilen wie save_txt mit save_conf:
    `Nummer x1 y1 ... Konfidenz`, Nummer = Stelle des Begriffs. Unbekannte Namen fallen weg."""
    if r.masks is None or r.boxes is None:
        return ""
    namen = getattr(r, "names", None) or {}
    klassen, konf = liste(r.boxes.cls), liste(r.boxes.conf)
    text = []
    for umriss, c, p in zip(r.masks.xyn, klassen, konf, strict=False):
        name = namen.get(int(c)) if isinstance(namen, dict) else None
        nr = begriffe.index(name) if name in begriffe else int(c)
        punkte = liste(umriss)
        if not 0 <= nr < len(begriffe) or len(punkte) < 3:
            continue
        text.append(f"{nr} " + " ".join(f"{x:.6f} {y:.6f}" for x, y in punkte) + f" {float(p):.4f}")
    return "\n".join(text) + ("\n" if text else "")


def zaehlen(fotos: dict[str, list[dict]], begriffe: list[str]) -> dict[str, int]:
    zahl = dict.fromkeys(begriffe, 0)
    for objekte in fotos.values():
        for o in objekte:
            zahl[begriffe[o["k"]]] += 1
    return zahl


# ---------------------------------------------------------------- Rechnen (nur Mac, lädt ultralytics)
def fotos_waehlen(ordner: Path, balken: list[str], anzahl: int) -> list[tuple[str, Path]]:
    """Fotos wie im Labeln gezeigt (ohne leere und doppelte), je Balken anzahl gleichmäßig verteilt, mit Zuschnitt."""
    def lesen(b):
        return json.loads((ordner / b / "balken.json").read_text(encoding="utf-8"))

    kette = k.Kette(ordner, lesen, lambda: sorted(p.parent.name for p in ordner.glob("B*/balken.json")))
    ergebnis = []
    for b in balken:
        namen = [f["name"] for f in kette.gezeigt(lesen(b))]
        for n in verteilt(namen, anzahl):
            ergebnis.append((n, kette.zuschnitt(n)))
    return ergebnis


def vorhersager(modell: str, wurzel: Path, begriffe: list[str], konf: float, geraet: str):
    """Funktion Kachelpfad -> Zeilen. Lädt das Modell einmal."""
    if modell == "yoloe":
        from ultralytics import YOLOE
        m = YOLOE(YOLOE_GEWICHTE)
        try:
            m.set_classes(begriffe)
        except TypeError:                               # ältere Fassung will die Text-Einbettung dazu
            m.set_classes(begriffe, m.get_text_pe(begriffe))
        return lambda pfad: zeilen_aus_ergebnis(m.predict(str(pfad), imgsz=vl.KACHEL, conf=konf, retina_masks=True,
                                                          device=geraet, verbose=False)[0], begriffe)
    pt = wurzel / "modelle" / "sam3.pt"
    if not pt.exists():
        raise ValueError(f"{pt} fehlt (Freigabe auf https://huggingface.co/facebook/sam3, dann sam3.pt dorthin).")
    from ultralytics.models.sam import SAM3SemanticPredictor
    p = SAM3SemanticPredictor(overrides={"conf": konf, "task": "segment", "mode": "predict", "model": str(pt),
                                         "save": False, "device": geraet, "verbose": False})

    def eins(pfad):
        p.set_image(str(pfad))
        return zeilen_aus_ergebnis(p(text=begriffe)[0], begriffe)
    return eins


def rechnen(fotos: list[tuple[str, Path]], modell: str, wurzel: Path, begriffe: list[str], konf: float,
            geraet: str) -> dict:
    from PIL import Image
    start = time.monotonic()
    vorher = vorhersager(modell, wurzel, begriffe, konf, geraet)
    laden = time.monotonic() - start
    ergebnis = {}
    with tempfile.TemporaryDirectory() as tmp:
        for i, (name, pfad) in enumerate(fotos, 1):
            with Image.open(pfad) as roh:
                bild = roh.convert("RGB")
            texte = {}
            for kachel in vl.kacheln(name, *bild.size):
                ziel = Path(tmp) / f"{kachel['name']}.jpg"
                bild.crop((kachel["x0"], kachel["y0"], kachel["x0"] + kachel["b"], kachel["y0"] + kachel["h"])) \
                    .save(ziel, quality=95)
                texte[kachel["name"]] = vorher(ziel)
            ergebnis[name] = vl.foto_objekte(name, *bild.size, texte, {n: n for n in range(len(begriffe))}, modell)
            print(f"{modell}: {i}/{len(fotos)} {name}: {len(ergebnis[name])} Objekte", flush=True)
    return {"sekunden_laden": round(laden, 1), "sekunden": round(time.monotonic() - start - laden, 1),
            "fotos": ergebnis}


# ---------------------------------------------------------------- Bilder
def zeichnen(foto: Path, je_modell: dict[str, list[dict]], begriffe_de: list[str], ziel: Path,
             breite: int = 1600) -> None:
    """Je Modell ein Streifen untereinander: Foto, Umrisse in der Farbe des Begriffs, Begriff und Konfidenz."""
    from PIL import Image, ImageDraw, ImageFont
    with Image.open(foto) as roh:
        bild = roh.convert("RGB")
    bild.thumbnail((breite, breite * 4))
    w, h = bild.size
    schrift = ImageFont.load_default(size=max(14, w // 80))
    groesse = getattr(schrift, "size", 11)
    kopf = groesse + 12
    ganz = Image.new("RGB", (w, (h + kopf) * len(je_modell)), "black")
    for zeile, (modell, objekte) in enumerate(je_modell.items()):
        y0 = zeile * (h + kopf)
        ganz.paste(bild, (0, y0 + kopf))
        d = ImageDraw.Draw(ganz)
        zahl = {}
        for o in objekte:
            zahl[o["k"]] = zahl.get(o["k"], 0) + 1
        d.text((6, y0 + 4), f"{modell}: " + ", ".join(f"{begriffe_de[n]} {z}" for n, z in sorted(zahl.items())),
               fill="white", font=schrift)
        for o in objekte:
            farbe = FARBEN[o["k"] % len(FARBEN)]
            p = [(x * w, y0 + kopf + y * h) for x, y in o["p"]]
            d.polygon(p, outline=farbe, width=2)
            x, y = min(p)
            d.text((x, max(y0 + kopf, y - groesse - 2)), f"{begriffe_de[o['k']]} {o.get('c', 0):.2f}",
                   fill=farbe, font=schrift)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ganz.save(ziel, quality=88)


def main(argv=None) -> int:
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    a.add_argument("--balken", nargs="+", required=True)
    a.add_argument("--anzahl", type=int, default=10, help="Fotos je Balken")
    a.add_argument("--modelle", nargs="+", default=list(MODELLE), choices=MODELLE)
    a.add_argument("--konf", type=float, default=0.2)
    a.add_argument("--geraet", default="mps", help="mps oder cpu")
    a.add_argument("--begriff", action="append", help='"englisch=Deutsch", ersetzt die Liste (mehrfach)')
    a.add_argument("--wurzel", type=Path, default=Path.home() / "fehlstellenscan")
    a.add_argument("--ausgabe", type=Path, default=None)
    x = a.parse_args(argv)
    begriffe = begriffe_lesen(x.begriff)
    en, de = [b[0] for b in begriffe], [b[1] for b in begriffe]
    ausgabe = x.ausgabe or x.wurzel / "textprompt-test"
    fotos = fotos_waehlen(x.wurzel / "aufnahmen", x.balken, x.anzahl)
    if not fotos:
        print("Keine Fotos gefunden.", file=sys.stderr)
        return 1
    ergebnis = {"begriffe": en, "namen": de, "konf": x.konf, "modelle": {}}
    for m in x.modelle:
        try:
            ergebnis["modelle"][m] = rechnen(fotos, m, x.wurzel, en, x.konf, x.geraet)
        except Exception as e:                          # ein Modell scheitert: das andere trotzdem rechnen
            print(f"{m} ging nicht: {type(e).__name__}: {e}", file=sys.stderr)
            ergebnis["modelle"][m] = {"fehler": f"{type(e).__name__}: {e}"}
        ausgabe.mkdir(parents=True, exist_ok=True)
        (ausgabe / "ergebnis.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")
    fertig = {m: e["fotos"] for m, e in ergebnis["modelle"].items() if "fotos" in e}
    for name, pfad in fotos:
        if fertig:
            zeichnen(pfad, {m: f[name] for m, f in fertig.items()}, de, ausgabe / "bilder" / f"{name}.jpg")
    for m, e in ergebnis["modelle"].items():
        if "fotos" in e:
            print(f"{m}: {e['sekunden']} s für {len(fotos)} Fotos, Laden {e['sekunden_laden']} s, "
                  + ", ".join(f"{b} {z}" for b, z in zaehlen(e["fotos"], en).items()))
    print(f"Fertig: {ausgabe}")
    return 0 if fertig else 1


if __name__ == "__main__":
    sys.exit(main())
