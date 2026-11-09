"""Die fünf Schritte einer Recherche: Aufgabe, Prompt, Pflichtfelder, Webquellen (nur Bordmittel, ohne Netz).

Zwei Varianten (variante_aus_text): MARKT (Wirtschaftlichkeit, Geschäftshypothesen; Standard) und AKTIEN
(Anlagemöglichkeiten: Firmen und ETFs, Kennzahlen aus SEC und Kursen, Anlagethesen; Auftrag "aktien: <Thema>").

Je Schritt schreibt Claude eine JSON-Datei (data/recherchen/<auftrag>/schritt<n>.json). Python prüft sie
(pruefung.py und hier die Pflichtfelder). Bei Fehlern bekommt Claude die Liste und bessert dieselbe Datei nach.

Webquellen (Geschäftsberichte, Pressemitteilungen): Claude schreibt statt einer Quellen-ID
    "quelle": {"url": "https://...", "zitat": "wörtliche Stelle mit der Zahl", "beschreibung": "..."}
Python lädt die Seite (agent.py), prüft mit webquelle_pruefen, dass das Zitat wörtlich dort steht und die Zahl im
Zitat vorkommt, legt die Seite als Quelle "web" ab und ersetzt die Angabe durch die ID.
"""

import json
import re
from dataclasses import dataclass
from datetime import date

import pruefung
import quellen


@dataclass(frozen=True)
class Schritt:
    nr: int
    name: str
    aufgabe: str
    beispiel: str  # Gerüst der Datei

    @property
    def datei(self) -> str:
        return f"schritt{self.nr}.json"


ZAHL_REGELN = """\
Regeln für Zahlen (Python prüft jede einzelne, sonst wird die Datei abgelehnt):
- Jede Zahl steht in einem Zahl-Objekt mit "wert" (Zahl, Punkt als Dezimaltrennzeichen) und "einheit" und
  GENAU EINEM Beleg:
  {"wert": 12.5, "einheit": "Mio EUR", "quelle": "Q-20261109-genesis-3fa2c1"}   (Quellen-ID aus der Liste unten;
      der Wert muss in den Rohdaten stehen, auch als Tsd/Mio/Mrd)
  {"wert": 4.1, "einheit": "% Umsatzrendite", "quelle": {"url": "https://...", "zitat": "wörtliche Stelle, in der
      die Zahl steht", "beschreibung": "Geschäftsbericht X 2025, S. 12"}}   (Webseite oder PDF, die du gelesen
      hast; das Zitat muss Zeichen für Zeichen auf der Seite stehen und die Zahl enthalten)
  {"wert": 0.3, "einheit": "Anteil", "annahme": "Begründung, warum dieser Wert plausibel ist"}
  {"wert": 0.08, "einheit": "Anteil", "berechnet": {"art": "quotient", "aus": [<Zahl-Objekt>, <Zahl-Objekt>]}}
      (art: produkt, quotient, summe, differenz; Python rechnet nach, höchstens 1 % Abweichung)
- Keine nackten Zahlen, auch nicht in Listen. Ausnahme: die Felder "jahr", "von_jahr", "bis_jahr", "nr", "cik" (ganze Zahl).
- Beträge, Anteile und Mengen nicht im Fließtext, sondern als Zahl-Objekt. Jahreszahlen und Daten dürfen im
  Text stehen, und zwar in Ziffern; schreibe Zahlen nie als Wort aus. Was du nicht belegen kannst, ist eine
  Annahme, keine Quelle.
- Erfinde keine Quellen-IDs und keine Zitate.
- Webquellen: die Originalseite des Herausgebers (Investor Relations, Destatis, Verband, Behörde) statt
  Nachrichtenportalen oder Sammelseiten, wenn sie erreichbar ist. PDFs (Geschäftsberichte) sind erlaubt, Python
  liest ihren Text selbst. Weil WebFetch PDFs nur in Auszügen zeigt, dort ein kurzes Zitat wählen: die Zahl mit
  den zwei, drei Wörtern unmittelbar davor, genau wie im Dokument."""

ARBEITSWEISE = """Arbeitsweise: Du hast höchstens 30 Arbeitsschritte (jeder Werkzeugaufruf zählt), danach wird der Lauf ohne
Ergebnis abgebrochen. Schreibe die Datei vollständig, spätestens wenn etwa die Hälfte verbraucht ist, und
verbessere sie danach mit Edit. Eine gültige Datei mit offenen Punkten ist besser als keine."""

SCHRITTE = (
    Schritt(1, "Wertschöpfungskette", """\
Zerlege die Wertschöpfungskette des Themas in Stufen (vom Rohstoff bzw. der Technologie bis zum Endkunden).
Zeige je Stufe, wo heute Gewinn anfällt: typische Firmen mit Umsatz, Marge (EBIT/Umsatz) und Kapitalrendite
(ROCE oder ROIC) aus echten Abschlüssen (Geschäftsberichte als Webquelle). Wo es keine Abschlüsse gibt,
benenne die Lücke unter "offene_punkte" statt Zahlen zu schätzen.""",
             '{"thema": "...", "stufen": [{"name": "...", "beschreibung": "...", "firmen": [{"name": "...", '
             '"jahr": 2025, "umsatz": <Zahl>, "marge": <Zahl>, "kapitalrendite": <Zahl>}], "einschaetzung": "..."}], '
             '"offene_punkte": ["..."]}'),
    Schritt(2, "Lücken zwischen Angebot und Nachfrage", """\
Belege aus Primärdaten, wo Angebot und Nachfrage auseinanderliegen: Produktion, Kostenstruktur und
Erzeugerpreise (Destatis), Produktion und Handel (Eurostat Prodcom/Comext, UN Comtrade), Holzmarkt (Thünen),
Roboterdichte (IFR, nur frei zugängliche Pressemitteilungen), Ausschreibungen (TED), Stellenanzeigen
(Jobsuche der Bundesagentur), Patente. Nutze zuerst die Quellen aus der Liste unten, dann Webquellen.
Jede Lücke braucht mindestens zwei Belege aus verschiedenen Quellen.""",
             '{"luecken": [{"titel": "...", "beschreibung": "...", "angebot": "...", "nachfrage": "...", '
             '"belege": [{"aussage": "...", "zahl": <Zahl>}]}]}'),
    Schritt(3, "Ursachen und Marktgröße", """\
Begründe je Lücke aus Schritt 2, warum sie besteht und ob sie bleibt: Engpass (Fachkräfte, Kapital,
Technik, Regulierung), Five Forces, Zyklus. Rechne die Marktgröße von unten: Zahl der Kunden mal Anteil mit
Bedarf mal Preis je Kunde und Jahr, als Zahl-Objekt mit "berechnet": {"art": "produkt", ...}. Die Zahl der
Kunden kommt aus einer Quelle; Anteil und Preis möglichst auch (Preislisten, Förderprogramme, Umfragen,
Stellenanzeigen). Was Annahme bleibt, benennst du in "begruendung" als größte Unsicherheit.""",
             '{"luecken": [{"titel": "...", "ursache": "...", "bleibt": "ja|nein|unklar", "begruendung": "...", '
             '"five_forces": {"rivalitaet": "...", "neue_anbieter": "...", "ersatz": "...", "kunden": "...", '
             '"lieferanten": "..."}, "zyklus": "...", "marktgroesse": <Zahl mit berechnet produkt>}]}'),
    Schritt(4, "Hypothesen", """\
Leite höchstens drei Geschäftshypothesen aus den Schritten 1 bis 3 ab. Je Hypothese: These, Begründung mit
Zahlen, Annahmen samt Quelle, drei Szenarien (pessimistisch, basis, optimistisch, jeweils mit Umsatz und
Ergebnis als Zahl-Objekt), Sicherheitsgrad (niedrig, mittel, hoch) und VORHER festgelegte Abbruchkriterien
mit Prüfdatum (JJJJ-MM-TT, in der Zukunft). Lieber eine gut belegte Hypothese als drei schwache.""",
             '{"hypothesen": [{"titel": "...", "these": "...", "begruendung": "...", "sicherheit": "mittel", '
             '"szenarien": {"pessimistisch": {"umsatz": <Zahl>, "ergebnis": <Zahl>, "text": "..."}, "basis": {...}, '
             '"optimistisch": {...}}, "abbruchkriterien": [{"text": "...", "pruefen_bis": "2027-06-30"}]}]}'),
    Schritt(5, "Externe Prüfung", """\
Prüfe jede Hypothese aus Schritt 4 von außen: Vergleichsfirmen (wer macht das schon, mit welchem Ergebnis),
Rückrechnung an einem bekannten Fall (stimmt das Modell für eine Firma, deren Zahlen bekannt sind?),
datierte Prognosen, die später automatisch gegen die Statistik geprüft werden (Indikator so genau benennen,
dass Python ihn abrufen kann, z. B. GENESIS-Tabelle und Merkmal), und Entwürfe für Kundengespräche und
Angebotsanfragen. Die Entwürfe werden NICHT verschickt; Jan gibt sie einzeln frei.
Umfang je Hypothese: höchstens zwei Vergleichsfirmen, eine Rückrechnung, ein bis zwei Prognosen, höchstens
zwei Entwürfe. Nutze zuerst die Quellen aus den Schritten 1 bis 4 und die abgelegten Primärdaten; höchstens
fünf neue Webseiten insgesamt.""",
             '{"pruefungen": [{"hypothese": "<titel aus Schritt 4>", "vergleichsfirmen": [{"name": "...", '
             '"ergebnis": "...", "zahl": <Zahl>}], "rueckrechnung": {"fall": "...", "erwartet": <Zahl>, '
             '"tatsaechlich": <Zahl>, "fazit": "..."}, "prognosen": [{"aussage": "...", "indikator": "...", '
             '"erwartet": <Zahl>, "pruefen_ab": "2027-12-31"}], "entwuerfe": [{"art": "kundengespraech|angebotsanfrage", '
             '"an": "Firma oder Rolle", "betreff": "...", "text": "..."}]}]}'),
)


def schritt(nr: int, v: "Variante | None" = None) -> Schritt:
    return (v or MARKT).schritte[nr - 1]


def quellenliste(metas: list[dict], ordner_rel: str) -> str:
    if not metas:
        return "(noch keine abgelegten Primärdaten; nutze Webquellen und Annahmen)"
    return "\n".join(f"- {m['id']} ({m['art']}, abgerufen {m['abgerufen'][:10]}): {m['beschreibung']}; "
                     f"Rohdaten: {ordner_rel}/{m['id']}.roh.{m['endung']}" for m in metas)


def prompt(s: Schritt, thema: str, ordner_rel: str, quellen_rel: str, metas: list[dict],
           fehler: list[str] | None = None, v: "Variante | None" = None) -> str:
    """Prompt für einen Schritt. Mit fehler: Nachbesserung derselben Datei."""
    v = v or MARKT
    vorige = [f"{ordner_rel}/{schritt(n, v).datei}" for n in range(1, s.nr)]
    teile = [
        f"{v.kopf}, Thema: {thema}",
        f"Schritt {s.nr} von 5: {s.name}",
    ]
    if fehler:
        teile.append(f"Deine Datei {ordner_rel}/{s.datei} wurde abgelehnt. Lies sie, korrigiere ALLE "
                     "folgenden Stellen und schreibe sie vollständig neu (Zählung ab 0):\n"
                     + "\n".join(f"- {f}" for f in fehler[:60]))
    teile += [
        "Aufgabe:\n" + s.aufgabe,
        ("Ergebnisse der vorigen Schritte (geprüft, lesen): " + ", ".join(vorige)) if vorige else "",
        (f"Übersicht der geladenen Abschlüsse und Kurse (zuerst lesen, Werte mit Quellen-ID): "
         f"{ordner_rel}/{UEBERSICHT}") if v.uebersicht and s.nr >= 2 else "",
        f"Schreibe das Ergebnis als JSON nach {ordner_rel}/{s.datei}, sonst keine Dateien. Gerüst:\n{s.beispiel}",
        ZAHL_REGELN,
        v.zusatz,
        ARBEITSWEISE,
        "Abgelegte Primärdaten (Quellen-IDs):\n" + quellenliste(metas, quellen_rel),
        "Antworte am Ende mit einem Satz, was in der Datei steht.",
    ]
    return "\n\n".join(t for t in teile if t)


ABFRAGEN_AUFGABE = """\
Plane Abfragen von Primärdaten, die Python für dich ausführt und unter einer Quellen-ID ablegt. Die Daten
nutzt du in Schritt 2 (Lücken zwischen Angebot und Nachfrage) und später als Beleg. Lies dafür die
Wertschöpfungskette aus Schritt 1. Plane 6 bis 12 Abfragen, die Produktion, Preise, Handel, Ausschreibungen
und Stellen für die Stufen des Themas abdecken. Codes (GENESIS-Tabellen, Eurostat-Datensätze, HS- und
CPV-Codes) suchst du per WebSearch/WebFetch heraus; erfinde keine.

Formate (je Eintrag "art" und "beschreibung", sonst nur diese Felder):
{"art": "genesis", "tabelle": "42111-0001", "von_jahr": 2020, "bis_jahr": 2025, "beschreibung": "..."}
    Destatis GENESIS-Online, Tabellencode NNNNN-NNNN
{"art": "eurostat", "datensatz": "sts_inpr_a", "filter": {"geo": "DE", "nace_r2": "C16"}, "von_jahr": 2020,
 "beschreibung": "..."}   Eurostat-Datensatz mit Filtern je Dimension (nur Codes)
{"art": "comtrade", "melder": 276, "partner": 0, "jahr": 2024, "hs": "847950", "richtung": "X",
 "beschreibung": "..."}   UN Comtrade; melder/partner M49-Code (276 Deutschland, 0 Welt), HS mit 2, 4 oder 6
    Ziffern, richtung X Export, M Import
{"art": "ted", "cpv": "42997300", "von": "2025-01-01", "land": "DEU", "beschreibung": "..."}
    EU-Ausschreibungen (TED) je CPV-Code (8 Ziffern), land freiwillig (ISO-3)
{"art": "jobsuche", "was": "Robotik Holz", "wo": "Bayern", "beschreibung": "..."}
    Stellenanzeigen der Bundesagentur (Anzahl in maxErgebnisse), wo freiwillig
"""


def abfragen_prompt(thema: str, ordner_rel: str, fehler: list[str] | None = None) -> str:
    """Prompt für die Phase Primärdaten (zwischen Schritt 1 und 2). Claude schreibt abfragen.json."""
    teile = [f"Recherche zur Wirtschaftlichkeit, Thema: {thema}", "Vorbereitung für Schritt 2: Primärdaten"]
    if fehler:
        teile.append("Diese Abfragen sind fehlgeschlagen. Schreibe abfragen.json neu, nur mit korrigierten oder "
                     "ersetzenden Abfragen (die erfolgreichen liegen schon ab):\n"
                     + "\n".join(f"- {f}" for f in fehler[:30]))
    teile += [
        ABFRAGEN_AUFGABE,
        f"Ergebnis von Schritt 1 (lesen): {ordner_rel}/{schritt(1).datei}",
        f'Schreibe {ordner_rel}/abfragen.json als {{"abfragen": [...]}}, sonst keine Dateien.',
        ARBEITSWEISE,
        "Antworte am Ende mit einem Satz, was in der Datei steht.",
    ]
    return "\n\n".join(teile)


def _ist_text(x) -> bool:
    return isinstance(x, str) and bool(x.strip())


def _liste(daten: dict, feld: str, fehler: list[str]) -> list:
    wert = daten.get(feld)
    if not isinstance(wert, list) or not wert:
        fehler.append(f"{feld}: Liste mit mindestens einem Eintrag fehlt")
        return []
    return wert


def _ist_zahl_objekt(x) -> bool:
    return isinstance(x, dict) and "wert" in x


def pflichtfelder(nr: int, daten: dict, heute: date, v: "Variante | None" = None) -> list[str]:
    """Aufbau je Schritt (die Zahlen selbst prüft pruefung.py)."""
    if v is not None and v.name == "aktien":
        return pflichtfelder_aktien(nr, daten, heute)
    f: list[str] = []
    if nr == 1:
        if not _ist_text(daten.get("thema")):
            f.append("thema: fehlt")
        for i, st in enumerate(_liste(daten, "stufen", f)):
            if not isinstance(st, dict) or not _ist_text(st.get("name")):
                f.append(f"stufen[{i}].name: fehlt")
    elif nr == 2:
        for i, lu in enumerate(_liste(daten, "luecken", f)):
            belege = lu.get("belege") if isinstance(lu, dict) else None
            if not isinstance(belege, list) or len(belege) < 2:
                f.append(f"luecken[{i}].belege: mindestens zwei Belege")
    elif nr == 3:
        for i, lu in enumerate(_liste(daten, "luecken", f)):
            if not isinstance(lu, dict):
                f.append(f"luecken[{i}]: muss ein Objekt sein")
                continue
            if lu.get("bleibt") not in ("ja", "nein", "unklar"):
                f.append(f"luecken[{i}].bleibt: ja, nein oder unklar")
            m = lu.get("marktgroesse")
            if not _ist_zahl_objekt(m) or not isinstance(m.get("berechnet"), dict) \
                    or m["berechnet"].get("art") != "produkt":
                f.append(f"luecken[{i}].marktgroesse: von unten rechnen (berechnet, art produkt)")
    elif nr == 4:
        if "hypothesen" not in daten:
            f.append("hypothesen: fehlt")
    elif nr == 5:
        for i, p in enumerate(_liste(daten, "pruefungen", f)):
            if not isinstance(p, dict):
                f.append(f"pruefungen[{i}]: muss ein Objekt sein")
                continue
            for j, pr in enumerate(p.get("prognosen") or []):
                s = f"pruefungen[{i}].prognosen[{j}]"
                if not isinstance(pr, dict) or not _ist_zahl_objekt(pr.get("erwartet")):
                    f.append(f"{s}.erwartet: Zahl-Objekt fehlt")
                elif not pruefung._datum_ok(pr.get("pruefen_ab")) or date.fromisoformat(pr["pruefen_ab"]) <= heute:
                    f.append(f"{s}.pruefen_ab: Datum JJJJ-MM-TT in der Zukunft")
            for j, e in enumerate(p.get("entwuerfe") or []):
                if not isinstance(e, dict) or e.get("art") not in ("kundengespraech", "angebotsanfrage") \
                        or not all(_ist_text(e.get(k)) for k in ("an", "betreff", "text")):
                    f.append(f"pruefungen[{i}].entwuerfe[{j}]: art, an, betreff und text nötig")
    return f


# --- Webquellen ---

def webquellen(daten) -> list[dict]:
    """Alle Zahl-Objekte, deren quelle eine Webangabe {url, zitat, beschreibung} ist."""
    gefunden: list[dict] = []

    def gehen(x):
        if isinstance(x, dict):
            if "wert" in x and isinstance(x.get("quelle"), dict):
                gefunden.append(x)
            for v in x.values():
                gehen(v)
        elif isinstance(x, list):
            for v in x:
                gehen(v)

    gehen(daten)
    return gefunden


def webangabe_fehler(angabe: dict) -> str | None:
    if set(angabe) != {"url", "zitat", "beschreibung"}:
        return "Webquelle braucht genau url, zitat, beschreibung"
    if not isinstance(angabe["url"], str) or not angabe["url"].startswith("https://"):
        return f"Webquelle ohne https-URL: {angabe['url']!r}"
    if not _ist_text(angabe["zitat"]) or not _ist_text(angabe["beschreibung"]):
        return "Webquelle ohne zitat oder beschreibung"
    return None


def webquelle_pruefen(wert: float, zitat: str, seitentext: str, steht_in) -> str | None:
    """Fehlertext oder None. steht_in ist agentkit.wortlaut.steht_in (übergeben, damit hier ohne agentkit)."""
    if not steht_in(zitat, seitentext):
        return "Zitat steht nicht wörtlich auf der Seite"
    if not pruefung.im_rohinhalt(wert, quellen.zahlen_im_rohinhalt(zitat.encode("utf-8"))):
        return f"Zahl {wert} steht nicht im Zitat"
    return None


def lesen(pfad) -> tuple[dict | None, str | None]:
    """JSON-Datei lesen: (daten, None) oder (None, Fehlertext)."""
    try:
        text = pfad.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, f"Datei {pfad.name} fehlt"
    # Claude setzt JSON manchmal in einen Markdown-Block
    text = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text)
    try:
        daten = json.loads(text)
    except json.JSONDecodeError as f:
        return None, f"Kein gültiges JSON: {f}"
    if not isinstance(daten, dict):
        return None, "Ergebnis muss ein JSON-Objekt sein"
    return daten, None


# --- Variante AKTIEN: Anlagemöglichkeiten (Firmen, ETFs) ---

UEBERSICHT = "uebersicht.json"  # schreibt Python nach der Phase Primärdaten (nur Variante AKTIEN)
MAX_FIRMEN, MAX_ETFS = 15, 5
_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,14}$")
THEMENANTEIL = ("hoch", "mittel", "gering")
BEWERTUNG = ("guenstig", "fair", "teuer", "unklar")

AKTIEN_ZUSATZ = """\
Hinweise zu Börsendaten:
- Die SEC-Auszüge und Kurse in der Übersicht stehen in ganzen Einheiten (z. B. 130497000000 USD). Schreibe
  Beträge in Mio oder Mrd mit passender Einheit ("Mrd USD"); Python erkennt die Umrechnung.
- Kurs und Abschluss müssen in derselben Währung verrechnet werden. Sonst brauchst du einen Wechselkurs
  (Eurostat aus der Übersicht oder Annahme) als eigenes Zahl-Objekt in der Rechnung.
- Anteile und Raten als Dezimalzahl mit Einheit "Anteil" (0.25 statt 25 %), Wachstum als Faktor oder Anteil,
  wie es die Aufgabe sagt.
- Du gibst keine Kauf- oder Verkaufsaufträge. Thesen sind prüfbare Aussagen mit Abbruchkriterien."""

SCHRITTE_AKTIEN = (
    Schritt(1, "Auswahl und Gewinnverteilung", """\
Zerlege das Thema in Teilbereiche der Wertschöpfungskette (z. B. Chips und Rechenzentren, Komponenten wie
Antriebe und Sensoren, Roboterhersteller, Software und Modelle, Integratoren, Anwender). Beschreibe je Bereich,
wo heute der Gewinn anfällt und warum (Marktmacht, Engpass, Wettbewerb).
Wähle börsennotierte Firmen, die einen wesentlichen Teil ihres Geschäfts im Thema haben: höchstens 15 Firmen
insgesamt und höchstens 5 ETFs zum Thema. Je Firma: Name, Börsenkürzel wie bei Yahoo Finance ("symbol", z. B.
NVDA, 6954.T, SIE.DE, ABBN.SW, 2330.TW; nimm die Heimatbörse, damit Kurs und Abschluss möglichst dieselbe
Währung haben), Land, "cik" (ganze Zahl), wenn die Firma bei der SEC Abschlüsse einreicht (10-K, 20-F, 40-F;
sonst weglassen), Themenanteil am Geschäft (hoch, mittel, gering) und warum sie dabei ist. CIK und Kürzel
suchst du per WebSearch/WebFetch heraus (z. B. sec.gov/cgi-bin/browse-edgar), erfinde keine.
Keine Kennzahlen schätzen: Abschlüsse und Kurse lädt Python nach diesem Schritt. Zahlen in dieser Datei sind
nur nötig, wenn du einen Gewinnanteil belegen willst.""",
             '{"thema": "...", "bereiche": [{"name": "...", "gewinn": "wo und warum hier Gewinn anfällt", '
             '"firmen": [{"name": "...", "symbol": "NVDA", "land": "US", "cik": 1045810, "themenanteil": "hoch", '
             '"warum": "..."}]}], "etfs": [{"name": "...", "symbol": "...", "warum": "..."}], '
             '"offene_punkte": ["..."]}'),
    Schritt(2, "Kennzahlen und Bewertung", """\
Je Firma aus Schritt 1: Kennzahlen des letzten Geschäftsjahres und Bewertung zum aktuellen Kurs. Belege mit
den Quellen-IDs aus der Übersicht (SEC-Auszug, Kurs). Für Firmen ohne SEC-Daten nimm den Geschäftsbericht von
der Investor-Relations-Seite (Webquelle, PDF erlaubt). Rechne mit "berechnet" (Python rechnet nach):
- operative_marge = quotient(operatives Ergebnis, Umsatz), Einheit "Anteil"
- umsatzwachstum = quotient(Umsatz letztes Jahr, Umsatz Vorjahr), Einheit "Faktor"
- freier_cashflow = differenz(operativer Cashflow, Investitionen in Sachanlagen)
- marktkapitalisierung = produkt(Kurs, ausstehende Aktien)
- kgv = quotient(Marktkapitalisierung, Nettoergebnis)
- fcf_rendite = quotient(freier Cashflow, Marktkapitalisierung), Einheit "Anteil"
Pflicht je Firma: umsatz, operative_marge, marktkapitalisierung; die übrigen, soweit Daten da sind.
Firmen ohne belastbare Daten nimmst du nicht in "firmen" auf, sondern nennst sie unter "offene_punkte" mit Grund.
Je ETF: aktueller Kurs und Entwicklung über 5 Jahre = quotient(aktueller Kurs, Monatsschluss vor 5 Jahren),
laufende Kosten (TER) als Webquelle des Anbieters, wenn erreichbar.""",
             '{"firmen": [{"name": "...", "symbol": "...", "jahr": 2025, "waehrung": "USD", "umsatz": <Zahl>, '
             '"umsatzwachstum": <Zahl>, "operative_marge": <Zahl>, "freier_cashflow": <Zahl>, "kurs": <Zahl>, '
             '"marktkapitalisierung": <Zahl>, "kgv": <Zahl>, "fcf_rendite": <Zahl>, "kommentar": "..."}], '
             '"etfs": [{"name": "...", "symbol": "...", "kurs": <Zahl>, "entwicklung_5_jahre": <Zahl>, '
             '"kosten": <Zahl>, "kommentar": "..."}], "offene_punkte": ["..."]}'),
    Schritt(3, "Was der Kurs einpreist", """\
Wähle aus Schritt 2 höchstens 8 Firmen, die für das Thema am wichtigsten sind. Je Firma:
- eingepreistes_wachstum: welches dauerhafte jährliche Wachstum des freien Cashflows der Kurs unterstellt,
  vereinfacht = differenz(geforderte Rendite, FCF-Rendite). Die geforderte Rendite ist eine Annahme (Begründung,
  z. B. 0.09 für einen großen, stabilen Konzern, mehr für zyklische oder kleine Firmen); die FCF-Rendite kommt
  als berechnet aus Schritt 2. Bei negativem freiem Cashflow: stattdessen "eingepreist_text" mit Begründung und
  eingepreistes_wachstum weglassen.
- erwartetes_wachstum: was belegbar zu erwarten ist (Ausblick der Firma, Auftragsbestand, Marktwachstum aus
  Primärdaten oder Verbänden), als Zahl-Objekt.
- burggraben (Five Forces knapp), zyklus, risiken (Liste), bewertung (guenstig, fair, teuer, unklar) mit
  begruendung: Ist das eingepreiste Wachstum höher oder niedriger als das erwartete, und wie sicher?""",
             '{"bewertungen": [{"name": "...", "symbol": "...", "eingepreistes_wachstum": <Zahl mit berechnet '
             'differenz>, "erwartetes_wachstum": <Zahl>, "burggraben": "...", "zyklus": "...", "risiken": ["..."], '
             '"bewertung": "fair", "begruendung": "..."}]}'),
    Schritt(4, "Anlagethesen", """\
Leite höchstens drei Anlagethesen aus den Schritten 1 bis 3 ab. Eine These betrifft eine Aktie, einen ETF oder
einen kleinen Korb (höchstens 5 Titel), z. B. auch "breiter ETF statt Einzelaktien, weil ...". Je These:
These, Begründung mit Zahlen, Instrumente (Name, Symbol), das stärkste Gegenargument, Risiken, drei Szenarien
(pessimistisch, basis, optimistisch) je mit erwarteter Rendite pro Jahr ("rendite_pa", Einheit "Anteil",
Kurs plus Dividende) und der Annahme dahinter, Anlagehorizont ("bis_jahr"), Sicherheitsgrad (niedrig, mittel,
hoch) und VORHER festgelegte Abbruchkriterien mit Prüfdatum (JJJJ-MM-TT, in der Zukunft), die sich an
Kennzahlen prüfen lassen (z. B. "operative Marge im Abschluss 2027 unter 0.2"). Eine gut belegte These ist
besser als drei schwache. Ist nichts attraktiv bewertet, darf eine These auch lauten: abwarten bis Bedingung X.""",
             '{"hypothesen": [{"titel": "...", "these": "...", "begruendung": "...", "instrumente": [{"name": "...", '
             '"symbol": "..."}], "gegenargument": "...", "risiken": ["..."], "bis_jahr": 2031, "sicherheit": "mittel", '
             '"szenarien": {"pessimistisch": {"rendite_pa": <Zahl>, "text": "..."}, "basis": {...}, '
             '"optimistisch": {...}}, "abbruchkriterien": [{"text": "...", "pruefen_bis": "2027-12-31"}]}]}'),
    Schritt(5, "Gegenprüfung", """\
Prüfe jede These aus Schritt 4 von außen:
- vergleich: höchstens zwei Alternativen (Wettbewerber oder breiter ETF) mit derselben Kennzahl, an der die These
  hängt, als Zahl-Objekt.
- rueckrechnung: ein bekannter Fall aus den Kursreihen oder Abschlüssen, z. B. was die These vor 3 bis 5 Jahren
  erwartet hätte und was tatsächlich kam (erwartet und tatsaechlich als Zahl-Objekt), mit Fazit.
- prognosen: 1 bis 3 datierte Prognosen, die Python später gegen SEC-Abschlüsse oder Kurse prüfen kann.
  Indikator so genau, dass er abrufbar ist, z. B. "SEC 1045810 umsatz Geschäftsjahr 2027" oder "Kurs NVDA".
Keine Entwürfe für Mails oder Gespräche. Nutze zuerst die Quellen aus den Schritten 1 bis 4; höchstens fünf
neue Webseiten insgesamt.""",
             '{"pruefungen": [{"hypothese": "<titel aus Schritt 4>", "vergleich": [{"name": "...", "ergebnis": "...", '
             '"zahl": <Zahl>}], "rueckrechnung": {"fall": "...", "erwartet": <Zahl>, "tatsaechlich": <Zahl>, '
             '"fazit": "..."}, "prognosen": [{"aussage": "...", "indikator": "...", "erwartet": <Zahl>, '
             '"pruefen_ab": "2027-12-31"}]}]}'),
)


@dataclass(frozen=True)
class Variante:
    name: str
    kopf: str            # erste Zeile jedes Prompts
    schritte: tuple
    zusatz: str = ""     # weitere Regeln im Prompt
    uebersicht: bool = False  # Python legt nach der Phase Primärdaten UEBERSICHT an
    thesen: str = "Hypothese"  # Wort im Text an Jan (Einzahl)


MARKT = Variante("markt", "Recherche zur Wirtschaftlichkeit", SCHRITTE)
AKTIEN = Variante("aktien", "Recherche zu Anlagemöglichkeiten (Aktien und ETFs)", SCHRITTE_AKTIEN,
                  zusatz=AKTIEN_ZUSATZ, uebersicht=True, thesen="These")
_PRAEFIX = re.compile(r"^\s*(aktien|aktie|invest|investment|anlage)\s*:\s*", re.IGNORECASE)


def variante_aus_text(text: str) -> tuple[Variante, str]:
    """Auftragstext -> (Variante, Thema). "aktien: Robotik" -> AKTIEN, "Robotik"; sonst MARKT."""
    m = _PRAEFIX.match(text or "")
    if m:
        return AKTIEN, text[m.end():].strip()
    return MARKT, (text or "").strip()


def _ganze_zahl(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def firmen_aus_auswahl(daten: dict) -> tuple[list[dict], list[dict]]:
    """(Firmen, ETFs) aus Schritt 1 der Variante AKTIEN, nur Einträge mit gültigem Symbol."""
    firmen = [f for b in daten.get("bereiche") or [] if isinstance(b, dict)
              for f in b.get("firmen") or [] if isinstance(f, dict) and _SYMBOL.match(str(f.get("symbol", "")))]
    etfs = [e for e in daten.get("etfs") or [] if isinstance(e, dict) and _SYMBOL.match(str(e.get("symbol", "")))]
    return firmen, etfs


def aktien_abfragen(daten: dict) -> list[dict]:
    """Abfragen (Format abrufer.py) aus Schritt 1: je Firma Kurs und, mit CIK, SEC; je ETF Kurs. Ohne Claude."""
    firmen, etfs = firmen_aus_auswahl(daten)
    abfragen, gesehen = [], set()
    for f in firmen[:MAX_FIRMEN]:
        if f["symbol"] not in gesehen:
            gesehen.add(f["symbol"])
            abfragen.append({"art": "kurs", "symbol": f["symbol"], "beschreibung": f"Kurs {f.get('name')} ({f['symbol']})"})
        if _ganze_zahl(f.get("cik")) and f["cik"] > 0:
            abfragen.append({"art": "sec", "cik": f["cik"],
                             "beschreibung": f"SEC-Abschlüsse {f.get('name')} (CIK {f['cik']})"})
    for e in etfs[:MAX_ETFS]:
        if e["symbol"] not in gesehen:
            gesehen.add(e["symbol"])
            abfragen.append({"art": "kurs", "symbol": e["symbol"], "beschreibung": f"Kurs ETF {e.get('name')} ({e['symbol']})"})
    return abfragen


def wechselkurs_abfragen(waehrungen: set[str]) -> list[dict]:
    """Eurostat-Jahresdurchschnitt der Wechselkurse (1 EUR = x Währung) für alle Nicht-Euro-Währungen."""
    return [{"art": "eurostat", "datensatz": "ert_bil_eur_a", "filter": {"currency": w, "statinfo": "AVG"},
             "von_jahr": 2020, "beschreibung": f"Wechselkurs EUR/{w}, Jahresdurchschnitt (Eurostat)"}
            for w in sorted(x for x in waehrungen if isinstance(x, str) and re.fullmatch(r"[A-Z]{3}", x) and x != "EUR")][:6]


def uebersicht(ergebnisse: list[dict], auszuege: dict[str, dict]) -> dict:
    """Übersicht für Claude aus abfragen_ergebnis (Liste {abfrage, id|fehler}) und den Auszügen je Quellen-ID.

    Je Kurs: aktueller Kurs, Stand, Währung, Monatsschluss vor rund 5 Jahren; je SEC-Firma die letzten 3 Jahre
    jeder Kennzahl und die ausstehenden Aktien. Werte unverändert aus den Rohdaten (Abgleich in pruefung.py).
    """
    kurse, abschluesse, wechselkurse, fehlgeschlagen = [], [], [], []
    for e in ergebnisse:
        a, qid = e.get("abfrage") or {}, e.get("id")
        if not qid:
            fehlgeschlagen.append(f"{a.get('beschreibung')}: {e.get('fehler')}")
            continue
        d = auszuege.get(qid) or {}
        if a.get("art") == "kurs":
            reihe = d.get("monatsschluss") or []
            kurse.append({"quelle": qid, "symbol": d.get("symbol"), "waehrung": d.get("waehrung"),
                          "kurs_aktuell": d.get("kurs_aktuell"), "stand": d.get("stand"),
                          "erster_monatsschluss": reihe[0] if reihe else None})
        elif a.get("art") == "sec":
            kz = {}
            for name, w in (d.get("kennzahlen") or {}).items():
                if "jahre" in w:
                    kz[name] = {"einheit": w.get("einheit"),
                                "jahre": [{"bis": j.get("bis"), "wert": j.get("wert")} for j in w["jahre"][:3]]}
                else:
                    kz[name] = w
            abschluesse.append({"quelle": qid, "firma": d.get("firma"), "cik": d.get("cik"), "kennzahlen": kz})
        else:
            wechselkurse.append({"quelle": qid, "beschreibung": a.get("beschreibung")})
    return {"hinweis": "Werte aus den Rohdaten der genannten Quelle; als quelle die Quellen-ID angeben. Vollständige "
                       "Reihen in der Rohdatei der Quelle.",
            "kurse": kurse, "abschluesse": abschluesse, "wechselkurse": wechselkurse,
            "nicht_geladen": fehlgeschlagen}


def pflichtfelder_aktien(nr: int, daten: dict, heute: date) -> list[str]:
    f: list[str] = []
    if nr == 1:
        if not _ist_text(daten.get("thema")):
            f.append("thema: fehlt")
        anzahl = 0
        for i, b in enumerate(_liste(daten, "bereiche", f)):
            if not isinstance(b, dict) or not _ist_text(b.get("name")):
                f.append(f"bereiche[{i}].name: fehlt")
                continue
            for j, fi in enumerate(b.get("firmen") or []):
                s = f"bereiche[{i}].firmen[{j}]"
                anzahl += 1
                if not isinstance(fi, dict) or not _ist_text(fi.get("name")):
                    f.append(f"{s}.name: fehlt")
                    continue
                if not _SYMBOL.match(str(fi.get("symbol", ""))):
                    f.append(f"{s}.symbol: Börsenkürzel wie bei Yahoo Finance, z. B. NVDA oder 6954.T")
                if "cik" in fi and not (_ganze_zahl(fi["cik"]) and fi["cik"] > 0):
                    f.append(f"{s}.cik: ganze Zahl oder weglassen")
                if fi.get("themenanteil") not in THEMENANTEIL:
                    f.append(f"{s}.themenanteil: {', '.join(THEMENANTEIL)}")
        if not 1 <= anzahl <= MAX_FIRMEN:
            f.append(f"bereiche: 1 bis {MAX_FIRMEN} Firmen insgesamt, nicht {anzahl}")
        etfs = daten.get("etfs") or []
        if not isinstance(etfs, list) or len(etfs) > MAX_ETFS:
            f.append(f"etfs: Liste mit höchstens {MAX_ETFS} Einträgen")
        else:
            for j, e in enumerate(etfs):
                if not isinstance(e, dict) or not _ist_text(e.get("name")) \
                        or not _SYMBOL.match(str(e.get("symbol", ""))):
                    f.append(f"etfs[{j}]: name und symbol nötig")
    elif nr == 2:
        for i, fi in enumerate(_liste(daten, "firmen", f)):
            if not isinstance(fi, dict):
                f.append(f"firmen[{i}]: muss ein Objekt sein")
                continue
            for k in ("umsatz", "operative_marge", "marktkapitalisierung"):
                if not _ist_zahl_objekt(fi.get(k)):
                    f.append(f"firmen[{i}].{k}: Zahl-Objekt fehlt (sonst Firma unter offene_punkte)")
    elif nr == 3:
        for i, b in enumerate(_liste(daten, "bewertungen", f)):
            if not isinstance(b, dict):
                f.append(f"bewertungen[{i}]: muss ein Objekt sein")
                continue
            if b.get("bewertung") not in BEWERTUNG:
                f.append(f"bewertungen[{i}].bewertung: {', '.join(BEWERTUNG)}")
            ew = b.get("eingepreistes_wachstum")
            if ew is None:
                if not _ist_text(b.get("eingepreist_text")):
                    f.append(f"bewertungen[{i}]: eingepreistes_wachstum oder eingepreist_text nötig")
            elif not _ist_zahl_objekt(ew) or not isinstance(ew.get("berechnet"), dict) \
                    or ew["berechnet"].get("art") != "differenz":
                f.append(f"bewertungen[{i}].eingepreistes_wachstum: berechnet, art differenz "
                         "(geforderte Rendite minus FCF-Rendite)")
        if len(daten.get("bewertungen") or []) > 8:
            f.append("bewertungen: höchstens 8 Firmen")
    elif nr == 4:
        hyp = daten.get("hypothesen")
        if not isinstance(hyp, list):
            f.append("hypothesen: fehlt")
        else:
            for i, h in enumerate(hyp):
                if not isinstance(h, dict):
                    continue  # meldet pruefung.hypothesen_pruefen
                inst = h.get("instrumente")
                if not isinstance(inst, list) or not 1 <= len(inst) <= 5 or not all(
                        isinstance(x, dict) and _SYMBOL.match(str(x.get("symbol", ""))) for x in inst):
                    f.append(f"hypothesen[{i}].instrumente: 1 bis 5 Einträge mit name und symbol")
                if not _ist_text(h.get("gegenargument")):
                    f.append(f"hypothesen[{i}].gegenargument: fehlt")
                if not isinstance(h.get("risiken"), list) or not h["risiken"]:
                    f.append(f"hypothesen[{i}].risiken: mindestens ein Risiko")
                for name, sz in (h.get("szenarien") or {}).items() if isinstance(h.get("szenarien"), dict) else ():
                    if not isinstance(sz, dict) or not _ist_zahl_objekt(sz.get("rendite_pa")):
                        f.append(f"hypothesen[{i}].szenarien.{name}.rendite_pa: Zahl-Objekt fehlt")
    elif nr == 5:
        for i, p in enumerate(_liste(daten, "pruefungen", f)):
            if not isinstance(p, dict):
                f.append(f"pruefungen[{i}]: muss ein Objekt sein")
                continue
            if p.get("entwuerfe"):
                f.append(f"pruefungen[{i}].entwuerfe: in dieser Recherche keine Entwürfe")
            prognosen = p.get("prognosen")
            if not isinstance(prognosen, list) or not 1 <= len(prognosen) <= 3:
                f.append(f"pruefungen[{i}].prognosen: 1 bis 3 Prognosen")
                continue
            for j, pr in enumerate(prognosen):
                s = f"pruefungen[{i}].prognosen[{j}]"
                if not isinstance(pr, dict) or not _ist_zahl_objekt(pr.get("erwartet")):
                    f.append(f"{s}.erwartet: Zahl-Objekt fehlt")
                elif not pruefung._datum_ok(pr.get("pruefen_ab")) or date.fromisoformat(pr["pruefen_ab"]) <= heute:
                    f.append(f"{s}.pruefen_ab: Datum JJJJ-MM-TT in der Zukunft")
    return f
