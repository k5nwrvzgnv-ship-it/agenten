"""Schritt 3: Szenenaufgabe, mit der die SuS das Stück im Stück selbst erfinden (Plan Jan 29.10.2026).

Claude schreibt die Renderer-Beschreibung (arbeitsblatt) direkt, im Stil von Lias Szenenaufgaben. Python prüft
sie mit renderer.pruefen; Fehler gehen einmal an Claude zurück. Eigene Sitzung mit dem Ablauf als Kurzfassung,
ohne Stücktext (kostet so einen Bruchteil einer fortgesetzten Sitzung).
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


def ablauf_kurz(ablauf: dict) -> str:
    """Bausteine des geprüften Ablaufs als Text (ohne Originaltext), damit Schritt 3 das Stück nicht braucht."""
    zeilen = []
    for b in ablauf["bausteine"]:
        zeilen.append(f"- {b['id']} (Teil {b['teil']}, {b['minuten']:g} Min, {b['art']}): {b['titel']}. {b['spielidee']}")
        if b.get("neuer_text"):
            zeilen.append("  Neuer Text: " + " ".join(b["neuer_text"].split()))
    return "\n".join(zeilen)


def prompt(ausgabe: str, vorgaben: str, grundlagen: str, ablauf: str, format_text: str, buch: list[str]) -> str:
    buchteile = "\n".join(f"- {t}" for t in buch)
    return f"""Du hilfst Lia, Lehrerin für Darstellendes Spiel. Ihr Kurs spielt eine eigene Fassung von „Der nackte
Wahnsinn“ (Michael Frayn): Eine Theatertruppe probt und spielt ein Stück im Stück, und in jedem Akt geht mehr schief.
Lia: „Unklar ist mir, wie das Stück im Stück aussehen soll – da hätte ich gern etwas Kurzes, das sich die SuS
selbst ausdenken.“

Lies zuerst mit Read: Lias Vorgaben {vorgaben} und Lias Grundlagen {grundlagen} (darin unter „Szenenaufgabe_CvO“
ihr Vorbild für Szenenaufgaben). Dazu Kapitel aus Lias Fachbuch (Kündiger, Praxis Schultheater), vor allem
Improvisation, Szenische Figurenarbeit, Konzeption und Komposition. Lies die Teile, die du brauchst, und nimm
passende Übungen oder Methoden von dort in die Aufgabe auf. Nutzt du eine, setze ans Ende des Blatts einen Absatz
„Methode nach: Kündiger, Praxis Schultheater, S. n“:
{buchteile}

Der Ablauf ihrer Fassung (schon geprüft):
{ablauf}

Aufgabe: eine Szenenaufgabe für die SuS, mit der sie das Stück im Stück selbst erfinden. Das Mini-Stück ersetzt
NACKTE TATSACHEN. Es soll etwa 3–4 Minuten dauern und so gebaut sein, dass der Ablauf oben funktioniert: Lege
fest, was das Mini-Stück enthalten muss, damit die Pannen der drei Akte möglich sind
(zum Beispiel Türen und Auftritte, ein Requisit, das verwechselt wird, ein Satz, der immer wiederkommt, eine
Figur, die oft fehlt). Nenne diese Bausteine als feste Vorgaben, alles andere erfinden die SuS (Ort, Handlung,
Figuren im Mini-Stück). Es muss einfach genug sein, dass alle es nach zwei Durchläufen auswendig können.

Stil wie Lias Szenenaufgabe: kurze Anweisung, Hinweise als Liste, klare Arbeitsschritte, du
sprichst die SuS mit „ihr“ an. Eine bis zwei Seiten. Gib eine Zeit an (z. B. eine Einheit à 60 Minuten) und
einen Tipp, wie sie anfangen (z. B. ein bewegtes Standbild als Anfang und Ende des Mini-Stücks).

Schreibe eine Beschreibung nach diesem Format als JSON in die Datei {ausgabe}. art = "arbeitsblatt", titel z. B.
„Szenenaufgabe: Unser Stück im Stück“.

{format_text}

Antworte am Ende nur mit „fertig“."""
