"""Runde 1 der Examensreihe: drei Grobskizzen (skizzen.py), Prüfer-Lauf (pruefer.py), Version (versionen.py).

Aufruf von Hand (noch kein Timer): AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python runde.py
Ablauf:
1. Grundlagen laden (grundlagen.py), Reihe aus lia/unterricht/reihen.toml, Quellen aus dem Register von
   lia/recherche, Lias Regeln und Leitfaden aus lia/unterricht (alles nur gelesen).
2. Skizzen-Lauf (Opus): Claude schreibt data/reihe/runde-1/skizzen.json, Python prüft. Fehler gehen einmal an
   Claude zurück (dieselbe Sitzung), danach Abbruch.
3. Prüfer-Lauf (Opus, neue Sitzung): pruefung.json, Python prüft, ebenso einmal Nachbesserung.
4. bericht.md (Skizzen + Bewertung + Kolloquiumsfragen), Commit im Repo data/reihe/, Meldung an Jan.
Kostengrenze 8 USD je Aufruf (Jan, 25.10.2026). Fehler: loggen und Meldung an Jan, nie still.
"""

import json
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import grundlagen
import pruefer
import skizzen
import versionen
from agentkit import claude_lauf, config, log, meldungen

AGENT = "examen"
HIER = Path(__file__).resolve().parent
logger = log.hole_logger(HIER, AGENT)
GRENZE_USD = 8.0


@dataclass
class Pfade:
    hier: Path = HIER
    repo: Path = HIER / "data" / "reihe"
    reihen: Path = HIER.parent / "unterricht" / "reihen.toml"  # gehört lia/unterricht, nur gelesen
    regeln: Path = HIER.parent / "unterricht" / "STATUS.md"  # Abschnitt „Gelernte Regeln“
    leitfaden: Path = HIER.parent / "unterricht" / "leitfaden.md"
    register: Path = HIER.parent / "recherche" / "data" / "register.json"  # gehört lia/recherche
    vorbild: Path = HIER / "seminar_vorbild.md"  # Beobachtungen aus Beispielen des Fachseminars


class RundenFehler(Exception):
    """Runde abgebrochen. Der Text ist für Jan."""


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


def reihe_text(pfad: Path, titel: str) -> str:
    """Die Reihe aus reihen.toml, deren titel mit `titel` beginnt, als Text."""
    reihen = tomllib.loads(pfad.read_text(encoding="utf-8")).get("reihe", [])
    treffer = [r for r in reihen if str(r.get("titel", "")).startswith(titel)]
    if len(treffer) != 1:
        raise RundenFehler(f"{pfad.name}: {len(treffer)} Reihen mit Titel „{titel}…“, erwartet genau eine")
    zeilen = []
    for k, v in treffer[0].items():
        zeilen.append(f"- {k}: " + ("; ".join(v) if isinstance(v, list) else str(v)))
    return "\n".join(zeilen)


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
    titel = examen.get("reihe", {}).get("titel_in_reihen_toml", "")
    if not titel:
        raise RundenFehler("examen.toml: [reihe] titel_in_reihen_toml fehlt")
    quellen = skizzen.quellen_aus_register(json.loads(pfade.register.read_text(encoding="utf-8")))
    if not quellen:
        raise RundenFehler(f"Keine verwendbaren Quellen im Register {pfade.register}")
    kontext = skizzen.kontext(rubrik, rlp, examen, reihe_text(pfade.reihen, titel), quellen,
                              abschnitt(pfade.regeln, "Gelernte Regeln"), pfade.leitfaden.read_text(encoding="utf-8"),
                              pfade.vorbild.read_text(encoding="utf-8") if pfade.vorbild.exists() else "")

    ordner = pfade.repo / "runde-1"
    ordner.mkdir(parents=True, exist_ok=True)
    kosten = Kosten()
    rlp_ids, refs = {s["id"] for s in rlp}, set(quellen)

    ausgabe = ordner / "skizzen.json"
    sk = _lauf_mit_pruefung(
        laufen, kosten, "Skizzen", skizzen.prompt(kontext, str(ausgabe), examen), ausgabe,
        skizzen.antwort_lesen, lambda d: skizzen.pruefen(d, rlp_ids, refs, examen), skizzen.nachbesserung_prompt)
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


def main(melden=jan_melden) -> int:
    try:
        z = runde_eins()
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
