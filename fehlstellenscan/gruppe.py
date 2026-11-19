"""Gruppen-Bot „Rüdiger“ (@nichtsotiefruedigerbot) für die Telegram-Gruppe des Forschungsprojekts (Jan 19.11.2026).

Dienst fehlstellenscan-gruppe.service, läuft dauerhaft (Long-Polling der Bot-API, nur Bordmittel).
- Fragen: Claude (agentkit.claude_lauf, Nur-Lesen-Lauf außerhalb des Repos) liest die Projektunterlagen
  (siehe LESE_ORDNER), sucht im Netz und antwortet als Text. Antwortet jemand auf Rüdiger, geht die Sitzung weiter.
- Mails: Claude meldet {"mail_auftrag": ...}. Python sucht Kontext im HNEE-Postfach (agentkit.mailauftrag),
  Claude schreibt den Entwurf, Python prüft ihn (agentkit.mail.pruefen) und legt ihn in Jans Freigabe. Nach der
  Freigabe sendet Python genau diesen Entwurf einmal und sagt der Gruppe das Ergebnis. „Ändern“ in der Zentrale
  kommt als Auftrag (quelle telegram-aendern) und wird hier überarbeitet.
- Unbekannte Chats und Personen bekommen keine Antwort; ihre IDs stehen im Log und in data/gruppe/unbekannt.jsonl.

Zugangsdaten in fehlstellenscan/.env: GRUPPE_BOT_TOKEN, GRUPPE_CHAT_ID, GRUPPE_NUTZER_IDS, HNEE_NUTZER,
HNEE_KENNWORT, IMAP_HOST, IMAP_PORT, MAIL_ABSENDER, MAIL_NAME.
"""

import json
import queue
import shutil
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

from agentkit import auftraege, claude_lauf, config, freigabe, imap, log, mail, mailauftrag

import gruppe_logik as gl

AGENT = "fehlstellenscan"
HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent
DATEN = HIER / "data" / "gruppe"
SPIEGEL = DATEN / "spiegel"            # Kopien von STATUS.md und Code, vor jedem Lauf neu (Code liegt sonst offen)
DATEIEN = DATEN / "dateien"            # Fotos und Dateien aus der Gruppe
STAND = DATEN / "stand.json"
VERLAUF = DATEN / "verlauf.jsonl"
UNBEKANNT = DATEN / "unbekannt.jsonl"
GESENDET_ORDNER = "Gesendete Elemente"

LESE_ORDNER = gl.lese_ordner_karte(HIER, WURZEL)
SPIEGEL_DATEIEN = ("STATUS.md", "agent.py", "datensatz.py", "auswertung.py", "gruppe_logik.py", "requirements.txt")
POSTFACH = mailauftrag.Postfach(
    agent="Assistent der Projektgruppe Fehlstellen an Holz",
    beschreibung="Jans Hochschulpostfach an der HNE Eberswalde (Outlook): Prof. Böhme, Projektpartner, Hochschule",
    eingang=("INBOX", "Archive"), gesendet=GESENDET_ORDNER, max_tage_zurueck=1100, unterschrift=None)

cfg = config.lade_config(HIER, pflicht=("GRUPPE_BOT_TOKEN",))
logger = log.hole_logger(HIER, "gruppe")
API = f"https://api.telegram.org/bot{cfg['GRUPPE_BOT_TOKEN']}/"
DATEI_API = f"https://api.telegram.org/file/bot{cfg['GRUPPE_BOT_TOKEN']}/"
_schloss = threading.Lock()  # Stand und Verlauf: Poll-Schleife und Arbeiter schreiben beide


# ---------- Telegram ----------

class TelegramFehler(Exception):
    pass


def api(methode: str, zeit_s: float = 30, **werte):
    daten = json.dumps({k: v for k, v in werte.items() if v is not None}).encode()
    anfrage = urllib.request.Request(API + methode, data=daten, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(anfrage, timeout=zeit_s) as r:
            antwort = json.load(r)
    except urllib.error.HTTPError as f:
        try:
            text = json.load(f).get("description", "")
        except (ValueError, OSError):
            text = ""
        raise TelegramFehler(f"{methode}: HTTP {f.code} {text}") from None
    except (OSError, ValueError) as f:
        raise TelegramFehler(f"{methode}: {type(f).__name__}") from None
    if not antwort.get("ok"):
        raise TelegramFehler(f"{methode}: {antwort.get('description')}")
    return antwort["result"]


def senden(chat_id: int, text: str, antwort_auf: int | None = None) -> list[int]:
    """Klartext senden (geteilt, falls zu lang). Gibt die message_ids zurück."""
    ids = []
    for i, stueck in enumerate(gl.teilen(text)):
        m = api("sendMessage", chat_id=chat_id, text=stueck, link_preview_options={"is_disabled": True},
                reply_parameters={"message_id": antwort_auf, "allow_sending_without_reply": True}
                if antwort_auf and i == 0 else None)
        ids.append(m["message_id"])
    return ids


def datei_laden(d: dict, ziel: Path) -> Path | None:
    if d.get("groesse", 0) > gl.MAX_DATEI_BYTES:
        logger.info("Datei %s zu groß (%s Byte)", d["name"], d["groesse"])
        return None
    info = api("getFile", file_id=d["file_id"])
    ziel.mkdir(parents=True, exist_ok=True)
    pfad = ziel / d["name"]
    with urllib.request.urlopen(DATEI_API + urllib.parse.quote(info["file_path"]), timeout=60) as r, \
            open(pfad, "wb") as f:
        shutil.copyfileobj(r, f)
    return pfad


class Tippen:
    """„schreibt …“ in der Gruppe, solange Claude arbeitet (Telegram zeigt es je Aufruf etwa 5 s)."""

    def __init__(self, chat_id: int):
        self.chat_id, self.stopp = chat_id, threading.Event()

    def __enter__(self):
        def schleife():
            while not self.stopp.is_set():
                try:
                    api("sendChatAction", zeit_s=10, chat_id=self.chat_id, action="typing")
                except TelegramFehler:
                    pass
                self.stopp.wait(4.5)
        threading.Thread(target=schleife, daemon=True).start()
        return self

    def __exit__(self, *_):
        self.stopp.set()


# ---------- Stand und Verlauf ----------

def stand_lesen() -> dict:
    try:
        s = json.loads(STAND.read_text())
    except (OSError, ValueError):
        s = {}
    for k, v in (("offset", 0), ("sitzungen", {}), ("mails", {}), ("gemeldet", []), ("zeiten", {})):
        s.setdefault(k, v)
    return s


def stand_schreiben(s: dict) -> None:
    DATEN.mkdir(parents=True, exist_ok=True)
    s["sitzungen"] = dict(list(s["sitzungen"].items())[-500:])
    neu = STAND.with_suffix(".neu")
    neu.write_text(json.dumps(s, ensure_ascii=False, indent=1))
    neu.replace(STAND)


def verlauf_lesen() -> list[dict]:
    try:
        zeilen = VERLAUF.read_text().splitlines()[-gl.MAX_VERLAUF:]
    except OSError:
        return []
    return [json.loads(z) for z in zeilen if z.strip()]


def verlauf_merken(name: str, frage: str, antwort: str) -> None:
    DATEN.mkdir(parents=True, exist_ok=True)
    with open(VERLAUF, "a") as f:
        f.write(json.dumps({"zeit": datetime.now().isoformat(timespec="seconds"), "name": name, "frage": frage,
                            "antwort": antwort}, ensure_ascii=False) + "\n")


def spiegel_auffrischen() -> None:
    SPIEGEL.mkdir(parents=True, exist_ok=True)
    for name in SPIEGEL_DATEIEN:
        if (HIER / name).is_file():
            shutil.copyfile(HIER / name, SPIEGEL / name)


# ---------- Claude ----------

def lese_ordner() -> list[Path]:
    return [p for p in LESE_ORDNER if p.is_dir()]


def laufen(prompt: str, art: str = "anspruchsvoll", werkzeuge=None, suchen: bool = True,
           sitzung: str | None = None) -> claude_lauf.Ergebnis:
    """claude -p nur lesend, außerhalb des Repos (keine CLAUDE.md), mit Wiederholung, falls der Agent belegt ist."""
    for _ in range(20):
        try:
            return claude_lauf.laufen(AGENT, HIER, prompt, art=art, lese_ordner=lese_ordner(), suchen=suchen,
                                      werkzeuge=werkzeuge, ohne_projekt=True, sitzung_fortsetzen=sitzung)
        except claude_lauf.LaeuftSchon:
            time.sleep(15)
    raise claude_lauf.LaeuftSchon("fehlstellenscan blieb belegt")


def frage_bearbeiten(a: gl.Anfrage) -> None:
    spiegel_auffrischen()
    pfade = []
    for d in a.dateien:
        try:
            if p := datei_laden(d, DATEIEN / str(a.nachricht_id)):
                pfade.append(str(p))
        except (TelegramFehler, OSError) as f:
            logger.warning("Datei %s nicht geladen: %s", d["name"], f)
    verlauf = verlauf_lesen()
    with _schloss:
        sitzung = stand_lesen()["sitzungen"].get(str(a.antwort_auf)) if a.antwort_auf else None
    teil = gl.prompt_frage(a, [] if sitzung else verlauf, pfade, datetime.now())
    rolle = gl.ROLLE.format(ordner=gl.ordner_text({str(p): w for p, w in LESE_ORDNER.items() if p.is_dir()}))
    prompt = teil if sitzung else rolle + "\n\n" + teil
    with Tippen(a.chat_id):
        e = laufen(prompt, sitzung=sitzung)
        if not e.ok:
            raise claude_lauf.LaufFehler(f"Lauf nicht ok: {e.text[:300]}")
        if wunsch := gl.mailauftrag_aus(e.text):
            antwort = mail_beginnen(a, wunsch, verlauf)
        else:
            antwort = gl.ohne_markdown(e.text)
    ids = senden(a.chat_id, antwort, a.nachricht_id)
    with _schloss:
        s = stand_lesen()
        for i in ids:
            if e.sitzung:
                s["sitzungen"][str(i)] = e.sitzung
        stand_schreiben(s)
    verlauf_merken(a.name, a.text, antwort)
    logger.info("Antwort an %s (%d Zeichen, %d Schritte, %.2f USD)", a.name, len(antwort), e.schritte, e.usd)


# ---------- Mails ----------

def postfach_suchen(ordner: str, **kriterien) -> list[dict]:
    return imap.suchen(cfg["IMAP_HOST"], int(cfg.get("IMAP_PORT") or 993), cfg["HNEE_NUTZER"], cfg["HNEE_KENNWORT"],
                       ordner, **kriterien)


def mail_senden(daten: dict) -> str:
    vorgaben = {"MAIL_NUTZER": cfg.get("HNEE_NUTZER"), "MAIL_KENNWORT": cfg.get("HNEE_KENNWORT"),
                "GESENDET_ORDNER": GESENDET_ORDNER}
    return mail.senden({**vorgaben, **{k: v for k, v in cfg.items() if v}}, daten)


def entwurf_einreichen(antwort: str, kontext: dict, herkunft: dict, vorgaenger: dict | None = None) -> str:
    """Claudes Antwort lesen: Entwurf in die Freigabe (gibt MAIL_BEI_JAN zurück) oder Rückfrage (Text)."""
    art, roh, original = mailauftrag.antwort_lesen(antwort, kontext)
    if art == "rueckfrage":
        return f"Für die Mail fehlt mir noch etwas: {roh}"
    daten = mail.pruefen(roh, original)
    if vorgaenger and not original:
        for feld in ("in_reply_to", "references", "antwort_auf", "antwort_auf_von", "antwort_auf_datum"):
            if vorgaenger["daten"].get(feld):
                daten[feld] = vorgaenger["daten"][feld]
    inhalt = mail.anzeige(daten) + f"\n\n(Gewünscht von {herkunft['name']} in der Projektgruppe)"
    fid = freigabe.neuer_entwurf(AGENT, gl.entwurf_titel(daten, herkunft["name"]), inhalt, typ="mail", daten=daten,
                                 vorgaenger=vorgaenger and vorgaenger["id"])
    (DATEN / "mails").mkdir(parents=True, exist_ok=True)
    (DATEN / "mails" / f"{fid}.json").write_text(json.dumps({**herkunft, "kontext": kontext}, ensure_ascii=False))
    with _schloss:
        s = stand_lesen()
        s["mails"][fid] = herkunft
        stand_schreiben(s)
    logger.info("Mail-Entwurf %s für %s in der Freigabe", fid, herkunft["name"])
    return gl.MAIL_BEI_JAN


def mail_beginnen(a: gl.Anfrage, wunsch: str, verlauf: list[dict]) -> str:
    text = gl.mail_text(wunsch, a.name, verlauf + [{"name": a.name, "frage": a.text}])
    heute = date.today()
    e = laufen(mailauftrag.prompt_suche(text, heute, POSTFACH), art="routine", werkzeuge=[], suchen=False)
    suche = mailauftrag.suche_lesen(e.text, POSTFACH)
    kontext = mailauftrag.kontext_sammeln(suche, postfach_suchen, None, heute, POSTFACH)
    e = laufen(mailauftrag.prompt_entwurf(text, kontext, heute, POSTFACH), werkzeuge=[], suchen=False)
    herkunft = {"chat_id": a.chat_id, "nachricht_id": a.nachricht_id, "name": a.name, "text": text}
    return entwurf_einreichen(e.text, kontext, herkunft)


def aenderung_bearbeiten(auftrag: dict, alt: dict) -> None:
    gespeichert = json.loads((DATEN / "mails" / f"{alt['id']}.json").read_text())
    herkunft = {k: gespeichert[k] for k in ("chat_id", "nachricht_id", "name", "text")}
    prompt = mailauftrag.prompt_aendern(auftrag["text"], alt["daten"], herkunft["text"], gespeichert["kontext"],
                                        date.today(), POSTFACH)
    try:
        e = laufen(prompt, werkzeuge=[], suchen=False)
        ergebnis = entwurf_einreichen(e.text, gespeichert["kontext"], herkunft, vorgaenger=alt)
        if ergebnis != gl.MAIL_BEI_JAN:
            senden(herkunft["chat_id"], ergebnis, herkunft["nachricht_id"])
        auftraege.abschliessen(auftrag["id"], "Neuer Entwurf liegt in der Freigabe." if ergebnis == gl.MAIL_BEI_JAN
                               else ergebnis)
    except (claude_lauf.LaufFehler, mailauftrag.AuftragFehler, mail.MailFehler) as f:
        logger.error("Änderung %s: %s", auftrag["id"], f)
        auftraege.abschliessen(auftrag["id"], f"Überarbeitung ging nicht: {f}", status="fehlgeschlagen")


def freigaben_pruefen(q: "queue.Queue", eingereiht: set) -> None:
    """Freigegebene Gruppen-Mails senden, Ergebnisse der Gruppe melden, Änderungswünsche einreihen (der Arbeiter
    überarbeitet sie, damit die Poll-Schleife nicht wartet)."""
    with _schloss:
        s = stand_lesen()
    for e in freigabe.zur_ausfuehrung(AGENT):
        if e["id"] not in s["mails"]:
            continue  # nicht aus der Gruppe (z. B. agent.py): nicht unsere Sache
        try:
            e = freigabe.ausfuehrung_beginnen(e["id"])
        except freigabe.FreigabeFehler as f:
            logger.error("Ausführung %s: %s", e["id"], f)
            continue
        try:
            ergebnis, ok = mail_senden(e["daten"]), True
        except (mail.MailFehler, OSError) as f:
            ergebnis, ok = f"Senden fehlgeschlagen: {f}", False
        freigabe.ausfuehrung_abschliessen(e["id"], ergebnis, ok)
        logger.info("Mail %s: %s", e["id"], ergebnis)
    for e in freigabe.erledigte(AGENT):
        herkunft = s["mails"].get(e["id"])
        if not herkunft or e["id"] in s["gemeldet"] or not (text := gl.ergebnis_text(e)):
            continue
        try:
            senden(herkunft["chat_id"], text, herkunft["nachricht_id"])
        except TelegramFehler as f:
            logger.warning("Ergebnis %s nicht gemeldet: %s", e["id"], f)
            continue
        with _schloss:
            s2 = stand_lesen()
            s2["gemeldet"].append(e["id"])
            stand_schreiben(s2)
    for a in auftraege.neue(AGENT):
        if a.get("quelle") == "telegram-aendern" and a.get("bezug") in s["mails"] and a["id"] not in eingereiht:
            alt = next((e for e in freigabe.erledigte(AGENT) if e["id"] == a["bezug"]), None)
            if alt:
                eingereiht.add(a["id"])
                q.put(("aendern", a, alt))


# ---------- Schleife ----------

def arbeiter(q: "queue.Queue") -> None:
    """Nacheinander: ("frage", Anfrage) oder ("aendern", Auftrag, alter Entwurf)."""
    while True:
        art, a, *rest = q.get()
        try:
            if art == "aendern":
                aenderung_bearbeiten(a, *rest)
                continue
            frage_bearbeiten(a)
        except claude_lauf.LimitErreicht:
            if art == "frage":
                senden(a.chat_id, gl.LIMIT, a.nachricht_id)
        except Exception as f:  # noqa: BLE001 – eine Frage darf den Bot nicht beenden; Jan sieht es im Log
            if art == "aendern":
                logger.exception("Änderung %s: %s", a["id"], f)
                continue
            logger.exception("Frage von %s: %s", a.name, f)
            try:
                senden(a.chat_id, gl.FEHLER, a.nachricht_id)
            except TelegramFehler:
                pass
        finally:
            q.task_done()


def unbekannt_merken(update: dict) -> None:
    if h := gl.herkunft(update):
        logger.info("Nicht freigeschaltet: Chat %s (%s), Person %s (%s)", h["chat_id"], h["chat"], h["nutzer_id"],
                    h["name"])
        DATEN.mkdir(parents=True, exist_ok=True)
        with open(UNBEKANNT, "a") as f:
            f.write(json.dumps({"zeit": datetime.now().isoformat(timespec="seconds"), **h}, ensure_ascii=False) + "\n")


def main() -> int:
    ich = api("getMe")
    zugang = gl.zugang_aus_env(cfg, ich["id"], ich["username"])
    logger.info("Rüdiger gestartet als @%s, Gruppe %s, %d Personen", zugang.bot_name, zugang.chat_id,
                len(zugang.nutzer))
    q: queue.Queue = queue.Queue()
    threading.Thread(target=arbeiter, args=(q,), daemon=True).start()
    naechste_pruefung, eingereiht = 0.0, set()
    while True:
        with _schloss:
            offset = stand_lesen()["offset"]
        try:
            updates = api("getUpdates", zeit_s=40, offset=offset, timeout=25,
                          allowed_updates=["message", "my_chat_member"])
        except TelegramFehler as f:
            logger.warning("getUpdates: %s", f)
            time.sleep(10)
            updates = []
        for u in updates:
            a = gl.anfrage_aus(u, zugang)
            if a is None:
                if gl.herkunft(u) and (gl.herkunft(u)["chat_id"] != zugang.chat_id
                                       or gl.herkunft(u)["nutzer_id"] not in zugang.nutzer):
                    unbekannt_merken(u)
            else:
                with _schloss:
                    s = stand_lesen()
                    zeiten = s["zeiten"].setdefault(str(a.nutzer_id), [])
                    erlaubt = gl.noch_erlaubt(zeiten, datetime.now())
                    if erlaubt:
                        zeiten.append(datetime.now().isoformat(timespec="seconds"))
                        del zeiten[:-gl.MAX_JE_TAG]
                    stand_schreiben(s)
                try:
                    if not erlaubt:
                        senden(a.chat_id, gl.ZU_VIEL, a.nachricht_id)
                    else:
                        if q.unfinished_tasks:
                            senden(a.chat_id, gl.BESCHAEFTIGT, a.nachricht_id)
                        q.put(("frage", a))
                except TelegramFehler as f:
                    logger.warning("Senden: %s", f)
            with _schloss:
                s = stand_lesen()
                s["offset"] = u["update_id"] + 1
                stand_schreiben(s)
        if time.monotonic() >= naechste_pruefung:
            try:
                freigaben_pruefen(q, eingereiht)
            except Exception as f:  # noqa: BLE001 – Prüfung wiederholt sich in einer Minute
                logger.exception("Freigaben prüfen: %s", f)
            naechste_pruefung = time.monotonic() + 30


if __name__ == "__main__":
    sys.exit(main())
