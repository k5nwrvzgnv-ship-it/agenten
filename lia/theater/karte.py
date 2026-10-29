"""Schritt 1: Szenenkarte des Originals (Plan Jan 29.10.2026).

Claude liest den nummerierten Stücktext und Lias Vorgaben und schreibt szenenkarte.json: je Akt die
Spielanlässe mit Nummernbereich, Figuren, Inhalt, Komik und Bezug zu Lias Muss-Liste. Python prüft Nummern,
Akte, Überschneidungen und die Muss-Liste, rechnet Seiten und Sprechzeit aus und baut daraus das Dokument.
"""

import json
from pathlib import Path

import stueck

FIGUREN = ("DOTTY", "GARRY", "BROOKE", "FREDERICK", "BELINDA", "SELSDON", "LLOYD", "POPPY", "TIM",
           "MRS CLACKETT", "ROGER", "VICKI", "PHILIP", "FLAVIA", "EINBRECHER", "SCHEICH")
MAX = {"titel": 80, "worum": 400, "komik": 300}
ANLAESSE_MIN, ANLAESSE_MAX = 8, 45
LUSTIG_MAX = 4  # lustige Stellen je Anlass
ZITAT_ZEICHEN = 220  # so lang wird eine lustige Stelle in der Szenenkarte gezeigt


class AntwortFehler(Exception):
    pass


def antwort_lesen(pfad: Path) -> dict:
    pfad = Path(pfad)
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise AntwortFehler(f"Claude hat {pfad.name} nicht geschrieben") from None
    except json.JSONDecodeError as e:
        raise AntwortFehler(f"{pfad.name} ist kein JSON: {e}") from None
    if not isinstance(daten, dict):
        raise AntwortFehler(f"{pfad.name}: erwartet ein Objekt")
    return daten


def nachbesserung_prompt(fehler: list[str], ausgabe: str) -> str:
    return ("Die Prüfung deiner Datei hat Fehler gefunden. Verbessere genau diese Punkte und schreibe die ganze "
            f"Datei {ausgabe} neu (gleiches Format):\n" + "\n".join(f"- {f}" for f in fehler))


def _text(d: dict, feld: str, wo: str, fehler: list[str]) -> None:
    wert = d.get(feld)
    if not isinstance(wert, str) or not wert.strip():
        fehler.append(f"{wo}.{feld}: Text fehlt")
    elif len(wert) > MAX[feld]:
        fehler.append(f"{wo}.{feld}: höchstens {MAX[feld]} Zeichen, sind {len(wert)}")


def pruefen(daten: dict, einheiten: list[stueck.Einheit], muss: list[dict]) -> list[str]:
    """Alle Fehler auf einmal (leer = in Ordnung)."""
    fehler: list[str] = []
    grenzen = stueck.akt_grenzen(einheiten)
    muss_ids = {m["id"] for m in muss}
    anlaesse = daten.get("anlaesse")
    if not isinstance(anlaesse, list) or not ANLAESSE_MIN <= len(anlaesse) <= ANLAESSE_MAX:
        return [f"anlaesse: Liste mit {ANLAESSE_MIN} bis {ANLAESSE_MAX} Spielanlässen erwartet"]
    ids, bereiche, abgedeckt = set(), [], set()
    for i, a in enumerate(anlaesse):
        wo = f"anlaesse[{i}]"
        if not isinstance(a, dict):
            fehler.append(f"{wo}: Objekt erwartet")
            continue
        if a.get("id") in ids or not isinstance(a.get("id"), str):
            fehler.append(f"{wo}.id: fehlt oder doppelt")
        ids.add(a.get("id"))
        for feld in MAX:
            _text(a, feld, wo, fehler)
        akt, von, bis = a.get("akt"), a.get("von"), a.get("bis")
        if akt not in grenzen:
            fehler.append(f"{wo}.akt: 1, 2 oder 3")
        elif not (isinstance(von, int) and isinstance(bis, int) and von <= bis):
            fehler.append(f"{wo}: von und bis müssen Nummern sein, von <= bis")
        elif not (grenzen[akt][0] <= von and bis <= grenzen[akt][1]):
            fehler.append(f"{wo}: [{von}]–[{bis}] liegt nicht in Akt {akt} ([{grenzen[akt][0]}]–[{grenzen[akt][1]}])")
        else:
            bereiche.append((von, bis, wo))
            lustig = a.get("lustige_stellen", [])
            if not isinstance(lustig, list) or len(lustig) > LUSTIG_MAX or \
                    any(not isinstance(n, int) or not von <= n <= bis for n in lustig):
                fehler.append(f"{wo}.lustige_stellen: höchstens {LUSTIG_MAX} Nummern zwischen {von} und {bis}")
        figuren = a.get("figuren")
        if not isinstance(figuren, list) or not figuren or any(f not in FIGUREN for f in figuren):
            fehler.append(f"{wo}.figuren: Liste aus {', '.join(FIGUREN)}")
        m = a.get("muss", [])
        if not isinstance(m, list) or any(x not in muss_ids for x in m):
            fehler.append(f"{wo}.muss: nur ids aus Lias Liste ({', '.join(sorted(muss_ids))})")
        else:
            abgedeckt.update(m)
    bereiche.sort()
    for (_, b1, w1), (v2, _, w2) in zip(bereiche, bereiche[1:], strict=False):
        if v2 <= b1:
            fehler.append(f"{w1} und {w2} überschneiden sich ab [{v2}]")
    nicht = daten.get("nicht_gefunden", [])
    if not isinstance(nicht, list):
        fehler.append("nicht_gefunden: Liste erwartet")
        nicht = []
    for i, n in enumerate(nicht):
        if not isinstance(n, dict) or n.get("muss") not in muss_ids or not str(n.get("grund", "")).strip():
            fehler.append(f"nicht_gefunden[{i}]: muss (id) und grund nötig")
        else:
            abgedeckt.add(n["muss"])
    offen = [m["id"] for m in muss if m["akt"] > 0 and m["id"] not in abgedeckt]
    if offen:
        fehler.append("Diese Punkte aus Lias Liste fehlen (in einem Anlass unter muss oder unter nicht_gefunden mit "
                      "Grund): " + ", ".join(offen))
    if not isinstance(daten.get("hinweise", []), list):
        fehler.append("hinweise: Liste von Texten erwartet")
    return fehler


def berechnet(a: dict, nach_nr: dict[int, stueck.Einheit]) -> dict:
    """Seiten und Sprechzeit eines geprüften Anlasses."""
    teil = [nach_nr[n] for n in range(a["von"], a["bis"] + 1)]
    return {"seite_von": teil[0].seite, "seite_bis": teil[-1].seite, "minuten": stueck.sprechminuten(teil)}


def zahl(x: float, stellen: int = 1) -> str:
    """Zahl für Lia mit Komma, ohne „,0“ am Ende."""
    return f"{x:.{stellen}f}".rstrip("0").rstrip(".").replace(".", ",") if stellen else f"{x:.0f}"


def seiten_text(von: int, bis: int) -> str:
    return f"S. {von}" if von == bis else f"S. {von}–{bis}"


def zitat(e: stueck.Einheit, n: int = ZITAT_ZEICHEN) -> str:
    z = stueck.zeile(e)
    return z if len(z) <= n else z[: n - 1].rsplit(" ", 1)[0] + " …"


def prompt(ausgabe: str, teile: list[str], vorgaben: str, grundlagen: str, schema: str, buch: list[str]) -> str:
    dateien = "\n".join(f"- {t}" for t in teile)
    buchteile = "\n".join(f"- {t}" for t in buch)
    return f"""Du hilfst Lia, Lehrerin für Darstellendes Spiel, eine eigene Fassung von „Der nackte Wahnsinn“
(Michael Frayn) für ihren Kurs zu entwickeln. Lia will nicht klassisch kürzen, sondern Spielanlässe finden, Szenen
daraus entwickeln und die lustigen Textstellen behalten. Die Rechte hat sie mit dem Verlag geklärt.

Lies zuerst vollständig (mit Read):
1. Lias Vorgaben und Ideen: {vorgaben}
2. Den Stücktext, in nummerierte Einheiten zerlegt ([Nummer] SPRECHER: Text, Regie ohne Sprecher, „--- S. n“ ist
   die Seite im Textbuch, „=== AKT n ===“ der Akt). Alle Teile lesen:
{dateien}
3. Lias Grundlagen aus dem Unterricht (was die SuS können): {grundlagen}
4. Lias Schema „Vom Text zur Szene“ (Bild): {schema}
5. Kapitel aus Lias Fachbuch (Kündiger, Praxis Schultheater: Slow Motion, Chor, Improvisation, Status,
   Figurenarbeit, Konzeption, Komposition, Ästhetik). Nutze es für Spielweisen und Übungen, nenne die Buchseite
   („Kündiger S. n“), wenn du dich darauf beziehst:
{buchteile}

Aufgabe in diesem Schritt: eine Szenenkarte des Originals. Teile jeden Akt in Spielanlässe: zusammenhängende
Abschnitte, aus denen man eine Szene entwickeln kann (eine Situation, ein Konflikt, eine Panne, ein Running Gag).
Zusammen sollen die Anlässe das Wichtige jedes Akts abdecken; Übergänge dazwischen dürfen fehlen.
Ordne jedem Punkt aus Lias Muss-Liste (ids in den Vorgaben) den Anlass zu, in dem er im Original vorkommt.
Steht ein Punkt so nicht im Original (z. B. weil er Lias eigene Idee ist), nenne ihn unter nicht_gefunden mit
einem kurzen Grund und, wenn es passt, dem Anlass, an den er anknüpfen kann.

Schreibe die Datei {ausgabe} (JSON, sonst nichts) in diesem Format:
{{
  "anlaesse": [
    {{"id": "A1-01", "akt": 1, "von": 13, "bis": 60, "titel": "Sardinen und Telefon (höchstens 80 Zeichen)",
      "figuren": ["DOTTY", "LLOYD"],
      "worum": "Was passiert, wer will was, worin liegt der Konflikt (höchstens 400 Zeichen)",
      "komik": "Warum es komisch ist, z. B. Wiederholung, Missverständnis, Statuswechsel (höchstens 300 Zeichen)",
      "muss": ["M1-1"], "lustige_stellen": [15, 22]}}
  ],
  "nicht_gefunden": [{{"muss": "M0-1", "grund": "Lias eigene Idee, im Original keine Einstiegsszene"}}],
  "hinweise": ["Beobachtungen, die für die Fassung wichtig sind, z. B. Akt 2 ist fast ohne Text"]
}}
Regeln:
- {ANLAESSE_MIN} bis {ANLAESSE_MAX} Anlässe, id-Muster A<akt>-<zweistellig>, in Textreihenfolge, ohne Überschneidung.
- von/bis sind Nummern aus dem Text, beide gehören zum genannten Akt.
- figuren nur aus: {", ".join(FIGUREN)} (Rollen im Stück im Stück zählen als eigene Namen).
- lustige_stellen: höchstens {LUSTIG_MAX} Nummern je Anlass, die Lia unbedingt behalten sollte (Pointen).
- Schreibe für Lia: kurze, klare Sätze, keine Fachbegriffe ohne Erklärung.
Antworte am Ende nur mit „fertig“."""


def beschreibung(daten: dict, einheiten: list[stueck.Einheit], muss: list[dict], titel: str) -> dict:
    """Renderer-Beschreibung (arbeitsblatt) der Szenenkarte."""
    nach_nr = {e.nr: e for e in einheiten}
    muss_text = {m["id"]: m["text"] for m in muss}
    bloecke = [
        {"typ": "absatz", "text": "Die Karte teilt das Original in Spielanlässe. Seiten wie in der Ansichtssendung des "
                                  "Verlags, Minuten sind reine Sprechzeit (130 Wörter je Minute, ohne Spiel und "
                                  "Pausen). „Deine Liste“ zeigt, welche deiner Muss-Punkte im Anlass vorkommen."},
    ]
    for akt in (1, 2, 3):
        teil = [e for e in einheiten if e.akt == akt]
        bloecke.append({"typ": "ueberschrift", "text": f"Akt {akt} im Original ({seiten_text(teil[0].seite, teil[-1].seite)}, "
                                                       f"etwa {stueck.sprechminuten(teil):.0f} Min Sprechzeit)"})
        for a in [a for a in daten["anlaesse"] if a["akt"] == akt]:
            b = berechnet(a, nach_nr)
            kopf = f"{a['id']} {a['titel']} ({seiten_text(b['seite_von'], b['seite_bis'])}, {zahl(b['minuten'])} Min)"
            zeilen = [a["worum"], f"Komik: {a['komik']}", "Figuren: " + ", ".join(a["figuren"])]
            if a.get("muss"):
                zeilen.append("Deine Liste: " + "; ".join(f"{m} {muss_text[m]}" for m in a["muss"]))
            zeilen += [f"Pointe S. {nach_nr[n].seite}: {zitat(nach_nr[n])}" for n in a.get("lustige_stellen", [])]
            bloecke += [{"typ": "ueberschrift", "text": kopf[:200], "ebene": 2},
                        {"typ": "absatz", "text": "\n".join(zeilen)[:5000]}]
    bloecke.append({"typ": "ueberschrift", "text": "Deine Liste"})
    wo: dict[str, list[str]] = {}
    for a in daten["anlaesse"]:
        for m in a.get("muss", []):
            wo.setdefault(m, []).append(a["id"])
    nicht = {n["muss"]: n["grund"] for n in daten.get("nicht_gefunden", [])}
    zeilen = [[m["id"], m["text"], ", ".join(wo.get(m["id"], [])) or nicht.get(m["id"], "eigene Szene")] for m in muss]
    bloecke.append({"typ": "tabelle", "kopf": ["Nr.", "Punkt", "Im Original"], "zeilen": zeilen, "erste_spalte_fett": True})
    if daten.get("hinweise"):
        bloecke += [{"typ": "ueberschrift", "text": "Hinweise"}, {"typ": "liste", "punkte": daten["hinweise"]}]
    return {"art": "arbeitsblatt", "titel": f"Szenenkarte: {titel}", "nummer": "1", "bloecke": bloecke}
