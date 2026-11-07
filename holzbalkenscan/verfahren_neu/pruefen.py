"""Prueft eine Bildreihe, BEVOR das Bauteil vom Bock genommen wird.

Das Werkzeug beurteilt nur. Es setzt nichts zusammen und schreibt nichts in
den Bildordner. Es beantwortet die eine Frage, die man am Bauteil nicht sehen
kann: Taugt diese Reihe zum Zusammensetzen - und wenn nicht, welche Aufnahmen
sind schuld und was ist zu aendern?

Warum diese Fassung anders prueft als die erste
-----------------------------------------------
Zwei Reihen desselben Balkens, Seite A und Seite C, halten dieselben
Aufnahmeregeln ein: gleicher Abstand (644 gegen 655 mm), gleicher
Bauteilanteil am Bild (25 gegen 25 %), gleiche Aufloesung (8.9 gegen
8.6 Px/mm), mehr Ueberlappung auf C (70 gegen 64 %). Trotzdem setzt sich A
sauber zusammen und C ueberhaupt nicht. Eine Checkliste haette das nicht
gefangen.

Gemessen unterscheiden sich die beiden an genau einer Stelle: dem Kontrast
der Bauteilkanten gegen ihren Hintergrund. Seite A hat 37 und 26 Graustufen,
Seite C hat 17 und 4.7 - der vergraute Balken steht vor grauem Pflaster. Und
daran haengt alles Weitere als Kette: schwache Unterkante, Kantengerade sitzt
79 statt 25 Px daneben, jedes Bild falsch entzerrt, Streifen verzogen,
Zuordnung findet nichts, 13 von 30 Aufnahmen abgehaengt.

Deshalb misst diese Fassung den Kantenkontrast je Kante und je Aufnahme. Der
Rasterabschnitt der ersten Fassung (Massstab aus Lamellenfugen) ist
entfallen: Vollholz hat keine Fugen, und ein Verfahren, das nur bei BSH
greift, taugt nicht als Regelpruefung.

Woran sich die Pruefung orientiert - und woran nicht
----------------------------------------------------
Grundsatz: Es darf nichts gemessen werden, was die Bauteile VONEINANDER
unterscheidet. Farbe, Helligkeit, Saettigung und Waerme wechseln von Bauteil
zu Bauteil und von Licht zu Licht; Geometrie und Faserrichtung nicht.

  Parallaxe          Das Bauteil ist das naechste grosse Objekt vor der
                     Kamera und wandert zwischen zwei Aufnahmen viel weiter
                     durchs Bild als der Hintergrund. Trug auf beiden Reihen.
  zwei gerade        Das Maassrueckgrat. Traegt, solange beide Kanten
  parallele Kanten   Kontrast haben - genau das wird hier geprueft.
  Faserrichtung      Laengs gerichtete Struktur. Trennt Holz vom Untergrund,
                     gilt fuer BSH und Vollholz gleichermassen.
  Farbe, Kontrast    NICHT als Merkmal. Auf Seite C gewinnt sonst die
  als solcher        Hallendecke. Kontrast ist Guetemass, nicht Kennzeichen.

Zwei Urteile, nicht eines
-------------------------
Geurteilt wird getrennt nach Masstreue und Farbtreue - den beiden Groessen,
auf die es ankommt. Eine Reihe kann masslich einwandfrei und farblich
wackelig sein; Reihe Seite A ist genau das, und ein gemeinsames Urteil
wuerde sie verwerfen.

Entscheidend fuer die Masstreue ist nicht der Mittelwert ueber die Reihe,
sondern die laengste zusammenhaengende Strecke unbrauchbarer Aufnahmen. Eine
einzelne laesst sich ueberspringen; zwei hintereinander trennen die Kette.
Reihe Seite C zeigt, warum der Mittelwert nicht taugt: Ihr Kantenkontrast
liegt im Median bei 50 und 37 Graustufen - voellig unauffaellig -, waehrend
die ersten elf Aufnahmen bei 4 bis 18 liegen und die Kette dort reisst.

Woran die Schwellen kalibriert sind
-----------------------------------
Drei Reihen desselben Balkens, mit bekanntem Ausgang:

                            Seite A      Seite B       Seite C
  Flaeche                   230 mm       120 mm        230 mm
  Bauteilanteil am Bild      27 %         11 %          27 %
  Aufloesung                9.04 Px/mm   9.07 Px/mm    8.59 Px/mm
  Kantenkontrast K1 / K2     88 / 62      47 / 66       50 / 38
  Textur                     7.5         10.4           8.0
  Ueberlappung, kleinste     56 %         57 %          56 %
  unbrauchbare Aufnahmen      0 von 26     4 von 22     17 von 30
  laengste Ausfallstrecke     -            1            11
  ---------------------------------------------------------------
  Urteil Masstreue          GRUEN        GELB          ROT
  Urteil Farbtreue          GELB         GELB          GELB

  tatsaechlicher Ausgang    setzt sich   noch nicht    faellt
                            sauber zu-   zusammen-     auseinander
                            sammen       gesetzt       (17 von 30
                            (Nahtver-                  verbunden)
                            satz 0.09 mm)

Die drei Reihen scheitern aus DREI verschiedenen Gruenden, und das ist der
Wert dieser Pruefreihe: C am Kantenkontrast, B am geringen Bauteilanteil und
den daraus folgenden Kantenresten, alle drei an der Farbdrift.

Aufruf
------
    python3 pruefen.py <Bildordner>
    python3 pruefen.py <Bildordner> --hoehe-mm 120
    python3 pruefen.py <Bildordner> --bericht bericht.txt

  --hoehe-mm    Hoehe der fotografierten Flaeche in mm. Ohne Angabe wird sie
                aus bauteil.json gelesen; fehlt auch die, entfallen alle
                Angaben in Millimetern (geprueft wird trotzdem).
  --teiler      Verkleinerung beim Lesen (Vorgabe 8). Groesser = schneller.
  --bericht     Ausgabe zusaetzlich in eine Textdatei schreiben.

Es braucht ausschliesslich Pillow, numpy und zusammensetzen2.py aus demselben
Ordner. Kein Netz, keine Installation, keine Fremdbibliothek.

Stand 2026-10-21 - zweite Fassung, Kriterien aus dem Vergleich der Reihen
Seite A / Seite B / Seite C.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import zusammensetzen2 as z
except Exception as fehler:                                  # pragma: no cover
    print("zusammensetzen2.py liegt nicht neben pruefen.py oder laesst sich "
          f"nicht laden:\n  {fehler}")
    sys.exit(2)

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()

# ------------------------------------------------------------- Schwellen ---
#
# Kalibriert an drei Reihen desselben Balkens: Seite A (gelingt), Seite B
# (Schmalseite), Seite C (misslingt). Die Schwelle liegt jeweils so, dass A
# besteht und der gemessene Mangel von C anschlaegt - nicht enger, damit nicht
# jede brauchbare Reihe rot wird.
#
# (Kennwert, gelb unter, rot unter)  bzw. bei "hoch ist schlecht" umgekehrt.

S_KONTRAST_MED = (20.0, 10.0)     # Graustufen, Median ueber die Stationen
S_KONTRAST_BLIND = (20.0, 40.0)   # Prozent blinder Laenge - hoch ist schlecht
S_TEXTUR = (5.0, 3.0)             # Hochpassstreuung im Band
S_FASER = (1.4, 1.1)              # quer/laengs - unter 1.1 ist es kein Holz
#
# Die Faserrichtung ist eine Sicherung gegen "das Band ist gar kein Holz",
# kein Guetemass: Die gehobelte Schmalseite (Reihe Seite B) kommt auf 1.71,
# die misslungene Reihe Seite C auf 1.86. Sie unterscheidet gute von
# schlechten Reihen nicht - sie unterscheidet Holz von Hallendecke.
S_ANTEIL = (25.0, 18.0)           # Prozent der Bildbreite
#
# Diese Schwelle ist am 2026-10-21 von (18, 8) heraufgesetzt worden, nachdem
# Reihe Seite B mit 11 % Bauteilanteil tatsaechlich zusammengesetzt wurde und
# auseinanderfiel. Die Flaeche, auf der sich zwei Aufnahmen wiederfinden
# koennen, ist das Band - und mit dem Band schrumpft die Ausbeute weit
# schneller als linear:
#
#               Band       Punktpaare   abgehaengte
#               im Bild     je Naht      Aufnahmen
#   Seite A     2170 Px       51.9        0 von 26     setzt sich zusammen
#   Seite B     1088 Px        7.8        9 von 22     faellt auseinander
#   Seite C     1976 Px        6.1       13 von 30     faellt auseinander
#
# Halbes Band, ein Siebtel der Punktpaare. Darunter reisst die Kette, und die
# Ausgleichung bekommt zu wenig zu fassen: Bei Seite B lief sie in die
# bekannte Entartung (73 Grad Querverkippung bei 70 mm Aufnahmeabstand -
# Verkippung und Abstand lassen sich gegeneinander tauschen).
#
# Seite C zeigt zugleich, dass ein breites Band allein nicht genuegt: Dort ist
# das Band breit und die Ausbeute trotzdem klein, weil die Entzerrung an den
# kontrastlosen Kanten scheitert. Die beiden Ursachen sind unabhaengig, und
# beide muessen geprueft werden.
#
# Zwischen 11 % (faellt auseinander) und 27 % (gelingt) ist nicht gemessen
# worden. Die rote Schwelle bei 18 % ist darum geschaetzt, nicht belegt.

S_ANTEIL_OBEN = (60.0, 72.0)      # Prozent - zu NAH ist auch ein Mangel
#
# Das Band wird daran erkannt, dass es sich von dem unterscheidet, was
# beidseits DANEBEN liegt. Fuellt das Bauteil fast das ganze Bild, bleibt
# dafuer kein Rand mehr. Ueber 72 % kann bandgueten gar nicht mehr suchen,
# und schon ab etwa 60 % wird der Vergleich duenn.
S_PXMM = (6.0, 4.0)               # Pixel je mm im Originalbild
S_UEBERLAPP = (45.0, 30.0)        # Prozent
S_NEIGUNG = (3.0, 6.0)            # Grad - hoch ist schlecht
S_REST = (3.0, 8.0)               # mm Abweichung von der Kantengeraden
S_WB = (5.0, 35.0)                # Prozent Farbdrift ueber die Reihe
S_HELL = (30.0, 80.0)             # Prozent Helligkeitsdrift ueber die Reihe
S_BANDSTREIT = (8.0, 20.0)         # Prozent Abweichung der zwei Bandwege
TEILER_MASS = 2                   # Verkleinerung fuer die Probe am Massstab
#
# Farbdrift und Helligkeitsdrift stehen weiter als die uebrigen Schwellen.
# Das ist kein Nachlassen, sondern eine andere Art Mangel: Der Zusammenbau
# rechnet je Aufnahme Kanalfaktoren und ein gemeinsames Lichtfeld heraus, und
# Reihe Seite A setzt sich mit 21 % Farb- und 73 % Helligkeitsdrift sauber
# zusammen (Nahtversatz 0.09 mm). Was bleibt, ist Unsicherheit in der FARBE,
# nicht im Mass. Darum urteilt der Bericht getrennt: Zusammensetzen und
# Farbtreue. Rot heisst "wird nicht", gelb heisst "wird, aber schlechter".
S_STATIONEN = (0.70, 0.45)        # Anteil auswertbarer Laengsstationen

zeilen = []
maengel = []     # (gewicht, bereich, kurz, erklaerung, abhilfe, betroffene)


def sag(t=""):
    print(t, flush=True)
    zeilen.append(t)


# Damit auch die Meldungen der uebernommenen Messroutinen im Bericht landen.
z.sag = sag


def mangel(rot, kurz, erklaerung, abhilfe, betroffene=(), bereich="Mass"):
    """`bereich` ist 'Mass' oder 'Farbe' - danach wird getrennt geurteilt."""
    maengel.append((2 if rot else 1, bereich, kurz, erklaerung, abhilfe,
                    list(betroffene)))


def note(wert, schwellen, hoch_ist_schlecht=False):
    """0 = gruen, 1 = gelb, 2 = rot."""
    gelb, rot = schwellen
    if wert is None or not np.isfinite(wert):
        return 2
    if hoch_ist_schlecht:
        return 2 if wert > rot else (1 if wert > gelb else 0)
    return 2 if wert < rot else (1 if wert < gelb else 0)


ZEICHEN = {0: "ok  ", 1: "gelb", 2: "ROT "}


# --------------------------------------------------------------- Kamera ---

def exif_lesen(pfad: Path) -> dict:
    """Die wenigen Werte, auf die es ankommt. Fehlende Werte sind None."""
    w = {}
    try:
        with Image.open(pfad) as im:
            w["groesse"] = im.size
            roh = im.getexif()
            alle = {TAGS.get(k, k): v for k, v in roh.items()}
            try:
                alle.update({TAGS.get(k, k): v
                             for k, v in roh.get_ifd(0x8769).items()})
            except Exception:
                pass
    except Exception as fehler:
        return {"fehler": str(fehler)}
    w["belichtung"] = alle.get("ExposureTime")
    w["iso"] = alle.get("ISOSpeedRatings") or alle.get("PhotographicSensitivity")
    w["blende"] = alle.get("FNumber")
    w["brennweite"] = alle.get("FocalLength")
    w["ausrichtung"] = alle.get("Orientation")
    return w


def bruch(wert):
    """1/78 statt 0.0128 - so liest man Belichtungszeiten."""
    if wert is None:
        return "?"
    try:
        w = float(wert)
    except (TypeError, ValueError):
        return str(wert)
    return f"1/{round(1 / w)} s" if 0 < w < 1 else f"{w:g} s"


def brueche_brauchbar(e):
    """Sind die Bruchfelder der Kameradaten verwertbar?

    Die Aufnahmen aus ProCamera tragen eine fehlerhafte EXIF-Struktur: Alle
    Felder vom Typ RATIONAL - Belichtungszeit, Blende, Brennweite,
    Verschlusszeit - zeigen auf dieselbe Stelle in der Datei und liefern
    darum denselben Wert (393475/196608 = 2.0013). Das steht so in der Datei
    und ist kein Lesefehler.

    Daran laesst sich nichts reparieren, also wird es erkannt und gemeldet.
    Dass die Belichtung ueber die Reihe fest war, prueft Abschnitt 4 ohnehin
    besser: an der gemessenen Helligkeit des Bauteils selbst.
    """
    w = [e.get("belichtung"), e.get("blende"), e.get("brennweite")]
    try:
        w = [float(v) for v in w]
    except (TypeError, ValueError):
        return False
    return not (abs(w[0] - w[1]) < 1e-9 and abs(w[1] - w[2]) < 1e-9)


def abschnitt_kamera(pfade):
    sag("1 - Aufnahme und Kamera")
    sag("-----------------------")
    daten = [exif_lesen(p) for p in pfade]
    gut = [e for e in daten if "fehler" not in e]
    echt = bool(gut) and any(brueche_brauchbar(e) for e in gut)
    for p, e in zip(pfade, daten):
        if "fehler" in e:
            sag(f"  {p.name:18} NICHT LESBAR: {e['fehler']}")
            continue
        w, h = e["groesse"]
        kopf = f"  {p.name:18} {w}x{h} {'quer' if w > h else 'hoch':5}"
        if echt:
            sag(f"{kopf} {bruch(e['belichtung']):>9}  "
                f"ISO {str(e['iso'] or '?'):<5} f/{e['blende'] or '?'}  "
                f"{e['brennweite'] or '?'} mm")
        else:
            sag(f"{kopf}  ISO {str(e['iso'] or '?'):<5}")

    if not gut:
        return daten
    sag("")
    if not echt:
        sag("  gelb  Die EXIF-Bruchfelder dieser Dateien sind fehlerhaft: "
            "Belichtungszeit,")
        sag("        Blende und Brennweite tragen alle denselben Wert. "
            "Belichtung und")
        sag("        Blende sind daran nicht pruefbar - stattdessen prueft "
            "Abschnitt 4")
        sag("        die gemessene Helligkeit des Bauteils.")
        mangel(False, "Kameradaten unvollstaendig",
               "Die Dateien tragen eine fehlerhafte EXIF-Struktur: alle "
               "Bruchfelder (Belichtungszeit, Blende, Brennweite) haben "
               "denselben Wert.",
               "Kein Mangel der Aufnahme selbst. Falls die Kamera-App eine "
               "Einstellung fuer die Metadaten hat, lohnt ein Blick; sonst "
               "einfach hinnehmen - gemessen wird die Helligkeit.",
               (), "Hinweis")

    fest = True
    felder = [("groesse", "Aufloesung"), ("iso", "ISO")]
    if echt:
        felder += [("belichtung", "Belichtungszeit"), ("brennweite", "Brennweite")]
    for schluessel, name in felder:
        werte = {str(e.get(schluessel)) for e in gut}
        if len(werte) > 1:
            fest = False
            sag(f"  gelb  {name} wechselt: {sorted(werte)}")
            mangel(False, f"{name} nicht fest",
                   f"{name} wechselt innerhalb der Reihe.",
                   "In der Kamera-App manuell festsetzen und waehrend der "
                   "ganzen Reihe nicht anfassen.")
    if fest:
        sag("  ok    " + ("Aufloesung, Belichtung, ISO und Brennweite sind "
                          "konstant." if echt else
                          "Aufloesung und ISO sind ueber die Reihe konstant."))

    lagen = {"quer" if e["groesse"][0] > e["groesse"][1] else "hoch" for e in gut}
    if len(lagen) > 1:
        sag("  ROT   Hoch- und Querformat gemischt.")
        mangel(True, "Formate gemischt",
               "In derselben Reihe liegen Hoch- und Queraufnahmen.",
               "Eine Reihe durchgehend im selben Format aufnehmen.")
    return daten


# ------------------------------------------------------- eine Bildreihe ---

def reihe_lesen(pfade, dreh, teiler, band, stationen=36):
    """Ein Durchgang durch die Reihe. Danach wird nur noch gerechnet.

    Gelesen wird jede Aufnahme genau einmal und gleich auf alles ausgewertet,
    was spaeter gebraucht wird: Querprofile (fuer die Kantensuche), die rohen
    Helligkeiten je Laengsstation (fuer den Kantenkontrast - die Querprofile
    sind normiert und haben die absoluten Graustufen verloren), Textur, Faser-
    richtung, Farbverhaeltnisse und der Laengsversatz zur Vorgaengeraufnahme.

    `band` ist die Vorgabe aus der Parallaxe (Spalten im Arbeitsbild) oder
    None. Textur, Faser und Farbe werden im mittleren Drittel dieses Bandes
    gemessen, damit kein Hintergrund hineinspielt.
    """
    stat, roh, textur, faser, farbe, versatz = [], [], [], [], [], []
    vorher = None
    for n, p in enumerate(pfade):
        with z.lade(p, teiler, dreh) as im:
            a = np.asarray(im, np.float32)
        L, Q, _ = a.shape

        stat.append(z.stationsprofile(a, stationen))

        # rohe Querprofile je Station, in Graustufen
        hoehe = max(6, L // stationen)
        r = np.empty((stationen, Q), np.float32)
        for k in range(stationen):
            y = k * (L - hoehe) // max(stationen - 1, 1)
            r[k] = a[y:y + hoehe].mean(axis=(0, 2))
        roh.append(r)

        # Messfenster fuer Oberflaeche: mittleres Drittel des Bandes
        if band is not None:
            lo, hi = band
            m, d = (lo + hi) / 2.0, (hi - lo)
            x0 = int(max(0, m - d / 6)); x1 = int(min(Q, m + d / 6))
        else:
            x0, x1 = int(0.40 * Q), int(0.60 * Q)
        if x1 - x0 < 12:
            x0, x1 = int(0.40 * Q), int(0.60 * Q)
        kern = a[int(0.15 * L):int(0.85 * L), x0:x1]
        g = kern.mean(axis=2)

        textur.append(float((g - z_glatt2(g, 9)).std()))
        gy, gx = np.gradient(g)
        faser.append(float(np.abs(gx).mean() / (np.abs(gy).mean() + 1e-6)))
        kr, kg, kb = kern[:, :, 0].mean(), kern[:, :, 1].mean(), kern[:, :, 2].mean()
        farbe.append((float(kr / (kg + 1e-6)), float(kb / (kg + 1e-6)), float(kg)))

        # Laengsversatz zur Vorgaengeraufnahme, eine Kachel aus der Bandmitte
        ganz = a.mean(axis=2)
        if vorher is not None:
            versatz.append(laengsversatz(vorher, ganz, x0, x1))
        vorher = ganz
        if (n + 1) % 5 == 0 or n + 1 == len(pfade):
            sag(f"      [{time.time()-T0:6.1f} s] {n+1}/{len(pfade)} gelesen")
    return stat, roh, textur, faser, farbe, versatz


def z_glatt2(g, k):
    """Kastenglaettung in beiden Richtungen, Rand fortgesetzt."""
    k = int(k) | 1
    r = k // 2
    kern = np.ones(k, np.float32) / k
    aus = np.apply_along_axis(
        lambda v: np.convolve(np.pad(v, r, mode="edge"), kern, "valid"), 1, g)
    return np.apply_along_axis(
        lambda v: np.convolve(np.pad(v, r, mode="edge"), kern, "valid"), 0, aus)


def laengsversatz(a, b, x0, x1):
    """Wie weit ist die Kamera zwischen zwei Aufnahmen gewandert (Px laengs)?

    Mehrere Kacheln statt einer, und erst die EINIGKEIT zaehlt. Die erste
    Fassung nahm eine einzige breite Kachel aus der Bandmitte; an der Reihe
    261022 hat sie sich reihenweise verlaufen und Vorschuebe von 16 bis
    103 mm gemeldet, wo der Zollstock im Bild rund 200 mm sagt. Holz ist
    laengs gestreift, und eine einzelne Korrelation rutscht auf dieser
    Streifung leicht um mehrere Jahrringe weiter.

    Genommen werden die Kacheln AUS DEM BAUTEIL (x0..x1), nicht aus dem
    ganzen Bild: Der Hintergrund wandert wegen der Parallaxe viel weniger,
    und gefragt ist die Ueberlappung auf dem Bauteil - nur dort wird spaeter
    zusammengesetzt.
    """
    L, Q = a.shape
    x0 = max(0, int(x0)); x1 = min(Q, int(x1))
    if x1 - x0 < 24 or x1 - x0 >= Q:
        x0, x1 = int(0.35 * Q), int(0.65 * Q)
    kh = max(30, L // 12)
    kw = max(24, (x1 - x0) // 3)
    treffer = []
    for fy in (0.18, 0.34, 0.50, 0.66, 0.82):
        for fx in (0.17, 0.50, 0.83):
            y = int(fy * (L - kh)); x = x0 + int(fx * (x1 - x0 - kw))
            t = a[y:y + kh, x:x + kw]
            if t.std() < 3:
                continue
            r = z.ncc_karte(b, t)
            if r is None or r[2] < 0.45:
                continue
            treffer.append((r[0] - y, r[1] - x, r[2]))
    if len(treffer) < 3:
        return None
    # groesste Gruppe, die sich auf 1 % der Bildhoehe einig ist
    tol = max(6.0, 0.01 * L)
    beste = None
    for kern in treffer:
        gr = [t for t in treffer if abs(t[0] - kern[0]) < tol
              and abs(t[1] - kern[1]) < tol]
        if beste is None or len(gr) > len(beste):
            beste = gr
    if len(beste) < 3:
        return None
    return float(np.median([t[0] for t in beste]))


# --------------------------------------------------------------- Kanten ---

def schnitt(profil, i0, i1):
    lo, hi = sorted((int(i0), int(i1)))
    lo = max(0, lo); hi = min(len(profil), hi)
    if hi - lo < 3:
        return None
    return float(profil[lo:hi].mean())


SCHWACH = 10.0      # Graustufen, ab hier ist eine Stelle praktisch blind


def kontrast_einer_kante(roh, ys, a0, steigung, drin, abstand, breite):
    """Helligkeitsunterschied diesseits und jenseits EINER Bauteilkante.

    Der entscheidende Kennwert. Gemessen wird je Laengsstation ein Streifen
    dicht INNERHALB der Kante gegen einen gleich breiten dicht AUSSERHALB,
    beide mit kleinem Abstand zur Kante selbst, damit der Uebergang nicht
    mitgemittelt wird. `drin` ist +1, wenn das Bauteil rechts der Kante
    liegt, und -1, wenn links.

    Stationen, an denen der Streifen INNERHALB der Kante nicht mehr zum
    Bauteil passt, fallen heraus: Dort liegt das Balkenende, und hinter dem
    Ende misst man Pflaster gegen Pflaster. Ohne diese Bedingung meldet jede
    Aufnahme mit einem Balkenende eine blinde Stelle, die es nicht gibt.

    Zurueck kommen Median, der Anteil blinder Stellen und die Zahl der
    verwerteten Stationen. Nicht der kleinste Einzelwert: Der geht gegen
    Null, sobald der Hintergrund an EINER Stelle zufaellig so hell ist wie
    das Holz, und eine einzelne Stelle bringt die Kantengerade nicht aus der
    Spur - ein Viertel der Laenge schon.
    """
    innen, aussen = [], []
    for k in range(len(ys)):
        x = a0 + steigung * ys[k]
        i = int(round(x))
        s_in = schnitt(roh[k], i + drin * abstand, i + drin * (abstand + breite))
        s_au = schnitt(roh[k], i - drin * abstand, i - drin * (abstand + breite))
        if s_in is None or s_au is None:
            continue
        innen.append(s_in); aussen.append(s_au)
    if len(innen) < 8:
        return float("nan"), float("nan"), 0
    innen = np.asarray(innen); aussen = np.asarray(aussen)
    m = float(np.median(innen))
    gut = np.abs(innen - m) < 0.45 * max(m, 1.0)
    if gut.sum() < 6:
        gut = np.ones(len(innen), bool)
    w = np.abs(innen - aussen)[gut]
    return float(np.median(w)), float((w < SCHWACH).mean()), int(gut.sum())


def faserscheiben(a, i, j, pxmm_arbeit, scheibe_mm=15.0):
    """Faserausrichtung in Querscheiben des gefundenen Bandes.

    Die Frage, die damit beantwortet wird: Steht im Band ueberall dasselbe
    Material, oder reicht es in etwas hinein, das nur daneben liegt?

    Gewachsenes Holz hat fast nur Struktur QUER zur Faser; laengs ist es
    glatt. Eine Scheibe des Bandes, in der dieses Verhaeltnis einbricht, ist
    kein Laengsholz: ein quer liegendes Auflager, ein Bock, ein Massstab mit
    seiner Querteilung, Pflaster.

    Noetig geworden an der Reihe 261022: Der Balken lag auf Kanthoelzern, und
    weil die auch aus Holz sind, zog die Bandsuche die Untergrenze bis unter
    die Kanthoelzer - 256 statt 223 mm, ein Massstabsfehler von 15 %. Als
    SUCHKANAL taugt die Faserrichtung dafuer nicht (geprueft: sie verschiebt
    das Ergebnis kaum und verschlechtert andere Reihen); als PRUEFUNG des
    fertigen Bandes trennt sie sauber.
    """
    g = a.mean(axis=2)
    L = g.shape[0]
    gy, gx = np.gradient(g)
    y0, y1 = int(0.12 * L), int(0.88 * L)
    n = max(6, int((j - i) / max(3.0, scheibe_mm * pxmm_arbeit)))
    aus = []
    for k in range(n):
        x0 = int(i + (j - i) * k / n)
        x1 = max(x0 + 2, int(i + (j - i) * (k + 1) / n))
        q = np.abs(gx[y0:y1, x0:x1]).mean()
        l = np.abs(gy[y0:y1, x0:x1]).mean()
        aus.append(q / (l + 1e-6))
    return np.asarray(aus)


def randscheibe(s):
    """Schwaechere der beiden Randscheiben, bezogen auf den Median."""
    med = float(np.median(s))
    if med < 1e-6:
        return 1.0, 0
    lo, hi = float(s[0]) / med, float(s[-1]) / med
    return min(lo, hi), (1 if lo <= hi else 2)


def teilung_suchen(a, i, j, pxmm_arbeit, soll_mm=10.0):
    """Maßstab im Bild: regelmaessige Teilung ausserhalb des Bandes finden.

    Ein Zollstock oder Bandmass im Bild traegt eine Teilung von bekanntem
    Abstand. Ihre Periode laesst sich ueber die Autokorrelation bestimmen -
    voellig unabhaengig von der Bandbreite, die sonst das einzige Massnormal
    ist. Damit laesst sich zum ersten Mal pruefen, statt nur zu glauben.

    Gesucht wird in Streifen NEBEN dem Bauteil, nicht darauf: Auf der Flaeche
    wuerde die Jahrringstreifung mitreden.

    Wichtig fuer die Auswertung: Der Massstab muss in der BAUTEILEBENE
    liegen. Bei 360 mm Aufnahmeabstand sind 5 mm Tiefenversatz schon 1.4 %
    Massstabsfehler. Liegt er auf der Oberseite statt auf der Flaeche, misst
    man den Fehler des Massstabs, nicht den des Verfahrens.
    """
    g = a.mean(axis=2)
    L, Q = g.shape
    breite = max(6, int(18 * pxmm_arbeit))
    bester = None
    for seite, anfang, richtung in ((1, i, -1), (2, j, +1)):
        for abstand_mm in (4, 12, 24, 40):
            x = int(anfang + richtung * abstand_mm * pxmm_arbeit)
            x0, x1 = (x - breite, x) if richtung < 0 else (x, x + breite)
            x0 = max(0, x0); x1 = min(Q, x1)
            if x1 - x0 < 5:
                continue
            v = g[int(0.10 * L):int(0.90 * L), x0:x1].mean(axis=1)
            lag, guete = _periode(v, soll_mm * pxmm_arbeit)
            if lag and guete >= 0.40 and (bester is None or guete > bester[1]):
                bester = (lag, guete, seite, abstand_mm)
    return bester


def _periode(v, erwartet_px):
    """Staerkster Autokorrelationsgipfel nahe der erwarteten Periode.

    Das Glaettungsfenster fuer den Trendabzug muss bei gut dem Doppelten der
    gesuchten Periode liegen. Mit einem langen Fenster bleibt grossflaechige
    Helligkeitsstruktur im Signal, und die Autokorrelation meldet auch fuer
    Pflaster und Kanthoelzer Guetewerte um 0.7 - gemessen an der Reihe
    261022, wo die Probe deshalb das Pflaster statt des Zollstocks abgriff
    und 10.0 statt 16.0 Px/mm lieferte. Mit dem kurzen Fenster bleibt vom
    Pflaster 0.14 uebrig und vom Zollstock 0.51.
    """
    k = int(max(31, min(len(v) // 4, 2.2 * erwartet_px))) | 1
    basis = np.convolve(np.pad(v, k // 2, mode="edge"), np.ones(k) / k, "valid")
    r = v - basis
    if r.std() < 1e-6 or len(r) < 60:
        return None, 0.0
    r = (r - r.mean()) / r.std()
    ak = np.correlate(r, r, "full")[len(r) - 1:]
    ak /= ak[0]
    lo = max(4, int(0.60 * erwartet_px))
    hi = min(len(ak) - 1, int(1.60 * erwartet_px) + 1)
    if hi <= lo + 2:
        return None, 0.0
    f = ak[lo:hi]
    k = int(np.argmax(f)) + lo
    return float(k), float(ak[k])


def naeher_text(lo, hi, Q_A, L_A, fak, hoehe_mm):
    """Wie viel naeher muss der Fotograf heran? Als Faktor, nicht in Metern.

    Den Aufnahmeabstand kennt die Pruefung nicht - wohl aber das Verhaeltnis:
    Aufloesung und Abstand sind umgekehrt proportional. 'Auf 70 % des
    bisherigen Abstands' ist am Bauteil genauso befolgbar wie eine Zahl in
    Zentimetern und setzt nichts voraus.

    Gerechnet wird gegen die KURZE Bildachse, weil das Bauteil quer darauf
    gehoert - siehe den Hinweis zur Haltung des Handys.
    """
    grund = ("Naeher herangehen. Der gewohnte Abstand von der breiten Seite "
             "reicht fuer eine schmalere Flaeche nicht.")
    if not hoehe_mm:
        return grund
    kurz = min(Q_A, L_A) * fak
    pxmm_soll = 0.30 * kurz / hoehe_mm
    pxmm_ist = (hi - lo) / hoehe_mm
    if pxmm_ist >= 0.95 * pxmm_soll:
        return grund
    return (f"Naeher herangehen, auf etwa "
            f"{pxmm_ist / pxmm_soll * 100:.0f} % des bisherigen Abstands - "
            f"dann fuellt das Bauteil rund 30 % der kurzen Bildseite. Der "
            f"gewohnte Abstand von der breiten Seite reicht fuer eine "
            f"schmalere Flaeche nicht; bei halber Flaechenhoehe gehoert "
            f"auch der Abstand etwa halbiert.")


def faserwert(a, x0, x1):
    """Faserausrichtung quer/laengs in einem Querstreifen."""
    g = a.mean(axis=2)
    L, Q = g.shape
    x0 = max(0, int(x0)); x1 = min(Q, int(x1))
    if x1 - x0 < 3:
        return float("nan")
    gy, gx = np.gradient(g)
    y0, y1 = int(0.12 * L), int(0.88 * L)
    return float(np.abs(gx[y0:y1, x0:x1]).mean()
                 / (np.abs(gy[y0:y1, x0:x1]).mean() + 1e-6))


def band_waehlen(pfade, dreh, teiler, stat, kandidaten, HOEHE, fak,
                 mitte, tol, hoechstens=4):
    """Welche der beiden Bandbestimmungen ist die richtige?

    Zwei Proben, die in ENTGEGENGESETZTE Richtungen greifen:

      innen  - die aeusserste Scheibe des Bandes muss noch Laengsholz sein.
               Faellt sie ab, reicht das Band ueber das Bauteil hinaus.
      aussen - der Streifen DICHT NEBEN dem Band darf kein Laengsholz mehr
               sein. Ist er es doch, hoert das Bauteil dort nicht auf und
               das Band ist zu klein.

    Die zweite Probe ist noetig, weil die erste "zu klein" grundsaetzlich
    nicht sehen kann: Ein zu schmales Band liegt vollstaendig im Holz und ist
    perfekt homogen. Gemessen an vier Reihen mit acht Kandidaten trennt
    'aussen/innen ueber 1.0' alle acht richtig - von 66 bis 96 % fuer die
    richtigen Baender und 123 bis 330 % fuer die falschen.
    """
    # Vorfilter: Ein Kandidat, der nur einen Bruchteil des Bildes einnimmt,
    # wird gar nicht erst geprueft. Die Faserproben degenerieren dort - bei
    # einem Band von 45 Px sind "Kern" und "Nachbarstreifen" wenige Pixel
    # breit und ihr Verhaeltnis bedeutet nichts mehr. An der Reihe
    # 261022/Versuch 1 lieferte die freie Suche so ein Band (1.60 statt
    # 16.0 Px/mm) und waere ohne diesen Filter sogar gewaehlt worden.
    Q = len(stat[0][0][0])
    gueltig = {k: v for k, v in kandidaten.items()
               if v and 0.12 * Q <= v <= 0.72 * Q}
    if not gueltig:
        gueltig = {k: v for k, v in kandidaten.items() if v}
    if len(gueltig) < 2 or not HOEHE:
        return list(gueltig.values())[0]
    schritt = max(1, len(pfade) // hoechstens)
    proben = list(range(0, len(pfade), schritt))[:hoechstens]
    bilder = []
    for n in proben:
        with z.lade(pfade[n], teiler, dreh) as im:
            bilder.append((n, np.asarray(im, np.float32)))

    sag("")
    sag("  Zwei unabhaengige Bandbestimmungen:")
    bewertung = {}
    for name, erw in gueltig.items():
        d_eng = np.arange(int(erw * 0.90), int(erw * 1.10) + 1)
        w = max(4, int(15.0 * erw / HOEHE))
        innen, aussen = [], []
        for n, a in bilder:
            b = z.bandsuche(stat[n][0], d_eng, mitte, tol)
            if not b:
                continue
            _, i, j = b
            kern = faserwert(a, i + 2 * w, j - 2 * w)
            if not np.isfinite(kern) or kern < 1e-6:
                continue
            s = faserscheiben(a, i, j, erw / HOEHE)
            innen.append(randscheibe(s)[0])
            nachbar = [faserwert(a, i - w - 2, i - 2),
                       faserwert(a, j + 2, j + w + 2)]
            nachbar = [v for v in nachbar if np.isfinite(v)]
            if nachbar:
                aussen.append(max(nachbar) / kern)
        i_med = float(np.median(innen)) if innen else 0.0
        a_med = float(np.median(aussen)) if aussen else 9.9
        fehler = []
        if i_med < 0.70:
            fehler.append("greift darueber hinaus")
        if a_med > 1.05:
            fehler.append("zu klein")
        bewertung[name] = (len(fehler), i_med, a_med, fehler)
        sag(f"    {name:10} {erw*fak/HOEHE:5.2f} Px/mm   "
            f"Randscheibe innen {i_med*100:3.0f} %, "
            f"Nachbarstreifen {a_med*100:3.0f} %"
            + ("   " + ", ".join(fehler) if fehler else "   schluessig"))

    namen = sorted(gueltig, key=lambda k: (bewertung[k][0],
                                           0 if k == "Parallaxe" else 1))
    gewaehlt = namen[0]
    werte = [v * fak / HOEHE for v in gueltig.values()]
    spanne = (max(werte) - min(werte)) / max(np.median(werte), 1e-9) * 100
    n = note(spanne, S_BANDSTREIT, True)
    sag(f"    Die beiden weichen um {spanne:4.1f} % voneinander ab   "
        f"{ZEICHEN[n]}   gewaehlt: {gewaehlt}")
    if n:
        mangel(n == 2, "Massstab ist nicht eindeutig",
               f"Die freie Bandsuche und die Suche im Fenster der Parallaxe "
               f"kommen auf Massstaebe, die um {spanne:.0f} % auseinander "
               f"liegen ({' und '.join(f'{v:.2f}' for v in sorted(werte))} "
               f"Px/mm). Solange das so ist, ist JEDES Mass im fertigen "
               f"Streifen um diesen Betrag unsicher.",
               "Dem Bauteil mehr freien Hintergrund geben: nichts "
               "Laengsholzartiges dicht an den Kanten, und das Bauteil nicht "
               "weiter als etwa die halbe Bildbreite fuellen. Ein Massstab "
               "flach auf der Flaeche entscheidet die Frage sofort.")
    return gueltig[gewaehlt]


def abschnitt_band(pfade, dreh, teiler, bw, mi, fak, PXMM, HOEHE, hoechstens=6):
    """Haelt das gefundene Band wirklich nur das Bauteil - und stimmt der
    Massstab?

    Zwei voneinander unabhaengige Proben an denselben Aufnahmen. Gelesen wird
    dafuer ein zweites Mal, aber nur ein paar Bilder; das kostet Sekunden und
    beantwortet die Frage, an der in der Reihe 261022 alles haengt.
    """
    sag("")
    sag("3b - Haelt das Band nur das Bauteil?")
    sag("------------------------------------")
    if not PXMM:
        sag("  uebersprungen - ohne Flaechenhoehe kein Massstab.")
        return
    pxmm_a = PXMM / fak
    schritt = max(1, len(pfade) // hoechstens)
    proben = list(range(0, len(pfade), schritt))[:hoechstens]
    schwach, teilungen = [], []
    for n in proben:
        with z.lade(pfade[n], teiler, dreh) as im:
            a = np.asarray(im, np.float32)
        i = mi[n] - bw[n] / 2.0
        j = mi[n] + bw[n] / 2.0
        s = faserscheiben(a, i, j, pxmm_a)
        anteil, seite = randscheibe(s)
        marke = "  <-- reicht ueber das Bauteil hinaus" if anteil < 0.70 else ""
        sag(f"  {pfade[n].name:18} Randscheibe Kante {seite}: "
            f"{anteil*100:3.0f} % der Faserauspraegung im Band{marke}")
        if anteil < 0.70:
            schwach.append((pfade[n].name, seite, anteil))
        # Die Teilung eines Massstabs ist fein: 10 mm sind bei Teiler 8 nur
        # gut 20 Px, und die Millimeterstriche liegen dann bei 2 Px. Dabei
        # greift die Autokorrelation nicht die Teilung, sondern den
        # Aliasrest ab (gemessen: 96 Px in JEDER Aufnahme, ein Artefakt der
        # JPEG-Bloecke). Fuer diese eine Probe wird darum feiner gelesen.
        if len(teilungen) < 3:
            with z.lade(pfade[n], TEILER_MASS, dreh) as im:
                af = np.asarray(im, np.float32)
            v = fak / TEILER_MASS
            t = teilung_suchen(af, i * v, j * v, pxmm_a * v)
            if t and t[1] > 0.25:
                teilungen.append((pfade[n].name, t, TEILER_MASS))

    # Eine einzelne Aufnahme genuegt nicht. An einem Bauteilende, an einem
    # Bock oder dort, wo ein Brett davorlehnt, bricht die Faserauspraegung
    # auch einmal zu Recht ein; die gelungene Reihe Seite A hat genau einen
    # solchen Fall. Erst ZWEI Aufnahmen sind ein Muster.
    if len(schwach) == 1:
        sag("")
        sag(f"  ok   Nur {schwach[0][0]} faellt heraus - eine einzelne "
            f"Aufnahme ist kein Muster.")
    if len(schwach) >= 2:
        n = 2 if len(schwach) > 0.25 * len(proben) else 1
        sag("")
        sag(f"  {ZEICHEN[n]} In {len(schwach)} von {len(proben)} geprueften "
            f"Aufnahmen reicht das Band in Material,")
        sag("       das nicht laengs gefasert ist - Auflager, Bock oder "
            "Massstab.")
        mangel(n == 2, "Band greift ueber das Bauteil hinaus",
               f"In {len(schwach)} von {len(proben)} geprueften Aufnahmen "
               f"faellt die Faserausrichtung in der aeussersten Scheibe des "
               f"Bandes unter 70 % des Bandmedians. Dort steht kein "
               f"Laengsholz mehr, sondern etwas, das nur daneben liegt. Der "
               f"Massstab wird dadurch zu gross und ALLE Masse zu klein.",
               "Unter der Bauteilkante darf kein Holz liegen: Bauteil ueber "
               "die Boecke ueberstehen lassen, Auflager schmal halten und "
               "nichts zusaetzlich darunterlegen. Muss doch etwas darunter, "
               "dann HELLER und BLASSER als das Bauteil - nicht dunkler und "
               "kraeftiger. Ein Massstab gehoert flach auf die Flaeche, "
               "nicht auf die Kante.",
               [f"{n_} (Kante {s_}, {a_*100:.0f} %)" for n_, s_, a_ in schwach])
    elif proben:
        sag("")
        sag("  ok   Das Band ist auf seiner ganzen Breite laengs gefasert.")

    sag("")
    werte = []
    for name, (lag, guete, seite, abstand), tm in teilungen:
        pxmm_t = lag / 10.0 * tm
        werte.append(pxmm_t)
        sag(f"  Massprobe {name:18} Teilung {lag*tm:6.1f} Px = "
            f"{pxmm_t:5.2f} Px/mm   (Guete {guete:.2f}, "
            f"{abstand} mm neben Kante {seite})")
    # Ein einzelner Fund wird verworfen, und uneinige Funde auch. Regel-
    # maessige Muster gibt es neben einem Bauteil reichlich: Pflasterfugen,
    # Wellblech, Trapezdach. In der Reihe Seite C meldete EIN Bild eine
    # "Teilung", die auf 12.20 statt 8.59 Px/mm gefuehrt haette - um 30 %
    # daneben, und es liegt dort gar kein Massstab. Zwei Aufnahmen, die sich
    # auf besser als 12 % einig sind, kommen durch ein Pflaster nicht
    # zustande.
    if len(werte) < 2 or (max(werte) - min(werte)) / np.median(werte) > 0.12:
        if werte:
            sag("  -> verworfen: " + ("nur ein Fund" if len(werte) < 2 else
                "die Funde sind sich nicht einig") + ", das kann auch ein "
                "Pflaster oder eine Wand sein.")
        else:
            sag("  Massprobe: kein Massstab neben dem Bauteil gefunden.")
        sag("  (Ein Zollstock im Bild - flach auf der Flaeche, 300 bis "
            "500 mm, an zwei")
        sag("   bis drei Stellen - macht aus der Bauteillaenge eine "
            "pruefbare Groesse.)")
        return
    m = float(np.median(werte))
    abw = (PXMM / m - 1.0) * 100
    n = note(abs(abw), (1.5, 4.0), True)
    sag(f"  Massstab aus dem Band {PXMM:5.2f} Px/mm gegen Teilung "
        f"{m:5.2f} Px/mm: {abw:+5.1f} %   {ZEICHEN[n]}")
    if HOEHE:
        sag(f"  -> Bauteilhoehe waere {HOEHE*PXMM/m:6.1f} statt "
            f"{HOEHE:.0f} mm")
    if n:
        mangel(n == 2, "Massstab und Teilung widersprechen sich",
               f"Der aus der Bauteilhoehe abgeleitete Massstab weicht um "
               f"{abw:+.1f} % von der Teilung des Massstabs im Bild ab. Einer "
               f"von beiden ist falsch - und auf die ganze Laenge gerechnet "
               f"sind das erhebliche Betraege.",
               "Zuerst pruefen, ob der Massstab wirklich in der Bauteilebene "
               "liegt: Bei 360 mm Aufnahmeabstand sind schon 5 mm "
               "Tiefenversatz 1.4 % Fehler, und auf der Oberseite statt auf "
               "der Flaeche ist er leicht 15 mm zurueck. Liegt er richtig, "
               "dann stimmt das Band nicht - siehe die Faserprobe darueber.")


def rest_grenzen(kanten, pxmm):
    """Ab welcher Abweichung von der Kantengeraden ist eine Aufnahme schlecht?

    Nicht absolut. Ein gesaegter Vollholzbalken hat KRUMME Kanten, und was
    dort als "Abweichung von der Geraden" erscheint, ist zum guten Teil das
    Bauteil selbst: Im fertigen Streifen der Reihe 261022/Versuch 2 wandert
    die Bauteilkante langwellig um 4.1 mm - bei BSH (Seite A) sind es 0.6 mm.
    Eine feste Schwelle von 8 mm erklaerte darum drei brauchbare Aufnahmen
    jenes Versuchs fuer unbrauchbar, und die Reihe fiel faelschlich durch,
    obwohl sie sich anschliessend mit 0.21 mm Nahtversatz zusammensetzen
    liess.

    Richtig ist beides zusammen: ein absoluter Boden fuer sauber gesaegte
    Bauteile, und darueber ein Vielfaches dessen, was die Reihe SELBST als
    Grundrauschen zeigt. Eine Aufnahme muss aus ihrer eigenen Reihe
    herausfallen, nicht aus einer Tabelle.
    """
    werte = [k["rest"] / pxmm for k in kanten if k]
    if not werte or not pxmm:
        return S_REST
    med = float(np.median(werte))
    return (max(S_REST[0], 1.8 * med), max(S_REST[1], 3.0 * med))


def bild_note(k, pxmm, grenzen=None):
    """Urteil ueber EINE Aufnahme, samt Begruendung.

    Je Aufnahme statt je Reihe, weil eine Reihe nicht gleichmaessig gut oder
    schlecht ist. Reihe Seite C ist das Lehrbeispiel: Die Aufnahmen 2291 bis
    2302 sind unbrauchbar (Kantenkontrast 4 bis 17 Graustufen,
    Kantengerade 4 bis 18 mm daneben), die Aufnahmen 2305 bis 2314 dagegen
    einwandfrei (57 bis 120 Graustufen, 0.8 bis 7 mm). Der Median ueber die
    Reihe sagt 50 und 37 Graustufen - er verdeckt den Ausfall vollstaendig.
    """
    if k is None:
        return 2, ["keine Kanten gefunden"]
    gew, grund = 0, []
    for nr in (1, 2):
        w = k[f"k{nr}"][0]
        n = note(w, S_KONTRAST_MED)
        if n:
            gew = max(gew, n)
            grund.append(f"Kante {nr} nur {w:.0f} Graustufen")
    if pxmm:
        r = k["rest"] / pxmm
        n = note(r, grenzen or S_REST, True)
        if n:
            gew = max(gew, n)
            grund.append(f"Kantengerade {r:.1f} mm daneben")
    n = note(abs(k["neigung"]), S_NEIGUNG, True)
    if n:
        gew = max(gew, n)
        grund.append(f"{abs(k['neigung']):.1f} Grad schraeg")
    # Die Zahl auswertbarer Laengsstationen zaehlt hoechstens als Abstrich,
    # nie als Ausfall: Sie sinkt voellig zu Recht in den Aufnahmen, in denen
    # ein Balkenende liegt - dort IST auf einem Teil der Bildhoehe kein
    # Bauteil. Als Ausfallgrund gewertet, erklaerte sie die beiden letzten
    # Aufnahmen der gelungenen Reihe Seite A zu einem Kettenbruch.
    if note(k["nst"] / max(k["nges"], 1), S_STATIONEN):
        gew = max(gew, 1)
        grund.append(f"nur {k['nst']}/{k['nges']} Stationen")
    return gew, grund


def laengster_lauf(schlecht, n):
    """Laengste zusammenhaengende Strecke unbrauchbarer Aufnahmen.

    Darauf kommt es an, nicht auf die Anzahl: Eine einzelne unbrauchbare
    Aufnahme laesst sich ueberspringen - bei 65 % Ueberlappung haben auch
    die Nachbarn links und rechts davon noch gut 30 % gemeinsam. ZWEI
    aufeinanderfolgende trennen die Kette, und alles dahinter kann nicht
    mehr angeschlossen werden. Genau so ist Reihe Seite C auseinander-
    gefallen: 17 von 30 Aufnahmen blieben verbunden.
    """
    m = np.zeros(n, bool)
    m[list(schlecht)] = True
    best, lauf, anf, besta = 0, 0, 0, 0
    for i in range(n + 1):
        if i < n and m[i]:
            if lauf == 0:
                anf = i
            lauf += 1
        else:
            if lauf > best:
                best, besta = lauf, anf
            lauf = 0
    return best, besta


def kanten_messen(stat, roh, erw, mitte, fak, hoehe_mm):
    """Je Aufnahme: Neigung, Rest der Kantengeraden, Kontrast beider Kanten.

    Der Kontrast wird nur auf dem Laengsabschnitt gemessen, auf dem das
    Bauteil ueberhaupt im Bild ist (y0..y1 aus der Kantenmessung). Sonst
    liefert jede Aufnahme, in der ein Balkenende liegt, eine schwaechste
    Stelle von 0 Graustufen - naemlich dort, wo gar kein Balken mehr ist.
    """
    erg = z.stationen_messen(stat, erw, mitte, hoehe_mm or 1.0, fak)
    if erg is None:
        return None
    a1, b1, a2, b2 = erg["gerade"]
    ys = np.asarray(stat[1], float)
    drin = (ys * fak >= erg["y0"] - 1e-6) & (ys * fak <= erg["y1"] + 1e-6)
    if drin.sum() < 6:
        drin = np.ones(len(ys), bool)
    abstand = max(3, int(0.02 * erw))
    breite = max(5, int(0.08 * erw))
    k1 = kontrast_einer_kante(roh[drin], ys[drin], a1 / fak, b1, +1,
                              abstand, breite)
    k2 = kontrast_einer_kante(roh[drin], ys[drin], a2 / fak, b2, -1,
                              abstand, breite)
    return dict(neigung=float(np.degrees(np.arctan((b1 + b2) / 2.0))),
                rest=erg["rest"], nst=erg["nst"], nges=erg["nges"],
                k1=k1, k2=k2, anteil_laengs=float(drin.mean()))


# --------------------------------------------------------------- Ablauf ---

def hoehe_bestimmen(ordner, vorgabe):
    if vorgabe:
        return float(vorgabe), "Befehlszeile"
    datei = ordner / "bauteil.json"
    if datei.exists():
        try:
            d = json.loads(datei.read_text(encoding="utf-8"))
            if d.get("flaeche_hoehe_mm"):
                return float(d["flaeche_hoehe_mm"]), "bauteil.json"
        except Exception:
            pass
    return None, None


def main() -> int:
    p = argparse.ArgumentParser(
        description="Prueft eine Bildreihe fuer die Panoramaaufnahme.")
    p.add_argument("ordner", type=Path)
    p.add_argument("--hoehe-mm", type=float, default=None,
                   help="Hoehe der fotografierten Flaeche in mm")
    p.add_argument("--teiler", type=int, default=8,
                   help="Verkleinerung beim Lesen (Vorgabe 8)")
    p.add_argument("--stationen", type=int, default=36)
    p.add_argument("--bericht", type=Path, default=None)
    a = p.parse_args()

    if not a.ordner.is_dir():
        print(f"Kein Ordner: {a.ordner}")
        return 2
    pfade = z.bilder_finden(a.ordner)
    if len(pfade) < 3:
        print(f"Mindestens drei JPEG-Dateien noetig, gefunden: {len(pfade)}")
        print("Hinweis: HEIC wird nicht gelesen - in der Kamera-App auf JPEG "
              "stellen.")
        return 2

    HOEHE, quelle = hoehe_bestimmen(a.ordner, a.hoehe_mm)
    sag(f"Bildreihe: {a.ordner}")
    sag(f"{len(pfade)} Aufnahmen, Teiler {a.teiler}" +
        (f", Flaechenhoehe {HOEHE:g} mm ({quelle})" if HOEHE else
         ", Flaechenhoehe unbekannt - keine Angaben in mm"))
    sag("")

    abschnitt_kamera(pfade)

    # --- 2  Lage des Bauteils im Bild -----------------------------------
    sag("")
    sag("2 - Lage des Bauteils im Bild")
    sag("-----------------------------")
    dreh = z.achse_bestimmen(pfade)
    sag(f"  Bauteil laeuft im Rohbild laengs der "
        f"{'Spalten' if dreh else 'Zeilen'}")
    # Arbeitskoordinaten: x laeuft QUER zum Bauteil, y LAENGS. `fak` rechnet
    # vom verkleinerten Messbild auf das Originalbild zurueck und wird - wie
    # im Zusammenbau - an der QUERACHSE gebildet.
    with z.lade(pfade[0], 1, dreh) as im:
        W_V, L_V = im.size
    with z.lade(pfade[0], a.teiler, dreh) as im:
        Q_A, L_A = im.size
    fak = W_V / float(Q_A)

    bew = z.band_aus_bewegung(pfade, dreh, teiler=max(8, a.teiler))
    band = None
    if bew is None:
        sag("  ROT   Die Parallaxe findet das Bauteil nicht.")
        mangel(True, "Bauteil nicht auffindbar",
               "Zwischen den Aufnahmen hebt sich kein zusammenhaengender "
               "Bereich durch staerkere Bewegung vom Hintergrund ab.",
               "Haeufigste Ursache: zu kleiner Vorschub (die Kamera stand "
               "fast still) oder das Bauteil liegt direkt am Hintergrund. "
               "Mit groesserem Vorschub und Abstand zum Hintergrund "
               "wiederholen.")
    else:
        lo, hi, n = bew
        band = (lo / fak, hi / fak)          # Rohspalten -> Arbeitsbild
        anteil = (hi - lo) / (Q_A * fak) * 100
        sag(f"  Bauteil quer im Bild von {lo/ (Q_A*fak)*100:4.1f} % bis "
            f"{hi/(Q_A*fak)*100:4.1f} % der Bildbreite  "
            f"(aus {n} Bildpaaren)")
        n_oben = note(anteil, S_ANTEIL_OBEN, True)
        sag(f"  Bauteilanteil an der Bildbreite  {anteil:5.1f} %   "
            f"{ZEICHEN[max(note(anteil, S_ANTEIL), n_oben)]}")
        if n_oben:
            mangel(n_oben == 2, "Bauteil fuellt das Bild zu weit aus",
                   f"Das Bauteil fuellt {anteil:.0f} % der Bildbreite. "
                   f"Erkannt wird es daran, dass es sich von dem "
                   f"unterscheidet, was beidseits daneben liegt - und dafuer "
                   f"bleibt dann kein Rand mehr. Ueber {S_ANTEIL_OBEN[1]:.0f} "
                   f"% findet die Bandsuche es gar nicht mehr.",
                   "Einen Schritt zuruecktreten. Zwischen 30 und 55 % der "
                   "Bildbreite ist der gute Bereich: genug Aufloesung und "
                   "noch genug Hintergrund zum Vergleichen.")
        elif note(anteil, S_ANTEIL):
            mangel(note(anteil, S_ANTEIL) == 2, "Bauteil zu klein im Bild",
                   f"Das Bauteil fuellt nur {anteil:.0f} % der Bildbreite "
                   f"(Ziel 35 %, Untergrenze {S_ANTEIL[1]:.0f} %). Auf "
                   f"dieser Flaeche muessen sich zwei Aufnahmen "
                   f"wiederfinden, und die Ausbeute schrumpft schneller als "
                   f"das Band: Bei halbem Band blieb in der Vergleichsreihe "
                   f"ein Siebtel der Punktpaare uebrig, die Kette riss und "
                   f"die Ausgleichung lief in eine unmoegliche Lage.",
                   naeher_text(lo, hi, Q_A, L_A, fak, HOEHE))

        # Liegt der Querschnitt auf der LANGEN Bildachse, wird zweimal
        # verschenkt: Das Bauteil fuellt weniger vom Bild, und je Aufnahme
        # wird weniger Laenge erfasst. Beides kehrt sich um, wenn das Handy
        # um 90 Grad gedreht wird - ohne einen Schritt zu gehen.
        if Q_A > L_A:
            gewinn = Q_A / float(L_A)
            pm = (hi - lo) / HOEHE if HOEHE else None
            sag("  gelb  Bauteilquerschnitt liegt auf der LANGEN Bildachse "
                "- Handy um 90 Grad")
            if pm:
                sag(f"        drehen: Bauteilanteil {anteil:.0f} -> "
                    f"{anteil*gewinn:.0f} %, erfasste Laenge je Aufnahme "
                    f"{L_A*fak/pm:.0f} -> {Q_A*fak/pm:.0f} mm")
            else:
                sag(f"        drehen: Bauteilanteil {anteil:.0f} -> "
                    f"{anteil*gewinn:.0f} %, {gewinn:.2f}-fache Laenge "
                    f"je Aufnahme")
            mangel(False, "Handy falsch herum gehalten",
                   f"Der Querschnitt des Bauteils liegt auf der langen "
                   f"Bildachse. Um 90 Grad gedreht fuellt das Bauteil "
                   f"{anteil*gewinn:.0f} statt {anteil:.0f} % der Bildbreite "
                   f"und jede Aufnahme erfasst die {gewinn:.2f}-fache "
                   f"Bauteillaenge - beides ohne einen Schritt zu gehen.",
                   "Handy so halten, dass die LANGE Bildseite laengs am "
                   "Bauteil liegt und die kurze quer darueber.",
                   (), "Hinweis")

    # --- 3/4  Reihe einlesen ---------------------------------------------
    sag("")
    sag("      Aufnahmen werden gelesen ...")
    stat, roh, textur, faser, farbe, versatz = reihe_lesen(
        pfade, dreh, a.teiler, band, a.stationen)

    # Bandbreite auf ZWEI unabhaengigen Wegen, und dann der Vergleich.
    #
    # Weg 1 sucht frei im ganzen Bild, Weg 2 im Fenster der Parallaxe. Keiner
    # von beiden ist zuverlaessig: An der Reihe 261022/Versuch 1 lieferte der
    # freie Weg 1.60 statt 16.0 Px/mm, an Versuch 2 der Parallaxenweg 13.7
    # statt 15.6. Dass sie sich EINIG sind, ist darum die eigentliche
    # Aussage - bei Seite A auf 1.2 % genau, bei Versuch 2 auf 14 %, bei
    # Seite C auf 27 %.
    profile = [s[0] for s in stat]
    erw_frei, _ = z.bandbreite_der_reihe(
        profile, np.arange(int(0.06 * Q_A), int(0.72 * Q_A), 2))
    if band is not None:
        mitte = (band[0] + band[1]) / 2.0
        d0 = band[1] - band[0]
        erw_par, _ = z.bandbreite_der_reihe(
            profile, np.arange(max(8, int(d0 * 0.75)), int(d0 * 1.30) + 1, 2),
            mitte, 0.30 * d0)
        tol = 0.30 * d0
    else:
        mitte, tol, erw_par = None, None, None
    erw = band_waehlen(pfade, dreh, a.teiler, stat,
                       {"frei": erw_frei, "Parallaxe": erw_par},
                       HOEHE, fak, mitte, tol)
    PXMM = (erw * fak / HOEHE) if HOEHE else None

    # Band je Aufnahme nachmessen. Freihand schwankt der Abstand um +-9 %,
    # und mit der Reihenbreite allein verliert die Kantensuche in einzelnen
    # Aufnahmen das Band - der Zusammenbau macht es genauso.
    d_eng = np.arange(int(erw * 0.90), int(erw * 1.10) + 1)
    bw, mi = [], []
    for s in stat:
        b = z.bandsuche(s[0], d_eng, mitte, tol)
        bw.append(b[2] - b[1] if b else erw)
        mi.append((b[1] + b[2]) / 2.0 if b
                  else (mitte if mitte is not None else Q_A / 2.0))
    tol_bild = tol if tol is not None else 0.30 * erw
    sag("")
    sag("3 - Kanten des Bauteils")
    sag("-----------------------")
    sag(f"  Bandbreite, auf die sich alle Aufnahmen einigen: {erw} Px im "
        f"Messbild" + (f" = {PXMM:.2f} Px/mm im Original" if PXMM else ""))
    if PXMM:
        sag(f"  Aufloesung  {PXMM:5.2f} Px/mm   {ZEICHEN[note(PXMM, S_PXMM)]}")
        if note(PXMM, S_PXMM):
            mangel(note(PXMM, S_PXMM) == 2, "Aufloesung zu grob",
                   f"{PXMM:.1f} Pixel je mm (Ziel 8, mindestens 6). Ein "
                   f"Merkmal von 2 mm ist dann {PXMM*2:.0f} Px gross.",
                   "Naeher herangehen.")
    sag("")
    sag("  Kante 1 und Kante 2 sind die beiden Laengskanten des Bauteils.")
    sag("  Welche davon im Bild oben liegt, haengt von der Haltung des "
        "Handys ab;")
    sag("  fuer die Pruefung zaehlt nur, dass BEIDE Kontrast haben.")
    sag("")
    sag("  Aufnahme            Neig.   Rest   Stationen  Kontr. K1 / K2   "
        "Urteil")

    kanten = [kanten_messen(stat[i], roh[i], bw[i], mi[i], fak, HOEHE)
              for i in range(len(pfade))]
    grenzen = rest_grenzen(kanten, PXMM)
    if PXMM and grenzen != S_REST:
        sag(f"  Die Kanten dieses Bauteils sind selbst krumm "
            f"(Mittel {np.median([k['rest']/PXMM for k in kanten if k]):.1f} "
            f"mm); eine Aufnahme gilt")
        sag(f"  darum erst ab {grenzen[0]:.1f} mm als auffaellig und ab "
            f"{grenzen[1]:.1f} mm als unbrauchbar.")
        sag("")

    noten, gruende = [], []
    for i, p in enumerate(pfade):
        k = kanten[i]
        gew, grund = bild_note(k, PXMM, grenzen)
        noten.append(gew); gruende.append(grund)
        if k is None:
            sag(f"  {p.name:18}  KEINE KANTEN GEFUNDEN               "
                f"       {ZEICHEN[gew]}")
            continue
        rest_mm = k["rest"] / PXMM if PXMM else None
        rest_txt = f"{rest_mm:5.1f} mm" if rest_mm else f"{k['rest']:5.0f} Px"
        sag(f"  {p.name:18} {k['neigung']:+5.1f}  {rest_txt}  "
            f"{k['nst']:3d}/{k['nges']:<3d}     "
            f"{k['k1'][0]:5.1f} / {k['k2'][0]:5.1f}   {ZEICHEN[gew]}")

    noten = np.asarray(noten)
    unbrauchbar = list(np.where(noten == 2)[0])
    lauf, anf = laengster_lauf(unbrauchbar, len(pfade))
    sag("")
    sag(f"  Aufnahmen: {int((noten == 0).sum())} ohne Beanstandung, "
        f"{int((noten == 1).sum())} mit Abstrichen, "
        f"{len(unbrauchbar)} unbrauchbar")
    if unbrauchbar:
        n = 2 if lauf >= 2 else 1
        sag(f"  laengste zusammenhaengende Ausfallstrecke: {lauf} "
            f"Aufnahme(n)" +
            (f", {pfade[anf].name} bis {pfade[anf+lauf-1].name}"
             if lauf else "") + f"   {ZEICHEN[n]}")
        if lauf >= 2:
            mangel(True, f"Kette an {lauf} Aufnahmen unterbrochen",
                   f"Von {pfade[anf].name} bis {pfade[anf+lauf-1].name} sind "
                   f"{lauf} Aufnahmen hintereinander unbrauchbar. Eine "
                   f"einzelne liesse sich ueberspringen - bei dieser "
                   f"Ueberlappung haben auch die Nachbarn beidseits davon "
                   f"noch genug gemeinsam. Zwei hintereinander trennen die "
                   f"Kette, und alles dahinter laesst sich nicht mehr "
                   f"anschliessen.",
                   "Diesen Abschnitt neu aufnehmen. Woran es liegt, steht "
                   "je Aufnahme in der Liste darueber und in den Punkten "
                   "unten.",
                   [f"{pfade[i].name}: {', '.join(gruende[i])}"
                    for i in range(anf, anf + lauf)])
        else:
            mangel(False, "einzelne Aufnahmen unbrauchbar",
                   f"{len(unbrauchbar)} Aufnahme(n) sind unbrauchbar, aber "
                   f"keine zwei hintereinander. Der Zusammenbau kann sie "
                   f"ueberspringen; an diesen Stellen wird der Streifen "
                   f"unsicherer.",
                   "Wenn es schnell geht, diese Aufnahmen wiederholen.",
                   [f"{pfade[i].name}: {', '.join(gruende[i])}"
                    for i in unbrauchbar])

    gute = [k for k in kanten if k]
    if not gute:
        sag("  ROT   In keiner Aufnahme sind zwei Bauteilkanten zu finden.")
        mangel(True, "keine Kanten", "Das Bauteil hebt sich nirgends vom "
               "Untergrund ab.", "Siehe Kantenkontrast.")
    else:
        ABHILFE_KANTE = (
            "Das Bauteil so legen oder beleuchten, dass hinter dieser Kante "
            "etwas anderes liegt als Material derselben Helligkeit. Am "
            "billigsten: auf Boecke legen, dann entsteht hinter der unteren "
            "Kante ein Schattenspalt. Keine Leinwand noetig. Hilft auch: "
            "etwas hoeher oder tiefer halten, so dass die Kante nicht vor "
            "dem Boden liegt, sondern vor dem Abstand dahinter.")
        sag("")
        for nr in (1, 2):
            med = float(np.nanmedian([k[f"k{nr}"][0] for k in gute]))
            blind = float(np.nanmedian([k[f"k{nr}"][1] for k in gute])) * 100
            schwach = [f"{p.name} ({k[f'k{nr}'][0]:.0f})"
                       for p, k in zip(pfade, kanten)
                       if k and np.isfinite(k[f"k{nr}"][0])
                       and k[f"k{nr}"][0] < S_KONTRAST_MED[0]]
            n1 = note(med, S_KONTRAST_MED)
            n2 = note(blind, S_KONTRAST_BLIND, True)
            sag(f"  Kantenkontrast Kante {nr}  Median {med:5.1f} Graustufen "
                f"{ZEICHEN[n1]}   blinde Laenge {blind:4.0f} % "
                f"{ZEICHEN[n2]}")
            if n1:
                mangel(n1 == 2, f"Kante {nr} hebt sich nicht ab",
                       f"Kante {nr} unterscheidet sich im Mittel nur um "
                       f"{med:.0f} Graustufen von ihrem Hintergrund "
                       f"(noetig {S_KONTRAST_MED[0]:.0f}, Untergrenze "
                       f"{S_KONTRAST_MED[1]:.0f}). Daran haengt alles "
                       f"Weitere: Sitzt die Kantengerade schief, wird jedes "
                       f"Bild falsch entzerrt und die Zuordnung findet "
                       f"nichts mehr.", ABHILFE_KANTE, schwach)
            elif n2:
                mangel(n2 == 2, f"Kante {nr} verschwindet stellenweise",
                       f"Kante {nr} ist im Mittel deutlich zu sehen "
                       f"({med:.0f} Graustufen), aber auf {blind:.0f} % "
                       f"ihrer Laenge unter {SCHWACH:.0f} Graustufen. Auf "
                       f"diesen Abschnitten verliert die Kantensuche die "
                       f"Spur und zieht die Ausgleichsgerade schief.",
                       ABHILFE_KANTE, schwach)

    # --- 3b  Haelt das Band nur das Bauteil, und stimmt der Massstab? -----
    abschnitt_band(pfade, dreh, a.teiler, bw, mi, fak, PXMM, HOEHE)

    # --- 4  Oberflaeche ---------------------------------------------------
    sag("")
    sag("4 - Oberflaeche im Band")
    sag("-----------------------")
    t_med = float(np.median(textur))
    f_med = float(np.median(faser))
    sag(f"  Textur (Hochpassstreuung)  {t_med:5.2f}   "
        f"{ZEICHEN[note(t_med, S_TEXTUR)]}      "
        f"- woran sich die Zuordnung festhaelt")
    sag(f"  Faserrichtung quer/laengs  {f_med:5.2f}   "
        f"{ZEICHEN[note(f_med, S_FASER)]}      "
        f"- ueber 1.8 ist es sicher Holz")
    if note(t_med, S_TEXTUR):
        mangel(note(t_med, S_TEXTUR) == 2, "zu wenig Textur",
               f"Die Oberflaeche traegt nur {t_med:.1f} Graustufen Struktur.",
               "Haeufigste Ursache ist Unschaerfe oder ein ausgebranntes "
               "Glanzlicht. Belichtung pruefen, Blitz aus, auf das Bauteil "
               "scharfstellen und den Fokus feststellen.")
    if note(f_med, S_FASER):
        mangel(note(f_med, S_FASER) == 2, "Faserrichtung nicht erkennbar",
               f"Quer/laengs nur {f_med:.2f}. Entweder ist das Band kein "
               f"Holz, oder die Aufnahme ist unscharf.",
               "Pruefen, ob das Bauteil wirklich laengs im Bild liegt und "
               "die Aufnahmen scharf sind.")

    rg = np.asarray([f[0] for f in farbe]); bg = np.asarray([f[1] for f in farbe])
    hell = np.asarray([f[2] for f in farbe])
    d_rg = (rg.max() - rg.min()) / max(np.median(rg), 1e-6) * 100
    d_bg = (bg.max() - bg.min()) / max(np.median(bg), 1e-6) * 100
    d_h = (hell.max() - hell.min()) / max(np.median(hell), 1e-6) * 100
    nw = max(note(d_rg, S_WB, True), note(d_bg, S_WB, True))
    sag(f"  Weissabgleich ueber die Reihe  R/G {d_rg:4.1f} %, B/G {d_bg:4.1f} % "
        f"  {ZEICHEN[nw]}")
    nh = note(d_h, S_HELL, True)
    sag(f"  Helligkeit ueber die Reihe     {d_h:4.1f} %                "
        f"  {ZEICHEN[nh]}")
    if nh:
        mangel(nh == 2, "Belichtung wandert",
               f"Die Helligkeit des Bauteils schwankt ueber die Reihe um "
               f"{d_h:.0f} % (zulaessig 25 %). Ein Teil davon ist der "
               f"eigene Schatten des Fotografen, der im Bild stehen bleibt "
               f"und sich herausrechnen laesst; der Rest ist die "
               f"Belichtungsautomatik.",
               "Belichtungszeit und ISO manuell festsetzen und das Bauteil "
               "nicht gegen das Licht fotografieren. Der eigene Schatten "
               "sollte nicht auf dem Bauteil liegen.", (), "Farbe")
    if nw:
        mangel(nw == 2, "Weissabgleich wandert",
               f"Die Farbverhaeltnisse wandern ueber die Reihe um "
               f"{max(d_rg, d_bg):.0f} % (zulaessig 4 %). Im fertigen "
               f"Streifen bleibt davon ein Farbverlauf uebrig, der sich "
               f"nicht vollstaendig herausrechnen laesst.",
               "In der Kamera-App den Weissabgleich auf einen festen "
               "Kelvinwert stellen, nicht auf Automatik.", (), "Farbe")

    # --- 5  Ueberlappung --------------------------------------------------
    sag("")
    sag("5 - Ueberlappung und Vorschub")
    sag("-----------------------------")
    ueb, fehlt = [], []
    for i, v in enumerate(versatz):
        name = f"{pfade[i].name} -> {pfade[i+1].name}"
        if v is None:
            sag(f"  {name:40} KEIN TREFFER")
            fehlt.append(name)
            continue
        u = max(0.0, 1 - abs(v) / L_A) * 100
        ueb.append(u)
        vor_mm = abs(v) * fak / PXMM if PXMM else None
        sag(f"  {name:40} {u:5.1f} %   Vorschub {abs(v)*fak:5.0f} Px"
            + (f" = {vor_mm:4.0f} mm" if vor_mm else ""))
    doppelt = [f"{pfade[i].name} / {pfade[i+1].name}"
               for i, v in enumerate(versatz)
               if v is not None and max(0.0, 1 - abs(v) / L_A) * 100 > 92]
    if ueb:
        u_min = float(np.min(ueb)); u_med = float(np.median(ueb))
        # Fast deckungsgleiche Paare nicht als "zu wenig Vorschub" werten -
        # es sind doppelt ausgeloeste Aufnahmen, und die stoeren nicht.
        ohne = [u for u in ueb if u <= 92]
        u_min = float(np.min(ohne)) if ohne else u_min
        sag("")
        if doppelt:
            sag(f"  Hinweis  {len(doppelt)} Paar(e) sind fast "
                f"deckungsgleich - doppelt ausgeloest: "
                f"{', '.join(doppelt[:3])}")
        n = note(u_min, S_UEBERLAPP)
        sag(f"  Ueberlappung  Median {u_med:5.1f} %, kleinste {u_min:5.1f} %  "
            f"{ZEICHEN[n]}")
        if n:
            mangel(n == 2, "Ueberlappung zu klein",
                   f"Die knappste Ueberlappung betraegt {u_min:.0f} % "
                   f"(Ziel 50 %, Untergrenze 30 %).",
                   "Kleinere Schritte machen. Als Faustregel: ein halbes "
                   "Bildfeld je Aufnahme, also etwa eine Armlaenge.")
    if fehlt:
        # Nur ein Hinweis, solange es Einzelfaelle sind. Diese Pruefung sucht
        # im ROHEN Bild; der Zusammenbau entzerrt jede Aufnahme vorher und
        # findet dieselben Paare oft trotzdem. An der Reihe 261022/Versuch 2
        # meldete die Schnellpruefung zwei Luecken, und der Zusammenbau
        # verband anschliessend alle sieben verbliebenen Aufnahmen.
        mangel(len(fehlt) > len(versatz) * 0.40, "Luecken in der Reihe",
               f"{len(fehlt)} von {len(versatz)} Bildpaaren finden einander "
               f"in dieser Schnellpruefung nicht. Der Zusammenbau entzerrt "
               f"die Aufnahmen vorher und kommt damit oft noch durch; "
               f"sicher ist es nicht.",
               "Wenn es schnell geht, an diesen Stellen eine Zwischenaufnahme "
               "machen.", [f for f in fehlt])

    # --- 6  Urteil --------------------------------------------------------
    sag("")
    sag("6 - Urteil")
    sag("----------")
    # Die durchgehenden Ursachen, getrennt von der Kettenfrage: Wenn dieselbe
    # Schwaeche fast die ganze Reihe betrifft, liegt sie nicht an einzelnen
    # Aufnahmen, sondern am Aufbau - und dann hilft Nachfotografieren nur,
    # wenn vorher der Aufbau geaendert wird.
    schraeg = [(p.name, k["neigung"]) for p, k in zip(pfade, kanten)
               if k and abs(k["neigung"]) > S_NEIGUNG[0]]
    if schraeg:
        mangel(len(schraeg) > 0.4 * len(pfade),
               "Handy nicht parallel zum Bauteil",
               f"In {len(schraeg)} von {len(pfade)} Aufnahmen liegt das "
               f"Bauteil ueber {S_NEIGUNG[0]:.0f} Grad schraeg im Bild. "
               f"Ueber 3 Grad wandert das Band ueber die Bildhoehe um mehr "
               f"als 300 Px; die Kantensuche folgt dem nur mit Muehe und "
               f"verliert es bei grosser Schraeglage.",
               "Das Handy parallel zur Bauteilachse halten - nicht aus der "
               "Hueft- oder Schulterdrehung heraus fotografieren, sondern "
               "mit dem ganzen Koerper mitgehen.",
               [f"{n} ({w:+.1f} Grad)" for n, w in schraeg])

    # Getrennt geurteilt wird nach den beiden Groessen, auf die es ankommt:
    # Masstreue und Farbtreue. Eine Reihe kann masslich einwandfrei sein und
    # farblich wackelig - Reihe Seite A ist genau das. Ein gemeinsames Urteil
    # wuerde sie verwerfen, und das waere falsch.
    URTEIL = {
        ("Mass", 0): "GRUEN - laesst sich sauber zusammensetzen.",
        ("Mass", 1): "GELB  - laesst sich zusammensetzen, Mass mit Abstrichen.",
        ("Mass", 2): "ROT   - wird kein brauchbares Panorama geben. "
                     "Nachfotografieren, solange das Bauteil liegt.",
        ("Farbe", 0): "GRUEN - Farben tragen ueber die ganze Reihe.",
        ("Farbe", 1): "GELB  - Farbwiedergabe nur eingeschraenkt vergleichbar.",
        ("Farbe", 2): "ROT   - Farben nicht wiederherstellbar.",
    }
    stand = {}
    for bereich, titel in (("Mass", "Masstreue"), ("Farbe", "Farbtreue")):
        eigene = [m for m in maengel if m[1] == bereich]
        stand[bereich] = max([m[0] for m in eigene], default=0)
        sag(f"  {titel:12} {URTEIL[(bereich, stand[bereich])]}")
    ergebnis = max(stand.values())

    if maengel:
        sag("")
        for gew, bereich, kurz, erklaerung, abhilfe, betroffene in sorted(
                maengel, key=lambda m: (-m[0], m[1])):
            sag(f"  [{'ROT ' if gew == 2 else 'gelb'}] {kurz}  ({bereich})")
            for zeile in umbruch(erklaerung, 70):
                sag(f"         {zeile}")
            for zeile in umbruch("-> " + abhilfe, 70):
                sag(f"         {zeile}")
            if betroffene:
                sag(f"         betrifft: {', '.join(betroffene[:8])}"
                    + (f" und {len(betroffene)-8} weitere"
                       if len(betroffene) > 8 else ""))
            sag("")

    sag("  (Geprueft wird die Aufnahmereihe, nicht das fertige Bild. Dass die")
    sag("   Reihe besteht, heisst noch nicht, dass der Streifen masshaltig")
    sag("   wird - das zeigt erst der Zusammenbau.)")
    sag(f"  [{time.time()-T0:.1f} s]")

    if a.bericht:
        a.bericht.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
        print(f"\nBericht geschrieben: {a.bericht}")
    return ergebnis


def umbruch(text, breite):
    worte, zeile, aus = text.split(), "", []
    for w in worte:
        if len(zeile) + len(w) + 1 > breite:
            aus.append(zeile); zeile = w
        else:
            zeile = (zeile + " " + w).strip()
    if zeile:
        aus.append(zeile)
    return aus


if __name__ == "__main__":
    sys.exit(main())
