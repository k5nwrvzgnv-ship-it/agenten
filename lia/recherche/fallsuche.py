"""Fallsuche: offene, gründliche Suche nach realen Fällen für Lias Examensreihe, mit Abgleich und Leitfragen.

Aufruf (vorerst von Hand):
    AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python fallsuche.py [--fenster a,b] [--weiter ORDNER] [--grenze USD]

Ablauf (Plan Jan 27.10.2026, Logik in faelle.py):
1. Sammeln: je Suchfenster (faelle.FENSTER) eine eigene Claude-Sitzung mit WebSearch/WebFetch, danach
   DURCHGAENGE - 1 Mal „weitersuchen“ in derselben Sitzung. Claude gleicht schon beim Suchen grob gegen das
   Regelwerk ab und schreibt Verworfenes mit Grund auf. Python prüft jeden Beleg wörtlich (webpruefung);
   Durchgefallenes geht einmal zurück. Ein Fenster, das scheitert (Zeitlimit, kaputte Datei), wird gemeldet,
   die übrigen laufen weiter. Ein Suchlauf startet nur, wenn danach (bis LAUF_USD) noch RESERVE_USD für
   Stufe 2 und 3 übrig sind.
2. Abgleich: neue Sitzung, alle Fälle gegen Regelwerk, Gelernte Regeln, Leitfaden, Seminarvorbild und Rubrik,
   je Prüfkriterium Stufe, Begründung und Regel-Kennungen. Eine Nachbesserung.
3. Dossier (neue Sitzung): stärkste Fälle, allgemeine Reihenfragen wie Lias eigene (Python lehnt Namen, Orte und
   Zahlen aus den Fällen ab) mit zwei Polen, Einstieg über einen Fall, Kant/Liszt mit Registerbelegen, RLP-Bezug;
   einige weitere interessante Fälle, wenige Rückfragen. Eine Nachbesserung. Schlankes docx über shared/renderer
   ohne Regel-Kennungen, Meldung an Jan. Kein Bewertungsbogen. --weiter ORDNER --nur-dossier schreibt nur das
   Dossier neu.
Ablage data/fallsuche/<datum-zeit>/. --weiter ORDNER übernimmt fertig geprüfte Fenster eines abgebrochenen Laufs
und wiederholt keine bezahlte Suche (sammeln-<fenster>-gesucht.json), nur die Prüfung.
Kostengrenze GRENZE_USD je Lauf (Jan 27.10.2026: 15 USD), mit --grenze anders (nur nach Jans Okay).
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import agent
import faelle
import register
import webauftrag
import webpruefung
from agentkit import claude_lauf, einstellungen

HIER = agent.HIER
logger = agent.logger
LIA = HIER.parent
GRENZE_USD = 15.0
RESERVE_USD = 3.0   # bleibt für Abgleich und Dossier
LAUF_USD = 5.0      # so viel kann ein Suchlauf kosten (erster echter Lauf 27.10.: 2,7–4,5 USD)
DURCHGAENGE = 2     # Suche + einmal weitersuchen je Fenster


@dataclass
class Pfade:
    regelwerk: Path = HIER / "regelwerk_reihe.md"
    status_unterricht: Path = LIA / "unterricht" / "STATUS.md"  # Abschnitt „Gelernte Regeln“
    leitfaden: Path = LIA / "unterricht" / "leitfaden.md"
    reihen: Path = agent.REIHEN
    examen: Path = LIA / "examen" / "examen.toml"
    vorbild: Path = LIA / "examen" / "seminar_vorbild.md"
    rubrik: Path = LIA / "examen" / "rubrik.toml"
    rlp: Path = LIA / "examen" / "rlp_auszug.toml"


def kontext_laden(pfade: Pfade, reg: dict) -> dict:
    """Alles, was Claude lesen soll, als Text (Claude darf außerhalb von lia/recherche nicht lesen)."""
    def lies(p: Path) -> str:
        return p.read_text(encoding="utf-8")
    regelwerk, reihen = lies(pfade.regelwerk), lies(pfade.reihen)
    k = {
        "regelwerk": regelwerk,
        "regeltexte": faelle.regeln_aus_regelwerk(regelwerk),
        "gelernte": faelle.gelernte_regeln(lies(pfade.status_unterricht)),
        "leitfaden": lies(pfade.leitfaden),
        "reihe": agent.reihe_laden(pfade.reihen),
        "examen": lies(pfade.examen),
        "vorbild": lies(pfade.vorbild),
        "rubrik": lies(pfade.rubrik),
        "rlp": faelle.rlp_stellen(lies(pfade.rlp)),
        "register": webauftrag.register_text(reg),
        "reihenfragen": faelle.reihenfragen_lias(reihen),
    }
    # Wörter, die in einer allgemeinen Reihenfrage stehen dürfen (Prüfung „keine Namen aus dem Fall“)
    k["allgemein"] = "\n".join([regelwerk, reihen, k["leitfaden"], k["examen"], k["vorbild"], k["rubrik"],
                                *k["gelernte"].values(), *k["rlp"].values()])
    return k


def _lauf(laufen, kosten: agent.Kosten, name: str):
    def lauf(text: str, sitzung: str | None, wofuer: str):
        kosten.vorher()
        erg = laufen(text, sitzung, art="anspruchsvoll")
        kosten.dazu(erg, f"Fallsuche {name} {wofuer}")
        if not erg.ok:  # z. B. max_turns: Die Datei kann trotzdem brauchbar sein
            logger.warning("Fallsuche %s %s: Lauf nicht ok: %s", name, wofuer, erg.text[:300])
        return erg
    return lauf


def sammeln(fenster: str, ordner: Path, hier: Path, kontext: dict, domains: list[str], seitentext, lauf,
            budget_frei) -> dict:
    """Ein Suchfenster. Gibt die geprüften Kandidaten zurück (auch aus einem früheren Lauf, siehe --weiter)."""
    fertig = ordner / f"sammeln-{fenster}-geprueft.json"
    if fertig.exists():
        logger.info("Fallsuche %s: Fenster %s schon fertig, übernommen", ordner.name, fenster)
        return json.loads(fertig.read_text(encoding="utf-8"))
    ausgabe = ordner.relative_to(hier) / f"sammeln-{fenster}.json"
    gesucht = ordner / f"sammeln-{fenster}-gesucht.json"  # Suche bezahlt; bei --weiter nicht wiederholen
    if gesucht.exists():
        logger.info("Fallsuche %s: Fenster %s schon gesucht, nur noch prüfen", ordner.name, fenster)
        sitzung = json.loads(gesucht.read_text(encoding="utf-8")).get("sitzung")
    else:
        erg = lauf(faelle.sammel_prompt(fenster, kontext, domains, str(ausgabe)), None, f"Sammeln {fenster}")
        for n in range(2, DURCHGAENGE + 1):
            if not budget_frei():
                break
            erg = lauf(faelle.weiter_prompt(str(ausgabe)), erg.sitzung, f"Sammeln {fenster} Durchgang {n}")
        sitzung = erg.sitzung
        gesucht.write_text(json.dumps({"sitzung": sitzung}), encoding="utf-8")
    daten, fehler = faelle.sammeln_lesen(hier / ausgabe)
    daten = faelle.belege_pruefen(daten, domains, seitentext)
    nachbessern = fehler + faelle.durchgefallene(daten)
    if nachbessern and sitzung and budget_frei():  # ohne Sitzung (Marke von Hand) keine Nachbesserung
        logger.info("Fallsuche %s %s: %d Punkte zur Nachbesserung", ordner.name, fenster, len(nachbessern))
        lauf(faelle.nachbesserung_prompt(nachbessern, str(ausgabe)), sitzung, f"Sammeln {fenster} Nachbesserung")
        daten, fehler = faelle.sammeln_lesen(hier / ausgabe)
        daten = faelle.belege_pruefen(daten, domains, seitentext)
    if fehler:
        logger.warning("Fallsuche %s %s: ungültige Kandidaten bleiben draußen: %s", ordner.name, fenster,
                       "; ".join(fehler)[:500])
    fertig.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    return daten


def _abgleichen(ges: dict, ordner: Path, hier: Path, kontext: dict, regel_ids: set[str], lauf):
    ids = [f["id"] for f in ges["faelle"]]
    ausgabe = ordner.relative_to(hier) / "abgleich.json"
    erg = lauf(faelle.abgleich_prompt(ges["faelle"], kontext, str(ausgabe)), None, "Abgleich")
    abgleich, fehler = faelle.abgleich_lesen(hier / ausgabe, ids, regel_ids)
    if fehler:
        logger.info("Fallsuche %s: Abgleich mit Fehlern (%s), Nachbesserung", ordner.name, "; ".join(fehler)[:300])
        lauf(faelle.nachbesserung_prompt(fehler, str(ausgabe)), erg.sitzung, "Abgleich Nachbesserung")
        abgleich, fehler = faelle.abgleich_lesen(hier / ausgabe, ids, regel_ids)
    return abgleich, fehler, erg.sitzung


def _dossier(ges: dict, abgleich: dict, ordner: Path, hier: Path, kontext: dict, regel_ids: set[str], reg: dict,
             lauf):
    """Dossier in einer neuen Sitzung (alles Nötige steht im Prompt), eine Nachbesserung."""
    ausgabe = ordner.relative_to(hier) / "dossier.json"
    verworfen = faelle.verworfen_ids(ges["verworfen"])
    pruef = dict(abgleich=abgleich, regel_ids=regel_ids, rlp_ids=set(kontext["rlp"]),
                 register_ids=set(webpruefung.register_stellen(reg)), verworfen=faelle.ohne_gewalt(verworfen),
                 fallbezug=faelle.fallwoerter(ges["faelle"], kontext["allgemein"]),
                 gewalt={f["id"] for f in ges["faelle"] if f["gewalt"]})
    (hier / ausgabe).unlink(missing_ok=True)
    erg = lauf(faelle.dossier_prompt(ges["faelle"], abgleich, verworfen, kontext, str(ausgabe)), None, "Dossier")
    sitzung = erg.sitzung
    dossier, fehler = faelle.dossier_lesen(hier / ausgabe, **pruef)
    if fehler:
        logger.info("Fallsuche %s: Dossier mit Fehlern (%s), Nachbesserung", ordner.name, "; ".join(fehler)[:300])
        lauf(faelle.nachbesserung_prompt(fehler, str(ausgabe)), sitzung, "Dossier Nachbesserung")
        dossier, fehler = faelle.dossier_lesen(hier / ausgabe, **pruef)
    if not dossier["leitfragen"] or not dossier["auswahl"]:
        raise faelle.FallFehler(f"Dossier ohne gültige Auswahl oder Leitfrage: {'; '.join(fehler)[:300]}")
    return dossier, fehler


def _renderer_standard():
    import tomllib

    import renderer
    profil = tomllib.loads(webauftrag.PROFIL.read_text(encoding="utf-8"))
    return lambda b, ziel: renderer.bauen(b, ziel, profil=profil, vorschau=False)


def ausfuehren(hier: Path = HIER, fenster: list[str] | None = None, weiter: Path | None = None, laufen=None,
               seitentext=None, renderer_bauen=None, melden=agent.jan_melden, cfg: dict | None = None,
               kosten: agent.Kosten | None = None, pfade: Pfade | None = None, nur_dossier: bool = False) -> Path:
    """Eine Fallsuche. Gibt den Ordner data/fallsuche/<id>/ zurück. nur_dossier (mit weiter): Suche und Abgleich
    aus faelle.json und abgleich.json übernehmen, nur das Dossier neu."""
    cfg = cfg or einstellungen.lade()
    domains = einstellungen.webfetch_domains(cfg, agent.AGENT) or []
    kosten = kosten or agent.Kosten(grenze=GRENZE_USD)
    fenster = fenster or list(faelle.FENSTER)
    if weiter:
        ordner = weiter
    else:
        ordner = hier / "data" / "fallsuche" / f"{datetime.now():%Y%m%d-%H%M%S}"
        ordner.mkdir(parents=True)
    reg = register.laden(hier / "data" / "register.json")
    kontext = kontext_laden(pfade or Pfade(), reg)
    regel_ids = set(kontext["regeltexte"]) | set(kontext["gelernte"])
    seitentext = seitentext or webauftrag.seitenleser(domains, ordner / "roh")
    lauf = _lauf(laufen or webauftrag._laufen_standard(hier), kosten, ordner.name)

    def budget_frei() -> bool:
        return kosten.summe + LAUF_USD <= kosten.grenze - RESERVE_USD

    probleme, je_fenster = [], {}
    try:
        if nur_dossier:
            ges = json.loads((ordner / "faelle.json").read_text(encoding="utf-8"))
            abgleich, _ = faelle.abgleich_lesen(ordner / "abgleich.json", [f["id"] for f in ges["faelle"]], regel_ids)
            fenster = []
        for f in fenster:
            if not budget_frei() and not (ordner / f"sammeln-{f}-geprueft.json").exists():
                probleme.append(f"Fenster {f} ausgelassen (Budget für Abgleich und Dossier reserviert)")
                continue
            try:
                je_fenster[f] = sammeln(f, ordner, hier, kontext, domains, seitentext, lauf, budget_frei)
            except (faelle.FallFehler, claude_lauf.Zeitueberschreitung) as e:
                logger.error("Fallsuche %s: Fenster %s gescheitert: %s", ordner.name, f, e)
                probleme.append(f"Fenster {f} gescheitert: {e}")
        if not nur_dossier:
            ges = faelle.zusammenfuehren(je_fenster)
            (ordner / "faelle.json").write_text(json.dumps(ges, ensure_ascii=False, indent=1), encoding="utf-8")
            if not ges["faelle"]:
                raise faelle.FallFehler("kein Fall mit Quelle gefunden")
            abgleich, fehler, _ = _abgleichen(ges, ordner, hier, kontext, regel_ids, lauf)
            if fehler:
                probleme.append(f"Abgleich unvollständig: {'; '.join(fehler)[:300]}")
        if not abgleich:
            raise faelle.FallFehler("kein gültiger Abgleich")
        dossier, fehler = _dossier(ges, abgleich, ordner, hier, kontext, regel_ids, reg, lauf)
        if fehler:
            probleme.append(f"Dossier: verworfen {'; '.join(fehler)[:300]}")
    except (faelle.FallFehler, agent.KostenGrenze, claude_lauf.LaufFehler) as e:
        logger.error("Fallsuche %s: %s", ordner.name, e)
        melden(f"Fallsuche {ordner.name} abgebrochen: {e}. {' '.join(probleme)} Kosten {kosten.summe:.2f} USD. "
               f"Fortsetzen mit --weiter {ordner}")
        raise

    zahlen = {"fenster": len({x for f in ges["faelle"] for x in f["fenster"]}), "faelle": len(ges["faelle"]),
              "belegt": sum(f["status"] == "belegt" for f in ges["faelle"]),
              "ungeprueft": sum(f["status"] == "ungeprueft" for f in ges["faelle"]),
              "verworfen": len(ges["verworfen"]), "nicht_belegt": len(ges["nicht_belegt"])}
    ergebnis = {"zahlen": zahlen, "abgleich": abgleich, "dossier": dossier, "probleme": probleme,
                "kosten_usd": round(kosten.summe, 4)}
    (ordner / "ergebnis.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")
    docx = ordner / "Fallsuche Strafe.docx"
    titel = f"Fallsuche Straftheorien vom {datetime.now():%d.%m.%Y}"
    (renderer_bauen or _renderer_standard())(
        faelle.beschreibung(titel, ges, dossier, zahlen), docx)
    melden(f"Fallsuche fertig: {zahlen['faelle']} Fälle aus {zahlen['fenster']} Fenstern ({zahlen['belegt']} mit "
           f"geprüftem Zitat), {len(dossier['auswahl'])} ausgewählt, {len(dossier['leitfragen'])} Leitfragen. "
           f"{' '.join(probleme)} Kosten {kosten.summe:.2f} USD in {kosten.laeufe} Läufen. Datei: {docx}")
    logger.info("Fallsuche %s fertig: %s, %.4f USD", ordner.name, zahlen, kosten.summe)
    return ordner


def main(argv: list[str]) -> int:
    teiler = argparse.ArgumentParser(prog="fallsuche.py", description="Fälle suchen, abgleichen, Leitfragen.")
    teiler.add_argument("--fenster", help=f"Komma-Liste aus {', '.join(faelle.FENSTER)} (ohne: alle)")
    teiler.add_argument("--weiter", metavar="ORDNER", help="abgebrochenen Lauf in data/fallsuche/<id> fortsetzen")
    teiler.add_argument("--nur-dossier", action="store_true", help="mit --weiter: nur das Dossier neu schreiben")
    teiler.add_argument("--grenze", type=float, default=GRENZE_USD, help=f"Kostengrenze in USD (ohne: {GRENZE_USD:g})")
    args = teiler.parse_args(argv[1:])
    fenster = args.fenster.split(",") if args.fenster else None
    if fenster and (falsch := [f for f in fenster if f not in faelle.FENSTER]):
        print(f"Unbekannte Fenster: {', '.join(falsch)}", file=sys.stderr)
        return 2
    weiter = Path(args.weiter).resolve() if args.weiter else None
    if args.nur_dossier and not weiter:
        print("--nur-dossier braucht --weiter ORDNER", file=sys.stderr)
        return 2
    if weiter and not weiter.is_dir():
        print(f"Ordner fehlt: {weiter}", file=sys.stderr)
        return 2
    try:
        print(ausfuehren(fenster=fenster, weiter=weiter, nur_dossier=args.nur_dossier,
                         kosten=agent.Kosten(grenze=args.grenze)))
    except (faelle.FallFehler, agent.KostenGrenze, claude_lauf.LaufFehler) as e:
        print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
