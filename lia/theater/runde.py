"""Eine Runde für Lias Fassung: Szenenkarte, Ablauf mit Spielfassung, Szenenaufgabe Stück im Stück.

Aufruf von Hand (kein Dienst): AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python runde.py [ordner]
(mit ordner, z. B. runde-20261029-140740: abgebrochene Runde fortsetzen, geprüfte Antworten werden übernommen)
Ablauf (Plan Jan 29.10.2026):
1. Vorbereiten ohne Claude: Stücktext zerlegen (stueck.py), nummerierte Teile, Lias Vorgaben, ausgewählte
   Grundlagen und Kapitel aus Lias Fachbuch (buch.py) nach data/runde-<zeit>/kontext/ (Claude liest nur im
   Agent-Ordner).
2. Szenenkarte (karte.py) und Ablauf (fassung.py) in einer Sitzung, Szenenaufgabe (aufgabe.py) in einer neuen,
   kleinen Sitzung (nur der Ablauf, nicht das Stück). Opus, je höchstens eine Nachbesserung, danach Abbruch.
3. Python baut die vier Dokumente nach data/runde-<zeit>/fuer-lia/ und meldet Jan das Ergebnis (Vorschau,
   erst danach geht es an Lia).
Kostengrenze 5 USD je Aufruf (Jan, 29.10.2026). Fehler: loggen und Meldung an Jan, nie still.
"""

import json
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

import aufgabe
import buch
import fassung
import karte
import stueck
from agentkit import claude_lauf, config, log, meldungen

AGENT = "theater"
HIER = Path(__file__).resolve().parent
logger = log.hole_logger(HIER, AGENT)
GRENZE_USD = 5.0
DOKUMENTE = ("1 Szenenkarte.docx", "2 Ablauf und Varianten.docx", "3 Spielfassung.docx",
             "4 Szenenaufgabe Stück im Stück.docx")


@dataclass
class Pfade:
    hier: Path = HIER
    vorgaben: Path = HIER / "theater.toml"
    nachricht: Path = HIER / "data" / "vorgaben" / "nachricht.md"  # Lias Nachricht mit Konzept und Unsicherheit
    texte: Path = HIER / "data" / "text"  # Textfassungen von Lias Dateien
    profil: Path = HIER / "profil.toml"


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
    meldungen.melden(AGENT, f"Lia, Agent theater: {text}", basis=basis or config.KONTINGENT_DIR / "meldungen")


def claude_laufen(prompt: str, sitzung: str | None = None):
    return claude_lauf.laufen(AGENT, HIER, prompt, art="anspruchsvoll", sitzung_fortsetzen=sitzung)


def textdatei(texte: Path, teilname: str) -> Path:
    """Die Textfassung in `texte`, deren Name `teilname` enthält (genau eine)."""
    treffer = [p for p in sorted(texte.glob("*.txt")) if teilname in p.name]
    if len(treffer) != 1:
        raise RundenFehler(f"{len(treffer)} Textfassungen mit „{teilname}“ in {texte}, erwartet genau eine")
    return treffer[0]


def lesbarer_name(name: str) -> str:
    """Dateinamen aus Lias Zip sind als cp437 gelesen (Mac-Umlaute zerlegt): zurück nach UTF-8, wenn möglich."""
    import unicodedata
    try:
        name = name.encode("cp437").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return unicodedata.normalize("NFC", name)


def vorgaben_text(v: dict, nachricht: str, gedanken: str, figuren: str) -> str:
    r = v["rahmen"]
    zeilen = ["# Lias Vorgaben", "", "## Rahmen",
              f"- {r['minuten_min']}–{r['minuten_max']} Minuten, {r['spieler']} SuS, {r['einheiten']}",
              "- Die SuS kennen: " + ", ".join(r["koennen"]),
              "- Zeitplan: " + "; ".join(f"{t['name']} {t['minuten']} Min" for t in r["teile"]),
              "", "## Muss-Liste (ids für deine Antwort)"]
    zeilen += [f"- {m['id']} (Teil {m['akt']}): {m['text']}" for m in v["muss"]]
    zeilen += ["", "## Lias Nachricht (29.10.2026)", nachricht.strip(),
               "", "## Lias Notizen: Erste Gedanken", gedanken.strip(),
               "", "## Lias Notizen: Figuren und Zeitplan", figuren.strip()]
    return "\n".join(zeilen) + "\n"


def vorbereiten(pfade: Pfade, ordner: Path) -> tuple[dict, list[stueck.Einheit], dict]:
    """Kontextdateien für Claude. Rückgabe: Vorgaben, Einheiten, Pfade der Kontextdateien (relativ zu hier)."""
    v = tomllib.loads(pfade.vorgaben.read_text(encoding="utf-8"))
    einheiten = stueck.zerlegen((pfade.hier / v["stueck"]["textfassung"]).read_text(encoding="utf-8"))
    kontext = ordner / "kontext"
    kontext.mkdir(parents=True, exist_ok=True)
    (ordner / "einheiten.json").write_text(json.dumps(stueck.als_dicts(einheiten), ensure_ascii=False), encoding="utf-8")
    teile = []
    for i, t in enumerate(stueck.nummeriert(einheiten), 1):
        p = kontext / f"stueck-teil-{i}.txt"
        p.write_text(t + "\n", encoding="utf-8")
        teile.append(p)
    vorgaben = kontext / "vorgaben.md"
    vorgaben.write_text(vorgaben_text(v, pfade.nachricht.read_text(encoding="utf-8"),
                                      textdatei(pfade.texte, "Erste_Gedanken").read_text(encoding="utf-8"),
                                      textdatei(pfade.texte, "eingang__Figuren").read_text(encoding="utf-8")),
                        encoding="utf-8")
    teile_grundlagen = []
    for name in v["kontext"]["dateien"]:
        p = textdatei(pfade.texte, name)
        kurz = lesbarer_name(p.name.removesuffix(".txt").rsplit("__", 1)[-1])
        teile_grundlagen.append(f"## {kurz}\n{p.read_text(encoding='utf-8').strip()}")
    grundlagen = kontext / "grundlagen.md"
    grundlagen.write_text("# Lias DS-Grundlagen (Infoblätter und Aufgaben)\n\n" + "\n\n".join(teile_grundlagen) + "\n",
                          encoding="utf-8")
    b = v["buch"]
    pfad = pfade.hier / b["textfassung"]
    if not pfad.exists():
        raise RundenFehler(f"Textfassung des Buchs fehlt: {pfad}")
    try:
        buch_teile = buch.auszug(pfad.read_text(encoding="utf-8"), b["bereiche"], b["versatz"], b["titel"])
    except buch.BuchFehler as e:
        raise RundenFehler(f"Buchauszug: {e}") from None
    buch_pfade = []
    for i, t in enumerate(buch_teile, 1):
        p = kontext / f"buch-teil-{i}.md"
        p.write_text(t, encoding="utf-8")
        buch_pfade.append(p)
    rel = {"teile": [str(p.relative_to(pfade.hier)) for p in teile],
           "vorgaben": str(vorgaben.relative_to(pfade.hier)), "grundlagen": str(grundlagen.relative_to(pfade.hier)),
           "schema": v["kontext"]["schema"], "buch": [str(p.relative_to(pfade.hier)) for p in buch_pfade]}
    return v, einheiten, rel


def _lauf_mit_pruefung(laufen, kosten: Kosten, wofuer: str, erster_prompt: str, ausgabe: Path, pruefen,
                       sitzung: str | None) -> tuple[dict, str | None]:
    """Ein Lauf, Antwort lesen und prüfen, höchstens eine Nachbesserung in derselben Sitzung."""
    kosten.vorher()
    erg = laufen(erster_prompt, sitzung)
    kosten.dazu(erg, wofuer)
    sitzung = erg.sitzung or sitzung
    try:
        daten = karte.antwort_lesen(ausgabe)
        fehler = pruefen(daten)
    except karte.AntwortFehler as e:
        daten, fehler = {}, [str(e)]
    if fehler:
        logger.warning("%s: %d Fehler, eine Nachbesserung: %s", wofuer, len(fehler), fehler)
        kosten.vorher()
        erg = laufen(karte.nachbesserung_prompt(fehler, str(ausgabe)), sitzung)
        kosten.dazu(erg, f"{wofuer} (Nachbesserung)")
        try:
            daten = karte.antwort_lesen(ausgabe)
        except karte.AntwortFehler as e:
            raise RundenFehler(f"{wofuer} nach Nachbesserung: {e}") from None
        fehler = pruefen(daten)
        if fehler:
            raise RundenFehler(f"{wofuer} nach Nachbesserung noch fehlerhaft: " + "; ".join(fehler))
    return daten, sitzung


def _schritt(laufen, kosten: Kosten, wofuer: str, erster_prompt: str, ausgabe: Path, pruefen,
             sitzung: str | None) -> tuple[dict, str | None]:
    """Wie _lauf_mit_pruefung; liegt die Antwort schon geprüft vor (fortgesetzte Runde), wird sie übernommen."""
    if ausgabe.exists():
        try:
            daten = karte.antwort_lesen(ausgabe)
            if not pruefen(daten):
                logger.info("%s: vorhandene Antwort %s übernommen, kein Claude-Lauf", wofuer, ausgabe.name)
                return daten, sitzung
        except karte.AntwortFehler:
            pass
    return _lauf_mit_pruefung(laufen, kosten, wofuer, erster_prompt, ausgabe, pruefen, sitzung)


def bauen(ordner: Path, beschreibungen: list[dict], profil: dict, renderer_bauen=None) -> list[Path]:
    """Dokumente für Lia. Ist eine von Python gebaute Beschreibung ungültig, ist das ein Fehler im Agenten."""
    if renderer_bauen is None:
        import renderer
        renderer_bauen = renderer.bauen
    ziel = ordner / "fuer-lia"
    ziel.mkdir(exist_ok=True)
    dateien = []
    for name, b in zip(DOKUMENTE, beschreibungen, strict=True):
        (ziel / name.replace(".docx", ".json")).write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
        try:
            erg = renderer_bauen(b, ziel / name, profil=profil)
        except ValueError as e:  # BeschreibungUngueltig ist ein ValueError
            raise RundenFehler(f"{name}: Renderer lehnt die Beschreibung ab: {e}") from None
        for h in getattr(erg, "hinweise", []):
            logger.warning("%s: %s", name, h)
        dateien.append(ziel / name)
    return dateien


def runde(pfade: Pfade | None = None, laufen=claude_laufen, renderer_bauen=None, fortsetzen: str | None = None) -> dict:
    """Führt eine Runde aus. Rückgabe: Zusammenfassung für die Meldung. Fehler: RundenFehler u. a.

    fortsetzen: Name eines Ordners in data/ (z. B. nach Abbruch an der Kostengrenze). Schon geprüfte Antworten
    werden übernommen, nur fehlende Schritte laufen. Eine neue Sitzung, weil die alte nicht mehr fortgesetzt wird.
    """
    pfade = pfade or Pfade()
    if fortsetzen:
        ordner = pfade.hier / "data" / fortsetzen
        if not (ordner / "einheiten.json").exists():
            raise RundenFehler(f"{ordner} ist keine angefangene Runde")
    else:
        ordner = pfade.hier / "data" / f"runde-{time.strftime('%Y%m%d-%H%M%S')}"
    v, einheiten, rel = vorbereiten(pfade, ordner)
    titel, muss, rahmen = v["stueck"]["titel"], v["muss"], v["rahmen"]
    kosten = Kosten()
    rel_ordner = ordner.relative_to(pfade.hier)

    k, sitzung = _schritt(
        laufen, kosten, "Szenenkarte",
        karte.prompt(str(rel_ordner / "szenenkarte.json"), rel["teile"], rel["vorgaben"], rel["grundlagen"],
                     rel["schema"], rel["buch"]),
        ordner / "szenenkarte.json", lambda d: karte.pruefen(d, einheiten, muss), None)
    f, sitzung = _schritt(
        laufen, kosten, "Ablauf", fassung.prompt(str(rel_ordner / "ablauf.json"), rahmen),
        ordner / "ablauf.json", lambda d: fassung.pruefen(d, einheiten, muss, rahmen), sitzung)
    # Eigene, kleine Sitzung: die Fortsetzung schickt sonst den ganzen Stücktext noch einmal mit (Lauf 29.10.:
    # Ablauf in derselben Sitzung 3,27 USD)
    a, _ = _schritt(
        laufen, kosten, "Szenenaufgabe",
        aufgabe.prompt(str(rel_ordner / "stueck_im_stueck.json"), rel["vorgaben"], rel["grundlagen"],
                       aufgabe.ablauf_kurz(f), aufgabe.format_abschnitte(), rel["buch"]),
        ordner / "stueck_im_stueck.json", aufgabe.pruefen, None)

    fassung.schreiben_text(ordner / "spielfassung.txt", f, einheiten)
    profil = tomllib.loads(pfade.profil.read_text(encoding="utf-8"))
    dateien = bauen(ordner, [karte.beschreibung(k, einheiten, muss, titel),
                             fassung.ablauf(f, einheiten, muss, rahmen, titel),
                             fassung.spielfassung(f, einheiten, rahmen, titel), a], profil, renderer_bauen)
    nach_nr = {e.nr: e for e in einheiten}
    behalten = sum(len(fassung.behalten(b)) for b in f["bausteine"])
    return {
        "ordner": str(ordner / "fuer-lia"), "usd": kosten.summe, "sitzung": sitzung, "dateien": [d.name for d in dateien],
        "anlaesse": len(k["anlaesse"]), "bausteine": len(f["bausteine"]),
        "minuten": sum(b["minuten"] for b in f["bausteine"]),
        "behalten": behalten, "einheiten": len(einheiten),
        "sprechminuten": stueck.sprechminuten([nach_nr[n] for b in f["bausteine"] for n in fassung.behalten(b)]),
    }


def melden_text(z: dict) -> str:
    return (f"Runde fertig ({z['usd']:.2f} USD). Szenenkarte mit {z['anlaesse']} Spielanlässen, Ablauf mit "
            f"{z['bausteine']} Bausteinen für {z['minuten']:g} Minuten. Vom Original bleiben {z['behalten']} von "
            f"{z['einheiten']} Einheiten (etwa {z['sprechminuten']:.0f} Min Sprechzeit). Dokumente zur Vorschau in "
            f"{z['ordner']}: " + ", ".join(z["dateien"]) + ". Noch nicht an Lia geschickt.")


def main(argv: list[str] | None = None, melden=jan_melden) -> int:
    """Ohne Argument eine neue Runde, mit Ordnername (z. B. runde-20261029-140740) Fortsetzung."""
    argv = sys.argv[1:] if argv is None else argv
    try:
        z = runde(fortsetzen=argv[0]) if argv else runde()
    except Exception as e:  # jeder Abbruch muss bei Jan ankommen
        logger.exception("Runde abgebrochen")
        melden(f"Runde abgebrochen: {e}")
        return 1
    logger.info("Runde fertig: %s", z)
    melden(melden_text(z))
    print(melden_text(z))
    return 0


if __name__ == "__main__":
    sys.exit(main())
