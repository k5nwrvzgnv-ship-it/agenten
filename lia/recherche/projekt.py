"""Webaufträge als Recherche-Projekte (docs/recherche-plan.md, Bauschritt 2, Jan 15.11.2026).

Adapter vom Format des Webauftrags (data/web/<id>/geprueft.json) zum Eingangsformat von
agentkit.recherche.einarbeiten. Die Ordner der Läufe bleiben unverändert; die Wissensbasis liegt unter
data/projekte/<projekt-id>/wissen.json, der Lauf verweist mit "ordner" auf data/web/<id> (relativ zum Agent-Ordner).

Zuordnung:
- Abschnitt -> Frage (Titel als Frage, gruppe "abschnitt"), Aussage -> Aussage mit dieser Frage.
- Text beginnt mit „Einschätzung“ -> art einschaetzung (wie traegt.py), sonst tatsache.
- Beleg {url, zitat} bleibt; {register: "<id>:<seite>"} -> register <id>, seite, Zitat = Wortlaut der Stellen
  dieser Seite aus register.json. pruefung.vermerk -> pruefung.grund.
- traegt {traegt: ja|teilweise|nein, fehlt} -> traegt {urteil, fehlt}; „nicht geprüft“ oder fehlt -> offen.
- Kosten: kosten_usd; nach einem nachträglichen Prüflauf (--nur-traegt, geprueft_vor_traegt.json daneben) hat
  geprueft.json nur dessen Kosten, dann zählt die Summe beider.

Aufruf (kein Claude-Lauf, keine Kosten):
    .venv/bin/python projekt.py --einlesen        # die vorhandenen Läufe (EINLESEN) als Projekte
    .venv/bin/python projekt.py <projekt-id> data/web/<id> [...]   # weitere Läufe in ein Projekt
Ein Ordner, der schon als Lauf im Projekt steht, wird übersprungen.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from agentkit import recherche

import agent
import register
import traegt

HIER = Path(__file__).resolve().parent
PROJEKTE = HIER / "data" / "projekte"
STANDARD_FACH = "Ethik"
MODELL = "opus"  # webauftrag: claude_lauf art "anspruchsvoll"
URTEIL = {"ja": "ja", "teilweise": "teilweise", "nein": "nein"}

# Vorhandene Läufe, je zwei in einem Projekt (Jan 15.11.2026). Titel und Fach von Hand, weil die ersten Läufe
# noch keinen Kopf (FACH, TITEL) hatten.
EINLESEN = {
    "reihe-strafe": {"titel": "Unterrichtsreihe Strafe", "fach": "Ethik", "laeufe": [
        "20261025-211339-lia-reihe-strafe", "20261025-211917-lia-reihe-strafe-v2"]},
    "theater-statuswechsel": {"titel": "Auslöser für Statuswechsel", "fach": "Darstellendes Spiel", "laeufe": [
        "20261113-194004-lia-theater-statuswechsel", "20261114-111445-lia-theater-statuswechsel-v2"]},
    "milde-jugendtaten": {"titel": "Milde Jugendtaten zum Einstieg ins Thema Strafe", "fach": "Ethik", "laeufe": [
        "20261114-130748-lia-milde-jugendtaten", "20261114-133343-lia-milde-jugendtaten-v2"]},
}

logger = agent.logger


# ---------- rein ----------

def _art(text: str) -> str:
    return "einschaetzung" if text.lstrip().startswith(traegt.EINSCHAETZUNG) else "tatsache"


def _pruefung(b: dict) -> dict:
    p = b.get("pruefung") or {}
    return {"status": p.get("status", "ungeprueft"), "grund": p.get("vermerk", p.get("grund", ""))}


def _beleg(b: dict, reg: dict[str, dict]) -> dict:
    if "register" in b:
        qid, _, seite = str(b["register"]).partition(":")
        return {"register": qid, "seite": seite or None, "zitat": traegt._register_wortlaut(b["register"], reg),
                "pruefung": _pruefung(b)}
    return {"url": b["url"], "zitat": b.get("zitat", ""), "seite": None, "pruefung": _pruefung(b)}


def _traegt(s: dict) -> dict | None:
    t = s.get("traegt")
    if not isinstance(t, dict):
        return None
    return {"urteil": URTEIL.get(t.get("traegt"), "offen"), "fehlt": t.get("fehlt", "")}


def _register_titel(e: dict) -> str:
    werk = e.get("werk", e.get("id", ""))
    return f"{e['autor']}: {werk}" if e.get("autor") else werk


def eingang(daten: dict, reg: dict[str, dict] | None = None) -> dict:
    """geprueft.json eines Webauftrags -> eintraege für recherche.einarbeiten. reg: register.laden()."""
    reg = reg or {}
    fragen, aussagen, register_ids = [], [], []
    for i, ab in enumerate(daten.get("abschnitte", []), 1):
        fid = f"F{i}"
        fragen.append({"id": fid, "frage": ab.get("titel") or f"Abschnitt {i}", "gruppe": "abschnitt"})
        for s in ab.get("aussagen", []):
            belege = [_beleg(b, reg) for b in s.get("belege", [])]
            for b in belege:
                if "register" in b and b["register"] not in register_ids:
                    register_ids.append(b["register"])
            aussagen.append({"frage": fid, "art": _art(s["text"]), "text": s["text"], "belege": belege,
                             "traegt": _traegt(s), "fall": None})
    quellen = [{"register": r, "titel": _register_titel(reg[r]) if r in reg else r, "art": "register"}
               for r in register_ids]
    return {"fragen": fragen, "quellen": quellen, "aussagen": aussagen,
            "luecken": [str(x) for x in daten.get("luecken", [])],
            "rueckfragen": [str(x) for x in daten.get("rueckfragen", [])]}


def kosten(daten: dict, vor_traegt: dict | None = None) -> float | None:
    """Kosten des Laufs. vor_traegt: geprueft_vor_traegt.json, falls der Prüflauf nachträglich lief."""
    usd = daten.get("kosten_usd")
    if vor_traegt is not None and usd is not None and vor_traegt.get("kosten_usd") is not None:
        usd = vor_traegt["kosten_usd"] + usd
    return round(usd, 4) if usd is not None else None


def lauf(ordner_name: str, daten: dict, usd: float | None) -> dict:
    """Laufangaben für einarbeiten. Datum aus dem Ordnernamen (JJJJMMTT-HHMMSS-...)."""
    try:
        datum = datetime.strptime(ordner_name[:15], "%Y%m%d-%H%M%S").isoformat()
    except ValueError:
        datum = None
    return {"art": "suche", "datum": datum, "usd": usd, "modell": MODELL,
            "auftrag": (daten.get("an_lia") or {}).get("auftrag"), "ordner": f"data/web/{ordner_name}",
            "zusammenfassung": daten.get("kern", "")}


# ---------- mit Dateien ----------

def _lies(pfad: Path) -> dict | None:
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else None


def lauf_einarbeiten(basis: dict, ordner: Path, reg: dict[str, dict]) -> dict | None:
    """Einen Webauftrags-Ordner in die Basis. None, wenn er schon als Lauf drinsteht."""
    name = ordner.name
    if any(x.get("ordner") == f"data/web/{name}" for x in basis["laeufe"]):
        return None
    daten = _lies(ordner / "geprueft.json")
    if daten is None:
        raise FileNotFoundError(f"{ordner}: kein geprueft.json")
    usd = kosten(daten, _lies(ordner / "geprueft_vor_traegt.json"))
    return recherche.einarbeiten(basis, lauf(name, daten, usd), eingang(daten, reg))


def einlesen(projekt_id: str, titel: str, fach: str, ordner: list[Path], hier: Path = HIER) -> dict:
    """Legt das Projekt an (falls neu) und arbeitet die Ordner der Reihe nach ein. Gibt die Basis zurück."""
    pfad = hier / "data" / "projekte" / projekt_id / recherche.WISSEN
    reg = register.laden(hier / "data" / "register.json")
    if not pfad.exists():
        recherche.speichern(pfad, recherche.neu(projekt_id, titel, "lia", "recherche", fach=fach))
    with recherche.bearbeiten(pfad) as basis:
        for o in ordner:
            e = lauf_einarbeiten(basis, o, reg)
            if e is None:
                logger.info("Projekt %s: %s steht schon drin", projekt_id, o.name)
            else:
                logger.info("Projekt %s: Lauf %d aus %s, neu %d Aussagen, doppelt %d", projekt_id, e["nr"],
                            o.name, len(e["neu"]["aussagen"]), e["doppelt"])
    return basis


def bericht(basis: dict) -> str:
    z = recherche.zahlen(basis)
    laeufe = "; ".join(f"Lauf {x['nr']}: neu {len(x['neu']['aussagen'])}, doppelt {x['doppelt']}, "
                       f"geändert {len(x['geaendert'])}, {x['usd']} USD" for x in basis["laeufe"])
    return (f"{basis['id']}: {z['aussagen']} Aussagen ({z['gesichert']} gesichert, {z['teilweise']} teilweise, "
            f"{z['verworfen']} verworfen, {z['unbelegt']} unbelegt, {z['einschaetzung']} Einschätzung), "
            f"{z['quellen']} Quellen, {len(basis['fragen'])} Fragen, {z['usd']} USD. {laeufe}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--einlesen", action="store_true", help="vorhandene Läufe (EINLESEN) als Projekte")
    p.add_argument("projekt", nargs="?")
    p.add_argument("ordner", nargs="*", type=Path)
    a = p.parse_args(argv)
    if a.einlesen:
        for pid, x in EINLESEN.items():
            basis = einlesen(pid, x["titel"], x["fach"], [HIER / "data" / "web" / o for o in x["laeufe"]])
            print(bericht(basis))
        return 0
    if not a.projekt or not a.ordner:
        p.error("Projekt-id und mindestens ein Ordner, oder --einlesen")
    ordner = [o.resolve() for o in a.ordner]
    kopf = (_lies(ordner[0] / "geprueft.json") or {}).get("kopf") or {}
    basis = einlesen(a.projekt, kopf.get("titel") or a.projekt, kopf.get("fach") or STANDARD_FACH, ordner)
    print(bericht(basis))
    return 0


if __name__ == "__main__":
    sys.exit(main())
