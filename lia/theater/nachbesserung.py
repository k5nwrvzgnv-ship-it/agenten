"""Aufträge an theater beantworten, vor allem Nachbesserungen aus Lias Feedback (Plan 30.10.2026).

Ein Auftrag bezieht sich auf eine Runde (data/runde-<zeit>/). Python sucht die Runde und den gültigen Ablauf,
rechnet Kennzahlen (Minuten je Baustein, Sprechzeit des Originals, Länge des neuen Texts) und legt alles in
data/<runde>/nachbesserung-<auftrag>/. Claude liest dort und entscheidet:
- "antwort": Lia bekommt nur eine kurze Antwort (Frage, Erklärung), die Fassung bleibt.
- "ueberarbeitung": Claude schreibt den ganzen Ablauf neu (ablauf.json, Format und Regeln wie in fassung.py),
  Python prüft ihn. Danach der Prüfschritt wie in einer Runde (runde.pruefschleife: unabhängiger Prüfer gegen die
  Rubrik, unter „gut“ überarbeitet der Autor in seiner Sitzung, höchstens kritik.MAX_UEBERARBEITUNGEN-mal).
  Python baut Ablauf (mit Lias Änderungen und der Prüfung) und Spielfassung neu. Lia bekommt beide Dateien.
Die Antwort für Lia steht in antwort.json (kern, höchstens 3 Punkte, pruefen) und wird gegen die Sprachregel der
Zentrale (agentkit.sprache, für Lia) geprüft. Eine Nachbesserung, danach Abbruch (harte Fehler) bzw. Versand mit
Warnung im Log (nur Sprachregel). stand.json merkt, welcher Ablauf nach dem Auftrag gilt (für Folgeaufträge).
Reine Logik, Claude und Renderer kommen als Funktionen herein.
"""

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import fassung
import karte
import kritik
import runde as runde_mod
import stueck
from agentkit import sprache

ARTEN = ("antwort", "ueberarbeitung")
MAX = {"kern": 400, "punkt": 250, "pruefen": 200}
MAX_PUNKTE = 3
WOERTER_JE_MINUTE = 130  # wie stueck.sprechminuten
RUNDE_MUSTER = re.compile(r"runde-\d{8}-\d{6}")
DOKUMENTE = ("2 Ablauf und Varianten.docx", "3 Spielfassung.docx")


class NachbesserungFehler(Exception):
    """Auftrag nicht bearbeitet. Der Text ist für Jan."""


@dataclass
class Ergebnis:
    text: str
    daten: dict
    dateien: list[Path] = field(default_factory=list)
    sitzung: str | None = None
    usd: float = 0.0
    laeufe: int = 0
    hinweise: list[str] = field(default_factory=list)


def runde_finden(auftrag: dict, data: Path) -> Path:
    """Ordner der Runde, auf die sich der Auftrag bezieht.

    Reihenfolge: bezug ist ein früherer Auftrag an theater (nachbesserung-<bezug>/), bezug ist die Zustellung einer
    Runde an Lia (an_lia.json), sonst ein Rundenname im Auftragstext."""
    bezug = auftrag.get("bezug")
    if bezug:
        treffer = sorted(data.glob(f"runde-*/nachbesserung-{bezug}"))
        if treffer:
            return treffer[0].parent
        for merker in sorted(data.glob("runde-*/an_lia.json")):
            try:
                if json.loads(merker.read_text(encoding="utf-8")).get("auftrag") == bezug:
                    return merker.parent
            except (OSError, json.JSONDecodeError):
                continue
    namen = RUNDE_MUSTER.findall(auftrag.get("text", ""))
    for name in dict.fromkeys(namen):
        if (data / name / "einheiten.json").exists():
            return data / name
    raise NachbesserungFehler(f"Auftrag {auftrag['id']}: keine Runde gefunden (bezug {bezug}, im Text {namen or 'keine'})")


def ablauf_finden(runde: Path, bezug: str | None) -> Path:
    """Der Ablauf, der für Lia gerade gilt: nach einem früheren Auftrag dessen Stand, sonst der der Runde."""
    if bezug:
        stand = runde / f"nachbesserung-{bezug}" / "stand.json"
        if stand.exists():
            return runde / json.loads(stand.read_text(encoding="utf-8"))["ablauf"]
    ergebnis = runde / "ergebnis.json"  # nach Prüfung und Überarbeitung (runde.py)
    name = json.loads(ergebnis.read_text(encoding="utf-8"))["ablauf"] if ergebnis.exists() else "ablauf.json"
    return runde / name


def _minuten(x: float) -> str:
    return karte.zahl(round(x, 1))


def kennzahlen(ablauf: dict, einheiten: list[stueck.Einheit], rahmen: dict) -> str:
    """Zahlen zur Fassung, von Python gerechnet, damit Claude sie nicht schätzen muss (Markdown)."""
    nach_nr = {e.nr: e for e in einheiten}
    teilnamen = {t["akt"]: t["name"] for t in rahmen["teile"]}
    zeilen = ["# Kennzahlen der Fassung (von Python gerechnet)", "",
              f"Sprechzeit: {WOERTER_JE_MINUTE} Wörter je Minute. Spielzeit = Minuten des Bausteins im Ablauf "
              "(mit Spiel, Pausen, Aktionen). Sprechzeit ist nur der gesprochene Text.", "",
              "| Baustein | Teil | Art | Spielzeit (Min) | Sprechzeit Original (Min) | Wörter neuer Text | "
              "Sprechzeit neuer Text (Min) |", "|---|---|---|---|---|---|---|"]
    summe = {"spiel": 0.0, "original": 0.0, "neu": 0.0, "woerter": 0}
    je_art: dict[str, float] = {}
    je_teil: dict[int, float] = {}
    for b in ablauf["bausteine"]:
        original = stueck.sprechminuten([nach_nr[n] for n in fassung.behalten(b) if n in nach_nr])
        woerter = len((b.get("neuer_text") or "").split())
        neu = woerter / WOERTER_JE_MINUTE
        zeilen.append(f"| {b['id']} {b['titel']} | {b['teil']} | {b['art']} | {_minuten(b['minuten'])} | "
                      f"{_minuten(original)} | {woerter} | {_minuten(neu)} |")
        summe["spiel"] += b["minuten"]
        summe["original"] += original
        summe["neu"] += neu
        summe["woerter"] += woerter
        je_art[b["art"]] = je_art.get(b["art"], 0) + b["minuten"]
        je_teil[b["teil"]] = je_teil.get(b["teil"], 0) + b["minuten"]
    behalten = sum(len(fassung.behalten(b)) for b in ablauf["bausteine"])
    zeilen += ["", "## Summen",
               f"- Bausteine: {len(ablauf['bausteine'])}, Spielzeit gesamt: {_minuten(summe['spiel'])} Min "
               f"(Rahmen {rahmen['minuten_min']}–{rahmen['minuten_max']} Min)",
               f"- Sprechzeit Originaltext: {_minuten(summe['original'])} Min ({behalten} von {len(einheiten)} "
               "Einheiten des Originals)",
               f"- Neuer Text: {summe['woerter']} Wörter, Sprechzeit {_minuten(summe['neu'])} Min",
               f"- Spielzeit ohne Sprechtext (Spiel, Pausen, Aktionen): "
               f"{_minuten(summe['spiel'] - summe['original'] - summe['neu'])} Min",
               "- Spielzeit je Art: " + ", ".join(f"{a} {_minuten(m)} Min" for a, m in sorted(je_art.items())),
               "- Spielzeit je Teil: " + ", ".join(f"Teil {t} ({teilnamen.get(t, '?')}) {_minuten(m)} Min"
                                                   for t, m in sorted(je_teil.items()))]
    return "\n".join(zeilen) + "\n"


def prompt(auftrag: dict, ordner: str, ablauf: str, spielfassung: str, kennzahlen_datei: str, lesen: list[str]) -> str:
    """Erster Lauf (neue Sitzung). ordner, ablauf, ... relativ zum Agent-Ordner. Lias Regeln gibt claude_lauf mit."""
    dateien = "\n".join(f"- {d}" for d in lesen)
    return f"""Du bist Lias Helfer für ihr Fach Darstellendes Spiel. Für ihren Kurs gibt es eine Fassung von
„Der nackte Wahnsinn“: einen Ablauf aus Bausteinen und eine Spielfassung. Lia hat sie bekommen und jetzt
eine Anfrage dazu geschickt.

Lias Anfrage:
<<<
{auftrag['text'].strip()}
>>>

Lies zuerst:
- {ablauf} (der aktuelle Ablauf, Bausteine mit Minuten, Originalstellen als Nummern, neuer Text)
- {spielfassung} (die Spielfassung als Text)
- {kennzahlen_datei} (Zahlen, die Python aus dem Ablauf gerechnet hat: Spielzeit, Sprechzeit, Wörter. Nimm
  diese Zahlen, rechne nicht selbst nach Gefühl.)
Bei Bedarf außerdem (Stück, Lias Vorgaben, Grundlagen, Szenenkarte, Fachbuch):
{dateien}

Entscheide:
- "antwort": Lia fragt etwas oder will eine Erklärung. Die Fassung bleibt, wie sie ist.
- "ueberarbeitung": Lia will die Fassung ändern. Dann schreibst du den ganzen Ablauf neu nach
  {ordner}/ablauf.json, im selben Format wie {ablauf} und mit denselben Regeln (Summe der Minuten im
  Rahmen, jeder Teil höchstens {fassung.TOLERANZ_TEIL_MIN} Min neben Lias Plan, Sprechzeit des Originals unter
  der Spielzeit jedes Bausteins, jede Nummer nur einmal, jeder Muss-Punkt genau einmal, Varianten und
  zuspitzung), dazu "aenderungen": 1 bis 8 Texte (je höchstens {kritik.MAX['aenderung']} Zeichen), was du
  geändert hast und warum. Ändere nur, was Lia will. Originaltext nur als Nummern, nie abschreiben.

Schreibe in jedem Fall {ordner}/antwort.json (JSON, sonst nichts):
{{"art": "antwort" oder "ueberarbeitung",
  "kern": "Die Antwort in 1 bis 3 kurzen Sätzen (höchstens {MAX['kern']} Zeichen)",
  "punkte": ["höchstens {MAX_PUNKTE} kurze Punkte, z. B. eine Aufschlüsselung (je höchstens {MAX['punkt']} Zeichen)"],
  "pruefen": "eine Rückfrage an Lia oder ein Hinweis, worauf sie achten soll; leer, wenn nichts (höchstens {MAX['pruefen']} Zeichen)"}}
So schreibst du für Lia: Sie ist Lehrerin, keine Technikerin. Duze sie. Kurze Sätze, höchstens 15 Wörter je
Satz, alles zusammen höchstens 600 Zeichen. Keine Dateinamen, keine Nummern von Bausteinen oder Einheiten, keine
Fachwörter aus der Technik. Sprich von dir als „ich“, nicht von einem Agenten. Sag ehrlich, wenn Zahlen nicht
zusammenpassen.
Antworte am Ende nur mit „fertig“."""


def text_fuer_lia(antwort: dict) -> str:
    teile = [antwort["kern"].strip()] + [f"- {p.strip()}" for p in antwort.get("punkte") or []]
    if (antwort.get("pruefen") or "").strip():
        teile.append(antwort["pruefen"].strip())
    return "\n".join(teile)


def antwort_pruefen(antwort: dict) -> list[str]:
    """Harte Fehler in antwort.json (leer = in Ordnung)."""
    fehler = []
    if antwort.get("art") not in ARTEN:
        fehler.append(f"art: eins von {', '.join(ARTEN)}")
    kern = antwort.get("kern")
    if not isinstance(kern, str) or not kern.strip():
        fehler.append("kern: Text fehlt")
    elif len(kern) > MAX["kern"]:
        fehler.append(f"kern: höchstens {MAX['kern']} Zeichen, sind {len(kern)}")
    punkte = antwort.get("punkte", [])
    if not isinstance(punkte, list) or len(punkte) > MAX_PUNKTE or \
            any(not isinstance(p, str) or not p.strip() or len(p) > MAX["punkt"] for p in punkte):
        fehler.append(f"punkte: höchstens {MAX_PUNKTE} Texte, je höchstens {MAX['punkt']} Zeichen")
    pruefen = antwort.get("pruefen", "")
    if not isinstance(pruefen, str) or len(pruefen) > MAX["pruefen"]:
        fehler.append(f"pruefen: Text mit höchstens {MAX['pruefen']} Zeichen")
    return fehler


def sprachbefunde(antwort: dict) -> list[str]:
    """Befunde der Sprachregel für Lia (weich: einmal nachbessern, danach trotzdem senden)."""
    return sprache.pruefen(text_fuer_lia(antwort), sprache.LIA)


def daten_fuer_lia(antwort: dict) -> dict:
    """Feld daten für Lias Zentrale (shared/telegram/vorlagen.py)."""
    d = {"kern": antwort["kern"].strip(), "punkte": [p.strip() for p in antwort.get("punkte") or []]}
    if (antwort.get("pruefen") or "").strip():
        d["pruefen"] = antwort["pruefen"].strip()
    return d


@dataclass
class Umgebung:
    """Was ein Auftrag braucht, ohne Netz: Agent-Ordner, Vorgaben, Funktionen für Claude und Renderer."""
    hier: Path
    vorgaben: dict  # theater.toml
    profil: dict
    laufen: object  # laufen(prompt, sitzung) -> claude_lauf.Ergebnis
    renderer_bauen: object  # renderer.bauen(beschreibung, ziel, profil=...)


def _pruefen_alles(ordner: Path, einheiten, v: dict) -> tuple[dict, dict | None, list[str], list[str]]:
    """Liest antwort.json (und bei Überarbeitung ablauf.json). Rückgabe: antwort, ablauf, harte Fehler, Sprachbefunde."""
    try:
        antwort = karte.antwort_lesen(ordner / "antwort.json")
    except karte.AntwortFehler as e:
        return {}, None, [str(e)], []
    fehler = antwort_pruefen(antwort)
    neu = None
    if antwort.get("art") == "ueberarbeitung":
        try:
            neu = karte.antwort_lesen(ordner / "ablauf.json")
            fehler += [f"ablauf.json: {f}" for f in
                       fassung.pruefen(neu, einheiten, v["muss"], v["rahmen"]) + kritik.aenderungen_pruefen(neu)]
        except karte.AntwortFehler as e:
            fehler.append(str(e))
    befunde = [] if fehler else sprachbefunde(antwort)
    return antwort, neu, fehler, befunde


def bearbeiten(auftrag: dict, u: Umgebung) -> Ergebnis:
    """Einen Auftrag bearbeiten. Fehler: NachbesserungFehler, claude_lauf.LaufFehler u. a."""
    data = u.hier / "data"
    runde = runde_finden(auftrag, data)
    alt = ablauf_finden(runde, auftrag.get("bezug"))
    v = u.vorgaben
    einheiten = stueck.aus_dicts(json.loads((runde / "einheiten.json").read_text(encoding="utf-8")))
    try:
        ablauf = karte.antwort_lesen(alt)
    except karte.AntwortFehler as e:
        raise NachbesserungFehler(f"Ablauf der Runde {runde.name}: {e}") from None
    ordner = runde / f"nachbesserung-{auftrag['id']}"
    ordner.mkdir(exist_ok=True)
    for muster in ("antwort.json", "ablauf*.json", "kritik-*.json"):  # Reste eines abgebrochenen Laufs zählen nicht
        for p in ordner.glob(muster):
            p.unlink()
    (ordner / "kennzahlen.md").write_text(kennzahlen(ablauf, einheiten, v["rahmen"]), encoding="utf-8")
    fassung.schreiben_text(ordner / "spielfassung-vorher.txt", ablauf, einheiten)
    rel = lambda p: str(p.relative_to(u.hier))  # noqa: E731
    lesen = sorted(rel(p) for p in (runde / "kontext").glob("*")) + [rel(runde / "szenenkarte.json")]
    erg = Ergebnis(text="", daten={})

    def lauf(text: str, sitzung: str | None):
        r = u.laufen(text, sitzung)
        erg.usd += r.usd or 0
        erg.laeufe += 1
        return r

    r = lauf(prompt(auftrag, rel(ordner), rel(alt), rel(ordner / "spielfassung-vorher.txt"),
                    rel(ordner / "kennzahlen.md"), lesen), None)
    erg.sitzung = r.sitzung
    antwort, neu, fehler, befunde = _pruefen_alles(ordner, einheiten, v)
    if fehler or befunde:
        hinweis = [] if fehler else ["Halte die Sprachregel für Lia ein (kurze Sätze, keine Technikwörter)."]
        r = lauf(karte.nachbesserung_prompt(fehler + befunde + hinweis, rel(ordner / "antwort.json")
                                            + (" bzw. " + rel(ordner / "ablauf.json") if neu is not None else "")),
                 erg.sitzung)
        erg.sitzung = r.sitzung or erg.sitzung
        antwort, neu, fehler, befunde = _pruefen_alles(ordner, einheiten, v)
        if fehler:
            raise NachbesserungFehler(f"Antwort nach Nachbesserung noch fehlerhaft: {'; '.join(fehler)}")
    if befunde:
        erg.hinweise.append(f"Sprachregel: {sprache.log_text(befunde)}")
    gilt = alt
    if neu is not None:
        p = pruefen_lassen(ordner, runde, neu, erg.sitzung, einheiten, v, u, lauf)
        if p.get("abgebrochen"):
            erg.hinweise.append(f"Prüfschritt abgebrochen, Stand {p['datei']}: {p['abgebrochen']}")
        if p["unter_gut"]:
            erg.hinweise.append(f"nach {p['ueberarbeitungen']} Überarbeitungen noch unter „gut“: "
                                + ", ".join(p["unter_gut"]))
        erg.dateien = bauen(ordner, p["ablauf"], einheiten, v, u, neu["aenderungen"], p)
        fassung.schreiben_text(ordner / "spielfassung.txt", p["ablauf"], einheiten)
        gilt = ordner / p["datei"]
    (ordner / "stand.json").write_text(json.dumps(
        {"auftrag": auftrag["id"], "art": antwort["art"], "ablauf": str(gilt.relative_to(runde))},
        ensure_ascii=False), encoding="utf-8")
    erg.text, erg.daten = text_fuer_lia(antwort), daten_fuer_lia(antwort)
    return erg


def pruefen_lassen(ordner: Path, runde: Path, neu: dict, sitzung: str | None, einheiten, v: dict, u: Umgebung,
                   laufen) -> dict:
    """Prüfschritt wie in runde.py auf den überarbeiteten Ablauf (ordner/ablauf.json). Rückgabe von
    runde.pruefschleife, dazu unter_gut (ids der Kriterien, die nach allen Überarbeitungen unter „gut“ bleiben)."""
    rel = lambda p: str(p.relative_to(u.hier))  # noqa: E731
    kontext = runde / "kontext"
    shutil.copy(runde / "szenenkarte.json", ordner / "szenenkarte.json")  # der Prüfer liest sie neben dem Ablauf
    pfade = {"teile": [rel(p) for p in sorted(kontext.glob("stueck-teil-*.txt"))],
             "vorgaben": rel(kontext / "vorgaben.md"), "grundlagen": rel(kontext / "grundlagen.md"),
             "buch": [rel(p) for p in sorted(kontext.glob("buch-teil-*.md"))]}
    try:
        p = runde_mod.pruefschleife(laufen, runde_mod.Kosten(None), ordner, ordner.relative_to(u.hier), pfade, neu,
                                    sitzung, einheiten, v["muss"], v["rahmen"], v)
    except (runde_mod.RundenFehler, karte.AntwortFehler) as f:
        # Lias Änderung ist da und geprüft; ein gescheiterter Prüfschritt soll sie nicht verwerfen (Probelauf 30.10.)
        p = letzter_guter_stand(ordner, einheiten, v)
        p["abgebrochen"] = str(f)
    p["unter_gut"] = [b["id"] for b in kritik.unter_schwelle(p["kritik"], v)] if p["kritik"] else []
    return p


def letzter_guter_stand(ordner: Path, einheiten, v: dict) -> dict:
    """Nach Abbruch des Prüfschritts: die höchste Version (ablauf.json, ablauf-2.json, ...), die die Prüfung von
    Python besteht, mit ihrer Bewertung kritik-<n>.json, falls es die gültig gibt. Format wie runde.pruefschleife."""
    gut, aenderungen = None, []
    for n in range(1, kritik.MAX_UEBERARBEITUNGEN + 2):
        datei = "ablauf.json" if n == 1 else f"ablauf-{n}.json"
        try:
            f = karte.antwort_lesen(ordner / datei)
        except karte.AntwortFehler:
            break
        if fassung.pruefen(f, einheiten, v["muss"], v["rahmen"]) + kritik.aenderungen_pruefen(f):
            break
        if n > 1:
            aenderungen += f["aenderungen"]
        gut = {"ablauf": f, "datei": datei, "ueberarbeitungen": n - 1, "aenderungen": list(aenderungen),
               "kritik": None, "kritik_datei": None}
        try:
            k = karte.antwort_lesen(ordner / f"kritik-{n}.json")
            if not kritik.pruefen(k, v):
                gut.update(kritik=k, kritik_datei=f"kritik-{n}.json")
        except karte.AntwortFehler:
            pass
    if gut is None:
        raise NachbesserungFehler("Prüfschritt abgebrochen und kein gültiger Ablauf vorhanden")
    return gut


def bauen(ordner: Path, ablauf: dict, einheiten, v: dict, u: Umgebung, lia_aenderungen: list[str],
          pruefung: dict) -> list[Path]:
    """Ablauf und Spielfassung neu; am Ende des Ablaufs, was nach Lias Rückmeldung geändert ist, und die Prüfung."""
    titel, rahmen = v["stueck"]["titel"], v["rahmen"]
    doc = fassung.ablauf(ablauf, einheiten, v["muss"], rahmen, titel)
    doc["bloecke"] += [{"typ": "ueberschrift", "text": "Was ich nach deiner Rückmeldung geändert habe"},
                       {"typ": "liste", "punkte": lia_aenderungen}]
    if pruefung["kritik"]:
        doc["bloecke"] += kritik.bloecke(pruefung["kritik"], v, pruefung["ueberarbeitungen"], pruefung["aenderungen"])
    elif pruefung["aenderungen"]:
        doc["bloecke"] += [{"typ": "ueberschrift", "text": "Nach der Prüfung geändert", "ebene": 2},
                           {"typ": "liste", "punkte": pruefung["aenderungen"]}]
    ziel = ordner / "fuer-lia"
    ziel.mkdir(exist_ok=True)
    dateien = []
    for name, b in zip(DOKUMENTE, [doc, fassung.spielfassung(ablauf, einheiten, rahmen, titel)], strict=True):
        (ziel / name.replace(".docx", ".json")).write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
        try:
            u.renderer_bauen(b, ziel / name, profil=u.profil)
        except ValueError as e:  # BeschreibungUngueltig ist ein ValueError
            raise NachbesserungFehler(f"{name}: Renderer lehnt die Beschreibung ab: {e}") from None
        dateien.append(ziel / name)
    return dateien
