"""Vorhersagen gegen Markierung und gegen Messungen am Holz prüfen (reine Logik, getestet, ohne PyTorch).

Läuft auf dem Server und auf dem Mac (numpy, Pillow, opencv über masken.py; kein ultralytics). Die Vorhersagen
kommen als Textdateien von `yolo segment predict save_txt=True save_conf=True`, Anleitung in STATUS.md.

Befehle (Einzelheiten mit --help):
  fehler   Markierung (YOLO-seg-Labels) gegen Vorhersage je Bild: Treffer, übersehen, Fehlalarm, Klasse
           vertauscht; Kennzahlen je Klasse, Trefferquote nach Größe in mm. Auch Person gegen Person: die eine
           Markierung als --markierung, die andere als --vorhersage (ohne Konfidenz zählt jedes Objekt).
  messung  Messschieber-Werte (messung.csv aus docs/messprotokoll-27-11.md) gegen die Funde auf dem Balken
           (funde.json von balken.py karte): Zuordnung nach Lage, Abweichung des kleinsten Durchmessers.

Zuordnung (wie üblich bei der Objekterkennung): Vorhersagen nach Konfidenz absteigend, jede nimmt das noch freie
markierte Objekt derselben Klasse mit der höchsten IoU der Masken, wenn diese mindestens die Schwelle erreicht
(Treffer). Danach dasselbe über Klassen hinweg für die Reste (Klasse vertauscht). Was dann übrig ist: markiert
ohne Vorhersage = übersehen, Vorhersage ohne markiertes Objekt = Fehlalarm. Die Zahlen sind P und R bei einer
festen Konfidenzschwelle, kein mAP (das rechnet ultralytics über alle Schwellen).

Größe in mm: kurze Achse der an den Umriss angepassten Ellipse (masken.masse_mm, Kodytek-Maßstab 16,66 Px/mm quer,
6,67 Px/mm längs). Bei Ästen ist das der kleinste Durchmesser, den die Norm misst, bei Rissen etwa die Breite.
"""

import argparse
import csv
import io
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import datensatz as d
import masken as m

GROESSEN_MM = (5.0, 10.0, 20.0, 40.0)        # Grenzen der Größenklassen (kurze Achse)
KODYTEK_PX = (2800, 1024)                     # Bildgröße, wenn keine Bilder angegeben sind
BILD_ENDUNGEN = (".bmp", ".jpg", ".jpeg", ".png")
ARTEN = ("treffer", "uebersehen", "vertauscht", "fehlalarm")
MESSUNG_SPALTEN = ["balken", "seite", "ast", "l_mm", "q_mm", "d_min_mm", "d_max_mm", "messer", "bemerkung"]
AST_NAMEN = {d.KLASSEN[k] for k in m.AESTE}


# ---------------------------------------------------------------- reine Logik: Masken und Zuordnung

def rahmen(punkte: np.ndarray) -> tuple[float, float, float, float]:
    """Umschließendes Rechteck (x0, y0, x1, y1) eines Umrisses in Pixeln."""
    x0, y0 = punkte.min(axis=0)
    x1, y1 = punkte.max(axis=0)
    return float(x0), float(y0), float(x1), float(y1)


def iou(a: np.ndarray, b: np.ndarray) -> float:
    """IoU zweier Umrisse (Polygone in Pixeln), gerastert im gemeinsamen Rechteck. 0, wenn sich die Rechtecke
    nicht schneiden."""
    ax0, ay0, ax1, ay1 = rahmen(a)
    bx0, by0, bx1, by1 = rahmen(b)
    if ax1 < bx0 or bx1 < ax0 or ay1 < by0 or by1 < ay0:
        return 0.0
    x0, y0 = int(np.floor(min(ax0, bx0))), int(np.floor(min(ay0, by0)))
    breite = int(np.ceil(max(ax1, bx1))) - x0 + 2
    hoehe = int(np.ceil(max(ay1, by1))) - y0 + 2

    def raster(punkte):
        bild = Image.new("1", (breite, hoehe), 0)
        ImageDraw.Draw(bild).polygon([(float(x) - x0, float(y) - y0) for x, y in punkte], fill=1, outline=1)
        return np.asarray(bild, dtype=bool)

    ma, mb = raster(a), raster(b)
    vereinigung = np.count_nonzero(ma | mb)
    return float(np.count_nonzero(ma & mb) / vereinigung) if vereinigung else 0.0


def groesse_mm(punkte: np.ndarray, px_je_mm: tuple[float, float] = m.PX_JE_MM) -> tuple[float, float]:
    """(kurz, lang) in mm: Achsen der angepassten Ellipse; bei weniger als 5 Punkten das Rechteck."""
    masse = m.masse_mm(punkte, px_je_mm)
    if masse is not None:
        return float(masse["kurz"]), float(masse["lang"])
    x0, y0, x1, y1 = rahmen(punkte)
    seiten = sorted(((x1 - x0) / px_je_mm[0], (y1 - y0) / px_je_mm[1]))
    return float(seiten[0]), float(seiten[1])


def groessenklasse(kurz_mm: float, grenzen: tuple[float, ...] = GROESSEN_MM) -> str:
    """Name der Größenklasse, z. B. "<5", "5-10", ">=40"."""
    if kurz_mm < grenzen[0]:
        return f"<{grenzen[0]:g}"
    for unten, oben in zip(grenzen, grenzen[1:], strict=False):
        if kurz_mm < oben:
            return f"{unten:g}-{oben:g}"
    return f">={grenzen[-1]:g}"


def groessenklassen(grenzen: tuple[float, ...] = GROESSEN_MM) -> list[str]:
    """Alle Klassennamen in aufsteigender Reihenfolge."""
    return [groessenklasse(g, grenzen) for g in (grenzen[0] - 1, *grenzen)]


def vergleichen(markiert: list, vorhergesagt: list, iou_schwelle: float = 0.5, konf_schwelle: float = 0.25,
                px_je_mm: tuple[float, float] = m.PX_JE_MM) -> list[dict]:
    """Ein Bild: markiert und vorhergesagt als [(klasse, Punkte in Pixeln, konfidenz oder None)] (wie
    masken.objekte_aus_label / objekte_aus_vorhersage). Ergebnis: ein Eintrag je Objekt mit art (treffer,
    uebersehen, vertauscht, fehlalarm), klasse (markiert, sonst vorhergesagt), klasse_vorhersage, konfidenz, iou,
    kurz_mm/lang_mm (des markierten Objekts, sonst der Vorhersage) und bei Treffern kurz_vorhersage_mm."""
    vor = [o for o in vorhergesagt if o[2] is None or o[2] >= konf_schwelle]
    vor.sort(key=lambda o: -(1.0 if o[2] is None else o[2]))
    ious = np.zeros((len(vor), len(markiert)))
    for i, (_, pv, _) in enumerate(vor):
        for j, (_, pm, _) in enumerate(markiert):
            ious[i, j] = iou(pv, pm)
    frei_m, frei_v, eintraege = set(range(len(markiert))), [], []

    def eintrag(art, j=None, i=None, wert=None):
        km = markiert[j][0] if j is not None else None
        kv = vor[i][0] if i is not None else None
        kurz, lang = groesse_mm(markiert[j][1] if j is not None else vor[i][1], px_je_mm)
        e = {"art": art, "klasse": d.KLASSEN[km if km is not None else kv],
             "klasse_vorhersage": d.KLASSEN[kv] if kv is not None else None,
             "konfidenz": vor[i][2] if i is not None else None,
             "iou": round(wert, 4) if wert is not None else None,
             "kurz_mm": round(kurz, 2), "lang_mm": round(lang, 2), "kurz_vorhersage_mm": None}
        if art == "treffer":
            e["kurz_vorhersage_mm"] = round(groesse_mm(vor[i][1], px_je_mm)[0], 2)
        return e

    for i, (kv, _, _) in enumerate(vor):
        kandidaten = [j for j in frei_m if markiert[j][0] == kv and ious[i, j] >= iou_schwelle]
        if kandidaten:
            j = max(kandidaten, key=lambda j: ious[i, j])
            frei_m.discard(j)
            eintraege.append(eintrag("treffer", j, i, ious[i, j]))
        else:
            frei_v.append(i)
    rest_v = []
    for i in frei_v:
        kandidaten = [j for j in frei_m if ious[i, j] >= iou_schwelle]
        if kandidaten:
            j = max(kandidaten, key=lambda j: ious[i, j])
            frei_m.discard(j)
            eintraege.append(eintrag("vertauscht", j, i, ious[i, j]))
        else:
            rest_v.append(i)
    eintraege += [eintrag("uebersehen", j=j) for j in sorted(frei_m)]
    eintraege += [eintrag("fehlalarm", i=i) for i in rest_v]
    return eintraege


def bootstrap_quote(paare: list[tuple[int, int]], anzahl: int = 1000, seed: int = 20261123) -> list | None:
    """95-%-Intervall einer Quote (Summe Zähler / Summe Nenner), Bilder mit Zurücklegen gezogen. paare: je Bild
    (zähler, nenner). None, wenn der Nenner insgesamt 0 ist."""
    werte = np.array(paare, dtype=np.float64).reshape(-1, 2)
    if not len(werte) or werte[:, 1].sum() == 0:
        return None
    rng = np.random.default_rng(seed)
    ziehung = rng.integers(0, len(werte), size=(anzahl, len(werte)))
    zaehler, nenner = werte[ziehung, 0].sum(axis=1), werte[ziehung, 1].sum(axis=1)
    quoten = zaehler[nenner > 0] / nenner[nenner > 0]
    return [round(float(np.percentile(quoten, 2.5)), 4), round(float(np.percentile(quoten, 97.5)), 4)]


def bland_altman(a: list[float], b: list[float]) -> dict:
    """Abweichung a - b: n, mittlere Abweichung, Streuung (Standardabweichung), 95-%-Grenzen (mittel ± 1,96 sd)
    und mittlerer Betrag. sd und Grenzen None bei n < 2."""
    diff = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    n = len(diff)
    if n == 0:
        return {"n": 0, "mittel": None, "sd": None, "grenzen": None, "betrag": None}
    mittel = float(diff.mean())
    sd = float(diff.std(ddof=1)) if n > 1 else None
    return {"n": n, "mittel": round(mittel, 3), "sd": round(sd, 3) if sd is not None else None,
            "grenzen": [round(mittel - 1.96 * sd, 3), round(mittel + 1.96 * sd, 3)] if sd is not None else None,
            "betrag": round(float(np.abs(diff).mean()), 3)}


def zusammenfassen(bilder: dict[str, list[dict]], grenzen: tuple[float, ...] = GROESSEN_MM) -> dict:
    """Ergebnisse je Bild (Name -> Einträge aus vergleichen) zu Kennzahlen: je Klasse (markiert, treffer,
    uebersehen, vertauscht, fehlalarm, vorhergesagt, trefferquote mit 95-%-Intervall, praezision), Trefferquote je
    Klasse und Größe, Verwechslungen (markiert -> vorhergesagt) und bei Ast-Treffern die mm-Abweichung der kurzen
    Achse Vorhersage gegen Markierung."""
    zaehl = defaultdict(Counter)
    je_bild = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # klasse -> bild -> [treffer, markiert]
    groesse = defaultdict(lambda: defaultdict(Counter))
    verwechslung = Counter()
    mm_vor, mm_mark = [], []
    for name, eintraege in bilder.items():
        for e in eintraege:
            k, kv, art = e["klasse"], e["klasse_vorhersage"], e["art"]
            if art in ("treffer", "uebersehen", "vertauscht"):
                zaehl[k]["markiert"] += 1
                je_bild[k][name][1] += 1
                g = groessenklasse(e["kurz_mm"], grenzen)
                groesse[k][g]["markiert"] += 1
                if art == "treffer":
                    groesse[k][g]["treffer"] += 1
            if art == "treffer":
                zaehl[k]["treffer"] += 1
                zaehl[k]["vorhergesagt"] += 1
                je_bild[k][name][0] += 1
                if k in AST_NAMEN:
                    mm_vor.append(e["kurz_vorhersage_mm"])
                    mm_mark.append(e["kurz_mm"])
            elif art == "uebersehen":
                zaehl[k]["uebersehen"] += 1
            elif art == "vertauscht":
                zaehl[k]["vertauscht"] += 1
                zaehl[kv]["vorhergesagt"] += 1
                verwechslung[f"{k} -> {kv}"] += 1
            elif art == "fehlalarm":
                zaehl[k]["fehlalarm"] += 1
                zaehl[k]["vorhergesagt"] += 1
    je_klasse = {}
    for k in d.KLASSEN:
        if k not in zaehl:
            continue
        z = zaehl[k]
        je_klasse[k] = {art: z[art] for art in ("markiert", *ARTEN, "vorhergesagt")}
        je_klasse[k]["trefferquote"] = round(z["treffer"] / z["markiert"], 4) if z["markiert"] else None
        je_klasse[k]["trefferquote_95"] = bootstrap_quote(list(je_bild[k].values()))
        je_klasse[k]["praezision"] = round(z["treffer"] / z["vorhergesagt"], 4) if z["vorhergesagt"] else None
    je_groesse = {k: {g: {"markiert": groesse[k][g]["markiert"], "treffer": groesse[k][g]["treffer"],
                          "quote": round(groesse[k][g]["treffer"] / groesse[k][g]["markiert"], 4)}
                      for g in groessenklassen(grenzen) if groesse[k][g]["markiert"]}
                  for k in d.KLASSEN if k in groesse}
    gesamt = Counter()
    for z in zaehl.values():
        gesamt.update(z)
    return {"bilder": len(bilder), "gesamt": {art: gesamt[art] for art in ("markiert", *ARTEN, "vorhergesagt")},
            "je_klasse": je_klasse, "je_groesse": je_groesse, "verwechslung": dict(verwechslung.most_common()),
            "aeste_mm_vorhersage_minus_markierung": bland_altman(mm_vor, mm_mark)}


# ---------------------------------------------------------------- reine Logik: Messungen am Holz

def zahl(text: str | None) -> float | None:
    """Zahl aus der Tabelle, Komma oder Punkt; leer -> None."""
    text = (text or "").strip()
    return float(text.replace(",", ".")) if text else None


def messungen_lesen(text: str) -> list[dict]:
    """messung.csv (Semikolon, Kopfzeile wie MESSUNG_SPALTEN) als Liste von Zeilen mit Zahlen. Fehlende Spalten
    brechen ab, leere Zeilen werden übersprungen."""
    leser = csv.DictReader(io.StringIO(text), delimiter=";")
    fehlend = [s for s in MESSUNG_SPALTEN if s not in (leser.fieldnames or [])]
    if fehlend:
        raise ValueError(f"messung.csv: Spalten fehlen: {', '.join(fehlend)}")
    zeilen = []
    for nr, z in enumerate(leser, start=2):
        if not any((v or "").strip() for v in z.values()):
            continue
        try:
            zeilen.append({"balken": z["balken"].strip(), "seite": z["seite"].strip(), "ast": z["ast"].strip(),
                           "l_mm": zahl(z["l_mm"]), "q_mm": zahl(z["q_mm"]), "d_min_mm": zahl(z["d_min_mm"]),
                           "d_max_mm": zahl(z["d_max_mm"]), "messer": (z["messer"] or "").strip(),
                           "bemerkung": (z["bemerkung"] or "").strip()})
        except ValueError as fehler:
            raise ValueError(f"messung.csv Zeile {nr}: {fehler}") from None
    return zeilen


def aeste(messungen: list[dict]) -> list[dict]:
    """Je Ast (balken, seite, ast) eine Zeile: Lage aus der ersten Zeile mit Lage, d_min und d_max gemittelt über
    alle Messenden, dazu die einzelnen Werte. Zeilen mit Bemerkung "mit Ring" zählen nicht (Zweitmaß)."""
    gruppen = defaultdict(list)
    for z in messungen:
        if "mit ring" not in z["bemerkung"].lower():
            gruppen[(z["balken"], z["seite"], z["ast"])].append(z)
    ergebnis = []
    for (balken, seite, ast), zeilen in gruppen.items():
        lage = next((z for z in zeilen if z["l_mm"] is not None and z["q_mm"] is not None), None)
        dmin = [z["d_min_mm"] for z in zeilen if z["d_min_mm"] is not None]
        dmax = [z["d_max_mm"] for z in zeilen if z["d_max_mm"] is not None]
        ergebnis.append({"balken": balken, "seite": seite, "ast": ast,
                         "l_mm": lage["l_mm"] if lage else None, "q_mm": lage["q_mm"] if lage else None,
                         "d_min_mm": float(np.mean(dmin)) if dmin else None,
                         "d_max_mm": float(np.mean(dmax)) if dmax else None,
                         "d_min_einzeln": dmin, "messer": [z["messer"] for z in zeilen]})
    return ergebnis


def wiederholbarkeit(messungen: list[dict]) -> dict:
    """Abweichung zwischen zwei Messenden am selben Ast (erste minus zweite Messung von d_min und d_max)."""
    paare_min, paare_max = ([], []), ([], [])
    for a in aeste(messungen):
        zeilen = [z for z in messungen if (z["balken"], z["seite"], z["ast"]) == (a["balken"], a["seite"], a["ast"])
                  and "mit ring" not in z["bemerkung"].lower()]
        if len({z["messer"] for z in zeilen}) < 2:
            continue
        erste, zweite = zeilen[0], next(z for z in zeilen if z["messer"] != zeilen[0]["messer"])
        for paare, feld in ((paare_min, "d_min_mm"), (paare_max, "d_max_mm")):
            if erste[feld] is not None and zweite[feld] is not None:
                paare[0].append(erste[feld])
                paare[1].append(zweite[feld])
    return {"d_min_mm": bland_altman(*paare_min), "d_max_mm": bland_altman(*paare_max)}


def fund_mitte(f: dict) -> tuple[float, float]:
    """Mitte eines Funds aus balken.py (l, q in mm), aus dem umschließenden Rechteck."""
    return (f["l_von"] + f["l_bis"]) / 2, (f["q_von"] + f["q_bis"]) / 2


def zuordnen(liste: list[dict], funde: list[dict], max_abstand_mm: float = 20.0,
             laenge_mm: float | None = None, hoehe_mm: float | None = None) -> tuple[list[dict], list[dict]]:
    """Gemessene Äste (aus aeste) den Ast-Funden des Modells zuordnen: kürzeste Abstände zuerst, jeder Fund und
    jeder Ast höchstens einmal, nur bis max_abstand_mm. laenge_mm / hoehe_mm spiegeln die Messlage (l -> laenge - l,
    q -> hoehe - q), wenn Ende A oder Kante K auf der anderen Seite des Streifenbilds liegt. Ergebnis: (paare,
    gemessene Äste ohne Fund)."""
    ast_funde = [f for f in funde if f["klasse"] in AST_NAMEN]
    kandidaten = []
    for i, a in enumerate(liste):
        if a["l_mm"] is None or a["q_mm"] is None:
            continue
        laengs = laenge_mm - a["l_mm"] if laenge_mm is not None else a["l_mm"]
        quer = hoehe_mm - a["q_mm"] if hoehe_mm is not None else a["q_mm"]
        for j, f in enumerate(ast_funde):
            fl, fq = fund_mitte(f)
            abstand = float(np.hypot(fl - laengs, fq - quer))
            if abstand <= max_abstand_mm:
                kandidaten.append((abstand, i, j))
    paare, frei_a, frei_f = [], set(range(len(liste))), set(range(len(ast_funde)))
    for abstand, i, j in sorted(kandidaten):
        if i in frei_a and j in frei_f:
            frei_a.discard(i)
            frei_f.discard(j)
            a, f = liste[i], ast_funde[j]
            paare.append({"balken": a["balken"], "seite": a["seite"], "ast": a["ast"],
                          "abstand_mm": round(abstand, 1), "klasse": f["klasse"], "konfidenz": f["konfidenz"],
                          "d_min_mm": a["d_min_mm"], "d_max_mm": a["d_max_mm"],
                          "modell_kurz_mm": f["ellipse_kurz"], "modell_lang_mm": f["ellipse_lang"]})
    paare.sort(key=lambda p: (p["balken"], p["seite"], p["ast"]))
    return paare, [liste[i] for i in sorted(frei_a)]


def messung_auswerten(messungen: list[dict], funde: list[dict], balken: str, seite: str,
                      max_abstand_mm: float = 20.0, laenge_mm: float | None = None,
                      hoehe_mm: float | None = None) -> dict:
    """Ein Balken, eine Seite: Zuordnung, Modell minus Messschieber (kurz gegen d_min, lang gegen d_max), Äste ohne
    Fund, Wiederholbarkeit der Messenden."""
    eigene = [z for z in messungen if z["balken"] == balken and z["seite"] == seite]
    if not eigene:
        raise ValueError(f"keine Messungen für Balken {balken} Seite {seite}")
    paare, ohne = zuordnen(aeste(eigene), funde, max_abstand_mm, laenge_mm, hoehe_mm)
    mit_min = [p for p in paare if p["modell_kurz_mm"] is not None and p["d_min_mm"] is not None]
    mit_max = [p for p in paare if p["modell_lang_mm"] is not None and p["d_max_mm"] is not None]
    return {"balken": balken, "seite": seite, "aeste": len(aeste(eigene)), "zugeordnet": len(paare),
            "ohne_fund": [a["ast"] for a in ohne],
            "modell_minus_messung_d_min": bland_altman([p["modell_kurz_mm"] for p in mit_min],
                                                       [p["d_min_mm"] for p in mit_min]),
            "modell_minus_messung_d_max": bland_altman([p["modell_lang_mm"] for p in mit_max],
                                                       [p["d_max_mm"] for p in mit_max]),
            "messende_untereinander": wiederholbarkeit(eigene), "paare": paare}


# ---------------------------------------------------------------- Dateien

def bildgroessen(bilder: Path | None, namen: list[str]) -> dict[str, tuple[int, int]]:
    """Breite und Höhe je Bildname aus dem Bildordner (nur Kopf gelesen); ohne Ordner die Kodytek-Größe."""
    if bilder is None:
        return {n: KODYTEK_PX for n in namen}
    vorhanden = {p.stem: p for p in bilder.iterdir() if p.suffix.lower() in BILD_ENDUNGEN}
    groessen = {}
    for n in namen:
        if n not in vorhanden:
            raise FileNotFoundError(f"kein Bild zu {n} in {bilder}")
        with Image.open(vorhanden[n]) as bild:
            groessen[n] = bild.size
    return groessen


def fehler_auswerten(markierung: Path, vorhersage: Path, bilder: Path | None = None, iou_schwelle: float = 0.5,
                     konf_schwelle: float = 0.25) -> tuple[dict, dict[str, list[dict]]]:
    """Alle Bilder mit Markierung (*.txt in markierung). Fehlt die Vorhersage zu einem Bild, hat das Modell dort
    nichts gefunden. Vorhersagen ohne Markierungsdatei werden nicht gezählt (Bild gehört nicht zum Vergleich)."""
    namen = sorted(p.stem for p in markierung.glob("*.txt"))
    if not namen:
        raise FileNotFoundError(f"keine Markierungen (*.txt) in {markierung}")
    groessen = bildgroessen(bilder, namen)
    ergebnisse = {}
    for n in namen:
        breite, hoehe = groessen[n]
        mark = m.objekte_aus_label((markierung / f"{n}.txt").read_text(encoding="utf-8"), breite, hoehe)
        datei = vorhersage / f"{n}.txt"
        vor = m.objekte_aus_vorhersage(datei.read_text(encoding="utf-8"), breite, hoehe) if datei.exists() else []
        ergebnisse[n] = vergleichen(mark, vor, iou_schwelle, konf_schwelle)
    bericht = zusammenfassen(ergebnisse)
    bericht["einstellungen"] = {"iou": iou_schwelle, "konfidenz": konf_schwelle,
                                "bildgroesse": "aus Bildern" if bilder else f"Kodytek {KODYTEK_PX}",
                                "groessen_mm": list(GROESSEN_MM)}
    return bericht, ergebnisse


def fehler_schreiben(ausgabe: Path, bericht: dict, ergebnisse: dict[str, list[dict]]) -> None:
    """bericht.json und fehler.csv (eine Zeile je Objekt, Semikolon) in den Ausgabeordner."""
    ausgabe.mkdir(parents=True, exist_ok=True)
    (ausgabe / "bericht.json").write_text(json.dumps(bericht, ensure_ascii=False, indent=1), encoding="utf-8")
    spalten = ["bild", "art", "klasse", "klasse_vorhersage", "konfidenz", "iou", "kurz_mm", "lang_mm",
               "kurz_vorhersage_mm"]
    with open(ausgabe / "fehler.csv", "w", encoding="utf-8", newline="") as datei:
        schreiber = csv.writer(datei, delimiter=";")
        schreiber.writerow(spalten)
        for n, eintraege in ergebnisse.items():
            for e in eintraege:
                schreiber.writerow([n, *("" if e[s] is None else e[s] for s in spalten[1:])])


def tabelle(bericht: dict) -> str:
    """Kurze Textübersicht je Klasse für das Terminal."""
    zeilen = [f"{'Klasse':16} {'mark':>5} {'treff':>5} {'übers':>5} {'vert':>5} {'falsch':>6} {'R':>6} {'P':>6}"]
    for k, z in bericht["je_klasse"].items():
        r = "-" if z["trefferquote"] is None else f"{z['trefferquote']:.3f}"
        p = "-" if z["praezision"] is None else f"{z['praezision']:.3f}"
        zeilen.append(f"{k:16} {z['markiert']:5} {z['treffer']:5} {z['uebersehen']:5} {z['vertauscht']:5} "
                      f"{z['fehlalarm']:6} {r:>6} {p:>6}")
    mm = bericht["aeste_mm_vorhersage_minus_markierung"]
    if mm["n"]:
        zeilen.append(f"Äste, kurze Achse Vorhersage minus Markierung: n={mm['n']}, mittel {mm['mittel']} mm, "
                      f"sd {mm['sd']} mm")
    return "\n".join(zeilen)


# ---------------------------------------------------------------- Befehle

def _fehler(args) -> None:
    bericht, ergebnisse = fehler_auswerten(args.markierung, args.vorhersage, args.bilder, args.iou, args.konf)
    fehler_schreiben(args.ausgabe, bericht, ergebnisse)
    print(tabelle(bericht))
    print(f"\n{bericht['bilder']} Bilder. Geschrieben: {args.ausgabe}/bericht.json, fehler.csv")


def _messung(args) -> None:
    messungen = messungen_lesen(args.messungen.read_text(encoding="utf-8"))
    funde = json.loads(args.funde.read_text(encoding="utf-8"))
    if isinstance(funde, dict):
        funde = funde.get("funde", [])
    ergebnis = messung_auswerten(messungen, funde, args.balken, args.seite, args.max_abstand, args.laenge_spiegeln,
                                 args.hoehe_spiegeln)
    args.ausgabe.mkdir(parents=True, exist_ok=True)
    (args.ausgabe / "messung.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    dmin = ergebnis["modell_minus_messung_d_min"]
    print(f"Balken {args.balken} Seite {args.seite}: {ergebnis['aeste']} Äste gemessen, {ergebnis['zugeordnet']} "
          f"zugeordnet, ohne Fund: {', '.join(ergebnis['ohne_fund']) or '-'}")
    print(f"Kleinster Durchmesser, Modell minus Messschieber: n={dmin['n']}, mittel {dmin['mittel']} mm, "
          f"sd {dmin['sd']} mm, Grenzen {dmin['grenzen']}")
    print(f"Messende untereinander (d_min): {ergebnis['messende_untereinander']['d_min_mm']}")
    print(f"Geschrieben: {args.ausgabe}/messung.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    befehle = parser.add_subparsers(dest="befehl", required=True)

    p = befehle.add_parser("fehler", help="Markierung gegen Vorhersage je Bild")
    p.add_argument("--markierung", type=Path, required=True, help="Ordner mit Labels (YOLO-seg, *.txt)")
    p.add_argument("--vorhersage", type=Path, required=True, help="Ordner mit Vorhersagen (*.txt von yolo predict)")
    p.add_argument("--bilder", type=Path, help="Bildordner für die echte Bildgröße (sonst Kodytek 2800 x 1024)")
    p.add_argument("--ausgabe", type=Path, required=True, help="Ordner für bericht.json und fehler.csv")
    p.add_argument("--iou", type=float, default=0.5, help="IoU-Schwelle der Masken (Vorgabe 0,5)")
    p.add_argument("--konf", type=float, default=0.25, help="Konfidenzschwelle (Vorgabe 0,25 wie yolo predict)")
    p.set_defaults(aufruf=_fehler)

    p = befehle.add_parser("messung", help="Messschieber gegen Funde auf dem Balken")
    p.add_argument("--messungen", type=Path, required=True, help="messung.csv (docs/messprotokoll-27-11.md)")
    p.add_argument("--funde", type=Path, required=True, help="funde.json von balken.py karte")
    p.add_argument("--balken", required=True)
    p.add_argument("--seite", required=True)
    p.add_argument("--ausgabe", type=Path, required=True, help="Ordner für messung.json")
    p.add_argument("--max-abstand", type=float, default=20.0, help="größter Abstand Ast zu Fund in mm (Vorgabe 20)")
    p.add_argument("--laenge-spiegeln", type=float, metavar="MM",
                   help="Balkenlänge, wenn Ende A rechts im Streifenbild liegt (l -> Länge - l)")
    p.add_argument("--hoehe-spiegeln", type=float, metavar="MM",
                   help="Flächenhöhe, wenn Kante K unten im Streifenbild liegt (q -> Höhe - q)")
    p.set_defaults(aufruf=_messung)

    args = parser.parse_args(argv)
    try:
        args.aufruf(args)
    except (FileNotFoundError, ValueError) as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
