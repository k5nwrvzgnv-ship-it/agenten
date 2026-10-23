"""Kennzahlen je Kategorie und Korrekturliste aus den eingeordneten Aufgaben (Schritt 6).

Eingabe: Aufgaben nach einordnen.zusammenfuehren. Runden = bis - von + 1.
Runden bis Ergebnis = runde_ergebnis - von + 1 (nur Aufgaben mit Ergebnis).
Ohne Netz, getestet in tests/test_statistik.py.
"""

from collections import Counter
from statistics import mean, median


def runden(a: dict) -> int:
    return a["bis"] - a["von"] + 1


def bis_ergebnis(a: dict) -> int | None:
    r = a.get("runde_ergebnis")
    return r - a["von"] + 1 if isinstance(r, int) and a["von"] <= r <= a["bis"] else None


def je_kategorie(aufgaben: list[dict]) -> dict[str, dict]:
    gruppen: dict[str, list[dict]] = {}
    for a in aufgaben:
        gruppen.setdefault(a["kategorie"], []).append(a)
    aus = {}
    for kat, liste in sorted(gruppen.items(), key=lambda x: -len(x[1])):
        r = [runden(a) for a in liste]
        e = [x for x in (bis_ergebnis(a) for a in liste) if x is not None]
        k = [len(a["korrekturen"]) for a in liste]
        aus[kat] = {
            "aufgaben": len(liste),
            "runden_summe": sum(r),
            "runden_median": median(r),
            "runden_mittel": round(mean(r), 1),
            "bis_ergebnis_median": median(e) if e else None,
            "korrekturen_summe": sum(k),
            "korrekturen_je_aufgabe": round(mean(k), 2),
            "mit_korrektur": sum(1 for x in k if x),
            "korrekturarten": dict(Counter(x["art"] for a in liste for x in a["korrekturen"]).most_common()),
            "ergebnis": dict(Counter(a["ergebnis"] for a in liste).most_common()),
            "automatisierbar": dict(Counter(a["automatisierbar"] for a in liste).most_common()),
            "eingaben": dict(Counter(x for a in liste for x in a["eingaben"]).most_common()),
            "faecher": dict(Counter(a["fach"] for a in liste).most_common()),
            "belastung": sum(1 for a in liste if a["belastung"]),
        }
    return aus


def korrekturen(aufgaben: list[dict]) -> list[dict]:
    """Alle Korrekturen flach, mit Kategorie und Titel der Aufgabe."""
    return [{"chat": a["chat"], "runde": k["runde"], "art": k["art"], "zitat": k.get("zitat", ""),
             "kategorie": a["kategorie"], "aufgabe": a["titel"]}
            for a in aufgaben for k in a["korrekturen"]]
