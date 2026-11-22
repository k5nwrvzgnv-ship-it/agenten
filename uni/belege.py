"""Belegpflicht für Lerninhalte: jede Aussage braucht eine Fundstelle, die es wirklich gibt.

Eine Fundstelle ist ein Text "<Kürzel> S. <Seiten>" oder "<Kürzel> Folie <Nummern>", mehrere mit ";" getrennt,
z. B. "SHB 01 S. 19; DIN 68800-4 S. 12". Das Kürzel steht im Quellenregister (JSON {"<Kürzel>": "<Pfad>"},
Pfad relativ zum Agent-Ordner, zur Datei oder ihrer Textfassung). Geprüft wird: Kürzel bekannt, Datei da,
Seite bzw. Folie innerhalb der Seitenzahl (aus "--- Seite N" bzw. "--- Folie N" der Textfassung, sonst aus dem PDF). Hat eine
Aussage ein Feld "zitat", muss es auf einer der genannten Seiten wörtlich stehen (Leerraum, Groß/klein,
Silbentrennung am Zeilenende und typografische Zeichen vereinheitlicht).

Geprüfte Dateien (Art nach Dateiname):
- blatt_<n>.json (Lernblatt im Renderer-Format): jeder Absatz, Listenpunkt, jede Tabelle, jeder Hinweis, jedes
  Rechenbeispiel und jede Lösung im Selbsttest braucht "quellen". art "norm" ist eine Fundstelle wie oben,
  "transkript" und "folie" werden über blatt_<n>.belege.json ({"transkript": "<Kürzel>", "folie": "<Kürzel>"})
  aufgelöst. Überschriften und offene Fragen sind keine Aussagen.
- karten*.json: jede Karte braucht im Feld "quelle" mindestens eine gültige Fundstelle.
- muendlich.json: jede Frage braucht "quellen" (Liste von Fundstellen) und eine Bewertung, deren Rubrikpunkte
  in rubrik.json (neben der Datei) stehen.
- pruefungsplan.json: jeder Eintrag in "dozent_signale" braucht "fundstelle" und ein wörtliches "zitat".
- *.md (aufbereitete Transkripte, Zusammenfassungen): jeder Listenpunkt braucht eine Seitenangabe
  "S. <n>" (Seite im Transkript). Mit --transkript <Kürzel> wird die Seite gegen das Register geprüft.
- *.belege.json eines Vortrags (Liste {"aussage", "quellen"}): jede Aussage braucht gültige Fundstellen.

Aufruf: .venv/bin/python belege.py <register.json> [--transkript <Kürzel>] <datei> ...
Ausgabe: je abgelehnter Aussage eine Zeile, Rückgabe 1, wenn etwas abgelehnt wurde.
"""

import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

HIER = Path(__file__).resolve().parent
SEITE = re.compile(r"^--- (?:Seite|Folie) (\d+)", re.M)  # pdf-Textfassung bzw. pptx-Textfassung
STELLE = re.compile(r"^(?P<kuerzel>.+?)\s+(?P<art>S\.|Folie|Folien)\s*(?P<zahlen>\d{1,4}(?:\s*[-–]\s*\d{1,4})?"
                    r"(?:\s*,\s*\d{1,4}(?:\s*[-–]\s*\d{1,4})?)*)(?P<rest>.*)$")
SEITENANGABE_MD = re.compile(r"\bS\.\s*(\d{1,4})(?:\s*[-–]\s*(\d{1,4}))?")
INHALT = ("absatz", "tabelle", "hinweis", "rechenbeispiel")


@dataclass
class Ablehnung:
    datei: str
    wo: str
    grund: str

    def __str__(self) -> str:
        return f"{self.datei}: {self.wo}: {self.grund}"


class Register:
    """Kürzel -> Datei, mit Seitenzahl und Seitentexten (zwischengespeichert)."""

    def __init__(self, eintraege: dict[str, str], basis: Path = HIER):
        self.eintraege = dict(eintraege)
        self.basis = Path(basis)
        self._seiten: dict[str, list[str]] = {}

    @classmethod
    def laden(cls, pfad: Path, basis: Path = HIER) -> "Register":
        return cls(json.loads(Path(pfad).read_text(encoding="utf-8")), basis)

    def seiten(self, kuerzel: str) -> list[str] | None:
        """Seitentexte (Index 0 = Seite 1); None, wenn die Datei fehlt."""
        if kuerzel in self._seiten:
            return self._seiten[kuerzel]
        pfad = self.basis / self.eintraege[kuerzel]
        txt = pfad if pfad.suffix == ".txt" else pfad.with_name(pfad.name + ".txt")
        seiten = None
        if txt.is_file():
            text = txt.read_text(encoding="utf-8", errors="replace")
            teile = SEITE.split(text)
            if len(teile) > 1:  # [vorspann, nr, text, nr, text, ...]
                nummern = [int(n) for n in teile[1::2]]
                seiten = [""] * max(nummern)
                for nr, inhalt in zip(nummern, teile[2::2], strict=True):
                    seiten[nr - 1] = inhalt
        if seiten is None and pfad.suffix.lower() == ".pdf" and pfad.is_file():
            import pypdf  # nur für Scans ohne Seitenmarken in der Textfassung
            seiten = [""] * len(pypdf.PdfReader(pfad).pages)
        self._seiten[kuerzel] = seiten
        return seiten


def normal(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)  # Silbentrennung am Zeilenende
    for alt, neu in (("„", '"'), ("“", '"'), ("”", '"'), ("‚", "'"), ("‘", "'"), ("’", "'"), ("–", "-"),
                     ("—", "-"), ("­", "")):
        text = text.replace(alt, neu)
    return " ".join(text.split()).casefold()


def zahlen(angabe: str) -> list[int]:
    """'4', '4-6', '4, 7-8' -> alle Seiten."""
    ergebnis = []
    for teil in re.split(r"\s*,\s*", angabe.strip()):
        m = re.fullmatch(r"(\d+)(?:\s*[-–]\s*(\d+))?", teil)
        von, bis = int(m.group(1)), int(m.group(2) or m.group(1))
        ergebnis += list(range(von, max(von, bis) + 1))
    return ergebnis


def stelle_pruefen(reg: Register, stelle: str, zitat: str | None = None) -> list[str]:
    """Fehler einer einzelnen Fundstelle ('<Kürzel> S. 4'); [] = gültig."""
    stelle = stelle.strip()
    m = STELLE.match(stelle)
    if not m:
        return [f"keine Fundstelle der Form '<Kürzel> S. <Seite>': {stelle!r}"]
    kuerzel = m.group("kuerzel").strip()
    if kuerzel not in reg.eintraege:
        return [f"Quelle {kuerzel!r} steht nicht im Register"]
    seiten = reg.seiten(kuerzel)
    if seiten is None:
        return [f"Datei zu {kuerzel!r} fehlt oder hat keine Seiten: {reg.eintraege[kuerzel]}"]
    nummern = zahlen(m.group("zahlen"))
    zu_gross = [n for n in nummern if not 1 <= n <= len(seiten)]
    if zu_gross:
        return [f"{kuerzel}: Seite {zu_gross[0]} gibt es nicht (Datei hat {len(seiten)} Seiten)"]
    if zitat:
        gesucht = normal(zitat)
        # Zitate dürfen über eine Seitengrenze laufen: Folgeseite mitnehmen
        text = normal(" ".join(seiten[n - 1] + " " + (seiten[n] if n < len(seiten) else "") for n in nummern))
        if gesucht not in text:
            return [f"Zitat steht nicht auf {kuerzel} S. {m.group('zahlen')}: {zitat[:80]!r}"]
    return []


def fundstellen_pruefen(reg: Register, angabe, zitat: str | None = None) -> list[str]:
    """Fehler einer Angabe aus einer oder mehreren Fundstellen (Text mit ';' oder Liste)."""
    teile = angabe if isinstance(angabe, list) else str(angabe or "").split(";")
    teile = [t for t in (str(x).strip() for x in teile) if t]
    if not teile:
        return ["keine Fundstelle"]
    fehler = []
    for t in teile:
        fehler += stelle_pruefen(reg, t)
    if zitat and not fehler and all(stelle_pruefen(reg, t, zitat) for t in teile):
        fehler.append(f"Zitat auf keiner der genannten Seiten gefunden: {zitat[:80]!r}")
    return fehler


# --- Lernblätter ------------------------------------------------------------------------------------------

def _blatt_quellen(reg: Register, quellen, zuordnung: dict) -> list[str]:
    if not quellen:
        return ["keine Quellen"]
    fehler = []
    for q in quellen:
        art, stelle = q.get("art"), str(q.get("stelle", ""))
        if art == "norm":
            fehler += stelle_pruefen(reg, stelle)
        elif art in ("transkript", "folie"):
            kuerzel = zuordnung.get(art)
            if not kuerzel:
                fehler.append(f"Quelle art {art!r} ohne Zuordnung in .belege.json")
            else:
                fehler += stelle_pruefen(reg, f"{kuerzel} {'S.' if art == 'transkript' else 'Folie'} {stelle}")
        else:
            fehler.append(f"unbekannte Quellenart {art!r}")
    return fehler


def lernblatt_pruefen(reg: Register, pfad: Path) -> list[Ablehnung]:
    blatt = json.loads(pfad.read_text(encoding="utf-8"))
    seite = pfad.with_name(pfad.stem + ".belege.json")
    zuordnung = json.loads(seite.read_text(encoding="utf-8")) if seite.exists() else {}
    abl = []

    def melde(wo, fehler, text=""):
        for f in fehler:
            abl.append(Ablehnung(pfad.name, wo, f + (f" | {text[:70]}" if text else "")))

    for i, b in enumerate(blatt.get("bloecke", [])):
        typ = b.get("typ")
        if typ in INHALT:
            melde(f"bloecke[{i}] {typ}", _blatt_quellen(reg, b.get("quellen"), zuordnung),
                  b.get("text") or b.get("titel") or b.get("aufgabe") or "")
        elif typ == "liste":
            for j, p in enumerate(b.get("punkte", [])):
                if isinstance(p, str):
                    melde(f"bloecke[{i}].punkte[{j}]", ["keine Quellen"], p)
                else:
                    melde(f"bloecke[{i}].punkte[{j}]", _blatt_quellen(reg, p.get("quellen"), zuordnung),
                          p.get("text", ""))
    for i, s in enumerate(blatt.get("selbsttest", [])):
        melde(f"selbsttest[{i}]", _blatt_quellen(reg, s.get("quellen"), zuordnung), s.get("frage", ""))
    return abl


# --- Karten, mündliche Fragen, Prüfungsplan, Vortrag --------------------------------------------------------

def karten_pruefen(reg: Register, pfad: Path, nur_herkunft: str | None = None) -> list[Ablehnung]:
    abl = []
    for k in json.loads(pfad.read_text(encoding="utf-8")):
        if nur_herkunft and k.get("herkunft") != nur_herkunft:
            continue
        for f in fundstellen_pruefen(reg, k.get("quelle")):
            abl.append(Ablehnung(pfad.name, k.get("id") or k.get("frage", "")[:40], f))
    return abl


def muendlich_pruefen(reg: Register, pfad: Path) -> list[Ablehnung]:
    rubrik_pfad = pfad.with_name("rubrik.json")
    punkte = {p["id"] for p in json.loads(rubrik_pfad.read_text(encoding="utf-8"))["punkte"]} \
        if rubrik_pfad.exists() else set()
    abl = []
    for nr, f in enumerate(json.loads(pfad.read_text(encoding="utf-8")).get("fragen", []), 1):
        wo = f"Frage {nr} ({f.get('thema', '?')})"
        for fehler in fundstellen_pruefen(reg, f.get("quellen")):
            abl.append(Ablehnung(pfad.name, wo, fehler))
        if not str(f.get("musterantwort", "")).strip():
            abl.append(Ablehnung(pfad.name, wo, "keine Musterantwort"))
        bew = f.get("bewertung") or {}
        ids = bew.get("rubrik") or []
        if not ids:
            abl.append(Ablehnung(pfad.name, wo, "Bewertung ohne Rubrikpunkt"))
        for i in ids:
            if i not in punkte:
                abl.append(Ablehnung(pfad.name, wo, f"Rubrikpunkt {i!r} steht nicht in rubrik.json"))
        if not all(str(bew.get(s, "")).strip() for s in ("erfuellt", "teilweise", "nicht")):
            abl.append(Ablehnung(pfad.name, wo, "Bewertung braucht erfuellt, teilweise und nicht"))
    return abl


def plan_pruefen(reg: Register, pfad: Path) -> list[Ablehnung]:
    abl = []
    for t in json.loads(pfad.read_text(encoding="utf-8")).get("themen", []):
        for nr, s in enumerate(t.get("dozent_signale", []), 1):
            if not str(s.get("zitat", "")).strip():
                abl.append(Ablehnung(pfad.name, f"{t['id']} Signal {nr}", "kein wörtliches Zitat"))
                continue
            for f in fundstellen_pruefen(reg, s.get("fundstelle"), s.get("zitat")):
                abl.append(Ablehnung(pfad.name, f"{t['id']} Signal {nr}", f))
    return abl


def aussagen_pruefen(reg: Register, pfad: Path) -> list[Ablehnung]:
    abl = []
    for nr, a in enumerate(json.loads(pfad.read_text(encoding="utf-8")), 1):
        for f in fundstellen_pruefen(reg, a.get("quellen"), a.get("zitat")):
            abl.append(Ablehnung(pfad.name, f"Aussage {nr}: {str(a.get('aussage', ''))[:50]}", f))
    return abl


def markdown_pruefen(reg: Register, pfad: Path, transkript: str | None = None) -> list[Ablehnung]:
    """Jeder Listenpunkt (auch eingerückt) braucht 'S. <n>'; mit transkript auch gegen dessen Seitenzahl."""
    seiten = reg.seiten(transkript) if transkript else None
    abl = []
    zeilen = pfad.read_text(encoding="utf-8").splitlines()
    for nr, z in enumerate(zeilen, 1):
        if not re.match(r"^\s*[-*] ", z):
            continue
        # Ein Punkt darf über mehrere Zeilen laufen: Folgezeilen ohne neuen Punkt gehören dazu
        text, k = z, nr
        while k < len(zeilen) and zeilen[k].strip() and not re.match(r"^\s*([-*] |#)", zeilen[k]):
            text += " " + zeilen[k].strip()
            k += 1
        angaben = SEITENANGABE_MD.findall(text)
        if not angaben:
            abl.append(Ablehnung(pfad.name, f"Zeile {nr}", f"Listenpunkt ohne Seitenangabe | {z.strip()[:70]}"))
        elif seiten is not None:
            for von, bis in angaben:
                if not 1 <= int(bis or von) <= len(seiten):
                    abl.append(Ablehnung(pfad.name, f"Zeile {nr}", f"Seite {bis or von} gibt es im Transkript nicht"))
    return abl


def pruefen(reg: Register, pfad: Path, transkript: str | None = None) -> list[Ablehnung]:
    name = pfad.name
    if name.endswith(".belege.json") and not re.match(r"^blatt_\d+\.belege\.json$", name):
        return aussagen_pruefen(reg, pfad)
    if re.match(r"^blatt_\d+\.json$", name):
        return lernblatt_pruefen(reg, pfad)
    if name.startswith("karten") and name.endswith(".json"):
        return karten_pruefen(reg, pfad)
    if name == "muendlich.json":
        return muendlich_pruefen(reg, pfad)
    if name == "pruefungsplan.json":
        return plan_pruefen(reg, pfad)
    if name.endswith(".md"):
        return markdown_pruefen(reg, pfad, transkript)
    return [Ablehnung(name, "-", "unbekannte Dateiart, nicht geprüft")]


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__.strip().splitlines()[-3])
        return 2
    reg = Register.laden(Path(argv[1]))
    rest, transkript = argv[2:], None
    if rest[:1] == ["--transkript"]:
        transkript, rest = rest[1], rest[2:]
    alle = []
    for d in rest:
        alle += pruefen(reg, Path(d), transkript)
    for a in alle:
        print(a)
    print(f"{len(rest)} Dateien geprüft, {len(alle)} Aussagen abgelehnt.")
    return 1 if alle else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
