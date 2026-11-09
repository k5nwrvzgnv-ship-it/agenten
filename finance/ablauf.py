"""Ablauf einer Recherche: fünf Schritte nacheinander, je Schritt Claude-Lauf, Webquellen auflösen, prüfen,
bei Fehlern nachbessern (ohne agentkit-Import, damit testbar; agent.py übergibt laufen, laden und steht_in).

Fortsetzen: Liegt eine Schritt-Datei schon geprüft vor (z. B. nach LimitErreicht im nächsten Schritt), wird sie
nur neu geprüft und nicht neu erzeugt. Fehler aus laufen (LimitErreicht usw.) gehen an agent.py durch.
"""

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import abrufer
import pruefung
import quellen
import schritte

MAX_VERSUCHE = 3  # erster Lauf und zwei Nachbesserungen je Schritt
MAX_ABFRAGE_LAEUFE = 2  # Primärdaten: Plan und eine Nachbesserung für fehlgeschlagene Abfragen
ABFRAGEN = "abfragen.json"  # schreibt Claude
ABFRAGEN_ERGEBNIS = "abfragen_ergebnis.json"  # schreibt Python; liegt sie vor, ist die Phase erledigt


@dataclass
class Web:
    """Was laden(url) liefert: Rohinhalt zum Ablegen, Text zum Prüfen des Zitats, Dateiendung."""
    inhalt: bytes
    text: str
    endung: str


class WebFehler(Exception):
    """laden(url) konnte die Seite nicht holen oder nicht lesen; Text geht an Claude zur Nachbesserung."""


@dataclass
class SchrittErgebnis:
    nr: int
    ok: bool
    fehler: list[str] = field(default_factory=list)
    hinweise: list[str] = field(default_factory=list)
    annahmen: list[tuple[str, str]] = field(default_factory=list)
    quellen: set[str] = field(default_factory=set)
    laeufe: int = 0
    daten: dict | None = None


def webquellen_aufloesen(daten: dict, quellen_ordner: Path, laden, steht_in) -> list[str]:
    """Ersetzt Webangaben durch Quellen-IDs (in daten). Gibt Fehler zurück; fehlerhafte Angaben bleiben stehen."""
    fehler = []
    geladen: dict[str, Web | str] = {}  # je URL einmal laden
    for obj in schritte.webquellen(daten):
        angabe = obj["quelle"]
        wert = obj.get("wert")
        f = schritte.webangabe_fehler(angabe)
        if f:
            fehler.append(f"Zahl {wert}: {f}")
            continue
        url = angabe["url"]
        if url not in geladen:
            try:
                geladen[url] = laden(url)
            except WebFehler as w:
                geladen[url] = str(w)
        web = geladen[url]
        if isinstance(web, str):
            fehler.append(f"Zahl {wert}, {url}: nicht ladbar ({web})")
            continue
        if not isinstance(wert, (int, float)) or isinstance(wert, bool):
            continue  # meldet pruefung.py
        f = schritte.webquelle_pruefen(wert, angabe["zitat"], web.text, steht_in)
        if f:
            fehler.append(f"Zahl {wert}, {url}: {f}")
            continue
        obj["quelle"] = quellen.speichern(quellen_ordner, "web", url, web.inhalt, angabe["beschreibung"],
                                          endung=web.endung)
    return fehler


def pruefen(nr: int, pfad: Path, quellen_ordner: Path, laden, steht_in, heute: date) -> SchrittErgebnis:
    """Liest, löst Webquellen auf, prüft. Geprüfte Daten (mit IDs statt Webangaben) werden zurückgeschrieben."""
    erg = SchrittErgebnis(nr, ok=False)
    daten, f = schritte.lesen(pfad)
    if f:
        erg.fehler = [f]
        return erg
    erg.fehler += webquellen_aufloesen(daten, quellen_ordner, laden, steht_in)
    erg.fehler += schritte.pflichtfelder(nr, daten, heute)
    p = pruefung.pruefen(daten, quellen_ordner, heute)
    erg.fehler += [f for f in p.fehler if f not in erg.fehler]
    erg.hinweise, erg.annahmen, erg.quellen = p.hinweise, p.annahmen, p.benutzte_quellen
    erg.daten = daten
    # Aufgelöste Webquellen behalten, auch wenn noch Fehler da sind (spart erneutes Laden)
    pfad.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    erg.ok = not erg.fehler
    return erg


def schritt_ausfuehren(s: schritte.Schritt, thema: str, hier: Path, ordner: Path, quellen_ordner: Path,
                       laufen, laden, steht_in, heute: date) -> SchrittErgebnis:
    """laufen(prompt) -> Objekt mit ok und text (agentkit.claude_lauf.Ergebnis)."""
    pfad = ordner / s.datei
    ordner_rel, quellen_rel = str(ordner.relative_to(hier)), str(quellen_ordner.relative_to(hier))
    fehler = None
    if pfad.exists():  # Fortsetzen
        erg = pruefen(s.nr, pfad, quellen_ordner, laden, steht_in, heute)
        if erg.ok:
            return erg
        fehler = erg.fehler
    laeufe = 0
    for _ in range(MAX_VERSUCHE):
        e = laufen(schritte.prompt(s, thema, ordner_rel, quellen_rel, quellen.alle(quellen_ordner), fehler))
        laeufe += 1
        if not e.ok and not pfad.exists():
            # Meist die Grenze der Arbeitsschritte (leerer Text): nächster Versuch mit diesem Hinweis
            erg = SchrittErgebnis(s.nr, ok=False, fehler=[lauf_fehler(e.text)], laeufe=laeufe)
            fehler = erg.fehler
            continue
        erg = pruefen(s.nr, pfad, quellen_ordner, laden, steht_in, heute)
        erg.laeufe = laeufe
        if erg.ok:
            return erg
        fehler = erg.fehler
    return erg


def lauf_fehler(text: str) -> str:
    text = (text or "").strip()
    return (f"Claude-Lauf fehlgeschlagen: {text}" if text else
            "Claude-Lauf ohne Ergebnis abgebrochen, vermutlich Grenze der Arbeitsschritte erreicht: "
            "schreibe die Datei früher und recherchiere weniger")


def primaerdaten(thema: str, hier: Path, ordner: Path, quellen_ordner: Path, laufen, abrufen) -> SchrittErgebnis:
    """Phase zwischen Schritt 1 und 2: Claude plant Abfragen (abfragen.json), Python führt sie aus.

    abrufen(abfrage) -> Quellen-ID, sonst WebFehler oder abrufer.AbfrageFehler (agent.py, über agentkit.abruf).
    Bricht die Recherche nie ab: ohne Primärdaten arbeitet Schritt 2 mit Webquellen und Annahmen.
    """
    erg = SchrittErgebnis(0, ok=True)
    ziel = ordner / ABFRAGEN_ERGEBNIS
    if ziel.exists():  # Fortsetzen
        alt, _ = schritte.lesen(ziel)
        erg.quellen = {e["id"] for e in (alt or {}).get("ergebnisse", []) if e.get("id")}
        return erg
    ordner_rel = str(ordner.relative_to(hier))
    ergebnisse: list[dict] = []
    fehler: list[str] | None = None
    for _ in range(MAX_ABFRAGE_LAEUFE):
        pfad = ordner / ABFRAGEN
        pfad.unlink(missing_ok=True)
        e = laufen(schritte.abfragen_prompt(thema, ordner_rel, fehler))
        erg.laeufe += 1
        daten, f = schritte.lesen(pfad)
        if f:
            fehler = [f if e.ok else lauf_fehler(e.text)]
            erg.hinweise = fehler
            continue
        liste, hinweis = abrufer.abfragen_lesen(daten)
        fehler = [] if liste else hinweis
        for i, abfrage in enumerate(liste):
            try:
                qid = abrufen(abfrage)
                ergebnisse.append({"abfrage": abfrage, "id": qid})
                erg.quellen.add(qid)
            except (WebFehler, abrufer.AbfrageFehler) as w:
                ergebnisse.append({"abfrage": abfrage, "fehler": str(w)})
                fehler.append(f"abfragen[{i}]: {w}")
        erg.hinweise = (hinweis if liste else []) + fehler
        if not fehler:
            break
    ziel.write_text(json.dumps({"ergebnisse": ergebnisse}, ensure_ascii=False, indent=1), encoding="utf-8")
    return erg


def recherche(thema: str, hier: Path, ordner: Path, quellen_ordner: Path, laufen, laden, steht_in,
              heute: date, abrufen=None) -> list[SchrittErgebnis]:
    """Alle Schritte; bricht beim ersten Schritt ab, der auch nach Nachbesserung Fehler hat.

    Mit abrufen (agent.py) zwischen Schritt 1 und 2 die Phase Primärdaten (Ergebnis mit nr 0).
    """
    ordner.mkdir(parents=True, exist_ok=True)
    ergebnisse = []
    for s in schritte.SCHRITTE:
        if s.nr == 2 and abrufen is not None:
            ergebnisse.append(primaerdaten(thema, hier, ordner, quellen_ordner, laufen, abrufen))
        erg = schritt_ausfuehren(s, thema, hier, ordner, quellen_ordner, laufen, laden, steht_in, heute)
        ergebnisse.append(erg)
        if not erg.ok:
            break
    return ergebnisse


def bericht_text(thema: str, ergebnisse: list[SchrittErgebnis], ordner_rel: str) -> str:
    """Kurzer Text für Jan (Telegram); Bericht und Modell hängen an (agent.dokumente)."""
    letzte = ergebnisse[-1]
    zeilen = [f"Recherche: {thema}"]
    if not letzte.ok:
        name = schritte.schritt(letzte.nr).name
        zeilen.append(f"Abgebrochen in Schritt {letzte.nr} ({name}) nach {letzte.laeufe} Läufen. Verbleibende Fehler:")
        zeilen += [f"- {f}" for f in letzte.fehler[:10]]
        if len(letzte.fehler) > 10:
            zeilen.append(f"- ... und {len(letzte.fehler) - 10} weitere")
    else:
        hyp = next((e.daten.get("hypothesen", []) for e in ergebnisse if e.nr == 4 and e.daten), [])
        zeilen.append(f"Fertig, {len(hyp)} Hypothese(n):")
        zeilen += [f"- {h.get('titel')} (Sicherheit: {h.get('sicherheit')})" for h in hyp]
    quellen_ids = set().union(*(e.quellen for e in ergebnisse))
    annahmen = sum(len(e.annahmen) for e in ergebnisse)
    hinweise = sum(len(e.hinweise) for e in ergebnisse)
    primaer = next((e for e in ergebnisse if e.nr == 0), None)
    if primaer:
        zeilen.append(f"Primärdaten: {len(primaer.quellen)} Abfragen abgelegt"
                      + (f", {len(primaer.hinweise)} Hinweise (siehe abfragen_ergebnis.json)." if primaer.hinweise
                         else "."))
    zeilen.append(f"{len(quellen_ids)} Quellen, {annahmen} Annahmen, {hinweise} Zahlen aus Webquellen ohne Rohdaten-"
                  f"abgleich. Läufe: {sum(e.laeufe for e in ergebnisse)}.")
    zeilen.append(f"Bericht (PDF) und Modell (xlsx) im Anhang, Schritt-Dateien in finance/{ordner_rel}/.")
    return "\n".join(zeilen)


def host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()
