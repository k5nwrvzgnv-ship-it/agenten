"""Klassenliste von Neurolign als Datei (aufnahmen/klassen.json), änderbar in der Oberfläche (Jan 26.11.2026:
umbenennen, löschen, neu, Farbe). Reine Logik ohne Dateien, getestet in tests/test_klassen.py.

Jede Klasse hat eine feste ID, die nie neu vergeben wird. Labels tragen die ID, darum bleiben sie beim Umbenennen
gültig. Der Schlüssel (z. B. live_knot) ist der Name fürs Training (data.yaml) und ändert sich nie; 0-9 sind die
Kodytek-Klassen, damit fertige Kodytek-Sätze und Modelle weiter passen. Training nimmt die ID als YOLO-Nummer;
gelöschte IDs bleiben als leere Klasse stehen.

Löschen einer Klasse mit Objekten heißt zusammenlegen: Die Objekte bekommen die Zielklasse und merken sich die alte
(Feld kv). Rückgängig holt genau diese Objekte zurück."""

import re

# Startfassung: Reihenfolge der Labelrichtlinie, Gruppen und Muster wie in labeln.js (Jan 25.11.2026)
STANDARD = [
    (0, "live_knot", "Ast lebend", "Ast", ""), (1, "dead_knot", "Ast tot", "Ast", "9 4"),
    (2, "knot_missing", "Astloch", "Ast", "3 3"), (3, "knot_with_crack", "Ast mit Riss", "Ast", "12 3 3 3"),
    (9, "overgrown", "Überwallung", "Ast", "5 4"),
    (4, "crack", "Riss", "Riss", ""),
    (10, "bohrloch", "Bohrloch", "Loch", ""), (12, "nagelloch", "Nagelloch", "Loch", "9 4"),
    (15, "insektenfrass", "Insektenfraß", "Loch", "3 3"),
    (17, "fuge", "Fuge", "Fuge", ""), (16, "verbindung", "Verbindung", "Fuge", "9 4"),
    (11, "metall", "Metall", "Metall", ""),
    (14, "faeule", "Fäule", "Weitere", "5 4"), (13, "farbe", "Farbe", "Weitere", "12 3 3 3"),
    (6, "resin", "Harz", "Weitere", ""), (7, "marrow", "Mark", "Weitere", "9 4"),
    (8, "blue_stain", "Bläue", "Weitere", "3 3"), (5, "quartzity", "Quartzity", "Weitere", "16 4"),
]
MUSTER = ["", "9 4", "3 3", "12 3 3 3", "5 4", "16 4", "2 6", "14 4 2 4"]
MAX_KLASSEN = 64

# Klassen der Projektgruppe (Telegram 27.11.2026, Felix, Henri, Jan): Äste, Abplatzung, Nagel-/Schraubloch,
# Harzgalle, Riss Lamelle und Riss Klebefuge getrennt, Insektenloch. Neue Klassen (Schlüssel, Name, Gruppe) und neue
# Namen je Schlüssel. Abplatzung steht bei Loch, weil eine neue Gruppe ans Ende unter „Weitere“ fiele.
GRUPPE_NEU = [("abplatzung", "Abplatzung", "Loch"), ("riss_klebefuge", "Riss Klebefuge", "Riss")]
GRUPPE_NAMEN = {"crack": "Riss Lamelle", "nagelloch": "Nagel-/Schraubloch", "resin": "Harzgalle"}


def standard() -> dict:
    return {"klassen": [{"id": i, "schluessel": s, "name": n, "gruppe": g, "muster": m, "farbe": None, "aktiv": True}
                        for i, s, n, g, m in STANDARD], "letzte": None}


def gruppen(d: dict) -> list[str]:
    """Gruppen in der Reihenfolge ihres ersten Auftretens (aktive Klassen)."""
    ergebnis = []
    for k in d["klassen"]:
        if k["aktiv"] and k["gruppe"] not in ergebnis:
            ergebnis.append(k["gruppe"])
    return ergebnis


def aktive_ids(d: dict) -> set[int]:
    return {k["id"] for k in d["klassen"] if k["aktiv"]}


def schluessel_liste(d: dict) -> list[str]:
    """Namen fürs Training, Index = ID. Auch gelöschte IDs stehen drin, damit die Nummern stimmen."""
    namen = {k["id"]: k["schluessel"] for k in d["klassen"]}
    return [namen.get(i, f"frei_{i}") for i in range(max(namen) + 1)]


def klasse(d: dict, kid) -> dict:
    for k in d["klassen"]:
        if k["id"] == kid and not isinstance(kid, bool):
            return k
    raise ValueError("Diese Klasse gibt es nicht.")


def text(wert, wofuer: str, laenge: int) -> str:
    if not isinstance(wert, str) or not " ".join(wert.split()):
        raise ValueError(f"{wofuer} fehlt.")
    return " ".join(wert.split())[:laenge]


def name_frei(d: dict, name: str, ausser=None) -> str:
    if any(k["aktiv"] and k["id"] != ausser and k["name"].casefold() == name.casefold() for k in d["klassen"]):
        raise ValueError(f"„{name}“ gibt es schon.")
    return name


def farbe(wert):
    if wert is None or wert == "":
        return None
    if not isinstance(wert, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", wert):
        raise ValueError("Farbe nicht lesbar.")
    return wert.lower()


def schluessel_neu(d: dict, name: str) -> str:
    """Fester Trainingsname aus dem ersten Namen, nur a-z, 0-9 und _, nie doppelt."""
    roh = name.casefold().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))
    basis = re.sub(r"[^a-z0-9]+", "_", roh).strip("_")[:30] or "klasse"
    vorhanden, s, n = {k["schluessel"] for k in d["klassen"]}, basis, 2
    while s in vorhanden:
        s, n = f"{basis}_{n}", n + 1
    return s


def aendern(d: dict, kid, name=None, gruppe=None, farbe_neu=...) -> dict:
    """Name, Gruppe oder Farbe einer aktiven Klasse. Neue Gruppe: einfach einen neuen Namen angeben."""
    k = klasse(d, kid)
    if not k["aktiv"]:
        raise ValueError("Diese Klasse ist gelöscht.")
    if name is not None:
        k["name"] = name_frei(d, text(name, "Name", 30), kid)
    if gruppe is not None:
        neu = text(gruppe, "Gruppe", 20)
        if neu != k["gruppe"]:
            k["gruppe"], k["muster"] = neu, muster_frei(d, neu, kid)
    if farbe_neu is not ...:
        k["farbe"] = farbe(farbe_neu)
    d["letzte"] = None
    return k


def gruppe_umbenennen(d: dict, alt, neu) -> None:
    alt, neu = text(alt, "Gruppe", 20), text(neu, "Gruppe", 20)
    treffer = [k for k in d["klassen"] if k["gruppe"] == alt]
    if not treffer:
        raise ValueError("Diese Gruppe gibt es nicht.")
    if neu != alt and neu in gruppen(d):
        raise ValueError(f"„{neu}“ gibt es schon.")
    for k in treffer:
        k["gruppe"] = neu
    d["letzte"] = None


def muster_frei(d: dict, gruppe: str, ausser=None) -> str:
    belegt = [k["muster"] for k in d["klassen"] if k["aktiv"] and k["gruppe"] == gruppe and k["id"] != ausser]
    return next((m for m in MUSTER if m not in belegt), MUSTER[len(belegt) % len(MUSTER)])


def neu(d: dict, name, gruppe) -> dict:
    if len(d["klassen"]) >= MAX_KLASSEN:
        raise ValueError(f"Höchstens {MAX_KLASSEN} Klassen.")
    name, gruppe = name_frei(d, text(name, "Name", 30)), text(gruppe, "Gruppe", 20)
    k = {"id": max(k["id"] for k in d["klassen"]) + 1, "schluessel": schluessel_neu(d, name), "name": name,
         "gruppe": gruppe, "muster": muster_frei(d, gruppe), "farbe": None, "aktiv": True}
    # hinter die letzte Klasse derselben Gruppe, sonst ans Ende
    stelle = max((i for i, x in enumerate(d["klassen"]) if x["gruppe"] == gruppe), default=len(d["klassen"]) - 1)
    d["klassen"].insert(stelle + 1, k)
    d["letzte"] = None
    return k


def gruppenklassen(d: dict) -> list[str]:
    """Klassen der Gruppe vom 27.11.2026 eintragen. Gibt es einen Schlüssel schon (auch gelöscht), bleibt er, wie er
    ist; gelöschte Klassen werden nicht umbenannt. Zweimal anwenden ändert nichts. Gibt die Änderungen als Text zurück."""
    gemacht = []
    for s, name, gruppe in GRUPPE_NEU:
        if any(k["schluessel"] == s for k in d["klassen"]):
            continue
        k = neu(d, name, gruppe)
        if k["schluessel"] != s:
            raise ValueError(f"Schlüssel {k['schluessel']} statt {s}.")
        gemacht.append(f"neu {k['id']} {s} „{name}“ ({gruppe})")
    for s, name in GRUPPE_NAMEN.items():
        k = next((k for k in d["klassen"] if k["schluessel"] == s), None)
        if k and k["aktiv"] and k["name"] != name:
            alt = k["name"]
            aendern(d, k["id"], name=name)
            gemacht.append(f"{k['id']} {s}: „{alt}“ -> „{name}“")
    return gemacht


def weg(d: dict, kid, ziel=None, anzahl: int = 0) -> None:
    """Klasse löschen. Mit Objekten (anzahl > 0) nur zusammen mit einer Zielklasse, in die sie wandern."""
    k = klasse(d, kid)
    if not k["aktiv"]:
        raise ValueError("Diese Klasse ist schon gelöscht.")
    if len(aktive_ids(d)) == 1:
        raise ValueError("Die letzte Klasse bleibt.")
    if anzahl and ziel is None:
        raise ValueError("Objekte dieser Klasse brauchen eine andere Klasse.")
    if ziel is not None:
        z = klasse(d, ziel)
        if not z["aktiv"] or z["id"] == kid:
            raise ValueError("Zielklasse nicht wählbar.")
    k["aktiv"], k["in"] = False, ziel
    d["letzte"] = {"art": "weg", "id": kid, "in": ziel}


def zurueck(d: dict) -> dict:
    """Letztes Löschen zurücknehmen. Gibt {"id", "in"} zurück, damit die Labels zurückwandern können."""
    zuletzt = d.get("letzte")
    if not zuletzt or zuletzt.get("art") != "weg":
        raise ValueError("Nichts zum Zurückholen.")
    k = klasse(d, zuletzt["id"])
    if zuletzt["in"] is not None and not klasse(d, zuletzt["in"])["aktiv"]:
        raise ValueError("Die Zielklasse ist inzwischen gelöscht.")
    name_frei(d, k["name"], k["id"])
    k["aktiv"] = True
    k.pop("in", None)
    d["letzte"] = None
    return {"id": zuletzt["id"], "in": zuletzt["in"]}


def objekte_umhaengen(objekte: list[dict], alt: int, ziel: int) -> int:
    """Objekte der Klasse alt in ziel, alte Klasse in kv gemerkt. Gibt die Zahl der geänderten zurück."""
    n = 0
    for o in objekte:
        if o.get("k") == alt:
            o["k"], o["kv"], n = ziel, alt, n + 1
    return n


def objekte_zurueck(objekte: list[dict], alt: int, ziel: int) -> int:
    n = 0
    for o in objekte:
        if o.get("kv") == alt and o.get("k") == ziel:
            o["k"], n = alt, n + 1
            del o["kv"]
    return n


def gelesen(roh) -> dict:
    """klassen.json prüfen; kaputt oder fehlend gibt ValueError, der Aufrufer nimmt dann nichts Stilles an."""
    if not isinstance(roh, dict) or not isinstance(roh.get("klassen"), list) or not roh["klassen"]:
        raise ValueError("klassen.json nicht lesbar.")
    ids, schl = set(), set()
    for k in roh["klassen"]:
        if not isinstance(k, dict) or not isinstance(k.get("id"), int) or isinstance(k.get("id"), bool) \
                or k["id"] < 0 or k["id"] in ids or not isinstance(k.get("schluessel"), str) or k["schluessel"] in schl:
            raise ValueError("klassen.json: Klasse nicht lesbar.")
        ids.add(k["id"])
        schl.add(k["schluessel"])
        for feld, wert in (("name", ""), ("gruppe", "Weitere"), ("muster", ""), ("farbe", None), ("aktiv", True)):
            k.setdefault(feld, wert)
    roh.setdefault("letzte", None)
    return roh
