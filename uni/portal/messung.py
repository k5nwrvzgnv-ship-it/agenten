"""Messlatte für die Portal-Oberfläche: Jan löst Aufgaben im echten Portal, das Werkzeug misst Zeit, Erfolg und Seitenaufrufe.

Aufruf auf dem Server, im Ordner uni/portal:
    ../.venv/bin/python messung.py pruefen      Sind die Sätze vollständig und gleich schwer? Zeigt keine Fragen, keine Lösungen.
    ../.venv/bin/python messung.py A            Satz A messen (Satz B entsprechend, zur Abnahme)

Nur lesend: Das Werkzeug schickt nichts ans Portal, ändert keine Daten und gehört nicht zum Web-Dienst. Es schreibt nur nach
portal/data/messung/ (nicht im Repo). Die Parameter der Aufgaben und die Lösungen entstehen zur Laufzeit aus den Daten, damit
weder Fragen noch Lösungen im Repo oder im Chat stehen. Lösungen erscheinen erst nach dem Satz, und nur zu gestellten Fragen.

Die Seitenaufrufe kommen aus dem Log des Dienstes. Das Log kennt die Quelle nicht (alles 127.0.0.1): Wer nebenher im Portal
surft, zählt mit. Lesen innerhalb einer Seite und Strg+F sieht das Log nicht, das steckt nur in der Zeit.
"""

import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.append(str(HIER.parent))  # lernmodell.py liegt in uni/; hinten, damit eigene Namen vorgehen

import ablage  # noqa: E402
import projekt as projektansicht  # noqa: E402

UNI = HIER.parent
ORDNER = HIER / "data" / "messung"
PROJEKT = "fehlstellen"
MODUL = "holzschutz"
SAETZE = ("A", "B")
DIENST = "uni-portal"
GRENZE_VERHAELTNIS = 2.0  # ab diesem Aufwandsverhältnis gelten zwei Aufgaben nicht mehr als gleich schwer
ANFANG_ZEICHEN = 80

# Geht am alten Stand gar nicht: wird nicht gefragt, sondern als "geht nicht" festgehalten. Bei der Abnahme neu zu bewerten.
GEHT_NICHT = ("K1: zwei Fassungen vergleichen (was hat sich geändert)", "K3: der Recherche im Portal eine Nachfrage stellen")

AUFRUF = re.compile(r'^(\d+)(?:\.\d+)?\s.*"([A-Z]+) (\S+) HTTP/[\d.]+" (\d{3})')
NICHT_GEZAEHLT = ("/statisch/", "/favicon.ico")


@dataclass
class Aufgabe:
    id: str
    kern: str
    frage: str
    art: str  # zahl, datum, text oder log
    loesung: str
    param: str  # was diese Aufgabe von der des anderen Satzes unterscheidet
    seite: str  # wo die Lösung am alten Stand steht
    nachweis: list[str] = field(default_factory=list)  # das muss dort im Text stehen, für den Lösbarkeitstest
    mal: int = 1  # so oft muss nachweis[0] dort stehen
    aufwand: float = 1  # wie viel man prüfen oder zählen muss, nur um die Sätze zu vergleichen
    heute_loesbar: bool = True
    beide: bool = False  # steht unverändert in beiden Sätzen


def _rang(aufgabe: Aufgabe) -> str:
    """Feste, aber nicht von Hand gewählte Reihenfolge, stabil auch wenn Kandidaten dazukommen."""
    return hashlib.sha256(f"{aufgabe.id}|{aufgabe.param}".encode()).hexdigest()


def _k1_umfang(d: dict) -> list[Aufgabe]:
    """Feste Reihenfolge: Satz A die kürzere Tabelle, Satz B die längere Literatur. So ist die Abnahme eher schwerer als die
    Ausgangsmessung, ein Fortschritt wird also nicht zu gut gerechnet."""
    expose = d.get("expose") or {}
    pool = []
    tabellen = [b for b in expose.get("bloecke") or [] if b.get("typ") == "tabelle"]
    if len(tabellen) == 1:
        zeilen = len(tabellen[0].get("zeilen") or [])
        pool.append(Aufgabe("umfang", "K1", "Wie viele Zeilen hat die Tabelle im Exposé (ohne Kopfzeile)?", "zahl", str(zeilen),
                            "tabelle", f"/projekt/{PROJEKT}", aufwand=zeilen))
    literatur = expose.get("literatur") or []
    if literatur:
        pool.append(Aufgabe("umfang", "K1", "Wie viele Literaturangaben hat die aktuelle Fassung des Exposés?", "zahl",
                            str(len(literatur)), "literatur", f"/projekt/{PROJEKT}", aufwand=len(literatur)))
    return pool


def _k2_offene_stellen(d: dict) -> list[Aufgabe]:
    zaehler: dict[str, int] = {}
    for o in projektansicht.offene_stellen(d.get("expose") or {}):
        zaehler[o["abschnitt"]] = zaehler.get(o["abschnitt"], 0) + 1
    return [Aufgabe("offen", "K2", f'Wie viele offene Stellen hat das Exposé im Abschnitt "{abschnitt}"?', "zahl", str(n), abschnitt,
                    f"/projekt/{PROJEKT}", [abschnitt], aufwand=n) for abschnitt, n in zaehler.items()]


def _k3_status(d: dict) -> list[Aufgabe]:
    """Fragen mittlerer Größe, in denen der Filter etwas zu tun hat."""
    aussagen = _liste(d.get("geprueft"), "aussagen")
    pool = []
    for f in _liste(d.get("geprueft"), "fragen"):
        eigene = [a for a in aussagen if a.get("frage") == f.get("id")]
        treffer = sum(a.get("status") == "teilweise" for a in eigene)
        if 5 <= len(eigene) <= 10 and 0 < treffer < len(eigene):
            pool.append(Aufgabe("status", "K3", f'Wie viele Aussagen sind in der Recherche-Frage {f["id"]} "teilweise belegt"?', "zahl",
                                str(treffer), str(f["id"]), f"/projekt/{PROJEKT}/recherche?status=teilweise&frage={f['id']}",
                                [f"{treffer} Aussagen"], aufwand=len(eigene)))
    return pool


def _k4_belege(d: dict) -> list[Aufgabe]:
    aussagen = _liste(d.get("geprueft"), "aussagen")
    pool = []
    for a in aussagen:
        text = str(a.get("text") or "")
        anfang = text[:ANFANG_ZEICHEN]
        anzahl = len(a.get("belege") or [])
        if 2 <= anzahl <= 3 and len(anfang) >= 40 and sum(str(x.get("text") or "").startswith(anfang) for x in aussagen) == 1:
            pool.append(Aufgabe("belege", "K4", f'Wie viele Belege hat diese Aussage aus der Recherche? "{anfang}…"', "zahl", str(anzahl),
                                str(a.get("id")), f"/projekt/{PROJEKT}/recherche", [anfang], aufwand=anzahl))
    return pool


def _k4_quelle(d: dict) -> list[Aufgabe]:
    """Nur Quellen mit eindeutigem Titel, deren Adresse sich auf der Seite eindeutig zählen lässt."""
    geprueft = d.get("geprueft")
    quellen = _liste(geprueft, "quellen")
    aussagen = _liste(geprueft, "aussagen")
    belege = [str(b.get("url") or "") for a in aussagen for b in a.get("belege") or []]
    pool = []
    for q in quellen:
        titel, url = str(q.get("titel") or ""), str(q.get("url") or "")
        if len(titel) < 15 or not url or sum(str(x.get("titel") or "") == titel for x in quellen) != 1:
            continue
        anzahl = sum(any(str(b.get("url") or "") == url for b in a.get("belege") or []) for a in aussagen)
        if 2 <= anzahl <= 4 and sum(url in b for b in belege) == anzahl:
            pool.append(Aufgabe("quelle", "K4", f'Bei wie vielen Aussagen der Recherche ist diese Quelle ein Beleg? "{titel}"', "zahl",
                                str(anzahl), url, f"/projekt/{PROJEKT}/recherche", [url], mal=anzahl, aufwand=anzahl))
    return pool


def _k5_suche(d: dict) -> list[Aufgabe]:
    suche = (d.get("geprueft") or {}).get("literatursuche") or {}
    return [Aufgabe("suche", "K5", f"Wie heißt die Literatursuche {s['nr']}? Der Titel genügt.", "text", str(s["titel"]), str(s["nr"]),
                    f"/projekt/{PROJEKT}/recherche?ansicht=suche", [f"{s['nr']}: {s['titel']}"])
            for s in suche.get("suchen") or [] if isinstance(s, dict) and s.get("nr") and s.get("titel")]


def _k6_pdf(d: dict) -> list[Aufgabe]:
    if not d.get("pdf"):
        return []
    return [Aufgabe("pdf", "K6", 'Öffne die aktuelle Fassung des Exposés als PDF. Wenn sie offen ist, gib "ok" ein.', "log", "PDF geöffnet",
                    "", f"/projekt/{PROJEKT}/fassung/pdf", beide=True)]


def _k7_mail(d: dict) -> list[Aufgabe]:
    """Feste Reihenfolge: Satz A die älteste, Satz B die neueste Mail."""
    daten = sorted(str(m.get("datum") or "") for m in _liste(d.get("schriftverkehr"), "mails"))
    daten = [x for x in daten if x]
    if len(daten) < 2:
        return []
    return [Aufgabe("mail", "K7", f"Welches Datum hat die {wort} Mail im Schriftverkehr?", "datum", datum[:10], param,
                    f"/projekt/{PROJEKT}/schriftverkehr", [datum[:10]])
            for wort, param, datum in (("älteste", "aelteste", daten[0]), ("neueste", "neueste", daten[-1]))]


def _k8_score(d: dict) -> list[Aufgabe]:
    return [Aufgabe("score", "K8", f'Welchen Score hat das Prüfungsthema "{t["titel"]}" im Modul Holzschutz?', "zahl", str(t["score"]),
                    str(t.get("id")), f"/modul/{MODUL}", [str(t["titel"]), f"Score {t['score']}"])
            for t in _liste(d.get("plan"), "themen") if t.get("titel") and t.get("score") is not None]


def _herkunft(d: dict) -> list[Aufgabe]:
    """Die Herkunft einer Aussage steht heute nirgends auf der Seite: darf aufgegeben werden, zeigt den Abstand zum Ziel."""
    zaehler: dict[str, int] = {}
    for a in _liste(d.get("geprueft"), "aussagen"):
        if not a.get("belege") and a.get("fenster"):
            zaehler[a["fenster"]] = zaehler.get(a["fenster"], 0) + 1
    return [Aufgabe("herkunft", "K3", f'Wie viele Aussagen aus dem Suchfenster "{f}" haben keinen Beleg?', "zahl", str(n), f,
                    f"/projekt/{PROJEKT}/recherche", aufwand=n, heute_loesbar=False) for f, n in zaehler.items()]


# Reihenfolge der Fragen. Die letzte geht heute nicht und steht deshalb am Ende, damit sie die anderen nicht beeinflusst.
BAUSTEINE = ((_k1_umfang, True), (_k2_offene_stellen, False), (_k3_status, False), (_k4_belege, False), (_k4_quelle, False),
             (_k5_suche, False), (_k6_pdf, False), (_k7_mail, True), (_k8_score, False), (_herkunft, False))


def _liste(daten, schluessel: str) -> list[dict]:
    return [x for x in ((daten or {}).get(schluessel) or []) if isinstance(x, dict)]


def _waehlen(pool: list[Aufgabe], satz: str, gesperrt: set[str]) -> Aufgabe | None:
    """A nimmt den ersten Kandidaten, B den zweiten. Was im anderen Satz schon gemessen wurde, kommt nicht noch einmal dran."""
    if pool and pool[0].beide:
        return pool[0]
    start = SAETZE.index(satz)
    for kandidat in pool[start:] + pool[:start]:
        if kandidat.param not in gesperrt:
            return kandidat
    return None


def satz_bauen(daten: dict, satz: str, benutzt: dict[str, set[str]] | None = None) -> list[Aufgabe | None]:
    """Aufgaben eines Satzes. None heißt: Für diesen Baustein gibt es in den Daten nichts Lösbares."""
    benutzt = benutzt or {}
    ergebnis = []
    for baustein, feste_reihenfolge in BAUSTEINE:
        pool = baustein(daten)
        if not feste_reihenfolge:
            pool = sorted(pool, key=_rang)
        ergebnis.append(_waehlen(pool, satz, benutzt.get(pool[0].id, set()) if pool else set()))
    return ergebnis


def saetze_pruefen(daten: dict, benutzt: dict[str, dict[str, set[str]]] | None = None) -> dict:
    """Vergleich der Sätze ohne Fragen, Parameter und Lösungen: nur Aufgabenart, ob vorhanden, Verhältnis des Aufwands."""
    benutzt = benutzt or {}
    a, b = (satz_bauen(daten, s, benutzt.get(s)) for s in SAETZE)
    zeilen, probleme = [], []
    for nr, (x, y) in enumerate(zip(a, b, strict=True), 1):
        vorhanden = x or y
        name = vorhanden.id if vorhanden else f"Baustein {nr}"
        verhaeltnis = None
        if not x or not y:
            probleme.append(f"{name}: nicht in beiden Sätzen vorhanden")
        else:
            if x.param == y.param and not x.beide:
                probleme.append(f"{name}: Satz A und B fragen dasselbe")
            verhaeltnis = round(max(x.aufwand, y.aufwand) / max(min(x.aufwand, y.aufwand), 0.5), 2)
            if verhaeltnis >= GRENZE_VERHAELTNIS:
                probleme.append(f"{name}: Aufwand um Faktor {verhaeltnis} verschieden")
        zeilen.append({"aufgabe": name, "kern": vorhanden.kern if vorhanden else "?", "A": bool(x), "B": bool(y),
                       "verhaeltnis": verhaeltnis, "heute_loesbar": vorhanden.heute_loesbar if vorhanden else False})
    return {"zeilen": zeilen, "probleme": probleme}


def nachweis_fehler(aufgabe: Aufgabe, seite: str) -> list[str]:
    """Steht die Lösung wirklich auf der genannten Seite? Prüft den von Jinja maskierten Seitentext. Ohne Inhalte in der Meldung."""
    fehler = []
    for nr, text in enumerate(aufgabe.nachweis):
        gefunden = seite.count(text)
        if gefunden < (aufgabe.mal if nr == 0 else 1):
            fehler.append(f"{aufgabe.id}: Nachweis {nr + 1} {gefunden}-mal auf der Seite")
    return fehler


def _woerter(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.casefold()))


def _datum(text: str) -> tuple[int | None, int, int] | None:
    """(Jahr oder None, Monat, Tag) aus 2026-10-29, 29.10.2026, 29.10.26, 29.10. oder 29.10"""
    iso = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text)
    if iso:
        return int(iso[1]), int(iso[2]), int(iso[3])
    deutsch = re.search(r"\b(\d{1,2})\.\s?(\d{1,2})\.?(?:\s?(\d{4}|\d{2}))?\b", text)
    if deutsch:
        jahr = int(deutsch[3]) if deutsch[3] else None
        return (jahr + 2000 if jahr is not None and jahr < 100 else jahr), int(deutsch[2]), int(deutsch[1])
    return None


def antwort_richtig(art: str, loesung: str, antwort: str) -> bool:
    """Zahl: die erste Zahl zählt. Datum: Tag und Monat, das Jahr nur, wenn angegeben. Text: wenigstens 60 % der Wörter des Titels."""
    if art == "zahl":
        zahl = re.search(r"\d+", antwort)
        return bool(zahl) and int(zahl[0]) == int(loesung)
    if art == "datum":
        gegeben, soll = _datum(antwort), _datum(loesung)
        return bool(gegeben and soll) and gegeben[1:] == soll[1:] and gegeben[0] in (None, soll[0])
    if art == "text":
        woerter = _woerter(loesung)
        return bool(woerter) and len(woerter & _woerter(antwort)) / len(woerter) >= 0.6
    raise ValueError(art)


def log_lesen(text: str) -> list[dict]:
    """Zeilen aus journalctl -o short-unix: Zeit, Methode, Pfad, Status. Alles andere wird übersprungen."""
    eintraege = []
    for zeile in text.splitlines():
        m = AUFRUF.match(zeile)
        if m:
            eintraege.append({"zeit": int(m[1]), "methode": m[2], "pfad": m[3], "status": int(m[4])})
    return eintraege


def im_fenster(eintraege: list[dict], beginn: float, ende: float) -> list[dict]:
    """Aufrufe in [beginn, ende], ohne CSS und Co. Das Log hat ganze Sekunden, deshalb zählt die Startsekunde mit."""
    return [e for e in eintraege if int(beginn) <= e["zeit"] <= ende and not e["pfad"].startswith(NICHT_GEZAEHLT)]


def bewerten(aufgabe: Aufgabe, antwort: str, aufrufe: list[dict] | None) -> str:
    """richtig, falsch oder aufgegeben; ungeprueft, wenn das Log fehlt und nur das Log es zeigen könnte."""
    if not antwort.strip():
        return "aufgegeben"
    if aufgabe.art != "log":
        return "richtig" if antwort_richtig(aufgabe.art, aufgabe.loesung, antwort) else "falsch"
    if aufrufe is None:
        return "ungeprueft"
    return "richtig" if any(e["pfad"] == aufgabe.seite and e["status"] in (200, 206, 304) for e in aufrufe) else "falsch"


def zusammenfassen(ergebnisse: list[dict]) -> dict:
    """Kennzahlen eines Satzes. Der Median ist robuster als der Schnitt, wenn eine Frage aus dem Rahmen fällt."""
    zaehler = {w: sum(e["bewertung"] == w for e in ergebnisse) for w in ("richtig", "falsch", "aufgegeben", "ungeprueft")}
    sekunden = [e["sekunden"] for e in ergebnisse]
    aufrufe = [e["aufrufe"] for e in ergebnisse if e["aufrufe"] is not None]
    loesbar = [e for e in ergebnisse if e["heute_loesbar"]]
    richtig_loesbar = sum(e["bewertung"] == "richtig" for e in loesbar)
    return {**zaehler, "gestellt": len(ergebnisse), "loesbar_gestellt": len(loesbar), "richtig_von_loesbar": richtig_loesbar,
            "sekunden_gesamt": round(sum(sekunden), 1), "sekunden_median": round(statistics.median(sekunden), 1) if sekunden else None,
            "aufrufe_gesamt": sum(aufrufe) if aufrufe else None, "aufrufe_median": statistics.median(aufrufe) if aufrufe else None}


def benutzte_parameter(ordner: Path, satz: str) -> dict[str, set[str]]:
    """Parameter, die in Messungen der anderen Sätze schon vorkamen, je Aufgabe."""
    benutzt: dict[str, set[str]] = {}
    for pfad in sorted(ordner.glob("*.json")):
        daten = _json(pfad)
        if daten and daten.get("satz") != satz:
            for e in daten.get("ergebnisse") or []:
                benutzt.setdefault(e.get("aufgabe"), set()).add(e.get("param"))
    return benutzt


def fertige_messung(ordner: Path, satz: str) -> bool:
    return any((_json(p) or {}).get("satz") == satz and (_json(p) or {}).get("fertig") for p in ordner.glob("*.json"))


def _json(pfad: Path):
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError) as fehler:
        print(f"Nicht lesbar: {pfad.name}: {fehler}", file=sys.stderr)
        return None


def _schreiben(pfad: Path, daten: dict) -> None:
    """Erst Temp-Datei, dann umbenennen. Ordner 700, Datei 600."""
    pfad.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = pfad.with_suffix(".tmp")
    temp.touch(mode=0o600)
    temp.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(temp, pfad)


def daten_laden() -> dict:
    return {"expose": ablage.expose_lesen(UNI, PROJEKT), "geprueft": ablage.geprueft_lesen(UNI, PROJEKT),
            "schriftverkehr": ablage.schriftverkehr_lesen(UNI, PROJEKT), "plan": ablage.plan_lesen(UNI, MODUL),
            "pdf": bool(ablage.fassung_pfad(UNI, PROJEKT, "pdf"))}


def _fingerabdruck(daten: dict) -> str:
    return hashlib.sha256(json.dumps(daten, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _journal(beginn: float, ende: float) -> str | None:
    """Log des Dienstes im Zeitraum. None, wenn journalctl nicht geht: dann fehlen die Aufrufe, das wird gesagt."""
    befehl = ["journalctl", "--user", "-u", DIENST, "--no-pager", "-o", "short-unix", "--since", f"@{int(beginn)}", "--until", f"@{int(ende) + 1}"]
    try:
        lauf = subprocess.run(befehl, capture_output=True, text=True, errors="replace", timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as fehler:
        print(f"journalctl geht nicht: {fehler}", file=sys.stderr)
        return None
    if lauf.returncode != 0:
        print(f"journalctl meldet Fehler: {lauf.stderr.strip()[:200]}", file=sys.stderr)
        return None
    return lauf.stdout


def befehl_pruefen() -> int:
    """Nur Aufgabenarten und Verhältnisse. Bewusst ohne Fragen und Lösungen, das darf auch Jan sehen."""
    daten = daten_laden()
    bericht = saetze_pruefen(daten, {s: benutzte_parameter(ORDNER, s) for s in SAETZE})
    for z in bericht["zeilen"]:
        vergleich = "Aufwand gleich" if z["verhaeltnis"] == 1 else f"Aufwand Faktor {z['verhaeltnis']}"
        hinweis = "" if z["heute_loesbar"] else ", heute auf der Seite nicht lösbar"
        print(f"{z['kern']} {z['aufgabe']:9} A:{'ja' if z['A'] else 'NEIN'} B:{'ja' if z['B'] else 'NEIN'} {vergleich}{hinweis}")
    for p in bericht["probleme"]:
        print("PROBLEM:", p)
    return 1 if any("nicht in beiden" in p or "dasselbe" in p for p in bericht["probleme"]) else 0


EINLEITUNG = """Messung des Portals, Satz {satz}: {n} Aufgaben, voraussichtlich 10 bis 20 Minuten.

So geht es:
- Öffne das Portal im Browser wie immer und arbeite dort. Strg+F ist erlaubt, alles, was du sonst auch tun würdest.
- Schick nichts ab und bewerte keine Karten, das würde echte Daten ändern.
- Eine Frage nach der anderen. Die Zeit läuft ab der Frage bis Enter. Antwort kurz eintippen.
- Leere Antwort = aufgegeben. Das ist ein gültiges Ergebnis, kein Versagen: Gemessen wird das Portal, nicht du.
  Wenn du nach kurzem Suchen meinst, es geht nicht, dann gib auf.
- Nebenher bitte keine anderen Portal-Seiten. Die Lösungen kommen erst nach dem letzten Satz der Messung.
"""


def befehl_messen(satz: str, nochmal: bool = False) -> int:
    if fertige_messung(ORDNER, satz) and not nochmal:
        print(f"Satz {satz} ist schon gemessen. Eine Wiederholung taugt wenig, weil du die Fragen kennst. Absichtlich: --nochmal")
        return 1
    daten = daten_laden()
    satzliste = satz_bauen(daten, satz, benutzte_parameter(ORDNER, satz))
    if not all(satzliste):
        print(f"Satz {satz} ist nicht vollständig, Messung nicht gestartet. Bitte `messung.py pruefen` ansehen.")
        return 1
    if _journal(time.time() - 60, time.time()) is None:
        print("Ohne Log des Dienstes fehlen die Seitenaufrufe, Messung nicht gestartet.")
        return 1
    print(EINLEITUNG.format(satz=satz, n=len(satzliste)))
    print("Geht nicht und wird deshalb nicht gefragt:", "; ".join(GEHT_NICHT))
    input("\nPortal offen? Dann Enter, und die erste Frage erscheint. ")

    ergebnisse: list[dict] = []
    beginn = time.time()
    pfad = ORDNER / f"{satz}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    fingerabdruck = _fingerabdruck(daten)
    kopf = {"satz": satz, "beginn": datetime.fromtimestamp(beginn).isoformat(timespec="seconds"), "wiederholung": nochmal, "geht_nicht": list(GEHT_NICHT)}
    abgebrochen = False
    try:
        for nr, aufgabe in enumerate(satzliste, 1):
            print(f"\nFrage {nr} von {len(satzliste)}\n{aufgabe.frage}")
            start = time.time()
            antwort = input("Antwort (leer = aufgegeben): ").encode("utf-8", "replace").decode()
            ende = time.time()
            ergebnisse.append({"aufgabe": aufgabe.id, "kern": aufgabe.kern, "frage": aufgabe.frage, "param": aufgabe.param, "loesung": aufgabe.loesung,
                               "seite": aufgabe.seite, "heute_loesbar": aufgabe.heute_loesbar, "antwort": antwort.strip(), "start": start, "ende": ende,
                               "sekunden": round(ende - start, 1)})
            _schreiben(pfad, {**kopf, "fertig": False, "ergebnisse": [{**e, "bewertung": "offen", "aufrufe": None} for e in ergebnisse]})
    except (KeyboardInterrupt, EOFError):
        abgebrochen = True
        print("\nAbgebrochen. Ausgewertet wird, was bis hier beantwortet ist.")

    time.sleep(2)  # das Journal bekommt die letzten Zeilen leicht verzögert
    text = _journal(beginn, time.time())
    eintraege = log_lesen(text) if text is not None else None
    fremde_posts = 0
    for e in ergebnisse:
        fenster = im_fenster(eintraege, e["start"], e["ende"]) if eintraege is not None else None
        aufgabe = next(a for a in satzliste if a.frage == e["frage"])
        e["bewertung"] = bewerten(aufgabe, e["antwort"], fenster)
        e["aufrufe"] = len(fenster) if fenster is not None else None
        e["seiten"] = [x["pfad"] for x in fenster] if fenster is not None else None
        fremde_posts += sum(x["methode"] != "GET" for x in fenster or [])
    zusammenfassung = zusammenfassen(ergebnisse)
    zusammenfassung["nicht_get"] = fremde_posts
    daten_gleich = _fingerabdruck(daten_laden()) == fingerabdruck
    _schreiben(pfad, {**kopf, "ende": datetime.now().isoformat(timespec="seconds"), "fertig": not abgebrochen, "daten_gleich": daten_gleich,
                      "log_vorhanden": eintraege is not None, "zusammenfassung": zusammenfassung, "ergebnisse": ergebnisse})

    print(f"\nErgebnis Satz {satz}\n")
    for e in ergebnisse:
        print(f"{e['kern']} {e['aufgabe']:9} {e['bewertung']:10} {e['sekunden']:7.1f} s  {e['aufrufe'] if e['aufrufe'] is not None else '?':>3} Aufrufe  "
              f"Antwort: {e['antwort'] or '-'}  Lösung: {e['loesung']}")
    print(f"\nRichtig {zusammenfassung['richtig']} von {zusammenfassung['gestellt']}, aufgegeben {zusammenfassung['aufgegeben']}, Gesamtzeit "
          f"{zusammenfassung['sekunden_gesamt']} s, Aufrufe {zusammenfassung['aufrufe_gesamt']}.")
    if not daten_gleich:
        print("Achtung: Die Daten haben sich während der Messung geändert (zum Beispiel neue Fassung).")
    if eintraege is None:
        print("Achtung: Das Log war nicht lesbar, Seitenaufrufe fehlen.")
    if fremde_posts:
        print(f"Achtung: {fremde_posts} Aufrufe waren kein GET. Bitte prüfen, ob dabei etwas geändert wurde.")
    print(f"\nGespeichert in {pfad}")
    return 0


def main(argv: list[str]) -> int:
    for strom in (sys.stdout, sys.stderr):
        strom.reconfigure(encoding="utf-8", errors="replace")
    if argv[:1] == ["pruefen"] and len(argv) == 1:
        return befehl_pruefen()
    if argv[:1] and argv[0] in SAETZE and argv[1:] in ([], ["--nochmal"]):
        return befehl_messen(argv[0], nochmal=bool(argv[1:]))
    print("Aufruf: messung.py pruefen | A | B [--nochmal]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
