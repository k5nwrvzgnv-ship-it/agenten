"""Eine Runde für Lias Fassung: Szenenkarte, Ablauf mit Spielfassung, Szenenaufgabe Stück im Stück.

Aufruf von Hand (kein Dienst): AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python runde.py [ordner]
(mit ordner, z. B. runde-20261029-140740: abgebrochene Runde fortsetzen, geprüfte Antworten werden übernommen)
An Lia nach Jans Durchsicht: runde.py --an-lia <ordner> (die vier docx über Lias Zentrale, ohne Feedback-Knöpfe,
ihre Textantwort ist Feedback; nur einmal je Runde, an_lia.json).
Ablauf (Plan Jan 29.10.2026):
1. Vorbereiten ohne Claude: Stücktext zerlegen (stueck.py), nummerierte Teile, Lias Vorgaben, ausgewählte
   Grundlagen und Kapitel aus Lias Fachbuch (buch.py) nach data/runde-<zeit>/kontext/ (Claude liest nur im
   Agent-Ordner).
2. Szenenkarte (karte.py), Ablauf (fassung.py) und Szenenaufgabe (aufgabe.py) in einer Sitzung (bei einer
   fortgesetzten Runde ohne Sitzung eine neue). Dazwischen der Prüfschritt (kritik.py): ein Prüfer in neuer
   Sitzung bewertet den Ablauf gegen die Rubrik, unter „gut“ überarbeitet der Autor, höchstens zweimal.
   Opus, je höchstens eine Nachbesserung, danach Abbruch.
3. Python baut die vier Dokumente nach data/runde-<zeit>/fuer-lia/ und meldet Jan das Ergebnis (Vorschau,
   erst danach geht es an Lia).
Keine Kostengrenze (Jan 29.10.2026: die Qualität entscheidet); Kosten stehen im Log und in der Meldung.
Fehler: loggen und Meldung an Jan, nie still.
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
import kritik
import stueck
from agentkit import auftraege, claude_lauf, config, log, meldungen

AGENT = "theater"
HIER = Path(__file__).resolve().parent
logger = log.hole_logger(HIER, AGENT)
GRENZE_USD = None  # Jan 29.10.2026: Kosten spielen keine Rolle, die Qualität entscheidet (vorher 5 USD)
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
    """Summe der Läufe fürs Log und die Meldung; grenze None = keine Grenze."""

    def __init__(self, grenze: float | None = GRENZE_USD):
        self.grenze, self.summe = grenze, 0.0

    def vorher(self):
        if self.grenze is not None and self.summe >= self.grenze:
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


def runde(pfade: Pfade | None = None, laufen=claude_laufen, renderer_bauen=None, fortsetzen: str | None = None,
          grenze: float | None = GRENZE_USD) -> dict:
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
    kosten = Kosten(grenze)
    rel_ordner = ordner.relative_to(pfade.hier)

    k, sitzung = _schritt(
        laufen, kosten, "Szenenkarte",
        karte.prompt(str(rel_ordner / "szenenkarte.json"), rel["teile"], rel["vorgaben"], rel["grundlagen"],
                     rel["schema"], rel["buch"]),
        ordner / "szenenkarte.json", lambda d: karte.pruefen(d, einheiten, muss), None)
    f, sitzung = _schritt(
        laufen, kosten, "Ablauf", fassung.prompt(str(rel_ordner / "ablauf.json"), rahmen),
        ordner / "ablauf.json", lambda d: fassung.pruefen(d, einheiten, muss, rahmen), sitzung)
    p = pruefschleife(laufen, kosten, ordner, rel_ordner, rel, f, sitzung, einheiten, muss, rahmen, v)
    f, sitzung = p["ablauf"], p["sitzung"]
    # In derselben Sitzung: Claude kennt dort Stück, Szenenkarte und die Gründe für den Ablauf (Qualität vor
    # Kosten, Jan 29.10.2026). Nur ohne Sitzung (fortgesetzte Runde, Schritte übernommen) eine neue; der Prompt
    # reicht dafür auch allein (Ablauf als Kurzfassung, Vorgaben, Grundlagen und Buch zum Lesen).
    a, sitzung = _schritt(
        laufen, kosten, "Szenenaufgabe",
        aufgabe.prompt(str(rel_ordner / "stueck_im_stueck.json"), rel["vorgaben"], rel["grundlagen"],
                       aufgabe.ablauf_kurz(f), aufgabe.format_abschnitte(), rel["buch"]),
        ordner / "stueck_im_stueck.json", aufgabe.pruefen, sitzung)

    fassung.schreiben_text(ordner / "spielfassung.txt", f, einheiten)
    profil = tomllib.loads(pfade.profil.read_text(encoding="utf-8"))
    ablauf_doc = fassung.ablauf(f, einheiten, muss, rahmen, titel)
    ablauf_doc["bloecke"] += kritik.bloecke(p["kritik"], v, p["ueberarbeitungen"], p["aenderungen"])
    dateien = bauen(ordner, [karte.beschreibung(k, einheiten, muss, titel), ablauf_doc,
                             fassung.spielfassung(f, einheiten, rahmen, titel), a], profil, renderer_bauen)
    (ordner / "ergebnis.json").write_text(json.dumps({"ablauf": p["datei"], "kritik": p["kritik_datei"]},
                                                     ensure_ascii=False), encoding="utf-8")
    nach_nr = {e.nr: e for e in einheiten}
    behalten = sum(len(fassung.behalten(b)) for b in f["bausteine"])
    return {
        "ordner": str(ordner / "fuer-lia"), "usd": kosten.summe, "sitzung": sitzung, "dateien": [d.name for d in dateien],
        "anlaesse": len(k["anlaesse"]), "bausteine": len(f["bausteine"]),
        "minuten": sum(b["minuten"] for b in f["bausteine"]),
        "behalten": behalten, "einheiten": len(einheiten),
        "sprechminuten": stueck.sprechminuten([nach_nr[n] for b in f["bausteine"] for n in fassung.behalten(b)]),
        "ueberarbeitungen": p["ueberarbeitungen"],
        "unter_gut": [b["id"] for b in kritik.unter_schwelle(p["kritik"], v)],
    }


def pruefschleife(laufen, kosten: Kosten, ordner: Path, rel_ordner: Path, rel: dict, f: dict, sitzung: str | None,
                   einheiten: list[stueck.Einheit], muss: list[dict], rahmen: dict, rubrik: dict) -> dict:
    """Prüfer (neue Sitzung) bewertet, Autor (seine Sitzung) überarbeitet, bis alles mindestens „gut“ ist oder
    kritik.MAX_UEBERARBEITUNGEN erreicht sind. Dateien: ablauf.json, kritik-1.json, ablauf-2.json, kritik-2.json, …"""
    version, aenderungen = 1, []
    while True:
        datei = "ablauf.json" if version == 1 else f"ablauf-{version}.json"
        spielfassung = ordner / f"spielfassung-{version}.txt"
        fassung.schreiben_text(spielfassung, f, einheiten)
        kdatei = f"kritik-{version}.json"
        k, _ = _schritt(
            laufen, kosten, f"Prüfung {version}",
            kritik.prompt(str(rel_ordner / kdatei), str(rel_ordner / spielfassung.name), str(rel_ordner / datei),
                          rel["vorgaben"], rel["grundlagen"], rel["buch"], str(rel_ordner / "szenenkarte.json"),
                          rubrik, version),
            ordner / kdatei, lambda d: kritik.pruefen(d, rubrik), None)
        unter = kritik.unter_schwelle(k, rubrik)
        logger.info("Prüfung %d: %d von %d Kriterien unter „%s“ (%s)", version, len(unter), len(k["kriterien"]),
                    rubrik["stufen"]["mindestens"], ", ".join(b["id"] for b in unter))
        if not unter or version > kritik.MAX_UEBERARBEITUNGEN:
            return {"ablauf": f, "sitzung": sitzung, "kritik": k, "ueberarbeitungen": version - 1,
                    "aenderungen": aenderungen, "datei": datei, "kritik_datei": kdatei}
        neu = f"ablauf-{version + 1}.json"
        f, sitzung = _schritt(
            laufen, kosten, f"Überarbeitung {version}",
            kritik.ueberarbeitung_prompt(str(rel_ordner / neu), str(rel_ordner / datei), k, rubrik,
                                         rel["teile"] + [rel["vorgaben"], str(rel_ordner / "szenenkarte.json"),
                                                         rel["grundlagen"]] + rel["buch"]),
            ordner / neu, lambda d: fassung.pruefen(d, einheiten, muss, rahmen) + kritik.aenderungen_pruefen(d),
            sitzung)
        aenderungen += f["aenderungen"]
        version += 1


def melden_text(z: dict) -> str:
    pruefung = ("alle Kriterien mindestens „gut“" if not z["unter_gut"] else
                "noch unter „gut“: " + ", ".join(z["unter_gut"]))
    return (f"Runde fertig ({z['usd']:.2f} USD). Szenenkarte mit {z['anlaesse']} Spielanlässen, Ablauf mit "
            f"{z['bausteine']} Bausteinen für {z['minuten']:g} Minuten, {z['ueberarbeitungen']}-mal nach Prüfung "
            f"überarbeitet, {pruefung}. Vom Original bleiben {z['behalten']} von "
            f"{z['einheiten']} Einheiten (etwa {z['sprechminuten']:.0f} Min Sprechzeit). Dokumente zur Vorschau in "
            f"{z['ordner']}: " + ", ".join(z["dateien"]) + ". Noch nicht an Lia geschickt.")


def nachricht_an_lia(z: dict) -> tuple[str, dict]:
    """Ergebnistext und daten für Lias Zentrale (shared/telegram/vorlagen.py: kern, höchstens 3 Punkte, pruefen)."""
    # Sprachregel der Zentrale (agentkit.sprache, für Lia): kurze Sätze, höchstens 600 Zeichen für alles zusammen
    kern = (f"Hier ist ein erster Plan für dein Stück. Er dauert {karte.zahl(z['minuten'])} Minuten. "
            f"Vom Original bleiben nur die besten Stellen, etwa {z['sprechminuten']:.0f} Minuten Text. "
            "Lies in Ruhe. Dann antworte einfach auf diese Nachricht.")
    punkte = [f"Datei 1 und 2: das Stück in {z['anlaesse']} Szenen und dein Ablauf, mit Ideen zu deinen Fragen.",
              "Datei 3: der Text zum Spielen, mit Strichen.",
              "Datei 4: Die Klasse erfindet das Stück im Stück selbst."]
    pruefen = "Fällt Frederick weg? Und wann ist die Aufführung?"
    text = "\n".join([kern] + [f"- {p}" for p in punkte] + [pruefen])
    # Keine Feedback-Knöpfe: „Passt“ sagt bei einem Entwurf mit Varianten nicht, was passt (wie lia/recherche).
    return text, {"kern": kern, "punkte": punkte, "pruefen": pruefen, "knoepfe": "nur_antwort"}


def an_lia(ordner: Path, basis: Path | None = None, agenten_dir: Path | None = None) -> str:
    """Die vier Dokumente einer fertigen Runde an Lias Zentrale (über ihre Auftrags-Warteschlange), nur nach Jans
    Durchsicht und nur einmal je Runde (an_lia.json). Gibt die Auftrags-ID zurück. Kein Claude-Lauf."""
    merker = ordner / "an_lia.json"
    if merker.exists():
        raise RundenFehler(f"Schon an Lia geschickt: {json.loads(merker.read_text(encoding='utf-8'))['auftrag']}")
    dateien = [ordner / "fuer-lia" / name for name in DOKUMENTE]
    fehlen = [d.name for d in dateien if not d.exists()]
    if fehlen:
        raise RundenFehler(f"Runde {ordner.name} ist nicht fertig, es fehlen: {', '.join(fehlen)}")
    v = tomllib.loads((ordner.parents[1] / "theater.toml").read_text(encoding="utf-8"))
    einheiten = stueck.aus_dicts(json.loads((ordner / "einheiten.json").read_text(encoding="utf-8")))
    k = karte.antwort_lesen(ordner / "szenenkarte.json")
    ergebnis = ordner / "ergebnis.json"  # welcher Ablauf in die Dokumente ging (nach Prüfung und Überarbeitung)
    name = json.loads(ergebnis.read_text(encoding="utf-8"))["ablauf"] if ergebnis.exists() else "ablauf.json"
    f = karte.antwort_lesen(ordner / name)
    if karte.pruefen(k, einheiten, v["muss"]) or fassung.pruefen(f, einheiten, v["muss"], v["rahmen"]):
        raise RundenFehler(f"Runde {ordner.name}: Szenenkarte oder Ablauf besteht die Prüfung nicht mehr")
    nach_nr = {e.nr: e for e in einheiten}
    z = {"bausteine": len(f["bausteine"]), "minuten": sum(b["minuten"] for b in f["bausteine"]),
         "anlaesse": len(k["anlaesse"]),
         "sprechminuten": stueck.sprechminuten([nach_nr[n] for b in f["bausteine"] for n in fassung.behalten(b)])}
    text, daten = nachricht_an_lia(z)
    aid = auftraege.neuer_auftrag(AGENT, f"Fassung {v['stueck']['titel']}: Runde {ordner.name}", quelle="theater",
                                  basis=basis, agenten_dir=agenten_dir)
    auftraege.abschliessen(aid, text, dateien=dateien, daten=daten, basis=basis, agenten_dir=agenten_dir)
    merker.write_text(json.dumps({"auftrag": aid, "zeit": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                  "dateien": [d.name for d in dateien]}, ensure_ascii=False), encoding="utf-8")
    logger.info("Runde %s an Lia (Auftrag %s)", ordner.name, aid)
    return aid


def main(argv: list[str] | None = None, melden=jan_melden) -> int:
    """Ohne Argument eine neue Runde, mit Ordnername (z. B. runde-20261029-140740) Fortsetzung,
    mit --an-lia <ordner> die fertigen Dokumente an Lia (nach Jans Durchsicht)."""
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--an-lia"]:
        if len(argv) != 2 or config.INSTANZ_NAME != "lia":
            print("Aufruf: AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python runde.py --an-lia <ordner>",
                  file=sys.stderr)
            return 2
        try:
            print(an_lia(HIER / "data" / argv[1]))
        except (OSError, RundenFehler, karte.AntwortFehler, auftraege.AuftragFehler) as e:
            print(e, file=sys.stderr)
            return 1
        return 0
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
