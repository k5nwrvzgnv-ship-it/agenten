"""Abfragekarten für ein Modul erzeugen und prüfen.

Claude denkt, Python handelt: Claude schreibt Kartenentwürfe nach
data/lernen/<modul>/karten_entwurf.json, Python prüft sie, vergibt feste IDs und übernimmt
neue Karten nach karten.json. Vorhandene Karten und ihr Lernstand (zustand.json) bleiben.

Bildkarten: Die Infokarten (Thünen-Steckbriefe, je Art ein Bild mit vier Fotos, Name oben,
Merkmale unten) schneidet Python zweimal aus: bilder/<praefix>-<n>-frage.jpg nur die Fotos
ohne Beschriftung (der Name stünde sonst auf der Frage), bilder/<praefix>-<n>-ganz.jpg die ganze
Seite, aus der Claude Name und Merkmale für die Antwort liest.

Welche Kurse und Bildquellen zu einem Modul gehören, steht in pruefungsplan.json
(Felder kurse, bildquellen). Aufruf von Hand: .venv/bin/python karten.py <modul>
"""

import hashlib
import io
import json
import sys
from pathlib import Path

import pypdf
from agentkit import claude_lauf, log
from PIL import Image

import lernmodell

AGENT = "uni"
HIER = Path(__file__).resolve().parent
LERNEN = HIER / "data" / "lernen"
logger = log.hole_logger(HIER, AGENT)

# Fotobereich der Infokarten ohne Bildunterschriften (Anteil der Bildhöhe, ausprobiert 20.10.)
FOTOS_OBEN, FOTOS_UNTEN = 0.165, 0.662
TYPEN = ("text", "bild")
FELDER = ("thema", "typ", "frage", "antwort", "quelle")
ANZAHL = {5: "8 bis 12", 4: "4 bis 6", 3: "2 bis 3"}

PROMPT = """Erstelle Abfragekarten für Jans mündliche Prüfung im Modul "{modul}".

Ziel: Jan soll mit wenig Aufwand bestehen. Karten sind Fragen, die er aus dem Gedächtnis
beantwortet, keine Fakten zum Lesen.

Lies zuerst data/lernen/{ordner}/pruefungsplan.json (Themen mit id, Score, Lernzielen, Quellen).
Material: {kurse} (je uebersicht.md und Textfassungen *.txt mit "--- Seite N"; per Grep suchen,
nicht alles lesen). Infokarten als ganze Seite (Name und Merkmale): {ganz}

Schreibe die Karten als JSON-Liste nach data/lernen/{ordner}/karten_entwurf.json, sonst nichts.
Felder je Karte: thema (id aus dem Plan), typ ("text" oder "bild"), frage, antwort, quelle,
bei typ "bild" zusätzlich bild (Pfad der passenden -frage.jpg).

Regeln:
- Nur Themen mit Score {min_score} oder mehr. Anzahl je Thema: {anzahl}.
- Prüfungsstil: erklären, abgrenzen, bestimmen, Fall begründen. Keine Ja/Nein-Fragen, die Frage
  verrät die Antwort nicht. Mindestens ein Drittel Fallfragen (konkrete Lage am Bau, Jan soll
  Diagnose oder Maßnahme begründen).
- Antwort: was Jan in der Prüfung sagen müsste, höchstens 5 kurze Zeilen.
- Nur aus dem Material, nichts erfinden. quelle = Datei und Seite (z. B. "SHB_01 S. 22").
  Steht etwas nur in einer Norm, die nicht vorliegt, lass die Karte weg.
- Bildkarten: je Infokarte genau eine Karte, Frage "Welcher Schädling ist das, woran erkennst du
  ihn, und was folgt daraus?", bild = die -frage.jpg, Antwort: Name, 2 bis 3 Merkmale aus der
  ganzen Seite und die Folge (Fäuletyp bzw. Trocken-/Frischholz, Sanierung) aus dem Material.
- Bestehende Karten nicht wiederholen: {vorhanden}

Antworte zum Schluss mit einer Zeile: Anzahl Karten je Thema."""


def bilder_schneiden(pdf: Path, ziel: Path, praefix: str) -> list[tuple[Path, Path]]:
    """Schneidet jede Infokarte aus dem PDF; gibt (frage.jpg, ganz.jpg) je Karte zurück."""
    ziel.mkdir(parents=True, exist_ok=True)
    paare, n = [], 0
    for seite in pypdf.PdfReader(pdf).pages:
        for bild in seite.images:
            n += 1
            im = Image.open(io.BytesIO(bild.data)).convert("RGB")
            frage, ganz = ziel / f"{praefix}-{n}-frage.jpg", ziel / f"{praefix}-{n}-ganz.jpg"
            im.save(ganz, quality=85)
            w, h = im.size
            im.crop((0, int(h * FOTOS_OBEN), w, int(h * FOTOS_UNTEN))).save(frage, quality=85)
            paare.append((frage, ganz))
    return paare


def karte_id(karte: dict) -> str:
    """Fest aus Thema und Frage, damit dieselbe Karte bei neuer Erzeugung dieselbe ID behält."""
    return f"{karte['thema']}-{hashlib.sha1(karte['frage'].strip().encode()).hexdigest()[:8]}"


def pruefen(entwurf, themen: set[str], basis: Path) -> tuple[list[dict], list[str]]:
    """Gültige Karten (mit id) und Fehlermeldungen. basis: Ordner, gegen den bild aufgelöst wird."""
    if not isinstance(entwurf, list):
        return [], ["Entwurf ist keine Liste"]
    gueltig, fehler = [], []
    for nr, k in enumerate(entwurf, 1):
        if not isinstance(k, dict):
            fehler.append(f"Karte {nr}: kein Objekt")
            continue
        fehlt = [f for f in FELDER if not isinstance(k.get(f), str) or not k[f].strip()]
        if fehlt:
            fehler.append(f"Karte {nr}: Feld fehlt oder leer: {', '.join(fehlt)}")
            continue
        if k["thema"] not in themen:
            fehler.append(f"Karte {nr}: unbekanntes Thema {k['thema']!r}")
            continue
        if k["typ"] not in TYPEN:
            fehler.append(f"Karte {nr}: unbekannter Typ {k['typ']!r}")
            continue
        bild = k.get("bild") if k["typ"] == "bild" else None
        if k["typ"] == "bild" and not (isinstance(bild, str) and bild.endswith("-frage.jpg")
                                       and (basis / bild).is_file()):
            fehler.append(f"Karte {nr}: Bild fehlt oder ist kein Fragebild: {bild!r}")
            continue
        karte = {f: k[f].strip() for f in FELDER} | {"bild": bild}
        gueltig.append({"id": karte_id(karte)} | karte)
    return gueltig, fehler


def uebernehmen(ordner: Path, karten: list[dict]) -> int:
    """Neue Karten an karten.json anhängen; gibt die Zahl der neuen zurück."""
    pfad = ordner / "karten.json"
    alle = lernmodell.lies_json(pfad, [])
    ids = {k["id"] for k in alle}
    neu = []
    for k in karten:
        if k["id"] not in ids:
            ids.add(k["id"])
            neu.append(k)
    lernmodell.schreibe_json(pfad, alle + neu)
    return len(neu)


def erzeugen(modul: str, min_score: int = 4) -> str:
    """Bilder schneiden, Claude Entwürfe schreiben lassen, prüfen, übernehmen. Gibt eine Zusammenfassung."""
    ordner = LERNEN / modul
    plan = json.loads((ordner / "pruefungsplan.json").read_text(encoding="utf-8"))
    ganz = []
    for q in plan.get("bildquellen", []):
        ganz += [g for _, g in bilder_schneiden(HIER / q["pdf"], ordner / "bilder", q["praefix"])]
    vorhanden = [k["frage"] for k in lernmodell.lies_json(ordner / "karten.json", [])]
    entwurf_pfad = ordner / "karten_entwurf.json"
    entwurf_pfad.unlink(missing_ok=True)
    prompt = PROMPT.format(
        modul=plan["modul"], ordner=modul, min_score=min_score,
        kurse=", ".join(f"data/kurse/{k}/" for k in plan["kurse"]),
        ganz=", ".join(str(g.relative_to(HIER)) for g in ganz) or "keine",
        anzahl=", ".join(f"Score {s}: {a}" for s, a in ANZAHL.items() if s >= min_score),
        vorhanden=json.dumps(vorhanden, ensure_ascii=False) if vorhanden else "keine")
    e = claude_lauf.laufen(AGENT, HIER, prompt, art="anspruchsvoll")
    if not entwurf_pfad.exists():
        raise lernmodell.LernFehler(f"Claude hat keinen Entwurf geschrieben: {e.text[:300]}")
    try:
        entwurf = json.loads(entwurf_pfad.read_text(encoding="utf-8"))
    except json.JSONDecodeError as f:
        raise lernmodell.LernFehler(f"Entwurf ist kein gültiges JSON: {f}") from f
    gueltig, fehler = pruefen(entwurf, {t["id"] for t in plan["themen"]}, HIER)
    for f in fehler:
        logger.warning("Karten %s: %s", modul, f)
    neu = uebernehmen(ordner, gueltig)
    return f"{neu} neue Karten ({len(gueltig)} gültig, {len(fehler)} verworfen). Claude: {e.text.strip()[-300:]}"


if __name__ == "__main__":
    print(erzeugen(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4))
