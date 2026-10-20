"""Telegram-Zentrale: einziger Kontakt zwischen Jan und den Agenten.

- Reagiert nur auf Jans Chat-ID (TELEGRAM_CHAT_ID).
- Zeigt neue Entwürfe aus shared/freigabe/offen/ mit Knöpfen an.
- /uni ..., /unilern ... usw. werden zu Aufträgen in shared/auftraege/neu/.
- Meldet ausgeführte Entwürfe, unklare Fälle und erledigte Aufträge.
- Antwortet Jan auf die Meldung eines Auftrags, wird daraus ein neuer Auftrag in
  derselben Claude-Sitzung. /pc (als Antwort) gibt die Sitzung an den PC, /weiter holt sie zurück.
- Verschickt Meldungen der Agenten aus shared/meldungen/neu/ (Fristen, wichtige Mails ...).
  Hat eine Meldung Knöpfe, wird ein Klick (einmal je Meldung) oder Jans Antwort darauf ein
  Auftrag an den Agenten, danach startet <dienst>.service der Meldung (siehe agentkit.meldungen).
  Ergebnisdateien von Aufträgen und Meldungen (bis 50 MB) kommen als Dokument hinterher.
- Nimmt Dateien und Fotos an (bis 20 MB). Mit /agent in der Bildunterschrift oder als Antwort auf
  eine Meldung gehen sie sofort an den Auftrag, sonst warten sie in data/eingang/ auf den nächsten
  Auftrag. agentkit.auftraege legt sie dann in <agent>/data/eingang/<auftrag-id>/ ab.

Start: .venv/bin/python zentrale.py
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from agentkit import auftraege, config, einstellungen, freigabe, log, meldungen, verbrauch
from agentkit._ablage import AblageFehler, anhaenge_pruefen, pruefe_dienst
from logik import (
    AGENTEN,
    MAX_DATEI_BYTES,
    STUFEN_TEXT,
    Eingang,
    Gemeldet,
    aufteilen,
    befehl_auswerten,
    entwurf_als_text,
    knopf_auswerten,
    knopf_beschriftung,
    meldung_knoepfe,
    verbrauch_text,
)

HIER = Path(__file__).resolve().parent
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

HILFE = (
    "Befehle:\n"
    + "\n".join(f"/{a} <Auftrag>  (erledigen)\n/{a}lern <Auftrag>  (gemeinsam lernen)" for a in AGENTEN)
    + "\nAuf eine Meldung antworten: Der Agent macht in derselben Sitzung weiter "
    "(bei Meldungen mit Knöpfen geht die Antwort statt eines Klicks an den Agenten).\n"
    "/pc  (als Antwort auf eine Meldung) Sitzung am PC fortsetzen\n/weiter  Sitzung vom PC zurückholen"
    + "\n/status  Überblick\n/verbrauch  Auslastung des Claude-Kontingents\n"
    "Text ohne Befehl: Ich frage, an welchen Agenten er geht.\n"
    "Dateien und Fotos (bis 20 MB): mit /uni ... als Bildunterschrift gehen sie sofort an den Auftrag. "
    "Ohne Befehl warten sie und hängen am nächsten Auftrag.\n/verwerfen  wartende Dateien löschen"
)


async def senden(context: ContextTypes.DEFAULT_TYPE, text: str, knoepfe=None) -> list:
    stuecke = aufteilen(text)
    gesendet = []
    for i, stueck in enumerate(stuecke):
        letzte = i == len(stuecke) - 1
        gesendet.append(await context.bot.send_message(JAN, stueck, reply_markup=knoepfe if letzte else None))
    return gesendet


async def dateien_senden(context: ContextTypes.DEFAULT_TYPE, agent: str, dateien: list[str]) -> list:
    """Schickt Ergebnisdateien eines Agenten. Ein Fehler betrifft nur die eine Datei, Jan erfährt davon."""
    gesendet = []
    for datei in dateien:
        try:
            # noch einmal prüfen: zwischen Ablage und Senden kann sich die Datei geändert haben
            pfad = AGENTEN_DIR / agent / anhaenge_pruefen(AGENTEN_DIR / agent, [datei])[0]
            with open(pfad, "rb") as f:
                gesendet.append(await context.bot.send_document(JAN, f, filename=pfad.name, write_timeout=120))
        except (AblageFehler, OSError, TelegramError) as f:
            logger.error("Datei %s von %s nicht gesendet: %s", datei, agent, f)
            await context.bot.send_message(JAN, f"Datei nicht gesendet ({agent}): {datei}\nGrund: {f}")
    return gesendet


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
    if agent not in AGENTEN or not (UNIT_DIR / f"{dienst}.service").exists():
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


# ---------- Eingang: Nachrichten von Jan ----------

async def fremd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    u = update.effective_user
    logger.warning("Nachricht von fremder ID ignoriert: chat=%s user=%s",
                   update.effective_chat.id if update.effective_chat else "?", u.username if u else "?")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Agentenzentrale läuft.\n\n" + HILFE)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    zeilen = [
        f"Offene Entwürfe: {len(freigabe.offene())}",
        f"Warten auf Ausführung: {len(freigabe.zur_ausfuehrung())}",
        f"Unklare Ausführungen: {len(freigabe.unklare())}",
        f"Offene Aufträge: {len(auftraege.neue())}",
        f"Sitzungen am PC: {len(gemeldet.listen['am_pc'])}",
        f"Wartende Dateien: {len(eingang.wartende())}",
    ]
    await update.message.reply_text("\n".join(zeilen))


def aktuelle_stufe() -> tuple[dict | None, str]:
    stand = verbrauch.letzter_stand()
    return stand, verbrauch.stufe(stand, einstellungen.lade())


async def verbrauch_befehl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    stand, stufe = aktuelle_stufe()
    await update.message.reply_text(verbrauch_text(stand, stufe, verbrauch.heute(), verbrauch.zeit_text))


async def auftrag_befehl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ergebnis = befehl_auswerten(update.message.text)
    if ergebnis is None:
        await update.message.reply_text("Unbekannter Befehl.\n\n" + HILFE)
        return
    agent, modus, text = ergebnis
    if not text:
        await update.message.reply_text(f"Bitte den Auftrag dazuschreiben, z. B. /{agent} Fristen prüfen")
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
        await bot.send_message(JAN, f"Auftrag nicht angelegt: {e}")
        return False
    eingang.aufraeumen()
    logger.info("Auftrag %s angelegt (%s, %s, Quelle %s, Sitzung %s, Meldung %s, Dienst %s, %d Dateien)",
                aid, agent, modus, quelle, sitzung, meldung, dienst, len(dateien))
    if bestaetigen or dateien:
        wort = "Antwort" if sitzung or meldung else "Auftrag"
        mit = f" mit {len(dateien)} Datei(en): " + ", ".join(d.name for d in dateien) if dateien else ""
        await bot.send_message(JAN, f"{wort} an {agent} ({modus}) weitergegeben{mit}.")
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
        await bot.send_message(JAN, "Zu diesem Auftrag ist keine Sitzung gespeichert. "
                                    "Schick es bitte als neuen Auftrag.")
        return
    if alt["sitzung"] in gemeldet.listen["am_pc"]:
        await bot.send_message(JAN, "Diese Sitzung liegt am PC. Erst dort beenden, dann /weiter schicken.")
        return
    await auftrag_anlegen(bot, alt["agent"], alt["modus"], text, bezug=alt["id"], sitzung=alt["sitzung"])


async def pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    alt = beantworteter_auftrag(update)
    if alt is None or not alt.get("sitzung"):
        await update.message.reply_text("Bitte /pc als Antwort auf die Meldung eines Auftrags schicken.")
        return
    sitzung = alt["sitzung"]
    if any(a.get("sitzung") == sitzung for a in auftraege.neue()):
        await update.message.reply_text("Der Agent arbeitet gerade in dieser Sitzung. Bitte erst seine Antwort abwarten.")
        return
    gemeldet.listen["am_pc"].add(sitzung)
    gemeldet.speichern()
    logger.info("Sitzung %s liegt am PC", sitzung)
    await update.message.reply_text(
        f"Die Sitzung liegt jetzt am PC. Dort eingeben:\n\ncd ~/agenten/{alt['agent']} && claude --resume {sitzung}"
        "\n\nDanach den PC-Chat beenden und hier /weiter schicken.")


async def weiter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not gemeldet.listen["am_pc"]:
        await update.message.reply_text("Keine Sitzung liegt am PC.")
        return
    logger.info("Sitzungen zurück vom PC: %s", sorted(gemeldet.listen["am_pc"]))
    gemeldet.listen["am_pc"].clear()
    gemeldet.speichern()
    await update.message.reply_text("Zurück in Telegram. Antworte auf die letzte Meldung des Agenten, "
                                    "dann macht er in derselben Sitzung weiter.")


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
    # Wartet ein "Ändern" auf Jans Kommentar?
    aendern_id = context.chat_data.pop("aendern", None)
    if aendern_id:
        await aenderung_eintragen(update, aendern_id, text)
        return
    await agent_fragen(context.bot, context.chat_data, text)


async def agent_fragen(bot, chat_data: dict, text: str) -> None:
    chat_data["wartender_text"] = text
    knoepfe = InlineKeyboardMarkup(
        [[InlineKeyboardButton(a, callback_data=f"z:{a}")] for a in AGENTEN]
        + [[InlineKeyboardButton("Verwerfen", callback_data="z:-")]]
    )
    await bot.send_message(JAN, "An welchen Agenten geht das? (Modus: erledigen)", reply_markup=knoepfe)


async def aenderung_eintragen(update: Update, eid: str, kommentar: str) -> None:
    try:
        entwurf = freigabe.entscheide(eid, "aendern", kommentar)
    except freigabe.FreigabeFehler as e:
        await update.message.reply_text(f"Geht nicht: {e}")
        return
    dateien = eingang.wartende()
    auftraege.neuer_auftrag(entwurf["agent"], kommentar, quelle="telegram-aendern", bezug=eid, dateien=dateien)
    eingang.aufraeumen()
    logger.info("Entwurf %s: Änderung gewünscht (%d Dateien)", eid, len(dateien))
    mit = f" mit {len(dateien)} Datei(en)" if dateien else ""
    await update.message.reply_text(f"Änderungswunsch an {entwurf['agent']} weitergegeben{mit}.")
    await agent_starten(entwurf["agent"])


# ---------- Dateien ----------

async def datei_empfangen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    m = update.message
    if m.document:
        datei, name = m.document, m.document.file_name
    else:  # Foto: größte Fassung nehmen
        datei, name = m.photo[-1], f"foto-{datetime.now():%Y%m%d-%H%M%S}.jpg"
    if datei.file_size and datei.file_size > MAX_DATEI_BYTES:
        await m.reply_text(f"{name} ist größer als 20 MB, das lässt Telegram für Bots nicht zu. "
                           "Bitte am PC in den Agent-Ordner legen.")
        return
    pfad = eingang.neuer_platz(name or "datei")
    try:
        await (await datei.get_file()).download_to_drive(pfad)
    except Exception as e:  # Netz oder Telegram: Jan soll es wissen und neu schicken können
        logger.error("Download von %s fehlgeschlagen: %s", name, e)
        pfad.unlink(missing_ok=True)
        eingang.aufraeumen()
        await m.reply_text(f"{name} konnte nicht geladen werden ({e}). Bitte noch einmal schicken.")
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
    beispiel = f"/{ergebnis[0]} ..." if ergebnis else "/uni Fasse das zusammen"
    hinweis = "Unbekannter Befehl in der Bildunterschrift. " if text and not ergebnis else ""
    await bot.send_message(JAN, f"{hinweis}{len(eingang.wartende())} Datei(en) liegen bereit. Schick jetzt den "
                                f"Auftrag, z. B. {beispiel}. Die Dateien hängen dann daran. /verwerfen löscht sie.")


async def verwerfen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    anzahl = eingang.verwerfen()
    logger.info("%d wartende Dateien verworfen", anzahl)
    await update.message.reply_text(f"{anzahl} wartende Datei(en) gelöscht." if anzahl else "Keine wartenden Dateien.")


# ---------- Knöpfe ----------

async def knopf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if update.effective_chat is None or update.effective_chat.id != JAN:
        await fremd(update, context)
        await q.answer()
        return
    art, _, wert = q.data.partition(":")

    if art == "m":  # Knopf unter einer Meldung
        await meldung_knopf(q, context)
        return

    if art == "z":  # Agent für Text ohne Befehl gewählt
        text = context.chat_data.pop("wartender_text", None)
        await q.answer()
        if wert == "-" or text is None:
            await q.edit_message_text("Verworfen." if text else "Text nicht mehr vorhanden, bitte neu senden.")
            return
        await q.edit_message_reply_markup(None)
        await auftrag_anlegen(context.bot, wert, "erledigen", text)
        return

    eid = wert
    try:
        if art == "f":
            gesehen = gemeldet.angezeigt.get(eid)
            entwurf = freigabe.entscheide(eid, "freigegeben", gesehen=gesehen)
            antwort = "Freigegeben. Der Agent führt es jetzt aus."
        elif art == "a":
            freigabe.entscheide(eid, "abgelehnt")
            antwort = "Abgelehnt."
        elif art == "c":
            context.chat_data["aendern"] = eid
            await q.answer()
            await q.message.reply_text("Was soll geändert werden? Schreib es als nächste Nachricht.")
            return
        else:
            await q.answer("Unbekannter Knopf")
            return
    except freigabe.FreigabeFehler as e:
        logger.warning("Knopf %s für %s: %s", art, eid, e)
        await q.answer()
        await q.edit_message_reply_markup(None)
        await q.message.reply_text(f"Nicht möglich: {e}")
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
        await q.answer("Unbekannter Knopf")
        return
    if m["id"] in gemeldet.listen["geklickt"]:
        await q.answer("Schon beantwortet")
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

async def pruefen(context: ContextTypes.DEFAULT_TYPE) -> None:
    geaendert = False

    for e in freigabe.offene():
        if e["id"] in gemeldet.angezeigt:
            continue
        knoepfe = InlineKeyboardMarkup([[
            InlineKeyboardButton("Freigeben", callback_data=f"f:{e['id']}"),
            InlineKeyboardButton("Ablehnen", callback_data=f"a:{e['id']}"),
            InlineKeyboardButton("Ändern", callback_data=f"c:{e['id']}"),
        ]])
        for i, stueck in enumerate(stuecke := entwurf_als_text(e)):
            await context.bot.send_message(JAN, stueck, reply_markup=knoepfe if i == len(stuecke) - 1 else None)
        gemeldet.angezeigt[e["id"]] = e["fingerabdruck"]
        geaendert = True

    for e in freigabe.erledigte():
        if e.get("ausgefuehrt") and e["id"] not in gemeldet.listen["ausgefuehrt"]:
            wort = "Ausgeführt" if e.get("erfolgreich") else "Fehlgeschlagen"
            await senden(context, f"{wort}: {e['titel']} ({e['agent']})\n{e.get('ausfuehrung', '')}")
            gemeldet.listen["ausgefuehrt"].add(e["id"])
            geaendert = True

    for e in freigabe.unklare():
        if e["id"] not in gemeldet.listen["unklar"]:
            await senden(context, f"Unklar, ob ausgeführt: {e['titel']} ({e['agent']}).\n"
                                  f"Der Agent hat begonnen, aber nie fertig gemeldet. Bitte selbst prüfen.\nID: {e['id']}")
            gemeldet.listen["unklar"].add(e["id"])
            geaendert = True

    for a in auftraege.erledigte():
        if a["id"] not in gemeldet.listen["auftraege"]:
            wort = "Auftrag erledigt" if a["status"] == "erledigt" else "Auftrag fehlgeschlagen"
            nachrichten = await senden(context, f"{wort} ({a['agent']}): {a['text'][:200]}\n\n{a.get('ergebnis', '')}")
            nachrichten += await dateien_senden(context, a["agent"], a.get("ergebnis_dateien", []))
            for n in nachrichten:  # auch eine Antwort auf die Datei setzt die Sitzung fort
                gemeldet.nachricht_merken(n.message_id, a["id"])
            gemeldet.listen["auftraege"].add(a["id"])
            geaendert = True

    for m in meldungen.neue():
        nachrichten = await senden(context, f"[{m['agent']}] {m['text']}", knopf_leiste(m))
        await dateien_senden(context, m["agent"], m.get("dateien", []))
        meldungen.als_gesendet(m["id"])  # erst nach erfolgreichem Senden, sonst nächster Versuch
        if meldungen.nimmt_antwort(m):
            for n in nachrichten:
                gemeldet.meldung_merken(n.message_id, m["id"])
            geaendert = True

    stand, stufe = aktuelle_stufe()
    if stufe != gemeldet.stufe:
        await senden(context, f"Neue Stufe: {STUFEN_TEXT[stufe]}\n(vorher: {gemeldet.stufe})")
        logger.info("Stufe %s -> %s", gemeldet.stufe, stufe)
        gemeldet.stufe = stufe
        geaendert = True

    if geaendert:
        gemeldet.speichern()


async def fehler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Fehler: %s", context.error, exc_info=context.error)


def main() -> None:
    app = Application.builder().token(cfg["TELEGRAM_BOT_TOKEN"]).build()
    jan = filters.Chat(chat_id=JAN)
    app.add_handler(MessageHandler(~jan, fremd))
    app.add_handler(CommandHandler(["start", "hilfe"], start, filters=jan))
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
