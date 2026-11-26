"""Reine Logik der Fotobox-Aufnahme: Seiten, Kameraabstand, Bildfeld, Abschnitte, Prüfung der Eingaben.

Alles in mm. Der Balken liegt in der Box auf Rollen, die Kamera blickt oben mittig senkrecht nach unten. Die lange
Bildseite liegt längs zum Balken (Annahme, Handy quer zur Schieberichtung nicht vorgesehen). Nur Bordmittel,
läuft auf dem Mac ohne .venv."""

import math

# Startwert: 24 mm Kleinbild bei 4:3, also Brennweite / lange Sensorseite (34,6 mm). Wird durch Messen ersetzt.
FAKTOR_START = 24 / 34.6
RAND = 30.0                 # so viel soll vor und hinter dem Balken mindestens noch im Bild sein
UEBERLAPPUNG = 0.25         # Felix' Verfahren braucht 25-30 %
SCHRITT_MAX = 500.0
GANZ = (0.0, 0.0, 1.0, 1.0)  # Zuschnitt [x, y, Breite, Höhe] als Anteile des quer liegenden Bildes
SEITEN = ("1", "2", "3", "4")


def seite_info(breite: float, hoehe: float, seite: str) -> dict:
    """Sichtbare Fläche und Höhe des Balkens über den Rollen. Seiten 1 und 3 sind die breiten, 2 und 4 die
    schmalen; von einer zur nächsten wird der Balken um 90 Grad gerollt."""
    lang, kurz = max(breite, hoehe), min(breite, hoehe)
    breitseite = seite in ("1", "3")
    name = "Seite" if lang == kurz else "Breitseite" if breitseite else "Schmalseite"
    return {"art": name, "flaeche_mm": lang if breitseite else kurz, "hoch_mm": kurz if breitseite else lang}


def bildfeld(abstand: float, faktor: float) -> tuple[float, float]:
    """(längs, quer) des Bildes auf der Balkenfläche, Format 4:3."""
    laengs = abstand / faktor
    return laengs, laengs * 0.75


def schritt_vorschlag(laengs: float) -> float:
    """Vorschub auf 5 cm abgerundet, mindestens 25 % Überlappung, höchstens 50 cm."""
    schritt = min(SCHRITT_MAX, math.floor(laengs * (1 - UEBERLAPPUNG) / 50) * 50)
    return float(schritt) if schritt >= 50 else max(10.0, math.floor(laengs * (1 - UEBERLAPPUNG) / 10) * 10.0)


def mitten(laenge: float, laengs: float, schritt: float) -> list[float]:
    """Lage der Bildmitte ab Balkenanfang für jeden Abschnitt. Der letzte schließt mit Rand am Ende ab."""
    erste, letzte = laengs / 2 - RAND, laenge + RAND - laengs / 2
    if letzte <= erste:
        return [laenge / 2]
    ergebnis = [erste]
    while ergebnis[-1] < letzte - 0.5:
        ergebnis.append(min(ergebnis[-1] + schritt, letzte))
    return ergebnis


def plan(balken: dict, seite: str, kamera_rolle: float, faktor: float, schritt: float | None = None,
         zuschnitt: list[float] | None = None) -> dict:
    """Alles, was für eine Seite vor dem ersten Foto feststeht. Wirft ValueError, wenn es nicht geht."""
    info = seite_info(balken["breite_mm"], balken["hoehe_mm"], seite)
    abstand = kamera_rolle - info["hoch_mm"]
    if abstand < 50:
        raise ValueError(f"{info['art']}: nur {abstand / 10:.1f} cm bis zur Kamera, das passt nicht in die Box.")
    voll, hoch = bildfeld(abstand, faktor)
    _, _, anteil_b, anteil_h = zuschnitt or GANZ
    laengs, quer = voll * anteil_b, hoch * anteil_h
    schritt = schritt or schritt_vorschlag(laengs)
    return {**info, "abstand_mm": abstand, "laengs_mm": laengs, "quer_mm": quer, "voll_mm": voll, "zuschnitt": zuschnitt, "schritt_mm": schritt,
            "kamera_rolle_mm": kamera_rolle, "faktor": faktor, "luecke": schritt >= laengs,
            "zu_breit": info["flaeche_mm"] >= quer, "mitten_mm": mitten(balken["laenge_mm"], laengs, schritt)}


def neu_skalieren(p: dict, faktor: float) -> dict:
    """Plan einer Seite mit Fotos auf einen neu gemessenen Bildwinkel umrechnen. Die Lage der Abschnitte bleibt, so
    sind die Fotos gemacht; nur die Maße im Bild ändern sich (Bildfeld proportional zu 1 / Faktor)."""
    k = p["faktor"] / faktor
    neu = {**p, "faktor": faktor, "laengs_mm": p["laengs_mm"] * k, "quer_mm": p["quer_mm"] * k}
    if p.get("voll_mm"):
        neu["voll_mm"] = p["voll_mm"] * k
    neu["luecke"], neu["zu_breit"] = p["schritt_mm"] >= neu["laengs_mm"], p["flaeche_mm"] >= neu["quer_mm"]
    return neu


def plan_anpassen(p: dict, balken: dict, seite: str, mit_foto: list[int]) -> dict:
    """Eingefrorenen Plan einer Seite an korrigierte Maße anpassen. Die Fotos sind am echten Balken entstanden: ihre
    Lage (mitten_mm) bleibt, Abstand und Bildfeld folgen der neuen Höhe in dieser Lage (Kamera, Bildwinkel, Zuschnitt
    und Vorschub wie beim ersten Foto). Abschnitte bis zum letzten Foto bleiben, danach geht es mit dem Vorschub bis
    zum neuen Ende weiter: länger gibt neue Abschnitte, kürzer streicht nur leere am Ende. mit_foto: Abschnitte mit
    Foto, nicht leer."""
    info = seite_info(balken["breite_mm"], balken["hoehe_mm"], seite)
    abstand = p["kamera_rolle_mm"] - info["hoch_mm"]
    if abstand < 50:
        raise ValueError(f"{info['art']}: nur {abstand / 10:.1f} cm bis zur Kamera, das passt nicht in die Box.")
    voll, hoch = bildfeld(abstand, p["faktor"])
    _, _, anteil_b, anteil_h = p.get("zuschnitt") or GANZ
    laengs, quer = voll * anteil_b, hoch * anteil_h
    schritt = p["schritt_mm"]
    m = list(p["mitten_mm"][:max(mit_foto) + 1])
    letzte = balken["laenge_mm"] + RAND - laengs / 2
    while m[-1] < letzte - 0.5:
        m.append(min(m[-1] + schritt, letzte))
    return {**p, **info, "abstand_mm": abstand, "laengs_mm": laengs, "quer_mm": quer, "voll_mm": voll,
            "luecke": schritt >= laengs, "zu_breit": info["flaeche_mm"] >= quer, "mitten_mm": m}


def name_pruefen(wert) -> str:
    """Anzeigename eines Balkens neben der festen ID, leer = keiner."""
    if wert is None:
        return ""
    if not isinstance(wert, str):
        raise ValueError("Name nicht lesbar.")
    return " ".join(wert.split())[:40]


def zuschnitt_pruefen(werte) -> list[float] | None:
    """Rechteck in Anteilen, None oder das ganze Bild = kein Zuschnitt."""
    if werte is None:
        return None
    if not isinstance(werte, list) or len(werte) != 4 or any(
            isinstance(w, bool) or not isinstance(w, (int, float)) or not 0 <= w <= 1 for w in werte):
        raise ValueError("Zuschnitt nicht lesbar.")
    x, y, b, h = (float(w) for w in werte)
    if b < 0.1 or h < 0.1 or x + b > 1.0001 or y + h > 1.0001:
        raise ValueError("Der Ausschnitt ist zu klein.")
    return [round(w, 4) for w in (x, y, b, h)]


def px_je_mm(lange_seite_px: int, laengs_mm: float) -> float:
    return lange_seite_px / laengs_mm


def faktor_aus_messung(anteil: float, strecke_mm: float, abstand: float) -> float:
    """Faktor aus einer bekannten Strecke auf der Balkenfläche. anteil = Strecke im Bild / lange Bildseite."""
    if not 0.02 <= anteil <= 1.3 or strecke_mm <= 0:
        raise ValueError("Strecke zu kurz. Zwei Punkte möglichst weit auseinander anklicken.")
    faktor = abstand * anteil / strecke_mm
    if not 0.2 <= faktor <= 4:
        raise ValueError("Das Maß passt nicht zum Bild. Punkte und Länge prüfen.")
    return faktor


def kontrolle(anteil: float, voll_mm: float, zollstock_mm: float) -> dict:
    """Prüfmessung: Strecke im Foto nach dem Plan der Seite gegen das Maß vom Zollstock. anteil = Strecke im Bild /
    lange Bildseite, voll_mm = lange Bildseite auf der Fläche. Abweichung in Prozent, plus heißt im Foto zu groß."""
    if isinstance(anteil, bool) or not isinstance(anteil, (int, float)) or not 0.002 <= anteil <= 1.3:
        raise ValueError("Zwei Punkte im Foto anklicken.")
    foto = anteil * voll_mm
    return {"foto_mm": round(foto, 1), "zollstock_mm": round(zollstock_mm, 1),
            "abweichung": round((foto / zollstock_mm - 1) * 100, 2)}


def kontrollen_mittel(liste: list[dict]) -> dict | None:
    """Mittlere Abweichung aller Prüfmessungen eines Balkens, None ohne Messung."""
    if not liste:
        return None
    werte = [k["abweichung"] for k in liste]
    return {"anzahl": len(werte), "mittel": round(sum(werte) / len(werte), 2), "min": min(werte), "max": max(werte)}


def zahl(daten: dict, feld: str, von: float, bis: float, name: str) -> float:
    wert = daten.get(feld)
    if isinstance(wert, bool) or not isinstance(wert, (int, float)) or not von <= wert <= bis:
        raise ValueError(f"{name}: bitte {von / 10:g} bis {bis / 10:g} cm eingeben.")
    return float(wert)


def masse_pruefen(daten: dict) -> dict:
    return {"laenge_mm": zahl(daten, "laenge_mm", 50, 20000, "Länge"),
            "breite_mm": zahl(daten, "breite_mm", 10, 500, "Breite"),
            "hoehe_mm": zahl(daten, "hoehe_mm", 10, 500, "Höhe"),
            "holzart": str(daten.get("holzart", "")).strip()[:60]}


def neue_id(letzte_nr: int, vorhandene: list[str]) -> tuple[str, int]:
    """Nächste Balken-ID B001, B002, ... Eine einmal vergebene Nummer kommt nie wieder."""
    nummern = [int(v[1:]) for v in vorhandene if v[:1] == "B" and v[1:].isdigit()]
    nr = max([letzte_nr, *nummern]) + 1
    return f"B{nr:03d}", nr


def foto_name(balken: str, seite: str, nr: int, mitte: float, zeit: str, endung: str) -> str:
    return f"{balken}_S{seite}_{nr + 1:02d}_{round(mitte):05d}mm_{zeit}{endung}"


def endung_von(daten: bytes) -> str:
    """Dateiart aus den ersten Bytes, ValueError bei allem, was kein Foto ist."""
    if daten[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if daten[4:8] == b"ftyp" and daten[8:12] in (b"heic", b"heix", b"mif1", b"msf1", b"heim", b"heis"):
        return ".heic"
    if daten[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    raise ValueError("Vom iPhone kam kein Foto. Im Kurzbefehl unter „Datei“ das Foto auswählen.")


def raster_fuers_handy(q: dict) -> dict | None:
    """Raster der Mac-Seite für die iPhone-App. q aus der Abfrage von /live.jpg: r = Rasterweite als Anteil der
    langen Bildseite (ganzes Bild), w = Rasterweite in mm, g = 1 bei gemessenem Bildwinkel. Ungültig oder ohne
    Plan: None, die App zeigt dann ein Raster ohne Maß."""
    try:
        anteil, mm = float(q["r"]), float(q["w"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (0.005 <= anteil <= 1 and 1 <= mm <= 10000):
        return None
    cm = f"{mm / 10:.1f}".rstrip("0").rstrip(".").replace(".", ",")
    return {"anteil": round(anteil, 5), "text": f"Raster {'' if q.get('g') == '1' else 'etwa '}{cm} cm"}
