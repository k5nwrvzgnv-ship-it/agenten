"""Reine Logik von Lias Zentrale (portal.py), ohne Telegram, damit sie testbar ist.

Oberfläche wie bei bekannten Telegram-Bots: eine einzige Menü-Nachricht ("Panel"), die sich beim
Tippen verändert (Ansichten). Schreibt Lia etwas, kommt das Panel neu unter ihre Nachricht.
- Material und Frage: Ansicht mit Anleitung, Lias nächste Nachricht ist der Inhalt, dann Bestätigen.
- Woche: geht sofort als Auftrag los.
- Text ohne Menü: Lia wählt, was damit passieren soll. Kurze Grüße zeigen nur das Menü.
- Meine Anfragen: die letzten Aufträge mit Stand. Hilfe: kurze Erklärung.
- Dateien: warten in der Zentrale, bis Lia schreibt, was damit passieren soll (Bildunterschrift oder nächste
  Nachricht), und hängen dann am Material- oder Frage-Auftrag. Abbrechen oder Verwerfen löscht sie.

- Ergebnisse: Vorlage aus vorlagen.py (HTML), darunter Feedback-Knöpfe (p:fb:<auftrag-id>:<k>). "Falscher Fokus"
  und "Feedback schreiben" warten auf Lias nächste Nachricht; eine Antwort auf das Ergebnis ist ebenfalls Feedback.

Zustand je Chat (chat_data): "wartet_auf" = Art, deren Inhalt als nächste Nachricht kommt,
"entwurf" = {"art", "text"}, der gleich abgeschickt wird, "feedback" = {"bezug", "k"}, das auf Lias Text wartet,
"letzter" = ID des zuletzt abgeschickten Wunsches (für "Zurückziehen").
Knopf-Daten: p:<aktion>, siehe AKTIONEN, und p:fb:... (vorlagen.feedback_auswerten).
"""

import re
from dataclasses import dataclass

import vorlagen as v
from logik import aufteilen

Knoepfe = list[list[tuple[str, str]]]


@dataclass(frozen=True)
class Art:
    knopf: str  # Beschriftung im Menü
    agent: str
    quelle: str  # Feld quelle im Auftrag, daran erkennt der Agent die Art
    anleitung: str = ""  # leer: kein Inhalt nötig, Auftrag geht sofort los


ARTEN = {
    "material": Art("Neues Material", "unterricht", "portal-material",
                    anleitung="Schreib mir, was du brauchst: Fach, Klasse, Thema und Dauer.\n\n"
                              "Zum Beispiel: „Arbeitsblatt zum kategorischen Imperativ, Klasse 10, 45 Minuten“"),
    "text": Art("Nachricht", "unterricht", "portal-text"),  # nur noch Anzeige alter Anfragen
}
VORSATZ = "p:"
# Aktionen, die ein Knopf auslösen kann (alles andere ist ein alter oder fremder Knopf)
# 16.11.2026 (Untersuchung B10): Platzhalter "Meine Woche" und "Frage stellen", die Rückfragen "Als Materialwunsch /
# Als Frage" und "Soll ich das so abschicken?" sowie "Aktualisieren" sind weg. Text geht sofort los, dafür gibt es
# danach "Zurückziehen". Alte Knöpfe dieser Arten zählen als veraltet.
AKTIONEN = ("home", "material", "anfragen", "hilfe", "menue", "verwerfen", "zurueck")

HILFE = (
    "So geht's\n\n"
    "Schreib mir einfach, was du brauchst. Ich mache dir ein Arbeitsblatt oder Folien und lege sofort los.\n"
    "Hast du dich vertan, tippst du danach auf Zurückziehen.\n"
    "Meine Anfragen: Was ich gerade mache und was fertig ist.\n\n"
    "Dateien und Fotos schickst du einfach mit, zum Beispiel ein altes Arbeitsblatt als Vorlage. "
    "Schreib am besten dazu, was ich damit machen soll.\n"
    "Unter jeder Antwort bringt dich ein Knopf zurück ins Menü."
)
FEHLGESCHLAGEN = "Das hat leider nicht geklappt. Sag Jan bitte Bescheid."
# Hinweise oben im Menü (portal.py)
ZU_GROSS = "Die Datei ist zu groß für Telegram. Schick sie Jan bitte auf einem anderen Weg."
NICHT_GELADEN = "Die Datei konnte ich nicht laden. Schick sie bitte noch einmal."
SPRACHNACHRICHT = "Sprachnachrichten verstehe ich noch nicht. Schreib mir bitte."
KNOPF_ALT = "Dieser Knopf ist veraltet. Hier ist das aktuelle Menü."
ZURUECKGEZOGEN = "Zurückgezogen. Ich mache damit nichts."
NICHT_MEHR_OFFEN = "Das ließ sich nicht mehr zurückziehen. Es ist schon fertig."
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

def ansicht_home(offen: int, fertig: int, hinweis: str = "", zurueckziehbar: bool = False) -> tuple[str, Knoepfe]:
    """zurueckziehbar: Lia hat gerade etwas abgeschickt, darunter steht einmal "Zurückziehen"."""
    zeilen = ["Hallo Lia!", f"In Arbeit: {offen}  |  Fertig: {fertig}"]
    if hinweis:
        zeilen += ["", hinweis]
    zeilen += ["", "Schreib mir einfach, was du brauchst."]
    knoepfe = [[k("↩ Zurückziehen", "zurueck")]] if zurueckziehbar else []
    knoepfe += [
        [k("Neues Material", "material"), k("Meine Anfragen", "anfragen")],
        [k("Hilfe", "hilfe")],
    ]
    return "\n".join(zeilen), knoepfe


def ansicht_anleitung(art: str) -> tuple[str, Knoepfe]:
    a = ARTEN[art]
    return f"{a.knopf}\n\n{a.anleitung}", ZURUECK


def dateien_anzahl(anzahl: int) -> str:
    return "1 Datei" if anzahl == 1 else f"{anzahl} Dateien"


def ansicht_dateien(anzahl: int) -> tuple[str, Knoepfe]:
    """Dateien ohne Text: Lia soll schreiben, was damit passieren soll."""
    liegt = "liegt" if anzahl == 1 else "liegen"
    return (f"{dateien_anzahl(anzahl)} {liegt} bereit.\n\nSchreib mir jetzt, was ich damit machen soll. "
            "Zum Beispiel: „Mach daraus ein Arbeitsblatt für Klasse 8“"), [
        [k("✕ Verwerfen", "verwerfen")], *ZURUECK]


def hinweis_dateien(anzahl: int) -> str:
    """Hinweis im Menü, solange Dateien warten."""
    if not anzahl:
        return ""
    liegt, kommt = ("liegt", "kommt") if anzahl == 1 else ("liegen", "kommen")
    return f"{dateien_anzahl(anzahl)} {liegt} bereit und {kommt} mit deiner nächsten Nachricht mit."


def ansicht_anfragen(auftraege: list[dict], anzahl: int = 5) -> tuple[str, Knoepfe]:
    """Die letzten Aufträge (neueste zuerst), Stand ohne Technik."""
    if not auftraege:
        return "Meine Anfragen\n\nNoch keine Anfragen.", ZURUECK
    zeilen = ["Meine Anfragen", ""]
    for a in sorted(auftraege, key=lambda a: a["id"], reverse=True)[:anzahl]:
        stand = {"neu": "in Arbeit", "erledigt": "fertig"}.get(a.get("status"), "hat nicht geklappt")
        art = next((x.knopf for x in ARTEN.values() if x.quelle == a.get("quelle")), "Nachricht")
        zeilen.append(f"• {art}: „{kurz(a['text'])}“ – {stand}")
    return "\n".join(zeilen), ZURUECK


def ansicht_hilfe() -> tuple[str, Knoepfe]:
    return HILFE, ZURUECK


def ansicht_feedback(k: str) -> tuple[str, Knoepfe]:
    """Lia hat "Falscher Fokus" oder "Feedback schreiben" getippt: ihre nächste Nachricht ist das Feedback."""
    return v.FB_FRAGE[k], ZURUECK


MENUE_KNOPF = [[k("☰ Menü", "menue")]]


# ---------- Zustandswechsel ----------

def anleitung_gewaehlt(zustand: dict, art: str) -> None:
    zustand.pop("entwurf", None)
    zustand.pop("feedback", None)
    zustand["wartet_auf"] = art


def text_eingang(zustand: dict, text: str) -> str:
    """Lia hat Text geschickt. Gibt zurück, was zu tun ist: "feedback" (zustand["feedback"] bleibt für portal.py),
    "home" (nur ein Gruß) oder "abschicken": Der Text ist ein Materialwunsch und geht ohne Rückfrage los,
    egal ob Lia vorher "Neues Material" getippt hat (zustand["entwurf"] für entwurf_nehmen)."""
    if "feedback" in zustand:
        return "feedback"
    art = zustand.pop("wartet_auf", None)
    zustand.pop("entwurf", None)
    if art is None and ist_gruss(text):
        return "home"
    zustand["entwurf"] = {"art": "material", "text": text.strip()}
    return "abschicken"


def entwurf_nehmen(zustand: dict) -> dict | None:
    """Entwurf aus dem Zustand holen (nur einmal, nichts geht doppelt los)."""
    return zustand.pop("entwurf", None)


def feedback_gewaehlt(zustand: dict, bezug: str, k: str) -> None:
    abbrechen(zustand)
    zustand["feedback"] = {"bezug": bezug, "k": k}


def abbrechen(zustand: dict) -> None:
    zustand.pop("entwurf", None)
    zustand.pop("wartet_auf", None)
    zustand.pop("feedback", None)
    zustand.pop("letzter", None)


def unterwegs(text: str, dateien: int) -> str:
    """Hinweis im Menü, nachdem Lia etwas abgeschickt hat."""
    mit = f" (mit {dateien_anzahl(dateien)})" if dateien else ""
    return f"Ich mache mich an „{kurz(text)}“{mit}. Ich melde mich, sobald es fertig ist."


def verworfen(anzahl: int) -> str:
    return f"Ich habe {'die Datei' if anzahl == 1 else f'die {anzahl} Dateien'} gelöscht."


def dateien_text(anzahl: int, alle_angekommen: bool) -> str:
    """Abschluss nach den Ergebnisdateien."""
    if not alle_angekommen:
        return "Eine Datei konnte ich leider nicht schicken. Sag Jan bitte Bescheid."
    return "Das ist die Datei." if anzahl == 1 else f"Das sind die {anzahl} Dateien."


def ergebnis_nachricht(auftrag: dict) -> list[str]:
    """Antwort an Lia (HTML), mit Bezug auf ihre Anfrage, ohne Technik (keine IDs, keine Agentennamen).

    Feedback-Bestätigungen haben ihren eigenen Kopf. Hat es nicht geklappt, steht der Grund des Agenten da.
    """
    if auftrag.get("agent") == "feedback":
        return [v.feedback_bestaetigung(auftrag)]
    kopf = f"Zu „{v.esc(kurz(auftrag.get('text', '')))}“:\n"
    if auftrag.get("status") != "erledigt":
        return [kopf + "\n" + v.esc(auftrag.get("ergebnis") or FEHLGESCHLAGEN)]
    return v.ergebnis_html(kopf, auftrag, aufteilen)


def mit_feedback(auftrag: dict) -> bool:
    """Bekommt dieses Ergebnis Feedback-Knöpfe? Nicht bei Fehlern und nicht bei Feedback-Bestätigungen."""
    return auftrag.get("status") == "erledigt" and auftrag.get("agent") != "feedback"


def ergebnis_knoepfe(auftrag: dict) -> Knoepfe:
    """Feedback-Knöpfe und Menü, nur Menü bei Fehlern, Bestätigungen und wenn der Agent sie abgewählt hat."""
    if not mit_feedback(auftrag) or v.ohne_feedback_knoepfe(auftrag):
        return MENUE_KNOPF
    return v.feedback_knoepfe(VORSATZ, auftrag["id"], MENUE_KNOPF)


def fuer_lia(auftraege: list[dict]) -> list[dict]:
    """Aufträge, die Lia als Anfragen sieht (ohne Feedback und Zurückgezogenes)."""
    return [a for a in auftraege if a.get("agent") != "feedback" and a.get("status") != "zurueckgezogen"]
