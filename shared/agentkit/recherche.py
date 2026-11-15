"""Gemeinsame Wissensbasis einer Recherche (docs/recherche-plan.md, Jan 15.11.2026, Bauschritt 1).

Eine Recherche ist ein Projekt: Wissensbasis (wissen.json), Läufe, Dokumente. Die Motoren (uni/recherche.py,
lia/recherche) bleiben getrennt; je Motor macht ein Adapter aus seinem Ergebnis Einträge im Eingangsformat (unten)
und gibt sie an einarbeiten(). Kein Netz, kein Claude.

Ablage je Agent: <agent>/data/projekte/<projekt-id>/wissen.json (Name WISSEN). Format siehe neu() und pruefen().

Eingangsformat für einarbeiten(basis, lauf, eintraege) (ids sind nur innerhalb dieses Laufs gültig):
  lauf      {"art": "suche|ausweiten|frage|nachpruefen|plan|dokument", "datum": iso, "usd": 2.02, "modell": "opus",
             "auftrag": "<id>", "ordner": "laeufe/1-suche", "zusammenfassung": "..."}  (nur art Pflicht)
  eintraege {"fragen":   [{"id": "F1", "frage": "...", "anlass": "", "gruppe": ""}],
             "quellen":  [{"url": "https://...", "titel": "", "autoren": [], "jahr": null, "doi": null, "art": ""}
                          oder {"register": "kant-mds-strafrecht", "titel": "..."}],
             "aussagen": [{"frage": "F1" | null, "art": "tatsache|einschaetzung|fall", "text": "...",
                           "belege": [{"url": "..." oder "register": "...", "zitat": "...", "seite": null,
                                       "pruefung": {"status": "bestanden|durchgefallen|ungeprueft", "grund": ""}}],
                           "traegt": {"urteil": "ja|teilweise|nein|offen", "fehlt": ""} | null, "fall": {...} | null}],
             "luecken": ["..."], "widersprueche": ["..."], "rueckfragen": ["..."]}
Ein Beleg auf eine Adresse ohne Eintrag unter quellen legt eine Quelle nur mit url an.

Gleiches bleibt einmal: dieselbe Adresse (ohne Fragment, ohne / am Ende, Host klein) bzw. dieselbe Register-id ist
dieselbe Quelle; dieselbe Frage (Text in Vergleichsform) dieselbe Frage; eine Aussage mit gleichem Text und
mindestens einer gemeinsamen Quelle (oder ohne Belege) dieselbe Aussage. Sie bekommt dann neue Belege dazu und die
Laufnummer in geaendert_in.

Status (wie uni/recherche.zusammenfuehren): kein bestandener Beleg -> unbelegt (art einschaetzung: einschaetzung);
bestanden und traegt ja -> gesichert, nein -> verworfen, sonst teilweise. Belege auf gesperrte Quellen zählen
nicht. Entscheidungen (verwerfen, uebernehmen, sperren, anfechten) stehen in "entscheidungen" und lassen sich
zurücknehmen; neu_berechnen() wendet die gültigen an. Gesichertes gilt als übernommen, solange niemand es verwirft
(Jan 15.11.2026).
"""

import fcntl
import re
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from . import _ablage, wortlaut

FORMAT = 1
WISSEN = "wissen.json"
FUER = ("jan", "lia")
ARTEN = ("tatsache", "einschaetzung", "fall")
STATUS = ("gesichert", "teilweise", "verworfen", "unbelegt", "einschaetzung")
SICHTUNG = ("offen", "uebernommen", "verworfen")
URTEILE = ("ja", "teilweise", "nein", "offen")
PRUEFSTATUS = ("bestanden", "durchgefallen", "ungeprueft")
LAUF_ARTEN = ("plan", "suche", "ausweiten", "frage", "nachpruefen", "dokument")
WAS = {"verwerfen": "A", "uebernehmen": "A", "anfechten": "A", "sperren": "Q"}  # Entscheidung -> Präfix des Ziels
WER = ("jan", "lia")
PROJEKT_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,79}")
_ID = re.compile(r"([FQA])([1-9][0-9]*)")

# Kostenschätzung aus gemessenen Läufen (Plan Abschnitt 3.1). von = None: nicht gemessen, bis = Grenze im Code.
# Jeder neue echte Lauf soll hier nachgetragen werden.
KOSTEN = {
    ("webauftrag", "suche", "normal"): {"von": 1.90, "bis": 2.63, "gemessen": True,
                                        "hinweis": "lia/recherche, 5 Läufe 25.10.–14.11.2026"},
    ("webauftrag", "suche", "gross"): {"von": 21.53, "bis": 21.53, "gemessen": True,
                                       "hinweis": "lia/recherche, 1 Lauf 14.11.2026 mit 3 Vertiefungen"},
    ("fallsuche", "suche", "fenster"): {"von": 6.5, "bis": 7.0, "gemessen": True,
                                        "hinweis": "lia/recherche, je Suchfenster mit zwei Durchgängen, 27.10.2026"},
    ("uni", "suche", "kurz"): {"von": None, "bis": 15.0, "gemessen": False,
                               "hinweis": "uni, nicht gemessen, Grenze im Code"},
    ("uni", "suche", "gruendlich"): {"von": 35.23, "bis": 50.0, "gemessen": True,
                                     "hinweis": "uni, Exposé-Recherche mit Scopus 02.11.2026; Grenze 50"},
    ("alle", "frage", ""): {"von": None, "bis": 0.50, "gemessen": False,
                            "hinweis": "nicht gemessen, Grenze laut Plan"},
}


class RechercheFehler(ValueError):
    """Eingang oder Wissensbasis ungültig; args[0] ist die Liste der Fehler."""


# ---------- Anlegen, Laden, Speichern ----------

def neu(projekt_id: str, titel: str, fuer: str, agent: str, **kopf) -> dict:
    """Leere Wissensbasis. kopf: weitere Angaben wie ort, fach (nur Text)."""
    basis = {"format": FORMAT, "id": projekt_id, "titel": titel, "fuer": fuer, "agent": agent, **kopf,
             "fragen": [], "quellen": [], "aussagen": [], "luecken": [], "widersprueche": [], "rueckfragen": [],
             "entscheidungen": [], "laeufe": [], "dokumente": []}
    fehler = pruefen(basis)
    if fehler:
        raise RechercheFehler(fehler)
    return basis


def laden(pfad: Path) -> dict:
    """Liest wissen.json und prüft sie; RechercheFehler, wenn sie nicht stimmt."""
    basis = _ablage.lies(Path(pfad))
    fehler = pruefen(basis)
    if fehler:
        raise RechercheFehler(fehler)
    return basis


def speichern(pfad: Path, basis: dict) -> None:
    """Prüft und schreibt atomar. Eine ungültige Basis wird nie geschrieben."""
    fehler = pruefen(basis)
    if fehler:
        raise RechercheFehler(fehler)
    Path(pfad).parent.mkdir(parents=True, exist_ok=True)
    _ablage.schreibe(Path(pfad), basis)


@contextmanager
def bearbeiten(pfad: Path):
    """Laden, ändern, speichern unter einer Sperre (Agent und Oberfläche schreiben dieselbe Datei).
    Fliegt im Block eine Ausnahme, bleibt die Datei unverändert."""
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with open(pfad.with_name(f".{pfad.name}.sperre"), "w") as sperre:
        fcntl.flock(sperre, fcntl.LOCK_EX)
        basis = laden(pfad)
        yield basis
        speichern(pfad, basis)


# ---------- Prüfen ----------

def _ids(liste: list, praefix: str, fehler: list[str]) -> set[str]:
    ids = set()
    for x in liste:
        i = x.get("id") if isinstance(x, dict) else None
        m = _ID.fullmatch(i or "")
        if not m or m.group(1) != praefix:
            fehler.append(f"ungültige id {i!r} (erwartet {praefix}<n>)")
        elif i in ids:
            fehler.append(f"id {i} doppelt")
        ids.add(i)
    return ids


def pruefen(basis) -> list[str]:
    """Fehler der Wissensbasis als Liste, leer heißt in Ordnung."""
    if not isinstance(basis, dict):
        return ["keine Wissensbasis (kein Objekt)"]
    f: list[str] = []
    if basis.get("format") != FORMAT:
        f.append(f"format muss {FORMAT} sein")
    if not PROJEKT_ID.fullmatch(str(basis.get("id", ""))):
        f.append("id fehlt oder ungültig (klein, Ziffern, Bindestrich)")
    if not str(basis.get("titel", "")).strip():
        f.append("titel fehlt")
    if basis.get("fuer") not in FUER:
        f.append(f"fuer muss {' oder '.join(FUER)} sein")
    if not str(basis.get("agent", "")).strip():
        f.append("agent fehlt")
    for feld in ("fragen", "quellen", "aussagen", "luecken", "widersprueche", "rueckfragen", "entscheidungen",
                 "laeufe", "dokumente"):
        if not isinstance(basis.get(feld), list):
            f.append(f"{feld} fehlt oder ist keine Liste")
    if f:
        return f
    fragen = _ids(basis["fragen"], "F", f)
    quellen = _ids(basis["quellen"], "Q", f)
    aussagen = _ids(basis["aussagen"], "A", f)
    laeufe = {x.get("nr") for x in basis["laeufe"] if isinstance(x, dict)}
    for n, lauf in enumerate(basis["laeufe"], 1):
        if lauf.get("nr") != n:
            f.append(f"Lauf {n}: nr muss {n} sein")
        if lauf.get("art") not in LAUF_ARTEN:
            f.append(f"Lauf {n}: art {lauf.get('art')!r} unbekannt")
    for q in basis["quellen"]:
        if not (q.get("url") or q.get("register")):
            f.append(f"{q.get('id')}: url oder register fehlt")
    for a in basis["aussagen"]:
        i = a.get("id")
        if a.get("art") not in ARTEN:
            f.append(f"{i}: art {a.get('art')!r} unbekannt")
        if not str(a.get("text", "")).strip():
            f.append(f"{i}: text fehlt")
        if a.get("frage") is not None and a.get("frage") not in fragen:
            f.append(f"{i}: Frage {a.get('frage')} gibt es nicht")
        if a.get("status") not in STATUS:
            f.append(f"{i}: status {a.get('status')!r} unbekannt")
        if a.get("sichtung") not in SICHTUNG:
            f.append(f"{i}: sichtung {a.get('sichtung')!r} unbekannt")
        if (a.get("traegt") or {}).get("urteil", "offen") not in URTEILE:
            f.append(f"{i}: traegt.urteil unbekannt")
        if a.get("lauf") not in laeufe:
            f.append(f"{i}: Lauf {a.get('lauf')} gibt es nicht")
        for b in a.get("belege", []):
            if b.get("quelle") not in quellen:
                f.append(f"{i}: Beleg auf unbekannte Quelle {b.get('quelle')}")
            if (b.get("pruefung") or {}).get("status") not in PRUEFSTATUS:
                f.append(f"{i}: Beleg ohne gültige Prüfung")
    for n, e in enumerate(basis["entscheidungen"], 1):
        praefix = WAS.get(e.get("was"))
        if praefix is None:
            f.append(f"Entscheidung {n}: was {e.get('was')!r} unbekannt")
        elif e.get("ziel") not in (aussagen if praefix == "A" else quellen):
            f.append(f"Entscheidung {n}: Ziel {e.get('ziel')} passt nicht")
        if e.get("wer") not in WER:
            f.append(f"Entscheidung {n}: wer {e.get('wer')!r} unbekannt")
    for d in basis["dokumente"]:
        if d.get("stand_lauf") not in laeufe:
            f.append(f"Dokument {d.get('nr')}: Lauf {d.get('stand_lauf')} gibt es nicht")
    return f


# ---------- Einarbeiten ----------

def url_schluessel(url: str) -> str:
    """Vergleichsform einer Adresse: ohne Fragment, Schema und Host klein, ohne / am Ende."""
    teile = urlsplit(url.strip())
    pfad = teile.path.rstrip("/")
    return urlunsplit((teile.scheme.lower(), teile.netloc.lower(), pfad, teile.query, ""))


def _text_schluessel(text: str) -> str:
    return wortlaut.normalisieren(text).casefold()


def _quelle_schluessel(x: dict) -> str:
    if x.get("register"):
        return "register:" + str(x["register"])
    if x.get("url"):
        return "url:" + url_schluessel(x["url"])
    return ""


def _naechste(liste: list, praefix: str) -> str:
    n = max((int(_ID.fullmatch(x["id"]).group(2)) for x in liste), default=0)
    return f"{praefix}{n + 1}"


def _eingang_pruefen(lauf, e) -> list[str]:
    f = []
    if not isinstance(lauf, dict) or lauf.get("art") not in LAUF_ARTEN:
        f.append(f"lauf.art muss eine von {', '.join(LAUF_ARTEN)} sein")
    if not isinstance(e, dict):
        return f + ["eintraege ist kein Objekt"]
    lokal = [x.get("id") for x in e.get("fragen", [])]
    if len(set(lokal)) != len(lokal) or not all(lokal):
        f.append("Fragen brauchen eindeutige ids")
    for x in e.get("fragen", []):
        if not str(x.get("frage", "")).strip():
            f.append(f"Frage {x.get('id')}: Text fehlt")
    for x in e.get("quellen", []):
        if not _quelle_schluessel(x):
            f.append("Quelle ohne url und register")
    for n, a in enumerate(e.get("aussagen", []), 1):
        if a.get("art") not in ARTEN:
            f.append(f"Aussage {n}: art {a.get('art')!r} unbekannt")
        if not str(a.get("text", "")).strip():
            f.append(f"Aussage {n}: text fehlt")
        if a.get("frage") is not None and a.get("frage") not in lokal:
            f.append(f"Aussage {n}: Frage {a.get('frage')} steht nicht unter fragen")
        if (a.get("traegt") or {}).get("urteil", "offen") not in URTEILE:
            f.append(f"Aussage {n}: traegt.urteil unbekannt")
        for b in a.get("belege", []):
            if not _quelle_schluessel(b):
                f.append(f"Aussage {n}: Beleg ohne url und register")
            if (b.get("pruefung") or {}).get("status") not in PRUEFSTATUS:
                f.append(f"Aussage {n}: Beleg ohne gültige Prüfung")
    return f


def einarbeiten(basis: dict, lauf: dict, eintraege: dict) -> dict:
    """Arbeitet einen Lauf in die Basis ein (ändert basis) und gibt den neuen Laufeintrag zurück.
    Bei ungültigem Eingang RechercheFehler, die Basis bleibt dann unverändert."""
    fehler = _eingang_pruefen(lauf, eintraege)
    if fehler:
        raise RechercheFehler(fehler)
    nr = len(basis["laeufe"]) + 1
    neu_ids = {"fragen": [], "quellen": [], "aussagen": []}
    geaendert, doppelt = [], 0

    quellen = {_quelle_schluessel(q): q for q in basis["quellen"]}

    def quelle(x: dict) -> str:
        k = _quelle_schluessel(x)
        if k not in quellen:
            q = {"id": _naechste(basis["quellen"], "Q"), "url": x.get("url"), "register": x.get("register"),
                 "titel": x.get("titel", ""), "autoren": x.get("autoren", []), "jahr": x.get("jahr"),
                 "doi": x.get("doi"), "art": x.get("art", ""), "gesperrt": False, "lauf": nr}
            basis["quellen"].append(q)
            quellen[k] = q
            neu_ids["quellen"].append(q["id"])
        return quellen[k]["id"]

    for x in eintraege.get("quellen", []):
        quelle(x)

    fragen = {_text_schluessel(q["frage"]): q["id"] for q in basis["fragen"]}
    frage_id = {}
    for x in eintraege.get("fragen", []):
        k = _text_schluessel(x["frage"])
        if k not in fragen:
            q = {"id": _naechste(basis["fragen"], "F"), "frage": x["frage"], "anlass": x.get("anlass", ""),
                 "gruppe": x.get("gruppe", ""), "lauf": nr}
            basis["fragen"].append(q)
            fragen[k] = q["id"]
            neu_ids["fragen"].append(q["id"])
        frage_id[x["id"]] = fragen[k]

    for x in eintraege.get("aussagen", []):
        belege = [{"quelle": quelle(b), "zitat": b.get("zitat", ""), "seite": b.get("seite"),
                   "pruefung": dict(b["pruefung"])} for b in x.get("belege", [])]
        vorhanden = _gleiche_aussage(basis["aussagen"], x["text"], {b["quelle"] for b in belege})
        if vorhanden is None:
            a = {"id": _naechste(basis["aussagen"], "A"), "frage": frage_id.get(x.get("frage")),
                 "art": x["art"], "text": x["text"], "belege": belege,
                 "traegt": dict(x.get("traegt") or {"urteil": "offen", "fehlt": ""}),
                 "status": "unbelegt", "sichtung": "offen", "fall": x.get("fall"), "lauf": nr, "geaendert_in": []}
            basis["aussagen"].append(a)
            neu_ids["aussagen"].append(a["id"])
            continue
        doppelt += 1
        belege_neu = _belege_dazu(vorhanden, belege)
        if _traegt_neu(vorhanden, x.get("traegt")) or belege_neu:
            vorhanden["geaendert_in"].append(nr)
            geaendert.append(vorhanden["id"])

    for feld in ("luecken", "widersprueche", "rueckfragen"):
        da = {_text_schluessel(_als_text(y)) for y in basis[feld]}
        for y in eintraege.get(feld, []):
            k = _text_schluessel(_als_text(y))
            if k and k not in da:
                basis[feld].append({"text": _als_text(y), "lauf": nr})
                da.add(k)

    eintrag = {"nr": nr, "art": lauf["art"], "datum": lauf.get("datum") or _ablage.jetzt(),
               "usd": lauf.get("usd"), "modell": lauf.get("modell"), "auftrag": lauf.get("auftrag"),
               "ordner": lauf.get("ordner"), "zusammenfassung": lauf.get("zusammenfassung", ""),
               "neu": neu_ids, "geaendert": geaendert, "doppelt": doppelt}
    basis["laeufe"].append(eintrag)
    neu_berechnen(basis)
    return eintrag


def _als_text(y) -> str:
    return y.get("text", "") if isinstance(y, dict) else str(y)


def _gleiche_aussage(aussagen: list, text: str, quellen: set[str]) -> dict | None:
    k = _text_schluessel(text)
    for a in aussagen:
        if _text_schluessel(a["text"]) != k:
            continue
        alte = {b["quelle"] for b in a["belege"]}
        if not quellen or not alte or quellen & alte:
            return a
    return None


def _belege_dazu(a: dict, belege: list) -> bool:
    """Neue Belege anhängen; gleicher Beleg (Quelle, Zitat) bekommt die neuere Prüfung. True bei Änderung."""
    da = {(b["quelle"], _text_schluessel(b["zitat"])): b for b in a["belege"]}
    anders = False
    for b in belege:
        alt = da.get((b["quelle"], _text_schluessel(b["zitat"])))
        if alt is None:
            a["belege"].append(b)
            anders = True
        elif alt["pruefung"] != b["pruefung"]:
            alt["pruefung"] = b["pruefung"]
            anders = True
    return anders


def _traegt_neu(a: dict, traegt: dict | None) -> bool:
    if not traegt or traegt.get("urteil", "offen") == "offen" or traegt == a["traegt"]:
        return False
    a["traegt"] = dict(traegt)
    return True


# ---------- Status und Entscheidungen ----------

def status(aussage: dict, gesperrt: set[str] = frozenset()) -> str:
    """Status aus Belegen und Urteil, ohne Entscheidungen."""
    tragend = [b for b in aussage["belege"]
               if b["pruefung"]["status"] == "bestanden" and b["quelle"] not in gesperrt]
    if not tragend:
        return "einschaetzung" if aussage["art"] == "einschaetzung" else "unbelegt"
    urteil = (aussage.get("traegt") or {}).get("urteil", "offen")
    return {"ja": "gesichert", "nein": "verworfen"}.get(urteil, "teilweise")


def gueltige_entscheidungen(basis: dict) -> list[dict]:
    return [e for e in basis["entscheidungen"] if not e.get("zurueckgenommen")]


def neu_berechnen(basis: dict) -> None:
    """Sperren, Status und Sichtung aus Belegen, Urteilen und gültigen Entscheidungen (die spätere gilt)."""
    gueltig = gueltige_entscheidungen(basis)
    gesperrt = {e["ziel"] for e in gueltig if e["was"] == "sperren"}
    for q in basis["quellen"]:
        q["gesperrt"] = q["id"] in gesperrt
    sichtung = {}
    for e in gueltig:
        if e["was"] in ("verwerfen", "uebernehmen"):
            sichtung[e["ziel"]] = "verworfen" if e["was"] == "verwerfen" else "uebernommen"
    for a in basis["aussagen"]:
        a["sichtung"] = sichtung.get(a["id"], "offen")
        a["status"] = "verworfen" if a["sichtung"] == "verworfen" else status(a, gesperrt)


def entscheiden(basis: dict, wer: str, was: str, ziel: str, grund: str = "", datum: str | None = None) -> int:
    """Trägt eine Entscheidung ein und rechnet neu. Gibt ihre Nummer (ab 1) zurück, für zuruecknehmen()."""
    praefix = WAS.get(was)
    ziele = {x["id"] for x in basis["aussagen" if praefix == "A" else "quellen"]} if praefix else set()
    if praefix is None or ziel not in ziele or wer not in WER:
        raise RechercheFehler([f"Entscheidung {was!r} auf {ziel!r} von {wer!r} geht nicht"])
    basis["entscheidungen"].append({"datum": datum or _ablage.jetzt(), "wer": wer, "was": was, "ziel": ziel,
                                    "grund": grund, "zurueckgenommen": None})
    neu_berechnen(basis)
    return len(basis["entscheidungen"])


def zuruecknehmen(basis: dict, nr: int, datum: str | None = None) -> None:
    """Nimmt Entscheidung nr zurück (bleibt mit Datum stehen) und rechnet neu."""
    if not 1 <= nr <= len(basis["entscheidungen"]) or basis["entscheidungen"][nr - 1].get("zurueckgenommen"):
        raise RechercheFehler([f"Entscheidung {nr} gibt es nicht oder sie ist schon zurückgenommen"])
    basis["entscheidungen"][nr - 1]["zurueckgenommen"] = datum or _ablage.jetzt()
    neu_berechnen(basis)


def gilt_als_uebernommen(aussage: dict) -> bool:
    """Übernommen ausdrücklich, oder gesichert und nicht verworfen (Jan 15.11.2026)."""
    return aussage["sichtung"] == "uebernommen" or (aussage["sichtung"] == "offen"
                                                     and aussage["status"] == "gesichert")


# ---------- Für Prompts und Anzeige ----------

def zahlen(basis: dict) -> dict:
    z = {s: sum(a["status"] == s for a in basis["aussagen"]) for s in STATUS}
    z["aussagen"] = len(basis["aussagen"])
    z["quellen"] = len(basis["quellen"])
    z["gesperrt"] = sum(q["gesperrt"] for q in basis["quellen"])
    z["offen_gesichtet"] = sum(a["sichtung"] == "offen" for a in basis["aussagen"])
    z["usd"] = round(sum(lauf.get("usd") or 0 for lauf in basis["laeufe"]), 4)
    return z


def _quelle_text(q: dict) -> str:
    return f"Register {q['register']}" if q.get("register") else q["url"]


def bestand_text(basis: dict) -> str:
    """Kompakte Liste des Bestands für den Prompt eines neuen Laufs (Ausweiten, Fragen), ohne Zitate."""
    zeilen = [f"Bestand der Recherche „{basis['titel']}“ ({len(basis['laeufe'])} Läufe):", "", "Fragen:"]
    zeilen += [f"- {q['id']}: {q['frage']}" for q in basis["fragen"]] or ["- (keine)"]
    zeilen += ["", "Quellen (schon bekannt):"]
    zeilen += [f"- {q['id']}: {_quelle_text(q)}" for q in basis["quellen"] if not q["gesperrt"]] or ["- (keine)"]
    zeilen += ["", "Aussagen:"]
    for a in basis["aussagen"]:
        if a["status"] == "verworfen":
            continue
        qs = ", ".join(sorted({b["quelle"] for b in a["belege"]})) or "ohne Beleg"
        zeilen.append(f"- {a['id']} [{a['status']}] {a['text']} ({qs})")
    if len(zeilen) and zeilen[-1] == "Aussagen:":
        zeilen.append("- (keine)")
    verworfen = [a for a in basis["aussagen"] if a["status"] == "verworfen"]
    gesperrt = [q for q in basis["quellen"] if q["gesperrt"]]
    if verworfen or gesperrt:
        zeilen += ["", "Nicht wieder vorschlagen:"]
        zeilen += [f"- verworfen: {a['text']}" for a in verworfen]
        zeilen += [f"- gesperrte Quelle: {_quelle_text(q)}" for q in gesperrt]
    if basis["luecken"]:
        zeilen += ["", "Bekannte Lücken:"] + [f"- {x['text']}" for x in basis["luecken"]]
    return "\n".join(zeilen)


def kosten_schaetzen(motor: str, art: str, aufwand: str = "") -> dict | None:
    """Schätzung aus KOSTEN; ausweiten wie suche gleichen Aufwands, frage für alle Motoren. None: unbekannt."""
    if art == "frage":
        return KOSTEN.get(("alle", "frage", ""))
    return KOSTEN.get((motor, "suche" if art == "ausweiten" else art, aufwand))
