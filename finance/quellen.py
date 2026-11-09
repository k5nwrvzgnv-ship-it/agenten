"""Ablage der Primärdaten: jede Abfrage unter einer Quellen-ID in data/quellen/ (nur Bordmittel, ohne Netz).

Je Quelle zwei Dateien:
- <ID>.json  Meta: id, art, url, abgerufen (ISO-Zeit), beschreibung, sha256, groesse, endung
- <ID>.roh.<endung>  der Rohinhalt genau so, wie er geladen wurde

ID: Q-<JJJJMMTT>-<art>-<6 Zeichen sha256 aus url und Inhalt>, z. B. Q-20261109-genesis-3fa2c1.
Gleiche URL mit gleichem Inhalt ergibt dieselbe ID (kein Doppel). Ändert sich der Inhalt, entsteht eine
neue ID, die alte bleibt als Beleg erhalten.

Maßgeblich ist index.toml im selben Ordner: je ID art, endung und sha256. Claude darf im Agent-Ordner schreiben,
aber keine *.toml (Schreibschutz in agentkit.claude_lauf). Eine geänderte Meta-Datei (z. B. Art "web" statt
"genesis", um den Abgleich zu umgehen) oder geänderte Rohdaten fallen damit auf.

Claude zitiert nur IDs, die hier liegen. pruefung.py gleicht Zahlen mit den Rohdaten ab (zahlen_im_rohinhalt).
"""

import hashlib
import json
import re
import tomllib
from datetime import datetime
from pathlib import Path

# Bekannte Arten von Primärdaten (Abrufer in Python) und "web" für Seiten/PDFs, die Claude per WebFetch liest
ARTEN = ("genesis", "eurostat", "comtrade", "ted", "jobsuche", "epo", "web")
_ID = re.compile(r"^Q-\d{8}-[a-z]+-[0-9a-f]{6}$")
_ENDUNG = re.compile(r"^[a-z0-9]{1,8}$")


class QuellenFehler(Exception):
    pass


def ist_id(text: str) -> bool:
    return bool(_ID.match(text or ""))


def neue_id(art: str, url: str, inhalt: bytes, zeit: datetime) -> str:
    kurz = hashlib.sha256(url.encode("utf-8") + b"\n" + inhalt).hexdigest()[:6]
    return f"Q-{zeit:%Y%m%d}-{art}-{kurz}"


def speichern(ordner: Path, art: str, url: str, inhalt: bytes, beschreibung: str, endung: str = "json",
              zeit: datetime | None = None) -> str:
    """Legt eine Quelle ab und gibt ihre ID zurück. Gibt es sie schon (gleiche ID), bleibt sie unverändert."""
    if art not in ARTEN:
        raise QuellenFehler(f"Unbekannte Art {art!r}, erlaubt: {', '.join(ARTEN)}")
    if not url.startswith("https://"):
        raise QuellenFehler(f"Quelle ohne https-URL: {url!r}")
    if not beschreibung.strip():
        raise QuellenFehler("Quelle ohne Beschreibung")
    if not _ENDUNG.match(endung):
        raise QuellenFehler(f"Ungültige Endung {endung!r}")
    zeit = zeit or datetime.now().astimezone()
    qid = neue_id(art, url, inhalt, zeit)
    ordner = Path(ordner)
    meta_pfad = ordner / f"{qid}.json"
    if qid in _index(ordner):
        return qid
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / f"{qid}.roh.{endung}").write_bytes(inhalt)
    meta = {"id": qid, "art": art, "url": url, "abgerufen": zeit.isoformat(timespec="seconds"),
            "beschreibung": beschreibung.strip(), "sha256": hashlib.sha256(inhalt).hexdigest(),
            "groesse": len(inhalt), "endung": endung}
    tmp = meta_pfad.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(meta_pfad)
    with open(ordner / INDEX, "a", encoding="utf-8") as f:  # Index zuletzt: ohne Eintrag gibt es die Quelle nicht
        f.write(f'"{qid}" = {{ art = "{art}", endung = "{endung}", sha256 = "{meta['sha256']}" }}\n')
    return qid


INDEX = "index.toml"


def _index(ordner: Path) -> dict:
    pfad = Path(ordner) / INDEX
    if not pfad.exists():
        return {}
    try:
        return tomllib.loads(pfad.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as f:
        raise QuellenFehler(f"{pfad} ist beschädigt: {f}") from f


def meta(ordner: Path, qid: str) -> dict:
    if not ist_id(qid):
        raise QuellenFehler(f"Keine Quellen-ID: {qid!r}")
    eintrag = _index(ordner).get(qid)
    pfad = Path(ordner) / f"{qid}.json"
    if eintrag is None or not pfad.exists():
        raise QuellenFehler(f"Quelle {qid} gibt es nicht")
    m = json.loads(pfad.read_text(encoding="utf-8"))
    if any(m.get(k) != v for k, v in eintrag.items()):
        raise QuellenFehler(f"Beschreibung von {qid} wurde nach dem Abruf verändert")
    return m


def rohinhalt(ordner: Path, qid: str) -> bytes:
    """Rohinhalt; prüft dabei die Prüfsumme (verändert = Fehler)."""
    m = meta(ordner, qid)
    inhalt = (Path(ordner) / f"{qid}.roh.{m['endung']}").read_bytes()
    if hashlib.sha256(inhalt).hexdigest() != m["sha256"]:
        raise QuellenFehler(f"Rohdaten von {qid} wurden nach dem Abruf verändert")
    return inhalt


def alle(ordner: Path) -> list[dict]:
    """Meta aller Quellen, nach ID sortiert (für die Quellenliste im Prompt und im Bericht)."""
    ordner = Path(ordner)
    if not ordner.exists():
        return []
    return [meta(ordner, qid) for qid in sorted(_index(ordner))]


# Zahlen in Rohdaten: 1234, -1.5, 1.234,5 (deutsch), 1,234.5 (englisch), 4.2549E6
_ZAHL = re.compile(r"-?\d[\d.,]*(?:[eE][+-]?\d+)?")


def _zahl_lesen(roh: str) -> list[float]:
    """Mögliche Werte einer Zeichenfolge; bei uneindeutigem Trennzeichen beide Lesarten."""
    roh = roh.rstrip(".,")
    kandidaten = set()
    for tausender, dezimal in ((",", "."), (".", ",")):
        t = roh.replace(tausender, "").replace(dezimal, ".")
        try:
            kandidaten.add(float(t))
        except ValueError:
            pass
    return sorted(kandidaten)


def zahlen_im_rohinhalt(inhalt: bytes) -> list[float]:
    """Alle Zahlen im Rohinhalt (JSON, CSV, Text). Für den Abgleich in pruefung.py."""
    text = inhalt.decode("utf-8", errors="replace")
    werte: list[float] = []
    for treffer in _ZAHL.finditer(text):
        werte.extend(_zahl_lesen(treffer.group()))
    return werte
