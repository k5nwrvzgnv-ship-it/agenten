"""Datensatz Kodytek et al. (Zenodo 10.5281/zenodo.4694695) ins YOLO-Format umwandeln und prüfen.

Läuft auf dem Server (11 Probebilder, alle Box-Dateien) und von Hand auf Jans Mac (alle Bilder). Deshalb nur
Python-Bordmittel und Pillow (Bildgröße), numpy nur für die Überlappungsprüfung; kein agentkit, kein PyTorch.

Befehle (Einzelheiten mit --help, Anleitung in STATUS.md):
  statistik    Box-Größen je Klasse in Trainingspixeln für imgsz 640, 1280 und volle Auflösung (Kacheln)
  aufteilung   Gruppen auf train/val/test verteilen und als JSON einfrieren (nur aus den Box-Dateien)
  bauen        YOLO-Ordner mit images/, labels/, data.yaml, bericht.json, manifest.json, DATENKARTE.md
  ueberlappung Nachbarbilder einer Gruppe auf Überlappung prüfen (Stichprobe)

Box-Format der Quelle (geprüft, siehe STATUS.md): je Bild <nummer>_anno.txt, je Zeile
Klasse TAB x1 TAB y1 TAB x2 TAB y2, Werte 0..1 relativ zur echten Bildgröße, (x2, y2) ausschließlich,
teils Dezimalkomma. Leere Datei = Bild ohne Fehlstelle.
"""

import argparse
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

# Feste Nummern 0-9 in der Reihenfolge der Semantic Map Specification (Label 1-8, 10, 11).
KLASSEN = ["live_knot", "dead_knot", "knot_missing", "knot_with_crack", "crack",
           "quartzity", "resin", "marrow", "blue_stain", "overgrown"]
NUMMER = {name: i for i, name in enumerate(KLASSEN)}

TEILE = ("train", "val", "test")
ANTEILE = (0.8, 0.1, 0.1)
MIN_PX = 2              # Jan 12.11.2026: Boxen unter 2 px in einer Richtung sind Klickfehler
SEED = 20261112
BREITE_NENN, HOEHE_NENN = 2800, 1024   # nur für Statistik und Aufteilung ohne Bilder; beim Bauen echte Größe
GRUPPE_STELLEN = 5      # Nummer = <Gruppe><5 Ziffern>, eine Gruppe ist vermutlich ein Brett oder Durchlauf

QUELLE = ("Kodytek P., Bodzas A., Bilik P.: A large-scale image dataset of wood surface defects for automated "
          "vision-based quality control processes. F1000Research 10:581 (2021, v2 2022). "
          "Daten: Zenodo 10.5281/zenodo.4694695, Lizenz CC BY 4.0.")


@dataclass(frozen=True)
class Box:
    klasse: int
    x1: float
    y1: float
    x2: float
    y2: float


# ---------------------------------------------------------------- Lesen und Umrechnen (reine Logik)

def klasse_nummer(name: str) -> int:
    """Klassenname der Box-Datei (z. B. Live_Knot) auf die feste Nummer. Unbekannt = Fehler."""
    schluessel = name.strip().lower()
    if schluessel not in NUMMER:
        raise ValueError(f"unbekannte Klasse {name!r}")
    return NUMMER[schluessel]


def zeile_lesen(zeile: str) -> Box:
    """Eine Zeile der Box-Datei. Dezimalkomma wird zu Punkt. Ecken müssen in 0..1 liegen, x1 < x2, y1 < y2."""
    teile = zeile.strip().split("\t")
    if len(teile) != 5:
        raise ValueError(f"Zeile hat {len(teile)} statt 5 Felder: {zeile!r}")
    x1, y1, x2, y2 = (float(t.replace(",", ".")) for t in teile[1:])
    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
        raise ValueError(f"Ecken außerhalb 0..1 oder vertauscht: {zeile!r}")
    return Box(klasse_nummer(teile[0]), x1, y1, x2, y2)


def datei_lesen(text: str) -> tuple[list[Box], bool]:
    """Inhalt einer _anno.txt als (Boxen, hatte_komma). Leerer Inhalt = keine Fehlstelle."""
    zeilen = [z for z in text.splitlines() if z.strip()]
    hatte_komma = any("," in z for z in zeilen)
    return [zeile_lesen(z) for z in zeilen], hatte_komma


def groesse_px(box: Box, breite: int, hoehe: int) -> tuple[float, float]:
    return (box.x2 - box.x1) * breite, (box.y2 - box.y1) * hoehe


def filtern(boxen: list[Box], breite: int, hoehe: int, min_px: float) -> tuple[list[Box], list[Box]]:
    """Teilt in (behalten, aussortiert): aussortiert, wenn Breite oder Höhe unter min_px Pixel liegt."""
    behalten, weg = [], []
    for b in boxen:
        # gerundet: die Quelle hat 6 Nachkommastellen, 2/2800*2800 ergibt sonst 1,9999999 und fiele heraus
        bp, hp = (round(v, 3) for v in groesse_px(b, breite, hoehe))
        (weg if bp < min_px or hp < min_px else behalten).append(b)
    return behalten, weg


def zu_yolo(box: Box) -> str:
    """YOLO-Zeile "klasse x_mitte y_mitte breite hoehe". Die Quelle ist schon relativ zur echten Bildgröße."""
    return (f"{box.klasse} {(box.x1 + box.x2) / 2:.6f} {(box.y1 + box.y2) / 2:.6f} "
            f"{box.x2 - box.x1:.6f} {box.y2 - box.y1:.6f}")


def von_yolo(zeile: str) -> Box:
    """Umkehrung von zu_yolo (für Tests und Gegenproben)."""
    k, xm, ym, b, h = zeile.split()
    xm, ym, b, h = float(xm), float(ym), float(b), float(h)
    return Box(int(k), xm - b / 2, ym - h / 2, xm + b / 2, ym + h / 2)


def gruppe(nummer: str) -> str:
    """Gruppe einer Bildnummer: alles vor den letzten 5 Ziffern (100000061 -> 1000, 99100031 -> 991)."""
    if not nummer.isdigit() or len(nummer) <= GRUPPE_STELLEN:
        raise ValueError(f"keine Bildnummer: {nummer!r}")
    return nummer[:-GRUPPE_STELLEN]


def data_yaml(pfad: str, val: str = "images/val", test: str | None = "images/test") -> str:
    """Inhalt der data.yaml für ultralytics (Klassennamen mit fester Nummer)."""
    zeilen = [f"path: {pfad}", "train: images/train", f"val: {val}"]
    if test:
        zeilen.append(f"test: {test}")
    zeilen.append("names:")
    zeilen += [f"  {i}: {name}" for i, name in enumerate(KLASSEN)]
    return "\n".join(zeilen) + "\n"


# ---------------------------------------------------------------- Aufteilung (reine Logik)

def _fehlt(hat: dict, gesamt: Counter, anteile: tuple, teil: str, schluessel) -> float:
    """Anteil am Gesamtbestand, der dem Teil für diesen Schlüssel noch fehlt."""
    soll = anteile[TEILE.index(teil)] * gesamt[schluessel]
    return (soll - hat[teil][schluessel]) / max(gesamt[schluessel], 1)


def aufteilen(gruppen: dict[str, Counter], seed: int = SEED,
              anteile: tuple[float, ...] = ANTEILE) -> dict[str, str]:
    """Verteilt ganze Gruppen auf train/val/test, damit Bilder eines Bretts nie in zwei Teilen landen.

    gruppen: Gruppe -> Counter mit "_bilder" (Anzahl Bilder) und Klassennummer -> Anzahl Boxen.
    Gierig, seltene Klassen zuerst: Gruppen mit der seltensten Klasse werden zuerst verteilt, jeweils in den
    Teil, dem für diese Klasse anteilig am meisten fehlt (Gleichstand: dem an Bildern am meisten fehlt).
    Reihenfolge innerhalb gleicher Seltenheit per festem Zufall, also bei gleichem Seed immer gleich.
    """
    gesamt: Counter = Counter()
    for c in gruppen.values():
        gesamt.update(c)
    rng = random.Random(seed)
    namen = sorted(gruppen)
    rng.shuffle(namen)

    def seltenste(g: str) -> float:
        klassen = [k for k in gruppen[g] if k != "_bilder" and gruppen[g][k] > 0]
        return min((gesamt[k] for k in klassen), default=float("inf"))

    namen.sort(key=seltenste)          # stabil: Zufallsreihenfolge bleibt innerhalb gleicher Seltenheit
    hat = {t: Counter() for t in TEILE}
    ergebnis = {}
    for g in namen:
        c = gruppen[g]
        klassen = [k for k in c if k != "_bilder" and c[k] > 0]
        selten = min(klassen, key=lambda k: gesamt[k]) if klassen else None

        teil = max(TEILE, key=lambda t, s=selten: (_fehlt(hat, gesamt, anteile, t, s) if s is not None else 0.0,
                                                  _fehlt(hat, gesamt, anteile, t, "_bilder")))
        ergebnis[g] = teil
        hat[teil].update(c)
    return ergebnis


# ---------------------------------------------------------------- Statistik (reine Logik)

MASSSTAEBE = {"imgsz 640": 640 / BREITE_NENN, "imgsz 1280": 1280 / BREITE_NENN, "volle Aufloesung": 1.0}


def statistik(boxen: list[Box], breite: int = BREITE_NENN, hoehe: int = HOEHE_NENN) -> dict:
    """Je Klasse: Anzahl, Median der kürzeren Seite in px und Anteil der Boxen, deren kürzere Seite nach dem
    Verkleinern unter 8 px (kleinste YOLO-Stufe, Stride 8) bzw. 16 px liegt."""
    je_klasse: dict[int, list[float]] = defaultdict(list)
    for b in boxen:
        je_klasse[b.klasse].append(min(groesse_px(b, breite, hoehe)))
    ergebnis = {}
    for k in sorted(je_klasse):
        werte = sorted(je_klasse[k])
        zeile = {"anzahl": len(werte), "median_kurze_seite_px": round(werte[len(werte) // 2], 1)}
        for name, m in MASSSTAEBE.items():
            zeile[name] = {f"unter_{s}px": round(sum(w * m < s for w in werte) / len(werte), 3) for s in (8, 16)}
        ergebnis[KLASSEN[k]] = zeile
    return ergebnis


# ---------------------------------------------------------------- Überlappung (numpy, nur auf Auftrag)

def ueberlappung(a, b, streifen: int = 32, rand: int = 400) -> dict:
    """Prüft zwei Graubilder (numpy-Arrays) auf gemeinsame Zeilen.

    Die Maserung läuft längs und ähnelt sich überall, deshalb wird je Bild das Spaltenmittel abgezogen und der
    schwarze Rand links und rechts abgeschnitten. Dann wird der letzte Streifen von a in b gesucht und umgekehrt.
    Bei echter Überlappung liegt die beste Korrelation nahe 1, bei fremden Bildern deutlich darunter
    (Probe 12.11.2026: Nachbarbilder 0,2-0,43, fremdes Paar 0,26-0,29).
    """
    import numpy as np
    w = min(a.shape[1], b.shape[1])
    a = a[:, rand:w - rand].astype(np.float32)
    b = b[:, rand:w - rand].astype(np.float32)
    a = a - a.mean(axis=0, keepdims=True)
    b = b - b.mean(axis=0, keepdims=True)

    def kor(x, y) -> float:
        x = x - x.mean()
        y = y - y.mean()
        nenner = float(np.sqrt((x * x).sum() * (y * y).sum()))
        return float((x * y).sum()) / nenner if nenner else 0.0

    def suchen(s, ziel) -> tuple[float, int]:
        return max((kor(s, ziel[k:k + streifen]), k) for k in range(0, ziel.shape[0] - streifen + 1, 2))

    ab, ab_zeile = suchen(a[-streifen:], b)
    ba, ba_zeile = suchen(b[-streifen:], a)
    return {"a_ende_in_b": round(ab, 3), "zeile_in_b": ab_zeile, "b_ende_in_a": round(ba, 3), "zeile_in_a": ba_zeile}


# ---------------------------------------------------------------- Dateien (dünn)

def box_dateien(ordner: Path) -> dict[str, Path]:
    """Bildnummer -> _anno.txt (rekursiv)."""
    return {p.name[:-len("_anno.txt")]: p for p in ordner.rglob("*_anno.txt")}


def bild_dateien(ordner: Path) -> dict[str, Path]:
    """Bildnummer -> .bmp (rekursiv), ohne Masken (_segm.bmp)."""
    return {p.stem: p for p in ordner.rglob("*.bmp") if p.stem.isdigit()}


def alle_boxen_lesen(ordner: Path) -> tuple[dict[str, list[Box]], list[str]]:
    """Alle Box-Dateien als (Nummer -> Boxen, Nummern mit Dezimalkomma)."""
    boxen, komma = {}, []
    for nummer, pfad in sorted(box_dateien(ordner).items()):
        try:
            boxen[nummer], hatte = datei_lesen(pfad.read_text(encoding="utf-8"))
        except ValueError as fehler:
            raise ValueError(f"{pfad.name}: {fehler}") from None
        if hatte:
            komma.append(nummer)
    return boxen, komma


def gruppen_zaehlen(boxen: dict[str, list[Box]], min_px: float) -> dict[str, Counter]:
    """Zählung je Gruppe für aufteilen() (mit Nenngröße gefiltert, die Aufteilung braucht keine Bilder)."""
    gruppen: dict[str, Counter] = defaultdict(Counter)
    for nummer, liste in boxen.items():
        behalten, _ = filtern(liste, BREITE_NENN, HOEHE_NENN, min_px)
        c = gruppen[gruppe(nummer)]
        c["_bilder"] += 1
        c.update(b.klasse for b in behalten)
    return dict(gruppen)


def md5(pfad: Path) -> str:
    h = hashlib.md5()
    with open(pfad, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def bildgroesse(pfad: Path) -> tuple[int, int]:
    from PIL import Image          # liest nur den Kopf der Datei
    with Image.open(pfad) as bild:
        return bild.size


def git_stand() -> str:
    try:
        return subprocess.run(["git", "-C", str(Path(__file__).parent), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unbekannt (Datei ohne Git, z. B. auf dem Mac)"


def ablegen(quelle: Path, ziel: Path, kopieren: bool) -> None:
    if kopieren:
        shutil.copy2(quelle, ziel)
    else:
        os.link(quelle, ziel)      # Hardlink: kein zusätzlicher Platz, Original bleibt unverändert


DATENKARTE = """# Datenkarte {name}

Quelle: {quelle}

- Aufnahme: Schnittholz aus einer Sägewerkslinie, Zeilenkamera, Farb-BMP 1024 hoch, meist 2800 breit
  (155 Bilder 2709-2799). Holzart im Paper nicht genannt. Schwarzer Hintergrund links und rechts des Bretts,
  in manchen Bildern senkrechte Nahtstellen mit Helligkeitssprung.
- Klassen (feste Nummern): {klassen}
- Boxen aus den Box-Dateien der Quelle, unverändert umgerechnet. Aussortiert: Boxen unter {min_px} px in einer
  Richtung (Klickfehler). Bilder, die dadurch alle Boxen verlieren, sind weggelassen (nicht "ohne Fehler").
- Bekannte Mängel: nicht alle sichtbaren Merkmale sind markiert (z. B. 100000022). overgrown hat nur wenige
  brauchbare Boxen, blue_stain unter 100: beide in der Auswertung mit Vorsicht.
- Aufteilung nach Gruppen (Nummer ohne die letzten 5 Ziffern, vermutlich ein Brett), eingefroren in
  {aufteilung}. Keine Gruppe liegt in zwei Teilen. Eine offizielle Aufteilung der Quelle gibt es nicht.
- Zählungen in bericht.json, Prüfsummen in manifest.json.
"""


def bauen(boxen_ordner: Path, bilder_ordner: Path, ziel: Path, aufteilung_datei: Path, min_px: float,
          kopieren: bool = False, nur_vorhandene: bool = False, probe: int = 0, mit_md5: bool = True) -> dict:
    """Baut den YOLO-Ordner. Bricht ab, wenn das Ziel schon existiert, eine Gruppe in der Aufteilung fehlt oder
    (ohne nur_vorhandene) ein Bild fehlt. probe > 0: Überanpassungstest, n Bilder mit Boxen, train = val."""
    if ziel.exists():
        raise FileExistsError(f"{ziel} gibt es schon, nichts überschrieben")
    boxen, komma = alle_boxen_lesen(boxen_ordner)
    bilder = bild_dateien(bilder_ordner)
    eingefroren = json.loads(aufteilung_datei.read_text(encoding="utf-8"))
    teil_von = {g: t for t, liste in eingefroren["teile"].items() for g in liste}

    fehlend = sorted(set(boxen) - set(bilder))
    if fehlend and not nur_vorhandene:
        raise FileNotFoundError(f"{len(fehlend)} Bilder fehlen, z. B. {fehlend[:5]}")
    ohne_box = sorted(set(bilder) - set(boxen))
    if ohne_box:
        raise ValueError(f"{len(ohne_box)} Bilder ohne Box-Datei, z. B. {ohne_box[:5]}")
    unbekannt = sorted({gruppe(n) for n in bilder} - set(teil_von))
    if unbekannt:
        raise ValueError(f"Gruppen fehlen in {aufteilung_datei.name}: {unbekannt[:5]}")

    nummern = sorted(bilder)
    if probe:
        nummern = [n for n in nummern if boxen[n]][:probe]

    zaehlung = {t: {"bilder": 0, "ohne_fehler": 0, "boxen": Counter(), "bilder_je_klasse": Counter()}
                for t in TEILE}
    aussortiert, weggelassen, manifest = [], [], {}
    for t in TEILE:
        (ziel / "images" / t).mkdir(parents=True)
        (ziel / "labels" / t).mkdir(parents=True)
    for nummer in nummern:
        breite, hoehe = bildgroesse(bilder[nummer])
        behalten, weg = filtern(boxen[nummer], breite, hoehe, min_px)
        for b in weg:
            bp, hp = groesse_px(b, breite, hoehe)
            aussortiert.append({"nummer": nummer, "klasse": KLASSEN[b.klasse],
                                "breite_px": round(bp, 1), "hoehe_px": round(hp, 1)})
        if weg and not behalten:
            weggelassen.append(nummer)
            continue
        teil = "train" if probe else teil_von[gruppe(nummer)]
        ablegen(bilder[nummer], ziel / "images" / teil / f"{nummer}.bmp", kopieren)
        (ziel / "labels" / teil / f"{nummer}.txt").write_text(
            "".join(zu_yolo(b) + "\n" for b in behalten), encoding="utf-8")
        z = zaehlung[teil]
        z["bilder"] += 1
        z["ohne_fehler"] += not behalten
        z["boxen"].update(KLASSEN[b.klasse] for b in behalten)
        z["bilder_je_klasse"].update({KLASSEN[b.klasse] for b in behalten})
        if mit_md5:
            manifest[nummer] = md5(bilder[nummer])

    pfad = str(ziel.resolve())
    (ziel / "data.yaml").write_text(
        data_yaml(pfad, val="images/train", test=None) if probe else data_yaml(pfad), encoding="utf-8")
    bericht = {
        "quelle": QUELLE,
        "min_px": min_px,
        "probe": probe,
        "aufteilung": aufteilung_datei.name,
        "klassen": KLASSEN,
        "teile": {t: {**z, "boxen": dict(z["boxen"]), "bilder_je_klasse": dict(z["bilder_je_klasse"])}
                  for t, z in zaehlung.items()},
        "aussortiert": aussortiert,
        "weggelassen_alle_boxen_aussortiert": weggelassen,
        "dateien_mit_dezimalkomma": len(komma),
        "fehlende_bilder": len(fehlend),
    }
    (ziel / "bericht.json").write_text(json.dumps(bericht, ensure_ascii=False, indent=1), encoding="utf-8")
    (ziel / "manifest.json").write_text(json.dumps({
        "git": git_stand(), "min_px": min_px, "kopieren": kopieren, "aufteilung": eingefroren,
        "md5_bilder": manifest}, indent=1), encoding="utf-8")
    (ziel / "DATENKARTE.md").write_text(DATENKARTE.format(
        name=ziel.name, quelle=QUELLE, min_px=min_px, aufteilung=aufteilung_datei.name,
        klassen=", ".join(f"{i} {k}" for i, k in enumerate(KLASSEN))), encoding="utf-8")
    return bericht


# ---------------------------------------------------------------- Befehle

def _statistik(args) -> None:
    boxen, _ = alle_boxen_lesen(args.boxen)
    alle = [b for liste in boxen.values() for b in liste]
    behalten, _ = filtern(alle, BREITE_NENN, HOEHE_NENN, args.min_px)
    print(json.dumps(statistik(behalten), ensure_ascii=False, indent=1))


def _aufteilung(args) -> None:
    boxen, _ = alle_boxen_lesen(args.boxen)
    gruppen = gruppen_zaehlen(boxen, args.min_px)
    zuordnung = aufteilen(gruppen, seed=args.seed)
    teile = {t: sorted(g for g, tt in zuordnung.items() if tt == t) for t in TEILE}
    zaehlung = {}
    for t in TEILE:
        c: Counter = Counter()
        for g in teile[t]:
            c.update(gruppen[g])
        zaehlung[t] = {"bilder": c["_bilder"], **{KLASSEN[k]: c[k] for k in range(len(KLASSEN))}}
    daten = {"quelle": "Kodytek et al., Zenodo 10.5281/zenodo.4694695", "seed": args.seed, "min_px": args.min_px,
             "einheit": f"Gruppe = Bildnummer ohne die letzten {GRUPPE_STELLEN} Ziffern",
             "zaehlung_boxen": zaehlung, "teile": teile}
    args.ausgabe.write_text(json.dumps(daten, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(zaehlung, ensure_ascii=False, indent=1))


def _bauen(args) -> None:
    bericht = bauen(args.boxen, args.bilder, args.ziel, args.aufteilung, args.min_px, kopieren=args.kopieren,
                    nur_vorhandene=args.nur_vorhandene, probe=args.probe, mit_md5=not args.ohne_md5)
    for t, z in bericht["teile"].items():
        print(f"{t}: {z['bilder']} Bilder, {z['ohne_fehler']} ohne Fehler, Boxen {z['boxen']}")
    print(f"aussortiert {len(bericht['aussortiert'])} Boxen, weggelassen "
          f"{len(bericht['weggelassen_alle_boxen_aussortiert'])} Bilder, fehlend {bericht['fehlende_bilder']}, "
          f"Dezimalkomma {bericht['dateien_mit_dezimalkomma']} Dateien")


def _ueberlappung(args) -> None:
    import numpy as np
    from PIL import Image
    bilder = bild_dateien(args.bilder)
    je_gruppe: dict[str, list[str]] = defaultdict(list)
    for n in sorted(bilder):
        je_gruppe[gruppe(n)].append(n)
    rng = random.Random(args.seed)
    gruppen = rng.sample(sorted(g for g, liste in je_gruppe.items() if len(liste) > 1),
                         min(args.anzahl, sum(len(liste) > 1 for liste in je_gruppe.values())))

    def grau(n):
        with Image.open(bilder[n]) as b:
            return np.asarray(b.convert("L"))

    for g in gruppen:
        liste = je_gruppe[g]
        i = rng.randrange(len(liste) - 1)
        nachbar = ueberlappung(grau(liste[i]), grau(liste[i + 1]))
        fremd_n = rng.choice([n for n in bilder if gruppe(n) != g])
        fremd = ueberlappung(grau(liste[i]), grau(fremd_n))
        print(f"{liste[i]}/{liste[i + 1]} Nachbarn {nachbar}  |  gegen {fremd_n} {fremd}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="befehl", required=True)
    s = sub.add_parser("statistik")
    s.add_argument("--boxen", type=Path, required=True)
    s.add_argument("--min-px", type=float, default=MIN_PX)
    s.set_defaults(los=_statistik)
    s = sub.add_parser("aufteilung")
    s.add_argument("--boxen", type=Path, required=True)
    s.add_argument("--ausgabe", type=Path, required=True)
    s.add_argument("--min-px", type=float, default=MIN_PX)
    s.add_argument("--seed", type=int, default=SEED)
    s.set_defaults(los=_aufteilung)
    s = sub.add_parser("bauen")
    s.add_argument("--boxen", type=Path, required=True)
    s.add_argument("--bilder", type=Path, required=True)
    s.add_argument("--ziel", type=Path, required=True)
    s.add_argument("--aufteilung", type=Path, required=True)
    s.add_argument("--min-px", type=float, default=MIN_PX)
    s.add_argument("--kopieren", action="store_true", help="Bilder kopieren statt Hardlink")
    s.add_argument("--nur-vorhandene", action="store_true", help="Box-Dateien ohne Bild überspringen")
    s.add_argument("--probe", type=int, default=0, help="Überanpassungstest: n Bilder, train = val")
    s.add_argument("--ohne-md5", action="store_true")
    s.set_defaults(los=_bauen)
    s = sub.add_parser("ueberlappung")
    s.add_argument("--bilder", type=Path, required=True)
    s.add_argument("--anzahl", type=int, default=20, help="Anzahl Gruppen in der Stichprobe")
    s.add_argument("--seed", type=int, default=SEED)
    s.set_defaults(los=_ueberlappung)
    args = p.parse_args(argv)
    try:
        args.los(args)
    except (ValueError, FileExistsError, FileNotFoundError, OSError) as fehler:
        print(f"FEHLER: {fehler}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
