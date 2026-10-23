"""Aufgabentypen und Rangliste (Schritt 7).

typ: feinere Einteilung innerhalb der Kategorie nach Stichwörtern in Titel und Ausgabe (erste passende Regel).
rangliste: je Typ Häufigkeit, Runden, Korrekturen und ein Wert = Summe der Runden, gewichtet nach
  Automatisierbarkeit (hoch 1, mittel 0,6, gering 0,2). Der Wert schätzt, wie viele Runden Lia ein Agent
  abnehmen könnte: Häufigkeit x Aufwand x Automatisierbarkeit in einer Zahl.
Ohne Netz, getestet in tests/test_rangliste.py.
"""

GEWICHT = {"hoch": 1.0, "mittel": 0.6, "gering": 0.2}

# (Kategorie, Typ, Stichwörter in Titel oder Ausgabe, klein geschrieben); erste passende Regel gilt
REGELN = [
    ("material", "theater_material", ["szene", "gedicht", "chor", "spielanweisung", "skala", "reflexionsfrage",
                                      "rollen", "standbild", "betonung"]),
    ("material", "zusammenfassung_stueck", ["zusammenfass", "themen", "dramen", "stück"]),
    ("material", "fallbeispiel", ["fallbeispiel", "fall ", "fälle", "beispiel zum anwenden", "anwendungsbeispiel",
                                  "singer-beispiel"]),
    ("material", "argumentieren_ueben", ["bbb", "argument", "erörterung"]),
    ("material", "ab_bausteine", ["aufgabe", "kärtchen", "sicherungstabelle", "erwartungshorizont", "ankreuz",
                                  "definition", "lek", "selbsteinschätzung", "zeile", "fehler"]),
    ("material", "ab_text_position", []),
    ("planung", "reihe_und_rlp", ["reihe", "leitfrage", "rlp", "rahmenlehrplan", "themenfeld", "standards",
                                  "eignung", "machbar", "für die klasse", "vermittelt"]),
    ("planung", "stunde_und_ub", []),
    ("auswahl", "stuecke_filme_themen", ["stück", "roman", "film", "szene", "themen"]),
    ("auswahl", "positionen_und_faelle", []),
    ("fachklaerung", "stueck_oder_film", ["film", "stück", "druck", "angry"]),
    ("fachklaerung", "philosophie_und_quellen", []),
    ("eigener_text", "ub_entwurf_und_texte", []),
    ("bewertung", "mitarbeit_auswerten", ["mitarbeit", "gruppenbeobachtung", "teilnahme"]),
    ("bewertung", "bewertungsbogen_und_noten", []),
    ("verwaltung", "verwaltung", []),
    ("kommunikation", "nachrichten", []),
    ("sonstiges", "sonstiges", []),
]


def typ(aufgabe: dict) -> str:
    text = f"{aufgabe.get('titel', '')} {aufgabe.get('ausgabe', '')}".lower()
    for kategorie, name, woerter in REGELN:
        if kategorie == aufgabe["kategorie"] and (not woerter or any(w in text for w in woerter)):
            return name
    return aufgabe["kategorie"]


def rangliste(aufgaben: list[dict]) -> list[dict]:
    gruppen: dict[tuple[str, str], list[dict]] = {}
    for a in aufgaben:
        gruppen.setdefault((a["kategorie"], typ(a)), []).append(a)
    zeilen = []
    for (kategorie, name), liste in gruppen.items():
        runden = [a["bis"] - a["von"] + 1 for a in liste]
        korrekturen = sum(len(a["korrekturen"]) for a in liste)
        wert = sum(r * GEWICHT[a["automatisierbar"]] for r, a in zip(runden, liste, strict=True))
        zeilen.append({"typ": name, "kategorie": kategorie, "aufgaben": len(liste), "runden": sum(runden),
                       "runden_je_aufgabe": round(sum(runden) / len(liste), 1),
                       "korrekturen_je_aufgabe": round(korrekturen / len(liste), 2),
                       "automatisierbar_hoch_anteil": round(sum(a["automatisierbar"] == "hoch" for a in liste)
                                                            / len(liste), 2),
                       "wert": round(wert, 1)})
    return sorted(zeilen, key=lambda z: -z["wert"])
