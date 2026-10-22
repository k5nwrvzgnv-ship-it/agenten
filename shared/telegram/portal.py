"""Lias Zentrale: Telegram-Bot für Lias Instanz, Bedienung nur über Knöpfe.

Läuft mit AGENTKIT_INSTANZ=<instanz-ordner> (Dienst lia-zentrale). Ohne die Variable startet
er nicht, damit er nie Jans Warteschlangen oder Jans Token benutzt. Jans Zentrale (zentrale.py)
bleibt davon unberührt.

- Reagiert nur auf Lias Chat-ID (TELEGRAM_CHAT_ID in <instanz-ordner>/.env).
- Oberfläche: eine einzige Menü-Nachricht (Panel), die beim Tippen bearbeitet wird
  (Ansichten in portal_logik). Schreibt Lia etwas, wird das alte Panel gelöscht und ein neues
  unter ihre Nachricht gesetzt. Die Nachrichten-ID steht in chat_data["panel"].
- Bestätigte Aufträge gehen nach <instanz-ordner>/auftraege/neu/, danach startet
  lia-<agent>.service. Ergebnisse kommen als eigene Nachricht zurück, Ergebnisdateien (Feld
  ergebnis_dateien, nur aus dem Agent-Ordner) als Dokumente dahinter, zuletzt der Knopf "Menü".
- Dateien und Fotos (bis 20 MB) warten in <instanz-ordner>/zentrale/data/eingang/, bis Lia schreibt, was damit
  passieren soll (Bildunterschrift oder nächste Nachricht). Beim Abschicken eines Material- oder
  Frage-Auftrags verschiebt agentkit.auftraege sie nach <agent>/data/eingang/<auftrag-id>/.
  Alben werden ALBUM_WARTEN Sekunden nach der letzten Datei zugeordnet. Sprachnachrichten nicht.
- Ins Log kommen nur IDs und Arten, keine Inhalte von Lia.

Start: AGENTKIT_INSTANZ=... .venv/bin/python portal.py
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from telegram import LinkPreviewOptions, Update
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
    Defaults,
    MessageHandler,
    filters,
)

from agentkit import auftraege, config, log
from agentkit._ablage import AblageFehler, anhaenge_pruefen
from logik import MAX_DATEI_BYTES, Eingang, Gemeldet, aufteilen
import panel as panel_
import portal_logik as p

UNIT_DIR = Path.home() / ".config" / "systemd" / "user"
AGENTEN_DIR = auftraege.AGENTEN_DIR
PRUEF_INTERVALL = 30  # Sekunden
ALBUM_WARTEN = 3  # Sekunden nach der letzten Datei eines Albums, dann wird zugeordnet

if config.SHARED_DIR == config.instanz_dir({}):
    raise SystemExit("portal.py braucht AGENTKIT_INSTANZ (sonst liefe er in Jans Instanz)")
DATEN_DIR = config.SHARED_DIR / "zentrale"  # data/ und logs/ von Lias Zentrale
cfg = config.lade_config(DATEN_DIR, pflicht=("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"))
LIA = int(cfg["TELEGRAM_CHAT_ID"])
logger = log.hole_logger(DATEN_DIR, "zentrale")
# httpx loggt Anfrage-Adressen, und die enthalten den Bot-Token: nur Warnungen zulassen.
logging.getLogger("httpx").setLevel(logging.WARNING)
gemeldet = Gemeldet(DATEN_DIR / "data" / "gemeldet.json")
eingang = Eingang(DATEN_DIR / "data" / "eingang")


def home(hinweis: str = "") -> tuple[str, p.Knoepfe]:
    hinweis = "\n".join(h for h in (hinweis, p.hinweis_dateien(len(eingang.wartende()))) if h)
    return p.ansicht_home(len(auftraege.neue()), len(auftraege.erledigte()), hinweis)


def nach_text(chat_data: dict, folge: str, text: str) -> tuple[str, p.Knoepfe]:
    """Ansicht nach Lias Text (Nachricht oder Bildunterschrift), siehe portal_logik.text_eingang."""
    if folge == "home":
        return home()
    if folge == "bestaetigen":
        return p.ansicht_bestaetigen(chat_data["entwurf"], len(eingang.wartende()))
    return p.ansicht_einordnen(text)


async def panel(bot, chat_data: dict, ansicht: tuple[str, p.Knoepfe], neu: bool = False) -> None:
    """Zeigt die Ansicht im Panel. neu=True: altes Panel löschen, neues unten anlegen."""
    await panel_.zeigen(bot, LIA, chat_data, *ansicht, neu=neu)


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
    dateien = eingang.wartende() if entwurf["art"] != "woche" else []  # Woche ist ein fester Knopf
    try:
        aid = auftraege.neuer_auftrag(art.agent, entwurf["text"], quelle=art.quelle, dateien=dateien)
    except auftraege.AuftragFehler as e:
        logger.error("Auftrag an %s nicht angelegt: %s", art.agent, e)
        return p.FEHLGESCHLAGEN
    finally:
        eingang.aufraeumen()
    logger.info("Auftrag %s angelegt (%s, %d Dateien)", aid, entwurf["art"], len(dateien))
    await agent_starten(art.agent)
    mit = f" (mit {p.dateien_anzahl(len(dateien))})" if dateien else ""
    return f"Ist unterwegs: „{p.kurz(entwurf['text'])}“{mit}\nIch melde mich mit der Antwort."


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
    await panel(context.bot, context.chat_data, nach_text(context.chat_data, folge, text), neu=True)


async def datei_empfangen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dokument oder Foto laden und warten lassen, bis klar ist, was damit passieren soll."""
    m = update.message
    if m.document:
        datei, name = m.document, m.document.file_name
    else:  # Foto: größte Fassung nehmen
        datei, name = m.photo[-1], f"foto-{datetime.now():%Y%m%d-%H%M%S}.jpg"
    if datei.file_size and datei.file_size > MAX_DATEI_BYTES:
        logger.info("Datei über 20 MB abgelehnt")
        hinweis = "Die Datei ist größer als 20 MB, das lässt Telegram nicht zu. Schick sie Jan bitte anders."
        await panel(context.bot, context.chat_data, home(hinweis), neu=True)
        return
    pfad = eingang.neuer_platz(name or "datei")
    try:
        await (await datei.get_file()).download_to_drive(pfad)
    except Exception as e:  # Netz oder Telegram: Lia soll sie noch einmal schicken können
        logger.error("Download fehlgeschlagen: %s", e)
        pfad.unlink(missing_ok=True)
        eingang.aufraeumen()
        await panel(context.bot, context.chat_data,
                    home("Die Datei konnte ich nicht laden. Schick sie bitte noch einmal."), neu=True)
        return
    logger.info("Datei empfangen (%d Bytes)", pfad.stat().st_size)
    if m.media_group_id is None:
        await dateien_zuordnen(context.bot, context.chat_data, m.caption)
        return
    # Album: Telegram schickt jede Datei als eigene Nachricht, die Bildunterschrift nur bei einer.
    alben = context.chat_data.setdefault("alben", {})
    album = alben.setdefault(m.media_group_id, {"caption": None, "job": None})
    album["caption"] = album["caption"] or m.caption
    if album["job"]:
        album["job"].schedule_removal()
    album["job"] = context.job_queue.run_once(album_fertig, ALBUM_WARTEN, data=m.media_group_id, chat_id=LIA)


async def album_fertig(context: ContextTypes.DEFAULT_TYPE) -> None:
    album = context.chat_data.get("alben", {}).pop(context.job.data, None)
    if album:
        await dateien_zuordnen(context.bot, context.chat_data, album["caption"])


async def dateien_zuordnen(bot, chat_data: dict, caption: str | None) -> None:
    """Bildunterschrift wie eine Nachricht behandeln; ohne sie auf Lias nächste Nachricht warten."""
    text = (caption or "").strip()
    if text:
        folge = p.text_eingang(chat_data, text)
        logger.info("Bildunterschrift -> %s", folge)
        ansicht = nach_text(chat_data, folge, text)
    elif chat_data.get("entwurf"):  # schon beim Bestätigen: Dateien kommen mit
        ansicht = p.ansicht_bestaetigen(chat_data["entwurf"], len(eingang.wartende()))
    else:
        ansicht = p.ansicht_dateien(len(eingang.wartende()))
    await panel(bot, chat_data, ansicht, neu=True)


async def sonstiges_empfangen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Weder Text noch Datei empfangen (Sprachnachricht o. Ä.)")
    hinweis = "Sprachnachrichten kann ich noch nicht annehmen. Schreib mir bitte als Text."
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
            ansicht = p.ansicht_bestaetigen(z["entwurf"], len(eingang.wartende()))
        else:
            ansicht = home("Das ist nicht mehr aktuell.")
    elif wert == "ja":
        entwurf = p.entwurf_nehmen(z)
        ansicht = home(await abschicken(entwurf) if entwurf else "Das ist nicht mehr aktuell.")
    elif wert == "verwerfen":
        ansicht = home(f"{p.dateien_anzahl(eingang.verwerfen())} verworfen.")
    else:  # nein: Abbrechen bzw. Verwerfen, mitgeschickte Dateien auch
        p.abbrechen(z)
        eingang.verwerfen()
        ansicht = home("Abgebrochen.")
    await panel(context.bot, z, ansicht)


# ---------- Ausgang: regelmäßige Prüfung ----------

async def dateien_senden(bot, agent: str, dateien: list[str]) -> bool:
    """Schickt Ergebnisdateien eines Agenten (nur Dateien im Agent-Ordner). True, wenn alle ankamen."""
    alle = True
    for datei in dateien:
        try:
            # noch einmal prüfen: zwischen Ablage und Senden kann sich die Datei geändert haben
            pfad = AGENTEN_DIR / agent / anhaenge_pruefen(AGENTEN_DIR / agent, [datei])[0]
            with open(pfad, "rb") as f:
                await bot.send_document(LIA, f, filename=pfad.name, write_timeout=120)
        except (AblageFehler, OSError, TelegramError) as e:
            logger.error("Datei %s von %s nicht gesendet: %s", datei, agent, e)
            alle = False
    return alle


async def pruefen(context: ContextTypes.DEFAULT_TYPE) -> None:
    neu = [a for a in auftraege.erledigte() if a["id"] not in gemeldet.listen["auftraege"]]
    for a in neu:
        dateien = a.get("ergebnis_dateien") or []
        stuecke = aufteilen(p.ergebnis_text(a))
        for i, stueck in enumerate(stuecke):
            letzte = i == len(stuecke) - 1 and not dateien
            await context.bot.send_message(LIA, stueck, reply_markup=panel_.markup(p.MENUE_KNOPF) if letzte else None)
        if dateien:
            ok = await dateien_senden(context.bot, a["agent"], dateien)
            await context.bot.send_message(LIA, p.dateien_text(len(dateien), ok),
                                           reply_markup=panel_.markup(p.MENUE_KNOPF))
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
    app.add_handler(MessageHandler(lia & (filters.Document.ALL | filters.PHOTO), datei_empfangen))
    app.add_handler(MessageHandler(lia, sonstiges_empfangen))
    app.add_handler(CallbackQueryHandler(knopf))
    app.add_error_handler(fehler)
    app.job_queue.run_repeating(pruefen, interval=PRUEF_INTERVALL, first=5)
    logger.info("Lias Zentrale startet (Instanz %s)", config.SHARED_DIR)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
