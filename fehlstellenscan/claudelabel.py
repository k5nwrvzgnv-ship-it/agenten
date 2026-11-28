"""Vorlabel mit Claude (Jan 28.11.2026 „Baller jetzt die Vorlabels“): Claude sieht Zuschnitte der Fotobox-Fotos mit
Lineal (0-100 %) und nennt je Fehlstelle Klasse, Kästchen und Sicherheit. Python macht daraus Umrisse (opencv) und
offene Vorlabel für Neurolign. Reine Logik ohne Netz und ohne Claude, getestet in tests/test_claudelabel.py.

Warum so: Modelle mit Textprompt (YOLOE, Test 28.11.) fanden auf B004/B005 weder Risse noch Abplatzungen. Claude
erkennt sie, zeichnet aber keine genauen Umrisse; deshalb nur Kästchen von Claude, die Umrisse rechnet opencv:
- Löcher (Nagel-, Bohr-, Astloch, Insekten): dunkelster Fleck im Kästchen (Otsu).
- Risse: je Zeile (oder Spalte) die dunkelste Stelle, als schmales Band über die ganze Länge des Kästchens.
- Sonst (Äste, Abplatzung, Harz, Metall, Verbindung): GrabCut im Kästchen.
Geht das schief (Fleck zu klein oder füllt das Kästchen), gilt die Ellipse im Kästchen."""

import json
import re

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

RAND = 60                     # Lineal um das Bild, px
MAX_PUNKTE = 120
# Schlüssel -> Beschreibung für Claude (Labelrichtlinie, Gruppe 27.11.2026). Nur aktive Klassen gehen in den Prompt.
KLASSEN = {
    "live_knot": "Ast, fest verwachsen, hell bis mittelbraun",
    "dead_knot": "Ast, dunkel, oft mit dunklem Ring, nicht verwachsen",
    "knot_missing": "Astloch: Ast herausgefallen, Loch an Stelle eines Asts",
    "knot_with_crack": "Ast mit Riss durch den Ast",
    "crack": "Riss im Holz (Schwind- oder Trockenriss): sichtbarer Spalt, meist längs zur Faser",
    "riss_klebefuge": "Riss genau in einer Klebefuge (nur bei Brettschichtholz mit Lamellen)",
    "resin": "Harzgalle: mit Harz gefüllte Tasche oder Harzfluss, gelblich bis braun, glänzend",
    "nagelloch": "Nagel- oder Schraubloch ohne Metall: kleines Loch, oft mit dunklem Rand (Rost), oft in einer Reihe",
    "bohrloch": "Bohrloch: rund, scharfer Rand, meist über 8 mm",
    "metall": "Sichtbares Metall: Nagel, Schraube, Klammer, Beschlag",
    "abplatzung": "Abplatzung oder mechanische Beschädigung: Stelle, an der Holz fehlt (Stoß, Werkzeug, Ausriss), "
                  "oft heller als die vergraute Oberfläche, Ränder ausgefranst",
    "insektenfrass": "Insektenloch: Ausflug- oder Einfluglöcher (rund oder oval, 1-6 mm, oft mehrere verstreut) oder "
                     "offene Fraßgänge",
    "verbindung": "Alte Holzverbindung: Zapfenloch, Kerve, Blatt, Versatz",
}
LOCH = {"nagelloch", "bohrloch", "insektenfrass", "knot_missing"}
RISS = {"crack", "riss_klebefuge"}


def prompt(fotos: list[dict], klassen: dict) -> str:
    """fotos: {name, datei (Pfad des Bilds mit Lineal), breite_mm, hoehe_mm, holz}. klassen: klassen.json."""
    aktiv = {k["schluessel"] for k in klassen["klassen"] if k["aktiv"]}
    liste = "\n".join(f"- {s}: {t}" for s, t in KLASSEN.items() if s in aktiv)
    bilder = "\n".join(f"- {f['name']}: Datei {f['datei']}, Bild etwa {f['breite_mm']:.0f} x {f['hoehe_mm']:.0f} mm, "
                       f"{f['holz']}" for f in fotos)
    return f"""Du markierst Fehlstellen auf Fotos von gebrauchten Holzbalken (Altholz) für ein Forschungsprojekt.
Lies jedes Bild mit Read. Um jedes Bild liegt ein Lineal: oben und links 0 bis 100 Prozent der Bildbreite bzw. -höhe
(lange Striche alle 10 %, kurze alle 5 %). Der dunkelblaue Grund neben dem Balken ist Hintergrund.

Bilder:
{bilder}

Klassen (nur diese Schlüssel):
{liste}

Nicht markieren: Maserung, Jahrringe, Farbunterschiede ohne Schaden, Schmutz, Staub, Kreide, Sägespuren, lose Späne,
Hintergrund. Im Zweifel markieren und die Sicherheit niedrig ansetzen.

Kästchen in Prozent des Bildes (Lineal), eng um das sichtbare Merkmal: [links, oben, rechts, unten]. Ein Riss ist ein
Kästchen über seine ganze Länge, auch wenn er sich verzweigt; unterbrochen um mehr als etwa 1 cm: zwei Kästchen.
Berührende Merkmale gleicher Klasse einzeln. Kleine Löcher ebenso eng (z. B. 1 % breit). Sicherheit s von 0 bis 1.

Antworte nur mit JSON, ohne Text davor oder danach:
{{"fotos": {{"<Name>": [{{"k": "<Schlüssel>", "box": [x0, y0, x1, y1], "s": 0.8}}]}}}}
Jedes Bild kommt vor, ohne Fehlstelle mit leerer Liste."""


def antwort_lesen(text: str, namen: list[str], klassen: dict) -> dict[str, list[dict]]:
    """JSON aus der Antwort, geprüft: nur bekannte Fotos und aktive Schlüssel, Kästchen 0-100 mit Fläche. Fotos ohne
    Eintrag fehlen im Ergebnis (nicht leer: dann weiß man, dass Claude sie nicht beantwortet hat)."""
    treffer = re.search(r"\{.*\}", text, re.S)
    if not treffer:
        raise ValueError("Keine JSON-Antwort.")
    roh = json.loads(treffer[0])
    aktiv = {k["schluessel"] for k in klassen["klassen"] if k["aktiv"]} & set(KLASSEN)
    ergebnis = {}
    for name, liste in (roh.get("fotos") or {}).items():
        if name not in namen or not isinstance(liste, list):
            continue
        gut = []
        for f in liste:
            try:
                k, box, s = f["k"], [float(v) for v in f["box"]], float(f.get("s", 0.5))
            except (KeyError, TypeError, ValueError):
                continue
            if k not in aktiv or len(box) != 4:
                continue
            x0, y0, x1, y1 = (min(100.0, max(0.0, v)) for v in box)
            x0, x1 = sorted((x0, x1))
            y0, y1 = sorted((y0, y1))
            if x1 - x0 > 0 and y1 - y0 > 0:
                gut.append({"k": k, "box": [x0, y0, x1, y1], "s": min(1.0, max(0.0, s))})
        ergebnis[name] = gut
    return ergebnis


# ---------------------------------------------------------------- Umrisse
def ellipse(x0: int, y0: int, x1: int, y1: int, n: int = 24) -> list[list[float]]:
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, max(1.0, (x1 - x0) / 2), max(1.0, (y1 - y0) / 2)
    return [[cx + rx * np.cos(2 * np.pi * i / n), cy + ry * np.sin(2 * np.pi * i / n)] for i in range(n)]


def _kontur(maske: np.ndarray, dx: int, dy: int) -> list[list[float]] | None:
    c, _ = cv2.findContours(maske.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not c:
        return None
    c = cv2.approxPolyDP(max(c, key=cv2.contourArea), 1.0, True)
    return [[float(p[0][0] + dx), float(p[0][1] + dy)] for p in c] if len(c) >= 3 else None


def loch(grau: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> list[list[float]] | None:
    """Dunkelster Fleck um die Mitte des Kästchens (Otsu im etwas größeren Ausschnitt)."""
    h, w = grau.shape
    pad = max(3, (x1 - x0 + y1 - y0) // 4)
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)
    roi = cv2.GaussianBlur(grau[Y0:Y1, X0:X1], (3, 3), 0)
    if roi.size < 9 or int(roi.max()) - int(roi.min()) < 15:
        return None
    _, m = cv2.threshold(roi, 0, 1, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    n, lab, st, mitte = cv2.connectedComponentsWithStats(m)
    if n < 2:
        return None
    cx, cy = (x0 + x1) / 2 - X0, (y0 + y1) / 2 - Y0
    i = min(range(1, n), key=lambda j: (st[j, cv2.CC_STAT_AREA] < 4, np.hypot(mitte[j][0] - cx, mitte[j][1] - cy)))
    if st[i, cv2.CC_STAT_AREA] < 4 or st[i, cv2.CC_STAT_AREA] > 0.9 * (X1 - X0) * (Y1 - Y0):
        return None
    return _kontur(lab == i, X0, Y0)


def verfolgen(roi: np.ndarray, sprung: int = 2) -> np.ndarray:
    """Dunkle Linie Zeile für Zeile verfolgen: Start in der Zeile mit dem dunkelsten Punkt, dann nach oben und unten
    je Zeile höchstens `sprung` px seitlich. So bleibt ein schräger Riss eine Linie statt Zickzack."""
    n = roi.shape[0]
    start = int(np.argmin(roi.min(axis=1)))
    lage = np.zeros(n, np.float32)
    lage[start] = float(np.argmin(roi[start]))
    for schritt in (1, -1):
        i = start + schritt
        while 0 <= i < n:
            v = int(lage[i - schritt])
            lo, hi = max(0, v - sprung), min(roi.shape[1], v + sprung + 1)
            lage[i] = lo + int(np.argmin(roi[i, lo:hi]))
            i += schritt
    return lage


def riss(grau: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> list[list[float]] | None:
    """Dunkle Linie je Zeile (hohes Kästchen) bzw. Spalte verfolgt, geglättet, als Band mit geschätzter Breite."""
    roi = cv2.GaussianBlur(grau[y0:y1, x0:x1], (5, 5), 0).astype(np.float32)
    hoch = roi.shape[0] >= roi.shape[1]
    if not hoch:
        roi = roi.T
    if roi.shape[0] < 5 or roi.shape[1] < 3:
        return None
    lage = verfolgen(roi)
    k = max(3, (len(lage) // 15) | 1)
    lage = np.array([np.median(lage[max(0, i - k // 2):i + k // 2 + 1]) for i in range(len(lage))])
    tief = roi[np.arange(len(lage)), lage.astype(int)]
    hell = np.median(roi, axis=1)
    breite = float(np.clip(np.median(np.sum(roi < (tief[:, None] + hell[:, None]) / 2, axis=1)) / 2, 1.5, 6))
    schritt = max(1, len(lage) // 40)
    zeilen = list(range(0, len(lage), schritt)) + [len(lage) - 1]
    links = [(lage[i] - breite, i) for i in zeilen]
    rechts = [(lage[i] + breite, i) for i in reversed(zeilen)]
    punkte = links + rechts
    if hoch:
        return [[float(a + x0), float(b + y0)] for a, b in punkte]
    return [[float(b + x0), float(a + y0)] for a, b in punkte]


def grabcut(bgr: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> list[list[float]] | None:
    h, w = bgr.shape[:2]
    bw, bh = x1 - x0, y1 - y0
    if min(bw, bh) < 6:
        return None
    pad = int(0.15 * max(bw, bh)) + 4
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)
    roi = np.ascontiguousarray(bgr[Y0:Y1, X0:X1])
    m = np.zeros(roi.shape[:2], np.uint8)
    try:
        cv2.grabCut(roi, m, (x0 - X0, y0 - Y0, bw, bh), np.zeros((1, 65)), np.zeros((1, 65)), 5,
                    cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return None
    vorne = ((m == 1) | (m == 3)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(vorne)
    if n < 2:
        return None
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    anteil = st[i, cv2.CC_STAT_AREA] / (bw * bh)
    if not 0.12 <= anteil <= 0.97:
        return None
    return _kontur(lab == i, X0, Y0)


def umriss(bgr: np.ndarray, klasse: str, box: list[float]) -> tuple[list[list[float]], str]:
    """Kästchen in Prozent -> Umriss in Pixeln und wie er entstand ("loch", "riss", "grabcut", "ellipse")."""
    h, w = bgr.shape[:2]
    x0, x1 = (int(round(v / 100 * w)) for v in (box[0], box[2]))
    y0, y1 = (int(round(v / 100 * h)) for v in (box[1], box[3]))
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, max(x1, x0 + 2)), min(h, max(y1, y0 + 2))
    grau = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    if klasse in LOCH:
        p, wie = loch(grau, x0, y0, x1, y1), "loch"
    elif klasse in RISS:
        p, wie = riss(grau, x0, y0, x1, y1), "riss"
    else:
        p, wie = grabcut(bgr, x0, y0, x1, y1), "grabcut"
    if p is None:
        return ellipse(x0, y0, x1, y1), "ellipse"
    return p, wie


def objekte(bgr: np.ndarray, funde: list[dict], ids: dict[str, int], quelle: str) -> list[dict]:
    """Funde eines Fotos -> offene Vorlabel (Anteile des Zuschnitts) wie vorlabeln.foto_objekte."""
    h, w = bgr.shape[:2]
    ergebnis = []
    for f in funde:
        if f["k"] not in ids:
            continue
        p, _ = umriss(bgr, f["k"], f["box"])
        if len(p) > MAX_PUNKTE:
            p = [p[round(i * len(p) / MAX_PUNKTE)] for i in range(MAX_PUNKTE)]
        p = [[round(min(1.0, max(0.0, x / w)), 6), round(min(1.0, max(0.0, y / h)), 6)] for x, y in p]
        ergebnis.append({"k": ids[f["k"]], "ok": False, "p": p, "c": round(f["s"], 4), "q": quelle})
    return ergebnis


# ---------------------------------------------------------------- Bilder
def mit_lineal(bild: Image.Image) -> Image.Image:
    """Bild mit weißem Rand und Lineal 0-100 % (lange Striche und Zahlen alle 10 %, kurze alle 5 %)."""
    w, h = bild.size
    g = Image.new("RGB", (w + 2 * RAND, h + 2 * RAND), "white")
    g.paste(bild, (RAND, RAND))
    d = ImageDraw.Draw(g)
    fo = ImageFont.load_default(size=22)
    for i in range(0, 101, 5):
        x, y, lang = RAND + i / 100 * w, RAND + i / 100 * h, 18 if i % 10 == 0 else 9
        for a, b in (((x, RAND - lang), (x, RAND)), ((x, RAND + h), (x, RAND + h + lang)),
                     ((RAND - lang, y), (RAND, y)), ((RAND + w, y), (RAND + w + lang, y))):
            d.line([a, b], fill="black", width=2)
        if i % 10 == 0:
            d.text((x, 4), str(i), fill="black", font=fo, anchor="ma")
            d.text((4, y), str(i), fill="black", font=fo, anchor="lm")
    return g


def kontrolle(bild: Image.Image, objekte_: list[dict], namen: dict[int, str]) -> Image.Image:
    """Zuschnitt mit Umrissen, Klassenname und Sicherheit (zum Ansehen, nicht fürs Labeln)."""
    farben = ["#00e5ff", "#ff2bd6", "#ffd400", "#7cff4d", "#ff6a00", "#b388ff", "#ffffff", "#ff4d4d"]
    g = bild.convert("RGB").copy()
    d = ImageDraw.Draw(g)
    fo = ImageFont.load_default(size=max(14, g.width // 70))
    w, h = g.size
    for o in objekte_:
        farbe = farben[o["k"] % len(farben)]
        p = [(x * w, y * h) for x, y in o["p"]]
        d.polygon(p, outline=farbe, width=3)
        d.text(min(p), f"{namen.get(o['k'], o['k'])} {o.get('c', 0):.1f}", fill=farbe, font=fo)
    return g
