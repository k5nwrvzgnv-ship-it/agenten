"""Vom Foto zum Training: Fotoliste, Labels, Aufteilung nach Balken, Datensatz- und Trainingslauf. Nur Bordmittel
(läuft mit dem Python des Mac). Bilder rechnet bilder.py in der Trainings-.venv (Pillow, opencv), das Training ist
`yolo segment train` als eigener Prozess. Auf dem Server läuft kein Training.

Ablage: aufnahmen/<Balken>/zuschnitt/<Foto>.jpg und <Foto>_k.jpg, aufnahmen/<Balken>/labels/<Foto>.json,
aufnahmen/teile.json (Balken -> train/val/test), datensaetze/altholz-N, runs/segment/altholz-N."""

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

if __package__:
    from . import saetze as sa
else:
    import saetze as sa

KLASSEN = ["live_knot", "dead_knot", "knot_missing", "knot_with_crack", "crack", "quartzity", "resin", "marrow",
           "blue_stain", "overgrown", "bohrloch", "metall", "nagelloch", "farbe", "faeule", "insektenfrass",
           "verbindung", "fuge"]            # docs/labelrichtlinie.md, 0-9 wie Kodytek
TEILE = ("train", "val", "test")
EPOCHEN = 60
LAUFEND = ("bauen", "training", "pruefen")
HIER = Path(__file__).resolve().parent


def schreiben(pfad: Path, daten) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    neu = pfad.with_suffix(".neu")
    neu.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    neu.replace(pfad)


def objekte_pruefen(werte) -> list[dict]:
    """Objekte aus dem Browser: Klasse und Umriss in Anteilen des Zuschnitts, dazu der Zustand des Editors."""
    if not isinstance(werte, list) or len(werte) > 2000:
        raise ValueError("Labels nicht lesbar.")
    ergebnis = []
    for o in werte:
        if not isinstance(o, dict) or isinstance(o.get("k"), bool) or o.get("k") not in range(len(KLASSEN)):
            raise ValueError("Unbekannte Klasse.")
        p = o.get("p")
        if not isinstance(p, list) or not 3 <= len(p) <= 2000:
            raise ValueError("Umriss nicht lesbar.")
        for q in p:
            if not isinstance(q, list) or len(q) != 2 or any(
                    isinstance(w, bool) or not isinstance(w, (int, float)) or not 0 <= w <= 1 for w in q):
                raise ValueError("Umriss außerhalb des Bildes.")
        ergebnis.append({"k": o["k"], "ok": bool(o.get("ok")), "p": [[round(w, 6) for w in q] for q in p]})
    return ergebnis


def fotos(balken: dict) -> list[dict]:
    """Alle gültigen Fotos eines Balkens, Seite für Seite."""
    ergebnis = []
    for seite, s in sorted(balken["seiten"].items()):
        for nr, f in sorted(s["fotos"].items(), key=lambda x: int(x[0])):
            ergebnis.append({"balken": balken["id"], "seite": seite, "nr": int(nr), "name": Path(f["datei"]).stem,
                             "datei": f["datei"], "plan": s["plan"]})
    return ergebnis


def vorschlag(teile: dict, ids: list[str]) -> dict:
    """Jeder neue Balken bekommt einen Teil: jeder fünfte (ab dem zweiten) prüft, der Rest trainiert."""
    ergebnis = {i: dict(t) for i, t in teile.items()}
    for i in ids:
        if i not in ergebnis:
            n = sum(t["teil"] != "test" for t in ergebnis.values())
            ergebnis[i] = {"teil": "val" if n % 5 == 1 else "train", "fest": False}
    return ergebnis


def pruefung(teile: dict, fotos: list[dict]) -> tuple[dict, str | None]:
    """Fertige Altholz-Fotos (je mit Zahl "objekte") -> ({(Balken, Foto): train/val}, Art der Prüfung). Geprüft wird
    nie auf Trainingsbildern. Art "balken": eigene Prüfbalken (teile.json). Fehlen Prüf- oder Trainingsbalken, wird
    eine ganze Seite zurückgehalten ("seite"): eine mit Objekten, bei der auch das Training Objekte behält, Fotozahl
    nahe einem Fünftel. Gibt es nur eine Seite, die letzten Fotos, ein Fünftel, mindestens eins ("fotos"; Nachbarn
    überlappen). Unter zwei Fotos ({}, None): keine Prüfung möglich. Balken "Nur Test" fehlen immer."""
    benutzt = [f for f in fotos if teile[f["balken"]]["teil"] != "test"]
    if {teile[f["balken"]]["teil"] for f in benutzt} == {"train", "val"}:
        return {(f["balken"], f["name"]): teile[f["balken"]]["teil"] for f in benutzt}, "balken"
    if len(benutzt) < 2:
        return {}, None
    gruppen: dict = {}
    for f in sorted(benutzt, key=lambda f: (f["balken"], f["seite"], f["nr"])):
        gruppen.setdefault((f["balken"], f["seite"]), []).append(f)
    if len(gruppen) > 1:
        ziel, alle = len(benutzt) / 5, sum(f["objekte"] for f in benutzt)

        def guete(x):
            i, g = x
            n = sum(f["objekte"] for f in gruppen[g])
            return (not 0 < n < alle, abs(len(gruppen[g]) - ziel), -i)
        _, wahl = min(enumerate(gruppen), key=guete)
        val = gruppen[wahl]
        art = "seite"
    else:
        reihe = next(iter(gruppen.values()))
        val = reihe[-max(1, round(len(reihe) / 5)):]
        art = "fotos"
    zurueck = {(f["balken"], f["name"]) for f in val}
    return {(f["balken"], f["name"]): "val" if (f["balken"], f["name"]) in zurueck else "train"
            for f in benutzt}, art


def epochen_gelesen(pfad: Path) -> list[dict]:
    if not pfad.exists():
        return []
    with pfad.open(encoding="utf-8") as f:
        return [{k.strip(): v.strip() for k, v in z.items() if k and v} for z in csv.DictReader(f)]


KENNZAHLEN = ("p", "r", "map50", "map")                  # Reihenfolge in der Tabelle von ultralytics


def args_gelesen(pfad: Path) -> dict:
    """Einfache Schlüssel aus args.yaml (ultralytics schreibt eine flache Liste `name: wert`)."""
    if not pfad.exists():
        return {}
    werte = {}
    for z in pfad.read_text(encoding="utf-8").splitlines():
        if (t := re.fullmatch(r"(\w+): (.*)", z)) and t[2] not in ("null", ""):
            werte[t[1]] = t[2].strip("'\"")
    return werte


def tabelle_gelesen(text: str) -> list[dict]:
    """Abschlusstabelle aus dem Trainingslog: ultralytics prüft am Ende best.pt und schreibt je Klasse eine Zeile
    `Klasse Bilder Objekte Box(P R mAP50 mAP50-95) Mask(P R mAP50 mAP50-95)`, die erste heißt `all`. Während der
    Epochen steht dort nur `all`, ohne Abschluss also höchstens eine Zeile."""
    zeilen = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text).replace("\r", "\n").splitlines()
    kopf = max((i for i, z in enumerate(zeilen) if "Class" in z and "Mask(P" in z), default=None)
    if kopf is None:
        return []
    tabelle = []
    for z in zeilen[kopf + 1:]:
        t = re.fullmatch(r"\s*(\S+)\s+(\d+)\s+(\d+)((?:\s+[\d.]+){8})\s*", z)
        if not t:
            if tabelle:
                break
            continue
        w = [float(x) for x in t[4].split()]
        tabelle.append({"klasse": t[1], "bilder": int(t[2]), "objekte": int(t[3]),
                        "box": dict(zip(KENNZAHLEN, w[:4], strict=True)),
                        "maske": dict(zip(KENNZAHLEN, w[4:], strict=True))})
    return tabelle


def spalten(z: dict, art: str) -> dict:
    s = {"p": "precision", "r": "recall", "map50": "mAP50", "map": "mAP50-95"}
    return {k: float(z[f"metrics/{n}({art})"]) for k, n in s.items() if f"metrics/{n}({art})" in z}


def tabelle_aus(log: Path) -> list[dict] | None:
    """Abschlusstabelle aus einer Logdatei, None ohne gültige Tabelle (erste Zeile all, mindestens eine Klasse)."""
    tabelle = tabelle_gelesen(log.read_text(encoding="utf-8", errors="replace")) if log.exists() else []
    return tabelle if len(tabelle) >= 2 and tabelle[0]["klasse"] == "all" else None


def mit_nummer(klassen: list[dict]) -> list[dict]:
    return [{**t, "k": KLASSEN.index(t["klasse"]) if t["klasse"] in KLASSEN else None} for t in klassen]


def ergebnis_gelesen(lauf: Path, log: Path, bericht: Path, pruef_log: Path | None = None) -> dict | None:
    """Ergebnis eines fertigen Laufs aus dem, was ultralytics und bilder.py schreiben. None ohne Abschlusstabelle.
    pruef_log: Log der zweiten Prüfung von best.pt nur auf Altholz (wenn Altholz mit anderen Sätzen trainiert wurde)."""
    tabelle = tabelle_aus(log)
    if not tabelle:
        return None
    z = epochen_gelesen(lauf / "results.csv")
    # best.pt ist die Epoche mit der höchsten Fitness von ultralytics: je 0,1 mAP50 + 0,9 mAP50-95 für Box und
    # Maske (geprüft an kodytek-seg1-n1280: Epoche 37 trifft die Abschlusstabelle)
    fit = [sum(0.1 * w.get("map50", 0) + 0.9 * w.get("map", 0) for w in (spalten(x, "B"), spalten(x, "M")))
           for x in z]
    beste = z[fit.index(max(fit))] if z else None
    args = args_gelesen(lauf / "args.yaml")
    modell = args.get("model", "")
    if "/weights/" in modell:                  # eigenes Modell: Name des Laufs statt Pfad
        modell = Path(modell).parents[1].name
    zahl = json.loads(bericht.read_text(encoding="utf-8")) if bericht.exists() else {}
    kacheln = zahl.get("kacheln", {})
    probe = zahl.get("probe")                  # alte Läufe: Ablaufprobe, geprüft auf den Trainingsbildern
    klassen = mit_nummer(tabelle[1:])
    altholz = tabelle_aus(pruef_log) if pruef_log else None
    return {"gesamt": tabelle[0], "klassen": klassen, "probe": probe, "pruefung": zahl.get("pruefung"),
            "altholz": {"gesamt": altholz[0], "klassen": mit_nummer(altholz[1:])} if altholz else None,
            "beste": int(float(beste["epoch"])) if beste else None, "gelaufen": len(z),
            "epochen": int(args["epochs"]) if args.get("epochs", "").isdigit() else None,
            "sekunden": float(z[-1]["time"]) if z and "time" in z[-1] else None,
            "modell": Path(modell).stem if modell else None, "imgsz": args.get("imgsz"), "batch": args.get("batch"),
            "train": kacheln.get("train"), "val": kacheln.get("train") if probe else kacheln.get("val")}


class Kette:
    def __init__(self, ordner: Path, lesen, ids):
        self.ordner, self.wurzel, self.lesen, self.ids = ordner, ordner.parent, lesen, ids
        self.schloss = threading.RLock()
        self.python = self.wurzel / ".venv" / "bin" / "python"
        self.yolo = self.wurzel / ".venv" / "bin" / "yolo"
        self.schneiden_schloss = threading.Lock()
        self.saetze_schloss = threading.Lock()
        self.koerper_schloss = threading.Lock()
        self._fremde: list[Path] | None = None
        self._zahlen: dict = {}
        self._auswahl: list[dict] | None = None
        self.lauf: dict | None = None
        self.prozess: subprocess.Popen | None = None
        self._ergebnis: tuple = (None, None)

    # ------------------------------------------------------ Bilder und Labels
    def alle(self) -> list[dict]:
        return [f for i in self.ids() for f in fotos(self.lesen(i))]

    def foto(self, name) -> dict:
        liste = self.kodytek() if str(name).startswith("kodytek_") else self.alle()
        treffer = [f for f in liste if f["name"] == name]
        if not treffer:
            raise ValueError("Dieses Foto gibt es nicht mehr.")
        return treffer[0]

    def label_pfad(self, f: dict) -> Path:
        return self.ordner / f["balken"] / "labels" / f"{f['name']}.json"

    def label(self, f: dict) -> dict | None:
        p = self.label_pfad(f)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    # ------------------------------------------------------ Kodytek-Auswahl und fertige Datensätze
    def kodytek(self) -> list[dict]:
        """Auswahl aus Kodytek zum Korrigieren, einmal gezogen und dann fest (aufnahmen/kodytek/auswahl.json)."""
        with self.saetze_schloss:
            if self._auswahl is None:
                p, quelle = self.ordner / "kodytek" / "auswahl.json", self.wurzel / "datensaetze" / sa.QUELLE
                if p.exists():
                    roh = json.loads(p.read_text(encoding="utf-8"))
                elif (quelle / "data.yaml").exists():
                    roh = sa.auswahl_ziehen(quelle)
                    if roh:
                        schreiben(p, roh)
                else:
                    return []
                self._auswahl = [{"balken": "kodytek", "name": e["name"], "datei": e["bild"], "teil": e["teil"],
                                  "plan": {"zuschnitt": None}} for e in roh]
            return self._auswahl

    def original(self, f: dict) -> str:
        return sa.label_zu(Path(f["datei"])).read_text(encoding="utf-8")

    def fremde(self) -> list[Path]:
        if self._fremde is None:
            self._fremde = sa.gefunden(self.wurzel, KLASSEN)
        return self._fremde

    def zahl(self, ordner: Path, teil: str) -> int:
        """Bilder eines Teils, neu gezählt nur, wenn sich der Ordner ändert."""
        weg = ordner / "images" / teil
        stempel = weg.stat().st_mtime_ns if weg.is_dir() else 0
        if self._zahlen.get(weg, (None, 0))[0] != stempel:
            self._zahlen[weg] = (stempel, len(sa.bilder_in(ordner, teil)))
        return self._zahlen[weg][1]

    def saetze(self) -> list[dict]:
        ergebnis = []
        if kod := self.kodytek():
            ergebnis.append({"id": "kodytek", "name": "Kodytek-Auswahl",
                             "train": sum(f["teil"] == "train" for f in kod),
                             "val": sum(f["teil"] == "val" for f in kod),
                             "fertig": sum(self.fertig(f) for f in kod)})
        ergebnis += [{"id": o.name, "name": f"{o.name} (ganz)", "train": self.zahl(o, "train"),
                      "val": self.zahl(o, "val"), "fertig": None} for o in self.fremde()]
        return ergebnis

    def kodytek_bilder(self) -> list[dict]:
        gesamt = []
        for f in self.kodytek():
            x = self.label(f)
            gesamt.append({"name": f["name"], "balken": "kodytek", "titel": f["name"][8:], "laengs_mm": None,
                           "objekte": x["objekte"] if x else sa.objekte_aus(self.original(f)),
                           "zeit": x["zeit"] if x else None})
        return gesamt

    def bilder(self) -> list[dict]:
        gesamt = []
        for f in self.alle():
            x = self.label(f)
            # Maße in mm gelten nur mit gemessenem Bildwinkel, sonst zeigt die Oberfläche Pixel
            p = f["plan"]
            gemessen = abs(p["faktor"] - 24 / 34.6) > 1e-9
            gesamt.append({"name": f["name"], "balken": f["balken"], "seite": f["seite"], "nr": f["nr"],
                           "titel": f"{f['balken']} Seite {f['seite']}, {f['nr'] + 1}", "laengs_mm": p["laengs_mm"] if gemessen else None,
                           "objekte": x["objekte"] if x else None, "zeit": x["zeit"] if x else None})
        return gesamt

    def speichern(self, daten: dict, von: str | None = None) -> dict:
        """Schickt der Browser "stand" (Zeit des Labels, das er geladen hat, oder None), wird nur gespeichert, wenn
        inzwischen niemand anderes gespeichert hat. Zwei Personen am selben Foto überschreiben sich so nicht still."""
        objekte = objekte_pruefen(daten.get("objekte"))
        with self.schloss:
            f = self.foto(daten.get("name"))
            if "stand" in daten:
                alt = self.label(f)
                if (alt or {}).get("zeit") != daten["stand"]:
                    wer = f" von {alt['von']}" if alt and alt.get("von") else ""
                    raise ValueError(f"Inzwischen{wer} gespeichert ({(alt or {}).get('zeit', '')[11:16]}). "
                                     "Seite neu laden, dann weiter.")
            zeit = datetime.now().isoformat(timespec="seconds")
            neu = {"foto": f["datei"], "zuschnitt": f["plan"]["zuschnitt"], "zeit": zeit, "objekte": objekte}
            if von:
                neu["von"] = von
            schreiben(self.label_pfad(f), neu)
        return {"zeit": zeit}

    def umgebung(self) -> Path:
        if not self.python.exists():
            raise ValueError(f"Trainings-Umgebung fehlt: {self.python}")
        return self.python

    def zuschnitt(self, name: str, klein: bool = False) -> Path:
        """Zugeschnittenes JPG, beim ersten Aufruf erzeugt. Das Original bleibt unberührt."""
        f = self.foto(name)
        ziel = self.ordner / f["balken"] / "zuschnitt" / f"{name}.jpg"
        kl = ziel.with_name(f"{name}_k.jpg")
        with self.schneiden_schloss:
            if not (ziel.exists() and kl.exists()):
                quelle = self.ordner / f["balken"] / f["datei"]
                ziel.parent.mkdir(exist_ok=True)
                kopie = ziel.with_name(f"{name}_h.jpg")
                try:
                    if quelle.suffix == ".heic":       # Pillow liest kein HEIC
                        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "100", str(quelle),
                                        "--out", str(kopie)], check=True, capture_output=True, timeout=120)
                        quelle = kopie
                    subprocess.run([str(self.umgebung()), str(HIER / "bilder.py"), "schneiden", str(quelle), str(ziel),
                                    str(kl), json.dumps(f["plan"]["zuschnitt"])], check=True, capture_output=True,
                                   timeout=120)
                except (OSError, subprocess.SubprocessError) as e:
                    text = (getattr(e, "stderr", b"") or b"").decode("utf-8", "replace").strip().splitlines()
                    print(f"Zuschnitt {name}: {text or e}", file=sys.stderr)
                    raise ValueError(f"Zuschnitt ging nicht: {text[-1] if text else e}") from e
                finally:
                    kopie.unlink(missing_ok=True)
        return kl if klein else ziel

    # ------------------------------------------------------ Körper
    def koerper(self, kennung) -> dict:
        """3D-Körper eines Balkens (koerper.py in der Trainings-.venv). Neu gerechnet, wenn Maße oder Fotos neuer sind
        als der letzte Körper. Antwort: koerper.json und "stand" (ändert sich mit jeder neuen Rechnung)."""
        if kennung not in self.ids():
            raise ValueError("Diesen Balken gibt es nicht.")
        namen = [f["name"] for f in fotos(self.lesen(kennung))]
        if not namen:
            raise ValueError("Noch keine Fotos.")
        for n in namen:
            self.zuschnitt(n)
        ordner = self.ordner / kennung
        ziel = ordner / "koerper" / "koerper.json"
        quellen = [ordner / "balken.json"] + [ordner / "zuschnitt" / f"{n}.jpg" for n in namen]
        with self.koerper_schloss:
            if not ziel.exists() or ziel.stat().st_mtime_ns < max(q.stat().st_mtime_ns for q in quellen):
                try:
                    subprocess.run([str(self.umgebung()), str(HIER / "koerper.py"), str(ordner)], check=True,
                                   capture_output=True, timeout=600)
                except (OSError, subprocess.SubprocessError) as e:
                    text = (getattr(e, "stderr", b"") or b"").decode("utf-8", "replace").strip().splitlines()
                    print(f"Körper {kennung}: {text or e}", file=sys.stderr)
                    raise ValueError(f"Körper ging nicht: {text[-1] if text else e}") from e
            daten = json.loads(ziel.read_text(encoding="utf-8"))
            daten["stand"] = ziel.stat().st_mtime_ns
        return daten

    # ------------------------------------------------------ Training
    def teile(self) -> dict:
        p = self.ordner / "teile.json"
        alt = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        neu = vorschlag(alt, self.ids())
        if neu != alt:
            schreiben(p, neu)
        return neu

    def teil_setzen(self, daten: dict) -> dict:
        with self.schloss:
            teile, i, t = self.teile(), daten.get("balken"), daten.get("teil")
            if i not in teile or t not in TEILE:
                raise ValueError("Unbekannter Balken oder Teil.")
            if teile[i]["fest"]:
                raise ValueError("Mit diesem Balken wurde schon trainiert, sein Teil bleibt.")
            teile[i]["teil"] = t
            schreiben(self.ordner / "teile.json", teile)
            return self.stand()

    def fertig(self, f: dict) -> bool:
        x = self.label(f)
        return x is not None and all(o["ok"] for o in x["objekte"])

    def startmodell(self) -> str:
        eigen = self.wurzel / "runs" / "segment" / "kodytek-seg1-n1280" / "weights" / "best.pt"
        return str(eigen) if eigen.exists() else "yolo11n-seg.pt"

    def stand(self) -> dict:
        with self.schloss:
            teile, balken, fertige = self.teile(), [], []
            for i in self.ids():
                fs = fotos(self.lesen(i))
                ok = [f for f in fs if self.fertig(f)]
                fertige += [{**f, "objekte": len(self.label(f)["objekte"])} for f in ok]
                balken.append({"id": i, "fotos": len(fs), "fertig": len(ok), **teile[i],
                               "objekte": sum(len(self.label(f)["objekte"]) for f in ok)})
            teil, art = pruefung(teile, fertige)
            lauf = None
            if self.lauf:
                z = epochen_gelesen(Path(self.lauf["ordner"]) / "results.csv")
                lauf = {**self.lauf, "epoche": len(z), "werte": [
                    {k: float(x[s]) for k, s in (("map", "metrics/mAP50(M)"), ("verlust", "train/seg_loss")) if s in x}
                    for x in z]}
            altholz = {"art": art, "fertig": sum(teile[f["balken"]]["teil"] != "test" for f in fertige),
                       **{t: sum(x == t for x in teil.values()) for t in ("train", "val")}}
            return {"balken": balken, "saetze": self.saetze(), "altholz": altholz, "lauf": lauf, "epochen": EPOCHEN,
                    "ergebnis": self.ergebnis(),
                    "modell": "Kodytek" if "kodytek" in self.startmodell() else "yolo11n-seg"}

    def ergebnis(self) -> dict | None:
        """Ergebnis des fertigen Laufs, nach einem Neustart des Programms das des letzten Laufs auf der Platte."""
        if self.lauf:
            name = self.lauf["name"] if self.lauf["status"] == "fertig" else None
        else:
            nummern = [int(p.name[8:]) for p in (self.wurzel / "runs" / "segment").glob("altholz-*")
                       if re.fullmatch(r"altholz-\d+", p.name)]
            name = f"altholz-{max(nummern)}" if nummern else None
        if not name:
            return None
        log, lauf = self.ordner / f"{name}.log", self.wurzel / "runs" / "segment" / name
        stempel = (name, log.stat().st_mtime_ns if log.exists() else 0)
        if self._ergebnis[0] != stempel:
            e = ergebnis_gelesen(lauf, log, self.wurzel / "datensaetze" / name / "bericht.json",
                                 self.ordner / f"{name}-altholz.log")
            plan = self.ordner / f"{name}.json"
            if e:
                e["name"] = name
                e["saetze"] = json.loads(plan.read_text(encoding="utf-8")).get("saetze", []) if plan.exists() else []
                e["gewichte"] = str(lauf / "weights" / "best.pt")
            self._ergebnis = (stempel, e)
        return self._ergebnis[1]

    def starten(self, daten: dict) -> dict:
        with self.schloss:
            if self.lauf and self.lauf["status"] in LAUFEND:
                raise ValueError("Es läuft schon ein Training.")
            wahl = daten.get("saetze", ["altholz"])
            bekannt = {"altholz", *(x["id"] for x in self.saetze())}
            if not isinstance(wahl, list) or not wahl or not all(isinstance(x, str) and x in bekannt for x in wahl):
                raise ValueError("Keinen oder einen unbekannten Datensatz gewählt.")
            teile = self.teile()
            fertige = [f for f in self.alle() if self.fertig(f)] if "altholz" in wahl else []
            fertige = [{**f, "objekte": len(self.label(f)["objekte"])} for f in fertige
                       if teile[f["balken"]]["teil"] != "test"]
            if "altholz" in wahl and not fertige:
                raise ValueError("Noch kein Foto fertig gelabelt." if len(wahl) == 1 else
                                 "Altholz hat noch kein fertig gelabeltes Foto für Training oder Prüfung.")
            if wahl == ["altholz"] and not any(f["objekte"] for f in fertige):
                raise ValueError("Auf den fertigen Fotos ist kein Objekt gezeichnet.")
            teil, art = pruefung(teile, fertige)
            if "altholz" in wahl and art is None:
                raise ValueError("Für die Prüfung fehlt ein zweites fertig gelabeltes Foto.")
            kod = self.kodytek() if "kodytek" in wahl else []
            fremd = [o for o in self.fremde() if o.name in wahl]
            vorhanden = (set(teil.values()) | {f["teil"] for f in kod}
                         | {t for o in fremd for t in ("train", "val") if self.zahl(o, t)})
            if not {"train", "val"} <= vorhanden:
                raise ValueError("Die gewählten Datensätze haben keine Bilder für Training und Prüfung.")
            if any(not Path(f["datei"]).exists() for f in kod):
                raise ValueError("Bilder der Kodytek-Auswahl fehlen.")
            self.umgebung()
            if not self.yolo.exists():
                raise ValueError(f"yolo fehlt: {self.yolo}")
            namen = [p.name for o in ("datensaetze", "runs/segment") for p in (self.wurzel / o).glob("altholz-*")]
            nummern = [int(n[8:]) for n in namen if re.fullmatch(r"altholz-\d+", n)]
            name = f"altholz-{max([0, *nummern]) + 1}"
            auftrag = {"ziel": str(self.wurzel / "datensaetze" / name), "pruefung": art, "klassen": KLASSEN, "bilder": [
                {"name": f["name"], "balken": f["balken"], "teil": teil[(f["balken"], f["name"])],
                 "bild": str(self.ordner / f["balken"] / "zuschnitt" / f"{f['name']}.jpg"),
                 "objekte": self.label(f)["objekte"]} for f in fertige]}
            auftrag["ganze"] = [
                {"name": f["name"], "teil": f["teil"], "bild": f["datei"], "label": sa.zeilen_aus(self.label(f)["objekte"])
                 if self.fertig(f) else self.original(f)} for f in kod]
            # Bilder der Auswahl stehen schon mit (korrigiertem) Label im Lauf, also nicht doppelt aus dem Gesamtsatz
            doppelt = {f["name"][8:] for f in kod}
            auftrag["dazu"] = {t: [str(b) for o in fremd for b in sa.bilder_in(o, t) if b.stem not in doppelt]
                               for t in ("train", "val")}
            auftrag["saetze"] = wahl
            self.lauf = {"name": name, "status": "bauen", "pruefung": art, "fehler": "", "epochen": EPOCHEN,
                         "ordner": str(self.wurzel / "runs" / "segment" / name)}
            if art == "balken":                 # Aufteilung nach Balken bleibt ab jetzt, damit Läufe vergleichbar sind
                for i in {f["balken"] for f in fertige}:
                    teile[i]["fest"] = True
                schreiben(self.ordner / "teile.json", teile)
            threading.Thread(target=self._laufen, args=(auftrag, self.lauf), daemon=True).start()
            return self.stand()

    def _laufen(self, auftrag: dict, lauf: dict) -> None:
        logdatei = self.ordner / f"{lauf['name']}.log"
        try:
            for b in auftrag["bilder"]:
                self.zuschnitt(b["name"])
            plan = self.ordner / f"{lauf['name']}.json"
            schreiben(plan, auftrag)
            with logdatei.open("w", encoding="utf-8") as log:
                subprocess.run([str(self.python), str(HIER / "bilder.py"), "bauen", str(plan)], check=True, stdout=log,
                               stderr=subprocess.STDOUT, cwd=self.wurzel, timeout=1800)
                befehl = [str(self.yolo), "segment", "train", f"data={auftrag['ziel']}/data.yaml",
                          f"model={self.startmodell()}", f"epochs={EPOCHEN}", "imgsz=1280", "batch=2", "workers=2",
                          "device=mps", f"project={self.wurzel / 'runs' / 'segment'}", f"name={lauf['name']}"]
                ende = self._prozess(lauf, "training", befehl, log)
            with self.schloss:
                if lauf["status"] == "training" and ende:
                    lauf["status"], lauf["fehler"] = "fehler", self._letzte_zeile(logdatei)
            mischung = Path(auftrag["ziel"]) / "altholz.yaml"
            if ende == 0 and mischung.exists():
                # Die Prüfzahl von ultralytics mischt Altholz mit Kodytek: best.pt noch einmal nur auf Altholz prüfen
                pruef_log = self.ordner / f"{lauf['name']}-altholz.log"
                lauf_ordner = Path(lauf["ordner"])
                befehl = [str(self.yolo), "segment", "val", f"data={mischung}",
                          f"model={lauf_ordner / 'weights' / 'best.pt'}", "imgsz=1280", "batch=2", "workers=2",
                          "device=mps", f"project={lauf_ordner}", "name=pruefung-altholz", "exist_ok=True"]
                with pruef_log.open("w", encoding="utf-8") as log:
                    ende_pruef = self._prozess(lauf, "pruefen", befehl, log)
                if ende_pruef:
                    print(f"Lauf {lauf['name']}: Altholz-Prüfung Code {ende_pruef}", file=sys.stderr)
                    with self.schloss:
                        lauf["fehler"] = f"Altholz-Prüfung ging nicht: {self._letzte_zeile(pruef_log)}"
            with self.schloss:
                if lauf["status"] in ("training", "pruefen"):
                    lauf["status"] = "fertig"
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            print(f"Lauf {lauf['name']}: {e}", file=sys.stderr)
            with self.schloss:
                lauf["status"], lauf["fehler"] = "fehler", self._letzte_zeile(logdatei) or str(e)

    def _prozess(self, lauf: dict, status: str, befehl: list[str], log) -> int | None:
        """yolo als eigener Prozess (abbrechbar, Mac bleibt wach). None, wenn vorher abgebrochen."""
        if shutil.which("caffeinate"):
            befehl = ["caffeinate", "-i", *befehl]
        with self.schloss:
            if lauf["status"] == "abgebrochen":
                return None
            lauf["status"] = status
            self.prozess = subprocess.Popen(befehl, stdout=log, stderr=subprocess.STDOUT, cwd=self.wurzel,
                                            start_new_session=True)
        return self.prozess.wait()

    @staticmethod
    def _letzte_zeile(pfad: Path) -> str:
        zeilen = pfad.read_text(encoding="utf-8", errors="replace").strip().splitlines() if pfad.exists() else []
        return zeilen[-1][-300:] if zeilen else ""

    def abbrechen(self, daten: dict) -> dict:
        with self.schloss:
            if not self.lauf or self.lauf["status"] not in LAUFEND:
                raise ValueError("Es läuft kein Training.")
            self.lauf["status"] = "abgebrochen"
            if self.prozess and self.prozess.poll() is None:
                os.killpg(self.prozess.pid, 15)
            return self.stand()
