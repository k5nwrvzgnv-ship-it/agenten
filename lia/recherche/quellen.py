"""quellen.toml lesen und prüfen (ohne Netz).

laden(pfad) -> (allowlist, quellen). Fehler: QuellenFehler mit Text für Jan.
Jede URL wird schon hier gegen die Allowlist geprüft (agentkit.abruf.pruefen), damit ein Tippfehler
nicht erst beim Laden auffällt.
"""

import tomllib
from pathlib import Path

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
    urls = q.get("urls")
    if not isinstance(urls, list) or not urls:
        raise QuellenFehler(f"Quelle {qid}: urls fehlt oder ist leer")
    for url in urls:
        try:
            abruf.pruefen(url, allowlist)
        except abruf.AbrufFehler as e:
            raise QuellenFehler(f"Quelle {qid}: {e}") from None
    if "seiten" in q and len(q["seiten"]) != len(urls):
        raise QuellenFehler(f"Quelle {qid}: {len(q['seiten'])} Seiten, aber {len(urls)} URLs")
