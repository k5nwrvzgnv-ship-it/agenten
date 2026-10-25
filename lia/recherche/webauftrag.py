"""Webauftrag: Ein Rechercheauftrag (Textdatei) wird von Claude im Web recherchiert und von Python geprüft.

Aufruf (vorerst von Hand, Lias Zentrale folgt in Teil C):
    AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python webauftrag.py <auftragsdatei>

Ablauf (Plan „Webrecherche“, Jan 25.10.2026):
1. Ablage data/web/<id>/ (auftrag.txt, ergebnis.json von Claude, geprueft.json, Recherche.docx, roh/ Cache).
2. Claude (claude_lauf, art "anspruchsvoll", Werkzeuge mit WebSearch/WebFetch laut einstellungen.toml, WebFetch nur
   auf Jans Domains) bekommt den Auftrag und die geprüften Stellen aus data/register.json und schreibt ergebnis.json
   (Format: webpruefung.py).
3. Python prüft jeden Beleg (webpruefung.py). Durchgefallene gehen einmal an Claude zurück (dieselbe Sitzung),
   danach wird endgültig geprüft.
4. docx über shared/renderer (profil.toml = Lias Profil), Meldung an Jan mit Zahlen, Kosten und Pfad.
Kostengrenze GRENZE_USD je Auftrag (agent.Kosten).
"""

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import agent
import auslesen
import register
import webpruefung
from agentkit import abruf, claude_lauf, einstellungen

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


def prompt(auftrag: str, reg_text: str, domains: list[str], ausgabe: str) -> str:
    return f"""Aufgabe: Recherchiere den folgenden Auftrag im Web und schreibe das Ergebnis als JSON in eine Datei.

AUFTRAG (von der Lehrkraft, wörtlich):
<<<
{auftrag}
>>>

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


def ausfuehren(datei: Path, hier: Path = HIER, laufen=None, seitentext=None, renderer_bauen=None,
               melden=agent.jan_melden, cfg: dict | None = None, kosten: agent.Kosten | None = None) -> Path:
    """Ein Webauftrag. Gibt den Ordner data/web/<id>/ zurück."""
    cfg = cfg or einstellungen.lade()
    domains = einstellungen.webfetch_domains(cfg, agent.AGENT) or []
    kosten = kosten or agent.Kosten()
    ordner = hier / "data" / "web" / auftrag_id(datei)
    ordner.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(datei, ordner / "auftrag.txt")
    auftrag = (ordner / "auftrag.txt").read_text(encoding="utf-8")
    reg = register.laden(hier / "data" / "register.json")
    stellen = webpruefung.register_stellen(reg)
    ausgabe = ordner.relative_to(hier) / "ergebnis.json"
    seitentext = seitentext or seitenleser(domains, ordner / "roh")
    if laufen is None:
        def laufen(text, sitzung=None):
            return claude_lauf.laufen(agent.AGENT, hier, text, art="anspruchsvoll", sitzung_fortsetzen=sitzung)

    def lauf(text: str, sitzung: str | None, wofuer: str):
        kosten.vorher()
        erg = laufen(text, sitzung)
        kosten.dazu(erg, f"Webauftrag {ordner.name} {wofuer}")
        if not erg.ok:  # z. B. max_turns: Die Datei kann trotzdem brauchbar sein
            logger.warning("Webauftrag %s %s: Lauf nicht ok: %s", ordner.name, wofuer, erg.text[:300])
        return erg

    try:
        erg = lauf(prompt(auftrag, register_text(reg), domains, str(ausgabe)), None, "Recherche")
        daten = webpruefung.pruefen(webpruefung.lesen(hier / ausgabe), domains, seitentext, stellen)
        nachbesserung = webpruefung.durchgefallene(daten)
        erste = dict(daten["zahlen"])
        if nachbesserung:
            logger.info("Webauftrag %s: %d Belege durchgefallen, Nachbesserung", ordner.name, len(nachbesserung))
            (ordner / "ergebnis_1.json").write_text((hier / ausgabe).read_text(encoding="utf-8"), encoding="utf-8")
            lauf(nachbesserung_prompt(nachbesserung, str(ausgabe)), erg.sitzung, "Nachbesserung")
            daten = webpruefung.pruefen(webpruefung.lesen(hier / ausgabe), domains, seitentext, stellen)
    except (webpruefung.WebFehler, agent.KostenGrenze, claude_lauf.LaufFehler) as f:
        logger.error("Webauftrag %s: %s", ordner.name, f)
        melden(f"Webauftrag {ordner.name} abgebrochen: {f}. Kosten {kosten.summe:.2f} USD. Ordner: {ordner}")
        raise
    daten["erste_pruefung"] = erste
    daten["kosten_usd"] = round(kosten.summe, 4)
    (ordner / "geprueft.json").write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")

    titel = f"Recherche vom {datetime.now():%d.%m.%Y}"
    if renderer_bauen is None:
        import renderer
        import tomllib
        profil = tomllib.loads(PROFIL.read_text(encoding="utf-8"))

        def renderer_bauen(b, ziel):
            return renderer.bauen(b, ziel, profil=profil, vorschau=False)
    docx = ordner / "Recherche.docx"
    renderer_bauen(webpruefung.beschreibung(titel, daten, reg), docx)

    z, e1 = daten["zahlen"], erste
    melden(f"Webauftrag fertig: {z['belegt']} von {z['aussagen']} Aussagen belegt, {z['unbelegt']} unbelegt. "
           f"Belege: {z['bestanden']} bestanden, {z['durchgefallen']} durchgefallen, {z['ungeprueft']} ungeprüft "
           f"(erste Prüfung: {e1['bestanden']}/{e1['durchgefallen']}/{e1['ungeprueft']}). "
           f"Lücken: {len(daten['luecken'])}, Rückfragen: {len(daten['rueckfragen'])}. "
           f"Kosten {kosten.summe:.2f} USD in {kosten.laeufe} Läufen. Datei: {docx}")
    logger.info("Webauftrag %s fertig: %s, %.4f USD", ordner.name, z, kosten.summe)
    return ordner


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not Path(argv[1]).is_file():
        print("Aufruf: webauftrag.py <auftragsdatei>", file=sys.stderr)
        return 2
    try:
        print(ausfuehren(Path(argv[1]).resolve()))
    except (webpruefung.WebFehler, agent.KostenGrenze, claude_lauf.LaufFehler):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
