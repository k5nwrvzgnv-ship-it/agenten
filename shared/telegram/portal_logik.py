"""Reine Logik von Lias Zentrale (portal.py), ohne Telegram, damit sie testbar ist.

Oberfläche wie bei bekannten Telegram-Bots: eine einzige Menü-Nachricht ("Panel"), die sich beim
Tippen verändert (Ansichten). Schreibt Lia etwas, kommt das Panel neu unter ihre Nachricht.
- Material und Frage: Ansicht mit Anleitung, Lias nächste Nachricht ist der Inhalt, dann Bestätigen.
- Woche: geht sofort als Auftrag los.
- Text ohne Menü: Lia wählt, was damit passieren soll. Kurze Grüße zeigen nur das Menü.
- Meine Anfragen: die letzten Aufträge mit Stand. Hilfe: kurze Erklärung.

Zustand je Chat (chat_data): "wartet_auf" = Art, deren Inhalt als nächste Nachricht kommt,
"entwurf" = {"art", "text"}, der auf Bestätigung wartet.
Knopf-Daten: p:<aktion>, siehe AKTIONEN.
"""

import re
from dataclasses import dataclass

Knoepfe = list[list[tuple[str, str]]]


@dataclass(frozen=True)
class Art:
    knopf: str  # Beschriftung im Menü
    agent: str
    quelle: str  # Feld quelle im Auftrag, daran erkennt der Agent die Art
    anleitung: str = ""  # leer: kein Inhalt nötig, Auftrag geht sofort los
    standardtext: str = ""  # Auftragstext, wenn es keine Anleitung gibt


ARTEN = {
    "material": Art("Neues Material", "unterricht", "portal-material",
                    anleitung="Schreib mir einfach, was du brauchst:\nFach, Klasse, Thema, Dauer\n\n"
                              "Zum Beispiel: Arbeitsblatt kategorischer Imperativ, Klasse 10, 45 min"),
    "woche": Art("Meine Woche", "unterricht", "portal-woche", standardtext="Überblick über meine Woche"),
    "frage": Art("Frage stellen", "unterricht", "portal-frage",
                 anleitung="Schreib mir deine Frage als nächste Nachricht."),
    "text": Art("Nachricht", "unterricht", "portal-text"),
}
VORSATZ = "p:"
# Aktionen, die ein Knopf auslösen kann (alles andere ist ein alter oder fremder Knopf)
AKTIONEN = ("home", "neu", "material", "woche", "frage", "anfragen", "hilfe",
            "ja", "nein", "alsmaterial", "alsfrage", "menue")

TITEL = "Zentrale"
IM_AUFBAU = "Im Aufbau: Ich sammle deine Wünsche, richtige Antworten kommen bald."
HILFE = (
    "So funktioniert's\n\n"
    "Neues Material: Du beschreibst, was du brauchst, ich gebe es weiter.\n"
    "Meine Woche: Überblick über deine Woche.\n"
    "Frage stellen: Du schreibst eine Frage, die Antwort kommt hierher.\n"
    "Meine Anfragen: Was unterwegs ist und was fertig ist.\n\n"
    "Du kannst mir auch einfach schreiben, dann frage ich, was ich damit tun soll. "
    "Antworten kommen als eigene Nachricht mit einem Knopf zurück ins Menü."
)
FEHLGESCHLAGEN = "Das hat leider nicht geklappt. Sag Jan bitte Bescheid."
GRUESSE = re.compile(r"(hallo|hi|hey|moin|servus|huhu|guten (morgen|tag|abend)|start)[\s!.?]*", re.IGNORECASE)

ZURUECK = [[("« Zurück", VORSATZ + "home")]]


def k(text: str, aktion: str) -> tuple[str, str]:
    return text, VORSATZ + aktion


def knopf_auswerten(daten: str) -> str | None:
    """'p:material' -> 'material'. Unbekanntes -> None."""
    if not daten.startswith(VORSATZ):
        return None
    wert = daten[len(VORSATZ):]
    return wert if wert in AKTIONEN else None


def kurz(text: str, laenge: int = 40) -> str:
    text = " ".join(text.split())
    return text if len(text) <= laenge else text[: laenge - 1] + "…"


def ist_gruss(text: str) -> bool:
    return bool(GRUESSE.fullmatch(text.strip()))


# ---------- Ansichten: (Text, Knöpfe) ----------

def ansicht_home(offen: int, fertig: int, hinweis: str = "") -> tuple[str, Knoepfe]:
    zeilen = [TITEL, "", "Hallo Lia!", f"Unterwegs: {offen}  |  Fertig: {fertig}"]
    if hinweis:
        zeilen += ["", hinweis]
    zeilen += ["", IM_AUFBAU]
    knoepfe = [
        [k("Neues Material", "material"), k("Meine Woche", "woche")],
        [k("Frage stellen", "frage"), k("Meine Anfragen", "anfragen")],
        [k("Hilfe", "hilfe"), k("↻ Aktualisieren", "neu")],
    ]
    return "\n".join(zeilen), knoepfe


def ansicht_anleitung(art: str) -> tuple[str, Knoepfe]:
    a = ARTEN[art]
    return f"{a.knopf}\n\n{a.anleitung}", ZURUECK


def ansicht_bestaetigen(entwurf: dict) -> tuple[str, Knoepfe]:
    a = ARTEN[entwurf["art"]]
    text = f"{a.knopf}\n\n{kurz(entwurf['text'], 3500)}\n\nSo abschicken?"  # Telegram: max. 4096 Zeichen
    return text, [[k("✓ Abschicken", "ja"), k("✕ Abbrechen", "nein")]]


def ansicht_einordnen(text: str) -> tuple[str, Knoepfe]:
    """Text ohne Menü: Lia wählt, was damit passieren soll."""
    return f"Was soll ich damit tun?\n\n„{kurz(text, 200)}“", [
        [k("Als Materialwunsch", "alsmaterial"), k("Als Frage", "alsfrage")],
        [k("✕ Verwerfen", "nein")],
    ]


def ansicht_anfragen(auftraege: list[dict], anzahl: int = 5) -> tuple[str, Knoepfe]:
    """Die letzten Aufträge (neueste zuerst), Stand ohne Technik."""
    if not auftraege:
        return "Meine Anfragen\n\nNoch keine Anfragen.", ZURUECK
    zeilen = ["Meine Anfragen", ""]
    for a in sorted(auftraege, key=lambda a: a["id"], reverse=True)[:anzahl]:
        stand = {"neu": "unterwegs", "erledigt": "fertig"}.get(a.get("status"), "nicht geklappt")
        art = next((x.knopf for x in ARTEN.values() if x.quelle == a.get("quelle")), "Nachricht")
        zeilen.append(f"• {art}: {kurz(a['text'])} – {stand}")
    return "\n".join(zeilen), ZURUECK


def ansicht_hilfe() -> tuple[str, Knoepfe]:
    return HILFE, ZURUECK


MENUE_KNOPF = [[k("☰ Menü", "menue")]]


# ---------- Zustandswechsel ----------

def anleitung_gewaehlt(zustand: dict, art: str) -> None:
    zustand.pop("entwurf", None)
    zustand["wartet_auf"] = art


def sofort_entwurf(zustand: dict, art: str) -> dict:
    """Art ohne Anleitung (Woche): Entwurf direkt, ohne Rückfrage."""
    zustand.pop("wartet_auf", None)
    zustand.pop("entwurf", None)
    return {"art": art, "text": ARTEN[art].standardtext}


def text_eingang(zustand: dict, text: str) -> str:
    """Lia hat Text geschickt. Gibt zurück, was zu zeigen ist: "home", "bestaetigen" oder "einordnen"."""
    art = zustand.pop("wartet_auf", None)
    if art is None and ist_gruss(text):
        zustand.pop("entwurf", None)
        return "home"
    zustand["entwurf"] = {"art": art or "text", "text": text.strip()}
    return "bestaetigen" if art else "einordnen"


def einordnen(zustand: dict, art: str) -> bool:
    """Text ohne Menü einer Art zuordnen ("material" oder "frage"). False, wenn nichts mehr wartet."""
    entwurf = zustand.get("entwurf")
    if entwurf is None:
        return False
    entwurf["art"] = art
    return True


def entwurf_nehmen(zustand: dict) -> dict | None:
    """Bestätigt: Entwurf aus dem Zustand holen (nur einmal, ein Doppelklick schickt nichts doppelt)."""
    return zustand.pop("entwurf", None)


def abbrechen(zustand: dict) -> None:
    zustand.pop("entwurf", None)
    zustand.pop("wartet_auf", None)


def ergebnis_text(auftrag: dict) -> str:
    """Antwort an Lia, mit Bezug auf ihre Anfrage, ohne Technik (keine IDs, keine Agentennamen)."""
    kopf = f"Zu deiner Anfrage „{kurz(auftrag.get('text', ''))}“:\n\n"
    if auftrag.get("status") != "erledigt":
        return kopf + FEHLGESCHLAGEN
    return kopf + (auftrag.get("ergebnis") or "Erledigt.")
