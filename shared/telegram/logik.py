"""Reine Logik der Telegram-Zentrale (ohne Telegram), damit sie testbar ist."""

import json
import re
import secrets
import shutil
from datetime import datetime
from pathlib import Path

AGENTEN = ("uni", "dokumente", "posteingang", "einkauf")
MAX_LAENGE = 3800  # Telegram erlaubt 4096 Zeichen pro Nachricht, etwas Puffer
MAX_DATEI_BYTES = 20 * 1024 * 1024  # mehr lädt die Bot-Schnittstelle von Telegram nicht herunter


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


def entwurf_als_text(entwurf: dict) -> list[str]:
    """Entwurf so darstellen, dass Jan alles sieht, was ausgeführt wird.

    Lange Inhalte werden auf mehrere Nachrichten verteilt (nichts abschneiden,
    denn freigegeben wird genau das, was angezeigt wurde).
    """
    kopf = f"Entwurf von {entwurf['agent']} ({entwurf['typ']})\n{entwurf['titel']}"
    if entwurf.get("vorgaenger"):
        kopf += "\n(überarbeitete Fassung)"
    teile = [kopf, entwurf["inhalt"]]
    if entwurf.get("daten"):
        teile.append("Details:\n" + json.dumps(entwurf["daten"], ensure_ascii=False, indent=2))
    return aufteilen("\n\n".join(teile))


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


STUFEN_TEXT = {
    "normal": "normal (alles läuft wie geplant)",
    "sparen": "sparen (1 Lauf gleichzeitig, jeder 2. Zeitlauf entfällt, kleineres Modell für Routine)",
    "nur_auftraege": "nur Aufträge (zeitgesteuerte Läufe pausiert, deine Aufträge laufen weiter)",
    "limit": "Limit erreicht (alles wartet bis zum Reset)",
}


def verbrauch_text(stand: dict | None, stufe: str, heute: dict[str, dict], zeit_text) -> str:
    zeilen = [f"Stufe: {STUFEN_TEXT[stufe]}"]
    if stand is None:
        zeilen.append("Noch kein Lauf protokolliert, Auslastung unbekannt.")
    else:
        zeilen += [
            f"5 Stunden: {stand.get('5h', 0) * 100:.0f} %  (Reset {zeit_text(stand.get('reset_5h'))})",
            f"7 Tage: {stand.get('7d', 0) * 100:.0f} %  (Reset {zeit_text(stand.get('reset_7d'))})",
            f"Stand vom letzten Lauf: {zeit_text(stand.get('zeit'))} (enthält auch deine eigenen Chats)",
        ]
    zeilen.append("")
    if not heute:
        zeilen.append("Heute noch keine Läufe.")
    else:
        zeilen.append("Heute:")
        for agent, s in sorted(heute.items()):
            fehler = f", {s['fehler']} mit Fehler" if s["fehler"] else ""
            zeilen.append(f"- {agent}: {s['laeufe']} {'Lauf' if s['laeufe'] == 1 else 'Läufe'}, {s['tokens'] / 1000:.0f}k Tokens, "
                          f"{s['minuten']:.1f} min{fehler}")
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


class Gemeldet:
    """Merkt sich, was Jan schon gezeigt wurde (data/gemeldet.json), damit nichts doppelt kommt.

    angezeigt: Entwurfs-ID -> Fingerabdruck zum Zeitpunkt der Anzeige.
    nachrichten: Telegram-Nachrichten-ID -> Auftrags-ID, damit Jans Antwort zugeordnet werden kann.
    Meldungen mit Rückfrage stehen dort als "m:<Meldungs-ID>" (siehe meldung_zu).
    listen["am_pc"]: Sitzungen, die gerade am PC liegen (Bot schreibt nicht hinein).
    listen["geklickt"]: Meldungen, deren Knopf schon gedrückt wurde (nur ein Klick je Meldung).
    """

    LISTEN = ("ausgefuehrt", "unklar", "auftraege", "am_pc", "geklickt")
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
