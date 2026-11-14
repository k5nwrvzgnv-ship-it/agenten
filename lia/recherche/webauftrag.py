"""Webauftrag: Ein Rechercheauftrag (Textdatei) wird von Claude im Web recherchiert und von Python geprüft.

Aufruf (vorerst von Hand, Lias Zentrale folgt in Teil C):
    AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python webauftrag.py <auftragsdatei> [--anhang <pfad>]
    AGENTKIT_INSTANZ=... .venv/bin/python webauftrag.py --nur-traegt data/web/<id>
    AGENTKIT_INSTANZ=... .venv/bin/python webauftrag.py --an-lia data/web/<id>

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
Kopfzeilen (Jan 14.11.2026, für andere Fächer), ganz oben im Auftrag, alle freiwillig:
    FACH: Darstellendes Spiel     Kopf des Dokuments; das Kant/Liszt-Register geht nur bei Ethik mit (Standard Ethik)
    TITEL: Auslöser für ...       Titel und Dateiname (ohne: „Recherche vom <Datum>“, Recherche.docx)
    AUFWAND: gross                großer, wichtiger Auftrag: Vertiefungsrunden in derselben Sitzung (je Runde neue
                                  claude-Schritte), Kostengrenze GRENZE_GROSS_USD; ohne: normal (ein Lauf)
Kostengrenze GRENZE_USD (agent.Kosten) bzw. GRENZE_GROSS_USD je Auftrag. Vertiefungsrunden nur, solange
höchstens RESERVE der Grenze verbraucht ist (Rest für Nachbesserung und Prüflauf).
PDF-Quellen: Python prüft Zitate auch in PDFs (Text über agentkit.textfassung).
An Lia (nach Jans Durchsicht): --an-lia data/web/<id> baut die PDF und legt sie mit Kern und Punkten in Lias
Warteschlange (ohne Feedback-Knöpfe, je Ordner einmal).
"""

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import agent
import anhaenge
import auslesen
import register
import traegt
import webpruefung
from agentkit import abruf, auftraege, claude_lauf, config, einstellungen, sprache, textfassung

HIER = agent.HIER
logger = agent.logger
PROFIL = HIER / "profil.toml"
MAX_ZITAT = 300
KOPF = ("FACH", "TITEL", "AUFWAND")
AUFWAENDE = {"normal": "normal", "gross": "gross", "groß": "gross"}
GRENZE_GROSS_USD = 25.0  # Jan 14.11.2026: große Aufträge brauchen Qualität, Kosten zweitrangig
VERTIEFUNGEN = 3         # Vertiefungsrunden bei AUFWAND: gross
RESERVE = 0.7            # Vertiefung nur bis 70 % der Grenze
STANDARD_FACH = "Ethik"


def kopf_lesen(text: str) -> dict:
    """Kopfzeilen FACH, TITEL, AUFWAND ganz oben im Auftrag (bis zur ersten anderen Zeile). Ergebnis mit
    Standardwerten: {"fach", "titel" ("" = keiner), "aufwand" ("normal" | "gross")}. Unbekannter Aufwand: WebFehler."""
    kopf = {}
    for zeile in text.splitlines():
        if not zeile.strip():
            continue
        m = re.match(r"^\s*([A-Z]+)\s*:\s*(.*?)\s*$", zeile)
        if not m or m.group(1) not in KOPF:
            break
        kopf[m.group(1).lower()] = m.group(2)
    aufwand = kopf.get("aufwand", "normal").lower()
    if aufwand not in AUFWAENDE:
        raise webpruefung.WebFehler(f"AUFWAND {kopf['aufwand']!r} unbekannt (erlaubt: normal, gross)")
    return {"fach": kopf.get("fach") or STANDARD_FACH, "titel": kopf.get("titel", ""), "aufwand": AUFWAENDE[aufwand]}


def mit_register(kopf: dict) -> bool:
    """Das Quellenregister (Kant, Liszt, StGB, JGG) gehört zu Lias Ethik-Reihe."""
    return kopf["fach"].strip().lower() == "ethik"


def dateiname(kopf: dict) -> str:
    """docx-Name aus dem Titel (ohne Zeichen, die Dateisysteme stören), sonst Recherche.docx."""
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", kopf.get("titel", ""))
    name = re.sub(r"\s+", " ", name).strip(" .")[:80].strip()
    return f"{name or 'Recherche'}.docx"


def dokument_titel(kopf: dict, jetzt: datetime | None = None) -> str:
    return kopf.get("titel") or f"Recherche vom {jetzt or datetime.now():%d.%m.%Y}"


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


def prompt(auftrag: str, reg_text: str | None, domains: list[str], ausgabe: str, beilagen: list[str] = (),
           gross: bool = False) -> str:
    """reg_text None: ohne Quellenregister (anderes Fach). gross: großer Auftrag mit Vertiefungsrunden."""
    if reg_text is None:
        register_teil, beleg_art = "", '{"url": "...", "zitat": "..."}'
        beispiel = '{"url": "https://...", "zitat": "..."}'
    else:
        register_teil = f"""
BEREITS GEPRÜFTE QUELLEN (Quellenregister; wörtlich geprüft, Liszt-Stellen vom Scan abgeschrieben).
Du darfst sie als Beleg nutzen mit {{"register": "<quelle>:<seite>"}}, genau mit dem Verweis vor der Klammer:
{reg_text}
"""
        beleg_art = '{"url": "...", "zitat": "..."} oder\n  {"register": "<quelle>:<seite>"}'
        beispiel = '{"url": "https://...", "zitat": "..."},\n{"register": "kant-mds-strafrecht:331"}'
    if gross:
        umfang = """- Das ist ein großer, wichtiger Auftrag. Qualität geht vor Tempo und Kosten. Lies Quellen selbst (WebFetch),
  statt dich auf Suchergebnisse zu verlassen. Suche Fachliteratur, Primärquellen, Unterrichtsmaterial und
  Gegenpositionen. Prüfe wichtige Aussagen an zwei Quellen, wo das geht. PDFs auf der Liste sind erlaubt.
- Ein Lauf endet nach etwa 30 Schritten. Schreibe die Datei früh und ergänze sie nach jedem Teil. Danach folgen
  Vertiefungsrunden in derselben Sitzung, in denen du weiterarbeitest."""
    else:
        umfang = "- Arbeite sparsam: höchstens etwa 20 Werkzeugaufrufe. Schreibe die Datei früh und ergänze sie dann."
    anhang = ("\nANHÄNGE zum Auftrag (mit Read lesen; bei pdf/docx liegt eine Textfassung .txt daneben):\n"
              + "\n".join(f"- {b}" for b in beilagen) + "\nAndere Pfade aus dem Auftrag sind nicht lesbar.\n"
              if beilagen else "")
    return f"""Aufgabe: Recherchiere den folgenden Auftrag im Web und schreibe das Ergebnis als JSON in eine Datei.

AUFTRAG (von der Lehrkraft, wörtlich):
<<<
{auftrag}
>>>
{anhang}{register_teil}
WERKZEUGE
- WebSearch zum Finden. WebFetch funktioniert nur für diese Domains (andere werden abgelehnt):
  {", ".join(domains)}
- Quellen außerhalb dieser Liste darfst du nennen, sie gelten aber als ungeprüft und belegen nichts.
{umfang}

REGELN (wichtig)
- Nichts erfinden. Keine Fälle, Zahlen, Zitate, Titel, Längen oder Links, die du nicht selbst gefunden hast.
- Jede Aussage braucht Belege. Ein Beleg ist {beleg_art}.
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
- "kern": 2-3 kurze Sätze an die Lehrkraft, in der du-Form: das wichtigste Ergebnis und was sie entscheiden muss.
  Jeder Satz höchstens 15 Wörter, einfache Wörter, keine Abkürzungen, Links oder Dateinamen.
  "punkte": höchstens 3 Stichpunkte mit dem Wichtigsten, je höchstens 12 Wörter.

AUSGABE: Schreibe NUR in die Datei {ausgabe}, als JSON:
{{"kern": "...", "punkte": ["..."], "abschnitte": [{{"titel": "...", "aussagen": [{{"text": "...", "belege": [
{beispiel}]}}]}}], "luecken": ["..."], "rueckfragen": ["..."]}}
Gliedere die Abschnitte nach den Teilen des Auftrags. Antworte danach mit einem Satz."""


def vertiefung_prompt(runde: int, runden: int, daten: dict, ausgabe: str) -> str:
    """Nächste Runde eines großen Auftrags: Stand der Prüfung und gezielte Aufträge zum Vertiefen."""
    z = daten["zahlen"]
    unbelegt = [f"- {a['titel'][:60]}: {s['text'][:160]}" for a in daten["abschnitte"] for s in a["aussagen"]
                if not s["belegt"] and not s["text"].startswith("Einschätzung")]
    ungeprueft = sum(1 for a in daten["abschnitte"] for s in a["aussagen"] for b in s.get("belege", [])
                     if b.get("pruefung", {}).get("status") == "ungeprueft")
    fallen = webpruefung.durchgefallene(daten)
    teile = [f"Vertiefungsrunde {runde} von {runden}. Python hat deine Datei {ausgabe} geprüft: {z['aussagen']} "
             f"Aussagen, {z['belegt']} belegt; Belege {z['bestanden']} bestanden, {z['durchgefallen']} durchgefallen, "
             f"{ungeprueft} ungeprüft (Quelle nicht auf der Liste)."]
    if fallen:
        teile.append("Durchgefallene Belege (korrigieren oder ersetzen):\n" + "\n".join(f"- {x}" for x in fallen[:40]))
    if unbelegt:
        teile.append("Tatsachenaussagen ohne bestandenen Beleg (belegen oder als Lücke führen):\n"
                     + "\n".join(unbelegt[:40]))
    if daten.get("luecken"):
        teile.append("Deine Lücken (schließen, wo es geht):\n" + "\n".join(f"- {x[:200]}" for x in daten["luecken"]))
    teile.append(f"""Vertiefe jetzt den Auftrag:
- Schließe Lücken und belege schwache Aussagen. Lies Quellen selbst, statt Suchergebnisse zu übernehmen.
- Ergänze, was für die Lehrkraft fehlt: weitere Quellen, Fachliteratur, Gegenpositionen, Beispiele, Übungen.
- Ungeprüfte Belege ersetzt du nach Möglichkeit durch Quellen von der Liste.
- Behalte, was gut belegt ist. Lösche nichts Gutes. Aktualisiere "kern" und "punkte".
- Dieselben Regeln wie oben: nichts erfinden, Zitate wörtlich, Einschätzungen kennzeichnen.
Schreibe die VOLLSTÄNDIGE Datei {ausgabe} neu, im selben Format. Antworte danach mit einem Satz.""")
    return "\n\n".join(teile)


def seiten_text(inhalt: bytes, content_type: str | None, pdf_text) -> str:
    """Text einer geladenen Seite: PDF über pdf_text(inhalt), sonst HTML ohne Tags."""
    if inhalt[:5] == b"%PDF-" or "pdf" in (content_type or "").lower():
        text = pdf_text(inhalt)
        if not text:
            raise abruf.AbrufFehler("PDF ohne lesbaren Text")
        return text
    return abruf.html_zu_text(auslesen.html_text(inhalt, content_type))


def _pdf_text_standard(cache: Path):
    def pdf_text(inhalt: bytes) -> str:
        cache.mkdir(parents=True, exist_ok=True)
        import hashlib
        pfad = cache / f"pdf-{hashlib.sha256(inhalt).hexdigest()[:16]}.pdf"
        pfad.write_bytes(inhalt)
        try:
            text = textfassung.als_text(pfad) or ""
        except Exception as e:  # kaputte PDFs: pypdf wirft verschiedenste Fehler
            raise abruf.AbrufFehler(f"PDF nicht lesbar: {e}") from None
        return "" if text.startswith("(Kein Text gefunden") else text
    return pdf_text


def nachbesserung_prompt(liste: list[str], ausgabe: str) -> str:
    zeilen = "\n".join(f"- {x}" for x in liste)
    return f"""Python hat die Belege geprüft. Diese Belege sind durchgefallen:
{zeilen}

Korrigiere sie: Zitat wörtlich von der Seite übernehmen (WebFetch erneut nutzen, keine Zusammenfassung), anderen
Beleg suchen, oder den Beleg entfernen. Eine Aussage ohne gültigen Beleg verschiebst du nach "luecken" oder lässt
sie ohne Beleg stehen (dann erscheint sie unter „Nicht belegt“). Nichts erfinden.
Schreibe die VOLLSTÄNDIGE, korrigierte Datei neu nach {ausgabe}, im selben Format. Antworte danach mit einem Satz."""


def adresse(url: str) -> str:
    """URL nur aus ASCII-Zeichen (Umlaute im Pfad prozentkodiert, Host als IDNA); urllib lehnt sonst ab."""
    t = urlsplit(url.strip())
    host = (t.hostname or "").encode("idna").decode("ascii") + (f":{t.port}" if t.port else "")
    sicher = "/%:@!$&'()*+,;=-._~"
    return urlunsplit((t.scheme, host, quote(t.path, safe=sicher), quote(t.query, safe=sicher + "?"), ""))


def seitenleser(domains: list[str], cache: Path):
    """seitentext(url) für webpruefung: lädt über agentkit.abruf (Allowlist = Jans Domains), Text ohne HTML."""
    texte = {}

    def seitentext(url: str) -> str:
        if url not in texte:
            erg = abruf.laden(adresse(url), domains, cache)
            texte[url] = seiten_text(erg.inhalt, erg.meta.get("content_type"), _pdf_text_standard(cache))
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
    kopf = daten.setdefault("kopf", {"fach": STANDARD_FACH, "titel": "", "aufwand": "normal"})
    daten["datei"] = dateiname(kopf)
    (ordner / "geprueft.json").write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    titel = dokument_titel(kopf)
    if renderer_bauen is None:
        import tomllib

        import renderer
        profil = tomllib.loads(PROFIL.read_text(encoding="utf-8"))
        profil["fach"] = kopf["fach"]

        def renderer_bauen(b, ziel):
            return renderer.bauen(b, ziel, profil=profil, vorschau=False)
    docx = ordner / daten["datei"]
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


def _vertiefen(daten: dict, erg, ordner: Path, hier: Path, ausgabe: Path, lauf, kosten, neu_pruefen):
    """Vertiefungsrunden eines großen Auftrags in derselben Sitzung. Jede Runde beginnt mit einer Sicherung
    (ergebnis_runde<n>.json). Ist die Datei danach kaputt, gilt die Sicherung und es geht ohne weitere Runde weiter.
    Ist mehr als RESERVE der Kostengrenze verbraucht, endet die Vertiefung (Rest für Nachbesserung und Prüflauf)."""
    for n in range(1, VERTIEFUNGEN + 1):
        if kosten.summe >= kosten.grenze * RESERVE:
            logger.info("Webauftrag %s: Vertiefung nach %d Runden beendet (%.2f von %.2f USD)", ordner.name, n - 1,
                        kosten.summe, kosten.grenze)
            break
        sicherung = ordner / f"ergebnis_runde{n - 1}.json"
        shutil.copyfile(hier / ausgabe, sicherung)
        neu_erg = lauf(vertiefung_prompt(n, VERTIEFUNGEN, daten, str(ausgabe)), erg.sitzung, f"Vertiefung {n}")
        erg = neu_erg if neu_erg.sitzung else erg
        try:
            daten = neu_pruefen()
        except webpruefung.WebFehler as f:
            logger.warning("Webauftrag %s: Datei nach Vertiefung %d unbrauchbar (%s), Stand davor gilt",
                           ordner.name, n, f)
            shutil.copyfile(sicherung, hier / ausgabe)
            daten = neu_pruefen()
            break
        logger.info("Webauftrag %s: nach Vertiefung %d: %s", ordner.name, n, daten["zahlen"])
    return daten, erg


def ausfuehren(datei: Path, hier: Path = HIER, laufen=None, seitentext=None, renderer_bauen=None,
               melden=agent.jan_melden, cfg: dict | None = None, kosten: agent.Kosten | None = None,
               anhang: list[str] = (), als_text=textfassung.als_text,
               anhang_wurzel: Path = anhaenge.ERLAUBT_UNTER) -> Path:
    """Ein Webauftrag. Gibt den Ordner data/web/<id>/ zurück."""
    cfg = cfg or einstellungen.lade()
    domains = einstellungen.webfetch_domains(cfg, agent.AGENT) or []
    kopf = kopf_lesen(Path(datei).read_text(encoding="utf-8"))
    gross = kopf["aufwand"] == "gross"
    kosten = kosten or agent.Kosten(grenze=GRENZE_GROSS_USD if gross else agent.GRENZE_USD)
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

    if not mit_register(kopf):
        reg, stellen = {}, {}

    try:
        erg = lauf(prompt(auftrag, register_text(reg) if reg else None, domains, str(ausgabe), beilagen, gross),
                   None, "Recherche")
        daten = webpruefung.pruefen(webpruefung.lesen(hier / ausgabe), domains, seitentext, stellen)
        if gross:
            daten, erg = _vertiefen(daten, erg, ordner, hier, ausgabe, lauf, kosten,
                                    lambda: webpruefung.pruefen(webpruefung.lesen(hier / ausgabe), domains,
                                                                seitentext, stellen))
        nachbesserung = webpruefung.durchgefallene(daten)
        erste = dict(daten["zahlen"])
        if nachbesserung:
            logger.info("Webauftrag %s: %d Belege durchgefallen, Nachbesserung", ordner.name, len(nachbesserung))
            (ordner / "ergebnis_1.json").write_text((hier / ausgabe).read_text(encoding="utf-8"), encoding="utf-8")
            lauf(nachbesserung_prompt(nachbesserung, str(ausgabe)), erg.sitzung, "Nachbesserung")
            daten = webpruefung.pruefen(webpruefung.lesen(hier / ausgabe), domains, seitentext, stellen)
        daten["erste_pruefung"] = erste
        daten["kopf"] = kopf
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


def nachricht_an_lia(daten: dict) -> tuple[str, dict]:
    """Text und daten (shared/telegram/vorlagen.py) für Lias Zentrale aus kern und punkte. Ohne kern oder mit
    Verstoß gegen die Sprachregel: WebFehler (dann kern/punkte in geprueft.json von Hand anpassen)."""
    if not daten.get("kern"):
        raise webpruefung.WebFehler("Kein Kern im Ergebnis; kern und punkte in geprueft.json von Hand eintragen")
    kern = f"{daten['kern']} Antworte direkt auf diese Nachricht, gern per Diktat."
    text = kern + "".join(f"\n- {x}" for x in daten.get("punkte", []))
    befunde = sprache.pruefen(text, sprache.LIA)
    if befunde:
        raise webpruefung.WebFehler(f"Nachricht verletzt die Sprachregel ({sprache.log_text(befunde)}); kern/punkte "
                                    "in geprueft.json kürzen")
    # Keine Feedback-Knöpfe: „Passt“ sagt bei einer Recherche nicht, was passt (wie Fallsuche, Jan 27.10.).
    return text, {"kern": kern, "punkte": daten.get("punkte", []), "knoepfe": "nur_antwort"}


def _pdf_standard(docx: Path) -> Path:
    from renderer import vorschau
    return vorschau.als_pdf(docx, docx.parent)


def an_lia(ordner: Path, pdf_bauen=None, basis: Path | None = None, agenten_dir: Path | None = None) -> str:
    """Fertigen Webauftrag (nach Jans Durchsicht) an Lias Zentrale: PDF in ihre Auftrags-Warteschlange, ohne
    Claude-Lauf, je Ordner einmal (geprueft.json "an_lia"). Braucht AGENTKIT_INSTANZ=Lias Instanz."""
    pfad = ordner / "geprueft.json"
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    if daten.get("an_lia"):
        raise webpruefung.WebFehler(f"Schon an Lia geschickt: {daten['an_lia']['auftrag']}")
    text, nachricht = nachricht_an_lia(daten)
    docx = ordner / daten.get("datei", "Recherche.docx")
    if not docx.exists():
        raise webpruefung.WebFehler(f"{docx.name} fehlt in {ordner.name}")
    pdf = docx.with_suffix(".pdf")
    if not pdf.exists() or pdf.stat().st_mtime < docx.stat().st_mtime:
        pdf = (pdf_bauen or _pdf_standard)(docx)
    titel = "Recherche: " + (daten.get("kopf", {}).get("titel") or ordner.name)
    aid = auftraege.neuer_auftrag(agent.AGENT, titel[:120], quelle="webauftrag", basis=basis, agenten_dir=agenten_dir)
    auftraege.abschliessen(aid, text, dateien=[pdf], daten=nachricht, basis=basis, agenten_dir=agenten_dir)
    daten["an_lia"] = {"auftrag": aid, "zeit": datetime.now().isoformat(timespec="seconds"), "datei": pdf.name}
    pfad.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    logger.info("Webauftrag %s an Lia (Auftrag %s)", ordner.name, aid)
    return aid


def main(argv: list[str]) -> int:
    teiler = argparse.ArgumentParser(prog="webauftrag.py", description="Webauftrag recherchieren und prüfen.")
    teiler.add_argument("auftrag", nargs="?", help="Auftragsdatei (Text)")
    teiler.add_argument("--anhang", action="append", default=[], help="Datei für Claude (mehrfach erlaubt)")
    teiler.add_argument("--nur-traegt", metavar="ORDNER", help="nur den Prüflauf auf data/web/<id> anwenden")
    teiler.add_argument("--an-lia", metavar="ORDNER", help="fertigen Auftrag data/web/<id> an Lias Zentrale")
    args = teiler.parse_args(argv[1:])
    try:
        if args.an_lia:
            if config.INSTANZ_NAME != "lia":  # sonst landet es in Jans Warteschlange
                print("--an-lia nur mit AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz", file=sys.stderr)
                return 2
            print(an_lia(Path(args.an_lia).resolve()))
        elif args.nur_traegt:
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
