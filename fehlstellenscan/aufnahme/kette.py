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

KLASSEN = ["live_knot", "dead_knot", "knot_missing", "knot_with_crack", "crack", "quartzity", "resin", "marrow",
           "blue_stain", "overgrown", "bohrloch", "metall", "nagelloch", "farbe", "faeule", "insektenfrass",
           "verbindung", "fuge"]            # docs/labelrichtlinie.md, 0-9 wie Kodytek
TEILE = ("train", "val", "test")
EPOCHEN = 60
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


def zuordnung(teile: dict, ids: list[str]) -> tuple[dict, bool]:
    """(Balken -> train/val ohne test, probe). Ohne Balken in beiden Teilen ist es nur eine Ablaufprobe, in der das
    Modell auf denselben Bildern geprüft wird, auf denen es trainiert."""
    benutzt = {i: teile[i]["teil"] for i in ids if teile[i]["teil"] != "test"}
    return benutzt, not {"train", "val"} <= set(benutzt.values())


def epochen_gelesen(pfad: Path) -> list[dict]:
    if not pfad.exists():
        return []
    with pfad.open(encoding="utf-8") as f:
        return [{k.strip(): v.strip() for k, v in z.items() if k and v} for z in csv.DictReader(f)]


class Kette:
    def __init__(self, ordner: Path, lesen, ids):
        self.ordner, self.wurzel, self.lesen, self.ids = ordner, ordner.parent, lesen, ids
        self.schloss = threading.RLock()
        self.python = self.wurzel / ".venv" / "bin" / "python"
        self.yolo = self.wurzel / ".venv" / "bin" / "yolo"
        self.schneiden_schloss = threading.Lock()
        self.lauf: dict | None = None
        self.prozess: subprocess.Popen | None = None

    # ------------------------------------------------------ Bilder und Labels
    def alle(self) -> list[dict]:
        return [f for i in self.ids() for f in fotos(self.lesen(i))]

    def foto(self, name) -> dict:
        treffer = [f for f in self.alle() if f["name"] == name]
        if not treffer:
            raise ValueError("Dieses Foto gibt es nicht mehr.")
        return treffer[0]

    def label_pfad(self, f: dict) -> Path:
        return self.ordner / f["balken"] / "labels" / f"{f['name']}.json"

    def label(self, f: dict) -> dict | None:
        p = self.label_pfad(f)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def bilder(self) -> list[dict]:
        gesamt = []
        for f in self.alle():
            x = self.label(f)
            # Maße in mm gelten nur mit gemessenem Bildwinkel, sonst zeigt die Oberfläche Pixel
            p = f["plan"]
            gemessen = abs(p["faktor"] - 24 / 34.6) > 1e-9
            gesamt.append({"name": f["name"], "balken": f["balken"], "seite": f["seite"], "nr": f["nr"],
                           "laengs_mm": p["laengs_mm"] if gemessen else None,
                           "objekte": x["objekte"] if x else None, "zeit": x["zeit"] if x else None})
        return gesamt

    def speichern(self, daten: dict) -> dict:
        objekte = objekte_pruefen(daten.get("objekte"))
        with self.schloss:
            f = self.foto(daten.get("name"))
            zeit = datetime.now().isoformat(timespec="seconds")
            schreiben(self.label_pfad(f), {"foto": f["datei"], "zuschnitt": f["plan"]["zuschnitt"], "zeit": zeit,
                                           "objekte": objekte})
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
            teile, balken = self.teile(), []
            for i in self.ids():
                fs = fotos(self.lesen(i))
                ok = [f for f in fs if self.fertig(f)]
                balken.append({"id": i, "fotos": len(fs), "fertig": len(ok), **teile[i],
                               "objekte": sum(len(self.label(f)["objekte"]) for f in ok)})
            _, probe = zuordnung(teile, [b["id"] for b in balken if b["fertig"]])
            lauf = None
            if self.lauf:
                z = epochen_gelesen(Path(self.lauf["ordner"]) / "results.csv")
                lauf = {**self.lauf, "epoche": len(z), "werte": [
                    {k: float(x[s]) for k, s in (("map", "metrics/mAP50(M)"), ("verlust", "train/seg_loss")) if s in x}
                    for x in z]}
            return {"balken": balken, "probe": probe, "lauf": lauf, "epochen": EPOCHEN,
                    "modell": "Kodytek" if "kodytek" in self.startmodell() else "yolo11n-seg"}

    def starten(self, daten: dict) -> dict:
        with self.schloss:
            if self.lauf and self.lauf["status"] in ("bauen", "training"):
                raise ValueError("Es läuft schon ein Training.")
            teile = self.teile()
            fertige = [f for f in self.alle() if self.fertig(f)]
            benutzt, probe = zuordnung(teile, sorted({f["balken"] for f in fertige}))
            fertige = [f for f in fertige if f["balken"] in benutzt]
            if not fertige:
                raise ValueError("Noch kein Foto fertig gelabelt.")
            if not any(self.label(f)["objekte"] for f in fertige):
                raise ValueError("Auf den fertigen Fotos ist kein Objekt gezeichnet.")
            self.umgebung()
            if not self.yolo.exists():
                raise ValueError(f"yolo fehlt: {self.yolo}")
            namen = [p.name for o in ("datensaetze", "runs/segment") for p in (self.wurzel / o).glob("altholz-*")]
            nummern = [int(n[8:]) for n in namen if re.fullmatch(r"altholz-\d+", n)]
            name = f"altholz-{max([0, *nummern]) + 1}"
            auftrag = {"ziel": str(self.wurzel / "datensaetze" / name), "probe": probe, "klassen": KLASSEN, "bilder": [
                {"name": f["name"], "balken": f["balken"], "teil": "train" if probe else benutzt[f["balken"]],
                 "bild": str(self.ordner / f["balken"] / "zuschnitt" / f"{f['name']}.jpg"),
                 "objekte": self.label(f)["objekte"]} for f in fertige]}
            self.lauf = {"name": name, "status": "bauen", "probe": probe, "fehler": "", "epochen": EPOCHEN,
                         "ordner": str(self.wurzel / "runs" / "segment" / name)}
            if not probe:
                for i in benutzt:
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
                if shutil.which("caffeinate"):
                    befehl = ["caffeinate", "-i", *befehl]     # Mac bleibt wach
                with self.schloss:
                    if lauf["status"] == "abgebrochen":
                        return
                    lauf["status"] = "training"
                    self.prozess = subprocess.Popen(befehl, stdout=log, stderr=subprocess.STDOUT, cwd=self.wurzel,
                                                    start_new_session=True)
                ende = self.prozess.wait()
            with self.schloss:
                if lauf["status"] == "training":
                    lauf["status"] = "fertig" if ende == 0 else "fehler"
                    if ende:
                        lauf["fehler"] = self._letzte_zeile(logdatei)
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            print(f"Lauf {lauf['name']}: {e}", file=sys.stderr)
            with self.schloss:
                lauf["status"], lauf["fehler"] = "fehler", self._letzte_zeile(logdatei) or str(e)

    @staticmethod
    def _letzte_zeile(pfad: Path) -> str:
        zeilen = pfad.read_text(encoding="utf-8", errors="replace").strip().splitlines() if pfad.exists() else []
        return zeilen[-1][-300:] if zeilen else ""

    def abbrechen(self, daten: dict) -> dict:
        with self.schloss:
            if not self.lauf or self.lauf["status"] not in ("bauen", "training"):
                raise ValueError("Es läuft kein Training.")
            self.lauf["status"] = "abgebrochen"
            if self.prozess and self.prozess.poll() is None:
                os.killpg(self.prozess.pid, 15)
            return self.stand()
