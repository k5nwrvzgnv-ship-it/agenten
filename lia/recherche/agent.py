"""Agent recherche in Lias Instanz (AGENTKIT_INSTANZ=lia/instanz): Quellenregister für die Examensreihe.

Ein Lauf (Teil B, ohne Claude und ohne Timer):
1. quellen.toml lesen (quellen.py), Allowlist steht dort.
2. Jede URL über agentkit.abruf.laden holen. Cache in data/roh/: Was dort liegt, wird nicht neu geladen.
3. Text auslesen (auslesen.py), Textfassung mit "--- Seite N" nach data/text/<id>.txt.
4. Gemeinfreiheit prüfen (gemeinfrei.py), Eintrag ins Register data/register.json (register.py).
Fehler bei einer Quelle: loggen, alter Registereintrag bleibt, am Ende eine Meldung an Jan (nicht an Lia).
Ebenso, wenn sich die Gemeinfreiheit einer Quelle ändert oder Stellen verworfen werden.
"""

from datetime import date
from pathlib import Path

import auslesen
import gemeinfrei
import quellen
import register
from agentkit import abruf, config, log, meldungen

AGENT = "recherche"
HIER = Path(__file__).resolve().parent
logger = log.hole_logger(HIER, AGENT)


class QuelleFehler(Exception):
    pass


def jan_melden(text: str, basis: Path | None = None) -> None:
    """Meldung in Jans Instanz (seine Zentrale), nicht in Lias. Wie lia/unterricht."""
    meldungen.melden(AGENT, f"Lia, Agent recherche: {text}", basis=basis or config.KONTINGENT_DIR / "meldungen")


def quelle_verarbeiten(q: dict, allowlist, hier: Path, alt: dict | None, jahr: int,
                       laden=abruf.laden) -> tuple[dict, list[str], int]:
    """Lädt, liest aus, schreibt die Textfassung. Gibt (Eintrag, Hinweise für Jan, neu geladen) zurück."""
    metas, seiten, normtext, neu = [], {}, None, 0
    for i, url in enumerate(q["urls"]):
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
    return register.eintrag(q, metas, str(textpfad), text, frei, stellen), hinweise, neu


def lauf(hier: Path = HIER, laden=abruf.laden, melden=jan_melden, jahr: int | None = None) -> list[str]:
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
        except (abruf.AbrufFehler, auslesen.ParserFehler, QuelleFehler, OSError) as f:
            logger.error("Quelle %s: %s", q["id"], f)
            fehler.append(f"{q['id']}: {f}")
            if q["id"] in alt:
                eintraege.append(alt[q["id"]])
            continue
        logger.info("Quelle %s: %d URLs, %d neu geladen, Gemeinfreiheit %s, %d Stellen",
                    q["id"], len(q["urls"]), neu, e["gemeinfreiheit"]["status"], len(e["stellen"]))
        eintraege.append(e)
        hinweise += h
    register.speichern(reg_pfad, eintraege)
    if fehler or hinweise:
        teile = ([f"{len(fehler)} Fehler:"] + fehler if fehler else []) + hinweise
        melden("Quellenregister. " + "\n".join(teile))
    return fehler


if __name__ == "__main__":
    lauf()
