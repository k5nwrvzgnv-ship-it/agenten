"""Auswahl der Fotos einer Seite fürs Labeln (Jan 27.11.2026: Serienaufnahmen zeigen viele Fehlstellen doppelt,
manche Fotos nur den Grund). Reine Logik, nur Bordmittel, getestet in tests/test_auswahl.py.

Aus der Lage jedes Fotos längs (a..b in mm ab Balkenanfang, aus koerper.py) werden so wenige Fotos gewählt, dass sie
die Seite abdecken und je zwei benachbarte sich um mindestens UEBERLAPPUNG_MM überlappen. Dann liegt jede Fehlstelle
bis zu dieser Länge ganz in mindestens einem gewählten Foto. Unter Fotos, die fast gleich weit reichen, gewinnt das
schärfere. Ist die Lage eines Fotos unsicher oder die ganze Seite unplausibel, bleibt es drin: lieber ein Foto zu
viel als eine Lücke. Nichts wird gelöscht, die übrigen Fotos werden nur im Labeln nicht gezeigt.

Wahl je Foto: "drin", "leer" (kein Holz) oder "doppelt" (von gewählten Nachbarn abgedeckt)."""

UEBERLAPPUNG_MM = 80.0    # Jan 27.11.2026: etwa die größte Fehlstelle längs
SPIEL_MM = 30.0           # so viel weniger weit darf ein schärferes Foto reichen
ANFANG_MM = 5.0           # so nah am Anfang der Seite zählt ein Foto als erstes


def auswaehlen(fotos: list[dict], ganz: bool = False, ueberlappung: float = UEBERLAPPUNG_MM,
               spiel: float = SPIEL_MM) -> list[str]:
    """fotos: je {"a": mm, "b": mm (beide None = leer), "schaerfe": Zahl oder None, "unsicher": bool}.
    ganz: Seite unplausibel, alle Fotos mit Holz bleiben. Ergebnis: Wahl je Foto in derselben Reihenfolge."""
    wahl = ["leer" if f.get("a") is None or f.get("b") is None else "doppelt" for f in fotos]
    holz = [i for i, w in enumerate(wahl) if w != "leer"]
    if ganz:
        return ["leer" if w == "leer" else "drin" for w in wahl]
    if not holz:
        return wahl
    a = {i: min(fotos[i]["a"], fotos[i]["b"]) for i in holz}
    b = {i: max(fotos[i]["a"], fotos[i]["b"]) for i in holz}
    scharf = {i: fotos[i].get("schaerfe") or 0.0 for i in holz}
    anfang, ende = min(a.values()), max(b.values())
    gewaehlt: list[int] = []
    bis = None
    while bis is None or bis < ende - 1e-6:
        offen = [i for i in holz if i not in gewaehlt]
        if bis is None:
            pool = [i for i in offen if a[i] <= anfang + ANFANG_MM]
        else:
            pool = [i for i in offen if a[i] <= bis - ueberlappung and b[i] > bis]
        if pool:
            weiteste = max(b[i] for i in pool)
            nah = [i for i in pool if b[i] >= weiteste - spiel]
            i = max(nah, key=lambda i: (scharf[i], b[i]))
        else:
            # zu wenig Überlappung oder Lücke: das Foto, das am meisten überlappt
            weiter = [i for i in offen if b[i] > bis]
            if not weiter:
                break
            i = min(weiter, key=lambda i: (a[i], -b[i]))
        gewaehlt.append(i)
        bis = b[i] if bis is None else max(bis, b[i])
    for i in holz:
        if i in gewaehlt or fotos[i].get("unsicher"):
            wahl[i] = "drin"
    return wahl


def unsichere_fotos(anzahl: int, unsichere_schritte: list[int]) -> set[int]:
    """Schritt i liegt zwischen Foto i und i+1 (Fotos mit Holz in Aufnahme-Reihenfolge): beide sind unsicher."""
    return {j for i in unsichere_schritte for j in (i, i + 1) if 0 <= j < anzahl}
