"""Reine Logik von Lias Zentrale (portal.py), ohne Telegram, damit sie testbar ist.

Bedienung ohne Schrägstrich-Befehle: Eine Menü-Nachricht mit Knöpfen (MENUE).
- Material und Frage: Der Bot fragt nach, Lias nächste Nachricht ist der Inhalt.
- Woche: geht sofort als Auftrag los.
- Text ohne Menü: Lia bestätigt per Knopf, dann geht er als Auftrag los.
Vor dem Abschicken zeigt der Bot den Auftrag mit "Abschicken" und "Verwerfen".

Zustand je Chat (chat_data): "wartet_auf" = Art, deren Inhalt als nächste Nachricht kommt,
"entwurf" = {"art", "text"}, der auf Bestätigung wartet.
Knopf-Daten: p:<art> (Menü), p:ja, p:nein (Bestätigung), p:menue (Menü neu zeigen).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Art:
    knopf: str  # Beschriftung im Menü ("" = nicht im Menü)
    agent: str
    quelle: str  # Feld quelle im Auftrag, daran erkennt der Agent die Art
    nachfrage: str = ""  # leer: kein Inhalt nötig, Auftrag geht sofort los
    standardtext: str = ""  # Auftragstext, wenn es keine Nachfrage gibt


ARTEN = {
    "material": Art("Neues Material", "unterricht", "portal-material",
                    nachfrage="Was brauchst du? Am besten mit Fach, Klasse, Thema und Dauer, "
                              "z. B. \"Arbeitsblatt kategorischer Imperativ, Klasse 10, 45 min\"."),
    "woche": Art("Meine Woche", "unterricht", "portal-woche", standardtext="Überblick über meine Woche"),
    "frage": Art("Frage stellen", "unterricht", "portal-frage", nachfrage="Was möchtest du wissen?"),
    "text": Art("", "unterricht", "portal-text"),
}
MENUE = [k for k, a in ARTEN.items() if a.knopf]
VORSATZ = "p:"

BEGRUESSUNG = "Hallo Lia, hier ist deine Zentrale. Tipp einfach auf einen Knopf oder schreib mir."
MENUE_TEXT = "Was möchtest du tun?"
WEITERGEGEBEN = "Ist unterwegs. Ich melde mich, sobald es eine Antwort gibt."
VERWORFEN = "Verworfen."
ABGELAUFEN = "Das ist nicht mehr aktuell. Bitte noch einmal über das Menü."
FEHLGESCHLAGEN = "Das hat leider nicht geklappt. Sag Jan bitte Bescheid."


def menue_knoepfe() -> list[list[tuple[str, str]]]:
    """Menü als (Beschriftung, Knopf-Daten), ein Knopf je Zeile (gut zu treffen am Handy)."""
    return [[(ARTEN[k].knopf, VORSATZ + k)] for k in MENUE]


BESTAETIGEN_KNOEPFE = [[("Abschicken", VORSATZ + "ja"), ("Verwerfen", VORSATZ + "nein")]]


def knopf_auswerten(daten: str) -> str | None:
    """p:material -> material, p:ja -> ja. Unbekanntes -> None."""
    if not daten.startswith(VORSATZ):
        return None
    wert = daten[len(VORSATZ):]
    return wert if wert in MENUE or wert in ("ja", "nein", "menue") else None


def menue_gewaehlt(zustand: dict, art: str) -> tuple[str, bool]:
    """Menüknopf gedrückt. Gibt (Antworttext, bestaetigen) zurück.

    bestaetigen=True: entwurf steht, der Bot zeigt die Bestätigungsknöpfe.
    """
    zustand.pop("entwurf", None)
    a = ARTEN[art]
    if a.nachfrage:
        zustand["wartet_auf"] = art
        return a.nachfrage, False
    zustand.pop("wartet_auf", None)
    zustand["entwurf"] = {"art": art, "text": a.standardtext}
    return bestaetigung_text(zustand["entwurf"]), True


def text_eingang(zustand: dict, text: str) -> str:
    """Lia hat Text geschickt: wird der Entwurf (Art aus wartet_auf, sonst "text"). Gibt die Rückfrage zurück."""
    art = zustand.pop("wartet_auf", None) or "text"
    zustand["entwurf"] = {"art": art, "text": text.strip()}
    return bestaetigung_text(zustand["entwurf"])


def bestaetigung_text(entwurf: dict) -> str:
    a = ARTEN[entwurf["art"]]
    titel = a.knopf or "Nachricht"
    return f"{titel}:\n{entwurf['text']}\n\nSo abschicken?"


def entwurf_nehmen(zustand: dict) -> dict | None:
    """Bestätigt: Entwurf aus dem Zustand holen (nur einmal, ein Doppelklick schickt nichts doppelt)."""
    return zustand.pop("entwurf", None)


def ergebnis_text(auftrag: dict) -> str:
    """Antwort an Lia, ohne Technik (keine IDs, keine Agentennamen)."""
    if auftrag.get("status") != "erledigt":
        return FEHLGESCHLAGEN
    return auftrag.get("ergebnis") or "Erledigt."
