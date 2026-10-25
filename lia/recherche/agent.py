"""Agent recherche in Lias Instanz (AGENTKIT_INSTANZ=lia/instanz): Quellenregister für die Examensreihe.

Ein Lauf (Teil B, ohne Claude und ohne Timer):
1. quellen.toml lesen (quellen.py), Allowlist steht dort.
2. Jede URL über agentkit.abruf.laden holen. Cache in data/roh/: Was dort liegt, wird nicht neu geladen.
3. Text auslesen (auslesen.py), Textfassung mit "--- Seite N" nach data/text/<id>.txt.
4. Gemeinfreiheit prüfen (gemeinfrei.py), Eintrag ins Register data/register.json (register.py).
5. Teil C: Für verwendbare Primärtexte ohne Stellen wählt Claude (Opus, agentkit.claude_lauf, ohne Bash)
   Kernstellen (kernstellen.py). Python prüft sie wörtlich; Durchgefallenes geht einmal an Claude zurück
   (dieselbe Sitzung), danach wird es gestrichen. Je Textfassung (sha256) nur ein Versuch, auch wenn
   weniger als 3 Stellen bestehen: Ein nächtlicher Lauf soll nicht jede Nacht neu bezahlen.
   Kosten je Claude-Lauf werden geloggt; über GRENZE_USD je agent.py-Lauf startet kein weiterer.
6. Scan-Quellen (scan_id, Liszt): Textfassung = OCR je Druckseite (scan.py), nur zur Orientierung.
   Kernstellen vom Seitenbild (seitenbild.py): Auswahl, Bilder laden, zwei unabhängige Abschriften,
   bei Abweichung eine dritte, Prüfung gegen die OCR. Lia prüft jede Stelle am Scan.
Fehler bei einer Quelle: loggen, alter Registereintrag bleibt, am Ende eine Meldung an Jan (nicht an Lia).
Ebenso, wenn sich die Gemeinfreiheit einer Quelle ändert, Stellen verworfen werden oder Claude gelaufen ist.
"""

import json
import tomllib
from datetime import date
from pathlib import Path

import abschrift
import auslesen
import gemeinfrei
import kernstellen
import quellen
import register
import scan
import seitenbild
from agentkit import abruf, claude_lauf, config, log, meldungen, wortlaut

AGENT = "recherche"
HIER = Path(__file__).resolve().parent
logger = log.hole_logger(HIER, AGENT)
GRENZE_USD = 8.0  # je Lauf von agent.py (Jan, 25.10.2026: 8 USD pro Nacht)
REIHEN = HIER.parent / "unterricht" / "reihen.toml"  # gehört lia/unterricht, hier nur gelesen


class QuelleFehler(Exception):
    pass


class KostenGrenze(Exception):
    pass


class Kosten:
    def __init__(self, grenze: float = GRENZE_USD):
        self.grenze, self.summe, self.laeufe = grenze, 0.0, 0

    def vorher(self):
        if self.summe >= self.grenze:
            raise KostenGrenze(f"Kostengrenze {self.grenze:.2f} USD erreicht ({self.summe:.2f} USD), kein weiterer Claude-Lauf")

    def dazu(self, erg, wofuer: str):
        self.summe += erg.usd or 0
        self.laeufe += 1
        logger.info("Claude-Lauf %s: %.4f USD, %d Tokens, %d Schritte, %.0f s, ok=%s, Summe %.4f USD",
                    wofuer, erg.usd or 0, erg.tokens, erg.schritte, erg.dauer_s, erg.ok, self.summe)


def jan_melden(text: str, basis: Path | None = None) -> None:
    """Meldung in Jans Instanz (seine Zentrale), nicht in Lias. Wie lia/unterricht."""
    meldungen.melden(AGENT, f"Lia, Agent recherche: {text}", basis=basis or config.KONTINGENT_DIR / "meldungen")


def claude_laufen(prompt: str, sitzung: str | None = None):
    return claude_lauf.laufen(AGENT, HIER, prompt, art="anspruchsvoll", sitzung_fortsetzen=sitzung)


def reihe_laden(pfad: Path) -> str:
    """Reihe Straftheorien als Prompt-Abschnitt. Fehlt oder kaputt: leer, mit Log (Claude läuft trotzdem)."""
    try:
        with open(pfad, "rb") as f:
            return kernstellen.reihe_text(tomllib.load(f).get("reihe", []))
    except (OSError, tomllib.TOMLDecodeError) as e:
        logger.warning("Reihenkontext fehlt (%s): %s", pfad, e)
        return ""


def kernstellen_finden(e: dict, q: dict, hier: Path, reihe: str, laufen, kosten: Kosten) -> list[str]:
    """Füllt e["stellen"] und e["kernstellen"] (Lauf-Angaben). Gibt Hinweise für Jan zurück."""
    text = (hier / e["textfassung"]).read_text(encoding="utf-8")
    ausgabe = Path("data") / "kernstellen" / f"{q['id']}.json"
    (hier / ausgabe).parent.mkdir(parents=True, exist_ok=True)
    (hier / ausgabe).unlink(missing_ok=True)
    usd_vorher = kosten.summe

    kosten.vorher()
    erg = laufen(kernstellen.prompt(q, e["textfassung"], str(ausgabe), reihe))
    kosten.dazu(erg, f"{q['id']} Auswahl")
    if not erg.ok:
        raise kernstellen.KernstellenFehler(f"Claude-Lauf fehlgeschlagen: {erg.text[:300]}")
    gut, schlecht = kernstellen.pruefen(kernstellen.antwort_lesen(hier / ausgabe), text)
    if schlecht and len(gut) < kernstellen.MAX_STELLEN:
        logger.info("%s: %d Stellen durchgefallen, eine Nachbesserung", q["id"], len(schlecht))
        (hier / ausgabe).unlink(missing_ok=True)
        kosten.vorher()
        erg = laufen(kernstellen.nachbesserung_prompt(schlecht, e["textfassung"], str(ausgabe)), erg.sitzung)
        kosten.dazu(erg, f"{q['id']} Nachbesserung")
        neu = kernstellen.antwort_lesen(hier / ausgabe) if erg.ok else []
        gut2, schlecht = kernstellen.pruefen(neu, text, schon=gut)
        gut += gut2
    gut = gut[:kernstellen.MAX_STELLEN]
    e["stellen"] = gut
    e["kernstellen"] = {"sha256": e["sha256"], "datum": date.today().isoformat(),
                        "usd": round(kosten.summe - usd_vorher, 4),
                        "gestrichen": [{"seite": d["stelle"].get("seite") if isinstance(d["stelle"], dict) else None,
                                        "grund": d["grund"]} for d in schlecht]}
    for d in schlecht:
        logger.warning("%s: Stelle gestrichen: %s (%r)", q["id"], d["grund"], d["stelle"])
    liste = ", ".join(f"S. {s['seite']} {s['position']}" for s in gut)
    hinweise = [f"{q['id']}: {len(gut)} Stellen geprüft ({liste}), {e['kernstellen']['usd']:.2f} USD"]
    if schlecht:
        hinweise.append(f"{q['id']}: {len(schlecht)} gestrichen: "
                        + "; ".join(f"S. {g['seite']}: {g['grund']}" for g in e["kernstellen"]["gestrichen"]))
    if len(gut) < kernstellen.MIN_STELLEN:
        hinweise.append(f"{q['id']}: nur {len(gut)} Stellen, erwartet {kernstellen.MIN_STELLEN} bis "
                        f"{kernstellen.MAX_STELLEN}. Kein neuer Versuch, solange die Textfassung gleich bleibt.")
    return hinweise


def _kernstellen_merken(e: dict, kosten: Kosten, usd_vorher: float, gestrichen: list[dict]) -> None:
    e["kernstellen"] = {"sha256": e["sha256"], "datum": date.today().isoformat(),
                        "usd": round(kosten.summe - usd_vorher, 4), "gestrichen": gestrichen}


def seitenbild_finden(e: dict, q: dict, hier: Path, reihe: str, laufen, kosten: Kosten, laden, allowlist) -> list[str]:
    """Kernstellen vom Seitenbild (seitenbild.py). Füllt e["stellen"], gibt Hinweise für Jan zurück."""
    ocr = wortlaut.seiten((hier / e["textfassung"]).read_text(encoding="utf-8"))
    von, bis = q["druckseiten"]
    ordner = Path("data") / "kernstellen"
    (hier / ordner).mkdir(parents=True, exist_ok=True)
    usd_vorher = kosten.summe

    # Eine geprüfte Auswahl zur selben Textfassung wird wiederverwendet (z. B. nach Abbruch der Abschriften
    # wegen Kontingent), damit sie nicht zweimal bezahlt wird.
    gemerkt = hier / ordner / f"{q['id']}_auswahl_geprueft.json"
    alt = json.loads(gemerkt.read_text(encoding="utf-8")) if gemerkt.exists() else {}
    if alt.get("sha256") == e["sha256"]:
        auswahl, verworfen = alt["stellen"], alt["verworfen"]
        logger.info("%s: gespeicherte Auswahl (%d Stellen) wiederverwendet", q["id"], len(auswahl))
    else:
        ausgabe = ordner / f"{q['id']}_auswahl.json"
        (hier / ausgabe).unlink(missing_ok=True)
        kosten.vorher()
        erg = laufen(seitenbild.auswahl_prompt(q, e["textfassung"], str(ausgabe), reihe, von, bis))
        kosten.dazu(erg, f"{q['id']} Auswahl")
        if not erg.ok:
            raise seitenbild.SeitenbildFehler(f"Auswahl-Lauf fehlgeschlagen: {erg.text[:300]}")
        auswahl, verworfen = seitenbild.auswahl_pruefen(hier / ausgabe, von, bis)
        gemerkt.write_text(json.dumps({"sha256": e["sha256"], "stellen": auswahl, "verworfen": verworfen},
                                      ensure_ascii=False, indent=1), encoding="utf-8")
    gestrichen = [{"seite": None, "grund": f"Auswahl: {g}"} for g in verworfen]

    bilder = {}
    for s in sorted({x for a in auswahl for x in a["seiten"]}):
        erg_bild = laden(scan.bild_url(e["scan_id"], e["scan_n"][str(s)]), allowlist, hier / "data" / "roh")
        pfad = Path("data") / "bilder" / q["id"] / f"s{s}.jpg"
        (hier / pfad).parent.mkdir(parents=True, exist_ok=True)
        (hier / pfad).write_bytes(erg_bild.inhalt)
        bilder[s] = str(pfad)

    def abschreiben(stellen: list[dict], name: str) -> dict[int, str]:
        datei = ordner / f"{q['id']}_abschrift_{name}.json"
        nrn = [s["nr"] for s in stellen]
        # Schon bezahlte Abschrift derselben Textfassung und derselben Stellen wiederverwenden
        merk = hier / ordner / f"{q['id']}_abschrift_{name}_merk.json"
        alt = json.loads(merk.read_text(encoding="utf-8")) if merk.exists() else {}
        if alt.get("sha256") == e["sha256"] and alt.get("nrn") == nrn and (hier / datei).exists():
            logger.info("%s: gespeicherte Abschrift %s wiederverwendet", q["id"], name)
            return seitenbild.abschriften_lesen(hier / datei, nrn)
        (hier / datei).unlink(missing_ok=True)
        kosten.vorher()
        erg = laufen(seitenbild.abschrift_prompt(stellen, bilder, str(datei)))  # neue Sitzung, kein Kontext
        kosten.dazu(erg, f"{q['id']} Abschrift {name}")
        if not erg.ok:
            logger.error("%s: Abschrift %s fehlgeschlagen: %s", q["id"], name, erg.text[:300])
            return {}
        try:
            gelesen = seitenbild.abschriften_lesen(hier / datei, nrn)
            merk.write_text(json.dumps({"sha256": e["sha256"], "nrn": nrn}), encoding="utf-8")
            return gelesen
        except seitenbild.SeitenbildFehler as f:
            logger.error("%s: %s", q["id"], f)
            return {}

    a = abschreiben(auswahl, "a") if auswahl else {}
    b = abschreiben(auswahl, "b") if auswahl else {}
    strittig = [s for s in auswahl if a.get(s["nr"]) and b.get(s["nr"])
                and abschrift.vergleichen([a[s["nr"]], b[s["nr"]]])[0] is None
                and "[?]" not in a[s["nr"]] + b[s["nr"]]]
    c = abschreiben(strittig, "c") if strittig else {}

    gut = []
    for s in auswahl:
        fassungen = [a.get(s["nr"]), b.get(s["nr"])] + ([c[s["nr"]]] if s["nr"] in c else [])
        if None in fassungen[:2]:
            gestrichen.append({"seite": s["seiten"][0], "grund": "Abschrift fehlt"})
            continue
        stelle, grund = seitenbild.stelle_pruefen(s, fassungen, ocr, e["scan"])
        if stelle:
            gut.append(stelle)
        else:
            gestrichen.append({"seite": s["seiten"][0], "grund": grund})
            logger.warning("%s: Stelle S. %s verworfen: %s", q["id"], s["seiten"], grund)
    e["stellen"] = gut
    _kernstellen_merken(e, kosten, usd_vorher, gestrichen)
    liste = ", ".join(f"S. {s['seite']} {s['position']} ({s['pruefung']['abschriften_gleich']}, "
                      f"OCR {s['pruefung']['ocr_aehnlichkeit']:.2f})" for s in gut)
    hinweise = [f"{q['id']}: {len(gut)} Stellen vom Scan ({liste}), {e['kernstellen']['usd']:.2f} USD. "
                "Lia prüft jede am Scan."]
    if gestrichen:
        hinweise.append(f"{q['id']}: {len(gestrichen)} verworfen: "
                        + "; ".join(f"S. {g['seite']}: {g['grund']}" for g in gestrichen))
    if len(gut) < seitenbild.MIN_STELLEN:
        hinweise.append(f"{q['id']}: nur {len(gut)} Stellen, erwartet {seitenbild.MIN_STELLEN} bis "
                        f"{seitenbild.MAX_STELLEN}. Kein neuer Versuch, solange die Textfassung gleich bleibt.")
    return hinweise


def scan_verarbeiten(q: dict, allowlist, hier: Path, laden) -> tuple[list[dict], dict, dict[int, int]]:
    """Scan-Quelle: (Metas, OCR je Druckseite, Zuordnung Druckseite -> n)."""
    d = scan.dateien(q["scan_id"])
    erg = {k: laden(u, allowlist, hier / "data" / "roh") for k, u in d.items()}
    try:
        zahlen = json.loads(erg["seitenzahlen"].inhalt)
    except json.JSONDecodeError as f:
        raise QuelleFehler(f"page_numbers.json von {q['scan_id']} ist kein JSON: {f}") from None
    zuord = scan.zuordnung(zahlen, *q["druckseiten"], q["scan_versatz"], q.get("scan_von_hand"))
    ocr = scan.ocr_seiten(erg["text"].inhalt, erg["index"].inhalt, zuord)
    return [erg[k].meta for k in d], ocr, zuord


def braucht_kernstellen(e: dict) -> bool:
    return (e["art"] == "primaertext" and e["gemeinfreiheit"]["verwendbar"] and not e["stellen"]
            and e.get("kernstellen", {}).get("sha256") != e["sha256"])


def quelle_verarbeiten(q: dict, allowlist, hier: Path, alt: dict | None, jahr: int,
                       laden=abruf.laden) -> tuple[dict, list[str], int]:
    """Lädt, liest aus, schreibt die Textfassung. Gibt (Eintrag, Hinweise für Jan, neu geladen) zurück."""
    metas, seiten, normtext, neu, zuord = [], {}, None, 0, None
    if "scan_id" in q:
        metas, seiten, zuord = scan_verarbeiten(q, allowlist, hier, laden)
    for i, url in enumerate([] if zuord else q["urls"]):
        erg = laden(url, allowlist, hier / "data" / "roh")
        neu += not erg.aus_cache
        metas.append(erg.meta)
        html = auslesen.html_text(erg.inhalt, erg.meta.get("content_type"))
        art = auslesen.art_der_seite(url)
        if art == "gesetz":
            if len(q["urls"]) != 1:
                raise QuelleFehler(f"Gesetz {q['id']} braucht genau eine URL")
            g = auslesen.gesetz(html)
            normtext = g.normtext
            seiten[1] = f"{g.ueberschrift}\n{g.normtext}"
        else:
            nummer, text = auslesen.korpora_seite(html)
            erwartet = q.get("seiten", [None] * len(q["urls"]))[i]
            if erwartet is not None and nummer != erwartet:
                raise QuelleFehler(f"{url} ist Seite {nummer}, erwartet {erwartet}")
            if nummer in seiten:
                raise QuelleFehler(f"Seite {nummer} doppelt in {q['id']}")
            seiten[nummer] = text

    text = auslesen.textfassung(seiten)
    textpfad = Path("data") / "text" / f"{q['id']}.txt"
    (hier / textpfad).parent.mkdir(parents=True, exist_ok=True)
    (hier / textpfad).write_text(text, encoding="utf-8")

    hinweise = []
    if q["art"] == "gesetz":
        stelle = register.gesetz_stelle(normtext, text)
        if not stelle["geprueft"]:
            raise QuelleFehler(f"Normtext von {q['id']} steht nicht in der Textfassung")
        stellen = [stelle]
    else:
        stellen, verworfen = register.alte_stellen(alt, text)
        if verworfen:
            hinweise.append(f"{q['id']}: Textfassung geändert, {len(alt['stellen'])} Stellen verworfen")
    frei = gemeinfrei.pruefen(q, jahr)
    if not alt or alt.get("gemeinfreiheit", {}).get("status") != frei["status"]:
        hinweise.append(f"{q['id']}: Gemeinfreiheit {frei['status']} ({frei['begruendung']})")
    e = register.eintrag(q, metas, str(textpfad), text, frei, stellen)
    if zuord:
        e["scan_id"] = q["scan_id"]
        e["scan_n"] = {str(s): n for s, n in zuord.items()}
        e["scan"] = {str(s): scan.link(q["scan_id"], n) for s, n in zuord.items()}
    return e, hinweise, neu


def lauf(hier: Path = HIER, laden=abruf.laden, melden=jan_melden, jahr: int | None = None,
         claude=claude_laufen, reihen: Path = REIHEN, kosten: Kosten | None = None) -> list[str]:
    """Ein Lauf über alle Quellen. Gibt die Fehler zurück (leer = alles gut)."""
    jahr = jahr or date.today().year
    try:
        allowlist, alle = quellen.laden(hier / "quellen.toml")
    except quellen.QuellenFehler as e:
        logger.error("%s", e)
        melden(f"quellen.toml fehlerhaft, kein Lauf: {e}")
        return [str(e)]
    reg_pfad = hier / "data" / "register.json"
    alt = register.laden(reg_pfad)
    eintraege, fehler, hinweise = [], [], []
    for q in alle:
        try:
            e, h, neu = quelle_verarbeiten(q, allowlist, hier, alt.get(q["id"]), jahr, laden)
        except (abruf.AbrufFehler, auslesen.ParserFehler, scan.ScanFehler, QuelleFehler, OSError) as f:
            logger.error("Quelle %s: %s", q["id"], f)
            fehler.append(f"{q['id']}: {f}")
            if q["id"] in alt:
                eintraege.append(alt[q["id"]])
            continue
        if alt.get(q["id"], {}).get("kernstellen", {}).get("sha256") == e["sha256"]:
            e["kernstellen"] = alt[q["id"]]["kernstellen"]
        logger.info("Quelle %s: %d URLs, %d neu geladen, Gemeinfreiheit %s, %d Stellen",
                    q["id"], len(q["urls"]), neu, e["gemeinfreiheit"]["status"], len(e["stellen"]))
        eintraege.append(e)
        hinweise += h

    kosten = kosten or Kosten()
    reihe = None
    for e in eintraege:
        if not braucht_kernstellen(e):
            continue
        q = next(q for q in alle if q["id"] == e["id"])
        reihe = reihe_laden(reihen) if reihe is None else reihe
        try:
            if "scan_id" in e:
                hinweise += seitenbild_finden(e, q, hier, reihe, claude, kosten, laden, allowlist)
            else:
                hinweise += kernstellen_finden(e, q, hier, reihe, claude, kosten)
        except KostenGrenze as f:
            logger.error("%s", f)
            fehler.append(f"{e['id']}: {f}")
            break
        except (kernstellen.KernstellenFehler, seitenbild.SeitenbildFehler, claude_lauf.LaufFehler,
                abruf.AbrufFehler, OSError) as f:
            logger.error("Kernstellen %s: %s", e["id"], f)
            fehler.append(f"{e['id']}: Kernstellen: {f}")
        register.speichern(reg_pfad, eintraege)  # nach jedem bezahlten Lauf sichern
    if kosten.laeufe:
        hinweise.append(f"Kosten: {kosten.summe:.2f} USD in {kosten.laeufe} Claude-Läufen (Grenze {kosten.grenze:.2f} USD)")

    register.speichern(reg_pfad, eintraege)
    if fehler or hinweise:
        teile = ([f"{len(fehler)} Fehler:"] + fehler if fehler else []) + hinweise
        melden("Quellenregister. " + "\n".join(teile))
    return fehler


if __name__ == "__main__":
    lauf()
