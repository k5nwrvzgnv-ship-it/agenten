"""Bericht (Renderer-Art "bericht") und Modell (Art "arbeitsmappe") aus den geprüften Schritt-JSONs.

Reine Logik ohne Netz und ohne Claude: Jede Zahl im Bericht kommt aus einem geprüften Zahl-Objekt und trägt ihren
Beleg (Quellen-ID) oder das Kennzeichen Annahme; berechnete Zahlen tragen die Belege ihrer Bestandteile und
"Annahme", sobald einer davon angenommen ist. Texte von Claude werden gekürzt und von Quellen-IDs befreit
(der Renderer lehnt IDs im Fließtext ab). Grenzen siehe shared/renderer/FORMAT.md.
"""

import re
from datetime import date

import schritte

_ID_IM_TEXT = re.compile(r"\s*\[?Q-\d{8}-[a-z]+-[0-9a-f]{6}\]?")
MAX_ZELLE, MAX_TEXT, MAX_ZEILEN = 500, 5000, 100
MAX_WERT = 1e9  # Arbeitsmappe: größere Beträge nimmt der Renderer nicht


def _text(x, n: int = MAX_TEXT) -> str:
    if x is None:
        return ""
    t = _ID_IM_TEXT.sub("", str(x)).strip()
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def ist_zahl(z) -> bool:
    return isinstance(z, dict) and isinstance(z.get("wert"), (int, float)) and not isinstance(z.get("wert"), bool)


def zahl_text(w: float) -> str:
    """Deutsche Schreibweise: 1.234,5; höchstens 4 Nachkommastellen, ohne Nullen am Ende."""
    if float(w).is_integer():
        s = f"{int(w):,}"
    else:
        s = f"{w:,.4f}".rstrip("0").rstrip(".")
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def blaetter(z) -> list[dict]:
    """Die belegten Bestandteile eines Zahl-Objekts (bei berechnet rekursiv)."""
    if not ist_zahl(z) and not (isinstance(z, dict) and "berechnet" in z):
        return []
    b = z.get("berechnet")
    if isinstance(b, dict):
        return [x for teil in b.get("aus") or [] for x in blaetter(teil)]
    return [z]


def belege(z) -> tuple[list[str], bool]:
    """(Quellen-IDs, ob eine Annahme darin steckt)."""
    ids, annahme = [], False
    for b in blaetter(z):
        q = b.get("quelle")
        if isinstance(q, str) and q not in ids:
            ids.append(q)
        if "annahme" in b:
            annahme = True
    return ids, annahme


def zelle(z) -> str | dict:
    """Zahl-Objekt als Tabellenzelle mit Beleg; sonst leerer Text."""
    if not ist_zahl(z):
        return ""
    text = _text(f"{zahl_text(z['wert'])} {z.get('einheit') or ''}", MAX_ZELLE)
    ids, annahme = belege(z)
    erg: dict = {"text": text}
    if ids:
        erg["quellen"] = [{"art": "quelle", "stelle": i} for i in ids[:10]]
    if annahme:
        erg["kennzeichnung"] = "annahme"
    return erg if len(erg) > 1 else text


def _alle_ids(daten) -> list[str]:
    ids: list[str] = []

    def gehen(x):
        if isinstance(x, dict):
            if isinstance(x.get("quelle"), str) and x["quelle"] not in ids:
                ids.append(x["quelle"])
            for v in x.values():
                gehen(v)
        elif isinstance(x, list):
            for v in x:
                gehen(v)

    gehen(daten)
    return ids


def _tabelle(titel: str, kopf: list[str], zeilen: list[list], erste_fett: bool = True) -> dict | None:
    if not zeilen:
        return None
    return {"typ": "tabelle", "titel": _text(titel, 200), "kopf": kopf, "zeilen": zeilen[:MAX_ZEILEN],
            "erste_spalte_fett": erste_fett}


def _liste(daten: dict | None, feld: str) -> list[dict]:
    return [x for x in (daten or {}).get(feld) or [] if isinstance(x, dict)]


def beschreibung(thema: str, daten: dict[int, dict], metas: dict[str, dict], heute: date,
                 abgebrochen: tuple[int, list[str]] | None = None) -> dict:
    """Renderer-Beschreibung (Art bericht). daten: Nr -> geprüfte Schritt-Daten (nur vorhandene Schritte).

    abgebrochen: (Nr, Fehler) des Schritts, an dem die Recherche gescheitert ist.
    """
    b: list[dict] = []
    fertig = [n for n in sorted(daten) if n >= 1]
    if abgebrochen:
        nr, fehler = abgebrochen
        b.append({"typ": "hinweis", "art": "einschraenkung", "titel": "Recherche unvollständig",
                  "text": _text(f"Abgebrochen in Schritt {nr} ({schritte.schritt(nr).name}). Der Bericht enthält "
                                f"nur die geprüften Schritte {', '.join(map(str, fertig)) or '(keine)'}. "
                                "Verbleibende Fehler: " + "; ".join(fehler[:5]))})

    s1 = daten.get(1)
    if s1:
        b.append({"typ": "ueberschrift", "text": "Wertschöpfungskette"})
        zeilen = []
        for st in _liste(s1, "stufen"):
            b.append({"typ": "ueberschrift", "ebene": 2, "text": _text(st.get("name"), 200) or "Stufe"})
            text = " ".join(t for t in (_text(st.get("beschreibung")), _text(st.get("einschaetzung"))) if t)
            if text:
                b.append({"typ": "absatz", "text": _text(text)})
            for f in _liste(st, "firmen"):
                zeilen.append([_text(f.get("name"), MAX_ZELLE), str(f.get("jahr") or ""), zelle(f.get("umsatz")),
                               zelle(f.get("marge")), zelle(f.get("kapitalrendite"))])
        if t := _tabelle("Firmen je Stufe", ["Firma", "Jahr", "Umsatz", "Marge", "Kapitalrendite"], zeilen):
            b.append(t)

    s2 = daten.get(2)
    if s2:
        b.append({"typ": "ueberschrift", "text": "Lücken zwischen Angebot und Nachfrage"})
        for lu in _liste(s2, "luecken"):
            b.append({"typ": "ueberschrift", "ebene": 2, "text": _text(lu.get("titel"), 200) or "Lücke"})
            teile = [_text(lu.get("beschreibung"))]
            teile += [f"{k.capitalize()}: {_text(lu.get(k))}" for k in ("angebot", "nachfrage") if lu.get(k)]
            if text := " ".join(t for t in teile if t):
                b.append({"typ": "absatz", "text": _text(text)})
            zeilen = [[_text(be.get("aussage"), MAX_ZELLE), zelle(be.get("zahl"))] for be in _liste(lu, "belege")]
            if t := _tabelle("Belege", ["Aussage", "Zahl"], zeilen, erste_fett=False):
                b.append(t)

    s3 = daten.get(3)
    if s3:
        b.append({"typ": "ueberschrift", "text": "Ursachen und Marktgröße"})
        for lu in _liste(s3, "luecken"):
            b.append({"typ": "ueberschrift", "ebene": 2, "text": _text(lu.get("titel"), 200) or "Lücke"})
            text = (f"Ursache: {_text(lu.get('ursache'))} Bleibt die Lücke? {lu.get('bleibt', 'unklar')}. "
                    f"{_text(lu.get('begruendung'))}")
            ff = lu.get("five_forces") if isinstance(lu.get("five_forces"), dict) else {}
            if ff:
                text += " Five Forces: " + "; ".join(f"{k.replace('_', ' ')}: {_text(v, 400)}" for k, v in ff.items())
            if lu.get("zyklus"):
                text += f" Zyklus: {_text(lu['zyklus'], 600)}"
            b.append({"typ": "absatz", "text": _text(text)})
            m = lu.get("marktgroesse")
            if ist_zahl(m):
                aus = (m.get("berechnet") or {}).get("aus") or []
                zeilen = [[f"Faktor {i + 1}", zelle(f)] for i, f in enumerate(aus)]
                zeilen.append(["Marktgröße (Produkt)", zelle(m)])
                b.append(_tabelle("Marktgröße von unten", ["Größe", "Wert"], zeilen))

    s4 = daten.get(4)
    if s4:
        b.append({"typ": "ueberschrift", "text": "Hypothesen"})
        for i, h in enumerate(_liste(s4, "hypothesen"), 1):
            abbruch = "\n".join(f"- bis {a.get('pruefen_bis')}: {_text(a.get('text'), 600)}"
                                for a in _liste(h, "abbruchkriterien"))
            b.append({"typ": "hinweis", "art": "wichtig", "titel": _text(f"Hypothese {i}: {h.get('titel')}", 200),
                      "text": _text(f"{_text(h.get('these'))}\nSicherheit: {h.get('sicherheit')}.\n"
                                    f"Abbruchkriterien:\n{abbruch}")})
            if h.get("begruendung"):
                b.append({"typ": "absatz", "text": _text(h["begruendung"])})
            sz = h.get("szenarien") if isinstance(h.get("szenarien"), dict) else {}
            zeilen = [[name, zelle(s.get("umsatz")), zelle(s.get("ergebnis")), _text(s.get("text"), MAX_ZELLE)]
                      for name, s in sz.items() if isinstance(s, dict)]
            if t := _tabelle("Szenarien", ["Szenario", "Umsatz", "Ergebnis", "Annahme dahinter"], zeilen):
                b.append(t)

    s5 = daten.get(5)
    if s5:
        b.append({"typ": "ueberschrift", "text": "Externe Prüfung"})
        for p in _liste(s5, "pruefungen"):
            b.append({"typ": "ueberschrift", "ebene": 2, "text": _text(p.get("hypothese"), 200) or "Hypothese"})
            zeilen = [[_text(v.get("name"), MAX_ZELLE), _text(v.get("ergebnis"), MAX_ZELLE), zelle(v.get("zahl"))]
                      for v in _liste(p, "vergleichsfirmen")]
            if t := _tabelle("Vergleichsfirmen", ["Firma", "Ergebnis", "Zahl"], zeilen):
                b.append(t)
            r = p.get("rueckrechnung") if isinstance(p.get("rueckrechnung"), dict) else None
            if r:
                b.append(_tabelle(f"Rückrechnung: {_text(r.get('fall'), 150)}", ["", "Wert"],
                                  [["erwartet", zelle(r.get("erwartet"))], ["tatsächlich", zelle(r.get("tatsaechlich"))]]))
                if r.get("fazit"):
                    b.append({"typ": "absatz", "text": _text(r["fazit"])})
            zeilen = [[_text(g.get("aussage"), MAX_ZELLE), _text(g.get("indikator"), MAX_ZELLE),
                       zelle(g.get("erwartet")), str(g.get("pruefen_ab") or "")] for g in _liste(p, "prognosen")]
            if t := _tabelle("Datierte Prognosen", ["Aussage", "Indikator", "Erwartet", "Prüfen ab"], zeilen, False):
                b.append(t)
            entw = [f"{e.get('art')} an {_text(e.get('an'), 200)}: {_text(e.get('betreff'), 300)}"
                    for e in _liste(p, "entwuerfe")]
            if entw:
                b.append({"typ": "absatz", "text": "Entwürfe (gehen erst nach Freigabe raus): " + "; ".join(entw)})

    if not b:
        b.append({"typ": "absatz", "text": "Kein Schritt der Recherche hat die Prüfung bestanden."})

    ids = [i for i in _alle_ids([daten[n] for n in fertig]) if i in metas]
    verzeichnis = [{"id": i, "text": _text(f"{metas[i].get('beschreibung')}, {metas[i].get('art')}, abgerufen "
                                           f"{_datum(metas[i].get('abgerufen'))}, {metas[i].get('url')}", 1000)}
                   for i in ids[:200]]
    offene = [_text(o, 1000) for o in (s1 or {}).get("offene_punkte") or [] if isinstance(o, str) and o.strip()]
    erg = {"art": "bericht", "rubrik": "Wirtschaftlichkeit", "titel": _text(thema, 200),
           "untertitel": "Wertschöpfung, Lücken und Hypothesen", "datum": f"{heute:%d.%m.%Y}", "bloecke": b[:200]}
    if offene:
        erg["offene_fragen"] = offene[:30]
    if verzeichnis:
        erg["quellenverzeichnis"] = verzeichnis
    _fremde_ids_entfernen(erg, {v["id"] for v in verzeichnis})
    return erg


def aus_ergebnissen(ergebnisse) -> tuple[dict[int, dict], tuple[int, list[str]] | None]:
    """Aus ablauf.SchrittErgebnis: (geprüfte Daten je Schritt 1-5, Abbruch (Nr, Fehler) oder None)."""
    daten = {e.nr: e.daten for e in ergebnisse if e.ok and e.nr >= 1 and isinstance(e.daten, dict)}
    letzte = ergebnisse[-1] if ergebnisse else None
    abbruch = (letzte.nr, list(letzte.fehler)) if letzte is not None and not letzte.ok else None
    return daten, abbruch


def _fremde_ids_entfernen(erg: dict, bekannt: set[str]) -> None:
    """Belege ohne Eintrag im Quellenverzeichnis (sollte nach der Prüfung nicht vorkommen) als unsicher zeigen."""
    def gehen(x):
        if isinstance(x, dict):
            q = x.get("quellen")
            if isinstance(q, list):
                rest = [e for e in q if e.get("stelle") in bekannt]
                if len(rest) != len(q):
                    x["kennzeichnung"] = x.get("kennzeichnung") or "unsicher"
                if rest:
                    x["quellen"] = rest
                else:
                    del x["quellen"]
            for v in x.values():
                gehen(v)
        elif isinstance(x, list):
            for v in x:
                gehen(v)
    gehen(erg["bloecke"])


def _datum(iso) -> str:
    try:
        return f"{date.fromisoformat(str(iso)[:10]):%d.%m.%Y}"
    except ValueError:
        return "?"


def _beleg_text(z) -> str:
    ids, annahme = belege(z)
    teile = ids[:3] + (["Annahme"] if annahme else [])
    return ", ".join(teile)


def _wert(z):
    return z["wert"] if ist_zahl(z) and abs(z["wert"]) <= MAX_WERT else None


def modell(thema: str, daten: dict[int, dict]) -> dict | None:
    """Arbeitsmappe: Marktgrößen (Faktoren, Excel multipliziert) und Szenarien je Hypothese. None ohne Inhalt."""
    blaetter_ = []
    markt = []
    for lu in _liste(daten.get(3), "luecken"):
        m = lu.get("marktgroesse")
        aus = (m.get("berechnet") or {}).get("aus") if isinstance(m, dict) else None
        if not isinstance(aus, list) or not 2 <= len(aus) <= 4 or not all(ist_zahl(a) for a in aus):
            continue
        zeile = {"luecke": _text(lu.get("titel"), 200), "einheit": _text(m.get("einheit"), 100),
                 "beleg_claude": _text(f"{zahl_text(m['wert'])} {m.get('einheit') or ''}", 100)}
        for i, a in enumerate(aus, 1):
            zeile[f"f{i}"] = _wert(a)
            zeile[f"e{i}"] = _text(f"{a.get('einheit') or ''} [{_beleg_text(a)}]", 200)
        markt.append(zeile)
    if markt:
        spalten = [{"id": "luecke", "kopf": "Lücke", "art": "text", "breite": 34}]
        for i in range(1, 5):
            spalten += [{"id": f"f{i}", "kopf": f"Faktor {i}", "art": "zahl", "nachkommastellen": 4},
                        {"id": f"e{i}", "kopf": f"Einheit/Beleg {i}", "art": "text", "breite": 26}]
        spalten += [{"id": "markt", "kopf": "Marktgröße", "art": "rechnung", "nachkommastellen": 2,
                     "formel": "f1 * f2 * wenn_leer(f3, 1) * wenn_leer(f4, 1)"},
                    {"id": "einheit", "kopf": "Einheit", "art": "text", "breite": 22},
                    {"id": "beleg_claude", "kopf": "Geprüfter Wert", "art": "text", "breite": 18}]
        blaetter_.append({"name": "Marktgröße", "titel": "Marktgröße von unten je Lücke",
                          "hinweise": ["Faktoren dürfen geändert werden, Excel rechnet die Marktgröße neu.",
                                       "Beleg je Faktor: Quellen-ID (siehe Bericht) oder Annahme."],
                          "zeilen": len(markt), "fixierte_spalten": 1, "spalten": spalten, "werte": markt})
    szen = []
    for h in _liste(daten.get(4), "hypothesen"):
        sz = h.get("szenarien") if isinstance(h.get("szenarien"), dict) else {}
        for name, s in sz.items():
            if not isinstance(s, dict):
                continue
            u, e = s.get("umsatz"), s.get("ergebnis")
            szen.append({"hypothese": _text(h.get("titel"), 200), "szenario": _text(name, 40),
                         "umsatz": _wert(u), "u_einheit": _text((u or {}).get("einheit"), 100) if ist_zahl(u) else "",
                         "ergebnis": _wert(e), "e_einheit": _text((e or {}).get("einheit"), 100) if ist_zahl(e) else "",
                         "beleg": _text(f"Umsatz: {_beleg_text(u)}; Ergebnis: {_beleg_text(e)}", 300)})
    if szen:
        blaetter_.append({"name": "Szenarien", "titel": "Szenarien je Hypothese",
                          "hinweise": ["Marge = Ergebnis / Umsatz, nur sinnvoll bei gleicher Einheit."],
                          "zeilen": min(len(szen), 500), "fixierte_spalten": 2, "spalten": [
                              {"id": "hypothese", "kopf": "Hypothese", "art": "text", "breite": 34},
                              {"id": "szenario", "kopf": "Szenario", "art": "text", "breite": 14},
                              {"id": "umsatz", "kopf": "Umsatz", "art": "zahl", "nachkommastellen": 2},
                              {"id": "u_einheit", "kopf": "Einheit Umsatz", "art": "text", "breite": 22},
                              {"id": "ergebnis", "kopf": "Ergebnis", "art": "zahl", "nachkommastellen": 2},
                              {"id": "e_einheit", "kopf": "Einheit Ergebnis", "art": "text", "breite": 22},
                              {"id": "marge", "kopf": "Marge", "art": "rechnung", "formel": "ergebnis / umsatz",
                               "nachkommastellen": 3},
                              {"id": "beleg", "kopf": "Beleg", "art": "text", "breite": 40}],
                          "werte": szen[:500]})
    if not blaetter_:
        return None
    return {"art": "arbeitsmappe", "titel": _text(f"Modell: {thema}", 200), "blaetter": blaetter_}
