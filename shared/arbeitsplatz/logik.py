"""Reine Logik des Arbeitsplatzes (ohne Netz, ohne Dateien): Baum, Brotkrumen, Dokumente an einem Ort, Schutz.

Ein Dokument ist eine Kette von Aufträgen über bezug (Ursprung zuerst), deren Ursprung am Ort liegt (Feld ort).
Nachbesserungen erben ort (agentkit.auftraege.herkunft_erben), zählen aber zur Kette ihres Ursprungs.
"""

import hmac
from urllib.parse import quote, urlsplit

from agentkit import orte

ORT_TRENNER = " › "
TITEL_LANG = 90
OHNE_TITEL = "Ohne Titel"
NICHT_GEKLAPPT = "Hat nicht geklappt"
LAEUFT = "Läuft"
FINAL = "Final"
NICHT_DOKUMENT = {"feedback"}  # Agenten, deren Aufträge keine Dokumente sind


# --- Schutz (wie shared/webapp/logik.py) -------------------------------------------------------------------------

def herkunft_passt(origin: str | None, host: str | None, sec_fetch_site: str | None) -> bool:
    """Kommt ein Formular von dieser Seite? Schutz gegen fremde Seiten im selben Browser (CSRF): Origin muss zum Host
    passen, Sec-Fetch-Site (wenn gesendet) same-origin sein."""
    if sec_fetch_site and sec_fetch_site != "same-origin":
        return False
    if not origin or not host or origin == "null":
        return False
    return urlsplit(origin).netloc == host


def formular_token(geheim: bytes) -> str:
    return hmac.new(geheim, b"arbeitsplatz-formular", "sha256").hexdigest()


def token_passt(geheim: bytes, token: str | None) -> bool:
    return bool(token) and hmac.compare_digest(formular_token(geheim), token)


def port_pruefen(wert: str | None) -> int | None:
    """ARBEITSPLATZ_PORT: Zahl von 1024 bis 65535, sonst None (dann Unix-Socket). Falsche Angabe: ValueError."""
    if not wert:
        return None
    if not wert.isdigit() or not 1024 <= int(wert) <= 65535:
        raise ValueError(f"ARBEITSPLATZ_PORT {wert!r}: Zahl von 1024 bis 65535")
    return int(wert)


def ziel_sicher(ziel: str, standard: str = "/") -> str:
    """Nur Pfade dieser Seite als Weiterleitung (kein //fremd, kein Schema)."""
    if not ziel.startswith("/") or ziel.startswith("//") or "\\" in ziel or "\n" in ziel or "\r" in ziel:
        return standard
    return ziel


# --- Baum und Brotkrumen -----------------------------------------------------------------------------------------

def ort_link(ort_id: str) -> str:
    return f"/ort/{quote(ort_id)}"


def baum_zeilen(baum: list[dict], aktiv: str | None) -> list[dict]:
    """Zeilen für den Baum links: oberste Ebene immer, darunter aufgeklappt nur der Weg zum aktiven Ort und dessen
    Unterseiten. Je Zeile {"art": "ort"|"neu", "text", "link", "tiefe", "aktiv", "ueber", "zu"} ("zu": hat
    zugeklappte Unterseiten). Nach den Unterseiten des aktiven Orts steht „+ Seite“ für diese Ebene."""
    weg = []
    if aktiv and any(k["id"] == aktiv for k in baum):
        weg = [k["id"] for k in orte.pfad(baum, aktiv)]
    zeilen = []

    def ebene(eltern: str | None, tiefe: int):
        for k in orte.kinder(baum, eltern):
            offen = k["id"] in weg
            unter = orte.kinder(baum, k["id"])
            zeilen.append({"art": "ort", "text": k["titel"], "link": ort_link(k["id"]), "tiefe": tiefe,
                           "aktiv": k["id"] == aktiv, "ueber": offen and k["id"] != aktiv,
                           "zu": bool(unter) and not offen})
            if offen:
                ebene(k["id"], tiefe + 1)
                if k["id"] == aktiv:
                    zeilen.append({"art": "neu", "text": "+ Seite", "link": f"/seite/neu?eltern={quote(k['id'])}",
                                   "tiefe": tiefe + 1})
    ebene(None, 0)
    return zeilen


def krumen(baum: list[dict], ort_id: str | None, hier: str | None = None) -> dict:
    """Brotkrumen {"teile": [{"text", "link"}], "hier": Text}. Mit ort_id die Orte bis dorthin; hier: eine Seite
    unterhalb des Orts (z. B. ein Dokument), dann ist der Ort selbst ein Link."""
    teile = [{"text": "Heute", "link": "/"}]
    weg = orte.pfad(baum, ort_id) if ort_id else []
    for k in weg:
        teile.append({"text": k["titel"], "link": ort_link(k["id"])})
    if hier is None:
        if not teile[1:]:
            return {"teile": [], "hier": "Heute"}
        letzte = teile.pop()
        return {"teile": teile, "hier": letzte["text"]}
    return {"teile": teile, "hier": kuerzen(hier, 60)}


def ort_text(baum: list[dict], ort_id: str | None) -> str:
    """„Projekt › Kapitel 3“ für Listen; unbekannter Ort: ""."""
    if not ort_id or not any(k["id"] == ort_id for k in baum):
        return ""
    return ORT_TRENNER.join(k["titel"] for k in orte.pfad(baum, ort_id))


def ziele_zum_verschieben(baum: list[dict], ort_id: str) -> list[dict]:
    """Mögliche neue Eltern für ort_id: oberste Ebene und alle sichtbaren Orte außer ihm selbst und seinen
    Unterseiten, in Baum-Reihenfolge mit Tiefe. {"id" ("" = oberste Ebene), "text", "tiefe", "jetzt"}."""
    gesperrt = orte.nachkommen(baum, ort_id) | {ort_id}
    eltern = next((k["eltern"] for k in baum if k["id"] == ort_id), None)
    ziele = [{"id": "", "text": "Oberste Ebene", "tiefe": 0, "jetzt": eltern is None}]

    def ebene(e: str | None, tiefe: int):
        for k in orte.kinder(baum, e):
            if k["id"] in gesperrt:
                continue
            ziele.append({"id": k["id"], "text": k["titel"], "tiefe": tiefe, "jetzt": k["id"] == eltern})
            ebene(k["id"], tiefe + 1)
    ebene(None, 1)
    return ziele


def kuerzen(text: str, laenge: int = TITEL_LANG) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= laenge else text[:laenge - 1].rstrip() + "…"


# --- Dokumente ---------------------------------------------------------------------------------------------------

def _ursprung(a: dict, nach_id: dict[str, dict]) -> str:
    weg = [a["id"]]
    while (b := nach_id.get(a.get("bezug") or "")) and b["id"] not in weg and b["agent"] == a["agent"]:
        weg.append(b["id"])
        a = b
    return weg[-1]


def ketten(auftraege: list[dict]) -> dict[str, list[dict]]:
    """Ursprung -> Aufträge der Kette (nach erstellt), nur Agenten, deren Aufträge Dokumente sind."""
    nach_id = {a["id"]: a for a in auftraege}
    gruppen: dict[str, list[dict]] = {}
    for a in auftraege:
        if a.get("agent") in NICHT_DOKUMENT:
            continue
        gruppen.setdefault(_ursprung(a, nach_id), []).append(a)
    return {u: sorted(k, key=lambda a: (a.get("erstellt") or "", a["id"])) for u, k in gruppen.items()}


def dateiname(pfad: str) -> str:
    return pfad.rsplit("/", 1)[-1]


def titel_von(kette: list[dict], arten_namen: dict[str, str]) -> str:
    """Name des Dokuments: daten.titel der neuesten fertigen Fassung, sonst der Name ihrer ersten Datei (ohne Endung),
    sonst Art und erstes gefülltes Feld des Ursprungs, sonst die erste Zeile des Auftrags."""
    for a in reversed(kette):
        if a.get("status") == "erledigt":
            titel = (a.get("daten") or {}).get("titel")
            if isinstance(titel, str) and titel.strip():
                return kuerzen(titel)
            if a.get("ergebnis_dateien"):
                return kuerzen(dateiname(a["ergebnis_dateien"][0]).rsplit(".", 1)[0])
    u = kette[0]
    felder = u.get("felder") or {}
    erstes = next((w for w in felder.values() if isinstance(w, str) and w.strip()), "")
    art = arten_namen.get(u.get("art") or "", "")
    if art and erstes:
        return kuerzen(f"{art}: {erstes}")
    zeile = next((z for z in (u.get("text") or "").splitlines() if z.strip()), "")
    return kuerzen(zeile) or OHNE_TITEL


def marke_von(kette: list[dict], final: dict | None) -> tuple[str, bool]:
    """(Marke, rot): Läuft, Hat nicht geklappt (rot), Final oder „Fassung n“ (n = fertige Fassungen)."""
    if any(a.get("status") == "neu" for a in kette):
        return LAEUFT, False
    fertig = [a for a in kette if a.get("status") == "erledigt"]
    letzte = kette[-1]
    if letzte.get("status") == "fehlgeschlagen":
        return NICHT_GEKLAPPT, True
    if final:
        return FINAL, False
    if not fertig:
        return ("Zurückgezogen", False) if letzte.get("status") == "zurueckgezogen" else (NICHT_GEKLAPPT, True)
    return f"Fassung {len(fertig)}", False


def dokumente(auftraege: list[dict], ort_id: str | None, arten_namen: dict[str, str],
              finals: dict[str, dict | None]) -> list[dict]:
    """Dokumente, deren Ursprung am Ort ort_id liegt (None: alle mit Ort), neueste Änderung zuerst.
    finals: Ursprung -> final-Eintrag aus agentkit.fassungen (oder None).
    Je Dokument {"id" (Ursprung), "titel", "art", "agent", "marke", "rot", "zeit", "link", "ort", "fassungen"}."""
    ergebnis = []
    for u, kette in ketten(auftraege).items():
        ursprung = kette[0]
        if ursprung["id"] != u:  # Ursprung nicht mehr da: Kette ohne Kopf, nicht zeigen
            continue
        if ort_id is None and not ursprung.get("ort"):
            continue
        if ort_id is not None and ursprung.get("ort") != ort_id:
            continue
        marke, rot = marke_von(kette, finals.get(u))
        zeit = max((a.get("abgeschlossen") or a.get("erstellt") or "") for a in kette)
        ergebnis.append({"id": u, "titel": titel_von(kette, arten_namen), "art": arten_namen.get(ursprung.get("art")
                         or "", ""), "agent": ursprung.get("agent", ""), "marke": marke, "rot": rot, "zeit": zeit,
                         "link": f"/dokument/{u}", "ort": ursprung.get("ort"),
                         "fassungen": sum(1 for a in kette if a.get("status") == "erledigt")})
    return sorted(ergebnis, key=lambda d: (d["zeit"], d["id"]), reverse=True)


def laufend(auftraege: list[dict], arten_namen: dict[str, str]) -> list[dict]:
    """Offene Aufträge aus dem Arbeitsplatz (quelle oder art gesetzt), älteste zuerst, für „Läuft gerade“."""
    nach_id = {a["id"]: a for a in auftraege}
    zeilen = []
    for a in auftraege:
        if a.get("status") != "neu" or a.get("agent") in NICHT_DOKUMENT:
            continue
        if not (a.get("art") or a.get("quelle") == "arbeitsplatz"):
            continue
        u = _ursprung(a, nach_id)
        zeilen.append({"id": a["id"], "ursprung": u, "titel": titel_von([nach_id[u], a] if u != a["id"] else [a],
                                                                         arten_namen),
                       "agent": a["agent"], "seit": a.get("erstellt") or "", "link": f"/dokument/{u}",
                       "nachbesserung": u != a["id"]})
    return sorted(zeilen, key=lambda z: z["seit"])


def zeit_kurz(iso: str, heute: str) -> str:
    """„heute 14:16“ bzw. „09.11. 14:16“ aus ISO-Zeit; heute als JJJJ-MM-TT."""
    if len(iso) < 16:
        return ""
    tag, uhr = iso[:10], iso[11:16]
    return f"heute {uhr}" if tag == heute else f"{tag[8:10]}.{tag[5:7]}. {uhr}"
