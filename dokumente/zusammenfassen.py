"""Zusammenfassung bauen: Claude beschreibt, der Renderer baut, Claude kontrolliert, Python prüft den Bericht.

Ablauf (erstellen):
1. Claude schreibt <ordner>/beschreibung.json im Renderer-Format (Art "zusammenfassung").
2. Python baut daraus docx und PDF. Kaputtes JSON oder BeschreibungUngueltig geht in derselben Sitzung an
   Claude zurück, höchstens MAX_BAU_RUNDEN Versuche je Bau.
3. Claude bekommt Kontrolltext und Vorschaubilder und schreibt <ordner>/kontrolle.json (BERICHT_FORMAT).
   Python prüft den Bericht gegen die Behauptungsliste (bericht_pruefen). Erst wenn er stimmt und Claude die
   Beschreibung dabei nicht mehr geändert hat, ist die Zusammenfassung fertig. Sonst neu bauen und neu prüfen,
   höchstens MAX_KONTROLL_RUNDEN Kontrollen.

Behauptungsliste: Datei behauptungen.json im Auftrag (uni legt sie bei), eine Liste aus
{"nr": 1, "aussage": "...", "quellen": [{"art": "transkript", "stelle": "4"}], "kennzeichnung": "muendlich"}.
quellen und kennzeichnung wie im Renderer (FORMAT.md) und optional. Ohne Liste prüft Claude nur gegen die Dateien.

Claude und der Renderer werden als Funktionen übergeben, damit sich der Ablauf ohne Netz testen lässt.
"""

import hashlib
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

MAX_BAU_RUNDEN = 3
MAX_KONTROLL_RUNDEN = 3
BEHAUPTUNGEN = "behauptungen.json"
NICHT_UNTERSTUETZT = "NICHT_UNTERSTUETZT"
BERICHT_FORMAT = """{"abgedeckt": [1, 2], "fehlt": [3], "erfunden": ["Aussage, die in keiner Quelle steht"],
 "darstellung": ["Seite 2: Tabelle läuft über den Rand"]}"""


class ZusammenfassungFehler(Exception):
    """Die Zusammenfassung ist nicht fertig geworden. Der Text geht an Jan."""


class BehauptungslisteUngueltig(ZusammenfassungFehler):
    pass


class BeschreibungKaputt(Exception):
    """beschreibung.json fehlt oder ist kein JSON. Geht wie BeschreibungUngueltig an Claude zurück."""


@dataclass
class Fertig:
    docx: Path
    pdf: Path
    titel: str
    seiten: int
    kontrollen: int
    antwort: str  # Claudes letzte Antwort, die Kurzfassung für Jan
    sitzung: str | None
    hinweise: list[str] = field(default_factory=list)


# Reine Logik -------------------------------------------------------------------

def behauptungsliste_finden(dateien: list[str]) -> str | None:
    """Pfad der Behauptungsliste unter den Dateien eines Auftrags (Name behauptungen.json, auch behauptungen-2.json)."""
    for d in dateien:
        name = Path(d).name.lower()
        if name == BEHAUPTUNGEN or re.fullmatch(r"behauptungen-\d+\.json", name):
            return d
    return None


def behauptungen_lesen(text: str) -> list[dict]:
    """Prüft die Liste von uni. Fehler hier liegen beim Absender, nicht bei Claude."""
    try:
        liste = json.loads(text)
    except json.JSONDecodeError as e:
        raise BehauptungslisteUngueltig(f"{BEHAUPTUNGEN} ist kein gültiges JSON: {e}") from None
    if not isinstance(liste, list) or not liste:
        raise BehauptungslisteUngueltig(f"{BEHAUPTUNGEN} muss eine nicht leere Liste sein")
    gesehen = set()
    for i, b in enumerate(liste):
        if not isinstance(b, dict):
            raise BehauptungslisteUngueltig(f"{BEHAUPTUNGEN}[{i}] ist kein Objekt")
        nr = b.get("nr")
        if not isinstance(nr, int) or isinstance(nr, bool) or nr in gesehen:
            raise BehauptungslisteUngueltig(f"{BEHAUPTUNGEN}[{i}].nr muss eine eindeutige ganze Zahl sein, ist {nr!r}")
        if not isinstance(b.get("aussage"), str) or not b["aussage"].strip():
            raise BehauptungslisteUngueltig(f"{BEHAUPTUNGEN}[{i}].aussage fehlt")
        gesehen.add(nr)
    return liste


def bericht_pruefen(text: str | None, nummern: list[int]) -> list[str]:
    """Probleme im Kontrollbericht von Claude. Leer heißt: nichts fehlt, nichts erfunden, Darstellung in Ordnung."""
    if text is None:
        return ["kontrolle.json fehlt"]
    try:
        b = json.loads(text)
    except json.JSONDecodeError as e:
        return [f"kontrolle.json ist kein gültiges JSON: {e}"]
    if not isinstance(b, dict):
        return ["kontrolle.json muss ein Objekt sein"]
    probleme = []
    unbekannt = set(b) - {"abgedeckt", "fehlt", "erfunden", "darstellung"}
    if unbekannt:
        probleme.append(f"Unbekannte Felder: {', '.join(sorted(unbekannt))}")
    listen = {}
    for name in ("abgedeckt", "fehlt", "erfunden", "darstellung"):
        wert = b.get(name, [])
        if not isinstance(wert, list):
            probleme.append(f"{name} muss eine Liste sein")
            wert = []
        listen[name] = wert
    for name in ("abgedeckt", "fehlt"):
        falsch = [n for n in listen[name] if n not in nummern]
        if falsch:
            probleme.append(f"{name}: unbekannte Nummern {falsch}")
    doppelt = sorted(set(listen["abgedeckt"]) & set(listen["fehlt"]), key=str)
    if doppelt:
        probleme.append(f"Nummern zugleich abgedeckt und fehlend: {doppelt}")
    offen = [n for n in nummern if n not in listen["abgedeckt"] and n not in listen["fehlt"]]
    if offen:
        probleme.append(f"Nicht beurteilt: Behauptungen {offen}")
    if listen["fehlt"]:
        probleme.append(f"Fehlende Behauptungen: {listen['fehlt']}")
    probleme += [f"Dazuerfunden: {t}" for t in listen["erfunden"]]
    probleme += [f"Darstellung: {t}" for t in listen["darstellung"]]
    return probleme


def beschreibung_lesen(text: str | None) -> dict:
    """beschreibung.json als dict. BeschreibungKaputt mit einem Text, den Claude beheben kann."""
    if text is None:
        raise BeschreibungKaputt("beschreibung.json fehlt")
    try:
        b = json.loads(text)
    except json.JSONDecodeError as e:
        raise BeschreibungKaputt(f"beschreibung.json ist kein gültiges JSON: {e}") from None
    if not isinstance(b, dict) or b.get("art") != "zusammenfassung":
        raise BeschreibungKaputt('beschreibung.json muss ein Objekt mit "art": "zusammenfassung" sein')
    return b


def dateiname(titel: str) -> str:
    """Dateiname ohne Endung aus dem Titel: Umlaute umschreiben, nur Buchstaben, Ziffern und Bindestriche."""
    t = titel.lower()
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(alt, neu)
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60].strip("-")
    return t or "zusammenfassung"


def format_abschnitt(format_md: str) -> str:
    """Aus FORMAT.md des Renderers nur, was Claude für eine Zusammenfassung braucht."""
    teile = re.split(r"^## ", format_md, flags=re.M)
    behalten = [t for t in teile[1:] if t.startswith(("Allgemein", "Zusammenfassung"))]
    if len(behalten) != 2:
        raise ValueError("FORMAT.md: Abschnitte 'Allgemein' und 'Zusammenfassung' nicht gefunden")
    return teile[0] + "".join("## " + t for t in behalten)


def ursprung(a: dict, holen) -> dict:
    """Erster Auftrag einer Antwortkette (bezug -> bezug -> ...). Fehlt ein Glied, der letzte gefundene."""
    gesehen = {a["id"]}
    while a.get("bezug") and a["bezug"] not in gesehen:
        try:
            a = holen(a["bezug"])
        except Exception:  # noqa: BLE001 – Kette unvollständig, dann ab hier
            break
        gesehen.add(a["id"])
    return a


# Texte für Claude ---------------------------------------------------------------

KONTEXT = """Du bist der Dokumente-Agent von Jan. Er studiert Holzingenieurwesen (M.Sc.) an der HNE Eberswalde.
Du schreibst Zusammenfassungen von Vorlesungen, die Jan an Kommilitonen weitergibt. Sie müssen stimmen:
Schreib nur, was in den Dateien des Auftrags steht. Erfinde nichts, auch keine Beispiele, Zahlen oder Normen.
Belege jede inhaltliche Aussage mit quellen. Übernimm Kennzeichnungen (unsicher, muendlich) aus der Vorlage.
Deutsch, klar, für Studierende, die nicht in der Vorlesung waren.

Du schreibst kein Dokument, sondern eine JSON-Beschreibung, aus der Python die Datei baut. Format:

{format}"""

PROMPT_START = KONTEXT + """

Auftrag{herkunft}:
{text}

{behauptungen}Lies die Dateien des Auftrags (zu Word, PowerPoint und Excel gibt es <datei>.txt daneben, zu PDFs
<datei>.txt und Seitenbilder in <datei>-seiten/). Schreib dann die Beschreibung nach {ordner}/beschreibung.json.
Ändere keine anderen Dateien.

Ist der Auftrag keine Zusammenfassung von Lehrmaterial, schreib keine Datei und antworte nur:
""" + NICHT_UNTERSTUETZT + """: <ein Satz, warum>
Sonst antworte nur: fertig"""

PROMPT_ANTWORT = """Jan antwortet auf die fertige Zusammenfassung:
{text}

Pass die Beschreibung entsprechend an und schreib sie vollständig nach {ordner}/beschreibung.json.
{behauptungen}Antworte nur: fertig"""

HINWEIS_BEHAUPTUNGEN = """Verbindlich ist die Behauptungsliste {pfad}: Jede Behauptung muss in der Zusammenfassung
vorkommen, mit ihren Quellen und ihrer Kennzeichnung. Was darüber hinausgeht, muss ebenso in den Dateien belegt sein.

"""

PROMPT_KORREKTUR = """Python konnte die Beschreibung nicht bauen:
{fehler}

Korrigiere alle genannten Stellen und schreib die vollständige Beschreibung neu nach {ordner}/beschreibung.json.
Antworte nur: fertig"""

PROMPT_KONTROLLE = """Die Zusammenfassung ist gebaut ({seiten} Seiten). Prüfe sie jetzt, bevor sie an Jan geht.
- Kontrolltext (Inhalt in Lesereihenfolge, Quellen in eckigen Klammern): {kontrolltext}
- Vorschaubilder, jedes mit Read ansehen: {bilder}
{pruefliste}
Schreib deinen Bericht nach {ordner}/kontrolle.json, genau in diesem Format:
{bericht}
- abgedeckt: Nummern der Behauptungen, die richtig enthalten sind (mit Quellen und Kennzeichnung)
- fehlt: Nummern, die fehlen oder falsch wiedergegeben sind
- erfunden: Aussagen in der Zusammenfassung, die in keiner Datei des Auftrags stehen
- darstellung: Fehler im Aussehen (abgeschnitten, überlappend, leere Seite, falsche Reihenfolge)
Leere Listen, wenn nichts zu beanstanden ist. Ohne Behauptungsliste bleiben abgedeckt und fehlt leer.
{vorher}
Findest du Fehler, korrigiere zusätzlich {ordner}/beschreibung.json. Dann wird neu gebaut und du prüfst noch einmal.
Ist alles in Ordnung, ändere beschreibung.json nicht.

Deine Antwort ist die Kurzfassung für Jan (höchstens 6 Zeilen, ohne Markdown): was drin ist, worauf er beim
Weitergeben achten sollte (z. B. Kennzeichnungen unsicher), offene Fragen."""

PRUEFLISTE_MIT = "- Behauptungsliste: {pfad}. Prüfe jede Behauptung: kommt sie vor, stimmen Quellen und Kennzeichnung?\n"
PRUEFLISTE_OHNE = "- Keine Behauptungsliste. Prüfe gegen die Dateien des Auftrags.\n"
VORHER = "\nPython hat in deinem letzten Bericht diese Probleme gefunden:\n{probleme}\n"


# Ablauf -------------------------------------------------------------------------

def _lies(pfad: Path) -> str | None:
    return pfad.read_text(encoding="utf-8") if pfad.is_file() else None


def _pruefsumme(pfad: Path) -> str | None:
    return hashlib.sha256(pfad.read_bytes()).hexdigest() if pfad.is_file() else None


def erstellen(auftrag: dict, ordner: Path, agent_dir: Path, claude, bauen, format_text: str,
              behauptungen_pfad: str | None = None, sitzung: str | None = None) -> Fertig:
    """Führt den ganzen Ablauf aus (siehe oben).

    ordner: data/ausgang/<auftrag-id>/ (absolut). claude(prompt, sitzung) -> (text, sitzung, ok).
    bauen(beschreibung, ziel) -> Renderer-Ergebnis, wirft BeschreibungUngueltig bei Fehlern in der Beschreibung.
    sitzung: Sitzung fortsetzen (Jan antwortet auf eine fertige Zusammenfassung).
    """
    from renderer import BeschreibungUngueltig

    ordner.mkdir(parents=True, exist_ok=True)
    rel = ordner.relative_to(agent_dir).as_posix()
    beschreibung_pfad, bericht_pfad = ordner / "beschreibung.json", ordner / "kontrolle.json"
    nummern = []
    if behauptungen_pfad:
        nummern = [b["nr"] for b in behauptungen_lesen((agent_dir / behauptungen_pfad).read_text(encoding="utf-8"))]
        hinweis = HINWEIS_BEHAUPTUNGEN.format(pfad=behauptungen_pfad)
    else:
        hinweis = ""

    def fragen(prompt: str) -> str:
        nonlocal sitzung
        text, neue_sitzung, ok = claude(prompt, sitzung)
        sitzung = neue_sitzung or sitzung
        if not ok:
            raise ZusammenfassungFehler(f"Claude-Lauf fehlgeschlagen: {text[:500]}")
        return text

    if sitzung:
        fragen(PROMPT_ANTWORT.format(text=auftrag["text"], ordner=rel, behauptungen=hinweis))
    else:
        herkunft = f" von {auftrag['von']} (Agent)" if auftrag.get("von") else " von Jan"
        antwort = fragen(PROMPT_START.format(format=format_text, herkunft=herkunft, text=auftrag["text"],
                                             behauptungen=hinweis, ordner=rel))
        if antwort.strip().startswith(NICHT_UNTERSTUETZT):
            raise ZusammenfassungFehler("dokumente kann bisher nur Zusammenfassungen. "
                                        + antwort.strip().removeprefix(NICHT_UNTERSTUETZT).lstrip(": "))

    probleme: list[str] = []
    for kontrolle in range(1, MAX_KONTROLL_RUNDEN + 1):
        for versuch in range(1, MAX_BAU_RUNDEN + 1):
            try:
                b = beschreibung_lesen(_lies(beschreibung_pfad))
                ziel = ordner / f"{dateiname(b.get('titel') or '')}.docx"
                ergebnis = bauen(b, ziel)
                break
            except (BeschreibungKaputt, BeschreibungUngueltig) as e:  # andere Fehler sind die des Agenten
                if versuch == MAX_BAU_RUNDEN:
                    raise ZusammenfassungFehler(f"Beschreibung nach {MAX_BAU_RUNDEN} Versuchen ungültig:\n{e}") from None
                fragen(PROMPT_KORREKTUR.format(fehler=e, ordner=rel))
        if ergebnis.pdf is None or not ergebnis.bilder:
            raise ZusammenfassungFehler("Keine Vorschau, also kein PDF: " + "; ".join(ergebnis.hinweise))
        kontrolltext = ordner / "kontrolltext.txt"
        kontrolltext.write_text(ergebnis.kontrolltext, encoding="utf-8")
        bericht_pfad.unlink(missing_ok=True)
        vorher_summe = _pruefsumme(beschreibung_pfad)
        antwort = fragen(PROMPT_KONTROLLE.format(
            seiten=len(ergebnis.bilder), kontrolltext=kontrolltext.relative_to(agent_dir).as_posix(),
            bilder=", ".join(p.relative_to(agent_dir).as_posix() for p in ergebnis.bilder),
            pruefliste=PRUEFLISTE_MIT.format(pfad=behauptungen_pfad) if behauptungen_pfad else PRUEFLISTE_OHNE,
            ordner=rel, bericht=BERICHT_FORMAT,
            vorher=VORHER.format(probleme="\n".join(f"- {p}" for p in probleme)) if probleme else ""))
        probleme = bericht_pruefen(_lies(bericht_pfad), nummern)
        if not probleme and _pruefsumme(beschreibung_pfad) == vorher_summe:
            pdf = ordner / f"{ziel.stem}.pdf"
            shutil.copyfile(ergebnis.pdf, pdf)
            return Fertig(docx=ziel, pdf=pdf, titel=b["titel"], seiten=len(ergebnis.bilder), kontrollen=kontrolle,
                          antwort=antwort.strip(), sitzung=sitzung, hinweise=list(ergebnis.hinweise))
    raise ZusammenfassungFehler(f"Nach {MAX_KONTROLL_RUNDEN} Kontrollen nicht fertig. Zuletzt:\n"
                                + "\n".join(f"- {p}" for p in probleme or ["Beschreibung noch geändert"]))


def ergebnistext(f: Fertig, nummern: int) -> str:
    """Text für Jan in Telegram (die Dateien schickt die Zentrale danach)."""
    pruefung = (f"alle {nummern} Behauptungen der Liste enthalten, nichts dazuerfunden" if nummern
                else "gegen die Dateien geprüft, nichts dazuerfunden")
    zeilen = [f"Zusammenfassung „{f.titel}“, {f.seiten} Seiten. Kontrolle ({f.kontrollen}. Runde): {pruefung}.",
              "", f.antwort]
    if f.hinweise:
        zeilen += ["", "Hinweise: " + "; ".join(f.hinweise)]
    return "\n".join(zeilen)
