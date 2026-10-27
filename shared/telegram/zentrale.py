"""Telegram-Zentrale: einziger Kontakt zwischen Jan und den Agenten.

- /start oder /menue: Menü-Nachricht mit Knöpfen (Agenten, Entwürfe, Verbrauch, Status, Hilfe),
  die sich beim Tippen ändert (panel.py, Ansichten in logik.py). Agent antippen, dann ist die
  nächste Nachricht der Auftrag. Alle Befehle bleiben nutzbar.
- Reagiert nur auf Jans Chat-ID (TELEGRAM_CHAT_ID).
- Zeigt neue Entwürfe aus shared/freigabe/offen/ mit Knöpfen an.
- /uni ..., /unilern ... usw. werden zu Aufträgen in shared/auftraege/neu/.
- Meldet ausgeführte Entwürfe, unklare Fälle und erledigte Aufträge.
- Antwortet Jan auf die Meldung eines Auftrags, wird daraus ein neuer Auftrag in
  derselben Claude-Sitzung. /pc (als Antwort) gibt die Sitzung an den PC, /weiter holt sie zurück.
- Verschickt Meldungen der Agenten aus shared/meldungen/neu/ (Fristen, wichtige Mails ...).
  Hat eine Meldung Knöpfe, wird ein Klick (einmal je Meldung) oder Jans Antwort darauf ein
  Auftrag an den Agenten, danach startet <dienst>.service der Meldung (siehe agentkit.meldungen).
  Ergebnisdateien von Aufträgen und Meldungen (bis 50 MB) kommen als Dokument, der Text steht
  möglichst als Beschriftung darunter (eine Nachricht statt zwei). Gibt es eine gleichnamige PDF,
  kommt nur sie (docx bleibt auf dem Server).
- Nachrichten an Jan bleiben kurz: Absender fett, Ergebnis, nichts Technisches (IDs, Pfade,
  Stufen). Stufenwechsel nur bei Limit und danach, Weitergaben nur, wenn der Auftrag liegen bleibt.
  Sprachregel docs/sprache/sprachregel.md: jede ausgehende Nachricht wird geprüft (sprachpruefung.py), Befunde
  ohne Inhalt als Warnung ins Log.
- Feedback (CLAUDE.md, "Lernen aus Feedback"): Unter jedem Ergebnis eines Agenten Knöpfe (vorlagen.py: Passt, Zu
  lang, Falscher Fokus, Feedback schreiben). Feedback wird ein Auftrag an "feedback" (bezug = Ergebnis), danach
  startet feedback.service (shared/feedback). Dessen Zusammenfassung kommt als Meldung mit Stopp-Knopf (auch für
  Lias Feedback); der Klick geht wie jeder Meldungsknopf an feedback.service. Eine Antwort auf das Ergebnis setzt
  weiter die Sitzung fort.
  Ergebnisse, die nur auf einen Entwurf in der Freigabe verweisen, kommen nicht (logik.nur_freigabe_verweis):
  Feedback dazu läuft über Ändern/Ablehnen am Entwurf.
- Nimmt Dateien und Fotos an (bis 20 MB). Mit /agent in der Bildunterschrift oder als Antwort auf
  eine Meldung gehen sie sofort an den Auftrag, sonst warten sie in data/eingang/ auf den nächsten
  Auftrag. agentkit.auftraege legt sie dann in <agent>/data/eingang/<auftrag-id>/ ab.

Start: .venv/bin/python zentrale.py
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from agentkit import auftraege, config, einstellungen, freigabe, log, meldungen, sprache, verbrauch
from agentkit._ablage import AblageFehler, anhaenge_pruefen, pruefe_dienst
from logik import (
    AGENTEN,
    AN_WEN,
    DATEI_NICHT_GELADEN,
    DATEI_ZU_GROSS,
    KNOPF_ALT,
    MAX_DATEI_BYTES,
    NICHT_ANGELEGT,
    TEXT_WEG,
    ZURUECK,
    Eingang,
    Gemeldet,
    ansicht_agent,
    ansicht_entwuerfe,
    ansicht_home,
    ansicht_text,
    anzeigename,
    auftrag_nachricht,
    aufteilen,
    befehl_auswerten,
    bestaetigung,
    aenderung_weiter,
    dateien_auswaehlen,
    dateien_verworfen,
    dateien_warten,
    datei_nicht_gesendet,
    entwurf_als_text,
    freigabe_antwort,
    freigabe_fehler,
    hilfe_text,
    home_zeilen,
    knopf_auswerten,
    knopf_beschriftung,
    meldung_knoepfe,
    mit_absender,
    nur_freigabe_verweis,
    panel_auswerten,
    passt_als_beschriftung,
    status_text,
    stufe_text,
    unklar_text,
    verbrauch_text,
    weitergabe_text,
)
import panel
import sprachpruefung
import vorlagen as v

HIER = Path(__file__).resolve().parent
FEEDBACK = "feedback"  # Feedback-Dienst (shared/feedback), kein Agent mit Befehl
UNIT_DIR = Path.home() / ".config" / "systemd" / "user"
AGENTEN_DIR = auftraege.AGENTEN_DIR
PRUEF_INTERVALL = 30  # Sekunden
ALBUM_WARTEN = 3  # Sekunden nach der letzten Datei eines Albums, dann wird zugeordnet

cfg = config.lade_config(HIER, pflicht=("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"))
JAN = int(cfg["TELEGRAM_CHAT_ID"])
logger = log.hole_logger(HIER, "zentrale")
# httpx loggt Anfrage-Adressen, und die enthalten den Bot-Token: nur Warnungen zulassen.
logging.getLogger("httpx").setLevel(logging.WARNING)
gemeldet = Gemeldet(HIER / "data" / "gemeldet.json")
eingang = Eingang(HIER / "data" / "eingang")

HILFE = hilfe_text(AGENTEN)


async def senden(context: ContextTypes.DEFAULT_TYPE, text: str | list[str], knoepfe=None) -> list:
    """Klartext (wird aufgeteilt) oder fertige HTML-Stücke aus mit_absender (Liste)."""
    stuecke, modus = (text, ParseMode.HTML) if isinstance(text, list) else (aufteilen(text), None)
    gesendet = []
    for i, stueck in enumerate(stuecke):
        letzte = i == len(stuecke) - 1
        gesendet.append(await context.bot.send_message(JAN, stueck, parse_mode=modus,
                                                       reply_markup=knoepfe if letzte else None))
    return gesendet


async def dateien_senden(context: ContextTypes.DEFAULT_TYPE, agent: str, dateien: list[str],
                         beschriftung: str | None = None, knoepfe=None) -> list:
    """Schickt Ergebnisdateien eines Agenten, beschriftung (HTML) unter der letzten.

    Ein Fehler betrifft nur die eine Datei, Jan erfährt davon. Scheitert die beschriftete Datei,
    kommt die Beschriftung als eigene Nachricht, damit der Text nicht verloren geht.
    """
    gesendet = []
    for i, datei in enumerate(dateien):
        text = beschriftung if i == len(dateien) - 1 else None
        try:
            # noch einmal prüfen: zwischen Ablage und Senden kann sich die Datei geändert haben
            pfad = AGENTEN_DIR / agent / anhaenge_pruefen(AGENTEN_DIR / agent, [datei])[0]
            with open(pfad, "rb") as f:
                gesendet.append(await context.bot.send_document(
                    JAN, f, filename=pfad.name, write_timeout=120, caption=text, parse_mode=ParseMode.HTML,
                    reply_markup=knoepfe if i == len(dateien) - 1 else None))
        except (AblageFehler, OSError, TelegramError) as f:
            logger.error("Datei %s von %s nicht gesendet: %s", datei, agent, f)
            if text:
                gesendet += await senden(context, [text], knoepfe)
            await senden(context, mit_absender(agent, datei_nicht_gesendet(datei)))
    return gesendet


async def mit_dateien(context: ContextTypes.DEFAULT_TYPE, agent: str, stuecke: list[str], dateien: list[str],
                      knoepfe=None) -> list:
    """Text (HTML-Stücke aus mit_absender) und Dateien so knapp wie möglich: kurzer Text steht mit den
    Knöpfen unter der Datei, sonst kommt er vorher als eigene Nachricht."""
    dateien = dateien_auswaehlen(dateien)
    if dateien and passt_als_beschriftung(stuecke):
        return await dateien_senden(context, agent, dateien, stuecke[0], knoepfe)
    return await senden(context, stuecke, knoepfe) + await dateien_senden(context, agent, dateien)


async def agent_starten(agent: str, dienst: str | None = None) -> None:
    """Startet <dienst>.service (ohne dienst: <agent>.service), falls es ihn gibt.

    --no-block: nicht auf das Ende warten.
    """
    dienst = dienst or agent
    try:
        pruefe_dienst(agent, dienst)
    except AblageFehler as f:
        logger.error("Dienst nicht gestartet: %s", f)
        return
    if agent not in (*AGENTEN, FEEDBACK) or not (UNIT_DIR / f"{dienst}.service").exists():
        logger.info("Kein Dienst %s.service, Auftrag wartet auf den nächsten Lauf", dienst)
        return
    proc = await asyncio.create_subprocess_exec(
        "systemctl", "--user", "start", "--no-block", f"{dienst}.service",
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        logger.error("Start von %s.service fehlgeschlagen: %s", dienst, err.decode().strip())
    else:
        logger.info("%s.service gestartet", dienst)


def agenten_mit_dienst() -> list[str]:
    """Nur Agenten, die einen Dienst haben, bekommen Knöpfe (sonst bliebe der Auftrag still liegen)."""
    return [a for a in AGENTEN if (UNIT_DIR / f"{a}.service").exists()] or list(AGENTEN)


# ---------- Menü-Nachricht (Panel) ----------

def status_zeilen() -> str:
    return status_text({"offen": len(freigabe.offene()), "ausfuehrung": len(freigabe.zur_ausfuehrung()),
                        "unklar": len(freigabe.unklare()), "auftraege": len(auftraege.neue()),
                        "am_pc": len(gemeldet.listen["am_pc"]), "dateien": len(eingang.wartende())})


def home(hinweis: str = "") -> tuple[str, list]:
    stand, stufe = aktuelle_stufe()
    entwuerfe = len(freigabe.offene())
    zeilen = home_zeilen(stand, stufe, entwuerfe, len(auftraege.neue()), len(eingang.wartende()))
    return ansicht_home(zeilen, agenten_mit_dienst(), entwuerfe, hinweis)


async def panel_zeigen(bot, chat_data: dict, ansicht: tuple[str, list], neu: bool = False) -> None:
    await panel.zeigen(bot, JAN, chat_data, *ansicht, neu=neu)


async def panel_knopf(q, context: ContextTypes.DEFAULT_TYPE) -> None:
    await q.answer()
    z = context.chat_data
    z["panel"] = q.message.message_id  # die angetippte Nachricht ist das Panel
    ausgewertet = panel_auswerten(q.data)
    neu = False
    if ausgewertet is None:
        z.pop("panel_agent", None)
        await panel_zeigen(context.bot, z, home(KNOPF_ALT))
        return
    aktion, agent, modus = ausgewertet
    z.pop("panel_agent", None)
    if aktion == "agent":
        z["panel_agent"] = (agent, modus)  # die nächste Nachricht ist der Auftrag
        ansicht = ansicht_agent(agent, modus)
    elif aktion == "entwuerfe":
        ansicht = ansicht_entwuerfe(freigabe.offene())
    elif aktion == "zeigen":
        for e in freigabe.offene():
            await entwurf_zeigen(context.bot, e)
        gemeldet.speichern()
        ansicht, neu = home("Die offenen Entwürfe stehen oben."), True
    elif aktion == "verbrauch":
        stand, stufe = aktuelle_stufe()
        ansicht = ansicht_text("Verbrauch", verbrauch_text(stand, stufe, verbrauch.heute(), verbrauch.zeit_text))
    elif aktion == "status":
        ansicht = ansicht_text("Status", status_zeilen())
    elif aktion == "hilfe":
        ansicht = (HILFE, ZURUECK)
    else:  # home, neu
        ansicht = home()
    await panel_zeigen(context.bot, z, ansicht, neu=neu)


# ---------- Eingang: Nachrichten von Jan ----------

async def fremd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    u = update.effective_user
    logger.warning("Nachricht von fremder ID ignoriert: chat=%s user=%s",
                   update.effective_chat.id if update.effective_chat else "?", u.username if u else "?")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start, /menue: Menü-Nachricht unten im Chat."""
    context.chat_data.pop("panel_agent", None)
    await panel_zeigen(context.bot, context.chat_data, home(), neu=True)


async def hilfe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HILFE)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(status_zeilen())


def aktuelle_stufe() -> tuple[dict | None, str]:
    stand = verbrauch.letzter_stand()
    return stand, verbrauch.stufe(stand, einstellungen.lade())


async def verbrauch_befehl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    stand, stufe = aktuelle_stufe()
    await update.message.reply_text(verbrauch_text(stand, stufe, verbrauch.heute(), verbrauch.zeit_text))


async def auftrag_befehl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ergebnis = befehl_auswerten(update.message.text)
    if ergebnis is None:
        await update.message.reply_text("Diesen Befehl kenne ich nicht.\n\n" + HILFE)
        return
    agent, modus, text = ergebnis
    if not text:
        await update.message.reply_text(f"Schreib den Auftrag bitte dazu, zum Beispiel /{agent} Fristen prüfen")
        return
    await auftrag_anlegen(context.bot, agent, modus, text)


async def auftrag_anlegen(bot, agent: str, modus: str, text: str, bezug: str | None = None,
                          sitzung: str | None = None, quelle: str = "telegram", meldung: str | None = None,
                          dienst: str | None = None, bestaetigen: bool = True) -> bool:
    """Legt den Auftrag an, hängt alle wartenden Dateien an und startet den Agenten (bzw. dienst)."""
    dateien = eingang.wartende()
    try:
        aid = auftraege.neuer_auftrag(agent, text, quelle=quelle, modus=modus, bezug=bezug, sitzung=sitzung,
                                      dateien=dateien, meldung=meldung, dienst=dienst)
    except auftraege.AuftragFehler as e:
        logger.error("Auftrag an %s nicht angelegt: %s", agent, e)
        await bot.send_message(JAN, NICHT_ANGELEGT)
        return False
    eingang.aufraeumen()
    logger.info("Auftrag %s angelegt (%s, %s, Quelle %s, Sitzung %s, Meldung %s, Dienst %s, %d Dateien)",
                aid, agent, modus, quelle, sitzung, meldung, dienst, len(dateien))
    if bestaetigen or dateien:
        await bot.send_message(JAN, bestaetigung(agent, modus, [d.name for d in dateien]))
    await agent_starten(agent, dienst)
    return True


def beantworteter_auftrag(update: Update) -> dict | None:
    """Der abgeschlossene Auftrag, auf dessen Meldung Jan geantwortet hat, sonst None."""
    bezug = update.message.reply_to_message
    aid = bezug and gemeldet.nachrichten.get(str(bezug.message_id))
    if not aid:
        return None
    try:
        return auftraege.erledigter(aid)
    except auftraege.AuftragFehler:
        return None


def beantwortete_meldung(update: Update) -> dict | None:
    """Die Meldung mit Rückfrage (Knöpfe oder Dienst), auf die Jan geantwortet hat, sonst None."""
    bezug = update.message.reply_to_message
    mid = bezug and gemeldet.meldung_zu(bezug.message_id)
    if not mid:
        return None
    try:
        m = meldungen.gesendete(mid)
    except meldungen.MeldungFehler:
        return None
    return m if meldungen.nimmt_antwort(m) else None


async def meldung_beantworten(bot, m: dict, text: str, quelle: str, bestaetigen: bool = True) -> bool:
    return await auftrag_anlegen(bot, m["agent"], "erledigen", text, quelle=quelle, meldung=m["id"],
                                 dienst=m.get("dienst"), bestaetigen=bestaetigen)


async def antwort_weitergeben(bot, alt: dict, text: str) -> None:
    if not alt.get("sitzung"):
        await bot.send_message(JAN, "Hier kann ich nicht im selben Gespräch weitermachen. "
                                    "Schick es bitte als neuen Auftrag.")
        return
    if alt["sitzung"] in gemeldet.listen["am_pc"]:
        await bot.send_message(JAN, "Dieses Gespräch liegt gerade am PC. Beende es dort und schick hier /weiter.")
        return
    await auftrag_anlegen(bot, alt["agent"], alt["modus"], text, bezug=alt["id"], sitzung=alt["sitzung"])


async def pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    alt = beantworteter_auftrag(update)
    if alt is None or not alt.get("sitzung"):
        await update.message.reply_text("Schick /pc bitte als Antwort auf ein Ergebnis.")
        return
    sitzung = alt["sitzung"]
    if any(a.get("sitzung") == sitzung for a in auftraege.neue()):
        await update.message.reply_text(f"{anzeigename(alt['agent'])} arbeitet gerade in diesem Gespräch. "
                                        "Warte bitte erst die Antwort ab.")
        return
    gemeldet.listen["am_pc"].add(sitzung)
    gemeldet.speichern()
    logger.info("Sitzung %s liegt am PC", sitzung)
    with sprachpruefung.ausnahmen("pfad", "bezeichner", "id", "glossar"):  # Befehl zum Kopieren
        await update.message.reply_text(
            f"Das Gespräch liegt jetzt am PC. Dort eingeben:\n\ncd ~/agenten/{alt['agent']} && claude --resume {sitzung}"
            "\n\nDanach den PC-Chat beenden und hier /weiter schicken.")


async def weiter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not gemeldet.listen["am_pc"]:
        await update.message.reply_text("Am PC liegt gerade kein Gespräch.")
        return
    logger.info("Sitzungen zurück vom PC: %s", sorted(gemeldet.listen["am_pc"]))
    gemeldet.listen["am_pc"].clear()
    gemeldet.speichern()
    await update.message.reply_text("Zurück in Telegram. Antworte auf das letzte Ergebnis, "
                                    "dann geht es im selben Gespräch weiter.")


async def text_ohne_befehl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    alt = beantworteter_auftrag(update)
    if alt is not None:
        await antwort_weitergeben(context.bot, alt, text)
        return
    m = beantwortete_meldung(update)
    if m is not None:
        await meldung_beantworten(context.bot, m, text, "antwort")
        return
    # Wartet ein Feedback ("Falscher Fokus", "Feedback schreiben") auf Jans Text?
    fb = context.chat_data.pop("feedback", None)
    if fb:
        await update.message.reply_text(await feedback_anlegen(fb["bezug"], fb["k"], text))
        await knoepfe_weg(context.bot, fb.get("nachricht"))
        return
    # Wartet ein "Ändern" auf Jans Kommentar?
    aendern_id = context.chat_data.pop("aendern", None)
    if aendern_id:
        await aenderung_eintragen(update, aendern_id, text)
        return
    # Im Menü einen Agenten gewählt? Dann ist dieser Text der Auftrag.
    ziel = context.chat_data.pop("panel_agent", None)
    if ziel:
        agent, modus = ziel
        if await auftrag_anlegen(context.bot, agent, modus, text, bestaetigen=False):
            await panel_zeigen(context.bot, context.chat_data,
                               home(bestaetigung(agent, modus, [])), neu=True)
        return
    await agent_fragen(context.bot, context.chat_data, text)


async def agent_fragen(bot, chat_data: dict, text: str) -> None:
    chat_data["wartender_text"] = text
    knoepfe = InlineKeyboardMarkup(
        [[InlineKeyboardButton(anzeigename(a), callback_data=f"z:{a}")] for a in agenten_mit_dienst()]
        + [[InlineKeyboardButton("Verwerfen", callback_data="z:-")]]
    )
    await bot.send_message(JAN, AN_WEN, reply_markup=knoepfe)


async def aenderung_eintragen(update: Update, eid: str, kommentar: str) -> None:
    try:
        entwurf = freigabe.entscheide(eid, "aendern", kommentar)
    except freigabe.FreigabeFehler as e:
        logger.warning("Änderung für %s: %s", eid, e)
        await update.message.reply_text(freigabe_fehler(str(e)))
        return
    dateien = eingang.wartende()
    auftraege.neuer_auftrag(entwurf["agent"], kommentar, quelle="telegram-aendern", bezug=eid, dateien=dateien)
    eingang.aufraeumen()
    logger.info("Entwurf %s: Änderung gewünscht (%d Dateien)", eid, len(dateien))
    await update.message.reply_text(aenderung_weiter(entwurf["agent"], len(dateien)))
    await agent_starten(entwurf["agent"])


# ---------- Feedback ----------

async def feedback_anlegen(bezug: str, k: str, eingabe: str = "") -> str:
    """Feedback als Auftrag an feedback.service (ohne wartende Dateien). Gibt die Antwort an Jan zurück."""
    try:
        fid = auftraege.neuer_auftrag(FEEDBACK, v.feedback_text(k, eingabe), quelle="feedback", bezug=bezug)
    except auftraege.AuftragFehler as e:
        logger.error("Feedback zu %s nicht angelegt: %s", bezug, e)
        return "Das Feedback konnte ich nicht anlegen. Schick es bitte noch einmal."
    logger.info("Feedback %s zu %s angelegt (%s)", fid, bezug, k)
    await agent_starten(FEEDBACK)
    return v.DANKE


async def knoepfe_weg(bot, nachricht_id: int | None) -> None:
    if nachricht_id:
        try:
            await bot.edit_message_reply_markup(JAN, nachricht_id, reply_markup=None)
        except TelegramError as e:
            logger.info("Knöpfe nicht entfernt: %s", e)


def ergebnis_knoepfe(a: dict) -> InlineKeyboardMarkup | None:
    """Feedback-Knöpfe unter erledigten Aufträgen der Agenten (nicht unter Fehlern, nicht beim Feedback-Dienst,
    nicht wenn der Agent sie abgewählt hat)."""
    if a["status"] != "erledigt" or a["agent"] == FEEDBACK or v.ohne_feedback_knoepfe(a):
        return None
    return panel.markup(v.feedback_knoepfe("", a["id"]))


async def feedback_knopf(q, context: ContextTypes.DEFAULT_TYPE, aid: str, k: str) -> None:
    await q.answer()
    try:
        a = auftraege.erledigter(aid)
    except auftraege.AuftragFehler:
        await q.edit_message_reply_markup(None)
        return
    logger.info("Feedback-Knopf %s zu %s", k, aid)
    if k == "lang":
        await q.edit_message_reply_markup(panel.markup(v.laenge_knoepfe("", aid)))
    elif k == "zu":
        await q.edit_message_reply_markup(ergebnis_knoepfe(a))
    elif k in ("fokus", "frei"):
        context.chat_data["feedback"] = {"bezug": aid, "k": k, "nachricht": q.message.message_id}
        await q.message.reply_text(v.FB_FRAGE[k])
    else:  # ok, lh, li
        if aid in gemeldet.listen["geklickt"]:
            return  # Doppelklick
        gemeldet.geklickt(aid)
        gemeldet.speichern()
        await q.edit_message_reply_markup(None)
        await q.message.reply_text(v.vermerk(k) if k == "ok" else await feedback_anlegen(aid, k))


# ---------- Dateien ----------

async def datei_empfangen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    m = update.message
    if m.document:
        datei, name = m.document, m.document.file_name
    else:  # Foto: größte Fassung nehmen
        datei, name = m.photo[-1], f"foto-{datetime.now():%Y%m%d-%H%M%S}.jpg"
    if datei.file_size and datei.file_size > MAX_DATEI_BYTES:
        await m.reply_text(DATEI_ZU_GROSS)
        return
    pfad = eingang.neuer_platz(name or "datei")
    try:
        await (await datei.get_file()).download_to_drive(pfad)
    except Exception as e:  # Netz oder Telegram: Jan soll es wissen und neu schicken können
        logger.error("Download von %s fehlgeschlagen: %s", name, e)
        pfad.unlink(missing_ok=True)
        eingang.aufraeumen()
        await m.reply_text(DATEI_NICHT_GELADEN)
        return
    logger.info("Datei empfangen: %s (%d Bytes)", pfad.name, pfad.stat().st_size)
    if m.media_group_id is None:
        await dateien_zuordnen(context.bot, context.chat_data, m.caption, beantworteter_auftrag(update))
        return
    # Album: Telegram schickt jede Datei als eigene Nachricht, die Bildunterschrift nur bei einer.
    # Erst ALBUM_WARTEN Sekunden nach der letzten Datei zuordnen, damit alle am Auftrag hängen.
    alben = context.chat_data.setdefault("alben", {})
    album = alben.setdefault(m.media_group_id, {"caption": None, "alt": None, "job": None})
    album["caption"] = album["caption"] or m.caption
    album["alt"] = album["alt"] or beantworteter_auftrag(update)
    if album["job"]:
        album["job"].schedule_removal()
    album["job"] = context.job_queue.run_once(album_fertig, ALBUM_WARTEN, data=m.media_group_id, chat_id=JAN)


async def album_fertig(context: ContextTypes.DEFAULT_TYPE) -> None:
    album = context.chat_data.get("alben", {}).pop(context.job.data, None)
    if album:
        await dateien_zuordnen(context.bot, context.chat_data, album["caption"], album["alt"])


async def dateien_zuordnen(bot, chat_data: dict, caption: str | None, alt: dict | None) -> None:
    """Wartende Dateien weitergeben: Antwort auf eine Meldung, /agent ... als Bildunterschrift,
    Text ohne Befehl (Agent per Knopf wählen), sonst bis zum nächsten Auftrag warten."""
    text = (caption or "").strip()
    if alt is not None:
        await antwort_weitergeben(bot, alt, text or "Siehe angehängte Dateien.")
        return
    if text and not text.startswith("/"):
        await agent_fragen(bot, chat_data, text)
        return
    ergebnis = befehl_auswerten(text) if text else None
    if ergebnis and ergebnis[2]:
        await auftrag_anlegen(bot, *ergebnis)
        return
    beispiel = f"/{ergebnis[0]} und dein Text" if ergebnis else "/uni Fasse das zusammen"
    await bot.send_message(JAN, dateien_warten(len(eingang.wartende()), beispiel, bool(text and not ergebnis)))


async def verwerfen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    anzahl = eingang.verwerfen()
    logger.info("%d wartende Dateien verworfen", anzahl)
    await update.message.reply_text(dateien_verworfen(anzahl))


# ---------- Knöpfe ----------

async def knopf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if update.effective_chat is None or update.effective_chat.id != JAN:
        await fremd(update, context)
        await q.answer()
        return
    art, _, wert = q.data.partition(":")

    if art == "u":  # Menü-Nachricht
        await panel_knopf(q, context)
        return

    if (fb := v.feedback_auswerten(q.data, "")) is not None:  # Knopf unter einem Ergebnis
        await feedback_knopf(q, context, *fb)
        return

    if art == "m":  # Knopf unter einer Meldung
        await meldung_knopf(q, context)
        return

    if art == "z":  # Agent für Text ohne Befehl gewählt
        text = context.chat_data.pop("wartender_text", None)
        await q.answer()
        if wert == "-" or text is None:
            await q.edit_message_text("Verworfen." if text else TEXT_WEG)
            return
        await q.edit_message_reply_markup(None)
        await auftrag_anlegen(context.bot, wert, "erledigen", text)
        return

    eid = wert
    try:
        if art == "f":
            gesehen = gemeldet.angezeigt.get(eid)
            entwurf = freigabe.entscheide(eid, "freigegeben", gesehen=gesehen)
            antwort = freigabe_antwort("freigegeben", entwurf["agent"])
        elif art == "a":
            entwurf = freigabe.entscheide(eid, "abgelehnt")
            antwort = freigabe_antwort("abgelehnt", entwurf["agent"])
        elif art == "c":
            context.chat_data["aendern"] = eid
            await q.answer()
            await q.message.reply_text(freigabe_antwort("aendern", ""))
            return
        else:
            await q.answer("Dieser Knopf ist veraltet.")
            return
    except freigabe.FreigabeFehler as e:
        logger.warning("Knopf %s für %s: %s", art, eid, e)
        await q.answer()
        await q.edit_message_reply_markup(None)
        await q.message.reply_text(freigabe_fehler(str(e)))
        return
    logger.info("Entwurf %s: %s", eid, antwort)
    await q.answer()
    await q.edit_message_reply_markup(None)
    await q.message.reply_text(antwort)
    if art == "f":
        await agent_starten(entwurf["agent"])


async def meldung_knopf(q, context: ContextTypes.DEFAULT_TYPE) -> None:
    ausgewertet = knopf_auswerten(q.data)
    m, beschriftung = None, None
    if ausgewertet:
        mid, zeile, spalte = ausgewertet
        try:
            m = meldungen.gesendete(mid)
            beschriftung = knopf_beschriftung(m, zeile, spalte)
        except meldungen.MeldungFehler as f:
            logger.warning("Knopf %s: %s", q.data, f)
    if m is None or beschriftung is None:
        await q.answer("Dieser Knopf ist veraltet.")
        return
    if m["id"] in gemeldet.listen["geklickt"]:
        await q.answer("Schon erledigt.")
        await q.edit_message_reply_markup(None)
        return
    gemeldet.geklickt(m["id"])  # vor dem Anlegen merken: ein schneller Doppelklick zählt nur einmal
    gemeldet.speichern()
    await q.answer()
    await q.edit_message_reply_markup(None)
    if await meldung_beantworten(context.bot, m, beschriftung, "knopf", bestaetigen=False):
        await q.message.reply_text(f"Gewählt: {beschriftung}")
    else:  # Klick ist nicht angekommen: wieder freigeben, Jan kann es noch einmal versuchen
        gemeldet.listen["geklickt"].discard(m["id"])
        gemeldet.speichern()
        await q.edit_message_reply_markup(knopf_leiste(m))


def knopf_leiste(m: dict) -> InlineKeyboardMarkup | None:
    knoepfe = meldung_knoepfe(m)
    if not knoepfe:
        return None
    return InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=d) for t, d in zeile] for zeile in knoepfe])


# ---------- Ausgang: regelmäßige Prüfung ----------

async def entwurf_zeigen(bot, e: dict) -> None:
    """Entwurf mit Knöpfen senden und merken, welcher Stand gezeigt wurde (Fingerabdruck)."""
    knoepfe = InlineKeyboardMarkup([[
        InlineKeyboardButton("Freigeben", callback_data=f"f:{e['id']}"),
        InlineKeyboardButton("Ändern", callback_data=f"c:{e['id']}"),
        InlineKeyboardButton("Ablehnen", callback_data=f"a:{e['id']}"),
    ]])
    with sprachpruefung.ausnahmen("laenge"):  # freigegeben wird genau der angezeigte Text
        for i, stueck in enumerate(stuecke := entwurf_als_text(e)):
            await bot.send_message(JAN, stueck, parse_mode=ParseMode.HTML,
                                   link_preview_options=LinkPreviewOptions(is_disabled=True),
                                   reply_markup=knoepfe if i == len(stuecke) - 1 else None)
    gemeldet.angezeigt[e["id"]] = e["fingerabdruck"]


async def pruefen(context: ContextTypes.DEFAULT_TYPE) -> None:
    geaendert = False

    for e in freigabe.offene():
        if e["id"] in gemeldet.angezeigt:
            continue
        await entwurf_zeigen(context.bot, e)
        geaendert = True

    for e in freigabe.erledigte():
        if e.get("ausgefuehrt") and e["id"] not in gemeldet.listen["ausgefuehrt"]:
            wort = "Ausgeführt" if e.get("erfolgreich") else "Hat nicht geklappt"
            await senden(context, mit_absender(e["agent"], f"{wort}: {e['titel']}\n{e.get('ausfuehrung', '')}"))
            gemeldet.listen["ausgefuehrt"].add(e["id"])
            geaendert = True

    for e in freigabe.unklare():
        if e["id"] not in gemeldet.listen["unklar"]:
            logger.warning("Unklare Ausführung %s (%s)", e["id"], e["agent"])
            await senden(context, mit_absender(e["agent"], unklar_text(e["titel"])))
            gemeldet.listen["unklar"].add(e["id"])
            geaendert = True

    for a in auftraege.neue():  # Aufträge von Agent an Agent: Jan Bescheid geben, Empfänger starten
        if a.get("von") and a["id"] not in gemeldet.listen["weitergaben"]:
            dienst_da = a["agent"] in AGENTEN and (UNIT_DIR / f"{a['agent']}.service").exists()
            logger.info("Weitergabe %s: %s -> %s (Dienst da: %s)", a["id"], a["von"], a["agent"], dienst_da)
            if text := weitergabe_text(a, dienst_da):
                await senden(context, text)
            await agent_starten(a["agent"])
            gemeldet.listen["weitergaben"].add(a["id"])
            geaendert = True

    for a in auftraege.erledigte():
        if a["id"] not in gemeldet.listen["auftraege"]:
            # Feedback: die Zusammenfassung kommt als Meldung; Zurückgezogenes: Jan hat selbst gestoppt
            if (a["agent"] == FEEDBACK and a.get("quelle") == "feedback" and a["status"] == "erledigt") \
                    or a["status"] == "zurueckgezogen":
                gemeldet.listen["auftraege"].add(a["id"])
                geaendert = True
                continue
            if nur_freigabe_verweis(a):  # der Entwurf kommt selbst, mit Freigeben/Ändern/Ablehnen (Jan, 28.10.)
                logger.info("Ergebnis %s nicht gesendet, verweist nur auf die Freigabe", a["id"])
                gemeldet.listen["auftraege"].add(a["id"])
                geaendert = True
                continue
            nachrichten = await mit_dateien(context, a["agent"], auftrag_nachricht(a), a.get("ergebnis_dateien", []),
                                            ergebnis_knoepfe(a))
            for n in nachrichten:  # auch eine Antwort auf die Datei setzt die Sitzung fort
                gemeldet.nachricht_merken(n.message_id, a["id"])
            gemeldet.listen["auftraege"].add(a["id"])
            geaendert = True

    for m in meldungen.neue():
        nachrichten = await mit_dateien(context, m["agent"], mit_absender(m["agent"], m["text"]),
                                        m.get("dateien", []), knopf_leiste(m))
        meldungen.als_gesendet(m["id"])  # erst nach erfolgreichem Senden, sonst nächster Versuch
        if meldungen.nimmt_antwort(m):
            for n in nachrichten:
                gemeldet.meldung_merken(n.message_id, m["id"])
            geaendert = True

    stand, stufe = aktuelle_stufe()
    if stufe != gemeldet.stufe:
        if text := stufe_text(gemeldet.stufe, stufe, stand, verbrauch.zeit_text):
            await senden(context, text)
        logger.info("Stufe %s -> %s", gemeldet.stufe, stufe)
        gemeldet.stufe = stufe
        geaendert = True

    if geaendert:
        gemeldet.speichern()


async def fehler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Fehler: %s", context.error, exc_info=context.error)


def main() -> None:
    app = (Application.builder().token(cfg["TELEGRAM_BOT_TOKEN"])
           .rate_limiter(sprachpruefung.Sprachpruefung(sprache.JAN, logger)).build())
    jan = filters.Chat(chat_id=JAN)
    app.add_handler(MessageHandler(~jan, fremd))
    app.add_handler(CommandHandler(["start", "menue", "menu"], start, filters=jan))
    app.add_handler(CommandHandler("hilfe", hilfe, filters=jan))
    app.add_handler(CommandHandler("status", status, filters=jan))
    app.add_handler(CommandHandler("verbrauch", verbrauch_befehl, filters=jan))
    app.add_handler(CommandHandler("pc", pc, filters=jan))
    app.add_handler(CommandHandler("weiter", weiter, filters=jan))
    app.add_handler(CommandHandler("verwerfen", verwerfen, filters=jan))
    app.add_handler(MessageHandler(jan & (filters.Document.ALL | filters.PHOTO), datei_empfangen))
    app.add_handler(MessageHandler(jan & filters.COMMAND, auftrag_befehl))
    app.add_handler(MessageHandler(jan & filters.TEXT, text_ohne_befehl))
    app.add_handler(CallbackQueryHandler(knopf))
    app.add_error_handler(fehler)
    app.job_queue.run_repeating(pruefen, interval=PRUEF_INTERVALL, first=5)
    logger.info("Zentrale startet")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
