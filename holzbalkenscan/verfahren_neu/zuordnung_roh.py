"""Zuordnung zweier Aufnahmen direkt im Rohbild, grob nach fein (Frage F5 der PROBLEMSTELLUNG).

Felix' Fassung ordnet auf Streifen zu, die vorher aus den Kantengeraden entzerrt wurden. Sitzt eine
Kante falsch (Reihe C, Prüffall pf-flau), ist der Streifen falsch und die Zuordnung findet nur noch
falsche Treffer. Hier dagegen braucht die Zuordnung weder Kanten noch Band:

1. grob (Teiler 8): Kacheln über das ganze Bild, je Kachel normierte Kreuzkorrelation im anderen Bild,
   Suchfenster weit längs, eng quer. Aus den Treffern per RANSAC mehrere Homographien (Ebenen). Gewählt
   wird die Ebene mit der größten Bewegung: Das Bauteil ist das nächste große Objekt vor der Kamera und
   wandert am weitesten (dieselbe Überlegung wie in band_aus_bewegung).
2. fein (Teiler 2): das zweite Bild mit der groben Homographie auf das erste gelegt, dann Kacheln nur in
   der Fläche der gewählten Ebene, Suche in kleinen Fenstern, RANSAC-Homographie auf den feinen Paaren.

Koordinaten: Arbeitskoordinaten wie im Verfahren (x quer = Spalte, y längs = Zeile), Ergebnis im
vollen Arbeitsbild (Pixel x Teiler). Nur numpy und Pillow.
"""

import numpy as np
from PIL import Image

# grob
G_KACHEL = 48
G_SCHRITT = 32
G_QUER = 60            # Suchfenster quer (Px bei Teiler 8), etwa +-50 mm
G_LAENGS = 0.75        # Suchfenster längs als Anteil der Bildlänge
G_NCC = 0.55
G_ABSTAND = 0.08     # bester Wert muss den zweitbesten (außerhalb des Scheitels) so weit übertreffen
G_ANTEIL = 1.0       # Anteil der Kacheln nach Struktur; 0,5 verdrängte an A die Balkenkacheln (Hintergrund hat mehr)
G_SCHWELLE = 2.0       # RANSAC (Px bei Teiler 8)
G_MIN = 10             # Mindestzahl Treffer einer Ebene
G_EBENEN = 5
# fein
F_KACHEL = 96
F_SUCHE = 24
F_NCC = 0.6
F_SCHWELLE = 2.0       # RANSAC (Px bei Teiler 2)
F_ANZAHL = 60
F_MIN = 8


# --- Bausteine --------------------------------------------------------------------------------

def ncc(bild: np.ndarray, kachel: np.ndarray, zweiter: bool = False):
    """Normierte Kreuzkorrelation über FFT: (dy, dx, wert) des besten Platzes der Kachel im Bild, sonst None.

    dy, dx sind die linke obere Ecke im Bild, mit Unterpixel über eine Parabel durch den Scheitel.
    zweiter=True hängt den besten Wert außerhalb einer halben Kachel um den Scheitel an (Eindeutigkeit).
    """
    kh, kw = kachel.shape
    H, W = bild.shape
    if kh > H or kw > W:
        return None
    k = kachel - kachel.mean()
    kn = float(np.sqrt((k * k).sum()))
    if kn < 1e-6:
        return None
    F = np.fft.rfft2(bild, s=(H, W))
    zaehler = np.fft.irfft2(F * np.fft.rfft2(k[::-1, ::-1], s=(H, W)), s=(H, W))
    eins = np.fft.rfft2(np.ones((kh, kw)), s=(H, W))
    summe = np.fft.irfft2(F * eins, s=(H, W))
    quadr = np.fft.irfft2(np.fft.rfft2(bild * bild, s=(H, W)) * eins, s=(H, W))
    var = np.maximum(quadr - summe * summe / (kh * kw), 1e-6)
    wert = zaehler / (np.sqrt(var) * kn)
    wert = wert[kh - 1:, kw - 1:]  # nur Lagen, in denen die Kachel ganz im Bild liegt
    iy, ix = np.unravel_index(int(np.argmax(wert)), wert.shape)

    def scheitel(v, i):
        if 0 < i < len(v) - 1:
            n = v[i - 1] - 2 * v[i] + v[i + 1]
            if n < 0:
                return i + 0.5 * (v[i - 1] - v[i + 1]) / n
        return float(i)

    erg = (scheitel(wert[:, ix], iy), scheitel(wert[iy, :], ix), float(min(1.0, wert[iy, ix])))
    if zweiter:
        rest = wert.copy()
        rest[max(0, iy - kh // 2):iy + kh // 2 + 1, max(0, ix - kw // 2):ix + kw // 2 + 1] = -1.0
        erg = erg + (float(rest.max()),)
    return erg


def homographie(p: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Normalisierte DLT, bildet p -> q ab (je N x 2, N >= 4)."""
    def norm(z):
        m = z.mean(0)
        s = np.sqrt(2) / (np.linalg.norm(z - m, axis=1).mean() + 1e-12)
        return np.array([[s, 0, -s * m[0]], [0, s, -s * m[1]], [0, 0, 1.0]])
    Tp, Tq = norm(p), norm(q)
    pn = np.c_[p, np.ones(len(p))] @ Tp.T
    qn = np.c_[q, np.ones(len(q))] @ Tq.T
    A = []
    for (x, y, _), (u, v, _) in zip(pn, qn, strict=True):
        A.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        A.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _, _, Vt = np.linalg.svd(np.asarray(A))
    H = np.linalg.inv(Tq) @ Vt[-1].reshape(3, 3) @ Tp
    return H / H[2, 2]


def anwenden(H: np.ndarray, p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, float).reshape(-1, 2)
    ph = np.c_[p, np.ones(len(p))] @ H.T
    with np.errstate(divide="ignore", invalid="ignore"):  # entartete RANSAC-Stichprobe: inf/nan, fällt dort heraus
        return ph[:, :2] / ph[:, 2:3]


def ransac_homographie(p, q, schwelle, runden=400, rng=None):
    """Größte Teilmenge, die EINE Homographie erfüllt: (H, maske) oder (None, leere Maske)."""
    p = np.asarray(p, float)
    q = np.asarray(q, float)
    n = len(p)
    if n < 6:
        return None, np.zeros(n, bool)
    rng = rng or np.random.default_rng(12345)
    best = np.zeros(n, bool)
    for _ in range(runden):
        k = rng.choice(n, 4, replace=False)
        try:
            H = homographie(p[k], q[k])
        except np.linalg.LinAlgError:
            continue
        if not np.all(np.isfinite(H)):
            continue
        drin = np.linalg.norm(anwenden(H, p) - q, axis=1) <= schwelle
        if drin.sum() > best.sum():
            best = drin
    if best.sum() < 6:
        return None, np.zeros(n, bool)
    for _ in range(3):
        H = homographie(p[best], q[best])
        neu = np.linalg.norm(anwenden(H, p) - q, axis=1) <= schwelle
        if neu.sum() < 6 or (neu == best).all():
            break
        best = neu
    return homographie(p[best], q[best]), best


def struktur(a: np.ndarray, y: int, x: int, k: int) -> float:
    """Shi-Tomasi: kleinerer Eigenwert des Strukturtensors der Kachel (Struktur in beiden Richtungen)."""
    t = a[y:y + k, x:x + k]
    gy, gx = np.gradient(t)
    A, B, C = float((gx * gx).mean()), float((gy * gy).mean()), float((gx * gy).mean())
    sp = A + B
    return sp / 2 - max(sp * sp / 4 - (A * B - C * C), 0.0) ** 0.5


# --- grob ---------------------------------------------------------------------------------------

def grobe_treffer(a: np.ndarray, b: np.ndarray):
    """Kachelpaare (Mitte in a, Mitte in b, NCC) über das ganze Bild."""
    L, W = a.shape
    k = G_KACHEL
    kandidaten = []
    for y in range(0, L - k + 1, G_SCHRITT):
        for x in range(0, W - k + 1, G_SCHRITT):
            if a[y:y + k, x:x + k].std() >= 4:
                kandidaten.append((struktur(a, y, x, k), y, x))
    # Holz hat fast nur Struktur quer zur Faser: eine Kachel mit Maserung allein passt längs - genau in
    # Suchrichtung - an vielen Stellen. Solche Treffer fallen über die Eindeutigkeit (G_ABSTAND) heraus.
    kandidaten.sort(reverse=True)
    pa, pb, w = [], [], []
    for _, y, x in kandidaten[:max(G_MIN, int(G_ANTEIL * len(kandidaten)))]:
        t = a[y:y + k, x:x + k]
        y0 = max(0, y - int(G_LAENGS * L))
        y1 = min(L, y + k + int(G_LAENGS * L))
        x0 = max(0, x - G_QUER)
        x1 = min(W, x + k + G_QUER)
        r = ncc(b[y0:y1, x0:x1], t, zweiter=True)
        if r is None or r[2] < G_NCC or r[2] - r[3] < G_ABSTAND:
            continue
        pa.append((x + k / 2, y + k / 2))
        pb.append((x0 + r[1] + k / 2, y0 + r[0] + k / 2))
        w.append(r[2])
    return np.asarray(pa, float).reshape(-1, 2), np.asarray(pb, float).reshape(-1, 2), np.asarray(w)


def ebenen(pa, pb, schwelle=G_SCHWELLE, mindest=G_MIN, hoechstens=G_EBENEN):
    """Bis zu `hoechstens` Homographien nacheinander (Treffer der vorigen entfernt): [(H, maske)]."""
    rest = np.ones(len(pa), bool)
    gefunden = []
    for _ in range(hoechstens):
        idx = np.flatnonzero(rest)
        H, m = ransac_homographie(pa[idx], pb[idx], schwelle)
        if H is None or m.sum() < mindest:
            break
        maske = np.zeros(len(pa), bool)
        maske[idx[m]] = True
        gefunden.append((H, maske))
        rest &= ~maske
    return gefunden


def ebene_waehlen(gefunden, pa, pb, form, erwartet=None, toleranz=0.45):
    """Die Ebene mit der größten Bewegung, die nicht nur ein Fleck ist. None, wenn keine taugt.

    Mit `erwartet` (Bewegung in denselben Px, etwa der Median der Reihe) zählt stattdessen die Ebene, deren
    Bewegung am nächsten daran liegt, und nur innerhalb der Toleranz (Anteil).
    """
    L, W = form
    beste = None
    for H, m in gefunden:
        xs, ys = pa[m, 0], pa[m, 1]
        if np.ptp(xs) < 0.05 * W or np.ptp(ys) < 0.10 * L:
            continue
        weg = float(np.median(np.linalg.norm(pb[m] - pa[m], axis=1)))
        if erwartet is not None:
            if abs(weg - erwartet) > toleranz * erwartet:
                continue
            weg = -abs(weg - erwartet)
        if beste is None or weg > beste[0]:
            beste = (weg, H, m)
    return None if beste is None else (beste[1], beste[2])


# --- Achse aus der Bewegung -----------------------------------------------------------------------

A_PAARE = 6            # Bildpaare, an denen die Achse geprüft wird
A_VERHAELTNIS = 3.0    # Bewegung längs mindestens so viel größer als quer, sonst keine Stimme
A_MEHRHEIT = 2 / 3     # Anteil der Stimmen, der für ein Urteil nötig ist


class NccFeld:
    """Normierte Kreuzkorrelation vieler gleich großer Kacheln gegen DASSELBE ganze Bild.

    Transformierte des Bildes und die Fenstersummen werden einmal gerechnet; je Kachel bleiben eine Hin- und
    eine Rücktransformation. Ergebnis wie ncc(..., zweiter=True).
    """

    def __init__(self, bild: np.ndarray, k: int):
        self.k = k
        self.H, self.W = bild.shape
        s = (self.H, self.W)
        self.F = np.fft.rfft2(bild, s=s)
        eins = np.fft.rfft2(np.ones((k, k)), s=s)
        summe = np.fft.irfft2(self.F * eins, s=s)
        quadr = np.fft.irfft2(np.fft.rfft2(bild * bild, s=s) * eins, s=s)
        self.wurzel = np.sqrt(np.maximum(quadr - summe * summe / (k * k), 1e-6))

    def suche(self, kachel: np.ndarray):
        k = self.k
        t = kachel - kachel.mean()
        kn = float(np.sqrt((t * t).sum()))
        if kn < 1e-6:
            return None
        z = np.fft.irfft2(self.F * np.fft.rfft2(t[::-1, ::-1], s=(self.H, self.W)), s=(self.H, self.W))
        wert = (z / (self.wurzel * kn))[k - 1:, k - 1:]
        iy, ix = np.unravel_index(int(np.argmax(wert)), wert.shape)
        rest = wert.copy()
        rest[max(0, iy - k // 2):iy + k // 2 + 1, max(0, ix - k // 2):ix + k // 2 + 1] = -1.0
        return float(iy), float(ix), float(min(1.0, wert[iy, ix])), float(rest.max())


def treffer_beidseitig(a: np.ndarray, b: np.ndarray):
    """Wie grobe_treffer, aber jede Kachel im GANZEN Bild b gesucht: keine Annahme über die Achse."""
    L, W = a.shape
    k = G_KACHEL
    feld = NccFeld(b, k)
    pa, pb = [], []
    for y in range(0, L - k + 1, G_SCHRITT):
        for x in range(0, W - k + 1, G_SCHRITT):
            t = a[y:y + k, x:x + k]
            if t.std() < 4:
                continue
            r = feld.suche(t)
            if r is None or r[2] < G_NCC or r[2] - r[3] < G_ABSTAND:
                continue
            pa.append((x + k / 2, y + k / 2))
            pb.append((r[1] + k / 2, r[0] + k / 2))
    return np.asarray(pa, float).reshape(-1, 2), np.asarray(pb, float).reshape(-1, 2)


def bewegung_beidseitig(a: np.ndarray, b: np.ndarray):
    """Mittlere Bewegung (dx, dy) der Ebene mit der größten Bewegung, sonst None."""
    pa, pb = treffer_beidseitig(a, b)
    if len(pa) < G_MIN:
        return None
    wahl = ebene_waehlen(ebenen(pa, pb), pa, pb, a.shape)
    if wahl is None:
        return None
    _, m = wahl
    d = pb[m] - pa[m]
    return float(np.median(d[:, 0])), float(np.median(d[:, 1]))


def achse_urteil(bewegungen) -> str | None:
    """'zeilen' (Bauteil bewegt sich längs y), 'spalten' (längs x) oder None, aus den (dx, dy) je Bildpaar."""
    stimmen = []
    for bw in bewegungen:
        if bw is None:
            continue
        dx, dy = abs(bw[0]), abs(bw[1])
        if dy >= A_VERHAELTNIS * max(dx, 1e-9):
            stimmen.append("zeilen")
        elif dx >= A_VERHAELTNIS * max(dy, 1e-9):
            stimmen.append("spalten")
    if len(stimmen) < 3:
        return None
    for urteil in ("zeilen", "spalten"):
        if stimmen.count(urteil) >= A_MEHRHEIT * len(stimmen):
            return urteil
    return None


def paare_fuer_achse(n: int, anzahl: int = A_PAARE) -> list[tuple[int, int]]:
    """Über die Reihe verteilte Nachbarpaare (i, i+1)."""
    if n < 2:
        return []
    return sorted({(i, i + 1) for i in np.linspace(0, n - 2, min(anzahl, n - 1)).round().astype(int).tolist()})


# --- fein ---------------------------------------------------------------------------------------

def skaliert(H: np.ndarray, f: float) -> np.ndarray:
    """Homographie für Koordinaten, die um den Faktor f größer sind."""
    S = np.diag([f, f, 1.0])
    G = S @ H @ np.linalg.inv(S)
    return G / G[2, 2]


def feine_paare(a: np.ndarray, b: np.ndarray, H: np.ndarray, bereich):
    """Paare (in a, in b, NCC je Paar) mit Vorgabe H (a -> b). bereich = (x0, x1, y0, y1) in a."""
    L, W = a.shape
    k = F_KACHEL
    bw = np.asarray(Image.fromarray(b).transform((W, L), Image.PERSPECTIVE, tuple((H / H[2, 2]).flatten()[:8]),
                                                 Image.BILINEAR), np.float32)
    x0, x1, y0, y1 = (int(round(v)) for v in bereich)
    x0, y0 = max(F_SUCHE, x0), max(F_SUCHE, y0)
    x1, y1 = min(W - k - F_SUCHE, x1 - k), min(L - k - F_SUCHE, y1 - k)
    if x1 <= x0 or y1 <= y0:
        return np.zeros((0, 2)), np.zeros((0, 2)), np.zeros(0)
    # Raster über den Bereich, je Zelle die Kachel mit der meisten Struktur in beiden Richtungen
    nx = max(1, min(6, (x1 - x0) // k + 1))
    ny = max(1, F_ANZAHL // nx)
    pa, pw, nw = [], [], []
    for y in np.linspace(y0, y1, ny).astype(int):
        for x in np.linspace(x0, x1, nx).astype(int):
            if struktur(a, y, x, k) < 1.0:
                continue
            if np.count_nonzero(bw[y:y + k, x:x + k] == 0) > 0.05 * k * k:
                continue  # Kachel fällt aus dem zweiten Bild
            sy0, sx0 = y - F_SUCHE, x - F_SUCHE
            r = ncc(bw[sy0:y + k + F_SUCHE, sx0:x + k + F_SUCHE], a[y:y + k, x:x + k])
            if r is None or r[2] < F_NCC:
                continue
            pa.append((x + k / 2, y + k / 2))
            pw.append((sx0 + r[1] + k / 2, sy0 + r[0] + k / 2))
            nw.append(r[2])
    if len(pa) < F_MIN:
        return np.zeros((0, 2)), np.zeros((0, 2)), np.zeros(0)
    pa = np.asarray(pa)
    pb = anwenden(H, np.asarray(pw))  # zurück in die Koordinaten von b
    G, m = ransac_homographie(pa, pb, F_SCHWELLE)
    if G is None or m.sum() < F_MIN:
        return np.zeros((0, 2)), np.zeros((0, 2)), np.zeros(0)
    return pa[m], pb[m], np.asarray(nw)[m]


# --- gesamt -------------------------------------------------------------------------------------

def zuordnen(a8: np.ndarray, b8: np.ndarray, a2: np.ndarray, b2: np.ndarray, voll: float = 2.0,
             erwartet_px: float | None = None):
    """Punktpaare zweier Aufnahmen im vollen Arbeitsbild: (pA, pB, info) oder None.

    a8/b8: grobe Graubilder (Teiler 8), a2/b2: feine (Teiler 2), float32; voll = Faktor fein -> volles Bild.
    erwartet_px: erwartete Bewegung des Bauteils im vollen Bild (Nachlauf mit dem Median der Reihe).
    info: grobe Treffer, Ebenen, gewählte Ebene (Treffer, Bewegung in Px voll), feine Paare, mittlere NCC.
    """
    f = a2.shape[1] / a8.shape[1]
    pa, pb, _ = grobe_treffer(a8, b8)
    info = {"grob": len(pa)}
    if len(pa) < G_MIN:
        return None
    gefunden = ebenen(pa, pb)
    info["ebenen"] = len(gefunden)
    wahl = ebene_waehlen(gefunden, pa, pb, a8.shape, None if erwartet_px is None else erwartet_px / (f * voll))
    if wahl is None:
        return None
    H8, m = wahl
    info["ebene"] = int(m.sum())
    info["bewegung_px"] = float(np.median(np.linalg.norm(pb[m] - pa[m], axis=1))) * f * voll
    g = G_KACHEL / 2
    bereich = np.array([pa[m, 0].min() - g, pa[m, 0].max() + g, pa[m, 1].min() - g, pa[m, 1].max() + g]) * f
    fa, fb, fn = feine_paare(a2, b2, skaliert(H8, f), bereich)
    info["fein"] = len(fa)
    if len(fa) < F_MIN:
        return None
    info["ncc"] = float(fn.mean())
    return fa * voll, fb * voll, info
