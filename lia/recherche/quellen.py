"""quellen.toml lesen und prüfen (ohne Netz).

laden(pfad) -> (allowlist, quellen). Fehler: QuellenFehler mit Text für Jan.
Jede URL wird schon hier gegen die Allowlist geprüft (agentkit.abruf.pruefen), damit ein Tippfehler
nicht erst beim Laden auffällt.
"""

import tomllib
from pathlib import Path

import scan
from agentkit import abruf

ARTEN = ("gesetz", "primaertext")
PERSONEN = ("herausgeber", "uebersetzer")


class QuellenFehler(Exception):
    pass


def laden(pfad: Path) -> tuple[list[str], list[dict]]:
    try:
        with open(pfad, "rb") as f:
            daten = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise QuellenFehler(f"{pfad} nicht lesbar: {e}") from None
    allowlist = daten.get("abruf", {}).get("allowlist")
    if not allowlist or not all(isinstance(d, str) and d for d in allowlist):
        raise QuellenFehler(f"{pfad}: [abruf] allowlist fehlt oder ist leer")
    quellen = daten.get("quelle", [])
    ids = set()
    for q in quellen:
        pruefen(q, allowlist)
        if q["id"] in ids:
            raise QuellenFehler(f"Quelle {q['id']} doppelt")
        ids.add(q["id"])
    return list(allowlist), quellen


def pruefen(q: dict, allowlist) -> None:
    """Pflichtfelder, Art, URLs, Seiten. Sonst QuellenFehler."""
    qid = q.get("id")
    if not isinstance(qid, str) or not qid or not qid.replace("-", "").isalnum():
        raise QuellenFehler(f"Quelle ohne gültige id (nur Buchstaben, Ziffern, -): {qid!r}")
    for feld in ("art", "werk", "ausgabe"):
        if not isinstance(q.get(feld), str) or not q[feld].strip():
            raise QuellenFehler(f"Quelle {qid}: Feld {feld} fehlt")
    if q["art"] not in ARTEN:
        raise QuellenFehler(f"Quelle {qid}: art {q['art']!r} unbekannt, erlaubt {', '.join(ARTEN)}")
    if q["art"] == "primaertext" and "autor" not in q:
        raise QuellenFehler(f"Quelle {qid}: autor fehlt")
    for feld in PERSONEN:
        if feld in q and f"{feld}_entfaellt" in q:
            raise QuellenFehler(f"Quelle {qid}: {feld} und {feld}_entfaellt zugleich")
    urls = q.get("urls")
    if not isinstance(urls, list) or not urls:
        raise QuellenFehler(f"Quelle {qid}: urls fehlt oder ist leer")
    for url in urls:
        try:
            abruf.pruefen(url, allowlist)
        except abruf.AbrufFehler as e:
            raise QuellenFehler(f"Quelle {qid}: {e}") from None
    if "scan_id" in q:
        _scan_pruefen(q)
    if "seiten" in q and len(q["seiten"]) != len(urls):
        raise QuellenFehler(f"Quelle {qid}: {len(q['seiten'])} Seiten, aber {len(urls)} URLs")


def _scan_pruefen(q: dict) -> None:
    """Scan-Quelle: druckseiten = [von, bis], scan_versatz, urls = genau die drei Dateien des Scans."""
    qid = q["id"]
    seiten = q.get("druckseiten")
    if not (isinstance(seiten, list) and len(seiten) == 2 and all(isinstance(s, int) for s in seiten)
            and 1 <= seiten[0] <= seiten[1]):
        raise QuellenFehler(f"Quelle {qid}: druckseiten = [von, bis] fehlt")
    if not isinstance(q.get("scan_versatz"), int):
        raise QuellenFehler(f"Quelle {qid}: scan_versatz fehlt")
    von, bis = seiten
    for h in q.get("stelle_von_hand", []):
        s = h.get("seiten")
        if (not isinstance(s, list) or not 1 <= len(s) <= 2 or not all(isinstance(x, int) and von <= x <= bis for x in s)
                or (len(s) == 2 and s[1] != s[0] + 1)):
            raise QuellenFehler(f"Quelle {qid}: stelle_von_hand mit ungültigen seiten {s!r}")
        for feld in ("anfang", "ende", "position", "zweck"):
            if not isinstance(h.get(feld), str) or not h[feld].strip():
                raise QuellenFehler(f"Quelle {qid}: stelle_von_hand S. {s[0]}: {feld} fehlt")
    if sorted(q["urls"]) != sorted(scan.dateien(q["scan_id"]).values()):
        raise QuellenFehler(f"Quelle {qid}: urls müssen die drei Dateien des Scans sein: "
                            + ", ".join(scan.dateien(q["scan_id"]).values()))
