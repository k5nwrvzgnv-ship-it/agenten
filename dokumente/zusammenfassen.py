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

Derselbe Ablauf baut auch die Arten des Arbeitsplatzes (arten.py: Präsentation, Bericht). Was je Art anders ist
(Renderer-Art, Prompts, Kontrollbericht), steht in einem Art-Objekt; ohne Angabe gilt ZUSAMMENFASSUNG wie bisher.

Claude und der Renderer werden als Funktionen übergeben, damit sich der Ablauf ohne Netz testen lässt.
"""

import hashlib
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

MAX_BAU_RUNDEN = 3
MAX_KONTROLL_RUNDEN = 3
BEHAUPTUNGEN = "behauptungen.json"
NICHT_UNTERSTUETZT = "NICHT_UNTERSTUETZT"
OFFEN_MUSTER = re.compile(r"\[OFFEN:[^\]]*\]")
KURZ = "kurz.json"
BERICHT_FORMAT = """{"abgedeckt": [1, 2], "fehlt": [3], "erfunden": ["Aussage, die in keiner Quelle steht"],
 "darstellung": ["Seite 2: Tabelle läuft über den Rand"]}"""


class ZusammenfassungFehler(Exception):
    """Das Dokument (Zusammenfassung oder eine andere Art) ist nicht fertig geworden. Der Text geht an Jan."""


class BehauptungslisteUngueltig(ZusammenfassungFehler):
    pass


class BeschreibungKaputt(Exception):
    """beschreibung.json fehlt oder ist kein JSON. Geht wie BeschreibungUngueltig an Claude zurück."""


@dataclass
class Fertig:
    datei: Path  # docx oder pptx zum Bearbeiten
    pdf: Path
    titel: str
    seiten: int
    kontrollen: int
    antwort: str  # Claudes letzte Antwort, die Kurzfassung für Jan
    sitzung: str | None
    hinweise: list[str] = field(default_factory=list)
    offen: list[str] = field(default_factory=list)  # Stellen [OFFEN: …] im fertigen Dokument
    kurz: dict | None = None  # kurz.json von Claude (kern, punkte, pruefen), nur wenn verlangt und gültig
    art: str = "zusammenfassung"


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


def beschreibung_lesen(text: str | None, renderer_art: str = "zusammenfassung") -> dict:
    """beschreibung.json als dict. BeschreibungKaputt mit einem Text, den Claude beheben kann."""
    if text is None:
        raise BeschreibungKaputt("beschreibung.json fehlt")
    try:
        b = json.loads(text)
    except json.JSONDecodeError as e:
        raise BeschreibungKaputt(f"beschreibung.json ist kein gültiges JSON: {e}") from None
    if not isinstance(b, dict) or b.get("art") != renderer_art:
        raise BeschreibungKaputt(f'beschreibung.json muss ein Objekt mit "art": "{renderer_art}" sein')
    return b


def offene_stellen(kontrolltext: str) -> list[str]:
    """Alle Stellen [OFFEN: …] im Kontrolltext, in Reihenfolge, ohne Doppelte."""
    return list(dict.fromkeys(OFFEN_MUSTER.findall(kontrolltext)))


def kurz_lesen(text: str | None) -> dict | None:
    """kurz.json von Claude: {"kern": Text, "punkte": [Texte], "pruefen": Text}. None, wenn es fehlt oder nicht passt
    (dann nimmt der Agent Claudes Antwort, ein Fehler hier ist keinen neuen Lauf wert)."""
    if text is None:
        return None
    try:
        k = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(k, dict) or not isinstance(k.get("kern"), str) or not k["kern"].strip():
        return None
    punkte = k.get("punkte", [])
    if not isinstance(punkte, list) or not all(isinstance(p, str) for p in punkte):
        return None
    pruefen = k.get("pruefen", "")
    if not isinstance(pruefen, str):
        return None
    return {"kern": k["kern"].strip(), "punkte": [p.strip() for p in punkte if p.strip()][:8],
            "pruefen": pruefen.strip()}


def dateiname(titel: str, ersatz: str = "zusammenfassung") -> str:
    """Dateiname ohne Endung aus dem Titel: Umlaute umschreiben, nur Buchstaben, Ziffern und Bindestriche."""
    t = titel.lower()
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(alt, neu)
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60].strip("-")
    return t or ersatz


def format_abschnitt(format_md: str, abschnitte: tuple[str, ...] = ("Allgemein", "Zusammenfassung")) -> str:
    """Aus FORMAT.md des Renderers nur die Abschnitte, die Claude für diese Art braucht."""
    teile = re.split(r"^## ", format_md, flags=re.M)
    behalten = [t for t in teile[1:] if t.startswith(abschnitte)]
    if len(behalten) != len(abschnitte):
        raise ValueError(f"FORMAT.md: Abschnitte {', '.join(abschnitte)} nicht gefunden")
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
{dateien}
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
{kurz}
Deine Antwort ist die Kurzfassung für Jan (höchstens 6 Zeilen, ohne Markdown): was drin ist, worauf er beim
Weitergeben achten sollte (z. B. Kennzeichnungen unsicher), offene Fragen."""

PRUEFLISTE_MIT = "- Behauptungsliste: {pfad}. Prüfe jede Behauptung: kommt sie vor, stimmen Quellen und Kennzeichnung?\n"
PRUEFLISTE_OHNE = "- Keine Behauptungsliste. Prüfe gegen die Dateien des Auftrags.\n"
VORHER = "\nPython hat in deinem letzten Bericht diese Probleme gefunden:\n{probleme}\n"
HINWEIS_KURZ = """Schreib außerdem {ordner}/""" + KURZ + """ für die Seite des Dokuments, genau so:
{{"kern": "1-2 Sätze: was das Dokument ist und kann", "punkte": ["bis zu 5 kurze Punkte zum Inhalt"],
 "pruefen": "was Jan vor dem Weitergeben prüfen oder ergänzen muss, leer wenn nichts"}}
"""
DATEIEN_ANTWORT = "Dazu hat er diese Dateien geschickt (Text daneben als <datei>.txt): {liste}\n"


@dataclass(frozen=True)
class Art:
    """Was eine Dokumentart vom Ablauf unterscheidet. Platzhalter der Prompts siehe erstellen()."""
    kennung: str  # wie im Auftrag (art) bzw. "zusammenfassung"
    name: str  # für Jan, z. B. "Präsentation"
    renderer_art: str  # art in der Beschreibung
    endung: str  # .docx oder .pptx
    abschnitte: tuple[str, ...]  # aus FORMAT.md für den Prompt
    prompt_start: str
    prompt_antwort: str
    prompt_kontrolle: str
    bericht_format: str
    pruefe_bericht: Callable[[str | None, list[int]], list[str]]
    einheit: str = "Seiten"
    abbruch: str = NICHT_UNTERSTUETZT  # Antwortanfang, mit dem Claude den Auftrag zurückgibt
    abbruch_text: str = "dokumente kann bisher nur Zusammenfassungen. "


ZUSAMMENFASSUNG = Art("zusammenfassung", "Zusammenfassung", "zusammenfassung", ".docx", ("Allgemein", "Zusammenfassung"),
                      PROMPT_START, PROMPT_ANTWORT, PROMPT_KONTROLLE, BERICHT_FORMAT, bericht_pruefen)


# Ablauf -------------------------------------------------------------------------

def _lies(pfad: Path) -> str | None:
    return pfad.read_text(encoding="utf-8") if pfad.is_file() else None


def _pruefsumme(pfad: Path) -> str | None:
    return hashlib.sha256(pfad.read_bytes()).hexdigest() if pfad.is_file() else None


def erstellen(auftrag: dict, ordner: Path, agent_dir: Path, claude, bauen, format_text: str,
              behauptungen_pfad: str | None = None, sitzung: str | None = None, art: Art = ZUSAMMENFASSUNG,
              mit_kurz: bool = False) -> Fertig:
    """Führt den ganzen Ablauf aus (siehe oben).

    ordner: data/ausgang/<auftrag-id>/ (absolut). claude(prompt, sitzung) -> (text, sitzung, ok).
    bauen(beschreibung, ziel) -> Renderer-Ergebnis, wirft BeschreibungUngueltig bei Fehlern in der Beschreibung.
    sitzung: Sitzung fortsetzen (Jan antwortet auf ein fertiges Dokument).
    format_text: die Abschnitte aus FORMAT.md für diese Art (format_abschnitt(..., art.abschnitte)).
    mit_kurz: Claude schreibt in der Kontrolle zusätzlich kurz.json (Arbeitsplatz, Ergebnis daten).
    Platzhalter der Prompts: format, herkunft, text, behauptungen, ordner, dateien, material (start/antwort);
    seiten, einheit, kontrolltext, bilder, pruefliste, ordner, bericht, vorher, kurz (kontrolle).
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

    eigene = [d for d in auftrag.get("dateien") or [] if d != behauptungen_pfad]
    dateien = DATEIEN_ANTWORT.format(liste=", ".join(eigene)) if eigene else ""
    if sitzung:
        fragen(art.prompt_antwort.format(text=auftrag["text"], ordner=rel, behauptungen=hinweis, dateien=dateien))
    else:
        herkunft = f" von {auftrag['von']} (Agent)" if auftrag.get("von") else " von Jan"
        antwort = fragen(art.prompt_start.format(format=format_text, herkunft=herkunft, text=auftrag["text"],
                                                 behauptungen=hinweis, ordner=rel, dateien=dateien,
                                                 material=", ".join(eigene) or "keine Dateien"))
        if antwort.strip().startswith(art.abbruch):
            raise ZusammenfassungFehler(art.abbruch_text + antwort.strip().removeprefix(art.abbruch).lstrip(": "))

    probleme: list[str] = []
    for kontrolle in range(1, MAX_KONTROLL_RUNDEN + 1):
        for versuch in range(1, MAX_BAU_RUNDEN + 1):
            try:
                b = beschreibung_lesen(_lies(beschreibung_pfad), art.renderer_art)
                ziel = ordner / f"{dateiname(b.get('titel') or '', art.kennung)}{art.endung}"
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
        (ordner / KURZ).unlink(missing_ok=True)
        vorher_summe = _pruefsumme(beschreibung_pfad)
        antwort = fragen(art.prompt_kontrolle.format(
            seiten=len(ergebnis.bilder), einheit=art.einheit,
            kontrolltext=kontrolltext.relative_to(agent_dir).as_posix(),
            bilder=", ".join(p.relative_to(agent_dir).as_posix() for p in ergebnis.bilder),
            pruefliste=PRUEFLISTE_MIT.format(pfad=behauptungen_pfad) if behauptungen_pfad else PRUEFLISTE_OHNE,
            ordner=rel, bericht=art.bericht_format, kurz=HINWEIS_KURZ.format(ordner=rel) if mit_kurz else "",
            vorher=VORHER.format(probleme="\n".join(f"- {p}" for p in probleme)) if probleme else ""))
        probleme = art.pruefe_bericht(_lies(bericht_pfad), nummern)
        if not probleme and _pruefsumme(beschreibung_pfad) == vorher_summe:
            pdf = ordner / f"{ziel.stem}.pdf"
            shutil.copyfile(ergebnis.pdf, pdf)
            return Fertig(datei=ziel, pdf=pdf, titel=b["titel"], seiten=len(ergebnis.bilder), kontrollen=kontrolle,
                          antwort=antwort.strip(), sitzung=sitzung, hinweise=list(ergebnis.hinweise),
                          offen=offene_stellen(ergebnis.kontrolltext),
                          kurz=kurz_lesen(_lies(ordner / KURZ)) if mit_kurz else None, art=art.kennung)
    raise ZusammenfassungFehler(f"Nach {MAX_KONTROLL_RUNDEN} Kontrollen nicht fertig. Zuletzt:\n"
                                + "\n".join(f"- {p}" for p in probleme or ["Beschreibung noch geändert"]))


def ergebnistext(f: Fertig, nummern: int) -> str:
    """Text für Jan in Telegram (die Dateien schickt die Zentrale danach)."""
    if f.art == "zusammenfassung":
        pruefung = (f"alle {nummern} Behauptungen der Liste enthalten, nichts dazuerfunden" if nummern
                    else "gegen die Dateien geprüft, nichts dazuerfunden")
        zeilen = [f"Zusammenfassung „{f.titel}“, {f.seiten} Seiten. Kontrolle ({f.kontrollen}. Runde): {pruefung}.",
                  "", f.antwort]
    else:
        name, einheit = {"praesentation": ("Präsentation", "Folien"), "bericht": ("Bericht", "Seiten")}.get(
            f.art, (f.art, "Seiten"))
        zeilen = [f"{name} „{f.titel}“, {f.seiten} {einheit}, {f.datei.suffix[1:]} und PDF. Kontrolle "
                  f"({f.kontrollen}. Runde): gegen Material und Auftrag geprüft, nichts dazuerfunden.", "", f.antwort]
        if f.offen:
            zeilen += ["", f"Offen ({len(f.offen)}): " + "; ".join(f.offen)]
    if f.hinweise:
        zeilen += ["", "Hinweise: " + "; ".join(f.hinweise)]
    return "\n".join(zeilen)


def ergebnisdaten(f: Fertig, umfang: str | None = None) -> dict:
    """daten für abschliessen (Arbeitsplatz): titel, kern, punkte, pruefen. Aus kurz.json, sonst aus Claudes Antwort.
    Python ergänzt pruefen um die offenen Stellen, Abweichungen vom gewünschten Umfang und Hinweise des Renderers."""
    kurz = f.kurz or {"kern": next((z for z in f.antwort.splitlines() if z.strip()), f.titel).strip(),
                      "punkte": [], "pruefen": ""}
    pruefen = [kurz["pruefen"]] if kurz["pruefen"] else []
    if f.offen:
        pruefen.append(f"{len(f.offen)} offene Stelle(n) [OFFEN: …] ergänzen")
    abweichung = umfang_abweichung(umfang, f.seiten, "Folien" if f.datei.suffix == ".pptx" else "Seiten")
    if abweichung:
        pruefen.append(abweichung)
    if f.hinweise:
        pruefen.append("Hinweise: " + "; ".join(f.hinweise))
    return {"titel": f.titel, "kern": kurz["kern"], "punkte": kurz["punkte"], "pruefen": " ".join(pruefen)}


def umfang_zahl(umfang: str | None) -> int | None:
    """Erste ganze Zahl aus einem Umfang wie "10 Folien" oder "ca. 5 Seiten". None, wenn keine drin ist."""
    m = re.search(r"\d+", umfang or "")
    return int(m.group()) if m and int(m.group()) > 0 else None


def umfang_abweichung(umfang: str | None, ist: int, einheit: str) -> str:
    """Hinweis, wenn das Ergebnis deutlich vom gewünschten Umfang abweicht (unter 70 % oder über 130 % plus 1).
    Nur ein Hinweis: Mit wenig Material ist ein kürzeres Dokument richtiger als ein aufgefülltes."""
    soll = umfang_zahl(umfang)
    if soll is None or soll * 0.7 <= ist <= soll * 1.3 + 1:
        return ""
    return f"Umfang: gewünscht {soll} {einheit}, es sind {ist}."
