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
    {"art": "sec", "cik": 1045810}       Abschlüsse einer bei der SEC gemeldeten Firma (10-K, 20-F, 40-F)
    {"art": "kurs", "symbol": "NVDA"}    Monatsschlusskurse der letzten 5 Jahre (Yahoo, z. B. 6954.T, SIE.DE)
    {"art": "epo", "begriffe": "timber", "anmelder": "Weinig", "cpc": "B27B", "land": "EP",
     "von_jahr": 2020, "bis_jahr": 2024}   Patentveröffentlichungen (EPO OPS, weltweit), mindestens eins von
                                         begriffe, anmelder, cpc; Rest freiwillig

SEC und Kurs: Die Antworten sind groß (SEC bis 5 MB) bzw. verschachtelt. Abgelegt wird ein Auszug mit den
Kennzahlen (sec_auszug, kurs_auszug), damit Claude ihn lesen kann; die URL in der Quelle führt zum Original.
Yahoo ist keine offizielle Schnittstelle (Jan 09.11.2026: genehmigt), sie kann wegfallen.

EPO: Erst holt agent.py mit EPO_OPS_KEY und EPO_OPS_SECRET einen Token (epo_token_anfrage, gilt 20 Minuten,
nur in einem Wegwerf-Cache), dann sucht anfrage_bauen mit {"EPO_TOKEN": ...} in published-data/search/biblio.
Abgelegt wird ein Auszug (epo_auszug): Trefferzahl und die ersten 25 Veröffentlichungen. Keine Treffer meldet
OPS als HTTP 404; agent.py legt dann epo_leer ab (Trefferzahl 0 ist auch ein Beleg). OPS drosselt die Suche
(etwa 5 je Minute), daher höchstens MAX_EPO Abfragen je Liste.
"""

import base64
import io
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

ARTEN = ("genesis", "eurostat", "comtrade", "ted", "jobsuche", "sec", "kurs", "epo")
MAX_ABFRAGEN = 15
MAX_EPO = 4

GENESIS = "https://genesis.destatis.de/genesisWS/rest/2020/data/tablefile"
EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
COMTRADE = "https://comtradeapi.un.org/data/v1/get/C/A/HS"
TED = "https://api.ted.europa.eu/v3/notices/search"
JOBSUCHE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs"
JOBSUCHE_KEY = "jobboerse-jobsuche"  # öffentlicher Schlüssel der Bundesagentur, kein Geheimnis
SEC = "https://data.sec.gov/api/xbrl/companyfacts/CIK{:010d}.json"
# Die SEC verlangt eine Kontaktangabe im User-Agent; Jan hat noch keine genannt (STATUS.md, offene Punkte)
SEC_AGENT = "agenten-finance (privat, nicht kommerziell)"
KURS = "https://query1.finance.yahoo.com/v8/finance/chart/{}?range=5y&interval=1mo"
_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,14}$")
EPO_TOKEN_URL = "https://ops.epo.org/3.2/auth/accesstoken"
EPO_SUCHE = "https://ops.epo.org/3.2/rest-services/published-data/search/biblio"
EPO_TREFFER = 25
EPO_GUELTIG = 15 * 60  # Sekunden; OPS sagt 20 Minuten, mit Abstand
_EPO_WORTE = re.compile(r"^[\wäöüÄÖÜß .&-]{2,60}$")  # ohne Anführungszeichen: kein Ausbruch aus der CQL
_CPC = re.compile(r"^[A-H]\d{2}([A-Z](\d{1,4}(/\d{1,6})?)?)?$")
_LAND = re.compile(r"^[A-Z]{2}$")
_NS = {"ex": "http://www.epo.org/exchange", "ops": "http://ops.epo.org"}

# Kennzahl -> XBRL-Konzepte (us-gaap, sonst ifrs-full), erstes vorhandenes je Periode zählt
SEC_KONZEPTE = {
    "umsatz": ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "Revenue"),
    "operatives_ergebnis": ("OperatingIncomeLoss", "ProfitLossFromOperatingActivities"),
    "nettoergebnis": ("NetIncomeLoss", "ProfitLoss", "ProfitLossAttributableToOwnersOfParent"),
    "operativer_cashflow": ("NetCashProvidedByUsedInOperatingActivities", "CashFlowsFromUsedInOperatingActivities"),
    "investitionen_sachanlagen": ("PaymentsToAcquirePropertyPlantAndEquipment",
                                  "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"),
    "forschung_entwicklung": ("ResearchAndDevelopmentExpense", "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"),
    "eigenkapital": ("StockholdersEquity", "EquityAttributableToOwnersOfParent", "Equity"),
    "liquide_mittel": ("CashAndCashEquivalentsAtCarryingValue", "CashAndCashEquivalents"),
    "langfristige_schulden": ("LongTermDebtNoncurrent", "LongTermDebt", "NoncurrentFinancialLiabilities"),
    "verwaessertes_ergebnis_je_aktie": ("EarningsPerShareDiluted", "DilutedEarningsLossPerShare"),
    "verwaesserte_aktien": ("WeightedAverageNumberOfDilutedSharesOutstanding",
                            "WeightedAverageNumberOfSharesOutstandingDiluted"),
}
JAHRESFORMEN = ("10-K", "20-F", "40-F", "10-K/A", "20-F/A", "40-F/A")
SEC_JAHRE = 6

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

    if art == "sec":
        cik = _code(abfrage.get("cik"), "cik", re.compile(r"^\d{1,10}$"))
        return Anfrage(art, SEC.format(int(cik)), beschreibung, ["data.sec.gov"], header={"User-Agent": SEC_AGENT})

    if art == "kurs":
        symbol = _code(abfrage.get("symbol"), "symbol", _SYMBOL)
        return Anfrage(art, KURS.format(symbol), beschreibung, ["query1.finance.yahoo.com"])

    if art == "epo":
        cql = epo_cql(abfrage)
        url = f"{EPO_SUCHE}?{urllib.parse.urlencode({'q': cql, 'Range': f'1-{EPO_TREFFER}'})}"
        return Anfrage(art, url, beschreibung, ["ops.epo.org"],
                       header={"Authorization": f"Bearer {_schluessel(schluessel, 'EPO_TOKEN')}",
                               "Accept": "application/xml"})

    # jobsuche
    werte = {"was": _code(abfrage.get("was"), "was", _TEXT), "size": "25"}
    if abfrage.get("wo"):
        werte["wo"] = _code(abfrage["wo"], "wo", _TEXT)
    return Anfrage(art, f"{JOBSUCHE}?{urllib.parse.urlencode(werte)}", beschreibung, ["rest.arbeitsagentur.de"],
                   header={"X-API-Key": JOBSUCHE_KEY})


def epo_cql(abfrage: dict) -> str:
    """CQL-Suche aus geprüften Teilen (oder AbfrageFehler)."""
    teile = []
    if abfrage.get("begriffe"):
        teile.append(f'ta="{_code(abfrage["begriffe"], "begriffe", _EPO_WORTE).strip()}"')
    if abfrage.get("anmelder"):
        teile.append(f'pa="{_code(abfrage["anmelder"], "anmelder", _EPO_WORTE).strip()}"')
    if abfrage.get("cpc"):
        teile.append(f'cpc="{_code(abfrage["cpc"], "cpc", _CPC)}"')
    if not teile:
        raise AbfrageFehler("epo: mindestens eins von begriffe, anmelder, cpc")
    if abfrage.get("land"):
        teile.append(f"pn={_code(abfrage['land'], 'land', _LAND)}")
    if "von_jahr" in abfrage or "bis_jahr" in abfrage:
        von = _jahr(abfrage.get("von_jahr", 1990), "von_jahr")
        bis = _jahr(abfrage.get("bis_jahr", 2100), "bis_jahr")
        if von > bis:
            raise AbfrageFehler("von_jahr liegt nach bis_jahr")
        teile.append(f'pd within "{von} {bis}"')
    return " and ".join(teile)


def epo_token_anfrage(schluessel: dict) -> Anfrage:
    """Token-Abruf bei OPS (POST mit Basic-Auth aus Key und Secret)."""
    paar = f"{_schluessel(schluessel, 'EPO_OPS_KEY')}:{_schluessel(schluessel, 'EPO_OPS_SECRET')}"
    return Anfrage("epo", EPO_TOKEN_URL, "EPO-Token", ["ops.epo.org"], "POST", b"grant_type=client_credentials",
                   {"Authorization": "Basic " + base64.b64encode(paar.encode()).decode(),
                    "Content-Type": "application/x-www-form-urlencoded"})


def epo_token_lesen(inhalt: bytes) -> str:
    d = _json(inhalt, "EPO-Token")
    token = d.get("access_token")
    if not isinstance(token, str) or not token or d.get("status") not in (None, "approved"):
        raise AbfrageFehler(f"EPO: kein Token erhalten (Status {d.get('status')!r}), Key und Secret prüfen")
    return token


def _text(e, pfad: str) -> str | None:
    x = e.find(pfad, _NS)
    return x.text.strip() if x is not None and x.text and x.text.strip() else None


def epo_auszug(inhalt: bytes) -> dict:
    """Trefferzahl und Veröffentlichungen aus OPS biblio-search (oder AbfrageFehler)."""
    try:
        wurzel = ET.fromstring(inhalt)
    except ET.ParseError:
        raise AbfrageFehler("EPO: Antwort ist kein XML") from None
    suche = wurzel.find("ops:biblio-search", _NS)
    if suche is None or not (suche.get("total-result-count") or "").isdigit():
        raise AbfrageFehler("EPO: Antwort ohne Trefferzahl")
    liste = []
    for doc in suche.iterfind(".//ex:exchange-document", _NS):
        bib = doc.find("ex:bibliographic-data", _NS)
        if bib is None:
            continue
        titel = {t.get("lang"): (t.text or "").strip() for t in bib.iterfind("ex:invention-title", _NS)}
        anmelder = [n.text.strip() for n in bib.iterfind(
            "ex:parties/ex:applicants/ex:applicant[@data-format='epodoc']/ex:applicant-name/ex:name", _NS)
            if n.text and n.text.strip()]
        cpc = []
        for k in bib.iterfind("ex:patent-classifications/ex:patent-classification", _NS):
            teile = [_text(k, f"ex:{t}") or "" for t in ("section", "class", "subclass", "main-group", "subgroup")]
            code = f"{''.join(teile[:3])}{teile[3]}/{teile[4]}"
            if code not in cpc:
                cpc.append(code)
        datum = _text(bib, "ex:publication-reference/ex:document-id[@document-id-type='docdb']/ex:date") or ""
        liste.append({
            "nummer": f"{doc.get('country', '')}{doc.get('doc-number', '')}{doc.get('kind', '')}",
            "veroeffentlicht": f"{datum[:4]}-{datum[4:6]}-{datum[6:8]}" if len(datum) == 8 else datum,
            "titel": titel.get("en") or next(iter(titel.values()), None),
            "anmelder": anmelder[:5], "cpc": cpc[:5], "familie": doc.get("family-id")})
    return {"suche": _text(suche, "ops:query"), "treffer_gesamt": int(suche.get("total-result-count")),
            "hinweis": f"EPO OPS (Espacenet-Daten, weltweit): Trefferzahl aller Veröffentlichungen (ein Patent kann "
                       f"in mehreren Ländern veröffentlicht sein, Familie gleich), dazu die ersten {EPO_TREFFER}",
            "veroeffentlichungen": liste}


def epo_leer(anfrage: Anfrage) -> bytes:
    """Auszug für eine Suche ohne Treffer (OPS antwortet mit HTTP 404)."""
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(anfrage.url).query).get("q", [""])[0]
    return _als_json({"suche": q, "treffer_gesamt": 0, "hinweis": "EPO OPS: keine Treffer (HTTP 404 No results found)",
                      "veroeffentlichungen": []})


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
    if art == "epo":
        return _als_json(epo_auszug(inhalt)), "json"
    d = _json(inhalt, art)
    if art == "eurostat" and not d.get("value"):
        raise AbfrageFehler("Eurostat: keine Werte (Datensatz oder Filter prüfen)")
    if art == "comtrade" and not d.get("data"):
        raise AbfrageFehler(f"Comtrade: keine Daten ({d.get('error') or 'Codes prüfen'})")
    if art == "ted" and "totalNoticeCount" not in d:
        raise AbfrageFehler("TED: Antwort ohne totalNoticeCount")
    if art == "jobsuche" and "maxErgebnisse" not in d:
        raise AbfrageFehler("Jobsuche: Antwort ohne maxErgebnisse")
    if art == "sec":
        return _als_json(sec_auszug(d)), "json"
    if art == "kurs":
        return _als_json(kurs_auszug(d)), "json"
    return inhalt, "json"


def _als_json(d: dict) -> bytes:
    return json.dumps(d, ensure_ascii=False, indent=1).encode("utf-8")


def _tage(von: str, bis: str) -> int:
    return (date.fromisoformat(bis) - date.fromisoformat(von)).days


def _jahreswerte(eintraege: list) -> dict[str, dict]:
    """Jahreswerte aus Jahresberichten: je Periodenende der zuletzt eingereichte Wert.

    Flussgrößen (mit start) nur bei 330 bis 400 Tagen Dauer, Bestandsgrößen (ohne start) am Periodenende.
    """
    erg: dict[str, dict] = {}
    for e in eintraege:
        if not isinstance(e, dict) or e.get("form") not in JAHRESFORMEN or e.get("fp") != "FY":
            continue
        ende, wert = e.get("end"), e.get("val")
        if not isinstance(ende, str) or not isinstance(wert, (int, float)) or isinstance(wert, bool):
            continue
        try:
            if e.get("start") and not 330 <= _tage(e["start"], ende) <= 400:
                continue
        except ValueError:
            continue
        alt = erg.get(ende)
        if alt is None or str(e.get("filed", "")) > alt["eingereicht"]:
            erg[ende] = {"von": e.get("start"), "bis": ende, "wert": wert, "form": e["form"],
                         "eingereicht": str(e.get("filed", ""))}
    return erg


def sec_auszug(d: dict) -> dict:
    """Kennzahlen der letzten SEC_JAHRE Geschäftsjahre aus companyfacts (oder AbfrageFehler)."""
    facts = d.get("facts")
    if not isinstance(facts, dict):
        raise AbfrageFehler("SEC: Antwort ohne facts (CIK prüfen)")
    werte = {}
    for name, konzepte in SEC_KONZEPTE.items():
        perioden: dict[str, dict] = {}
        einheit = None
        for konzept in konzepte:
            fakt = (facts.get("us-gaap") or {}).get(konzept) or (facts.get("ifrs-full") or {}).get(konzept)
            if not isinstance(fakt, dict) or not isinstance(fakt.get("units"), dict) or not fakt["units"]:
                continue
            e_name, eintraege = next(iter(fakt["units"].items()))
            if einheit not in (None, e_name):
                continue  # andere Währung als das erste Konzept: nicht mischen
            for ende, p in _jahreswerte(eintraege).items():
                if ende not in perioden:
                    perioden[ende] = dict(p, konzept=konzept)
                    einheit = e_name
        if perioden:
            werte[name] = {"einheit": einheit,
                           "jahre": [perioden[k] for k in sorted(perioden, reverse=True)[:SEC_JAHRE]]}
    aktien = ((facts.get("dei") or {}).get("EntityCommonStockSharesOutstanding") or {}).get("units", {}).get("shares")
    if isinstance(aktien, list) and aktien:
        letzte = max((a for a in aktien if isinstance(a, dict) and "end" in a), key=lambda a: a["end"], default=None)
        if letzte:
            werte["ausstehende_aktien"] = {"einheit": "Stück", "stand": letzte["end"], "wert": letzte.get("val")}
    if not werte:
        raise AbfrageFehler("SEC: keine Jahreskennzahlen gefunden (Firma meldet nicht per XBRL?)")
    return {"firma": d.get("entityName"), "cik": d.get("cik"),
            "hinweis": "Auszug aus SEC companyfacts: Jahresberichte, je Periodenende der zuletzt eingereichte Wert",
            "kennzahlen": werte}


def kurs_auszug(d: dict) -> dict:
    """Aktueller Kurs und Monatsschlusskurse aus Yahoo chart (oder AbfrageFehler)."""
    try:
        r = d["chart"]["result"][0]
        meta, zeiten = r["meta"], r.get("timestamp") or []
        schluss = r["indicators"]["quote"][0].get("close") or []
    except (KeyError, IndexError, TypeError):
        fehler = (d.get("chart") or {}).get("error") if isinstance(d.get("chart"), dict) else None
        raise AbfrageFehler(f"Kurs: keine Daten ({(fehler or {}).get('description') or 'Symbol prüfen'})") from None
    kurs = meta.get("regularMarketPrice")
    if not isinstance(kurs, (int, float)):
        raise AbfrageFehler("Kurs: kein aktueller Kurs (Symbol prüfen)")
    reihe = [{"monat": datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m"), "schluss": round(c, 4)}
             for t, c in zip(zeiten, schluss, strict=False) if isinstance(t, int) and isinstance(c, (int, float))]
    return {"symbol": meta.get("symbol"), "waehrung": meta.get("currency"), "boerse": meta.get("fullExchangeName"),
            "kurs_aktuell": kurs,
            "stand": datetime.fromtimestamp(meta.get("regularMarketTime") or 0, timezone.utc).strftime("%Y-%m-%d"),
            "hoch_52_wochen": meta.get("fiftyTwoWeekHigh"), "tief_52_wochen": meta.get("fiftyTwoWeekLow"),
            "hinweis": "Yahoo Finance (inoffizielle Schnittstelle), Monatsschlusskurse ohne Dividenden",
            "monatsschluss": reihe}


def _json(inhalt: bytes, art: str) -> dict:
    try:
        d = json.loads(inhalt)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise AbfrageFehler(f"{art}: Antwort ist kein JSON") from None
    if not isinstance(d, dict):
        raise AbfrageFehler(f"{art}: Antwort ist kein JSON-Objekt")
    return d


def abfragen_lesen(daten, maximal: int = MAX_ABFRAGEN) -> tuple[list[dict], list[str]]:
    """Liste aus abfragen.json: (Abfragen, Fehler). Höchstens maximal."""
    if not isinstance(daten, dict) or not isinstance(daten.get("abfragen"), list):
        return [], ['abfragen.json: {"abfragen": [...]} erwartet']
    liste = daten["abfragen"]
    fehler = [f"Nur die ersten {maximal} Abfragen ausgeführt"] if len(liste) > maximal else []
    liste, epo = liste[:maximal], 0
    behalten = []
    for a in liste:
        if isinstance(a, dict) and a.get("art") == "epo":
            epo += 1
            if epo > MAX_EPO:
                continue
        behalten.append(a)
    if epo > MAX_EPO:
        fehler.append(f"Nur die ersten {MAX_EPO} EPO-Abfragen ausgeführt (OPS drosselt die Suche)")
    return behalten, fehler
