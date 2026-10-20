"""Lernermodell eines Moduls: Karten, Wiederholungsplan (FSRS) und Auswertung.

Ablage in data/lernen/<modul>/ (nicht im Repo, Inhalte stammen aus den Skripten):
- pruefungsplan.json  Themen mit Score (siehe STATUS.md, Lernsystem)
- karten.json         Inhalt der Karten, Liste von {id, thema, typ, frage, antwort, quelle, bild}
                      typ "text" oder "bild"; bild ist ein Pfad relativ zum Agent-Ordner oder None
- zustand.json        FSRS-Stand je Karten-ID (fsrs.Card.to_dict())
- verlauf.jsonl       jede Bewertung: zeit, karte, thema, bewertung (1 Nochmal ... 4 Leicht)
Inhalt und Zustand sind getrennt, damit neu erzeugte Karten den Lernstand nicht löschen.

Geplant wird in Tagen (keine Lernschritte im Minutenbereich), weil Jan einmal am Tag abgefragt
wird. Eine falsch beantwortete Karte wiederholt die Sitzung selbst noch einmal (lernen.py).
"""

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import fsrs

BEWERTUNGEN = {"Nochmal": 1, "Schwer": 2, "Gut": 3, "Leicht": 4}
RICHTIG_AB = 3            # Gut oder Leicht zählt als Treffer
SEKUNDEN_PRO_KARTE = 45   # Schätzung; ergibt mit MINUTEN_PRO_TAG die Höchstzahl Karten
MINUTEN_PRO_TAG = 10
MAX_KARTEN = MINUTEN_PRO_TAG * 60 // SEKUNDEN_PRO_KARTE
NEUE_PRO_TAG = 8
SITZT_AB_TAGEN = 7        # Stabilität, ab der eine Karte als sicher gilt
MAX_ABSTAND_TAGE = 60     # bis zur Prüfung soll jede Karte mehrmals kommen

PLANER = fsrs.Scheduler(learning_steps=(), relearning_steps=(), maximum_interval=MAX_ABSTAND_TAGE)


class LernFehler(Exception):
    pass


def lies_json(pfad: Path, leer):
    if not pfad.exists():
        return leer
    return json.loads(pfad.read_text(encoding="utf-8"))


def schreibe_json(pfad: Path, daten) -> None:
    tmp = pfad.with_suffix(pfad.suffix + ".tmp")
    tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, pfad)


class Modul:
    def __init__(self, ordner: Path):
        self.ordner = Path(ordner)
        self.karten = {k["id"]: k for k in lies_json(self.ordner / "karten.json", [])}
        self.zustand = {i: fsrs.Card.from_dict(c) for i, c in lies_json(self.ordner / "zustand.json", {}).items()}
        plan = lies_json(self.ordner / "pruefungsplan.json", {"themen": []})
        self.themen = {t["id"]: t for t in plan["themen"]}
        verlauf = self.ordner / "verlauf.jsonl"
        self.verlauf = [json.loads(z) for z in verlauf.read_text(encoding="utf-8").splitlines() if z.strip()] \
            if verlauf.exists() else []

    def score(self, thema: str) -> int:
        return self.themen.get(thema, {}).get("score", 0)

    def bewerten(self, karte_id: str, bewertung: int, jetzt: datetime) -> datetime:
        """Bewertung speichern, gibt den nächsten Termin der Karte zurück."""
        if karte_id not in self.karten:
            raise LernFehler(f"Unbekannte Karte {karte_id}")
        if bewertung not in BEWERTUNGEN.values():
            raise LernFehler(f"Ungültige Bewertung {bewertung}")
        karte = self.zustand.get(karte_id) or fsrs.Card()
        if jetzt.tzinfo is None:
            raise LernFehler("Zeit ohne Zeitzone")
        karte, _ = PLANER.review_card(karte, fsrs.Rating(bewertung), jetzt.astimezone(timezone.utc))  # fsrs will UTC
        self.zustand[karte_id] = karte
        eintrag = {"zeit": jetzt.isoformat(), "karte": karte_id, "thema": self.karten[karte_id]["thema"],
                   "bewertung": bewertung}
        self.verlauf.append(eintrag)
        schreibe_json(self.ordner / "zustand.json", {i: c.to_dict() for i, c in self.zustand.items()})
        with open(self.ordner / "verlauf.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
        return karte.due

    def faellige(self, jetzt: datetime) -> list[str]:
        """Bereits gesehene Karten, deren Termin erreicht ist, am längsten überfällige zuerst."""
        ids = [i for i, c in self.zustand.items() if i in self.karten and c.due <= jetzt]
        return sorted(ids, key=lambda i: self.zustand[i].due)

    def neue_heute(self, jetzt: datetime) -> int:
        erste = {}
        for e in self.verlauf:
            erste.setdefault(e["karte"], e["zeit"])
        return sum(1 for z in erste.values() if datetime.fromisoformat(z).date() == jetzt.date())

    def neue(self) -> list[str]:
        """Ungesehene Karten: wichtige Themen zuerst, bei gleichem Score die mit schlechterer Trefferquote."""
        def quote(thema):
            richtig, gesamt = self.trefferquote(thema)
            return richtig / gesamt if gesamt else 1.0
        ids = [i for i in self.karten if i not in self.zustand]  # dict behält die Reihenfolge der Datei
        return sorted(ids, key=lambda i: (-self.score(self.karten[i]["thema"]), quote(self.karten[i]["thema"])))

    def auswahl(self, jetzt: datetime, max_karten: int = MAX_KARTEN, neue_max: int = NEUE_PRO_TAG) -> list[str]:
        """Karten für die heutige Abfrage: fällige vor neuen, dann über Themen gemischt."""
        frei_neu = max(0, neue_max - self.neue_heute(jetzt))
        ids = self.faellige(jetzt)[:max_karten]
        ids += self.neue()[:min(frei_neu, max_karten - len(ids))]
        return mischen(ids, lambda i: self.karten[i]["thema"])

    def trefferquote(self, thema: str | None = None, seit: datetime | None = None) -> tuple[int, int]:
        """(richtig, gesamt) über alle Bewertungen, optional je Thema und ab einem Zeitpunkt."""
        es = [e for e in self.verlauf if (thema is None or e["thema"] == thema)
              and (seit is None or datetime.fromisoformat(e["zeit"]) >= seit)]
        return sum(1 for e in es if e["bewertung"] >= RICHTIG_AB), len(es)

    def behaltensrate(self, seit: datetime | None = None) -> tuple[int, int]:
        """(behalten, gesamt) bei Wiederholungen schon gesehener Karten; behalten = nicht 'Nochmal'."""
        gesehen, behalten, gesamt = set(), 0, 0
        for e in self.verlauf:
            if e["karte"] in gesehen and (seit is None or datetime.fromisoformat(e["zeit"]) >= seit):
                gesamt += 1
                behalten += e["bewertung"] > 1
            gesehen.add(e["karte"])
        return behalten, gesamt

    def status(self, thema: str) -> str:
        """nicht gesehen / wackelig / sitzt (jede Karte mindestens zweimal, zuletzt richtig, stabil)."""
        ids = [i for i, k in self.karten.items() if k["thema"] == thema]
        if not any(i in self.zustand for i in ids):
            return "nicht gesehen"
        letzte, anzahl = {}, defaultdict(int)
        for e in self.verlauf:
            letzte[e["karte"]] = e["bewertung"]
            anzahl[e["karte"]] += 1
        sitzt = all(anzahl[i] >= 2 and letzte[i] >= RICHTIG_AB
                    and self.zustand[i].stability >= SITZT_AB_TAGEN for i in ids)
        return "sitzt" if sitzt else "wackelig"


def mischen(ids: list[str], thema_von) -> list[str]:
    """Reihum über die Themen, innerhalb eines Themas bleibt die Reihenfolge."""
    gruppen = defaultdict(list)
    for i in ids:
        gruppen[thema_von(i)].append(i)
    ergebnis = []
    while any(gruppen.values()):
        for thema in list(gruppen):
            if gruppen[thema]:
                ergebnis.append(gruppen[thema].pop(0))
    return ergebnis

