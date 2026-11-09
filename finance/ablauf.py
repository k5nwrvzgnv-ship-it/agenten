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

import pruefung
import quellen
import schritte

MAX_VERSUCHE = 3  # erster Lauf und zwei Nachbesserungen je Schritt


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
        if not e.ok:
            return SchrittErgebnis(s.nr, ok=False, fehler=[f"Claude-Lauf fehlgeschlagen: {e.text}"], laeufe=laeufe)
        erg = pruefen(s.nr, pfad, quellen_ordner, laden, steht_in, heute)
        erg.laeufe = laeufe
        if erg.ok:
            return erg
        fehler = erg.fehler
    return erg


def recherche(thema: str, hier: Path, ordner: Path, quellen_ordner: Path, laufen, laden, steht_in,
              heute: date) -> list[SchrittErgebnis]:
    """Alle Schritte; bricht beim ersten Schritt ab, der auch nach Nachbesserung Fehler hat."""
    ordner.mkdir(parents=True, exist_ok=True)
    ergebnisse = []
    for s in schritte.SCHRITTE:
        erg = schritt_ausfuehren(s, thema, hier, ordner, quellen_ordner, laufen, laden, steht_in, heute)
        ergebnisse.append(erg)
        if not erg.ok:
            break
    return ergebnisse


def bericht_text(thema: str, ergebnisse: list[SchrittErgebnis], ordner_rel: str) -> str:
    """Kurzer Text für Jan (Telegram), bis der Renderer den PDF-Bericht kann."""
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
    zeilen.append(f"{len(quellen_ids)} Quellen, {annahmen} Annahmen, {hinweise} Zahlen aus Webquellen ohne Rohdaten-"
                  f"abgleich. Läufe: {sum(e.laeufe for e in ergebnisse)}.")
    zeilen.append(f"Dateien: finance/{ordner_rel}/schritt1.json bis schritt{letzte.nr}.json "
                  "(PDF-Bericht folgt, sobald der Renderer es kann).")
    return "\n".join(zeilen)


def host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()
