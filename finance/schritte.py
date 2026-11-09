"""Die fünf Schritte einer Recherche: Aufgabe, Prompt, Pflichtfelder, Webquellen (nur Bordmittel, ohne Netz).

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
- Keine nackten Zahlen, auch nicht in Listen. Ausnahme: die Felder "jahr", "von_jahr", "bis_jahr", "nr" (ganze Zahl).
- Zahlen im Fließtext vermeiden. Was du nicht belegen kannst, ist eine Annahme, keine Quelle.
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


def schritt(nr: int) -> Schritt:
    return SCHRITTE[nr - 1]


def quellenliste(metas: list[dict], ordner_rel: str) -> str:
    if not metas:
        return "(noch keine abgelegten Primärdaten; nutze Webquellen und Annahmen)"
    return "\n".join(f"- {m['id']} ({m['art']}, abgerufen {m['abgerufen'][:10]}): {m['beschreibung']}; "
                     f"Rohdaten: {ordner_rel}/{m['id']}.roh.{m['endung']}" for m in metas)


def prompt(s: Schritt, thema: str, ordner_rel: str, quellen_rel: str, metas: list[dict],
           fehler: list[str] | None = None) -> str:
    """Prompt für einen Schritt. Mit fehler: Nachbesserung derselben Datei."""
    vorige = [f"{ordner_rel}/{schritt(n).datei}" for n in range(1, s.nr)]
    teile = [
        f"Recherche zur Wirtschaftlichkeit, Thema: {thema}",
        f"Schritt {s.nr} von 5: {s.name}",
    ]
    if fehler:
        teile.append(f"Deine Datei {ordner_rel}/{s.datei} wurde abgelehnt. Lies sie, korrigiere ALLE "
                     "folgenden Stellen und schreibe sie vollständig neu (Zählung ab 0):\n"
                     + "\n".join(f"- {f}" for f in fehler[:60]))
    teile += [
        "Aufgabe:\n" + s.aufgabe,
        ("Ergebnisse der vorigen Schritte (geprüft, lesen): " + ", ".join(vorige)) if vorige else "",
        f"Schreibe das Ergebnis als JSON nach {ordner_rel}/{s.datei}, sonst keine Dateien. Gerüst:\n{s.beispiel}",
        ZAHL_REGELN,
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


def pflichtfelder(nr: int, daten: dict, heute: date) -> list[str]:
    """Aufbau je Schritt (die Zahlen selbst prüft pruefung.py)."""
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
