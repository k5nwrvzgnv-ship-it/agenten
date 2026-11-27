"""Körper eines Balkens aus seinen vier Seiten (Plan: docs/ideen-galerie-3d-und-aufteilung.md).

Je Foto: Holz vom dunklen Grund trennen, Fläche gerade drehen, quer auf ihre Kanten schneiden. Je Seite: Fotos
nach ihrer Lage längs (mitte_mm) überblendet aneinanderlegen und auf die eingetragenen Maße bringen. Gemessene
Maße stehen daneben in koerper.json, damit Abweichungen sichtbar bleiben.

Lage der Seiten: Der Balken wird um seine Längsachse gerollt, das Handy bleibt. Dann stößt die nächste Seite an
die obere Bildkante (an B002 an den Zapfen des Bodens geprüft). Die vier Bilder übereinander ergeben so den
abgewickelten Mantel, ohne Spiegeln.

Nur numpy und Pillow, läuft in der Trainings-.venv am Mac und in der .venv auf dem Server:
  python koerper.py <Balkenordner>      schreibt <Balkenordner>/koerper/ (S1.jpg bis S4.jpg, klein S1_k.jpg, koerper.json)
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

try:
    from . import auswahl as au
except ImportError:                     # als Skript gestartet (python koerper.py <Ordner>)
    import auswahl as au

SUCHE_PX = 1200          # lange Bildseite für die Kantensuche
ZIEL_PX_JE_MM = 4.0      # Auflösung der fertigen Seitenbilder
MERK_PX_JE_MM = 6.0      # so fein bleiben die geraden Fotos einer Seite bis zum Zusammensetzen im Speicher
MAX_BREITE_PX = 8000     # längs höchstens so viele Pixel (lange Balken bekommen weniger px/mm)
KACHEL_MM = 1000         # 3D-Ansicht: Seite in Stücke von etwa so viel mm ...
KACHEL_PX_JE_MM = 6.0    # ... in dieser Auflösung (Fotos haben 9 bis 15, gemerkt werden höchstens MERK_PX_JE_MM)
KLEIN_PX = 480           # Breite der kleinen Seitenbilder für die Galerie
AUSREISSER_GRAD = 4.0    # so viel anders als der Median der Seite: Foto bekommt den Winkel der übrigen
MAX_WINKEL = 25.0        # schiefer liegt der Balken nicht längs im Bild: Seite unbrauchbar (B004: bis 20° beim Schieben, wird gerade gedreht)
MAX_ABWEICHUNG = 15.0    # Prozent gegen die eingetragenen Maße, darüber stimmt Lage oder Maßstab nicht
LEER_ANTEIL = 0.15       # weniger Holz in der Bildbreite: Foto ist leer (Serie schon durch) und zählt nicht
HOLZ_HELL = 100          # gefundene Fläche ist nur Grund, wenn sie dunkler ist als das (Helligkeit 0-255) ...
HOLZ_ROT = 40            # ... und weniger rot (Rot minus Blau). Holz 175-204 hell (B002), vergraut 145 (B004 S4),
                         # Grund 20-90 und bläulich (Rot minus Blau unter 0)
RAND = 0.01              # Fläche gilt als am Bildrand abgeschnitten, wenn sie näher als 1 % am Rand liegt
VERSATZ_PX_JE_MM = 2.0   # Serie: Auflösung des Profils längs und quer
VERSATZ_MIN_MM = 25      # Serie: so viel müssen zwei Fotos mindestens überlappen (B007: 191 mm Bildfeld, Schritte bis 130 mm)
VERSATZ_GUETE = 0.25     # Serie: darunter gilt ein Versatz als unsicher (normierte Korrelation)
VERSATZ_RUHE_MM = 25     # Serie: so kurze Schritte (fast Stillstand) ...
VERSATZ_RUHE_GUETE = 0.6  # ... zählen nur, wenn die beiden Fotos so gut zusammenpassen (echte: 0,7 bis 1,0)
VERSATZ_RAND_MM = 12     # Serie: so viel am Bildrand nicht vergleichen (helle Flecken vom Licht der Box, B007)
VERSATZ_RUECK_MM = 5     # Serie: so weit darf das Holz gegen die Schieberichtung zurückrutschen
VERSATZ_GLATT = 1e-4     # Serie: Strafe je mm² Unterschied zum vorigen Schritt (Güte-Einheiten) ...
VERSATZ_GLATT_MAX = 0.15  # ... höchstens so viel, ein echter Ruck bleibt möglich
VERSATZ_ZWEI = 0.5       # Serie: Gewicht der Güte über zwei Fotos (Weg i bis i+2)


def otsu(werte: np.ndarray) -> tuple[float, float]:
    """Schwelle, die zwei Gruppen von Werten am besten trennt (Otsu), und wie gut sie trennt (0 bis 1: Anteil der
    Streuung, der zwischen den Gruppen liegt)."""
    werte = werte.ravel().astype(np.float64)
    haeufig, raender = np.histogram(werte, bins=256)
    mitten = (raender[:-1] + raender[1:]) / 2
    w0 = np.cumsum(haeufig)
    w1 = w0[-1] - w0
    s0 = np.cumsum(haeufig * mitten)
    m0 = s0 / np.maximum(w0, 1)
    m1 = (s0[-1] - s0) / np.maximum(w1, 1)
    zwischen = w0 * w1 * (m0 - m1) ** 2
    i = int(np.argmax(zwischen))
    gesamt = float(werte.var()) * len(werte) ** 2
    return float(mitten[i]), float(zwischen[i]) / gesamt if gesamt > 0 else 0.0


def schwelle_otsu(werte: np.ndarray) -> float:
    """Schwelle, die zwei Gruppen von Werten am besten trennt (Otsu)."""
    return otsu(werte)[0]


def holzmaske(rgb: np.ndarray, gueltig: np.ndarray | None = None) -> np.ndarray:
    """True, wo Holz ist. Frisches Holz ist rot-gelblich, der Grund schwarz bis bläulich grau: Rot minus Blau trennt
    beides. Altes, vergrautes Holz (B004 Seite 4) ist kaum röter als der Grund, aber deutlich heller. Genommen wird
    das Merkmal, das Holz und Grund am klarsten trennt; Holz ist stets die hellere bzw. rötere Gruppe.
    gueltig: False für Pixel, die nicht zum Foto gehören (Füllung beim Drehen), die sind nie Holz."""
    r, g, b = (rgb[..., i].astype(np.float32) for i in range(3))
    hell = 0.299 * r + 0.587 * g + 0.114 * b
    bestes = None
    for m in (r - b, hell, (r - b) + 0.5 * hell):
        schwelle, trennung = otsu(m[gueltig] if gueltig is not None else m)
        if bestes is None or trennung > bestes[0] + 0.02:       # bei Gleichstand bleibt Rot minus Blau
            bestes = (trennung, m > schwelle)
    return bestes[1] & gueltig if gueltig is not None else bestes[1]


def laengster_lauf(an: np.ndarray) -> tuple[int, int]:
    """Anfang und Ende (einschließlich) des längsten zusammenhängenden True-Stücks."""
    bester, start, beste = (0, -1), None, -1
    for i, x in enumerate(list(an) + [False]):
        if x and start is None:
            start = i
        elif not x and start is not None:
            if i - start > beste:
                bester, beste = (start, i - 1), i - start
            start = None
    if beste < 0:
        raise ValueError("kein Holz im Bild gefunden")
    return bester


def ausgleichsgerade(x: np.ndarray, y: np.ndarray) -> float:
    """Steigung einer Geraden durch die Punkte, Ausreißer (Zapfen, Ecken) werden einmal verworfen."""
    a, b = np.polyfit(x, y, 1)
    rest = y - (a * x + b)
    mad = np.median(np.abs(rest - np.median(rest))) or 1.0
    gut = np.abs(rest) <= 3 * 1.4826 * mad
    if gut.sum() >= 2:
        a, b = np.polyfit(x[gut], y[gut], 1)
    return float(a)


def kanten(maske: np.ndarray) -> dict:
    """Kanten der Fläche in einer Maske (Pixel der Maske) und ihre Neigung in Grad (positiv = im Uhrzeigersinn)."""
    anteil = maske.mean(axis=0)
    links, rechts = laengster_lauf(anteil > 0.5 * anteil.max())
    breite = rechts - links + 1
    innen = np.arange(links + breite // 10, rechts - breite // 10 + 1)
    hat = maske[:, innen].any(axis=0)
    innen = innen[hat]
    if len(innen) < 2:
        raise ValueError("Fläche zu schmal für die Kantensuche")
    spalten = maske[:, innen]
    oben = spalten.argmax(axis=0).astype(np.float64)
    unten = (maske.shape[0] - 1 - spalten[::-1].argmax(axis=0)).astype(np.float64)
    neigung = (ausgleichsgerade(innen, oben) + ausgleichsgerade(innen, unten)) / 2
    return {"links": float(links), "rechts": float(rechts + 1), "oben": float(np.median(oben)),
            "unten": float(np.median(unten) + 1), "winkel": math.degrees(math.atan(neigung)),
            "rand_links": links <= RAND * maske.shape[1], "rand_rechts": rechts + 1 >= (1 - RAND) * maske.shape[1]}


def flaeche_finden(bild: Image.Image, fest: float | None = None) -> tuple[Image.Image, dict]:
    """Dreht das Bild so, dass die Fläche waagerecht liegt, und gibt ihre Kanten in Pixeln des gedrehten Bildes.
    fest: Winkel vorgegeben (Ausreißer einer Seite bekommen den der übrigen Fotos)."""
    faktor = max(bild.size) / SUCHE_PX
    klein_groesse = (round(bild.width / faktor), round(bild.height / faktor))
    erste = kanten(holzmaske(np.asarray(bild.resize(klein_groesse, Image.Resampling.BILINEAR))))
    ausreisser = fest is not None or abs(erste["winkel"]) > MAX_WINKEL
    drehen = fest if fest is not None else 0.0 if ausreisser else erste["winkel"]
    gerade = bild.rotate(drehen, resample=Image.Resampling.BICUBIC, fillcolor=(0, 0, 0)) if drehen else bild
    # Die schwarzen Ecken der Drehung sind kein Grund und kein Holz: Schwarz hat Rot minus Blau 0 und lag damit über
    # dem bläulichen Grund (B004 Seite 2: aus -1,2° wurden -19°). Sie zählen nicht mit.
    gueltig = None
    if drehen:
        gueltig = np.asarray(Image.new("L", klein_groesse, 255).rotate(drehen, resample=Image.Resampling.NEAREST)) > 0
    k = kanten(holzmaske(np.asarray(gerade.resize(klein_groesse, Image.Resampling.BILINEAR)), gueltig))
    sx, sy = bild.width / klein_groesse[0], bild.height / klein_groesse[1]
    k.update(links=k["links"] * sx, rechts=k["rechts"] * sx, oben=k["oben"] * sy, unten=k["unten"] * sy,
             winkel=drehen + (0.0 if ausreisser else k["winkel"]), ausreisser=ausreisser)
    return gerade, k


def profil(s: dict, hoehe_mm: float) -> tuple[np.ndarray, int, int]:
    """Gerades Foto als Grauwert-Profil über die ganze Bildbreite, VERSATZ_PX_JE_MM Spalten je mm längs und Zeilen
    je mm quer, über hoehe_mm um die Mitte der Holzfläche. Feste mm statt Anteil der gemessenen Breite: Die Breite
    schwankt in der Serie um einige mm (B004 Seite 4: 98 bis 91), dann lägen die 2 bis 4 mm breiten Jahrringe quer
    nicht mehr übereinander. Dazu die Spalten, in denen Holz liegt (Anfang, Ende ausschließlich). Langsame
    Helligkeitsverläufe längs (über 40 mm) sind abgezogen: Das Licht der Box steht im Bild, das Holz wandert."""
    k, px = s["kanten"], s["px_je_mm"]
    mitte = (k["oben"] + k["unten"]) / 2
    y0, y1 = mitte - hoehe_mm / 2 * px, mitte + hoehe_mm / 2 * px
    zeilen = max(2, round(hoehe_mm * VERSATZ_PX_JE_MM))
    je_px = VERSATZ_PX_JE_MM / px
    breite = max(2, round(s["bild"].width * je_px))
    grau = s["bild"].convert("L").resize((breite, zeilen), Image.Resampling.BOX, box=(0, y0, s["bild"].width, y1))
    a = np.asarray(grau, np.float64)
    f = min(round(40 * VERSATZ_PX_JE_MM), a.shape[1])
    kum = np.cumsum(np.pad(a, ((0, 0), (f // 2 + 1, f - f // 2)), mode="edge"), axis=1)
    a = a - (kum[:, f:] - kum[:, :-f])[:, :a.shape[1]] / f
    anfang = 0 if k["rand_links"] else min(breite - 2, max(0, round(k["links"] * je_px)))
    ende = breite if k["rand_rechts"] else max(anfang + 2, min(breite, round(k["rechts"] * je_px)))
    return a, anfang, ende


def korrelation(a: np.ndarray, b: np.ndarray, min_spalten: int) -> tuple[np.ndarray, np.ndarray]:
    """Normierte Korrelation für jede Verschiebung s (Spalte j von b auf Spalte j + s von a) mit mindestens
    min_spalten Überlappung, über FFT. Ergebnis: Verschiebungen und Güte (-1 bis 1)."""
    zeilen, wa = a.shape
    wb = b.shape[1]
    s = np.arange(-(wb - min_spalten), wa - min_spalten + 1)
    if len(s) == 0:
        return s, np.zeros(0)
    n = wa + wb
    xy = np.fft.irfft((np.fft.rfft(a, n) * np.conj(np.fft.rfft(b, n))).sum(axis=0), n)[s % n]
    def fenster(c: np.ndarray, von: np.ndarray, bis: np.ndarray) -> np.ndarray:
        kum = np.concatenate([[0.0], np.cumsum(c)])
        return kum[bis] - kum[von]
    a0, a1 = np.maximum(0, s), np.minimum(wa, wb + s)
    b0, b1 = np.maximum(0, -s), np.minimum(wb, wa - s)
    anzahl = zeilen * (a1 - a0)
    sx, sxx = fenster(a.sum(0), a0, a1), fenster((a * a).sum(0), a0, a1)
    sy, syy = fenster(b.sum(0), b0, b1), fenster((b * b).sum(0), b0, b1)
    zaehler = xy - sx * sy / anzahl
    nenner = np.sqrt(np.maximum(sxx - sx * sx / anzahl, 1e-9) * np.maximum(syy - sy * sy / anzahl, 1e-9))
    return s, zaehler / nenner


def guete_bei(kurve: tuple[int, np.ndarray], weg: np.ndarray | int) -> np.ndarray:
    """Güte einer Kurve (erster Weg, Güten je Spalte) an den Wegen weg, -1 außerhalb."""
    lo, g = kurve
    i = np.asarray(weg) - lo
    drin = (i >= 0) & (i < len(g))
    return np.where(drin, g[np.clip(i, 0, max(len(g) - 1, 0))] if len(g) else -1.0, -1.0)


def serie_lage(stuecke: list[dict]) -> dict:
    """Serie (Jan 27.11.2026: Balken langsam durchgeschoben, Handy fotografiert laufend): Lage längs jedes Fotos aus
    der Überlappung mit dem nächsten und übernächsten. Die Stücke stehen in Aufnahme-Reihenfolge; mitte_mm wird
    gesetzt. Richtung wie beim Plan: das erste Foto zeigt den Anfang (vorderes Ende) des Balkens.

    Bei Fichte mit Maserung längs ist die Korrelation eines einzelnen Paares oft schwach und hat Nebengipfel
    (B004, B005). Darum werden alle Wege gemeinsam gewählt: eine Schieberichtung für die ganze Serie, Schritte
    ähnlich lang wie ihre Nachbarn, und der Weg über zwei Fotos muss zur Summe der beiden Schritte passen."""
    hoehe = 0.8 * float(np.median([(s["kanten"]["unten"] - s["kanten"]["oben"]) / s["px_je_mm"] for s in stuecke]))
    profile = [profil(s, hoehe) for s in stuecke]
    # Was in allen Fotos an derselben Bildstelle steht (Licht, Spiegelungen, Staub), wandert nicht mit dem Holz und
    # zog bei B004 den Versatz auf 0: den Median über die Serie je Bildstelle abziehen.
    if len(profile) >= 3 and len({p[0].shape for p in profile}) == 1:
        stehend = np.median(np.stack([p[0] for p in profile]), axis=0)
        profile = [(p - stehend, a, e) for p, a, e in profile]
    holz = []
    rand = round(VERSATZ_RAND_MM * VERSATZ_PX_JE_MM)
    for p, a, e in profile:
        # Liegt das Holz am Bildrand an, ist es dort heller (Licht der Box), an wechselnder Stelle quer: Der Abzug des
        # stehenden Anteils nimmt das nicht weg, und bei Weg 0 decken sich die Ränder (B007 Seite 4: Güte 0,85 bei 0).
        if a == 0 and e - a > 2 * rand + 2:
            a += rand
        if e == p.shape[1] and e - a > 2 * rand + 2:
            e -= rand
        p = p[:, a:e]
        p = p - p.mean(axis=1, keepdims=True)
        holz.append((p / max(float(p.std()), 1e-6), a))
    min_sp = round(VERSATZ_MIN_MM * VERSATZ_PX_JE_MM)
    # Güte je Weg (Spalten, Holz wandert nach rechts positiv), für Nachbarn (eins) und Übernächste (zwei)
    def kurve(i: int, j: int) -> tuple[int, np.ndarray]:
        (pa, xa), (pb, xb) = holz[i], holz[j]
        s, g = korrelation(pa, pb, min_sp)
        if not len(s):
            return 0, np.zeros(0)
        weg, g = (xb - xa - s)[::-1], g[::-1].copy()                  # Weg wächst mit fallendem s
        # Stillstand oder Schleichen nur, wenn die Fotos fast gleich sind (B005 Seite 1: Güte 1,0, B004 Seite 2:
        # 14 mm mit 0,88). Sonst ist ein Gipfel nahe 0 der Rest des stehenden Bildanteils (B005 Seite 3: drei
        # Schritte 0 mit Güte 0,2 bis 0,35, Länge 23 % kurz; B007: viele Schritte von genau 10 mm).
        g[(np.abs(weg) < VERSATZ_RUHE_MM * VERSATZ_PX_JE_MM) & (g < VERSATZ_RUHE_GUETE)] = -1.0
        return int(weg[0]), g
    eins = [kurve(i, i + 1) for i in range(len(holz) - 1)]
    zwei = [kurve(i, i + 2) for i in range(len(holz) - 2)]
    weit = max(max(abs(lo), abs(lo + len(g))) for lo, g in eins) + 1
    toleranz = round(VERSATZ_RUECK_MM * VERSATZ_PX_JE_MM)
    bestes = None
    for r in (1, -1):                       # Holz wandert im Bild nach rechts (1) oder nach links (-1)
        w = np.arange(-toleranz, weit + 1) * r                       # mögliche Wege je Schritt (Spalten)
        sprung = (w[None, :] - w[:, None]) / VERSATZ_PX_JE_MM        # Unterschied zum vorigen Schritt in mm
        strafe = np.minimum(VERSATZ_GLATT * sprung ** 2, VERSATZ_GLATT_MAX)
        summe = w[:, None] + w[None, :]
        punkte, zurueck = guete_bei(eins[0], w), []
        for i in range(1, len(eins)):
            # i bis i+2 belohnt nur: Bei großen Schritten überlappen die beiden gar nicht (B004: 100 mm Schritt,
            # 196 mm Bildfeld), das darf den Weg nicht bestrafen
            gesamt = punkte[:, None] - strafe + VERSATZ_ZWEI * np.maximum(guete_bei(zwei[i - 1], summe), 0.0)
            zurueck.append(gesamt.argmax(axis=0))
            punkte = gesamt.max(axis=0) + guete_bei(eins[i], w)
        pfad = [int(punkte.argmax())]
        for z in reversed(zurueck):
            pfad.append(int(z[pfad[-1]]))
        pfad.reverse()
        if bestes is None or punkte.max() > bestes[0]:
            bestes = (float(punkte.max()), r, np.array([int(w[p]) for p in pfad]))
    _, r_bild, wege_sp = bestes
    gueten = [float(guete_bei(eins[i], x)) for i, x in enumerate(wege_sp)]
    # unsicher: weder das Paar selbst noch ein Weg über zwei Fotos, an dem der Schritt beteiligt ist, trägt ihn
    stuetze = [max([gueten[i]] + [float(guete_bei(zwei[j], wege_sp[j] + wege_sp[j + 1]))
                                  for j in (i - 1, i) if 0 <= j < len(zwei)]) for i in range(len(wege_sp))]
    wege = [x / VERSATZ_PX_JE_MM for x in wege_sp]
    k = stuecke[0]["kanten"]
    if not k["rand_links"] and k["rand_rechts"]:
        r = 1
    elif not k["rand_rechts"] and k["rand_links"]:
        r = -1
    else:              # vorderes Ende zeigt in Schieberichtung: schiebt das Holz nach rechts, liegt der Anfang rechts
        r = -r_bild
    # Bildmitte von Foto b gegen Foto a: Weg des Holzes, dazu der Unterschied der halben Bildbreiten in mm (gleich,
    # solange beide Fotos denselben Maßstab haben)
    lage = 0.0
    stuecke[0]["mitte_mm"] = lage
    for a, b, x in zip(stuecke[:-1], stuecke[1:], wege, strict=True):
        lage += r * (-x + (b["bild"].width / b["px_je_mm"] - a["bild"].width / a["px_je_mm"]) / 2)
        b["mitte_mm"] = lage
    return {"versatz_mm": [round(x, 1) for x in wege], "guete": [round(g, 2) for g in gueten],
            "unsicher": sum(g < VERSATZ_GUETE for g in stuetze), "richtung": r,
            "unsicher_schritte": [i for i, g in enumerate(stuetze) if g < VERSATZ_GUETE]}


def ist_holz(bild: Image.Image, k: dict) -> bool:
    """Die gefundene Fläche ist Holz, nicht nur Grund. Auf einem Foto ohne Holz trennt die Maske Rauschen oder
    Lichtflecken und meldet die ganze Bildfläche."""
    ausschnitt = bild.crop((round(k["links"]), round(k["oben"]), round(k["rechts"]), round(k["unten"])))
    if not ausschnitt.width or not ausschnitt.height:
        return False
    ausschnitt.thumbnail((400, 400))
    a = np.asarray(ausschnitt.convert("RGB"), np.float32)
    hell = float(np.median(0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]))
    return hell >= HOLZ_HELL or float(np.median(a[..., 0] - a[..., 2])) >= HOLZ_ROT


def schaerfe(bild: Image.Image, k: dict) -> float:
    """Schärfe der Holzfläche: Streuung des Laplace-Filters im Grauwert, in voller Auflösung (Bewegungsunschärfe
    beim Schieben ist nur wenige Pixel breit). Nur innerhalb einer Seite vergleichbar."""
    x0, x1 = round(k["links"]), round(k["rechts"])
    rand = round((k["unten"] - k["oben"]) * 0.1)
    y0, y1 = round(k["oben"]) + rand, round(k["unten"]) - rand
    if x1 - x0 < 3 or y1 - y0 < 3:
        return 0.0
    g = np.asarray(bild.crop((x0, y0, x1, y1)).convert("L"), np.float32)
    lap = 4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    return round(float(lap.var()), 2)


def richtung(stuecke: list[dict], fest: int | None = None) -> int:
    """+1, wenn mm längs nach rechts wachsen. Das Foto mit der kleinsten Lage zeigt den Anfang des Balkens."""
    if fest:
        return fest
    erstes = min(stuecke, key=lambda s: s["mitte_mm"])
    if not erstes["kanten"]["rand_links"]:
        return 1
    if not erstes["kanten"]["rand_rechts"]:
        return -1
    raise ValueError("erstes Foto zeigt kein Balkenende, Lage längs nicht bestimmbar")


def verkleinert(bild: Image.Image, k: dict, px: float) -> tuple[Image.Image, dict, float]:
    """Gerades Foto auf höchstens MERK_PX_JE_MM verkleinert, Kanten und px je mm mitgerechnet. Das Seitenbild hat
    höchstens ZIEL_PX_JE_MM, das Handy liefert 9 bis 15 px je mm: So bleibt je Foto ein Sechstel im Speicher (B007:
    29 Fotos je Seite, sonst über 1,5 GB)."""
    f = MERK_PX_JE_MM / px
    if f >= 1:
        return bild, k, px
    klein = bild.resize((max(1, round(bild.width * f)), max(1, round(bild.height * f))), Image.Resampling.BOX)
    fx, fy = klein.width / bild.width, klein.height / bild.height
    k = {**k, "links": k["links"] * fx, "rechts": k["rechts"] * fx, "oben": k["oben"] * fy, "unten": k["unten"] * fy}
    return klein, k, px * fx


def seite_bauen(fotos: list[dict], laenge_mm: float, flaeche_mm: float, serie: bool = False,
                kacheln=None) -> tuple[Image.Image, dict]:
    """fotos: je {"bild": PIL-Bild (Zuschnitt) oder "laden": Funktion, die es liefert, "mitte_mm": Lage der Bildmitte
    längs, "px_je_mm"}. Mit "laden" liegt je Foto nur das gerade gedrehte, verkleinerte Bild im Speicher.
    Ergebnis: Seitenbild genau laenge_mm x flaeche_mm (längs waagerecht) und ein Bericht mit den gemessenen Maßen.
    serie: Lage unbekannt, Fotos in Aufnahme-Reihenfolge; mitte_mm wird aus der Überlappung gerechnet.
    kacheln: Funktion (nr, Bild), bekommt die feinen Kacheln nacheinander in Rechenreihenfolge (Balkenanfang zuerst);
    im Bericht stehen dann ihre Breiten in Bildrichtung (kacheln_mm)."""
    stuecke, leer = [], 0
    for nr, f in enumerate(fotos):
        try:
            gerade, k = flaeche_finden(f["bild"] if "bild" in f else f["laden"]())
        except ValueError:
            k = None
        # Leere Fotos am Ende einer Serie (Balken schon durch, B004 Seite 2) oder nur ein Rest der Stirnseite: Die
        # Maske greift dann die Schiene am Bildrand. Weniger als LEER_ANTEIL der Bildbreite Holz zählt nicht.
        if k is None or (k["rechts"] - k["links"]) < LEER_ANTEIL * gerade.width or not ist_holz(gerade, k):
            leer += 1
            continue
        scharf = schaerfe(gerade, k)
        gerade, k, px = verkleinert(gerade, k, float(f["px_je_mm"]))
        stuecke.append({"bild": gerade, "kanten": k, "mitte_mm": float(f.get("mitte_mm") or 0), "px_je_mm": px,
                        "quelle": f, "nr": nr, "schaerfe": scharf})
    if not stuecke:
        raise ValueError("kein Foto der Seite zeigt Holz")
    # Ein Foto, das deutlich anders schief liegt als die übrigen, zeigt meist das Balkenende oder eine Stirnseite
    # (B005: −1° überall, am Ende −22° und −18°). Es bekommt den Winkel der übrigen.
    if len(stuecke) >= 3:
        mitte = float(np.median([s["kanten"]["winkel"] for s in stuecke]))
        for s in stuecke:
            if abs(s["kanten"]["winkel"] - mitte) > AUSREISSER_GRAD:
                q = s["quelle"]
                s["bild"] = None                                        # erst freigeben, dann neu laden
                gerade, k = flaeche_finden(q["bild"] if "bild" in q else q["laden"](), fest=mitte)
                s["bild"], s["kanten"], s["px_je_mm"] = verkleinert(gerade, k, float(q["px_je_mm"]))
    lage = serie_lage(stuecke) if serie and len(stuecke) > 1 else None
    r = richtung(stuecke, lage and lage["richtung"])
    # Lage jeder Bildspalte längs in mm, Nullpunkt am Anfang des Balkens im ersten Foto
    for s in stuecke:
        s["mm"] = lambda x, s=s: s["mitte_mm"] + r * (x - s["bild"].width / 2) / s["px_je_mm"]
    erstes, letztes = min(stuecke, key=lambda s: s["mitte_mm"]), max(stuecke, key=lambda s: s["mitte_mm"])
    anfang = erstes["mm"](erstes["kanten"]["links" if r > 0 else "rechts"])
    ende_px = letztes["kanten"]["rechts" if r > 0 else "links"]
    ende = letztes["mm"](ende_px) if not letztes["kanten"]["rand_rechts" if r > 0 else "rand_links"] else None

    gemessen_laenge = (ende - anfang) if ende is not None else None
    streck = (gemessen_laenge / laenge_mm) if gemessen_laenge else 1.0      # gemessene auf eingetragene Länge
    quer = []
    lagen = []                    # je Stück: Spalten x0..x1 im Foto und ihre Lage a..b in mm ab Balkenanfang
    for s in stuecke:
        k = s["kanten"]
        quer.append((k["unten"] - k["oben"]) / s["px_je_mm"])
        x0 = 0.0 if k["rand_links"] else k["links"]
        x1 = float(s["bild"].width) if k["rand_rechts"] else k["rechts"]
        lagen.append(sorted(((s["mm"](x0) - anfang) / streck, (s["mm"](x1) - anfang) / streck)))

    def zeichnen(von_mm: float, bis_mm: float, aus: float) -> tuple[np.ndarray, np.ndarray]:
        """Ausschnitt von_mm..bis_mm (ab Balkenanfang) in aus px je mm, dazu das Gewicht (0 = Lücke)."""
        z_von, z_bis = round(von_mm * aus), round(bis_mm * aus)
        breite, hoehe = z_bis - z_von, round(flaeche_mm * aus)
        summe = np.zeros((hoehe, breite, 3), np.float32)
        gewicht = np.zeros((hoehe, breite), np.float32)
        for s, (a, b) in zip(stuecke, lagen, strict=True):
            k = s["kanten"]
            z0, z1 = max(z_von, math.floor(a * aus)), min(z_bis, math.ceil(b * aus))
            if z1 <= z0:
                continue
            # Zielspalten z0..z1 zeigen die Bildspalten zwischen x0 und x1 (Richtung beachten), quer oben..unten
            links_mm, rechts_mm = z0 / aus * streck + anfang, z1 / aus * streck + anfang
            bx = [s["bild"].width / 2 + r * (m - s["mitte_mm"]) * s["px_je_mm"] for m in (links_mm, rechts_mm)]
            stueck = s["bild"].transform((z1 - z0, hoehe), Image.Transform.EXTENT,
                                         (bx[0], k["oben"], bx[1], k["unten"]), Image.Resampling.BICUBIC)
            # Überblenden: Gewicht steigt zu den Rändern des Stücks hin linear ab (höchstens 30 mm breit)
            spalten = np.arange(z0, z1) + 0.5
            rampe = max(1.0, 30 * aus)
            w = np.clip(np.minimum(spalten - a * aus, b * aus - spalten) / rampe, 0.01, 1.0)
            summe[:, z0 - z_von:z1 - z_von] += np.asarray(stueck, np.float32) * w[None, :, None]
            gewicht[:, z0 - z_von:z1 - z_von] += w[None, :]
        bild = (summe / np.maximum(gewicht, 1e-9)[..., None]).clip(0, 255).astype(np.uint8)
        return (bild[:, ::-1] if r < 0 else bild), gewicht[0]   # r < 0: Bildrichtung des Fotos, nie spiegeln

    # Feine Kacheln (Jan 27.11.2026: 3D-Ansicht verschwommen, 2,25 statt 9,8 px je mm bei 3,55 m): je KACHEL_MM
    # ein Bild in KACHEL_PX_JE_MM, nacheinander gerechnet (Speicher). Das Übersichtsbild entsteht aus ihnen.
    aus = min(ZIEL_PX_JE_MM, MAX_BREITE_PX / laenge_mm)
    fein = max(aus, min(KACHEL_PX_JE_MM, max(s["px_je_mm"] for s in stuecke)))
    anzahl = max(1, math.ceil(laenge_mm / KACHEL_MM - 0.05))
    grenzen = [laenge_mm * i / anzahl for i in range(anzahl + 1)]
    uebersicht = np.zeros((round(flaeche_mm * aus), round(laenge_mm * aus), 3), np.uint8)
    leer_sp, alle_sp, fertig = 0, 0, []
    for von, bis in zip(grenzen, grenzen[1:], strict=False):
        kachel, gew = zeichnen(von, bis, fein)
        leer_sp, alle_sp = leer_sp + int((gew == 0).sum()), alle_sp + gew.size
        u0, u1 = round(von * aus), round(bis * aus)
        if r < 0:
            u0, u1 = uebersicht.shape[1] - u1, uebersicht.shape[1] - u0
        klein = Image.fromarray(kachel).resize((u1 - u0, uebersicht.shape[0]), Image.Resampling.LANCZOS)
        uebersicht[:, u0:u1] = np.asarray(klein)
        if kacheln is not None:
            fertig.append((von, bis))
            kacheln(len(fertig) - 1, Image.fromarray(kachel))
        del kachel, klein
    luecke = leer_sp / max(1, alle_sp)
    # Lage jedes Fotos (mm ab Balkenanfang, nur der Holzteil) für die Auswahl fürs Labeln (auswahl.py)
    unsicher = au.unsichere_fotos(len(stuecke), lage["unsicher_schritte"]) if lage else set()
    je_foto = [{"a_mm": None, "b_mm": None} for _ in fotos]
    for j, (s, (a, b)) in enumerate(zip(stuecke, lagen, strict=True)):
        je_foto[s["nr"]] = {"a_mm": round(float(a), 1), "b_mm": round(float(b), 1), "schaerfe": s["schaerfe"],
                            **({"unsicher": True} if j in unsicher else {})}
    bericht = {"fotos": len(fotos), "leer": leer, "richtung": r, "winkel_grad": [round(s["kanten"]["winkel"], 2) for s in stuecke],
               "ausreisser": sum(bool(s["kanten"].get("ausreisser")) for s in stuecke), **({"serie": lage} if lage else {}),
               "laenge_mm": round(gemessen_laenge, 1) if gemessen_laenge else None,
               "flaeche_mm": round(float(np.median(quer)), 1), "luecke_anteil": round(luecke, 4),
               "px_je_mm": round(aus, 3), "lagen": je_foto}
    if kacheln is not None:
        # in Bildrichtung von links nach rechts: bei r < 0 liegt die letzte gerechnete Kachel links
        breiten = [round(b - a, 1) for a, b in fertig]
        bericht["kacheln_mm"] = breiten[::-1] if r < 0 else breiten
        bericht["kachel_px_je_mm"] = round(fein, 3)
    return Image.fromarray(uebersicht), bericht


def px_aus_plan(zuschnitt: Image.Image, plan: dict) -> float:
    """px je mm, wenn das Foto keinen Wert hat (auf dem Mac misst sips ihn): ganze Bildbreite durch voll_mm."""
    anteil = (plan.get("zuschnitt") or [0, 0, 1, 1])[2]
    return zuschnitt.width / anteil / plan["voll_mm"]


def abweichung(gemessen: float | None, soll: float) -> float | None:
    return None if gemessen is None else round(100 * (gemessen - soll) / soll, 1)


def unplausibel(bericht: dict) -> str | None:
    """Grund, warum eine Seite nicht auf den Körper gehört (schief, falsch gelegt, Maßstab falsch), sonst None."""
    winkel = max((abs(w) for w in bericht["winkel_grad"]), default=0.0)
    if winkel > MAX_WINKEL:
        return f"liegt {winkel:.0f}° schief"
    if bericht.get("serie") and bericht["serie"]["unsicher"] > len(bericht["serie"]["guete"]) // 2:
        return "Fotos der Serie passen nicht aneinander"
    abw = [abs(a) for a in bericht["abweichung_prozent"].values() if a is not None]
    if abw and max(abw) > MAX_ABWEICHUNG:
        return f"Maß weicht {max(abw):.0f} % ab"
    if bericht["luecke_anteil"] > 0.02:
        return f"{100 * bericht['luecke_anteil']:.0f} % der Länge fehlen"
    return None


def koerper_bauen(ordner: Path) -> dict:
    """Liest <ordner>/balken.json und die Zuschnitte, schreibt <ordner>/koerper/. Seiten ohne Fotos fehlen."""
    balken = json.loads((ordner / "balken.json").read_text(encoding="utf-8"))
    ziel = ordner / "koerper"
    ziel.mkdir(exist_ok=True)
    ergebnis = {"id": balken["id"], "laenge_mm": balken["laenge_mm"], "breite_mm": balken["breite_mm"],
                "hoehe_mm": balken["hoehe_mm"], "seiten": {}}
    for nr, seite in sorted(balken.get("seiten", {}).items()):
        eintraege = [f for _, f in sorted(seite.get("fotos", {}).items(), key=lambda x: int(x[0]))]
        if not eintraege:
            continue
        flaeche = seite["plan"]["flaeche_mm"]
        senkrecht = seite["plan"].get("richtung") == "kurz"      # Balken lief im Bild von oben nach unten
        fotos = []
        for f in eintraege:
            pfad = ordner / "zuschnitt" / (Path(f["datei"]).stem + ".jpg")
            if not pfad.exists():
                raise FileNotFoundError(f"Zuschnitt fehlt: {pfad}")
            def laden(pfad: Path = pfad, senkrecht: bool = senkrecht) -> Image.Image:
                with Image.open(pfad) as roh:
                    bild = roh.convert("RGB")
                return bild.transpose(Image.Transpose.ROTATE_90) if senkrecht else bild   # längs waagerecht
            px = f.get("px_je_mm")
            if not px:
                with Image.open(pfad) as roh:
                    px = px_aus_plan(Image.new("1", roh.size[::-1] if senkrecht else roh.size), seite["plan"])
            fotos.append({"laden": laden, "mitte_mm": f["mitte_mm"], "px_je_mm": px, "name": Path(f["datei"]).stem})
        for alt in ziel.glob(f"S{nr}_[0-9]*.jpg"):
            alt.unlink()

        def kachel(i: int, bild: Image.Image, nr: str = nr) -> None:
            bild.save(ziel / f"S{nr}_r{i}.tmp", "JPEG", quality=88)

        bild, bericht = seite_bauen(fotos, balken["laenge_mm"], flaeche, bool(seite["plan"].get("serie")), kachel)
        n = len(bericht["kacheln_mm"])
        for i in range(n):
            (ziel / f"S{nr}_r{i}.tmp").replace(ziel / f"S{nr}_{(n - 1 - i) if bericht['richtung'] < 0 else i}.jpg")
        vorlaeufig = ziel / f"S{nr}.tmp"
        bild.save(vorlaeufig, "JPEG", quality=90)
        vorlaeufig.replace(ziel / f"S{nr}.jpg")
        klein = bild.resize((KLEIN_PX, max(24, round(bild.height * KLEIN_PX / bild.width))), Image.Resampling.LANCZOS)
        klein.save(vorlaeufig, "JPEG", quality=85)
        vorlaeufig.replace(ziel / f"S{nr}_k.jpg")
        bericht["soll_mm"] = {"laenge": balken["laenge_mm"], "flaeche": flaeche}
        bericht["abweichung_prozent"] = {"laenge": abweichung(bericht["laenge_mm"], balken["laenge_mm"]),
                                         "flaeche": abweichung(bericht["flaeche_mm"], flaeche)}
        bericht["grund"] = unplausibel(bericht)
        lagen = bericht.pop("lagen")
        wahl = au.auswaehlen([{"a": x["a_mm"], "b": x["b_mm"], "schaerfe": x.get("schaerfe"),
                               "unsicher": x.get("unsicher")} for x in lagen], ganz=bool(bericht["grund"]))
        bericht["auswahl"] = [{"name": f["name"], "wahl": w, **x} for f, w, x in zip(fotos, wahl, lagen, strict=True)]
        ergebnis["seiten"][nr] = bericht
    (ziel / "koerper.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")
    return ergebnis


if __name__ == "__main__":
    print(json.dumps(koerper_bauen(Path(sys.argv[1])), ensure_ascii=False, indent=1))
