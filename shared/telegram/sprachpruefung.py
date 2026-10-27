"""Laufzeitprüfung jeder ausgehenden Nachricht gegen die Sprachregel (agentkit.sprache), nur Warnung ins Log.

Hängt sich als rate_limiter in python-telegram-bot ein (Application.builder().rate_limiter(...)): Durch diesen Haken
läuft jede Anfrage an Telegram. Er bremst nichts und ändert nichts, er schaut nur auf Text, Beschriftung und
Knöpfe und ruft dann die Anfrage auf. Ein Fehler in der Prüfung hält keine Nachricht auf.

Ins Log kommen Endpunkt, Absender (fette erste Zeile, z. B. „Uni“) und die Befunde als Art und Glossarwort, nie der
Inhalt. Nachrichten mit erlaubten Ausnahmen (Entwürfe, Befehl unter /pc) im Block `with ausnahmen("laenge"):`.
"""

import contextvars
import logging
import re
from contextlib import contextmanager

from telegram.ext import BaseRateLimiter

from agentkit import sprache

_AUSNAHMEN: contextvars.ContextVar[tuple[str, ...]] = contextvars.ContextVar("sprache_ausnahmen", default=())
FELDER = {"sendMessage": "text", "editMessageText": "text", "answerCallbackQuery": "text",
          "sendDocument": "caption", "editMessageCaption": "caption"}


@contextmanager
def ausnahmen(*arten: str):
    """Arten (agentkit.sprache), die für die Nachrichten in diesem Block erlaubt sind."""
    marke = _AUSNAHMEN.set(arten)
    try:
        yield
    finally:
        _AUSNAHMEN.reset(marke)


def beschriftungen(markup) -> list[str]:
    """Texte der Inline-Knöpfe (Objekt oder schon als dict)."""
    zeilen = getattr(markup, "inline_keyboard", None)
    if zeilen is None and isinstance(markup, dict):
        zeilen = markup.get("inline_keyboard")
    return [k.get("text", "") if isinstance(k, dict) else getattr(k, "text", "") for z in zeilen or () for k in z]


def absender(text: str) -> str:
    m = re.match(r"<b>([^<\n]{1,30})</b>", text or "")
    return m.group(1) if m else "-"


def befunde(endpunkt: str, daten: dict, fuer: str, erlaubt: tuple[str, ...] = ()) -> list[str]:
    """Befunde zu einer Anfrage an Telegram, leer für alles ohne Text."""
    text = daten.get(FELDER.get(endpunkt, ""), "") or ""
    gefunden = sprache.pruefen(text, fuer, erlaubt) if text else []
    for k in beschriftungen(daten.get("reply_markup")):
        gefunden += ["knopf " + b for b in sprache.pruefen(k, fuer, ("laenge", *erlaubt))]
    return gefunden


class Sprachpruefung(BaseRateLimiter):
    def __init__(self, fuer: str, logger: logging.Logger):
        self.fuer, self.logger = fuer, logger

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def process_request(self, callback, args, kwargs, endpoint, data, rate_limit_args):
        try:
            if gefunden := befunde(endpoint, data, self.fuer, _AUSNAHMEN.get()):
                text = data.get(FELDER.get(endpoint, ""), "") or ""
                self.logger.warning("Sprache %s (%s): %s", endpoint, absender(text), sprache.log_text(gefunden))
        except Exception:  # die Prüfung darf keine Nachricht aufhalten
            self.logger.exception("Sprachprüfung fehlgeschlagen")
        return await callback(*args, **kwargs)
