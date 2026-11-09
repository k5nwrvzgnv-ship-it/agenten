"""Reine Logik des Arbeitsplatzes (ohne Netz, ohne Dateien): Baum, Brotkrumen, Dokumente an einem Ort, Schutz.

Ein Dokument ist eine Kette von Aufträgen über bezug (Ursprung zuerst), deren Ursprung am Ort liegt (Feld ort).
Nachbesserungen erben ort (agentkit.auftraege.herkunft_erben), zählen aber zur Kette ihres Ursprungs.
"""

import hmac
import re
from urllib.parse import quote, urlsplit

from agentkit import orte
from agentkit._ablage import ID_MUSTER as ID_AUFTRAG
from agentkit.auftraege import REIHE_MUSTER as ORT_ID

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


def ort_von(ursprung: dict, zuordnung: dict[str, str]) -> str | None:
    """Ort eines Dokuments: Feld ort des Ursprungs, sonst die Zuordnung alter Ergebnisse (orte-zuordnung.json)."""
    return ursprung.get("ort") or zuordnung.get(ursprung["id"])


def zuordnung_pruefen(daten) -> dict[str, str]:
    """Inhalt von orte-zuordnung.json ({"zuordnung": {ursprung: ort}}) -> nur gültige Paare."""
    roh = daten.get("zuordnung") if isinstance(daten, dict) else None
    if not isinstance(roh, dict):
        return {}
    return {u: o for u, o in roh.items() if isinstance(u, str) and isinstance(o, str)
            and ID_AUFTRAG.match(u) and ORT_ID.fullmatch(o)}


def dokumente(auftraege: list[dict], ort_id: str | None, arten_namen: dict[str, str],
              finals: dict[str, dict | None], zuordnung: dict[str, str] | None = None) -> list[dict]:
    """Dokumente, deren Ursprung am Ort ort_id liegt (None: alle mit Ort), neueste Änderung zuerst.
    finals: Ursprung -> final-Eintrag aus agentkit.fassungen (oder None). zuordnung: siehe ort_von.
    Je Dokument {"id" (Ursprung), "titel", "art", "agent", "marke", "rot", "zeit", "link", "ort", "fassungen"}."""
    ergebnis = []
    for u, kette in ketten(auftraege).items():
        ursprung = kette[0]
        if ursprung["id"] != u:  # Ursprung nicht mehr da: Kette ohne Kopf, nicht zeigen
            continue
        ort = ort_von(ursprung, zuordnung or {})
        if ort_id is None and not ort:
            continue
        if ort_id is not None and ort != ort_id:
            continue
        marke, rot = marke_von(kette, finals.get(u))
        zeit = max((a.get("abgeschlossen") or a.get("erstellt") or "") for a in kette)
        ergebnis.append({"id": u, "titel": titel_von(kette, arten_namen), "art": arten_namen.get(ursprung.get("art")
                         or "", ""), "agent": ursprung.get("agent", ""), "marke": marke, "rot": rot, "zeit": zeit,
                         "link": f"/dokument/{u}", "ort": ort,
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


# --- Dokument-Ansicht --------------------------------------------------------------------------------------------

STATUS_TEXT = {"neu": "läuft", "erledigt": "fertig", "fehlgeschlagen": "hat nicht geklappt",
               "zurueckgezogen": "zurückgezogen"}
MAX_RUECKMELDUNG = 4000  # Zeichen Text einer Rückmeldung


def eigene_ref(n: int) -> str:
    return f"eigene-{n}"


def _datei_zeilen(pfade: list[str], info: list[tuple[bool, bool, int]]) -> list[dict]:
    zeilen = []
    info = list(info) + [(False, False, 0)] * (len(pfade) - len(info))
    for nr, (pfad, (original, pdf, seiten)) in enumerate(zip(pfade, info, strict=False)):
        endung = pfad.rsplit(".", 1)[-1].lower() if "." in pfad else ""
        zeilen.append({"nr": nr, "name": dateiname(pfad), "endung": endung, "original": original,
                       "pdf": pdf or (original and endung == "pdf"), "seiten": seiten})
    return zeilen


def dokument_ansicht(kette: list[dict], rueckmeldungen: list[dict], stand: dict, vorschauen: dict[str, list],
                     kosten: dict[str, float], art: dict | None, heute: str) -> dict:
    """Alles für /dokument/<ursprung>.
    kette: Aufträge der Kette (Ursprung zuerst); rueckmeldungen: Aufträge an feedback mit bezug in der Kette;
    stand: agentkit.fassungen.lesen(); vorschauen: Auftrag -> dateien.vorschau_info(); kosten: Auftrag -> USD.
    Fassungen neueste zuerst: Ergebnisse des Agenten („Fassung n“) und eigene Fassungen („Deine Fassung k“),
    Dateien zur Rückmeldung, die nur Anmerkungen sind, stehen bei den Rückmeldungen. haupt: die finale Fassung,
    sonst die neueste fertige."""
    final_ref = (stand.get("final") or {}).get("fassung") or ""
    eintraege = []
    n = 0
    for a in kette:
        if a.get("status") == "erledigt":
            n += 1
        d = a.get("daten") or {}
        eintraege.append({
            "ref": a["id"], "art": "agent", "name": f"Fassung {n}" if a.get("status") == "erledigt" else
            STATUS_TEXT.get(a.get("status"), a.get("status") or "").capitalize(),
            "status": a.get("status"), "status_text": STATUS_TEXT.get(a.get("status"), a.get("status") or ""),
            "zeit": a.get("abgeschlossen") or a.get("erstellt") or "",
            "nachbesserung": a["id"] != kette[0]["id"],
            "kern": d.get("kern") if isinstance(d.get("kern"), str) else "",
            "punkte": [p for p in d.get("punkte") or [] if isinstance(p, str)][:12],
            "pruefen": d.get("pruefen") if isinstance(d.get("pruefen"), str) else "",
            "ergebnis": a.get("ergebnis", "") if a.get("status") != "erledigt" or not d.get("kern") else "",
            "auftrag_text": a.get("text", ""), "kosten": kosten.get(a["id"]),
            "dateien": _datei_zeilen(a.get("ergebnis_dateien") or [], vorschauen.get(a["id"]) or []),
            "final": final_ref == a["id"], "final_moeglich": a.get("status") == "erledigt"})
    k = 0
    anmerkungen = []
    for e in sorted(stand.get("eigene") or [], key=lambda e: e.get("n", 0)):
        if (e.get("art") or "fassung") != "fassung":
            anmerkungen.append({"n": e["n"], "name": e.get("name", ""), "zeit": e.get("zeit", "")})
            continue
        k += 1
        ref = eigene_ref(e["n"])
        eintraege.append({"ref": ref, "art": "eigene", "name": f"Deine Fassung {k}", "status": "erledigt",
                          "status_text": "hochgeladen", "zeit": e.get("zeit", ""), "nachbesserung": False,
                          "kern": e.get("notiz", ""), "punkte": [], "pruefen": "", "ergebnis": "",
                          "auftrag_text": "", "kosten": None, "eigene_n": e["n"], "datei_name": e.get("name", ""),
                          "dateien": [], "final": final_ref == ref, "final_moeglich": True})
    eintraege.sort(key=lambda e: e["zeit"], reverse=True)
    for e in eintraege:
        e["zeit_text"] = zeit_kurz(e["zeit"], heute)
    fertig = [e for e in eintraege if e["status"] == "erledigt"]
    haupt = next((e for e in eintraege if e["final"]), None) or (fertig[0] if fertig else None)
    bezug = next((e["ref"] for e in eintraege if e["art"] == "agent" and e["status"] == "erledigt"), "")
    rueck = [{"id": r["id"], "text": r.get("text", ""), "zeit_text": zeit_kurz(r.get("erstellt") or "", heute),
              "status_text": STATUS_TEXT.get(r.get("status"), r.get("status") or ""),
              "antwort": r.get("ergebnis", "") if r.get("status") != "neu" else ""}
             for r in sorted(rueckmeldungen, key=lambda r: r.get("erstellt") or "", reverse=True)]
    for a in anmerkungen:
        a["zeit_text"] = zeit_kurz(a["zeit"], heute)
    return {"fassungen": eintraege, "haupt": haupt, "bezug": bezug, "laeuft": any(a.get("status") == "neu"
            for a in kette), "rueckmeldungen": rueck, "anmerkungen": anmerkungen,
            "rueckmeldung_moeglich": bool(bezug) and (art or {}).get("rueckmeldung", True),
            "kosten": round(sum(v for v in kosten.values() if v), 2) if kosten else None}


def final_erlaubt(ref: str, ansicht: dict) -> bool:
    return any(e["ref"] == ref and e["final_moeglich"] for e in ansicht["fassungen"])


def rueckmeldung_pruefen(text: str, hat_datei: bool) -> tuple[str, list[str]]:
    text = (text or "").replace("\r\n", "\n").strip()
    if not text and not hat_datei:
        return text, ["Schreib, was anders werden soll, oder hänge eine Datei an."]
    if len(text) > MAX_RUECKMELDUNG:
        return text, [f"Höchstens {MAX_RUECKMELDUNG} Zeichen."]
    return text, []


def datei_erlaubt(name: str, endungen: set[str]) -> str:
    """Fehlertext, wenn die Endung nicht passt, sonst ""."""
    endung = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
    if endung not in endungen:
        return f"{name}: nur {', '.join(sorted(e.lstrip('.') for e in endungen))}"
    return ""


def dateiname_bereinigen(name: str) -> str:
    name = re.sub(r"[^\w.\- ]", "_", (name or "").replace("\\", "/").rsplit("/", 1)[-1]).strip().lstrip(".")
    return name[:120] or "datei"


# --- Heute und Kosten --------------------------------------------------------------------------------------------

WARTET_TAGE = 14


def wartet_auf_mich(docs: list[dict], heute: str) -> list[dict]:
    """Dokumente, bei denen Jan dran ist: fertig, aber nicht final (in den letzten WARTET_TAGE Tagen), und solche, die
    nicht geklappt haben. docs aus dokumente()."""
    from datetime import date, timedelta
    grenze = (date.fromisoformat(heute) - timedelta(days=WARTET_TAGE)).isoformat()
    return [d for d in docs if d["rot"] or (d["marke"].startswith("Fassung") and d["zeit"][:10] >= grenze)]


def kosten_zeilen(laeufe: list[dict], ursprung_von: dict[str, str], titel_von_: dict[str, str]) -> list[dict]:
    """Letzte Läufe für die rechte Spalte: {"text", "unter", "usd", "link", "ok"}. ursprung_von: Auftrag ->
    Ursprung des Dokuments, titel_von_: Ursprung -> Titel."""
    from datetime import datetime
    zeilen = []
    for e in laeufe:
        u = ursprung_von.get(e.get("auftrag") or "")
        zeilen.append({"text": titel_von_.get(u, "") if u else "", "agent": e.get("agent") or "?",
                       "usd": f"{(e.get('usd') or 0):.2f}", "ok": bool(e.get("ok")),
                       "zeit": datetime.fromtimestamp(e["zeit"]).strftime("%d.%m. %H:%M") if e.get("zeit") else "",
                       "link": f"/dokument/{u}" if u else ""})
    return zeilen
