"""Reine Logik der Telegram-Zentrale (ohne Telegram), damit sie testbar ist."""

import json
import re
import secrets
import shutil
from datetime import datetime
from html import escape, unescape
from pathlib import Path

AGENTEN = ("uni", "dokumente", "posteingang", "einkauf")
MAX_LAENGE = 3800  # Telegram erlaubt 4096 Zeichen pro Nachricht, etwas Puffer
MAX_DATEI_BYTES = 20 * 1024 * 1024  # mehr lädt die Bot-Schnittstelle von Telegram nicht herunter
ZENTRALE = "zentrale"  # Absender für Systemnachrichten (Sprachregel, Jan 27.10.2026)

# ---------- Texte für Jan (docs/sprache/sprachregel.md) ----------
OHNE_GRUND = "Einen Grund kann ich dir leider nicht nennen. Schick den Auftrag noch einmal, oder sieh am PC nach."
HILFE = (
    "Hilfe\n\n"
    "Das Menü holst du mit /start.\n\n"
    "Aufträge:\n"
    "/uni Text: Uni erledigt das allein.\n"
    "/unilern Text: Du lernst es zusammen mit Uni.\n"
    "Genauso für {weitere}.\n"
    "Text ohne Befehl: Ich frage, an wen er geht.\n"
    "Antwort auf ein Ergebnis: Es geht im selben Gespräch weiter.\n"
    "Antwort auf eine Meldung mit Knöpfen: zählt wie ein Knopf.\n\n"
    "Dateien und Fotos: Mit /uni und Text als Bildunterschrift gehen sie gleich mit. "
    "Ohne Befehl warten sie auf den nächsten Auftrag. /verwerfen löscht sie.\n\n"
    "Am PC weitermachen: /pc als Antwort auf ein Ergebnis. Zurück nach Telegram mit /weiter.\n\n"
    "Überblick: /status zeigt, was offen ist. /verbrauch zeigt die Rechenzeit."
)
KNOPF_ALT = "Dieser Knopf ist veraltet. Hier ist das aktuelle Menü."
NICHT_ANGELEGT = "Den Auftrag konnte ich nicht anlegen. Schick ihn bitte noch einmal. Einzelheiten stehen am PC."
DATEI_ZU_GROSS = "Die Datei ist zu groß für Telegram. Leg sie am PC in den Ordner des passenden Agenten."
DATEI_NICHT_GELADEN = "Die Datei konnte ich nicht laden. Schick sie bitte noch einmal."
TEXT_WEG = "Der Text ist nicht mehr da. Schick ihn bitte noch einmal."
AN_WEN = "An wen geht das?"


def hilfe_text(agenten) -> str:
    weitere = [f"/{a}" for a in agenten if a != "uni"]
    return HILFE.format(weitere=", ".join(weitere) or "die anderen Agenten")


def status_text(zahlen: dict[str, int]) -> str:
    """Überblick für /status und das Menü. zahlen: offen, ausfuehrung, unklar, auftraege, am_pc, dateien."""
    return "\n".join([
        f"Entwürfe offen: {zahlen['offen']}",
        f"Freigegeben, nicht ausgeführt: {zahlen['ausfuehrung']}",
        f"Unklar, ob ausgeführt: {zahlen['unklar']}",
        f"Aufträge in Arbeit: {zahlen['auftraege']}",
        f"Gespräche am PC: {zahlen['am_pc']}",
        f"Wartende Dateien: {zahlen['dateien']}",
    ])


def home_zeilen(stand: dict | None, stufe: str, entwuerfe: int, offen: int, wartend: int) -> list[str]:
    """Kurzstand oben im Menü."""
    zeilen = []
    if stufe != "normal":
        zeilen.append(STUFEN_TEXT[stufe].split(". ")[0].rstrip(".") + ".")
    if stand:
        zeilen.append(f"Verbraucht: {stand.get('5h', 0) * 100:.0f} % (5 Stunden), "
                      f"{stand.get('7d', 0) * 100:.0f} % (7 Tage)")
    zeilen.append(f"Entwürfe: {entwuerfe}  |  Aufträge in Arbeit: {offen}")
    if wartend:
        zeilen.append(f"Wartende Dateien: {wartend}")
    return zeilen


def freigabe_antwort(entscheidung: str, agent: str) -> str:
    name = anzeigename(agent)
    if entscheidung == "freigegeben":
        return f"Freigegeben. {name} führt es jetzt aus und meldet sich."
    if entscheidung == "abgelehnt":
        return f"Abgelehnt. {name} führt nichts aus."
    return "Was soll anders werden? Schreib es als nächste Nachricht."


def freigabe_fehler(grund: str) -> str:
    """Antwort auf einen Knopf, der nicht mehr geht (Grund aus agentkit.freigabe, steht nur im Log)."""
    if "weicht von der Anzeige ab" in grund:
        return ("Der Entwurf wurde nach der Anzeige geändert. Ich habe nichts freigegeben. "
                "Im Menü unter Entwürfe kannst du ihn neu anzeigen lassen.")
    if "nicht (mehr) offen" in grund:
        return "Über diesen Entwurf ist schon entschieden."
    return "Das ging nicht. Einzelheiten stehen am PC."


def aenderung_weiter(agent: str, dateien: int) -> str:
    mit = f" (mit {anzahl_dateien(dateien)})" if dateien else ""
    return f"{anzeigename(agent)} überarbeitet den Entwurf{mit}. Die neue Fassung kommt hierher."


def unklar_text(titel: str) -> str:
    return (f"Ich weiß nicht, ob das geklappt hat: {titel}\n"
            "Ich habe damit angefangen, aber kein Ende gemeldet. Bitte prüf selbst, ob es angekommen ist. "
            "Ich wiederhole es nicht von allein.")


def datei_nicht_gesendet(datei: str) -> str:
    name = Path(datei).stem.replace("_", " ")
    return f"Die Datei „{name}“ kam nicht an. Sie liegt am PC in meinem Ordner."


def dateien_warten(anzahl: int, beispiel: str, befehl_unbekannt: bool) -> str:
    vorweg = "Den Befehl in der Bildunterschrift kenne ich nicht. " if befehl_unbekannt else ""
    liegt = "liegt" if anzahl == 1 else "liegen"
    return (f"{vorweg}{anzahl_dateien(anzahl)} {liegt} bereit. Schick jetzt den Auftrag, zum Beispiel {beispiel}. "
            "Die Dateien kommen mit. /verwerfen löscht sie.")


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


TYP_NAMEN = {"mail": "Mail-Entwurf", "nachricht": "Nachrichten-Entwurf", "kauf": "Kauf-Entwurf",
             "termin": "Termin-Entwurf"}


def _steht_im_inhalt(wert, inhalt: str) -> bool:
    """Steht der Wert (Text oder Liste von Texten) wörtlich, als ganzes Wort, schon im Inhalt?"""
    werte = wert if isinstance(wert, list) else [wert]
    if not all(isinstance(w, str) for w in werte):
        return False  # Zahlen, Objekte usw. immer zeigen
    return all(not w.strip() or re.search(r"(?<!\w)" + re.escape(w.strip()) + r"(?!\w)", inhalt) for w in werte)


DETAIL_NAMEN = {"an": "An", "cc": "Cc", "bcc": "Bcc", "betreff": "Betreff", "text": "Text", "begruendung": "Warum",
                "antwort_auf_uid": "Antwort auf Mail Nr.", "in_reply_to": "Antwort auf"}


def detail_name(schluessel: str) -> str:
    return DETAIL_NAMEN.get(schluessel, schluessel.replace("_", " ").capitalize())


def detail_wert(wert) -> str:
    """Wert eines Entwurfs lesbar: Listen mit Komma, ja/nein, Objekte als „Name: Wert“."""
    if isinstance(wert, bool):
        return "ja" if wert else "nein"
    if isinstance(wert, list):
        return ", ".join(detail_wert(w) for w in wert)
    if isinstance(wert, dict):
        return ", ".join(f"{detail_name(k)}: {detail_wert(w)}" for k, w in wert.items())
    return str(wert)


def entwurf_als_text(entwurf: dict) -> list[str]:
    """Entwurf so darstellen, dass Jan alles sieht, was ausgeführt wird (HTML wie mit_absender).

    Unter Details steht nur, was im Inhalt nicht schon wörtlich steht (Jan, 27.10.2026),
    damit z. B. der Mailtext nicht zweimal kommt. Lange Inhalte werden auf mehrere
    Nachrichten verteilt (nichts abschneiden, denn freigegeben wird genau das, was
    angezeigt wurde).
    """
    zusatz = TYP_NAMEN.get(entwurf["typ"], "Entwurf") + (", überarbeitet" if entwurf.get("vorgaenger") else "")
    teile = [entwurf["titel"], entwurf["inhalt"]]
    details = [f"{detail_name(k)}: {detail_wert(v)}" for k, v in (entwurf.get("daten") or {}).items()
               if v not in ("", [], {}, None) and not _steht_im_inhalt(v, entwurf["inhalt"])]
    if details:
        teile.append("Details:\n" + "\n".join(details))
    return mit_absender(entwurf["agent"], "\n\n".join(teile), zusatz)


def aufteilen(text: str, max_laenge: int = MAX_LAENGE) -> list[str]:
    stuecke = []
    while len(text) > max_laenge:
        schnitt = text.rfind("\n", 0, max_laenge)
        if schnitt <= 0:
            schnitt = max_laenge
        stuecke.append(text[:schnitt])
        text = text[schnitt:].lstrip("\n")
    stuecke.append(text)
    return stuecke


STUFEN_TEXT = {  # erster Satz steht auch im Menü
    "normal": "Die Rechenzeit reicht. Alles läuft wie geplant.",
    "sparen": "Die Rechenzeit wird knapp, darum spare ich. Ich mache nur eine Sache auf einmal. Jeder zweite feste "
              "Durchgang fällt aus. Leichte Sachen mache ich mit weniger Aufwand.",
    "nur_auftraege": "Die Rechenzeit ist fast aufgebraucht. Nur deine Aufträge laufen, feste Durchgänge machen Pause.",
    "limit": "Die Rechenzeit ist aufgebraucht. Alles wartet.",
}


def verbrauch_text(stand: dict | None, stufe: str, heute: dict[str, dict], zeit_text) -> str:
    zeilen = [STUFEN_TEXT[stufe]]
    if stand is None:
        zeilen.append("Wie viel verbraucht ist, weiß ich erst nach der ersten Aufgabe.")
    else:
        zeilen += [
            f"Letzte 5 Stunden: {stand.get('5h', 0) * 100:.0f} % verbraucht, wieder frei {zeit_text(stand.get('reset_5h'))}",
            f"Letzte 7 Tage: {stand.get('7d', 0) * 100:.0f} % verbraucht, wieder frei {zeit_text(stand.get('reset_7d'))}",
            f"Stand: {zeit_text(stand.get('zeit'))}",
        ]
    zeilen.append("")
    if not heute:
        zeilen.append("Heute hat noch niemand gearbeitet.")
    else:
        zeilen.append("Heute:")
        for agent, s in sorted(heute.items(), key=lambda x: anzeigename(x[0])):
            fehler = f", {s['fehler']}-mal hat es nicht geklappt" if s["fehler"] else ""
            zeilen.append(f"• {anzeigename(agent)}: {s['laeufe']}-mal gearbeitet, "
                          f"{str(round(s['minuten'], 1)).replace('.', ',')} Minuten{fehler}")
    return "\n".join(zeilen)


MELDUNG = "m:"  # Vorsatz für Meldungen in Gemeldet.nachrichten und in Knopf-Daten


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


def anzeigename(agent: str) -> str:
    """'dokumente' -> 'Dokumente', 'lia/recherche' -> 'Recherche (Lia)' (so steht der Absender über der Nachricht)."""
    instanz, _, name = agent.rpartition("/")
    name = name[:1].upper() + name[1:]
    return f"{name} ({instanz[:1].upper()}{instanz[1:]})" if instanz else name


def mit_absender(agent: str, text: str, zusatz: str = "") -> list[str]:
    """Nachricht(en) im HTML-Format: Agent fett in der ersten Zeile, darunter der Text (escaped).

    Technisches (IDs, Pfade, Auftragstext) gehört nicht hierher, sondern ins Log.
    """
    kopf = f"<b>{escape(anzeigename(agent), False)}</b>" + (f" · {escape(zusatz, False)}" if zusatz else "")
    stuecke = aufteilen(text.strip(), MAX_LAENGE - 100)
    return [f"{kopf}\n{escape(stuecke[0], False)}".rstrip(), *(escape(s, False) for s in stuecke[1:])]


def auftrag_nachricht(auftrag: dict) -> list[str]:
    """Ergebnis eines abgeschlossenen Auftrags für Jan: nur Absender und Ergebnis des Agenten."""
    if auftrag["status"] == "erledigt":
        if (auftrag.get("daten") or {}).get("kern"):  # strukturiertes Ergebnis: Vorlage, Kern zuerst
            import vorlagen
            return vorlagen.ergebnis_html(mit_absender(auftrag["agent"], "")[0], auftrag, aufteilen)
        return mit_absender(auftrag["agent"], auftrag.get("ergebnis") or "Erledigt.")
    return mit_absender(auftrag["agent"], auftrag.get("ergebnis") or OHNE_GRUND, "hat nicht geklappt")


def weitergabe_text(auftrag: dict, dienst_da: bool) -> list[str] | None:
    """Info an Jan zu einem Auftrag von Agent an Agent: nur wenn er liegen bleibt, sonst None."""
    if dienst_da:
        return None
    an = anzeigename(auftrag["agent"])
    return mit_absender(ZENTRALE, f"{anzeigename(auftrag['von'])} hat {an} etwas aufgetragen. {an} ist aber noch "
                                  "nicht eingerichtet. So lange wartet der Auftrag.")


def stufe_text(alt: str, neu: str, stand: dict | None, zeit_text) -> list[str] | None:
    """Stufenwechsel nur melden, wenn Jan es merkt: Rechenzeit aufgebraucht und wieder frei."""
    if neu == "limit" and alt != "limit":
        bis = (stand or {}).get("reset_status")
        return mit_absender(ZENTRALE, "Die Rechenzeit ist aufgebraucht. Deine Aufträge warten"
                            + (f" bis {zeit_text(bis)} und laufen dann von selbst." if bis
                               else " und laufen von selbst weiter, sobald wieder Rechenzeit frei ist."))
    if alt == "limit" and neu != "limit":
        return mit_absender(ZENTRALE, "Es ist wieder Rechenzeit frei. Die Agenten arbeiten weiter.")
    return None


def anzahl_dateien(n: int) -> str:
    return "1 Datei" if n == 1 else f"{n} Dateien"


def bestaetigung(agent: str, modus: str, dateinamen: list[str]) -> str:
    """Kurze Rückmeldung nach einem Auftrag: 'Uni ist dran. Das Ergebnis kommt hierher.'"""
    text = f"{anzeigename(agent)} ist dran" + (" (lernen)" if modus == "lernen" else "")
    if dateinamen:
        text += f", mit {anzahl_dateien(len(dateinamen))}"
    return text + ". Das Ergebnis kommt hierher."


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

    LISTEN = ("ausgefuehrt", "unklar", "auftraege", "am_pc", "geklickt", "weitergaben")
    MAX_GEKLICKT = 500
    MAX_NACHRICHTEN = 500  # ältere Meldungen kann Jan nicht mehr per Antwort fortsetzen

    def __init__(self, pfad: Path):
        self.pfad = pfad
        daten = json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else {}
        self.angezeigt: dict[str, str] = daten.get("angezeigt", {})
        self.nachrichten: dict[str, str] = daten.get("nachrichten", {})
        self.listen: dict[str, set[str]] = {n: set(daten.get(n, [])) for n in self.LISTEN}
        self.stufe: str = daten.get("stufe", "normal")

    def nachricht_merken(self, nachricht_id: int, auftrag_id: str) -> None:
        self.nachrichten[str(nachricht_id)] = auftrag_id
        for alt in list(self.nachrichten)[: -self.MAX_NACHRICHTEN]:
            del self.nachrichten[alt]

    def meldung_merken(self, nachricht_id: int, meldung_id: str) -> None:
        self.nachricht_merken(nachricht_id, MELDUNG + meldung_id)

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
                 **{n: sorted(v) for n, v in self.listen.items()}}
        tmp = self.pfad.with_suffix(".tmp")
        tmp.write_text(json.dumps(daten, indent=2), encoding="utf-8")
        tmp.replace(self.pfad)


def dateiname_bereinigen(name: str | None, ersatz: str = "datei") -> str:
    """Dateiname aus Telegram sicher machen: kein Pfad, nicht versteckt (.env), nur harmlose Zeichen."""
    name = Path((name or "").replace("\\", "/")).name
    name = re.sub(r"[^\w.\- ]", "_", name).strip(" .")
    stamm, punkt, endung = name.rpartition(".")
    if punkt and len(name) > 100:
        name = stamm[: 99 - len(endung)] + "." + endung
    return name[:100] or ersatz


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
    """'u:status' -> ('status', None, None), 'u:a:uni:lernen' -> ('agent', 'uni', 'lernen'), sonst None."""
    if not daten.startswith(PANEL):
        return None
    wert = daten[len(PANEL):]
    if wert in PANEL_AKTIONEN:
        return wert, None, None
    m = re.fullmatch(r"a:([a-z]+):(erledigen|lernen)", wert)
    if m and m.group(1) in AGENTEN:
        return "agent", m.group(1), m.group(2)
    return None


def ansicht_home(zeilen: list[str], agenten: list[str], entwuerfe: int, hinweis: str = "") -> tuple[str, list]:
    """Startansicht: Kurzstand (zeilen), je Agent mit Dienst ein Knopf, darunter Werkzeuge."""
    text = "\n".join(["Zentrale", "", *zeilen] + (["", hinweis] if hinweis else []))
    knoepfe = [[(anzeigename(a), f"{PANEL}a:{a}:erledigen") for a in agenten[i:i + 2]]
               for i in range(0, len(agenten), 2)]
    knoepfe += [
        [(f"Entwürfe ({entwuerfe})", PANEL + "entwuerfe"), ("Verbrauch", PANEL + "verbrauch")],
        [("Status", PANEL + "status"), ("Hilfe", PANEL + "hilfe")],
        [("↻ Aktualisieren", PANEL + "neu")],
    ]
    return text, knoepfe


def ansicht_agent(agent: str, modus: str) -> tuple[str, list]:
    anders = "lernen" if modus == "erledigen" else "erledigen"
    text = (f"Auftrag an {anzeigename(agent)} ({modus})\n\n"
            f"Schreib mir jetzt, was {anzeigename(agent)} tun soll. Dateien, die schon warten, kommen mit.")
    return text, [[(f"Modus wechseln: {anders}", f"{PANEL}a:{agent}:{anders}")], *ZURUECK]


def ansicht_entwuerfe(offene: list[dict]) -> tuple[str, list]:
    if not offene:
        return "Entwürfe\n\nKeine offenen Entwürfe.", ZURUECK
    zeilen = ["Entwürfe", ""] + [f"• {e['titel']} ({anzeigename(e['agent'])})" for e in offene]
    return "\n".join(zeilen), [[("Alle mit Knöpfen anzeigen", PANEL + "zeigen")], *ZURUECK]


def ansicht_text(titel: str, text: str) -> tuple[str, list]:
    return aufteilen(f"{titel}\n\n{text}")[0], ZURUECK
