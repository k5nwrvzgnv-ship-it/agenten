"""Vorlabel mit Claude für Fotobox-Balken auf dem Server (Jan 28.11.2026). Logik in claudelabel.py.

  .venv/bin/python vorlabel_claude.py --balken B004 B005            rechnet, schreibt data/vorlabel-claude/<Zeit>/
  .venv/bin/python vorlabel_claude.py --einfuegen data/vorlabel-claude/<Zeit>/ergebnis.json
                                                                    fügt das geprüfte Ergebnis in die Labels ein

Ablauf: Fotos wie im Labeln gezeigt (ohne leere und doppelte), Zuschnitt aus der Vorschau (2400 px, gleicher
Zuschnitt wie am Mac, Labels sind Anteile), Bild mit Lineal in einen Lese-Ordner, je Lauf einige Fotos an Claude
(claude_lauf, nur Read in diesem Ordner, außerhalb des Repos, Konto des Agenten), Antwort prüfen, Umrisse mit opencv,
Kontrollbilder. Einfügen wie das Vorlabeln vom Mac (Kette.vorlabel_einfuegen): bestätigte und von Hand gezeichnete
Objekte bleiben, alte offene Vorlabel werden ersetzt. Zwischen den Läufen eine Pause, damit Rüdiger drankommt."""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
from PIL import Image

from agentkit import claude_lauf

import claudelabel as cl
from aufnahme import bilder
from aufnahme import kette as k
from aufnahme import klassen as kl

HIER = Path(__file__).resolve().parent
AGENT = "fehlstellenscan"
ORDNER = HIER / "data" / "neurolign" / "aufnahmen"
AUSGABE = HIER / "data" / "vorlabel-claude"
QUELLE = "claude"
PAUSE_S = 20
logger = logging.getLogger("vorlabel_claude")


def kette_bauen(ordner: Path = ORDNER) -> k.Kette:
    def lesen(b):
        return json.loads((ordner / b / "balken.json").read_text(encoding="utf-8"))
    return k.Kette(ordner, lesen, lambda: sorted(p.parent.name for p in ordner.glob("B*/balken.json")))


def fotos_vorbereiten(kette: k.Kette, balken: list[str], ziel: Path, nur: int = 0) -> list[dict]:
    """Zuschnitt aus der Vorschau nach ziel/bilder, Bild mit Lineal nach ziel/lese. Gibt je Foto Name, Pfade, mm."""
    (ziel / "bilder").mkdir(parents=True, exist_ok=True)
    (ziel / "lese").mkdir(parents=True, exist_ok=True)
    ergebnis = []
    for b in balken:
        daten = kette.lesen(b)
        for f in kette.gezeigt(daten):
            original = daten["seiten"][f["seite"]]["fotos"][str(f["nr"])]
            quelle = kette.ordner / b / original.get("vorschau", f["datei"])
            if quelle.suffix.lower() not in (".jpg", ".jpeg", ".png") or not quelle.exists():
                logger.warning("%s: keine lesbare Vorschau (%s), ausgelassen", f["name"], quelle.name)
                continue
            zuschnitt = f["plan"].get("zuschnitt")
            bild = ziel / "bilder" / f"{f['name']}.jpg"
            bilder.schneiden(quelle, bild, ziel / "bilder" / f"{f['name']}_k.jpg", zuschnitt)
            with Image.open(bild) as z:
                cl.mit_lineal(z).save(ziel / "lese" / f"{f['name']}.jpg", quality=90)
            ergebnis.append({"name": f["name"], "bild": str(bild), "datei": str(ziel / "lese" / f"{f['name']}.jpg"),
                             **masse(original, zuschnitt), "holz": f"{daten.get('holzart') or 'Holz'}, "
                                                                f"{daten.get('name') or ''}".strip(", ")})
            if nur and len(ergebnis) >= nur:
                break
        else:
            continue
        break
    (ziel / "fotos.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")
    return ergebnis


def masse(f: dict, zuschnitt) -> dict:
    """Breite und Höhe des Zuschnitts in mm aus Fotogröße und px_je_mm (wie bilder.schneiden: hochkant wird gedreht)."""
    b, h, pxmm = f.get("breite_px"), f.get("hoehe_px"), f.get("px_je_mm")
    if not (b and h and pxmm):
        return {"breite_mm": 0.0, "hoehe_mm": 0.0}
    b, h = max(b, h), min(b, h)
    _, _, zb, zh = zuschnitt or (0, 0, 1, 1)
    return {"breite_mm": b * zb / pxmm, "hoehe_mm": h * zh / pxmm}


def claude_fragen(text: str, lese: Path) -> claude_lauf.Ergebnis:
    for _ in range(40):
        try:
            return claude_lauf.laufen(AGENT, HIER, text, art="anspruchsvoll", lese_ordner=[lese], werkzeuge=[],
                                      ohne_projekt=True)
        except claude_lauf.LaeuftSchon:
            time.sleep(15)
    raise claude_lauf.LaeuftSchon("fehlstellenscan blieb belegt")


def rechnen(balken: list[str], je_lauf: int, nur: int, ziel: Path) -> dict:
    kette = kette_bauen()
    klassen = kette.klassen()
    ids = {x["schluessel"]: x["id"] for x in klassen["klassen"] if x["aktiv"]}
    namen = {x["id"]: x["name"] for x in klassen["klassen"]}
    fotos = fotos_vorbereiten(kette, balken, ziel, nur)
    logger.info("%d Fotos vorbereitet in %s", len(fotos), ziel)
    (ziel / "antworten").mkdir(exist_ok=True)
    (ziel / "kontrolle").mkdir(exist_ok=True)
    funde, kosten, fehlt = {}, {"usd": 0.0, "tokens": 0, "laeufe": 0}, []
    offen = [fotos[i:i + je_lauf] for i in range(0, len(fotos), je_lauf)]
    for n, teil in enumerate(offen, 1):
        if n > 1:
            time.sleep(PAUSE_S)
        e = claude_fragen(cl.prompt(teil, klassen), ziel / "lese")
        kosten["usd"] += e.usd
        kosten["tokens"] += e.tokens
        kosten["laeufe"] += 1
        (ziel / "antworten" / f"{n:03d}.txt").write_text(e.text, encoding="utf-8")
        try:
            antwort = cl.antwort_lesen(e.text, [f["name"] for f in teil], klassen) if e.ok else {}
        except ValueError as f:
            logger.warning("Lauf %d: Antwort nicht lesbar: %s", n, f)
            antwort = {}
        funde.update(antwort)
        fehlt += [f["name"] for f in teil if f["name"] not in antwort]
        logger.info("Lauf %d/%d: %d Fotos, %d Funde, %.2f USD", n, len(offen), len(antwort),
                    sum(len(v) for v in antwort.values()), e.usd)
    ergebnis = {}
    for f in fotos:
        if f["name"] not in funde:
            continue
        bgr = cv2.imread(f["bild"])
        ergebnis[f["name"]] = cl.objekte(bgr, funde[f["name"]], ids, QUELLE)
        with Image.open(f["bild"]) as z:
            cl.kontrolle(z, ergebnis[f["name"]], namen).save(ziel / "kontrolle" / f"{f['name']}.jpg", quality=85)
    (ziel / "funde.json").write_text(json.dumps(funde, ensure_ascii=False, indent=1), encoding="utf-8")
    (ziel / "ergebnis.json").write_text(json.dumps(ergebnis, ensure_ascii=False), encoding="utf-8")
    bericht = {"balken": balken, "fotos": len(fotos), "beantwortet": len(funde), "fehlt": fehlt,
               "objekte": sum(len(v) for v in ergebnis.values()), "kosten": kosten,
               "je_klasse": {namen[i]: sum(o["k"] == i for v in ergebnis.values() for o in v) for i in namen}}
    (ziel / "bericht.json").write_text(json.dumps(bericht, ensure_ascii=False, indent=1), encoding="utf-8")
    return bericht


def aus_funde(ziel: Path, funde: dict, quelle: str) -> dict:
    """Umrisse und Kontrollbilder aus fertigen Funden (Kästchen), ohne Claude-Lauf. Fotos aus ziel/fotos.json."""
    kette = kette_bauen()
    klassen = kette.klassen()
    ids = {x["schluessel"]: x["id"] for x in klassen["klassen"] if x["aktiv"]}
    namen = {x["id"]: x["name"] for x in klassen["klassen"]}
    fotos = json.loads((ziel / "fotos.json").read_text(encoding="utf-8"))
    geprueft = cl.antwort_lesen(json.dumps({"fotos": funde}), [f["name"] for f in fotos], klassen)
    (ziel / "kontrolle").mkdir(exist_ok=True)
    ergebnis = {}
    for f in fotos:
        if f["name"] in geprueft:
            ergebnis[f["name"]] = cl.objekte(cv2.imread(f["bild"]), geprueft[f["name"]], ids, quelle)
            with Image.open(f["bild"]) as z:
                cl.kontrolle(z, ergebnis[f["name"]], namen).save(ziel / "kontrolle" / f"{f['name']}.jpg", quality=85)
    (ziel / "ergebnis.json").write_text(json.dumps(ergebnis, ensure_ascii=False), encoding="utf-8")
    return {"fotos": len(fotos), "mit_funden": len(ergebnis), "objekte": sum(len(v) for v in ergebnis.values()),
            "fehlt": [f["name"] for f in fotos if f["name"] not in geprueft],
            "je_klasse": {namen[i]: n for i in namen if (n := sum(o["k"] == i for v in ergebnis.values() for o in v))}}


def einfuegen(datei: Path) -> dict:
    ergebnis = json.loads(datei.read_text(encoding="utf-8"))
    kette = kette_bauen()
    aktiv = kl.aktive_ids(kette.klassen())
    for objekte in ergebnis.values():
        objekte[:] = [o for o in objekte if o["k"] in aktiv]
    return kette.vorlabel_einfuegen(ergebnis, "vorlabel")


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    a.add_argument("--balken", nargs="+")
    a.add_argument("--je-lauf", type=int, default=4, help="Fotos je Claude-Lauf")
    a.add_argument("--nur", type=int, default=0, help="nur die ersten N Fotos (Probe)")
    a.add_argument("--einfuegen", type=Path, help="ergebnis.json in die Labels einfügen")
    a.add_argument("--vorbereiten", action="store_true", help="nur Zuschnitte und Bilder mit Lineal, ohne Claude")
    a.add_argument("--funde", type=Path, help="Funde (wie Claudes Antwort, {Foto: [...]}) statt Claude-Lauf")
    a.add_argument("--ziel", type=Path, help="Ordner eines vorbereiteten Laufs (mit --funde)")
    a.add_argument("--quelle", default=QUELLE, help="Wert für q der Vorlabel")
    x = a.parse_args(argv)
    if x.funde:
        if not x.ziel:
            a.error("--funde braucht --ziel")
        funde = json.loads(x.funde.read_text(encoding="utf-8"))
        print(json.dumps(aus_funde(x.ziel, funde.get("fotos", funde), x.quelle), ensure_ascii=False, indent=1))
        return 0
    if x.einfuegen:
        print(json.dumps(einfuegen(x.einfuegen), ensure_ascii=False))
        return 0
    if not x.balken:
        a.error("--balken oder --einfuegen")
    ziel = AUSGABE / datetime.now().strftime("%Y%m%d-%H%M%S")
    if x.vorbereiten:
        fotos = fotos_vorbereiten(kette_bauen(), x.balken, ziel, x.nur)
        print(f"{len(fotos)} Fotos vorbereitet: {ziel}")
        return 0
    print(json.dumps(rechnen(x.balken, max(1, x.je_lauf), x.nur, ziel), ensure_ascii=False, indent=1))
    print(f"Ausgabe: {ziel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
