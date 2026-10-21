"""Menü-Nachricht ("Panel") für beide Zentralen: eine Nachricht, die beim Tippen bearbeitet wird.

Die Nachrichten-ID steht in chat_data["panel"]. neu=True löscht das alte Panel und setzt ein
neues ans Ende des Chats (nach einer Nachricht der Person, damit das Menü unten bleibt).
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, TelegramError

Knoepfe = list[list[tuple[str, str]]]
logger = logging.getLogger("zentrale")


def markup(knoepfe: Knoepfe) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=d) for t, d in z] for z in knoepfe])


async def zeigen(bot, chat_id: int, chat_data: dict, text: str, knoepfe: Knoepfe, neu: bool = False) -> None:
    mid = chat_data.get("panel")
    if mid and not neu:
        try:
            await bot.edit_message_text(text, chat_id, mid, reply_markup=markup(knoepfe))
            return
        except BadRequest as e:
            if "not modified" in str(e):
                return
            logger.info("Panel nicht bearbeitbar (%s), lege neues an", e)
    if mid:
        try:
            await bot.delete_message(chat_id, mid)
        except TelegramError:
            pass  # zu alt oder schon weg: dann bleibt es eben stehen
    nachricht = await bot.send_message(chat_id, text, reply_markup=markup(knoepfe))
    chat_data["panel"] = nachricht.message_id
