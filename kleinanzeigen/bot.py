"""Telegram-Bot des Agenten kleinanzeigen (Dauerdienst kleinanzeigen.service).

Nutzer (Chat-IDs in ERLAUBTE_CHAT_IDS) legen per Text oder Foto Suchen an. Alle TAKT_MIN Minuten
holt der Bot die neuesten Anzeigen jeder aktiven Suche, Python filtert vor, Claude (Sonnet über
agentkit.claude_lauf) bewertet nur neue Kandidaten, gute Angebote kommen sofort mit Link.
Der Bot schreibt nie selbst an Verkäufer und hat kein Kleinanzeigen-Konto.
"""

import asyncio
import copy
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler,
                          filters)

from agentkit import claude_lauf, config, einstellungen
from agentkit.log import hole_logger

import bewertung
import eingabe
import pruefung
import seite
from abruf import Abruf, AbrufFehler
from db import Speicher
from texte import HILFE, e, ist_nacht, suche_text, tag

AGENT = "kleinanzeigen"
HIER = Path(__file__).resolve().parent
DB_PFAD = HIER / "data" / "kleinanzeigen.db"
FOTO_DIR = HIER / "data" / "fotos"
STANDARD_UMKREIS = 30

log = hole_logger(HIER, AGENT)


class Einstellung:
    """Werte aus kleinanzeigen/.env. Bewusst NICHT aus shared/.env: dort steht der Token der Zentrale."""

    def __init__(self, werte: dict[str, str]):
        self.token = werte.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.erlaubt = eingabe.chat_ids_lesen(werte.get("ERLAUBTE_CHAT_IDS", ""))
        self.takt_min = max(2, int(werte.get("TAKT_MIN") or 5))
        self.tagesgrenze = int(werte.get("TAGESGRENZE") or 100)
        self.schwelle = int(werte.get("MELDE_SCHWELLE") or bewertung.MELDE_SCHWELLE)
        von, _, bis = (werte.get("NACHTRUHE") or "1-6").partition("-")
        self.nacht = (int(von), int(bis or von))


E = Einstellung(config.lies_env(HIER / ".env"))
sp = Speicher(DB_PFAD)
abruf: Abruf | None = None
_durchgang = asyncio.Lock()


# ---------- Claude ----------

def _lauf_cfg(foto: bool) -> dict:
    cfg = copy.deepcopy(einstellungen.lade())
    cfg["werkzeuge"][AGENT] = [""]  # keine Werkzeuge; mit Foto nur Read im Fotoordner (lese_ordner)
    cfg["lauf"].update(max_schritte=6 if foto else 3, max_minuten=5, warten_minuten=3)
    return cfg


def claude_text(prompt: str, zeitgesteuert: bool, lese_ordner: list[Path] | None = None) -> str:
    """Ein Claude-Lauf (Sonnet, art routine), blockierend: nur über asyncio.to_thread aufrufen."""
    erg = claude_lauf.laufen(AGENT, HIER, prompt, art="routine", zeitgesteuert=zeitgesteuert,
                             cfg=_lauf_cfg(bool(lese_ordner)), lese_ordner=lese_ordner)
    if not erg.ok:
        raise RuntimeError(f"Claude-Lauf fehlgeschlagen: {erg.text[:200]}")
    return erg.text


# ---------- Zugang ----------

def erlaubt(update: Update) -> bool:
    return update.effective_chat is not None and update.effective_chat.id in E.erlaubt


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    if not erlaubt(update):
        # Einmal die Chat-ID nennen, damit Jan sie in ERLAUBTE_CHAT_IDS eintragen kann
        if sp.wert(f"fremd_{chat}") is None:
            sp.wert_setzen(f"fremd_{chat}", "1")
            log.info("Unbekannter Chat %s hat /start geschickt", chat)
            await update.message.reply_text(f"Dieser Bot ist privat. Deine Chat-ID: {chat}")
        return
    await update.message.reply_html("Kleinanzeigen-Agent bereit.\n\n" + HILFE)


async def hilfe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if erlaubt(update):
        await update.message.reply_html(HILFE)


# ---------- Suche anlegen ----------

async def neue_suche(update: Update, text: str, foto_dir: Path | None) -> None:
    chat = update.effective_chat.id
    msg = await update.message.reply_text("Schaue es mir an …")
    try:
        prompt = bewertung.such_prompt(text, str(foto_dir / "foto.jpg") if foto_dir else None)
        antwort = await asyncio.to_thread(claude_text, prompt, False, [foto_dir] if foto_dir else None)
        daten = bewertung.such_antwort_pruefen(antwort)
    except claude_lauf.LimitErreicht:
        await msg.edit_text("Das Claude-Kontingent der Agenten ist gerade erschöpft. Bitte später nochmal.")
        return
    except Exception as f:
        log.exception("Suche anlegen fehlgeschlagen")
        await msg.edit_text(f"Das hat nicht geklappt ({type(f).__name__}). Bitte nochmal versuchen.")
        return
    finally:
        sp.lauf_zaehlen(tag(datetime.now()))
        if foto_dir:
            shutil.rmtree(foto_dir, ignore_errors=True)
    if not daten["begriffe"]:
        await msg.edit_text(f"Daraus kann ich keine Suche machen: {daten['beschreibung']}")
        return
    sp.entwuerfe_verwerfen(chat)
    sid = sp.suche_anlegen(chat, daten)
    vorschlag = f"{daten['max_preis']:g} €" if daten["max_preis"] else "80 €"
    await msg.edit_text(
        f"{suche_text(sp.suche(sid))}\n{e(daten['beschreibung'])}\n\n"
        f"Preisgrenze und Ort? z. B. <code>{vorschlag} 30 km 34128</code>, "
        f"<code>{vorschlag}</code> für ganz Deutschland oder <code>egal</code>.",
        parse_mode=ParseMode.HTML)
    log.info("Suche %s angelegt (Entwurf) für Chat %s: %s", sid, chat, daten["titel"])


async def details_setzen(update: Update, ctx: ContextTypes.DEFAULT_TYPE, entwurf: dict, text: str) -> None:
    d = eingabe.details_lesen(text)
    max_preis = d.max_preis if d.max_preis is not None else (None if "egal" in text.lower()
                                                             else entwurf["max_preis"])
    ort_id, umkreis = None, None
    if d.plz:
        try:
            ort_id = await abruf.ort_id(d.plz)
        except AbrufFehler as f:
            log.warning("Ortssuche %s: %s", d.plz, f)
        if not ort_id:
            await update.message.reply_text(f"Die PLZ {d.plz} finde ich bei Kleinanzeigen nicht. Bitte nochmal.")
            return
        umkreis = eingabe.umkreis_runden(d.umkreis_km or STANDARD_UMKREIS)
    sp.suche_aendern(entwurf["id"], max_preis=max_preis, plz=d.plz, ort_id=ort_id, umkreis_km=umkreis,
                     status="aktiv")
    suche = sp.suche(entwurf["id"])
    await update.message.reply_html(
        f"{suche_text(suche)}\n\nDie aktuellen Anzeigen schaue ich mir gleich an, danach prüfe ich alle "
        f"{E.takt_min} Minuten auf Neues und melde gute Angebote sofort.")
    ctx.application.create_task(durchgang(ctx.application, suche, zeitgesteuert=False))


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not erlaubt(update):
        return
    text = (update.message.text or "").strip()
    entwurf = sp.entwurf(update.effective_chat.id)
    if entwurf and eingabe.ist_details(text):
        await details_setzen(update, ctx, entwurf, text)
    elif len(text) < 3:
        await update.message.reply_html(HILFE)
    else:
        await neue_suche(update, text, None)


async def on_foto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not erlaubt(update):
        return
    ordner = FOTO_DIR / uuid.uuid4().hex
    ordner.mkdir(parents=True)
    datei = await update.message.photo[-1].get_file()
    await datei.download_to_drive(ordner / "foto.jpg")
    await neue_suche(update, (update.message.caption or "").strip(), ordner)


# ---------- Suchen verwalten ----------

def _knoepfe(s: dict) -> InlineKeyboardMarkup:
    umschalten = (InlineKeyboardButton("Fortsetzen", callback_data=f"f:{s['id']}") if s["status"] == "pause"
                  else InlineKeyboardButton("Pausieren", callback_data=f"p:{s['id']}"))
    return InlineKeyboardMarkup([[umschalten, InlineKeyboardButton("Löschen", callback_data=f"l:{s['id']}")]])


async def suchen_zeigen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not erlaubt(update):
        return
    liste = sp.suchen(update.effective_chat.id)
    if not liste:
        await update.message.reply_text("Keine Suchen. Schreib einfach, was du suchst, oder schick ein Foto.")
        return
    for s in liste:
        await update.message.reply_html(suche_text(s), reply_markup=_knoepfe(s))


async def on_knopf(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not erlaubt(update):
        await q.answer()
        return
    art, _, sid = (q.data or "").partition(":")
    s = sp.suche(int(sid), chat_id=update.effective_chat.id) if sid.isdigit() else None
    if s is None:
        await q.answer("Diese Suche gibt es nicht mehr.")
        return
    if art == "l":
        sp.suche_loeschen(s["id"])
        await q.answer("Gelöscht")
        await q.edit_message_text(f"Suche #{s['id']} {s['titel']} gelöscht.")
        return
    if art in ("p", "f") and s["status"] != "entwurf":
        sp.suche_aendern(s["id"], status="pause" if art == "p" else "aktiv")
        s = sp.suche(s["id"])
        await q.answer("Pausiert" if art == "p" else "Läuft wieder")
        await q.edit_message_text(suche_text(s), parse_mode=ParseMode.HTML, reply_markup=_knoepfe(s))
        return
    await q.answer()


# ---------- Prüfen ----------

async def _allen_melden(app: Application, text: str) -> None:
    for chat in E.erlaubt:
        try:
            await app.bot.send_message(chat, text)
        except TelegramError as f:
            log.warning("Meldung an %s ging nicht: %s", chat, f)


async def _stoerung(app: Application, art: str, text: str | None) -> None:
    """Störung (Abruf oder Claude) einmal melden, Ende der Störung auch einmal. text None = alles gut."""
    schluessel = f"stoerung_{art}"
    war = sp.wert(schluessel) == "1"
    if text and not war:
        sp.wert_setzen(schluessel, "1")
        await _allen_melden(app, f"Störung: {text}\nIch versuche es weiter und melde mich, wenn es wieder geht.")
    elif not text and war:
        sp.wert_setzen(schluessel, "0")
        await _allen_melden(app, "Die Störung ist vorbei, die Suchen laufen wieder.")


def _pruefen_im_thread(suche: dict, anzeigen: list, frei: bool, heute: str,
                       zeitgesteuert: bool = True) -> pruefung.Ergebnis:
    """Eigene DB-Verbindung im Thread (sqlite-Verbindungen nicht über Threads teilen)."""
    eigener = Speicher(DB_PFAD)

    def claude(prompt: str) -> str:
        text = claude_text(prompt, zeitgesteuert=zeitgesteuert)
        eigener.lauf_zaehlen(heute)  # erst nach dem Lauf: ausgelassene Läufe (Stufe sparen) zählen nicht
        return text
    try:
        return pruefung.suche_pruefen(eigener, suche, anzeigen, claude, frei, E.schwelle)
    finally:
        eigener.con.close()


async def _ohne_claude(app: Application, suche: dict, anzeigen: list, heute: str,
                       grund: Exception) -> pruefung.Ergebnis:
    """Claude pausiert (Kontingent der Agenten): nur klare Schnäppchen ohne Bewertung melden."""
    log.warning("Suche %s ohne Claude: %s", suche["id"], grund)
    if sp.wert(f"kontingent_{heute}") is None:
        sp.wert_setzen(f"kontingent_{heute}", "1")
        await _allen_melden(app, "Claude ist gerade pausiert (Kontingent der Agenten). Bis dahin melde ich nur "
                                 "Anzeigen klar unter dem üblichen Preis, ohne Bewertung.")
    return await asyncio.to_thread(_pruefen_im_thread, suche, anzeigen, False, heute)


async def durchgang(app: Application, suche: dict, zeitgesteuert: bool = True) -> None:
    """Eine Suche einmal prüfen: abrufen, vorfiltern, bewerten, melden.
    zeitgesteuert=False: erster Durchgang direkt nach dem Anlegen (Auftrag des Nutzers, Stufe sparen lässt
    ihn nicht aus)."""
    async with _durchgang:
        suche = sp.suche(suche["id"])
        if suche is None or suche["status"] != "aktiv":
            return
        listen = []
        for begriff in suche["begriffe"]:
            url = seite.such_url(begriff, suche["max_preis"], suche["ort_id"], suche["plz"], suche["umkreis_km"])
            try:
                listen.append(seite.anzeigen_lesen(await abruf.seite(url)))
            except (AbrufFehler, seite.SeitenFehler) as f:
                log.error("Abruf Suche %s (%s): %s", suche["id"], url, f)
                await _stoerung(app, "abruf", f"Kleinanzeigen ist gerade nicht abrufbar ({f}).")
                return
        await _stoerung(app, "abruf", None)
        heute = tag(datetime.now())
        frei = sp.laeufe(heute) < E.tagesgrenze
        if not frei and sp.grenze_erstmals(heute):
            await _allen_melden(app, f"Tagesgrenze von {E.tagesgrenze} Claude-Läufen erreicht. Bis Mitternacht melde "
                                     "ich nur noch Anzeigen klar unter dem üblichen Preis, ohne Bewertung.")
        anzeigen = pruefung.zusammenfuehren(listen)
        try:
            erg = await asyncio.to_thread(_pruefen_im_thread, suche, anzeigen, frei, heute, zeitgesteuert)
        except claude_lauf.Pausiert as f:
            if "sparen" in str(f):
                # Kontingent knapp: dieser Lauf entfällt, die Kandidaten bleiben offen für den nächsten Takt
                log.info("Suche %s: %s", suche["id"], f)
                return
            erg = await _ohne_claude(app, suche, anzeigen, heute, f)
        except claude_lauf.LimitErreicht as f:
            erg = await _ohne_claude(app, suche, anzeigen, heute, f)
        except Exception as f:
            log.exception("Bewertung Suche %s fehlgeschlagen", suche["id"])
            await _stoerung(app, "claude", f"Die Bewertung durch Claude klappt nicht ({type(f).__name__}).")
            return
        if erg.claude:
            await _stoerung(app, "claude", None)
        sp.suche_aendern(suche["id"], letzter_lauf=datetime.now().timestamp())
        log.info("Suche %s: %d Kandidaten, %d Treffer%s", suche["id"], erg.kandidaten, len(erg.meldungen),
                 " (ohne Claude)" if erg.notfall else "")
        for text in erg.meldungen:
            try:
                await app.bot.send_message(suche["chat_id"], text, parse_mode=ParseMode.HTML)
            except TelegramError as f:
                log.error("Treffer an %s ging nicht: %s", suche["chat_id"], f)


async def takt(ctx: ContextTypes.DEFAULT_TYPE):
    if ist_nacht(datetime.now(), *E.nacht):
        return
    for s in sp.suchen(status="aktiv"):
        if s["chat_id"] in E.erlaubt:  # Freischaltung entzogen: Suche ruht
            await durchgang(ctx.application, s)


async def aufraeumen(ctx: ContextTypes.DEFAULT_TYPE):
    sp.gesehen_aufraeumen()


# ---------- Start ----------

async def _beim_start(app: Application) -> None:
    global abruf
    abruf = Abruf()


async def _beim_ende(app: Application) -> None:
    if abruf:
        await abruf.schliessen()


async def _fehler(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Fehler im Bot: %s", ctx.error, exc_info=ctx.error)


def main() -> int:
    if not E.token:
        log.error("TELEGRAM_BOT_TOKEN fehlt in %s/.env, Bot startet nicht", HIER)
        return 0  # kein Fehler für systemd: erst Token eintragen, dann Dienst starten
    if not E.erlaubt:
        log.warning("ERLAUBTE_CHAT_IDS ist leer: der Bot nennt nur Chat-IDs und tut sonst nichts")
    app = (Application.builder().token(E.token).post_init(_beim_start).post_shutdown(_beim_ende).build())
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hilfe", hilfe))
    app.add_handler(CommandHandler("suchen", suchen_zeigen))
    app.add_handler(CallbackQueryHandler(on_knopf))
    app.add_handler(MessageHandler(filters.PHOTO, on_foto))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(_fehler)
    app.job_queue.run_repeating(takt, interval=E.takt_min * 60, first=20)
    app.job_queue.run_repeating(aufraeumen, interval=86400, first=3600)
    log.info("Bot startet: Takt %d min, Tagesgrenze %d, Nachtruhe %s, %d Nutzer",
             E.takt_min, E.tagesgrenze, E.nacht, len(E.erlaubt))
    app.run_polling(allowed_updates=Update.ALL_TYPES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
