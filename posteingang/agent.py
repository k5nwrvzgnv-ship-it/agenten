"""Agent posteingang: Jans privates Postfach jan@kleinke.org lesen und Wichtiges melden (Stufe 1).

Ein Lauf (gestartet vom Timer):
1. neue Mails holen (agentkit.imap, nur lesend) und sofort in data/mails_offen.json speichern,
   damit sie bei einem Ausfall nicht verloren gehen,
2. vorfiltern ohne Claude (vorfilter.py: Spam, Newsletter, Massenmail, gesperrte Absender aus den Regeln),
3. den Rest von Claude einordnen lassen (einordnung.py, art routine). Antwort KEINE = nichts melden,
4. Meldung an Jan mit [post], danach data/mails_offen.json löschen.

Kann Claude gerade nicht (Limit, Pause, Platz), bleiben die Mails offen und kommen im nächsten Lauf dran.

Mail-Aufträge (Stufe 2, gestartet von der Zentrale nach /posteingang oder einer Freigabe):
- Auftrag: Claude nennt Suchbegriffe, Python sucht im Postfach und Kalender (auftrag.py), Claude schreibt
  einen Entwurf oder eine Rückfrage. Der Entwurf geht in die Freigabe, der Kontext bleibt in
  data/auftraege/<auftrag-id>/kontext.json (für Ändern und Antworten auf eine Rückfrage).
- Ändern in Telegram: neuer Entwurf mit demselben Kontext. Antwort auf das Ergebnis: Nachtrag zum Auftrag.
- Freigegeben: genau diese Mail einmal senden (agentkit.mail), Ergebnis trägt die Freigabe ein.
Braucht agentkit.mail und agentkit.imap.suchen (Bedarf Nr. 19 in der Haupt-STATUS.md). Fehlen sie, lehnt
der Agent Mail-Aufträge mit einem Hinweis ab und liest weiter nur.
"""

import json
from datetime import date
from pathlib import Path

from agentkit import auftraege, claude_lauf, config, freigabe, imap, kalender, log, meldungen, regeln

import auftrag
import einordnung
import vorfilter

try:
    from agentkit import mail  # Bedarf Nr. 19b in der Haupt-STATUS.md
except ImportError:
    mail = None

AGENT = "posteingang"
HIER = Path(__file__).resolve().parent
DATA = HIER / "data"
STAND_DATEI = DATA / "postfach.json"
MAILS_OFFEN = DATA / "mails_offen.json"
FEHLER_DATEI = DATA / "schritt_fehler.json"
AUFTRAEGE = DATA / "auftraege"
ENTWUERFE = DATA / "entwuerfe.json"  # Freigabe-ID -> Auftrag-ID, dessen Kontext der Entwurf nutzt
PFLICHT = ("IMAP_HOST", "IMAP_NUTZER", "IMAP_KENNWORT")

logger = log.hole_logger(HIER, AGENT)

WARTEN = (claude_lauf.LimitErreicht, claude_lauf.KeinPlatz, claude_lauf.LaeuftSchon, claude_lauf.Pausiert)


def _lies_json(pfad: Path, standard):
    return json.loads(pfad.read_text()) if pfad.exists() else standard


def _schreibe_json(pfad: Path, daten) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix(".tmp")
    tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=1))
    tmp.replace(pfad)


def melden(text: str) -> str:
    """Hinweis an Jan per Telegram (über die Zentrale), gibt die ID der Meldung zurück."""
    mid = meldungen.melden(AGENT, text)
    logger.info("Meldung: %s", text.splitlines()[0])
    return mid


def neue_mails() -> list[dict]:
    cfg = config.lade_config(HIER, pflicht=PFLICHT)
    return imap.neue_mails(cfg["IMAP_HOST"], int(cfg.get("IMAP_PORT", 993)),
                           cfg["IMAP_NUTZER"], cfg["IMAP_KENNWORT"], STAND_DATEI)


def gesperrte_absender() -> list[str]:
    return vorfilter.gesperrte_absender(regeln.allgemeine_regeln() + regeln.agent_regeln(HIER))


def post_pruefen(holen=neue_mails, laufen=claude_lauf.laufen, melden=melden,
                 gesperrt=gesperrte_absender, offen_datei: Path | None = None) -> None:
    offen_datei = offen_datei or MAILS_OFFEN
    # Geholte Mails erst als offen speichern: Fällt der Claude-Lauf aus, gehen sie nicht verloren.
    offen = _lies_json(offen_datei, []) + holen()
    if not offen:
        return
    _schreibe_json(offen_datei, offen)

    behalten, weg = vorfilter.vorfiltern(offen, gesperrt())
    for m, grund in weg:
        logger.info("Vorgefiltert (%s): uid %s", grund, m["uid"])
    if behalten:
        try:
            e = laufen(AGENT, HIER, einordnung.prompt(behalten), art="routine", zeitgesteuert=True)
        except WARTEN as f:
            logger.info("Post wartet (%d Mails offen): %s", len(offen), f)
            return
        if not e.ok:
            raise claude_lauf.LaufFehler(f"Einordnung fehlgeschlagen, {len(offen)} Mails bleiben offen: {e.text[:300]}")
        if text := einordnung.meldung(e.text, len(behalten), len(weg)):
            melden(text)
        else:
            logger.info("%d Mails geprüft, %d vorgefiltert, nichts Wichtiges", len(behalten), len(weg))
    else:
        logger.info("%d Mails, alle vorgefiltert", len(weg))
    offen_datei.unlink()


# Mail-Aufträge ----------------------------------------------------------------

def _cfg() -> dict:
    return config.lade_config(HIER, pflicht=PFLICHT)


def fehlende_bausteine() -> list[str]:
    fehlt = [] if mail is not None else ["agentkit.mail"]
    return fehlt + ([] if hasattr(imap, "suchen") else ["agentkit.imap.suchen"])


def postfach_suchen(ordner: str, **kriterien) -> list[dict]:
    cfg = _cfg()
    return imap.suchen(cfg["IMAP_HOST"], int(cfg.get("IMAP_PORT", 993)), cfg["IMAP_NUTZER"], cfg["IMAP_KENNWORT"],
                       ordner, **kriterien)


def auftragstext(a: dict, ablage: Path) -> str:
    """Antwort auf ein Ergebnis (bezug mit gespeichertem Kontext): ursprünglicher Auftrag plus Nachtrag."""
    alt = ablage / str(a.get("bezug")) / "kontext.json"
    if a.get("bezug") and alt.exists():
        return f"{_lies_json(alt, {})['text']}\n\nNachtrag von Jan: {a['text']}"
    return a["text"]


def entwurf_einreichen(antwort: str, kontext: dict, auftrag_id: str, vorgaenger: dict | None = None,
                       neuer_entwurf=None, entwuerfe: Path | None = None) -> str:
    """Claudes Antwort prüfen und als Mail-Entwurf in die Freigabe legen. Gibt den Text für Jan zurück.

    Rückfrage: deren Text. Ungültig: AuftragFehler oder mail.MailFehler.
    vorgaenger: der geänderte Entwurf; sein Gesprächsbezug bleibt, wenn der neue keinen nennt.
    """
    neuer_entwurf = neuer_entwurf or freigabe.neuer_entwurf
    art, roh, original = auftrag.antwort_lesen(antwort, kontext)
    if art == "rueckfrage":
        return f"{roh}\n\nAntworte auf diese Nachricht, dann mache ich weiter."
    daten = mail.pruefen(roh, original)
    for feld in ("in_reply_to", "references", "antwort_auf"):
        if vorgaenger and vorgaenger["daten"].get(feld) and not daten.get(feld):
            daten[feld] = vorgaenger["daten"][feld]
    eid = neuer_entwurf(AGENT, titel=f"Mail: {daten['betreff']}", inhalt=mail.anzeige(daten), typ="mail",
                        daten=daten, vorgaenger=vorgaenger and vorgaenger["id"])
    entwuerfe = entwuerfe or ENTWUERFE
    _schreibe_json(entwuerfe, {**_lies_json(entwuerfe, {}), eid: auftrag_id})
    logger.info("Mail-Entwurf %s zur Freigabe: %s", eid, daten["betreff"])
    return f"Entwurf an {', '.join(daten['an'])} liegt zur Freigabe."


def _fertig(a: dict, text: str, ok: bool, sitzung: str | None = None) -> None:
    auftraege.abschliessen(a["id"], text, status="erledigt" if ok else "fehlgeschlagen", sitzung=sitzung)


def mail_auftrag(a: dict, laufen=claude_lauf.laufen, suchen=postfach_suchen, termine=kalender.termine,
                 heute: date | None = None, ablage: Path | None = None, einreichen=entwurf_einreichen,
                 fertig=_fertig) -> bool:
    """Ein Auftrag von Jan. False: Claude ist gerade nicht verfügbar, der Auftrag bleibt in neu/."""
    heute = heute or date.today()
    ablage = ablage or AUFTRAEGE
    text = auftragstext(a, ablage)
    try:
        e = laufen(AGENT, HIER, auftrag.prompt_suche(text, heute), art="routine", auftrag_id=a["id"])
        if not e.ok:
            raise claude_lauf.LaufFehler(e.text[:300])
        suche = auftrag.suche_lesen(e.text)
        kontext = auftrag.kontext_sammeln(suche, suchen, termine, heute,
                                          gesendet=_cfg().get("GESENDET_ORDNER", auftrag.ORDNER_GESENDET))
        _schreibe_json(ablage / a["id"] / "kontext.json", {"text": text, "kontext": kontext})
        logger.info("Auftrag %s: %d Mails, %d Stilvorlagen, %d Termine gefunden", a["id"], len(kontext["mails"]),
                    len(kontext["stil"]), len(kontext["termine"]))
        e = laufen(AGENT, HIER, auftrag.prompt_entwurf(text, kontext, heute), art="anspruchsvoll",
                   auftrag_id=a["id"])
        if not e.ok:
            raise claude_lauf.LaufFehler(e.text[:300])
        fertig(a, einreichen(e.text, kontext, a["id"]), True, e.sitzung)
    except WARTEN as f:
        logger.info("Auftrag %s wartet: %s", a["id"], f)
        return False
    except (claude_lauf.LaufFehler, auftrag.AuftragFehler, mail.MailFehler) as f:
        logger.warning("Auftrag %s fehlgeschlagen: %s", a["id"], f)
        fertig(a, f"Kein Entwurf möglich: {f}", False)
    return True


def aenderung(a: dict, laufen=claude_lauf.laufen, heute: date | None = None, ablage: Path | None = None,
              entwuerfe: Path | None = None, holen=None, einreichen=entwurf_einreichen, fertig=_fertig) -> bool:
    """Jan hat bei einem Entwurf "Ändern" getippt: a["text"] ist sein Kommentar, a["bezug"] der alte Entwurf."""
    holen = holen or (lambda eid: next((e for e in freigabe.erledigte(AGENT) if e["id"] == eid), None))
    ablage = ablage or AUFTRAEGE
    alt = holen(a.get("bezug"))
    ursprung = _lies_json(entwuerfe or ENTWUERFE, {}).get(str(a.get("bezug")))
    gespeichert = ablage / str(ursprung) / "kontext.json"
    if not alt or alt.get("typ") != "mail" or not ursprung or not gespeichert.exists():
        fertig(a, "Diesen Entwurf kann ich nicht mehr ändern (Kontext fehlt). Schick den Auftrag bitte neu.", False)
        return True
    g = _lies_json(gespeichert, {})
    try:
        e = laufen(AGENT, HIER, auftrag.prompt_aendern(a["text"], alt["daten"], g["text"], g["kontext"],
                                                       heute or date.today()),
                   art="anspruchsvoll", auftrag_id=a["id"])
        if not e.ok:
            raise claude_lauf.LaufFehler(e.text[:300])
        fertig(a, einreichen(e.text, g["kontext"], ursprung, vorgaenger=alt), True, e.sitzung)
    except WARTEN as f:
        logger.info("Änderung %s wartet: %s", a["id"], f)
        return False
    except (claude_lauf.LaufFehler, auftrag.AuftragFehler, mail.MailFehler) as f:
        logger.warning("Änderung %s fehlgeschlagen: %s", a["id"], f)
        fertig(a, f"Kein neuer Entwurf möglich: {f}", False)
    return True


def auftrag_bearbeiten(a: dict) -> bool:
    if fehlt := fehlende_bausteine():
        _fertig(a, "Mail-Aufträge kann ich noch nicht bearbeiten, es fehlt noch ein Baustein "
                   f"({', '.join(fehlt)}). Ich lese weiter nur das Postfach.", False)
        return True
    if a.get("quelle") == "telegram-aendern":
        return aenderung(a)
    return mail_auftrag(a)


def auftraege_abarbeiten(neue=lambda: auftraege.neue(AGENT, dienst=None), bearbeiten=auftrag_bearbeiten) -> None:
    """Arbeitet ab, bis keine neuen mehr da sind (ein Auftrag während des Laufs startet keinen zweiten)."""
    gesehen = set()
    while offen := [a for a in neue() if a["id"] not in gesehen]:
        for a in offen:
            gesehen.add(a["id"])
            if not bearbeiten(a):
                return


def ausfuehren(entwurf: dict) -> str:
    if entwurf["typ"] == "mail":
        return mail.senden(_cfg(), entwurf["daten"])  # genau die freigegebenen daten
    raise NotImplementedError(f"Entwurfstyp {entwurf['typ']} kann posteingang nicht ausführen")


def freigegebene_ausfuehren(ausfuehren=ausfuehren) -> None:
    if mail is None:
        return
    for e in freigabe.zur_ausfuehrung(AGENT):
        try:
            e = freigabe.ausfuehrung_beginnen(e["id"])
        except freigabe.FreigabeFehler as f:
            logger.warning("Nicht ausgeführt: %s", f)
            continue
        try:
            freigabe.ausfuehrung_abschliessen(e["id"], ausfuehren(e), erfolgreich=True)
        except Exception as f:  # noqa: BLE001 – jeder Fehler wird Jan gemeldet
            logger.exception("Ausführung %s fehlgeschlagen", e["id"])
            freigabe.ausfuehrung_abschliessen(e["id"], f"Fehler: {f}", erfolgreich=False)


def schritt_fehler_melden(schritt: str, f: Exception, heute: str | None = None, datei: Path | None = None,
                          melden=melden) -> bool:
    """Meldet einen fehlgeschlagenen Schritt, höchstens einmal am Tag je Schritt."""
    datei = datei or FEHLER_DATEI
    heute = heute or date.today().isoformat()
    stand = _lies_json(datei, {})
    if stand.get(schritt) == heute:
        return False
    melden(f"[post] Schritt {schritt} fehlgeschlagen: {type(f).__name__}: {f}\n"
           f"Weitere Fehler dieses Schritts heute nur im Log: posteingang/logs/posteingang.log")
    stand[schritt] = heute
    _schreibe_json(datei, stand)
    return True


if __name__ == "__main__":
    for schritt in (freigegebene_ausfuehren, auftraege_abarbeiten, post_pruefen):
        try:
            schritt()
        except Exception as f:  # noqa: BLE001 – ein Fehler soll die anderen Schritte nicht blockieren
            logger.exception("Schritt %s fehlgeschlagen", schritt.__name__)
            try:
                schritt_fehler_melden(schritt.__name__, f)
            except Exception:  # noqa: BLE001 – Melden darf den Lauf nicht abbrechen
                logger.exception("Fehler von %s nicht gemeldet", schritt.__name__)
