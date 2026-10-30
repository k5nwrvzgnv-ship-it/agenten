"""Neue Aufträge aus Lias Web-App (Plan Jan 30.10.2026, board-plan.md Punkt 8). Reine Logik, ohne Netz.

Art steht am Anfang des Texts: „Spielfassung: <Stück>“ oder „Szenenaufgabe: <Thema>“. Darunter Zeilen
„Schlüssel: Wert“, z. B. bei der Spielfassung „Länge: 35–40 Minuten“, „Spieler*innen: 18“, „Was bleiben muss: …“.
Fehlt eine Angabe, gilt theater.toml. Eine neue Länge rechnet Lias Zeitplan je Teil anteilig um; was bleiben muss,
wird ein zusätzliches Kriterium der Rubrik (Python prüft weiter nur die feste Muss-Liste aus theater.toml).
"""

import copy
import re

QUELLE = "portal-theater"
ARTEN = {"spielfassung": "spielfassung:", "szenenaufgabe": "szenenaufgabe:"}
BLEIBEN_MAX = 1500
SPIELER_MAX = 40
MINUTEN = (5, 120)  # plausible Länge einer Fassung
EINZELWERT_SPIEL = 2  # „Länge: 30 Minuten“ heißt 28–32 Minuten (fassung.pruefen braucht einen Bereich)

# Schlüssel im Text -> Feld (klein, ohne „*innen“ und Leerzeichen am Rand)
SCHLUESSEL = {"länge": "laenge", "laenge": "laenge", "dauer": "laenge", "spieler": "spieler", "spielerinnen": "spieler",
              "sus": "spieler", "personen": "spieler", "was bleiben muss": "bleiben", "bleiben muss": "bleiben",
              "muss bleiben": "bleiben", "reihe": "reihe"}
_ZEILE = re.compile(r"\s*([^:\n]{1,40}):\s*(.*)")


class WunschFehler(Exception):
    """Auftrag nicht lesbar. Der Text ist für Jan."""


def art(auftrag: dict) -> str | None:
    """„spielfassung“, „szenenaufgabe“ oder None (Nachbesserung wie bisher)."""
    erste = (auftrag.get("text") or "").lstrip().split("\n", 1)[0].lower()
    for name, anfang in ARTEN.items():
        if erste.startswith(anfang):
            return name
    if auftrag.get("quelle") == QUELLE and not auftrag.get("bezug"):
        raise WunschFehler("Auftrag aus der Web-App beginnt weder mit „Spielfassung:“ noch mit „Szenenaufgabe:“")
    return None


def _schluessel(roh: str) -> str:
    k = roh.strip().lower().replace("*innen", "innen").replace("*", "")
    return SCHLUESSEL.get(k, k)


def felder(text: str) -> dict[str, str]:
    """Erste Zeile unter „titel“, danach „Schlüssel: Wert“; Zeilen ohne Schlüssel gehören zum Feld davor."""
    zeilen = text.strip().splitlines()
    if not zeilen:
        return {}
    erg = {"titel": zeilen[0].split(":", 1)[1].strip() if ":" in zeilen[0] else ""}
    letzter = "titel"
    for z in zeilen[1:]:
        m = _ZEILE.match(z)
        if m and _schluessel(m.group(1)) in SCHLUESSEL.values():
            letzter = _schluessel(m.group(1))
            erg[letzter] = m.group(2).strip()
        elif z.strip():
            erg[letzter] = f"{erg.get(letzter, '')}\n{z.strip()}".strip()
    return erg


def laenge(wert: str) -> tuple[float, float]:
    zahlen = [float(z.replace(",", ".")) for z in re.findall(r"\d+(?:[.,]\d+)?", wert)]
    if not zahlen:
        raise WunschFehler(f"Länge ohne Zahl: {wert!r}")
    von, bis = (zahlen[0], zahlen[1]) if len(zahlen) > 1 else (zahlen[0] - EINZELWERT_SPIEL,
                                                               zahlen[0] + EINZELWERT_SPIEL)
    if not MINUTEN[0] <= von <= bis <= MINUTEN[1]:
        raise WunschFehler(f"Länge nicht plausibel: {wert!r}")
    return von, bis


def spielfassung_angaben(text: str) -> dict:
    """Stück, minuten_min/max, spieler, bleiben (None, wenn nicht angegeben) und der Text selbst."""
    f = felder(text)
    a = {"text": text.strip(), "stueck": f.get("titel", ""), "minuten_min": None, "minuten_max": None,
         "spieler": None, "bleiben": (f.get("bleiben") or "").strip() or None}
    if f.get("laenge"):
        a["minuten_min"], a["minuten_max"] = laenge(f["laenge"])
    if f.get("spieler"):
        m = re.search(r"\d+", f["spieler"])
        if not m or not 1 <= int(m.group()) <= SPIELER_MAX:
            raise WunschFehler(f"Spieler*innen nicht lesbar: {f['spieler']!r}")
        a["spieler"] = int(m.group())
    if a["bleiben"] and len(a["bleiben"]) > BLEIBEN_MAX:
        raise WunschFehler(f"„Was bleiben muss“ ist länger als {BLEIBEN_MAX} Zeichen")
    return a


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^\wäöüß ]", " ", s.lower()).split())


def stueck_passt(angabe: str, titel: str) -> bool:
    """Kein Stück genannt oder das aus theater.toml (auch „Noises Off“)."""
    a, t = _norm(angabe), _norm(titel)
    return not a or t in a or a in t or "noises off" in a


def anpassen(v: dict, a: dict) -> dict:
    """Vorgaben (theater.toml) mit Lias Angaben; das Original bleibt unverändert."""
    v = copy.deepcopy(v)
    r = v["rahmen"]
    if a.get("minuten_min") is not None:
        faktor = (a["minuten_min"] + a["minuten_max"]) / (r["minuten_min"] + r["minuten_max"])
        for t in r["teile"]:
            t["minuten"] = max(1.0, round(t["minuten"] * faktor * 2) / 2)
        r["minuten_min"], r["minuten_max"] = a["minuten_min"], a["minuten_max"]
    if a.get("spieler") and a["spieler"] != r["spieler"]:
        alt = str(r["spieler"])
        for k in v["kriterium"]:
            if k["id"] == "ensemble":
                for feld in ("name", "frage", "gut"):
                    k[feld] = k[feld].replace(alt, str(a["spieler"]))
        r["spieler"] = a["spieler"]
    if a.get("bleiben"):
        v["kriterium"].append({
            "id": "auftrag", "name": "Lias Auftrag umgesetzt",
            "frage": "Ist spielbar umgesetzt, was Lia in ihrem Auftrag als unverzichtbar nennt: " + a["bleiben"],
            "gut": "Jeder Punkt aus Lias Auftrag hat einen erkennbaren, spielbaren Moment im Ablauf.",
            "quelle": "Lias Auftrag aus der Web-App"})
    return v


def vorgaben_abschnitt(a: dict) -> str:
    """Abschnitt für vorgaben.md: Lias Auftrag geht bei Widerspruch vor (Rahmen ist schon angepasst)."""
    return ("## Lias Auftrag für diese Fassung (geht bei Widerspruch vor; Rahmen und Zeitplan oben sind schon "
            "angepasst)\n" + a["text"] + "\n")
