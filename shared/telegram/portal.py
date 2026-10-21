"""Lias Zentrale: Telegram-Bot für Lias Instanz, Bedienung nur über Knöpfe.

Läuft mit AGENTKIT_INSTANZ=<instanz>/shared (Dienst lia-zentrale). Ohne die Variable startet
er nicht, damit er nie Jans Warteschlangen oder Jans Token benutzt. Jans Zentrale (zentrale.py)
bleibt davon unberührt.

- Reagiert nur auf Lias Chat-ID (TELEGRAM_CHAT_ID in <instanz>/shared/.env).
- Oberfläche: eine einzige Menü-Nachricht (Panel), die beim Tippen bearbeitet wird
  (Ansichten in portal_logik). Schreibt Lia etwas, wird das alte Panel gelöscht und ein neues
  unter ihre Nachricht gesetzt. Die Nachrichten-ID steht in chat_data["panel"].
- Bestätigte Aufträge gehen nach <instanz>/shared/auftraege/neu/, danach startet
  lia-<agent>.service. Ergebnisse kommen als eigene Nachricht mit Knopf "Menü" zurück.
- Dateien nimmt er noch nicht an.
- Ins Log kommen nur IDs und Arten, keine Inhalte von Lia.

Start: AGENTKIT_INSTANZ=... .venv/bin/python portal.py
"""

import asyncio
import logging
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions, Update
from telegram.error import BadRequest, TelegramError
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


def markup(knoepfe: p.Knoepfe) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=d) for t, d in z] for z in knoepfe])


def home(hinweis: str = "") -> tuple[str, p.Knoepfe]:
    return p.ansicht_home(len(auftraege.neue()), len(auftraege.erledigte()), hinweis)


async def panel(bot, chat_data: dict, ansicht: tuple[str, p.Knoepfe], neu: bool = False) -> None:
    """Zeigt die Ansicht im Panel. neu=True: altes Panel löschen, neues unten anlegen."""
    text, knoepfe = ansicht
    mid = chat_data.get("panel")
    if mid and not neu:
        try:
            await bot.edit_message_text(text, LIA, mid, reply_markup=markup(knoepfe))
            return
        except BadRequest as e:
            if "not modified" in str(e):
                return
            logger.info("Panel nicht bearbeitbar (%s), lege neues an", e)
    if mid:
        try:
            await bot.delete_message(LIA, mid)
        except TelegramError:
            pass  # zu alt oder schon weg: dann bleibt es eben stehen
    nachricht = await bot.send_message(LIA, text, reply_markup=markup(knoepfe))
    chat_data["panel"] = nachricht.message_id


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


async def abschicken(entwurf: dict) -> str:
    """Legt den Auftrag an und startet den Agenten. Gibt den Hinweis fürs Panel zurück."""
    art = p.ARTEN[entwurf["art"]]
    try:
        aid = auftraege.neuer_auftrag(art.agent, entwurf["text"], quelle=art.quelle)
    except auftraege.AuftragFehler as e:
        logger.error("Auftrag an %s nicht angelegt: %s", art.agent, e)
        return p.FEHLGESCHLAGEN
    logger.info("Auftrag %s angelegt (%s)", aid, entwurf["art"])
    await agent_starten(art.agent)
    return f"Ist unterwegs: „{p.kurz(entwurf['text'])}“\nIch melde mich mit der Antwort."


# ---------- Eingang: Nachrichten von Lia ----------

async def fremd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    logger.warning("Nachricht von fremder ID ignoriert: chat=%s", chat.id if chat else "?")


async def begruessen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start und jeder andere Befehl: Menü (Befehle braucht Lia nicht)."""
    p.abbrechen(context.chat_data)
    await panel(context.bot, context.chat_data, home(), neu=True)


async def text_empfangen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    folge = p.text_eingang(context.chat_data, text)
    logger.info("Text empfangen -> %s", folge)
    if folge == "home":
        ansicht = home()
    elif folge == "bestaetigen":
        ansicht = p.ansicht_bestaetigen(context.chat_data["entwurf"])
    else:
        ansicht = p.ansicht_einordnen(text)
    await panel(context.bot, context.chat_data, ansicht, neu=True)


async def sonstiges_empfangen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Kein Text empfangen (Datei, Sprachnachricht o. Ä.)")
    hinweis = "Dateien, Fotos und Sprachnachrichten kann ich noch nicht annehmen. Schreib mir bitte als Text."
    await panel(context.bot, context.chat_data, home(hinweis), neu=True)


# ---------- Knöpfe ----------

async def knopf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    if update.effective_chat is None or update.effective_chat.id != LIA:
        await fremd(update, context)
        return
    z = context.chat_data
    wert = p.knopf_auswerten(q.data or "")
    logger.info("Knopf %s", wert)
    if wert == "menue":  # unter einem Ergebnis: Menü unten neu
        p.abbrechen(z)
        await panel(context.bot, z, home(), neu=True)
        return
    z["panel"] = q.message.message_id  # die angetippte Nachricht ist das Panel
    if wert is None:
        ansicht = home("Dieser Knopf ist nicht mehr aktuell.")
    elif wert in ("home", "neu"):
        p.abbrechen(z)
        ansicht = home()
    elif wert in ("material", "frage"):
        p.anleitung_gewaehlt(z, wert)
        ansicht = p.ansicht_anleitung(wert)
    elif wert == "woche":
        ansicht = home(await abschicken(p.sofort_entwurf(z, "woche")))
    elif wert == "anfragen":
        ansicht = p.ansicht_anfragen(auftraege.neue() + auftraege.erledigte())
    elif wert == "hilfe":
        ansicht = p.ansicht_hilfe()
    elif wert in ("alsmaterial", "alsfrage"):
        if p.einordnen(z, wert[len("als"):]):
            ansicht = p.ansicht_bestaetigen(z["entwurf"])
        else:
            ansicht = home("Das ist nicht mehr aktuell.")
    elif wert == "ja":
        entwurf = p.entwurf_nehmen(z)
        ansicht = home(await abschicken(entwurf) if entwurf else "Das ist nicht mehr aktuell.")
    else:  # nein
        p.abbrechen(z)
        ansicht = home("Abgebrochen.")
    await panel(context.bot, z, ansicht)


# ---------- Ausgang: regelmäßige Prüfung ----------

async def pruefen(context: ContextTypes.DEFAULT_TYPE) -> None:
    neu = [a for a in auftraege.erledigte() if a["id"] not in gemeldet.listen["auftraege"]]
    for a in neu:
        stuecke = aufteilen(p.ergebnis_text(a))
        for i, stueck in enumerate(stuecke):
            letzte = i == len(stuecke) - 1
            await context.bot.send_message(LIA, stueck, reply_markup=markup(p.MENUE_KNOPF) if letzte else None)
        gemeldet.listen["auftraege"].add(a["id"])
        logger.info("Ergebnis zu %s gesendet (%s)", a["id"], a["status"])
    if neu:
        gemeldet.speichern()
        chat_data = context.application.chat_data[LIA]
        if chat_data.get("panel") and not chat_data.get("entwurf") and not chat_data.get("wartet_auf"):
            await panel(context.bot, chat_data, home())  # Zahlen im Panel auffrischen


async def fehler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Fehler: %s", context.error, exc_info=context.error)


def main() -> None:
    vorgaben = Defaults(link_preview_options=LinkPreviewOptions(is_disabled=True))
    app = Application.builder().token(cfg["TELEGRAM_BOT_TOKEN"]).defaults(vorgaben).build()
    lia = filters.Chat(chat_id=LIA)
    app.add_handler(MessageHandler(~lia, fremd))
    app.add_handler(MessageHandler(lia & filters.COMMAND, begruessen))
    app.add_handler(MessageHandler(lia & filters.TEXT, text_empfangen))
    app.add_handler(MessageHandler(lia, sonstiges_empfangen))
    app.add_handler(CallbackQueryHandler(knopf))
    app.add_error_handler(fehler)
    app.job_queue.run_repeating(pruefen, interval=PRUEF_INTERVALL, first=5)
    logger.info("Lias Zentrale startet (Instanz %s)", config.SHARED_DIR)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
