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
    from . import klassen as kl
    from . import saetze as sa
    from . import vorlabeln as vl
else:
    import klassen as kl
    import saetze as sa
    import vorlabeln as vl

KLASSEN = ["live_knot", "dead_knot", "knot_missing", "knot_with_crack", "crack", "quartzity", "resin", "marrow",
           "blue_stain", "overgrown", "bohrloch", "metall", "nagelloch", "farbe", "faeule", "insektenfrass",
           "verbindung", "fuge"]            # Startfassung (docs/labelrichtlinie.md, 0-9 wie Kodytek), gilt: klassen.json
TEILE = ("train", "val", "test")
EPOCHEN = 60
LAUFEND = ("bauen", "training", "pruefen")
VLAUFEND = ("holen", "rechnen")
HIER = Path(__file__).resolve().parent


def schreiben(pfad: Path, daten) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    neu = pfad.with_suffix(".neu")
    neu.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    neu.replace(pfad)


def zahl_oder_nichts(wert, lo: float, hi: float):
    if wert is None:
        return None
    if isinstance(wert, bool) or not isinstance(wert, (int, float)) or not lo <= wert <= hi:
        raise ValueError("Zahl außerhalb des Bereichs.")
    return round(float(wert), 4)


def messungen_pruefen(werte, von: str | None) -> list[dict]:
    """Am Holz gemessene Durchmesser eines Objekts (Messschieber, mm), je Person eine Zeile. Ohne Namen gilt, wer
    speichert (auf dem Mac: mac)."""
    if werte is None:
        return []
    if not isinstance(werte, list) or len(werte) > 6:
        raise ValueError("Messung nicht lesbar.")
    ergebnis = []
    for m in werte:
        if not isinstance(m, dict):
            raise ValueError("Messung nicht lesbar.")
        z = {"min": zahl_oder_nichts(m.get("min"), 0.1, 5000), "max": zahl_oder_nichts(m.get("max"), 0.1, 5000)}
        if z["min"] is None and z["max"] is None:
            continue
        wer = m.get("von") or von or "mac"
        if not isinstance(wer, str) or not re.fullmatch(r"[a-z]{1,20}", wer):
            raise ValueError("Messung: Name nicht lesbar.")
        ergebnis.append({"von": wer, **z})
    return ergebnis


def objekte_pruefen(werte, ids=None, von: str | None = None) -> list[dict]:
    """Objekte aus dem Browser: Klasse und Umriss in Anteilen des Zuschnitts, dazu der Zustand des Editors.
    Dazu, wenn vorhanden: Konfidenz c und Quelle q (Vorlabel), alte Klasse kv (zusammengelegt), Messungen m."""
    ids = set(range(len(KLASSEN))) if ids is None else ids
    if not isinstance(werte, list) or len(werte) > 2000:
        raise ValueError("Labels nicht lesbar.")
    ergebnis = []
    for o in werte:
        if not isinstance(o, dict) or isinstance(o.get("k"), bool) or o.get("k") not in ids:
            raise ValueError("Unbekannte Klasse. Seite neu laden (Klassen wurden geändert).")
        p = o.get("p")
        if not isinstance(p, list) or not 3 <= len(p) <= 2000:
            raise ValueError("Umriss nicht lesbar.")
        for q in p:
            if not isinstance(q, list) or len(q) != 2 or any(
                    isinstance(w, bool) or not isinstance(w, (int, float)) or not 0 <= w <= 1 for w in q):
                raise ValueError("Umriss außerhalb des Bildes.")
        neu = {"k": o["k"], "ok": bool(o.get("ok")), "p": [[round(w, 6) for w in q] for q in p]}
        if (c := zahl_oder_nichts(o.get("c"), 0, 1)) is not None:
            neu["c"] = c
        if o.get("q") is not None:
            if not isinstance(o["q"], str) or len(o["q"]) > 60:
                raise ValueError("Quelle nicht lesbar.")
            neu["q"] = o["q"]
        if isinstance(o.get("kv"), int) and not isinstance(o["kv"], bool):
            neu["kv"] = o["kv"]
        if m := messungen_pruefen(o.get("m"), von):
            neu["m"] = m
        ergebnis.append(neu)
    return ergebnis


def fotos(balken: dict) -> list[dict]:
    """Alle gültigen Fotos eines Balkens, Seite für Seite."""
    ergebnis = []
    for seite, s in sorted(balken["seiten"].items()):
        for nr, f in sorted(s["fotos"].items(), key=lambda x: int(x[0])):
            ergebnis.append({"balken": balken["id"], "seite": seite, "nr": int(nr), "name": Path(f["datei"]).stem,
                             "datei": f["datei"], "plan": s["plan"], "px_je_mm": f.get("px_je_mm"),
                             "breite_px": f.get("breite_px")})
    return ergebnis


def koerper_veraltet(ordner: Path, namen: list[str]) -> bool:
    """Körper fehlt, ist älter als Maße oder ein Zuschnitt (auch ein noch fehlender), hat keine kleinen Bilder oder
    stammt von vor der Plausibilitätsprüfung."""
    ziel = ordner / "koerper" / "koerper.json"
    if not ziel.exists() or not any(ziel.parent.glob("S?_k.jpg")):
        return True
    stand = ziel.stat().st_mtime_ns
    if any("grund" not in s for s in json.loads(ziel.read_text(encoding="utf-8")).get("seiten", {}).values()):
        return True                                     # Körper von vor der Plausibilitätsprüfung
    for q in [ordner / "balken.json"] + [ordner / "zuschnitt" / f"{n}.jpg" for n in namen]:
        if not q.exists() or q.stat().st_mtime_ns > stand:
            return True
    return False


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


def mit_nummer(klassen: list[dict], namen: list[str] | None = None) -> list[dict]:
    namen = namen or KLASSEN
    return [{**t, "k": namen.index(t["klasse"]) if t["klasse"] in namen else None} for t in klassen]


def ergebnis_gelesen(lauf: Path, log: Path, bericht: Path, pruef_log: Path | None = None,
                     namen: list[str] | None = None) -> dict | None:
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
    klassen = mit_nummer(tabelle[1:], namen)
    altholz = tabelle_aus(pruef_log) if pruef_log else None
    return {"gesamt": tabelle[0], "klassen": klassen, "probe": probe, "pruefung": zahl.get("pruefung"),
            "altholz": {"gesamt": altholz[0], "klassen": mit_nummer(altholz[1:], namen)} if altholz else None,
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
        self.vlauf: dict | None = None          # Vorlabeln: ein Lauf auf einmal (Mac)
        self.vprozess: subprocess.Popen | None = None
        self._modelle: dict = {}

    # ------------------------------------------------------ Klassen (klassen.json)
    def klassen(self) -> dict:
        """Gültige Klassenliste. Fehlt die Datei, gilt die Startfassung; ist sie kaputt, bricht es laut ab."""
        p = self.ordner / "klassen.json"
        return kl.gelesen(json.loads(p.read_text(encoding="utf-8"))) if p.exists() else kl.standard()

    def namen(self) -> list[str]:
        return kl.schluessel_liste(self.klassen())

    def label_dateien(self) -> list[Path]:
        return sorted(self.ordner.glob("*/labels/*.json"))

    def klassen_zahl(self) -> dict[int, int]:
        zahl: dict[int, int] = {}
        for p in self.label_dateien():
            for o in json.loads(p.read_text(encoding="utf-8")).get("objekte", []):
                zahl[o["k"]] = zahl.get(o["k"], 0) + 1
        return zahl

    def klassen_stand(self, ich: str | None = None) -> dict:
        d = self.klassen()
        return {"klassen": d["klassen"], "gruppen": kl.gruppen(d), "zahl": self.klassen_zahl(),
                "zurueck": d.get("letzte"), "ich": ich or "mac"}

    def labels_umschreiben(self, wie) -> int:
        """wie(objekte) -> Zahl geänderter; schreibt nur Dateien, in denen sich etwas ändert."""
        n = 0
        for p in self.label_dateien():
            x = json.loads(p.read_text(encoding="utf-8"))
            if m := wie(x.get("objekte", [])):
                schreiben(p, x)
                n += m
        return n

    def klassen_aendern(self, daten: dict, von: str | None = None) -> dict:
        """Eine Änderung aus der Oberfläche: aendern, gruppe, neu, weg, zurueck."""
        art = daten.get("art")
        with self.schloss:
            d = self.klassen()
            if art == "aendern":
                kl.aendern(d, daten.get("id"), daten.get("name"), daten.get("gruppe"),
                           daten["farbe"] if "farbe" in daten else ...)
            elif art == "gruppe":
                kl.gruppe_umbenennen(d, daten.get("alt"), daten.get("neu"))
            elif art == "neu":
                kl.neu(d, daten.get("name"), daten.get("gruppe"))
            elif art == "weg":
                kid, ziel = daten.get("id"), daten.get("in")
                kl.weg(d, kid, ziel, self.klassen_zahl().get(kid, 0))
                if ziel is not None:
                    d["letzte"]["anzahl"] = self.labels_umschreiben(lambda o: kl.objekte_umhaengen(o, kid, ziel))
            elif art == "zurueck":
                z = kl.zurueck(d)
                if z["in"] is not None:
                    self.labels_umschreiben(lambda o: kl.objekte_zurueck(o, z["id"], z["in"]))
            else:
                raise ValueError("Unbekannte Änderung.")
            schreiben(self.ordner / "klassen.json", d)
            self._fremde = None
            return self.klassen_stand(von)

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
            self._fremde = sa.gefunden(self.wurzel, self.namen())
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
        gesamt, e = [], self.einmessungen("kodytek")
        for f in self.kodytek():
            x = self.label(f)
            gesamt.append({"name": f["name"], "balken": "kodytek", "titel": f["name"][8:], "laengs_mm": None,
                           "mm_je_px": (e.get(f["name"]) or {}).get("mm_je_px"),
                           "objekte": x["objekte"] if x else sa.objekte_aus(self.original(f)),
                           "zeit": x["zeit"] if x else None})
        return gesamt

    def bilder(self) -> list[dict]:
        gesamt = []
        for i in self.ids():
            b = self.lesen(i)
            e = None
            for f in fotos(b):
                if e is None:
                    e = self.einmessungen(f["balken"])
                gesamt.append(self.bild(f, b.get("name") or "", e))
        return gesamt

    # ------------------------------------------------------ Einmessen (digitaler Zollstock in Labeln)
    def einmessungen(self, balken: str) -> dict:
        """Eingemessene Maßstäbe eines Balkens: Foto -> {mm_je_px, von, zeit}. mm_je_px bezieht sich auf die Pixel
        des Zuschnitts. Gilt vor dem Maßstab aus Plan oder Streifenbild."""
        p = self.ordner / balken / "einmessung.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    def foto_massstab(self, daten: dict, von: str | None = None) -> dict:
        """Maßstab eines Fotos speichern (mm_je_px) oder mit None entfernen. Antwort: der vorige Wert."""
        mm = daten.get("mm_je_px")
        if mm is not None and (isinstance(mm, bool) or not isinstance(mm, (int, float)) or not 1e-4 <= mm <= 100):
            raise ValueError("Maßstab außerhalb des Bereichs.")
        with self.schloss:
            f = self.foto(daten.get("name"))
            p = self.ordner / f["balken"] / "einmessung.json"
            alle = self.einmessungen(f["balken"])
            vorher = (alle.get(f["name"]) or {}).get("mm_je_px")
            if mm is None:
                alle.pop(f["name"], None)
            else:
                alle[f["name"]] = {"mm_je_px": round(float(mm), 7), "von": von or "mac",
                                   "zeit": datetime.now().isoformat(timespec="seconds")}
            schreiben(p, alle)
        return {"mm_je_px": mm, "vorher": vorher}

    def bild(self, f: dict, balken_name: str, einmessung: dict | None = None) -> dict:
        """Ein Foto für die Seite Labeln. frei = hochgeladen (im Servermodus verwerfbar), name_b = Name des Balkens."""
        x = self.label(f)
        # Maße in mm gelten nur mit gemessenem Bildwinkel, sonst zeigt die Oberfläche Pixel
        p = f["plan"]
        gemessen = abs(p["faktor"] - 24 / 34.6) > 1e-9
        mm = p["laengs_mm"] if gemessen else None
        if p.get("frei") and f.get("px_je_mm") and f.get("breite_px"):
            mm = round(f["breite_px"] / f["px_je_mm"], 2)   # hochgeladen mit bekanntem Maßstab (Streifenbild)
        return {"name": f["name"], "balken": f["balken"], "seite": f["seite"], "nr": f["nr"],
                "titel": f"{f['balken']} Seite {f['seite']}, {f['nr'] + 1}", "laengs_mm": mm,
                "name_b": balken_name, "frei": bool(p.get("frei")),
                "mm_je_px": ((einmessung or {}).get(f["name"]) or {}).get("mm_je_px"),
                "objekte": x["objekte"] if x else None, "zeit": x["zeit"] if x else None}

    def speichern(self, daten: dict, von: str | None = None) -> dict:
        """Schickt der Browser "stand" (Zeit des Labels, das er geladen hat, oder None), wird nur gespeichert, wenn
        inzwischen niemand anderes gespeichert hat. Zwei Personen am selben Foto überschreiben sich so nicht still."""
        objekte = objekte_pruefen(daten.get("objekte"), kl.aktive_ids(self.klassen()), von)
        with self.schloss:
            f = self.foto(daten.get("name"))
            if "stand" in daten:
                alt = self.label(f)
                if (alt or {}).get("zeit") != daten["stand"]:
                    wer = f" von {alt['von']}" if alt and alt.get("von") else ""
                    raise ValueError(f"Inzwischen{wer} gespeichert ({(alt or {}).get('zeit', '')[11:16]}). "
                                     "Seite neu laden, dann weiter.")
            zeit = datetime.now().isoformat(timespec="seconds")
            neu = {"foto": f["datei"], "zuschnitt": f["plan"].get("zuschnitt"), "zeit": zeit, "objekte": objekte}
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
                                    str(kl), json.dumps(f["plan"].get("zuschnitt"))], check=True, capture_output=True,
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
        with self.koerper_schloss:
            if koerper_veraltet(ordner, namen):
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

    def galerie(self) -> list[dict]:
        """Alle Balken für die Galerie, neueste zuerst: Maße, Teil, Fotos je Seite, Vorschaufoto, Labelstand und,
        wenn schon gerechnet, die größte Maßabweichung des Körpers (ohne ihn dafür zu rechnen)."""
        with self.schloss:
            teile, ergebnis = self.teile(), []
            for i in reversed(self.ids()):
                b = self.lesen(i)
                fs = fotos(b)
                je_seite = {n: sum(f["seite"] == n for f in fs) for n in ("1", "2", "3", "4")}
                abw, stand, alt, gruende = None, None, False, {}
                k = self.ordner / i / "koerper" / "koerper.json"
                if k.exists():
                    stand = k.stat().st_mtime_ns
                    alt = koerper_veraltet(self.ordner / i, [f["name"] for f in fs])
                    seiten = json.loads(k.read_text(encoding="utf-8"))["seiten"]
                    gruende = {n: s["grund"] for n, s in seiten.items() if s.get("grund")}
                    werte = [abs(x) for n, s in seiten.items() if n not in gruende
                             for x in s["abweichung_prozent"].values() if x is not None]
                    abw = max(werte, default=None)
                ergebnis.append({"id": i, "laenge_mm": b["laenge_mm"], "breite_mm": b["breite_mm"],
                                 "hoehe_mm": b["hoehe_mm"], "holzart": b.get("holzart", ""), "name": b.get("name", ""), **teile[i],
                                 "seiten": je_seite, "bild": fs[0]["name"] if fs else None, "fotos": len(fs),
                                 "fertig": sum(self.fertig(f) for f in fs), "abweichung": abw, "koerper": stand,
                                 "weg": sorted(gruende), "gruende": gruende,
                                 "koerper_alt": alt})
            return ergebnis

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
                                 self.ordner / f"{name}-altholz.log", self.namen())
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
            if self.vlauf and self.vlauf["status"] in VLAUFEND:
                raise ValueError("Es läuft gerade ein Vorlabeln.")
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
            auftrag = {"ziel": str(self.wurzel / "datensaetze" / name), "pruefung": art, "klassen": self.namen(), "bilder": [
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

    # ------------------------------------------------------ Vorlabeln (docs/plan-vorlabeln.md)
    def modelle(self) -> list[dict]:
        """Läufe in runs/segment mit weights/best.pt: Name, Zeit, Altholz-Prüfzahl (Masken-mAP50-95 auf Altholz) oder
        None. Gelesen nur, wenn sich best.pt oder das Log ändert."""
        ergebnis = []
        for pt in sorted((self.wurzel / "runs" / "segment").glob("*/weights/best.pt")):
            name, lauf = pt.parents[1].name, pt.parents[1]
            if not vl.NAME.fullmatch(name):
                continue
            log = self.ordner / f"{name}.log"
            stempel = (pt.stat().st_mtime_ns, log.stat().st_mtime_ns if log.exists() else 0)
            if self._modelle.get(name, (None,))[0] != stempel:
                zahl = None
                if re.fullmatch(r"altholz-\d+", name):
                    e = ergebnis_gelesen(lauf, log, self.wurzel / "datensaetze" / name / "bericht.json",
                                         self.ordner / f"{name}-altholz.log", self.namen())
                    plan = self.ordner / f"{name}.json"
                    saetze = json.loads(plan.read_text(encoding="utf-8")).get("saetze", []) if plan.exists() else []
                    if e and not e["probe"]:
                        if e["altholz"]:
                            zahl = e["altholz"]["gesamt"]["maske"]["map"]
                        elif saetze == ["altholz"]:
                            zahl = e["gesamt"]["maske"]["map"]
                self._modelle[name] = (stempel, {"name": name, "zahl": zahl, "zeit": stempel[0]})
            ergebnis.append(self._modelle[name][1])
        return ergebnis

    def modell_namen(self, name: str) -> dict[int, str]:
        """Klassennamen eines Modells: bei altholz-N aus dem Lauf (aufnahmen/altholz-N.json), sonst aus der data.yaml,
        die in args.yaml steht."""
        plan = self.ordner / f"{name}.json"
        if re.fullmatch(r"altholz-\d+", name) and plan.exists():
            return dict(enumerate(json.loads(plan.read_text(encoding="utf-8"))["klassen"]))
        daten = args_gelesen(self.wurzel / "runs" / "segment" / name / "args.yaml").get("data")
        if daten:
            pfad = Path(daten) if Path(daten).is_absolute() else self.wurzel / daten
            if pfad.exists():
                return vl.namen_aus_yaml(pfad.read_text(encoding="utf-8"))
        raise ValueError(f"Klassen des Modells {name} nicht gefunden (data.yaml).")

    def vorlabeln_stand(self, fern: bool = False) -> dict:
        """Für die Seite: Modelle, gewähltes Modell, Teile, laufender oder letzter Lauf. fern (Server fragt): mit den
        Ergebnissen fertiger Balken, bis der Server sie abholt."""
        with self.schloss:
            modelle = self.modelle()
            lauf = None
            if self.vlauf:
                lauf = {k: v for k, v in self.vlauf.items() if k != "balken"}
                lauf["balken"] = {}
                for b, e in self.vlauf["balken"].items():
                    x = {k: v for k, v in e.items() if k not in ("ergebnis", "log", "fotos") or (k == "ergebnis" and fern)}
                    if e["status"] == "rechnen" and e.get("log"):
                        log = Path(e["log"])
                        if (f := vl.fortschritt(log.read_text(encoding="utf-8", errors="replace") if log.exists() else "")):
                            x["n"], x["m"] = f
                    lauf["balken"][b] = x
            return {"mac": True, "modell": vl.modell_wahl(modelle), "modelle": [m["name"] for m in modelle],
                    "teile": {i: t["teil"] for i, t in self.teile().items()}, "lauf": lauf,
                    "training": bool(self.lauf and self.lauf["status"] in LAUFEND)}

    def vorlabeln_starten(self, daten: dict, fern: bool = False, abgleich=None) -> dict:
        """Lauf anlegen und im Hintergrund rechnen. daten: balken (Liste IDs), fotos (Namen, leer = alle), modell
        (leer = Wahl), pruefung (auch Prüf- und Testbalken, nur bewusst über ···)."""
        balken, namen = daten.get("balken"), daten.get("fotos") or []
        if not isinstance(balken, list) or not 1 <= len(balken) <= 200 or not all(
                isinstance(b, str) and re.fullmatch(r"B\d{3,6}", b) for b in balken):
            raise ValueError("Welche Balken?")
        if not isinstance(namen, list) or len(namen) > 2000 or not all(isinstance(n, str) for n in namen):
            raise ValueError("Welche Fotos?")
        with self.schloss:
            if self.lauf and self.lauf["status"] in LAUFEND:
                raise ValueError("Es läuft gerade ein Training.")
            if self.vlauf and (self.vlauf["status"] in VLAUFEND or any(
                    "ergebnis" in e for e in self.vlauf["balken"].values())):
                raise ValueError("Es läuft schon ein Vorlabeln.")
            modelle = [m["name"] for m in self.modelle()]
            modell = daten.get("modell") or vl.modell_wahl(self.modelle())
            if not modell or modell not in modelle:
                raise ValueError("Kein Modell auf dem Mac (runs/segment/*/weights/best.pt).")
            self.umgebung()
            if not self.yolo.exists():
                raise ValueError(f"yolo fehlt: {self.yolo}")
            lauf = {"id": datetime.now().strftime("%Y%m%d-%H%M%S-%f"), "modell": modell, "status": "holen",
                    "fehler": "", "fern": fern, "pruefung": bool(daten.get("pruefung")),
                    "balken": {b: {"status": "wartet", "fotos": [n for n in namen if n.startswith(b + "_")]}
                               for b in dict.fromkeys(balken)}}
            self.vlauf = lauf
            threading.Thread(target=self._vorlabeln, args=(lauf, abgleich), daemon=True).start()
            return self.vorlabeln_stand(fern)

    def _vorlabeln(self, lauf: dict, abgleich) -> None:
        arbeit = self.wurzel / "vorlabeln" / lauf["id"]
        try:
            if abgleich:
                abgleich()                    # Fotos und balken.json vom Server (rsync), wie vor dem Training
            with self.schloss:
                if lauf["status"] == "abgebrochen":
                    return
                lauf["status"] = "rechnen"
                teile, ids = self.teile(), set(self.ids())
            zuordnung = vl.zuordnung(self.modell_namen(lauf["modell"]), self.klassen())
            if not zuordnung:
                raise ValueError(f"Keine Klasse von {lauf['modell']} passt zu klassen.json.")
            pt = self.wurzel / "runs" / "segment" / lauf["modell"] / "weights" / "best.pt"
            for b, e in lauf["balken"].items():
                if lauf["status"] == "abgebrochen":
                    break
                if b not in ids:
                    e["status"], e["fehler"] = "fehler", "Diesen Balken gibt es auf dem Mac nicht."
                    continue
                if teile[b]["teil"] != "train" and not lauf["pruefung"]:
                    e["status"] = "gesperrt"           # Prüflabels nicht vom Modell übernehmen
                    continue
                fs = [f for f in fotos(self.lesen(b)) if not e["fotos"] or f["name"] in e["fotos"]]
                if not fs:
                    e["status"] = "leer"
                    continue
                try:
                    e["status"] = "rechnen"
                    ergebnis = self._vorhersagen(b, fs, pt, lauf, e, arbeit / b, zuordnung)
                except (OSError, ValueError, subprocess.SubprocessError) as x:
                    print(f"Vorlabeln {b}: {x}", file=sys.stderr)
                    e["status"], e["fehler"] = "fehler", str(x)[-300:]
                    continue
                if lauf["fern"]:
                    e["ergebnis"] = ergebnis           # holt der Server ab (vorlabeln_ab)
                else:
                    e["neu"] = self.vorlabel_einfuegen(ergebnis, "vorlabel")["neu"]
                e["status"] = "fertig"
            with self.schloss:
                if lauf["status"] != "abgebrochen":
                    lauf["status"] = "fertig"
        except (OSError, ValueError, subprocess.SubprocessError) as x:
            print(f"Vorlabeln: {x}", file=sys.stderr)
            with self.schloss:
                lauf["status"], lauf["fehler"] = "fehler", str(x)[-300:]
        finally:
            shutil.rmtree(arbeit, ignore_errors=True)

    def _vorhersagen(self, balken: str, fs: list[dict], pt: Path, lauf: dict, e: dict, arbeit: Path,
                     zuordnung: dict) -> dict:
        """Zuschnitte kacheln (bilder.py), yolo segment predict als eigener Prozess, Kacheln zurück aufs Foto."""
        bilder = [self.zuschnitt(f["name"]) for f in fs]
        quelle = arbeit / "kacheln"
        r = subprocess.run([str(self.python), str(HIER / "bilder.py"), "kacheln", str(quelle), *map(str, bilder)],
                           capture_output=True, text=True, timeout=1800)
        if r.returncode:
            raise ValueError(f"Kacheln ging nicht: {(r.stderr.strip().splitlines() or ['ohne Meldung'])[-1]}")
        groessen = json.loads((quelle / "groessen.json").read_text(encoding="utf-8"))
        e["log"] = str(arbeit / "predict.log")
        befehl = [str(self.yolo), "segment", "predict", f"model={pt}", f"source={quelle}", "imgsz=1280",
                  "retina_masks=True", "save_txt=True", "save_conf=True", "save=False", "device=mps",
                  f"project={arbeit}", "name=vorhersage", "exist_ok=True"]
        if shutil.which("caffeinate"):
            befehl = ["caffeinate", "-i", *befehl]
        with open(e["log"], "w", encoding="utf-8") as log:
            with self.schloss:
                if lauf["status"] == "abgebrochen":
                    raise ValueError("Abgebrochen.")
                self.vprozess = subprocess.Popen(befehl, stdout=log, stderr=subprocess.STDOUT, cwd=self.wurzel,
                                                 start_new_session=True)
            ende = self.vprozess.wait()
        if ende:
            raise ValueError(f"yolo predict: {self._letzte_zeile(Path(e['log']))}")
        texte = {p.stem: p.read_text(encoding="utf-8") for p in (arbeit / "vorhersage" / "labels").glob("*.txt")}
        return {f["name"]: vl.foto_objekte(f["name"], *groessen[f["name"]], texte, zuordnung, lauf["modell"])
                for f in fs}

    def vorlabeln_ab(self, daten: dict) -> dict:
        """Server hat das Ergebnis eines Balkens abgeholt: hier vergessen."""
        with self.schloss:
            if self.vlauf and self.vlauf["id"] == daten.get("lauf"):
                e = self.vlauf["balken"].get(daten.get("balken"))
                if e:
                    e.pop("ergebnis", None)
                    if isinstance(daten.get("neu"), int):
                        e["neu"] = daten["neu"]
            return {"ok": True}

    def vorlabel_einfuegen(self, ergebnis: dict, von: str) -> dict:
        """Vorhersagen eines Balkens ({Foto: Objekte}) in die Labels, nach vorlabeln.einfuegen. Objekte werden wie
        jede Eingabe geprüft (sie kommen auf dem Server vom Mac)."""
        if not isinstance(ergebnis, dict):
            raise ValueError("Ergebnis nicht lesbar.")
        zahl = {"neu": 0, "verdeckt": 0, "ersetzt": 0, "fotos": 0}
        with self.schloss:
            ids = kl.aktive_ids(self.klassen())
            for name, neu in ergebnis.items():
                try:
                    f = self.foto(name)
                except ValueError:
                    continue                    # Foto inzwischen verworfen
                if not isinstance(neu, list):
                    raise ValueError("Ergebnis nicht lesbar.")
                neu = objekte_pruefen([{**o, "ok": False} for o in neu if isinstance(o, dict) and o.get("k") in ids],
                                      ids)
                alt = self.label(f)
                objekte, z = vl.einfuegen((alt or {}).get("objekte", []), neu)
                for k in z:
                    zahl[k] += z[k]
                zahl["fotos"] += 1
                schreiben(self.label_pfad(f), {"foto": f["datei"], "zuschnitt": f["plan"].get("zuschnitt"),
                                               "zeit": datetime.now().isoformat(timespec="seconds"),
                                               "objekte": objekte, "von": von})
        return zahl

    def vorlabeln_abbrechen(self, daten: dict) -> dict:
        with self.schloss:
            if not self.vlauf or self.vlauf["status"] not in VLAUFEND:
                raise ValueError("Es läuft kein Vorlabeln.")
            self.vlauf["status"] = "abgebrochen"
            if self.vprozess and self.vprozess.poll() is None:
                os.killpg(self.vprozess.pid, 15)
            return self.vorlabeln_stand()
