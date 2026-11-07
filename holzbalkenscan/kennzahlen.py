"""Kennzahlen aus den Textberichten des Verfahrens auslesen (rein, ohne Netz und ohne Dateizugriff).

Zwei Berichte je Reihe:
- Zusammenbau (verfahren/zusammensetzen2.py, <ziel>.txt)
- Vorprüfung (verfahren/pruefen.py --bericht)

Fehlt eine Zeile (Lauf abgebrochen, anderes Format), steht der Wert auf None. Kommt eine Zeile
mehrfach vor (der Bericht hängt bei --weiter die Meldungen des Rechenlaufs vorn an, Durchgänge
der Ausgleichung wiederholen sich), gilt die letzte.
"""

import re

ZAHL = r"([-+]?\d+(?:\.\d+)?)"


def _letzte(muster: str, text: str) -> tuple[str, ...] | None:
    treffer = re.findall(muster, text, flags=re.MULTILINE)
    if not treffer:
        return None
    t = treffer[-1]
    return t if isinstance(t, tuple) else (t,)


def _zahlen(muster: str, text: str, namen: list[str], ganz: tuple[str, ...] = ()) -> dict:
    t = _letzte(muster, text)
    if t is None:
        return dict.fromkeys(namen)
    return {n: (int(float(w)) if n in ganz else float(w)) for n, w in zip(namen, t, strict=True)}


def _punkte_nach(text: str, kopf: str) -> list[str] | None:
    """Spiegelstriche ("    - ...") im Abschnitt nach der Kopfzeile; [] bei "Keine Beanstandung"."""
    zeilen = text.splitlines()
    start = None
    for i, z in enumerate(zeilen):
        if z.strip() == kopf:
            start = i  # letzte Fundstelle
    if start is None:
        return None
    punkte = []
    for z in zeilen[start + 1:]:
        s = z.strip()
        if s.startswith("- "):
            punkte.append(s[2:])
        elif s == "Keine Beanstandung.":
            return []
        elif punkte and not s:
            break
        elif s.startswith("Ergebnis:"):
            break
    return punkte


def aus_zusammenbau(text: str) -> dict:
    """Kennzahlen aus dem Bericht von zusammensetzen2.py."""
    k = {}
    k.update(_zahlen(r"= " + ZAHL + r" Px/mm im Original", text, ["px_mm_band"]))
    k.update(_zahlen(r"je Bild: " + ZAHL + r" \.\. " + ZAHL + r" Px/mm", text, ["px_mm_min", "px_mm_max"]))
    k.update(_zahlen(r"Querversatz an den (\d+) Naehten: Median " + ZAHL + r" mm, groesster " + ZAHL + r" mm",
                     text, ["naehte", "nahtversatz_median_mm", "nahtversatz_max_mm"], ganz=("naehte",)))
    ohne = _letzte(r"ohne Verbindung zur Reihe: (.+)$", text)
    k["ohne_verbindung"] = [n.strip() for n in ohne[0].split(",") if n.strip()] if ohne else []
    k.update(_zahlen(r"Balken im Streifen: " + ZAHL + r" mm, Aufmass " + ZAHL + r" mm -> " + ZAHL
                     + r" mm = " + ZAHL + r" %", text,
                     ["laenge_roh_mm", "aufmass_mm", "laengsabweichung_mm", "laengsabweichung_prozent"]))
    k.update(_zahlen(r"Laengsmassstab auf das Aufmass gesetzt \(Faktor " + ZAHL + r"\)", text, ["einpassfaktor"]))
    k.update(_zahlen(r"Bauteilkante im Streifen: Streuung " + ZAHL + r" mm, langwellige Abweichung " + ZAHL
                     + r" mm \(auf " + ZAHL + r" % der Laenge", text,
                     ["kante_streuung_mm", "kante_langwellig_mm", "kante_gefunden_prozent"]))
    k.update(_zahlen(r"Nahtsichtbarkeit: (\d+) Spalten mit senkrechter Kante, staerkste " + ZAHL + r"-fach",
                     text, ["nahtkanten", "nahtkante_staerke"], ganz=("nahtkanten",)))
    k.update(_zahlen(r"Punktpaare \d+, Rest Median " + ZAHL + r" mm", text, ["punktpaar_rest_median_mm"]))
    k.update(_zahlen(r"Flaeche belegt: " + ZAHL + r" %", text, ["belegt_prozent"]))
    k.update(_zahlen(r"Rechenzeit:\s+" + ZAHL + r" s", text, ["rechenzeit_s"]))
    k["pruefbericht"] = _punkte_nach(text, "Pruefbericht")
    k.update(_zuordnung(text))
    return k


def _lage_zeilen(text: str) -> int | None:
    """Aufnahmen im Abschnitt "Lage der Aufnahmen im Bauteilrahmen" (letzte Fundstelle), sonst None."""
    zeilen = text.splitlines()
    start = None
    for i, z in enumerate(zeilen):
        if z.strip() == "Lage der Aufnahmen im Bauteilrahmen":
            start = i
    if start is None:
        return None
    n = 0
    for z in zeilen[start + 1:]:
        if not re.match(r"^  \S+: +[-+]?\d+ \.\. ", z):
            break
        n += 1
    return n


def _zuordnung(text: str) -> dict:
    """Zuordnung: direkte Nachbarpaare, Punktpaare je Durchgang, verwendete Aufnahmen, Paare je Naht."""
    k = {}
    k.update(_zahlen(r" - (\d+) Aufnahmen$", text, ["aufnahmen"], ganz=("aufnahmen",)))
    # Nur der erste Rechenlauf zählt; bei --weiter steht der Kopf ein zweites Mal ohne Zuordnung.
    teil = text.split("\nZuordnung, zweiter Durchgang")[0]
    direkt = re.findall(r"^  \S+ -> \S+: +\d+ Paare", teil, flags=re.MULTILINE)
    k["direkte_paare"] = len(direkt) if "\nZuordnung (" in text else None
    k.update(_zahlen(r"^  (\d+) Bildpaare, (\d+) Punktpaare$", text, ["bildpaare_1", "punktpaare_1"],
                     ganz=("bildpaare_1", "punktpaare_1")))
    k.update(_zahlen(r"; (\d+) Punktpaare statt \d+", text, ["punktpaare_2"], ganz=("punktpaare_2",)))
    k["verwendet"] = _lage_zeilen(text)
    k["abgehaengt"] = (k["aufnahmen"] - k["verwendet"]
                       if k["aufnahmen"] is not None and k["verwendet"] is not None else None)
    naehte = k.get("naehte") or _zahlen(r"Querversatz an den (\d+) Naehten", text, ["n"], ganz=("n",))["n"]
    k["punktpaare_je_naht"] = (round(k["punktpaare_2"] / naehte, 1)
                               if k["punktpaare_2"] is not None and naehte else None)
    return k


def aus_vorpruefung(text: str) -> dict:
    """Kennzahlen aus dem Bericht von pruefen.py."""
    k = {}
    k.update(_zahlen(r"^(\d+) Aufnahmen, Teiler", text, ["aufnahmen"], ganz=("aufnahmen",)))
    for feld, titel in (("masstreue", "Masstreue"), ("farbtreue", "Farbtreue")):
        t = _letzte(r"^\s*" + titel + r"\s+(GRUEN|GELB|ROT)\b", text)
        k[feld] = t[0] if t else None
    k.update(_zahlen(r"Aufloesung\s+" + ZAHL + r" Px/mm", text, ["aufloesung_px_mm"]))
    k.update(_zahlen(r"Ueberlappung\s+Median\s+" + ZAHL + r" %, kleinste\s+" + ZAHL + r" %", text,
                     ["ueberlappung_median_prozent", "ueberlappung_min_prozent"]))
    k["maengel"] = [f"{'ROT' if g.strip() == 'ROT' else 'gelb'}: {kurz} ({bereich})" for g, kurz, bereich in
                    re.findall(r"^\s*\[(ROT |gelb)\] (.+?)  \((Mass|Farbe)\)\s*$", text, flags=re.MULTILINE)]
    k.update(_zahlen(r"^\s*\[\s*" + ZAHL + r" s\]\s*$", text, ["rechenzeit_s"]))
    return k
