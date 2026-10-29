"""Schritt 3: Szenenaufgabe, mit der die SuS das Stück im Stück selbst erfinden (Plan Jan 29.10.2026).

Claude schreibt die Renderer-Beschreibung (arbeitsblatt) direkt, im Stil von Lias Szenenaufgaben. Python prüft
sie mit renderer.pruefen; Fehler gehen einmal an Claude zurück.
"""

from pathlib import Path

from renderer import pruefen as renderer_pruefen

# Claude liest nur im Agent-Ordner: die nötigen Abschnitte kommen zur Laufzeit in den Prompt (bleiben aktuell)
FORMAT = Path(__file__).resolve().parents[2] / "shared" / "renderer" / "FORMAT.md"


def format_abschnitte(pfad: Path = FORMAT) -> str:
    """Abschnitte „Allgemein“ und „Arbeitsblatt“ aus FORMAT.md."""
    text = Path(pfad).read_text(encoding="utf-8")
    anfang, ende = text.index("## Allgemein"), text.index("## Zusammenfassung")
    return text[anfang:ende].strip()


def pruefen(daten: dict) -> list[str]:
    if daten.get("art") != "arbeitsblatt":
        return ['art: "arbeitsblatt" erwartet']
    return renderer_pruefen(daten)


def prompt(ausgabe: str, vorbild: str, format_text: str) -> str:
    return f"""Gut. Jetzt Schritt 3: eine Szenenaufgabe für die SuS, mit der sie das Stück im Stück selbst erfinden.
Lia: „Unklar ist mir, wie das Stück im Stück aussehen soll – da hätte ich gern etwas Kurzes, das sich die SuS
selbst ausdenken.“

Das Mini-Stück ersetzt NACKTE TATSACHEN. Es soll etwa 3–4 Minuten dauern und so gebaut sein, dass dein Ablauf aus
Schritt 2 funktioniert: Lege fest, was das Mini-Stück enthalten muss, damit die Pannen der drei Akte möglich sind
(zum Beispiel Türen und Auftritte, ein Requisit, das verwechselt wird, ein Satz, der immer wiederkommt, eine
Figur, die oft fehlt). Nenne diese Bausteine als feste Vorgaben, alles andere erfinden die SuS (Ort, Handlung,
Figuren im Mini-Stück). Es muss einfach genug sein, dass alle es nach zwei Durchläufen auswendig können.

Stil wie Lias Szenenaufgabe (Vorbild: {vorbild}): kurze Anweisung, Hinweise als Liste, klare Arbeitsschritte, du
sprichst die SuS mit „ihr“ an. Eine bis zwei Seiten. Gib eine Zeit an (z. B. eine Einheit à 60 Minuten) und
einen Tipp, wie sie anfangen (z. B. ein bewegtes Standbild als Anfang und Ende des Mini-Stücks).

Schreibe eine Beschreibung nach diesem Format als JSON in die Datei {ausgabe}. art = "arbeitsblatt", titel z. B.
„Szenenaufgabe: Unser Stück im Stück“.

{format_text}

Antworte am Ende nur mit „fertig“."""
