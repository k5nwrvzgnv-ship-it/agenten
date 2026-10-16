"""Jans eigene Vorlesungstranskripte übernehmen (aus Telegram-Aufträgen, ohne Netz, testbar).

Auftrag: erste Zeile "Transkript <Kurs> [TT.MM.[JJJJ]]", dazu eine oder mehrere Dateien
(txt, md, docx, pdf ...) oder der Text direkt unter der ersten Zeile.
Abgelegt wird nach data/kurse/<Kurs>/transkripte/<JJJJ-MM-TT>_transkript.txt (ohne Datum: heute).
Den Kurs findet kurs_finden über die Ordnernamen in data/kurse/. Ist er nicht eindeutig,
kommt TranskriptFehler mit den Kandidaten zurück, und Jan schickt es noch einmal.
"""

import re
from datetime import date
from pathlib import Path

import kurse

DATEI_MARKE = "\n\nAngehängte Dateien von Jan"  # so hängt agentkit.auftraege die Pfade an
DATUM = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4}|\d{2})?(?=\s|$)")


class TranskriptFehler(Exception):
    pass


def ist_transkript(text: str) -> bool:
    return text.strip().lower().startswith("transkript")


def kopf_lesen(text: str, heute: date) -> tuple[str, date, str]:
    """(Kursangabe, Datum, Text unter der ersten Zeile) aus dem Auftragstext."""
    text = text.split(DATEI_MARKE)[0].strip()
    erste, _, rest = text.partition("\n")
    angabe = re.sub(r"(?i)^transkripte?\s*:?\s*", "", erste.strip())
    datum = heute
    if treffer := DATUM.search(angabe):
        tag, monat, jahr = treffer.groups()
        jahr = int(jahr) + 2000 if jahr and len(jahr) == 2 else int(jahr or heute.year)
        try:
            datum = date(jahr, int(monat), int(tag))
        except ValueError:
            raise TranskriptFehler(f"Datum nicht lesbar: {treffer.group(0)}") from None
        angabe = (angabe[:treffer.start()] + angabe[treffer.end():]).strip()
    return angabe.strip(" ,-:"), datum, rest.strip()


def kurs_finden(angabe: str, kursnamen: list[str]) -> list[str]:
    """Kurse, deren Name alle Wörter der Angabe enthält (ohne Groß/Klein). Exakter Name gewinnt."""
    woerter = [w for w in re.findall(r"\w+", angabe.lower()) if len(w) >= 2]
    if not woerter:
        return []
    exakt = [k for k in kursnamen if k.lower() == angabe.lower()]
    return exakt or [k for k in kursnamen if all(w in k.lower() for w in woerter)]


def _freier_pfad(ordner: Path, datum: date) -> Path:
    pfad, n = ordner / f"{datum.isoformat()}_transkript.txt", 2
    while pfad.exists():
        pfad, n = ordner / f"{datum.isoformat()}_transkript-{n}.txt", n + 1
    return pfad


def ablegen(auftrag: dict, agent_dir: Path, ziel: Path, heute: date) -> tuple[str, list[Path]]:
    """Legt die Transkripte ab. Gibt (Kursordner, Pfade) zurück."""
    angabe, datum, rest = kopf_lesen(auftrag["text"], heute)
    kursnamen = sorted(p.name for p in ziel.iterdir() if p.is_dir() and not p.name.startswith("."))
    treffer = kurs_finden(angabe, kursnamen)
    if len(treffer) != 1:
        auswahl = treffer or kursnamen
        raise TranskriptFehler(
            f"Kurs {'nicht eindeutig' if treffer else 'nicht gefunden'}: \"{angabe}\". Bitte noch einmal schicken, "
            "erste Zeile z. B. \"Transkript Bauklimatik 14.10.\". Mögliche Kurse:\n"
            + "\n".join(f"- {k}" for k in auswahl))
    texte = []
    for datei in auftrag.get("dateien") or []:
        pfad = agent_dir / datei
        if pfad.suffix.lower() in (".txt", ".md", ".text", ""):
            texte.append(pfad.read_text(encoding="utf-8", errors="replace"))
        elif (text := kurse.als_text(pfad)) is not None:
            texte.append(text)
        else:
            raise TranskriptFehler(f"Dateiformat nicht lesbar: {pfad.name}. Bitte als .txt schicken.")
    if not texte and rest:
        texte.append(rest)
    if not any(t.strip() for t in texte):
        raise TranskriptFehler("Kein Transkript-Text gefunden: Datei anhängen oder Text unter die erste Zeile.")
    ordner = ziel / treffer[0] / "transkripte"
    ordner.mkdir(parents=True, exist_ok=True)
    pfade = []
    for text in texte:
        inhalt = f"Transkript von Jan, Vorlesung {datum:%d.%m.%Y}, Kurs {treffer[0]}\n\n{text.strip()}\n"
        # Schon da (Auftrag wurde nach einer Wartepause erneut verarbeitet)? Dann nicht doppelt ablegen.
        gleich = [p for p in ordner.glob(f"{datum.isoformat()}_transkript*.txt") if p.read_text(encoding="utf-8") == inhalt]
        pfad = gleich[0] if gleich else _freier_pfad(ordner, datum)
        pfad.write_text(inhalt, encoding="utf-8")
        pfade.append(pfad)
    return treffer[0], pfade
