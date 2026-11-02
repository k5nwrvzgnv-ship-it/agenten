"""Recherche vor dem Exposé (Jan 02.11.2026: "aufwendig, damit das Ergebnis verlässlich ist").

Grundsatz wie bei lia/recherche: Claude sucht, Python prüft jeden Beleg. Ablauf in data/expose/<kette>/recherche/:
1. eckpunkte.json: Claude liest Transkript und Schriftwechsel und stellt die Recherchefragen (je Frage ein
   Suchfenster, mit Anlass aus der Besprechung).
2. <fenster>.json: je Suchfenster mit Fragen eine eigene Sitzung (WebSearch, WebFetch, lokale Normen), zwei
   Durchgänge (suchen, dann Lücken, Gegenpositionen, Primärquellen). Python prüft danach jeden Beleg: Zitat
   wörtlich auf der Seite bzw. im PDF oder auf der Seite der lokalen Datei, DOI gegen Crossref. Durchgefallenes
   geht einmal zurück in dieselbe Sitzung. Ergebnis <fenster>-geprueft.json.
   Liegt Jans Scopus-Export in recherche/scopus/ (scopus.py), folgt eine eigene Sitzung für die Fragen aus
   Literatur, Methoden und Daten mit der Kandidatenliste scopus.md. Zitate aus einem Abstract prüft Python gegen
   den Export. Kommt der Export erst nach der Gegenprüfung, läuft sie danach noch einmal (Nachtrag).
3. gegenpruefung.json: neue Sitzung, je belegter Aussage "trägt das Zitat die Aussage?" (ja, teilweise, nein),
   dazu Widersprüche zwischen Quellen und unbeantwortete Fragen.
4. geprueft.json (für das Exposé) und Recherchebericht.md (für Jan und die Gruppe), von Python gebaut.

Jede Stufe legt ihre Datei ab, ein neuer Anlauf (z. B. nach Kontingentpause) setzt dort fort und bezahlt nichts
doppelt. stand.json hält Kosten und Sitzungen. Die Kostengrenze gilt für die ganze Recherche.
Netz nur über die übergebenen Funktionen seitentext(url) und metadaten(doi), die echten stehen am Ende (dünn).
"""

import json
import re
import tempfile
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, urlsplit

from agentkit import abruf, textfassung, wortlaut

import normen
import scopus

ORDNER = "recherche"
# Jan 02.11.2026: 50 USD je Recherche. Ein Suchlauf startet nur, wenn danach noch die Reserve für
# Gegenprüfung und Exposé frei ist.
GRENZE_USD = 50.0
LAUF_USD = 4.0
RESERVE_USD = 5.0
DURCHGAENGE = 2
FRAGEN_MAX = 24
ZITAT_LAENGE = (15, 400)

# Suchfenster: Schlüssel -> (Titel, worauf die Suche achtet)
FENSTER = {
    "literatur": ("Veröffentlichte Forschung",
                  "Fachartikel, Konferenzbeiträge, Dissertationen und Abschlussarbeiten. Such deutsch und englisch, "
                  "mit Fachbegriffen und Synonymen (z. B. wood defect detection, knot detection, lumber grading, "
                  "machine vision). Begutachtete Arbeiten mit DOI zuerst, neuere zuerst, Übersichtsarbeiten nutzen, "
                  "um Primärarbeiten zu finden. Nenne Datengrundlage und Ergebnisse so, wie sie in der Arbeit stehen."),
    "methoden": ("Verfahren und Modelle",
                 "Welche Verfahren dem Stand der Technik entsprechen, Vergleiche zwischen Modellen, übliche Kennzahlen "
                 "(z. B. Präzision, Trefferquote, mAP) und wovon die Ergebnisse abhängen (Aufnahme, Licht, "
                 "Auflösung, Datenmenge). Vergleichsstudien und Originalveröffentlichungen der Modelle zuerst."),
    "daten": ("Datensätze",
              "Öffentliche Datensätze: wer sie erhoben hat, wie (Linie, Kamera, Holzart, Oberfläche), wie sie "
              "beschriftet sind (Klassen, Bounding Boxes, Segmentierung), Umfang, Lizenz und Bedingungen. Lizenz nur "
              "aus der Seite des Datensatzes selbst."),
    "projekte": ("Laufende und abgeschlossene Projekte",
                 "Forschungsvorhaben bei Hochschulen, Instituten und Firmen, auch unveröffentlichte: "
                 "Förderdatenbanken (z. B. FNR, CORDIS, GEPRIS, Förderkatalog des Bundes), Projektseiten, "
                 "Pressemitteilungen. Laufzeit, Beteiligte und Ziel so, wie sie auf der Seite stehen."),
    "markt": ("Technik am Markt",
              "Anbieter und Systeme, ihre Leistungsangaben, Einsatzbereiche und Preise. Herstellerangaben im Text "
              "als solche kennzeichnen (\"laut Hersteller\"). Preise nur mit Beleg, sonst als Lücke."),
    "regelwerk": ("Normen und Regelwerke",
                  "Zuerst die Normen in data/normen/ (Verzeichnis data/normen/uebersicht.md, Textfassung .txt mit "
                  "\"--- Seite N\", mit Grep suchen). Belege daraus als {\"datei\", \"seite\", \"zitat\"}, kurze "
                  "Zitate, keine langen Auszüge. Fehlt eine nötige Norm, nenne sie als Lücke und gib ihren Inhalt "
                  "nicht aus dem Gedächtnis an. Erläuterungen aus dem Netz (Verbände, Institute) dürfen ergänzen."),
}

# Systematische Literatursuche aus Jans Scopus-Export (Jan 02.11.2026), als zusätzliches Suchfenster
SCOPUS = "scopus"
SCOPUS_TITEL = "Systematische Literatursuche (Scopus)"
SCOPUS_FUER = ("literatur", "methoden", "daten")

KURZREGELN = """Regeln für Belege (Python prüft jeden):
- {"url": "https://...", "zitat": "..."}: Das Zitat steht wörtlich auf dieser Seite bzw. in diesem PDF (Python lädt
  die Adresse und vergleicht Zeichen für Zeichen, nur Leerraum und Silbentrennung zählen nicht). Ein bis zwei
  Sätze, 15 bis 400 Zeichen, aus dem Text kopiert, nicht übersetzt oder gekürzt.
- {"datei": "data/normen/....txt", "seite": 12, "zitat": "..."}: lokale Textfassung unter data/, Seite laut
  "--- Seite N".
- Nur Quellen, die du in dieser Sitzung selbst geöffnet hast (WebFetch bzw. Read). Nichts aus dem Gedächtnis.
- Hinter einer DOI-Adresse (doi.org) steht oft nur eine Verlagsseite mit Zusammenfassung: Zitate dann aus der
  Zusammenfassung oder aus dem frei zugänglichen PDF (dessen Adresse als url).
- art "tatsache": steht so in der Quelle (mindestens ein Beleg). art "einschaetzung": deine Schlussfolgerung,
  im Text als solche erkennbar."""

FORMAT_ECKPUNKTE = """{
  "thema": "Thema in einem Satz",
  "fragen": [{"id": "F1", "fenster": "literatur", "frage": "...", "anlass": "Henri 15:00: ... (oder: für den Stand der Forschung nötig)"}]
}
fenster: """ + ", ".join(FENSTER) + f""". Höchstens {FRAGEN_MAX} Fragen, ids F1, F2, ... ohne Lücken."""

FORMAT_FENSTER = """{
  "aussagen": [{"frage": "F1", "art": "tatsache", "text": "...", "belege": [{"url": "...", "zitat": "..."}]}],
  "quellen": [{"url": "https://...", "titel": "...", "autoren": ["Nachname, V."], "jahr": 2023,
               "doi": "10.xxxx/... oder null", "art": "artikel|konferenz|abschlussarbeit|projekt|datensatz|produkt|norm|sonstiges"}],
  "luecken": ["was du nicht gefunden hast und wo du gesucht hast"]
}
Jede url aus einem Beleg steht genau einmal unter quellen (Angaben so, wie sie auf der Seite stehen)."""

PROMPT_ECKPUNKTE = """Auftrag von Jan: ein Exposé für ein Forschungsprojekt.
{text}

Vor dem Exposé kommt eine gründliche Recherche. Du stellst dafür jetzt nur die Fragen, du recherchierst noch nicht.
Lies das angehängte Besprechungstranskript (Textfassung .txt neben .docx/.pdf) ganz und den Schriftwechsel zum
Projekt (Grep nach Stichworten des Themas in data/mails/ und data/mailauftraege/*/kontext.json).

Stell die Fragen, die das Exposé braucht:
- Jeden Prüfauftrag aus der Besprechung ("müssen wir validieren", "noch zu prüfen", "Research-Auftrag",
  offene oder strittige Annahmen) als eigene Frage, Anlass mit Sprecher und Zeitmarke.
- Was der Stand der Forschung und Technik braucht (Literatur, Verfahren, Daten, Projekte, Markt, Normen).
- Konkret und beantwortbar, Namen von Firmen, Projekten oder Datensätzen so, wie sie im Transkript stehen
  (Hörfehler möglich, dann mit Hinweis "im Transkript: ...").
Keine Fragen, die nur die Gruppe selbst beantworten kann (Zeitplan, Arbeitsteilung).

Schreib {pfad}:
{format}
Antworte danach mit einem Satz."""

PROMPT_SUCHE = """Recherche für ein Exposé. Thema: {thema}
Suchfenster: {titel}. {hinweis}

Deine Fragen:
{fragen}

Alle Fragen der Recherche (nur zur Einordnung, die anderen bearbeiten andere Sitzungen):
{alle}

Arbeite gründlich, das Ergebnis muss verlässlich sein: je Frage mehrere Suchanfragen, deutsch und englisch,
Primärquellen statt Zusammenfassungen Dritter, jede Quelle öffnen, bevor du sie nennst. Widersprechen sich
Quellen, nenn beide. Findest du nichts Belastbares, ist das ein Ergebnis: schreib es unter luecken.

{regeln}

Du hast höchstens etwa 25 Arbeitsschritte. Schreib {pfad} früh (nach etwa 12 Schritten) und ergänze die Datei
danach, damit nichts verloren geht:
{format}
Antworte danach mit einem Satz (Zahl der Aussagen und Lücken)."""

PROMPT_SCOPUS = """Recherche für ein Exposé. Thema: {thema}
Suchfenster: {titel}. Jan hat in Scopus gesucht und die Treffer exportiert. {kandidaten} enthält {anzahl} Arbeiten
ohne Doppelte, nach Zitationen sortiert, je Arbeit Kennung, Suchen, Titel, Autoren, Quelle, DOI, url, Abstract und
Schlagwörter. Oben stehen die Suchen. Sie sind breit, viele Treffer gehören nicht zum Thema.

Deine Fragen:
{fragen}

Alle Fragen der Recherche (nur zur Einordnung):
{alle}

Die Websuche hat diese Fragen schon bearbeitet: {bisher} (nur lesen). Ergänze sie, wiederhole sie nicht.
Ziel ist ein belastbarer Stand der Forschung:
- Durchsuch {kandidaten} mit Grep nach Fachbegriffen der Fragen (englisch, Synonyme) und lies passende Einträge
  ganz. Nimm Übersichtsarbeiten, viel zitierte Arbeiten und neue Arbeiten (seit 2022), nenne je Arbeit
  Datengrundlage und Ergebnisse so, wie sie im Abstract stehen.
- Aussagen über die Forschungslandschaft (z. B. "die meisten Arbeiten nutzen ...") nur, wenn du die Einträge
  dafür gezählt hast, mit der Zahl und als art "einschaetzung".
- Beleg aus dem Abstract: {{"url": "<url des Eintrags>", "zitat": "..."}}, Zitat wörtlich aus Titel, Abstract oder
  Schlagwörtern des Eintrags. Python prüft es gegen den Export. Frei zugängliche Volltexte darfst du mit WebFetch
  öffnen, dann gilt deren Adresse wie sonst auch.
- quellen: titel, autoren, jahr, doi und url so, wie sie im Eintrag stehen, art "artikel" oder "konferenz".

{regeln}

Du hast höchstens etwa 25 Arbeitsschritte. Schreib {pfad} früh (nach etwa 12 Schritten) und ergänze die Datei
danach, damit nichts verloren geht:
{format}
Antworte danach mit einem Satz (Zahl der Aussagen und Lücken)."""

PROMPT_WEITER = """Zweiter Durchgang für dasselbe Suchfenster. Lies {pfad} und such gezielt weiter:
- Fragen ohne oder mit nur einer Quelle, und was unter luecken steht.
- Gegenpositionen und Einschränkungen zu den bisherigen Aussagen.
- Primärquellen für Aussagen, die bisher nur auf Sekundärquellen stehen, und neuere Arbeiten (letzte 3 Jahre).
Ergänze {pfad} (bisherige Einträge behalten, außer sie sind falsch; dann korrigieren). Gleiche Regeln:
{regeln}
Antworte danach mit einem Satz, was neu ist."""

PROMPT_NACHBESSERN = """Python hat {pfad} geprüft. Diese Stellen sind nicht in Ordnung:
{fehler}

Korrigiere sie in {pfad}: Zitat genau so kopieren, wie es auf der Seite steht (oder ein anderes, das dort steht),
andere Quelle suchen, oder den Beleg streichen (eine Tatsache ohne Beleg wird zur Lücke). Antworte mit einem Satz."""

PROMPT_GEGEN = """Gegenprüfung einer Recherche für ein Exposé. Thema: {thema}
Du hast die Recherche nicht selbst gemacht. Prüfe streng, ob die geprüften Zitate die Aussagen wirklich tragen:
- ja: Das Zitat sagt das (allein oder zusammen mit den anderen Zitaten derselben Aussage).
- teilweise: Ein Teil der Aussage (Zahl, Zeitraum, Verallgemeinerung, Name) steht nicht in den Zitaten.
- nein: Die Zitate tragen die Aussage nicht oder sagen etwas anderes.
Bewerte nur anhand der Zitate unten, ohne eigenes Wissen. Nenne außerdem Widersprüche zwischen Aussagen und
Fragen, die die Recherche nicht beantwortet hat.

Fragen:
{fragen}

Aussagen (id, Text, Zitate mit Quelle):
{aussagen}

Schreib {pfad}:
{{"urteile": [{{"id": "literatur-1", "traegt": "ja|teilweise|nein", "fehlt": "was fehlt (leer bei ja)"}}],
 "widersprueche": [{{"ids": ["literatur-1", "markt-2"], "worum": "..."}}],
 "offen": [{{"frage": "F3", "warum": "..."}}]}}
Jede id genau einmal. Antworte danach mit einem Satz."""

PROMPT_DATEI_NACHBESSERN = """{pfad} ist nicht gültig:
{fehler}
Korrigiere die Datei und antworte mit einem Satz."""


class RechercheFehler(Exception):
    pass


@dataclass
class Ergebnis:
    geprueft: Path | None = None  # geprueft.json für das Exposé
    bericht: Path | None = None  # Recherchebericht.md
    usd: float = 0.0
    zeilen: list[str] = field(default_factory=list)  # für das Ergebnis an Jan (Probleme, Zahlen)


def _text(x) -> bool:
    return isinstance(x, str) and bool(x.strip())


def _lies(pfad: Path):
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RechercheFehler(f"{pfad.name} fehlt") from None
    except (OSError, json.JSONDecodeError) as e:
        raise RechercheFehler(f"{pfad.name} ist kein gültiges JSON: {e}") from None


def _schreib(pfad: Path, daten) -> None:
    pfad.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")


# --- Prüfung der Dateien von Claude (rein) ---

def eckpunkte_pruefen(d) -> list[str]:
    if not isinstance(d, dict):
        return ["eckpunkte: muss ein JSON-Objekt sein"]
    fehler = [f"{f}: unbekanntes Feld" for f in sorted(set(d) - {"thema", "fragen"})]
    if not _text(d.get("thema")):
        fehler.append("thema: Text nötig")
    fragen = d.get("fragen")
    if not isinstance(fragen, list) or not 1 <= len(fragen) <= FRAGEN_MAX:
        return fehler + [f"fragen: Liste aus 1 bis {FRAGEN_MAX} Fragen nötig"]
    for i, f in enumerate(fragen):
        ort = f"fragen[{i}]"
        if not isinstance(f, dict):
            fehler.append(f"{ort}: Objekt nötig")
            continue
        if f.get("id") != f"F{i + 1}":
            fehler.append(f"{ort}.id: muss F{i + 1} sein, ist {f.get('id')!r}")
        if f.get("fenster") not in FENSTER:
            fehler.append(f"{ort}.fenster: einer von {', '.join(FENSTER)}")
        for feld in ("frage", "anlass"):
            if not _text(f.get(feld)):
                fehler.append(f"{ort}.{feld}: Text nötig")
    return fehler


def _beleg_fehler(b, ort: str) -> list[str]:
    if not isinstance(b, dict):
        return [f"{ort}: Objekt nötig"]
    zitat = b.get("zitat")
    fehler = []
    if not _text(zitat) or not ZITAT_LAENGE[0] <= len(zitat) <= ZITAT_LAENGE[1]:
        fehler.append(f"{ort}.zitat: {ZITAT_LAENGE[0]} bis {ZITAT_LAENGE[1]} Zeichen nötig")
    if "url" in b:
        if set(b) - {"url", "zitat"} or not _text(b["url"]) or not b["url"].startswith("https://"):
            fehler.append(f"{ort}: {{url (https), zitat}} nötig")
    elif "datei" in b:
        if set(b) - {"datei", "seite", "zitat"} or not _text(b["datei"]) or \
                not (b.get("seite") is None or (isinstance(b["seite"], int) and b["seite"] > 0)):
            fehler.append(f"{ort}: {{datei, seite (Zahl), zitat}} nötig")
    else:
        fehler.append(f"{ort}: url oder datei nötig")
    return fehler


def fenster_pruefen(d, fragen_ids: set[str]) -> list[str]:
    """Aufbau einer <fenster>.json (ohne Netz). fragen_ids: die Fragen dieses Fensters."""
    if not isinstance(d, dict):
        return ["muss ein JSON-Objekt sein"]
    fehler = [f"{f}: unbekanntes Feld" for f in sorted(set(d) - {"aussagen", "quellen", "luecken"})]
    quellen = d.get("quellen", [])
    urls = set()
    if not isinstance(quellen, list):
        fehler.append("quellen: Liste nötig")
        quellen = []
    for i, q in enumerate(quellen):
        ort = f"quellen[{i}]"
        if not isinstance(q, dict) or not _text(q.get("url")) or not _text(q.get("titel")):
            fehler.append(f"{ort}: url und titel nötig")
            continue
        if q["url"] in urls:
            fehler.append(f"{ort}: url doppelt")
        urls.add(q["url"])
        if not isinstance(q.get("autoren", []), list) or not all(_text(a) for a in q.get("autoren", [])):
            fehler.append(f"{ort}.autoren: Liste aus Texten")
        if q.get("jahr") is not None and not (isinstance(q["jahr"], int) and 1900 <= q["jahr"] <= 2100):
            fehler.append(f"{ort}.jahr: Jahreszahl oder null")
        if q.get("doi") is not None and not (_text(q["doi"]) and re.match(r"^10\.\d{4,9}/\S+$", q["doi"])):
            fehler.append(f"{ort}.doi: 10.xxxx/... oder null")
    aussagen = d.get("aussagen")
    if not isinstance(aussagen, list):
        return fehler + ["aussagen: Liste nötig"]
    for i, s in enumerate(aussagen):
        ort = f"aussagen[{i}]"
        if not isinstance(s, dict) or not _text(s.get("text")):
            fehler.append(f"{ort}: text nötig")
            continue
        if s.get("frage") not in fragen_ids:
            fehler.append(f"{ort}.frage: eine von {', '.join(sorted(fragen_ids))}")
        if s.get("art") not in ("tatsache", "einschaetzung"):
            fehler.append(f"{ort}.art: tatsache oder einschaetzung")
        belege = s.get("belege", [])
        if not isinstance(belege, list):
            fehler.append(f"{ort}.belege: Liste nötig")
            continue
        if s.get("art") == "tatsache" and not belege:
            fehler.append(f"{ort}: eine Tatsache braucht mindestens einen Beleg")
        for k, b in enumerate(belege):
            fehler += _beleg_fehler(b, f"{ort}.belege[{k}]")
            if isinstance(b, dict) and _text(b.get("url")) and b["url"] not in urls:
                fehler.append(f"{ort}.belege[{k}]: url fehlt unter quellen")
    if not isinstance(d.get("luecken", []), list) or not all(_text(x) for x in d.get("luecken", [])):
        fehler.append("luecken: Liste aus Texten")
    return fehler


# --- Belege prüfen (ohne Netz, Netz kommt über seitentext und metadaten) ---

def _lokale_datei(hier: Path, datei: str) -> Path | None:
    """Nur Textfassungen unter data/ (kein Ausbruch über .. oder Symlinks)."""
    basis = (hier / "data").resolve()
    pfad = (hier / datei).resolve()
    if not pfad.is_relative_to(basis) or pfad.suffix not in (".txt", ".md") or not pfad.is_file():
        return None
    return pfad


def steht_in(zitat: str, text: str) -> bool:
    """wortlaut.steht_in nach NFKC: Ligaturen aus PDFs (ﬁ, ﬂ) und Sonderleerzeichen wie getippter Text."""
    return wortlaut.steht_in(unicodedata.normalize("NFKC", zitat), unicodedata.normalize("NFKC", text))


def beleg_pruefen(b: dict, hier: Path, seitentext, abstracts: dict[str, str] | None = None) -> dict:
    """{"status": bestanden|durchgefallen|ungeprueft, "vermerk"}. seitentext(url) -> Text, wirft AbrufFehler;
    für eine Domain außerhalb der Liste wirft er DomainNichtErlaubt. abstracts: scopus.abstracts (Zitate aus dem
    Abstract gelten ohne Abruf, sonst wird die Seite geladen)."""
    if "datei" in b:
        pfad = _lokale_datei(hier, b["datei"])
        if pfad is None:
            return {"status": "durchgefallen", "vermerk": "Datei gibt es nicht (nur .txt/.md unter data/)"}
        text = pfad.read_text(encoding="utf-8", errors="replace")
        if b.get("seite") is not None:
            text = wortlaut.seiten(text).get(b["seite"])
            if text is None:
                return {"status": "durchgefallen", "vermerk": f"Seite {b['seite']} gibt es in der Datei nicht"}
        if steht_in(b["zitat"], text):
            return {"status": "bestanden", "vermerk": "Zitat in der lokalen Datei gefunden"}
        return {"status": "durchgefallen", "vermerk": "Zitat steht nicht wörtlich auf dieser Seite der Datei"}
    abstract = (abstracts or {}).get(scopus.schluessel(b["url"]))
    if abstract and steht_in(b["zitat"], abstract):
        return {"status": "bestanden", "vermerk": "Zitat im Abstract laut Scopus-Export gefunden"}
    try:
        text = seitentext(b["url"])
    except DomainNichtErlaubt:
        return {"status": "ungeprueft", "vermerk": "Domain nicht auf der Liste, nicht geladen"}
    except abruf.AbrufFehler as e:
        return {"status": "durchgefallen", "vermerk": f"Seite nicht ladbar: {e}"}
    if steht_in(b["zitat"], text):
        return {"status": "bestanden", "vermerk": "Zitat auf der Seite gefunden"}
    return {"status": "durchgefallen", "vermerk": "Zitat steht nicht wörtlich auf der Seite"}


def _woerter(text: str) -> set[str]:
    return set(re.findall(r"\w{3,}", text.lower()))


def doi_vergleichen(q: dict, meta: dict) -> dict:
    """Quellenangabe gegen Crossref: Titel (Wortüberschneidung), Jahr und Nachname des ersten Autors."""
    abweichungen = []
    t1, t2 = _woerter(q.get("titel", "")), _woerter(meta.get("titel", ""))
    if not t1 or not t2 or len(t1 & t2) / max(len(t1), len(t2)) < 0.7:
        abweichungen.append(f"Titel laut Crossref: {meta.get('titel', '')!r}")
    if q.get("jahr") is not None and meta.get("jahr") is not None and q["jahr"] != meta["jahr"]:
        abweichungen.append(f"Jahr laut Crossref: {meta['jahr']}")
    nachnamen = [n.lower() for n in meta.get("nachnamen", [])]
    if q.get("autoren") and nachnamen and not any(n in q["autoren"][0].lower() for n in nachnamen):
        abweichungen.append(f"Autoren laut Crossref: {', '.join(meta.get('nachnamen', [])[:3])}")
    if abweichungen:
        return {"status": "durchgefallen", "vermerk": "; ".join(abweichungen)}
    return {"status": "bestanden", "vermerk": "DOI, Titel, Jahr und Autor stimmen mit Crossref überein"}


def doi_pruefen(q: dict, metadaten) -> dict:
    if not q.get("doi"):
        return {"status": "ungeprueft", "vermerk": "ohne DOI"}
    try:
        meta = metadaten(q["doi"])
    except DomainNichtErlaubt:
        return {"status": "ungeprueft", "vermerk": "Crossref nicht auf der Liste"}
    except abruf.AbrufFehler as e:
        return {"status": "durchgefallen", "vermerk": f"DOI bei Crossref nicht gefunden: {e}"}
    return doi_vergleichen(q, meta)


def fenster_belege_pruefen(d: dict, hier: Path, seitentext, metadaten, abstracts: dict[str, str] | None = None) -> dict:
    """Setzt "pruefung" an jedem Beleg und jeder Quelle, "belegt" an jeder Aussage."""
    for q in d.get("quellen", []):
        q["pruefung"] = doi_pruefen(q, metadaten)
    for s in d["aussagen"]:
        for b in s.get("belege", []):
            b["pruefung"] = beleg_pruefen(b, hier, seitentext, abstracts)
        s["belegt"] = any(b["pruefung"]["status"] == "bestanden" for b in s.get("belege", []))
    return d


def durchgefallene(d: dict) -> list[str]:
    aus = []
    for i, q in enumerate(d.get("quellen", [])):
        if q.get("pruefung", {}).get("status") == "durchgefallen":
            aus.append(f"quellen[{i}] ({q['url']}): {q['pruefung']['vermerk']}")
    for i, s in enumerate(d["aussagen"]):
        for k, b in enumerate(s.get("belege", [])):
            if b.get("pruefung", {}).get("status") == "durchgefallen":
                wo = b.get("url") or f"{b.get('datei')} Seite {b.get('seite')}"
                aus.append(f"aussagen[{i}].belege[{k}] ({s['text'][:80]}): {wo} | Zitat {b['zitat'][:120]!r} -> "
                           f"{b['pruefung']['vermerk']}")
    return aus


# --- Gegenprüfung ---

def zur_gegenpruefung(fenster: dict[str, dict]) -> list[dict]:
    """Belegte Aussagen mit ids <fenster>-<n> (n ab 1 je Fenster) und ihren bestandenen Zitaten."""
    aus = []
    for name, d in fenster.items():
        for n, s in enumerate(d["aussagen"], 1):
            s["id"] = f"{name}-{n}"
            if s.get("belegt"):
                zitate = [(b.get("url") or f"{b['datei']} S. {b.get('seite')}", b["zitat"])
                          for b in s["belege"] if b["pruefung"]["status"] == "bestanden"]
                aus.append({"id": s["id"], "text": s["text"], "zitate": zitate})
    return aus


def gegen_pruefen(d, ids: set[str]) -> list[str]:
    if not isinstance(d, dict) or not isinstance(d.get("urteile"), list):
        return ["urteile: Liste nötig"]
    fehler, gesehen = [], set()
    for i, u in enumerate(d["urteile"]):
        if not isinstance(u, dict) or u.get("id") not in ids:
            fehler.append(f"urteile[{i}].id: unbekannt ({u.get('id') if isinstance(u, dict) else u!r})")
            continue
        if u["id"] in gesehen:
            fehler.append(f"urteile[{i}].id: {u['id']} doppelt")
        gesehen.add(u["id"])
        if u.get("traegt") not in ("ja", "teilweise", "nein"):
            fehler.append(f"urteile[{i}].traegt: ja, teilweise oder nein")
    if fehlend := sorted(ids - gesehen):
        fehler.append(f"urteile: es fehlen {', '.join(fehlend)}")
    for feld in ("widersprueche", "offen"):
        if not isinstance(d.get(feld, []), list):
            fehler.append(f"{feld}: Liste nötig")
    return fehler


# --- Zusammenführen und Bericht ---

def fenster_titel(name: str) -> str:
    return SCOPUS_TITEL if name == SCOPUS else FENSTER[name][0]


STATUS_TEXT = {"gesichert": "gesichert", "teilweise": "nur teilweise belegt", "verworfen": "verworfen",
               "unbelegt": "nicht belegt", "einschaetzung": "Einschätzung"}


def zusammenfuehren(eck: dict, fenster: dict[str, dict], gegen: dict | None, suche: dict | None = None) -> dict:
    """geprueft.json: Aussagen mit status, zitierfähige Quellen, Lücken, Widersprüche, Zahlen.
    suche: scopus.beschreibung, wenn ein Scopus-Export einbezogen ist."""
    urteile = {u["id"]: u for u in (gegen or {}).get("urteile", [])}
    aussagen, quellen, luecken = [], [], []
    for name, d in fenster.items():
        for n, s in enumerate(d["aussagen"], 1):
            s.setdefault("id", f"{name}-{n}")
            u = urteile.get(s["id"])
            if not s.get("belegt"):
                status = "einschaetzung" if s.get("art") == "einschaetzung" else "unbelegt"
            elif u is None:
                status = "teilweise"  # belegt, aber nicht gegengeprüft
            else:
                status = {"ja": "gesichert", "teilweise": "teilweise", "nein": "verworfen"}[u["traegt"]]
            aussagen.append({"id": s["id"], "fenster": name, "frage": s["frage"], "art": s.get("art"),
                             "text": s["text"], "status": status, "fehlt": (u or {}).get("fehlt", ""),
                             "belege": s.get("belege", [])})
        tragend = {b.get("url") for a in aussagen if a["fenster"] == name and a["status"] in ("gesichert", "teilweise")
                   for b in a["belege"] if b["pruefung"]["status"] == "bestanden"}
        for q in d.get("quellen", []):
            q = {**q, "fenster": name}
            q["zitierfaehig"] = q["url"] in tragend and q["pruefung"]["status"] != "durchgefallen"
            quellen.append(q)
        luecken += [{"fenster": name, "text": x} for x in d.get("luecken", [])]
    zahlen = {s: sum(a["status"] == s for a in aussagen) for s in STATUS_TEXT}
    zahlen["quellen_zitierfaehig"] = sum(q["zitierfaehig"] for q in quellen)
    return {"thema": eck["thema"], "fragen": eck["fragen"], "aussagen": aussagen, "quellen": quellen,
            "luecken": luecken, "widersprueche": (gegen or {}).get("widersprueche", []),
            "offen": (gegen or {}).get("offen", []), "zahlen": zahlen,
            **({"literatursuche": suche} if suche else {})}


def normquellen(geprueft: dict) -> set[str]:
    """Kennungen der lokalen Normen, aus denen ein tragender Beleg stammt (Nautos-Dateiname)."""
    aus = set()
    for a in geprueft["aussagen"]:
        if a["status"] not in ("gesichert", "teilweise"):
            continue
        for b in a["belege"]:
            if b.get("datei", "").startswith("data/normen/") and b["pruefung"]["status"] == "bestanden":
                name = Path(b["datei"]).name.removesuffix(".txt")
                if k := normen.aus_dateiname(name):
                    aus.add(k[0])
    return aus


def literatur_pruefen(literatur: list[str], geprueft: dict) -> list[str]:
    """Jede Literaturangabe nennt DOI oder Adresse einer zitierfähigen Quelle oder eine verwendete lokale Norm."""
    schluessel = []
    for q in geprueft["quellen"]:
        if q["zitierfaehig"]:
            schluessel += [q["url"].lower()] + ([q["doi"].lower()] if q.get("doi") else [])
    kennungen = normquellen(geprueft)
    fehler = []
    for i, eintrag in enumerate(literatur):
        e = eintrag.lower()
        if not any(s in e for s in schluessel) and not any(k.lower() in e for k in kennungen):
            fehler.append(f"literatur[{i}]: {eintrag[:80]!r} ist keine geprüfte Quelle der Recherche (DOI oder "
                          "Adresse einer zitierfähigen Quelle aus geprueft.json angeben, Normen mit Kennung)")
    return fehler


def bericht(g: dict, usd: float, export: "scopus.Export | None" = None) -> str:
    """Recherchebericht für Jan und die Gruppe (Markdown, alle Belege mit Prüfvermerk)."""
    z = g["zahlen"]
    zeilen = [f"# Recherchebericht: {g['thema']}", "",
              f"{len(g['aussagen'])} Aussagen: {z['gesichert']} gesichert, {z['teilweise']} nur teilweise belegt, "
              f"{z['verworfen']} verworfen, {z['unbelegt']} nicht belegt, {z['einschaetzung']} Einschätzungen. "
              f"{z['quellen_zitierfaehig']} zitierfähige Quellen. Kosten {usd:.2f} USD.", "",
              "Gesichert: Zitat wörtlich auf der Quelle gefunden und in der Gegenprüfung als tragend bewertet. "
              "Teilweise: belegt, aber ein Teil der Aussage steht nicht im Zitat (oder nicht gegengeprüft). "
              "Nur Gesichertes steht im Exposé als Tatsache."]
    if export:
        verwendet = {scopus.schluessel(q["url"]) for q in g["quellen"] if q["zitierfaehig"]}
        zeilen += scopus.uebersicht_md(export, verwendet)
    for f in g["fragen"]:
        zeilen += ["", f"## {f['id']}: {f['frage']}", f"*Anlass: {f['anlass']} – Suchfenster: "
                   f"{FENSTER[f['fenster']][0]}*", ""]
        eigene = [a for a in g["aussagen"] if a["frage"] == f["id"]]
        if not eigene:
            zeilen.append("Keine Aussage gefunden.")
        for a in eigene:
            zeilen.append(f"- **{STATUS_TEXT[a['status']]}** ({a['id']}): {a['text']}"
                          + (f" – fehlt: {a['fehlt']}" if a["fehlt"] else ""))
            for b in a["belege"]:
                wo = b.get("url") or f"{b['datei']}, S. {b.get('seite')}"
                zeilen.append(f"  - „{b['zitat']}“ ({wo}; {b['pruefung']['vermerk']})")
        for o in g["offen"]:
            if o.get("frage") == f["id"]:
                zeilen.append(f"- Offen laut Gegenprüfung: {o.get('warum', '')}")
    if g["widersprueche"]:
        zeilen += ["", "## Widersprüche", ""]
        zeilen += [f"- {', '.join(w.get('ids', []))}: {w.get('worum', '')}" for w in g["widersprueche"]]
    if g["luecken"]:
        zeilen += ["", "## Lücken (nicht gefunden)", ""]
        zeilen += [f"- {fenster_titel(x['fenster'])}: {x['text']}" for x in g["luecken"]]
    zeilen += ["", "## Quellen", ""]
    for q in g["quellen"]:
        autoren = ", ".join(q.get("autoren", [])) or "o. A."
        doi = f" DOI {q['doi']}." if q.get("doi") else ""
        marke = "" if q["zitierfaehig"] else " (nicht zitierfähig)"
        zeilen.append(f"- {autoren} ({q.get('jahr') or 'o. J.'}): {q['titel']}.{doi} {q['url']} – "
                      f"{q['pruefung']['vermerk']}{marke}")
    return "\n".join(zeilen) + "\n"


# --- Ablauf ---

def _fragen_text(fragen: list[dict]) -> str:
    return "\n".join(f"- {f['id']} ({f['fenster']}): {f['frage']} [Anlass: {f['anlass']}]" for f in fragen)


def durchfuehren(hier: Path, ordner: Path, auftrag: dict, laufen, seitentext, metadaten,
                 grenze_usd: float = GRENZE_USD) -> Ergebnis:
    """Ganze Recherche für einen Exposé-Auftrag (setzt fort, was in ordner/recherche schon fertig ist).

    laufen wie agentkit.claude_lauf.laufen; Kontingent- und Lauffehler gehen an den Aufrufer (Auftrag bleibt
    offen, der nächste Anlauf setzt fort). Ein Suchfenster, das scheitert, hält die anderen nicht auf.
    """
    r = ordner / ORDNER
    r.mkdir(parents=True, exist_ok=True)
    rel = lambda p: p.relative_to(hier)  # noqa: E731
    stand_pfad = r / "stand.json"
    stand = json.loads(stand_pfad.read_text()) if stand_pfad.exists() else {"usd": 0.0, "fertig": []}
    erg = Ergebnis()

    def lauf(prompt: str, sitzung: str | None = None):
        e = laufen("uni", hier, prompt, art="anspruchsvoll", auftrag_id=auftrag["id"], sitzung_fortsetzen=sitzung)
        stand["usd"] = round(stand["usd"] + (e.usd or 0), 4)
        _schreib(stand_pfad, stand)
        return e

    def fertig(name: str):
        stand["fertig"].append(name)
        _schreib(stand_pfad, stand)

    # 1. Eckpunkte
    eck_pfad = r / "eckpunkte.json"
    if "eckpunkte" not in stand["fertig"]:
        e = lauf(PROMPT_ECKPUNKTE.format(text=auftrag["text"], pfad=rel(eck_pfad), format=FORMAT_ECKPUNKTE))
        fehler = _datei_fehler(eck_pfad, eckpunkte_pruefen)
        if fehler and e.sitzung:
            lauf(PROMPT_DATEI_NACHBESSERN.format(pfad=rel(eck_pfad), fehler="\n".join(fehler)), e.sitzung)
            fehler = _datei_fehler(eck_pfad, eckpunkte_pruefen)
        if fehler:
            raise RechercheFehler("Recherchefragen ungültig:\n" + "\n".join(f"- {f}" for f in fehler))
        fertig("eckpunkte")
    eck = _lies(eck_pfad)

    # 2. Suchfenster
    geprueft_fenster = {}
    for name, (titel, hinweis) in FENSTER.items():
        fragen = [f for f in eck["fragen"] if f["fenster"] == name]
        if not fragen:
            continue
        ziel = r / f"{name}-geprueft.json"
        if name in stand["fertig"]:
            geprueft_fenster[name] = _lies(ziel)
            continue
        if stand["usd"] + LAUF_USD + RESERVE_USD > grenze_usd:
            erg.zeilen.append(f"Suchfenster {titel} nicht gestartet: Kostengrenze {grenze_usd:.0f} USD "
                              f"(bisher {stand['usd']:.2f} USD).")
            continue
        prompt = PROMPT_SUCHE.format(thema=eck["thema"], titel=titel, hinweis=hinweis, fragen=_fragen_text(fragen),
                                     alle=_fragen_text(eck["fragen"]), regeln=KURZREGELN,
                                     pfad=rel(r / f"{name}.json"), format=FORMAT_FENSTER)
        try:
            geprueft_fenster[name] = _fenster(hier, r, name, prompt, {f["id"] for f in fragen}, lauf, seitentext,
                                              metadaten)
        except RechercheFehler as f:
            erg.zeilen.append(f"Suchfenster {titel} gescheitert: {f}")
            continue
        _schreib(ziel, geprueft_fenster[name])
        fertig(name)

    # 2b. Systematische Literatursuche aus Jans Scopus-Export (nur, wenn er vorliegt)
    export = None
    try:
        export = scopus.einlesen(r / scopus.ORDNER) if (r / scopus.ORDNER).is_dir() else None
    except scopus.ScopusFehler as f:
        erg.zeilen.append(f"Scopus-Export nicht lesbar, Recherche ohne Scopus: {f}")
    if export:
        _scopus(hier, r, eck, export, stand, geprueft_fenster, erg, lauf, fertig, seitentext, metadaten, grenze_usd)
    if not geprueft_fenster:
        raise RechercheFehler("kein Suchfenster mit Ergebnis\n" + "\n".join(erg.zeilen))

    # 3. Gegenprüfung (neue Sitzung)
    zur_pruefung = zur_gegenpruefung(geprueft_fenster)
    gegen_pfad = r / "gegenpruefung.json"
    gegen = None
    if "gegenpruefung" in stand["fertig"]:
        gegen = _lies(gegen_pfad)
    elif zur_pruefung:
        ids = {a["id"] for a in zur_pruefung}
        aussagen = "\n".join(f"- {a['id']}: {a['text']}\n" + "\n".join(f"    „{z}“ ({wo})" for wo, z in a["zitate"])
                             for a in zur_pruefung)
        e = lauf(PROMPT_GEGEN.format(thema=eck["thema"], fragen=_fragen_text(eck["fragen"]), aussagen=aussagen,
                                     pfad=rel(gegen_pfad)))
        pruef = lambda d: gegen_pruefen(d, ids)  # noqa: E731
        fehler = _datei_fehler(gegen_pfad, pruef)
        if fehler and e.sitzung:
            lauf(PROMPT_DATEI_NACHBESSERN.format(pfad=rel(gegen_pfad), fehler="\n".join(fehler)), e.sitzung)
            fehler = _datei_fehler(gegen_pfad, pruef)
        if fehler:
            erg.zeilen.append("Gegenprüfung ungültig, belegte Aussagen gelten nur als teilweise belegt: "
                              + "; ".join(fehler[:5]))
        else:
            gegen = _lies(gegen_pfad)
            fertig("gegenpruefung")

    # 4. Zusammenführen
    g = zusammenfuehren(eck, geprueft_fenster, gegen, scopus.beschreibung(export) if export else None)
    erg.geprueft, erg.bericht, erg.usd = r / "geprueft.json", r / "Recherchebericht.md", stand["usd"]
    _schreib(erg.geprueft, g)
    erg.bericht.write_text(bericht(g, stand["usd"], export), encoding="utf-8")
    z = g["zahlen"]
    erg.zeilen.insert(0, f"Recherche: {len(g['fragen'])} Fragen, {len(g['aussagen'])} Aussagen ({z['gesichert']} "
                         f"gesichert, {z['teilweise']} teilweise, {z['verworfen']} verworfen, {z['unbelegt']} "
                         f"unbelegt), {z['quellen_zitierfaehig']} zitierfähige Quellen, {stand['usd']:.2f} USD.")
    return erg


def scopus_nachtrag(ordner: Path, neu: bool = False) -> bool:
    """Wartet ein Scopus-Export der Kette auf Auswertung? Nur nach einer ersten Recherche (sonst wertet sie ihn
    ohnehin aus). neu: gerade neue Dateien abgelegt, dann wird er auch nach einer früheren Auswertung neu bewertet."""
    r = ordner / ORDNER
    stand_pfad = r / "stand.json"
    if not stand_pfad.exists() or not any((r / scopus.ORDNER).glob("*.csv")):
        return False
    stand = json.loads(stand_pfad.read_text())
    if neu and SCOPUS in stand["fertig"]:
        stand["fertig"].remove(SCOPUS)
        _schreib(stand_pfad, stand)
    return SCOPUS not in stand["fertig"]


def _datei_fehler(pfad: Path, pruefen) -> list[str]:
    try:
        return pruefen(_lies(pfad))
    except RechercheFehler as f:
        return [str(f)]


def _scopus(hier, r, eck, export, stand, geprueft_fenster, erg, lauf, fertig, seitentext, metadaten, grenze_usd):
    """Suchfenster aus dem Scopus-Export. Kommt es nach der Gegenprüfung dazu, wird sie wiederholt (Nachtrag)."""
    ziel = r / f"{SCOPUS}-geprueft.json"
    if SCOPUS in stand["fertig"]:
        geprueft_fenster[SCOPUS] = _lies(ziel)
        return
    fragen = [f for f in eck["fragen"] if f["fenster"] in SCOPUS_FUER]
    if not fragen:
        erg.zeilen.append("Scopus-Export nicht ausgewertet: keine Fragen zu Literatur, Methoden oder Daten.")
        return
    if stand["usd"] + LAUF_USD + RESERVE_USD > grenze_usd:
        erg.zeilen.append(f"{SCOPUS_TITEL} nicht gestartet: Kostengrenze {grenze_usd:.0f} USD "
                          f"(bisher {stand['usd']:.2f} USD).")
        return
    kandidaten = r / f"{SCOPUS}.md"
    kandidaten.write_text(scopus.kandidaten_md(export), encoding="utf-8")
    bisher = [r / f"{n}-geprueft.json" for n in SCOPUS_FUER if (r / f"{n}-geprueft.json").exists()]
    prompt = PROMPT_SCOPUS.format(
        thema=eck["thema"], titel=SCOPUS_TITEL, kandidaten=kandidaten.relative_to(hier), anzahl=len(export.treffer),
        fragen=_fragen_text(fragen), alle=_fragen_text(eck["fragen"]),
        bisher=", ".join(str(p.relative_to(hier)) for p in bisher) or "noch nichts", regeln=KURZREGELN,
        pfad=(r / f"{SCOPUS}.json").relative_to(hier), format=FORMAT_FENSTER)
    try:
        d = _fenster(hier, r, SCOPUS, prompt, {f["id"] for f in fragen}, lauf, seitentext, metadaten,
                     scopus.abstracts(export))
    except RechercheFehler as f:
        erg.zeilen.append(f"{SCOPUS_TITEL} gescheitert: {f}")
        return
    geprueft_fenster[SCOPUS] = d
    _schreib(ziel, d)
    if "gegenpruefung" in stand["fertig"]:
        stand["fertig"].remove("gegenpruefung")
    fertig(SCOPUS)


def _fenster(hier, r, name, prompt, ids, lauf, seitentext, metadaten, abstracts=None) -> dict:
    pfad = r / f"{name}.json"
    rel = pfad.relative_to(hier)
    e = lauf(prompt)
    sitzung = e.sitzung
    for _ in range(DURCHGAENGE - 1):
        if not sitzung or not pfad.exists():
            break
        sitzung = lauf(PROMPT_WEITER.format(pfad=rel, regeln=KURZREGELN), sitzung).sitzung or sitzung
    fehler = _datei_fehler(pfad, lambda d: fenster_pruefen(d, ids))
    if not fehler:
        d = fenster_belege_pruefen(_lies(pfad), hier, seitentext, metadaten, abstracts)
        fehler = durchgefallene(d)
        if not fehler:
            return d
    if not sitzung:
        raise RechercheFehler("; ".join(fehler[:5]))
    lauf(PROMPT_NACHBESSERN.format(pfad=rel, fehler="\n".join(f"- {f}" for f in fehler)), sitzung)
    fehler = _datei_fehler(pfad, lambda d: fenster_pruefen(d, ids))
    if fehler:
        raise RechercheFehler("; ".join(fehler[:5]))
    return fenster_belege_pruefen(_lies(pfad), hier, seitentext, metadaten, abstracts)  # Durchgefallenes bleibt vermerkt


# --- Netz (dünn) ---

class DomainNichtErlaubt(abruf.AbrufFehler):
    pass


def _allowlist(url: str, domains: list[str] | None) -> list[str]:
    """Ohne Eintrag in [webfetch] (None) gilt wie bei WebFetch: jede https-Adresse."""
    host = urlsplit(url).hostname or ""
    if domains is None:
        return [host]
    if not abruf.host_erlaubt(host, domains):
        raise DomainNichtErlaubt(f"{host} nicht auf der Liste")
    return domains


def seitentext_laden(domains: list[str] | None, cache_dir: Path):
    """seitentext(url) für beleg_pruefen: HTML als Text, PDF über agentkit.textfassung."""
    def seitentext(url: str) -> str:
        erg = abruf.laden(url, _allowlist(url, domains), cache_dir)
        art = (erg.meta.get("content_type") or "").lower()
        if "pdf" in art or erg.inhalt[:5] == b"%PDF-":
            with tempfile.TemporaryDirectory() as tmp:
                datei = Path(tmp) / "seite.pdf"
                datei.write_bytes(erg.inhalt)
                try:
                    return textfassung.als_text(datei) or ""
                except Exception as f:  # noqa: BLE001 – kaputte PDFs: Beleg fällt durch, Lauf geht weiter
                    raise abruf.AbrufFehler(f"PDF nicht lesbar: {f}") from None
        return erg.text_ohne_html()
    return seitentext


def crossref_laden(domains: list[str] | None, cache_dir: Path):
    """metadaten(doi) -> {titel, jahr, nachnamen} aus der Crossref-API."""
    def metadaten(doi: str) -> dict:
        url = f"https://api.crossref.org/works/{quote(doi, safe='/')}"
        erg = abruf.laden(url, _allowlist(url, domains), cache_dir)
        try:
            m = json.loads(erg.text())["message"]
        except (ValueError, KeyError) as f:
            raise abruf.AbrufFehler(f"Antwort von Crossref unlesbar: {f}") from None
        teile = (m.get("issued") or m.get("published") or {}).get("date-parts") or [[None]]
        return {"titel": " ".join(m.get("title") or []), "jahr": teile[0][0],
                "nachnamen": [a.get("family", "") for a in m.get("author", []) if a.get("family")]}
    return metadaten
