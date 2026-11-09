"""Abrufer der Primärdaten: Abfrage prüfen, Anfrage bauen, Antwort prüfen (nur Bordmittel, ohne Netz).

Claude plant die Abfragen (abfragen.json im Recherche-Ordner), Python prüft jede Angabe streng (nur Ziffern,
Codes, Datum), baut daraus URL, Körper und Header und lädt über agentkit.abruf (agent.py). So erreicht Claude
nur diese Schnittstellen und nur mit diesen Parametern. Schlüssel kommen aus finance/.env und stehen nie in
Quellen-Meta oder Cache (agentkit.abruf lässt Header weg).

Abfrage-Formate (je Eintrag ein Objekt mit "art" und "beschreibung"):
    {"art": "genesis", "tabelle": "42111-0001", "von_jahr": 2020, "bis_jahr": 2024}
    {"art": "eurostat", "datensatz": "sts_inpr_a", "filter": {"geo": "DE", "nace_r2": "C16"}, "von_jahr": 2020}
    {"art": "comtrade", "melder": 276, "partner": 0, "jahr": 2024, "hs": "847950", "richtung": "X"}
    {"art": "ted", "cpv": "42997300", "von": "2025-01-01", "land": "DEU"}           (land freiwillig)
    {"art": "jobsuche", "was": "Robotik", "wo": "Bayern"}                            (wo freiwillig)
"""

import io
import json
import re
import urllib.parse
import zipfile
from dataclasses import dataclass, field
from datetime import date

ARTEN = ("genesis", "eurostat", "comtrade", "ted", "jobsuche")
MAX_ABFRAGEN = 15

GENESIS = "https://genesis.destatis.de/genesisWS/rest/2020/data/tablefile"
EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
COMTRADE = "https://comtradeapi.un.org/data/v1/get/C/A/HS"
TED = "https://api.ted.europa.eu/v3/notices/search"
JOBSUCHE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs"
JOBSUCHE_KEY = "jobboerse-jobsuche"  # öffentlicher Schlüssel der Bundesagentur, kein Geheimnis

_TABELLE = re.compile(r"^\d{5}-\d{4}$")
_CODE = re.compile(r"^[A-Za-z0-9_]{1,40}$")
_TEXT = re.compile(r"^[\wäöüÄÖÜß .,/+-]{2,60}$")


class AbfrageFehler(Exception):
    pass


@dataclass
class Anfrage:
    art: str
    url: str
    beschreibung: str
    allowlist: list[str]
    methode: str = "GET"
    daten: bytes | None = None
    header: dict = field(default_factory=dict)  # mit Schlüsseln, nur an agentkit.abruf
    quelle_url: str = ""  # für die Ablage: bei POST mit der Abfrage als Query, ohne Schlüssel

    def __post_init__(self):
        self.quelle_url = self.quelle_url or self.url


def _jahr(x, name: str) -> int:
    if not isinstance(x, int) or isinstance(x, bool) or not 1990 <= x <= 2100:
        raise AbfrageFehler(f"{name}: Jahr als ganze Zahl (1990 bis 2100)")
    return x


def _code(x, name: str, muster=_CODE) -> str:
    x = str(x) if isinstance(x, int) and not isinstance(x, bool) else x
    if not isinstance(x, str) or not muster.match(x):
        raise AbfrageFehler(f"{name}: ungültiger Wert {x!r}")
    return x


def _schluessel(schluessel: dict, name: str) -> str:
    wert = schluessel.get(name)
    if not wert:
        raise AbfrageFehler(f"{name} fehlt in finance/.env")
    return wert


def anfrage_bauen(abfrage: dict, schluessel: dict) -> Anfrage:
    """Aus einer Abfrage von Claude eine Anfrage (oder AbfrageFehler mit Text für Claude)."""
    if not isinstance(abfrage, dict):
        raise AbfrageFehler("Abfrage muss ein Objekt sein")
    art = abfrage.get("art")
    beschreibung = abfrage.get("beschreibung")
    if art not in ARTEN:
        raise AbfrageFehler(f"art: eine von {', '.join(ARTEN)}")
    if not isinstance(beschreibung, str) or not beschreibung.strip():
        raise AbfrageFehler("beschreibung fehlt")
    beschreibung = beschreibung.strip()[:300]

    if art == "genesis":
        werte = {"name": _code(abfrage.get("tabelle"), "tabelle", _TABELLE), "area": "all", "compress": "false",
                 "format": "ffcsv", "language": "de"}
        if "von_jahr" in abfrage:
            werte["startyear"] = str(_jahr(abfrage["von_jahr"], "von_jahr"))
        if "bis_jahr" in abfrage:
            werte["endyear"] = str(_jahr(abfrage["bis_jahr"], "bis_jahr"))
        daten = urllib.parse.urlencode(werte).encode()
        header = {"username": _schluessel(schluessel, "GENESIS_TOKEN"), "password": "",
                  "Content-Type": "application/x-www-form-urlencoded"}
        return Anfrage(art, GENESIS, beschreibung, ["destatis.de"], "POST", daten, header,
                       quelle_url=f"{GENESIS}?{daten.decode()}")

    if art == "eurostat":
        datensatz = _code(abfrage.get("datensatz"), "datensatz")
        filt = abfrage.get("filter") or {}
        if not isinstance(filt, dict):
            raise AbfrageFehler("filter: Objekt {Dimension: Code}")
        werte = [(_code(k, "filter"), _code(v, f"filter.{k}")) for k, v in sorted(filt.items())]
        if "von_jahr" in abfrage:
            werte.append(("sinceTimePeriod", str(_jahr(abfrage["von_jahr"], "von_jahr"))))
        werte.append(("lang", "de"))
        return Anfrage(art, f"{EUROSTAT}{datensatz}?{urllib.parse.urlencode(werte)}", beschreibung,
                       ["ec.europa.eu"])

    if art == "comtrade":
        richtung = abfrage.get("richtung")
        if richtung not in ("X", "M"):
            raise AbfrageFehler("richtung: X (Export) oder M (Import)")
        hs = _code(abfrage.get("hs"), "hs", re.compile(r"^\d{2}(\d{2}){0,2}$"))
        werte = {"reporterCode": _code(abfrage.get("melder"), "melder", re.compile(r"^\d{1,3}$")),
                 "partnerCode": _code(abfrage.get("partner", 0), "partner", re.compile(r"^\d{1,3}$")),
                 "period": str(_jahr(abfrage.get("jahr"), "jahr")), "cmdCode": hs, "flowCode": richtung,
                 # Ohne diese drei liefert Comtrade eine Zeile je Zollverfahren und Transportart
                 "partner2Code": "0", "customsCode": "C00", "motCode": "0", "includeDesc": "true"}
        return Anfrage(art, f"{COMTRADE}?{urllib.parse.urlencode(werte)}", beschreibung, ["comtradeapi.un.org"],
                       header={"Ocp-Apim-Subscription-Key": _schluessel(schluessel, "COMTRADE_KEY")})

    if art == "ted":
        cpv = _code(abfrage.get("cpv"), "cpv", re.compile(r"^\d{8}$"))
        try:
            von = date.fromisoformat(abfrage.get("von") or "")
        except (TypeError, ValueError):
            raise AbfrageFehler("von: Datum JJJJ-MM-TT") from None
        query = f"classification-cpv={cpv} AND publication-date>={von:%Y%m%d}"
        if abfrage.get("land"):
            query += f" AND buyer-country={_code(abfrage['land'], 'land', re.compile(r'^[A-Z]{3}$'))}"
        koerper = {"query": query, "fields": ["publication-number", "publication-date", "buyer-country",
                                              "notice-title"], "limit": 10}  # Gesamtzahl in totalNoticeCount
        daten = json.dumps(koerper).encode()
        return Anfrage(art, TED, beschreibung, ["api.ted.europa.eu"], "POST", daten,
                       {"Content-Type": "application/json"},
                       quelle_url=f"{TED}?{urllib.parse.urlencode({'query': query})}")

    # jobsuche
    werte = {"was": _code(abfrage.get("was"), "was", _TEXT), "size": "25"}
    if abfrage.get("wo"):
        werte["wo"] = _code(abfrage["wo"], "wo", _TEXT)
    return Anfrage(art, f"{JOBSUCHE}?{urllib.parse.urlencode(werte)}", beschreibung, ["rest.arbeitsagentur.de"],
                   header={"X-API-Key": JOBSUCHE_KEY})


def antwort_pruefen(art: str, inhalt: bytes, content_type: str | None) -> tuple[bytes, str]:
    """(Rohinhalt zum Ablegen, Endung) oder AbfrageFehler, wenn die Antwort keine Daten enthält."""
    art_ct = (content_type or "").lower()
    if art == "genesis":
        if "zip" in art_ct or inhalt[:2] == b"PK":
            with zipfile.ZipFile(io.BytesIO(inhalt)) as z:
                namen = [n for n in z.namelist() if n.endswith(".csv")]
                if not namen:
                    raise AbfrageFehler("GENESIS: ZIP ohne CSV")
                return z.read(namen[0]), "csv"
        if "json" in art_ct:
            status = _json(inhalt, art).get("Status") or {}
            raise AbfrageFehler(f"GENESIS: {status.get('Content') or 'keine Daten'} (Code {status.get('Code')})")
        if inhalt.strip():
            return inhalt, "csv"
        raise AbfrageFehler("GENESIS: leere Antwort")
    d = _json(inhalt, art)
    if art == "eurostat" and not d.get("value"):
        raise AbfrageFehler("Eurostat: keine Werte (Datensatz oder Filter prüfen)")
    if art == "comtrade" and not d.get("data"):
        raise AbfrageFehler(f"Comtrade: keine Daten ({d.get('error') or 'Codes prüfen'})")
    if art == "ted" and "totalNoticeCount" not in d:
        raise AbfrageFehler("TED: Antwort ohne totalNoticeCount")
    if art == "jobsuche" and "maxErgebnisse" not in d:
        raise AbfrageFehler("Jobsuche: Antwort ohne maxErgebnisse")
    return inhalt, "json"


def _json(inhalt: bytes, art: str) -> dict:
    try:
        d = json.loads(inhalt)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise AbfrageFehler(f"{art}: Antwort ist kein JSON") from None
    if not isinstance(d, dict):
        raise AbfrageFehler(f"{art}: Antwort ist kein JSON-Objekt")
    return d


def abfragen_lesen(daten) -> tuple[list[dict], list[str]]:
    """Liste aus abfragen.json: (Abfragen, Fehler). Höchstens MAX_ABFRAGEN."""
    if not isinstance(daten, dict) or not isinstance(daten.get("abfragen"), list):
        return [], ['abfragen.json: {"abfragen": [...]} erwartet']
    liste = daten["abfragen"]
    fehler = [f"Nur die ersten {MAX_ABFRAGEN} Abfragen ausgeführt"] if len(liste) > MAX_ABFRAGEN else []
    return liste[:MAX_ABFRAGEN], fehler
