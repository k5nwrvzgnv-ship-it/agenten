"""Reine Logik der Telegram-Zentrale (ohne Telegram), damit sie testbar ist."""

import json
import re
import secrets
import shutil
import unicodedata
from datetime import datetime
from html import escape, unescape
from pathlib import Path

from agentkit.entwurfsanzeige import MAX_LAENGE, anzeigename
from agentkit.entwurfsanzeige import entwurf_als_text  # noqa: F401 (die Zentrale importiert sie von hier)

# Jans Agenten mit Befehl und Knopf. Die Zentrale ersetzt die Liste beim Start durch agenten_finden():
# wer einen Ordner mit agent.py und einen Dienst hat. Diese Vorgabe gilt für Tests und als Rückhalt.
AGENTEN = ("uni", "dokumente", "posteingang", "finance")
REIHENFOLGE = ("uni", "dokumente", "posteingang", "finance")  # vorn im Menü, weitere folgen nach dem Alphabet
MAX_DATEI_BYTES = 20 * 1024 * 1024  # mehr lädt die Bot-Schnittstelle von Telegram nicht herunter
ZENTRALE = "zentrale"  # Absender für Systemnachrichten (Sprachregel, Jan 27.10.2026)
SYSTEM = ("feedback",)  # Dienste ohne eigenen Namen bei Jan: sie schreiben als Zentrale

# Schalter (Nachtauftrag 22.11.2026, docs/befund-ux.md Abschnitt 3): Jan korrigiert per Antwort auf das Ergebnis.
# Die Feedback-Knöpfe (Passt, Zu lang, Falscher Fokus, Feedback schreiben) bleiben im Code, sichtbar sind sie nur mit
# True. Alte Knöpfe in früheren Nachrichten funktionieren weiter. Lias Zentrale (portal.py) hat eigene Knöpfe.
FEEDBACK_KNOEPFE = False

# ---------- Texte für Jan (docs/sprache/sprachregel.md) ----------
# Jede Nachricht: eine Zeile Kern, höchstens drei Punkte, höchstens eine Handlung, keine Höflichkeitsformeln, keine
# Statusprosa. Geprüft über alle Snapshots (regelverstoesse, tests/test_regeln.py).
# Lernmodus (/unilern), /pc, /weiter und /verwerfen nimmt die Zentrale still weiter an, Hilfe und Menü nennen sie nicht.
OHNE_GRUND = "Den Grund kenne ich nicht. Schick den Auftrag noch einmal."
HILFE = (
    "Aufträge: /uni und Text, genauso {weitere}.\n"
    "• Text ohne Befehl: Ich frage, an wen er geht.\n"
    "• Antwort auf ein Ergebnis: Es geht im selben Gespräch weiter.\n"
    "• Dateien: mit /uni und Text als Bildunterschrift."
)
KNOPF_ALT = "Der Knopf ist veraltet."
NICHT_ANGELEGT = "Auftrag nicht angelegt. Schick ihn noch einmal."
DATEI_ZU_GROSS = "Die Datei ist zu groß für Telegram. Leg sie am PC ab."
DATEI_NICHT_GELADEN = "Die Datei kam nicht an. Schick sie noch einmal."
TEXT_WEG = "Der Text ist weg. Schick ihn noch einmal."
AN_WEN = "An wen geht das?"
UNBEKANNT = "Diesen Befehl kenne ich nicht. /hilfe zeigt alle."
NOTIERT = "Notiert."  # nach Feedback über alte Knöpfe (statt „Danke“)


def agenten_finden(wurzel: Path, unit_dir: Path) -> tuple[str, ...]:
    """Jans Agenten aus dem, was da ist: Ordner im Hauptordner mit agent.py, zu dem <name>.service eingerichtet ist.
    Ein neuer Agent bekommt so Befehl und Knopf, sobald sein Dienst steht; ein geplanter ohne Dienst taucht nicht auf."""
    namen = [p.name for p in sorted(Path(wurzel).iterdir())
             if re.fullmatch(r"[a-z]+", p.name) and (p / "agent.py").is_file()
             and (Path(unit_dir) / f"{p.name}.service").exists()]
    return tuple(sorted(namen, key=lambda n: (REIHENFOLGE.index(n) if n in REIHENFOLGE else len(REIHENFOLGE), n)))


def agenten_setzen(agenten) -> tuple[str, ...]:
    """Liste für befehl_auswerten und panel_auswerten setzen (leer: Vorgabe bleibt). Gibt die geltende Liste zurück."""
    global AGENTEN
    if agenten:
        AGENTEN = tuple(agenten)
    return AGENTEN


def ist_netzfehler(fehler: BaseException | None) -> bool:
    """Netzfehler von Telegram (NetworkError samt TimedOut, Bad Gateway) und httpx: Die Bibliothek wiederholt
    selbst, im Log reicht eine Zeile. Am Klassennamen erkannt, damit die Logik ohne Telegram testbar bleibt."""
    namen = {k.__name__ for k in type(fehler).__mro__}
    return bool(namen & {"NetworkError", "TransportError"})


def hilfe_text(agenten) -> str:
    weitere = [f"/{a}" for a in agenten if a != "uni"]
    return HILFE.format(weitere=", ".join(weitere) or "die anderen Agenten")


def mehrzahl(n: int, eins: str, viele: str) -> str:
    return f"{n} {eins if n == 1 else viele}"


def status_text(zahlen: dict[str, int]) -> str:
    """Überblick für /status in einer Zeile, nur was nicht null ist.
    zahlen: offen, ausfuehrung, unklar, auftraege, am_pc, dateien."""
    teile = [mehrzahl(zahlen["offen"], "Entwurf", "Entwürfe"),
             f"{zahlen['ausfuehrung']} freigegeben, noch nicht ausgeführt" if zahlen["ausfuehrung"] else "",
             f"{zahlen['unklar']} unklar, ob ausgeführt" if zahlen["unklar"] else "",
             mehrzahl(zahlen["auftraege"], "Auftrag", "Aufträge") + " in Arbeit",
             mehrzahl(zahlen["am_pc"], "Gespräch", "Gespräche") + " am PC",
             mehrzahl(zahlen["dateien"], "Datei wartet", "Dateien warten")]
    teile = [t for t in teile if t and not t.startswith("0 ")]
    return "Offen: " + ", ".join(teile) + "." if teile else "Nichts offen."


def home_zeilen(stufe: str, wartend: int) -> list[str]:
    """Kurzstand oben im Menü, nur wenn etwas zu tun ist (Entwürfe zeigt der Knopf)."""
    zeilen = []
    if stufe == "limit":
        zeilen.append(STUFEN_TEXT[stufe])
    if wartend:
        zeilen.append(f"{mehrzahl(wartend, 'Datei wartet', 'Dateien warten')} auf einen Auftrag.")
    return zeilen


def freigabe_antwort(entscheidung: str, agent: str) -> str:
    if entscheidung == "freigegeben":
        return "Freigegeben."
    if entscheidung == "abgelehnt":
        return "Abgelehnt."
    return "Was soll anders werden?"


def freigabe_fehler(grund: str, abgelaufen: bool = False) -> str:
    """Antwort auf einen Knopf, der nicht mehr geht (Grund aus agentkit.freigabe, steht nur im Log)."""
    if "weicht von der Anzeige ab" in grund:
        return "Der Entwurf hat sich nach der Anzeige geändert, nichts freigegeben. Die neue Fassung steht im Menü."
    if "nicht (mehr) offen" in grund:
        if abgelaufen:
            return "Der Entwurf ist abgelaufen, nichts ausgeführt."
        return "Über diesen Entwurf ist schon entschieden."
    return "Das ging nicht. Einzelheiten am PC."


def tage_text(stunden: float) -> str:
    tage = int(stunden // 24)
    return "seit heute" if tage < 1 else "seit gestern" if tage == 1 else f"seit {tage} Tagen"


def verfall_text(abgelaufene: list[dict], tage: int) -> str:
    """Kurze Meldung, wenn Entwürfe abgelaufen sind (ohne Inhalt, nur Titel)."""
    if len(abgelaufene) == 1:
        e = abgelaufene[0]
        return f"Entwurf nach {tage} Tagen abgelaufen, nichts ausgeführt: {e['titel']} ({anzeigename(e['agent'])})."
    return "\n".join([f"{len(abgelaufene)} Entwürfe nach {tage} Tagen abgelaufen, nichts ausgeführt:",
                      *[f"• {e['titel']} ({anzeigename(e['agent'])})" for e in abgelaufene]])


ERINNERUNG_AB_UHR = 9  # nicht nachts
ERINNERUNG_AB_STUNDEN = 24


def erinnerung_text(alter: list[float], jetzt: datetime, zuletzt: str, verfall_tage: int) -> str | None:
    """Einmal am Tag eine Zeile, wenn Entwürfe länger als einen Tag offen sind. alter: Stunden je offenem Entwurf,
    zuletzt: Tag der letzten Erinnerung (JJJJ-MM-TT oder ""). None: heute nichts (mehr) zu sagen."""
    alt = [a for a in alter if a >= ERINNERUNG_AB_STUNDEN]
    if not alt or jetzt.hour < ERINNERUNG_AB_UHR or zuletzt == jetzt.date().isoformat():
        return None
    rest = max(0, int((verfall_tage * 24 - max(alt)) // 24))
    wann = "heute" if rest < 1 else "morgen" if rest == 1 else f"in {rest} Tagen"
    if len(alt) == 1:
        return f"1 Entwurf wartet {tage_text(alt[0])}, er läuft {wann} ab."
    return f"{len(alt)} Entwürfe warten, der älteste läuft {wann} ab."


ERINNERUNG_KNOEPFE = [[("Entwürfe ansehen", "u:entwuerfe")]]


def aenderung_weiter(agent: str, dateien: int) -> str:
    mit = f" (mit {anzahl_dateien(dateien)})" if dateien else ""
    return f"{anzeigename(agent)} überarbeitet den Entwurf{mit}."


def unklar_text(titel: str) -> str:
    return (f"Unklar, ob das geklappt hat: {titel}\n"
            "Angefangen, aber kein Ende gemeldet. Ich wiederhole es nicht. Prüf, ob es angekommen ist.")


def datei_nicht_gesendet(datei: str) -> str:
    name = Path(datei).stem.replace("_", " ")
    return f"„{name}“ kam nicht an. Die Datei liegt am PC."


def dateien_warten(anzahl: int, beispiel: str, befehl_unbekannt: bool) -> str:
    vorweg = "Den Befehl kenne ich nicht. " if befehl_unbekannt else ""
    liegt = "liegt" if anzahl == 1 else "liegen"
    return f"{vorweg}{anzahl_dateien(anzahl)} {liegt} bereit. Schick den Auftrag dazu, zum Beispiel {beispiel}."


def dateien_verworfen(anzahl: int) -> str:
    return f"{anzahl_dateien(anzahl)} gelöscht." if anzahl else "Es warten keine Dateien."


def befehl_auswerten(text: str) -> tuple[str, str, str] | None:
    """'/uni Kapitel 3' -> ('uni', 'erledigen', 'Kapitel 3'), '/unilern ...' -> lernen.

    Gibt None zurück, wenn der Befehl keinem Agenten gehört.
    """
    kopf, _, rest = text.strip().partition(" ")
    befehl = kopf.lstrip("/").split("@", 1)[0].lower()
    modus = "erledigen"
    if befehl.endswith("lern"):
        befehl, modus = befehl[: -len("lern")], "lernen"
    if befehl not in AGENTEN:
        return None
    return befehl, modus, rest.strip()


def aufteilen(text: str, max_laenge: int = MAX_LAENGE) -> list[str]:
    """Klartext an Zeilenenden aufteilen (für HTML: html_aufteilen)."""
    stuecke = []
    while len(text) > max_laenge:
        schnitt = text.rfind("\n", 0, max_laenge)
        if schnitt <= 0:
            schnitt = max_laenge
        stuecke.append(text[:schnitt])
        text = text[schnitt:].lstrip("\n")
    stuecke.append(text)
    return stuecke



def nur_freigabe_verweis(auftrag: dict) -> bool:
    """Ergebnis sagt nur „Entwurf … liegt zur Freigabe“ (Jan, 28.10.2026: dann keine eigene Nachricht, der Entwurf
    kommt mit Freigeben/Ändern/Ablehnen). daten.nur_freigabe = True setzt ein Agent ausdrücklich."""
    if auftrag.get("status") != "erledigt" or auftrag.get("ergebnis_dateien"):
        return False
    if (auftrag.get("daten") or {}).get("nur_freigabe"):
        return True
    zeilen = [z for z in (auftrag.get("ergebnis") or "").splitlines() if z.strip()]
    return bool(zeilen) and all(re.fullmatch(r"(Mail-)?Entwurf an \S.* liegt zur Freigabe([.:].*)?", z.strip())
                                for z in zeilen)


STUFEN_TEXT = {  # „limit“ steht auch im Menü
    "normal": "Die Rechenzeit reicht.",
    "sparen": "Die Rechenzeit wird knapp, darum spare ich.",
    "nur_auftraege": "Die Rechenzeit ist fast aufgebraucht. Nur deine Aufträge laufen.",
    "limit": "Die Rechenzeit ist aufgebraucht. Alles wartet.",
}


def usd_text(wert: float) -> str:
    return f"{wert:.2f}".replace(".", ",") + " USD"


def woche_zeilen(woche: dict[str, dict]) -> list[str]:
    """Letzte 7 Tage in einer Zeile, teuerster zuerst. USD ist ein Vergleichswert (bezahlt ist pauschal)."""
    if not woche:
        return []
    je = [f"{anzeigename(a)} {usd_text(s['usd'])}"
          for a, s in sorted(woche.items(), key=lambda x: (-x[1]["usd"], x[0]))]
    return [f"7 Tage: {usd_text(sum(s['usd'] for s in woche.values()))} Vergleichswert ({', '.join(je)})"]


def verbrauch_text(stand: dict | None, stufe: str, heute: dict[str, dict], zeit_text,
                   woche: dict[str, dict] | None = None) -> str:
    """Verbrauch in wenigen Zeilen: Stufe, Anteil mit Freigabezeit, heute je Agent, Woche."""
    zeilen = [STUFEN_TEXT[stufe]]
    if stand is not None:
        zeilen.append(f"Verbraucht: {stand.get('5h', 0) * 100:.0f} % in 5 Stunden (frei {zeit_text(stand.get('reset_5h'))}), "
                      f"{stand.get('7d', 0) * 100:.0f} % in 7 Tagen (frei {zeit_text(stand.get('reset_7d'))})")
    if heute:
        je = []
        for agent, s in sorted(heute.items(), key=lambda x: anzeigename(x[0])):
            fehler = f", {s['fehler']}-mal nicht geklappt" if s["fehler"] else ""
            je.append(f"{anzeigename(agent)} {s['laeufe']}-mal{fehler}")
        zeilen.append("Heute: " + "; ".join(je))
    return "\n".join(zeilen + woche_zeilen(woche or {}))


MELDUNG = "m:"  # Vorsatz für Meldungen in Gemeldet.nachrichten und in Knopf-Daten
ENTWURF = "e:"  # Vorsatz für Entwürfe in Gemeldet.nachrichten (Antwort auf einen Entwurf = Ändern)


def absender_aus_text(text: str | None, agenten) -> str | None:
    """Agent, von dem eine Bot-Nachricht stammt, aus ihrer ersten Zeile („Uni“, „Uni · Mail-Entwurf“,
    „Uni ist dran.“). So geht eine Antwort auf jede Nachricht eines Agenten an ihn, ohne Rückfrage (Jan 26.11.2026)."""
    erste = (text or "").strip().split("\n", 1)[0].strip()
    kopf = erste.split(" · ", 1)[0].strip()
    for a in agenten:
        name = anzeigename(a)
        if kopf == name or erste.startswith(f"{name} ist dran"):
            return a
    return None


def meldung_knoepfe(meldung: dict) -> list[list[tuple[str, str]]]:
    """Knöpfe einer Meldung als (Beschriftung, Knopf-Daten). Daten: m:<id>:<zeile>:<spalte>
    (Telegram erlaubt höchstens 64 Bytes, die Beschriftung selbst wäre zu lang)."""
    return [[(text, f"{MELDUNG}{meldung['id']}:{z}:{s}") for s, text in enumerate(zeile)]
            for z, zeile in enumerate(meldung.get("knoepfe") or [])]


def knopf_auswerten(daten: str) -> tuple[str, int, int] | None:
    """'m:<id>:1:0' -> (id, 1, 0), sonst None."""
    m = re.fullmatch(rf"{MELDUNG}([\w-]+):(\d+):(\d+)", daten)
    return (m.group(1), int(m.group(2)), int(m.group(3))) if m else None


def knopf_beschriftung(meldung: dict, zeile: int, spalte: int) -> str | None:
    knoepfe = meldung.get("knoepfe") or []
    if zeile < len(knoepfe) and spalte < len(knoepfe[zeile]):
        return knoepfe[zeile][spalte]
    return None




# ---------- Signal-Filter (docs/befund-ux.md, Entscheidung 5) ----------
# Für Meldungen der Agenten und Ergebnisse ohne Vorlage: Rauschen raus, sichtbar Kopfzeile und höchstens PUNKTE_MAX
# Punkte, der Rest zugeklappt als <blockquote expandable> darunter (nichts geht verloren). Entwürfe zur Freigabe
# laufen nie hier durch (entwurf_als_text, freigegeben wird genau der gezeigte Text).

PUNKTE_MAX = 3
SICHTBAR_MAX = 600  # Zeichen für Kopfzeile und Punkte (Sprachregel Jan: höchstens 800 ohne aufklappbaren Teil)
KOPF_MAX = 100  # eine Zeile Kern; ist sie länger, bleibt nur ihr erster Satz sichtbar
PUNKT_MAX = 300
NACHRICHT_MAX = 3800  # Telegram erlaubt 4096, Rest Luft für Formatierung
_ZUGEKLAPPT = ("<blockquote expandable>", "</blockquote>")
_STATUSWORT = r"(?:neue? )?(?:geprüft|vorgefiltert|neu|neue|gelesen|übersprungen|gefunden)"
ZAEHLER = re.compile(rf"\s*\(\d+ {_STATUSWORT}(?:, \d+ {_STATUSWORT})*\)")
PRAEFIX = re.compile(r"^(?:\[[a-z_]+\]\s*|Lia, Agent [a-z]+:\s*|Agent [a-z]+:\s*|Fehler im Agenten \(\w+\):\s*)+")
_PFAD = r"(?:~|/home|/opt|/tmp|/var|/srv|/etc|/usr|/root)/\S*"
PFAD_ZEILE = re.compile(rf"\s*\b(?:Datei|Pfad|Details|Log|Ordner|Text):\s*(?:{_PFAD}.*|\S+\.log)$")
PFAD = re.compile(rf"(?<![\w:/]){_PFAD}")
STERNE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
AUFZAEHLUNG = re.compile(r"^[-*]\s+")
UEBERSCHRIFT = re.compile(r"^#{1,6}\s+")


def signal_zeile(zeile: str, erste: bool = False) -> str:
    """Eine Zeile entrauschen: Technikpräfix (nur erste Zeile), Zählerklammern, Markdown, absolute Pfade."""
    if erste:
        zeile = PRAEFIX.sub("", zeile)
    einzug = zeile[: len(zeile) - len(zeile.lstrip())]
    zeile = zeile.strip()
    zeile = UEBERSCHRIFT.sub("", zeile)
    zeile = AUFZAEHLUNG.sub("• ", zeile)
    zeile = STERNE.sub(lambda m: m.group(1) or m.group(2), zeile)
    zeile = ZAEHLER.sub("", zeile)
    ohne_pfad = PFAD.sub("", PFAD_ZEILE.sub("", zeile))
    if ohne_pfad != zeile and re.fullmatch(r"[•\s]*[\w ]{1,20}:?\s*", ohne_pfad):  # nur noch ein Etikett („Datei:“)
        return ""
    zeile = re.sub(r"\s+([:.,])", r"\1", re.sub(r"[ \t]{2,}", " ", ohne_pfad)).strip()
    return einzug + zeile if zeile else ""


def _kopf_teilen(kopf: str) -> tuple[str, str]:
    """Zu lange Kopfzeile am Satzende teilen: (sichtbar, Rest für den zugeklappten Teil)."""
    if len(kopf) <= KOPF_MAX:
        return kopf, ""
    sichtbar = re.split(r"(?<=[.!?])\s+", kopf)[0]  # zu lang: nur der erste Satz bleibt sichtbar
    if len(sichtbar) > PUNKT_MAX:  # ein einziger langer Satz: am Wortende kürzen
        sichtbar = kopf[: PUNKT_MAX - 1].rsplit(" ", 1)[0] + " …"
        return sichtbar, "… " + kopf[len(sichtbar) - 2:].lstrip()
    return sichtbar, kopf[len(sichtbar):].strip()


def signal_teile(text: str) -> tuple[str, list[str], str]:
    """Text eines Agenten -> (Kopfzeile, sichtbare Punkte, zugeklappter Rest), alles Klartext."""
    roh = [z.rstrip() for z in (text or "").strip().splitlines()]
    zeilen, erste = [], True
    for z in roh:
        if not z.strip():
            zeilen.append("")
            continue
        sauber = signal_zeile(z, erste)
        erste = False
        if sauber:
            zeilen.append(sauber)
    while zeilen and not zeilen[0]:
        zeilen.pop(0)
    if not zeilen:
        return "", [], ""
    kopf, kopf_rest = _kopf_teilen(zeilen[0].strip())
    # Rest einer langen Kopfzeile ist Einzelheit (oft Zählerprosa): zugeklappt, danach keine sichtbaren Punkte
    rest = ([kopf_rest] if kopf_rest else []) + zeilen[1:]
    punkte, laenge, i = [], len(kopf), 0
    while not kopf_rest and i < len(rest) and len(punkte) < PUNKTE_MAX:
        z = rest[i]
        if not z:
            i += 1
            continue
        if z[0].isspace() or len(z) > PUNKT_MAX or laenge + len(z) > SICHTBAR_MAX:
            break
        punkte.append(z)
        laenge += len(z)
        i += 1
    return kopf, punkte, re.sub(r"\n{3,}", "\n\n", "\n".join(rest[i:])).strip("\n")


def _zugeklappt_stuecke(rest: str, erster_platz: int) -> list[str]:
    """Zugeklappten Teil in Blöcke teilen: der erste passt in erster_platz, weitere je in eine eigene Nachricht.
    Gezählt wird wie bei Telegram ohne Formatierung (&amp; zählt als ein Zeichen)."""
    stuecke, platz = [], erster_platz
    while rest:
        luft = platz - 20
        if luft < 200:  # kein Platz mehr in dieser Nachricht
            stuecke.append("")
            platz = NACHRICHT_MAX
            continue
        teil = aufteilen(rest, luft)[0] if len(rest) > luft else rest
        stuecke.append(_ZUGEKLAPPT[0] + escape(teil, False) + _ZUGEKLAPPT[1])
        rest = rest[len(teil):].lstrip("\n")
        platz = NACHRICHT_MAX
    return stuecke


def signal_html(kopfzeile: str, text: str) -> list[str]:
    """Signal-Filter: kopfzeile (fertiges HTML, z. B. <b>Uni</b>) plus Kern, Punkte und zugeklappter Rest.
    Mehr als eine Nachricht nur, wenn der zugeklappte Teil nicht in eine passt; dann folgen weitere Blöcke."""
    kopf, punkte, rest = signal_teile(text)
    sichtbar = "\n".join(escape(z, False) for z in [kopf, *punkte] if z)
    erste = f"{kopfzeile}\n{sichtbar}".rstrip()
    if not rest:
        return [erste]
    bloecke = _zugeklappt_stuecke(rest, NACHRICHT_MAX - len(sichtbarer_teil(erste)) - 1)
    if bloecke and bloecke[0]:
        return [f"{erste}\n{bloecke[0]}", *bloecke[1:]]
    return [erste, *[b for b in bloecke if b]]


def mit_absender(agent: str, text: str, zusatz: str = "") -> list[str]:
    """Nachricht(en) im HTML-Format: Agent fett in der ersten Zeile, darunter der Text durch den Signal-Filter.

    Technisches (IDs, Pfade, Auftragstext) gehört nicht hierher, sondern ins Log.
    """
    agent = ZENTRALE if agent in SYSTEM else agent
    kopf = f"<b>{escape(anzeigename(agent), False)}</b>" + (f" · {escape(zusatz, False)}" if zusatz else "")
    return signal_html(kopf, text)


PRUEFEN_JAN = "Prüfen: "  # Lia: „Bitte prüfen: “ (vorlagen.ergebnis_html)


def auftrag_nachricht(auftrag: dict) -> list[str]:
    """Ergebnis eines abgeschlossenen Auftrags für Jan: nur Absender und Ergebnis des Agenten."""
    if auftrag["status"] == "erledigt":
        if (auftrag.get("daten") or {}).get("kern"):  # strukturiertes Ergebnis: Vorlage, Kern zuerst
            import vorlagen
            return vorlagen.ergebnis_html(mit_absender(auftrag["agent"], "")[0], auftrag, aufteilen,
                                          pruefen_vorsatz=PRUEFEN_JAN)
        return mit_absender(auftrag["agent"], auftrag.get("ergebnis") or "Erledigt.")
    return mit_absender(auftrag["agent"], auftrag.get("ergebnis") or OHNE_GRUND, "hat nicht geklappt")


def ergebnis_knoepfe(auftrag: dict, feedback: str = "feedback") -> list | None:
    """Feedback-Knöpfe unter einem Ergebnis (nur mit Schalter FEEDBACK_KNOEPFE; nicht unter Fehlern, nicht beim
    Feedback-Dienst, nicht wenn der Agent sie abgewählt hat). None: keine Knöpfe, Antwort genügt."""
    import vorlagen
    if not FEEDBACK_KNOEPFE or auftrag["status"] != "erledigt" or auftrag["agent"] == feedback \
            or vorlagen.ohne_feedback_knoepfe(auftrag):
        return None
    return vorlagen.feedback_knoepfe("", auftrag["id"])


def weitergabe_beachten(auftrag: dict) -> bool:
    """Auftrag von Agent an Agent, um den sich die Zentrale kümmert (melden, Empfänger starten). Stille Weitergaben
    (still=True, z. B. lia/schnell nach einer kleinen Änderung) startet der Absender selbst."""
    return bool(auftrag.get("von")) and not auftrag.get("still")


def weitergabe_text(auftrag: dict, dienst_da: bool) -> list[str] | None:
    """Info an Jan zu einem Auftrag von Agent an Agent: nur wenn er liegen bleibt, sonst None."""
    if dienst_da:
        return None
    an = anzeigename(auftrag["agent"])
    return mit_absender(ZENTRALE, f"{anzeigename(auftrag['von'])} hat für {an} einen Auftrag.\n{an} ist noch "
                                  "nicht eingerichtet, der Auftrag wartet so lange.")


def stufe_text(alt: str, neu: str, stand: dict | None, zeit_text) -> list[str] | None:
    """Stufenwechsel nur melden, wenn Jan es merkt: Rechenzeit aufgebraucht und wieder frei."""
    if neu == "limit" and alt != "limit":
        bis = (stand or {}).get("reset_status")
        return mit_absender(ZENTRALE, "Rechenzeit aufgebraucht. Aufträge warten"
                            + (f" bis {zeit_text(bis)}." if bis else ", bis wieder Rechenzeit frei ist."))
    if alt == "limit" and neu != "limit":
        return mit_absender(ZENTRALE, "Rechenzeit wieder frei.")
    return None


def anzahl_dateien(n: int) -> str:
    return "1 Datei" if n == 1 else f"{n} Dateien"


def bestaetigung(agent: str, modus: str, dateinamen: list[str]) -> str:
    """Kurze Rückmeldung nach einem Auftrag: 'Uni ist dran.'"""
    text = f"{anzeigename(agent)} ist dran" + (" (lernen)" if modus == "lernen" else "")
    if dateinamen:
        text += f", mit {anzahl_dateien(len(dateinamen))}"
    return text + "."


BESCHRIFTUNG_MAX = 1024  # Telegram: Text unter einer Datei, gezählt ohne Formatierung


def passt_als_beschriftung(stuecke: list[str]) -> bool:
    return len(stuecke) == 1 and len(unescape(re.sub(r"<[^>]+>", "", stuecke[0]))) <= BESCHRIFTUNG_MAX


def dateien_auswaehlen(dateien: list[str]) -> list[str]:
    """Gibt es zu einer Datei eine gleichnamige PDF, bekommt Jan nur die PDF (docx bleibt auf dem Server)."""
    pdfs = {str(Path(d).with_suffix("")) for d in dateien if Path(d).suffix.lower() == ".pdf"}
    return [d for d in dateien if Path(d).suffix.lower() == ".pdf" or str(Path(d).with_suffix("")) not in pdfs]


class Gemeldet:
    """Merkt sich, was Jan schon gezeigt wurde (data/gemeldet.json), damit nichts doppelt kommt.

    angezeigt: Entwurfs-ID -> Fingerabdruck zum Zeitpunkt der Anzeige.
    nachrichten: Telegram-Nachrichten-ID -> Auftrags-ID, damit Jans Antwort zugeordnet werden kann.
    Meldungen mit Rückfrage stehen dort als "m:<Meldungs-ID>" (siehe meldung_zu).
    listen["am_pc"]: Sitzungen, die gerade am PC liegen (Bot schreibt nicht hinein).
    listen["geklickt"]: Meldungen, deren Knopf schon gedrückt wurde (nur ein Klick je Meldung).
    listen["weitergaben"]: Aufträge von Agent an Agent, die Jan schon gemeldet wurden.
    """

    LISTEN = ("ausgefuehrt", "unklar", "auftraege", "am_pc", "geklickt", "weitergaben", "abgelaufen")
    MAX_GEKLICKT = 500
    MAX_NACHRICHTEN = 500  # ältere Meldungen kann Jan nicht mehr per Antwort fortsetzen

    def __init__(self, pfad: Path):
        self.pfad = pfad
        daten = json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else {}
        self.angezeigt: dict[str, str] = daten.get("angezeigt", {})
        self.nachrichten: dict[str, str] = daten.get("nachrichten", {})
        self.listen: dict[str, set[str]] = {n: set(daten.get(n, [])) for n in self.LISTEN}
        self.stufe: str = daten.get("stufe", "normal")
        self.erinnert: str = daten.get("erinnert", "")  # Tag der letzten Erinnerung an offene Entwürfe

    def nachricht_merken(self, nachricht_id: int, auftrag_id: str) -> None:
        self.nachrichten[str(nachricht_id)] = auftrag_id
        for alt in list(self.nachrichten)[: -self.MAX_NACHRICHTEN]:
            del self.nachrichten[alt]

    def meldung_merken(self, nachricht_id: int, meldung_id: str) -> None:
        self.nachricht_merken(nachricht_id, MELDUNG + meldung_id)

    def entwurf_merken(self, nachricht_id: int, entwurf_id: str) -> None:
        self.nachricht_merken(nachricht_id, ENTWURF + entwurf_id)

    def entwurf_zu(self, nachricht_id: int) -> str | None:
        """ID des Entwurfs, zu dem die Telegram-Nachricht gehört, sonst None."""
        wert = self.nachrichten.get(str(nachricht_id), "")
        return wert[len(ENTWURF):] if wert.startswith(ENTWURF) else None

    def meldung_zu(self, nachricht_id: int) -> str | None:
        """ID der Meldung, zu der die Telegram-Nachricht gehört, sonst None (auch bei Aufträgen)."""
        wert = self.nachrichten.get(str(nachricht_id), "")
        return wert[len(MELDUNG):] if wert.startswith(MELDUNG) else None

    def geklickt(self, meldung_id: str) -> None:
        self.listen["geklickt"].add(meldung_id)
        for alt in sorted(self.listen["geklickt"])[: -self.MAX_GEKLICKT]:  # IDs beginnen mit Datum
            self.listen["geklickt"].discard(alt)

    def speichern(self) -> None:
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        daten = {"angezeigt": self.angezeigt, "nachrichten": self.nachrichten, "stufe": self.stufe,
                 "erinnert": self.erinnert,
                 **{n: sorted(v) for n, v in self.listen.items()}}
        tmp = self.pfad.with_suffix(".tmp")
        tmp.write_text(json.dumps(daten, indent=2), encoding="utf-8")
        tmp.replace(self.pfad)


def dateiname_bereinigen(name: str | None, ersatz: str = "datei") -> str:
    """Dateiname aus Telegram sicher machen: kein Pfad, nicht versteckt (.env), nur harmlose Zeichen."""
    name = Path((name or "").replace("\\", "/")).name
    name = unicodedata.normalize("NFC", name)  # macOS: ü als u plus zwei Punkte, sonst würde daraus u_
    name = re.sub(r"[^\w.\- ]", "_", name).strip(" .")
    stamm, punkt, endung = name.rpartition(".")
    if punkt and len(name) > 100:
        name = stamm[: 99 - len(endung)] + "." + endung
    return name[:100] or ersatz


def datei_gehoert_zum_auftrag(bildunterschrift: str | None, weitergeleitet: bool, ist_antwort: bool) -> bool:
    """Gehört eine Datei zum Auftragstext, der gerade kurz wartet? Ja, außer sie ist eine Antwort auf eine Nachricht
    oder Jan hat ihr eine eigene Bildunterschrift gegeben. Bei weitergeleiteten stammt die Unterschrift vom Original."""
    if ist_antwort:
        return False
    return weitergeleitet or not (bildunterschrift or "").strip()


class Eingang:
    """Dateien von Jan, die noch keinem Auftrag gehören (je Datei ein Unterordner, älteste zuerst).

    Liegt auf der Platte statt im Speicher, damit nach einem Neustart nichts verloren geht.
    """

    def __init__(self, pfad: Path):
        self.pfad = pfad

    def neuer_platz(self, name: str) -> Path:
        ordner = self.pfad / f"{datetime.now():%Y%m%d-%H%M%S-%f}-{secrets.token_hex(2)}"
        ordner.mkdir(parents=True)
        return ordner / dateiname_bereinigen(name)

    def wartende(self) -> list[Path]:
        if not self.pfad.exists():
            return []
        return [d for o in sorted(self.pfad.iterdir()) if o.is_dir() for d in sorted(o.iterdir()) if d.is_file()]

    def aufraeumen(self) -> None:
        """Leere Unterordner entfernen (nachdem die Dateien in einen Auftrag verschoben wurden)."""
        if self.pfad.exists():
            for o in self.pfad.iterdir():
                if o.is_dir() and not any(o.iterdir()):
                    o.rmdir()

    def verwerfen(self) -> int:
        anzahl = len(self.wartende())
        if self.pfad.exists():
            shutil.rmtree(self.pfad)
        return anzahl


# ---------- Menü-Nachricht (Panel) der Zentrale ----------
# Knopf-Daten: u:<aktion> oder u:a:<agent>:<modus> (Agent gewählt, Modus umschalten).

PANEL = "u:"
PANEL_AKTIONEN = ("home", "neu", "entwuerfe", "zeigen", "verbrauch", "status", "hilfe")
ZURUECK = [[("« Zurück", PANEL + "home")]]


def panel_auswerten(daten: str) -> tuple[str, str | None, str | None] | None:
    """'u:status' -> ('status', None, None), 'u:a:uni:lernen' -> ('agent', 'uni', 'lernen'),
    'u:e:<Entwurfs-ID>' -> ('entwurf', ID, None), sonst None."""
    if not daten.startswith(PANEL):
        return None
    wert = daten[len(PANEL):]
    if wert in PANEL_AKTIONEN:
        return wert, None, None
    m = re.fullmatch(r"a:([a-z]+):(erledigen|lernen)", wert)
    if m and m.group(1) in AGENTEN:
        return "agent", m.group(1), m.group(2)
    m = re.fullmatch(r"e:(\d{8}-\d{6}-[a-z]+-[0-9a-f]{6})", wert)  # ein Entwurf aus der Liste (ID wie agentkit)
    if m:
        return "entwurf", m.group(1), None
    return None


def ansicht_home(zeilen: list[str], agenten: list[str], entwuerfe: int, hinweis: str = "") -> tuple[str, list]:
    """Startansicht: Kurzstand nur, wenn etwas zu tun ist (zeilen), je Agent mit Dienst ein Knopf, darunter
    „Entwürfe (n)“, wenn welche offen sind. Status, Verbrauch und Hilfe gibt es als Befehl."""
    text = "\n".join(["Zentrale", *zeilen, *([hinweis] if hinweis else [])])
    knoepfe = [[(anzeigename(a), f"{PANEL}a:{a}:erledigen") for a in agenten[i:i + 2]]
               for i in range(0, len(agenten), 2)]
    if entwuerfe:
        knoepfe.append([(f"Entwürfe ({entwuerfe})", PANEL + "entwuerfe")])
    return text, knoepfe


def ansicht_agent(agent: str, modus: str) -> tuple[str, list]:
    """Agent gewählt: die nächste Nachricht ist der Auftrag (Modus „lernen“ nur noch über alte Knöpfe)."""
    zusatz = " (lernen)" if modus == "lernen" else ""
    return f"Was soll {anzeigename(agent)}{zusatz} tun?", ZURUECK


MAX_ENTWURF_KNOEPFE = 10


def ansicht_entwuerfe(offene: list[dict], alter: dict[str, float] | None = None) -> tuple[str, list]:
    """Liste der offenen Entwürfe, jeder einzeln antippbar (zeigt ihn mit Freigeben, Ändern, Ablehnen).
    alter: Stunden je Entwurfs-ID, dann steht dabei, seit wann er wartet."""
    if not offene:
        return "Keine offenen Entwürfe.", ZURUECK
    alter = alter or {}
    kopf = mehrzahl(len(offene), "Entwurf offen", "Entwürfe offen")
    if alter:
        kopf += f", der älteste {tage_text(max(alter.values()))}" if len(offene) > 1 else f", {tage_text(max(alter.values()))}"
    knoepfe = [[(_knopf_kurz(e["titel"]), f"{PANEL}e:{e['id']}")] for e in offene if e.get("id")]
    return kopf + ".", [*knoepfe[:MAX_ENTWURF_KNOEPFE], *ZURUECK]


def _knopf_kurz(titel: str, laenge: int = 40) -> str:
    titel = " ".join(titel.split())
    return titel if len(titel) <= laenge else titel[: laenge - 1].rstrip() + "…"


def ansicht_text(titel: str, text: str) -> tuple[str, list]:
    return aufteilen(f"{titel}\n\n{text}")[0], ZURUECK


# ---------- Regeln für Jans Nachrichten (prüfbar, tests/test_regeln.py) ----------
FUELLWORT = re.compile(r"\b(bitte|danke|dankesch[öo]n|leider|gerne?)\b|kommt hierher|meldet sich|meldet er sich",
                       re.IGNORECASE)
IMPERATIV = re.compile(r"(?:^|(?<=[.!?:]\s)|(?<=\n))(?:Bitte\s+)?(?:Schick|Schreib|Tipp|Leg|Prüf|Sieh|Gib|Antworte|"
                       r"Warte|Beende|Lies|Öffne|Wähl|Ruf|Hol)e?\b|\bPrüfen:", re.MULTILINE)
NAVIGATION = ("« Zurück",)


def sichtbarer_teil(html: str) -> str:
    """Was Jan ohne Aufklappen sieht: ohne <blockquote expandable>, ohne Formatierung."""
    ohne = re.sub(r"<blockquote expandable>.*?</blockquote>", "", html or "", flags=re.DOTALL)
    return unescape(re.sub(r"<[^>]+>", "", ohne)).strip()


def regelverstoesse(html: str, knoepfe: list[str] | None = None) -> list[str]:
    """Verstöße einer Nachricht an Jan gegen die Kürze-Regeln (docs/befund-ux.md, Entscheidung 4):
    sichtbar höchstens SICHTBAR_MAX + Kopf, höchstens PUNKTE_MAX Punkte, höchstens eine Handlung (Aufforderung im
    Text oder Auswahl per Knopf, „« Zurück“ zählt nicht), keine Füllwörter. Entwürfe zur Freigabe sind ausgenommen."""
    sichtbar = sichtbarer_teil(html)
    befunde = []
    if len(sichtbar) > SICHTBAR_MAX + 100:  # 100 Zeichen für Absender und Zusatz
        befunde.append(f"laenge: {len(sichtbar)} sichtbare Zeichen")
    punkte = [z for z in sichtbar.splitlines() if z.lstrip().startswith(("•", "- "))]
    if len(punkte) > PUNKTE_MAX:
        befunde.append(f"punkte: {len(punkte)}")
    handlungen = len(IMPERATIV.findall(sichtbar)) + (1 if [k for k in knoepfe or [] if k not in NAVIGATION] else 0)
    if handlungen > 1:
        befunde.append(f"handlungen: {handlungen}")
    for m in FUELLWORT.finditer(sichtbar):
        befunde.append(f"fuellwort: {m.group(0)}")
    return befunde
