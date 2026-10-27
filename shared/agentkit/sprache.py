"""Sprachregel der Zentralen prüfbar machen (docs/sprache/sprachregel.md, von Jan angenommen 27.10.2026).

- jargon(text, fuer): Treffer aus dem Glossar („nie sagen“) und Technik: IDs, Pfade, Dateinamen, Beträge, Modellnamen,
  rohe Fehlertexte, Bezeichner. fuer = LIA oder JAN (manche Wörter sind nur für Lia tabu).
- lesbarkeit(text): 1. Wiener Sachtextformel (Schulstufe, niedriger = leichter), längster Satz, sichtbare Zeichen.
  Gemessen wird erst nach dem Entfernen von HTML, aufklappbaren Teilen, URLs, Pfaden, Zahlen und Zitaten der Person
  („…“); Beschriftungen wie „Neues Material“ zählen nur für die Satzlänge. Unter MIN_WOERTER Wörtern ist die Formel
  zu ungenau: dann gilt nur die Satzlänge.
- pruefen(text, fuer, ausnahmen=()): beides gegen GRENZEN, als Liste von Befunden. ausnahmen: Arten, die in dieser
  Nachricht erlaubt sind (z. B. "betrag" unter Verbrauch, "pfad" beim Befehl unter /pc) oder "laenge" (Entwürfe:
  freigegeben wird genau der angezeigte Text, er wird nicht gekürzt).
- log_text(befunde): Befunde ohne Inhalt der Nachricht (nur Art und Glossarwort), für das Log beider Zentralen.

Silben werden geschätzt (Vokalgruppen, Doppellaute als eine Silbe). Reine Logik ohne Netz.
"""

import re
from dataclasses import dataclass
from html import unescape

LIA, JAN = "lia", "jan"
MIN_WOERTER = 10


@dataclass(frozen=True)
class Grenzen:
    wstf: float
    satz_woerter: int
    zeichen: int


GRENZEN = {LIA: Grenzen(6, 15, 600), JAN: Grenzen(8, 20, 800)}


@dataclass(frozen=True)
class Regel:
    art: str  # glossar, id, pfad, datei, betrag, modell, fehlertext, bezeichner
    wort: str  # Name für Log und Befund (nie der gefundene Text selbst)
    muster: re.Pattern
    stattdessen: str
    fuer: tuple[str, ...] = (LIA, JAN)


def _r(muster: str, flags: int = 0) -> re.Pattern:
    return re.compile(muster, flags)


GROSS_KLEIN = re.IGNORECASE
AGENTEN_KLEIN = r"(?<![/\w])(uni|dokumente|recherche|unterricht|examen|feedback|sicherung|posteingang|einkauf)\b"

REGELN = [
    # Glossar (docs/sprache/sprachregel.md). Zu allgemeine Wörter (Fehler, Notiz, Modell, Lauf im Sinn von Verlauf)
    # stehen nur in der Sprachregel, nicht hier.
    Regel("glossar", "Agent", _r(r"\bAgent(en)?\b"), "„ich“", (LIA,)),
    Regel("glossar", "der Agent", _r(r"\b([Dd]er|[Dd]en|[Dd]em|[Dd]es) Agent(en)?\b"), "Name des Agenten („Uni“)", (JAN,)),
    Regel("glossar", "Agentenname klein", _r(AGENTEN_KLEIN), "Lia: „ich“, Jan: „Uni“, „Recherche“"),
    Regel("glossar", "Dienst", _r(r"\bDienst(e|es)?\b"), "„ich“", (LIA,)),
    Regel("glossar", "Auftrag", _r(r"\bAuftr(a|ä)g(e|es|en)?\b"), "„Anfrage“, „Wunsch“", (LIA,)),
    Regel("glossar", "Kontingent", _r(r"Kontingent", GROSS_KLEIN), "„Rechenzeit ist aufgebraucht, weiter ab 14 Uhr“"),
    Regel("glossar", "Limit", _r(r"\bLimits?\b"), "„Rechenzeit ist aufgebraucht“"),
    Regel("glossar", "Stufe", _r(r"\bStufen?\b"), "„Rechenzeit“"),
    Regel("glossar", "5h/7d", _r(r"\b(5\s?h|7\s?d)\b"), "„heute“, „diese Woche“"),
    Regel("glossar", "Reset", _r(r"\bReset\b", GROSS_KLEIN), "„wieder frei ab …“"),
    Regel("glossar", "Lauf", _r(r"\b(Zeitl|L)äufen?\b|\b\d+ Lauf\b|\bZeitlauf\b"), "„hat 3-mal gearbeitet“"),
    Regel("glossar", "Tokens", _r(r"\bTokens?\b", GROSS_KLEIN), "weglassen"),
    Regel("glossar", "Nachbesserung", _r(r"Nachbesserung", GROSS_KLEIN), "„überarbeitete Fassung“"),
    Regel("glossar", "Regel (dauerhaft)", _r(r"Regel \(dauerhaft\)|^Art: ", re.MULTILINE), "„Ab jetzt gilt: …“"),
    Regel("glossar", "Programmänderung", _r(r"Programmänderung|\bCode\b|\bOberfläche\b"),
          "„Das kann ich noch nicht. Jan baut es ein.“", (LIA,)),
    Regel("glossar", "fehlgeschlagen", _r(r"fehlgeschlagen", GROSS_KLEIN), "„hat nicht geklappt“ + Grund in Worten"),
    Regel("glossar", "Log", _r(r"\bLogs?\b"), "Lia: nichts, Jan: „Einzelheiten am PC“"),
    Regel("glossar", "Commit", _r(r"\b(Commit|committet|commiten|Hash)\b", GROSS_KLEIN), "weglassen"),
    Regel("glossar", "Version", _r(r"\bVersion [0-9a-f]{7,}\b"), "weglassen"),
    Regel("glossar", "USD", _r(r"\bUSD\b|\$\s?\d"), "Lia: nie, Jan: nur unter Verbrauch"),
    Regel("glossar", "OCR", _r(r"\bOCR\b|\bSchwelle\b|\bdurchgefallen\b|Kontrollrunde|Behauptungsliste|\(\d+\. Runde\)"),
          "„geprüft“, „31 von 49 Aussagen haben einen Beleg“"),
    Regel("glossar", "(en)", _r(r"\w\((en|e|n|s)\)"), "Einzahl und Mehrzahl ausschreiben"),
    Regel("glossar", "Bot", _r(r"\bBots?\b"), "weglassen"),
    Regel("glossar", "MB", _r(r"\b\d+\s?(MB|GB|KB)\b"), "„zu groß für Telegram“"),
    Regel("glossar", "läuft noch nicht", _r(r"läuft noch nicht"), "„ist noch nicht eingerichtet“", (JAN,)),
    Regel("glossar", "Zentrale", _r(r"\bZentrale\b|\bPanel\b"), "„Menü“", (LIA,)),
    Regel("glossar", "Sitzung", _r(r"\bSitzung(en)?\b"), "weglassen", (LIA,)),
    # Technik
    Regel("id", "ID", _r(r"\b\d{8}-\d{6}(-[a-z]+-[0-9a-f]{6})?\b"), "weglassen"),
    Regel("id", "Hash", _r(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b"), "weglassen"),
    Regel("pfad", "Pfad", _r(r"(?<![\w:/])~?/[\w.\-]+(/[\w.\-]+)+|\b[a-z_]+/[a-z_\-]+/"), "„am PC“ oder weglassen"),
    Regel("datei", "Dateiname", _r(r"[\w\-]\.(pdf|docx?|pptx?|xlsx?|md|json|toml|txt|log|py|zip|ics|mp4|csv|html|"
                                  r"service|timer|env|sh|btl|3d)\b", GROSS_KLEIN), "sagen, was es ist („die PDF“)"),
    Regel("betrag", "Betrag", _r(r"\d+([.,]\d+)?\s?(USD|EUR|Euro|€)"), "Lia: nie, Jan: nur unter Verbrauch"),
    Regel("modell", "Modellname", _r(r"\b(Sonnet|Opus|Haiku|claude-(opus|sonnet|haiku|fable)[\w.\-]*|GPT|LLM)\b"), "weglassen"),
    Regel("fehlertext", "Fehlertext", _r(r"\b[A-Z][a-z]+(Error|Exception|Fehler)\b|\bErrno\b|Traceback|"
                                          r"\b(timed out|failed|Connection|LOGIN)\b"), "Grund in Worten"),
    Regel("bezeichner", "Bezeichner", _r(r"\b[a-z]+_[a-z_]+\b|(?<![\w-])--[a-z]|\[\s*\"|\{\""), "in Worten"),
]

URL = re.compile(r"https?://\S+|\b[\w.\-]+@[\w\-]+\.[\w.\-]+")
ZITAT = re.compile(r"„[^“\n]*“|\"[^\"\n]*\"")
AUFKLAPPBAR = re.compile(r"<blockquote expandable>.*?</blockquote>", re.DOTALL)
WORT = re.compile(r"[A-Za-zÄÖÜäöüß]+")
DOPPELLAUT = re.compile(r"ei|ie|au|eu|äu|ai|ee|aa|oo", re.IGNORECASE)
VOKALE = re.compile(r"[aeiouäöüy]+", re.IGNORECASE)


@dataclass(frozen=True)
class Treffer:
    art: str
    wort: str
    stattdessen: str


@dataclass(frozen=True)
class Lesbarkeit:
    wstf: float | None  # None: zu wenige Wörter
    laengster_satz: int
    woerter: int
    zeichen: int


def sichtbar(html: str, mit_aufklappbarem: bool = True) -> str:
    """Text, wie Telegram ihn zeigt (ohne Tags). mit_aufklappbarem=False lässt <blockquote expandable> weg."""
    if not mit_aufklappbarem:
        html = AUFKLAPPBAR.sub("", html or "")
    return unescape(re.sub(r"<[^>]+>", "", html or ""))


def jargon(text: str, fuer: str, ausnahmen: tuple[str, ...] = ()) -> list[Treffer]:
    """Glossar- und Technik-Treffer, je Regel höchstens einmal. URLs und Mailadressen zählen nicht."""
    rein = URL.sub(" ", sichtbar(text))
    return [Treffer(r.art, r.wort, r.stattdessen) for r in REGELN
            if fuer in r.fuer and r.art not in ausnahmen and r.muster.search(rein)]


def silben(wort: str) -> int:
    return max(1, len(VOKALE.findall(DOPPELLAUT.sub("a", wort))))


def _fuer_messung(text: str) -> str:
    rein = URL.sub(" ", sichtbar(text, mit_aufklappbarem=False))
    for r in REGELN:
        if r.art in ("pfad", "datei", "id"):
            rein = r.muster.sub(" ", rein)
    rein = ZITAT.sub(" ", rein)  # Worte der Person selbst (ihre Anfrage, ihr Feedback)
    rein = re.sub(r"\b(z|d|u|v|o|s|bzw|vgl|ggf|ca|Nr|Abs|Bd)\. ?(B|h|a|ä|Ä)?\.?", " ", rein)  # Abkürzungen
    return re.sub(r"\d+([.,:]\d+)*\.?", " ", rein)


def ist_fliesstext(zeile: str) -> bool:
    """Satz statt Beschriftung: endet mit . ! ? … oder hat mehr als 4 Wörter ("Entwürfe offen: 1" zählt nicht)."""
    return bool(re.search(r"[.!?…]\s*$", zeile)) or len(WORT.findall(zeile)) > 4


def lesbarkeit(text: str) -> Lesbarkeit:
    """1. Wiener Sachtextformel: 0,1935·MS + 0,1672·SL + 0,1297·IW − 0,0327·ES − 0,875.

    MS: % Wörter mit 3+ Silben, SL: Wörter je Satz, IW: % Wörter mit mehr als 6 Buchstaben, ES: % einsilbige Wörter.
    Satzenden: . ! ? und Zeilenumbrüche (jeder Aufzählungspunkt ist ein Satz). Die Formel ist für Fließtext gemacht:
    Beschriftungen (Überschriften, Menüzeilen) und Zitate der Person zählen nicht, die Satzlänge gilt für alle Zeilen.
    """
    zeilen = _fuer_messung(text).split("\n")
    saetze = [WORT.findall(s) for z in zeilen if ist_fliesstext(z) for s in re.split(r"[.!?;]+", z)]
    saetze = [s for s in saetze if s]
    woerter = [w for s in saetze for w in s]
    zeichen = len(sichtbar(text, mit_aufklappbarem=False).strip())
    laengster = max((len(WORT.findall(s)) for z in zeilen for s in re.split(r"[.!?;]+", z)), default=0)
    if len(woerter) < MIN_WOERTER:
        return Lesbarkeit(None, laengster, len(woerter), zeichen)
    n, s = len(woerter), [silben(w) for w in woerter]
    ms, iw, es = (100 * sum(x) / n for x in ([z >= 3 for z in s], [len(w) > 6 for w in woerter], [z == 1 for z in s]))
    wstf = 0.1935 * ms + 0.1672 * (n / len(saetze)) + 0.1297 * iw - 0.0327 * es - 0.875
    return Lesbarkeit(round(wstf, 1), laengster, n, zeichen)


def pruefen(text: str, fuer: str, ausnahmen: tuple[str, ...] = ()) -> list[str]:
    """Befunde gegen die Sprachregel, leer = in Ordnung. Ohne den Inhalt der Nachricht, nur Art und Wort."""
    befunde = [f"{t.art}: {t.wort} (stattdessen {t.stattdessen})" for t in jargon(text, fuer, ausnahmen)]
    if "laenge" in ausnahmen:
        return befunde
    g, m = GRENZEN[fuer], lesbarkeit(text)
    if m.wstf is not None and m.wstf > g.wstf:
        befunde.append(f"lesbarkeit: WSTF {m.wstf} über {g.wstf}")
    if m.laengster_satz > g.satz_woerter:
        befunde.append(f"satz: {m.laengster_satz} Wörter, höchstens {g.satz_woerter}")
    if m.zeichen > g.zeichen:
        befunde.append(f"laenge: {m.zeichen} Zeichen, höchstens {g.zeichen}")
    return befunde


def log_text(befunde: list[str]) -> str:
    """Kurzform fürs Log: nur die Art bzw. das Wort vor der Klammer (Logs enthalten keine Inhalte)."""
    return "; ".join(b.split(" (stattdessen", 1)[0] for b in befunde)
