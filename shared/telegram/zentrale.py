"""Telegram-Zentrale: einziger Kontakt zwischen Jan und den Agenten.

- Reagiert nur auf Jans Chat-ID (TELEGRAM_CHAT_ID).
- Zeigt neue Entwürfe aus shared/freigabe/offen/ mit Knöpfen an.
- /uni ..., /unilern ... usw. werden zu Aufträgen in shared/auftraege/neu/.
- Meldet ausgeführte Entwürfe, unklare Fälle und erledigte Aufträge.
- Verschickt Meldungen der Agenten aus shared/meldungen/neu/ (Fristen, wichtige Mails ...).

Start: .venv/bin/python zentrale.py
"""

import asyncio
import logging
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from agentkit import auftraege, config, einstellungen, freigabe, log, meldungen, verbrauch
from logik import AGENTEN, STUFEN_TEXT, Gemeldet, aufteilen, befehl_auswerten, entwurf_als_text, verbrauch_text

HIER = Path(__file__).resolve().parent
UNIT_DIR = Path.home() / ".config" / "systemd" / "user"
PRUEF_INTERVALL = 30  # Sekunden

cfg = config.lade_config(HIER, pflicht=("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"))
JAN = int(cfg["TELEGRAM_CHAT_ID"])
logger = log.hole_logger(HIER, "zentrale")
# httpx loggt Anfrage-Adressen, und die enthalten den Bot-Token: nur Warnungen zulassen.
logging.getLogger("httpx").setLevel(logging.WARNING)
gemeldet = Gemeldet(HIER / "data" / "gemeldet.json")

HILFE = (
    "Befehle:\n"
    + "\n".join(f"/{a} <Auftrag>  (erledigen)\n/{a}lern <Auftrag>  (gemeinsam lernen)" for a in AGENTEN)
    + "\n/status  Überblick\n/verbrauch  Auslastung des Claude-Kontingents\n"
    "Text ohne Befehl: Ich frage, an welchen Agenten er geht."
)


async def senden(context: ContextTypes.DEFAULT_TYPE, text: str, knoepfe=None) -> None:
    stuecke = aufteilen(text)
    for i, stueck in enumerate(stuecke):
        letzte = i == len(stuecke) - 1
        await context.bot.send_message(JAN, stueck, reply_markup=knoepfe if letzte else None)


async def agent_starten(agent: str) -> None:
    """Startet <agent>.service, falls es ihn gibt (--no-block: nicht auf das Ende warten)."""
    if agent not in AGENTEN or not (UNIT_DIR / f"{agent}.service").exists():
        logger.info("Kein Dienst %s.service, Auftrag wartet auf den nächsten Lauf", agent)
        return
    proc = await asyncio.create_subprocess_exec(
        "systemctl", "--user", "start", "--no-block", f"{agent}.service",
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        logger.error("Start von %s.service fehlgeschlagen: %s", agent, err.decode().strip())
    else:
        logger.info("%s.service gestartet", agent)


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
    await auftrag_anlegen(update, agent, modus, text)


async def auftrag_anlegen(update: Update, agent: str, modus: str, text: str, bezug: str | None = None) -> None:
    aid = auftraege.neuer_auftrag(agent, text, modus=modus, bezug=bezug)
    logger.info("Auftrag %s angelegt (%s, %s)", aid, agent, modus)
    await update.effective_message.reply_text(f"Auftrag an {agent} ({modus}) angelegt.")
    await agent_starten(agent)


async def text_ohne_befehl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    # Wartet ein "Ändern" auf Jans Kommentar?
    aendern_id = context.chat_data.pop("aendern", None)
    if aendern_id:
        await aenderung_eintragen(update, aendern_id, text)
        return
    context.chat_data["wartender_text"] = text
    knoepfe = InlineKeyboardMarkup(
        [[InlineKeyboardButton(a, callback_data=f"z:{a}")] for a in AGENTEN]
        + [[InlineKeyboardButton("Verwerfen", callback_data="z:-")]]
    )
    await update.message.reply_text("An welchen Agenten geht das? (Modus: erledigen)", reply_markup=knoepfe)


async def aenderung_eintragen(update: Update, eid: str, kommentar: str) -> None:
    try:
        entwurf = freigabe.entscheide(eid, "aendern", kommentar)
    except freigabe.FreigabeFehler as e:
        await update.message.reply_text(f"Geht nicht: {e}")
        return
    auftraege.neuer_auftrag(entwurf["agent"], kommentar, quelle="telegram-aendern", bezug=eid)
    logger.info("Entwurf %s: Änderung gewünscht", eid)
    await update.message.reply_text(f"Änderungswunsch an {entwurf['agent']} weitergegeben.")
    await agent_starten(entwurf["agent"])


# ---------- Knöpfe ----------

async def knopf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if update.effective_chat is None or update.effective_chat.id != JAN:
        await fremd(update, context)
        await q.answer()
        return
    art, _, wert = q.data.partition(":")

    if art == "z":  # Agent für Text ohne Befehl gewählt
        text = context.chat_data.pop("wartender_text", None)
        await q.answer()
        if wert == "-" or text is None:
            await q.edit_message_text("Verworfen." if text else "Text nicht mehr vorhanden, bitte neu senden.")
            return
        await q.edit_message_reply_markup(None)
        await auftrag_anlegen(update, wert, "erledigen", text)
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
            await senden(context, f"{wort} ({a['agent']}): {a['text'][:200]}\n\n{a.get('ergebnis', '')}")
            gemeldet.listen["auftraege"].add(a["id"])
            geaendert = True

    for m in meldungen.neue():
        await senden(context, f"[{m['agent']}] {m['text']}")
        meldungen.als_gesendet(m["id"])  # erst nach erfolgreichem Senden, sonst nächster Versuch

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
    app.add_handler(MessageHandler(jan & filters.COMMAND, auftrag_befehl))
    app.add_handler(MessageHandler(jan & filters.TEXT, text_ohne_befehl))
    app.add_handler(CallbackQueryHandler(knopf))
    app.add_error_handler(fehler)
    app.job_queue.run_repeating(pruefen, interval=PRUEF_INTERVALL, first=5)
    logger.info("Zentrale startet")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
