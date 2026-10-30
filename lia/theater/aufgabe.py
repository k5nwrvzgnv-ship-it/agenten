"""Schritt 3: Szenenaufgabe, mit der die SuS das Stück im Stück selbst erfinden (Plan Jan 29.10.2026).

Claude schreibt die Renderer-Beschreibung (arbeitsblatt) direkt, im Stil von Lias Szenenaufgaben. Python prüft
sie mit renderer.pruefen; Fehler gehen einmal an Claude zurück. Läuft in der Sitzung von Szenenkarte und Ablauf;
der Prompt enthält den Ablauf als Kurzfassung, damit er auch in einer neuen Sitzung reicht (fortgesetzte Runde).
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


# Szenenaufgabe auf Lias Auftrag aus der Web-App („Szenenaufgabe: …“, Plan Jan 30.10.2026): ein Arbeitsblatt für
# eine Gruppe. Originaltext tippt Claude nicht ab, sondern nennt Nummern; Python hängt den Text wörtlich an.
TEXT_MAX_EINHEITEN = 150  # so viel Originaltext höchstens auf einem Blatt


def szenen_pruefen(daten: dict, anzahl: int) -> list[str]:
    """Antwort {"blatt": arbeitsblatt, "text_aus_dem_stueck": [{"von": n, "bis": m}, ...]}; anzahl = Einheiten."""
    if not isinstance(daten.get("blatt"), dict):
        return ["blatt fehlt (die Beschreibung des Arbeitsblatts)"]
    fehler = pruefen(daten["blatt"])
    stellen = daten.get("text_aus_dem_stueck", [])
    if not isinstance(stellen, list):
        return fehler + ["text_aus_dem_stueck muss eine Liste sein"]
    summe = 0
    for i, s in enumerate(stellen, 1):
        von, bis = (s.get("von"), s.get("bis")) if isinstance(s, dict) else (None, None)
        if not (isinstance(von, int) and isinstance(bis, int) and 1 <= von <= bis <= anzahl):
            fehler.append(f"text_aus_dem_stueck {i}: von/bis müssen Nummern 1–{anzahl} sein, von <= bis")
            continue
        summe += bis - von + 1
    if summe > TEXT_MAX_EINHEITEN:
        fehler.append(f"text_aus_dem_stueck: {summe} Einheiten, höchstens {TEXT_MAX_EINHEITEN}")
    return fehler


def mit_text(daten: dict, originalbloecke) -> dict:
    """Arbeitsblatt mit dem Originaltext am Ende. originalbloecke(stellen) -> Blöcke (fassung._originalbloecke)."""
    blatt = dict(daten["blatt"], bloecke=list(daten["blatt"]["bloecke"]))
    stellen = daten.get("text_aus_dem_stueck") or []
    if stellen:
        blatt["bloecke"] += [{"typ": "ueberschrift", "text": "Text aus dem Stück"}] + originalbloecke(stellen)
    return blatt


def szenen_prompt(ausgabe: str, auftrag: str, vorgaben: str, grundlagen: str, teile: list[str], ablauf: str,
                  spielfassung: str, anhaenge: list[str], format_text: str, buch: list[str],
                  vorher: str | None = None) -> str:
    """vorher: Beschreibung einer früheren Szenenaufgabe; dann ist auftrag Lias Rückmeldung dazu."""
    liste = lambda xs: "\n".join(f"- {x}" for x in xs)  # noqa: E731
    anhang = (f"\nLia hat Material angehängt (gehört zu diesem Auftrag):\n{liste(anhaenge)}\n" if anhaenge else "")
    worum = (f"Lia hat eine Szenenaufgabe von dir bekommen ({vorher}, lies sie zuerst) und meldet zurück. Überarbeite "
             "sie danach; was Lia nicht anspricht, bleibt. Ihre Rückmeldung, wörtlich:" if vorher else
             "Lia möchte eine Szenenaufgabe für eine Gruppe. Ihr Auftrag, wörtlich:")
    return f"""Du hilfst Lia, Lehrerin für Darstellendes Spiel. Ihr Kurs spielt eine eigene Fassung von „Der nackte
Wahnsinn“ (Michael Frayn). {worum}

{auftrag}
{anhang}
Lies zuerst mit Read: Lias Vorgaben {vorgaben}, ihre Grundlagen {grundlagen} (darin unter „Szenenaufgabe_CvO“ ihr
Vorbild für Szenenaufgaben) und die aktuelle Spielfassung {spielfassung}. Das Stück in nummerierten Einheiten
([n] vor jeder Einheit), lies die Teile, die du für die Szene brauchst:
{liste(teile)}
Kapitel aus Lias Fachbuch (Kündiger, Praxis Schultheater). Passt eine Methode oder Übung von dort, nimm sie auf und
setze ans Ende des Blatts einen Absatz „Methode nach: Kündiger, Praxis Schultheater, S. n“:
{liste(buch)}

Der aktuelle Ablauf ihrer Fassung (Bausteine B.., wie Lia sie kennt):
{ablauf}

Aufgabe: ein Arbeitsblatt für die Gruppe, mit der Methode, der Szene und dem Material aus Lias Auftrag. Stil wie
Lias Szenenaufgabe: kurze Anweisung, Hinweise als Liste, klare Arbeitsschritte mit Zeitangaben, du sprichst die
SuS mit „ihr“ an, ein bis zwei Seiten. Fehlt im Auftrag etwas (z. B. die Gruppengröße), triff eine sinnvolle Wahl
und nenne sie im Blatt.

Originaltext tippst du nicht ab. Braucht die Gruppe Text aus dem Stück, nenne die Nummern in
„text_aus_dem_stueck“; Python setzt den Text wörtlich unter die Überschrift „Text aus dem Stück“ ans Ende des
Blatts (höchstens {TEXT_MAX_EINHEITEN} Einheiten). Kurze Zitate (ein Satz) im Blatt sind in Ordnung.

Schreibe JSON in die Datei {ausgabe}:
{{"blatt": <Beschreibung nach dem Format unten, art = "arbeitsblatt", titel beginnt mit „Szenenaufgabe:“>,
  "text_aus_dem_stueck": [{{"von": 1201, "bis": 1234}}]}}
(leere Liste, wenn kein Originaltext nötig ist)

{format_text}

Antworte am Ende nur mit „fertig“."""
