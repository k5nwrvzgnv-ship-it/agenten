"""Paket für eine mündliche Prüfungssimulation mit einem ElevenLabs-Sprachagenten.

Stufe 1 (Entscheidung Jan 29.10.2026): Jan richtet Konto, Stimmklon und Agent selbst im
ElevenLabs-Web ein. Dieses Skript baut nur die Dateien, die er dort einfügt, aus vorhandenem
Material, ohne Claude-Lauf:
- prompt.md            System-Prompt des Agenten (Rolle, Ablauf, Bewertung, Sprechregeln)
- begruessung.txt      erster Satz des Agenten
- wissen_themen.md     Themen des Teils nach Score mit Lernzielen, Quellen und Kartenwissen
- wissen_vorlesung.md  aufbereitete Transkripte der Vorlesung (Schwerpunkte der Prüferin)
- ANLEITUNG.md         Klickweg in ElevenLabs

Ablage in data/lernen/<modul>/elevenlabs/<teil>/ (nicht im Repo, Inhalte aus den Skripten).
Aufruf von Hand: .venv/bin/python sprachpruefung.py <modul> <teil>, z. B. holzschutz IHS
"""

import sys
from pathlib import Path

import lernmodell

HIER = Path(__file__).resolve().parent
LERNEN = HIER / "data" / "lernen"
KURSE = HIER / "data" / "kurse"

PROMPT = """# Rolle
Sie sind {pruefer}, Prüferin im Teil "{kurs}" des Moduls "{modul}".
Sie nehmen eine mündliche Übungsprüfung ab. Prüfungsform laut Modulhandbuch: {form}.
Der Prüfling übt damit für die echte Prüfung ({termin}). Den genauen Ablauf der echten Prüfung
kennt niemand sicher; behaupten Sie dazu nichts.

# Ablauf
1. Begrüßen Sie kurz und fragen Sie nach dem Thema des Vortrags.
2. Vortrag: Hören Sie zu, bis der Prüfling sagt, dass er fertig ist. Unterbrechen Sie nicht.
   Bei Pausen sagen Sie höchstens "Mhm" oder "Bitte, fahren Sie fort".
3. Fragen, etwa 15 bis 20 Minuten:
   - Beginnen Sie mit ein bis zwei Fragen zum Vortrag.
   - Dann Fragen zu den Themen unten, wichtige zuerst, reihum, nicht zweimal dasselbe.
   - Immer nur eine Frage auf einmal. Bleibt eine Antwort vage, haken Sie nach
     ("Warum?", "Woran erkennen Sie das?", "Was folgt daraus für die Sanierung?").
   - Bevorzugen Sie Fallfragen aus der Praxis, wie sie in der Vorlesung und auf der Exkursion
     vorkamen (eine Einbausituation, ein Schadensbild im Keller, eine Holzartenwahl).
   - Bilder und Proben können Sie nicht zeigen. Beschreiben Sie stattdessen das Schadensbild
     mit seinen Merkmalen und fragen Sie, was es ist und was daraus folgt.
   - Bei einem Blackout geben Sie einen kleinen Anstoß, verraten aber nicht die Lösung.
4. Abschluss: Sagen Sie, dass die Prüfung beendet ist. Dann nennen Sie eine Note nach der
   deutschen Notenskala (1,0 bis 5,0), begründen sie in zwei bis drei Sätzen, nennen die drei
   größten Lücken mit der Fundstelle aus der Wissensbasis und je einen Tipp.

# Themen nach Wichtigkeit (5 = sehr wahrscheinlich geprüft)
{themen}

# Fachliche Grundlage
- Prüfen Sie nur, was in der Wissensbasis steht (wissen_themen.md, wissen_vorlesung.md).
  Was dort in der Vorlesung betont wurde, fragen Sie bevorzugt.
- Bewerten Sie Antworten gegen die Wissensbasis. Steht etwas nicht darin, erfinden Sie keine
  Zahlen oder Normstellen. Sagen Sie dann ehrlich, dass Sie das offenlassen.
- Während der Prüfung verraten Sie keine Lösungen und loben nicht übertrieben.

# Sprechen
- Sie sprechen, Sie schreiben nicht: kurze Sätze, keine Aufzählungszeichen, keine Tabellen,
  keine Abkürzungen. Sagen Sie "Gebrauchsklasse" statt "GK", "Dauerhaftigkeitsklasse" statt
  "DKL", "DIN achtundsechzig achthundert" statt "DIN 68800".
- Siezen Sie den Prüfling. Freundlich, sachlich, wie in einer echten Prüfung.
- Bleiben Sie in der Rolle. Nur wenn der Prüfling "Pause" oder "Abbruch" sagt, unterbrechen
  Sie die Prüfung; bei "Abbruch" geben Sie gleich die Auswertung.
"""

BEGRUESSUNG = ("Guten Tag. Schön, dass Sie da sind. Wir beginnen wie besprochen mit Ihrem Vortrag. "
               "Welches Thema haben Sie mitgebracht?")

ANLEITUNG = """# ElevenLabs einrichten: Übungsprüfung {kurs}

Die Bezeichnungen im ElevenLabs-Web können sich ändern; sinngemäß:

1. Stimme klonen (Voices -> neue Stimme -> Instant Voice Clone):
   1 bis 3 Minuten Audio, in denen nur {pruefer} spricht, ohne Pausen, Fragen aus dem
   Publikum und Hall. Die Einwilligung bestätigen.
2. Agent anlegen (Agents -> neuer, leerer Agent):
   - Sprache: Deutsch.
   - Stimme: die geklonte Stimme.
   - Erste Nachricht: Inhalt von begruessung.txt.
   - System-Prompt: Inhalt von prompt.md.
   - Sprachmodell: ein starkes Modell aus der Liste (wenn vorhanden, Claude).
   - Wissensbasis: wissen_themen.md und wissen_vorlesung.md hochladen.
   - Wenn es eine Einstellung für Geduld beim Sprecherwechsel oder für die maximale Dauer
     gibt: Geduld hoch (sonst fällt der Agent in den Vortrag), Dauer etwa 40 Minuten.
3. Testen: kurzer Durchlauf mit "Abbruch" nach zwei Fragen, prüfen, ob Aussprache und
   Fachbegriffe stimmen. Fehler bei Aussprache: Regel unter "Sprechen" in prompt.md ergänzen.
4. Nach einer echten Übung: Transkript aus ElevenLabs herunterladen und per /uni an den
   uni-Agenten schicken, damit Lücken in die Lernkarten kommen.

Paket neu bauen (z. B. nach neuen Karten oder Transkripten):
.venv/bin/python sprachpruefung.py {modul_ordner} {teil}
"""


class PaketFehler(Exception):
    pass


def teil_lesen(plan: dict, teil: str) -> tuple[str, str]:
    """Aus plan["teile"][teil] ("Kurs, Prüfer") Kursname und Prüfer."""
    eintrag = plan.get("teile", {}).get(teil)
    if not eintrag:
        raise PaketFehler(f"Teil {teil} fehlt im Prüfungsplan (teile: {', '.join(plan.get('teile', {}))})")
    kurs, _, pruefer = eintrag.partition(", ")
    if not pruefer:
        raise PaketFehler(f"Teil {teil}: Eintrag '{eintrag}' hat nicht die Form 'Kurs, Prüfer'")
    return kurs, pruefer


def themen_des_teils(plan: dict, teil: str) -> list[dict]:
    """Themen, die der Teil prüft ("IHS" oder "IHS+SHB"), nach Score absteigend."""
    themen = [t for t in plan.get("themen", []) if teil in t.get("teil", "").split("+")]
    return sorted(themen, key=lambda t: -t.get("score", 0))


def prompt_bauen(plan: dict, teil: str) -> str:
    kurs, pruefer = teil_lesen(plan, teil)
    themen = themen_des_teils(plan, teil)
    if not themen:
        raise PaketFehler(f"Teil {teil}: keine Themen im Prüfungsplan")
    zeilen = "\n".join(f"- {t['score']}: {t['titel']}" for t in themen)
    pruefung = plan.get("pruefung", {})
    return PROMPT.format(pruefer=pruefer, kurs=kurs, modul=plan.get("modul", ""),
                         form=pruefung.get("form", "unbekannt"), termin=pruefung.get("termin", "unbekannt"),
                         themen=zeilen)


def wissen_themen(plan: dict, karten: list[dict], teil: str) -> str:
    """Je Thema Lernziele, Quellen und das Wissen der Karten als Frage und Antwort."""
    kurs, _ = teil_lesen(plan, teil)
    teile = [f"# Wissensbasis {kurs}: Themen und Kartenwissen", "",
             "Grundlage der Übungsprüfung. Bildkarten sind als Beschreibung der Merkmale enthalten.", ""]
    for t in themen_des_teils(plan, teil):
        teile += [f"## {t['titel']} (Wichtigkeit {t['score']} von 5)", ""]
        if t.get("lernziele"):
            teile.append("Lernziele:")
            teile += [f"- {z['text']} ({z['aufgabentyp']})" for z in t["lernziele"]]
            teile.append("")
        if t.get("quellen"):
            teile += ["Quellen: " + "; ".join(t["quellen"]), ""]
        for k in (k for k in karten if k.get("thema") == t["id"]):
            # Bildkarten fragen "Was ist das?" zu einem Foto; die erste Antwortzeile ist der Name
            frage = "Merkmale: " + k["antwort"].strip().splitlines()[0] if k.get("typ") == "bild" else k["frage"]
            teile += [f"### {frage}", "", k["antwort"].strip(), "", f"Fundstelle: {k['quelle']}", ""]
    return "\n".join(teile).rstrip() + "\n"


def wissen_vorlesung(kurs: str, transkripte: list[Path]) -> str:
    if not transkripte:
        raise PaketFehler(f"Keine aufbereiteten Transkripte für {kurs} (data/kurse/{kurs}/transkripte/*.md)")
    teile = [f"# Wissensbasis {kurs}: Vorlesung und Exkursion", "",
             "Aufbereitete Transkripte. Was hier betont wird, ist der Prüferin wichtig.", ""]
    for pfad in sorted(transkripte):
        teile += [pfad.read_text(encoding="utf-8").strip(), "", "---", ""]
    return "\n".join(teile).rstrip("-\n ") + "\n"


def paket_bauen(modul_ordner: Path, kurse_ordner: Path, teil: str) -> Path:
    modul = lernmodell.Modul(modul_ordner)
    plan = lernmodell.lies_json(Path(modul_ordner) / "pruefungsplan.json", None)
    if plan is None:
        raise PaketFehler(f"Kein Prüfungsplan in {modul_ordner}")
    kurs, pruefer = teil_lesen(plan, teil)
    transkripte = list((Path(kurse_ordner) / kurs / "transkripte").glob("*.md"))
    dateien = {
        "prompt.md": prompt_bauen(plan, teil),
        "begruessung.txt": BEGRUESSUNG + "\n",
        "wissen_themen.md": wissen_themen(plan, list(modul.karten.values()), teil),
        "wissen_vorlesung.md": wissen_vorlesung(kurs, transkripte),
        "ANLEITUNG.md": ANLEITUNG.format(kurs=kurs, pruefer=pruefer, modul_ordner=Path(modul_ordner).name,
                                         teil=teil),
    }
    ziel = Path(modul_ordner) / "elevenlabs" / teil
    ziel.mkdir(parents=True, exist_ok=True)
    for name, inhalt in dateien.items():
        (ziel / name).write_text(inhalt, encoding="utf-8")
    return ziel


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Aufruf: sprachpruefung.py <modul> <teil>, z. B. holzschutz IHS")
        return 2
    try:
        ziel = paket_bauen(LERNEN / argv[1], KURSE, argv[2])
    except PaketFehler as fehler:
        print(f"Fehler: {fehler}")
        return 1
    for pfad in sorted(ziel.iterdir()):
        print(f"{pfad.relative_to(HIER)}  ({pfad.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
