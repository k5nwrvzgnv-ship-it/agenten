"""Runde 1 der Examensreihe: drei Grobskizzen (skizzen.py), Prüfer-Lauf (pruefer.py), Version (versionen.py).

Aufruf von Hand (noch kein Timer): AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python runde.py
Ablauf:
1. Grundlagen laden (grundlagen.py), Reihe aus lia/instanz/reihen.toml über agentkit.struktur (die eine Reihe
   mit einer Stunde mit Marke „Prüfung“), Quellen aus dem Register von lia/recherche, Lias Regeln und Leitfaden
   aus lia/unterricht (alles nur gelesen). Keine oder mehrere Prüfungsreihen bzw. -stunden: kein Lauf, Meldung an
   Jan nur, wenn sich dieser Zustand seit der letzten Meldung geändert hat (data/zustand.json).
2. Skizzen-Lauf (Opus): Claude schreibt data/reihe/runde-1/skizzen.json, Python prüft. Fehler gehen einmal an
   Claude zurück (dieselbe Sitzung), danach Abbruch.
3. Prüfer-Lauf (Opus, neue Sitzung): pruefung.json, Python prüft, ebenso einmal Nachbesserung.
4. bericht.md (Skizzen + Bewertung + Kolloquiumsfragen), Commit im Repo data/reihe/, Meldung an Jan.
Kostengrenze 8 USD je Aufruf (Jan, 25.10.2026). Fehler: loggen und Meldung an Jan, nie still.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import grundlagen
import pruefer
import skizzen
import versionen
from agentkit import claude_lauf, config, log, meldungen, struktur

AGENT = "examen"
HIER = Path(__file__).resolve().parent
logger = log.hole_logger(HIER, AGENT)
GRENZE_USD = 8.0


@dataclass
class Pfade:
    hier: Path = HIER
    repo: Path = HIER / "data" / "reihe"
    instanz: Path = struktur.LIA_INSTANZ  # reihen.toml und lerngruppen.toml, nur gelesen über agentkit.struktur
    regeln: Path = HIER.parent / "unterricht" / "STATUS.md"  # Abschnitt „Gelernte Regeln“
    leitfaden: Path = HIER.parent / "unterricht" / "leitfaden.md"
    register: Path = HIER.parent / "recherche" / "data" / "register.json"  # gehört lia/recherche
    vorbild: Path = HIER / "seminar_vorbild.md"  # Beobachtungen aus Beispielen des Fachseminars
    zustand: Path = HIER / "data" / "zustand.json"  # zuletzt gemeldeter Zustand der Reihe


class RundenFehler(Exception):
    """Runde abgebrochen. Der Text ist für Jan."""


class ReiheFehlt(RundenFehler):
    """Keine eindeutige Reihe mit Prüfungsstunde oder reihen.toml kaputt: Lauf findet nicht statt."""


class Kosten:
    def __init__(self, grenze: float = GRENZE_USD):
        self.grenze, self.summe = grenze, 0.0

    def vorher(self):
        if self.summe >= self.grenze:
            raise RundenFehler(f"Kostengrenze {self.grenze:.2f} USD erreicht ({self.summe:.2f} USD)")

    def dazu(self, erg, wofuer: str):
        self.summe += erg.usd or 0
        logger.info("Claude-Lauf %s: %.4f USD, %d Tokens, %.0f s, ok=%s, Summe %.4f USD",
                    wofuer, erg.usd or 0, erg.tokens, erg.dauer_s, erg.ok, self.summe)


def jan_melden(text: str, basis: Path | None = None) -> None:
    """Meldung in Jans Instanz (seine Zentrale), nicht in Lias."""
    meldungen.melden(AGENT, f"Lia, Agent examen: {text}", basis=basis or config.KONTINGENT_DIR / "meldungen")


def claude_laufen(prompt: str, sitzung: str | None = None):
    return claude_lauf.laufen(AGENT, HIER, prompt, art="anspruchsvoll", sitzung_fortsetzen=sitzung)


# Felder der aufgelösten Reihe (agentkit.struktur) für den Kontext; Systemfelder (ids, agenten, archiviert) nicht
REIHE_FELDER = ("fach", "klasse", "schuljahr", "titel", "reihenfrage", "stand", "lerngruppe", "notizen", "behandelt",
                "merksaetze", "bisherige_reihen")


def reihe_finden(instanz: Path) -> tuple[dict, dict]:
    """(Reihe, Prüfungsstunde) aus <instanz>/reihen.toml. Nicht eindeutig oder Datei kaputt: ReiheFehlt."""
    try:
        return grundlagen.pruefungsreihe(struktur.laden(instanz))
    except (grundlagen.ReiheOffen, struktur.StrukturFehler) as e:
        raise ReiheFehlt(str(e)) from None


def reihe_text(reihe: dict, pruefungsstunde: dict) -> str:
    """Die Reihe als Text für den Kontext, die Stunden mit Nummer, die Prüfungsstunde markiert."""
    zeilen = []
    for k in REIHE_FELDER:
        v = reihe.get(k)
        if v:
            zeilen.append(f"- {k}: " + ("; ".join(map(str, v)) if isinstance(v, list) else str(v)))
    zeilen.append(f"- Prüfungsstunde: Stunde {pruefungsstunde['nr']} von {len(reihe['stunden'])} "
                  f"(„{pruefungsstunde['thema']}“)")
    zeilen.append("- Stunden (von Lia eingetragen):")
    for st in reihe["stunden"]:
        marke = " [PRÜFUNGSSTUNDE]" if st["id"] == pruefungsstunde["id"] else (f" [{st['marke']}]" if st["marke"] else "")
        zeilen.append(f"  {st['nr']}. {st['thema']}{marke}")
    return "\n".join(zeilen)


def neu_zu_melden(zustand: Path, text: str) -> bool:
    """Merkt sich den Zustand der Reihe ("" = in Ordnung). True, wenn `text` ein Problem ist, das seit der letzten
    Meldung neu ist; dann muss Jan es erfahren. Gleicher Text wie zuletzt: False (kein Melden bei jedem Lauf)."""
    try:
        bisher = json.loads(zustand.read_text(encoding="utf-8")).get("reihe", "")
    except FileNotFoundError:
        bisher = ""
    except (json.JSONDecodeError, AttributeError):
        logger.warning("%s unlesbar, gilt als leer", zustand)
        bisher = ""
    if text == bisher:
        return False
    zustand.parent.mkdir(parents=True, exist_ok=True)
    zustand.write_text(json.dumps({"reihe": text}, ensure_ascii=False) + "\n", encoding="utf-8")
    return bool(text)


def abschnitt(pfad: Path, ueberschrift: str) -> str:
    """Text unter „## <ueberschrift>“ bis zur nächsten Überschrift gleicher Ebene."""
    text, drin, zeilen = pfad.read_text(encoding="utf-8"), False, []
    for zeile in text.splitlines():
        if zeile.startswith("## "):
            drin = zeile[3:].strip() == ueberschrift
            continue
        if drin:
            zeilen.append(zeile)
    return "\n".join(zeilen).strip()


def _lauf_mit_pruefung(laufen, kosten: Kosten, wofuer: str, erster_prompt: str, ausgabe: Path,
                       lesen, pruefen, nachbessern) -> dict:
    kosten.vorher()
    erg = laufen(erster_prompt)
    kosten.dazu(erg, wofuer)
    daten = lesen(ausgabe)
    fehler = pruefen(daten)
    if fehler:
        logger.warning("%s: %d Fehler, eine Nachbesserung: %s", wofuer, len(fehler), fehler)
        kosten.vorher()
        erg = laufen(nachbessern(fehler, str(ausgabe)), erg.sitzung)
        kosten.dazu(erg, f"{wofuer} (Nachbesserung)")
        daten = lesen(ausgabe)
        fehler = pruefen(daten)
        if fehler:
            raise RundenFehler(f"{wofuer} nach Nachbesserung noch fehlerhaft: " + "; ".join(fehler))
    return daten


def runde_eins(pfade: Pfade | None = None, laufen=claude_laufen, sichern=versionen.sichern) -> dict:
    """Führt Runde 1 aus. Rückgabe: Zusammenfassung (für die Meldung). Fehler: RundenFehler u. a."""
    pfade = pfade or Pfade()
    rubrik, rlp = grundlagen.rubrik_laden(), grundlagen.auszug_laden()
    examen = grundlagen._toml(grundlagen.EXAMEN)
    reihe, ps = reihe_finden(pfade.instanz)
    neu_zu_melden(pfade.zustand, "")  # Reihe wieder eindeutig: ein späteres Problem wird wieder gemeldet
    quellen = skizzen.quellen_aus_register(json.loads(pfade.register.read_text(encoding="utf-8")))
    if not quellen:
        raise RundenFehler(f"Keine verwendbaren Quellen im Register {pfade.register}")
    kontext = skizzen.kontext(rubrik, rlp, examen, reihe_text(reihe, ps), quellen,
                              abschnitt(pfade.regeln, "Gelernte Regeln"), pfade.leitfaden.read_text(encoding="utf-8"),
                              pfade.vorbild.read_text(encoding="utf-8") if pfade.vorbild.exists() else "")

    ordner = pfade.repo / "runde-1"
    ordner.mkdir(parents=True, exist_ok=True)
    kosten = Kosten()
    rlp_ids, refs = {s["id"] for s in rlp}, set(quellen)

    ausgabe = ordner / "skizzen.json"
    sk = _lauf_mit_pruefung(
        laufen, kosten, "Skizzen", skizzen.prompt(kontext, str(ausgabe), examen, ps["nr"]), ausgabe,
        skizzen.antwort_lesen, lambda d: skizzen.pruefen(d, rlp_ids, refs, examen, ps["nr"]),
        skizzen.nachbesserung_prompt)
    rlp_nach_id = {s["id"]: s for s in rlp}
    teile = [skizzen.darstellen(s, rlp_nach_id, quellen) for s in sk["skizzen"]]
    for s, md in zip(sk["skizzen"], teile, strict=True):
        (ordner / f"skizze-{s['kennung']}.md").write_text(md + "\n", encoding="utf-8")

    ausgabe = ordner / "pruefung.json"
    kennungen = [s["kennung"] for s in sk["skizzen"]]
    pr = _lauf_mit_pruefung(
        laufen, kosten, "Prüfer", pruefer.prompt(kontext, "\n\n".join(teile), rubrik, str(ausgabe)), ausgabe,
        pruefer.antwort_lesen, lambda d: pruefer.pruefen(d, rubrik, kennungen), pruefer.nachbesserung_prompt)
    bewertung = {b["kennung"]: b for b in pr["skizzen"]}

    bericht = ["# Runde 1: drei Grobskizzen", "",
               "Annahmen: " + ("; ".join(sk.get("annahmen") or []) or "keine"), "",
               f"Kosten: {kosten.summe:.2f} USD", ""]
    for s, md in zip(sk["skizzen"], teile, strict=True):
        bericht += [md, "", pruefer.darstellen(bewertung[s["kennung"]], rubrik), "", "---", ""]
    (ordner / "bericht.md").write_text("\n".join(bericht), encoding="utf-8")
    commit = sichern(pfade.repo, f"Runde 1: drei Grobskizzen mit Prüfung ({kosten.summe:.2f} USD)")

    return {
        "commit": commit, "usd": kosten.summe, "bericht": str(ordner / "bericht.md"),
        "skizzen": [(s["kennung"], s["titel"], len(pruefer.unter_schwelle(bewertung[s["kennung"]], rubrik)))
                    for s in sk["skizzen"]],
        "kriterien": len(rubrik["kriterium"]),
    }


def melden_text(z: dict) -> str:
    zeilen = [f"Runde 1 fertig ({z['usd']:.2f} USD, Version {z['commit']}). Bericht: {z['bericht']}"]
    zeilen += [f"Skizze {k}: {t} ({u} von {z['kriterien']} Kriterien unter „gut“)" for k, t, u in z["skizzen"]]
    return "\n".join(zeilen)


def main(melden=jan_melden, pfade: Pfade | None = None) -> int:
    pfade = pfade or Pfade()
    try:
        z = runde_eins(pfade)
    except ReiheFehlt as e:
        logger.warning("Runde 1 läuft nicht: %s", e)
        if neu_zu_melden(pfade.zustand, str(e)):
            melden(f"Runde 1 läuft nicht: {e}")
        return 1
    except Exception as e:  # jeder Abbruch muss bei Jan ankommen
        logger.exception("Runde 1 abgebrochen")
        melden(f"Runde 1 abgebrochen: {e}")
        return 1
    logger.info("Runde 1 fertig: %s", z)
    melden(melden_text(z))
    print(melden_text(z))
    return 0


if __name__ == "__main__":
    sys.exit(main())
