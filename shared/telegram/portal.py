"""Lias Zentrale: Telegram-Bot für Lias Instanz, Bedienung nur über Knöpfe.

Läuft mit AGENTKIT_INSTANZ=<instanz>/shared (Dienst lia-zentrale). Ohne die Variable startet
er nicht, damit er nie Jans Warteschlangen oder Jans Token benutzt. Jans Zentrale (zentrale.py)
bleibt davon unberührt.

- Reagiert nur auf Lias Chat-ID (TELEGRAM_CHAT_ID in <instanz>/shared/.env).
- Menü als Nachricht mit Knöpfen (portal_logik.MENUE). Jede abschließende Nachricht des Bots
  trägt das Menü, so ist es immer an der letzten Nachricht.
- Bestätigte Aufträge gehen nach <instanz>/shared/auftraege/neu/, danach startet
  lia-<agent>.service. Ergebnisse kommen ohne Technik zurück (portal_logik.ergebnis_text).
- Dateien nimmt er noch nicht an.
- Ins Log kommen nur IDs und Arten, keine Inhalte von Lia.

Start: AGENTKIT_INSTANZ=... .venv/bin/python portal.py
"""

import asyncio
import logging
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
    Defaults,
    MessageHandler,
    filters,
)

from agentkit import auftraege, config, log
from logik import Gemeldet, aufteilen
import portal_logik as p

UNIT_DIR = Path.home() / ".config" / "systemd" / "user"
PRUEF_INTERVALL = 30  # Sekunden

if config.SHARED_DIR == config.instanz_dir({}):
    raise SystemExit("portal.py braucht AGENTKIT_INSTANZ (sonst liefe er in Jans Instanz)")
DATEN_DIR = config.SHARED_DIR / "zentrale"  # data/ und logs/ von Lias Zentrale
cfg = config.lade_config(DATEN_DIR, pflicht=("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"))
LIA = int(cfg["TELEGRAM_CHAT_ID"])
logger = log.hole_logger(DATEN_DIR, "zentrale")
# httpx loggt Anfrage-Adressen, und die enthalten den Bot-Token: nur Warnungen zulassen.
logging.getLogger("httpx").setLevel(logging.WARNING)
gemeldet = Gemeldet(DATEN_DIR / "data" / "gemeldet.json")


def knoepfe(zeilen: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=d) for t, d in z] for z in zeilen])


MENUE = knoepfe(p.menue_knoepfe())


async def senden(bot, text: str, markup=MENUE) -> None:
    """Text an Lia, lange Texte in Stücken. Die Knöpfe hängen an der letzten Nachricht."""
    stuecke = aufteilen(text)
    for i, stueck in enumerate(stuecke):
        await bot.send_message(LIA, stueck, reply_markup=markup if i == len(stuecke) - 1 else None)


async def agent_starten(agent: str) -> None:
    """Startet lia-<agent>.service, falls es ihn gibt (--no-block: nicht auf das Ende warten)."""
    dienst = f"lia-{agent}"
    if not (UNIT_DIR / f"{dienst}.service").exists():
        logger.info("Kein Dienst %s.service, Auftrag wartet", dienst)
        return
    proc = await asyncio.create_subprocess_exec(
        "systemctl", "--user", "start", "--no-block", f"{dienst}.service",
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        logger.error("Start von %s.service fehlgeschlagen: %s", dienst, err.decode().strip())


# ---------- Eingang: Nachrichten von Lia ----------

async def fremd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    logger.warning("Nachricht von fremder ID ignoriert: chat=%s", chat.id if chat else "?")


async def begruessen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start und jeder andere Befehl: Begrüßung mit Menü (Befehle braucht Lia nicht)."""
    context.chat_data.clear()
    await senden(context.bot, p.BEGRUESSUNG)


async def text_empfangen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rueckfrage = p.text_eingang(context.chat_data, update.message.text)
    await senden(context.bot, rueckfrage, knoepfe(p.BESTAETIGEN_KNOEPFE))


async def datei_empfangen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await senden(context.bot, "Dateien kann ich noch nicht annehmen. Das kommt bald.")


# ---------- Knöpfe ----------

async def knopf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    if update.effective_chat is None or update.effective_chat.id != LIA:
        await fremd(update, context)
        return
    wert = p.knopf_auswerten(q.data or "")
    if wert is None:
        await senden(context.bot, p.ABGELAUFEN)
    elif wert == "menue":
        await senden(context.bot, p.MENUE_TEXT)
    elif wert in p.MENUE:
        text, bestaetigen = p.menue_gewaehlt(context.chat_data, wert)
        await senden(context.bot, text, knoepfe(p.BESTAETIGEN_KNOEPFE) if bestaetigen else None)
    else:  # ja / nein unter einer Rückfrage
        await q.edit_message_reply_markup(None)
        entwurf = p.entwurf_nehmen(context.chat_data)
        if entwurf is None:
            await senden(context.bot, p.ABGELAUFEN)
        elif wert == "nein":
            await senden(context.bot, p.VERWORFEN)
        else:
            await abschicken(context.bot, entwurf)


async def abschicken(bot, entwurf: dict) -> None:
    art = p.ARTEN[entwurf["art"]]
    try:
        aid = auftraege.neuer_auftrag(art.agent, entwurf["text"], quelle=art.quelle)
    except auftraege.AuftragFehler as e:
        logger.error("Auftrag an %s nicht angelegt: %s", art.agent, e)
        await senden(bot, p.FEHLGESCHLAGEN)
        return
    logger.info("Auftrag %s angelegt (%s)", aid, entwurf["art"])
    await senden(bot, p.WEITERGEGEBEN)
    await agent_starten(art.agent)


# ---------- Ausgang: regelmäßige Prüfung ----------

async def pruefen(context: ContextTypes.DEFAULT_TYPE) -> None:
    geaendert = False
    for a in auftraege.erledigte():
        if a["id"] in gemeldet.listen["auftraege"]:
            continue
        await senden(context.bot, p.ergebnis_text(a))
        gemeldet.listen["auftraege"].add(a["id"])
        logger.info("Ergebnis zu %s gesendet (%s)", a["id"], a["status"])
        geaendert = True
    if geaendert:
        gemeldet.speichern()


async def fehler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Fehler: %s", context.error, exc_info=context.error)


def main() -> None:
    vorgaben = Defaults(link_preview_options=LinkPreviewOptions(is_disabled=True))
    app = Application.builder().token(cfg["TELEGRAM_BOT_TOKEN"]).defaults(vorgaben).build()
    lia = filters.Chat(chat_id=LIA)
    app.add_handler(MessageHandler(~lia, fremd))
    app.add_handler(MessageHandler(lia & filters.COMMAND, begruessen))
    app.add_handler(MessageHandler(lia & filters.TEXT, text_empfangen))
    app.add_handler(MessageHandler(lia, datei_empfangen))
    app.add_handler(CallbackQueryHandler(knopf))
    app.add_error_handler(fehler)
    app.job_queue.run_repeating(pruefen, interval=PRUEF_INTERVALL, first=5)
    logger.info("Lias Zentrale startet (Instanz %s)", config.SHARED_DIR)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
