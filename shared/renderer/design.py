"""Design-Profil: Aussehen und feste Angaben, die der Agent mitgibt (nicht Claude).

Ein Profil ist ein dict, z. B. aus einer TOML-Datei des Agenten. Fehlende Werte bekommen schlichte
Standardwerte. Lias Stil steht nicht hier, sondern in ihrem Agenten: Der Renderer enthält keine Daten
einer Person. Ein falsches Profil ist ein Fehler des Agenten (für Jan), nicht von Claude.
"""

import re

STANDARD = {
    "schrift": "Calibri",
    "schriftgroesse_pt": 11,
    "zeilenabstand": 1.15,
    "fach": "",
    "lehrkraft": "",
    "nummer_text": "Arbeitsblatt",  # vor der Nummer im Kopf: "Arbeitsblatt 5"
    "erstellt_von": "",  # Zusammenfassung: "erstellt von ..." im Kopf, leer: weglassen
    "linienabstand_cm": 0.8,  # Abstand der Schreiblinien
    "folien_schrift": "Aptos",
    "folien_titelschrift": "Aptos Display",
    "farben": {
        "thema": "E7E6E6",  # Thema-Zelle im Kopf
        "merksatz": "EDEDED",
        "material": "F2F2F2",
        "akzent": "404040",  # Folien: Titel, Striche, Balken, Leitfrage
        "kasten": "F2F2F2",  # Folien: Textkästen, Spalten, Auswahl
        "satzanfang": "196B24",  # Folien: Satzanfänge mit Zeigefinger, Smiley im Feedback
        "ueberschrift": "262626",  # Zusammenfassung: Überschriften, Kurs im Kopf, Balken der Kästen
        "pruefungsrelevant": "E7E6E6",  # Zusammenfassung: Hinweiskasten (Fläche)
        "organisatorisch": "F2F2F2",
        "rechenbeispiel": "F2F2F2",
        "tabellenkopf": "E7E6E6",
        "kennzeichnung": "7F7F7F",  # Zusammenfassung: [unsicher], [nur mündlich] und Quellen (Schrift)
    },
}

_FARBE = re.compile(r"^[0-9A-Fa-f]{6}$")
_GRENZEN = {"schriftgroesse_pt": (8, 16), "zeilenabstand": (1.0, 2.0), "linienabstand_cm": (0.5, 1.5)}


class ProfilUngueltig(ValueError):
    """Das Design-Profil des Agenten ist falsch."""


def profil_lesen(profil: dict | None) -> dict:
    """Vollständiges Profil: Standardwerte, überschrieben mit `profil`. Wirft ProfilUngueltig."""
    profil = profil or {}
    fehler = []
    for name in profil:
        if name not in STANDARD:
            fehler.append(f"{name}: unbekannt, erlaubt sind: {', '.join(STANDARD)}")
    ergebnis = {**STANDARD, **{k: v for k, v in profil.items() if k in STANDARD and k != "farben"}}
    farben = profil.get("farben", {})
    if not isinstance(farben, dict):
        fehler.append("farben: muss eine Tabelle sein")
        farben = {}
    for name, wert in farben.items():
        if name not in STANDARD["farben"]:
            fehler.append(f"farben.{name}: unbekannt, erlaubt sind: {', '.join(STANDARD['farben'])}")
        elif not isinstance(wert, str) or not _FARBE.match(wert.lstrip("#")):
            fehler.append(f"farben.{name}: muss eine Farbe wie \"FFD873\" sein, ist {wert!r}")
    ergebnis["farben"] = {**STANDARD["farben"], **{k: v.lstrip("#").upper() for k, v in farben.items()
                                                    if k in STANDARD["farben"] and isinstance(v, str)}}
    for name in ("schrift", "fach", "lehrkraft", "nummer_text", "erstellt_von", "folien_schrift",
                 "folien_titelschrift"):
        if not isinstance(ergebnis[name], str) or len(ergebnis[name]) > 60:
            fehler.append(f"{name}: muss ein Text mit höchstens 60 Zeichen sein")
    for name, (unten, oben) in _GRENZEN.items():
        wert = ergebnis[name]
        if isinstance(wert, bool) or not isinstance(wert, int | float) or not unten <= wert <= oben:
            fehler.append(f"{name}: muss eine Zahl von {unten} bis {oben} sein, ist {wert!r}")
    if fehler:
        raise ProfilUngueltig("Design-Profil ungültig: " + "; ".join(fehler))
    return ergebnis
