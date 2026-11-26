"""Vorlabeln per Modell (Jan 26.11.2026, docs/plan-vorlabeln.md). Reine Logik, nur Bordmittel, läuft auf Server und
Mac. Getestet in tests/test_vorlabeln.py.

- Kacheln wie beim Training (1280 px, mindestens 256 px Überlappung, bilder.raster). Ein Objekt gehört der Kachel, in
  deren Kern (bis zur Mitte der Überlappung) die Mitte seiner Box liegt, so entsteht es nicht doppelt.
- yolo segment predict mit save_txt und save_conf schreibt je Kachel Zeilen `Nummer x1 y1 ... xn yn Konfidenz` in
  Anteilen der Kachel. Die Nummer heißt über die Namen des Modells (Schlüssel) die feste ID aus klassen.json.
- Einfügen: bestätigte und von Hand gezeichnete Objekte bleiben, alte offene Vorlabel werden ersetzt, neue, die ein
  bleibendes Objekt überdecken, fallen weg.
- Modell: bestes altholz-Modell nach Altholz-Prüfzahl (bei Gleichstand das neuere), sonst kodytek-seg1-n1280."""

import re

KACHEL = 1280
UEBERLAPPUNG = 256
MAX_PUNKTE = 200
UEBERDECKT = 0.5                    # Schnitt mindestens halb so groß wie das kleinere Objekt
STANDARD_MODELL = "kodytek-seg1-n1280"
NAME = re.compile(r"[A-Za-z0-9_.-]{1,60}")


def raster(laenge: int) -> list[int]:
    """Anfänge der Kacheln entlang einer Bildseite, gleich wie bilder.raster (dort mit Pillow, hier ohne)."""
    if laenge <= KACHEL:
        return [0]
    n = -(-(laenge - UEBERLAPPUNG) // (KACHEL - UEBERLAPPUNG))
    return [round(i * (laenge - KACHEL) / (n - 1)) for i in range(n)]


def kerne(anfaenge: list[int], laenge: int) -> list[tuple[float, float]]:
    """Kern jeder Kachel: von der Mitte der Überlappung mit der vorigen bis zur Mitte mit der nächsten."""
    groesse = min(KACHEL, laenge)
    grenzen = [(anfaenge[i] + groesse + anfaenge[i + 1]) / 2 for i in range(len(anfaenge) - 1)]
    return [(grenzen[i - 1] if i else 0.0, grenzen[i] if i < len(grenzen) else float(laenge))
            for i in range(len(anfaenge))]


def kachel_name(foto: str, x0: int, y0: int) -> str:
    return f"{foto}_x{x0:05d}_y{y0:05d}"


def kacheln(foto: str, breite: int, hoehe: int) -> list[dict]:
    """Alle Kacheln eines Fotos mit Lage, Größe und Kern in Pixeln."""
    xs, ys = raster(breite), raster(hoehe)
    kx, ky = kerne(xs, breite), kerne(ys, hoehe)
    return [{"name": kachel_name(foto, x0, y0), "x0": x0, "y0": y0, "b": min(KACHEL, breite), "h": min(KACHEL, hoehe),
             "kern": (kx[i], ky[j])} for j, y0 in enumerate(ys) for i, x0 in enumerate(xs)]


def zeilen_lesen(text: str) -> list[tuple[int, list[tuple[float, float]], float | None]]:
    """Zeilen von yolo segment predict: (Nummer, Punkte in Anteilen der Kachel, Konfidenz oder None)."""
    ergebnis = []
    for zeile in text.splitlines():
        teile = zeile.split()
        if len(teile) < 7:
            continue
        try:
            nr, werte = int(teile[0]), [float(x) for x in teile[1:]]
        except ValueError:
            continue
        conf = werte.pop() if len(werte) % 2 else None
        punkte = list(zip(werte[0::2], werte[1::2], strict=True))
        if len(punkte) >= 3:
            ergebnis.append((nr, punkte, conf))
    return ergebnis


def ausduennen(p: list, n: int = MAX_PUNKTE) -> list:
    if len(p) <= n:
        return p
    return [p[round(i * len(p) / n)] for i in range(n)]


def foto_objekte(foto: str, breite: int, hoehe: int, texte: dict[str, str], zuordnung: dict[int, int],
                 modell: str) -> list[dict]:
    """Vorhersagen aller Kacheln eines Fotos -> offene Objekte in Anteilen des ganzen Zuschnitts."""
    objekte = []
    for k in kacheln(foto, breite, hoehe):
        for nr, punkte, conf in zeilen_lesen(texte.get(k["name"], "")):
            if nr not in zuordnung:
                continue
            px = [(k["x0"] + x * k["b"], k["y0"] + y * k["h"]) for x, y in punkte]
            xs, ys = [q[0] for q in px], [q[1] for q in px]
            mx, my = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            (xl, xh), (yl, yh) = k["kern"]
            if not (xl <= mx <= xh and yl <= my <= yh):
                continue
            p = [[round(min(1.0, max(0.0, x / breite)), 6), round(min(1.0, max(0.0, y / hoehe)), 6)] for x, y in px]
            o = {"k": zuordnung[nr], "ok": False, "p": ausduennen(p), "q": modell}
            if conf is not None:
                o["c"] = round(min(1.0, max(0.0, conf)), 4)
            objekte.append(o)
    return objekte


# ---------------------------------------------------------------- Einfügen in bestehende Labels
def flaeche(p: list) -> float:
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, p[1:] + p[:1], strict=True))) / 2


def drin(x: float, y: float, p: list) -> bool:
    innen, j = False, len(p) - 1
    for i in range(len(p)):
        (xi, yi), (xj, yj) = p[i], p[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            innen = not innen
        j = i
    return innen


def box(p: list) -> tuple[float, float, float, float]:
    xs, ys = [q[0] for q in p], [q[1] for q in p]
    return min(xs), min(ys), max(xs), max(ys)


def ueberdeckt(a: list, b: list, raster_n: int = 24) -> bool:
    """Schnitt zweier Umrisse (gleiche Einheit) mindestens UEBERDECKT des kleineren? Geschätzt über ein Punktraster
    im gemeinsamen Rechteck."""
    ax0, ay0, ax1, ay1 = box(a)
    bx0, by0, bx1, by1 = box(b)
    x0, y0, x1, y1 = max(ax0, bx0), max(ay0, by0), min(ax1, bx1), min(ay1, by1)
    kleiner = min(flaeche(a), flaeche(b))
    if x1 <= x0 or y1 <= y0 or kleiner <= 0:
        return False
    if (x1 - x0) * (y1 - y0) < UEBERDECKT * kleiner:
        return False
    dx, dy = (x1 - x0) / raster_n, (y1 - y0) / raster_n
    treffer = sum(drin(x0 + (i + .5) * dx, y0 + (j + .5) * dy, a) and drin(x0 + (i + .5) * dx, y0 + (j + .5) * dy, b)
                  for i in range(raster_n) for j in range(raster_n))
    return treffer * dx * dy >= UEBERDECKT * kleiner


def einfuegen(alt: list[dict], neu: list[dict]) -> tuple[list[dict], dict]:
    """Neue Vorhersagen in die Objekte eines Fotos. Bestätigte (ok) und offene ohne Quelle (von Hand) bleiben, offene
    Vorlabel (mit q) werden ersetzt. Neue, die ein bleibendes Objekt überdecken, fallen weg."""
    bleibt = [o for o in alt if o.get("ok") or not o.get("q")]
    dazu = [n for n in neu if not any(ueberdeckt(n["p"], o["p"]) for o in bleibt)]
    return bleibt + dazu, {"neu": len(dazu), "verdeckt": len(neu) - len(dazu), "ersetzt": len(alt) - len(bleibt)}


# ---------------------------------------------------------------- Modell und Klassen
def namen_aus_yaml(text: str) -> dict[int, str]:
    """Klassennamen aus einer data.yaml von ultralytics: `names:` als Block (`  0: name` oder `- name`) oder in einer
    Zeile (`[a, b]` oder `{0: a, 1: b}`)."""
    zeilen = text.splitlines()
    for i, z in enumerate(zeilen):
        t = re.fullmatch(r"names:\s*(.*?)\s*", z)
        if not t:
            continue
        rest = t[1]
        if rest.startswith("["):
            return {n: w.strip().strip("'\"") for n, w in enumerate(rest.strip("[]").split(",")) if w.strip()}
        if rest.startswith("{"):
            return {int(a): b.strip().strip("'\"") for a, _, b in
                    (x.partition(":") for x in rest.strip("{}").split(",")) if a.strip().isdigit()}
        namen, n = {}, 0
        for z2 in zeilen[i + 1:]:
            if not z2.startswith((" ", "\t", "-")):
                break
            if e := re.fullmatch(r"\s*(\d+)\s*:\s*(.+?)\s*", z2):
                namen[int(e[1])] = e[2].strip("'\"")
            elif e := re.fullmatch(r"\s*-\s*(.+?)\s*", z2):
                namen[n] = e[1].strip("'\"")
                n += 1
        return namen
    return {}


def zuordnung(namen: dict[int, str], klassen: dict) -> dict[int, int]:
    """YOLO-Nummer des Modells -> feste ID aus klassen.json, über den Schlüssel. Nur aktive Klassen."""
    ids = {k["schluessel"]: k["id"] for k in klassen["klassen"] if k["aktiv"]}
    return {nr: ids[n] for nr, n in namen.items() if n in ids}


def modell_wahl(modelle: list[dict]) -> str | None:
    """modelle: {name, zahl (Altholz-Prüfzahl oder None), zeit}. Bestes altholz-Modell, bei Gleichstand das neuere,
    sonst kodytek-seg1-n1280, sonst keins."""
    altholz = [m for m in modelle if m["name"].startswith("altholz-") and m.get("zahl") is not None]
    if altholz:
        return max(altholz, key=lambda m: (m["zahl"], m["zeit"]))["name"]
    return STANDARD_MODELL if any(m["name"] == STANDARD_MODELL for m in modelle) else None


def fortschritt(log: str) -> tuple[int, int] | None:
    """Letztes `image n/m` aus der Ausgabe von yolo predict."""
    treffer = re.findall(r"image (\d+)/(\d+)", log)
    return (int(treffer[-1][0]), int(treffer[-1][1])) if treffer else None
