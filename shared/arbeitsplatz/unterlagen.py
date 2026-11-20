"""Unterlagen am Ordner: Verweise auf Dateien, die kein Auftrag ist (Haupt-STATUS 45c b, Jans Okay 20.11.2026).

Datei <instanz>/orte-verweise.json (wie orte-zuordnung.json, nicht im Repo):
  {"verweise": {"<ort>": ["<pfad>", {"pfad": "<pfad>", "titel": "<Anzeige>"}, ...]}}
Pfade relativ zum Hauptordner (neben der Instanz). Ein Verweis auf eine Datei zeigt sie, auf einen Ordner alle Dateien
darin (bis zwei Ebenen tief), neueste zuerst. Nur lesend und immer aktuell, nichts wird kopiert.

Erlaubt sind nur Pfade unter WURZELN, nichts Verstecktes, kein "..", aufgelöst (auch Symlinks) innerhalb der Wurzel,
nur ENDUNGEN; von .json nur schriftverkehr.json (Auszug von uni, als Mailliste). Sonst steht der Verweis nicht da.
In URLs stehen Ordner und Nummer ("<n>" bzw. "<n>-<m>" für die m-te Datei eines Ordner-Verweises), nie ein Pfad.
"""

import json
import re
from pathlib import Path

WURZELN = ("fehlstellenscan/docs", "fehlstellenscan/unterlagen", "fehlstellenscan/data/gruppe/dateien",
           "uni/data/projekte")
TEXT = {".md", ".txt"}
SEITEN = {".pdf", ".docx", ".pptx", ".xlsx"}
BILD = {".png", ".jpg", ".jpeg"}
SCHRIFTVERKEHR = "schriftverkehr.json"
ENDUNGEN = TEXT | SEITEN | BILD | {".json"}
MAX_TIEFE = 2
MAX_DATEIEN = 200  # je Ordner-Verweis
MAX_VERWEISE = 100  # je Ort
MAX_TITEL = 120
NR = re.compile(r"(\d{1,3})(?:-(\d{1,4}))?")


def erlaubt(relativ: str) -> bool:
    """Nur nach dem Text: relativ, ohne "..", nichts Verstecktes, unter einer der WURZELN (oder sie selbst)."""
    if not isinstance(relativ, str) or not relativ.strip() or "\\" in relativ:
        return False
    teile = relativ.strip("/").split("/")
    if relativ.startswith("/") or any(not t or t.startswith(".") for t in teile):
        return False
    rel = Path(relativ)
    return any(rel.parts[:len(Path(w).parts)] == Path(w).parts for w in WURZELN)


def pruefen(daten) -> dict[str, list[dict]]:
    """Inhalt von orte-verweise.json -> {ort: [{"pfad", "titel"}]}, nur gültige Einträge (titel "" = aus der Datei)."""
    roh = daten.get("verweise") if isinstance(daten, dict) else None
    if not isinstance(roh, dict):
        return {}
    ergebnis = {}
    for ort, liste in roh.items():
        if not isinstance(ort, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", ort) or not isinstance(liste, list):
            continue
        gut = []
        for v in liste[:MAX_VERWEISE]:
            pfad, titel = (v, "") if isinstance(v, str) else (v.get("pfad"), v.get("titel") or "") \
                if isinstance(v, dict) else (None, "")
            if erlaubt(pfad) and isinstance(titel, str):
                gut.append({"pfad": pfad.strip("/"), "titel": " ".join(titel.split())[:MAX_TITEL]})
        if gut:
            ergebnis[ort] = gut
    return ergebnis


def _wurzel(haupt: Path, relativ: str) -> Path | None:
    rel = Path(relativ)
    for w in WURZELN:
        if rel.parts[:len(Path(w).parts)] == Path(w).parts:
            return (haupt / w).resolve()
    return None


def aufloesen(haupt: Path, relativ: str) -> Path | None:
    """Datei oder Ordner des Verweises, nur wenn er (aufgelöst) in seiner Wurzel liegt und da ist."""
    if not erlaubt(relativ):
        return None
    wurzel = _wurzel(haupt, relativ)
    pfad = (haupt / relativ).resolve()
    if wurzel is None or not pfad.is_relative_to(wurzel) or not pfad.exists():
        return None
    return pfad


def zeigbar(pfad: Path) -> bool:
    endung = pfad.suffix.lower()
    if pfad.name.startswith(".") or endung not in ENDUNGEN or not pfad.is_file():
        return False
    return endung != ".json" or pfad.name == SCHRIFTVERKEHR


def dateien_von(haupt: Path, relativ: str) -> list[Path]:
    """Dateien eines Verweises: die Datei selbst, bzw. die eines Ordners (bis MAX_TIEFE, ohne Verstecktes) nach
    relativem Namen sortiert (die Nummer m bleibt so stabil, solange nichts dazwischen kommt)."""
    pfad = aufloesen(haupt, relativ)
    if pfad is None:
        return []
    if pfad.is_file():
        return [pfad] if zeigbar(pfad) else []
    wurzel = _wurzel(haupt, relativ)
    gefunden = []

    def ebene(ordner: Path, tiefe: int):
        try:
            inhalt = sorted(ordner.iterdir(), key=lambda p: p.name)
        except OSError:
            return
        for p in inhalt:
            if p.name.startswith(".") or len(gefunden) >= MAX_DATEIEN:
                continue
            q = p.resolve()
            if not q.is_relative_to(wurzel):
                continue
            if q.is_dir() and tiefe < MAX_TIEFE:
                ebene(q, tiefe + 1)
            elif zeigbar(q):
                gefunden.append(q)
    ebene(pfad, 1)
    return gefunden


def art(pfad: Path) -> str:
    """"mails" | "text" | "seiten" | "bild"."""
    endung = pfad.suffix.lower()
    if endung == ".json":
        return "mails"
    if endung in TEXT:
        return "text"
    return "bild" if endung in BILD else "seiten"


def titel_aus(pfad: Path) -> str:
    """Erste Überschrift einer .md, beim Schriftverkehr „Schriftverkehr“, sonst der Dateiname ohne Endung."""
    if pfad.name == SCHRIFTVERKEHR:
        return "Schriftverkehr"
    if pfad.suffix.lower() == ".md":
        try:
            with pfad.open(encoding="utf-8", errors="replace") as f:
                for _, zeile in zip(range(20), f, strict=False):
                    if zeile.startswith("# "):
                        return " ".join(zeile[2:].split())[:MAX_TITEL]
        except OSError:
            pass
    return pfad.stem


def eintraege(haupt: Path, verweise: list[dict]) -> list[dict]:
    """Zeilen für die Ordner-Seite, in der Reihenfolge der Verweise; innerhalb eines Ordner-Verweises neueste zuerst.
    Je Zeile {"nr", "titel", "unter", "zeit" (mtime), "art", "fehlt"}. Fehlt ein Verweis: eine Zeile mit fehlt=True."""
    zeilen = []
    for n, v in enumerate(verweise):
        pfad = aufloesen(haupt, v["pfad"])
        if pfad is None:
            zeilen.append({"nr": str(n), "titel": v["titel"] or Path(v["pfad"]).name, "unter": v["pfad"], "zeit": 0,
                           "art": "", "fehlt": True})
            continue
        if pfad.is_file():
            if zeigbar(pfad):
                zeilen.append({"nr": str(n), "titel": v["titel"] or titel_aus(pfad), "unter": str(Path(v["pfad"]).parent),
                               "zeit": pfad.stat().st_mtime, "art": art(pfad), "fehlt": False})
            continue
        gruppe = [{"nr": f"{n}-{m}", "titel": titel_aus(p), "unter": v["titel"] or Path(v["pfad"]).name,
                   "zeit": p.stat().st_mtime, "art": art(p), "fehlt": False}
                  for m, p in enumerate(dateien_von(haupt, v["pfad"]))]
        zeilen.extend(sorted(gruppe, key=lambda z: z["zeit"], reverse=True))
    return zeilen


def finden(haupt: Path, verweise: list[dict], nr: str) -> tuple[Path, dict] | None:
    """Datei zur Nummer ("<n>" oder "<n>-<m>") und ihr Verweis, oder None."""
    m = NR.fullmatch(nr or "")
    if m is None or int(m.group(1)) >= len(verweise):
        return None
    v = verweise[int(m.group(1))]
    pfad = aufloesen(haupt, v["pfad"])
    if pfad is None:
        return None
    if m.group(2) is None:
        return (pfad, v) if pfad.is_file() and zeigbar(pfad) else None
    if not pfad.is_dir():
        return None
    liste = dateien_von(haupt, v["pfad"])
    i = int(m.group(2))
    return (liste[i], v) if i < len(liste) else None


def mails(pfad: Path) -> dict:
    """schriftverkehr.json (uni/schriftverkehr.py) -> {"stand", "seit", "gekappt", "mails": neueste zuerst}.
    Kaputt oder falsche Form: ValueError."""
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    if not isinstance(daten, dict) or not isinstance(daten.get("mails"), list):
        raise ValueError("erwartet {\"mails\": [...]}")

    def liste(x) -> list[str]:
        return [str(e) for e in x] if isinstance(x, list) else ([str(x)] if x else [])
    zeilen = [{"betreff": str(m.get("betreff") or ""), "datum": str(m.get("datum") or ""),
               "von_mir": m.get("richtung") == "an", "von": str(m.get("von") or ""), "an": liste(m.get("an")),
               "anhaenge": liste(m.get("anhaenge")), "text": str(m.get("text") or "")}
              for m in daten["mails"] if isinstance(m, dict)]
    return {"stand": str(daten.get("stand") or ""), "seit": str(daten.get("seit") or ""),
            "gekappt": bool(daten.get("gekappt")), "mails": sorted(zeilen, key=lambda z: z["datum"], reverse=True)}
