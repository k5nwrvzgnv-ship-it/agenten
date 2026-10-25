"""Prüflauf „trägt das Zitat die Aussage?“ für Webaufträge (Jan, 25.10.2026). Reine Funktionen.

Nach der wörtlichen Prüfung (webpruefung.py) bekommt Claude in einem günstigen Lauf (art "routine", neue
Sitzung, keine Websuche) je belegter Tatsachenaussage eine id, den Text und die bestandenen Belege (Zitat mit
URL, bei Register-Verweisen den Wortlaut der Stelle). Claude schreibt je id {traegt: ja | teilweise | nein,
fehlt: "..."}. Einschätzungen („Einschätzung: …“) werden nicht geprüft.
Folgen (anwenden): "nein" -> unbelegt (unter „Nicht belegt“ mit Grund), "teilweise" bleibt mit Vermerk
„Detail nicht belegt: …“, "ja" bleibt. Fehlende ids (auch nach einer Nachbesserung) -> „nicht geprüft“.
"""

import json
from pathlib import Path

WERTE = ("ja", "teilweise", "nein")
EINSCHAETZUNG = "Einschätzung"


class TraegtFehler(Exception):
    pass


def faelle(daten: dict, register: dict[str, dict]) -> list[dict]:
    """Je belegter Tatsachenaussage: {id, text, belege: [{quelle, zitat}]}. id = "a<i>-<j>"."""
    aus = []
    for i, a in enumerate(daten["abschnitte"]):
        for j, s in enumerate(a["aussagen"]):
            if not s.get("belegt") or s["text"].lstrip().startswith(EINSCHAETZUNG):
                continue
            belege = []
            for b in s.get("belege", []):
                if b.get("pruefung", {}).get("status") != "bestanden":
                    continue
                if "register" in b:
                    belege.append({"quelle": f"Quellenregister {b['register']}",
                                   "zitat": _register_wortlaut(b["register"], register)})
                else:
                    belege.append({"quelle": b["url"], "zitat": b["zitat"]})
            aus.append({"id": f"a{i}-{j}", "text": s["text"], "belege": belege})
    return aus


def _register_wortlaut(verweis: str, register: dict[str, dict]) -> str:
    qid, _, seite = verweis.partition(":")
    for s in register.get(qid, {}).get("stellen", []):
        if str(seite) in [str(x) for x in (s.get("seiten") or [s.get("seite")])]:
            return s["zitat"]
    return ""


def prompt(liste: list[dict], ausgabe: str) -> str:
    return f"""Aufgabe: Prüfe für jede Aussage, ob die angegebenen Zitate sie tragen. Du brauchst keine Werkzeuge
außer Write: nicht suchen, nichts im Web öffnen, keine anderen Dateien lesen. Urteile nur nach den Zitaten unten.

Für jede Aussage:
- "ja": Jede Einzelheit der Aussage (Namen, Orte, Zahlen, Daten, Urteile, Zuordnungen) steht in den Zitaten
  oder folgt unmittelbar daraus.
- "teilweise": Der Kern steht in den Zitaten, aber mindestens eine Einzelheit nicht. Nenne unter "fehlt"
  genau diese Einzelheiten.
- "nein": Die Zitate tragen den Kern der Aussage nicht. Nenne unter "fehlt", was nicht belegt ist.
Sei streng: Was nur plausibel ist oder aus deinem Wissen stammt, gilt als nicht belegt.

AUSSAGEN (JSON):
{json.dumps(liste, ensure_ascii=False, indent=1)}

Schreibe NUR in die Datei {ausgabe}, als JSON, jede id genau einmal:
{{"urteile": [{{"id": "a0-0", "traegt": "ja", "fehlt": ""}}]}}
Antworte danach mit einem Satz."""


def nachbesserung_prompt(fehler: list[str], ausgabe: str) -> str:
    return (f"Die Datei hat Fehler: {'; '.join(fehler)}. Schreibe die VOLLSTÄNDIGE Datei {ausgabe} neu, "
            "jede id genau einmal, traegt nur ja, teilweise oder nein. Antworte danach mit einem Satz.")


def lesen(pfad: Path, ids: list[str]) -> tuple[dict[str, dict], list[str]]:
    """(gültige Urteile je id, Fehler). Fehler: Datei kaputt, unbekannte, doppelte oder fehlende ids,
    ungültige Werte. Gültige Urteile werden auch bei Fehlern anderer ids zurückgegeben."""
    try:
        daten = json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return {}, [f"{Path(pfad).name} fehlt oder ist kein JSON: {e}"]
    urteile = daten.get("urteile") if isinstance(daten, dict) else None
    if not isinstance(urteile, list):
        return {}, ["Feld urteile fehlt"]
    gueltig, fehler, gesehen = {}, [], set()
    for u in urteile:
        uid = u.get("id") if isinstance(u, dict) else None
        if uid not in ids:
            fehler.append(f"unbekannte id {uid!r}")
            continue
        if uid in gesehen:
            fehler.append(f"id {uid} doppelt")
            gueltig.pop(uid, None)
            continue
        gesehen.add(uid)
        if u.get("traegt") not in WERTE:
            fehler.append(f"id {uid}: traegt {u.get('traegt')!r} ungültig")
            continue
        gueltig[uid] = {"traegt": u["traegt"], "fehlt": str(u.get("fehlt") or "").strip()}
    fehlend = [i for i in ids if i not in gesehen]
    if fehlend:
        fehler.append(f"ids fehlen: {', '.join(fehlend)}")
    return gueltig, fehler


def anwenden(daten: dict, ids: list[str], urteile: dict[str, dict]) -> dict:
    """Schreibt das Urteil in jede geprüfte Aussage (Feld traegt) und zählt. "nein" macht die Aussage unbelegt."""
    zahlen = {"ja": 0, "teilweise": 0, "nein": 0, "nicht_geprueft": 0}
    for uid in ids:
        i, j = (int(x) for x in uid[1:].split("-"))
        s = daten["abschnitte"][i]["aussagen"][j]
        u = urteile.get(uid)
        if u is None:
            s["traegt"] = {"traegt": "nicht geprüft", "fehlt": ""}
            zahlen["nicht_geprueft"] += 1
            continue
        s["traegt"] = u
        zahlen[u["traegt"]] += 1
        if u["traegt"] == "nein":
            s["belegt"] = False
    z = daten["zahlen"]
    z["belegt"] = sum(s["belegt"] for a in daten["abschnitte"] for s in a["aussagen"])
    z["unbelegt"] = z["aussagen"] - z["belegt"]
    daten["traegt_zahlen"] = zahlen
    return daten
