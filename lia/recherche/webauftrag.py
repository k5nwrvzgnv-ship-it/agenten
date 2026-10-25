"""Webauftrag: Ein Rechercheauftrag (Textdatei) wird von Claude im Web recherchiert und von Python geprüft.

Aufruf (vorerst von Hand, Lias Zentrale folgt in Teil C):
    AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python webauftrag.py <auftragsdatei> [--anhang <pfad>]
    AGENTKIT_INSTANZ=... .venv/bin/python webauftrag.py --nur-traegt data/web/<id>

Ablauf (Plan „Webrecherche“, Jan 25.10.2026):
1. Ablage data/web/<id>/ (auftrag.txt, ergebnis.json von Claude, geprueft.json, Recherche.docx, roh/ Cache).
2. Claude (claude_lauf, art "anspruchsvoll", Werkzeuge mit WebSearch/WebFetch laut einstellungen.toml, WebFetch nur
   auf Jans Domains) bekommt den Auftrag und die geprüften Stellen aus data/register.json und schreibt ergebnis.json
   (Format: webpruefung.py).
3. Python prüft jeden Beleg (webpruefung.py). Durchgefallene gehen einmal an Claude zurück (dieselbe Sitzung),
   danach wird endgültig geprüft.
4. docx über shared/renderer (profil.toml = Lias Profil), Meldung an Jan mit Zahlen, Kosten und Pfad.
5. Prüflauf (traegt.py): Trägt jedes Zitat seine Tatsachenaussage? Günstiger Lauf (art routine), "nein" wird
   unbelegt, "teilweise" bekommt im docx „Detail nicht belegt: …“. Einzeln: --nur-traegt data/web/<id>.
Anhänge: Zeilen "ANHANG: <pfad>" im Auftrag oder --anhang <pfad> (anhaenge.py), Kopie nach data/web/<id>/anhaenge/.
Kostengrenze GRENZE_USD je Auftrag (agent.Kosten).
"""

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import agent
import anhaenge
import auslesen
import register
import traegt
import webpruefung
from agentkit import abruf, claude_lauf, einstellungen, textfassung

HIER = agent.HIER
logger = agent.logger
PROFIL = HIER / "profil.toml"
MAX_ZITAT = 300


def auftrag_id(datei: Path, jetzt: datetime | None = None) -> str:
    jetzt = jetzt or datetime.now()
    name = re.sub(r"[^a-z0-9]+", "-", datei.stem.lower()).strip("-")[:30] or "auftrag"
    return f"{jetzt:%Y%m%d-%H%M%S}-{name}"


def register_text(reg: dict[str, dict]) -> str:
    """Geprüfte Stellen aus dem Register für den Prompt: Verweis, Werk, Position, Zitat."""
    zeilen = []
    for qid, e in reg.items():
        if not e.get("gemeinfreiheit", {}).get("verwendbar"):
            continue
        for s in e.get("stellen", []):
            seite = s.get("seite")
            wer = ", ".join(x for x in (e.get("autor", ""), e.get("werk", "")) if x)
            position = f" [{s['position']}]" if s.get("position") else ""
            zeilen.append(f"- {qid}:{seite} ({wer}){position}: „{s['zitat'][:700]}“")
    return "\n".join(zeilen) or "(keine)"


def prompt(auftrag: str, reg_text: str, domains: list[str], ausgabe: str, beilagen: list[str] = ()) -> str:
    anhang = ("\nANHÄNGE zum Auftrag (mit Read lesen; bei pdf/docx liegt eine Textfassung .txt daneben):\n"
              + "\n".join(f"- {b}" for b in beilagen) + "\nAndere Pfade aus dem Auftrag sind nicht lesbar.\n"
              if beilagen else "")
    return f"""Aufgabe: Recherchiere den folgenden Auftrag im Web und schreibe das Ergebnis als JSON in eine Datei.

AUFTRAG (von der Lehrkraft, wörtlich):
<<<
{auftrag}
>>>
{anhang}
BEREITS GEPRÜFTE QUELLEN (Quellenregister; wörtlich geprüft, Liszt-Stellen vom Scan abgeschrieben).
Du darfst sie als Beleg nutzen mit {{"register": "<quelle>:<seite>"}}, genau mit dem Verweis vor der Klammer:
{reg_text}

WERKZEUGE
- WebSearch zum Finden. WebFetch funktioniert nur für diese Domains (andere werden abgelehnt):
  {", ".join(domains)}
- Quellen außerhalb dieser Liste darfst du nennen, sie gelten aber als ungeprüft und belegen nichts.
- Arbeite sparsam: höchstens etwa 20 Werkzeugaufrufe. Schreibe die Datei früh und ergänze sie dann.

REGELN (wichtig)
- Nichts erfinden. Keine Fälle, Zahlen, Zitate, Titel, Längen oder Links, die du nicht selbst gefunden hast.
- Jede Aussage braucht Belege. Ein Beleg ist entweder {{"url": "...", "zitat": "..."}} oder
  {{"register": "<quelle>:<seite>"}}.
- Das Zitat muss Zeichen für Zeichen so auf der Seite stehen (höchstens {MAX_ZITAT} Zeichen, ein Satz oder
  Satzteil). Python lädt die Seite und prüft das wörtlich. WebFetch zeigt oft nur eine Zusammenfassung oder
  Umformulierung: Übernimm als Zitat nur Text, der erkennbar wörtlich auf der Seite steht, nicht deine Zusammenfassung.
- Bei Videos (YouTube, Mediatheken): Als Zitat den Titel des Videos, wie er auf der Seite steht. Länge und
  Untertitel kann Python nicht prüfen; nenne sie nur, wenn sie auf der Seite stehen, sonst als Lücke.
- Eigene Einschätzungen (Stärken, Schwächen, Empfehlungen, Vorschläge) beginnen mit „Einschätzung:“. Belege sie,
  wo eine Quelle sie stützt. Ohne Quelle bleiben sie unbelegt und erscheinen unter „Nicht belegt“; das ist
  erlaubt. Gib eine Einschätzung nie als Tatsache aus.
- Was du nicht belegen konntest oder nicht gefunden hast, schreibe unter "luecken" (z. B. „Kein frei
  abrufbares Video zu X gefunden“). Fragen an die Lehrkraft unter "rueckfragen".
- Schreibe knapp, sachlich, ohne Emojis.

AUSGABE: Schreibe NUR in die Datei {ausgabe}, als JSON:
{{"abschnitte": [{{"titel": "...", "aussagen": [{{"text": "...", "belege": [{{"url": "https://...", "zitat": "..."}},
{{"register": "kant-mds-strafrecht:331"}}]}}]}}], "luecken": ["..."], "rueckfragen": ["..."]}}
Gliedere die Abschnitte nach den Teilen des Auftrags. Antworte danach mit einem Satz."""


def nachbesserung_prompt(liste: list[str], ausgabe: str) -> str:
    zeilen = "\n".join(f"- {x}" for x in liste)
    return f"""Python hat die Belege geprüft. Diese Belege sind durchgefallen:
{zeilen}

Korrigiere sie: Zitat wörtlich von der Seite übernehmen (WebFetch erneut nutzen, keine Zusammenfassung), anderen
Beleg suchen, oder den Beleg entfernen. Eine Aussage ohne gültigen Beleg verschiebst du nach "luecken" oder lässt
sie ohne Beleg stehen (dann erscheint sie unter „Nicht belegt“). Nichts erfinden.
Schreibe die VOLLSTÄNDIGE, korrigierte Datei neu nach {ausgabe}, im selben Format. Antworte danach mit einem Satz."""


def seitenleser(domains: list[str], cache: Path):
    """seitentext(url) für webpruefung: lädt über agentkit.abruf (Allowlist = Jans Domains), Text ohne HTML."""
    texte = {}

    def seitentext(url: str) -> str:
        if url not in texte:
            erg = abruf.laden(url, domains, cache)
            texte[url] = abruf.html_zu_text(auslesen.html_text(erg.inhalt, erg.meta.get("content_type")))
        return texte[url]
    return seitentext


def _laufen_standard(hier: Path):
    def laufen(text, sitzung=None, art="anspruchsvoll"):
        return claude_lauf.laufen(agent.AGENT, hier, text, art=art, sitzung_fortsetzen=sitzung)
    return laufen


def _lauf(laufen, kosten: "agent.Kosten", name: str):
    def lauf(text: str, sitzung: str | None, wofuer: str, art: str = "anspruchsvoll"):
        kosten.vorher()
        erg = laufen(text, sitzung, art=art)
        kosten.dazu(erg, f"Webauftrag {name} {wofuer}")
        if not erg.ok:  # z. B. max_turns: Die Datei kann trotzdem brauchbar sein
            logger.warning("Webauftrag %s %s: Lauf nicht ok: %s", name, wofuer, erg.text[:300])
        return erg
    return lauf


def traegt_pruefen(daten: dict, reg: dict, ordner: Path, hier: Path, lauf) -> dict:
    """Prüflauf „trägt das Zitat die Aussage?“ (traegt.py): art routine, neue Sitzung, eine Nachbesserung."""
    liste = traegt.faelle(daten, reg)
    ids = [f["id"] for f in liste]
    if not ids:
        return traegt.anwenden(daten, [], {})
    ausgabe = ordner.relative_to(hier) / "traegt.json"
    (hier / ausgabe).unlink(missing_ok=True)
    erg = lauf(traegt.prompt(liste, str(ausgabe)), None, "Prüflauf trägt", art="routine")
    urteile, fehler = traegt.lesen(hier / ausgabe, ids)
    if fehler:
        logger.info("Webauftrag %s: Prüflauf mit Fehlern (%s), Nachbesserung", ordner.name, "; ".join(fehler)[:300])
        lauf(traegt.nachbesserung_prompt(fehler, str(ausgabe)), erg.sitzung, "Prüflauf Nachbesserung", art="routine")
        neu, fehler = traegt.lesen(hier / ausgabe, ids)
        urteile = {**urteile, **neu}
        if fehler:
            logger.warning("Webauftrag %s: Prüflauf bleibt fehlerhaft: %s", ordner.name, "; ".join(fehler)[:300])
    return traegt.anwenden(daten, ids, urteile)


def _abschliessen(ordner: Path, daten: dict, reg: dict, kosten, renderer_bauen, melden, abgelehnt: list[str]) -> None:
    daten["kosten_usd"] = round(kosten.summe, 4)
    (ordner / "geprueft.json").write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    titel = f"Recherche vom {datetime.now():%d.%m.%Y}"
    if renderer_bauen is None:
        import tomllib

        import renderer
        profil = tomllib.loads(PROFIL.read_text(encoding="utf-8"))

        def renderer_bauen(b, ziel):
            return renderer.bauen(b, ziel, profil=profil, vorschau=False)
    docx = ordner / "Recherche.docx"
    renderer_bauen(webpruefung.beschreibung(titel, daten, reg), docx)
    z, e1, t = daten["zahlen"], daten.get("erste_pruefung") or daten["zahlen"], daten.get("traegt_zahlen")
    traegt_text = (f"Trägt das Zitat die Aussage: {t['ja']} ja, {t['teilweise']} teilweise, {t['nein']} nein, "
                   f"{t['nicht_geprueft']} nicht geprüft. ") if t else ""
    anhang_text = f"Abgelehnte Anhänge: {'; '.join(abgelehnt)}. " if abgelehnt else ""
    melden(f"Webauftrag fertig: {z['belegt']} von {z['aussagen']} Aussagen belegt, {z['unbelegt']} unbelegt. "
           f"Belege: {z['bestanden']} bestanden, {z['durchgefallen']} durchgefallen, {z['ungeprueft']} ungeprüft "
           f"(erste Prüfung: {e1['bestanden']}/{e1['durchgefallen']}/{e1['ungeprueft']}). {traegt_text}"
           f"Lücken: {len(daten['luecken'])}, Rückfragen: {len(daten['rueckfragen'])}. {anhang_text}"
           f"Kosten {kosten.summe:.2f} USD in {kosten.laeufe} Läufen. Datei: {docx}")
    logger.info("Webauftrag %s fertig: %s, trägt %s, %.4f USD", ordner.name, z, t, kosten.summe)


def ausfuehren(datei: Path, hier: Path = HIER, laufen=None, seitentext=None, renderer_bauen=None,
               melden=agent.jan_melden, cfg: dict | None = None, kosten: agent.Kosten | None = None,
               anhang: list[str] = (), als_text=textfassung.als_text,
               anhang_wurzel: Path = anhaenge.ERLAUBT_UNTER) -> Path:
    """Ein Webauftrag. Gibt den Ordner data/web/<id>/ zurück."""
    cfg = cfg or einstellungen.lade()
    domains = einstellungen.webfetch_domains(cfg, agent.AGENT) or []
    kosten = kosten or agent.Kosten()
    basis, n = hier / "data" / "web" / auftrag_id(datei), 1
    ordner = basis
    while ordner.exists():
        n += 1
        ordner = basis.with_name(f"{basis.name}-{n}")
    ordner.mkdir(parents=True)
    shutil.copyfile(datei, ordner / "auftrag.txt")
    auftrag = (ordner / "auftrag.txt").read_text(encoding="utf-8")
    kopiert, abgelehnt = anhaenge.kopieren(anhaenge.aus_auftrag(auftrag) + list(anhang), ordner / "anhaenge",
                                           als_text, anhang_wurzel)
    for a in abgelehnt:
        logger.warning("Webauftrag %s: Anhang abgelehnt: %s", ordner.name, a)
    reg = register.laden(hier / "data" / "register.json")
    stellen = webpruefung.register_stellen(reg)
    ausgabe = ordner.relative_to(hier) / "ergebnis.json"
    seitentext = seitentext or seitenleser(domains, ordner / "roh")
    lauf = _lauf(laufen or _laufen_standard(hier), kosten, ordner.name)
    beilagen = [str(k.relative_to(hier)) for k in kopiert]

    try:
        erg = lauf(prompt(auftrag, register_text(reg), domains, str(ausgabe), beilagen), None, "Recherche")
        daten = webpruefung.pruefen(webpruefung.lesen(hier / ausgabe), domains, seitentext, stellen)
        nachbesserung = webpruefung.durchgefallene(daten)
        erste = dict(daten["zahlen"])
        if nachbesserung:
            logger.info("Webauftrag %s: %d Belege durchgefallen, Nachbesserung", ordner.name, len(nachbesserung))
            (ordner / "ergebnis_1.json").write_text((hier / ausgabe).read_text(encoding="utf-8"), encoding="utf-8")
            lauf(nachbesserung_prompt(nachbesserung, str(ausgabe)), erg.sitzung, "Nachbesserung")
            daten = webpruefung.pruefen(webpruefung.lesen(hier / ausgabe), domains, seitentext, stellen)
        daten["erste_pruefung"] = erste
        daten["anhaenge"] = {"kopiert": beilagen, "abgelehnt": abgelehnt}
        daten = traegt_pruefen(daten, reg, ordner, hier, lauf)
    except (webpruefung.WebFehler, agent.KostenGrenze, claude_lauf.LaufFehler) as f:
        logger.error("Webauftrag %s: %s", ordner.name, f)
        anhang_text = f" Abgelehnte Anhänge: {'; '.join(abgelehnt)}." if abgelehnt else ""
        melden(f"Webauftrag {ordner.name} abgebrochen: {f}. Kosten {kosten.summe:.2f} USD.{anhang_text} Ordner: {ordner}")
        raise
    _abschliessen(ordner, daten, reg, kosten, renderer_bauen, melden, abgelehnt)
    return ordner


def nur_traegt(ordner: Path, hier: Path = HIER, laufen=None, renderer_bauen=None, melden=agent.jan_melden,
               kosten: agent.Kosten | None = None) -> Path:
    """Prüflauf auf einen fertigen Auftrag anwenden (ohne neue Recherche), neues docx. Das alte geprueft.json
    bleibt als geprueft_vor_traegt.json."""
    kosten = kosten or agent.Kosten()
    alt = ordner / "geprueft.json"
    daten = json.loads(alt.read_text(encoding="utf-8"))
    if "traegt_zahlen" in daten:
        raise webpruefung.WebFehler(f"{ordner.name}: Prüflauf ist schon gelaufen")
    shutil.copyfile(alt, ordner / "geprueft_vor_traegt.json")
    reg = register.laden(hier / "data" / "register.json")
    lauf = _lauf(laufen or _laufen_standard(hier), kosten, ordner.name)
    try:
        daten = traegt_pruefen(daten, reg, ordner, hier, lauf)
    except (agent.KostenGrenze, claude_lauf.LaufFehler) as f:
        melden(f"Prüflauf für {ordner.name} abgebrochen: {f}. Kosten {kosten.summe:.2f} USD.")
        raise
    daten["kosten_usd_traegt"] = round(kosten.summe, 4)
    _abschliessen(ordner, daten, reg, kosten, renderer_bauen, melden, daten.get("anhaenge", {}).get("abgelehnt", []))
    return ordner


def main(argv: list[str]) -> int:
    teiler = argparse.ArgumentParser(prog="webauftrag.py", description="Webauftrag recherchieren und prüfen.")
    teiler.add_argument("auftrag", nargs="?", help="Auftragsdatei (Text)")
    teiler.add_argument("--anhang", action="append", default=[], help="Datei für Claude (mehrfach erlaubt)")
    teiler.add_argument("--nur-traegt", metavar="ORDNER", help="nur den Prüflauf auf data/web/<id> anwenden")
    args = teiler.parse_args(argv[1:])
    try:
        if args.nur_traegt:
            print(nur_traegt(Path(args.nur_traegt).resolve()))
        elif args.auftrag and Path(args.auftrag).is_file():
            print(ausfuehren(Path(args.auftrag).resolve(), anhang=args.anhang))
        else:
            teiler.print_usage(sys.stderr)
            return 2
    except (webpruefung.WebFehler, agent.KostenGrenze, claude_lauf.LaufFehler) as f:
        print(f, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
