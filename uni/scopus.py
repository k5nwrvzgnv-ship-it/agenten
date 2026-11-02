"""Scopus-Export für die Recherche vor dem Exposé (Jan 02.11.2026: Forschungsstand mit echter Literatursuche).

Die Scopus-API geht nicht (die Uni gibt kein Institutional Token heraus). Jan sucht deshalb selbst in Scopus
(Claude in Chrome auf seinem Mac), exportiert die Treffer als CSV und schickt sie mit dem Protokoll der Suche.
Dieses Modul ist rein: CSV lesen, Doppelte zusammenführen, Kandidatenliste für Claude (scopus.md), Abstracts für
die Belegprüfung und die Beschreibung der Suche für Recherchebericht und Exposé.

Ablage in data/expose/<kette>/recherche/scopus/:
- *.csv: Export aus Scopus (Feldgruppen Citation, Bibliographical, Abstract & keywords)
- suchen.json: {"S1": {"titel": "...", "suchstring": "TITLE-ABS-KEY(...)"}} (optional)
- protokoll.txt: Protokoll aus Chrome, Zeilen "S1 | Treffer gesamt | exportiert | Dateiname | Vermerk" und
  "Scopus-Export, Datum: ..." (optional; ohne Zuordnung zählt jede Datei als eigene Suche)
"""

import csv
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

ORDNER = "scopus"
PROTOKOLL = "protokoll.txt"
SUCHEN = "suchen.json"
PFLICHT = ("EID", "Title", "Abstract")
NEU_AB = 2020  # Spalte "seit 2020" in der Übersicht

csv.field_size_limit(10 ** 8)


class ScopusFehler(Exception):
    pass


@dataclass
class Export:
    treffer: list[dict]  # ohne Doppelte, nach Zitationen sortiert, je Treffer "suchen": ["S1", ...]
    suchen: dict[str, dict] = field(default_factory=dict)  # Nr -> {titel, suchstring, gesamt, exportiert, ...}
    datum: str = ""


def _zahl(s: str) -> int | None:
    s = (s or "").strip().replace(".", "").replace(",", "")
    return int(s) if s.isdigit() else None


def autoren(s: str) -> list[str]:
    """"Xie C.; van der Berg J.-P." -> ["Xie, C.", "van der Berg, J.-P."] (Format der Recherche)."""
    aus = []
    for name in (s or "").split(";"):
        name = name.strip()
        if not name or name.startswith("["):
            continue
        teile = name.rsplit(" ", 1)
        aus.append(f"{teile[0]}, {teile[1]}" if len(teile) == 2 and teile[1].endswith(".") else name)
    return aus


def schluessel(url: str) -> str:
    """Vergleichsschlüssel einer Adresse: DOI-Adressen ohne Rücksicht auf Groß- und Kleinschreibung."""
    url = url.strip()
    m = re.match(r"^https?://(?:dx\.)?doi\.org/(.+)$", url, re.I)
    return "doi:" + m.group(1).lower() if m else url


def zeile(x: dict) -> dict:
    """Eine Zeile des Exports in der Form der Recherche."""
    doi = (x.get("DOI") or "").strip()
    abstract = (x.get("Abstract") or "").strip()
    if abstract.startswith("[No abstract"):
        abstract = ""
    jahr = _zahl(x.get("Year", ""))
    return {"eid": x["EID"].strip(), "titel": (x.get("Title") or "").strip(), "jahr": jahr,
            "autoren": autoren(x.get("Authors", "")), "quelle": (x.get("Source title") or "").strip(),
            "zitiert": _zahl(x.get("Cited by", "")) or 0, "doi": doi or None,
            "url": f"https://doi.org/{doi}" if doi else (x.get("Link") or "").strip(),
            "art": (x.get("Document Type") or "").strip(), "abstract": abstract,
            "schlagwoerter": "; ".join(s for s in ((x.get("Author Keywords") or "").strip(),
                                                    (x.get("Index Keywords") or "").strip()) if s)}


def lesen(pfad: Path) -> list[dict]:
    try:
        with open(pfad, encoding="utf-8-sig", newline="") as h:
            leser = csv.DictReader(h)
            fehlend = [s for s in PFLICHT if s not in (leser.fieldnames or [])]
            if fehlend:
                raise ScopusFehler(f"{pfad.name}: kein Scopus-Export (Spalten fehlen: {', '.join(fehlend)})")
            return [zeile(x) for x in leser if (x.get("EID") or "").strip()]
    except (OSError, UnicodeDecodeError, csv.Error) as f:
        raise ScopusFehler(f"{pfad.name}: nicht lesbar: {f}") from None


def protokoll_lesen(text: str) -> tuple[str, dict[str, dict]]:
    """(Datum, {Nr: {gesamt, exportiert, datei, vermerk}}) aus dem Protokoll von Claude in Chrome."""
    datum, suchen = "", {}
    for z in text.splitlines():
        if m := re.search(r"Datum:\s*(.+)$", z):
            datum = m.group(1).strip()
        teile = [t.strip() for t in z.strip().strip("|").split("|")]
        if len(teile) >= 4 and re.fullmatch(r"S\d+", teile[0]):
            suchen[teile[0]] = {"gesamt": _zahl(teile[1]), "exportiert": _zahl(teile[2]), "datei": teile[3],
                                "vermerk": " | ".join(teile[4:]).strip()}
    return datum, suchen


def ist_protokoll(text: str) -> bool:
    return bool(protokoll_lesen(text)[1])


def einlesen(ordner: Path) -> Export | None:
    """Alle Exporte eines Ordners (None, wenn keiner da ist). Wirft ScopusFehler bei kaputten Dateien."""
    dateien = sorted(ordner.glob("*.csv"))
    if not dateien:
        return None
    datum, protokoll = "", {}
    if (ordner / PROTOKOLL).exists():
        datum, protokoll = protokoll_lesen((ordner / PROTOKOLL).read_text(encoding="utf-8"))
    suchen = {}
    if (ordner / SUCHEN).exists():
        try:
            suchen = json.loads((ordner / SUCHEN).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as f:
            raise ScopusFehler(f"{SUCHEN} ist kein gültiges JSON: {f}") from None
    nr_zu_datei = {p["datei"]: nr for nr, p in protokoll.items()}
    treffer: dict[str, dict] = {}
    gefunden = {}
    for pfad in dateien:
        nr = nr_zu_datei.get(pfad.name, pfad.stem)
        zeilen = lesen(pfad)
        gefunden[nr] = {"datei": pfad.name, "exportiert": len(zeilen), "seit": sum((z["jahr"] or 0) >= NEU_AB
                                                                                   for z in zeilen)}
        for z in zeilen:
            t = treffer.setdefault(z["eid"], {**z, "suchen": []})
            if nr not in t["suchen"]:
                t["suchen"].append(nr)
    alle = {}
    for nr in sorted(set(suchen) | set(gefunden), key=_sortiernr):
        alle[nr] = {"titel": "", "suchstring": "", "gesamt": None, "vermerk": "", **suchen.get(nr, {}),
                    **{k: v for k, v in protokoll.get(nr, {}).items() if k in ("gesamt", "vermerk")},
                    **gefunden.get(nr, {"datei": "", "exportiert": 0, "seit": 0})}
    liste = sorted(treffer.values(), key=lambda t: (-t["zitiert"], -(t["jahr"] or 0), t["titel"]))
    return Export(treffer=liste, suchen=alle, datum=datum)


def _sortiernr(nr: str):
    m = re.fullmatch(r"S(\d+)", nr)
    return (0, int(m.group(1)), "") if m else (1, 0, nr)


def abstracts(export: Export) -> dict[str, str]:
    """schluessel(url) -> Titel, Abstract und Schlagwörter (dagegen prüft die Recherche Zitate)."""
    return {schluessel(t["url"]): "\n".join(x for x in (t["titel"], t["abstract"], t["schlagwoerter"]) if x)
            for t in export.treffer if t["url"]}


def kandidaten_md(export: Export) -> str:
    """Kandidatenliste für Claude: oben die Suchen, dann je Treffer ein Abschnitt (mit Grep durchsuchbar)."""
    z = [f"# Scopus-Export ({export.datum or 'Datum unbekannt'}): {len(export.treffer)} Arbeiten ohne Doppelte, "
         "nach Zitationen sortiert", "", "## Suchen", ""]
    for nr, s in export.suchen.items():
        z.append(f"- {nr}: {s['titel'] or s['datei']} – {s['suchstring'] or 'Suchstring unbekannt'} "
                 f"(Treffer {s['gesamt'] if s['gesamt'] is not None else 'unbekannt'}, exportiert {s['exportiert']})")
    z += ["", "## Treffer", ""]
    for i, t in enumerate(export.treffer, 1):
        z += [f"### SC{i:04d} | {t['jahr'] or 'o. J.'} | zitiert {t['zitiert']} | {', '.join(t['suchen'])}",
              f"Titel: {t['titel']}",
              f"Autoren: {'; '.join(t['autoren']) or 'o. A.'}",
              f"Quelle: {t['quelle']} ({t['art']})",
              f"DOI: {t['doi'] or 'keine'}",
              f"url: {t['url']}",
              f"Abstract: {t['abstract'] or 'keiner'}",
              f"Schlagwörter: {t['schlagwoerter'] or 'keine'}", ""]
    return "\n".join(z)


def beschreibung(export: Export) -> dict:
    """Die Suche in Kurzform für geprueft.json (das Exposé nennt Datenbank, Datum und Umfang)."""
    return {"datenbank": "Scopus", "datum": export.datum, "arbeiten_ohne_doppelte": len(export.treffer),
            "suchen": [{"nr": nr, "titel": s["titel"], "suchstring": s["suchstring"], "treffer": s["gesamt"],
                        "exportiert": s["exportiert"]} for nr, s in export.suchen.items()]}


def uebersicht_md(export: Export, verwendet: set[str] | None = None) -> list[str]:
    """Abschnitt für den Recherchebericht. verwendet: schluessel(url) der zitierfähigen Quellen."""
    z = ["", "## Systematische Literatursuche (Scopus)", "",
         f"Suche in Scopus{' am ' + export.datum if export.datum else ''}, Export durch Jan (je Suche höchstens "
         f"300 Treffer). Zusammen {len(export.treffer)} Arbeiten ohne Doppelte. "
         "Die Suchstrings sind breit, die Zahlen zählen Treffer, nicht nur passende Arbeiten.", "",
         f"| Nr | Suche | Treffer | exportiert | davon seit {NEU_AB} | Vermerk |", "|---|---|---|---|---|---|"]
    for nr, s in export.suchen.items():
        z.append(f"| {nr} | {s['titel'] or s['datei']} | {s['gesamt'] if s['gesamt'] is not None else '?'} | "
                 f"{s['exportiert']} | {s['seit']} | {s['vermerk']} |")
    strings = [(nr, s["suchstring"]) for nr, s in export.suchen.items() if s["suchstring"]]
    if strings:
        z += ["", "Suchstrings:", ""] + [f"- {nr}: `{s}`" for nr, s in strings]
    if verwendet is not None:
        genutzt = [t for t in export.treffer if schluessel(t["url"]) in verwendet]
        z += ["", f"In der Recherche als Quelle verwendet: {len(genutzt)} Arbeiten aus dem Export."]
    return z


def uebernehmen(quellen: list[Path], text: str, ziel: Path) -> list[Path]:
    """CSV-Dateien nach ziel verschieben, ein Protokoll (im Text oder als .txt unter quellen) dazulegen.
    Gibt die übernommenen CSV-Dateien zurück. Ohne CSV bleibt alles liegen."""
    csvs = [p for p in quellen if p.suffix.lower() == ".csv" and p.is_file()]
    if not csvs:
        return []
    protokolle = [p for p in quellen if p.suffix.lower() == ".txt" and p.is_file()
                  and ist_protokoll(p.read_text(encoding="utf-8", errors="replace"))]
    ziel.mkdir(parents=True, exist_ok=True)
    aus = []
    for p in csvs:
        neu = ziel / p.name
        if neu.exists() and neu.resolve() != p.resolve():
            neu = ziel / f"{p.stem}-{len(list(ziel.glob('*.csv')))}{p.suffix}"
        shutil.move(str(p), neu)
        aus.append(neu)
    for t in [text] + [p.read_text(encoding="utf-8", errors="replace") for p in protokolle]:
        if ist_protokoll(t):
            with open(ziel / PROTOKOLL, "a", encoding="utf-8") as h:
                h.write(t.rstrip() + "\n")
    for p in protokolle:
        if p.resolve() != (ziel / PROTOKOLL).resolve():
            p.unlink()
    return aus
