"""Schritt 2: Ablauf und Spielfassung (Plan Jan 29.10.2026).

Claude schreibt ablauf.json: Bausteine für 35–40 Minuten (Originalfragmente als Nummern, eigene Szenen mit neuem
Text), dazu Varianten zu Lias offenen Fragen und Vorschläge zur Zuspitzung. Python prüft Zeiten, Muss-Liste und
Nummern und baut daraus zwei Dokumente: den Ablauf (mit Varianten) und die Spielfassung, in der der Originaltext
wörtlich aus der Textfassung kommt. Claude tippt keinen Originaltext ab.
"""

from pathlib import Path

import karte
import stueck

ARTEN = ("original", "neu", "gemischt")
FRAGEN = {"splitting": "Figurensplitting", "akt2": "Schwerpunkt in Akt 2", "partitur": "Eigene Partitur oder Montage"}
MAX = {"titel": 80, "spielidee": 700, "neuer_text": 3000, "beschreibung": 600, "vorteile": 300, "nachteile": 300,
       "vorschlag": 600}
TOLERANZ_TEIL_MIN = 3  # so weit darf ein Teil von Lias Minutenplan abweichen
BLOCK_ZEICHEN = 4500  # Originaltext je Renderer-Block (Grenze 5000)


def _text(d: dict, feld: str, wo: str, fehler: list[str], pflicht: bool = True) -> None:
    wert = d.get(feld)
    if wert is None and not pflicht:
        return
    if not isinstance(wert, str) or not wert.strip():
        fehler.append(f"{wo}.{feld}: Text fehlt")
    elif len(wert) > MAX[feld]:
        fehler.append(f"{wo}.{feld}: höchstens {MAX[feld]} Zeichen, sind {len(wert)}")


def behalten(b: dict) -> list[int]:
    """Nummern der Originaleinheiten, die ein Baustein spielt (Stellen ohne Striche)."""
    nrs = []
    for s in b.get("stellen", []):
        striche = set(s.get("striche", []))
        nrs += [n for n in range(s["von"], s["bis"] + 1) if n not in striche]
    return nrs


def pruefen(daten: dict, einheiten: list[stueck.Einheit], muss: list[dict], rahmen: dict) -> list[str]:
    """Alle Fehler auf einmal (leer = in Ordnung)."""
    fehler: list[str] = []
    nach_nr = {e.nr: e for e in einheiten}
    muss_ids = {m["id"] for m in muss}
    plan = {t["akt"]: t["minuten"] for t in rahmen["teile"]}
    bausteine = daten.get("bausteine")
    if not isinstance(bausteine, list) or not bausteine:
        return ["bausteine: Liste erwartet"]
    ids, benutzt, muss_zaehler, minuten = set(), {}, {}, {}
    for i, b in enumerate(bausteine):
        wo = f"bausteine[{i}]"
        if not isinstance(b, dict):
            fehler.append(f"{wo}: Objekt erwartet")
            continue
        if not isinstance(b.get("id"), str) or b["id"] in ids:
            fehler.append(f"{wo}.id: fehlt oder doppelt")
        ids.add(b.get("id"))
        _text(b, "titel", wo, fehler)
        _text(b, "spielidee", wo, fehler)
        teil, art, m = b.get("teil"), b.get("art"), b.get("minuten")
        if teil not in plan:
            fehler.append(f"{wo}.teil: eins von {sorted(plan)}")
        if art not in ARTEN:
            fehler.append(f"{wo}.art: eins von {', '.join(ARTEN)}")
        if not isinstance(m, (int, float)) or not 0 < m <= 15:
            fehler.append(f"{wo}.minuten: Zahl über 0 bis 15")
            m = 0
        elif teil in plan:
            minuten[teil] = minuten.get(teil, 0) + m
        stellen = b.get("stellen", [])
        if art in ("original", "gemischt") and not stellen:
            fehler.append(f"{wo}: art {art} braucht stellen")
        if art in ("neu", "gemischt"):
            _text(b, "neuer_text", wo, fehler)
        else:
            _text(b, "neuer_text", wo, fehler, pflicht=False)
        if art == "neu" and stellen:
            fehler.append(f"{wo}: art neu hat keine stellen (sonst gemischt)")
        stellen_ok = isinstance(stellen, list)
        for j, s in enumerate(stellen if stellen_ok else []):
            sw = f"{wo}.stellen[{j}]"
            von, bis = (s.get("von"), s.get("bis")) if isinstance(s, dict) else (None, None)
            if not (isinstance(von, int) and isinstance(bis, int) and von in nach_nr and bis in nach_nr and von <= bis):
                fehler.append(f"{sw}: von und bis müssen Nummern aus dem Text sein, von <= bis")
                stellen_ok = False
                continue
            striche = s.get("striche", [])
            if not isinstance(striche, list) or any(not isinstance(n, int) or not von <= n <= bis for n in striche):
                fehler.append(f"{sw}.striche: nur Nummern zwischen {von} und {bis}")
                stellen_ok = False
                continue
            for n in range(von, bis + 1):
                if n in benutzt:
                    fehler.append(f"{sw}: [{n}] steht schon in {benutzt[n]}; jede Stelle nur einmal verwenden")
                    break
                benutzt[n] = b.get("id")
        if not stellen_ok:
            fehler.append(f"{wo}.stellen: Liste aus {{von, bis, striche}} erwartet")
        elif stellen and m:
            sprech = stueck.sprechminuten([nach_nr[n] for n in behalten(b)])
            if sprech > m:
                fehler.append(f"{wo}: Originaltext allein braucht etwa {sprech:.1f} Min Sprechzeit, geplant sind "
                              f"{m} Min. Mehr streichen (striche) oder kürzere Stellen wählen.")
        ms = b.get("muss", [])
        if not isinstance(ms, list) or any(x not in muss_ids for x in ms):
            fehler.append(f"{wo}.muss: nur ids aus Lias Liste")
        else:
            for x in ms:
                muss_zaehler[x] = muss_zaehler.get(x, 0) + 1
    summe = sum(minuten.values())
    if not rahmen["minuten_min"] <= summe <= rahmen["minuten_max"]:
        fehler.append(f"Summe der Minuten ist {summe:g}, Lias Rahmen ist {rahmen['minuten_min']}–{rahmen['minuten_max']}")
    for teil, soll in plan.items():
        ist = minuten.get(teil, 0)
        if abs(ist - soll) > TOLERANZ_TEIL_MIN:
            fehler.append(f"Teil {teil}: {ist:g} Min, Lias Plan {soll} Min (höchstens {TOLERANZ_TEIL_MIN} Min Abweichung)")
    for mid in sorted(muss_ids):
        if muss_zaehler.get(mid, 0) != 1:
            fehler.append(f"{mid} kommt {muss_zaehler.get(mid, 0)}-mal vor, genau einmal nötig")
    fehler += _varianten_pruefen(daten)
    z = daten.get("zuspitzung")
    if not isinstance(z, list) or not 3 <= len(z) <= 6:
        fehler.append("zuspitzung: 3 bis 6 Vorschläge")
    else:
        for i, v in enumerate(z):
            if not isinstance(v, dict):
                fehler.append(f"zuspitzung[{i}]: Objekt erwartet")
                continue
            _text(v, "titel", f"zuspitzung[{i}]", fehler)
            _text(v, "vorschlag", f"zuspitzung[{i}]", fehler)
    for feld in ("annahmen", "rueckfragen"):
        if not isinstance(daten.get(feld, []), list):
            fehler.append(f"{feld}: Liste von Texten erwartet")
    return fehler


def _varianten_pruefen(daten: dict) -> list[str]:
    fehler = []
    varianten = daten.get("varianten")
    if not isinstance(varianten, list):
        return ["varianten: Liste erwartet"]
    gefunden = set()
    for i, v in enumerate(varianten):
        wo = f"varianten[{i}]"
        if not isinstance(v, dict) or v.get("frage") not in FRAGEN:
            fehler.append(f"{wo}.frage: eins von {', '.join(FRAGEN)}")
            continue
        gefunden.add(v["frage"])
        optionen = v.get("optionen")
        if not isinstance(optionen, list) or len(optionen) != 2:
            fehler.append(f"{wo}.optionen: genau 2")
            continue
        for j, o in enumerate(optionen):
            if not isinstance(o, dict):
                fehler.append(f"{wo}.optionen[{j}]: Objekt erwartet")
                continue
            for feld in ("titel", "beschreibung", "vorteile", "nachteile"):
                _text(o, feld, f"{wo}.optionen[{j}]", fehler)
        if v.get("empfehlung") not in (0, 1):
            fehler.append(f"{wo}.empfehlung: 0 oder 1 (Index der empfohlenen Option)")
    for frage in FRAGEN:
        if frage not in gefunden:
            fehler.append(f"varianten: Frage {frage} fehlt")
    return fehler


def prompt(ausgabe: str, rahmen: dict) -> str:
    teile = "\n".join(f"  - teil {t['akt']}: {t['name']}, {t['minuten']} Min" for t in rahmen["teile"])
    fragen = "\n".join(f"  - {k}: {v}" for k, v in FRAGEN.items())
    return f"""Gut. Jetzt Schritt 2: der Ablauf für Lias Fassung. Du kennst Stück, Szenenkarte und Lias Vorgaben schon.

Lias Rahmen: {rahmen['minuten_min']}–{rahmen['minuten_max']} Minuten, {rahmen['spieler']} SuS, {rahmen['einheiten']}.
Ihr Zeitplan:
{teile}
Plane Bausteine (Szenen) in Spielreihenfolge. Ein Baustein ist
- "original": Originalfragmente (stellen), gespielt wie im Text, mit Strichen,
- "neu": eigene Szene ohne Originaltext (Einstieg, Publikumsaktion, Heraustreten, Chor, Durchsagen),
- "gemischt": Originalfragmente plus neuer Text.
Originaltext gibst du nur als Nummern an (stellen mit von, bis und optional striche = einzelne Nummern, die
innerhalb des Bereichs wegfallen). Python setzt den Text wörtlich ein. Schreibe keinen Originaltext ab.
Neuer Text (neuer_text) ist alles, was die SuS sprechen und nicht im Original steht: Chortext, Sätze beim
Heraustreten, Durchsagen, Texte für das Publikum. Schreibe ihn spielbar, in der Sprache von Jugendlichen, nicht
kitschig. Den Chortext am Ende schreibst du ganz aus, als Vorschlag, den die SuS umarbeiten können.

Lia sagt: „Mir ist es auch alles noch etwas zu lasch inhaltlich.“ Mach das Thema Scheitern und Angst vor dem
Scheitern stärker: Jeder Akt soll die Fallhöhe steigern, das Heraustreten aus den Rollen soll etwas über die SuS
selbst erzählen (Angst, vor Publikum zu versagen, Erwartungen, Gruppendruck), nicht nur Gags unterbrechen.
Nutze, was die SuS können (Kompositionsmethoden, chorisches Sprechen, Status, bewegte Standbilder).
Zum Stück im Stück (NACKTE TATSACHEN): Lia möchte etwas Kurzes, das sich die SuS selbst ausdenken. Plane
deshalb im Ablauf mit einem Mini-Stück, das die SuS erfinden; Originalstellen aus NACKTE TATSACHEN nur dort,
wo eine Pointe davon lebt. Die Aufgabe dafür kommt im nächsten Schritt.

Schreibe die Datei {ausgabe} (JSON, sonst nichts):
{{
  "bausteine": [
    {{"id": "B01", "teil": 0, "titel": "Kostümchoreo (höchstens 80 Zeichen)", "minuten": 3, "art": "neu",
      "spielidee": "Wie es gespielt wird: Raum, Publikum, Mittel wie Freeze, Chor, Status (höchstens 700 Zeichen)",
      "neuer_text": "...", "muss": ["M0-1"]}},
    {{"id": "B02", "teil": 1, "titel": "...", "minuten": 2.5, "art": "original",
      "spielidee": "...", "stellen": [{{"von": 13, "bis": 40, "striche": [21, 22]}}], "muss": ["M1-1"]}}
  ],
  "varianten": [
    {{"frage": "splitting", "optionen": [
      {{"titel": "...", "beschreibung": "höchstens 600 Zeichen", "vorteile": "höchstens 300", "nachteile": "höchstens 300"}},
      {{"titel": "...", "beschreibung": "...", "vorteile": "...", "nachteile": "..."}}], "empfehlung": 0}}
  ],
  "zuspitzung": [{{"titel": "...", "vorschlag": "Was genau, wo im Ablauf (Baustein-id), was es bewirkt (höchstens 600 Zeichen)"}}],
  "annahmen": ["z. B. Frederick spielt mit, obwohl er in Lias Figurentabelle fehlt"],
  "rueckfragen": ["Fragen an Lia, die die Fassung verändern"]
}}
Regeln, die Python prüft:
- Summe der Minuten {rahmen['minuten_min']}–{rahmen['minuten_max']}, jeder Teil höchstens {TOLERANZ_TEIL_MIN} Min neben Lias Plan.
- Minuten eines Bausteins sind Spielzeit. Die reine Sprechzeit des Originaltexts (130 Wörter je Minute) muss
  darunter liegen; Spiel, Pausen und Slapstick brauchen zusätzlich Zeit. Streiche also kräftig.
- Jede Nummer höchstens in einem Baustein. Jeder Punkt aus Lias Liste (M0-1 bis M3-4) genau einmal unter muss.
- varianten: genau die Fragen {", ".join(FRAGEN)}, je 2 Optionen und empfehlung (0 oder 1):
{fragen}
- zuspitzung: 3 bis 6 Vorschläge gegen „zu lasch“.
Antworte am Ende nur mit „fertig“."""


def _originalbloecke(b: dict, nach_nr: dict[int, stueck.Einheit]) -> list[dict]:
    """Originaltext eines Bausteins: Seitenangaben, Striche als Hinweis, in Blöcke bis BLOCK_ZEICHEN."""
    zeilen, seite = [], None
    for s in b.get("stellen", []):
        striche = set(s.get("striche", []))
        lauf = 0
        for n in range(s["von"], s["bis"] + 1):
            e = nach_nr[n]
            if n in striche:
                lauf += 1
                continue
            if lauf:
                zeilen.append(f"[Strich: {lauf} {'Einheit' if lauf == 1 else 'Einheiten'}]")
                lauf = 0
            if e.seite != seite:
                seite = e.seite
                zeilen.append(f"[S. {seite}]")
            zeilen.append(stueck.zeile(e))
        if lauf:
            zeilen.append(f"[Strich: {lauf} {'Einheit' if lauf == 1 else 'Einheiten'}]")
    bloecke, aktuell = [], ""
    for z in zeilen:
        if aktuell and len(aktuell) + len(z) + 1 > BLOCK_ZEICHEN:
            bloecke.append({"typ": "absatz", "text": aktuell})
            aktuell = ""
        aktuell = f"{aktuell}\n{z}" if aktuell else z[:BLOCK_ZEICHEN]
    if aktuell:
        bloecke.append({"typ": "absatz", "text": aktuell})
    return bloecke


def _teilname(rahmen: dict, teil: int) -> str:
    return next(t["name"] for t in rahmen["teile"] if t["akt"] == teil)


def _seiten(b: dict, nach_nr: dict[int, stueck.Einheit]) -> str:
    """Seiten der Stellen, gleiche und anschließende Seiten zusammengefasst (S. 8; S. 8; S. 9 -> S. 8–9)."""
    bereiche: list[list[int]] = []
    for von, bis in sorted((nach_nr[s["von"]].seite, nach_nr[s["bis"]].seite) for s in b.get("stellen", [])):
        if bereiche and von <= bereiche[-1][1] + 1:
            bereiche[-1][1] = max(bereiche[-1][1], bis)
        else:
            bereiche.append([von, bis])
    return "; ".join(karte.seiten_text(v, b) for v, b in bereiche)


def spielfassung(daten: dict, einheiten: list[stueck.Einheit], rahmen: dict, titel: str) -> dict:
    """Renderer-Beschreibung der Spielfassung: Bausteine mit Originaltext (wörtlich) und neuem Text."""
    nach_nr = {e.nr: e for e in einheiten}
    bloecke = [{"typ": "absatz", "text": "Entwurf. Originaltext wörtlich aus dem Textbuch, [S. n] = Seite, "
                                         "[Strich] = hier fällt Text weg. Neuer Text steht in den grünen Kästen."}]
    teil = None
    for b in daten["bausteine"]:
        if b["teil"] != teil:
            teil = b["teil"]
            bloecke.append({"typ": "ueberschrift", "text": _teilname(rahmen, teil)})
        bloecke.append({"typ": "ueberschrift", "text": f"{b['id']} {b['titel']} ({karte.zahl(b['minuten'])} Min)", "ebene": 2})
        bloecke.append({"typ": "absatz", "text": f"Spielidee: {b['spielidee']}"})
        bloecke += _originalbloecke(b, nach_nr)
        if b.get("neuer_text"):
            bloecke.append({"typ": "material", "titel": "Neuer Text", "text": b["neuer_text"]})
    bloecke += strichuebersicht(daten, einheiten)
    return {"art": "arbeitsblatt", "titel": f"Spielfassung (Entwurf): {titel}", "nummer": "3", "bloecke": bloecke}


def strichuebersicht(daten: dict, einheiten: list[stueck.Einheit]) -> list[dict]:
    """Welche Seiten des Originals bleiben (Baustein, behaltene Einheiten), je Akt; alles andere ist gestrichen."""
    nach_nr = {e.nr: e for e in einheiten}
    bloecke = [{"typ": "ueberschrift", "text": "Strichübersicht"},
               {"typ": "absatz", "text": "Nur diese Stellen des Originals bleiben, alles andere ist gestrichen."}]
    stellen = sorted((s["von"], s["bis"], b["id"], len(s.get("striche", [])))
                     for b in daten["bausteine"] for s in b.get("stellen", []))
    for akt in (1, 2, 3):
        teil = [e for e in einheiten if e.akt == akt]
        zeilen = [[karte.seiten_text(nach_nr[v].seite, nach_nr[b].seite), f"[{v}]–[{b}]", bid,
                   f"{b - v + 1 - st} von {b - v + 1}"]
                  for v, b, bid, st in stellen if nach_nr[v].akt == akt]
        behalten_akt = sum(int(z[3].split()[0]) for z in zeilen)
        bloecke.append({"typ": "ueberschrift", "text": f"Akt {akt} im Original: {behalten_akt} von {len(teil)} "
                                                       "Einheiten bleiben", "ebene": 2})
        if zeilen:
            bloecke.append({"typ": "tabelle", "kopf": ["Seiten", "Nummern", "Baustein", "Einheiten behalten"],
                            "zeilen": zeilen})
    return bloecke


def ablauf(daten: dict, einheiten: list[stueck.Einheit], muss: list[dict], rahmen: dict, titel: str) -> dict:
    """Renderer-Beschreibung des Ablaufs mit Zeiten, Varianten und Zuspitzung."""
    nach_nr = {e.nr: e for e in einheiten}
    summe = sum(b["minuten"] for b in daten["bausteine"])
    art = {"original": "Original", "neu": "neu", "gemischt": "gemischt"}
    # drei Spalten: der Renderer teilt die Breite gleichmäßig auf, eine eigene Spalte „Nr.“ wäre zu breit
    zeilen = [[f"{b['id']} {b['titel']}" + (f"\nDeine Punkte: {', '.join(b['muss'])}" if b.get("muss") else ""),
               karte.zahl(b["minuten"]),
               art[b["art"]] + (f"\n{_seiten(b, nach_nr)}" if b.get("stellen") else "")] for b in daten["bausteine"]]
    bloecke = [
        {"typ": "absatz", "text": f"Vorschlag für {karte.zahl(summe)} Minuten mit {rahmen['spieler']} SuS. Die Spielfassung mit "
                                  "dem ganzen Text ist eine eigene Datei."},
        {"typ": "ueberschrift", "text": "Ablauf"},
        {"typ": "tabelle", "kopf": ["Baustein", "Min.", "Art und Seiten"], "zeilen": zeilen},
        {"typ": "ueberschrift", "text": "Deine offenen Fragen"},
    ]
    for v in sorted(daten["varianten"], key=lambda v: list(FRAGEN).index(v["frage"])):
        bloecke.append({"typ": "ueberschrift", "text": FRAGEN[v["frage"]], "ebene": 2})
        for i, o in enumerate(v["optionen"]):
            empf = " (Empfehlung)" if i == v["empfehlung"] else ""
            bloecke += [{"typ": "ueberschrift", "text": f"{o['titel']}{empf}", "ebene": 3},
                        {"typ": "absatz", "text": f"{o['beschreibung']}\nDafür: {o['vorteile']}\nDagegen: {o['nachteile']}"}]
    bloecke.append({"typ": "ueberschrift", "text": "Damit es weniger lasch wird"})
    bloecke.append({"typ": "liste", "punkte": [f"{z['titel']}: {z['vorschlag']}" for z in daten["zuspitzung"]]})
    for feld, ueberschrift in (("annahmen", "Annahmen"), ("rueckfragen", "Fragen an dich")):
        if daten.get(feld):
            bloecke += [{"typ": "ueberschrift", "text": ueberschrift}, {"typ": "liste", "punkte": daten[feld]}]
    return {"art": "arbeitsblatt", "titel": f"Ablauf und Varianten: {titel}", "nummer": "2", "bloecke": bloecke}


def schreiben_text(pfad: Path, daten: dict, einheiten: list[stueck.Einheit]) -> None:
    """Spielfassung zusätzlich als reiner Text (zum Nachsehen und für spätere Runden)."""
    nach_nr = {e.nr: e for e in einheiten}
    zeilen = []
    for b in daten["bausteine"]:
        zeilen += [f"## {b['id']} {b['titel']} ({b['minuten']:g} Min, Teil {b['teil']})", f"Spielidee: {b['spielidee']}"]
        zeilen += [blk["text"] for blk in _originalbloecke(b, nach_nr)]
        if b.get("neuer_text"):
            zeilen += ["NEUER TEXT:", b["neuer_text"]]
        zeilen.append("")
    Path(pfad).write_text("\n".join(zeilen), encoding="utf-8")
