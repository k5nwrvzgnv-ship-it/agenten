"""Setzt die Aufnahmen EINER Bauteilseite zu einem masshaltigen Streifen zusammen.

Neubau, 2026-10-20. Nachfolger von `zusammensetzen.py` (Fassung v37). Das alte
Skript bleibt unberuehrt daneben liegen.

Der Unterschied steht in einem Satz: **eine gemeinsame Ausgleichung statt einer
Kette.** Die alte Fassung entzerrte jedes Bild einzeln, haengte Paar an Paar und
reparierte hinterher, was sich dabei aufgeschaukelt hatte - mit Daempfung des
Laengsmassstabs, Abzug eines Trends in der Querlage und einer pauschalen
Stauchung auf die Aufmasslaenge. Jede dieser Reparaturen verschiebt den Fehler,
statt ihn zu beseitigen.

Hier wird stattdessen EIN Gleichungssystem fuer alle Aufnahmen zugleich geloest.

Ablauf
------
    1. Kanten     - je Bild die beiden Bauteilkanten, in drei Durchgaengen:
                    erst die Bandbreite ueber die ganze Reihe, dann je Bild mit
                    Vorhersage aus den Nachbarn, dann je Station. Stationen
                    hinter dem Balkenende fallen heraus.
    2. Zuordnung  - Punktpaare zwischen i und i+1, i+2, i+3. Mehrfachverbindung
                    ueberbrueckt ein gescheitertes Paar von selbst; in der
                    alten Fassung wurden fuenf von 25 Lagen schlicht geraten.
    3. Ausgleich  - je Bild die Kamerapose gegen die Bauteilebene (6 Groessen),
                    dazu die Brennweite global. Residuen: Kantenstationen gegen
                    die bekannte Flaechenhoehe, Punktpaare gegeneinander.
                    Levenberg-Marquardt mit Huber-Gewichten.
                    Weil die Pose metrisch ist, ist der Laengsmassstab KEINE
                    freie Groesse mehr - er folgt aus der Flaechenhoehe und der
                    Kamerageometrie. Darum gibt es hier keine Drift, keine
                    Daempfung und keine Einpassung auf die Aufmasslaenge.
                    Die Aufmasslaenge wird nur noch GEPRUEFT.
    4. Photometrie- je Bild ein Faktor pro Farbkanal plus eine gemeinsame
                    radiale Vignettierung, global aus den Ueberlappungen
                    geloest. Die alte Fassung glich gar nichts an; der
                    Weissabgleich der Kamera lief in der Testreihe um 21 %
                    (R/G) und 28 % (B/G) davon.
    5. Naht       - je Ausgabespalte GENAU EIN Quellbild. Der Schnitt wandert
                    dorthin, wo die beiden Bilder am besten uebereinstimmen,
                    danach wird ueber wenige Millimeter ueberblendet. Die alte
                    Zweibandmischung mittelte die tiefen Frequenzen ueber bis
                    zu drei Bilder und nahm die hohen hart aus einem - daher
                    die Doppelkonturen.
    6. Zeichnen   - jedes Bild GENAU EINMAL vom Originalpixel ins Endraster.
                    Alt waren es drei Abtastungen und zwei JPEG-Stufen.
    7. Bericht    - mit Zahlen, die sich nachrechnen lassen.

Angaben zum Bauteil in `bauteil.json` neben den Aufnahmen.

    python3 zusammensetzen2.py <Bildordner>
    python3 zusammensetzen2.py <Bildordner> --ziel streifen.jpg --px-mm 3
    python3 zusammensetzen2.py <Bildordner> --naht hart     (Naehte sichtbar)

Es braucht ausschliesslich Pillow und numpy.
"""

import argparse
import json
import pickle
import math
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import zuordnung_roh as ZR   # verfahren_neu: Zuordnung im Rohbild (F5)

Image.MAX_IMAGE_PIXELS = None

MELDUNGEN, WARNUNGEN = [], []
T0 = time.time()


def sag(t=""):
    print(t, flush=True)
    MELDUNGEN.append(t)


def warn(t):
    WARNUNGEN.append(t)


def takt(t):
    print(f"      [{time.time()-T0:6.1f} s] {t}", flush=True)


# =============================================================== Geometrie ===

def _norm(p):
    m = p.mean(0)
    s = np.sqrt(2) / (np.linalg.norm(p - m, axis=1).mean() + 1e-12)
    T = np.array([[s, 0, -s * m[0]], [0, s, -s * m[1]], [0, 0, 1]])
    return (np.c_[p, np.ones(len(p))] @ T.T)[:, :2], T


def homographie(quelle, ziel):
    """Normalisierte DLT. Bildet quelle -> ziel ab."""
    q = np.asarray(quelle, float)
    z = np.asarray(ziel, float)
    qn, Tq = _norm(q)
    zn, Tz = _norm(z)
    A = []
    for (x, y), (u, v) in zip(qn, zn):
        A.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        A.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _, _, Vt = np.linalg.svd(np.asarray(A))
    H = np.linalg.inv(Tz) @ Vt[-1].reshape(3, 3) @ Tq
    return H / H[2, 2]


def anwenden(H, p):
    p = np.asarray(p, float).reshape(-1, 2)
    ph = np.c_[p, np.ones(len(p))] @ H.T
    return ph[:, :2] / ph[:, 2:3]


def rodrigues(r):
    """Drehvektor -> Drehmatrix."""
    th = float(np.linalg.norm(r))
    if th < 1e-12:
        return np.eye(3)
    k = np.asarray(r, float) / th
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * (K @ K)


def rodrigues_inv(R):
    """Drehmatrix -> Drehvektor."""
    c = (np.trace(R) - 1) / 2
    c = max(-1.0, min(1.0, c))
    th = math.acos(c)
    if th < 1e-9:
        return np.zeros(3)
    if abs(math.pi - th) < 1e-6:
        # halbe Drehung: ueber die symmetrische Form
        A = (R + np.eye(3)) / 2
        k = np.sqrt(np.maximum(np.diag(A), 0))
        if k[np.argmax(k)] > 0:
            i = int(np.argmax(k))
            k = A[:, i] / k[i]
        return k / (np.linalg.norm(k) + 1e-12) * th
    w = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    return w / (2 * math.sin(th)) * th


def K_matrix(f, cx, cy):
    return np.array([[f, 0.0, cx], [0.0, f, cy], [0.0, 0.0, 1.0]])


def pose_zu_H(rvec, tvec, K):
    """Ebene (u,v,1) -> Bild (x,y,w). u laengs, v quer, beide in mm."""
    R = rodrigues(rvec)
    return K @ np.column_stack([R[:, 0], R[:, 1], np.asarray(tvec, float)])


def H_zu_pose(H, K):
    """Zerlegt eine Ebenen-Homographie in Drehung und Verschiebung."""
    A = np.linalg.inv(K) @ H
    l = 2.0 / (np.linalg.norm(A[:, 0]) + np.linalg.norm(A[:, 1]))
    if (l * A[2, 2]) < 0:                  # Kamera muss vor der Ebene liegen
        l = -l
    r1, r2, t = l * A[:, 0], l * A[:, 1], l * A[:, 2]
    Q = np.column_stack([r1, r2, np.cross(r1, r2)])
    U, _, Vt = np.linalg.svd(Q)
    R = U @ Vt
    if np.linalg.det(R) < 0:
        R = U @ np.diag([1.0, 1.0, -1.0]) @ Vt
    return rodrigues_inv(R), t


# ================================================================= Bilder ===

ENDUNGEN = {".jpg", ".jpeg"}


EIGENE = ("streifen", "kantenbefund", "uebersicht", "pruefbericht")


def bilder_finden(ordner: Path):
    """Aufnahmen im Ordner - ohne das, was diese Werkzeuge selbst schreiben.

    Liegt ein fertiger Streifen im selben Ordner, las ihn die erste Fassung
    als weitere Aufnahme ein. Das faellt nicht sofort auf: Der Streifen ist
    laengs gefasert wie das Bauteil und bringt die Reihenstatistik erst
    langsam durcheinander.
    """
    tr = [p for p in ordner.iterdir()
          if p.is_file() and p.suffix.lower() in ENDUNGEN
          and not p.name.startswith(".")
          and not any(p.name.lower().startswith(s) for s in EIGENE)]
    return sorted(tr, key=lambda p: p.name.lower())


def lade(pfad, teiler=1, dreh=False, grau=False):
    """Oeffnet eine Aufnahme in Arbeitskoordinaten.

    Arbeitskoordinaten heisst: x laeuft QUER zum Bauteil, y LAENGS. Liegt das
    Bauteil im Rohbild andersherum, wird um 90 Grad gedreht - das ist eine
    reine Umsortierung der Pixel, keine zweite Abtastung.

    `teiler` nutzt die JPEG-Stufen des Decoders (draft): ein Viertel der
    Kantenlaenge kostet rund ein Fuenfzehntel der Zeit. Fuer Kantenmessung und
    Zuordnung reicht das; gezeichnet wird spaeter aus dem vollen Bild.
    """
    im = Image.open(pfad)
    if teiler > 1:
        im.draft("L" if grau else "RGB", (im.width // teiler, im.height // teiler))
    im = im.convert("L" if grau else "RGB")
    if dreh:
        im = im.transpose(Image.ROTATE_90)
    return im


def _glatt(v, k):
    """Kastenglaettung mit FORTGESETZTEM Rand.

    np.convolve(mode="same") fuellt ausserhalb mit Null. Das erzeugt an beiden
    Profilenden eine kuenstliche Stufe - und genau auf die ist die Bandsuche
    beim ersten Versuch hereingefallen: Sie meldete als linke Bauteilkante die
    Bildkante.
    """
    k = int(k) | 1
    r = k // 2
    return np.convolve(np.pad(v, r, mode="edge"), np.ones(k) / k, "valid")


def querprofile(a):
    """Drei Querprofile aus einem Bildausschnitt (L,Q,3): hell, satt, warm.

    Drei statt eines: In der Halle war der Balken warm vor grauem Beton, im
    Tageslicht dunkel vor heller Wand. Welches Merkmal an der Kante springt,
    bleibt offen - dass EINES springt, gilt immer.
    """
    hell = a.mean(axis=(0, 2))
    satt = (a.max(axis=2) - a.min(axis=2)).mean(axis=0)
    warm = (a[:, :, 0] - a[:, :, 2]).mean(axis=0)
    out = []
    for v in (hell, satt, warm):
        v = _glatt(v, 5)
        out.append((v - v.mean()) / (v.std() + 1e-6))
    return out


def _gradienten(profile):
    return [np.gradient(p) for p in profile]


def bandgueten(profile, d_bereich, mitte=None, mitte_tol=None, rand=0.025):
    """Guete JEDER Bandbreite: innen anders als aussen, auf BEIDEN Seiten.

    Die erste Fassung suchte "zwei gegenlaeufige Kontraststufen". Das genuegt
    nicht: Zwei Stufen gibt es auch zwischen Bildkante und Bauteiloberkante,
    und die sind staerker als das Bauteil selbst. Gefordert ist jetzt, dass
    der Streifen zwischen i und j sich von BEIDEN Nachbarschaften in dieselbe
    Richtung unterscheidet - das kann nur ein Gegenstand vor einem Hintergrund.

    Gewertet wird mit dem KLEINEREN der beiden Unterschiede: Eine Kante allein
    reicht nicht.
    """
    B = len(profile[0])
    cs = [np.concatenate([[0.0], np.cumsum(p.astype(np.float64))]) for p in profile]
    m0 = int(max(3, rand * B))
    guete = np.full(len(d_bereich), -1e18)
    stelle = np.zeros(len(d_bereich), int)
    for n, d in enumerate(d_bereich):
        d = int(d)
        m = int(max(4, 0.15 * d))
        if d < 8 or d + 2 * m + 2 * m0 >= B:
            continue
        i = np.arange(max(m0, m), B - d - max(m0, m))
        if len(i) < 4:
            continue
        s_ges = np.zeros(len(i))
        for c in cs:
            innen = (c[i + d] - c[i]) / d
            links = (c[i] - c[i - m]) / m
            rechts = (c[i + d + m] - c[i + d]) / m
            a1 = innen - links
            a2 = innen - rechts
            s_ges += np.where(a1 * a2 > 0, np.minimum(np.abs(a1), np.abs(a2)), 0.0)
        if mitte is not None:
            s_ges = np.where(np.abs(i + d / 2.0 - mitte) <= mitte_tol, s_ges, -1e18)
        k = int(np.argmax(s_ges))
        guete[n] = s_ges[k]
        stelle[n] = i[k]
    return guete, stelle


def bandsuche(profile, d_bereich, mitte=None, mitte_tol=None):
    g, st = bandgueten(profile, d_bereich, mitte, mitte_tol)
    k = int(np.argmax(g))
    if g[k] <= -1e17:
        return None
    return float(g[k]), int(st[k]), int(st[k] + d_bereich[k])


def band_aus_bewegung(pfade, dreh, teiler=8, kachel=64, paare=6):
    """Querlage des Bauteils aus der PARALLAXE zwischen zwei Aufnahmen.

    Das Bauteil ist das naechste grosse Objekt vor der Kamera. Zwischen zwei
    Aufnahmen wandert es darum viel weiter durchs Bild als der Hintergrund -
    gemessen an der Reihe Seite C: 280 Px gegen 32 Px. Hintergrund und Boden
    fallen zusaetzlich dadurch heraus, dass ihre Baender an den Bildrand
    stossen; das Bauteil liegt frei im Bild.

    Noetig ist das, wo Helligkeit, Saettigung und Faserrichtung nicht
    ausreichen. In der Reihe Seite C ist der Balken vergraut und steht vor
    grauem Pflaster, waehrend ueber ihm die Hallendecke mit Pfetten und
    Leuchtstoffroehren liegt - lauter lange Linien parallel zum Bauteil. Die
    Suche ueber Farbe und Kontrast griff dort mitten in die Decke und meldete
    6,8 statt 8,8 Px/mm; danach sassen die Kantengeraden um 100 Px daneben
    und nichts passte mehr zusammen.

    Das Ergebnis ist eine VORGABE, keine Messung: Es trifft die Bandbreite auf
    etwa +-8 %. Damit sucht die eigentliche Kantenmessung anschliessend im
    richtigen Bereich.
    """
    schritt = max(1, len(pfade) // (paare + 1))
    grenzen = []
    for k in range(0, min(paare * schritt, len(pfade) - 1), schritt):
        with lade(pfade[k], teiler, dreh, grau=True) as i1, \
             lade(pfade[k + 1], teiler, dreh, grau=True) as i2:
            a = np.asarray(i1, np.float32); b = np.asarray(i2, np.float32)
        L, W = a.shape
        xs, dys = [], []
        for x in range(24, W - kachel - 24, 24):
            for y in range(30, L - kachel - 30, 70):
                t = a[y:y + kachel, x:x + kachel]
                if t.std() < 4:
                    continue
                y0 = max(0, y - int(0.6 * L)); y1 = min(L, y + kachel + int(0.6 * L))
                x0 = max(0, x - 50); x1 = min(W, x + kachel + 50)
                r = ncc_karte(b[y0:y1, x0:x1], t)
                if r is None or r[2] < 0.55:
                    continue
                xs.append(x + kachel / 2.0); dys.append((y0 + r[0]) - y)
        if len(xs) < 15:
            continue
        xs = np.asarray(xs); dys = np.asarray(dys)
        bestes = None
        for d0 in dys:
            m = np.abs(dys - d0) <= max(6.0, 0.12 * abs(d0))
            if m.sum() < 6:
                continue
            lo, hi = np.percentile(xs[m], 4), np.percentile(xs[m], 96)
            if lo < 0.04 * W or hi > 0.96 * W or hi - lo < 0.08 * W:
                continue
            w = abs(np.median(dys[m]))
            if bestes is None or w > bestes[0]:
                bestes = (w, lo, hi)
        if bestes:
            grenzen.append(bestes)
    if len(grenzen) < 2:
        return None
    g = np.asarray([[z[1], z[2]] for z in grenzen], float)
    return (float(np.median(g[:, 0])) * teiler,
            float(np.median(g[:, 1])) * teiler, len(grenzen))


def faserwert(a, x0, x1):
    """Faserausrichtung quer/laengs in einem Querstreifen.

    Gewachsenes Holz hat fast nur Struktur QUER zur Faser; laengs ist es
    glatt. Der Quotient liegt im Balken bei 2 bis 3, in quer liegenden
    Auflagern bei 1.3, auf Pflaster bei 1.5 und auf einem Massstab mit
    seiner Querteilung bei 0.6.
    """
    g = a.mean(axis=2) if a.ndim == 3 else a
    L, Q = g.shape
    x0 = max(0, int(x0)); x1 = min(Q, int(x1))
    if x1 - x0 < 3:
        return float("nan")
    gy, gx = np.gradient(g)
    y0, y1 = int(0.12 * L), int(0.88 * L)
    return float(np.abs(gx[y0:y1, x0:x1]).mean()
                 / (np.abs(gy[y0:y1, x0:x1]).mean() + 1e-6))


def faserscheiben(a, i, j, pxmm_arbeit, scheibe_mm=15.0):
    """Faserausrichtung in Querscheiben des Bandes."""
    n = max(6, int((j - i) / max(3.0, scheibe_mm * pxmm_arbeit)))
    return np.asarray([faserwert(a, i + (j - i) * k / n,
                                 max(i + (j - i) * k / n + 2,
                                     i + (j - i) * (k + 1) / n))
                       for k in range(n)])


def randscheibe(s):
    """Schwaechere der beiden Randscheiben, bezogen auf den Median."""
    med = float(np.median(s))
    if med < 1e-6:
        return 1.0
    return min(float(s[0]), float(s[-1])) / med


def band_waehlen(bilder, stats, kandidaten, HOEHE, fak, mitte, tol, Q):
    """Welche von zwei Bandbestimmungen ist die richtige?

    Das Band ist der Querstreifen, den das Verfahren fuer das Bauteil haelt;
    an ihm haengt der gesamte Massstab, denn seine Breite IST die bekannte
    Flaechenhoehe. Es wird auf zwei Wegen bestimmt - frei im ganzen Bild und
    im Fenster der Parallaxe -, und keiner von beiden ist zuverlaessig: An
    der Reihe 261022/Versuch 1 lieferte der freie Weg 1.60 statt 16.0 Px/mm,
    an Versuch 2 der Parallaxenweg 13.7 statt 15.7.

    Entschieden wird mit zwei Faserproben, die in ENTGEGENGESETZTE
    Richtungen greifen:

      innen  - die aeusserste Scheibe des Bandes muss noch Laengsholz sein.
               Faellt sie unter 70 % des Bandmedians, reicht das Band ueber
               das Bauteil hinaus (Auflager, Massstab).
      aussen - der Streifen DICHT NEBEN dem Band darf kein Laengsholz mehr
               sein. Ist er es doch, hoert das Bauteil dort nicht auf und
               das Band ist zu klein.

    Die zweite Probe ist noetig, weil die erste "zu klein" grundsaetzlich
    nicht sehen kann: Ein zu schmales Band liegt vollstaendig im Holz und
    ist perfekt homogen. An vier Reihen mit acht Kandidaten trennt die
    Schwelle 1.0 alle acht richtig.
    """
    gueltig = {k: v for k, v in kandidaten.items()
               if v and 0.12 * Q <= v <= 0.72 * Q}
    if not gueltig:
        gueltig = {k: v for k, v in kandidaten.items() if v}
    if len(gueltig) < 2:
        return list(gueltig.values())[0], 0.0
    sag("  Zwei unabhaengige Bandbestimmungen:")
    bewertung = {}
    for name, erw in gueltig.items():
        d_eng = np.arange(int(erw * 0.90), int(erw * 1.10) + 1)
        w = max(4, int(15.0 * erw / HOEHE))
        innen, aussen = [], []
        for a, st in zip(bilder, stats):
            b = bandsuche(st[0], d_eng, mitte, tol)
            if not b:
                continue
            _, i, j = b
            kern = faserwert(a, i + 2 * w, j - 2 * w)
            if not np.isfinite(kern) or kern < 1e-6:
                continue
            innen.append(randscheibe(faserscheiben(a, i, j, erw / HOEHE)))
            nb = [faserwert(a, i - w - 2, i - 2), faserwert(a, j + 2, j + w + 2)]
            nb = [v for v in nb if np.isfinite(v)]
            if nb:
                aussen.append(max(nb) / kern)
        i_med = float(np.median(innen)) if innen else 0.0
        a_med = float(np.median(aussen)) if aussen else 9.9
        fehler = []
        if i_med < 0.70:
            fehler.append("greift darueber hinaus")
        if a_med > 1.05:
            fehler.append("zu klein")
        bewertung[name] = len(fehler)
        sag(f"    {name:10} {erw*fak/HOEHE:5.2f} Px/mm   innen {i_med*100:3.0f} %, "
            f"aussen {a_med*100:3.0f} %"
            + ("   " + ", ".join(fehler) if fehler else "   schluessig"))
    namen = sorted(gueltig, key=lambda k: (bewertung[k],
                                           0 if k == "Parallaxe" else 1))
    werte = [v * fak / HOEHE for v in gueltig.values()]
    spanne = (max(werte) - min(werte)) / max(np.median(werte), 1e-9) * 100
    sag(f"    Abweichung der beiden: {spanne:4.1f} %   gewaehlt: {namen[0]}")
    if spanne > 8.0:
        warn(f"Die zwei Bandbestimmungen weichen um {spanne:.0f} % voneinander "
             f"ab - der Massstab ist um diesen Betrag unsicher")
    return gueltig[namen[0]], spanne


def bandbreite_der_reihe(profile_je_bild, d_bereich, mitte=None, mitte_tol=None):
    """Die Bandbreite, auf die sich ALLE Aufnahmen einigen.

    Ein einzelnes Bild laesst sich taeuschen - ein Brett davor, ein Bock, eine
    Latte. Dass sich 26 Aufnahmen auf dieselbe falsche Breite einigen, ist
    dagegen unwahrscheinlich. Deshalb wird nicht je Bild gesucht und hinterher
    gemittelt, sondern erst der gemeinsame Nenner bestimmt.
    """
    S = []
    for prof in profile_je_bild:
        g, _ = bandgueten(prof, d_bereich, mitte, mitte_tol)
        g = np.where(g > -1e17, g, 0.0)
        S.append(g / (g.max() + 1e-9))
    S = np.median(np.asarray(S), axis=0)
    return int(d_bereich[int(np.argmax(S))]), S


def _teilerscharf(s, k):
    """Scheitel einer Parabel durch drei Werte - fuer Unterpixel."""
    if 0 < k < len(s) - 1:
        n = s[k - 1] - 2 * s[k] + s[k + 1]
        if abs(n) > 1e-12:
            return k + float(np.clip((s[k - 1] - s[k + 1]) / (2 * n), -1, 1))
    return float(k)


def stationsprofile(a, stationen=36):
    """Querprofile fuer das ganze Bild und fuer jede Laengsstation.

    Beides in EINEM Durchgang, damit die Aufnahme nur einmal gelesen werden
    muss. Die Profile sind winzig (drei Zeilen je Station); alles Weitere -
    Bandbreite der Reihe, Kanten, Nachmessen im Modellfenster - laeuft
    anschliessend ohne Bildzugriff.
    """
    L = a.shape[0]
    hoehe = max(6, L // stationen)
    ys, sp = [], []
    for k in range(stationen):
        y = k * (L - hoehe) // max(stationen - 1, 1)
        ys.append(y + hoehe / 2.0)
        sp.append(querprofile(a[y:y + hoehe]))
    return querprofile(a), np.asarray(ys, float), sp, float(L)


def kanten_je_station(stat, erw, mitte, tol):
    """`mitte` darf eine Zahl sein oder ein Wert je Station."""
    """Je Laengsstation das Kantenpaar, mit Unterpixelscheitel.

    Der Abstand ist auf +-6 % der Bandbreite der Reihe festgelegt: Bei festem
    Aufnahmeabstand IST die Bandbreite die Bildhoehe des Bauteils, und ein um
    10 % zu schmales Paar ist immer eine Verwechslung mit einer Lamellenfuge.
    """
    _, ys, sp, _ = stat
    d_bereich = np.arange(max(8, int(erw * 0.94)), int(erw * 1.06) + 1)
    mi = np.full(len(ys), float(mitte)) if np.isscalar(mitte) \
        else np.asarray(mitte, float)
    li, re, gu = [], [], []
    for k in range(len(ys)):
        prof = sp[k]
        b = bandsuche(prof, d_bereich, float(mi[k]), tol)
        if b is None:
            continue
        g, i, j = b
        si = sum(np.abs(np.gradient(pp)) for pp in prof)
        li.append((ys[k], _scheitel_nah(si, i)))
        re.append((ys[k], _scheitel_nah(si, j)))
        gu.append((ys[k], g))
    return li, re, gu


def _scheitel_nah(si, i, fen=5):
    """Groesster Gradient in der Naehe von i, dann Parabelscheitel."""
    a = max(1, i - fen); b = min(len(si) - 1, i + fen + 1)
    k = a + int(np.argmax(si[a:b]))
    return _teilerscharf(si, k)


def ausgleichsgerade(pkt, runden=5):
    """x = a + b*y, Ausreisser fallen heraus. Liefert auch die Restabweichung."""
    p = np.asarray(pkt, float)
    y, x = p[:, 0], p[:, 1]
    keep = np.ones(len(y), bool)
    a = b = 0.0
    for _ in range(runden):
        b, a = np.polyfit(y[keep], x[keep], 1)
        r = np.abs(a + b * y - x)
        s = max(1.0, 1.4826 * np.median(r[keep]))
        nk = r <= 3.0 * s
        if nk.sum() < 5 or (nk == keep).all():
            break
        keep = nk
    b, a = np.polyfit(y[keep], x[keep], 1)
    rest = float(np.median(np.abs(a + b * y - x)[keep]))
    return a, b, rest, keep


# ============================================================== Zuordnung ===

def ncc_karte(bild, kachel):
    """Normierte Kreuzkorrelation ueber FFT. Liefert (y, x, wert) des Scheitels."""
    kh, kw = kachel.shape
    H, W = bild.shape
    if kh >= H or kw >= W:
        return None
    k = kachel - kachel.mean()
    kn = float(np.sqrt((k * k).sum()))
    if kn < 1e-6:
        return None
    F = np.fft.rfft2(bild, s=(H, W))
    K = np.fft.rfft2(k[::-1, ::-1], s=(H, W))
    zaehler = np.fft.irfft2(F * K, s=(H, W))
    eins = np.fft.rfft2(np.ones((kh, kw), np.float32)[::-1, ::-1], s=(H, W))
    summe = np.fft.irfft2(F * eins, s=(H, W))
    quadr = np.fft.irfft2(np.fft.rfft2(bild * bild, s=(H, W)) * eins, s=(H, W))
    n = kh * kw
    var = np.maximum(quadr - summe * summe / n, 1e-6)
    wert = np.clip(zaehler / (np.sqrt(var) * kn), -1.0, 1.0)
    g = np.zeros_like(wert, bool)
    g[kh - 1:H, kw - 1:W] = True
    wert = np.where(g, wert, -1.0)
    iy, ix = np.unravel_index(int(np.argmax(wert)), wert.shape)
    # Unterpixel ueber den Scheitel in beiden Richtungen
    sy = _teilerscharf(wert[:, ix], iy) - iy
    sx = _teilerscharf(wert[iy, :], ix) - ix
    return iy - kh + 1 + sy, ix - kw + 1 + sx, float(wert[iy, ix])


def kachelwahl(a, kachel, anzahl, bereich, rand):
    """Kacheln mit Struktur in BEIDEN Richtungen (Shi-Tomasi).

    Nicht die kontrastreichsten: Die kontrastreichste Stelle auf einem
    BSH-Traeger ist eine Lamellenfuge, und eine gerade Linie passt entlang
    ihrer eigenen Richtung ueberall.
    """
    H, W = a.shape
    x0, x1 = bereich
    x0 = max(rand, int(x0)); x1 = min(W - rand, int(x1))
    if x1 - x0 < 2 * kachel:
        return []
    gy, gx = np.gradient(a)
    gxx, gyy, gxy = gx * gx, gy * gy, gx * gy
    out = []
    for fy in np.linspace(0.08, 0.92, 5):
        for fx in np.linspace(0.02, 0.98, 23):
            y = int(rand + fy * (H - 2 * rand)) - kachel // 2
            x = int(x0 + fx * (x1 - x0)) - kachel // 2
            if y < 0 or x < 0 or y + kachel > H or x + kachel > W:
                continue
            s = (slice(y, y + kachel), slice(x, x + kachel))
            A = float(gxx[s].mean()); B = float(gyy[s].mean()); C = float(gxy[s].mean())
            sp = A + B; det = A * B - C * C
            out.append((sp / 2 - max(sp * sp / 4 - det, 0) ** 0.5, y, x))
    out.sort(reverse=True)
    return [(y, x) for _, y, x in out[:anzahl]]


def ransac_affin(p, q, schwelle=2.5, runden=250, rng=None):
    """Groesste Teilmenge, die EINE affine Abbildung erfuellt.

    An dieser Stelle stand frueher ein Mehrheitsentscheid ueber gleiche
    Verschiebungen mit 10 Px Toleranz. Der ist in sich widerspruechlich: Er
    verwirft genau die Abweichungen zwischen den Kacheln, aus denen sich
    Massstab und Perspektive erst ablesen lassen - und meldete deshalb
    'kein Treffer', wo die Bilder nur leicht gegeneinander verdreht waren.
    """
    p = np.asarray(p, float); q = np.asarray(q, float)
    n = len(p)
    if n < 4:
        return np.zeros(n, bool)
    rng = rng or np.random.default_rng(12345)
    A = np.c_[p, np.ones(n)]
    best = np.zeros(n, bool)
    for _ in range(runden):
        k = rng.choice(n, 3, replace=False)
        try:
            M = np.linalg.solve(A[k], q[k])
        except np.linalg.LinAlgError:
            continue
        r = np.linalg.norm(A @ M - q, axis=1)
        drin = r <= schwelle
        if drin.sum() > best.sum():
            best = drin
    if best.sum() >= 4:
        for _ in range(3):
            M, *_ = np.linalg.lstsq(A[best], q[best], rcond=None)
            r = np.linalg.norm(A @ M - q, axis=1)
            nb = r <= schwelle
            if nb.sum() < 4 or (nb == best).all():
                break
            best = nb
    return best


def paar_zuordnen(A, B, berA, berB, kachel, erwartet, fenster,
                  ncc_min=0.45, anzahl=26):
    """Punktpaare zwischen zwei vorentzerrten Streifen.

    A, B sind Graustreifen im GLEICHEN Ebenenrahmen (x laengs, y quer), also
    bleibt nur eine kleine Restverschiebung. `erwartet` ist die Vorhersage in
    Px, `fenster` ihre Unsicherheit; ohne Vorhersage wird der ganze Streifen
    durchsucht.
    """
    kac = kachelwahl(A, kachel, anzahl, berA, rand=4)
    pA, pB, wert = [], [], []
    for y, x in kac:
        if fenster is None:
            x0, x1 = 0, B.shape[1]
        else:
            xm = int(x + erwartet)
            x0 = max(0, xm - fenster); x1 = min(B.shape[1], xm + kachel + fenster)
        y0 = max(0, y - 40); y1 = min(B.shape[0], y + kachel + 40)
        if x1 - x0 <= kachel or y1 - y0 <= kachel:
            continue
        r = ncc_karte(B[y0:y1, x0:x1], A[y:y + kachel, x:x + kachel])
        if r is None or r[2] < ncc_min:
            continue
        pA.append((x + kachel / 2.0, y + kachel / 2.0))
        pB.append((x0 + r[1] + kachel / 2.0, y0 + r[0] + kachel / 2.0))
        wert.append(r[2])
    if len(pA) < 5:
        return None
    drin = ransac_affin(pA, pB, schwelle=2.5)
    if drin.sum() < 5:
        return None
    pA = np.asarray(pA)[drin]; pB = np.asarray(pB)[drin]
    return pA, pB, float(np.mean(np.asarray(wert)[drin]))


# =========================================================== Ausgleichung ===

class Modell:
    """Alle Unbekannten der Reihe in einem Vektor.

    Je Bild: Drehung IN DER BILDEBENE (eine Groesse) und Verschiebung (drei).
    Fuer die ganze Reihe gemeinsam: die VERKIPPUNG gegen die Bauteilebene
    (zwei Groessen) und die Brennweite.

    Warum die Verkippung gemeinsam und nicht je Bild - das ist der Kern:

    Bei fast senkrechter Aufnahme lassen sich Verkippung und Aufnahmeabstand
    gegeneinander tauschen, ohne dass sich das Bild merklich aendert. Kippt
    man die Kamera um die Laengsachse und geht naeher heran, bleibt die
    Bauteilhoehe im Bild gleich breit - nur der Laengsmassstab aendert sich.
    Je Bild ist diese Groesse also NICHT bestimmbar, und eine Ausgleichung,
    die sie trotzdem freigibt, laeuft in den Unsinn: Gemessen wurden 70 Grad
    Verkippung bei 55 mm Aufnahmeabstand fuer Bilder, deren Kante durch ein
    davorstehendes Brett gestoert war - und das passte zu allen Punktpaaren
    genauso gut wie die richtige Loesung.

    Gemeinsam ist sie dagegen gut bestimmt, denn sie ist fuer die ganze Reihe
    eine Groesse gegen tausend Beobachtungen. Und sie ist auch physikalisch
    richtig: Wer eine Reihe fotografiert, haelt das Geraet dabei gleich.

    Die eine verbleibende Mehrdeutigkeit - der gemeinsame Laengsmassstab -
    wird von der bekannten Gesamtlaenge aufgeloest.
    """

    JE_BILD = 5

    def __init__(self, gammas, kx, tvecs, ky, basis, f, cx, cy, f0):
        self.n = len(gammas)
        self.f0 = f0
        self.cx, self.cy = cx, cy
        self.basis = basis
        teile = []
        for g, a, t in zip(gammas, kx, tvecs):
            teile.append(np.concatenate([[g, a], t]))
        self.p = np.concatenate(teile + [[ky], [f]])

    def drehung(self, p, i):
        """Bilddrehung, Verjuengung laengs (je Bild), Verkippung quer (global).

        Die Aufteilung ist der Kern des Modells:

        Eine Drehung um die QUERachse laesst das Band laengs zulaufen. Das ist
        im Bild zu sehen und also messbar - sie bleibt je Bild frei.

        Eine Drehung um die LAENGSachse staucht das Band nur quer, und
        dasselbe tut ein kleinerer Aufnahmeabstand. Die beiden sind aus einer
        Aufnahme von vorn nicht zu trennen. Je Bild freigegeben, laeuft die
        Ausgleichung damit in den Unsinn (gemessen: 70 Grad Verkippung bei
        55 mm Aufnahmeabstand). Fuer die ganze Reihe EINE Groesse ist sie
        dagegen gut bestimmt - und physikalisch richtig, denn wer eine Reihe
        fotografiert, haelt das Geraet dabei gleich.
        """
        g, a = p[5 * i], p[5 * i + 1]
        ky = p[5 * self.n]
        return (rodrigues([a, ky, 0.0])
                @ rodrigues([0.0, 0.0, g]) @ self.basis)

    def tvec(self, p, i):
        return p[5 * i + 2:5 * i + 5]

    def entpacken(self, p=None):
        p = self.p if p is None else p
        f = p[-1]
        K = K_matrix(f, self.cx, self.cy)
        Hs, His = [], []
        for i in range(self.n):
            R = self.drehung(p, i)
            H = K @ np.column_stack([R[:, 0], R[:, 1], self.tvec(p, i)])
            Hs.append(H); His.append(np.linalg.inv(H))
        return Hs, His, f

    def lot(self, p, i):
        R = self.drehung(p, i)
        return abs(float(self.tvec(p, i) @ R[:, 2]))

    def neigung(self, p, i):
        R = self.drehung(p, i)
        return math.degrees(math.acos(min(1.0, abs(R[2, 2]))))


def bauen_residuen(mod, kanten, paare, HOEHE, s_kante, s_paar, u_fix,
                   d0, laenge=None, gew=None):
    """Residuenfunktion fuer Levenberg-Marquardt. Alles in Millimetern.

    Zur Laengenbedingung: Der LAENGSmassstab folgt aus zwei parallelen Kanten
    im bekannten Abstand NICHT - siehe die Begruendung bei `Modell`. Die
    bekannte Gesamtlaenge ist deshalb Eingangsgroesse und nicht Probe. Wer
    eine unabhaengige Laengsprobe will, braucht zwei eingemessene Marken im
    Bild.
    """

    SIN_KIPP = math.sin(math.radians(25.0))

    def f(p):
        _, His, fbr = mod.entpacken(p)
        teile = []
        for i, (qs, soll) in enumerate(kanten):
            if len(qs) == 0:
                continue
            uv = anwenden(His[i], qs)
            teile.append((uv[:, 1] - soll) / s_kante)
        for (i, j, qi, qj) in paare:
            a = anwenden(His[i], qi)
            b = anwenden(His[j], qj)
            teile.append(((a - b) / s_paar).ravel())
        uv0 = anwenden(His[0], [[mod.cx, mod.cy]])[0]
        teile.append(np.array([(uv0[0] - u_fix) / 2.0]))
        # Verkippung quer (global) und Verjuengung laengs (je Bild): beide nur
        # gegen das voellig Unmoegliche gefesselt.
        teile.append(np.array([p[5 * mod.n] / math.radians(25.0)]))
        kx = p[1:5 * mod.n:5]
        # Die gemessene Verjuengung der Reihe liegt bei 1 bis 2 % ueber das
        # Bild, das sind unter 1,5 Grad. Mehr als ein paar Grad ist deshalb
        # keine Perspektive mehr, sondern eine verrutschte Kantenmessung.
        teile.append(kx / math.radians(2.5))
        teile.append((kx - kx.mean()) / math.radians(1.5))
        # Aufnahmeabstand je Bild: absolut und gegen den Reihenmittelwert
        ab = np.array([(mod.lot(p, i) - d0) / (0.25 * d0) for i in range(mod.n)])
        teile.append(ab)
        teile.append((ab - ab.mean()) * 0.25 / 0.10)
        if laenge is not None:
            qa, ia, qb, ib = laenge[0], laenge[1], laenge[2], laenge[3]
            ua = anwenden(His[ia], [qa])[0][0]
            ub = anwenden(His[ib], [qb])[0][0]
            teile.append(np.full(8, (abs(ub - ua) - laenge[4]) / 2.0))
        teile.append(np.full(24, (fbr - mod.f0) / (0.03 * mod.f0)))
        r = np.concatenate(teile)
        return r if gew is None else r * gew[0]

    return f


def levenberg(fun, p0, runden=40, lam=1e-3, melde=None, frei=None):
    """Levenberg-Marquardt mit numerischer Jacobimatrix.

    Die Jacobimatrix numerisch zu bilden kostet hier rund 160 Auswertungen je
    Schritt. Jede Auswertung ist eine Handvoll 3x3-Inversen und ein paar
    tausend Punkttransformationen - in numpy Millisekunden. Analytisch
    abzuleiten waere schneller und deutlich fehleranfaelliger.
    """
    p = p0.copy()
    r = fun(p)
    F = float(r @ r)
    n = len(p)
    sp = np.arange(n) if frei is None else np.nonzero(frei)[0]
    for it in range(runden):
        J = np.zeros((len(r), n))
        for k in sp:
            h = max(1e-7, abs(p[k]) * 1e-6)
            q = p.copy(); q[k] += h
            J[:, k] = (fun(q) - r) / h
        A = J.T @ J
        g = J.T @ r
        dia = np.maximum(np.diag(A), 1e-12)
        if frei is not None:                 # eingefrorene Spalten stilllegen
            A[~frei, :] = 0.0; A[:, ~frei] = 0.0
            A[~frei, ~frei] = 1.0; g[~frei] = 0.0; dia[~frei] = 1.0
        besser = False
        for _ in range(8):
            try:
                dp = np.linalg.solve(A + lam * np.diag(dia), -g)
            except np.linalg.LinAlgError:
                lam *= 10; continue
            rn = fun(p + dp)
            Fn = float(rn @ rn)
            if Fn < F:
                p, r, F = p + dp, rn, Fn
                lam = max(lam * 0.3, 1e-9)
                besser = True
                break
            lam *= 10
        if melde:
            melde(it, F, len(r))
        if not besser or (it > 2 and abs(dp).max() < 1e-7):
            break
    return p, r


# ============================================================ Photometrie ===

def lichtfeld_basis(xi, eta):
    """Glattes Feld ueber dem BILD, Grad zwei ohne konstantes Glied."""
    return np.stack([xi, eta, xi * xi, xi * eta, eta * eta], axis=1)


def photometrie(proben, n):
    """Je Bild ein Faktor pro Farbkanal UND ein gemeinsames Lichtfeld.

    Zwei Dinge zugleich, und beides ist noetig:

    Die FAKTOREN gleichen aus, dass Belichtung und Weissabgleich der Kamera
    mitliefen. Sie werden nicht verkettet, sondern in einem Gleichungssystem
    fuer die ganze Reihe geloest.

    Das LICHTFELD gleicht aus, was von der Stelle IM BILD abhaengt und nicht
    vom Bild: Vignettierung des Objektivs - und, wichtiger, der Schatten des
    Fotografen, der mit der Kamera mitwandert und deshalb immer an derselben
    Stelle im Bildfeld steht.

    Ohne das Feld geht es schief, und zwar systematisch: In der Ueberlappung
    liegt dieselbe Stelle am Bauteil im einen Bild vorn und im anderen hinten.
    Ist es vorn heller als hinten, meldet JEDES Bildpaar denselben kleinen
    Helligkeitsunterschied - und der summiert sich ueber die Reihe auf. Ein
    Lauf endete so mit Faktoren von 0,82 bis 1,47, obwohl die Aufnahmen selbst
    nur +-7 % auseinanderlagen. Das Feld faengt genau diesen Anteil ab.

    Zusaetzlich ein schwacher Zug der Faktoren gegen eins: Was weder Faktor
    noch Feld erklaeren koennen, soll nicht in den Faktoren landen.
    """
    M = 5
    if not proben:
        return np.ones((n, 3)), np.zeros(M)
    A, b, w = [], [], []
    for (i, j, li, lj, pi, pj) in proben:
        dF = lichtfeld_basis(pj[:, 0], pj[:, 1]) - lichtfeld_basis(pi[:, 0], pi[:, 1])
        for c in range(3):
            d = lj[:, c] - li[:, c]
            Z = np.zeros((len(d), 3 * n + M))
            Z[:, 3 * i + c] = -1.0
            Z[:, 3 * j + c] = 1.0
            Z[:, 3 * n:] = dF
            A.append(Z); b.append(d); w.append(np.full(len(d), 1.0))
    # Eichung: je Kanal bleibt das Mittel der Reihe stehen
    for c in range(3):
        Z = np.zeros((1, 3 * n + M)); Z[0, c::3][:n] = 1.0
        A.append(Z); b.append(np.zeros(1)); w.append(np.full(1, 60.0))
    # schwacher Zug der Faktoren gegen eins und des Feldes gegen flach
    Z = np.zeros((3 * n, 3 * n + M)); Z[np.arange(3 * n), np.arange(3 * n)] = 1.0
    A.append(Z); b.append(np.zeros(3 * n)); w.append(np.full(3 * n, 1.0 / 0.30))
    Z = np.zeros((M, 3 * n + M)); Z[np.arange(M), 3 * n + np.arange(M)] = 1.0
    A.append(Z); b.append(np.zeros(M)); w.append(np.full(M, 1.0 / 0.40))
    A = np.vstack(A); b = np.concatenate(b); w = np.concatenate(w)
    x = None
    for _ in range(3):
        Aw = A * w[:, None]; bw = b * w
        x, *_ = np.linalg.lstsq(Aw, bw, rcond=None)
        r = A @ x - b
        sg = 1.4826 * np.median(np.abs(r)) + 1e-9
        w = np.minimum(1.0, 2.0 * sg / np.maximum(np.abs(r), 1e-9)) ** 0.5 * \
            np.where(np.arange(len(r)) >= len(r) - 3 * n - M - 3, 1.0, 1.0)
        w[-(3 * n + M + 3):] = np.concatenate([np.full(3, 60.0),
                                               np.full(3 * n, 1.0 / 0.30),
                                               np.full(M, 1.0 / 0.40)])
    G = x[:3 * n].reshape(n, 3)
    k = x[3 * n:]
    return np.exp(G), k


# ============================================================== Zeichnen ====

def schrift(groesse):
    from PIL import ImageFont
    for pfad in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "/System/Library/Fonts/HelveticaNeue.ttc",
                 "/Library/Fonts/Arial Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(pfad, groesse), True
        except Exception:
            continue
    return ImageFont.load_default(), False


def fett(d, xy, text, font, echt, farbe=(40, 40, 40)):
    d.text(xy, text, fill=farbe, font=font)
    if not echt:
        d.text((xy[0] + 1, xy[1]), text, fill=farbe, font=font)


def beschriften(kern, daten, LAENGE, HOEHE, PXMM, SP):
    """Weisse Einfassung mit Teilung. Nullpunkt oben links AM BAUTEIL."""
    LUFT = int(round(4 * PXMM)); TICK = int(round(9 * PXMM)); TEXT = int(round(16 * PXMM))
    R = LUFT + TICK + TEXT
    f, echt = schrift(max(11, int(round(4.2 * PXMM))))
    KOPF = int(round(7 * PXMM))
    out = Image.new("RGB", (kern.width + 2 * R, kern.height + 2 * R + KOPF), (255, 255, 255))
    out.paste(kern, (R, R))
    d = ImageDraw.Draw(out)
    d.rectangle([R - 1, R - 1, R + kern.width, R + kern.height], outline=(200, 200, 200))
    # Haarlinien auf der Sollkante: Daran laesst sich ablesen, ob die
    # Bauteilkante wandert oder ob nur der Hintergrund dahinter wechselt.
    for mm in (0.0, HOEHE):
        y = R + SP + mm * PXMM
        d.line([R, y, R + kern.width, y], fill=(220, 60, 60), width=1)
    for mm in (0.0, LAENGE):
        x = R + SP + mm * PXMM
        d.line([x, R, x, R + kern.height], fill=(220, 60, 60), width=1)
    nx = R + SP; ny = R + SP

    def striche(laenge_mm, start, richtung):
        for mm in range(0, int(laenge_mm) + 1, 10):
            p = start + mm * PXMM
            lang = TICK if mm % 100 == 0 else (int(TICK * 0.6) if mm % 50 == 0 else int(TICK * 0.35))
            br = 3 if mm % 100 == 0 else 1
            if richtung == "x":
                for yA, yB in ((R - LUFT - lang, R - LUFT),
                               (R + kern.height + LUFT, R + kern.height + LUFT + lang)):
                    d.line([p, yA, p, yB], fill=(40, 40, 40), width=br)
                if mm % 100 == 0:
                    t = f"{mm}"; w = d.textlength(t, font=f)
                    fett(d, (p - w / 2, R - LUFT - TICK - TEXT + 2), t, f, echt)
                    fett(d, (p - w / 2, R + kern.height + LUFT + TICK + 2), t, f, echt)
            else:
                for xA, xB in ((R - LUFT - lang, R - LUFT),
                               (R + kern.width + LUFT, R + kern.width + LUFT + lang)):
                    d.line([xA, p, xB, p], fill=(40, 40, 40), width=br)
                if mm % 100 == 0:
                    t = f"{mm}"; w = d.textlength(t, font=f)
                    fett(d, (R - LUFT - TICK - w - 4, p - 7), t, f, echt)
                    fett(d, (R + kern.width + LUFT + TICK + 4, p - 7), t, f, echt)

    striche(LAENGE, nx, "x")
    striche(HOEHE, ny, "y")
    fett(d, (R, R + kern.height + R + int(KOPF * 0.15)),
         f"{daten.get('bauteil','?')}  Seite {daten.get('seite','?')}   "
         f"BAUTEIL {LAENGE:.0f} x {HOEHE:.0f} mm   {PXMM:g} Px/mm   "
         f"Teilung 10 / 50 / 100 mm   "
         f"Nullpunkt = obere linke Bauteilecke, nicht Bildecke   "
         f"Saum ringsum {SP/PXMM:g} mm echter Hintergrund",
         f, echt, (110, 110, 110))
    return out


# ================================================================ Pruefung ===

def nahtversatz(bild, PXMM, SP, naehte_px):
    """Springt das Lamellenbild AN DEN NAEHTEN quer?

    Das ist die Zahl, auf die es ankommt. Ein langsames Wandern ueber Meter
    hinweg kann auch das Bauteil selbst haben; ein Sprung an einer Naht kann
    nur vom Verfahren kommen.

    Gemessen wird der Querversatz des Querprofils zwischen 15 mm vor und
    15 mm hinter der Naht - also lokal, wo die Lamellenfolge eindeutig ist.
    Ein Vergleich gegen ein festes Bezugsprofil taugt hier NICHT: Das
    Querprofil wiederholt sich alle 33 mm, und die Zuordnung rastet dann um
    eine ganze Lamelle versetzt ein.
    """
    a = np.asarray(bild.convert("L"), np.float32)
    H, W = a.shape
    q0 = SP + int(0.06 * (H - 2 * SP)); q1 = H - SP - int(0.06 * (H - 2 * SP))
    F = max(4, int(round(10 * PXMM)))
    rg = int(round(6 * PXMM))

    def prof(x):
        x = int(max(0, min(W - F, x)))
        v = a[q0:q1, x:x + F].mean(axis=1)
        return v - v.mean()

    def schritt(xa, xb):
        p1, p2 = prof(xa), prof(xb)
        c = np.correlate(p2, p1, "full")
        seg = c[len(p1) - 1 - rg:len(p1) + rg]
        return (_teilerscharf(seg, int(np.argmax(seg))) - rg) / PXMM

    # In kleinen Schritten ueber die Naht, nicht in einem Sprung: Nur so
    # bleibt jeder Einzelschritt eindeutig - das Querprofil wiederholt sich
    # alle 33 mm, und ein weiter Sprung rastet leicht eine Lamelle versetzt
    # ein.
    sw = max(2, int(round(5 * PXMM)))
    out = []
    for nx in naehte_px:
        v = 0.0
        for x in range(int(nx - 3 * sw), int(nx + 3 * sw), sw):
            v += schritt(x, x + sw)
        out.append(v)
    return np.asarray(out)


def balkenenden(bild, pxmm, SAUM, HOEHE):
    """Anfang und Ende des Bauteils im Streifen - ueber die Faserrichtung.

    Gewachsenes Holz hat fast nur Struktur QUER zur Faser: Jahrringe, Fugen
    und Risse laufen laengs. Der Quotient aus Querkanten und Laengskanten ist
    darum im Holz gross (hier 2,7) und im Hintergrund klein (0,3 bis 0,9) -
    gleich, ob dort Beton, ein Feuerloescher oder eine Hose steht.

    Zwei naheliegende Tests taugen NICHT:
    - "Hinter dem Balkenende hoert das Kantenpaar auf": Die Bauteilkante
      streut im fertigen Streifen um gut einen Millimeter, ein Test auf einen
      Helligkeitssprung an genau einer Zeile greift deshalb kaum.
    - "Innen ist Holz, aussen Hintergrund": Am Balkenende steht dahinter
      weiter Hintergrund, aber im Saum ebenso - der Unterschied verschwindet
      nicht, er wird nur zufaellig.

    Das ist keine Feinheit. Beim ersten Lauf lag der Balkenanfang um 100 mm
    und das Ende um 146 mm daneben; weil die Gesamtlaenge auf diese beiden
    Punkte gezogen wird, war der ganze Streifen laengs 4 % zu klein.
    """
    SPp = int(round(SAUM * pxmm))
    a = np.asarray(bild.convert("L"), np.float32)
    H, W = a.shape
    q0 = SPp + int(0.10 * (H - 2 * SPp)); q1 = H - SPp - int(0.10 * (H - 2 * SPp))
    inn = a[q0:q1]
    gv = np.abs(np.gradient(inn, axis=0)); gu = np.abs(np.gradient(inn, axis=1))
    # Feine Bloecke (4 mm): Die Balkenenden sollen auf wenige Millimeter
    # sitzen, denn an ihnen haengt der Laengsmassstab. Die Mittelung ueber
    # die Bauteilhoehe traegt das - ein Block hat immer noch einige tausend
    # Bildpunkte.
    blk = max(4, int(round(4 * pxmm)))
    nb = inn.shape[1] // blk
    if nb < 12:
        return None
    rv = gv[:, :nb * blk].reshape(-1, nb, blk).mean(axis=(0, 2))
    ru = gu[:, :nb * blk].reshape(-1, nb, blk).mean(axis=(0, 2))
    r = rv / np.maximum(ru, 1e-6)
    m = float(np.median(r[nb // 4:3 * nb // 4]))
    if not m > 0:
        return None
    ok = r > 0.50 * m
    # Laengster Lauf OHNE Lueckenschluss - und erst danach nach aussen
    # wachsen, solange die naechsten 100 mm im Mittel noch Holz sind.
    #
    # Pauschal Luecken zu ueberbruecken geht hier schief: Hinter dem
    # Balkenende steht oft wieder Holz - eine Latte, ein Bock. Einzelne
    # Bloecke davon bestehen den Schwellwert, und der Lauf zieht sich dann
    # bis dorthin (gemessen: 157 mm zu weit, und weil die Gesamtlaenge auf
    # diese Punkte gezogen wird, war der ganze Streifen 4 % zu klein).
    # Mit dem Fenster faellt so ein kurzes Stueck durch, waehrend ein echter
    # Einbruch im Balken - ueber einem Bock, an einer Fehlstelle - ueberfahren
    # wird, weil dahinter wieder Balken kommt.
    best, lf = (0, 0), None
    for k in range(nb + 1):
        d = k < nb and bool(ok[k])
        if d and lf is None:
            lf = k
        elif not d and lf is not None:
            if k - lf > best[1] - best[0]:
                best = (lf, k)
            lf = None
    if best[1] - best[0] < 4:
        return None
    fen = max(2, int(round(100.0 * pxmm / blk)))
    a0, a1 = best
    while a0 > 0 and r[max(0, a0 - fen):a0].mean() > 0.55 * m:
        a0 -= 1
    while a1 < nb and r[a1:min(nb, a1 + fen)].mean() > 0.55 * m:
        a1 += 1

    # Das Fenster schaut 100 mm nach aussen; es haelt deshalb schon an, wenn
    # die Kante noch rund ihre halbe Breite entfernt ist. Zum Schluss also
    # scharfstellen: die Stelle suchen, an der sich 40 mm innen und 40 mm
    # aussen am staerksten unterscheiden - und zwar nur in der Naehe der
    # gewachsenen Grenze, damit nicht eine Helligkeitsstufe IM Balken
    # genommen wird (am Reihenanfang lehnt ein helleres Brett davor).
    kf = max(2, int(round(40.0 * pxmm / blk)))
    um = max(2, int(round(90.0 * pxmm / blk)))

    def scharf(k0, nach_rechts):
        bw, bk = -1e9, k0
        for x in range(max(kf, k0 - um), min(nb - kf, k0 + um) + 1):
            drin = r[x:x + kf].mean() if nach_rechts else r[x - kf:x].mean()
            raus = r[x - kf:x].mean() if nach_rechts else r[x:x + kf].mean()
            if raus > 0.5 * m:
                continue
            if drin - raus > bw:
                bw, bk = drin - raus, x
        return bk

    a0 = scharf(a0, True)
    a1 = scharf(a1, False)
    if a1 - a0 < 4:
        a0, a1 = best
    return (a0 * blk / pxmm, a1 * blk / pxmm, m)


def vorschau(B, Hs, rang, schnitte, U0, U1, dreh, W_V, SAUM, HOEHE, pxmm=2.0):
    """Grober Streifen in Grau - nur zum Auffinden der Balkenenden."""
    Wv = int(math.ceil((U1 - U0) * pxmm))
    Hv = int(round((HOEHE + 2 * SAUM) * pxmm))
    lw = np.full((Hv, Wv), 255, np.uint8)
    for k, i in enumerate(rang):
        ua = U0 if k == 0 else schnitte[k - 1]
        ub = U1 if k == len(rang) - 1 else schnitte[k]
        X0 = max(0, int(math.floor((ua - U0) * pxmm)))
        X1 = min(Wv, int(math.ceil((ub - U0) * pxmm)))
        if X1 - X0 < 2:
            continue
        im = lade(B[i]["pfad"], 4, dreh, grau=True)
        sk = im.size[0] / W_V
        A = np.array([[1 / pxmm, 0, X0 / pxmm + U0], [0, 1 / pxmm, -SAUM],
                      [0, 0, 1.0]])
        M = np.diag([sk, sk, 1.0]) @ Hs[i] @ A
        M = M / M[2, 2]
        lw[:, X0:X1] = np.asarray(im.transform((X1 - X0, Hv), Image.PERSPECTIVE,
                                               tuple(M.flatten()[:8]),
                                               Image.BILINEAR), np.uint8)
        im.close()
    return Image.fromarray(lw)


def kantenlauf(bild, PXMM, SP):
    """Wie gerade laeuft die Bauteilkante im fertigen Streifen?

    Der Saum ist dafuer da: Die Kante muss im Streifen ueberall bei SP liegen.
    Was davon abweicht, ist Ausbruch am Bauteil ODER Verfahrensfehler - die
    langwellige Abweichung ist das Verfahren, die kurzwellige das Bauteil.
    """
    a = np.asarray(bild.convert("L"), np.float32)
    H, W = a.shape
    such = min(H - 1, 3 * SP + 6)
    xs = range(0, W, max(1, int(5 * PXMM)))
    k = []
    for x in xs:
        d = np.diff(a[:such, x])
        k.append(int(np.argmin(d)) + 1)
    k = np.asarray(k, float)
    med = float(np.median(k))
    gut = np.abs(k - med) < 4 * PXMM
    if gut.mean() < 0.5:
        return None
    v = np.where(gut, k, med)
    f = 41 if len(v) > 60 else max(3, (len(v) // 2) * 2 - 1)
    sm = np.convolve(np.pad(v, f // 2, mode="edge"), np.ones(f) / f, "valid")[:len(v)]
    return (float(k[gut].std() / PXMM), float((sm.max() - sm.min()) / PXMM),
            float(gut.mean()))


def nahtmass(bild, pxmm):
    """Senkrechte Kanten im Streifen. Holz hat fast nur waagerechte Struktur."""
    a = np.asarray(bild.convert("L"), np.float32)
    H = a.shape[0]
    inn = a[int(0.15 * H):int(0.85 * H)]
    gx = np.abs(np.gradient(inn, axis=1)).mean(axis=0)
    gy = float(np.abs(np.gradient(inn, axis=0)).mean())
    g = gx / max(gy, 1e-6)
    grund = float(np.median(g))
    if not grund > 0:
        return 0, 0.0
    st = np.nonzero(g > 3 * grund)[0]
    return len(st), float(g.max() / grund)


def welligkeit(bild, PXMM, SP):
    """Helligkeitswelligkeit laengs, nach Abzug des Verlaufs ueber 600 mm."""
    a = np.asarray(bild.convert("L"), np.float32)
    H = a.shape[0]
    L = a[SP + 10:H - SP - 10].mean(axis=0)
    L = L[::max(1, int(PXMM))]
    k = 601 if len(L) > 700 else (len(L) // 2) * 2 + 1
    pad = np.pad(L, (k // 2, k // 2), mode="edge")
    gl = np.convolve(pad, np.ones(k) / k, "valid")[:len(L)]
    d = L - gl
    m = float(np.median(L))
    return float(d.std() / max(m, 1e-6) * 100)


# ================================================================== Daten ===

def daten_lesen(ordner):
    datei = ordner / "bauteil.json"
    if not datei.exists():
        print(f"Es fehlt {datei}. Bitte anlegen (Vorlage: bauteil_vorlage.json).")
        return None
    d = {k: v for k, v in json.loads(datei.read_text(encoding="utf-8")).items()
         if not k.startswith("_")}
    d.setdefault("px_mm", 6.0)
    fehlt = [s for s in ("flaeche_hoehe_mm", "laenge_mm") if not d.get(s)]
    if fehlt:
        print(f"In bauteil.json fehlt: {', '.join(fehlt)}")
        return None
    return d


def brennweite_schaetzen(pfad, lang):
    """Aus den Kameradaten, sonst Nennwert eines Handyobjektivs."""
    try:
        ex = Image.open(pfad).getexif()
        f35 = ex.get_ifd(0x8769).get(41989)
        if f35 and 10 < float(f35) < 200:
            return lang * float(f35) / 36.0, f"EXIF {float(f35):.0f} mm (KB)"
    except Exception:
        pass
    return lang * 26.0 / 36.0, "angenommen 26 mm (KB)"


# ================================================================= Ablauf ===

class Bildcache:
    """Haelt wenige Aufnahmen in verkleinerter Fassung vor.

    Die volle Reihe im Speicher zu halten, waeren bei 26 Aufnahmen und einem
    Viertel der Kantenlaenge knapp ein Gigabyte. Neu einzulesen kostet Bruch-
    teile einer Sekunde, weil der JPEG-Decoder die Verkleinerung selbst macht.
    """

    def __init__(self, dreh, tiefe=4):
        self.dreh = dreh
        self.tiefe = tiefe
        self.inhalt = {}
        self.folge = []

    def hole(self, pfad, teiler, grau=False):
        s = (str(pfad), teiler, grau)
        if s in self.inhalt:
            return self.inhalt[s]
        im = lade(pfad, teiler, self.dreh, grau=grau)
        a = np.asarray(im, np.float32 if not grau else np.float32)
        im.close()
        self.inhalt[s] = a
        self.folge.append(s)
        while len(self.folge) > self.tiefe:
            del self.inhalt[self.folge.pop(0)]
        return a


def achse_bestimmen(pfade):
    """Laeuft das Bauteil im Rohbild laengs der Zeilen oder der Spalten?

    Massgeblich ist nicht die Guete einer einzelnen Suche, sondern die
    Bestaendigkeit: Auf der richtigen Achse findet sich in jeder Aufnahme ein
    Band von fast derselben Breite. Auf der falschen findet sich irgendetwas,
    und jedes Mal etwas anderes.
    """
    proben = pfade[:: max(1, len(pfade) // 5)][:5]
    erg = {}
    for dreh in (False, True):
        br = []
        for q in proben:
            im = lade(q, 8, dreh)
            prof = querprofile(np.asarray(im, np.float32))
            im.close()
            B = len(prof[0])
            # Obergrenze 0.72, nicht 0.48: Sobald das Bauteil mehr als die
            # Haelfte des Bildes fuellt, liegt sein Band ueber der alten
            # Grenze und die Suche findet auf der RICHTIGEN Achse nur noch
            # Bruchstuecke - gemessen an der Reihe 261022/Versuch 2, wo der
            # Balken 60 % der Bildhoehe einnimmt: 46, 61, 61, 46, 361 Px
            # statt der wahren 433 bis 459. Die Achse kippte dadurch auf die
            # falsche, und alles Weitere war Unsinn (Faserrichtung 0.40 -
            # der Kehrwert des richtigen Werts). Mit 0.72 sind es 3.6 %
            # Streuung statt 24.6 %. Weiter als 0.73 geht nicht: bandgueten
            # braucht beidseits noch Rand zum Vergleichen.
            b = bandsuche(prof, np.arange(int(0.06 * B), int(0.72 * B), 1))
            if b:
                br.append(b[2] - b[1])
        if len(br) >= 3:
            m = float(np.median(br))
            erg[dreh] = float(np.median(np.abs(np.asarray(br) - m))) / max(m, 1e-6)
        else:
            erg[dreh] = 9.9
    sag(f"Bauteilachse: laengs der Zeilen {erg[False]*100:5.1f} % Streuung der "
        f"Bandbreite, laengs der Spalten {erg[True]*100:5.1f} %")
    return erg[True] < erg[False]


def stationen_messen(stat, erw, mitte, HOEHE, fak, tol_f=0.08):
    """Kantenstationen eines Bildes samt Gueltigkeit.

    Gueltig ist eine Station nur, wenn BEIDE Kanten auf ihrer Ausgleichsgeraden
    liegen. Die reine Kantenstaerke taugt dafuer nicht: Hinter dem Balkenende
    findet die Suche immer irgendein Paar - eine Fuge im Pflaster, eine
    Hosenkante -, nur eben nicht auf der Geraden der Bauteilkanten.
    """
    # Zwei Durchgaenge. Im ersten steht das Suchfenster fest, im zweiten
    # folgt es der gefundenen Kante.
    #
    # Das ist noetig, sobald das Bauteil merklich schraeg im Bild liegt: Bei
    # 3 Grad wandert das Band ueber die Bildhoehe um mehr als 300 Px, und ein
    # festes Fenster von +-70 Px verliert es auf halber Strecke. Die Reihe
    # Seite C lag so; die Kantengeraden sassen dort um 80 bis 180 Px daneben,
    # waehrend es in einer geraden Reihe 2 bis 20 Px sind.
    li, re, gu = kanten_je_station(stat, erw, mitte, max(tol_f * 2 * erw,
                                                        0.30 * erw))
    if len(li) < 12:
        return None
    a1, b1, _, _ = ausgleichsgerade(li)
    a2, b2, _, _ = ausgleichsgerade(re)
    ys_ = stat[1]
    li, re, gu = kanten_je_station(
        stat, erw, (a1 + b1 * ys_ + a2 + b2 * ys_) / 2.0, 0.12 * erw)
    if len(li) < 12:
        return None
    a1, b1, r1, _ = ausgleichsgerade(li)
    a2, b2, r2, _ = ausgleichsgerade(re)
    y = np.asarray([v[0] for v in li], float)
    xl = np.asarray([v[1] for v in li], float)
    xr = np.asarray([v[1] for v in re], float)
    g = np.asarray([v[1] for v in gu], float)
    dl = np.abs(a1 + b1 * y - xl); dr = np.abs(a2 + b2 * y - xr)
    tol = max(2.5, tol_f * erw)
    # ZWEI Massstaebe, und das ist wichtig:
    #
    #   streng  - welche Stationen in die Ausgleichung eingehen. Hier zaehlt
    #             Genauigkeit; eine Station an einer ausgebrochenen Ecke wuerde
    #             die Kantengerade verziehen.
    #   weit    - auf welchem Laengsabschnitt das Bauteil ueberhaupt im Bild
    #             ist. Hier zaehlt Vollstaendigkeit. Mit nur einem, strengen
    #             Mass fielen Bilder auf ein Drittel ihrer Laenge zusammen,
    #             obwohl der Balken durchgehend zu sehen war - und im Streifen
    #             blieben Luecken.
    streng = (dl < tol) & (dr < tol) & (g > 0.50 * np.median(g))
    weit = (dl < 4 * tol) & (dr < 4 * tol) & (g > 0.22 * np.median(g))

    def laengster(m):
        bs, lf = (0, 0), None
        for k in range(len(m) + 1):
            d = k < len(m) and bool(m[k])
            if d and lf is None:
                lf = k
            elif not d and lf is not None:
                if k - lf > bs[1] - bs[0]:
                    bs = (lf, k)
                lf = None
        return bs

    bs = laengster(weit)
    if bs[1] - bs[0] < 8:
        return None
    sel = np.zeros(len(streng), bool)
    sel[bs[0]:bs[1]] = True
    sel &= streng
    if sel.sum() < 6:
        sel = np.zeros(len(streng), bool); sel[bs[0]:bs[1]] = True
    qs = np.concatenate([np.c_[xl[sel], y[sel]], np.c_[xr[sel], y[sel]]]) * fak
    soll = np.concatenate([np.zeros(int(sel.sum())), np.full(int(sel.sum()), HOEHE)])
    yb = y[bs[0]:bs[1]]
    return dict(qs=qs, soll=soll, gerade=(a1 * fak, b1, a2 * fak, b2),
                rest=max(r1, r2) * fak, y0=float(yb.min()) * fak,
                y1=float(yb.max()) * fak, nst=int(sel.sum()), nges=len(streng),
                ymax=stat[3])


def verjuengung_abgleichen(B, L_V, HOEHE, fak, grenze=0.015):
    """Die Bandbreite darf sich ueber das Bild nur so verjuengen wie bei allen.

    Dass das Band oben etwas breiter ist als unten, ist Perspektive und bei
    gleichem Aufnahmeabstand in jeder Aufnahme fast gleich (hier -1 bis -2 %).
    Weicht eine Aufnahme davon stark ab, liegt das nicht an der Kamera,
    sondern daran, dass die Kantensuche auf etwas anderes gelaufen ist - in
    dieser Reihe auf ein Brett, das vor dem Balkenanfang lehnte.

    Das ist kein Schoenheitsfehler: Aus einer Verjuengung von 5 % folgert das
    Kameramodell eine starke Verkippung, und mit ihr einen falschen
    LAENGSmassstab. Die betroffenen Aufnahmen bekamen 60 Grad Verkippung und
    110 mm Aufnahmeabstand zugewiesen, die Reihenmitte 12 Grad und 630 mm.

    Darum: Verjuengung messen, Median der Reihe bilden, und bei Ausreissern
    die Kantenstationen durch Punkte auf den berichtigten Geraden ersetzen.
    Die LAGE der Kanten bleibt gemessen, nur ihre Verjuengung wird gesetzt.
    """
    Y = float(L_V - 1)
    v = []
    for b in B:
        a1, b1, a2, b2 = b["gerade"]
        v.append((b2 - b1) * Y / max(a2 - a1, 1e-6))
    v = np.asarray(v)
    m = float(np.median(v))
    mad = float(np.median(np.abs(v - m))) + 1e-9
    schlecht = np.abs(v - m) > max(grenze, 4.0 * mad)
    sag(f"  Verjuengung des Bandes ueber das Bild: Median {m*100:+.2f} %, "
        f"Streuung {mad*100:.2f} %")
    for i, b in enumerate(B):
        if not schlecht[i]:
            continue
        a1, b1, a2, b2 = b["gerade"]
        b2n = b1 + m * (a2 - a1) / Y
        ys = np.linspace(b["y0"], b["y1"], 24)
        qs = np.concatenate([np.c_[(a1 + b1 * ys), ys], np.c_[(a2 + b2n * ys), ys]])
        b["qs"] = qs
        b["soll"] = np.concatenate([np.zeros(24), np.full(24, HOEHE)])
        b["gerade"] = (a1, b1, a2, b2n)
        sag(f"  {b['name']}: Verjuengung {v[i]*100:+.2f} % statt {m*100:+.2f} % "
            f"- Kante auf die Reihe abgeglichen (steht dort etwas vor dem Bauteil?)")
        warn(f"{b['name']}: Bandverjuengung {v[i]*100:+.1f} % unplausibel - "
             f"Kante abgeglichen, Geometrie dort weniger sicher")
    return int(schlecht.sum())


def main() -> int:
    p = argparse.ArgumentParser(description="Setzt eine Bauteilseite zusammen.")
    p.add_argument("ordner", type=Path)
    p.add_argument("--ziel", type=Path, default=None)
    p.add_argument("--px-mm", type=float, default=None)
    p.add_argument("--naht", choices=("weich", "hart"), default="weich")
    p.add_argument("--ohne-einpassung", action="store_true",
                   help="Laengsmassstab NICHT auf das Aufmass setzen - zeigt "
                        "die rohe Geometrie samt ihrer Laengenabweichung")
    p.add_argument("--ohne-massstab", action="store_true")
    p.add_argument("--ohne-photometrie", action="store_true")
    p.add_argument("--achse", choices=("auto", "zeilen", "spalten"), default="auto")
    p.add_argument("--band", choices=("parallaxe", "frei", "melden"),
                   default="melden",
                   help="welche der zwei Bandbestimmungen benutzt wird. "
                        "'melden' (Vorgabe) rechnet beide, nimmt den "
                        "Parallaxenweg und meldet den Streit; 'frei' nimmt "
                        "den gewaehlten; 'parallaxe' spart die zweite "
                        "Rechnung ganz.")
    p.add_argument("--weiter", action="store_true",
                   help="Geometrie und Photometrie aus dem Zwischenspeicher "
                        "neben dem Ziel uebernehmen und nur neu zeichnen")
    p.add_argument("--brennweite-frei", action="store_true",
                   help="Brennweite mitschaetzen statt sie auf den EXIF-Wert "
                        "festzuhalten")
    p.add_argument("--nur-geometrie", action="store_true",
                   help="nur rechnen und den Zwischenspeicher schreiben")
    p.add_argument("--ohne-rohbild", action="store_true",
                   help="verfahren_neu: Zuordnung nur auf den Streifen wie in "
                        "der alten Fassung (zum Messen des Achsentests allein)")
    a = p.parse_args()

    if not a.ordner.is_dir():
        print(f"Kein Ordner: {a.ordner}"); return 2
    daten = daten_lesen(a.ordner)
    if daten is None:
        return 2
    alle = bilder_finden(a.ordner)
    if len(alle) < 2:
        print(f"Mindestens zwei JPEG-Dateien noetig, gefunden: {len(alle)}")
        return 2

    HOEHE = float(daten["flaeche_hoehe_mm"])
    LAENGE = float(daten["laenge_mm"])
    PXMM = float(a.px_mm or daten["px_mm"])
    SAUM = float(daten.get("saum_mm", 5.0))
    SP = int(round(SAUM * PXMM))
    ZH = int(round((HOEHE + 2 * SAUM) * PXMM))
    SUCH = 3.0
    FEDER = 24.0                                    # Ueberblendbreite in mm
    ziel = a.ziel or a.ordner.parent / f"streifen2_{a.ordner.name}.jpg"

    sag(f"Bauteil {daten.get('bauteil','?')}, Seite {daten.get('seite','?')} "
        f"- {len(alle)} Aufnahmen")
    sag(f"{LAENGE:g} x {HOEHE:g} mm, Ziel {PXMM:g} Px/mm, Saum {SAUM:g} mm")
    gem = daten.get("flaeche_hoehe_mm_gemessen")
    if gem and len(gem) >= 2:
        sp = max(gem) - min(gem)
        sag(f"  Hoehe an {len(gem)} Stellen gemessen, Spanne {sp:.1f} mm "
            f"= {sp/HOEHE*100:.2f} % - das ist die Toleranz des Massnormals")
    if daten.get("lamellen"):
        sag(f"  {daten['lamellen']} Lamellen -> im Mittel "
            f"{HOEHE/daten['lamellen']:.1f} mm")
    sag("")

    zsp = ziel.with_suffix(".modell.pkl")
    if a.weiter and zsp.exists():
        with open(zsp, "rb") as fh:
            Z = pickle.load(fh)
        sag(f"Zwischenspeicher uebernommen: {zsp.name}")
        MELDUNGEN[:0] = Z["meldungen"]
        WARNUNGEN[:] = Z["warnungen"]
        return zeichnen(a, daten, Z, HOEHE, LAENGE, PXMM, SAUM, SP, ZH, ziel)

    dreh = achse_bestimmen(alle) if a.achse == "auto" else (a.achse == "spalten")
    if a.achse == "auto":
        # verfahren_neu: zweiter Achsentest aus der BEWEGUNG zwischen den
        # Aufnahmen. Der Bandtest oben haengt am Kantenkontrast; im Pruefling
        # pf-flau (13 Bilder mit flauer Kante) waehlte er die falsche Achse,
        # und alles Weitere war gedreht. Wer eine Reihe fotografiert, geht am
        # Bauteil entlang: die Ebene mit der groessten Bewegung (das Bauteil)
        # wandert laengs. Gesucht wird ohne Annahme ueber die Achse, im ganzen
        # Bild. Ist das Urteil eindeutig, gilt es; sonst bleibt der Bandtest.
        bew = []
        for i, j in ZR.paare_fuer_achse(len(alle)):
            with lade(alle[i], 8, False, grau=True) as i1, \
                 lade(alle[j], 8, False, grau=True) as i2:
                bew.append(ZR.bewegung_beidseitig(np.asarray(i1, np.float32),
                                                  np.asarray(i2, np.float32)))
        urteil = ZR.achse_urteil(bew)
        txt = ", ".join("-" if b is None else f"{b[0]:+.0f}/{b[1]:+.0f}" for b in bew)
        sag(f"  Achse aus der Bewegung (dx/dy je Bildpaar, Teiler 8: {txt}): "
            f"{ {'zeilen': 'laengs der Zeilen', 'spalten': 'laengs der Spalten', None: 'kein Urteil'}[urteil] }")
        if urteil is not None and (urteil == "spalten") != dreh:
            dreh = urteil == "spalten"
            warn("Bauteilachse aus der Bewegung weicht vom Bandtest ab - die Bewegung gilt")
            sag("  ACHTUNG  Bandtest und Bewegung uneins - die Bewegung gilt")
        takt("Achse aus der Bewegung")
    cache = Bildcache(dreh)
    with lade(alle[0], 1, dreh) as im0:
        W_V, L_V = im0.size
    cx, cy = (W_V - 1) / 2.0, (L_V - 1) / 2.0
    F_BR, F_Q = brennweite_schaetzen(alle[0], max(W_V, L_V))
    sag(f"  Arbeitsbild {W_V} x {L_V} Px, Brennweite {F_BR:.0f} Px ({F_Q})")

    # --- 1: Band und Kanten je Bild ---------------------------------------
    sag("")
    sag("Kanten")
    TEILER = 4
    stats = []
    for q in alle:
        stats.append(stationsprofile(cache.hole(q, TEILER), 36))
    Bq = len(stats[0][0][0])
    fak = W_V / Bq
    takt("Profile gelesen")

    # Vorgabe aus der Parallaxe - sie sagt, WO im Bild das Bauteil liegt.
    bv = band_aus_bewegung(alle, dreh)
    if bv is None:
        sag("  Bewegungsvorgabe nicht moeglich - es wird im ganzen Bild gesucht")
        warn("Querlage des Bauteils nicht aus der Bewegung bestimmbar")
        d_grob = np.arange(int(0.06 * Bq), int(0.72 * Bq), 2)
        m0 = t0 = None
    else:
        lo, hi = bv[0] / fak, bv[1] / fak
        br0 = hi - lo; m0 = (lo + hi) / 2.0; t0 = 0.30 * br0
        d_grob = np.arange(max(8, int(0.75 * br0)), int(1.30 * br0) + 1, 2)
        sag(f"  Vorgabe aus der Bewegung ({bv[2]} Bildpaare): Bauteil liegt bei "
            f"{bv[0]:.0f}..{bv[1]:.0f} Px quer, also etwa "
            f"{(hi-lo)*fak/HOEHE:.1f} Px/mm")
    takt("Bewegungsvorgabe")
    # Zwei Wege zum Band, und dann die Entscheidung dazwischen. Frueher
    # wurde nur der Parallaxenweg genommen; an der Reihe 261022/Versuch 2
    # waren das 13.69 statt 15.68 Px/mm, und erst die Nachmessung je Bild
    # brachte den Streifen auf 15.06 zurueck - die rohe Laenge wich trotzdem
    # 3.1 % vom Aufmass ab.
    erw_par, _S = bandbreite_der_reihe([t[0] for t in stats], d_grob, m0, t0)
    erw = erw_par
    if bv is not None and a.band != "parallaxe":
        erw_frei, _ = bandbreite_der_reihe(
            [t[0] for t in stats], np.arange(int(0.06 * Bq), int(0.72 * Bq), 2))
        proben = list(range(0, len(alle), max(1, len(alle) // 4)))[:4]
        gewaehlt, _spanne = band_waehlen(
            [cache.hole(alle[n], TEILER) for n in proben],
            [stats[n] for n in proben],
            {"Parallaxe": erw_par, "frei": erw_frei},
            HOEHE, fak, m0, t0, Bq)
        # Gewaehlt wird nur auf ausdrueckliche Anweisung.
        #
        # Die Wahl erkennt den Streit richtig, aber sie entscheidet ihn nicht
        # zuverlaessig genug, um stillschweigend umzuschalten: An der Reihe
        # 261022/Versuch 2 waehlt sie das freie Band (15.64 statt 13.69
        # Px/mm) - und der Streifen wird davon SCHLECHTER (Nahtversatz 0.92
        # statt 0.21 mm, belegt 1222 statt 1568 mm), weil das breitere Band
        # ueber das Bild um 8.7 % statt 4.1 % verjuengt und die Ausgleichung
        # das als Perspektive deuten muss. Eine unabhaengige Probe ueber
        # Brennweite und Aufnahmeabstand (5824 Px / 389 mm) sagt 14.97 Px/mm
        # - die Wahrheit liegt also ZWISCHEN beiden Kandidaten, und keiner
        # der beiden Wege trifft sie.
        #
        # Bis das geklaert ist, bleibt es beim bisherigen Weg und der Streit
        # wird nur gemeldet. `--band frei` nimmt den anderen.
        if a.band == "frei":
            erw = gewaehlt
            sag("    (--band frei: der gewaehlte Wert wird benutzt)")
        else:
            sag("    (es wird weiter der Parallaxenweg benutzt; "
                "--band frei nimmt den anderen)")
    sag(f"  Bandbreite, auf die sich alle Aufnahmen einigen: {erw} Px im "
        f"Messbild = {erw*fak/HOEHE:.2f} Px/mm im Original")

    d_eng = np.arange(int(erw * 0.90), int(erw * 1.10) + 1)
    mi, bw = [], []
    for t in stats:
        b = bandsuche(t[0], d_eng, m0, t0)
        mi.append((b[1] + b[2]) / 2.0 if b else np.nan)
        bw.append(b[2] - b[1] if b else np.nan)
    mi = np.asarray(mi, float); bw = np.asarray(bw, float)
    sag(f"  je Bild: {np.nanmin(bw)*fak/HOEHE:.2f} .. {np.nanmax(bw)*fak/HOEHE:.2f} Px/mm "
        f"(+/-{(np.nanmax(bw)/np.nanmin(bw)-1)*50:.0f} % - Abstandsschwankung der Hand)")
    # Bandmitte wandert laengs der Reihe stetig; was ausschert, wird im
    # Fenster der Nachbarn noch einmal gesucht.
    idx = np.arange(len(mi))
    gut = np.isfinite(mi)
    if gut.sum() >= 3:
        vorh = np.interp(idx, idx[gut], mi[gut])
        vorh = _glatt(vorh, min(7, (len(vorh) // 2) * 2 - 1)) if len(vorh) > 4 else vorh
        for i in range(len(mi)):
            if gut[i] and abs(mi[i] - vorh[i]) < 0.12 * erw:
                continue
            bb = bandsuche(stats[i][0], d_eng, vorh[i], 0.12 * erw)
            if bb:
                sag(f"  {alle[i].name}: Band im Fenster der Nachbarn nachgemessen")
                mi[i] = (bb[1] + bb[2]) / 2.0
                bw[i] = bb[2] - bb[1]

    B = []
    for i, q in enumerate(alle):
        if not np.isfinite(mi[i]):
            warn(f"{q.name}: kein Band gefunden, nicht verwendet"); continue
        st = stationen_messen(stats[i], bw[i], mi[i], HOEHE, fak)
        if st is None:
            sag(f"  {q.name}: Kantenpaar nicht durchgehend - uebersprungen")
            warn(f"{q.name}: Bauteil im Bild nicht durchgehend, nicht verwendet")
            continue
        st["pfad"] = q; st["name"] = q.name; st["stat"] = stats[i]
        B.append(st)
        sag(f"  {q.name}: Neigung {np.degrees(np.arctan(st['gerade'][1])):+.2f} Grad, "
            f"Rest {st['rest']:4.1f} Px, Balken im Bild "
            f"{st['y0']/fak/st['ymax']*100:3.0f}-{st['y1']/fak/st['ymax']*100:3.0f} % "
            f"({st['nst']}/{st['nges']} Stationen)")
    n = len(B)
    if n < 2:
        sag("Zu wenige brauchbare Aufnahmen."); return 1
    reste = np.array([b["rest"] for b in B])
    sag(f"  Rest der Kantengeraden: Median {np.median(reste):.1f} Px, "
        f"groesster {reste.max():.1f} Px")
    for b in B:
        if b["rest"] > max(8.0, 6 * np.median(reste)):
            warn(f"{b['name']}: Kantengerade sitzt schlecht ({b['rest']:.0f} Px)")
    verjuengung_abgleichen(B, L_V, HOEHE, fak)
    takt("Kanten gemessen")

    # --- 2: vorlaeufige Abbildung je Bild ---------------------------------
    for b in B:
        a1, b1, a2, b2 = b["gerade"]
        Y = float(L_V - 1)
        s = ((a2 - a1) + (b2 - b1) * Y / 2) / HOEHE
        U = Y / s
        b["H0"] = homographie([(0.0, 0.0), (0.0, HOEHE), (U, 0.0), (U, HOEHE)],
                              [(a1, 0.0), (a2, 0.0), (a1 + b1 * Y, Y), (a2 + b2 * Y, Y)])
        b["U"] = U
        b["pxmm"] = s

    # --- 3: Streifen und Zuordnung ----------------------------------------
    sag("")
    sag(f"Zuordnung ({SUCH:g} Px/mm)")
    # Die Suchstreifen bekommen einen FESTEN schmalen Rand, nicht den Saum
    # der Zeichnung.
    #
    # Beides war dasselbe, und damit veraenderte eine reine Darstellungs-
    # einstellung die Geometrie: Mit saum_mm 30 statt 5 sind die Streifen
    # 285 statt 235 mm hoch, und die zusaetzlichen 60 mm Pflaster und Bock
    # wandern wegen der Parallaxe anders als das Bauteil. Gemessen an der
    # Reihe 261022/Versuch 2 fiel der Nahtversatz dadurch von 0.21 auf
    # 0.61 mm und die belegte Laenge von 1568 auf 1364 mm - ohne dass an
    # der Reihe oder am Verfahren etwas anders war.
    SUCHSAUM = 5.0
    SH = int(round((HOEHE + 2 * SUCHSAUM) * SUCH))
    for b in B:
        im = lade(b["pfad"], 2, dreh, grau=True)
        sk = im.size[0] / W_V
        SW = max(16, int(round(b["U"] * SUCH)))
        A = np.array([[1 / SUCH, 0, 0], [0, 1 / SUCH, -SUCHSAUM], [0, 0, 1.0]])
        M = np.diag([sk, sk, 1.0]) @ b["H0"] @ A
        M = M / M[2, 2]
        b["st"] = np.asarray(im.transform((SW, SH), Image.PERSPECTIVE,
                                          tuple(M.flatten()[:8]), Image.BILINEAR),
                             np.float32)
        im.close()
        Hi = np.linalg.inv(b["H0"])
        xcm = (b["gerade"][0] + b["gerade"][2]) / 2
        uv = anwenden(Hi, [[xcm, b["y0"]], [xcm, b["y1"]]])
        b["lok"] = (float(uv[:, 0].min()), float(uv[:, 0].max()))
    takt("Streifen erzeugt")

    KACHEL = int(round(42 * SUCH))

    # verfahren_neu: zuerst im ROHBILD zuordnen (zuordnung_roh), ohne Kanten
    # und ohne Band. Die alte Fassung ordnete nur auf den Streifen zu, die
    # aus den Kantengeraden entzerrt sind; sitzt eine Kante falsch (Reihe C,
    # Pruefling pf-flau), sind die Streifen falsch und es bleiben nur falsche
    # Treffer. Die Paare werden in die Streifenkoordinaten umgerechnet, damit
    # alles Folgende unveraendert bleibt. Nur wo das Rohbild nichts liefert,
    # sucht der alte Weg auf den Streifen.
    grob = []
    for b in ([] if a.ohne_rohbild else B):
        with lade(b["pfad"], 8, dreh, grau=True) as im:
            grob.append(np.asarray(im, np.float32))
    fein_ablage = {}

    def fein(i):
        if i not in fein_ablage:
            if len(fein_ablage) >= 3:
                fein_ablage.pop(next(iter(fein_ablage)))
            with lade(B[i]["pfad"], 2, dreh, grau=True) as im:
                fein_ablage[i] = np.asarray(im, np.float32)
        return fein_ablage[i]

    def streifen_px(b, p):
        uv = anwenden(np.linalg.inv(b["H0"]), p)
        return np.c_[uv[:, 0] * SUCH, (uv[:, 1] + SUCHSAUM) * SUCH]

    def roh_paar(i, j, erwartet=None):
        a2, b2 = fein(i), fein(j)
        r = ZR.zuordnen(grob[i], grob[j], a2, b2, voll=W_V / a2.shape[1],
                        erwartet_px=erwartet)
        if r is None:
            return None
        pA, pB, info = r
        return streifen_px(B[i], pA), streifen_px(B[j], pB), info

    roh = []
    schr = {}
    bew = {}
    n_roh = 0
    erst = {i: None if a.ohne_rohbild else roh_paar(i, i + 1) for i in range(n - 1)}
    gut = [r[2]["bewegung_px"] for r in erst.values() if r is not None]
    M_BEW = float(np.median(gut)) if gut else None
    if M_BEW is not None:
        sag(f"  Rohbild: {len(gut)} von {n - 1} direkten Paaren, Bewegung des "
            f"Bauteils im Median {M_BEW:.0f} Px")
    for i in range(n - 1):
        r = erst[i]
        zusatz = ""
        if M_BEW is not None and (r is None or
                                  abs(r[2]["bewegung_px"] - M_BEW) > 0.45 * M_BEW):
            r2 = roh_paar(i, i + 1, erwartet=M_BEW)
            if r2 is not None:
                r, zusatz = r2, ", mit Vorgabe aus der Reihe"
            elif r is not None:
                sag(f"  {B[i]['name']} -> {B[i+1]['name']}: Rohbild-Ebene bewegt sich "
                    f"{r[2]['bewegung_px']:.0f} statt etwa {M_BEW:.0f} Px - verworfen")
                r = None
        if r is not None:
            pA, pB, info = r
            d = float(np.median(pB[:, 0] - pA[:, 0])) / SUCH
            schr[i] = d
            bew[i] = info["bewegung_px"]
            roh.append((i, i + 1, pA, pB, info["ncc"]))
            n_roh += 1
            sag(f"  {B[i]['name']} -> {B[i+1]['name']}: {len(pA):2d} Paare, "
                f"NCC {info['ncc']:.2f}, Versatz {d:+.0f} mm (Rohbild{zusatz})")
            continue
        bA = (B[i]["lok"][0] * SUCH, B[i]["lok"][1] * SUCH)
        r = paar_zuordnen(B[i]["st"], B[i + 1]["st"], bA, None, KACHEL, None, None)
        zusatz = " (Streifen)"
        if r is None:
            r = paar_zuordnen(B[i]["st"], B[i + 1]["st"], bA, None,
                              int(70 * SUCH), None, None, ncc_min=0.38)
            zusatz = " (Streifen, zweiter Anlauf)"
        if r is None:
            sag(f"  {B[i]['name']} -> {B[i+1]['name']}: kein direkter Treffer "
                f"- wird ueber die uebernaechsten Nachbarn gefuehrt")
            continue
        pA, pB, nc = r
        d = float(np.median(pB[:, 0] - pA[:, 0])) / SUCH
        schr[i] = d
        roh.append((i, i + 1, pA, pB, nc))
        sag(f"  {B[i]['name']} -> {B[i+1]['name']}: {len(pA):2d} Paare, "
            f"NCC {nc:.2f}, Versatz {d:+.0f} mm{zusatz}")
    if not schr:
        sag("Keine einzige Zuordnung gefunden."); return 1
    med_d = float(np.median([abs(v) for v in schr.values()]))
    vz0 = 1.0 if np.median(list(schr.values())) > 0 else -1.0

    # Dritter Anlauf fuer die Paare ohne Treffer: jetzt mit dem Schritt der
    # Nachbarn als Vorgabe. Die freie Suche ueber den ganzen Streifen ist auf
    # texturarmem Holz unsicher - die Maserung wiederholt sich, und RANSAC
    # verwirft dann auch richtige Kacheln. Mit Fenster faellt das weg.
    fehlend = [i for i in range(n - 1) if i not in schr]
    nach_vorgabe = 0
    for i in fehlend:
        bA = (B[i]["lok"][0] * SUCH, B[i]["lok"][1] * SUCH)
        for kw, nc, az in ((int(42 * SUCH), 0.38, 40), (int(90 * SUCH), 0.32, 40)):
            r = paar_zuordnen(B[i]["st"], B[i + 1]["st"], bA, None, kw,
                              vz0 * med_d * SUCH, int(0.45 * med_d * SUCH),
                              ncc_min=nc, anzahl=az)
            if r is not None:
                break
        if r is None:
            continue
        pA, pB, nc = r
        d = float(np.median(pB[:, 0] - pA[:, 0])) / SUCH
        if abs(abs(d) - med_d) > 0.45 * med_d:
            continue
        schr[i] = d
        roh.append((i, i + 1, pA, pB, nc))
        nach_vorgabe += 1
        sag(f"  {B[i]['name']} -> {B[i+1]['name']}: {len(pA):2d} Paare, "
            f"NCC {nc:.2f}, Versatz {d:+.0f} mm (mit Vorgabe aus den Nachbarn)")
    if fehlend:
        sag(f"  {nach_vorgabe} von {len(fehlend)} offenen Paaren mit Vorgabe "
            f"nachgeholt")
    med_d = float(np.median([abs(v) for v in schr.values()]))
    vz = 1.0 if np.median(list(schr.values())) > 0 else -1.0
    takt("direkte Nachbarn")

    # Vorlaeufige Lage jedes Bildes: Kette ueber die gefundenen Schritte,
    # Luecken mit dem Median ueberbrueckt. Nur eine VORHERSAGE fuer die
    # weiteren Suchen - gerechnet wird spaeter aus allen Paaren zugleich.
    pos = [0.0]
    for i in range(n - 1):
        pos.append(pos[-1] - schr.get(i, vz * med_d))
    pos = np.asarray(pos)
    feld = float(np.median([b["U"] for b in B]))

    # Weitere Nachbarn nach der tatsaechlichen Ueberlappung, nicht nach dem
    # Dateiabstand: faellt eine Aufnahme aus, ruecken die anderen zusammen.
    # verfahren_neu: Ueberlappung und Vorgabe aus der Bewegung im Rohbild
    # (unabhaengig von den Kanten), sonst wie bisher aus der Kette.
    versuch = 0
    n_vor = len(roh)
    for i in range(n):
        for j in range(i + 2, min(n, i + 5)):
            erw = (sum(bew.get(k, M_BEW) for k in range(i, j))
                   if M_BEW is not None else None)
            ueb = (1.0 - erw / L_V if erw is not None
                   else 1.0 - abs(pos[i] - pos[j]) / feld)
            if ueb < 0.18:
                continue
            versuch += 1
            r = roh_paar(i, j, erwartet=erw) if erw is not None else None
            if r is not None:
                roh.append((i, j, r[0], r[1], r[2]["ncc"]))
                n_roh += 1
                continue
            bA = (B[i]["lok"][0] * SUCH, B[i]["lok"][1] * SUCH)
            r = paar_zuordnen(B[i]["st"], B[j]["st"], bA, None, KACHEL,
                              (pos[i] - pos[j]) * SUCH, int(80 * SUCH))
            if r is not None:
                roh.append((i, j, r[0], r[1], r[2]))
    fein_ablage.clear()
    del grob
    sag(f"  Weitere Nachbarn mit genug Ueberlappung: {versuch} versucht, "
        f"{len(roh)-n_vor} verbunden")
    sag(f"  davon aus dem Rohbild: {n_roh} von {len(roh)} Bildpaaren")
    takt("weitere Nachbarn")
    sag(f"  {len(roh)} Bildpaare, {sum(len(r[2]) for r in roh)} Punktpaare")

    # Zusammenhang: die GROESSTE verbundene Gruppe zaehlt, nicht die um das
    # erste Bild. In der Reihe Seite C riss die Kette hinter dem dritten Bild;
    # mit der Gruppe um Bild eins waeren 27 von 30 Aufnahmen weggeworfen
    # worden, obwohl sie untereinander sauber verbunden sind.
    nach = {i: set() for i in range(n)}
    for i, j, *_ in roh:
        nach[i].add(j); nach[j].add(i)
    offen = set(range(n)); gruppen = []
    while offen:
        start = offen.pop()
        grp, rand = {start}, [start]
        while rand:
            k = rand.pop()
            for m in nach[k]:
                if m not in grp:
                    grp.add(m); rand.append(m); offen.discard(m)
        gruppen.append(grp)
    ges = max(gruppen, key=len)
    if len(ges) < n:
        fehlt = [B[i]["name"] for i in range(n) if i not in ges]
        sag(f"  ACHTUNG  ohne Verbindung zur Reihe: {', '.join(fehlt)}")
        warn(f"{len(fehlt)} Aufnahme(n) ohne Verbindung - zu wenig Ueberlappung "
             f"oder zu wenig Struktur")
        beh = sorted(ges); um = {o: k for k, o in enumerate(beh)}
        B = [B[i] for i in beh]
        roh = [(um[i], um[j], pA, pB, nc) for i, j, pA, pB, nc in roh
               if i in um and j in um]
        n = len(B)

    # --- 4: gemeinsamer Nullpunkt der Laengsachse -------------------------
    A, bb, w = [], [], []
    for (i, j, pA, pB, nc) in roh:
        z = np.zeros(n); z[i] = 1.0; z[j] = -1.0
        A.append(z); bb.append(float(np.median(pB[:, 0] - pA[:, 0])) / SUCH)
        w.append(len(pA) ** 0.5)
    z = np.zeros(n); z[0] = 1.0
    A.append(z); bb.append(0.0); w.append(20.0)
    A = np.asarray(A) * np.asarray(w)[:, None]
    bb = np.asarray(bb) * np.asarray(w)
    vers, *_ = np.linalg.lstsq(A, bb, rcond=None)
    paare = []
    for (i, j, pA, pB, nc) in roh:
        uvA = np.c_[pA[:, 0] / SUCH, pA[:, 1] / SUCH - SUCHSAUM]
        uvB = np.c_[pB[:, 0] / SUCH, pB[:, 1] / SUCH - SUCHSAUM]
        paare.append((i, j, anwenden(B[i]["H0"], uvA), anwenden(B[j]["H0"], uvB)))
    for i in range(n):
        T = np.array([[1.0, 0, -vers[i]], [0, 1.0, 0], [0, 0, 1.0]])
        B[i]["H0"] = B[i]["H0"] @ T
        B[i]["lok"] = (B[i]["lok"][0] + vers[i], B[i]["lok"][1] + vers[i])

    # --- 5: Ausgleichung ---------------------------------------------------
    sag("")
    sag("Ausgleichung  (je Bild Pose gegen die Bauteilebene, Brennweite global)")
    K = K_matrix(F_BR, cx, cy)
    posen = [H_zu_pose(b["H0"], K) for b in B]
    Rs = [rodrigues(rv) for rv, _ in posen]
    nk_ = [math.acos(min(1.0, abs(R[2, 2]))) for R in Rs]
    i0 = int(np.argmin(np.abs(np.asarray(nk_) - np.median(nk_))))
    basis = Rs[i0]
    qv = [rodrigues_inv(R @ basis.T) for R in Rs]
    mod = Modell([q[2] for q in qv], [q[0] for q in qv],
                 [tv for _, tv in posen],
                 float(np.median([q[1] for q in qv])),
                 basis, F_BR, cx, cy, F_BR)
    u_fix = anwenden(np.linalg.inv(B[0]["H0"]), [[cx, cy]])[0][0]


    d0 = float(np.median([mod.lot(mod.p, i) for i in range(n)]))
    frei = np.ones(len(mod.p), bool)
    frei[-1] = bool(a.brennweite_frei)
    sag(f"  Aufnahmeabstand zu Beginn: {d0:.0f} mm; Brennweite "
        f"{'frei' if a.brennweite_frei else 'fest'}")

    # Eichung und Fesseln stehen am ENDE des Residuenvektors. Sie duerfen von
    # der Ausreisserabwertung nicht erfasst werden: Beim ersten Versuch wurde
    # genau die Fessel abgewertet, die eine entgleiste Pose haette halten
    # sollen - ein Bild endete mit 60 Grad Verkippung und 129 mm Abstand.
    def enden():
        """Die beiden aeussersten Balkenenden als Bildpunkte."""
        _, Hi, _ = mod.entpacken()
        lage = []
        for i, b in enumerate(B):
            xcm = (b["gerade"][0] + b["gerade"][2]) / 2
            uv = anwenden(Hi[i], [[xcm, b["y0"]], [xcm, b["y1"]]])
            lage.append((i, xcm, float(uv[0, 0]), float(uv[1, 0])))
        ia = min(lage, key=lambda z: min(z[2], z[3]))
        ib = max(lage, key=lambda z: max(z[2], z[3]))
        qa = [ia[1], B[ia[0]]["y0"] if ia[2] < ia[3] else B[ia[0]]["y1"]]
        qb = [ib[1], B[ib[0]]["y1"] if ib[3] > ib[2] else B[ib[0]]["y0"]]
        return (qa, ia[0], qb, ib[0], LAENGE)

    def lauf(runden=28):
        kant = [(b["qs"], b["soll"]) for b in B]
        lg = enden()
        schwanz = 1 + 1 + 2 * n + 2 * n + 8 + 24
        fun = bauen_residuen(mod, kant, paare, HOEHE, 0.8, 0.35, u_fix, d0, lg)
        p, r = levenberg(fun, mod.p, runden=runden, frei=frei)
        for _ in range(2):
            rr = fun(p)
            sg = 1.4826 * np.median(np.abs(rr[:-schwanz])) + 1e-9
            g = np.minimum(1.0, 2.0 * sg / np.maximum(np.abs(rr), 1e-9)) ** 0.5
            g[-schwanz:] = 1.0
            p, _ = levenberg(bauen_residuen(mod, kant, paare, HOEHE, 0.8, 0.35,
                                            u_fix, d0, lg, gew=(g,)), p,
                             runden=max(8, runden // 2), frei=frei)
        return p, fun(p)

    def berichten(rest, tag):
        nk = sum(len(b["qs"]) for b in B)
        rk = np.abs(rest[:nk]) * 0.8
        rp = np.abs(rest[nk:-(2 + 4 * n + 8 + 24)]) * 0.35
        sag(f"  {tag}: Kanten {len(rk)} Stationen, Rest Median {np.median(rk):.2f} mm, "
            f"90 % unter {np.percentile(rk,90):.2f} mm")
        sag(f"  {' '*len(tag)}  Punktpaare {len(rp)//2}, Rest Median "
            f"{np.median(rp):.3f} mm, 90 % unter {np.percentile(rp,90):.3f} mm")

    mod.p, rest = lauf()
    berichten(rest, "1. Durchgang")
    takt("erste Ausgleichung")

    Hs, His, _ = mod.entpacken()

    # --- Zuordnung ein zweites Mal, jetzt im Modellrahmen -----------------
    #
    # Beim ersten Mal musste jedes Paar blind gesucht werden; eine schwache
    # Stelle lieferte dann fuenf Punktpaare, und die Naht sass um ueber einen
    # Zentimeter daneben. Jetzt ist die Lage auf wenige Millimeter bekannt:
    # Die Suche laeuft in einem engen Fenster, mit mehr Kacheln und milderer
    # Schwelle - und findet dort, wo es vorher kaum reichte, ein Vielfaches.
    sag("")
    sag("Zuordnung, zweiter Durchgang im Modellrahmen")
    for i, b in enumerate(B):
        xcm = (b["gerade"][0] + b["gerade"][2]) / 2
        uv = anwenden(His[i], [[xcm, b["y0"]], [xcm, b["y1"]]])
        b["u0"], b["u1"] = float(uv[:, 0].min()), float(uv[:, 0].max())
    for i, b in enumerate(B):
        im = lade(b["pfad"], 2, dreh, grau=True)
        sk = im.size[0] / W_V
        SW = max(16, int(round((b["u1"] - b["u0"]) * SUCH)))
        A = np.array([[1 / SUCH, 0, b["u0"]], [0, 1 / SUCH, -SUCHSAUM], [0, 0, 1.0]])
        M = np.diag([sk, sk, 1.0]) @ Hs[i] @ A
        b["st"] = np.asarray(im.transform((SW, SH), Image.PERSPECTIVE,
                                          tuple((M / M[2, 2]).flatten()[:8]),
                                          Image.BILINEAR), np.float32)
        im.close()
    FEN = 22.0
    alt = {(i, j): (qi, qj) for (i, j, qi, qj) in paare}
    paare2, gefunden, verworfen = [], 0, 0
    for i in range(n):
        for j in range(i + 1, min(n, i + 5)):
            o0 = max(B[i]["u0"], B[j]["u0"]); o1 = min(B[i]["u1"], B[j]["u1"])
            if o1 - o0 < 0.18 * (B[i]["u1"] - B[i]["u0"]):
                continue
            bA = ((o0 - B[i]["u0"]) * SUCH, (o1 - B[i]["u0"]) * SUCH)
            vorh = (B[i]["u0"] - B[j]["u0"]) * SUCH
            r = paar_zuordnen(B[i]["st"], B[j]["st"], bA, None, KACHEL,
                              vorh, int(FEN * SUCH), ncc_min=0.40, anzahl=44)
            if r is None:
                if (i, j) in alt:
                    paare2.append((i, j) + alt[(i, j)])
                continue
            pA, pB, nc = r
            # Rastet die Suche am Fensterrand ein, ist sie auf etwas
            # Falsches gelaufen - die Vorhersage war ja gerade das Mass.
            ab = (float(np.median(pB[:, 0] - pA[:, 0])) - vorh) / SUCH
            if abs(ab) > 0.75 * FEN:
                verworfen += 1
                if (i, j) in alt:
                    paare2.append((i, j) + alt[(i, j)])
                continue
            uvA = np.c_[pA[:, 0] / SUCH + B[i]["u0"], pA[:, 1] / SUCH - SUCHSAUM]
            uvB = np.c_[pB[:, 0] / SUCH + B[j]["u0"], pB[:, 1] / SUCH - SUCHSAUM]
            paare2.append((i, j, anwenden(Hs[i], uvA), anwenden(Hs[j], uvB)))
            gefunden += 1
    for b in B:
        b.pop("st", None)
    if gefunden >= 0.6 * len(paare):
        sag(f"  {gefunden} Bildpaare neu zugeordnet, {verworfen} verworfen "
            f"(Suche am Fensterrand); {sum(len(q[2]) for q in paare2)} "
            f"Punktpaare statt {sum(len(q[2]) for q in paare)}")
        paare[:] = paare2
    else:
        sag(f"  nur {gefunden} Paare wiedergefunden - der erste Durchgang bleibt")
    takt("Zuordnung im Modellrahmen")
    mod.p, rest = lauf(runden=16)
    berichten(rest, "3. Durchgang")
    # --- Aufnahmen mit grob abweichender Kante: Kante fallenlassen --------
    #
    # Eine Kantenmessung, die zehnmal schlechter sitzt als der Rest, misst
    # nicht die Bauteilkante - etwas steht davor, oder der Balken endet mitten
    # im Bild. Sie fliegt heraus; die Aufnahme haengt danach an ihren
    # Punktpaaren und an der gemeinsamen Haltung der Reihe.
    for _ in range(2):
        _, Hi_, _ = mod.entpacken()
        schl = []
        rr = []
        for i, b in enumerate(B):
            if not len(b["qs"]):
                rr.append(np.nan); continue
            uv = anwenden(Hi_[i], b["qs"])
            rr.append(float(np.median(np.abs(uv[:, 1] - b["soll"]))))
        rr = np.asarray(rr)
        mr = float(np.nanmedian(rr))
        schl = [i for i in range(n) if np.isfinite(rr[i])
                and rr[i] > max(4.0, 6.0 * mr)]
        if not schl:
            break
        for i in schl:
            sag(f"  {B[i]['name']}: Kante sitzt {rr[i]:.1f} mm daneben "
                f"(Reihe: {mr:.2f} mm) - Kantenmessung fallengelassen")
            warn(f"{B[i]['name']}: Kantenmessung verworfen - Querlage dort "
                 f"nur aus den Punktpaaren")
            B[i]["qs"] = np.zeros((0, 2)); B[i]["soll"] = np.zeros(0)
        mod.p, rest = lauf(runden=14)
        berichten(rest, "noch ein Durchgang")
    # Bleibt eine Aufnahme trotz allem bei einer unmoeglichen Verjuengung,
    # dann sind ihre Punktpaare irrefuehrend (am Bock, am Balkenende). Ihre
    # Verjuengung wird dann auf die der Reihe gesetzt und festgehalten.
    for _ in range(2):
        kx = mod.p[1:5 * n:5]
        mkx = float(np.median(kx))
        schl = [i for i in range(n)
                if frei[5 * i + 1] and abs(kx[i] - mkx) > math.radians(4.0)]
        if not schl:
            break
        for i in schl:
            sag(f"  {B[i]['name']}: Verjuengung {math.degrees(kx[i]):+.0f} Grad "
                f"unmoeglich - auf die Reihe gesetzt und festgehalten")
            warn(f"{B[i]['name']}: Verjuengung auf die Reihe gesetzt - "
                 f"Geometrie dort weniger sicher")
            mod.p[5 * i + 1] = mkx
            frei[5 * i + 1] = False
        mod.p, rest = lauf(runden=12)
        berichten(rest, "noch ein Durchgang")
    sag(f"  Verkippung quer, fuer die ganze Reihe: "
        f"{math.degrees(abs(mod.p[5*n])):.1f} Grad")
    kxg = np.degrees(mod.p[1:5*n:5])
    sag(f"  Verjuengung laengs je Bild: {kxg.min():+.1f} .. {kxg.max():+.1f} Grad")
    Hs, His, fbr = mod.entpacken()
    takt("letzte Ausgleichung")

    # --- 6: Lage und Ausdehnung im Modellrahmen ---------------------------
    # Laengsachse so legen, dass die erste Aufnahme links liegt und die Zahlen
    # der Skala in Aufnahmerichtung wachsen.
    u_erst = float(anwenden(His[0], [[cx, cy]])[0][0])
    u_letzt = float(anwenden(His[-1], [[cx, cy]])[0][0])
    if u_letzt < u_erst:
        Fl = np.array([[-1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]])
        Hs = [H @ Fl for H in Hs]
        His = [np.linalg.inv(H) for H in Hs]
        sag("  Laengsachse gespiegelt (Aufnahmerichtung)")
    # Balkenenden: wo in der AEUSSERSTEN Aufnahme das Kantenpaar aufhoert.
    enden_u = []
    for i, b in enumerate(B):
        xcm = (b["gerade"][0] + b["gerade"][2]) / 2
        uv = anwenden(His[i], [[xcm, b["y0"]], [xcm, b["y1"]]])
        enden_u.append((float(uv[:, 0].min()), float(uv[:, 0].max())))
    u_anf = min(z[0] for z in enden_u); u_end = max(z[1] for z in enden_u)
    # Abdeckung je Bild aus der GEOMETRIE, nicht aus den Kantenstationen.
    # Die Stationen fallen dort aus, wo eine Kante schlecht zu sehen ist -
    # am Bock, an einer Fehlstelle. Das Bauteil ist dort trotzdem im Bild.
    # Mit der Stationsgrenze als Revier blieben Luecken von ueber 500 mm.
    for i, b in enumerate(B):
        xcm = (b["gerade"][0] + b["gerade"][2]) / 2
        uv = anwenden(His[i], [[xcm, 0.0], [xcm, float(L_V - 1)]])
        b["u0"] = max(float(uv[:, 0].min()), u_anf)
        b["u1"] = min(float(uv[:, 0].max()), u_end)
        b["uc"] = float(anwenden(His[i], [[cx, cy]])[0][0])
        b["neig"] = mod.neigung(mod.p, i)
        b["abst"] = mod.lot(mod.p, i)
    rang = sorted(range(n), key=lambda i: B[i]["uc"])
    sag("")
    sag("Lage der Aufnahmen im Bauteilrahmen")
    for k, i in enumerate(rang):
        b = B[i]
        sag(f"  {b['name']}: {b['u0']:7.0f} .. {b['u1']:7.0f} mm "
            f"({b['u1']-b['u0']:5.0f} mm), Mitte {b['uc']:7.0f}, "
            f"Abstand {b['abst']:4.0f} mm, {b['neig']:4.1f} Grad")
    schr = np.diff([B[i]["uc"] for i in rang])
    sag("")
    sag(f"Vorschub: Median {np.median(schr):.0f} mm, Spanne "
        f"{schr.min():.0f}..{schr.max():.0f} mm")
    sag(f"Aufnahmeabstand: Median {np.median([b['abst'] for b in B]):.0f} mm, "
        f"Spanne {min(b['abst'] for b in B):.0f}..{max(b['abst'] for b in B):.0f} mm "
        f"({(max(b['abst'] for b in B)/min(b['abst'] for b in B)-1)*100:.0f} % - "
        f"Schwankung der Hand)")
    sag(f"Verkippung gegen die Bauteilebene: Median "
        f"{np.median([b['neig'] for b in B]):.1f} Grad, groesste "
        f"{max(b['neig'] for b in B):.1f} Grad")
    for i in rang:
        if B[i]["neig"] > 32.0:
            warn(f"{B[i]['name']}: {B[i]['neig']:.0f} Grad schraeg aufgenommen")
    U0 = min(b["u0"] for b in B) - SAUM
    U1 = max(b["u1"] for b in B) + SAUM
    sag(f"Belegt: {U0:.0f} .. {U1:.0f} mm ({U1-U0:.0f} mm)")

    # --- 7: Photometrie ----------------------------------------------------
    sag("")
    if a.ohne_photometrie:
        G = np.ones((n, 3)); kv = np.zeros(2)
        sag("Photometrie uebersprungen (--ohne-photometrie)")
    else:
        sag("Photometrie")
        rmax = math.hypot(cx, cy)
        proben = []
        for (i, j, qi, qj) in sorted(paare, key=lambda t: t[0]):
            o0 = max(B[i]["u0"], B[j]["u0"]); o1 = min(B[i]["u1"], B[j]["u1"])
            if o1 - o0 < 30:
                continue
            uu, vv = np.meshgrid(np.linspace(o0, o1, 26),
                                 np.linspace(0.12 * HOEHE, 0.88 * HOEHE, 9))
            pts = np.c_[uu.ravel(), vv.ravel()]
            ai = cache.hole(B[i]["pfad"], 4); aj = cache.hole(B[j]["pfad"], 4)
            sk = ai.shape[1] / W_V
            pi = anwenden(Hs[i], pts) * sk; pj = anwenden(Hs[j], pts) * sk
            ok = ((pi[:, 0] > 4) & (pi[:, 0] < ai.shape[1] - 5) &
                  (pi[:, 1] > 4) & (pi[:, 1] < ai.shape[0] - 5) &
                  (pj[:, 0] > 4) & (pj[:, 0] < aj.shape[1] - 5) &
                  (pj[:, 1] > 4) & (pj[:, 1] < aj.shape[0] - 5))
            if ok.sum() < 20:
                continue
            pi, pj = pi[ok], pj[ok]
            vi = np.array([ai[int(y) - 2:int(y) + 3, int(x) - 2:int(x) + 3].mean(axis=(0, 1))
                           for x, y in pi])
            vj = np.array([aj[int(y) - 2:int(y) + 3, int(x) - 2:int(x) + 3].mean(axis=(0, 1))
                           for x, y in pj])
            m = (vi.min(axis=1) > 6) & (vj.min(axis=1) > 6) & \
                (vi.max(axis=1) < 250) & (vj.max(axis=1) < 250)
            if m.sum() < 20:
                continue
            ni = np.c_[(pi[m, 0] / sk - cx) / rmax, (pi[m, 1] / sk - cy) / rmax]
            nj = np.c_[(pj[m, 0] / sk - cx) / rmax, (pj[m, 1] / sk - cy) / rmax]
            proben.append((i, j, np.log(vi[m]), np.log(vj[m]), ni, nj))
        G, kv = photometrie(proben, n)
        sag(f"  {len(proben)} Bildpaare beprobt")
        h = G.mean(axis=1)
        sag(f"  Helligkeitsfaktoren: {h.min():.3f} .. {h.max():.3f} "
            f"(Spanne {(h.max()/h.min()-1)*100:.0f} %)")
        rg = G[:, 0] / G[:, 1]; bg = G[:, 2] / G[:, 1]
        sag(f"  Weissabgleich der Kamera lief um R/G {(rg.max()/rg.min()-1)*100:.0f} %, "
            f"B/G {(bg.max()/bg.min()-1)*100:.0f} % - wird herausgerechnet")
        if max(rg.max() / rg.min(), bg.max() / bg.min()) > 1.06:
            warn("Weissabgleich der Kamera war nicht fest - die Farbe des "
                 "Streifens ist das Mittel der Reihe, nicht die wahre Farbe. "
                 "In ProCamera Kelvin fest einstellen.")
        ec = lichtfeld_basis(np.array([-0.7, 0.7, -0.7, 0.7]),
                             np.array([-0.7, -0.7, 0.7, 0.7])) @ kv
        sag(f"  Lichtfeld ueber dem Bild: {(math.exp(ec.min())-1)*100:+.1f} % bis "
            f"{(math.exp(ec.max())-1)*100:+.1f} % gegen die Bildmitte")
        if math.exp(ec.max() - ec.min()) > 1.5:
            warn("Das Licht ueber dem Bildfeld schwankt um mehr als 50 % - "
                 "steht der Fotograf im eigenen Licht?")
    takt("Photometrie")

    # --- 8: Naehte waehlen -------------------------------------------------
    sag("")
    sag("Naehte")
    for i, b in enumerate(B):
        im = lade(b["pfad"], 2, dreh, grau=True)
        sk = im.size[0] / W_V
        SW = max(16, int(round((b["u1"] - b["u0"]) * SUCH)))
        A = np.array([[1 / SUCH, 0, b["u0"]], [0, 1 / SUCH, -SUCHSAUM], [0, 0, 1.0]])
        M = np.diag([sk, sk, 1.0]) @ Hs[i] @ A
        M = M / M[2, 2]
        b["g"] = np.asarray(im.transform((SW, SH), Image.PERSPECTIVE,
                                         tuple(M.flatten()[:8]), Image.BILINEAR),
                            np.float32) / max(G[i].mean(), 1e-6)
        im.close()
    schnitte = []
    for k in range(len(rang) - 1):
        i, j = rang[k], rang[k + 1]
        o0 = max(B[i]["u0"], B[j]["u0"]); o1 = min(B[i]["u1"], B[j]["u1"])
        if o1 - o0 < 4 * FEDER:
            schnitte.append((B[i]["u1"] + B[j]["u0"]) / 2.0)
            continue
        ua = o0 + FEDER; ub = o1 - FEDER
        xs = np.arange(int(ua * SUCH), int(ub * SUCH))
        xi = xs - int(B[i]["u0"] * SUCH); xj = xs - int(B[j]["u0"] * SUCH)
        ok = ((xi >= 0) & (xi < B[i]["g"].shape[1]) &
              (xj >= 0) & (xj < B[j]["g"].shape[1]))
        if ok.sum() < 8:
            schnitte.append((ua + ub) / 2.0); continue
        xs, xi, xj = xs[ok], xi[ok], xj[ok]
        ai = B[i]["g"][:, xi]
        aj = B[j]["g"][:, xj]
        q0 = int(SAUM * SUCH) + 4; q1 = SH - int(SAUM * SUCH) - 4
        d = np.abs(ai[q0:q1] - aj[q0:q1]).mean(axis=0)
        kb = max(3, int(8 * SUCH)) | 1
        d = np.convolve(np.pad(d, kb // 2, mode="edge"), np.ones(kb) / kb, "valid")[:len(xs)]
        mitte = (ua + ub) / 2
        d = d + 0.0025 * d.mean() * np.abs(xs / SUCH - mitte)
        schnitte.append(float(xs[int(np.argmin(d))]) / SUCH)
    for b in B:
        b.pop("g", None); b.pop("st", None)
    sag(f"  {len(schnitte)} Naehte, Abstand Median "
        f"{np.median(np.diff(schnitte)) if len(schnitte)>1 else 0:.0f} mm")
    takt("Naehte gewaehlt")

    # --- Zwischenspeicher --------------------------------------------------
    Z = dict(Hs=Hs, His=His, G=G, kv=kv, schnitte=schnitte, rang=rang,
             dreh=dreh, U0=U0, U1=U1, cx=cx, cy=cy, W_V=W_V, L_V=L_V,
             bilder=[dict(pfad=b["pfad"], name=b["name"], u0=b["u0"], u1=b["u1"],
                          uc=b["uc"], pxmm=b["pxmm"]) for b in B],
             meldungen=list(MELDUNGEN), warnungen=list(WARNUNGEN))
    ziel.parent.mkdir(parents=True, exist_ok=True)
    with open(ziel.with_suffix(".modell.pkl"), "wb") as fh:
        pickle.dump(Z, fh)
    sag(f"Zwischenspeicher: {ziel.with_suffix('.modell.pkl').name} "
        f"(mit --weiter laesst sich ohne Neurechnung anders zeichnen)")
    if a.nur_geometrie:
        ziel.with_suffix(".txt").write_text("\n".join(MELDUNGEN) + "\n",
                                            encoding="utf-8")
        return 0
    return zeichnen(a, daten, Z, HOEHE, LAENGE, PXMM, SAUM, SP, ZH, ziel)


def zeichnen(a, daten, Z, HOEHE, LAENGE, PXMM, SAUM, SP, ZH, ziel):
    """Schritt 9 bis 11: einmal entzerren, Laengenprobe, Pruefzahlen."""
    Hs = Z["Hs"]; His = Z["His"]; G = Z["G"]; kv = Z["kv"]
    schnitte = Z["schnitte"]; rang = Z["rang"]; dreh = Z["dreh"]
    U0 = Z["U0"]; U1 = Z["U1"]; cx = Z["cx"]; cy = Z["cy"]; W_V = Z["W_V"]
    B = Z["bilder"]
    FEDER = 24.0
    sag("")

    # --- 9: Balkenenden finden, Laengsmassstab darauf setzen ---------------
    #
    # Erst ein grober Streifen in Grau, nur um zu sehen, WO der Balken anfaengt
    # und aufhoert. Daran wird dann der Laengsmassstab gesetzt - und zwar als
    # Wahl des einen freien Freiheitsgrades, nicht als nachtraegliches
    # Stauchen des fertigen Bildes. Beides sieht aehnlich aus und ist
    # grundverschieden: Hier aendert sich nur, welcher Millimeter welcher ist;
    # die Lage der Bildpunkte zueinander bleibt unberuehrt, und abgetastet
    # wird weiterhin genau einmal.
    vs = vorschau(B, Hs, rang, schnitte, U0, U1, dreh, W_V, SAUM, HOEHE, 2.0)
    en = balkenenden(vs, 2.0, SAUM, HOEHE)
    if en is None:
        sag("Balkenenden nicht gefunden - es wird die belegte Flaeche genommen")
        warn("Balkenenden nicht gefunden - Laengsmassstab unsicher")
        ua_b, ub_b = min(b["u0"] for b in B), max(b["u1"] for b in B)
    else:
        ua_b, ub_b = U0 + en[0], U0 + en[1]
        sag(f"Balkenenden ueber die Faserrichtung gefunden "
            f"(Holz {en[2]:.1f}-fach quergerichtet)")
    ist = ub_b - ua_b
    sag(f"Balken im Streifen: {ist:.0f} mm, Aufmass {LAENGE:g} mm "
        f"-> {ist-LAENGE:+.0f} mm = {(ist/LAENGE-1)*100:+.2f} %")
    skal = 1.0
    if getattr(a, "ohne_einpassung", False):
        sag("  --ohne-einpassung: rohe Geometrie, Skala auf das gemessene Mass")
    elif abs(ist / LAENGE - 1) > 0.15:
        sag("  ACHTUNG  zu grosse Abweichung - es wird NICHT eingepasst")
        warn(f"Laenge weicht {(ist/LAENGE-1)*100:+.0f} % ab - nicht eingepasst")
    else:
        skal = LAENGE / ist
        sag(f"  Laengsmassstab auf das Aufmass gesetzt (Faktor {skal:.4f}).")
        sag("  Quer ist die Flaechenhoehe das Mass, laengs die Gesamtlaenge -")
        sag("  beide gemessen am Bauteil. Eine unabhaengige Laengsprobe gibt")
        sag("  diese Reihe nicht her; dafuer braeuchte es zwei eingemessene")
        sag("  Marken im Bild.")
    if abs(ist / LAENGE - 1) > 0.02:
        warn(f"rohe Laenge wich {(ist/LAENGE-1)*100:+.1f} % vom Aufmass ab")
    L_AUS = LAENGE if skal != 1.0 else ist

    # --- 10: Zeichnen ------------------------------------------------------
    # Nullpunkt der Ausgabe liegt AM BAUTEIL: Leinwandspalte SAUM*PXMM ist der
    # Balkenanfang, Zeile SAUM*PXMM die Oberkante.
    W_out = int(round((L_AUS + 2 * SAUM) * PXMM))
    sag("")
    sag(f"Leinwand {W_out} x {ZH} Px = {W_out/PXMM:.0f} x {ZH/PXMM:.0f} mm "
        f"(Balkenfeld {L_AUS:.0f} x {HOEHE:g} mm)")

    def nach_spalte(u):
        return ((u - ua_b) * skal + SAUM) * PXMM

    def nach_u(x):
        return ua_b + (x / PXMM - SAUM) / skal

    leinwand = np.full((ZH, W_out, 3), 255, np.uint8)
    belegt = np.zeros(W_out, bool)
    rmax = math.hypot(cx, cy)
    red = max(1, int(np.median([b["pxmm"] for b in B]) / PXMM))
    if red > 1:
        sag(f"  Vorfilter: Originale um {red}x kastengemittelt "
            f"(gegen Treppen beim Verkleinern)")
    for k, i in enumerate(rang):
        b = B[i]
        ua = nach_u(0.0) if k == 0 else schnitte[k - 1] - FEDER / 2
        ub = nach_u(W_out) if k == len(rang) - 1 else schnitte[k] + FEDER / 2
        X0 = max(0, int(math.floor(nach_spalte(ua))))
        X1 = min(W_out, int(math.ceil(nach_spalte(ub))))
        tw = X1 - X0
        if tw < 2:
            continue
        im = lade(b["pfad"], 1, dreh)
        if red > 1:
            im = im.reduce(red)
        sk = im.size[0] / W_V
        A = np.array([[1 / (PXMM * skal), 0,
                       X0 / (PXMM * skal) + ua_b - SAUM / skal],
                      [0, 1 / PXMM, -SAUM], [0, 0, 1.0]])
        M = np.diag([sk, sk, 1.0]) @ Hs[i] @ A
        M = M / M[2, 2]
        kach = np.asarray(im.transform((tw, ZH), Image.PERSPECTIVE,
                                       tuple(M.flatten()[:8]), Image.BICUBIC),
                          np.float32)
        im.close()
        if not a.ohne_photometrie:
            gx = np.arange(0, tw, 16); gy = np.arange(0, ZH, 16)
            GX, GY = np.meshgrid(gx, gy)
            src = anwenden(M, np.c_[GX.ravel(), GY.ravel()]) / max(sk, 1e-9)
            xi = (src[:, 0] - cx) / rmax; eta = (src[:, 1] - cy) / rmax
            V = np.exp(np.clip(lichtfeld_basis(xi, eta) @ kv, -0.30, 0.30))
            V = np.asarray(Image.fromarray(V.reshape(GY.shape).astype(np.float32),
                                           mode="F").resize((tw, ZH),
                                                            Image.BILINEAR),
                           np.float32)
            kach = kach / (G[i][None, None, :] * V[:, :, None])
        np.clip(kach, 0, 255, out=kach)
        al = np.ones(tw, np.float32)
        if k > 0 and a.naht == "weich":
            fw = min(tw, max(1, int(round(FEDER * PXMM * skal))))
            al[:fw] = np.linspace(0.0, 1.0, fw)
        alt = leinwand[:, X0:X1].astype(np.float32)
        leinwand[:, X0:X1] = np.clip(
            alt * (1 - al)[None, :, None] + kach * al[None, :, None],
            0, 255).astype(np.uint8)
        belegt[X0:X1] = True
        print(f"    {k+1:3d}/{len(rang)}  {b['name']}  "
              f"{(ua-ua_b)*skal:7.0f} - {(ub-ua_b)*skal:7.0f} mm", flush=True)
    sag(f"Flaeche belegt: {belegt.mean()*100:.1f} % der Laenge")
    if belegt.mean() < 0.995:
        warn(f"nur {belegt.mean()*100:.1f} % der Laenge belegt")
    takt("gezeichnet")
    kern_b = Image.fromarray(leinwand)
    del leinwand

    # --- 11: Pruefzahlen ---------------------------------------------------
    sag("")
    sag("Pruefzahlen")
    UEB = 2.0
    klein = kern_b.resize((max(1, int(kern_b.width * UEB / PXMM)),
                           max(1, int(kern_b.height * UEB / PXMM))), Image.LANCZOS)
    npx = [int(round(nach_spalte(sx))) for sx in Z["schnitte"]]
    npx = [q for q in npx if 3 * SP < q < kern_b.width - 3 * SP]
    if npx:
        nv = nahtversatz(kern_b, PXMM, SP, npx)
        sag(f"  Querversatz an den {len(nv)} Naehten: Median "
            f"{np.median(np.abs(nv)):.2f} mm, groesster {np.abs(nv).max():.2f} mm")
        for q, w in zip(npx, nv):
            if abs(w) > 1.0:
                sag(f"    bei {q/PXMM:.0f} mm: {w:+.2f} mm")
                warn(f"Querversatz {w:+.1f} mm an der Naht bei {q/PXMM:.0f} mm")
    kl = kantenlauf(kern_b, PXMM, SP)
    if kl:
        sag(f"  Bauteilkante im Streifen: Streuung {kl[0]:.2f} mm, langwellige "
            f"Abweichung {kl[1]:.2f} mm (auf {kl[2]*100:.0f} % der Laenge gefunden)")
        sag("    (die kurzwellige Streuung ist das Bauteil - Ausbrueche, "
            "Saegespuren; die langwellige ist das Verfahren)")
        if kl[1] > 4.0:
            warn(f"Bauteilkante wandert langwellig um {kl[1]:.1f} mm")
    nz, nmax = nahtmass(klein, UEB)
    sag(f"  Nahtsichtbarkeit: {nz} Spalten mit senkrechter Kante, "
        f"staerkste {nmax:.0f}-fach ueber dem Grundwert")
    if nz > 15:
        warn(f"{nz} sichtbare Nahtkanten")
    sag(f"  Helligkeitswelligkeit laengs: {welligkeit(kern_b, PXMM, SP):.1f} % "
        f"(Streuung um den Verlauf ueber 600 mm)")

    fertig = kern_b if a.ohne_massstab else beschriften(
        kern_b, daten, L_AUS, HOEHE, PXMM, SP)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    fertig.save(ziel, quality=92)
    zweit = ziel.with_name(ziel.stem + "_uebersicht" + ziel.suffix)
    (fertig.resize((max(1, int(fertig.width * UEB / PXMM)),
                    max(1, int(fertig.height * UEB / PXMM))), Image.LANCZOS)
     .save(zweit, quality=88))

    sag("")
    sag("Pruefbericht")
    sag("------------")
    if WARNUNGEN:
        sag(f"  {len(WARNUNGEN)} Punkt(e):")
        for w in WARNUNGEN:
            sag(f"    - {w}")
    else:
        sag("  Keine Beanstandung.")
    sag("")
    sag(f"Ergebnis:   {fertig.width} x {fertig.height} Px, Balkenfeld "
        f"{L_AUS:.0f} x {HOEHE:g} mm bei {PXMM:g} Px/mm")
    sag(f"Geschrieben: {ziel}")
    sag(f"Uebersicht:  {zweit}")
    sag(f"Rechenzeit:  {time.time()-T0:.0f} s")
    ziel.with_suffix(".txt").write_text("\n".join(MELDUNGEN) + "\n", encoding="utf-8")
    return 1 if WARNUNGEN else 0


if __name__ == "__main__":
    import faulthandler, traceback
    faulthandler.enable()
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        traceback.print_exc()
        sys.exit(3)
