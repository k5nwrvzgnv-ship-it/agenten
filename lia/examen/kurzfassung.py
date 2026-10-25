"""Für Lia: Kurzfassung einer Runde (Skizzen + Prüfer-Kernsatz) und Bewertungsbogen, beide als docx.

Plan Examensreihe, Schritt 5 (Jan 25.10.2026): Der ausführliche bericht.md ist zu lang zum Bewerten. Die
Kurzfassung zeigt je Skizze Grundentscheidung, Reihenfrage, Abschlussaufgabe, Stundenübersicht, Differenzierung,
Risiken und den Kernsatz des Prüfers. Der Bogen fragt je Skizze Note, Störendes, Übernehmenswertes, dann die Wahl,
die Annahmen und noch offene Angaben aus examen.toml. Beides ohne Claude, gebaut über shared/renderer.
Aufruf: .venv/bin/python kurzfassung.py  (Runde 1, Dateien nach data/reihe/runde-1/fuer-lia/, neue Version)
"""

import json
import re
import sys
import tomllib
from pathlib import Path

import grundlagen
import pruefer
import skizzen
import versionen

HIER = Path(__file__).resolve().parent
PROFIL = HIER / "profil.toml"
MAX_ANNAHME = 180  # Zeichen je Annahme in der Kurzfassung: erster Satz, der Rest steht im Bericht

# Lesbare Namen für offene Angaben aus examen.toml (fehlt ein Name, wird der Schlüssel gezeigt)
ANGABEN = {
    "pruefung.termin": "Datum der Prüfungsstunde",
    "pruefung.abgabe_entwurf": "Abgabe des schriftlichen Entwurfs bis",
    "pruefung.stundenzahl": "Stunden der Reihe insgesamt",
    "pruefung.pruefungsstunde_in_reihe": "Die wievielte Stunde ist die Prüfungsstunde?",
    "pruefung.stundenlaenge": "Stundenlänge (45 oder 90 Minuten)",
    "pruefung.schulform": "Schulform (ISS grundlegend/erweitert oder Gymnasium)",
    "pruefung.bewertungsbogen": "Offizieller Bewertungsbogen vorhanden? (bitte schicken)",
    "pruefung.fachseminarleitung_gesehen": "Grobskizze der Fachseminarleitung gezeigt am",
    "reihe.reihenfrage": "Deine Reihenfrage (falls schon klar)",
    "reihe.seminarvorgaben_reihenfrage": "Vorgaben des Seminars zur Reihenfrage (bitte schicken)",
}
NICHT_FRAGEN = {"impuls.eingesetzt_am", "impuls.ergebnis"}  # kommen später, nicht auf diesen Bogen
# Satzende: Punkt, Leerzeichen, Großbuchstabe, aber nicht nach Abkürzungen wie „bzw.“, „z. B.“, „ca.“, „S.“
_ABKUERZUNGEN = ("bzw", "z", "B", "ca", "vgl", "S", "Nr", "d", "h", "u", "a", "usw", "etc", "ggf", "Kl", "Abs")
_SATZENDE = re.compile(r"(?<![\w.])(?!(?:" + "|".join(_ABKUERZUNGEN) + r")\.)\w+[)“\"]?\.(?= [A-ZÄÖÜ„])")


def _kurz(text: str, n: int = MAX_ANNAHME) -> str:
    """Erster Satz, höchstens n Zeichen (am Wortende gekürzt, dann mit „…“)."""
    text = " ".join(text.split())
    ende = _SATZENDE.search(text)
    satz = text if not ende else text[: ende.end()]
    return satz if len(satz) <= n else satz[: n - 1].rsplit(" ", 1)[0] + " …"


def abkuerzungen(sk: dict) -> list[str]:
    """Erklärungen der GLOSSAR-Abkürzungen, die in den Skizzen vorkommen."""
    text = json.dumps(sk, ensure_ascii=False)
    return [f"{k}: {v}" for k, v in skizzen.GLOSSAR.items() if re.search(rf"\b{re.escape(k)}\b", text)]


def _fehlt(s: dict, lesehilfe: dict | None) -> list[str]:
    """Material, das es noch nicht gibt: aus der Skizze (ab Runde 2) oder aus dem Nachtrag lesehilfe.json."""
    if "material_fehlt" in s:
        return s["material_fehlt"]
    if lesehilfe:
        return lesehilfe.get("material_alle", []) + lesehilfe.get("material_fehlt", {}).get(s["kennung"], [])
    return []


def kurzfassung(sk: dict, pr: dict, rubrik: dict, runde: int, reihe: str, lesehilfe: dict | None = None) -> dict:
    """Renderer-Beschreibung (art arbeitsblatt) der Kurzfassung.

    lesehilfe: Nachtrag für Runden, deren Skizzen Fall und fehlendes Material noch nicht selbst erklären (Runde 1).
    """
    bewertung = {b["kennung"]: b for b in pr["skizzen"]}
    n = len(rubrik["kriterium"])
    bloecke = [
        {"typ": "anweisung", "text": "Lies die drei Skizzen und fülle danach den Bewertungsbogen aus."},
        {"typ": "absatz", "text": "Die Skizzen sind Varianten zur Auswahl. Bewertet hat sie ein Prüfer-Lauf gegen "
                                  f"{n} Kriterien (Seminarkriterien und Ergänzungen). Quellen mit Zitaten und je fünf "
                                  "mögliche Fragen für das Reflexionsgespräch stehen im ausführlichen Bericht."},
    ]
    if lesehilfe and lesehilfe.get("faelle"):
        bloecke.append({"typ": "ueberschrift", "text": "Die Fälle in den Skizzen", "ebene": 2})
        for f in lesehilfe["faelle"]:
            bloecke.append({"typ": "material", "titel": f["name"], "text": f["text"]})
    erklaert = abkuerzungen(sk)
    if erklaert:
        bloecke += [{"typ": "ueberschrift", "text": "Abkürzungen", "ebene": 2}, {"typ": "liste", "punkte": erklaert}]
    for s in sk["skizzen"]:
        b = bewertung[s["kennung"]]
        unter = len(pruefer.unter_schwelle(b, rubrik))
        bloecke += [
            {"typ": "neue_seite"},
            {"typ": "ueberschrift", "text": f"Skizze {s['kennung']}: {s['titel']}"},
            {"typ": "material", "titel": "Prüfer",
             "text": f"{unter} von {n} Kriterien unter „{rubrik['stufen']['mindestens']}“. "
                     f"Zuerst verbessern: {b['staerkste_schwaeche']}"},
            {"typ": "absatz", "text": f"Grundentscheidung: {s['grundentscheidung']}"},
        ]
        if s.get("fall"):
            bloecke.append({"typ": "material", "titel": "Fall", "text": s["fall"]})
        bloecke += [
            {"typ": "merksatz", "titel": "Reihenfrage:", "text": s["reihenfrage"]},
            {"typ": "absatz", "text": f"Abschlussaufgabe: {s['abschlussaufgabe']}"},
        ]
        if s.get("abschlussfall"):
            bloecke.append({"typ": "absatz", "text": f"Fall der Abschlussaufgabe: {s['abschlussfall']}"})
        bloecke += [
            # Nr. und Thema in einer Spalte: Der Renderer macht alle Spalten gleich breit.
            {"typ": "tabelle", "kopf": ["Stunde", "Ziel", "Perspektive"],
             "zeilen": [[f"{st['nr']}{' (Prüfung)' if st.get('pruefungsstunde') else ''}: {st['thema']}",
                         st["ziel"], st["perspektive"]] for st in s["stunden"]]},
            {"typ": "absatz", "text": f"Differenzierung: {s['differenzierung']}"},
            {"typ": "absatz", "text": f"Risiken: {s['risiken']}"},
        ]
        fehlt = _fehlt(s, lesehilfe)
        if fehlt:
            # In einer Zeile, damit die Skizze auf ihrer Seite bleibt
            bloecke.append({"typ": "material", "titel": "Gibt es noch nicht (müsstest du erstellen oder suchen)",
                            "text": "; ".join(fehlt)})
    if sk.get("annahmen"):
        bloecke += [{"typ": "neue_seite"},
                    {"typ": "material", "titel": "Annahmen (bitte im Bogen bestätigen oder ändern)",
                     "text": "\n".join(f"– {_kurz(a)}" for a in sk["annahmen"])}]
    return {"art": "arbeitsblatt", "titel": f"{reihe}: drei Grobskizzen (Runde {runde})", "nummer": f"R{runde}",
            "bloecke": bloecke}


def bogen(sk: dict, examen: dict, runde: int, reihe: str) -> dict:
    """Renderer-Beschreibung (art arbeitsblatt) des Bewertungsbogens."""
    aufgaben = []
    for s in sk["skizzen"]:
        k = s["kennung"]
        aufgaben += [
            {"text": f"Skizze {k} ({s['titel']}): Wie gut passt sie dir insgesamt? (1 = sehr gut, 5 = gar nicht)",
             "antwort": {"art": "ankreuzen", "optionen": ["1", "2", "3", "4", "5"]}},
            {"text": f"Was stört dich an Skizze {k}?", "antwort": {"art": "linien", "anzahl": 3}},
            {"text": f"Was willst du aus Skizze {k} übernehmen?", "antwort": {"art": "linien", "anzahl": 3}},
        ]
    aufgaben += [
        {"text": "Welche Richtung soll weiter ausgearbeitet werden?",
         "antwort": {"art": "ankreuzen", "optionen": [f"Skizze {s['kennung']}" for s in sk["skizzen"]] + ["Mischung"]}},
        {"text": "Bei Mischung: Was aus welcher Skizze?", "antwort": {"art": "linien", "anzahl": 3}},
        {"text": "Stimmen die Annahmen aus der Kurzfassung? Was ist anders?", "antwort": {"art": "linien", "anzahl": 4}},
        {"text": "Gibt es etwas, das die Agenten sich allgemein merken sollen (für alle künftigen Skizzen)?",
         "hilfe": "Daraus wird eine Regel vorgeschlagen. Sie gilt erst, wenn du sie bestätigst.",
         "antwort": {"art": "linien", "anzahl": 4}},
    ]
    bloecke = [{"typ": "anweisung", "text": "Kurz reicht. Stichworte sind in Ordnung."},
               {"typ": "aufgaben", "titel": "", "aufgaben": aufgaben}]
    offen = [a for a in grundlagen.offene_angaben(examen) if a not in NICHT_FRAGEN]
    if offen:
        bloecke += [{"typ": "ueberschrift", "text": "Noch offene Angaben", "ebene": 2},
                    {"typ": "tabelle", "kopf": ["Angabe", "Deine Antwort"], "zeilenhoehe_cm": 1.0,
                     "erste_spalte_fett": True, "zeilen": [[ANGABEN.get(a, a), ""] for a in offen]}]
    return {"art": "arbeitsblatt", "titel": f"{reihe}: Bewertungsbogen Runde {runde}", "nummer": f"B{runde}",
            "bloecke": bloecke}


def bauen(ordner: Path, examen: dict, reihe: str, runde: int = 1, renderer_bauen=None) -> list[Path]:
    """Liest skizzen.json und pruefung.json aus `ordner`, baut beide docx nach ordner/fuer-lia/."""
    if renderer_bauen is None:
        import renderer
        renderer_bauen = renderer.bauen
    sk = json.loads((ordner / "skizzen.json").read_text(encoding="utf-8"))
    pr = json.loads((ordner / "pruefung.json").read_text(encoding="utf-8"))
    profil = tomllib.loads(PROFIL.read_text(encoding="utf-8"))
    ziel = ordner / "fuer-lia"
    ziel.mkdir(exist_ok=True)
    dateien = [ziel / f"Runde {runde} - drei Grobskizzen.docx", ziel / f"Runde {runde} - Bewertungsbogen.docx"]
    nachtrag = ordner / "lesehilfe.json"
    lesehilfe = json.loads(nachtrag.read_text(encoding="utf-8")) if nachtrag.exists() else None
    beschreibungen = [kurzfassung(sk, pr, grundlagen.rubrik_laden(), runde, reihe, lesehilfe),
                      bogen(sk, examen, runde, reihe)]
    for datei, b in zip(dateien, beschreibungen, strict=True):
        renderer_bauen(b, datei, profil=profil)
    return dateien


def main() -> int:
    examen = grundlagen._toml(grundlagen.EXAMEN)
    reihe = "Examensreihe " + examen.get("reihe", {}).get("titel_in_reihen_toml", "")
    dateien = bauen(HIER / "data" / "reihe" / "runde-1", examen, reihe)
    commit = versionen.sichern(HIER / "data" / "reihe", "Runde 1: Kurzfassung und Bewertungsbogen für Lia (mit Lesehilfe)")
    for d in dateien:
        print(d)
    print(f"Version {commit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
