"""Adapter: uni-Recherche (recherche/geprueft.json) -> gemeinsame Wissensbasis (agentkit.recherche).

docs/recherche-plan.md, Bauschritt 3. Rein bis auf einlesen() (liest den Laufordner, schreibt wissen.json).
Kein Netz, kein Claude. Der Laufordner (data/expose/<kette>/recherche/ bzw. data/recherchen/<auftrag>/recherche/)
bleibt unverändert; der Lauf verweist mit "ordner" relativ zum Projektordner darauf.

Abbildung:
- Fragen: id, frage, anlass; gruppe = Suchfenster (literatur, methoden, ..., scopus).
- Quellen: url, titel, autoren, jahr, doi, art. DOI-Prüfung und "zitierfähig" bleiben im Laufordner.
- Belege auf Adressen: {url, zitat}. Lokale Dateien bekommen eine register-Kennung (keine Adresse):
    Norm mit Nautos-Dateiname -> "norm:<Kennung>:<Ausgabe>", z. B. "norm:DIN 4074-1:2026-05" (art norm),
    sonst                     -> "datei:<Pfad unter uni/ ohne .txt>", z. B. "datei:data/literatur/kit/x.pdf" (art werk).
  Die Seite steht im Beleg. Prüfung {status, vermerk} -> {status, grund}.
- traegt: Urteil der Gegenprüfung (gegenpruefung.json) mit fehlt; ohne Urteil "offen".
- luecken: Text (beginnt meist mit der Frage-Kennung des Laufs). widersprueche: worum, Aussage-Kennungen des Motors
  in Klammern, falls sie nicht im Text stehen. offen -> rueckfragen "F<n>: warum".
  Die Frage-Kennungen darin sind die des Laufs. Sie sind gleich denen der Basis, wenn der Lauf ein neues Projekt
  anlegt und seine Fragen lückenlos F1..Fn heißen (so schreibt recherche.eckpunkte_pruefen sie); einlesen() prüft das.
- Lauf: art suche, usd aus stand.json, modell opus, auftrag = Kette bzw. Auftrag.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from agentkit import recherche as wissen

import normen

MODELL = "opus"  # recherche.durchfuehren läuft mit art "anspruchsvoll"


def _datei_schluessel(datei: str) -> dict:
    """Quelle für einen lokalen Beleg (siehe Modulkopf)."""
    ohne_txt = datei.removesuffix(".txt")
    name = normen.aus_dateiname(Path(ohne_txt).name) if datei.startswith("data/normen/") else None
    if name:
        kennung = f"{name[0]}:{name[1]}"
        return {"register": f"norm:{kennung}", "titel": kennung, "art": "norm"}
    return {"register": f"datei:{ohne_txt}", "titel": Path(ohne_txt).stem, "art": "werk"}


def _beleg(b: dict) -> dict:
    p = b.get("pruefung") or {}
    pruefung = {"status": p.get("status", "ungeprueft"), "grund": p.get("vermerk", "")}
    if b.get("datei"):
        ort = {"register": _datei_schluessel(b["datei"])["register"]}
    else:
        ort = {"url": b["url"]}
    return {**ort, "zitat": b.get("zitat", ""), "seite": b.get("seite"), "pruefung": pruefung}


def _widerspruch(w) -> str:
    if not isinstance(w, dict):
        return str(w)
    text = str(w.get("worum", "")).strip()
    fehlen = [i for i in w.get("ids", []) if i not in text]
    return f"{text} ({', '.join(fehlen)})" if fehlen else text


def eintraege(geprueft: dict, gegen: dict | None = None) -> dict:
    """Eingang für agentkit.recherche.einarbeiten aus geprueft.json (und gegenpruefung.json, falls vorhanden)."""
    urteile = {u["id"]: u for u in (gegen or {}).get("urteile", [])}
    fragen = [{"id": f["id"], "frage": f["frage"], "anlass": f.get("anlass", ""), "gruppe": f.get("fenster", "")}
              for f in geprueft["fragen"]]
    quellen = [{"url": q["url"], "titel": q.get("titel", ""), "autoren": q.get("autoren", []),
                "jahr": q.get("jahr"), "doi": q.get("doi"), "art": q.get("art", "")}
               for q in geprueft["quellen"] if q.get("url")]
    lokal = {}
    aussagen = []
    for a in geprueft["aussagen"]:
        for b in a.get("belege", []):
            if b.get("datei"):
                q = _datei_schluessel(b["datei"])
                lokal.setdefault(q["register"], q)
        u = urteile.get(a.get("id"))
        traegt = {"urteil": u["traegt"], "fehlt": u.get("fehlt", "")} if u else None
        aussagen.append({"frage": a.get("frage"), "art": a.get("art") or "tatsache", "text": a["text"],
                         "belege": [_beleg(b) for b in a.get("belege", [])], "traegt": traegt, "fall": None})
    rueckfragen = [f"{o['frage']}: {o['warum']}" if o.get("frage") else str(o.get("warum", ""))
                   for o in geprueft.get("offen", []) if isinstance(o, dict)]
    return {"fragen": fragen, "quellen": quellen + list(lokal.values()), "aussagen": aussagen,
            "luecken": [x["text"] if isinstance(x, dict) else str(x) for x in geprueft.get("luecken", [])],
            "widersprueche": [_widerspruch(w) for w in geprueft.get("widersprueche", [])],
            "rueckfragen": rueckfragen}


def zusammenfassung(geprueft: dict, usd: float | None) -> str:
    """Eine Zeile wie die Ergebniszeile von recherche.durchfuehren."""
    z = geprueft.get("zahlen", {})
    text = (f"{len(geprueft['fragen'])} Fragen, {len(geprueft['aussagen'])} Aussagen ({z.get('gesichert', 0)} "
            f"gesichert, {z.get('teilweise', 0)} teilweise, {z.get('verworfen', 0)} verworfen, "
            f"{z.get('unbelegt', 0)} unbelegt, {z.get('einschaetzung', 0)} Einschätzungen), "
            f"{z.get('quellen_zitierfaehig', 0)} zitierfähige Quellen")
    suche = geprueft.get("literatursuche")
    if suche:
        text += (f"; {suche.get('datenbank', 'Literatursuche')} {suche.get('datum', '')}: "
                 f"{len(suche.get('suchen', []))} Suchen, {suche.get('arbeiten_ohne_doppelte', '?')} Arbeiten")
    if usd is not None:
        text += f"; {usd:.2f} USD"
    return text + "."


def lauf_angaben(stand: dict | None, auftrag: str, ordner: str, datum: str, geprueft: dict) -> dict:
    usd = (stand or {}).get("usd")
    return {"art": "suche", "datum": datum, "usd": usd, "modell": MODELL, "auftrag": auftrag, "ordner": ordner,
            "zusammenfassung": zusammenfassung(geprueft, usd)}


def _lies(pfad: Path):
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else None


def einlesen(hier: Path, laufordner: Path, auftrag: str, projekt_id: str, titel: str, **kopf) -> tuple[Path, dict]:
    """Legt data/projekte/<projekt_id>/wissen.json aus einem fertigen Laufordner (mit geprueft.json) an.
    Nur für ein neues Projekt; gibt es wissen.json schon, RechercheFehler (nichts doppelt einlesen).
    Datum des Laufs: Änderungszeit von stand.json (Ende der Läufe), sonst von geprueft.json."""
    hier, laufordner = Path(hier).resolve(), Path(laufordner).resolve()
    geprueft = _lies(laufordner / "geprueft.json")
    if geprueft is None:
        raise wissen.RechercheFehler([f"{laufordner}/geprueft.json fehlt"])
    projekt = hier / "data" / "projekte" / projekt_id
    ziel = projekt / wissen.WISSEN
    if ziel.exists():
        raise wissen.RechercheFehler([f"{ziel} gibt es schon"])
    stand_pfad = laufordner / "stand.json"
    zeit = (stand_pfad if stand_pfad.exists() else laufordner / "geprueft.json").stat().st_mtime
    datum = datetime.fromtimestamp(zeit).astimezone().isoformat(timespec="seconds")
    ordner = Path("..", "..", laufordner.relative_to(hier / "data")).as_posix()
    basis = wissen.neu(projekt_id, titel, "jan", "uni", thema=geprueft.get("thema", ""), **kopf)
    lauf = wissen.einarbeiten(basis, lauf_angaben(_lies(stand_pfad), auftrag, ordner, datum, geprueft),
                              eintraege(geprueft, _lies(laufordner / "gegenpruefung.json")))
    if [f["id"] for f in basis["fragen"]] != [f["id"] for f in geprueft["fragen"]]:
        raise wissen.RechercheFehler(["Frage-Kennungen der Basis weichen vom Lauf ab (doppelte Frage?), "
                                      "Lücken und Rückfragen würden falsch zeigen"])
    wissen.speichern(ziel, basis)
    return ziel, lauf


if __name__ == "__main__":
    # .venv/bin/python rechercheprojekt.py <laufordner> <auftrag> <projekt-id> <titel>
    pfad, eintrag = einlesen(Path(__file__).parent, Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4])
    print(pfad)
    print(json.dumps(wissen.zahlen(wissen.laden(pfad)), ensure_ascii=False))
