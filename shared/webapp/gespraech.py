"""Reine Logik für Gespräche in der Mitte (Bauplan bauplan-gespraech.md), ohne Netz und ohne Dateizugriff.

bloecke() zerlegt eine Antwort von Claude (Markdown) in Blöcke, die die Vorlagen mit Autoescape zeigen. Es gibt nie
HTML von außen: Text bleibt Text, Links nur http/https (logik.link_ziel).

Blöcke:
  {"ueberschrift": [Teile], "stufe": 2|3}          # "# " und "## " werden 2, "### " und tiefer 3
  {"absatz": [Teile]}
  {"punkte": [[Teile], ...], "nummeriert": bool}
  {"zitat": [Teile]}                                # Zeilen mit "> "
  {"tabelle": {"kopf": [[Teile], ...], "zeilen": [[[Teile], ...], ...]}}
  {"code": "Text"}                                  # ``` ohne Sprache oder mit fremder Sprache
  {"baustein": {"art", "name", "bloecke", "kopie"}} # ```baustein <art>: graue Fläche mit "Kopieren"
  {"linie": True}                                   # "---"
Teile: {"text", "fett", "kursiv", "code", "link" (nur bei Links)}.
"""

import re
from datetime import datetime

import logik

# Arten der Bausteine (Prompt von lia/chat: ```baustein <art>), Name für Lia
BAUSTEINE = {"reihenfrage": "Reihenfrage", "merksatz": "Merksatz", "arbeitsauftrag": "Arbeitsauftrag",
             "fall": "Fallbeispiel", "text": "Text"}

_INLINE = re.compile(r"\*\*(?P<fett>.+?)\*\*|`(?P<code>[^`\n]+)`|(?<![\w*])\*(?P<kursiv>[^*\s](?:[^*\n]*?[^*\s])?)\*(?![\w*])")
_PUNKT = re.compile(r"^(?P<nr>[-*+]|\d+[.)])\s+(?P<text>.*)$")
_TRENNER = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$")


def teile(zeile: str, fett: bool = False, kursiv: bool = False) -> list[dict]:
    """Teile einer Zeile: **fett**, *kursiv*, `code`, [Titel](URL)."""
    out, pos = [], 0
    for m in _INLINE.finditer(zeile):
        if m.start() > pos:
            out += _mit_links(zeile[pos:m.start()], fett, kursiv)
        if m.group("fett") is not None:
            out += teile(m.group("fett"), True, kursiv)
        elif m.group("kursiv") is not None:
            out += teile(m.group("kursiv"), fett, True)
        else:
            out.append({"text": m.group("code"), "fett": fett, "kursiv": kursiv, "code": True})
        pos = m.end()
    if pos < len(zeile):
        out += _mit_links(zeile[pos:], fett, kursiv)
    return out


def _mit_links(text: str, fett: bool, kursiv: bool) -> list[dict]:
    out = []
    for t in logik._links(text, fett):
        t.setdefault("kursiv", kursiv)
        t.setdefault("code", False)
        out.append(t)
    return out


def klartext(text: str) -> str:
    """Text zum Kopieren (Baustein nach Word): ohne **, *, ` und Link-Klammern, Listenpunkte als „– “."""
    zeilen = []
    for zeile in (text or "").replace("\r\n", "\n").split("\n"):
        z = zeile.rstrip()
        p = _PUNKT.match(z.strip())
        if p:
            z = ("– " if p.group("nr") in "-*+" else p.group("nr") + " ") + p.group("text")
        zeilen.append("".join(t["text"] for t in teile(z)))
    return "\n".join(zeilen).strip("\n")


def _zellen(zeile: str) -> list[str]:
    z = zeile.strip()
    if z.startswith("|"):
        z = z[1:]
    if z.endswith("|") and not z.endswith("\\|"):
        z = z[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", z)]


def bloecke(text: str, bausteine: bool = True) -> list[dict]:
    """Antwort in Blöcke (siehe Modulkopf). bausteine=False: ```baustein wird ein Codeblock (in Bausteinen selbst)."""
    zeilen = (text or "").replace("\r\n", "\n").split("\n")
    out: list[dict] = []
    absatz: list[str] = []

    def absatz_ende():
        if absatz:
            gesamt = []
            for i, z in enumerate(absatz):
                if i:
                    gesamt.append({"text": " ", "fett": False, "kursiv": False, "code": False})
                gesamt += teile(z)
            out.append({"absatz": gesamt})
            absatz.clear()

    i = 0
    while i < len(zeilen):
        roh = zeilen[i]
        z = roh.strip()
        zaun = re.match(r"^(`{3,}|~{3,})\s*(.*)$", z)
        if zaun:
            absatz_ende()
            marke, info = zaun.group(1), zaun.group(2).strip().split()
            inhalt = []
            i += 1
            while i < len(zeilen) and not zeilen[i].strip().startswith(marke):
                inhalt.append(zeilen[i])
                i += 1
            i += 1  # schließender Zaun (fehlt er, endet der Block am Textende)
            roh_text = "\n".join(inhalt).strip("\n")
            if bausteine and info and info[0].lower() == "baustein":
                art = info[1].lower() if len(info) > 1 and info[1].lower() in BAUSTEINE else "text"
                out.append({"baustein": {"art": art, "name": BAUSTEINE[art],
                                         "bloecke": bloecke(roh_text, bausteine=False), "kopie": klartext(roh_text)}})
            elif roh_text:
                out.append({"code": roh_text})
            continue
        if not z:
            absatz_ende()
            i += 1
            continue
        kopf = re.match(r"^(#{1,6})\s+(.*?)\s*#*$", z)
        if kopf:
            absatz_ende()
            out.append({"ueberschrift": teile(kopf.group(2)), "stufe": 2 if len(kopf.group(1)) <= 2 else 3})
            i += 1
            continue
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", z):
            absatz_ende()
            out.append({"linie": True})
            i += 1
            continue
        if z.startswith("|") and i + 1 < len(zeilen) and _TRENNER.match(zeilen[i + 1].strip()):
            absatz_ende()
            kopf_zellen = _zellen(z)
            reihen = []
            i += 2
            while i < len(zeilen) and zeilen[i].strip().startswith("|"):
                zellen = _zellen(zeilen[i])
                zellen = (zellen + [""] * len(kopf_zellen))[:len(kopf_zellen)]
                reihen.append([teile(c) for c in zellen])
                i += 1
            out.append({"tabelle": {"kopf": [teile(c) for c in kopf_zellen], "zeilen": reihen}})
            continue
        if z.startswith(">"):
            absatz_ende()
            inhalt = []
            while i < len(zeilen) and zeilen[i].strip().startswith(">"):
                inhalt.append(zeilen[i].strip()[1:].strip())
                i += 1
            out.append({"zitat": teile(" ".join(x for x in inhalt if x))})
            continue
        punkt = _PUNKT.match(z)
        if punkt:
            absatz_ende()
            nummeriert = punkt.group("nr") not in "-*+"
            if not out or "punkte" not in out[-1] or out[-1]["nummeriert"] != nummeriert:
                out.append({"punkte": [], "nummeriert": nummeriert})
            out[-1]["punkte"].append(teile(punkt.group("text")))
            i += 1
            continue
        if out and "punkte" in out[-1] and not absatz and roh[:1] in (" ", "\t"):
            # eingerückte Fortsetzung eines Listenpunkts
            out[-1]["punkte"][-1] += [{"text": " ", "fett": False, "kursiv": False, "code": False}, *teile(z)]
            i += 1
            continue
        absatz.append(z)
        i += 1
    absatz_ende()
    return out


def bausteine_von(bl: list[dict]) -> list[dict]:
    """Alle Bausteine einer Antwort, in Reihenfolge (für „Als Reihenfrage übernehmen“ und Tests)."""
    return [b["baustein"] for b in bl if "baustein" in b]


# --- Ebenen: Klasse/Kurs, Reihe, Stunde (Jan 09.11.: jedes Gespräch und jede Datei hängt an genau einer) -----------
EBENEN_WORT = {"klasse": "Klasse", "reihe": "Reihe", "stunde": "Stunde"}


def orte(reihen: list[dict], gruppen: list[dict]) -> dict[str, dict]:
    """Alle Orte nach ihrer festen id: {"ebene", "id", "name", "pfad" (für Lia, „Ethik › Klasse 8 › Straftheorien“),
    "link", "eltern" (id oder None), "reihe_id" (bei Reihe und Stunde), "archiv"}. Stunden: nur sichtbare."""
    out: dict[str, dict] = {}
    for g in gruppen:
        out[g["gruppe_id"]] = {"ebene": "klasse", "id": g["gruppe_id"], "name": g["gruppe"],
                               "pfad": f"{g['fach']} › {g['gruppe']}", "link": logik.klasse_link(g), "eltern": None,
                               "reihe_id": "", "archiv": g["archiv"]}
    for r in reihen:
        pfad = f"{r['fach']} › {r['gruppe']} › {r['titel']}"
        out[r["id"]] = {"ebene": "reihe", "id": r["id"], "name": r["titel"], "pfad": pfad, "link": logik.reihe_link(r),
                        "eltern": r["gruppe_id"] if r["gruppe_id"] in out else None, "reihe_id": r["id"],
                        "archiv": r["archiv"]}
        wort = logik.stunden_wort(r)[0]
        for nr, st in enumerate(logik.reihe_stunden(r), 1):
            name = f"{wort} {nr}" + (f": {st['thema']}" if st.get("thema") else "")
            out[st["id"]] = {"ebene": "stunde", "id": st["id"], "name": name, "pfad": f"{pfad} › {wort} {nr}",
                             "link": logik.stunde_link(r, nr), "eltern": r["id"], "reihe_id": r["id"],
                             "archiv": r["archiv"]}
    return out


def kette(orte_: dict[str, dict], ort_id: str | None) -> list[dict]:
    """Der Ort und alles darüber, oberstes zuerst (Klasse, Reihe, Stunde). Unbekannt: leer."""
    out, gesehen = [], set()
    while ort_id and ort_id in orte_ and ort_id not in gesehen:
        gesehen.add(ort_id)
        out.insert(0, orte_[ort_id])
        ort_id = orte_[ort_id]["eltern"]
    return out


def darunter(orte_: dict[str, dict], ort_id: str) -> list[str]:
    """ids aller Orte unter diesem (Reihen und Stunden einer Klasse, Stunden einer Reihe), in Reihenfolge."""
    kinder = [o["id"] for o in orte_.values() if o["eltern"] == ort_id]
    return [x for k in kinder for x in (k, *darunter(orte_, k))]


# --- Gespräch als Ansicht (Daten von lia/chat: schnittstelle.gespraech(), gespraeche()) -------------------------------
FOTO_ENDUNGEN = (".jpg", ".jpeg", ".png")
WOCHENTAGE = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
FEHLER_SATZ = "Das hat nicht geklappt. Schick die Nachricht bitte noch einmal."


def _zeit(text: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(text) if text else None
    except ValueError:
        return None


def tag_text(z: datetime, jetzt: datetime) -> str:
    z = z.astimezone(jetzt.tzinfo)
    if z.date() == jetzt.date():
        return "Heute"
    if (jetzt.date() - z.date()).days == 1:
        return "Gestern"
    return f"{WOCHENTAGE[z.weekday()]} {z:%d.%m.}"


def zuletzt_text(text: str | None, jetzt: datetime) -> str:
    """„heute 14:16“, „gestern“, „Mo 09.11.“ für Listen."""
    z = _zeit(text)
    if z is None:
        return ""
    t = tag_text(z, jetzt)
    return f"heute {z.astimezone(jetzt.tzinfo):%H:%M}" if t == "Heute" else t.lower() if t == "Gestern" else t


def ort_von(ort: dict | None, orte_: dict[str, dict]) -> dict | None:
    """Ort eines Gesprächs aus den Orten der App; None: ohne Ort oder unbekannt (z. B. Stunde gelöscht)."""
    if not isinstance(ort, dict):
        return None
    o = orte_.get(str(ort.get("id") or ""))
    return o if o and o["ebene"] == ort.get("ebene") else None


def liste_zeile(k: dict, orte_: dict[str, dict], jetzt: datetime, mit_ort: bool = True) -> dict:
    """Eine Zeile in Listen der Gespräche (kurz() von lia/chat)."""
    o = ort_von(k.get("ort"), orte_)
    return {"id": k["id"], "name": k.get("name") or "Neues Gespräch", "link": f"/gespraech/{k['id']}",
            "unter": (o["pfad"] if o else "ohne Ort") if mit_ort else "", "zuletzt": zuletzt_text(k.get("zuletzt"), jetzt),
            "laeuft": bool(k.get("laeuft")), "neu": bool(k.get("neu"))}


def verlauf(g: dict, jetzt: datetime, saetze: dict[str, str] | None = None) -> list[dict]:
    """Nachrichten mit Tagestrennern: {"tag"}, {"du": True, "text", "fotos", "dateien", "zeit", "fehler", "satz"},
    {"claude": True, "bloecke", "zeit", "fehler"} und am Ende {"denkt": True}, solange Lias Nachricht wartet.
    Fotos und Dateien als {"name", "link"} (Route /gespraech/<id>/datei/<nachricht>/<name>).
    Schlägt eine Antwort fehl, trägt lia/chat das an Lias Eintrag ein (stand "fehler"); den Satz für Lia liefert
    antwort_holen, die App reicht ihn als saetze {nachricht_id: Satz} herein (sonst FEHLER_SATZ)."""
    out, tag = [], None
    for e in g.get("eintraege", []):
        z = _zeit(e.get("zeit"))
        if z is not None and tag_text(z, jetzt) != tag:
            tag = tag_text(z, jetzt)
            out.append({"tag": tag})
        zeit = f"{z.astimezone(jetzt.tzinfo):%H:%M}" if z else ""
        if e.get("rolle") == "lia":
            basis = f"/gespraech/{g['id']}/datei/{e.get('id', '')}/"
            out.append({"du": True, "text": e.get("text") or "", "zeit": zeit,
                        "fotos": [{"name": n, "link": basis + n} for n in e.get("fotos") or []],
                        "dateien": [{"name": n, "link": basis + n} for n in e.get("dateien") or []],
                        "fehler": e.get("stand") == "fehler",
                        "satz": ((saetze or {}).get(e.get("id", "")) or FEHLER_SATZ) if e.get("stand") == "fehler" else ""})
        elif e.get("rolle") == "claude":
            ok = e.get("ok", True) and not e.get("fehler")
            out.append({"claude": True, "zeit": zeit, "fehler": not ok,
                        "bloecke": bloecke(e.get("text") or "") if ok else [],
                        "satz": "" if ok else (e.get("text") or FEHLER_SATZ)})
    if g.get("laeuft"):
        out.append({"denkt": True})
    return out


def reihenfrage_moeglich(o: dict | None) -> str:
    """id der Reihe, deren Reihenfrage ein Baustein übernehmen darf (Gespräch an Reihe oder Stunde), sonst ""."""
    return o["reihe_id"] if o and o["ebene"] in ("reihe", "stunde") and not o["archiv"] else ""
